// Editor-only: export (PNG, GIF, WebM/MP4 encoders, share card)
//
// Lifted VERBATIM out of app.js, which served the editor AND the public player:
// every visitor opening a shared link downloaded this code to run none of it.
// The code is unchanged — only its file moved — so the editor keeps one
// implementation and there is no second copy to drift.
//
// LOAD ORDER MATTERS. This is a classic script, not a module, and it reads
// globals that app.js declares (strokes, canvas, showToast, renderStrokes...). It must stay
// AFTER app.js in the template, and it is deliberately absent from
// skribl_player.html.
// ==================== EXPORT ====================
(function initExport() {
  const exportItem = document.getElementById('exportItem');
  const overlay = document.getElementById('exportOverlay');
  const sheet = document.getElementById('exportSheet');
  const pngBtn = document.getElementById('exportPng');
  const videoBtn = document.getElementById('exportVideo');
  const progress = document.getElementById('exportProgress');
  const progressFill = document.getElementById('exportProgressFill');
  const progressLabel = document.getElementById('exportProgressLabel');
  const exportCancel = document.getElementById('exportCancel');
  let _exportAbort = false;
  if (exportCancel) exportCancel.addEventListener('click', () => {
    _exportAbort = true;
    if (progressLabel) progressLabel.textContent = 'Cancelling…';
  });
  const videoDesc = document.getElementById('exportVideoDesc');
  const gifBtn = document.getElementById('exportGif');
  const gifDesc = document.getElementById('exportGifDesc');
  const gifToggle = document.getElementById('exportGifToggle');
  let gifBgMode = 'color';   // 'color' | 'transparent'
  let closeTimer = null;

  function openExport() {
    // Update the video option description based on what's available
    const videoTitle = videoBtn.querySelector('.export-opt-title');
    if (!strokes.length) {
      videoDesc.textContent = 'Record a drawing first to export video';
      videoBtn.disabled = true;
    } else {
      videoDesc.textContent = audioEl ? 'Replay of your drawing with music' : 'Replay of your drawing';
      videoBtn.disabled = false;
      // Label the button with the format this browser will actually output.
      // The container lives in the TITLE only — the description's job is the
      // tradeoff, and repeating "WebM" in both lines said it twice.
      if (videoTitle) {
        expectedVideoFormat().then((fmt) => {
          videoTitle.textContent = 'Video (' + fmt + ')';
        }).catch(() => { videoTitle.textContent = 'Video'; });
      }
    }
    pngBtn.disabled = !hasContent;
    // GIF option: needs strokes AND the vendored gifenc library.
    if (gifBtn) {
      // Availability is now 'the server has the file', not 'the file is already
      // in memory' — gifenc is fetched on the click. Asking for the global here
      // would disable the option on every page load; see _skribl_vendor.html.
      const gifReady = !!(window.gifenc && window.gifenc.GIFEncoder)
        || !!(window.SKRIBL_VENDOR && window.SKRIBL_VENDOR.gifenc);
      if (!strokes.length) {
        gifBtn.disabled = true;
        if (gifDesc) gifDesc.textContent = 'Record a drawing first to export a GIF';
        if (gifToggle) gifToggle.hidden = true;
      } else if (!gifReady) {
        gifBtn.disabled = true;
        if (gifDesc) gifDesc.textContent = 'GIF encoder didn’t load — try reloading';
        if (gifToggle) gifToggle.hidden = true;
      } else {
        gifBtn.disabled = false;
        const hasPhoto = photoBgImg && photoBgImg.src && photoBgImg.style.display !== 'none';
        if (gifDesc) gifDesc.textContent = hasPhoto
          ? 'Strokes only · your photo won’t be included (use Video for that)'
          : 'Just the strokes — loops, no sound';
        if (gifToggle) gifToggle.hidden = false;
      }
    }
    progress.hidden = true;
    clearTimeout(closeTimer);
    overlay.hidden = false;
    requestAnimationFrame(() => {
      overlay.classList.add('open');
      // Re-measure the GIF toggle's sliding pill now that the sheet has real
      // layout — the observers can miss this on reopen, leaving the pill wrongly
      // sized. A rAF after reveal guarantees correct button widths.
      if (gifToggle && !gifToggle.hidden) {
        const seg = gifToggle.querySelector('.gif-seg');
        if (seg && typeof positionSegSlider === 'function') {
          requestAnimationFrame(() => positionSegSlider(seg));
        }
      }
    });
  }
  function closeExport() {
    overlay.classList.remove('open');
    closeTimer = setTimeout(() => { overlay.hidden = true; }, 350);
  }

  exportItem.addEventListener('click', () => {
    closeMenu();
    openExport();
  });
  overlay.addEventListener('click', (e) => {
    if (!e.target.closest('.menu-sheet')) closeExport();
  });
  // Close on Escape, consistent with the main menu.
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden) closeExport();
  });
  // Mobile sheet handle closes too.
  const exportHandle = sheet ? sheet.querySelector('.menu-handle') : null;
  if (exportHandle) exportHandle.addEventListener('click', (e) => { e.stopPropagation(); closeExport(); });

  // GIF background toggle (Background color | Transparent)
  if (gifToggle) {
    gifToggle.querySelectorAll('.gif-seg-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        gifBgMode = btn.getAttribute('data-gif-bg') || 'color';
        gifToggle.querySelectorAll('.gif-seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
      });
    });
    // Same sliding-pill highlight as the smoothing/focus/magnifier segments.
    const gifSeg = gifToggle.querySelector('.gif-seg');
    if (gifSeg && typeof attachSegSlider === 'function') attachSegSlider(gifSeg);
  }

  // ---- GIF export (strokes only; looping; silent) ------------------------
  // Renders the SAME replay frames as the video path, but strokes-only (no
  // photo) at a capped size/framerate, and encodes an animated GIF via the
  // vendored `gifenc` global. Transparent mode keys out the background (GIF's
  // 1-bit alpha → crisp for bold line art); color mode paints the pad's solid
  // background (no fringe). Gated on gifenc; dormant/handled if absent.
  async function exportGif() {
    try {
      await skriblLoadVendor('gifenc');
    } catch (e) {
      showToast('GIF encoder didn\u2019t load — check your connection', null);
      return;
    }
    const G = window.gifenc;
    if (!(G && G.GIFEncoder && G.quantize && G.applyPalette)) {
      showToast('GIF export needs gifenc.min.js', null);
      return;
    }
    const timeline = buildPlaybackTimeline();
    if (!timeline.length) return;
    const transparent = (gifBgMode === 'transparent');

    // Cap output size so GIFs stay a sane weight (256-color, no inter-frame delta).
    const dpr = window.devicePixelRatio || 1;
    const logicalW = canvas.width / dpr, logicalH = canvas.height / dpr;
    const MAX_EDGE = 480;
    const scale = Math.min(1, MAX_EDGE / Math.max(logicalW, logicalH));
    const outW = Math.max(2, Math.round(logicalW * scale));
    const outH = Math.max(2, Math.round(logicalH * scale));

    _exportAbort = false;
    videoBtn.disabled = true; pngBtn.disabled = true; gifBtn.disabled = true;
    progress.hidden = false; progressFill.style.width = '0%'; progressLabel.textContent = 'Rendering GIF…';

    try {
      // Strokes accumulate on a transparent canvas (the live canvas is already
      // transparent — bg color/photo live behind it — so this is strokes-only).
      const strokeCanvas = document.createElement('canvas'); strokeCanvas.width = canvas.width; strokeCanvas.height = canvas.height;
      const sctx = strokeCanvas.getContext('2d'); sctx.scale(dpr, dpr);
      const sDot = (x, y, c, s, er) => { sctx.globalCompositeOperation = er ? 'destination-out' : 'source-over'; sctx.beginPath(); sctx.arc(x, y, s / 2, 0, Math.PI * 2); sctx.fillStyle = er ? 'rgba(0,0,0,1)' : c; sctx.fill(); sctx.globalCompositeOperation = 'source-over'; };
      const sLine = (x1, y1, x2, y2, c, s, er) => { sctx.globalCompositeOperation = er ? 'destination-out' : 'source-over'; sctx.beginPath(); sctx.moveTo(x1, y1); sctx.lineTo(x2, y2); sctx.strokeStyle = er ? 'rgba(0,0,0,1)' : c; sctx.lineWidth = s; sctx.lineCap = 'round'; sctx.lineJoin = 'round'; sctx.stroke(); sctx.globalCompositeOperation = 'source-over'; };
      const comp = strokeLayersOn() ? makeStrokeCompositor(sctx, strokeCanvas) : null;

      // Seed prior strokes (pre-record snapshot is drawing-only on transparent).
      if (preRecordSnapshot) {
        await new Promise((res) => { const im = new Image(); im.onload = () => { try { sctx.drawImage(im, 0, 0, logicalW, logicalH); } catch (e) {} res(); }; im.onerror = () => res(); im.src = preRecordSnapshot; });
      }

      const out = document.createElement('canvas'); out.width = outW; out.height = outH;
      const octx = out.getContext('2d');
      function frameData() {
        octx.clearRect(0, 0, outW, outH);
        if (!transparent) { octx.fillStyle = bgColor || '#0d0f14'; octx.fillRect(0, 0, outW, outH); }
        octx.drawImage(strokeCanvas, 0, 0, outW, outH);
        return octx.getImageData(0, 0, outW, outH);
      }

      const enc = G.GIFEncoder();
      const fps = 15, delay = Math.round(1000 / fps);
      const totalMs = timeline[timeline.length - 1].playT || 0;
      const holdMs = 600;
      const totalFrames = Math.max(1, Math.ceil(((totalMs + holdMs) / 1000) * fps));
      const fmt = transparent ? 'rgba4444' : 'rgb565';
      let ti = 0;
      for (let f = 0; f < totalFrames; f++) {
        if (_exportAbort) {
          videoBtn.disabled = false; pngBtn.disabled = false; gifBtn.disabled = false;
          progress.hidden = true; showToast('Export cancelled', null);
          return;
        }
        const elapsed = f * (1000 / fps);
        if (comp) { ti = replayTimelineToCanvas(timeline, ti, elapsed, comp.dotFn, comp.lineFn); comp.present(); }
        else { ti = replayTimelineToCanvas(timeline, ti, elapsed, sDot, sLine); }
        if (f === totalFrames - 1 && comp) { comp.finish(); comp.present(); }
        const img = frameData();
        const palette = G.quantize(img.data, 256, { format: fmt, oneBitAlpha: transparent });
        const index = G.applyPalette(img.data, palette, fmt);
        const opts = { palette, delay };
        if (f === 0) opts.repeat = 0;                 // loop forever
        if (transparent) {
          let tIdx = palette.findIndex((c) => c.length > 3 && c[3] === 0);
          if (tIdx < 0) tIdx = 0;
          opts.transparent = true; opts.transparentIndex = tIdx; opts.dispose = 2;
        }
        enc.writeFrame(index, outW, outH, opts);
        if ((f & 3) === 0) { progressFill.style.width = Math.min(95, (f / totalFrames) * 95) + '%'; await new Promise((r) => setTimeout(r, 0)); }
      }
      enc.finish();
      const bytes = enc.bytes();
      downloadBlob(new Blob([bytes], { type: 'image/gif' }), 'skribl.gif');
      progressFill.style.width = '100%'; progressLabel.textContent = 'Done!';
      showToast('GIF exported', null);
      videoBtn.disabled = false; pngBtn.disabled = false; gifBtn.disabled = false;
      setTimeout(closeExport, 800);
    } catch (err) {
      console.error('GIF export failed:', err);
      showToast('GIF export failed', null);
      progress.hidden = true;
      videoBtn.disabled = false; pngBtn.disabled = false; gifBtn.disabled = false;
    }
  }

  if (gifBtn) gifBtn.addEventListener('click', () => { exportGif(); });

  // ---- Build a flattened composite of bg color + photo + drawing ----
  function drawComposite(targetCtx, w, h) {
    // Background color
    targetCtx.fillStyle = bgColor || '#0d0f14';
    targetCtx.fillRect(0, 0, w, h);
    // Photo (respect fit + opacity + blur)
    if (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src) {
      targetCtx.save();
      targetCtx.globalAlpha = photoOpacityVal_ != null ? photoOpacityVal_ : 1;
      if (photoBlur_ > 0 && 'filter' in targetCtx) targetCtx.filter = `blur(${photoBlur_}px)`;
      drawPhotoFitted(targetCtx, photoBgImg, w, h, photoFit, photoOffsetX, photoOffsetY, photoZoom);
      targetCtx.restore();
    }
    // Drawing canvas on top
    targetCtx.drawImage(canvas, 0, 0, w, h);
  }

  // Geometry is shared with Flip and the player via lib/photofit.js — this
  // function is now just "compute the rect, then draw it". The two copies of
  // the arithmetic agreed on cover/contain but not on the third mode's NAME,
  // which is how a value one surface posts became unreadable to the other.
  function drawPhotoFitted(c, img, w, h, fit, ox, oy, zoom) {
    const iw = img.naturalWidth || w, ih = img.naturalHeight || h;
    const r = window.SkriblPhotoFit.rect(iw, ih, w, h,
      { fit: fit, offX: ox, offY: oy, zoom: zoom });
    c.drawImage(img, r.x, r.y, r.w, r.h);
  }

  // ---- PNG export ----
  pngBtn.addEventListener('click', () => {
    const w = canvas.width, h = canvas.height;
    const out = document.createElement('canvas');
    out.width = w; out.height = h;
    const octx = out.getContext('2d');
    drawComposite(octx, w, h);
    out.toBlob((blob) => {
      if (!blob) { showToast('Export failed', null); return; }
      downloadBlob(blob, 'skribl.png');
      showToast('Image exported', null);
      closeExport();
    }, 'image/png');
  });

  // ---- MP4 export via WebCodecs + mp4-muxer (Route A) --------------------
  // Produces a real H.264/AAC MP4 by stepping the SAME replay core frame-by-
  // frame into a VideoEncoder and looping the baked WAV into an AudioEncoder,
  // muxed by the vendored `Mp4Muxer` global. Everything is capability-gated:
  // if WebCodecs, the codecs, or the muxer aren't present it returns false and
  // the caller falls back to the MediaRecorder path — so this is never worse
  // than today, and stays dormant until mp4-muxer is deployed.
  async function pickAvcCodec(w, h) {
    if (typeof VideoEncoder === 'undefined' || !VideoEncoder.isConfigSupported) return null;
    const cands = ['avc1.640028', 'avc1.4d0028', 'avc1.42001f', 'avc1.42e01e'];
    for (const c of cands) {
      try {
        const r = await VideoEncoder.isConfigSupported({ codec: c, width: w, height: h, bitrate: 6000000, framerate: 30 });
        if (r && r.supported) return c;
      } catch (e) {}
    }
    return null;
  }
  async function aacSupported(sr, ch) {
    if (typeof AudioEncoder === 'undefined' || !AudioEncoder.isConfigSupported) return false;
    try {
      const r = await AudioEncoder.isConfigSupported({ codec: 'mp4a.40.2', sampleRate: sr, numberOfChannels: ch, bitrate: 128000 });
      return !!(r && r.supported);
    } catch (e) { return false; }
  }

  // What format will the Video button actually produce in THIS browser? Used to
  // label the export option honestly (MP4 vs WebM).
  function mediaRecorderFormat() {
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return null;
    const types = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
    for (const t of types) { if (MediaRecorder.isTypeSupported(t)) return t.indexOf('mp4') >= 0 ? 'mp4' : 'webm'; }
    return null;
  }
  async function webcodecsMp4Ready() {
    // Deliberately does NOT load the muxer. This runs when the export SHEET
    // OPENS, only to choose between the "MP4 (H.264)" and "WebM" labels, and
    // pulling 32 KB to pick a word would move the cost from every page load to
    // every sheet open — better, but still paid by people who never export.
    // Whether MP4 is possible depends on the browser's encoder support and on
    // the muxer being DEPLOYED; presence of the URL answers the second without
    // fetching it. exportViaWebCodecsMp4() does the real load, on the click.
    if (!(window.Mp4Muxer || (window.SKRIBL_VENDOR && window.SKRIBL_VENDOR.mp4muxer))) return false;
    if (typeof VideoEncoder === 'undefined' || typeof VideoFrame === 'undefined') return false;
    const w = canvas.width & ~1, h = canvas.height & ~1;
    if (!(await pickAvcCodec(w, h))) return false;
    // If the Skribl has music, MP4 needs AAC too — else the export falls back to
    // MediaRecorder, so don't promise MP4 in the label.
    const hasAudio = !!(audioEl && (audioEl._objectUrl || audioEl.src)) && (typeof musicEnabled === 'undefined' ? true : musicEnabled);
    if (hasAudio && !(await aacSupported(44100, 2))) return false;
    return true;
  }
  async function expectedVideoFormat() {
    if (await webcodecsMp4Ready()) return 'MP4';
    return mediaRecorderFormat() === 'mp4' ? 'MP4' : 'WebM';
  }

  async function exportViaWebCodecsMp4() {
    // ---- capability pre-check (NO UI side effects; false ⇒ clean fallback) ----
    try { await skriblLoadVendor('mp4muxer'); } catch (e) { return false; }
    const MM = window.Mp4Muxer;
    if (!(MM && MM.Muxer && MM.ArrayBufferTarget)) return false;
    if (typeof VideoEncoder === 'undefined' || typeof VideoFrame === 'undefined') return false;
    const w = canvas.width & ~1, h = canvas.height & ~1;   // encoders want even dims
    if (w < 2 || h < 2) return false;
    const avcCodec = await pickAvcCodec(w, h);
    if (!avcCodec) return false;
    const timeline = buildPlaybackTimeline();
    if (!timeline.length) return false;

    // Audio: only if the Skribl has enabled music. If it does but we can't
    // AAC-encode, decline so the MediaRecorder fallback keeps the audio rather
    // than us shipping a silent MP4.
    const hasAudio = !!(audioEl && (audioEl._objectUrl || audioEl.src)) &&
                     (typeof musicEnabled === 'undefined' ? true : musicEnabled);
    let audioBuf = null, useAudio = false;
    if (hasAudio) {
      try {
        const built = (typeof buildTrimmedLoopWav === 'function') ? buildTrimmedLoopWav() : null;
        if (built && built.dataUrl) {
          const tmpCtx = new (window.AudioContext || window.webkitAudioContext)();
          const ab = await fetch(built.dataUrl).then(r => r.arrayBuffer());
          audioBuf = await tmpCtx.decodeAudioData(ab);
          try { tmpCtx.close(); } catch (e) {}
          useAudio = await aacSupported(audioBuf.sampleRate, audioBuf.numberOfChannels);
        }
      } catch (e) { audioBuf = null; useAudio = false; }
      if (!useAudio) return false;
    }

    // ---- commit: from here we own the export UI ----
    _exportAbort = false;
    videoBtn.disabled = true; pngBtn.disabled = true;
    progress.hidden = false; progressFill.style.width = '0%'; progressLabel.textContent = 'Preparing…';
    const cleanup = () => { videoBtn.disabled = false; pngBtn.disabled = false; };

    try {
      const muxer = new MM.Muxer({
        target: new MM.ArrayBufferTarget(),
        video: { codec: 'avc', width: w, height: h },
        audio: useAudio ? { codec: 'aac', numberOfChannels: audioBuf.numberOfChannels, sampleRate: audioBuf.sampleRate } : undefined,
        fastStart: 'in-memory'    // moov at front → immediately playable file
      });
      let encErr = null;
      const vEnc = new VideoEncoder({ output: (c, m) => muxer.addVideoChunk(c, m), error: (e) => { encErr = e; } });
      vEnc.configure({ codec: avcCodec, width: w, height: h, bitrate: 6000000, framerate: 30 });
      let aEnc = null;
      if (useAudio) {
        aEnc = new AudioEncoder({ output: (c, m) => muxer.addAudioChunk(c, m), error: (e) => { encErr = e; } });
        aEnc.configure({ codec: 'mp4a.40.2', numberOfChannels: audioBuf.numberOfChannels, sampleRate: audioBuf.sampleRate, bitrate: 128000 });
      }

      // Offscreen frame renderer (mirrors renderFrameUpTo in the MediaRecorder path).
      const rec = document.createElement('canvas'); rec.width = w; rec.height = h;
      const rctx = rec.getContext('2d');
      const strokeCanvas = document.createElement('canvas'); strokeCanvas.width = w; strokeCanvas.height = h;
      const sctx = strokeCanvas.getContext('2d');
      const dpr = window.devicePixelRatio || 1; sctx.scale(dpr, dpr);
      const sDot = (x, y, c, s, er) => { sctx.globalCompositeOperation = er ? 'destination-out' : 'source-over'; sctx.beginPath(); sctx.arc(x, y, s / 2, 0, Math.PI * 2); sctx.fillStyle = er ? 'rgba(0,0,0,1)' : c; sctx.fill(); sctx.globalCompositeOperation = 'source-over'; };
      const sLine = (x1, y1, x2, y2, c, s, er) => { sctx.globalCompositeOperation = er ? 'destination-out' : 'source-over'; sctx.beginPath(); sctx.moveTo(x1, y1); sctx.lineTo(x2, y2); sctx.strokeStyle = er ? 'rgba(0,0,0,1)' : c; sctx.lineWidth = s; sctx.lineCap = 'round'; sctx.lineJoin = 'round'; sctx.stroke(); sctx.globalCompositeOperation = 'source-over'; };
      const comp = strokeLayersOn() ? makeStrokeCompositor(sctx, strokeCanvas) : null;
      function composite() {
        rctx.fillStyle = bgColor || '#0d0f14'; rctx.fillRect(0, 0, w, h);
        if (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src) {
          rctx.save(); rctx.globalAlpha = (photoOpacityVal_ != null ? photoOpacityVal_ : 1);
          if (photoBlur_ > 0 && 'filter' in rctx) rctx.filter = 'blur(' + photoBlur_ + 'px)';
          drawPhotoFitted(rctx, photoBgImg, w, h, photoFit, photoOffsetX, photoOffsetY, photoZoom);
          rctx.restore();
        }
        rctx.drawImage(strokeCanvas, 0, 0, w, h);
      }

      // Seed the pre-record base drawing, if any.
      if (preRecordSnapshot) {
        await new Promise((res) => { const im = new Image(); im.onload = () => { try { sctx.drawImage(im, 0, 0, w / dpr, h / dpr); } catch (e) {} res(); }; im.onerror = () => res(); im.src = preRecordSnapshot; });
      }

      const fps = 30, frameDurUs = 1000000 / fps;
      const totalMs = timeline[timeline.length - 1].playT || 0;
      const holdMs = 700;
      const totalFrames = Math.max(1, Math.ceil(((totalMs + holdMs) / 1000) * fps));
      progressLabel.textContent = 'Encoding…';
      let ti = 0;
      for (let f = 0; f < totalFrames; f++) {
        if (_exportAbort) {
          try { vEnc.close(); } catch (e) {}
          try { if (aEnc) aEnc.close(); } catch (e) {}
          progress.hidden = true; cleanup(); showToast('Export cancelled', null);
          return true;
        }
        const elapsed = f * (1000 / fps);
        if (comp) { ti = replayTimelineToCanvas(timeline, ti, elapsed, comp.dotFn, comp.lineFn); comp.present(); }
        else { ti = replayTimelineToCanvas(timeline, ti, elapsed, sDot, sLine); }
        if (f === totalFrames - 1 && comp) { comp.finish(); comp.present(); }
        composite();
        const vf = new VideoFrame(rec, { timestamp: Math.round(f * frameDurUs), duration: Math.round(frameDurUs) });
        vEnc.encode(vf, { keyFrame: (f % (fps * 2)) === 0 });
        vf.close();
        if (encErr) throw encErr;
        if (vEnc.encodeQueueSize > 8) { await new Promise(r => setTimeout(r, 0)); }
        if ((f & 7) === 0) { progressFill.style.width = Math.min(85, (f / totalFrames) * 85) + '%'; await new Promise(r => setTimeout(r, 0)); }
      }
      await vEnc.flush();

      // Audio: tile the baked loop across the full duration, encode in blocks.
      if (useAudio && aEnc) {
        progressLabel.textContent = 'Encoding audio…';
        const sr = audioBuf.sampleRate, ch = audioBuf.numberOfChannels, loopLen = audioBuf.length;
        const chans = []; for (let c = 0; c < ch; c++) chans.push(audioBuf.getChannelData(c));
        const totalSamples = Math.ceil(((totalMs + holdMs) / 1000) * sr);
        const blk = 1024; let pos = 0;
        while (pos < totalSamples) {
          const n = Math.min(blk, totalSamples - pos);
          const data = new Float32Array(n * ch);         // f32-planar: [ch0…, ch1…]
          for (let c = 0; c < ch; c++) { const src = chans[c]; const off = c * n; for (let k = 0; k < n; k++) { data[off + k] = src[(pos + k) % loopLen]; } }
          const ad = new AudioData({ format: 'f32-planar', sampleRate: sr, numberOfFrames: n, numberOfChannels: ch, timestamp: Math.round((pos / sr) * 1000000), data });
          aEnc.encode(ad); ad.close();
          if (encErr) throw encErr;
          pos += n;
          if ((pos % (blk * 32)) === 0) { await new Promise(r => setTimeout(r, 0)); }
        }
        await aEnc.flush();
      }
      if (encErr) throw encErr;

      muxer.finalize();
      const buffer = muxer.target.buffer;
      progressFill.style.width = '100%'; progressLabel.textContent = 'Done!';
      downloadBlob(new Blob([buffer], { type: 'video/mp4' }), 'skribl.mp4');
      showToast('MP4 exported', null);
      try { vEnc.close(); } catch (e) {} try { if (aEnc) aEnc.close(); } catch (e) {}
      cleanup();
      setTimeout(closeExport, 800);
      return true;
    } catch (err) {
      console.error('WebCodecs MP4 export failed:', err);
      showToast('MP4 failed — using standard video', null);
      progress.hidden = true;
      cleanup();
      return false;    // let the caller fall back to the MediaRecorder export
    }
  }

  // ---- Video export ----
  videoBtn.addEventListener('click', async () => {
    if (!strokes.length) return;
    if (typeof MediaRecorder === 'undefined') {
      showToast('Video export not supported on this browser', null);
      return;
    }
    // Stop any live playback/preview/seam so live audio doesn't overlap export.
    stopPlayback();
    stopLoopPreview();
    stopSeamTest();

    // Prefer a real MP4 (H.264/AAC) via WebCodecs + muxer when available. Returns
    // false (cleanly, no UI left dangling) if unsupported or on failure, so we
    // fall through to the MediaRecorder path below — never worse than today.
    try {
      const okMp4 = await exportViaWebCodecsMp4();
      if (okMp4) return;
    } catch (e) { /* fall through to MediaRecorder */ }

    // Pick a supported mime type
    const types = ['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm','video/mp4'];
    let mimeType = '';
    for (const t of types) { if (MediaRecorder.isTypeSupported(t)) { mimeType = t; break; } }
    if (!mimeType) { showToast('Video export not supported here', null); return; }

    videoBtn.disabled = true; pngBtn.disabled = true;
    progress.hidden = false;
    progressFill.style.width = '0%';
    progressLabel.textContent = 'Preparing…';

    try {
    // Clear any export-audio globals from a prior run so a stale loop buffer
    // can't be picked up by an export that has no audio this time.
    window._exportAudioSrc = null; window._exportAudioNode = null;
    window._exportAudioBuf = null; window._exportAudioCtx = null; window._exportAudioDest = null;
    const w = canvas.width, h = canvas.height;
    const rec = document.createElement('canvas');
    rec.width = w; rec.height = h;
    const rctx = rec.getContext('2d');

    const fps = 30;
    // Manual capture (0) so requestFrame() explicitly pushes each composited
    // frame — more reliable start and end than auto-capture. Fall back to
    // auto-capture if the browser lacks requestFrame support.
    let stream = rec.captureStream(0);
    let manualCapture = true;
    if (!stream.getVideoTracks()[0] || typeof stream.getVideoTracks()[0].requestFrame !== 'function') {
      stream = rec.captureStream(fps);
      manualCapture = false;
    }
    let videoTrack = null;

    // Mix audio in if present
    let audioContextForExport = null;
    let mixDest = null;
    if (audioEl) {
      try {
        audioContextForExport = new (window.AudioContext || window.webkitAudioContext)();
        // Browsers often start an AudioContext suspended; resume it so samples
        // actually flow from the very first frame (fixes silent/glitchy intro).
        if (audioContextForExport.state === 'suspended') {
          await audioContextForExport.resume().catch(()=>{});
        }
        mixDest = audioContextForExport.createMediaStreamDestination();

        // Prefer the SAME baked loop the post uses: buildTrimmedLoopWav() folds
        // the crossfade and slices [trimStart,trimEnd] into one clip, so the
        // exported audio loops seamlessly (no hard-cut seam click) and matches
        // the posted Skribl exactly. Decode it into the export context and play
        // it as a gapless looping AudioBufferSourceNode (started in runTimeline).
        let loopBuf = null;
        try {
          const built = (typeof buildTrimmedLoopWav === 'function') ? buildTrimmedLoopWav() : null;
          if (built && built.dataUrl) {
            const ab = await fetch(built.dataUrl).then(r => r.arrayBuffer());
            loopBuf = await audioContextForExport.decodeAudioData(ab);
          }
        } catch (e) { loopBuf = null; }

        if (loopBuf) {
          stream.getAudioTracks().forEach(t => t.stop());
          mixDest.stream.getAudioTracks().forEach(t => stream.addTrack(t));
          window._exportAudioBuf = loopBuf;
          window._exportAudioCtx = audioContextForExport;
          window._exportAudioDest = mixDest;
          window._exportAudioSrc = null;
        } else {
          // Fallback (baked loop unavailable, e.g. source not decoded): raw
          // <audio> region loop — the previous hard-cut behavior, wrap in frame().
          const srcEl = new Audio();
          srcEl.src = audioEl._draftData || audioEl.src;
          srcEl.crossOrigin = 'anonymous';
          srcEl.loop = false;
          srcEl.preload = 'auto';
          // Wait until the audio is actually ready to play through.
          await new Promise((resolve) => {
            let done = false;
            const finish = () => { if (!done) { done = true; resolve(); } };
            if (srcEl.readyState >= 3) finish();
            srcEl.addEventListener('canplaythrough', finish, { once: true });
            srcEl.addEventListener('loadeddata', finish, { once: true });
            setTimeout(finish, 1500); // safety timeout
            srcEl.load();
          });
          srcEl.currentTime = trimStart;
          const track = audioContextForExport.createMediaElementSource(srcEl);
          track.connect(mixDest);
          stream.getAudioTracks().forEach(t => t.stop());
          mixDest.stream.getAudioTracks().forEach(t => stream.addTrack(t));
          window._exportAudioSrc = srcEl;
        }
      } catch (e) { audioContextForExport = null; }
    }

    const chunks = [];
    videoTrack = stream.getVideoTracks()[0];
    const recorder = new MediaRecorder(stream, { mimeType });
    recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: mimeType.split(';')[0] });
      const ext = mimeType.indexOf('mp4') >= 0 ? 'mp4' : 'webm';
      downloadBlob(blob, 'skribl.' + ext);
      progressLabel.textContent = 'Done!';
      progressFill.style.width = '100%';
      showToast('Video exported', null);
      videoBtn.disabled = false; pngBtn.disabled = false;
      if (audioContextForExport) { try { audioContextForExport.close(); } catch(e){} }
      if (window._exportAudioNode) { try { window._exportAudioNode.stop(); } catch(e){} try { window._exportAudioNode.disconnect(); } catch(e){} window._exportAudioNode = null; }
      window._exportAudioBuf = null; window._exportAudioCtx = null; window._exportAudioDest = null;
      if (window._exportAudioSrc) { try { window._exportAudioSrc.pause(); } catch(e){} window._exportAudioSrc = null; }
      setTimeout(closeExport, 800);
    };

    // Prepare the base frame (bg + photo + pre-record snapshot)
    const baseImg = new Image();
    // Compressed timeline so export matches preview (capped idle gaps).
    const timeline = buildPlaybackTimeline();
    const totalMs = timeline.length ? timeline[timeline.length - 1].playT : 0;

    function renderFrameUpTo(strokeIndex) {
      // Composite: bg + photo + a temp canvas holding strokes drawn so far
      rctx.fillStyle = bgColor || '#0d0f14';
      rctx.fillRect(0, 0, w, h);
      if (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src) {
        rctx.save();
        rctx.globalAlpha = photoOpacityVal_ != null ? photoOpacityVal_ : 1;
        if (photoBlur_ > 0 && 'filter' in rctx) rctx.filter = `blur(${photoBlur_}px)`;
        drawPhotoFitted(rctx, photoBgImg, w, h, photoFit, photoOffsetX, photoOffsetY, photoZoom);
        rctx.restore();
      }
      rctx.drawImage(strokeCanvas, 0, 0, w, h);
    }

    // Offscreen canvas that accumulates strokes during export (so we don't disturb the live one)
    const strokeCanvas = document.createElement('canvas');
    strokeCanvas.width = w; strokeCanvas.height = h;
    const sctx = strokeCanvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    sctx.scale(dpr, dpr);

    function sDot(x,y,c,s,erase){ sctx.globalCompositeOperation = erase?'destination-out':'source-over'; sctx.beginPath(); sctx.arc(x,y,s/2,0,Math.PI*2); sctx.fillStyle = erase?'rgba(0,0,0,1)':c; sctx.fill(); sctx.globalCompositeOperation='source-over'; }
    function sLine(x1,y1,x2,y2,c,s,erase){ sctx.globalCompositeOperation = erase?'destination-out':'source-over'; sctx.beginPath(); sctx.moveTo(x1,y1); sctx.lineTo(x2,y2); sctx.strokeStyle = erase?'rgba(0,0,0,1)':c; sctx.lineWidth=s; sctx.lineCap='round'; sctx.lineJoin='round'; sctx.stroke(); sctx.globalCompositeOperation='source-over'; }

    function startRecording() {
      progressLabel.textContent = 'Recording…';
      renderFrameUpTo(0);
      // Wet/dry compositor for low-opacity strokes, targeting the export stroke
      // layer. Seeds dry from strokeCanvas (base already painted). Flag-gated.
      const comp = strokeLayersOn() ? makeStrokeCompositor(sctx, strokeCanvas) : null;

      const pushFrame = () => { if (manualCapture && videoTrack && videoTrack.requestFrame) { try { videoTrack.requestFrame(); } catch(e){} } };

      // 1. Start the recorder first and push a few opening frames so it has a
      //    stable stream before anything happens.
      recorder.start();
      renderFrameUpTo(0);
      pushFrame();

      // 2. After a short warm-up, start audio and the drawing timeline TOGETHER
      //    on the same tick — so they're in sync and the recorder is already
      //    running when audio begins (no early clipped blip).
      function runTimeline() {
        // Start audio in sync with the timeline: the gapless crossfaded loop
        // buffer (preferred) or the raw <audio> region-loop fallback.
        if (window._exportAudioBuf && window._exportAudioCtx && window._exportAudioDest) {
          try {
            const node = window._exportAudioCtx.createBufferSource();
            node.buffer = window._exportAudioBuf;
            node.loop = true;
            node.loopStart = 0;
            node.loopEnd = window._exportAudioBuf.duration;
            node.connect(window._exportAudioDest);
            node.start();
            window._exportAudioNode = node;
          } catch (e) {}
        } else if (window._exportAudioSrc) {
          const a = window._exportAudioSrc;
          try { a.currentTime = trimStart; a.play().catch(()=>{}); } catch(e){}
        }
        const startTime = performance.now();
        let i = 0;
        let finished = false;
        function frame() {
          const elapsed = performance.now() - startTime;
          if (comp) {
            i = replayTimelineToCanvas(timeline, i, elapsed, comp.dotFn, comp.lineFn);
            comp.present();
          } else {
            i = replayTimelineToCanvas(timeline, i, elapsed, sDot, sLine);
          }
          renderFrameUpTo(i);
          pushFrame();
          if (window._exportAudioSrc) {
            const a = window._exportAudioSrc;
            if (a.currentTime >= trimEnd - 0.05) { a.currentTime = trimStart; }
          }
          progressFill.style.width = Math.min(100, (elapsed / Math.max(1, totalMs)) * 100) + '%';
          if (i < timeline.length || elapsed < totalMs) {
            requestAnimationFrame(frame);
          } else if (!finished) {
            finished = true;
            if (comp) { comp.finish(); comp.present(); }
            const holdStart = performance.now();
            function holdFrame() {
              renderFrameUpTo(timeline.length);
              pushFrame();
              if (performance.now() - holdStart < 700) {
                requestAnimationFrame(holdFrame);
              } else {
                if (window._exportAudioNode) { try { window._exportAudioNode.stop(); } catch(e){} }
                if (window._exportAudioSrc) { try { window._exportAudioSrc.pause(); } catch(e){} }
                try { recorder.stop(); } catch(e){}
              }
            }
            requestAnimationFrame(holdFrame);
          }
        }
        requestAnimationFrame(frame);
      }

      // Brief warm-up so the recorder/stream are established, then go.
      setTimeout(runTimeline, 250);
    }

    // If there's a pre-record base drawing, paint it into strokeCanvas first
    progressLabel.textContent = 'Preparing…';
    if (preRecordSnapshot) {
      baseImg.onload = () => { sctx.drawImage(baseImg, 0, 0, w/dpr, h/dpr); startRecording(); };
      baseImg.onerror = () => startRecording();
      baseImg.src = preRecordSnapshot;
    } else {
      startRecording();
    }
    } catch (err) {
      // Any failure in setup (MediaRecorder, audio context, stream) must not
      // leave the export sheet stuck with disabled buttons.
      showToast('Video export failed', null);
      videoBtn.disabled = false; pngBtn.disabled = false;
      progress.hidden = true;
      if (window._exportAudioNode) { try { window._exportAudioNode.stop(); } catch(e){} window._exportAudioNode = null; }
      window._exportAudioBuf = null; window._exportAudioCtx = null; window._exportAudioDest = null;
      if (window._exportAudioSrc) { try { window._exportAudioSrc.pause(); } catch(e){} window._exportAudioSrc = null; }
    }
  });

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
})();

