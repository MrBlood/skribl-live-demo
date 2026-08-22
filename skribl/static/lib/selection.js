/* Selection — pick a region, then move what is inside it.
 *
 * The geometry only. Flip already built the hard half of this for Move
 * artwork: capture the ORIGINAL point positions once, then rewrite them as
 * origin + offset on every drag frame. That is the pattern reused here, and it
 * is the reason a move is exact rather than cumulative — adding a delta to the
 * live points each frame accumulates float error and makes "back to zero"
 * impossible to hit.
 *
 * SELECTION IS BY STROKE GROUP, never by individual point. A stroke is one
 * gesture; moving half of one would split a line down the middle and leave the
 * replay drawing a segment between the two halves — the same connecting-line
 * failure as the mirror bug, and just as baked into the payload. Groups are
 * what strokeGroups already records, so this needs no new bookkeeping.
 *
 * A group counts as selected when ANY of its points falls inside the marquee,
 * not when all of them do. "All" is unusable in practice: a long stroke that
 * wanders slightly outside a box the user drew around the thing they meant is
 * the normal case, and requiring containment means the obvious drag selects
 * nothing. "Any" over-selects occasionally, which is visible and correctable;
 * "all" under-selects silently, which reads as the tool being broken.
 */
(function () {
  'use strict';

  /* rect(a, b) -> {x, y, w, h} normalised, so a drag in any direction works. */
  function rect(a, b) {
    if (!a || !b) return null;
    return {
      x: Math.min(a.x, b.x), y: Math.min(a.y, b.y),
      w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y)
    };
  }

  function inRect(pt, r) {
    return pt.x >= r.x && pt.x <= r.x + r.w && pt.y >= r.y && pt.y <= r.y + r.h;
  }

  /* groupsIn(strokes, groups, r) -> array of group INDICES whose stroke has at
   * least one point inside r. Returns [] for a degenerate marquee, so a stray
   * click cannot select the whole drawing.
   */
  function groupsIn(strokes, groups, r) {
    if (!r || r.w < 3 || r.h < 3) return [];
    var out = [], at = 0;
    for (var g = 0; g < groups.length; g++) {
      var n = groups[g], hit = false;
      for (var i = at; i < at + n && i < strokes.length; i++) {
        if (inRect(strokes[i], r)) { hit = true; break; }
      }
      if (hit) out.push(g);
      at += n;
    }
    return out;
  }

  /* spans(groups, indices) -> [[start, end), ...] point ranges for those groups. */
  function spans(groups, indices) {
    var starts = [], at = 0;
    for (var g = 0; g < groups.length; g++) { starts[g] = at; at += groups[g]; }
    return indices.map(function (g) { return [starts[g], starts[g] + groups[g]]; });
  }

  /* captureOrigin(strokes, ranges) -> a flat copy of the ORIGINAL coordinates.
   * Snapshot once when the move begins; see the note at the top about why the
   * live points are never used as the base.
   */
  function captureOrigin(strokes, ranges) {
    var origin = [];
    ranges.forEach(function (r) {
      for (var i = r[0]; i < r[1] && i < strokes.length; i++) {
        origin.push({ i: i, x: strokes[i].x, y: strokes[i].y });
      }
    });
    return origin;
  }

  /* applyOffset(strokes, origin, dx, dy) — rewrite from the snapshot, so
   * dragging back to 0,0 restores the exact original coordinates.
   */
  function applyOffset(strokes, origin, dx, dy) {
    for (var k = 0; k < origin.length; k++) {
      var o = origin[k], s = strokes[o.i];
      if (!s) continue;
      s.x = o.x + dx;
      s.y = o.y + dy;
    }
  }

  /* bounds(strokes, origin) -> the selection's box, for drawing the outline. */
  function bounds(strokes, origin) {
    if (!origin || !origin.length) return null;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (var k = 0; k < origin.length; k++) {
      var s = strokes[origin[k].i];
      if (!s) continue;
      if (s.x < minX) minX = s.x;
      if (s.y < minY) minY = s.y;
      if (s.x > maxX) maxX = s.x;
      if (s.y > maxY) maxY = s.y;
    }
    if (minX === Infinity) return null;
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
  }

  var api = {
    rect: rect, inRect: inRect, groupsIn: groupsIn, spans: spans,
    captureOrigin: captureOrigin, applyOffset: applyOffset, bounds: bounds
  };
  if (typeof window !== 'undefined') window.SkriblSelect = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
