/* The Gallery of everyone (Explore; docs/SOCIAL-SITE.md section 16, the
 * map's step 3; the Gallery mock's B and the owner's "Your picks are great",
 * Nov 13). gallery.py says who is in it and in what order; this file moves
 * it (explore.html).
 *
 * A PICK. Following | Everyone (signed in) and New | Hot are the one pill:
 * social.js places and glides its tint (window.SocialPill). A tap glides
 * it, fades the tiles out, puts the first page of the new pick in while they
 * can't be seen (/explore/more), and fades them back; the page doesn't
 * scroll. The search box asks once the typing pauses (350ms, as Skribl's
 * gallery's box did) or at once with Enter; emptied, everything is back.
 * Words already in the box when this file runs (typed on a slow phone, or
 * put back by the browser) count. The address says what is shown
 * (history.replaceState), so a reload, or the way back from a post, opens on
 * it.
 *
 * LOAD MORE brings the next page in place, by its cursor (a Hot one holds
 * the moment its first page was ranked at, so one scroll-through is one
 * order).
 *
 * PEOPLE TOO (finding people; the owner's "All yes", Nov 15): a search's
 * first page brings its People section ([data-fp-box], gallery.py's
 * {people}), put in with the tiles while they can't be seen, so it comes and
 * goes with them; the pills change the drawings alone. SEE ALL is the same
 * page asked for the people alone ([data-who="people"]): its search and its
 * Load more bring rows instead of tiles, by the people's own cursor, and an
 * emptied box keeps the rows it has (nothing to find).
 *
 * KIND, NEVER JUMPY: nothing moves but the pill's tint, which glides, and
 * the tiles, which fade (social.css, .gal-swap). Under Reduce Motion the tint
 * is put there and the tiles still only fade. Only the newest answer is
 * shown: one that comes back after a later pick is let go, so a slow answer
 * never puts back what the person has moved on from. A pick that cannot be
 * had puts the pills back to what the tiles show, and says so kindly.
 *
 * SEARCH'S OWN PAGE moves the same way (search.html: the box and what it
 * finds, no pills; the owner's "Yes to all", Nov 22). There an emptied box
 * asks the server for nothing and shows nothing of its own ([data-blank]):
 * what shows then is the recent searches, search.js's. Each time what is
 * shown changes, while it cannot be seen, this file says so on the part
 * that fades ('gal:swap', with the words it shows), so search.js puts its
 * list in or takes it out unseen too.
 *
 * The words are the page's ([data-gal-words]): this file says nothing of its
 * own.
 */
