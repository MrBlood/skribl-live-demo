"""Loop-state ownership: the two bugs behind iPhone-silent shared links (v210).

BUG A — the player's loop bounds were installed only inside the <audio>
element's 'loadedmetadata' handler. trimEnd starts at 0; iOS defers media
loading until playback is requested, so on a shared link the event routinely
had not fired when the user tapped Play. buildLoopAudioBuffer() then saw a
zero-length window, returned null WITHOUT throwing, and no source was ever
constructed. Silent on iPhone, fine on desktop, invisible to the harness —
until the event was suppressed here, which reproduces it exactly.

BUG B — the post-time loop crop guarded on payload.music, a field
serializeSkribl() stopped producing at the v2 frame migration (media lives in
frames[0].music). The branch was dead on every v2 Pad post, so shared posts
carried the whole song. The server had been migrated for frames; this client
consumer had not.

Both are pinned behaviourally. Bug A suppresses the event PERMANENTLY rather
than delaying it, because the claim is that the event is not load-bearing, not
that it is merely slow.
"""
import json
import math
import os
import struct
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
SRC_SECONDS = 30.0
LOOP_SECONDS = 20.0          # the editor's default trim window
RATE = 22050

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def wav_bytes(seconds, rate=RATE):
    n = int(seconds * rate)
    frames = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate)))
                      for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(frames)) + frames)


