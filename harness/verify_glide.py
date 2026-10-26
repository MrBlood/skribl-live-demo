#!/usr/bin/env python3
"""A replay glides (lib/holdtiming.js untie(); owner's iPhone, after v323:
"Why is it jumpy when drawing? ... The playback. It does it at 1x too").

A pointermove hands over every sample since the last one, and the editors
stamp the whole bundle with one time, so a replay put each bundle down at
once, held still, and jumped. Each row plays a stroke recorded in bundles and
watches it the way a person does, frame by frame:

  1. THE SHARED PLAYER at 1/4x and at 1x: the pen's nib moves on nearly every
     frame of the stroke, never holding still for more than two frames.
  2. THE PAD: a drawing recorded in bundles glides at 1/4x in its replay.
  3. A FLIP PAGE THAT DRAWS ITSELF reveals one point at a time.
  4. NOTHING IS LONGER OR SHORTER: the replay's length is what it was.
"""
import base64
import json
import math
import os
import struct
import sys
import urllib.error
import urllib.request

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)


def bundled(per, gap, groups):
    """One stroke of `groups` bundles, `per` points each sharing a time, the
    bundles `gap` ms apart: what a phone's pointermoves record."""
    pts = []
    for g in range(groups):
        for k in range(per):
            i = g * per + k
            pts.append({"x": 120 + i * 3, "y": 300 + (i % 40) * 2, "color": "#1f1b2e", "size": 6,
                        "t": g * gap, "start": i == 0})
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": "tight", "fps": None,
            "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}],
            "title": "glide"}


def tone(seconds, rate=8000):
    """A quiet sine, as a WAV: a song for a drawing to keep to."""
    pcm = b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 330 * i / rate))) for i in range(int(seconds * rate)))
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)


# A browser moves the audio clock a callback at a time; a phone's Bluetooth
# can make that 40ms. This makes it so here, and notes when a song starts.
COARSE = """(() => { const d = Object.getOwnPropertyDescriptor(BaseAudioContext.prototype, 'currentTime');
  Object.defineProperty(BaseAudioContext.prototype, 'currentTime', { configurable: true,
    get() { return Math.floor(d.get.call(this) / 0.04) * 0.04; } });
  const real = AudioBufferSourceNode.prototype.start;
  AudioBufferSourceNode.prototype.start = function () { if (this.loop) window.__song = performance.now(); return real.apply(this, arguments); }; })();"""


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


