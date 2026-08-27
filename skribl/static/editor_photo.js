// Editor-only: the photo drawer's wiring, plus the eraser cursor.
//
// Upload/drop handlers, the fit buttons, reposition, the opacity and blur
// sliders and their nudgers, and the eraser cursor's canvas listeners. Same rule
// as editor_music.js: only STATEMENTS move. The functions they call
// (initPhotoFitSlider, updateSliderFill, drawPhotoFitted and the rest) stay in
// app.js, because the player reaches some of them through loadSkribl and a
// binding declared here would not exist there at all.
//
// The eraser cursor's listeners are on .canvas-wrap, which the player DOES have
// — they are here because the player has no eraser, not because the element is
// missing.
//
// LOAD ORDER: classic script reading globals app.js declares. After app.js, and
// out of skribl_player.html.
canvasWrap.addEventListener('mousemove', (e) => {
  // The shape badge rides the same pointer tracking as the eraser ring: the
  // shape kind is chosen on the toolbar, so without this there is nothing at
  // the point of drawing saying what the next drag will make.
  if (tool === 'shape' && typeof shapeCursor !== 'undefined') {
    if (finishedRecording && !recording) { shapeCursor.style.display = 'none'; return; }
    const r = canvas.getBoundingClientRect();
    updateShapeCursor(e.clientX - r.left, e.clientY - r.top);
    shapeCursor.style.display = 'block';
    return;
  }
  if (tool !== 'eraser') return;
  if (finishedRecording && !recording) { eraserCursor.style.display = 'none'; return; }
  const rect = canvas.getBoundingClientRect();
  updateEraserCursor(e.clientX - rect.left, e.clientY - rect.top);
  eraserCursor.style.display = 'block';
});

canvasWrap.addEventListener('mouseleave', () => {
  eraserCursor.style.display = 'none';
  if (typeof shapeCursor !== 'undefined') shapeCursor.style.display = 'none';
});

canvasWrap.addEventListener('touchmove', (e) => {
  if (tool === 'shape' && typeof shapeCursor !== 'undefined') {
    if (finishedRecording && !recording) { shapeCursor.style.display = 'none'; return; }
    const r = canvas.getBoundingClientRect();
    const t0 = SkriblEventPoint.at(e);
    updateShapeCursor(t0.clientX - r.left, t0.clientY - r.top);
    shapeCursor.style.display = 'block';
    return;
  }
  if (tool !== 'eraser') return;
  if (finishedRecording && !recording) { eraserCursor.style.display = 'none'; return; }
  const rect = canvas.getBoundingClientRect();
  const touch = SkriblEventPoint.at(e);
  updateEraserCursor(touch.clientX - rect.left, touch.clientY - rect.top);
  eraserCursor.style.display = 'block';
}, { passive: true });

// touchcancel as well as touchend: a cancelled touch never fires touchend, so
// the eraser ring stayed painted on the canvas with no finger near it. Stale
// visual state rather than a stuck gesture, but the same lifecycle mistake —
// and the ring is what the user aims with.
function hideEraserCursor() {
  eraserCursor.style.display = 'none';
  // Same lifecycle rule for the shape badge: a cancelled touch never fires
  // touchend, and a badge left painted with no finger near it is the same stale
  // visual state the ring used to have.
  if (typeof shapeCursor !== 'undefined') shapeCursor.style.display = 'none';
}
canvasWrap.addEventListener('touchend', hideEraserCursor);
canvasWrap.addEventListener('touchcancel', hideEraserCursor);

photoUploadBtn.addEventListener('click', (e) => {
  if (e.target.closest('.dropzone-remove')) return;
  photoInput.click();
});

photoUploadBtn.addEventListener('dragover', (e) => {
  e.preventDefault();
  photoUploadBtn.classList.add('drag-over');
});

photoUploadBtn.addEventListener('dragleave', () => {
  photoUploadBtn.classList.remove('drag-over');
});

photoUploadBtn.addEventListener('drop', (e) => {
  e.preventDefault();
  photoUploadBtn.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (!file) return;
  if (!isImageFile(file)) {
    showToast('Please drop an image file — jpg, png, gif, or webp', photoUploadBtn);
    return;
  }
  // Reuse the existing photo input handler
  const dt = new DataTransfer();
  dt.items.add(file);
  photoInput.files = dt.files;
  photoInput.dispatchEvent(new Event('change'));
});

photoInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const seq = ++photoSelectionSeq;
  if (!file) return;
  if (!isImageFile(file)) {
    if (seq === photoSelectionSeq) showToast('Please choose an image file — jpg, png, gif, or webp', photoUploadBtn);
    photoInput.value = '';
    return;
  }
  const decodeErr = await skriblDecodeCheckImage(file);
  if (seq !== photoSelectionSeq) return;          // superseded or removed mid-decode
  if (decodeErr) { showToast(decodeErr, photoUploadBtn); photoInput.value = ''; return; }
  resetPhotoAdjustments();
  if (photoBgImg._objectUrl) URL.revokeObjectURL(photoBgImg._objectUrl);
  const url = URL.createObjectURL(file);
  photoBgImg._objectUrl = url;
  photoBgImg.src = url;
  // Keep a base64 copy so drafts can embed the photo
  const readToken = Symbol('photoRead');
  photoBgImg._readToken = readToken;
  const photoDraftReader = new FileReader();
  beginMediaRead();
  photoDraftReader.onload = () => {
    const original = photoDraftReader.result;
    // Downscale/recompress before storing so drafts + posts stay small. Keep the
    // media-read open until normalization settles, so a post fired mid-import
    // waits for the final bytes rather than grabbing the full-size original. The
    // readToken guard still applies — a fast remove/replace must never let a
    // stale photo's normalized result win. On any failure, fall back to the
    // original so the photo is never dropped.
    const attach = (data) => {
      if (photoBgImg._readToken === readToken && photoBgImg.style.display !== 'none') {
        photoBgImg._draftData = data;
      }
    };
    Promise.resolve(normalizePhotoDataURL(file, original))
      .then((finalData) => { attach(finalData); })
      .catch(() => { attach(original); })
      .finally(() => { endMediaRead(); });
  };
  photoDraftReader.onerror = () => { endMediaRead(); };
  photoDraftReader.onabort = () => { endMediaRead(); };
  photoDraftReader.readAsDataURL(file);
  photoBgImg.style.display = 'block';
  photoBgImg.style.objectFit = 'cover';
  photoBgImg.style.opacity = 1;
  photoOffsetX = 0.5; photoOffsetY = 0.5;
  photoZoom = 1; setZoomSliderUI();
  applyPhotoPosition();
  photoBg = photoBgImg;
  // canvas is always transparent
  canvasWrap.style.backgroundColor = bgColor;
  document.querySelector('#photoUploadBtn span').textContent = file.name;
  photoBgImg._fileName = file.name;
  document.getElementById('photoDetail').hidden = false;
  photoUploadBtn.classList.add('loaded');
  resetPhotoToggle();
  document.getElementById('photoTabDot').hidden = false;
  document.getElementById('photoRemove').hidden = false;
  setTimeout(initPhotoFitSlider, 50);
  updateRepositionUI();
});

bindEl('photoRemove', 'click', (e) => {
  // Review round 10, #1: this was missing, so a decode still running when the
  // user hit Remove would finish with a CURRENT token and re-apply the photo
  // that had just been removed. The old test incremented the counter by hand
  // instead of clicking this control, which hid the gap.
  photoSelectionSeq++;
  e.stopPropagation();
  if (typeof pendingPhotoMeta !== 'undefined') pendingPhotoMeta = null;
  { const c = document.getElementById('photoPending'); if (c) c.hidden = true; }
  photoBg = null;
  if (photoBgImg._objectUrl) { URL.revokeObjectURL(photoBgImg._objectUrl); photoBgImg._objectUrl = null; }
  photoBgImg.src = '';
  photoBgImg.style.display = 'none';
  canvasWrap.style.backgroundColor = bgColor;
  document.getElementById('photoDetail').hidden = true;
  photoInput.value = '';
  photoUploadBtn.classList.remove('loaded');
  document.querySelector('#photoUploadBtn span').textContent = 'Add a photo';
  document.getElementById('photoTabDot').hidden = true;
  document.getElementById('photoRemove').hidden = true;
  document.getElementById('photoOpacity').value = 100;
  document.getElementById('photoOpacityVal').textContent = '100%';
  photoOpacityVal_ = 1;
  photoBlur_ = 0;
  photoBgImg.style.filter = '';
  const blEl = document.getElementById('photoBlur');
  if (blEl) { blEl.value = 0; document.getElementById('photoBlurVal').textContent = '0px'; updateSliderFill(blEl); }
  updateSliderFill(document.getElementById('photoOpacity'));
  // Reset fit to Fill
  document.querySelectorAll('.photo-fit-btn').forEach(b => b.classList.toggle('active', b.dataset.fit === 'cover'));
  if (photoFitSlider) { photoFitSlider.style.width = '0'; photoFitSlider.style.transform = 'translateX(0)'; }
  photoOffsetX = 0.5; photoOffsetY = 0.5;
  photoZoom = 1; setZoomSliderUI();
  exitReposition();
  updateRepositionUI();
});

setTimeout(initPhotoFitSlider, 50);

document.querySelectorAll('.photo-fit-btn').forEach((btn, idx) => {
  btn.addEventListener('click', () => {
    photoFit = btn.dataset.fit;
    document.querySelectorAll('.photo-fit-btn').forEach(b => b.classList.toggle('active', b === btn));
    const fitMap = { cover: 'cover', contain: 'contain', stretch: 'fill' };
    photoBgImg.style.objectFit = fitMap[photoFit];
    applyPhotoPosition();
    updateRepositionUI();
    // Slide the slider
    const allBtns = [...document.querySelectorAll('.photo-fit-btn')];
    const offset = allBtns.slice(0, idx).reduce((sum, b) => sum + b.offsetWidth, 0);
    photoFitSlider.style.width = btn.offsetWidth + 'px';
    photoFitSlider.style.transform = `translateX(${offset}px)`;
  });
});

