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

  var KINDS = ['line', 'rect', 'ellipse', 'poly'];
  /* A regular polygon's sides. 3 is a triangle, 12 a dodecagon — past that it
     is an ellipse with extra points, and the ellipse generator already spaces
     itself by arc length, which a polygon cannot. */
  var MIN_SIDES = 3, MAX_SIDES = 12;
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

  /* A closed vertex list walked as straight edges. Shared so a rect and a
     polygon differ only in where their corners are. */
  function _walk(verts) {
    var out = [];
    for (var i = 0; i < verts.length - 1; i++) {
      var seg = _line(verts[i][0], verts[i][1], verts[i + 1][0], verts[i + 1][1]);
      // Drop each segment's first point except on the first edge: it is the
      // previous edge's last point, and a duplicate stamps the corner twice.
      out = out.concat(i === 0 ? seg : seg.slice(1));
      if (out.length >= MAX_POINTS) break;
    }
    return out;
  }

  /* THE SAME CORNER TREATMENT FOR EVERY STRAIGHT-EDGED SHAPE.
   *
   * Each corner is cut back along both of its edges by `r` and the gap filled
   * with a quarter-ish arc. The radius is clamped to half the SHORTEST edge, not
   * to some fixed maximum: a slider that lets the user ask for more rounding
   * than an edge can give produces a shape that folds through itself, and the
   * value that does it is different for every shape and every drag size. Clamped
   * here, the slider simply stops having an effect, which is what a person
   * expects from a control they have run to the end of.
   *
   * `verts` is CLOSED — first point repeated last — so every corner has two
   * edges without the caller special-casing the seam. */
  function _rounded(verts, r) {
    var n = verts.length - 1;
    if (!(r > 0) || n < 3) return _walk(verts);
    var shortest = Infinity;
    for (var i = 0; i < n; i++) {
      var d = Math.hypot(verts[i + 1][0] - verts[i][0], verts[i + 1][1] - verts[i][1]);
      if (d < shortest) shortest = d;
    }
    r = Math.min(r, shortest / 2);
    if (!(r > 0.5)) return _walk(verts);

    var out = [];
    for (var k = 0; k < n; k++) {
      var prev = verts[(k - 1 + n) % n], cur = verts[k], next = verts[k + 1];
      var v1x = prev[0] - cur[0], v1y = prev[1] - cur[1];
      var v2x = next[0] - cur[0], v2y = next[1] - cur[1];
      var l1 = Math.hypot(v1x, v1y) || 1, l2 = Math.hypot(v2x, v2y) || 1;
      var a = { x: cur[0] + (v1x / l1) * r, y: cur[1] + (v1y / l1) * r };
      var b = { x: cur[0] + (v2x / l2) * r, y: cur[1] + (v2y / l2) * r };
      // The straight run into this corner, then the corner itself as a
      // quadratic through the vertex — the same curve a canvas arcTo draws,
      // sampled rather than stroked because this returns POINTS.
      if (out.length) {
        var run = _line(out[out.length - 1].x, out[out.length - 1].y, a.x, a.y);
        out = out.concat(run.slice(1));
      } else {
        out.push(a);
      }
      var steps = Math.max(3, Math.min(24, Math.round(r / SPACING) + 2));
      for (var t = 1; t <= steps; t++) {
        var u = t / steps, iu = 1 - u;
        out.push({ x: iu * iu * a.x + 2 * iu * u * cur[0] + u * u * b.x,
                   y: iu * iu * a.y + 2 * iu * u * cur[1] + u * u * b.y });
      }
      if (out.length >= MAX_POINTS) break;
    }
    // Close back onto the first point.
    if (out.length > 1) {
      var back = _line(out[out.length - 1].x, out[out.length - 1].y, out[0].x, out[0].y);
      out = out.concat(back.slice(1));
    }
    return out.slice(0, MAX_POINTS);
  }

  /* A regular polygon inscribed in the drag's box. The first vertex is at the
     TOP, so a triangle points up — which is what everybody draws when they
     mean "triangle", and an unrotated polygon starting at 0 radians gives a
     triangle lying on its side. */
  function _poly(ax, ay, bx, by, sides) {
    var n = Math.max(MIN_SIDES, Math.min(MAX_SIDES, Math.round(sides || 3)));
    var cx = (ax + bx) / 2, cy = (ay + by) / 2;
    var rx = Math.abs(bx - ax) / 2, ry = Math.abs(by - ay) / 2;
    if (rx < 0.5 && ry < 0.5) return [{ x: cx, y: cy }];
    var verts = [];
    for (var i = 0; i <= n; i++) {
      var a = -Math.PI / 2 + (i % n) * (Math.PI * 2 / n);
      verts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
    }
    return verts;
  }

  function _rectVerts(ax, ay, bx, by) {
    return [[ax, ay], [bx, ay], [bx, by], [ax, by], [ax, ay]];
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
   *   kind     'line' | 'rect' | 'ellipse' | 'poly'
   *   anchor   where the drag started
   *   current  where the pointer is now
   *   opts     { square: bool }   Shift, for everything but a line
   *            { sides: 3..12 }   'poly' only
   *            { radius: px }     corner rounding, straight-edged kinds only
   */
  function points(kind, anchor, current, opts) {
    if (!anchor || !current) return [];
    opts = opts || {};
    var b = current;
    if (opts.square && kind !== 'line') b = _squared(anchor.x, anchor.y, b.x, b.y);
    var r = opts.radius || 0;
    if (kind === 'rect') {
      return _rounded(_rectVerts(anchor.x, anchor.y, b.x, b.y), r);
    }
    if (kind === 'poly') {
      var verts = _poly(anchor.x, anchor.y, b.x, b.y, opts.sides);
      // A degenerate drag returns a single point rather than a vertex list.
      if (verts.length && typeof verts[0].x === 'number') return verts;
      return _rounded(verts, r);
    }
    if (kind === 'ellipse') return _ellipse(anchor.x, anchor.y, b.x, b.y);
    return _line(anchor.x, anchor.y, b.x, b.y);
  }

  /* WHICH KNOBS A KIND HAS, and the only copy of that fact.
   *
   * Sides is meaningless for anything but a polygon; rounding is meaningless
   * for a line and for an ellipse, which has no corners to round. Both editors
   * used to state that rule in their own syncShapeKnobs, which was fine while
   * the only consumer was "hide the row" — but the shape picker now also has
   * to know whether a pick left anything on screen worth staying open for, and
   * a rule asked two different questions in three places is a rule that drifts.
   * It is shape knowledge, not DOM knowledge, so it lives with the shapes.
   */
  var KNOBS = { line: [], rect: ['radius'], ellipse: [], poly: ['sides', 'radius'] };
  function knobs(kind) {
    return (KNOBS[kind] || []).slice();
  }
  function hasKnob(kind, name) {
    return knobs(kind).indexOf(name) !== -1;
  }

  var api = { KINDS: KINDS.slice(), SPACING: SPACING, MAX_POINTS: MAX_POINTS,
              MIN_SIDES: MIN_SIDES, MAX_SIDES: MAX_SIDES, points: points,
              knobs: knobs, hasKnob: hasKnob };
  if (typeof window !== 'undefined') window.SkriblShapes = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
