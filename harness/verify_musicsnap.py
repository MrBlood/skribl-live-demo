#!/usr/bin/env python3
"""The music drawer's beat on the timeline: where an end lands, its marks,
the Restart view, the beat kept with the song, and the words (out of
verify_musicbeat.py).

WHY THIS IS ITS OWN SUITE. verify_musicbeat.py took 591 of run_harness.sh's
600 seconds on #663's PostgreSQL shard, and on #665's it was stopped at 600
before it reported, every check it had reached passing (610 seconds here,
alone). The sections from its marks on moved here whole, as
verify_musicclick.py and verify_musictempo.py left it before: nothing in them
changed in what it asks. verify_musicbeat.py keeps the pair, Tap the beat,
the nearest beat and Beats.

  SNAP TO THE BEAT (the owner: "I need a free set so it's not all
  automatic"; then, of the switch in the Beat door, "do you think it is
  hidden down in there", and of the mock, "all yes"). The magnet by the zoom
  is there from the first, out of reach and unlit until there is a tempo,
  then lit to start, its tooltip saying what it does, and none in the Beat
  door. Exact times' Each press takes a bar in once there is a tempo,
  gliding wider, frame by frame, at once under Reduce Motion. Off, nothing
  settles: the start and the end let go on the timeline, the song slid, a
  tap on the whole song, an end near a beat in the Restart view.

  WHERE THE MUSIC BEGINS (the owner, of a song with dead air before it: "It
  snaps back to empty space"; of the mock, "All yes"). At 1x a start let go
  in the silence before the music and nearer it than the next beat, or with
  the nearest beat in the silence, or up to half a beat into the music,
  lands where the music begins, the beat kept and the loop whole beats; music
  that begins within an eighth of a beat of one, on that beat. Past half a
  beat into the music, in a gap too short to be a silence, and in the quiet
  between two drums on beats, it lands on the nearest beat, as before.
  Zoomed in, a start let go far from a beat stays, and so does the beat.

  THE MARKS. The timeline puts a dot on every beat that stands 6px from the
  next (else every bar, else every fourth bar), bigger on each bar counted
  from the loop's start; the Restart view marks the beats in its two windows.
  Read from what each canvas records it painted, and the dots on the pixels.

  THE RESTART VIEW (it took over the loop detail's close-up). An end let go
  there near a beat settles on it (the end where the loop comes round); far
  from one it stays. A typed end never settles, nor a locked loop's.

  KEPT. The tempo goes with the song into the drafts and comes back with it,
  from an autosave and from a re-add card, Snap to the beat with it; tapped
  again, the switch stays as it was; a new song starts with none, and the
  switch is put away.

  WORDS. The pair's words are whole on every phone (one to a row under
  360px), and the one line, the doors' words, Beats and the tap's read
  against what is behind them, each with its door open, and the beat's dots
  against the song's lane, on the pixels.

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
    print("No assertions were executed. This is NOT evidence an end lands on the music drawer's beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICSNAP_ONLY=Pad (or Flip) runs one editor, and
# MUSICSNAP_PART=marks (detail, snap, silence, keep, words) one part.
# A real run sets neither.
ONLY = os.environ.get("MUSICSNAP_ONLY", "")
PART = os.environ.get("MUSICSNAP_PART", "")
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


SHORT = {"name": "six.wav", "mimeType": "audio/wav", "buffer": _wav(6.0)}
TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
LONG = {"name": "minute.wav", "mimeType": "audio/wav", "buffer": _wav(60.0)}
# Songs whose music begins after a silence, for where the music begins: each a
# sum of parts, a function of the time each, at 8000 a second.
P90 = 60 / 90


def _song(name, *parts, seconds=12.0, rate=8000):
    n = int(seconds * rate)
    v = [sum(f(i / rate) for f in parts) for i in range(n)]
    k = 0.9 * 32767 / (max(abs(x) for x in v) or 1)
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack("<%dh" % n, *[int(x * k) for x in v]))
    w.close()
    return {"name": name, "mimeType": "audio/wav", "buffer": buf.getvalue()}


def _drum(t, p=P90, first=P90):
    """A drum on every beat from `first`, under a hundredth of the loudest 0.28s on."""
    if t < first:
        return 0.0
    x = (t - first) % p
    return 0.9 * math.exp(-x / 0.06) * math.sin(2 * math.pi * 110 * x)


def _held(t, first=P90):
    """A chord held under the drums from `first`, never quiet."""
    return 0.06 * math.sin(2 * math.pi * 220 * t) if t >= first else 0.0


def _lead(t):
    """A note at 0.40s, between two beats, ringing on into the first drum."""
    return 0.3 * math.exp(-(t - 0.4) / 0.25) * math.sin(2 * math.pi * 440 * (t - 0.4)) if t >= 0.4 else 0.0


# Silence to 0.40s, a lead-in note there, then the drums and the chord from the beat at 0.667s.
LEADIN = _song("lead-in.wav", _lead, _drum, _held)
# The same with no lead-in: the music begins on the beat.
NOLEAD = _song("no-lead.wav", _drum, _held)
# The music from 0:00, stopping on the beat at 2.0 and back on the beat at
# 3.33, with a tenth of a second's gap at 1.05, too short to be a silence.
BREAK = _song("break.wav", lambda t: 0.0 if 2.0 <= t < 5 * P90 or 1.05 <= t < 1.15 else _drum(t, first=0.0) + _held(t, first=0.0))
# A drum every second from 1.0 and nothing between.
SPARSE = _song("sparse.wav", lambda t: _drum(t, p=1.0, first=1.0))
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
  return { line: ink(q('#musicPickText')), length: ink(q('#musicPickText b')), pick: ink(q('#musicPickCard .dp-k')), tempo: ink(q('#musicTempo')),
           tap: ink(q('#musicTapWords')), hear: ink(q('#previewLoopBtn .tp-k')), press: ink(q('#musicStepLbl')),
           magnet: ink(q('#musicSnap')),
           beats: ink(q('#musicBeatsLbl')), count: ink(q('#musicBeatsSeg button:not(.on):not([hidden])')),
           tiles: Math.min(...[...document.querySelectorAll('#musicDoors .dp-tile .dp-v')].filter((v) => v.textContent).map((v) => ink(v))) }; }"""
