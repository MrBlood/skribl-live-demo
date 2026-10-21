/* Skribl says hi: the first time Skribl opens, on any screen (FUTURE.md 6m).
 *
 * The mark writes itself with the real pen, the i's dot drops in and bounces
 * into place, and the ink lifts away into the canvas in the order it was
 * written: the in-post player playing a Flip drawn through the real Flip
 * editor (brand/hello.json, harness/tools/make_hello.py, from the header's own
 * mark) on the page's own ground, light or dark. The owner's picks: once only,
 * a tap, a click or any key skips it, a still hello under Reduce Motion, one
 * module for the Pad and Flip.
 *
 * NOTHING IS FETCHED UNLESS IT COMES. It comes when this browser has never
 * seen this hello, on a page of its own (not a composer's frame). When it will
 * not, its element goes at once, so lib/learncard.js (one welcome at a time)
 * can tell by looking. The player, the hold timing it reads and the drawing
 * are asked for first; it draws once the page's own scripts are done, and if
 * they are not here within LATE ms of that it does not come this time, and is
 * not marked seen, so the canvas is never held up waiting for it.
 *
 * SEEN IS PER HELLO: v1 was Blooby's, on his star, and someone who met him
 * meets the mark once too.
 *
 * THE REPLAY LINK (owner: "Yes to the replay link"): an address with
 * ?hello=again plays it on that open, seen or not, and asks for it as a
 * suite does. Every load that carries it plays it, so a reload replays it.
 * Never in a composer's frame, all the same.
 *
 * AUTOMATION NEVER MEETS IT unless it asks (window.__skriblHelloForce, set
 * before the page loads): every suite opens a fresh browser, and a hello on
 * top of every first canvas would be in each one's way. verify_hello asks.
 *
 * SHARP (owner: "I was hoping for a super crisp look, but it looks kind of
 * blurry"). Its box sits on whole screen pixels and the drawing fills it at a
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
  var KEY = 'skribl.hello.v2';
  var LATE = 4000;
  var BUDGET = 8e6;
  var again = /[?&]hello=again(&|$)/.test(location.search);
  var force = window.__skriblHelloForce === true || again;

  function seen() { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return true; } }
  function mark() { try { localStorage.setItem(KEY, '1'); } catch (e) {} }
  function away() { if (el.parentNode) el.parentNode.removeChild(el); }

  if ((navigator.webdriver && !force) || (seen() && !again) || window.top !== window || /[?&]compose=1\b/.test(location.search)) {
    away();
    return;
  }

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stage = el.querySelector('.skribl-hello-stage');
  var box = el.querySelector('.skribl-inline');

  /* THE PLAYER, AND THE HOLD TIMING IT READS as it takes a Flip
   * (lib/holdtiming.js). The page has its own copy, among its deferred
   * scripts, which run after this one: on a slow line the player and the
   * drawing came first, and the mark played as plain pages, all at once and
   * gone in 0.8 s. The same file as the page's, so one of the two is the
   * cache's.
   *
   * ASKED FOR FIRST (owner: "Why does it not show every time in
   * incognito"). An empty cache, as every private window has, on a slow
   * line: the three files were asked for after the editor's hundred-odd
   * scripts and came with them, 6.5 s into LATE's 4 on 3G, so it did not
   * come. At high priority they are here within its first second, long
   * before the page's own scripts are done, which is when it draws (below). */
  function script(src, name) {
    if (window[name]) return Promise.resolve();
    return new Promise(function (done, fail) {
      var js = document.createElement('script');
      js.src = src;
      js.fetchPriority = 'high';
      js.onload = function () { if (window[name]) done(); else fail(); };
      js.onerror = fail;
      document.head.appendChild(js);
    });
  }
  function player() {
    if (!window.SkriblInline) {
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = el.getAttribute('data-player-css');
      document.head.appendChild(css);
    }
    return Promise.all([script(el.getAttribute('data-hold-js'), 'SkriblHold'),
                        script(el.getAttribute('data-player-js'), 'SkriblInline')]);
  }
  function drawing() {
    return fetch(el.getAttribute('data-hello'), { priority: 'high' }).then(function (r) {
      if (!r.ok) throw new Error('hello ' + r.status);
      return r.json();
    });
  }
  function late() { return new Promise(function (done, fail) { setTimeout(fail, LATE); }); }

  /* THE BOX ON THE GRID: a whole number of the drawing's own steps (9 x 16
   * screen pixels for a 9:16 drawing), as big as the screen allows, centred
   * on whole screen pixels. Returns the drawing's pixels a point that fill it
   * exactly. On a resize (a turned phone) the box moves and the drawing keeps
   * its pixels until it leaves. */
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
  /* THE WAY OUT: the frame it is on holds, and the ink lifts away in the
   * order it was written while the ground fades into the canvas (styles.css,
   * .is-evaporating). The edge goes in place first, all of the ink still
   * showing, so the way out moves from it; and the ground's fade starts in
   * the same breath as the ink's, so its wait is the evaporating one. Under
   * Reduce Motion it all just fades: decided here rather than by a media
   * query there, which would ride into player.css (cssgraph keeps every one). */
  function leave() {
    if (gone) return;
    gone = true;
    window.removeEventListener('keydown', key, true);
    window.removeEventListener('resize', fit);
    // Held where it is; at its end the player holds a Flip's last page whole.
    if (p && p.state().state === 'playing') p.pause();
    if (!reduce) {
      el.classList.add('is-lifting');
      void box.offsetWidth;
      el.classList.add('is-evaporating');
    }
    el.classList.add('is-leaving');
    setTimeout(function () {
      if (p) p.settle();
      away();
    }, reduce ? 470 : 1070);
  }
  /* Any key skips it, and does nothing else: the canvas under it was not
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

  function never() { window.removeEventListener('keydown', key, true); away(); }

  /* THE PAGE'S OWN SCRIPTS FIRST, THEN THE HELLO. Its files are asked for
   * now, and first, but it draws once the page's scripts are done
   * (DOMContentLoaded), as it always did on a fast line: started while they
   * still ran, on a slowed phone over a slow line it froze for up to 0.65 s
   * at a time as each one did. LATE counts from then. */
  function ready() {
    return new Promise(function (done) {
      if (document.readyState === 'complete') { done(); return; }
      document.addEventListener('DOMContentLoaded', function () { done(); });
      window.addEventListener('load', function () { done(); });
    });
  }
  var files = Promise.all([player(), drawing()]);
  files.catch(function () {});   // said below, once the page is ready
  ready().then(function () { return Promise.race([files, late()]); }).then(function (got) {
    var payload = got[1];
    var cs = payload.canvasSize || {};
    cw = cs.cssWidth || cw;
    ch = cs.cssHeight || ch;
    box.setAttribute('data-skribl-w', cw);
    box.setAttribute('data-skribl-h', ch);
    el.hidden = false;
    p = window.SkriblInline.attach(box, payload, { ambient: true, dpr: fit() });
    if (!p) { never(); return; }
    mark();
    // Once through, ending on the finished mark: a post loops, a hello does not.
    p.setLoop(false);
    el.addEventListener('pointerdown', leave);
    window.addEventListener('resize', fit);
    requestAnimationFrame(function () { el.classList.add('is-on'); });
    if (reduce) {
      // Still: the finished mark, its dot in place, then the fade. At rest,
      // with no card, the player shows a Flip's last page whole: that mark.
      setTimeout(leave, 1800);
      return;
    }
    p.toggle();
    // It goes once the dot is at rest over the i: the end of the drawing.
    var end = p.state().totalMs || 3000;
    var t0 = Date.now();
    (function watch() {
      if (gone) return;
      var at = p.state().elapsedMs || 0;
      if (at >= end - 40 || Date.now() - t0 > end + 3000) { leave(); return; }
      requestAnimationFrame(watch);
    })();
  }).catch(never);
})();
