/* COMPOSE MODE: the Pad opened from a host's post composer.
 *
 * ===========================================================================
 * WHAT IT IS, AND THE ONE RULE THAT SHAPES EVERYTHING ELSE
 * ===========================================================================
 *
 * A host's composer has a row of attachment buttons — photo, video, GIF, poll —
 * and one of them is a Skribl. Pressing it opens this editor over their feed;
 * you draw; you press "Add to post"; the drawing goes back to their draft and
 * appears inline in the post they are still writing. Press it again and the
 * editor reopens with the drawing in it. Their Post button publishes the whole
 * thing.
 *
 * THE RULE: COMPOSE MODE PUBLISHES NOTHING. It hands back the PAYLOAD, not an
 * id. This is the difference between an attachment and a post, and it is not a
 * preference — the alternative does not work:
 *
 *   * POST /api/skribls is CREATE-ONLY. There is no update route (routes.py
 *     registers one POST and two GETs). So "publish on Add, republish on edit"
 *     means every edit ORPHANS the previous skribl, and each one has spent a
 *     slot of the author's posting quota (ratelimit.py) on a drawing nobody
 *     will ever see.
 *   * A draft that is abandoned — closed tab, changed mind, "actually I'll post
 *     this tomorrow" — would have left a published, shareable skribl behind
 *     with no post attached to it. There is no way for the host to withdraw it.
 *
 * Holding the payload costs the host memory on a draft they are already
 * holding, and buys exactly the semantics an image attachment has. The single
 * POST happens once, when they post.
 *
 * ===========================================================================
 * WHAT IS HANDED BACK IS WHAT PAD WOULD HAVE POSTED
 * ===========================================================================
 *
 * editor_post.js's buildPostPayload() runs first and in full: the share-card
 * thumbnail (which becomes /s/<id>/card.png, which is the in-post player's idle
 * poster) and the mono audio bake that halves a music-bearing row. Those are
 * post-time steps, and a composed skribl that skipped them would be a second,
 * quietly different kind of post — the exact defect that file's BUG B note
 * records, one path silently stopping while the metadata looked identical.
 * There is one builder and both endings call it.
 *
 * ===========================================================================
 * THE HANDSHAKE
 * ===========================================================================
 *
 * postMessage, both ways, even though the intended deployment is SAME-ORIGIN.
 * Skribl mounts into a Flask host as a blueprint (docs/INTEGRATION.md), so the
 * overlay is normally an iframe on the host's own origin and a direct call into
 * contentWindow would work. postMessage anyway, for two reasons: it is the same
 * code if the host ever runs Skribl on its own deployment, and it keeps the
 * boundary explicit rather than letting host and editor reach into each other's
 * globals. targetOrigin is the editor's own origin by default, so a mis-mounted
 * cross-origin embed fails loudly instead of leaking a drawing to whoever is
 * framing it.
 *
 *   editor -> host   skribl:compose:ready    {editor} the editor is up; send
 *                                            a payload now if this is a re-edit
 *   host   -> editor skribl:compose:load     {payload} put this back on canvas
 *   editor -> host   skribl:compose:done     {payload, preview, hasAudio, editor}
 *
 * `editor` is 'pad' or 'flip' (v316). Composing, the Pad's ⋯ "Flip Mode" row
 * opens Flip in the same frame and Flip's "Skribl Pad" row comes back, so the
 * frame can hold either editor. A payload goes back only into the editor that
 * made it: a one-page Flip and a Pad drawing are both `playbackMode: 'replay'`,
 * so the payload cannot say which it is, and the message does.
 *   editor -> host   skribl:compose:cancel   closed without attaching
 *
 * `preview` is a flat PNG of the finished drawing, so the host can show
 * something the instant the overlay closes without waiting on anything. The
 * real in-post player renders the payload itself (SkriblInline.attach).
 */
