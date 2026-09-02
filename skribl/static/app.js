// CSRF: echo the token the server issued. Empty when the deployment is
// unauthenticated, in which case no header is sent and nothing changes.
function skriblPostHeaders(){
  const h = {'Content-Type':'application/json'};
  if (window.SKRIBL_CSRF_TOKEN) { h['X-Skribl-CSRF'] = window.SKRIBL_CSRF_TOKEN; }
  return h;
}
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

// A small badge that follows the pointer while the Shape tool is active, so the
// kind you are about to draw is visible at the point you are drawing it. The
// shape picker lives on the toolbar button, and once you have drawn a few and
// looked away there is otherwise nothing on screen saying whether the next drag
// makes a line, a rectangle or an oval.
const shapeCursor = document.createElement('div');
shapeCursor.id = 'shapeCursor';
shapeCursor.style.cssText = `
  position: absolute;
  pointer-events: none;
  display: none;
  transform: translate(14px, 14px);
  z-index: 11;
  opacity: .85;
`;
canvasWrap.appendChild(shapeCursor);

const _SHAPE_GLYPH = {
  line:    '<line x1="3" y1="15" x2="15" y2="3"/>',
  rect:    '<rect x="3" y="4.5" width="12" height="9" rx="1.5"/>',
  ellipse: '<ellipse cx="9" cy="9" rx="6.5" ry="5"/>',
  // A pentagon: enough sides to read as "polygon" at 18px, few enough that the
  // corners survive. The glyph is deliberately not redrawn per `sides` -- a
  // cursor that changes shape as a slider moves is noise under the hand.
  poly:    '<path d="M9 3l6 4.4-2.3 7H5.3L3 7.4z"/>'
};
function updateShapeCursor(x, y) {
  const kind = (typeof shapeKind !== 'undefined') ? shapeKind : 'line';
  shapeCursor.innerHTML =
    '<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#fff" ' +
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ' +
    'style="filter:drop-shadow(0 1px 2px rgba(0,0,0,.8))">' +
    (_SHAPE_GLYPH[kind] || _SHAPE_GLYPH.line) + '</svg>';
  shapeCursor.style.left = x + 'px';
  shapeCursor.style.top = y + 'px';
}

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
  const areaEl = canvasArea || canvasWrap.parentElement || canvasWrap;
  const area = areaEl.getBoundingClientRect();
  // Subtract the padding. getBoundingClientRect() reports the BORDER box, so
  // the breathing room .canvas-area reserves was being handed straight back to
  // the canvas and the drawing still touched the column edge.
  const cs = getComputedStyle(areaEl);
  const padX = parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0);
  const padY = parseFloat(cs.paddingTop || 0) + parseFloat(cs.paddingBottom || 0);
  const availW = Math.max(1, area.width - padX);
  const availH = Math.max(1, area.height - padY);
  // Capped at 1: canvas.width is authoredW x dpr, so any scale above 1
  // stretches a fixed bitmap and softens every line. Flip allowed up to 1.4
  // and was visibly softer than Pad for the same drawing.
  const scale = Math.min(1, availW / authoredW, availH / authoredH);
  const dispW = Math.round(authoredW * scale);
  const dispH = Math.round(authoredH * scale);
  canvasWrap.style.width = dispW + 'px';
  canvasWrap.style.height = dispH + 'px';
  canvas.style.width = dispW + 'px';
  canvas.style.height = dispH + 'px';
  canvas.style.minHeight = '0';
  canvasWrap.style.backgroundColor = bgColor;
  if (window._skriblSyncPadGrid) window._skriblSyncPadGrid();  // no-op in player
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
    // A PRESET, not the viewport. This took whatever getBoundingClientRect()
    // returned on first load, so a drawing's shape depended on how wide the
    // browser window happened to be — different on phone and desktop, different
    // between two people drawing the same thing, and never anything the user
    // chose. A restored draft still re-establishes from its own canvasSize
    // (loadSkribl), so nothing already drawn changes shape.
    //
    // WHICH preset, though, follows the device: bestFor() picks the one that
    // displays largest in the band between header and toolbar, so a portrait
    // phone starts 9:16 instead of a 4:3 letterbox floating in dead space.
    // Still a preset — two people on the same kind of screen get the same
    // shape — and the Canvas picker can change it while the canvas is empty.
    const t = window.SkriblCanvasSizes || null;
    let d = t ? t.DEFAULT : null;
    if (t && t.bestFor) {
      const areaEl = canvasArea || canvasWrap.parentElement || canvasWrap;
      const r = areaEl.getBoundingClientRect();
      const cs = getComputedStyle(areaEl);
      const availW = r.width - (parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0));
      const availH = r.height - (parseFloat(cs.paddingTop || 0) + parseFloat(cs.paddingBottom || 0));
      // A degenerate band (display:none boot states, tests without CSS) keeps
      // the classic default rather than trusting a 0x0 measurement.
      if (availW > 50 && availH > 50) d = t.bestFor(availW, availH);
    }
    if (d) establishEditorCanvas(d.w, d.h);
    else {
      const area = (canvasArea || canvasWrap.parentElement || canvasWrap).getBoundingClientRect();
      establishEditorCanvas(area.width || 320, area.height || 320);
    }
    if (typeof window.syncCanvasSeg === 'function') window.syncCanvasSeg();
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
  // A TAKE IN PROGRESS MUST NOT REVEAL THE FINISHED-TAKE CONTROLS.
  // `recorded` is derived from stroke count alone, so undoing during a
  // recording (with any stroke still on the canvas) made this reveal Play,
  // Post and the duration badge — the three things startRecording() had just
  // deliberately hidden. The header then overflowed, and #recIndicator wrapped
  // its "1:04 · 0:19 play" text from one line to three, which is the record
  // pill visibly ballooning mid-take. Undoing all the way to an empty canvas
  // "fixed" it only because `recorded` went false and the same line re-hid them.
  // `recorded` still tracks state; only the DOM reveal is gated.
  const showTakeControls = recorded && !recording;
  playWrap.hidden = !showTakeControls;
  // Post keeps its header slot from first paint — disabled until there is a
  // take, hidden only DURING one (the recording header is a different mode,
  // and on a phone the rec pill + Stop need the room). A primary action that
  // pops in and out makes the header feel unstable; a dimmed one says "this
  // is where posting will happen" from the start.
  postBtn.hidden = recording;
  postBtn.disabled = !showTakeControls;
  if (recorded) {
    updateDrawingTimeLabels();
    durationBadge.hidden = !showTakeControls;
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

// Editor-only elements: authoring controls and the tab panels' contents. They
// exist only in the EDITOR template, and app.js touches them from dozens of
// places, so an absent one falls back to a DETACHED element of the same kind
// that absorbs writes and listeners harmlessly. Cheaper and more durable than
// guarding every site. See START-HERE.
function _authoringCtl(id, tag) {
  return document.getElementById(id) || document.createElement(tag || 'button');
}
const undoBtn = _authoringCtl('undoBtn');
const redoBtn = _authoringCtl('redoBtn');
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

/* eventPoint / pinch helpers live in lib/eventpoint.js — ONE implementation
 * shared by Pad, Flip and the player. It was briefly written out in both
 * app.js and flip.js; verify_surfaces.py counts function names defined in both
 * files and correctly refused the duplicate. See that file for the rule and
 * the defect it closes. */

function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  // See SkriblEventPoint.at() above for why this is not `e.touches[0]`. The stroke path
  // is where it matters most: every point of a mark landed where a resting
  // thumb was rather than where the drawing finger went. That was masked until
  // the pinch guard stopped reading the same screen-wide list — measured, the
  // stroke drew at x=56 (the thumb) instead of x=201 (the finger).
  const src = SkriblEventPoint.at(e);
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
  // Paint the reflections alongside, so the mirror is visible WHILE drawing
  // rather than appearing on release. No points are generated here — the commit
  // does that from the finished stroke, one group per reflection.
  if (window.SkriblMirror && SkriblMirror.active() && !_mirrorPainting) {
    _mirrorPainting = true;
    try {
      const _sz = getCanvasLogicalSize();
      const _a = SkriblMirror.reflect({ x: x1, y: y1 }, _sz.width, _sz.height);
      const _b = SkriblMirror.reflect({ x: x2, y: y2 }, _sz.width, _sz.height);
      for (let _i = 0; _i < _a.length; _i++) {
        drawLine(_a[_i].x, _a[_i].y, _b[_i].x, _b[_i].y, c, s, erase);
      }
    } finally { _mirrorPainting = false; }
  }
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
  // The player draws a Flip document's frames through here. Flip's editor has
  // capped how much one frame may spend on layering since the playback stall;
  // this path never did, so a frame full of see-through strokes played fine
  // while authoring and stalled for the viewer. Same ceiling, same module.
  const _sl = (typeof window !== 'undefined') ? window.SkriblStrokeLayers : null;
  const _over = !!(_sl && _sl.overBudget && _sl.overBudget(strokeArr, parseStrokeAlpha));
  if (strokeLayersOn() && !_over) {
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
/* ---- stylus pressure ------------------------------------------------------
   Pressure scales the existing per-point `size` rather than adding a field, so
   the player, the replay path, every exporter and every already-released
   client honour it without changing, and an old payload stays a valid new one.

   PAD IS NOT FLIP. Flip binds Pointer Events and reads `e.pressure`. Pad binds
   `mousedown`/`touchstart` (see the bindings below), where PointerEvent fields
   do not exist — an `e.pointerType === 'pen'` check here is dead code that
   silently never fires, which is exactly what the first draft of this was.
   Migrating Pad to Pointer Events would touch the pinch handler, the
   capture-phase space-drag and the mouse/touch split throughout, so the narrow
   correct reader is `Touch.force`.

   Gated on `touchType === 'stylus'` (iOS/iPadOS, i.e. Apple Pencil). Force is
   also reported for FINGERS on force-capable screens, so an ungated read would
   make ordinary touch drawing vary in width — a change to how every existing
   user's lines look. Android touch events expose no touchType, so a stylus
   there draws at constant width: narrower than ideal, and correct rather than
   guessing.

   PRESSURE_MIN keeps the lightest touch visible instead of vanishing. Erasing
   is exempt — a variable-width eraser leaves streaks you cannot see. */
const PRESSURE_MIN = 0.35;
// Eraser width: the pen size times a shared multiplier (lib/erasersize.js).
// This 3 used to be written out seven times across the two editors, including
// in the two eraser-CURSOR sites, where a drifted copy would leave the ring
// lying about how much it erases. Fall back to the shipped 3 so a surface that
// somehow loads without the lib erases exactly as it always did.
// Distance from the previously captured point, which is what the pencil and
// airbrush tapers read as speed. Pixels per POINT, not per millisecond: see the
// note in lib/brushes.js about 60Hz and 120Hz devices drawing the same gesture
// differently if a clock were used.
let _brushLastPt = null;
function _brushWidth(base, pos, erase) {
  if (erase || !window.SkriblBrush || SkriblBrush.name() === 'pen') return base;
  const d = (_brushLastPt && pos)
    ? Math.hypot(pos.x - _brushLastPt.x, pos.y - _brushLastPt.y) : 0;
  return SkriblBrush.shape(base, d);
}

function _eraserSize(size, erase) {
  return (typeof SkriblEraser !== 'undefined' && SkriblEraser)
    ? SkriblEraser.sizeFor(size, erase)
    : (erase ? size * 3 : size);
}

function pressureSize(e, base, erase) {
  if (erase || !e) return base;
  let raw = 0;
  if (e.pointerType === 'pen' && typeof e.pressure === 'number') {
    raw = e.pressure;                       // Pointer Events, if ever adopted here
  } else if (e.targetTouches || e.touches) {
    // targetTouches first, for the reason given at the pinch guard in
    // editor_draw.js: `touches` counts contacts that never touched the canvas,
    // so a palm resting on an iPad made `length === 1` false and quietly
    // dropped Apple Pencil pressure back to constant width. The length check
    // stays — with two fingers ON the canvas this is a pinch, not a stroke.
    const list = (e.targetTouches && e.targetTouches.length) ? e.targetTouches : e.touches;
    if (list && list.length === 1) {
      const t = list[0];
      if (t && t.touchType === 'stylus' && typeof t.force === 'number') raw = t.force;
    }
  }
  // A stylus commonly reports 0 on the first event of a stroke. Treat that as
  // "no reading yet" rather than as a feather touch, or every line would start
  // at minimum width.
  // Curve, floor and on/off live in lib/pressure.js (shared with Flip). Reading
  // `raw` stays here: Pad is on touch events and Flip on Pointer Events, so the
  // extraction cannot be shared even though the response can. Fall back to the
  // shipped curve if the lib is absent.
  return (typeof SkriblPressure !== 'undefined' && SkriblPressure)
    ? SkriblPressure.sizeFrom(base, raw)
    : (raw > 0 ? base * (PRESSURE_MIN + (1 - PRESSURE_MIN) * Math.min(1, raw)) : base);
}
// Exposed for the harness: the stylus path cannot be synthesised in Chromium
// (touchType is an iOS extension with no constructor support), so the mapping
// is asserted directly. This is a measurement seam, not an API.
window.__skriblPressureSize = pressureSize;

/* Bind an event without letting a missing element abort the rest of the file.
 * A null from getElementById throws at the top level and every binding written
 * after it never happens — see the same helper in flip.js. */
function bindEl(id, ev, fn, opts) {
  const el = document.getElementById(id);
  if (!el) { console.warn('[skribl] missing element for binding:', id, ev); return null; }
  el.addEventListener(ev, fn, opts);
  return el;
}


const toolGroupEl = document.getElementById('toolGroup');
/* ---------- v226: the tool shelf and its overflow tray --------------------
   The mechanics live in lib/toolshelf.js and are shared with Flip — see that
   file's header for why the row needed this at all. What stays here is what is
   genuinely Pad's: which tools exist, and what applying one does to the canvas.

   WITH THREE TOOLS NOTHING CHANGES. 3 <= SHELF_MAX, so all three keep their
   cells, the chevron stays hidden and the tray is never built. */
const SHELF_MAX = 3;
const toolMoreBtn = document.getElementById('toolMoreBtn');
const toolTray = document.getElementById('toolTray');
const toolShelf = (typeof window !== 'undefined' && window.SkriblToolShelf && toolGroupEl)
  ? window.SkriblToolShelf.create({
      group: toolGroupEl,
      moreBtn: toolMoreBtn,
      tray: toolTray,
      shelfMax: SHELF_MAX,
      // #selectToolBtn is DELIBERATELY absent: v219 removed Select from Pad,
      // because it edited points that were already recorded and replay then
      // drew a stroke at its NEW position at its OLD timestamp. It is therefore
      // not in this list either — the registry describes what the row HAS.
      tools: [
        { id: 'pen',    label: 'Pen',    btn: 'penToolBtn' },
        { id: 'eraser', label: 'Eraser', btn: 'eraserToolBtn' },
        { id: 'shape',  label: 'Shape',  btn: 'shapeToolBtn' },
      ],
      currentTool: () => tool,
      slider: toolSlider,
      setTool: (id) => setTool(id),
      closeTray: () => { if (_padDrawerCtl) _padDrawerCtl.open(null); },
    })
  : null;
if (typeof window !== 'undefined') window.SkriblPadTools = toolShelf;

function setTool(nextTool) {
  tool = nextTool;
  const penBtn = document.getElementById('penToolBtn');
  // 'select' is still accepted by name: SkriblSelectTool is loaded on Pad and
  // other code may still ask for the tool. It has no registry entry and no
  // button, so btnFor() returns null and the pen takes the highlight — a no-op
  // rather than a crash, exactly as the old ternary's `selectBtn || penBtn`
  // fallback did. If Select ever returns, add it to the registry above and this
  // works unchanged.
  const activeBtn = (toolShelf && toolShelf.btnFor(nextTool)) || penBtn;
  // Leaving the tool drops the selection: an invisible selection that a later
  // drag would move is worse than making the user re-pick.
  if (nextTool !== 'select' && window.SkriblSelectTool) window.SkriblSelectTool.clear();
  // Records the MRU, re-syncs the shelf and repaints the tray's pressed state.
  if (toolShelf) toolShelf.noteUse(nextTool);
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
  if (nextTool !== 'shape' && typeof shapeCursor !== 'undefined') shapeCursor.style.display = 'none';
  if (toolShelf) toolShelf.placeSlider(activeBtn);
}

function initToolSlider() {
  setTool(tool || 'pen');
}
setTimeout(initToolSlider, 50);
// A single timed call is not enough: on a phone the bar is often laid out after
// that 50ms, and the pill then sits at a position measured against zero widths.
// Re-place it whenever the group actually changes size, and on orientation
// change. Same failure lib/segslider.js was written for, different element.
(function keepToolSliderPlaced() {
  if (!toolGroupEl) return;
  const replace = () => setTool(tool || 'pen');
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(replace).observe(toolGroupEl);
  window.addEventListener('resize', replace);
  window.addEventListener('orientationchange', replace);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(replace);
})();

document.querySelectorAll('.tool-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    // The chevron is a .tool-btn so it inherits the pill's shape and the sliding
    // highlight's geometry, but it is NOT a tool: it carries no data-tool.
    // Without this guard clicking it called setTool(undefined), and Pad assigns
    // `tool` unconditionally — so opening the tray left the editor with no tool
    // selected. Flip clamped unknown ids to the pen and merely looked fine.
    if (!btn.dataset.tool) return;
    // See the twin of this guard in flip.js: lib/toolshelf.js binds the cells it
    // builds, and a button carrying both bindings has its second handler undo
    // the first. Harmless on Pad today -- both routes here merely derive -- and
    // kept identical so the two surfaces cannot drift into one having the bug.
    if (btn.dataset.shelfBound) return;
    setTool(btn.dataset.tool);
    // Shape opens its picker; every other tool closes it. Tapping Shape while
    // it is already the active tool re-opens the picker to switch kind — which
    // is the whole point of moving it out of the drawer.
    const pop = document.getElementById('shapePop');
    if (pop) pop.hidden = (btn.dataset.tool !== 'shape') ? true : !pop.hidden;
  });
});

