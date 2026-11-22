/* SEARCH'S RECENT SEARCHES (the owner's "Yes to all", Nov 22, to round two
 * of the "Blooby and Search" mock; search.html, gallery.py search_page).
 *
 * Before a search, Search shows what this person searched lately, newest
 * first: the people they opened from what it found and the words they
 * searched, an × on each and Clear all above them. Nothing searched yet:
 * one quiet line. KEPT ON THIS PHONE ALONE (localStorage, a list for each
 * person signed in here and one for nobody, [data-recent-key]), never sent
 * anywhere: the site never learns them.
 *
 * WHAT COUNTS. Words searched with the keyboard's Search (or Enter), or
 * that found something then opened (a drawing, See all). A person opened
 * from what was found, or from this list. Ten at most; the same words (in
 * any case) or the same person again goes back to the top.
 *
 * A recent person is a link to their page; recent words search again, here,
 * in place. An × takes its row away; a keyboard's focus goes on to the next
 * row's × (the box when none is left), and a screen reader hears what went.
 *
 * KIND, NEVER JUMPY: the list is inside the part of the page that fades
 * (explore.js), and it goes in or out only while that cannot be seen, when
 * explore.js says what it shows ('gal:swap'). It waits hidden until this
 * file has read the phone, so the quiet line never shows and then turns
 * into the list. Storage refused (a private window) is a list of nothing:
 * the quiet line, and nothing kept.
 *
 * The words are the page's (search.html's data-* words): this file says
 * nothing of its own.
 */
