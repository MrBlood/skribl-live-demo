const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const canvasWrap = document.querySelector('.canvas-wrap');
const canvasArea = document.querySelector('.canvas-area') || (canvasWrap && canvasWrap.parentElement);
const toolSlider = document.getElementById('toolSlider');

// Create eraser cursor early so setTool() can reference it safely
const eraserCursor = document.createElement('div');
eraserCursor.id = 'eraserCursor';
eraserCursor.style.cssText = `
  position: absolute;
  border: 2px solid rgba(255,255,255,0.6);
  border-radius: 50%;
  pointer-events: none;
  display: none;
  transform: translate(-50%, -50%);
  z-index: 10;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.3);
`;
canvasWrap.appendChild(eraserCursor);

let bgColor = '#0d0f14';
let photoBg = null;
let photoFit = 'cover';
let photoEnabled = true;   // Image on/off toggle
let musicEnabled = true;   // Music on/off toggle
let photoOpacityVal_ = 1;
let photoBlur_ = 0;
let photoOffsetX = 0.5, photoOffsetY = 0.5; // Fill-mode crop position (0..1 each)
let photoZoom = 1;                          // Fill-mode zoom multiplier (1..3)
let repositioning = false;                  // photo-drag mode; suspends drawing

// The canvas's logical drawing size (the coordinate space strokes replay in).
// In the editor this equals the CSS display size. In player mode the canvas is
// shrunk to fit the viewport (CSS size < authored size) while the backing store
// stays at authored size × dpr, so drawing/clearing/restoring must use the
// authored logical size — otherwise the base snapshot paints at the small
// display size while strokes replay at authored coords and they don't line up.
function getCanvasLogicalSize() {
  // Both editor and player now use a FIXED authored backing store and only scale
  // the CSS display size to fit (letterbox). The logical drawing space is always
  // the backing store in CSS px, so strokes / replay / clear never distort.
  const dpr = window.devicePixelRatio || 1;
  return { width: canvas.width / dpr, height: canvas.height / dpr };
}

// The editor authors at a FIXED logical size (like the player) and scales the
// display to fit the available area, letterboxing when the viewport aspect
// differs — so rotating never stretches or reflows the drawing. The authored
// size is established once from the initial available area, or from a restored
// draft's canvasSize.
let authoredW = 0, authoredH = 0;
function establishEditorCanvas(w, h) {
  const dpr = window.devicePixelRatio || 1;
  authoredW = Math.max(1, Math.round(w));
  authoredH = Math.max(1, Math.round(h));
  canvas.width = Math.round(authoredW * dpr);
  canvas.height = Math.round(authoredH * dpr);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
}
// Fit the fixed authored size into the available area with ONE uniform scale
// (aspect locked, never upscaled past 1:1) and center it via .canvas-area. The
// backing store is untouched here, so this never clears the canvas or distorts
// the drawing — rotating just re-fits the display.
function layoutEditorCanvas() {
  if (!authoredW || !authoredH) return;
  const area = (canvasArea || canvasWrap.parentElement || canvasWrap).getBoundingClientRect();
  const availW = Math.max(1, area.width);
  const availH = Math.max(1, area.height);
  const scale = Math.min(1, availW / authoredW, availH / authoredH);
  const dispW = Math.round(authoredW * scale);
  const dispH = Math.round(authoredH * scale);
  canvasWrap.style.width = dispW + 'px';
  canvasWrap.style.height = dispH + 'px';
  canvas.style.width = dispW + 'px';
  canvas.style.height = dispH + 'px';
  canvas.style.minHeight = '0';
  canvasWrap.style.backgroundColor = bgColor;
}

function resizeCanvas() {
  // Player mode sizes its canvas from the authored dimensions itself.
  if (document.body.classList.contains('player-mode')) return;
  // Establish the authored space once, from the initial available area. After
  // that only the DISPLAY is re-fit on resize/rotate — the backing store (and
  // therefore the drawing and every stroke coordinate) stays fixed, so rotating
  // letterboxes instead of stretching. A restored draft re-establishes it from
  // its own canvasSize (see loadSkribl).
  if (!authoredW || !authoredH) {
    const area = (canvasArea || canvasWrap.parentElement || canvasWrap).getBoundingClientRect();
    establishEditorCanvas(area.width || 320, area.height || 320);
  }
  layoutEditorCanvas();
}
resizeCanvas();
window.addEventListener('resize', () => {
  resizeCanvas();
  updateTabSlider(document.querySelector('.tab-btn.active'));
  const activeFitBtn = document.querySelector('.photo-fit-btn.active');
  if (activeFitBtn && photoFitSlider) {
    const allBtns = [...document.querySelectorAll('.photo-fit-btn')];
    const idx = allBtns.indexOf(activeFitBtn);
    const offset = allBtns.slice(0, idx).reduce((sum, b) => sum + b.offsetWidth, 0);
    photoFitSlider.style.width = activeFitBtn.offsetWidth + 'px';
    photoFitSlider.style.transform = `translateX(${offset}px)`;
  }
  initToolSlider();
});
// Some mobile browsers fire orientationchange without a paired resize; re-fit the
// letterbox display (backing store untouched, so the drawing is preserved).
window.addEventListener('orientationchange', () => {
  if (!document.body.classList.contains('player-mode')) layoutEditorCanvas();
});

let drawing = false;
// Canvas magnify (editor only). ZoomView is assigned by initCanvasZoom() near
// the bottom; it stays null on the player (no #zoomLayer), so every zoom/pinch
// path below no-ops there. `pinching` suspends drawing during a 2-finger
// gesture; `_autoArmedThisStroke` lets a pinch-aborted first stroke also unwind
// the recording it auto-started.
let ZoomView = null;
let pinching = false;
let _autoArmedThisStroke = false;
let recording = false;
let playing = false;
let scrubbing = false, lastTargetMs = 0;   // v84 scrub state (used by stopPlayback)
let frameIndex = 0;   // Phase 1: current frame. Always 0 until Flip Mode adds frames.
let recorded = false;
let hasContent = false;
// Post-record rule (Option B): once a recording is finished, the canvas is
// locked — no new drawing on the completed replay. Drawing re-enables when the
// user starts a new recording or clears the canvas. This keeps a finished
// Skribl = base snapshot + recorded strokes, with no ambiguous extra layer.
let finishedRecording = false;
let color = '#ffffff';
let size = 5;
let tool = 'pen';

const canvasEmptyHint = document.getElementById('canvasEmptyHint');
function updateEmptyHint() {
  if (canvasEmptyHint) canvasEmptyHint.classList.toggle('hidden', hasContent);
}

// Recompute all derived UI state after a history change (undo/redo).
// Keeps hasContent, the empty hint, clear button, play/post buttons,
// and the duration badge in sync with the restored strokes/canvas.
// restoredHasContent comes from the history state being restored — strokes
// alone can't tell us, because un-recorded drawing lives only as pixels.
function syncStateAfterHistoryChange(restoredHasContent) {
  hasContent = restoredHasContent;
  recorded = strokes.length > 0;
  // Keep the finished-object model coherent: if recorded strokes still exist,
  // the replay is still a finished recording, so stay locked. Undo/redo through
  // recorded strokes still works; you just can't draw NEW unrecorded pixels on
  // a finished Skribl (which would silently diverge from play/export/save).
  // If undo removes all recorded strokes, `recorded` is false and it unlocks.
  if (!recording) finishedRecording = recorded;
  playWrap.hidden = !recorded;
  postBtn.hidden = !recorded;
  if (recorded) {
    updateDrawingTimeLabels();
    durationBadge.hidden = false;
  } else {
    durationBadge.hidden = true;
    const matchLabel = document.getElementById('matchDrawingLabel');
    if (matchLabel) matchLabel.textContent = '';
  }
  document.querySelector('.header').classList.toggle('compact', recording || recorded);
  updateEmptyHint();
  updateClearVisibility();
  updateCanvasLockCue();
}

function updateClearVisibility() {
  // Clear now lives in the overflow menu; disable it during recording
  const clearItem = document.getElementById('clearMenuItem');
  if (clearItem) clearItem.disabled = recording || !(hasContent || recorded);
}

// Reflect the post-record lock in the cursor so it's obvious the canvas
// is no longer drawable until the user records again or clears.
function updateCanvasLockCue() {
  canvasWrap.classList.toggle('locked', finishedRecording && !recording);
  if (finishedRecording && !recording) {
    canvas.style.cursor = 'not-allowed';
    eraserCursor.style.display = 'none';
  } else {
    canvas.style.cursor = tool === 'eraser' ? 'none' : '';
  }
}

let strokes = [];
let currentStroke = [];
let strokeGroups = [];
let startTime = null;
let lastPos = null;
let preRecordSnapshot = null;
let undoStack = [];
let redoStack = [];
let clearBackup = null;   // snapshot so "Clear drawing" can be undone (the stack is wiped on clear)

// --- More-tools state (opacity, smoothing, eyedropper, recent colors) ---
let strokeOpacity = 1;    // 0.1..1 — baked into the pen color as rgba() per point
let smoothingAlpha = 1;   // 1 = off; <1 = stabilizer strength (lower = smoother)
let smoothPt = null;      // running smoothed position during an active stroke
let lastRawPos = null;    // last true pointer position (for snap-to-final on release)
let pickingColor = false; // eyedropper fallback: next canvas tap samples a pixel
let recentColors = [];    // recently used custom / eyedropped colors (hex)

const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
undoBtn.disabled = true;
redoBtn.disabled = true;


function makeHistoryState() {
  // Snapshot into an offscreen canvas via drawImage instead of toDataURL():
  // toDataURL PNG-encodes the whole canvas synchronously on EVERY stroke start
  // (main-thread jank, worst on mobile/large canvases) and kept up to 30
  // multi-MB base64 strings alive in the undo stack. A canvas-to-canvas
  // drawImage is cheap, and restore becomes synchronous drawImage too (no
  // async <img> decode). Nothing serializes these states, so the shape change
  // (string -> canvas) is safe: undo/redo below are the only consumers.
  const snap = document.createElement('canvas');
  snap.width = Math.max(1, canvas.width);
  snap.height = Math.max(1, canvas.height);
  if (canvas.width > 0 && canvas.height > 0) {
    snap.getContext('2d').drawImage(canvas, 0, 0);
  }
  return {
    image: snap,
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    hasContent: hasContent
  };
}

function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  const src = e.touches ? e.touches[0] : e;
  // The canvas may be displayed smaller than its authored size (letterbox fit),
  // so map the CSS-pixel pointer position back into the fixed logical space.
  const lg = getCanvasLogicalSize();
  const sx = rect.width ? lg.width / rect.width : 1;
  const sy = rect.height ? lg.height / rect.height : 1;
  return {
    x: (src.clientX - rect.left) * sx,
    y: (src.clientY - rect.top) * sy,
  };
}

function drawDot(x, y, c, s, erase) {
  ctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
  ctx.beginPath();
  ctx.arc(x, y, s / 2, 0, Math.PI * 2);
  ctx.fillStyle = erase ? 'rgba(0,0,0,1)' : c;
  ctx.fill();
  ctx.globalCompositeOperation = 'source-over';
}

function drawLine(x1, y1, x2, y2, c, s, erase) {
  ctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = erase ? 'rgba(0,0,0,1)' : c;
  ctx.lineWidth = s;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke();
  ctx.globalCompositeOperation = 'source-over';
}

// --- Low-opacity stroke compositing (wet/dry layers) -------------------------
// A stroke drawn as many overlapping semi-transparent stamps compounds at the
// overlaps into dark "beads". Fix: draw the whole stroke OPAQUE on an offscreen
// "wet" layer, keep finished work on the "dry" layer (a copy of the canvas as it
// was when the stroke began), and show dry + wet×alpha. One composite per stroke
// instead of per-stamp → uniform translucency, no beads. Opacity is read back
// from the point color's rgba alpha, so NO data/serialize/timeline change is
// needed. ON by default across all consumers (live drawing, preview, player,
// export); set window.SKRIBL_STROKE_LAYERS = false as an instant kill switch if a
// problem ever surfaces. Only non-eraser, sub-100% strokes take this path —
// everything else is byte-identical to the old direct drawing.
function strokeLayersOn() {
  return typeof window === 'undefined' ? false : window.SKRIBL_STROKE_LAYERS !== false;
}
function parseStrokeAlpha(c) {
  if (typeof c !== 'string') return 1;
  const m = c.match(/^rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)$/i);
  return m ? Math.max(0, Math.min(1, parseFloat(m[1]))) : 1;
}
function solidStrokeColor(c) {
  if (typeof c !== 'string') return c;
  const m = c.match(/^rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*[\d.]+\s*\)$/i);
  return m ? `rgb(${m[1]}, ${m[2]}, ${m[3]})` : c;
}

let _dryCanvas = null, _wetCanvas = null, _dryCtx = null, _wetCtx = null;
let _wetAlpha = 1, _slActive = false;
function ensureStrokeLayers() {
  const dpr = window.devicePixelRatio || 1;
  if (!_dryCanvas) { _dryCanvas = document.createElement('canvas'); _dryCtx = _dryCanvas.getContext('2d'); }
  if (!_wetCanvas) { _wetCanvas = document.createElement('canvas'); _wetCtx = _wetCanvas.getContext('2d'); }
  if (_dryCanvas.width !== canvas.width || _dryCanvas.height !== canvas.height) {
    _dryCanvas.width = canvas.width; _dryCanvas.height = canvas.height;
    _dryCtx.setTransform(1, 0, 0, 1, 0, 0);            // dry: identity (blit target)
  }
  if (_wetCanvas.width !== canvas.width || _wetCanvas.height !== canvas.height) {
    _wetCanvas.width = canvas.width; _wetCanvas.height = canvas.height;
    _wetCtx.setTransform(1, 0, 0, 1, 0, 0); _wetCtx.scale(dpr, dpr);  // wet: logical coords
  }
}
// Opaque primitives targeting an arbitrary context (the wet layer).
function drawDotOn(c2, x, y, color, s) {
  c2.globalCompositeOperation = 'source-over';
  c2.beginPath(); c2.arc(x, y, s / 2, 0, Math.PI * 2);
  c2.fillStyle = color; c2.fill();
}
function drawLineOn(c2, x1, y1, x2, y2, color, s) {
  c2.globalCompositeOperation = 'source-over';
  c2.beginPath(); c2.moveTo(x1, y1); c2.lineTo(x2, y2);
  c2.strokeStyle = color; c2.lineWidth = s; c2.lineCap = 'round'; c2.lineJoin = 'round'; c2.stroke();
}
// Present dry + wet×alpha onto the visible canvas. Blits at identity (backing-
// store pixels), then restores the main ctx's dpr transform + alpha.
function presentWet() {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(_dryCanvas, 0, 0);
  ctx.globalAlpha = _wetAlpha;
  ctx.drawImage(_wetCanvas, 0, 0);
  ctx.restore();
}
// Begin a wet/dry stroke: snapshot the canvas as "dry", clear "wet", stamp the
// first dot opaque. Returns true if this stroke is taking the layered path.
function beginWetStroke(x, y, drawColor, drawSize) {
  ensureStrokeLayers();
  _wetAlpha = parseStrokeAlpha(drawColor);
  _dryCtx.clearRect(0, 0, _dryCanvas.width, _dryCanvas.height);
  _dryCtx.drawImage(canvas, 0, 0);                       // 1:1 copy of current canvas
  const lg = getCanvasLogicalSize();
  _wetCtx.clearRect(0, 0, lg.width, lg.height);          // dpr-scaled → clears full layer
  drawDotOn(_wetCtx, x, y, solidStrokeColor(drawColor), drawSize);
  presentWet();
}

// Replay compositor: the same wet/dry idea as live drawing, but driven by
// replayTimelineToCanvas's own dot/line callbacks — so the ONE timing loop is
// reused UNCHANGED. dotFn fires exactly at stroke starts, which is the boundary
// to bake the previous stroke. Low-opacity non-eraser strokes go wet→bake; opaque
// and eraser strokes draw straight onto dry (byte-identical to drawDot/drawLine).
// Consumers: build one after the base is on `visCanvas`, pass its dotFn/lineFn to
// the loop, call present() each frame, and finish() at the end.
function makeStrokeCompositor(visCtx, visCanvas) {
  const dpr = window.devicePixelRatio || 1;
  const dry = document.createElement('canvas');
  const wet = document.createElement('canvas');
  dry.width = wet.width = visCanvas.width;
  dry.height = wet.height = visCanvas.height;
  const dctx = dry.getContext('2d');
  const wctx = wet.getContext('2d');
  // Seed dry with the base already on the visible canvas (photo/bg + snapshot).
  dctx.setTransform(1, 0, 0, 1, 0, 0);
  dctx.drawImage(visCanvas, 0, 0);
  dctx.scale(dpr, dpr);                                  // dry now draws in logical coords
  wctx.setTransform(1, 0, 0, 1, 0, 0); wctx.scale(dpr, dpr);
  const lgW = visCanvas.width / dpr, lgH = visCanvas.height / dpr;
  let wetActive = false, wetAlpha = 1;

  function bakeWet() {
    dctx.save();
    dctx.setTransform(1, 0, 0, 1, 0, 0);
    dctx.globalAlpha = wetAlpha;
    dctx.drawImage(wet, 0, 0);
    dctx.restore();
    wctx.clearRect(0, 0, lgW, lgH);
    wetActive = false; wetAlpha = 1;
  }
  function dryDot(x, y, color, size, erase) {
    dctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
    dctx.beginPath(); dctx.arc(x, y, size / 2, 0, Math.PI * 2);
    dctx.fillStyle = erase ? 'rgba(0,0,0,1)' : color; dctx.fill();
    dctx.globalCompositeOperation = 'source-over';
  }
  function dryLine(x1, y1, x2, y2, color, size, erase) {
    dctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
    dctx.beginPath(); dctx.moveTo(x1, y1); dctx.lineTo(x2, y2);
    dctx.strokeStyle = erase ? 'rgba(0,0,0,1)' : color;
    dctx.lineWidth = size; dctx.lineCap = 'round'; dctx.lineJoin = 'round'; dctx.stroke();
    dctx.globalCompositeOperation = 'source-over';
  }
  return {
    dotFn(x, y, color, size, erase) {
      if (wetActive) bakeWet();                          // close out the previous stroke
      const a = erase ? 1 : parseStrokeAlpha(color);
      if (!erase && a < 1) {
        wetActive = true; wetAlpha = a;
        wctx.clearRect(0, 0, lgW, lgH);
        drawDotOn(wctx, x, y, solidStrokeColor(color), size);
      } else {
        dryDot(x, y, color, size, erase);
      }
    },
    lineFn(x1, y1, x2, y2, color, size, erase) {
      if (wetActive) drawLineOn(wctx, x1, y1, x2, y2, solidStrokeColor(color), size);
      else dryLine(x1, y1, x2, y2, color, size, erase);
    },
    present() {
      visCtx.save();
      visCtx.setTransform(1, 0, 0, 1, 0, 0);
      visCtx.globalAlpha = 1;
      visCtx.clearRect(0, 0, visCanvas.width, visCanvas.height);
      visCtx.drawImage(dry, 0, 0);
      if (wetActive) { visCtx.globalAlpha = wetAlpha; visCtx.drawImage(wet, 0, 0); }
      visCtx.restore();
    },
    finish() { if (wetActive) bakeWet(); }
  };
}

// Static (non-timed) paint of a full strokes array — the poster/recovery render
// used by loadSkribl and restoreAutosave. Routes through the wet/dry compositor
// when the flag is on (low-opacity strokes match playback), else the direct path.
// Uses the same start/continuation dispatch as replayTimelineToCanvas.
function paintStrokesStatic(strokeArr) {
  if (strokeLayersOn()) {
    const comp = makeStrokeCompositor(ctx, canvas);
    for (let i = 0; i < strokeArr.length; i++) {
      const p = strokeArr[i];
      if (p.start || i === 0) comp.dotFn(p.x, p.y, p.color, p.size, p.erase);
      else { const prev = strokeArr[i - 1]; comp.lineFn(prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase); }
    }
    comp.finish();
    comp.present();
  } else {
    for (let i = 0; i < strokeArr.length; i++) {
      const p = strokeArr[i];
      if (p.start || i === 0) drawDot(p.x, p.y, p.color, p.size, p.erase);
      else { const prev = strokeArr[i - 1]; drawLine(prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase); }
    }
  }
}

// Pure replay core shared by preview playback and video export, so stroke
// timing can never diverge between them. Draws every timeline point whose
// playT has elapsed, using the supplied dot/line fns (main canvas vs the
// offscreen export canvas). No audio, no DOM, no globals — just drawing.
// Returns the next index to resume from.
function replayTimelineToCanvas(timeline, startIndex, elapsedMs, dotFn, lineFn) {
  let i = startIndex;
  while (i < timeline.length && timeline[i].playT <= elapsedMs) {
    const p = timeline[i];
    if (p.start || i === 0) {
      dotFn(p.x, p.y, p.color, p.size, p.erase);
    } else {
      const prev = timeline[i - 1];
      lineFn(prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
    }
    i++;
  }
  return i;
}
let lockToastShown = false;
function startDraw(e) {
  // Two (or more) fingers → magnify/pan gesture, never a stroke. Handled before
  // preventDefault/anything else so it can cleanly abort a nascent 1-finger
  // stroke that the first finger just began. Guarded on ZoomView so the player
  // (no zoom) behaves exactly as before.
  if (ZoomView && e.touches && e.touches.length >= 2) { beginPinch(e); return; }
  e.preventDefault();
  _autoArmedThisStroke = false;
  // Ignore non-primary mouse buttons (right/middle click). A right-click
  // mousedown would otherwise enter here mid-stroke and reset currentStroke,
  // wiping the in-progress stroke from the replay array (still painted live,
  // but gone on playback). Touch events have no .button, so guard on != null
  // so touch drawing still works.
  if (e.button != null && e.button !== 0) return;
  // A preview is playing (or being scrubbed): the canvas is a playback surface,
  // not a drawing surface. Block every pointer-initiated action so a stray tap
  // can't start a stroke, sample, or reposition mid-replay. (Record/Play/Stop
  // still work via their own buttons.)
  if (playing) return;
  // Eyedropper (fallback path): consume this tap to sample a pixel instead of
  // starting a stroke. Allowed even on a locked canvas — it only reads.
  if (pickingColor) { const p = getPos(e); sampleColorAt(p.x, p.y); return; }
  // Photo reposition mode: this drag moves the background, never the drawing.
  // Returns before the lock check and the undo push, so it can't start a stroke,
  // fire the lock toast, or create an undo entry. Ignored during recording so a
  // take is never blocked.
  if (repositioning && !recording) { beginPhotoDrag(e); return; }
  // Tapping the canvas while a drawer is open just dismisses it (no stray dot).
  // After the eyedropper/reposition checks so those keep working.
  if (!document.getElementById('drawPanel').hidden ||
      !document.getElementById('musicPanel').hidden ||
      !document.getElementById('photoPanel').hidden) {
    openDrawer(null);
    return;
  }
  // Post-record lock: the completed replay can't be drawn over.
  if (finishedRecording && !recording) {
    if (!lockToastShown) {
      showToast('Recording done — Record again to add another take, or Clear to restart', recordBtn);
      lockToastShown = true;
      setTimeout(() => { lockToastShown = false; }, 3000);
    }
    return;
  }
  // Auto-arm: on a blank, unlocked canvas the first stroke starts recording on
  // its own, so a first-time user who "just draws" still gets a replay to post
  // without knowing to press Record first. Only fires when nothing is drawn yet
  // and no take is in progress or finished; every other entry path is unchanged.
  // beginRecording captures the (blank) base and flips `recording` true before we
  // read `t` below, so this first point lands at t≈0 like a normal take start.
  if (!recording && !finishedRecording && !hasContent) {
    beginRecording(false);
    _autoArmedThisStroke = true;
  }
  const pos = getPos(e);
  drawing = true;
  document.body.classList.add('stroking');
  lastPos = pos;
  smoothPt = { x: pos.x, y: pos.y };
  lastRawPos = { x: pos.x, y: pos.y };
  currentStroke = [];
  undoStack.push(makeHistoryState());
  if (undoStack.length > 30) undoStack.shift();
  undoBtn.disabled = false;
  redoStack = [];
  redoBtn.disabled = true;
  const t = recording ? Date.now() - startTime : 0;
  const erase = tool === 'eraser';
  const drawColor = erase ? bgColor : penColorFor(color);
  const drawSize = erase ? size * 3 : size;
  const point = { x: pos.x, y: pos.y, color: drawColor, size: drawSize, t, start: true, erase };
  currentStroke.push(point);
  _slActive = strokeLayersOn() && !erase && parseStrokeAlpha(drawColor) < 1;
  if (_slActive) {
    beginWetStroke(pos.x, pos.y, drawColor, drawSize);
  } else {
    drawDot(pos.x, pos.y, drawColor, drawSize, erase);
  }
  hasContent = true;
  updateClearVisibility();
  updateEmptyHint();
}

function continueDraw(e) {
  e.preventDefault();
  if (pinching) return;
  if (!drawing) return;
  const pos = getPos(e);
  lastRawPos = pos;
  // Stabilizer: ease the drawn point toward the raw position. At smoothingAlpha
  // === 1 this is a no-op (dp === pos), so "Off" is byte-identical to before.
  // The smoothed point is what gets stored, so replay reproduces it exactly.
  if (!smoothPt) smoothPt = { x: lastPos.x, y: lastPos.y };
  smoothPt = {
    x: smoothPt.x + (pos.x - smoothPt.x) * smoothingAlpha,
    y: smoothPt.y + (pos.y - smoothPt.y) * smoothingAlpha
  };
  const dp = smoothingAlpha >= 1 ? pos : smoothPt;
  const t = recording ? Date.now() - startTime : 0;
  const erase = tool === 'eraser';
  const drawColor = erase ? bgColor : penColorFor(color);
  const drawSize = erase ? size * 3 : size;
  const point = { x: dp.x, y: dp.y, color: drawColor, size: drawSize, t, erase };
  currentStroke.push(point);
  if (_slActive) {
    drawLineOn(_wetCtx, lastPos.x, lastPos.y, dp.x, dp.y, solidStrokeColor(drawColor), drawSize);
    presentWet();
  } else {
    drawLine(lastPos.x, lastPos.y, dp.x, dp.y, drawColor, drawSize, erase);
  }
  lastPos = dp;
}

// With smoothing on, the drawn line lags the finger, so a stroke would end
// slightly short of where you lifted. Extend it to the true final point on
// release. No-op when smoothing is off or already there. Runs before the stroke
// is committed, so the final point rides into the replay array normally.
function snapStrokeToFinal() {
  if (!drawing || smoothingAlpha >= 1) return;
  if (!currentStroke.length || !lastRawPos || !lastPos) return;
  const dx = lastRawPos.x - lastPos.x, dy = lastRawPos.y - lastPos.y;
  if (dx * dx + dy * dy < 0.25) return;   // within ~0.5px: nothing to add
  const t = recording ? Date.now() - startTime : 0;
  const erase = tool === 'eraser';
  const drawColor = erase ? bgColor : penColorFor(color);
  const drawSize = erase ? size * 3 : size;
  currentStroke.push({ x: lastRawPos.x, y: lastRawPos.y, color: drawColor, size: drawSize, t, erase });
  if (_slActive) {
    drawLineOn(_wetCtx, lastPos.x, lastPos.y, lastRawPos.x, lastRawPos.y, solidStrokeColor(drawColor), drawSize);
    presentWet();
  } else {
    drawLine(lastPos.x, lastPos.y, lastRawPos.x, lastRawPos.y, drawColor, drawSize, erase);
  }
  lastPos = lastRawPos;
}

function endDraw() {
  if (!drawing) return;
  snapStrokeToFinal();
  drawing = false;
  document.body.classList.remove('stroking');
  _slActive = false;
  if (recording && currentStroke.length > 0) {
    strokes = strokes.concat(currentStroke);
    strokeGroups.push(currentStroke.length);
  }
  currentStroke = [];
}

// Commit an in-progress stroke into the replay array WITHOUT a normal mouseup —
// for when a context menu, focus loss, or off-canvas release interrupts the
// drag before endDraw fires. Idempotent with endDraw (both bail when !drawing),
// so a stroke can never be double-added.
function commitActiveStroke() {
  if (!drawing) return;
  snapStrokeToFinal();
  drawing = false;
  document.body.classList.remove('stroking');
  _slActive = false;
  if (recording && currentStroke.length > 0) {
    strokes = strokes.concat(currentStroke);
    strokeGroups.push(currentStroke.length);
  }
  currentStroke = [];
}

canvas.addEventListener('mousedown', startDraw);
canvas.addEventListener('mousemove', continueDraw);
canvas.addEventListener('mouseup', endDraw);
canvas.addEventListener('mouseleave', endDraw);
canvas.addEventListener('touchstart', startDraw);
canvas.addEventListener('touchmove', continueDraw);
canvas.addEventListener('touchend', endDraw);
canvas.addEventListener('touchcancel', endDraw);

// Right-click on the canvas: commit the current stroke, then suppress the
// browser context menu so it can't interrupt drawing mid-stroke.
canvas.addEventListener('contextmenu', (e) => {
  commitActiveStroke();
  e.preventDefault();
});
// Releasing the mouse outside the canvas, or the window losing focus, also
// commits — otherwise an interrupted stroke stays painted but unrecorded.
window.addEventListener('mouseup', () => { if (drawing) commitActiveStroke(); });
window.addEventListener('blur', () => { if (drawing) commitActiveStroke(); });

function setTool(nextTool) {
  tool = nextTool;
  const penBtn = document.getElementById('penToolBtn');
  const eraserBtn = document.getElementById('eraserToolBtn');
  const activeBtn = nextTool === 'pen' ? penBtn : eraserBtn;
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.classList.toggle('active', btn === activeBtn);
  });
  canvasWrap.classList.toggle('eraser', nextTool === 'eraser');
  if (finishedRecording && !recording) {
    canvas.style.cursor = 'not-allowed';
  } else {
    canvas.style.cursor = nextTool === 'eraser' ? 'none' : '';
  }
  if (nextTool !== 'eraser') eraserCursor.style.display = 'none';
  if (toolSlider) {
    toolSlider.style.width = activeBtn.offsetWidth + 'px';
    toolSlider.style.transform =
      nextTool === 'pen' ? 'translateX(0)' : `translateX(${penBtn.offsetWidth}px)`;
  }
}

