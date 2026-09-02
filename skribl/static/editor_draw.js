// Editor-only: the whole stroke CAPTURE path.
//
// startDraw / continueDraw / snapStrokeToFinal / commitActiveStroke /
// commitStrokeWithMirrors / endDraw, and the canvas + window listeners that
// drive them. The fourth carve, after editor_music.js, editor_photo.js and
// editor_shapes.js — and the first one done BEFORE the feature that needed the
// room rather than after it. The shape tool proved the other order costs a
// ratchet raise and a second pass.
//
// WHY THIS BELONGS OUT OF app.js. The player loads app.js and replays a
// finished drawing; it never captures one. Every line here ran only in the
// editor and the player carried all of it, which is where roughly 5 KB of the
// v213 ratchet raises came from.
//
// WHAT STAYS BEHIND, and this is the line that matters: drawLine(), drawDot(),
// getPos(), pressureSize(), _eraserSize() and _brushWidth() are all still in
// app.js, because replayTimelineToCanvas hands drawLine/drawDot to the PLAYER
// as its painters. Only the code that turns a gesture into points moved. The
// rule from editor_music.js applies — a binding declared here does not exist
// on the player at all — so the LISTENERS moved with the functions: a
// `canvas.addEventListener('mousedown', startDraw)` left behind in app.js
// would throw a ReferenceError on every player load and take the rest of the
// file down with it.
//
// commitActiveStroke() is reached from app.js's record-stop path, so it is
// published on window and that ONE call site is guarded. Unreachable-today is
// not the same as safe.
//
// LOAD ORDER: classic script reading globals app.js declares (canvas, ctx,
// tool, size, color, strokes, strokeGroups, currentStroke, recording, drawing,
// drawLine, drawDot, getPos, pressureSize). After app.js, and out of
// skribl_player.html.


// ---- Select tool ------------------------------------------------------------
// Two phases in one tool. With nothing selected, a drag draws a marquee and
// picks the stroke groups it touches. With a selection live, a drag MOVES it.
// Escape clears. Done/undo go through the ordinary history stack rather than an
// inverse-offset of their own: makeHistoryState() is pushed before the first
// move commits, so Ctrl+Z restores the pre-move coordinates with machinery that
// already existed and is already pinned.
//
// The preview uses the same canvas-copy trick as the shape tool, for the same
// reason: this canvas paints incrementally and there is nothing to repaint from.
let selGroups = [], selOrigin = null, selBase = null;
let selMarqueeFrom = null, selMoveFrom = null, selDx = 0, selDy = 0, selPushed = false;

function selCaptureBase() {
  const sz = getCanvasLogicalSize();
  const c = document.createElement('canvas');
  c.width = sz.width; c.height = sz.height;
  c.getContext('2d').drawImage(canvas, 0, 0, sz.width, sz.height);
  selBase = c;
}

function selRestoreBase() {
  if (!selBase) return;
  const sz = getCanvasLogicalSize();
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, sz.width, sz.height);
  ctx.drawImage(selBase, 0, 0, sz.width, sz.height);
  ctx.restore();
}

function selOutline(r, dashed) {
  if (!r) return;
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.setLineDash(dashed ? [6, 5] : []);
  ctx.strokeStyle = 'rgba(124,92,255,0.95)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(r.x, r.y, r.w, r.h);
  ctx.restore();
}

// Repaint the whole drawing from `strokes`, then outline the selection. Needed
// because moving points invalidates the cached bitmap the preview draws over —
// the copy still shows the artwork where it USED to be.
function selRepaint() {
  clearAndRestore(() => {
    // THROUGH THE COMPOSITOR, not the raw painters. This was the one repaint in
    // the editor still passing drawDot/drawLine straight to the replay loop, so
    // every see-through stroke was re-painted segment by segment and its own
    // overlaps stacked back into beads — the exact thing stroke layers exists to
    // prevent, undone by a repaint. Live drawing looked right because it takes
    // the wet path; the beads appeared the moment anything called this.
    //
    // And setTool() calls SkriblSelectTool.clear() on EVERY tool change, so
    // simply picking the eraser re-beaded the whole canvas without erasing
    // anything. Preview, playback and all three export paths already route
    // through makeStrokeCompositor; this is the one that did not.
    const tl = buildPlaybackTimeline();
    if (strokeLayersOn()) {
      const comp = makeStrokeCompositor(ctx, canvas);
      replayTimelineToCanvas(tl, 0, Infinity, comp.dotFn, comp.lineFn);
      comp.finish();
      comp.present();
    } else {
      replayTimelineToCanvas(tl, 0, Infinity, drawDot, drawLine);
    }
    selCaptureBase();
    const b = window.SkriblSelect && SkriblSelect.bounds(strokes, selOrigin);
    if (b) selOutline({ x: b.x - 6, y: b.y - 6, w: b.w + 12, h: b.h + 12 }, true);
  });
}

