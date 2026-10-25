/* SKRIBL'S EARS: where a song's beat falls, which beat starts a bar, and
 * which stretch of whole bars comes round most smoothly. Step 3 of the music
 * plan ("the part that loops best, on the beat"), mocked from the real drawer
 * with songs to hear, and picked by the owner: "all yes".
 *
 *   listen(buffer, done)  reads the song's first two minutes a few
 *                         milliseconds at a time, so the page never stalls,
 *                         then calls done(heard); returns { cancel }.
 *   hear(samples, rate)   the same at once, for a channel already in hand.
 *   pick(heard, o)        Skribl's pick, with ears, or null:
 *                         o = { duration, target, maxLoop, minLoop, fadeMs }
 *                         -> { start, end, beats, bpm, phase, heard, join }
 *   steady(heard)         a beat was heard (pick can then still be null:
 *                         no whole bars fit the song or the loop's limits)
 *
 * HOW IT HEARS. A spectral flux, how much new sound each step of about 12ms
 * brings, and its low part (the kick, as sound grows, not as heard, so a
 * snare's wide noise does not pass for one); per step, twelve bands (what is
 * playing) and twelve pitch classes (which chord). The tempo is the flux's
 * strongest repeat between 40 and 240 beats a minute, leaning to 120 (people
 * tap most music between 80 and 160), then refined over the song to the
 * thousandth: 32 beats a beat-a-minute off are 130ms off by the time a loop
 * comes round. A beat heard slower than 85 with a sound starting halfway
 * between most of its beats is twice as fast, the count nearer 120: the flux
 * hears a kick least, and a rock beat at 120, its kicks between its snares,
 * was heard at 60. Where the beat falls is where the flux gathers, read round
 * the beat's circle; the flux peaks about 10ms before a sound is heard to
 * start (its window reaches it early), measured on clicks, and put back. A
 * bar is four beats; the beat that starts one is where the kicks and the
 * chord changes gather.
 *
 * NO STEADY BEAT, NO BEAT. A pad, a voice, a steady tone or a sweep has none,
 * and then Skribl says so and picks as it did before it had ears. Two things
 * must both hold: the flux gathers round the beat's circle (`sure`, its peak
 * against its mean: songs with drums measured 5.7 to 15.9, click tracks 23
 * to 32, slow chords about 2, against 3.5), and most beats in the played part
 * have a sound starting on them, a drum's or a kick's (`hits`): a steady
 * tone's one start, or a sweep's even drift, gathers round any circle and
 * lands on no beats.
 *
 * THE PICK. Of 4, 8, 16 and 32 beats (the owner: "we only ever want
 * 4,8,16,..."), the count nearest the length wanted that fits; starting on a
 * bar; where the song after the loop's end would go on as it goes on after
 * its start, or came to its start as it comes to the end (the same chord,
 * the same things playing, as loud); of joins as good, the earliest (the
 * owner's pick: usually where the beat comes in). An intro or a fade joins
 * badly with the music either side of it, so the join keeps them out: a
 * rule against quiet stretches as well was tried, never changed a test
 * song's pick, and would have skipped a soft verse; it went. A band that speeds up has a beat of its own in each
 * stretch, so each stretch is heard again on its own. Then the loop's length
 * is its end laid over its start, to the half millisecond, so the restart
 * lands where the next bar would; the beat given back is that length's own.
 * (Moving the start onto its own sound as well was tried, and measured: 3ms
 * better on one test song, 4ms worse on another, under a smooth restart's
 * 250ms either way. It went.)
 *
 * Measured against songs whose every beat is known (verify_musicears): the
 * start within a few milliseconds of the bar, the length within a few of
 * whole bars. Editor-only, like the drawer that uses it. */
