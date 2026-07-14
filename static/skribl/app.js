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
let recording = false;
let playing = false;
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
  e.preventDefault();
  // Ignore non-primary mouse buttons (right/middle click). A right-click
  // mousedown would otherwise enter here mid-stroke and reset currentStroke,
  // wiping the in-progress stroke from the replay array (still painted live,
  // but gone on playback). Touch events have no .button, so guard on != null
  // so touch drawing still works.
  if (e.button != null && e.button !== 0) return;
  // Eyedropper (fallback path): consume this tap to sample a pixel instead of
  // starting a stroke. Allowed even on a locked canvas — it only reads.
  if (pickingColor) { const p = getPos(e); sampleColorAt(p.x, p.y); return; }
  // Photo reposition mode: this drag moves the background, never the drawing.
  // Returns before the lock check and the undo push, so it can't start a stroke,
  // fire the lock toast, or create an undo entry. Ignored during recording so a
  // take is never blocked.
  if (repositioning && !recording) { beginPhotoDrag(e); return; }
  // Post-record lock: the completed replay can't be drawn over.
  if (finishedRecording && !recording) {
    if (!lockToastShown) {
      showToast('Recording finished — hit Record for a new take from here, or Clear to start over', recordBtn);
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
  }
  const pos = getPos(e);
  drawing = true;
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
}
updateCurrentColorChip();

document.getElementById('sizeGroup').addEventListener('click', (e) => {
  const btn = e.target.closest('.size-btn');
  if (!btn) return;
  size = parseInt(btn.dataset.size, 10);
  document.querySelectorAll('.size-btn').forEach(b => {
    b.classList.toggle('active', b === btn);
    b.style.background = '';
  });
});

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
      clearCanvas();
      if (typeof clearAutosave === 'function') clearAutosave();
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

document.getElementById('tabBar').addEventListener('click', (e) => {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  const tabName = btn.dataset.tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
  updateTabSlider(btn);
  document.getElementById('drawPanel').hidden = tabName !== 'draw';
  document.getElementById('musicPanel').hidden = tabName !== 'music';
  document.getElementById('photoPanel').hidden = tabName !== 'photo';
  if (tabName !== 'photo' && typeof exitReposition === 'function') exitReposition();
  if (typeof pickingColor !== 'undefined' && pickingColor) stopPicking();
  if (tabName === 'photo' && typeof updateRepositionUI === 'function') updateRepositionUI();
  if (tabName === 'music') updateDrawingTimeLabels();
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
    showToast('Take saved — hit Record to add another, or Play to preview', recordBtn);
  }
  updateClearVisibility();
}

