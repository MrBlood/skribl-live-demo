/* Pinch contact tracking — the two editors only, never the player.
 *
 * SPLIT OUT OF lib/eventpoint.js DELIBERATELY. The player loads eventpoint.js
 * because its scrub track needs at(); it does not load this, because it has no
 * ZoomView and every pinch path in app.js returns before reaching these. That
 * was worth doing rather than shipping one convenient file: measured, these two
 * functions are ~480 B of stripped JavaScript the player could never execute,
 * against a payload whose remaining headroom is in the hundreds of bytes.
 *
 * Callers must stay guarded. app.js references SkriblPinch inside beginPinch,
 * _pinchMove and _pinchEnd, all three of which bail on `!ZoomView` or
 * `!pinching` before touching it — which is exactly why the split is safe. If a
 * future change reaches these before those guards, the player throws.
 */
(function () {
  'use strict';

  /* The two contacts of a pinch, found by identifier rather than by slot.
   * Returns null once either has lifted.
   *
   * A pinch handler bound to `window` reads the screen-wide list, so a third
   * contact — a resting thumb — could take a slot and the gesture would be
   * computed from a pair that includes a finger standing still, halving the
   * apparent zoom. Ending on "fewer than two contacts on screen" has the mirror
   * problem: one of the pinch's own fingers lifts, an unrelated one keeps the
   * count at two, and the gesture stays live steered by a pair that no longer
   * exists.
   */
  function pinchPair(e, ids) {
    if (!ids || !e || !e.touches) return null;
    var a = null, b = null;
    for (var i = 0; i < e.touches.length; i++) {
      var t = e.touches[i];
      if (t.identifier === ids[0]) a = t;
      else if (t.identifier === ids[1]) b = t;
    }
    return (a && b) ? [a, b] : null;
  }

  /* The contacts that started on this element, for deciding whether a gesture
   * is a pinch. Two fingers ON THE CANVAS is a pinch; one on the canvas plus a
   * thumb resting on the header is a stroke. */
  function ownTouches(e) {
    if (!e) return null;
    if (e.targetTouches && e.targetTouches.length >= 2) return e.targetTouches;
    return e.touches || null;
  }

  var api = { pair: pinchPair, own: ownTouches };
  if (typeof window !== 'undefined') window.SkriblPinch = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
