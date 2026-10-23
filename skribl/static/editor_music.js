// Editor-only: the Pad's half of the music drawer.
//
// THE DRAWER'S CONTROLS ARE lib/musicdrawer.js's, one copy shared with Flip
// (owner: "it needs to be the same music editor on both pad and flip"): the
// three levels, Skribl's pick, the loop detail's zoom and Scroll, the edges'
// drags, nudges and typed times, Smooth restart, Fit my drawing, Whole song,
// the hear buttons, Play with my drawing and the switch. The Pad hands it its
// own state through the hooks below. What is left here is the
// Pad's own: the file row (add and remove), the hooks, and Play's music loop,
// which follows the replay's speed.
//
// WHAT STAYED IN app.js, and why. The drawer's STATE and the functions the
// PLAYER reaches through loadSkribl (clampTrim, drawWaveform, updateTrimUI,
// showToast and the rest) are still in app.js. A binding declared in an
// editor-only file does not exist on the player at all, so any player code
// touching it throws — state can never live here. This file only holds things
// nothing on the player names.
//
// LOAD ORDER: classic script reading globals app.js declares. Keep it after
// app.js and lib/musicdrawer.js, and out of skribl_player.html.
let padDrawer = null;
if (window.SkriblMusicDrawer) padDrawer = window.SkriblMusicDrawer.wire({
  trim: () => ({ start: trimStart, end: trimEnd, duration: audioDuration }),
  setTrim: (start, end) => { trimStart = start; trimEnd = end; },
  view: () => ({ mag: zoomMag, focus: zoomFocus, center: zoomCenter }),
  setView: (v) => {
    if ('mag' in v) zoomMag = v.mag;
    if ('focus' in v) zoomFocus = v.focus;
    if ('center' in v) zoomCenter = v.center;
  },
  crossfade: () => loopCrossfadeMs,
  setCrossfade: (ms) => { loopCrossfadeMs = ms; },
  hasTrack: () => !!audioEl && Number.isFinite(audioDuration) && audioDuration > 0,
  refresh: updateTrimUI,
  strip: () => { if (currentAudioBuffer) drawWaveform(currentAudioBuffer); },
  zoomWindow: getZoomWindow,
  changed: () => { if (typeof scheduleAutosave === 'function') scheduleAutosave(); },
  // The replay's length at 1x, pauses as Pauses replays them.
  drawingSeconds: () => strokes.length ? getPlaybackDuration() / 1000 : 0,
  // A new song's loop is as long as the drawing already there, as it was.
  fitsByDefault: true,
  // One frame of the video the Pad exports (lib/mp4export.js).
  frameSeconds: () => 1 / ((window.SkriblMp4 && window.SkriblMp4.FPS) || 30),
  playButton: () => playBtn,
  audio: () => audioEl,
  buffer: () => currentAudioBuffer,
  loop: { start: startWebAudioLoop, stop: stopWebAudioLoop,
          playing: () => _waLoop.playing(), elapsed: () => _waLoop.elapsed() },
  clip: buildTrimmedLoopWav,
  playing: () => playing,
  setPreviewing: (on) => { previewingLoop = on; },
  enabled: () => musicEnabled,
  setEnabled: (on) => { musicEnabled = on; },
  musicOn: padMusicOn,
  musicOff: padMusicOff,
  // The row says "Muted" while the track is switched off.
  syncRow: () => { syncLayerToggle(document.getElementById('musicToggle'), musicEnabled); padMusicRow(); },
});
// app.js reaches these by name, typeof-guarded, because the player has no drawer.
function stopLoopPreview() { if (padDrawer) padDrawer.stopPreview(); }
function setCrossfadeUI() { if (padDrawer) padDrawer.syncCrossfade(); }
function syncMusicDrawer() { if (padDrawer) padDrawer.sync(); }
function resetMusicView() { if (padDrawer) padDrawer.resetView(); }

