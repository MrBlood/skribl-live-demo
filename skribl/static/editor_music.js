// Editor-only: the music drawer's wiring.
//
// Upload/drop handlers, the trim-track drag installers, the zoom magnification
// and fine-tune controls, and the remove button — plus the five helpers only
// they call (dragHandle, dragZoomHandle, dragRangeWindow, positionSegSlider,
// validateMusicFile). Every call site of those five is in this file; nothing
// left in app.js names them.
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
// LOAD ORDER: classic script reading globals app.js declares. Keep it after
// app.js, and out of skribl_player.html.
function dragZoomHandle(handle, isStart) {
  if (!handle) return;   // trim track is editor-only
  function onStart(e) {
    e.preventDefault();
    handle.classList.add('dragging');

    function onMove(ev) {
      const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const rect = zoomTrackWrap.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const zoom = getZoomWindow();
      const time = zoom.start + pct * (zoom.end - zoom.start);

      // Shared with Flip via lib/looptrim.js. 'slide': the zoom track pushes
      // the OTHER end to hold the cap, unlike the main track below. The cap was
      // a bare 20 here and in seven other places in this file, with no constant.
      {
        const _t = window.SkriblLoopTrim.setHandle(
          { start: trimStart, end: trimEnd, duration: audioDuration },
          isStart ? 'start' : 'end', time, 'slide');
        trimStart = _t.start; trimEnd = _t.end;
      }
      updateTrimUI();
    }

    function onEnd() {
      handle.classList.remove('dragging');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onEnd);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
    }

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onEnd);
  }

  handle.addEventListener('mousedown', onStart);
  handle.addEventListener('touchstart', onStart, { passive: false });
}

dragZoomHandle(zoomHandleStart, true);

dragZoomHandle(zoomHandleEnd, false);

function positionSegSlider(group){ if(window.SkriblSegSlider) window.SkriblSegSlider.placeAttached(group); }

(function initZoomMagControl() {
  if (!zoomTrackWrap || !zoomTrackWrap.parentNode) return;
  const bar = document.createElement('div');
  bar.className = 'zoom-mag-bar';
  // v207: the two groups are real .seg pill sliders now (same shell as the
  // tune drawer's Speed / Onion), not the ad-hoc rounded-rect buttons they were.
  // A magnifier glyph labels the 1x-8x group so it reads as "zoom level".
  bar.innerHTML = '<span class="seg zoom-seg" data-role="focus" title="What the loop view centres on"><button type="button" class="zoom-mag-btn on" data-focus="loop">Loop</button><button type="button" class="zoom-mag-btn" data-focus="start">Start</button><button type="button" class="zoom-mag-btn" data-focus="end">End</button></span>' + '<span class="zoom-mag-wrap"><span class="zoom-mag-glyph"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg></span><span class="seg zoom-seg" data-role="mag" title="Zoom level"><button type="button" class="zoom-mag-btn on" data-mag="1">1&times;</button><button type="button" class="zoom-mag-btn" data-mag="2">2&times;</button><button type="button" class="zoom-mag-btn" data-mag="4">4&times;</button><button type="button" class="zoom-mag-btn" data-mag="8">8&times;</button></span></span>';
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-seg[data-role="focus"]'));
  attachSegSlider(bar.querySelector('.zoom-seg[data-role="mag"]'));
  bar.addEventListener('click', (e) => {
    const b = e.target.closest('.zoom-mag-btn');
    if (!b) return;
    // .on, not .active: these are .seg pill cells now, and the shared seg
    // slider positions its highlight from the .on button.
    b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    if (b.dataset.focus) { zoomFocus = b.dataset.focus; zoomCenter = null; }
    if (b.dataset.mag) zoomMag = parseFloat(b.dataset.mag) || 1;
    updateTrimUI();   // recomputes the window, redraws waveform + handles
  });
  // v207: the groups ARE .seg pills now (styles.css owns the shell + cells),
  // so the old injected rounded-rect styles are gone. Only the bar layout and
  // the magnifier glyph beside the zoom group are styled here.
  const style = document.createElement('style');
  style.textContent =
    '.zoom-mag-bar{display:flex;gap:10px;justify-content:space-between;align-items:center;margin:8px 0 6px;flex-wrap:wrap}' +
    '.zoom-mag-wrap{display:inline-flex;align-items:center;gap:8px}' +
    '.zoom-mag-glyph{display:inline-flex;color:var(--text-muted)}' +
    '.zoom-mag-glyph svg{width:16px;height:16px}' +
    // v210 (owner's iPhone): on phone the bar wraps to two rows, and the
    // 16px glyph + 8px gap pushed the 1x-8x segment 24px right of the
    // Loop/Start/End segment above it, so the two pills did not line up.
    // Give the focus segment the SAME 24px lead so both start on one line;
    // the glyph now reads as labelling the row rather than offsetting it.
    '@media (max-width:640px){.zoom-mag-bar{justify-content:flex-start;gap:8px 10px}' +
    '.zoom-seg[data-role="focus"]{margin-left:24px}}';
  document.head.appendChild(style);
})();

