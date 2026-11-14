/* A profile's tabs (the map's step 4, docs/SOCIAL-SITE.md section 16; the
 * owner's "Yes" to its mock, Nov 14): Posts · Gallery · Likes · Drafts on
 * your own page, Posts · Gallery on anybody else's (social/_profile.html).
 * profiles.py says what each holds and for whom.
 *
 * EACH TAB IS A LINK WITH ITS OWN ADDRESS. A tap stays on the page: the
 * pen's line glides under the tab (social.css places it by the tab's place,
 * --at), the tab takes the first ink, the panel fades out, the tab's first
 * page goes in while it can't be seen (/@<handle>/more), and fades back;
 * then the address is the tab's own (history.pushState), so the back button
 * comes back to the tab before, and a reload or a shared link opens on it.
 * With Ctrl, ⌘ or Shift, or the middle button, a tab opens as a link does;
 * without this file each tab is a page of its own.
 *
 * LOAD MORE brings a tab's next page in place, by its cursor; the players
 * are mounted and the times said, as Home's Load more does.
 *
 * KIND, NEVER JUMPY: the line glides and the panel fades, nothing else
 * moves. The page doesn't scroll: the panel keeps its height while the new
 * one fades in, and then keeps whatever room holds the page where it is (a
 * short tab under a page scrolled to its strip), so nothing hops. Under
 * Reduce Motion the line is put there and the panel still only fades. Only
 * the newest answer is shown, so a slow one never puts back a tab the person
 * has left; a tab that cannot be had puts the strip back to what the panel
 * shows and says so, kindly.
 *
 * The words are the page's ([data-tab-words]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var strip = doc.querySelector('[data-prof-tabs]');
  var swap = doc.querySelector('[data-prof-swap]');
  var url = swap && swap.getAttribute('data-more');
  if (!strip || !swap || !url) return;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-tab-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  var said = doc.querySelector('[data-page-say]');
  var tabs = Array.prototype.slice.call(strip.querySelectorAll('a[data-tab]'));
  var turn = 0;

  function tell(text) {
    if (!said) return;
    said.textContent = text || '';
    said.hidden = !text;
  }
  function keyOf(a) { return a ? a.getAttribute('data-tab') : null; }
  function tabNamed(key) { return tabs.filter(function (a) { return keyOf(a) === key; })[0] || null; }
  /* What the panel shows, and what the strip says (the same, but while a
     tab is on its way). */
  function shown() {
    var p = swap.querySelector('[data-prof-panel]');
    return p ? p.getAttribute('data-tab') : null;
  }
  function chosen() { return keyOf(strip.querySelector('a[aria-current]')); }

  /* The strip says `key`: its ink, and the pen's place, which glides there
     (social.css; put there under Reduce Motion). */
  function mark(key) {
    tabs.forEach(function (a, i) {
      if (keyOf(a) === key) {
        a.setAttribute('aria-current', 'page');
        strip.style.setProperty('--at', String(i));
      } else a.removeAttribute('aria-current');
    });
  }

  function ask(key, before) {
    return fetch(url + '?tab=' + encodeURIComponent(key) + (before ? '&before=' + encodeURIComponent(before) : ''),
                 { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); });
  }

  /* What comes in later is met as the page's first was: times said in the
     person's own (social.js), drawings mounted as Skribl asks of a feed. */
  function settle(root) {
    if (window.SocialWhen) window.SocialWhen(root);
    if (window.SkriblInline) window.SkriblInline.mount(root);
  }

  /* The panel fades out (social.css, .prof-swap.is-out); this waits for it
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

  /* The height held over the change, let go: down to the new panel's own,
     but never below what keeps the page where it is. */
  function letGo() {
    var p = swap.querySelector('[data-prof-panel]');
    var own = p ? Math.ceil(p.getBoundingClientRect().height) : 0;
    var rest = doc.documentElement.scrollHeight - swap.offsetHeight;
    var need = Math.ceil(window.scrollY + window.innerHeight - rest);
    swap.style.minHeight = need > own ? need + 'px' : '';
  }

  /* `key`'s first page, in place of the panel; `push` when it is a tap (the
     back button's own is already where it goes). */
  function go(key, push) {
    var a = tabNamed(key);
    if (!a) return;
    var n = ++turn;
    var y = window.scrollY;
    tell('');
    mark(key);
    Promise.all([faded(), ask(key)]).then(function (res) {
      if (n !== turn) return;
      var j = res[1];
      /* Changed while it can't be seen, the page held at its height and its
         place, then faded back. */
      swap.style.minHeight = swap.offsetHeight + 'px';
      swap.innerHTML = j.html || '';
      settle(swap);
      if (push && window.history && history.pushState) history.pushState({ profTab: key }, '', a.href);
      if (window.scrollY !== y) window.scrollTo(0, y);
      requestAnimationFrame(function () {
        if (n !== turn) return;
        swap.classList.remove('is-out');
        setTimeout(function () { if (n === turn) letGo(); }, 260);
      });
    }, function () {
      if (n !== turn) return;
      var was = shown();
      mark(was);
      /* The back button's own move: the address goes back to what is shown. */
      if (!push && window.history && history.replaceState && tabNamed(was)) {
        history.replaceState({ profTab: was }, '', tabNamed(was).href);
      }
      swap.classList.remove('is-out');
      tell(WORDS.network);
    });
  }

  strip.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-tab]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (keyOf(a) === chosen() && keyOf(a) === shown()) return;
    go(keyOf(a), true);
  });

  /* THE BACK BUTTON (and forward): the tab the address names. */
  window.addEventListener('popstate', function () {
    var here = window.location.pathname.toLowerCase();
    var a = tabs.filter(function (t) { return t.pathname.toLowerCase() === here; })[0];
    if (!a || (keyOf(a) === chosen() && keyOf(a) === shown())) return;
    go(keyOf(a), false);
  });

  /* LOAD MORE, in whichever tab is shown. */
  swap.addEventListener('click', function (e) {
    var more = e.target.closest('[data-prof-next]');
    if (!more) return;
    var next = more.getAttribute('data-prof-next');
    var list = swap.querySelector('[data-prof-list]');
    if (!next || more.disabled || !list) return;
    var n = turn;
    more.disabled = true;
    ask(shown(), next).then(function (j) {
      if (n !== turn) return;
      var box = doc.createElement('div');
      box.innerHTML = j.html || '';
      Array.prototype.slice.call(box.children).forEach(function (c) { list.appendChild(c); });
      settle(list);
      more.setAttribute('data-prof-next', j.next || '');
      more.hidden = !j.next;
      more.disabled = false;
    }, function () {
      if (n !== turn) return;
      more.disabled = false;
      tell(WORDS.network);
    });
  });
})();
