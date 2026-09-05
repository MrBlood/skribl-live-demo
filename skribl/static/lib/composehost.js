/* The pad button's lifecycle, for a HOST's composer.
 *
 *   var pad = SkriblComposeHost.create({
 *     frame: document.getElementById('padFrame'),
 *     src:   document.body.getAttribute('data-skribl-compose'),
 *     onDone: function (payload, preview, hasAudio) { ... },
 *     onCancel: function () { ... }
 *   });
 *   padButton.addEventListener('click', pad.open);
 *
 * WHAT THIS OWNS, and why each of these is a rule rather than a preference.
 * Skribl's side of compose mode is two things: the editor at ?compose=1 and the
 * four postMessage types in editor_compose.js. The HOST's side is the sequence
 * below, and every host writes the same one — so it lives here once instead of
 * being retyped, correctly or otherwise, by everyone who mounts Skribl.
 *
 *   1. THE SRC IS SET ON FIRST OPEN, NEVER IN MARKUP. The Pad is a whole
 *      application with a stylesheet and thirty-odd scripts. A composer that
 *      puts src= in its HTML has charged every visitor for a drawing tool they
 *      never opened, on every page view of the feed.
 *   2. RE-OPENING AN ALREADY-LOADED EDITOR PUSHES THE PAYLOAD DIRECTLY.
 *      `skribl:compose:ready` fires once per load, so on the second press the
 *      iframe is still there and will not announce itself again. Be precise
 *      about what this buys, because the obvious claim — "otherwise the editor
 *      reopens empty" — is FALSE in the simple case and was written here before
 *      it was checked: the editor kept the author's drawing on its own canvas,
 *      so a host that answers only `ready` looks correct. What it is really
 *      doing is trusting the editor's retained state, which is a coincidence
 *      rather than a contract. This rule makes the editor show THE DRAFT'S
 *      payload every time, which is the difference the moment the two are not
 *      the same drawing — a host calling setPayload() to re-edit the Skribl on
 *      an already-saved post, into a frame still loaded from a previous
 *      compose. verify_compose.py counts the message rather than the ink,
 *      because the ink assertion stays green with this rule disabled.
 *   3. CLEARING RESETS THE FRAME TO about:blank. Otherwise "remove" leaves the
 *      editor loaded with the removed drawing, and the next pad press reopens
 *      exactly what was just thrown away.
 *   4. ORIGIN IS CHECKED IN AND TARGETED OUT, never '*'. Same-origin is the
 *      normal case — Skribl mounts as a blueprint — but a wildcard hands the
 *      author's drawing to whatever page is framing the editor, and the check
 *      on the way in is what stops another frame injecting one.
 *
 * WHAT THIS DOES NOT OWN: the overlay's appearance, the attachment preview, and
 * POSTING. Posting is the host's, and deliberately: a real host writes their own
 * row and stores the id on it, or calls skribl.create_post() server-side and
 * never posts from the browser at all. A module that posted for them would have
 * to guess which. See docs/INTEGRATION.md.
 *
 * NO ROUTE LITERALS. `src` is passed in, because only the server knows where
 * the blueprint is mounted (verify_seam.py SECTION 1 enforces this).
 *
 * NOT LOADED BY THE IN-POST PLAYER. A page that only DISPLAYS Skribls never
 * composes one, so this is not in skribl_inline_assets() and does not count
 * against the embed ratchet — the same reader-is-not-the-writer split
 * lib/postedcard.js is on.
 */
(function (global) {
  'use strict';

  var PREFIX = 'skribl:compose:';
  var BLANK = 'about:blank';

  function create(opts) {
    opts = opts || {};
    var frame = opts.frame;
    var src = opts.src;
    if (!frame || !src) {
      throw new Error('SkriblComposeHost.create needs {frame, src}. The src is '
                      + 'the editor URL the SERVER rendered (url_for), because '
                      + 'only the server knows the mount prefix.');
    }
    /* The host's own origin by default. A host serving Skribl from a different
       origin passes it, and must also set window.SKRIBL_COMPOSE_ORIGIN on the
       editor page so the two agree — the editor targets the host, not '*'. */
    var origin = opts.origin || global.location.origin;

    var payload = null;
    var loaded = false;
    var open_ = false;

    function post(type, data) {
      var msg = { type: PREFIX + type };
      if (data) for (var k in data) if (data.hasOwnProperty(k)) msg[k] = data[k];
      try {
        frame.contentWindow.postMessage(msg, origin);
      } catch (e) {
        /* The frame is not ready to receive yet. Not an error: `ready` is what
           tells us it is, and rule 2's direct push only runs when we already
           saw one. */
      }
    }

    function onMessage(e) {
      if (e.origin !== origin) return;
      if (frame.contentWindow && e.source !== frame.contentWindow) return;
      var d = e.data;
      if (!d || typeof d.type !== 'string' || d.type.indexOf(PREFIX) !== 0) return;
      var kind = d.type.slice(PREFIX.length);
      if (kind === 'ready') {
        loaded = true;
        /* Re-editing: hand back what the draft is holding. A first open has no
           payload and sends nothing, which is what leaves the canvas blank. */
        if (payload) post('load', { payload: payload });
        if (opts.onReady) opts.onReady();
      } else if (kind === 'done') {
        payload = d.payload;
        close();
        if (opts.onDone) opts.onDone(d.payload, d.preview, d.hasAudio);
      } else if (kind === 'cancel') {
        close();
        if (opts.onCancel) opts.onCancel();
      }
    }

    global.addEventListener('message', onMessage);

    function open() {
      open_ = true;
      if (frame.getAttribute('src') !== src) {
        /* First open, or reopened after a clear(). `ready` will arrive and
           rule 2 does not apply yet. */
        loaded = false;
        frame.setAttribute('src', src);
      } else if (loaded && payload) {
        /* RULE 2. Already loaded, so no second `ready` is coming; push the held
           drawing or the author reopens an empty canvas over their own work. */
        post('load', { payload: payload });
      }
      if (opts.onOpen) opts.onOpen();
    }

    function close() {
      if (!open_) return;
      open_ = false;
      if (opts.onClose) opts.onClose();
    }

    function clear() {
      payload = null;
      loaded = false;
      /* RULE 3. Drop the editor as well as the payload, so the next open starts
         blank rather than reopening the drawing just removed. */
      frame.setAttribute('src', BLANK);
    }

    return {
      open: open,
      close: close,
      clear: clear,
      isOpen: function () { return open_; },
      payload: function () { return payload; },
      /* Re-editing a Skribl already on a saved post: give the module the
         payload before the first open and `ready` will carry it in. */
      setPayload: function (p) { payload = p || null; },
      destroy: function () {
        global.removeEventListener('message', onMessage);
        frame.setAttribute('src', BLANK);
        payload = null;
        loaded = false;
      }
    };
  }

  global.SkriblComposeHost = { create: create };
})(window);
