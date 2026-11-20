/* YOUR HAND, OVER THE EDITOR: for the Pad or Flip inside a host's post
 * (compose mode). The owner's "All yes" (Nov 19) to B of the Text drawer
 * mock: "Your hand opens over your post, and your drawing waits for you."
 *
 * WHAT WAS WRONG. Make yours and Edit your hand (lib/textwrite.js, toHand)
 * WENT to Your hand: the frame a host's composer holds left the editor for
 * /skribl-pad?letters=1. Compose keeps no draft, so the drawing was gone (126
 * strokes, then none), and Close came back to the editor BY ITSELF: "Post to
 * Skribl" where "Add to post" had been, and no way back to the post.
 *
 * WHAT THIS DOES. Inside a post, Your hand opens OVER the editor, in a frame
 * of its own, and the editor never leaves: its drawing, its Undo, its take,
 * its photo and its music are under it exactly as they were, because nothing
 * was unloaded and nothing had to be put back. Your hand keeps its letters
 * where it always has (this device's store), and the Text drawer reads that
 * store each time it is asked (textwrite's readHand), so when Your hand goes
 * the drawer has the new letters without being told.
 *
 *   SkriblHandOver.open(url, back)   true when it took the trip: compose
 *                                    mode, its layer in the page. Anywhere
 *                                    else false, and the caller goes to Your
 *                                    hand as it always did.
 *
 * `url` is Your hand's own address as the server wrote it on the Text
 * drawer (data-hand; no route is written here). It is opened with over=1
 * (over=face from the Pad a host opened for somebody's face, where there is
 * no post to name), which is how that page knows to say where the drawing
 * is, to leave out Post your letters (it posts to Skribl, not to this post)
 * and to ASK TO BE CLOSED where it used to go somewhere (editor_letters.js).
 * `back` is called once it has gone.
 *
 * THE ONE MESSAGE, from Your hand to the editor that opened it:
 *   skribl:hand:close     Close, Done, Finish later or Write with it
 * taken only from this page's own origin and only from the frame this
 * opened, as compose's messages are (editor_compose.js).
 *
 * THE FRAME IS MADE WHEN IT OPENS AND TAKEN OUT WHEN IT HAS GONE. Your hand
 * is the whole Pad again (a stylesheet and thirty-odd scripts): nobody who
 * never opens it loads it, and once it has gone it is not kept. A new frame
 * each time also leaves the browser's Back alone: a frame's first address
 * takes the place of its empty one, where a second address in a kept frame
 * would be a step Back could undo.
 *
 * HOW IT MOVES (handover.css). It glides up over the editor and back down;
 * under Reduce Motion it fades where it sits. While it is up the editor
 * under it is out of reach (inert), and comes back as it was.
 *
 * COMPOSE ONLY: its template loads it there alone. On the editors' own pages
 * Make yours goes to Your hand as it always did, and the page's own draft
 * keeps the drawing for that trip.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var CLOSE = 'skribl:hand:close';
  /* Longer than the glide, in case its transitionend never comes (a tab put
     in the background as it goes). */
  var SETTLE_MS = 450;

  var layer = null, frame = null, back = null, timer = 0, up = false;
  var held = [];   // what this made inert, to put back

  function find() {
    if (layer) return true;
    layer = doc.getElementById('handOver');
    if (!layer) return false;
    layer.addEventListener('transitionend', function (e) {
      if (e.target === layer && !up) settle();
    });
    return true;
  }

  /* The editor under it, out of reach while it is up: everything else in the
     page, except what was out of reach already. */
  function hold(on) {
    var i;
    if (!on) {
      for (i = 0; i < held.length; i++) held[i].removeAttribute('inert');
      held = [];
      return;
    }
    var kids = doc.body.children;
    for (i = 0; i < kids.length; i++) {
      var k = kids[i];
      if (k === layer || k.tagName === 'SCRIPT' || k.tagName === 'TEMPLATE' || k.hasAttribute('inert')) continue;
      k.setAttribute('inert', '');
      held.push(k);
    }
  }

  function open(url, then) {
    if (!global.SKRIBL_COMPOSE || !url || !find()) return false;
    if (up) return true;
    up = true;
    back = then || null;
    clearTimeout(timer);
    if (frame && frame.parentNode) frame.parentNode.removeChild(frame);
    frame = doc.createElement('iframe');
    frame.className = 'hand-over-frame';
    frame.setAttribute('title', layer.getAttribute('data-title') || 'Your hand');
    frame.addEventListener('load', function () { if (up) layer.classList.add('is-ready'); });
    /* Over a post, or over a face being drawn (a host's ?face=1), where
       there is no post for Your hand to name. */
    frame.setAttribute('src', url + (url.indexOf('?') >= 0 ? '&' : '?') + 'over=' + (global.SKRIBL_FACE === true ? 'face' : '1'));
    layer.classList.remove('is-closing', 'is-ready');
    layer.appendChild(frame);
    layer.hidden = false;
    /* Read a size, so the glide starts from where the layer rests closed. */
    void layer.offsetHeight;
    layer.classList.add('is-open');
    hold(true);
    try { frame.focus({ preventScroll: true }); } catch (e) { /* not focusable yet */ }
    return true;
  }

  /* Gone: the frame taken out, and the editor told. */
  function settle() {
    if (up || !layer || layer.hidden) return;
    clearTimeout(timer);
    layer.hidden = true;
    layer.classList.remove('is-closing', 'is-ready');
    if (frame && frame.parentNode) frame.parentNode.removeChild(frame);
    frame = null;
    var then = back;
    back = null;
    if (then) then();
  }

  function close() {
    if (!up) return;
    up = false;
    layer.classList.add('is-closing');
    layer.classList.remove('is-open');
    hold(false);
    clearTimeout(timer);
    timer = setTimeout(settle, SETTLE_MS);
  }

  global.addEventListener('message', function (e) {
    if (!up || !frame || e.origin !== global.location.origin || e.source !== frame.contentWindow) return;
    if (e.data && e.data.type === CLOSE) close();
  });

  global.SkriblHandOver = {
    open: open,
    close: close,
    isOpen: function () { return up; }
  };
})(typeof window !== 'undefined' ? window : this);
