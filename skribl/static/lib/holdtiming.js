/* Per-page timing — the ONE definition of how long a page lasts and how much
 * of a drawing page has been revealed, shared by the Flip editor and every
 * surface that plays one.
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
 * AND THE SECOND HALF OF THE SAME LESSON, learned one release later. `draw`
 * shipped with pageMs() shared and the RENDER left to each surface, so four of
 * them — the editor's reveal loop, app.js, inlineplayer.js and flip.js's
 * exporter — each turned a progress into a stroke count themselves. They
 * agreed in the middle of the range and disagreed at both ends. The inline
 * player decided a page was still whenever its progress read 0, which is also
 * what a drawing page reads at the instant it begins, so on the feed alone a
 * Draw-on page opened FINISHED and then wiped and redrew; the exporter
 * re-denominated the page in fps slots and ran it short. Neither was visible
 * from the editor, which is the same blind spot as the original bug above.
 *
 *     dueCount()   how much of page i is on screen at progress p
 *
 * is therefore here beside pageMs(), and for the same reason: how long a page
 * lasts and how much of it you can see are one question asked twice.
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

  /* 8, not 4: subdividing a document doubles every stored hold (see flip.js's
   * carveForInsert), so a page the artist holds x4 stores as 8. The ceiling is
   * on the STORED unit, not on what anyone chooses in the editor -- the badge
   * still cycles 1..4. skribl/validation.py carries the same number and
   * verify_sharedrules.py fails if they part company. */
  var MAX_HOLD = 8;

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
    var p = frame && frame.strokes, q = Number(prog), n = 0;
    if (!p || !p.length || !(q > 0)) return 0;
    if (q >= 1) return p.length;
    var t0 = Number(p[0].t);
    var due = q * Math.max(1, Number(p[p.length - 1].t) - t0);
    while (n < p.length && Number(p[n].t) - t0 <= due) n++;
    return n;
  }

  /* WHICH PAGE TO PAINT, AND HOW MUCH OF IT — the composition, not a third
   * helper beside the other two.
   *
   * pageMs() and dueCount() were each correct and still could not, together,
   * ever show a drawing page finished. indexAtMs() owns a page over the
   * HALF-OPEN interval [start, end): at end the next page is current. So a
   * drawing page's progress climbs toward 1 and the clock takes the page away
   * before it arrives, and dueCount() releases the last point only at 1. On a
   * 1,150ms page of 26 points the 26th was never due while that page was up —
   * its final mark simply never appeared, and if that mark began a stroke, the
   * whole stroke was missing. An inclusive stroke timeline does not fit a
   * half-open display interval; something has to give, and it must not be the
   * millisecond semantics of dueCount().
   *
   * So the last thing RENDERED gives instead. When the clock has moved off a
   * drawing page that has not yet been shown whole, this returns that page at
   * progress 1 for one more display frame, and only then yields. The caller
   * passes back what it last painted, which is what makes this terminate: once
   * that carries progress 1, the next call moves on. One frame late at a page
   * turn, which is the same tolerance the exporter already accepts, and it is
   * the only way the invariant can read the same on every surface:
   *
   *   a drawing page begins empty, reveals monotonically, reaches its complete
   *   recorded state, and only then yields to the next page.
   *
   * NOT FOR SEEKING. A scrub asks for a page and must get that page; the guard
   * belongs to playback, where the pages go by on their own. (Outside review of
   * v286, P1-M-03.) */
  function displayAt(ms, frames, elapsedMs, last) {
    var i = indexAtMs(ms, elapsedMs);
    if (last && last.index !== i && last.index >= 0 && last.progress < 1
        && drawOf(frames && frames[last.index])) {
      return { index: last.index, progress: 1 };
    }
    return { index: i, progress: progressAt(ms, frames, elapsedMs) };
  }

  /* A LOOPED STRETCH (owner: Blooby's card -- "keep it looping forever so he
   * just keeps waving ... and it doesn't start over"). A document may carry
   * one `loop`: pages from..to (0-based, inclusive) play on repeat, then the
   * document carries on. Exactly one of:
   *   times    -- the stretch plays this many times in all (2..MAX_LOOP_TIMES)
   *   ms       -- it repeats for about this long: whole passes, the nearest
   *               count to ms, never fewer than one (LOOP_MS_MIN..LOOP_MS_MAX)
   *   forever  -- it never ends: the pages before it play once, then the
   *               stretch repeats for as long as the Flip is on screen, and
   *               any page after it never plays.
   * Read defensively, as hold and draw are: a payload without `loop`, or with
   * one that does not parse, plays exactly as it always did. The bounds are a
   * shared rule with skribl/validation.py (verify_sharedrules). */
  var MAX_LOOP_TIMES = 8, LOOP_MS_MIN = 500, LOOP_MS_MAX = 30000;
  function loopOf(raw, n) {
    if (!raw || typeof raw !== 'object' || !(n > 0)) return null;
    var from = raw.from, to = raw.to;
    if (!(from === Math.floor(from) && to === Math.floor(to))) return null;
    if (from < 0 || to < from || to >= n) return null;
    // The server's shape exactly: no key it would refuse, and one kind only.
    // A loop it would not have posted is not one to honour from a draft either.
    var kinds = 0;
    for (var k in raw) {
      if (!Object.prototype.hasOwnProperty.call(raw, k)) continue;
      if (k === 'times' || k === 'ms' || k === 'forever') kinds++;
      else if (k !== 'from' && k !== 'to') return null;
    }
    if (kinds !== 1) return null;
    if (raw.forever === true) return { from: from, to: to, forever: true };
    if (raw.times === Math.floor(raw.times) && raw.times >= 2 && raw.times <= MAX_LOOP_TIMES)
      return { from: from, to: to, times: raw.times };
    if (raw.ms === Math.floor(raw.ms) && raw.ms >= LOOP_MS_MIN && raw.ms <= LOOP_MS_MAX)
      return { from: from, to: to, ms: raw.ms };
    return null;
  }

  /* THE PLAY ORDER. Every surface that plays a Flip asks this, not the page
   * list, so a loop cannot mean one thing in the editor and another in a
   * player -- the reason this module exists. `slots` is the order pages play
   * in for one finite pass (the pages before the loop, the stretch repeated,
   * the pages after); a forever loop's pass is the pages before plus the
   * stretch ONCE, and its clock wraps inside the stretch, never to page 1.
   * Without a loop, slots are 0..n-1 and every answer is the old one. */
  function plan(frames, fps, rawLoop) {
    var ms = msTable(frames, fps), n = ms.length, lp = loopOf(rawLoop, n);
    var slots = [], i, r;
    if (!lp) { for (i = 0; i < n; i++) slots.push(i); }
    else {
      var stretch = 0;
      for (i = lp.from; i <= lp.to; i++) stretch += ms[i];
      var reps = lp.forever ? 1 : lp.times ? lp.times
               : Math.max(1, Math.round(lp.ms / Math.max(1, stretch)));
      for (i = 0; i < lp.from; i++) slots.push(i);
      for (r = 0; r < reps; r++) for (i = lp.from; i <= lp.to; i++) slots.push(i);
      if (!lp.forever) for (i = lp.to + 1; i < n; i++) slots.push(i);
    }
    var starts = [], acc = 0;
    for (i = 0; i < slots.length; i++) { starts.push(acc); acc += ms[slots[i]]; }
    var introMs = 0;
    if (lp) for (i = 0; i < lp.from; i++) introMs += ms[i];
    return { ms: ms, loop: lp, slots: slots, starts: starts, cycle: Math.max(1, acc),
             forever: !!(lp && lp.forever), introMs: introMs,
             loopStart: lp ? lp.from : 0, stretchMs: Math.max(1, acc - introMs) };
  }

  /* Elapsed time since play began -> time within the plan. A finite plan
   * cycles whole, as every Flip always has; a forever plan never goes back
   * before its loop. */
  function wrapMs(p, elapsedMs) {
    var e = Number(elapsedMs);
    if (!(e >= 0)) e = 0;
    if (p.forever && e >= p.introMs) return p.introMs + ((e - p.introMs) % p.stretchMs);
    return e % p.cycle;
  }

  /* Which slot is on screen at plan time `t`, and the page it shows. */
  function slotAt(p, t) {
    var lo = 0, hi = p.slots.length - 1;
    while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (p.starts[mid] <= t) lo = mid; else hi = mid - 1; }
    return lo;
  }

  /* displayAt() over a plan: the same contract (a drawing page reaches its
   * complete state before it yields), keyed by SLOT rather than page, since a
   * one-page loop shows the same page in consecutive slots. Takes ELAPSED
   * time since play began; wraps it itself. */
  function planDisplayAt(p, frames, elapsedMs, last) {
    var t = wrapMs(p, elapsedMs), s = slotAt(p, t), i = p.slots[s];
    if (last && last.slot !== s && last.slot >= 0 && last.progress < 1
        && drawOf(frames && frames[last.index])) {
      return { slot: last.slot, index: last.index, progress: 1 };
    }
    var prog = 0;
    if (drawOf(frames && frames[i])) {
      var into = t - p.starts[s], span = p.ms[i] || 1;
      prog = into > 0 ? Math.max(0, Math.min(1, into / span)) : 0;
    }
    return { slot: s, index: i, progress: prog };
  }

  /* The editor's timer steps slot to slot: what plays after slot `s`. */
  function nextSlot(p, s) {
    var n = p.slots.length;
    if (p.forever && s + 1 >= n) {
      var k = 0; while (k < n && p.slots[k] !== p.loopStart) k++;
      return k < n ? k : 0;
    }
    return (s + 1) % n;
  }

  /* What an EXPORTED file holds. A file can only replay whole, so a forever
   * loop exports the pages before it once and then the stretch repeated
   * until the file runs about FOREVER_EXPORT_MS (at least once, at most
   * MAX_LOOP_TIMES * 4 passes); the export sheet says so. A finite plan
   * exports its own slots. Returns page indices in order. */
  var FOREVER_EXPORT_MS = 10000;
  function exportSlots(p) {
    if (!p.forever) return p.slots.slice();
    var out = [], i, k = 0, lp = p.loop;
    for (i = 0; i < lp.from; i++) out.push(i);
    var reps = Math.max(1, Math.min(MAX_LOOP_TIMES * 4,
      Math.ceil((FOREVER_EXPORT_MS - p.introMs) / p.stretchMs)));
    for (k = 0; k < reps; k++) for (i = lp.from; i <= lp.to; i++) out.push(i);
    return out;
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
    dueCount: dueCount,
    displayAt: displayAt,
    MAX_LOOP_TIMES: MAX_LOOP_TIMES,
    LOOP_MS_MIN: LOOP_MS_MIN,
    LOOP_MS_MAX: LOOP_MS_MAX,
    FOREVER_EXPORT_MS: FOREVER_EXPORT_MS,
    loopOf: loopOf,
    plan: plan,
    wrapMs: wrapMs,
    planDisplayAt: planDisplayAt,
    nextSlot: nextSlot,
    exportSlots: exportSlots
  };

  if (typeof window !== 'undefined') window.SkriblHold = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
