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
 *     displayAt()  which page is on screen at time t  (the player's clock)
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
  /* A pause plays as a beat (owner, DECISIONS.md): each gap between a drawing
   * page's points counts up to GAP_MAX, the Pad's "Trim" cap. A page with no
   * usable `t` draws in point order, 16 ms a point. */
  var GAP_MAX = 250;
  function playTimes(p) {
    for (var t = [0], a = 0, i = 1, g; i < p.length; i++) t.push(a += (g = p[i].t - p[i - 1].t) > 0 ? Math.min(g, GAP_MAX) : 0);
    if (!a) for (i = 1; i < p.length; i++) t[i] = i * 16;
    return t;
  }
  function spanMs(frame) {
    var p = frame && frame.strokes;
    if (!p || p.length < 2) return DRAW_MIN;
    return Math.max(DRAW_MIN, Math.min(DRAW_MAX, playTimes(p)[p.length - 1]));
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
    var t = playTimes(p), due = q * t[p.length - 1];
    while (n < p.length && t[n] <= due) n++;
    return n;
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
  var LOOP_KINDS = { times: [2, MAX_LOOP_TIMES], ms: [LOOP_MS_MIN, LOOP_MS_MAX], forever: 0 };
  function isInt(v) { return typeof v === 'number' && v === Math.floor(v); }
  function loopOf(raw, n) {
    if (!raw || typeof raw !== 'object' || !(n > 0)) return null;
    var from = raw.from, to = raw.to, kind = null, k, v, b;
    if (!isInt(from) || !isInt(to) || from < 0 || to < from || to >= n) return null;
    // The server's shape exactly: no key it would refuse, and one kind only.
    // A loop it would not have posted is not one to honour from a draft either.
    for (k in raw) {
      if (!Object.prototype.hasOwnProperty.call(raw, k) || k === 'from' || k === 'to') continue;
      if (kind || !Object.prototype.hasOwnProperty.call(LOOP_KINDS, k)) return null;
      kind = k;
    }
    if (!kind) return null;
    v = raw[kind]; b = LOOP_KINDS[kind];
    if (b ? !(isInt(v) && v >= b[0] && v <= b[1]) : v !== true) return null;
    var out = { from: from, to: to }; out[kind] = v;
    return out;
  }

  /* THE PAGE UNDERNEATH (owner, on Blooby's card: the card drawn once on page
   * 1 and kept under the waving pages, "rasterized" as it plays rather than
   * copied onto every page). A document may carry one `under`: page `page`
   * is painted, COMPLETE, beneath every page `from`..`to` (0-based,
   * inclusive). The page itself still plays where it stands, so a card can
   * draw itself on page 1 and then stay under pages 2-8. Only the stored
   * shape is decided here -- each surface paints it once into an offscreen
   * image and puts that image beneath the page's ink, so the page's own
   * eraser reveals the card instead of cutting it, as in the editor.
   * The shape is validation.py's exactly (verify_sharedrules), so an `under`
   * either posts and shows everywhere or does neither. */
  function underOf(raw, n) {
    if (!raw || typeof raw !== 'object' || !(n > 0)) return null;
    for (var k in raw) {
      if (Object.prototype.hasOwnProperty.call(raw, k) && k !== 'page' && k !== 'from' && k !== 'to') return null;
    }
    var p = raw.page, a = raw.from, b = raw.to;
    if (!isInt(p) || !isInt(a) || !isInt(b) || p < 0 || p >= n || a < 0 || b < a || b >= n) return null;
    if (p >= a && p <= b) return null;    // a page cannot sit under itself
    return { page: p, from: a, to: b };
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
             stretchMs: Math.max(1, acc - introMs) };
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

  /* WHICH PAGE TO PAINT, AND HOW MUCH OF IT — the composition, not a third
   * helper beside the other two.
   *
   * pageMs() and dueCount() were each correct and still could not, together,
   * ever show a drawing page finished. A slot owns its page over the
   * HALF-OPEN interval [start, end): at end the next slot is current. So a
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
   * v286, P1-M-03.)
   *
   * Over a PLAN, keyed by SLOT rather than page, since a one-page loop shows
   * the same page in consecutive slots. Takes ELAPSED time since play began
   * and wraps it itself. An empty document has no slots and reads as page 0. */
  function displayAt(p, frames, elapsedMs, last) {
    var t = wrapMs(p, elapsedMs), s = slotAt(p, t), i = p.slots[s] | 0;
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
    dueCount: dueCount,
    MAX_LOOP_TIMES: MAX_LOOP_TIMES,
    loopOf: loopOf,
    underOf: underOf,
    plan: plan,
    wrapMs: wrapMs,
    displayAt: displayAt
  };

  if (typeof window !== 'undefined') window.SkriblHold = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