// The preset dots are built here rather than written into the template, from
// the same lib/palette.js Flip builds its own from — one list, not two kept in
// step by hand. The click handler below is delegated on the group, so a dot
// created at runtime needs no listener of its own.
(function(){
  const g = document.getElementById('colorGroup');
  if (g && window.SkriblPalette) window.SkriblPalette.mount(g, { selectFirst: true });
})();

bindEl('colorGroup', 'click', (e) => {
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

bindEl('bgGroup', 'click', (e) => {
  const btn = e.target.closest('.bg-swatch');
  if (!btn || btn.id === 'customBgBtn') return;
  bgColor = btn.dataset.bg;
  document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b === btn));
  canvasWrap.style.backgroundColor = bgColor;
  updateVignette();
});

const customBgBtn = document.getElementById('customBgBtn');
const customBgInput = _authoringCtl('customBgInput', 'input');

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
const customColorInput = _authoringCtl('customColorInput', 'input');

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
  // Brush presets shape opacity here rather than at each call site, so every
  // path that already asks for "the pen colour" — strokes, shapes, mirrors,
  // the settle points — picks the brush up for free. lib/brushes.js returns
  // the same two shapes this function always has ('#rrggbb' or 'rgba(...)'),
  // which is what parseStrokeAlpha and the nib tint parse.
  if (window.SkriblBrush && SkriblBrush.name() !== 'pen') {
    return SkriblBrush.colorFor(hex, strokeOpacity);
  }
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
  // Validation, casing and swatch state are shared with Flip via
  // lib/colorselect.js. What Pad does with the result — the custom swatch, the
  // colour input, feeding recents — stays here: Flip is built differently.
  const sel = window.SkriblColorSelect
    && window.SkriblColorSelect.apply(document.getElementById('colorGroup'), hex);
  if (!sel) return;
  hex = sel.hex;
  const matched = sel.matched;
  color = hex;
  setTool('pen');
  if (!matched) {
    customColorBtn.style.background = hex;
    if (customColorInput) customColorInput.value = hex;
    customColorBtn.classList.add('active');
    addRecent(hex);
  }
  updateCurrentColorChip();
}

// Shared with Flip via lib/recentcolors.js. Only onPick differs: Pad's drawer
// stays open after a pick, Flip's popover closes because it covers the canvas.
// `recentColors` is kept in step through onChange because other call sites in
// this file read it directly.
let _recent = null;
function _initRecent() {
  if (_recent || !window.SkriblRecentColors) return;
  _recent = window.SkriblRecentColors.create({
    wrap: document.getElementById('recentColors'),
    row: document.getElementById('recentRow'),
    onPick: hex => setPenColor(hex),
    onChange: list => { recentColors = list; },
  });
}
function addRecent(hex) { _initRecent(); if (_recent) _recent.add(hex); }
function renderRecent() { _initRecent(); if (_recent) _recent.render(); }

/* The artwork stage lives in lib/artwork.js — ONE implementation shared with
 * Flip. See that file for the rule and for what each surface was getting wrong.
 * Pad deliberately does NOT wrap it in a local paintArtwork(): flip.js already
 * defines that name, and verify_surfaces.py ratchets how many functions the two
 * files define in common. It caught exactly that on a release run. */
const artCv = document.createElement('canvas');

function padArtwork() {
  const dpr = window.devicePixelRatio || 1;
  const showing = photoBgImg && photoBgImg.src && photoBgImg.complete
    && photoBgImg.naturalWidth && photoBgImg.style.display !== 'none';
  return window.SkriblArtwork.stage({
    canvas: artCv, w: canvas.width / dpr, h: canvas.height / dpr, dpr: dpr,
    bg: bgColor,
    photo: showing ? { img: photoBgImg, fit: photoFit, offX: photoOffsetX,
                       offY: photoOffsetY, zoom: photoZoom,
                       opacity: photoOpacityVal_, blur: photoBlur_ } : null,
    // Pad's canvas holds artwork only: the nib is a DOM element, and the wet
    // layer is a stroke in progress, which IS artwork.
    strokes: canvas
  });
}

function sampleColorAt(x, y) {
  try {
    const dpr = window.devicePixelRatio || 1;
    const art = padArtwork();
    const d = art.getContext('2d').getImageData(Math.round(x * dpr), Math.round(y * dpr), 1, 1).data;
    // The stage is opaque, so this fallback should never fire now. Kept because
    // a zero-sized canvas before first layout would otherwise return black.
    let hex = d[3] < 10 ? bgColor
      : '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
    setPenColor(hex);
  } catch (err) {}
  stopPicking();
}

