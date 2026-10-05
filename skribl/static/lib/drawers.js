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
      if (cfg.reveal) cfg.reveal(name != null ? panels[name].panel : null, name);
    }

    var api = {
      open: open,
      toggle: function (name) { open(currentName === name ? null : name); },
      current: function () { return currentName; },
      isOpen: function (name) { return currentName === name; }
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

  if (typeof window !== 'undefined') window.skriblDrawers = skriblDrawers;
  if (typeof module !== 'undefined' && module.exports) module.exports = { skriblDrawers: skriblDrawers };
})();
