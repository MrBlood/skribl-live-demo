/* The draw drawer's HALF detent — one implementation, both editors.
 *
 * WHY. On a phone the draw drawer covered most of the canvas, so choosing a
 * pen colour meant judging contrast against art you could no longer see
 * (owner picked this fix from the design audit, mocked before built). At
 * compact widths the drawer now OPENS at the half detent: the grabber, the
 * colour section, and the four tiles (lib/drawtiles.js) — the canvas stays
 * visible above. Pulling the grabber up, or opening a tile, expands to the
 * full drawer; pulling down returns to half; pulling down
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
   *
   * A DRAWER TALLER THAN THE SCREEN OPENS AT ITS TOP. Its end at the foot of
   * the screen took its top -- the tabs, the song, the strip -- up under the
   * header: with More open the music drawer is 1236px on the owner's 874px
   * phone, and it opened at Lock the length (the owner: "When you click the
   * media button and click music it open all the way to the bottom?"). So,
   * as followGrowth below already did for a song landing, never so far that
   * `dock` -- the bar that sits right above the drawer -- passes under the
   * pinned header; without one, never past the drawer's own top. A drawer
   * that fits still opens with its end on screen. The re-asserts put the
   * page back on that place whichever way it was carried (what is above the
   * drawer can still be settling its height as it opens), until the person
   * acts: a press or a key in the drawer, or a wheel or trackpad anywhere.
   */
  var revealGen = 0;   // a newer reveal calls off an older one's re-asserts
  function revealPanelEnd(panel, behavior, dock) {
    var mine = ++revealGen;
    function target() {
      var r = panel.getBoundingClientRect();
      var scroller = document.scrollingElement || document.documentElement;
      var top = scroller.scrollTop;
      var want = top + r.bottom - viewH() + 8;
      var lid = dock && dock.offsetParent !== null ? dock.getBoundingClientRect().top - 4 : r.top - 8;
      want = Math.min(want, top + lid - stuckBottom());
      var max = scroller.scrollHeight - window.innerHeight;
      return Math.max(0, Math.min(want, max));
    }
    // A press inside the drawer calls the re-asserts off: they settle the
    // device's own scrolls, and once the person acts the page is theirs. The
    // music drawer's Fine-tune, tapped within 1.2s of the drawer opening, made
    // it taller, and the last re-assert carried the page to its new end with
    // the switch just tapped under the header.
    // A wheel or a trackpad anywhere is a person scrolling on, too.
    var acted = false;
    function act() { acted = true; }
    panel.addEventListener('pointerdown', act);
    panel.addEventListener('keydown', act);
    window.addEventListener('wheel', act, { passive: true });
    setTimeout(function () {
      panel.removeEventListener('pointerdown', act); panel.removeEventListener('keydown', act);
      window.removeEventListener('wheel', act, { passive: true });
    }, 1300);
    requestAnimationFrame(function () {
      if (mine !== revealGen) return;
      window.scrollTo({ top: target(), behavior: behavior || 'smooth' });
    });
    [300, 700, 1200].forEach(function (ms) {
      setTimeout(function () {
        if (mine !== revealGen || acted || panel.hidden || panel.classList.contains('eyedropper-veiled')) return;
        var scroller = document.scrollingElement || document.documentElement, t = target();
        if (Math.abs(t - scroller.scrollTop) > 2) scroller.scrollTop = t;
      }, ms);
    });
  }

  /* PLAY SHOWS THE WHOLE DRAWING. With a drawer open the page can sit scrolled
   * down to it while Play is still in reach -- the phone's header is sticky,
   * and Flip's Space starts a Flip from anywhere -- and the drawing then played
   * with its top under the header. Measured: 26-45px of the Pad's on a 375x667
   * phone with any drawer open, 53px of a Flip's on a 402x874 one, and all but
   * the bottom 64px of a Flip's on a desk. The drawing heads the page in both
   * editors, so the top of the page is where it is whole. A no-op when it is
   * already in view; and it calls off a drawer's pending re-asserts above,
   * which would carry the page straight back down to the drawer. */
  function revealTop(el, behavior) {
    revealGen++;
    if (!el) return;
    var r = el.getBoundingClientRect();
    if (r.top >= stuckBottom() - 1 && r.bottom <= viewH() + 1) return;
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: behavior || (still ? 'auto' : 'smooth') });
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

    /* A TILE OPENED (lib/drawtiles.js). On a phone its choices need the full
     * drawer, and they need to be on screen: from half, go full (which
     * reveals); already full, re-fit to the new height and reveal again,
     * since the choices just added height below the fold. A tile closing only
     * re-fits. Desktop has no detent, and the page is left where it is. */
    panel.addEventListener('drawtile', function (e) {
      if (handle.offsetParent === null) return;
      if (!(e.detail && e.detail.open)) { requestAnimationFrame(fit); return; }
      if (!isFull()) { setFull(true); return; }
      fit();
      reveal();
    });

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
   * NOT an open, a tab switch or the music drawer's More: each has its own
   * reveal already. Each shows or hides one of the panels, or opens or closes
   * More (#musicDetail's data-level, set before More shows or hides), so
   * that moves the baseline instead of being followed -- watched
   * on those elements, not read off the card's size, because Photo and Music
   * empty are the same height and a switch between them resizes nothing (the
   * first draft of this kept the panel's name per resize, missed that switch,
   * and so never followed a song added after it).
   *
   * Never so far that the dock slides under the pinned header: that is
   * controls on top of controls (verify_ux's phone audit), and the reason
   * the music drawer's More stops its own nudge short of the header. Capped
   * there, a short phone may still leave the last row to scroll to; growth
   * only ever scrolls down, but for one thing.
   *
   * THE CAP IS HELD, NOT ONLY AIMED AT. On a 390x640 phone a photo could
   * leave the page past it, the dock 1-9px under the header -- in anything
   * from none of eight runs to six of six, batch to batch on one box: the
   * photo's row changes height while the glide is under way, and the
   * browser's scroll anchoring and the glide itself carry the page on past
   * the target. With anchoring switched off, two runs of six still went past,
   * so the re-asserts take back the drift whatever moved it. There is little room for one: of
   * the three phones verify_parity drives, only the Pad's photo at 390x640
   * can scroll past the cap at all, and by 13px.
   *
   * A DRIFT, NOT A PERSON'S SCROLL. The take-back stood for 1.2s after any
   * growth and fought whoever scrolled on in that time: a song added and the
   * page scrolled to its end came straight back to the cap, 231px, in three
   * runs of three. A drift is the few px a glide overshoots; a scroll is a
   * screenful. Past DRIFT the page is where the person put it, and it stays.
   *
   * NOR BEATS OPENING AS A BEAT LANDS (lib/musicdrawer.js): its height is
   * left out of the card's, so the page does not move by itself a moment
   * after Skribl hears the beat or a tap settles it, under a finger reaching
   * for the timeline (it scrolled 46px on the Pad and 22px on Flip, and
   * verify_musicbeat's drags on Flip let go a bar off). Beats glides open,
   * and what is under it glides down; a song landing with it is followed.
   *
   * A PERSON WHO SCROLLS BACK UP IS LEFT THERE TOO. The take-back only ever
   * pushes down, so a scroll up to the drawing as a song landed came straight
   * back to the drawer's end, 300px in one frame at the next re-assert, on a
   * desk's wheel and a phone's finger alike. As the opening's re-asserts do
   * (revealPanelEnd above), a wheel, a touch, a press or a key anywhere while
   * they are due calls them off: once the person acts, the page is theirs. */
  var DRIFT = 24;
  var ACTS = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
  function followGrowth(card, o) {
    if (!card || typeof ResizeObserver === 'undefined') return;
    var dock = o.dock || null, lastH = 0, gen = 0, beats = card.querySelector('#musicBeatsRow');
    function height() {
      return card.getBoundingClientRect().height - (beats && !beats.hidden ? beats.getBoundingClientRect().height : 0);
    }
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
      var mine = ++gen;
      // A GROWTH IS THE NEWER REVEAL, so it calls off the opening's
      // re-asserts (revealPanelEnd above), which aimed at the drawer's end
      // before it grew. A song landing within 1.2s of the drawer opening had
      // them snap this glide short, the page 260px in one frame on Flip, then
      // hold the page a pixel off this cap (the panel's end, not the card's).
      revealGen++;
      function act() { if (mine === gen) gen++; }
      var opts = { capture: true, passive: true };
      ACTS.forEach(function (n) { window.addEventListener(n, act, opts); });
      setTimeout(function () { ACTS.forEach(function (n) { window.removeEventListener(n, act, opts); }); }, 1300);
      var b = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto' : 'smooth';
      requestAnimationFrame(function () { window.scrollTo({ top: target(), behavior: b }); });
      [300, 700, 1200].forEach(function (ms) {
        setTimeout(function () {
          if (mine !== gen || card.offsetParent === null) return;
          var scroller = document.scrollingElement || document.documentElement;
          var t = target();
          if (t > scroller.scrollTop + 1) { scroller.scrollTop = t; return; }
          if (!dock || dock.offsetParent === null) return;
          var over = stuckBottom() + 4 - dock.getBoundingClientRect().top;
          if (over > 1 && over <= DRIFT) scroller.scrollTop -= over;
        }, ms);
      });
    }
    // A move of the baseline also calls off the last growth's re-asserts: a
    // level picked within 1.2s of a song landing (the levels More replaced)
    // had them chase the taller card's end, the switch just tapped scrolled
    // away under the header.
    var moves = new MutationObserver(function () { lastH = height(); gen++; });
    [].forEach.call(card.querySelectorAll('#photoPanel, #musicPanel'), function (m) {
      moves.observe(m, { attributes: true, attributeFilter: ['hidden'] });
    });
    // Only More: #musicDetail un-hiding is a song landing, which IS followed.
    var lv = card.querySelector('#musicDetail');
    if (lv) moves.observe(lv, { attributes: true, attributeFilter: ['data-level'] });
    new ResizeObserver(function () {
      var h = height(), grew = !!o.current() && lastH > 0 && h > lastH + 1;
      lastH = h;
      if (grew) reveal();
    }).observe(card);
  }

  window.SkriblDrawerDetent = { attach: attach, revealPanelEnd: revealPanelEnd, revealTop: revealTop, veil: veil,
                                shrinkGently: shrinkGently, followGrowth: followGrowth, stuckBottom: stuckBottom };
}());