let _eyedropper = null;
function stopPicking() {
  if (_eyedropper) _eyedropper.disarm();
  pickingColor = false;
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

  // Shared with Flip via lib/smoothing.js — the level-to-alpha mapping was
  // three magic numbers written out twice. Pill positioning stays here because
  // Pad and Flip do it differently; see the note in that file.
  const smoothSeg = document.getElementById('smoothSeg');
  if (smoothSeg && window.SkriblSmoothing) {
    window.SkriblSmoothing.create({
      seg: smoothSeg,
      onChange: a => { smoothingAlpha = a; },
    });
    attachSegSlider(smoothSeg);
  }

  // Eraser width — the shared multiplier (lib/erasersize.js). Repainting the
  // cursor on change matters: the ring is what the user aims with, so a size
  // that only took effect on the next stroke would be a cursor that lies.
  const eraserSeg = document.getElementById('eraserSeg');
  if (eraserSeg && window.SkriblEraser) {
    window.SkriblEraser.create({
      seg: eraserSeg,
      onChange: () => { if (typeof updateEraserCursor === 'function') updateEraserCursor(); },
    });
    attachSegSlider(eraserSeg);
  }

  const brushSeg = document.getElementById('brushSeg');
  if (brushSeg && window.SkriblBrush) {
    window.SkriblBrush.create({ seg: brushSeg });
    attachSegSlider(brushSeg);
  }

  const pressureSeg = document.getElementById('pressureSeg');
  if (pressureSeg && window.SkriblPressure) {
    window.SkriblPressure.create({ seg: pressureSeg });
    attachSegSlider(pressureSeg);
  }

  // Shared with Flip via lib/eyedropper.js. The native window.EyeDropper
  // branch that used to live here is GONE: it existed only on Chromium, so the
  // tap-to-sample path had to exist anyway, and keeping both shipped two
  // different experiences behind one button. See the note in that file.
  const eyedropperBtn = document.getElementById('eyedropperBtn');
  if (eyedropperBtn && window.SkriblEyedropper) {
    _eyedropper = window.SkriblEyedropper.create({
      button: eyedropperBtn,
      surface: canvas,
      idleCursor: '',
      onArm: () => showToast('Touch the canvas — drag to aim, release to pick', eyedropperBtn),
      // pickingColor is read by the pointer handler and by two teardown paths.
      onChange: v => { pickingColor = v; },
      // Loupe wiring: the lib magnifies and reads the SAME composited stage
      // sampleColorAt reads, so the ring shows what release will pick.
      getPoint: ev => getPos(ev),
      artwork: () => padArtwork(),
      dpr: () => window.devicePixelRatio || 1,
      bg: () => bgColor,
      // stopPicking, not just the lib's disarm: it also restores the
      // lock/eraser/normal cursor cue, same as the tap path.
      onPick: hex => { setPenColor(hex); stopPicking(); },
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

// Toolbar drawers: the exclusive-open machine lives in lib/drawers.js
// (shared with Flip); only Pad's hooks and its scroll behaviour are here.
// Per-name hooks below reproduce the old openDrawer() exactly: leaving any
// non-photo state exits reposition and cancels an eyedropper pick; opening
// photo refreshes reposition UI; opening music refreshes the time labels.
// The `typeof skriblDrawers` guard is load-bearing: the PLAYER runs app.js
// without lib/drawers.js (editor furniture), so the reference must not throw.
const _padDrawerCtl = (typeof skriblDrawers === 'function') ? skriblDrawers({
  panels: {
    draw:  { panel: 'drawPanel',  button: 'colorOpenBtn',  openClass: 'open' },
    photo: { panel: 'photoPanel', button: 'imageOpenBtn', openClass: 'open' },
    music: { panel: 'musicPanel', button: 'musicOpenBtn', openClass: 'open' },
    // The tray joins the drawer set so it is mutually exclusive with draw,
    // photo and music — opening it closes them, and vice versa. Rebuilt on
    // every open; see lib/toolshelf.js.
    tools: { panel: 'toolTray', button: 'toolMoreBtn', openClass: 'open', aria: true }
  },
  reveal(panel, name) {
    // The tray is anchored ABOVE the toolbar rather than docked below it, so
    // none of the scroll-to-reveal work below applies: it is already fully on
    // screen, and scrolling for it would drag the canvas out of frame.
    if (name === 'tools') { if (toolShelf) { toolShelf.buildTray(); toolShelf.sync(); } return; }
    if (name !== 'photo' && typeof exitReposition === 'function') exitReposition();
    if (typeof pickingColor !== 'undefined' && pickingColor) stopPicking();
    if (name === 'photo' && typeof updateRepositionUI === 'function') updateRepositionUI();
    if (name === 'music') {
      updateDrawingTimeLabels();
      // Nothing else re-calls drawWaveform — the decode chain is its only
      // caller — so opening the drawer is the one moment the strip can recover
      // a paint it missed while the panel had no layout. TWO frames: one for
      // the [hidden] removal to take effect, a second for the panel to be laid
      // out, so musicTrack reports its real width rather than 0.
      if (currentAudioBuffer) {
        requestAnimationFrame(() => requestAnimationFrame(() => drawWaveform(currentAudioBuffer)));
      }
    }
    // Drawer opens below the bar; scroll just enough to reveal it (keeps max
    // canvas in frame), and scroll back to rest when everything closes. Honor
    // the user's reduced-motion preference — the CSS sets scroll-behavior:auto
    // for them, but a JS-requested 'smooth' scroll would override that intent,
    // so mirror it here.
    const b = (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) ? 'auto' : 'smooth';
    if (panel) requestAnimationFrame(() => panel.scrollIntoView({ behavior: b, block: 'end' }));
    else window.scrollTo({ top: 0, behavior: b });
  }
}) : null;
function openDrawer(name) {                      // name = 'draw'|'photo'|'music' or null
  if (_padDrawerCtl) _padDrawerCtl.open(name);
}
const toolBarEl = document.getElementById('toolBar');
if (toolBarEl) toolBarEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.tool-open');
  if (btn && _padDrawerCtl) _padDrawerCtl.toggle(btn.dataset.drawer);
});                                              // pen/eraser use their own setTool binding
// The chevron is not a .tool-open, so it needs its own binding; the tray is
// dismissed by tapping away from it or by Escape, like every other overlay.
if (toolMoreBtn && _padDrawerCtl) {
  toolMoreBtn.addEventListener('click', (e) => { e.stopPropagation(); _padDrawerCtl.toggle('tools'); });
}
function hideToolTray() { if (_padDrawerCtl && _padDrawerCtl.isOpen('tools')) _padDrawerCtl.open(null); }
document.addEventListener('click', (e) => {
  if (!toolTray || toolTray.hidden) return;
  if (e.target.closest('#toolTray') || e.target.closest('#toolMoreBtn')) return;
  hideToolTray();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideToolTray(); });
// First paint: with three tools this only hides the chevron, which the template
// already ships hidden. It is here so the shelf is correct from the registry
// rather than from the markup happening to agree with it.
if (toolShelf) toolShelf.sync();

const recordBtn = _authoringCtl('recordBtn');
const playBtn = document.getElementById('playBtn');
const playWrap = document.getElementById('playWrap');
const postBtn = _authoringCtl('postBtn');
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

// ---- Pause handling ---------------------------------------------------
// The 50ms cap below was hardcoded at BOTH gap sites and never surfaced, so
// the single largest thing separating "how it was drawn" from "how it plays
// back" was a magic number no one could see or change: a drawing made with
// long thinking pauses replayed with those pauses silently squeezed out.
//
// IT TRAVELS IN THE PAYLOAD, deliberately. The PLAYER builds its timeline with
// this same function, so a device-local setting would mean the editor's Play
// and a viewer's shared link disagreed about the same Skribl. serializeSkribl()
// writes `pauseMode` and loadSkribl() adopts it, which makes the choice part of
// the work rather than part of the browser.
//
// `tight` is 50 — the shipped behaviour — so an unset or unknown value replays
// exactly as before.
const PAUSE_CAPS = { keep: Infinity, trim: 250, tight: 50 };
let pauseMode = 'tight';
function pauseCapMs() {
  return Object.prototype.hasOwnProperty.call(PAUSE_CAPS, pauseMode)
    ? PAUSE_CAPS[pauseMode] : PAUSE_CAPS.tight;
}
function setPauseMode(m) {
  if (!Object.prototype.hasOwnProperty.call(PAUSE_CAPS, m)) return pauseMode;
  pauseMode = m;
  return pauseMode;
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
    if (gap > 0) playT += Math.min(gap, pauseCapMs());
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
    if (gap > 0) total += Math.min(gap, pauseCapMs());
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
  // v208 (v207 review F4): close the Pad tune drawer before recording. The
  // recording CSS hides #tuneBtn; leaving #tuneShell open would strand an
  // expanded drawer with no visible opener. Editor-only hook (player has none).
  window._skriblClosePadTune?.();
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
  postBtn.hidden = true;          // the recording header is its own mode; Post returns on Stop
  durationBadge.hidden = true;

  recTimer.textContent = '0:00';
  clearInterval(recTimerInterval);   // defensive: never stack intervals
  recTimerInterval = setInterval(() => {
    const wall = formatDuration(Date.now() - startTime);
    // getPlaybackDuration() sums across ALL strokes, so on a continue-take the
    // "play" readout keeps counting up from the previous takes' total.
    const play = formatDuration(getPlaybackDuration());
    // Plain words, not a readout: "0:06 · plays 0:01" says the second number is
    // the replay's length after pause-tightening; "0:06 · 0:01 play" said
    // nothing a first-time user could parse.
    recTimer.textContent = wall + ' · plays ' + play;
  }, 200);
}

function endRecordingTake() {
  // Guarded, not assumed: commitActiveStroke lives in editor_draw.js, which
  // the player does not load. The player never reaches Stop, but a bare
  // call would be a ReferenceError waiting for the first path that does.
  if (window.SkriblCapture) window.SkriblCapture.commitActiveStroke();   // capture a stroke still in progress when Stop is hit
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
  postBtn.hidden = false;          // back in its slot either way; dimmed if the take was empty
  postBtn.disabled = !recorded;
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
  postBtn.hidden = false;          // stays in its slot, disabled until the next take
  postBtn.disabled = true;
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
// ---- Replay speed -----------------------------------------------------
// PREVIEW ONLY, and deliberately NOT in the payload — unlike pauseMode, which
// IS. The distinction is whether the setting describes the WORK or the act of
// reviewing it: pause handling changes what the drawing is, so a viewer must
// get the author's choice; speed is a way of looking at your own take, like
// zoom, and posting it would impose your review habits on everyone who opens
// the link. serializeSkribl() must never learn about this, and there is a pin
// on exactly that.
//
// The stored `t` values are never touched. Only the replay CLOCK is scaled, so
// a fast preview cannot rewrite the timing that is the artifact.
const REPLAY_RATES = [0.5, 1, 2];
let replayRate = 1;
try {
  const _rr = parseFloat(localStorage.getItem('skribl_replay_rate'));
  if (REPLAY_RATES.indexOf(_rr) !== -1) replayRate = _rr;
} catch (e) {}
function setReplayRate(r) {
  r = parseFloat(r);
  if (REPLAY_RATES.indexOf(r) === -1) return replayRate;
  replayRate = r;
  try { localStorage.setItem('skribl_replay_rate', String(r)); } catch (e) {}
  return replayRate;
}

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
  // Inset by the frame's corner radius at BOTH ends so the bar spans only the
  // flat part of the canvas bottom. Full width put its ends level with the
  // rounded corners, where the frame has already curved away. Read from the
  // token so it stays correct if --r-frame changes.
  const _r = parseFloat(getComputedStyle(document.documentElement)
                          .getPropertyValue('--r-frame')) || 14;
  const _inset = Math.min(_r, w.width / 4);   // never eat the whole bar
  playScrub.style.left = (w.left - a.left + _inset) + 'px';
  playScrub.style.width = Math.max(0, w.width - _inset * 2) + 'px';
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
  // Scaled CLOCK, not scaled data: elapsed wall time is converted into position
  // along the drawing's own timeline. The badge and the scrub bar therefore keep
  // reading in the drawing's time, which is what the author is judging.
  const elapsed = (performance.now() - playStart) * replayRate;
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
  unlockWebAudio();   // F3: inside the gesture — clearAndRestore below may not
                      // call back until an Image decode has resolved, long
                      // after iOS stops treating this as a user activation.
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
      // WALL-CLOCK duration, so a 2x preview stops the music when the
      // drawing ends rather than half a take later. The source's own
      // playbackRate is scaled to match in startWebAudioLoop().
      playMusicLooped(playTotal / replayRate, beginFrames);
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
    const x = SkriblEventPoint.at(e).clientX;
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
    // Divided by the rate for the same reason the multiply above exists:
    // lastTargetMs is in the drawing's time, playStart is wall time.
    playStart = performance.now() - lastTargetMs / replayRate;   // resume from the released position
  };
  playScrub.addEventListener('pointerup', endScrub);
  playScrub.addEventListener('pointercancel', endScrub);
  window.addEventListener('resize', () => { if (playing) positionScrub(); });
}

// The Post button opens the composer sheet — wired in initPostComposer() below.

// ---------- Overflow menu / help drawer ----------
// Moved to editor_menu.js, loaded only by the editor template. The cut stops
// short of initBrandFit() below, which the PLAYER executes — its inner fit()
// is why the header brand collapses correctly on a shared link.
(function initBrandFit() {
  const brand = document.querySelector('.brand');
  const brandText = brand && brand.querySelector(':scope > span');
  const actions = document.getElementById('actions');
  const header = document.querySelector('.header');
  if (!brand || !brandText || !actions || !header) return;
  // v210 (owner's iPhone): the test used to be scrollWidth > clientWidth. That
  // detects the cluster pushing PAST the header's edge — but on a phone the
  // header's controls are laid out on top of the wordmark, so nothing pushes
  // past anything: at 375 the tune glyph painted over the "d" of "Pad" and at
  // 320 both the glyph and the record dot sat INSIDE the wordmark, while
  // scrollWidth stayed equal to clientWidth and the collapse never fired.
  // Measure the actual thing: does the first control clear the wordmark's
  // right edge with a real gap? Overflow is still checked as a second test.
  // 8, not 12: measured at 375 with a take saved, the fully-collapsed cluster
  // clears the brand by 5px before the gap step and 8+ after it. A 12px floor
  // forced Post to drop its label at 375 for 4px of air; 8 keeps the word on
  // the phone that matters most and still shows daylight past the mark.
  const MIN_GAP = 8;   // px between the brand (mark or wordmark) and the first control
  function firstControlLeft() {
    let left = Infinity;
    for (const el of actions.querySelectorAll('button, a')) {
      if (el.hidden || el.closest('[hidden]')) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0) left = Math.min(left, r.left);
    }
    return left;
  }
  const collides = () => {
    const b = brand.getBoundingClientRect();
    const first = firstControlLeft();
    // What matters is the BRAND, not the cluster's own box: with
    // justify-content:flex-end an over-full cluster overflows leftward, and
    // that is fine right up until it reaches the brand's gap. (A first draft
    // also tested the cluster's box edge, and at 430 it shed Post's label for
    // an overflow of 3px into a margin the user cannot see.)
    return first < b.right + MIN_GAP
        || header.scrollWidth > header.clientWidth + 1;
  };
  function fit() {
    brand.classList.remove('brand-collapsed');           // reveal, then measure
    header.classList.remove('rec-collapsed');
    header.classList.remove('gap-collapsed');
    header.classList.remove('post-collapsed');
    header.classList.remove('tag-collapsed');
    // Pixel-snap the cluster. The wordmark's text width is fractional (the
    // brand's right edge measured 435.65625 at 1280) and justify-content:
    // flex-end hands that fraction straight to the cluster's x (715.609375),
    // where the buttons' rounded corners then anti-alias differently between
    // two renders of BYTE-IDENTICAL CSS — verify_cssplit's editor-pad scene
    // failed twice on a 4x34 strip at exactly this button's edge, 1-3 RGB per
    // pixel, corners only. Rounding the actions box to whole pixels removes
    // the sensitivity at its source instead of loosening a zero-tolerance
    // pixel test that is right to be zero-tolerance.
    // With flex:1 + flex-end the buttons are packed to the RIGHT edge, so
    // their x is (right edge - content width); a margin on the box shifts
    // nothing. What is fractional is the content width itself (252.390625:
    // the labelled Record/Post pills size to their text). So the snap goes on
    // the flex item's right side: a fractional padding-right that makes the
    // content start on a whole pixel. Cheap, invisible, idempotent.
    actions.style.paddingRight = '';
    const first = firstControlLeft();
    const frac = Number.isFinite(first) ? first % 1 : 0;
    if (frac) actions.style.paddingRight = (parseFloat(getComputedStyle(actions).paddingRight) || 0) + frac + 'px';
    // Shed in order of how little it costs, re-measuring after each, and stop
    // as soon as nothing collides. The mark is shed LAST, not first: the brand
    // is logo-only (there is no wordmark behind it), so collapsing it leaves
    // the header with nothing naming the surface, which costs more than any
    // button's word. Measured at 390 with a take saved: the mark is 21px
    // over-full on its own; Record is already icon-only there (the
    // `:has(#playWrap)` rule), the gap step frees 8, and Post's label frees
    // 47 — so dropping Post's word is what buys the mark its place (+34).
    //
    // Two passes, because "shed the mark last" alone would be worse than the
    // bug at narrow widths. At 360 the mark cannot fit even with every label
    // gone (+4 against an 8px floor), so a single ordered pass would spend
    // Post's word AND still lose the mark. Pass A tries to keep the mark; if
    // it still does not fit, pass B puts the labels back and drops the mark
    // instead, which is what 320/344/360 actually want.
    // Shed order follows which action is CURRENT. While Post is disabled
    // (nothing to post yet) its word is the cheapest thing on the bar — a
    // dimmed pill reads fine as an icon, and Record's word is the one a
    // first-time user needs. Once a take exists the order flips back:
    // Record is already icon-only by then (the `:has(#playWrap)` rule) and
    // Post's word is the primary action's name.
    // The MODE tag ('tag-collapsed') sheds right after the current action's
    // cheapest word: the sticker still says SKRIBL without it, and its ~55px
    // is worth more than any remaining label.
    const pb = document.getElementById('postBtn');
    const steps = (pb && pb.disabled)
      ? ['post-collapsed', 'tag-collapsed', 'rec-collapsed', 'gap-collapsed']
      : ['rec-collapsed', 'tag-collapsed', 'gap-collapsed', 'post-collapsed'];
    for (const s of steps) if (collides()) header.classList.add(s);
    if (collides()) {
      header.classList.remove('rec-collapsed');
      header.classList.remove('gap-collapsed');
      header.classList.remove('post-collapsed');
      brand.classList.add('brand-collapsed');
      for (const s of steps) if (collides()) header.classList.add(s);
    }
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
      attributeFilter: ['hidden', 'class', 'style', 'disabled'],
    });
  }
  requestAnimationFrame(fit);
})();

