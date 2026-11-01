#!/usr/bin/env python3
"""The music timeline, the Restart view and Cut on silence (step 2 of the music
plan, mocked first; the owner: "Yes on all").

  THE TIMELINE (lib/musictimeline.js). The drawer's one view: the drawing's
  lane over the song, two handles, and the whole song's line under them. The
  lane says what it is and how long it plays, and its marks sit where the
  drawing plays, from the loop's start, a dot at the drawing's very end
  ending on it rather than past it. The view frames the loop: 1.28 times
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

  EACH END'S GRIP IS A TAB AT ITS FOOT (the owner: in the middle of the line
  it "kind of gets in the way of seeing where the wave starts for the beat").
  Asked of what is painted on top, on a phone and a desk: beside either line,
  over the song, nothing is the grip; the tab shows half under the song's
  edge and keeps clear of the whole song's line, and a tap under it, on that
  line, takes the end, whose reach runs 26px below its tab (verify_musicundo
  reads the reach); and the tab, pressed below the song's edge, drags its end.

  THE LOOP'S EDGES ARE SHARP (the owner's pick in the whole-drawer mock, "1.5px
  sharp"). Read on the screenshot at the screen's own pixels, each end placed
  between pixels in the quiet of a song: a run of the accent as wide as 1.5px
  rounds to on that screen (2 on a desk, 3 at 2x, 5 at 3x, the owner's phone),
  the ground either side flat. The 3px line before was 5 columns at 2x with
  half-lit ones either side.

  MAGNIFY (the owner, looking for Fine-tune's: "All yes but maybe go to
  x64?", then "stay"; then "Like 512x?" to see the wave cross). Magnifier -
  and + at the end of the name's line, its middle on the name's, step 1x to
  512x and say the rung, each stopping at its end of the ladder, and stay
  where they are as the rung's words grow. Each rung is the framing over
  that many, around the end last touched (the start until the end is), and
  the loop never moves for it; a step glides there frame by frame, at once
  under Reduce Motion.
  Zoomed in, an end follows the finger at the zoom while the view holds
  still; held at either edge the view slides along, and let go it glides
  back with that end in the middle. The end's own - and + make it the end
  zoomed around. The zoom stays when the drawer is put away and opened again;
  a new song starts at 1x on its start. Zoomed past a block a column, the
  song is drawn from its samples. Its words and glyphs read against what is
  behind them, light and dark.

  CLOSE IN, THE WAVE ITSELF (the owner: "We need to magnify by enough to see
  where it crosses the middle line"; "All yes" to the mock). Asked of what is
  painted, on a 44.1kHz tone whose every zero is known: while a point holds 64
  samples or more the song is loudness, the same above and below; under 64 it
  is the wave, which crosses the middle line; the line sits at the wave's zero,
  halfway between its crests and troughs; the wave crosses it where the song
  crosses zero, to the pixel; past the loop it is dimmed, as the bars are; and
  under 8 samples a point it is the samples themselves, joined. The line
  reads 3:1 and up against the song's ground, inside the loop and past it,
  light and dark (the owner's pick, the stronger of the two mocked).

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
from PIL import Image  # noqa: E402

# For calibration: MUSICTL_ONLY=Pad (or Flip) runs one editor, and
# MUSICTL_PART=layout (frame, slide, ends, grip, mag, inside, head, wave,
# whole, playhead, restart, cut, bake, post) one part. A real run sets neither.
ONLY = os.environ.get("MUSICTL_ONLY", "")
PART = os.environ.get("MUSICTL_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
WORK = {"Pad": "drawing", "Flip": "flip"}


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


def _quiet(rate=8000):
    """A second of tone, four of silence, a second of tone, six of silence:
    a loop's ends in the quiet have nothing but the ground beside them."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    on = lambda i: i < rate or 5 * rate <= i < 6 * rate
    w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 220 * i / rate)) if on(i) else 0)
                           for i in range(12 * rate)))
    w.close()
    return buf.getvalue()


QUIET = {"name": "quiet.wav", "mimeType": "audio/wav", "buffer": _quiet()}
# A 55Hz tone at a real song's rate: it crosses zero every 1/110s, exactly.
LOW = {"name": "low.wav", "mimeType": "audio/wav", "buffer": _wav(8.0, rate=44100, hz=55.0)}
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
# THE VIEW AT REST. It eases toward where it belongs, each frame counted as
# 64ms at most (lib/musictimeline.js, so a frame after a long pause does not
# jump), so where frames come further apart than that the glide takes longer
# than it does here. A row about where the view LANDS reads it once it has
# stopped: the same reading three frames running, or after 4s. (Main red
# after #709, the postgres machines: at 512x the view was read 3px short of
# where it settles, 500ms after the step.)
SETTLED = """() => new Promise(done => { const el = document.getElementById('musicTimeline'); let last = el.dataset.view, n = 0; const t0 = performance.now();
  (function tick() { const v = el.dataset.view; n = v === last ? n + 1 : 0; last = v;
    if (n >= 3 || performance.now() - t0 > 4000) done(v); else requestAnimationFrame(tick); })(); })"""
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