recordBtn.addEventListener('click', () => {
  if (!recording) {
    // If a completed take is already on the canvas, continue it as another take
    // (append) instead of wiping and starting over.
    beginRecording(strokes.length > 0);
  } else {
    endRecordingTake();
  }
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
}

function stopPlayback() {
  playing = false;
  playBtn.innerHTML = ICON_PLAY + LABEL_PLAY;
  playBtn.disabled = false;
  playBtn.classList.remove('playing');
  if (audioEl) audioEl.pause();
  if (typeof stopWebAudioLoop === 'function') stopWebAudioLoop();
  hideEditorNib();
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

playBtn.addEventListener('click', () => {
  stopLoopPreview();
  if (playing) {
    stopPlayback();
    return;
  }
  const timeline = buildPlaybackTimeline();
  if (!timeline.length) return;
  playing = true;
  playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg><span class="btn-label">Stop</span>';
  playBtn.classList.add('playing');

  // Compressed playback duration (same timeline the export uses).
  const totalDuration = timeline[timeline.length - 1].playT;

  function startDrawing() {
    let i = 0;
    const start = performance.now();
    const comp = strokeLayersOn() ? makeStrokeCompositor(ctx, canvas) : null;
    function frame() {
      if (!playing) return;
      const elapsed = performance.now() - start;
      if (comp) {
        i = replayTimelineToCanvas(timeline, i, elapsed, comp.dotFn, comp.lineFn);
        comp.present();
      } else {
        i = replayTimelineToCanvas(timeline, i, elapsed, drawDot, drawLine);
      }
      positionEditorNib(i > 0 ? timeline[i - 1] : null);
      if (i < timeline.length) {
        requestAnimationFrame(frame);
      } else {
        if (comp) { comp.finish(); comp.present(); }
        stopPlayback();
      }
    }
    requestAnimationFrame(frame);
  }

  clearAndRestore(() => {
    if (audioEl) {
      playMusicLooped(totalDuration, startDrawing);
    } else {
      startDrawing();
    }
  });
});

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

function closeMenu() {
  menuOverlay.classList.remove('open');
  menuCloseTimer = setTimeout(() => { menuOverlay.hidden = true; }, 350);
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

const helpBtn = document.getElementById('helpBtn');
const helpDrawer = document.getElementById('helpDrawer');
const helpClose = document.getElementById('helpClose');
const helpBackdrop = document.getElementById('helpBackdrop');

let helpCloseTimer = null;

helpBtn.addEventListener('click', () => {
  clearTimeout(helpCloseTimer);
  helpDrawer.hidden = false;
  helpDrawer.classList.remove('closing');
  requestAnimationFrame(() => {
    helpDrawer.classList.add('open');
  });
});

function closeHelpDrawer() {
  clearTimeout(helpCloseTimer);
  helpDrawer.classList.add('closing');
  helpDrawer.classList.remove('open');
  helpCloseTimer = setTimeout(() => {
    helpDrawer.hidden = true;
    helpDrawer.classList.remove('closing');
  }, 250);
}

helpClose.addEventListener('click', closeHelpDrawer);
helpBackdrop.addEventListener('click', closeHelpDrawer);

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
  bubbleStart.textContent = formatTimeH(trimStart);
  bubbleEnd.textContent = formatTimeH(trimEnd);
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
      showToast('Loop set to your drawing length — fine-tune anytime', musicUploadBtn);
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
  const ok = !!loaded && photoFit === 'cover' && !recording;
  btn.hidden = !ok;
  const hint = document.getElementById('repositionHint');
  if (hint) hint.hidden = !ok;
  const zoomRow = document.getElementById('photoZoomRow');
  if (zoomRow) zoomRow.hidden = !ok;
  if (!ok && repositioning) exitReposition();
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
  return {
    version: 1,
    savedAt: new Date().toISOString(),
    baseSnapshot: baseSnapshot,
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    background: { color: bgColor },
    // Metadata only — no bytes. Prefer live media; fall back to pending meta
    // (from a restore where the user hasn't re-added the file yet) so it persists.
    photoMeta: (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
      ? { name: photoBgImg._fileName, fit: photoFit, opacity: photoOpacityVal_, blur: photoBlur_, offset: { x: photoOffsetX, y: photoOffsetY }, zoom: photoZoom }
      : (typeof pendingPhotoMeta !== 'undefined' ? pendingPhotoMeta : null),
    musicMeta: (audioEl && audioEl._fileName)
      ? { name: audioEl._fileName, trimStart: trimStart, trimEnd: trimEnd, crossfadeMs: loopCrossfadeMs }
      : (typeof pendingMusicMeta !== 'undefined' ? pendingMusicMeta : null)
  };
}

function showAutosaveStatus(state) {
  const el = document.getElementById('autosaveStatus');
  const txt = document.getElementById('autosaveStatusText');
  if (!el || !txt) return;
  clearTimeout(el._hideTimer);
  el.hidden = false;
  el.classList.remove('saving', 'failed');
  if (state === 'saving') { el.classList.add('saving'); txt.textContent = 'Saving…'; }
  else if (state === 'failed') { el.classList.add('failed'); txt.textContent = 'Autosave failed'; }
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
  // Nothing meaningful on the canvas → clear any stale save instead of writing.
  if (!hasContent && strokes.length === 0) {
    try { localStorage.removeItem(AUTOSAVE_KEY); } catch (e) {}
    return;
  }
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeAutosave()));
    showAutosaveStatus('saved');
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

  const renderStrokes = () => paintStrokesStatic(strokes);
  const { width: cw, height: ch } = getCanvasLogicalSize();
  if (data.baseSnapshot) {
    preRecordSnapshot = strokes.length ? data.baseSnapshot : null;
    const baseImg = new Image();
    baseImg.onload = () => { ctx.drawImage(baseImg, 0, 0, cw, ch); renderStrokes(); };
    baseImg.src = data.baseSnapshot;
    hasContent = true;
  } else if (strokes.length) {
    renderStrokes();
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
  showToast(hadMedia ? 'Drawing restored — re-add your media below' : 'Drawing restored', null);
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
    } else {
      mCard.hidden = true;
      musicUploadBtn.hidden = false;
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
    } else {
      pCard.hidden = true;
      photoUploadBtn.hidden = false;
    }
  }
}

function serializeSkribl() {
  // Snapshot whatever is currently on the canvas as the base layer.
  // This captures drawing done before recording, and drawing that was
  // never recorded at all — the strokes array only holds recorded strokes.
  let baseSnapshot = null;
  try {
    if (hasContent && strokes.length === 0) {
      // Un-recorded drawing: the canvas pixels are the only record of it
      baseSnapshot = canvas.toDataURL();
    } else if (preRecordSnapshot) {
      // Recorded on top of earlier drawing: keep that earlier layer
      baseSnapshot = preRecordSnapshot;
    }
  } catch (e) {
    baseSnapshot = null;
  }

  return {
    version: 1,
    draftId: 'draft_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
    userId: null,               // server stamps this later
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    title: 'Untitled Skribl',
    baseSnapshot: baseSnapshot,
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    background: { color: bgColor },
    canvasSize: (() => {
      // The authored logical size (backing store in CSS px), NOT the fitted
      // display rect — otherwise a post made while rotated would record the
      // shrunken display size and the player would misplace the strokes.
      const lg = getCanvasLogicalSize();
      return { cssWidth: Math.round(lg.width), cssHeight: Math.round(lg.height), dpr: window.devicePixelRatio || 1 };
    })(),
    photo: photoBgImg && photoBgImg._draftData && photoBgImg.style.display !== 'none'
      ? { data: photoBgImg._draftData, name: photoBgImg._fileName || null, fit: photoFit, opacity: photoOpacityVal_, blur: photoBlur_, offset: { x: photoOffsetX, y: photoOffsetY }, zoom: photoZoom }
      : null,
    music: audioEl && audioEl._objectUrl
      ? { data: audioEl._draftData || null, name: audioEl._fileName || null, trimStart: trimStart, trimEnd: trimEnd, crossfadeMs: loopCrossfadeMs }
      : null
  };
}

