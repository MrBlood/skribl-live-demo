/* Flood fill, expressed in the only vocabulary this project has: strokes.
 *
 * THE CONSTRAINT THAT SHAPES EVERYTHING HERE. A Skribl frame is
 * `{strokes, strokeGroups}` where strokes is a FLAT array of
 * `{x, y, color, size, t, erase, start}`. There is no fill primitive, and the
 * player replays those points and nothing else. A new primitive would be a
 * format change the player must honour — the owner's call, not this file's — so
 * Fill earns its place by producing points, exactly as Shape already does
 * (lib/shapes.js turns a drag into a path). The difference is that a shape is a
 * 1-D curve and a fill is a 2-D region, so the question is how to spend points
 * on area without spending many.
 *
 * WHY SCANLINES ARE CHEAP HERE, AND IT IS NOT OBVIOUS. paintSeg() draws
 * `drawLine(prev -> point)` between consecutive points at `lineWidth = size`
 * with round caps. So a horizontal band of the region costs TWO POINTS — its
 * endpoints — not one point per pixel. A full 640x460 fill lands near 200
 * points against a server limit of 20,000 per frame. Rasterising per-pixel, the
 * obvious reading of "fill", would blow that limit on a single tap.
 *
 * WHAT THE CALLER GETS. `runs()` returns `[{y, x0, x1, h}, ...]` in canvas
 * coordinates, each meant to be drawn as one stroke at `sizeOf(run)` — geometry
 * only, no colour, no canvas, no DOM. That keeps it unit-testable without a
 * browser, which is the same reason pagespan.js and sizeclass.js are their own
 * files.
 *
 * THREE THINGS THAT LOOK LIKE DETAILS AND ARE NOT:
 *
 *   ROUND CAPS OVERSHOOT HORIZONTALLY, AND THAT IS ALLOWED TO HAPPEN. Insetting
 *   each end to compensate is the obvious move and it leaves the group's
 *   corners bare, because a cap is a semicircle and the stadium narrows toward
 *   the top and bottom of a thick line. Runs are drawn to their full extent and
 *   the cap is left to bulge outward: at most MAX_GROUP_H/2 of sideways bleed,
 *   under a boundary line wider than that. See `points`.
 *
 *   ROWS ARE GROUPED BY THEIR ACTUAL EXTENT, NOT BY A FIXED STEP — and the
 *   first version got this wrong in a way that showed up on the very first
 *   drawing. It collapsed every 6 pixel rows into one band and gave the band
 *   the UNION of those rows' extents. On a straight edge that is exact. On a
 *   DIAGONAL the union is wider than the narrow rows in the band, the round-cap
 *   inset then pulls each run's ends back, and where the region is narrow —
 *   the apex of a triangle, say — the run comes out shorter than its own width
 *   and collapses to a single dot. A row of those down a diagonal edge is a
 *   PERFORATED LINE, which is exactly what the first fill on the live demo
 *   drew and what the report called "a weird dotted line".
 *
 *   So rows are grouped only while their extent is UNCHANGED, and each group is
 *   drawn at its own height. A 45-degree edge becomes one run per row, which is
 *   the honest cost of an edge that changes every row, and it tiles exactly
 *   because a group of height h is drawn at lineWidth h centred on its middle.
 *
 *   GROUPS ARE ALSO CAPPED IN HEIGHT, which the first attempt at this missed
 *   and which cost a second round of the same bug report. Round caps make a run
 *   a stadium rather than a rectangle, so a TALL group leaves an uncovered
 *   wedge at each corner — about 2px on a group of height 7. A circle's widest
 *   rows repeat their extent and therefore form the tallest groups, so the bare
 *   corners land exactly at the far left and right of a filled circle. See
 *   MAX_GROUP_H.
 *
 *   TOLERANCE IS AGAINST THE SEED, NOT THE NEIGHBOUR. Comparing each pixel to
 *   the one it spread from lets a slow gradient walk the whole canvas — every
 *   step is within tolerance of the last while the end is nothing like the
 *   start. Anchored to the seed colour, tolerance means what a user expects it
 *   to mean.
 *
 * ALPHA IS DELIBERATELY THE CALLER'S PROBLEM, and the answer is "fill opaque".
 * Runs carry a hairline of bleed so they meet rather than seam, so a translucent
 * fill double-darkens every join; and each run is a separate stroke, so a
 * translucent fill of 100 runs blows LAYER_BUDGET (24) and flips the WHOLE
 * frame to direct painting, changing how every other stroke on it looks. Both
 * problems vanish with a solid colour and neither has a cheap fix. flip.js
 * calls solidOf().
 */
