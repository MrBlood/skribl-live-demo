#!/usr/bin/env python3
"""The music timeline, the Restart view and Cut on silence (step 2 of the music
plan, mocked first; the owner: "Yes on all").

  THE TIMELINE (lib/musictimeline.js). The drawer's one view: the drawing's
  lane over the song, two handles, and the whole song's line under them. The
  lane says what it is and how long it plays, and its marks sit where the
  drawing plays, from the loop's start. The view frames the loop: 1.28 times
  the longer of the loop and the drawing, the drawing counted up to three
  loops, the loop's start 9% in.

  FINGERS. On the song a finger slides it under the drawing: the loop keeps
  its length and its handles stay put. On the drawing's lane nothing moves.
  On a phone a finger that goes up or down first scrolls the page, and one
  that goes sideways slides the song. An end follows the finger, its bubble
  saying its time, while the view holds still; held near the edge the view
  widens, frame by frame, the far side kept. Let go, the view eases to its
  framing, frame by frame, at once under Reduce Motion. A tap on the whole
  song's line moves the loop there, its middle under the finger; a drag along
  it slides the loop with the finger.

  THE PLAYHEAD runs across the loop on the timeline while the loop plays.

  THE RESTART VIEW (lib/musicrestart.js). The loop's last 0.6s beside its
  first 0.6s, a smooth restart's fold counted. A finger on the left moves the
  end, on the right the start, the music following the finger. The dot pulls
  the smooth restart longer or shorter in 5ms steps, back to the line for a
  clean cut, and stops at half a second or half the loop. Its hint says what
  to do, with a tempo and without.

  CUT ON SILENCE (lib/audioloop.js cutFrames). On for a new song, off for a
  song from a draft that never said, kept in the drafts. Its words say how far
  both ends move, the same as the loop baked. The baked loop: both ends moved
  the same, the length kept, and no click where it comes round (the fixture
  clicks without it); with a smooth restart nothing moves. Switched while the
  loop plays, it plays on from the new join. Posted, the clip is the cut loop,
  and the player plays it as it is.

Every row runs on the Pad and on Flip: one drawer (lib/musicdrawer.js), one
timeline and one Restart view, each editor's half its hooks.
"""
import base64
import io
import json
import math
import os
import re
import struct
import sys
import urllib.request
import wave

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the music timeline works.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICTL_ONLY=Pad (or Flip) runs one editor, and
# MUSICTL_PART=layout (frame, slide, ends, whole, playhead, restart, cut,
# bake, post) one part. A real run sets neither.
ONLY = os.environ.get("MUSICTL_ONLY", "")
PART = os.environ.get("MUSICTL_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
WORK = {"Pad": "drawing", "Flip": "animation"}


def _wav(seconds, rate=8000, hz=220.0):
    """A steady tone: a loop cut anywhere but on a whole number of its cycles
    clicks where it comes round."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * hz * i / rate)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
SHORT = {"name": "six.wav", "mimeType": "audio/wav", "buffer": _wav(6.0)}
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""
# A drawing on the Pad as its own strokes make one: a point every 50ms for
# `secs` seconds, a stroke every second.
LONGDRAW = """(secs) => { strokes.length = 0;
  for (let i = 0; i <= secs * 20; i++) strokes.push({ x: 40 + (i % 20) * 9, y: 60 + Math.floor(i / 20) % 8 * 20, color: '#7c5cff', size: 6, t: i * 50, start: i % 20 === 0 });
  updateDrawingTimeLabels(); }"""
# How long each editor's drawing plays, one pass, as its timeline counts it.
DRAWN = {"Pad": "() => strokes.length ? getPlaybackDuration() / 1000 : 0",
         "Flip": "() => frames.some((f) => f.strokes.length) ? SkriblHold.plan(frames, fps, docLoop).cycle / 1000 : 0"}
TRIM = "() => ({ s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs, cut: loopCutOnSilence })"
SET = """(o) => { if ('tempo' in o) musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; }
  if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } if ('cut' in o) loopCutOnSilence = o.cut; updateTrimUI(); }"""
# The view as painted (the time at the left edge, the seconds across), the
# stage's box, and each handle's line on screen.
VIEW = "() => (document.getElementById('musicTimeline').dataset.view || '').split(' ').map(Number)"
BOX = """(s) => { const r = document.querySelector(s).getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }"""
HANDS = """() => ['tlStart', 'tlEnd'].map((id) => { const r = document.getElementById(id).getBoundingClientRect(); return +(r.left + r.width / 2).toFixed(2); })"""
# What a canvas recorded it painted (each keeps it on its root as it paints).
PAINTED = """(id) => { const host = document.getElementById(id), p = host && host._painted; if (!p) return null;
  return { w: host.querySelector('canvas').clientWidth, view: (host.dataset.view || '').split(' ').map(Number),
           marks: p.marks || null, lines: p.lines || null, turns: p.turns || 0, beats: p.beats,
           end: p.end || null, start: p.start || null, blend: p.blend }; }"""
# Every animation frame for `ms`, from the next one: the view and the loop.
# On frames only: a reading taken as the call lands is the frame before, and
# a let-go read that way looks like a view that has not moved yet.
FRAMES = """(ms) => new Promise((res) => { const tl = document.getElementById('musicTimeline'), out = []; let t0 = null;
  const tick = () => { const now = performance.now(); if (t0 === null) t0 = now;
    out.push([+(now - t0).toFixed(1), (tl.dataset.view || '').split(' ').map(Number), trimStart, trimEnd]);
    if (now - t0 < ms) requestAnimationFrame(tick); else res(out); };
  requestAnimationFrame(tick); })"""


def editor(b, name, path, *, drawn=True, song=TWELVE, opts=DESK, more=False, ctx=None):
    c = ctx or waits.instrument(b.new_context(**opts))
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if drawn:
        if name == "Pad":
            box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
            pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down()
            for k in range(40):
                pg.mouse.move(box["x"] + 80 + k * 6, box["y"] + 80 + k * 3); pg.wait_for_timeout(50)
            pg.mouse.up(); pg.wait_for_timeout(300)
            pg.click("#recordBtn"); pg.wait_for_timeout(700)
        else:
            pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 8})
    if song:
        add(pg, song)
    if more:
        set_more(pg, True)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def set_more(pg, want):
    if (pg.get_attribute("#fineTuneToggle", "aria-expanded") == "true") != want:
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(350)
        browsing.wait_scroll_still(pg)


def into_view(pg, sel):
    pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", sel)
    pg.wait_for_timeout(250)
    browsing.wait_scroll_still(pg)


def drag(pg, x0, y0, x1, y1, steps=12, up=True):
    pg.mouse.move(x0, y0); pg.mouse.down()
    for k in range(1, steps + 1):
        pg.mouse.move(x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps); pg.wait_for_timeout(16)
    if up:
        pg.mouse.up()


def at(view, w, t):
    """Where a song time sits on the timeline, in px from its left."""
    return (t - view[0]) / view[1] * w


def framing(t, drawing):
    """Where the view belongs: (left edge, span)."""
    L = max(0.05, t["e"] - t["s"])
    span = 1.28 * max(L, min(drawing, 3 * L))
    return t["s"] - 0.09 * span, span


def says(s):
    """Seconds as the drawer says them: whole when within a twentieth, else to the tenth."""
    t = math.floor(s * 10 + 1e-9 + 0.5) / 10
    return str(round(t)) if abs(t - round(t)) < 0.05 else f"{t:.1f}"


def clock(s):
    c = round(s * 100)
    return f"{c // 6000}:{(c // 100) % 60:02d}.{c % 100:02d}"


with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    print("\nMUSIC TIMELINE — the one view")
    for _n, _p in eds("layout"):
        c, pg, errs = editor(b, _n, _p, drawn=False)
        bare = pg.evaluate("""() => { const q = (s) => document.querySelector(s), shows = (s) => { const e = q(s); return !!e && e.getClientRects().length > 0; };
          return { name: q('#musicTlName').textContent, stage: shows('#musicTlStage'), start: shows('#tlStart'), end: shows('#tlEnd'),
                   whole: shows('#musicTlWhole'), part: shows('#musicTlPart'),
                   order: ['musicTlName', 'musicTlStage', 'musicTlWhole'].map((id) => Math.round(document.getElementById(id).getBoundingClientRect().top)) }; }""")
        c.close()
        c, pg, errs = editor(b, _n, _p)
        secs = pg.evaluate(DRAWN[_n])
        drawn_name = pg.evaluate("() => document.getElementById('musicTlName').textContent")
        want = f"Your {WORK[_n]} · {says(secs)}s"
        check(f"{_n}: the timeline is the drawer's one view: the drawing's lane over the song, two handles, and the whole song's line under them",
              bare["stage"] and bare["start"] and bare["end"] and bare["whole"] and bare["part"]
              and bare["order"] == sorted(bare["order"]) and len(set(bare["order"])) == 3,
              str(bare))
        check(f"{_n}: the drawing's lane says what it is: nothing drawn yet, or your {WORK[_n]} and how long it plays",
              bare["name"].strip().lower().endswith("nothing drawn yet") and drawn_name == want,
              f"empty {bare['name']!r}; drawn {drawn_name!r}, want {want!r}")
        check(f"{_n}: no page errors in the one view", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("layout"):
        # The lane's marks where the drawing plays, from the loop's start: a
        # stroke every second on the Pad, each page as long as it shows on Flip.
        c, pg, errs = editor(b, _n, _p)
        if _n == "Pad":
            pg.evaluate(LONGDRAW, 4)
            want = [k * 1.0 for k in range(5)]
        else:
            want = [0.0, 8 / 12, 16 / 12]
        pg.evaluate(SET, {"s": 1.0, "e": 5.0, "xf": 0, "tempo": None})
        pg.wait_for_timeout(700)
        m = pg.evaluate(PAINTED, "musicTimeline")
        got = [x[0] for x in m["marks"] if x[2] == 0] if m else []
        wx = [round(at(m["view"], m["w"], 1.0 + t), 2) for t in want] if m else []
        check(f"{_n}: the lane's marks sit where the {WORK[_n]} plays, from the loop's start",
              m is not None and len(got) == len(wx) and all(abs(g - x) < 0.6 for g, x in zip(got, wx)),
              f"marks at {got}, want {wx}")
        c.close()

    print("\nMUSIC TIMELINE — the framing")
    for _n, _p in eds("frame"):
        c, pg, errs = editor(b, _n, _p)
        secs = pg.evaluate(DRAWN[_n])
        rows = []
        # The loop longer than the drawing; the drawing longer, counted whole;
        # the drawing longer than three loops, counted as three. The drawing
        # plays about 2s, so the last two ask for it whole and for three loops
        # of it, and the row says so of the fixture as well as of the view.
        for s, e in ((1.0, 5.0), (2.0, 3.0), (3.0, 3.5)):
            pg.evaluate(SET, {"s": s, "e": e, "xf": 0})
            pg.wait_for_timeout(900)
            v = pg.evaluate(VIEW)
            rows.append(((s, e), v, framing({"s": s, "e": e}, secs)))
        ok = all(abs(v[0] - f[0]) < 2e-3 * f[1] and abs(v[1] - f[1]) < 2e-3 * f[1] for _, v, f in rows)
        check(f"{_n}: the view frames the loop: 1.28 times the longer of the loop and the {WORK[_n]} (counted up to three loops), the loop's start 9% in",
              ok and abs(rows[0][2][1] - 1.28 * 4) < 1e-9
              and abs(rows[1][2][1] - 1.28 * secs) < 1e-9 and abs(rows[2][2][1] - 1.28 * 1.5) < 1e-9,
              "; ".join(f"loop {lp}: view {v[0]:.3f}+{v[1]:.3f}, want {f[0]:.3f}+{f[1]:.3f}" for lp, v, f in rows)
              + f" (the {WORK[_n]} plays {secs:.2f}s)")
        c.close()

    print("\nMUSIC TIMELINE — a finger on the song")
    for _n, _p in eds("slide"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(500)
        st = pg.evaluate(BOX, "#musicTlStage")
        t0, v0, h0 = pg.evaluate(TRIM), pg.evaluate(VIEW), pg.evaluate(HANDS)
        drag(pg, st["x"] + st["w"] / 2, st["y"] + st["h"] * 0.65, st["x"] + st["w"] / 2 - 60, st["y"] + st["h"] * 0.65, up=False)
        t1, h1 = pg.evaluate(TRIM), pg.evaluate(HANDS)
        pg.mouse.up(); pg.wait_for_timeout(500)
        t2, h2 = pg.evaluate(TRIM), pg.evaluate(HANDS)
        moved = 60 / st["w"] * v0[1]
        check(f"{_n}: a finger on the song slides it under the drawing: the loop keeps its length and its handles stay put",
              abs((t1["s"] - t0["s"]) - moved) < 0.02 and abs((t1["e"] - t1["s"]) - (t0["e"] - t0["s"])) < 1e-6
              and max(abs(a - b_) for a, b_ in zip(h0, h1)) < 1 and max(abs(a - b_) for a, b_ in zip(h0, h2)) < 1
              and abs(t2["s"] - t1["s"]) < 1e-6,
              f"60px left: the loop {t0['s']:.3f}-{t0['e']:.3f} -> {t1['s']:.3f}-{t1['e']:.3f} (want +{moved:.3f}s), "
              f"let go {t2['s']:.3f}; handles {h0} -> {h1} -> {h2}")
        # A press on the drawing's lane: the drawing stays put, and nothing moves.
        v1 = pg.evaluate(VIEW)
        drag(pg, st["x"] + st["w"] / 2, st["y"] + 10, st["x"] + st["w"] / 2 - 80, st["y"] + 10)
        pg.wait_for_timeout(400)
        t3, v3 = pg.evaluate(TRIM), pg.evaluate(VIEW)
        check(f"{_n}: a press on the drawing's lane moves nothing",
              abs(t3["s"] - t2["s"]) < 1e-9 and abs(t3["e"] - t2["e"]) < 1e-9 and max(abs(a - b_) for a, b_ in zip(v1, v3)) < 1e-4,
              f"the loop {t2['s']:.3f}-{t2['e']:.3f} -> {t3['s']:.3f}-{t3['e']:.3f}, view {v1} -> {v3}")
        check(f"{_n}: no page errors from the song's fingers", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("slide"):
        # On a phone: up or down first scrolls the page; sideways slides the
        # song. The drawer opens at the page's foot, so the finger goes down
        # (the page scrolls back up), and drifts 12px sideways as it goes: past
        # the 6px a finger has to go sideways to slide, had it gone that way
        # first.
        c, pg, errs = editor(b, _n, _p, opts=PHONE)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(500)
        cdp = c.new_cdp_session(pg)

        def touch(kind, x, y):
            cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
        st = pg.evaluate(BOX, "#musicTlStage")
        t0 = pg.evaluate(TRIM)
        x0, y0 = st["x"] + st["w"] / 2, st["y"] + st["h"] * 0.65
        touch("touchStart", x0, y0)
        for k in range(1, 13):
            touch("touchMove", x0 + k, y0 + k * 10); pg.wait_for_timeout(16)
        touch("touchEnd", x0 + 12, y0 + 120)
        pg.wait_for_timeout(600)
        t1, st1 = pg.evaluate(TRIM), pg.evaluate(BOX, "#musicTlStage")
        check(f"{_n}: on a phone a finger that goes up or down first scrolls the page, and the loop stays",
              abs(t1["s"] - t0["s"]) < 1e-9 and abs(t1["e"] - t0["e"]) < 1e-9 and st1["y"] > st["y"] + 15,
              f"the loop {t0['s']:.3f}-{t0['e']:.3f} -> {t1['s']:.3f}-{t1['e']:.3f}; the timeline's top {st['y']:.0f} -> {st1['y']:.0f}px")
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(300)
        st = pg.evaluate(BOX, "#musicTlStage")
        v0 = pg.evaluate(VIEW)
        x0, y0 = st["x"] + st["w"] / 2, st["y"] + st["h"] * 0.65
        touch("touchStart", x0, y0)
        for k in range(1, 13):
            touch("touchMove", x0 - k * 5, y0 + k * 0.3); pg.wait_for_timeout(16)
        touch("touchEnd", x0 - 60, y0)
        pg.wait_for_timeout(500)
        t2 = pg.evaluate(TRIM)
        moved = 60 / st["w"] * v0[1]
        check(f"{_n}: on a phone a finger that goes sideways slides the song, the loop's length kept",
              abs((t2["s"] - t1["s"]) - moved) < 0.1 * moved and abs((t2["e"] - t2["s"]) - (t1["e"] - t1["s"])) < 1e-6,
              f"60px left: the loop {t1['s']:.3f}-{t1['e']:.3f} -> {t2['s']:.3f}-{t2['e']:.3f} (want +{moved:.3f}s)")
        c.close()

    print("\nMUSIC TIMELINE — an end")
    for _n, _p in eds("ends"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(600)
        st, v0 = pg.evaluate(BOX, "#musicTlStage"), pg.evaluate(VIEW)
        he = pg.evaluate(BOX, "#tlEnd")
        hx, hy = he["x"] + he["w"] / 2, he["y"] + he["h"] / 2
        drag(pg, hx, hy, hx - 50, hy, steps=10, up=False)
        held = pg.evaluate("""() => { const b = document.getElementById('bubbleEnd');
          return { e: trimEnd, words: b.textContent, shown: getComputedStyle(b).opacity, view: (document.getElementById('musicTimeline').dataset.view || '').split(' ').map(Number) }; }""")
        pg.mouse.up(); pg.wait_for_timeout(300)
        ex = at(v0, st["w"], held["e"])
        check(f"{_n}: an end follows the finger, its bubble saying its time, while the view holds still",
              abs(ex - (hx - 50 - st["x"])) < 1.0 and held["words"] == clock(held["e"]) and float(held["shown"]) > 0.95
              and max(abs(a - b_) for a, b_ in zip(v0, held["view"])) < 1e-4,
              f"the end at {ex:.1f}px under a finger at {hx - 50 - st['x']:.1f}px, saying {held['words']!r} at opacity {held['shown']}; "
              f"view {v0} -> {held['view']}")
        # Held at the edge: the view widens, frame by frame, the left edge kept.
        pg.evaluate(SET, {"s": 2.0, "e": 4.0})
        pg.wait_for_timeout(700)
        st, v0 = pg.evaluate(BOX, "#musicTlStage"), pg.evaluate(VIEW)
        he = pg.evaluate(BOX, "#tlEnd")
        hx, hy = he["x"] + he["w"] / 2, he["y"] + he["h"] / 2
        drag(pg, hx, hy, st["x"] + st["w"] - 3, hy, steps=6, up=False)
        fr = pg.evaluate(FRAMES, 700)
        pg.mouse.up()
        after = pg.evaluate(FRAMES, 900)
        spans = [f[1][1] for f in fr]
        ratios = [spans[i + 1] / spans[i] for i in range(len(spans) - 1) if spans[i] > 0]
        last = fr[-1]
        ex = at(last[1], st["w"], last[3])
        check(f"{_n}: held near the edge, the view widens smoothly, frame by frame, the far side kept, and the end follows out",
              len(fr) >= 20 and spans[-1] > spans[0] * 1.8 and all(r >= 1 - 1e-9 for r in ratios) and max(ratios) <= 1.1
              and max(abs(f[1][0] - v0[0]) for f in fr) < 1e-3 and abs(ex - (st["w"] - 3)) < 2.0,
              f"{len(fr)} frames, span {spans[0]:.2f} -> {spans[-1]:.2f}s, the most in a frame x{max(ratios) if ratios else 0:.3f}, "
              f"left edge {v0[0]:.3f} -> {last[1][0]:.3f}; the end at {ex:.1f}px of {st['w']:.0f}")
        # Let go: the view eases to its framing, a step each frame.
        goal = framing({"s": after[-1][2], "e": after[-1][3]}, pg.evaluate(DRAWN[_n]))
        gap = [abs(f[1][1] - goal[1]) + abs(f[1][0] - goal[0]) for f in after]
        g0 = abs(last[1][1] - goal[1]) + abs(last[1][0] - goal[0])
        steps = [(gap[i] - gap[i + 1]) / gap[i] for i in range(len(gap) - 1) if gap[i] > 1e-3 * goal[1]]
        landed = next((i for i, g in enumerate(gap) if g < 2e-3 * goal[1]), None)
        check(f"{_n}: let go, the view eases to its framing, frame by frame, with no jump",
              g0 > 0.2 and landed is not None and landed >= 4 and gap[0] > 0.3 * g0
              and all(s_ > -1e-6 for s_ in steps) and max(steps) <= 0.7,
              f"from {g0:.2f}s off its framing: {len(after)} frames, at it on frame {landed}; the first frame {gap[0]:.2f}s off, "
              f"the most covered in a frame {max(steps) if steps else 0:.2f}")
        check(f"{_n}: no page errors from an end", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("ends"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **DESK))
        c, pg, errs = editor(b, _n, _p, ctx=c)
        pg.evaluate(SET, {"s": 2.0, "e": 4.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(400)
        st = pg.evaluate(BOX, "#musicTlStage")
        he = pg.evaluate(BOX, "#tlEnd")
        hx, hy = he["x"] + he["w"] / 2, he["y"] + he["h"] / 2
        drag(pg, hx, hy, st["x"] + st["w"] - 3, hy, steps=6, up=False)
        pg.wait_for_timeout(500)
        pg.mouse.up()
        after = pg.evaluate(FRAMES, 300)
        goal = framing({"s": after[-1][2], "e": after[-1][3]}, pg.evaluate(DRAWN[_n]))
        off = [abs(f[1][1] - goal[1]) + abs(f[1][0] - goal[0]) for f in after]
        check(f"{_n}: under Reduce Motion the view is where it belongs at once",
              off and max(off) < 2e-3 * goal[1],
              f"off its framing by {[round(o, 3) for o in off[:5]]}s on the first frames")
        c.close()

    print("\nMUSIC TIMELINE — the whole song's line")
    for _n, _p in eds("whole"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 4.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(500)
        wh = pg.evaluate(BOX, "#musicTlWhole")
        y = wh["y"] + wh["h"] / 2
        pg.mouse.click(wh["x"] + wh["w"] * 0.75, y); pg.wait_for_timeout(900)
        t1 = pg.evaluate(TRIM)
        # With a tempo, 31% along: the loop's middle there would start it at
        # 2.72s, between two beats (2.6 and 3.1).
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.1}})
        pg.mouse.click(wh["x"] + wh["w"] * 0.31, y); pg.wait_for_timeout(900)
        t2 = pg.evaluate(TRIM)
        on_beat = abs(((t2["s"] - 0.1) / 0.5) - round((t2["s"] - 0.1) / 0.5)) < 1e-3
        check(f"{_n}: a tap on the whole song's line moves the loop there, its middle under the finger, on a beat once there is a tempo",
              abs(t1["s"] - (0.75 * 12 - 1)) < 0.02 and abs((t1["e"] - t1["s"]) - 2) < 1e-6
              and on_beat and abs(t2["s"] - (0.31 * 12 - 1)) <= 0.25 + 1e-6 and abs((t2["e"] - t2["s"]) - 2) < 1e-6,
              f"at 75%: {t1['s']:.3f}-{t1['e']:.3f} (want 8.000); with a tempo, at 31%: {t2['s']:.3f}-{t2['e']:.3f} (the beat nearest 2.72)")
        pg.evaluate(SET, {"tempo": None})
        drag(pg, wh["x"] + wh["w"] * 0.25, y, wh["x"] + wh["w"] * 0.6, y, steps=10, up=False)
        mid = pg.evaluate(TRIM)
        pg.mouse.up(); pg.wait_for_timeout(500)
        end = pg.evaluate(TRIM)
        check(f"{_n}: a drag along the whole song's line slides the loop with the finger",
              abs(mid["s"] - (0.6 * 12 - 1)) < 0.05 and abs((mid["e"] - mid["s"]) - 2) < 1e-6 and abs(end["s"] - mid["s"]) < 1e-6,
              f"25% to 60%: the loop at {mid['s']:.3f}-{mid['e']:.3f} (want 6.2), let go {end['s']:.3f}")
        c.close()

    print("\nMUSIC TIMELINE — the playhead")
    for _n, _p in eds("playhead"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 4.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(500)
        pg.click("#previewLoopBtn")
        seen = pg.evaluate("""() => new Promise((res) => { const ph = document.getElementById('playhead'), tl = document.getElementById('musicTimeline'),
              stage = document.getElementById('musicTlStage'), out = [], t0 = performance.now();
            (function tick() { const m = /translateX\\(([-\\d.]+)px\\)/.exec(ph.style.transform), v = (tl.dataset.view || '0 1').split(' ').map(Number);
              out.push([performance.now() - t0, ph.hidden || !m ? null : v[0] + parseFloat(m[1]) / stage.clientWidth * v[1]]);
              if (performance.now() - t0 < 2600) requestAnimationFrame(tick); else res(out); })(); })""")
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(300)
        late = [t for ms, t in seen if ms > 400]
        shown = [t for t in late if t is not None]
        check(f"{_n}: the playhead runs across the loop on the timeline while the loop plays, and comes round",
              late and len(shown) >= 0.8 * len(late) and min(shown) >= 2.0 - 0.06 and max(shown) <= 4.0 + 0.06
              and max(shown) - min(shown) > 1.0 and any(shown[i] < shown[i - 1] - 0.5 for i in range(1, len(shown))),
              f"{len(shown)} of {len(late)} frames shown, at {min(shown) if shown else None}..{max(shown) if shown else None}s of the loop 2-4")
        c.close()

    print("\nMUSIC TIMELINE — the Restart view")
    for _n, _p in eds("restart"):
        c, pg, errs = editor(b, _n, _p, more=True)
        pg.evaluate(SET, {"s": 1.0, "e": 3.0, "xf": 0, "cut": False, "tempo": None})
        into_view(pg, "#musicRestart")
        pg.wait_for_timeout(300)
        clean = pg.evaluate(PAINTED, "musicRestart")
        pg.evaluate(SET, {"xf": 200})
        pg.wait_for_timeout(300)
        fold = pg.evaluate(PAINTED, "musicRestart")
        close = lambda a, b_: a is not None and all(abs(x - y) < 1e-3 for x, y in zip(a, b_))
        check(f"{_n}: the Restart view shows the loop's last 0.6s beside its first 0.6s, a smooth restart's fold counted",
              clean and fold and close(clean["end"], [2.4, 3.0]) and close(clean["start"], [1.0, 1.6])
              and close(fold["end"], [2.2, 2.8]) and close(fold["start"], [1.0, 1.6]) and abs(fold["blend"] - 0.2) < 1e-9,
              f"clean cut: {clean and clean['end']} beside {clean and clean['start']}; a 0.2s smooth restart: {fold and fold['end']} beside {fold and fold['start']}")
        # The two sides: the music follows the finger.
        pg.evaluate(SET, {"xf": 0})
        pg.wait_for_timeout(250)
        rv = pg.evaluate(BOX, "#musicRestart")
        half = rv["w"] / 2
        drag(pg, rv["x"] + half * 0.5, rv["y"] + 60, rv["x"] + half * 0.5 + 30, rv["y"] + 60)
        pg.wait_for_timeout(300)
        a = pg.evaluate(TRIM)
        drag(pg, rv["x"] + half * 1.5, rv["y"] + 60, rv["x"] + half * 1.5 - 30, rv["y"] + 60)
        pg.wait_for_timeout(300)
        bb = pg.evaluate(TRIM)
        d = 30 / half * 0.6
        check(f"{_n}: a finger on the Restart view's left moves the end, on its right the start, the music following the finger",
              abs(a["e"] - (3.0 - d)) < 0.01 and abs(a["s"] - 1.0) < 1e-6 and abs(bb["s"] - (1.0 + d)) < 0.01 and abs(bb["e"] - a["e"]) < 1e-6,
              f"left 30px right: the end 3.000 -> {a['e']:.3f} (want {3 - d:.3f}), the start {a['s']:.3f}; "
              f"right 30px left: the start -> {bb['s']:.3f} (want {1 + d:.3f})")
        # The dot: longer, back to the line, and as far as it goes.
        pg.evaluate(SET, {"s": 1.0, "e": 3.0, "xf": 0})
        pg.wait_for_timeout(250)

        def dot():
            r = pg.evaluate(BOX, "#musicBlendDot")
            return r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
        # 43px: not a whole number of 5ms steps on these widths, so a dot
        # that did not keep to them would show it.
        dx, dy = dot()
        drag(pg, dx, dy, dx + 43, dy, steps=8)
        pg.wait_for_timeout(250)
        on = pg.evaluate("() => ({ xf: loopCrossfadeMs, sw: document.getElementById('musicSmooth').getAttribute('aria-checked') })")
        dx, dy = dot()
        drag(pg, dx, dy, rv["x"] + half - 30, dy, steps=8)
        pg.wait_for_timeout(250)
        off = pg.evaluate("() => ({ xf: loopCrossfadeMs, sw: document.getElementById('musicSmooth').getAttribute('aria-checked') })")
        want = 43 / half * 600
        check(f"{_n}: the dot pulls the smooth restart longer or shorter, in 5ms steps, back to the line for a clean cut",
              on["xf"] % 5 == 0 and abs(on["xf"] - want) <= 5 and on["sw"] == "true" and off["xf"] == 0 and off["sw"] == "false",
              f"43px out: {on} (want about {want:.0f}ms); back past the line: {off}")
        caps = []
        for s, e, most in ((1.0, 3.0, 500), (1.0, 1.6, 300)):
            pg.evaluate(SET, {"s": s, "e": e, "xf": 0})
            pg.wait_for_timeout(250)
            dx, dy = dot()
            drag(pg, dx, dy, rv["x"] + rv["w"] - 2, dy, steps=8)
            pg.wait_for_timeout(250)
            caps.append((pg.evaluate("() => loopCrossfadeMs"), most))
        check(f"{_n}: the dot stops at half a second, or half the loop",
              all(gotxf == most for gotxf, most in caps), f"(ms, the most): {caps}")
        hint = pg.evaluate("() => document.getElementById('musicRvHint').textContent")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}})
        pg.wait_for_timeout(200)
        hint_beat = pg.evaluate("() => document.getElementById('musicRvHint').textContent")
        check(f"{_n}: the Restart view's hint says what to do, with the beat and without",
              hint == "Drag either side to line the music up across the middle. Pull the dot to blend them."
              and hint_beat == "Line the beats up across the middle: drag either side. Pull the dot to blend them.",
              f"without: {hint!r}; with a tempo: {hint_beat!r}")
        check(f"{_n}: no page errors in the Restart view", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC TIMELINE — Cut on silence")
    # A loop the steady tone clicks at: 3.8013s is 836.29 of its cycles. The
    # tone comes round to a clean join every half of its period (100 frames at
    # 44.1kHz), so the nearest clean join is never further than that: here 21
    # frames later, under a thousandth of a second; ending 0.9ms sooner, 40
    # later; 1.8ms sooner, 39 earlier.
    LOOP = {"s": 0.5, "e": 4.3013, "xf": 0}
    ENDS = (4.3013, 4.3004, 4.2995)
    for _n, _p in eds("cut"):
        c, pg, errs = editor(b, _n, _p, more=True)
        fresh = pg.evaluate("() => ({ cut: loopCutOnSilence, sw: document.getElementById('musicCut').getAttribute('aria-checked') })")
        pg.evaluate("() => { pendingMusicMeta = { trimStart: 1, trimEnd: 3, crossfadeMs: 0, enabled: true }; }")
        add(pg, SHORT)
        old = pg.evaluate("() => ({ cut: loopCutOnSilence, sw: document.getElementById('musicCut').getAttribute('aria-checked') })")
        pg.evaluate("() => { pendingMusicMeta = { trimStart: 1, trimEnd: 3, crossfadeMs: 0, enabled: true, cut: true }; }")
        add(pg, TWELVE)
        said = pg.evaluate("() => loopCutOnSilence")
        check(f"{_n}: Cut on silence is on for a new song, and off for a song from a draft that never said",
              fresh == {"cut": True, "sw": "true"} and old == {"cut": False, "sw": "false"} and said is True,
              f"a new song {fresh}; a draft's that never said {old}; a draft's that said on: {said}")
        kept = []
        for want in (False, True):
            browsing.pad_drawer(pg, "music")             # a reload shuts the drawer
            set_more(pg, True)
            if pg.evaluate("() => loopCutOnSilence") != want:
                pg.click("#musicCut"); pg.wait_for_timeout(200)
            pg.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
            pg.wait_for_timeout(2500)
            pg.reload()
            pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
            waits.settle(pg, 600)
            kept.append((want, pg.evaluate("() => loopCutOnSilence")))
        check(f"{_n}: Cut on silence is kept in the drafts, on or off",
              all(w_ == g for w_, g in kept), f"(set, after a reload): {kept}")
        c.close()
    for _n, _p in eds("cut"):
        c, pg, errs = editor(b, _n, _p, more=True)
        said = []
        for e in ENDS:
            pg.evaluate(SET, dict(LOOP, e=e, cut=True))
            pg.wait_for_timeout(200)
            words = pg.evaluate("() => document.getElementById('musicCutSub').textContent")
            d = pg.evaluate("""() => SkriblAudioLoop.cutSeconds({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs, cut: true })""")
            how = "under a thousandth of a second" if abs(d) < 0.0005 else f"{abs(d):.3f}s"
            said.append((d, words, f"Both ends move {how} {'later' if d > 0 else 'earlier'}, to where the end runs into the start without a click."))
        pg.evaluate(SET, {"xf": 200})
        smooth = pg.evaluate("() => document.getElementById('musicCutSub').textContent")
        pg.evaluate(SET, {"xf": 0, "cut": False})
        offw = pg.evaluate("() => document.getElementById('musicCutSub').textContent")
        check(f"{_n}: Cut on silence's words say how far both ends move, the same as the loop it bakes",
              all(w_ == want for _, w_, want in said) and all(abs(d) > 1e-4 for d, _, _ in said)
              and {d > 0 for d, _, _ in said} == {True, False} and len({abs(d) < 0.0005 for d, _, _ in said}) == 2
              and smooth == "For a clean cut: with Smooth restart on, the restart is already smooth."
              and offw == "Each end cuts exactly where it is set.",
              "; ".join(f"{d * 1000:.3f}ms: {w_!r}" + ("" if w_ == want else f" (want {want!r})") for d, w_, want in said)
              + f"; with a smooth restart: {smooth!r}; off: {offw!r}")
        c.close()

    print("\nMUSIC TIMELINE — the loop baked, cut on silence")
    # The editor's own bake (its buildLoopAudioBuffer, with its switch) beside
    # lib/audioloop.js's uncut slice, read sample by sample.
    BAKE = """(o) => { const raw = currentAudioBuffer.getChannelData(0), sr = currentAudioBuffer.sampleRate;
      const got = buildLoopAudioBuffer(), on = got ? got.getChannelData(0) : null;
      const off = SkriblAudioLoop.loopChannels({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs, cut: false }).channels[0];
      const s0 = Math.floor(trimStart * sr); let at = null;
      for (let k = -o.span; k <= o.span && at === null; k++) { let same = true;
        for (let i = 0; i < 32; i++) if (Math.abs(raw[s0 + k + i] - on[i]) > 1e-6) { same = false; break; }
        if (same) at = k; }
      let step = 0; for (let i = 1; i < off.length; i++) step = Math.max(step, Math.abs(off[i] - off[i - 1]));
      // Where it comes round: the sample the loop goes back to, against the
      // one the song itself plays after the loop's last.
      const jump = (x, from) => Math.abs(x[0] - raw[from + x.length]);
      return { sr, n: on.length, nOff: off.length, at, said: Math.round(SkriblAudioLoop.cutSeconds({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs, cut: true }) * sr),
               jumpOn: at === null ? null : jump(on, s0 + at), jumpOff: jump(off, s0), step,
               sameOff: on.length === off.length && on.every((v, i) => Math.abs(v - off[i]) < 1e-6) }; }"""
    for _n, _p in eds("bake"):
        c, pg, errs = editor(b, _n, _p, more=True)
        pg.evaluate(SET, dict(LOOP, cut=True))
        span = pg.evaluate("() => Math.round(SkriblAudioLoop.CUT_MS / 1000 * currentAudioBuffer.sampleRate) + 2")
        on = pg.evaluate(BAKE, {"span": span})
        # No click: the loop goes back to a sample no further off the song's
        # own next than two of the song's own steps (uncut, this one is 31).
        check(f"{_n}: the baked loop is cut where it joins without a click, as near as there is one: both ends moved the same, the length kept",
              on["at"] is not None and on["at"] != 0 and on["at"] == on["said"] and abs(on["at"]) <= on["sr"] / 440 + 1
              and on["n"] == on["nOff"]
              and on["jumpOff"] > 10 * on["step"] and on["jumpOn"] is not None and on["jumpOn"] <= 2 * on["step"],
              f"moved {on['at']} frames (said {on['said']}), {on['n']} frames against {on['nOff']} uncut; where it comes round, "
              f"off the song's own next sample by {on['jumpOn'] if on['jumpOn'] is None else round(on['jumpOn'], 4)} cut and "
              f"{on['jumpOff']:.4f} uncut, against the song's own largest step {on['step']:.4f}")
        pg.evaluate(SET, {"xf": 200})
        fold = pg.evaluate("""() => { const got = buildLoopAudioBuffer().getChannelData(0);
          const off = SkriblAudioLoop.loopChannels({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs, cut: false }).channels[0];
          return { same: got.length === off.length && got.every((v, i) => Math.abs(v - off[i]) < 1e-6), n: got.length,
                   said: SkriblAudioLoop.cutSeconds({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs, cut: true }) }; }""")
        pg.evaluate(SET, {"xf": 0, "cut": False})
        plain = pg.evaluate(BAKE, {"span": span})
        check(f"{_n}: with a smooth restart, or switched off, Cut on silence moves nothing",
              fold["same"] and fold["said"] == 0 and plain["sameOff"] and plain["at"] == 0,
              f"smooth restart: the same as uncut {fold['same']}, moves {fold['said']}s; off: the same as uncut {plain['sameOff']}")
        # Switched while the loop plays: it plays on from the new join.
        pg.evaluate(SET, {"cut": False})
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(700)
        pg.evaluate("() => { window.__src = _waLoop.source(); }")
        pg.click("#musicCut"); pg.wait_for_timeout(500)
        z = pg.evaluate(BAKE.replace("const got = buildLoopAudioBuffer(), on = got ? got.getChannelData(0) : null;",
                                     "const s = _waLoop.source(), on = s ? s.buffer.getChannelData(0) : null; if (!on) return null; if (s === window.__src) return { stale: true };"),
                        {"span": span})
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(200)
        check(f"{_n}: switched while the loop plays, Cut on silence plays on from the new join",
              z is not None and "stale" not in z and z["at"] == z["said"] and z["at"] != 0, str(z))
        check(f"{_n}: no page errors from the bake", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC TIMELINE — posted, cut on silence")
    for _n, _p in eds("post"):
        c, pg, errs = editor(b, _n, _p, more=True)
        pg.evaluate(SET, dict(LOOP, cut=True))
        pg.wait_for_timeout(300)
        bake = pg.evaluate("""() => { const x = buildLoopAudioBuffer().getChannelData(0);
          return { n: x.length, sr: currentAudioBuffer.sampleRate, head: Array.from(x.slice(0, 16)), tail: Array.from(x.slice(-16)) }; }""")
        if _n == "Pad":
            browsing.pad_drawer_close(pg)
            pg.wait_for_timeout(300)
            pg.click("#postBtn"); pg.wait_for_timeout(500)
            pg.fill("#postTitleInput", "cut on silence")
            pg.click("#postSubmitBtn")
        else:
            pg.evaluate("shareSkribl()")
        pg.wait_for_function("() => window.SkriblPosted && SkriblPosted.list && SkriblPosted.list().length > 0", timeout=30000)
        pid = pg.evaluate("() => SkriblPosted.list()[0].id")
        sk = json.load(urllib.request.urlopen(BASE + "/api/skribls/" + pid, timeout=15))["skribl"]
        music = sk.get("music") or (sk.get("frames") or [{}])[0].get("music")
        clip, data = None, str((music or {}).get("data", ""))
        wav = (base64.b64decode(data.split(",", 1)[1]) if data.startswith("data:audio/wav;base64,")
               else urllib.request.urlopen(BASE + data if data.startswith("/") else data, timeout=15).read() if data else None)
        if wav and wav[:4] == b"RIFF":
            w = wave.open(io.BytesIO(wav))
            n, raw = w.getnframes(), w.readframes(w.getnframes())
            vals = [v / 32768 for v in struct.unpack(f"<{n * w.getnchannels()}h", raw)][::w.getnchannels()]
            clip = {"n": n, "sr": w.getframerate(), "head": vals[:16], "tail": vals[-16:]}
        near = lambda a, b_: all(abs(x - y) < 3 / 32768 for x, y in zip(a, b_))
        check(f"{_n}: the posted clip is the cut loop, sample for sample",
              clip is not None and clip["n"] == bake["n"] and clip["sr"] == bake["sr"]
              and near(clip["head"], bake["head"]) and near(clip["tail"], bake["tail"]) and "cut" not in music,
              f"posted {clip and clip['n']} frames at {clip and clip['sr']}Hz against the bake's {bake['n']} at {bake['sr']}Hz; "
              f"says cut: {'cut' in (music or {})}")
        pl = c.new_page()
        perr = []
        pl.on("pageerror", lambda e: perr.append(str(e)))
        pl.goto(BASE + "/s/" + pid, wait_until="load")
        pl.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
        pl.wait_for_timeout(300)
        st = pl.evaluate("""() => { const x = buildLoopAudioBuffer(); return { cut: loopCutOnSilence, s: trimStart,
          n: x ? x.length : null, all: currentAudioBuffer.length }; }""")
        check(f"{_n}: the player plays the posted clip as it is, not cut again",
              st["cut"] is False and st["s"] == 0 and st["n"] is not None and abs(st["n"] - st["all"]) <= 1 and not perr,
              f"{st}; {perr[:1]}")
        c.close()

    b.close()

summarise_and_exit()
