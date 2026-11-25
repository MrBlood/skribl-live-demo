/* Exclusive drawer controller — the ONE implementation of a machine both
 * editors had hand-rolled: named panels above/below a toolbar, at most one
 * open, the opener button reflecting state, and a scroll that reveals the
 * opened panel without stranding it under browser chrome.
 *
 * What was duplicated before this: Pad's openDrawer() (idMap + class toggling
 * + reduced-motion scroll) and Flip's openPop/closePop/openPhoto/openMusic/
 * hidePhoto/hideMusic/closeMediaDrawers/refitDrawer octet — eight functions
 * whose pairwise "close the others first" calls were the exclusivity rule
 * written out by hand, differently, twice. The editors keep their own hooks
 * (repositioning, waveforms, slider positioning); only the machine moved.
 *
 * skriblDrawers({
 *   panels: {
 *     name: {
 *       panel:  element or id            (required)
 *       button: element or id            (optional: gets openClass/aria)
 *       openClass: 'open'                (optional: class toggled on button)
 *       aria: true                       (optional: aria-expanded on button)
 *       onOpen(), onClose()              (optional hooks, run AFTER state set)
 *     }, ...
 *   },
 *   reveal(openPanelOrNull, name|null)   (required: editor's scroll behaviour)
 *   side: { canvas: id, move: selector } (optional: drawers beside the drawing
 *                                         on a desk, below; `move` is what
 *                                         sits under the drawing and slides)
 * }) -> { open(name|null), toggle(name), current(), isOpen(name) }
 *
 * open(name) closes whatever else is open (firing its onClose), opens `name`,
 * then calls reveal() exactly once — the hand-rolled versions refitted after
 * every intermediate close, scrolling panels that were about to vanish.
 * open(null) closes everything. Degrades safely: a name whose panel is
 * missing from the DOM is ignored, like every other lib here.
 */
