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

# v224 merged Image and Music into ONE #mediaOpenBtn on both surfaces, opening a
# router drawer whose rows open the real photo/music panels. Reaching a media
# drawer is two taps now, and the same two on Pad and Flip.
def open_media(pg, which, settle=350):
    """which: 'photo' or 'music'."""
    pg.click("#mediaOpenBtn")
    pg.wait_for_timeout(200)
    pg.click("#mediaAddImage" if which == "photo" else "#mediaAddMusic")
    pg.wait_for_timeout(settle)


# The old single button TOGGLED, so the same click opened and closed. The router
# does not: clicking #mediaOpenBtn while a panel is open opens the ROUTER, which
# then sits over the canvas -- which is exactly how the first pass at this edit
# broke, timing out on #recordBtn with a drawer covering it. Closing is its own
# operation now, and it says so.
def close_media(pg, settle=250):
    pg.evaluate("() => { for (const id of ['photoPanel','musicPanel','mediaPanel']) {"
                " const p = document.getElementById(id); if (p) p.hidden = true; } }")
    pg.wait_for_timeout(settle)



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
    open_media(pg, "music")
    pg.wait_for_timeout(300)
    pg.set_input_files("#musicInput",
                       {"name": "t.wav", "mimeType": "audio/wav", "buffer": audio})
    pg.wait_for_timeout(3000)
    state = pg.evaluate("() => ({trimStart, trimEnd, dur: audioDuration})")
    close_media(pg, settle=400)
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

# ---- v211: v210 review F1 + H1 — a suspended context whose resume() NEVER
# settles. The reviewer's exact counterexample. On the broken Flip, a source
# was constructed and start()ed on the still-suspended context and the
# function returned true, suppressing the native fallback. Now: no source
# while suspended, and native <audio> is asked to play within the 600ms
# unlock timeout. Same test on the shared player (H1) and Pad (parity).
HANG = """
  const AC = window.AudioContext || window.webkitAudioContext;
  window.__ev = [];
  Object.defineProperty(AC.prototype, 'state', { configurable: true, get() { return 'suspended'; } });
  AC.prototype.resume = function () { window.__ev.push('resume'); return new Promise(() => {}); };   // never settles
  const cbs = AC.prototype.createBufferSource;
  AC.prototype.createBufferSource = function () { window.__ev.push('createBufferSource'); return cbs.apply(this, arguments); };
  const st = AudioBufferSourceNode.prototype.start;
  AudioBufferSourceNode.prototype.start = function () { window.__ev.push('start'); return st.apply(this, arguments); };
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () { window.__ev.push('native-play'); return play.apply(this, arguments); };
"""

with sync_playwright() as browser_ctx:
    b = browser_ctx.chromium.launch()

    # Flip (F1): load music, press Preview Loop under a hung unlock.
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.add_init_script(HANG)
    pg.goto(BASE + "/flip", wait_until="load"); pg.wait_for_timeout(700)
    open_media(pg, "music", settle=300)
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD}); pg.wait_for_timeout(2500)
    pg.evaluate("() => { window.__ev = []; document.getElementById('previewLoopBtn').click(); }")
    pg.wait_for_timeout(1200)
    ev = pg.evaluate("() => window.__ev")
    check("F1 Flip: resume() was asked for", "resume" in ev, str(ev))
    check("F1 Flip: NO source constructed while the context stays suspended",
          "createBufferSource" not in ev and "start" not in ev, str(ev))
    check("F1 Flip: native <audio> was handed the loop within the unlock timeout",
          "native-play" in ev, str(ev))
    pg.close()

    # Pad (parity): same, Preview Loop.
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.add_init_script(HANG)
    pg.goto(BASE + "/", wait_until="load"); pg.wait_for_timeout(700)
    open_media(pg, "music", settle=300)
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD}); pg.wait_for_timeout(2500)
    pg.evaluate("() => { window.__ev = []; document.getElementById('previewLoopBtn').click(); }")
    pg.wait_for_timeout(1200)
    ev = pg.evaluate("() => window.__ev")
    check("F1 Pad: no source while suspended", "createBufferSource" not in ev and "start" not in ev, str(ev))
    check("F1 Pad: native fallback taken", "native-play" in ev, str(ev))
    pg.close()

    # Shared player (H1): a posted skribl with music, Play under a hung unlock.
    # The drawing must OUTLAST the 600ms unlock timeout: on a 400ms stroke the
    # replay ended (audioPause -> paStop) before the fallback could fire, and
    # the fallback correctly refused to start music after the end — a fixture
    # trap, caught while building this. 3s of drawing here.
    import base64 as _b64
    long_frame = {"strokes": [{"x": 20 + i * 8, "y": 40 + (i % 7) * 20, "t": i * 150, "color": "#ffffff", "size": 4} for i in range(21)],
                  "strokeGroups": [21], "background": {"color": "#101418"},
                  "music": {"data": "data:audio/wav;base64," + _b64.b64encode(AUD).decode(),
                            "name": "h1.wav", "trimStart": 0, "trimEnd": 20}}
    _req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps({"frames": [long_frame]}).encode(),
                                  headers={"Content-Type": "application/json"})
    long_id = json.loads(urllib.request.urlopen(_req).read())["id"]
    pg = b.new_page(viewport={"width": 390, "height": 860})
    pg.add_init_script(HANG)
    pg.goto(f"{BASE}/s/{long_id}", wait_until="load"); pg.wait_for_timeout(2500)
    pg.evaluate("() => { window.__ev = []; }")
    pg.click("#playerPlayBtn"); pg.wait_for_timeout(1500)
    ev = pg.evaluate("() => window.__ev")
    check("H1 player: no source while suspended", "createBufferSource" not in ev and "start" not in ev, str(ev))
    check("H1 player: native <audio> handed the loop instead of going silent", "native-play" in ev, str(ev))
    pg.close()
    b.close()

