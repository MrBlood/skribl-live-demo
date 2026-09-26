/* Skribl shared audio-loop DSP — canonical copy (INTEGRATION step 3b).
   Extracted from the byte-identical copies that lived in app.js + flip.js.
   - buildLoopChannels(buffer, startFrame, frames, xfadeFrames): PURE
       equal-power crossfade fold -> { channels, frames }.
   - buildLoopAudioBuffer(state): reads audio state passed in as a plain object
       ({ currentAudioBuffer, audioCtx, trimStart, trimEnd, loopCrossfadeMs });
       writes nothing. Slices [trimStart,trimEnd] and folds the crossfade.
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

  function buildLoopAudioBuffer(state) {
    const currentAudioBuffer = state.currentAudioBuffer;
    const audioCtx = state.audioCtx;
    const trimStart = state.trimStart;
    const trimEnd = state.trimEnd;
    const loopCrossfadeMs = state.loopCrossfadeMs;
    if (!currentAudioBuffer || !audioCtx) return null;
    const sr = currentAudioBuffer.sampleRate;
    const ls = Math.max(0, trimStart || 0);
    const le = Math.min(currentAudioBuffer.duration, (trimEnd != null ? trimEnd : currentAudioBuffer.duration));
    if (le - ls < 0.05) return null;
    const startFrame = Math.floor(ls * sr);
    const endFrame = Math.min(currentAudioBuffer.length, Math.floor(le * sr));
    const frames = endFrame - startFrame;
    if (frames <= 0) return null;
    const numCh = currentAudioBuffer.numberOfChannels;
    const xfadeFrames = Math.min(Math.floor((loopCrossfadeMs / 1000) * sr), Math.floor(frames / 2));
    let channels, outLen;
    if (loopCrossfadeMs > 0 && xfadeFrames > 0) {
      const built = buildLoopChannels(currentAudioBuffer, startFrame, frames, xfadeFrames);
      channels = built.channels; outLen = built.frames;
    } else {
      outLen = frames;
      channels = [];
      for (let c = 0; c < numCh; c++) channels.push(currentAudioBuffer.getChannelData(c).subarray(startFrame, startFrame + frames));
    }
    const out = audioCtx.createBuffer(numCh, outLen, sr);
    for (let c = 0; c < numCh; c++) out.getChannelData(c).set(channels[c]);
    return out;
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
  function loopChannels(state) {
    const currentAudioBuffer = state.currentAudioBuffer;
    const trimStart = state.trimStart;
    const trimEnd = state.trimEnd;
    const loopCrossfadeMs = state.loopCrossfadeMs;
    if (!currentAudioBuffer) return null;
    const sr = currentAudioBuffer.sampleRate;
    const ls = Math.max(0, trimStart || 0);
    const le = Math.min(currentAudioBuffer.duration, (trimEnd != null ? trimEnd : currentAudioBuffer.duration));
    if (le - ls < 0.05) return null;
    const startFrame = Math.floor(ls * sr);
    const endFrame = Math.min(currentAudioBuffer.length, Math.floor(le * sr));
    const frames = endFrame - startFrame;
    if (frames <= 0) return null;
    // Crossfade can't exceed half the loop, or the fold would overlap itself.
    const xfadeFrames = Math.min(Math.floor((loopCrossfadeMs / 1000) * sr), Math.floor(frames / 2));
    if (loopCrossfadeMs > 0 && xfadeFrames > 0) {
      const built = buildLoopChannels(currentAudioBuffer, startFrame, frames, xfadeFrames);
      return { channels: built.channels, frames: built.frames, sampleRate: sr };
    }
    const channels = [];
    for (let c = 0; c < currentAudioBuffer.numberOfChannels; c++) {
      channels.push(currentAudioBuffer.getChannelData(c).subarray(startFrame, startFrame + frames));
    }
    return { channels: channels, frames: frames, sampleRate: sr };
  }

  function buildTrimmedLoopWav(state) {
    const lc = loopChannels(state);
    if (!lc) return null;
    return { dataUrl: encodeWavFromChannels(lc.channels, lc.sampleRate),
             duration: lc.frames / lc.sampleRate };
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
   *      rate: () => number (optional; 1 when absent) } */
  function engine(o) {
    var source = null, startCtx = 0, duration = 0, gen = 0, pendingUnlock = null;

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
      if (source) {
        try { source.stop(); } catch (e) {}
        try { source.disconnect(); } catch (e) {}
        source = null;
      }
    }

    function start(onFail) {
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
        src.connect(c.destination);
        try { src.start(); } catch (e) { return false; }
        source = src; startCtx = c.currentTime; duration = buf.duration;
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
    buildTrimmedLoopWav: buildTrimmedLoopWav
  };
})(typeof window !== 'undefined' ? window : this);
