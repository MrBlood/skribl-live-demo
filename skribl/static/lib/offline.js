/* Opening with no signal: registers Skribl's service worker (the /sw.js route,
 * skribl/templates/skribl/sw.js), which keeps the last copy of each editor page
 * and the files it loaded, and answers from them only when the network fails.
 *
 * ONLY FROM THE HOME SCREEN APP. Opening offline is what an installed app is
 * expected to do, and the installed app is where it matters: on an iPhone the
 * Home Screen copy keeps its own storage, apart from Safari's, so a worker
 * registered in a Safari tab would never reach it anyway. A browser tab --
 * Skribl's own pages in a normal visit, every harness suite, a host's site with
 * Skribl mounted at its root -- registers nothing and never meets the worker.
 * That is not caution for its own sake: a worker answers requests before the
 * page's own interception sees them, which is exactly what turned red every
 * suite that blocks or fakes a request the first time this ran in every tab.
 *
 * Loaded by the Pad, Flip and the library, the three pages the worker keeps.
 * The worker's URL and scope come from the script tag's data- attributes,
 * written by url_for, so a url_prefix mount registers under its own prefix.
 */
(function (global) {
  'use strict';
  var me = global.document.currentScript;
  var nav = global.navigator;
  if (!me || !nav.serviceWorker) return;
  var installed = nav.standalone === true;
  try { installed = installed || global.matchMedia('(display-mode: standalone)').matches; } catch (e) {}
  if (!installed) return;
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
