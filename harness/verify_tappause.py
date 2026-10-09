"""Tap to pause: a tap on an editor's canvas while its preview plays pauses it
where it is, and another tap carries on from there -- on the Pad's replay and on
Flip's flip, by real touches at 390 and by mouse clicks on a desk.

The owner: "tapping the screen while a flip/pad playing on creation canvas will
pause. With ability to resume with a tap.. but show icons right". Before this,
a tap on either canvas during a preview did nothing at all: both editors refuse
the canvas as a drawing surface while a preview runs, and Stop was the only
control.

WHAT IS ASKED, AND HOW IT IS READ
  * Paused is read off the preview itself, not a flag: the Pad's scrub bar and
    canvas stop changing, and Flip stays on its page well past that page's
    time.
  * The icon is read off the screen. Paused, the in-post player's round Play
    is PAINTED in the middle of the canvas: the white of its arrow is counted
    in a screenshot, centred on the canvas, and absent before the tap and
    after the resume. (It takes no pointer events, so elementFromPoint could
    never see it -- and a rect is not a paint.) Flip's corner badge reads the
    pause too: two bars where the play arrow was.
  * Carrying on is read as WHERE it carries on from: the Pad's bar picks up
    from its paused place, not from zero; Flip's page gives way after what was
    left of its time, not a whole page's; a drawing page's reveal goes on from
    the ink it had.
  * The music is read off the audio engine's own calls: the loop's source is
    stopped by the pause and started again by the resume, at the offset the
    music had reached -- measured from the stop and start calls' own times.
  * What is not a tap stays not one: a drag, two fingers. A paused canvas is
    still not a drawing surface. Stop while paused ends the preview and takes
    the round Play with it. A paused Flip scrubbed to another page stays paused
    there, and that page gets its whole time on resume.

The drawings keep their ink clear of the canvas's middle, so the only white
there is the arrow.
"""
import io
import math
import os
import struct
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

PHONE = dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
DESK = dict(viewport={"width": 1100, "height": 760}, device_scale_factor=1)
BARS = "❚❚"

# The loop's source, as the engine drives it: every start (with its offset) and
# stop, with the page's own clock.
AUDIO_SPY = """
  window.__aud = [];
  const st = AudioBufferSourceNode.prototype.start, sp = AudioBufferSourceNode.prototype.stop;
  AudioBufferSourceNode.prototype.start = function (when, offset) {
    window.__aud.push({ k: 'start', off: offset || 0, t: performance.now(), dur: this.buffer ? this.buffer.duration : 0 });
    return st.apply(this, arguments); };
  AudioBufferSourceNode.prototype.stop = function () {
    window.__aud.push({ k: 'stop', t: performance.now() }); return sp.apply(this, arguments); };
"""


def wav_bytes(seconds, rate=22050):
    n = int(seconds * rate)
    frames = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(frames)) + frames)


AUD = wav_bytes(3.0)


def fresh(b, route, kind=PHONE, spy=False):
    ctx = b.new_context(**kind)
    if spy:
        ctx.add_init_script(AUDIO_SPY)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, route)
    pg.wait_for_timeout(900)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    # How long the last press on the canvas lasted, by the events' own clock: a
    # drag can only prove the tap's distance rule if it was quick enough to be a
    # tap on time alone.
    pg.evaluate("""(sel) => { const el = document.querySelector(sel); window.__g = {};
        el.addEventListener('pointerdown', e => { window.__g.down = e.timeStamp; }, true);
        el.addEventListener('pointerup', e => { window.__g.up = e.timeStamp; }, true); }""",
                "#pad" if route == "/flip" else "#canvas")
    cdp = ctx.new_cdp_session(pg) if kind is PHONE else None
    return ctx, pg, cdp, errs


def press_ms(pg):
    return pg.evaluate("() => Math.round(window.__g.up - window.__g.down)")


def quick(pg):
    """The last press was a tap on time: only its distance can have kept it from being one."""
    return press_ms(pg) < pg.evaluate("() => window.SkriblTapPause ? window.SkriblTapPause.TAP_MS : 500")


def box(pg, sel):
    return pg.locator(sel).first.bounding_box()


def centre(pg, sel):
    r = box(pg, sel)
    return r["x"] + r["width"] / 2, r["y"] + r["height"] / 2


