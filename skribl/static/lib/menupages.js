/* The ⋯ menu's pages: the main page, New Skribl and Settings, one sheet
 * (templates/skribl/_skribl_menu.html; owner, after v323, from the menu mock).
 *
 * WHY PAGES AND NOT MORE SHEETS. A sheet over a sheet is two dims, two
 * grabbers and two ways to close. A page swaps inside the menu the person
 * already opened: Back returns to it, and closing the menu closes all of it.
 *
 * WHAT IT DOES:
 *   - [data-menu-go="<page>"] shows that page. Arriving, focus goes to the
 *     page's Back; coming back, to the row or tile that opened the page.
 *   - Escape on a page goes back one page; on the main page it is the
 *     editor's (it closes the menu).
 *   - Every opening starts on the main page, at the top (reset(), which each
 *     editor's openMenu calls).
 *   - New Skribl's shape is a choice kept here until Start: it opens on the
 *     drawing's own shape (read from the Settings row's lit option), and
 *     chosenSize() is what each editor's Start reads. Its labels come from
 *     lib/canvassizes.js, as the Settings row's do, read as the page opens
 *     (that table loads after this file).
 *
 * WHAT IT DOES NOT: start, save or switch anything. Every action keeps the
 * handler its editor bound to its id (app.js, editor_menu.js, flip.js).
 */
(function (global) {
  'use strict';
  var doc = global.document;
  var root = doc.getElementById('menuSheet') || doc.getElementById('moreMenu');
  if (!root || !root.querySelector('.menu-page')) return;

  function pages() { return root.querySelectorAll(':scope > .menu-page'); }
  function current() {
    var on = root.querySelector(':scope > .menu-page:not([hidden])');
    return on ? on.getAttribute('data-menu-page') : 'main';
  }
  function page(name) { return root.querySelector(':scope > .menu-page[data-menu-page="' + name + '"]'); }

  function syncNew() {
    var seg = doc.getElementById('newSizeSeg');
    if (!seg) return;
    var lit = doc.querySelector('#canvasSeg button.on');
    var want = lit ? lit.getAttribute('data-size') : 'classic';
    [].forEach.call(seg.querySelectorAll(':scope > button'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-size') === want);
    });
  }
  function labels() {
    var table = global.SkriblCanvasSizes, seg = doc.getElementById('newSizeSeg');
    if (!table || !seg) return;
    [].forEach.call(seg.querySelectorAll(':scope > button'), function (b) {
      var preset = table.byId(b.getAttribute('data-size'));
      var lbl = b.querySelector('.menu-shape-lbl');
      if (preset && lbl) lbl.textContent = preset.label;
    });
  }

  function show(name, focus) {
    var was = current();
    if (!page(name)) return;
    [].forEach.call(pages(), function (p) { p.hidden = p.getAttribute('data-menu-page') !== name; });
    root.scrollTop = 0;
    if (name === 'new') { labels(); syncNew(); }
    if (!focus) return;
    var target = name === 'main'
      ? page('main').querySelector('[data-menu-go="' + was + '"]')
      : page(name).querySelector('.menu-back');
    if (target) target.focus({ preventScroll: true });
  }

  root.addEventListener('click', function (e) {
    var go = e.target.closest('[data-menu-go]');
    if (go && root.contains(go)) { e.preventDefault(); show(go.getAttribute('data-menu-go'), true); return; }
    var b = e.target.closest('#newSizeSeg > button');
    if (b) {
      [].forEach.call(b.parentNode.querySelectorAll(':scope > button'), function (x) { x.classList.toggle('on', x === b); });
    }
  });
  root.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || current() === 'main') return;
    e.preventDefault();
    e.stopPropagation();
    show('main', true);
  });

  // ONE CHOICE LIT FROM THE START (verify_a11y: every pick-one has exactly
  // one pressed). The template lights the first; this follows the drawing's
  // own shape whenever the Settings row's lit option moves, except while the
  // New page is open and the choice there is the person's.
  var canvasSeg = doc.getElementById('canvasSeg');
  if (canvasSeg && global.MutationObserver) {
    new MutationObserver(function () { if (current() !== 'new') syncNew(); })
      .observe(canvasSeg, { subtree: true, attributes: true, attributeFilter: ['class'] });
  }
  syncNew();

  global.SkriblMenuPages = {
    reset: function () { show('main', false); },
    show: show,
    current: current,
    chosenSize: function () {
      var b = doc.querySelector('#newSizeSeg > button.on');
      return b ? b.getAttribute('data-size') : null;
    }
  };
})(window);