def editor(b, name, path, *, drawn=True, song=TWELVE, opts=DESK, door=None, ctx=None):
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
    if door:
        set_door(pg, door)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = (len(song["buffer"]) - 44) / struct.unpack("<I", song["buffer"][28:32])[0]   # its byte rate
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def set_door(pg, want):
    """One of the drawer's doors open by its tile, as a person opens it: the
    Restart view and Cut on silence are in Restart, the typed times and their
    - and + in Exact times."""
    t = f'#musicDoors .dp-tile[data-dp="{want}"]'
    if pg.get_attribute(t, "aria-expanded") != "true":
        pg.click(t)
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
        # A mark is painted 3px wide at least (a page's 6), and one that would
        # end past where the drawing ends moves back to end on it: the Pad's
        # last stroke here is one dot, at the drawing's very end.
        c, pg, errs = editor(b, _n, _p)
        if _n == "Pad":
            pg.evaluate(LONGDRAW, 4)
            want = [k * 1.0 for k in range(5)]
        else:
            want = [0.0, 8 / 12, 16 / 12]
        pg.evaluate(SET, {"s": 1.0, "e": 5.0, "xf": 0, "tempo": None})
        pg.wait_for_timeout(700)
        m = pg.evaluate(PAINTED, "musicTimeline")
        secs = pg.evaluate(DRAWN[_n])
        got = [x for x in m["marks"] if x[2] == 0] if m else []
        stop = at(m["view"], m["w"], 1.0 + secs) if m else 0
        wx = [round(min(at(m["view"], m["w"], 1.0 + t), stop - max(g[1] - g[0], 3 if _n == "Pad" else 6)), 2)
              for t, g in zip(want, got)] if m else []
        check(f"{_n}: the lane's marks sit where the {WORK[_n]} plays, from the loop's start, one that would run past its end ending on it",
              m is not None and len(got) == len(want) and all(abs(g[0] - x) < 0.6 for g, x in zip(got, wx)),
              f"marks at {[g[0] for g in got]}, want {wx}")
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
        # Held near an edge that already shows the song's start, nothing is
        # past it to show: the view holds still and the start stays under the
        # finger. On a phone at 1x the song's start sits inside the edge's
        # zone, and a start held near where the music begins ran off to 0:00
        # (the owner: "It snaps back to empty space"). The loop is placed so
        # the song begins a few pixels in from the edge, inside its zone.
        _sp = framing({"s": 0.0, "e": 2.0}, pg.evaluate(DRAWN[_n]))[1]
        pg.evaluate(SET, {"s": 0.09 * _sp - 0.02, "e": 0.09 * _sp - 0.02 + 2.0})
        pg.wait_for_timeout(700)
        st, v0 = pg.evaluate(BOX, "#musicTlStage"), pg.evaluate(VIEW)
        hs_ = pg.evaluate(BOX, "#tlStart")
        hx, hy = hs_["x"] + hs_["w"] / 2, hs_["y"] + hs_["h"] / 2
        song0 = at(v0, st["w"], 0.0)                       # where the song begins, from the stage's left
        fx = song0 + 3                                     # over the song, inside the edge's zone
        drag(pg, hx, hy, st["x"] + fx, hy, steps=6, up=False)
        fr = pg.evaluate(FRAMES, 700)
        pg.mouse.up(); pg.wait_for_timeout(300)
        under = at(fr[-1][1], st["w"], fr[-1][2])
        moved = max(abs(f[1][0] - fr[0][1][0]) + abs(f[1][1] - fr[0][1][1]) for f in fr)   # across the hold
        check(f"{_n}: held near the edge that already shows the song's start, the view holds still and the start stays under the finger",
              v0[0] < 0 and fx < 28 and moved < 1e-4 and abs(under - fx) < 1.0 and fr[-1][2] > 0.002,
              f"the song begins {song0:.1f}px in, the finger {fx:.1f}px in; the view moved {moved:.4f}s; "
              f"the start {fr[-1][2]:.3f}s, {under:.1f}px in")
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

    print("\nMUSIC TIMELINE — the ends' grips, at their foot")
    # What is on top, asked of the page at every other pixel beside each line
    # (3 to 14px either side, its own pixels left out) from the song's top to
    # 10px above its foot: never the grip. Then a point of the tab below the
    # song's edge (the tab shows there), the whole song's line under the line
    # (the end's: an end reaches 26px below its tab, over the line, and the
    # line has the press beside it), and the boxes for the words. What is on top is
    # what is painted only while the grip can be hit, so that is asked too.
    GRIPS = """() => { const st = document.getElementById('musicTlStage').getBoundingClientRect(), wl = document.getElementById('musicTlWhole'),
        w = wl.getBoundingClientRect(), out = {};
      for (const id of ['tlStart', 'tlEnd']) {
        const h = document.getElementById(id), r = h.getBoundingClientRect(), g = h.querySelector('.mt-tl-grip'), line = r.left + r.width / 2;
        const isGrip = (e) => !!e && !!g && (e === g || g.contains(e));
        let hits = 0, asked = 0;
        const lane = (document.getElementById('musicTimeline')._painted || {}).lane || 26;
        for (let y = st.top + lane + 8 + 2; y <= st.bottom - 10; y += 2)
          for (let dx = 3; dx <= 14; dx += 1) for (const sd of [-1, 1]) { asked++; if (isGrip(document.elementFromPoint(line + sd * dx, y))) hits++; }
        const gr = g.getBoundingClientRect(), ty = Math.min(gr.bottom - 2, st.bottom + 5), under = document.elementFromPoint(line, w.top + w.height / 2);
        out[id] = { hits: hits, asked: asked, hit: getComputedStyle(g).pointerEvents !== 'none' && getComputedStyle(g).visibility === 'visible',
                    line: line, x: gr.left + gr.width / 2, y: ty, below: isGrip(document.elementFromPoint(line, ty)),
                    top: gr.top, bottom: gr.bottom, edge: st.bottom, wholeTop: w.top, end: !!under && (under === h || h.contains(under)) };
      }
      return out; }"""
    for _n, _p in eds("grip"):
        for face, opts in (("a phone", PHONE), ("a desk", DESK)):
            c, pg, errs = editor(b, _n, _p, opts=opts)
            pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
            into_view(pg, "#musicTimeline")
            pg.wait_for_timeout(600)
            g = pg.evaluate(GRIPS)
            ends = ("tlStart", "tlEnd")
            check(f"{_n}, {face}: each end's grip sits at its foot: beside either line, over the song, nothing on top is the grip",
                  all(g[i]["asked"] > 300 and g[i]["hits"] == 0 and g[i]["hit"] for i in ends),
                  "; ".join(f"{i}: the grip on top at {g[i]['hits']} of {g[i]['asked']} points beside the line (it can be hit: {g[i]['hit']})" for i in ends))
            check(f"{_n}, {face}: ...a tab that shows half under the song's edge and keeps clear of the whole song's line, and a tap under it, on that line, takes the end",
                  all(g[i]["below"] and g[i]["top"] < g[i]["edge"] < g[i]["bottom"] and g[i]["bottom"] <= g[i]["wholeTop"] - 2 and g[i]["end"] for i in ends),
                  "; ".join(f"{i}: shown below the edge {g[i]['below']}, the tab {g[i]['top']:.1f}-{g[i]['bottom']:.1f} over the edge at {g[i]['edge']:.1f},"
                            f" the whole line from {g[i]['wholeTop']:.1f}, the end under it {g[i]['end']}" for i in ends))
            # The tab, pressed below the song's edge, drags its end (no tempo, so nothing settles).
            t0, v0, st = pg.evaluate(TRIM), pg.evaluate(VIEW), pg.evaluate(BOX, "#musicTlStage")
            drag(pg, g["tlEnd"]["x"], g["tlEnd"]["y"], g["tlEnd"]["x"] - 40, g["tlEnd"]["y"], steps=10)
            pg.wait_for_timeout(300)
            t1 = pg.evaluate(TRIM)
            moved = (t0["e"] - t1["e"]) / v0[1] * st["w"]
            check(f"{_n}, {face}: the tab, pressed below the song's edge, drags its end",
                  abs(moved - 40) < 1.5 and t1["s"] == t0["s"],
                  f"the end {t0['e']:.3f} -> {t1['e']:.3f}, {moved:.1f}px for a 40px drag; the start {t0['s']} -> {t1['s']}")
            check(f"{_n}, {face}: no page errors from the grips", not errs, "; ".join(errs[:2]))
            c.close()

    print("\nMUSIC TIMELINE — the loop's edges, sharp")
    # THE LOOP'S EDGE LINE IS SHARP (the owner's pick in the whole-drawer
    # mock, "1.5px sharp"): about 1.5px, rounded to the screen's own pixels,
    # and laid on whole ones. Read on the screenshot, at the screen's own
    # pixels, across each end placed between pixels in a quiet stretch of the
    # song, above its middle: the line is a run of the accent exactly as wide
    # as 1.5px rounds to on that screen (2 on a desk, 3 at 2x, 5 at 3x, the
    # owner's phone), and the column either side of it is the ground beyond,
    # not part-lit. It was 3px, its handle a fraction of a pixel off, so its
    # sides fell between pixels: 5 columns of the accent at 2x, and half-lit
    # ones either side.
    EDGE_AT = """() => { const st = document.getElementById('musicTlStage').getBoundingClientRect();
        return { top: st.top, acc: getComputedStyle(document.getElementById('musicTimeline')).getPropertyValue('--accent').trim(),
                 hands: ['tlStart', 'tlEnd'].map((id) => { const r = document.getElementById(id).getBoundingClientRect(); return r.left + r.width / 2; }) }; }"""

    def sharp(img, acc, n):
        W, H = img.size
        px = [[img.getpixel((i, j)) for j in range(H)] for i in range(W)]
        near = lambda a, z, t: max(abs(u - v) for u, v in zip(a, z)) <= t
        line = [i for i in range(W) if all(near(px[i][j], acc, 10) for j in range(H))]
        row = " ".join("%02x%02x%02x" % px[i][H // 2] for i in range(W))
        if not line or line != list(range(line[0], line[-1] + 1)) or line[0] < 2 or line[-1] > W - 3:
            return False, f"the accent's columns {line}: {row}"
        a, z = line[0], line[-1]
        flat = all(near(px[a - 1][j], px[a - 2][j], 3) and near(px[z + 1][j], px[z + 2][j], 3) for j in range(H))
        return len(line) == n and flat, f"{len(line)} columns of the accent ({n} wanted), the ground either side {'flat' if flat else 'part-lit'}: {row}"

    for _n, _p in eds("sharp"):
        got = []
        for face, opts in (("a desk", DESK), ("a 2x phone", PHONE), ("the owner's phone at 3x", dict(PHONE, device_scale_factor=3))):
            c, pg, errs = editor(b, _n, _p, opts=opts, song=QUIET)
            pg.evaluate(SET, {"s": 1.437, "e": 4.613, "xf": 0, "tempo": None})
            into_view(pg, "#musicTimeline")
            pg.wait_for_timeout(700)
            dpr = opts.get("device_scale_factor", 1)
            n = int(math.floor(1.5 * dpr + 0.5))
            e = pg.evaluate(EDGE_AT)
            acc = tuple(int(e["acc"][k:k + 2], 16) for k in (1, 3, 5))
            for which, x in zip(("start", "end"), e["hands"]):
                shot = pg.screenshot(clip={"x": math.floor(x) - 6, "y": math.floor(e["top"]) + 42, "width": 12, "height": 12})
                ok, why = sharp(Image.open(io.BytesIO(shot)).convert("RGB"), acc, n)
                got.append((ok, f"{face}, the {which} at {x:.2f}: {why}"))
            c.close()
        check(f"{_n}: the loop's edges are sharp lines: each a run of the accent as wide as 1.5px rounds to on the screen (2 pixels "
              "on a desk, 3 at 2x, 5 at 3x), the ground either side of it flat, read on the screenshot with each end between pixels",
              all(ok for ok, _ in got), "; ".join(w for _, w in got))

    print("\nMUSIC TIMELINE — magnify")
    MAG = """() => { const q = (id) => document.getElementById(id);
      return { said: q('musicTlMag').textContent, out: q('musicTlOut').disabled, in: q('musicTlIn').disabled,
               xo: q('musicTlOut').getBoundingClientRect().left, xi: q('musicTlIn').getBoundingClientRect().left }; }"""
    LADDER = ["1\u00d7", "2\u00d7", "4\u00d7", "8\u00d7", "16\u00d7", "32\u00d7", "64\u00d7", "128\u00d7", "256\u00d7", "512\u00d7"]

    def around(view, t, span):
        """How far a view is from `span` seconds with `t` in its middle, as a share of the span."""
        return max(abs(view[1] - span), abs(view[0] + view[1] / 2 - t)) / span

    def zoomed(pg, n, m):
        """The seconds across at `m`x for the loop as it is now: its framing over `m`."""
        return framing(pg.evaluate(TRIM), pg.evaluate(DRAWN[n]))[1] / m

    def mag_to(pg, want):
        for _ in range(len(LADDER) + 1):
            m = pg.evaluate(MAG)
            if m["said"] == want or m["said"] not in LADDER:
                return
            up = LADDER.index(want) > LADDER.index(m["said"])
            if m["in" if up else "out"]:
                return       # stopped short of it: the rows say where it is
            pg.click("#musicTlIn" if up else "#musicTlOut")
            pg.wait_for_timeout(60)

    def press(pg, sel):
        """A real click on a magnify button, or none when it is disabled."""
        if pg.evaluate("(s) => document.querySelector(s).disabled", sel):
            return False
        pg.click(sel)
        return True

    for _n, _p in eds("mag"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(600)
        f0 = framing(pg.evaluate(TRIM), pg.evaluate(DRAWN[_n]))
        said, views, loops = [pg.evaluate(MAG)], [], []
        for k in range(len(LADDER) - 1):
            if not press(pg, "#musicTlIn"):
                break
            pg.wait_for_timeout(120)
            pg.evaluate(SETTLED)
            said.append(pg.evaluate(MAG)); views.append(pg.evaluate(VIEW)); loops.append(pg.evaluate(TRIM))
        for k in range(len(views)):
            press(pg, "#musicTlOut"); pg.wait_for_timeout(80)
        back = pg.evaluate(MAG)
        check(f"{_n}: magnify steps 1x to 512x and says the rung, each button stopping at its end of the ladder",
              [m["said"] for m in said] == LADDER and said[0]["out"] and not said[0]["in"] and said[-1]["in"] and not said[-1]["out"]
              and all(not m["in"] and not m["out"] for m in said[1:-1]) and back["said"] == "1\u00d7" and back["out"],
              f"{[m['said'] for m in said]}; at 1x out {said[0]['out']}, in {said[0]['in']}; at 512x in {said[-1]['in']}; back to {back['said']}")
        # Its words grow from "1x" to "512x": - and + stay where they are.
        moved = max(max(abs(m["xo"] - said[0]["xo"]), abs(m["xi"] - said[0]["xi"])) for m in said)
        check(f"{_n}: ...and - and + stay where they are on every rung, the rung's words as wide as the widest",
              len(said) == len(LADDER) and moved <= 0.25,
              f"over {len(said)} rungs, - and + moved {moved:.2f}px at most")
        off = [around(v, 2.0, f0[1] / 2 ** (k + 1)) for k, v in enumerate(views)]
        check(f"{_n}: each rung frames the loop over that many, the start in the middle, and the loop never moves for it",
              off and max(off) < 2e-3 and all(l["s"] == 2.0 and l["e"] == 5.0 for l in loops),
              f"the framing {f0[1]:.3f}s; at 2x..512x off by {[round(o, 5) for o in off]} of a span;"
              f" the loop {loops[-1]['s'] if loops else None}-{loops[-1]['e'] if loops else None}")
        # A step glides there, read on every frame from the click.
        pg.wait_for_timeout(700)
        pg.evaluate("() => { window.__fr = []; const tl = document.getElementById('musicTimeline'), t0 = performance.now();"
                    " (function f() { window.__fr.push((tl.dataset.view || '').split(' ').map(Number)); if (performance.now() - t0 < 600) requestAnimationFrame(f); })(); }")
        press(pg, "#musicTlIn")
        pg.wait_for_timeout(700)
        fr = [v[1] for v in pg.evaluate("() => window.__fr")]
        goal = f0[1] / 2
        gap = [abs(sp - goal) for sp in fr]
        g0 = gap[0] if gap else 0
        way = [g for g in gap if 2e-3 * goal < g < g0 - 2e-3 * goal]
        # Each frame's share of the way, until it is there: the view is read
        # to 4 places, so the last frames' steps are the rounding's.
        # None at all (nothing to glide, or a jump) reads as a jump.
        shares = [(gap[i] - gap[i + 1]) / g0 for i in range(len(gap) - 1) if gap[i] > 2e-3 * goal] if g0 else []
        shares = shares or [1.0]
        check(f"{_n}: a step glides there, frame by frame",
              g0 > 0.3 * goal and len(way) >= 4 and max(shares) <= 0.7 and min(shares) > -1e-6 and gap[-1] < 2e-3 * goal,
              f"from {fr[0] if fr else None:.3f}s to {goal:.3f}s: {len(way)} frames on the way, the most in a frame {max(shares):.2f} of it,"
              f" the least {min(shares):.4f}")
        # A tap on an end's handle, nothing moved, makes it the end zoomed around.
        press(pg, "#musicTlOut"); pg.wait_for_timeout(700)
        he = pg.evaluate(BOX, "#tlEnd")
        pg.mouse.click(he["x"] + he["w"] / 2, he["y"] + he["h"] / 2)
        pg.wait_for_timeout(300)
        press(pg, "#musicTlIn"); pg.wait_for_timeout(700)
        vt, tt = pg.evaluate(VIEW), pg.evaluate(TRIM)
        check(f"{_n}: a tap on an end's handle makes it the end zoomed around",
              around(vt, tt["e"], f0[1] / 2) < 2e-3 and abs(tt["s"] - 2.0) < 1e-9 and abs(tt["e"] - 5.0) < 1e-9,
              f"the loop {tt['s']:.3f}-{tt['e']:.3f}; at 2x the view {vt}, its middle {vt[0] + vt[1] / 2:.3f}")
        check(f"{_n}: no page errors from magnify", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("mag"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **DESK))
        c, pg, errs = editor(b, _n, _p, ctx=c)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(400)
        f0 = framing(pg.evaluate(TRIM), pg.evaluate(DRAWN[_n]))
        press(pg, "#musicTlIn")
        fr = pg.evaluate(FRAMES, 200)
        off = [around(v[1], 2.0, f0[1] / 2) for v in fr]
        check(f"{_n}: under Reduce Motion a step is there at once",
              off and max(off) < 2e-3, f"off by {[round(o, 4) for o in off[:4]]} of a span on the first frames")
        c.close()
    for _n, _p in eds("mag"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 2.0, "e": 5.0, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(600)
        f0 = framing(pg.evaluate(TRIM), pg.evaluate(DRAWN[_n]))
        mag_to(pg, "8\u00d7"); pg.wait_for_timeout(700)
        span = f0[1] / 8
        st, v0 = pg.evaluate(BOX, "#musicTlStage"), pg.evaluate(VIEW)
        hs = pg.evaluate(BOX, "#tlStart")
        hx, hy = hs["x"] + hs["w"] / 2, hs["y"] + hs["h"] / 2
        drag(pg, hx, hy, hx - 40, hy, steps=8, up=False)
        held, vh = pg.evaluate(TRIM), pg.evaluate(VIEW)
        sx = at(vh, st["w"], held["s"])
        check(f"{_n}: zoomed in, an end follows the finger at the zoom while the view holds still",
              abs(sx - (hx - 40 - st["x"])) < 1.0 and max(abs(a - b_) for a, b_ in zip(v0, vh)) < 1e-4 and abs(vh[1] - span) < 1e-3 * span,
              f"the start at {sx:.1f}px under a finger at {hx - 40 - st['x']:.1f}px; view {v0} -> {vh} (8x is {span:.4f}s)")
        # Held at the left edge, then the right: the view slides along at the zoom.
        pg.mouse.move(st["x"] + 3, hy, steps=4)
        left = pg.evaluate(FRAMES, 600)
        pg.mouse.move(st["x"] + st["w"] - 3, hy, steps=10)
        right = pg.evaluate(FRAMES, 600)
        lv, rv = [f[1][0] for f in left], [f[1][0] for f in right]
        under_l = at(left[-1][1], st["w"], left[-1][2]); under_r = at(right[-1][1], st["w"], right[-1][2])
        check(f"{_n}: zoomed in, held at either edge, the view slides along at the zoom, the end under the finger",
              lv[-1] < lv[0] - 0.05 * span and all(b_ <= a + 1e-9 for a, b_ in zip(lv, lv[1:]))
              and rv[-1] > rv[0] + 0.05 * span and all(b_ >= a - 1e-9 for a, b_ in zip(rv[3:], rv[4:]))
              and max(abs(f[1][1] - span) for f in left + right) < 1e-3 * span and abs(under_l - 3) < 2.0 and abs(under_r - (st["w"] - 3)) < 2.0,
              f"left edge {lv[0]:.3f} -> {lv[-1]:.3f}s, then right {rv[0]:.3f} -> {rv[-1]:.3f}s; span {span:.4f}s throughout;"
              f" the start {under_l:.1f}px and {under_r:.1f}px from the left")
        pg.mouse.up()
        after = pg.evaluate(FRAMES, 900)
        # The loop is longer now, and so is its framing over 8.
        span = zoomed(pg, _n, 8)
        gap = [around(f[1], f[2], span) for f in after]
        shares = [(gap[i] - gap[i + 1]) / gap[0] for i in range(len(gap) - 1) if gap[i] > 2e-3] if gap and gap[0] else []
        shares = shares or [1.0]
        landed = next((i for i, g in enumerate(gap) if g < 2e-3), None)
        check(f"{_n}: let go, the view glides back with that end in the middle, frame by frame",
              gap[0] > 0.2 and landed is not None and landed >= 4 and max(shares) <= 0.7 and min(shares) > -1e-6,
              f"from {gap[0]:.2f} of a span off: in the middle on frame {landed}, the most in a frame {max(shares):.2f}, the least {min(shares):.4f}")
        # A finger on the song at the zoom: the song slides under it, and the
        # end zoomed around stays where it is on screen.
        pg.wait_for_timeout(300)
        t0, v0, h0 = pg.evaluate(TRIM), pg.evaluate(VIEW), pg.evaluate(HANDS)
        sy = st["y"] + st["h"] * 0.65
        drag(pg, st["x"] + st["w"] * 0.25, sy, st["x"] + st["w"] * 0.25 - 60, sy, up=False)
        t1, h1 = pg.evaluate(TRIM), pg.evaluate(HANDS)
        pg.mouse.up()
        slid = pg.evaluate(FRAMES, 500)
        h2 = pg.evaluate(HANDS)
        moved = 60 / st["w"] * v0[1]
        check(f"{_n}: zoomed in, a finger on the song slides it under the finger at the zoom, the loop's ends staying put on screen",
              abs((t1["s"] - t0["s"]) - moved) < 0.05 * moved and abs((t1["e"] - t1["s"]) - (t0["e"] - t0["s"])) < 1e-6
              and max(abs(a - b_) for a, b_ in zip(h0, h1)) < 1 and max(abs(a - b_) for a, b_ in zip(h0, h2)) < 1
              and max(around(f[1], f[2], v0[1]) for f in slid) < 2e-3,
              f"60px left: the loop {t0['s']:.4f} -> {t1['s']:.4f} (want +{moved:.4f}s); handles {h0} -> {h1} -> {h2};"
              f" let go, the start off the middle by {max(around(f[1], f[2], v0[1]) for f in slid):.4f} of a span at most")
        # The end's own + in Exact times: the end is the one zoomed around now.
        set_door(pg, "exact")
        pg.click('.nudge-btn[data-which="end"][data-amount="1"]')
        pg.wait_for_timeout(900)
        t1, v1 = pg.evaluate(TRIM), pg.evaluate(VIEW)
        span = zoomed(pg, _n, 8)
        check(f"{_n}: the end's own - and + make it the end zoomed around",
              around(v1, t1["e"], span) < 2e-3 and pg.evaluate(MAG)["said"] == "8\u00d7",
              f"the end at {t1['e']:.3f}; view {v1}, its middle {v1[0] + v1[1] / 2:.3f}")
        # Put away and opened again, it stays; a new song is 1x on its start.
        browsing.pad_drawer_close(pg)
        browsing.pad_drawer(pg, "music")
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(900)
        kept, vk = pg.evaluate(MAG)["said"], pg.evaluate(VIEW)
        add(pg, SHORT)
        pg.evaluate(SET, {"s": 1.0, "e": 3.0})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(900)
        fresh, vf = pg.evaluate(MAG), pg.evaluate(VIEW)
        g = framing(pg.evaluate(TRIM), pg.evaluate(DRAWN[_n]))
        check(f"{_n}: the zoom stays when the drawer is put away and opened again, and a new song starts at 1x on its start",
              kept == "8\u00d7" and around(vk, t1["e"], span) < 2e-3 and fresh["said"] == "1\u00d7" and fresh["out"]
              and abs(vf[0] - g[0]) < 2e-3 * g[1] and abs(vf[1] - g[1]) < 2e-3 * g[1],
              f"opened again: {kept}, view {vk}; a new song: {fresh['said']}, view {vf} (its framing {g[0]:.3f} {g[1]:.3f})")
        check(f"{_n}: no page errors from a finger at the zoom", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("mag"):
        # Held at the edge, the view slides only as far as the end can follow:
        # the start held at the left edge until it reaches the song's start.
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"s": 0.6, "e": 3.6, "xf": 0, "tempo": None})
        into_view(pg, "#musicTimeline")
        pg.wait_for_timeout(600)
        mag_to(pg, "8\u00d7"); pg.wait_for_timeout(700)
        st, v0 = pg.evaluate(BOX, "#musicTlStage"), pg.evaluate(VIEW)
        hs = pg.evaluate(BOX, "#tlStart")
        hx, hy = hs["x"] + hs["w"] / 2, hs["y"] + hs["h"] / 2
        drag(pg, hx, hy, st["x"] + 3, hy, steps=8, up=False)
        fr = pg.evaluate(FRAMES, 1400)
        pg.mouse.up()
        last, tail = fr[-1], [f[1][0] for f in fr[-12:]]
        under = at(last[1], st["w"], last[2])
        check(f"{_n}: zoomed in, held at the edge, the view slides only as far as the end can follow, and stops with it under the finger",
              v0[0] - last[1][0] > 0.3 and abs(last[2]) < 1e-9 and max(tail) - min(tail) < 1e-4 * last[1][1] and abs(under - 3) < 2.0,
              f"the view's left edge {v0[0]:.3f} -> {last[1][0]:.4f}s, over the last frames {min(tail):.4f}..{max(tail):.4f};"
              f" the start {last[2]:.3f}s, {under:.1f}px from the left under a finger at 3px")
        # Already as far as it goes, the start at the song's start: held at the
        # edge, the view holds still, with no jump.
        pg.wait_for_timeout(900)
        v1 = pg.evaluate(VIEW)
        hs = pg.evaluate(BOX, "#tlStart")
        hx, hy = hs["x"] + hs["w"] / 2, hs["y"] + hs["h"] / 2
        drag(pg, hx, hy, st["x"] + 3, hy, steps=8, up=False)
        fr = pg.evaluate(FRAMES, 800)
        pg.mouse.up()
        moved = max(abs(f[1][0] - v1[0]) for f in fr)
        check(f"{_n}: zoomed in, held at the edge past where the end can go, the view holds still",
              abs(fr[-1][2]) < 1e-9 and moved < 1e-4 * v1[1],
              f"the start {fr[-1][2]:.3f}s; the view's left edge {v1[0]:.4f}s, {moved:.5f}s from it at most while held")
        check(f"{_n}: no page errors at the edge", not errs, "; ".join(errs[:2]))
        c.close()
    print("\nMUSIC TIMELINE — zoomed in, inside the song")
    # ZOOMED IN, THE BOX STAYS INSIDE THE SONG (the owner: "when I magnify it
    # scoots the wave (beginning) to the middle ... when it is at the very
    # beginning it's a little strange"; of the mock, "all yes"): at 2x with
    # the loop at 0:00 the box starts the tab's 12px before the song, the
    # start off the middle; with the loop at the song's end and the end
    # touched last, it ends 12px past it; mid-song, the end in the middle.
    for _n, _p in eds("inside"):
        for label, opts in (("phone", PHONE), ("desk", DESK)):
            c, pg, errs = editor(b, _n, _p, opts=opts)
            pg.evaluate(SET, {"s": 0.0, "e": 2.0, "xf": 0, "tempo": None})
            into_view(pg, "#musicTimeline")
            pg.wait_for_timeout(600)
            mag_to(pg, "2\u00d7"); pg.wait_for_timeout(800); pg.evaluate(SETTLED)
            w, v0 = pg.evaluate(BOX, "#musicTlStage")["w"], pg.evaluate(VIEW)
            d = pg.evaluate("() => audioDuration")
            # The end touched at 1x, where it is in view, then zoomed in again.
            mag_to(pg, "1\u00d7"); pg.wait_for_timeout(500)
            pg.evaluate(SET, {"s": d - 2.0, "e": d}); pg.wait_for_timeout(800)
            he = pg.evaluate(BOX, "#tlEnd")
            pg.mouse.click(he["x"] + he["w"] / 2, he["y"] + he["h"] / 2); pg.wait_for_timeout(400)
            mag_to(pg, "2\u00d7"); pg.wait_for_timeout(800); pg.evaluate(SETTLED)
            v1, t1 = pg.evaluate(VIEW), pg.evaluate(TRIM)
            pg.evaluate(SET, {"s": d / 2 - 1.0, "e": d / 2 + 1.0}); pg.wait_for_timeout(800); pg.evaluate(SETTLED)
            v2 = pg.evaluate(VIEW)
            room0, room1 = 12 / w * v0[1], 12 / w * v1[1]
            check(f"{_n} ({label}): zoomed in, the box stays inside the song: at 0:00 it starts 12px before it, at the song's end it ends 12px past it, and mid-song the end is in the middle",
                  abs(v0[0] + room0) < 2e-3 * v0[1] and abs(v1[0] + v1[1] - (d + room1)) < 2e-3 * v1[1] and abs(t1["e"] - d) < 1e-9
                  and abs(v2[0] + v2[1] / 2 - (d / 2 + 1.0)) < 2e-3 * v2[1],
                  f"at 2x the loop at 0:00: the view from {v0[0]:.4f}s (want {-room0:.4f}); at the end, {v1[0] + v1[1]:.4f}s (want {d + room1:.4f});"
                  f" mid-song the middle {v2[0] + v2[1] / 2:.4f} (the end at {d / 2 + 1.0:.4f})")
            check(f"{_n} ({label}): no page errors zoomed in by the song's edges", not errs, "; ".join(errs[:2]))
            c.close()

    print("\nMUSIC TIMELINE — the magnet's own box, when there's room")
    # SNAP TO THE BEAT, THE MAGNET (the owner: "i do like the magnet having
    # it's own button. is there a way to have its own button if there's
    # room, but merge them if there's not enough room?"; the mock's C2):
    # its own box beside the taller button while the name keeps one line
    # with it there, the two boxes one where it would not. "Room" is the
    # name's one-line width, read here from a copy of it that never wraps,
    # against the room it has beside the magnet's own box.
    HEADFIT = """() => { const h = document.querySelector('.mt-tl-head'), n = document.getElementById('musicTlName');
      const r = document.createRange(); r.selectNodeContents(n);
      const one = n.cloneNode(true); one.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;max-width:none;width:auto';
      n.parentNode.appendChild(one); const want = one.getBoundingClientRect().width; one.remove();
      const R = (e) => e.getBoundingClientRect(), mag = R(h.querySelector('.mt-tl-mag')), sb = R(h.querySelector('.mt-tl-snapbox'));
      const tb = R(h.querySelector('.mt-tl-snapbox + .mt-tl-tallbox')), sn = R(document.getElementById('musicSnap')), tl = R(document.getElementById('musicTlTall'));
      const own = h.classList.contains('joined') ? null : h.querySelector('.mt-tl-namebox').getBoundingClientRect().width;
      return { joined: h.classList.contains('joined'), want: Math.round(want * 10) / 10, own: own && Math.round(own * 10) / 10,
               lines: new Set([...r.getClientRects()].map((q) => Math.round(q.top))).size, words: n.textContent,
               between: Math.round((sb.left - mag.right) * 10) / 10, boxes: Math.round((tb.left - sb.right) * 10) / 10,
               cells: Math.round((tl.left - sn.right) * 10) / 10, wide: Math.round(window.innerWidth) }; }"""
    for _n, _p in eds("head"):
        seen = []
        for w in (402, 390, 375, 360, 1280):
            opts = DESK if w == 1280 else dict(viewport={"width": w, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
            c, pg, errs = editor(b, _n, _p, opts=opts)
            into_view(pg, "#musicTimeline"); pg.wait_for_timeout(500)
            f = pg.evaluate(HEADFIT)
            if f["joined"]:
                # Closed up, the room it would have had beside its own box, read
                # once it is taken apart again by hand.
                pg.evaluate("() => document.querySelector('.mt-tl-head').classList.remove('joined', 'fitted')")
                f["own"] = pg.evaluate(HEADFIT)["own"]
            seen.append(f)
            check(f"{_n} at {w}px: the magnet has its own box exactly when the name keeps one line beside it, and otherwise one box with the taller button",
                  (not f["joined"]) == (f["want"] <= f["own"] + 0.5)
                  and (f["lines"] == 1 if not f["joined"] else True)
                  and abs(f["between"] - 10) < 0.6
                  and (abs(f["boxes"] - 10) < 0.6 if not f["joined"] else abs(f["boxes"]) < 0.6 and abs(f["cells"] - 2) < 0.6),
                  str(f))
            c.close()
        check(f"{_n}: across a phone's widths and a desk, both: its own box on a desk, closed up on a narrow phone",
              not seen[-1]["joined"] and seen[3]["joined"], str([(x["wide"], x["joined"], x["want"], x["own"]) for x in seen]))
    for _n, _p in eds("head"):
        if _n != "Pad":
            continue   # drawing on Flip closes the drawer; the glide is the one timeline's, its rows above Flip's too
        # The name grows as the drawing does: past the room, the boxes close up
        # over frames, not in one; under Reduce Motion, at once. The phone is
        # made just wide enough for the name as drawn to keep its line beside
        # the magnet's own box, from what a 402px phone leaves it, and the
        # drawing then runs over a minute ("1:05", two figures longer).
        for still in (False, True):
            ph = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
            ctx = waits.instrument(b.new_context(reduced_motion="reduce", **ph)) if still else None
            c, pg, errs = editor(b, _n, _p, opts=ph, ctx=ctx)
            into_view(pg, "#musicTimeline"); pg.wait_for_timeout(500)
            f0 = pg.evaluate(HEADFIT)
            if f0["joined"]:
                pg.evaluate("() => document.querySelector('.mt-tl-head').classList.remove('joined', 'fitted')")
                f0 = dict(f0, own=pg.evaluate(HEADFIT)["own"])
            fit_w = int(402 - f0["own"] + f0["want"] + 4) + 1
            pg.set_viewport_size({"width": fit_w, "height": 874}); pg.wait_for_timeout(600)
            before = pg.evaluate(HEADFIT)
            t = pg.evaluate(TRIM)
            pg.evaluate("""() => { window.__mg = []; const sn = document.getElementById('musicSnap'), t0 = performance.now();
              (function f() { window.__mg.push(sn.getBoundingClientRect().left); if (performance.now() - t0 < 700) requestAnimationFrame(f); })(); }""")
            if _n == "Pad":
                pg.evaluate(LONGDRAW, 65)
            else:
                pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 260})
            pg.evaluate(SET, {"s": t["s"], "e": t["e"]}); pg.wait_for_timeout(800)
            after, rec = pg.evaluate(HEADFIT), pg.evaluate("() => window.__mg")
            moved = [round(b2 - a2, 2) for a2, b2 in zip(rec, rec[1:]) if abs(b2 - a2) > 0.05]
            if not still:
                check(f"{_n}: the name grown past the room, the boxes close up over frames, the magnet keeping its place beside the zoom",
                      not before["joined"] and before["lines"] == 1 and after["joined"] and len(moved) >= 4 and max(abs(m) for m in moved) <= 8
                      and abs(after["between"] - 10) < 0.6 and after["words"].endswith("\u00b7 1:05"),
                      f"at {fit_w}px: before {before['words']!r} {before['joined']}, after {after['words']!r} {after['joined']}; the magnet's steps {moved}")
            else:
                check(f"{_n}: ...under Reduce Motion, at once", not before["joined"] and after["joined"] and len(moved) <= 1,
                      f"at {fit_w}px: the magnet's steps {moved}")
            check(f"{_n}: no page errors as the magnet's box closes up{' under Reduce Motion' if still else ''}", not errs, "; ".join(errs[:2]))
            c.close()

    for _n, _p in eds("mag"):
        # Past a block a column the song is drawn from its samples: a single
        # loud sample shows in the column that holds it and in no other.
        c, pg, errs = editor(b, _n, _p, drawn=False, song=None)
        r = pg.evaluate("""() => { const sr = 8000, b = new AudioBuffer({ length: sr, numberOfChannels: 1, sampleRate: sr }), d = b.getChannelData(0);
          for (let i = 0; i < d.length; i++) d[i] = 0.01; d[1000] = 1;
          const T = window.SkriblMusicTimeline, P = T.peaksOf(b), at = (s) => s / sr;
          return { on: T.peakOf(P, at(990), at(1010)), beside: T.peakOf(P, at(1010), at(1050)), before: T.peakOf(P, at(960), at(990)) }; }""")
        check(f"{_n}: zoomed past a block a column, the song is drawn from its samples",
              r["on"] > 0.99 and r["beside"] < 0.02 and r["before"] < 0.02,
              f"the column with the loud sample {r['on']:.3f}, the columns beside it {r['beside']:.3f} and {r['before']:.3f} (its block of 128 holds them all)")
        c.close()
    for _n, _p in eds("mag"):
        for theme in ("light", "dark"):
            c = waits.instrument(b.new_context(color_scheme=theme, **PHONE))
            c, pg, errs = editor(b, _n, _p, ctx=c)
            into_view(pg, "#musicTimeline")
            mag_to(pg, "8\u00d7"); pg.wait_for_timeout(600)
            r = pg.evaluate("""() => {
              const parse = (s) => { const m = s.match(/^rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
              const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a }; };
              const ground = (el) => { const l = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { l.push(c); if (c.a >= 0.999) break; } }
                let acc = { r: 255, g: 255, b: 255, a: 1 }; for (let i = l.length - 1; i >= 0; i--) acc = over(l[i], acc); return acc; };
              const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
              const ratio = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
              const ink = (el) => { const g = ground(el); return ratio(over(parse(getComputedStyle(el).color), g), g); };
              const q = (s) => document.querySelector(s), n = q('#musicTlName').getBoundingClientRect(), m = q('.mt-tl-mag').getBoundingClientRect(), st = q('#musicTlStage').getBoundingClientRect();
              // The taller box after it ends the line (verify_musictall).
              const k = q('.mt-tl-tallbox').getBoundingClientRect();
              return { level: ink(q('#musicTlMag')), glyph: Math.min(ink(q('#musicTlIn')), ink(q('#musicTlOut'))),
                       middle: (m.top + m.bottom) / 2 - (n.top + n.bottom) / 2, right: k.right - st.right, after: k.left - m.right, below: st.top - m.bottom }; }""")
            check(f"{_n}: magnify sits at the end of the name's line, its middle on the name's, and its words and glyphs read against what is behind them ({theme})",
                  abs(r["middle"]) <= 0.5 and abs(r["right"]) <= 0.5 and r["after"] >= 4 and r["below"] >= 4 and r["level"] >= 4.5 and r["glyph"] >= 3,
                  f"middle {r['middle']:+.2f}px from the name's, the taller box after it {r['after']:.1f}px on, its right edge {r['right']:+.2f}px from the song's,"
                  f" {r['below']:.1f}px over the lane; the level {r['level']:.2f}:1, the glyphs {r['glyph']:.2f}:1")
            c.close()

    print("\nMUSIC TIMELINE — close in, the wave itself")
    # THE SONG AS PAINTED, read back from the canvas: the middle line found by
    # its paint, the rows inked across nine columns in ten (the wave crosses
    # any one row only near its zeros; loudness has no line, and there the
    # stage's middle stands in); then per device column the first and last row
    # of ink, the line's rows left out, against the ground at the top of that
    # column, and the colours at the line and beside it. Asked of the pixels,
    # not of what the timeline says it drew.
    WAVEPX = """() => {
      const tl = document.getElementById('musicTimeline'), cv = document.getElementById('musicTlCanvas'), P = tl._painted || {};
      const w = cv.clientWidth, hh = cv.clientHeight, dpr = cv.width / w, W = cv.width;
      const img = cv.getContext('2d').getImageData(0, 0, W, cv.height).data;
      const at = (c, r) => { const i = (r * W + c) * 4; return [img[i], img[i + 1], img[i + 2]]; };
      const far = (a, b) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]);
      const sTop = (P.lane || 26) + 8, r0 = Math.ceil((sTop + 3) * dpr), r1 = Math.floor((hh - 3) * dpr);
      const c0 = Math.ceil(12 * dpr), c1 = W - 12 * dpr;
      let mid = sTop + (hh - sTop) / 2 + 3, line = null;
      if (P.song === 'wave' || P.song === 'samples') {
        const runs = []; let run = null;
        for (let r = r0 + 1; r <= r1; r++) {
          let n = 0, k = 0;
          for (let c = c0; c < c1; c++) { k++; if (far(at(c, r), at(c, r0)) > 30) n++; }
          if (n >= 0.9 * k) { if (run && run[1] === r - 1) run[1] = r; else runs.push(run = [r, r]); }
        }
        runs.sort((a, b) => Math.abs((a[0] + a[1] + 1) / 2 - mid * dpr) - Math.abs((b[0] + b[1] + 1) / 2 - mid * dpr));
        if (runs.length) { line = runs[0]; mid = (line[0] + line[1] + 1) / 2 / dpr; }
      }
      const m0 = line ? line[0] - 2 : Math.floor((mid - 1.5) * dpr), m1 = line ? line[1] + 2 : Math.ceil((mid + 1.5) * dpr);
      const lr = line ? line[0] : Math.floor(mid * dpr), cols = [];
      for (let c = c0; c < c1; c++) {
        const g = at(c, r0); let top = null, bot = null, inkTop = null;
        for (let r = r0 + 1; r <= r1; r++) {
          if (r >= m0 && r <= m1) continue;
          if (far(at(c, r), g) > 60) { if (top === null) { top = r; inkTop = at(c, r); } bot = r; }
        }
        cols.push({ c, top, bot, g, ink: inkTop, line: at(c, lr),
                    beside: at(c, top !== null && top < lr ? Math.min(r1, lr + Math.round(5 * dpr)) : Math.max(r0, lr - Math.round(5 * dpr))) });
      }
      return { dpr, w, mid, lr, m0, m1, line, song: P.song || null, zero: P.zero != null ? P.zero : null,
               view: (tl.dataset.view || '').split(' ').map(Number), trim: [trimStart, trimEnd], cols };
    }"""

    def lum(c):
        f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = (f(v / 255) for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def sides(px):
        """Each column with ink: above the middle line only, below only, or both."""
        out = []
        for col in px["cols"]:
            if col["top"] is None:
                continue
            up, down = col["top"] < px["m0"], col["bot"] > px["m1"]
            out.append((col["c"], "both" if up and down else "above" if up else "below"))
        return out

    def one_side(px):
        sd = sides(px)
        return sum(1 for _, k in sd if k != "both") / max(1, len(sd)), len(sd)

    def symmetric(px):
        """In the columns with ink both sides, how far the ink's two ends are from even about the line, at most (device px)."""
        lr = px["mid"] * px["dpr"]
        return max([abs((lr - col["top"]) - (col["bot"] - lr)) for col in px["cols"] if col["top"] is not None
                    and col["top"] < px["m0"] and col["bot"] > px["m1"]] or [0])

    def crossings(px):
        """Where the painted wave goes from one side of the line to the other, in CSS px."""
        out, last = [], None
        for c, k in sides(px):
            if k == "both":
                continue
            if last and last[1] != k:
                out.append((last[0] + c) / 2 / px["dpr"])
            last = (c, k)
        return out

    def zeros(px):
        """Where the 55Hz tone crosses zero, every 1/110s, in CSS px, inside the columns read."""
        v0, span, w = px["view"][0], px["view"][1], px["w"]
        k0, k1 = math.ceil(v0 * 110), math.floor((v0 + span) * 110)
        return [x for x in ((k / 110 - v0) / span * w for k in range(k0, k1 + 1)) if 14 <= x <= w - 14]

    for _n, _p in eds("wave"):
        for theme in ("dark", "light"):
            ctx = waits.instrument(b.new_context(color_scheme=theme, **PHONE))
            c, pg, errs = editor(b, _n, _p, song=LOW, ctx=ctx)
            pg.evaluate(SET, {"s": 2.003, "e": 6.0, "xf": 0, "tempo": None})
            into_view(pg, "#musicTimeline")
            pg.wait_for_timeout(600)
            shot = {}
            for want in ("8×", "16×", "32×", "64×", "128×"):
                mag_to(pg, want); pg.wait_for_timeout(700)
                shot[want] = pg.evaluate(WAVEPX)
            spp = {k: v["view"][1] / v["w"] * 44100 for k, v in shot.items()}
            a8, a16 = one_side(shot["8×"]), one_side(shot["16×"])
            check(f"{_n} ({theme}): while a point holds 64 samples or more the song is loudness, the same above and below the middle",
                  spp["8×"] >= 64 and shot["8×"]["song"] == "loudness" and a8[1] > 50 and a8[0] < 0.05 and symmetric(shot["8×"]) <= 2,
                  f"at 8x, {spp['8×']:.0f} samples a point: {shot['8×']['song']}, {a8[0] * 100:.0f}% of {a8[1]} columns on one side only, uneven by {symmetric(shot['8×'])}px at most")
            check(f"{_n} ({theme}): ...and under 64 samples a point, the wave itself, which crosses the middle line",
                  spp["16×"] < 64 and shot["16×"]["song"] == "wave" and a16[1] > 50 and a16[0] > 0.5 and len(crossings(shot["16×"])) >= 3,
                  f"at 16x, {spp['16×']:.0f} samples a point: {shot['16×']['song']}, {a16[0] * 100:.0f}% of {a16[1]} columns on one side only,"
                  f" {len(crossings(shot['16×']))} crossings painted")
            # The line at the wave's zero: halfway between its crests and troughs.
            off = []
            for want in ("16×", "128×"):
                px = shot[want]
                ink = [col for col in px["cols"] if col["top"] is not None]
                crest, trough = min(col["top"] for col in ink), max(col["bot"] for col in ink)
                line = (px["line"][0] + px["line"][1] + 1) / 2 if px["line"] else None
                off.append((want, (crest + trough + 1) / 2, line))
            check(f"{_n} ({theme}): the middle line sits at the wave's zero, halfway between its crests and its troughs",
                  all(l is not None and abs(m - l) <= 1.0 for _, m, l in off),
                  "; ".join(f"at {w_}: the wave's middle row {m:.1f}, the line's {l if l is None else round(l, 1)} (device px)" for w_, m, l in off))
            # The wave crosses the line where the song crosses zero.
            err = []
            for want in ("32×", "128×"):
                got, want_x = crossings(shot[want]), zeros(shot[want])
                err.append((want, len(want_x), max([min(abs(g - x) for g in got) for x in want_x] or [99]) if got else 99))
            check(f"{_n} ({theme}): ...and the wave crosses it where the song crosses zero, to the pixel",
                  all(n_ >= 1 and e <= 1.0 for _, n_, e in err),
                  "; ".join(f"at {w_}: {n_} zeros in view, the painted crossing {e:.2f}px from each at most" for w_, n_, e in err))
            # The middle line against the song's ground, inside the loop and past it.
            px = shot["32×"]
            xs = (px["trim"][0] - px["view"][0]) / px["view"][1] * px["w"] * px["dpr"]
            calm = [col for col in px["cols"] if col["top"] is not None and (col["bot"] < px["m0"] - 6 * px["dpr"] or col["top"] > px["m1"] + 6 * px["dpr"])]
            inside = [ratio(col["line"], col["beside"]) for col in calm if col["c"] > xs + 4]
            outside = [ratio(col["line"], col["beside"]) for col in calm if col["c"] < xs - 4]
            check(f"{_n} ({theme}): the middle line reads 3:1 and up against the song's ground, inside the loop and past it",
                  inside and outside and min(inside) >= 3.0 and min(outside) >= 3.0,
                  f"inside {f'{min(inside):.2f}:1' if inside else 'nothing to read'} over {len(inside)} columns,"
                  f" past the loop {f'{min(outside):.2f}:1' if outside else 'nothing to read'} over {len(outside)}")
            # Past the loop the wave is dimmed, as the bars are.
            wi = [ratio(col["ink"], col["g"]) for col in calm if col["c"] > xs + 4]
            wo = [ratio(col["ink"], col["g"]) for col in calm if col["c"] < xs - 4]
            check(f"{_n} ({theme}): ...and past the loop the wave is dimmed, as the bars are",
                  wi and wo and max(wo) < 0.6 * max(wi) and max(wi) >= 2.5,
                  f"the wave's edge {max(wi) if wi else 0:.2f}:1 in the loop, {max(wo) if wo else 0:.2f}:1 past it")
            check(f"{_n} ({theme}): under 8 samples a point, the samples themselves, joined",
                  spp["128×"] < 8 and shot["128×"]["song"] == "samples" and spp["64×"] >= 8 and shot["64×"]["song"] == "wave",
                  f"at 64x {spp['64×']:.1f} samples a point: {shot['64×']['song']}; at 128x {spp['128×']:.1f}: {shot['128×']['song']}")
            check(f"{_n} ({theme}): no page errors close in", not errs, "; ".join(errs[:2]))
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
        c, pg, errs = editor(b, _n, _p, door="restart")
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
        c, pg, errs = editor(b, _n, _p, door="restart")
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
            set_door(pg, "restart")
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
        c, pg, errs = editor(b, _n, _p, door="restart")
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
        c, pg, errs = editor(b, _n, _p, door="restart")
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
        c, pg, errs = editor(b, _n, _p, door="restart")
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