def finger(pg, cdp, path, step=16):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": path[0][0], "y": path[0][1]}]})
    for x, y in path[1:]:
        pg.wait_for_timeout(step)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
    pg.wait_for_timeout(step)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def flick(pg, cdp, x, y, dx, dy, n=3):
    """A quick drag, done well inside the time a tap has: only its distance
    makes it not one."""
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for k in range(1, n + 1):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + dx * k / n, "y": y + dy * k / n}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    # A quick swipe leaves the browser flinging, and a touch then only stops the
    # fling: measured, a tap on Flip's Play 700ms after a 60px swipe gave no
    # click, and 1500ms after, it did. The drag checks read their state after.
    pg.wait_for_timeout(1500)


def quick_drag(pg, sel, x, y, dx, dy):
    """A drag of pointer events fired at `sel` in one go, so it lasts about a
    millisecond: nothing but its distance keeps it from being a tap. For the
    Pad, whose replay keeps the page so busy that a touch sent from outside
    took up to 504ms to cross 60px -- at the edge of a tap's 500ms by time
    alone, which is no test of the distance rule."""
    pg.evaluate("""(o) => { const el = document.querySelector(o.sel);
        const ev = (type, x, y) => new PointerEvent(type, { pointerId: 77, pointerType: 'touch', isPrimary: true,
          clientX: x, clientY: y, button: type === 'pointermove' ? -1 : 0, buttons: type === 'pointerup' ? 0 : 1,
          bubbles: true, cancelable: true });
        el.dispatchEvent(ev('pointerdown', o.x, o.y));
        for (let k = 1; k <= 3; k++) el.dispatchEvent(ev('pointermove', o.x + o.dx * k / 3, o.y + o.dy * k / 3));
        el.dispatchEvent(ev('pointerup', o.x + o.dx, o.y + o.dy)); }""", {"sel": sel, "x": x, "y": y, "dx": dx, "dy": dy})


def tap(pg, cdp, x, y):
    if cdp:
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        pg.wait_for_timeout(60)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    else:
        pg.mouse.click(x, y)


def two_fingers(pg, cdp, x, y):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart",
                                          "touchPoints": [{"x": x - 30, "y": y, "id": 1}, {"x": x + 30, "y": y, "id": 2}]})
    pg.wait_for_timeout(60)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def arrow(pg, sel):
    """White of the round Play's arrow, painted, in an 84px square at the
    middle of `sel`: (count, centroid dx, centroid dy) from that middle."""
    cx, cy = centre(pg, sel)
    raw = pg.screenshot(clip={"x": cx - 42, "y": cy - 42, "width": 84, "height": 84})
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    px = im.load()
    pts = [(x, y) for y in range(h) for x in range(w) if min(px[x, y]) > 225]
    if not pts:
        return 0, None, None
    s = w / 84.0
    return (len(pts), round(sum(p[0] for p in pts) / len(pts) / s - 42, 1),
            round(sum(p[1] for p in pts) / len(pts) / s - 42, 1))


def painted_mid(a):
    n, dx, dy = a
    return n > 40 and abs(dx) <= 8 and abs(dy) <= 8


def glyph_display(pg):
    return pg.evaluate("() => { const g = document.querySelector('.tap-paused'); return g ? getComputedStyle(g).display : 'absent'; }")


# ------------------------------------------------------------------ the Pad
PAD = """() => ({ fill: parseFloat((document.getElementById('playScrubFill') || {style: {}}).style.width) || 0,
  replaying: document.body.classList.contains('replaying'), paused: document.body.classList.contains('playback-paused'),
  strokes: strokes.length })"""
CANVAS_SUM = """() => { const c = document.getElementById('canvas'), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0;
  for (let i = 0; i < d.length; i += 4 * 97) s = (s + d[i] * 3 + d[i + 1] * 5 + d[i + 2] * 7) % 1000003;
  return s; }"""


def pad_take(pg, cdp, n=6):
    """A take drawn by touch (or mouse), its ink kept to the left of the middle."""
    r = box(pg, "#canvas")
    for k in range(n):
        x0, y0 = r["x"] + r["width"] * (0.08 + 0.04 * k), r["y"] + r["height"] * 0.18
        path = [(x0 + j * 1.5, y0 + j * r["height"] * 0.025) for j in range(26)]
        if cdp:
            finger(pg, cdp, path)
        else:
            pg.mouse.move(*path[0]); pg.mouse.down()
            for p in path[1:]:
                pg.mouse.move(*p); pg.wait_for_timeout(16)
            pg.mouse.up()
        pg.wait_for_timeout(120)
    pg.wait_for_function("() => recording === true")
    pg.evaluate("() => document.getElementById('recordBtn').click()")
    pg.wait_for_function("() => recording === false")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { for (const t of document.querySelectorAll('.toast')) t.hidden = true; }")