(function (global) {
  'use strict';

  var doc = global.document;

  /* Where messages go. The host may declare an origin explicitly for a
   * cross-origin deployment; otherwise it is this page's own origin, which is
   * the same-origin blueprint case and is also the safe default — a wildcard
   * would post the drawing to whatever page happens to be framing us. */
  var HOST_ORIGIN = global.SKRIBL_COMPOSE_ORIGIN || global.location.origin;
  /* Which editor this is. Set by its template; the Pad is the default. */
  var EDITOR = global.SKRIBL_COMPOSE === 'flip' ? 'flip' : 'pad';

  function send(type, data) {
    var msg = { type: type };
    if (data) for (var k in data) if (Object.prototype.hasOwnProperty.call(data, k)) msg[k] = data[k];
    try {
      var target = global.parent && global.parent !== global ? global.parent : global.opener;
      if (target) target.postMessage(msg, HOST_ORIGIN);
    } catch (e) {
      /* No host listening (someone opened ?compose=1 directly). Not an error
       * worth breaking the editor over — the drawing surface still works. */
    }
  }

  /* The title and caption fields are HIDDEN here, not removed. The host's own
   * composer already has the text box for this post; a second title field
   * inside the overlay asks the same question twice and the answers then
   * disagree. buildPostPayload() still reads the inputs — they are empty, so
   * the payload gets the "Untitled Skribl" default — and the host sets a real
   * title from their post's text when they publish, which is what /s/<id>
   * unfurls with. */
  function hideDuplicateFields() {
    var fields = doc.querySelector('#postSheet .post-fields');
    if (fields) fields.hidden = true;
    /* "Watch your Skribl" is a link to a post that does not exist yet. */
    var watch = doc.getElementById('postWatchBtn');
    if (watch) watch.hidden = true;
  }

  var api = {
    /* Called by editor_post.js's submit() once the payload is fully prepared.
     * Everything post-time has already happened by here. */
    deliver: function (payload, preview) {
      var media = global.SkriblPayload
        ? global.SkriblPayload.currentFrameMedia(payload)
        : (payload && payload.frames && payload.frames[0]) || null;
      send('skribl:compose:done', {
        payload: payload,
        preview: preview || null,
        hasAudio: !!(media && media.music && media.music.data),
        editor: EDITOR
      });
    },
    /* The host closing the overlay itself does not need this; it is for a
     * Cancel inside the editor, so the host can drop a spinner or restore
     * focus without guessing. */
    cancel: function () { send('skribl:compose:cancel'); }
  };
  global.SkriblCompose = api;

  global.addEventListener('message', function (e) {
    if (e.origin !== HOST_ORIGIN) return;
    var d = e.data;
    if (!d || d.type !== 'skribl:compose:load' || !d.payload) return;
    /* Re-editing. loadSkribl() is the same function the player and the
     * draft-restore path use, so a re-opened drawing is restored exactly as a
     * loaded draft is — including its pauseMode, which decides replay timing.
     * Flip supplies its own loader (window.SkriblComposeLoad). */
    if (typeof global.SkriblComposeLoad === 'function') global.SkriblComposeLoad(d.payload);
    else if (typeof loadSkribl === 'function') loadSkribl(d.payload);
  });

  /* ADD IS NEVER GREYED OUT HERE (owner, mock A2). Standalone, a dimmed Post
   * from first paint says "this is where posting will happen". Opened from a
   * composer, the author arrived to add a drawing, the dimmed Add looked broken,
   * and a disabled button cannot say why. So in compose mode the editors keep
   * deciding WHEN there is something to add -- app.js and flip.js still write
   * postBtn.disabled exactly as before -- and this turns that into
   * data-waiting: the button looks ready, stays focusable, and a press says
   * what is missing, in the toast both editors already speak through (a
   * role=status region). Not aria-disabled: styles.css dims and deafens
   * anything carrying that, and a button that answers is not disabled.
   *
   * The property is shadowed ON THIS ONE ELEMENT, so every existing write and
   * read keeps its meaning; only the attribute that greys and deafens the
   * button is never set. The capture listener on the window runs before either
   * editor's own click handler. */
  var WAIT_MSG = 'Draw something first, then Add';
  function addAlwaysReady() {
    var btn = doc.getElementById('postBtn');
    if (!btn) return;
    var native = Object.getOwnPropertyDescriptor(HTMLButtonElement.prototype, 'disabled');
    var waiting = native.get.call(btn);
    function show(v) {
      waiting = !!v;
      native.set.call(btn, false);
      if (waiting) btn.setAttribute('data-waiting', '');
      else btn.removeAttribute('data-waiting');
    }
    Object.defineProperty(btn, 'disabled', {
      configurable: true,
      get: function () { return waiting; },
      set: show
    });
    show(waiting);
    global.addEventListener('click', function (e) {
      if (!waiting || !e.target || !e.target.closest || e.target.closest('#postBtn') !== btn) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (typeof global.showToast === 'function') global.showToast(WAIT_MSG, btn);
      else if (typeof global.chip === 'function') global.chip(WAIT_MSG);
    }, true);
  }

  function ready() {
    hideDuplicateFields();
    addAlwaysReady();
    /* The header's × (compose mode only): back to the host's post. The host
     * closes its overlay on cancel and keeps the frame, so the drawing is
     * still there when the author presses the Skribl button again. */
    var close = doc.getElementById('composeCloseBtn');
    if (close) close.addEventListener('click', api.cancel);
    /* Announced AFTER the editor's own scripts have run, so a host that replies
     * immediately with a payload finds loadSkribl() defined. */
    send('skribl:compose:ready', { editor: EDITOR });
  }

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', ready);
  else ready();
})(typeof window !== 'undefined' ? window : this);
