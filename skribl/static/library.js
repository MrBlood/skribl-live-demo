/* The profile's Skribls tab: every Skribl this listing returns, with a
 * transport a post is not allowed to have.
 *
 * IT SHOWS REAL POSTS. A page that draws its own content cannot tell you
 * whether the thing it is previewing WORKS; this reads GET /api/skribls and
 * plays real payloads, so when it is wrong it is wrong about something.
 *
 * IT DOES NOT CONTAIN A PLAYER.
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
 * ONE PAYLOAD AT A TIME. The grid tiles are share-card images, not players. Fifty mounted players each
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
  var stageEmpty = document.getElementById('stageEmpty');
  var stageError = document.getElementById('stageError');
  var libRetry = document.getElementById('libRetry');
  var playerCard = document.querySelector('.player');
  var btnFull = document.getElementById('btnFull');
  var loaded = !me;        /* host mode: no empty state until the first page answers */
  var listFailed = false;  /* host mode: the first page did not answer */

  var listEl = document.getElementById('postedList');
  var moreWrap = document.getElementById('moreWrap');
  var foot = document.getElementById('libFoot');
  var statCount = document.getElementById('statCount');
  var search = document.getElementById('postedSearch');
  var chips = document.querySelectorAll('.chips .chip[data-filter]');
  var showing = 'all';        /* the filter chip: all | public | unlisted */

  var stageBox = document.getElementById('stageBox');
  var stageWrap = stageBox.closest('.stageCanvasWrap');
  /* The drawing's own shape, for the stage's box (the template says why). The
     in-post player reads the same canvasSize, and falls back the same way. */
  function drawRatio(payload) {
    var cs = payload && payload.canvasSize;
    if (cs && cs.cssWidth > 0 && cs.cssHeight > 0) return cs.cssWidth + ' / ' + cs.cssHeight;
    var d = window.SkriblCanvasSizes && window.SkriblCanvasSizes.DEFAULT;
    return d ? d.w + ' / ' + d.h : '816 / 612';
  }
  /* BARE FROM THE FIRST PAINT, NOT ONLY IN FULL SCREEN. This page owns the
     transport under the stage at every size, so the component's own duration
     chip is a second answer to "how long is this" whenever it is visible --
     and the macro is already called with controls=false, so the chip is all
     `is-bare` suppresses here.

     DO NOT TOGGLE IT WITH FULL SCREEN. That is backwards -- full screen is
     the one moment the page's own row is off the display -- and the inversion
     costs a duplicated loop button on anything that has been full-screened
     once. Answered once, at build. */
  stageBox.classList.add('is-bare');
  var pTitle = document.getElementById('pTitle');
  var pKind = document.getElementById('pKind');
  var pMeta = document.getElementById('pMeta');
  var pVis = document.getElementById('pVis');
  var scrub = document.getElementById('scrub');
  var scrubFill = document.getElementById('scrubFill');
  var tElapsed = document.getElementById('tElapsed');
  var btnPlay = document.getElementById('btnPlay');
  var btnRestart = document.getElementById('btnRestart');
  var btnLoop = document.getElementById('btnLoop');
  var btnMute = document.getElementById('btnMute');
  var btnShare = document.getElementById('btnShare');

  /* THE TRANSPORT IS DEAD UNTIL SOMETHING IS ON THE STAGE (PRESEAL-005).
     Play, Restart, Loop and Copy link were enabled from the first paint and
     silently did nothing; Loop even toggled its own pressed state, which is a
     control reporting a change it did not make. They come alive when a
     payload has been adopted. Mute is not in this list: refresh() owns it,
     because whether it means anything depends on the drawing having sound.
     Full screen is in the list too (#10): an empty stage offered to go full
     screen on nothing, and looked as live as the rest. */
  function transportLive(on) {
    [btnPlay, btnRestart, btnLoop, btnShare, btnFull].forEach(function (b) {
      if (b) b.disabled = !on;
    });
    if (scrub) {
      scrub.setAttribute('aria-disabled', String(!on));
      scrub.classList.toggle('inert', !on);
    }
  }

  var items = [];          /* every row loaded so far, newest first */
  var cursor = null;       /* the keyset cursor for the next page */
  var current = null;      /* the item on the stage */
  var pending = null;      /* the item asked for and not on the stage yet */
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
    // One vocabulary on this page: the rows' (lib/posted.js), not a second one.
    if (window.SkriblPosted && window.SkriblPosted.ago) return window.SkriblPosted.ago(d.getTime());
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

  /* THE WORDS ABOVE THE TRANSPORT. Split out of select() so the reconcile can
     refresh them WITHOUT re-selecting: select() also loads the payload, and
     that fetch is what counts a play. */
  function showMeta(item) {
    pTitle.textContent = item.title || 'Untitled Skribl';
    pMeta.textContent = when(item.created_at);
    /* THREE STATES. `item.has_audio ? 'with sound' : 'silent'` called every
       unknown SILENT, and until the field existed at all that was every
       browser-kept row -- music included. An unknown says nothing, the same
       way the row's kind does. */
    /* HIDDEN, NOT BLANK. Emptying the text left the pill's own border and
       padding on screen — a 20px ghost under the title with nothing in it.
       A control that says nothing should not be there.
       With the reconcile above this is now rare rather than universal, but it
       is still reachable: a local save has no server post to ask. */
    var sound = item.has_audio === true ? 'with sound'
              : item.has_audio === false ? 'silent' : '';
    pKind.textContent = sound;
    pKind.hidden = !sound;
    /* The same three words the row uses (lib/postedui.js): in the gallery,
       link only, or the state's own name. A host row may not know; say
       nothing rather than guess.
       HIDDEN when there is nothing to say, for the same reason the sound pill
       above is: this span carries a `\u00B7` in a ::before, so an emptied one
       would leave a bare dot on the meta line. */
    var vis = !item.visibility ? ''
      : item.visibility === 'public' ? 'in the gallery'
      : item.visibility === 'unlisted' ? 'link only' : item.visibility;
    pVis.textContent = vis;
    pVis.hidden = !vis;
  }

  /* ONE IDENTITY ON SCREEN (outside audit V319-001). select() used to make
     the clicked item `current` before its payload had arrived: during a slow
     load the title, the highlighted row and Copy link all said B while A
     went on playing under the transport, and a failed B left A on the stage
     with Copy link pointing at B. Now the stage, its words, its row and every
     control keep saying A until B has actually been adopted -- B is only
     `pending` -- and a B that fails leaves A exactly as it was. */
  function markRows() {
    Array.prototype.forEach.call(listEl.querySelectorAll('.posted-row'), function (c) {
      var id = c.getAttribute('data-id');
      c.classList.toggle('active', !!current && id === current.id);
      if (pending && id === pending.id) c.setAttribute('aria-busy', 'true');
      else c.removeAttribute('aria-busy');
    });
  }

  function select(item) {
    /* THE ROW ALREADY ON THE STAGE (v321 preflight, PF-002). Picking it again
       fetched the whole payload again -- megabytes with a photo or a song --
       to hand the player the drawing it was already playing; the owner's
       network panel showed the second request. It restarts the drawing, as
       Restart does, and asks the network for nothing. A row still loading is
       let go: the person picked this one. */
    if (current && player && current.id === item.id) {
      pending = null;
      markRows();
      player.seek(0);
      player.play();
      refresh();
      return;
    }
    pending = item;
    /* An empty stage has nothing to contradict (the transport is dead until
       a payload lands), so it can say what is coming. */
    if (!current) showMeta(item);
    markRows();

    /* ONE FETCH, for the one drawing about to play. The listing already gave us
     * everything else on this page. */
    fetch(api + '/' + encodeURIComponent(item.id), { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        /* IS THIS STILL THE SKRIBL BEING ASKED FOR -- asked by id, not by
           object identity. The reconcile REPLACES an item with an equal one
           when it learns a row's kind or sound; an identity test would then
           drop this payload and leave the stage loading forever with no error
           anywhere. By id, select A, B, then A again, and A's first response
           is usable rather than discarded. `pending`, not the item passed in,
           is what lands: it is the freshest copy of the metadata. */
        if (!pending || pending.id !== item.id) return;
        current = pending;
        pending = null;
        var payload = (body && (body.skribl || body.payload)) || body;
        if (stageWrap) stageWrap.style.setProperty('--draw-ratio', drawRatio(payload));
        if (!player) {
          player = window.SkriblInline.attach(stageBox, payload);
          player.setLoop(looping);
        } else {
          player.adopt(payload);
        }
        showMeta(current);
        scrubFill.style.width = '0%';
        tElapsed.textContent = '0:00 / 0:00';
        setPlayIcon(false);
        markRows();
        transportLive(true);
        refresh();
      })
      .catch(function () {
        /* A failure for a request nobody is waiting on any more says nothing:
           it used to overwrite the title of whatever had loaded since. */
        if (!pending || pending.id !== item.id) return;
        pending = null;
        markRows();
        var live = document.getElementById('postedStatus');
        if (!current) {
          pTitle.textContent = "Couldn't load this Skribl.";
          if (live) live.textContent = "Couldn't load this Skribl.";
          return;
        }
        /* Something else is still on the stage and still what every control
           acts on, so the title stays its title; the failure is said under
           the list, where the row that was picked is. */
        var msg = "Couldn\u2019t load \u201c" + (item.title || 'Untitled Skribl')
                + "\u201d. Pick it again to retry.";
        foot.textContent = msg;
        if (live) live.textContent = msg;
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
  transportLive(false);
  if (btnMute) btnMute.disabled = true;

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
  /* FULL SIZE, ON EVERY DEVICE (lib/immersive.js). Gating this on
     `document.fullscreenEnabled` is right on its own terms and wrong in
     practice: iOS Safari has the API for <video> and nothing else, so the
     device where a drawing is smallest is the one with no way to enlarge it.
     The module takes the real API where there is one and pins the stage over
     the viewport where there is not. */
  if (btnFull && stageWrap && window.SkriblImmersive) {
    btnFull.hidden = false;
    /* THE SAME BAR THE GALLERY'S TILE USES (lib/fullbar.js). This page had an
       exit and no controls; the gallery had controls and no exit; neither
       looked like the other, which is what a screenshot showed. Neither
       page builds one now. */
    var fbar = window.SkriblFullBar ? window.SkriblFullBar.attach(stageWrap, {
      player: function () { return player; },
      meta: function () {
        return current ? { title: current.title,
                           name: me || '',
                           handle: me ? '@' + me : '' } : null;
      },
      onExit: function () { imm.close(); }
    }) : null;
    var syncFull = function (on) {
      btnFull.classList.toggle('on', !!on);
      btnFull.setAttribute('aria-pressed', String(!!on));
      btnFull.title = on ? 'Leave full screen' : 'Full screen';
      btnFull.setAttribute('aria-label', btnFull.title);
      if (fbar) fbar.running(!!on);
    };
    var imm = window.SkriblImmersive.attach(stageWrap, { onChange: syncFull });
    btnFull.addEventListener('click', function () { imm.toggle(); });
    /* THE EXIT IS NOT DECORATION AND IT IS LESS OPTIONAL THAN IT WAS. Under
       the real API only the fullscreened subtree renders, so the transport row
       is off screen and Escape is the only other way out; in the FALLBACK the
       page is still the page, and nothing at all exits it but this button. */
    var fullExit = document.getElementById('fullExit');
    if (fullExit) fullExit.addEventListener('click', function () { imm.close(); });
  }

  scrub.addEventListener('click', function (e) {
    if (!player) return;
    var r = e.currentTarget.getBoundingClientRect();
    var f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    player.seek(player.state().totalMs * f);
    refresh();
  });

  /* ---- the list ----------------------------------------------------------
     RENDERED BY lib/postedui.js — the shared rows, actions and custody
     rules — with this page's poster as each row's picture and the title
     putting the Skribl on the stage. What this
     file owns is the POPULATION (whose Skribls; see below), the filter chip
     and the words around the list. */
  var ui = null;

  function asItem(e) {
    /* A browser-kept entry from before v304 recorded no visibility, and no
       editor post before v304 sent one, so it is unlisted -- the server's
       default -- not unknown. A host row without one is unknown. */
    return { id: e.id, title: e.title || '', caption: '',
             kind: e.kind || null, pages: e.pages || 0,
             created_at: e.at ? new Date(e.at).toISOString() : (e.created_at || null),
             /* NOT `!!e.has_audio`: that collapsed "no sound" and "nobody
                said" into the same false, which is what put SILENT on a
                Skribl with music. */
             has_audio: e.has_audio === true ? true : e.has_audio === false ? false : null,
             visibility: e.visibility || (me ? '' : 'unlisted') };
  }

  function passes(e) {
    if (showing === 'all') return true;
    return (e.visibility || '') === showing;
  }

  /* THE THUMBNAIL IS THE DRAWING, NOT THE CARD. The picture behind each row
     is the share card -- 1200x630, a wordmark band across the foot and the
     drawing letterboxed on a plate in the middle -- and the stylesheet showed
     it by scaling to 128% and pulling up 5.5% so the band fell outside. That
     hides the branding rather than showing the drawing: it happens to land on
     the drawing for a 4:3 or 16:9 canvas and does not for the other two
     presets, so a 9:16 Skribl came out 35px wide in an 84px box with 24px of
     plate down each side. That is what the owner was looking at when they
     asked whether the page looked right.

     THE RECTANGLE COMES FROM lib/sharecard.js, the module that DEFINES it.
     The first cut of this read it from inlineplayer.js instead, by
     generalising that component's private fitPoster over box aspect and
     contain/cover and exporting it -- which worked, and cost 75 bytes in the
     file EVERY HOST downloads to embed a Skribl, for a crop only this page
     performs. verify_inline's budget caught it 32 bytes over and was right to:
     a host embedding a post should not pay for the profile page's thumbnails.
     Reading sharecard here costs those bytes to /library alone, and buys a
     better source at the same time -- inlineplayer inlines its own copy of
     these constants precisely so hosts need not load this module, so that copy
     is the derived one and this is the original.

     COVER, NOT CONTAIN, which is the one thing this does differently from the
     card and the tile: they letterbox the drawing into a frame, and a thumbnail
     this small has no room to spend on bars. Whichever axis runs out LAST
     decides, so the drawing fills the tile and the overflow is clipped by
     .posted-shot.

     THE BOX IS MEASURED, NOT ASSUMED: every length written below is a
     percentage of this element, so it needs the aspect the browser actually
     laid out, and a sheet that changes the thumb's size needs no second edit
     here. A shot with no shape on it keeps the band crop, which is what a row
     the reconcile has not reached yet gets -- a real state on the first paint
     after a post, not a hypothetical. */
  function fitShots() {
    var S = window.SkriblShareCard;
    if (!S || !listEl) return;
    Array.prototype.forEach.call(
      listEl.querySelectorAll('.posted-shot[data-skribl-w][data-skribl-h]'),
      function (shot) {
        var img = shot.querySelector('.posted-poster');
        var w = +shot.getAttribute('data-skribl-w');
        var h = +shot.getAttribute('data-skribl-h');
        var box = shot.getBoundingClientRect();
        if (!img || !(w > 0 && h > 0) || !(box.width > 0 && box.height > 0)) return;
        var r = S.drawingRect(w, h);          /* card pixels */
        if (!(r.w > 0 && r.h > 0)) return;
        /* Units of the BOX's height: width is A, height is 1. */
        var A = box.width / box.height, a = r.w / r.h;
        var cw = Math.max(a, A), ch = cw / a;
        var k = cw / r.w, st = img.style, i = S.PLATE_LW;
        function p(n, of) { return n / of * 100 + '%'; }
        st.width = p(S.CARD_W * k, A);
        st.height = p(S.CARD_H * k, 1);
        st.left = p((A - cw) / 2 - r.x * k, A);
        st.top = p((1 - ch) / 2 - r.y * k, 1);
        /* The stylesheet centres the band crop with a transform; this one is
           positioned outright, so the transform has to go or it shifts twice. */
        st.transform = 'none';
        st.maxWidth = 'none';
        /* Clipped to the drawing INSIDE its plate hairline, so the accent
           stroke on the card's edge is never in frame. */
        st.clipPath = 'inset(' + p(r.y + i, S.CARD_H) + ' '
          + p(S.CARD_W - r.x - r.w + i, S.CARD_W) + ' '
          + p(S.CARD_H - r.y - r.h + i, S.CARD_H) + ' '
          + p(r.x + i, S.CARD_W) + ')';
      });
  }

  function words(all, hits) {
    var q = (search && search.value.trim()) || '';
    /* NOT KNOWING IS NOT ZERO (V319-003). A listing that failed says so, and
       says nothing about how many there are; the empty card and its "Post a
       Skribl" line are for a listing that answered with none. */
    var failed = listFailed && !all.length;
    statCount.textContent = failed ? '\u2014' : all.length;
    if (libEmpty) libEmpty.hidden = all.length > 0 || !loaded || failed;
    // Nothing posted: the player card becomes the empty card (Blooby, Make one).
    var none = loaded && !all.length && !failed;
    if (stageEmpty) stageEmpty.hidden = !none;
    if (stageError) stageError.hidden = !failed;
    if (playerCard) playerCard.classList.toggle('is-empty', none || failed);
    foot.textContent = !all.length ? ''
      : (q ? (me ? 'Filtering the ' + all.length + ' loaded so far. Load more to search further.'
                 : 'Filtering your ' + all.length + '.')
           : 'Newest first. Pick one to play it.');
    markRows();
    fitShots();
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
      reconcile();
      var first = window.SkriblPosted.list().filter(function (e) { return e && e.id && !e.local; })[0];
      if (first) select(asItem(first));
    }
  }

  /* BACKFILL THE BROWSER, the way the migration backfilled the database.
     `kind`, `pages` and `has_audio` were each added after posts were already
     being made, so every row this browser wrote before them reads undefined —
     and a client that renders an unknown honestly then shows nothing, which
     looks exactly like a feature that did not ship. Rendering is right; the
     data is old.

     GET /api/skribls/meta, NOT /api/skribls/<id>. The per-id endpoint answers
     with the whole payload and COUNTS A PLAY — reconciling thirty rows through
     it would have pulled thirty payloads and added thirty plays to the owner's
     own counts. A listing is not a play.

     Local saves are skipped: there is no server post to ask about. Failure is
     silent and harmless — the rows render exactly as they did before, which is
     the state this repairs rather than one it creates. */
  function reconcile() {
    var store = window.SkriblPosted;
    if (!store) return;
    var stale = store.list().filter(function (e) {
      return e && e.id && !e.local
          && (!e.kind || typeof e.has_audio !== 'boolean'
              || !(e.canvas_w > 0 && e.canvas_h > 0));
    }).map(function (e) { return e.id; });
    if (!stale.length) return;
    var chunks = [];
    for (var i = 0; i < stale.length; i += 50) chunks.push(stale.slice(i, i + 50));
    Promise.all(chunks.map(function (ids) {
      return fetch(api + '/meta?ids=' + encodeURIComponent(ids.join(',')),
                   { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .catch(function () { return { items: [] }; });
    })).then(function (answers) {
      var touched = 0;
      answers.forEach(function (body) {
        (body.items || []).forEach(function (it) {
          if (store.update(it.id, { kind: it.kind, pages: it.pages,
                                    has_audio: it.has_audio,
                                    canvas_w: it.canvas_w, canvas_h: it.canvas_h,
                                    visibility: it.visibility })) touched++;
        });
      });
      /* Only repaint when something actually moved: a reconcile that changed
         nothing must not stamp over the row the person has already selected. */
      if (touched && ui) {
        ui.render();
        /* THE WORDS, NOT THE WHOLE SELECTION. select() loads the payload, and
           the payload fetch is the one that COUNTS A PLAY -- re-selecting
           here makes the stage fetch the same Skribl twice on every boot and
           counts a second play for one look. The reconcile only ever learns
           metadata, so it only writes metadata. */
        if (current) {
          var fresh = store.list().filter(function (e) { return e.id === current.id; })[0];
          if (fresh) { current = asItem(fresh); showMeta(current); }
        }
        /* The item still loading learns it too, and is what select() commits. */
        if (pending) {
          var later = store.list().filter(function (e) { return e.id === pending.id; })[0];
          if (later) { pending = asItem(later); if (!current) showMeta(pending); }
        }
      }
    });
  }

  if (libRetry) libRetry.addEventListener('click', function () {
    libRetry.disabled = true;
    loadPage();
  });

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
          /* THE LISTING CARRIES THE KIND. It still defers the PAYLOAD -- that is
             not going to change -- but `kind` and `pages` are columns on the
             post, written at post time from the same payload `has_audio` comes
             from, so a row can say which it is without one. A null means "not
             backfilled" and renders as nothing. `canvas_w`/`canvas_h` are two
             more of them, and the host branch needs no reconcile to learn
             them: the listing has answered with them since v309. */
          hostRows.push({ id: i.id, url: playerBase + '/' + encodeURIComponent(i.id), title: i.title || '',
                          kind: i.kind || null, pages: i.pages || 0,
                          at: i.created_at ? Date.parse(i.created_at) : Date.now(),
                          visibility: i.visibility || '',
                          canvas_w: i.canvas_w || 0, canvas_h: i.canvas_h || 0,
                          has_audio: i.has_audio === true ? true : i.has_audio === false ? false : null,
                          owned: true, tok: null });
        });
        items = hostRows.map(asItem);
        cursor = body.next_cursor || null;
        loaded = true;
        listFailed = false;
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
        if (!current && !pending && items.length) select(items[0]);
        /* An empty profile is the empty state above the footer (renderGrid
           hides and shows it); the route-naming sentence that used to sit
           here is gone with the population it described. */
      })
      .catch(function () {
        var live = document.getElementById('postedStatus');
        loaded = true;
        if (libRetry) libRetry.disabled = false;
        moreWrap.innerHTML = '';
        if (hostRows.length) {
          /* A LATER PAGE FAILED. What is on the page stays; the button that
             asked for more asks again. */
          var again = document.createElement('button');
          again.type = 'button';
          again.className = 'more';
          again.textContent = 'Couldn\u2019t load more \u2014 try again';
          again.addEventListener('click', function () { loadPage(); });
          moreWrap.appendChild(again);
          if (live) live.textContent = 'Couldn\u2019t load more of your Skribls.';
          return;
        }
        listFailed = true;
        renderGrid();
        if (live) live.textContent = 'Couldn\u2019t load your Skribls. They\u2019re still there.';
      });
  }

  /* The module is loaded by the page and started here; it suppresses itself
     on coarse pointers, so on a phone this call does nothing by design. */
  if (window.SkriblTooltip) window.SkriblTooltip.init();

  /* ---- DRAFTS (v317) -------------------------------------------------
     The second tab lists SkriblSavedDrafts: the account's drafts when the
     host says who is signed in, this browser's otherwise, the same list the
     editors' ⋯ Open a draft… shows. Open goes to the editor that made the
     draft with ?draft=<id> (the editors' own hand-off); Delete asks on the
     button first. #drafts in the address opens this tab. */
  var tabS = document.getElementById('tabSkribls');
  var tabD = document.getElementById('tabDrafts');
  var panS = document.getElementById('libSkribls');
  var panD = document.getElementById('libDrafts');
  var dList = document.getElementById('draftsList');
  var dEmpty = document.getElementById('draftsEmpty');
  var dWhere = document.getElementById('draftsWhere');
  var libSection = panS && panS.closest('section');
  var draftsCfg = window.SKRIBL_DRAFTS || {};
  var SD = window.SkriblSavedDrafts;

  /* THE SAME ROW AS THE EDITORS' SHEET (v317): picture, name, "Pad · 12m
     ago", and a bin. The owner: too many bubble pills, and the sheet "looks
     nothing like the others". The card itself opens the draft, in the editor
     that made it; the bin asks once, and only one row asks at a time. */
  var BIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    + 'stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/>'
    + '<path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/></svg>';
  var draftDisarmers = [];
  function draftRow(it) {
    var row = document.createElement('div');
    row.className = 'draft-row';
    var kind = it.kind === 'flip' ? 'Flip' : 'Pad';
    var title = it.title || 'Untitled Skribl';
    var base = it.kind === 'flip' ? draftsCfg.flip : draftsCfg.pad;
    var open = document.createElement('a');
    open.className = 'draft-open';
    open.href = (base || '') + '?draft=' + encodeURIComponent(it.id);
    open.setAttribute('aria-label', 'Open ' + title + ' in ' + kind);
    var pic = document.createElement('span');
    pic.className = 'draft-pic';
    if (it.thumbnail) {
      var img = document.createElement('img');
      img.alt = '';
      img.src = it.thumbnail;
      pic.appendChild(img);
    }
    var words = document.createElement('span');
    words.className = 'draft-words';
    var name = document.createElement('span');
    name.className = 'draft-name';
    name.textContent = title;
    var meta = document.createElement('span');
    meta.className = 'draft-meta';
    meta.textContent = kind + ' \u00B7 ' + (SD ? SD.ago(it.updatedAt) : '');
    words.appendChild(name);
    words.appendChild(meta);
    open.appendChild(pic);
    open.appendChild(words);
    var del = document.createElement('button');
    del.type = 'button';
    del.className = 'draft-del';
    del.innerHTML = BIN;
    del.setAttribute('aria-label', 'Delete ' + title);
    /* THE BIN ASKS WITHOUT MOVING (#3; the v317 bin rule). Armed, it keeps
       its 44px circle and tints its icon, and the META LINE asks -- spoken,
       since the line is a live region. It disarms when focus leaves it, on a
       tap anywhere else, and on a 20 s safety net: a question that never goes
       away is a trap for the next stray tap, and one that goes away in four
       seconds is a race. The editors' saved-drafts sheet is the same row. */
    meta.setAttribute('aria-live', 'polite');
    var metaText = meta.textContent, armed = false, armT = null;
    function outside(e) { if (!del.contains(e.target)) disarm(); }
    function disarm() {
      if (!armed) return;
      armed = false;
      clearTimeout(armT);
      document.removeEventListener('pointerdown', outside, true);
      del.classList.remove('armed');
      meta.classList.remove('asks');
      meta.textContent = metaText;
      del.setAttribute('aria-label', 'Delete ' + title);
    }
    draftDisarmers.push(disarm);
    del.addEventListener('focusout', disarm);
    del.addEventListener('click', function () {
      if (!armed) {
        draftDisarmers.forEach(function (d) { if (d !== disarm) d(); });
        armed = true;
        del.classList.add('armed');
        meta.classList.add('asks');
        meta.textContent = 'Tap the bin again to delete';
        del.setAttribute('aria-label', 'Tap again to delete ' + title);
        armT = setTimeout(disarm, 20000);
        document.addEventListener('pointerdown', outside, true);
        return;
      }
      disarm();
      // The rebuilt list takes the focused bin with it: focus goes to the row
      // that took this one's place, or the Drafts tab (third review). Read
      // before the bin is disabled, which drops its focus by itself.
      var at = Array.prototype.indexOf.call(dList.querySelectorAll('.draft-row'), row);
      var hadFocus = row.contains(document.activeElement);
      del.disabled = true;
      SD.remove(it.id).then(renderDrafts, function (e) {
        del.disabled = false;
        meta.textContent = metaText = e.message;
        return false;
      }).then(function (ok) {
        if (ok === false || !hadFocus) return;
        var rows = dList.querySelectorAll('.draft-row');
        var next = rows[Math.min(at, rows.length - 1)];
        var target = (next && next.querySelector('.draft-open')) || document.getElementById('tabDrafts');
        if (target) target.focus();
      });
    });
    row.appendChild(open);
    row.appendChild(del);
    return row;
  }

  // Only the latest list draws (v317 review): a read that answers late must not
  // put back a row deleted since.
  var draftsSeq = 0;
  /* THE SEARCH IS BOTH TABS' (owner, from a mock): one field beside the tabs,
     so nothing moves when you switch, and on Drafts it narrows the drafts by
     title as it narrows the Skribls on theirs. The list is read once per
     render and filtered here, so typing does not re-read storage. */
  var draftsItems = null;
  function draftsQuery() { return (search && search.value.trim().toLowerCase()) || ''; }
  /* "3 of 25 drafts" (owner): how close you are to the limit, said where the
     list says where it is kept. The limit is SKRIBL_MAX_DRAFTS, never typed. */
  function draftsLine(n) {
    var lim = draftsCfg.limit;
    var count = (lim ? n + ' of ' + lim : String(n)) + (n === 1 && !lim ? ' draft' : ' drafts');
    return count + ' \u00B7 ' + (SD.where() === 'account'
      ? 'saved to your account, on every device you sign in on.'
      : 'saved on this browser only.');
  }
  function drawDrafts() {
    if (!draftsItems) return;
    var q = draftsQuery();
    var shown = q ? draftsItems.filter(function (it) {
      return (it.title || 'Untitled Skribl').toLowerCase().indexOf(q) !== -1;
    }) : draftsItems;
    dList.textContent = '';
    draftDisarmers.forEach(function (d) { d(); });   // a stale question takes its listener with it
    draftDisarmers = [];
    dEmpty.hidden = draftsItems.length > 0;
    shown.forEach(function (it) { dList.appendChild(draftRow(it)); });
    if (q && !shown.length && draftsItems.length) {
      var none = document.createElement('p');
      none.className = 'state drafts-nomatch';
      none.textContent = 'No draft is called that.';
      dList.appendChild(none);
    }
  }
  function renderDrafts() {
    if (!SD || !dList) return;
    var mine = ++draftsSeq;
    return SD.list().then(function (items) {
      if (mine !== draftsSeq) return;
      draftsItems = items;
      dWhere.textContent = (SD.stalled && SD.stalled()) || draftsLine(items.length);
      drawDrafts();
    }, function (e) {
      if (mine !== draftsSeq) return;
      dList.textContent = '';
      dEmpty.hidden = true;
      dWhere.textContent = e.message;
    });
  }

  function showTab(drafts, focus) {
    if (!tabS || !tabD) return;
    tabS.classList.toggle('active', !drafts);
    tabD.classList.toggle('active', drafts);
    tabS.setAttribute('aria-selected', String(!drafts));
    tabD.setAttribute('aria-selected', String(drafts));
    tabS.tabIndex = drafts ? -1 : 0;
    tabD.tabIndex = drafts ? 0 : -1;
    panS.hidden = drafts;
    panD.hidden = !drafts;
    if (libSection) libSection.classList.toggle('drafts-mode', drafts);
    if (focus) (drafts ? tabD : tabS).focus();
    try {
      history.replaceState(null, '', location.pathname + location.search + (drafts ? '#drafts' : ''));
    } catch (e) {}
    if (drafts) renderDrafts();
  }
  var searchClear = document.getElementById('searchClear');
  function searchChanged() {
    if (searchClear) searchClear.hidden = !(search && search.value);
    if (libSection && libSection.classList.contains('drafts-mode')) drawDrafts();
  }
  if (search) {
    search.addEventListener('input', searchChanged);
    // Esc empties the field in lib/postedui.js without an input event.
    search.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setTimeout(searchChanged, 0);
    });
  }
  if (searchClear) searchClear.addEventListener('click', function () {
    search.value = '';
    search.dispatchEvent(new Event('input', { bubbles: true }));
    search.focus();
  });
  if (tabS && tabD) {
    tabS.addEventListener('click', function () { showTab(false); });
    tabD.addEventListener('click', function () { showTab(true); });
    /* The tabs pattern: arrows move between them, Home/End jump. */
    [tabS, tabD].forEach(function (t) {
      t.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'Home' || e.key === 'End') {
          e.preventDefault();
          var toDrafts = e.key === 'End' || (e.key === 'ArrowRight' && t === tabS) || (e.key === 'ArrowLeft' && t === tabS);
          if (e.key === 'Home') toDrafts = false;
          showTab(toDrafts, true);
        }
      });
    });
    if (location.hash === '#drafts') showTab(true);
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