// Help search — shared via lib/helpsearch.js so the two editors cannot
// drift. Safe if the lib is absent: the accordions keep working.
if (window.SkriblHelpSearch) window.SkriblHelpSearch.init();

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
// The drawer WIRING moved to editor_music.js (editor-only). What remains here
// is state and the functions the player reaches through loadSkribl.
const musicInput = _authoringCtl('musicInput', 'input');
// Selection tokens (review round 9, #1). Adding `await` to these handlers created
// a race that did not exist when they were synchronous: a slow decode of file A
// could finish AFTER the user picked B and overwrite it. Each slot has a counter
// bumped on every selection AND every removal; a handler that returns from its
// await with a stale token drops its result silently — including its toast, since
// complaining about a file the user already replaced is noise.
let musicSelectionSeq = 0;
let photoSelectionSeq = 0;
const musicPanel = document.getElementById('musicPanel');
const musicRemove = _authoringCtl('musicRemove');
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

function clampTrim() {
  // Clamp half of the old updateTrimUI, split out so it runs on the PLAYER too.
  // It is the single choke point enforcing the loop cap on load: put it behind
  // a player-mode guard and a shared link can play a loop longer than either
  // editor allows. Returns false when there is nothing to clamp.
  // (This file ships uncompressed to every visitor — see START-HERE for the
  // full reasoning rather than carrying it here.)
  if (!Number.isFinite(audioDuration) || audioDuration <= 0) return false;
  // Guard against NaN/invalid trim values sneaking in from a drag/nudge edge
  // case — clamp both to a valid range so a bad value can't propagate.
  if (!Number.isFinite(trimStart)) trimStart = 0;
  if (!Number.isFinite(trimEnd)) trimEnd = Math.min(audioDuration, trimStart + Math.min(20, audioDuration));
  const minLoop = 0.01;
  trimStart = Math.max(0, Math.min(trimStart, Math.max(0, audioDuration - minLoop)));
  trimEnd = Math.max(trimStart + minLoop, Math.min(trimEnd, audioDuration));
  // Single choke point for the cap, matching Flip. Pad enforced the <=20s
  // limit in its drag and nudge paths only, so a loop that arrived any OTHER
  // way — a load, a draft restore, a re-add — kept whatever length it came
  // with. Measured before this line: a 60s loop through updateTrimUI stayed
  // 60s on Pad and became 20s on Flip.
  const _maxLoop = window.SkriblLoopTrim.MAX_LOOP_SECONDS;
  if (trimEnd - trimStart > _maxLoop) trimEnd = trimStart + _maxLoop;
  return true;
}

function updateTrimUI() {
  // Clamp always; paint only where there is a trim track to paint on. The null
  // check is what lets the player's template drop the editor shell safely.
  if (!clampTrim()) return;
  if (!handleStart || !musicRange || !musicTrack) return;
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

// Waveform canvases live in the music panel — editor only. A detached <canvas>
// gives a real 2d context, so drawWaveform() and every clearRect() downstream
// work unchanged and paint into nothing.
const waveformCanvas = _authoringCtl('waveformCanvas', 'canvas');
const waveformCtx = waveformCanvas.getContext('2d');
const zoomWaveformCanvas = _authoringCtl('zoomWaveformCanvas', 'canvas');
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
    b.classList.toggle('on', zoomFocus !== 'free' && b.dataset.focus === zoomFocus);
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



// Sliding-pill highlight for segmented button groups — the same affordance as
// the draw/eraser tool slider, generalized so it can be attached to any group.
// It injects an absolutely-positioned pill as the group's first child and slides
// it under whichever button carries `.active`. A group with NO active button
// (e.g. the Loop/Start/End focus row while free-panning) hides the pill. It
// repositions on active-state changes (MutationObserver) and when the group
// resizes or first becomes visible from a hidden tab/drawer (ResizeObserver);
// both are feature-detected so the headless harness — which stubs neither — runs
// this file top-level without throwing.

// Both editors carried an equivalent of this; it lives in lib/segslider.js now.
function attachSegSlider(group){ if(window.SkriblSegSlider) window.SkriblSegSlider.attach(group); }

// Focus + magnification control for the Loop Detail view. Built in JS (styles
// injected once) so the whole feature lives in this one file. Focus centers the
// zoom window on the loop / start edge / end edge; the multiplier tightens it.

// Fine-tune disclosure: the Music panel opens to essentials (waveform + trim +
// Match/Preview); the deep Loop Detail (zoom, focus/magnifier, nudgers) lives
// behind this toggle so all three tab panels share the same "essentials shown,
// depth one tap away" rhythm. Null-guarded — the player shell has no toggle.
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
  if (!audioBuffer || !musicTrack || !waveformCanvas) return;
  const rect = musicTrack.getBoundingClientRect();
  // THE THIRD "sized from a rect with no layout yet" BUG IN THIS DRAWER, and
  // the first one that left a canvas permanently blank rather than briefly
  // wrong. Sizing a canvas from a 0-wide rect is not a no-op: it sets
  // canvas.width = 0, which CLEARS the bitmap, and the loop below then paints
  // zero peaks. The decode chain calls this exactly once, so if the music
  // drawer happened to be shut at that instant — a draft reload, or picking a
  // file and closing the drawer before decode lands, both slower and so easier
  // to hit on a phone — the strip stayed empty for the rest of the session.
  //
  // drawZoomWaveform() has carried this same guard for a while and therefore
  // never showed the bug: it is re-called from updateTrimUI(), so any trim
  // nudge, drag or label refresh repaints it. That asymmetry is what a user
  // sees — Loop Detail drawn, the strip above it blank, one decoded buffer
  // behind both. Bailing here keeps the last good bitmap instead of wiping it;
  // openDrawer()'s music branch is what schedules the repaint once the panel
  // has real layout.
  if (!rect.width) return;
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

const musicUploadBtn = _authoringCtl('musicUploadBtn');
const musicBtnLabel = document.getElementById('musicBtnLabel');
const musicDetail = document.getElementById('musicDetail');
const musicTabDot = document.getElementById('musicTabDot');






const toast = document.getElementById('toast');
// Media format policy + byte checks now live in lib/media_validation.js
// (loaded before this file). Aliases there keep these call sites unchanged.

let toastTimer = null;
let toastHideTimer = null;   // the 200ms post-fade hidden=true; must be cancellable

function showToast(msg, anchorEl, action) {
  // `action` is an optional { label, onClick } that renders a tappable button
  // inside the toast — used for offering an undo on destructive actions. Note
  // .toast is pointer-events:none so it never blocks the canvas; .toast-action
  // re-enables pointer events on itself only.
  clearTimeout(toastHideTimer);     // a replacement toast must survive the
                                    // outgoing one's pending hide
  toast.hidden = false;
  toast.textContent = msg;          // also clears any previous action button
  let holdMs = 2800;
  if (action && action.label && typeof action.onClick === 'function') {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'toast-action';
    btn.textContent = action.label;
    btn.addEventListener('click', () => {
      clearTimeout(toastTimer);
      toast.classList.remove('show');
      toastHideTimer = setTimeout(() => { toast.hidden = true; }, 200);
      // Runs AFTER the hide is scheduled, so if it shows a follow-up toast
      // (Undo -> Redo) that toast clears the pending hide on its way in.
      action.onClick();
    });
    toast.appendChild(btn);
    holdMs = 7000;                  // an offer to undo needs time to read and reach
  }
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
    toastHideTimer = setTimeout(() => { toast.hidden = true; }, 200);
  }, holdMs);
}



function isImageFile(file) {
  // Mirrors ALLOWED_IMAGE_SUBTYPES in app.py — see the note above.
  if (skriblHasUsableMime(file)) return SKRIBL_IMAGE_MIMES.has(file.type.toLowerCase());
  return SKRIBL_IMAGE_EXTENSIONS.test(file.name || '');
}

function setLoopToDrawingLength() {
  if (!audioEl || !strokes.length) return;
  const drawingSeconds = getPlaybackDuration() / 1000;
  const loopLength = window.SkriblLoopTrim.loopLength(drawingSeconds, audioDuration);
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



// Drag the middle of the selection to slide the whole loop window along the
// song, keeping its length locked. Edges (handles) still resize independently
// because they sit above the range in z-order. Stops at the song boundaries.

// --- Loop preview & test seam ---
const previewLoopBtn = _authoringCtl('previewLoopBtn');
const testSeamBtn = _authoringCtl('testSeamBtn');
const matchDrawingBtn = _authoringCtl('matchDrawingBtn');

const nudgeSteps = [0.01, 0.02, 0.05, 0.1];
let nudgeStepIdx = 3;
const nudgeStepLabel = document.getElementById('nudgeStepLabel');
const nudgeStepFinerBtn = _authoringCtl('nudgeStepFiner');
const nudgeStepCoarserBtn = _authoringCtl('nudgeStepCoarser');

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
  // 'slide', matching Flip's nudge and both zoom tracks.
  {
    const _n = window.SkriblLoopTrim.setHandle(
      { start: trimStart, end: trimEnd, duration: audioDuration },
      which, (which === 'start' ? trimStart : trimEnd) + amount, 'slide');
    trimStart = _n.start; trimEnd = _n.end;
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

bindEl('resetPhotoBtn', 'click', resetPhotoAdjustments);
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

function playMusicLooped(totalDurationMs, onStarted) {
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
    playNativeLooped(totalDurationMs, onStarted);
  };
  if (startWebAudioLoop(nativeFallback)) {
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
  nativeFallback();
}

function playNativeLooped(totalDurationMs, onStarted) {
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
  const cursorSize = _eraserSize(size, true) * scale;
  eraserCursor.style.width = cursorSize + 'px';
  eraserCursor.style.height = cursorSize + 'px';
  eraserCursor.style.left = x + 'px';
  eraserCursor.style.top = y + 'px';
}




const photoUploadBtn = _authoringCtl('photoUploadBtn');
const photoBgImg = document.getElementById('photoBgImg');
const photoInput = _authoringCtl('photoInput', 'input');
const photoFitSlider = document.getElementById('photoFitSlider');





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



const photoFitBtns = document.querySelectorAll('.photo-fit-btn');

function initPhotoFitSlider() {
  const active = document.querySelector('.photo-fit-btn.active');
  if (active && photoFitSlider) {
    photoFitSlider.style.width = active.offsetWidth + 'px';
    photoFitSlider.style.transform = 'translateX(0)';
  }
}


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

const photoOpacityEl = _authoringCtl('photoOpacity', 'input');
const photoBlurEl = _authoringCtl('photoBlur', 'input');
const photoBlurValEl = document.getElementById('photoBlurVal');



// Set initial track fills so both sliders render correctly before any input

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
  const cx = (e) => SkriblEventPoint.at(e).clientX;
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
      window.removeEventListener('touchcancel', onEnd);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onMove, { passive: false });
    // touchcancel too — see the note in editor_music.js. A cancelled
    // sequence never fires touchend, so cleanup keyed only to touchend
    // leaves the move listener installed and the drag state set.
    window.addEventListener('touchend', onEnd);
    window.addEventListener('touchcancel', onEnd);
  }
  wrap.addEventListener('mousedown', onStart);
  wrap.addEventListener('touchstart', onStart, { passive: false });
}





// ---------- Skribl name (title) ----------
// The name-tab UI + auto-default naming live in lib/nametab.js, shared with
// Flip (window.SkriblName). serializeSkribl reads the current title through it.
function currentSkriblTitle() {
  return (window.SkriblName && window.SkriblName.get()) || 'Untitled Skribl';
}


