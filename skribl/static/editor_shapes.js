// Editor-only: the Shape tool's preview, commit and kind picker.
//
// Carved out of app.js at v213. The helpers below cost 3,191 B in the PLAYER,
// which can never select a shape — the single largest editor-only addition to
// the shared file since v212, bigger than the five before it combined, and the
// raise that left only 1,622 B of headroom to the target.
//
// SAME RULE AS editor_music.js AND editor_photo.js, with one difference worth
// stating. Those files move only STATEMENTS, because the player reaches some
// app.js functions through loadSkribl and a binding declared here would not
// exist there at all. These are functions, and they move because the player
// cannot reach them: `tool` is never 'shape' there. Rather than rely on that
// unreachability, app.js calls through `window.SkriblShapeTool` and checks the
// hook exists — so the player is safe even if some future path does set the
// tool. Unreachable-today is not the same as safe.
//
// LOAD ORDER: classic script reading globals app.js declares (canvas, ctx,
// currentStroke, size, color, recording, startTime, drawLine, penColorFor,
// getCanvasLogicalSize). After app.js, and out of skribl_player.html.

// ---- Shape tool -------------------------------------------------------------
// A shape is generated as ordinary stroke points (lib/shapes.js), so the player
// replays it with the code it already has and no payload field is added.
//
// The PREVIEW is the only awkward part. Both editors paint live and append
// points, so there is nothing to un-draw when the drag resizes the shape.
// Instead the canvas as it stood when the drag began is copied once, and every
// move restores that copy and strokes the current outline over it. One copy per
// drag, not per move — copying per move is what makes this stutter on a phone.
let shapeKind = 'line';
let _shapeAnchor = null, _shapeBase = null, _shapeStartT = 0;

function _shapeCaptureBase() {
  const { width: cw, height: ch } = getCanvasLogicalSize();
  const c = document.createElement('canvas');
  c.width = cw; c.height = ch;
  c.getContext('2d').drawImage(canvas, 0, 0, cw, ch);
  _shapeBase = c;
}

function _shapeRestoreBase() {
  if (!_shapeBase) return;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(_shapeBase, 0, 0, cw, ch);
  ctx.restore();
}

function _shapePreview(pos, square) {
  if (!_shapeAnchor || typeof SkriblShapes === 'undefined') return;
  _shapeRestoreBase();
  const pts = SkriblShapes.points(shapeKind, _shapeAnchor, pos,
    { square: square, sides: shapeSides, radius: shapeRadius });
  if (pts.length < 2) return;
  const erase = false;
  const drawColor = penColorFor(color);
  for (let i = 1; i < pts.length; i++) {
    drawLine(pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y, drawColor, size, erase);
  }
}

// Commit: turn the outline into points and hand them to the normal stroke
// machinery. `t` is spread across the drag's real duration so the shape REPLAYS
// as a drawing rather than appearing all at once — the same reason strokes
// carry per-point timing at all.
function _shapeCommit(pos, square) {
  if (!_shapeAnchor || typeof SkriblShapes === 'undefined') return;
  const pts = SkriblShapes.points(shapeKind, _shapeAnchor, pos,
    { square: square, sides: shapeSides, radius: shapeRadius });
  if (pts.length < 2) { _shapeAnchor = null; _shapeBase = null; return; }
  const drawColor = penColorFor(color);
  const endT = recording ? Date.now() - startTime : 0;
  const span = Math.max(1, endT - _shapeStartT);
  currentStroke = [];
  for (let i = 0; i < pts.length; i++) {
    currentStroke.push({
      x: pts[i].x, y: pts[i].y, color: drawColor, size: size,
      t: _shapeStartT + Math.round(span * (i / (pts.length - 1))),
      start: i === 0, erase: false
    });
  }
  _shapeRestoreBase();
  for (let i = 1; i < pts.length; i++) {
    drawLine(pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y, drawColor, size, false);
  }
  _shapeAnchor = null; _shapeBase = null;
  hasContent = true;
}


// The hook app.js calls. Keeping the surface this small is the point: the
// player carries three guarded call sites, not the implementation.
window.SkriblShapeTool = {
  begin: function (pos, t) {
    _shapeAnchor = { x: pos.x, y: pos.y };
    _shapeStartT = t;
    _shapeCaptureBase();
  },
  preview: function (pos, square) { _shapePreview(pos, square); },
  commit: function (pos, square) { _shapeCommit(pos || _shapeAnchor, square); },
};

