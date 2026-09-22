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
  var sort = 'new';        /* new | hot -- the server's orders */
  var query = '';          /* the search box's words, sent as q */
  var noneEl = document.getElementById('galleryNone');
  var subEl = document.getElementById('gallerySub');
  /* WHICH REQUEST IS STILL WANTED. Bumped by every load; a response may only
     touch the page while its own number is still the current one. See load(). */
  var gen = 0;

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
    /* PLAYS, as counted (v304): the seven-day count under Hot, the total
       otherwise. Zero says nothing rather than "0 plays". */
    var n = sort === 'hot' ? (item.views_recent || 0) : (item.views || 0);
    if (n > 0) {
      var pl = document.createElement('span');
      pl.className = 'plays';
      pl.textContent = n + (n === 1 ? ' play' : ' plays');
      head.appendChild(pl);
    }
    /* REPORT, ON EVERY TILE. The button carries the post's id; the sheet is
       one, shared, and opened with it. */
    var rep = document.createElement('button');
    rep.type = 'button';
    rep.className = 'report';
    rep.setAttribute('data-report', item.id);
    rep.setAttribute('aria-label', 'Report ' + (item.title || 'this Skribl'));
    rep.textContent = 'Report';
    rep.addEventListener('click', function () { openReport(item.id, rep); });
    head.appendChild(rep);
    art.appendChild(head);

    /* The macro rendered the poster URL with the placeholder in it, so the
       real one is that same server-built path with the id substituted — no
       path is assembled here, which keeps this correct under a url_prefix. */
    /* FULL SCREEN, PER TILE (owner: "since the controls stay on the screen
       when playing, there should be a way to watch full size"). The gallery
       had no way to watch a drawing big: the profile stage has one, /s/<id>
       has one, and the page where the drawings actually are had none.

       THE WRAPPER IS FULLSCREENED, NOT THE PLAYER. This page's own comment
       says "Not one rule touches .skribl-inline: the component is the
       component", and a `:fullscreen` rule on it would be exactly that. The
       wrapper takes the display and the component sizes itself inside it,
       which is the same shape the profile's .stageCanvasWrap uses.

       The button exists only where the API does. iPhone Safari has fullscreen
       for <video> alone, and a control that did nothing there would be worse
       than not having one — the same rule library.js states at its own. */
    var stage = document.createElement('div');
    stage.className = 'tileStage';
    var fsEl = function () { return document.fullscreenElement || document.webkitFullscreenElement || null; };
    var fsReq = stage.requestFullscreen || stage.webkitRequestFullscreen;
    if ((document.fullscreenEnabled || document.webkitFullscreenEnabled) && fsReq) {
      var full = document.createElement('button');
      full.type = 'button';
      full.className = 'tileFull';
      full.title = 'Full screen';
      full.setAttribute('aria-label', 'Watch ' + (item.title || 'this Skribl') + ' full screen');
      full.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
        + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/>'
        + '<path d="M8 21H5a2 2 0 0 1-2-2v-3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
      full.addEventListener('click', function () {
        if (fsEl() === stage) {
          (document.exitFullscreen || document.webkitExitFullscreen).call(document);
          return;
        }
        try { var p = fsReq.call(stage); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      });
      head.insertBefore(full, rep);
    }

    var frag = tpl.content.cloneNode(true);
    var box = frag.querySelector('[data-skribl-inline]');
    box.setAttribute('data-skribl-id', item.id);
    var poster = box.querySelector('.skribl-inline-poster');
    if (poster) {
      poster.setAttribute('src', poster.getAttribute('src').replace('__ID__', encodeURIComponent(item.id)));
      poster.setAttribute('alt', item.title || 'A Skribl');
    }
    stage.appendChild(frag);
    art.appendChild(stage);

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
    /* A RESET IS THE PERSON'S LATEST INTENT AND IS NEVER DROPPED.
     *
     * This was `if (loading) return`, which discarded it: tapping Hot, or
     * typing, while the first listing was still in flight set `sort`/`query`
     * and then threw the reload away, and nothing re-issued it when the old
     * request settled. The grid then rendered the OLD answer under a bar
     * saying Hot, or under a search term it had never sent -- on a slow phone,
     * routinely (PRESEAL-001 of the pre-v305 audit).
     *
     * So only PAGING is guarded here, against a double tap on Load more. A
     * reset always goes, and the generation below makes the superseded
     * response harmless. */
    if (loading && !reset) return;
    var myGen = ++gen;
    loading = true;
    errEl.hidden = true;
    empty.hidden = true;
    more.disabled = true;
    if (reset) {
      cursor = null;
      while (list.firstChild) list.removeChild(list.firstChild);
    }
    var url = api + '?limit=' + PAGE + '&sort=' + sort
            + (query ? '&q=' + encodeURIComponent(query) : '')
            + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    if (noneEl) noneEl.hidden = true;
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        /* SUPERSEDED: a newer load has started, so this answer describes a
           sort or a search the person has already moved on from. Drop it
           without touching the grid, the cursor or the loading flag -- the
           newer request owns all three now. */
        if (myGen !== gen) return;
        var items = (body && body.items) || [];
        for (var i = 0; i < items.length; i++) list.appendChild(tile(items[i]));
        if (items.length) window.SkriblInline.mount(list);
        cursor = (body && body.next_cursor) || null;
        more.hidden = !cursor;
        /* Two empty states: nothing in the gallery at all, and nothing that
           matches what was typed. */
        empty.hidden = list.children.length > 0 || !!query;
        if (noneEl) noneEl.hidden = list.children.length > 0 || !query;
      })
      .catch(function () {
        if (myGen !== gen) return;
        errEl.hidden = false;
        more.hidden = true;
      })
      .then(function () {
        /* The stale arm must not clear the flag either: the live request is
           still running and would be left thinking nothing is in flight. */
        if (myGen !== gen) return;
        loading = false;
        more.disabled = false;
      });
  }

  /* ---- the report sheet ------------------------------------------------
     A report is a row in the operator's queue (POST /api/skribls/<id>/report),
     never an action on the post, and the sheet's words say so. One sheet for
     the page, opened per tile; lib/modalfocus.js owns focus. 429 and any
     other refusal are said in the sheet, which stays open for another try. */
  var sheet = document.getElementById('reportSheet');
  var form = document.getElementById('reportForm');
  var note = document.getElementById('reportNote');
  var status = document.getElementById('reportStatus');
  var send = document.getElementById('reportSend');
  var csrf = document.body.getAttribute('data-skribl-csrf');
  var reporting = null;       /* { id, button } while the sheet is open */

  function say(msg, bad) {
    status.textContent = msg || '';
    status.hidden = !msg;
    status.classList.toggle('error', !!bad);
  }

  function openReport(id, button) {
    reporting = { id: id, button: button };
    form.reset();
    /* Already reported from this page: the sheet opens as the record of
       that, with nothing to send. The button stays focusable (it is where
       focus returns on close — a disabled button cannot take it). */
    var done = button.getAttribute('data-reported') === '1';
    say(done ? 'You already reported this one. Thanks.' : '');
    send.disabled = done;
    sheet.hidden = false;
    if (window.SkriblModal) window.SkriblModal.open(sheet, button);
  }

  function closeReport() {
    if (sheet.hidden) return;
    sheet.hidden = true;
    if (window.SkriblModal) window.SkriblModal.close(sheet);
    reporting = null;
  }

  document.getElementById('reportCancel').addEventListener('click', closeReport);
  sheet.addEventListener('click', function (e) { if (e.target === sheet) closeReport(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !sheet.hidden) { e.preventDefault(); closeReport(); }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!reporting || send.disabled) return;
    var reason = (form.querySelector('input[name=reason]:checked') || {}).value;
    if (!reason) { say('Pick a reason.', true); return; }
    var target = reporting;
    var headers = { 'Content-Type': 'application/json' };
    if (csrf) headers['X-Skribl-CSRF'] = csrf;
    send.disabled = true;
    say('Sending…');
    /* The route is the listing's URL plus the id, exactly as the poster URL
       is built from the macro's: no path assembled from a literal, so a
       url_prefix is honoured. */
    fetch(api + '/' + encodeURIComponent(target.id) + '/report', {
      method: 'POST', headers: headers, credentials: 'same-origin',
      body: JSON.stringify({ reason: reason, note: note.value.trim() })
    }).then(function (r) {
      if (r.status === 429) throw new Error('Too many reports from here right now. Try again later.');
      if (!r.ok) return r.json().catch(function () { return {}; })
        .then(function (j) { throw new Error(j.error || ('Could not send (HTTP ' + r.status + ').')); });
      return r.json();
    }).then(function () {
      /* SAID ON THE TILE: the button becomes the record that this reader
         reported this post, and cannot be pressed again this page-load. The
         server would answer a second one the same way and write nothing. */
      target.button.textContent = 'Reported';
      target.button.setAttribute('aria-pressed', 'true');
      target.button.setAttribute('data-reported', '1');
      say('Thanks. The people who run this site will look at it.');
      send.disabled = true;
    }).catch(function (err) {
      say(err.message || 'Could not send the report.', true);
      send.disabled = false;
    });
  });

  /* ---- New / Hot, and the search box --------------------------------- */
  var tabs = document.querySelectorAll('.tabs .tab[data-sort]');
  Array.prototype.forEach.call(tabs, function (tab) {
    tab.addEventListener('click', function () {
      var want = tab.getAttribute('data-sort') === 'hot' ? 'hot' : 'new';
      if (want === sort) return;
      sort = want;
      Array.prototype.forEach.call(tabs, function (t) {
        var on = t === tab;
        t.classList.toggle('active', on);
        t.setAttribute('aria-pressed', String(on));
      });
      if (subEl) subEl.textContent = sort === 'hot'
        ? 'Most played in the last seven days. Tap one to watch it draw itself.'
        : 'Skribls people chose to show. Tap one to watch it draw itself.';
      load(true);
    });
  });
  var find = document.getElementById('galleryFind');
  var qEl = document.getElementById('galleryQ');
  var qTimer = null;
  function search() {
    var words = (qEl.value || '').trim().slice(0, 80);
    if (words === query) return;
    query = words;
    load(true);
  }
  find.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(qTimer); search(); });
  qEl.addEventListener('input', function () { clearTimeout(qTimer); qTimer = setTimeout(search, 350); });

  document.getElementById('galleryRetry').addEventListener('click', function () { load(true); });
  more.addEventListener('click', function () { load(false); });
  load(true);
})();

/* THE BOOT FLAG, and it must stay last (harness/browsing.py waits on it). */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { gallery: true });
