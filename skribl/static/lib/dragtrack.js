/* A horizontal drag on a track: the plumbing, once, for both editors.
 *
 * WHY (SK312-003, v315). The music trim drawer's four drags -- a trim handle,
 * a zoom-track handle, the whole loop window, and panning the zoomed view --
 * were written out in Pad AND in Flip: eight copies of the same mousedown /
 * touchstart / mousemove / touchmove / mouseup / touchend / touchcancel
 * wiring around a few lines of maths each. That wiring is where the bugs were:
 * v214 found the touchcancel missing on every one of them (a cancelled touch
 * left the drag live, so the next unrelated touch moved a trim whose gesture
 * was over) and fixed it eight times. Now the wiring lives here and each
 * editor keeps only its maths.
 *
 * bind(el, begin): on a press on `el`, begin(e) is called. It returns a falsy
 * value to decline the press (no audio yet, the loop too narrow to grab, a
 * press that belongs to a child), or { move(clientX, ev), end() } for the rest
 * of the gesture. begin owns preventDefault/stopPropagation and any class it
 * adds; end() is where it takes them off again. Every way a gesture can finish
 * -- mouseup, touchend, touchcancel -- ends it, and ends it once.
 *
 * Still mouse + touch, not Pointer Events, on purpose: verify_tools' V214a
 * drives these drags with real touch sequences including touchcancel, and a
 * move to pointer events is its own change with its own verification.
 */
(function (global) {
  'use strict';

  function bind(el, begin) {
    if (!el) return;
    function onStart(e) {
      var g = begin(e);
      if (!g) return;
      var ended = false;
      function move(ev) { g.move(global.SkriblEventPoint.at(ev).clientX, ev); }
      function end() {
        if (ended) return;
        ended = true;
        global.removeEventListener('mousemove', move);
        global.removeEventListener('mouseup', end);
        global.removeEventListener('touchmove', move);
        global.removeEventListener('touchend', end);
        global.removeEventListener('touchcancel', end);
        if (g.end) g.end();
      }
      global.addEventListener('mousemove', move);
      global.addEventListener('mouseup', end);
      global.addEventListener('touchmove', move, { passive: false });
      global.addEventListener('touchend', end);
      global.addEventListener('touchcancel', end);
    }
    el.addEventListener('mousedown', onStart);
    el.addEventListener('touchstart', onStart, { passive: false });
  }

  global.SkriblDragTrack = { bind: bind };
})(window);
