/* Shapes — line, rectangle and ellipse, expressed as ordinary stroke points.
 *
 * THE WHOLE POINT OF THIS FILE IS THAT IT ADDS NO FORMAT. A Skribl is a flat
 * array of {x, y, color, size, t, start, erase} that the player replays; a
 * shape primitive would mean a schema change, new rendering in the player, and
 * every existing post needing to keep working. Instead a shape is GENERATED as
 * points along its own outline, so the player draws it with the code it already
 * has and never learns that shapes exist.
 *
 * That also means shapes replay the way everything else does — they are drawn,
 * not stamped — and they undo, export, and post with no special cases.
 *
 * Sampling is by arc length rather than by parameter. An ellipse sampled at
 * even angles bunches its points at the ends of the long axis and starves the
 * flat sides, which shows up as a lumpy line once each segment is stroked with
 * a round cap. Even spacing costs one extra pass and looks right at any aspect.
 *
 * `square` is what Shift means for a rectangle or an ellipse: equal extent on
 * both axes, keeping the sign of each so the shape still follows the drag into
 * whichever quadrant it was headed. For a line, Shift is handled by
 * lib/constrain.js before the anchor ever reaches here — same modifier, two
 * different meanings, which is the convention everywhere else.
 */
(function () {
  'use strict';

  var KINDS = ['line', 'rect', 'ellipse'];
  var SPACING = 3;      // px between generated points
  var MAX_POINTS = 900; // a guard: a huge drag must not emit an unbounded array

  function _squared(ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay;
    var m = Math.max(Math.abs(dx), Math.abs(dy));
    return { x: ax + (dx < 0 ? -m : m), y: ay + (dy < 0 ? -m : m) };
  }

  function _count(len) {
    return Math.max(2, Math.min(MAX_POINTS, Math.round(len / SPACING) + 1));
  }

  function _line(ax, ay, bx, by) {
    var n = _count(Math.hypot(bx - ax, by - ay));
    var out = [];
    for (var i = 0; i < n; i++) {
      var t = i / (n - 1);
      out.push({ x: ax + (bx - ax) * t, y: ay + (by - ay) * t });
    }
    return out;
  }

  function _rect(ax, ay, bx, by) {
    // Corners in order, closing back to the start so the outline joins.
    var c = [[ax, ay], [bx, ay], [bx, by], [ax, by], [ax, ay]];
    var out = [];
    for (var i = 0; i < 4; i++) {
      var seg = _line(c[i][0], c[i][1], c[i + 1][0], c[i + 1][1]);
      // Drop each segment's first point except on the first edge: it is the
      // previous edge's last point, and a duplicate stamps the corner twice.
      out = out.concat(i === 0 ? seg : seg.slice(1));
    }
    return out;
  }

  function _ellipse(ax, ay, bx, by) {
    var cx = (ax + bx) / 2, cy = (ay + by) / 2;
    var rx = Math.abs(bx - ax) / 2, ry = Math.abs(by - ay) / 2;
    if (rx < 0.5 && ry < 0.5) return [{ x: cx, y: cy }];
    // Ramanujan's perimeter approximation — good to well under a pixel here,
    // and it decides how many samples an even spacing needs.
    var h = Math.pow(rx - ry, 2) / Math.pow(rx + ry || 1, 2);
    var per = Math.PI * (rx + ry) * (1 + (3 * h) / (10 + Math.sqrt(4 - 3 * h)));
    var n = _count(per);
    // Walk the ellipse at even ARC LENGTH: step a fine parameter and emit a
    // point each time the accumulated distance passes the target spacing.
    var fine = Math.max(n * 8, 256);
    var step = per / (n - 1);
    var out = [{ x: cx + rx, y: cy }];
    var acc = 0, px = cx + rx, py = cy;
    for (var i = 1; i <= fine; i++) {
      var a = (i / fine) * Math.PI * 2;
      var x = cx + rx * Math.cos(a), y = cy + ry * Math.sin(a);
      acc += Math.hypot(x - px, y - py);
      px = x; py = y;
      if (acc >= step) { out.push({ x: x, y: y }); acc = 0; }
      if (out.length >= MAX_POINTS) break;
    }
    out.push({ x: cx + rx, y: cy });   // close it
    return out;
  }

  /* points(kind, anchor, current, opts) -> [{x, y}, ...]
   *   kind     'line' | 'rect' | 'ellipse'
   *   anchor   where the drag started
   *   current  where the pointer is now
   *   opts     { square: bool }  Shift, for rect and ellipse
   */
  function points(kind, anchor, current, opts) {
    if (!anchor || !current) return [];
    opts = opts || {};
    var b = current;
    if (opts.square && kind !== 'line') b = _squared(anchor.x, anchor.y, b.x, b.y);
    if (kind === 'rect') return _rect(anchor.x, anchor.y, b.x, b.y);
    if (kind === 'ellipse') return _ellipse(anchor.x, anchor.y, b.x, b.y);
    return _line(anchor.x, anchor.y, b.x, b.y);
  }

  var api = { KINDS: KINDS.slice(), SPACING: SPACING, MAX_POINTS: MAX_POINTS, points: points };
  if (typeof window !== 'undefined') window.SkriblShapes = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
