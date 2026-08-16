/* Loop trim clamping — the rule both editors apply six times between them.
 *
 * WHAT IS SHARED: given a handle, a target time and the current loop, where do
 * the two trim points end up. Four invariants, in this order:
 *
 *     start >= 0                          end <= duration
 *     end - start >= MIN_LOOP_SECONDS     end - start <= MAX_LOOP_SECONDS
 *
 * WHY IT IS HERE. The cap was a NAMED CONSTANT on Flip (MAX_LOOP_SECONDS, nine
 * uses) and a BARE 20 on Pad, eight times, with no constant anywhere in the
 * file. Changing the cap therefore meant editing one line on one surface and
 * eight magic numbers on the other, and nothing would have failed if the second
 * edit was missed — the two surfaces would simply have allowed different loop
 * lengths. MIN was scattered the same way as a bare 0.5.
 *
 * THE TWO MODES, and why this module has a parameter instead of an opinion.
 *
 * When a drag would make the loop longer than the cap, the surfaces do one of
 * two things, and BOTH of them do both:
 *
 *   'constrain'  the handle being dragged stops at the cap; the other end does
 *                not move. Used by the main-track handles on Pad and Flip.
 *   'slide'      the dragged handle goes where it was put and the OTHER end is
 *                pushed to keep the loop exactly at the cap, so the window
 *                slides. Used by the zoom-track handles and by nudge, on Pad
 *                and Flip.
 *
 * That is one control behaving two ways depending on which track you grabbed
 * it from — but Pad and Flip are IDENTICAL about it, path for path, so it is a
 * design inconsistency faithfully duplicated, not drift between the surfaces.
 * Unifying it would change what dragging a handle does, which is a UX decision
 * and not a refactor's to make. So the mode is an explicit named argument: the
 * inconsistency is now stated at each call site instead of hidden inside six
 * copies of the arithmetic, and whoever decides has one place to change.
 */
(function () {
  'use strict';

  var MAX_LOOP_SECONDS = 20;
  var MIN_LOOP_SECONDS = 0.5;

  function num(v, fallback) {
    v = Number(v);
    return Number.isFinite(v) ? v : fallback;
  }

  /* setHandle(state, which, time, mode) -> { start, end }
   *
   * state: { start, end, duration }
   * which: 'start' | 'end'        — the handle being moved
   * time:  the target time, in seconds, unclamped
   * mode:  'constrain' | 'slide'  — see above. Anything else is 'constrain',
   *        which is the more conservative of the two: it never moves a handle
   *        the user did not touch.
   *
   * Returns a NEW object. The callers keep their own trimStart/trimEnd module
   * globals, so handing back a fresh pair rather than mutating means this
   * cannot reach into a surface's state and the caller stays in charge of it.
   */
  function setHandle(state, which, time, mode) {
    state = state || {};
    var duration = num(state.duration, 0);
    var start = num(state.start, 0);
    var end = num(state.end, duration);
    var t = num(time, 0);
    var slide = (mode === 'slide');

    if (!(duration > 0)) return { start: start, end: end };

    if (which === 'start') {
      start = Math.max(0, Math.min(t, end - MIN_LOOP_SECONDS));
      if (end - start > MAX_LOOP_SECONDS) {
        if (slide) end = start + MAX_LOOP_SECONDS;
        else start = end - MAX_LOOP_SECONDS;
      }
    } else {
      end = Math.min(duration, Math.max(t, start + MIN_LOOP_SECONDS));
      if (end - start > MAX_LOOP_SECONDS) {
        if (slide) start = end - MAX_LOOP_SECONDS;
        else end = start + MAX_LOOP_SECONDS;
      }
    }
    return { start: start, end: end };
  }

  /* loopLength(seconds, duration) -> a length that satisfies both bounds.
   * Used by "match the drawing": Pad clamped with a bare 20 here too. */
  function loopLength(seconds, duration) {
    var d = num(duration, 0);
    var s = num(seconds, 0);
    if (!(d > 0)) return 0;
    // The minimum is only enforceable when the media is at least that long.
    // Returning 0.5 for a 0.2-second clip violated this helper's own <=duration
    // contract and forced every caller to repair the result afterwards.
    var minLength = Math.min(MIN_LOOP_SECONDS, d);
    return Math.min(MAX_LOOP_SECONDS, d, Math.max(minLength, Math.min(s, d)));
  }

  window.SkriblLoopTrim = {
    setHandle: setHandle,
    loopLength: loopLength,
    MAX_LOOP_SECONDS: MAX_LOOP_SECONDS,
    MIN_LOOP_SECONDS: MIN_LOOP_SECONDS
  };
}());