(function initReposition() {
  const btn = document.getElementById('repositionBtn');
  if (btn) btn.addEventListener('click', () => {
    if (repositioning) exitReposition(); else enterReposition();
  });
  const zoom = document.getElementById('photoZoom');
  if (zoom) zoom.addEventListener('input', () => {
    photoZoom = Math.max(1, Math.min(3, (parseInt(zoom.value, 10) || 100) / 100));
    const v = document.getElementById('photoZoomVal');
    if (v) v.textContent = Math.round(photoZoom * 100) + '%';
    if (typeof updateSliderFill === 'function') updateSliderFill(zoom);
    applyPhotoPosition();
    if (typeof scheduleAutosave === 'function') scheduleAutosave();
  });
  updateRepositionUI();
})();

photoOpacityEl.addEventListener('input', (e) => {
  photoOpacityVal_ = parseInt(e.target.value) / 100;
  document.getElementById('photoOpacityVal').textContent = e.target.value + '%';
  photoBgImg.style.opacity = photoOpacityVal_;
  updateSliderFill(e.target);
});

photoBlurEl.addEventListener('input', (e) => {
  photoBlur_ = parseInt(e.target.value, 10);
  photoBlurValEl.textContent = photoBlur_ + 'px';
  applyPhotoFilter();
  updateSliderFill(e.target);
});

updateSliderFill(photoOpacityEl);

updateSliderFill(photoBlurEl);

(function initSliderExtras() {
  // The stylesheet this used to build at runtime now lives in styles.css. It
  // was duplicated verbatim in flip.js, and being a JS string put it outside
  // every colour audit — which is how its +/- buttons stayed dark after light
  // mode shipped.

  // ---- (1) Nudgers on existing sliders ----
  ['photoOpacity', 'photoBlur', 'photoZoom', 'opacitySlider'].forEach(id => {
    const el = document.getElementById(id);
    if (el) addSliderNudgers(el, { step: parseFloat(el.step) || 1 });
  });

  // ---- (2) Loop Detail pan: scroll slider + waveform drag ----
  const zoomWrap = document.getElementById('zoomTrackWrap');
  if (zoomWrap) {
    const panRow = document.createElement('div');
    panRow.className = 'zoom-pan-row';
    panRow.innerHTML =
      '<span class="zoom-pan-label">Scroll</span>' +
      '<input type="range" id="zoomPanSlider" class="slider" min="0" max="1000" value="500" step="1" aria-label="Scroll the loop detail view">';
    zoomWrap.insertAdjacentElement('afterend', panRow);
    const panSlider = document.getElementById('zoomPanSlider');
    panSlider.addEventListener('input', () => {
      if (!Number.isFinite(audioDuration) || audioDuration <= 0) return;
      zoomCenter = (parseInt(panSlider.value, 10) / 1000) * audioDuration;
      zoomFocus = 'free';
      syncZoomFocusButtons();
      updateTrimUI();
    });
    addSliderNudgers(panSlider, {
      nudgeFn: (dir) => {
        if (!Number.isFinite(audioDuration) || audioDuration <= 0) return;
        const zw = getZoomWindow();
        const center = (zw.start + zw.end) / 2;
        const half = zw.duration / 2;
        const lo = half, hi = Math.max(half, audioDuration - half);
        zoomCenter = Math.max(lo, Math.min(center + dir * zw.duration * 0.1, hi));
        zoomFocus = 'free';
        syncZoomFocusButtons();
        updateTrimUI();
      }
    });
    dragZoomPan(zoomWrap);
  }

  // ---- (3) Crossfade control (bake-only; default Off) ----
  const finePanel = document.querySelector('.finetune-panel');
  const cfRow = document.createElement('div');
  cfRow.className = 'crossfade-row';
  cfRow.innerHTML =
    '<span class="crossfade-label">Crossfade</span>' +
    '<input type="range" id="crossfadeSlider" class="slider" min="0" max="500" value="0" step="5" aria-label="Loop crossfade length">' +
    '<span class="crossfade-val" id="crossfadeVal">Off</span>';
  if (finePanel) finePanel.insertAdjacentElement('afterend', cfRow);
  else {
    const preRow = document.querySelector('.loop-preview-row');
    if (preRow) preRow.parentNode.insertBefore(cfRow, preRow);
  }
  const cf = document.getElementById('crossfadeSlider');
  if (cf) {
    cf.addEventListener('input', () => {
      loopCrossfadeMs = parseInt(cf.value, 10) || 0;
      setCrossfadeUI();
      // Refresh the loop waveform so the amber crossfade bands track the slider.
      if (typeof updateTrimUI === 'function') updateTrimUI();
      if (typeof scheduleAutosave === 'function') scheduleAutosave();
    });
    addSliderNudgers(cf, { step: 5 });
    setCrossfadeUI();
  }
})();
