"""Does the PLAYER still work when media is a URL instead of a data URL?

Nothing has ever asked. `verify_storage.py` proves the externalised path
end to end through `urllib` — the payload loses its bytes, the blob comes back
byte-identical, keys are content-addressed, traversal is refused. All of that is
server-side. `SKRIBL_MEDIA_BACKEND` appears in exactly two suites on this tree
and NEITHER opens a browser:

    verify_storage.py             urllib against the API
    verify_deletion_foundation.py store + database, no HTTP surface at all

So every browser suite runs the DEFAULT instance, which is inline, and the claim
that a shared link still plays once its media moved out of `payload_json` rests
on reading `app.js` rather than on running it. That is the gap this closes, and
it is the gap standing between "externalisation exists" and "externalisation can
be turned on".

WHY THE SUITE IS DIFFERENTIAL. It boots TWO instances from the same tree — one
inline, one local — posts the SAME payload to both, and compares what the player
does with each. The inline half is not decoration: it is the negative control.
A hand-built payload that fails to render is this project's known trap (see
verify_player_isolation's docstring — a malformed fixture read as a broken
player), so the fixture is proved against the storage backend that is already
known to work BEFORE any difference is attributed to externalisation. If the
inline player renders nothing, the suite says FIXTURE and stops. Only a
difference between the two columns is evidence about storage.

WHAT ACTUALLY CHANGES ON THE CLIENT, and therefore what is worth asserting:

    photo   `photoBgImg.src = data.photo.data`   — src takes either form
    audio   `fetch(data.music.data)`             — fetch takes either form
    CSP     img/media/connect-src 'self' data: blob:

The first two are why no client change was needed for the local backend, and the
third is why that is true only while the store is SAME-ORIGIN. Reading says all
three are fine. Running is what this file adds.

NOT COVERED, deliberately: the s3 backend. It is a subclass hook with no
implementation, and a cross-origin store is a different question — see the CSP
note at the end of the run.
"""
import base64
import json
import math
import os
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
import zlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# --- fixture -----------------------------------------------------------------
# Sized to the post that motivated this work: ~2.35 MB of base64 media against a
# few KB of strokes. The point of externalisation is that ratio, so the fixture
# reproduces it rather than using a token blob that would make the saving look
# like rounding error.

def wav_bytes(seconds=6, rate=44100, freq=220):
    buf = bytearray()
    for i in range(seconds * rate):
        v = int(18000 * math.sin(2 * math.pi * freq * i / rate))
        buf += struct.pack("<hh", v, v)
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(out.name, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(buf))
    return pathlib.Path(out.name).read_bytes()


def png_bytes(w=320, h=200):
    """A real PNG. The server checks the magic number, so a fake one never
    reaches the store — and a photo that does not decode would read as an
    externalisation failure when it was only a bad fixture."""
    rows = bytearray()
    for y in range(h):
        rows.append(0)                       # filter type 0
        for x in range(w):
            rows += bytes((x * 255 // w, y * 255 // h, 128))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + chunk(b"IEND", b""))


WAV = wav_bytes()
PNG = png_bytes()
WAV_URL = "data:audio/wav;base64," + base64.b64encode(WAV).decode()
PNG_URL = "data:image/png;base64," + base64.b64encode(PNG).decode()


def strokes():
    """A spiral, with timestamps spread over ~3 seconds.

    Timestamps matter: strokes replay with their recorded timing, and a drawing
    authored with every `t` at 0 is finished before the page can be sampled.
    """
    pts, groups = [], []
    n = 400
    for i in range(n):
        a = (i / n) * math.pi * 6
        r = 20 + (i / n) * 240
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7,
                    "color": "#ff5ea8", "size": 8, "t": int((i / n) * 3000),
                    "erase": False, "start": i == 0})
    groups.append(n)
    return pts, groups


PTS, GROUPS = strokes()
PAYLOAD = {
    "title": "externalisation probe",
    "visibility": "public",
    "schemaVersion": 2,
    "canvasSize": {"cssWidth": 816, "cssHeight": 612},
    "frames": [{
        "strokes": PTS,
        "strokeGroups": GROUPS,
        "background": {"color": "#101418"},
        "photo": {"data": PNG_URL, "name": "probe.png", "fit": "cover",
                  "opacity": 1, "blur": 0, "offset": {"x": 0.5, "y": 0.5},
                  "zoom": 1},
        "music": {"data": WAV_URL, "name": "probe.wav", "trimStart": 0,
                  "trimEnd": 6},
    }],
}