(function () {
  'use strict';
  var doc = document;
  var swap = doc.querySelector('[data-gal-swap]');
  var find = doc.querySelector('[data-gal-find]');
  var qBox = doc.querySelector('[data-gal-q]');
  if (!swap || !find || !qBox || !swap.hasAttribute('data-recent-key')) return;
  var KEY = swap.getAttribute('data-recent-key');
  var MOST = 10;
  var page = swap.getAttribute('data-explore') || location.pathname;
  var root = doc.querySelector('[data-recent]');
  var list = root && root.querySelector('[data-recent-list]');
  var clear = root && root.querySelector('[data-recent-clear]');
  var none = doc.querySelector('[data-recent-none]');
  var said = doc.querySelector('[data-recent-said]');
  var tWords = doc.querySelector('template[data-recent-words]');
  var tPerson = doc.querySelector('template[data-recent-person]');
  var HANDLE = /^[A-Za-z][A-Za-z0-9_]{2,19}$/;
  var FRAME = /^--skribl-face-[wxy]$/;
  var AMOUNT = /^-?\d{1,5}(\.\d{1,4})?%$/;

  function tidy(words) { return String(words || '').replace(/\s+/g, ' ').trim().slice(0, 80); }
  /* A path on this site, and nothing else. */
  function path(u) { return typeof u === 'string' && u.length <= 300 && /^\/(?![\/\\])[^\s\\]*$/.test(u) ? u : ''; }
  function fill(words, what) { return String(words || '').replace('{}', what); }

  /* The list as kept: only rows this file writes, so a list gone strange is
     read as far as it is good. */
  function read() {
    var got;
    try { got = JSON.parse(window.localStorage.getItem(KEY) || '[]'); } catch (e) { got = []; }
    if (!Array.isArray(got)) return [];
    return got.filter(function (r) {
      return !!r && ((r.t === 'q' && typeof r.q === 'string' && !!tidy(r.q))
                     || (r.t === 'p' && typeof r.h === 'string' && HANDLE.test(r.h) && !!path(r.u)
                         && typeof r.n === 'string'));
    }).slice(0, MOST);
  }
  function keep(rows) {
    try { window.localStorage.setItem(KEY, JSON.stringify(rows.slice(0, MOST))); } catch (e) { /* this visit only */ }
  }
  function same(a, b) {
    return a.t === b.t && (a.t === 'q' ? a.q.toLowerCase() === b.q.toLowerCase()
                                       : a.h.toLowerCase() === b.h.toLowerCase());
  }
  function add(r) {
    if (!r) return;
    var rows = read().filter(function (x) { return !same(x, r); });
    rows.unshift(r);
    keep(rows);
  }
  function drop(r) { keep(read().filter(function (x) { return !same(x, r); })); }

  /* A person as their row shows them: their page, name, @handle, and their
     face's still picture with the frame the server gave it. */
  function personOf(a) {
    var u = path(a.getAttribute('href'));
    var n = a.querySelector('.fp-words b'), h = a.querySelector('.fp-words span');
    var handle = h ? h.textContent.trim().replace(/^@/, '') : '';
    if (!u || !HANDLE.test(handle)) return null;
    var r = { t: 'p', h: handle, n: tidy(n ? n.textContent : handle), u: u };
    var face = a.querySelector('.skribl-face'), img = face && face.querySelector('img');
    var src = img ? path(img.getAttribute('src')) : '';
    if (src) {
      r.f = src;
      r.v = {};
      ['--skribl-face-w', '--skribl-face-x', '--skribl-face-y'].forEach(function (k) {
        var v = face.style.getPropertyValue(k).trim();
        if (AMOUNT.test(v)) r.v[k] = v;
      });
    }
    return r;
  }

  /* What the page shows now, by its address (explore.js keeps it so). */
  function shownWords() {
    try { return tidy(new URLSearchParams(location.search).get('q')); } catch (e) { return ''; }
  }

  /* RECORDING, on Search and on its See all alike. */
  find.addEventListener('submit', function () {
    var q = tidy(qBox.value);
    if (q) add({ t: 'q', q: q });
  });
  swap.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !swap.contains(a) || (root && root.contains(a))) return;
    if (a.matches('.fp-row .fp-who')) { add(personOf(a)); return; }
    var q = shownWords();
    if (q) add({ t: 'q', q: q });
  });

  if (!root || !list || !clear || !none || !tWords || !tPerson) return;

  function row(r) {
    var li = (r.t === 'p' ? tPerson : tWords).content.firstElementChild.cloneNode(true);
    var a = li.querySelector('a'), x = li.querySelector('.rs-x');
    li._recent = r;
    if (r.t === 'q') {
      a.setAttribute('href', page + '?q=' + encodeURIComponent(r.q));
      li.querySelector('.rs-words').textContent = r.q;
      x.setAttribute('aria-label', fill(x.getAttribute('data-label'), '“' + r.q + '”'));
      return li;
    }
    a.setAttribute('href', r.u);
    var ring = li.querySelector('.face-ring');
    function circle() {
      var blank = doc.createElement('span');
      blank.className = 'face-blank';
      blank.setAttribute('aria-hidden', 'true');
      ring.textContent = '';
      ring.classList.add('is-blank');
      ring.appendChild(blank);
    }
    if (r.f) {
      var f = doc.createElement('span');
      f.className = 'skribl-face';
      f.setAttribute('aria-hidden', 'true');
      f.setAttribute('data-skribl-face', '');
      f.setAttribute('data-play', 'still');
      Object.keys(r.v || {}).forEach(function (k) {
        if (FRAME.test(k) && AMOUNT.test(r.v[k])) f.style.setProperty(k, r.v[k]);
      });
      var img = doc.createElement('img');
      img.className = 'skribl-face-still';
      img.alt = '';
      img.decoding = 'async';
      /* A picture that cannot be had (the phone offline): the empty
         circle, never a broken picture. (A face gone from the site comes
         back as Skribl's own blank paper, from the same address.) */
      img.addEventListener('error', circle);
      img.src = r.f;
      f.appendChild(img);
      ring.appendChild(f);
    } else {
      circle();
    }
    li.querySelector('.fp-words b').textContent = r.n;
    li.querySelector('.fp-words span').textContent = '@' + r.h;
    x.setAttribute('aria-label', fill(x.getAttribute('data-label'), r.n));
    return li;
  }
  function show() {
    var rows = read();
    list.textContent = '';
    rows.forEach(function (r) { list.appendChild(row(r)); });
    root.hidden = !rows.length;
    none.hidden = !!rows.length;
  }
  function hide() { root.hidden = true; none.hidden = true; }
  function tell(text) { if (said) said.textContent = text || ''; }

  /* What the page shows: the server's words in the box, then each swap. */
  if (tidy(qBox.defaultValue)) hide(); else show();
  swap.addEventListener('gal:swap', function (e) {
    if (e.detail && e.detail.q) hide(); else show();
  });
  /* Back from a person's page: the list as it is now (they went to the top). */
  window.addEventListener('pageshow', function (e) {
    if (e.persisted && !tidy(qBox.value) && !shownWords()) show();
  });

  list.addEventListener('click', function (e) {
    var li = e.target.closest ? e.target.closest('li') : null;
    if (!li || !li._recent) return;
    var r = li._recent, x = e.target.closest('.rs-x');
    if (x) {
      var had = doc.activeElement === x;
      var next = li.nextElementSibling || li.previousElementSibling;
      drop(r);
      li.remove();
      if (!list.children.length) { root.hidden = true; none.hidden = false; }
      tell(fill(said && said.getAttribute('data-gone'), r.t === 'q' ? '“' + r.q + '”' : r.n));
      if (had) (next ? next.querySelector('.rs-x') : qBox).focus();
      return;
    }
    if (r.t === 'p') { add(r); return; }
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    qBox.value = r.q;
    if (find.requestSubmit) find.requestSubmit();
    else find.dispatchEvent(new Event('submit', { cancelable: true }));
  });
  clear.addEventListener('click', function () {
    var had = doc.activeElement === clear;
    keep([]);
    list.textContent = '';
    root.hidden = true;
    none.hidden = false;
    tell(said && said.getAttribute('data-cleared'));
    if (had) qBox.focus();
  });
})();
