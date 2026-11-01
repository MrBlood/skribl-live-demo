// Editor-only: the Text tool's Pad side. lib/textwrite.js is the tool (the
// typing sheet, the lettering, the words as strokes, writing them in time),
// shared with Flip; this hands it what only the Pad knows: its canvas, its
// pen, its take clock and its Undo.
//
// WHERE IT STARTS. Text is the fifth kind in Shape's picker (editor_shapes.js).
// With it chosen, a press on the canvas says where the words go and opens
// the sheet (editor_draw.js asks window.SkriblTextTool before anything is
// drawn or a take is armed): nothing is ink, and nothing is recorded, until
// Write it.
//
// WHAT WRITING IS, HERE. The same steps a pen stroke takes: the take arms on
// a blank canvas as the pen's first stroke arms it, one history state is
// pushed so one Undo takes the whole line back, and each stroke is kept by
// commitStrokeWithMirrors -- told to leave Mirror out, because mirrored words
// read backwards. Each point's t is the take clock's when the words began
// plus the time the plan gives it, so the replay writes them at the pace
// they were written. If the words are finished early (any press or key while
// they write), the clock is moved on by what was left, so the next line comes
// after them and the take's times keep running forward.
//
// LOAD ORDER: classic script reading globals app.js and editor_draw.js
// declare (canvas, size, color, recording, startTime, undoStack, drawLine,
// drawDot, penColorFor, commitStrokeWithMirrors). After editor_shapes.js,
// whose shapeKind it reads; out of skribl_player.html.
(function () {
  'use strict';
  if (!window.SkriblText || window.SKRIBL_LETTERS === true) return;

  window.SkriblText.attach({
    canvas: canvas,
    logical: getCanvasLogicalSize,
    pen: function () { return { color: penColorFor(color), size: size }; },
    begin: function () {
      // As startDraw does for a pen: a blank canvas starts its take. A
      // finished take carries on, as Keep drawing does (app.js addTakePill):
      // Write it is as deliberate as that press. One history state for the
      // whole line.
      if (playing) stopPlayback();
      if (finishedRecording && !recording) beginRecording(strokes.length > 0);
      else if (!recording && !hasContent) beginRecording(false);
      undoStack.push(makeHistoryState());
      if (undoStack.length > 30) undoStack.shift();
      undoBtn.disabled = false;
      redoStack = [];
      redoBtn.disabled = true;
      hasContent = true;
      updateClearVisibility();
      updateEmptyHint();
      return recording ? Date.now() - startTime : 0;
    },
    draw: function (pts, from, to) {
      if (from === 0) drawDot(pts[0].x, pts[0].y, pts[0].color, pts[0].size, false);
      for (let i = Math.max(1, from); i <= to; i++) {
        drawLine(pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y, pts[i].color, pts[i].size, false);
      }
    },
    stroke: function (pts, t0) {
      currentStroke = pts.map((p, i) => ({
        x: p.x, y: p.y, color: p.color, size: p.size,
        t: recording ? t0 + p.t : 0, start: i === 0, erase: false
      }));
      commitStrokeWithMirrors(true);
    },
    end: function () {
      if (typeof showTakeHint === 'function') showTakeHint();   // the first take says so, once (editor_bar.js)
      if (typeof scheduleAutosave === 'function') scheduleAutosave();
    },
    skip: function (ms) { if (recording) startTime -= ms; },
    say: function (words) { if (typeof showToast === 'function') showToast(words, null); },
  });

  // The badge by a mouse pointer says what a press makes (app.js
  // _SHAPE_GLYPH): for Text, a T. Added here, so the player's copy of app.js
  // carries nothing for a tool it never has.
  if (typeof _SHAPE_GLYPH !== 'undefined') _SHAPE_GLYPH.text = '<path d="M4 4.5h10M9 4.5V15"/>';

  // editor_draw.js asks this before a press draws anything.
  window.SkriblTextTool = {
    wants: function () { return tool === 'shape' && shapeKind === 'text'; },
  };
})();
