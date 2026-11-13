/* Comments (phase 2; the comments mock and the owner's "all yes on both",
 * Nov 12): a post's own page, and a drawing's (post.html,
 * social/_comments.html), the same section on both: the page names its own
 * addresses (data-new, data-more, data-drop).
 *
 * THE BOX ON TOP: the words grow as they are typed and say how many are left
 * once few are; Post sends them (/social/p/<id>/comments, or a drawing's
 * /social/b/<id>/comments; the page's token in
 * X-Social-CSRF) and the new comment fades in at the top, newest first, the
 * count with it. With nothing written or drawn, Post says so and sends
 * nothing.
 *
 * A DRAWING ANSWER (the mock's 6): Draw and Flip open Skribl's editor over the
 * post in compose mode (social.js's SocialPadOverlay over lib/composehost.js,
 * as Home's composer; no gallery tick: a drawing answer is unlisted). Its Add
 * hands the drawing back, and it waits in the box in Skribl's in-post player,
 * the one the comment will have, with Edit drawing (the editor again, the
 * drawing in it) and Remove, until Post sends it with the words. A comment's
 * drawing is still until tapped: posts.js plays only the post's own.
 *
 * ANSWER BRINGS THE BOX to the comment, under its answers, saying "Answer
 * Theo…"; it goes back on Answer again, Esc, or once the answer is posted.
 * An answer to an answer sits under the same comment (the server says
 * which). KIND, NEVER JUMPY: the comment keeps its place on the screen while
 * the box moves (the page scrolls by what moved above it, with the browser's
 * own scroll anchoring held off for that one change, so the two never both
 * move it), and the box fades in where it lands; under a long thread, below
 * what the screen shows, the page then glides down to it.
 *
 * A COMMENT'S ⋯ (social.js's SocialSheet, as the post's): Your comment:
 * Delete comment; somebody else's on your own post: Remove from my post and
 * Report comment; anybody else's: Report comment. Delete and Remove go at
 * once, the comment fading out with its answers; Report rises as a sheet of
 * its own with a post's reasons, into the site's own queue.
 *
 * LOAD MORE brings the next page of comments in place.
 *
 * OPENED AT A COMMENT (#c-<id>, a row in Activity; notifications): it glows
 * a moment in the note's tint, and a drawing answer draws itself once (below).
 *
 * The words are the page's ([data-comment-words]): this file says nothing of
 * its own. Times are said by posts.js (window.SocialWhen).
 */
