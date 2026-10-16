/* Blooby says hi: the first time Skribl opens on a phone (FUTURE.md 6m).
 *
 * He walks up from far away on his star, waves once, and fades into the
 * canvas: the in-post player playing a Flip drawn with the real pen
 * (brand/blooby-hello.json, harness/tools/make_grow.py take C). The owner's
 * picks: once only, a tap skips him, a still hello under Reduce Motion, one
 * module for the Pad and Flip.
 *
 * NOTHING IS FETCHED UNLESS HE COMES. He comes when this browser has never
 * seen him, on a phone (a touch screen whose short side is under 600 css px),
 * on a page of its own (not a composer's frame). The player and his drawing
 * load first; if they are not here within LATE ms he does not come this time,
 * and is not marked seen, so the canvas is never held up waiting for him.
 *
 * AUTOMATION NEVER MEETS HIM unless it asks (window.__skriblHelloForce, set
 * before the page loads): every suite opens a fresh browser, and a hello on
 * top of every first canvas would be in each one's way. verify_hello asks.
 *
 * SHARP: the player draws at most 2 pixels a point; alone on the screen he
 * asks for the phone's own (attach's maxDpr), which at 2 drew soft on a 3x
 * iPhone.
 */
(function () {
  'use strict';
  var el = document.getElementById('skriblHello');
  if (!el) return;
  var KEY = 'skribl.hello.v1';
  var LATE = 4000;
  var force = window.__skriblHelloForce === true;

  function seen() { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return true; } }
  function mark() { try { localStorage.setItem(KEY, '1'); } catch (e) {} }
  function phone() {
    var touch = window.matchMedia && window.matchMedia('(hover: none) and (pointer: coarse)').matches;
    return touch && Math.min(window.screen.width, window.screen.height) < 600;
  }

  if (!phone() || (navigator.webdriver && !force)) return;
  if (seen() || window.top !== window || /[?&]compose=1\b/.test(location.search)) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var box = el.querySelector('.skribl-inline');

  function player() {
    if (window.SkriblInline) return Promise.resolve();
    return new Promise(function (done, fail) {
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = el.getAttribute('data-player-css');
      document.head.appendChild(css);
      var js = document.createElement('script');
      js.src = el.getAttribute('data-player-js');
      js.onload = function () { if (window.SkriblInline) done(); else fail(); };
      js.onerror = fail;
      document.head.appendChild(js);
    });
  }
  function drawing() {
    return fetch(el.getAttribute('data-hello')).then(function (r) {
      if (!r.ok) throw new Error('hello ' + r.status);
      return r.json();
    });
  }
  function late() { return new Promise(function (done, fail) { setTimeout(fail, LATE); }); }

  var p = null, gone = false;
  function leave() {
    if (gone) return;
    gone = true;
    el.classList.add('is-leaving');
    setTimeout(function () {
      if (p) p.settle();
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 520);
  }

  Promise.race([Promise.all([player(), drawing()]), late()]).then(function (got) {
    var payload = got[1];
    var cs = payload.canvasSize || {};
    box.setAttribute('data-skribl-w', cs.cssWidth || 9);
    box.setAttribute('data-skribl-h', cs.cssHeight || 16);
    el.hidden = false;
    p = window.SkriblInline.attach(box, payload, { ambient: true, maxDpr: 3 });
    if (!p) { el.hidden = true; return; }
    if (p.shape) p.shape(true);
    mark();
    el.addEventListener('pointerdown', leave);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') leave();
    }, true);
    requestAnimationFrame(function () { el.classList.add('is-on'); });
    if (reduce) {
      // Still: the finished drawing, him at full size waving, then the fade.
      setTimeout(leave, 1800);
      return;
    }
    p.toggle();
    var total = (p.state().totalMs || 5400);
    var t0 = Date.now();
    (function watch() {
      if (gone) return;
      var s = p.state();
      if ((s.elapsedMs || 0) >= total - 40 || Date.now() - t0 > total + 3000) { leave(); return; }
      requestAnimationFrame(watch);
    })();
  }).catch(function () { el.hidden = true; });
})();