function selClear() {
  // Nothing selected means nothing to erase from the canvas, so a full repaint
  // is pure cost — and setTool() calls this on every tool change. Pad no longer
  // has a Select tool at all, so without this guard the common case was
  // repainting the entire drawing to remove a marquee that was never there.
  const had = selGroups.length > 0 || selOrigin;
  selGroups = []; selOrigin = null; selDx = selDy = 0; selPushed = false;
  if (had) selRepaint();
}

window.SkriblSelectTool = {
  hasSelection: () => selGroups.length > 0,
  clear: selClear,
  begin(pos) {
    selCaptureBase();
    const b = selOrigin && window.SkriblSelect && SkriblSelect.bounds(strokes, selOrigin);
    // Inside the current selection: start a move. Anywhere else: start a new
    // marquee, which also DISCARDS the old selection — the alternative is a
    // tool where a stray tap silently keeps a selection the user has visually
    // moved on from.
    if (b && pos.x >= b.x - 8 && pos.x <= b.x + b.w + 8 &&
             pos.y >= b.y - 8 && pos.y <= b.y + b.h + 8) {
      selMoveFrom = { x: pos.x, y: pos.y };
      selMarqueeFrom = null;
    } else {
      selMarqueeFrom = { x: pos.x, y: pos.y };
      selMoveFrom = null;
      selGroups = []; selOrigin = null; selDx = selDy = 0;
    }
  },
  drag(pos) {
    if (!window.SkriblSelect) return;
    if (selMarqueeFrom) {
      selRestoreBase();
      selOutline(SkriblSelect.rect(selMarqueeFrom, pos), true);
      return;
    }
    if (selMoveFrom && selOrigin) {
      // One history entry per selection, pushed on the FIRST move rather than
      // on every drag frame — otherwise a single reposition fills the 30-deep
      // undo stack and evicts everything the user actually wants back.
      if (!selPushed) {
        // The same three lines startDraw uses, so a moved selection undoes
        // through exactly the machinery a stroke does — no second history path.
        //
        // BUT the selected points must be REPLACED, not mutated. makeHistoryState
        // does `strokes.slice()`, which copies the ARRAY and not the point
        // objects — every stroke lives in the snapshot and in `strokes` at the
        // same address. Editing x/y in place therefore edited the undo state
        // too, and Ctrl+Z restored the moved position: a silent no-op that
        // looked like undo being broken rather than the move being wrong.
        //
        // Every other writer here APPENDS points, so nothing had ever mutated
        // an existing one and the aliasing had never mattered. Cloning just the
        // selected points before the snapshot keeps the fix local to the one
        // path that mutates.
        // ORDER IS LOAD-BEARING: snapshot FIRST, so the snapshot's array holds
        // the ORIGINAL point objects, and only then swap `strokes` over to
        // clones that the move is free to mutate. Cloning first and then
        // snapshotting captures the clones — the same aliasing, one step later,
        // and undo stays a no-op.
        undoStack.push(makeHistoryState());
        SkriblSelect.spans(strokeGroups, selGroups).forEach(([a, b]) => {
          for (let i = a; i < b && i < strokes.length; i++) {
            strokes[i] = Object.assign({}, strokes[i]);
          }
        });
        // Re-snapshot AFTER the clone: selOrigin holds indices, but applyOffset
        // writes through `strokes[i]`, so it must see the new objects.
        selOrigin = SkriblSelect.captureOrigin(
          strokes, SkriblSelect.spans(strokeGroups, selGroups));
        if (undoStack.length > 30) undoStack.shift();
        undoBtn.disabled = false;
        selPushed = true;
      }
      selDx = pos.x - selMoveFrom.x;
      selDy = pos.y - selMoveFrom.y;
      SkriblSelect.applyOffset(strokes, selOrigin, selDx, selDy);
      selRepaint();
    }
  },
  end(pos) {
    if (!window.SkriblSelect) return;
    if (selMarqueeFrom) {
      const r = SkriblSelect.rect(selMarqueeFrom, pos);
      selGroups = SkriblSelect.groupsIn(strokes, strokeGroups, r);
      selOrigin = selGroups.length
        ? SkriblSelect.captureOrigin(strokes, SkriblSelect.spans(strokeGroups, selGroups))
        : null;
      selMarqueeFrom = null;
      selRepaint();
      return;
    }
    if (selMoveFrom) {
      // Re-snapshot at the new position so a SECOND drag starts from where the
      // artwork now is. Without this the origin still describes the pre-move
      // coordinates and the next drag snaps the selection back before moving.
      selMoveFrom = null;
      selOrigin = selGroups.length
        ? SkriblSelect.captureOrigin(strokes, SkriblSelect.spans(strokeGroups, selGroups))
        : null;
      selDx = selDy = 0; selPushed = false;
    }
  },
};

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && selGroups.length) { selClear(); }
});