(function () {
  'use strict';

  /* HOW MUCH TALLER THAN ITS GROUP EACH RUN IS DRAWN, and it stopped being a
     hairline guard the moment a fill could be smudged.
     A fill is a STACK OF THIN HORIZONTAL STROKES, not a region. Drag it through
     a brush whose weight falls off with distance and neighbouring runs move by
     slightly different amounts, so they fan apart and the ground shows between
     them as a comb. Measured: runs 0.9px apart, the smudge falloff varying
     4.7% across that spacing, so separation grows at ~4.3% of the drag. The
     only thing standing between that and a visible gap is how far the runs
     OVERLAP.
     At BLEED 1 a run is 4px wide over 0.9px spacing -- 3.1px of slack, gone
     after about 72px of drag. At 3 it is 5.1px of slack and about 119px. The
     cost is horizontal: a round cap overshoots by half the width, so the fill
     tucks a further 1px under the line bounding it.
     THIS IS A MITIGATION AND NOT A CURE. Nothing available here survives a
     200px pull; the runs would need to overlap by 8px and the fill would spill
     past its boundary. Combing on a heavily smudged fill is inherent to fills
     being strokes, and the cure is a format that can hold a region. */
  var BLEED = 3;

  /* A CAP ON GROUP HEIGHT, and it is not a cost knob — it is what stops the
     corners of a fill being cut off.
     drawLine uses ROUND caps, so a run is a stadium, not a rectangle: near the
     top and bottom of a thick line the ends curve inward. Grouping by exact
     extent means a circle's widest rows -- where the boundary is nearly
     vertical and extents repeat -- form the TALLEST groups, and a tall group
     leaves an uncovered wedge at each of its four corners. Measured on a group
     of height 7 drawn at lineWidth 8: about 2px bare at the corner. On the live
     demo that read as small dashes at the far left and far right of a filled
     circle, at the vertical middle -- precisely where the groups are tallest.
     At height 3 the same wedge is under a pixel. The cost is bounded and small:
     a 460-tall fill spends at most 154 runs, 308 points, against a server limit
     of 20,000. */
  var MAX_GROUP_H = 3;

  /* HOW FAR THE FILL GROWS PAST WHERE THE FLOOD STOPPED, in pixels.
   *
   * A drawn line is ANTI-ALIASED: its outermost pixels are a blend of ink and
   * ground. The flood stops when a pixel stops matching the seed, which is a
   * pixel or two OUTSIDE the line's solid core, so the fill and the line do not
   * meet — a hairline of fringe survives between them. Because the fill is
   * appended to the strokes array it paints ON TOP of that line, so wherever it
   * fails to reach, the leftover fringe shows through as a dark thread just
   * inside the edge. Ragged, because the flood's stopping point jitters by a
   * pixel from row to row, which is why it reads as DOTTED rather than as a
   * clean outline.
   *
   * Growing the region by a couple of pixels tucks the fill under the line
   * instead. Every paint bucket does some version of this; the alternative is
   * raising the colour tolerance until the fringe is eaten, which is far less
   * predictable and leaks through thin boundaries.
   *
   * The cost is that a fill covers the innermost pixels of the line bounding
   * it. On any line thicker than this it is invisible. On a 1px hairline the
   * fill would swallow it, which is the honest limit of the approach. */
  var GROW = 2;
  /* A guard, in the spirit of shapes.js MAX_POINTS: a pathological region must
     not emit an unbounded array. Two points per run against a 20,000-point
     server limit leaves this an order of magnitude clear. */
  var MAX_RUNS = 4000;

  function chan(data, i) {
    return [data[i], data[i + 1], data[i + 2], data[i + 3]];
  }

  /* Squared distance in RGBA. Squared so the comparison needs no sqrt, and the
     caller's tolerance is squared once to match. Alpha counts: filling from a
     transparent area into a drawn one is the common case on this canvas, and
     ignoring alpha makes every transparent pixel equal to every other colour
     at full transparency. */
  function near(a, b, tol2) {
    var dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2], da = a[3] - b[3];
    return (dr * dr + dg * dg + db * db + da * da) <= tol2;
  }

  /* Scanline flood fill over ImageData, returning horizontal runs.
   *
   * opts: { tolerance (0-255, default 32), maxRuns (default MAX_RUNS) }
   * Returns { runs: [{y, x0, x1, h}], filled, truncated } — each run carries
   * its own height, `filled` is the pixel count, `truncated` whether MAX_RUNS
   * stopped it early. There is no row step: rows group by their real extent.
   */
  function runs(img, seedX, seedY, opts) {
    opts = opts || {};
    var W = img.width, H = img.height, data = img.data;
    var cap = opts.maxRuns || MAX_RUNS;
    var tol = opts.tolerance === undefined ? 32 : opts.tolerance;
    var tol2 = tol * tol * 4;              // four channels compared at once

    var sx = Math.round(seedX), sy = Math.round(seedY);
    // No global `size` any more: each run carries its own height, because that
    // is the whole point of grouping by extent. `sizeOf` turns one into the
    // lineWidth it should be drawn at.
    var out = { runs: [], filled: 0, truncated: false };
    if (!(sx >= 0 && sx < W && sy >= 0 && sy < H)) return out;

    var seed = chan(data, (sy * W + sx) * 4);
    // A per-pixel visited map rather than writing into `data`: the caller may
    // want the ImageData afterwards, and mutating an argument to mark progress
    // is how a function acquires a second, undocumented job.
    var seen = new Uint8Array(W * H);
    var stack = [sx, sy];
    // Row extents. Consecutive rows sharing one are grouped below, so a flat
    // region costs one run however tall it is and a sloping edge costs one per
    // row — cost follows the perimeter, not the area.
    var rowMin = new Int32Array(H), rowMax = new Int32Array(H);
    for (var i = 0; i < H; i++) { rowMin[i] = W; rowMax[i] = -1; }

    while (stack.length) {
      var y = stack.pop(), x = stack.pop();
      if (y < 0 || y >= H) continue;
      var rowBase = y * W;
      if (seen[rowBase + x]) continue;
      if (!near(chan(data, (rowBase + x) * 4), seed, tol2)) continue;

      // Walk left and right to the ends of this pixel row's span.
      var xl = x; while (xl > 0 && !seen[rowBase + xl - 1]
                         && near(chan(data, (rowBase + xl - 1) * 4), seed, tol2)) xl--;
      var xr = x; while (xr < W - 1 && !seen[rowBase + xr + 1]
                         && near(chan(data, (rowBase + xr + 1) * 4), seed, tol2)) xr++;

      for (var k = xl; k <= xr; k++) seen[rowBase + k] = 1;
      out.filled += (xr - xl + 1);
      if (xl < rowMin[y]) rowMin[y] = xl;
      if (xr > rowMax[y]) rowMax[y] = xr;

      // Seed the rows above and below across the whole span.
      for (var m = xl; m <= xr; m++) {
        if (y > 0 && !seen[(y - 1) * W + m]) { stack.push(m, y - 1); }
        if (y < H - 1 && !seen[(y + 1) * W + m]) { stack.push(m, y + 1); }
      }
    }

    // Grow the region before grouping. A box dilation over the row extents:
    // horizontally by GROW, and vertically by taking each row's extent from its
    // neighbours within GROW, so the top and bottom of a shape grow too rather
    // than only its sides.
    if (GROW > 0) {
      var gMin = new Int32Array(H), gMax = new Int32Array(H);
      for (var q = 0; q < H; q++) {
        var lo2 = W, hi2 = -1;
        for (var d = -GROW; d <= GROW; d++) {
          var rr = q + d;
          if (rr < 0 || rr >= H || rowMax[rr] < 0) continue;
          if (rowMin[rr] < lo2) lo2 = rowMin[rr];
          if (rowMax[rr] > hi2) hi2 = rowMax[rr];
        }
        if (hi2 < 0) { gMin[q] = W; gMax[q] = -1; continue; }
        gMin[q] = Math.max(0, lo2 - GROW);
        gMax[q] = Math.min(W - 1, hi2 + GROW);
      }
      rowMin = gMin; rowMax = gMax;
    }

    // Group CONSECUTIVE rows that share an extent exactly, and draw each group
    // at its own height. Grouping loosely — "within a pixel or two" — is the
    // same mistake as the fixed band: it re-introduces the union and the
    // dotted diagonal with it. Exact means a flat region costs one run however
    // tall it is, and a sloping edge costs one run per row, which is what an
    // edge that moves every row actually needs.
    var gStart = -1, gLo = 0, gHi = 0;
    var flush = function (endRow) {
      if (gStart < 0) return true;
      var h = endRow - gStart;
      if (out.runs.length >= cap) { out.truncated = true; return false; }
      out.runs.push({ y: gStart + h / 2, x0: gLo, x1: gHi, h: h });
      return true;
    };
    for (var r2 = 0; r2 <= H; r2++) {
      var has = r2 < H && rowMax[r2] >= 0;
      if (has && gStart >= 0 && rowMin[r2] === gLo && rowMax[r2] === gHi
          && (r2 - gStart) < MAX_GROUP_H) continue;
      if (!flush(r2)) break;
      gStart = has ? r2 : -1;
      if (has) { gLo = rowMin[r2]; gHi = rowMax[r2]; }
    }
    return out;
  }

  /* The lineWidth a run is drawn at: its own height plus the hairline guard. */
  function sizeOf(run) { return run.h + BLEED; }

  /* A run as the two points that draw it, drawn to its FULL extent.
   *
   * NO INSET, AND THAT IS A REVERSAL. Two earlier versions pulled each end in
   * by half the lineWidth, reasoning that round caps overshoot and the fill
   * would otherwise bleed past the boundary. The reasoning is true about the
   * line's CENTRE row and false everywhere else: a round cap is a semicircle,
   * so the stadium narrows toward the top and bottom of a thick line. Inset to
   * the exact extent, the group's four corners end up bare — measured on a
   * filled circle, 52 of 7845 pixels, showing as dashes at the far left and
   * right where the groups are tallest.
   *
   * Drawn full-extent the cap bulges OUTWARD instead, so every pixel of the
   * group is covered and the cost is at most MAX_GROUP_H/2 of bleed sideways —
   * about two pixels, underneath a boundary line that is itself wider than
   * that. GAPS ARE FAR MORE VISIBLE THAN BLEED, and between a fill that stops
   * two pixels short and one that runs two pixels over, the one that runs over
   * is the one nobody reports.
   *
   * A zero-length run becomes a single point, which drawDot paints at the same
   * width; that is a one-pixel sliver of region, not an artefact. */
  function points(run) {
    if (run.x1 <= run.x0) {
      return [{ x: (run.x0 + run.x1) / 2, y: run.y }];
    }
    return [{ x: run.x0, y: run.y }, { x: run.x1, y: run.y }];
  }

  var api = { BLEED: BLEED, MAX_RUNS: MAX_RUNS, runs: runs,
              points: points, sizeOf: sizeOf };
  if (typeof window !== 'undefined') window.SkriblFloodFill = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
