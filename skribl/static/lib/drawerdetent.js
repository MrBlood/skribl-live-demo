/* The draw drawer's HALF detent — one implementation, both editors.
 *
 * WHY. On a phone the draw drawer covered most of the canvas, so choosing a
 * pen colour meant judging contrast against art you could no longer see
 * (owner picked this fix from the design audit, mocked before built). At
 * compact widths the drawer now OPENS at the half detent: the grabber, the
 * colour section, and an honest "Brush, smoothing & more" button — the
 * canvas stays visible above. Pulling or tapping the grabber (or the more
 * button) expands to the full drawer; pulling down returns to half; pulling
 * down again closes. Desktop is untouched: the sections were never in the
 * canvas's way there, and the CSS shows the handle only at sheet widths —
 * the same pattern .menu-handle uses.
 *
 * WHAT THIS OWNS: the detent-full class, the grabber's tap/drag/keyboard
 * behaviour, the reveal scroll on expand, and the reset — a drawer HIDDEN by
 * any route forgets its detent, so every fresh open starts at half,
 * predictable. WHAT IT DOES NOT: opening and closing. The exclusive-drawer
 * machine (lib/drawers.js on Pad, Flip's wrappers) keeps that; `close` is
 * injected so a pull-down-past-half can hand off to whichever machine owns
 * the panel.
 */
(function () {
  'use strict';

  function attach(panel, opts) {
    if (!panel) return;
    opts = opts || {};
    var handle = panel.querySelector('.drawer-detent-handle');
    var more = panel.querySelector('.drawer-detent-more');
    if (!handle) return;
    var close = typeof opts.close === 'function' ? opts.close : null;

    function reveal() {
      // The expand adds height below the fold; bring the drawer's end back
      // on screen, honouring reduced motion the way the drawer machine does.
      var b = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto' : 'smooth';
      requestAnimationFrame(function () {
        panel.scrollIntoView({ behavior: b, block: 'end' });
      });
    }

    function isFull() { return panel.classList.contains('detent-full'); }
    function setFull(v) {
      v = !!v;
      if (v === isFull()) return;
      panel.classList.toggle('detent-full', v);
      if (v) reveal();
    }

    if (more) more.addEventListener('click', function () { setFull(true); });

    /* The grabber: a tap toggles half<->full; a deliberate drag reads the
     * direction — up expands, down collapses, down again closes. Threshold
     * 24px so a wobbly tap is still a tap. */
    var sy = null, pid = null, acted = false;
    handle.addEventListener('pointerdown', function (e) {
      e.preventDefault();
      e.stopPropagation();
      sy = e.clientY; pid = e.pointerId; acted = false;
      try { handle.setPointerCapture(e.pointerId); } catch (err) {}
    });
    handle.addEventListener('pointermove', function (e) {
      if (sy == null || e.pointerId !== pid || acted) return;
      var dy = e.clientY - sy;
      if (Math.abs(dy) <= 24) return;
      acted = true;
      if (dy < 0) setFull(true);
      else if (isFull()) setFull(false);
      else if (close) close();
    });
    handle.addEventListener('pointerup', function (e) {
      if (e.pointerId !== pid) return;
      if (sy != null && !acted) setFull(!isFull());
      sy = null; pid = null;
    });
    handle.addEventListener('pointercancel', function (e) {
      if (e.pointerId === pid) { sy = null; pid = null; }
    });
    handle.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setFull(!isFull()); }
    });

    // A drawer hidden by ANY route forgets its detent: every open is half.
    new MutationObserver(function () {
      if (panel.hidden) panel.classList.remove('detent-full');
    }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  }

  window.SkriblDrawerDetent = { attach: attach };
}());
