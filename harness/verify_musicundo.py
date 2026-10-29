#!/usr/bin/env python3
"""The music drawer's own Undo and Redo, the bin's Undo, and the ends' reach.

THE OWNER, of the music timeline: "sometimes when I go to drag something I
move the whole waveform. shouldn't there be an undo button on the editor
(just to go back to what it was before) and maybe a redo button too?"; of
the Undo, reach and Repeat page, "All yes": the drawer's own Undo and Redo
at the end of the one line under the timeline (A), every change to the loop,
in place of the Length door's eight-second Undo; Undo brings back a song the
bin took away; and the ends reach further, a near miss beside a tab moves
nothing, the whole song's line only on its own row, the nearer end wins.
One drawer (lib/musicdrawer.js) and one timeline (lib/musictimeline.js), so
every row runs on the Pad and on Flip.

WHAT IS ASKED, AND HOW IT IS READ
  * THE PAIR: at the end of the one line, in the zoom's box, each a 28px
    cell, painted where it sits (what is on top at its middle), named, its
    words its tooltip; greyed while there is nothing to take back or again,
    as the zoom's minus is at 1x. On a phone the line is two rows tall with
    or without a drawing, the pair in the middle; on a desk one row, as tall
    as the pair. There is one Undo: the Length door's own is gone. The
    arrows read at 3:1 or more on their cell, light and dark, phone and desk.
  * EVERY CHANGE IS A STEP, made as a person makes it (real presses, drags
    and keys): an end dragged, the song slid, a tap on the whole song's line,
    a Length card, Skribl's pick as the way back, a count in Beats, Beats in
    a bar, Smooth restart, Cut on silence, a nudge, a typed time, Tap the
    beat. Each is undone and done again as soon as it is made, Undo putting
    the loop back exactly as the change before left it (its ends, its
    restart, its cut, its beat), so a change that is not a step reds its own
    row and no other; then Undo all the way down and Redo all the way up.
  * ONE STEP: however far a drag goes, and however often a held finger
    moves the restart's length. An end let go and settled on the beat is
    one step with its glide; a change made while a settle still glides is a
    step of its own, from where the settle was going.
  * NOT STEPS: the zoom, the taller box, the magnet and Lock the length leave
    Undo greyed, and a step put back leaves the magnet and Lock as they are.
    A new song's pick is not a step; a new song starts a new history. A
    change after an Undo starts afresh, and what Redo held goes. As one of
    the pair runs out, the keyboard's place moves to the other.
  * THE BIN: the song goes at once and the note says so with an Undo, which
    brings the song back as it was, its loop and the loop's own Undo with it,
    and says "Song restored" with a Redo that takes it away again and offers
    the Undo again. The Pad's draft has it again (its bytes back in the
    store, the draft naming it); Flip's next save writes it again. New
    Skribl's clear has its own Undo and no bin note (the Pad's goes through
    the bin's own control; Flip's does not, so it cannot fail there).
  * THE REACH, read where a press lands (elementFromPoint) on a phone and a
    desk: 30px either side of an end's line, on the wave and by its tab, and
    16px below its tab, takes the end; 40px beside a tab moves nothing; the
    whole song's line takes a press on its own row and not 6px above it.
    Then real presses on a desk: 28px beside an end's line a drag takes the
    end; a near miss beside a tab moves nothing; and where the two ends are
    close, a press takes the nearer one.

Skribl's ears are off here (verify_musicears holds them to their songs, and
asks there that what Skribl does once it has listened is not a step).
"""
import io
import math
import os
import struct
import sys
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
    print("No assertions were executed. This is NOT evidence the loop's Undo takes anything back.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICUNDO_ONLY=Pad (or Flip) runs one editor, and
# MUSICUNDO_PART=pair (chain, one, notsteps, afresh, focus, bin, reach, press,
# ink) one part. A real run sets neither.
ONLY = os.environ.get("MUSICUNDO_ONLY", "")
PART = os.environ.get("MUSICUNDO_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def part(name):
    return not PART or PART == name


def eds(name):
    return EDITORS if part(name) else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
WORK = {"Pad": "drawing", "Flip": "animation"}
NOTE = {"Pad": "#toast", "Flip": "#flipChip"}


def _wav(seconds, rate=8000, bpm=120.0, f0=70.0):
    """A pulse on every beat: a song with a beat to snap to."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    p = 60.0 / bpm
    w.writeframes(b"".join(struct.pack("<h", int(16000 * math.sin(2 * math.pi * f0 * i / rate) * math.exp(-((i / rate) % p) * 9)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


SONG = {"name": "pulse.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
OTHER = {"name": "other.wav", "mimeType": "audio/wav", "buffer": _wav(8.0, f0=110.0)}
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
# A drawing: the Pad's strokes about 5.8s long, Flip's three pages held 8 frames at 12fps.
DRAW = {"Pad": """() => { strokes.length = 0; let t = 0;
  for (let k = 0; k < 5; k++) { for (let j = 0; j <= 10; j++) strokes.push({ x: 60 + j * 10, y: 60 + k * 30, color: '#7c5cff', size: 8, t: t + j * 45, start: j === 0 }); t += 600; }
  while (t < 5800) { strokes.push({ x: 300, y: 60 + (t % 700) / 3, color: '#7c5cff', size: 8, t: t, start: true }); t += 300; }
  updateDrawingTimeLabels(); }""",
        "Flip": """() => { frames.length = 0;
  for (let k = 0; k < 3; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); f.hold = 8; frames.push(f); }
  fps = 12; idx = 0; buildStrip(); render(); updateToolState(); }"""}
# The loop and the beat set as a draft would, never as a step.
SETUP = """(o) => { musicTempo = o.tempo; trimStart = o.s; trimEnd = o.e; loopCrossfadeMs = o.xf; loopCutOnSilence = o.cut;
  if (typeof setCrossfadeUI === 'function') setCrossfadeUI(); updateTrimUI(); }"""
FREE = {"tempo": {"bpm": 120, "phase": 0, "snap": False}, "s": 1.0, "e": 5.0, "xf": 250, "cut": True}
SNAPPING = {"tempo": {"bpm": 120, "phase": 0}, "s": 1.0, "e": 5.0, "xf": 250, "cut": True}
# The loop as a step keeps it, and the pair.
STATE = """() => { const u = document.getElementById('musicUndo'), r = document.getElementById('musicRedo'), tp = musicTempo;
  return { s: trimStart, e: trimEnd == null ? audioDuration : trimEnd, xf: loopCrossfadeMs, cut: !!loopCutOnSilence,
           tempo: tp ? { bpm: tp.bpm, phase: tp.phase, bar: tp.bar || 4 } : null, snap: !!tp && tp.snap !== false,
           undo: !!u && !u.disabled, redo: !!r && !r.disabled,
           track: (typeof musicData !== 'undefined' ? !!musicData : !!audioEl) && audioDuration > 0 }; }"""


def same(a, b):
    return (a is not None and b is not None and abs(a["s"] - b["s"]) < 1e-6 and abs(a["e"] - b["e"]) < 1e-6
            and a["xf"] == b["xf"] and a["cut"] == b["cut"] and a["tempo"] == b["tempo"])


def says(t):
    return f"{t['s']:.3f}-{t['e']:.3f} xf {t['xf']} cut {t['cut']} {t['tempo']}"


def editor(b, name, path, *, opts=DESK, scheme="light", drawn=True, song=SONG):
    c = waits.instrument(b.new_context(color_scheme=scheme, **opts))
    c.add_init_script(NO_EARS)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if drawn:
        pg.evaluate(DRAW[name])
    if song:
        add(pg, song)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def setup(pg, o):
    pg.evaluate(SETUP, o)
    pg.wait_for_timeout(150)
    timeline(pg)


def timeline(pg):
    pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })")
    browsing.wait_scroll_still(pg)
    pg.wait_for_timeout(150)


def tile(k):
    return f'#musicDoors .dp-tile[data-dp="{k}"]'


def set_door(pg, want):
    """A door open (its name) or every door shut (None), by the tiles, as a person does."""
    now = pg.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[aria-expanded=\"true\"]'); return t ? t.dataset.dp : null; }")
    if now == want:
        return
    pg.click(tile(want or now))
    pg.wait_for_timeout(350)
    browsing.wait_scroll_still(pg)


def press(pg, sel, door=None, ms=500):
    """A real click on a control, its door opened first: a control a broken
    build hides makes a row say so in red, not a timeout."""
    try:
        if door:
            set_door(pg, door)
        pg.click(sel, timeout=3000)
    except Exception:
        return False
    waits.settle(pg, ms)
    return True


def st(pg):
    return pg.evaluate(STATE)


GEOM = """() => { const q = (s) => document.querySelector(s), R = (e) => e.getBoundingClientRect();
  const sg = R(q('#musicTlStage')), wh = R(q('#musicTlWhole')), hs = R(q('#tlStart')), he = R(q('#tlEnd'));
  const gs = R(q('#tlStart .mt-tl-grip')), ge = R(q('#tlEnd .mt-tl-grip'));
  return { stage: [sg.left, sg.top, sg.right, sg.bottom], whole: [wh.left, wh.top, wh.right, wh.bottom],
           start: hs.left + hs.width / 2, end: he.left + he.width / 2, tab: [Math.max(gs.top, ge.top), Math.min(gs.bottom, ge.bottom)],
           tabMid: (gs.top + gs.bottom) / 2 }; }"""
# What a press at each point lands on: an end, the song (it slides), the
# whole song's line (it jumps), or nothing.
HIT = """(pts) => pts.map(([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return 'nothing';
  const h = e.closest('.mt-tl-handle'); if (h) return h.dataset.which;
  if (e.closest('#musicTlWhole')) return 'whole'; if (e.closest('#musicTlStage')) return 'song'; return 'nothing'; })"""


def drag(pg, x, y, dx, steps=10):
    pg.mouse.move(x, y)
    pg.mouse.down()
    for i in range(1, steps + 1):
        pg.mouse.move(x + dx * i / steps, y)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    waits.settle(pg, 500)


def grip(pg, which):
    return pg.evaluate("(w) => { const r = document.querySelector('#tl' + w + ' .mt-tl-grip').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }", which)


def slide_at(pg):
    """A point on the song, between the ends and out of their reach."""
    g = pg.evaluate(GEOM)
    if g["end"] - g["start"] < 110:
        return None
    return [(g["start"] + g["end"]) / 2, g["stage"][1] + (g["stage"][3] - g["stage"][1]) * 0.65]


def whole_at(pg):
    """A point on the whole song's line out of both ends' reach and away from the loop."""
    return pg.evaluate("""() => { const w = document.getElementById('musicTlWhole').getBoundingClientRect(),
        x = (id) => { const r = document.getElementById(id).getBoundingClientRect(); return r.left + r.width / 2; }, s = x('tlStart'), e = x('tlEnd');
      for (const f of [0.92, 0.85, 0.78, 0.7, 0.62]) { const px = w.left + w.width * f; if (Math.abs(px - s) > 45 && Math.abs(px - e) > 45) return [px, w.top + w.height / 2]; }
      return null; }""")


def note(pg, name):
    return pg.evaluate("""(sel) => { const t = document.querySelector(sel); if (!t) return null; const b = t.querySelector('button');
      return { words: (t.textContent || '').replace(b ? b.textContent : '', '').trim(), action: b ? b.textContent.trim() : null }; }""", NOTE[name])


def note_action(pg, name):
    try:
        pg.click(NOTE[name] + " button", timeout=3000)
    except Exception:
        return False
    waits.settle(pg, 500)
    return True


def bin_song(pg):
    """The bin's two taps, as a person makes them: the first asks, the second removes."""
    try:
        pg.click("#musicRemove", timeout=3000)
        pg.wait_for_timeout(200)
        pg.click("#musicRemove", timeout=3000)
    except Exception:
        return False
    waits.settle(pg, 400)
    return True


TAPS = """(n) => new Promise((done) => { const b = document.getElementById('musicTapBtn'); let k = 0;
  (function t() { b.click(); if (++k < n) setTimeout(t, 400); else done(); })(); })"""


with sync_playwright() as pw:
    b = pw.chromium.launch()

    if part("pair"):
        print("\nTHE PAIR — at the end of the one line, in the zoom's box")
    PAIR = """() => { const q = (s) => document.querySelector(s), R = (e) => e.getBoundingClientRect();
      const line = R(q('#musicPickLine')), text = R(q('#musicPickText')), box = q('.mt-undo'), zoom = q('#musicTlOut').parentElement;
      if (!box) return null;
      const bx = R(box), cell = (id) => { const e = q('#' + id), r = R(e), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return { w: Math.round(r.width), h: Math.round(r.height), painted: !!at && (at === e || e.contains(at)), name: e.getAttribute('aria-label'),
                 tip: e.getAttribute('data-tip') || e.title, off: e.disabled, op: getComputedStyle(e).opacity }; };
      const cs = getComputedStyle(box), zs = getComputedStyle(zoom);
      return { right: Math.round((line.right - bx.right) * 10) / 10, mid: Math.round(((line.top + line.bottom) - (bx.top + bx.bottom)) * 5) / 10,
               clear: Math.round((bx.left - text.right) * 10) / 10, inLine: box.parentElement === q('#musicPickLine'),
               zoomBox: box.classList.contains('mt-tl-mag') && cs.backgroundColor === zs.backgroundColor && cs.borderTopColor === zs.borderTopColor && cs.borderRadius === zs.borderRadius,
               undo: cell('musicUndo'), redo: cell('musicRedo'), zoomOff: getComputedStyle(q('#musicTlOut')).opacity,
               height: Math.round(line.height * 10) / 10, pairH: Math.round(bx.height * 10) / 10 }; }"""
    for _n, _p in eds("pair"):
        for dev, o, scheme in (("phone", PHONE, "dark"), ("desk", DESK, "light")):
            c, pg, errs = editor(b, _n, _p, opts=o, scheme=scheme)
            setup(pg, FREE)
            fresh = pg.evaluate(PAIR)
            # two steps and one back, so both are there to read
            press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]', door="exact")
            press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
            set_door(pg, None)
            timeline(pg)
            press(pg, "#musicUndo")
            got = pg.evaluate(PAIR)
            ok = bool(got and fresh) and abs(got["right"]) <= 0.5 and abs(got["mid"]) <= 1 and got["clear"] >= 9.5 and got["inLine"] and got["zoomBox"]
            for k, words in (("undo", "Undo a change to the loop"), ("redo", "Redo a change to the loop")):
                cl = (got or {}).get(k) or {}
                ok = ok and cl.get("w") == 28 and cl.get("h") == 28 and cl.get("painted") and not cl.get("off") and cl.get("name") == words and cl.get("tip") == words
            check(f"{_n} ({dev}): the loop's Undo and Redo sit at the end of the one line, in the zoom's box, each a 28px cell, painted, named, their words their tooltips",
                  ok, str(got))
            check(f"{_n} ({dev}): with nothing to take back or again both are greyed, as the zoom's minus is at 1x",
                  bool(fresh) and fresh["undo"]["off"] and fresh["redo"]["off"] and fresh["undo"]["op"] == fresh["redo"]["op"] == fresh["zoomOff"],
                  str(fresh and {k: fresh[k] for k in ("undo", "redo", "zoomOff")}))
            if dev == "phone":
                bare_c, bare, _ = editor(b, _n, _p, opts=o, scheme=scheme, drawn=False)
                setup(bare, FREE)
                h0 = bare.evaluate(PAIR)
                bare_c.close()
                check(f"{_n} (phone): the one line is two rows tall with or without a {WORK[_n]}, the pair in the middle of them",
                      bool(h0) and abs(got["height"] - 38) <= 0.6 and abs(h0["height"] - 38) <= 0.6 and abs(h0["mid"]) <= 1,
                      f"with a {WORK[_n]} {got['height']}px, the pair {got['mid']}px off its middle; without {h0 and h0['height']}px, {h0 and h0['mid']}px off")
            else:
                check(f"{_n} (desk): the one line is one row, as tall as the pair",
                      abs(got["height"] - got["pairH"]) <= 0.6 and got["height"] < 40, f"the line {got['height']}px, the pair {got['pairH']}px")
            check(f"{_n} ({dev}): no page errors around the pair", not errs, "; ".join(errs[:2]))
            c.close()
    for _n, _p in eds("pair"):
        c, pg, _ = editor(b, _n, _p)
        one = pg.evaluate("""() => ({ old: !!document.getElementById('musicPickUndo'),
            inLength: [...document.querySelectorAll('#musicDoorLength button')].filter((x) => /undo/i.test(x.textContent + ' ' + (x.getAttribute('aria-label') || ''))).length,
            inDrawer: [...document.querySelectorAll('#musicDetail button')].filter((x) => /^undo/i.test(x.getAttribute('aria-label') || x.textContent.trim())).map((x) => x.id) })""")
        check(f"{_n}: there is one Undo in the drawer, the loop's; the Length door's own, for eight seconds, is gone",
              not one["old"] and one["inLength"] == 0 and one["inDrawer"] == ["musicUndo"], str(one))
        c.close()

    # ------------------------------------------------------------------ steps
    if part("chain"):
        print("\nEVERY CHANGE IS A STEP — made as a person makes it, undone and done again at once, then Undo all the way down and Redo all the way up")
    for _n, _p in eds("chain"):
        c, pg, errs = editor(b, _n, _p)
        setup(pg, FREE)
        states, made = [st(pg)], []

        # Each change is undone and done again as soon as it is made, so a
        # change that is not a step reds its own row and no other.
        def did(kind, ok):
            before, after = states[-1], st(pg)
            u = press(pg, "#musicUndo", ms=400)
            undone = st(pg)
            r = press(pg, "#musicRedo", ms=400)
            redone = st(pg)
            made.append((kind, ok, before, after, u, undone, r, redone))
            states.append(redone)
            timeline(pg)

        g = grip(pg, "End")
        drag(pg, g[0], g[1], 50); did("an end dragged", True)
        at = slide_at(pg)
        if at:
            drag(pg, at[0], at[1], -40)
        did("the song slid under the " + WORK[_n], bool(at))
        at = whole_at(pg)
        if at:
            pg.mouse.click(at[0], at[1]); waits.settle(pg, 600)
        did("a tap on the whole song's line", bool(at))
        card = "#musicWholeBtn" if _n == "Pad" else "#matchDrawingBtn"
        did("a Length card (" + ("Whole song" if _n == "Pad" else "Fit my animation") + ")", press(pg, card, door="length"))
        did("Skribl's pick, the way back", press(pg, "#musicPickCard", door="length"))
        did("a count in Beats", press(pg, '#musicBeatsSeg button[data-beats="8"]', door="length", ms=600))
        did("Beats in a bar", press(pg, '#musicBarSeg button[data-bar="3"]', door="beat"))
        did("Smooth restart", press(pg, "#musicSmooth", door="restart"))
        did("Cut on silence", press(pg, "#musicCut", door="restart"))
        did("a nudge of an end", press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]', door="exact"))
        try:
            pg.fill("#startReadout", "1.5"); pg.press("#startReadout", "Enter"); waits.settle(pg, 400); typed = True
        except Exception:
            typed = False
        did("a typed time", typed)
        set_door(pg, "beat")
        pg.evaluate(TAPS, 6); pg.wait_for_timeout(2700)
        did("Tap the beat", True)
        set_door(pg, None)
        timeline(pg)
        for kind, ok, before, after, pressed_u, undone, pressed_r, redone in made:
            check(f"{_n}: {kind} is a step: Undo puts the loop back as it was, and Redo takes it again",
                  ok and not same(before, after) and pressed_u and same(undone, before) and pressed_r and same(redone, after),
                  f"made {ok}: {says(before)} -> {says(after)}; Undo ({pressed_u}) {says(undone)}; Redo ({pressed_r}) {says(redone)}")
        n = len(made)
        downs, ups = [], []
        for k in range(n):
            downs.append((press(pg, "#musicUndo", ms=400), st(pg)))
        for k in range(n):
            ups.append((press(pg, "#musicRedo", ms=400), st(pg)))
        down_ok = all(pr and same(t, states[n - 1 - k]) for k, (pr, t) in enumerate(downs))
        up_ok = all(pr and same(t, states[k + 1]) for k, (pr, t) in enumerate(ups))
        check(f"{_n}: Undo all the way down puts the loop back through every change in turn, and Redo all the way up takes each again",
              down_ok and up_ok, f"down {[says(t) for _, t in downs]}; up {[says(t) for _, t in ups]}")
        check(f"{_n}: at the bottom Undo is greyed, and at the top Redo",
              not downs[-1][1]["undo"] and downs[-1][1]["redo"] and not ups[-1][1]["redo"] and ups[-1][1]["undo"],
              f"bottom: undo {downs[-1][1]['undo']}, redo {downs[-1][1]['redo']}; top: undo {ups[-1][1]['undo']}, redo {ups[-1][1]['redo']}")
        check(f"{_n}: no page errors through every change and back", not errs, "; ".join(errs[:2]))
        c.close()

    if part("one"):
        print("\nONE STEP — however far a drag goes; a settle with its glide")
    settled = {}
    for _n, _p in eds("one"):
        c, pg, _ = editor(b, _n, _p)
        setup(pg, FREE)
        t0 = st(pg)
        g = grip(pg, "End")
        drag(pg, g[0], g[1], -150, steps=30)
        t1 = st(pg)
        u = press(pg, "#musicUndo", ms=400)
        t2 = st(pg)
        check(f"{_n}: however far a drag goes, it is one step: one Undo puts the loop back where the drag began",
              not same(t0, t1) and t1["undo"] and u and same(t2, t0) and not t2["undo"],
              f"{says(t0)} -> {says(t1)}; Undo ({u}): {says(t2)}, Undo then {t2['undo']}")
        set_door(pg, "restart")
        sl = pg.evaluate("() => { const r = document.getElementById('crossfadeSlider').getBoundingClientRect(); return [r.left, r.top + r.height / 2, r.width]; }")
        t3 = st(pg)
        pg.mouse.move(sl[0] + sl[2] * 0.2, sl[1]); pg.mouse.down()
        for i in range(1, 16):
            pg.mouse.move(sl[0] + sl[2] * (0.2 + 0.6 * i / 15), sl[1]); pg.wait_for_timeout(20)
        pg.mouse.up(); waits.settle(pg, 400)
        t4 = st(pg)
        u = press(pg, "#musicUndo", ms=400)
        t5 = st(pg)
        check(f"{_n}: however often a held finger moves the restart's length, it is one step",
              t4["xf"] != t3["xf"] and u and same(t5, t3) and not t5["undo"],
              f"{t3['xf']}ms -> {t4['xf']}ms; Undo ({u}): {t5['xf']}ms, Undo then {t5['undo']}")
        c.close()
        c, pg, _ = editor(b, _n, _p)
        setup(pg, SNAPPING)
        t0 = st(pg)
        g = grip(pg, "End")
        drag(pg, g[0], g[1], 37)
        t1 = st(pg)
        settled[_n] = t1
        u = press(pg, "#musicUndo", ms=400)
        t2 = st(pg)
        # whole beats heard each time round: the end less the smooth restart
        heard = t1["e"] - t1["s"] - t1["xf"] / 1000
        on_beat = abs(heard * 2 - round(heard * 2)) < 1e-6
        check(f"{_n}: an end let go and settled on the beat is one step with its glide: Undo puts it back where it was before the drag",
              on_beat and not same(t0, t1) and u and same(t2, t0) and not t2["undo"],
              f"{says(t0)} -> let go and settled {says(t1)} ({heard:.3f}s heard, whole beats {on_beat}); Undo ({u}): {says(t2)}, Undo then {t2['undo']}")
        c.close()
        c, pg, _ = editor(b, _n, _p)
        setup(pg, SNAPPING)
        set_door(pg, "exact")
        timeline(pg)
        t0 = st(pg)
        g = grip(pg, "End")
        pg.mouse.move(g[0], g[1]); pg.mouse.down()
        for i in range(1, 11):
            pg.mouse.move(g[0] + 3.7 * i, g[1]); pg.wait_for_timeout(16)
        # let go, and a nudge while the settle still glides: from the page,
        # 40ms after the finger lifts (the glide is 200ms)
        pg.evaluate("""() => { window.__mid = null; document.addEventListener('pointerup', () => setTimeout(() => {
            window.__mid = trimEnd; document.querySelector('.nudge-btn[data-which="start"][data-amount="1"]').click(); }, 40), { once: true }); }""")
        pg.mouse.up(); waits.settle(pg, 600)
        mid = pg.evaluate("() => window.__mid")
        t1 = st(pg)
        u1 = press(pg, "#musicUndo", ms=400)
        t2 = st(pg)
        u2 = press(pg, "#musicUndo", ms=400)
        t3 = st(pg)
        want = settled.get(_n)
        check(f"{_n}: a change made while a settle still glides is a step of its own: Undo puts back where the settle was going, and again to before the drag",
              want is not None and mid is not None and abs(mid - want["e"]) > 1e-4 and abs(t1["s"] - t0["s"]) > 1e-4
              and u1 and same(t2, want) and u2 and same(t3, t0),
              f"settling toward {want and says(want)}, the nudge at end {mid}; then {says(t1)}; Undo ({u1}) {says(t2)}; Undo ({u2}) {says(t3)}")
        c.close()

    if part("notsteps"):
        print("\nNOT STEPS — how it is looked at and worked; Skribl's own; a new song")
    for _n, _p in eds("notsteps"):
        c, pg, _ = editor(b, _n, _p)
        first = st(pg)
        check(f"{_n}: a new song's pick is not a step: Undo and Redo start greyed",
              first["track"] and not first["undo"] and not first["redo"], str(first))
        setup(pg, SNAPPING)
        press(pg, "#musicTlIn", ms=400); press(pg, "#musicTlTall", ms=500); press(pg, "#musicSnap", ms=300)
        press(pg, "#musicLock", door="length", ms=300)
        look = st(pg)
        locked = pg.evaluate("() => document.getElementById('musicLock').getAttribute('aria-checked')")
        check(f"{_n}: the zoom, the taller box, the magnet and Lock the length are not steps: Undo stays greyed",
              not look["undo"] and not look["snap"] and locked == "true", f"undo {look['undo']}, magnet {look['snap']}, lock {locked}")
        # A step that changed the beat, the magnet turned on after it: the beat
        # goes back and the magnet stays as it is now.
        before = st(pg)
        press(pg, '#musicBarSeg button[data-bar="3"]', door="beat")
        changed = st(pg)
        press(pg, "#musicSnap", ms=300)
        snapped = st(pg)["snap"]
        u = press(pg, "#musicUndo", ms=400)
        back = st(pg)
        locked2 = pg.evaluate("() => document.getElementById('musicLock').getAttribute('aria-checked')")
        check(f"{_n}: a step put back leaves the magnet and Lock the length as they are",
              not same(changed, before) and snapped and u and same(back, before) and back["snap"] and locked2 == "true",
              f"a bar of 3 {says(changed)}, then the magnet on {snapped}; Undo ({u}): {says(back)}, magnet {back['snap']}, lock {locked2}")
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]', door="exact")
        had = st(pg)
        add(pg, OTHER)
        new = st(pg)
        check(f"{_n}: a new song starts a new history: Undo and Redo greyed",
              had["undo"] and new["track"] and not new["undo"] and not new["redo"], f"before {had['undo']}; the new song: undo {new['undo']}, redo {new['redo']}")
        c.close()

    if part("afresh"):
        print("\nAFRESH — a change after an Undo")
    for _n, _p in eds("afresh"):
        c, pg, _ = editor(b, _n, _p)
        setup(pg, FREE)
        set_door(pg, "exact")
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
        one = st(pg)
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
        press(pg, "#musicUndo", ms=400)
        mid = st(pg)
        press(pg, '.nudge-btn[data-which="start"][data-amount="1"]')
        new = st(pg)
        press(pg, "#musicUndo", ms=400)
        back = st(pg)
        check(f"{_n}: a change after an Undo starts afresh: what Redo held goes, and Undo goes back from the new change",
              mid["redo"] and not new["redo"] and new["undo"] and same(back, one),
              f"after the Undo redo {mid['redo']}; after a new change redo {new['redo']}; Undo then {says(back)} (want {says(one)})")
        c.close()

    if part("focus"):
        print("\nTHE KEYBOARD'S PLACE")
    for _n, _p in eds("focus"):
        c, pg, _ = editor(b, _n, _p)
        setup(pg, FREE)
        set_door(pg, "exact")
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
        pg.focus("#musicUndo")
        pg.keyboard.press("Enter"); waits.settle(pg, 300)
        f1 = pg.evaluate("() => document.activeElement && document.activeElement.id")
        pg.keyboard.press("Enter"); waits.settle(pg, 300)
        f2, s2 = pg.evaluate("() => document.activeElement && document.activeElement.id"), st(pg)
        pg.keyboard.press("Enter"); waits.settle(pg, 300)
        pg.keyboard.press("Enter"); waits.settle(pg, 300)
        f3, s3 = pg.evaluate("() => document.activeElement && document.activeElement.id"), st(pg)
        check(f"{_n}: Undo and Redo keep the keyboard's place: as one runs out, focus moves to the other",
              f1 == "musicUndo" and f2 == "musicRedo" and not s2["undo"] and f3 == "musicUndo" and not s3["redo"] and s3["undo"],
              f"after one Undo {f1}; after the last {f2} (undo {s2['undo']}); after the last Redo {f3} (redo {s3['redo']})")
        c.close()

    # -------------------------------------------------------------------- bin
    if part("bin"):
        print("\nTHE BIN'S UNDO")
    STORE = {"Pad": """() => new Promise((done) => { SkriblDraftStore.get('pad:music').then((r) => done(r ? { size: r.blob ? r.blob.size : null, name: r.name } : null), () => done('error')); })""",
             "Flip": """() => new Promise((done) => { SkriblDraftStore.get('flip:draft').then((r) => { try { const d = r && JSON.parse(r.json); done(d ? { music: !!d.music } : null); } catch (e) { done('bad'); } }, () => done('error')); })"""}
    META = "() => { const r = localStorage.getItem('skribl_autosave_v1'); if (!r) return null; const d = JSON.parse(r); return d.musicMeta ? d.musicMeta.name : 'none'; }"

    def stored(pg, name, want, ms=8000):
        """The draft's copy of the song, once it says `want` (or the last it said)."""
        got = None
        for _ in range(ms // 250):
            got = pg.evaluate(STORE[name])
            if name == "Pad":
                got = {"bytes": got, "named": pg.evaluate(META)}
                has = bool(got["bytes"] and got["bytes"] != "error" and got["bytes"]["size"] == len(SONG["buffer"])) and got["named"] == SONG["name"]
                gone = got["bytes"] is None and got["named"] == "none"
            else:
                # with no media left the record goes (dropStoredMedia)
                has = bool(got and got not in ("error", "bad") and got["music"])
                gone = got is None or (isinstance(got, dict) and not got["music"])
            if (want and has) or (not want and gone):
                return got, True
            pg.wait_for_timeout(250)
        return got, False

    for _n, _p in eds("bin"):
        c, pg, errs = editor(b, _n, _p)
        setup(pg, FREE)
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]', door="exact")
        press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
        one_back = None
        kept = st(pg)
        stored(pg, _n, True)
        binned = bin_song(pg)
        gone, said = st(pg), note(pg, _n)
        check(f"{_n}: the bin takes the song at once and says so, with an Undo",
              binned and kept["track"] and not gone["track"] and bool(said) and said["words"] == "Song removed" and said["action"] == "Undo",
              f"binned {binned}: track {gone['track']}; the note {said}")
        # the note offers its Undo for seven seconds: the draft is read within three
        away, away_ok = stored(pg, _n, False, ms=3000)
        undid = note_action(pg, _n)
        back, said2 = st(pg), note(pg, _n)
        shown = pg.evaluate("() => { const d = document.getElementById('musicDetail'); return !!d && !d.hidden && d.getClientRects().length > 0; }")
        here, here_ok = stored(pg, _n, True)
        check(f"{_n}: Undo brings the song back as it was, and says Song restored, with a Redo",
              undid and back["track"] and same(back, kept) and shown and bool(said2) and said2["words"] == "Song restored" and said2["action"] == "Redo",
              f"Undo {undid}: {says(back)} (was {says(kept)}), the drawer shown {shown}; the note {said2}")
        if _n == "Pad":
            check("Pad: the song put back is the draft's again: its bytes back in the store, and the draft names it",
                  away_ok and here_ok, f"binned: {away}; put back: {here}")
        else:
            check("Flip: the song put back is saved with the animation again", away_ok and here_ok, f"binned: {away}; put back: {here}")
        redid = note_action(pg, _n)
        again, said3 = st(pg), note(pg, _n)
        undid2 = note_action(pg, _n)
        back2 = st(pg)
        check(f"{_n}: Redo takes the song away again and offers the Undo again, which brings it back again",
              redid and not again["track"] and bool(said3) and said3["words"] == "Song removed" and said3["action"] == "Undo"
              and undid2 and back2["track"] and same(back2, kept),
              f"Redo {redid}: track {again['track']}, the note {said3}; Undo {undid2}: {says(back2)}")
        timeline(pg)
        u = press(pg, "#musicUndo", ms=400)
        one_back = st(pg)
        check(f"{_n}: and the loop's own Undo comes back with it: one Undo takes back the last nudge",
              back2["undo"] and u and abs(one_back["e"] - (kept["e"] + 0.1)) < 1e-6 and abs(one_back["s"] - kept["s"]) < 1e-9,
              f"undo {back2['undo']}; Undo ({u}): {says(one_back)}, from {says(kept)}")
        check(f"{_n}: no page errors through the bin and back", not errs, "; ".join(errs[:2]))
        c.close()
    if part("bin") and (not ONLY or ONLY == "Pad"):
        c, pg, _ = editor(b, "Pad", "/")
        pg.evaluate("() => { window.__said = []; const o = showToast; showToast = function (m) { window.__said.push(String(m)); return o.apply(this, arguments); }; }")
        pg.evaluate("() => clearAllWithUndo()")
        waits.settle(pg, 500)
        said, after = pg.evaluate("() => window.__said"), st(pg)
        check("Pad: New Skribl's clear has its own Undo and no bin note of its own",
              not after["track"] and "Song removed" not in said, f"track {after['track']}; said {said}")
        c.close()

    # ------------------------------------------------------------------ reach
    if part("reach"):
        print("\nTHE REACH — where a press lands, on a phone and a desk")
    for _n, _p in eds("reach"):
        for dev, o in (("phone", PHONE), ("desk", DESK)):
            c, pg, _ = editor(b, _n, _p, opts=o)
            setup(pg, FREE)
            g = pg.evaluate(GEOM)
            wave_y = g["stage"][1] + (g["stage"][3] - g["stage"][1]) * 0.65
            tab_y = g["stage"][3] + 4
            takes = [(g[w] + d, y) for w in ("start", "end") for d in (-30, 30) for y in (wave_y, g["tabMid"])] + \
                    [(g["start"], g["tab"][1] + 16), (g["end"], g["tab"][1] + 16)]
            got = pg.evaluate(HIT, takes)
            want = ["start"] * 4 + ["end"] * 4 + ["start", "end"]
            check(f"{_n} ({dev}): an end takes a press 30px either side of its line, on the wave and by its tab, and 16px below its tab",
                  got == want, f"{list(zip([(round(x), round(y)) for x, y in takes], got))}")
            miss = [(g["start"] - 40, tab_y), (g["end"] + 40, tab_y)]
            if g["end"] - g["start"] > 90:
                miss += [(g["start"] + 40, tab_y), (g["end"] - 40, tab_y)]
            mg = pg.evaluate(HIT, miss)
            check(f"{_n} ({dev}): 40px beside a tab, past an end's reach, a press lands on nothing",
                  all(h == "nothing" for h in mg), f"{list(zip([(round(x), round(y)) for x, y in miss], mg))}")
            w = whole_at(pg)
            on = pg.evaluate(HIT, [w, [w[0], g["whole"][1] - 6]]) if w else None
            check(f"{_n} ({dev}): the whole song's line takes a press on its own row, and not 6px above it",
                  on == ["whole", "nothing"], f"at {w}: {on}")
            c.close()

    if part("press"):
        print("\nTHE REACH — real presses on a desk")
    for _n, _p in eds("press"):
        c, pg, _ = editor(b, _n, _p)
        setup(pg, FREE)
        g = pg.evaluate(GEOM)
        t0 = st(pg)
        pps = (g["end"] - g["start"]) / (t0["e"] - t0["s"])
        drag(pg, g["end"] + 28, g["stage"][1] + (g["stage"][3] - g["stage"][1]) * 0.65, -30)
        t1 = st(pg)
        # it keeps its distance from the finger: 30px left, from where it was
        moved = (t0["e"] - t1["e"]) * pps
        check(f"{_n}: a press 28px beside an end's line takes the end: a drag moves that end as far as the finger, and only that end",
              abs(moved - 30) <= 2 and abs(t1["s"] - t0["s"]) < 1e-9, f"{says(t0)} -> {says(t1)}: the end moved {moved:.1f}px for a 30px drag")
        g = pg.evaluate(GEOM)
        pg.mouse.click(g["end"] + 40, g["stage"][3] + 4); waits.settle(pg, 500)
        pg.mouse.click(g["start"] - 40, g["stage"][3] + 4); waits.settle(pg, 500)
        t2 = st(pg)
        check(f"{_n}: a near miss beside a tab moves nothing", same(t2, t1), f"{says(t1)} -> {says(t2)}")
        # At 1x the view keeps the ends a quarter of the timeline apart or
        # more (its framing counts the drawing up to three loops), so their
        # reaches meet only while it eases back after a drag. Here each end
        # reaches the whole loop's width, so a press between them reaches both.
        pg.add_style_tag(content=".mt-tl-handle::before { inset: 0 -400px -26px !important; }")
        pg.wait_for_timeout(100)
        g = pg.evaluate(GEOM)
        gap = g["end"] - g["start"]
        y = g["stage"][1] + (g["stage"][3] - g["stage"][1]) * 0.65
        n0 = st(pg)
        drag(pg, g["start"] + gap * 0.3, y, -25)
        n1 = st(pg)
        g = pg.evaluate(GEOM)
        gap2 = g["end"] - g["start"]
        drag(pg, g["end"] - gap2 * 0.3, y, 25)
        n2 = st(pg)
        check(f"{_n}: where the two ends' reach meets, a press takes the nearer one",
              abs(n1["s"] - n0["s"]) > 0.05 and abs(n1["e"] - n0["e"]) < 1e-9
              and abs(n2["e"] - n1["e"]) > 0.05 and abs(n2["s"] - n1["s"]) < 1e-9,
              f"the ends {gap:.0f}px apart: nearer the start {says(n0)} -> {says(n1)}; nearer the end -> {says(n2)}")
        c.close()
    # A mouse overshoots: an end dragged and let go past the drawer's edge.
    # Flip closed its drawer on the click that lands on what the two share;
    # the Pad's has no tap away to close it, so only Flip can fail this.
    if part("press") and (not ONLY or ONLY == "Flip"):
        c, pg, _ = editor(b, "Flip", "/flip")
        setup(pg, FREE)
        g = grip(pg, "End")
        edge = pg.evaluate("() => document.getElementById('musicPanel').getBoundingClientRect().right")
        t0 = st(pg)
        drag(pg, g[0], g[1], edge + 60 - g[0], steps=20)
        t1 = st(pg)
        shown = pg.evaluate("() => { const d = document.getElementById('musicDetail'); return !!d && !d.closest('[hidden]') && d.getClientRects().length > 0; }")
        check("Flip: an end dragged and let go past the drawer's edge moves the end, and the drawer stays open",
              shown and t1["e"] > t0["e"] + 0.5 and t1["undo"], f"let go {edge + 60 - g[0]:.0f}px on, 60px past the drawer: {says(t0)} -> {says(t1)}, the drawer open {shown}")
        c.close()

    # -------------------------------------------------------------------- ink
    if part("ink"):
        print("\nTHE ARROWS READ")
    INK = """(sel) => {
      const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', { willReadFrequently: true });
      const parse = (s) => { cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = s; cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data; return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 }; };
      const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return a ? { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a } : b; };
      const ground = (el) => { const l = []; for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e).backgroundColor; if (s === 'rgba(0, 0, 0, 0)' || s === 'transparent') continue;
          const c = parse(s); if (c.a > 0) { l.push(c); if (c.a >= 0.999) break; } }
        let acc = { r: 255, g: 255, b: 255, a: 1 }; for (let i = l.length - 1; i >= 0; i--) acc = over(l[i], acc); return acc; };
      const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
      const ratio = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
      const el = document.querySelector(sel), g = ground(el);
      return Math.round(ratio(over(parse(getComputedStyle(el).color), g), g) * 100) / 100; }"""
    for _n, _p in eds("ink"):
        seen = {}
        for scheme in ("light", "dark"):
            for dev, o in (("phone", PHONE), ("desk", DESK)):
                c, pg, _ = editor(b, _n, _p, opts=o, scheme=scheme)
                setup(pg, FREE)
                press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]', door="exact")
                press(pg, '.nudge-btn[data-which="end"][data-amount="-1"]')
                set_door(pg, None)
                timeline(pg)
                press(pg, "#musicUndo", ms=400)
                pg.mouse.move(2, 2); pg.wait_for_timeout(300)
                seen[f"{scheme} {dev}"] = (pg.evaluate(INK, "#musicUndo"), pg.evaluate(INK, "#musicRedo"))
                c.close()
        check(f"{_n}: the arrows read at 3:1 or more on their cell, light and dark, phone and desk",
              all(min(v) >= 3 for v in seen.values()), "; ".join(f"{k}: Undo {v[0]}:1, Redo {v[1]}:1" for k, v in seen.items()))

    b.close()

summarise_and_exit()
