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
 * WHAT THE CALLER GETS. `runs()` returns `[{y, x0, x1}, ...]` in canvas
 * coordinates, each meant to be drawn as one stroke of `size = rowStep / OVERLAP`
 * — geometry only, no colour, no canvas, no DOM. That keeps it unit-testable
 * without a browser, which is the same reason pagespan.js and sizeclass.js are
 * their own files.
 *
 * THREE THINGS THAT LOOK LIKE DETAILS AND ARE NOT:
 *
 *   ROUND CAPS OVERSHOOT. A run drawn from x0 to x1 with round caps extends
 *   size/2 past BOTH ends, so a fill that stops exactly at the region edge
 *   bleeds over the line that bounds it. Every run is therefore inset by half
 *   its own width, and a run too short to survive the inset collapses to its
 *   midpoint — a dot, which drawDot() renders at the same width. Without this
 *   a filled shape grows a halo the width of the brush.
 *
 *   ROWS MUST OVERLAP. Stepping exactly `size` leaves hairline gaps wherever
 *   the row boundary lands mid-pixel, and they are very visible against a dark
 *   ground. OVERLAP makes each row a little taller than its step.
 *
 *   TOLERANCE IS AGAINST THE SEED, NOT THE NEIGHBOUR. Comparing each pixel to
 *   the one it spread from lets a slow gradient walk the whole canvas — every
 *   step is within tolerance of the last while the end is nothing like the
 *   start. Anchored to the seed colour, tolerance means what a user expects it
 *   to mean.
 *
 * ALPHA IS DELIBERATELY THE CALLER'S PROBLEM, and the answer is "fill opaque".
 * Rows overlap by design, so a translucent fill double-darkens every seam into
 * visible banding; and each run is a separate stroke, so a translucent fill of
 * 100 runs blows LAYER_BUDGET (24) and flips the WHOLE frame to direct
 * painting, changing how every other stroke on it looks. Both problems vanish
 * with a solid colour and neither has a cheap fix. flip.js calls solidOf().
 */
(function () {
  'use strict';

  /* Each row is drawn this much taller than the step between rows, so
     consecutive rows meet instead of leaving a seam. */
  var OVERLAP = 1.35;
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
   * opts: { tolerance (0-255, default 32), rowStep (px, default 6),
   *         maxRuns (default MAX_RUNS) }
   * Returns { runs: [{y, x0, x1}], size, filled, truncated } — `size` is the
   * stroke width the caller should draw each run at, `filled` the pixel count,
   * `truncated` whether MAX_RUNS stopped it early.
   */
  function runs(img, seedX, seedY, opts) {
    opts = opts || {};
    var W = img.width, H = img.height, data = img.data;
    var step = Math.max(1, Math.round(opts.rowStep || 6));
    var cap = opts.maxRuns || MAX_RUNS;
    var tol = opts.tolerance === undefined ? 32 : opts.tolerance;
    var tol2 = tol * tol * 4;              // four channels compared at once

    var sx = Math.round(seedX), sy = Math.round(seedY);
    var out = { runs: [], size: step * OVERLAP, filled: 0, truncated: false };
    if (!(sx >= 0 && sx < W && sy >= 0 && sy < H)) return out;

    var seed = chan(data, (sy * W + sx) * 4);
    // A per-pixel visited map rather than writing into `data`: the caller may
    // want the ImageData afterwards, and mutating an argument to mark progress
    // is how a function acquires a second, undocumented job.
    var seen = new Uint8Array(W * H);
    var stack = [sx, sy];
    // Row extents, so the runs can be emitted per BAND rather than per pixel
    // row. minX/maxX per y, then bands of `step` rows collapse to one run each.
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

    // Collapse pixel rows into bands `step` tall. A band takes the union of the
    // rows it covers, which is what makes a fill cost two points per band
    // instead of two per pixel row. It also means a band is only as accurate as
    // its height — the price of the whole approach, and why step is small.
    for (var by = 0; by < H; by += step) {
      var lo = W, hi = -1;
      for (var r = by; r < Math.min(H, by + step); r++) {
        if (rowMax[r] < 0) continue;
        if (rowMin[r] < lo) lo = rowMin[r];
        if (rowMax[r] > hi) hi = rowMax[r];
      }
      if (hi < 0) continue;
      if (out.runs.length >= cap) { out.truncated = true; break; }
      out.runs.push({ y: by + step / 2, x0: lo, x1: hi });
    }
    return out;
  }

  /* A run as the two points that draw it, inset for the round caps. Returns one
     point when the run is shorter than its own width — drawDot() paints that at
     the same size, so a one-pixel sliver still gets covered rather than
     vanishing or bleeding. */
  function points(run, size) {
    var half = size / 2;
    var len = run.x1 - run.x0;
    if (len <= size) {
      return [{ x: (run.x0 + run.x1) / 2, y: run.y }];
    }
    return [{ x: run.x0 + half, y: run.y }, { x: run.x1 - half, y: run.y }];
  }

  var api = { OVERLAP: OVERLAP, MAX_RUNS: MAX_RUNS, runs: runs, points: points };
  if (typeof window !== 'undefined') window.SkriblFloodFill = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
