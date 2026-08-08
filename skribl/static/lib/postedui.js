/* Your Skribls — rendering. The store is lib/posted.js; this draws it.
 *
 * SHARED because the alternative is two copies. app.js and flip.js already
 * duplicate their accordion handlers and their drawer controllers, and that
 * duplication is the project's largest known-open. Both surfaces call
 * SkriblPostedUI.init() and get identical behaviour from one implementation.
 *
 * Degrades to nothing if the partial is absent: init() returns and the editor
 * is unaffected.
 */
(function (global) {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function init(opts) {
    opts = opts || {};
    var store = global.SkriblPosted;
    var drawer = document.getElementById('postedDrawer');
    if (!store || !drawer) return null;

    var listEl = document.getElementById('postedList');
    var countEl = document.getElementById('postedCount');
    var searchEl = document.getElementById('postedSearch');
    var clearEl = document.getElementById('postedClear');
    var backdrop = document.getElementById('postedBackdrop');
    var closeEl = document.getElementById('postedClose');

    function open() {
      drawer.hidden = false;
      drawer.classList.add('open');
      render();
      if (searchEl) setTimeout(function () { try { searchEl.focus(); } catch (e) {} }, 40);
    }

    function close() {
      drawer.classList.remove('open');
      drawer.hidden = true;
      if (searchEl) searchEl.value = '';
    }

    function copy(text, btn) {
      function done() {
        var was = btn.dataset.label || btn.textContent;
        btn.dataset.label = was;
        btn.textContent = 'Copied';
        btn.classList.add('done');
        // A timer per button: two quick copies on different rows would
        // otherwise leave the first stuck reading "Copied".
        clearTimeout(btn._t);
        btn._t = setTimeout(function () {
          btn.textContent = btn.dataset.label;
          btn.classList.remove('done');
        }, 1400);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
      } else {
        fallback(text, done);
      }
    }

    // execCommand needs a real selection, and a detached input is not focusable
    // on iOS — so the field is attached, read-only, and off-screen rather than
    // display:none, which would make it unselectable.
    function fallback(text, done) {
      var t = document.createElement('input');
      t.setAttribute('readonly', '');
      t.value = text;
      t.style.cssText = 'position:fixed;top:-1000px;left:0;opacity:0';
      document.body.appendChild(t);
      t.select();
      try { document.execCommand('copy'); done(); } catch (e) {}
      t.remove();
    }

    function render() {
      var all = store.list();
      var q = (searchEl && searchEl.value.trim().toLowerCase()) || '';
      var hits = all.filter(function (e) {
        return !q || (e.title || '').toLowerCase().indexOf(q) >= 0;
      });

      if (countEl) {
        countEl.textContent = !all.length ? ''
          : q ? (hits.length + ' of ' + all.length)
              : (all.length + (all.length === 1 ? ' Skribl' : ' Skribls'));
      }
      if (clearEl) clearEl.hidden = !all.length;

      if (!all.length) {
        // An invitation, not an apology: this screen is what a new tester sees.
        listEl.innerHTML =
          '<div class="posted-empty">' +
          '<div class="posted-empty-title">Nothing posted yet</div>' +
          '<div class="posted-empty-sub">Draw something and hit Post &mdash; ' +
          'the link will show up here so you can find it again.</div></div>';
        return;
      }
      if (!hits.length) {
        listEl.innerHTML =
          '<div class="posted-empty">' +
          '<div class="posted-empty-title">Nothing matches that</div>' +
          '<div class="posted-empty-sub">Try part of a title.</div></div>';
        return;
      }

      listEl.innerHTML = hits.map(function (e) {
        var sub = (e.kind === 'flip'
          ? (e.pages + (e.pages === 1 ? ' page' : ' pages'))
          : 'replay') + ' \u00b7 ' + store.ago(e.at);
        // NO route literal. A '/s/' fallback here is exactly what v132 removed
        // from flip.js: it silently posts the wrong URL under a url_prefix, and
        // verify_seam.py exists to catch it. The stored entry carries the url
        // the SERVER returned; if it is missing, fall back to the injected
        // player base, never to a hand-written path.
        var base = global.SKRIBL_PLAYER_BASE || '';
        var url = store.absolute(e.url || (base ? base + '/' + e.id : ''));
        return '<div class="posted-row" data-id="' + esc(e.id) + '">' +
          '<span class="posted-thumb posted-thumb-' + esc(e.kind) + '" aria-hidden="true">' +
            (e.kind === 'flip' ? '\u25A6' : '\u270E') + '</span>' +
          '<a class="posted-main" href="' + esc(url) + '" target="_blank" rel="noopener">' +
            '<span class="posted-title">' + esc(e.title || 'Untitled Skribl') + '</span>' +
            '<span class="posted-sub">' + esc(sub) + '</span>' +
          '</a>' +
          '<button type="button" class="posted-copy" data-url="' + esc(url) + '">Copy link</button>' +
          '<button type="button" class="posted-del" data-del="' + esc(e.id) + '" ' +
            'aria-label="Remove from this list">\u2715</button>' +
        '</div>';
      }).join('');
    }

    listEl.addEventListener('click', function (ev) {
      var c = ev.target.closest('.posted-copy');
      if (c) { copy(c.dataset.url, c); return; }
      var d = ev.target.closest('.posted-del');
      if (d) {
        // Removes the entry, NOT the Skribl. The link keeps working, which is
        // why this is not a confirm dialog — nothing is destroyed.
        store.remove(d.dataset.del);
        render();
      }
    });

    if (searchEl) searchEl.addEventListener('input', render);
    if (searchEl) searchEl.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && searchEl.value) {
        e.stopPropagation(); searchEl.value = ''; render();
      }
    });
    if (closeEl) closeEl.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);
    if (clearEl) clearEl.addEventListener('click', function () {
      if (clearEl.dataset.armed === '1') {
        store.clear(); clearEl.dataset.armed = ''; clearEl.textContent = 'Clear list'; render();
      } else {
        // Armed rather than a dialog, matching Flip's delete affordance.
        clearEl.dataset.armed = '1';
        clearEl.textContent = 'Tap again to clear';
        setTimeout(function () {
          clearEl.dataset.armed = ''; clearEl.textContent = 'Clear list';
        }, 3000);
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !drawer.hidden && (!searchEl || !searchEl.value)) close();
    });

    render();
    return { open: open, close: close, render: render };
  }

  global.SkriblPostedUI = { init: init };
})(window);
