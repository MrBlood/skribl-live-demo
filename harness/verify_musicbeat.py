#!/usr/bin/env python3
"""The music drawer's pair and its beat (owner: "How do I test the loop without
having it show me drawing? It's cumbersome, plus to know how many beats are in
the loop, so I'm not at 7 or 9 when I want 8"; "All yes" to the mock; then
"we only ever want 4,8,16,... beats").

  THE PAIR. Play with my drawing and Hear the loop sit under the timeline in
  the same place whichever door is open, or none, the same size, and no door
  has a second Hear. Hear the loop plays the music alone, round and round,
  until Stop; an end moved while it plays is heard from its next time round.

  THE CLICK AND THE LIT BEAT are verify_musicclick's, and ZOOMED IN, THE
  START and THE END SETTING THE TEMPO verify_musictempo's: with the click
  here this suite went past run_harness.sh's ten minutes a suite on CI and
  was stopped before it reported, and it had taken nine before the click.

  TAP THE BEAT. The first tap starts the loop and is not a beat. Taps in time
  settle on the tempo two seconds after the last, to the nearest whole beat a
  minute, from the middle gap (a stray one does not move it); where the beat
  falls is the taps' own, read off the song's clock less the time the sound
  takes to reach the ear. Fewer than four taps
  leave the tempo as it was, and say so. On a phone the tap stays put under
  the finger while its words change.

  THE NEAREST BEAT, with the magnet by the zoom on (the owner: "it kept
  snapping"; of the mock, "all yes"; it was whole bars, 4, 8, 16 or 32
  beats). An end let go on the timeline settles on the nearest beat, smooth
  restart and all, counted from the start wherever it is: a start set off
  the beat is never moved. The start let go lands on the nearest beat (or
  where the music begins, below), and the end follows to whole beats. Beats
  the song or the 20s cap has no room for are passed over. An end past what is in view is
  held at the timeline's edge until the view has widened to it, as a person
  holds it. The settle glides there frame by frame, at once under Reduce
  Motion. The song slid under the drawing settles the loop's start on a
  beat, its length kept. (Make it went with the streamline; - and + moving a
  bar is verify_musicdoors's.)

  BEATS (the owner: "There should be ways to have skribl pick 4 or 8 16 32";
  of the mock, "All yes if it's intuitive"). In the Length door, under its
  three choices, once there is a beat, the counts the song and the 20s cap
  have room for, the loop's own lit, none while it is not whole bars (and
  none pressed). It opens out, Lock under it gliding down, at once under
  Reduce Motion, and the page
  stays still as it does (the drawer's growth follow scrolled it 46px under
  a finger reaching for the timeline), as it does in the Beat door as Beats
  in a bar opens (with Snap to the beat's row there, 61-63px on a phone and
  139 on a desk). A count tapped
  on a loop of the person's own keeps the start and makes the loop that
  many beats, smooth restart and all; near the song's end it moves back by
  whole beats, only as far as it must. It glides there, the count lit from
  the tap all the way, at once under Reduce Motion; a second tap while it
  glides counts from where it lands. Each tap is a step the loop's Undo
  takes back, a tap at a time, Skribl's pick beside it as the way back (the
  Undo itself is verify_musicundo's). (A tap on Skribl's pick, with ears,
  is verify_musicears'.)

  SNAP TO THE BEAT, WHERE THE MUSIC BEGINS, THE MARKS, THE RESTART VIEW,
  KEPT and WORDS are verify_musicsnap's: with them here this suite took 591
  of run_harness.sh's 600 seconds on #663's PostgreSQL shard, and on #665's
  it was stopped at 600 before it reported (every check it reached passing).
  They moved whole, as the click and the tempo did before them.

Every row runs on the Pad and on Flip: one drawer (lib/musicdrawer.js), and
each editor's half is its hooks. A control behind a door is reached as a
person reaches it, by opening its door (Tap the beat and Beats in a bar in
Beat, Beats and Lock in Length, the Restart view in Restart, the typed
times and Each press in Exact times). Skribl's ears are off here (lib/musicears.js):
every row is a person with no beat yet, and the pulse below is a beat the ears
would hear at once; verify_musicears holds the ears to songs of their own.
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
    print("No assertions were executed. This is NOT evidence the music drawer can hear its beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICBEAT_ONLY=Pad (or Flip) runs one editor, and
# MUSICBEAT_PART=pair (tap, bars, beats) one part.
# A real run sets neither.
ONLY = os.environ.get("MUSICBEAT_ONLY", "")
PART = os.environ.get("MUSICBEAT_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
WORK = {"Pad": "drawing", "Flip": "flip"}
PLAY = {"Pad": "#playBtn", "Flip": "#play"}


def _wav(seconds, rate=8000):
    """A pulse twice a second, on the half seconds: 120 beats a minute."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(11000 * math.sin(2 * math.pi * 220 * i / rate) * math.exp(-((2 * i / rate) % 1) * 7)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


SHORT = {"name": "six.wav", "mimeType": "audio/wav", "buffer": _wav(6.0)}
TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
LONG = {"name": "minute.wav", "mimeType": "audio/wav", "buffer": _wav(60.0)}
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""
TRIM = "() => ({ s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs })"
# The drawer as it stands: what the pair, the tap and the one line say, and the tempo kept.
SAID = """() => { const q = (id) => document.getElementById(id), tx = (id) => q(id) ? q(id).textContent : null;
  return { play: tx('musicPlayLabel'), hear: tx('musicHearLabel'), tap: tx('musicTapWords'), tempo: tx('musicTempo'),
           line: tx('musicPickText'), kept: musicTempo, pv: previewingLoop, playing: playing }; }"""
