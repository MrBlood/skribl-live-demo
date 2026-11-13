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
 *
 * YOUR OWN PAGE: "Followed by…" (or "You follow…") opens who follows you and
 * whom you follow, the one pill between them; opened at #followers or
 * #following (a follow row in Activity), it rises on that list.
 *
 * HOME'S PILL, Following | Everyone: a tap glides the pill to it, keeps the
 * pick for the account (/home/show), fades the posts out, puts the other
 * tab's first page in while they can't be seen (/feed?show=), and fades them
 * back; the page doesn't scroll. Load more then carries on from that page
 * (posts.js: its cursor says which).
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
  /* Placed from the rendered boxes, to the hundredth of a pixel (as Skribl's
     lib/segslider.js places the Gallery's): the first time, and `now`, put
     there; after that it glides (social.css), and is put there under Reduce
     Motion. Until it is placed, the chosen option wears the tint itself. */
  function place(seg, now) {
    var pill = seg.querySelector('.fo-slider'), btn = seg.querySelector('button[aria-pressed="true"]');
    var g = seg.getBoundingClientRect(), b = btn ? btn.getBoundingClientRect() : null;
    if (!pill || !b || !b.width || !g.width) { seg.removeAttribute('data-pill'); return; }
    var x = Math.round((b.left - g.left - seg.clientLeft - (parseFloat(getComputedStyle(pill).left) || 0)) * 100) / 100;
    var w = Math.round(b.width * 100) / 100;
    var first = now || !seg.hasAttribute('data-pill');
    if (first) pill.style.transition = 'none';
    pill.style.transform = 'translateX(' + x + 'px)';
    pill.style.width = w + 'px';
    if (first) {
      seg.setAttribute('data-pill', '');
      void pill.offsetWidth;
      pill.style.transition = '';
    }
  }
  function choose(seg, btn) {
    Array.prototype.forEach.call(seg.querySelectorAll('button'), function (b) {
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    place(seg, false);
  }
  /* Watched, so a pill in a sheet that ships hidden, a late font or a turned
     phone still has its tint where its option is. */
  Array.prototype.forEach.call(doc.querySelectorAll('.fo-seg'), function (seg) {
    var wide = 0;
    function again() {
      var w = seg.getBoundingClientRect().width;
      place(seg, !wide || !w);
      wide = w;
    }
    if (window.ResizeObserver) new ResizeObserver(again).observe(seg);
    again();
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(again);
  });

  /* ---- Follow, then Following ------------------------------------------------ */
  var said = doc.querySelector('[data-say]');
  var heard = doc.querySelector('[data-follow-said]');
  function tell(text) {
    if (!said) return;
    said.textContent = text || '';
    said.hidden = !text;
  }
  var btn = doc.querySelector('[data-follow]');
  var unWrap = doc.getElementById('unfollowSheet');
  var un = btn && unWrap && window.SocialSheet ? window.SocialSheet(unWrap, {
    openers: [btn], doorCloses: false,
    first: function () { return unWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;
  /* What the button shows: following or not (a change fades, and following
     draws the check: .fo-anim; unfollowing fades it, nothing un-drawing:
     .fo-fade), its name, and whether a tap raises a sheet. */
  function show(on, moving) {
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
  if (btn) {
    var st = { on: btn.classList.contains('is-following'), sure: btn.classList.contains('is-following'), busy: false };
    var send = function () {
      if (st.busy) return;      /* its answer sends again if a tap changed what they want */
      st.busy = true;
      var want = st.on;
      post(btn.getAttribute('data-follow'), { following: want }).then(function (j) {
        st.busy = false;
        if (j.ok) {
          st.sure = !!j.following;
          if (st.on !== want) { send(); return; }
          if (st.on !== st.sure) { st.on = st.sure; show(st.on, true); }
          if (heard) heard.textContent = st.sure ? say('fo_now_following', { name: btn.getAttribute('data-name') || '' }) : '';
          return;
        }
        st.on = st.sure;
        show(st.on, true);
        tell(why(j));
      });
    };
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      if (st.on) {
        if (un) un.open(btn);
        return;
      }
      st.on = true;
      tell('');
      show(true, true);
      send();
    });
    var go = unWrap && unWrap.querySelector('[data-unfollow]');
    if (go) {
      go.addEventListener('click', function () {
        if (un) un.close();
        if (!st.on) return;
        st.on = false;
        tell('');
        show(false, true);
        if (heard) heard.textContent = '';
        send();
      });
    }
  }

  /* ---- signed out --------------------------------------------------------------- */
  var outWrap = doc.getElementById('followOutSheet');
  var outBtn = doc.querySelector('[data-follow-out]');
  if (outWrap && outBtn && window.SocialSheet) {
    var out = window.SocialSheet(outWrap, {
      openers: [outBtn], doorCloses: false,
      first: function () { return outWrap.querySelector('.post-sheet-acts [data-make-close]'); }
    });
    outBtn.addEventListener('click', function (e) { e.preventDefault(); out.open(outBtn); });
  }

  /* ---- your own page: who follows you, and whom you follow -------------------- */
  var lists = doc.getElementById('followsSheet');
  if (lists && window.SocialSheet) {
    var opener = doc.querySelector('[data-follows-open]');
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
      openers: opener ? [opener] : [], doorCloses: false, ownTouch: '.lk-list',
      first: function () { return seg.querySelector('button[aria-pressed="true"]'); },
      onOpen: function () { place(seg, true); }
    });
    if (opener) {
      opener.addEventListener('click', function (e) {
        e.preventDefault();
        tab(opener.getAttribute('data-follows-open'));
        sheet.open(opener);
      });
    }
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
      if (!sheet.isOpen()) sheet.open(opener);
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
      var was = home.querySelector('button[aria-pressed="true"]');
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
        if (was) choose(home, was);
        swap.classList.remove('is-out');
        if (pageSay) {
          pageSay.textContent = say('fo_network');
          pageSay.hidden = false;
        }
      });
    });
  }
})();