function initToolSlider() {
  setTool(tool || 'pen');
}
setTimeout(initToolSlider, 50);

document.querySelectorAll('.tool-btn').forEach(btn => {
  btn.addEventListener('click', () => setTool(btn.dataset.tool));
});

document.getElementById('colorGroup').addEventListener('click', (e) => {
  const btn = e.target.closest('.color-dot');
  if (!btn || btn.id === 'customColorBtn') return;
  color = btn.dataset.color;
  document.querySelectorAll('.color-dot').forEach(b => b.classList.toggle('active', b === btn));
  setTool('pen');
  updateCurrentColorChip();
});

// Reflect the active pen color on the always-visible chip in the More tools toggle.
function updateCurrentColorChip() {
  const chip = document.getElementById('currentColorChip');
  if (chip) chip.style.background = color;
  const toolChip = document.getElementById('toolColorChip');
  if (toolChip) toolChip.style.background = color;
}
updateCurrentColorChip();

(function initBrushSize() {
  const range = document.getElementById('brushSizeRange');
  const val = document.getElementById('brushSizeVal');
  if (!range) return;
  if (typeof addSliderNudgers === 'function') addSliderNudgers(range, { step: 1 });
  const apply = () => {
    size = parseInt(range.value, 10) || 1;
    if (val) val.textContent = size + 'px';
    const dot = document.getElementById('brushSizeDot');
    if (dot) { const d = Math.min(size, 22); dot.style.width = d + 'px'; dot.style.height = d + 'px'; }
    if (typeof updateSliderFill === 'function') updateSliderFill(range);
  };
  range.addEventListener('input', apply);
  apply();
})();

document.getElementById('bgGroup').addEventListener('click', (e) => {
  const btn = e.target.closest('.bg-swatch');
  if (!btn || btn.id === 'customBgBtn') return;
  bgColor = btn.dataset.bg;
  document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b === btn));
  canvasWrap.style.backgroundColor = bgColor;
  updateVignette();
});

const customBgBtn = document.getElementById('customBgBtn');
const customBgInput = document.getElementById('customBgInput');

customBgInput.addEventListener('input', (e) => {
  const newColor = e.target.value;
  customBgBtn.style.background = newColor;
  bgColor = newColor;
  document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b === customBgBtn));
  canvasWrap.style.backgroundColor = bgColor;
  updateVignette();
});

// The screen-only inset vignette is tuned for dark canvases; on a light/white
// background the dark edges look muddy, so swap to a soft light vignette when
// the background is bright. Purely cosmetic — export stays clean either way.
function updateVignette() {
  const hex = (bgColor || '#0d0f14').replace('#', '');
  if (hex.length < 6) return;
  const r = parseInt(hex.slice(0, 2), 16), g = parseInt(hex.slice(2, 4), 16), b = parseInt(hex.slice(4, 6), 16);
  const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  canvasWrap.classList.toggle('light-bg', lum > 0.6);
}
updateVignette();

const customColorBtn = document.getElementById('customColorBtn');
const customColorInput = document.getElementById('customColorInput');

customColorInput.addEventListener('input', (e) => {
  const newColor = e.target.value;
  customColorBtn.style.background = newColor;
  color = newColor;
  document.querySelectorAll('.color-dot').forEach(b => b.classList.toggle('active', b === customColorBtn));
  setTool('pen');
  addRecent(newColor);
  updateCurrentColorChip();
});

// ============ More-tools drawer: opacity, smoothing, eyedropper, recents, clear
// Opacity rides inside the per-point color (rgba) so it flows through the shared
// replay/export/player with no signature changes; smoothing bakes into the
// stored coordinates. Neither adds a timeline loop or changes the save format.

