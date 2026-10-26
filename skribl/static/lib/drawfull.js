/* Draw in full screen, on a desk: the page itself goes full screen, the
 * header and the dock with it, and the canvas takes the room.
 *
 * THE OWNER, after the measured mock ("All yes" to A, built on B): a button at
 * the dock's end, after Magnify, on a desk only, and the drawers open where
 * they open today, under the dock. On a 1920x1080 screen the Pad's canvas
 * goes from B's 1017x763 to about 1197x898.
 *
 * ONE MODULE, BOTH EDITORS. Each editor already sizes its canvas to the room
 * it has and redraws it sharp at that size (lib/chromefit.js, app.js
 * layoutEditorCanvas, flip.js fitPad), so going full screen is all this does:
 * the window grows, and the canvas follows as it does when a window is
 * dragged bigger.
 *
 * THE REAL THING OR NOTHING. Going full screen is lib/immersive.js, and its
 * stand-in (an element pinned over the page, for the iPhone) means nothing for
 * the page itself, which already fills the window. So where the API cannot
 * take the page -- an iPhone, a frame that does not allow it -- the button
 * stays hidden: a button that cannot work is not put on screen.
 *
 * NOT THE WATCH. lib/watchfull.js plays the drawing as big as the screen goes,
 * with nothing to draw with; this keeps every tool. Watching from here comes
 * back here: the browser keeps the two full screens one inside the other.
 *
 * ON WEARS THE DOCK'S ON TILE, as Magnify and Media do (styles.css: the
 * controls that are on rather than selected), and its words say how out.
 * Escape leaves too: the browser owns that key in a real full screen.
 */
(function (global) {
  'use strict';

  var doc = global.document;

  function attach(btn) {
    if (!btn || !global.SkriblImmersive) return null;
    var full = global.SkriblImmersive.attach(doc.documentElement, { onChange: sync });
    if (!full.isNative()) return null;

    function sync(on) {
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.setAttribute('aria-label', on ? 'Leave full screen' : 'Draw in full screen');
      btn.title = on ? 'Leave full screen (Esc)' : 'Draw in full screen';
    }

    sync(false);
    btn.hidden = false;
    btn.addEventListener('click', full.toggle);
    return full;
  }

  global.SkriblDrawFull = { attach: attach, view: attach(doc.getElementById('drawFullBtn')) };
})(window);
