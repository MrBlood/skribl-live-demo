/* The Home Screen app: opening with no signal, and staying current.
 *
 * ONLY FROM THE HOME SCREEN APP. Everything here is what an installed app is
 * expected to do and a browser tab already does for itself. A browser tab --
 * Skribl's own pages in a normal visit, every harness suite, a host's site with
 * Skribl mounted at its root -- runs none of it.
 *
 * 1. OPENING OFFLINE. Registers Skribl's service worker (the /sw.js route,
 *    skribl/templates/skribl/sw.js), which keeps the last copy of each editor
 *    page and the files it loaded, and answers from them only when the network
 *    fails. On an iPhone the Home Screen copy keeps its own storage, apart from
 *    Safari's, so a worker registered in a Safari tab would never reach it
 *    anyway; and a worker answers requests before the page's own interception
 *    sees them, which is what turned red every suite that blocks or fakes a
 *    request the first time this ran in every tab.
 *
 * 2. A NEWER BUILD IS OFFERED, NEVER FORCED. iOS keeps the app alive in the
 *    background, so coming back to it shows the page it already had; a new
 *    build arrived only when the app was killed and reopened (the owner:
 *    "shouldn't the app refresh on pull down now that it's full screen?").
 *    When the app comes back to the front, the page asks the server for its
 *    build (skribl.build_id, /build.json) and, if it differs from the one this
 *    page was rendered from, the Pad and Flip show "A new version of Skribl is
 *    ready · Reload". It never reloads by itself: a reload in the middle of a
 *    stroke is the thing it must not do. The draft is flushed on pagehide
 *    (editor_draft.js), so Reload brings the drawing back.
 *
 * 3. RELOAD IN THE MENU. There is no browser bar to reload from, so the
 *    editors' ⋯ menu shows a Reload row (_skribl_homescreen.html reload_row),
 *    in the slot Add to Home Screen takes in a tab.
 *
 * 4. PULL TO REFRESH, ON THE LIBRARY. Safari's own pull-to-refresh goes with
 *    its bar. The Library is a list, where the gesture is expected; the editors
 *    are drawing surfaces, where a downward stroke must never reload the page,
 *    so they have no pull. Pulling past 64px and letting go reloads the page,
 *    which also picks up a new build.
 *
 * Loaded by the Pad, Flip and the library. URLs and the page's build come from
 * the script tag's data- attributes, written by url_for, so a url_prefix mount
 * works under its own prefix.
 */
(function (global) {
  'use strict';
  var doc = global.document;
  var me = doc.currentScript;
  var nav = global.navigator;
  if (!me) return;
  var installed = nav.standalone === true;
  try { installed = installed || global.matchMedia('(display-mode: standalone)').matches; } catch (e) {}
  if (!installed) return;

  function reload() { global.location.reload(); }

  // 1. Opening offline.
  var swUrl = me.getAttribute('data-sw');
  var scope = me.getAttribute('data-scope');
  function register() {
    if (!nav.serviceWorker || !swUrl || !scope) return;
    nav.serviceWorker.register(swUrl, { scope: scope }).catch(function () {
      /* Never load-bearing: without it the page works exactly as before. */
    });
  }

  // 2. A newer build.
  var mine = me.getAttribute('data-build');
  var buildUrl = me.getAttribute('data-build-url');
  var offered = false, asking = false;
  function offer() {
    // The editors' toast (styles.css .skribl-hint), as its own node so it never
    // takes the place of a tip. The library has no such sheet; it has the pull.
    if (offered || !doc.querySelector('.header')) return;
    offered = true;
    var node = doc.createElement('div');
    node.className = 'skribl-hint skribl-update';
    node.id = 'skriblUpdate';
    node.setAttribute('role', 'status');
    var ic = doc.createElement('span');
    ic.className = 'skribl-hint-ic';
    ic.setAttribute('aria-hidden', 'true');
    ic.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg>';
    var text = doc.createElement('span');
    text.className = 'skribl-hint-text';
    text.textContent = 'A new version of Skribl is ready';
    var go = doc.createElement('button');
    go.type = 'button';
    go.className = 'skribl-hint-action';
    go.textContent = 'Reload';
    go.addEventListener('click', function (e) { e.stopPropagation(); reload(); });
    node.appendChild(ic); node.appendChild(text); node.appendChild(go);
    doc.body.appendChild(node);
    global.requestAnimationFrame(function () { node.classList.add('in'); });
    // Like every toast here it lets taps through to the canvas (only its
    // button takes one), so it cannot be tapped away; it goes by itself after
    // 15s, and the menu's Reload row stays.
    global.setTimeout(function () { node.classList.remove('in'); }, 15000);
  }
  function check() {
    if (offered || asking || !mine || !buildUrl || doc.visibilityState !== 'visible') return;
    asking = true;
    global.fetch(buildUrl, { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { asking = false; if (j && j.build && j.build !== mine) offer(); },
            function () { asking = false; });   // no signal: ask again next time
  }

  // 3. Reload in the menu.
  function wireRow() {
    var row = doc.getElementById('reloadAppItem');
    if (!row) return;
    row.hidden = false;
    row.addEventListener('click', reload);
  }

  // 4. Pull to refresh, where the page carries the indicator (the library).
  function wirePull() {
    var bar = doc.getElementById('pullRefresh');
    if (!bar) return;
    var label = bar.querySelector('.pull-refresh-label');
    var READY = 64, startY = null, depth = 0;
    doc.documentElement.classList.add('has-pull');
    function set(h) {
      depth = h;
      bar.style.height = h + 'px';
      bar.classList.toggle('is-ready', h >= READY);
      if (label) label.textContent = h >= READY ? 'Release to refresh' : 'Pull to refresh';
    }
    global.addEventListener('touchstart', function (e) {
      startY = (e.touches.length === 1 && global.scrollY <= 0) ? e.touches[0].clientY : null;
      if (startY !== null) bar.classList.add('is-pulling');
    }, { passive: true });
    global.addEventListener('touchmove', function (e) {
      if (startY === null) return;
      var dy = e.touches[0].clientY - startY;
      if (dy <= 0 || global.scrollY > 0) { set(0); return; }
      set(Math.min(Math.round(dy * 0.5), 88));
    }, { passive: true });
    function release() {
      bar.classList.remove('is-pulling');
      if (startY === null) return;
      startY = null;
      if (depth >= READY) {
        set(READY);
        bar.classList.add('is-busy');
        if (label) label.textContent = 'Refreshing…';
        reload();
      } else {
        set(0);
      }
    }
    global.addEventListener('touchend', release, { passive: true });
    global.addEventListener('touchcancel', release, { passive: true });
  }

  function start() {
    register();
    wireRow();
    wirePull();
    check();
  }
  doc.addEventListener('visibilitychange', check);
  global.addEventListener('online', check);
  if (doc.readyState === 'complete') start();
  else global.addEventListener('load', start);
})(window);