def pad_play(pg, cdp):
    x, y = centre(pg, "#playBtn")
    tap(pg, cdp, x, y)
    pg.wait_for_function("() => document.body.classList.contains('replaying')")


def pad_fresh_play(pg, cdp):
    """Stop whatever is playing, then Play: the next check starts from a
    replay that is running and not paused, whatever the last one left."""
    if pg.evaluate(PAD)["replaying"]:
        tap(pg, cdp, *centre(pg, "#playBtn"))
        pg.wait_for_function("() => !document.body.classList.contains('replaying')")
        pg.wait_for_timeout(200)
    pad_play(pg, cdp)
    pg.wait_for_timeout(300)


def pad_suite(b):
    print("\nPAD -- by touch at 390")
    ctx, pg, cdp, errs = fresh(b, "/skribl-pad")
    pad_take(pg, cdp)
    cx, cy = centre(pg, "#canvas")
    pad_play(pg, cdp)
    pg.wait_for_timeout(700)
    before = arrow(pg, ".canvas-wrap")
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(150)
    s1, c1 = pg.evaluate(PAD), pg.evaluate(CANVAS_SUM)
    pg.wait_for_timeout(800)
    s2, c2 = pg.evaluate(PAD), pg.evaluate(CANVAS_SUM)
    check("Pad: a tap on the canvas pauses the replay where it is",
          s1["paused"] and s2["replaying"] and s1["fill"] > 0 and s1["fill"] == s2["fill"] and c1 == c2,
          f"{s1} -> {s2}, canvas {'same' if c1 == c2 else 'changed'}")
    during = arrow(pg, ".canvas-wrap")
    check("Pad: paused, the round Play is painted in the middle of the canvas, and was not before",
          painted_mid(during) and before[0] < 10, f"before {before}, paused {during}")
    r = box(pg, "#canvas")
    quick_drag(pg, "#canvas", r["x"] + r["width"] * 0.12, r["y"] + r["height"] * 0.7, 0, 60)
    pg.wait_for_timeout(150)
    s2b = pg.evaluate(PAD)
    check("Pad: paused, a drag on the canvas draws nothing and leaves it paused",
          s2b["strokes"] == s2["strokes"] and s2b["paused"] and quick(pg),
          f"{s2['strokes']} -> {s2b['strokes']} points, {s2b}, the drag took {press_ms(pg)}ms")
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(60)
    s3 = pg.evaluate(PAD)
    pg.wait_for_timeout(600)
    s4 = pg.evaluate(PAD)
    after = arrow(pg, ".canvas-wrap")
    check("Pad: a second tap carries the replay on from where it paused",
          not s3["paused"] and s3["fill"] >= s2["fill"] - 0.5 and (s4["fill"] > s3["fill"] + 1 or not s4["replaying"]),
          f"paused at {s2['fill']}%, {s3['fill']}% on resume, {s4['fill']}% later")
    check("...and the round Play is gone once it carries on", after[0] < 10, str(after))

    # Not taps, each from a fresh Play
    pad_fresh_play(pg, cdp)
    pg.wait_for_timeout(500)
    f0 = pg.evaluate(PAD)["fill"]
    quick_drag(pg, "#canvas", r["x"] + r["width"] * 0.1, r["y"] + r["height"] * 0.8, 60, 0)
    pg.wait_for_timeout(250)
    s5 = pg.evaluate(PAD)
    check("Pad: a drag across the canvas is not a tap: the replay plays on",
          not s5["paused"] and (s5["fill"] > f0 or not s5["replaying"]) and quick(pg),
          f"{f0}% -> {s5}, the drag took {press_ms(pg)}ms")
    pad_fresh_play(pg, cdp)
    two_fingers(pg, cdp, cx, cy)
    pg.wait_for_timeout(200)
    check("Pad: two fingers on the canvas are not a tap", not pg.evaluate(PAD)["paused"], str(pg.evaluate(PAD)))

    # Stop while paused
    pad_fresh_play(pg, cdp)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(150)
    was = pg.evaluate(PAD)
    tap(pg, cdp, *centre(pg, "#playBtn"))
    pg.wait_for_timeout(300)
    s6 = pg.evaluate(PAD)
    check("Pad: Stop while paused ends the replay, and the round Play goes with it",
          was["paused"] and not s6["replaying"] and not s6["paused"] and glyph_display(pg) == "none",
          f"{was} -> {s6}, glyph {glyph_display(pg)}")
    check("Pad: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nPAD -- the music")
    ctx, pg, cdp, errs = fresh(b, "/skribl-pad", spy=True)
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
    pg.wait_for_timeout(2500)
    pad_take(pg, cdp, n=8)
    music_checks(pg, cdp, "Pad", "#canvas", lambda: pad_play(pg, cdp))
    ctx.close()

    print("\nPAD -- by mouse on a desk")
    ctx, pg, cdp, errs = fresh(b, "/skribl-pad", kind=DESK)
    pad_take(pg, None)
    cx, cy = centre(pg, "#canvas")
    pad_play(pg, None)
    pg.wait_for_timeout(500)
    tap(pg, None, cx, cy)
    pg.wait_for_timeout(150)
    a = pg.evaluate(PAD)
    pg.wait_for_timeout(500)
    a2 = pg.evaluate(PAD)
    tap(pg, None, cx, cy)
    pg.wait_for_timeout(400)
    a3 = pg.evaluate(PAD)
    check("Pad (desk): a click on the canvas pauses the replay, and another carries it on",
          a["paused"] and a["fill"] == a2["fill"] and not a3["paused"] and (a3["fill"] > a2["fill"] or not a3["replaying"]),
          f"{a} -> {a2} -> {a3}")
    ctx.close()