// The file row: the drop area until a track is added, then the track itself
// (lib/pendingcards.js renderRow writes its name and "Loops under the drawing
// · 0:08"). Called after every change this drawer makes to them, and by
// app.js's loadSkribl through a typeof guard, because the player loads app.js
// and has no drawer.
function padMusicRow() {
  if (!window.SkriblPendingCards || !window.SkriblPendingCards.renderRow) return;
  window.SkriblPendingCards.renderRow('music', {
    name: audioEl && audioEl._fileName, dur: audioDuration, on: musicEnabled
  });
}

// Drops are taken by the whole media card (lib/pendingcards.js bindDrops,
// wired in editor_bar.js), not by the row.
musicUploadBtn.addEventListener('click', (e) => {
  if (e.target.closest('.dropzone-remove')) return;
  if (!musicUploadBtn.classList.contains('loaded')) {
    musicInput.click();
  }
});
musicInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const seq = ++musicSelectionSeq;
  const err = validateMusicFile(file);
  if (err) { if (seq === musicSelectionSeq) showToast(err, musicUploadBtn); return; }
  // Bytes, not just the label. (Round 6, #7)
  const decodeErr = await skriblDecodeCheckAudio(file);
  if (seq !== musicSelectionSeq) return;          // superseded or removed mid-decode
  if (decodeErr) { showToast(decodeErr, musicUploadBtn); musicInput.value = ''; return; }
  if (audioEl && audioEl._objectUrl) URL.revokeObjectURL(audioEl._objectUrl);
  const url = URL.createObjectURL(file);
  audioEl = new Audio(url);
  audioEl._objectUrl = url;
  // Keep a base64 copy so drafts can embed the full song
  const thisAudio = audioEl;
  const draftReader = new FileReader();
  beginMediaRead();
  draftReader.onload = () => {
    try {
      // Only attach if this is still the same audio object (guards against a
      // fast remove/replace before the read finished).
      if (audioEl === thisAudio && thisAudio) thisAudio._draftData = draftReader.result;
    } finally {
      endMediaRead();
    }
  };
  draftReader.onerror = () => { endMediaRead(); };
  draftReader.onabort = () => { endMediaRead(); };
  draftReader.readAsDataURL(file);
  audioEl._fileName = file.name;
  audioEl.addEventListener('loadedmetadata', () => {
    audioDuration = audioEl.duration;
    trimStart = 0;
    trimEnd = Math.min(audioDuration, 20);
    musicDetail.hidden = false;
    musicUploadBtn.classList.add('loaded');
    resetMusicToggle();
    // A new song starts on its whole loop at 1x, as Flip's does: the last
    // track's zoom, focus and scroll belonged to a different song.
    resetMusicView();
    musicTabDot.hidden = false;
    document.getElementById('musicRemove').hidden = false;
    updateTrimUI();
    padMusicRow();
    // "Just works" default: Skribl's pick (lib/musicdrawer.js). With a
    // recording already there the loop is as long as the drawing, so the
    // music and the replay come round together, with a smooth restart; the
    // levels are one tap away. Skipped while restoring saved trim from an
    // autosave/draft, so a user's chosen loop is never overwritten.
    const _restoringTrim = (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta);
    const _pick = !_restoringTrim && padDrawer ? padDrawer.applyPick() : null;
    if (_pick && _pick.fits) showToast('Loop set to your drawing length', musicUploadBtn);
    // Reapply any pending trim from an autosave restore, from THIS path so it
    // can't race a separately-attached listener.
    if (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta) {
      const _meta = pendingMusicMeta;
      applyPendingMusicSettings(_meta);
      pendingMusicMeta = null;
      // The switch comes back as it was left: the autosave keeps it, as Flip's does.
      if (_meta.enabled === false) {
        musicEnabled = false;
        syncLayerToggle(document.getElementById('musicToggle'), false);
        padMusicRow();
      }
      const mCard = document.getElementById('musicPending');
      if (mCard) mCard.hidden = true;
      musicUploadBtn.hidden = false;
      // Same omission as the photo path above — the dot kept its amber
      // .pending class after the file was successfully re-added.
      refreshPendingCards();
    }
    if (typeof scheduleAutosave === 'function') scheduleAutosave();
  });

  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  // v211 (v210 review F2): the decode is RETAINED as a promise the poster
  // can await. mediaBusy is cleared by the FileReader's onload — a different
  // async chain from this one — so "media ready" and "decoded" were never the
  // same instant, and a post in the gap saw currentAudioBuffer === null and
  // silently skipped the loop crop, shipping the full source. Same
  // readiness/decode split as Bug A, on the write side.
  // THE SEQ CHECK HAS TO BE INSIDE THE DECODE, not only before it.
  // `seq` was captured at the top of this handler and checked twice above, but
  // both checks run BEFORE decodeAudioData is awaited — so they prove the
  // selection was current when the decode STARTED, which is not the question.
  // Select A, select B, let B finish first and A finish last, and A's
  // completion wrote its buffer over B's: reproduced with A=3.00s and B=9.00s
  // leaving currentAudioBuffer at 3.00s while audioDuration still read 9.00s.
  // A split state, not just a stale waveform — the poster crops from
  // currentAudioBuffer, so the track shown and the audio shipped were different
  // recordings.
  window._skriblDecodePending = file.arrayBuffer().then(buf => audioCtx.decodeAudioData(buf)).then(audioBuffer => {
    if (seq !== musicSelectionSeq) return;        // superseded while decoding
    currentAudioBuffer = audioBuffer;
    setTimeout(() => {
      if (seq !== musicSelectionSeq) return;      // and superseded before the paint
      drawWaveform(audioBuffer);
      drawZoomWaveform();
      updateZoomHandles();
    }, 50);
  }).catch(() => {}).finally(() => {
    // Only the CURRENT decode may clear the shared flag. An older completion
    // clearing it told shareSkribl "nothing is decoding" while the newer decode
    // was still in flight, which is the same readiness/decode split this flag
    // was added to close.
    if (seq === musicSelectionSeq) window._skriblDecodePending = null;
  });
});

