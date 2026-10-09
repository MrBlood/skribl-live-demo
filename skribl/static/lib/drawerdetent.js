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

  function viewH() {
    return (window.visualViewport && window.visualViewport.height)
      ? window.visualViewport.height : window.innerHeight;
  }

  /* Where the sticky header ends, measured where it STICKS -- its own top plus
   * its height -- rather than where it happens to be before the page scrolls.
   * 0 when the header is not sticky (desktop), so nothing below changes there. */
  function stuckBottom() {
    var h = document.querySelector('.header');
    if (!h) return 0;
    var cs = getComputedStyle(h);
    if (cs.position !== 'sticky' && cs.position !== 'fixed') return 0;
    return (parseFloat(cs.top) || 0) + h.getBoundingClientRect().height;
  }

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
    var dock = opts.dock || null;

    function reveal() {
      // The expand adds height below the fold; bring the drawer's end back
      // on screen, honouring reduced motion the way the drawer machine does.
      var b = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto' : 'smooth';
      revealPanelEnd(panel, b);
      // ...and the TOP stays under the dock. The editors' own open-scrolls
      // can settle a little past the end (Flip's block:'end' scrollIntoView, by
      // 9-15px at 700-720px tall), and a fitted drawer is exactly the room, so
      // that little is the dock under the header. Fitted, the drawer
      // fits, so scrolling it back never hides its end. After the reveal's own
      // re-asserts, so it has the last word.
      [750, 1300].forEach(function (ms) {
        setTimeout(function () {
          if (!isFull() || panel.hidden || panel.classList.contains('eyedropper-veiled')) return;
          var under = ceiling() - panel.getBoundingClientRect().top;
          if (under > 0) (document.scrollingElement || document.documentElement).scrollTop -= under;
        }, ms);
      });
    }

    /* THE FULL DRAWER FITS UNDER THE HEADER. Expanding brings the drawer's END
     * on screen (revealPanelEnd), and a drawer taller than the room under the
     * sticky header took its top -- the grabber -- underneath the header to do
     * it, where a tap lands on the header instead: on a 664px phone Flip's grip
     * sat at y 3-27 behind a header at 6-66, and "I hit the drawer grip and
     * they stay" came back. So a full drawer taller than the room under the
     * header AND THE DOCK is capped to that room and
     * scrolls inside itself, with the grabber pinned at its top (CSS,
     * .detent-fit) -- so the grip is on screen and under the finger however
     * far down the person scrolls for Clear all pages. Measured after the
     * class lands, and again when the screen changes size (the iPhone's URL
     * bar, a rotation). Sheet widths only: the handle is display:none above
     * them, and the cap goes with it.
     *
     * Under the dock, not just the header: the dock sits right above the
     * drawer, and fitted under the header alone it landed in the header's band
     * -- glass over glass, its icons through the logo and Post. Measured as the
     * dock's distance above the drawer, which scrolling does not change. */
    function ceiling() {
      var top = stuckBottom();
      if (dock && dock.offsetParent !== null) {
        top += panel.getBoundingClientRect().top - dock.getBoundingClientRect().top;
      }
      return top + 4;
    }
    function fit() {
      panel.classList.remove('detent-fit');
      panel.style.removeProperty('--detent-room');
      if (!isFull() || panel.hidden || handle.offsetParent === null) return;
      var room = Math.floor(viewH() - ceiling() - 10);
      if (panel.getBoundingClientRect().height <= room) return;
      panel.style.setProperty('--detent-room', room + 'px');
      panel.classList.add('detent-fit');
    }
    function isFull() { return panel.classList.contains('detent-full'); }
    function setFull(v) {
      v = !!v;
      if (v === isFull()) return;
      panel.classList.toggle('detent-full', v);
      fit();
      if (v) reveal();
    }
    (window.visualViewport || window).addEventListener('resize', function () { if (isFull()) fit(); });

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
      if (panel.hidden) { panel.classList.remove('detent-full'); fit(); }
    }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  }

  /* SHRINK WITHOUT A JUMP. `change()` makes `box` shorter (the music drawer
   * going from Fine-tune back to Trim drops ~290px at a phone width). Scrolled
   * near the end, the page is suddenly shorter than where it stands, the
   * browser clamps the scroll in the same frame, and everything under the
   * finger leaps -- the owner, from an iPhone: "when you're in fine tune and
   * switch back to trim it snaps back". So hold the page at its old height
   * across the change, glide to where it would have clamped to, and let go.
   * Not scrolled that far, nothing moves and the hold is released at once. */
  function shrinkGently(box, change) {
    var scroller = document.scrollingElement || document.documentElement;
    var root = document.documentElement;
    var before = box.getBoundingClientRect().height;
    var held = scroller.scrollHeight;
    root.style.minHeight = held + 'px';
    change();
    var lost = before - box.getBoundingClientRect().height;
    var from = scroller.scrollTop;
    var to = Math.max(0, Math.min(from, held - lost - window.innerHeight));
    if (lost <= 0 || to >= from - 1) { root.style.minHeight = ''; return; }
    window.scrollTo({ top: to, behavior: 'smooth' });
    var t0 = Date.now();
    (function wait() {
      if (Math.abs(scroller.scrollTop - to) < 2 || Date.now() - t0 > 900) { root.style.minHeight = ''; return; }
      requestAnimationFrame(wait);
    }());
  }

  /* FOLLOW A CARD THAT GROWS WHILE OPEN. The media card is revealed as it
   * opens, and then a song or a photo lands in it: the file row, the trim
   * strip or the fit controls appear below what was revealed. Measured on
   * both editors once the drawer had settled (a picker takes seconds): a
   * song left 134-142px of the card below the screen, a photo 201-245px, at
   * 390x640, 390x844 and the owner's 402x874 alike. So growth while the card
   * is open brings its end on screen again, the way opening did, and with the
   * same re-asserts. `current()` is the open panel, or null while it is shut.
   *
   * NOT an open, a tab switch or Fine-tune: each has its own reveal already.
   * Each shows or hides one of the panels or the Fine-tune body, so that moves
   * the baseline instead of being followed -- watched on those elements, not
   * read off the card's size, because Photo and Music empty are the same
   * height and a switch between them resizes nothing (the first draft of this
   * kept the panel's name per resize, missed that switch, and so never followed
   * a song added after it).
   *
   * Never so far that the dock slides under the pinned header: that is
   * controls on top of controls (verify_ux's phone audit), and the reason
   * Fine-tune's own nudge stops at its waveform. Capped there, a short phone
   * may still leave the last row to scroll to; growth only ever scrolls
   * down. */
  function followGrowth(card, o) {
    if (!card || typeof ResizeObserver === 'undefined') return;
    var dock = o.dock || null, lastH = 0;
    function height() { return card.getBoundingClientRect().height; }
    function target() {
      var scroller = document.scrollingElement || document.documentElement;
      var top = scroller.scrollTop;
      var want = top + card.getBoundingClientRect().bottom - viewH() + 8;
      if (dock && dock.offsetParent !== null) {
        want = Math.min(want, top + dock.getBoundingClientRect().top - stuckBottom() - 4);
      }
      return Math.max(top, Math.min(want, scroller.scrollHeight - window.innerHeight));
    }
    function reveal() {
      var b = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto' : 'smooth';
      requestAnimationFrame(function () { window.scrollTo({ top: target(), behavior: b }); });
      [300, 700, 1200].forEach(function (ms) {
        setTimeout(function () {
          if (card.offsetParent === null) return;
          var scroller = document.scrollingElement || document.documentElement;
          var t = target();
          if (t > scroller.scrollTop + 1) scroller.scrollTop = t;
        }, ms);
      });
    }
    var moves = new MutationObserver(function () { lastH = height(); });
    [].forEach.call(card.querySelectorAll('#photoPanel, #musicPanel, #fineTuneBody'), function (m) {
      moves.observe(m, { attributes: true, attributeFilter: ['hidden'] });
    });
    new ResizeObserver(function () {
      var h = height(), grew = !!o.current() && lastH > 0 && h > lastH + 1;
      lastH = h;
      if (grew) reveal();
    }).observe(card);
  }

  window.SkriblDrawerDetent = { attach: attach, revealPanelEnd: revealPanelEnd, veil: veil, shrinkGently: shrinkGently,
                                followGrowth: followGrowth };
}());
