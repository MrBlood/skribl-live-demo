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
 * not finish a dismissal the person never finished (verify_tools V214c). */
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

  function isBottomSheet(sheet) {
    var r = sheet.getBoundingClientRect();
    return r.width > 0 && r.bottom >= window.innerHeight - 2;
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

  function attach(sheet, opts) {
    if (!sheet || sheet._skriblSheetSwipe) return;
    sheet._skriblSheetSwipe = true;
    opts = opts || {};
    var close = opts.close;
    var handle = opts.handle || null;
    var canClose = opts.canClose || function () { return true; };

    var tracking = false, dragging = false, fromTop = false, scroller = null;
    var sy = 0, dy = 0, lastY = 0, lastT = 0, vel = 0, base = '';

    function reset() {
      tracking = false; dragging = false; dy = 0; vel = 0;
      sheet.style.transition = '';
      sheet.style.transform = '';
    }

    function onTouchStart(e) {
      tracking = false;
      if (!e.touches || e.touches.length !== 1 || !canClose() || !isBottomSheet(sheet)) return;
      // A slider or a text field owns its own drag.
      if (e.target.closest && e.target.closest('input, textarea, select')) return;
      var p = point(e);
      tracking = true; dragging = false; dy = 0; vel = 0;
      sy = lastY = p.clientY; lastT = e.timeStamp || Date.now();
      fromTop = (handle && handle.contains(e.target)) ||
                (p.clientY - sheet.getBoundingClientRect().top <= GRAB_ZONE);
      scroller = scrollerFor(e.target, sheet);
    }

    function onTouchMove(e) {
      if (!tracking) return;
      var p = point(e), d = p.clientY - sy;
      if (!dragging) {
        if (Math.abs(d) < SLOP) return;
        // Up is a scroll of the sheet's list; so is down while that list has
        // somewhere to go. Either way this touch is not a dismissal.
        if (d < 0 || (!fromTop && scroller && scroller.scrollTop > 0)) { tracking = false; return; }
        dragging = true;
        base = getComputedStyle(sheet).transform;
        if (!base || base === 'none') base = '';
        sheet.style.transition = 'none';
      }
      if (e.cancelable) e.preventDefault();
      var now = e.timeStamp || Date.now();
      vel = (p.clientY - lastY) / Math.max(1, now - lastT);
      lastY = p.clientY; lastT = now;
      dy = Math.max(0, d);
      sheet.style.transform = (base ? base + ' ' : '') + 'translateY(' + dy + 'px)';
    }

    function onTouchEnd() {
      if (!tracking) return;
      var was = dragging, pulled = dy, fast = vel;
      tracking = false; dragging = false;
      if (!was) return;
      // Close FIRST, then hand the transform back: a sheet that animates out
      // does so from where the finger left it, not from a snap back up.
      if (pulled > CLOSE_AT || (pulled > 24 && fast > FLICK)) close();
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

  window.SkriblSheetSwipe = { attach: attach, isBottomSheet: isBottomSheet };
}());
