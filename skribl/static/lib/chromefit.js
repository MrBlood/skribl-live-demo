/* The editors' fit when the chrome around the canvas changes size and the
 * window says nothing -- Pad's and Flip's, one watch -- the canvas's row
 * reaching past the column on a wide window (span()), and the shape the canvas
 * starts in (a new drawing's, startShape; a draft's own, noted beside it).
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
  // How far the row reaches out on each side, read without moving it: the
  // Pad picks a new drawing's shape against the row it will be before the
  // row reaches (roomOf), because a row reaching while it is still empty
  // grows taller than it will be (on a desk, 949px where it lays out at 700).
  function reach(row) {
    var col = row && row.parentElement, body = global.document.body;
    if (!col || !body) return 0;
    var r = Math.max(0, (body.clientWidth - columnWidth(row)) / 2);
    return r < 0.5 ? 0 : r;
  }
  // The room inside a row's padding: in its column, in the whole row as it
  // will reach, and its height. The Pad's, before its first drawing.
  function roomOf(row) {
    var r = row.getBoundingClientRect(), cs = global.getComputedStyle(row);
    var px = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0), col = columnWidth(row);
    return { col: Math.min(r.width, col) - px, row: col + 2 * reach(row) - px,
             h: r.height - (parseFloat(cs.paddingTop) || 0) - (parseFloat(cs.paddingBottom) || 0) };
  }
  // A NEW DRAWING'S SHAPE, one rule for both editors, each measuring its own
  // room: the preset that shows largest in the column (lib/canvassizes.js
  // bestFor), unless a touch screen is held upright and the square fits at
  // its own size in the whole row; then the square. The owner's A after the
  // tablet mock ("All yes"), then "do Flip on the 12.9 too": an upright
  // iPad's column is just short of the square (696 of its 707), so the Pad
  // started tall on an Air and an 11-inch, and Flip, whose stage is taller
  // there, on a 12.9-inch Pro. A phone (the square never fits), a desk (no
  // finger) and a tablet on its side start as they did. Here and not in
  // app.js, which the link player loads and never needs this from.
  function startShape(col, row, h) {
    var t = global.SkriblCanvasSizes, mm = global.matchMedia;
    if (!t || !t.bestFor || !(col > 50 && h > 50)) return null;
    var sq = t.byId && t.byId('square');
    if (sq && row >= sq.w && h >= sq.h && mm && mm('(pointer: coarse) and (orientation: portrait)').matches) return sq;
    return t.bestFor(col, h);
  }
  // THE SHAPE THE PAD STARTS IN (app.js resizeCanvas): a draft's own, noted
  // beside it (below), else a new drawing's for the room its row has. Here,
  // with the rest of the rule, where the link player never loads it.
  function padShape(row) {
    var room = roomOf(row);
    return noted('pad') || startShape(room.col, room.row, room.h);
  }
  function span(row) {
    var body = global.document.body;
    if (!row || !row.parentElement || !body) return 0;
    var r = reach(row);
    var m = r ? -r + 'px' : '';
    if (row.style.marginLeft !== m) { row.style.marginLeft = m; row.style.marginRight = m; }
    body.classList.toggle('canvas-wide', r > 0);
    return r;
  }

  /* A DRAFT'S SHAPE, NOTED BESIDE IT (the calm open, part 2). Each editor
   * notes its drawing's shape beside its draft as it saves it, and drops the
   * note with the draft: the size, Flip's page count, and whether there is
   * ink. It is small enough to read before anything paints, so
   * _skribl_fit_early.html lays a draft you come back to out in its own
   * shape, and the Pad starts in it (app.js resizeCanvas) rather than in a
   * new drawing's shape that the draft replaced a moment later: on a slower
   * phone a frame was drawn between the two (verify_identity). A site's post
   * box and the letter sheet keep no draft, so they start as a new drawing.
   *
   *   SkriblChromeFit.note('pad' | 'flip', { w, h, pages, ink } | null)
   *   SkriblChromeFit.noted('pad' | 'flip')  ->  that shape, or null
   */
  var NOTE = 'skribl.shape.v1.';
  function note(kind, shape) {
    try {
      if (shape) global.localStorage.setItem(NOTE + kind, JSON.stringify(shape));
      else global.localStorage.removeItem(NOTE + kind);
    } catch (e) {}
  }
  function noted(kind) {
    if (global.SKRIBL_COMPOSE || global.SKRIBL_LETTERS) return null;
    var n = null;
    try { n = JSON.parse(global.localStorage.getItem(NOTE + kind) || 'null'); } catch (e) { return null; }
    var px = function (v) { return v === Math.round(v) && v > 0 && v <= 4096; };
    return n && px(n.w) && px(n.h) ? n : null;
  }

  global.SkriblChromeFit = { watch: watch, span: span, columnWidth: columnWidth, reach: reach, roomOf: roomOf, startShape: startShape,
                             padShape: padShape, note: note, noted: noted };
})(window);
