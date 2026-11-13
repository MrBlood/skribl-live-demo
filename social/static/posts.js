/* Posts (piece 4): Home's composer and feed (feed.html), a post's own page
 * (post.html), and the ⋯ sheet both share (social/_post.html).
 *
 * THE COMPOSER. Draw and Flip open Skribl's editor over Home in compose mode
 * (social.js's SocialPadOverlay over lib/composehost.js). Its Add hands the
 * drawing back; it shows here in Skribl's in-post player
 * (SkriblInline.attach: the same player the post will have), with Edit
 * drawing (the editor again, the drawing in it) and Remove. Post sends the
 * words and the drawing to the site (/posts, its token in X-Social-CSRF) and
 * goes to the new post's page. A press on Post with nothing drawn says so;
 * nothing is posted before Post.
 *
 * THE FEED: Load more brings the next page in place and mounts its players
 * (SkriblInline.mount, as Skribl asks of a feed that adds posts later). A tap
 * anywhere on a card's own ground opens its post; what has a job of its own
 * keeps it (below, "ANYWHERE ON A CARD").
 *
 * A POST'S OWN PAGE plays its drawing by itself once it is here (the
 * player's own play(), docs/INTEGRATION.md "A post's own page can start
 * it"), sound off until the viewer turns it on, and never under Reduce
 * Motion; the feed's players wait for a tap. Opened at a comment from
 * Activity (#c-<id>), comments.js says whether it plays: a drawing answer
 * there draws itself instead.
 *
 * THE ⋯ SHEET (social.js's SocialSheet, as Make's): Copy link, Share…,
 * Report this post and, signed in, Block @them; or on your own Delete post.
 * Report and Delete each rise as a sheet of their own: Report into the
 * site's own queue (/report, the page's token, the Gallery's reasons and "A
 * child's safety"; piece 5), Delete asked once. Block is safety.js's sheet
 * (window.SocialSafety), and afterwards Home says so.
 *
 * TIMES are said in the person's own time: "35m" in the feed, "Nov 10 at
 * 8:20 PM" on a post's page (social.js's SocialWhen, with this page's
 * words); without the scripts, the day in UTC.
 *
 * The words are the page's ([data-word]): this file says nothing of its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key, vars) {
    var s = WORDS[key] || '';
    Object.keys(vars || {}).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  function tell(box, text) {
    if (!box) return;
    box.textContent = text || '';
    box.hidden = !text;
  }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var pageSay = doc.querySelector('[data-feed-say], [data-page-say]');

  function post(url, body, headers) {
    var h = { 'Content-Type': 'application/json' };
    Object.keys(headers || {}).forEach(function (k) { h[k] = headers[k]; });
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: h, body: JSON.stringify(body || {}) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!j || typeof j !== 'object') j = {};
          j.status = r.status;
          return j;
        });
      }, function () { return { error: 'network' }; });
  }
  function why(j) {
    if (!j) return say('failed');
    if (j.error === 'rejected' && j.message) return j.message;
    if (WORDS[j.error]) return say(j.error);
    if (j.status === 413) return say('too_big');
    if (j.status === 429) return say('limited');
    if (j.status === 403) return say('stale');
    if (j.status === 401) return say('signed_out');
    return say('failed');
  }

  /* ---- times, in the person's own -------------------------------------- */
  /* One way to say a time, social.js's (window.SocialWhen), for this page and
     for what arrives later: a comment (comments.js), a page of the feed. */
  var when = window.SocialWhen || function () {};
  when();

  /* ---- a post's link: copied, or the device's own share sheet ------------- */
  function absolute(url) { return new URL(url, window.location.href).href; }
  function copy(url, box) {
    function byHand() { tell(box, say('copy_by_hand', { url: url })); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () { tell(box, say('copied')); }, byHand);
    } else byHand();
  }
  function share(url, box) {
    if (navigator.share) {
      navigator.share({ url: url }).catch(function () { /* closed: nothing to say */ });
    } else copy(url, box);
  }

  /* ---- the post a control belongs to ------------------------------------- */
  function postOf(el) {
    var p = el.closest('[data-post]') || doc.querySelector('.post-page[data-post]');
    if (!p) return null;
    return { el: p, id: p.getAttribute('data-post'), url: absolute(p.getAttribute('data-url')),
             skribl: p.getAttribute('data-skribl'), mine: p.hasAttribute('data-mine'),
             del: p.getAttribute('data-del'), kind: p.getAttribute('data-kind') || 'p',
             handle: p.getAttribute('data-handle') || '' };
  }

  /* ---- the ⋯ sheet, and Report and Delete -------------------------------- */
  var current = null;
  var menuWrap = doc.getElementById('postSheet');
  var reportWrap = doc.getElementById('reportSheet');
  var deleteWrap = doc.getElementById('deleteSheet');
  var menu = menuWrap && window.SocialSheet ? window.SocialSheet(menuWrap, { doorCloses: false }) : null;
  var report = reportWrap && window.SocialSheet
    ? window.SocialSheet(reportWrap, { doorCloses: false, ownTouch: '.post-note',
                                       first: function () { return reportWrap.querySelector('input[name=reason]:checked'); } })
    : null;
  var del = deleteWrap && window.SocialSheet
    ? window.SocialSheet(deleteWrap, { doorCloses: false, first: function () { return deleteWrap.querySelector('[data-make-close]:not(.make-scrim):not(.make-grip)'); } })
    : null;
  var opener = null;

  doc.addEventListener('click', function (e) {
    var m = e.target.closest('[data-post-menu]');
    if (m && menu) {
      e.preventDefault();
      current = postOf(m);
      if (!current) return;
      opener = m;
      Array.prototype.forEach.call(menuWrap.querySelectorAll('[data-mine-only]'), function (b) { b.hidden = !current.mine; });
      Array.prototype.forEach.call(menuWrap.querySelectorAll('[data-theirs]'), function (b) { b.hidden = current.mine; });
      var who = menuWrap.querySelector('[data-block-who]');
      if (who) who.textContent = say('block_who', { handle: current.handle });
      tell(menuWrap.querySelector('[data-post-say]'), '');
      menu.open(m);
      return;
    }
    var s = e.target.closest('[data-post-share]');
    if (s) {
      var p = postOf(s);
      if (p) share(p.url, pageSay);
    }
  });

  if (menuWrap) {
    menuWrap.addEventListener('click', function (e) {
      var a = e.target.closest('[data-act]');
      if (!a || !current) return;
      var act = a.getAttribute('data-act'), box = menuWrap.querySelector('[data-post-say]');
      if (act === 'copy') copy(current.url, box);
      else if (act === 'share') share(current.url, box);
      else if (act === 'report' && report) {
        menu.close(true);
        resetReport();
        report.open(opener);
      } else if (act === 'block' && window.SocialSafety) {
        menu.close(true);
        window.SocialSafety.block(current.handle, opener);
      } else if (act === 'delete' && del) {
        menu.close(true);
        tell(deleteWrap.querySelector('[data-delete-say]'), '');
        /* A drawing shown outside a post has no words to lose. */
        deleteWrap.querySelector('[data-lede-p]').hidden = current.kind === 's';
        deleteWrap.querySelector('[data-lede-s]').hidden = current.kind !== 's';
        del.open(opener);
      }
    });
  }

  function resetReport() {
    var form = reportWrap.querySelector('[data-report-form]');
    form.reset();
    var send = reportWrap.querySelector('[data-report-send]');
    send.disabled = false;
    send.hidden = false;
    var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
    if (c && c.hasAttribute('data-was')) { c.textContent = c.getAttribute('data-was'); c.removeAttribute('data-was'); }
    tell(reportWrap.querySelector('[data-report-say]'), '');
  }
  if (reportWrap) {
    reportWrap.querySelector('[data-report-form]').addEventListener('submit', function (e) {
      e.preventDefault();
      if (!current) return;
      var send = reportWrap.querySelector('[data-report-send]'), box = reportWrap.querySelector('[data-report-say]');
      var picked = reportWrap.querySelector('input[name=reason]:checked');
      send.disabled = true;
      tell(box, say('sending'));
      /* A drawing shown outside a post is reported as itself. */
      var drawing = current.kind === 's';
      post(reportWrap.getAttribute('data-report'),
           { kind: drawing ? 'drawing' : 'post', target: drawing ? current.skribl : current.id,
             reason: picked ? picked.value : 'other', note: (reportWrap.querySelector('.post-note').value || '').trim() },
           { 'X-Social-CSRF': token })
        .then(function (j) {
          if (j.status === 202) {
            tell(box, say('reported'));
            send.hidden = true;
            var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
            if (c) { c.setAttribute('data-was', c.textContent); c.textContent = say('done'); }
            return;
          }
          send.disabled = false;
          tell(box, j.status === 429 ? say('report_limited') : j.error === 'network' ? say('network') : say('failed'));
        });
    });
  }

  if (deleteWrap) {
    deleteWrap.querySelector('[data-delete-now]').addEventListener('click', function (e) {
      if (!current) return;
      var b = e.currentTarget, box = deleteWrap.querySelector('[data-delete-say]');
      b.disabled = true;
      tell(box, say('deleting'));
      post(current.del || deleteWrap.getAttribute('data-delete').replace('__ID__', encodeURIComponent(current.id)), {},
           { 'X-Social-CSRF': token })
        .then(function (j) {
          if (j.ok && j.go) { window.location.assign(j.go); return; }
          b.disabled = false;
          tell(box, why(j));
        });
    });
  }

  /* ---- ANYWHERE ON A CARD OPENS ITS POST ----------------------------------
     (the owner's yes, Nov 12.) A tap or a click on a card's own ground opens
     its page, as its words and its time do: they are its real links, for a
     keyboard and a screen reader, and the card is not one big link. What
     does a thing of its own keeps it: the drawing plays and pauses and never
     opens the post (its player keeps its own taps from reaching here); the
     face, the name and the @handle open the person's page; ⋯ and Share do
     their own job; the 💬 opens the comments; any other control its own. A
     press that moved is a drag, not a tap, and a click that ends a text
     selection opens nothing, a link's included. With Ctrl or ⌘, or the
     middle button, the post opens in a new tab, as a link's would. */
  var OWN = 'a, button, input, textarea, select, label, summary, [role="button"], [role="slider"], [tabindex], .post-art';
  var press = null;
  doc.addEventListener('pointerdown', function (e) { press = { x: e.clientX, y: e.clientY }; }, true);
  /* A keyboard's click (Enter on a link) has no press behind it (detail 0). */
  function moved(e) {
    return e.detail > 0 && !!press && Math.abs(e.clientX - press.x) + Math.abs(e.clientY - press.y) > 6;
  }
  function selectedIn(card) {
    var s = window.getSelection ? window.getSelection() : null;
    return !!s && !s.isCollapsed && !!String(s).trim() && (card.contains(s.anchorNode) || card.contains(s.focusNode));
  }
  /* The card a tap on its own ground opened, or null. */
  function tapped(e) {
    var card = e.target && e.target.closest ? e.target.closest('.post-card') : null;
    if (!card || e.defaultPrevented) return null;
    var own = e.target.closest(OWN);
    if (own && card.contains(own)) return null;
    if (moved(e) || selectedIn(card)) return null;
    return card;
  }
  doc.addEventListener('click', function (e) {
    var card = e.target && e.target.closest ? e.target.closest('.post-card') : null;
    if (!card) return;
    var a = e.target.closest('a');
    if (a && card.contains(a)) {
      /* A drag that selected words, ending on a link, is a selection. */
      if (moved(e) && selectedIn(card)) e.preventDefault();
      return;
    }
    if (e.button !== 0 || !tapped(e)) return;
    var url = card.getAttribute('data-url');
    if (!url) return;
    if (e.ctrlKey || e.metaKey || e.shiftKey) window.open(url, '_blank', 'noopener');
    else window.location.assign(url);
  });
  doc.addEventListener('auxclick', function (e) {
    if (e.button !== 1) return;
    var card = tapped(e);
    if (card && card.getAttribute('data-url')) window.open(card.getAttribute('data-url'), '_blank', 'noopener');
  });

  /* ---- a post's own page: it plays by itself ----------------------------- */
  var page = doc.querySelector('.post-page[data-autoplay]');
  function playOwn() {
    if (!page || (reduced && reduced.matches) || !window.SkriblInline) return;
    /* The post's own drawing alone: a comment's waits for a tap (phase 2). */
    var players = window.SkriblInline.mount(page.querySelector('.post-art') || page);
    if (players && players[0] && players[0].play) players[0].play();
  }
  /* OPENED AT A COMMENT (#c-<id>: a row in Activity, notifications), the
     comment decides (comments.js, window.SocialPlayOwn): a drawing answer
     draws itself and the post's own waits, since one plays at a time; any
     other comment, and the post's own plays here as always. */
  window.SocialPlayOwn = playOwn;
  if (!(/^#c-/.test(window.location.hash || '') && doc.querySelector('[data-comments]'))) playOwn();

  /* ---- the feed: Load more ------------------------------------------------ */
  var feed = doc.querySelector('[data-feed]');
  var more = doc.querySelector('[data-feed-next]');
  if (feed && more) {
    more.addEventListener('click', function () {
      var next = more.getAttribute('data-feed-next');
      if (!next) return;
      more.disabled = true;
      fetch(feed.getAttribute('data-more') + '?before=' + encodeURIComponent(next), { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
        .then(function (j) {
          var box = doc.createElement('div');
          box.innerHTML = j.html || '';
          var added = Array.prototype.slice.call(box.children);
          added.forEach(function (c) { feed.appendChild(c); });
          added.forEach(function (c) { when(c); });
          if (window.SkriblInline) window.SkriblInline.mount(feed);
          if (j.next) more.setAttribute('data-feed-next', j.next);
          else { more.setAttribute('data-feed-next', ''); more.hidden = true; }
          more.disabled = false;
        }, function () {
          more.disabled = false;
          tell(pageSay, say('network'));
        });
    });
  }

  /* ---- the composer ------------------------------------------------------- */
  var composer = doc.querySelector('[data-composer]');
  if (!composer) return;
  var words = composer.querySelector('[data-compose-words]');
  var left = composer.querySelector('[data-compose-left]');
  var draftWrap = composer.querySelector('[data-compose-draft]');
  var draftBox = draftWrap ? draftWrap.querySelector('.skribl-inline') : null;
  var chips = Array.prototype.slice.call(composer.querySelectorAll('[data-compose-open]'));
  var postBtn = composer.querySelector('[data-compose-post]');
  var sayBox = composer.querySelector('[data-compose-say]');
  var LIMIT = +(words && words.getAttribute('maxlength')) || 500;
  var draft = null;     // { payload, over }
  var sending = false;

  /* The words' box grows with what is typed, and says how many characters
     are left once there are few. */
  function grow() {
    words.style.height = 'auto';
    words.style.height = words.scrollHeight + 'px';
    var n = LIMIT - words.value.length;
    left.textContent = n <= 100 ? say('left', { n: n }) : '';
  }
  if (words) { words.addEventListener('input', grow); grow(); }

  var overs = {};
  chips.forEach(function (chip) {
    var kind = chip.getAttribute('data-compose-open');
    var wrap = doc.getElementById(kind === 'flip' ? 'composeFlip' : 'composePad');
    var over = window.SocialPadOverlay ? window.SocialPadOverlay(wrap, {
      openers: [chip],
      onDone: function (payload) { attach(payload, over); }
    }) : null;
    overs[kind] = over;
    chip.addEventListener('click', function () {
      if (!over || sending) return;
      tell(sayBox, '');
      over.open(chip);
    });
  });

  function attach(payload, over) {
    draft = { payload: payload, over: over };
    draftWrap.hidden = false;
    if (draftBox && window.SkriblInline) window.SkriblInline.attach(draftBox, payload);
    chips.forEach(function (c) { c.hidden = true; });
    tell(sayBox, '');
    var edit = composer.querySelector('[data-compose-edit]');
    if (edit) edit.focus({ preventScroll: true });
  }

  composer.querySelector('[data-compose-edit]').addEventListener('click', function (e) {
    if (draft && draft.over && !sending) draft.over.open(e.currentTarget);
  });
  composer.querySelector('[data-compose-remove]').addEventListener('click', function () {
    if (!draft || sending) return;
    if (draft.over) draft.over.pad.clear();
    draft = null;
    draftWrap.hidden = true;
    chips.forEach(function (c) { c.hidden = false; });
    if (chips[0]) chips[0].focus({ preventScroll: true });
  });

  postBtn.addEventListener('click', function () {
    if (sending) return;
    if (!draft) { tell(sayBox, say('no_drawing')); return; }
    sending = true;
    postBtn.disabled = true;
    tell(sayBox, say('posting'));
    post(composer.getAttribute('data-post-new'), { words: words.value, payload: draft.payload },
         { 'X-Social-CSRF': token })
      .then(function (j) {
        if (j.ok && j.go) { window.location.assign(j.go); return; }
        sending = false;
        postBtn.disabled = false;
        tell(sayBox, why(j));
      });
  });
})();
