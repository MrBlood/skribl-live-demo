/* Sheets that go away — one swipe, every bottom sheet.
 *
 * WHY (v317, the owner on a phone): "menus should always go down or away
 * easily. Some of these menus, I hit the drawer grip and they stay, I swipe it
 * down and accidentally reload the page." Only the Pad's ⋯ menu could be
 * swiped down, and even that one listened passively -- so the page scrolled
 * under the finger at the same time, and at the top of the page a downward
 * swipe is the browser's pull-to-refresh. Every other sheet (export, post,
 * report, Flip's ⋯, the page menu, saved drafts) had no swipe at all, and the
 * page menu's grabber did nothing when tapped.
 *
 * WHAT A SHEET GETS:
 *   - the grabber, tapped, closes it;
 *   - a downward drag from the grabber or the sheet's top strip follows the
 *     finger and closes past CLOSE_AT, or on a quick flick; less snaps back;
 *   - a downward drag in the sheet's own list does the same once that list is
 *     scrolled to its top -- the gesture every phone's sheets use -- and
 *     scrolls the list otherwise;
 *   - while it drags, the touch is the sheet's: preventDefault on a
 *     NON-passive touchmove is what stops the page scrolling behind it and the
 *     browser starting a reload. (The CSS overscroll rules in styles.css and
 *     pagemenu.css are the second belt.)
 *
 * ONLY WHILE IT IS A BOTTOM SHEET. The same element is a dropdown on a desktop
 * (the Pad's ⋯) or a centred card; a drag there means nothing. The test is
 * geometry, not a media query, so no width breakpoint has to be kept in step:
 * a sheet whose box meets the bottom of the screen is one.
 *
 * A CANCELLED touch resets, it never closes: a gesture the OS took away must
 * not finish a dismissal the person never finished (verify_tools V214c).
 *
 * AND IT EASES AWAY (v317, the owner: "when those menus close shouldn't they
 * ease closed?"). The Pad's ⋯ menu, the export sheets and Post always slid
 * down; Flip's ⋯ menu, the report sheet, the page menu and your drafts just
 * vanished, and a sheet swiped past the line jumped out from under the finger.
 * slideOut() carries a bottom sheet the rest of the way down -- from wherever
 * the finger left it -- and fades its dim with it, then runs the surface's own
 * hide. Those surfaces call it from their close, so a tap on the grabber, the
 * dim, a row or Escape eases the same way a swipe does. Reduced motion, or a
 * sheet that is not a bottom sheet right now, hides at once. */
