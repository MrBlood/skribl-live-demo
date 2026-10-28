#!/usr/bin/env python3
"""Match the beat: Flip's Beat speed (the mock, with today's speed and a
matched one playing side by side to a song, and the owner: "all yes").

With a song that has a beat, heard by Skribl or tapped, Speed in Tune is
6 · 12 · 24 · Beat. Beat makes a round of the pages last a quarter, a half,
one or two bars of the song, the one nearest the speed there was to start,
and says what that makes ("12 pages in ½ bar · 12.4 a second"). A round is
what plays before it starts again; a stretch that loops forever is its own
round, the pages before it playing once. Still pages share the round by
their holds; a page that draws itself keeps its own time. Every row is held
to the song's own beat as Skribl heard it (musicTempo), never to a number
the editor wrote down for itself.

  SHOWS WITH A BEAT. With no song, or a song with no beat (a steady tone),
  Speed is as it was; with a beat heard, or tapped with Skribl not
  listening, Beat is there beside 24.

  THE ROUND. Turned on, the round nearest the speed there was: 12 pages at
  12 a second, at 124, is half a bar (12.4 a second), to half a millisecond;
  Beat is lit and the numbers not, the hint says "on the song's beat", and
  the line under the round says what it makes. The round's choices open
  under Speed as a glide, read on every animation frame, and at once under
  Reduce Motion. A quarter, one and two bars each make a round of exactly
  that; a round these pages cannot make (48 of them in a quarter bar, over
  60 a second) is not offered. A page held twice counts twice; a page that
  draws itself keeps its own time; a page added keeps the round, at a new
  speed; a stretch looping forever is the round. 6, 12 or 24 turns Beat off
  at that speed; the song taken away puts Beat aside and the speed stays.

  KEPT. After a reload Beat is the speed, the same round and speed; the post
  carries both (the server's half: verify_sharedrules).

  ON THE BEAT. Playing, every round starts on the song's beat as heard, for
  sixteen seconds: each within 45ms (about where a person starts to notice
  the sound coming before the picture) and the middle one within 20ms; on
  their own timer the same pages slid 179ms off in that time. Play from a later page
  starts the song as far into its round: that page is up as long as page 1
  is from Play (a song started from its top held it half a second, waiting
  for the song to come round), and the first round lands on the beat too. A
  pause and a resume keep them together.

  POSTED. A Beat Flip posted, its pages each a colour of their own, read off
  the middle of the canvas on every frame against the song as heard: on the
  link page and in a post's box in the feed, every round within 60ms of its
  beat and none sliding, the last four where the first four were; a pause in
  the box carries the song on from where it was. The box slid 190ms in
  sixteen seconds, each pass starting again from zero on the frame that
  noticed, and started its song from its top after a pause, 340ms off. A
  song that stalls for 0.3s three seconds in (its clock held, as a busy
  phone holds it) keeps the pages with it, on the link page and in the box:
  every round after it within 60ms. Counting the wall's time, they came
  0.34s early on the link page and 0.31s in the box, for good. The players'
  clock is the song's, as heard (lib/holdtiming.js songClock): a song begun
  where the drawing was 1000ms, half a second on, less the speaker's 40ms,
  at twice the speed, is 1920ms; held, the drawing waits and never steps
  back; a song whose context has not run yet is not the clock, and once it
  runs the drawing waits for it to catch up; ended, the wall's time again.

  HELD BY THE BOX. A round late while the box held the page (50ms or more
  between two looks, ended after the page fell due: a frame held, or a
  frame's or a timer's work) says how long the box held it, not where the
  drawing was. Each row sets one such round aside, the furthest off, and
  names it (judged, said); a drawing late on every round is still late. On
  main after #652 one round came 106ms late, and in the next run one came
  73ms late, each between rounds on the beat.

On Flip only (the Pad has no pages), on a phone. FLIPBEAT_PART=show (round,
kept, beat, posted) runs one part, for calibration. Each row was shown red by its
own break, served in place of the real file; the Reduce Motion row only with
flip.css's rule and styles.css's two global ones all gone, since each alone
keeps the row still.
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

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence that Flip's pages keep to the beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

PART = os.environ.get("FLIPBEAT_PART", "")
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)


def part(name):
    return not PART or PART == name


def _wav(seconds, bpm=None, rate=22050):
    """A click on every beat at `bpm`, the first of each bar louder (a beat
    Skribl hears); with no bpm, a steady tone (no beat at all)."""
    n = int(seconds * rate)
    out = []
    for i in range(n):
        t = i / rate
        if bpm:
            p = 60.0 / bpm
            k = int(t / p)
            x = t - k * p
            a = (0.9 if k % 4 == 0 else 0.55) * math.exp(-x * 60)
            v = a * (math.sin(2 * math.pi * 1000 * x) + 0.6 * math.sin(2 * math.pi * 90 * x)) if x < 0.08 else 0.0
        else:
            v = 0.3 * math.sin(2 * math.pi * 220 * t)
        out.append(int(max(-1.0, min(1.0, v * 0.7)) * 32767))
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack("<%dh" % len(out), *out))
    w.close()
    return buf.getvalue()


BEAT = {"name": "clicks.wav", "mimeType": "audio/wav", "buffer": _wav(32.0, 124)}
TONE = {"name": "tone.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}

# Pages quickly, as the beat suite makes them: a short stroke on each, `n` of them.
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.05 * (k % 16)) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); frames.push(f); }
  fps = o.fps || 12; idx = 0; buildStrip(); render(); updateToolState(); scheduleSave(); }"""