// ---------- Draft save / load ----------
// serializeSkribl() produces one self-contained object. The same object shape
// will POST to skribls.net later — only the transport changes.
// ---------- Autosave / crash recovery ----------
// The whole autosave path — serialize/write/schedule/read/restore, the
// restore banner, the trigger bindings and the leave guard — lives in
// editor_draft.js (editor-only; the player never autosaves, and this block
// was ~7 KB of the player's budget). Every call site outside that file is
// typeof-guarded, so the player pays nothing and breaks nothing. The
// pendingPhotoMeta/pendingMusicMeta re-add machinery STAYS below: the
// music/photo drawers use it independently of restore.


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
      _authoringCtl('musicPendingName').textContent = pendingMusicMeta.name;
      let meta = 'Loop saved';
      if (pendingMusicMeta.trimStart != null && pendingMusicMeta.trimEnd != null) {
        const len = (pendingMusicMeta.trimEnd - pendingMusicMeta.trimStart);
        meta = `Loop ${fmtLoopTime(pendingMusicMeta.trimStart)}–${fmtLoopTime(pendingMusicMeta.trimEnd)} · ${len.toFixed(1)}s`;
      }
      _authoringCtl('musicPendingMeta').textContent = meta;
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
      _authoringCtl('photoPendingName').textContent = pendingPhotoMeta.name;
      const parts = [];
      if (pendingPhotoMeta.fit) {
        const fitName = { cover: 'Fill', contain: 'Fit', stretch: 'Stretch' }[pendingPhotoMeta.fit] || pendingPhotoMeta.fit;
        parts.push(fitName);
      }
      if (pendingPhotoMeta.opacity != null) parts.push(Math.round(pendingPhotoMeta.opacity * 100) + '% opacity');
      if (pendingPhotoMeta.blur) parts.push(pendingPhotoMeta.blur + 'px blur');
      if (pendingPhotoMeta.zoom && pendingPhotoMeta.zoom !== 1) parts.push(Math.round(pendingPhotoMeta.zoom * 100) + '% zoom');
      _authoringCtl('photoPendingMeta').textContent = parts.length ? parts.join(' · ') : 'Adjustments saved';
      pCard.hidden = false;
      photoUploadBtn.hidden = true;
      _authoringCtl('photoTabDot').hidden = false;
      _authoringCtl('photoTabDot').classList.add('pending');
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

// The canonical place a payload's current-frame media lives, for WRITERS.
// normalizeSkribl() above does this for readers; before v210 there was no
// writer-side equivalent, so editor_post.js kept mutating payload.music — a
// field serializeSkribl() stopped producing at the v2 frame migration. The
// post-time loop crop was therefore skipped on every v2 Pad post, silently,
// and shared posts shipped the whole song instead of the selected loop. The
// server was migrated for frames; that one client consumer was not. Anything
// that needs to READ OR REPLACE current-frame media goes through here rather
// than learning about frames[0] for itself — format knowledge drifting
// between modules is exactly what caused the bug.
function currentFrameMedia(payload) {
  const frames = payload && payload.frames;
  const f0 = (Array.isArray(frames) && frames.length) ? frames[0] : null;
  return {
    // Legacy top-level is still read so a pre-v2 payload keeps working.
    music: f0 && f0.music != null ? f0.music : ((payload && payload.music) || null),
    photo: f0 && f0.photo != null ? f0.photo : ((payload && payload.photo) || null),
    setMusic(value) {
      if (f0) f0.music = value; else payload.music = value;
    }
  };
}
window.SkriblPayload = { currentFrameMedia };

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
    pauseMode: pauseMode,   // how idle gaps replay; see PAUSE_CAPS
    fps: null,              // replay Skribls don't use fps
    frames: [ frame ],
    draftId: 'draft_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
    userId: null,               // server stamps this later
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    title: currentSkriblTitle(),
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
  // Bump the generation FIRST (v209 review F1). v209 introduced _waGen with the
  // comment "a stop during unlock must not be overtaken by a late start" and
  // then never incremented it here — so Play, Stop, then a resume that resolves
  // afterwards still started the loop, because the deferred go() saw its
  // generation unchanged. The counter existed; the property did not. Clearing
  // _waUnlock with it stops a stale promise from a previous Play standing in
  // for the next one's unlock.
  _waGen++;
  _waUnlock = null;
  if (_waLoopSource) { try { _waLoopSource.stop(); } catch (e) {} try { _waLoopSource.disconnect(); } catch (e) {} _waLoopSource = null; }
}
// F3 (v207 review): the unlock used to be `resume()` with the Promise thrown
// away, and Pad's ordinary Play reaches here from INSIDE clearAndRestore's
// Image.onload callback — i.e. after the click gesture has already returned.
// iOS Safari can still report 'suspended' until resume's promise resolves, so
// start() ran against a context that never unlocked and the replay was silent.
// That is precisely the class the v203 player fix (A1) closed for the player;
// the editor replay never got it. Same shape as A1 here: resume is called
// INSIDE the gesture (unlockWebAudio, from the Play handler), the promise is
// RETAINED, and the source starts only once it resolves. The drawing does not
// wait — it is already running from clearAndRestore — only the audio start is
// gated, and nothing is swallowed by a silent catch.
let _waUnlock = null;      // resume() promise captured in the click gesture
let _waGen = 0;            // a stop during unlock must not be overtaken by a late start
function unlockWebAudio() {
  if (!audioCtx || audioCtx.state !== 'suspended') return null;
  try { const p = audioCtx.resume(); return (_waUnlock = (p && p.then) ? p : null); }
  catch (e) { console.warn('skribl: resume threw', e); return null; }
}
function startWebAudioLoop(onFail) {
  if (!audioCtx || !currentAudioBuffer) return false;
  const buf = buildLoopAudioBuffer();
  if (!buf) return false;
  // Take the gesture-captured unlock BEFORE stopWebAudioLoop(), which clears
  // _waUnlock to kill stale promises (F1). Without this, the Play handler's
  // in-gesture resume would be discarded here and re-requested outside the
  // gesture — silently undoing F3 while every ordering pin still passed.
  const pending = _waUnlock;
  stopWebAudioLoop();
  const gen = ++_waGen, go = () => {
    // 'running', not merely 'not suspended': a source begun on a context that
    // is closed or still unlocking is silence that reports success, which is
    // the whole v210 player lesson applied to the editor path too.
    if (gen !== _waGen || !audioCtx || audioCtx.state !== 'running') return false;
    const src = audioCtx.createBufferSource();
    src.buffer = buf; src.loop = true; src.loopStart = 0; src.loopEnd = buf.duration;
    // Keep the music in lockstep with a sped-up preview. It pitch-shifts,
    // which is the honest trade: music running at its own rate against a
    // 2x drawing drifts a whole take out of sync, and that is worse to
    // review against than a chipmunk. Only the preview is affected — the
    // posted clip and the export are untouched.
    try { src.playbackRate.value = (typeof replayRate === 'number' ? replayRate : 1); } catch (e) {}
    src.connect(audioCtx.destination);
    try { src.start(); } catch (e) { return false; }
    _waLoopSource = src; _waLoopStartCtx = audioCtx.currentTime; _waLoopDuration = buf.duration;
    return true;
  };
  if (audioCtx.state === 'running') return go();
  // Suspended: prefer the promise captured in the gesture; if there is none
  // (Preview Loop calls this synchronously from its OWN click) resume here,
  // which is still inside that gesture. Consumed either way — a promise that
  // resolved for an earlier play says nothing about a context iOS has since
  // re-suspended.
  // HANDING OFF, not just declining (v209 review F2, and the owner's iPhone).
  // Refusing to start on a suspended context is correct but not sufficient: the
  // callers below suppress their native <audio> fallback whenever this returns
  // true, so a context that never reaches 'running' turned "intermittently
  // silent" into "always silent, honestly". On that device Test Seam (native
  // <audio>) plays while Preview Loop (Web Audio) does not, so native is the
  // path that actually works there and must be reachable.
  const fail = (why) => {
    _waGen++;                      // nothing from this attempt may start later
    if (onFail) { const f = onFail; onFail = null; console.warn('skribl: web audio unavailable — ' + why); f(); }
  };
  const p = pending || unlockWebAudio();
  _waUnlock = null;
  if (p && p.then) {
    let settled = false;
    p.then(() => { settled = true; if (!go()) fail('context not running after resume'); },
           (e) => { settled = true; fail('resume rejected: ' + ((e && e.message) || e)); });
    // iOS can leave resume() pending indefinitely rather than rejecting. Silence
    // with no error is the worst outcome for the listener, so time it out.
    setTimeout(() => { if (!settled && !_waLoopSource) fail('resume never settled'); }, 600);
  } else if (p) {
    if (!go()) fail('synchronous resume did not reach running');
  } else {
    fail('no AudioContext resume available');
    return false;
  }
  return true;   // the Web Audio path IS the path taken; only its start defers
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
  a.download = (window.SkriblName ? window.SkriblName.filename(draft.title)
    : (draft.title || 'skribl').replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.skribl');
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
  loopCrossfadeMs = 0;
  // State above, drawer UI below. The player runs this on every load — it was
  // clearing waveform canvases and rewriting button labels for a drawer it does
  // not have. Unguarded property writes on absent elements (musicDetail.hidden)
  // would throw the moment the player's template drops the editor shell.
  if (!document.body.classList.contains('player-mode')) {
    if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
    if (musicDetail) musicDetail.hidden = true;
    if (musicInput) musicInput.value = '';
    if (musicUploadBtn) musicUploadBtn.classList.remove('loaded');
    if (musicBtnLabel) musicBtnLabel.textContent = 'Add music';
    if (musicTabDot) musicTabDot.hidden = true;
    if (musicRemove) musicRemove.hidden = true;
    if (waveformCtx) waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
    if (zoomWaveformCtx) zoomWaveformCtx.clearRect(0, 0, zoomWaveformCanvas.width, zoomWaveformCanvas.height);
    if (loopZoomLabel) loopZoomLabel.textContent = '0:00.00 → 0:00.00 [0.00s]';
  }
  // Photo
  photoBg = null;
  if (photoBgImg._objectUrl) { URL.revokeObjectURL(photoBgImg._objectUrl); photoBgImg._objectUrl = null; }
  photoBgImg._draftData = null;
  photoBgImg._fileName = null;
  photoBgImg.src = '';
  photoBgImg.style.display = 'none';
  photoBgImg.style.filter = '';
  photoInput.value = '';
  // Photo STATE resets unconditionally; the photo drawer's DOM is editor-only.
  // Same split as the music half above.
  photoFit = 'cover';
  photoOpacityVal_ = 1;
  photoBlur_ = 0;
  if (!document.body.classList.contains('player-mode')) {
    photoUploadBtn.classList.remove('loaded');
    const _pLabel = document.querySelector('#photoUploadBtn span');
    if (_pLabel) _pLabel.textContent = 'Add a photo';
    for (const _id of ['photoDetail', 'photoTabDot', 'photoRemove']) {
      const _e = document.getElementById(_id);
      if (_e) _e.hidden = true;
    }
    const _opEl = document.getElementById('photoOpacity');
    if (_opEl) _opEl.value = 100;
    const _opVal = document.getElementById('photoOpacityVal');
    if (_opVal) _opVal.textContent = '100%';
    const _blEl = document.getElementById('photoBlur');
    if (_blEl) {
      _blEl.value = 0;
      const _blVal = document.getElementById('photoBlurVal');
      if (_blVal) _blVal.textContent = '0px';
      updateSliderFill(_blEl);
    }
  }
  photoOffsetX = 0.5;
  photoOffsetY = 0.5;
  photoZoom = 1; setZoomSliderUI();
  // Hide the Reposition button/hint now that no photo is loaded. If the draft
  // being loaded has a photo, loadSkribl's photo block re-shows it right after.
  if (typeof updateRepositionUI === 'function') updateRepositionUI();
}

// Document-load generation. Every asynchronous completion loadSkribl() starts —
// the base-snapshot Image, the music fetch, loadedmetadata, the decode, and the
// deferred writeAutosave — belongs to ONE document load, and any of them can
// land after the user has opened a different Skribl.
//
// Reproduced before this existed: load draft A (3s music), load draft B (9s),
// let B's decode finish and then A's, and A rewrote currentAudioBuffer,
// audioDuration AND trimEnd to A's values while B was the document on screen.
// The user's open loop window was silently replaced by one from a draft they
// had already navigated away from.
//
// A generation token checked at EVERY completion is preferable to a guard per
// callback: the failure mode is a callback nobody remembered to guard, so the
// rule has to be uniform enough that omitting it is visible.
let skriblLoadSeq = 0;

function loadSkribl(data) {
  // Validate the raw payload has a recognizable format marker, THEN canonicalize.
  if (!data || (data.version == null && data.schemaVersion == null && !data.frames)) { showToast('That file isn\'t a valid draft', menuBtn); return; }
  const loadSeq = ++skriblLoadSeq;   // this document load owns every callback below
  data = normalizeSkribl(data);
  // Adopt the drawing's own pause handling BEFORE any timeline is built,
  // so the player replays it the way it was posted rather than the way
  // this browser happens to be set.
  if (data.pauseMode) setPauseMode(data.pauseMode);
  // Adopt the loaded draft's name into the tab (blank leaves the auto-default).
  if (window.SkriblName && data.title && !/^Untitled Skribl$/.test(data.title)) window.SkriblName.set(data.title);
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
      // Pinned by V214e's base-snapshot scenario: two payloads with known
      // snapshot colours, A released last. Remove this line and the open
      // document's blue canvas is overwritten by A's red — a silent overwrite
      // of the drawing itself, not of media metadata.
      if (loadSeq !== skriblLoadSeq) return;   // a later Skribl is on screen
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
    postBtn.disabled = false;
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
    photoOpacityVal_ = data.photo.opacity != null ? data.photo.opacity : 1;
    photoBgImg.style.opacity = photoOpacityVal_;
    photoBlur_ = data.photo.blur != null ? data.photo.blur : 0;
    photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
    const _off = data.photo.offset || {};
    photoOffsetX = _off.x != null ? _off.x : 0.5;
    photoOffsetY = _off.y != null ? _off.y : 0.5;
    photoZoom = clampPhotoZoom(data.photo.zoom);
    applyPhotoPosition();

    // State above, drawer UI below — the same split the music branch has.
    // Every line below touches markup only the editor has; v190 removed it from
    // the player, and the unguarded version threw inside loadSkribl, aborting
    // the whole restore. See harness/verify_player_photo.py.
    if (!document.body.classList.contains('player-mode')) {
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
      setZoomSliderUI();
      if (typeof updateRepositionUI === 'function') updateRepositionUI();
      const _pd = document.getElementById('photoDetail');
      if (_pd) _pd.hidden = false;
      if (photoUploadBtn) photoUploadBtn.classList.add('loaded');
      const _ptd = document.getElementById('photoTabDot');
      if (_ptd) _ptd.hidden = false;
      const _prm = document.getElementById('photoRemove');
      if (_prm) _prm.hidden = false;
      const opEl2 = document.getElementById('photoOpacity');
      if (opEl2) {
        opEl2.value = Math.round(photoOpacityVal_ * 100);
        const _ov = document.getElementById('photoOpacityVal');
        if (_ov) _ov.textContent = Math.round(photoOpacityVal_ * 100) + '%';
        updateSliderFill(opEl2);
      }
      const blEl2 = document.getElementById('photoBlur');
      if (blEl2) {
        blEl2.value = photoBlur_;
        const _bv = document.getElementById('photoBlurVal');
        if (_bv) _bv.textContent = photoBlur_ + 'px';
        updateSliderFill(blEl2);
      }
      setTimeout(initPhotoFitSlider, 50);
    }
  }

  // Music — restore full audio + trim points (reversible)
  if (data.music && data.music.data) {
    // BUG A (v210). Loop bounds used to be installed ONLY inside the <audio>
    // element's 'loadedmetadata' handler below. trimEnd starts at 0, and iOS
    // defers media loading until playback is requested, so on a shared link the
    // event routinely had not fired when the user tapped Play: trimEnd was
    // still 0, buildLoopAudioBuffer() saw a zero-length loop window, returned
    // null with no exception, and nothing was ever constructed. Silent on
    // iPhone, fine on desktop, invisible to every headless test — until the
    // harness suppressed the event and reproduced it exactly.
    //
    // The serialized values are authority and are installed SYNCHRONOUSLY here.
    // trimEnd stays null when the payload omits it; the default needs a real
    // duration, and the decoded buffer supplies that below. loadedmetadata may
    // still refresh the element and the editor's drawer UI, but it is no longer
    // load-bearing for Web Audio playback.
    trimStart = data.music.trimStart != null ? data.music.trimStart : 0;
    trimEnd = data.music.trimEnd != null ? data.music.trimEnd : null;
    loopCrossfadeMs = data.music.crossfadeMs != null ? data.music.crossfadeMs : 0;
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    fetch(data.music.data).then(r => r.arrayBuffer()).then(buf => {
      if (loadSeq !== skriblLoadSeq) return;   // superseded before the bytes arrived
      if (audioEl && audioEl._objectUrl) URL.revokeObjectURL(audioEl._objectUrl);
      const blob = new Blob([buf]);
      const url = URL.createObjectURL(blob);
      audioEl = new Audio(url);
      audioEl._objectUrl = url;
      audioEl._draftData = data.music.data;
      audioEl._fileName = data.music.name || 'Music from draft';
      audioEl.addEventListener('loadedmetadata', () => {
        if (loadSeq !== skriblLoadSeq) return;   // this element belongs to an older load
        // UI/element refresh only. The authoritative loop state was installed
        // synchronously above and is finalised on decode (BUG A) — do not move
        // trim assignment back in here.
        if (!Number.isFinite(audioDuration) || audioDuration <= 0) audioDuration = audioEl.duration;
        if (trimEnd == null && Number.isFinite(audioEl.duration)) {
          trimEnd = Math.min(audioEl.duration, 20);
        }
        clampTrim();
        if (!document.body.classList.contains('player-mode')) {
          if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
          if (musicDetail) musicDetail.hidden = false;
          if (musicUploadBtn) musicUploadBtn.classList.add('loaded');
          if (musicBtnLabel) musicBtnLabel.textContent = 'Loaded from draft';
          if (musicTabDot) musicTabDot.hidden = false;
          const _mr = document.getElementById('musicRemove');
          if (_mr) _mr.hidden = false;
          updateTrimUI();
        }
      });
      audioCtx.decodeAudioData(buf.slice(0)).then(audioBuffer => {
        if (loadSeq !== skriblLoadSeq) return;   // THE ONE THAT BIT: see the note above
        currentAudioBuffer = audioBuffer;
        // BUG A: the decoded buffer is the authoritative duration source. It
        // arrives independently of the <audio> element, so a post whose
        // serialized trimEnd is absent (legacy, or a default-trim post) still
        // gets a usable loop window without waiting on loadedmetadata. After
        // this line the invariant holds: once currentAudioBuffer exists, the
        // loop bounds are valid whether or not media metadata ever loaded.
        audioDuration = audioBuffer.duration;
        if (trimEnd == null) trimEnd = Math.min(audioDuration, 20);
        clampTrim();
        // LATE-DECODE START (v202 review amendment, A1). On a phone the decode
        // routinely finishes AFTER the user pressed Play: the drawing was
        // already animating, paStartAtElapsed() had no buffer and no-op'd, and
        // nothing ever revisited the music — a silently mute post on iPhone.
        // If playback is running when the buffer arrives, start the loop at
        // the drawing's CURRENT elapsed position. paStartAtElapsed() calls
        // paStop() first, so a race with a simultaneous play/seek cannot
        // stack two sources.
        if (window._skriblLateAudio) window._skriblLateAudio();
        // Waveforms are drawer furniture; the player painted them into canvases
        // it never shows, on every shared link with music.
        if (!document.body.classList.contains('player-mode')) {
          setTimeout(() => { drawWaveform(audioBuffer); drawZoomWaveform(); updateZoomHandles(); }, 60);
        }
      }).catch(e => console.warn('skribl: music decode failed', e));
    }).catch(e => console.warn('skribl: music fetch failed', e));
  }

  updateEmptyHint();
  updateCanvasLockCue();
  if (!document.body.classList.contains('player-mode')) {
    showToast('Draft loaded', menuBtn);
    // The loaded draft is now the active work — refresh autosave so a later
    // restore prompt reflects this, not a stale previous session.
    setTimeout(() => {
      // UNPINNED, deliberately labelled, and for a reason worth keeping:
      // with the four guards above holding, the state at 300ms IS the
      // current document, so a stale timer would autosave the RIGHT thing
      // and no assertion can see the difference. Pinning it would need a
      // compound mutation (this guard AND another removed), which is
      // weaker evidence than none. It earns its place only if one of the
      // others is ever removed.
      if (loadSeq !== skriblLoadSeq) return;   // do not autosave a superseded draft
      if (typeof writeAutosave === 'function') writeAutosave();
    }, 300);
  }
}

