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
 * }) -> { open(name|null), toggle(name), current(), isOpen(name), add(name, d), side(s) }
 *
 * side({ canvas: id, move: selector }) puts the drawers beside the drawing on
 * a desk (below); `move` is what sits under the drawing and slides with it.
 * Each editor's own script says it, as add() is said: the link player loads
 * the Pad's machine and has no drawer to put anywhere.
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
   * drawing with what sits under it (side()'s move: the Pad's stage and dock,
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
  /* A TAB ON THE DRAWER (the owner, Nov 26: "Put a tab on the drawer in
   * addition to clicking pen again (and other drawers)"; then "All yes on
   * A", taken for the Drawer Tab mock's A, DECISIONS.md). Beside the
   * drawing, the drawer wears a tab on its edge facing the drawing, near its
   * top, that closes it: the drawer's own paper and line, joined to it, with
   * a › that points the way the drawer goes (styles.css .drawer-tab). It
   * stands SIDE_TAB out of the drawer, and the drawing gives it that room as
   * it gives the drawer its own: it slides that much further and clears the
   * tab by SIDE_EDGE. A button named "Close the drawer", which the keyboard
   * reaches just before the drawer; closed from the keyboard, the drawer's
   * own button takes the focus back. One tab per editor, made when side()
   * is said and moved to sit before whichever drawer is beside; it comes and
   * goes with the drawer, as one piece. */
  var SIDE_TAB = 24;
  var selfResize = false;
  function still() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function sideBoxOf(panel) { return (panel.closest && panel.closest('.media-card')) || panel; }
  function movers(side) { return side.move ? Array.prototype.slice.call(document.querySelectorAll(side.move)) : []; }
  // Where a drawer beside would go, { shift, top }, or null where the two
  // don't fit. Read as if nothing had slid (the slide now, mid-glide too, is
  // the first mover's computed `left`); the top is the drawing's own with the
  // page at its top, where a drawer beside brings it (revealPanelEnd).
  // Where a drawer held to the screen ends on the right: the screen's edge
  // less the gutter the page keeps for a scrollbar (styles.css, html's
  // scrollbar-gutter, both edges: 10px on a desk, which clientWidth does not
  // count). Measured, so the drawing clears the drawer by SIDE_EDGE, not 6px.
  function fixedRight() {
    var p = document.createElement('div');
    p.style.cssText = 'position:fixed;top:0;right:0;width:0;height:0;visibility:hidden;pointer-events:none';
    document.body.appendChild(p);
    var x = p.getBoundingClientRect().left;
    p.remove();
    return x;
  }
  function sideFit(side) {
    if (!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches)) return null;
    var cv = _el(side.canvas), m = movers(side);
    if (!cv || !cv.getClientRects().length) return null;
    var off = m.length ? (parseFloat(getComputedStyle(m[0]).left) || 0) : 0;
    var r = cv.getBoundingClientRect(), W = fixedRight();
    var left = r.left - off, right = W - (r.right - off);
    var shift = Math.max(0, SIDE_W + SIDE_TAB + 2 * SIDE_EDGE - right);
    if (shift > left - SIDE_EDGE) return null;
    return { shift: Math.ceil(shift), top: Math.round(Math.max(SIDE_EDGE, r.top + (window.scrollY || 0))) };
  }
  /* ROOM FOR THE DRAWER (the owner's "All yes", Nov 26, to the Room for the
   * Drawer mock). Where the drawing doesn't fit whole beside a drawer by
   * sliding alone (a wide 16:9 drawing fills a desk's width), it gets a
   * little smaller as well, the least it needs and never past SIDE_MIN of
   * its width, a quarter off at most: past that (a narrow window) a drawer
   * opens below as before. In a maximised desk window a wide drawing gives
   * up 4 to 15%; in full screen on a 16:10 desk, about 22. The room is taken out of the drawing's row as
   * padding, half each side (side.row; each editor's own fit takes its row's
   * padding off the room it has), so the drawing stays centred over its dock
   * as both slide, and the editor fits it again at once (side.fit). The
   * change glides with the slide (FLIP on side.glide, added to whatever
   * transform it has), and closing the drawer gives the room back the same
   * way. Measured in the mock: a wide drawing 88% of its width on a
   * 1366x768 desk, 92% on 1920x1080, 58% and 73% of it on screen before. */
  var SIDE_MIN = 0.75;
  var room = 0, roomPad = null, glidingTill = 0, glideSize = '';
  function rowOf(side) { return side.row ? document.querySelector(side.row) : null; }
  function setRoom(side, px) {
    var row = rowOf(side);
    if (!row || px === room) return;
    if (px > 0) {
      if (roomPad == null) { var cs = getComputedStyle(row); roomPad = [parseFloat(cs.paddingLeft) || 0, parseFloat(cs.paddingRight) || 0]; }
      row.style.paddingLeft = (roomPad[0] + px / 2) + 'px';
      row.style.paddingRight = (roomPad[1] + px / 2) + 'px';
    } else {
      row.style.paddingLeft = '';
      row.style.paddingRight = '';
      roomPad = null;
    }
    room = px;
    if (side.fit) side.fit();
  }
  // The px to take out of the drawing's row so that it sits beside a drawer,
  // read with none taken: 0 where it fits as it is, null where it would give
  // up more than SIDE_MIN allows (or nothing points with a mouse). The row
  // has room to spare beside a drawing its height holds back, so what comes
  // out of it is what brings the row's own width down to the drawing's most.
  function roomNeed(side) {
    if (!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches)) return null;
    var cv = _el(side.canvas), row = rowOf(side);
    if (!cv || !cv.getClientRects().length || !row) return 0;
    var w = cv.getBoundingClientRect().width, most = fixedRight() - SIDE_W - SIDE_TAB - 3 * SIDE_EDGE;
    if (w <= most) return 0;
    if (most < SIDE_MIN * w) return null;
    var cs = getComputedStyle(row);
    var inside = row.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    return Math.max(0, Math.ceil(inside - most)) + 2;
  }
  // Where side.glide sits in its row, by its centre, and how big it is: the
  // two ends of the drawing's glide when the room changes.
  function inRow(side) {
    var g = side.glide ? document.querySelector(side.glide) : null, row = rowOf(side);
    if (!g || !row || !g.getClientRects().length) return null;
    var a = g.getBoundingClientRect(), b = row.getBoundingClientRect();
    return { el: g, x: a.left - b.left + a.width / 2, y: a.top - b.top + a.height / 2, w: a.width };
  }
  function glideRoom(from, to) {
    if (!from || !to || !to.w || !to.el.animate || still()) return;
    var s = from.w / to.w, dx = from.x - to.x, dy = from.y - to.y;
    if (Math.abs(s - 1) < 0.002 && Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
    to.el.animate([{ transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + s + ')' }, { transform: 'none' }],
                  { duration: SIDE_MS, easing: SIDE_EASE, composite: 'add' });
  }
  // FLIP'S PAGE STRIP RUNS UNDER THE DRAWER (the owner's same "All yes", from
  // "on flip the bottom slides would extend under the right side window"):
  // what side.under names reaches right to the drawer's own right edge, and
  // the drawer ends above it, scrolling inside itself when it is taller.
  // Its end glides with the slide, out to the drawer's edge and back again.
  var underNow = [];                    // [element, its own width, how far it reaches]
  function underApply(side, box, fit, glide) {
    var els = side.under ? Array.prototype.slice.call(document.querySelectorAll(side.under)) : [];
    if (!els.length) return;
    var was = underNow;
    underNow = [];
    els.forEach(function (el) {
      el.getAnimations && el.getAnimations().forEach(function (a) { if (a.id === 'under') a.cancel(); });
      el.style.width = ''; el.style.maxWidth = ''; el.style.marginRight = '';
    });
    document.documentElement.style.removeProperty('--side-max');
    var W = fixedRight(), top = Infinity;
    if (fit && box) {
      els.forEach(function (el) {
        var r = el.getBoundingClientRect(), now = parseFloat(getComputedStyle(el).left) || 0;
        var reach = Math.max(0, Math.floor(W - SIDE_EDGE - (r.right - now - fit.shift)));
        // (a pixel's rounding on a decision without a glide is kept as it was, as the slide's is)
        was.forEach(function (u) { if (!glide && u[0] === el && Math.abs(u[2] - reach) <= 1) reach = u[2]; });
        top = Math.min(top, r.top + (window.scrollY || 0));
        if (reach < 1) return;
        el.style.maxWidth = 'none';
        el.style.width = (r.width + reach) + 'px';
        el.style.marginRight = (-reach) + 'px';
        underNow.push([el, r.width, reach]);
      });
      // A custom property the drawer's rule reads (styles.css), not its own
      // max-height: Text's sheet sets that itself as a keyboard comes and goes.
      if (top < Infinity) document.documentElement.style.setProperty('--side-max', Math.max(120, Math.floor(top - fit.top - 12)) + 'px');
    }
    if (!glide || still()) return;
    els.forEach(function (el) {
      var a = null, b = null;
      was.forEach(function (u) { if (u[0] === el) a = u; });
      underNow.forEach(function (u) { if (u[0] === el) b = u; });
      if (!el.animate || (!a && !b)) return;
      var own = (b || a)[1];
      var at = function (u) { return u ? { width: (u[1] + u[2]) + 'px', marginRight: (-u[2]) + 'px' } : { width: own + 'px', marginRight: '0px' }; };
      if (!b) el.style.maxWidth = 'none';   // held while it glides home, as wide as it was
      var go = el.animate([at(a), at(b)], { duration: SIDE_MS, easing: SIDE_EASE, id: 'under' });
      if (!b) go.onfinish = function () { if (underNow.indexOf(el) < 0) el.style.maxWidth = ''; };
    });
  }
  /* A DRAWER CLOSED BESIDE THE DRAWING SLIDES AWAY (the same mock: "Click the
   * tab, and the drawer slides away as the drawing glides back"). It vanished
   * in one frame while the drawing glided back. Closed to nothing now, it
   * leaves the way it came in, fading as it moves 24px right, its tab with
   * it. Its panel is hidden at once, as it always was (current() and `hidden`
   * say closed): the drawer is only drawn where it was until the glide ends,
   * inert, so nothing in it can be reached or clicked. A switch to another
   * drawer stays a swap; Reduce Motion, a resize, and a drawer below don't
   * glide. */
  var leaving = null;
  // How a drawer beside looks now, read before its panel is hidden: its box,
  // the panel inside it where that is another (Photo's, Music's), how each
  // is displayed, its height and its scroll.
  function sideNow(panel) {
    var box = panel ? sideBoxOf(panel) : null;
    if (!box || !box.classList.contains('drawer-side')) return null;
    var inner = panel !== box ? panel : null;
    return { box: box, inner: inner, show: getComputedStyle(box).display, showInner: inner ? getComputedStyle(inner).display : '',
             h: box.getBoundingClientRect().height, top: box.scrollTop, inert: box.inert };
  }
  var SIDE_OUT = [{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'translateX(24px)' }];
  function leave(g, tab) {
    var box = g.box, l = { g: g, tab: tab, anims: [] };
    box.classList.add('drawer-leaving');
    box.style.setProperty('display', g.show, 'important');
    if (g.inner) g.inner.style.setProperty('display', g.showInner, 'important');
    box.style.height = g.h + 'px';
    box.scrollTop = g.top;
    box.inert = true;
    l.anims.push(box.animate(SIDE_OUT, { duration: SIDE_MS, easing: SIDE_EASE, fill: 'forwards' }));
    if (tab) {
      tab.hidden = false;
      tab.inert = true;
      l.anims.push(tab.animate(SIDE_OUT, { duration: SIDE_MS, easing: SIDE_EASE, fill: 'forwards' }));
    }
    leaving = l;
    l.anims[0].onfinish = function () { if (leaving === l) stopLeaving(); };
  }
  // The glide out ends (or is cut short by the next decision): the drawer is
  // its panel's again, hidden, and the tab goes with it.
  function stopLeaving() {
    var l = leaving;
    if (!l) return;
    leaving = null;
    l.anims.forEach(function (a) { a.cancel(); });
    var box = l.g.box;
    box.classList.remove('drawer-leaving');
    box.style.removeProperty('display');
    if (l.g.inner) l.g.inner.style.removeProperty('display');
    box.style.height = '';
    box.inert = l.g.inert;
    if (l.tab) { l.tab.inert = false; l.tab.hidden = true; }
  }
  // The drawer `panel` beside the drawing where it fits, else below (and
  // null: none open). `glide`: an open or a close, not a resize. `going`:
  // the drawer that was beside, as sideNow() read it before it closed.
  function sideApply(side, panel, glide, going) {
    var body = document.body, root = document.documentElement;
    stopLeaving();
    var was = document.querySelector('.drawer-side');
    var box = panel ? sideBoxOf(panel) : null, tab = side.tab || null;
    if (glide && !still()) { glidingTill = Date.now() + SIDE_MS; glideSize = window.innerWidth + 'x' + window.innerHeight; }
    // A drawer just opened sits under the dock in the page's flow until it
    // goes beside, a layout never painted: the drawing is read with it lifted
    // out, as it is on the screen now, and put back before anything paints.
    // (Read with it in, a smaller drawing's top was where it would sit with a
    // drawer below, and the drawer beside stood 36px above it.)
    var lifted = box && !box.classList.contains('drawer-side') ? box : null;
    if (lifted) lifted.style.setProperty('position', 'absolute', 'important');
    var from = glide ? inRow(side) : null, roomWas = room;
    // What the drawing needs is read with no room taken; then taken, fitted.
    setRoom(side, 0);
    var need = box ? roomNeed(side) : null;
    // Decided again without a glide (a resize, or the editor's chrome changing
    // size: Flip's strip reaching under the drawer is one), a pixel or two
    // either way is the layout's own rounding, not a move: kept as it was, the
    // drawing and the strip wobbled a pixel left and back after the glide.
    if (!glide && need && roomWas && Math.abs(need - roomWas) <= 2) need = roomWas;
    if (need) setRoom(side, need);
    var fit = box && need != null ? sideFit(side) : null;
    if (!fit) setRoom(side, 0);
    if (lifted) lifted.style.removeProperty('position');
    var prev = body.classList.contains('drawers-beside') ? (parseFloat(root.style.getPropertyValue('--side-shift')) || 0) : 0;
    var next = fit ? fit.shift : 0;
    if (fit && !glide && prev && Math.abs(next - prev) <= 1) next = fit.shift = prev;
    if (was && (!fit || was !== box)) was.classList.remove('drawer-side');
    if (fit) {
      root.style.setProperty('--side-shift', next + 'px');
      root.style.setProperty('--side-top', fit.top + 'px');
      root.style.setProperty('--side-w', SIDE_W + 'px');
      // The tab sits just before the drawer, for the keyboard's order.
      if (tab) {
        if (tab.nextSibling !== box) box.parentNode.insertBefore(tab, box);
        tab.hidden = false;
      }
      if (!box.classList.contains('drawer-side')) {
        box.classList.add('drawer-side');
        box.scrollTop = 0;
        if (glide && !still() && box.animate) {
          var into = [{ opacity: 0, transform: 'translateX(24px)' }, { opacity: 1, transform: 'none' }];
          box.animate(into, { duration: SIDE_MS, easing: SIDE_EASE });
          if (tab && tab.animate) tab.animate(into, { duration: SIDE_MS, easing: SIDE_EASE });
        }
      }
      body.classList.add('drawers-beside');
    } else {
      if (tab) tab.hidden = true;
      body.classList.remove('drawers-beside');
      root.style.removeProperty('--side-shift');
    }
    // The drawing glides to where it now sits from where it was.
    if (room !== roomWas) glideRoom(from, inRow(side));
    underApply(side, fit ? box : null, fit, glide);
    if (prev !== next) slide(side, prev, next, glide);
    // Closed to nothing beside it, the drawer that was there slides away.
    if (!fit && going && glide && !still() && going.box.animate) leave(going, tab);
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
      var going = side && prev != null ? sideNow(panels[prev].panel) : null;   // before it is hidden
      if (prev != null) _set(prev, false);   // current() must see the new state
      if (name != null) _set(name, true);
      if (side) sideApply(side, name != null && name !== 'tools' ? panels[name].panel : null, true, going);
      if (cfg.reveal) cfg.reveal(name != null ? panels[name].panel : null, name);
    }
    // Beside the drawing on a desk, once the editor says what slides (side()).
    // A window resized with a drawer beside decides again (no glide), once
    // the editor has fitted its drawing to the new window.
    var side = null;
    // A resize heard while the drawing and the strip glide (the strip's own
    // growing is heard as one, through the editor's watch on its chrome)
    // waits for the glide's end, and then decides again only if the window's
    // size is not what it was: decided again mid-glide, the strip landed at
    // once, and after it, a pixel off what the glide had decided.
    var later = null, tab = null;
    // The drawer's tab (SIDE_TAB, above): closes whichever drawer is beside.
    // Pressed from the keyboard (a click with no pointer behind it), the
    // focus goes back to that drawer's own button, where it came from.
    function makeTab() {
      var t = document.createElement('button');
      t.type = 'button';
      t.className = 'drawer-tab';
      t.setAttribute('aria-label', 'Close the drawer');
      t.title = 'Close the drawer';
      t.hidden = true;
      var mark = window.SkriblMarks && window.SkriblMarks.get('chev');
      if (mark) t.appendChild(mark); else t.textContent = '›';
      t.addEventListener('click', function (e) {
        var d = currentName != null ? panels[currentName] : null;
        var keys = e.detail === 0 && document.activeElement === t;
        open(null);
        if (keys && d && d.button && d.button.focus) d.button.focus({ preventScroll: true });
      });
      document.body.appendChild(t);
      return t;
    }
    function sideOn(s) {
      if (!tab) tab = makeTab();
      s.tab = tab;
      if (!side) {
        var again = function () {
          if (currentName != null && currentName !== 'tools' && panels[currentName]) sideApply(side, panels[currentName].panel, false);
        };
        window.addEventListener('resize', function () {
          if (selfResize || currentName == null || currentName === 'tools') return;
          var wait = glidingTill - Date.now();
          clearTimeout(later);
          if (wait > 0) later = setTimeout(function () { if (window.innerWidth + 'x' + window.innerHeight !== glideSize) again(); }, wait + 20);
          else requestAnimationFrame(again);
        });
      }
      side = s;
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
      },
      side: sideOn
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