# Which words are read with which door open, as a person sees them: the
# view's with every door shut, and each door's with it open.
CONTRAST_DOORS = ((None, ("line", "length", "hear", "tiles", "magnet")), ("beat", ("tempo", "tap", "tiles")),
                  ("length", ("pick", "beats", "count")), ("exact", ("press",)))


# The beat's dots, on the pixels: the timeline paints them on a canvas, so a
# style says nothing about them. A beat and a bar each, read at its middle
# (the most contrasting pixel within a pixel of it) against the lane beside
# it, 6px along, where nothing else is painted at that height: 16px under the
# drawing's lane as the timeline painted it (26px on the Pad, 34 on Flip).
def dot_contrast(pg):
    import io as _io
    from PIL import Image as _Img
    # The picture is of the stage where it is WHILE it is taken. The drawer's
    # hold can still put the page back where it glided to, up to 1.2s after it
    # grew (lib/drawerdetent.js), which a person's own scroll stands down but
    # this one does not: read where the stage is before and after the picture,
    # and take it again until the two agree (a picture of the strip below it,
    # dots and all missing, read 1.00 here).
    STAGE = "() => { const r = document.getElementById('musicTlStage').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
    for _ in range(8):
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        st = pg.evaluate(STAGE)
        m = pg.evaluate(MARKS, "musicTimeline")
        png = pg.screenshot(clip={"x": st[0], "y": st[1], "width": st[2], "height": st[3]})
        if pg.evaluate(STAGE) == st:
            break
    im = _Img.open(_io.BytesIO(png)).convert("RGB")
    k = im.width / st[2]

    def lum(c):
        f = [(v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]

    def ratio(a, b):
        x, y = lum(a), lum(b)
        return (max(x, y) + 0.05) / (min(x, y) + 0.05)
    # Not under a handle: the loop's ends are bars, and the handle's line
    # stands over the dot there.
    hx = pg.evaluate("() => ['tlStart', 'tlEnd'].map(id => { const r = document.getElementById(id).getBoundingClientRect(), s = document.getElementById('musicTlStage').getBoundingClientRect(); return r.left + r.width / 2 - s.left; })")
    out, y = {}, (m["lane"] if m else 26) + 16
    for name, want in (("beat", False), ("bar", True)):
        for x, bar, _t in (m["beats"] if m else []):
            if bar != want or x < 12 or x > st[2] - 12 or any(abs(x - h) < 14 for h in hx):
                continue
            gx = x + 6 if x + 6 < st[2] - 4 else x - 6
            ground = im.getpixel((int(gx * k), int(y * k)))
            out[name] = max(ratio(im.getpixel((int((x + dx) * k), int((y + dy) * k))), ground) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            break
    return out


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

    print("\nMUSIC BEAT — the beat, marked")
    # A long drawing on the Pad, as its own strokes would make one: a point
    # every 50ms for `secs` seconds, a stroke every second.
    LONGDRAW = """(secs) => { strokes.length = 0;
      for (let i = 0; i <= secs * 20; i++) strokes.push({ x: 40 + (i % 20) * 9, y: 60 + Math.floor(i / 20) % 8 * 20, color: '#7c5cff', size: 6, t: i * 50, start: i % 20 === 0 });
      updateDrawingTimeLabels(); }"""
    for _n, _p in eds("marks"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 1.0, "e": 5.25, "xf": 250})
        pg.wait_for_timeout(600)                         # the view has eased to its framing
        m = pg.evaluate(MARKS, "musicTimeline")
        v0, span = m["view"] if m else (0, 1)
        want = [k * 0.5 for k in range(0, 40) if max(0, v0) - 1e-6 <= k * 0.5 <= v0 + span + 1e-6]
        got = [x[2] for x in m["beats"]] if m else []
        xs = all(abs(x[0] - (x[2] - v0) / span * m["w"]) < 0.6 for x in m["beats"]) if m else False
        bars = [x[2] for x in (m["beats"] if m else []) if x[1]]
        check(f"{_n}: the timeline puts a dot on every beat in view, bigger on each bar counted from the loop's start",
              m is not None and got == want and len(got) >= 8 and xs and bars == [t for t in want if round((t - 1.0) / 0.5) % 4 == 0],
              f"{len(got)} dots at {got[:4]}...{got[-2:]} in view {v0:.2f}-{v0 + span:.2f}s, bars at {bars}")
        c.close()
    for _n, _p in eds("marks"):
        # On a phone, a long drawing and a 20s loop: beats 2px apart, so only
        # the bars show; a drawing lane and the dashed comes-round lines too.
        c, pg, errs = editor(b, _n, _p, song=LONG, opts=PHONE)
        if _n == "Pad":
            pg.evaluate(LONGDRAW, 60)
        else:
            # 45 pages held 8 (the most a page holds) at 6 a second: a minute.
            pg.evaluate(PAGES, {"n": 45, "fps": 6, "hold": 8})
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 20, "xf": 0})
        pg.wait_for_timeout(700)
        m = pg.evaluate(MARKS, "musicTimeline")
        v0, span = m["view"] if m else (0, 1)
        px = [m["beats"][i + 1][0] - m["beats"][i][0] for i in range(len(m["beats"]) - 1)] if m else []
        k = [round(x[2] / 0.5) for x in (m["beats"] if m else [])]
        check(f"{_n}: a timeline that shows a minute marks only as many beats as stand 6px apart: every bar, or every fourth",
              m is not None and px and min(px) >= 6 and all(x % 4 == 0 for x in k) and len(k) >= 6,
              f"{len(k)} dots on a {m and m['w']}px timeline showing {span:.1f}s, the closest {min(px) if px else 0:.1f}px apart, at beats {k[:6]}...")
        lines = m["lines"] if m else []
        check(f"{_n}: the drawing's own lane runs under the loop, with a dashed line each time the loop comes round under it",
              m is not None and len(m["marks"]) >= 3 and len(lines) >= 1
              and all(abs(x - (20 * (i + 1) - v0) / span * m["w"]) < 0.6 for i, x in enumerate(lines)),
              f"{len(m['marks']) if m else 0} marks on the lane; lines at {lines}, every 20s")
        c.close()
    for _n, _p in eds("marks"):
        c, pg, errs = editor(b, _n, _p, door="restart")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.1}, "s": 1.0, "e": 3.0, "xf": 0})
        pg.wait_for_timeout(300)
        m = pg.evaluate(MARKS, "musicRestart")
        half = m["w"] / 2 if m else 1
        want = []
        if m:
            for side, (a0, a1) in (("end", m["end"]), ("start", m["start"])):
                for kb in range(0, 40):
                    t = 0.1 + kb * 0.5
                    if a0 - 1e-9 <= t <= a1 + 1e-9:
                        x = (t - a0) / 0.6 * half + (half if side == "start" else 0)
                        if 2 <= x <= m["w"] - 2 and abs(x - half) >= 1.5:
                            want.append((side, round(x, 1)))
        got = [(x[0], round(x[1], 1)) for x in m["beats"]] if m else []
        check(f"{_n}: the Restart view marks the beats in its two windows, the end's and the start's",
              m is not None and got == want and len(got) >= 2 and abs(m["end"][1] - 3.0) < 0.006 and abs(m["start"][0] - 1.0) < 0.006,
              f"windows {m and m['end']} and {m and m['start']}: marks {got}, want {want}")
        c.close()

    print("\nMUSIC BEAT — the Restart view")
    # A drag on the Restart view's end side, as a finger drags it, so the end
    # lands at `t`: the music follows the finger, so a drag to the right
    # makes the end earlier. The distance to the beat is read at the view's
    # own scale (0.6s a side), then let go.
    RV = "() => { const r = document.getElementById('musicRestart').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }"

    def rv_drag(pg, t):
        door_for(pg, "#musicRestart")
        pg.evaluate("() => document.getElementById('musicRestart').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(250)
        r, g0 = pg.evaluate(RV), pg.evaluate(TRIM)
        half = r["w"] / 2
        x0, y = r["x"] + half * 0.5, r["y"] + r["h"] * 0.5
        dx = (g0["e"] - t) / 0.6 * half
        pg.mouse.move(x0, y); pg.mouse.down()
        pg.mouse.move(x0 + dx / 2, y, steps=3); pg.mouse.move(x0 + dx, y, steps=3)
        g, ph = pg.evaluate(TRIM), pg.evaluate("() => (musicTempo && musicTempo.phase) || 0")
        fold = min(g["xf"] / 1000, (g["e"] - g["s"]) / 2)
        beat = ph + round((g["e"] - fold - ph) / 0.5) * 0.5
        px = abs(g["e"] - fold - beat) / 0.6 * half
        pg.mouse.up(); pg.wait_for_timeout(450)
        return px, pg.evaluate(TRIM), g

    for _n, _p in eds("detail"):
        c, pg, errs = editor(b, _n, _p, song=SHORT, door="restart")
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 4.35, "xf": 250})
        pg.wait_for_timeout(300)
        n_px, near, _ = rv_drag(pg, 4.25 + 0.01)                        # just past where the 8th beat comes round
        f_px, far, _ = rv_drag(pg, 4.5)                                 # half a beat on
        check(f"{_n}: in the Restart view an end let go near a beat settles on it; far from one, it stays",
              n_px <= 8 and abs((near["e"] - 0.25) - 4.0) < 1e-6 and f_px > 8 and abs(far["e"] - 4.5) < 0.05,
              f"let go {n_px:.1f}px from a beat: end {near['e']:.4f} (comes round at {near['e'] - 0.25:.4f}); {f_px:.1f}px from one: {far['e']:.4f}")
        door_for(pg, "#endReadout")
        pg.fill("#endReadout", "3.27"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        typed = pg.evaluate(TRIM)
        press(pg, "#musicLock", 100)
        g, locked, _ = tl_drag(pg, "tlEnd", 4.0)
        press(pg, "#musicLock", 100)
        check(f"{_n}: a typed end never settles, nor a locked loop's",
              abs(typed["e"] - 3.27) < 1e-6 and abs((locked["e"] - locked["s"]) - (typed["e"] - typed["s"])) < 1e-6 and locked == g,
              f"typed 3.27: {typed['e']}; locked, dragged: {g} then {locked}")
        c.close()

    print("\nMUSIC BEAT — Snap to the beat, the magnet by the zoom")
    # The magnet (the owner, of the switch in the Beat door: "do you think it
    # is hidden down in there"; of the mock, "all yes"): its words are its
    # tooltip, the title lib/tooltip.js keeps as data-tip. Lit is what is
    # painted: the chosen choice's purple, read against a probe beside it
    # wearing that fill.
    SNAP = """() => { const s = document.getElementById('musicSnap'), box = s && s.closest('.mt-tl-head .mt-tl-snapbox');
      let lit = false;
      if (s) { const p = document.createElement('i'); p.style.background = 'var(--seg-on-fill)'; s.parentNode.appendChild(p);
               lit = getComputedStyle(s).backgroundColor === getComputedStyle(p).backgroundColor; p.remove(); }
      return { shown: !!box && box.getClientRects().length > 0, usable: !!s && !s.disabled, on: s && s.getAttribute('aria-pressed'), lit,
               says: s && (s.getAttribute('data-tip') || s.title), kept: musicTempo,
               inDoor: !!document.querySelector('#musicDoors #musicSnap, #musicSnapRow') }; }"""
    for _n, _p in eds("snap"):
        c, pg, errs = editor(b, _n, _p)
        s0 = pg.evaluate(SNAP)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}})
        pg.wait_for_timeout(400)
        s1 = pg.evaluate(SNAP)
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(250)
        press(pg, "#musicSnap")
        s2 = pg.evaluate(SNAP)
        press(pg, "#musicSnap")
        s3 = pg.evaluate(SNAP)
        check(f"{_n}: the magnet by the zoom is there from the first, out of reach and unlit until there is a tempo, then lit to start, saying what it does; off, that the ends stay where they are let go",
              s0["shown"] and not s0["usable"] and s0["on"] == "false" and not s0["lit"] and s0["says"] == "Snap to the beat, once there is a beat"
              and s1["shown"] and s1["usable"] and s1["on"] == "true" and s1["lit"] and s1["says"] == "Snap to the beat: on. A dragged end lands on the nearest beat."
              and s2["on"] == "false" and not s2["lit"] and s2["says"] == "Snap to the beat: off. Ends stay where you let them go." and s2["kept"] == {"bpm": 120, "phase": 0, "snap": False}
              and s3["on"] == "true" and s3["lit"] and s3["kept"] == {"bpm": 120, "phase": 0} and not s0["inDoor"],
              f"no tempo: {s0}; a tempo: {s1}; pressed: {s2}; again: {s3['on']}, {s3['kept']}")
        c.close()
    print("\nON IS OUTLINED — the magnet, Taller and the click: ringed when on, plain when off")
    # The owner, of the mock: "rather than solid purple on snap and taller
    # click and repeat I like the outline, but not so thick". On and off
    # differed by a deeper tint alone, 1.22:1 between them on the light card
    # and 1.19:1 on the dark. Read off the pixels at 2x: each button's top
    # edge on against the same edge off, which the 1px ring makes at least
    # 3:1, and the glyph at least 3:1 on its tint while on; light and dark.
    from PIL import Image as _RImg
    _RLUM = lambda c: sum(w * ((v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4)
                          for w, v in zip((0.2126, 0.7152, 0.0722), c[:3]))
    _rr = lambda a, b: (max(_RLUM(a), _RLUM(b)) + 0.05) / (min(_RLUM(a), _RLUM(b)) + 0.05)
    _RGEO = """(id) => { const e = document.getElementById(id), r = e.getBoundingClientRect(), s = e.querySelector('svg').getBoundingClientRect();
      return { b: [r.left, r.top, r.width, r.height], g: [s.left, s.top, s.width, s.height] }; }"""
    _RIDS = ("musicSnap", "musicTlTall", "musicClickBtn")

    def _redge(img, b):
        x, y, w, h = b
        return img.getpixel((int((x + w / 2) * 2), int(y * 2) + 1))

    def _rglyph(img, b, g):
        x, y, w, h = b
        tint = img.getpixel((int((x + 4) * 2), int((y + h / 2) * 2)))
        gx, gy, gw, gh = g
        return max(_rr(img.getpixel((i, j)), tint) for i in range(int(gx * 2), int((gx + gw) * 2)) for j in range(int(gy * 2), int((gy + gh) * 2)))

    for _n, _p in eds("ring"):
        _res = {}
        for _th in ("light", "dark"):
            c, pg, errs = editor(b, _n, _p + "?theme=" + _th, opts=dict(DESK, device_scale_factor=2))
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}}); pg.wait_for_timeout(400)      # a tempo: the magnet on
            pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
            g1 = {i: pg.evaluate(_RGEO, i) for i in _RIDS}
            a1 = _RImg.open(io.BytesIO(pg.screenshot())).convert("RGB")                       # the magnet on; Taller and the click off
            for i in _RIDS:
                press(pg, "#" + i)
            pg.wait_for_timeout(300)
            g2 = {i: pg.evaluate(_RGEO, i) for i in _RIDS}                                      # Taller moves what is under it
            a2 = _RImg.open(io.BytesIO(pg.screenshot())).convert("RGB")                       # the magnet off; Taller and the click on
            _on = {"musicSnap": (a1, g1), "musicTlTall": (a2, g2), "musicClickBtn": (a2, g2)}
            _off = {"musicSnap": (a2, g2), "musicTlTall": (a1, g1), "musicClickBtn": (a1, g1)}
            _res[_th] = {i: (round(_rr(_redge(_on[i][0], _on[i][1][i]["b"]), _redge(_off[i][0], _off[i][1][i]["b"])), 2),
                             round(_rglyph(_on[i][0], _on[i][1][i]["b"], _on[i][1][i]["g"]), 2)) for i in _RIDS}
            _res[_th + " pressed"] = pg.evaluate("(ids) => ids.map(i => document.getElementById(i).getAttribute('aria-pressed'))", list(_RIDS))
            c.close()
        check(f"{_n}: ON IS OUTLINED: the magnet, Taller and the click, on, are ringed (the edge at least 3:1 against the same edge off), the glyph at least 3:1 on the tint; light and dark",
              all(_res[t + " pressed"] == ["false", "true", "true"] and all(e >= 3.0 and gl >= 3.0 for e, gl in _res[t].values()) for t in ("light", "dark")),
              str(_res))
    for _n, _p in eds("snap"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0.1}, "s": 0.5, "e": 4.75, "xf": 250})
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(250)
        press(pg, "#musicSnap")
        # Each let go between two beats (at 0.1 + k/2), where a snap would move it.
        g1, t1, _ = tl_drag(pg, "tlStart", 1.33)
        g2, t2, _ = tl_drag(pg, "tlEnd", 6.07)
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        r = pg.evaluate(TL, "tlEnd")
        x0, y0 = r["x"] + r["w"] * 0.45, r["hy"] + 20
        dx = -0.37 / r["span"] * r["w"]
        pg.mouse.move(x0, y0); pg.mouse.down()
        pg.mouse.move(x0 + dx / 2, y0, steps=4); pg.mouse.move(x0 + dx, y0, steps=4)
        g3 = pg.evaluate(TRIM)
        pg.mouse.up(); pg.wait_for_timeout(500)
        t3 = pg.evaluate(TRIM)
        # A tap on the whole song's line, so the loop's start comes to 2.85,
        # halfway between the beats at 2.6 and 3.1.
        wh = pg.evaluate("() => { const r = document.getElementById('musicTlWhole').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }")
        ln = t3["e"] - t3["s"]
        pg.mouse.click(wh["x"] + wh["w"] * (2.85 + ln / 2) / t3["d"], wh["y"] + wh["h"] / 2); pg.wait_for_timeout(900)
        t4 = pg.evaluate(TRIM)
        # In the Restart view, an end let go 0.01s past where a beat comes round.
        pg.evaluate(LOOP, {"s": 0.1, "e": 4.35})
        pg.wait_for_timeout(300)
        n_px, t5, g5 = rv_drag(pg, 4.35 + 0.01)
        check(f"{_n}: Snap to the beat off, nothing settles: the start and the end let go on the timeline, the song slid, a tap on the whole song, an end near a beat in the Restart view",
              pg.get_attribute("#musicSnap", "aria-pressed") == "false"
              and t1 == g1 and abs(g1["s"] - 1.33) < 0.06 and t2 == g2 and abs(g2["e"] - 6.07) < 0.06
              and t3 == g3 and abs((g3["s"] - g1["s"]) - 0.37) < 0.03
              and abs(t4["s"] - 2.85) < 0.03 and abs((t4["e"] - t4["s"]) - ln) < 1e-6
              and n_px <= 8 and t5 == g5,
              f"start let go {g1['s']:.3f}, after {t1['s']:.3f}; end {g2['e']:.3f}, {t2['e']:.3f}; slid {g3['s']:.3f}, {t3['s']:.3f}; "
              f"the whole song tapped for 2.85: {t4['s']:.3f}; Restart view, {n_px:.1f}px from a beat: {g5['e']:.4f}, {t5['e']:.4f}")
        check(f"{_n}: no page errors with Snap to the beat", not errs, "; ".join(errs[:2]))
        c.close()
    # What shows once there is a beat opens out, read on every frame from just
    # before the tempo lands, each door with it open: the Beat door's end
    # glides down as Beats in a bar opens under the tap, and in Exact times
    # Each press widens to take a bar in, neither in one frame; at once under
    # Reduce Motion.
    OPENS = """(door) => new Promise((res) => { const out = [], t0 = performance.now(),
        panel = document.getElementById('musicDoorBeat'), seg = document.getElementById('musicStepSeg');
      const read = () => out.push([performance.now() - t0, door === 'beat' ? panel.getBoundingClientRect().bottom + scrollY : seg.getBoundingClientRect().width]);
      read(); musicTempo = { bpm: 120, phase: 0 }; updateTrimUI();
      (function f() { read(); if (performance.now() - t0 < 700) requestAnimationFrame(f); else res(out); })(); })"""

    def opened(rec):
        """A move: how far in all, the frames on the way, and the largest one
        frame's share of it."""
        v = [f[1] for f in rec]
        total = v[-1] - v[0]
        way = [x for x in v if abs(x - v[0]) > 0.5 and abs(x - v[-1]) > 0.5]
        big = max((abs(b2 - a2) for a2, b2 in zip(v, v[1:])), default=0)
        return (round(total, 1), len(way), round(big / total, 2) if total else 1)
    for _n, _p in eds("snap"):
        for still in (False, True):
            o = {}
            for name, door in (("door", "beat"), ("pill", "exact")):
                ctx = waits.instrument(b.new_context(reduced_motion="reduce", **DESK)) if still else None
                c, pg, errs = editor(b, _n, _p, ctx=ctx, door=door)
                pg.evaluate("(id) => document.getElementById(id).scrollIntoView({ block: 'center' })", "musicDoorBeat" if door == "beat" else "musicDoorExact")
                pg.wait_for_timeout(300)
                o[name] = opened(pg.evaluate(OPENS, door))
                c.close()
            if not still:
                check(f"{_n}: Beats in a bar and a bar in Each press open out as the tempo lands: the Beat door's end glides down, and Each press wider, frame by frame",
                      o["door"][0] > 30 and o["door"][1] >= 4 and o["door"][2] <= 0.6 and o["pill"][0] > 20 and o["pill"][1] >= 4 and o["pill"][2] <= 0.6,
                      f"(px in all, frames on the way, the largest frame's share): {o}")
            else:
                check(f"{_n}: under Reduce Motion they are there at once",
                      o["door"][0] > 30 and o["door"][1] == 0 and o["pill"][0] > 20 and o["pill"][1] == 0, f"{o}")

    print("\nMUSIC BEAT — where the music begins")
    # At 1x, each start let go once from a loop of four beats, with the beat
    # set as the ears or the taps would set it: on the lead-in song a beat
    # falls at 0:00, in the silence, and the music begins at FIRST, between
    # beats (lib/musicdrawer.js soundAt).
    T90 = {"bpm": 90, "phase": 0}
    FIRST = 0.4

    def let_go_at(pg, at, s=P90, e=5 * P90, tempo=T90):
        """Where a start let go at `at` lands, the loop s to e before: (let go, after, the beat after)."""
        pg.evaluate(SET, {"tempo": tempo, "s": s, "e": e, "xf": 0})
        pg.wait_for_timeout(350)
        g, t, _ = tl_drag(pg, "tlStart", at)
        return g, t, pg.evaluate("() => musicTempo")

    def bars_of(t, p=P90):
        n = heard(t) / p
        return abs(n - round(n)) < 1e-6 and n >= 1

    def said(g, t, k, p=P90):
        return f"let go at {g['s']:.3f}: {t['s']:.4f}-{t['e']:.4f}, {heard(t) / p:.3f} beats heard; the beat {k}"
    for _n, _p in eds("silence"):
        c, pg, errs = editor(b, _n, _p, song=LEADIN, door=None)
        g, t, k = let_go_at(pg, 0.30)
        check(f"{_n}: a start let go in the silence before the music lands where the music begins, the beat kept and the loop whole beats",
              abs(g["s"] - 0.30) < 0.06 and abs(t["s"] - FIRST) < 0.001 and k == T90 and bars_of(t), said(g, t, k) + f" (the music begins at {FIRST})")
        g, t, k = let_go_at(pg, 0.38)
        check(f"{_n}: ...let go in the silence nearer the music than the next beat (a drum), where the music begins",
              abs(g["s"] - 0.38) < 0.015 and abs(t["s"] - FIRST) < 0.001 and k == T90 and bars_of(t), said(g, t, k))
        g, t, k = let_go_at(pg, 0.55)
        check(f"{_n}: ...let go up to half a beat into the music, where the music begins",
              abs(g["s"] - 0.55) < 0.03 and abs(t["s"] - FIRST) < 0.001 and k == T90 and bars_of(t), said(g, t, k))
        g, t, k = let_go_at(pg, 0.80)
        check(f"{_n}: past half a beat into the music, the nearest beat, as before",
              abs(g["s"] - 0.80) < 0.03 and abs(t["s"] - P90) < 1e-6 and k == T90 and bars_of(t), said(g, t, k))
        # Zoomed in to 4x, where the music begins: a third of a beat from the
        # first drum, far from any beat.
        pg.evaluate(SET, {"tempo": T90, "s": P90, "e": 5 * P90, "xf": 0})
        pg.wait_for_timeout(350)
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        for _ in range(2):
            press(pg, "#musicTlIn", 260)
        pg.wait_for_timeout(500)
        mag = pg.evaluate("() => document.getElementById('musicTlMag').textContent")
        g, t, _ = tl_drag(pg, "tlStart", FIRST)
        k = pg.evaluate("() => musicTempo")
        check(f"{_n}: zoomed in, a start let go where the music begins, far from a beat, stays there, and the beat stays on the drums",
              "4" in mag and abs(t["s"] - g["s"]) < 1e-6 and abs(g["s"] - FIRST) < 0.01 and k == T90 and bars_of(t), f"at {mag}: " + said(g, t, k))
        for _ in range(2):
            press(pg, "#musicTlOut", 260)
        pg.wait_for_timeout(500)
        # The music beginning on a beat.
        add(pg, NOLEAD)
        g, t, k = let_go_at(pg, 0.30)
        check(f"{_n}: where the music begins within an eighth of a beat of one, the start lands exactly on that beat",
              abs(g["s"] - 0.30) < 0.06 and abs(t["s"] - P90) < 1e-6 and k == T90 and bars_of(t), said(g, t, k) + f" (the music begins on the beat at {P90:.4f})")
        # A break in the music: gone on the beat at 2.0, back on the beat at 3.33.
        add(pg, BREAK)
        g, t, k = let_go_at(pg, 1.90, s=2 * P90, e=10 * P90)
        check(f"{_n}: just before a break in the music, with the nearest beat in it, where the music comes back",
              abs(g["s"] - 1.90) < 0.03 and abs(t["s"] - 5 * P90) < 1e-6 and k == T90 and bars_of(t), said(g, t, k) + f" (back at {5 * P90:.4f})")
        g, t, k = let_go_at(pg, 1.10)
        check(f"{_n}: in a gap a tenth of a second long, too short to be a silence, the nearest beat, as before",
              abs(g["s"] - 1.10) < 0.015 and abs(t["s"] - 2 * P90) < 1e-6 and k == T90 and bars_of(t), said(g, t, k))
        # Drums on every beat at 60 and nothing between.
        add(pg, SPARSE)
        T60 = {"bpm": 60, "phase": 0}
        g, t, k = let_go_at(pg, 3.40, s=2.0, e=6.0, tempo=T60)
        check(f"{_n}: in the quiet between two drums on beats, the nearer beat, as before",
              abs(g["s"] - 3.40) < 0.03 and abs(t["s"] - 3.0) < 1e-6 and k == T60 and bars_of(t, 1.0), said(g, t, k, 1.0))
        check(f"{_n}: no page errors where the music begins", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC BEAT — kept with the song")
    for _n, _p in eds("keep"):
        c, pg, errs = editor(b, _n, _p)
        pg.evaluate(SET, {"tempo": {"bpm": 96, "phase": 0.21, "snap": False}})
        pg.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
        pg.wait_for_timeout(2500)
        pg.reload()
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        waits.settle(pg, 600)
        back = pg.evaluate("() => musicTempo")
        c.close()
        c, pg, errs = editor(b, _n, _p, song=None, door=None)
        browsing.pad_drawer(pg, "music")
        pg.evaluate("() => { pendingMusicMeta = { trimStart: 1, trimEnd: 3, crossfadeMs: 0, enabled: true, tempo: { bpm: 84, phase: 0.3 } }; }")
        add(pg, TWELVE)
        card = pg.evaluate("() => musicTempo")
        check(f"{_n}: the tempo is saved with the song in the drafts, and comes back with it, Snap to the beat with it",
              back == {"bpm": 96, "phase": 0.21, "snap": False} and card == {"bpm": 84, "phase": 0.3},
              f"after a reload: {back}; re-added from its card: {card}")
        add(pg, SHORT)
        st = pg.evaluate(SAID)
        m = pg.evaluate(MARKS, "musicTimeline")
        put = pg.evaluate("() => { const s = document.getElementById('musicSnap'); return s.disabled && s.getAttribute('aria-pressed') === 'false'; }")
        check(f"{_n}: a new song starts with no tempo, and no marks, and the magnet unlit and out of reach",
              st["kept"] is None and m is not None and not m["beats"] and "beats" not in st["line"] and put,
              f"{st['kept']}; {st['line']!r}; the magnet unlit and out of reach {put}")
        c.close()

    print("\nMUSIC BEAT — words")
    # The pair's words, whole, from the smallest phone to the owner's: side by
    # side from 360px, one to a row below it.
    # Each of the pair as laid out (Play, and Hear's pill with the click at
    # its end): where it sits, and whether its button's words overflow.
    FIT = """() => [...document.querySelectorAll('.mt-transport > *')].map(x => { const r = x.getBoundingClientRect(), b = x.matches('.mt-play') ? x : x.querySelector('.mt-play');
      return { over: b.scrollWidth - b.clientWidth, top: Math.round(r.top), w: Math.round(r.width) }; })"""
    for _n, _p in eds("words"):
        seen = {}
        for w in (320, 360, 402):
            c, pg, errs = editor(b, _n, _p, opts=dict(PHONE, viewport={"width": w, "height": 874}), door=None)
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
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}, "s": 0, "e": 4.25, "xf": 250})
            pg.wait_for_timeout(600)
            r = {}
            for door, keys in CONTRAST_DOORS:
                set_door(pg, door)
                got = pg.evaluate(CONTRAST)
                r.update({k: min(got[k], r.get(k, 99)) for k in keys})
            set_door(pg, None)
            dots = dot_contrast(pg)
            check(f"{_n}: the one line, the doors' words, Beats and the tap's read against what is behind them, each with its door open, and the beat's dots against the song's lane ({theme})",
                  min(r.values()) >= 4.5 and dots.get("beat", 0) >= 3 and dots.get("bar", 0) >= 3,
                  ", ".join(f"{k} {v:.2f}" for k, v in list(r.items()) + [("dot " + k, v) for k, v in dots.items()]))
            c.close()

    b.close()

summarise_and_exit()