bindEl('draftInput', 'change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(reader.result);
      // A Flip .skribl (playbackMode 'flip') shares the {frames} container but
      // is a flipbook, not a replay; it loaded here as an EMPTY drawing that
      // still said "Draft loaded". Refuse with directions. Draft-file path
      // only — the shared player still opens Flip posts via loadSkribl.
      if (data && data.playbackMode === 'flip') return showToast('That\'s a Flip Skribl — open it in Flip Mode', menuBtn);
      loadSkribl(data);
    } catch (err) {
      showToast('Couldn\'t read that draft file', menuBtn);
    }
  };
  reader.readAsText(file);
  e.target.value = '';
});

// ---------- Autosave wiring: moved to editor_draft.js ----------


// Reapply saved media settings when the user re-adds a file after a restore.
if (typeof pendingMusicMeta !== 'undefined') {
  const musicInputEl = document.getElementById('musicInput');
  // Music trim reapply is handled in the main loadedmetadata handler
  // (applyPendingMusicSettings) to avoid a listener-timing race.

  const photoInputEl = document.getElementById('photoInput');
  // Absent on the player, which has no photo picker.
  if (photoInputEl) photoInputEl.addEventListener('change', () => {
    if (!pendingPhotoMeta) return;
    const meta = pendingPhotoMeta;
    pendingPhotoMeta = null;
    const pCard = document.getElementById('photoPending');
    if (pCard) pCard.hidden = true;
    photoUploadBtn.hidden = false;
    // The dot stays AMBER without this. Amber means "remembered but missing —
    // re-add it"; the user has just re-added it, so it must go green. This
    // path cleared the meta and the card by hand but never the dot's .pending
    // class, and refreshPendingCards is the only function that owns it.
    refreshPendingCards();
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
        _authoringCtl('photoOpacityVal').textContent = Math.round(photoOpacityVal_ * 100) + '%';
        updateSliderFill(opEl);
      }
      if (meta.blur != null) {
        photoBlur_ = meta.blur;
        photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
        const blEl = document.getElementById('photoBlur');
        blEl.value = photoBlur_;
        _authoringCtl('photoBlurVal').textContent = photoBlur_ + 'px';
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
    _authoringCtl('musicPending').hidden = true;
    musicUploadBtn.hidden = false;
    if (!audioEl) musicTabDot.hidden = true;
    scheduleAutosave();
  });

  const pBtn = document.getElementById('photoPendingBtn');
  const pDismiss = document.getElementById('photoPendingDismiss');
  if (pBtn) pBtn.addEventListener('click', () => photoInputEl.click());
  if (pDismiss) pDismiss.addEventListener('click', () => {
    pendingPhotoMeta = null;
    _authoringCtl('photoPending').hidden = true;
    photoUploadBtn.hidden = false;
    if (!photoBgImg || photoBgImg.style.display === 'none') _authoringCtl('photoTabDot').hidden = true;
    scheduleAutosave();
  });
}