def music_checks(pg, cdp, who, sel, play):
    cx, cy = centre(pg, sel)
    play()
    pg.wait_for_timeout(1300)
    tap(pg, cdp, cx, cy)
    t_pause = pg.evaluate("() => performance.now()")
    pg.wait_for_timeout(700)
    t_resume = pg.evaluate("() => performance.now()")
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(400)
    ev = pg.evaluate("() => window.__aud")
    starts = [e for e in ev if e["k"] == "start"]
    first = starts[0] if starts else None
    stop = next((e for e in ev if e["k"] == "stop" and first and e["t"] > first["t"] and e["t"] <= t_pause + 50), None)
    quiet = [e for e in ev if e["k"] == "start" and t_pause + 50 < e["t"] < t_resume]
    again = next((e for e in ev if e["k"] == "start" and e["t"] >= t_resume), None)
    want = ((stop["t"] - first["t"]) / 1000.0) % first["dur"] if (first and stop and first["dur"]) else None
    check(f"{who}: the music stops with the pause and starts again where it stopped",
          bool(first and stop and not quiet and again and want is not None
               and want > 0.3 and abs(again["off"] - want) < 0.15),
          f"first {first}, stop {stop}, during the pause {quiet}, resumed {again}, wanted offset {want}")


# ------------------------------------------------------------------ Flip
FLIP = """() => ({ idx, playing, paused: document.body.classList.contains('playback-paused'),
  badge: document.querySelector('.flip-live').textContent, points: frames[idx] ? frames[idx].strokes.length : 0,
  clock: parseFloat(document.getElementById('flipDuration').textContent) })"""
PAGES = """(o) => { const line = (x0, y0, t0) => { const pts = []; for (let j = 0; j < 14; j++)
    pts.push({ x: x0 + j * 2, y: y0 + j * 14, color: '#ffffff', size: 6, t: t0 + j * (o.span / 14), start: j === 0 }); return pts; };
  frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const l = line(CW * (0.1 + 0.05 * k), CH * 0.15, 0);
    f.strokes.push(...l); f.strokeGroups.push(l.length); if (o.draw && k === 0) f.draw = true; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); updateFlipEmptyHint(); }"""
INK = """() => { const c = document.getElementById('pad'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const g = [d[0], d[1], d[2]]; let n = 0;
  for (let i = 0; i < d.length; i += 4 * 3) if (Math.abs(d[i] - g[0]) + Math.abs(d[i + 1] - g[1]) + Math.abs(d[i + 2] - g[2]) > 90) n++;
  return n; }"""


def flip_setup(pg, n=4, fps=1, draw=False, span=60):
    pg.evaluate(PAGES, {"n": n, "fps": fps, "draw": draw, "span": span})


def flip_play(pg, cdp):
    tap(pg, cdp, *centre(pg, "#play"))
    pg.wait_for_function("() => playing === true")


