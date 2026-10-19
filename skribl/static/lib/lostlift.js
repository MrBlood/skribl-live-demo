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
 * THE SCREEN SETTLES IT. Every touch event lists every touch on the glass.
 * If the stroke's own touch is not among them, its finger is gone: the stroke
 * is kept as it stands, and a refused finger draws, as its pointerdown asked.
 * A real second finger, or a palm, leaves the stroke's own touch on the list,
 * so it is refused exactly as before, and two fingers on the canvas are still
 * a pinch. Touch only: a pen or a mouse that is still down cannot leave the
 * glass unannounced the way a finger running off its edge did.
 *
 * BY ITS OWN TOUCH, NOT BY COUNTING (the owner's iPhone, the v326 re-test:
 * "When I go really fast it stops accepting strokes at a certain point, but
 * after a little wait it will accept them again", and Flip fine). This first
 * asked whether the refused finger was the ONLY touch on the glass. A thumb
 * resting anywhere on the screen made it two, so the Pad refused every finger
 * after the lost lift until the thumb lifted too, and Flip, which ends a
 * stroke on any lift, lost one. The stroke's own touch is remembered from the
 * touchstart that came with its pointerdown; a stroke whose touch was never
 * seen (a press this missed) is judged by the count, as before. And any touch
 * ending anywhere that leaves the stroke's own touch off the list ends the
 * stroke too, so a stuck stroke cannot keep the chrome faded until the next
 * press on the drawing.
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

  // The touch a press made: the changed touch nearest where its pointerdown
  // landed (two fingers can land in one touchstart).
  function touchOf(e, down) {
    var list = e.changedTouches, best = null, d = Infinity;
    for (var i = 0; list && i < list.length; i++) {
      var t = list[i], dd = Math.abs(t.clientX - down.clientX) + Math.abs(t.clientY - down.clientY);
      if (dd < d) { d = dd; best = t; }
    }
    return best ? best.identifier : null;
  }
  function listed(e, id) {
    for (var i = 0; e.touches && i < e.touches.length; i++) if (e.touches[i].identifier === id) return true;
    return false;
  }

  function watch(surface, o) {
    var refused = null, pressed = null, at = 0;
    var mine = null;   // the stroke in progress: { pointer, touch }
    function gone(e) {
      var own = o.owner();
      if (own == null || !mine || mine.pointer !== own) return own != null && e.touches && e.touches.length === 1 ? 'count' : false;
      return listed(e, mine.touch) ? false : 'touch';
    }
    surface.addEventListener('pointerdown', function (e) {
      var own = o.owner();
      refused = (own != null && e.pointerId !== own && e.pointerType === 'touch') ? e : null;
      pressed = e.pointerType === 'touch' ? e : null;
      at = now();
    }, true);
    surface.addEventListener('touchstart', function (e) {
      var down = refused, press = pressed;
      refused = null; pressed = null;
      if (!press || now() - at > SAME_PRESS_MS) return;
      var own = o.owner();
      if (down && own != null && own !== down.pointerId && gone(e)) {
        o.end();
        o.down(down);
        own = o.owner();
      }
      // The press that began the stroke now in progress: remember its touch.
      if (own != null && own === press.pointerId) mine = { pointer: own, touch: touchOf(e, press) };
    }, { capture: true, passive: true });
    // A lift anywhere that leaves the stroke's own touch off the glass.
    function lifted(e) { if (gone(e) === 'touch') o.end(); }
    window.addEventListener('touchend', lifted, true);
    window.addEventListener('touchcancel', lifted, true);
  }

  var api = { watch: watch };
  if (typeof window !== 'undefined') window.SkriblLostLift = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
