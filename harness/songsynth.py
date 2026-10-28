"""Songs made in the page, so where every beat and every bar falls is known
exactly: drums, bass, chords, chord stabs and a plucked lead, a section at a
time, in four beats a bar or three, every beat's and every bar's time kept.
verify_musicears hears its songs with it, verify_musicthree its songs in
three. SYNTH(spec), evaluated in a page, returns
{ wav: base64, truth: { bpm, meter, beats, downbeats, drums }, seconds }.

  spec  { bpm, lead: seconds before the first beat, seed, meter: 4, or 3 for
          a song in three, sections: [{ bars, chords, pad, kit, lead }],
          swing, drift: how much faster by the end, jitter: seconds off the
          beat, as a band plays, sub: an 808's kick with no click, fade;
          and for a song with no beat: tone, sweep or scatter }
  kit   { kick, snare, hat, bass, stab }: each a level for every sixteenth
          of the bar, 16 of them in four and 12 in three

A song in four is made exactly as it was before songs in three: the same
samples, the same truth.
"""

SYNTH = r"""(spec) => {
  const SR = 22050; let s0 = spec.seed >>> 0;
  const r = () => { s0 = (s0 * 1664525 + 1013904223) >>> 0; return s0 / 4294967296; };
  const gauss = () => { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); };
  const hz = (pc, oct) => 440 * Math.pow(2, (pc - 9) / 12 + (oct - 4));
  const CH = { C: [0, [0, 4, 7]], G: [7, [0, 4, 7]], Am: [9, [0, 3, 7]], F: [5, [0, 4, 7]], Dm: [2, [0, 3, 7, 10]],
               G7: [7, [0, 4, 7, 10]], Cmaj7: [0, [0, 4, 7, 11]], Em: [4, [0, 3, 7]] };
  const M = spec.meter || 4;
  const bars = spec.sections.reduce((n, s) => n + s.bars, 0), N = bars * M, p0 = 60 / spec.bpm;
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
  const tones = (ch) => { const [root, ivs] = CH[ch]; return ivs.map((iv) => hz((root + iv) % 12, 4 + (root + iv >= 12 ? 1 : 0))); };
  const pad = (t, ch, dur, a) => { const fs = tones(ch);
    add(t, (x) => { let v = 0; for (const f of fs) v += Math.sin(2 * Math.PI * f * x + 0.002 * Math.sin(2 * Math.PI * 5 * x) * f) + 0.11 * Math.sin(6 * Math.PI * f * x);
      return a * 0.045 * v * Math.min(1, x / 0.25) * (x < dur ? 1 : Math.exp(-(x - dur) * 6)); }, dur + 0.6); };
  // A chord struck short: a waltz's two "pah"s after its "oom".
  const stab = (t, ch, a) => { const fs = tones(ch); add(t + jit() * 0.5, (x) => { let v = 0;
    for (const f of fs) v += Math.sin(2 * Math.PI * f * x) + 0.25 * Math.sin(4 * Math.PI * f * x);
    return a * 0.06 * v * Math.min(1, x * 300) * Math.exp(-x * 9); }, 0.4); };
  const pluck = (t, f, a) => add(t + jit() * 0.5, (x) => a * 0.09 * (Math.sin(2 * Math.PI * f * x) + 0.3 * Math.sin(4 * Math.PI * f * x)) * Math.exp(-x * 7) * Math.min(1, x * 400), 0.6);
  const truth = { bpm: spec.bpm, meter: M, beats: beats.slice(0, N), downbeats: [], drums: [] };
  let bar = 0;
  for (const sec of spec.sections) for (let j = 0; j < sec.bars; j++, bar++) {
    const b0 = bar * M, ch = sec.chords[j % sec.chords.length], k = sec.kit || {};
    truth.downbeats.push(at(b0));
    if (sec.pad) pad(at(b0), ch, at(b0 + M) - at(b0), sec.pad);
    for (let q = 0; q < 4 * M; q++) {
      const t = at(b0 + (q + (q % 2 && spec.swing ? spec.swing : 0)) / 4);
      if (k.kick && k.kick[q]) kick(t, k.kick[q]);
      if (k.snare && k.snare[q]) snare(t, k.snare[q]);
      if (k.hat && k.hat[q]) hat(t, k.hat[q]);
      if (k.bass && k.bass[q]) bass(t, hz(CH[ch][0], 2), (at(b0 + (q + 2) / 4) - t) * 0.9, k.bass[q]);
      if (k.stab && k.stab[q]) stab(t, ch, k.stab[q]);
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

# THE EARS' SONGS (verify_musicears), in four or with no beat at all: a
# steady song at 124, a swung one at 88, a band speeding up from 100 to 102,
# a rock beat at 120 with an 808's kick, slow chords, a steady tone, a sweep
# and rain.
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

# SONGS IN THREE: a bar of three beats, twelve sixteenths. A waltz's
# oom-pah-pah: the kick and the bass on one, a chord struck on two and three.
OOMPAH = {"kick": [X] + [0] * 11, "bass": [X] + [0] * 11,
          "stab": [0, 0, 0, 0, X, 0, 0, 0, X, 0, 0, 0], "hat": [0, 0, 0, 0, x, 0, 0, 0, x, 0, 0, 0]}
# A ballad in three: the kick on one, a brushed snare on three, a hat on each beat.
BALLAD3 = {"kick": [X] + [0] * 11, "snare": [0] * 8 + [x, 0, 0, 0], "hat": [x, 0, 0, 0] * 3,
           "bass": [X, 0, 0, 0, 0, 0, 0, 0, x, 0, 0, 0]}
# A band in three: the kick on one, a cross-stick on two and three, the ride on every beat.
BAND3 = {"kick": [X] + [0] * 11, "snare": [0, 0, 0, 0, x, 0, 0, 0, x, 0, 0, 0], "hat": [x, 0, 0, 0] * 3,
         "bass": [X] + [0] * 11}
# A piano's waltz, no drums: the bass on one, the chord on two and three.
PIANO3 = {"bass": [X] + [0] * 11, "stab": [0, 0, 0, 0, X, 0, 0, 0, X, 0, 0, 0]}
WALTZ_CHORDS = ["C", "C", "G7", "G7", "G7", "G7", "C", "C", "F", "F", "C", "C", "G7", "G7", "C", "C"]
THREES = {
    "waltz": {"bpm": 168, "lead": 0.35, "meter": 3, "fade": 2.5, "seed": 53, "sections": [
        {"bars": 2, "chords": ["C", "G7"], "pad": 1},
        {"bars": 32, "chords": WALTZ_CHORDS, "pad": 0.6, "kit": OOMPAH},
        {"bars": 16, "chords": WALTZ_CHORDS, "pad": 0.6, "kit": OOMPAH, "lead": 1},
        {"bars": 1, "chords": ["C"], "pad": 1}]},
    "ballad3": {"bpm": 92, "lead": 0.6, "meter": 3, "fade": 2.5, "seed": 61, "sections": [
        {"bars": 2, "chords": ["Am", "F"], "pad": 1},
        {"bars": 24, "chords": ["Am", "F", "C", "G", "Am", "Em", "F", "G"], "pad": 1, "kit": BALLAD3, "lead": 0.7}]},
    "band3": {"bpm": 132, "lead": 0.2, "meter": 3, "drift": 0.015, "jitter": 0.008, "fade": 2.5, "seed": 67, "sections": [
        {"bars": 1, "chords": ["Dm"], "kit": {"hat": [x, 0, 0, 0] * 3}},
        {"bars": 32, "chords": ["Dm", "Dm", "G7", "G7", "C", "C", "Am", "Am"], "pad": 0.8, "kit": BAND3}]},
    "piano3": {"bpm": 150, "lead": 0.3, "meter": 3, "fade": 2.5, "seed": 73, "sections": [
        {"bars": 32, "chords": WALTZ_CHORDS, "pad": 0.4, "kit": PIANO3, "lead": 0.6}]},
    # Two slow waltzes heard first at their eighths, where their bars gather
    # in sixes: one at 84 with its eighths played and no drums (heard at
    # 168), one at 76 with a kick on one and soft hats between (152).
    "slow3": {"bpm": 84, "lead": 0.4, "meter": 3, "fade": 2.5, "seed": 87, "sections": [
        {"bars": 32, "chords": ["F", "F", "C", "C", "G7", "G7", "C", "C"], "pad": 0.8,
         "kit": {"bass": [x] + [0] * 11, "stab": [0, 0, 0, 0, x, 0, 0, 0, x, 0, 0, 0]}, "lead": 0.8}]},
    "slow76": {"bpm": 76, "lead": 0.3, "meter": 3, "fade": 2.5, "seed": 167, "sections": [
        {"bars": 28, "chords": ["F", "F", "C", "C", "G7", "G7", "C", "C"], "pad": 0.8, "lead": 0.35,
         "kit": {"bass": [X] + [0] * 11, "stab": [0, 0, 0, 0, X, 0, 0, 0, X, 0, 0, 0], "hat": [x, 0, 0.25, 0] * 3, "kick": [X] + [0] * 11}}]},
}
# A piano in four, a waltz's own sounds two to a bar (the bass on one and
# three, the chord on two and four): it must still be heard in four.
PIANO4 = {"bpm": 112, "lead": 0.3, "fade": 2.5, "seed": 81, "sections": [
    {"bars": 24, "chords": ["C", "C", "Am", "Am", "F", "F", "G", "G"], "pad": 0.4, "lead": 0.5,
     "kit": {"bass": [X, 0, 0, 0, 0, 0, 0, 0, X, 0, 0, 0, 0, 0, 0, 0], "stab": [0, 0, 0, 0, X, 0, 0, 0, 0, 0, 0, 0, X, 0, 0, 0]}}]}
