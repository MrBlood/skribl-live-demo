/* The header's ground, only while the drawing is under it.
 *
 * On the Pad and Flip the header has no card at rest (styles.css, NO CONTAINER
 * AT REST): its controls sit on the page. A phone pins the header (sticky), so
 * once the page scrolls -- the Pen drawer opening is what scrolls it -- the
 * drawing slides under the controls, and Play, Tune and the menu would sit on
 * the ink. This marks the header .over-canvas from the moment the canvas's top
 * passes under it -- and for as long as the page stays scrolled past that, so
 * the dock and the drawer below the canvas are covered too -- and the
 * stylesheet gives it its ground back for that long.
 *
 * Measured, not inferred from scrollY: what matters is whether the two boxes
 * overlap, and the canvas moves for reasons other than a scroll (a drawer
 * opening above the fold, the canvas re-fitting to a new aspect). Each check is
 * one pair of getBoundingClientRect calls, batched to one per frame.
 *
 * Loaded by the Pad and Flip, which each call SkriblHeaderGlass.wire(header,
 * canvas) with their own canvas (app.js, flip.js). The player keeps its header
 * card and does not load this.
 */
(function (global) {
  'use strict';
  var doc = global.document;

  function wire(header, canvas) {
    if (!header || !canvas) return;
    var queued = false;
    function check() {
      queued = false;
      var a = header.getBoundingClientRect(), b = canvas.getBoundingClientRect();
      // Once the drawing's top has gone under the header, everything below
      // it follows: the dock, then the open drawer. So the ground stays for
      // as long as the page is scrolled past that point, not only while the
      // drawing itself is underneath -- scrolled to the end of a long drawer
      // (Music, Fine-tune), the drawing had passed above the header, the
      // ground went, and the dock's icons showed through it, stacked on the
      // header's own (owner's iPhone, after v321).
      var over = a.bottom > b.top + 1 && a.right > b.left && a.left < b.right;
      header.classList.toggle('over-canvas', over);
    }
    function later() {
      if (queued) return;
      queued = true;
      global.requestAnimationFrame(check);
    }
    global.addEventListener('scroll', later, { passive: true });
    global.addEventListener('resize', later);
    if (global.visualViewport) {
      global.visualViewport.addEventListener('scroll', later, { passive: true });
      global.visualViewport.addEventListener('resize', later);
    }
    if (typeof global.ResizeObserver === 'function') {
      var ro = new global.ResizeObserver(later);
      ro.observe(canvas);
      ro.observe(doc.body);
    }
    check();
  }

  global.SkriblHeaderGlass = { wire: wire };
})(window);