// lib/media_validation.js's rule, which Flip asks too. It mirrors
// ALLOWED_AUDIO_SUBTYPES in app.py, so the editor refuses at selection time what
// the server would refuse at post time. (Review round 5, #3)
function validateMusicFile(file) { return window.SkriblMedia.validateAudioFile(file); }

musicRemove.addEventListener('click', (e) => {
  musicSelectionSeq++;   // a pending decode must not restore what was just removed
  e.stopPropagation();
  stopLoopPreview();
  if (typeof pendingMusicMeta !== 'undefined') pendingMusicMeta = null;
  { const c = document.getElementById('musicPending'); if (c) c.hidden = true; }
  if (audioEl) {
    audioEl.pause();
    if (audioEl._objectUrl) URL.revokeObjectURL(audioEl._objectUrl);
    audioEl = null;
  }
  musicDetail.hidden = true;
  musicInput.value = '';
  musicUploadBtn.classList.remove('loaded');
  padMusicRow();
  musicTabDot.hidden = true;
  document.getElementById('musicRemove').hidden = true;
  waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  zoomWaveformCtx.clearRect(0, 0, zoomWaveformCanvas.width, zoomWaveformCanvas.height);
  currentAudioBuffer = null;
  loopCrossfadeMs = 0; if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
  if (loopZoomLabel) loopZoomLabel.textContent = '0:00.00 → 0:00.00 [0.00s]';
});

// ---- Play's music loop ---------------------------------------------------
//
// CARVED FROM app.js, which every shared link downloads (owner: "1, carve
// it"). A shared link plays its music through its own loop bed (app.js,
// "Player audio") and never named any of this. Preview Loop and Test Seam,
// carved with it, are lib/musicdrawer.js's now. WHAT STAYED in app.js:
// `previewingLoop`, the flag stopPlayback reads, and the Web Audio engine
// with its wrappers (startWebAudioLoop and the rest), which editor_draw.js
// calls too.
//
// ONE TIMER: switched off and on again mid-Play, the music starts again, and
// the timer that ran it before is the one replaced.
let padPlayTimer = null;