// ==================== EXPORT / POST COMPOSER ====================
// Both sections now live in editor_export.js and editor_post.js, loaded ONLY
// by the editor template. They were self-contained IIFEs (checked: nothing
// outside them referenced anything they defined), and the player executed
// initExport() and initPostComposer() on every shared link to wire up
// controls it does not have. Moved verbatim, not rewritten.
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
    const apiBase = window.SKRIBL_API_BASE;
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
    // Measure the COLUMN the canvas actually lives in, not the viewport. This
    // used to be `window.innerWidth - 40`, and .app has a max-width: on a 1023px
    // viewport the column is 718px, so the scale came out at the 1:1 cap and the
    // wrap was set to the authored 816px. `.canvas-wrap { max-width: 100% }` then
    // clipped it back to 718 and `overflow: hidden` cropped the drawing — a
    // shared link lost ~100px of its right-hand side on any viewport wider than
    // the column. The editor never had this because layoutEditorCanvas() measures
    // its container; this is the same measurement, done the same way.
    //
    // .app rather than canvasWrap.parentElement: in player mode .canvas-area is
    // `display: contents`, so its own rect is 0x0 and would scale everything to
    // the 120px floor.
    const appEl = document.querySelector('.app');
    let availW = Math.max(120, window.innerWidth - 40);   // fallback, as before
    if (appEl) {
      const r = appEl.getBoundingClientRect();
      if (r.width > 0) {
        const cs = getComputedStyle(appEl);
        // getBoundingClientRect() reports the BORDER box, so both the padding
        // and the border have to come off to get the space a child can occupy.
        // .app has a 1px border each side; subtracting only the padding left the
        // canvas 2px wider than its column and `overflow: hidden` clipped it.
        const insetX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0)
          + (parseFloat(cs.borderLeftWidth) || 0) + (parseFloat(cs.borderRightWidth) || 0);
        availW = Math.max(120, r.width - insetX);
      }
    }
    // Clamp the viewport budget so a short viewport (or an on-screen keyboard)
    // can't drive the available height ≤ 0 and flip the scale negative.
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
  /* Declared HERE, above sizePlayerCanvas, because that function runs
     immediately on the line after its own definition and resets this -- and a
     `let` read before its declaration is executed is a temporal-dead-zone
     throw, not an undefined. Its meaning belongs with drawFlipFrame below. */
  let lastFlipDrawn = -1;
  /* Same placement rule as lastFlipDrawn, same reason. Created lazily inside
     drawFlipFrame — the frames it caches are immutable for the life of the
     page, so index keys are safe and the store never needs invalidating except
     by the backing-store reset below. */
  let flipBitmaps = null;
  function sizePlayerCanvas() {
    const dpr = window.devicePixelRatio || 1;
    layoutPlayerCanvas();
    canvas.width = Math.round(authorW * dpr);
    canvas.height = Math.round(authorH * dpr);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    // Assigning canvas.width CLEARS the bitmap, so whatever drawFlipFrame
    // believes is on screen is gone and the memo would skip the repaint,
    // leaving the player blank.
    //
    // NOT CURRENTLY REACHABLE, and said so rather than implied: this function
    // runs once, on the line after its own definition, before any frame has
    // been drawn. Every resize path goes to layoutPlayerCanvas(), which is CSS
    // only and deliberately does not clear. Removing this line passes the suite.
    // It stays because the one thing that would make it reachable -- calling
    // sizePlayerCanvas() again -- is exactly the change whose failure mode is a
    // blank player, and the reset costs nothing to keep beside the assignment
    // that causes it.
    lastFlipDrawn = -1;
    flipBitmaps = null;   // captures describe the old backing store
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
  // Per-page hold (v109): a page occupies `hold` base-fps slots instead of one.
  // Read defensively — a payload written before v109 has no hold field at all, so
  // every page reads as 1 and playback is bit-for-bit what it always was.
  // lib/holdtiming.js owns the clamp and the cumulative table; the Flip editor
  // reads the same module, so a hold means one thing on both surfaces. The 4
  // used to be written out here as a literal, a copy of flip.js's MAX_HOLD with
  // nothing forcing them to agree. Inline fallback kept, as the other libs do.
  const _hold = (typeof window !== 'undefined' && window.SkriblHold) ? window.SkriblHold : null;
  const flipHolds = isFlip
    ? (_hold ? _hold.table(flipFrames) : flipFrames.map(f => {
        const h = Math.round(Number(f && f.hold));
        return (isFinite(h) && h >= 1) ? Math.min(h, 4) : 1;
      }))
    : null;
  const flipUnits = isFlip ? (_hold ? _hold.units(flipHolds) : flipHolds.reduce((a, b) => a + b, 0)) : 0;
  const flipDurMs = isFlip
    ? (_hold ? _hold.durationMs(flipHolds, flipFps) : Math.max(1, (flipUnits / flipFps) * 1000))
    : 0;
  // Map elapsed time -> page index through the cumulative hold table.
  function flipIndexAt(cycT) {
    if (_hold) return _hold.indexAt(flipHolds, flipFps, cycT);
    let u = Math.floor((cycT / 1000) * flipFps);
    if (!(u >= 0)) u = 0;
    let acc = 0;
    for (let i = 0; i < flipHolds.length; i++) {
      acc += flipHolds[i];
      if (u < acc) return i;
    }
    return flipHolds.length - 1;
  }
  /* A FLIP FRAME IS STATIC, SO PAINTING IT TWICE IS PURE WASTE, and the RAF
     loop was asking for it about five times per frame: requestAnimationFrame
     runs at the display's rate while the flipbook advances at fps, so at 12fps
     on a 60Hz screen four of every five paints redrew a picture already on
     screen.

     Invisible while every page costs the same. A key page measured 0.4ms, so
     the extra four cost 1.6ms of a 83ms budget and nobody noticed. A blurred
     in-between of the same drawing measured 41ms -- 26 samples of every stroke,
     five passes each -- and five of those is 205ms of work for 83ms of wall
     clock, which the loop simply cannot deliver. Reported as "it slows way down
     when it shows the in-between slides", and that is what it was.

     The memo is safe because the backing store is only cleared by
     sizePlayerCanvas(), which resets it; a plain resize deliberately re-lays
     out CSS only and leaves the painted frame alone (see below). Seek and the
     end-of-play paint go through here too and are correct without forcing: if
     the frame they want is already the one on screen, not repainting it is the
     right answer. */
  /* v262: and a frame is rasterised at most ONCE per loaded document. The memo
     above stops repaints of the frame already on screen; this stops repaints of
     a frame the player has ALREADY shown once. A generated in-between is
     thousands of points and repainting it on every loop costs ~100-200ms on a
     phone — the same stall the editor had, fixed by the same shared rule
     (lib/framebitmap.js): first paint is captured at the displayed resolution,
     every later visit is one drawImage. Keys are frame indices because the
     player's frames never change; the store is dropped only with the backing
     store (sizePlayerCanvas), whose captures it describes. */
  function drawFlipFrame(fi) {
    const at = Math.max(0, Math.min(flipFrames.length - 1, fi));
    if (at === lastFlipDrawn) return;
    const s = getCanvasLogicalSize();
    const FB = window.SkriblFrameBitmap;
    if (FB && !flipBitmaps) flipBitmaps = FB.store();
    const hit = FB ? FB.get(flipBitmaps, at) : null;
    ctx.clearRect(0, 0, s.width, s.height);
    if (hit) { ctx.drawImage(hit, 0, 0, s.width, s.height); lastFlipDrawn = at; return; }
    const fr = flipFrames[at];
    if (fr && Array.isArray(fr.strokes) && fr.strokes.length) {
      paintStrokesStatic(fr.strokes);
      if (FB) {
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        const sz = FB.captureSize(canvas.width, canvas.height,
                                  rect.width * dpr, rect.height * dpr);
        if (FB.wants(flipBitmaps, fr.strokes.length, sz.w, sz.h))
          FB.capture(flipBitmaps, at, canvas, sz.w, sz.h);
      }
    }
    lastFlipDrawn = at;
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
  let paSource = null, paGain = null, paBuffer = null, paGen = 0;
  function paLoopBuffer() {
    // Build once and cache — the player's trims/crossfade don't change post-load.
    if (!paBuffer) {
      try { paBuffer = buildLoopAudioBuffer(); } catch (e) {
        // NOT silent any more (v210). This catch swallowed the exception, which
        // made "the builder threw" and "the builder returned null" identical
        // to every caller — and erased the one piece of evidence that would
        // have named the iPhone silence in a day instead of a week. The permanent
        // diagnostic path is a warning; the harness pins the equivalence class.
        console.warn('skribl: loop buffer build failed', e);
        paBuffer = null;
      }
    }
    return paBuffer;
  }
  function paStop() {
    // Bump the generation FIRST: a start awaiting its unlock must not land
    // after the user stopped (v209 review F1 — the counter existed in the Pad
    // path but nothing ever incremented it on stop).
    paGen++;
    if (audioEl && !audioEl.paused) { try { audioEl.pause(); } catch (e) {} }   // native fallback, if it took over (H1)
    if (paSource) {
      try { paSource.stop(); } catch (e) {}
      try { paSource.disconnect(); } catch (e) {}
      paSource = null;
    }
  }
  // Start the loop bed aligned to a drawing-elapsed position (ms). Returns false
  // (a no-op) if audio isn't decoded yet — the drawing still plays and a later
  // start (next play/seek) picks the audio up once the buffer is ready.
  //
  // v210, and this is the whole bug the iPhone found. The player builds its
  // AudioContext in loadSkribl(), which on a share link runs at PAGE LOAD with
  // no user activation, so iOS hands back a SUSPENDED context. This function
  // used to fire-and-forget resume() and then start() anyway, which sets
  // paSource without producing a sound. A1's repair in play() was then
  // unreachable, because it only retried `if (running && !paSource)` — and
  // paSource was already non-null. A source object existing is NOT the same as
  // audible playback, and treating them as equivalent is what let A1 look
  // fixed for three builds while every shared link was silent on iPhone.
  // Desktop never showed it: its context is running from the start, so the
  // suspended branch is dead code there — including in the harness.
  //
  // So: no source is EVER constructed while the context is suspended. The
  // unlock is awaited, the generation is re-checked after the await (a Stop or
  // a second Play during the wait must win), and only a confirmed 'running'
  // context gets a source. paSource now means "started on a running context".
  function paStartAtElapsed(elapsedMs) {
    if (!audioCtx) return false;
    const buf = paLoopBuffer();
    if (!buf) return false;
    paStop();
    const gen = ++paGen;
    const mk = () => {
      // Re-check EVERYTHING that could have changed across the await.
      if (gen !== paGen || !audioCtx || audioCtx.state !== 'running') return false;
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
    };
    if (audioCtx.state === 'running') return mk();
    // v211 (v210 review H1): parity with the editor. If Web Audio cannot
    // unlock — resume() rejects, never settles (iOS leaves it pending), or
    // resolves onto a context that still isn't running — hand off to the
    // native <audio> element loadSkribl already created from the same media,
    // aligned to the drawing position. A browser where Web Audio will not
    // unlock but <audio> would play must not stay silent because Web Audio
    // was tried first. Nothing is swallowed: the reason is logged.
    const nativeFallback = (why) => {
      // Guard against a stale attempt (a Stop or a newer Play happened), but
      // NOT against our own paStop(): paStartAtElapsed calls paStop() before
      // bumping to `gen`, so `gen` IS the current generation here.
      if (gen !== paGen) return;
      paGen++;
      console.warn('skribl: player web audio unavailable — ' + why + ' — using native audio');
      if (!audioEl) return;
      try {
        const dur = buf.duration;
        const off = dur > 0 ? (((elapsedMs / 1000) % dur) + dur) % dur : 0;
        audioEl.currentTime = trimStart + off;
        audioEl.loop = true;
        const pp = audioEl.play();
        if (pp && pp.catch) pp.catch((e) => console.warn('skribl: native audio failed too', e));
      } catch (e) { console.warn('skribl: native audio failed too', e); }
    };
    let p = null;
    try { p = audioCtx.resume(); } catch (e) { nativeFallback('resume threw'); return false; }
    if (p && p.then) {
      let settled = false;
      p.then(() => { settled = true; if (!mk()) nativeFallback('context not running after resume'); },
             (e) => { settled = true; nativeFallback('resume rejected: ' + ((e && e.message) || e)); });
      setTimeout(() => { if (!settled && !paSource) nativeFallback('resume never settled'); }, 600);
    } else if (!mk()) {
      nativeFallback('synchronous resume did not reach running');
    }
    // The drawing never waits on audio; the loop joins when the context is up.
    return false;
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
      drawFlipFrame(flipIndexAt(cycT));
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
    const clientX = SkriblEventPoint.at(e).clientX;
    return (clientX - rect.left) / rect.width;
  }

  function frame() {
    const elapsed = elapsedBase + (performance.now() - segStart);
    if (isFlip) {
      const cycT = flipDurMs ? (elapsed % flipDurMs) : 0;
      drawFlipFrame(flipIndexAt(cycT));
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

  // Late-decode hook (module scopes differ): when the buffer arrives
  // mid-playback, start the loop where the drawing already is.
  window._skriblLateAudio = () => { if (running) paStartAtElapsed(elapsedBase + (performance.now() - segStart)); };

  function play() {
    if (running || (!timeline.length && !isFlip)) return;
    // Unlock the AudioContext inside the click gesture — and AWAIT it (v202
    // review amendment, A1): resume() is promise-returning, and iOS Safari can
    // report 'suspended' until that promise resolves. The old fire-and-forget
    // call let AudioBufferSourceNode.start() run against a context that never
    // actually unlocked. The drawing does not wait (begin() runs on its own
    // path); only the AUDIO start is gated on the resolved resume, via the
    // second audioStart() below once the context is genuinely running.
    if (audioCtx && audioCtx.state === 'suspended') {
      // Ask for the unlock INSIDE the gesture — iOS is far happier resuming
      // here than from a later callback. The result is not acted on here:
      // paStartAtElapsed owns the "only start on a running context" rule, so
      // whichever of the two resumes wins, no source exists until the context
      // genuinely reports running. The old retry (`if (running && !paSource)`)
      // is GONE — it was unreachable, because begin() had already set paSource
      // by starting a silent source on the suspended context (v210).
      try { audioCtx.resume(); } catch (e) { console.warn('skribl: resume threw', e); }
    }
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
      // touchcancel too: a cancelled scrub otherwise leaves playback
      // frozen at the scrub position with the listener still live.
      window.addEventListener('touchend', onScrubEnd);
      window.addEventListener('touchcancel', onScrubEnd);
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
      window.removeEventListener('touchcancel', onScrubEnd);
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
  // The two fingers of THIS pinch are the ones on the canvas, not the first two
  // on the screen. See the note at the call site in editor_draw.js.
  const _own = SkriblPinch.own(e);
  if (!_own || _own.length < 2) return;
  if (typeof e.preventDefault === 'function') e.preventDefault();
  // Show the HUD too, not just the zoom: Fit lives there, and on a skinny phone
  // the magnify button that would otherwise reveal it is hidden.
  //
  // AFTER the two-finger check, not before. Enabling the magnifier is a visible
  // state change and it used to happen on any call that reached this function,
  // including the ones that then bailed out one line later — so a gesture that
  // was never a pinch still turned zoom on. Nothing about revealing the HUD
  // needs to precede knowing that this is a pinch.
  if (typeof ZoomView.enabled === 'function' && !ZoomView.enabled()) {
    if (typeof ZoomView.enable === 'function') ZoomView.enable();
  }
  if (window._skriblRevealZoomHud) window._skriblRevealZoomHud();
  abortStrokeForPinch();
  pinching = true;
  const t0 = _own[0], t1 = _own[1];
  // Remember WHICH two fingers. _pinchMove is bound to window and reads the
  // screen-wide list, so a third contact — the resting thumb again — could
  // otherwise take a slot and the pinch would be computed from a pair that
  // includes a finger standing still, halving the apparent zoom.
  _pinch = {
    ids: [t0.identifier, t1.identifier],
    startDist: _touchDist(t0, t1), lastDist: _touchDist(t0, t1),
    lastMid: _touchMid(t0, t1)
  };
}

function _pinchMove(e) {
  if (!pinching || !_pinch) return;
  const pair = SkriblPinch.pair(e, _pinch && _pinch.ids);
  if (!pair) return;
  e.preventDefault();
  const t0 = pair[0], t1 = pair[1];
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
  // End the pinch as soon as either of ITS OWN fingers lifts. A single remaining
  // finger will NOT resume drawing (it never fired a fresh touchstart); the user
  // lifts and taps again to draw — standard, and avoids a stray line.
  //
  // Counting to two instead would leave the pinch live when one of its fingers
  // lifted while an unrelated resting contact kept the screen-wide total at two:
  // the gesture would then be steered by a pair that no longer exists.
  if (SkriblPinch.pair(e, _pinch && _pinch.ids)) return;
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

  bindEl('zoomInBtn', 'click', function () { ZoomView.step(1); });
  bindEl('zoomOutBtn', 'click', function () { ZoomView.step(-1); });
  bindEl('zoomFitBtn', 'click', function () { ZoomView.fit(); });

  // Header magnifier: a toggle that shows/hides the zoom pill. Turning it OFF
  // also resets to 100% so you're never left magnified with no controls. While
  // off, pinch / wheel / Space-drag all no-op (they check ZoomView.enabled()).
  const magnifyBtn = document.getElementById('magnifyBtn');
  function setMagnify(on) {
    // Same hint key as Flip: this is one behaviour across two surfaces, so
    // being taught it on Pad should not mean being taught it again on Flip.
    if (on && window.SkriblHints) {
      window.SkriblHints.show('magnify-pan',
        'Zoomed in. Scroll — or hold Space and drag — to move to the part you want.');
    }
    magnifyOn = on;
    hud.hidden = !on;
    if (magnifyBtn) {
      magnifyBtn.classList.toggle('active', on);
      magnifyBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    }
    if (!on) ZoomView.fit();     // return the canvas to 100% when hiding controls
  }
  if (magnifyBtn) magnifyBtn.addEventListener('click', function () { setMagnify(!magnifyOn); });
  // Published so a PINCH can reveal the zoom HUD. On a skinny phone the magnify
  // button is hidden (there is no room for nine controls in one row), and the
  // HUD is where Fit lives — so without this a pinch-zoomed user would have no
  // way back to 100%: zoomed in, no button, no Fit, and pinching out is fiddly
  // to land exactly. Hiding a control is only safe when nothing reachable only
  // through it becomes unreachable.
  window._skriblRevealZoomHud = function () { if (!magnifyOn) setMagnify(true); };

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
    const t = SkriblEventPoint.at(ev);
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
  //
  // v211 (owner, desktop): this used to gate BOTH the intercept and the
  // cursor on `zoom > 1`. At 100% the guard was false, the capture-phase
  // intercept skipped, and startDraw ran — so Space+drag DREW A LINE. That is
  // the wrong failure even when there is nothing to pan: the universal
  // contract of holding Space is "the pointer is a hand now, not a pen". So
  // Space always claims the drag and always suppresses drawing; the pan
  // itself is simply a no-op at 100% (nothing to move), and the cursor says
  // 'grab' either way so the user knows the mode changed.
  let spaceHeld = false, spaceDragging = false, lastX = 0, lastY = 0;
  function typingTarget(el) { return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable); }
  window.addEventListener('keydown', function (e) {
    if (e.code === 'Space' && !typingTarget(e.target)) {
      if (!spaceHeld) canvasWrap.style.cursor = spaceDragging ? 'grabbing' : 'grab';
      spaceHeld = true;
      e.preventDefault();               // no page scroll / button activation
    }
  });
  window.addEventListener('keyup', function (e) {
    if (e.code === 'Space') { spaceHeld = false; spaceDragging = false; canvasWrap.style.cursor = ''; }
  });
  // Capture phase so a Space-drag claims the mousedown before startDraw fires.
  canvasWrap.addEventListener('mousedown', function (e) {
    if (spaceHeld) {
      spaceDragging = true; lastX = e.clientX; lastY = e.clientY;
      canvasWrap.style.cursor = 'grabbing';
      e.preventDefault(); e.stopPropagation();
    }
  }, true);
  // Belt and braces: if focus was somewhere that ate the keydown (a button
  // the user just clicked), the mousedown still must not draw while Space is
  // physically down. startDraw checks this flag too.
  window._skriblSpaceHeld = function () { return spaceHeld; };
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

/* ---- canvas size (Pad) ----------------------------------------------------
   Flip has had this since v110; Pad had nothing, so a drawing's shape was
   whatever the viewport gave it. Same table, same ids, same markup as Flip's
   row — see lib/canvassizes.js.

   THE DIFFERENCE FROM FLIP, and the reason this is not a copy of Flip's
   handler: Pad records STROKE TIMING, and a take is a continuous performance.
   Flip can resize freely because its pages are independent and coordinates are
   simply kept. Here, resizing mid-take would change the space a replay is
   drawn into halfway through the recording it is replaying.

   So the rule is: free while the canvas is empty, refused once there is
   content. Refused, not silently ignored — the note says why, and "clear all"
   or a reload is the way out. Destroying a recording to change a canvas would
   be a far worse trade than declining. */
(function () {
  const seg = document.getElementById('canvasSeg');
  const note = document.getElementById('canvasSegNote');
  const table = window.SkriblCanvasSizes;
  if (!seg || !table) return;

  // Labels come from the table so a preset cannot be renamed there and left
  // stale in the markup — the exact drift that made '9:16' mean 2:3.
  [...seg.querySelectorAll('button')].forEach(b => {
    const preset = table.byId(b.dataset.size);
    if (preset) b.textContent = preset.label;
    else b.remove();
  });

  // The menu ships `hidden`, so at init the buttons have no width and a
  // one-shot position leaves the pill at opacity 0 — the canvas row showed no
  // selection until you tapped one. The shared tracker watches for the group
  // gaining layout and places the pill then.
  if (window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  function positionSlider() {
    if (window.SkriblSegSlider) { window.SkriblSegSlider.place(seg); return; }
    const on = seg.querySelector('button.on');
    const pill = seg.querySelector('.seg-slider');
    if (!on || !pill || !on.offsetWidth) return;
    pill.style.width = on.offsetWidth + 'px';
    pill.style.transform = 'translateX(' + (on.offsetLeft - 3) + 'px)';
    pill.style.opacity = 1;
  }

  function locked() {
    return hasContent || recording || finishedRecording;
  }

  function sync() {
    const id = table.idFor(authoredW, authoredH);
    [...seg.querySelectorAll('button')].forEach(b => {
      b.classList.toggle('on', b.dataset.size === id);
      // Kept enabled deliberately: a disabled control is low-contrast and shows
      // no explanation on touch. Tapping one says why instead.
      b.setAttribute('aria-pressed', String(b.dataset.size === id));
    });
    if (note) {
      const size = Math.round(authoredW) + ' \u00d7 ' + Math.round(authoredH);
      if (id === 'custom') {
        // Drawings made before Pad had presets are a custom size. Say so rather
        // than show no selection and let it look broken.
        note.textContent = size + ' \u00b7 custom size';
      } else if (locked()) {
        note.textContent = size + ' \u00b7 locked once you start drawing';
      } else {
        note.textContent = size;
      }
    }
    requestAnimationFrame(positionSlider);
  }

  seg.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    const preset = table.byId(b.dataset.size);
    if (!preset) return;
    if (locked()) {
      if (typeof showToast === 'function') {
        showToast('Canvas is locked once you have drawn — clear all to change it');
      }
      sync();
      return;
    }
    // establishEditorCanvas + layoutEditorCanvas is the whole sequence — it is
    // exactly what loadSkribl does. No redraw is needed precisely BECAUSE the
    // lock above guarantees the canvas is empty; if that rule is ever relaxed,
    // a repaint has to be added here or strokes will vanish on resize.
    establishEditorCanvas(preset.w, preset.h);
    layoutEditorCanvas();
    sync();
    if (typeof scheduleAutosave === 'function') scheduleAutosave();
  });

  window.syncCanvasSeg = sync;
  sync();
})();

/* Your Skribls — shared with Flip via lib/postedui.js. */
window._skriblPostedUI = window.SkriblPostedUI ? window.SkriblPostedUI.init() : null;
{
  const item = document.getElementById('postedItem');
  if (item) item.addEventListener('click', () => {
    if (typeof closeMenu === 'function') closeMenu();
    else {
      const o = document.getElementById('menuOverlay');
      if (o) { o.classList.remove('open'); o.hidden = true; }
    }
    if (window._skriblPostedUI) window._skriblPostedUI.open();
  });
}

// Report sheet — shared via lib/report.js so the two editors collect the same
// context. Null-safe: without the lib the menu item simply does nothing.
if (window.SkriblReport) window.SkriblReport.init();

// Tips toggle — the SAME stored setting as Flip's, surfaced here too.
(function(){
  const seg = document.getElementById('hintSeg');
  if (!seg || !window.SkriblHints) return;
  function sync() {
    const on = window.SkriblHints.isEnabled();
    seg.querySelectorAll('button').forEach(b =>
      b.classList.toggle('on', (b.dataset.hints === 'on') === on));
    if (window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  }
  seg.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    // Turning them back ON also forgets what has been seen, or the switch
    // does nothing for anyone who already dismissed every hint.
    if (b.dataset.hints === 'on') window.SkriblHints.reset();
    else window.SkriblHints.setEnabled(false);
    sync();
  });
  if (window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  window._skriblSyncHintToggle = sync;
  sync();
})();

// Theme switch — the SAME stored setting as Flip's. lib/theme.js owns the key
// and the <html> attribute; this is only the control that drives it.
(function(){
  const seg = document.getElementById('themeSeg');
  if (!seg || !window.SkriblTheme) return;
  function sync() {
    const mode = window.SkriblTheme.get();
    seg.querySelectorAll('button').forEach(b =>
      b.classList.toggle('on', b.dataset.theme === mode));
    if (window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  }
  seg.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b || !b.dataset.theme) return;
    window.SkriblTheme.set(b.dataset.theme);
  });
  // Driven by the lib rather than by the click, so a change made in another
  // tab moves this switch too — the setting is per browser, not per page.
  window.SkriblTheme.onChange(sync);
  if (window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  window._skriblSyncThemeToggle = sync;
  sync();
})();

// Styled tooltips. Native `title` cannot be rounded; this swaps them out.
if (window.SkriblTooltip) window.SkriblTooltip.init();

/* ===================================================================
   v215 — media dot, paint target, inspector, seg pills, Flip guard
   =================================================================== */


// Paint target. Swaps WHICH grid is shown, not what the sheet shows: size,
// opacity and brush stay put underneath and never move.
(function initPaintTarget() {
  const seg = document.getElementById('paintTargetSeg');
  if (!seg) return;
  seg.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-target]');
    if (!btn) return;
    const target = btn.dataset.target;
    seg.querySelectorAll('button').forEach(b => {
      const on = b === btn;
      b.classList.toggle('active', !!on);
      b.setAttribute('aria-pressed', String(!!on));
    });
    ['colorGroup', 'bgGroup'].forEach(id => {
      const g = document.getElementById(id);
      if (g) g.hidden = g.dataset.target !== target;
    });
    // Recent is a list of PEN colours. It sits between the two swatch grids as a
    // sibling, so it stayed on screen in Background mode and read as "recent
    // backgrounds" — which is what it was reported as. It belongs to the pen.
    const recent = document.getElementById('recentRow');
    if (recent) {
      // Read the real state rather than inventing a flag: lib/recentcolors.js
      // owns this row's visibility, and a parallel copy would drift from it.
      const swatches = document.getElementById('recentColors');
      const has = !!(swatches && swatches.children.length);
      recent.hidden = (target !== 'stroke') || !has;
    }
    if (window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  });
  if (window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
})();

// The inspector describes the ACTIVE MODE only. Absent, not greyed: a greyed
// control still costs a glance and still invites a tap, and showing colour or
// brush while the eraser is selected is a small lie about what the tool does.
function syncInspectorToTool(nextTool) {
  const eraser = nextTool === 'eraser';
  ['colorGroup', 'bgGroup', 'paintTargetSeg', 'brushRow', 'opacityRow'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (id === 'colorGroup')      el.hidden = eraser || el.dataset.target !== currentPaintTarget();
    else if (id === 'bgGroup')    el.hidden = eraser || el.dataset.target !== currentPaintTarget();
    else                          el.hidden = eraser;
  });
  const er = document.getElementById('eraserRow');
  if (er) er.hidden = !eraser;
}
function currentPaintTarget() {
  const on = document.querySelector('#paintTargetSeg button.active');
  return on ? on.dataset.target : 'stroke';
}

