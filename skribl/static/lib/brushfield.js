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
 * blocker. A frame is `{strokes, strokeGroups}` -- a flat array of
 * `{x, y, color, size, t, erase, start}` -- and you cannot blur a polyline by
 * moving its points. There is no raster layer to convolve and adding one is a
 * format change the player must honour.
 *
 * The way through is EXPANDED TRANSLUCENT COPIES: draw the same path several
 * times, widest and faintest first, so the crisp core lands on top of its own
 * halo and the overlap of the passes is the falloff. flip.js's blurRebuild owns
 * that, and the in-between has used the same shape since v238.
 *
 * WHAT THAT IS NOT, and the limit is unchanged: it is not a convolution. It
 * cannot soften a photograph underneath, because it only ever redraws strokes
 * -- there are no pixels beneath to sample. On a photo background a blurred
 * line gets its own soft edge and the photo stays exactly as sharp as it was.
 * That is the honest boundary of doing this without a format change, and it is
 * written here rather than discovered later.
 *
 * THIS FILE'S `mix` IS SMUDGE'S, NOT BLUR'S -- a note that used to say the
 * opposite. Blur fades a pass by ALPHA now, written as an 8-digit hex so that
 * paintStatic's layering test (alphaOf, which only matches rgba()) reads it as
 * opaque while the canvas still renders it translucent; that is what keeps four
 * passes per stroke from spending LAYER_BUDGET. Smudge still mixes toward the
 * ground, because smudged pigment genuinely thins as it is dragged, and that IS
 * a colour change rather than a transparency one.
 *
 * The paragraph here previously argued that per-point alpha could not work at
 * all, on the grounds that paintStatic takes a stroke's alpha from its FIRST
 * point. True of rgba(), and false of '#rrggbbaa': that form is honoured per
 * point by the canvas itself. The reasoning was sound about the mechanism it
 * had in mind and wrong about the conclusion it drew.
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
