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

  global.SkriblAudioLoop = {
    buildLoopChannels: buildLoopChannels,
    buildLoopAudioBuffer: buildLoopAudioBuffer
  };
})(typeof window !== 'undefined' ? window : this);