function startDraw(e) {
  // Playback surface, never a drawing one. Bound at load, before player-mode
  // is set, so the guard belongs here. See verify_player_isolation.py.
  if (document.body.classList.contains('player-mode')) return;
  // Space held = grab-pan mode; never a stroke (v211).
  if (window._skriblSpaceHeld && window._skriblSpaceHeld()) return;
  // Two (or more) fingers ON THE CANVAS → magnify/pan gesture, never a stroke.
  // Handled before preventDefault/anything else so it can cleanly abort a
  // nascent 1-finger stroke that the first finger just began. Guarded on
  // ZoomView so the player (no zoom) behaves exactly as before.
  //
  // targetTouches, NOT touches. `touches` is every contact on the SCREEN,
  // including ones that never came near the canvas — a thumb resting on the
  // header while holding the phone, a palm on an iPad. Reading it meant one
  // resting finger anywhere on the page turned every drawing gesture into a
  // pinch: measured on a 430px viewport, the drag captured ZERO stroke points
  // and silently switched the magnifier ON. The user drew and nothing appeared.
  // `targetTouches` is the subset that started on this element, which is what
  // "two fingers on the canvas" always meant.
  const _canvasTouches = e.targetTouches || e.touches;
  if (ZoomView && _canvasTouches && _canvasTouches.length >= 2) { beginPinch(e); return; }
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
  // The shape picker is tool OPTIONS, not a dialog: the press that starts
  // your shape shoves it aside, and the SAME gesture draws — not close-on-
  // release (the click dismisser fires after the drag is over, so the card
  // stood over the canvas the whole time; owner: "how can we get that menu
  // to go away while I'm trying to draw the shape?"), and not tap-to-close,
  // tap-again-to-draw. Hide, don't return. UNLESS the user dragged it
  // somewhere (data-moved, set by lib/popdrag.js): a pop they positioned is
  // a palette they want to keep while they draw.
  {
    const _shapePop = document.getElementById('shapePop');
    if (_shapePop && !_shapePop.hidden && !_shapePop.dataset.moved) _shapePop.hidden = true;
  }
  // Eyedropper: this press opens the magnifying loupe — drag to aim, release
  // picks (lib/eyedropper.js). Allowed even on a locked canvas — it only
  // reads. The one-shot tap sample stays as the fallback if the loupe
  // declines (created without its wiring).
  if (pickingColor) {
    if (_eyedropper && _eyedropper.beginPick && _eyedropper.beginPick(e)) return;
    const p = getPos(e); sampleColorAt(p.x, p.y); return;
  }
  // Photo reposition mode: this drag moves the background, never the drawing.
  // Returns before the lock check and the undo push, so it can't start a stroke,
  // fire the lock toast, or create an undo entry. Ignored during recording so a
  // take is never blocked.
  if (repositioning && !recording) { beginPhotoDrag(e); return; }
  // Tapping the canvas while a drawer is open just dismisses it (no stray dot).
  // After the eyedropper/reposition checks so those keep working.
  if (['drawPanel', 'musicPanel', 'photoPanel']
      .some(i => { const p = document.getElementById(i); return p && !p.hidden; })) {
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
  // A stroke's FIRST point has no previous point, so the taper must start from
  // zero speed — i.e. full width. Carrying _brushLastPt over from the previous
  // stroke would taper the start of each new line by however far the pointer
  // happened to travel between strokes, which on a long reposition is the whole
  // canvas and draws the first segment hairline-thin.
  _brushLastPt = null;
  const drawSize = _brushWidth(pressureSize(e, _eraserSize(size, erase), erase), pos, erase);
  _brushLastPt = { x: pos.x, y: pos.y };
  const point = { x: pos.x, y: pos.y, color: drawColor, size: drawSize, t, start: true, erase };
  currentStroke.push(point);
  // The shape tool lives in editor_shapes.js — see the note there. Guarded by
  // the hook's existence, not by `tool` alone: the player loads this file and
  // must not depend on a binding that only the editor declares.
  if (tool === 'select' && window.SkriblSelectTool) {
    window.SkriblSelectTool.begin(pos);
    currentStroke = [];
    return;
  }
  if (tool === 'shape' && window.SkriblShapeTool) {
    window.SkriblShapeTool.begin(pos, t);
    currentStroke = [];
    hasContent = true;
    updateClearVisibility();
    updateEmptyHint();
    return;
  }
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

let _constrainActive = false;   // Shift held during the last move of this stroke
function continueDraw(e) {
  e.preventDefault();
  if (pinching) return;
  if (!drawing) return;
  const pos = getPos(e);
  lastRawPos = pos;
  if (tool === 'select') {
    if (window.SkriblSelectTool) window.SkriblSelectTool.drag(pos);
    return;
  }
  if (tool === 'shape') { _constrainActive = !!(e && e.shiftKey);
    if (window.SkriblShapeTool) window.SkriblShapeTool.preview(pos, _constrainActive);
    return; }
  // Stabilizer: ease the drawn point toward the raw position. At smoothingAlpha
  // === 1 this is a no-op (dp === pos), so "Off" is byte-identical to before.
  // The smoothed point is what gets stored, so replay reproduces it exactly.
  if (!smoothPt) smoothPt = { x: lastPos.x, y: lastPos.y };
  smoothPt = {
    x: smoothPt.x + (pos.x - smoothPt.x) * smoothingAlpha,
    y: smoothPt.y + (pos.y - smoothPt.y) * smoothingAlpha
  };
  let dp = smoothingAlpha >= 1 ? pos : smoothPt;
  // Shift-to-constrain (lib/constrain.js). Anchored at the stroke's FIRST
  // point, so every captured point is collinear with it and the line is
  // genuinely straight; see the note in that file about why per-segment
  // snapping staircases. Applied AFTER the stabilizer so the two do not fight.
  _constrainActive = !!(e && e.shiftKey);
  if (_constrainActive && typeof SkriblConstrain !== 'undefined' && currentStroke.length) {
    dp = SkriblConstrain.apply(currentStroke[0], dp, true);
  }
  const t = recording ? Date.now() - startTime : 0;
  const erase = tool === 'eraser';
  const drawColor = erase ? bgColor : penColorFor(color);
  const drawSize = _brushWidth(pressureSize(e, _eraserSize(size, erase), erase), dp, erase);
  _brushLastPt = { x: dp.x, y: dp.y };
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
  // Settle to the axis, not to the raw pointer: an unconstrained final point
  // would kink the line off the axis at the very end of every Shift stroke.
  const _final = (_constrainActive && typeof SkriblConstrain !== 'undefined' && currentStroke.length)
    ? SkriblConstrain.apply(currentStroke[0], lastRawPos, true)
    : lastRawPos;
  const dx = _final.x - lastPos.x, dy = _final.y - lastPos.y;
  if (dx * dx + dy * dy < 0.25) return;   // within ~0.5px: nothing to add
  const t = recording ? Date.now() - startTime : 0;
  const erase = tool === 'eraser';
  const drawColor = erase ? bgColor : penColorFor(color);
  // Carry the stroke's final captured width. This read the nominal slider value,
  // which was invisible at constant width but with pressure would snap the last
  // point back to full thickness — a blob on the end of every tapered stroke.
  const _lastPt = currentStroke[currentStroke.length - 1];
  const drawSize = (_lastPt && typeof _lastPt.size === 'number') ? _lastPt.size : (_eraserSize(size, erase));
  currentStroke.push({ x: _final.x, y: _final.y, color: drawColor, size: drawSize, t, erase });
  if (_slActive) {
    drawLineOn(_wetCtx, lastPos.x, lastPos.y, lastRawPos.x, lastRawPos.y, solidStrokeColor(drawColor), drawSize);
    presentWet();
  } else {
    drawLine(lastPos.x, lastPos.y, lastRawPos.x, lastRawPos.y, drawColor, drawSize, erase);
  }
  lastPos = lastRawPos;
}

let _mirrorPainting = false;   // re-entry guard for the mirrored paint below

// Commit a finished stroke, plus any mirrored copies (lib/mirror.js).
//
// Each reflection is its own GROUP, never appended to the original. A single
// stroke holding both halves would draw a connecting line straight across the
// canvas the moment the replay joins consecutive points — the same class of
// bug as the stray line, except baked into the payload instead of being a
// live-draw artifact.
//
// The axis is the CANVAS centre, so it is stable across strokes; a mirror
// anchored to wherever the stroke began drifts and cannot be aimed.
function commitStrokeWithMirrors() {
  if (!recording || currentStroke.length === 0) { currentStroke = []; return; }
  strokes = strokes.concat(currentStroke);
  strokeGroups.push(currentStroke.length);
  if (window.SkriblMirror && SkriblMirror.active()) {
    const { width: cw, height: ch } = getCanvasLogicalSize();
    const n = SkriblMirror.count();
    for (let r = 0; r < n; r++) {
      const copy = currentStroke.map(pt => {
        const m = SkriblMirror.reflect(pt, cw, ch)[r];
        return Object.assign({}, pt, { x: m.x, y: m.y });
      });
      strokes = strokes.concat(copy);
      strokeGroups.push(copy.length);
    }
  }
  currentStroke = [];
}

function endDraw() {
  if (!drawing) return;
  if (tool === 'select') {
    if (window.SkriblSelectTool) window.SkriblSelectTool.end(lastRawPos);
    drawing = false;
    document.body.classList.remove('stroking');
    currentStroke = [];
    return;
  }
  if (tool === 'shape') {
    if (window.SkriblShapeTool) window.SkriblShapeTool.commit(lastRawPos, _constrainActive);
    drawing = false;
    document.body.classList.remove('stroking');
    commitStrokeWithMirrors();
    return;
  }
  snapStrokeToFinal();
  drawing = false;
  document.body.classList.remove('stroking');
  _slActive = false;
  commitStrokeWithMirrors();
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
/* NO mouseleave -> endDraw.
 *
 * It ended the stroke the moment the cursor crossed the canvas edge, so
 * sweeping a line out past the border and back produced two strokes with a gap
 * — and a stroke that ends where you did not lift the button is a stroke you
 * did not draw. Touch never had this, because there is no mouseleave, which is
 * why the same gesture behaved differently on a phone.
 *
 * Continuing outside is the drawing-app convention: the line follows the
 * pointer, the canvas clips what falls outside, and coming back resumes the
 * same stroke. The window handlers below still commit on mouseup anywhere and
 * on losing focus, so a stroke can never be left painted but unrecorded. */
window.addEventListener('mousemove', (e) => {
  if (!drawing) return;
  // DO NOT DOUBLE-CAPTURE. This listener exists only so a stroke keeps
  // following the pointer once it leaves the canvas; over the canvas the
  // element's own mousemove has already handled this very event, and it then
  // BUBBLES here. Measured before this guard: 21 mousemove events produced 41
  // captured points. Two costs, neither visible as a wrong pixel — the replay
  // array and the posted payload carry twice the points they need, and
  // continueDraw()'s stabiliser lerps TWICE per event toward the same position,
  // so smoothing converged at one rate over the canvas and half that outside
  // it. The slider therefore meant two different things depending on where the
  // pointer was. `composedPath` covers a canvas inside a shadow root; the
  // target check alone is enough today.
  if (e.target === canvas) return;
  continueDraw(e);
});
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
window.addEventListener('mouseup', () => { if (drawing) endDraw(); });
window.addEventListener('blur', () => { if (drawing) commitActiveStroke(); });

// Published for app.js's record-stop path — the only caller outside this file.
window.SkriblCapture = { commitActiveStroke: commitActiveStroke };