LISTENED = """() => { const E = window.SkriblEars; if (!E || E.__wrapped) return; const real = E.listen; E.__wrapped = true;
  E.listen = (b, d) => real(b, (H) => { d(H); window.__earsDone = true; }); }"""
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
# Speed as it stands, and what the round makes by the timing lib's own plan.
ST = """() => { const q = (id) => document.getElementById(id), H = window.SkriblHold, p = H.plan(frames, fps, docLoop);
  return { fps, bars: beatBars, bpm: musicTempo ? musicTempo.bpm : 0, shown: !q('fpsBeat').hidden, lit: [...document.querySelectorAll('#fps button')]
      .filter((b) => b.classList.contains('on') && !b.hidden).map((b) => b.textContent),
    open: q('beatMore').classList.contains('open'), inert: q('beatMore').hasAttribute('inert'),
    hint: document.querySelector('#tuneFpsRow .tune-hint').textContent, say: q('beatSay').textContent,
    rounds: [...document.querySelectorAll('#beatRoundSeg button')].filter((b) => !b.hidden).map((b) => +b.dataset.bars),
    round: p.forever ? p.stretchMs : p.cycle, pages: frames.length }; }"""
# While it plays: each time a new page is up, which page, where the song is as
# heard, and the longest the box held the page in the 300ms before (held: the
# longest gap between two looks; heldAt: how long before this look it ended;
# see judged()).
HELD_JS = """const recent = []; let prev = null;
  const look = (now) => { const gap = prev == null ? 0 : now - prev; prev = now; recent.push([now, gap]);
    while (recent[0][0] < now - 300) recent.shift(); };
  const heldBy = (now) => { let held = 0, heldAt = 0; for (const [t, g] of recent) if (g > held) { held = g; heldAt = now - t; }
    return { held, heldAt }; };"""
REC = """(secs) => new Promise((done) => { const out = [], t0 = performance.now(); let last = -1; """ + HELD_JS + """
  (function tick() { const now = performance.now(); look(now);
    if (playing && !playPaused && idx !== last) { last = idx;
      out.push(Object.assign({ t: now - t0, at: now, page: idx, heard: _waLoop.playing() ? _waLoop.elapsed() - _waLoop.latency() : null }, heldBy(now))); }
    if (now - t0 < secs * 1000) requestAnimationFrame(tick); else done(out); })(); })"""
# For the players, which run no flip.js: pages each a colour of their own
# across the canvas's middle, so the middle pixel says which page is up.
COLOURS = [(40 + 17 * k, 220 - 15 * k, (90 + 37 * k) % 256) for k in range(12)]
COLOURED = """(o) => { frames.length = 0;
  for (let k = 0; k < o.cols.length; k++) { const f = newFrame(), pts = [], col = '#' + o.cols[k].map((v) => v.toString(16).padStart(2, '0')).join('');
    for (let j = 0; j < 30; j++) pts.push({ x: CW * 0.2 + j * CW * 0.6 / 29, y: CH * 0.5, color: col, size: 60, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); frames.push(f); }
  fps = 12; idx = 0; buildStrip(); render(); updateToolState(); scheduleSave(); }"""
# Where a player's song is, as heard: every looping source started is noted
# with the clock, its offset and its rate (a player's own variables are its own).
HEARD = """(() => { const real = AudioBufferSourceNode.prototype.start;
  AudioBufferSourceNode.prototype.start = function (when, off) {
    if (this.loop && this.buffer && this.buffer.duration > 2)
      window.__src = { ctx: this.context, at: Math.max(this.context.currentTime, when || 0), off: off || 0, dur: this.buffer.duration, rate: this.playbackRate.value };
    return real.apply(this, arguments); };
  window.__heard = () => { const s = window.__src; if (!s) return null; const c = s.ctx;
    return ((c.currentTime - s.at) * s.rate + s.off) % s.dur - ((c.baseLatency || 0) + (c.outputLatency || 0)); }; })();"""
# Each time the canvas's middle changes, its colour, the song as heard and how
# long the box held the page before (as REC's). The song is read FIRST: reading
# the canvas back waits on the GPU, longer the busier the box, and the song
# read after it was read that much late (rounds came 79ms "late" beside other
# suites).
WATCH = """([sel, secs]) => new Promise((done) => { const cv = document.querySelector(sel), g = cv.getContext('2d'), out = [], t0 = performance.now(); let last = null; """ + HELD_JS + """
  (function tick() { const now = performance.now(), h = window.__heard(), d = g.getImageData(cv.width >> 1, cv.height >> 1, 1, 1).data, key = d[0] + ',' + d[1] + ',' + d[2];
    look(now);
    if (key !== last) { last = key; out.push(Object.assign({ page: null, rgb: [d[0], d[1], d[2]], heard: h, t: now - t0 }, heldBy(now))); }
    if (now - t0 < secs * 1000) requestAnimationFrame(tick); else done(out); })(); })"""
# The song's clock held for ms, at ms into watching: its context suspended,
# then resumed, what a busy phone does by itself.
STALL = """([at, ms]) => { setTimeout(() => { const s = window.__src; if (!s) { window.__stalled = 'no song'; return; }
  window.__stalled = 'held'; s.ctx.suspend().then(() => setTimeout(() => s.ctx.resume(), ms)); }, at); }"""