(function () {
  'use strict';

  function _el(ref) {
    if (!ref) return null;
    return typeof ref === 'string' ? document.getElementById(ref) : ref;
  }

  var machines = [];                    // every editor's drawer set, for anyOpen()

  /* CLOSING THE LAST DRAWER SCROLLS HOME; IT DOES NOT JUMP (motion survey: the
   * whole screen moved 250px in one frame on both editors). The page was
   * scrolled to show the drawer, and hiding it shortens the page at once, so
   * the browser clamped the scroll to the top before the editor's smooth scroll
   * home could start. So the page keeps its height for as long as that scroll
   * takes -- the drawer's space is empty while the page glides down past it --
   * and gives it back when the top is reached, or after 800ms whatever happens.
   * Reduced motion keeps the jump, which is what its scroll home does anyway. */
  var heldBy = null;
  function holdHeight() {
    var root = document.documentElement;
    if (!(window.scrollY > 0) || heldBy) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    root.style.minHeight = root.scrollHeight + 'px';
    var release = function () {
      clearTimeout(heldBy); heldBy = null;
      window.removeEventListener('scroll', check);
      root.style.minHeight = '';
    };
    var check = function () { if (window.scrollY <= 0) release(); };
    window.addEventListener('scroll', check, { passive: true });
    heldBy = setTimeout(release, 800);
  }
  /* BESIDE THE DRAWING, ON A DESK (the owner's "all yes", Nov 25, to the
   * Drawers Beside the Drawing mock). With a mouse (hover and a fine pointer),
   * and where the drawing fits whole beside a phone-width drawer, a drawer
   * opens at the drawing's right, its top level with the drawing's, and the
   * drawing with what sits under it (cfg.side.move: the Pad's stage and dock,
   * Flip's stage, page strip and dock) slides left only as far as the drawer
   * needs; the header stays. Measured in the mock with Pen open: the Pad
   * showed 60-73% of its drawing on four desks and Flip 42-65%, the page
   * scrolled 335px; beside, 100% and nothing scrolled. Where the two don't
   * fit (a narrow window), or with a finger (a tablet, a phone), a drawer
   * opens below as it always has. The tools tray is no drawer here: it rises
   * over the dock and never moves the page. While a drawer is beside, the
   * page's reveals scroll its own column instead (lib/drawerdetent.js).
   * The slide is a relative offset (styles.css body.drawers-beside; each
   * of those elements is position: relative already), glided here with Web
   * Animations so the elements' own transitions stay theirs; the drawer
   * comes in from the right; under Reduce Motion both simply move. A window
   * resized while one is beside decides again, without gliding. */
  var SIDE_W = 392, SIDE_EDGE = 16, SIDE_MS = 280, SIDE_EASE = 'cubic-bezier(.22,.8,.24,1)';
  var selfResize = false;
  function still() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function sideBoxOf(panel) { return (panel.closest && panel.closest('.media-card')) || panel; }
  function movers(side) { return side.move ? Array.prototype.slice.call(document.querySelectorAll(side.move)) : []; }
  // Where a drawer beside would go, { shift, top }, or null where the two
  // don't fit. Read as if nothing had slid (the slide now, mid-glide too, is
  // the first mover's computed `left`); the top is the drawing's own with the
  // page at its top, where a drawer beside brings it (revealPanelEnd).
  function sideFit(side) {
    if (!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches)) return null;
    var cv = _el(side.canvas), m = movers(side);
    if (!cv || !cv.getClientRects().length) return null;
    var off = m.length ? (parseFloat(getComputedStyle(m[0]).left) || 0) : 0;
    var r = cv.getBoundingClientRect(), W = document.documentElement.clientWidth;
    var left = r.left - off, right = W - (r.right - off);
    var shift = Math.max(0, SIDE_W + 2 * SIDE_EDGE - right);
    if (shift > left - SIDE_EDGE) return null;
    return { shift: Math.ceil(shift), top: Math.round(Math.max(SIDE_EDGE, r.top + (window.scrollY || 0))) };
  }
  // The drawer `panel` beside the drawing where it fits, else below (and
  // null: none open). `glide`: an open or a close, not a resize.
  function sideApply(side, panel, glide) {
    var body = document.body, root = document.documentElement;
    var was = document.querySelector('.drawer-side');
    var box = panel ? sideBoxOf(panel) : null;
    var fit = box ? sideFit(side) : null;
    var prev = body.classList.contains('drawers-beside') ? (parseFloat(root.style.getPropertyValue('--side-shift')) || 0) : 0;
    var next = fit ? fit.shift : 0;
    if (was && (!fit || was !== box)) was.classList.remove('drawer-side');
    if (fit) {
      root.style.setProperty('--side-shift', next + 'px');
      root.style.setProperty('--side-top', fit.top + 'px');
      root.style.setProperty('--side-w', SIDE_W + 'px');
      if (!box.classList.contains('drawer-side')) {
        box.classList.add('drawer-side');
        box.scrollTop = 0;
        if (glide && !still() && box.animate) {
          box.animate([{ opacity: 0, transform: 'translateX(24px)' }, { opacity: 1, transform: 'none' }],
                      { duration: SIDE_MS, easing: SIDE_EASE });
        }
      }
      body.classList.add('drawers-beside');
    } else {
      body.classList.remove('drawers-beside');
      root.style.removeProperty('--side-shift');
    }
    if (prev !== next) slide(side, prev, next, glide);
  }
  // The drawing and what sits under it glide from one slide to the other; at
  // the end (or at once) everything that keeps the drawing's place hears a
  // resize (the brush rings, the eyedropper's lens), as lib/chromefit.js does.
  function slide(side, from, to, glide) {
    var m = movers(side);
    function done() {
      selfResize = true;
      try { window.dispatchEvent(new Event('resize')); } finally { selfResize = false; }
    }
    if (!glide || still() || !m.length || !m[0].animate) { done(); return; }
    var last = null;
    m.forEach(function (el) {
      last = el.animate([{ left: (-from) + 'px' }, { left: (-to) + 'px' }], { duration: SIDE_MS, easing: SIDE_EASE });
    });
    last.onfinish = done;
  }

  function skriblDrawers(cfg) {
    homeOnSettle();
    var panels = {};
    var order = [];
    Object.keys(cfg.panels || {}).forEach(function (name) {
      var d = cfg.panels[name];
      var panel = _el(d.panel);
      if (!panel) return;                 // absent in this page's DOM: skip
      panels[name] = {
        panel: panel,
        button: _el(d.button),
        openClass: d.openClass || null,
        aria: !!d.aria,
        onOpen: d.onOpen || null,
        onClose: d.onClose || null
      };
      order.push(name);
    });
    var currentName = null;

    function _set(name, open) {
      var d = panels[name];
      d.panel.hidden = !open;
      if (d.button) {
        if (d.openClass) d.button.classList.toggle(d.openClass, open);
        if (d.aria) d.button.setAttribute('aria-expanded', String(open));
      }
      var hook = open ? d.onOpen : d.onClose;
      if (hook) hook();
    }

    function open(name) {
      if (name != null && !panels[name]) name = null;
      var prev = currentName;
      if (prev === name) {
        if (name != null && cfg.reveal) cfg.reveal(panels[name].panel, name);
        return;
      }
      currentName = name;               // set BEFORE hooks: a hook asking
      if (name == null && prev != null) holdHeight();
      if (prev != null) _set(prev, false);   // current() must see the new state
      if (name != null) _set(name, true);
      if (cfg.side) sideApply(cfg.side, name != null && name !== 'tools' ? panels[name].panel : null, true);
      if (cfg.reveal) cfg.reveal(name != null ? panels[name].panel : null, name);
    }
    // A window resized with a drawer beside decides again (no glide), once
    // the editor has fitted its drawing to the new window.
    if (cfg.side) {
      window.addEventListener('resize', function () {
        if (selfResize || currentName == null || currentName === 'tools') return;
        requestAnimationFrame(function () {
          if (currentName != null && currentName !== 'tools' && panels[currentName]) sideApply(cfg.side, panels[currentName].panel, false);
        });
      });
    }

    var api = {
      open: open,
      toggle: function (name) { open(currentName === name ? null : name); },
      current: function () { return currentName; },
      isOpen: function (name) { return currentName === name; },
      // A drawer an editor-only script brings (Text's, editor_text.js), joined
      // after the machine was made: the Pad's machine is made in app.js, which
      // the link player loads too, and the player has no Text to carry.
      add: function (name, d) {
        var panel = _el(d && d.panel);
        if (!panel || panels[name]) return;
        panels[name] = { panel: panel, button: _el(d.button), openClass: d.openClass || null, aria: !!d.aria,
                         onOpen: d.onOpen || null, onClose: d.onClose || null };
        order.push(name);
      }
    };
    machines.push(api);
    return api;
  }

  /* THE PAGE GOES HOME WHEN NOTHING IS OPEN (owner, from an iPhone: the page
   * "bounced back too high ... stuck out of view about the header's size ...
   * and header menu is gone"). On a phone the editors scroll the PAGE to show
   * an open drawer, and nothing promised to bring it back: Flip never scrolled
   * on close at all, and the Pad's smooth scroll home can be cut short by the
   * next touch. With nothing open there is no reason for an editor page to be
   * scrolled -- it is built to fit one phone screen -- so once a scroll has
   * settled and no finger is down, it returns to the top.
   *
   * Phones only -- 640px and under, lib/sizeclass.js's compact boundary,
   * asked of the media query because the Pad does not load that lib -- since
   * a short desktop window can legitimately scroll. "Nothing open" means no drawer in any machine,
   * no visible modal or menu, and no text field being typed in, whose
   * keyboard moves the page on purpose. Never during a touch: it waits for
   * the scroll to stop, so it cannot fight a finger or a bounce. */
  var touches = 0, settle = null;
  function somethingOpen() {
    for (var i = 0; i < machines.length; i++) if (machines[i].current() != null) return true;
    var a = document.activeElement;
    if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable)) return true;
    var shown = document.querySelectorAll('[aria-modal="true"], .menu-overlay.open, .flip-menu');
    for (var j = 0; j < shown.length; j++) {
      var el = shown[j];
      if (!el.hidden && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden') return true;
    }
    return false;
  }
  function goHome() {
    settle = null;
    if (touches || !window.matchMedia('(max-width: 640px)').matches || somethingOpen()) return;
    var vv = window.visualViewport;
    if ((window.scrollY || 0) > 0 || (vv && vv.offsetTop > 0)) window.scrollTo(0, 0);
  }
  var homeWired = false;
  function homeOnSettle() {
    if (homeWired || typeof window === 'undefined') return;
    homeWired = true;
    var later = function () { clearTimeout(settle); settle = setTimeout(goHome, 250); };
    window.addEventListener('scroll', later, { passive: true });
    // Safari can slide its VISUAL viewport over the page -- the whole layout,
    // pinned header included, moves up -- and that reports here, not above.
    if (window.visualViewport) window.visualViewport.addEventListener('scroll', later, { passive: true });
    window.addEventListener('touchstart', function (e) { touches = e.touches.length; clearTimeout(settle); }, { passive: true });
    var lift = function (e) { touches = e.touches.length; if (!touches) later(); };
    window.addEventListener('touchend', lift, { passive: true });
    window.addEventListener('touchcancel', lift, { passive: true });
  }
  skriblDrawers.anyOpen = function () { return machines.some(function (m) { return m.current() != null; }); };
  // Whether a drawer is beside the drawing now (the checks ask).
  skriblDrawers.beside = function () { return !!document.querySelector('body.drawers-beside .drawer-side'); };

  if (typeof window !== 'undefined') window.skriblDrawers = skriblDrawers;
  if (typeof module !== 'undefined' && module.exports) module.exports = { skriblDrawers: skriblDrawers };
})();
