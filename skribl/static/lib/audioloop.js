/* Skribl shared audio-loop DSP — canonical copy (INTEGRATION step 3b).
   Extracted from the byte-identical copies that lived in app.js + flip.js.
   - buildLoopChannels(buffer, startFrame, frames, xfadeFrames): PURE
       equal-power crossfade fold -> { channels, frames }.
   - buildLoopAudioBuffer(state): reads audio state passed in as a plain object
       ({ currentAudioBuffer, audioCtx, trimStart, trimEnd, loopCrossfadeMs, cut });
       writes nothing. Slices [trimStart,trimEnd] and folds the crossfade; with
       `cut` (Cut on silence) and no crossfade, both ends move together to
       where the loop joins without a click (cutSeconds says how far).
   Loaded as a classic script BEFORE app.js / flip.js; publishes
   window.SkriblAudioLoop. Each host file keeps a 1-line shim that passes its own
   module-level audio globals, so behavior is identical to the pre-extraction copies. */
(function (global) {
  'use strict';

  function buildLoopChannels(buffer, startFrame, frames, xfadeFrames) {
    const numCh = buffer.numberOfChannels;
    const outLen = frames - xfadeFrames;
    const channels = [];
    for (let c = 0; c < numCh; c++) {
      const src = buffer.getChannelData(c);
      const o = new Float32Array(outLen);
      for (let i = 0; i < outLen; i++) {
        let s = src[startFrame + i] || 0;
        if (i < xfadeFrames) {
          const t = i / xfadeFrames;                 // 0 -> 1
          const wIn = Math.sin(t * Math.PI / 2);     // head fades in
          const wOut = Math.cos(t * Math.PI / 2);    // tail fades out
          const tail = src[startFrame + i + outLen] || 0;  // = source[le - X + i]
          s = s * wIn + tail * wOut;
        }
        o[i] = s;
      }
      channels.push(o);
    }
    return { channels, frames: outLen };
  }

  // The same slice and fold as the posted clip (loopChannels, below), into
  // an AudioBuffer: one copy of the arithmetic, so what plays is what posts.
  function buildLoopAudioBuffer(state) {
    const audioCtx = state.audioCtx;
    if (!state.currentAudioBuffer || !audioCtx) return null;
    const lc = loopChannels(state);
    if (!lc) return null;
    const out = audioCtx.createBuffer(lc.channels.length, lc.frames, lc.sampleRate);
    for (let c = 0; c < lc.channels.length; c++) out.getChannelData(c).set(lc.channels[c]);
    return out;
  }

  /* CUT ON SILENCE (the music drawer's switch, under How it loops). A clean
   * cut clicks where the loop's last sample jumps to its first. With the cut
   * on, both ends move together, by the same number of frames and CUT_MS at
   * most either way, to where the loop's first samples come nearest the
   * song's own next ones after its last, over every channel. ONE MOVE FOR
   * BOTH ENDS keeps the loop's length, so Fit my drawing and whole bars stay
   * exact: moving each end to its own quiet moment, as the step 2 mock drew
   * it, changed the length by up to ten thousandths, and a loop that goes
   * round for minutes hears that as drift.
   * THE NEAREST CLEAN JOIN, NOT THE CLEANEST. A note comes round to the same
   * place every half of its period, so there are joins nearly as clean as
   * each other all through the reach; the cleanest by a hair was as often
   * the farthest (a 220Hz tone: 5ms off, when one 0.5ms off was within a
   * sixth of it). So of the moves within a quarter of the cleanest, the
   * smallest wins, and the loop goes no further than it has to.
   * With a smooth restart there is nothing to cut (the fold joins two samples
   * that were neighbours in the song), so the move is 0. */
  const CUT_MS = 5, NEAR = 1.25;
  function cutFrames(buffer, startFrame, frames) {
    const n = buffer.length, m = Math.round(CUT_MS / 1000 * buffer.sampleRate), chans = [];
    for (let c = 0; c < buffer.numberOfChannels; c++) chans.push(buffer.getChannelData(c));
    // Nearest first: 0, then 1 and -1, then 2 and -2, and so on.
    const tried = [];
    let least = Infinity;
    for (let k = 0; k <= m; k++) {
      for (let side = 0; side < (k ? 2 : 1); side++) {
        const d = side ? -k : k, s = startFrame + d, e = s + frames;
        if (s < 0 || e + 3 > n) continue;
        let cost = 0;
        for (let c = 0; c < chans.length; c++) {
          const x = chans[c];
          cost += Math.abs(x[s] - x[e]) + Math.abs(x[s + 1] - x[e + 1]) + Math.abs(x[s + 2] - x[e + 2]);
        }
        tried.push(d, cost);
        if (cost < least) least = cost;
      }
    }
    for (let i = 0; i < tried.length; i += 2) if (tried[i + 1] <= least * NEAR + 1e-12) return tried[i];
    return 0;
  }
  // The loop's window in frames, with the cut moved: { buffer, sr, startFrame,
  // frames, xfadeFrames }, or null when the buffer is not usable.
  function loopWindow(state) {
    const buffer = state.currentAudioBuffer;
    if (!buffer) return null;
    const sr = buffer.sampleRate;
    const ls = Math.max(0, state.trimStart || 0);
    const le = Math.min(buffer.duration, (state.trimEnd != null ? state.trimEnd : buffer.duration));
    if (le - ls < 0.05) return null;
    let startFrame = Math.floor(ls * sr);
    const endFrame = Math.min(buffer.length, Math.floor(le * sr));
    const frames = endFrame - startFrame;
    if (frames <= 0) return null;
    // Crossfade can't exceed half the loop, or the fold would overlap itself.
    const xfadeFrames = state.loopCrossfadeMs > 0 ? Math.min(Math.floor((state.loopCrossfadeMs / 1000) * sr), Math.floor(frames / 2)) : 0;
    if (state.cut && !(xfadeFrames > 0)) startFrame += cutFrames(buffer, startFrame, frames);
    return { buffer: buffer, sr: sr, startFrame: startFrame, frames: frames, xfadeFrames: xfadeFrames };
  }
  // How far Cut on silence moves both ends, in seconds (later is more), for
  // the words under its switch: 0 when it is off, with a smooth restart, or
  // when the ends already join.
  function cutSeconds(state) {
    const w = state && state.cut ? loopWindow(state) : null;
    if (!w || w.xfadeFrames > 0) return 0;
    return (w.startFrame - Math.floor(Math.max(0, state.trimStart || 0) * w.sr)) / w.sr;
  }

  // --- WAV encoders (pure) ---------------------------------------------------
  // Bodies lifted verbatim from app.js so the Pad's posted bytes are unchanged.

  function audioBufferToWavDataURL(buffer, startFrame, frames) {
    const numCh = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    startFrame = startFrame || 0;
    frames = frames != null ? frames : buffer.length - startFrame;
    const blockAlign = numCh * 2;              // 16-bit
    const dataSize = frames * blockAlign;
    const ab = new ArrayBuffer(44 + dataSize);
    const view = new DataView(ab);
    let p = 0;
    const wStr = (s) => { for (let i = 0; i < s.length; i++) view.setUint8(p++, s.charCodeAt(i)); };
    const wU32 = (v) => { view.setUint32(p, v, true); p += 4; };
    const wU16 = (v) => { view.setUint16(p, v, true); p += 2; };
    wStr('RIFF'); wU32(36 + dataSize); wStr('WAVE');
    wStr('fmt '); wU32(16); wU16(1); wU16(numCh);
    wU32(sampleRate); wU32(sampleRate * blockAlign); wU16(blockAlign); wU16(16);
    wStr('data'); wU32(dataSize);
    const chans = [];
    for (let c = 0; c < numCh; c++) chans.push(buffer.getChannelData(c));
    for (let i = 0; i < frames; i++) {
      const idx = startFrame + i;
      for (let c = 0; c < numCh; c++) {
        let s = Math.max(-1, Math.min(1, chans[c][idx] || 0));
        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(p, s, true); p += 2;
      }
    }
    // Base64-encode in chunks to avoid call-stack limits on large buffers.
    const bytes = new Uint8Array(ab);
    let binary = '';
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return 'data:audio/wav;base64,' + btoa(binary);
  }

  function encodeWavFromChannels(channels, sampleRate) {
    const numCh = channels.length;
    const frames = channels[0] ? channels[0].length : 0;
    const blockAlign = numCh * 2;
    const dataSize = frames * blockAlign;
    const ab = new ArrayBuffer(44 + dataSize);
    const view = new DataView(ab);
    let p = 0;
    const wStr = (s) => { for (let i = 0; i < s.length; i++) view.setUint8(p++, s.charCodeAt(i)); };
    const wU32 = (v) => { view.setUint32(p, v, true); p += 4; };
    const wU16 = (v) => { view.setUint16(p, v, true); p += 2; };
    wStr('RIFF'); wU32(36 + dataSize); wStr('WAVE');
    wStr('fmt '); wU32(16); wU16(1); wU16(numCh);
    wU32(sampleRate); wU32(sampleRate * blockAlign); wU16(blockAlign); wU16(16);
    wStr('data'); wU32(dataSize);
    for (let i = 0; i < frames; i++) {
      for (let c = 0; c < numCh; c++) {
        let s = Math.max(-1, Math.min(1, channels[c][i] || 0));
        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(p, s, true); p += 2;
      }
    }
    const bytes = new Uint8Array(ab);
    let binary = '';
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return 'data:audio/wav;base64,' + btoa(binary);
  }

  // Slice the decoded buffer to [trimStart, trimEnd] and return a small WAV data
  // URL + its duration, or null if the buffer isn't usable. Folds the crossfade
  // in when one is set (the clip is then shorter by the crossfade length), so
  // the posted clip IS the loop. Same state-object contract as
  // buildLoopAudioBuffer, minus audioCtx: no Web Audio context needed.
  // The slice-and-fold half of a loop bake, with no encoding opinion. Split out
  // of buildTrimmedLoopWav when buildPostedLoopWav (below) needed the SAME
  // window and the SAME crossfade fold but a different encode. Two copies of
  // this arithmetic is exactly how the two surfaces drifted apart before lib/
  // existed; there is one copy and both builders call it.
  // `state.cut`: Cut on silence (above), absent on the player, whose clip was
  // cut when it was posted.
  function loopChannels(state) {
    const w = loopWindow(state);
    if (!w) return null;
    if (w.xfadeFrames > 0) {
      const built = buildLoopChannels(w.buffer, w.startFrame, w.frames, w.xfadeFrames);
      return { channels: built.channels, frames: built.frames, sampleRate: w.sr };
    }
    const channels = [];
    for (let c = 0; c < w.buffer.numberOfChannels; c++) {
      channels.push(w.buffer.getChannelData(c).subarray(w.startFrame, w.startFrame + w.frames));
    }
    return { channels: channels, frames: w.frames, sampleRate: w.sr };
  }

  function buildTrimmedLoopWav(state) {
    const lc = loopChannels(state);
    if (!lc) return null;
    return { dataUrl: encodeWavFromChannels(lc.channels, lc.sampleRate),
             duration: lc.frames / lc.sampleRate };
  }

  /* NO CLICK WHERE THE SOUND STARTS OR STOPS (the owner: "All yes" to a
   * 5ms fade on Play, Stop and the sound switch). A sound begun or ended
   * mid-wave jumps from silence to the wave, or the wave to silence, in one
   * sample, and a jump is a click. So each of them glides over FADE_MS
   * instead: too short to hear as a fade, long enough that nothing jumps. The
   * loop's own join needs none of this: a smooth restart folds its end into
   * its start, and Cut on silence moves both ends to where they match.
   * glide: an AudioParam from where it is now to `to`. fadeIn: a source begun
   * from silence through a gain of its own, which it returns. fadeOut: that
   * source and gain to silence, the source stopped once there and both let go
   * once it has ended (a source and its gain are made together, always).
   * The link page uses these too; a post's box, which loads neither this
   * file nor app.js, carries the same block word for word (verify_soundfade
   * compares the two).
   * WHERE IT IS NOW is worked out from the last glide, not read: an
   * AudioParam's value lags the sound by up to a block (3ms), and a glide
   * begun from that mid-glide jumps. Nor cancelAndHoldAtTime: Chrome's hold
   * after a finished ramp starts the next ramp from that ramp's end, long ago,
   * so the new one is all but over before it begins, which is a jump too.
   * AND A MOMENT AHEAD (LEAD). The audio is made ahead of the page's clock,
   * a few blocks at a time (here the clock moves 384 to 512 samples at a
   * step), and a change scheduled for audio already made lands late, a glide
   * begun there part done: measured, a start came in at 58% of the level, 3ms
   * of its 5 gone, with the glide begun 10ms on. Most of all just after a
   * context wakes, which is every first Play: begun "now", 3 starts in 52
   * jumped the whole level (verify_soundfade asks 80). So each glide begins
   * 30ms on, and a source starts as its glide begins (fadeIn's gain says when,
   * g.at) and that much further into the clip, so it is where it would have
   * been: the music keeps its time with the drawing, to the sample. */
  var FADE_MS = 5, LEAD = 0.03;
  function at(p, t) {
    var g = p._glide;
    return !g ? p.value : t >= g.t1 ? g.v1 : g.v0 + (g.v1 - g.v0) * (t - g.t0) / (g.t1 - g.t0);
  }
  function glide(ctx, p, to, t) {
    if (t == null) t = ctx.currentTime + LEAD;
    var g = p._glide, end = t + FADE_MS / 1000, v = at(p, t);
    p.cancelScheduledValues(t);
    // One still under way is cut short at t, where it has got to: its ramp is
    // its end, so cancelling that would leave it flat until t, then a jump.
    if (g && t > g.t0 && t < g.t1) p.linearRampToValueAtTime(v, t); else p.setValueAtTime(v, t);
    p.linearRampToValueAtTime(to, end);
    p._glide = { v0: v, t0: t, v1: to, t1: end };
    return end;
  }
  function fadeIn(ctx, src, out, to) {
    var g = ctx.createGain();
    g.gain.value = 0; g.at = ctx.currentTime + LEAD;
    glide(ctx, g.gain, to == null ? 1 : to, g.at);
    src.connect(g); g.connect(out);
    return g;
  }
  function fadeOut(src, g) {
    var end = glide(src.context, g.gain, 0);
    src.onended = function () { src.disconnect(); g.disconnect(); };
    try { src.stop(end); } catch (e) { src.onended(); }
  }

  /* THE LIVE LOOP ENGINE: one for Pad, Flip and the player (SK312-003, v315).
   *
   * Plays the trimmed loop as an AudioBufferSourceNode with loop=true, on the
   * audio hardware clock, so the wrap is gapless and never drifts. It was
   * written out in app.js and flip.js, and each copy had a fix the other
   * lacked, which is the cost this exists to end:
   *
   *   - Pad kept the resume() promise captured INSIDE the click gesture
   *     (unlock), because its Play reaches start() from an Image.onload after
   *     the gesture has returned; iOS then reports 'suspended' and a fresh
   *     resume() out of the gesture never unlocks. Flip did not.
   *   - Flip's fail() stood down when a Stop had come in between; Pad's did not,
   *     so Play -> Stop -> an unlock that hung (iOS) or was refused handed off
   *     to native <audio> and STARTED THE MUSIC AFTER STOP. Reproduced on Pad
   *     before this file carried the engine; verify_audiosession pins it.
   *   - Pad matched a sped-up preview's rate; Flip had no rate.
   *
   * THE CONTRACT (v209/v210 reviews): no source is built until the context
   * reports 'running' -- a source begun on a suspended or closed context is
   * silence that reports success; a generation counter stops a late start
   * after stop(); and when the unlock rejects, never settles, or lands on a
   * context that still is not running, onFail fires ONCE so the caller can hand
   * off to native <audio>. start() returning true means "the Web Audio path was
   * taken and will either play or call onFail" -- never "sound".
   *
   * o: { ctx: () => AudioContext|null, build: () => AudioBuffer|null,
   *      rate: () => number (optional; 1 when absent) }
   *
   * start(onFail, offset): `offset` is seconds into the loop clip to begin
   * at, so an editor's paused preview carries its music on from where it
   * stopped (lib/tappause.js) instead of from the top. Absent or 0 is the top,
   * as every other caller has it. elapsed() counts from there. */
  function engine(o) {
    var source = null, fade = null, startCtx = 0, duration = 0, gen = 0, pendingUnlock = null;

    function unlock() {
      var ctx = o.ctx();
      if (!ctx || ctx.state !== 'suspended') return null;
      try { var p = ctx.resume(); return (pendingUnlock = (p && p.then) ? p : null); }
      catch (e) { console.warn('skribl: resume threw', e); return null; }
    }

    function stop() {
      // Generation FIRST (v209 review F1): a stop during an unlock must not be
      // overtaken by a late start, and a stale promise from an earlier Play
      // must not stand in for the next one's unlock.
      gen++;
      pendingUnlock = null;
      if (source) { fadeOut(source, fade); source = fade = null; }
    }

    function start(onFail, offset) {
      var ctx = o.ctx();
      if (!ctx) return false;
      var buf = o.build();
      if (!buf) return false;
      // Take the gesture-captured unlock BEFORE stop(), which clears it.
      var pending = pendingUnlock;
      stop();
      var mine = ++gen;
      function go() {
        var c = o.ctx();
        if (mine !== gen || !c || c.state !== 'running') return false;
        var src = c.createBufferSource();
        src.buffer = buf; src.loop = true; src.loopStart = 0; src.loopEnd = buf.duration;
        // A sped-up preview keeps the music in lockstep (it pitch-shifts,
        // which beats a take drifting out of sync). Preview only: the posted
        // clip and the export are untouched.
        try { src.playbackRate.value = o.rate ? o.rate() : 1; } catch (e) {}
        var g = fadeIn(c, src, c.destination);
        var off = (offset || 0) % buf.duration;
        try { src.start(g.at, (off + LEAD * src.playbackRate.value) % buf.duration); } catch (e) { g.disconnect(); return false; }
        source = src; fade = g; startCtx = g.at - LEAD - off; duration = buf.duration;
        return true;
      }
      function fail(why) {
        if (mine !== gen) return;        // a stop or a newer start came in: stand down
        gen++;                           // nothing from this attempt may start later
        if (onFail) { var f = onFail; onFail = null; console.warn('skribl: web audio unavailable — ' + why); f(); }
      }
      if (ctx.state === 'running') return go();
      // Suspended: prefer the promise captured in the gesture; with none,
      // resume here (still inside the gesture for a synchronous caller).
      // Consumed either way -- a promise that resolved for an earlier play
      // says nothing about a context iOS has since re-suspended.
      var p = pending || unlock();
      pendingUnlock = null;
      if (p && p.then) {
        var settled = false;
        p.then(function () { settled = true; if (!go()) fail('context not running after resume'); },
               function (e) { settled = true; fail('resume rejected: ' + ((e && e.message) || e)); });
        // iOS can leave resume() pending forever rather than rejecting.
        setTimeout(function () { if (!settled && !source) fail('resume never settled'); }, 600);
      } else if (p) {
        if (!go()) fail('synchronous resume did not reach running');
      } else {
        fail('no AudioContext resume available');
        return false;
      }
      return true;
    }

    return {
      start: start, stop: stop, unlock: unlock,
      playing: function () { return !!source; },
      source: function () { return source; },
      duration: function () { return duration; },
      // Seconds into the loop clip, by the audio clock; add trimStart for song time.
      elapsed: function () {
        var c = o.ctx();
        if (!c || duration <= 0) return 0;
        return (c.currentTime - startCtx) % duration;
      },
      // How long after the audio clock the sound reaches the ear: the
      // context's own processing and the device's (a phone's speaker, more
      // with Bluetooth). What a person taps to is the clock less this.
      latency: function () {
        var c = o.ctx();
        return c ? (c.baseLatency || 0) + (c.outputLatency || 0) : 0;
      }
    };
  }

  global.SkriblAudioLoop = {
    engine: engine,
    buildLoopChannels: buildLoopChannels,
    buildLoopAudioBuffer: buildLoopAudioBuffer,
    audioBufferToWavDataURL: audioBufferToWavDataURL,
    encodeWavFromChannels: encodeWavFromChannels,
    loopChannels: loopChannels,
    buildTrimmedLoopWav: buildTrimmedLoopWav,
    cutSeconds: cutSeconds,
    CUT_MS: CUT_MS,
    glide: glide, fadeIn: fadeIn, fadeOut: fadeOut,
    FADE_MS: FADE_MS, LEAD: LEAD
  };
})(typeof window !== 'undefined' ? window : this);