(function () {
  'use strict';

  var GRAB_ZONE = 60;    // px from the sheet's top that always drags
  var CLOSE_AT = 80;     // px of pull that closes
  var FLICK = 0.5;       // px/ms: a fast short pull closes too
  var SLOP = 6;          // px before a touch is a drag, so taps stay taps

  function point(e) {
    if (window.SkriblEventPoint) return window.SkriblEventPoint.at(e);
    return (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0]) || e;
  }

  // Its bottom edge ON the screen's bottom edge -- not merely past it: a
  // dropdown taller than a landscape phone runs off the bottom and is still a
  // dropdown (v317 review). A sheet being dragged sits lower by the drag.
  function isBottomSheet(sheet) {
    var r = sheet.getBoundingClientRect();
    return r.width > 0 && Math.abs(r.bottom - (sheet._dragDy || 0) - window.innerHeight) <= 3;
  }

  // The nearest element between the touch and the sheet that scrolls.
  function scrollerFor(target, sheet) {
    for (var el = target; el; el = el.parentElement) {
      if (el.scrollHeight > el.clientHeight + 1) {
        var oy = getComputedStyle(el).overflowY;
        if (oy === 'auto' || oy === 'scroll') return el;
      }
      if (el === sheet) break;
    }
    return null;
  }

  var SLIDE_MS = 220;

  /* An entrance still running owns the transform -- a CSS keyframe (Flip's
     menu, the page menu) or slideIn's animation -- so a drag or a close that
     starts during it would be ignored and then jump. Land it first. */
  function settle(sheet) {
    if (typeof sheet.getAnimations !== 'function') return;
    sheet.getAnimations().forEach(function (a) {
      if (typeof CSSTransition === 'undefined' || !(a instanceof CSSTransition)) {
        try { a.finish(); } catch (e) {}
      }
    });
  }

  function unslide(sheet) {
    clearTimeout(sheet._slideT);
    sheet._slideT = null;
    sheet.style.transition = '';
    sheet.style.transform = '';
    sheet.style.animation = '';
    sheet.style.pointerEvents = '';
    sheet._dragDy = 0;
    (sheet._slideFades || []).forEach(function (f) {
      f.el.style.transition = '';
      f.el.style[f.prop] = '';
    });
    sheet._slideFades = null;
  }

  /* opts: { done: the surface's hide, fade: [dims to fade out],
             fadeBg: [dims whose own background is the dim, the sheet inside] }
     A second call while one is running lets the first finish. */
  function slideOut(sheet, opts) {
    opts = opts || {};
    var done = opts.done || function () {};
    if (!sheet) { done(); return; }
    if (sheet._slideT) return;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    settle(sheet);   // an entrance still running is landed before it is measured
    if (reduce || sheet.hidden || !isBottomSheet(sheet)) { unslide(sheet); done(); return; }
    var rest = window.innerHeight - sheet.getBoundingClientRect().top + 12;
    // ONE MATRIX EACH END. The start is whatever the sheet shows now -- its
    // resting transform, a finger's drag on top of it -- read back as the
    // computed matrix; the end is that matrix moved down. A list like
    // "matrix(...) translateY(140px)" -> "... translateY(393px)" does not
    // interpolate in Chrome (it jumped at the half-way mark on the report
    // sheet), and a single matrix always does.
    var cur = getComputedStyle(sheet).transform || 'none';
    var m = /^matrix\(([^)]+)\)$/.exec(cur);
    if (!m && cur !== 'none') { unslide(sheet); done(); return; }   // a 3-D sheet: no slide, no jump
    var v = m ? m[1].split(',').map(parseFloat) : [1, 0, 0, 1, 0, 0];
    var mat = function (ty) { return 'matrix(' + [v[0], v[1], v[2], v[3], v[4], ty].join(', ') + ')'; };
    // An entrance keyframe would otherwise own the transform (Flip's menu, the
    // page menu); pin the start, then ease to the bottom edge and past it.
    sheet.style.animation = 'none';
    sheet.style.transition = 'none';
    sheet.style.transform = mat(v[5]);
    sheet.style.pointerEvents = 'none';   // leaving: its rows take no more taps
    void sheet.offsetHeight;
    // Moving from the first frame: an ease-in sat still long enough on a
    // short sheet to read as a stall, and a flicked sheet should keep going.
    sheet.style.transition = 'transform ' + SLIDE_MS + 'ms cubic-bezier(.3, .1, .4, 1)';
    sheet.style.transform = mat(v[5] + rest);
    var fades = [];
    (opts.fade || []).forEach(function (el) { if (el) fades.push({ el: el, prop: 'opacity', to: '0' }); });
    (opts.fadeBg || []).forEach(function (el) { if (el) fades.push({ el: el, prop: 'backgroundColor', to: 'transparent' }); });
    fades.forEach(function (f) {
      f.el.style.transition = (f.prop === 'opacity' ? 'opacity ' : 'background-color ') + SLIDE_MS + 'ms ease';
      f.el.style[f.prop] = f.to;
    });
    sheet._slideFades = fades;
    sheet._slideT = setTimeout(function () {
      sheet._slideT = null;
      done();
      unslide(sheet);
    }, SLIDE_MS);
  }

  /* The way in, mirroring slideOut: a bottom sheet rises from below its own
     resting place. Driven here, not by a stylesheet keyframe, so a page that
     has no such sheet -- the player -- carries none of it (v317; the drafts
     sheet is the one that uses it). Reduced motion, or not a bottom sheet:
     it is simply there. */
  function slideIn(sheet) {
    if (!sheet || sheet.hidden || typeof sheet.animate !== 'function') return;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !isBottomSheet(sheet)) return;
    var cur = getComputedStyle(sheet).transform || 'none';
    var m = /^matrix\(([^)]+)\)$/.exec(cur);
    if (!m && cur !== 'none') return;
    var v = m ? m[1].split(',').map(parseFloat) : [1, 0, 0, 1, 0, 0];
    var h = sheet.getBoundingClientRect().height;
    var mat = function (ty) { return 'matrix(' + [v[0], v[1], v[2], v[3], v[4], ty].join(', ') + ')'; };
    sheet.animate([{ transform: mat(v[5] + h) }, { transform: mat(v[5]) }],
                  { duration: 300, easing: 'cubic-bezier(0.4, 0.0, 0.2, 1.1)' });
  }

  function attach(sheet, opts) {
    if (!sheet || sheet._skriblSheetSwipe) return;
    sheet._skriblSheetSwipe = true;
    opts = opts || {};
    var close = opts.close;
    var handle = opts.handle || null;
    var canClose = opts.canClose || function () { return true; };

    var tracking = false, dragging = false, fromTop = false, scroller = null;
    var sx = 0, sy = 0, dy = 0, lastY = 0, lastT = 0, vel = 0, base = '';

    function reset() {
      tracking = false; dragging = false; dy = 0; vel = 0;
      sheet._dragDy = 0;
      sheet.style.transition = '';
      sheet.style.transform = '';
    }

    function onTouchStart(e) {
      // A second finger mid-drag ends the drag and puts the sheet back; it
      // used to leave it stuck part-way down with nothing to clear it.
      if (dragging) reset();
      tracking = false;
      if (!e.touches || e.touches.length !== 1 || !canClose() || !isBottomSheet(sheet)) return;
      // A slider or a text field owns its own drag.
      if (e.target.closest && e.target.closest('input, textarea, select')) return;
      var p = point(e);
      tracking = true; dragging = false; dy = 0; vel = 0;
      sx = p.clientX; sy = lastY = p.clientY; lastT = e.timeStamp || Date.now();
      scroller = scrollerFor(e.target, sheet);
      // The top strip drags only while the sheet's list is at its top: in a
      // sheet scrolled down, a pull on the first rows scrolls back up. The
      // grabber always drags.
      fromTop = (handle && handle.contains(e.target)) ||
                (p.clientY - sheet.getBoundingClientRect().top <= GRAB_ZONE &&
                 !(scroller && scroller.scrollTop > 0));
    }

    function onTouchMove(e) {
      if (!tracking) return;
      var p = point(e), d = p.clientY - sy, dx = p.clientX - sx;
      if (!dragging) {
        // Up is a scroll of the sheet's list; so is down while that list has
        // somewhere to go; so is anything mostly SIDEWAYS (a row that scrolls
        // across, a control dragged along) however it drifts. None of these
        // is a dismissal, and none of them is the sheet's to take.
        var mayDismiss = d > 0 && Math.abs(d) >= Math.abs(dx) &&
                         (fromTop || !scroller || scroller.scrollTop <= 0);
        if (Math.abs(d) < SLOP && Math.abs(dx) < SLOP) {
          // CLAIM IT FROM THE FIRST PIXEL (v317 review). A real phone commits
          // to a page scroll -- or at the top, a pull-to-refresh -- on the
          // first move it is not told otherwise about, and every move after
          // that arrives uncancellable. So a move that could still become the
          // dismiss is cancelled even inside the slop.
          if (mayDismiss && e.cancelable) e.preventDefault();
          return;
        }
        if (!mayDismiss) { tracking = false; return; }
        dragging = true;
        settle(sheet);
        base = getComputedStyle(sheet).transform;
        if (!base || base === 'none') base = '';
        sheet.style.transition = 'none';
      }
      if (e.cancelable) e.preventDefault();
      var now = e.timeStamp || Date.now();
      vel = (p.clientY - lastY) / Math.max(1, now - lastT);
      lastY = p.clientY; lastT = now;
      dy = Math.max(0, d);
      sheet._dragDy = dy;
      sheet.style.transform = (base ? base + ' ' : '') + 'translateY(' + dy + 'px)';
    }

    function onTouchEnd(e) {
      if (!tracking) return;
      // A flick is a flick only if the finger was still moving when it left:
      // drag, pause, let go means "put it back".
      var still = ((e && e.timeStamp) || Date.now()) - lastT > 100;
      var was = dragging, pulled = dy, fast = still ? 0 : vel;
      tracking = false; dragging = false;
      if (!was) return;
      // Close FIRST, then hand the transform back: a sheet that animates out
      // does so from where the finger left it, not from a snap back up. A
      // surface whose close eases through slideOut() has already taken the
      // transform over, and keeps it.
      if (pulled > CLOSE_AT || (pulled > 24 && fast > FLICK)) close();
      if (sheet._slideT) return;
      sheet._dragDy = 0;
      sheet.style.transition = '';
      sheet.style.transform = '';
    }

    function onTouchCancel() {
      if (!tracking) return;
      reset();
    }

    sheet.addEventListener('touchstart', onTouchStart, { passive: true });
    sheet.addEventListener('touchmove', onTouchMove, { passive: false });
    sheet.addEventListener('touchend', onTouchEnd);
    sheet.addEventListener('touchcancel', onTouchCancel);

    if (handle) {
      handle.addEventListener('click', function (e) {
        e.stopPropagation();
        if (canClose()) close();
      });
    }
  }

  window.SkriblSheetSwipe = { attach: attach, isBottomSheet: isBottomSheet,
                              slideIn: slideIn, slideOut: slideOut, cancelSlide: unslide };
}());
