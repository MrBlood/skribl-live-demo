/* Which contact a gesture belongs to — shared by Pad, Flip and the player.
 *
 * THE RULE. `e.touches[0]` is the first contact on the SCREEN, not the one on
 * the element being dragged. Those are the same thing only while nothing else
 * is touching the glass. With a thumb resting anywhere on the page — holding a
 * phone one-handed, a palm on a tablet — `touches[0]` is the thumb, and the
 * gesture reads its position instead of the finger's.
 *
 * `targetTouches` is the subset that started on the element receiving the
 * event, which is the contact that owns the drag. `changedTouches` covers
 * touchend/touchcancel, where the lifted contact has already left
 * targetTouches and the list would otherwise be empty. Mouse and Pointer
 * events fall through to the event itself, which already carries clientX/Y.
 *
 * WHY THIS IS A LIB AND NOT A HELPER IN EACH FILE. It was written twice, once
 * in app.js and once in flip.js, and verify_surfaces.py caught it immediately:
 * that suite counts function names defined in BOTH files and it is a ratchet,
 * not a target — the 61st shared name has to justify itself. This one could
 * not. Unlike _eraserSize or _brushWidth, which are four-line adapters over
 * each surface's differently-named state, this function reads nothing but its
 * argument. There was no reason for two copies beyond the order they were
 * written in.
 *
 * THE DEFECT IT CLOSES, measured rather than argued: with a thumb resting off
 * the canvas, a Pad stroke drew at x=56 — the thumb — instead of x=201, where
 * the drawing finger actually was. Reverting the canvas read alone reproduces
 * x=56. DESIGN-DIRECTION.md calls "my mark goes where my finger went" the first
 * promise a drawing app makes.
 *
 * The player loads this too: the scrub track is a player control and it read
 * the same screen-wide list, so a viewer holding the phone with a thumb on the
 * glass scrubbed to wherever the thumb was.
 *
 * THE PINCH HELPERS ARE NOT HERE. They live in lib/pinchgesture.js, which the
 * two editors load and the player does not: the player has no ZoomView, so
 * every pinch path in app.js returns before reaching them. Keeping them here
 * cost the player 480 B of code it can never execute, on a payload with three
 * figures of headroom.
 *
 * NO FALLBACK IN THE CALLERS, deliberately. A silent fallback to `touches[0]`
 * would restore exactly the bug this exists to remove, on the surface where the
 * lib failed to load and nowhere else — the hardest possible thing to notice.
 * If this file is missing, the gesture paths throw, which is what
 * verify_lib.py's negative test expects of a real dependency.
 */
(function () {
  'use strict';

  function eventPoint(e) {
    if (!e) return e;
    var list = (e.targetTouches && e.targetTouches.length) ? e.targetTouches
             : (e.changedTouches && e.changedTouches.length) ? e.changedTouches
             : (e.touches && e.touches.length) ? e.touches
             : null;
    return list ? list[0] : e;
  }

  var api = { at: eventPoint };
  if (typeof window !== 'undefined') window.SkriblEventPoint = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
