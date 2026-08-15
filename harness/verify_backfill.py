"""Posts written while the store was inline — can they be converted afterwards?

Flipping `SKRIBL_MEDIA_BACKEND` changes what NEW posts do and nothing else.
Every row already in the table keeps its base64 inside `payload_json`, which is
the row size the change exists to fix, so without a backfill the saving applies
only to posts nobody has made yet. A mixed table is correct — `verify_storage.py`
asserts inline posts keep working — but correct is not reclaimed.

This drives `storage.backfill_media` over a database that was genuinely written
by the inline backend, not by a fixture pretending to be one: phase 1 boots a
real inline instance and posts through the API, and phases 2 and 3 open the SAME
sqlite file with an externalising store. If the conversion only works on
payloads this file authored, it proves nothing about the table you actually have.

THE ASSERTIONS THAT MATTER MOST ARE THE NEGATIVE ONES:

  * a dry run must write NO BYTES. It is rehearsed on a table holding real
    media, and a rehearsal that fills a disk is not a rehearsal. This is easy to
    get wrong, because the obvious implementation calls externalise_payload and
    throws the result away — which has already stored everything.
  * a second run must be a no-op. It WILL be interrupted on a large table, so
    resuming has to be safe; an association re-inserted over the unique index
    would abort a batch that had otherwise succeeded.
  * the player must still render the converted post. A backfill that produces
    small rows and a blank shared link has made things worse, and `verify_storage`
    would not notice because it never opens a browser.
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
sys.path.insert(0, str(ROOT))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# --- fixture (same shape as verify_externalised.py) --------------------------

def wav_bytes(seconds=6, rate=44100, freq=220):
    buf = bytearray()
    for i in range(seconds * rate):
        v = int(18000 * math.sin(2 * math.pi * freq * i / rate))
        buf += struct.pack("<hh", v, v)
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(out.name, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(bytes(buf))
    return pathlib.Path(out.name).read_bytes()


def png_bytes(w=320, h=200):
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        for x in range(w):
            rows += bytes((x * 255 // w, y * 255 // h, 128))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + chunk(b"IEND", b""))


WAV, PNG = wav_bytes(), png_bytes()
WAV_URL = "data:audio/wav;base64," + base64.b64encode(WAV).decode()
PNG_URL = "data:image/png;base64," + base64.b64encode(PNG).decode()


def spiral():
    pts, n = [], 400
    for i in range(n):
        a, r = (i / n) * math.pi * 6, 20 + (i / n) * 240
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7,
                    "color": "#ff5ea8", "size": 8, "t": int((i / n) * 3000),
                    "erase": False, "start": i == 0})
    return pts, [n]


PTS, GROUPS = spiral()


def payload(title):
    return {"title": title, "visibility": "public", "schemaVersion": 2,
            "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": PTS, "strokeGroups": GROUPS,
                        "background": {"color": "#101418"},
                        "photo": {"data": PNG_URL, "name": "p.png",
                                  "fit": "cover", "opacity": 1, "blur": 0,
                                  "offset": {"x": 0.5, "y": 0.5}, "zoom": 1},
                        "music": {"data": WAV_URL, "name": "m.wav",
                                  "trimStart": 0, "trimEnd": 6}}]}


DB_DIR = tempfile.mkdtemp()
DB_URL = f"sqlite:///{DB_DIR}/backfill.db"
MEDIA_ROOT = tempfile.mkdtemp()
PORT = 5014
BASE = f"http://127.0.0.1:{PORT}"


def env_for(backend):
    return dict(os.environ, SKRIBL_MEDIA_BACKEND=backend,
                SKRIBL_MEDIA_ROOT=MEDIA_ROOT, DATABASE_URL=DB_URL,
                SKRIBL_RATE_MAX_POSTS="100000",
                SKRIBL_RATE_MAX_ATTEMPTS="100000",
                SECRET_KEY="harness-backfill")


def boot(backend):
    subprocess.run([sys.executable, "-c",
                    "from app import app, db; app.app_context().push(); db.create_all()"],
                   cwd=ROOT, env=env_for(backend), check=True, capture_output=True)
    p = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                          "--port", str(PORT), "--no-reload"],
                         cwd=ROOT, env=env_for(backend),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 25
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", PORT), 0.5):
                return p
        except OSError:
            time.sleep(0.3)
    p.kill()
    return None


def stop(p):
    if not p:
        return
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()


def api_post(body):
    req = urllib.request.Request(BASE + "/api/skribls", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def api_get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def stored_files():
    n = 0
    for _sub, _dirs, files in os.walk(MEDIA_ROOT):
        n += len([f for f in files if not f.endswith(".part")])
    return n


INK = """() => {
  const c = document.getElementById('canvas');
  if (!c) return null;
  let ink = 0;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) ink++;
  return ink;
}"""
PHOTO = """() => { try { if (typeof photoBgImg === 'undefined' || !photoBgImg) return null;
  return {src: String(photoBgImg.src).slice(0,64), w: photoBgImg.naturalWidth}; }
  catch (e) { return null; } }"""
AUDIO = """() => { try { if (typeof currentAudioBuffer === 'undefined' || !currentAudioBuffer) return null;
  return {duration: currentAudioBuffer.duration}; } catch (e) { return null; } }"""

proc = None
try:
    # ---- phase 1: a table written by the real inline backend ---------------
    print("\nBACKFILL — a database written while the store was inline")
    proc = boot("inline")
    if not proc:
        print(f"SKIP: instance did not start on port {PORT}.")
        sys.exit(0)
    made = []
    for i in range(3):
        st, body = api_post(payload(f"legacy {i}"))
        if st == 201:
            made.append(body)
    check("three posts were created by the inline backend", len(made) == 3,
          f"{len(made)} of 3")
    st, before = api_get(f"/api/skribls/{made[0]['id']}")
    check("their payloads carry the media inline", len(before) > len(WAV),
          f"{len(before):,}B payload vs {len(WAV):,}B of audio")
    check("and nothing was written to the store, because there was none",
          stored_files() == 0, f"{stored_files()} files")
    stop(proc); proc = None

    # ---- phase 2: convert them in process -----------------------------------
    print("\nBACKFILL — the dry run counts without writing")
    os.environ.update(env_for("local"))
    from app import create_app                       # noqa: E402
    import skribl.storage as storage                 # noqa: E402
    from skribl.models import SkriblPost, SkriblPostMedia, session  # noqa: E402
    from skribl.validation import _iter_media_items  # noqa: E402
    from flask import url_for                        # noqa: E402

    app = create_app()
    with app.test_request_context():
        store = storage.LocalDiskStore(
            MEDIA_ROOT, lambda key: url_for("skribl.media", key=key))

        rehearsal = storage.backfill_media(store, session, _iter_media_items)
        check("the dry run finds every post holding inline media",
              rehearsal["converted"] == 3, str(rehearsal["converted"]))
        check("it sizes the base64 that would leave",
              rehearsal["inline_bytes"] > 3 * len(WAV_URL) * 0.9,
              f"{rehearsal['inline_bytes']:,}B across 3 posts")
        check("A DRY RUN WRITES NOTHING TO THE STORE", stored_files() == 0,
              f"{stored_files()} files — a rehearsal that fills a disk is not one")
        check("and it says it was a rehearsal", rehearsal["dry_run"] is True)

        print("\nBACKFILL — the real run converts them")
        real = storage.backfill_media(store, session, _iter_media_items,
                                      dry_run=False)
        check("it reports the same conversion count as the rehearsal",
              real["converted"] == rehearsal["converted"],
              f"{real['converted']} vs {rehearsal['converted']}")
        # Content addressing: three identical fixtures are ONE wav + ONE png.
        check("identical media across three posts is stored once, not nine times",
              stored_files() == 2, f"{stored_files()} objects on disk")
        check("every converted post has its association rows",
              session().query(SkriblPostMedia).count() == 6,
              f"{session().query(SkriblPostMedia).count()} rows "
              "— 3 posts x 2 objects, and authorisation depends on them")
        rows = session().query(SkriblPost).all()
        still_inline = [p.public_id for p in rows
                        if any(storage.is_data_url(v) for v, _k, _c, _l
                               in _iter_media_items(p.payload_json or {}))]
        check("no payload still carries a data URL", not still_inline,
              ", ".join(still_inline))

        print("\nBACKFILL — running it again is a no-op")
        # THE PAYLOAD IS THE PROGRESS MARKER. There is no separate bookkeeping,
        # so this asserts the actual mechanism: a converted post has no data URL
        # left, externalise_payload finds nothing to replace, and the post is
        # skipped — which is also what stops a second set of association rows
        # being inserted against the unique index. Mutation-tested by removing
        # the skip, which turns this section into an IntegrityError.
        again = storage.backfill_media(store, session, _iter_media_items,
                                       dry_run=False)
        check("a resumed run scans the converted posts and converts none",
              again["converted"] == 0 and again["scanned"] == 3,
              f"scanned {again['scanned']}, converted {again['converted']}")
        check("so no second association is inserted against the unique index",
              session().query(SkriblPostMedia).count() == 6,
              f"{session().query(SkriblPostMedia).count()} rows")
        check("and resuming from a recorded last_id skips them entirely",
              storage.backfill_media(store, session, _iter_media_items,
                                     after_id=again["last_id"],
                                     dry_run=False)["scanned"] == 0,
              f"resume point {again['last_id']}")

        print("\nBACKFILL — `limit` caps scanned posts EXACTLY")
        # limit used to be checked only after a whole batch committed, so
        # limit=1 with the default batch scanned all three posts on the run
        # where caution was the point.
        capped = storage.backfill_media(store, session, _iter_media_items,
                                        batch=100, limit=1)
        check("limit=1 scans exactly one post even with batch=100",
              capped["scanned"] == 1, f"scanned {capped['scanned']}")
        check("limit=0 scans nothing",
              storage.backfill_media(store, session, _iter_media_items,
                                     batch=100, limit=0)["scanned"] == 0)

        print("\nBACKFILL — it refuses a store that cannot externalise")
        try:
            storage.backfill_media(storage.InlineStore(), session,
                                   _iter_media_items)
            check("an inline store is refused, not reported as zero work",
                  False, "it returned instead of raising")
        except ValueError as e:
            check("an inline store is refused, not reported as zero work",
                  "externalising" in str(e), str(e)[:80])

    # ---- phase 3: the converted post still plays ---------------------------
    print("\nBACKFILL — a converted post is still a working shared link")
    proc = boot("local")
    if not proc:
        print(f"SKIP: local instance did not restart on port {PORT}.")
        sys.exit(0)
    st, after = api_get(f"/api/skribls/{made[0]['id']}")
    check("the converted post reads back", st == 200, str(st))
    check("its payload lost the media it used to carry",
          len(after) < len(before) / 10,
          f"{len(before):,} -> {len(after):,}B "
          f"({100 - len(after) * 100 // len(before)}% smaller)")

    with sync_playwright() as sp:
        b = sp.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                                     "--use-fake-device-for-media-stream"])
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.add_init_script("window.__csp=[];document.addEventListener("
                           "'securitypolicyviolation',e=>window.__csp.push("
                           "e.violatedDirective+' <- '+e.blockedURI));")
        pg.goto(BASE + made[0]["url"], wait_until="load")
        out = {}
        deadline = time.time() + 12
        while time.time() < deadline:
            out = {"ink": pg.evaluate(INK), "photo": pg.evaluate(PHOTO),
                   "audio": pg.evaluate(AUDIO)}
            if out["ink"] and (out["photo"] or {}).get("w") and out["audio"]:
                break
            pg.wait_for_timeout(400)
        csp = pg.evaluate("() => window.__csp || []")
        print(f"    converted: ink={out.get('ink')} photo={out.get('photo')} "
              f"audio={out.get('audio')} errors={len(errs)} csp={len(csp)}")
        check("the player paints the drawing", bool(out.get("ink")),
              f"{out.get('ink')} inked pixels")
        check("the photo now loads from the store, not from the payload",
              "/media/" in str((out.get("photo") or {}).get("src", ""))
              and (out.get("photo") or {}).get("w") == 320,
              str((out.get("photo") or {}).get("src", ""))[:64])
        check("the audio decodes from the store",
              bool(out.get("audio")) and abs(out["audio"]["duration"] - 6) < 0.05,
              str(out.get("audio")))
        check("no CSP violation and no uncaught error",
              not csp and not errs, "; ".join(csp + errs)[:200])
        b.close()

finally:
    stop(proc)

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
