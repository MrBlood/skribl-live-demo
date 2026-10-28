#!/usr/bin/env python3
"""Skribl's ears: a new song's pick starts on a bar and is whole bars long,
on the beat Skribl heard (step 3 of the music plan, "the part that loops
best, on the beat"; the mock, with songs to hear, and the owner: "all yes").

THE SONGS ARE MADE HERE, in the page, so where every beat and every bar falls
is known exactly, and every row is held to that, never to the ears' own
numbers. A steady song at 124 a minute (an intro of chords and hi-hats, then
the drums); a swung one at 88 (32 beats would be over the 20s a loop can be);
a live band speeding up from 100 to 102, every hit a little early or late; a
rock beat at 120 whose kicks, an 808's with no click, fall between its
snares; slow chords with no drums; and three that must not be heard as a
beat: a steady tone and a sweeping one, the kind of song the other music
suites load, and sounds starting at random, as rain does. Each of the two things that make
a beat steady has one of them only it can tell (lib/musicears.js): the sweep
gathers round a beat's circle but has no sound starting on its beats, and the
rain has sounds on most beats but gathers round no circle.

  ON THE BEAT. A new song with a steady beat starts on the bar where the
  drums come in, within 10ms, and is 32 beats long by the song's own beats,
  within 10ms (the swung song 16, from its groove's first bar; the band 32,
  within 15ms of its bars). The beat heard is the song's, to a twentieth of
  a beat a minute, on the loop's start, and marked heard; the one line
  counts it ("32 beats") under Skribl's pick, and the beat line says so
  ("124 beats a minute, heard by Skribl · tap to change it"), having said
  "Listening for the beat…" while it listened. The rock beat is heard at
  120, not at 60 on its snares (the flux hears a kick least), and its pick
  is 32 of its beats from the bar where its drums come in. Decoded at
  48 kHz, as phones and Windows decode, the swung song is heard as it is at
  44.1 (it was heard at 176).

  KIND. The loop glides to its pick and the beat marks fade in, read on every
  animation frame; at once under Reduce Motion. With no steady beat (slow
  chords, a tone, a sweep, rain) the pick is today's, the first 20 seconds,
  no beat is set, and the beat line says Skribl didn't hear one. A loop
  moved, or a beat tapped, before Skribl has listened stays as it is. Back to
  Skribl's pick goes to the heard pick and beat, and its Undo brings back the
  loop and the beat that were there.

  THE PAD'S LENGTH. With a drawing, whole bars nearest it (the owner's pick):
  a 7-second drawing gets 16 beats.

  BEATS (the owner: "There should be ways to have skribl pick 4 or 8 16
  32"; of the mock, "All yes if it's intuitive"). A count tapped on Skribl's
  pick is Skribl's pick for that many beats where the loop is: from the
  steady song's 32, 8 is inside the loop (picked from the whole song it was
  at 23.5s, the loop at 4.2s), on a bar and 8 of the song's beats long; it is
  still Skribl's pick, and the way back never shows on the way there. Undo
  brings back the 32 and its beat. Longer, 16 from that 8 is around it and
  keeps its start, and Undo of it brings back the 8, still Skribl's pick. A
  band that speeds up keeps the start to the millisecond from its 4 to its
  32 (its bars sit a little apart in each stretch heard). A loop of the
  person's own, its start a beat past the bar, keeps its start.

  KEPT. The loop and the heard beat come back after a reload, still "heard
  by Skribl". The song brought back is heard again, once and quietly: the
  loop and the beat stay as kept, and it is still Skribl's pick (not heard
  again, the pick said "Back to Skribl's pick", and that went to the song's
  first 20 seconds, 40.8 beats from 0:00); while Skribl hears it, Skribl's
  pick is not lit nor the way back offered; moved, the way back (Skribl's
  pick, in the Length door) goes to the heard pick. Snap to the beat's switch
  keeps it heard. (`tag` below is Skribl's pick lit, as the pick line's tag
  said it until the four doors.)

Every row runs on the Pad and on Flip, on a phone: one drawer
(lib/musicdrawer.js) and one pair of ears (lib/musicears.js).
"""
import base64
import json
import os
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence that Skribl hears a song's beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICEARS_ONLY=Pad (or Flip) runs one editor, and
# MUSICEARS_PART=beat (glide, none, pad, beats, kind, kept) one part. A real run sets neither.
ONLY = os.environ.get("MUSICEARS_ONLY", "")
PART = os.environ.get("MUSICEARS_PART", "")
EDITORS = [e for e in (("Pad", "/skribl-pad"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


# THE SONGS, synthesised in the page: drums, bass, chords and a plucked lead,
# a section at a time, with every beat's and every bar's time kept.
SYNTH = r"""(spec) => {
  const SR = 22050; let s0 = spec.seed >>> 0;
  const r = () => { s0 = (s0 * 1664525 + 1013904223) >>> 0; return s0 / 4294967296; };
  const gauss = () => { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); };
  const hz = (pc, oct) => 440 * Math.pow(2, (pc - 9) / 12 + (oct - 4));
  const CH = { C: [0, [0, 4, 7]], G: [7, [0, 4, 7]], Am: [9, [0, 3, 7]], F: [5, [0, 4, 7]], Dm: [2, [0, 3, 7, 10]],
               G7: [7, [0, 4, 7, 10]], Cmaj7: [0, [0, 4, 7, 11]], Em: [4, [0, 3, 7]] };
  const bars = spec.sections.reduce((n, s) => n + s.bars, 0), N = bars * 4, p0 = 60 / spec.bpm;
  const beats = [spec.lead];
  for (let b = 0; b < N; b++) beats.push(beats[b] + p0 / (1 + (spec.drift || 0) * b / N));
  const at = (b) => { const i = Math.floor(b), f = b - i; return beats[i] + f * (beats[i + 1] - beats[i]); };
  const out = new Float32Array(Math.ceil((beats[N] + 1.5) * SR));
  const add = (t0, fn, dur) => { const i0 = Math.max(0, Math.round(t0 * SR)), n = Math.min(out.length - i0, Math.round(dur * SR));
    for (let i = 0; i < n; i++) out[i0 + i] += fn(i / SR); };
  const jit = () => spec.jitter ? gauss() * spec.jitter : 0;
  const kick = (t, a) => add(t + jit(), (x) => a * 0.9 * Math.sin(2 * Math.PI * (45 * x + 75 * (1 - Math.exp(-x * 30)) / 30)) * Math.exp(-x * 9) + (x < 0.003 && !spec.sub ? a * 0.3 * (r() - 0.5) : 0), 0.45);
  const snare = (t, a) => { let hp = 0, pv = 0; add(t + jit(), (x) => { const n = r() * 2 - 1; hp = 0.6 * (hp + n - pv); pv = n;
    return a * (0.45 * hp * Math.exp(-x * 18) + 0.25 * Math.sin(2 * Math.PI * 185 * x) * Math.exp(-x * 25)); }, 0.3); };
  const hat = (t, a) => { let pv = 0; add(t + jit(), (x) => { const n = r() * 2 - 1, v = n - pv; pv = n; return a * 0.12 * v * Math.exp(-x * 70); }, 0.08); };
  const bass = (t, f, dur, a) => { let lp = 0; add(t + jit() * 0.5, (x) => { const ph = f * x;
    const v = Math.sin(2 * Math.PI * ph) + 0.5 * Math.sin(4 * Math.PI * ph) + 0.25 * Math.sin(6 * Math.PI * ph); lp += 0.25 * (v - lp);
    return a * 0.22 * lp * Math.min(1, x * 200) * Math.exp(-x * 2.5) * (x < dur ? 1 : Math.exp(-(x - dur) * 40)); }, dur + 0.15); };
  const pad = (t, ch, dur, a) => { const [root, ivs] = CH[ch], fs = ivs.map((iv) => hz((root + iv) % 12, 4 + (root + iv >= 12 ? 1 : 0)));
    add(t, (x) => { let v = 0; for (const f of fs) v += Math.sin(2 * Math.PI * f * x + 0.002 * Math.sin(2 * Math.PI * 5 * x) * f) + 0.11 * Math.sin(6 * Math.PI * f * x);
      return a * 0.045 * v * Math.min(1, x / 0.25) * (x < dur ? 1 : Math.exp(-(x - dur) * 6)); }, dur + 0.6); };
  const pluck = (t, f, a) => add(t + jit() * 0.5, (x) => a * 0.09 * (Math.sin(2 * Math.PI * f * x) + 0.3 * Math.sin(4 * Math.PI * f * x)) * Math.exp(-x * 7) * Math.min(1, x * 400), 0.6);
  const truth = { bpm: spec.bpm, beats: beats.slice(0, N), downbeats: [], drums: [] };
  let bar = 0;
  for (const sec of spec.sections) for (let j = 0; j < sec.bars; j++, bar++) {
    const b0 = bar * 4, ch = sec.chords[j % sec.chords.length], k = sec.kit || {};
    truth.downbeats.push(at(b0));
    if (sec.pad) pad(at(b0), ch, at(b0 + 4) - at(b0), sec.pad);
    for (let q = 0; q < 16; q++) {
      const t = at(b0 + (q + (q % 2 && spec.swing ? spec.swing : 0)) / 4);
      if (k.kick && k.kick[q]) kick(t, k.kick[q]);
      if (k.snare && k.snare[q]) snare(t, k.snare[q]);
      if (k.hat && k.hat[q]) hat(t, k.hat[q]);
      if (k.bass && k.bass[q]) bass(t, hz(CH[ch][0], 2), (at(b0 + (q + 2) / 4) - t) * 0.9, k.bass[q]);
      if (sec.lead && q % 2 === 0) { const [rt, ivs] = CH[ch]; pluck(t, hz((rt + ivs[(q / 2) % ivs.length]) % 12, 5), sec.lead); }
    }
    if (k.kick || k.snare) truth.drums.push(at(b0));
  }
  if (spec.tone) { for (let i = 0; i < out.length; i++) out[i] = 0.37 * Math.sin(2 * Math.PI * 220 * i / SR); }
  if (spec.sweep) { for (let i = 0; i < out.length; i++) out[i] = 0.27 * Math.sin(2 * Math.PI * (220 + 30 * i / SR) * i / SR); }
  if (spec.scatter) for (let t = 0.2; t < out.length / SR - 0.3; t += -Math.log(1 - r()) / spec.scatter)
    add(t, (x) => (r() * 2 - 1) * Math.exp(-x * 60) * 0.6, 0.06);
  if (spec.fade) { const n = Math.round(spec.fade * SR), e = Math.round(beats[N] * SR); for (let i = 0; i < out.length; i++) out[i] *= i < e - n ? 1 : i < e ? (e - i) / n : 0; }
  let pk = 0; for (const v of out) pk = Math.max(pk, Math.abs(v)); pk = pk || 1;
  const pcm = new Int16Array(out.length);
  const plain = spec.tone || spec.sweep;
  for (let i = 0; i < out.length; i++) pcm[i] = Math.round(plain ? out[i] * 32767 : Math.tanh(out[i] / pk * 1.2) * 0.85 * 32767);
  const head = new DataView(new ArrayBuffer(44)), w = (o, s) => { for (let i = 0; i < 4; i++) head.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); head.setUint32(4, 36 + pcm.length * 2, true); w(8, 'WAVE'); w(12, 'fmt '); head.setUint32(16, 16, true);
  head.setUint16(20, 1, true); head.setUint16(22, 1, true); head.setUint32(24, SR, true); head.setUint32(28, SR * 2, true);
  head.setUint16(32, 2, true); head.setUint16(34, 16, true); w(36, 'data'); head.setUint32(40, pcm.length * 2, true);
  const bytes = new Uint8Array(44 + pcm.length * 2); bytes.set(new Uint8Array(head.buffer), 0); bytes.set(new Uint8Array(pcm.buffer), 44);
  let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return { wav: btoa(bin), truth, seconds: out.length / SR };
}"""
X, x = 1, 0.5
FLOOR = {"kick": [X, 0, 0, 0] * 4, "snare": [0, 0, 0, 0, X, 0, 0, 0] * 2, "hat": [0, 0, x, 0] * 4, "bass": [X, 0, x, 0] * 4}
HATS = {"hat": [x, 0] * 8}
LAZY = {"kick": [X, 0, 0, 0, 0, 0, x, 0, 0, 0, X, x, 0, 0, 0, 0], "snare": [0, 0, 0, 0, X, 0, 0, 0, 0, 0, 0, 0, X, 0, 0, x],
        "hat": [x] * 16, "bass": [X, 0, 0, 0, 0, 0, x, 0, 0, 0, X, 0, 0, 0, x, 0]}
BAND = {"kick": [X, 0, 0, 0, 0, 0, 0, 0] * 2, "snare": [0, 0, 0, 0, X, 0, 0, 0] * 2, "hat": [x, 0] * 8, "bass": [X, 0, 0, 0] * 4}
ROCK = {"kick": [X, 0, 0, 0, 0, 0, 0, 0] * 2, "snare": [0, 0, 0, 0, X, 0, 0, 0] * 2, "bass": [X, 0, 0, 0, 0, 0, 0, 0] * 2}
SPECS = {
    "steady": {"bpm": 124, "lead": 0.30, "fade": 2.5, "seed": 11, "sections": [
        {"bars": 2, "chords": ["C", "G"], "pad": 1, "kit": HATS},
        {"bars": 12, "chords": ["C", "G", "Am", "F"], "pad": 1, "kit": FLOOR},
        {"bars": 4, "chords": ["Am", "F", "C", "G"], "pad": 1, "kit": FLOOR, "lead": 1},
        {"bars": 1, "chords": ["C"], "pad": 1, "kit": HATS}]},
    "swung": {"bpm": 88, "lead": 0.80, "swing": 0.33, "fade": 2.5, "seed": 23, "sections": [
        {"bars": 1, "chords": ["Dm"], "pad": 1},
        {"bars": 12, "chords": ["Dm", "G7", "Cmaj7", "Am"], "pad": 1, "kit": LAZY}]},
    "band": {"bpm": 100, "lead": 0.12, "drift": 0.02, "jitter": 0.008, "fade": 2.5, "seed": 31, "sections": [
        {"bars": 1, "chords": ["C"], "kit": {"hat": [X, 0, 0, 0] * 4}},
        {"bars": 16, "chords": ["C", "F", "Am", "G"], "pad": 0.8, "kit": BAND}]},
    # kicks on 1 and 3, snares on 2 and 4, and the kick an 808's: no click
    "rock": {"bpm": 120, "lead": 0.40, "fade": 2.5, "seed": 71, "sub": True, "sections": [
        {"bars": 1, "chords": ["Am"], "pad": 1, "kit": HATS},
        {"bars": 12, "chords": ["Am", "F", "C", "G"], "pad": 1, "kit": ROCK}]},
    "chords": {"bpm": 45, "lead": 0.5, "fade": 4, "seed": 41, "sections": [
        {"bars": 6, "chords": ["Cmaj7", "Am", "F", "G", "Em", "F"], "pad": 1.4}]},
    "tone": {"bpm": 60, "lead": 0, "seed": 1, "tone": True, "sections": [{"bars": 3, "chords": ["C"]}]},
    "sweep": {"bpm": 60, "lead": 0, "seed": 2, "sweep": True, "sections": [{"bars": 3, "chords": ["C"]}]},
    "scatter": {"bpm": 60, "lead": 0, "seed": 5, "scatter": 12, "sections": [{"bars": 7, "chords": ["C"]}]},
}

STATE = """() => { const tl = document.getElementById('musicTimeline'), p = tl && tl._painted;
  return { s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs, tempo: musicTempo,
           line: (document.getElementById('musicPickText') || {}).textContent || '',
           tag: ((c) => !!c && c.getAttribute('aria-pressed') === 'true')(document.getElementById('musicPickCard')),
           back: ((c) => !!c && c.getAttribute('aria-pressed') !== 'true' && !c.disabled)(document.getElementById('musicPickCard')),
           undo: !(document.getElementById('musicPickUndo') || { hidden: true }).hidden,
           beat: (document.getElementById('musicTempo') || {}).textContent || '', beatIn: p ? p.beatIn : null }; }"""
# Every animation frame from now: the loop's ends, how far the marks have
# faded in, and the beat line's words (the glide, the fade and "Listening").
RECORD = """() => { window.__rec = []; const t0 = performance.now();
  (function tick() { const tl = document.getElementById('musicTimeline'), p = tl && tl._painted;
    window.__rec.push({ t: performance.now() - t0, s: trimStart, e: trimEnd, bi: p && musicTempo ? p.beatIn : null,
                        w: (document.getElementById('musicTempo') || {}).textContent || '', tempo: !!musicTempo });
    if (window.__rec.length < 900) requestAnimationFrame(tick); })(); }"""
# Every animation frame from just before a tap on Beats: the loop's start,
# and whether Skribl's pick is lit (`tag`, as the pick line's tag said until
# the four doors) and the way back is offered; and when the tap landed.
TAGS = """() => { const out = window.__rec = [], t0 = performance.now(), q = (id) => document.getElementById(id), card = q('musicPickCard');
  window.__tapAt = null;
  q('musicBeatsSeg').addEventListener('click', () => { window.__tapAt = performance.now() - t0; }, { capture: true, once: true });
  (function f() { const lit = card.getAttribute('aria-pressed') === 'true';
    out.push([performance.now() - t0, trimStart, lit, !lit && !card.disabled]);
    if (performance.now() - t0 < 800) requestAnimationFrame(f); })(); }"""
# Skribl's answer held until released, so what a person does meanwhile can be done.
HOLD = """() => { const E = window.SkriblEars, real = E.listen; window.__held = [];
  E.listen = (buf, done) => { let h = null; window.__held.push(() => { h = real(buf, done); }); return { cancel() { if (h) h.cancel(); } }; }; }"""
RELEASE = "() => { (window.__held || []).splice(0).forEach((go) => go()); }"
# How many times the ears are asked to listen, from before the page's scripts
# run; each answer held until RELEASE, so what shows while Skribl listens can
# be read.
COUNT_INIT = """Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return this.__ears; },
  set(v) { const real = v.listen; window.__held = [];
    v.listen = function (b, d) { window.__listens = (window.__listens || 0) + 1; let h = null;
      window.__held.push(() => { h = real(b, d); }); return { cancel() { if (h) h.cancel(); } }; }; this.__ears = v; } });"""
LONGDRAW = """(secs) => { strokes.length = 0;
  for (let i = 0; i <= secs * 20; i++) strokes.push({ x: 40 + (i % 20) * 9, y: 60 + Math.floor(i / 20) % 8 * 20, color: '#7c5cff', size: 6, t: i * 50, start: i % 20 === 0 });
  updateDrawingTimeLabels(); }"""
EARS_DONE = "() => !!window.__earsDone"
# The page's audio at 48 kHz, as phones and Windows decode (this box's Chromium decodes at 44.1).
AT48K = """(() => { const A = window.AudioContext; if (!A) return;
  window.AudioContext = class extends A { constructor(o) { super(Object.assign({ sampleRate: 48000 }, o || {})); } }; })();"""
LISTENED = """() => { const E = window.SkriblEars; if (!E || E.__wrapped) return; const real = E.listen; E.__wrapped = true;
  E.listen = (b, d) => real(b, (H) => { d(H); window.__earsDone = true; }); }"""

SONGS = {}


def songs(b):
    c = b.new_context()
    q = c.new_page()
    browsing.goto(q, BASE, "/skribl-pad")
    for name, spec in SPECS.items():
        r = q.evaluate(SYNTH, spec)
        SONGS[name] = {"file": {"name": name + ".wav", "mimeType": "audio/wav", "buffer": base64.b64decode(r["wav"])},
                       "truth": r["truth"], "seconds": r["seconds"]}
    c.close()


def editor(b, path, *, still=False, init=None):
    c = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", **PHONE))
    if init:
        c.add_init_script(init)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, path)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    q.evaluate(LISTENED)
    return c, q, errs


def add(q, name, wait=True):
    browsing.pad_drawer(q, "music")
    q.set_input_files("#musicInput", SONGS[name]["file"])
    q.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                        " && Math.abs(audioDuration - d) < 0.2", arg=SONGS[name]["seconds"], timeout=20000)
    if wait:
        q.wait_for_function(EARS_DONE, timeout=20000)
        waits.settle(q, 600)
    return q.evaluate(STATE)


def length_door(q):
    """The Length door open: Skribl's pick, Beats and their Undo are in it."""
    t = '#musicDoors .dp-tile[data-dp="length"]'
    if q.get_attribute(t, "aria-expanded") != "true":
        q.click(t); waits.settle(q, 400)


def tap(q, sel):
    """A real click on a count of Beats (or on Skribl's pick, or on Undo), in
    the Length door, then the glide: a control a broken build hides makes a
    row say so in red, not a timeout."""
    length_door(q)
    try:
        q.click(sel if str(sel).startswith("#") else f'#musicBeatsSeg button[data-beats="{sel}"]', timeout=3000)
    except Exception:
        return False
    waits.settle(q, 500)
    return True


def heard_len(st):
    n = st["e"] - st["s"]
    return n - min(st["xf"] / 1000, n / 2)


def nearest(ts, t):
    return min(ts, key=lambda v: abs(v - t))


def bars_from(truth, start, k):
    """The song's own length of k beats from the bar nearest `start`."""
    db = nearest(truth["downbeats"], start)
    j = min(range(len(truth["beats"])), key=lambda i: abs(truth["beats"][i] - db))
    return truth["beats"][j + k] - truth["beats"][j] if j + k < len(truth["beats"]) else None


with sync_playwright() as p:
    b = p.chromium.launch()
    songs(b)
    T = SONGS["steady"]["truth"]

    print("\nON THE BEAT -- a new song starts on a bar, whole bars long, on the beat heard")
    for name, path in eds("beat"):
        c, q, errs = editor(b, path)
        q.evaluate(RECORD)
        st = add(q, "steady")
        rec = q.evaluate("() => window.__rec")
        check(f"{name}: a new song with a steady beat starts on the bar where the drums come in, within 10ms",
              abs(st["s"] - T["drums"][0]) <= 0.010, f"start {st['s']:.4f}, the drums come in at {T['drums'][0]:.4f}")
        L, want = heard_len(st), bars_from(T, st["s"], 32)
        check(f"{name}: it is 32 beats long by the song's own beats, within 10ms",
              want is not None and abs(L - want) <= 0.010, f"heard {L:.4f}s, 32 beats from that bar {want}")
        tp = st["tempo"] or {}
        check(f"{name}: the beat heard is the song's, on the loop's start, and marked heard",
              abs(tp.get("bpm", 0) - 124) <= 0.05 and abs(tp.get("phase", -1) - st["s"]) <= 0.001 and tp.get("heard") is True,
              f"tempo {tp}, start {st['s']:.4f}")
        check(f"{name}: the one line counts it under Skribl's pick",
              "32 beats" in st["line"] and st["tag"] and not st["back"], f"line {st['line']!r}, tag {st['tag']}, back {st['back']}")
        check(f"{name}: the beat line says it was heard",
              st["beat"] == "124 beats a minute, heard by Skribl\u00a0· tap to change it", repr(st["beat"]))
        said = [r["w"] for r in rec]
        check(f"{name}: while it listened the beat line said so",
              any(w == "Listening for the beat…" for w in said), " | ".join(dict.fromkeys(said))[:200])
        check(f"{name}: nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()

        c, q, errs = editor(b, path)
        st = add(q, "swung")
        TS = SONGS["swung"]["truth"]
        L, want = heard_len(st), bars_from(TS, st["s"], 16)
        check(f"{name}: at 88 a minute (32 beats would be over 20s) it is 16 beats from the groove's first bar, within 10ms",
              abs(st["s"] - TS["drums"][0]) <= 0.010 and want is not None and abs(L - want) <= 0.010
              and abs((st["tempo"] or {}).get("bpm", 0) - 88) <= 0.05,
              f"start {st['s']:.4f} (groove {TS['drums'][0]:.4f}), heard {L:.4f}s against {want}, tempo {st['tempo']}")
        c.close()

        c, q, errs = editor(b, path)
        st = add(q, "band")
        TB = SONGS["band"]["truth"]
        L, want = heard_len(st), bars_from(TB, st["s"], 32)
        off = st["s"] - nearest(TB["downbeats"], st["s"])
        check(f"{name}: a band speeding up starts within 15ms of a bar and is 32 of its beats long, within 15ms",
              abs(off) <= 0.015 and want is not None and abs(L - want) <= 0.015,
              f"start {st['s']:.4f} ({off * 1000:+.1f}ms from a bar), heard {L:.4f}s against {want}")
        c.close()

        c, q, errs = editor(b, path)
        st = add(q, "rock")
        TR, tp = SONGS["rock"]["truth"], st["tempo"] or {}
        L, want = heard_len(st), bars_from(TR, st["s"], 32)
        check(f"{name}: a rock beat at 120, an 808's kicks between its snares, is heard at 120, not at 60 on its snares",
              abs(tp.get("bpm", 0) - 120) <= 0.05 and tp.get("heard") is True and "32 beats" in st["line"],
              f"tempo {tp}, line {st['line']!r}")
        check(f"{name}: and its pick is 32 of its beats from the bar where its drums come in, within 10ms",
              abs(st["s"] - TR["drums"][0]) <= 0.010 and want is not None and abs(L - want) <= 0.010,
              f"start {st['s']:.4f} (the drums come in at {TR['drums'][0]:.4f}), heard {L:.4f}s against {want}")
        c.close()

        c, q, errs = editor(b, path, init=AT48K)
        st = add(q, "swung")
        rate = q.evaluate("() => currentAudioBuffer.sampleRate")
        L, want = heard_len(st), bars_from(TS, st["s"], 16)
        check(f"{name}: decoded at 48 kHz, as phones and Windows decode, the swung song is heard as at 44.1: 88 a minute, 16 beats from its groove's first bar",
              rate == 48000 and abs((st["tempo"] or {}).get("bpm", 0) - 88) <= 0.05
              and abs(st["s"] - TS["drums"][0]) <= 0.010 and want is not None and abs(L - want) <= 0.010,
              f"decoded at {rate}; start {st['s']:.4f} (groove {TS['drums'][0]:.4f}), heard {L:.4f}s against {want}, tempo {st['tempo']}")
        c.close()

    print("\nKIND -- the loop glides to its pick and the marks fade in; at once under Reduce Motion")
    for name, path in eds("glide"):
        for still in (False, True):
            c, q, errs = editor(b, path, still=still)
            q.evaluate(RECORD)
            st = add(q, "steady")
            rec = q.evaluate("() => window.__rec")
            moving = [r for r in rec if 0.01 < r["s"] < st["s"] - 0.01]
            fading = [r for r in rec if r["bi"] is not None and 0.02 < r["bi"] < 0.98]
            if not still:
                check(f"{name}: the loop glides to its pick, frame by frame",
                      len(moving) >= 3 and all(b2["s"] >= a["s"] - 1e-6 for a, b2 in zip(moving, moving[1:])),
                      f"{len(moving)} frames on the way: " + ", ".join(f"{r['s']:.2f}" for r in moving[:8]))
                check(f"{name}: and the beat marks fade in, frame by frame",
                      len(fading) >= 3 and all(b2["bi"] >= a["bi"] for a, b2 in zip(fading, fading[1:])),
                      f"{len(fading)} frames fading: " + ", ".join(f"{r['bi']:.2f}" for r in fading[:8]))
            else:
                first = next((r for r in rec if r["bi"] is not None), None)
                check(f"{name}: under Reduce Motion the loop and the marks are there at once",
                      not moving and not fading and first is not None and first["bi"] == 1,
                      f"{len(moving)} frames moving, {len(fading)} fading, first {first}")
            c.close()

    print("\nNO STEADY BEAT -- the pick is today's and nothing is set")
    for name, path in eds("none"):
        for song, what in (("chords", "slow chords"), ("tone", "a steady tone"), ("sweep", "a sweeping tone"),
                           ("scatter", "sounds starting at random, as rain does")):
            c, q, errs = editor(b, path)
            st = add(q, song)
            check(f"{name}: with {what}, the pick is today's, the first 20 seconds, and no beat is set",
                  abs(st["s"]) < 1e-6 and abs(st["e"] - min(20, st["d"])) < 1e-3 and st["tempo"] is None,
                  f"loop {st['s']:.3f}-{st['e']:.3f} of {st['d']:.2f}s, tempo {st['tempo']}")
            check(f"{name}: with {what}, the beat line says Skribl didn't hear one",
                  st["beat"] == "Skribl didn’t hear a steady beat. Tap along with the music to count one.", repr(st["beat"]))
            c.close()

    print("\nTHE PAD'S LENGTH -- with a drawing, whole bars nearest it")
    for name, path in [e for e in eds("pad") if e[0] == "Pad"]:
        c, q, errs = editor(b, path)
        q.evaluate(LONGDRAW, 7)
        secs = q.evaluate("() => getPlaybackDuration() / 1000")
        st = add(q, "steady")
        L = heard_len(st)
        check(f"{name}: a {secs:.1f}-second drawing gets 16 beats, the count nearest it, from the bar where the drums come in",
              abs(st["s"] - T["drums"][0]) <= 0.010 and abs(L - bars_from(T, st["s"], 16)) <= 0.010 and "16 beats" in st["line"],
              f"start {st['s']:.4f}, heard {L:.4f}s, line {st['line']!r}")
        c.close()

    print("\nBEATS -- a count tapped on Skribl's pick is Skribl's pick for that many, where the loop is")
    for name, path in eds("beats"):
        c, q, errs = editor(b, path)
        st = add(q, "steady")
        length_door(q)
        q.evaluate("() => document.getElementById('musicBeatsRow').scrollIntoView({ block: 'center' })"); q.wait_for_timeout(300)
        q.evaluate(TAGS)
        tap(q, 8)
        a8 = q.evaluate(STATE)
        rec, at = q.evaluate("() => window.__rec"), q.evaluate("() => window.__tapAt")
        after = [f for f in rec if at is not None and f[0] >= at]
        L, want = heard_len(a8), bars_from(T, a8["s"], 8)
        off = a8["s"] - nearest(T["downbeats"], a8["s"])
        check(f"{name}: from the pick's 32 beats, 8 is inside the loop, on a bar within 10ms, and 8 of the song's beats long within 10ms",
              st["s"] - 1e-6 <= a8["s"] and a8["e"] <= st["e"] + 1e-6 and abs(off) <= 0.010 and want is not None and abs(L - want) <= 0.010,
              f"the pick {st['s']:.3f}-{st['e']:.3f}; 8: {a8['s']:.4f}-{a8['e']:.4f} ({off * 1000:+.1f}ms from a bar), heard {L:.4f}s against {want}")
        way = [f for f in after if abs(f[1] - st["s"]) > 1e-6 and abs(f[1] - a8["s"]) > 1e-6]
        check(f"{name}: it is still Skribl's pick, and the way back never shows on the way there; Undo is offered",
              a8["tag"] and not a8["back"] and a8["undo"] and len(way) >= 3 and all(f[2] and not f[3] for f in after),
              f"tag {a8['tag']}, the way back {a8['back']}, Undo {a8['undo']}; {len(way)} frames on the way, "
              f"{sum(1 for f in after if not f[2] or f[3])} of {len(after)} without the tag or with the way back")
        tap(q, "#musicPickUndo")
        u = q.evaluate(STATE)
        check(f"{name}: Undo brings back the pick's 32 beats and their beat",
              abs(u["s"] - st["s"]) < 1e-9 and abs(u["e"] - st["e"]) < 1e-9 and u["tempo"] == st["tempo"] and u["tag"] and not u["back"],
              f"{u['s']:.4f}-{u['e']:.4f}, tempo {u['tempo']} (the pick's {st['tempo']}), tag {u['tag']}")
        tap(q, 8)
        e8 = q.evaluate(STATE)
        tap(q, 16)
        a16 = q.evaluate(STATE)
        L16, want16 = heard_len(a16), bars_from(T, a16["s"], 16)
        check(f"{name}: longer, 16 from that 8 is around it and keeps its start, where it joins as well, 16 of the song's beats long within 10ms",
              abs(a16["s"] - e8["s"]) < 1e-9 and a16["e"] >= e8["e"] - 1e-6 and want16 is not None and abs(L16 - want16) <= 0.010 and a16["tag"],
              f"the 8 {e8['s']:.4f}-{e8['e']:.4f}; 16: {a16['s']:.4f}-{a16['e']:.4f}, heard {L16:.4f}s against {want16}, tag {a16['tag']}")
        tap(q, "#musicPickUndo")
        u8 = q.evaluate(STATE)
        check(f"{name}: and Undo of it brings back the 8, still Skribl's pick",
              abs(u8["s"] - e8["s"]) < 1e-9 and abs(u8["e"] - e8["e"]) < 1e-9 and u8["tag"] and not u8["back"],
              f"{u8['s']:.4f}-{u8['e']:.4f}, tag {u8['tag']}, the way back {u8['back']}")
        check(f"{name}: nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()

        c, q, errs = editor(b, path)
        st = add(q, "band")
        TB = SONGS["band"]["truth"]
        tap(q, 4)
        a4 = q.evaluate(STATE)
        tap(q, 32)
        a32 = q.evaluate(STATE)
        off = a4["s"] - nearest(TB["downbeats"], a4["s"])
        L, want = heard_len(a32), bars_from(TB, a32["s"], 32)
        check(f"{name}: a band speeding up, from its 4 beats (on a bar within 15ms), 32 keeps the start to the millisecond, 32 of its beats long within 15ms",
              "4 beats" in a4["line"] and abs(off) <= 0.015 and abs(a32["s"] - a4["s"]) < 0.0005 and want is not None and abs(L - want) <= 0.015,
              f"the 4 {a4['s']:.4f}-{a4['e']:.4f} ({off * 1000:+.1f}ms from a bar); 32: {a32['s']:.4f}-{a32['e']:.4f}, heard {L:.4f}s against {want}")
        c.close()

        c, q, errs = editor(b, path)
        st = add(q, "steady")
        p = 60 / st["tempo"]["bpm"]
        q.evaluate("(p) => { trimStart += p; trimEnd += p; updateTrimUI(); }", p)
        own = q.evaluate(STATE)
        tap(q, 8)
        a = q.evaluate(STATE)
        check(f"{name}: a loop of the person's own, its start a beat past the bar, keeps its start: 8 beats from it, theirs and not Skribl's pick",
              not own["tag"] and abs(a["s"] - own["s"]) < 1e-9 and abs(heard_len(a) - 8 * p) < 1e-6 and not a["tag"],
              f"their loop {own['s']:.4f}-{own['e']:.4f} (tag {own['tag']}); 8: {a['s']:.4f}-{a['e']:.4f}, heard {heard_len(a) / p:.3f} beats, tag {a['tag']}")
        c.close()

    print("\nKIND -- what a person does before Skribl has listened stays")
    for name, path in eds("kind"):
        # a loop moved
        c, q, errs = editor(b, path)
        q.evaluate(HOLD)
        before = add(q, "steady", wait=False)
        q.evaluate("() => { trimEnd = 12.5; updateTrimUI(); }")
        q.evaluate(RELEASE)
        q.wait_for_function(EARS_DONE, timeout=20000); waits.settle(q, 600)
        st = q.evaluate(STATE)
        check(f"{name}: a loop moved before Skribl has listened stays where it was put, and no beat is set",
              abs(st["s"] - before["s"]) < 1e-6 and abs(st["e"] - 12.5) < 1e-6 and st["tempo"] is None,
              f"loop {st['s']:.3f}-{st['e']:.3f}, tempo {st['tempo']}")
        # and the way back (Skribl's pick, in the Length door), then its Undo
        # (each offered only when it applies: a broken build that moved the
        # loop anyway offers neither, and says so here)
        length_door(q)
        offered = q.evaluate(STATE)["back"]
        if offered:
            q.click("#musicPickCard"); waits.settle(q, 600)
        back = q.evaluate(STATE)
        check(f"{name}: the way back goes to the heard pick, with the beat heard",
              offered and abs(back["s"] - T["drums"][0]) <= 0.010 and (back["tempo"] or {}).get("heard") is True,
              f"offered {offered}; loop {back['s']:.3f}-{back['e']:.3f}, tempo {back['tempo']}")
        offered = q.is_visible("#musicPickUndo")
        if offered:
            q.click("#musicPickUndo"); waits.settle(q, 600)
        und = q.evaluate(STATE)
        check(f"{name}: and its Undo brings back the loop and the beat that were there (none)",
              offered and abs(und["s"] - before["s"]) < 1e-6 and abs(und["e"] - 12.5) < 1e-6 and und["tempo"] is None,
              f"offered {offered}; loop {und['s']:.3f}-{und['e']:.3f}, tempo {und['tempo']}")
        c.close()
        # a beat tapped
        c, q, errs = editor(b, path)
        q.evaluate(HOLD)
        before = add(q, "steady", wait=False)
        q.evaluate("() => { musicTempo = { bpm: 120, phase: 0.25 }; updateTrimUI(); }")
        q.evaluate(RELEASE)
        q.wait_for_function(EARS_DONE, timeout=20000); waits.settle(q, 600)
        st = q.evaluate(STATE)
        check(f"{name}: a beat tapped before Skribl has listened stays, and so does the loop",
              st["tempo"] == {"bpm": 120, "phase": 0.25} and abs(st["s"] - before["s"]) < 1e-6 and abs(st["e"] - before["e"]) < 1e-6,
              f"tempo {st['tempo']}, loop {st['s']:.3f}-{st['e']:.3f}")
        c.close()

    print("\nKEPT -- the heard beat comes back with the song, and is not listened for again")
    for name, path in eds("kept"):
        c, q, errs = editor(b, path, init=COUNT_INIT)
        add(q, "steady", wait=False)
        q.wait_for_function("() => (window.__listens || 0) >= 1", timeout=20000)
        q.evaluate(RELEASE)
        q.wait_for_function(EARS_DONE, timeout=20000); waits.settle(q, 600)
        st = q.evaluate(STATE)
        q.click('#musicDoors .dp-tile[data-dp="beat"]'); waits.settle(q, 500)
        if q.is_visible("#musicSnap"):
            q.click("#musicSnap"); waits.settle(q, 300)
        off = q.evaluate(STATE)
        if q.is_visible("#musicSnap"):
            q.click("#musicSnap"); waits.settle(q, 300)
        on = q.evaluate(STATE)
        check(f"{name}: Snap to the beat's switch keeps the beat heard, off and on",
              (off["tempo"] or {}).get("heard") is True and (off["tempo"] or {}).get("snap") is False
              and (on["tempo"] or {}).get("heard") is True and "snap" not in (on["tempo"] or {}),
              f"off {off['tempo']}, on {on['tempo']}")
        q.evaluate("() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()")
        q.wait_for_timeout(2500)
        q.reload()
        q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        waits.settle(q, 1500)
        mid = q.evaluate(STATE)
        asked = q.evaluate("() => window.__listens || 0")
        q.evaluate(RELEASE)
        try:
            q.wait_for_function("() => document.getElementById('musicPickCard').getAttribute('aria-pressed') === 'true'", timeout=15000)
        except Exception:
            pass
        waits.settle(q, 600)
        again = q.evaluate(STATE)
        check(f"{name}: after a reload the loop and the heard beat come back, still heard by Skribl",
              abs(again["s"] - st["s"]) < 1e-3 and abs(again["e"] - st["e"]) < 1e-3 and (again["tempo"] or {}).get("heard") is True
              and again["beat"] == "124 beats a minute, heard by Skribl\u00a0· tap to change it",
              f"loop {again['s']:.4f}-{again['e']:.4f}, tempo {again['tempo']}, beat {again['beat']!r}")
        check(f"{name}: the song brought back is heard again, once and quietly: its loop and beat stay as kept, and it is still Skribl's pick",
              asked == 1 and q.evaluate("() => window.__listens || 0") == 1 and again["tempo"] == st["tempo"]
              and abs(again["s"] - st["s"]) < 1e-9 and abs(again["e"] - st["e"]) < 1e-9 and again["tag"] and not again["back"],
              f"asked to listen {asked} times; loop {again['s']:.4f}-{again['e']:.4f}, tempo {again['tempo']}, tag {again['tag']}, the way back {again['back']}")
        check(f"{name}: while Skribl hears it again, Skribl's pick is not lit and the way back is not offered",
              asked == 1 and not mid["tag"] and not mid["back"], f"asked {asked}; while it listened: tag {mid['tag']}, the way back {mid['back']}")
        p = 60 / st["tempo"]["bpm"]
        browsing.pad_drawer(q, "music")
        q.evaluate("(p) => { trimStart += 4 * p; trimEnd += 4 * p; updateTrimUI(); }", p)
        moved = q.evaluate(STATE)
        went = tap(q, "#musicPickCard")
        k = q.evaluate(STATE)
        check(f"{name}: and moved a bar, the way back goes to the heard pick, not to the song's first 20 seconds",
              moved["back"] and went and abs(k["s"] - st["s"]) < 1e-6 and abs(k["e"] - st["e"]) < 1e-6 and k["tag"],
              f"moved to {moved['s']:.4f} (the way back {moved['back']}, tapped {went}); Back: {k['s']:.4f}-{k['e']:.4f}, the pick {st['s']:.4f}-{st['e']:.4f}")
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