SET = "(o) => { musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; } if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } updateTrimUI(); }"
# The loop alone, the tempo (and its switch) left as they are.
LOOP = "(o) => { trimStart = o.s; trimEnd = o.e; updateTrimUI(); }"
# Taps from inside the page, so their gaps are the page's own clock and not a
# driver's round trips: the first after `lead` ms, then each gap in turn, each
# timed from the first (a tap's own handler does not push the next one later).
# When the first starts the loop, the next comes 600ms on: the loop's start
# keeps the page busy for a moment, and a tap held up by it is the page's
# hiccup, not the tempo's. Each tap wakes 15ms early and waits out the rest
# on the clock, so a busy page cannot make it late, and it answers how far
# its taps strayed from their marks (ms): see in_time().
TAPS = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'), off = []; let i = 0, t0 = null, due = 0;
  const go = () => { if (t0 != null) while (performance.now() < t0 + due) {}
    const now = performance.now(); if (t0 == null) t0 = now; off.push(now - t0 - due); b.click();
    if (i >= o.gaps.length) { res(Math.max(...off) - Math.min(...off)); return; }
    due += o.gaps[i++]; setTimeout(go, Math.max(0, t0 + due - performance.now() - 15)); };
  setTimeout(go, o.lead || 0); })"""
# Taps on the song's own beat, `off` past each half second as heard: timed on
# the page's clock from one reading of the song's (which moves in steps, of
# 2.9 or 11.6ms on this box), less the time the sound takes to reach the ear.
# Where the song had got to as each tap landed is read BESIDE THE TAP'S OWN
# HANDLER: by a listener on the button that goes first (capture, at the
# target) and one that goes after it, so the handler's own reading is between
# the two, and equal to both unless the clock stepped in that moment. Read
# before the click, a busy page let the clock step before the handler on some
# taps (CI, Flip: the means 10ms apart; here, the processor slowed sixfold,
# 11.6ms on four taps of six); read after it alone, the other way (7ms).
# Woken early as TAPS is.
ON_BEAT = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'), seen = [], after = [], off = [];
  const lat = _waLoop.latency(), heard = () => trimStart + _waLoop.elapsed() - lat;
  const first_ = () => seen.push(heard()), last_ = () => after.push(heard());
  b.addEventListener('click', first_, true); b.addEventListener('click', last_);
  const s0 = heard(), t0 = performance.now(), first = Math.ceil((s0 - o.off) / 0.5) * 0.5 + o.off + 0.5;
  const mark = (k) => t0 + (first + k * 0.5 - s0) * 1000;
  const go = () => { const k = seen.length; while (performance.now() < mark(k)) {} off.push(performance.now() - mark(k)); b.click();
    if (seen.length >= o.n) { b.removeEventListener('click', first_, true); b.removeEventListener('click', last_);
      res({ seen, after, lat, spread: Math.max(...off) - Math.min(...off) }); return; }
    setTimeout(go, Math.max(0, mark(seen.length) - performance.now() - 15)); };
  setTimeout(go, Math.max(0, mark(0) - performance.now() - 15)); })"""
# A machine busy enough to hold a tap up past its mark anyway makes a tempo a
# beat a minute off, which is the machine, not the rule: such a try is tapped
# again on a fresh page, three tries at most, and the row says which it was.
# 4ms is the most the rows can stand: the stray gap's tempo is the mean of
# four gaps, and half a beat a minute at 120 is 2.1ms in that mean, which
# taps 4ms apart at most cannot reach (2 x 4 / 4). Quiet, they land within
# 1ms; beside another suite, 3.4; a page held up 40ms just before a tap's
# mark read 12.
SPREAD_MS = 4
# What a canvas recorded it painted (lib/musictimeline.js and musicrestart.js
# keep it on their root as they paint): the timeline's beats [x, bar, time],
# its lane's marks and comes-round lines, and its view [left edge s, span s];
# the Restart view's two windows and its beats [side, x, time].
MARKS = """(id) => { const host = document.getElementById(id), p = host && host._painted; if (!p) return null;
  const cv = host.querySelector('canvas');
  return { w: cv.clientWidth, h: cv.clientHeight, view: (host.dataset.view || '').split(' ').map(Number), beats: p.beats, lane: p.lane || 26,
           marks: p.marks || null, lines: p.lines || null, turns: p.turns || 0, end: p.end || null, start: p.start || null }; }"""

def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=TWELVE, opts=DESK, door="beat", ctx=None):
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
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def tile(k):
    return f'#musicDoors .dp-tile[data-dp="{k}"]'


def open_door(pg):
    """The door that is open, or None."""
    return pg.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[aria-expanded=\"true\"]'); return t ? t.dataset.dp : null; }")


def set_door(pg, want):
    """A door open (its name) or every door shut (None), by the tiles, as a person does."""
    now = open_door(pg)
    if now == want:
        return
    pg.click(tile(want or now))
    pg.wait_for_timeout(350)
    browsing.wait_scroll_still(pg)


def door_for(pg, sel):
    """The door that holds `sel` open, as a person opens it to reach it."""
    k = pg.evaluate("(s) => { const e = document.querySelector(s), d = e && e.closest('#musicDoors .dp-panel'); return d ? d.dataset.dp : null; }", sel)
    if k:
        set_door(pg, k)


def press(pg, sel, ms=200):
    """A real click on a control that may be missing from a broken build: a
    row then says so in red rather than the run stopping on a timeout. Its
    door is opened first, where it is behind one."""
    try:
        door_for(pg, sel)
        pg.click(sel, timeout=3000)
    except Exception:
        return False
    pg.wait_for_timeout(ms)
    return True


