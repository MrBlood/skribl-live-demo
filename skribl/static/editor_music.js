// Editor-only: the music drawer's wiring.
//
// Upload/drop handlers, the trim-track drag installers, the zoom magnification
// and fine-tune controls, and the remove button — plus the four helpers only
// they call (dragHandle, dragZoomHandle, dragRangeWindow, validateMusicFile).
// Every call site of those four is in this file; nothing left in app.js names
// them. (A fifth, positionSegSlider, went with the one pill: lib/segslider.js
// places every pill and re-homes it when its drawer is revealed.)
//
// WHAT STAYED, and why. The drawer's STATE and the functions the PLAYER reaches
// through loadSkribl (clampTrim, drawWaveform, updateTrimUI, showToast and the
// rest) are still in app.js. A binding declared in an editor-only file does not
// exist on the player at all, so any player code touching it throws — state can
// never live here. This file only holds things nothing on the player names.
//
// Since the player template lost the music panel, these listeners were attaching
// to DETACHED stub elements on every shared link: work with no possible effect.
//
// And, at the foot, Preview Loop, Test Seam and Play's music loop, carved from
// app.js later with the same rule.
//
// LOAD ORDER: classic script reading globals app.js declares. Keep it after
// app.js, and out of skribl_player.html.
function dragZoomHandle(handle, isStart) {
  // The drag plumbing (mouse, touch, and the touchcancel a cancelled gesture
  // needs) is lib/dragtrack.js's, shared with Flip since v315.
  SkriblDragTrack.bind(handle, function (e) {
    e.preventDefault();
    handle.classList.add('dragging');
    return {
      move: function (clientX) {
        const rect = zoomTrackWrap.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        const zoom = getZoomWindow();
        const time = zoom.start + pct * (zoom.end - zoom.start);
        // Shared with Flip via lib/looptrim.js. 'slide': the zoom track pushes
        // the OTHER end to hold the cap, unlike the main track below.
        const _t = window.SkriblLoopTrim.setHandle(
          { start: trimStart, end: trimEnd, duration: audioDuration },
          isStart ? 'start' : 'end', time, 'slide');
        trimStart = _t.start; trimEnd = _t.end;
        updateTrimUI();
      },
      end: function () { handle.classList.remove('dragging'); }
    };
  });
}

dragZoomHandle(zoomHandleStart, true);

dragZoomHandle(zoomHandleEnd, false);

(function initZoomMagControl() {
  if (!zoomTrackWrap || !zoomTrackWrap.parentNode) return;
  const bar = document.createElement('div');
  bar.className = 'zoom-mag-bar';
  // The focus pill is a real .seg pill slider (same shell as the tune drawer's
  // Speed / Onion). The magnification half is NOT a .seg any more: v254 made it
  // a stepper, which is where the ladder above 8x and the one-line row both
  // came from. Its markup is lib/zoomstep.js's, not a literal here, because
  // this control used to exist as two literal strings -- one in this file and
  // one in flip.js -- that nothing forced to agree.
  bar.innerHTML = '<span class="seg zoom-seg" data-role="focus" role="group" aria-label="Loop view focus" title="What the loop view centres on"><button type="button" class="zoom-mag-btn on" data-focus="loop">Loop</button><button type="button" class="zoom-mag-btn" data-focus="start">Start</button><button type="button" class="zoom-mag-btn" data-focus="end">End</button></span>' + window.SkriblZoomStep.markup();
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-seg[data-role="focus"]'));
  bar.addEventListener('click', (e) => {
    const b = e.target.closest('.zoom-mag-btn');
    if (b) {
      // .on, not .active: these are .seg pill cells now, and the shared seg
      // slider positions its highlight from the .on button.
      b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      if (b.dataset.focus) { zoomFocus = b.dataset.focus; zoomCenter = null; }
      updateTrimUI();   // recomputes the window, redraws waveform + handles
      return;
    }
    const step = e.target.closest('.mag-step-btn');
    if (!step || step.disabled) return;
    const m = window.SkriblZoomStep.next(zoomMag, step.id === 'zoomMagIn' ? 1 : -1);
    if (m === zoomMag) return;
    zoomMag = m;
    window.SkriblZoomStep.sync(zoomMag);
    updateTrimUI();
  });
  window.SkriblZoomStep.sync(zoomMag);
  // the groups ARE .seg pills now (styles.css owns the shell + cells),
  // so the old injected rounded-rect styles are gone. Only the bar layout is
  // styled here, and it is styled in styles.css: Flip built the same sheet in
  // its own string and had already lost the 640px rule from it.
  //
  // WHAT v254 REPLACED. The magnification half was four labelled cells,
  // 1x/2x/4x/8x, costing 179px; with the 171.5px focus pill and the gap the row
  // needed 361px and split onto two lines on a phone. The stepper is 94px and
  // the bar is one line at 390 and 430. The ceiling went 8x -> 32x in the same
  // change, because six rungs cost a stepper nothing and 8x was too coarse to
  // show the panel's own finest nudge step -- see lib/zoomstep.js for that
  // arithmetic. Both surfaces now build this from the same function.
})();

