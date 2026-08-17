/* Help drawer search + live section counts.
 *
 * SHARED, DELIBERATELY. The accordion open/close handler is written twice —
 * app.js:1779 and flip.js:2168 — driving the same partial. That duplication is
 * the project's largest known-open, and adding search to both files would have
 * made a third copy of it. This publishes window.SkriblHelpSearch instead; both
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
      var shown = 0;

      sections.forEach(function (sec) {
        var hits = 0;
        sec.items.forEach(function (item) {
          var match = !q || textOf(item).indexOf(q) >= 0;
          item.hidden = !match;
          if (match) { hits++; highlight(item, q); }
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

  global.SkriblHelpSearch = { init: init };
})(window);
