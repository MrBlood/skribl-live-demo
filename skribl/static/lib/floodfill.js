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
 *   ROUND CAPS OVERSHOOT HORIZONTALLY. A run drawn from x0 to x1 extends
 *   half its lineWidth past BOTH ends, so a fill that stops at the region edge
 *   bleeds over the line bounding it. Each run's ends are pulled in by that
 *   much. Note what the inset is measured against: the run's HEIGHT, which is
 *   its lineWidth — not its length. A long thin run is barely shortened.
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
 *   So rows are now grouped only while their extent is UNCHANGED, and each
 *   group is drawn at its own height. A rectangle is one run of two points. A
 *   45-degree edge becomes one run per row, which is the honest cost of an
 *   edge that changes every row — and it tiles exactly, because a group of
 *   height h is drawn at lineWidth h centred on its own middle. Cost follows
 *   the PERIMETER rather than the area, which is the right shape for a fill.
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

  /* Groups tile exactly, so this is only the hairline guard: half a pixel of
     bleed at each end of a group beats an anti-aliased seam between them. */
  var BLEED = 1;
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
      if (has && gStart >= 0 && rowMin[r2] === gLo && rowMax[r2] === gHi) continue;
      if (!flush(r2)) break;
      gStart = has ? r2 : -1;
      if (has) { gLo = rowMin[r2]; gHi = rowMax[r2]; }
    }
    return out;
  }

  /* The lineWidth a run is drawn at: its own height plus the hairline guard. */
  function sizeOf(run) { return run.h + BLEED; }

  /* A run as the two points that draw it.
     THE INSET IS HORIZONTAL ONLY, and that distinction is what the first
     version missed. Round caps overshoot by size/2 at each END of the line, so
     the ends are pulled in by that much — but `size` is now the run's HEIGHT,
     not a proxy for its length, so a long thin run is barely inset at all and
     never collapses. A run genuinely shorter than its own height still becomes
     one point, which drawDot paints at the same width; that is a real sliver,
     not an artefact of over-wide banding. */
  function points(run) {
    var half = sizeOf(run) / 2;
    var len = run.x1 - run.x0;
    if (len <= half) {
      return [{ x: (run.x0 + run.x1) / 2, y: run.y }];
    }
    return [{ x: run.x0 + half, y: run.y }, { x: run.x1 - half, y: run.y }];
  }

  var api = { BLEED: BLEED, MAX_RUNS: MAX_RUNS, runs: runs,
              points: points, sizeOf: sizeOf };
  if (typeof window !== 'undefined') window.SkriblFloodFill = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