(function initFineTuneMode() {
  // TRIM | FINE-TUNE, one pill (lib/segslider.js places it and writes
  // aria-pressed from the .on class). Fine-tune swaps the trim strip for the
  // loop detail IN PLACE -- it used to open below the fold behind a quiet row,
  // and a tap seemed to do nothing. Flip runs the same switch (flip.js).
  const seg = document.getElementById('fineTuneSeg');
  const body = document.getElementById('fineTuneBody');
  if (!seg || !body) return;
  seg.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const fine = b.id === 'fineTuneToggle';
    const apply = () => {
      seg.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
      body.hidden = !fine;
      seg.parentElement.classList.toggle('ft-on', fine);
    };
    // Back to Trim the drawer is ~290px shorter; scrolled near its end, the
    // page would clamp and leap under the finger (lib/drawerdetent.js).
    const D = window.SkriblDrawerDetent;
    if (!fine && D && D.shrinkGently) D.shrinkGently(seg.parentElement, apply); else apply();
    // Whichever canvas is now showing was laid out at zero size while hidden;
    // redraw it now that it has a box.
    requestAnimationFrame(() => {
      if (typeof updateTrimUI === 'function') updateTrimUI();
      if (!fine && typeof drawWaveform === 'function' && typeof currentAudioBuffer !== 'undefined'
          && currentAudioBuffer) drawWaveform(currentAudioBuffer);
      // The loop detail is taller than the strip it replaces: nudge the page
      // just far enough to show its waveform. NOT the drawer's whole end --
      // that scrolled far enough to tuck the dock under the pinned header
      // (verify_ux's phone audit), and the waveform is what says it worked.
      if (fine) {
        const z = document.getElementById('zoomTrackWrap');
        const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        const over = z ? z.getBoundingClientRect().bottom - vh + 12 : 0;
        if (over > 0) window.scrollBy({ top: over, behavior: 'smooth' });
      }
    });
  });
})();

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
// The switch's own handler (app.js) runs first and flips musicEnabled; this
// re-reads the row, which says "Muted" while the track is switched off.
bindEl('musicToggle', 'click', padMusicRow);

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
    musicTabDot.hidden = false;
    document.getElementById('musicRemove').hidden = false;
    updateTrimUI();
    padMusicRow();
    // "Just works" default: if a recording already exists, size the loop to the
    // drawing's length so the music and the replay finish together — no manual
    // trimming for the common case. Fine-tune stays one tap away. Reuses the
    // tested match-drawing logic (keeps start at 0, clamps to song + 20s cap).
    // Skipped while restoring saved trim from an autosave/draft, so a user's
    // chosen loop is never overwritten.
    const _restoringTrim = (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta);
    if (!_restoringTrim && strokes.length) {
      setLoopToDrawingLength();
      showToast('Loop set to your drawing length', musicUploadBtn);
    }
    // Reapply any pending trim from an autosave restore, from THIS path so it
    // can't race a separately-attached listener.
    if (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta) {
      applyPendingMusicSettings(pendingMusicMeta);
      pendingMusicMeta = null;
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

function validateMusicFile(file) {
  if (!file) return 'No file selected.';
  // Mirrors ALLOWED_AUDIO_SUBTYPES in app.py, so the editor refuses at selection
  // time what the server would refuse at post time. (Review round 5, #3)
  if (skriblHasUsableMime(file)) {
    if (!SKRIBL_AUDIO_MIMES.has(file.type.toLowerCase())) {
      return 'That file type is not supported for audio.';
    }
  } else if (!SKRIBL_AUDIO_EXTENSIONS.test(file.name || '')) {
    return 'Please choose an audio file (mp3, m4a, wav, flac, ogg, webm).';
  }
  return null;
}

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

function dragHandle(handle, isStart) {
  SkriblDragTrack.bind(handle, function (e) {
    e.preventDefault();
    handle.classList.add('dragging');
    return {
      move: function (clientX) {
        const rect = musicTrack.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        const time = pct * audioDuration;
        // 'constrain': the dragged handle stops at the cap; the other end stays.
        const _t = window.SkriblLoopTrim.setHandle(
          { start: trimStart, end: trimEnd, duration: audioDuration },
          isStart ? 'start' : 'end', time, 'constrain');
        trimStart = _t.start; trimEnd = _t.end;
        updateTrimUI();
      },
      end: function () { handle.classList.remove('dragging'); }
    };
  });
}

dragHandle(handleStart, true);

dragHandle(handleEnd, false);

function dragRangeWindow(rangeEl) {
  SkriblDragTrack.bind(rangeEl, function (e) {
    if (!audioEl || !Number.isFinite(audioDuration) || audioDuration <= 0) return null;
    if (rangeEl.classList.contains('narrow')) return null;
    e.preventDefault();
    e.stopPropagation();
    rangeEl.classList.add('dragging');
    const rect = musicTrack.getBoundingClientRect();
    const loopLength = trimEnd - trimStart;
    const grabTime = (SkriblEventPoint.at(e).clientX - rect.left) / rect.width * audioDuration;
    const grabOffset = grabTime - trimStart; // where inside the loop we grabbed
    return {
      move: function (clientX) {
        const time = (clientX - rect.left) / rect.width * audioDuration;
        const newStart = Math.max(0, Math.min(time - grabOffset, audioDuration - loopLength));
        trimStart = newStart;
        trimEnd = newStart + loopLength;
        updateTrimUI();
      },
      end: function () { rangeEl.classList.remove('dragging'); }
    };
  });
}

dragRangeWindow(musicRange);

// ---- Preview Loop, Test Seam and Play's music loop ------------------------
//
// CARVED FROM app.js, which every shared link downloads (owner: "1, carve
// it"). A shared link plays its music through its own loop bed (app.js,
// "Player audio") and never named any of this except stopLoopPreview, which
// loadSkribl reaches through clearCanvas and resetMediaForLoad, now behind a
// typeof guard. Moving it paid the debt the smart fade ran up on
// verify_jsstrip's 153,800 B target.
//
// WHAT STAYED: `previewingLoop`, the flag stopPlayback reads (state never
// lives here, above), and the Web Audio engine with its wrappers
// (startWebAudioLoop and the rest), which editor_draw.js calls too.
//
// A BINDING TRAVELS WITH ITS FUNCTION: the two buttons and their click
// listeners came along.
const previewLoopBtn = _authoringCtl('previewLoopBtn');
const testSeamBtn = _authoringCtl('testSeamBtn');
let previewLoopTimer = null;
let seamTimer = null;
let seamStopTimer = null;

function stopSeamTest() {
  if (seamTimer) clearInterval(seamTimer);
  if (seamStopTimer) clearTimeout(seamStopTimer);
  seamTimer = null;
  seamStopTimer = null;
}

// Audition the exact clip that will be posted — the built (optionally
// crossfaded) loop WAV, played on repeat — so Test Seam can prove the seam is
// smooth. Used only when a crossfade is set; the hard-cut case keeps the
// original source-seam behavior below. Auto-stops after a few loops.
let _builtLoopPreviewAudio = null;
let _builtLoopPreviewTimer = null;
function stopBuiltLoopPreview() {
  if (_builtLoopPreviewAudio) { try { _builtLoopPreviewAudio.pause(); } catch (e) {} _builtLoopPreviewAudio = null; }
  if (_builtLoopPreviewTimer) { clearTimeout(_builtLoopPreviewTimer); _builtLoopPreviewTimer = null; }
}
function playBuiltLoopPreview() {
  stopBuiltLoopPreview();
  const built = buildTrimmedLoopWav();
  if (!built) return false;
  const a = new Audio(built.dataUrl);
  a.loop = true;
  _builtLoopPreviewAudio = a;
  a.play().catch(() => {});
  const ms = Math.max(2000, built.duration * 1000 * 3);
  _builtLoopPreviewTimer = setTimeout(() => { if (_builtLoopPreviewAudio === a) stopBuiltLoopPreview(); }, ms);
  return true;
}

// Preview Loop plays the baked loop clip (below) via native loop=true, so it
// wraps sample-accurately with no timer-cut click. Its own element, stopped here.
let _previewLoopAudio = null;
function stopPreviewLoopAudio() {
  if (_previewLoopAudio) { try { _previewLoopAudio.pause(); } catch (e) {} _previewLoopAudio = null; }
}

function stopLoopPreview() {
  previewingLoop = false;
  // Guarded on `playing`, as Flip's is: Play's own music still needs it.
  if (!playing && window.SkriblAudioSession) window.SkriblAudioSession.release();
  if (audioEl) audioEl.pause();
  if (previewLoopTimer) clearInterval(previewLoopTimer);
  stopSeamTest();
  stopBuiltLoopPreview();
  stopPreviewLoopAudio();
  if (typeof stopWebAudioLoop === 'function') stopWebAudioLoop();
  previewLoopTimer = null;
  if (playhead) playhead.hidden = true;
  if (zoomPlayhead) zoomPlayhead.hidden = true;
  if (previewLoopBtn) previewLoopBtn.textContent = 'Preview Loop';
}

function startLoopPreview() {
  if (!audioEl) return;
  /* iOS silences Web Audio when the ringer switch is off; hold a playback
     session so this is audible. Gesture-scoped — see lib/audiosession.js. */
  if (window.SkriblAudioSession) window.SkriblAudioSession.claim();
  previewingLoop = true;
  previewLoopBtn.textContent = 'Stop Preview';
  try { audioEl.pause(); } catch (e) {}   // keep the raw source from playing underneath

  // Primary path: sample-accurate Web Audio loop of the exact posted clip.
  // Gapless + drift-free. Playhead reads the audio clock, mapped to song time.
  // The fallbacks below are reachable ASYNCHRONOUSLY too: on a device whose
  // AudioContext never reaches 'running', the Web Audio attempt fails after
  // this function has already returned, and the preview must still play.
  let previewHandedOff = false;
  const previewFallback = () => {
    if (previewHandedOff || !previewingLoop) return;
    previewHandedOff = true;
    if (previewLoopTimer) { clearInterval(previewLoopTimer); previewLoopTimer = null; }
    startLoopPreviewNative();
  };
  if (startWebAudioLoop(previewFallback)) {
    previewLoopTimer = setInterval(() => {
      if (!previewingLoop || !_waLoop.playing()) return;
      const songTime = webAudioLoopSongTime();
      const pct = (songTime / audioDuration) * 100;
      if (playhead) { playhead.hidden = false; playhead.style.left = pct + '%'; }
      if (zoomPlayhead && currentAudioBuffer) {
        const zw = getZoomWindow();
        const zoomPct = ((songTime - zw.start) / zw.duration) * 100;
        zoomPlayhead.hidden = false;
        zoomPlayhead.style.left = Math.max(0, Math.min(100, zoomPct)) + '%';
      }
    }, 30);
    return;
  }

  startLoopPreviewNative();
}

function startLoopPreviewNative() {
  if (!audioEl) return;
  // Fallback A: baked clip via native <audio> loop (if Web Audio unavailable).
  const built = (typeof buildTrimmedLoopWav === 'function') ? buildTrimmedLoopWav() : null;
  if (built) {
    stopPreviewLoopAudio();
    const a = new Audio(built.dataUrl);
    a.loop = true;
    _previewLoopAudio = a;
    a.play().catch(() => {});
    previewLoopTimer = setInterval(() => {
      if (!previewingLoop || !_previewLoopAudio) return;
      const songTime = (trimStart || 0) + _previewLoopAudio.currentTime;
      const pct = (songTime / audioDuration) * 100;
      if (playhead) { playhead.hidden = false; playhead.style.left = pct + '%'; }
      if (zoomPlayhead && currentAudioBuffer) {
        const zw = getZoomWindow();
        const zoomPct = ((songTime - zw.start) / zw.duration) * 100;
        zoomPlayhead.hidden = false;
        zoomPlayhead.style.left = Math.max(0, Math.min(100, zoomPct)) + '%';
      }
    }, 30);
    return;
  }

  // Fallback (decoded buffer not ready): original hand-wrapped source preview.
  audioEl.currentTime = trimStart;
  audioEl.play();
  previewLoopTimer = setInterval(() => {
    if (!previewingLoop || !audioEl) return;
    if (audioEl.currentTime >= trimEnd - 0.05) {
      audioEl.currentTime = trimStart;
      audioEl.play();
    }
    const pct = (audioEl.currentTime / audioDuration) * 100;
    if (playhead) {
      playhead.hidden = false;
      playhead.style.left = pct + '%';
    }
    // Zoom playhead — position within the zoom window
    if (zoomPlayhead && currentAudioBuffer) {
      const zw = getZoomWindow();
      const zoomPct = ((audioEl.currentTime - zw.start) / zw.duration) * 100;
      zoomPlayhead.hidden = false;
      zoomPlayhead.style.left = Math.max(0, Math.min(100, zoomPct)) + '%';
    }
  }, 50);
}

previewLoopBtn.addEventListener('click', () => {
  if (!audioEl) return;
  previewingLoop ? stopLoopPreview() : startLoopPreview();
});

testSeamBtn.addEventListener('click', () => {
  if (!audioEl) return;
  stopLoopPreview();
  // With a crossfade set, the raw source has no smoothed seam to hear — audition
  // the actual built (folded) clip on repeat instead. Hard-cut case falls
  // through to the original source-seam test below.
  if (loopCrossfadeMs > 0 && currentAudioBuffer) {
    if (playBuiltLoopPreview()) {
      showToast('Previewing crossfaded loop', testSeamBtn);
      return;
    }
  }
  const seamStart = Math.max(trimStart, trimEnd - 1.25);
  audioEl.currentTime = seamStart;
  audioEl.play();
  seamTimer = setInterval(() => {
    if (!audioEl) { stopSeamTest(); return; }
    const pct = (audioEl.currentTime / audioDuration) * 100;
    if (playhead) {
      playhead.hidden = false;
      playhead.style.left = pct + '%';
    }
    if (zoomPlayhead && currentAudioBuffer) {
      const zw = getZoomWindow();
      const zoomPct = ((audioEl.currentTime - zw.start) / zw.duration) * 100;
      zoomPlayhead.hidden = false;
      zoomPlayhead.style.left = Math.max(0, Math.min(100, zoomPct)) + '%';
    }
    if (audioEl.currentTime >= trimEnd - 0.05 && !seamStopTimer) {
      audioEl.currentTime = trimStart;
      seamStopTimer = setTimeout(() => {
        if (audioEl) audioEl.pause();
        if (playhead) playhead.hidden = true;
        if (zoomPlayhead) zoomPlayhead.hidden = true;
        stopSeamTest();
      }, 1250);
    }
  }, 30);
});

function playMusicLooped(drawingMs, onStarted) {
  if (!audioEl) {
    if (onStarted) onStarted();
    return;
  }
  if (playhead) playhead.hidden = false;

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
    playNativeLooped(drawingMs, onStarted);
  };
  if (startWebAudioLoop(nativeFallback)) {
    if (onStarted) onStarted();
    let elapsedWA = 0;
    const loopCheckWA = setInterval(() => {
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

function playNativeLooped(drawingMs, onStarted) {
  // Timer-wrapped <audio> loop. On iOS this is the path that actually plays:
  // the element's own gesture-driven play() has none of Web Audio's unlock
  // conditions, which is why Test Seam works on the owner's phone while the
  // Web Audio preview does not.
  if (!audioEl) { if (onStarted) onStarted(); return; }
  audioEl.currentTime = trimStart;

  const playPromise = audioEl.play();
  const begin = () => { if (onStarted) onStarted(); };

  if (playPromise && typeof playPromise.then === 'function') {
    playPromise.then(begin).catch(begin);
  } else {
    begin();
  }

  let elapsed = 0;
  const loopCheck = setInterval(() => {
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