def wav_duration(raw):
    """Seconds of PCM in a RIFF/WAVE byte string, from its own header.

    WHY THIS AND NOT trimEnd. An UNCROPPED payload carries the authored trim
    too, so `trimEnd == 20` is true whether or not the crop ran — asserting it
    proves nothing and passed happily against the broken build. Only the
    generated media's own length distinguishes a baked loop from the full
    source. Do not "simplify" this back into a metadata assertion.
    """
    if raw[:4] != b"RIFF":
        return None
    pos, channels, rate, bits, data = 12, None, None, None, None
    while pos + 8 <= len(raw):
        cid = raw[pos:pos + 4]
        size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            channels, rate = struct.unpack("<HI", body[2:8])
            bits = struct.unpack("<H", body[14:16])[0]
        elif cid == b"data":
            data = size
        pos += 8 + size + (size & 1)
    if not (channels and rate and bits and data):
        return None
    return data / float(rate * channels * (bits // 8))


def post_with_music(pg, audio):
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(700)
    pg.click("#musicOpenBtn")
    pg.wait_for_timeout(300)
    pg.set_input_files("#musicInput",
                       {"name": "t.wav", "mimeType": "audio/wav", "buffer": audio})
    pg.wait_for_timeout(3000)
    state = pg.evaluate("() => ({trimStart, trimEnd, dur: audioDuration})")
    pg.evaluate("() => { const c = document.getElementById('musicOpenBtn'); if (c) c.click(); }")
    pg.wait_for_timeout(400)
    box = pg.evaluate("() => { const r = document.getElementById('canvas')"
                      ".getBoundingClientRect(); return {x: r.x, y: r.y}; }")
    pg.mouse.move(box["x"] + 80, box["y"] + 80)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 300, box["y"] + 200, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(800)
    pg.click("#postBtn")
    pg.wait_for_timeout(500)
    pg.fill("#postTitleInput", "audiostate")
    pg.click("#postSubmitBtn")
    pg.wait_for_timeout(5000)
    pid = pg.evaluate("() => (window.SkriblPosted && SkriblPosted.list "
                      "&& SkriblPosted.list()[0] || {}).id || null")
    return pid, state


SUPPRESS = """
  // PERMANENT suppression, not a delay: the claim under test is that
  // loadedmetadata is not load-bearing for playback at all.
  const proto = HTMLMediaElement.prototype;
  const add = proto.addEventListener;
  proto.addEventListener = function (type) {
    if (type === 'loadedmetadata') { window.__suppressed = (window.__suppressed || 0) + 1; return; }
    return add.apply(this, arguments);
  };
  window.__srcCreated = 0;
  const AC = window.AudioContext || window.webkitAudioContext;
  const cbs = AC.prototype.createBufferSource;
  AC.prototype.createBufferSource = function () {
    window.__srcCreated++;
    return cbs.apply(this, arguments);
  };
"""

COUNT_ONLY = """
  window.__srcCreated = 0;
  const AC = window.AudioContext || window.webkitAudioContext;
  const cbs = AC.prototype.createBufferSource;
  AC.prototype.createBufferSource = function () {
    window.__srcCreated++;
    return cbs.apply(this, arguments);
  };
"""

AUD = wav_bytes(SRC_SECONDS)

with sync_playwright() as browser_ctx:
    b = browser_ctx.chromium.launch()

    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pid, editor_state = post_with_music(pg, AUD)
    pg.close()
    check("a Skribl with music posts", bool(pid), str(pid))
    check("the editor's default loop window is a subset of the source",
          editor_state["trimEnd"] < editor_state["dur"],
          f"trim {editor_state['trimStart']}..{editor_state['trimEnd']} of {editor_state['dur']}s")

    envelope = json.loads(urllib.request.urlopen(f"{BASE}/api/skribls/{pid}").read())
    sk = envelope.get("skribl") or {}
    frames = sk.get("frames") or []
    fmusic = (frames[0].get("music") if frames else None) or {}
    check("v2: current-frame media lives in frames[0].music, not top level",
          bool(fmusic) and not sk.get("music"), str(sorted(fmusic)))

    raw = fmusic.get("data") or ""
    payload_seconds = None
    if raw.startswith("data:"):
        import base64
        payload_seconds = wav_duration(base64.b64decode(raw.split(",", 1)[1]))

    # ---- BUG B ----------------------------------------------------------
    check("BUG B: the POSTED MEDIA is the baked loop, measured from its own "
          "WAV header — not inferred from trimEnd, which an uncropped payload "
          "carries identically",
          payload_seconds is not None
          and abs(payload_seconds - LOOP_SECONDS) < 1.0,
          f"posted media is {payload_seconds:.2f}s; loop {LOOP_SECONDS}s, "
          f"source {SRC_SECONDS}s")
    check("BUG B: and it is not the full source",
          payload_seconds is not None
          and abs(payload_seconds - SRC_SECONDS) > 1.0,
          f"{payload_seconds}s")
    check("BUG B: the baked clip's trims collapse to 0..len",
          fmusic.get("trimStart") == 0
          and abs((fmusic.get("trimEnd") or 0) - (payload_seconds or 0)) < 0.5,
          f"trims {fmusic.get('trimStart')}..{fmusic.get('trimEnd')}")

    # ---- BUG A ----------------------------------------------------------
    pg = b.new_page(viewport={"width": 390, "height": 860})
    pg.add_init_script(SUPPRESS)
    pg.goto(f"{BASE}/s/{pid}", wait_until="load")
    pg.wait_for_timeout(2500)
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(2500)
    got = pg.evaluate("() => ({suppressed: window.__suppressed || 0, "
                      "srcCreated: window.__srcCreated || 0})")
    pg.close()
    check("BUG A setup: loadedmetadata really was suppressed",
          got["suppressed"] > 0, str(got))
    check("BUG A: playback constructs a source with loadedmetadata suppressed "
          "FOREVER — the event is not load-bearing",
          got["srcCreated"] > 0,
          f"{got['srcCreated']} sources — zero means the loop window was never installed")

    pg = b.new_page(viewport={"width": 390, "height": 860})
    pg.add_init_script(COUNT_ONLY)
    pg.goto(f"{BASE}/s/{pid}", wait_until="load")
    pg.wait_for_timeout(2500)
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(2500)
    normal = pg.evaluate("() => window.__srcCreated || 0")
    pg.close()
    check("CONTROL: the ordinary path still builds exactly one source",
          normal == 1, f"{normal} sources")

    # ---- BUG A, the invariant itself ---------------------------------------
    # A payload that OMITS trimEnd (legacy shape; the fixed crop always writes
    # it now, so this is posted straight through the API) with loadedmetadata
    # suppressed forever must still resolve trimEnd from the DECODED duration
    # and build a source. Pinning the value as well as the source construction
    # matters: without it a later change could make playback "work" only
    # because some unrelated fallback happened to mask invalid bounds.
    import base64
    # It needs SOMETHING to play: play() returns before touching audio when the
    # timeline is empty, so a strokeless fixture proves nothing about audio (a
    # first draft of this pin failed for exactly that reason and looked like a
    # real regression for ten minutes).
    legacy_frame = {"strokes": [{"x": 20, "y": 20, "t": 0, "color": "#ffffff", "size": 4},
                                {"x": 200, "y": 160, "t": 400, "color": "#ffffff", "size": 4}],
                    "strokeGroups": [2], "background": {"color": "#101418"},
                    "music": {"data": "data:audio/wav;base64," + base64.b64encode(AUD).decode(),
                              "name": "legacy.wav", "trimStart": 0}}   # no trimEnd
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps({"frames": [legacy_frame]}).encode(),
                                 headers={"Content-Type": "application/json"})
    legacy_id = json.loads(urllib.request.urlopen(req).read())["id"]
    pg = b.new_page(viewport={"width": 390, "height": 860})
    pg.add_init_script(SUPPRESS)
    pg.goto(f"{BASE}/s/{legacy_id}", wait_until="load")
    pg.wait_for_timeout(2500)
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(2500)
    inv = pg.evaluate("() => ({trimEnd, dur: audioDuration, srcCreated: window.__srcCreated || 0, "
                      "hasBuf: !!(typeof currentAudioBuffer !== 'undefined' && currentAudioBuffer)})")
    pg.close()
    check("INVARIANT setup: the buffer decoded", inv["hasBuf"], str(inv))
    check("INVARIANT: with trimEnd OMITTED and metadata suppressed, trimEnd == "
          "min(decoded duration, 20)",
          abs(inv["trimEnd"] - min(inv["dur"], 20)) < 0.01,
          f"trimEnd={inv['trimEnd']} decoded={inv['dur']}")
    check("INVARIANT: ...and a source is still constructed",
          inv["srcCreated"] > 0, f"{inv['srcCreated']} sources")

    b.close()

# Static guards on the ownership itself, so a later edit cannot quietly move
# the state back under the event.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
appjs = open(os.path.join(ROOT, "skribl", "static", "app.js")).read()
postjs = open(os.path.join(ROOT, "skribl", "static", "editor_post.js")).read()
# Comments EXPLAIN the old field by name, so the guard must read code only —
# the first version of this check failed against the fixed tree.
import re as _re
postcode = "\n".join(_re.sub(r"//.*$", "", ln) for ln in postjs.split("\n"))
check("BUG A: trims are installed synchronously, outside the media event",
      "trimEnd = data.music.trimEnd != null ? data.music.trimEnd : null;" in appjs,
      "the synchronous install is gone")
check("BUG A: the decoded buffer is the authoritative duration",
      "audioDuration = audioBuffer.duration;" in appjs
      and "if (trimEnd == null) trimEnd = Math.min(audioDuration, 20);" in appjs)
check("BUG B: posting locates media through the shared accessor",
      "currentFrameMedia(payload)" in postcode and "payload.music" not in postcode,
      "editor_post.js still reaches for a top-level field")
check("BUG B: a failed crop is reported, not swallowed",
      "loop crop failed" in postjs)

bad = [n for ok, n, _ in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} passed")
for n in bad:
    print(f"  FAILED: {n}")
sys.exit(1 if bad else 0)