# ---- v211: v210 review F2 — the crop/decode readiness race, both editors.
# mediaBusy is cleared by the FileReader; decodeAudioData is a separate
# promise. Hold the decode UNRESOLVED, get the editor to the point where the
# post button is enabled, submit, THEN release the decode, and inspect the
# posted WAV. Before the fix: currentAudioBuffer was null at submit, the crop
# silently skipped, and the full 30s shipped. After: submit awaits the
# retained decode and the 20s loop ships. Measured from the WAV header, never
# from trimEnd (an uncropped payload carries the authored trim too).
HOLD_DECODE = """
  const AC = window.AudioContext || window.webkitAudioContext;
  const real = AC.prototype.decodeAudioData;
  window.__releaseDecode = null;
  AC.prototype.decodeAudioData = function (buf) {
    const ctx = this;
    return new Promise((res, rej) => {
      window.__releaseDecode = () => real.call(ctx, buf).then(res, rej);
    });
  };
"""

def post_under_held_decode(pg, editor):
    # Both editors take the same route now -- the merged control is shared, so
    # the branch this used to need is gone.
    open_media(pg, "music", settle=300)
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
    pg.wait_for_timeout(2500)          # FileReader done; decode HELD
    held = pg.evaluate("() => ({busy: (typeof mediaBusy!=='undefined')?mediaBusy:0, buf: !!(typeof currentAudioBuffer!=='undefined' && currentAudioBuffer), rel: !!window.__releaseDecode})")
    check(f"F2 {editor} setup: media read complete but decode still held (the race window)",
          held["busy"] == 0 and not held["buf"] and held["rel"], str(held))
    if editor == "pad":
        close_media(pg, settle=300)
        box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return {x: r.x, y: r.y}; }")
        pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down(); pg.mouse.move(box["x"] + 300, box["y"] + 200, steps=10); pg.mouse.up()
        pg.wait_for_timeout(400); pg.click("#recordBtn"); pg.wait_for_timeout(800)
        pg.click("#postBtn"); pg.wait_for_timeout(500)
        pg.fill("#postTitleInput", "f2 race")
        pg.click("#postSubmitBtn")
    else:
        close_media(pg, settle=200)
        box = pg.evaluate("() => { const r = document.getElementById('pad').getBoundingClientRect(); return {x: r.x, y: r.y}; }")
        pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down(); pg.mouse.move(box["x"] + 300, box["y"] + 200, steps=10); pg.mouse.up()
        pg.wait_for_timeout(400)
        pg.click("#postBtn"); pg.wait_for_timeout(500)
        # Flip's share sheet has its own ids
        pg.fill("#flipShareTitle", "f2 race")
        pg.click("#flipShareSubmit")
    pg.wait_for_timeout(600)           # submit is now waiting on the decode
    pg.evaluate("() => { if (window.__releaseDecode) window.__releaseDecode(); }")
    pg.wait_for_timeout(5000)
    if editor == "pad":
        return pg.evaluate("() => (window.SkriblPosted && SkriblPosted.list && SkriblPosted.list()[0] || {}).id || null")
    url = pg.evaluate("() => { const u = document.getElementById('flipShareUrl'); return u ? (u.value || u.textContent || u.href || '') : ''; }")
    return url.rstrip('/').split('/')[-1] if url else None


with sync_playwright() as browser_ctx:
    b = browser_ctx.chromium.launch()
    for editor, url in (("pad", "/"), ("flip", "/flip")):
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.add_init_script(HOLD_DECODE)
        pg.goto(BASE + url, wait_until="load"); pg.wait_for_timeout(700)
        rid = post_under_held_decode(pg, editor)
        pg.close()
        check(f"F2 {editor}: the post went through", bool(rid), str(rid))
        if not rid:
            continue
        env = json.loads(urllib.request.urlopen(f"{BASE}/api/skribls/{rid}").read())
        fm = ((env.get("skribl") or {}).get("frames") or [{}])[0].get("music") or {}
        raw = fm.get("data") or ""
        secs = None
        if raw.startswith("data:"):
            import base64 as _b64
            secs = wav_duration(_b64.b64decode(raw.split(",", 1)[1]))
        check(f"F2 {editor}: posted media is the {LOOP_SECONDS:.0f}s LOOP even though decode was still pending at submit "
              f"— submit awaited it (WAV header, not trimEnd)",
              secs is not None and abs(secs - LOOP_SECONDS) < 1.0,
              f"posted media {secs}s (source {SRC_SECONDS}s)")
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
