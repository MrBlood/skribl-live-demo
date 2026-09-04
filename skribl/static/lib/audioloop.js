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

  global.SkriblAudioLoop = {
    buildLoopChannels: buildLoopChannels,
    buildLoopAudioBuffer: buildLoopAudioBuffer,
    audioBufferToWavDataURL: audioBufferToWavDataURL,
    encodeWavFromChannels: encodeWavFromChannels,
    loopChannels: loopChannels,
    buildTrimmedLoopWav: buildTrimmedLoopWav
  };
})(typeof window !== 'undefined' ? window : this);
