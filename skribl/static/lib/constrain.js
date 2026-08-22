/* Shift-to-constrain — snap a stroke to the nearest axis, shared by both editors.
 *
 * Holding Shift while drawing pins every point to one of eight directions from
 * where the stroke STARTED: horizontal, vertical, or 45 degrees.
 *
 * ANCHORED AT THE STROKE START, not at the previous point. Snapping each
 * segment against its predecessor is the obvious version and it is wrong: every
 * point gets its own tiny axis, the line wanders in a staircase, and the result
 * is neither straight nor what the user asked for. Anchoring at the start makes
 * every captured point collinear with the anchor, so the drawn path IS a
 * straight line without anything having to be un-drawn — which matters here,
 * because both editors paint live and append points as they go. There is no
 * provisional stroke to erase and redraw.
 *
 * Backtracking retraces the same ray rather than reversing direction, which is
 * the conventional behaviour and falls out of the same rule.
 *
 * Length is preserved along the snapped direction rather than orthogonally
 * projected: dragging out at 40 degrees and snapping to 45 keeps the distance
 * you dragged, so the line does not shrink as it locks.
 *
 * No key listener: `shiftKey` rides on mouse, pointer AND keyboard events, so
 * each surface reads it off the move event it already handles. Touch has no
 * Shift, and that is fine — there is no key to hold on a phone.
 */
(function () {
  'use strict';

  var STEP = Math.PI / 4;   // eight directions

  /* snap(ax, ay, x, y) -> {x, y} on the nearest axis through the anchor. */
  function snap(ax, ay, x, y) {
    var dx = x - ax, dy = y - ay;
    var len = Math.sqrt(dx * dx + dy * dy);
    if (!(len > 0)) return { x: x, y: y };
    var a = Math.round(Math.atan2(dy, dx) / STEP) * STEP;
    return { x: ax + Math.cos(a) * len, y: ay + Math.sin(a) * len };
  }

  /* apply(anchor, pos, active) — convenience for the call sites: returns `pos`
   * untouched when the modifier is not held or there is no anchor yet, so a
   * caller can wrap unconditionally.
   */
  function apply(anchor, pos, active) {
    if (!active || !anchor) return pos;
    return snap(anchor.x, anchor.y, pos.x, pos.y);
  }

  var api = { STEP: STEP, snap: snap, apply: apply };
  if (typeof window !== 'undefined') window.SkriblConstrain = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
