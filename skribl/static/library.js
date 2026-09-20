/* The profile's Skribls tab: every Skribl this listing returns, with a
 * transport a post is not allowed to have.
 *
 * ===========================================================================
 * WHAT THIS REPLACED, AND WHY THAT MATTERED
 * ===========================================================================
 *
 * Until v275 this file was a MOCK. It carried its own tiny replay engine and a
 * table of hand-drawn motifs — a bolt, a cassette, a smiley — and rendered
 * those. Nothing on the page had ever been posted by anyone. It was registered
 * as a real route the whole time, so a host mounting Skribl got it in their own
 * URL space serving invented drawings, and README.md had to carry a warning
 * saying so.
 *
 * The problem with that was not the pretending. It was that a page which draws
 * its own content cannot tell you whether the thing it is previewing WORKS.
 * This one reads GET /api/skribls and plays real payloads, so when it is wrong
 * it is wrong about something.
 *
 * ===========================================================================
 * IT DOES NOT CONTAIN A PLAYER
 * ===========================================================================
 *
 * The stage is inlineplayer.js — the same player the feed uses — driven through
 * the handle it exposes: play, pause, seek, setLoop, state. A third replay
 * implementation for the profile is how three of them would drift, and
 * verify_sharedrules.py's note explains what that costs: nothing an author can
 * see reveals it.
 *
 * What this file owns is the LIBRARY: which drawing is on the stage, the
 * transport around it, and the grid.
 *
 * THE TRANSPORT IS THE DIFFERENCE BETWEEN THE TWO SURFACES, and it is
 * deliberate. A post gets a play tap and a mute button, because a feed is not a
 * media player (inlineplayer.css says so at the mute rule). A profile tab is a
 * page ABOUT the drawings — somebody came here to look at one — so scrub,
 * restart and a loop toggle belong.
 *
 * ===========================================================================
 * ONE PAYLOAD AT A TIME
 * ===========================================================================
 *
 * The grid tiles are share-card images, not players. Fifty mounted players each
 * holding a payload is tens of megabytes for a page of thumbnails, and
 * GET /api/skribls returns metadata precisely so a listing does not have to pay
 * that. Selecting a tile fetches ONE payload and hands it to the stage.
 */
