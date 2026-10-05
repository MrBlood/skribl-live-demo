/* Opening with no signal: registers Skribl's service worker (the /sw.js route,
 * skribl/templates/skribl/sw.js), which keeps the last copy of each editor page
 * and the files it loaded, and answers from them only when the network fails.
 *
 * Loaded by _skribl_app_identity.html, so every page that has a Home Screen
 * identity can also open offline. The worker's URL and scope come from the
 * script tag's data- attributes, written by url_for, so a url_prefix mount
 * registers under its own prefix. Browsers without service workers, and pages
 * served over plain http from anywhere but localhost, simply skip it.
 */
(function (global) {
  'use strict';
  var me = global.document.currentScript;
  var nav = global.navigator;
  if (!me || !nav.serviceWorker) return;
  var url = me.getAttribute('data-sw');
  var scope = me.getAttribute('data-scope');
  if (!url || !scope) return;
  function register() {
    nav.serviceWorker.register(url, { scope: scope }).catch(function () {
      /* Never load-bearing: without it the page works exactly as before. */
    });
  }
  if (global.document.readyState === 'complete') register();
  else global.addEventListener('load', register);
})(window);
