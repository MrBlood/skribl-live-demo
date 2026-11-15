/* MENTIONS: THE LIST UNDER AN @ (the map, part two, item 4; docs/SOCIAL-SITE.md
 * section 17; the owner's "All yes", Nov 15, to the mentions mock). One module
 * for both places words are written: the composer (compose.js) and a
 * comment's box, answers too (comments.js). mentions.py is its server side,
 * _mentions.html its markup; it says no words of its own.
 *
 * FROM THE @ ON, a list right under the line being typed, narrowing as you
 * type: the people you follow first, then anybody whose name or @handle
 * starts with what follows the @ (/people/suggest), four at most, each row
 * 52px, their face, their name and their @handle. It is placed, never laid
 * out in the page: nothing under it moves and the sheet is not pushed. With
 * no room under the line for it (a phone's comment sheet, sitting on the
 * keyboard), it opens above the line; with room neither way, under it, and
 * the words scroll to show it. So on a phone it stays above the keyboard.
 *
 * A TAP ON A ROW (or Enter or Tab on the highlighted one with a keyboard, the
 * arrow keys moving it, Esc closing the list) puts "@handle " in at the
 * caret, in place of what was typed after the @, and the field keeps its
 * focus and its keyboard: a press on the list never takes them. Esc closes
 * the list and leaves the sheet as it is; the list stays shut for that @
 * until another is typed.
 *
 * KIND, NEVER JUMPY: it fades in and out (social.css, .mn-list); under
 * Reduce Motion it is simply there, and simply gone.
 *
 * A SCREEN READER: the list is a listbox of options; the field says whether
 * it is open (aria-expanded) and which row is highlighted
 * (aria-activedescendant).
 *
 *   SocialMentions(field, list)  the field (a textarea) and its list (the
 *                                listbox under it, its data-mn-suggest the
 *                                list's address); returns { close, isOpen }.
 */
