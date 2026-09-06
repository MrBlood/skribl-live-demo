/* Focus for surfaces that declare aria-modal="true".
 *
 *   SkriblModal.open(dialog);    // remembers the opener, moves focus in
 *   SkriblModal.close(dialog);   // returns focus to the opener
 *
 * WHY THIS EXISTS. An accessibility audit of v278 found that Pad's modal
 * surfaces — the More sheet, Help, Post, Export, the leave confirm — declare
 * `role="dialog" aria-modal="true"` and then do nothing about focus. They are
 * shown by unhiding a node. Focus stays wherever it was, behind the sheet, so
 * a keyboard user can Tab into controls the modal is covering; closing leaves
 * focus nowhere useful; and two of them called `blur()` on the active element,
 * which is not focus management, it is throwing focus at the document body.
 *
 * ARIA-MODAL IS A CLAIM ABOUT BEHAVIOUR. Saying it while the page underneath
 * stays reachable is worse than not saying it, because a screen reader tells
 * the user they are in a modal and the interaction contradicts that.
 *
 * WHAT IT DOES, and deliberately no more:
 *   - remembers what was focused when the dialog opened, and puts it back;
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

  var FOCUSABLE = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
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

  function open(dialog, opener) {
    if (!dialog) return;
    dialog._skriblOpener = opener || global.document.activeElement || null;
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
    dialog._skriblOpener = null;
    /* isConnected: the opener may have been re-rendered away while the dialog
       was up (the posted list rebuilds its rows), and focusing a detached node
       silently does nothing — which is how focus ends up on <body>. */
    if (opener && opener.isConnected && typeof opener.focus === 'function') {
      opener.focus();
    }
  }

  global.SkriblModal = { open: open, close: close };
})(window);