// ---- Loop-crop for posting -------------------------------------------------
// Encode a slice of a decoded AudioBuffer to a 16-bit PCM WAV data URL. Reads
// straight from the buffer's channel data with a frame offset, so no temporary
// AudioBuffer / AudioContext is needed. Synchronous and dependency-free.
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
        const t = i / xfadeFrames;                 // 0 → 1
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

// Encode raw Float32 channel arrays (all same length) to a 16-bit PCM WAV data
// URL. Mirrors audioBufferToWavDataURL's writer but reads from provided arrays,
// so the crossfade path can encode samples that don't exist in the source
// buffer. Kept separate so the untouched no-crossfade path stays byte-for-byte.
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

// Slice currentAudioBuffer to the [trimStart, trimEnd] loop and return a small
// WAV data URL + its duration, or null if the decoded buffer isn't usable. When
// a crossfade is set, the tail is folded over the head so the clip loops
// seamlessly (the clip is then shorter by the crossfade length).
function buildTrimmedLoopWav() {
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
    return { dataUrl: encodeWavFromChannels(built.channels, sr), duration: built.frames / sr };
  }
  return { dataUrl: audioBufferToWavDataURL(currentAudioBuffer, startFrame, frames), duration: frames / sr };
}

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
function buildLoopAudioBuffer() {
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
  if (!data || data.version == null) { showToast('That file isn\'t a valid draft', menuBtn); return; }
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
  const videoDesc = document.getElementById('exportVideoDesc');
  let closeTimer = null;

  function openExport() {
    // Update the video option description based on what's available
    if (!strokes.length) {
      videoDesc.textContent = 'Record a drawing first to export video';
      videoBtn.disabled = true;
    } else {
      videoDesc.textContent = audioEl ? 'Replay of your drawing with music' : 'Replay of your drawing';
      videoBtn.disabled = false;
    }
    pngBtn.disabled = !hasContent;
    progress.hidden = true;
    clearTimeout(closeTimer);
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add('open'));
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
      hasAudio: !!(payload.music && payload.music.data),
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
      if (localOnly) {
        // Saved to this device only (no server, or a temporary server/network
        // failure). Be honest — this is NOT a shared post.
        statusLabel.textContent = 'Saved on this device only';
        showToast('Saved locally only — link works on this device', null);
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
        showToast(res.status === 404 ? 'Skribl not found' : 'Could not load that Skribl', null);
        return;
      }
      // Server envelope: { id, title, caption, hasAudio, createdAt, author, skribl }
      post = await res.json();
    } catch (e) { showToast('Could not load that Skribl', null); return; }
  } else if (hashMatch) {
    const id = decodeURIComponent(hashMatch[1]);
    try {
      const raw = localStorage.getItem('skribl_post_' + id);
      if (!raw) { showToast('Skribl not found on this device', null); return; }
      post = JSON.parse(raw);
    } catch (e) { showToast('Could not load that Skribl', null); return; }
  } else {
    return;   // editor mode — leave the app untouched
  }

  // Accept the wrapper { ..., skribl } or a bare serializeSkribl() object.
  const data = post && post.skribl ? post.skribl : post;
  if (!data || data.version == null) { showToast('That Skribl looks invalid', null); return; }

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
  function playerFitScale() {
    // Clamp the viewport budget so a short viewport (or an on-screen keyboard)
    // can't drive the available height ≤ 0 and flip the scale negative.
    const availW = Math.max(120, window.innerWidth - 40);
    const availH = Math.max(120, window.innerHeight - 220);
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

  // Restore all state and paint the finished drawing as the poster frame.
  loadSkribl(data);

  // ---- Player-owned playback orchestrator ----
  // Reuses the shared timeline + replayTimelineToCanvas core (NO second replay
  // loop) but drives it with its own clock, so we get true pause/resume, a
  // progress bar, and looping. Compositing reuses clearAndRestore (baseSnapshot);
  // the photo shows through from the DOM layer loadSkribl already positioned.
  const timeline = buildPlaybackTimeline();
  const totalMs = timeline.length ? timeline[timeline.length - 1].playT : 0;

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
    if (running || !timeline.length) return;
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
      showToast('Couldn\u2019t copy — long-press the address bar instead', null);
    }
  });

  setPlayIcon();
  setProgress(0);
})();
