/* The draw drawer's HALF detent — one implementation, both editors.
 *
 * WHY. On a phone the draw drawer covered most of the canvas, so choosing a
 * pen colour meant judging contrast against art you could no longer see
 * (owner picked this fix from the design audit, mocked before built). At
 * compact widths the drawer now OPENS at the half detent: the grabber, the
 * colour section, and an honest "Brush, smoothing & more" button — the
 * canvas stays visible above. Pulling the grabber up (or the more button)
 * expands to the full drawer; pulling down returns to half; pulling down
 * again closes. TAPPING the grabber closes the drawer, at either detent (v317,
 * the owner: "I hit the drawer grip and they stay" -- it toggled half and
 * full, which on a phone reads as a menu that will not go away; every sheet's
 * grabber closes it, and this one does too). Desktop is untouched: the sections were never in the
 * canvas's way there, and the CSS shows the handle only at sheet widths —
 * the same pattern .menu-handle uses.
 *
 * WHAT THIS OWNS: the detent-full class, the grabber's tap/drag/keyboard
 * behaviour, the reveal scroll on expand, and the reset — a drawer HIDDEN by
 * any route forgets its detent, so every fresh open starts at half,
 * predictable. WHAT IT DOES NOT: opening and closing. The exclusive-drawer
 * machine (lib/drawers.js on Pad, Flip's wrappers) keeps that; `close` is
 * injected so a tap on the grabber, or a pull down past half, can hand off to
 * whichever machine owns the panel.
 */
(function () {
  'use strict';

  /* Scroll so `panel`'s end sits at the bottom of the VISIBLE screen.
   *
   * Not scrollIntoView, on hard-won evidence: the owner's iPhone shipped the
   * half detent with its "Brush, smoothing & more" button below the fold
   * through TWO rounds of scrollIntoView-based reveals — a smooth call
   * issued as the panel un-hides, and an instant re-assert 450ms later —
   * while every Chromium run scrolled perfectly. So this computes the
   * absolute position itself and writes document.scrollingElement.scrollTop,
   * the bluntest scrolling primitive there is; measures the fold against
   * visualViewport.height where it exists, because iOS Safari's bottom bar
   * overlays the layout viewport and innerHeight can lie about what a
   * person can actually see; and re-asserts at three delays, because the
   * device settles its URL bar, its layout and its own competing scrolls on
   * a schedule no single timeout catches. Each assert is a no-op when the
   * end is already visible, so browsers that got it right the first time
   * feel nothing.
   */
  function revealPanelEnd(panel, behavior) {
    function viewH() {
      return (window.visualViewport && window.visualViewport.height)
        ? window.visualViewport.height : window.innerHeight;
    }
    function target() {
      var r = panel.getBoundingClientRect();
      var scroller = document.scrollingElement || document.documentElement;
      var want = scroller.scrollTop + r.bottom - viewH() + 8;
      var max = scroller.scrollHeight - window.innerHeight;
      return Math.max(0, Math.min(want, max));
    }
    requestAnimationFrame(function () {
      window.scrollTo({ top: target(), behavior: behavior || 'smooth' });
    });
    [300, 700, 1200].forEach(function (ms) {
      setTimeout(function () {
        if (panel.hidden || panel.classList.contains('eyedropper-veiled')) return;
        if (panel.getBoundingClientRect().bottom > viewH() + 1) {
          (document.scrollingElement || document.documentElement).scrollTop = target();
        }
      }, ms);
    });
  }

  /* STEP ASIDE FOR THE EYEDROPPER. On a phone an open colour panel scrolls the
   * page to show itself, which carries the top of the canvas off the screen,
   * and the eyedropper then has nothing up there to pick from. Found by a
   * scripted drawing on both editors: a stroke near the top could not be
   * sampled with the panel open, and closing the panel disarmed the pick.
   *
   * veil(panel, true) hides the panel without closing it (so no close hook
   * disarms the pick it is making room for), remembers where the page was,
   * and scrolls the whole canvas back into view. veil(panel, false) shows it
   * again and, if it is still open, puts the page back -- that is the
   * abandoned pick. A pick closes the panel for real, and a closed panel is
   * left where the drawer machine puts it. One helper, so Pad and Flip cannot
   * drift apart on it. */
  var veiledAt = null;
  function veil(panel, on) {
    if (!panel) return;
    var scroller = document.scrollingElement || document.documentElement;
    if (on) {
      if (!panel.classList.contains('eyedropper-veiled')) veiledAt = scroller.scrollTop;
      panel.classList.add('eyedropper-veiled');
      window.scrollTo({ top: 0, behavior: 'auto' });
      return;
    }
    if (!panel.classList.contains('eyedropper-veiled')) return;
    panel.classList.remove('eyedropper-veiled');
    var back = veiledAt; veiledAt = null;
    requestAnimationFrame(function () {
      if (panel.hidden || back == null) return;
      window.scrollTo({ top: back, behavior: 'auto' });
    });
  }

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
      revealPanelEnd(panel, b);
    }

    function isFull() { return panel.classList.contains('detent-full'); }
    function setFull(v) {
      v = !!v;
      if (v === isFull()) return;
      panel.classList.toggle('detent-full', v);
      if (v) reveal();
    }

    if (more) more.addEventListener('click', function () { setFull(true); });

    /* The grabber: a tap closes; a deliberate drag reads the direction — up
     * expands, down collapses, down again closes. Threshold 24px so a wobbly
     * tap is still a tap. Both editors pass `close`; the toggle is the
     * defensive fallback for a caller that does not, so a tap is never dead. */
    function tap() { if (close) close(); else setFull(!isFull()); }
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
      if (sy != null && !acted) tap();
      sy = null; pid = null;
    });
    handle.addEventListener('pointercancel', function (e) {
      if (e.pointerId === pid) { sy = null; pid = null; }
    });
    handle.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tap(); }
    });

    // A drawer hidden by ANY route forgets its detent: every open is half.
    new MutationObserver(function () {
      if (panel.hidden) panel.classList.remove('detent-full');
    }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  }

  window.SkriblDrawerDetent = { attach: attach, revealPanelEnd: revealPanelEnd, veil: veil };
}());
