#!/usr/bin/env python3
"""The music drawer's pair and its beat (owner: "How do I test the loop without
having it show me drawing? It's cumbersome, plus to know how many beats are in
the loop, so I'm not at 7 or 9 when I want 8"; "All yes" to the mock).

  THE PAIR. Play with my drawing and Hear the loop sit under the strip in the
  same place on every level, the same size, and the loop detail has no second
  Hear. Hear the loop plays the music alone, round and round, until Stop; an
  end moved while it plays is heard from its next time round.

  TAP THE BEAT. The first tap starts the loop and is not a beat. Taps in time
  settle on the tempo two seconds after the last, to the nearest whole beat a
  minute, from the middle gap (a stray one does not move it); where the beat
  falls is the taps' own, read off the song's clock less the time the sound
  takes to reach the ear. Fewer than four taps
  leave the tempo as it was, and say so. On a phone the tap stays put under
  the finger while its words change.

  MAKE IT. The three whole counts nearest what is heard; one sets what is
  heard to exactly that many beats, smooth restart and all, from the same
  start; a count the song is too short for is faded.

  EACH TAP gains one beat, in size order, only while there is a tempo.

  THE MARKS. A tick on every beat that stands 6px from the next, taller every
  four from the loop's start, and with a smooth restart a dashed line where
  the loop comes round; the loop detail marks its own window.

  SNAPPING. An end let go near a beat settles on it (the end where the loop
  comes round); far from one, or typed, it stays.

  KEPT. The tempo goes with the song into the drafts and comes back with it,
  from an autosave and from a re-add card; a new song starts with none.

  WORDS. The pair's words are whole on every phone (one to a row under
  360px), and the counts and the marks read against what is behind them.

Every row runs on the Pad and on Flip: one drawer (lib/musicdrawer.js), and
each editor's half is its hooks.
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
# MUSICBEAT_PART=pair (tap, make, steps, marks, snap, keep, words) one part.
# A real run sets neither.
ONLY = os.environ.get("MUSICBEAT_ONLY", "")
PART = os.environ.get("MUSICBEAT_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
WORK = {"Pad": "drawing", "Flip": "animation"}
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
# The drawer as it stands: what the pair, the tap and the counts say, and the tempo kept.
SAID = """() => { const q = (id) => document.getElementById(id), tx = (id) => q(id) ? q(id).textContent : null;
  return { play: tx('musicPlayLabel'), hear: tx('musicHearLabel'), tap: tx('musicTapWords'), tempo: tx('musicTempo'),
           len: tx('musicLenLine'), sync: tx('musicSyncLine'), kept: musicTempo, pv: previewingLoop, playing: playing,
           counts: [...document.querySelectorAll('#musicMake .mt-count')].map(c => [c.textContent, c.disabled, c.getAttribute('aria-pressed')]),
           make: q('musicMake') ? !q('musicMake').hidden : false }; }"""
SET = "(o) => { musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; } if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } updateTrimUI(); }"
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
# the page's clock from one reading of the song's (which moves in 8-21ms
# steps), less the time the sound takes to reach the ear; each tap says where
# the song had got to, as heard, as it landed. Woken early as TAPS is.
ON_BEAT = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'), seen = [], off = [];
  const lat = _waLoop.latency(), heard = () => trimStart + _waLoop.elapsed() - lat;
  const s0 = heard(), t0 = performance.now(), first = Math.ceil((s0 - o.off) / 0.5) * 0.5 + o.off + 0.5;
  const mark = (k) => t0 + (first + k * 0.5 - s0) * 1000;
  const go = () => { const k = seen.length; while (performance.now() < mark(k)) {} off.push(performance.now() - mark(k)); b.click(); seen.push(heard());
    if (seen.length >= o.n) { res({ seen, lat, spread: Math.max(...off) - Math.min(...off) }); return; }
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
# The marks laid in a host: each tick's left (%), whether it is a bar, and the dashed line.
MARKS = """(id) => { const box = document.querySelector('#' + id + ' .mt-ticks'), host = document.getElementById(id);
  if (!box) return null;
  return { w: host.clientWidth, ticks: [...box.querySelectorAll('i')].map(i => [parseFloat(i.style.left), i.classList.contains('bar')]),
           fold: box.querySelector('b') ? parseFloat(box.querySelector('b').style.left) : null }; }"""

# Each new word, and the marks, against what is painted behind them: the
# backgrounds from the element up, composed, as verify_contrast reads a sheet.
CONTRAST = """() => {
  const parse = (s) => { let m = s.match(/^rgba?\\(([^)]+)\\)/); if (m) { const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; }
    m = s.match(/^color\\(srgb ([^)]+)\\)/); if (m) { const p = m[1].split(/[\\s\\/]+/).filter(Boolean).map(Number); return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 }; } return null; };
  const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a }; };
  const ground = (el) => { const l = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { l.push(c); if (c.a >= 0.999) break; } }
    let acc = { r: 255, g: 255, b: 255, a: 1 }; for (let i = l.length - 1; i >= 0; i--) acc = over(l[i], acc); return acc; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
  // A word on its own ground; a mark (bg) on its host's.
  const ink = (el, bg) => { const cs = getComputedStyle(el), g = ground(bg ? el.parentElement : el), c = parse(bg ? cs.backgroundColor : cs.color);
    return ratio(over({ ...c, a: c.a * (bg ? +cs.opacity : 1) }, g), g); };
  const q = (s) => document.querySelector(s);
  return { count: ink(q('#musicMake .mt-count:not(:disabled)')), make: ink(q('#musicMake > span')), tempo: ink(q('#musicTempo')),
           tap: ink(q('#musicTapWords')), hear: ink(q('#previewLoopBtn .tp-k')), tick: ink(q('#musicTrack .mt-ticks i:not(.bar)'), true),
           bar: ink(q('#musicTrack .mt-ticks i.bar'), true) }; }"""


def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=TWELVE, opts=DESK, level="adjust"):
    c = waits.instrument(b.new_context(**opts))
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
    if level:
        pick_level(pg, level)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def pick_level(pg, level):
    pg.click({"simple": "#musicLevelSimple", "adjust": "#fineTuneTrim", "fine": "#fineTuneToggle"}[level])
    pg.wait_for_timeout(350)
    browsing.wait_scroll_still(pg)


def press(pg, sel, ms=200):
    """A real click on a control that may be missing from a broken build: a
    row then says so in red rather than the run stopping on a timeout."""
    try:
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


with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("\nMUSIC BEAT — the pair that plays")
    for _n, _p in eds("pair"):
        c, pg, errs = editor(b, _n, _p, level=None)
        at = {}
        for lv in ("simple", "adjust", "fine"):
            pick_level(pg, lv)
            at[lv] = pg.evaluate("""() => { const r = (id) => document.getElementById(id).getBoundingClientRect(), t = r('musicTrack');
                const a = r('musicPlayBtn'), h = r('previewLoopBtn');
                const hears = [...document.querySelectorAll('#fineTuneBody button')].filter(x => /hear/i.test(x.textContent)).length;
                return { below: Math.round(a.top - t.bottom), side: Math.round(a.top) === Math.round(h.top) && h.left > a.right,
                         same: Math.round(a.width) === Math.round(h.width) && Math.round(a.height) === Math.round(h.height),
                         h: Math.round(a.height), hears }; }""")
        ok = all(v["side"] and v["same"] and v["h"] >= 44 and v["hears"] == 0 for v in at.values())
        check(f"{_n}: the pair sits under the strip in the same place on every level, the same size, and the loop detail has no second Hear",
              ok and at["simple"]["below"] == at["adjust"]["below"] == at["fine"]["below"] and at["simple"]["below"] < 140, str(at))
        c.close()
    for _n, _p in eds("pair"):
        c, pg, errs = editor(b, _n, _p, level="simple")
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
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": None, "s": 0, "e": 2.0, "xf": 0})
        press(pg, "#previewLoopBtn", 500)
        first = pg.evaluate("() => { window.__src = _waLoop.source(); return _waLoop.source().buffer.duration; }")
        pg.fill("#musicTo", "3"); pg.press("#musicTo", "Enter"); pg.wait_for_timeout(150)
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
        check(f"{_n}: taps in time settle on the tempo, two seconds after the last, and the lines count the beats",
              mid["kept"] is None and mid["tap"] == "Keep tapping" and st["kept"] and st["kept"]["bpm"] == 120
              and st["tempo"] == "120 beats a minute · tap again to change it" and st["tap"] == "Tap the beat"
              and f"· {words}" in st["len"] and f"{words} at 120 a minute" in st["sync"],
              f"1.5s after: {mid['kept']}, {mid['tap']!r}; settled: {st['kept']}, {st['tempo']!r}; {st['len']!r}; {st['sync']!r}"
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
        c, pg, spread, k = in_time(b, _n, _p, TAPS, {"gaps": [600, 500, 500, 900, 500, 500]})
        pg.wait_for_timeout(2300)
        st = pg.evaluate(SAID)
        check(f"{_n}: a stray gap does not move the tempo: the middle gap counts",
              st["kept"] and st["kept"]["bpm"] == 120,
              f"gaps 0.5, 0.5, 0.9, 0.5, 0.5: {st['kept']} (taps within {spread:.1f}ms of their marks, try {k})")
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
        seen = got["seen"]
        x = sum(math.cos(2 * math.pi * s / 0.5) for s in seen); y = sum(math.sin(2 * math.pi * s / 0.5) for s in seen)
        mean = (math.atan2(y, x) / (2 * math.pi) * 0.5) % 0.5
        check(f"{_n}: where the beat falls is the taps' own, read off the song's clock as heard",
              ph is not None and st["kept"]["bpm"] == 120 and got["lat"] > 0 and phase_gap(ph, mean) < 0.005 and phase_gap(ph, 0.12) < 0.04,
              f"tapped 0.12s past each half second as heard ({got['lat'] * 1000:.0f}ms after the clock; the song's clock, less that, said {mean:.4f} on average): {st['kept']}"
              f" (taps within {got['spread']:.1f}ms of their marks, try {k})")
        c.close()

    print("\nMUSIC BEAT — Make it")
    for _n, _p in eds("make"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0.5, "e": 5.17, "xf": 250})
        st = pg.evaluate(SAID)
        check(f"{_n}: Make it offers the three whole counts nearest what is heard",
              st["make"] and [x[0] for x in st["counts"]] == ["8", "9", "10"] and not any(x[1] for x in st["counts"])
              and all(x[2] == "false" for x in st["counts"]),
              f"heard {heard(pg.evaluate(TRIM)):.3f}s at 120: {st['counts']}")
        pressed = press(pg, "#musicMake .mt-count >> nth=0")
        t, st = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: Make it 8 makes what is heard 8 beats exactly, smooth restart and all, from the same start",
              pressed and abs(t["s"] - 0.5) < 1e-9 and abs(heard(t) - 4.0) < 0.001 and t["xf"] == 250
              and [x[0] for x in st["counts"]] == ["7", "8", "9"] and st["counts"][1][2] == "true" and st["len"].startswith("4.00s · 8 beats"),
              f"{t['s']}-{t['e']:.3f} with {t['xf']}ms: heard {heard(t):.4f}s; {st['counts']}; {st['len']!r}")
        c.close()
    for _n, _p in eds("make"):
        c, pg, errs = editor(b, _n, _p, song=SHORT)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 6, "xf": 250})
        st = pg.evaluate(SAID)
        check(f"{_n}: a count the song is too short for is faded",
              [x[0] for x in st["counts"]] == ["11", "12", "13"] and [x[1] for x in st["counts"]] == [False, True, True],
              f"a 6s song, heard {heard(pg.evaluate(TRIM)):.2f}s: {st['counts']}")
        c.close()

    print("\nMUSIC BEAT — Each tap's beat")
    for _n, _p in eds("steps"):
        c, pg, errs = editor(b, _n, _p, level="fine")
        order = "() => [...document.querySelectorAll('#musicStepSeg button[data-step]')].filter(x => !x.hidden).map(x => x.dataset.step)"
        none = pg.evaluate(order)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 3, "xf": 0})
        at120 = pg.evaluate(order)
        pg.evaluate(SET, {"tempo": {"bpm": 30, "phase": 0}})
        at30 = pg.evaluate(order)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}})
        press(pg, "#musicStepSeg [data-step='beat']", 100)
        e0 = pg.evaluate(TRIM)["e"]
        press(pg, ".nudge-btn[data-which='end'][data-amount='1']", 150)
        e1 = pg.evaluate(TRIM)["e"]
        pg.evaluate(SET, {"tempo": None})
        gone = pg.evaluate("() => [document.querySelector('#musicStepSeg [data-step=\"beat\"]').hidden, document.querySelector('#musicStepSeg button.on').dataset.step]")
        check(f"{_n}: Each tap gains one beat, in size order, only while there is a tempo",
              "beat" not in none and at120 == ["0.01", "frame", "0.1", "beat", "1"] and at30 == ["0.01", "frame", "0.1", "1", "beat"]
              and abs((e1 - e0) - 0.5) < 1e-6 and gone == [True, "0.1"],
              f"no tempo {none}; at 120 {at120}; at 30 {at30}; one tap {e0:.3f}->{e1:.3f}; tempo gone: {gone}")
        c.close()

    print("\nMUSIC BEAT — the beat, marked")
    for _n, _p in eds("marks"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 1.0, "e": 5.25, "xf": 250})
        m = pg.evaluate(MARKS, "musicTrack")
        want = [k * 0.5 / 12 * 100 for k in range(25)]
        bars = [round(x[0] / 100 * 12 / 0.5) for x in (m["ticks"] if m else []) if x[1]]
        check(f"{_n}: the strip marks every beat, taller every four from the loop's start, with a dashed line where it comes round",
              m is not None and len(m["ticks"]) == 25 and all(abs(a[0] - w) < 0.01 for a, w in zip(m["ticks"], want))
              and bars == [2, 6, 10, 14, 18, 22] and m["fold"] is not None and abs(m["fold"] - 5.0 / 12 * 100) < 0.01,
              f"{len(m['ticks']) if m else None} ticks, bars at beats {bars}, the dashed line at {m and m['fold']}% (want {5 / 12 * 100:.3f})")
        c.close()
    for _n, _p in eds("marks"):
        c, pg, errs = editor(b, _n, _p, song=LONG)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 8, "xf": 0})
        m = pg.evaluate(MARKS, "musicTrack")
        px = [(m["ticks"][i + 1][0] - m["ticks"][i][0]) / 100 * m["w"] for i in range(len(m["ticks"]) - 1)] if m else []
        k = [round(x[0] / 100 * 60 / 0.5) for x in (m["ticks"] if m else [])]
        check(f"{_n}: a long song marks only as many beats as stand 6px apart",
              m is not None and px and min(px) >= 6 and all(x % 4 == 0 for x in k) and len(k) >= 20 and m["fold"] is None,
              f"{len(k)} marks on a {m and m['w']}px strip, the closest {min(px) if px else None:.1f}px apart, at beats {k[:6]}...")
        c.close()
    for _n, _p in eds("marks"):
        c, pg, errs = editor(b, _n, _p, level="fine")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.1}, "s": 1.0, "e": 3.0, "xf": 0})
        pg.wait_for_timeout(200)
        m, zw = pg.evaluate(MARKS, "zoomTrackWrap"), pg.evaluate("() => getZoomWindow()")
        want = [(0.1 + k * 0.5 - zw["start"]) / zw["duration"] * 100 for k in range(0, 40) if zw["start"] - 1e-9 <= 0.1 + k * 0.5 <= zw["end"] + 1e-9]
        got = [x[0] for x in m["ticks"]] if m else []
        check(f"{_n}: the loop detail marks the beats in its own window",
              m is not None and len(got) == len(want) and len(got) >= 4 and all(abs(a - w) < 0.01 for a, w in zip(got, want)),
              f"window {zw['start']:.2f}-{zw['end']:.2f}s: marks at {[round(x, 1) for x in got]}, want {[round(x, 1) for x in want]}")
        c.close()

    print("\nMUSIC BEAT — an end settles on a beat")
    for _n, _p in eds("snap"):
        c, pg, errs = editor(b, _n, _p, song=SHORT)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 3.0, "xf": 250})
        # A tempo grows the drawer (Make it), and the page follows its end:
        # read the handle where it is once that has settled, before each drag.
        pg.wait_for_timeout(1300); browsing.wait_scroll_still(pg)
        HANDLE = ("() => { const r = document.getElementById('musicTrack').getBoundingClientRect(), h = document.getElementById('handleEnd').getBoundingClientRect();"
                  " return { x: r.left, w: r.width, hx: h.left + h.width / 2, hy: h.top + h.height / 2 }; }")
        box = pg.evaluate(HANDLE)
        def drag_to(t):
            at = pg.evaluate(HANDLE)
            x = at["x"] + t / 6 * at["w"]
            pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down()
            pg.mouse.move((at["hx"] + x) / 2, at["hy"], steps=4); pg.mouse.move(x, at["hy"], steps=4)
            pg.mouse.up(); pg.wait_for_timeout(200)
            return pg.evaluate(TRIM)
        near = drag_to(4.0 + 0.25 + 3 / box["w"] * 6)            # 3px past the 8th beat, as heard
        far = drag_to(4.0 + 0.25 + 0.25)                          # half a beat on: about 17px from either
        check(f"{_n}: an end let go near a beat settles on it; far from one, it stays",
              abs((near["e"] - 0.25) - 4.0) < 1e-6 and abs(far["e"] - 4.5) < 0.04 and abs((far["e"] - 0.25) / 0.5 - round((far["e"] - 0.25) / 0.5)) > 0.2,
              f"let go 3px past a beat: end {near['e']:.4f} (comes round at {near['e'] - 0.25:.4f}); half a beat on: {far['e']:.4f}")
        pick_level(pg, "adjust")
        pg.fill("#musicTo", "3.27"); pg.press("#musicTo", "Enter"); pg.wait_for_timeout(150)
        check(f"{_n}: a typed end never snaps", abs(pg.evaluate(TRIM)["e"] - 3.27) < 1e-6, str(pg.evaluate(TRIM)))
        c.close()

    print("\nMUSIC BEAT — kept with the song")
    for _n, _p in eds("keep"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 96, "phase": 0.21}})
        pg.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
        pg.wait_for_timeout(2500)
        pg.reload()
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        waits.settle(pg, 600)
        back = pg.evaluate("() => musicTempo")
        c.close()
        c, pg, errs = editor(b, _n, _p, song=None, level=None)
        browsing.pad_drawer(pg, "music")
        pg.evaluate("() => { pendingMusicMeta = { trimStart: 1, trimEnd: 3, crossfadeMs: 0, enabled: true, tempo: { bpm: 84, phase: 0.3 } }; }")
        add(pg, TWELVE)
        card = pg.evaluate("() => musicTempo")
        check(f"{_n}: the tempo is saved with the song in the drafts, and comes back with it",
              back == {"bpm": 96, "phase": 0.21} and card == {"bpm": 84, "phase": 0.3},
              f"after a reload: {back}; re-added from its card: {card}")
        add(pg, SHORT)
        st = pg.evaluate(SAID)
        check(f"{_n}: a new song starts with no tempo, and no marks",
              st["kept"] is None and not st["make"] and pg.evaluate(MARKS, "musicTrack") is None and "beats" not in st["len"],
              f"{st['kept']}; Make it shown {st['make']}; {st['len']!r}")
        c.close()

    print("\nMUSIC BEAT — words")
    # The pair's words, whole, from the smallest phone to the owner's: side by
    # side from 360px, one to a row below it.
    FIT = """() => [...document.querySelectorAll('.mt-transport .mt-play')].map(x => { const r = x.getBoundingClientRect();
      return { over: x.scrollWidth - x.clientWidth, top: Math.round(r.top), w: Math.round(r.width) }; })"""
    for _n, _p in eds("words"):
        seen = {}
        for w in (320, 360, 402):
            c, pg, errs = editor(b, _n, _p, opts=dict(PHONE, viewport={"width": w, "height": 874}), level="simple")
            seen[w] = pg.evaluate(FIT)
            c.close()
        whole = all(x["over"] <= 0 for v in seen.values() for x in v)
        rows = {w: len({x["top"] for x in v}) for w, v in seen.items()}
        check(f"{_n}: the pair's words are whole on every phone, side by side from 360px and one to a row below",
              whole and rows == {320: 2, 360: 1, 402: 1}, f"{seen}")
    for _n, _p in eds("words"):
        for theme in ("light", "dark"):
            c = waits.instrument(b.new_context(color_scheme=theme, **DESK))
            pg = c.new_page()
            browsing.goto(pg, BASE, _p)
            pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
            add(pg, TWELVE)
            pick_level(pg, "adjust")
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 4.25, "xf": 250})
            r = pg.evaluate(CONTRAST)
            words = {k: v for k, v in r.items() if k not in ("tick", "bar")}
            check(f"{_n}: the counts and the marks read against what is behind them ({theme})",
                  min(words.values()) >= 4.5 and r["tick"] >= 3 and r["bar"] >= 3,
                  ", ".join(f"{k} {v:.2f}" for k, v in r.items()))
            c.close()

    b.close()

summarise_and_exit()
