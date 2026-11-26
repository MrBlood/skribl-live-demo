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
 *   host   -> editor skribl:compose:guide    {file} a face's photo to trace
 *   host   -> editor skribl:compose:underlay {payload, first} draw back: a
 *                                            drawing faint under the pen
 *                                            (lib/drawback.js)
 *   host   -> editor skribl:compose:say      {button, lead, rest, aside}
 *                                            what the host is making (below)
 *   host   -> editor skribl:compose:help     open How it works (lib/ask.js):
 *                                            a host's own page explaining
 *                                            the host, sending people on to
 *                                            the editor's own help
 *
 * `guide` is a face's only (?face=1, after v330): a photo the host's page
 * picked, under the canvas as a guide to trace (editor_face.js). It is never
 * part of the face: what goes back on done is the lines alone. Anywhere else
 * the Pad ignores it.
 *
 * `say` names what the host is making (Nov 26, the Skribl site's drawn letters;
 * lib/composehost.js say): the word on the header's button and the post sheet's
 * (`button`, "Send"), a pill under the header (`lead` bold, then `rest`; while
 * drawing back, Draw back's own pill says them, lib/drawback.js words), and
 * what steps aside, dimmed and saying why when tapped, as Draw back's do
 * (`aside.media`: the picture and music drawer; `aside.editor`: the door to
 * the other editor). Pad and Flip: this file serves both.
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

  /* WHAT THE SHEET ASKS HERE is the template's to say (_skribl_post.html),
   * from the first frame: no title, because the host's own composer already
   * has the words for this post and a second title field asks the same
   * question twice; "Viewers start at", which is part of the drawing; and,
   * when the host asked for it (?gallery=1), "Show in the Skribls gallery"
   * with the gallery caption that opens under it (lib/postsheet.js). It used
   * to hide the whole block from here, "Viewers start at" with it. The title
   * input is still in the page, hidden: buildPostPayload() reads it, gets the
   * "Untitled Skribl" default, and the host sets a real title from their
   * post's text when they publish, which is what /s/<id> unfurls with. */
  function hideDuplicateFields() {
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

  /* ---- what the host is making (skribl:compose:say) --------------------- */
  var aside = {};
  var ASIDE = { media: '#mediaOpenBtn', editor: '#flipBtn, #padBtn' };
  var sayPill = null;
  function tell(words, near) {
    if (typeof global.showToast === 'function') global.showToast(words, near || null);
    else if (typeof global.chip === 'function') global.chip(words);
  }
  /* What steps aside is held at the press, before the editor's own handler:
     dimmed (styles.css body.compose-aside-*), and a tap says why. */
  var guarding = false;
  function guardAside() {
    if (guarding) return;
    guarding = true;
    ['click', 'input', 'pointerdown'].forEach(function (type) {
      doc.addEventListener(type, function (e) {
        if (!e.target || !e.target.closest) return;
        for (var k in ASIDE) {
          if (!aside[k]) continue;
          var hit = e.target.closest(ASIDE[k]);
          if (!hit) continue;
          e.preventDefault();
          e.stopImmediatePropagation();
          if (type === 'click') tell(aside[k], hit);
          return;
        }
      }, true);
    });
  }
  function canvasEl() { return doc.getElementById('canvas') || doc.getElementById('pad'); }
  /* THE PILL ON FRESH PAPER: Draw along's pill, under the header, saying what
     this is and for whom. It stays while it is clear of the drawing; one that
     lies over the drawing fades away at the first stroke, so nothing sits on
     what is being drawn (the owner, Nov 23, of Draw back's pill). */
  function placePill() {
    if (!sayPill) return;
    var head = doc.querySelector('.header');
    var b = head ? head.getBoundingClientRect().bottom : 0;
    sayPill.style.top = Math.max(8, b + 8) + 'px';
  }
  function dropPill() {
    var p = sayPill;
    sayPill = null;
    global.removeEventListener('resize', placePill);
    if (!p) return;
    if (!p.animate) { p.remove(); return; }
    var a = p.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, easing: 'ease', fill: 'forwards' });
    a.onfinish = function () { p.remove(); };
  }
  function pillWords(el, lead, rest) {
    el.textContent = '';
    if (lead) {
      var b = doc.createElement('b');
      b.textContent = lead;
      el.appendChild(b);
    }
    if (rest) el.appendChild(doc.createTextNode(rest));
  }
  function showPill(lead, rest) {
    if (global.SkriblDrawBack && global.SkriblDrawBack.state && global.SkriblDrawBack.state()) {
      if (sayPill) dropPill();
      if (global.SkriblDrawBack.words) global.SkriblDrawBack.words(lead, rest);
      return;
    }
    if (!lead && !rest) { dropPill(); return; }
    if (!sayPill) {
      sayPill = doc.createElement('div');
      sayPill.className = 'da-pill cs-pill';
      sayPill.setAttribute('role', 'note');
      var w = doc.createElement('span');
      w.className = 'da-where cs-where';
      sayPill.appendChild(w);
      doc.body.appendChild(sayPill);
      global.addEventListener('resize', placePill);
      var down = null;
      var onDown = function (e) { down = (e.isPrimary && e.target === canvasEl()) ? { x: e.clientX, y: e.clientY, d: 0 } : null; };
      var onMove = function (e) { if (down && e.isPrimary) down.d = Math.max(down.d, Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y)); };
      var onUp = function () {
        var was = down;
        down = null;
        if (!was || was.d <= 6 || !sayPill) return;
        var cv = canvasEl(), a = sayPill.getBoundingClientRect(), c = cv ? cv.getBoundingClientRect() : null;
        if (c && a.bottom > c.top && a.top < c.bottom && a.right > c.left && a.left < c.right) {
          doc.removeEventListener('pointerdown', onDown, true);
          doc.removeEventListener('pointermove', onMove, true);
          doc.removeEventListener('pointerup', onUp, true);
          dropPill();
        }
      };
      doc.addEventListener('pointerdown', onDown, true);
      doc.addEventListener('pointermove', onMove, true);
      doc.addEventListener('pointerup', onUp, true);
    }
    pillWords(sayPill.firstChild, lead, rest);
    sayPill.setAttribute('aria-label', (lead || '') + (rest || ''));
    placePill();
  }
  function onSay(d) {
    var word = typeof d.button === 'string' ? d.button.slice(0, 24) : '';
    if (word) {
      ['#postBtn .btn-label', '#postSubmitLabel'].forEach(function (sel) {
        var el = doc.querySelector(sel);
        if (el) el.textContent = word;
      });
      /* The sheet puts its idle word back each time it opens (lib/postsheet.js):
         this one, from now on. */
      var sub = doc.getElementById('postSubmitLabel');
      if (sub) sub.setAttribute('data-idle', word);
      var pb = doc.getElementById('postBtn');
      if (pb) pb.title = word;
    }
    aside = {};
    var a = d.aside && typeof d.aside === 'object' ? d.aside : {};
    for (var k in ASIDE) {
      if (typeof a[k] === 'string' && a[k]) aside[k] = a[k].slice(0, 160);
      doc.body.classList.toggle('compose-aside-' + k, !!aside[k]);
    }
    guardAside();
    showPill(typeof d.lead === 'string' ? d.lead.slice(0, 60) : '', typeof d.rest === 'string' ? d.rest.slice(0, 160) : '');
  }
  api.said = function () { return { aside: Object.keys(aside), pill: !!sayPill }; };

  global.addEventListener('message', function (e) {
    if (e.origin !== HOST_ORIGIN) return;
    var d = e.data;
    if (d && d.type === 'skribl:compose:say') { onSay(d); return; }
    /* A face's photo to trace: face mode alone has the guide (editor_face.js
       is loaded only there), so anywhere else this does nothing. */
    if (d && d.type === 'skribl:compose:guide') {
      if (d.file && global.SkriblFaceGuide) global.SkriblFaceGuide.take(d.file);
      return;
    }
    /* DRAW BACK (lib/drawback.js): somebody's drawing faint under the pen,
       its shape and paper the canvas's. Sent before a re-edit's `load`, so
       the drawing comes back onto the original's shape. */
    if (d && d.type === 'skribl:compose:underlay') {
      if (d.payload && global.SkriblDrawBack) global.SkriblDrawBack.take({ payload: d.payload, first: d.first, own: !!d.own });
      return;
    }
    /* HOW IT WORKS, ASKED FOR BY THE HOST (the Skribl site's own How it
       works: its "The Pad" and "Flip" rows open the editor inside a post
       with its help showing). The editor's own drawer, opened as its menu's
       row opens it (lib/ask.js). */
    if (d && d.type === 'skribl:compose:help') {
      if (typeof global.SkriblAskOpen === 'function') global.SkriblAskOpen();
      errand = true;   // closed as it is read, the editor goes back (below)
      return;
    }
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
   * editor's own click handler. A host's face (?face=1, after v330) has its
   * own words on the button (data-waiting-words), as its Use says Use. */
  var WAIT_MSG = 'Draw something first, then Add';
  function addAlwaysReady() {
    var btn = doc.getElementById('postBtn');
    if (!btn) return;
    var said = btn.getAttribute('data-waiting-words') || WAIT_MSG;
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
      if (typeof global.showToast === 'function') global.showToast(said, btn);
      else if (typeof global.chip === 'function') global.chip(said);
    }, true);
  }

  /* ...AND CLOSED AS IT IS READ, THE EDITOR GOES BACK WHERE THE PERSON WAS
     (the owner, Nov 23: How it works opened from the site's own page closed
     into the Pad, not back to that page; WORKING-AGREEMENTS "Never stranded",
     DECISIONS "The way back"). Asked for by the host, How it works is the host
     page's errand: closed as a person closes what they have read (its ×, the
     dim around it, Escape), the editor goes as its own × sends it, back to
     the host's page. Closed by something it offers to try here (Ask's Show
     me, the little book's Draw along, a card's Try it), the person stays to
     try it, and the help is the editor's own from then on. Nothing can be
     drawn while it is open, so going loses nothing: the host keeps the frame. */
  var errand = false, readIt = false;
  function watchErrand() {
    var drawer = doc.getElementById('helpDrawer');
    if (!drawer || typeof MutationObserver === 'undefined') return;
    /* A press or a key that closes it as read: only once it has begun to close
       (a key Ask's own box takes, or a press that misses, is not one). */
    function read() {
      if (!errand || drawer.hidden) return;
      setTimeout(function () { if (drawer.classList.contains('closing')) readIt = true; }, 0);
    }
    doc.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('#helpClose, #helpBackdrop')) read();
    }, true);
    doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') read(); }, true);
    new MutationObserver(function () {
      if (!drawer.hidden || !errand) return;
      var back = readIt;
      errand = false; readIt = false;
      if (back) api.cancel();
    }).observe(drawer, { attributes: true, attributeFilter: ['hidden'] });
  }

  function ready() {
    hideDuplicateFields();
    addAlwaysReady();
    watchErrand();
    /* The header's × (compose mode only): back to the host's post. The host
     * closes its overlay on cancel and keeps the frame, so the drawing is
     * still there when the author presses the Skribl button again. */
    var close = doc.getElementById('composeCloseBtn');
    if (close) close.addEventListener('click', api.cancel);
    /* Announced AFTER the editor's own scripts have run, so a host that replies
     * immediately with a payload finds loadSkribl() defined. */
    send('skribl:compose:ready', { editor: EDITOR });
  }

  /* READY ONCE EVERY SCRIPT OF THE EDITOR'S OWN HAS RUN: at DOMContentLoaded,
     which comes after the last deferred script. This used to call ready() at
     once whenever the page was past 'loading', and a deferred script always
     is (the page is 'interactive' while its deferred scripts run): so ready
     was said as THIS script ran, with scripts still to come after it in the
     page (Draw back's lib/drawback.js, a face's editor_face.js, and
     editor_draft.js, which sets the paper). The host answers ready at once
     with what it holds (a drawing to lay under the pen, a photo to trace),
     and on a slow line that answer reached a Pad that could not take it yet
     and was dropped: the Pad opened on blank paper under "Drawing back on
     Ana’s" (main's red after #989; verify_socialdrawback 4, with those
     scripts held back). 'load' is the net for a page that has had its
     DOMContentLoaded already. */
  if (doc.readyState === 'complete') ready();
  else {
    var said = false;
    var once = function () { if (!said) { said = true; ready(); } };
    doc.addEventListener('DOMContentLoaded', once);
    global.addEventListener('load', once);
  }
})(typeof window !== 'undefined' ? window : this);
