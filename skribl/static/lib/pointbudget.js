/* The DOCUMENT's point budget — the one number the editors were spending
 * without being able to see it.
 *
 * The server refuses a payload over MAX_TOTAL_POINTS (200,000) across every
 * frame. Nothing client-side tracked that. The smear planner budgets per
 * FRAME -- TWEEN_POINT_CAP 14,000, TWEEN_GROUP_CAP 4,500, both comfortably
 * under the server's per-frame ceiling -- and no code anywhere summed the
 * document. So the limit was enforced in one place only, at POST, at the end
 * of the work.
 *
 * WHAT THAT COSTS, measured. A generated page is about 27x a hand-drawn one:
 * ~1,755 points against ~65 for the same little drawing. The real budget is
 * therefore "how many Motion Smears", and a hundred-page flipbook of them
 * lands at 88% of the cap. Nothing said so until the button.
 *
 * It was never silent -- the server answers "Too many points overall" and the
 * share error puts it on screen, and the drawing is safe locally either way.
 * It arrived LATE, and it named the limit rather than what was eating it.
 *
 * Same shape as MAX_HOLD before lib/holdtiming.js: a limit the server owns and
 * the clients had to guess at. verify_sharedrules.py pins the two together, so
 * this file and skribl/validation.py cannot drift apart again.
 *
 * NOT A PLACE TO RAISE THE CAP. The comment above MAX_TOTAL_POINTS in
 * validation.py says why it exists -- a payload that pins a phone -- and this
 * module exists because the client spent a budget it could not see, which is a
 * different problem with a different fix.
 */
(function () {
  'use strict';

  // Mirrors SKRIBL_MAX_TOTAL_POINTS in skribl/validation.py. A deployment that
  // moves the server's value moves this one in the same change; the harness
  // fails if they part company.
  var MAX_TOTAL_POINTS = 200000;

  /* Every point on every page. Frames that are missing or malformed contribute
     nothing rather than throwing: this runs on the post path, and a budget
     check that can itself fail is worse than no check. */
  function totalPoints(frames) {
    if (!frames || !frames.length) return 0;
    var n = 0;
    for (var i = 0; i < frames.length; i++) {
      var f = frames[i];
      if (f && f.strokes && typeof f.strokes.length === 'number') n += f.strokes.length;
    }
    return n;
  }

  function remaining(frames) {
    return Math.max(0, MAX_TOTAL_POINTS - totalPoints(frames));
  }

  /* Would a page of `extra` points still fit? Asked BEFORE a page is generated,
     which is the whole point: refusing to make an unpostable page is kinder
     than making a hundred of them and finding out at the end. */
  function wouldFit(frames, extra) {
    return totalPoints(frames) + Math.max(0, extra || 0) <= MAX_TOTAL_POINTS;
  }

  function overBudget(frames) {
    return totalPoints(frames) > MAX_TOTAL_POINTS;
  }

  /* The sentence a person can act on. It names the share of the budget that is
     GENERATED, because that is the part they can do something about -- deleting
     a smear frees 27 hand-drawn pages' worth and deleting a drawing frees
     almost nothing. `isGenerated` is passed in rather than detected here: this
     module has no opinion about how a surface marks its own generated pages. */
  function describe(frames, isGenerated) {
    var total = totalPoints(frames), gen = 0, genPages = 0;
    if (typeof isGenerated === 'function') {
      for (var i = 0; i < (frames || []).length; i++) {
        var f = frames[i];
        if (f && f.strokes && isGenerated(f, i)) { gen += f.strokes.length; genPages++; }
      }
    }
    return { total: total, limit: MAX_TOTAL_POINTS,
             pct: Math.round(total / MAX_TOTAL_POINTS * 100),
             generated: gen, generatedPages: genPages,
             over: total > MAX_TOTAL_POINTS };
  }

  var api = {
    MAX_TOTAL_POINTS: MAX_TOTAL_POINTS,
    totalPoints: totalPoints,
    remaining: remaining,
    wouldFit: wouldFit,
    overBudget: overBudget,
    describe: describe
  };

  if (typeof window !== 'undefined') window.SkriblPointBudget = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
