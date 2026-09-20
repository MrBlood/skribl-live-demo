/* The public gallery's own script: fetch the real listing, clone the real macro.
 *
 * This file is NOT the in-post player — inlineplayer.js is. What this does is
 * the job a host page does (feed.js is the recipe, and this is the same recipe
 * without a composer): get a page of public posts from GET /api/skribls, put a
 * skribl_inline() block in the DOM for each one, call SkriblInline.mount(), and
 * offer the next page through the listing's own keyset cursor.
 *
 * NOTHING HERE DECIDES WHAT IS PUBLIC. The author did, with one tick on the
 * post sheet (editor_post.js buildPostPayload, flip.js buildSharePayload), and
 * the server's visibility rules are the only filter. The listing is asked for
 * with a limit and a cursor and nothing else: no client-side filtering, no
 * fallback to invented tiles. An empty gallery renders as an empty gallery.
 */
(function () {
  'use strict';

  var list = document.getElementById('galleryList');
  var empty = document.getElementById('galleryEmpty');
  var errEl = document.getElementById('galleryError');
  var more = document.getElementById('galleryMore');
  var tpl = document.getElementById('skriblTileTpl');
  var api = document.body.getAttribute('data-skribl-api');
  var PAGE = 24;
  var cursor = null;       /* the keyset cursor for the next page, or null */
  var loading = false;

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

  function tile(item) {
    var art = document.createElement('article');
    art.className = 'tile';
    art.setAttribute('data-id', item.id);

    var head = document.createElement('div');
    head.className = 'thead';
    var tt = document.createElement('span');
    tt.className = 'tt';
    tt.textContent = item.title || 'Untitled Skribl';
    head.appendChild(tt);
    var tm = document.createElement('span');
    tm.className = 'tm';
    tm.textContent = when(item.created_at);
    head.appendChild(tm);
    art.appendChild(head);

    /* The macro rendered the poster URL with the placeholder in it, so the
       real one is that same server-built path with the id substituted — no
       path is assembled here, which keeps this correct under a url_prefix. */
    var frag = tpl.content.cloneNode(true);
    var box = frag.querySelector('[data-skribl-inline]');
    box.setAttribute('data-skribl-id', item.id);
    var poster = box.querySelector('.skribl-inline-poster');
    if (poster) {
      poster.setAttribute('src', poster.getAttribute('src').replace('__ID__', encodeURIComponent(item.id)));
      poster.setAttribute('alt', item.title || 'A Skribl');
    }
    art.appendChild(frag);

    if (item.caption) {
      var tc = document.createElement('p');
      tc.className = 'tc';
      tc.textContent = item.caption;
      art.appendChild(tc);
    }
    return art;
  }

  /* One page of the listing. `reset` starts from the top with a clean grid —
     a retry after a response that failed mid-way must not double every row —
     and otherwise the page is appended after the cursor the last one gave. */
  function load(reset) {
    if (loading) return;
    loading = true;
    errEl.hidden = true;
    empty.hidden = true;
    more.disabled = true;
    if (reset) {
      cursor = null;
      while (list.firstChild) list.removeChild(list.firstChild);
    }
    var url = api + '?limit=' + PAGE + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        var items = (body && body.items) || [];
        for (var i = 0; i < items.length; i++) list.appendChild(tile(items[i]));
        if (items.length) window.SkriblInline.mount(list);
        cursor = (body && body.next_cursor) || null;
        more.hidden = !cursor;
        empty.hidden = list.children.length > 0;
      })
      .catch(function () {
        errEl.hidden = false;
        more.hidden = true;
      })
      .then(function () {
        loading = false;
        more.disabled = false;
      });
  }

  document.getElementById('galleryRetry').addEventListener('click', function () { load(true); });
  more.addEventListener('click', function () { load(false); });
  load(true);
})();

/* THE BOOT FLAG, and it must stay last (harness/browsing.py waits on it). */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { gallery: true });