function penColorFor(hex) {
  // Full opacity keeps the plain hex, so 100% is byte-identical to old behavior.
  if (strokeOpacity >= 1) return hex;
  const h = (hex || '#ffffff').replace('#', '');
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${strokeOpacity})`;
}

// The replay nib is tinted to match the ink at the current point. Stored colors
// are either '#rrggbb' or 'rgba(r,g,b,a)' (low-opacity strokes), so pull the RGB
// out of both and return an "r,g,b" string for the nib's --nib-rgb variable.
// Any stroke alpha is dropped: the nib keeps its own opacity so a faint stroke
// still gets a clearly visible bead. Falls back to white if the color is odd.
function nibRGB(color) {
  if (typeof color === 'string') {
    const hex = color.match(/^#([0-9a-fA-F]{6})$/);
    if (hex) {
      const h = hex[1];
      return parseInt(h.slice(0, 2), 16) + ',' + parseInt(h.slice(2, 4), 16) + ',' + parseInt(h.slice(4, 6), 16);
    }
    const rgb = color.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (rgb) return rgb[1] + ',' + rgb[2] + ',' + rgb[3];
  }
  return '255,255,255';
}

function setPenColor(hex) {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex || '')) return;
  hex = hex.toLowerCase();
  color = hex;
  setTool('pen');
  let matched = null;
  document.querySelectorAll('#colorGroup .color-dot').forEach(b => {
    const isMatch = b.dataset.color && b.dataset.color.toLowerCase() === hex;
    if (isMatch) matched = b;
    b.classList.toggle('active', isMatch);
  });
  if (!matched) {
    customColorBtn.style.background = hex;
    if (customColorInput) customColorInput.value = hex;
    customColorBtn.classList.add('active');
    addRecent(hex);
  }
  updateCurrentColorChip();
}

function addRecent(hex) {
  hex = (hex || '').toLowerCase();
  if (!/^#[0-9a-f]{6}$/.test(hex)) return;
  recentColors = [hex, ...recentColors.filter(c => c !== hex)].slice(0, 6);
  try { localStorage.setItem('skribl_recent_colors', JSON.stringify(recentColors)); } catch (e) {}
  renderRecent();
}

function renderRecent() {
  const row = document.getElementById('recentRow');
  const wrap = document.getElementById('recentColors');
  if (!row || !wrap) return;
  wrap.innerHTML = '';
  recentColors.forEach(hex => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'recent-swatch';
    b.style.background = hex;
    b.setAttribute('aria-label', 'Use color ' + hex);
    b.addEventListener('click', () => setPenColor(hex));
    wrap.appendChild(b);
  });
  row.hidden = recentColors.length === 0;
}

function sampleColorAt(x, y) {
  try {
    const dpr = window.devicePixelRatio || 1;
    const d = ctx.getImageData(Math.round(x * dpr), Math.round(y * dpr), 1, 1).data;
    // Transparent spot (empty canvas) reads as the visible background instead.
    let hex = d[3] < 10 ? bgColor
      : '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
    setPenColor(hex);
  } catch (err) {}
  stopPicking();
}

function stopPicking() {
  pickingColor = false;
  const b = document.getElementById('eyedropperBtn');
  if (b) b.classList.remove('picking');
  updateCanvasLockCue();   // restore lock/eraser/normal cursor rather than wiping it
}

(function initMoreTools() {
  const moreToggle = document.getElementById('moreToggle');
  const moreDrawer = document.getElementById('moreDrawer');
  if (moreToggle && moreDrawer) {
    moreToggle.addEventListener('click', () => {
      const open = moreDrawer.hidden;      // currently hidden -> we are opening
      moreDrawer.hidden = !open;
      moreToggle.classList.toggle('open', open);
      moreToggle.setAttribute('aria-expanded', String(open));
    });
  }

  const opacitySlider = document.getElementById('opacitySlider');
  const opacityVal = document.getElementById('opacityVal');
  if (opacitySlider) {
    opacitySlider.addEventListener('input', () => {
      const v = parseInt(opacitySlider.value, 10);
      strokeOpacity = v / 100;
      if (opacityVal) opacityVal.textContent = v + '%';
      if (typeof updateSliderFill === 'function') updateSliderFill(opacitySlider);
    });
    if (typeof updateSliderFill === 'function') updateSliderFill(opacitySlider);
  }

  const smoothSeg = document.getElementById('smoothSeg');
  if (smoothSeg) {
    smoothSeg.addEventListener('click', (e) => {
      const btn = e.target.closest('.smooth-btn');
      if (!btn) return;
      const lvl = btn.dataset.smooth;
      smoothingAlpha = lvl === 'high' ? 0.25 : lvl === 'low' ? 0.5 : 1;
      smoothSeg.querySelectorAll('.smooth-btn').forEach(b => b.classList.toggle('active', b === btn));
    });
    attachSegSlider(smoothSeg);
  }

  const eyedropperBtn = document.getElementById('eyedropperBtn');
  if (eyedropperBtn) {
    eyedropperBtn.addEventListener('click', async () => {
      if (window.EyeDropper) {
        try {
          const res = await new EyeDropper().open();
          if (res && res.sRGBHex) setPenColor(res.sRGBHex);
        } catch (e) {}
        return;
      }
      // Fallback (e.g. iOS Safari): arm a one-tap sample on the canvas.
      if (pickingColor) { stopPicking(); return; }
      pickingColor = true;
      eyedropperBtn.classList.add('picking');
      canvas.style.cursor = 'crosshair';
      showToast('Tap the canvas to pick a color', eyedropperBtn);
    });
  }

  const clearDrawerBtn = document.getElementById('clearDrawerBtn');
  if (clearDrawerBtn) {
    let armed = false, armTimer = null;
    const label = clearDrawerBtn.querySelector('span');
    const disarm = () => { armed = false; clearDrawerBtn.classList.remove('armed'); if (label) label.textContent = 'Clear drawing'; };
    clearDrawerBtn.addEventListener('click', () => {
      if (recording) { showToast('Stop recording before clearing', clearDrawerBtn); return; }
      if (!armed) {
        armed = true;
        clearDrawerBtn.classList.add('armed');
        if (label) label.textContent = 'Tap again to clear drawing';
        clearTimeout(armTimer);
        armTimer = setTimeout(disarm, 3000);
        return;
      }
      clearTimeout(armTimer);
      disarm();
      const _clearSnap = hasContent ? makeHistoryState() : null;
      clearCanvas();
      if (typeof clearAutosave === 'function') clearAutosave();
      clearBackup = _clearSnap; updateClearUndoBtn();
    });
  }

  // Restore recent colors from a previous session.
  try {
    const saved = JSON.parse(localStorage.getItem('skribl_recent_colors') || '[]');
    if (Array.isArray(saved)) {
      recentColors = saved.filter(c => /^#[0-9a-f]{6}$/.test(c)).slice(0, 6);
      renderRecent();
    }
  } catch (e) {}
})();

const tabSlider = document.getElementById('tabSlider');
const tabBgSlider = document.getElementById('tabBgSlider');

function updateTabSlider(activeBtn) {
  if (!tabSlider || !activeBtn) return;
  tabSlider.style.width = activeBtn.offsetWidth + 'px';
  tabSlider.style.transform = `translateX(${activeBtn.offsetLeft}px)`;
  if (tabBgSlider) {
    tabBgSlider.style.width = activeBtn.offsetWidth + 'px';
    tabBgSlider.style.transform = `translateX(${activeBtn.offsetLeft}px)`;
  }
}

setTimeout(() => {
  updateTabSlider(document.querySelector('.tab-btn.active'));
}, 50);

// Toolbar drawers: each .tool-open button toggles its panel open as a drawer
// above the bar; only one open at a time; tapping the open one closes it.
function openDrawer(name) {                      // name = 'draw'|'photo'|'music' or null
  const idMap = { draw: 'drawPanel', photo: 'photoPanel', music: 'musicPanel' };
  document.getElementById('drawPanel').hidden  = name !== 'draw';
  document.getElementById('musicPanel').hidden = name !== 'music';
  document.getElementById('photoPanel').hidden = name !== 'photo';
  document.querySelectorAll('#toolBar .tool-open').forEach(b =>
    b.classList.toggle('open', b.dataset.drawer === name));
  if (name !== 'photo' && typeof exitReposition === 'function') exitReposition();
  if (typeof pickingColor !== 'undefined' && pickingColor) stopPicking();
  if (name === 'photo' && typeof updateRepositionUI === 'function') updateRepositionUI();
  if (name === 'music') updateDrawingTimeLabels();
  // Drawer opens below the bar; scroll just enough to reveal it (keeps max canvas
  // in frame), and scroll back to rest when everything closes. Honor the user's
  // reduced-motion preference — the CSS sets scroll-behavior:auto for them, but a
  // JS-requested 'smooth' scroll would override that intent, so mirror it here.
  const reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const scrollBehavior = reduceMotion ? 'auto' : 'smooth';
  if (name && idMap[name]) {
    const panel = document.getElementById(idMap[name]);
    requestAnimationFrame(() => panel.scrollIntoView({ behavior: scrollBehavior, block: 'end' }));
  } else {
    window.scrollTo({ top: 0, behavior: scrollBehavior });
  }
}
const toolBarEl = document.getElementById('toolBar');
if (toolBarEl) toolBarEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.tool-open');
  if (!btn) return;                              // pen/eraser use their own setTool binding
  const name = btn.dataset.drawer;
  openDrawer(btn.classList.contains('open') ? null : name);
});

const recordBtn = document.getElementById('recordBtn');
const playBtn = document.getElementById('playBtn');
const playWrap = document.getElementById('playWrap');
const postBtn = document.getElementById('postBtn');
const recIndicator = document.getElementById('recIndicator');
const recTimer = document.getElementById('recTimer');
const durationBadge = document.getElementById('durationBadge');

const ICON_STOP = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>';
const ICON_RECORD = '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>';
const ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 4l14 8-14 8z"/></svg>';
const LABEL_STOP = '<span class="btn-label"> Stop</span>';
const LABEL_RECORD = '<span class="btn-label"> Record</span>';
const LABEL_PLAY = '<span class="btn-label"> Play</span>';

function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m + ':' + String(s).padStart(2, '0');
}

// True playback duration: sums the gaps between strokes exactly the way
// the replay does (capping any gap at 50ms), so long idle pauses don't count.
// Build a compact playback timeline: same capped-gap logic as preview, so the
// exported video matches what Play shows (long idle pauses are compressed).
function buildPlaybackTimeline() {
  if (!strokes.length) return [];
  let playT = 0;
  const timeline = [{ x: strokes[0].x, y: strokes[0].y, color: strokes[0].color, size: strokes[0].size, erase: strokes[0].erase, start: strokes[0].start, playT: 0, i: 0 }];
  for (let i = 1; i < strokes.length; i++) {
    const gap = strokes[i].t - strokes[i - 1].t;
    if (gap > 0) playT += Math.min(gap, 50);
    const s = strokes[i];
    timeline.push({ x: s.x, y: s.y, color: s.color, size: s.size, erase: s.erase, start: s.start, playT: playT, i: i });
  }
  return timeline;
}

function getPlaybackDuration() {
  if (strokes.length < 2) return 0;
  let total = 0;
  for (let i = 1; i < strokes.length; i++) {
    const gap = strokes[i].t - strokes[i - 1].t;
    if (gap > 0) total += Math.min(gap, 50);
  }
  return total;
}

function updateDrawingTimeLabels() {
  const playMs = getPlaybackDuration();
  if (durationBadge) {
    durationBadge.textContent = formatDuration(playMs);
  }
  const matchLabel = document.getElementById('matchDrawingLabel');
  if (matchLabel) {
    matchLabel.textContent = strokes.length ? 'Plays for ' + formatDuration(playMs) : '';
  }
}

let recTimerInterval = null;

// Recording is split into begin/end helpers so the Record button, the auto-arm
// path (first stroke on a blank canvas), and a continue-take all share one code
// path. Multi-take needs NO change to the replay timeline: buildPlaybackTimeline()
// sums only capped, positive gaps between consecutive points, so appending a
// take strings it together seamlessly — the cross-take seam is a non-positive
// gap (each take restarts startTime, so the new take's first t is < the prior
// take's last t) which contributes 0ms, i.e. no dead air. Each take's first
// point keeps start:true, so on replay it draws as a fresh pen-down dot rather
// than a line connecting from wherever the previous take ended.
function beginRecording(continueTake) {
  if (!continueTake) {
    // Fresh Skribl: snapshot whatever is already on the canvas as the static
    // base image, and start the stroke list empty.
    preRecordSnapshot = canvas.toDataURL();
    strokes = []; strokeGroups = [];
  }
  // continueTake: keep existing strokes/strokeGroups AND the original base so the
  // new take appends on top. Never re-snapshot the base mid-Skribl, or the prior
  // takes would bake into the base and also replay (drawn twice).
  startTime = Date.now();
  recording = true;
  recorded = false;
  finishedRecording = false;   // unlock: recording is active
  updateCanvasLockCue();
  if (typeof exitReposition === 'function') { exitReposition(); updateRepositionUI(); }
  if (typeof pickingColor !== 'undefined' && pickingColor) stopPicking();
  recordBtn.innerHTML = ICON_STOP + LABEL_STOP;
  recordBtn.classList.add('active');
  canvasWrap.classList.add('recording');
  document.body.classList.add('recording');
  document.querySelector('.header').classList.add('compact');
  recIndicator.hidden = false;
  playWrap.hidden = true;
  playBtn.innerHTML = ICON_PLAY + LABEL_PLAY;
  postBtn.hidden = true;
  durationBadge.hidden = true;

  recTimer.textContent = '0:00';
  clearInterval(recTimerInterval);   // defensive: never stack intervals
  recTimerInterval = setInterval(() => {
    const wall = formatDuration(Date.now() - startTime);
    // getPlaybackDuration() sums across ALL strokes, so on a continue-take the
    // "play" readout keeps counting up from the previous takes' total.
    const play = formatDuration(getPlaybackDuration());
    recTimer.textContent = wall + ' · ' + play + ' play';
  }, 200);
}

function endRecordingTake() {
  commitActiveStroke();   // capture a stroke still in progress when Stop is hit
  recording = false;
  recorded = strokes.length > 0;
  // Lock the canvas only if we actually captured a replay.
  finishedRecording = recorded;
  updateCanvasLockCue();
  if (typeof updateRepositionUI === 'function') updateRepositionUI();
  recordBtn.innerHTML = ICON_RECORD + LABEL_RECORD;
  recordBtn.classList.remove('active');
  canvasWrap.classList.remove('recording');
  document.body.classList.remove('recording');
  recIndicator.hidden = true;
  playWrap.hidden = !recorded;
  postBtn.hidden = !recorded;
  if (!recorded) document.querySelector('.header').classList.remove('compact');

  clearInterval(recTimerInterval);
  if (recorded) {
    updateDrawingTimeLabels();
    durationBadge.hidden = false;
    // Confirm the capture and surface multi-take: the canvas is now locked on
    // this take; pressing Record again appends another take to the same Skribl.
    showToast('Take saved — Record again to add more to this Skribl, or Play to preview', recordBtn);
  }
  updateClearVisibility();
}

recordBtn.addEventListener('click', () => {
  if (recording) { endRecordingTake(); return; }
  // Leaving a preview to record: stop the preview first. stopPlayback restores
  // the complete drawing, so the new take appends onto the finished frame — not
  // a half-replayed one — and `playing` + `recording` are never both true.
  if (playing) stopPlayback();
  // If a completed take is already on the canvas, continue it as another take
  // (append) instead of wiping and starting over.
  beginRecording(strokes.length > 0);
});


function clearCanvas() {
  stopPlayback();
  stopLoopPreview();
  const { width: cw, height: ch } = getCanvasLogicalSize(); ctx.clearRect(0, 0, cw, ch);
  canvasWrap.style.backgroundColor = bgColor;
  strokes = []; strokeGroups = [];
  recorded = false;
  hasContent = false;
  finishedRecording = false;   // unlock: canvas is drawable again
  updateCanvasLockCue();
  updateEmptyHint();
  preRecordSnapshot = null;
  undoStack = [];
  redoStack = [];
  undoBtn.disabled = true;
  redoBtn.disabled = true;
  durationBadge.hidden = true;
  playWrap.hidden = true;
  postBtn.hidden = true;
  document.querySelector('.header').classList.remove('compact');
  updateClearVisibility();
  const matchLabel = document.getElementById('matchDrawingLabel');
  if (matchLabel) matchLabel.textContent = '';
  if (ZoomView) ZoomView.fit();
  clearBackup = null;                       // a fresh clear/reset invalidates any prior undo snapshot
  if (typeof updateClearUndoBtn === 'function') updateClearUndoBtn();
}

// "Clear drawing" wipes the undo stack, so a normal undo can't bring it back.
// Snapshot before clearing (in the button handler) and let this restore it.
function updateClearUndoBtn() { const b = document.getElementById('clearUndoBtn'); if (b) b.disabled = !clearBackup; }
function restoreClear() {
  if (!clearBackup) return;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  ctx.save(); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch); ctx.drawImage(clearBackup.image, 0, 0, cw, ch); ctx.restore();
  strokes = clearBackup.strokes.slice();
  strokeGroups = clearBackup.strokeGroups.slice();
  syncStateAfterHistoryChange(clearBackup.hasContent);
  clearBackup = null; updateClearUndoBtn();
  if (typeof showToast === 'function') showToast('Drawing restored', null);
}
(function () { const b = document.getElementById('clearUndoBtn'); if (b) b.addEventListener('click', restoreClear); })();

function stopPlayback() {
  playing = false;
  scrubbing = false;
  playBtn.innerHTML = ICON_PLAY + LABEL_PLAY;
  playBtn.disabled = false;
  playBtn.classList.remove('playing');
  if (audioEl) audioEl.pause();
  if (typeof stopWebAudioLoop === 'function') stopWebAudioLoop();
  hideEditorNib();
  hideScrub();
  document.body.classList.remove('replaying');
  // A preview stopped part-way leaves the canvas half-redrawn. Restore the whole
  // finished drawing so Record (append), Post, and undo all act on the complete
  // frame — never a partial one. (At a natural end the frame is already complete,
  // so this just repaints the same pixels; the base image is cached, so it's a
  // synchronous, flicker-free redraw.)
  if (strokes.length) clearAndRestore(() => paintStrokesStatic(strokes));
  updateDrawingTimeLabels();   // restore the duration badge to the total length
}

// The editor Play preview mirrors the posted player's replay bead so what you
// see before posting matches what viewers get. Reuses the player's .player-nib
// styling; positioned over the editor canvas with the same author->display
// mapping getPos uses (independent x/y so it lands exactly on the stroke).
let editorNib = null;
function ensureEditorNib() {
  if (!editorNib) {
    editorNib = document.createElement('div');
    editorNib.className = 'player-nib';
    editorNib.hidden = true;
    canvasWrap.appendChild(editorNib);
  }
  return editorNib;
}
function positionEditorNib(p) {
  const nib = ensureEditorNib();
  if (!p) { nib.hidden = true; return; }
  const rect = canvas.getBoundingClientRect();
  const lg = getCanvasLogicalSize();
  const sx = lg.width > 0 && rect.width > 0 ? rect.width / lg.width : 1;
  const sy = lg.height > 0 && rect.height > 0 ? rect.height / lg.height : 1;
  nib.style.left = (p.x * sx) + 'px';
  nib.style.top = (p.y * sy) + 'px';
  nib.classList.toggle('erase', !!p.erase);
  if (!p.erase) nib.style.setProperty('--nib-rgb', nibRGB(p.color));
  nib.hidden = false;
}
function hideEditorNib() { if (editorNib) editorNib.hidden = true; }

// Cache the decoded base snapshot so repeated redraws (rapid player scrubbing,
// preview restarts) are synchronous. Without this, each call spun up a fresh
// Image with an async onload; during a fast scrub older onloads could resolve
// after newer ones and paint a stale frame. First call for a given snapshot is
// still async (one decode); every call after it draws immediately.
let _baseImgCache = null;   // { src, img }
let restoreSeq = 0;         // monotonic — only the newest call's async paint wins
function clearAndRestore(callback) {
  const seq = ++restoreSeq;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  ctx.clearRect(0, 0, cw, ch);
  if (preRecordSnapshot) {
    if (_baseImgCache && _baseImgCache.src === preRecordSnapshot && _baseImgCache.img.complete) {
      ctx.drawImage(_baseImgCache.img, 0, 0, cw, ch);
      callback();
      return;
    }
    const img = new Image();
    img.onload = () => {
      _baseImgCache = { src: preRecordSnapshot, img };   // cache regardless, so later calls are sync
      if (seq !== restoreSeq) return;                    // superseded by a newer scrub/play — don't paint
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, 0, 0, cw, ch);
      callback();
    };
    img.src = preRecordSnapshot;
  } else {
    callback();
  }
}

// ---- Editor replay + scrubbable play bar ----
// Hoisted state so the seek + scrub handlers (outside the click closure) share it.
let playTimeline = null, playTotal = 0, playStart = 0, playIndex = 0, playComp = null;
const playScrub = document.getElementById('playScrub');
const playScrubFill = document.getElementById('playScrubFill');

function setScrubProgress(frac) {
  if (playScrubFill) playScrubFill.style.width = Math.max(0, Math.min(1, frac)) * 100 + '%';
}
function positionScrub() {
  // Hang the bar just below the canvas, matched to its width — flush to the
  // bottom edge so it reads as dropping down from the canvas frame.
  if (!playScrub || playScrub.hidden || !canvasArea) return;
  const a = canvasArea.getBoundingClientRect();
  const w = canvasWrap.getBoundingClientRect();
  playScrub.style.left = (w.left - a.left) + 'px';
  playScrub.style.width = w.width + 'px';
  playScrub.style.top = (w.bottom - a.top) + 'px';
}
function showScrub() {
  if (!playScrub) return;
  playScrub.hidden = false;
  setScrubProgress(0);
  positionScrub();
  requestAnimationFrame(() => playScrub.classList.add('show'));
}
function hideScrub() {
  if (!playScrub) return;
  playScrub.classList.remove('show');
  playScrub.hidden = true;
  setScrubProgress(0);
}

function editorReplayFrame() {
  if (!playing) return;
  if (scrubbing) { requestAnimationFrame(editorReplayFrame); return; }  // frozen at the scrub position
  const elapsed = performance.now() - playStart;
  if (durationBadge && !durationBadge.hidden) {
    durationBadge.textContent = formatDuration(Math.min(elapsed, playTotal));
  }
  setScrubProgress(playTotal ? elapsed / playTotal : 1);
  if (playComp) {
    playIndex = replayTimelineToCanvas(playTimeline, playIndex, elapsed, playComp.dotFn, playComp.lineFn);
    playComp.present();
  } else {
    playIndex = replayTimelineToCanvas(playTimeline, playIndex, elapsed, drawDot, drawLine);
  }
  positionEditorNib(playIndex > 0 ? playTimeline[playIndex - 1] : null);
  if (playIndex < playTimeline.length) {
    requestAnimationFrame(editorReplayFrame);
  } else {
    if (playComp) { playComp.finish(); playComp.present(); }
    stopPlayback();
  }
}

// Seek to a fraction of the replay: recomposite the base, then replay 0->target
// via the shared helper (no second loop). lastTargetMs carries the position so
// the running loop resumes from there on scrub release. clearAndRestore's
// restoreSeq guard drops any stale paint from a superseded scrub.
function editorSeek(frac) {
  if (!playing || !playTimeline) return;
  frac = Math.max(0, Math.min(1, frac));
  lastTargetMs = playTotal * frac;
  const paint = () => {
    if (strokeLayersOn()) {
      playComp = makeStrokeCompositor(ctx, canvas);
      playIndex = replayTimelineToCanvas(playTimeline, 0, lastTargetMs, playComp.dotFn, playComp.lineFn);
      playComp.present();
    } else {
      playComp = null;
      playIndex = replayTimelineToCanvas(playTimeline, 0, lastTargetMs, drawDot, drawLine);
    }
    setScrubProgress(frac);
    if (durationBadge && !durationBadge.hidden) {
      durationBadge.textContent = formatDuration(Math.min(lastTargetMs, playTotal));
    }
    positionEditorNib(playIndex > 0 ? playTimeline[playIndex - 1] : null);
  };
  clearAndRestore(paint);
}

playBtn.addEventListener('click', () => {
  if (recording) return;   // can't preview mid-take (Play is hidden while recording; guard anyway)
  stopLoopPreview();
  if (playing) { stopPlayback(); return; }
  playTimeline = buildPlaybackTimeline();
  if (!playTimeline.length) return;
  playing = true;
  playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg><span class="btn-label">Stop</span>';
  playBtn.classList.add('playing');
  document.body.classList.add('replaying');
  playTotal = playTimeline[playTimeline.length - 1].playT;
  showScrub();

  clearAndRestore(() => {
    playIndex = 0;
    const beginFrames = () => {
      playComp = strokeLayersOn() ? makeStrokeCompositor(ctx, canvas) : null;
      playStart = performance.now();
      requestAnimationFrame(editorReplayFrame);
    };
    if (audioEl && musicEnabled) {
      playMusicLooped(playTotal, beginFrames);
    } else {
      beginFrames();
    }
  });
});

// Scrub interactions (pointer events cover mouse + touch). Freeze the loop while
// dragging; resume from the released position.
if (playScrub) {
  const scrubFrac = (e) => {
    const r = playScrub.getBoundingClientRect();
    const x = (e.touches && e.touches[0]) ? e.touches[0].clientX : e.clientX;
    return (x - r.left) / r.width;
  };
  playScrub.addEventListener('pointerdown', (e) => {
    if (!playing) return;
    scrubbing = true;
    try { playScrub.setPointerCapture(e.pointerId); } catch (_) {}
    editorSeek(scrubFrac(e));
    e.preventDefault();
  });
  playScrub.addEventListener('pointermove', (e) => {
    if (!scrubbing) return;
    editorSeek(scrubFrac(e));
  });
  const endScrub = () => {
    if (!scrubbing) return;
    scrubbing = false;
    playStart = performance.now() - lastTargetMs;   // resume from the released position
  };
  playScrub.addEventListener('pointerup', endScrub);
  playScrub.addEventListener('pointercancel', endScrub);
  window.addEventListener('resize', () => { if (playing) positionScrub(); });
}

// The Post button opens the composer sheet — wired in initPostComposer() below.

// ---------- Overflow menu ----------
const menuBtn = document.getElementById('menuBtn');
const menuOverlay = document.getElementById('menuOverlay');
let menuCloseTimer = null;

function openMenu() {
  clearTimeout(menuCloseTimer);
  updateClearVisibility();
  menuOverlay.hidden = false;
  requestAnimationFrame(() => menuOverlay.classList.add('open'));
}

function closeMenu(instant) {
  menuOverlay.classList.remove('open');
  clearTimeout(menuCloseTimer);
  if (instant) {
    menuOverlay.hidden = true;   // dismiss with no slide (e.g. when opening another panel)
  } else {
    menuCloseTimer = setTimeout(() => { menuOverlay.hidden = true; }, 350);
  }
}

menuBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  if (menuOverlay.hidden) openMenu(); else closeMenu();
});

menuOverlay.addEventListener('click', (e) => {
  // Close if the tap is not inside the sheet itself
  if (!e.target.closest('.menu-sheet')) closeMenu();
});

// Full reset for the overflow menu's "Clear all": the drawing AND the music,
// photo, and background all back to a fresh start. Reuses each item's existing
// removal (via its own control) so behavior can't drift from the single-item
// remove buttons. clearCanvas() intentionally keeps media, so we clear those
// explicitly here, then return the background to the default swatch.
function resetAll() {
  clearCanvas();
  const mr = document.getElementById('musicRemove');
  if (mr && !mr.hidden) mr.click();
  const pr = document.getElementById('photoRemove');
  if (pr && !pr.hidden) pr.click();
  bgColor = '#0d0f14';
  document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b.dataset.bg === '#0d0f14'));
  canvasWrap.style.backgroundColor = bgColor;
  if (typeof updateVignette === 'function') updateVignette();
  if (typeof clearAutosave === 'function') clearAutosave();
}

// "Clear all" wipes music/photo too, so it's the most destructive action —
// guarded with the same two-tap arm as the drawer's Clear drawing. The first tap
// arms (menu stays open for the confirm); the second clears everything.
(function initClearAllMenu() {
  const item = document.getElementById('clearMenuItem');
  if (!item) return;
  let armed = false, armTimer = null;
  const label = item.querySelector('span');
  const disarm = () => { armed = false; item.classList.remove('armed'); if (label) label.textContent = 'Clear all'; };
  item.addEventListener('click', () => {
    if (recording) { showToast('Stop recording before clearing', item); return; }
    if (!armed) {
      armed = true;
      item.classList.add('armed');
      if (label) label.textContent = 'Tap again to clear all';
      clearTimeout(armTimer);
      armTimer = setTimeout(disarm, 3000);
      return;   // keep the menu open for the confirm tap
    }
    clearTimeout(armTimer);
    disarm();
    resetAll();
    closeMenu();
  });
})();

document.getElementById('saveDraftItem').addEventListener('click', () => {
  saveDraft();
  closeMenu();
});

document.getElementById('loadDraftItem').addEventListener('click', () => {
  document.getElementById('draftInput').click();
  closeMenu();
});

// Swipe-to-dismiss + tap-to-close on the mobile sheet handle
(function setupSheetGestures() {
  const sheet = document.getElementById('menuSheet');
  const handle = sheet ? sheet.querySelector('.menu-handle') : null;
  if (!sheet) return;

  let dragStartY = 0;
  let dragging = false;
  let currentY = 0;

  function onTouchStart(e) {
    // Only engage drag from the top region of the sheet (handle + header area)
    const touchY = e.touches[0].clientY;
    const rect = sheet.getBoundingClientRect();
    if (touchY - rect.top > 60) return; // only near the top
    dragging = true;
    dragStartY = touchY;
    currentY = 0;
    sheet.style.transition = 'none';
  }

  function onTouchMove(e) {
    if (!dragging) return;
    currentY = Math.max(0, e.touches[0].clientY - dragStartY);
    sheet.style.transform = `translateY(${currentY}px)`;
  }

  function onTouchEnd() {
    if (!dragging) return;
    dragging = false;
    sheet.style.transition = '';
    sheet.style.transform = '';
    if (currentY > 80) {
      closeMenu();
    }
  }

  sheet.addEventListener('touchstart', onTouchStart, { passive: true });
  sheet.addEventListener('touchmove', onTouchMove, { passive: true });
  sheet.addEventListener('touchend', onTouchEnd);

  // Tap the handle to close
  if (handle) {
    handle.addEventListener('click', (e) => {
      e.stopPropagation();
      closeMenu();
    });
  }
})();

// Close menu on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !menuOverlay.hidden) closeMenu();
  if (e.key === 'Escape' && helpDrawer && !helpDrawer.hidden) closeHelpDrawer();

  // Undo / redo shortcuts (desktop). Ignore while typing in a field.
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '') ||
                 (e.target && e.target.isContentEditable);
  if (!typing && (e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    if (e.shiftKey) { if (!redoBtn.disabled) redoBtn.click(); }
    else { if (!undoBtn.disabled) undoBtn.click(); }
  } else if (!typing && (e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
    e.preventDefault();
    if (!redoBtn.disabled) redoBtn.click();
  }
});

undoBtn.addEventListener('click', () => {
  if (undoStack.length === 0) return;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  redoStack.push(makeHistoryState());
  redoBtn.disabled = false;
  const prev = undoStack.pop();
  // Synchronous restore from the snapshot canvas (see makeHistoryState).
  // save/restore + explicit source-over/alpha guards against a stale
  // 'destination-out' left on the ctx by a just-finished eraser stroke,
  // which would make this drawImage erase instead of paint.
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(prev.image, 0, 0, cw, ch);
  ctx.restore();
  strokes = prev.strokes.slice();
  strokeGroups = prev.strokeGroups.slice();
  syncStateAfterHistoryChange(prev.hasContent === undefined ? strokes.length > 0 : prev.hasContent);
  if (undoStack.length === 0) undoBtn.disabled = true;
});

redoBtn.addEventListener('click', () => {
  if (redoStack.length === 0) return;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  undoStack.push(makeHistoryState());
  undoBtn.disabled = false;
  const next = redoStack.pop();
  // Synchronous restore from the snapshot canvas — same pattern as undo.
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(next.image, 0, 0, cw, ch);
  ctx.restore();
  strokes = next.strokes.slice();
  strokeGroups = next.strokeGroups.slice();
  syncStateAfterHistoryChange(next.hasContent === undefined ? strokes.length > 0 : next.hasContent);
  if (redoStack.length === 0) redoBtn.disabled = true;
});

const helpBtn = document.getElementById('helpBtn');       // legacy header button (now null in editor)
const helpItem = document.getElementById('helpItem');     // "How it works" — moved into the ⋯ menu
const helpDrawer = document.getElementById('helpDrawer');
const helpClose = document.getElementById('helpClose');
const helpBackdrop = document.getElementById('helpBackdrop');

let helpCloseTimer = null;

function openHelpDrawer() {
  clearTimeout(helpCloseTimer);
  document.documentElement.classList.add('help-open');   // lock page scroll (one scrollbar)
  helpDrawer.hidden = false;
  helpDrawer.classList.remove('closing');
  requestAnimationFrame(() => {
    helpDrawer.classList.add('open');
  });
}

if (helpBtn) helpBtn.addEventListener('click', openHelpDrawer);
if (helpItem) helpItem.addEventListener('click', () => { closeMenu(true); openHelpDrawer(); });

function closeHelpDrawer() {
  clearTimeout(helpCloseTimer);
  // Drop focus off the trigger so its :focus-visible ring doesn't linger (Escape).
  if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
  helpDrawer.classList.add('closing');
  helpDrawer.classList.remove('open');
  helpCloseTimer = setTimeout(() => {
    helpDrawer.hidden = true;
    helpDrawer.classList.remove('closing');
    document.documentElement.classList.remove('help-open');   // restore page scroll after it's gone
  }, 250);
}

helpClose.addEventListener('click', closeHelpDrawer);
helpBackdrop.addEventListener('click', closeHelpDrawer);

// Show the "Skribl Pad" wordmark whenever the header has room for it, and drop
// to logo-only when it doesn't (after a take, while recording, on tiny screens)
// — measured, not a fixed breakpoint, so it adapts to every state and width.
(function initBrandFit() {
  const brand = document.querySelector('.brand');
  const brandText = brand && brand.querySelector(':scope > span');
  const actions = document.getElementById('actions');
  const header = document.querySelector('.header');
  if (!brand || !brandText || !actions || !header) return;
  function fit() {
    brand.classList.remove('brand-collapsed');           // reveal, then measure
    header.classList.remove('rec-collapsed');
    // Step 1: if the wordmark makes it overflow, drop the wordmark.
    if (header.scrollWidth > header.clientWidth + 1) brand.classList.add('brand-collapsed');
    // Step 2: if it's STILL tight, shed Record's label (keep the function-critical
    // controls over decoration). The flex spacer absorbs slack, so overflow only
    // appears when it genuinely doesn't fit.
    if (header.scrollWidth > header.clientWidth + 1) header.classList.add('rec-collapsed');
  }
  const refit = () => requestAnimationFrame(fit);   // measure after layout settles
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(refit);
    ro.observe(actions);          // record→stop, post/play appearing, etc.
    ro.observe(header);           // viewport / layout changes
  } else {
    window.addEventListener('resize', refit);
  }
  // Buttons appear/disappear by toggling `hidden` — catch those too.
  if (typeof MutationObserver !== 'undefined') {
    new MutationObserver(refit).observe(actions, {
      subtree: true, childList: true, attributes: true,
      attributeFilter: ['hidden', 'class', 'style'],
    });
  }
  requestAnimationFrame(fit);
})();

// Help drawer accordions — tap a section header to expand/collapse it.
// Multiple sections can be open at once (it's a reference, not a wizard).
document.querySelectorAll('.accordion-header').forEach(header => {
  header.addEventListener('click', () => {
    const body = header.nextElementSibling;
    const isOpen = header.classList.toggle('open');
    header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    if (body && body.classList.contains('accordion-body')) {
      body.classList.toggle('open', isOpen);
    }
  });
});

// --- Music upload + trim ---
const musicInput = document.getElementById('musicInput');
const musicPanel = document.getElementById('musicPanel');
const musicRemove = document.getElementById('musicRemove');
const musicTrack = document.getElementById('musicTrack');
const musicRange = document.getElementById('musicRange');
const handleStart = document.getElementById('handleStart');
const handleEnd = document.getElementById('handleEnd');
const trimStartLabel = document.getElementById('trimStartLabel');
const trimEndLabel = document.getElementById('trimEndLabel');
const trimDurLabel = document.getElementById('trimDurLabel');
const startReadout = document.getElementById('startReadout');
const endReadout = document.getElementById('endReadout');

let audioEl = null;
let audioDuration = 0;
let trimStart = 0;
let trimEnd = 0;

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m + ':' + String(s).padStart(2, '0');
}

function formatTimeH(sec) {
  let total = Math.round(sec * 100); // work in hundredths to avoid float drift
  const hh = total % 100;
  total = (total - hh) / 100;        // whole seconds
  const s = total % 60;
  const m = Math.floor(total / 60);
  return m + ':' + String(s).padStart(2, '0') + '.' + String(hh).padStart(2, '0');
}

function updateTrimUI() {
  if (!Number.isFinite(audioDuration) || audioDuration <= 0) return;
  // Guard against NaN/invalid trim values sneaking in from a drag/nudge edge
  // case — clamp both to a valid range so a bad value can't propagate.
  if (!Number.isFinite(trimStart)) trimStart = 0;
  if (!Number.isFinite(trimEnd)) trimEnd = Math.min(audioDuration, trimStart + Math.min(20, audioDuration));
  const minLoop = 0.01;
  trimStart = Math.max(0, Math.min(trimStart, Math.max(0, audioDuration - minLoop)));
  trimEnd = Math.max(trimStart + minLoop, Math.min(trimEnd, audioDuration));
  const startPct = (trimStart / audioDuration) * 100;
  const endPct = (trimEnd / audioDuration) * 100;
  handleStart.style.left = startPct + '%';
  handleEnd.style.left = endPct + '%';
  musicRange.style.left = startPct + '%';
  musicRange.style.width = (endPct - startPct) + '%';
  // If the selection is too thin to grab a center, drop the move affordance
  // (the edge handles cover it). ~40px is roughly two handle half-widths.
  const rangePx = ((endPct - startPct) / 100) * musicTrack.getBoundingClientRect().width;
  musicRange.classList.toggle('narrow', rangePx < 40);
  trimStartLabel.textContent = formatTime(0);
  trimEndLabel.textContent = formatTime(audioDuration);
  trimDurLabel.textContent = formatTimeH(trimEnd - trimStart) + ' selected';
  // Update bubbles — hundredths, since these mark exact cut points
  if (bubbleStart) bubbleStart.textContent = formatTimeH(trimStart);
  if (bubbleEnd) bubbleEnd.textContent = formatTimeH(trimEnd);
  // Fine-tune panel readouts — 2 decimals so even a 0.01s nudge is visible
  if (startReadout) startReadout.textContent = trimStart.toFixed(2) + 's';
  if (endReadout) endReadout.textContent = trimEnd.toFixed(2) + 's';
  // Update loop summary
  const dur = trimEnd - trimStart;
  
  if (loopSummary) loopSummary.textContent = `Loop: ${formatTimeH(trimStart)} → ${formatTimeH(trimEnd)} [${dur.toFixed(2)}s]`;
  // Update zoom waveform (throttled)
  requestZoomWaveformDraw();
  updateZoomHandles();
  if (typeof updateZoomPanSlider === 'function') updateZoomPanSlider();
}

const waveformCanvas = document.getElementById('waveformCanvas');
const waveformCtx = waveformCanvas.getContext('2d');
const zoomWaveformCanvas = document.getElementById('zoomWaveformCanvas');
const zoomWaveformCtx = zoomWaveformCanvas.getContext('2d');
const loopZoomLabel = document.getElementById('loopZoomLabel');
const loopSummary = document.getElementById('loopSummary');
const playhead = document.getElementById('playhead');
const zoomPlayhead = document.getElementById('zoomPlayhead');
const zoomHandleStart = document.getElementById('zoomHandleStart');
const zoomHandleEnd = document.getElementById('zoomHandleEnd');
const zoomTrackWrap = document.getElementById('zoomTrackWrap');

// --- Loop-detail magnification -------------------------------------------
// ONE source of truth for the zoom window, replacing the context formula that
// used to be duplicated across updateZoomHandles / dragZoomHandle /
// drawZoomWaveform. zoomFocus centers the window on the whole loop, the start
// edge, or the end edge; zoomMag tightens it so a boundary can be pushed right
// up against the waveform (down to a few ms per pixel at 8x).
let zoomMag = 1;
let zoomFocus = 'loop';   // 'loop' | 'start' | 'end' | 'free'
let zoomCenter = null;    // explicit pan center (seconds); null = derive from focus
function getZoomWindow() {
  const loopDuration = Math.max(0, trimEnd - trimStart);
  const contextSeconds = Math.max(1, Math.min(4, loopDuration * 0.25));
  const halfSpan = (loopDuration / 2 + contextSeconds) / zoomMag;
  // Panning (drag / slider) sets an explicit center; otherwise the focus anchor
  // (whole loop / start edge / end edge) decides it. Either way the center is
  // clamped so the window never runs off the ends of the song.
  let center;
  if (zoomCenter != null) center = zoomCenter;
  else if (zoomFocus === 'start') center = trimStart;
  else if (zoomFocus === 'end') center = trimEnd;
  else center = (trimStart + trimEnd) / 2;
  const lo = halfSpan;
  const hi = Math.max(halfSpan, audioDuration - halfSpan);
  center = Math.max(lo, Math.min(center, hi));
  let start = Math.max(0, center - halfSpan);
  let end = Math.min(audioDuration, center + halfSpan);
  if (end - start < 0.001) end = Math.min(audioDuration, start + 0.001);
  return { start, end, duration: Math.max(0.001, end - start) };
}

// Reflect the active focus anchor on the Loop/Start/End buttons; nothing is
// highlighted while free-panning ('free'). Called when panning takes over.
function syncZoomFocusButtons() {
  document.querySelectorAll('.zoom-mag-btn[data-focus]').forEach(b => {
    b.classList.toggle('active', zoomFocus !== 'free' && b.dataset.focus === zoomFocus);
  });
}

function updateZoomHandles() {
  if (!zoomTrackWrap || !zoomHandleStart || !zoomHandleEnd) return;
  if (!Number.isFinite(audioDuration) || audioDuration <= 0) return;
  const zw = getZoomWindow();
  const zoomStartTime = zw.start;
  const zoomDuration = zw.duration;

  const startPct = ((trimStart - zoomStartTime) / zoomDuration) * 100;
  const endPct = ((trimEnd - zoomStartTime) / zoomDuration) * 100;

  zoomHandleStart.style.left = startPct + '%';
  zoomHandleEnd.style.left = endPct + '%';
  // Hide a handle that has scrolled outside the magnified window (e.g. the far
  // edge when you're zoomed in on the other one).
  zoomHandleStart.hidden = !(startPct >= -2 && startPct <= 102);
  zoomHandleEnd.hidden = !(endPct >= -2 && endPct <= 102);
}

function dragZoomHandle(handle, isStart) {
  function onStart(e) {
    e.preventDefault();
    handle.classList.add('dragging');

    function onMove(ev) {
      const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const rect = zoomTrackWrap.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const zoom = getZoomWindow();
      const time = zoom.start + pct * (zoom.end - zoom.start);

      if (isStart) {
        trimStart = Math.max(0, Math.min(time, trimEnd - 0.5));
        if (trimEnd - trimStart > 20) trimEnd = trimStart + 20;
      } else {
        trimEnd = Math.min(audioDuration, Math.max(time, trimStart + 0.5));
        if (trimEnd - trimStart > 20) trimStart = trimEnd - 20;
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

// Sliding-pill highlight for segmented button groups — the same affordance as
// the draw/eraser tool slider, generalized so it can be attached to any group.
// It injects an absolutely-positioned pill as the group's first child and slides
// it under whichever button carries `.active`. A group with NO active button
// (e.g. the Loop/Start/End focus row while free-panning) hides the pill. It
// repositions on active-state changes (MutationObserver) and when the group
// resizes or first becomes visible from a hidden tab/drawer (ResizeObserver);
// both are feature-detected so the headless harness — which stubs neither — runs
// this file top-level without throwing.
function positionSegSlider(group) {
  if (!group) return;
  const pill = group.__segPill;
  if (!pill) return;
  const btns = Array.prototype.slice.call(group.querySelectorAll('button'));
  let idx = -1;
  for (let i = 0; i < btns.length; i++) {
    if (btns[i].classList.contains('active')) idx = i;
  }
  const activeBtn = idx >= 0 ? btns[idx] : null;
  // No selection, or the group is still collapsed (zero-width) — keep it hidden
  // and let the next reflow place it once it has real layout.
  if (!activeBtn || !activeBtn.offsetWidth) { pill.style.opacity = '0'; return; }
  // Measure from the first button via offsetLeft so any inter-button `gap`
  // (the zoom groups use gap:2px) is included. Summing widths alone drifts the
  // pill left by one gap per button. The pill at translateX(0) sits under btn 0.
  const offset = activeBtn.offsetLeft - btns[0].offsetLeft;
  pill.style.width = activeBtn.offsetWidth + 'px';
  pill.style.transform = 'translateX(' + offset + 'px)';
  pill.style.opacity = '1';
}

function attachSegSlider(group) {
  if (!group || group.__segAttached) return;
  group.__segAttached = true;
  const pill = document.createElement('div');
  pill.className = 'seg-slider';
  group.insertBefore(pill, group.firstChild);
  group.__segPill = pill;
  const reflow = () => positionSegSlider(group);
  // Active-state changes (clicks, syncZoomFocusButtons, the programmatic 'free'
  // state) all flip the `active` class — observing it keeps the pill in sync
  // without threading a call through every one of those code paths.
  if (typeof MutationObserver !== 'undefined') {
    new MutationObserver(reflow).observe(group, {
      subtree: true, attributes: true, attributeFilter: ['class'],
    });
  }
  // Fires when the group gains size (revealed from a hidden panel) and on
  // viewport resize, so the pill lands correctly the first time it's seen.
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(reflow).observe(group);
  } else if (window.addEventListener) {
    window.addEventListener('resize', reflow);
  }
  reflow();
}

// Focus + magnification control for the Loop Detail view. Built in JS (styles
// injected once) so the whole feature lives in this one file. Focus centers the
// zoom window on the loop / start edge / end edge; the multiplier tightens it.
(function initZoomMagControl() {
  if (!zoomTrackWrap || !zoomTrackWrap.parentNode) return;
  const bar = document.createElement('div');
  bar.className = 'zoom-mag-bar';
  bar.innerHTML =
    '<div class="zoom-mag-group" data-role="focus">' +
      '<button type="button" class="zoom-mag-btn active" data-focus="loop">Loop</button>' +
      '<button type="button" class="zoom-mag-btn" data-focus="start">Start</button>' +
      '<button type="button" class="zoom-mag-btn" data-focus="end">End</button>' +
    '</div>' +
    '<div class="zoom-mag-group" data-role="mag">' +
      '<button type="button" class="zoom-mag-btn active" data-mag="1">1&times;</button>' +
      '<button type="button" class="zoom-mag-btn" data-mag="2">2&times;</button>' +
      '<button type="button" class="zoom-mag-btn" data-mag="4">4&times;</button>' +
      '<button type="button" class="zoom-mag-btn" data-mag="8">8&times;</button>' +
    '</div>';
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-mag-group[data-role="focus"]'));
  attachSegSlider(bar.querySelector('.zoom-mag-group[data-role="mag"]'));
  bar.addEventListener('click', (e) => {
    const b = e.target.closest('.zoom-mag-btn');
    if (!b) return;
    b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    if (b.dataset.focus) { zoomFocus = b.dataset.focus; zoomCenter = null; }
    if (b.dataset.mag) zoomMag = parseFloat(b.dataset.mag) || 1;
    updateTrimUI();   // recomputes the window, redraws waveform + handles
  });
  const style = document.createElement('style');
  style.textContent =
    '.zoom-mag-bar{display:flex;gap:10px;justify-content:space-between;align-items:center;margin:8px 0 6px;flex-wrap:wrap}' +
    '.zoom-mag-group{position:relative;overflow:hidden;display:inline-flex;gap:2px;background:#13161c;border:1px solid rgba(255,255,255,.055);border-radius:8px;padding:3px}' +
    '.zoom-mag-btn{position:relative;z-index:1;appearance:none;-webkit-appearance:none;border:0;background:transparent;color:#8a93a6;font:inherit;font-size:12px;line-height:1;padding:5px 9px;border-radius:6px;cursor:pointer;transition:color .12s}' +
    '.zoom-mag-btn:hover{color:#c8cede}' +
    '.zoom-mag-btn.active{color:#fff}';
  document.head.appendChild(style);
})();

// Fine-tune disclosure: the Music panel opens to essentials (waveform + trim +
// Match/Preview); the deep Loop Detail (zoom, focus/magnifier, nudgers) lives
// behind this toggle so all three tab panels share the same "essentials shown,
// depth one tap away" rhythm. Null-guarded — the player shell has no toggle.
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
          body.querySelectorAll('.zoom-mag-group').forEach(g => positionSegSlider(g));
        }
      });
    }
  });
})();
const bubbleStart = document.getElementById('bubbleStart');
const bubbleEnd = document.getElementById('bubbleEnd');
let audioCtx = null;
let currentAudioBuffer = null;
let loopCrossfadeMs = 0;   // loop crossfade length in ms (0 = off); see buildTrimmedLoopWav

let zoomDrawPending = false;

function requestZoomWaveformDraw() {
  if (zoomDrawPending) return;
  zoomDrawPending = true;
  requestAnimationFrame(() => {
    zoomDrawPending = false;
    drawZoomWaveform();
  });
}

function drawZoomWaveform() {
  if (!currentAudioBuffer || !zoomWaveformCanvas) return;
  const rect = zoomWaveformCanvas.getBoundingClientRect();
  if (!rect.width) return;
  const dpr = window.devicePixelRatio || 1;
  zoomWaveformCanvas.width = Math.round(rect.width * dpr);
  zoomWaveformCanvas.height = Math.round(rect.height * dpr);
  zoomWaveformCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = rect.width;
  const h = rect.height;
  const mid = h / 2;

  // Window comes from the shared helper (focus + magnification aware).
  const loopDuration = trimEnd - trimStart;
  const zw = getZoomWindow();
  const zoomStartTime = zw.start;
  const zoomEndTime = zw.end;
  const zoomDuration = zw.duration;

  // Background
  zoomWaveformCtx.fillStyle = '#161a22';
  zoomWaveformCtx.fillRect(0, 0, w, h);

  const data = currentAudioBuffer.getChannelData(0);
  const sampleRate = currentAudioBuffer.sampleRate;
  const startSample = Math.max(0, Math.floor(zoomStartTime * sampleRate));
  const endSample = Math.min(data.length, Math.floor(zoomEndTime * sampleRate));
  const totalSamples = Math.max(1, endSample - startSample);
  const samplesPerPixel = Math.max(1, Math.floor(totalSamples / w));

  // Draw full waveform in muted color
  zoomWaveformCtx.fillStyle = '#3a4150';
  for (let x = 0; x < w; x++) {
    const sStart = startSample + x * samplesPerPixel;
    const sEnd = Math.min(sStart + samplesPerPixel, endSample);
    let min = 1, max = -1;
    for (let i = sStart; i < sEnd; i++) {
      const v = data[i] || 0;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    const y1 = mid + min * mid * 0.9;
    const y2 = mid + max * mid * 0.9;
    zoomWaveformCtx.fillRect(x, y1, 1, Math.max(1, y2 - y1));
  }

  // Highlight the selected loop region
  const loopStartX = ((trimStart - zoomStartTime) / zoomDuration) * w;
  const loopEndX = ((trimEnd - zoomStartTime) / zoomDuration) * w;

  zoomWaveformCtx.fillStyle = 'rgba(124, 92, 255, 0.2)';
  zoomWaveformCtx.fillRect(loopStartX, 0, loopEndX - loopStartX, h);

  // Redraw loop section waveform in purple
  zoomWaveformCtx.fillStyle = '#7c5cff';
  for (let x = Math.floor(loopStartX); x < Math.ceil(loopEndX); x++) {
    const sStart = startSample + x * samplesPerPixel;
    const sEnd = Math.min(sStart + samplesPerPixel, endSample);
    let min = 1, max = -1;
    for (let i = sStart; i < sEnd; i++) {
      const v = data[i] || 0;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    const y1 = mid + min * mid * 0.9;
    const y2 = mid + max * mid * 0.9;
    zoomWaveformCtx.fillRect(x, y1, 1, Math.max(1, y2 - y1));
  }

  // Loop boundary lines
  zoomWaveformCtx.fillStyle = '#7c5cff';
  zoomWaveformCtx.fillRect(loopStartX, 0, 2, h);
  zoomWaveformCtx.fillRect(loopEndX - 2, 0, 2, h);

  // Crossfade region (bake-only). The posted/exported loop folds its TAIL over
  // its HEAD (equal-power), so the last `xfade` of the loop is blended into the
  // first `xfade`. Shade both bands in amber and dash their inner edges, using
  // the SAME xfadeFrames clamp as bake time (see buildTrimmedLoopWav) so the
  // picture matches exactly what gets posted — including the "can't exceed half
  // the loop" cap.
  if (loopCrossfadeMs > 0 && loopDuration > 0) {
    const loopFrames = Math.floor(loopDuration * sampleRate);
    const xfadeFrames = Math.min(
      Math.floor((loopCrossfadeMs / 1000) * sampleRate),
      Math.floor(loopFrames / 2)
    );
    const xfadeW = ((xfadeFrames / sampleRate) / zoomDuration) * w;
    if (xfadeW > 0) {
      const headX = loopStartX;          // fade-in: the loop tail is mixed in here
      const tailX = loopEndX - xfadeW;    // folded over the head / trimmed from the end
      zoomWaveformCtx.fillStyle = 'rgba(255, 176, 32, 0.22)';
      zoomWaveformCtx.fillRect(headX, 0, xfadeW, h);
      zoomWaveformCtx.fillRect(tailX, 0, xfadeW, h);
      zoomWaveformCtx.fillStyle = 'rgba(255, 176, 32, 0.9)';
      for (let yy = 0; yy < h; yy += 9) {
        zoomWaveformCtx.fillRect(headX + xfadeW - 1, yy, 1.5, 5);
        zoomWaveformCtx.fillRect(tailX, yy, 1.5, 5);
      }
    }
  }

  // Center line
  zoomWaveformCtx.fillStyle = '#2e3340';
  zoomWaveformCtx.fillRect(0, mid, w, 1);

  if (loopZoomLabel) {
    const xfLabel = loopCrossfadeMs > 0 ? `  ·  xfade ${loopCrossfadeMs}ms` : '';
    loopZoomLabel.textContent = `${formatTimeH(trimStart)} → ${formatTimeH(trimEnd)} [${loopDuration.toFixed(2)}s]${xfLabel}`;
  }
}

function drawWaveform(audioBuffer) {
  const rect = musicTrack.getBoundingClientRect();
  waveformCanvas.width = rect.width;
  waveformCanvas.height = rect.height;

  const data = audioBuffer.getChannelData(0);
  const samples = waveformCanvas.width;
  const blockSize = Math.floor(data.length / samples);
  const peaks = [];

  for (let i = 0; i < samples; i++) {
    const start = i * blockSize;
    let min = 1.0, max = -1.0;
    for (let j = 0; j < blockSize; j++) {
      const v = data[start + j] || 0;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    peaks.push([min, max]);
  }

  const h = waveformCanvas.height;
  const mid = h / 2;
  waveformCtx.clearRect(0, 0, waveformCanvas.width, h);
  waveformCtx.fillStyle = '#3a4150';
  for (let i = 0; i < peaks.length; i++) {
    const [min, max] = peaks[i];
    const y1 = mid + min * mid * 0.85;
    const y2 = mid + max * mid * 0.85;
    waveformCtx.fillRect(i, y1, 1, Math.max(1, y2 - y1));
  }
}

const musicUploadBtn = document.getElementById('musicUploadBtn');
const musicBtnLabel = document.getElementById('musicBtnLabel');
const musicDetail = document.getElementById('musicDetail');
const musicTabDot = document.getElementById('musicTabDot');

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

musicInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  const err = validateMusicFile(file);
  if (err) { showToast(err, musicUploadBtn); return; }
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

const toast = document.getElementById('toast');
let toastTimer = null;

function showToast(msg, anchorEl) {
  toast.hidden = false;
  toast.textContent = msg;
  toast.style.bottom = '';
  toast.style.top = '';

  if (anchorEl) {
    toast.style.position = 'absolute';
    const appRect = document.querySelector('.app').getBoundingClientRect();
    const rect = anchorEl.getBoundingClientRect();
    const mid = rect.top - appRect.top + rect.height / 2;
    // Position above or below the anchor depending on space
    if (mid > appRect.height / 2) {
      toast.style.top = (rect.top - appRect.top - 50) + 'px';
      toast.style.bottom = 'auto';
    } else {
      toast.style.top = (rect.bottom - appRect.top + 10) + 'px';
      toast.style.bottom = 'auto';
    }
  } else {
    // No anchor → pin to the top of the viewport so it's always visible,
    // even when the app is taller than the screen and scrolled.
    toast.style.position = 'fixed';
    toast.style.top = 'calc(16px + env(safe-area-inset-top))';
    toast.style.bottom = 'auto';
  }

  requestAnimationFrame(() => toast.classList.add('show'));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => { toast.hidden = true; }, 200);
  }, 2800);
}

function validateMusicFile(file) {
  if (!file) return 'No file selected.';
  const okType = file.type && file.type.startsWith('audio/');
  const okExt = /\.(mp3|m4a|wav|ogg|aac)$/i.test(file.name || '');
  if (!okType && !okExt) return 'Please choose an audio file (mp3, m4a, wav, etc).';
  return null;
}

function isImageFile(file) {
  const okType = file.type && file.type.startsWith('image/');
  const okExt = /\.(jpe?g|png|gif|webp)$/i.test(file.name || '');
  return okType || okExt;
}

function setLoopToDrawingLength() {
  if (!audioEl || !strokes.length) return;
  const drawingSeconds = getPlaybackDuration() / 1000;
  const loopLength = Math.min(20, Math.max(0.5, Math.min(drawingSeconds, audioDuration)));
  // Resize in place: keep the current start, just change the length. Only pull
  // the start back if the loop would otherwise run past the end of the song.
  trimEnd = trimStart + loopLength;
  if (trimEnd > audioDuration) {
    trimEnd = audioDuration;
    trimStart = Math.max(0, trimEnd - loopLength);
  }
  updateTrimUI();
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
  document.getElementById('photoOpacityVal').textContent = '100%';
  updateSliderFill(opEl);
  const blEl = document.getElementById('photoBlur');
  if (blEl) {
    blEl.value = 0;
    document.getElementById('photoBlurVal').textContent = '0px';
    updateSliderFill(blEl);
  }
  document.querySelectorAll('.photo-fit-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.fit === 'cover');
  });
  initPhotoFitSlider();
  updateRepositionUI();
}

musicRemove.addEventListener('click', (e) => {
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
      if (isStart) {
        trimStart = Math.min(time, trimEnd - 0.5);
        trimStart = Math.max(0, trimStart);
        if (trimEnd - trimStart > 20) trimStart = trimEnd - 20;
      } else {
        trimEnd = Math.max(time, trimStart + 0.5);
        trimEnd = Math.min(audioDuration, trimEnd);
        if (trimEnd - trimStart > 20) trimEnd = trimStart + 20;
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

// Drag the middle of the selection to slide the whole loop window along the
// song, keeping its length locked. Edges (handles) still resize independently
// because they sit above the range in z-order. Stops at the song boundaries.
function dragRangeWindow(rangeEl) {
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

// --- Loop preview & test seam ---
const previewLoopBtn = document.getElementById('previewLoopBtn');
const testSeamBtn = document.getElementById('testSeamBtn');
const matchDrawingBtn = document.getElementById('matchDrawingBtn');

const nudgeSteps = [0.01, 0.02, 0.05, 0.1];
let nudgeStepIdx = 3;
const nudgeStepLabel = document.getElementById('nudgeStepLabel');
const nudgeStepFinerBtn = document.getElementById('nudgeStepFiner');
const nudgeStepCoarserBtn = document.getElementById('nudgeStepCoarser');

function updateNudgeStepLabel() {
  nudgeStepLabel.textContent = nudgeSteps[nudgeStepIdx] + 's';
  nudgeStepFinerBtn.disabled = nudgeStepIdx === 0;
  nudgeStepCoarserBtn.disabled = nudgeStepIdx === nudgeSteps.length - 1;
}

nudgeStepFinerBtn.addEventListener('click', () => {
  nudgeStepIdx = Math.max(0, nudgeStepIdx - 1);
  updateNudgeStepLabel();
});

nudgeStepCoarserBtn.addEventListener('click', () => {
  nudgeStepIdx = Math.min(nudgeSteps.length - 1, nudgeStepIdx + 1);
  updateNudgeStepLabel();
});

function nudgeTrim(which, direction) {
  if (!audioEl) return;
  // Guard against a stray caller (e.g. a button without data-which/amount):
  // a NaN amount would corrupt trimEnd and make updateTrimUI reset the loop.
  if ((which !== 'start' && which !== 'end') || !Number.isFinite(direction)) return;
  const amount = direction * nudgeSteps[nudgeStepIdx];
  if (which === 'start') {
    trimStart = Math.max(0, Math.min(trimStart + amount, trimEnd - 0.5));
    if (trimEnd - trimStart > 20) trimEnd = trimStart + 20;
  } else {
    trimEnd = Math.min(audioDuration, Math.max(trimEnd + amount, trimStart + 0.5));
    if (trimEnd - trimStart > 20) trimStart = trimEnd - 20;
  }
  updateTrimUI();
}

// Only the loop-edge nudgers carry data-which; scope to them so the step-size
// +/- buttons (which share the .nudge-btn class) can't trigger a trim nudge.
document.querySelectorAll('.nudge-btn[data-which]').forEach(btn => {
  btn.addEventListener('click', () => {
    nudgeTrim(btn.dataset.which, parseFloat(btn.dataset.amount));
  });
});

matchDrawingBtn.addEventListener('click', setLoopToDrawingLength);

document.getElementById('resetPhotoBtn').addEventListener('click', resetPhotoAdjustments);
let previewingLoop = false;
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
  previewingLoop = true;
  previewLoopBtn.textContent = 'Stop Preview';
  try { audioEl.pause(); } catch (e) {}   // keep the raw source from playing underneath

  // Primary path: sample-accurate Web Audio loop of the exact posted clip.
  // Gapless + drift-free. Playhead reads the audio clock, mapped to song time.
  if (startWebAudioLoop()) {
    previewLoopTimer = setInterval(() => {
      if (!previewingLoop || !_waLoopSource) return;
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

function playMusicLooped(totalDurationMs, onStarted) {
  if (!audioEl) {
    if (onStarted) onStarted();
    return;
  }
  if (playhead) playhead.hidden = false;

  // Primary: sample-accurate Web Audio loop (gapless, drift-free) — the same
  // clip the post uses. The drawing replay (onStarted) starts immediately in
  // lockstep. The interval only drives the playhead + the total-time stop.
  if (startWebAudioLoop()) {
    if (onStarted) onStarted();
    let elapsedWA = 0;
    const loopCheckWA = setInterval(() => {
      if (!playing) { stopWebAudioLoop(); if (playhead) playhead.hidden = true; clearInterval(loopCheckWA); return; }
      elapsedWA += 100;
      const songTime = webAudioLoopSongTime();
      if (playhead) playhead.style.left = (songTime / audioDuration * 100) + '%';
      if (elapsedWA >= totalDurationMs) { stopWebAudioLoop(); if (playhead) playhead.hidden = true; clearInterval(loopCheckWA); }
    }, 100);
    return;
  }

  // Fallback: original timer-wrapped source loop (if Web Audio unavailable).
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
    elapsed += 100;
    if (audioEl.currentTime >= trimEnd - 0.05) {
      audioEl.currentTime = trimStart;
      audioEl.play();
    }
    const pct = (audioEl.currentTime / audioDuration) * 100;
    if (playhead) {
      playhead.style.left = pct + '%';
    }
    if (elapsed >= totalDurationMs) {
      audioEl.pause();
      if (playhead) playhead.hidden = true;
      clearInterval(loopCheck);
    }
  }, 100);
}

// --- Eraser cursor ---
function updateEraserCursor(x, y) {
  // size is in authored (logical) px; the canvas may be displayed smaller, so
  // scale the on-screen cursor to match the real erased footprint.
  const rect = canvas.getBoundingClientRect();
  const lg = getCanvasLogicalSize();
  const scale = lg.width > 0 && rect.width > 0 ? rect.width / lg.width : 1;
  const cursorSize = size * 3 * scale;
  eraserCursor.style.width = cursorSize + 'px';
  eraserCursor.style.height = cursorSize + 'px';
  eraserCursor.style.left = x + 'px';
  eraserCursor.style.top = y + 'px';
}

canvasWrap.addEventListener('mousemove', (e) => {
  if (tool !== 'eraser') return;
  if (finishedRecording && !recording) { eraserCursor.style.display = 'none'; return; }
  const rect = canvas.getBoundingClientRect();
  updateEraserCursor(e.clientX - rect.left, e.clientY - rect.top);
  eraserCursor.style.display = 'block';
});

canvasWrap.addEventListener('mouseleave', () => {
  eraserCursor.style.display = 'none';
});

canvasWrap.addEventListener('touchmove', (e) => {
  if (tool !== 'eraser') return;
  if (finishedRecording && !recording) { eraserCursor.style.display = 'none'; return; }
  const rect = canvas.getBoundingClientRect();
  const touch = e.touches[0];
  updateEraserCursor(touch.clientX - rect.left, touch.clientY - rect.top);
  eraserCursor.style.display = 'block';
}, { passive: true });

canvasWrap.addEventListener('touchend', () => {
  eraserCursor.style.display = 'none';
});
const photoUploadBtn = document.getElementById('photoUploadBtn');
const photoBgImg = document.getElementById('photoBgImg');
const photoInput = document.getElementById('photoInput');
const photoFitSlider = document.getElementById('photoFitSlider');

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

// ── Photo import / normalization ────────────────────────────────────────────
// A freshly imported photo is downscaled + recompressed to JPEG right here, at
// the import boundary, so drafts/posts stay small. This is the ONLY place a
// photo is normalized; everything downstream (serializeSkribl, saveDraft, the
// player, export) keeps consuming the same photo.data data-URL shape unchanged.
// loadSkribl does NOT re-normalize — the data it loads is already normalized,
// and re-encoding would compound JPEG loss on every open.
const PHOTO_MAX_EDGE = 2048;       // cap the longest edge (px); never upscales
const PHOTO_JPEG_QUALITY = 0.85;   // quality-first baseline; tune after on-device bytes
// WebP beats JPEG ~25-30% at the same quality and — unlike JPEG — keeps alpha,
// so transparent backgrounds no longer fall back to (potentially huge) lossless
// PNG. Used only when the browser can actually encode WebP (see canEncodeWebP);
// otherwise we keep the JPEG/PNG path. The alpha branch runs a touch higher
// because canvas WebP is lossy even near 1.0, and hard sticker/line-art edges
// soften at lower quality.
const PHOTO_WEBP_QUALITY = 0.85;        // opaque photos
const PHOTO_WEBP_ALPHA_QUALITY = 0.92;  // transparent images — protect crisp edges

// Feature-detect WebP *encoding* once (decoding support is broader). Per the
// canvas spec, toDataURL silently returns PNG for any unsupported type, so we
// ask a 1x1 canvas for WebP and check the prefix: a 'data:image/webp' answer
// means real support. Cached — the answer can't change within a session.
let _webpEncodeSupported = null;
function canEncodeWebP() {
  if (_webpEncodeSupported !== null) return _webpEncodeSupported;
  try {
    const c = document.createElement('canvas');
    c.width = 1; c.height = 1;
    _webpEncodeSupported = c.toDataURL('image/webp').indexOf('data:image/webp') === 0;
  } catch (e) {
    _webpEncodeSupported = false;
  }
  return _webpEncodeSupported;
}

// Pure geometry: target draw size preserving aspect ratio, never upscaling.
// Mirrored by tooling/photo_resize_test.js — keep that copy in sync if you edit.
function photoTargetDims(w, h, maxEdge) {
  if (!w || !h) return { w: w || 0, h: h || 0 };
  const longest = Math.max(w, h);
  if (longest <= maxEdge) return { w: w, h: h };   // already small — no upscale
  const scale = maxEdge / longest;
  return { w: Math.round(w * scale), h: Math.round(h * scale) };
}

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

photoInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (!isImageFile(file)) {
    showToast('Please choose an image file — jpg, png, gif, or webp', photoUploadBtn);
    photoInput.value = '';
    return;
  }
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

document.getElementById('photoRemove').addEventListener('click', (e) => {
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

const photoFitBtns = document.querySelectorAll('.photo-fit-btn');

function initPhotoFitSlider() {
  const active = document.querySelector('.photo-fit-btn.active');
  if (active && photoFitSlider) {
    photoFitSlider.style.width = active.offsetWidth + 'px';
    photoFitSlider.style.transform = 'translateX(0)';
  }
}
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

// ===== Photo reposition (Fill mode) ========================================
// Fill (object-fit: cover) crops the photo; dragging picks which part shows.
// On screen this is CSS object-position; export mirrors it with the same
// fraction (see drawPhotoFitted / the WebM compositor). object-position p% for
// cover places the image at (box - scaledImage) * p, which is exactly the
// export offset (w-dw)*p — so screen and export always agree. Only meaningful
// for cover, so we center for Fit/Stretch and hide the control there.
function applyPhotoPosition() {
  if (!photoBgImg) return;
  const cover = photoFit === 'cover';
  const ox = cover ? photoOffsetX : 0.5;
  const oy = cover ? photoOffsetY : 0.5;
  const z = cover ? photoZoom : 1;
  photoBgImg.style.objectPosition = (ox * 100) + '% ' + (oy * 100) + '%';
  // Zoom scales the covered image about the same focal fraction the offset uses,
  // which matches the export math exactly (dw = iw*cover*zoom, x = (w-dw)*ox).
  photoBgImg.style.transformOrigin = (ox * 100) + '% ' + (oy * 100) + '%';
  photoBgImg.style.transform = z !== 1 ? 'scale(' + z + ')' : '';
}

function enterReposition() {
  if (recording) { showToast('Stop recording to reposition the photo', document.getElementById('repositionBtn')); return; }
  repositioning = true;
  const btn = document.getElementById('repositionBtn');
  if (btn) { btn.classList.add('active'); btn.setAttribute('aria-pressed', 'true'); }
  canvasWrap.classList.add('repositioning');
  canvas.style.cursor = 'grab';   // beats any inline lock/eraser cursor on the canvas
  showToast('Drag the photo to choose what shows', document.getElementById('repositionBtn'));
}

function exitReposition() {
  repositioning = false;
  const btn = document.getElementById('repositionBtn');
  if (btn) { btn.classList.remove('active'); btn.setAttribute('aria-pressed', 'false'); }
  canvasWrap.classList.remove('repositioning');
  updateCanvasLockCue();          // restore the correct canvas cursor (lock/eraser/normal)
}

// Show the control only when a photo is loaded AND in Fill AND not recording.
// Leaving those conditions also drops us out of reposition mode.
function updateRepositionUI() {
  const btn = document.getElementById('repositionBtn');
  if (!btn) return;
  const loaded = photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src;
  const available = !!loaded && photoFit === 'cover';   // show whenever Fill + image loaded
  const enabled = available && !recording;              // interactive only before you draw
  btn.hidden = !available;
  btn.disabled = !enabled;
  const zoomRow = document.getElementById('photoZoomRow');
  if (zoomRow) zoomRow.hidden = !available;
  const zoom = document.getElementById('photoZoom');
  if (zoom) zoom.disabled = !enabled;
  const hint = document.getElementById('repositionHint');
  if (hint) {
    hint.hidden = !available;
    hint.textContent = enabled
      ? 'In Fill, parts of your image may be cropped. Drag the image to choose which part shows behind your drawing.'
      : 'Stop recording to reposition the image.';
  }
  if (!enabled && repositioning) exitReposition();
}

// Clamp a restored zoom to the valid 1..3 range — a bad/hand-edited draft or
// stale localStorage could otherwise push photoZoom outside the slider's range.
function clampPhotoZoom(v) {
  v = Number(v);
  return Number.isFinite(v) ? Math.max(1, Math.min(3, v)) : 1;
}

// Reflect photoZoom onto the Zoom slider UI (used on load / re-add / reset).
function setZoomSliderUI() {
  const z = document.getElementById('photoZoom');
  if (!z) return;
  const pct = Math.round(photoZoom * 100);
  z.value = pct;
  const v = document.getElementById('photoZoomVal');
  if (v) v.textContent = pct + '%';
  if (typeof updateSliderFill === 'function') updateSliderFill(z);
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
  const up = () => {
    window.removeEventListener('mousemove', move);
    window.removeEventListener('mouseup', up);
    window.removeEventListener('touchmove', move);
    window.removeEventListener('touchend', up);
    window.removeEventListener('touchcancel', up);
    if (typeof scheduleAutosave === 'function') scheduleAutosave();
  };
  window.addEventListener('mousemove', move);
  window.addEventListener('mouseup', up);
  window.addEventListener('touchmove', move, { passive: false });
  window.addEventListener('touchend', up);
  window.addEventListener('touchcancel', up);
}

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

// Paint the WebKit track fill up to the thumb (Chrome/Safari have no native
// progress element). Firefox uses ::-moz-range-progress and ignores this.
function updateSliderFill(input) {
  const min = parseFloat(input.min) || 0;
  const max = parseFloat(input.max) || 100;
  const pct = ((parseFloat(input.value) - min) / (max - min)) * 100;
  input.style.setProperty('--slider-fill', pct + '%');
}

// Blur lives on the same filter property; keep it as the single source.
function applyPhotoFilter() {
  photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
}

const photoOpacityEl = document.getElementById('photoOpacity');
const photoBlurEl = document.getElementById('photoBlur');
const photoBlurValEl = document.getElementById('photoBlurVal');

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

// Set initial track fills so both sliders render correctly before any input
updateSliderFill(photoOpacityEl);
updateSliderFill(photoBlurEl);

// ===== Slider nudgers + Loop Detail pan + crossfade control =================
// Three related additions, all self-contained (DOM + CSS injected here so the
// whole feature lives in this file and neither HTML template needs editing):
//   (1) +/- buttons on every range slider, for exact incremental control since
//       a slider alone can't land on a precise value on a phone.
//   (2) Scroll the Loop Detail window anywhere along the song — drag the
//       waveform or use a scroll slider — instead of only the Loop/Start/End
//       anchors. Adds a pan center to getZoomWindow (already wired above).
//   (3) A loop crossfade length control (bake-only — see buildTrimmedLoopWav).

// Wrap an existing <input type=range> with - / + buttons. Each press steps the
// value (press-and-hold repeats) and dispatches a native 'input' event so every
// existing listener (value label, track fill, autosave) fires unchanged. Pass
// opts.step for a fixed step, or opts.nudgeFn(dir) for custom behavior (pan).
function addSliderNudgers(input, opts) {
  opts = opts || {};
  if (!input || input.dataset.nudged) return;
  input.dataset.nudged = '1';
  const parent = input.parentNode;
  const wrap = document.createElement('div');
  wrap.className = 'slider-nudge-wrap';
  parent.insertBefore(wrap, input);
  const minus = document.createElement('button');
  const plus = document.createElement('button');
  minus.type = plus.type = 'button';
  minus.className = 'slider-nudge-btn';
  plus.className = 'slider-nudge-btn';
  minus.textContent = '\u2212';
  plus.textContent = '+';
  minus.setAttribute('aria-label', 'Decrease');
  plus.setAttribute('aria-label', 'Increase');
  wrap.appendChild(minus);
  wrap.appendChild(input);   // move the slider between the buttons
  wrap.appendChild(plus);
  const step = opts.step != null ? opts.step : (parseFloat(input.step) || 1);
  function apply(dir) {
    if (opts.nudgeFn) { opts.nudgeFn(dir); return; }
    const min = parseFloat(input.min) || 0;
    const maxRaw = parseFloat(input.max);
    const max = Number.isFinite(maxRaw) ? maxRaw : Infinity;
    let next = (parseFloat(input.value) || 0) + dir * step;
    next = Math.max(min, Math.min(next, max));
    next = Math.round(next / step) * step;
    input.value = next;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function bind(btn, dir) {
    let holdTimer = null, repeat = null;
    const start = (e) => {
      e.preventDefault();
      apply(dir);
      holdTimer = setTimeout(() => { repeat = setInterval(() => apply(dir), 90); }, 350);
    };
    const end = () => { clearTimeout(holdTimer); if (repeat) clearInterval(repeat); repeat = null; };
    btn.addEventListener('mousedown', start);
    btn.addEventListener('touchstart', start, { passive: false });
    btn.addEventListener('mouseup', end);
    btn.addEventListener('mouseleave', end);
    btn.addEventListener('touchend', end);
    btn.addEventListener('touchcancel', end);
  }
  bind(minus, -1);
  bind(plus, 1);
}

// Sync the crossfade slider + label from loopCrossfadeMs (load / re-add / reset).
function setCrossfadeUI() {
  const s = document.getElementById('crossfadeSlider');
  const v = document.getElementById('crossfadeVal');
  if (s) { s.value = loopCrossfadeMs; if (typeof updateSliderFill === 'function') updateSliderFill(s); }
  if (v) v.textContent = loopCrossfadeMs > 0 ? loopCrossfadeMs + ' ms' : 'Off';
}

// Reflect the current zoom-window center onto the pan slider (called from
// updateTrimUI). No-op until the slider is injected.
function updateZoomPanSlider() {
  const s = document.getElementById('zoomPanSlider');
  if (!s) return;
  if (!Number.isFinite(audioDuration) || audioDuration <= 0) { s.value = 500; return; }
  const zw = getZoomWindow();
  const center = (zw.start + zw.end) / 2;
  const frac = Math.max(0, Math.min(1, center / audioDuration));
  s.value = Math.round(frac * 1000);
  if (typeof updateSliderFill === 'function') updateSliderFill(s);
}

// Drag the Loop Detail waveform to pan the window. Ignores drags that start on
// an edge handle (those resize the loop) so the two never fight.
function dragZoomPan(wrap) {
  if (!wrap) return;
  const cx = (e) => (e.touches ? e.touches[0].clientX : e.clientX);
  function onStart(e) {
    if (!audioEl || !Number.isFinite(audioDuration) || audioDuration <= 0) return;
    if (e.target.closest('.zoom-handle')) return;   // let the handle drag win
    e.preventDefault();
    const rect = wrap.getBoundingClientRect();
    const zw = getZoomWindow();
    const startCenter = (zw.start + zw.end) / 2;
    const winDur = zw.duration;
    const startX = cx(e);
    wrap.classList.add('panning');
    function onMove(ev) {
      const dx = cx(ev) - startX;
      // Drag right → reveal earlier audio → center moves earlier.
      const deltaT = -(dx / rect.width) * winDur;
      const half = winDur / 2;
      const lo = half, hi = Math.max(half, audioDuration - half);
      zoomCenter = Math.max(lo, Math.min(startCenter + deltaT, hi));
      zoomFocus = 'free';
      syncZoomFocusButtons();
      updateTrimUI();
    }
    function onEnd() {
      wrap.classList.remove('panning');
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
  wrap.addEventListener('mousedown', onStart);
  wrap.addEventListener('touchstart', onStart, { passive: false });
}

(function initSliderExtras() {
  // ---- CSS (injected once) ----
  const style = document.createElement('style');
  style.textContent =
    '.slider-nudge-wrap{display:flex;align-items:center;gap:6px;flex:1;min-width:0}' +
    '.slider-nudge-wrap input[type=range]{flex:1;min-width:0}' +
    '.slider-nudge-btn{flex:none;width:26px;height:26px;padding:0;border:0;border-radius:7px;background:#232734;color:#c8cede;font-size:16px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;-webkit-user-select:none;user-select:none;touch-action:manipulation;transition:background .12s}' +
    '.slider-nudge-btn:hover{background:#2c3140}' +
    '.slider-nudge-btn:active{background:#7c5cff;color:#fff}' +
    '.zoom-pan-row,.crossfade-row{display:flex;align-items:center;gap:10px;margin:8px 0 2px}' +
    '.zoom-pan-label,.crossfade-label{font-size:12px;color:#8a93a6;flex:none;min-width:64px}' +
    '.crossfade-val{font-size:12px;color:#c8cede;flex:none;min-width:38px;text-align:right}' +
    '#zoomTrackWrap{cursor:grab}#zoomTrackWrap.panning{cursor:grabbing}';
  document.head.appendChild(style);

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




// ---------- Draft save / load ----------
// serializeSkribl() produces one self-contained object. The same object shape
// will POST to skribls.net later — only the transport changes.
// ---------- Autosave / crash recovery ----------
// Saves the DRAWING (strokes, snapshot, background) plus media *metadata*
// (filenames + settings) to localStorage — never the photo/music bytes, which
// are far too large. On reload we can restore the drawing exactly and tell the
// user which files to re-add, with their settings already in place.
const AUTOSAVE_KEY = 'skribl_autosave_v1';
let autosaveTimer = null;

function serializeAutosave() {
  let baseSnapshot = null;
  try {
    if (hasContent && strokes.length === 0) {
      baseSnapshot = canvas.toDataURL();
    } else if (preRecordSnapshot) {
      baseSnapshot = preRecordSnapshot;
    }
  } catch (e) {
    baseSnapshot = null;
  }
  // Persist the deepest undone state too — redoStack[0] is the maximal drawing
  // (most strokes). With it plus the applied strokes above, a refresh can rebuild
  // the redo stack, so undone strokes aren't lost on reload.
  let redoStrokes = null, redoStrokeGroups = null;
  if (redoStack.length) {
    const deepest = redoStack[0];
    if (deepest && deepest.strokes) {
      redoStrokes = deepest.strokes.slice();
      redoStrokeGroups = (deepest.strokeGroups || []).slice();
    }
  }
  return {
    version: 1,
    savedAt: new Date().toISOString(),
    baseSnapshot: baseSnapshot,
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    redoStrokes: redoStrokes,
    redoStrokeGroups: redoStrokeGroups,
    background: { color: bgColor },
    // Metadata only — no bytes. Prefer live media; fall back to pending meta
    // (from a restore where the user hasn't re-added the file yet) so it persists.
    photoMeta: (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
      ? { name: photoBgImg._fileName, fit: photoFit, opacity: photoOpacityVal_, blur: photoBlur_, offset: { x: photoOffsetX, y: photoOffsetY }, zoom: photoZoom }
      : (typeof pendingPhotoMeta !== 'undefined' ? pendingPhotoMeta : null),
    musicMeta: currentMusicMeta()
  };
}

// The loop numbers only mean anything once loadedmetadata/decodeAudioData has
// run. Before that `trimEnd` is still its initial 0, and an autosave landing in
// that window used to persist a zero-length "loop" — which came back on re-add
// as the 0.5s minimum-loop clamp in applyPendingMusicSettings, and rendered as
// "Loop 0:00–0:00" on the pending card. While the duration is unknown we keep a
// previously saved loop for the same file if there is one, and otherwise write
// the name with null trim values so the load-time defaults apply instead of a
// bogus loop. (Flip doesn't need this: decodeForWaveform installs its 20s
// default BEFORE applying any saved meta, so a null never reaches the clamp.)
function currentMusicMeta() {
  const prev = (typeof pendingMusicMeta !== 'undefined') ? pendingMusicMeta : null;
  if (!(audioEl && audioEl._fileName)) return prev;
  const decoded = Number.isFinite(audioDuration) && audioDuration > 0 && trimEnd > trimStart;
  if (!decoded) {
    if (prev && prev.name === audioEl._fileName) return prev;
    return { name: audioEl._fileName, trimStart: null, trimEnd: null, crossfadeMs: loopCrossfadeMs };
  }
  return { name: audioEl._fileName, trimStart: trimStart, trimEnd: trimEnd, crossfadeMs: loopCrossfadeMs };
}

function showAutosaveStatus(state) {
  const el = document.getElementById('autosaveStatus');
  const txt = document.getElementById('autosaveStatusText');
  if (!el || !txt) return;
  clearTimeout(el._hideTimer);
  el.hidden = false;
  el.classList.remove('saving', 'failed', 'partial');
  if (state === 'saving') { el.classList.add('saving'); txt.textContent = 'Saving…'; }
  else if (state === 'failed') { el.classList.add('failed'); txt.textContent = 'Autosave failed'; }
  // The Pad's autosave stores media METADATA only (bytes never fit in localStorage),
  // so whenever a photo/track is attached the session is not fully recoverable.
  // Amber says so up front instead of a green light the drawers quietly contradict.
  else if (state === 'saved-no-media') { el.classList.add('partial'); txt.textContent = 'Saved without media'; }
  else { txt.textContent = 'Saved'; }
  requestAnimationFrame(() => el.classList.add('show'));
  // "Saved"/"failed" fade out after a moment; "saving" stays until resolved.
  if (state !== 'saving') {
    el._hideTimer = setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => { el.hidden = true; }, 300);
    }, 1600);
  }
}

function writeAutosave() {
  // Player mode is read-only — never mutate the editor's autosave.
  if (document.body.classList.contains('player-mode')) return;
  // Nothing meaningful on the canvas AND nothing undone to preserve → clear any
  // stale save. (Keep it when redo is pending, so undoing to blank then reloading
  // can still redo the undone strokes.)
  if (!hasContent && strokes.length === 0 && redoStack.length === 0) {
    try { localStorage.removeItem(AUTOSAVE_KEY); } catch (e) {}
    return;
  }
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeAutosave()));
    const hasPhoto = !!((photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
                        || (typeof pendingPhotoMeta !== 'undefined' && pendingPhotoMeta));
    const hasMusic = !!((audioEl && audioEl._fileName)
                        || (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta));
    showAutosaveStatus((hasPhoto || hasMusic) ? 'saved-no-media' : 'saved');
  } catch (e) {
    // Quota or private-mode failure — fail silently in storage, but tell the user.
    showAutosaveStatus('failed');
  }
}

// Debounced: batch a flurry of edits into one write ~1.2s after activity stops.
function scheduleAutosave() {
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(writeAutosave, 1200);
}

function clearAutosave() {
  clearTimeout(autosaveTimer);
  try { localStorage.removeItem(AUTOSAVE_KEY); } catch (e) {}
}

function readAutosave() {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    const hasDrawing = (data.strokes && data.strokes.length) || data.baseSnapshot;
    return hasDrawing ? data : null;
  } catch (e) {
    return null;
  }
}

// Reconstruct the per-stroke undo AND redo history for a restored drawing. The
// autosave persists the drawing plus the deepest undone state (the maximal stroke
// set) and how many strokes are currently applied — not the stacks themselves,
// which are piles of full-canvas snapshots far too big to store. So we rebuild
// them here: snapshot the canvas at each stroke boundary of the maximal drawing,
// exactly as startDraw does live. States before the applied cut become the undo
// stack; states after it become the redo stack. Result — a restored Skribl undoes
// AND redoes stroke by stroke, identical to one edited this session. Undo is
// bounded to the last 30 (the in-session cap). Renders the applied state on the
// canvas as it goes. Fully guarded: any failure falls back to the applied drawing
// with no history, never a broken stack.
//   maxStrokes/maxGroups — the maximal drawing (applied + undone strokes)
//   appliedCount         — how many strokes are currently on the canvas (prefix)
function rebuildHistoryForRestore(maxStrokes, maxGroups, appliedCount, baseHasContent) {
  undoStack = [];
  redoStack = [];
  const total = maxGroups.length;
  appliedCount = Math.max(0, Math.min(appliedCount, total));
  // starts[k] = point index where stroke k begins; starts[total] = all points.
  const starts = [];
  let acc = 0;
  for (let k = 0; k <= total; k++) { starts.push(acc); if (k < total) acc += maxGroups[k]; }

  const snapshotMain = () => {
    const s = document.createElement('canvas');
    s.width = Math.max(1, canvas.width);
    s.height = Math.max(1, canvas.height);
    if (canvas.width > 0 && canvas.height > 0) s.getContext('2d').drawImage(canvas, 0, 0);
    return s;
  };
  // Render base + the first k strokes. clearAndRestore is synchronous once the
  // base image is cached, so the canvas is fully painted before we snapshot.
  const renderPrefix = (k) => clearAndRestore(() => paintStrokesStatic(maxStrokes.slice(0, starts[k])));
  const stateAt = (k) => {
    renderPrefix(k);
    return {
      image: snapshotMain(),
      strokes: maxStrokes.slice(0, starts[k]),
      strokeGroups: maxGroups.slice(0, k),
      hasContent: (k === 0) ? baseHasContent : true
    };
  };

  const build = () => {
    try {
      // Undo: the state before each applied stroke = state(0)..state(appliedCount-1),
      // capped to the most recent 30.
      const undoFirst = Math.max(0, appliedCount - 30);
      for (let k = undoFirst; k < appliedCount; k++) undoStack.push(stateAt(k));
      // Redo: the undone future states = state(appliedCount+1)..state(total), pushed
      // deepest-first so pop() yields the next redo (appliedCount+1) first.
      for (let k = total; k > appliedCount; k--) redoStack.push(stateAt(k));
    } catch (e) {
      undoStack = [];
      redoStack = [];
    }
    // Leave the applied state on the canvas as the live drawing.
    renderPrefix(appliedCount);
    undoBtn.disabled = undoStack.length === 0;
    redoBtn.disabled = redoStack.length === 0;
  };

  // Warm the base-image cache once (async only on the first load), then build the
  // snapshots synchronously inside the callback.
  clearAndRestore(build);
}

function restoreAutosave(data) {
  clearCanvas();
  if (data.background && data.background.color) {
    bgColor = data.background.color;
    canvasWrap.style.backgroundColor = bgColor;
    document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b.dataset.bg === bgColor));
  }
  updateVignette();
  strokes = (data.strokes || []).slice();
  strokeGroups = (data.strokeGroups || []).slice();

  const { width: cw, height: ch } = getCanvasLogicalSize();
  // The autosave stores the *applied* strokes in strokes/strokeGroups and, if any
  // strokes were undone (redo pending), the *maximal* drawing in redoStrokes/
  // redoStrokeGroups. Rebuild both stacks around the applied cut so undo AND redo
  // survive the refresh.
  const hasRedo = !!(data.redoStrokes && data.redoStrokes.length);
  const maxStrokes = hasRedo ? data.redoStrokes.slice() : strokes.slice();
  const maxGroups = (hasRedo && data.redoStrokeGroups) ? data.redoStrokeGroups.slice() : strokeGroups.slice();
  const appliedCount = strokeGroups.length;   // strokes currently on canvas (a prefix of maximal)
  if (strokes.length || hasRedo) {
    preRecordSnapshot = data.baseSnapshot || null;
    hasContent = strokes.length > 0 || !!preRecordSnapshot;
    // The pre-stroke base only counts as content if a photo was baked into it.
    rebuildHistoryForRestore(maxStrokes, maxGroups, appliedCount, !!(data.photoMeta && data.photoMeta.name));
  } else if (data.baseSnapshot) {
    // Base image with no strokes (e.g. a saved photo background): just draw it.
    preRecordSnapshot = null;
    const baseImg = new Image();
    baseImg.onload = () => { ctx.drawImage(baseImg, 0, 0, cw, ch); };
    baseImg.src = data.baseSnapshot;
    hasContent = true;
  }
  if (strokes.length) {
    hasContent = true;
    recorded = true;
    finishedRecording = true;
    playWrap.hidden = false;
    postBtn.hidden = false;
    updateDrawingTimeLabels();
    durationBadge.hidden = false;
  } else if (data.baseSnapshot) {
    hasContent = true;
  }
  updateEmptyHint();
  updateCanvasLockCue();
  updateClearVisibility();

  // Set pending media and show the placeholder cards with their saved settings.
  pendingMusicMeta = (data.musicMeta && data.musicMeta.name) ? data.musicMeta : null;
  pendingPhotoMeta = (data.photoMeta && data.photoMeta.name) ? data.photoMeta : null;
  refreshPendingCards();

  const hadMedia = pendingMusicMeta || pendingPhotoMeta;
  showToast(hadMedia ? 'Restored — re-add your media below' : 'Drawing restored', null);
}

// When the user re-adds media after a restore, reapply the saved settings.
let pendingMusicMeta = null;
let pendingPhotoMeta = null;

// Shared, race-free reapply of saved loop trim onto the freshly loaded audio.
function applyPendingMusicSettings(meta) {
  if (!meta || !audioEl || !Number.isFinite(audioDuration) || audioDuration <= 0) return;
  if (meta.trimStart != null) trimStart = Math.min(meta.trimStart, audioDuration);
  if (meta.trimEnd != null) trimEnd = Math.min(meta.trimEnd, audioDuration);
  // Keep a sane minimum loop length.
  trimEnd = Math.max(trimStart + 0.5, Math.min(trimEnd, audioDuration));
  if (meta.crossfadeMs != null) { loopCrossfadeMs = meta.crossfadeMs; if (typeof setCrossfadeUI === 'function') setCrossfadeUI(); }
  updateTrimUI();
}

function fmtLoopTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m + ':' + String(s).padStart(2, '0');
}

// Build the human-readable settings summary for each pending card and toggle
// the cards' visibility + the little tab dots that hint media is waiting.
function refreshPendingCards() {
  const mCard = document.getElementById('musicPending');
  const pCard = document.getElementById('photoPending');

  if (mCard) {
    if (pendingMusicMeta && !audioEl) {
      document.getElementById('musicPendingName').textContent = pendingMusicMeta.name;
      let meta = 'Loop saved';
      if (pendingMusicMeta.trimStart != null && pendingMusicMeta.trimEnd != null) {
        const len = (pendingMusicMeta.trimEnd - pendingMusicMeta.trimStart);
        meta = `Loop ${fmtLoopTime(pendingMusicMeta.trimStart)}–${fmtLoopTime(pendingMusicMeta.trimEnd)} · ${len.toFixed(1)}s`;
      }
      document.getElementById('musicPendingMeta').textContent = meta;
      mCard.hidden = false;
      musicUploadBtn.hidden = true;
      musicTabDot.hidden = false;
      musicTabDot.classList.add('pending');
    } else {
      mCard.hidden = true;
      musicUploadBtn.hidden = false;
      musicTabDot.classList.remove('pending');
    }
  }

  if (pCard) {
    if (pendingPhotoMeta && (!photoBgImg || photoBgImg.style.display === 'none')) {
      document.getElementById('photoPendingName').textContent = pendingPhotoMeta.name;
      const parts = [];
      if (pendingPhotoMeta.fit) {
        const fitName = { cover: 'Fill', contain: 'Fit', stretch: 'Stretch' }[pendingPhotoMeta.fit] || pendingPhotoMeta.fit;
        parts.push(fitName);
      }
      if (pendingPhotoMeta.opacity != null) parts.push(Math.round(pendingPhotoMeta.opacity * 100) + '% opacity');
      if (pendingPhotoMeta.blur) parts.push(pendingPhotoMeta.blur + 'px blur');
      if (pendingPhotoMeta.zoom && pendingPhotoMeta.zoom !== 1) parts.push(Math.round(pendingPhotoMeta.zoom * 100) + '% zoom');
      document.getElementById('photoPendingMeta').textContent = parts.length ? parts.join(' · ') : 'Adjustments saved';
      pCard.hidden = false;
      photoUploadBtn.hidden = true;
      document.getElementById('photoTabDot').hidden = false;
      document.getElementById('photoTabDot').classList.add('pending');
    } else {
      pCard.hidden = true;
      photoUploadBtn.hidden = false;
      { const d = document.getElementById('photoTabDot'); if (d) d.classList.remove('pending'); }
    }
  }
}

// ===========================================================================
// Frame model (Phase 1: frame-aware core)
// A Skribl is a list of frames; a classic record/replay Skribl is a 1-frame
// Skribl. Phase 1 lands the model + a single normalize-on-read canonicalizer so
// every past Skribl stays valid, with NO change to the pad's behaviour. Live
// editing still runs on the existing globals (= the current frame); multi-frame
// editing arrives in Phase 2 using these same capture/load paths.
// ===========================================================================

// Build a Frame object from whatever is live on the canvas right now. (Same field
// logic serializeSkribl has always used — a frame IS the pad's drawing state.)
function captureCurrentFrame() {
  let baseSnapshot = null;
  try {
    if (hasContent && strokes.length === 0) baseSnapshot = canvas.toDataURL();
    else if (preRecordSnapshot) baseSnapshot = preRecordSnapshot;
  } catch (e) { baseSnapshot = null; }
  return {
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    baseSnapshot: baseSnapshot,
    background: { color: bgColor },
    photo: photoBgImg && photoBgImg._draftData && photoBgImg.style.display !== 'none'
      ? { data: photoBgImg._draftData, name: photoBgImg._fileName || null, fit: photoFit, opacity: photoOpacityVal_, blur: photoBlur_, offset: { x: photoOffsetX, y: photoOffsetY }, zoom: photoZoom }
      : null,
    music: audioEl && audioEl._objectUrl && musicEnabled
      ? { data: audioEl._draftData || null, name: audioEl._fileName || null, trimStart: trimStart, trimEnd: trimEnd, crossfadeMs: loopCrossfadeMs }
      : null
  };
}

// Canonicalize ANY Skribl payload — legacy (frame-less) or new (frames[]) — into
// one shape that always has frames[] AND mirrors the current frame's drawing
// fields to the top level, so every existing reader keeps working untouched.
// This is the single upgrade-on-read that sits in front of every deserialize.
function normalizeSkribl(payload) {
  if (!payload || typeof payload !== 'object') return payload;
  let frames, playbackMode, fps;
  if (Array.isArray(payload.frames) && payload.frames.length) {
    frames = payload.frames;
    playbackMode = payload.playbackMode || (frames.length > 1 ? 'flip' : 'replay');
    fps = payload.fps || 12;
  } else {
    // Legacy Skribl: wrap the top-level drawing into a single frame.
    frames = [{
      strokes: payload.strokes || [],
      strokeGroups: payload.strokeGroups || [],
      baseSnapshot: payload.baseSnapshot || null,
      background: payload.background || { color: bgColor },
      photo: payload.photo || null,
      music: payload.music || null
    }];
    playbackMode = 'replay';
    fps = payload.fps || 12;
  }
  const f0 = frames[Math.min(frameIndex, frames.length - 1)] || frames[0];
  return Object.assign({}, payload, {
    schemaVersion: payload.schemaVersion || 2,
    playbackMode: playbackMode,
    fps: fps,
    frames: frames,
    // legacy top-level mirror of the current frame (keeps loadSkribl et al. intact)
    strokes: f0.strokes || [],
    strokeGroups: f0.strokeGroups || [],
    baseSnapshot: f0.baseSnapshot != null ? f0.baseSnapshot : (payload.baseSnapshot || null),
    background: f0.background || payload.background || { color: bgColor },
    photo: f0.photo != null ? f0.photo : (payload.photo || null),
    music: f0.music != null ? f0.music : (payload.music || null)
  });
}

function serializeSkribl() {
  // A frame captures the live drawing (base layer + recorded strokes + media).
  // Frame-format: the drawing lives under frames[] only — no legacy top-level
  // mirror — so the payload stays lean (no duplicated photo/audio blobs). Every
  // reader goes through normalizeSkribl(), which surfaces frame 0 on read.
  const frame = captureCurrentFrame();
  return {
    version: 2,             // format marker: drawing lives under frames[]
    schemaVersion: 2,
    playbackMode: 'replay', // 1 frame ⇒ timed replay
    fps: null,              // replay Skribls don't use fps
    frames: [ frame ],
    draftId: 'draft_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
    userId: null,               // server stamps this later
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    title: 'Untitled Skribl',
    canvasSize: (() => {
      // The authored logical size (backing store in CSS px), NOT the fitted
      // display rect — otherwise a post made while rotated would record the
      // shrunken display size and the player would misplace the strokes.
      const lg = getCanvasLogicalSize();
      return { cssWidth: Math.round(lg.width), cssHeight: Math.round(lg.height), dpr: window.devicePixelRatio || 1 };
    })()
  };
}

// ---- Loop-crop for posting -------------------------------------------------
// Encode a slice of a decoded AudioBuffer to a 16-bit PCM WAV data URL. Reads
// straight from the buffer's channel data with a frame offset, so no temporary
// AudioBuffer / AudioContext is needed. Synchronous and dependency-free.
function audioBufferToWavDataURL(buffer, startFrame, frames) { return window.SkriblAudioLoop.audioBufferToWavDataURL(buffer, startFrame, frames); }

// --- Loop crossfade (bake-only) --------------------------------------------
// The posted/exported loop is a hard cut at the seam (le → ls). If those points
// don't line up you get a click every wrap — that's what Test Seam lets you
// hear. A crossfade folds the loop's tail over its head so the wrap becomes two
// originally-adjacent samples (smooth). It's applied only to the rendered clip
// at post/preview time — live playback of the source is untouched. Default off.
// (State `loopCrossfadeMs` is declared with the other audio state near the top,
//  so it exists before initSliderExtras / setCrossfadeUI run.)

// Build the crossfaded loop as raw channel arrays. Output length = frames - X.
// For the first X output samples we equal-power blend the head (fading in) with
// the loop's tail (fading out); the rest is the loop body verbatim. When this
// clip loops, its last sample and out[0] are contiguous in the source, so there
// is no discontinuity at the seam.
function buildLoopChannels(buffer, startFrame, frames, xfadeFrames) { return window.SkriblAudioLoop.buildLoopChannels(buffer, startFrame, frames, xfadeFrames); }

// Encode raw Float32 channel arrays (all same length) to a 16-bit PCM WAV data
// URL. Mirrors audioBufferToWavDataURL's writer but reads from provided arrays,
// so the crossfade path can encode samples that don't exist in the source
// buffer. Kept separate so the untouched no-crossfade path stays byte-for-byte.
function encodeWavFromChannels(channels, sampleRate) { return window.SkriblAudioLoop.encodeWavFromChannels(channels, sampleRate); }

// Slice currentAudioBuffer to the [trimStart, trimEnd] loop and return a small
// WAV data URL + its duration, or null if the decoded buffer isn't usable. When
// a crossfade is set, the tail is folded over the head so the clip loops
// seamlessly (the clip is then shorter by the crossfade length).
function buildTrimmedLoopWav() { return window.SkriblAudioLoop.buildTrimmedLoopWav({ currentAudioBuffer, trimStart, trimEnd, loopCrossfadeMs }); }

// --- Sample-accurate live loop engine (Web Audio) ---------------------------
// The live monitors (Preview Loop, editor Play) used timer-wrapped <audio>,
// which drifts (the wrap is caught up to a timer-tick late, variably) and can
// click. This plays the SAME loop the post uses, but as an AudioBufferSourceNode
// with loop=true — scheduled in the audio hardware clock, so it's gapless and
// drift-free forever. Reuses buildLoopChannels for the crossfaded fold, so no
// WAV round-trip: we build the AudioBuffer directly.
let _waLoopSource = null;
let _waLoopStartCtx = 0;   // audioCtx.currentTime when the loop started
let _waLoopDuration = 0;   // loop clip length (seconds)
function buildLoopAudioBuffer() { return window.SkriblAudioLoop.buildLoopAudioBuffer({ currentAudioBuffer: currentAudioBuffer, audioCtx: audioCtx, trimStart: trimStart, trimEnd: trimEnd, loopCrossfadeMs: loopCrossfadeMs }); }
function stopWebAudioLoop() {
  if (_waLoopSource) { try { _waLoopSource.stop(); } catch (e) {} try { _waLoopSource.disconnect(); } catch (e) {} _waLoopSource = null; }
}
function startWebAudioLoop() {
  if (!audioCtx || !currentAudioBuffer) return false;
  const buf = buildLoopAudioBuffer();
  if (!buf) return false;
  stopWebAudioLoop();
  if (audioCtx.state === 'suspended') { try { audioCtx.resume(); } catch (e) {} }
  const src = audioCtx.createBufferSource();
  src.buffer = buf;
  src.loop = true;
  src.loopStart = 0;
  src.loopEnd = buf.duration;
  src.connect(audioCtx.destination);
  try { src.start(); } catch (e) { return false; }
  _waLoopSource = src;
  _waLoopStartCtx = audioCtx.currentTime;
  _waLoopDuration = buf.duration;
  return true;
}
// Current position within the looping clip, mapped onto the song timeline.
function webAudioLoopSongTime() {
  if (!audioCtx || _waLoopDuration <= 0) return trimStart || 0;
  const el = audioCtx.currentTime - _waLoopStartCtx;
  return (trimStart || 0) + (el % _waLoopDuration);
}
// draft saved immediately after adding a big song/photo doesn't omit the bytes.
let mediaBusy = 0;
function beginMediaRead() {
  mediaBusy++;
  const item = document.getElementById('saveDraftItem');
  if (item) { item.disabled = true; item.classList.add('busy'); }
}
function endMediaRead() {
  mediaBusy = Math.max(0, mediaBusy - 1);
  if (mediaBusy === 0) {
    const item = document.getElementById('saveDraftItem');
    if (item) { item.disabled = false; item.classList.remove('busy'); }
  }
}

function saveDraft() {
  // Real guard (not just the disabled menu item) so any caller is protected.
  if (mediaBusy > 0) {
    showToast('Preparing media — try again in a moment', menuBtn);
    return;
  }
  const draft = serializeSkribl();
  const blob = new Blob([JSON.stringify(draft)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (draft.title || 'skribl').replace(/\s+/g, '-').toLowerCase() + '.skribl';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast('Draft saved', menuBtn);
}

// Fully tear down any loaded music + photo before loading a draft, so a draft
// with no media doesn't leave the previous session's media hanging around.
// (clearCanvas intentionally keeps media, which is right for the Clear action
// but wrong for Load — a loaded draft must reflect exactly what was saved.)
function resetMediaForLoad() {
  stopLoopPreview();
  if (typeof exitReposition === 'function') exitReposition();   // don't stay stuck repositioning a photo that's about to be replaced
  // Music
  if (audioEl) {
    audioEl.pause();
    if (audioEl._objectUrl) URL.revokeObjectURL(audioEl._objectUrl);
    audioEl = null;
  }
  audioDuration = 0;
  trimStart = 0;
  trimEnd = 0;
  currentAudioBuffer = null;
  loopCrossfadeMs = 0; if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
  musicDetail.hidden = true;
  musicInput.value = '';
  musicUploadBtn.classList.remove('loaded');
  musicBtnLabel.textContent = 'Add music';
  musicTabDot.hidden = true;
  musicRemove.hidden = true;
  if (waveformCtx) waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  if (zoomWaveformCtx) zoomWaveformCtx.clearRect(0, 0, zoomWaveformCanvas.width, zoomWaveformCanvas.height);
  if (loopZoomLabel) loopZoomLabel.textContent = '0:00.00 → 0:00.00 [0.00s]';
  // Photo
  photoBg = null;
  if (photoBgImg._objectUrl) { URL.revokeObjectURL(photoBgImg._objectUrl); photoBgImg._objectUrl = null; }
  photoBgImg._draftData = null;
  photoBgImg._fileName = null;
  photoBgImg.src = '';
  photoBgImg.style.display = 'none';
  photoBgImg.style.filter = '';
  photoInput.value = '';
  photoUploadBtn.classList.remove('loaded');
  document.querySelector('#photoUploadBtn span').textContent = 'Add a photo';
  document.getElementById('photoDetail').hidden = true;
  document.getElementById('photoTabDot').hidden = true;
  document.getElementById('photoRemove').hidden = true;
  photoFit = 'cover';
  photoOpacityVal_ = 1;
  photoBlur_ = 0;
  document.getElementById('photoOpacity').value = 100;
  document.getElementById('photoOpacityVal').textContent = '100%';
  const _blEl = document.getElementById('photoBlur');
  if (_blEl) { _blEl.value = 0; document.getElementById('photoBlurVal').textContent = '0px'; updateSliderFill(_blEl); }
  photoOffsetX = 0.5;
  photoOffsetY = 0.5;
  photoZoom = 1; setZoomSliderUI();
  // Hide the Reposition button/hint now that no photo is loaded. If the draft
  // being loaded has a photo, loadSkribl's photo block re-shows it right after.
  if (typeof updateRepositionUI === 'function') updateRepositionUI();
}

function loadSkribl(data) {
  // Validate the raw payload has a recognizable format marker, THEN canonicalize.
  if (!data || (data.version == null && data.schemaVersion == null && !data.frames)) { showToast('That file isn\'t a valid draft', menuBtn); return; }
  data = normalizeSkribl(data);
  clearCanvas();
  resetMediaForLoad();

  // In the editor, adopt the draft's authored logical size so its strokes (which
  // live in that space) map 1:1 — even if the current viewport orientation
  // differs from when it was drawn. The player sizes its own canvas separately
  // (see initPlayer) before calling loadSkribl, so skip there.
  if (!document.body.classList.contains('player-mode') && data.canvasSize
      && data.canvasSize.cssWidth && data.canvasSize.cssHeight) {
    establishEditorCanvas(data.canvasSize.cssWidth, data.canvasSize.cssHeight);
    layoutEditorCanvas();
  }

  // Background
  if (data.background && data.background.color) {
    bgColor = data.background.color;
    canvasWrap.style.backgroundColor = bgColor;
    document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b.dataset.bg === bgColor));
  }
  updateVignette();

  // Strokes — replay-render them onto the canvas
  strokes = (data.strokes || []).slice();
  strokeGroups = (data.strokeGroups || []).slice();

  const renderStrokes = () => paintStrokesStatic(strokes);

  const { width: cw, height: ch } = getCanvasLogicalSize();

  if (data.baseSnapshot) {
    // Draw the base layer (pre-record or un-recorded drawing) first,
    // then render recorded strokes on top — mirroring playback.
    preRecordSnapshot = strokes.length ? data.baseSnapshot : null;
    const baseImg = new Image();
    baseImg.onload = () => {
      ctx.drawImage(baseImg, 0, 0, cw, ch);
      renderStrokes();
    };
    baseImg.src = data.baseSnapshot;
    hasContent = true;
  } else if (strokes.length) {
    renderStrokes();
  }

  if (strokes.length) {
    hasContent = true;
    recorded = true;
    finishedRecording = true;   // a loaded replay is a finished recording — lock it
    playWrap.hidden = false;
    postBtn.hidden = false;
    updateDrawingTimeLabels();
    durationBadge.hidden = false;
  } else if (data.baseSnapshot) {
    hasContent = true;
  }

  // Photo
  if (data.photo && data.photo.data) {
    photoBgImg.src = data.photo.data;
    photoBgImg._draftData = data.photo.data;
    photoBgImg._fileName = data.photo.name || 'Photo from draft';
    photoBgImg.style.display = 'block';
    photoFit = data.photo.fit || 'cover';
    const fitMap = { cover: 'cover', contain: 'contain', stretch: 'fill' };
    photoBgImg.style.objectFit = fitMap[photoFit] || 'cover';
    // Sync the segmented Fit control to the restored fit (was showing stale state).
    const _fitBtns = [...document.querySelectorAll('.photo-fit-btn')];
    _fitBtns.forEach(b => b.classList.toggle('active', b.dataset.fit === photoFit));
    const _ai = _fitBtns.findIndex(b => b.dataset.fit === photoFit);
    if (_ai >= 0 && photoFitSlider) {
      const _mv = () => {
        const off = _fitBtns.slice(0, _ai).reduce((s, b) => s + b.offsetWidth, 0);
        photoFitSlider.style.width = _fitBtns[_ai].offsetWidth + 'px';
        photoFitSlider.style.transform = `translateX(${off}px)`;
      };
      _mv(); setTimeout(_mv, 80);
    }
    photoOpacityVal_ = data.photo.opacity != null ? data.photo.opacity : 1;
    photoBgImg.style.opacity = photoOpacityVal_;
    photoBlur_ = data.photo.blur != null ? data.photo.blur : 0;
    photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
    const _off = data.photo.offset || {};
    photoOffsetX = _off.x != null ? _off.x : 0.5;
    photoOffsetY = _off.y != null ? _off.y : 0.5;
    photoZoom = clampPhotoZoom(data.photo.zoom);
    setZoomSliderUI();
    applyPhotoPosition();
    if (typeof updateRepositionUI === 'function') updateRepositionUI();
    document.getElementById('photoDetail').hidden = false;
    photoUploadBtn.classList.add('loaded');
    document.getElementById('photoTabDot').hidden = false;
    document.getElementById('photoRemove').hidden = false;
    const opEl2 = document.getElementById('photoOpacity');
    opEl2.value = Math.round(photoOpacityVal_ * 100);
    document.getElementById('photoOpacityVal').textContent = Math.round(photoOpacityVal_ * 100) + '%';
    updateSliderFill(opEl2);
    const blEl2 = document.getElementById('photoBlur');
    if (blEl2) {
      blEl2.value = photoBlur_;
      document.getElementById('photoBlurVal').textContent = photoBlur_ + 'px';
      updateSliderFill(blEl2);
    }
    setTimeout(initPhotoFitSlider, 50);
  }

  // Music — restore full audio + trim points (reversible)
  if (data.music && data.music.data) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    fetch(data.music.data).then(r => r.arrayBuffer()).then(buf => {
      if (audioEl && audioEl._objectUrl) URL.revokeObjectURL(audioEl._objectUrl);
      const blob = new Blob([buf]);
      const url = URL.createObjectURL(blob);
      audioEl = new Audio(url);
      audioEl._objectUrl = url;
      audioEl._draftData = data.music.data;
      audioEl._fileName = data.music.name || 'Music from draft';
      audioEl.addEventListener('loadedmetadata', () => {
        audioDuration = audioEl.duration;
        trimStart = data.music.trimStart != null ? data.music.trimStart : 0;
        trimEnd = data.music.trimEnd != null ? data.music.trimEnd : Math.min(audioDuration, 20);
        loopCrossfadeMs = data.music.crossfadeMs != null ? data.music.crossfadeMs : 0;
        if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
        musicDetail.hidden = false;
        musicUploadBtn.classList.add('loaded');
        musicBtnLabel.textContent = 'Loaded from draft';
        musicTabDot.hidden = false;
        document.getElementById('musicRemove').hidden = false;
        updateTrimUI();
      });
      audioCtx.decodeAudioData(buf.slice(0)).then(audioBuffer => {
        currentAudioBuffer = audioBuffer;
        setTimeout(() => { drawWaveform(audioBuffer); drawZoomWaveform(); updateZoomHandles(); }, 60);
      }).catch(() => {});
    }).catch(() => {});
  }

  updateEmptyHint();
  updateCanvasLockCue();
  if (!document.body.classList.contains('player-mode')) {
    showToast('Draft loaded', menuBtn);
    // The loaded draft is now the active work — refresh autosave so a later
    // restore prompt reflects this, not a stale previous session.
    setTimeout(() => { if (typeof writeAutosave === 'function') writeAutosave(); }, 300);
  }
}

document.getElementById('draftInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(reader.result);
      loadSkribl(data);
    } catch (err) {
      showToast('Couldn\'t read that draft file', menuBtn);
    }
  };
  reader.readAsText(file);
  e.target.value = '';
});

// ---------- Autosave wiring ----------
(function initAutosave() {
  // Player mode is read-only: no restore prompt, no autosave triggers. Covers
  // both the Flask path player (SKRIBL_MODE==='player', no hash) and the local
  // #skribl=<id> hash player.
  if ((typeof window !== 'undefined' && window.SKRIBL_MODE === 'player') ||
      /^#skribl=/.test(location.hash || '')) return;
  const banner = document.getElementById('restoreBanner');
  const sub = document.getElementById('restoreSub');
  const confirmBtn = document.getElementById('restoreConfirm');
  const discardBtn = document.getElementById('restoreDiscard');
  let bannerTimer = null;

  function hideBanner() {
    banner.classList.remove('show');
    bannerTimer = setTimeout(() => { banner.hidden = true; }, 400);
  }

  // On load: if there's a saved drawing, offer to restore it.
  const saved = readAutosave();
  if (saved) {
    const bits = [];
    if (saved.savedAt) {
      try {
        const d = new Date(saved.savedAt);
        bits.push(d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }));
      } catch (e) {}
    }
    const media = [];
    if (saved.musicMeta && saved.musicMeta.name) media.push('music');
    if (saved.photoMeta && saved.photoMeta.name) media.push('photo');
    if (media.length) bits.push(media.join(' + ') + ' to re-add');
    sub.textContent = bits.join(' · ') || 'From your last session';

    banner.hidden = false;
    requestAnimationFrame(() => banner.classList.add('show'));

    confirmBtn.addEventListener('click', () => {
      restoreAutosave(saved);
      hideBanner();
      // Write a fresh autosave reflecting the restored state, so reloading
      // again doesn't re-show this same prompt.
      setTimeout(writeAutosave, 200);
    });
    discardBtn.addEventListener('click', () => {
      clearAutosave();
      hideBanner();
    });
  }

  // Triggers: schedule an autosave whenever the drawing meaningfully changes.
  canvas.addEventListener('mouseup', scheduleAutosave);
  canvas.addEventListener('touchend', scheduleAutosave);
  recordBtn.addEventListener('click', scheduleAutosave);
  undoBtn.addEventListener('click', scheduleAutosave);
  redoBtn.addEventListener('click', scheduleAutosave);
  document.getElementById('bgGroup').addEventListener('click', scheduleAutosave);
  customBgInput.addEventListener('input', scheduleAutosave);

  // Media triggers — so adding/adjusting music or photo is captured too.
  document.getElementById('musicInput').addEventListener('change', scheduleAutosave);
  document.getElementById('photoInput').addEventListener('change', scheduleAutosave);
  document.getElementById('musicRemove').addEventListener('click', scheduleAutosave);
  document.getElementById('photoRemove').addEventListener('click', scheduleAutosave);
  document.getElementById('photoOpacity').addEventListener('input', scheduleAutosave);
  document.getElementById('photoBlur').addEventListener('input', scheduleAutosave);
  // Loop changes: trim handles, nudges, match-drawing, zoom handles all funnel
  // through updateTrimUI → so trigger autosave from the music track interactions.
  musicTrack.addEventListener('mouseup', scheduleAutosave);
  musicTrack.addEventListener('touchend', scheduleAutosave);
  if (zoomTrackWrap) {
    zoomTrackWrap.addEventListener('mouseup', scheduleAutosave);
    zoomTrackWrap.addEventListener('touchend', scheduleAutosave);
  }
  document.querySelectorAll('.nudge-btn').forEach(b => b.addEventListener('click', scheduleAutosave));
  matchDrawingBtn.addEventListener('click', scheduleAutosave);
  document.querySelectorAll('.photo-fit-btn').forEach(b => b.addEventListener('click', scheduleAutosave));
})();

// Reapply saved media settings when the user re-adds a file after a restore.
if (typeof pendingMusicMeta !== 'undefined') {
  const musicInputEl = document.getElementById('musicInput');
  // Music trim reapply is handled in the main loadedmetadata handler
  // (applyPendingMusicSettings) to avoid a listener-timing race.

  const photoInputEl = document.getElementById('photoInput');
  photoInputEl.addEventListener('change', () => {
    if (!pendingPhotoMeta) return;
    const meta = pendingPhotoMeta;
    pendingPhotoMeta = null;
    const pCard = document.getElementById('photoPending');
    if (pCard) pCard.hidden = true;
    photoUploadBtn.hidden = false;
    setTimeout(() => {
      if (!photoBgImg || photoBgImg.style.display === 'none') return;
      if (meta.fit) {
        photoFit = meta.fit;
        const fitMap = { cover: 'cover', contain: 'contain', stretch: 'fill' };
        photoBgImg.style.objectFit = fitMap[photoFit] || 'cover';
        const fitBtns = [...document.querySelectorAll('.photo-fit-btn')];
        fitBtns.forEach(b => b.classList.toggle('active', b.dataset.fit === photoFit));
        const activeIdx = fitBtns.findIndex(b => b.dataset.fit === photoFit);
        const moveSlider = () => {
          if (activeIdx < 0 || !photoFitSlider) return;
          const off = fitBtns.slice(0, activeIdx).reduce((s, b) => s + b.offsetWidth, 0);
          photoFitSlider.style.width = fitBtns[activeIdx].offsetWidth + 'px';
          photoFitSlider.style.transform = `translateX(${off}px)`;
        };
        moveSlider();
        setTimeout(moveSlider, 80);
      }
      if (meta.opacity != null) {
        photoOpacityVal_ = meta.opacity;
        photoBgImg.style.opacity = photoOpacityVal_;
        const opEl = document.getElementById('photoOpacity');
        opEl.value = Math.round(photoOpacityVal_ * 100);
        document.getElementById('photoOpacityVal').textContent = Math.round(photoOpacityVal_ * 100) + '%';
        updateSliderFill(opEl);
      }
      if (meta.blur != null) {
        photoBlur_ = meta.blur;
        photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
        const blEl = document.getElementById('photoBlur');
        blEl.value = photoBlur_;
        document.getElementById('photoBlurVal').textContent = photoBlur_ + 'px';
        updateSliderFill(blEl);
      }
      if (meta.offset) {
        photoOffsetX = meta.offset.x != null ? meta.offset.x : 0.5;
        photoOffsetY = meta.offset.y != null ? meta.offset.y : 0.5;
      }
      photoZoom = clampPhotoZoom(meta.zoom);
      setZoomSliderUI();
      applyPhotoPosition();
      updateRepositionUI();
    }, 140);
  });

  // Pending card buttons: "Re-add" opens the file picker; "✕" dismisses.
  const mBtn = document.getElementById('musicPendingBtn');
  const mDismiss = document.getElementById('musicPendingDismiss');
  if (mBtn) mBtn.addEventListener('click', () => musicInputEl.click());
  if (mDismiss) mDismiss.addEventListener('click', () => {
    pendingMusicMeta = null;
    document.getElementById('musicPending').hidden = true;
    musicUploadBtn.hidden = false;
    if (!audioEl) musicTabDot.hidden = true;
    scheduleAutosave();
  });

  const pBtn = document.getElementById('photoPendingBtn');
  const pDismiss = document.getElementById('photoPendingDismiss');
  if (pBtn) pBtn.addEventListener('click', () => photoInputEl.click());
  if (pDismiss) pDismiss.addEventListener('click', () => {
    pendingPhotoMeta = null;
    document.getElementById('photoPending').hidden = true;
    photoUploadBtn.hidden = false;
    if (!photoBgImg || photoBgImg.style.display === 'none') document.getElementById('photoTabDot').hidden = true;
    scheduleAutosave();
  });
}

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
      if (videoTitle) {
        expectedVideoFormat().then((fmt) => {
          videoTitle.textContent = 'Video (' + fmt + ')';
          if (fmt === 'MP4') videoDesc.textContent = audioEl ? 'Replay with music · MP4 (H.264)' : 'Replay · MP4 (H.264)';
        }).catch(() => { videoTitle.textContent = 'Video'; });
      }
    }
    pngBtn.disabled = !hasContent;
    // GIF option: needs strokes AND the vendored gifenc library.
    if (gifBtn) {
      const gifReady = typeof window.gifenc !== 'undefined' && window.gifenc.GIFEncoder;
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
          : 'Just the strokes, animated · silent · loops';
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

  function drawPhotoFitted(c, img, w, h, fit, ox, oy, zoom) {
    const iw = img.naturalWidth || w, ih = img.naturalHeight || h;
    if (fit === 'stretch') { c.drawImage(img, 0, 0, w, h); return; }
    let scale = fit === 'contain' ? Math.min(w/iw, h/ih) : Math.max(w/iw, h/ih);
    if (fit === 'cover' && zoom) scale *= zoom;   // zoom multiplies the cover scale
    const dw = iw * scale, dh = ih * scale;
    // Cover uses the stored crop offset; contain/stretch stay centered.
    const fx = fit === 'cover' && ox != null ? ox : 0.5;
    const fy = fit === 'cover' && oy != null ? oy : 0.5;
    c.drawImage(img, (w-dw)*fx, (h-dh)*fy, dw, dh);
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
    const MM = window.Mp4Muxer;
    if (!(MM && MM.Muxer && MM.ArrayBufferTarget)) return false;
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

// ==================== POST COMPOSER ====================
// The client-side half of posting: a sheet to title/caption the Skribl, a
// preview, and a sending → success/error state machine. serializeSkribl()
// already produces the self-contained payload; sendSkribl() is the ONE seam
// where a real network call drops in later — nothing else here changes.
(function initPostComposer() {
  const overlay = document.getElementById('postOverlay');
  const sheet = document.getElementById('postSheet');
  const titleInput = document.getElementById('postTitleInput');
  const captionInput = document.getElementById('postCaptionInput');
  const charCount = document.getElementById('postCharCount');
  const previewImg = document.getElementById('postPreviewImg');
  const previewFrame = document.getElementById('postPreview');
  const submitBtn = document.getElementById('postSubmitBtn');
  const submitLabel = document.getElementById('postSubmitLabel');
  const watchBtn = document.getElementById('postWatchBtn');
  let lastPostUrl = null;
  const status = document.getElementById('postStatus');
  const statusLabel = document.getElementById('postStatusLabel');
  const progressFill = document.getElementById('postProgressFill');
  const body = document.getElementById('postBody');
  let closeTimer = null;
  let posting = false;

  // ---- THE NETWORK SEAM ----
  // The ONE place a post leaves the app. When Flask serves the page the editor
  // template sets window.SKRIBL_API_BASE ("/api/skribls"); we POST the authored
  // serializeSkribl() payload there and return the server's { id, url } — url is
  // a real /s/<id> path. If there's no API base, or the request fails for any
  // reason, we fall back to the localStorage stub so a post never hard-fails in
  // front of the user (a Render free-tier cold start can 502 on first hit; a
  // transient failure shouldn't lose the user's work). Fallback url is a
  // #skribl=<id> hash the in-page player opens on this device only.
  async function sendSkribl(payload) {
    const apiBase = (typeof window !== 'undefined' && window.SKRIBL_API_BASE) || null;

    if (apiBase) {
      // Serialize once so the size-check and the request send the exact same bytes.
      const body = JSON.stringify(payload);

      // Client-side size guard: the server caps the request body at
      // MAX_CONTENT_LENGTH (25 MB via a Render env var) and raises a 413 that the
      // composer would otherwise only discover after uploading the whole payload.
      // Measure the true UTF-8 byte length up front and reject instantly with the
      // same wording the server's 413 handler uses, so an oversized post fails
      // immediately instead of stalling on the way up. Keep MAX_POST_BYTES a little
      // under the server cap for HTTP/proxy overhead beyond the body; if the Render
      // env var changes, keep this roughly in step with it.
      const MAX_POST_BYTES = 24_000_000;
      const bodyBytes = (typeof Blob !== 'undefined') ? new Blob([body]).size : body.length;
      if (bodyBytes > MAX_POST_BYTES) {
        throw new Error('This Skribl is too large to post. Try a smaller photo or a shorter audio loop.');
      }

      let res;
      try {
        res = await fetch(apiBase, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: body
        });
      } catch (netErr) {
        // Network failure (offline / DNS / CORS) — temporary. Save locally so
        // the user's work isn't lost, but flag it so the UI won't claim "Posted".
        console.warn('sendSkribl: network error, saving locally —', netErr);
        return saveLocalFallback(payload);
      }
      if (res.ok) {
        const data = await res.json().catch(() => null);
        // Server returns { id, url:"/s/<id>" } — a real, shared post.
        if (data && data.id && data.url) return { id: data.id, url: data.url, local: false };
        throw new Error('The server returned an unexpected response.');
      }
      // Server errors ≥500 are temporary → local fallback (flagged). But a 4xx
      // means the post was REJECTED (bad/oversized payload, auth, etc.) — never
      // fake success; surface the real error so the user knows it wasn't shared.
      if (res.status >= 500) {
        console.warn('sendSkribl: server ' + res.status + ', saving locally');
        return saveLocalFallback(payload);
      }
      let msg = 'Post rejected by the server (' + res.status + ').';
      try { const e = await res.json(); if (e && e.error) msg = e.error; } catch (e) {}
      throw new Error(msg);
    }

    // No API base at all (pure standalone build) — local-only by design.
    return saveLocalFallback(payload);
  }

  // Persist to localStorage under an id; hand back a #skribl=<id> hash URL the
  // in-page player opens on THIS device only. `local:true` tells the composer to
  // say "saved locally" rather than "posted/shared".
  async function saveLocalFallback(payload) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const id = 'local_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const post = {
      id,
      createdAt: new Date().toISOString(),
      title: payload.title,
      caption: payload.caption,
      hasAudio: !!((normalizeSkribl(payload).music) || {}).data,
      skribl: payload
    };
    try {
      localStorage.setItem('skribl_post_' + id, JSON.stringify(post));
    } catch (e) {
      throw new Error('Local storage full — could not save Skribl');
    }
    return { id, url: '#skribl=' + id, local: true };
  }

  // Flatten bg + photo + drawing into a single opaque canvas at native size.
  // Kept local (a few lines duplicated from export) so the delicate export IIFE
  // stays untouched. Returns a <canvas>, or null on failure.
  function buildPreviewCanvas() {
    try {
      const w = canvas.width, h = canvas.height;
      const out = document.createElement('canvas');
      out.width = w; out.height = h;
      const octx = out.getContext('2d');
      octx.fillStyle = bgColor || '#0d0f14';
      octx.fillRect(0, 0, w, h);
      if (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src) {
        octx.save();
        octx.globalAlpha = photoOpacityVal_ != null ? photoOpacityVal_ : 1;
        if (photoBlur_ > 0 && 'filter' in octx) octx.filter = `blur(${photoBlur_}px)`;
        const iw = photoBgImg.naturalWidth || w, ih = photoBgImg.naturalHeight || h;
        if (photoFit === 'stretch') {
          octx.drawImage(photoBgImg, 0, 0, w, h);
        } else {
          let scale = photoFit === 'contain' ? Math.min(w/iw, h/ih) : Math.max(w/iw, h/ih);
          if (photoFit === 'cover') scale *= photoZoom;
          const dw = iw * scale, dh = ih * scale;
          const fx = photoFit === 'cover' ? photoOffsetX : 0.5;
          const fy = photoFit === 'cover' ? photoOffsetY : 0.5;
          octx.drawImage(photoBgImg, (w-dw)*fx, (h-dh)*fy, dw, dh);
        }
        octx.restore();
      }
      octx.drawImage(canvas, 0, 0, w, h);
      return out;
    } catch (e) {
      return null;
    }
  }

  function buildPreviewDataURL() {
    const out = buildPreviewCanvas();
    return out ? out.toDataURL('image/png') : null;
  }

  // Render the finished drawing onto a 1200×630 branded share card (the Open
  // Graph aspect) so a shared /s/<id> link unfurls with the actual drawing
  // instead of the generic card. Composited client-side at post time and sent as
  // payload.thumbnail; encoded per-content — JPEG q0.92 when a photo is present
  // (~6x smaller, artifacts hidden), PNG for line-art cards (smaller AND crisp as
  // PNG). The /s/<id>/card.png route serves either format (also legacy PNG posts).
  function buildShareCardDataURL() {
    try {
      const flat = buildPreviewCanvas();
      const CARD_W = 1200, CARD_H = 630;
      const card = document.createElement('canvas');
      card.width = CARD_W; card.height = CARD_H;
      const c = card.getContext('2d');

      // Ground + soft accent wash (echoes the static og-card).
      c.fillStyle = '#0b0d12';
      c.fillRect(0, 0, CARD_W, CARD_H);
      const wash = c.createRadialGradient(CARD_W*0.5, CARD_H*0.28, 40, CARD_W*0.5, CARD_H*0.28, CARD_W*0.7);
      wash.addColorStop(0, 'rgba(124,92,255,0.16)');
      wash.addColorStop(1, 'rgba(124,92,255,0)');
      c.fillStyle = wash;
      c.fillRect(0, 0, CARD_W, CARD_H);

      const roundRect = (x, y, w, h, r) => {
        c.beginPath();
        c.moveTo(x+r, y);
        c.arcTo(x+w, y, x+w, y+h, r);
        c.arcTo(x+w, y+h, x, y+h, r);
        c.arcTo(x, y+h, x, y, r);
        c.arcTo(x, y, x+w, y, r);
        c.closePath();
      };

      // Contain the drawing centered, leaving a strip at the bottom for the mark.
      const footer = 84;
      const pad = 54;
      if (flat && flat.width && flat.height) {
        const areaW = CARD_W - pad*2;
        const areaH = CARD_H - pad - footer;
        const scale = Math.min(areaW / flat.width, areaH / flat.height);
        const dw = Math.round(flat.width * scale);
        const dh = Math.round(flat.height * scale);
        const dx = Math.round((CARD_W - dw) / 2);
        const dy = Math.round((CARD_H - footer - dh) / 2);
        c.save();
        roundRect(dx, dy, dw, dh, 18);
        c.clip();
        c.drawImage(flat, dx, dy, dw, dh);   // flat is already opaque (bg baked in)
        c.restore();
        c.lineWidth = 2;
        c.strokeStyle = 'rgba(124,92,255,0.45)';
        roundRect(dx, dy, dw, dh, 18);
        c.stroke();
      }

      // Brand mark: 6-point star + wordmark, centered in the footer strip.
      const cy = CARD_H - footer/2 + 6;
      const label = 'Skribl Pad';
      c.font = '700 30px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
      c.textBaseline = 'middle';
      const tw = c.measureText(label).width;
      const starR = 13;
      const gap = 14;
      const totalW = starR*2 + gap + tw;
      let x = (CARD_W - totalW) / 2;
      // star
      const scx = x + starR, scy = cy;
      c.save();
      c.translate(scx, scy);
      c.beginPath();
      for (let i = 0; i < 12; i++) {
        const ang = (Math.PI / 6) * i - Math.PI/2;
        const rr = (i % 2 === 0) ? starR : starR * 0.42;
        const px = Math.cos(ang) * rr, py = Math.sin(ang) * rr;
        i === 0 ? c.moveTo(px, py) : c.lineTo(px, py);
      }
      c.closePath();
      const sg = c.createLinearGradient(-starR, -starR, starR, starR);
      sg.addColorStop(0, '#7c5cff');
      sg.addColorStop(1, '#5b8cff');
      c.fillStyle = sg;
      c.fill();
      c.restore();
      // wordmark
      c.fillStyle = 'rgba(246,247,249,0.94)';
      c.textAlign = 'left';
      c.fillText(label, x + starR*2 + gap, cy);

      // Encode by content. A photo card compresses several x smaller as JPEG (the
      // point of this change), but the drawn lines sit ON TOP of the photo as sharp
      // white-on-dark edges, so use q0.92 (not a lower q) to keep JPEG's edge
      // ringing off those lines while still landing ~4-5x under PNG. A line-art
      // card (no photo) is the opposite: PNG is both SMALLER and crisp, and JPEG
      // would bloat AND ring it — so PNG there. The /s/<id>/card.png route serves
      // either format. The photo-present test mirrors buildPreviewCanvas exactly.
      const hasPhoto = !!(photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg.src);
      return hasPhoto ? card.toDataURL('image/jpeg', 0.92) : card.toDataURL('image/png');
    } catch (e) {
      return null;
    }
  }

  function updateCharCount() {
    charCount.textContent = captionInput.value.length + ' / 280';
  }

  // states: 'idle' | 'sending' | 'success' | 'error'
  function setState(state) {
    if (state === 'idle') {
      posting = false;
      status.hidden = true;
      status.classList.remove('error');
      progressFill.style.width = '0%';
      if (watchBtn) watchBtn.hidden = true;
      body.style.opacity = '';
      titleInput.disabled = false;
      captionInput.disabled = false;
      submitBtn.disabled = false;
      submitBtn.hidden = false;
      submitLabel.textContent = 'Post to Skribl';
    } else if (state === 'sending') {
      posting = true;
      status.hidden = false;
      status.classList.remove('error');
      statusLabel.textContent = 'Posting…';
      progressFill.style.width = '35%';
      body.style.opacity = '0.5';
      titleInput.disabled = true;
      captionInput.disabled = true;
      submitBtn.disabled = true;
    } else if (state === 'success') {
      posting = false;
      progressFill.style.width = '100%';
      statusLabel.textContent = 'Posted!';
      submitBtn.hidden = true;
    } else if (state === 'error') {
      posting = false;
      status.classList.add('error');
      statusLabel.textContent = 'Couldn\u2019t post — try again';
      progressFill.style.width = '100%';
      body.style.opacity = '';
      titleInput.disabled = false;
      captionInput.disabled = false;
      submitBtn.disabled = false;
      submitBtn.hidden = false;
      submitLabel.textContent = 'Try again';
    }
  }

  function openPost() {
    setState('idle');
    // Field values persist across an accidental close within the session; they
    // reset only after a successful post. So don't clear them here.
    updateCharCount();
    const preview = buildPreviewDataURL();
    if (preview) {
      previewImg.src = preview;
      // Mirror the pad's shape so the snapshot shows whole (no crop), and match
      // the frame background to the canvas color so there are never odd bars.
      if (previewFrame) {
        const ratio = (canvas.width && canvas.height) ? (canvas.width / canvas.height) : 1.6;
        previewFrame.style.aspectRatio = ratio.toFixed(4);
        previewFrame.style.background = bgColor || '#0d0f14';
        previewFrame.style.display = '';
      }
    } else if (previewFrame) {
      previewFrame.style.display = 'none';
    }
    clearTimeout(closeTimer);
    overlay.hidden = false;
    requestAnimationFrame(() => { overlay.classList.add('open'); applyKeyboardInset(); });
  }

  function closePost() {
    if (document.activeElement === titleInput || document.activeElement === captionInput) {
      document.activeElement.blur();
    }
    overlay.classList.remove('open');
    if (sheet) sheet.style.maxHeight = '';
    overlay.style.top = ''; overlay.style.bottom = ''; overlay.style.height = '';
    closeTimer = setTimeout(() => { overlay.hidden = true; }, 350);
  }

  // iOS doesn't shrink CSS viewport units for the on-screen keyboard, so the
  // bottom-anchored sheet ends up behind it. Fix: resize the fixed overlay to
  // the *visible* region (above the keyboard) using visualViewport. The sheet,
  // anchored to the overlay's bottom, then sits right on the keyboard — and iOS
  // has no reason to scroll the page and push the header off the top.
  // Mobile only; desktop / unsupported clears any inline styles.
  function applyKeyboardInset() {
    const vv = window.visualViewport;
    if (overlay.hidden || window.innerWidth > 640 || !vv) {
      overlay.style.top = '';
      overlay.style.bottom = '';
      overlay.style.height = '';
      if (sheet) sheet.style.maxHeight = '';
      return;
    }
    overlay.style.top = vv.offsetTop + 'px';
    overlay.style.bottom = 'auto';
    overlay.style.height = vv.height + 'px';
    if (sheet) sheet.style.maxHeight = Math.max(200, vv.height - 12) + 'px';
  }

  async function submit() {
    // Mirror saveDraft(): don't serialize while photo/music bytes are still
    // being read into base64, or the posted Skribl could omit them.
    if (mediaBusy > 0) {
      showToast('Preparing media — try again in a moment', submitBtn);
      return;
    }
    setState('sending');
    const payload = serializeSkribl();
    payload.title = (titleInput.value || '').trim() || 'Untitled Skribl';
    payload.caption = (captionInput.value || '').trim();
    // Per-Skribl share card for link unfurls. Post-only (kept out of
    // serializeSkribl so drafts stay lean); the server serves it at
    // /s/<id>/card.png and drops it from the player GET envelope. Best-effort —
    // a null card just falls back to the static branded image server-side.
    const card = buildShareCardDataURL();
    if (card) payload.thumbnail = card;
    // Crop music down to just the loop for posting. Post-only — drafts keep the
    // full sample so they can be re-trimmed. The trimmed clip IS the loop, so
    // trimStart/trimEnd become 0..loopLen. Falls back to the full sample if the
    // decoded buffer isn't ready or encoding fails, so a post never breaks here.
    if (payload.music && payload.music.data && currentAudioBuffer) {
      try {
        const cropped = buildTrimmedLoopWav();
        if (cropped) {
          payload.music = { data: cropped.dataUrl, name: payload.music.name, trimStart: 0, trimEnd: cropped.duration };
        }
      } catch (e) { /* keep the full-sample payload.music */ }
    }
    try {
      const res = await sendSkribl(payload);
      lastPostUrl = (res && res.url) || null;
      const localOnly = !!(res && res.local);
      titleInput.value = '';
      captionInput.value = '';
      updateCharCount();
      setState('success');
      // A posted (or locally-saved) Skribl is finished, so drop the crash-recovery
      // autosave — otherwise returning to the editor (e.g. via "Make your own
      // Skribl") offers to restore the drawing you just posted. Recovery turns
      // back on by itself as soon as you start a new drawing (scheduleAutosave).
      if (typeof clearAutosave === 'function') clearAutosave();
      if (localOnly) {
        // Saved to this device only (no server, or a temporary server/network
        // failure). Be honest — this is NOT a shared post.
        statusLabel.textContent = 'Saved on this device only';
        showToast('Saved locally — works on this device', null);
      } else {
        showToast('Posted! 🎨', null);
      }
      if (watchBtn && lastPostUrl) watchBtn.hidden = false;
    } catch (e) {
      setState('error');
      if (e && e.message) statusLabel.textContent = e.message;
    }
  }

  captionInput.addEventListener('input', updateCharCount);
  submitBtn.addEventListener('click', submit);
  if (watchBtn) watchBtn.addEventListener('click', () => {
    if (!lastPostUrl) return;
    if (lastPostUrl.charAt(0) === '#') {
      // Local fallback: #skribl=<id> — boot the in-page player via the hash.
      location.hash = lastPostUrl;
      location.reload();
    } else {
      // Server post: a real /s/<id> path — navigate to the player route.
      location.href = lastPostUrl;
    }
  });

  // Recompute the keyboard lift when the viewport changes or a field is focused.
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', applyKeyboardInset);
    window.visualViewport.addEventListener('scroll', applyKeyboardInset);
  }
  titleInput.addEventListener('focus', () => setTimeout(applyKeyboardInset, 100));
  captionInput.addEventListener('focus', () => setTimeout(applyKeyboardInset, 100));

  // Backdrop tap / Escape / handle tap all close — but never mid-send.
  overlay.addEventListener('click', (e) => {
    if (posting) return;
    if (!e.target.closest('.menu-sheet')) closePost();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden && !posting) closePost();
  });
  const postHandle = sheet ? sheet.querySelector('.menu-handle') : null;
  if (postHandle) postHandle.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!posting) closePost();
  });

  // The Post button in the header opens the composer.
  postBtn.addEventListener('click', openPost);
})();

// ==================== READ-ONLY PLAYER ====================
// Two ways to enter the read-only player, ONE code path once the post is in hand:
//   (a) Flask path player — the /s/<id> template sets window.SKRIBL_MODE="player"
//       and window.SKRIBL_PLAYER_ID. We fetch the post from SKRIBL_API_BASE.
//   (b) Local hash player — a #skribl=<id> hash (from the localStorage fallback
//       post). We read it back out of localStorage.
// Neither present → this is the editor, so bail and leave it untouched. Both
// sources yield the same wrapper shape { title, caption, hasAudio, skribl }, so
// everything below (canvas sizing, loadSkribl, the playback orchestrator) is
// identical regardless of source. It reuses loadSkribl() + the shared Play path
// (replayTimelineToCanvas), so the player is never a second timeline loop.
// A load failure used to show a transient toast and return, leaving the visitor
// on a blank dark page once the toast faded (the player shell stays hidden until
// a load succeeds). Instead, surface a persistent error panel with a retry and a
// link to the editor. Enters player-mode and hides the shell so the panel is the
// only thing shown.
function showPlayerError(msg) {
  document.body.classList.add('player-mode');
  const shell = document.getElementById('playerShell');
  if (shell) shell.hidden = true;
  const err = document.getElementById('playerError');
  if (!err) { showToast(msg, null); return; }   // fallback if markup is absent
  const m = document.getElementById('playerErrorMsg');
  if (m && msg) m.textContent = msg;
  err.hidden = false;
  const retry = document.getElementById('playerRetryBtn');
  if (retry && !retry._wired) {
    retry._wired = true;
    retry.addEventListener('click', () => location.reload());
  }
}

(async function initPlayer() {
  const mode = (typeof window !== 'undefined' && window.SKRIBL_MODE) || null;
  const hashMatch = (location.hash || '').match(/^#skribl=(.+)$/);

  let post;
  if (mode === 'player' && window.SKRIBL_PLAYER_ID) {
    // Flask path player. Enter player-mode immediately so the editor chrome
    // never flashes while the fetch is in flight.
    document.body.classList.add('player-mode');
    const apiBase = window.SKRIBL_API_BASE || '/api/skribls';
    const pid = window.SKRIBL_PLAYER_ID;
    try {
      const res = await fetch(apiBase + '/' + encodeURIComponent(pid));
      if (!res.ok) {
        showPlayerError(res.status === 404 ? "This Skribl couldn't be found." : "Couldn't load this Skribl.");
        return;
      }
      // Server envelope: { id, title, caption, hasAudio, createdAt, author, skribl }
      post = await res.json();
    } catch (e) { showPlayerError("Couldn't load this Skribl."); return; }
  } else if (hashMatch) {
    const id = decodeURIComponent(hashMatch[1]);
    try {
      const raw = localStorage.getItem('skribl_post_' + id);
      if (!raw) { showPlayerError("This Skribl isn't saved on this device."); return; }
      post = JSON.parse(raw);
    } catch (e) { showPlayerError("Couldn't load this Skribl."); return; }
  } else {
    return;   // editor mode — leave the app untouched
  }

  // Accept the wrapper { ..., skribl } or a bare serializeSkribl() object.
  const raw = post && post.skribl ? post.skribl : post;
  // Valid if it carries a format marker: legacy (version) or frame-format (schemaVersion/frames).
  if (!raw || (raw.version == null && raw.schemaVersion == null && !raw.frames)) { showPlayerError('This Skribl looks invalid.'); return; }
  // Canonicalize so every downstream read is uniform.
  const data = normalizeSkribl(raw);
  // Valid if it's a legacy Skribl (version) OR a frame-format one (schemaVersion/frames).
  if (!data || (data.version == null && data.schemaVersion == null && !data.frames)) { showPlayerError('This Skribl looks invalid.'); return; }

  document.body.classList.add('player-mode');

  const shell = document.getElementById('playerShell');
  if (shell) shell.hidden = false;
  const titleEl = document.getElementById('playerTitle');
  const capEl = document.getElementById('playerCaption');
  if (titleEl) titleEl.textContent = post.title || data.title || 'Untitled Skribl';
  if (capEl) {
    const c = post.caption || '';
    capEl.textContent = c;
    capEl.hidden = !c;
  }

  // Reproduce the authoring canvas dimensions exactly, so recorded (CSS-pixel)
  // stroke coordinates map 1:1 and every reused draw path stays pixel-accurate.
  const cs = data.canvasSize || {};
  const authorW = Math.round(cs.cssWidth || canvas.getBoundingClientRect().width || 320);
  const authorH = Math.round(cs.cssHeight || canvas.getBoundingClientRect().height || 320);
  // Fit the authored dimensions into the viewport with ONE uniform scale
  // (aspect locked, never stretched, never upscaled past 1:1). Split in two:
  //   layoutPlayerCanvas() — sets only the CSS *display* size. Safe to re-run;
  //     it never touches the backing store, so it never clears the canvas.
  //   sizePlayerCanvas()   — display size + backing store + transform. The
  //     backing-store write clears pixels, so this runs once, before the poster
  //     frame is painted.
  // The backing store stays at author size × dpr, so ctx.scale(dpr) keeps
  // recorded CSS-pixel stroke coords 1:1 — only the CSS display size shrinks.
  // The player app is a centered flex column: [canvas-wrap] — gap — [player
  // shell]. To fit the canvas without the page scrolling, reserve the ACTUAL
  // vertical space taken by the shell + the app's top/bottom padding + the column
  // gap, measured live. A hardcoded reserve (was 220px) underestimated the shell
  // — it measures ~243px bare and ~267px with a caption, and with the 40px app
  // padding + 20px gap on top, that produced 80–100px of overflow and vertical
  // scroll. Falls back to a safe constant if the shell can't be measured yet.
  function playerReservedV() {
    const shellEl = document.getElementById('playerShell');
    const appEl = document.querySelector('.app');
    if (!shellEl || shellEl.hidden || !appEl) return 300;
    const cs = getComputedStyle(appEl);
    const padV = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
    const gap = (parseFloat(cs.rowGap) || parseFloat(cs.gap) || 0);
    return shellEl.getBoundingClientRect().height + padV + gap;
  }
  function playerFitScale() {
    // Clamp the viewport budget so a short viewport (or an on-screen keyboard)
    // can't drive the available height ≤ 0 and flip the scale negative.
    const availW = Math.max(120, window.innerWidth - 40);
    const availH = Math.max(96, window.innerHeight - playerReservedV());
    return Math.min(1, availW / authorW, availH / authorH);
  }
  function layoutPlayerCanvas() {
    const scale = playerFitScale();
    const dispW = Math.round(authorW * scale);
    const dispH = Math.round(authorH * scale);
    canvasWrap.style.width = dispW + 'px';
    canvasWrap.style.height = dispH + 'px';
    canvas.style.width = dispW + 'px';
    canvas.style.height = dispH + 'px';
  }
  function sizePlayerCanvas() {
    const dpr = window.devicePixelRatio || 1;
    layoutPlayerCanvas();
    canvas.width = Math.round(authorW * dpr);
    canvas.height = Math.round(authorH * dpr);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }
  sizePlayerCanvas();
  // Rotate/resize should refit the display size without clearing the frame the
  // player has already painted — so re-layout CSS only. The backing store is
  // dpr-invariant here, so the existing pixels stay valid at the new CSS size.
  window.addEventListener('resize', layoutPlayerCanvas);
  window.addEventListener('orientationchange', layoutPlayerCanvas);
  // Caption wrapping or responsive control layout can change the shell height
  // without a window resize; re-fit (CSS display size only — never clears) when
  // it does. Observing the shell and mutating the sibling wrap can't loop.
  if (window.ResizeObserver) {
    const shellEl = document.getElementById('playerShell');
    if (shellEl) new ResizeObserver(() => layoutPlayerCanvas()).observe(shellEl);
  }

  // Restore all state and paint the finished drawing as the poster frame.
  loadSkribl(data);

  // ---- Player-owned playback orchestrator ----
  // Reuses the shared timeline + replayTimelineToCanvas core (NO second replay
  // loop) but drives it with its own clock, so we get true pause/resume, a
  // progress bar, and looping. Compositing reuses clearAndRestore (baseSnapshot);
  // the photo shows through from the DOM layer loadSkribl already positioned.
  const timeline = buildPlaybackTimeline();
  // Flip playback (multi-frame): cycle whole frames at fps instead of replaying
  // one frame's strokes. Gated on playbackMode/flip so single-frame replays are
  // completely unaffected. Media (bg color + photo) sit behind the canvas from
  // loadSkribl(frame 0), so clearing the canvas per frame shows them through.
  const isFlip = data.playbackMode === 'flip' && Array.isArray(data.frames) && data.frames.length > 1;
  const flipFrames = isFlip ? data.frames : null;
  const flipFps = data.fps || 12;
  const flipDurMs = isFlip ? Math.max(1, (flipFrames.length / flipFps) * 1000) : 0;
  function drawFlipFrame(fi) {
    const s = getCanvasLogicalSize();
    ctx.clearRect(0, 0, s.width, s.height);
    const fr = flipFrames[Math.max(0, Math.min(flipFrames.length - 1, fi))];
    if (fr && Array.isArray(fr.strokes) && fr.strokes.length) paintStrokesStatic(fr.strokes);
  }
  const totalMs = isFlip ? flipDurMs : (timeline.length ? timeline[timeline.length - 1].playT : 0);

  const pPlay = document.getElementById('playerPlayBtn');
  const pRestart = document.getElementById('playerRestartBtn');
  const pLoop = document.getElementById('playerLoopBtn');
  const pMute = document.getElementById('playerMuteBtn');
  const pCopy = document.getElementById('playerCopyBtn');
  const pFill = document.getElementById('playerProgressFill');
  const pTrack = document.getElementById('playerProgress');

  const ICON_PLAY_P = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
  const ICON_PAUSE_P = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>';
  const ICON_SOUND_P = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>';
  const ICON_MUTED_P = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';

  let running = false;
  let rafId = null;
  let elapsedBase = 0;   // ms elapsed before the current run segment
  let segStart = 0;      // performance.now() at the current segment's start
  let idx = 0;           // next timeline index to draw
  let loop = false;
  let strokeComp = null; // wet/dry stroke compositor for low-opacity replay (flag-gated)
  let muted = false;

  function setPlayIcon() {
    if (!pPlay) return;
    pPlay.innerHTML = running ? ICON_PAUSE_P : ICON_PLAY_P;
    pPlay.setAttribute('aria-label', running ? 'Pause' : 'Play');
  }
  function setProgress(frac) {
    if (pFill) pFill.style.width = Math.max(0, Math.min(1, frac)) * 100 + '%';
  }
  // A small nib that rides the current replay point so watching reads as a hand
  // drawing rather than lines appearing. Player-only; positioned in display px
  // inside canvasWrap (which loadSkribl/sizePlayerCanvas size to the fitted
  // display rect). It reads the same timeline points the replay draws — no new
  // timing loop, no effect on the drawing itself.
  const nib = document.createElement('div');
  nib.className = 'player-nib';
  nib.hidden = true;
  if (canvasWrap) canvasWrap.appendChild(nib);
  function nibScale() {
    // Authored CSS px -> current display px. canvasWrap is the fitted rect, so
    // its width over the authored width is the live scale (handles rotate/resize).
    const dispW = (canvasWrap && canvasWrap.clientWidth) || authorW;
    return authorW ? dispW / authorW : 1;
  }
  function showNibAtIndex(nextIdx) {
    // replayTimelineToCanvas returns the NEXT index, so the point just drawn is
    // nextIdx - 1. Nothing drawn yet (index 0) -> keep the nib hidden.
    const p = nextIdx > 0 ? timeline[nextIdx - 1] : null;
    if (!p) { nib.hidden = true; return; }
    const s = nibScale();
    nib.style.left = (p.x * s) + 'px';
    nib.style.top = (p.y * s) + 'px';
    nib.classList.toggle('erase', !!p.erase);
    // Tint the bead to the ink; erasing keeps the neutral hollow ring.
    if (!p.erase) nib.style.setProperty('--nib-rgb', nibRGB(p.color));
    nib.hidden = false;
  }
  function hideNib() { nib.hidden = true; }
  // Keep a paused/idle nib aligned if the viewport changes scale under it.
  window.addEventListener('resize', () => { if (!nib.hidden) showNibAtIndex(idx); });
  // ---- Player audio: gapless Web Audio loop bed --------------------------
  // Play the SAME loop the post bakes instead of the raw <audio>:
  // buildLoopAudioBuffer() folds the crossfade and slices [trimStart,trimEnd]
  // into one AudioBuffer, played on an AudioBufferSourceNode with loop=true so
  // the wrap is sample-accurate — gapless and drift-free, matching the editor's
  // live monitor. We own a GainNode (mute) and start the source at a phase
  // offset from the drawing clock so play/resume/seek stay aligned under the
  // replay. The decoded source + trim/crossfade state are set by loadSkribl().
  let paSource = null, paGain = null, paBuffer = null;
  function paLoopBuffer() {
    // Build once and cache — the player's trims/crossfade don't change post-load.
    if (!paBuffer) { try { paBuffer = buildLoopAudioBuffer(); } catch (e) { paBuffer = null; } }
    return paBuffer;
  }
  function paStop() {
    if (paSource) {
      try { paSource.stop(); } catch (e) {}
      try { paSource.disconnect(); } catch (e) {}
      paSource = null;
    }
  }
  // Start the loop bed aligned to a drawing-elapsed position (ms). Returns false
  // (a no-op) if audio isn't decoded yet — the drawing still plays and a later
  // start (next play/seek) picks the audio up once the buffer is ready.
  function paStartAtElapsed(elapsedMs) {
    if (!audioCtx) return false;
    const buf = paLoopBuffer();
    if (!buf) return false;
    paStop();
    if (audioCtx.state === 'suspended') { try { audioCtx.resume(); } catch (e) {} }
    if (!paGain) { paGain = audioCtx.createGain(); paGain.connect(audioCtx.destination); }
    paGain.gain.value = muted ? 0 : 1;
    const dur = buf.duration;
    const offset = dur > 0 ? (((elapsedMs / 1000) % dur) + dur) % dur : 0;
    const src = audioCtx.createBufferSource();
    src.buffer = buf; src.loop = true; src.loopStart = 0; src.loopEnd = dur;
    src.connect(paGain);
    try { src.start(0, offset); } catch (e) { return false; }
    paSource = src;
    return true;
  }
  // Loop bed replaces <audio>; the gapless source loops itself, so frame() no
  // longer wraps the audio. elapsedBase carries the aligned position on resume.
  function audioStart() { paStartAtElapsed(elapsedBase); }
  function audioPause() { paStop(); }

  // ---- Scrubbing ----
  // Seek to a fraction of the timeline: recomposite the base frame, then replay
  // from index 0 up to the target elapsed via the shared replay helper (no
  // second loop). elapsedBase carries the seek position; a subsequent play()
  // resumes from there. Audio is moved to the matching point in its loop window
  // so the music follows the scrubber instead of restarting or lagging behind.
  let wasRunning = false;
  function seekTo(frac) {
    frac = Math.max(0, Math.min(1, frac));
    const targetMs = totalMs * frac;
    cancelAnimationFrame(rafId);
    running = false;
    setPlayIcon();
    if (isFlip) {
      const cycT = flipDurMs ? (targetMs % flipDurMs) : 0;
      drawFlipFrame(Math.floor((cycT / 1000) * flipFps));
      elapsedBase = targetMs; setProgress(frac); hideNib();
      return;
    }
    const paint = () => {
      if (strokeLayersOn()) {
        strokeComp = makeStrokeCompositor(ctx, canvas);
        idx = replayTimelineToCanvas(timeline, 0, targetMs, strokeComp.dotFn, strokeComp.lineFn);
        strokeComp.present();   // no finish(): the stroke at the playhead stays mid-draw
      } else {
        strokeComp = null;
        idx = replayTimelineToCanvas(timeline, 0, targetMs, drawDot, drawLine);
      }
      elapsedBase = targetMs;
      setProgress(frac);
      showNibAtIndex(idx);
      // Audio alignment is handled on resume: elapsedBase (= targetMs) drives the
      // loop-bed phase offset in audioStart(), so there's no per-seek audio work.
      // (Playback is paused during a scrub; the bed restarts aligned on release.)
    };
    clearAndRestore(paint);   // clear + redraw baseSnapshot, then replay to target
  }
  function fracFromEvent(e) {
    const rect = pTrack.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    return (clientX - rect.left) / rect.width;
  }

  function frame() {
    const elapsed = elapsedBase + (performance.now() - segStart);
    if (isFlip) {
      const cycT = flipDurMs ? (elapsed % flipDurMs) : 0;
      drawFlipFrame(Math.floor((cycT / 1000) * flipFps));
      setProgress(flipDurMs ? cycT / flipDurMs : 1);
      hideNib();
      if (!loop && elapsed >= flipDurMs) { drawFlipFrame(flipFrames.length - 1); onEnded(); return; }
      rafId = requestAnimationFrame(frame);
      return;
    }
    if (strokeComp) {
      idx = replayTimelineToCanvas(timeline, idx, elapsed, strokeComp.dotFn, strokeComp.lineFn);
      strokeComp.present();
    } else {
      idx = replayTimelineToCanvas(timeline, idx, elapsed, drawDot, drawLine);
    }
    setProgress(totalMs ? elapsed / totalMs : 1);
    showNibAtIndex(idx);
    if (idx < timeline.length) rafId = requestAnimationFrame(frame);
    else { if (strokeComp) { strokeComp.finish(); strokeComp.present(); showNibAtIndex(idx); } onEnded(); }
  }

  function play() {
    if (running || (!timeline.length && !isFlip)) return;
    // Unlock the AudioContext inside the click gesture: begin() below can run in
    // an async image onload on the first fresh play, which is outside the gesture
    // and would leave the context suspended on stricter browsers (iOS Safari).
    if (audioCtx && audioCtx.state === 'suspended') { try { audioCtx.resume(); } catch (e) {} }
    const fresh = idx === 0;
    const begin = () => {
      running = true;
      if (fresh) strokeComp = strokeLayersOn() ? makeStrokeCompositor(ctx, canvas) : null;
      segStart = performance.now();
      audioStart();
      rafId = requestAnimationFrame(frame);
      setPlayIcon();
    };
    if (fresh) {
      elapsedBase = 0;
      setProgress(0);
      hideNib();                // clear any nib left from a prior paused run
      clearAndRestore(begin);   // clear + redraw baseSnapshot, then start
    } else {
      begin();                  // resume: keep the partial drawing on canvas
    }
  }

  function pause() {
    if (!running) return;
    running = false;
    cancelAnimationFrame(rafId);
    elapsedBase += performance.now() - segStart;
    audioPause();
    setPlayIcon();
  }

  function restart() {
    cancelAnimationFrame(rafId);
    running = false;
    audioPause();
    elapsedBase = 0;
    idx = 0;
    play();
  }

  function onEnded() {
    running = false;
    audioPause();
    setProgress(1);
    hideNib();   // finished poster shows without the nib
    // Reset so the next Play restarts cleanly rather than resuming at the end.
    elapsedBase = 0;
    idx = 0;
    setPlayIcon();
    if (loop) restart();
  }

  if (pPlay) pPlay.addEventListener('click', () => { running ? pause() : play(); });
  if (pRestart) pRestart.addEventListener('click', restart);
  if (pLoop) pLoop.addEventListener('click', () => {
    loop = !loop;
    pLoop.classList.toggle('active', loop);
    pLoop.setAttribute('aria-pressed', loop ? 'true' : 'false');
  });
  // Mute toggle — gate on the wrapper's hasAudio flag, NOT on audioEl, because
  // audioEl is created async by loadSkribl() and is still null here. audioStart()
  // applies the muted state whenever playback actually begins.
  if (pMute) {
    if (post.hasAudio) {
      pMute.hidden = false;
      pMute.addEventListener('click', () => {
        muted = !muted;
        if (paGain) paGain.gain.value = muted ? 0 : 1;
        pMute.classList.toggle('active', muted);
        pMute.innerHTML = muted ? ICON_MUTED_P : ICON_SOUND_P;
        pMute.setAttribute('aria-label', muted ? 'Unmute' : 'Mute');
        pMute.setAttribute('aria-pressed', muted ? 'true' : 'false');
      });
    } else {
      pMute.hidden = true;
    }
  }
  // Drag-to-seek on the progress track. Pause playback while dragging, seek to
  // the release point, and resume if it had been playing.
  if (pTrack) {
    let scrubbing = false;
    const onScrubStart = (e) => {
      e.preventDefault();
      scrubbing = true;
      wasRunning = running;
      if (running) pause();
      seekTo(fracFromEvent(e));
      window.addEventListener('mousemove', onScrubMove);
      window.addEventListener('mouseup', onScrubEnd);
      window.addEventListener('touchmove', onScrubMove, { passive: false });
      window.addEventListener('touchend', onScrubEnd);
    };
    const onScrubMove = (e) => {
      if (!scrubbing) return;
      if (e.cancelable) e.preventDefault();
      seekTo(fracFromEvent(e));
    };
    const onScrubEnd = () => {
      if (!scrubbing) return;
      scrubbing = false;
      window.removeEventListener('mousemove', onScrubMove);
      window.removeEventListener('mouseup', onScrubEnd);
      window.removeEventListener('touchmove', onScrubMove);
      window.removeEventListener('touchend', onScrubEnd);
      // Resume only if not already at the very end.
      if (wasRunning && idx < timeline.length) play();
    };
    pTrack.style.cursor = 'pointer';
    pTrack.addEventListener('mousedown', onScrubStart);
    pTrack.addEventListener('touchstart', onScrubStart, { passive: false });
  }

  if (pCopy) pCopy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      showToast('Link copied', null);
    } catch (e) {
      showToast('Couldn\u2019t copy — long-press the address bar', null);
    }
  });

  setPlayIcon();
  setProgress(0);
})();

// ---------- Image / Music on-off toggles ----------
function syncLayerToggle(el, on) {
  if (!el) return;
  el.classList.toggle('on', on);
  el.setAttribute('aria-checked', String(on));
}
function resetPhotoToggle() { photoEnabled = true; syncLayerToggle(document.getElementById('photoToggle'), true); }
function resetMusicToggle() { musicEnabled = true; syncLayerToggle(document.getElementById('musicToggle'), true); }
(function initLayerToggles() {
  const pt = document.getElementById('photoToggle');
  if (pt) pt.addEventListener('click', (e) => {
    e.stopPropagation();
    photoEnabled = !photoEnabled;
    syncLayerToggle(pt, photoEnabled);
    if (photoBgImg) photoBgImg.style.display = (photoEnabled && photoBgImg.src) ? 'block' : 'none';
    if (typeof updateRepositionUI === 'function') updateRepositionUI();
  });
  const mt = document.getElementById('musicToggle');
  if (mt) mt.addEventListener('click', (e) => {
    e.stopPropagation();
    musicEnabled = !musicEnabled;
    syncLayerToggle(mt, musicEnabled);
    if (!musicEnabled && audioEl) audioEl.pause();
  });
})();


// ===========================================================================
// Canvas magnify (editor only) — zoom + pan of the display, never the drawing.
//
// Mechanic: only #zoomLayer is CSS-transformed (translate + scale). The
// drawing's backing store and every stroke coordinate stay in the fixed
// authored space, so getPos()/eraser-cursor/eyedropper/replay/serialize are all
// untouched — they read canvas.getBoundingClientRect(), which already reflects
// the transform, so they self-correct. .canvas-wrap (overflow:hidden) is the
// fixed viewport clip. Controls (#zoomHud) are a SIBLING of the layer, so they
// stay put while the content magnifies.
//
// The whole module is guarded on #zoomLayer, which the player template does not
// have, so ZoomView stays null there and nothing below runs.
// ===========================================================================

// --- pinch gesture (called from startDraw when a 2nd finger lands) ----------
let _pinch = null;   // { startDist, lastDist, lastMid }

function _touchMid(t0, t1) {
  const r = canvasWrap.getBoundingClientRect();
  return { x: (t0.clientX + t1.clientX) / 2 - r.left,
           y: (t0.clientY + t1.clientY) / 2 - r.top };
}
function _touchDist(t0, t1) {
  return Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY);
}

// Undo the nascent 1-finger stroke the first finger began just before the
// second landed — restore the pre-stroke snapshot startDraw pushed, and if that
// stroke had auto-armed a fresh recording, unwind it too. So a pinch never
// leaves a stray dot or a phantom take.
function abortStrokeForPinch() {
  const wasAutoArmed = _autoArmedThisStroke;
  if (drawing) {
    const snap = undoStack.pop();
    if (snap) {
      const { width: cw, height: ch } = getCanvasLogicalSize();
      ctx.save();
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, cw, ch);
      if (snap.image) ctx.drawImage(snap.image, 0, 0, cw, ch);
      ctx.restore();
      strokes = snap.strokes.slice();
      strokeGroups = snap.strokeGroups.slice();
      hasContent = snap.hasContent;
    }
    drawing = false;
    _slActive = false;
    currentStroke = [];
    document.body.classList.remove('stroking');
    if (undoStack.length === 0) undoBtn.disabled = true;
    updateClearVisibility();
    updateEmptyHint();
  }
  // Roll back an auto-armed recording that captured nothing (blank-canvas pinch).
  if (wasAutoArmed && recording && strokes.length === 0) {
    clearInterval(recTimerInterval);
    recording = false;
    recorded = false;
    finishedRecording = false;
    startTime = null;
    preRecordSnapshot = null;
    recordBtn.innerHTML = ICON_RECORD + LABEL_RECORD;
    recordBtn.classList.remove('active');
    canvasWrap.classList.remove('recording');
  document.body.classList.remove('recording');
    recIndicator.hidden = true;
    document.querySelector('.header').classList.remove('compact');
    updateCanvasLockCue();
    updateClearVisibility();
  }
  _autoArmedThisStroke = false;
}

function beginPinch(e) {
  // Image reposition owns its own gestures; leave it alone.
  if (typeof repositioning !== 'undefined' && repositioning) return;
  if (!ZoomView) return;
  // A pinch turns the magnifier on if it's off — pinching should never feel dead.
  if (typeof ZoomView.enabled === 'function' && !ZoomView.enabled()) {
    if (typeof ZoomView.enable === 'function') ZoomView.enable();
  }
  if (!e.touches || e.touches.length < 2) return;
  if (typeof e.preventDefault === 'function') e.preventDefault();
  abortStrokeForPinch();
  pinching = true;
  const t0 = e.touches[0], t1 = e.touches[1];
  _pinch = { startDist: _touchDist(t0, t1), lastDist: _touchDist(t0, t1), lastMid: _touchMid(t0, t1) };
}

function _pinchMove(e) {
  if (!pinching || !_pinch) return;
  if (!e.touches || e.touches.length < 2) return;
  e.preventDefault();
  const t0 = e.touches[0], t1 = e.touches[1];
  const dist = _touchDist(t0, t1);
  const mid = _touchMid(t0, t1);
  if (_pinch.lastDist > 0) {
    const factor = dist / _pinch.lastDist;
    ZoomView.zoomAt(factor, mid.x, mid.y);       // scale about the pinch midpoint
  }
  ZoomView.panBy(mid.x - _pinch.lastMid.x, mid.y - _pinch.lastMid.y);  // two-finger pan
  _pinch.lastDist = dist;
  _pinch.lastMid = mid;
}

function _pinchEnd(e) {
  if (!pinching) return;
  // End the pinch as soon as we drop below two fingers. A single remaining
  // finger will NOT resume drawing (it never fired a fresh touchstart); the user
  // lifts and taps again to draw — standard, and avoids a stray line.
  if (e.touches && e.touches.length >= 2) return;
  pinching = false;
  _pinch = null;
}

window.addEventListener('touchmove', _pinchMove, { passive: false });
window.addEventListener('touchend', _pinchEnd);
window.addEventListener('touchcancel', _pinchEnd);

// --- zoom controller + pill -------------------------------------------------
(function initCanvasZoom() {
  const layer = document.getElementById('zoomLayer');
  const hud = document.getElementById('zoomHud');
  if (!layer || !hud) return;                                  // player: no-op
  if (document.body.classList.contains('player-mode')) return;

  const MIN = 1, MAX = 4, STEP = 0.5;
  let zoom = 1, panX = 0, panY = 0;
  let magnifyOn = false;   // the header magnifier toggle gates the whole feature

  function wrapSize() {
    const r = canvasWrap.getBoundingClientRect();
    return { w: r.width || 1, h: r.height || 1 };
  }
  function clampPan() {
    const { w, h } = wrapSize();
    // Keep the magnified content covering the viewport (no empty gaps).
    panX = Math.min(0, Math.max(w * (1 - zoom), panX));
    panY = Math.min(0, Math.max(h * (1 - zoom), panY));
    if (zoom <= 1) { panX = 0; panY = 0; }
  }
  function render(animate) {
    clampPan();
    layer.classList.toggle('zoom-anim', !!animate);
    layer.style.transform = zoom === 1 ? '' : 'translate(' + panX + 'px,' + panY + 'px) scale(' + zoom + ')';
    const val = document.getElementById('zoomVal');
    if (val) val.textContent = Math.round(zoom * 100) + '%';
    hud.classList.toggle('zoomed', zoom > 1.001);
    const zin = document.getElementById('zoomInBtn');
    const zout = document.getElementById('zoomOutBtn');
    if (zin) zin.disabled = zoom >= MAX - 0.001;
    if (zout) zout.disabled = zoom <= MIN + 0.001;
    if (animate) setTimeout(function () { layer.classList.remove('zoom-anim'); }, 200);
    if (typeof maybePanHint === 'function') maybePanHint();
  }

  ZoomView = {
    isZoomed: function () { return zoom > 1.001; },
    enabled: function () { return magnifyOn; },
    enable: function () { if (!magnifyOn) setMagnify(true); },
    get: function () { return { zoom: zoom, panX: panX, panY: panY }; },
    // Scale by `factor` about viewport point (cx,cy), keeping the content under
    // that point fixed. Used by both pinch and the +/- buttons.
    zoomAt: function (factor, cx, cy) {
      const nz = Math.min(MAX, Math.max(MIN, zoom * factor));
      if (nz === zoom) return;
      const coordX = (cx - panX) / zoom, coordY = (cy - panY) / zoom;
      panX = cx - coordX * nz;
      panY = cy - coordY * nz;
      zoom = nz;
      render(false);
    },
    panBy: function (dx, dy) { panX += dx; panY += dy; render(false); },
    step: function (dir) {
      const { w, h } = wrapSize();
      const nz = Math.min(MAX, Math.max(MIN, zoom + dir * STEP));
      this.zoomAt(nz / zoom, w / 2, h / 2);
      render(true);
    },
    fit: function () { zoom = 1; panX = 0; panY = 0; render(true); },
    // Set an exact zoom percentage (from the type-in field), about the viewport
    // center, clamped to the allowed range.
    setPct: function (pct) {
      const s = wrapSize();
      const target = Math.min(MAX, Math.max(MIN, (pct || 0) / 100));
      this.zoomAt(target / zoom, s.w / 2, s.h / 2);
      render(true);
    }
  };

  document.getElementById('zoomInBtn').addEventListener('click', function () { ZoomView.step(1); });
  document.getElementById('zoomOutBtn').addEventListener('click', function () { ZoomView.step(-1); });
  document.getElementById('zoomFitBtn').addEventListener('click', function () { ZoomView.fit(); });

  // Header magnifier: a toggle that shows/hides the zoom pill. Turning it OFF
  // also resets to 100% so you're never left magnified with no controls. While
  // off, pinch / wheel / Space-drag all no-op (they check ZoomView.enabled()).
  const magnifyBtn = document.getElementById('magnifyBtn');
  function setMagnify(on) {
    magnifyOn = on;
    hud.hidden = !on;
    if (magnifyBtn) {
      magnifyBtn.classList.toggle('active', on);
      magnifyBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    }
    if (!on) ZoomView.fit();     // return the canvas to 100% when hiding controls
  }
  if (magnifyBtn) magnifyBtn.addEventListener('click', function () { setMagnify(!magnifyOn); });

  // Click the % to type an exact zoom — the precise path for desktop (no pinch),
  // and a numeric-keypad shortcut on touch. Enter/blur commits, Escape cancels.
  const valEl = document.getElementById('zoomVal');
  valEl.title = 'Click to type a zoom %';
  valEl.addEventListener('click', function () {
    if (valEl.querySelector('input')) return;               // already editing
    const cur = Math.round(ZoomView.get().zoom * 100);
    valEl.textContent = '';
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.inputMode = 'numeric';
    inp.setAttribute('enterkeyhint', 'done');
    inp.maxLength = 4;
    inp.className = 'zoom-val-input';
    inp.value = String(cur);
    valEl.appendChild(inp);
    // Transparent backdrop over the canvas: guarantees a tap anywhere else
    // commits and dismisses the keypad WITHOUT starting a stroke. Needed because
    // the canvas's touchstart preventDefault (iOS especially) otherwise swallows
    // the input's blur, stranding the field open.
    const backdrop = document.createElement('div');
    backdrop.className = 'zoom-edit-backdrop';
    canvasWrap.appendChild(backdrop);
    inp.focus();
    inp.select();
    let done = false;
    function commit(apply) {
      if (done) return;
      done = true;
      if (backdrop.parentNode) backdrop.remove();
      const n = apply ? parseInt(inp.value, 10) : NaN;
      if (!isNaN(n)) {
        ZoomView.setPct(n);        // render() inside rewrites the label (drops input)
      } else {
        if (inp.parentNode) inp.remove();
        render(false);             // restore the "N%" label unchanged
      }
    }
    backdrop.addEventListener('pointerdown', function (e) { e.preventDefault(); commit(true); });
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); commit(true); }
      else if (e.key === 'Escape') { e.preventDefault(); commit(false); }
    });
    inp.addEventListener('blur', function () { commit(true); });
  });

  // Re-clamp on resize/rotate (viewport bounds change under a live zoom).
  window.addEventListener('resize', function () { if (zoom > 1) render(false); });

  // --- grip: drag the pill, dock to the nearest corner ----------------------
  const grip = document.getElementById('zoomGrip');
  let snapEl = null, dragging = false, grabDX = 0, grabDY = 0;

  function corners() {
    const r = canvasWrap.getBoundingClientRect();
    const pw = hud.offsetWidth, ph = hud.offsetHeight, m = 12;
    return {
      tl: { key: 'tl', x: m,               y: m },
      tr: { key: 'tr', x: r.width - pw - m, y: m },
      bl: { key: 'bl', x: m,               y: r.height - ph - m },
      br: { key: 'br', x: r.width - pw - m, y: r.height - ph - m }
    };
  }
  function nearestCorner(x, y) {
    const c = corners();
    let best = null, bd = Infinity;
    for (const k in c) {
      const d = Math.hypot(x - c[k].x, y - c[k].y);
      if (d < bd) { bd = d; best = c[k]; }
    }
    return best;
  }
  function pointer(ev) {
    const t = ev.touches ? ev.touches[0] : ev;
    return { x: t.clientX, y: t.clientY };
  }
  function gripStart(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    const r = hud.getBoundingClientRect();
    const wrapR = canvasWrap.getBoundingClientRect();
    const p = pointer(ev);
    grabDX = p.x - r.left;
    grabDY = p.y - r.top;
    dragging = true;
    hud.classList.add('dragging');
    // switch from corner-anchoring to free left/top positioning
    hud.style.right = 'auto';
    hud.style.bottom = 'auto';
    hud.style.left = (r.left - wrapR.left) + 'px';
    hud.style.top = (r.top - wrapR.top) + 'px';
    // snap ghost
    snapEl = document.createElement('div');
    snapEl.className = 'zoom-snap';
    snapEl.style.height = hud.offsetHeight + 'px';
    canvasWrap.appendChild(snapEl);
    if (ev.type === 'mousedown') {
      window.addEventListener('mousemove', gripMove);
      window.addEventListener('mouseup', gripEnd);
    } else {
      window.addEventListener('touchmove', gripMove, { passive: false });
      window.addEventListener('touchend', gripEnd);
      window.addEventListener('touchcancel', gripEnd);
    }
  }
  function gripMove(ev) {
    if (!dragging) return;
    ev.preventDefault();
    const wrapR = canvasWrap.getBoundingClientRect();
    const p = pointer(ev);
    let x = p.x - wrapR.left - grabDX;
    let y = p.y - wrapR.top - grabDY;
    // keep within the wrap
    x = Math.max(0, Math.min(wrapR.width - hud.offsetWidth, x));
    y = Math.max(0, Math.min(wrapR.height - hud.offsetHeight, y));
    hud.style.left = x + 'px';
    hud.style.top = y + 'px';
    const near = nearestCorner(x, y);
    if (snapEl) {
      snapEl.style.left = near.x + 'px';
      snapEl.style.top = near.y + 'px';
    }
  }
  function gripEnd(ev) {
    if (!dragging) return;
    dragging = false;
    hud.classList.remove('dragging');
    const wrapR = canvasWrap.getBoundingClientRect();
    const x = parseFloat(hud.style.left) || 0;
    const y = parseFloat(hud.style.top) || 0;
    const near = nearestCorner(x, y);
    // clear inline positioning and re-anchor to the chosen corner via CSS
    hud.style.left = '';
    hud.style.top = '';
    hud.style.right = '';
    hud.style.bottom = '';
    hud.setAttribute('data-corner', near.key);
    if (snapEl) { snapEl.remove(); snapEl = null; }
    window.removeEventListener('mousemove', gripMove);
    window.removeEventListener('mouseup', gripEnd);
    window.removeEventListener('touchmove', gripMove);
    window.removeEventListener('touchend', gripEnd);
    window.removeEventListener('touchcancel', gripEnd);
  }
  grip.addEventListener('mousedown', gripStart);
  grip.addEventListener('touchstart', gripStart, { passive: false });

  // --- Desktop pan (touch already pans with two fingers) --------------------
  // Both paths only act while zoomed, so at 100% nothing changes.
  const finePointer = !!(window.matchMedia && window.matchMedia('(pointer: fine)').matches);
  let panHintShown = false;
  function maybePanHint() {
    if (panHintShown || !finePointer || zoom <= 1.001) return;
    panHintShown = true;
    if (typeof showToast === 'function') showToast('Scroll or Space-drag to move around', null);
  }

  // Scroll wheel pans the magnified view (Shift+wheel → horizontal).
  canvasWrap.addEventListener('wheel', function (e) {
    if (zoom <= 1) return;
    e.preventDefault();
    let dx = e.deltaX, dy = e.deltaY;
    if (e.shiftKey && dx === 0) { dx = dy; dy = 0; }
    panX -= dx; panY -= dy;
    render(false);
  }, { passive: false });

  // Hold Space and drag to grab-pan.
  let spaceHeld = false, spaceDragging = false, lastX = 0, lastY = 0;
  function typingTarget(el) { return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable); }
  window.addEventListener('keydown', function (e) {
    if (e.code === 'Space' && !typingTarget(e.target)) {
      spaceHeld = true;
      if (zoom > 1) { e.preventDefault(); canvasWrap.style.cursor = spaceDragging ? 'grabbing' : 'grab'; }
    }
  });
  window.addEventListener('keyup', function (e) {
    if (e.code === 'Space') { spaceHeld = false; spaceDragging = false; canvasWrap.style.cursor = ''; }
  });
  // Capture phase so a Space-drag claims the mousedown before startDraw fires.
  canvasWrap.addEventListener('mousedown', function (e) {
    if (spaceHeld && zoom > 1) {
      spaceDragging = true; lastX = e.clientX; lastY = e.clientY;
      canvasWrap.style.cursor = 'grabbing';
      e.preventDefault(); e.stopPropagation();
    }
  }, true);
  window.addEventListener('mousemove', function (e) {
    if (!spaceDragging) return;
    panX += e.clientX - lastX; panY += e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    render(false);
  });
  window.addEventListener('mouseup', function () {
    if (spaceDragging) { spaceDragging = false; canvasWrap.style.cursor = spaceHeld ? 'grab' : ''; }
  });

  render(false);
})();
