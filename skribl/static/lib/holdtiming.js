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
 *     indexAtMs()  which page is on screen at time t  (the player's clock)
 *     pageMs()     how long page i should stay up      (the editor's timer)
 *
 * A PAGE THAT DRAWS ITSELF IS EXEMPT FROM fps, which is why this module now
 * denominates a page in MILLISECONDS rather than in fps slots. `hold` says how
 * many slots a still page occupies; `draw` says the page replays its own
 * strokes over their recorded timing instead, exactly as the Pad does, and a
 * stroke timeline is not a whole number of slots at any frame rate.
 *
 * pageMs() is the one answer both questions are now built on: a still page is
 * holdOf()/fps, a drawing page is its own span. Everything else — the
 * cumulative table, the cycle duration, elapsed -> index — falls out of it, so
 * a drawing page cannot mean one thing in the editor and another in the player.
 * That is the same failure this module was created for; `draw` is simply the
 * second field capable of causing it.
 *
 * THE SLOT-DENOMINATED API IS GONE rather than kept beside this one. table(),
 * units(), durationMs(), indexAt() and slotMs() answered the same question in
 * a unit that can no longer express every page, and two ways to ask "how long
 * is page i" is the duplication this file was extracted to remove. A document
 * with no `draw` gets identical numbers either way, so no existing post
 * changes.
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

  /* Read defensively for the same reason holdOf() does: a payload written
   * before per-page draw has no `draw` field, so every page must read as false
   * and play bit-for-bit as it always did. Only a literal true counts — a
   * truthy string from a hand-edited payload is not an opt-in. */
  function drawOf(frame) {
    return !!(frame && frame.draw === true);
  }

  /* How long this page's own strokes took to make, from the points' recorded
   * `t`. Floored at DRAW_MIN so a page holding one dot is not zero-length and
   * therefore skipped entirely; capped at DRAW_MAX so one very long page cannot
   * make a loop unwatchable. A page with no strokes has no span and falls back
   * to DRAW_MIN rather than 0, for the same skip reason. */
  var DRAW_MIN = 320, DRAW_MAX = 8000;
  function spanMs(frame) {
    var p = frame && frame.strokes;
    if (!p || p.length < 2) return DRAW_MIN;
    var span = Number(p[p.length - 1].t) - Number(p[0].t);
    if (!(span > 0)) return DRAW_MIN;
    return Math.max(DRAW_MIN, Math.min(DRAW_MAX, span));
  }

  /* THE ONE ANSWER. How many milliseconds page `frame` occupies. Takes the
   * FRAME, not a hold, for the reason slotMs() does: a caller cannot read the
   * wrong page's field. A drawing page ignores fps entirely — that is the
   * point of it. */
  function pageMs(frame, fps) {
    if (drawOf(frame)) return spanMs(frame);
    return (1000 / fpsOf(fps)) * holdOf(frame);
  }

  /* Per-page milliseconds, in page order. The ms counterpart of table(). */
  function msTable(frames, fps) {
    var out = [], i, n = frames && frames.length ? frames.length : 0;
    for (i = 0; i < n; i++) out.push(pageMs(frames[i], fps));
    return out;
  }

  /* Total run time of one cycle, from the ms table. Floored at 1ms for the
   * same reason durationMs() is. */
  function cycleMs(ms) {
    var s = 0, i, n = ms && ms.length ? ms.length : 0;
    for (i = 0; i < n; i++) s += ms[i];
    return Math.max(1, s);
  }

  /* Which page is on screen `elapsedMs` into a cycle, walking the ms table.
   * The slot version floors elapsed into integer units first; this one cannot,
   * because a drawing page's duration is not a whole number of units. */
  function indexAtMs(ms, elapsedMs) {
    if (!ms || !ms.length) return 0;
    var e = Number(elapsedMs);
    if (!(e >= 0)) e = 0;
    var acc = 0, i;
    for (i = 0; i < ms.length; i++) {
      acc += ms[i];
      if (e < acc) return i;
    }
    return ms.length - 1;
  }

  /* How far INTO page `i` the clock is, 0..1 — what a drawing page needs to
   * know which strokes to have revealed. A still page returns 0: it has no
   * progress, it is simply up. */
  function progressAt(ms, frames, elapsedMs) {
    var i = indexAtMs(ms, elapsedMs);
    if (!drawOf(frames && frames[i])) return 0;
    var acc = 0, k;
    for (k = 0; k < i; k++) acc += ms[k];
    var into = Number(elapsedMs) - acc, span = ms[i] || 1;
    if (!(into > 0)) return 0;
    return Math.max(0, Math.min(1, into / span));
  }


  /* THE OTHER ONE ANSWER: how much of a drawing page is on screen at progress
   * `prog`. pageMs() owns how long a page lasts; this owns what that duration
   * has revealed, and it is here for the same reason — four surfaces were each
   * computing it, and they disagreed at the boundaries.
   *
   * Progress 0 reveals NOTHING. That is the case the copies got wrong: the
   * inline player read progress 0 as "not a drawing page" and painted the
   * finished picture, so a page that reveals in the editor and in /s/ arrived
   * on the feed already drawn, then redrew. The three classes are exactly:
   *   prog <= 0   -> 0 points        (the page has not started)
   *   0 < prog < 1 -> a prefix       (the points whose t has come due)
   *   prog >= 1   -> every point     (the page is complete)
   * A non-finite prog is a clock that has not produced a reading yet, which is
   * the start of the page, so it lands on 0 with every other non-positive. */
  function dueCount(frame, prog) {
    var p = frame && frame.strokes;
    if (!p || !p.length) return 0;
    var q = Number(prog);
    if (!(q > 0)) return 0;
    if (q >= 1) return p.length;
    var t0 = Number(p[0].t);
    var span = Math.max(1, Number(p[p.length - 1].t) - t0);
    var due = q * span, n = 0;
    while (n < p.length && (Number(p[n].t) - t0) <= due) n++;
    return n;
  }

  function fpsOf(fps) {
    var f = Number(fps);
    return (isFinite(f) && f > 0) ? f : 12;
  }

  var api = {
    MAX_HOLD: MAX_HOLD,
    holdOf: holdOf,
    DRAW_MIN: DRAW_MIN,
    DRAW_MAX: DRAW_MAX,
    drawOf: drawOf,
    spanMs: spanMs,
    pageMs: pageMs,
    msTable: msTable,
    cycleMs: cycleMs,
    indexAtMs: indexAtMs,
    progressAt: progressAt,
    dueCount: dueCount
  };

  if (typeof window !== 'undefined') window.SkriblHold = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
