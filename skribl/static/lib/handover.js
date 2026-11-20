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
 * IT IS A DIALOG, AND KEEPS A DIALOG'S PROMISES (its markup says
 * aria-modal; verify_a11y's census drives it as it drives every sheet). The
 * day it merged it kept one of four: focus went in, and then Tab walked out
 * of Your hand's last button to the browser (inside a host, to whatever the
 * host has under its composer), Shift+Tab out of its first, and Escape did
 * nothing at all. Now:
 *   - FOCUS IS ON THE LAYER WHILE YOUR HAND LOADS, and goes into its page
 *     the moment there is one. A frame still loading takes the keys and
 *     answers none of them, Escape included.
 *   - TAB STAYS IN. Two stops nobody sees, one each side of the frame
 *     (edge()), are the only other places in this page Tab can reach while
 *     the rest is inert. Each hands focus straight back: out of Your hand's
 *     last stop comes round to its first, out of its first to its last. They
 *     hold nothing, so the order inside is Your hand's own, untouched. A Tab
 *     pressed in this page (not in Your hand's) goes in the same way.
 *   - ESCAPE CLOSES IT. Pressed in Your hand's page it is that page's to
 *     answer, and it asks to be closed (editor_letters.js, wayOut); pressed
 *     here (while it loads, or after a click on the layer's own paper) it
 *     closes from here.
 *   - NO KEY REACHES THE EDITOR UNDER IT. inert stops a click and a Tab; it
 *     does not stop a shortcut, which the editors hear on the page itself.
 *     Ctrl+Z pressed while Your hand loaded would have taken a stroke off a
 *     drawing nobody could see. Every keydown stops here while it is up.
 *   - FOCUS GOES BACK with the caller's `back`: Text is chosen again and its
 *     words take focus (lib/textwrite.js, again), so this hands it nowhere
 *     itself.
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
  var ready = false;   // Your hand's page has loaded in the frame
  var edges = null;    // the two stops that keep Tab in (edge)
  var held = [];       // what this made inert, to put back

  /* What Tab can stop on, as the editors' own dialogs count it
     (lib/modalfocus.js). */
  var STOPS = [
    'a[href]:not([tabindex="-1"])', 'button:not([disabled]):not([tabindex="-1"])',
    'input:not([disabled]):not([tabindex="-1"])', 'select:not([disabled]):not([tabindex="-1"])',
    'textarea:not([disabled]):not([tabindex="-1"])', '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  /* Into Your hand, at one end: its first stop, or its last. Each is TRIED,
     not trusted: a control that is there but put away (hidden by a rule,
     out of reach under one of its pages) takes no focus and says nothing,
     so the next is asked until one has it. With no page yet, the layer keeps
     focus; with a page and no stop, the frame does. */
  function into(toLast) {
    if (!up || !frame) return;
    if (!ready) { layer.focus({ preventScroll: true }); return; }
    var d = null, list = [], i, el;
    try { d = frame.contentDocument; } catch (e) { d = null; }
    if (d) list = d.querySelectorAll(STOPS);
    for (i = 0; i < list.length; i++) {
      el = list[toLast ? list.length - 1 - i : i];
      if (!el.getClientRects().length) continue;
      try { el.focus(); } catch (e2) { continue; }
      if (d.activeElement === el) return;
    }
    frame.focus({ preventScroll: true });
  }

  /* One of the two stops round the frame. Focus that reaches it CAME OUT OF
     YOUR HAND (Tab off its last stop reaches the one after the frame,
     Shift+Tab off its first the one before) and goes back in at the other
     end. Nothing else reaches one: a Tab pressed in this page never gets to
     the browser (the keydown below), a finger cannot touch one, and a screen
     reader is told they are not there. (Which way focus came was first read
     from the event's relatedTarget, which is the frame the first time round
     and not the second: the walk stuck on Your hand's last button.) */
  function edge(after) {
    var s = doc.createElement('span');
    s.className = 'hand-over-edge';
    s.setAttribute('tabindex', '0');
    s.setAttribute('aria-hidden', 'true');
    s.addEventListener('focus', function () { into(!after); });
    return s;
  }

  function find() {
    if (layer) return true;
    layer = doc.getElementById('handOver');
    if (!layer) return false;
    layer.addEventListener('transitionend', function (e) {
      if (e.target === layer && !up) settle();
    });
    if (!layer.hasAttribute('tabindex')) layer.setAttribute('tabindex', '-1');
    edges = [edge(false), edge(true)];
    layer.insertBefore(edges[0], layer.firstChild);
    layer.appendChild(edges[1]);
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
    ready = false;
    frame.addEventListener('load', function () {
      if (!up) return;
      ready = true;
      layer.classList.add('is-ready');
      /* There is a page to take the keys now: focus goes in. */
      try { frame.focus({ preventScroll: true }); } catch (e) { /* the layer keeps it */ }
    });
    /* Over a post, or over a face being drawn (a host's ?face=1), where
       there is no post for Your hand to name. */
    frame.setAttribute('src', url + (url.indexOf('?') >= 0 ? '&' : '?') + 'over=' + (global.SKRIBL_FACE === true ? 'face' : '1'));
    layer.classList.remove('is-closing', 'is-ready');
    layer.insertBefore(frame, edges[1]);
    layer.hidden = false;
    /* Read a size, so the glide starts from where the layer rests closed. */
    void layer.offsetHeight;
    layer.classList.add('is-open');
    hold(true);
    /* On the layer while Your hand loads (the header: a frame still loading
       answers no key). */
    layer.focus({ preventScroll: true });
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

  /* A KEY PRESSED IN THIS PAGE WHILE IT IS UP (the header). On the window as
     the key arrives, before the editor's own shortcuts, which listen on the
     page: none of them hears it. Escape closes. Tab goes into Your hand, at
     its first stop or (with Shift) its last, and never to the browser's own
     walk: from the layer, which holds focus while Your hand loads, Shift+Tab
     has nothing before it in this page and went out to the browser. A key
     let go is not stopped, so one held down when it opened is not left
     held. */
  global.addEventListener('keydown', function (e) {
    if (!up) return;
    e.stopImmediatePropagation();
    if (e.key === 'Tab') { e.preventDefault(); into(e.shiftKey); return; }
    if (e.key !== 'Escape') return;
    e.preventDefault();
    close();
  }, true);

  global.SkriblHandOver = {
    open: open,
    close: close,
    isOpen: function () { return up; }
  };
})(typeof window !== 'undefined' ? window : this);