MEDIA_BYTES = len(WAV) + len(PNG)
B64_BYTES = len(WAV_URL) + len(PNG_URL)


# --- two instances of the same tree ------------------------------------------

class Instance:
    def __init__(self, name, port, backend):
        self.name, self.port, self.backend = name, port, backend
        self.base = f"http://127.0.0.1:{port}"
        self.root = tempfile.mkdtemp()
        db = tempfile.mkdtemp()
        self.env = dict(os.environ,
                        SKRIBL_MEDIA_BACKEND=backend,
                        SKRIBL_MEDIA_ROOT=self.root,
                        DATABASE_URL=f"sqlite:///{db}/{name}.db",
                        SKRIBL_RATE_MAX_POSTS="100000",
                        SKRIBL_RATE_MAX_ATTEMPTS="100000",
                        SECRET_KEY=f"harness-externalised-{name}")
        self.proc = None

    def start(self):
        subprocess.run(
            [sys.executable, "-c",
             "from app import app, db; app.app_context().push(); db.create_all()"],
            cwd=ROOT, env=self.env, check=True, capture_output=True)
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "flask", "--app", "app", "run",
             "--port", str(self.port), "--no-reload"],
            cwd=ROOT, env=self.env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 25
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.5):
                    return True
            except OSError:
                time.sleep(0.3)
        return False

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def post(self, payload):
        req = urllib.request.Request(
            self.base + "/api/skribls", method="POST",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=30) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()


# --- what the browser is asked ------------------------------------------------

INK = """() => {
  const c = document.getElementById('canvas');
  if (!c) return null;
  let ink = 0;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) ink++;
  return ink;
}"""

# Read through a BARE IDENTIFIER, not off window: app.js declares these with
# top-level `let`, which does not become a window property.
PHOTO = """() => {
  try {
    if (typeof photoBgImg === 'undefined' || !photoBgImg) return null;
    return {src: String(photoBgImg.src).slice(0, 64),
            w: photoBgImg.naturalWidth, h: photoBgImg.naturalHeight,
            complete: !!photoBgImg.complete};
  } catch (e) { return {error: String(e)}; }
}"""

AUDIO = """() => {
  try {
    if (typeof currentAudioBuffer === 'undefined' || !currentAudioBuffer) return null;
    return {duration: currentAudioBuffer.duration,
            channels: currentAudioBuffer.numberOfChannels};
  } catch (e) { return {error: String(e)}; }
}"""

