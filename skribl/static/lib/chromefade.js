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
 * "CONTROLS THAT STEP BACK"), so a surface cannot fade differently by
 * accident.
 *
 * NEVER ASLEEP WHEN IT WOULD STRAND SOMEONE. `awake()` is the caller's: a
 * paused or finished drawing keeps its controls, so does an open menu. A
 * key, a focus moving in, a press and a mouse that moves all wake it. What
 * else a press does is the caller's: the editors let a finger's first tap on
 * a faded screen only wake it, as a video app does (lib/watchfull.js).
 *
 *   SkriblChromeFade.attach(root, { awake, ms })
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
