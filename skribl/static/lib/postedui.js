/* Your Skribls — rendering. The store is lib/posted.js; this draws it.
 *
 * ON THE PROFILE PAGE SINCE v304, not in the editors. It was a drawer both
 * editors opened from their menu; the profile (/library) is where somebody's
 * Skribls live now, and the menu row links there. The engine is unchanged —
 * the armed deletes, the 404 rule, the key custody — because every line of
 * it was earned (SK-AUD-014, RE-AUD-001, the v279 audit) and verify_posted
 * pins it; what changed is where it renders and what a row can do:
 *
 *   opts.poster(id)   -> a URL; the row's thumb becomes the poster image
 *   opts.onSelect(e)  -> the title puts the Skribl on the page's stage
 *                        instead of opening the player in a new tab
 *   opts.filter(e)    -> which entries render (the profile's chips)
 *   opts.source()     -> entries from somewhere other than the store (a
 *                        host's author listing); actions that need a key
 *                        appear only where `tok` or `owned` says they may
 *   opts.patchBase    -> the API base for PATCH visibility (the gallery
 *                        switch) and DELETE; SKRIBL_API_BASE when absent
 *   opts.pageEmpty    -> the page owns the empty state, so an empty list
 *                        renders nothing here (the profile showed two
 *                        "nothing yet" messages stacked until v304's
 *                        proofread)
 *
 * Degrades to nothing if the partial is absent: init() returns null.
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
        headers: (function () {
          var h = { 'Content-Type': 'application/json' };
          /* Sent even though neither route consults it today: the POST path
             has always sent it, and a DELETE that omits it is why enforcing
             bp.skribl_csrf on these routes would be a breaking change rather
             than a one-line one. See the note above delete_skribl in
             routes.py. Absent on an anonymous deployment, where the global is
             never injected. */
          if (global.SKRIBL_CSRF_TOKEN) { h['X-Skribl-CSRF'] = global.SKRIBL_CSRF_TOKEN; }
          return h;
        })(),
        body: JSON.stringify(entry.tok ? { deleteToken: entry.tok } : {})
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

  /* ARMED, NOT confirm() (SK-AUD-014). The two destructive controls here --
     the × on a keyed row, which throws away this browser's copy of the
     revocation key, and Delete, which takes the Skribl down for everyone --
     asked with window.confirm(): the one browser-painted dialog left in a
     product whose every other destructive act is an armed second tap (Flip's
     tile delete and Clear, this drawer's own Clear list, the local row's ×).
     Same contract now: the first tap arms the button, says what the second
     will do in its accessible name and through the drawer's live region, and
     disarms itself after a few seconds; the second tap does it. The
     consequence wording is kept whole, because the presentation was the
     defect and the words were not. Returns true when the tap is the second. */
  function arm(btn, warning, restLabel, armedText) {
    if (btn.dataset.armed === '1') {
      clearTimeout(btn._arm);
      btn.dataset.armed = '';
      btn.classList.remove('armed');
      return true;
    }
    btn.dataset.armed = '1';
    btn.classList.add('armed');
    if (armedText) { btn.dataset.label = btn.textContent; btn.textContent = armedText; }
    btn.setAttribute('aria-label', warning);
    announce(warning);
    clearTimeout(btn._arm);
    btn._arm = setTimeout(function () {
      btn.dataset.armed = '';
      btn.classList.remove('armed');
      if (armedText && btn.dataset.label) btn.textContent = btn.dataset.label;
      btn.setAttribute('aria-label', restLabel);
    }, 4000);
    return false;
  }

  function init(opts) {
    opts = opts || {};
    var store = global.SkriblPosted;
    var drawer = document.getElementById('postedDrawer') || document.getElementById('postedPanel');
    if (!store || !drawer) return null;

    var isDialog = drawer.getAttribute('role') === 'dialog';
    var source = typeof opts.source === 'function' ? opts.source : null;
    var poster = typeof opts.poster === 'function' ? opts.poster : null;
    var onSelect = typeof opts.onSelect === 'function' ? opts.onSelect : null;
    var filter = typeof opts.filter === 'function' ? opts.filter : null;
    var listEl = document.getElementById('postedList');
    var countEl = document.getElementById('postedCount');
    var searchEl = document.getElementById('postedSearch');
    var clearEl = document.getElementById('postedClear');
    var backdrop = document.getElementById('postedBackdrop');
    var closeEl = document.getElementById('postedClose');
    var recoverEl = document.getElementById('postedRecover');

    function open() {
      if (!isDialog) { render(); return; }
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
      if (!isDialog) return;
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
      var all = source ? source() : store.list();
      var q = (searchEl && searchEl.value.trim().toLowerCase()) || '';
      var hits = all.filter(function (e) {
        return (!q || (e.title || '').toLowerCase().indexOf(q) >= 0) && (!filter || filter(e));
      });
      if (opts.onRender) opts.onRender(all, hits);

      if (countEl) {
        countEl.textContent = !all.length ? ''
          : q ? (hits.length + ' of ' + all.length)
              : (all.length + (all.length === 1 ? ' Skribl' : ' Skribls'));
      }
      if (clearEl) clearEl.hidden = !all.length;

      if (!all.length) {
        // An invitation, not an apology: this screen is what a new tester sees.
        // Unless the page around the list already says it (opts.pageEmpty).
        if (opts.pageEmpty) { listEl.innerHTML = ''; return; }
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
          '<div class="posted-empty-title">' + (q ? 'Nothing matches that' : 'Nothing here') + '</div>' +
          '<div class="posted-empty-sub">' + (q ? 'Try part of a title.' : 'Nothing of yours is in this view.') + '</div></div>';
        return;
      }

      listEl.innerHTML = hits.map(function (e) {
        /* A LOCAL SAVE (SK-AUD-010): Pad's fallback when the server could not
           be reached. Listed so the orphan sweep in lib/posted.js keeps its
           bytes, and drawn as what it is \u2014 on this device, nothing to send:
           no Copy link, no Share, no Delete-for-everyone, and the \u00d7 deletes
           the save itself rather than a list entry, so it arms first. */
        var isLocal = !!e.local;
        /* WHAT KIND OF THING IT IS, only where that is known. A host's
           listing carries no kind (the payload is deferred there), so a row
           from it says when it was posted and nothing it cannot know -- the
           first cut called every host row a "replay" with a pencil on it. */
        var kindWord = isLocal ? 'on this device only'
          : e.kind === 'flip' ? (e.pages + (e.pages === 1 ? ' page' : ' pages'))
          : e.kind === 'pad' ? 'replay' : '';
        var sub = (kindWord ? kindWord + ' \u00b7 ' : '') + store.ago(e.at);
        // NO route literal. A '/s/' fallback here is exactly what v132 removed
        // from flip.js: it silently posts the wrong URL under a url_prefix, and
        // verify_seam.py exists to catch it. The stored entry carries the url
        // the SERVER returned; if it is missing, fall back to the injected
        // player base, never to a hand-written path.
        var base = global.SKRIBL_PLAYER_BASE || '';
        var url = store.absolute(e.url || (base ? base + '/' + e.id : ''));
        // .posted-row-keyed: three actions, not one; on the compact size class
        // they stack under the title (v293 — the meta line wrapped a word per
        // line beside them on a phone). The actions share one wrapper so the
        // stylesheet can move them as a group; the × stays on the title line.
        if (isLocal) {
          return '<div class="posted-row posted-row-local" data-id="' + esc(e.id) + '">' +
            '<span class="posted-thumb posted-thumb-' + esc(e.kind) + '" aria-hidden="true">' +
              (e.kind === 'flip' ? ICON_FLIP : ICON_PAD) + '</span>' +
            /* Same document, a hash the Pad reads at boot: the click handler
               reloads into it, because a hash change alone boots nothing. */
            '<a class="posted-main" data-local="1" href="' + esc(url) + '">' +
              '<span class="posted-title">' + esc(e.title || 'Untitled Skribl') + '</span>' +
              '<span class="posted-sub">' + esc(sub) + '</span>' +
            '</a>' +
            '<button type="button" class="posted-del" data-del="' + esc(e.id) + '" data-local="1" ' +
              'aria-label="Delete this save from this device">' +
              '✕</button>' +
          '</div>';
        }
        /* MAY ACT: this browser holds the key, or the page says the viewer
           is the author (a host's signed-in user, authorised server-side). */
        var may = !!(e.tok || e.owned);
        /* WHICH WAY IT WAS POSTED. An entry this browser kept before v304
           recorded no visibility, and every editor post before v304 went
           without the key -- the server's default, unlisted -- so that is
           what a store row without one IS, not a guess; a host row without
           one is unknown and says nothing. Three words for three states:
           in the gallery, link only, or the state's own name (a host's
           private post is not reachable by link). */
        var vis = e.visibility || (source ? '' : 'unlisted');
        var inGallery = vis === 'public';
        var visWord = inGallery ? 'in the gallery' : vis === 'unlisted' ? 'link only' : vis;
        var offWord = vis === 'unlisted' ? 'Link only' : (vis.charAt(0).toUpperCase() + vis.slice(1));
        /* MORE THAN ONE ACTION puts the actions under the title on a phone
           (posted.css). Keyed rows always have more than one; a plain row
           does where the system has a share sheet -- which is every phone,
           and was the row that ran off the right edge of one. */
        var many = may || !!(global.navigator && global.navigator.share);
        return '<div class="posted-row' + (may ? ' posted-row-keyed' : '') + (many ? ' posted-row-many' : '') + '" data-id="' + esc(e.id) + '">' +
          /* The poster where the page can build one (the profile), and the
             kind's icon always -- as a badge over the poster, because a Flip
             is marked with the book everywhere else in the app. */
          '<span class="posted-thumb posted-thumb-' + esc(e.kind || 'any') + '" aria-hidden="true">' +
            (poster ? '<img class="posted-poster" src="' + esc(poster(e.id)) + '" alt="" loading="lazy" decoding="async">' : '') +
            (e.kind === 'flip' ? ICON_FLIP : e.kind === 'pad' ? ICON_PAD : '') + '</span>' +
          /* HONOURS player_target, which it did not until v281. __init__.py
             names this link as one of the three "watch it" paths and says
             _blank is their DEFAULT and that a host passing _self "takes
             over" — but this one was hardcoded, so an SPA rendering /s/<id>
             in its own shell got its choice obeyed by Pad's button and Flip's
             anchor and ignored here. Both of those read the value; this was
             the odd one out precisely because it is built in JS rather than
             server-rendered, which is the same seam the docstring says caused
             the original drift. */
          '<a class="posted-main" href="' + esc(url) + '" target="' +
            esc(global.SKRIBL_PLAYER_TARGET || '_blank') + '" rel="noopener"' +
            (onSelect ? ' data-select="' + esc(e.id) + '"' : '') + '>' +
            '<span class="posted-title">' + esc(e.title || 'Untitled Skribl') + '</span>' +
            '<span class="posted-sub">' + esc(sub) +
              (vis ? ' \u00b7 ' + esc(visWord) : '') + '</span>' +
          '</a>' +
          '<span class="posted-actions">' +
          '<button type="button" class="posted-copy" data-url="' + esc(url) + '">Copy link</button>' +
          /* SHARE, where the system has a sheet (v304): the same rule the
             post sheets follow — shown only where navigator.share exists. */
          (global.navigator && global.navigator.share
            ? '<button type="button" class="posted-share" data-url="' + esc(url) + '" data-title="' + esc(e.title || 'A Skribl') + '">Share</button>'
            : '') +
          /* THE GALLERY SWITCH (v304): in or out of the public gallery, the
             same choice the post sheet offered, changeable after the fact by
             whoever may act on the post. PATCH visibility; the record follows. */
          (may && vis
            ? '<button type="button" class="posted-gallery' + (inGallery ? ' on' : '') + '" data-gallery="' + esc(e.id) +
                '" aria-pressed="' + (inGallery ? 'true' : 'false') + '" aria-label="' +
                (inGallery ? 'In the public gallery. Tap to make it link only' : esc(offWord) + '. Tap to show it in the public gallery') + '">' +
                (inGallery ? 'In gallery' : esc(offWord)) + '</button>'
            : '') +
          /* TWO DIFFERENT ACTIONS, AND THEY USED TO BE ONE BUTTON. The \u2715
             removed the local entry and nothing else — the Skribl stayed live
             and the link kept working — which an audit of v278 called out as
             making recovery WORSE: it threw away the only handle the person
             had on a post they might want to withdraw.
             "Delete" appears only when this browser holds the revocation
             capability for the post (see lib/posted.js). Without it there is
             nothing honest to offer, so nothing is offered. */
          (may
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
              (e.tok ? '<button type="button" class="posted-key" data-key="' +
                esc(e.id) + '" aria-label="Copy the recovery key for this ' +
                'Skribl">Copy key</button>' : '')
            : '') +
          '</span>' +
          '<button type="button" class="posted-del" data-del="' + esc(e.id) + '" ' +
            'aria-label="Remove from this list, keeping the Skribl online">' +
            '\u2715</button>' +
        '</div>';
      }).join('');
    }

    /* The gallery switch: PATCH visibility with whatever authorises this
       browser (the key, or the host's signed-in author), then the record. */
    function setGallery(entry, on, btn) {
      var base = opts.patchBase || global.SKRIBL_API_BASE;
      if (!base) { announce('This Skribl is not wired up.'); return; }
      var want = on ? 'public' : 'unlisted';
      var body = { visibility: want };
      if (entry.tok) body.deleteToken = entry.tok;
      var h = { 'Content-Type': 'application/json' };
      if (global.SKRIBL_CSRF_TOKEN) h['X-Skribl-CSRF'] = global.SKRIBL_CSRF_TOKEN;
      btn.disabled = true;
      global.fetch(base + '/' + encodeURIComponent(entry.id), {
        method: 'PATCH', headers: h, credentials: 'same-origin', body: JSON.stringify(body)
      }).then(function (r) {
        if (!r.ok) throw new Error(r.status === 404
          ? 'Could not change it — the key may not match this Skribl.'
          : 'Could not change it — try again.');
        return r.json();
      }).then(function (res) {
        var vis = (res && res.visibility) || want;
        if (!source) store.update(entry.id, { visibility: vis }); else entry.visibility = vis;
        announce(vis === 'public' ? 'Now in the public gallery' : 'Now link only');
        render();
      }).catch(function (err) {
        btn.disabled = false;
        announce(err.message || 'Could not change it — try again.');
      });
    }

    listEl.addEventListener('click', function (ev) {
      var sel = onSelect && ev.target.closest('.posted-main[data-select]');
      if (sel) {
        ev.preventDefault();
        var sent = byId(sel.dataset.select) || (source ? source().filter(function (e) { return e.id === sel.dataset.select; })[0] : null);
        if (sent) onSelect(sent);
        return;
      }
      var c = ev.target.closest('.posted-copy');
      if (c) { copy(c.dataset.url, c); return; }
      var sh = ev.target.closest('.posted-share');
      if (sh) {
        try { global.navigator.share({ title: sh.dataset.title, url: sh.dataset.url }).catch(function () {}); } catch (e) {}
        return;
      }
      var g = ev.target.closest('.posted-gallery');
      if (g) {
        var gent = byId(g.dataset.gallery) || (source ? source().filter(function (e) { return e.id === g.dataset.gallery; })[0] : null);
        if (gent) setGallery(gent, gent.visibility !== 'public', g);
        return;
      }
      var lm = ev.target.closest('.posted-main[data-local]');
      if (lm) {
        /* The Pad boots its #skribl=<id> player from the hash at LOAD, so a
           same-page hash change has to be followed by a reload; from Flip the
           href already points at the Pad's path and a plain navigation does
           the same job. editor_post.js's Watch button takes the same route. */
        ev.preventDefault();
        var u = new URL(lm.getAttribute('href'), global.location.href);
        if (u.pathname === global.location.pathname) {
          global.location.hash = u.hash; global.location.reload();
        } else {
          global.location.href = u.href;
        }
        return;
      }
      var k = ev.target.closest('.posted-key');
      if (k) {
        var kent = byId(k.dataset.key);
        if (kent && kent.tok) copy(kent.tok, k);
        return;
      }
      var d = ev.target.closest('.posted-del');
      if (d && d.dataset.local) {
        /* For a LOCAL save the × destroys the only copy, so it arms first —
           the same two-tap contract Flip's tile delete and this drawer's own
           Clear list use, and spoken through the drawer's live region rather
           than a browser confirm. */
        if (!arm(d, 'Tap again to delete this save from this device',
                 'Delete this save from this device')) return;
        store.remove(d.dataset.del);
        announce('Deleted from this device');
        render();
        return;
      }
      if (d) {
        // Removes the entry, NOT the Skribl. The link keeps working, which is
        // why this is not a confirm dialog — nothing is destroyed.
        //
        // It DOES throw away the revocation capability, though, so it is worth
        // saying once. Only asked when there is something to lose.
        var ent = byId(d.dataset.del);
        if (ent && ent.tok && !arm(d,
              'Tap again to remove — the Skribl stays online, but this ' +
              "browser's copy of the key goes with the entry",
              'Remove from this list, keeping the Skribl online')) return;
        store.remove(d.dataset.del);
        render();
        return;
      }

      var del = ev.target.closest('.posted-delete');
      if (del) {
        var entry = byId(del.dataset.delete) || (source ? source().filter(function (e) { return e.id === del.dataset.delete; })[0] : null);
        if (!entry || !(entry.tok || entry.owned)) return;
        if (!arm(del,
              'Tap again to delete this Skribl for everyone — the link ' +
              'stops working at once and this cannot be undone',
              'Delete this Skribl for everyone', 'Tap again to delete')) return;
        del.disabled = true;
        var was = del.textContent;
        del.textContent = 'Deleting…';
        destroy(entry, function (ok, msg) {
          if (ok) {
            if (source) { if (opts.onRemoved) opts.onRemoved(entry.id); } else store.remove(entry.id);
            render(); return;
          }
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
      if (isDialog && e.key === 'Escape' && !drawer.hidden && (!searchEl || !searchEl.value)) close();
    });

    render();
    return { open: open, close: close, render: render };
  }

  global.SkriblPostedUI = { init: init };
})(window);
