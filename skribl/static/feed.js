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

  function row(item) {
    var post = document.createElement('article');
    post.className = 'post';

    var head = document.createElement('div');
    head.className = 'phead';
    var who = document.createElement('span');
    who.className = 'dn';
    /* The listing carries a user_id and no display name — resolving one is the
       host's job (init_skribl's author_resolver seam), and inventing a handle
       here would be the preview lying about what the API returns. */
    who.textContent = item.user_id == null ? 'Someone' : 'User ' + item.user_id;
    head.appendChild(who);
    var meta = document.createElement('span');
    meta.className = 'tm';
    meta.textContent = when(item.created_at);
    head.appendChild(meta);
    post.appendChild(head);

    if (item.title || item.caption) {
      var body = document.createElement('div');
      body.className = 'pbody';
      body.textContent = item.title
        ? (item.caption ? item.title + ' — ' + item.caption : item.title)
        : item.caption;
      post.appendChild(body);
    }

    var frag = tpl.content.cloneNode(true);
    var box = frag.querySelector('[data-skribl-inline]');
    box.setAttribute('data-skribl-id', item.id);
    var poster = box.querySelector('.skribl-inline-poster');
    if (poster) {
      /* The macro rendered the card URL with the placeholder in it, so the real
         one is that same server-built path with the id substituted — no path is
         assembled here, which is what keeps this correct under a url_prefix. */
      poster.setAttribute('src', poster.getAttribute('src').replace('__ID__', encodeURIComponent(item.id)));
      poster.setAttribute('alt', item.title || 'A Skribl');
    }
    post.appendChild(frag);
    return post;
  }

  fetch(api + '?limit=12', { credentials: 'same-origin' })
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
})();
