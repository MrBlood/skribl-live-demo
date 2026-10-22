/* Skribl says hi: the first time Skribl opens, on any screen (FUTURE.md 6m).
 *
 * The mark writes itself with the real pen, the i's dot drops in, bounces
 * into place and winks (owner: "A, the wink. build it."), and the ink lifts
 * away into the canvas in the order it was written: the in-post player playing a Flip drawn through the real Flip
 * editor (brand/hello.json, harness/tools/make_hello.py, from the header's own
 * mark) on the page's own ground, light or dark. The owner's picks: once only,
 * a tap, a click or any key skips it, a still hello under Reduce Motion, one
 * module for the Pad and Flip.
 *
 * NOTHING IS FETCHED UNLESS IT COMES, which the page's head decides before
 * its first paint (_skribl_hello_boot.html; nothing here decides it again):
 * when this browser has never seen this hello, on a page of its own (not a
 * composer's frame). When it will not, its element goes at once, so
 * lib/learncard.js (one welcome at a time) can tell by looking. The player, the hold timing it reads and the drawing
 * are asked for first; it draws once the page's own scripts are done, and if
 * they are not here within LATE ms of that it does not come this time, and is
 * not marked seen, so the canvas is never held up waiting for it.
 *
 * SEEN IS PER HELLO: v1 was Blooby's, on his star, and someone who met him
 * meets the mark once too.
 *
 * ITS GROUND FROM THE FIRST PAINT (the owner, on a reload: "it goes to the
 * canvas first, then goes to the skribl cursive"). It shows once the page's
 * scripts and its files are here, and the page had painted the canvas by
 * then. When it comes, the head lays its ground over the page before the
 * first paint (styles.css, THE HELLO'S GROUND); the hello comes in over that,
 * the ground goes from under it as it leaves, and the canvas is first seen
 * as the ink lifts. The ground never holds up a page that is ready: once
 * the page's scripts are done it waits GRACE more for the files, then fades
 * (the hello can still come within LATE, over the canvas, as it used to); it
 * fades too when the hello does not come after all; and the head fades it
 * by itself at 8 s if nothing here ever runs.
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
  var KEY = 'skribl.hello.v2';   // the head reads the same key (_skribl_hello_boot.html)
  var LATE = 4000;
  var GRACE = 300;
  var BUDGET = 8e6;
  var root = document.documentElement;

  function mark() { try { localStorage.setItem(KEY, '1'); } catch (e) {} }
  function away() { if (el.parentNode) el.parentNode.removeChild(el); }
  // The ground the head laid: "up" while it waits, "on" under the hello.
  function cover() { return root.getAttribute('data-hello-cover'); }
  function lift() {
    if (cover() !== 'up' && cover() !== 'on') return;
    root.setAttribute('data-hello-cover', 'lift');
    setTimeout(function () { if (cover() === 'lift') root.removeAttribute('data-hello-cover'); }, 400);
  }

  if (!root.hasAttribute('data-hello-comes')) {
    away();
    return;
  }

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  /* UNDER REDUCE MOTION IT STILL FADES, coming and going (the owner's iPhone,
   * after v328: "it just disappears and opens the pad canvas screen"). Both
   * of the stylesheet's Reduce Motion rules take every transition to nothing,
   * and its fade went with them. A fade is not motion, so the hello keeps its
   * own, set on itself: an inline !important outranks a sheet's, and no
   * Reduce Motion rule is added to styles.css (it would ride into
   * player.css). Durations are the sheet's: in over 0.25 s, out over 0.45. */
  function fade(s) { if (reduce) el.style.setProperty('transition', 'opacity ' + s + 's ease', 'important'); }
  fade(0.25);
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
    // The ground goes from under it, so its own fade shows the canvas.
    root.removeAttribute('data-hello-cover');
    window.removeEventListener('keydown', key, true);
    window.removeEventListener('resize', fit);
    // Held where it is; at its end the player holds a Flip's last page whole.
    if (p && p.state().state === 'playing') p.pause();
    if (!reduce) {
      el.classList.add('is-lifting');
      void box.offsetWidth;
      el.classList.add('is-evaporating');
    }
    fade(0.45);
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

  /* A TAP THAT SKIPS IT PRESSES NOTHING ELSE (found building the hello's
   * mock). It lets go of the pointer the moment it starts to leave
   * (.is-leaving), and a phone makes a tap's click where the finger lifts, on
   * whatever is under it: a tap over the menu at the top right skipped the
   * hello and opened the menu. Ending that tap here makes no click at all; a
   * mouse's click never reached what was under it. A touchend is never
   * passive, so it may; and it holds no gesture, so it has no touchcancel to
   * pair with: a touch the system takes away makes no click (verify_tools
   * V214b names it). */
  function noClick(e) { if (gone) e.preventDefault(); }

  function never() { window.removeEventListener('keydown', key, true); lift(); away(); }

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
  var have = false;
  var files = Promise.all([player(), drawing()]);
  files.then(function () { have = true; }, function () {});   // a failure is said below, once the page is ready
  ready().then(function () {
    // The page is ready: its ground waits GRACE more for the hello, no longer.
    if (!have) setTimeout(function () { if (!p) lift(); }, GRACE);
    return Promise.race([files, late()]);
  }).then(function (got) {
    var payload = got[1];
    var cs = payload.canvasSize || {};
    cw = cs.cssWidth || cw;
    ch = cs.cssHeight || ch;
    box.setAttribute('data-skribl-w', cw);
    box.setAttribute('data-skribl-h', ch);
    el.hidden = false;
    p = window.SkriblInline.attach(box, payload, { ambient: true, dpr: fit() });
    if (!p) { never(); return; }
    // Over its ground now, which stays under it until it leaves.
    if (cover() === 'up') root.setAttribute('data-hello-cover', 'on');
    mark();
    // Once through, ending on the finished mark: a post loops, a hello does not.
    p.setLoop(false);
    el.addEventListener('pointerdown', leave);
    el.addEventListener('touchend', noClick);
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
