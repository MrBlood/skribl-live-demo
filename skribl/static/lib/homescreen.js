/* Getting Skribl onto the Home Screen: the ⋯ row, the one-time banner, and the
 * steps sheet both open. Markup and the why: _skribl_homescreen.html.
 *
 * WHO SEES IT. An iPhone or iPad in a browser tab -- not once Skribl is
 * already on the Home Screen (navigator.standalone, or the standalone display
 * mode the manifest asks for). iPadOS reports itself as a Mac, so a Mac with a
 * touch screen counts as an iPad. On Android, Chrome offers its own install,
 * and the row appears only when the browser has said it can
 * (beforeinstallprompt); pressing it asks the browser rather than showing
 * steps that are Safari's. A desktop sees nothing.
 *
 * THE BANNER IS ONCE. Closing it, opening the steps from it, or starting to
 * draw under it each put it away for good (localStorage). Storage that throws
 * -- Safari private mode -- means it can come back on the next visit, which is
 * the right failure for a hint: never load-bearing, never broken.
 *
 * ITS ICON WAITS FOR THE PAGE (FUTURE 6af, Nov 8). The banner's and the
 * sheet's icon are loading="lazy" in the markup, so a first open does not
 * download them; they are fetched once the page has loaded and gone idle,
 * and the banner, when its time comes, waits for its icon to be decoded (a
 * moment at most, ICON_WAIT_MS) so it never shows an empty square.
 * verify_identity asks both.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var SEEN_KEY = 'skribl_homescreen_hint_v1';
  var SHOW_AFTER_MS = 1200;   // after the page settles, not over its first paint
  var ICON_WAIT_MS = 400;     // the most the banner waits for its icon

  function read(k) { try { return global.localStorage.getItem(k); } catch (e) { return null; } }
  function write(k, v) { try { global.localStorage.setItem(k, v); } catch (e) { /* fails quiet */ } }

  function standalone() {
    if (global.navigator.standalone === true) return true;
    try { return global.matchMedia('(display-mode: standalone)').matches; } catch (e) { return false; }
  }
  /* The icons in the banner and the sheet: fetched now (they are lazy, and
     hidden), and a promise that settles when IMG is decoded or after WAIT ms,
     whichever comes first; a broken image settles it too. */
  function icons() { return doc.querySelectorAll('#homeScreenBanner img, #homeScreenSteps img'); }
  function fetchIcons() {
    var all = icons();
    for (var i = 0; i < all.length; i++) all[i].loading = 'eager';
  }
  function iconReady(img, wait) {
    if (!img) return Promise.resolve();
    img.loading = 'eager';
    var decoded = img.decode ? img.decode().catch(function () {}) : Promise.resolve();
    return Promise.race([decoded, new Promise(function (done) { global.setTimeout(done, wait); })]);
  }
  function apple() {
    var n = global.navigator;
    return /iP(hone|od|ad)/.test(n.userAgent || '')
      || (n.platform === 'MacIntel' && n.maxTouchPoints > 1);
  }

  function init() {
    // Running from the Home Screen: styles.css reserves the home bar for the
    // sheets that rise from the bottom (iOS reports its inset as 0 here).
    if (standalone()) doc.documentElement.setAttribute('data-skribl-app', '');
    var row = doc.getElementById('homeScreenItem');
    var banner = doc.getElementById('homeScreenBanner');
    var scrim = doc.getElementById('homeScreenScrim');
    var sheet = doc.getElementById('homeScreenSteps');
    if (!scrim || !sheet || standalone()) return;
    var settled = function () {
      if ('requestIdleCallback' in global) global.requestIdleCallback(fetchIcons, { timeout: 3000 });
      else global.setTimeout(fetchIcons, 1000);
    };
    if (doc.readyState === 'complete') settled();
    else global.addEventListener('load', settled, { once: true });
    var Modal = global.SkriblModal;
    var ios = apple();
    api.open = function () { openSteps(); };
    var installEvent = null;   // Android's deferred prompt, when the browser offers one

    /* Focus comes back to the ⋯, where the row lives, unless something more
       specific opened the sheet. Opened from the banner, the banner is gone
       by the time it closes, and with no opener focus would land on <body>. */
    function menuButton() { return doc.getElementById('menuBtn') || doc.getElementById('moreBtn'); }
    function openSteps(opener) {
      if (installEvent) {
        var ev = installEvent;
        installEvent = null;
        ev.prompt();
        return;
      }
      iconReady(sheet.querySelector('img'), 0);   // a tap opens it at once; the icon follows if it must
      scrim.hidden = false;
      if (Modal) Modal.open(sheet, opener || menuButton());
    }
    function closeSteps() {
      if (scrim.hidden) return;
      scrim.hidden = true;
      if (Modal) Modal.close(sheet);
    }
    doc.getElementById('homeScreenDone').addEventListener('click', closeSteps);
    scrim.addEventListener('click', function (e) { if (e.target === scrim) closeSteps(); });
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !scrim.hidden) { e.preventDefault(); closeSteps(); }
    });

    if (row) {
      row.hidden = !ios;
      row.addEventListener('click', function () {
        /* The menu goes first so the sheet is not opened behind it, and focus
           returns to the menu button rather than to a row that is now hidden. */
        if (typeof global.closeMenu === 'function') { try { global.closeMenu(true); } catch (e) {} }
        openSteps(menuButton());
      });
      global.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        installEvent = e;
        row.hidden = false;
      });
      global.addEventListener('appinstalled', function () { row.hidden = true; installEvent = null; });
    }

    if (!banner || !ios || read(SEEN_KEY)) return;
    function place() {
      var tools = doc.getElementById('toolBar');
      var r = tools && tools.getBoundingClientRect();
      var lift = r && r.height ? Math.max(0, global.innerHeight - r.top) + 12 : 96;
      banner.style.bottom = Math.round(lift) + 'px';
    }
    function putAway() {
      if (banner.hidden) return;
      banner.hidden = true;
      write(SEEN_KEY, '1');
      global.removeEventListener('resize', place);
    }
    doc.getElementById('homeScreenBannerClose').addEventListener('click', putAway);
    doc.getElementById('homeScreenBannerOpen').addEventListener('click', function () {
      putAway();
      openSteps();
    });
    /* Drawing under it means the canvas is wanted, so the card steps aside. */
    var canvas = doc.getElementById('canvas');
    if (canvas) canvas.addEventListener('pointerdown', putAway, { once: true });
    global.setTimeout(function () {
      iconReady(banner.querySelector('img'), ICON_WAIT_MS).then(function () {
        if (read(SEEN_KEY) || doc.body.classList.contains('stroking')) return;
        place();
        banner.hidden = false;
        global.addEventListener('resize', place);
      });
    }, SHOW_AFTER_MS);
  }

  /* open() is filled in by init() on a page that has the sheet: the census in
     verify_a11y drives it on a desktop, where the row is rightly hidden. */
  var api = { init: init, isStandalone: standalone, open: function () {} };
  global.SkriblHomeScreen = api;
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
