/* What is open, said once on <html>, so no style rule has to search the page.
 *
 * THE COST THIS REMOVES. Five rules began at the top of the page --
 * `html:has(...)` and `body:has(...)` -- to hide the Saved pill while a drawer,
 * a sheet or a button's card is open, and to stop pull-to-refresh while a sheet
 * is up. A :has() anchored at the root is checked again whenever anything under
 * it changes, and each check walks the whole page. An editor makes about 235
 * small style passes while it opens, and at phone pace (Chromium, the CPU 4x
 * slower, 4G) those five rules were 2.9 s of Pad's style work and 4.3 s of
 * Flip's. A copy of the stylesheet without just those five took 0.16 s and
 * 0.23 s, with every element's computed style the same at rest (Phase 1 of the
 * polish plan, DECISIONS.md).
 *
 * SO THE PAGE SAYS IT INSTEAD. Each state below is a class on <html> and the
 * surfaces that put it on; the stylesheets key on the class (styles.css,
 * pagemenu.css). The lists live here and only here, and verify_pagewide.py
 * fails if a root-anchored :has() comes back. Full screen is the one state not
 * here: lib/immersive.js owns full screen, so it says that one.
 *
 * WHEN. A MutationObserver hears the hidden attribute and the class change
 * anywhere, and elements arriving and leaving; a record that cannot touch one
 * of the surfaces is passed over without a query. Its callback runs before the
 * next frame is drawn, so the class is right in the frame the surface opens,
 * as the :has() rule was.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var root = doc.documentElement;

  /* Each entry names the element that CARRIES the hidden attribute. Tune opens
     and shuts by its class, so that is what names it (and the name drawer,
     which wears the same shell). The report sheet is not here because its
     OVERLAY is what hides, and .menu-overlay already covers it. */
  var STATES = [
    /* The Saved pill, and its x, step out of the way of whatever covers the
       page: the surface just opened is what the person is looking at, and the
       pill returns the moment it closes (styles.css). */
    ['skribl-covered', '.tab-panel:not([hidden]), #drawPanel:not([hidden]), .menu-overlay:not([hidden]),'
      + ' #moreMenu:not([hidden]), #helpDrawer:not([hidden]), #savedDraftsSheet:not([hidden]),'
      + ' .flip-export:not([hidden]), .tune-shell.open'],
    /* ...and out of a button's card (lib/learncard.js), where "Saved" sat on
       the card's title. */
    ['skribl-carded', '.lc-card:not([hidden])'],
    /* While a menu, sheet or drawer is open the page does not pull to refresh
       (styles.css, pagemenu.css; lib/sheetswipe.js takes the drags). */
    ['skribl-sheet', '.menu-overlay:not([hidden]), #moreMenu:not([hidden]), #savedDraftsSheet:not([hidden]),'
      + ' #helpDrawer:not([hidden]), #drawPanel:not([hidden]), #photoPanel:not([hidden]),'
      + ' #musicPanel:not([hidden]), .flip-export:not([hidden]), .pm-overlay:not([hidden]),'
      + ' .sheet:not([hidden])']
  ];
  /* Any element that could be one of those surfaces, open or shut. */
  var ANY = '.tab-panel, #drawPanel, .menu-overlay, #moreMenu, #helpDrawer, #savedDraftsSheet,'
    + ' .flip-export, .tune-shell, .lc-card, #photoPanel, #musicPanel, .pm-overlay, .sheet';

  function sync() {
    for (var i = 0; i < STATES.length; i++) {
      root.classList.toggle(STATES[i][0], !!doc.querySelector(STATES[i][1]));
    }
  }

  function holds(nodes) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.nodeType === 1 && (n.matches(ANY) || n.querySelector(ANY))) return true;
    }
    return false;
  }

  function heard(records) {
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if (r.type === 'attributes' ? r.target.matches(ANY) : (holds(r.addedNodes) || holds(r.removedNodes))) {
        sync();
        return;
      }
    }
  }

  new MutationObserver(heard).observe(root, {
    subtree: true, childList: true, attributes: true, attributeFilter: ['hidden', 'class']
  });
  sync();
})(window);
