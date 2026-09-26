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
// POINTERMOVE, not mousemove (v315): a stroke's pointerdown is prevented, which
// suppresses the compatibility mouse events -- so a mousemove ring stood still
// for the whole of a mouse erase. Touch keeps its own touchmove below.
canvasWrap.addEventListener('pointermove', (e) => {
  if (e.pointerType === 'touch') return;
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
  document.querySelectorAll('.photo-fit-btn').forEach(b => {
    /* aria-pressed alongside the class: the visual selection was the only
       selection, so a screen reader could operate these and never learn
       which was chosen. */
    const sel = b.dataset.fit === 'cover';
    b.classList.toggle('active', sel);
    b.setAttribute('aria-pressed', String(sel));
  });
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
    document.querySelectorAll('.photo-fit-btn').forEach(b => {
      const sel = b === btn;
      b.classList.toggle('active', sel);
      b.setAttribute('aria-pressed', String(sel));
    });
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

/* ---- CARVED OUT OF app.js -----------------------------------------
 *
 * Four functions whose every call site was already in this file or in
 * editor_draw.js, and which the player therefore cannot name -- but which the
 * player downloaded on every shared link anyway, because they sat in app.js.
 *
 * They are the photo drawer's own work: decoding and re-encoding an upload to
 * a canvas the editor can afford, resetting the adjustment sliders, and the
 * two drag gestures that move and zoom the backdrop. A person reading a
 * Skribl has no photo drawer.
 *
 * STATE STAYED, as this file's header requires and as every carve before it
 * did: a binding declared here does not exist on the player at all, so
 * anything the player touches has to remain in app.js. These are functions
 * that read app.js's globals, not owners of them.
 *
 * The prose above each one came with it. A comment is the decision record for
 * the code it sits on, and a carve that leaves the reasoning behind in the
 * file the code left is how a tree ends up with explanations for things that
 * are not there.
 */

// Decode → (optionally) downscale → re-encode. Opaque images re-encode as JPEG
// (the size win); images with any transparency re-encode as PNG so alpha is
// preserved. Returns a smaller data URL, or the original untouched if the
// re-encode isn't actually smaller or anything fails (so a photo is never lost).
// On-device only: createImageBitmap, the canvas encode/inspect, and EXIF
// orientation can't be exercised headless — this function is never called at load
// time (only from the import handler), so the harness only *defines* it.
async function normalizePhotoDataURL(file, originalDataUrl) {
  try {
    if (typeof createImageBitmap !== 'function' ||
        typeof document === 'undefined' || !document.createElement) {
      return originalDataUrl;   // no decode path available — keep the original
    }
    // imageOrientation:'from-image' bakes EXIF rotation into the pixels so the
    // stored image matches what the <img> preview shows; toDataURL then drops the
    // EXIF tag, so no downstream viewer double-rotates. Fall back to the no-option
    // form on engines that reject the options bag.
    let bmp;
    try {
      bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch (optErr) {
      bmp = await createImageBitmap(file);
    }
    const srcW = bmp.width, srcH = bmp.height;
    const t = photoTargetDims(srcW, srcH, PHOTO_MAX_EDGE);
    const cv = document.createElement('canvas');
    cv.width = t.w; cv.height = t.h;
    const c = cv.getContext('2d');
    if ('imageSmoothingQuality' in c) c.imageSmoothingQuality = 'high';
    c.drawImage(bmp, 0, 0, t.w, t.h);   // no bg fill — keep any transparency intact
    if (bmp.close) bmp.close();
    // A background photo can be a truly transparent PNG (sticker / line-art).
    // JPEG has no alpha, so flattening it here would freeze the transparent
    // regions to a single color and they'd stop tracking the live canvas
    // background — editor vs player, or a later bg change, then disagree. So keep
    // alpha as PNG and only re-encode opaque images as JPEG (where the size win
    // matters and there's no transparency to lose). JPEG inputs are always opaque,
    // so skip the pixel scan for them.
    let hasAlpha = false;
    if (file.type !== 'image/jpeg' && file.type !== 'image/jpg') {
      try {
        const px = c.getImageData(0, 0, t.w, t.h).data;
        for (let i = 3; i < px.length; i += 4) {
          if (px[i] !== 255) { hasAlpha = true; break; }
        }
      } catch (readErr) {
        hasAlpha = true;   // couldn't inspect — assume alpha, prefer lossless PNG
      }
    }
    // Prefer WebP when the browser can encode it: it keeps alpha (so transparent
    // images stay transparent instead of falling back to bulky lossless PNG) and
    // beats JPEG on opaque photos. When WebP isn't available, keep the original
    // behaviour exactly — PNG for alpha, JPEG for opaque. The alpha detect and the
    // "only keep it if smaller" guard below both still apply, so a see-through
    // background still tracks the live canvas colour and nothing ever gets larger.
    const webpOK = canEncodeWebP();
    let out, outFormat;
    if (hasAlpha) {
      if (webpOK) { out = cv.toDataURL('image/webp', PHOTO_WEBP_ALPHA_QUALITY); outFormat = 'webp-alpha'; }
      else        { out = cv.toDataURL('image/png');                            outFormat = 'png'; }
    } else {
      if (webpOK) { out = cv.toDataURL('image/webp', PHOTO_WEBP_QUALITY);       outFormat = 'webp'; }
      else        { out = cv.toDataURL('image/jpeg', PHOTO_JPEG_QUALITY);       outFormat = 'jpeg'; }
    }
    const smaller = !!(out && originalDataUrl && out.length < originalDataUrl.length);
    if (typeof window !== 'undefined' && window.__SKRIBL_PHOTO_DEBUG) {
      try {
        console.log('[photo] normalize', {
          srcW: srcW, srcH: srcH, outW: t.w, outH: t.h,
          format: outFormat,
          origBytes: originalDataUrl ? originalDataUrl.length : null,
          outBytes: out ? out.length : null,
          kept: smaller ? 'downscaled' : 'original'
        });
      } catch (logErr) { /* debug only */ }
    }
    return smaller ? out : originalDataUrl;
  } catch (e) {
    return originalDataUrl;   // any failure → keep the original, never lose it
  }
}

function resetPhotoAdjustments() {
  photoFit = 'cover';
  photoOpacityVal_ = 1;
  photoBlur_ = 0;
  photoOffsetX = 0.5; photoOffsetY = 0.5;
  photoZoom = 1; setZoomSliderUI();
  photoBgImg.style.objectFit = 'cover';
  photoBgImg.style.opacity = 1;
  photoBgImg.style.filter = '';
  applyPhotoPosition();
  const opEl = document.getElementById('photoOpacity');
  opEl.value = 100;
  _authoringCtl('photoOpacityVal').textContent = '100%';
  updateSliderFill(opEl);
  const blEl = document.getElementById('photoBlur');
  if (blEl) {
    blEl.value = 0;
    _authoringCtl('photoBlurVal').textContent = '0px';
    updateSliderFill(blEl);
  }
  document.querySelectorAll('.photo-fit-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.fit === 'cover');
  });
  initPhotoFitSlider();
  updateRepositionUI();
}

// Drag the background. Attaches window listeners for the duration of one drag
// (like the loop-trim handles) so the pointer can leave the canvas mid-drag.
function beginPhotoDrag(e) {
  const start = getPos(e);
  const startOX = photoOffsetX, startOY = photoOffsetY;
  // Use the authored logical size (matches getPos above and the export path's
  // drawPhotoFitted); getPos now returns authored px, so overflow must too.
  const { width: w, height: h } = getCanvasLogicalSize();
  const iw = photoBgImg.naturalWidth || w, ih = photoBgImg.naturalHeight || h;
  const scale = Math.max(w / iw, h / ih) * photoZoom;   // cover scale × zoom
  const overflowX = iw * scale - w;              // cropped-off width  (>0 if cropped)
  const overflowY = ih * scale - h;              // cropped-off height
  const move = (ev) => {
    ev.preventDefault();
    const p = getPos(ev);
    const dx = p.x - start.x, dy = p.y - start.y;
    // Dragging the image right (dx>0) reveals its LEFT side, so offset decreases.
    if (overflowX > 0) photoOffsetX = Math.max(0, Math.min(1, startOX - dx / overflowX));
    if (overflowY > 0) photoOffsetY = Math.max(0, Math.min(1, startOY - dy / overflowY));
    applyPhotoPosition();
  };
  // Pointer events (v315): the press that started this is a prevented
  // pointerdown, which suppresses mousemove/mouseup for it -- a mouse drag of
  // the photo would never move. Pointer events carry mouse, pen and touch.
  const up = () => {
    window.removeEventListener('pointermove', move);
    window.removeEventListener('pointerup', up);
    window.removeEventListener('pointercancel', up);
    if (typeof scheduleAutosave === 'function') scheduleAutosave();
  };
  window.addEventListener('pointermove', move, { passive: false });
  window.addEventListener('pointerup', up);
  window.addEventListener('pointercancel', up);
}

// Drag the Loop Detail waveform to pan the window. Ignores drags that start on
// an edge handle (those resize the loop) so the two never fight.
function dragZoomPan(wrap) {
  SkriblDragTrack.bind(wrap, function (e) {
    if (!audioEl || !Number.isFinite(audioDuration) || audioDuration <= 0) return null;
    if (e.target.closest('.zoom-handle')) return null;   // let the handle drag win
    e.preventDefault();
    const rect = wrap.getBoundingClientRect();
    const zw = getZoomWindow();
    const startCenter = (zw.start + zw.end) / 2;
    const winDur = zw.duration;
    const startX = SkriblEventPoint.at(e).clientX;
    wrap.classList.add('panning');
    return {
      move: function (clientX) {
        const deltaT = -((clientX - startX) / rect.width) * winDur;
        const half = winDur / 2;
        const lo = half, hi = Math.max(half, audioDuration - half);
        zoomCenter = Math.max(lo, Math.min(startCenter + deltaT, hi));
        zoomFocus = 'free';
        syncZoomFocusButtons();
        updateTrimUI();
      },
      end: function () { wrap.classList.remove('panning'); }
    };
  });
}

/* THE BINDING TRAVELS WITH THE FUNCTION, and leaving it behind is what the
 * first draft of this carve did. `bindEl('resetPhotoBtn', 'click', ...)` sits
 * at app.js's TOP LEVEL and passes the handler by REFERENCE, so the name has
 * to exist at the moment that line runs -- and a function carved into a file
 * that loads after app.js does not. The Pad threw a ReferenceError on load,
 * abandoned every line after it, and took `photoUploadBtn`'s declaration down
 * with it, which is why the second error named a variable this change never
 * touched. verify_boot's "the script reached its last line" is the row that
 * says so, and it is the reason that row exists.
 *
 * bindEl is declared in app.js and this file loads after it, so calling it
 * here is the same call one line later. */
bindEl('resetPhotoBtn', 'click', resetPhotoAdjustments);