# The nib's place on every animation frame for `ms`, while it is showing.
WATCH = """(ms) => new Promise(res => { const out = [], t0 = performance.now();
  (function f() { const n = [...document.querySelectorAll('.player-nib')].find(e => !e.hidden && e.getClientRects().length);
    out.push(n ? n.style.left + ',' + n.style.top : null);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""


def glide(frames):
    """Of the frames with the nib up, the share on which it moved, and the
    longest run of frames it held still (the stroke's ends excluded)."""
    seen = [f for f in frames if f]
    if len(seen) < 10:
        return {"frames": len(seen), "moved": 0, "hold": 99}
    moved, run, hold = 0, 0, 0
    for a, b in zip(seen, seen[1:]):
        if a != b:
            moved += 1
            run = 0
        else:
            run += 1
            hold = max(hold, run)
    return {"frames": len(seen), "moved": round(moved / (len(seen) - 1), 2), "hold": hold}


def pick(pg, scope, r):
    pg.evaluate("""([s, r]) => { document.querySelector(s + ' .rl-speed').click();
        document.querySelector(s + ' .rl-chips [data-r="' + r + '"]').click(); }""", [scope, r])
    pg.wait_for_timeout(80)


with sync_playwright() as p:
    b = p.chromium.launch()

    # 1. the shared player
    print("\nTHE SHARED PLAYER")
    for label, per, gap, groups, rate, watch in (("1/4x", 4, 16, 40, 0.25, 1600), ("1x", 12, 48, 30, 1, 1100)):
        st, body = post(bundled(per, gap, groups))
        if st not in (200, 201) or not body.get("url"):
            check(f"[shared player] the {label} drawing posted", False, f"{st} {body}")
            continue
        pg = b.new_page(viewport={"width": 1100, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + body["url"], wait_until="load")
        pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
        pg.wait_for_timeout(300)
        if rate != 1:
            pick(pg, "#playerLine", rate)
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(120)
        g = glide(pg.evaluate(WATCH, watch))
        check(f"[shared player] a stroke recorded in bundles of {per}, {gap} ms apart, glides at {label}: "
              "the nib moves on nearly every frame, never still for more than two",
              g["moved"] >= 0.8 and g["hold"] <= 2, str(g))
        check(f"[shared player, {label}] no page errors", not errs, "; ".join(errs[:2]))
        pg.close()

    # 1b. ...WITH ITS SONG. While a song plays in step the drawing keeps to it
    # (lib/holdtiming.js songClock), and a drawing that read its time off the
    # audio clock moved only when the clock did: with 40ms steps, on four
    # frames in ten. It keeps the wall's pace and only waits for the song.
    music = bundled(12, 48, 60)
    music["frames"][0]["music"] = {"data": "data:audio/wav;base64," + base64.b64encode(tone(2)).decode(),
                                   "name": "tone.wav", "trimStart": 0, "trimEnd": 2}
    st, body = post(music)
    if st not in (200, 201) or not body.get("url"):
        check("[shared player] the drawing with its song posted", False, f"{st} {body}")
    else:
        pg = b.new_page(viewport={"width": 1100, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.add_init_script(COARSE)
        pg.goto(BASE + body["url"], wait_until="load")
        pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
        pg.wait_for_timeout(300)
        pg.click("#playerPlayBtn")
        pg.wait_for_function("() => window.__song", timeout=8000)
        pg.wait_for_timeout(250)   # the song heard, the start's wait over
        g = glide(pg.evaluate(WATCH, 1500))
        check("[shared player] ...and with its song playing, the song's clock moving in 40ms steps (a phone's "
              "Bluetooth): the nib still moves on nearly every frame, never still for more than two",
              g["moved"] >= 0.8 and g["hold"] <= 2, str(g))
        check("[shared player, with its song] no page errors", not errs, "; ".join(errs[:2]))
        pg.close()

    # 2. the Pad, with a real touch stroke the browser bundles
    print("\nTHE PAD")
    c = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.wait_for_timeout(900)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    # The drawing a phone records: bundles of points sharing one time. (A
    # touch sent from here arrives a sample at a time, so the browser never
    # bundles it; the Pad loads the bundled drawing as it would a draft.)
    pg.evaluate("(d) => loadSkribl(d)", bundled(4, 16, 40))
    pg.wait_for_timeout(500)
    rec = pg.evaluate("""() => { const s = strokes, n = s.length; let same = 0;
        for (let i = 1; i < n; i++) if (s[i].t === s[i - 1].t && !s[i].start) same++;
        // Past each stroke's first bundle, which has no moment before it.
        const tl = buildPlaybackTimeline(); let tied = 0, t0 = 0;
        for (let i = 1; i < tl.length; i++) { if (tl[i].start) t0 = tl[i].playT;
          if (tl[i].playT === tl[i - 1].playT && !tl[i].start && tl[i].playT !== t0) tied++; }
        return { n, same, tied, last: tl.length ? tl[tl.length - 1].playT : 0, dur: getPlaybackDuration() }; }""")
    check("[Pad] (setup) the drawing holds bundles: points sharing one time",
          rec["n"] > 40 and rec["same"] > rec["n"] / 3, str(rec))
    check("[Pad] its replay plays them one after another: past a stroke's first bundle, no two points at one moment",
          rec["tied"] == 0, str(rec))
    check("[Pad] ...and the replay is exactly as long as before (the bundles' last points stay put)",
          abs(rec["last"] - rec["dur"]) < 0.001, str(rec))
    if pg.evaluate("() => document.body.classList.contains('recording')"):
        pg.evaluate("() => document.getElementById('recordBtn').click()")
        pg.wait_for_timeout(400)
    pick(pg, "#padLine", 0.25)
    pg.click("#playBtn")
    pg.wait_for_timeout(120)
    g = glide(pg.evaluate(WATCH, 1500))
    check("[Pad] a drawing recorded in bundles glides at 1/4x: the nib moves on nearly every frame",
          g["moved"] >= 0.8 and g["hold"] <= 2, str(g))
    check("[Pad] no page errors", not errs, "; ".join(errs[:2]))
    c.close()

    # 3. Flip: a page that draws itself
    print("\nFLIP")
    pg = b.new_page()
    browsing.goto(pg, BASE, "/flip")
    pg.wait_for_timeout(600)
    steps = pg.evaluate("""() => { const H = window.SkriblHold, pts = [];
        for (let g = 0; g < 20; g++) for (let k = 0; k < 4; k++) pts.push({ x: g * 4 + k, y: 0, t: g * 16, start: !g && !k });
        const f = { draw: true, strokes: pts }, out = [];
        for (let q = 0; q <= 400; q++) out.push(H.dueCount(f, q / 400));
        // After the first bundle: a stroke's first points have no moment
        // before them to spread into, so they come together, as drawn.
        let jump = 0; for (let i = 1; i < out.length; i++) if (out[i - 1] >= 4) jump = Math.max(jump, out[i] - out[i - 1]);
        return { jump, end: out[out.length - 1], span: H.spanMs(f) }; }""")
    check("[Flip] a page that draws itself reveals its bundled points one at a time, not four at once (after the first)",
          steps["jump"] == 1 and steps["end"] == 80, str(steps))
    pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
