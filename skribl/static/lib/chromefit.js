/* The editors' fit when the chrome around the canvas changes size and the
 * window says nothing -- Pad's and Flip's, one watch.
 *
 * WHY. The chrome around the stage changes size without the window changing:
 * on Flip the header's play control widens once there are two pages (2px
 * taller on a phone) and the strip's rows come and go, and each of those left
 * the dock that much past the bottom until the next resize. Flip watched its
 * chrome for that since #289. The Pad re-fit only on the window's resize event,
 * and the owner found what that costs (L3 at 150%, the v327 re-test): "When I
 * switch back to 100% I get 3rd screen shot" -- the drawing stayed the size it
 * had at 150% after Safari's Page Zoom went back to 100%, in a band of empty
 * page. A zoom changed in Settings while Safari sat in the background reached
 * the page with no resize event. Held back here, that event left the Pad at
 * 244px wide at 150% and still 244 at 100%; Flip, watching its chrome, went
 * to 378. Now both watch.
 *
 * WHAT. Only the chrome is observed (the header, the dock, Flip's strip),
 * never the stage, so re-fitting cannot feed back into itself. When any of it
 * changes size, the editor's fit runs on the next frame. A change that moved
 * or resized the canvas is, to everything that tracks the canvas, a resize:
 * the cached rect behind the brush rings and the eyedropper's lens both
 * listen for one. Without it an armed lens stayed where the canvas USED to be
 * (main's CI, after #289). Compared with the last box seen here, not with the
 * box before the fit: the header's growth has already moved the canvas by the
 * time this runs.
 *
 *   SkriblChromeFit.watch({ chrome: [elements], target: canvasEl, fit: fn })
 *
 * Checked in verify_layout: the Pad and Flip each re-fit when the page widens
 * with its resize event held back, and Flip's armed lens follows a header
 * grown by hand.
 */
(function (global) {
  'use strict';

  function watch(opts) {
    if (typeof global.ResizeObserver !== 'function' || !opts || !opts.target) return null;
    var target = opts.target, fit = opts.fit;
    var queued = false, lastBox = null;
    var ro = new global.ResizeObserver(function () {
      if (queued) return;
      queued = true;
      global.requestAnimationFrame(function () {
        queued = false;
        fit();
        var r = target.getBoundingClientRect();
        var box = r.left + ',' + r.top + ',' + r.width + ',' + r.height;
        if (lastBox !== null && box !== lastBox) global.dispatchEvent(new Event('resize'));
        lastBox = box;
      });
    });
    // border-box: padding and borders are height the stage has to give up too.
    (opts.chrome || []).forEach(function (el) { if (el) ro.observe(el, { box: 'border-box' }); });
    return ro;
  }

  global.SkriblChromeFit = { watch: watch };
})(window);