def page_change(pg, timeout=2500):
    """ms until idx moves off the page it is on now (None if it does not)."""
    return pg.evaluate("""(timeout) => new Promise(res => { const i0 = idx, t0 = performance.now();
        const poll = () => { if (idx !== i0) return res(performance.now() - t0);
          if (performance.now() - t0 > timeout) return res(null); setTimeout(poll, 10); }; poll(); })""", timeout)


def flip_fresh_play(pg, cdp):
    """Stop, then Play: running and not paused, whatever came before."""
    if pg.evaluate("() => playing"):
        tap(pg, cdp, *centre(pg, "#play"))
        pg.wait_for_function("() => playing === false")
        pg.wait_for_timeout(200)
    flip_play(pg, cdp)
    pg.wait_for_timeout(300)


def flip_suite(b):
    print("\nFLIP -- by touch at 390, one page a second")
    ctx, pg, cdp, errs = fresh(b, "/flip")
    flip_setup(pg)
    cx, cy = centre(pg, "#pad")
    flip_play(pg, cdp)
    page_change(pg)                       # a page has just come up
    before = arrow(pg, ".flip-wrap")
    pg.wait_for_timeout(450)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(100)
    f1 = pg.evaluate(FLIP)
    moved = page_change(pg, timeout=1800)
    f2 = pg.evaluate(FLIP)
    check("Flip: a tap on the canvas pauses the flip on the page it is on",
          f1["paused"] and f2["playing"] and moved is None and f1["idx"] == f2["idx"],
          f"{f1} -> {f2}, page moved after {moved}")
    check("...and its badge says so: two bars where the play arrow was",
          f2["badge"].startswith(BARS), repr(f2["badge"]))
    check("...and the time readout stands still", f1["clock"] == f2["clock"], f"{f1['clock']} -> {f2['clock']}")
    during = arrow(pg, ".flip-wrap")
    check("Flip: paused, the round Play is painted in the middle of the canvas, and was not before",
          painted_mid(during) and before[0] < 10, f"before {before}, paused {during}")
    r = box(pg, "#pad")
    flick(pg, cdp, r["x"] + r["width"] * 0.7, r["y"] + r["height"] * 0.6, 0, 60)
    pg.wait_for_timeout(150)
    f2b = pg.evaluate(FLIP)
    check("Flip: paused, a drag on the canvas draws nothing and leaves it paused",
          f2b["points"] == f2["points"] and f2b["paused"] and quick(pg),
          f"{f2['points']} -> {f2b['points']} points, {f2b}, the drag took {press_ms(pg)}ms")
    tap(pg, cdp, cx, cy)
    gone = page_change(pg)
    f3 = pg.evaluate(FLIP)
    after = arrow(pg, ".flip-wrap")
    check("Flip: a second tap carries the flip on from where it paused",
          gone is not None and 250 < gone < 800 and not f3["paused"],
          f"the page gave way {gone}ms after the resume, with about 550ms of its 1000 left")
    check("...the badge plays again and the round Play is gone",
          not f3["badge"].startswith(BARS) and after[0] < 10, f"{f3['badge']!r}, {after}")
    check("...and the time readout counts on from where it stood, not from nought",
          f3["clock"] >= f2["clock"] + 0.2, f"{f2['clock']}s paused, {f3['clock']}s once the page gave way")

    # Scrubbed while paused
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(100)
    pr = box(pg, "#flipProgress")
    finger(pg, cdp, [(pr["x"] + pr["width"] * (0.1 + 0.08 * j), pr["y"] + pr["height"] / 2) for j in range(11)])
    pg.wait_for_timeout(100)
    f4 = pg.evaluate(FLIP)
    moved = page_change(pg, timeout=1500)
    f5 = pg.evaluate(FLIP)
    check("Flip: a paused flip scrubbed to another page stays paused on that page",
          f4["idx"] == 3 and moved is None and f5["paused"] and f5["badge"].startswith(BARS),
          f"{f4} -> {f5}, moved after {moved}")
    tap(pg, cdp, cx, cy)
    gone = page_change(pg)
    check("...and on resume that page gets its whole time", gone is not None and 800 < gone < 1400,
          f"gave way after {gone}ms of a 1000ms page")

    # Not taps, each from a fresh Play
    flip_fresh_play(pg, cdp)
    pg.wait_for_timeout(300)
    flick(pg, cdp, r["x"] + r["width"] * 0.6, r["y"] + r["height"] * 0.8, 60, 0, n=1)
    pg.wait_for_timeout(150)
    f6 = pg.evaluate(FLIP)
    moved = page_change(pg)
    check("Flip: a drag across the canvas is not a tap: the flip plays on",
          not f6["paused"] and moved is not None and quick(pg), f"{f6}, next page after {moved}, the drag took {press_ms(pg)}ms")
    flip_fresh_play(pg, cdp)
    two_fingers(pg, cdp, cx, cy)
    pg.wait_for_timeout(200)
    check("Flip: two fingers on the canvas are not a tap", not pg.evaluate(FLIP)["paused"], str(pg.evaluate(FLIP)))

    # Stop while paused
    flip_fresh_play(pg, cdp)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(150)
    was = pg.evaluate(FLIP)
    tap(pg, cdp, *centre(pg, "#play"))
    pg.wait_for_timeout(300)
    f7 = pg.evaluate(FLIP)
    badge_shown = pg.evaluate("() => getComputedStyle(document.querySelector('.flip-live')).display !== 'none'")
    check("Flip: Stop while paused ends the flip, and the round Play goes with it",
          was["paused"] and not f7["playing"] and not f7["paused"] and glyph_display(pg) == "none" and not badge_shown,
          f"{was} -> {f7}, glyph {glyph_display(pg)}, badge shown {badge_shown}")
    check("Flip: no page errors", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nFLIP -- a drawing page")
    ctx, pg, cdp, errs = fresh(b, "/flip")
    flip_setup(pg, n=2, fps=1, draw=True, span=3000)
    cx, cy = centre(pg, "#pad")
    flip_play(pg, cdp)
    pg.wait_for_timeout(1200)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(100)
    i1 = pg.evaluate(INK)
    pg.wait_for_timeout(600)
    i2 = pg.evaluate(INK)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(50)
    i3 = pg.evaluate(INK)
    pg.wait_for_timeout(700)
    i4 = pg.evaluate(INK)
    check("Flip: a drawing page's reveal stops where it is and carries on from there",
          i1 > 0 and i1 == i2 and i3 >= i2 * 0.9 and i4 > i3, f"ink {i1} paused, {i2} later, {i3} on resume, {i4} after")
    pg.wait_for_function("() => idx === 1", timeout=8000)
    tap(pg, cdp, cx, cy)
    pg.wait_for_timeout(100)
    pr = box(pg, "#flipProgress")
    finger(pg, cdp, [(pr["x"] + pr["width"] * (0.6 - 0.06 * j), pr["y"] + pr["height"] / 2) for j in range(10)])
    pg.wait_for_timeout(100)
    k1 = pg.evaluate(FLIP)
    j1 = pg.evaluate(INK)
    pg.wait_for_timeout(600)
    j2 = pg.evaluate(INK)
    check("Flip: a paused flip scrubbed onto a drawing page shows it whole, and still, until the resume",
          k1["idx"] == 0 and k1["paused"] and j1 >= i4 and j1 == j2, f"{k1}, ink {j1} then {j2} (the page drawn out: at least {i4})")
    ctx.close()

    print("\nFLIP -- the music")
    ctx, pg, cdp, errs = fresh(b, "/flip", spy=True)
    pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
    pg.wait_for_timeout(2500)
    flip_setup(pg, n=6)
    music_checks(pg, cdp, "Flip", "#pad", lambda: flip_play(pg, cdp))
    ctx.close()

    print("\nFLIP -- by mouse on a desk")
    ctx, pg, cdp, errs = fresh(b, "/flip", kind=DESK)
    flip_setup(pg)
    cx, cy = centre(pg, "#pad")
    flip_play(pg, None)
    pg.wait_for_timeout(300)
    tap(pg, None, cx, cy)
    pg.wait_for_timeout(100)
    d1 = pg.evaluate(FLIP)
    moved = page_change(pg, timeout=1500)
    tap(pg, None, cx, cy)
    gone = page_change(pg)
    d2 = pg.evaluate(FLIP)
    check("Flip (desk): a click on the canvas pauses the flip, and another carries it on",
          d1["paused"] and moved is None and gone is not None and not d2["paused"], f"{d1}, moved {moved}, then {gone}ms, {d2}")
    ctx.close()


with sync_playwright() as p:
    b = p.chromium.launch()
    pad_suite(b)
    flip_suite(b)
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