// The switch turned on while the drawing plays: its music joins the drawing
// where it is, as Flip's comes back. Paused, it waits for the resume
// (editor_draw.js resumePlayback restarts the loop it was told of).
function padMusicOn() {
  if (!audioEl || !playing) return;
  if (playPaused) { if (currentAudioBuffer) pausedMusic = 'wa'; return; }
  playMusicLooped(playTotal, null, Math.min(playTotal, (performance.now() - playStart) * replayRate));
}
// ...and off, both engines and the playhead with them; the drawing plays on.
function padMusicOff() {
  if (padPlayTimer) { clearInterval(padPlayTimer); padPlayTimer = null; }
  stopWebAudioLoop();
  if (audioEl) audioEl.pause();
  if (playhead) playhead.hidden = true;
  if (playPaused) pausedMusic = null;
}

// fromMs: where in the drawing the music joins it (0, from the top).
function playMusicLooped(drawingMs, onStarted, fromMs) {
  if (!audioEl) {
    if (onStarted) onStarted();
    return;
  }
  if (playhead) playhead.hidden = false;
  const from = fromMs || 0;

  // Primary: sample-accurate Web Audio loop (gapless, drift-free) — the same
  // clip the post uses. The drawing replay (onStarted) starts immediately in
  // lockstep. The interval only drives the playhead + the total-time stop.
  // The native path is a FUNCTION now, not just the code below, because the
  // Web Audio attempt can fail asynchronously (an unlock that never reaches
  // 'running'). Called at most once, by whichever path gives up first.
  let handedOff = false;
  const nativeFallback = () => {
    if (handedOff) return;
    handedOff = true;
    playNativeLooped(drawingMs, onStarted, from);
  };
  // The loop runs at musicRate(): the drawing's time, over the drawing's rate
  // and times the music's, is where in the clip it has got to (resumePlayback).
  if (startWebAudioLoop(nativeFallback, from / replayRate * musicRate() / 1000)) {
    if (onStarted) onStarted();
    let elapsedWA = from;
    if (padPlayTimer) clearInterval(padPlayTimer);
    const loopCheckWA = padPlayTimer = setInterval(() => {
      if (!playing) { stopWebAudioLoop(); if (playhead) playhead.hidden = true; clearInterval(loopCheckWA); return; }
      if (playPaused) return;   // a pause is not music played
      elapsedWA += 100 * replayRate;
      const songTime = webAudioLoopSongTime();
      if (playhead) playhead.style.left = (songTime / audioDuration * 100) + '%';
      if (elapsedWA >= drawingMs) { stopWebAudioLoop(); if (playhead) playhead.hidden = true; clearInterval(loopCheckWA); }
    }, 100);
    return;
  }
  nativeFallback();
}

function playNativeLooped(drawingMs, onStarted, fromMs) {
  // Timer-wrapped <audio> loop. On iOS this is the path that actually plays:
  // the element's own gesture-driven play() has none of Web Audio's unlock
  // conditions, which is why Test Seam works on the owner's phone while the
  // Web Audio preview does not.
  if (!audioEl) { if (onStarted) onStarted(); return; }
  const from = fromMs || 0, len = trimEnd - trimStart;
  audioEl.currentTime = trimStart + (len > 0 ? (from / replayRate / 1000) % len : 0);

  const playPromise = audioEl.play();
  const begin = () => { if (onStarted) onStarted(); };

  if (playPromise && typeof playPromise.then === 'function') {
    playPromise.then(begin).catch(begin);
  } else {
    begin();
  }

  let elapsed = from;
  if (padPlayTimer) clearInterval(padPlayTimer);
  const loopCheck = padPlayTimer = setInterval(() => {
    if (!playing) {
      audioEl.pause();
      if (playhead) playhead.hidden = true;
      clearInterval(loopCheck);
      return;
    }
    if (playPaused) return;
    elapsed += 100 * replayRate;
    if (audioEl.currentTime >= trimEnd - 0.05) {
      audioEl.currentTime = trimStart;
      audioEl.play();
    }
    const pct = (audioEl.currentTime / audioDuration) * 100;
    if (playhead) {
      playhead.style.left = pct + '%';
    }
    if (elapsed >= drawingMs) {
      audioEl.pause();
      if (playhead) playhead.hidden = true;
      clearInterval(loopCheck);
    }
  }, 100);
}
