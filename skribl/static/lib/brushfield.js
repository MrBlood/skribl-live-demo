/* The arithmetic behind tools that act on ink already on the page.
 *
 * WHAT THESE TOOLS HAVE IN COMMON. Liquify, Smudge and Blur all sweep a round
 * brush over existing strokes and change the points inside it by an amount that
 * falls off from the centre. Liquify moves them; Smudge moves them differently;
 * Blur recolours and widens them. The traversal and the falloff are the same
 * question three times, so they live here, pure and testable, rather than being
 * typed out three times with three slightly different constants nobody meant to
 * make different.
 *
 * WHY BLUR IS EXPRESSIBLE AT ALL, which is not obvious and was nearly a
 * blocker. A frame is `{strokes, strokeGroups}` — a flat array of
 * `{x, y, color, size, t, erase, start}` — and you cannot blur a polyline by
 * moving its points. There is no raster layer to convolve and adding one is a
 * format change the player must honour.
 *
 * The way through is a detail of paintStatic(): a stroke whose FIRST point is
 * opaque is painted by paintSeg with each point's OWN colour and OWN size. So
 * per-point colour is honoured, and "blur" becomes a thing that can be said in
 * this format after all — fade a point toward the ground it sits on and widen
 * it, and the line goes faint and soft exactly where the brush passed. It reads
 * as defocus on line art, it composes when you go over it twice, and the player
 * renders it identically because the player runs the same paint path.
 *
 * WHAT THAT IS NOT. It is not a convolution: it cannot soften a photograph
 * underneath, and it fades toward the page's background colour rather than
 * toward whatever pixels happen to be behind the line. On a photo background a
 * blurred line goes toward the page colour, not toward the photo. That is a
 * real limit, it is the honest boundary of doing this without a format change,
 * and it is written here rather than discovered later.
 *
 * ALPHA IS DELIBERATELY UNTOUCHED. Reducing a stroke's alpha would be the
 * obvious way to fade it, and it is the wrong one twice over: paintStatic takes
 * a stroke's alpha from its FIRST point, so a per-point change would not apply;
 * and translucent strokes are composited one at a time against LAYER_BUDGET
 * (24), so a blur that made a dozen of them would flip the whole frame to
 * direct painting and change how every other stroke on it looks. Mixing toward
 * the background gets the same appearance with none of that.
 */
(function () {
  'use strict';

  /* Falloff from the centre of the brush. `sharpness` 1 is Liquify's smooth
     shoulder; higher values pull the effect toward the middle, which is what
     makes Smudge feel like a fingertip rather than a field. Returns 0 outside
     the radius so a caller can use it as its own reject test. */
  function weight(d2, r2, sharpness) {
    if (!(r2 > 0) || d2 >= r2) return 0;
    var t = 1 - Math.sqrt(d2 / r2);
    var s = sharpness === undefined ? 1 : sharpness;
    return s === 1 ? t : Math.pow(t, s);
  }

  function _clamp255(v) { return v < 0 ? 0 : (v > 255 ? 255 : Math.round(v)); }

  /* RGB out of the two forms this project's colours actually take: '#rrggbb'
     (and the 8-digit variant the in-betweener writes) and 'rgb()/rgba()'.
     Returns null for anything else so a caller can leave the point alone rather
     than paint it black — a colour parser that guesses is how one bad string
     turns a drawing into a silhouette. */
  function rgbOf(col) {
    if (typeof col !== 'string') return null;
    var m = col.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (m) return [+m[1], +m[2], +m[3]];
    var h = col.replace('#', '');
    if (/^[0-9a-f]{8}$/i.test(h)) h = h.slice(0, 6);
    if (!/^[0-9a-f]{6}$/i.test(h)) {
      if (/^[0-9a-f]{3}$/i.test(h)) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
      else return null;
    }
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16),
            parseInt(h.slice(4, 6), 16)];
  }

  /* Blend `col` toward `toward` by t (0..1), preserving the ALPHA `col` already
     carried. Blur must not silently make a see-through stroke opaque, and the
     brush preset that produced that alpha is not this file's business. */
  function mix(col, toward, t) {
    var a = rgbOf(col), b = rgbOf(toward);
    if (!a || !b) return col;
    if (t <= 0) return col;
    if (t > 1) t = 1;
    var r = _clamp255(a[0] + (b[0] - a[0]) * t),
        g = _clamp255(a[1] + (b[1] - a[1]) * t),
        bl = _clamp255(a[2] + (b[2] - a[2]) * t);
    var am = (typeof col === 'string')
      ? col.match(/^rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)$/i)
      : null;
    if (am) return 'rgba(' + r + ', ' + g + ', ' + bl + ', ' + am[1] + ')';
    return 'rgb(' + r + ', ' + g + ', ' + bl + ')';
  }

  /* Every point of `strokes` inside a brush at (px, py), with its weight.
     Bounding-box reject before the distance test, because this runs at the
     display rate over a page that can hold thousands of points: a hypot per
     point per frame is the difference between a tool that tracks the finger and
     one that does not. Liquify learned that the hard way and this keeps it. */
  function each(strokes, px, py, r, sharpness, fn) {
    var r2 = r * r;
    var x0 = px - r, x1 = px + r, y0 = py - r, y1 = py + r;
    var hit = false;
    for (var i = 0; i < strokes.length; i++) {
      var p = strokes[i];
      if (p.x < x0 || p.x > x1 || p.y < y0 || p.y > y1) continue;
      var ex = p.x - px, ey = p.y - py, d2 = ex * ex + ey * ey;
      var w = weight(d2, r2, sharpness);
      if (w <= 0) continue;
      fn(p, w, i);
      hit = true;
    }
    return hit;
  }

  var api = { weight: weight, rgbOf: rgbOf, mix: mix, each: each };
  if (typeof window !== 'undefined') window.SkriblBrushField = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