(function () {
  'use strict';

  var api = document.body.getAttribute('data-skribl-api');
  var playerBase = document.body.getAttribute('data-skribl-player') || '';
  /* WHOSE PROFILE (v304). `me` is the host's signed-in user, or '' when there
   * are no accounts — the standalone app. See whose() below. */
  var me = document.body.getAttribute('data-skribl-me') || '';
  var libEmpty = document.getElementById('libEmpty');
  var libEmptyLocal = document.getElementById('libEmptyLocal');
  var whoBio = document.getElementById('whoBio');
  var btnFull = document.getElementById('btnFull');

  var grid = document.getElementById('grid');
  var moreWrap = document.getElementById('moreWrap');
  var foot = document.getElementById('libFoot');
  var libCnt = document.getElementById('libCnt');
  var statCount = document.getElementById('statCount');
  var search = document.getElementById('search');

  var stageBox = document.getElementById('stageBox');
  var stageWrap = stageBox.closest('.stageCanvasWrap');
  var pTitle = document.getElementById('pTitle');
  var pKind = document.getElementById('pKind');
  var pMeta = document.getElementById('pMeta');
  var pStats = document.getElementById('pStats');
  var scrub = document.getElementById('scrub');
  var scrubFill = document.getElementById('scrubFill');
  var tElapsed = document.getElementById('tElapsed');
  var btnPlay = document.getElementById('btnPlay');
  var btnRestart = document.getElementById('btnRestart');
  var btnLoop = document.getElementById('btnLoop');
  var btnMute = document.getElementById('btnMute');
  var btnShare = document.getElementById('btnShare');

  var items = [];          /* every row loaded so far, newest first */
  var cursor = null;       /* the keyset cursor for the next page */
  var current = null;      /* the item on the stage */
  var player = null;       /* the inlineplayer handle */
  var looping = true;
  var tick = null;

  function fmt(ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
  }

  function when(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    var mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    if (mins < 1440) return Math.round(mins / 60) + 'h ago';
    return d.toLocaleDateString();
  }

  /* The poster: the share card's drawing, or a blank canvas for a post that
   * has no thumbnail — never the branded card itself (v287 audit SK-BUG-006).
   * Built from the player base the server gave us — never assembled from a
   * literal path, so a host's url_prefix is honoured. */
  function posterUrl(id) { return playerBase + '/' + encodeURIComponent(id) + '/poster'; }

  /* ---- the stage ---------------------------------------------------------- */

  function select(item) {
    current = item;
    pTitle.textContent = item.title || 'Untitled Skribl';
    pMeta.textContent = when(item.created_at);
    pKind.textContent = item.has_audio ? 'with sound' : 'silent';
    /* A browser-kept entry may not know its visibility; say nothing rather
       than guess. */
    pStats.textContent = !item.visibility ? '' : (item.visibility === 'public' ? 'in the gallery' : item.visibility);
    scrubFill.style.width = '0%';
    tElapsed.textContent = '0:00 / 0:00';
    setPlayIcon(false);
    Array.prototype.forEach.call(grid.children, function (c) {
      c.classList.toggle('active', c.getAttribute('data-id') === item.id);
    });

    /* ONE FETCH, for the one drawing about to play. The listing already gave us
     * everything else on this page. */
    fetch(api + '/' + encodeURIComponent(item.id), { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        if (current !== item) return;      /* a later selection won */
        var payload = (body && (body.skribl || body.payload)) || body;
        if (!player) {
          player = window.SkriblInline.attach(stageBox, payload);
          player.setLoop(looping);
        } else {
          player.adopt(payload);
        }
        refresh();
      })
      .catch(function () {
        pTitle.textContent = "Couldn't load this Skribl.";
      });
  }

  function setPlayIcon(on) {
    document.getElementById('playIcon').innerHTML = on
      ? '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>'
      : '<path d="M8 5v14l11-7z"/>';
    btnPlay.title = on ? 'Pause' : 'Play';
  }

  /* The transport reads the PLAYER's clock rather than keeping one of its own.
   * Two clocks is two answers to "how far through is it", and the one on screen
   * would be the wrong one. */
  function refresh() {
    if (!player) return;
    var st = player.state();
    var frac = st.totalMs ? Math.min(1, st.elapsedMs / st.totalMs) : 0;
    scrubFill.style.width = (frac * 100) + '%';
    tElapsed.textContent = fmt(st.elapsedMs) + ' / ' + fmt(st.totalMs);
    setPlayIcon(st.state === 'playing');
    btnMute.classList.toggle('on', !st.muted);
    btnMute.disabled = !st.hasAudio;
    btnMute.title = !st.hasAudio ? 'This Skribl has no sound'
                                 : (st.muted ? 'Unmute' : 'Mute');
  }

  tick = setInterval(refresh, 100);

  btnPlay.addEventListener('click', function () { if (player) { player.toggle(); refresh(); } });
  btnRestart.addEventListener('click', function () {
    if (!player) return;
    player.seek(0);
    player.play();
    refresh();
  });
  btnLoop.addEventListener('click', function () {
    looping = !looping;
    this.classList.toggle('on', looping);
    this.setAttribute('aria-pressed', String(looping));
    if (player) player.setLoop(looping);
  });
  btnMute.addEventListener('click', function () {
    window.SkriblInline.setSoundOn(!window.SkriblInline.soundOn());
    refresh();
  });
  btnShare.addEventListener('click', function () {
    if (!current) return;
    var url = location.origin + playerBase + '/' + current.id;
    var done = function () {
      var t = btnShare.title;
      btnShare.title = 'Link copied';
      setTimeout(function () { btnShare.title = t; }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, done);
    } else { done(); }
  });

  /* ---- full screen -------------------------------------------------------
     The stage wrap on the whole display, through the Fullscreen API. The
     button exists only where the API does: iPhone Safari has it for <video>
     alone, and a button that did nothing there would be worse than none.
     Escape leaves through the browser; the button leaves too, and its
     pressed state follows the document, not a flag of its own. */
  var fsEl = function () { return document.fullscreenElement || document.webkitFullscreenElement || null; };
  var fsOn = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled)
             && stageWrap && (stageWrap.requestFullscreen || stageWrap.webkitRequestFullscreen);
  if (btnFull && fsOn) {
    btnFull.hidden = false;
    btnFull.addEventListener('click', function () {
      if (fsEl() === stageWrap) {
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      } else {
        var req = stageWrap.requestFullscreen || stageWrap.webkitRequestFullscreen;
        try { var p = req.call(stageWrap); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      }
    });
    var syncFull = function () {
      var on = fsEl() === stageWrap;
      btnFull.classList.toggle('on', on);
      btnFull.setAttribute('aria-pressed', String(on));
      btnFull.title = on ? 'Leave full screen' : 'Full screen';
      btnFull.setAttribute('aria-label', btnFull.title);
    };
    var fullExit = document.getElementById('fullExit');
    if (fullExit) fullExit.addEventListener('click', function () {
      if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    });
    document.addEventListener('fullscreenchange', syncFull);
    document.addEventListener('webkitfullscreenchange', syncFull);
  }

  scrub.addEventListener('click', function (e) {
    if (!player) return;
    var r = e.currentTarget.getBoundingClientRect();
    var f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    player.seek(player.state().totalMs * f);
    refresh();
  });

  /* ---- the grid ----------------------------------------------------------- */

  function tile(item) {
    var el = document.createElement('button');
    el.type = 'button';
    el.className = 'card';
    el.setAttribute('data-id', item.id);

    /* The tile's picture is the poster, cropped by the same rule the feed
     * poster uses — sharecard.js's geometry, expressed as literals in this
     * page's own CSS. The module itself is NOT loaded here (v281 removed it);
     * verify_inline.py is what holds the literals to band(). One cached image
     * per tile, and no payload until the tile is picked. */
    var art = document.createElement('div');
    art.className = 'art';
    var img = document.createElement('img');
    img.src = posterUrl(item.id);
    img.alt = item.title || 'A Skribl';
    img.loading = 'lazy';
    img.decoding = 'async';
    art.appendChild(img);
    el.appendChild(art);

    var body = document.createElement('div');
    body.className = 'body';
    var t = document.createElement('div');
    t.className = 'ct';
    t.textContent = item.title || 'Untitled Skribl';
    var cm = document.createElement('div');
    cm.className = 'cm';
    var w = document.createElement('span');
    w.textContent = when(item.created_at);
    cm.appendChild(w);
    if (item.has_audio) {
      var snd = document.createElement('span');
      snd.className = 'dur';
      snd.textContent = 'sound';
      cm.appendChild(snd);
    }
    body.appendChild(t);
    body.appendChild(cm);
    el.appendChild(body);

    el.addEventListener('click', function () { select(item); });
    return el;
  }

  function renderGrid() {
    var q = (search.value || '').trim().toLowerCase();
    var shown = items.filter(function (i) {
      return !q || (i.title || '').toLowerCase().indexOf(q) !== -1
                || (i.caption || '').toLowerCase().indexOf(q) !== -1;
    });
    grid.innerHTML = '';
    shown.forEach(function (i) { grid.appendChild(tile(i)); });
    libCnt.textContent = shown.length + (q ? ' matching' : '');
    statCount.textContent = items.length;
    if (current) {
      Array.prototype.forEach.call(grid.children, function (c) {
        c.classList.toggle('active', c.getAttribute('data-id') === current.id);
      });
    }
    /* SAYS WHAT IT IS SHOWING. The search filters what has been LOADED, not the
     * table — the listing is keyset-paginated and a server-side search is a
     * query this API does not have. A box that silently searched one page while
     * looking like it searched everything is the kind of half-truth that gets
     * believed. */
    foot.textContent = !items.length ? ''
      : (q ? (me ? 'Filtering the ' + items.length + ' loaded so far. Load more to search further.'
                 : 'Filtering your ' + items.length + '.')
           : 'Newest first. Pick one to play it.');
    if (libEmpty) libEmpty.hidden = items.length > 0;
  }

  /* ======================================================================
     WHOSE SKRIBLS THESE ARE
     ======================================================================

     Until the gallery this page read the public listing and called it "Your
     skribls" — true only because nothing posted from the editors was ever
     public, so the page was empty. The gallery made that false the day
     somebody ticked the box: the profile filled with strangers' work.

     A profile is somebody's. Two answers, one per deployment:

       HOST WITH ACCOUNTS  data-skribl-me is set -> GET /api/skribls?user_id=me,
                           the listing's own author filter, paged by its
                           cursor. The server decides what an author sees of
                           their own (public and private; unlisted stays out of
                           every listing by definition).
       NO ACCOUNTS         the list this browser kept — lib/posted.js, the same
                           record the menu's "Your Skribls" shows. Unlisted
                           posts included: they are yours. Local-only fallbacks
                           (ids starting local_) are not on the server and are
                           left out. Nothing is fetched to build the grid: the
                           tile is the poster, as before, and one payload is
                           fetched when a tile is picked.

     The gallery is the public page. This one never was. */
  function mine() {
    var list = (window.SkriblPosted && window.SkriblPosted.list) ? window.SkriblPosted.list() : [];
    return list.filter(function (e) { return e && e.id && String(e.id).indexOf('local_') !== 0; })
      .sort(function (a, b) { return (b.at || 0) - (a.at || 0); })
      .map(function (e) {
        return { id: e.id, title: e.title || '', caption: '',
                 created_at: e.at ? new Date(e.at).toISOString() : null,
                 has_audio: false, visibility: e.visibility || '' };
      });
  }

  function loadPage() {
    if (!me) {
      items = mine();
      cursor = null;
      renderGrid();
      moreWrap.innerHTML = '';
      if (items.length) select(items[0]);
      return Promise.resolve();
    }
    var url = api + '?limit=24&user_id=' + encodeURIComponent(me)
            + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    moreWrap.innerHTML = '<span class="more-status">Loading…</span>';
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        items = items.concat(body.items || []);
        cursor = body.next_cursor || null;
        renderGrid();
        moreWrap.innerHTML = '';
        if (cursor) {
          /* KEYSET, not offset — the cursor the server handed back. See
             list_skribls() for why offset paging is wrong for a feed: page 50
             costs fifty times page 1, and a post created mid-scroll shifts every
             page after it. */
          var more = document.createElement('button');
          more.type = 'button';
          more.className = 'more';
          more.textContent = 'Load more';
          more.addEventListener('click', function () { loadPage(); });
          moreWrap.appendChild(more);
        }
        if (!current && items.length) select(items[0]);
        /* An empty profile is the empty state above the footer (renderGrid
           hides and shows it); the route-naming sentence that used to sit
           here is gone with the population it described. */
      })
      .catch(function () {
        moreWrap.innerHTML = '';
        foot.textContent = "Couldn't load the listing.";
      });
  }

  search.addEventListener('input', renderGrid);
  loadPage();
})();

/* THE BOOT FLAG, and it must stay last. app.js and flip.js have set one since
   v-early; this surface did not, so every suite that opened it waited a fixed
   guess instead of a signal — the harness spent 15.7 minutes sleeping and 78
   seconds launching browsers. A flag is the cheapest possible check for the
   most expensive possible bug (the file did not reach its end), and unlike a
   page-error listener it also catches a swallowed throw. */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { library: true });