// The draw drawer's segmented rows now carry a pill on BOTH surfaces. track()
// rather than a one-shot place(): the drawer ships `hidden`, so at init the
// buttons have no layout and any single call bails, leaving the pill at
// opacity 0 — the exact bug lib/segslider.js was written for.
(function trackDrawerSegs() {
  ['smoothSeg', 'brushSeg', 'shapeSeg', 'pressureSeg', 'eraserSeg'].forEach(id => {
    const seg = document.getElementById(id);
    if (seg && window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  });
})();

// Media drawer rows route to the existing photo/music drawers. A router, so
// nothing about their internals changes.

// The Pad leave guard (Flip navigation) moved to editor_draft.js with the
// rest of the draft-durability machinery — it is now keyed to whether the
// current revision is durable, not to whether media is attached.


/* Dismiss the shape picker on a tap outside it. Closing on a PICK is decided
   in the pick handler (editor_shapes.js) rather than here, because the decision
   now depends on whether the chosen kind has a knob to offer -- which is the
   picker's business, not the dismisser's. */
(function shapePopDismiss() {
  const pop = document.getElementById('shapePop');
  if (!pop) return;
  document.addEventListener('click', (e) => {
    if (pop.hidden) return;
    if (e.target.closest('#shapePop') || e.target.closest('#shapeToolBtn')) return;
    pop.hidden = true;
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !pop.hidden) { pop.hidden = true; }
  });
})();

/* ---------- boot marker: the last statement in this file --------------------
   Its only job is to prove that this file reached its end. flip.js and app.js
   are classic scripts of several thousand lines, and a throw ANYWHERE at top
   level silently abandons every line after it — the page keeps rendering, the
   markup is all there, and some arbitrary suffix of the behaviour is simply
   missing. That failure mode cost four separate debugging rounds in one
   session, every one of them a `let` declared below a function that setTool()
   reaches during init, and every one of them presenting as several unrelated
   features breaking at once.

   verify_boot.py asserts this flag. It is the cheapest possible check for the
   most expensive possible bug, and unlike a page-error listener it also catches
   the case where something swallowed the throw. Keep it last. */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { pad: true });
