/* The profile's Skribls tab: every Skribl this listing returns, with a
 * transport a post is not allowed to have.
 *
 * ===========================================================================
 * WHAT THIS REPLACED, AND WHY THAT MATTERED
 * ===========================================================================
 *
 * Until now this file was a MOCK. It carried its own tiny replay engine and a
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

  var grid = document.getElementById('grid');
  var moreWrap = document.getElementById('moreWrap');
  var foot = document.getElementById('libFoot');
  var libCnt = document.getElementById('libCnt');
  var statCount = document.getElementById('statCount');
  var search = document.getElementById('search');

  var stageBox = document.getElementById('stageBox');
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

  /* The share card, which is also the in-post player's idle poster. Built from
   * the player base the server gave us — never assembled from a literal path,
   * so a host's url_prefix is honoured. */
  function cardUrl(id) { return playerBase + '/' + encodeURIComponent(id) + '/card.png'; }

  /* ---- the stage ---------------------------------------------------------- */

  function select(item) {
    current = item;
    pTitle.textContent = item.title || 'Untitled Skribl';
    pMeta.textContent = when(item.created_at);
    pKind.textContent = item.has_audio ? 'with sound' : 'silent';
    pStats.textContent = item.visibility === 'public' ? 'listed' : item.visibility;
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

    /* The tile's picture is the share card, cropped by the same rule the feed
     * poster uses (lib/sharecard.js, applied in the page's own CSS). One cached
     * image per tile, and no payload until the tile is picked. */
    var art = document.createElement('div');
    art.className = 'art';
    var img = document.createElement('img');
    img.src = cardUrl(item.id);
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
      : (q ? 'Filtering the ' + items.length + ' loaded so far. Load more to search further.'
           : 'Newest first, from GET /api/skribls. Pick one to play it.');
  }

  function loadPage() {
    var url = api + '?limit=24' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
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
        if (!items.length) {
          foot.innerHTML = '<b>Nothing listed.</b> POST /api/skribls defaults to '
            + '<code>visibility: "unlisted"</code>, so nothing posted from the Pad '
            + 'appears here — a host feed’s composer is what sends '
            + '<code>"visibility": "public"</code>.';
        }
      })
      .catch(function () {
        moreWrap.innerHTML = '';
        foot.textContent = "Couldn't load the listing.";
      });
  }

  search.addEventListener('input', renderGrid);
  loadPage();
})();
