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

  /* THE CANVAS'S ROW SPANS THE PAGE (the owner's B, "All yes"). Both editors
   * live in a 720px column; on a wider window the row the canvas sits in (the
   * Pad's .canvas-area, Flip's .flip-stage) reaches out of it to the page's
   * own edges, so the drawing can show as big as the window allows, while the
   * header, the dock and the drawers stay in the column. The reach is
   * measured, half the difference between the page and the column on each
   * side, and the page is the body's box: inside the scrollbar gutters the
   * root keeps, so the row never runs under a scrollbar or past the window.
   * While it reaches, the page wears one surface (styles.css,
   * body.canvas-wide), because the column's edges would cut across the row.
   * Each editor's fit calls this before it measures the room it has.
   *
   *   SkriblChromeFit.span(rowEl)  ->  the px it reaches out on each side
   */
  // The column's own width inside its padding: what the row is without the
  // reach. Which shape a new drawing starts in is picked against this, so it
  // is what it was before the row could reach (the owner's B changes how big
  // a drawing shows, never the drawing).
  function columnWidth(row) {
    var col = row && row.parentElement;
    if (!col) return 0;
    var cs = global.getComputedStyle(col);
    return col.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
  }
  function span(row) {
    var col = row && row.parentElement, body = global.document.body;
    if (!col || !body) return 0;
    var inner = columnWidth(row);
    var reach = Math.max(0, (body.clientWidth - inner) / 2);
    if (reach < 0.5) reach = 0;
    var m = reach ? -reach + 'px' : '';
    if (row.style.marginLeft !== m) { row.style.marginLeft = m; row.style.marginRight = m; }
    body.classList.toggle('canvas-wide', reach > 0);
    return reach;
  }

  global.SkriblChromeFit = { watch: watch, span: span, columnWidth: columnWidth };
})(window);