(function (global) {
  'use strict';

  var N = 1024, HOP = 256, EDGE_HZ = 150;
  var MAX_SECONDS = 120;          // the song's first two minutes are heard
  var SLICE_MS = 8;               // listen() holds the page no longer than this at a time
  var LAG = -0.22;                // the flux's peak before the heard start, in windows (clicks)
  var SURE = 3.5, HITS = 0.5, MIN_HITS = 8;
  var WIDE = 64;                  // of 511 bins growing at once: a beat (drums, a pluck) is a burst
  var COUNTS = [4, 8, 16, 32];
  var TIE = 0.03;                 // joins this close are as good: the earlier wins

  function makeFFT(n) {
    var bits = Math.round(Math.log(n) / Math.LN2), rev = new Uint32Array(n), i, b;
    for (i = 0; i < n; i++) { var r = 0; for (b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
    var cs = new Float64Array(n / 2), sn = new Float64Array(n / 2);
    for (i = 0; i < n / 2; i++) { cs[i] = Math.cos(2 * Math.PI * i / n); sn[i] = -Math.sin(2 * Math.PI * i / n); }
    return function (re, im) {
      var i, j, t;
      for (i = 0; i < n; i++) { j = rev[i]; if (j > i) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
      for (var size = 2; size <= n; size <<= 1) {
        var half = size >> 1, step = n / size;
        for (var s0 = 0; s0 < n; s0 += size) {
          for (var k = 0; k < half; k++) {
            var wr = cs[k * step], wi = sn[k * step], a = s0 + k, c = a + half;
            var xr = re[c] * wr - im[c] * wi, xi = re[c] * wi + im[c] * wr;
            re[c] = re[a] - xr; im[c] = im[a] - xi; re[a] += xr; im[a] += xi;
          }
        }
      }
    };
  }

  // One channel, the first two minutes, at 22.05 kHz whatever the device
  // decodes at (each step the mean of the samples it spans): the beat lives
  // well below, and a song is heard the same at 44.1 kHz as at 48.
  function mono(channels, rate) {
    var r = Math.max(1, rate / 22050), len = Math.min(channels[0].length, Math.round(MAX_SECONDS * rate));
    var y = new Float32Array(Math.floor(len / r)), nc = channels.length;
    for (var i = 0; i < y.length; i++) {
      var a = i * r, b = a + r, j0 = Math.floor(a), j1 = Math.min(len, Math.ceil(b)), s = 0;
      for (var c = 0; c < nc; c++) {
        var ch = channels[c];
        for (var j = j0; j < j1; j++) s += (Math.min(j + 1, b) - Math.max(j, a)) * ch[j];
      }
      y[i] = s / (r * nc);
    }
    return { x: y, rate: r > 1 ? 22050 : rate };
  }

  // The steps, a slice at a time: step(budgetMs) returns true when all are read.
  function framer(x, rate) {
    var fft = makeFFT(N), win = new Float64Array(N), i, k;
    for (i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N);
    var nF = Math.floor(x.length / HOP) + 1, bins = N / 2;
    var F = { n: nF, hop: HOP / rate, lag: LAG * N / rate, flux: new Float32Array(nF), low: new Float32Array(nF), rms: new Float32Array(nF),
              wide: new Uint16Array(nF), bands: new Float32Array(nF * 12), chroma: new Float32Array(nF * 12) };
    var lowBin = Math.max(1, Math.round(EDGE_HZ * N / rate));
    var bandOf = new Int8Array(bins), pcOf = new Int8Array(bins);
    for (k = 0; k < bins; k++) {
      var f = k * rate / N;
      bandOf[k] = f < 40 ? -1 : Math.min(11, Math.floor(12 * Math.log(f / 40) / Math.log(8000 / 40)));
      pcOf[k] = f < 65 || f > 2100 ? -1 : ((Math.round(12 * Math.log(f / 261.6256) / Math.LN2) % 12) + 12) % 12;
    }
    var re = new Float64Array(N), im = new Float64Array(N), prev = new Float64Array(bins), cur = new Float64Array(bins);
    var lin = new Float64Array(lowBin + 1), n = 0;
    F.step = function (budget) {
      var t0 = Date.now();
      while (n < nF) {
        var c0 = n * HOP - N / 2, e = 0, j;
        for (j = 0; j < N; j++) { var v = x[c0 + j] || 0; re[j] = v * win[j]; im[j] = 0; e += v * v; }
        F.rms[n] = Math.sqrt(e / N);
        fft(re, im);
        var fl = 0, lw = 0, wd = 0;
        for (k = 1; k < bins; k++) {
          var m = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
          cur[k] = Math.log(1 + 10 * m);
          var d = cur[k] - prev[k];
          if (d > 0) { fl += d; if (d > 0.3) wd++; }
          if (k <= lowBin) { if (m > lin[k]) lw += m - lin[k]; lin[k] = m; }
          if (bandOf[k] >= 0) F.bands[n * 12 + bandOf[k]] += m * m;
          if (pcOf[k] >= 0) F.chroma[n * 12 + pcOf[k]] += m;
        }
        for (k = 0; k < 12; k++) F.bands[n * 12 + k] = Math.log(1e-6 + F.bands[n * 12 + k]);
        F.flux[n] = fl; F.low[n] = lw; F.wide[n] = wd;
        var t = prev; prev = cur; cur = t;
        n++;
        if (budget && (n & 15) === 0 && Date.now() - t0 >= budget) break;
      }
      return n >= nF;
    };
    return F;
  }

  // The flux less its own running level (a loud stretch is not a beat), as
  // it is (`raw`, for hits) and against its mean (`o`, for the circles). The
  // song's first and last 0.3s are left out, and no one sound weighs more
  // than the loudest few in a hundred: a steady tone is one sound starting,
  // and that one start gathered round any circle there is.
  function onsets(fl, hop) {
    var w = Math.round(0.25 / hop), edge = Math.round(0.3 / hop), n = fl.length, i;
    var raw = new Float32Array(n), o = new Float32Array(n), c = new Float64Array(n + 1);
    for (i = 0; i < n; i++) c[i + 1] = c[i] + fl[i];
    for (i = edge; i < n - edge; i++) {
      var a = Math.max(0, i - w), b = Math.min(n, i + w + 1);
      raw[i] = Math.max(0, fl[i] - (c[b] - c[a]) / (b - a));
    }
    var pos = [];
    for (i = 0; i < n; i++) if (raw[i] > 0) pos.push(raw[i]);
    pos.sort(function (x, y) { return x - y; });
    var cap = pos.length ? pos[Math.min(pos.length - 1, Math.floor(pos.length * 0.98))] : 0, s = 0;
    for (i = 0; i < n; i++) { o[i] = Math.min(raw[i], cap); s += o[i]; }
    var mean = s / n;
    if (mean > 0) for (i = 0; i < n; i++) o[i] /= mean;
    return { raw: raw, o: o };
  }

  // How the onsets gather round the beat's circle at `bpm`: the circle in 96
  // parts, smoothed; its peak against its mean, and where the peak is.
  function circle(o, hop, bpm) {
    var P = 60 / bpm / hop, H = new Float64Array(96), tot = 0, n, i;
    for (n = 0; n < o.length; n++) {
      if (!o[n]) continue;
      var ph = n / P; ph -= Math.floor(ph);
      var x = ph * 96, i0 = Math.floor(x) % 96, fr = x - Math.floor(x);
      H[i0] += o[n] * (1 - fr); H[(i0 + 1) % 96] += o[n] * fr; tot += o[n];
    }
    var best = 0, at = 0, S = new Float64Array(96);
    for (i = 0; i < 96; i++) {
      S[i] = 0.25 * H[(i + 95) % 96] + 0.5 * H[i] + 0.25 * H[(i + 1) % 96];
      if (S[i] > best) { best = S[i]; at = i; }
    }
    var l = S[(at + 95) % 96], r = S[(at + 1) % 96], den = l - 2 * best + r;
    var off = den < 0 ? 0.5 * (l - r) / den : 0;
    return { peak: tot ? best / (tot / 96) : 0, phase: ((at + off) / 96 + 1) % 1 * P * hop };
  }
  // The best circle near `bpm` (within `spread` of it), coarse to fine.
  function refine(o, hop, bpm, spread) {
    var top = { peak: -1 }, q, c, steps = [[bpm * (1 - spread), bpm * (1 + spread), 0.1], [0, 0, 0.01], [0, 0, 0.001]];
    for (var s = 0; s < steps.length; s++) {
      var lo = s ? top.bpm - steps[s - 1][2] : steps[0][0], hi = s ? top.bpm + steps[s - 1][2] : steps[0][1];
      for (q = lo; q <= hi + 1e-9; q += steps[s][2]) { c = circle(o, hop, q); if (c.peak > top.peak) top = { bpm: q, peak: c.peak, phase: c.phase }; }
    }
    return top;
  }

  function tempoOf(o, hop) {
    var lo = Math.floor(60 / 240 / hop), hi = Math.ceil(60 / 40 / hop), ac = [], best = -1, bl = lo, l, n;
    for (l = lo; l <= hi; l++) {
      var s = 0;
      for (n = 0; n + l < o.length; n++) s += o[n] * o[n + l];
      s /= Math.max(1, o.length - l);
      var w = Math.exp(-0.5 * Math.pow(Math.log(60 / (l * hop) / 120) / Math.LN2 / 0.9, 2));
      ac.push(s);
      if (s * w > best) { best = s * w; bl = l; }
    }
    var i = bl - lo, a = ac[i - 1], b = ac[i], c = ac[i + 1];
    var off = (a != null && c != null && a - 2 * b + c < 0) ? 0.5 * (a - c) / (a - 2 * b + c) : 0;
    return whole(o, hop, refine(o, hop, 60 / ((bl + off) * hop), 0.03));
  }
  // Most made music is a whole number of beats a minute: take it when it
  // holds the beat as well.
  function whole(o, hop, top) {
    var w = Math.round(top.bpm), cw = circle(o, hop, w);
    return Math.abs(w - top.bpm) < 0.06 && cw.peak >= top.peak * 0.99 ? { bpm: w, peak: cw.peak, phase: cw.phase } : top;
  }

  function unit(v) { var s = 0, i; for (i = 0; i < v.length; i++) s += v[i] * v[i]; s = Math.sqrt(s) || 1; for (i = 0; i < v.length; i++) v[i] /= s; return v; }
  function dot(a, b) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i] * b[i]; return s; }

  // Per beat from t0 to t1 on a grid { period, phase }: what plays (bands,
  // against the song's own), which chord, and the kick at it.
  function beatsOn(H, g, t0, t1) {
    var F = H.F, hop = H.hop, p = g.period, out = [], k, n;
    var t = g.phase + Math.ceil((t0 - g.phase) / p - 1e-9) * p;
    for (; t + p <= t1 + 1e-6; t += p) {
      var a = Math.max(0, Math.round(t / hop)), b = Math.min(F.n, Math.round((t + p) / hop));
      var bands = new Float64Array(12), ch = new Float64Array(12);
      for (n = a; n < b; n++) for (k = 0; k < 12; k++) { bands[k] += F.bands[n * 12 + k]; ch[k] += F.chroma[n * 12 + k]; }
      var cnt = Math.max(1, b - a);
      for (k = 0; k < 12; k++) bands[k] = (bands[k] / cnt - H.mu[k]) / H.sd[k];
      var kick = 0;
      for (n = Math.max(0, a - 2); n <= Math.min(F.n - 1, a + 2); n++) kick = Math.max(kick, F.low[n]);
      out.push({ t: t, z: bands, chroma: unit(ch), kick: kick });
    }
    return out;
  }
  function barOf(B) {
    var sc = [0, 0, 0, 0], cn = [0, 0, 0, 0], km = 0, j;
    for (j = 0; j < B.length; j++) km += B[j].kick / B.length;
    km = km || 1;
    for (j = 1; j < B.length; j++) { sc[j % 4] += B[j].kick / km + 4 * (1 - dot(B[j - 1].chroma, B[j].chroma)); cn[j % 4]++; }
    var bar = 0;
    for (j = 1; j < 4; j++) if (sc[j] / (cn[j] || 1) > sc[bar] / (cn[bar] || 1)) bar = j;
    return bar;
  }

  // Peaks of x, strongest first; the middle of the strongest k of them.
  function peaksOf(x) {
    var v = [];
    for (var n = 1; n < x.length - 1; n++) if (x[n] > 0 && x[n] >= x[n - 1] && x[n] >= x[n + 1]) v.push(x[n]);
    return v.sort(function (a, b) { return b - a; });
  }
  function midTop(v, k) { var top = v.slice(0, Math.max(1, k)); return top[Math.floor(top.length / 2)] || 0; }

  // The steps of the beats in the played part, or of the points `at` of the
  // way from each to the next.
  function played(H, at) {
    var F = H.F, out = [];
    for (var t = H.phase + H.lag; t + at * H.period < H.duration; t += H.period) {
      var c = Math.round(t / H.hop);
      if (c >= 0 && c < F.n && F.rms[c] >= 0.25 * H.loud) out.push(Math.round((t + at * H.period) / H.hop));
    }
    return out;
  }

  // A sound starting within 35ms of step c: a peak of the flux at least
  // `floor` and across the spectrum, or of the low part at least `kick`.
  function hitAt(H, c, floor, kick) {
    var raw = H.raw, low = H.low, F = H.F, reach = Math.ceil(0.035 / H.hop);
    for (var m = Math.max(1, c - reach); m <= Math.min(raw.length - 2, c + reach); m++) {
      if (raw[m] >= floor && raw[m] >= raw[m - 1] && raw[m] >= raw[m + 1]
          && Math.max(F.wide[m - 1], F.wide[m], F.wide[m + 1]) >= WIDE) return true;
      if (low[m] > 0 && low[m] >= kick && low[m] >= low[m - 1] && low[m] >= low[m + 1]) return true;
    }
    return false;
  }

  // Of the beats in the played part (or the points `at` of the way to the
  // next), how many have a sound starting on them: a peak of the flux within
  // 35ms, standing out of the flux around it, or a kick. Standing out means a
  // quarter as strong as the song's own strong starts (the middle of its
  // strongest, one for each beat), more than the flux's numerical dust, and
  // across the spectrum: at a beat of the test songs 100 to 490 bins grew at
  // once, as a sweep crossed from bin to bin 2 to 9, and slow chords at most
  // 33. A kick grows a few of the 511 bins and the flux hardly hears it, so a
  // kick is the low part growing half as much as the song's own strong kicks
  // do (the middle of its strongest, one for each bar), and twenty times the
  // song's loudness at least: the test songs' strong kicks grew 670 to 1300
  // times it, songs with no bass under 35.
  function hitsOf(H, at) {
    var beats = played(H, 0), n = beats.length, pts = at ? played(H, at) : beats;
    var floor = Math.max(1, 0.25 * midTop(H.peaks, n)), kick = Math.max(20 * H.loud, 0.5 * midTop(H.lowPeaks, Math.floor(n / 4)));
    return { hits: pts.filter(function (c) { return hitAt(H, c, floor, kick); }).length, beats: pts.length };
  }

  // The beat T = { bpm, peak, phase } on H: its period, where it falls, how
  // sure, and its hits.
  function beat(H, T) {
    var p = 60 / T.bpm, hb;
    H.bpm = T.bpm; H.period = p; H.phase = ((T.phase - H.lag) % p + p) % p; H.sure = T.peak;
    hb = hitsOf(H, 0); H.hits = hb.hits; H.beatsPlayed = hb.beats;
  }

  function finish(F, duration) {
    var hop = F.hop, k, n, on = onsets(F.flux, hop), low = onsets(F.low, hop).raw, T = tempoOf(on.o, hop);
    var mu = new Float64Array(12), sd = new Float64Array(12);
    for (n = 0; n < F.n; n++) for (k = 0; k < 12; k++) mu[k] += F.bands[n * 12 + k] / F.n;
    for (n = 0; n < F.n; n++) for (k = 0; k < 12; k++) sd[k] += Math.pow(F.bands[n * 12 + k] - mu[k], 2) / F.n;
    for (k = 0; k < 12; k++) sd[k] = Math.sqrt(sd[k]) || 1;
    var loud = Array.prototype.slice.call(F.rms).sort(function (a, b) { return a - b; });
    var H = { F: F, o: on.o, raw: on.raw, low: low, peaks: peaksOf(on.raw), lowPeaks: peaksOf(low), hop: hop, lag: F.lag,
              mu: mu, sd: sd, duration: Math.min(duration, F.n * hop), loud: loud[Math.floor(loud.length * 0.9)] || 0 };
    beat(H, T);
    // A beat heard slower than 85 a minute, with a sound starting halfway
    // between most of its beats, is twice as fast: the count nearer 120, as
    // people tap. A rock beat at 120 was heard at 60, on its snares on 2 and
    // 4: its kicks between them, on 1 and 3, are what the flux hears least.
    // It must hold as steady there.
    if (H.bpm < 120 / Math.SQRT2 && steady(H)) {
      var hm = hitsOf(H, 0.5);
      if (hm.hits >= HITS * hm.beats) {
        var c2 = circle(H.o, hop, 2 * T.bpm);
        beat(H, whole(H.o, hop, { bpm: 2 * T.bpm, peak: c2.peak, phase: c2.phase }));
        if (!steady(H)) beat(H, T);
      }
    }
    return H;
  }

  function steady(H) {
    return !!H && H.sure >= SURE && H.hits >= MIN_HITS && H.hits >= HITS * H.beatsPlayed;
  }

  function hear(samples, rate) {
    var m = mono([samples], rate), F = framer(m.x, m.rate);
    F.step(0);
    return finish(F, samples.length / rate);
  }

  function listen(buffer, done) {
    var stopped = false, chans = [], c;
    for (c = 0; c < buffer.numberOfChannels; c++) chans.push(buffer.getChannelData(c));
    var began = Date.now(), m = mono(chans, buffer.sampleRate), F = framer(m.x, m.rate);
    function go() {
      if (stopped) return;
      if (!F.step(SLICE_MS)) { setTimeout(go, 0); return; }
      var H = finish(F, buffer.duration);
      H.ms = Date.now() - began;       // how long it listened, in all
      if (!stopped) done(H);
    }
    setTimeout(go, 0);
    return { cancel: function () { stopped = true; } };
  }

  // The beat between t0 and t1, heard there: the song's tempo, refined.
  function local(H, t0, t1) {
    var a = Math.max(0, Math.floor(t0 / H.hop)), b = Math.min(H.o.length, Math.ceil(t1 / H.hop));
    var top = refine(H.o.subarray(a, b), H.hop, H.bpm, 0.04), p = 60 / top.bpm, ph = a * H.hop + top.phase - H.lag;
    return { bpm: top.bpm, period: p, phase: ((ph % p) + p) % p, sure: top.peak };
  }

  function alike(B, i, j, n) {
    var s = 0;
    for (var q = 0; q < n; q++) {
      var a = B[i + q], b = B[j + q];
      if (!a || !b) return null;
      var d = 0;
      for (var k = 0; k < 12; k++) d += Math.pow(a.z[k] - b.z[k], 2);
      s += 0.5 * dot(a.chroma, b.chroma) + 0.5 * Math.exp(-d / 12 / 0.5);
    }
    return s / n;
  }
  // The onsets either side of the start and of `L` after it, laid over each other.
  function overlay(H, s, L) {
    var o = H.o, hop = H.hop, sum = 0;
    for (var x = -0.6; x <= 0.6; x += hop) {
      var a = (s + x) / hop, b = (s + L + x) / hop, ia = Math.floor(a), ib = Math.floor(b);
      if (ia < 0 || ib + 1 >= o.length) continue;
      sum += (o[ia] + (a - ia) * (o[ia + 1] - o[ia])) * (o[ib] + (b - ib) * (o[ib + 1] - o[ib]));
    }
    return sum;
  }
  function pick(H, o) {
    if (!steady(H)) return null;
    var fade = Math.max(0, o.fadeMs || 0) / 1000, all = [], k = 0, d = Math.min(o.duration, H.duration);
    COUNTS.forEach(function (c) {
      var sel = c * H.period + fade;
      if (sel > o.maxLoop + 1e-6 || sel < o.minLoop || sel > d) return;
      if (!k || Math.abs(c * H.period - o.target) < Math.abs(k * H.period - o.target)) k = c;
    });
    if (!k) return null;
    var span = k * H.period + fade, W = Math.max(24, span + 8);
    for (var w0 = 0; w0 < d; w0 += 4) {
      var w1 = Math.min(d, w0 + W);
      if (w1 - w0 < span + 2) break;
      var g = local(H, w0, w1);
      if (!(g.sure >= SURE)) continue;
      var B = beatsOn(H, g, w0, w1), bar = barOf(B), p = g.period;
      for (var i = 0; i < B.length; i++) {
        if ((i - bar) % 4 !== 0) continue;
        var s = B[i].t;
        if (s + k * p + fade > d - 0.05 || i + k + 2 > B.length) break;
        var post = alike(B, i, i + k, 2), pre = i >= 2 ? alike(B, i - 2, i + k - 2, 2) : null;
        all.push({ start: s, beats: k, join: Math.max(post == null ? 0 : post, pre == null ? 0 : pre), bpm: g.bpm });
      }
    }
    if (!all.length) return null;
    var J = Math.max.apply(null, all.map(function (c) { return c.join; }));
    var best = all.filter(function (c) { return c.join >= J - TIE; }).sort(function (a, b) { return a.start - b.start; })[0];
    var start = Math.max(0, best.start);
    var L0 = 60 / best.bpm * best.beats, L = L0, top = -1;
    for (var dL = -0.03; dL <= 0.03 + 1e-9; dL += 0.0005) { var v = overlay(H, start, L0 + dL); if (v > top) { top = v; L = L0 + dL; } }
    var end = start + L + fade;
    if (end > d) return null;
    return { start: start, end: end, beats: best.beats, heard: L, bpm: 60 * best.beats / L, phase: start, join: best.join };
  }

  global.SkriblEars = { listen: listen, hear: hear, pick: pick, steady: steady, COUNTS: COUNTS, MAX_SECONDS: MAX_SECONDS };
}(typeof window !== 'undefined' ? window : globalThis));
