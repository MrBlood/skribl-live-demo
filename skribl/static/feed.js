/* The /feed preview's own script: fetch the real listing, clone the real macro.
 *
 * This file is NOT the in-post player — inlineplayer.js is, and this page has no
 * privileged access to it. What this does is the job a HOST does: get a page of
 * posts from GET /api/skribls, put a skribl_inline() block in the DOM for each
 * one, and call SkriblInline.mount(). If a host cannot do that with this much
 * code, the component is wrong.
 *
 * WHY THE MARKUP IS CLONED FROM A <template> RATHER THAN BUILT HERE. The block
 * inside #skriblPostTpl is the output of the skribl_inline() macro, rendered by
 * the server with '__ID__' where the public id goes. Cloning it means this page
 * exercises the SHIPPED markup — if the macro grows an element, the preview gets
 * it without anyone remembering to update a string of HTML here, which is
 * exactly how a mock drifts from the thing it is previewing. <template> content
 * is inert, so the placeholder poster URL is never fetched.
 *
 * The listing itself is untouched: no query parameters beyond a limit, no
 * client-side filtering, no fallback to invented posts. An empty feed renders as
 * an empty feed, because that is the truth about a database with nothing in it —
 * and because a preview that manufactures content is how /library ended up
 * showing drawings that were never posted.
 */
