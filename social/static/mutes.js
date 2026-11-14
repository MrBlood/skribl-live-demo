/* Mutes (phase 2; the mute mock and the owner's "Yes to all", C, quiet
 * everywhere, Nov 13): Mute @them in somebody's ⋯ (their page: safety.js;
 * their post or drawing: posts.js), the toast with Undo, Home's cards
 * folding away and back, and the line on their page (social/_mute.html).
 * mutes.py says the rules.
 *
 * NOTHING IS ASKED FIRST. A tap on Mute @theo: the sheet goes down (its own
 * controller), the site is told (/@<handle>/mute, the page's token in
 * X-Social-CSRF), and at once
 *   - on Home every card of theirs folds away from where you are: it fades,
 *     then its room closes and the next post rises into its place;
 *   - on their page the line opens under the buttons, "You muted Theo ·
 *     Unmute", yours alone;
 *   - on a post's own page nothing moves: it is what you went to;
 * and once the sheet has gone (0.3s from the tap) and the site has said yes,
 * the toast rises: "Theo is muted. They aren’t told." (following them, "Theo
 * is muted. You still follow them.": a mute never touches a follow), with
 * Undo for seven seconds, the Pad's own time for an Undo. A refusal puts
 * everything back and the toast says why, kindly.
 * UNDO, and Unmute (the line's, the ⋯'s): the site is told, the cards come
 * back the same way (their room opens, then they fade in), the line closes,
 * and the toast says "Unmuted. Theo’s posts are back." for the Pad's 2.8s.
 *
 * ONLY UNDO TAKES A TAP: a tap on the toast's words reaches the page under
 * it (social.css). A card that held the focus as it folds hands it to Undo,
 * and Undo hands it back to the ⋯ the mute began from.
 *
 * KIND, NEVER JUMPY: what moves glides, a fade first and then the room, or
 * the room and then the fade; under Reduce Motion a room is put there while
 * what it holds can't be seen, and only the fades remain.
 *
 * The words are the page's ([data-mute-words]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-mute-words] [data-word]'), function (w) {
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
  var EASE = 'cubic-bezier(0.4, 0, 0.2, 1)';
  var UNDO_MS = 7000, SAY_MS = 2800, WAIT_MS = 300, CARD_DELAY = 0.18, FEED_GAP = 16;

  function post(url, body) {
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
    if (j && j.error && WORDS['mu_' + j.error]) return say('mu_' + j.error);
    if (j && j.status === 429) return say('mu_limited');
    if (j && j.status === 401) return say('mu_signed_out');
    if (j && j.status === 403) return say('mu_stale');
    if (j && j.status === 404) return say('mu_gone');
    return say('mu_failed');
  }
  function shown(el) { return !!el && el.isConnected && el.getClientRects().length > 0; }

  /* ---- THE TOAST ---------------------------------------------------------- */
  var box = doc.querySelector('[data-mute-toasts]');
  var toast = box ? box.querySelector('.mu-toast') : null;
  var said = toast ? toast.querySelector('[data-mute-said]') : null;
  var undo = toast ? toast.querySelector('[data-mute-undo]') : null;
  var holdT = 0, goneT = 0, onUndo = null, toUndo = false;

  /* `text`, with Undo when `then` is given, rising `wait` ms from now (the
     rest of the sheet's going down). One already up keeps its place and
     takes the new words. */
  function rise(text, then, wait) {
    if (!toast) return;
    clearTimeout(holdT);
    clearTimeout(goneT);
    wait = Math.max(0, wait || 0);
    var up = !toast.hidden && toast.classList.contains('is-up');
    onUndo = then || null;
    toast.classList.remove('is-going');
    if (!up) {
      toast.classList.remove('is-up');
      toast.style.setProperty('--mu-wait', (wait / 1000).toFixed(3) + 's');
      toast.hidden = false;
      void toast.offsetHeight;          // laid out where it starts: lower, unseen
    }
    said.textContent = text;
    undo.hidden = !then;
    toast.classList.add('is-up');
    if (then && toUndo) {
      toUndo = false;
      undo.focus({ preventScroll: true });
    }
    holdT = setTimeout(fall, (then ? UNDO_MS : SAY_MS) + (up ? 0 : wait));
  }
  function fall() {
    if (!toast || toast.hidden) return;
    clearTimeout(holdT);
    onUndo = null;
    var had = doc.activeElement === undo;
    toast.classList.add('is-going');
    toast.classList.remove('is-up');
    goneT = setTimeout(function () {
      toast.hidden = true;
      toast.classList.remove('is-going');
      if (had && doc.activeElement === undo) undo.blur();
    }, 260);
  }
  if (undo) {
    undo.addEventListener('click', function () {
      var then = onUndo;
      onUndo = null;
      if (then) then();
    });
  }

  /* ---- A ROOM: what comes or goes, so nothing below it jumps ---------------- */
  /* Moving a node blurs whatever it holds: the focus is put back where it was. */
  function keep(el, move) {
    var had = el && el.contains(doc.activeElement) ? doc.activeElement : null;
    move();
    if (had && doc.activeElement !== had && had.isConnected) had.focus({ preventScroll: true });
  }
  function roomOf(el) {
    var p = el.parentElement;
    if (p && p.classList.contains('mu-room')) return p;
    var r = doc.createElement('div');
    r.className = 'mu-room';
    keep(el, function () {
      el.parentNode.insertBefore(r, el);
      r.appendChild(el);
    });
    return r;
  }
  /* Its work done, what the room holds stands where it was without it. */
  function unroom(r) {
    if (!r.parentNode) return;
    var el = r.firstElementChild;
    keep(el, function () {
      if (el) r.parentNode.insertBefore(el, r);
      r.parentNode.removeChild(r);
    });
  }
  /* `fn` once `r`'s `prop` has finished moving (the last of its glide: going,
     its height; coming, its fade), or a little after it should have: a tab
     put in the background mid-glide may never say. A glide turned round
     before then calls it off, its ending never run (freeze). */
  function settled(r, prop, ms, fn) {
    var t = 0;
    function off() { clearTimeout(t); r.removeEventListener('transitionend', on); if (r.__muOff === off) r.__muOff = null; }
    function end() { off(); fn(); }
    function on(e) { if (e.target === r && e.propertyName === prop) end(); }
    r.addEventListener('transitionend', on);
    t = setTimeout(end, ms);
    r.__muOff = off;
  }
  /* Where a room is now, kept there: read before its glide is called off, so
     a glide that turns round starts from where it was, never from its end. */
  function freeze(r) {
    if (r.__muOff) r.__muOff();
    var h = r.getBoundingClientRect().height, cs = getComputedStyle(r), op = cs.opacity, mb = cs.marginBottom;
    r.style.transition = 'none';
    r.style.height = h + 'px';
    r.style.opacity = op;
    r.style.marginBottom = mb;
    return h;
  }
  /* GOING: it fades, then its room closes, taking `gap` (the column's own
     gap) with it, `delay` seconds from now. Under Reduce Motion the room is
     put away once it can't be seen. */
  function shut(el, gap, delay, then) {
    var r = roomOf(el);
    freeze(r);
    void r.offsetHeight;
    r.style.transition = still()
      ? 'opacity 0.2s ease ' + delay + 's, height 0s linear ' + (delay + 0.2) + 's, margin-bottom 0s linear ' + (delay + 0.2) + 's'
      : 'opacity 0.2s ease ' + delay + 's, height 0.34s ' + EASE + ' ' + (delay + 0.16) + 's, margin-bottom 0.34s ' + EASE + ' ' + (delay + 0.16) + 's';
    r.style.opacity = '0';
    r.style.height = '0px';
    r.style.marginBottom = (-gap) + 'px';
    r.setAttribute('data-mute-shut', '');
    settled(r, 'height', (delay + 0.7) * 1000, function () { if (then) then(r); });
    return r;
  }
  /* COMING: its room opens to its whole height (what it holds and its
     margins, measured on the room itself), then it fades in, `delay`
     seconds from now; then it stands where it was, room or no room. Under
     Reduce Motion the room is put there while it can't be seen, and it
     fades in. */
  function open(el, delay) {
    var r = roomOf(el);
    var from = freeze(r), mb = r.style.marginBottom;
    r.style.height = 'auto';
    r.style.marginBottom = '';
    var h = r.getBoundingClientRect().height;
    r.style.height = from + 'px';
    r.style.marginBottom = mb;
    void r.offsetHeight;
    r.style.transition = still()
      ? 'height 0s linear ' + delay + 's, margin-bottom 0s linear ' + delay + 's, opacity 0.22s ease ' + delay + 's'
      : 'height 0.34s ' + EASE + ' ' + delay + 's, margin-bottom 0.34s ' + EASE + ' ' + delay + 's, opacity 0.22s ease ' + (delay + 0.2) + 's';
    r.style.height = h + 'px';
    r.style.marginBottom = '0px';
    r.style.opacity = '1';
    r.removeAttribute('data-mute-shut');
    settled(r, 'opacity', (delay + 0.7) * 1000, function () { unroom(r); });
    return r;
  }

  /* ---- HOME: their cards fold away, and come back -------------------------- */
  function cardsOf(handle) {
    var feed = doc.querySelector('[data-feed]');
    if (!feed) return [];
    return Array.prototype.filter.call(feed.querySelectorAll('.post-card[data-handle]'), function (c) {
      return c.getAttribute('data-handle') === handle;
    });
  }
  function fold(handle) {
    cardsOf(handle).forEach(function (c) {
      if (c.contains(doc.activeElement)) toUndo = true;
      shut(c, FEED_GAP, CARD_DELAY);
    });
  }
  function unfold(handle, delay) {
    cardsOf(handle).forEach(function (c) {
      var p = c.parentElement;
      if (p && p.classList.contains('mu-room') && p.hasAttribute('data-mute-shut')) open(c, delay || 0);
    });
  }

  /* ---- THEIR PAGE: the line under the buttons -------------------------------- */
  var prof = doc.querySelector('[data-profile][data-handle]');
  var tpl = doc.querySelector('template[data-mute-line-tpl]');
  function lineFor(handle) {
    return prof && prof.getAttribute('data-handle') === handle ? prof.querySelector('[data-mute-line]') : null;
  }
  function lineOpen(handle, delay) {
    if (!prof || !tpl || prof.getAttribute('data-handle') !== handle) return;
    var p = lineFor(handle);
    if (!p) {
      p = tpl.content.firstElementChild.cloneNode(true);
      tpl.parentNode.insertBefore(p, tpl);
      var r = roomOf(p);
      r.style.height = '0px';
      r.style.opacity = '0';
    }
    open(p, delay);
  }
  function lineShut(handle, delay) {
    var p = lineFor(handle);
    if (!p) return;
    p.removeAttribute('data-mute-line');
    shut(p, 0, delay || 0, function (r) { if (r.parentNode) r.parentNode.removeChild(r); });
  }

  /* ---- WHAT EACH PLACE SAYS NOW ------------------------------------------------ */
  /* The cards and the page carry it (posts.js fills its ⋯ from it); their
     page's ⋯ says it in its row. */
  function mark(handle, on) {
    Array.prototype.forEach.call(doc.querySelectorAll('.post-card[data-handle], .post-page[data-handle]'), function (a) {
      if (a.getAttribute('data-handle') !== handle) return;
      if (on) a.setAttribute('data-muted', ''); else a.removeAttribute('data-muted');
    });
    var person = doc.getElementById('personSheet');
    var row = person && person.getAttribute('data-handle') === handle ? person.querySelector('[data-safety="mute"]') : null;
    if (row) {
      row.setAttribute('data-muted', on ? 'true' : 'false');
      row.querySelector('[data-mute-name]').textContent = say(on ? 'mu_unmute' : 'mu_mute', { handle: handle });
      row.querySelector('[data-mute-say]').textContent = say(on ? 'mu_say_un' : 'mu_say');
    }
  }

  /* ---- MUTE, UNMUTE, UNDO ---------------------------------------------------- */
  var busy = {};
  /* o: { handle, first, muted (as it stands), opener (what the ⋯ was) }. */
  function act(o) {
    if (!box || !o || !o.handle || busy[o.handle]) return;
    busy[o.handle] = true;
    var want = !o.muted, t0 = Date.now();
    function show(on, delay) {
      if (on) { fold(o.handle); lineOpen(o.handle, delay); }
      else { unfold(o.handle, 0); lineShut(o.handle, 0); }
      mark(o.handle, on);
    }
    show(want, CARD_DELAY);
    post(box.getAttribute(want ? 'data-mute' : 'data-unmute').replace('__H__', encodeURIComponent(o.handle)), {}).then(function (j) {
      busy[o.handle] = false;
      var wait = WAIT_MS - (Date.now() - t0);
      if (j.ok) {
        if (want) {
          rise(say(j.following ? 'mu_muted_following' : 'mu_muted', { first: o.first }), function () {
            act({ handle: o.handle, first: o.first, muted: true, opener: o.opener, undoing: true });
          }, wait);
        } else {
          rise(say('mu_back', { first: o.first }), null, wait);
          if (o.undoing && shown(o.opener)) o.opener.focus({ preventScroll: true });
        }
        return;
      }
      toUndo = false;
      show(!want, 0);
      rise(why(j), null, wait);
    });
  }
  /* THEIR PAGE'S LINE: Unmute there, and the ⋯ keeps the focus once it goes. */
  doc.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('[data-mute-unmute]') : null;
    if (!b || !prof) return;
    e.preventDefault();
    var more = doc.querySelector('[data-person-menu]');
    if (more) more.focus({ preventScroll: true });
    act({ handle: prof.getAttribute('data-handle'), first: prof.getAttribute('data-first') || '', muted: true,
          opener: more });
  });

  window.SocialMute = { act: act };
})();
