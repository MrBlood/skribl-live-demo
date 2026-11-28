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
 * REPOSTS (the reposts mock, the owner's "All yes", Nov 14): the row's
 * repost raises its own small sheet (#repostSheet, the ⋯'s shape): Repost,
 * or Undo repost once it is yours, and Quote; a drawing shown outside a post
 * has Quote alone, and to its maker Post it first (the owner's A, Nov 24),
 * which opens the composer with it attached (compose.js post). Repost asks
 * nothing more: the sheet goes down, every
 * place on the page that shows the post lights its repost (the small violet
 * ink) and its count moves at once, as the heart's does, the count fading
 * and the button growing round the arrows, which keep their place; the site
 * is told (/p/<id>/repost, the page's token) and its count is what stays.
 * No toast: Undo is the sheet's own row. One request at a time a post, taps
 * made meanwhile where it ends up; one that did not take goes back and the
 * site's toast says why, kindly. QUOTE asks the site for the post, small
 * (/p/<id>/quoted), and opens the composer with it under the words
 * (compose.js, window.SocialComposer.quote). Signed out, the repost raises
 * a small sheet that says how ("Repost this post?"), and nothing is done.
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
    /* A COMMENT OR A REPLY IN ITS THREAD (the comment thread, step 3): its
       Repost and its Bookmark (comments.js has its ⋯), as a post's own. A
       comment's card out in the world is a card (data-kind c), below. */
    var cm = el.closest('.cm[data-comment], .cm-page[data-comment]');
    if (cm && !el.closest('.post-card')) {
      return { el: cm, id: cm.getAttribute('data-comment'), url: absolute(cm.getAttribute('data-url') || ''),
               skribl: '', mine: cm.hasAttribute('data-mine'), del: '', kind: 'c',
               handle: cm.getAttribute('data-handle') || '', first: cm.getAttribute('data-first') || '',
               muted: false, markable: cm.hasAttribute('data-markable'), marked: cm.hasAttribute('data-marked'),
               repost: cm.getAttribute('data-repost') || '', quoted: cm.getAttribute('data-quoted') || '' };
    }
    var p = el.closest('[data-post]') || doc.querySelector('.post-page[data-post]');
    if (!p) return null;
    return { el: p, id: p.getAttribute('data-post'), url: absolute(p.getAttribute('data-url')),
             skribl: p.getAttribute('data-skribl'), mine: p.hasAttribute('data-mine'),
             del: p.getAttribute('data-del'), kind: p.getAttribute('data-kind') || 'p',
             handle: p.getAttribute('data-handle') || '', first: p.getAttribute('data-first') || '',
             muted: p.hasAttribute('data-muted'), markable: p.hasAttribute('data-markable'),
             marked: p.hasAttribute('data-marked'), repost: p.getAttribute('data-repost') || '',
             quoted: p.getAttribute('data-quoted') || '',
             pinnable: p.hasAttribute('data-pinnable'), pinned: p.hasAttribute('data-pinned') };
  }
  /* What a thing is, wherever the page shows it: a comment by its address,
     a post or a drawing by its card's (a drawing's is b-<its id>). */
  function keyOf(p) { return (p.kind === 'c' ? 'c:' : 'p:') + p.id; }
  /* WHAT THE SHEETS CALL IT ([data-kind-word]): "This post", or for a
     comment (the comment thread, step 3) "This comment", and the rows and
     sheets that name it the same way. */
  function kindWords(p) {
    var k = p && p.kind === 'c' ? 'c' : 'p';
    Array.prototype.forEach.call(doc.querySelectorAll('[data-kind-word]'), function (el) {
      var w = say('kw_' + el.getAttribute('data-kind-word') + '_' + k);
      if (w) el.textContent = w;
    });
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

  /* HER SAY, WHO CAN DRAW BACK (the owner's "All yes to everything", Nov 20;
     _who.html): the card with Settings' pill, in the ⋯ of your own post that
     can be drawn back on (its card says what it is set to: data-who). */
  var whoCard = menuWrap ? menuWrap.querySelector('[data-who-card]') : null;
  var whoSw = whoCard ? whoCard.querySelector('[data-who-switch]') : null;
  var whoSay = whoCard ? whoCard.querySelector('[data-who-say]') : null;
  var SW = window.SocialSwitch;
  if (whoSw && SW) SW.watch(whoSw);
  function whoOf(p) { return p && p.mine && p.kind === 'p' ? p.el.getAttribute('data-who') : null; }
  function whoShow(by, first) {
    if (!whoSw || !SW) return;
    SW.press(whoSw, by, first);
    SW.says(whoSay, by);
  }

  doc.addEventListener('click', function (e) {
    /* The ⋯, or on your own post's page the quiet line's Change (who can
       draw back): the same sheet, and focus back on what was pressed. */
    var m = e.target.closest('[data-post-menu], [data-who-change]');
    if (m && menu) {
      e.preventDefault();
      current = postOf(m);
      if (!current) return;
      opener = m;
      kindWords(current);
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
      /* PIN THIS POST (pins.py): on your own post alone, Pin to your page,
         or Unpin from your page once it is the one. */
      var pn = menuWrap.querySelector('[data-act="pin"]');
      if (pn) {
        pn.hidden = !(current.pinnable && current.kind === 'p');
        pn.querySelector('[data-pin-words]').textContent = say(current.pinned ? 'pin_remove' : 'pin_add');
      }
      /* MUTE (mutes): Mute @them, or Unmute @them, as the card says. */
      var mu = menuWrap.querySelector('[data-act="mute"]');
      if (mu) {
        mu.setAttribute('data-muted', current.muted ? 'true' : 'false');
        mu.querySelector('[data-mute-name]').textContent = say(current.muted ? 'mu_unmute' : 'mu_mute', { handle: current.handle });
        mu.querySelector('[data-mute-say]').textContent = say(current.muted ? 'mu_say_un' : 'mu_say');
      }
      tell(menuWrap.querySelector('[data-post-say]'), '');
      var by = whoOf(current);
      if (whoCard) whoCard.hidden = !by || !SW;
      menu.open(m);
      /* Placed once the sheet is laid out (it is, from here on: it rises by
         a transform, which moves no box inside it). */
      if (by) whoShow(by, true);
      return;
    }
  });

  /* A TAP ON THE PILL IS THE CHANGE, as in Settings: nothing to confirm. The
     tint slides and the line under it says what the choice means at once;
     the site is told (/p/<id>/drawback-by), and if that fails the pill goes
     back to where it was and the sheet says why (a bookmark's own words for
     a failure, which say nothing of bookmarks). Every card of that post on
     the page takes the choice, and its page's quiet line follows
     (social:who, below). One request at a time: what is asked meanwhile is
     where it ends up. */
  var whoBusy = false, whoNext = null;
  function whoSet(p, want) {
    var was = whoOf(p);
    if (!was || want === was) return;
    if (whoBusy) { whoNext = want; whoShow(want, false); return; }
    whoBusy = true;
    whoShow(want, false);
    tell(menuWrap.querySelector('[data-post-say]'), '');
    post(whoCard.getAttribute('data-who-url').replace('__ID__', encodeURIComponent(p.id)), { by: want }, { 'X-Social-CSRF': token })
      .then(function (j) {
        whoBusy = false;
        var next = whoNext;
        whoNext = null;
        if (!j.ok) {
          if (current === p) { whoShow(was, false); tell(menuWrap.querySelector('[data-post-say]'), markWhy(j)); }
          return;
        }
        Array.prototype.forEach.call(doc.querySelectorAll('.post-card[data-post], .post-page[data-post]'), function (el) {
          if (el.getAttribute('data-post') !== p.id || !el.hasAttribute('data-who')) return;
          el.setAttribute('data-who', want);
          el.dispatchEvent(new CustomEvent('social:who', { bubbles: true, detail: { by: want } }));
        });
        if (next && next !== want) whoSet(p, next);
      });
  }
  /* ON HER OWN POST'S PAGE, the quiet line follows the pill: what it is set
     to while that is not Everyone, and nothing at Everyone. */
  doc.addEventListener('social:who', function (e) {
    var page = e.target && e.target.closest ? e.target.closest('.post-page') : null;
    var note = page ? page.querySelector('[data-db-who]') : null;
    if (!note) return;
    var by = e.detail && e.detail.by, w = note.querySelector('[data-db-who-words]');
    var text = w ? w.getAttribute('data-says-' + by) : '';
    if (w && text) w.textContent = text;
    note.hidden = !text;
  });

  if (menuWrap) {
    menuWrap.addEventListener('click', function (e) {
      var c = e.target.closest('[data-who-card] [data-choice]');
      if (c && current) { whoSet(current, c.getAttribute('data-choice')); return; }
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
      else if (act === 'pin' && menuWrap.hasAttribute('data-pin')) {
        /* Nothing asked first: the sheet goes down, focus back on the ⋯. */
        menu.close();
        pinAct(current, !current.pinned, opener, false);
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
      } else if (act === 'delete' && current.kind === 'c') {
        /* A COMMENT'S CARD (the comment thread, step 3): gone at once, as in
           its thread (comments.js), and the card folds away where it was. */
        var was = current;
        a.disabled = true;
        tell(box, say('deleting'));
        post(was.del, {}, { 'X-Social-CSRF': token }).then(function (j) {
          a.disabled = false;
          if (!j.ok) { tell(box, why(j)); return; }
          tell(box, '');
          menu.close(true);
          foldAway(was.el, say('deleted_c'));
        });
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
  var MARK_WAIT = 300, MENUS = '[data-post-menu], [data-cm-menu]';
  function markUrl(p) {
    var tpl = menuWrap.getAttribute(p.kind === 's' ? 'data-bookmark-s' : p.kind === 'c' ? 'data-bookmark-c' : 'data-bookmark-p') || '';
    return tpl.replace('__ID__', encodeURIComponent(p.kind === 's' ? p.skribl : p.id));
  }
  /* Every place on the page that shows it (its card, its own page; a
     comment in its thread too) says whether it is yours, so the next ⋯ says
     it. */
  function markShow(p, on) {
    var k = keyOf(p);
    Array.prototype.forEach.call(doc.querySelectorAll('.post-card[data-post], .post-page[data-post], .cm[data-comment], .cm-page[data-comment]'), function (el) {
      var o = postOf(el);
      if (!o || keyOf(o) !== k) return;
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
  function markSay(text, undo, wait, plain) {
    if (window.SocialToast) window.SocialToast.rise(text, plain ? { undo: undo || null, wait: wait, clear: MENUS, plain: true }
                                                              : { undo: undo || null, wait: wait, clear: MENUS, icon: 'mark' });
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

  /* PIN THIS POST (pins.py; the Pin mock's A, the owner's "all yes", Nov
     25): one of your own posts first on your page. A tap pins it (or takes
     it away), the sheet goes down, every place on the page that shows it
     says so at once (data-pinned: the next ⋯ says Unpin), and the post that
     was pinned before (`was`) is told it is not; the site's toast says what
     happened, with Undo, which puts back what was. One request at a time:
     a tap made while one is out is let go. A refusal puts it back, and the
     toast says why in a bookmark's words, which name no bookmark. */
  function pinShow(id, on) {
    Array.prototype.forEach.call(doc.querySelectorAll('.post-card[data-post], .post-page[data-post]'), function (el) {
      var o = postOf(el);
      if (!o || o.kind !== 'p' || o.id !== id) return;
      if (on) el.setAttribute('data-pinned', ''); else el.removeAttribute('data-pinned');
    });
  }
  var pinBusy = false;
  function pinAct(p, want, opener, undoing) {
    if (pinBusy) return;
    pinBusy = true;
    var t0 = Date.now();
    pinShow(p.id, want);
    post(menuWrap.getAttribute('data-pin').replace('__ID__', encodeURIComponent(p.id)), { pinned: want }, { 'X-Social-CSRF': token })
      .then(function (j) {
        pinBusy = false;
        var wait = Math.max(0, MARK_WAIT - (Date.now() - t0));
        if (!j.ok) {
          pinShow(p.id, !want);
          markSay(markWhy(j), null, wait);
          return;
        }
        var was = want && j.was ? j.was : null;
        if (was) pinShow(was, false);
        var text = say(want ? (was ? 'pin_moved' : 'pin_added') : 'pin_removed');
        markSay(text, undoing ? null : function () {
          if (opener && opener.isConnected) opener.focus({ preventScroll: true });
          /* Undo puts back what was: the other pin, or none, or this one. */
          if (was) pinAct({ kind: 'p', id: was }, true, opener, true);
          else pinAct(p, !want, opener, true);
        }, wait, true);
      });
  }

  /* A COMMENT'S ⋯ IN ITS THREAD (comments.js; the comment thread, step 3):
     its Bookmark is this one, the toast and Undo the post's. Signed out, the
     small sheet that says how. */
  window.SocialMark = {
    out: !!markOut,
    act: function (el, from) {
      var p = postOf(el);
      if (!p) return;
      kindWords(p);
      if (markOut) { markOut.open(from); return; }
      if (menuWrap && menuWrap.hasAttribute('data-bookmark-c')) markAct(p, !p.marked, from, false);
    }
  };

  /* ---- REPOSTS ------------------------------------------------------------- */
  var rpWrap = doc.getElementById('repostSheet');
  var rpSheet = rpWrap && window.SocialSheet ? window.SocialSheet(rpWrap, { doorCloses: false }) : null;
  var rpOutWrap = doc.getElementById('repostOutSheet');
  var rpOut = rpOutWrap && window.SocialSheet ? window.SocialSheet(rpOutWrap, {
    doorCloses: false, first: function () { return rpOutWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;
  var rpNow = null, rpFrom = null;
  var GLIDE = { duration: 220, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' };
  function still() { return !!(reduced && reduced.matches); }
  /* Every repost on the page for it (its cards, its own page's row; a
     comment's row in its thread, and on its own page). */
  function rpButtons(p) {
    var k = keyOf(p);
    return Array.prototype.filter.call(doc.querySelectorAll('.post-card[data-post] .post-row .rp-btn, .post-page[data-post] > .post-row .rp-btn, .cm-acts .rp-btn, .cm-page > .cm-row .rp-btn'),
      function (b) { var o = postOf(b); return !!o && keyOf(o) === k; });
  }
  /* WHAT MOVES, GLIDES (the heart's own, likes.js): a count that comes or
     goes fades, and the button grows or shrinks round the arrows, which keep
     their place, what follows it in the row moving along a frame at a time;
     under Reduce Motion it fades where it sits. */
  function rpGrow(b, change) {
    var w0 = b.getBoundingClientRect().width;
    if (b._grow) b._grow.cancel();
    change();
    var w1 = b.getBoundingClientRect().width;
    if (still() || !b.animate || Math.abs(w1 - w0) < 0.5) return;
    b.style.overflow = 'hidden';
    var a = b._grow = b.animate([{ width: w0 + 'px' }, { width: w1 + 'px' }], GLIDE);
    a.onfinish = a.oncancel = function () { if (b._grow === a) { b._grow = null; b.style.overflow = ''; } };
  }
  /* As likes.js's fade: its end hands `done` the fade itself, so one that
     puts away its own effect never puts away a fade begun since. */
  function rpFade(el, from, to, done) {
    if (!el.animate) { if (done) done(); return null; }
    var a = el.animate([{ opacity: from }, { opacity: to }], { duration: to ? 200 : 150, easing: 'ease', fill: 'forwards' });
    a.onfinish = function () { if (done) done(a); };
    return a;
  }
  function rpCount(b, n) {
    var span = b.querySelector('.rp-n');
    if (n > 0) {
      if (span) {
        span.textContent = String(n);
        if (span._going) {
          var was = parseFloat(getComputedStyle(span).opacity);
          span._going.cancel();
          span._going = null;
          rpFade(span, isFinite(was) ? was : 0, 1, function (a) { if (a) a.cancel(); });
        }
        return;
      }
      span = doc.createElement('span');
      span.className = 'rp-n';
      span.textContent = String(n);
      rpGrow(b, function () { b.appendChild(span); b.classList.remove('is-zero'); });
      rpFade(span, 0, 1, function (a) { if (a) a.cancel(); });
    } else if (span && !span._going) {
      span._going = rpFade(span, 1, 0, function () {
        if (!span._going) return;
        span._going = null;
        rpGrow(b, function () { span.remove(); b.classList.add('is-zero'); });
      });
      if (!span._going) { span.remove(); b.classList.add('is-zero'); }
    }
  }
  function rpShow(p, on, n) {
    rpButtons(p).forEach(function (b) {
      b.classList.toggle('is-on', on);
      rpCount(b, n);
      b.setAttribute('aria-label', say(on ? 'rp_reposted' : 'rp_repost')
        + (n > 0 ? ', ' + say(n === 1 ? 'rp_one' : 'rp_many', { n: n }) : ''));
    });
  }
  var rps = {};
  function rpState(p, b) {
    var st = rps[keyOf(p)];
    if (!st) {
      var span = b && b.querySelector('.rp-n'), on = !!b && b.classList.contains('is-on');
      var n = span ? parseInt(span.textContent, 10) || 0 : 0;
      st = rps[keyOf(p)] = { on: on, n: n, sure: on, sureN: n, busy: false, p: p };
    }
    return st;
  }
  function rpWhy(j) {
    if (j && j.error && WORDS['rp_' + j.error]) return say('rp_' + j.error);
    if (j && j.status === 429) return say('rp_limited');
    if (j && j.status === 401) return say('rp_signed_out');
    if (j && j.status === 403) return say('rp_stale');
    if (j && j.status === 404) return say('rp_gone');
    return say('rp_failed');
  }
  function rpSay(text) {
    if (window.SocialToast) window.SocialToast.rise(text, { plain: true, wait: 300, clear: '[data-repost-menu], ' + MENUS });
    else tell(pageSay, text);
  }
  function rpAct(p, want) {
    var st = rpState(p, rpButtons(p)[0]);
    if (st.on !== want) {
      st.on = want;
      st.n = Math.max(0, st.n + (want ? 1 : -1));
    }
    rpShow(p, st.on, st.n);
    rpSend(st);
  }
  function rpSend(st) {
    if (st.busy) return;           /* its answer sends again if a tap changed what they want */
    st.busy = true;
    var want = st.on;
    post(st.p.repost, { reposted: want }, { 'X-Social-CSRF': token }).then(function (j) {
      st.busy = false;
      if (j.ok) {
        st.sure = !!j.reposted;
        st.sureN = +j.n || 0;
        if (st.on !== want) { rpSend(st); return; }
        st.on = st.sure;
        st.n = st.sureN;
        rpShow(st.p, st.on, st.n);
        return;
      }
      st.on = st.sure;
      st.n = st.sureN;
      rpShow(st.p, st.on, st.n);
      rpSay(rpWhy(j));
    });
  }
  /* QUOTE: the post, small, from the site, then the composer with it under
     the words; the sheet goes down as it is asked for. */
  var quoting = false;
  function quote(p, from) {
    if (quoting || !p.quoted || !window.SocialComposer || !window.SocialComposer.quote) return;
    quoting = true;
    rpSheet.close(true);
    fetch(p.quoted, { credentials: 'same-origin' })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; }); },
            function () { return { error: 'network' }; })
      .then(function (j) {
        quoting = false;
        if (j && typeof j.html === 'string' && j.status === 200) {
          window.SocialComposer.quote({ kind: p.kind, id: p.kind === 's' ? p.skribl : p.id, html: j.html, from: from });
          return;
        }
        if (from && from.isConnected) from.focus({ preventScroll: true });
        rpSay(rpWhy(j));
      });
  }
  /* WHEN A REPLAY ENDS (Draw back, the mock's choice 2): where the row has
     Draw back's pen, "Watch again" and Draw back rise where the play button
     was, over the finished drawing: you have just watched it, so that is the
     moment to answer. They go as it plays again, by either. A glide up and a
     fade (social.css .db-end); under Reduce Motion a fade where they sit.
     ON A POST'S OWN PAGE THE INVITATION IS SAID ONCE (the Calm Post Page;
     the owner's "All yes to everything", Nov 20): the answer bar is there
     with Draw back in it (`lit`), so Watch again rises alone and the bar's
     Draw back lights up, the pill's own purple, until it plays again. */
  doc.addEventListener('skribl:ended', function (e) {
    var box = e.target, art = box && box.closest ? box.closest('.post-art') : null;
    var root = art && art.closest('[data-post], .post-page');
    var pen = root && root.querySelector('.post-row .db-pen');
    if (!art || !pen || box.querySelector('.db-end')) return;
    var lit = root.querySelector('.ans-bar .ans-draw');
    var end = doc.createElement('div');
    end.className = 'db-end';
    var again = doc.createElement('button');
    again.type = 'button';
    again.className = 'db-again';
    again.innerHTML = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false"><path d="M4 2.5l9 5.5-9 5.5z" fill="currentColor"/></svg>';
    again.appendChild(doc.createTextNode(say('db_again') || 'Watch again'));
    end.appendChild(again);
    if (lit) lit.classList.add('is-go');
    else {
      var go = doc.createElement('button');
      go.type = 'button';
      go.className = 'db-go';
      go.setAttribute('data-drawback', pen.getAttribute('data-drawback'));
      go.setAttribute('data-drawback-first', pen.getAttribute('data-drawback-first') || '');
      if (pen.hasAttribute('data-drawback-own')) go.setAttribute('data-drawback-own', '');
      go.innerHTML = (pen.querySelector('svg') || { outerHTML: '' }).outerHTML;
      go.appendChild(doc.createTextNode(say('db_go') || 'Draw back'));
      end.appendChild(go);
      /* Its own click, so the box's tap (play or pause) never takes it first. */
      go.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        away();
        if (window.SocialComposer && window.SocialComposer.drawBack) {
          window.SocialComposer.drawBack({ id: go.getAttribute('data-drawback'), first: go.getAttribute('data-drawback-first'),
                                           own: go.hasAttribute('data-drawback-own'), from: pen });
        }
      });
    }
    /* In the drawing's own box, at its foot; the box's own replay button
       steps aside while they are up (they say it in words). */
    box.appendChild(end);
    /* The box can run taller than the drawing (room for its line): the pills
       stand 12px above the drawing's own foot, measured. */
    var cv = box.querySelector('canvas, img'), br = box.getBoundingClientRect(), cr = cv ? cv.getBoundingClientRect() : br;
    end.style.bottom = Math.max(12, br.bottom - cr.bottom + 12) + 'px';
    box.classList.add('db-ended');
    void end.offsetHeight;
    end.classList.add('is-up');
    function away() {
      if (!end.parentNode) return;
      watch.disconnect();
      end.remove();
      box.classList.remove('db-ended');
      if (lit) lit.classList.remove('is-go');
    }
    again.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      away();
      var p = box._skriblInline;
      if (p && p.play) p.play();
    });
    var watch = new MutationObserver(function () { if (box.classList.contains('is-playing')) away(); });
    watch.observe(box, { attributes: true, attributeFilter: ['class'] });
  });

  /* HER SAY, ON HER OWN STRIP (the owner's "All yes to everything", Nov 20):
     as an eye hides a draw-back from her post or brings it back (eye.js says
     so on its cell), the page's own counts follow at once: the label is what
     everyone else sees ("2 draw-backs"; none at none), the quiet line under
     it how many are hidden, hers alone ("1 hidden from your post"), and the
     row's pen one fewer or one more, with its name. ONE FEWER OR ONE MORE,
     FROM WHAT THEY SAID (Nov 27): the counts are every draw-back's (the
     page says them), and the strip holds twelve, SEE ALL's page a page at
     a time, so the tiles on the page are not all there are to count. The
     page of every draw-back is a strip to this too ([data-db-strip]). */
  doc.addEventListener('social:eye', function (e) {
    var cell = e.target, strip = cell && cell.closest ? cell.closest('[data-db-strip]') : null;
    if (!strip) return;
    var off = !!(e.detail && e.detail.hidden), h = strip.querySelector('[data-db-hidden]');
    var label = strip.querySelector('.db-title'), n = strip.querySelector('[data-db-n]'), noun = strip.querySelector('[data-db-noun]');
    var shown = Math.max(0, (n ? +n.textContent || 0 : 0) + (off ? -1 : 1));
    var hidden = Math.max(0, (h ? +h.textContent || 0 : 0) + (off ? 1 : -1));
    if (n) n.textContent = String(shown);
    if (noun) noun.textContent = noun.getAttribute(shown === 1 ? 'data-one' : 'data-many');
    if (label) label.hidden = !shown;
    var note = strip.querySelector('[data-db-note]');
    if (h) h.textContent = String(hidden);
    if (note) note.hidden = !hidden;
    var page = strip.closest('.post-page'), pen = page ? page.querySelector(':scope > .post-row .db-pen') : null;
    if (!pen) return;
    var c = pen.querySelector('span'), now = Math.max(0, (c ? +c.textContent || 0 : 0) + (e.detail && e.detail.hidden ? -1 : 1));
    if (!c && now) { c = doc.createElement('span'); pen.appendChild(c); }
    if (c) { if (now) c.textContent = String(now); else pen.removeChild(c); }
    pen.setAttribute('aria-label', (say('db_go') || 'Draw back')
      + (now ? ', ' + now + ' ' + (now === 1 ? say('db_one') || 'draw-back' : say('db_many') || 'draw-backs') : ''));
  });

  /* SEE ALL'S LOAD MORE (the page of every draw-back on a post; the owner's
     C, Nov 27): the next page of tiles after the last, fading in (social.css,
     .db-grid > .is-new), and the button gone once there are no more. One
     that did not come leaves the button to try again, and the page says so. */
  doc.addEventListener('click', function (e) {
    var more = e.target.closest ? e.target.closest('[data-db-more]') : null;
    var grid = doc.querySelector('[data-db-grid]'), next = more ? more.getAttribute('data-db-next') : '';
    if (!more || !grid || !next || more.disabled) return;
    more.disabled = true;
    fetch(more.getAttribute('data-db-more') + '?before=' + encodeURIComponent(next), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (j) {
        var box = doc.createElement('div');
        box.innerHTML = j.html || '';
        Array.prototype.slice.call(box.children).forEach(function (t) {
          if (!(reduced && reduced.matches)) t.classList.add('is-new');
          grid.appendChild(t);
        });
        more.setAttribute('data-db-next', j.next || '');
        more.hidden = !j.next;
        more.disabled = false;
      }, function () {
        more.disabled = false;
        tell(pageSay, say('network'));
      });
  });

  /* DRAW BACK (the owner's "All yes", Nov 19): the row's pen opens the
     composer, and the Pad over it with the drawing faint under the pen
     (compose.js drawBack). */
  doc.addEventListener('click', function (e) {
    var d = e.target.closest('[data-drawback]');
    if (!d || !window.SocialComposer || !window.SocialComposer.drawBack) return;
    e.preventDefault();
    window.SocialComposer.drawBack({ id: d.getAttribute('data-drawback'), first: d.getAttribute('data-drawback-first'),
                                     own: d.hasAttribute('data-drawback-own'), from: d });
  });
  doc.addEventListener('click', function (e) {
    var b = e.target.closest('[data-repost-menu]');
    if (b && rpSheet) {
      e.preventDefault();
      var p = postOf(b);
      if (!p) return;
      rpNow = p;
      rpFrom = b;
      var st = rpState(p, b), row = rpWrap.querySelector('[data-rp="repost"]');
      /* A drawing shown outside a post: Quote alone (only its maker posts it),
         and to its maker Post it where Repost would be (the owner's A, Nov
         24): the composer, it attached, for their own words. */
      row.hidden = !p.repost;
      var postRow = rpWrap.querySelector('[data-rp="post"]');
      if (postRow) postRow.hidden = !(!p.repost && p.kind === 's' && p.mine && p.skribl
                                       && window.SocialComposer && window.SocialComposer.post);
      row.querySelector('[data-rp-name]').textContent = say(st.on ? 'rp_undo' : 'rp_do');
      row.querySelector('[data-rp-say]').textContent = say(st.on ? 'rp_undo_say' : 'rp_do_say');
      rpWrap.querySelector('[data-rp="quote"]').hidden = !p.quoted;
      rpSheet.open(b);
      return;
    }
    var o = e.target.closest('[data-repost-out]');
    if (o && rpOut) {
      e.preventDefault();
      kindWords(postOf(o));
      rpOut.open(o);
    }
  });
  if (rpWrap) {
    rpWrap.addEventListener('click', function (e) {
      var a = e.target.closest('[data-rp]');
      if (!a || !rpNow) return;
      if (a.getAttribute('data-rp') === 'repost') {
        /* Nothing asked first: the sheet goes down, focus back on the repost. */
        rpSheet.close();
        rpAct(rpNow, !rpState(rpNow).on);
      } else if (a.getAttribute('data-rp') === 'post') {
        /* The sheet goes down and the composer comes up with the drawing in
           it; closed unposted, focus goes back to the repost. */
        rpSheet.close();
        window.SocialComposer.post({ id: rpNow.skribl, from: rpFrom });
      } else {
        quote(rpNow, rpFrom);
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
      /* A drawing shown outside a post is reported as itself, and a
         comment's card as the comment (the comment thread, step 3). */
      var drawing = current.kind === 's';
      post(reportWrap.getAttribute('data-report'),
           { kind: drawing ? 'drawing' : current.kind === 'c' ? 'comment' : 'post', target: drawing ? current.skribl : current.id,
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
  function foldAway(card, words) {
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
      if (window.SocialToast) window.SocialToast.rise(words || say('deleted'), { plain: true, clear: '[data-prof-list] .post-card [data-post-menu]' });
      else tell(pageSay, words || say('deleted'));
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
     face, the name and the @handle open the person's page; ⋯ and the repost
     do their own job; the 💬 opens the comments; any other control its own. A
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
    /* Not under the Blooby app's splash (splash.js): it plays as that goes. */
    var after = window.BloobySplash ? window.BloobySplash.after : function (fn) { fn(); };
    if (players && players[0] && players[0].play) after(function () { players[0].play(); });
  }
  /* OPENED AT A COMMENT (#c-<id>: a row in Activity, notifications), the
     comment decides (comments.js, window.SocialPlayOwn): a drawing answer
     draws itself and the post's own waits, since one plays at a time; any
     other comment, and the post's own plays here as always. */
  window.SocialPlayOwn = playOwn;
  if (!(/^#c-/.test(window.location.hash || '') && doc.querySelector('[data-comments]'))) playOwn();

  /* ---- DRAW BACK, TWO HANDS: what you watch (the owner's "all yes", Nov
     25, to the Two Hands mock: "It changes only what you watch, never the
     drawing") ------------------------------------------------------------
     On a two-hands draw-back's own page, the one pill under the drawing:
     Both, hers alone, his alone, each its own player (post.html). A choice
     glides the pill's tint, puts away the view that was, and fades the
     chosen one in where it stood, the same shape; if the one put away was
     playing, the chosen one plays from its start. */
  doc.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('.hands-seg > button[data-hands]') : null;
    var box = b ? b.closest('[data-hands-box]') : null;
    if (!box || b.getAttribute('aria-pressed') === 'true') return;
    var want = b.getAttribute('data-hands');
    var was = box.querySelector('[data-hands-view]:not([hidden])');
    var now = box.querySelector('[data-hands-view="' + want + '"]');
    if (!now || now === was) return;
    var Inline = window.SkriblInline;
    var before = was && Inline ? Inline.mount(was)[0] : null;
    var playing = !!(before && before.state && before.state().state === 'playing');
    Array.prototype.forEach.call(b.parentNode.querySelectorAll('button[data-hands]'), function (o) {
      o.setAttribute('aria-pressed', o === b ? 'true' : 'false');
    });
    if (window.SocialPill) window.SocialPill.choose(b.parentNode, b);
    if (before && before.pause) before.pause();
    if (was) was.hidden = true;
    now.classList.remove('is-in');
    now.hidden = false;
    void now.offsetWidth;
    now.classList.add('is-in');
    var after = Inline ? Inline.mount(now)[0] : null;
    if (playing && after && after.play) after.play();
  });

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
