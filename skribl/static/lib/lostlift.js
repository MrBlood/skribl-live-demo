/* A stroke whose lift never came — the two editors only, never the player.
 *
 * THE OWNER'S IPHONE, after v325 (checklist P1): "I made several fast strokes
 * and eventually it won't draw one. It might be when I draw fast and it goes
 * offscreen. Sometimes next one draws and then soon fails."
 *
 * A stroke belongs to one pointer: both editors refuse a second pointer while
 * one is drawing, so a palm or a second finger cannot steer or restart it.
 * When the end of a stroke never reaches the page (no pointerup, no
 * pointercancel, no touchend), the editor still believes that finger is down.
 * It refuses the next finger, and only the lift after that clears the state:
 * one stroke lost, then one drawn, then lost again. Driven with real touch
 * input (CDP), both editors did exactly that.
 *
 * THE SCREEN SETTLES IT. The touchstart of a refused finger lists every touch
 * on the glass. If it lists only that finger, the stroke's own finger is gone:
 * the stroke is kept as it stands, and the new finger draws, as its pointerdown
 * asked. A real second finger, or a palm, is a second touch on the glass, so it
 * is refused exactly as before, and two fingers on the canvas are still a
 * pinch. Touch only: a pen or a mouse that is still down cannot leave the glass
 * unannounced the way a finger running off its edge did.
 *
 *   SkriblLostLift.watch(surface, {
 *     owner()    the pointerId whose stroke is in progress, or null
 *     end()      end that stroke, keeping it
 *     down(e)    the editor's own pointerdown, run again for the new finger
 *   })
 */
(function () {
  'use strict';

  // A pointerdown and the touchstart of the same finger are handled within a
  // moment of each other; a refusal older than this belongs to another press.
  // Read off the page's own clock when each is handled, not the events'
  // timeStamps, which a browser need not measure from the same origin.
  var SAME_PRESS_MS = 250;
  function now() { return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now(); }

  function watch(surface, o) {
    var refused = null, at = 0;
    surface.addEventListener('pointerdown', function (e) {
      var own = o.owner();
      refused = (own != null && e.pointerId !== own && e.pointerType === 'touch') ? e : null;
      at = now();
    }, true);
    surface.addEventListener('touchstart', function (e) {
      var down = refused;
      refused = null;
      if (!down || !e.touches || e.touches.length !== 1) return;
      if (now() - at > SAME_PRESS_MS) return;
      var own = o.owner();
      if (own == null || own === down.pointerId) return;
      o.end();
      o.down(down);
    }, { capture: true, passive: true });
  }

  var api = { watch: watch };
  if (typeof window !== 'undefined') window.SkriblLostLift = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