# 4x from the link page's speed line, as a viewer picks it.
PICK4 = "() => { document.querySelector('#playerLine .rl-speed').click(); document.querySelector('#playerLine .rl-chips [data-r=\"4\"]').click(); }"
# The players' clock on its own: a context made up, its time set by hand.
# Each at() is given the caller's own time, the last one shown plus a frame's
# worth, as a player's frame() gives it.
CLOCK = """() => { const H = window.SkriblHold; if (!H || !H.songClock) return null;
  const a = { currentTime: 10, baseLatency: 0.01, outputLatency: 0.03, state: 'running' }, c = H.songClock(), o = {};
  c.began(a, 1000, 2); a.currentTime = 10.5; o.heard = c.at(99999);
  o.held = c.at(o.heard + 600); a.currentTime = 10.02; o.back = c.at(o.held + 100); o.long = c.at(o.back + 1500);
  const s = { currentTime: 5, state: 'suspended' }, d = H.songClock();
  d.began(s, 0, 1); o.notYet = d.at(777);
  s.state = 'running'; s.currentTime = 5.2; o.catching = d.at(900); s.currentTime = 6; o.follows = d.at(950);
  d.ended(); o.ended = d.at(4321);
  const g = { currentTime: 0, state: 'running' }, e = H.songClock(); let t = 0; const step = (ms) => (t = e.at(t + ms));
  e.began(g, 0, 1); g.currentTime = 0.1; step(100);
  g.state = 'interrupted'; step(500); o.gone = [step(500), step(500), step(500)];
  g.state = 'running'; g.currentTime = 0.6; o.gone.push(step(500), step(300));
  const q = { currentTime: 0, state: 'running' }, h = H.songClock(); let w = 0; o.glide = []; o.near = 0; h.began(q, 0, 1);
  for (let k = 1; k <= 40; k++) { q.currentTime = Math.floor(k * 16.667 / 40) * 0.04; const n = h.at(w + 16.667); o.glide.push(n - w); w = n;
    if (k > 8) o.near = Math.max(o.near, Math.abs(n - k * 16.667)); }
  const y = { currentTime: 0, state: 'running' }, z = H.songClock(); let v = 0, hic = []; z.began(y, 0, 1);
  for (let k = 1; k <= 180; k++) { const tt = k * 16.667 - Math.max(0, Math.min(k * 16.667 - 1000, 45)); y.currentTime = tt / 1000;
    const n = z.at(v + 16.667); if (k > 62) hic.push(n - v); v = n; if (k === 180) o.hicEnd = n - tt; }
  o.hic = [Math.min(...hic), Math.max(...hic)];
  const f = { currentTime: 0, state: 'running' }, m = H.songClock(); let x = 0; o.behind = 0; m.began(f, 0, 1);
  for (let k = 1; k <= 1200; k++) { f.currentTime = k * 0.016667 * 1.01; x = m.at(x + 16.667); o.behind = Math.max(o.behind, f.currentTime * 1000 - x); }
  return o; }"""
# A song that does not start when Play asks: its context suspended, and its
# unlock made to land ms late, as an iPhone's first Play can.
LATE = """(ms) => { const c = window.__src && window.__src.ctx; if (!c) return 'no song'; const r = c.resume.bind(c);
  return c.suspend().then(() => { c.resume = () => new Promise((ok, no) => setTimeout(() => r().then(ok, no), ms)); return c.state; }); }"""
