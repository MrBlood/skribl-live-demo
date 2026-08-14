/* The artwork stage — ONE implementation, shared by Pad and Flip.
 *
 * THE RULE: anything that reads a COLOUR or writes a FILE reads the artwork,
 * never the live pad. The pad is a presentation surface — artwork with editor
 * overlays drawn on top so you can work — and an overlay is a temporary aid
 * with no business in a picked colour or a published frame.
 *
 * Both surfaces broke that rule, in OPPOSITE directions, which is why fixing
 * one made them disagree rather than agree:
 *
 *   Flip's pad carried too MUCH — onion skin and motion guides were sampled.
 *     Measured: sampling where only the onion showed returned #561317, the
 *     previous page's red at reduced alpha over the backdrop.
 *   Pad's canvas carried too LITTLE — the background photo is a DOM <img>
 *     layered BEHIND it, so a transparent pixel fell through to bgColor.
 *     Measured: sampling over a loaded photo returned #0d0f14, the backdrop.
 *
 * This file exists rather than a function in each because verify_surfaces.py
 * ratchets the number of functions app.js and flip.js define under the same
 * name — it stood at 57 and a second `paintArtwork` would have made it 58. The
 * ratchet caught that on the release run. Raising it to accommodate the commit
 * that broke it is how a ratchet stops meaning anything.
 *
 * The photo GEOMETRY is not re-derived here: lib/photofit.js owns it, and the
 * export path already goes through it. A second copy of that maths is how the
 * fit buttons and the export drifted apart once before.
 */
(function () {
  'use strict';

  // cfg = { canvas, w, h, dpr, bg, strokes, photo }
  //   canvas  a scratch canvas the caller owns and reuses
  //   strokes the surface holding the current drawing (composited last)
  //   photo   optional { img, fit, offX, offY, zoom, opacity, blur }
  //           omit entirely when the caller already painted its own backdrop
  function stage(cfg) {
    var cv = cfg.canvas, w = cfg.w, h = cfg.h, dpr = cfg.dpr || 1;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
      cv.width = Math.round(w * dpr);
      cv.height = Math.round(h * dpr);
    }
    var c = cv.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);

    // cfg.keep: the caller has ALREADY painted a backdrop onto this canvas and
    // only wants the strokes layered on. Flip does that — drawBackdrop() there
    // composites the background colour and the photo in one pass, and clearing
    // here would erase it. Without this the stage returned bare strokes on
    // transparency and every sample read as the fallback colour.
    if (!cfg.keep) {
      c.clearRect(0, 0, w, h);
      if (cfg.bg) { c.fillStyle = cfg.bg; c.fillRect(0, 0, w, h); }
    }

    var ph = cfg.photo;
    if (ph && ph.img && ph.img.complete && ph.img.naturalWidth && window.SkriblPhotoFit) {
      var r = window.SkriblPhotoFit.rect(ph.img.naturalWidth, ph.img.naturalHeight, w, h,
        { fit: ph.fit, offX: ph.offX, offY: ph.offY, zoom: ph.zoom });
      c.save();
      if (ph.opacity != null) c.globalAlpha = ph.opacity;
      // ctx.filter is absent on older Safari. Blur shifts a sampled colour only
      // slightly, so an unblurred draw is a fair approximation — and far better
      // than the previous answer, which was the backdrop.
      if (ph.blur > 0 && 'filter' in c) c.filter = 'blur(' + ph.blur + 'px)';
      try { c.drawImage(ph.img, r.x, r.y, r.w, r.h); } catch (e) {}
      c.restore();
    }

    if (cfg.strokes) c.drawImage(cfg.strokes, 0, 0, w, h);
    return cv;
  }

  window.SkriblArtwork = { stage: stage };
})();