(function initFineTuneToggle() {
  const toggle = document.getElementById('fineTuneToggle');
  const body = document.getElementById('fineTuneBody');
  if (!toggle || !body) return;
  toggle.addEventListener('click', () => {
    const open = body.hidden;
    body.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      // First reveal: the zoom canvas and the two seg-pills were laid out at
      // zero size while hidden. Redraw and re-home them now that they have a box.
      requestAnimationFrame(() => {
        if (typeof updateTrimUI === 'function') updateTrimUI();
        if (typeof positionSegSlider === 'function') {
          body.querySelectorAll('.zoom-seg').forEach(g => positionSegSlider(g));
        }
      });
    }
  });
})();

musicUploadBtn.addEventListener('click', (e) => {
  if (e.target.closest('.dropzone-remove')) return;
  if (!musicUploadBtn.classList.contains('loaded')) {
    musicInput.click();
  }
});

musicUploadBtn.addEventListener('dragover', (e) => {
  e.preventDefault();
  if (!musicUploadBtn.classList.contains('loaded')) {
    musicUploadBtn.classList.add('drag-over');
  }
});

musicUploadBtn.addEventListener('dragleave', () => {
  musicUploadBtn.classList.remove('drag-over');
});

musicUploadBtn.addEventListener('drop', (e) => {
  e.preventDefault();
  musicUploadBtn.classList.remove('drag-over');
  if (musicUploadBtn.classList.contains('loaded')) return;
  const file = e.dataTransfer.files[0];
  const err = validateMusicFile(file);
  if (err) { showToast(err, musicUploadBtn); return; }
  const dt = new DataTransfer();
  dt.items.add(file);
  musicInput.files = dt.files;
  musicInput.dispatchEvent(new Event('change'));
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
    musicBtnLabel.textContent = file.name;
    resetMusicToggle();
    musicTabDot.hidden = false;
    document.getElementById('musicRemove').hidden = false;
    updateTrimUI();
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
  file.arrayBuffer().then(buf => audioCtx.decodeAudioData(buf)).then(audioBuffer => {
    currentAudioBuffer = audioBuffer;
    setTimeout(() => {
      drawWaveform(audioBuffer);
      drawZoomWaveform();
      updateZoomHandles();
    }, 50);
  }).catch(() => {});
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
  musicBtnLabel.textContent = 'Add music';
  musicTabDot.hidden = true;
  document.getElementById('musicRemove').hidden = true;
  waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  zoomWaveformCtx.clearRect(0, 0, zoomWaveformCanvas.width, zoomWaveformCanvas.height);
  currentAudioBuffer = null;
  loopCrossfadeMs = 0; if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
  if (loopZoomLabel) loopZoomLabel.textContent = '0:00.00 → 0:00.00 [0.00s]';
});

function dragHandle(handle, isStart) {
  if (!handle) return;   // trim track is editor-only
  function getClientX(e) {
    return e.touches ? e.touches[0].clientX : e.clientX;
  }

  function onStart(e) {
    e.preventDefault();
    handle.classList.add('dragging');
    function onMove(ev) {
      const rect = musicTrack.getBoundingClientRect();
      let pct = (getClientX(ev) - rect.left) / rect.width;
      pct = Math.max(0, Math.min(1, pct));
      const time = pct * audioDuration;
      // 'constrain': the dragged handle stops at the cap; the other end does
      // not move. Declared difference from the zoom track — see the module.
      {
        const _t = window.SkriblLoopTrim.setHandle(
          { start: trimStart, end: trimEnd, duration: audioDuration },
          isStart ? 'start' : 'end', time, 'constrain');
        trimStart = _t.start; trimEnd = _t.end;
      }
      updateTrimUI();
    }
    function onEnd() {
      handle.classList.remove('dragging');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onEnd);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onEnd);
  }

  handle.addEventListener('mousedown', onStart);
  handle.addEventListener('touchstart', onStart, { passive: false });
}

dragHandle(handleStart, true);

dragHandle(handleEnd, false);

function dragRangeWindow(rangeEl) {
  if (!rangeEl) return;   // trim track is editor-only
  function getClientX(e) {
    return e.touches ? e.touches[0].clientX : e.clientX;
  }
  function onStart(e) {
    if (!audioEl || !Number.isFinite(audioDuration) || audioDuration <= 0) return;
    if (rangeEl.classList.contains('narrow')) return;
    e.preventDefault();
    e.stopPropagation();
    rangeEl.classList.add('dragging');
    const rect = musicTrack.getBoundingClientRect();
    const loopLength = trimEnd - trimStart;
    const grabTime = (getClientX(e) - rect.left) / rect.width * audioDuration;
    const grabOffset = grabTime - trimStart; // where inside the loop we grabbed

    function onMove(ev) {
      const time = (getClientX(ev) - rect.left) / rect.width * audioDuration;
      let newStart = time - grabOffset;
      // Clamp so the whole window stays within the song, length unchanged.
      newStart = Math.max(0, Math.min(newStart, audioDuration - loopLength));
      trimStart = newStart;
      trimEnd = newStart + loopLength;
      updateTrimUI();
    }
    function onEnd() {
      rangeEl.classList.remove('dragging');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onEnd);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onEnd);
  }
  rangeEl.addEventListener('mousedown', onStart);
  rangeEl.addEventListener('touchstart', onStart, { passive: false });
}

dragRangeWindow(musicRange);
