/* Help drawer search + live section counts.
 *
 * SHARED, DELIBERATELY, AND NOW THE ACCORDIONS TOO. The sections' open/close
 * handler was written twice, once in app.js and once in flip.js, driving the
 * same partial -- the duplication this file was first written to avoid
 * extending. It lives in init() below since v320 (outside audit V319-009):
 * a fix to how a section opens now lands on both editors or on neither. This publishes window.SkriblHelpSearch instead; both
 * surfaces call init() and get identical behaviour from one implementation.
 *
 * IT ALSO RETIRES A DRIFT SOURCE. Every accordion carried a hand-typed
 * "N tips" badge. Adding one tip made one of them wrong immediately, which is
 * the same class of failure as the editor's version string drifting nine
 * releases. Counts are now derived from the DOM, so they cannot disagree with
 * what is inside — and during a search they show MATCHES rather than totals,
 * which is more useful information from the same pixels.
 *
 * Degrades safely: if the drawer or the search field is absent, init() returns
 * and the accordions behave exactly as they did before.
 */
(function (global) {
  'use strict';

  function textOf(el) {
    return (el.textContent || '').toLowerCase();
  }

  /* EVERYDAY COUSINS (Ask, after v323: "ask in your own words"). A query is
     also each word people use for the same thing, so "repeat" finds the loop
     entries and "picture" the photo ones. Words, not sentences: this is a
     list, not a chatbot, and it never leaves the page. Each row is one idea;
     a query that is any word of a row (or starts one, from three letters)
     matches entries holding any word of it. */
  var COUSINS = [
    ['loop', 'repeat', 'again and again', 'forever'],
    ['music', 'song', 'sound', 'audio', 'track'],
    ['speed', 'faster', 'slower', 'slow', 'fast', 'time-lapse', 'timelapse'],
    ['photo', 'picture', 'image', 'background', 'trace'],
    ['post', 'share', 'link', 'publish', 'send'],
    ['export', 'download', 'gif', 'video', 'mp4', 'png'],
    ['save', 'draft', 'keep', 'backup'],
    ['undo', 'mistake', 'oops', 'take back'],
    ['colour', 'color', 'paint'],
    ['size', 'thick', 'thin', 'bigger', 'smaller'],
    ['erase', 'eraser', 'rub out', 'delete'],
    ['take', 'record', 'again'],
    ['page', 'frame', 'animate', 'animation', 'move', 'flipbook'],
    ['new', 'start', 'blank', 'fresh', 'clear']
  ];
  function cousins(q) {
    var out = [q];
    if (q.length < 3) return out;
    COUSINS.forEach(function (row) {
      if (row.some(function (w) { return w === q || w.indexOf(q) === 0; })) {
        row.forEach(function (w) { if (out.indexOf(w) < 0) out.push(w); });
      }
    });
    return out;
  }

  // Highlighting rewrites innerHTML, so the original markup has to be kept
  // somewhere restorable. Reading it back out of the DOM after a highlight
  // would re-capture the <mark> wrappers and compound them on every keystroke.
  function cacheOriginal(items) {
    items.forEach(function (it) {
      if (it.dataset.helpOrig === undefined) it.dataset.helpOrig = it.innerHTML;
    });
  }

  function restore(items) {
    items.forEach(function (it) {
      if (it.dataset.helpOrig !== undefined) it.innerHTML = it.dataset.helpOrig;
    });
  }

  function highlight(item, needle) {
    var html = item.dataset.helpOrig;
    if (!needle) { item.innerHTML = html; return; }
    // Walk text nodes only. A naive string replace would corrupt tag names and
    // attribute values the moment a query matched one of them ("p", "s", "div").
    item.innerHTML = html;
    var walker = document.createTreeWalker(item, NodeFilter.SHOW_TEXT, null);
    var nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      var lower = node.nodeValue.toLowerCase();
      var i = lower.indexOf(needle);
      if (i < 0) return;
      var frag = document.createDocumentFragment();
      var pos = 0;
      while (i >= 0) {
        frag.appendChild(document.createTextNode(node.nodeValue.slice(pos, i)));
        var mk = document.createElement('mark');
        mk.className = 'help-hit';
        mk.textContent = node.nodeValue.slice(i, i + needle.length);
        frag.appendChild(mk);
        pos = i + needle.length;
        i = lower.indexOf(needle, pos);
      }
      frag.appendChild(document.createTextNode(node.nodeValue.slice(pos)));
      node.parentNode.replaceChild(frag, node);
    });
  }

  function init(opts) {
    opts = opts || {};
    var drawer = document.getElementById(opts.drawerId || 'helpDrawer');
    if (!drawer) return null;
    var input = drawer.querySelector('#helpSearch');
    var countEl = drawer.querySelector('#helpSearchCount');
    var emptyEl = drawer.querySelector('#helpEmpty');
    var headers = [].slice.call(drawer.querySelectorAll('.accordion-header'));
    if (!headers.length) return null;
    // Tap a header to open or close its section. Several can be open at once:
    // this is a reference, not a wizard.
    headers.forEach(function (header) {
      header.addEventListener('click', function () {
        var body = header.nextElementSibling;
        var isOpen = header.classList.toggle('open');
        header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        if (body && body.classList.contains('accordion-body')) body.classList.toggle('open', isOpen);
        if (isOpen) fitSoon();
      });
    });

    // MORE (How it works layout 1, after v323): each entry shows its first
    // two lines, and More shows the rest. The words stay in .help-desc, all of
    // them, so search finds them and every check reading an entry still does;
    // only the drawing is clamped. Added before the markup is cached, so a
    // highlight that rewrites an entry keeps its button; clicks are heard on
    // the drawer for the same reason.
    [].slice.call(drawer.querySelectorAll('.help-tip')).forEach(function (tip) {
      if (tip.querySelector('.help-more')) return;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'help-more';
      b.textContent = 'More';
      b.setAttribute('aria-expanded', 'false');
      tip.appendChild(b);
    });
    // Only while How it works is open, and once a frame at most: it reads
    // every entry's layout, and run on each resize with the panel shut it
    // held up the editors (Flip's Play disc began its fade late).
    var fitting = false;
    function fitSoon() {
      if (fitting || drawer.hidden) return;
      fitting = true;
      requestAnimationFrame(function () { fitting = false; fitMore(); });
    }
    /* EVERY ENTRY IS READ FIRST, THEN WRITTEN, and only what changed (main
     * red after #571: How it works jumped 59% of its rise in one frame). It
     * wrote each More's word and then read the next entry's height, so the
     * browser worked out the page's style again once an entry, and once more
     * for each new label lib/labels.js wrapped: 150 to 165 times as it began
     * to rise, 120-170 ms in one go here and about a second on a phone-slow
     * processor (verify_helpdemos counts them). */
    function fitMore() {
      if (drawer.hidden) return;
      var seen = [].slice.call(drawer.querySelectorAll('.help-tip')).map(function (tip) {
        var b = tip.querySelector('.help-more'), d = tip.querySelector('.help-desc');
        if (!b || !d) return null;
        var open = tip.classList.contains('is-open');
        // A rendered entry whose words all fit has nothing more to show.
        return { b: b, open: open, fits: !open && d.clientHeight ? d.scrollHeight <= d.clientHeight + 1 : null };
      });
      seen.forEach(function (s) {
        if (!s) return;
        var word = s.open ? 'Less' : 'More';
        if (s.b.textContent !== word) s.b.textContent = word;
        if (s.b.getAttribute('aria-expanded') !== String(s.open)) s.b.setAttribute('aria-expanded', String(s.open));
        if (s.fits !== null && s.b.hidden !== s.fits) s.b.hidden = s.fits;
      });
    }
    drawer.addEventListener('click', function (e) {
      var b = e.target.closest('.help-more');
      if (!b) return;
      var tip = b.closest('.help-tip');
      tip.classList.toggle('is-open');
      fitMore();
    });
    drawer.addEventListener('helptab', fitSoon);
    global.addEventListener('resize', fitSoon);

    var sections = headers.map(function (h) {
      var body = h.nextElementSibling;
      while (body && !body.classList.contains('accordion-body')) body = body.nextElementSibling;
      var items = body ? [].slice.call(body.querySelectorAll('.help-tip, .help-step')) : [];
      cacheOriginal(items);
      return {
        header: h,
        body: body,
        badge: h.querySelector('.accordion-count'),
        items: items,
        wasOpen: h.classList.contains('open')
      };
    });

    var total = sections.reduce(function (a, s) { return a + s.items.length; }, 0);

    function setOpen(sec, open) {
      sec.header.classList.toggle('open', open);
      sec.header.setAttribute('aria-expanded', String(open));
      if (sec.body) sec.body.classList.toggle('open', open);
    }

    function apply() {
      var q = input ? input.value.trim().toLowerCase() : '';
      var words = q ? cousins(q) : [];
      var shown = 0;

      sections.forEach(function (sec) {
        var hits = 0;
        sec.items.forEach(function (item) {
          var text = textOf(item);
          // What was typed matches anywhere in a word; a cousin only as a whole
          // word ("repeat" must not find "repeated passes" for "loop").
          var hit = !q ? '' : (words.filter(function (w, k) {
            return k === 0 ? text.indexOf(w) >= 0 : new RegExp('\\b' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b').test(text);
          })[0] || null);
          var match = !q || hit !== null;
          item.hidden = !match;
          // A match is shown whole: the words it matched may be past two lines.
          item.classList.toggle('is-searching', !!q && match);
          if (match) { hits++; highlight(item, hit || q); }
        });
        shown += hits;
        sec.header.hidden = q ? hits === 0 : false;
        if (sec.body) sec.body.hidden = q ? hits === 0 : false;
        // The badge counts what is VISIBLE. Deriving it removes the hand-typed
        // number that drifted the moment a tip was added.
        if (sec.badge) sec.badge.textContent = q ? String(hits) : (hits + (hits === 1 ? ' tip' : ' tips'));
        if (q) setOpen(sec, hits > 0);
        else setOpen(sec, sec.wasOpen);
      });

      if (!q) restoreAll();
      if (countEl) {
        countEl.textContent = q
          ? (shown + ' of ' + total + (total === 1 ? ' entry' : ' entries'))
          : (total + ' entries in ' + sections.length + ' sections');
      }
      if (emptyEl) emptyEl.hidden = !(q && shown === 0);
      fitSoon();
      return shown;
    }

    function restoreAll() {
      sections.forEach(function (sec) { restore(sec.items); });
    }

    if (input) {
      input.addEventListener('input', apply);
      input.addEventListener('keydown', function (e) {
        // Esc clears a query first and only closes the drawer when empty, so a
        // search is never one keypress away from losing the whole panel.
        if (e.key === 'Escape' && input.value) { e.stopPropagation(); input.value = ''; apply(); }
      });
    }

    // '/' and Cmd/Ctrl-K focus the field, but only while the drawer is open —
    // otherwise '/' would be stolen from anything else that wants a keystroke.
    document.addEventListener('keydown', function (e) {
      if (drawer.hidden || !input) return;
      var typing = document.activeElement === input;
      if ((e.key === '/' && !typing) || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });

    apply();
    return { apply: apply, reset: function () { if (input) input.value = ''; apply(); }, total: total };
  }

  global.SkriblHelpSearch = { init: init, cousins: cousins };
})(window);