(function () {
  'use strict';
  var doc = document;
  var swap = doc.querySelector('[data-gal-swap]');
  var url = swap && swap.getAttribute('data-more');
  if (!swap || !url) return;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-gal-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  var page = swap.getAttribute('data-explore');
  var who = swap.getAttribute('data-who') || '';
  var blank = swap.hasAttribute('data-blank');
  var box = swap.querySelector('[data-fp-box]');
  var grid = swap.querySelector('[data-gal-grid]');
  var more = swap.querySelector('[data-gal-next]');
  var nones = swap.querySelectorAll('[data-gal-none]');
  var said = doc.querySelector('[data-gal-say]');
  var segs = { show: doc.querySelector('[data-gal-show]'), sort: doc.querySelector('[data-gal-sort]') };
  var find = doc.querySelector('[data-gal-find]');
  var qBox = doc.querySelector('[data-gal-q]');
  var Pill = window.SocialPill;

  function pressed(key, dflt) {
    var b = segs[key] && segs[key].querySelector('button[aria-pressed="true"]');
    return b ? b.getAttribute('data-' + key) : dflt;
  }
  function tidy(words) { return String(words || '').replace(/\s+/g, ' ').trim().slice(0, 80); }
  /* What the tiles show, and what the person has picked since (the same
     until a pick is asked for and comes back). */
  var shown = { show: pressed('show', 'everyone'), sort: pressed('sort', 'new'), q: qBox ? tidy(qBox.defaultValue) : '' };
  var want = { show: shown.show, sort: shown.sort, q: shown.q };
  var turn = 0;

  function tell(text) {
    if (!said) return;
    said.textContent = text || '';
    said.hidden = !text;
  }
  function query(s, before) {
    var p = [];
    if (s.show !== 'everyone') p.push('show=' + encodeURIComponent(s.show));
    if (s.sort !== 'new') p.push('sort=' + encodeURIComponent(s.sort));
    if (s.q) p.push('q=' + encodeURIComponent(s.q));
    if (who) p.push('who=' + encodeURIComponent(who));
    if (before) p.push('before=' + encodeURIComponent(before));
    return p.length ? '?' + p.join('&') : '';
  }
  function ask(s, before) {
    if (blank && !s.q) return Promise.resolve({ html: '', next: null, people: '' });
    return fetch(url + query(s, before), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); });
  }
  /* Nothing to show says why, in its own words for the way of looking (a
     search that found people but no drawings says so of the drawings). */
  function empties() {
    var key = grid.children.length ? '' : who ? who
      : !shown.q ? (blank ? '' : shown.show) : (box && box.querySelector('.fp-row') ? 'search-people' : 'search');
    Array.prototype.forEach.call(nones, function (n) { n.hidden = n.getAttribute('data-gal-none') !== key; });
  }
  /* The tiles fade out (social.css, .gal-swap.is-out); this waits for them
     to be gone, however the fade ends. */
  function faded() {
    return new Promise(function (done) {
      var t = 0;
      function end() { clearTimeout(t); swap.removeEventListener('transitionend', on); done(); }
      function on(e) { if (e.target === swap && e.propertyName === 'opacity') end(); }
      swap.addEventListener('transitionend', on);
      t = setTimeout(end, 260);
      swap.classList.add('is-out');
    });
  }
  function putBack() {
    ['show', 'sort'].forEach(function (key) {
      var seg = segs[key], b = seg && seg.querySelector('button[data-' + key + '="' + shown[key] + '"]');
      if (b && b.getAttribute('aria-pressed') !== 'true') press(seg, b);
      want[key] = shown[key];
    });
  }
  function press(seg, b) {
    if (Pill) { Pill.choose(seg, b); return; }
    Array.prototype.forEach.call(seg.querySelectorAll('button'), function (x) {
      x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
    });
  }

  /* A new pick: its first page, in place of the tiles. */
  function load() {
    var s = { show: want.show, sort: want.sort, q: want.q };
    var n = ++turn;
    var y = window.SocialScroll.y();
    tell('');
    Promise.all([faded(), ask(s)]).then(function (res) {
      if (n !== turn) return;
      var j = res[1];
      /* Changed while they can't be seen, the page held at its height and
         its place, then faded back. */
      swap.style.minHeight = swap.offsetHeight + 'px';
      if (box) box.innerHTML = j.people || '';
      grid.innerHTML = j.html || '';
      shown = s;
      more.setAttribute('data-gal-next', j.next || '');
      more.hidden = !j.next;
      more.disabled = false;
      empties();
      swap.dispatchEvent(new CustomEvent('gal:swap', { detail: { q: s.q } }));
      if (window.history && history.replaceState) history.replaceState(history.state, '', page + query(s));
      if (window.SocialScroll.y() !== y) window.SocialScroll.to(y);
      requestAnimationFrame(function () {
        if (n !== turn) return;
        swap.classList.remove('is-out');
        setTimeout(function () { if (n === turn) swap.style.minHeight = ''; }, 260);
      });
    }, function () {
      if (n !== turn) return;
      putBack();
      swap.classList.remove('is-out');
      tell(WORDS.network);
    });
  }

  Object.keys(segs).forEach(function (key) {
    var seg = segs[key];
    if (!seg) return;
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-' + key + ']');
      if (!b || b.getAttribute('aria-pressed') === 'true') return;
      press(seg, b);
      want[key] = b.getAttribute('data-' + key);
      load();
    });
  });

  if (find && qBox) {
    var qTimer = 0;
    var search = function () {
      var words = tidy(qBox.value);
      if (words === want.q || (who && !words)) return;
      want.q = words;
      load();
    };
    find.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(qTimer); search(); });
    qBox.addEventListener('input', function () { clearTimeout(qTimer); qTimer = setTimeout(search, 350); });
    if (tidy(qBox.value) !== shown.q) search();
  }

  more.addEventListener('click', function () {
    var next = more.getAttribute('data-gal-next');
    if (!next || more.disabled) return;
    var n = turn;
    more.disabled = true;
    ask(shown, next).then(function (j) {
      if (n !== turn) return;
      var tmp = doc.createElement('div');
      tmp.innerHTML = j.html || '';
      Array.prototype.slice.call(tmp.children).forEach(function (c) { grid.appendChild(c); });
      more.setAttribute('data-gal-next', j.next || '');
      more.hidden = !j.next;
      more.disabled = false;
      empties();
    }, function () {
      if (n !== turn) return;
      more.disabled = false;
      tell(WORDS.network);
    });
  });
})();
