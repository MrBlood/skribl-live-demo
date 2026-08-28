/* Per-page hold — the ONE definition of what a hold MEANS, shared by the Flip
 * editor and the player.
 *
 * A page with `hold: n` occupies n base-fps slots instead of one. That is a
 * two-line idea, and it was implemented twice:
 *
 *     flip.js  frameHold()      clamp to [1, MAX_HOLD], default 1
 *     flip.js  runPlayTimer()   a self-rescheduling setTimeout per page
 *     app.js   flipHolds        the SAME clamp, with the 4 written out again
 *     app.js   flipIndexAt()    a cumulative table, elapsed -> page index
 *
 * The two schedulers disagreed. app.js's cumulative table was right the whole
 * time; flip.js's timer took its delay from frames[playI] AFTER playStep() had
 * advanced playI, and never wrapped playI, so a hold stretched the page BEFORE
 * the one carrying it and was ignored entirely from the second loop onward.
 * Reported as "hold doesn't do anything noticeable", which is exactly what it
 * did. What makes that expensive is not the bug, it is that the EDITOR was
 * disagreeing with what a viewer sees: nothing in the preview could reveal it.
 *
 * Same shape as the eraser multiplier before lib/erasersize.js and
 * MAX_LOOP_SECONDS before lib/looptrim.js — a rule duplicated across surfaces
 * with nothing forcing the copies to agree. This module owns the clamp, the
 * cumulative table, and the two questions each surface actually asks:
 *
 *     indexAt()  which page is on screen at time t   (the player's clock)
 *     slotMs()   how long page i should stay up      (the editor's timer)
 *
 * The two mechanisms stay different — the player maps a clock to an index, the
 * editor reschedules a timer — because they are solving different problems.
 * What they can no longer do is disagree about the ANSWER.
 *
 * Every caller keeps an inline fallback, as the other libs here do, so a
 * surface that somehow loads without this file behaves exactly as it did.
 */
(function () {
  'use strict';

  var MAX_HOLD = 4;

  /* Read defensively: a payload written before per-page holds has no `hold`
   * field at all, so every page must read as 1 and play bit-for-bit as it
   * always did. NaN, 0, negatives and junk all land on 1 for the same reason. */
  function holdOf(frame) {
    var h = Math.round(Number(frame && frame.hold));
    return (isFinite(h) && h >= 1) ? Math.min(h, MAX_HOLD) : 1;
  }

  function table(frames) {
    var out = [], i, n = frames && frames.length ? frames.length : 0;
    for (i = 0; i < n; i++) out.push(holdOf(frames[i]));
    return out;
  }

  function units(holds) {
    var u = 0, i, n = holds && holds.length ? holds.length : 0;
    for (i = 0; i < n; i++) u += holds[i];
    return u;
  }

  function fpsOf(fps) {
    var f = Number(fps);
    return (isFinite(f) && f > 0) ? f : 12;
  }

  /* Total run time of one cycle. Floored at 1ms so a caller dividing by it
   * cannot produce Infinity on an empty document. */
  function durationMs(holds, fps) {
    return Math.max(1, (units(holds) / fpsOf(fps)) * 1000);
  }

  /* Which page is on screen `elapsedMs` into a cycle. */
  function indexAt(holds, fps, elapsedMs) {
    if (!holds || !holds.length) return 0;
    var u = Math.floor((Number(elapsedMs) / 1000) * fpsOf(fps));
    if (!(u >= 0)) u = 0;
    var acc = 0, i;
    for (i = 0; i < holds.length; i++) {
      acc += holds[i];
      if (u < acc) return i;
    }
    return holds.length - 1;
  }

  /* How long page `i` should stay on screen. Takes the FRAME, not a hold, so a
   * caller cannot read the hold off the wrong page — which is the mistake this
   * module exists to stop. */
  function slotMs(frame, fps) {
    return (1000 / fpsOf(fps)) * holdOf(frame);
  }

  var api = {
    MAX_HOLD: MAX_HOLD,
    holdOf: holdOf,
    table: table,
    units: units,
    durationMs: durationMs,
    indexAt: indexAt,
    slotMs: slotMs
  };

  if (typeof window !== 'undefined') window.SkriblHold = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
