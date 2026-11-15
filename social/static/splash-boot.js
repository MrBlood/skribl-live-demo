/* THE BLOOBY APP'S SPLASH, DECIDED BEFORE THE FIRST PAINT (the owner, Nov 15,
 * with Bluesky's splash: "make a splash screen load first and show blooby",
 * on the dark ground "with no stars"). A file, not inline: the site's pages
 * carry one inline script, Skribl's theme boot (base.html), and this one runs
 * right after it, in the head, before the body paints, so a page that will
 * not show the splash is never seen covered, and one that will never shows
 * its own page first.
 *
 * ONLY THE APP, ONCE A LAUNCH. Opened from the Home Screen (navigator
 * .standalone, or the standalone display the site's manifest asks for) and
 * not yet this launch (sessionStorage, which the app keeps from page to page
 * and loses when it is closed): <html> gets is-splashing, which shows the
 * splash (social.css, THE SPLASH), and is-splash-first the first time ever
 * (localStorage), when the word writes itself; after that only the blush
 * falls. A browser tab never shows it. Storage that throws shows nothing.
 *
 * THE BROWSER'S BAR in the splash's ground while it shows (both theme-color
 * metas, their colour kept to put back: splash.js puts it back as it goes).
 * And never longer than LONGEST, whatever becomes of splash.js.
 *
 * Automation asks for it (window.__bloobySplashForce, before the page loads),
 * as Skribl's hello is asked for: every suite's browser is a tab. */
(function () {
  'use strict';
  var LONGEST = 6000;
  var root = document.documentElement, nav = window.navigator;
  var app = nav.standalone === true || window.__bloobySplashForce === true;
  try { app = app || window.matchMedia('(display-mode: standalone)').matches; } catch (e) { /* none */ }
  if (!app) return;
  try {
    if (window.sessionStorage.getItem('blooby.splash.launch')) return;
    window.sessionStorage.setItem('blooby.splash.launch', '1');
  } catch (e) { return; }
  var first = true;
  try { first = !window.localStorage.getItem('blooby.splash.v1'); } catch (e) { /* first, then */ }
  root.classList.add('is-splashing');
  if (first) root.classList.add('is-splash-first');
  var metas = document.querySelectorAll('meta[name="theme-color"]');
  for (var i = 0; i < metas.length; i++) {
    metas[i].setAttribute('data-splash-was', metas[i].getAttribute('content'));
    metas[i].setAttribute('content', '#0f1218');
  }
  window.setTimeout(function () {
    if (window.BloobySplash) window.BloobySplash.leave();
    else root.classList.remove('is-splashing', 'is-splash-first');
  }, LONGEST);
})();
