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
  var btnFull = document.getElementById('btnFull');
  var loaded = !me;        /* host mode: no empty state until the first page answers */

  var listEl = document.getElementById('postedList');
  var moreWrap = document.getElementById('moreWrap');
  var foot = document.getElementById('libFoot');
  var statCount = document.getElementById('statCount');
  var search = document.getElementById('postedSearch');
  var chips = document.querySelectorAll('.chips .chip[data-filter]');
  var showing = 'all';        /* the filter chip: all | public | unlisted */

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
    /* The same three words the row uses (lib/postedui.js): in the gallery,
       link only, or the state's own name. A host row may not know; say
       nothing rather than guess. */
    pStats.textContent = !item.visibility ? ''
      : item.visibility === 'public' ? 'in the gallery'
      : item.visibility === 'unlisted' ? 'link only' : item.visibility;
    scrubFill.style.width = '0%';
    tElapsed.textContent = '0:00 / 0:00';
    setPlayIcon(false);
    Array.prototype.forEach.call(listEl.querySelectorAll('.posted-row'), function (c) {
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
    /* SAYS WHAT HAPPENED (PRESEAL-002). This ran its "Link copied" handler as
       BOTH arms of .then(), and again when there was no Clipboard API at all,
       so a refused copy was reported as a completed one. lib/postedui.js owns
       the one copy implementation and answers whether the text got there. */
    var rest = 'Copy link';
    function say(msg) {
      btnShare.title = msg;
      btnShare.setAttribute('aria-label', msg);
      var live = document.getElementById('postedStatus');
      if (live) live.textContent = msg;
      clearTimeout(btnShare._t);
      btnShare._t = setTimeout(function () {
        btnShare.title = rest;
        btnShare.setAttribute('aria-label', rest);
      }, 1600);
    }
    var copier = window.SkriblPostedUI && window.SkriblPostedUI.copyText;
    if (!copier) { say("Couldn't copy the link"); return; }
    copier(url).then(function (ok) {
      say(ok ? 'Link copied' : "Couldn't copy the link");
    });
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

  /* ---- the list ----------------------------------------------------------
     RENDERED BY lib/postedui.js — the same rows, actions and custody rules
     the editors' drawer had until v304 — with this page's poster as each
     row's picture and the title putting the Skribl on the stage. What this
     file owns is the POPULATION (whose Skribls; see below), the filter chip
     and the words around the list. */
  var ui = null;

  function asItem(e) {
    /* A browser-kept entry from before v304 recorded no visibility, and no
       editor post before v304 sent one, so it is unlisted -- the server's
       default -- not unknown. A host row without one is unknown. */
    return { id: e.id, title: e.title || '', caption: '',
             created_at: e.at ? new Date(e.at).toISOString() : (e.created_at || null),
             has_audio: !!e.has_audio, visibility: e.visibility || (me ? '' : 'unlisted') };
  }

  function passes(e) {
    if (showing === 'all') return true;
    return (e.visibility || '') === showing;
  }

  function words(all, hits) {
    var q = (search && search.value.trim()) || '';
    statCount.textContent = all.length;
    if (libEmpty) libEmpty.hidden = all.length > 0 || !loaded;
    foot.textContent = !all.length ? ''
      : (q ? (me ? 'Filtering the ' + all.length + ' loaded so far. Load more to search further.'
                 : 'Filtering your ' + all.length + '.')
           : 'Newest first. Pick one to play it.');
    if (current) {
      Array.prototype.forEach.call(listEl.querySelectorAll('.posted-row'), function (c) {
        c.classList.toggle('active', c.getAttribute('data-id') === current.id);
      });
    }
  }

  function renderGrid() { if (ui) ui.render(); }

  Array.prototype.forEach.call(chips, function (chip) {
    chip.addEventListener('click', function () {
      showing = chip.getAttribute('data-filter') || 'all';
      Array.prototype.forEach.call(chips, function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-pressed', String(on));
      });
      renderGrid();
    });
  });

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
                           every listing by definition). Rows are marked
                           `owned`, so Delete and the gallery switch appear:
                           the server authorises them by author.
       NO ACCOUNTS         the list this browser kept — lib/posted.js, the same
                           record "Your Skribls" has always been. Unlisted
                           posts included: they are yours. Local-only fallbacks
                           (ids starting local_) stay listed as what they are,
                           on this device.

     Nothing is fetched to build the list: the row's picture is the poster,
     and one payload is fetched when a title is picked. The gallery is the
     public page. This one never was. */
  var hostRows = [];       /* the host branch's entries, in listing order */

  function hostSource() { return hostRows; }

  function boot() {
    /* A HOST'S PROFILE IS NOT A BROWSER'S LIST, and two sentences on the
       page say it is: the empty state's "kept in this browser only", and
       the panel's footer about site data and local saves. Both describe
       lib/posted.js, which the host branch never reads. */
    if (me) {
      if (libEmptyLocal) libEmptyLocal.hidden = true;
      var footTop = document.querySelector('#postedPanel .posted-foot-top');
      if (footTop) footTop.hidden = true;
    }
    ui = window.SkriblPostedUI && window.SkriblPostedUI.init({
      poster: posterUrl,
      onSelect: function (e) { select(asItem(e)); },
      filter: passes,
      onRender: words,
      source: me ? hostSource : null,
      pageEmpty: true,
      onRemoved: function (id) { hostRows = hostRows.filter(function (e) { return e.id !== id; }); }
    });
    window._skriblPostedUI = ui;
    if (!ui) return;
    if (!me) {
      var first = window.SkriblPosted.list().filter(function (e) { return e && e.id && !e.local; })[0];
      if (first) select(asItem(first));
    }
  }

  function loadPage() {
    if (!me) { renderGrid(); moreWrap.innerHTML = ''; return Promise.resolve(); }
    var url = api + '?limit=24&user_id=' + encodeURIComponent(me)
            + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    moreWrap.innerHTML = '<span class="more-status">Loading…</span>';
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        (body.items || []).forEach(function (i) {
          /* No kind: the listing defers the payload, so a host row does not
             know whether it is a Pad or a Flip, and the row says nothing it
             cannot know (lib/postedui.js). */
          hostRows.push({ id: i.id, url: playerBase + '/' + encodeURIComponent(i.id), title: i.title || '',
                          kind: null, pages: 0, at: i.created_at ? Date.parse(i.created_at) : Date.now(),
                          visibility: i.visibility || '', has_audio: !!i.has_audio, owned: true, tok: null });
        });
        items = hostRows.map(asItem);
        cursor = body.next_cursor || null;
        loaded = true;
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
        loaded = true;
        renderGrid();
        foot.textContent = "Couldn't load the listing.";
      });
  }

  boot();
  loadPage();
})();

/* THE BOOT FLAG, and it must stay last. app.js and flip.js have set one since
   v-early; this surface did not, so every suite that opened it waited a fixed
   guess instead of a signal — the harness spent 15.7 minutes sleeping and 78
   seconds launching browsers. A flag is the cheapest possible check for the
   most expensive possible bug (the file did not reach its end), and unlike a
   page-error listener it also catches a swallowed throw. */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { library: true });
