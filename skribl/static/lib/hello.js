/* Blooby says hi: the first time Skribl opens, on any screen (FUTURE.md 6m).
 *
 * His star draws itself and its light comes on, he walks up from far away
 * onto it, waves once, and the picture opens onto the canvas: the in-post
 * player playing a Flip drawn with the real pen (brand/blooby-hello.json,
 * harness/tools/make_grow.py's take `hello`) in the Home Screen icon's own
 * light. The owner's picks: once only, a tap, a click or any key skips him,
 * a still hello under Reduce Motion, one module for the Pad and Flip.
 *
 * NOTHING IS FETCHED UNLESS HE COMES. He comes when this browser has never
 * seen him, on a page of its own (not a composer's frame). The player and his
 * drawing load first; if they are not here within LATE ms he does not come
 * this time, and is not marked seen, so the canvas is never held up waiting
 * for him.
 *
 * AUTOMATION NEVER MEETS HIM unless it asks (window.__skriblHelloForce, set
 * before the page loads): every suite opens a fresh browser, and a hello on
 * top of every first canvas would be in each one's way. verify_hello asks.
 *
 * SHARP (owner: "I was hoping for a super crisp look, but it looks kind of
 * blurry"). His box sits on whole screen pixels and his drawing fills it at a
 * whole number of its pixels to a screen pixel, so no engine shrinks it by an
 * odd amount: three pixels a point drew 1.39 of them to a screen pixel, off
 * the grid, and the iPhone's shrink softened every edge. Twice the screen's
 * pixels where the drawing stays within BUDGET; past it a canvas leaves the
 * fast path (Chrome here: half a millisecond a frame at 8.1 million pixels,
 * nine at 9), so a big screen draws at its own pixels, one for one.
 */
(function () {
  'use strict';
  var el = document.getElementById('skriblHello');
  if (!el) return;
  var KEY = 'skribl.hello.v1';
  var LATE = 4000;
  var BUDGET = 8e6;
  var force = window.__skriblHelloForce === true;

  function seen() { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return true; } }
  function mark() { try { localStorage.setItem(KEY, '1'); } catch (e) {} }

  if (navigator.webdriver && !force) return;
  if (seen() || window.top !== window || /[?&]compose=1\b/.test(location.search)) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stage = el.querySelector('.skribl-hello-stage');
  var box = el.querySelector('.skribl-inline');
  var glow = el.querySelector('.skribl-hello-glow');

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

  /* THE BOX ON THE GRID: a whole number of the drawing's own steps (9 x 16
   * screen pixels for a 9:16 drawing), as big as the screen allows, centred
   * on whole screen pixels. Returns the drawing's pixels a point that fill it
   * exactly. On a resize (a turned phone) the box moves and the drawing keeps
   * its pixels until he leaves. */
  var cw = 9, ch = 16;
  function gcd(a, b) { return b ? gcd(b, a % b) : a; }
  function fit() {
    var dpr = window.devicePixelRatio || 1, g = gcd(cw, ch), a = cw / g, b = ch / g;
    var vw = el.clientWidth * dpr, vh = el.clientHeight * dpr;
    var m = Math.max(1, Math.floor(Math.min(vw / a, vh / b)));
    var s = stage.style;
    s.width = a * m / dpr + 'px';
    s.height = b * m / dpr + 'px';
    s.left = Math.round((vw - a * m) / 2) / dpr + 'px';
    s.top = Math.round((vh - b * m) / 2) / dpr + 'px';
    return (4 * a * m * b * m <= BUDGET ? 2 : 1) * m / g;
  }

  var p = null, gone = false;
  function light() { if (glow) glow.classList.add('is-lit'); }
  function leave() {
    if (gone) return;
    gone = true;
    window.removeEventListener('keydown', key, true);
    window.removeEventListener('resize', fit);
    el.classList.add('is-leaving');
    if (!reduce) el.classList.add('is-swell');
    setTimeout(function () {
      if (p) p.settle();
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 620);
  }
  /* Any key skips him, and does nothing else: the canvas under him was not
   * in view. One with Ctrl, Cmd or Alt is the browser's, and goes on to it.
   * Listened for from here, on the window, as it reaches the page: this
   * script runs before the editors' own, so no shortcut of theirs hears it
   * first. */
  function key(e) {
    if (!p || gone) return;
    leave();
    if (!e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); e.stopImmediatePropagation(); }
  }
  window.addEventListener('keydown', key, true);

  Promise.race([Promise.all([player(), drawing()]), late()]).then(function (got) {
    var payload = got[1];
    var cs = payload.canvasSize || {};
    cw = cs.cssWidth || cw;
    ch = cs.cssHeight || ch;
    box.setAttribute('data-skribl-w', cw);
    box.setAttribute('data-skribl-h', ch);
    el.hidden = false;
    p = window.SkriblInline.attach(box, payload, { ambient: true, dpr: fit() });
    if (!p) { el.hidden = true; window.removeEventListener('keydown', key, true); return; }
    mark();
    el.addEventListener('pointerdown', leave);
    window.addEventListener('resize', fit);
    requestAnimationFrame(function () { el.classList.add('is-on'); });
    if (reduce) {
      // Still: the finished drawing, him at full size waving, the star lit, then the fade.
      light();
      setTimeout(leave, 1800);
      return;
    }
    p.toggle();
    // The star's light comes on as its page finishes drawing itself, and he
    // leaves after his first wave: the loop's one pass holds two.
    var H = window.SkriblHold, fps = payload.fps || 12, loop = payload.loop;
    var lit = H ? H.pageMs(payload.frames[0], fps) : 0;
    var wave = loop ? (loop.to - loop.from + 1) / 2 / fps * 1000 : 0;
    var end = (p.state().totalMs || 6000) - wave;
    var t0 = Date.now();
    (function watch() {
      if (gone) return;
      var at = p.state().elapsedMs || 0;
      if (at >= lit) light();
      if (at >= end - 40 || Date.now() - t0 > end + 3000) { leave(); return; }
      requestAnimationFrame(watch);
    })();
  }).catch(function () { el.hidden = true; window.removeEventListener('keydown', key, true); });
})();