def in_time(b, name, path, probe, arg, prep=None):
    """An editor whose taps (probe TAPS or ON_BEAT) landed within SPREAD_MS of
    their marks: (context, page, what the probe answered, which try)."""
    for k in range(1, 4):
        c, pg, errs = editor(b, name, path)
        if prep:
            prep(pg)
        got = pg.evaluate(probe, arg)
        if (got["spread"] if isinstance(got, dict) else got) <= SPREAD_MS or k == 3:
            return c, pg, got, k
        c.close()


def phase_gap(a, b, p=0.5):
    """How far apart two places in a beat are, round the circle."""
    d = abs(a - b) % p
    return min(d, p - d)


# SKRIBL'S EARS ARE OFF HERE (lib/musicears.js). These rows are what a person
# does with no beat yet, from the first tap, and the pulse below is a beat the
# ears would hear at once; verify_musicears holds the ears to songs of their own.
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    _new_context = b.new_context

    def _deaf(*a, **k):
        c = _new_context(*a, **k)
        c.add_init_script(NO_EARS)
        return c
    b.new_context = _deaf

    print("\nMUSIC BEAT — the pair that plays")
    for _n, _p in eds("pair"):
        c, pg, errs = editor(b, _n, _p, door=None)
        at = {}
        for lv in (None, "length", "beat", "restart", "exact"):
            set_door(pg, lv)
            at[lv or "none"] = pg.evaluate("""() => { const r = (id) => document.getElementById(id).getBoundingClientRect(), t = r('musicTimeline');
                const a = r('musicPlayBtn'), hp = document.querySelector('#musicPanel .mt-hear'), h = hp ? hp.getBoundingClientRect() : r('previewLoopBtn');
                const hears = [...document.querySelectorAll('#musicPanel button')].filter(x => /hear the loop/i.test(x.textContent)).length - 1;
                return { below: Math.round(a.top - t.bottom), side: Math.round(a.top) === Math.round(h.top) && h.left > a.right,
                         same: Math.round(a.width) === Math.round(h.width) && Math.round(a.height) === Math.round(h.height),
                         h: Math.round(a.height), hears }; }""")
        ok = all(v["side"] and v["same"] and v["h"] >= 44 and v["hears"] == 0 for v in at.values())
        check(f"{_n}: the pair sits under the timeline in the same place whichever door is open, or none, the same size (Hear the loop's pill and Play), and no door has a second Hear",
              ok and len({v["below"] for v in at.values()}) == 1 and at["none"]["below"] < 140, str(at))
        c.close()
    for _n, _p in eds("pair"):
        c, pg, errs = editor(b, _n, _p, door=None)
        press(pg, "#previewLoopBtn", 1200)
        st = pg.evaluate(SAID)
        wa = pg.evaluate("() => _waLoop.playing()")
        press(pg, "#previewLoopBtn", 300)
        stop = pg.evaluate(SAID)
        check(f"{_n}: Hear the loop plays the music alone, round and round, and Stop stops it",
              st["pv"] and wa and not st["playing"] and st["hear"] == "Stop the loop" and st["play"] == f"Play with my {WORK[_n]}"
              and not stop["pv"] and stop["hear"] == "Hear the loop" and not pg.evaluate("() => _waLoop.playing()"),
              f"playing: {dict((k, st[k]) for k in ('pv', 'playing', 'hear', 'play'))}, engine {wa}; stopped: {stop['hear']!r}, {stop['pv']}")
        c.close()
    for _n, _p in eds("pair"):
        c, pg, errs = editor(b, _n, _p, door="exact")
        pg.evaluate(SET, {"tempo": None, "s": 0, "e": 2.0, "xf": 0})
        press(pg, "#previewLoopBtn", 500)
        first = pg.evaluate("() => { window.__src = _waLoop.source(); return _waLoop.source().buffer.duration; }")
        pg.fill("#endReadout", "3"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        soon = pg.evaluate("() => _waLoop.source() === window.__src")
        pg.wait_for_timeout(2200)
        later = pg.evaluate("() => ({ fresh: _waLoop.source() !== window.__src, dur: _waLoop.source() ? _waLoop.source().buffer.duration : null, on: previewingLoop })")
        check(f"{_n}: an end moved while the loop plays is heard from its next time round",
              abs(first - 2.0) < 0.01 and soon and later["fresh"] and later["on"] and later["dur"] is not None and abs(later["dur"] - 3.0) < 0.01,
              f"a {first:.2f}s loop; just after the end moved, the same clip: {soon}; a time round later: {later}")
        c.close()

    print("\nMUSIC BEAT — Tap the beat")
    for _n, _p in eds("tap"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(TAPS, {"gaps": [600, 500, 500]})   # the start, then three taps
        lead = pg.evaluate(SAID)
        pg.wait_for_timeout(2300)
        st = pg.evaluate(SAID)
        check(f"{_n}: Tap the beat's first tap starts the loop and is not a beat: three more are not enough",
              lead["pv"] and lead["tap"] == "Keep tapping" and st["kept"] is None and st["tempo"] == "Four taps or more, in time with the music.",
              f"while tapping: {lead['tap']!r}, loop on {lead['pv']}; settled: {st['kept']}, {st['tempo']!r}")
        c.close()
    for _n, _p in eds("tap"):
        c, pg, spread, k = in_time(b, _n, _p, TAPS, {"gaps": [600] + [500] * 6})
        pg.wait_for_timeout(1500)
        mid = pg.evaluate(SAID)
        pg.wait_for_timeout(900)
        st, t = pg.evaluate(SAID), pg.evaluate(TRIM)
        n = heard(t) / 0.5
        words = f"{round(n)} beats" if abs(n - round(n)) < 0.05 else f"{n:.1f} beats"
        check(f"{_n}: taps in time settle on the tempo, two seconds after the last, and the one line counts the beats",
              mid["kept"] is None and mid["tap"] == "Keep tapping" and st["kept"] and st["kept"]["bpm"] == 120
              and st["tempo"] == "120 beats a minute\u00a0· tap again to change it" and st["tap"] == "Tap the beat"
              and st["line"].startswith(f"{heard(t):.2f}s · {words}"),
              f"1.5s after: {mid['kept']}, {mid['tap']!r}; settled: {st['kept']}, {st['tempo']!r}; {st['line']!r}"
              f" (taps within {spread:.1f}ms of their marks, try {k})")
        c.close()
    # Its words change as it listens; on the owner's phone the tap must not
    # move under the finger that is tapping it (a line that wrapped to three
    # beside it made the row taller, and the first tap moved it 4.3px).
    TAP_AT = "() => Math.round((document.getElementById('musicTapBtn').getBoundingClientRect().top - document.querySelector('.mt-tap-row').getBoundingClientRect().top) * 10) / 10"
    for _n, _p in eds("tap"):
        c, pg, errs = editor(b, _n, _p, opts=PHONE)
        at = [pg.evaluate(TAP_AT)]
        pg.evaluate(TAPS, {"gaps": [300]}); at.append(pg.evaluate(TAP_AT))
        pg.evaluate(TAPS, {"gaps": [500, 500], "lead": 500}); at.append(pg.evaluate(TAP_AT))
        pg.wait_for_timeout(2300); at.append(pg.evaluate(TAP_AT))
        check(f"{_n}: on a phone the tap stays put under the finger while its words change",
              max(at) - min(at) <= 0.5 and pg.evaluate(SAID)["kept"] is not None,
              f"its top in its row, idle, first tap, tapping, settled: {at}")
        c.close()
    for _n, _p in eds("tap"):
        # Over a tempo tapped before, Snap to the beat turned off for it.
        c, pg, spread, k = in_time(b, _n, _p, TAPS, {"gaps": [600, 500, 500, 900, 500, 500]},
                                   prep=lambda pg: pg.evaluate(SET, {"tempo": {"bpm": 100, "phase": 0, "snap": False}}))
        pg.wait_for_timeout(2300)
        st = pg.evaluate(SAID)
        check(f"{_n}: a stray gap does not move the tempo: the middle gap counts",
              st["kept"] and st["kept"]["bpm"] == 120,
              f"gaps 0.5, 0.5, 0.9, 0.5, 0.5: {st['kept']} (taps within {spread:.1f}ms of their marks, try {k})")
        check(f"{_n}: tapped again, the tempo changes and Snap to the beat stays as it was",
              st["kept"] and st["kept"]["bpm"] == 120 and st["kept"].get("snap") is False
              and pg.get_attribute("#musicSnap", "aria-pressed") == "false",
              f"over 100 a minute with the magnet off: {st['kept']}, the magnet lit {pg.get_attribute('#musicSnap', 'aria-pressed')}")
        c.close()
    for _n, _p in eds("tap"):
        def start(pg):
            pg.evaluate(SET, {"tempo": None, "s": 0, "e": 12, "xf": 0})
            press(pg, "#musicTapBtn", 0)                                       # the start
            # ...once the loop is playing (a resume can take a moment): the
            # taps are planned from where the song has got to.
            pg.wait_for_function("() => _waLoop.playing() && _waLoop.elapsed() > 0.3", timeout=5000)
        c, pg, got, k = in_time(b, _n, _p, ON_BEAT, {"off": 0.12, "n": 6}, prep=start)
        pg.wait_for_timeout(2300)
        st = pg.evaluate(SAID)
        ph = st["kept"]["phase"] if st["kept"] else None

        def mean_of(xs):
            x = sum(math.cos(2 * math.pi * s / 0.5) for s in xs); y = sum(math.sin(2 * math.pi * s / 0.5) for s in xs)
            return (math.atan2(y, x) / (2 * math.pi) * 0.5) % 0.5
        # The handler's own mean is between the two readings' (the tempo keeps
        # four places: half a millisecond either side).
        lo, hi = sorted((mean_of(got["seen"]), mean_of(got["after"])))
        stepped = sum(1 for a, z in zip(got["seen"], got["after"]) if abs(z - a) > 1e-9)
        check(f"{_n}: where the beat falls is the taps' own, read off the song's clock as heard",
              ph is not None and st["kept"]["bpm"] == 120 and got["lat"] > 0 and lo - 0.0005 <= ph <= hi + 0.0005 and phase_gap(ph, 0.12) < 0.04,
              f"tapped 0.12s past each half second as heard ({got['lat'] * 1000:.0f}ms after the clock; the song's clock, less that, said {lo:.4f} on average"
              + (f" to {hi:.4f}, stepping in the tap on {stepped} of {len(got['seen'])}" if stepped else "") + f", beside the tap's own handler): {st['kept']}"
              f" (taps within {got['spread']:.1f}ms of their marks, try {k})")
        c.close()

    print("\nMUSIC BEAT — the nearest beat")
    # A drag on the timeline as a finger makes one, from the handle to `t`
    # seconds on the song, let go; then the settle's glide, read on every
    # frame from just before the finger lifts. Where `t` is past what is in
    # view, the finger holds at the edge until the view has widened to it,
    # then goes there, as a person does (lib/musictimeline.js widen).
    TL = ("(id) => { const s = document.getElementById('musicTlStage').getBoundingClientRect(), h = document.getElementById(id).getBoundingClientRect(),"
          " v = (document.getElementById('musicTimeline').dataset.view || '0 1').split(' ').map(Number);"
          " return { x: s.left, w: s.width, hx: h.left + h.width / 2, hy: h.top + h.height / 2, v0: v[0], span: v[1], d: audioDuration }; }")
    REC = """() => { const out = window.__rec = [], t0 = performance.now();
      (function f() { out.push([performance.now() - t0, trimStart, trimEnd]); if (performance.now() - t0 < 700) requestAnimationFrame(f); })(); }"""

    def tl_drag(pg, handle, t, rec=False):
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        at = pg.evaluate(TL, handle)
        x_of = lambda a: a["x"] + (t - a["v0"]) / a["span"] * a["w"]   # noqa: E731
        # Clear of the edge's zone, or as clear as it gets: where the view
        # already shows the song's start (or its end), it widens no further.
        inside = lambda a: ((a["x"] + 36 <= x_of(a) or (handle == "tlStart" and a["v0"] <= 0))   # noqa: E731
                            and (x_of(a) <= a["x"] + a["w"] - 36 or (handle == "tlEnd" and a["v0"] + a["span"] >= a["d"])))
        pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down()
        if not inside(at):
            pg.mouse.move(at["x"] + (at["w"] - 3 if handle == "tlEnd" else 3), at["hy"], steps=6)
            for _ in range(160):
                pg.wait_for_timeout(50)
                if inside(pg.evaluate(TL, handle)):
                    break
            # Out of the edge's zone first, where the view holds still, and
            # only then read where `t` is (still widening, the view moved
            # under the old reading).
            pg.mouse.move(at["x"] + (at["w"] - 44 if handle == "tlEnd" else 44), at["hy"], steps=2)
            pg.wait_for_timeout(120)
            at = pg.evaluate(TL, handle)
        x = x_of(at)
        pg.mouse.move(x, at["hy"], steps=6)
        let_go = pg.evaluate(TRIM)
        if rec:
            pg.evaluate(REC)
        pg.mouse.up(); pg.wait_for_timeout(800 if rec else 450)
        return let_go, pg.evaluate(TRIM), (pg.evaluate("() => window.__rec") if rec else None)

    for _n, _p in eds("bars"):
        c, pg, errs = editor(b, _n, _p, door=None)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0.5, "e": 4.75, "xf": 250})
        # NEAREST BEAT, NOT WHOLE BARS (the owner: "it kept snapping"; of the
        # mock, "all yes"): 10.6 beats heard settles on 11 (whole bars went
        # back to 8), 12.8 on 13 (on to 16).
        g1, t1, _ = tl_drag(pg, "tlEnd", 0.5 + 5.3 + 0.25)
        g2, t2, rec = tl_drag(pg, "tlEnd", 0.5 + 6.4 + 0.25, rec=True)
        said = pg.evaluate(SAID)
        check(f"{_n}: an end let go on the timeline settles on the nearest beat, smooth restart and all, the start kept",
              abs(heard(g1) / 0.5 - 10.6) < 0.15 and abs(heard(t1) - 5.5) < 1e-6 and abs(heard(g2) / 0.5 - 12.8) < 0.15 and abs(heard(t2) - 6.5) < 1e-6
              and t1["s"] == t2["s"] == 0.5 and t2["xf"] == 250 and said["line"].startswith("6.50s · 13 beats"),
              f"let go at {heard(g1) / 0.5:.2f} beats: {heard(t1) / 0.5:.3f}; at {heard(g2) / 0.5:.2f}: {heard(t2) / 0.5:.3f}; start {t2['s']}; {said['line']!r}")
        ends = [f[2] for f in rec]
        moving = [f for f in rec if abs(f[2] - g2["e"]) > 1e-6 and abs(f[2] - t2["e"]) > 1e-6]
        done = next((f[0] for f in rec if abs(f[2] - t2["e"]) < 1e-6), None)
        steps = all(b2 >= a2 - 1e-9 for a2, b2 in zip(ends, ends[1:]))
        check(f"{_n}: the settle glides there, frame by frame, the timeline and the line together",
              len(moving) >= 5 and steps and done is not None and done < 450,
              f"{len(moving)} frames on the way from {g2['e']:.3f} to {t2['e']:.3f}, there at {done and round(done)}ms; always onward {steps}")
        # Off the beat, with the end off it too: the start let go at 3.15
        # lands on the beat at 3.0, from where the end, 8.4, is 5.15s heard,
        # 10.3 beats, so the end follows to 10 (whole bars took it to 8).
        pg.evaluate(LOOP, {"s": 0.5, "e": 8.4})
        g3, t3, _ = tl_drag(pg, "tlStart", 3.15)
        check(f"{_n}: the start let go lands on the nearest beat, and the end follows so the loop is whole beats",
              abs(g3["s"] - 3.15) < 0.06 and abs(t3["s"] - 3.0) < 1e-6 and abs(heard(t3) - 5.0) < 1e-6 and abs(t3["e"] - 8.25) < 1e-6,
              f"let go at {g3['s']:.3f}: {t3['s']:.4f}-{t3['e']:.4f}, heard {heard(t3) / 0.5:.3f} beats")
        # A start set off the beat (typed, or placed with the magnet off) is
        # the person's: an end let go counts its beats from there.
        pg.evaluate(LOOP, {"s": 1.23, "e": 5.0})
        g4, t4, _ = tl_drag(pg, "tlEnd", 1.23 + 4.4 + 0.25)     # 8.8 beats heard: 9 is nearest (whole bars were 8)
        check(f"{_n}: an end let go counts whole beats from the start wherever it is: a start off the beat is never moved",
              t4["s"] == 1.23 and abs(heard(t4) - 4.5) < 1e-6 and abs(heard(g4) / 0.5 - 8.8) < 0.15,
              f"the start at 1.23, the end let go at {heard(g4) / 0.5:.2f} beats: {t4['s']}-{t4['e']:.4f}, heard {heard(t4) / 0.5:.3f}")
        check(f"{_n}: no page errors through the nearest beat", not errs, "; ".join(errs[:2]))
        c.close()
    for _n, _p in eds("bars"):
        # Let go at a 6s song's very end, 11.5 beats heard, 12 is nearest but
        # 6.25s is past the song; at 90 a minute at the 20s cap, 29.6 beats,
        # 30 is past the cap: the beats there is room for, one fewer.
        c, pg, errs = editor(b, _n, _p, song=SHORT, door=None)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 3.0, "xf": 250})
        g1, t1, _ = tl_drag(pg, "tlEnd", 6.3)                    # past the song: the end holds at 6.0
        add(pg, LONG)
        pg.evaluate(SET, {"tempo": {"bpm": 90, "phase": 0}, "s": 0, "e": 5.0, "xf": 250})
        g2, t2, _ = tl_drag(pg, "tlEnd", 20.6)                   # past the cap: the end holds at 20.0
        p90 = 60 / 90
        check(f"{_n}: beats the song or the 20s cap has no room for are passed over, for the nearest there is room for",
              heard(g1) / 0.5 > 11.49 and abs(heard(t1) - 5.5) < 1e-6 and heard(g2) / p90 > 29.6 and abs(heard(t2) - 29 * p90) < 1e-6,
              f"a 6s song let go at {heard(g1) / 0.5:.2f} beats: {heard(t1) / 0.5:.3f}; at 90 a minute let go at {heard(g2) / p90:.2f}: {heard(t2) / p90:.3f}")
        c.close()
    for _n, _p in eds("bars"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **DESK))
        c, pg, errs = editor(b, _n, _p, ctx=c, door=None)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0.5, "e": 4.75, "xf": 250})
        g, t, rec = tl_drag(pg, "tlEnd", 0.5 + 6.4 + 0.25, rec=True)
        between = [f for f in rec if abs(f[2] - g["e"]) > 1e-6 and abs(f[2] - t["e"]) > 1e-6]
        check(f"{_n}: under Reduce Motion the settle is at once, nothing on the way",
              abs(heard(t) - 6.5) < 1e-6 and not between, f"from {g['e']:.3f} to {t['e']:.3f}; {len(between)} frames between")
        c.close()
    for _n, _p in eds("bars"):
        c, pg, errs = editor(b, _n, _p, door=None)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.1}, "s": 0.5, "e": 4.75, "xf": 250})
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        r = pg.evaluate(TL, "tlEnd")
        # The song under the drawing, grabbed between the ends and moved left:
        # the song goes with the finger, so the loop starts 0.37s later.
        x0, y0 = r["x"] + r["w"] * 0.45, r["hy"] + 20
        dx = -0.37 / r["span"] * r["w"]
        pg.mouse.move(x0, y0); pg.mouse.down()
        pg.mouse.move(x0 + dx / 2, y0, steps=4); pg.mouse.move(x0 + dx, y0, steps=4)
        g = pg.evaluate(TRIM)
        pg.mouse.up(); pg.wait_for_timeout(500)
        t = pg.evaluate(TRIM)
        check(f"{_n}: the song slid under the drawing settles the loop's start on a beat, its length kept",
              abs(g["s"] - 0.87) < 0.03 and abs(t["s"] - 1.1) < 1e-6 and abs((t["e"] - t["s"]) - 4.25) < 1e-6,
              f"let go at {g['s']:.3f}: {t['s']:.4f}-{t['e']:.4f} (beats at 0.1 + k/2)")
        c.close()

    print("\nMUSIC BEAT — Beats")
    # Beats as it stands: shown, the counts offered and those pressed, its
    # free state, and what the one line offers.
    BEATS = """() => { const q = (id) => document.getElementById(id), r = q('musicBeatsRow'), seg = q('musicBeatsSeg'),
        bs = seg ? [...seg.querySelectorAll('button')] : [];
      return { shown: !!r && !r.hidden && r.getClientRects().length > 0, offered: bs.filter((x) => !x.hidden).map((x) => +x.dataset.beats),
               lit: bs.filter((x) => x.getAttribute('aria-pressed') === 'true').map((x) => +x.dataset.beats),
               on: bs.filter((x) => x.classList.contains('on')).length, free: !!seg && seg.hasAttribute('data-free'),
               tag: q('musicPickCard').getAttribute('aria-pressed') === 'true',
               back: q('musicPickCard').getAttribute('aria-pressed') !== 'true' && !q('musicPickCard').disabled, undo: !q('musicUndo').disabled,
               s: trimStart, e: trimEnd, xf: loopCrossfadeMs }; }"""
    # Every frame from just before a tap: the loop's ends and the counts
    # pressed; and when the tap landed.
    BEATS_REC = """() => { const out = window.__rec = [], t0 = performance.now(), seg = document.getElementById('musicBeatsSeg');
      window.__tapAt = null;
      seg.addEventListener('click', () => { window.__tapAt = performance.now() - t0; }, { capture: true, once: true });
      (function f() { out.push([performance.now() - t0, trimStart, trimEnd,
          [...seg.querySelectorAll('button')].filter((x) => x.getAttribute('aria-pressed') === 'true').map((x) => +x.dataset.beats)]);
        if (performance.now() - t0 < 800) requestAnimationFrame(f); })(); }"""
    # What is under Beats (Lock) as a beat lands and Beats opens out, against
    # the three choices above it, in the Length door.
    BEATS_OPEN = """() => new Promise((res) => { const out = [], t0 = performance.now(),
        top = document.querySelector('#musicDoorLength .mt-lengths'), lock = document.getElementById('musicLock').closest('.mt-switch');
      const read = () => out.push([performance.now() - t0, lock.getBoundingClientRect().top - top.getBoundingClientRect().bottom]);
      read(); musicTempo = { bpm: 120, phase: 0 }; updateTrimUI();
      (function f() { read(); if (performance.now() - t0 < 700) requestAnimationFrame(f); else res(out); })(); })"""

    # The page as a beat lands, every frame for 1.6s: where it is scrolled to,
    # and the timeline's top on the screen.
    STILL = """() => new Promise((res) => { const out = [], t0 = performance.now(), tl = document.getElementById('musicTlStage');
      const read = () => out.push([performance.now() - t0, scrollY, tl.getBoundingClientRect().top]);
      read(); musicTempo = { bpm: 120, phase: 0 }; updateTrimUI();
      (function f() { read(); if (performance.now() - t0 < 1600) requestAnimationFrame(f); else res(out); })(); })"""

    def beats(pg, n, ms=450):
        return press(pg, f'#musicBeatsSeg button[data-beats="{n}"]', ms)

    for _n, _p in eds("beats"):
        c, pg, errs = editor(b, _n, _p, door="length")
        b0 = pg.evaluate(BEATS)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0.5, "e": 4.75, "xf": 250})
        pg.wait_for_timeout(400)
        b1 = pg.evaluate(BEATS)
        where = pg.evaluate("""() => { const r = (id) => document.getElementById(id).getBoundingClientRect();
          return { line: document.querySelector('#musicDoorLength .mt-lengths').getBoundingClientRect().bottom, row: r('musicBeatsRow').top,
                   end: r('musicBeatsRow').bottom, pair: document.getElementById('musicLock').closest('.mt-switch').getBoundingClientRect().top }; }""")
        add(pg, LONG)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 4.25, "xf": 250})
        b2 = pg.evaluate(BEATS)
        pg.evaluate(SET, {"tempo": {"bpm": 90, "phase": 0}})
        b3 = pg.evaluate(BEATS)
        check(f"{_n}: Beats shows in the Length door, under its three choices and over Lock, once there is a beat, with the counts the song and the 20s cap have room for, the loop's own lit",
              not b0["shown"] and b1["shown"] and where["line"] <= where["row"] + 0.5 and where["end"] <= where["pair"] + 0.5
              and b1["offered"] == [4, 8, 16] and b1["lit"] == [8] and b2["offered"] == [4, 8, 16, 32] and b2["lit"] == [8]
              and b3["offered"] == [4, 8, 16],
              f"no beat: shown {b0['shown']}; a 12s song at 120, the loop 8 beats: {b1['offered']}, lit {b1['lit']}; {where}; "
              f"a minute's song at 120: {b2['offered']}, lit {b2['lit']}; at 90 (32 beats would be 21.6s): {b3['offered']}")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 4.37, "xf": 250})   # 8.24 beats: near 8, and not 8
        b4 = pg.evaluate(BEATS)
        check(f"{_n}: a loop that is not whole bars, 8.24 beats, has none lit, and none pressed (the free state a screen reader is told)",
              b4["shown"] and b4["lit"] == [] and b4["on"] == 0 and b4["free"], f"{b4}")
        c.close()
    for _n, _p in eds("beats"):
        c, pg, errs = editor(b, _n, _p, door="length")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0.5, "e": 4.75, "xf": 250})
        pg.wait_for_timeout(300)
        beats(pg, 16)
        t1 = pg.evaluate(BEATS)
        beats(pg, 4)
        t2 = pg.evaluate(BEATS)
        check(f"{_n}: a count tapped on a loop of the person's own keeps the start and makes the loop that many beats, smooth restart and all, lit",
              t1["s"] == 0.5 and abs(heard(t1) - 8.0) < 1e-6 and t1["lit"] == [16] and t2["s"] == 0.5 and abs(heard(t2) - 2.0) < 1e-6
              and t2["lit"] == [4] and t1["xf"] == t2["xf"] == 250,
              f"16: {t1['s']}-{t1['e']:.4f}, lit {t1['lit']}; then 4: {t2['s']}-{t2['e']:.4f}, lit {t2['lit']}; smooth restart {t1['xf']}, {t2['xf']}")
        press(pg, "#musicUndo", 300)
        u = pg.evaluate(BEATS)
        press(pg, "#musicUndo", 300)
        u2 = pg.evaluate(BEATS)
        check(f"{_n}: each tap is a step the loop's Undo takes back, a tap at a time, Skribl's pick beside it as the way back",
              t2["undo"] and t2["back"] and not t2["tag"] and abs(u["s"] - 0.5) < 1e-9 and abs(u["e"] - 8.75) < 1e-9 and u["lit"] == [16]
              and u["undo"] and u["back"] and abs(u2["s"] - 0.5) < 1e-9 and abs(u2["e"] - 4.75) < 1e-9 and not u2["undo"],
              f"after the taps: Undo {t2['undo']}, the way back {t2['back']}; Undo: {u['s']}-{u['e']:.4f}, lit {u['lit']}, Undo still {u['undo']},"
              f" the way back {u['back']}; Undo again: {u2['s']}-{u2['e']:.4f}, Undo then {u2['undo']}")
        pg.evaluate(LOOP, {"s": 6.0, "e": 10.25})
        beats(pg, 16)
        t3 = pg.evaluate(BEATS)
        check(f"{_n}: near the song's end the loop moves back by whole beats, only as far as it must",
              abs(t3["s"] - 3.5) < 1e-6 and abs(t3["e"] - 11.75) < 1e-6 and t3["lit"] == [16],
              f"16 beats from 6.0 on a 12s song: {t3['s']:.4f}-{t3['e']:.4f}, lit {t3['lit']}")
        # Two taps 60ms apart, from inside the page: the second while the first glides.
        pg.evaluate(LOOP, {"s": 6.0, "e": 10.25})
        mid = pg.evaluate("""() => new Promise((res) => { const q = (n) => document.querySelector('#musicBeatsSeg button[data-beats="' + n + '"]');
          q(16).click(); setTimeout(() => { const at = trimStart; q(4).click(); res(at); }, 60); })""")
        pg.wait_for_timeout(450)
        t4 = pg.evaluate(BEATS)
        press(pg, "#musicUndo", 300)
        t5 = pg.evaluate(BEATS)
        check(f"{_n}: a second tap while the loop glides counts from where it lands, and Undo goes back to where the first put it",
              3.5 + 1e-6 < mid <= 6.0 and abs(t4["s"] - 3.5) < 1e-6 and abs(heard(t4) - 2.0) < 1e-6 and t4["lit"] == [4]
              and abs(t5["s"] - 3.5) < 1e-6 and abs(t5["e"] - 11.75) < 1e-6,
              f"the second tap with the start at {mid:.3f}, on its way from 6.0 to 3.5: {t4['s']:.4f}-{t4['e']:.4f}, lit {t4['lit']}; Undo: {t5['s']:.4f}-{t5['e']:.4f}")
        check(f"{_n}: no page errors through Beats", not errs, "; ".join(errs[:2]))
        c.close()
    # The same in the Beat door, where Beats in a bar opens as the beat lands
    # (with Snap to the beat's row there too, they scrolled the page 61-63px
    # on a phone and 139px on a desk, and verify_musictempo's tap on the
    # end's tab, read a moment before, landed on the whole song's line and
    # moved the loop to the song's end).
    OPENS = {"length": "Beats opens", "beat": "Beats in a bar opens in the Beat door"}
    for _n, _p in eds("beats"):
        for door, opens in OPENS.items():
            for dev, opts in (("phone", PHONE), ("desk", DESK)):
                # Where the song's landing left the page (its follow brings the
                # drawer's end on screen), once that follow is over.
                c, pg, errs = editor(b, _n, _p, door=door, opts=opts)
                pg.wait_for_timeout(1500)
                rec = pg.evaluate(STILL)
                ys, tops = sorted({round(f[1]) for f in rec}), [f[2] for f in rec]
                check(f"{_n}: as the beat lands and {opens}, the page stays still: nothing scrolls it ({dev})",
                      len(ys) == 1 and max(tops) - min(tops) < 0.5,
                      f"scrolled to {ys}; the timeline's top moved {max(tops) - min(tops):.1f}px")
                c.close()
    for _n, _p in eds("beats"):
        for still in (False, True):
            c = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", **DESK))
            c, pg, errs = editor(b, _n, _p, ctx=c, door="length")
            pg.evaluate("() => document.getElementById('musicDoorLength').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
            rec = pg.evaluate(BEATS_OPEN)
            v = [f[1] for f in rec]
            total, way = v[-1] - v[0], [x for x in v if abs(x - v[0]) > 0.5 and abs(x - v[-1]) > 0.5]
            big = max((abs(y - x) for x, y in zip(v, v[1:])), default=0)
            pg.evaluate(LOOP, {"s": 6.0, "e": 10.25})
            pg.wait_for_timeout(300)
            pg.evaluate(BEATS_REC)
            beats(pg, 16, 900)
            fr, at = pg.evaluate("() => window.__rec"), pg.evaluate("() => window.__tapAt")
            after = [f for f in fr if at is not None and f[0] >= at]
            moving = [f for f in after if abs(f[1] - 6.0) > 1e-6 and abs(f[1] - 3.5) > 1e-6]
            onward = all(y[1] <= x[1] + 1e-9 for x, y in zip(after, after[1:]))
            lit = {tuple(f[3]) for f in after}
            if not still:
                check(f"{_n}: Beats opens out as the beat lands, Lock under it gliding down frame by frame",
                      total > 30 and len(way) >= 4 and big <= 0.6 * total, f"{total:.1f}px in all, {len(way)} frames on the way, the largest {big:.1f}px")
                check(f"{_n}: a tap glides the loop there frame by frame, the count lit from the tap all the way",
                      len(moving) >= 5 and onward and lit == {(16,)} and abs(after[-1][1] - 3.5) < 1e-6,
                      f"{len(moving)} frames on the way from 6.0 to {after[-1][1] if after else None}; always onward {onward}; lit on the way {sorted(lit)}")
            else:
                check(f"{_n}: under Reduce Motion Beats is there at once, and so is the loop a tap makes",
                      total > 30 and not way and not moving and lit == {(16,)} and bool(after) and abs(after[-1][1] - 3.5) < 1e-6,
                      f"{total:.1f}px, {len(way)} frames on the way; the loop {len(moving)} frames on the way; lit {sorted(lit)}")
            c.close()

    b.close()

summarise_and_exit()
