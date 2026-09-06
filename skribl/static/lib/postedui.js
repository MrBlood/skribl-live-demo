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

  /* The SAME open-book that opens Flip from Pad's header. The tray used the
   * glyph U+25A6 (a hatched square), which meant nothing and matched nothing —
   * a Flip is identified by the book everywhere else in the app, so the tray
   * disagreeing with the header is a small lie about what the thing is.
   *
   * Inline SVG rather than a character: the two glyphs rendered at whatever
   * weight and baseline the system font felt like, which is why they sat
   * unevenly against each other.
   */
  var ICON_FLIP =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"' +
    ' stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 6.5C9.5 4.9 6.4 4.6 3 5.2v13c3.4-.6 6.5-.3 9 1.3 2.5-1.6 5.6-1.9 9-1.3v-13c-3.4-.6-6.5-.3-9 1.3z"/>' +
    '<path d="M12 6.5v13.3"/></svg>';

  /* Pencil, mirrored to point down-left. The glyph it replaces (U+270E) leans
   * the opposite way to every other pencil in the app — the Pen tool, the
   * "Start drawing" hint — so a Pad Skribl was marked with a pencil facing
   * away from the one the user just drew with. */
  var ICON_PAD =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"' +
    ' stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M17 3.5a2.1 2.1 0 0 1 3 3L8.5 18 4 20l2-4.5z"/></svg>';

  /* The entry, so the click handler works from stored state rather than from
     what the DOM happens to say. */
  function byId(id) {
    /* global.SkriblPosted.list(), not a captured `store`: this helper sits at
       module scope while `store` is bound inside init(). And `list` is the
       exported name — an earlier draft called store.read(), which does not
       exist, so the lookup silently returned null and the Delete button did
       nothing at all. */
    var api = global.SkriblPosted;
    var all = (api && api.list) ? api.list() : [];
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i];
    return null;
  }

  /* Server-side deletion, authorised by the capability this browser holds.
     NO ROUTE LITERAL — the API base is injected, for the same reason
     lib/posted.js refuses to hand-write '/s/': a literal is wrong the moment
     Skribl is mounted under a url_prefix, and verify_seam.py fails it. */
  function destroy(entry, done) {
    var base = global.SKRIBL_API_BASE;
    if (!base) { done(false, 'This Skribl is not wired up.'); return; }
    var req;
    try {
      req = global.fetch(base + '/' + encodeURIComponent(entry.id), {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deleteToken: entry.tok })
      });
    } catch (e) { done(false, 'Could not reach the server.'); return; }
    req.then(function (r) {
      if (r.ok) { done(true, null); return; }
      /* 404 IS AMBIGUOUS BY DESIGN AND MUST STAY AMBIGUOUS HERE. The server
         answers the same 404 for "no such post" and "not yours" so the API
         cannot be walked to learn which public ids exist — deletion.py's whole
         anti-oracle rule. Until v281 this client collapsed that into success,
         with a comment reasoning "the local entry should go either way".
         It does not: a wrong or corrupted key gets exactly this 404, and
         treating it as done threw away the only credential for a post that is
         still live. Security ambiguity on the server cannot become certainty
         in the UI — that is the client undoing the server's care.
         So: unknown. The entry and its key stay. */
      if (r.status === 404) {
        done(false, 'Could not confirm it was deleted — the key may not match '
                    + 'this Skribl. Your key has been kept; open the link to '
                    + 'check whether it is still there.');
        return;
      }
      done(false, 'Could not delete — try again.');
    }).catch(function () { done(false, 'Could not reach the server.'); });
  }

  /* Status for assistive technology as well as eyes. The list has no toast of
     its own, so this writes into a polite live region the drawer owns. */
  function announce(msg) {
    var live = global.document.getElementById('postedStatus');
    if (live) live.textContent = msg;
  }

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
    var recoverEl = document.getElementById('postedRecover');

    function open() {
      drawer.hidden = false;
      drawer.classList.add('open');
      render();
      /* The manual focus stays — search is the right first stop here and
         modalfocus would pick whatever comes first in the DOM. What was
         missing is everything around it: Tab escaped into the page behind,
         and closing dropped focus entirely. SkriblModal.open() installs the
         trap and remembers the opener; the timeout then moves focus on to
         search inside the same dialog, which the trap is happy with. */
      if (global.SkriblModal) global.SkriblModal.open(drawer);
      if (searchEl) setTimeout(function () { try { searchEl.focus(); } catch (e) {} }, 40);
    }

    function close() {
      drawer.classList.remove('open');
      drawer.hidden = true;
      if (searchEl) searchEl.value = '';
      if (global.SkriblModal) global.SkriblModal.close(drawer);
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
            (e.kind === 'flip' ? ICON_FLIP : ICON_PAD) + '</span>' +
          '<a class="posted-main" href="' + esc(url) + '" target="_blank" rel="noopener">' +
            '<span class="posted-title">' + esc(e.title || 'Untitled Skribl') + '</span>' +
            '<span class="posted-sub">' + esc(sub) + '</span>' +
          '</a>' +
          '<button type="button" class="posted-copy" data-url="' + esc(url) + '">Copy link</button>' +
          /* TWO DIFFERENT ACTIONS, AND THEY USED TO BE ONE BUTTON. The \u2715
             removed the local entry and nothing else — the Skribl stayed live
             and the link kept working — which an audit of v278 called out as
             making recovery WORSE: it threw away the only handle the person
             had on a post they might want to withdraw.
             "Delete" appears only when this browser holds the revocation
             capability for the post (see lib/posted.js). Without it there is
             nothing honest to offer, so nothing is offered. */
          (e.tok
            ? '<button type="button" class="posted-delete" data-delete="' +
                esc(e.id) + '" aria-label="Delete this Skribl for everyone">' +
                'Delete</button>' +
              /* THE KEY ITSELF, offered for copying. Everything above assumes
                 this browser will still be here when the person changes their
                 mind, and an audit was right that the assumption is the weak
                 part: clearing site data, a new phone, or Safari evicting the
                 origin all end it, and no endpoint can reissue the key. This
                 is the one affordance that outlives the browser. Shown only
                 where a key exists, for the same reason Delete is. */
              '<button type="button" class="posted-key" data-key="' +
                esc(e.id) + '" aria-label="Copy the recovery key for this ' +
                'Skribl">Copy key</button>'
            : '') +
          '<button type="button" class="posted-del" data-del="' + esc(e.id) + '" ' +
            'aria-label="Remove from this list, keeping the Skribl online">' +
            '\u2715</button>' +
        '</div>';
      }).join('');
    }

    listEl.addEventListener('click', function (ev) {
      var c = ev.target.closest('.posted-copy');
      if (c) { copy(c.dataset.url, c); return; }
      var k = ev.target.closest('.posted-key');
      if (k) {
        var kent = byId(k.dataset.key);
        if (kent && kent.tok) copy(kent.tok, k);
        return;
      }
      var d = ev.target.closest('.posted-del');
      if (d) {
        // Removes the entry, NOT the Skribl. The link keeps working, which is
        // why this is not a confirm dialog — nothing is destroyed.
        //
        // It DOES throw away the revocation capability, though, so it is worth
        // saying once. Only asked when there is something to lose.
        var ent = byId(d.dataset.del);
        if (ent && ent.tok && !global.confirm(
              'Remove this from your list?\n\n' +
              'The Skribl stays online and the link keeps working — but this ' +
              'browser holds the only key that can delete it, and removing ' +
              'the entry throws that key away.')) return;
        store.remove(d.dataset.del);
        render();
        return;
      }

      var del = ev.target.closest('.posted-delete');
      if (del) {
        var entry = byId(del.dataset.delete);
        if (!entry || !entry.tok) return;
        if (!global.confirm(
              'Delete this Skribl for everyone?\n\n' +
              'The link stops working immediately and this cannot be undone.'))
          return;
        del.disabled = true;
        var was = del.textContent;
        del.textContent = 'Deleting…';
        destroy(entry, function (ok, msg) {
          if (ok) { store.remove(entry.id); render(); return; }
          del.disabled = false;
          del.textContent = was;
          announce(msg || 'Could not delete — try again.');
        });
      }
    });

    if (searchEl) searchEl.addEventListener('input', render);
    if (searchEl) searchEl.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && searchEl.value) {
        e.stopPropagation(); searchEl.value = ''; render();
      }
    });
    if (recoverEl) recoverEl.addEventListener('click', function () {
      if (global.SkriblRecoveryKey) global.SkriblRecoveryKey.openRecover();
    });
    if (closeEl) closeEl.addEventListener('click', close);
    if (backdrop) backdrop.addEventListener('click', close);
    if (clearEl) clearEl.addEventListener('click', function () {
      /* KEYS ARE NOT HISTORY, AND THIS CONTROL USED TO TREAT THEM AS HISTORY.
         Two taps emptied the whole store — including every revocation key —
         while the posts stayed online, so the user kept nothing but a dead
         list and lost the only thing that could withdraw anything on it. The
         single-row X has warned about exactly this since v279; the button that
         does it to ALL of them at once did not, which is the weaker contract
         winning on the more destructive path.
         The tray's own footer says clearing site data forfeits the keys. That
         is a statement about the BROWSER's control. This is Skribl's own. */
      var keyed = store.list().filter(function (e) { return !!e.tok; });
      if (keyed.length && global.SkriblRecoveryKey
          && global.SkriblRecoveryKey.confirmClear) {
        clearEl.dataset.armed = ''; clearEl.textContent = 'Clear list';
        global.SkriblRecoveryKey.confirmClear(keyed, function () {
          store.clear(); render();
        });
        return;
      }
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
