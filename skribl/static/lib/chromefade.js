/* Controls that step back while a drawing plays, and come back the moment
 * someone reaches for them.
 *
 * THE OWNER, from the full-screen mock: in full screen the controls fade a
 * moment after the drawing starts, and come back when the mouse moves or a
 * finger taps. Measured, that is what makes full screen full size: in a
 * 1333x906 window the Pad's drawing is 738px tall with the controls kept in a
 * band under it and 906 with them gone. The drawing takes the whole screen;
 * the controls lie over its foot when they are up.
 *
 * ONE RULE, EVERY SURFACE THAT GOES FULL SCREEN. This owns only WHEN: it
 * puts `chrome-asleep` on the root after a quiet spell and takes it off at
 * the first sign of a person. What fades is the page's CSS (styles.css,
 * "CONTROLS THAT STEP BACK", and fullbar.css for the Gallery's and the
 * Library's bar), so a surface cannot fade differently by accident.
 *
 * NEVER ASLEEP WHEN IT WOULD STRAND SOMEONE. `awake()` is the caller's: a
 * drawing paused part-way keeps its controls, so does an open menu. A
 * key, a focus moving in, a press and a mouse that moves all wake it.
 *
 * A FINISHED DRAWING IS SEEN WHOLE (the owner, after the full-screen A/B: the
 * drawing fills the screen, so the controls lie over its foot when they are
 * up). The caller pokes as it ends, so they come up with Play to see it again,
 * and its awake() says no, so they step back after the next quiet spell.
 *
 * THE FIRST TAP ON A FADED SCREEN ONLY BRINGS THEM BACK (the owner: "matching
 * how video apps work"), wherever `tapWakes` asks for it: a finger's press
 * while they are away is swallowed, and so is the click it makes, so it
 * neither pauses nor draws. The click matters as much as the press: the
 * in-post player pauses on a click, the editors and the link page on the
 * press (lib/tappause.js). A mouse has already woken them by moving there, so
 * its click is the page's.
 *
 *   SkriblChromeFade.attach(root, { awake, ms, tapWakes })
 *     -> { start, stop, poke, asleep }
 *   start()  begin watching (full screen opened); arms the first quiet spell
 *   stop()   stop watching and wake for good (full screen closed)
 *   poke()   wake and re-arm, for a caller whose state just changed
 */
(function (global) {
  'use strict';

  var ASLEEP = 'chrome-asleep';
  var MS = 2500;      // a quiet spell this long, while it plays, puts them away
  var STILL = 3;      // a mouse that moved less than this many px did not move

  function attach(root, o) {
    if (!root) return null;
    o = o || {};
    var ms = o.ms || MS;
    var awake = o.awake || function () { return false; };
    var on = false, timer = 0, last = null;

    function wake() {
      root.classList.remove(ASLEEP);
      arm();
    }
    function arm() {
      clearTimeout(timer);
      if (!on) return;
      timer = setTimeout(function () {
        if (!on) return;
        if (awake()) { arm(); return; }      // asked again after the next spell
        root.classList.add(ASLEEP);
      }, ms);
    }
    function moved(e) {
      if (e.pointerType === 'touch') return;          // a finger is a press, below
      var p = [e.clientX, e.clientY];
      var far = !last || Math.abs(p[0] - last[0]) >= STILL || Math.abs(p[1] - last[1]) >= STILL;
      last = p;
      if (far) wake();
    }
    function any() { wake(); }
    /* Registered here, ahead of start()'s own, so the press still finds them
       asleep; and a click is swallowed only just after a swallowed press, so
       a key's click never is. */
    var swallowTill = 0;
    if (o.tapWakes) {
      root.addEventListener('pointerdown', function (e) {
        swallowTill = 0;
        if (!on || e.pointerType === 'mouse' || !root.classList.contains(ASLEEP)) return;
        swallowTill = e.timeStamp + 1000;
        e.preventDefault();
        e.stopPropagation();
      }, true);
      root.addEventListener('click', function (e) {
        if (e.timeStamp > swallowTill) return;
        swallowTill = 0;
        e.preventDefault();
        e.stopPropagation();
      }, true);
    }

    function start() {
      if (on) return;
      on = true;
      last = null;
      root.addEventListener('pointermove', moved);
      root.addEventListener('pointerdown', any, true);
      root.addEventListener('focusin', any);
      global.document.addEventListener('keydown', any, true);
      wake();
    }
    function stop() {
      on = false;
      clearTimeout(timer);
      root.removeEventListener('pointermove', moved);
      root.removeEventListener('pointerdown', any, true);
      root.removeEventListener('focusin', any);
      global.document.removeEventListener('keydown', any, true);
      root.classList.remove(ASLEEP);
    }

    return {
      start: start,
      stop: stop,
      poke: function () { if (on) wake(); },
      asleep: function () { return root.classList.contains(ASLEEP); }
    };
  }

  global.SkriblChromeFade = { attach: attach, MS: MS };
})(window);
