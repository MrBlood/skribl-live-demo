/* Likes (phase 2; the likes mock and the owner's "I like d.", Nov 13): the
 * heart on Home's cards and on a post's or a drawing's own page
 * (social/_post.html, heart()), the maker's "Liked by…" and its sheet, and
 * the signed-out sheet (social/_likes.html). likes.py says the rules.
 *
 * A TAP LIKES, AND THE SAME TAP TAKES IT BACK. The heart changes at once (its
 * line draws itself round in blush and fills; taken back, it fades), the
 * count with it, and the site is told (/p/<id>/like or /b/<id>/like, the
 * page's token in X-Social-CSRF). One request at a time a heart: taps made
 * meanwhile are where it ends up, and the site's answer is what stays. One
 * that did not take goes back, kindly, and the page says why.
 *
 * EACH LIKE KEEPS ITS MOMENT: where the drawing was, if it was playing, read
 * from Skribl's in-post player through its playhead seam (player.playhead():
 * docs/INTEGRATION.md, "Where the playhead is"); nothing when it was not.
 *
 * SIGNED OUT the heart raises a small sheet that says how (social.js's
 * SocialSheet, as Make's); Sign in comes back to the same page, and nothing
 * is pressed for them.
 *
 * THE MAKER'S "Liked by…" opens who liked it in Make's own sheet. A like they
 * give or take back on their own answers with the line and the rows as they
 * now stand. Opened from a like in Activity (#liked), the line glows a moment
 * in the note's tint, as a comment does when you land on it.
 *
 * KIND, NEVER JUMPY: the heart draws or fades (social.css, "LIKES"); a count
 * that comes or goes fades, and what it moves glides there, as does the line
 * of who. Under Reduce Motion nothing moves: things fade where they sit.
 *
 * The words are the page's ([data-like-words]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-like-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key, vars) {
    var s = WORDS[key] || '';
    Object.keys(vars || {}).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still() { return !!(reduced && reduced.matches); }
  var pageSay = doc.querySelector('[data-feed-say], [data-page-say]');
  function tell(text) {
    if (!pageSay) return;
    pageSay.textContent = text || '';
    pageSay.hidden = !text;
  }
  var GLIDE = { duration: 220, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' };

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
    if (j && j.error && WORDS['lk_' + j.error]) return say('lk_' + j.error);
    if (j && j.status === 429) return say('lk_limited');
    if (j && j.status === 401) return say('lk_signed_out');
    if (j && j.status === 403) return say('lk_stale');
    if (j && j.status === 404) return say('lk_gone');
    return say('lk_failed');
  }

  /* ---- what moves, glides ------------------------------------------------- */
  /* `change` alters the layout around `el`; whatever of `els` it moves glides
     from where it was to where it is (nothing under Reduce Motion). */
  function glide(els, change) {
    var before = els.map(function (e) { return e.getBoundingClientRect(); });
    change();
    if (still()) return;
    els.forEach(function (e, i) {
      if (!e.isConnected || !e.animate) return;
      var r = e.getBoundingClientRect();
      var dx = before[i].left - r.left, dy = before[i].top - r.top;
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
      e.animate([{ transform: 'translate(' + dx + 'px, ' + dy + 'px)' }, { transform: 'none' }], GLIDE);
    });
  }
  function fade(el, from, to, done) {
    if (!el.animate) { if (done) done(); return null; }
    var a = el.animate([{ opacity: from }, { opacity: to }], { duration: to ? 200 : 150, easing: 'ease', fill: 'forwards' });
    a.onfinish = function () { if (done) done(); };
    return a;
  }
  /* The heart's icon, and what sits after it on its row: what a count that
     comes or goes can move. */
  function movers(b) {
    var out = [b.querySelector('.ic-heart')];
    for (var s = b.nextElementSibling; s; s = s.nextElementSibling) out.push(s);
    return out.filter(Boolean);
  }

  /* ---- the heart ---------------------------------------------------------- */
  function count(b, n) {
    var span = b.querySelector('.lk-n');
    if (n > 0) {
      if (span) {
        span.textContent = String(n);
        if (span._going) {          /* going, and wanted back: it stays, from where it was */
          var was = parseFloat(getComputedStyle(span).opacity);
          span._going.cancel();
          span._going = null;
          fade(span, isFinite(was) ? was : 0, 1, function () { span.getAnimations().forEach(function (a) { a.cancel(); }); });
        }
        return;
      }
      span = doc.createElement('span');
      span.className = 'lk-n';
      span.textContent = String(n);
      glide(movers(b), function () { b.appendChild(span); });
      fade(span, 0, 1, function () { span.getAnimations().forEach(function (a) { a.cancel(); }); });
    } else if (span && !span._going) {
      span._going = fade(span, 1, 0, function () {
        if (!span._going) return;
        span._going = null;
        glide(movers(b), function () { span.remove(); });
      });
      if (!span._going) span.remove();
    }
  }
  /* What the heart shows: liked or not (a change draws or fades: social.css,
     .lk-anim and .lk-fade), how many, and its name. */
  function show(b, liked, n, moving) {
    if (b.classList.contains('is-liked') !== liked) {
      b.classList.remove('lk-anim', 'lk-fade');
      if (moving) b.classList.add(liked ? 'lk-anim' : 'lk-fade');
      b.classList.toggle('is-liked', liked);
      b.setAttribute('aria-pressed', liked ? 'true' : 'false');
    }
    count(b, n);
    b.setAttribute('aria-label', say(liked ? 'lk_liked' : 'lk_like')
      + (n > 0 ? ', ' + say(n === 1 ? 'lk_one' : 'lk_many', { n: n }) : ''));
  }
  function stateOf(b) {
    if (!b._lk) {
      var span = b.querySelector('.lk-n');
      var liked = b.getAttribute('aria-pressed') === 'true', n = span ? parseInt(span.textContent, 10) || 0 : 0;
      /* What they see, and what the site last said. */
      b._lk = { liked: liked, n: n, sure: liked, sureN: n, at: null, busy: false };
    }
    return b._lk;
  }

  /* Where the drawing is, on its own replay clock, if it is playing: the
     playhead seam of the player on this heart's card or page. Else null. */
  function moment(b) {
    var holder = b.closest('.post-card, .post-page');
    var art = holder && holder.querySelector('.post-art');
    if (!art || !window.SkriblInline) return null;
    var players = window.SkriblInline.mount(art);
    var p = players && players[0];
    var h = p && p.playhead ? p.playhead() : null;
    return h && h.playing && isFinite(h.ms) ? Math.max(0, Math.round(h.ms)) : null;
  }

  function tap(b) {
    var st = stateOf(b);
    st.liked = !st.liked;
    st.n = Math.max(0, st.n + (st.liked ? 1 : -1));
    if (st.liked) st.at = moment(b);
    show(b, st.liked, st.n, true);
    tell('');
    send(b);
  }
  function send(b) {
    var st = stateOf(b);
    if (st.busy) return;           /* its answer sends again if a tap changed what they want */
    st.busy = true;
    var want = st.liked;
    post(b.getAttribute('data-like'), { liked: want, at_ms: want ? st.at : null }).then(function (j) {
      st.busy = false;
      if (j.ok) {
        st.sure = !!j.liked;
        st.sureN = +j.count || 0;
        if (typeof j.by === 'string') maker(j);
        if (st.liked !== want) { send(b); return; }
        st.liked = st.sure;
        st.n = st.sureN;
        show(b, st.liked, st.n, true);
        return;
      }
      st.liked = st.sure;
      st.n = st.sureN;
      show(b, st.liked, st.n, true);
      tell(why(j));
    });
  }

  /* ---- the maker's "Liked by…", and who ----------------------------------- */
  var whoWrap = doc.getElementById('likeSheet');
  var byOpeners = Array.prototype.slice.call(doc.querySelectorAll('[data-like-by]'));
  var who = whoWrap && window.SocialSheet ? window.SocialSheet(whoWrap, {
    openers: byOpeners, doorCloses: false, ownTouch: '.lk-list',
    first: function () { return whoWrap.querySelector('.lk-row') || whoWrap.querySelector('.make-cancel'); }
  }) : null;

  /* Their own like, given or taken back: the line and the rows as they stand.
     A line that comes or goes opens or closes its room, and fades. */
  function maker(j) {
    var line = doc.querySelector('[data-like-by]');
    var meta = doc.querySelector('.post-page > .post-meta');
    var list = whoWrap && whoWrap.querySelector('[data-like-who]');
    if (list && typeof j.who === 'string') {
      list.innerHTML = j.who;
      if (window.SocialWhen) window.SocialWhen(list);
    }
    var html = j.by.trim();
    if (html) {
      var box = doc.createElement('div');
      box.innerHTML = html;
      var fresh = box.firstElementChild;
      if (!fresh) return;
      byOpeners.length = 0;
      byOpeners.push(fresh);
      if (line) { line.parentNode.replaceChild(fresh, line); return; }
      if (!meta) return;
      meta.parentNode.insertBefore(fresh, meta.nextSibling);
      room(fresh, true);
    } else if (line) {
      byOpeners.length = 0;
      room(line, false);
    }
  }
  /* The line's room, opening (`on`) or closing: its height and the space
     above it grow from nothing, or shrink to it, as it fades. */
  function room(el, on) {
    if (still() || !el.animate) {
      if (on) fade(el, 0, 1, function () { el.getAnimations().forEach(function (a) { a.cancel(); }); });
      else fade(el, 1, 0, function () { el.remove(); });
      return;
    }
    var cs = getComputedStyle(el);
    var h = el.offsetHeight + 'px';
    var full = { height: h, minHeight: h, marginTop: cs.marginTop, opacity: 1 };
    var none = { height: '0px', minHeight: '0px', marginTop: '0px', opacity: 0 };
    el.style.overflow = 'hidden';
    var a = el.animate(on ? [none, full] : [full, none], { duration: 240, easing: 'ease', fill: 'forwards' });
    a.onfinish = function () {
      if (!on) { el.remove(); return; }
      el.style.overflow = '';
      a.cancel();
    };
  }

  /* ---- signed out --------------------------------------------------------- */
  var outWrap = doc.getElementById('likeOutSheet');
  var out = outWrap && window.SocialSheet ? window.SocialSheet(outWrap, {
    openers: Array.prototype.slice.call(doc.querySelectorAll('[data-like-out]')), doorCloses: false,
    first: function () { return outWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;

  doc.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target : null;
    if (!t) return;
    var b = t.closest('[data-like]');
    if (b) { e.preventDefault(); tap(b); return; }
    var o = t.closest('[data-like-out]');
    if (o) {
      e.preventDefault();
      if (!out) return;
      var first = outWrap.querySelector('[data-like-first]');
      if (first && o.getAttribute('data-first')) first.textContent = o.getAttribute('data-first');
      out.open(o);
      return;
    }
    var by = t.closest('[data-like-by]');
    if (by && who) { e.preventDefault(); who.open(by); }
  });

  /* ---- landing from Activity (#liked) ------------------------------------- */
  (function land() {
    if (window.location.hash !== '#liked') return;
    var line = doc.getElementById('liked');
    if (!line || !line.hasAttribute('data-like-by')) return;
    line.classList.add('is-landed');
    setTimeout(function () {
      var done = false;
      function end() {
        if (done) return;
        done = true;
        line.classList.remove('is-landed', 'is-fading');
      }
      line.classList.add('is-fading');
      line.addEventListener('transitionend', function (e) { if (e.target === line && e.pseudoElement === '::before') end(); });
      setTimeout(end, 1500 + 400);
    }, 900);
  })();
})();