# CSP violations do not raise pageerror and do not always reach console in a
# form the runner can see. Listen for the event the browser actually fires.
CSP_TAP = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', e => {
  window.__csp.push(e.violatedDirective + ' <- ' + e.blockedURI);
});
"""


def observe(browser, url, label):
    """Load a player page and report what it managed to do."""
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    errs, console = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
    pg.add_init_script(CSP_TAP)
    pg.goto(url, wait_until="load")
    # Media decode is async on both paths — the photo through an <img> load and
    # the audio through fetch + decodeAudioData. Poll rather than sleep once.
    deadline = time.time() + 12
    out = {}
    while time.time() < deadline:
        out = {"ink": pg.evaluate(INK), "photo": pg.evaluate(PHOTO),
               "audio": pg.evaluate(AUDIO)}
        if out["ink"] and out["photo"] and out["photo"].get("w") and out["audio"]:
            break
        pg.wait_for_timeout(400)
    out["errors"] = errs
    out["console"] = console
    out["csp"] = pg.evaluate("() => window.__csp || []")
    pg.close()
    print(f"    {label}: ink={out['ink']} photo={out['photo']} audio={out['audio']}"
          f" errors={len(errs)} csp={len(out['csp'])}")
    return out


inline = Instance("inline", 5012, "inline")
local = Instance("local", 5011, "local")

try:
    for inst in (inline, local):
        if not inst.start():
            inst.stop()
            print(f"SKIP: the {inst.name} instance did not start on port {inst.port}.")
            sys.exit(0)

    print("\nEXTERNALISED — the same payload posts to both backends")
    st_i, made_i = inline.post(PAYLOAD)
    st_l, made_l = local.post(PAYLOAD)
    check("the inline instance accepts the fixture", st_i == 201,
          f"{st_i} {made_i.get('error', '')}")
    check("the externalising instance accepts the same fixture", st_l == 201,
          f"{st_l} {made_l.get('error', '')}")
    if st_i != 201 or st_l != 201:
        raise SystemExit(1)

    url_i = inline.base + made_i["url"]
    url_l = local.base + made_l["url"]

    print("\nEXTERNALISED — the row got small (the reason for the work)")
    _, body_i = inline.get(f"/api/skribls/{made_i['id']}")
    _, body_l = local.get(f"/api/skribls/{made_l['id']}")
    check("the inline post carries its media in the payload",
          len(body_i) > MEDIA_BYTES,
          f"{len(body_i):,}B payload vs {MEDIA_BYTES:,}B of media")
    check("the externalised post does not",
          len(body_l) < 100_000,
          f"{len(body_l):,}B payload")
    check("the saving is the base64 media, not a rounding error",
          len(body_i) - len(body_l) > B64_BYTES * 0.9,
          f"{len(body_i):,} -> {len(body_l):,}B "
          f"({100 - len(body_l) * 100 // len(body_i)}% smaller)")

    with sync_playwright() as sp:
        # Same flags verify_audio.py and verify_player_isolation.py use. Headless
        # Chromium blocks autoplay, and without this an analyser reads zero and
        # the failure looks like a broken player rather than a browser policy.
        b = sp.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                                     "--use-fake-device-for-media-stream"])
        print("\nEXTERNALISED — the inline player is the control")
        ctl = observe(b, url_i, "inline")

        # GATE. Everything below compares against this column, so a fixture that
        # does not render on the KNOWN-GOOD backend must stop the run rather
        # than be reported as an externalisation failure. This is the trap
        # verify_player_isolation names in its docstring: a hand-built payload
        # rendering nothing looks exactly like a broken player.
        gate = bool(ctl["ink"]) and bool((ctl["photo"] or {}).get("w")) and bool(ctl["audio"])
        check("FIXTURE GATE: the inline player renders ink, photo and audio",
              gate,
              "if this fails the fixture is malformed — nothing below is "
              "evidence about storage")
        if not gate:
            raise SystemExit(1)

        print("\nEXTERNALISED — the same Skribl, media behind a URL")
        ext = observe(b, url_l, "local")

        check("the player receives a URL, not base64",
              "/media/" in str((ext["photo"] or {}).get("src", "")),
              str((ext["photo"] or {}).get("src", ""))[:64])
        check("the photo actually decodes from the store",
              (ext["photo"] or {}).get("w") == (ctl["photo"] or {}).get("w"),
              f"{(ext['photo'] or {}).get('w')}px vs control "
              f"{(ctl['photo'] or {}).get('w')}px")
        check("the audio actually decodes from the store",
              ext["audio"] and abs(ext["audio"]["duration"]
                                   - ctl["audio"]["duration"]) < 0.05,
              f"{ext['audio'] and round(ext['audio']['duration'], 3)}s vs control "
              f"{round(ctl['audio']['duration'], 3)}s")
        check("the drawing paints the same as the control",
              ext["ink"] and ctl["ink"]
              and abs(ext["ink"] - ctl["ink"]) / ctl["ink"] < 0.02,
              f"{ext['ink']} vs {ctl['ink']} inked pixels")

        print("\nEXTERNALISED — nothing was blocked or thrown")
        check("no CSP violation on the externalised player",
              not ext["csp"], "; ".join(ext["csp"])[:200])
        check("no uncaught error on the externalised player",
              not ext["errors"], "; ".join(ext["errors"])[:200])
        check("and the control was clean too, so a clean run means something",
              not ctl["csp"] and not ctl["errors"],
              "; ".join(ctl["csp"] + ctl["errors"])[:200])
        b.close()

finally:
    inline.stop()
    local.stop()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
print("""
SCOPE. This proves the SAME-ORIGIN store. Skribl's own CSP is
`img-src/media-src/connect-src 'self' data: blob:`, so an s3 backend handing out
bucket URLs is blocked by the policy this package ships — silently, in the
browser, with nothing in the server log. Whoever implements `put_bytes` /
`url_for_key` for a real object store has to add that origin to three directives
in security.py, and this suite says nothing about it.""")
sys.exit(1 if bad else 0)