(function () {
  'use strict';

  var list = document.getElementById('feedList');
  var empty = document.getElementById('feedEmpty');
  var errEl = document.getElementById('feedError');
  var tpl = document.getElementById('skriblPostTpl');
  var api = document.body.getAttribute('data-skribl-api');

  function when(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    var mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return mins + 'm';
    if (mins < 1440) return Math.round(mins / 60) + 'h';
    return Math.round(mins / 1440) + 'd';
  }

  /* Where the author put the drawing in their text. Typed into the composer
     on attach and split on in row(); a host that stores the position its own
     way (an attachment offset, a node in a rich-text document) needs neither. */
  var MARK = '[skribl]';
  function textBlock(words) {
    var el = document.createElement('div');
    el.className = 'pbody';
    el.textContent = words;
    return el;
  }

  function row(item) {
    var post = document.createElement('article');
    post.className = 'post';

    var head = document.createElement('div');
    head.className = 'phead';
    var who = document.createElement('span');
    who.className = 'dn';
    /* The listing carries a user_id and no display name — resolving one is the
       host's job (init_skribl's author_resolver seam), and inventing a handle
       here would be the preview lying about what the API returns. With no
       user_id at all there is no byline: "Someone" read as a shrug. */
    if (item.user_id != null) {
      who.textContent = 'User ' + item.user_id;
      head.appendChild(who);
    }
    var meta = document.createElement('span');
    meta.className = 'tm';
    meta.textContent = when(item.created_at);
    head.appendChild(meta);
    post.appendChild(head);

    /* THE SKRIBL SITS WHERE THE AUTHOR PUT IT (v315). The composer writes
       MARK into the text at the cursor when a drawing is attached; here the
       text is split at the first one, words before it above the player and
       words after it below. No marker -- a post written before this, or one
       whose author deleted it -- keeps the old order: text, then drawing.
       A real host does the same with its OWN post body; the marker is this
       page's stand-in for that, since it has no post table (see below). */
    var cap = item.caption || '';
    var at = cap.indexOf(MARK);
    var before = (at >= 0 ? cap.slice(0, at) : cap).trim();
    var after = at >= 0 ? cap.slice(at + MARK.length).trim() : '';
    if (before) post.appendChild(textBlock(before));

    var frag = tpl.content.cloneNode(true);
    var box = frag.querySelector('[data-skribl-inline]');
    box.setAttribute('data-skribl-id', item.id);
    /* THE DRAWING'S SHAPE, so the component can frame the idle poster where the
       canvas will be rather than showing the share card's ground either side of
       it (v309). Null on a row written before the column, and the component
       then keeps the band crop -- so this is written only when the listing
       actually answered, never as a default. */
    if (item.canvas_w && item.canvas_h) {
      box.setAttribute('data-skribl-w', item.canvas_w);
      box.setAttribute('data-skribl-h', item.canvas_h);
    }
    var poster = box.querySelector('.skribl-inline-poster');
    if (poster) {
      /* The macro rendered the card URL with the placeholder in it, so the real
         one is that same server-built path with the id substituted — no path is
         assembled here, which is what keeps this correct under a url_prefix. */
      poster.setAttribute('src', poster.getAttribute('src').replace('__ID__', encodeURIComponent(item.id)));
      poster.setAttribute('alt', item.title || 'A Skribl');
    }
    post.appendChild(frag);
    /* The title under the player (v315), as the macro's `title=` renders it
       for a host's server-side feed. Shown only when it is the drawing's own
       name: not the "Untitled Skribl" default, and not the opening words of
       the post itself, which a host that derives one from the other would
       otherwise print twice. */
    var name = (item.title || '').trim();
    if (name && name !== 'Untitled Skribl' && cap.replace(MARK, '').trim().indexOf(name) !== 0) {
      var line = document.createElement('p');
      line.className = 'skribl-inline-title';
      var b = document.createElement('b');
      b.textContent = name;
      var kind = document.createElement('span');
      kind.textContent = 'Skribl';
      line.appendChild(b);
      line.appendChild(kind);
      post.appendChild(line);
    }
    if (after) post.appendChild(textBlock(after));
    return post;
  }

  /* ======================================================================
     THE COMPOSER — the whole point of this page.
     ======================================================================

     Everything below is HOST code. Skribl's side of this contract is two
     things: the editor at ?compose=1, and the four postMessage types in
     skribl/static/editor_compose.js. A real host writes roughly this, against
     their own composer and their own post table.

     THE LIFECYCLE, which is the part worth copying:

       pad icon      -> open the editor in an overlay iframe
       ready         -> if we are RE-EDITING, send the payload we are holding
       done          -> keep the payload on the draft, render it inline,
                        PUBLISH NOTHING
       Post          -> POST /api/skribls exactly once, take the id

     A real host's Post also writes their own row and stores that id on it; this
     page has no post table, so the skribl IS the post and the composer's text
     becomes its caption. That is the one place this demo differs from a host,
     and it is why the text lands in the caption rather than beside it. */
  var compose = {
    payload: null,
    overlay: document.getElementById('padOverlay'),
    frame: document.getElementById('padFrame'),
    attachWrap: document.getElementById('composerAttach'),
    box: document.getElementById('composerSkribl'),
    text: document.getElementById('composerText'),
    postBtn: document.getElementById('postBtn'),
    status: document.getElementById('composerStatus'),
    player: null,
    src: document.body.getAttribute('data-skribl-compose'),
    createUrl: document.body.getAttribute('data-skribl-create'),
    csrf: document.body.getAttribute('data-skribl-csrf')
  };

  function say(msg, bad) {
    compose.status.textContent = msg || '';
    compose.status.hidden = !msg;
    compose.status.classList.toggle('error', !!bad);
  }

  /* PUT THE DRAWING WHERE THE CURSOR IS (v315): MARK goes into the text at
     the caret, on a line of its own, the first time a drawing is attached.
     Re-attaching after an edit leaves the marker where the author has since
     moved it. One per post, so a second MARK is never written. */
  function placeMark() {
    var t = compose.text;
    if (t.value.indexOf(MARK) >= 0) return;
    var at = typeof t.selectionStart === 'number' ? t.selectionStart : t.value.length;
    var head = t.value.slice(0, at), tail = t.value.slice(at);
    var ins = (head && !/\n$/.test(head) ? '\n' : '') + MARK + (/^\n/.test(tail) ? '' : '\n');
    t.value = head + ins + tail;
    t.selectionStart = t.selectionEnd = (head + ins).length;
  }

  function syncPostBtn() {
    /* A post needs something in it. Text alone is a post; a Skribl alone is a
       post; neither is not. */
    compose.postBtn.disabled = !(compose.payload || compose.text.value.trim());
  }

  function showAttached() {
    compose.attachWrap.hidden = false;
    /* The REAL in-post player, rendering the real payload — not a thumbnail.
       What the composer previews is what the post will publish. */
    if (!compose.player) {
      compose.player = window.SkriblInline.attach(compose.box, compose.payload);
    } else {
      compose.player.adopt(compose.payload);
    }
    syncPostBtn();
  }

  /* THE LIFECYCLE IS lib/composehost.js, not this file. Everything that used to
     be written out here — the lazy src, re-pushing the payload into an
     already-loaded editor, the origin checks, resetting the frame on remove —
     is the same in every host, so it lives in the module and this page is left
     with only what is genuinely its own: an overlay to show and a preview to
     render. That subtraction IS the deliverable; what remains is the honest
     measure of what a host writes. */
  var pad = window.SkriblComposeHost.create({
    frame: compose.frame,
    src: compose.src,
    onOpen: function () { say(''); compose.overlay.hidden = false; },
    onClose: function () { compose.overlay.hidden = true; },
    onDone: function (payload) {
      compose.payload = payload;
      placeMark();
      showAttached();
    }
  });

  document.getElementById('padBtn').addEventListener('click', pad.open);
  document.getElementById('editSkriblBtn').addEventListener('click', pad.open);
  document.getElementById('padCloseBtn').addEventListener('click', pad.close);
  document.getElementById('removeSkriblBtn').addEventListener('click', function () {
    compose.payload = null;
    compose.text.value = compose.text.value.replace(MARK + '\n', '').replace(MARK, '');
    compose.attachWrap.hidden = true;
    if (compose.player) compose.player.settle();
    pad.clear();
    syncPostBtn();
  });
  compose.text.addEventListener('input', syncPostBtn);

  document.getElementById('composer').addEventListener('submit', function (e) {
    e.preventDefault();
    if (compose.postBtn.disabled) return;
    var words = compose.text.value.trim();
    if (!compose.payload) {
      say('This demo host has no post table of its own — a post here IS a '
          + 'Skribl, so add a drawing.', true);
      return;
    }
    compose.postBtn.disabled = true;
    say('Posting…');
    /* THE ONE POST. Everything before this was a draft. `visibility: public` is
       the host's decision, not Skribl's: POST /api/skribls defaults to
       "unlisted" because that is what a link-sharing product should do, and a
       feed's composer is exactly the caller that means otherwise. */
    var body = Object.assign({}, compose.payload, {
      /* The drawing's own name when it has one; otherwise the post's words,
         which is what /s/<id> unfurls with. The marker is never a title. */
      title: (compose.payload.title && compose.payload.title !== 'Untitled Skribl')
        ? compose.payload.title
        : (words.replace(MARK, ' ').replace(/\s+/g, ' ').trim().slice(0, 80) || 'Untitled Skribl'),
      caption: words,
      visibility: 'public'
    });
    var headers = { 'Content-Type': 'application/json' };
    if (compose.csrf) headers['X-Skribl-CSRF'] = compose.csrf;
    fetch(compose.createUrl, {
      method: 'POST', headers: headers, credentials: 'same-origin',
      body: JSON.stringify(body)
    }).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; })
        .then(function (j) { throw new Error(j.error || ('HTTP ' + r.status)); });
      return r.json();
    }).then(function (res) {
      /* A real host stores res.id on THEIR post row here and renders it with
         {{ skribl_inline(post.skribl_id) }}. This page just prepends it. */
      list.insertBefore(row({ id: res.id, title: body.title, caption: body.caption,
                              created_at: new Date().toISOString(), user_id: null }),
                        list.firstChild);
      window.SkriblInline.mount(list);
      empty.hidden = true;
      compose.payload = null;
      compose.text.value = '';
      compose.attachWrap.hidden = true;
      /* The player object is kept and reused — attaching a second one to the
         same element would leave the first in the one-at-a-time registry,
         still holding a drawing nobody can see or stop. */
      if (compose.player) compose.player.settle();
      pad.clear();
      say('Posted.');
      syncPostBtn();
    }).catch(function (err) {
      say(err.message || 'Could not post.', true);
      compose.postBtn.disabled = false;
    });
  });

  syncPostBtn();

  /* THE LISTING, AS A FUNCTION, so the error state's Retry can call it
     (SK-AUD-012): "Couldn't load the listing." was a sentence with nothing to
     press, on the one page where a tester on a bad connection is most likely
     to land. A retry starts from a clean list -- a half-populated one from a
     response that failed mid-way would otherwise double every row. */
  function load() {
    errEl.hidden = true;
    empty.hidden = true;
    while (list.firstChild) list.removeChild(list.firstChild);
    return fetch(api + '?limit=12', { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        var items = (body && body.items) || [];
        if (!items.length) { empty.hidden = false; return; }
        for (var i = 0; i < items.length; i++) list.appendChild(row(items[i]));
        window.SkriblInline.mount(list);
      })
      .catch(function () { errEl.hidden = false; });
  }
  var retry = document.getElementById('feedRetry');
  if (retry) retry.addEventListener('click', function () { load(); });
  load();
})();

/* THE BOOT FLAG, and it must stay last. app.js and flip.js have set one since
   v-early; this surface did not, so every suite that opened it waited a fixed
   guess instead of a signal — the harness spent 15.7 minutes sleeping and 78
   seconds launching browsers. A flag is the cheapest possible check for the
   most expensive possible bug (the file did not reach its end), and unlike a
   page-error listener it also catches a swallowed throw. */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { feed: true });
