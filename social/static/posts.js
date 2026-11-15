/* Posts (piece 4): Home's feed (feed.html), a post's own page (post.html),
 * and the ⋯ sheet both share (social/_post.html). The composer that was
 * Home's is compose.js's since Nov 14, on every page (one Make).
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
 * THE ⋯ SHEET (social.js's SocialSheet, as Make's): Bookmark first (Remove
 * bookmark once it is yours: the card says which; none on what is taken
 * down), Copy link, Share…,
 * signed in Mute @them (Unmute @them once muted: the card says which), Report
 * this post and, signed in, Block @them; or on your own Delete post. Report
 * and Delete each rise as a sheet of their own: Report into the site's own
 * queue (/report, the page's token, the Gallery's reasons and "A child's
 * safety"; piece 5), Delete asked once (then, on your own page, the post
 * folds away there and the site's toast says it is gone; anywhere else Home
 * says it went). Block is safety.js's sheet
 * (window.SocialSafety), and afterwards Home says so. Mute asks nothing:
 * mutes.js (window.SocialMute) folds their cards away and offers Undo.
 *
 * BOOKMARK asks nothing either (the bookmarks mock's A, the owner's "All
 * yes", Nov 14): a tap keeps the post for you (or takes it away), the sheet
 * goes down, every place on the page that shows it says so at once (its
 * data-marked: the next ⋯ says Remove bookmark), the site is told
 * (/p/<id>/bookmark, /b/<id>/bookmark, the page's token), and the site's
 * toast says "Bookmarked. It’s on your page, under Bookmarks." (or "Removed
 * from your bookmarks.") beside the ribbon, with Undo, clear of every ⋯ on
 * the page, the next press (mutes.js, window.SocialToast). Undo puts it back
 * as it was and says so, with no Undo of its own, the focus back on the ⋯.
 * One request at a time a post; taps made meanwhile are where it ends up. A
 * refusal puts it back and the toast says why, kindly. Signed out, the row
 * raises a small sheet that says how ("Bookmark this post?", the heart's
 * own), and nothing is kept. Nobody is told, and nothing counts them.
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
  /* Every word on the page (the ⋯ reads Block's and Mute's), then the
     posts' own over them ([data-post-words]): a profile holds your face's
     words too, some by the same names ("failed", "stale"), and each file
     says its own. */
  ['[data-word]', '[data-post-words] [data-word]'].forEach(function (sel) {
    Array.prototype.forEach.call(doc.querySelectorAll(sel), function (w) {
      WORDS[w.getAttribute('data-word')] = w.textContent;
    });
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
             handle: p.getAttribute('data-handle') || '', first: p.getAttribute('data-first') || '',
             muted: p.hasAttribute('data-muted'), markable: p.hasAttribute('data-markable'),
             marked: p.hasAttribute('data-marked') };
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
      /* BOOKMARK (bookmarks): Bookmark, or Remove bookmark with its ribbon
         filled, as the card says; none on what is taken down. */
      var bm = menuWrap.querySelector('[data-act="bookmark"]');
      if (bm) {
        bm.hidden = !current.markable;
        bm.classList.toggle('is-marked', current.marked);
        bm.querySelector('[data-bm-words]').textContent = say(current.marked ? 'bm_remove' : 'bm_add');
      }
      /* MUTE (mutes): Mute @them, or Unmute @them, as the card says. */
      var mu = menuWrap.querySelector('[data-act="mute"]');
      if (mu) {
        mu.setAttribute('data-muted', current.muted ? 'true' : 'false');
        mu.querySelector('[data-mute-name]').textContent = say(current.muted ? 'mu_unmute' : 'mu_mute', { handle: current.handle });
        mu.querySelector('[data-mute-say]').textContent = say(current.muted ? 'mu_say_un' : 'mu_say');
      }
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
      else if (act === 'bookmark') {
        if (markOut) {
          /* Signed out: the small sheet that says how. */
          menu.close(true);
          markOut.open(opener);
        } else if (menuWrap.hasAttribute('data-bookmark-p')) {
          /* Nothing asked first: the sheet goes down, focus back on the ⋯. */
          menu.close();
          markAct(current, !current.marked, opener, false);
        }
      }
      else if (act === 'report' && report) {
        menu.close(true);
        resetReport();
        report.open(opener);
      } else if (act === 'block' && window.SocialSafety) {
        menu.close(true);
        window.SocialSafety.block(current.handle, opener);
      } else if (act === 'mute' && window.SocialMute) {
        /* Nothing asked first: the sheet goes down, focus back on the ⋯. */
        menu.close();
        window.SocialMute.act({ handle: current.handle, first: current.first, muted: current.muted, opener: opener });
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

  /* ---- BOOKMARKS ----------------------------------------------------------- */
  var markOutWrap = doc.getElementById('bookmarkOutSheet');
  var markOut = markOutWrap && window.SocialSheet ? window.SocialSheet(markOutWrap, {
    doorCloses: false, first: function () { return markOutWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;
  /* The toast waits for the sheet to go (0.3s from the tap, as Mute's), and
     keeps clear of every ⋯ on the page: the next press. */
  var MARK_WAIT = 300, MENUS = '[data-post-menu]';
  function markUrl(p) {
    var tpl = menuWrap.getAttribute(p.kind === 's' ? 'data-bookmark-s' : 'data-bookmark-p') || '';
    return tpl.replace('__ID__', encodeURIComponent(p.kind === 's' ? p.skribl : p.id));
  }
  /* Every place on the page that shows the post (its card, its own page)
     says whether it is yours, so the next ⋯ says it. */
  function markShow(p, on) {
    Array.prototype.forEach.call(doc.querySelectorAll('.post-card[data-post], .post-page[data-post]'), function (el) {
      if (el.getAttribute('data-post') !== p.id) return;
      if (on) el.setAttribute('data-marked', ''); else el.removeAttribute('data-marked');
    });
  }
  function markWhy(j) {
    if (j && j.error && WORDS['bm_' + j.error]) return say('bm_' + j.error);
    if (j && j.status === 429) return say('bm_limited');
    if (j && j.status === 401) return say('bm_signed_out');
    if (j && j.status === 403) return say('bm_stale');
    if (j && j.status === 404) return say('bm_gone');
    return say('bm_failed');
  }
  function markSay(text, undo, wait) {
    if (window.SocialToast) window.SocialToast.rise(text, { undo: undo || null, wait: wait, clear: MENUS, icon: 'mark' });
    else tell(pageSay, text);
  }
  /* `want`: kept (true) or taken away. One request at a time a post: what is
     asked meanwhile is where it ends up. `undoing`: an Undo, which says what
     happened with no Undo of its own and gives the ⋯ its focus back. */
  var marks = {};
  function markAct(p, want, opener, undoing) {
    var key = p.kind + ':' + p.id, st = marks[key] || (marks[key] = { busy: false });
    st.want = want;
    st.p = p;
    st.opener = opener;
    st.undoing = !!undoing;
    markShow(p, want);
    if (!st.busy) markSend(st, Date.now());
  }
  function markSend(st, t0) {
    var want = st.want, p = st.p;
    st.busy = true;
    post(markUrl(p), { bookmarked: want }, { 'X-Social-CSRF': token }).then(function (j) {
      st.busy = false;
      if (j.ok && st.want !== want) { markSend(st, t0); return; }
      var wait = Math.max(0, MARK_WAIT - (Date.now() - t0));
      if (j.ok) {
        markSay(say(want ? 'bm_added' : 'bm_removed'), st.undoing ? null : function () {
          if (st.opener && st.opener.isConnected) st.opener.focus({ preventScroll: true });
          markAct(p, !want, st.opener, true);
        }, wait);
        return;
      }
      st.want = !want;
      markShow(p, !want);
      markSay(markWhy(j), null, wait);
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

  /* DELETED FROM YOUR OWN PAGE (a profile's card: the owner's "Yes", Nov 14)
     you stay there, and the post folds away where it was: it fades, then its
     room closes and the next rises into its place, as a muted person's cards
     fold on Home (mutes.js); under Reduce Motion it fades, and its room goes
     once it can't be seen. Focus goes to the next card's ⋯ (else the one
     before, else the tab), and the last one gone leaves the tab's own kind
     words. Once it has folded away THE SITE'S TOAST says so, near the finger,
     in Home's own words (the owner's "Yes", Nov 14: it said so on the tab's
     status line at the foot of the tab), a status a screen reader hears; no
     Undo, a delete is final, and clear of the cards' ⋯, the next delete's
     first press (mutes.js, window.SocialToast). From a post's own page, and
     Home, the site's answer leads on: Home, its note. */
  var FOLD_EASE = 'cubic-bezier(0.4, 0, 0.2, 1)';
  function foldAway(card) {
    var list = card.parentElement, panel = card.closest('[data-prof-panel]');
    var cards = Array.prototype.slice.call(list.querySelectorAll(':scope > .post-card'));
    var at = cards.indexOf(card), next = cards[at + 1] || cards[at - 1] || null;
    var to = next ? next.querySelector('.post-more') : doc.querySelector('.prof-tab[aria-current="page"]');
    if (to) to.focus({ preventScroll: true });
    tell(pageSay, '');
    var gap = parseFloat(getComputedStyle(list).rowGap) || 0, still = !!(reduced && reduced.matches);
    function gone() {
      card.remove();
      var none = panel && panel.querySelector('[data-prof-none]');
      if (none && !list.querySelector('.post-card') && none.hidden) {
        none.hidden = false;
        if (none.animate) none.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease' });
      }
      if (window.SocialToast) window.SocialToast.rise(say('deleted'), { plain: true, clear: '[data-prof-list] .post-card [data-post-menu]' });
      else tell(pageSay, say('deleted'));
    }
    if (!card.animate) { gone(); return; }
    card.style.pointerEvents = 'none';
    var out = card.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200, easing: 'ease', fill: 'forwards' });
    out.onfinish = function () {
      /* Unseen it stays, whatever moving it into its room does to its fade. */
      card.style.opacity = '0';
      if (still) { gone(); return; }
      /* Its room, a box of no padding of its own, closes: the card's own
         padding would hold it open. */
      var room = doc.createElement('div'), h = card.getBoundingClientRect().height;
      room.style.overflow = 'hidden';
      list.insertBefore(room, card);
      room.appendChild(card);
      var shut = room.animate([{ height: h + 'px', marginBottom: '0px' }, { height: '0px', marginBottom: -gap + 'px' }],
                              { duration: 340, easing: FOLD_EASE, fill: 'forwards' });
      shut.onfinish = function () { room.remove(); gone(); };
    };
  }

  if (deleteWrap) {
    deleteWrap.querySelector('[data-delete-now]').addEventListener('click', function (e) {
      if (!current) return;
      var b = e.currentTarget, box = deleteWrap.querySelector('[data-delete-say]'), was = current;
      b.disabled = true;
      tell(box, say('deleting'));
      post(current.del || deleteWrap.getAttribute('data-delete').replace('__ID__', encodeURIComponent(current.id)), {},
           { 'X-Social-CSRF': token })
        .then(function (j) {
          var card = was.el;
          if (j.ok && card && card.classList.contains('post-card') && card.closest('[data-profile]')) {
            del.close(true);
            b.disabled = false;
            tell(box, '');
            foldAway(card);
            return;
          }
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
     middle button, the post opens in a new tab, as a link's would.
     THE LINE UNDER THE DRAWING IS THE CARD'S TOO (Nov 13, from the owner's
     "I thought on card?"): "Drawn in 16 sec · watching at" and the space
     around the drawing open the post; the speed and its choices (a group),
     the heart, the scrubber and the loop keep theirs. The player and its
     line keep their clicks from bubbling (docs/INTEGRATION.md, the lead: a
     host's whole-post link must not open on a scrub or a speed), so a click
     in the drawing's part of the card (.post-art, the site's own) is heard
     here on the way down, and only there. */
  var OWN = 'a, button, input, textarea, select, label, summary, [role="button"], [role="slider"], [role="group"], [tabindex]';
  var ART = '.post-art';
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
  function openCard(e) {
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
  }
  function inArt(e) { return !!(e.target && e.target.closest && e.target.closest(ART)); }
  doc.addEventListener('click', function (e) { if (inArt(e)) openCard(e); }, true);
  doc.addEventListener('click', function (e) { if (!inArt(e)) openCard(e); });
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

})();
