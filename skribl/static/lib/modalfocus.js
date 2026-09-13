/* Focus for surfaces that declare aria-modal="true".
 *
 *   SkriblModal.open(dialog);    // remembers the opener, moves focus in
 *   SkriblModal.close(dialog);   // returns focus to the opener
 *
 * WHY THIS EXISTS. An accessibility audit of v278 found that Skribl's modal
 * surfaces declare `role="dialog" aria-modal="true"` and then do nothing about
 * focus. They are shown by unhiding a node. Focus stays wherever it was, behind
 * the sheet, so a keyboard user can Tab into controls the modal is covering;
 * closing leaves focus nowhere useful; and two of them called `blur()` on the
 * active element, which is not focus management, it is throwing focus at the
 * document body.
 *
 * This used to name five surfaces. There are eight, and v279 wired three of
 * them — a second audit caught that, and `verify_a11y.py` now reads the
 * population out of the DOM rather than trusting a list anybody has to keep
 * up to date, this one included.
 *
 * ARIA-MODAL IS A CLAIM ABOUT BEHAVIOUR. Saying it while the page underneath
 * stays reachable is worse than not saying it, because a screen reader tells
 * the user they are in a modal and the interaction contradicts that.
 *
 * WHAT IT DOES, and deliberately no more:
 *   - remembers what was focused when the dialog opened, and puts it back —
 *     falling back to that if an explicitly named opener is no longer VISIBLE,
 *     which `isConnected` alone did not catch and which put focus on <body>;
 *   - moves focus to the first usable control inside, or the dialog itself;
 *   - keeps Tab inside while it is open.
 *
 * WHAT IT DOES NOT DO. It does not hide the dialog, animate it, or bind
 * Escape — every surface here already owns those and they differ (the menu
 * slides on a timer, the help drawer does not). A utility that also controlled
 * visibility would have to know about all of that, and the surfaces would end
 * up fighting it.
 *
 * THE `inert` ALTERNATIVE was considered and skipped: it needs a single
 * wrapper around "everything that is not the dialog", and these templates do
 * not have one. A Tab loop needs nothing from the markup.
 */
(function (global) {
  'use strict';

  /* THE TAB SEQUENCE, not "everything focusable": tabindex="-1" is excluded
     on every kind, not only the bare [tabindex] entry. Since v292 a seg's
     unselected options carry tabindex="-1" (lib/segslider.js, one Tab stop
     per seg), and with them counted here the trap's idea of the LAST control
     in Flip's More menu was an option the browser would never Tab to — so
     from the real last stop, Tab left the dialog. verify_a11y's census caught
     it the same run the roving stop landed. */
  var FOCUSABLE = [
    'a[href]:not([tabindex="-1"])', 'button:not([disabled]):not([tabindex="-1"])',
    'input:not([disabled]):not([tabindex="-1"])', 'select:not([disabled]):not([tabindex="-1"])',
    'textarea:not([disabled]):not([tabindex="-1"])', '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  /* Visible only. A dialog full of hidden rows would otherwise send focus to
     something the user cannot see — offsetParent is the cheap test this
     project already uses for the same question elsewhere. */
  function usable(dialog) {
    var all = dialog.querySelectorAll(FOCUSABLE);
    var out = [];
    for (var i = 0; i < all.length; i++) {
      if (all[i].offsetParent !== null || all[i] === global.document.activeElement) {
        out.push(all[i]);
      }
    }
    return out;
  }

  function onKeydown(e) {
    if (e.key !== 'Tab') return;
    var dialog = e.currentTarget;
    var items = usable(dialog);
    if (!items.length) { e.preventDefault(); return; }
    var first = items[0], last = items[items.length - 1];
    var active = global.document.activeElement;
    /* Wrap at both ends. Without the shift branch, Shift+Tab from the first
       control escapes backwards into the page, which is the same hole from
       the other side. */
    if (e.shiftKey && (active === first || !dialog.contains(active))) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault(); first.focus();
    }
  }

  /* Connected is not the same as focusable. `focus()` on a node that is
     display:none does nothing and throws nothing, so focus stays where it was
     — on <body> — and the caller has no way to tell. */
  function focusable(el) {
    return !!(el && el.isConnected && typeof el.focus === 'function' &&
              el.offsetParent !== null);
  }

  function open(dialog, opener) {
    if (!dialog) return;
    dialog._skriblOpener = opener || global.document.activeElement || null;
    /* AND WHATEVER HAD FOCUS, always, as a second chance. An explicit opener
       can be gone from view by the time the dialog closes: the leave confirm
       is opened from a menu item and closes that menu on the way, so the item
       it names is display:none when focus should come back to it. v279 checked
       isConnected only, so that case put focus on <body> — the exact outcome
       the utility was written to prevent, reached through the one door it did
       not cover. Found by making verify_a11y enumerate every modal instead of
       testing the one whose opener happens to stay visible. */
    dialog._skriblFallback = global.document.activeElement || null;
    if (!dialog._skriblTrap) {
      dialog._skriblTrap = onKeydown;
      dialog.addEventListener('keydown', onKeydown);
    }
    /* tabindex="-1" so the dialog can hold focus itself when it contains
       nothing focusable — better than leaving focus outside it. */
    if (!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex', '-1');
    var items = usable(dialog);
    (items.length ? items[0] : dialog).focus();
  }

  function close(dialog) {
    if (!dialog) return;
    var opener = dialog._skriblOpener;
    var fallback = dialog._skriblFallback;
    dialog._skriblOpener = null;
    dialog._skriblFallback = null;
    /* The opener first, then whatever had focus when it opened. Both are
       checked with focusable() rather than isConnected: the posted list
       rebuilds its rows so an opener can be detached, and a menu item can be
       present but hidden. Either way focusing it is a silent no-op and the
       user lands on <body>. */
    if (focusable(opener)) { opener.focus(); return; }
    if (focusable(fallback)) { fallback.focus(); }
  }

  global.SkriblModal = { open: open, close: close };
})(window);
