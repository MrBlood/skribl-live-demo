/* Follows (phase 2; the follow mock and the owner's "Yes to all", B, Nov
 * 13): Follow on a person's page, your own page's lists, and Home's pill
 * (social/_follow.html). follows.py says the rules.
 *
 * FOLLOW, THEN FOLLOWING. A tap on Follow changes the button at once (the
 * purple fades to the quiet button, the words cross over in their one place,
 * the check draws itself in our pen) and tells the site (/@<handle>/follow,
 * {following: true}, the page's token in X-Social-CSRF); one that did not
 * take goes back, and the page says why, kindly. A tap on Following raises
 * "Unfollow Theo?" (social.js's SocialSheet, Make's own): Unfollow fades the
 * button back to Follow and tells the site; Keep following keeps it. Nobody
 * is told either way. SIGNED OUT, Follow raises the small sheet that says
 * how; Sign in comes back to the same page, and nothing is pressed for them.
 * EVERY FOLLOW ON A PAGE works so, each its own (a person's page has one;
 * the Gallery's People, finding people, one a row, rows that a search or
 * Load more brings later too), and one sheet serves them all, saying the
 * name of the one tapped.
 *
 * THE COUNTS FOLLOW THE TAP (the quick-patterns mock's A): the site's answer
 * to a follow brings the page's counts as it now shows them to you ("New
 * here" becomes "1 follower"); they fade out, change while they can't be
 * seen, and fade back (social.css, .fo-counts.is-out), so nothing beside
 * them jumps as the words change width.
 *
 * YOUR OWN PAGE: each count opens who follows you and whom you follow, on its
 * own list, the one pill between them; opened at #followers or #following
 * (a follow row in Activity), the sheet rises on that list.
 *
 * HOME'S PILL, Following | Everyone: a tap glides the pill to it, keeps the
 * pick for the account (/home/show), fades the posts out, puts the other
 * tab's first page in while they can't be seen (/feed?show=), and fades them
 * back; the page doesn't scroll. Load more then carries on from that page
 * (posts.js: its cursor says which).
 *
 * THE GALLERY'S PILLS (Following | Everyone and New | Hot) are the one pill
 * too, and so is the composer's Drafts | Drawings (compose.js): the tint is
 * placed and glided by social.js (window.SocialPill, on every page since the
 * composer is), and explore.js presses the Gallery's through it and says
 * what they show.
 *
 * KIND, NEVER JUMPY: nothing moves but the pill's tint, which glides; the
 * rest fades or draws (social.css, "FOLLOWING"). Under Reduce Motion the
 * tint is put there and the rest only fades.
 *
 * The words are the page's ([data-follow-words]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-follow-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key, vars) {
    var s = WORDS[key] || '';
    Object.keys(vars || {}).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';

  function post(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
                        body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!j || typeof j !== 'object') j = {};
          j.status = r.status;
          return j;
        });
      }, function () { return { error: 'network' }; });
  }
  function why(j) {
    if (j && j.error && WORDS['fo_' + j.error]) return say('fo_' + j.error);
    if (j && j.status === 429) return say('fo_limited');
    if (j && j.status === 401) return say('fo_signed_out');
    if (j && j.status === 403) return say('fo_stale');
    if (j && j.status === 404) return say('fo_gone');
    return say('fo_failed');
  }

  /* ---- the one pill: the tint under the chosen option ----------------------- */
  /* social.js's (window.SocialPill), the site's every page's since the
     composer's picker carries one on all of them: placed, glided, watched. */
  var choose = window.SocialPill.choose, place = window.SocialPill.place;

  /* ---- Follow, then Following ------------------------------------------------ */
  /* EVERY FOLLOW ON THE PAGE (a person's page has one; the Gallery's People,
     finding people, one a row, rows that come later with a search or Load
     more too): each keeps its own state, and a tap reaches it wherever it
     sits (one listener, on the page). ONE SHEET FOR THEM ALL: "Unfollow
     Theo?" says the name of the button that raised it ([data-fo-first]),
     and is that button's alone while it is up. */
  function tell(text) {
    var said = doc.querySelector('[data-say]');
    if (!said) return;
    said.textContent = text || '';
    said.hidden = !text;
  }
  var heard = doc.querySelector('[data-follow-said]');
  var counts = doc.querySelector('[data-follow-counts]');
  var pending = null, fading = false;
  /* The page's counts again, from the site's answer (follows.py: its own
     markup, counted for you): out, changed while unseen, and back. One fade
     at a time; it puts in the latest answer. */
  function recount(html) {
    if (!counts || typeof html !== 'string') return;
    var t = doc.createElement('template');
    t.innerHTML = html;
    var next = t.content.querySelector('[data-follow-counts]');
    if (!next) return;
    pending = next.innerHTML;
    if (fading) return;
    if (pending === counts.innerHTML) { pending = null; return; }
    fading = true;
    var timer = 0;
    var gone = function (e) {
      if (e && (e.target !== counts || e.propertyName !== 'opacity')) return;
      counts.removeEventListener('transitionend', gone);
      clearTimeout(timer);
      if (pending !== null) counts.innerHTML = pending;
      pending = null;
      requestAnimationFrame(function () { counts.classList.remove('is-out'); fading = false; });
    };
    counts.addEventListener('transitionend', gone);
    timer = setTimeout(gone, 260);
    counts.classList.add('is-out');
  }
  /* YOUR OWN PAGE'S COUNTS, after a follow or an unfollow from a row of your
     follows sheet (the owner's "A", Nov 15): the site's answer carries them
     (j.mine, your lists' lengths), and the numbers change in place while the
     counts are out, the same fade, so the buttons that open the lists stay
     the ones they are. A following count only while it isn't zero, as the
     page draws it. Somebody else's counts never land on yours. */
  var ownPage = !!(counts && counts.querySelector('[data-follows-open]'));
  function ownRecount(n) {
    if (!counts || !n) return;
    var cells = {}, changed = false;
    ['followers', 'following'].forEach(function (k) {
      var b = counts.querySelector('[data-follows-open="' + k + '"] b');
      if (b) { cells[k] = b; if (b.textContent !== String(n[k])) changed = true; }
    });
    if (!changed || fading) return;
    fading = true;
    var timer = 0;
    var gone = function (e) {
      if (e && (e.target !== counts || e.propertyName !== 'opacity')) return;
      counts.removeEventListener('transitionend', gone);
      clearTimeout(timer);
      Object.keys(cells).forEach(function (k) { cells[k].textContent = String(n[k]); });
      var fol = counts.querySelector('[data-follows-open="following"]'), dot = counts.querySelector('.fo-dot');
      if (fol) fol.hidden = !n.following;
      if (dot) dot.hidden = !n.following;
      requestAnimationFrame(function () { counts.classList.remove('is-out'); fading = false; });
    };
    counts.addEventListener('transitionend', gone);
    timer = setTimeout(gone, 260);
    counts.classList.add('is-out');
  }
  /* The name of the person a sheet is about, from the button that raised it;
     and Sign in coming back to this page as its address is now (the
     Gallery's search changes its address as it goes). */
  function about(wrap, b) {
    var first = b.getAttribute('data-first') || '';
    Array.prototype.forEach.call(wrap.querySelectorAll('[data-fo-first]'), function (s) { s.textContent = first; });
    var signin = wrap.querySelector('[data-fo-signin]');
    if (signin) signin.href = signin.getAttribute('data-fo-signin') + '?next=' +
      encodeURIComponent(window.location.pathname + window.location.search);
  }
  var unWrap = doc.getElementById('unfollowSheet');
  var unFrom = [];           /* the button the sheet is up for, alone */
  var un = unWrap && window.SocialSheet ? window.SocialSheet(unWrap, {
    openers: unFrom, doorCloses: false,
    first: function () { return unWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;
  /* Each button's own: following as the page shows it, as the site last
     said, and whether its answer is on the way. */
  function state(btn) {
    if (!btn._fo) {
      var on = btn.classList.contains('is-following');
      btn._fo = { on: on, sure: on, busy: false };
    }
    return btn._fo;
  }
  /* What the button shows: following or not (a change fades, and following
     draws the check: .fo-anim; unfollowing fades it, nothing un-drawing:
     .fo-fade), its name, and whether a tap raises a sheet. */
  function show(btn, on, moving) {
    var name = btn.getAttribute('data-name') || '';
    if (btn.classList.contains('is-following') !== on) {
      btn.classList.remove('fo-anim', 'fo-fade');
      if (moving) btn.classList.add(on ? 'fo-anim' : 'fo-fade');
      btn.classList.toggle('is-following', on);
    }
    btn.setAttribute('aria-label', say(on ? 'fo_following' : 'fo_follow', { name: name }));
    if (on) {
      btn.setAttribute('aria-haspopup', 'dialog');
      btn.setAttribute('aria-controls', 'unfollowSheet');
      if (!btn.hasAttribute('aria-expanded')) btn.setAttribute('aria-expanded', 'false');
    } else {
      btn.removeAttribute('aria-haspopup');
      btn.removeAttribute('aria-controls');
      btn.removeAttribute('aria-expanded');
    }
  }
  function send(btn) {
    var st = state(btn);
    if (st.busy) return;      /* its answer sends again if a tap changed what they want */
    st.busy = true;
    var want = st.on;
    post(btn.getAttribute('data-follow'), { following: want }).then(function (j) {
      st.busy = false;
      if (j.ok) {
        st.sure = !!j.following;
        if (st.on !== want) { send(btn); return; }
        if (st.on !== st.sure) { st.on = st.sure; show(btn, st.on, true); }
        if (ownPage) ownRecount(j.mine); else recount(j.counts);
        if (heard) heard.textContent = st.sure ? say('fo_now_following', { name: btn.getAttribute('data-name') || '' }) : '';
        return;
      }
      st.on = st.sure;
      show(btn, st.on, true);
      tell(why(j));
    });
  }
  doc.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-follow]');
    if (!btn) return;
    e.preventDefault();
    var st = state(btn);
    if (st.on) {
      if (un) {
        about(unWrap, btn);
        unFrom.length = 0;
        unFrom.push(btn);
        un.open(btn);
      }
      return;
    }
    st.on = true;
    tell('');
    show(btn, true, true);
    send(btn);
  });
  var go = unWrap && unWrap.querySelector('[data-unfollow]');
  if (go) {
    go.addEventListener('click', function () {
      var btn = unFrom[0];
      if (un) un.close();
      if (!btn) return;
      var st = state(btn);
      if (!st.on) return;
      st.on = false;
      tell('');
      show(btn, false, true);
      if (heard) heard.textContent = '';
      send(btn);
    });
  }

  /* ---- signed out --------------------------------------------------------------- */
  var outWrap = doc.getElementById('followOutSheet');
  var outFrom = [];
  if (outWrap && window.SocialSheet) {
    var out = window.SocialSheet(outWrap, {
      openers: outFrom, doorCloses: false,
      first: function () { return outWrap.querySelector('.post-sheet-acts [data-make-close]'); }
    });
    doc.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-follow-out]');
      if (!b) return;
      e.preventDefault();
      about(outWrap, b);
      outFrom.length = 0;
      outFrom.push(b);
      out.open(b);
    });
  }

  /* ---- your own page: who follows you, and whom you follow -------------------- */
  var lists = doc.getElementById('followsSheet');
  if (lists && window.SocialSheet) {
    /* Your counts: "3 followers" opens Followers, "2 following" Following. */
    var openers = Array.prototype.slice.call(doc.querySelectorAll('[data-follows-open]'));
    var openerFor = function (key) {
      return openers.filter(function (o) { return o.getAttribute('data-follows-open') === key; })[0] || openers[0] || null;
    };
    var seg = lists.querySelector('.fo-seg');
    /* When each followed, in your own time ("8m", "2d"): social.js's. */
    if (window.SocialWhen) window.SocialWhen(lists);
    var tab = function (key) {
      var b = seg.querySelector('button[data-tab="' + key + '"]');
      if (!b) return;
      choose(seg, b);
      Array.prototype.forEach.call(lists.querySelectorAll('[data-list]'), function (l) {
        l.classList.toggle('is-on', l.getAttribute('data-list') === key);
      });
    };
    var sheet = window.SocialSheet(lists, {
      openers: openers, doorCloses: false, ownTouch: '.lk-list',
      first: function () { return seg.querySelector('button[aria-pressed="true"]'); },
      onOpen: function () { place(seg, true); }
    });
    openers.forEach(function (opener) {
      opener.addEventListener('click', function (e) {
        e.preventDefault();
        tab(opener.getAttribute('data-follows-open'));
        sheet.open(opener);
      });
    });
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-tab]');
      if (b && b.getAttribute('aria-pressed') !== 'true') tab(b.getAttribute('data-tab'));
    });
    /* Opened from a follow row in Activity: the lists, on the one asked
       (and the same for an address changed in place). */
    var landed = function () {
      var hash = (window.location.hash || '').slice(1);
      if (hash !== 'followers' && hash !== 'following') return;
      tab(hash);
      if (!sheet.isOpen()) sheet.open(openerFor(hash));
    };
    landed();
    window.addEventListener('hashchange', landed);
  }

  /* ---- Home's pill: Following | Everyone --------------------------------------- */
  var home = doc.querySelector('[data-home-pill]');
  var swap = doc.querySelector('[data-feed-swap]');
  if (home && swap) {
    var feed = swap.querySelector('[data-feed]');
    var more = swap.querySelector('[data-feed-next]');
    var none = swap.querySelector('[data-feed-none]');
    var pageSay = doc.querySelector('[data-feed-say]');
    var turn = 0;
    /* The tab the posts are showing: where the pill goes back to if the
       other's posts cannot be had. */
    var showing = (home.querySelector('button[aria-pressed="true"]') || { getAttribute: function () { return null; } })
      .getAttribute('data-show');
    /* The posts fade out (social.css, .feed-swap.is-out); this waits for them
       to be gone, however the fade ends. */
    var faded = function () {
      return new Promise(function (done) {
        var t = 0;
        function end() { clearTimeout(t); swap.removeEventListener('transitionend', on); done(); }
        function on(e) { if (e.target === swap && e.propertyName === 'opacity') end(); }
        swap.addEventListener('transitionend', on);
        t = setTimeout(end, 260);
        swap.classList.add('is-out');
      });
    };
    home.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-show]');
      if (!b || b.getAttribute('aria-pressed') === 'true') return;
      var show = b.getAttribute('data-show');
      var n = ++turn;
      choose(home, b);
      post(home.getAttribute('data-pick'), { show: show });
      var y = window.scrollY;
      var got = fetch(home.getAttribute('data-first') + '?show=' + encodeURIComponent(show), { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); });
      Promise.all([faded(), got]).then(function (res) {
        if (n !== turn) return;
        var j = res[1];
        /* Changed while they can't be seen, the page held at its height and
           its place, then faded back. */
        swap.style.minHeight = swap.offsetHeight + 'px';
        feed.innerHTML = j.html || '';
        showing = show;
        if (window.SocialWhen) window.SocialWhen(feed);
        if (window.SkriblInline) window.SkriblInline.mount(feed);
        if (more) {
          more.setAttribute('data-feed-next', j.next || '');
          more.hidden = !j.next;
        }
        if (none) none.hidden = !!feed.children.length;
        if (window.scrollY !== y) window.scrollTo(0, y);
        requestAnimationFrame(function () {
          if (n !== turn) return;
          swap.classList.remove('is-out');
          setTimeout(function () { if (n === turn) swap.style.minHeight = ''; }, 260);
        });
      }, function () {
        if (n !== turn) return;
        var back = home.querySelector('button[data-show="' + showing + '"]');
        if (back) choose(home, back);
        swap.classList.remove('is-out');
        if (pageSay) {
          pageSay.textContent = say('fo_network');
          pageSay.hidden = false;
        }
      });
    });
  }
})();