# When Play is pressed, by the page's own clock.
PLAYAT = "() => document.getElementById('play').addEventListener('click', () => { window.__playAt = performance.now(); }, { once: true, capture: true })"
TAPS = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'); let i = 0, t0 = null, due = 0;
  const go = () => { if (t0 != null) while (performance.now() < t0 + due) {}
    if (t0 == null) t0 = performance.now(); b.click();
    if (i >= o.gaps.length) { res(true); return; }
    due += o.gaps[i++]; setTimeout(go, Math.max(0, t0 + due - performance.now() - 15)); };
  setTimeout(go, o.lead || 0); })"""


def editor(b, *, ears=True, still=False):
    c = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", **PHONE))
    if not ears:
        c.add_init_script(NO_EARS)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, "/flip")
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    q.evaluate(LISTENED)
    return c, q, errs


def song(q, f=BEAT, listen=True):
    browsing.pad_drawer(q, "music")
    q.set_input_files("#musicInput", f)
    q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
    if listen:
        q.wait_for_function("() => !!window.__earsDone", timeout=20000)
    waits.settle(q, 500)
    browsing.pad_drawer_close(q)


def tune(q):
    if not q.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"):
        q.click("#tuneBtn")
    waits.settle(q, 600)


def untune(q):
    if q.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"):
        q.click("#tuneBtn")
    waits.settle(q, 400)


def bar(st):
    return 4 * 60000 / st["bpm"]


def words(b):
    return {0.25: "¼ bar", 0.5: "½ bar", 1: "1 bar", 2: "2 bars"}[b]


def on_beat(off):
    """Every round within 45ms of its beat, and the middle one within 20ms:
    a frame late now and then is not a drift, nor a steady lag."""
    return bool(off) and max(abs(x) for x in off) <= 45 and abs(sorted(off)[len(off) // 2]) <= 20


def first_up(q, rec):
    """How long the page Play started on stayed up: from the press to the
    next page, as painted."""
    return rec[1]["at"] - q.evaluate("() => window.__playAt") if len(rec) > 1 else None


def page_of(rgb):
    """Which page a colour is, or None (the card, the ground, a blend)."""
    d, k = min((sum(abs(a - b) for a, b in zip(rgb, c)), k) for k, c in enumerate(COLOURS))
    return k if d < 30 else None


def steady(off):
    """Every round within 60ms of its beat, and none sliding: the last four
    where the first four were, within 25ms."""
    mid = lambda xs: sorted(xs)[len(xs) // 2]
    return len(off) >= 8 and max(abs(x) for x in off) <= 60 and abs(mid(off[-4:]) - mid(off[:4])) <= 25


class Round(float):
    """How far (ms) a round's first page came up from its beat, the longest
    the box held the page in the 300ms before it was seen (held, ms) and how
    long before it was seen that hold ended (held_at, ms)."""
    held = 0.0
    held_at = 0.0


def round_starts(rec, bpm, bars, first=0):
    """How far (ms) each round's first page came up from the song's beat grid
    for that round, as heard. Only pages that came up while listening: the
    page already up when it began says when the listening began."""
    R = bars * 4 * 60 / bpm
    out = []
    for r in rec[1:]:
        if r["page"] == first and r["heard"] is not None:
            e = r["heard"] % R
            x = Round((e - R if e > R / 2 else e) * 1000)
            x.held, x.held_at = r.get("held") or 0, r.get("heldAt") or 0
            out.append(x)
    return out


# A LOOK THAT COMES THIS LONG AFTER THE ONE BEFORE (ms, three frames) MEANS THE
# BOX HELD THE PAGE: a frame held, or a frame's work, or a timer's, and a page
# due in that time comes up, or is seen, as late as the box held it.
HELD = 50


def _held(off):
    """The round judged() sets aside: of those late while the box held the
    page (a hold of HELD or more that ended after the page fell due, so within
    the time it was late), the furthest off its beat; None when there is none."""
    held = [k for k, x in enumerate(off) if x.held >= HELD and x.held_at < x]
    return max(held, key=lambda k: abs(off[k])) if held else None


def judged(off):
    """The rounds a row holds to its beat: all but one late while the box held
    the page, which says how long the box held it, not where the drawing was.
    Flip's pages are a timer's, so the look after a hold can come before the
    timer and see the page late a look later: the hold is read off the looks
    of the 300ms before, not the last one alone.
    On main after #652 one round in a run came 106ms late, and in the next run
    one came 73ms late, each between rounds on the beat (the other 858 rounds
    in ten shards' logs were within 34ms); beside a CPU hog here, the two over
    60ms came up on frames 100 and 283ms after the frame before (86 and 134ms
    late), and one 58ms late was read 49ms into its frame. One at most, the
    furthest off, and said() names it: a drawing late on every round is late
    on rounds the box did not hold, and a page that holds itself every round
    is held on more than one."""
    i = _held(off)
    return off if i is None else off[:i] + off[i + 1:]


def said(off):
    """The rounds as a row says them, the one judged() sets aside marked."""
    i = _held(off)
    return " ".join(f"{x:+.0f}" + (f" (late while the box held the page {x.held:.0f}ms, set aside)" if k == i else "")
                    for k, x in enumerate(off))


with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    if part("show"):
        print("\nSHOWS WITH A BEAT -- heard or tapped; with none, Speed is as it was")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12})
        tune(q)
        st = q.evaluate(ST)
        check("with no song, Speed is 6 · 12 · 24 and Beat does not show",
              not st["shown"] and st["lit"] == ["12"] and st["hint"] == "pages per second", f"{st}")
        untune(q); song(q, TONE); tune(q)
        st = q.evaluate(ST)
        check("with a song Skribl hears no beat in (a steady tone), Beat does not show",
              not st["shown"] and st["bpm"] == 0, f"{st}")
        c.close()
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        st = q.evaluate(ST)
        check("with a beat Skribl heard, Beat shows beside 24",
              st["shown"] and abs(st["bpm"] - 124) < 0.1 and st["lit"] == ["12"], f"{st}")
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
        c, q, errs = editor(b, ears=False)
        q.evaluate(PAGES, {"n": 12}); song(q, listen=False)
        browsing.pad_drawer(q, "music")
        q.click('#musicDoors .dp-tile[data-dp="beat"]'); waits.settle(q, 500)   # Tap the beat is behind the Beat door
        q.evaluate("() => document.getElementById('musicTapBtn').scrollIntoView({ block: 'center' })")
        q.click("#musicTapBtn")                                     # the first tap starts the loop
        q.wait_for_function("() => _waLoop.playing() && _waLoop.elapsed() > 0.3", timeout=5000)
        q.evaluate(TAPS, {"lead": 300, "gaps": [500] * 6})
        q.wait_for_timeout(2600)
        browsing.pad_drawer_close(q); tune(q)
        st = q.evaluate(ST)
        check("with a beat tapped (Skribl not listening), Beat shows too",
              st["shown"] and abs(st["bpm"] - 120) < 1, f"{st}")
        c.close()

    if part("round"):
        print("\nTHE ROUND -- whole bars of the song, nearest the speed there was")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.evaluate("() => { const el = document.getElementById('beatMore'); window.__hs = [];"
                   " (function t() { window.__hs.push(el.getBoundingClientRect().height); if (window.__hs.length < 40) requestAnimationFrame(t); })(); }")
        q.click("#fpsBeat")
        q.wait_for_timeout(900)
        hs = q.evaluate("() => window.__hs")
        st = q.evaluate(ST)
        R = bar(st) * 0.5
        check("Beat picks the round nearest the speed there was: 12 pages at 12 a second is half a bar, to half a millisecond",
              st["bars"] == 0.5 and abs(st["round"] - R) < 0.5 and abs(st["fps"] - 12000 / R) < 1e-6,
              f"round {st['round']:.3f}ms against half a bar {R:.3f}, {st['fps']:.4f} a second, bars {st['bars']}")
        want = f"12 pages in ½ bar · {round(12000 / R, 1)} a second"
        check("Beat is lit and the numbers not; Speed says it is on the song's beat, and the line says what the round makes",
              st["lit"] == ["Beat"] and st["hint"] == "on the song’s beat" and st["say"] == want and st["open"] and not st["inert"],
              f"lit {st['lit']}, hint {st['hint']!r}, line {st['say']!r} (want {want!r}), open {st['open']}, inert {st['inert']}")
        full = max(hs) if hs else 0
        mid = [x for x in hs if 1 < x < full - 1]
        check("the round's choices open under Speed as a glide, frame by frame",
              full > 30 and len(mid) >= 3 and all(y >= x - 0.5 for x, y in zip(hs, hs[1:])),
              f"{len(mid)} frames on the way to {full:.0f}px: " + ", ".join(f"{x:.0f}" for x in hs[:14]))
        made = {}
        for bars in (0.25, 1, 2):
            q.click(f"#beatRoundSeg [data-bars='{bars}']"); waits.settle(q, 300)
            s2 = q.evaluate(ST); made[bars] = (s2["bars"], s2["round"], s2["fps"], s2["say"])
        ok = all(m[0] == bb and abs(m[1] - bar(st) * bb) < 0.5 and m[3].startswith("12 pages in " + words(bb)) for bb, m in made.items())
        check("a quarter, one and two bars each make a round of exactly that",
              ok, "; ".join(f"{bb}: {m[1]:.1f}ms at {m[2]:.3f} ({m[3]})" for bb, m in made.items()))
        q.click("#beatRoundSeg [data-bars='0.5']"); waits.settle(q, 300)
        untune(q)
        q.evaluate("() => { frames[2].hold = 2; scheduleSave(); }")
        s3 = q.evaluate(ST)
        q.evaluate("() => { delete frames[2].hold; frames[3].draw = true; scheduleSave(); }")
        s4 = q.evaluate(ST)
        span = q.evaluate("() => SkriblHold.pageMs(frames[3], fps)")
        check("a page held twice counts twice, and a page that draws itself keeps its own time",
              abs(s3["fps"] - 13000 / R) < 1e-6 and abs(s3["round"] - R) < 0.5
              and abs(s4["fps"] - 11000 / (R - span)) < 1e-6 and abs(s4["round"] - R) < 0.5,
              f"held: {s3['fps']:.4f} a second, round {s3['round']:.2f}; drawn ({span:.0f}ms): {s4['fps']:.4f}, round {s4['round']:.2f} (half a bar {R:.2f})")
        q.evaluate("() => { delete frames[3].draw; scheduleSave(); }")
        q.click("#addblank"); waits.settle(q, 400)
        s5 = q.evaluate(ST)
        check("a page added keeps the round: 13 pages in half a bar, at a new speed",
              s5["pages"] == 13 and s5["bars"] == 0.5 and abs(s5["round"] - R) < 0.5 and s5["say"].startswith("13 pages in ½ bar"),
              f"{s5['pages']} pages, round {s5['round']:.2f}ms, {s5['fps']:.4f} a second, {s5['say']!r}")
        q.evaluate("() => { docLoop = { from: 5, to: 12, forever: true }; scheduleSave(); }")
        s6 = q.evaluate(ST)
        check("a stretch looping forever is the round, the pages before it playing once",
              abs(s6["round"] - R) < 0.5 and abs(s6["fps"] - 8000 / R) < 1e-6 and s6["say"].startswith("The loop in ½ bar"),
              f"stretch {s6['round']:.2f}ms at {s6['fps']:.4f} a second, {s6['say']!r}")
        q.evaluate("() => { docLoop = null; frames.push(...Array.from({ length: 35 }, () => JSON.parse(JSON.stringify(frames[0])))); buildStrip(); scheduleSave(); }")
        s7 = q.evaluate(ST)
        check("a round these pages cannot make is not offered: 48 pages in a quarter bar would be over 60 a second",
              s7["pages"] == 48 and 0.25 not in s7["rounds"] and 0.5 in s7["rounds"] and 48000 / (bar(st) * 0.25) > 60,
              f"{s7['pages']} pages, rounds offered {s7['rounds']}")
        q.evaluate("() => { frames.length = 13; buildStrip(); scheduleSave(); }")
        tune(q)
        q.click("#fps [data-fps='12']"); waits.settle(q, 500)
        s8 = q.evaluate(ST)
        check("6, 12 or 24 turns Beat off and plays at that speed; the round's choices close",
              s8["bars"] is None and s8["fps"] == 12 and s8["lit"] == ["12"] and not s8["open"] and s8["inert"] and s8["shown"],
              f"{s8}")
        q.click("#fpsBeat"); waits.settle(q, 400)
        before = q.evaluate(ST)["fps"]
        untune(q)
        browsing.pad_drawer(q, "music")
        q.click("#musicRemove"); q.click("#musicRemove")           # it asks once more before it goes
        waits.settle(q, 500); browsing.pad_drawer_close(q)
        tune(q)
        s9 = q.evaluate(ST)
        check("the song taken away puts Beat aside, and the speed stays where it was",
              s9["bars"] is None and not s9["shown"] and abs(s9["fps"] - before) < 1e-9
              and s9["hint"] == f"pages per second · this one plays at {round(before, 2)}",
              f"before {before:.4f}; now {s9}")
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
        c, q, errs = editor(b, still=True)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.evaluate("() => { const el = document.getElementById('beatMore'); window.__hs = [];"
                   " (function t() { window.__hs.push(el.getBoundingClientRect().height); if (window.__hs.length < 30) requestAnimationFrame(t); })(); }")
        q.click("#fpsBeat"); q.wait_for_timeout(700)
        hs = q.evaluate("() => window.__hs")
        full = max(hs) if hs else 0
        check("under Reduce Motion the round's choices are there at once",
              full > 30 and not [x for x in hs if 1 < x < full - 1], ", ".join(f"{x:.0f}" for x in hs[:10]))
        c.close()

    if part("kept"):
        print("\nKEPT -- with the draft, and in the post")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.click("#fpsBeat"); waits.settle(q, 300)
        q.click("#beatRoundSeg [data-bars='1']"); waits.settle(q, 300)
        st = q.evaluate(ST)
        pay = q.evaluate("async () => { const p = await buildSharePayload(); return { fps: p.fps, beat: p.beat || null }; }")
        check("the post carries the speed and the round",
              pay["beat"] == {"bars": 1} and abs(pay["fps"] - st["fps"]) < 1e-9, f"{pay}, speed {st['fps']}")
        q.wait_for_timeout(2500)
        q.reload()
        q.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip", timeout=15000)
        waits.settle(q, 1200)
        tune(q)
        again = q.evaluate(ST)
        check("after a reload Beat is the speed, the same round and the same speed",
              again["bars"] == 1 and abs(again["fps"] - st["fps"]) < 1e-9 and again["lit"] == ["Beat"] and again["open"],
              f"before {st['bars']} at {st['fps']:.4f}; after {again['bars']} at {again['fps']:.4f}, lit {again['lit']}")
        c.close()

    if part("posted"):
        print("\nPOSTED -- the link page and a post's box keep it on the song")
        c, q, errs = editor(b)
        q.evaluate(COLOURED, {"cols": COLOURS}); song(q); tune(q)
        q.click("#fpsBeat"); waits.settle(q, 400); untune(q)
        bpm = q.evaluate("() => musicTempo.bpm")
        pid = q.evaluate("""async () => { const r = await fetch(window.SKRIBL_API_BASE, { method: 'POST', headers: skriblPostHeaders(),
            body: JSON.stringify(Object.assign(buildSharePayload(), { title: 'On the beat', visibility: 'public' })) });
          return (await r.json()).id; }""")
        c.close()
        v = b.new_context(**PHONE)
        v.add_init_script(HEARD)
        pg = v.new_page()
        perrs = []
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        pg.goto(f"{BASE}/s/{pid}", wait_until="load")
        pg.wait_for_selector("#playerPlayBtn", state="visible", timeout=20000); pg.wait_for_timeout(900)
        pg.click("#playerPlayBtn")
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, ["#canvas", 16])]
        off = round_starts(rec, bpm, 0.5)
        check("posted, the link page keeps the rounds on the song: each within 60ms of its beat as heard, none sliding",
              steady(judged(off)), f"{len(off)} rounds: " + said(off))
        pg.close()
        pg = v.new_page()
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        browsing.goto(pg, BASE, "/feed")
        box = f".skribl-inline[data-skribl-id='{pid}']"
        pg.wait_for_selector(box, state="attached", timeout=20000)
        pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", box)
        pg.wait_for_timeout(800)
        pg.evaluate("(s) => document.querySelector(s).click()", box)
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, [box + " .skribl-inline-canvas", 16])]
        off = round_starts(rec, bpm, 0.5)
        check("...and so does a post's box in the feed, its song started where the drawing is",
              steady(judged(off)), f"{len(off)} rounds: " + said(off))
        # Paused 2.3s into a fresh play, the drawing is a third of a round into
        # a pass: a song started again from its top is that far off the beat.
        pg.close()
        pg = v.new_page()
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        browsing.goto(pg, BASE, "/feed")
        pg.wait_for_selector(box, state="attached", timeout=20000)
        pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", box)
        pg.wait_for_timeout(800)
        pg.evaluate("(s) => document.querySelector(s).click()", box); pg.wait_for_timeout(2300)
        pg.evaluate("(s) => document.querySelector(s).click()", box); pg.wait_for_timeout(900)
        pg.evaluate("(s) => document.querySelector(s).click()", box)
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, [box + " .skribl-inline-canvas", 8])]
        off = round_starts(rec, bpm, 0.5)
        check("a pause in a post's box carries the song on from where it was: every round after it within 60ms of its beat",
              len(off) >= 6 and max(abs(x) for x in judged(off)) <= 60, said(off))
        # A STALL, on the link page and in the box: every round after it.
        def after_stall(rec):
            return round_starts([rec[0]] + [r for r in rec[1:] if r["t"] > 4600], bpm, 0.5) if rec else []
        pg.close()
        pg = v.new_page()
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        pg.goto(f"{BASE}/s/{pid}", wait_until="load")
        pg.wait_for_selector("#playerPlayBtn", state="visible", timeout=20000); pg.wait_for_timeout(900)
        clk = pg.evaluate(CLOCK)
        check("the players' clock is the song's as heard: begun at 1000ms, half a second on, less the speaker's 40ms, at twice the speed, is 1920ms",
              bool(clk) and abs(clk["heard"] - 1920) < 0.01, str(clk))
        check("...held, the drawing waits there and never steps back; a song whose context has not run is not the clock, "
              "and once it runs the drawing waits for it to catch up, then follows; ended, the wall's time again",
              bool(clk) and abs(clk["held"] - 1920) < 0.01 and abs(clk["back"] - 1920) < 0.01 and clk["notYet"] == 777
              and clk["catching"] == 777 and abs(clk["follows"] - 1000) < 0.01 and clk["ended"] == 4321, str(clk))
        check("...and it waits a second at most: a song gone (its context stopped: a call, the lock screen) is waited for a second "
              "(two of the drawing's at twice the speed), then the drawing goes on at the wall's pace; the song back, "
              "the drawing follows it from there and waits for the next stall again",
              bool(clk) and [round(x) for x in clk["gone"]] == [100, 600, 1100, 1600, 1600] and round(clk["long"]) == 2120,
              str(clk and [clk["gone"], clk["long"]]))
        # A browser moves the audio clock a callback at a time (9 to 20ms a
        # frame here, 40ms with a phone's Bluetooth): read straight off it, a
        # drawing stepped 0, 0, 40 where it should glide 16.7 a frame.
        _gl = (clk or {}).get("glide") or []
        check("...and it glides: with the song's clock moving in 40ms steps, as a phone's can, the drawing moves "
              "on every frame once the song is heard, 16.7ms give or take a tenth",
              len(_gl) == 40 and all(15.0 <= x <= 18.34 for x in _gl[4:]) and max(_gl[:4]) <= 40.01,
              " ".join(f"{x:.1f}" for x in _gl[:12]))
        check("...and keeps within 10ms of the song as it really plays: the clock's own steps are left out of how far it is",
              bool(clk) and clk["near"] <= 10, f"at most {clk and clk['near']:.1f}ms from it")
        check("...and a hiccup under 50ms (45ms), not waited for, is eased out: never more than a tenth slower, "
              "and the drawing is back on the song", bool(clk) and clk["hic"][0] >= 14.99 and abs(clk["hicEnd"]) <= 2,
              f"frames {clk and clk['hic'][0]:.2f} to {clk and clk['hic'][1]:.2f}ms; {clk and clk['hicEnd']:.1f}ms off the song at the end")
        check("...and a drawing that falls behind its song (a song's clock 1% fast, twenty seconds) eases back onto it, "
              "never more than 20ms behind", bool(clk) and 0 < clk["behind"] <= 20, f"at most {clk and clk['behind']:.1f}ms behind")
        pg.click("#playerPlayBtn")
        pg.evaluate(STALL, [3000, 300])
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, ["#canvas", 12])]
        off = after_stall(rec)
        check("posted, a song that stalls for 0.3s keeps the link page's rounds with it: every round after it within 60ms of its beat as heard",
              pg.evaluate("() => window.__stalled") == "held" and len(off) >= 6 and max(abs(x) for x in judged(off)) <= 60,
              f"{len(off)} rounds after it: " + said(off))
        # A song gone for 2.5s, a call's worth: the drawing waits a second for
        # it, no more, and goes on.
        pg.evaluate("() => { window.__stalled = null; }")
        pg.evaluate(STALL, [300, 2500])
        gone = pg.evaluate(WATCH, ["#canvas", 4.5])
        gap = max((y["t"] - x["t"] for x, y in zip(gone, gone[1:])), default=9999)
        check("...and a song gone for 2.5s (its context stopped, as a call stops it) holds the link page's drawing a second at most, "
              "then the drawing goes on: no page stays up 1.5s",
              pg.evaluate("() => window.__stalled") == "held" and len(gone) >= 25 and gap < 1500,
              f"{len(gone)} pages up in 4.5s; the longest a page stayed up {gap:.0f}ms")
        # A speed the song does not follow (4x: it keeps its own past 2x),
        # picked mid-play: the song is no longer the clock, and the drawing
        # takes it.
        pg.evaluate(PICK4)
        pg.wait_for_timeout(300)
        quick = pg.evaluate(WATCH, ["#canvas", 2])
        check("...and a speed it does not follow, picked mid-play (4x), the drawing takes: about four times the pages a second",
              len(quick) >= 60 and pg.evaluate("() => musicRate()") == 1,
              f"{len(quick)} pages up in 2s ({round(2 * 12 * bpm / 120)} at 1x: 12 a round, a round half a bar at {bpm:.0f} bpm)")
        # There the song is a bed at its own speed, not in step: when it stalls
        # the drawing does not wait for it (a page comes up every 20ms or so).
        pg.evaluate("() => { window.__stalled = null; }")
        pg.evaluate(STALL, [400, 300])
        bed = pg.evaluate(WATCH, ["#canvas", 2])
        gap = max((y["t"] - x["t"] for x, y in zip(bed, bed[1:])), default=9999)
        check("...and the song, a bed at its own speed there, does not hold the drawing when it stalls: no page stays up 0.15s",
              pg.evaluate("() => window.__stalled") == "held" and len(bed) >= 50 and gap < 150,
              f"{len(bed)} pages up in 2s with the song held 0.3s; the longest a page stayed up {gap:.0f}ms")
        pg.close()
        # Play again with the song's unlock landing 0.25s late, as an
        # iPhone's first Play can: the song starts where the drawing is by
        # then. Started where Play was pressed, the song's clock took the
        # drawing back three pages to meet it.
        pg = v.new_page()
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        pg.goto(f"{BASE}/s/{pid}", wait_until="load")
        pg.wait_for_selector("#playerPlayBtn", state="visible", timeout=20000); pg.wait_for_timeout(900)
        pg.click("#playerPlayBtn"); pg.wait_for_timeout(1500); pg.click("#playerPlayBtn")
        late = pg.evaluate(LATE, 250)
        pg.click("#playerPlayBtn")
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, ["#canvas", 4])]
        seen = [r["page"] for r in rec if r["page"] is not None]
        seen = seen[seen.index(0):] if 0 in seen else []
        back = [(x, y) for x, y in zip(seen, seen[1:]) if (y - x) % 12 not in (1, 2, 3)]
        off = round_starts([rec[0]] + [r for r in rec[1:] if r["t"] > 800], bpm, 0.5)
        check("...and when its song's unlock lands late (an iPhone's first Play), the song starts where the drawing is by then: "
              "the drawing never goes back a page, and every round after is within 60ms of its beat as heard",
              late == "suspended" and len(seen) >= 30 and not back and len(off) >= 2 and max(abs(x) for x in judged(off)) <= 60,
              f"{len(seen)} pages from the first, back {back[:3]}; rounds after " + said(off))
        pg.close()
        pg = v.new_page()
        pg.on("pageerror", lambda e: perrs.append(str(e)))
        browsing.goto(pg, BASE, "/feed")
        pg.wait_for_selector(box, state="attached", timeout=20000)
        pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", box)
        pg.wait_for_timeout(800)
        pg.evaluate("(s) => document.querySelector(s).click()", box)
        pg.evaluate(STALL, [3000, 300])
        rec = [dict(r, page=page_of(r["rgb"])) for r in pg.evaluate(WATCH, [box + " .skribl-inline-canvas", 12])]
        off = after_stall(rec)
        check("...and a post's box's: every round after it within 60ms of its beat as heard",
              pg.evaluate("() => window.__stalled") == "held" and len(off) >= 6 and max(abs(x) for x in judged(off)) <= 60,
              f"{len(off)} rounds after it: " + said(off))
        check("nothing went wrong on the link page or in the feed", not perrs, "; ".join(perrs)[:200])
        v.close()

    if part("beat"):
        print("\nON THE BEAT -- the pages keep to the song's own clock")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.click("#fpsBeat"); waits.settle(q, 300); untune(q)
        bpm = q.evaluate("() => musicTempo.bpm")
        q.evaluate("() => { idx = 0; render(); }"); q.evaluate(PLAYAT)
        q.click("#play"); rec = q.evaluate(REC, 16); q.click("#play")
        up1 = first_up(q, rec)
        off = round_starts(rec, bpm, 0.5)
        check("playing, every round starts on the song's beat as heard, for sixteen seconds: each within 45ms, the middle one within 20ms",
              len(off) >= 15 and on_beat(judged(off)),
              f"{len(off)} rounds: " + said(off))
        waits.settle(q, 400)
        # A song started from its top would hold page 8 up until the song came
        # round to it: half a second, standing still.
        q.evaluate("() => { idx = 7; render(); }"); q.evaluate(PLAYAT)
        q.click("#play"); rec = q.evaluate(REC, 5); q.click("#play")
        up8 = first_up(q, rec)
        first = rec[0]["page"] if rec else None
        off = round_starts(rec, bpm, 0.5)
        check("Play from page 8 starts the song as far into its round: page 8 is up as long as page 1 was from Play, and the first round lands on the beat too",
              first == 7 and up1 is not None and up8 is not None and abs(up8 - up1) <= 40
              and len(off) >= 4 and abs(judged(off)[0]) <= 45 and on_beat(judged(off)),
              f"first page {first}, up {up8 or 0:.0f}ms (page 1 from Play {up1 or 0:.0f}), rounds: " + said(off))
        waits.settle(q, 400)
        q.evaluate("() => { idx = 0; render(); }")
        q.click("#play"); q.wait_for_timeout(2300)
        q.evaluate("() => pausePlay()"); q.wait_for_timeout(900); q.evaluate("() => resumePlay()")
        rec = q.evaluate(REC, 5); q.click("#play")
        off = round_starts(rec, bpm, 0.5)
        check("a pause and a resume keep them together",
              len(off) >= 4 and on_beat(judged(off)), said(off))
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