(function () {
  'use strict';
  var doc = document;
  var root = doc.querySelector('[data-comments]');
  if (!root) return;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-comment-words] [data-word]'), function (w) {
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

  function send(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
                        body: JSON.stringify(body || {}) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!j || typeof j !== 'object') j = {};
          j.status = r.status;
          return j;
        });
      }, function () { return { error: 'network' }; });
  }
  function why(j) {
    if (j && j.error === 'rejected' && j.message) return j.message;
    if (j && j.error && WORDS['c_' + j.error]) return say('c_' + j.error);
    if (j && j.status === 413) return say('c_too_big');
    if (j && j.status === 429) return say('c_limited');
    if (j && j.status === 403) return say('c_stale');
    if (j && j.status === 401) return say('c_signed_out');
    if (j && j.status === 404) return say('c_gone');
    return say('c_failed');
  }

  var title = root.querySelector('#commentsTitle');
  var list = root.querySelector('[data-cm-list]');
  var countEl = root.querySelector('[data-cm-count]');
  var pageSay = root.querySelector('[data-cm-page-say]');
  function setCount(n) {
    if (!countEl || typeof n !== 'number') return;
    countEl.textContent = String(n);
    countEl.hidden = !n;
  }
  /* What arrives later is said as what was there: its times, and its
     drawing's player (still until tapped, as Skribl asks of a feed that adds
     posts later). */
  function settle(el) {
    if (window.SocialWhen) window.SocialWhen(el);
    if (window.SkriblInline) window.SkriblInline.mount(el);
  }

  /* KEEP `anchor` WHERE IT IS ON THE SCREEN while `change` moves what is
     above it. The browser's own scroll anchoring is held off for this one
     change (overflow-anchor), so it and this never both correct it; an
     iPhone has none, so this is its only one. */
  function keep(anchor, change) {
    var html = doc.documentElement;
    var top = anchor && anchor.isConnected ? anchor.getBoundingClientRect().top : null;
    html.style.overflowAnchor = 'none';
    change();
    if (top !== null && anchor.isConnected) {
      var d = anchor.getBoundingClientRect().top - top;
      if (Math.abs(d) >= 0.5) window.scrollBy(0, d);
    }
    requestAnimationFrame(function () { requestAnimationFrame(function () { html.style.overflowAnchor = ''; }); });
  }

  /* THE BOX WHERE IT CAN BE SEEN: if Answer brought it under a long thread,
     below what the screen shows (above a phone's bar), the page glides down
     to it, never jumps; under Reduce Motion it is simply put there. */
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function reveal(el) {
    var r = el.getBoundingClientRect(), floor = window.innerHeight;
    var bar = doc.querySelector('body > .nav');
    if (bar) {
      var b = bar.getBoundingClientRect();
      if (b.top > floor / 2) floor = b.top;           // a phone's bar along the bottom
    }
    var over = r.bottom - (floor - 12);
    if (over > 0) window.scrollBy({ top: Math.min(over, r.top - 12), behavior: reduced && reduced.matches ? 'auto' : 'smooth' });
  }

  /* ---- the box: on top, or under the comment it answers ------------------- */
  var box = root.querySelector('[data-cm-box]');
  var words = box ? box.querySelector('[data-cm-words]') : null;
  var label = box ? box.querySelector('[data-cm-label]') : null;
  var left = box ? box.querySelector('[data-cm-left]') : null;
  var postBtn = box ? box.querySelector('[data-cm-post]') : null;
  var sayBox = box ? box.querySelector('[data-cm-say]') : null;
  var hint = words ? words.getAttribute('placeholder') : '';
  var LIMIT = words ? (+words.getAttribute('maxlength') || 500) : 500;
  var answering = null;      // { id, top, btn }
  var sending = false;
  var draftWrap = box ? box.querySelector('[data-cm-draft]') : null;
  var draftBox = draftWrap ? draftWrap.querySelector('.skribl-inline') : null;
  var chips = box ? Array.prototype.slice.call(box.querySelectorAll('[data-cm-open]')) : [];
  var draft = null;          // { payload, over }

  function grow() {
    if (!words) return;
    words.style.height = 'auto';
    words.style.height = words.scrollHeight + 'px';
    var n = LIMIT - words.value.length;
    left.textContent = n <= 100 ? say('c_left', { n: n }) : '';
  }
  if (words) { words.addEventListener('input', grow); grow(); }

  function arrive() {
    box.classList.remove('is-arriving');
    void box.offsetWidth;
    box.classList.add('is-arriving');
  }
  box && box.addEventListener('animationend', function () { box.classList.remove('is-arriving'); });

  function pressed(btn, on) { if (btn) btn.setAttribute('aria-expanded', on ? 'true' : 'false'); }

  /* The box under `li`'s comment, to answer `li` (a comment or an answer). */
  function answer(li, btn) {
    var top = li.parentNode && li.parentNode.classList.contains('cm-answers') ? li.parentNode.closest('.cm') : li;
    var id = li.getAttribute('data-comment');
    if (answering && answering.id === id) { home(btn); return; }
    if (answering) pressed(answering.btn, false);
    answering = { id: id, top: top, btn: btn };
    var name = li.getAttribute('data-first') || '';
    keep(li, function () { top.appendChild(box); });
    words.setAttribute('placeholder', say('c_answer', { name: name }));
    label.textContent = say('c_answer_label', { name: name });
    tell(sayBox, '');
    pressed(btn, true);
    arrive();
    words.focus({ preventScroll: true });
    reveal(box);
  }

  /* The box back on top. `focusTo`: what takes focus there (the Answer that
     sent it home), and `anchor`: what keeps its place on the screen. */
  function home(focusTo, anchor) {
    if (!answering) return;
    var was = answering;
    answering = null;
    pressed(was.btn, false);
    keep(anchor || was.top, function () { title.parentNode.insertBefore(box, title.nextSibling); });
    words.setAttribute('placeholder', hint);
    label.textContent = say('c_say');
    tell(sayBox, '');
    arrive();
    if (focusTo && focusTo.isConnected) focusTo.focus({ preventScroll: true });
  }

  /* ---- a drawing answer: the editor over the post, the drawing in the box -- */
  function attach(payload, over) {
    draft = { payload: payload, over: over };
    draftWrap.hidden = false;
    if (draftBox && window.SkriblInline) window.SkriblInline.attach(draftBox, payload);
    chips.forEach(function (c) { c.hidden = true; });
    tell(sayBox, '');
    var edit = box.querySelector('[data-cm-edit]');
    if (edit) edit.focus({ preventScroll: true });
  }
  function unattach(focus) {
    if (draft && draft.over) draft.over.pad.clear();
    draft = null;
    if (draftWrap) draftWrap.hidden = true;
    chips.forEach(function (c) { c.hidden = false; });
    if (focus && chips[0]) chips[0].focus({ preventScroll: true });
  }
  chips.forEach(function (chip) {
    var wrap = doc.getElementById(chip.getAttribute('data-cm-open') === 'flip' ? 'commentFlip' : 'commentPad');
    var over = window.SocialPadOverlay ? window.SocialPadOverlay(wrap, {
      openers: [chip],
      onDone: function (payload) { attach(payload, over); }
    }) : null;
    chip.addEventListener('click', function () {
      if (!over || sending) return;
      tell(sayBox, '');
      over.open(chip);
    });
  });
  if (box && draftWrap) {
    box.querySelector('[data-cm-edit]').addEventListener('click', function (e) {
      if (draft && draft.over && !sending) draft.over.open(e.currentTarget);
    });
    box.querySelector('[data-cm-remove]').addEventListener('click', function () {
      if (!draft || sending) return;
      unattach(true);
    });
  }

  if (box) {
    words.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && answering) { e.preventDefault(); home(answering.btn); }
    });
    postBtn.addEventListener('click', function () {
      if (sending) return;
      if (!words.value.trim() && !draft) { tell(sayBox, say('c_empty')); return; }
      sending = true;
      postBtn.disabled = true;
      tell(sayBox, say('c_posting'));
      var body = { words: words.value };
      if (draft) body.payload = draft.payload;
      if (answering) body.answer_to = answering.id;
      send(root.getAttribute('data-new'), body).then(function (j) {
        sending = false;
        postBtn.disabled = false;
        if (!(j.ok && j.html)) { tell(sayBox, why(j)); return; }
        tell(sayBox, '');
        words.value = '';
        grow();
        if (draft) unattach(false);
        var holder = doc.createElement('div');
        holder.innerHTML = j.html;
        var li = holder.querySelector('.cm');
        if (!li) return;
        li.classList.add('is-new');
        var top = j.under ? doc.getElementById('c-' + j.under) : null;
        if (top) {
          var ans = top.querySelector(':scope > .cm-answers');
          if (!ans) {
            ans = doc.createElement('ol');
            ans.className = 'cm-answers';
            top.insertBefore(ans, box.parentNode === top ? box : null);
          }
          ans.appendChild(li);
          settle(li);
          home(li.querySelector('[data-cm-answer]'), li);
        } else {
          list.insertBefore(li, list.firstChild);
          settle(li);
        }
        setCount(j.count);
      });
    });
  }

  /* ---- a comment's ⋯ ------------------------------------------------------ */
  var menuWrap = doc.getElementById('commentSheet');
  var reportWrap = doc.getElementById('commentReportSheet');
  function firstAct(wrap) {
    return function () {
      return Array.prototype.filter.call(wrap.querySelectorAll('.post-act'), function (b) { return !b.hidden; })[0] || null;
    };
  }
  var menu = menuWrap && window.SocialSheet ? window.SocialSheet(menuWrap, { doorCloses: false, first: firstAct(menuWrap) }) : null;
  var report = reportWrap && window.SocialSheet
    ? window.SocialSheet(reportWrap, { doorCloses: false, ownTouch: '.post-note',
                                       first: function () { return reportWrap.querySelector('input[name=reason]:checked'); } })
    : null;
  var current = null, opener = null;

  root.addEventListener('click', function (e) {
    var a = e.target.closest('[data-cm-answer]');
    if (a && box) {
      e.preventDefault();
      answer(a.closest('.cm'), a);
      return;
    }
    var m = e.target.closest('[data-cm-menu]');
    if (m && menu) {
      e.preventDefault();
      var li = m.closest('.cm');
      current = { li: li, id: li.getAttribute('data-comment'), first: li.getAttribute('data-first') || '',
                  mine: li.hasAttribute('data-mine') };
      opener = m;
      var postMine = root.hasAttribute('data-post-mine');
      menuWrap.querySelector('#commentSheetTitle').textContent =
        current.mine ? say('c_yours') : say('c_theirs', { name: current.first });
      menuWrap.querySelector('[data-cm-act=delete]').hidden = !current.mine;
      menuWrap.querySelector('[data-cm-act=remove]').hidden = current.mine || !postMine;
      menuWrap.querySelector('[data-cm-act=report]').hidden = current.mine;
      tell(menuWrap.querySelector('[data-cm-sheet-say]'), '');
      Array.prototype.forEach.call(menuWrap.querySelectorAll('.post-act'), function (b) { b.disabled = false; });
      menu.open(m);
    }
  });

  function drop(li) {
    if (answering && li.contains(box)) home(null);
    li.classList.add('is-going');
    var gone = false;
    function out() { if (gone) return; gone = true; if (li.parentNode) li.parentNode.removeChild(li); }
    li.addEventListener('transitionend', function (e) { if (e.target === li) out(); });
    setTimeout(out, 400);
  }

  if (menuWrap) {
    menuWrap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-cm-act]');
      if (!b || !current) return;
      var act = b.getAttribute('data-cm-act'), sayIt = menuWrap.querySelector('[data-cm-sheet-say]');
      if (act === 'report' && report) {
        menu.close(true);
        var form = reportWrap.querySelector('[data-report-form]');
        form.reset();
        var go = reportWrap.querySelector('[data-cm-report-send]');
        go.disabled = false;
        go.hidden = false;
        var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
        if (c && c.hasAttribute('data-was')) { c.textContent = c.getAttribute('data-was'); c.removeAttribute('data-was'); }
        tell(reportWrap.querySelector('[data-cm-report-say]'), '');
        report.open(opener);
        return;
      }
      /* Delete comment, or Remove from my post: one route, gone at once. */
      b.disabled = true;
      tell(sayIt, say('c_deleting'));
      var li = current.li;
      send(root.getAttribute('data-drop').replace('__ID__', encodeURIComponent(current.id)), {}).then(function (j) {
        b.disabled = false;
        if (!j.ok) { tell(sayIt, why(j)); return; }
        tell(sayIt, '');
        menu.close(true);
        setCount(j.count);
        drop(li);
      });
    });
  }

  if (reportWrap) {
    reportWrap.querySelector('[data-report-form]').addEventListener('submit', function (e) {
      e.preventDefault();
      if (!current) return;
      var go = reportWrap.querySelector('[data-cm-report-send]'), sayIt = reportWrap.querySelector('[data-cm-report-say]');
      var picked = reportWrap.querySelector('input[name=reason]:checked');
      go.disabled = true;
      tell(sayIt, say('c_sending'));
      send(reportWrap.getAttribute('data-report'),
           { kind: 'comment', target: current.id, reason: picked ? picked.value : 'other',
             note: (reportWrap.querySelector('.post-note').value || '').trim() })
        .then(function (j) {
          if (j.status === 202) {
            tell(sayIt, say('c_reported'));
            go.hidden = true;
            var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
            if (c) { c.setAttribute('data-was', c.textContent); c.textContent = say('c_done'); }
            return;
          }
          go.disabled = false;
          tell(sayIt, j.status === 429 ? say('c_report_limited') : why(j));
        });
    });
  }

  /* ---- Load more ------------------------------------------------------------ */
  var more = root.querySelector('[data-cm-next]');
  /* The next page in place: a promise of whether one came. */
  function loadMore() {
    var next = more ? more.getAttribute('data-cm-next') : '';
    if (!next) return Promise.resolve(false);
    more.disabled = true;
    return fetch(root.getAttribute('data-more') + '?before=' + encodeURIComponent(next), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (j) {
        var holder = doc.createElement('div');
        holder.innerHTML = j.html || '';
        Array.prototype.slice.call(holder.children).forEach(function (li) { list.appendChild(li); settle(li); });
        if (j.next) more.setAttribute('data-cm-next', j.next);
        else { more.setAttribute('data-cm-next', ''); more.hidden = true; }
        more.disabled = false;
        return true;
      }, function () {
        more.disabled = false;
        tell(pageSay, say('c_network'));
        return false;
      });
  }
  if (more) more.addEventListener('click', function () { loadMore(); });

  /* ---- OPENED AT A COMMENT (#c-<id>: a row in Activity; notifications) ------
     The comment glows a moment in the note's tint, then the tint fades over a
     second and a half (social.css, .cm.is-landed: the comment alone, its own
     height, not the answers under it). A drawing answer draws itself once,
     sound off, as a post's drawing starts on its own page, and the post's own
     waits (one plays at a time); at any other comment the post's own plays,
     as it always does (posts.js, window.SocialPlayOwn). One on a later page is
     brought in with Load more, a page at a time, and the page glides to it.
     UNDER REDUCE MOTION nothing moves or plays: the page is put there, and the
     tint fades where it sits. */
  var GLOW_MS = 900, FADE_MS = 1500, LAND_PAGES = 10;
  function playOwn() { if (window.SocialPlayOwn) window.SocialPlayOwn(); }
  function still() { return !!(reduced && reduced.matches); }
  function glow(li) {
    var main = li.querySelector(':scope > .cm-main');
    if (main) {
      var own = main.getBoundingClientRect().bottom - li.getBoundingClientRect().top + 2;
      li.style.setProperty('--cm-own', Math.max(0, Math.round(own)) + 'px');
    }
    li.classList.add('is-landed');
    var done = false;
    function end() {
      if (done) return;
      done = true;
      li.classList.remove('is-landed', 'is-fading');
      li.style.removeProperty('--cm-own');
    }
    setTimeout(function () {
      li.classList.add('is-fading');
      li.addEventListener('transitionend', function (e) { if (e.target === li && e.pseudoElement === '::before') end(); });
      setTimeout(end, FADE_MS + 400);
    }, GLOW_MS);
  }
  function drawOnce(art) {
    if (still() || !window.SkriblInline) return;
    var players = window.SkriblInline.mount(art);
    if (players && players[0] && players[0].play) players[0].play();
  }
  function landed(li, brought) {
    if (brought) li.scrollIntoView({ block: 'center', behavior: still() ? 'auto' : 'smooth' });
    glow(li);
    var art = li.querySelector(':scope > .cm-main .cm-art');
    if (art) drawOnce(art); else playOwn();
  }
  (function land() {
    var m = /^#(c-[A-Za-z0-9_-]+)$/.exec(window.location.hash || '');
    if (!m) return;
    var pages = 0;
    (function look() {
      var li = doc.getElementById(m[1]);
      if (li && li.classList.contains('cm')) { landed(li, pages > 0); return; }
      if (pages >= LAND_PAGES || !more || !more.getAttribute('data-cm-next')) { playOwn(); return; }
      pages++;
      loadMore().then(function (got) { if (got) look(); else playOwn(); });
    })();
  })();
})();