// Which shape the Shape tool draws. Picking one also SELECTS the tool: a
// user who taps "Oval" has said what they want, and leaving them on the pen
// with an invisible preference changed is the kind of dead control this
// project keeps finding.
const shapeSeg = document.getElementById('shapeSeg');
if (shapeSeg && window.SkriblShapes) {
  shapeSeg.addEventListener('click', (e) => {
    const b = e.target.closest('[data-shape]');
    if (!b || !shapeSeg.contains(b)) return;
    const kind = b.getAttribute('data-shape');
    if (SkriblShapes.KINDS.indexOf(kind) === -1) return;
    shapeKind = kind;
    shapeSeg.querySelectorAll('[data-shape]').forEach(x => {
      const on = x === b;
      x.classList.toggle('active', on);
      x.setAttribute('aria-pressed', String(on));
    });
    setTool('shape');
    syncShapeKnobs();
    /* CLOSE ON A PICK ONLY WHEN THE PICK LEFT NOTHING TO SET. See the twin of
       this comment in flip.js: closing on every pick hid the knobs the pick
       had just revealed, and Poly had to be chosen twice to reach them. */
    const pop = document.getElementById('shapePop');
    if (pop && !window.SkriblShapes.knobs(kind).length) pop.hidden = true;
  });
  attachSegSlider(shapeSeg);
}

/* The polygon's sides and the corner rounding, shared with Flip through
   lib/shapes.js — including WHICH kinds offer which knob, which is asked of the
   lib rather than restated here. Each row hides rather than greying out: a
   disabled control is still something the eye has to read and dismiss. */
let shapeSides = 5, shapeRadius = 0;

function syncShapeKnobs() {
  const sidesRow = document.getElementById('shapeSidesRow');
  const radiusRow = document.getElementById('shapeRadiusRow');
  if (sidesRow) sidesRow.hidden = !window.SkriblShapes.hasKnob(shapeKind, 'sides');
  if (radiusRow) radiusRow.hidden = !window.SkriblShapes.hasKnob(shapeKind, 'radius');
}

(function shapeKnobs() {
  const sides = document.getElementById('shapeSides');
  const sidesOut = document.getElementById('shapeSidesOut');
  const radius = document.getElementById('shapeRadius');
  const radiusOut = document.getElementById('shapeRadiusOut');
  if (sides) {
    sides.value = String(shapeSides);
    if (sidesOut) sidesOut.textContent = String(shapeSides);
    sides.addEventListener('input', () => {
      shapeSides = Math.max(3, Math.min(12, parseInt(sides.value, 10) || 3));
      if (sidesOut) sidesOut.textContent = String(shapeSides);
    });
  }
  if (radius) {
    radius.value = String(shapeRadius);
    if (radiusOut) radiusOut.textContent = String(shapeRadius);
    radius.addEventListener('input', () => {
      shapeRadius = Math.max(0, parseInt(radius.value, 10) || 0);
      if (radiusOut) radiusOut.textContent = String(shapeRadius);
    });
  }
  syncShapeKnobs();
})();



// Mirror mode (lib/mirror.js). Editor-only, like the shape picker above: the
// player replays reflected strokes as ordinary strokes and has no use for the
// control that produced them.
const mirrorSeg = document.getElementById('mirrorSeg');
if (mirrorSeg && window.SkriblMirror) {
  window.SkriblMirror.create({ seg: mirrorSeg });
}


// Preview speed (Pad only — Flip is fps-driven and already has a Speed row).
// Editor-only by nature: the player has no use for a control that exists so an
// author can review their own take faster.
const speedSeg = document.getElementById('speedSeg');
if (speedSeg && typeof setReplayRate === 'function') {
  const renderSpeed = () => speedSeg.querySelectorAll('[data-rate]').forEach(b => {
    b.classList.toggle('on', parseFloat(b.getAttribute('data-rate')) === replayRate);
  });
  renderSpeed();
  speedSeg.addEventListener('click', (e) => {
    const b = e.target.closest('[data-rate]');
    if (!b || !speedSeg.contains(b)) return;
    setReplayRate(b.getAttribute('data-rate'));
    renderSpeed();
  });
}
