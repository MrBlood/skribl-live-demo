/* Photo fit geometry — the part both editors and the player must agree on.
 *
 * WHAT IS SHARED: where a background photo lands on the canvas. Given the
 * image's natural size, the canvas size, a fit mode, a crop offset and a zoom,
 * this returns the destination rectangle. Pad drew it inline (drawPhotoFitted),
 * Flip computed it inline (photoRect), and the player used Pad's copy — three
 * call sites, two implementations, one of which could not read the vocabulary
 * the other wrote.
 *
 * THE VOCABULARY, and why normalise() exists.
 *
 * The third fit is labelled "Stretch" on both surfaces, but the shared partial
 * carried `data-fit="{{ 'fill' if kind == 'flip' else 'stretch' }}"` — the
 * markup was bent to fit two controller vocabularies rather than the
 * controllers agreeing. `stretch` is the value that travels: flip.js
 * translates 'fill' -> 'stretch' when it builds the post payload, so 'stretch'
 * is what the player and the database see, and 'fill' is a Flip-local alias.
 *
 * That translation ran in exactly ONE direction. Flip's restore whitelist was
 * ['cover','contain','fill'], so the value Flip itself posts was rejected on
 * the way back in and fell through to 'cover'; and photoRect only special-cased
 * 'fill', so a 'stretch' that did get in rendered as cover while NO fit button
 * showed as active. A surface that cannot read what it writes is the drift this
 * module exists to end.
 *
 * normalise() therefore accepts both spellings and returns the canonical one.
 * It does NOT change what either surface stores: Flip may keep saying 'fill'
 * internally, because normalising on the way in costs nothing and changing a
 * persisted vocabulary is a decision about live data, not a refactor.
 */
(function () {
  'use strict';

  var CANON = ['cover', 'contain', 'stretch'];
  // 'fill' is Flip's local spelling of 'stretch'. It is an ALIAS, not a fourth
  // mode: a fourth mode would need a fourth button.
  var ALIAS = { fill: 'stretch' };

  /* normalise(fit) -> 'cover' | 'contain' | 'stretch'
   * Anything unrecognised becomes 'cover', which is the default both surfaces
   * already fell back to, so an unknown value degrades the way it used to. */
  function normalise(fit) {
    var f = String(fit == null ? '' : fit).trim().toLowerCase();
    if (ALIAS[f]) f = ALIAS[f];
    return CANON.indexOf(f) === -1 ? 'cover' : f;
  }

  /* rect(iw, ih, cw, ch, opts) -> { x, y, w, h }
   *
   * opts: { fit, offX, offY, zoom }. Returns the destination rectangle to draw
   * the image into, in canvas units.
   *
   *   stretch  fills the canvas, ignoring aspect ratio, offset and zoom
   *   contain  fits entirely inside, CENTRED — offset and zoom do not apply,
   *            because there is nothing cropped to choose between
   *   cover    fills the canvas, crops the overflow, and is the only mode
   *            where offset and zoom mean anything
   *
   * Degenerate input returns the whole canvas rather than NaN: a zero-width
   * image is not a reason to paint nothing at coordinates the caller cannot
   * debug.
   */
  function rect(iw, ih, cw, ch, opts) {
    opts = opts || {};
    iw = Number(iw); ih = Number(ih); cw = Number(cw); ch = Number(ch);
    if (!(iw > 0) || !(ih > 0) || !(cw > 0) || !(ch > 0)) {
      return { x: 0, y: 0, w: cw > 0 ? cw : 0, h: ch > 0 ? ch : 0 };
    }
    var fit = normalise(opts.fit);
    if (fit === 'stretch') return { x: 0, y: 0, w: cw, h: ch };

    var scale;
    if (fit === 'contain') {
      scale = Math.min(cw / iw, ch / ih);
    } else {
      var z = Number(opts.zoom);
      // Zoom multiplies the cover scale. A missing or absurd zoom means 1, not
      // a collapsed image.
      if (!Number.isFinite(z) || z <= 0) z = 1;
      scale = Math.max(cw / iw, ch / ih) * z;
    }
    var w = iw * scale, h = ih * scale;

    // Only cover has anything cropped to choose between, so only cover reads
    // the offset. 0.5 is centred.
    var fx = 0.5, fy = 0.5;
    if (fit === 'cover') {
      var ox = Number(opts.offX), oy = Number(opts.offY);
      if (Number.isFinite(ox)) fx = ox;
      if (Number.isFinite(oy)) fy = oy;
    }
    return { x: (cw - w) * fx, y: (ch - h) * fy, w: w, h: h };
  }

  window.SkriblPhotoFit = { rect: rect, normalise: normalise, FITS: CANON.slice() };
}());