(function () {
  'use strict';
  var doc = document;
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  /* Between the line and the list. */
  var GAP = 8;
  /* Quiet typing before the list is asked for, so a word typed at speed asks
     once. */
  var WAIT = 120;
  /* A little longer than the list's fade (social.css). */
  var FADE_MS = 220;
  /* An @ being typed, before the caret: the @ with no letter, digit, _ or @
     right before it (not in an email address or another word), then the
     start of a handle, or nothing yet. */
  var TYPED = /(^|[^A-Za-z0-9_@])@([A-Za-z][A-Za-z0-9_]{0,19})?$/;
  var TAIL = /^[A-Za-z0-9_]*/;

  function still() { return !!(reduced && reduced.matches); }

  /* WHERE THE CARET'S LINE IS IN THE FIELD: a copy of the field, laid out as
     it lays its words (its width, padding, face, size and wrapping), its
     words up to the @ and then the rest from it; the rest's first line is
     the @'s, counted in whole lines (an inline box sits inside its line, by
     half its leading). {top, bottom} from the field's own top, its scroll
     taken off. The copy is in the page only while it is read. */
  var COPY = ['boxSizing', 'width', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'borderTopWidth',
              'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth', 'borderTopStyle', 'borderRightStyle',
              'borderBottomStyle', 'borderLeftStyle', 'fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
              'fontStretch', 'fontVariant', 'letterSpacing', 'lineHeight', 'textTransform', 'wordSpacing',
              'textIndent', 'tabSize', 'overflowWrap', 'wordBreak', 'whiteSpace'];
  function lineOf(field, index) {
    var cs = getComputedStyle(field);
    var mirror = doc.createElement('div');
    mirror.setAttribute('aria-hidden', 'true');
    mirror.className = 'mn-mirror';
    COPY.forEach(function (k) { mirror.style[k] = cs[k]; });
    mirror.textContent = field.value.slice(0, index);
    var rest = doc.createElement('span');
    rest.textContent = field.value.slice(index) || '@';
    mirror.appendChild(rest);
    doc.body.appendChild(mirror);
    var lh = parseFloat(cs.lineHeight);
    if (!(lh > 0)) lh = parseFloat(cs.fontSize) * 1.4;
    var pad = parseFloat(cs.paddingTop) || 0, edge = parseFloat(cs.borderTopWidth) || 0;
    var n = Math.max(0, Math.floor((rest.offsetTop - pad) / lh + 0.5));
    mirror.remove();
    var top = edge + pad + n * lh - field.scrollTop;
    return { top: top, bottom: top + lh };
  }

  /* What of the screen the list may use: the visual viewport (above a phone's
     keyboard), inside every box round the field that clips what it holds (the
     composer's words scroll inside its sheet). Also the nearest of those
     that scrolls, to show the list when it fits nowhere else. */
  function room(field) {
    var vv = window.visualViewport;
    var top = vv ? vv.offsetTop : 0, bottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    var scroller = null;
    for (var n = field.parentElement; n && n !== doc.body; n = n.parentElement) {
      var oy = getComputedStyle(n).overflowY;
      if (oy === 'visible') continue;
      var r = n.getBoundingClientRect();
      top = Math.max(top, r.top);
      bottom = Math.min(bottom, r.bottom);
      if (!scroller && (oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight) scroller = n;
    }
    return { top: top, bottom: bottom, scroller: scroller };
  }

  function attach(field, list) {
    if (!field || !list || !window.fetch) return null;
    var url = list.getAttribute('data-mn-suggest');
    var at = null;          // the @ being typed: { start, end, q }
    var rows = [];          // the people shown
    var active = -1;        // the highlighted row
    var shut = -1;          // an @ the list was closed on with Esc (its place)
    var timer = 0, hideTimer = 0, asked = 0;
    var cache = {};

    function isOpen() { return !list.hidden && list.classList.contains('is-open'); }

    /* The @ being typed at the caret, or null. What follows the caret and
       carries on the handle is replaced too ("@ju|no": all of it). */
    function token() {
      if (doc.activeElement !== field) return null;
      var v = field.value, s = field.selectionStart, e = field.selectionEnd;
      if (s !== e) return null;
      var m = TYPED.exec(v.slice(0, s));
      if (!m) return null;
      var typed = m[2] || '';
      var tail = TAIL.exec(v.slice(s))[0];
      if (!typed && tail && !/^[A-Za-z]/.test(tail)) tail = '';
      if (typed.length + tail.length > 20) return null;
      return { start: s - typed.length - 1, end: s + tail.length, q: typed.toLowerCase() };
    }

    function update() {
      var t = token();
      if (!t || t.start === shut) {
        if (!t) shut = -1;
        close();
        return;
      }
      shut = -1;
      at = t;
      clearTimeout(timer);
      if (Object.prototype.hasOwnProperty.call(cache, t.q)) { show(cache[t.q]); return; }
      timer = setTimeout(function () { ask(t.q); }, WAIT);
    }

    function ask(q) {
      var n = ++asked;
      fetch(url + '?q=' + encodeURIComponent(q), { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          var people = j && j.people ? j.people : null;
          if (people) cache[q] = people;
          if (n !== asked) return;
          var t = token();
          if (!t || t.q !== q || t.start === shut) return;
          at = t;
          show(people || []);
        }, function () { if (n === asked) close(); });
    }

    /* The rows, the first highlighted: built from the site's answer, the
       face its own markup (mentions.py renders it), the name and the
       @handle as text. */
    function show(people) {
      if (!people.length || !at) { close(); return; }
      rows = people;
      list.textContent = '';
      people.forEach(function (p, i) {
        var li = doc.createElement('li');
        li.className = 'mn-row';
        li.id = list.id + '-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', 'false');
        li.setAttribute('data-handle', p.handle);
        li.innerHTML = p.face || '';
        var who = doc.createElement('span');
        who.className = 'mn-who';
        var b = doc.createElement('b');
        b.className = 'mn-name';
        b.textContent = p.name;
        var h = doc.createElement('span');
        h.className = 'mn-handle';
        h.textContent = '@' + p.handle;
        who.appendChild(b);
        who.appendChild(h);
        li.appendChild(who);
        list.appendChild(li);
      });
      open();
      light(0);
      place();
    }

    function light(i) {
      active = i;
      Array.prototype.forEach.call(list.children, function (li, k) {
        li.setAttribute('aria-selected', k === i ? 'true' : 'false');
      });
      if (i >= 0 && list.children[i]) field.setAttribute('aria-activedescendant', list.children[i].id);
      else field.removeAttribute('aria-activedescendant');
    }

    /* Under the caret's line; above it where there is no room under it and
       there is above; under it otherwise, the words scrolling it into view. */
    function place() {
      if (!at || list.hidden) return;
      var host = list.offsetParent || list.parentNode;
      var line = lineOf(field, at.start);
      var fr = field.getBoundingClientRect(), hr = host.getBoundingClientRect();
      list.style.left = (fr.left - hr.left) + 'px';
      var h = list.offsetHeight, r = room(field);
      var top = fr.top + line.top, bottom = fr.top + line.bottom;
      var under = bottom + GAP + h <= r.bottom, over = top - GAP - h >= r.top;
      var y = (under || !over) ? bottom + GAP : top - GAP - h;
      list.style.top = (y - hr.top) + 'px';
      list.classList.toggle('is-above', !under && over);
      if (!under && !over && r.scroller) {
        var by = y + h - r.bottom;
        if (by > 0) r.scroller.scrollBy({ top: by, behavior: still() ? 'auto' : 'smooth' });
      }
    }

    function open() {
      clearTimeout(hideTimer);
      if (isOpen()) return;
      list.hidden = false;
      void list.offsetWidth;                 // laid out, then it fades in
      list.classList.add('is-open');
      field.setAttribute('aria-expanded', 'true');
    }

    function close() {
      clearTimeout(timer);
      asked++;
      if (list.hidden) return;
      list.classList.remove('is-open');
      field.setAttribute('aria-expanded', 'false');
      field.removeAttribute('aria-activedescendant');
      active = -1;
      clearTimeout(hideTimer);
      var done = function () { if (!list.classList.contains('is-open')) { list.hidden = true; list.textContent = ''; } };
      if (still()) done();
      else hideTimer = setTimeout(done, FADE_MS);
    }

    /* "@handle " in at the caret, in place of what was typed after the @; a
       space already there is kept as the space. The field keeps its focus;
       its own input handlers hear it (grow, the characters left, Post). */
    function choose(i) {
      var p = rows[i];
      if (!p || !at) return;
      var v = field.value, put = '@' + p.handle, end = at.end;
      var spaced = v.charAt(end) === ' ';
      if (!spaced) put += ' ';
      var max = +field.getAttribute('maxlength') || Infinity;
      if (v.length - (end - at.start) + put.length > max) { close(); return; }
      var caret = at.start + put.length + (spaced ? 1 : 0);
      close();
      field.focus({ preventScroll: true });
      field.setSelectionRange(at.start, end);
      var done = false;
      try { done = doc.execCommand('insertText', false, put); } catch (e) { done = false; }
      if (!done || field.value.slice(at.start, at.start + put.length) !== put) {
        field.value = v.slice(0, at.start) + put + v.slice(end);
        field.dispatchEvent(new Event('input', { bubbles: true }));
      }
      field.setSelectionRange(caret, caret);
      at = null;
    }

    field.addEventListener('input', update);
    field.addEventListener('click', update);
    /* The caret moved by a key: the list follows it (up and down move the
       highlight instead while it is open). */
    field.addEventListener('keyup', function (e) {
      if (/^(ArrowLeft|ArrowRight|Home|End)$/.test(e.key) || (/^(ArrowUp|ArrowDown)$/.test(e.key) && !isOpen())) update();
    });
    field.addEventListener('blur', function () { close(); });
    field.addEventListener('keydown', function (e) {
      if (!isOpen() || e.isComposing) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        var n = rows.length;
        light(((active < 0 ? (e.key === 'ArrowDown' ? -1 : 0) : active) + (e.key === 'ArrowDown' ? 1 : -1) + n) % n);
        return;
      }
      if ((e.key === 'Enter' || e.key === 'Tab') && !e.shiftKey && !e.altKey && !e.ctrlKey && !e.metaKey && active >= 0) {
        e.preventDefault();
        e.stopPropagation();
        choose(active);
        return;
      }
      if (e.key === 'Escape') {
        /* The list closes, and nothing else: the sheet, or a desk's fold,
           stays as it is. */
        e.preventDefault();
        e.stopPropagation();
        shut = at ? at.start : -1;
        close();
      }
    });
    /* A press on the list never takes the field's focus (or a phone's
       keyboard with it); the row is chosen on the click that follows. */
    list.addEventListener('mousedown', function (e) { e.preventDefault(); });
    list.addEventListener('click', function (e) {
      var li = e.target.closest ? e.target.closest('.mn-row') : null;
      if (!li) return;
      choose(Array.prototype.indexOf.call(list.children, li));
    });
    list.addEventListener('mousemove', function (e) {
      var li = e.target.closest ? e.target.closest('.mn-row') : null;
      var i = li ? Array.prototype.indexOf.call(list.children, li) : -1;
      if (i >= 0 && i !== active) light(i);
    });
    /* Kept under its line as the page, the sheet or a phone's keyboard move. */
    function again() { if (isOpen()) place(); }
    window.addEventListener('resize', again);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', again);
      window.visualViewport.addEventListener('scroll', again);
    }

    return { close: close, isOpen: isOpen };
  }

  window.SocialMentions = attach;
})();
