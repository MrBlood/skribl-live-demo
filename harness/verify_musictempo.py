#!/usr/bin/env python3
"""Zoomed in, the loop's ends set the beat: the start where a beat falls, the
end the tempo; and the Beat door says where its tempo came from (the owner,
zoomed in; then the picks in the whole-drawer mock, FUTURE.md 6s, step 5, from
the Wizard's "click the end of the first bar"; "All yes").

  ZOOMED IN, THE START (the owner, zoomed in on where the music begins: "how
  do I tell it where the beginning is?"). With the tempo tapped 45ms off the
  music, at 16x a start let go on the music's beat stays exactly there and a
  beat falls on it, the tempo's beats a minute kept, and the end follows on
  whole bars. The marks glide there frame by frame, at once under Reduce
  Motion. Then at 1x a start lands on the new beat, the new beat is kept
  with the song in the drafts, and tapped again the beat is the taps' own.

  THE END SETS THE TEMPO. Zoomed in, an end let go within an eighth of a beat
  of 4, 8, 16 or 32 beats stays exactly where it was let go, and the beat
  becomes the one that makes the loop exactly that many, counted from the
  loop's start and heard to where it comes round (a smooth restart's length
  before the handle): to the thousandth of a beat a minute, set by the end,
  no longer the one Skribl heard. A note says so with Undo (the Pad's toast,
  Flip's chip), clear of the header and the toolbar right under it on the
  owner's phone; Undo puts the beat back as it was, the end where it was let
  go and the drawer still open. Further off than an eighth, or at 1x, the end
  settles on whole bars at the tempo there is. The beat marks glide to the
  new beat frame by frame, at once under Reduce Motion. The beat is kept with
  the song in the drafts, and Flip's Match the beat refits a round of pages
  to it.

  WHERE THE BEAT CAME FROM. The Beat tile says it, "120 · heard", tapped or
  "118.8 · by hand", where it has room (verify_musicdoors reads every tile's
  words on two phones and a desk), its name says it in words, and the door's
  line says the loop's end set it. A start let go zoomed in moves where the
  beat falls and keeps where the beat came from, and so does Snap to the
  beat turned off and on; tapped again, the beat is the taps', tapped.

Every row runs on the Pad and on Flip: one drawer (lib/musicdrawer.js), and
each editor's half is its hooks. Skribl's ears are off here
(lib/musicears.js): the pulse below is a beat the ears would hear at once, and
the beat is set as they or a tap would set it.
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
    print("No assertions were executed. This is NOT evidence the loop's ends can set the beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICTEMPO_ONLY=Pad (or Flip) runs one editor, and
# MUSICTEMPO_PART=zoomed (or end) one part.
# A real run sets neither.
ONLY = os.environ.get("MUSICTEMPO_ONLY", "")
PART = os.environ.get("MUSICTEMPO_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)


def _wav(seconds, rate=8000):
    """A pulse twice a second, on the half seconds: 120 beats a minute."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(11000 * math.sin(2 * math.pi * 220 * i / rate) * math.exp(-((2 * i / rate) % 1) * 7)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()
TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
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

    print("\nMUSIC TEMPO — zoomed in, the start")
    # The song's beat is on the half seconds and the tempo tapped 45ms late;
    # at 16x the start is let go on the music's beat at 2.0, between the
    # marks. The mark nearest 2.0 is read on every frame from just before the
    # finger lifts.
    NEAR = """(o) => { const out = window.__recb = [], t0 = performance.now();
      (function f() { const b = ((document.getElementById('musicTimeline')._painted || {}).beats || []).map((m) => m[2]);
        out.push([performance.now() - t0, b.length ? b.reduce((a, c) => Math.abs(c - o.at) < Math.abs(a - o.at) ? c : a) : null]);
        if (performance.now() - t0 < o.ms) requestAnimationFrame(f); })(); }"""
    for _n, _p in eds("zoomed"):
        for still in (False, True):
            ctx = waits.instrument(b.new_context(reduced_motion="reduce", **DESK)) if still else None
            c, pg, errs = editor(b, _n, _p, door=None, ctx=ctx)
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.045}, "s": 2.045, "e": 6.045, "xf": 0})
            pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
            for _ in range(4):
                press(pg, "#musicTlIn", 260)
            pg.wait_for_timeout(500)
            at = pg.evaluate(TL, "tlStart")
            pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down()
            pg.mouse.move(at["x"] + (2.0 - at["v0"]) / at["span"] * at["w"], at["hy"], steps=8); pg.wait_for_timeout(100)
            let_go = pg.evaluate(TRIM)
            pg.evaluate(NEAR, {"at": 2.0, "ms": 700})
            pg.mouse.up(); pg.wait_for_timeout(900)
            got, rec, tp = pg.evaluate(TRIM), pg.evaluate("() => window.__recb"), pg.evaluate("() => musicTempo")
            # Where the beat nearest 2.0 belongs now: on the start let go.
            fin = tp["phase"] + round((2.0 - tp["phase"]) / 0.5) * 0.5 if tp else None
            seen = [f[1] for f in rec if f[1] is not None]
            between = [v for v in seen if fin is not None and fin + 1.5e-4 < v < 2.045 - 1.5e-4]
            there = next((f[0] for f in rec if f[1] is not None and fin is not None and abs(f[1] - fin) < 1.5e-4), None)
            if not still:
                k = tp and (tp["phase"] - got["s"]) / 0.5
                check(f"{_n}: zoomed in, a start let go stays exactly where it was let go, and a beat falls on it, the tempo's beats a minute kept",
                      abs(got["s"] - let_go["s"]) < 1e-6 and abs(let_go["s"] - 2.0) < 0.01 and tp is not None and tp["bpm"] == 120
                      and abs(k - round(k)) * 0.5 < 1e-4 and tp.get("snap", True) is not False,
                      f"let go at {let_go['s']:.4f}: {got['s']:.4f}; the tempo {tp}")
                n = heard(got) / 0.5
                check(f"{_n}: ...and the end follows on whole bars from it",
                      any(abs(n - q) < 1e-6 for q in (4, 8, 16, 32)), f"{got['s']:.4f}-{got['e']:.4f}, {n:.3f} beats heard")
                check(f"{_n}: the beat marks glide there, frame by frame, the shorter way round",
                      len(between) >= 4 and all(b2 <= a2 + 1.5e-4 for a2, b2 in zip(seen, seen[1:])) and there is not None and there < 600,
                      f"{len(between)} frames on the way from 2.045 to {fin}; always back {all(b2 <= a2 + 1.5e-4 for a2, b2 in zip(seen, seen[1:]))}; "
                      f"there at {there and round(there)}ms")
                # Then at 1x a start let go lands on the new beat, not the taps' (2.045 + k/2).
                for _ in range(4):
                    press(pg, "#musicTlOut", 260)
                pg.wait_for_timeout(500)
                g2, t2, _ = tl_drag(pg, "tlStart", 3.13)
                want = tp["phase"] + round((3.13 - tp["phase"]) / 0.5) * 0.5
                check(f"{_n}: then at 1x a start let go lands on the new beat",
                      abs(t2["s"] - want) < 1e-6 and abs(want - 3.0) < 0.01 and abs(g2["s"] - 3.13) < 0.06,
                      f"let go at {g2['s']:.3f}: {t2['s']:.4f} (the new beat {want:.4f}; the taps' was 3.045)")
                pg.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
                pg.wait_for_timeout(2500)
                pg.reload()
                pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
                waits.settle(pg, 600)
                back = pg.evaluate("() => musicTempo")
                check(f"{_n}: the new beat is kept with the song in the drafts", back == tp, f"{tp} -> after a reload {back}")
            else:
                check(f"{_n}: under Reduce Motion the start stays and the beat marks are there at once",
                      abs(got["s"] - let_go["s"]) < 1e-6 and not between and there is not None,
                      f"let go at {let_go['s']:.4f}: {got['s']:.4f}; {len(between)} frames on the way; there at {there and round(there)}ms")
            check(f"{_n}: no page errors zoomed in{' under Reduce Motion' if still else ''}", not errs, "; ".join(errs[:2]))
            c.close()

    for _n, _p in eds("zoomed"):
        # Tapped again after a start set zoomed in made 2.0 a beat, the beat is
        # the taps' own: tapped 0.12s past each half second as heard.
        def start(pg):
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 1.9999}, "s": 0, "e": 12, "xf": 0})
            press(pg, "#musicTapBtn", 0)                                       # the start
            pg.wait_for_function("() => _waLoop.playing() && _waLoop.elapsed() > 0.3", timeout=5000)
        c, pg, got, k = in_time(b, _n, _p, ON_BEAT, {"off": 0.12, "n": 6}, prep=start)
        pg.wait_for_timeout(2300)
        st = pg.evaluate(SAID)
        ph = st["kept"]["phase"] if st["kept"] else None
        check(f"{_n}: tapped again after that, the beat is the taps' own",
              ph is not None and st["kept"]["bpm"] == 120 and phase_gap(ph, 0.12) < 0.04 and phase_gap(ph, 1.9999) > 0.08,
              f"a beat at 2.0 (1.9999), then tapped 0.12s past each half second: {st['kept']} (taps within {got['spread']:.1f}ms of their marks, try {k})")
        c.close()

    print("\nMUSIC TEMPO — zoomed in, the end sets the tempo")
    # The pulse's beat is on the half seconds and Skribl heard it (120, heard);
    # at 16x around the loop's end, an end let go 40ms past 8 beats heard is
    # 8.08 beats, within an eighth of 8, and one at 5.90 is 7.8, further off.
    # The beat mark nearest 6.02 is read on every frame from just before the
    # finger lifts (NEAR, above).
    NOTE = """() => { const t = document.getElementById('toast') || document.getElementById('flipChip');
      if (!t) return null;
      const box = (el) => { if (!el || !el.getClientRects().length) return null; const r = el.getBoundingClientRect(); return (r.width || r.height) ? r : null; };
      const a = t.getBoundingClientRect(), b = t.querySelector('.toast-action'), hd = box(document.querySelector('.header')),
            br = box(document.getElementById('toolBar') || document.querySelector('.flip-tools'));
      const hit = (r) => !!r && a.top < r.bottom && a.bottom > r.top && a.left < r.right && a.right > r.left;
      return { words: [...t.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(''), undo: b ? b.textContent : null,
               shown: !t.hidden && t.classList.contains('show'), top: Math.round(a.top), bottom: Math.round(a.bottom), onScreen: a.top >= 0 && a.bottom <= innerHeight,
               header: hit(hd), bar: hit(br), headerBottom: hd && Math.round(hd.bottom), barTop: br && Math.round(br.top), barBottom: br && Math.round(br.bottom) }; }"""
    BEAT_SAYS = """() => { const t = document.querySelector('#musicDoors .dp-tile[data-dp="beat"]'), v = t.querySelector('.dp-v');
      return { tile: v.textContent, fits: v.scrollWidth <= v.clientWidth + 0.5, name: t.getAttribute('aria-label'),
               line: document.getElementById('musicTempo').textContent }; }"""
    HEARD = {"bpm": 120, "phase": 0, "heard": True}
    UNDO = {"Pad": "#toast .toast-action", "Flip": "#flipChip .toast-action"}

    def tenth(x):
        """Beats a minute to the tenth, as the drawer says them (half up)."""
        return f"{math.floor(x * 10 + 0.5) / 10:.1f}"

    def zoom_end(pg, presses=4):
        """Zoomed in around the loop's end as a person does it: the end touched,
        then + (the timeline zooms around the end touched last)."""
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        at = pg.evaluate(TL, "tlEnd")
        pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(200)
        for _ in range(presses):
            press(pg, "#musicTlIn", 260)
        pg.wait_for_timeout(500)
        return pg.evaluate("() => document.getElementById('musicTlMag').textContent")

    def end_to(pg, t, near=None):
        """The end dragged to `t` seconds, in view, and let go: (as let go, once settled)."""
        at = pg.evaluate(TL, "tlEnd")
        pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down()
        pg.mouse.move(at["x"] + (t - at["v0"]) / at["span"] * at["w"], at["hy"], steps=8); pg.wait_for_timeout(100)
        g = pg.evaluate(TRIM)
        if near is not None:
            pg.evaluate(NEAR, {"at": near, "ms": 700})
        pg.mouse.up(); pg.wait_for_timeout(900)
        return g, pg.evaluate(TRIM)

    for _n, _p in eds("end"):
        for still in (False, True):
            ctx = waits.instrument(b.new_context(reduced_motion="reduce", **DESK)) if still else None
            c, pg, errs = editor(b, _n, _p, ctx=ctx)
            pg.evaluate(SET, {"tempo": HEARD, "s": 2.0, "e": 6.0, "xf": 0})
            mag = zoom_end(pg)
            g, t = end_to(pg, 6.04, near=6.02)
            tp, rec, said, beat = pg.evaluate("() => musicTempo"), pg.evaluate("() => window.__recb"), pg.evaluate(NOTE), pg.evaluate(BEAT_SAYS)
            want = round(60 * 8 / heard(g), 3)
            n = heard(t) * tp["bpm"] / 60 if tp else 0
            # Where the beat on the end belongs now: the 8th from the loop's start.
            fin = tp["phase"] + 8 * 60 / tp["bpm"] if tp else None
            seen = [f[1] for f in rec if f[1] is not None]
            between = [v for v in seen if fin is not None and 6.0 + 1.5e-4 < v < fin - 1.5e-4]
            there = next((f[0] for f in rec if f[1] is not None and fin is not None and abs(f[1] - fin) < 1.5e-4), None)
            if not still:
                check(f"{_n}: zoomed in, an end let go within an eighth of a beat of 8 stays exactly where it was let go, "
                      "and the beat becomes the one that makes the loop exactly 8 beats, counted from its start",
                      "16" in mag and abs(t["e"] - g["e"]) < 1e-6 and abs(g["e"] - 6.04) < 0.005 and t["s"] == 2.0 and tp is not None
                      and tp.get("by") == "end" and "heard" not in tp and tp["phase"] == 2.0 and tp["bpm"] == want and abs(n - 8) < 1e-4,
                      f"at {mag}, let go at {g['e']:.4f}: {t['e']:.4f}; the tempo {tp} (want {want}); {n:.5f} beats heard")
                check(f"{_n}: ...a note says so, with Undo; the Beat tile says the beat is by hand, and its door that the loop's end set it",
                      bool(said) and said["shown"] and said["words"] == f"The beat fits your loop now: {tenth(want)} a minute, 8 beats."
                      and said["undo"] == "Undo" and beat["tile"] == f"{tenth(want)} · by hand" and beat["fits"]
                      and beat["name"].startswith(f"Beat, {tenth(want)} beats a minute, by hand")
                      and beat["line"] == f"{tenth(want)} beats a minute, set by the loop’s end · tap to change it",
                      f"{said}; {beat}")
                check(f"{_n}: the beat marks glide to the new beat frame by frame, the one at the end drawing in to it",
                      len(between) >= 4 and all(b2 >= a2 - 1.5e-4 for a2, b2 in zip(seen, seen[1:])) and there is not None and there < 600,
                      f"{len(between)} frames on the way from 6.0 to {fin}; always on {all(b2 >= a2 - 1.5e-4 for a2, b2 in zip(seen, seen[1:]))}; "
                      f"there at {there and round(there)}ms")
                ok = press(pg, UNDO[_n], 300)
                back, t2, beat2 = pg.evaluate("() => musicTempo"), pg.evaluate(TRIM), pg.evaluate(BEAT_SAYS)
                # Flip took the chip's Undo for a tap away from the drawer, and closed it.
                kept_open = pg.evaluate("() => !document.getElementById('musicPanel').hidden"
                                        " && document.getElementById('musicTlStage').getBoundingClientRect().width > 0")
                check(f"{_n}: the note's Undo puts the beat back as it was, heard by Skribl, the end staying where it was let go and the drawer open",
                      ok and back == HEARD and abs(t2["e"] - t["e"]) < 1e-9 and beat2["tile"] == "120 · heard" and kept_open,
                      f"pressed {ok}: {back}; the loop {t2['s']}-{t2['e']:.4f}; the tile {beat2['tile']!r}; the drawer open {kept_open}")
                g3, t3 = end_to(pg, 5.90)
                tp3 = pg.evaluate("() => musicTempo")
                check(f"{_n}: zoomed in, an end let go further than an eighth of a beat from whole bars settles on them at the tempo there is",
                      abs(g3["e"] - 5.90) < 0.005 and abs(t3["e"] - 6.0) < 1e-6 and tp3 == HEARD,
                      f"let go at {g3['e']:.4f}: {t3['e']:.4f}; the tempo {tp3}")
            else:
                check(f"{_n}: under Reduce Motion the end stays and the beat marks are there at once",
                      abs(t["e"] - g["e"]) < 1e-6 and tp is not None and tp.get("by") == "end" and not between and there is not None,
                      f"let go at {g['e']:.4f}: {t['e']:.4f}; {len(between)} frames on the way; there at {there and round(there)}ms")
            check(f"{_n}: no page errors as the end sets the tempo{' under Reduce Motion' if still else ''}", not errs, "; ".join(errs[:2]))
            c.close()

    for _n, _p in eds("end"):
        c, pg, errs = editor(b, _n, _p)
        # A smooth restart folds the loop's end over its start: the loop comes
        # round 0.25s before the handle, and that is where the 8th beat goes.
        pg.evaluate(SET, {"tempo": HEARD, "s": 2.0, "e": 6.25, "xf": 250})
        zoom_end(pg)
        g, t = end_to(pg, 6.29)
        tp = pg.evaluate("() => musicTempo")
        n = heard(t) * tp["bpm"] / 60 if tp else 0
        check(f"{_n}: with a smooth restart the beats are counted to where the loop comes round, a restart's length before the end",
              abs(t["e"] - g["e"]) < 1e-6 and abs(heard(g) - 4.04) < 0.005 and tp is not None and tp.get("by") == "end"
              and tp["bpm"] == round(60 * 8 / heard(g), 3) and abs(n - 8) < 1e-4,
              f"let go at {g['e']:.4f}, heard {heard(g):.4f}: the tempo {tp}; {n:.5f} beats heard")
        pg.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
        pg.wait_for_timeout(2500)
        pg.reload()
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        waits.settle(pg, 600)
        browsing.pad_drawer(pg, "music")
        set_door(pg, "beat")
        back, beat = pg.evaluate("() => musicTempo"), pg.evaluate(BEAT_SAYS)
        check(f"{_n}: the beat the end set is kept with the song in the drafts, and its door still says the loop's end set it",
              tp is not None and back == tp and beat["tile"] == f"{tenth(tp['bpm'])} · by hand" and "set by the loop’s end" in beat["line"],
              f"{tp} -> after a reload {back}; {beat}")
        check(f"{_n}: no page errors with a smooth restart and a reload", not errs, "; ".join(errs[:2]))
        c.close()

    for _n, _p in eds("end"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": HEARD, "s": 2.0, "e": 6.0, "xf": 0})
        pg.wait_for_timeout(300)
        g, t, _ = tl_drag(pg, "tlEnd", 6.04)
        tp, said = pg.evaluate("() => musicTempo"), pg.evaluate(NOTE)
        check(f"{_n}: at 1x an end let go as near whole bars settles on them, the tempo as it was and no note",
              abs(g["e"] - 6.04) < 0.03 and abs(t["e"] - 6.0) < 1e-6 and tp == HEARD
              and not (said and said["shown"] and said["words"].startswith("The beat fits")),
              f"let go at {g['e']:.4f}: {t['e']:.4f}; the tempo {tp}; the note {said}")
        # Zoomed in, a start let go near a beat moves where the beat falls and
        # keeps where the beat came from.
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        at = pg.evaluate(TL, "tlStart")
        pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(200)
        for _ in range(4):
            press(pg, "#musicTlIn", 260)
        pg.wait_for_timeout(500)
        kept = []
        for tp0, says in (({"bpm": 120, "phase": 0.045, "heard": True}, "heard"), ({"bpm": 118.812, "phase": 2.045, "by": "end"}, "by hand")):
            pg.evaluate(SET, {"tempo": tp0, "s": 2.045, "e": 2.045 + 8 * 60 / tp0["bpm"], "xf": 0})
            pg.wait_for_timeout(400)
            at = pg.evaluate(TL, "tlStart")
            pg.mouse.move(at["hx"], at["hy"]); pg.mouse.down()
            pg.mouse.move(at["x"] + (2.0 - at["v0"]) / at["span"] * at["w"], at["hy"], steps=8); pg.wait_for_timeout(100)
            pg.mouse.up(); pg.wait_for_timeout(900)
            got, beat = pg.evaluate("() => musicTempo"), pg.evaluate(BEAT_SAYS)
            kept.append((tp0, got, beat["tile"], says))
        check(f"{_n}: a start let go zoomed in moves where the beat falls and keeps where the beat came from: heard stays heard, by hand stays by hand",
              all(g2 is not None and abs(g2["phase"] - 2.0) < 0.005 and g2["bpm"] == t0["bpm"] and g2.get("heard") == t0.get("heard")
                  and g2.get("by") == t0.get("by") and tile.endswith(says) for t0, g2, tile, says in kept),
              "; ".join(f"{t0} -> {g2}, the tile {tile!r}" for t0, g2, tile, _ in kept))
        # The Snap switch off and on again keeps it too.
        pg.evaluate(SET, {"tempo": {"bpm": 118.812, "phase": 2.0, "by": "end"}}); pg.wait_for_timeout(150)
        pg.click("#musicSnap"); pg.wait_for_timeout(150)
        off = pg.evaluate("() => musicTempo")
        pg.click("#musicSnap"); pg.wait_for_timeout(150)
        on = pg.evaluate("() => musicTempo")
        check(f"{_n}: Snap to the beat turned off and on keeps where the beat came from",
              off == {"bpm": 118.812, "phase": 2.0, "by": "end", "snap": False} and on == {"bpm": 118.812, "phase": 2.0, "by": "end"},
              f"off {off}; on again {on}")
        check(f"{_n}: no page errors at 1x and with the start", not errs, "; ".join(errs[:2]))
        c.close()

    for _n, _p in eds("end"):
        # Tapped again after the end set it, the beat is the taps' own, tapped.
        def by_end(pg):
            pg.evaluate(SET, {"tempo": {"bpm": 118.812, "phase": 2.0, "by": "end"}, "s": 0, "e": 12, "xf": 0})
            press(pg, "#musicTapBtn", 0)                                       # the start
            pg.wait_for_function("() => _waLoop.playing() && _waLoop.elapsed() > 0.3", timeout=5000)
        c, pg, got, k = in_time(b, _n, _p, ON_BEAT, {"off": 0.12, "n": 6}, prep=by_end)
        pg.wait_for_timeout(2300)
        st, beat = pg.evaluate(SAID), pg.evaluate(BEAT_SAYS)
        check(f"{_n}: tapped again after the end set the beat, the beat is the taps', tapped",
              st["kept"] is not None and st["kept"]["bpm"] == 120 and "by" not in st["kept"] and beat["tile"] == "120 · tapped"
              and st["tempo"] == "120 beats a minute · tap again to change it",
              f"{st['kept']}; the tile {beat['tile']!r}; {st['tempo']!r} (taps within {got['spread']:.1f}ms of their marks, try {k})")
        c.close()

    for _n, _p in [e for e in eds("end") if e[0] == "Flip"]:
        # Match the beat on, a round of pages in a bar: the end's beat refits it.
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": HEARD, "s": 2.0, "e": 6.0, "xf": 0})
        pg.evaluate("() => { beatBars = 1; beatRefit(); scheduleSave(); }")
        f0 = pg.evaluate("() => fps")
        zoom_end(pg)
        end_to(pg, 6.04)
        f1, cyc, tp = pg.evaluate("() => [fps, SkriblHold.plan(frames, fps, docLoop).cycle, musicTempo]")
        bar = 4 * 60 / tp["bpm"] * 1000 if tp else 0
        check(f"{_n}: Match the beat follows the beat the end set: a round of pages is still exactly a bar",
              tp is not None and tp.get("by") == "end" and abs(cyc - bar) < 0.5 and abs(f1 - f0) > 0.01,
              f"{f0:.4f} pages a second -> {f1:.4f}; a round {cyc:.1f}ms, a bar {bar:.1f}ms; {tp}")
        check(f"{_n}: no page errors with Match the beat", not errs, "; ".join(errs[:2]))
        c.close()

    for _n, _p in eds("end"):
        # On the owner's phone the drawer is scrolled to, the toolbar right
        # under the header: the note shows clear of both.
        c, pg, errs = editor(b, _n, _p, opts=PHONE)
        pg.evaluate(SET, {"tempo": HEARD, "s": 2.0, "e": 6.0, "xf": 0})
        zoom_end(pg)
        end_to(pg, 6.04)
        said = pg.evaluate(NOTE)
        reach = bool(said) and said["barTop"] is not None and said["headerBottom"] is not None \
            and said["barTop"] < said["headerBottom"] + 8 + (said["bottom"] - said["top"])
        check(f"{_n}: on the owner's phone the note shows clear of the header and the toolbar right under it",
              bool(said) and said["shown"] and said["onScreen"] and reach and not said["header"] and not said["bar"],
              f"{said}; the toolbar within a note's reach of the header: {reach}")
        c.close()

    b.close()

summarise_and_exit()
