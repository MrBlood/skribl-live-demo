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

  /* HAS SOUND. Top right, opposite the kind badge at top left, because the
     two answer different questions and stacking them in one corner makes both
     harder to read. Only drawn where the answer is KNOWN to be yes: a null
     (a local save, a recovered key, a row written before the store carried the
     field) shows nothing rather than claiming silence, which is the bug this
     badge shipped alongside the fix for. */
  var ICON_SOUND =
    '<svg class="posted-sound" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>' +
    '<path d="M19.5 5.5a9 9 0 0 1 0 13"/></svg>';

  /* THE ROW'S ACTIONS, AS ICONS ON A PHONE ("use icons instead of
     words on phones... maybe left justify").
     Five word-labelled pills wrapped to two lines on a 390px screen and sat
     indented under nothing. Each button carries its icon AND its word now; the
     sheet hides the word at the compact tier, so the same markup is a labelled
     pill on a desktop and a 34px icon on a phone, and the strip fits one line
     left-aligned under the thumbnail.
     THE WORD IS STILL THE ACCESSIBLE NAME where a button has no aria-label of
     its own, which is why it is hidden with `display: none` inside a labelled
     button rather than deleted -- and why the ones whose label is only an icon
     carry an explicit aria-label below. */
  var ICONS = {
    link: '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/>'
        + '<path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
    share: '<path d="M12 3v12"/><path d="m8 7 4-4 4 4"/>'
         + '<path d="M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/>',
    /* ONE GLYPH PER ACTION IN A ROW, which the strip did not manage until
       v311: the visibility toggle borrowed `link` for its off state, so a
       link-only row drew the same chain twice -- once meaning "copy the
       link" and once meaning "only the link reaches this" -- and neither
       tooltip is reachable on the phone the icons were drawn for.

       DRAWN AT 20px AND JUDGED AT 20px, which is the size the row uses and
       not the size an icon is designed at. The first pair failed there and
       nowhere else: a globe replaced by stacked picture-cards (a card, a
       card behind it, a sun and a hill inside the front one) and an eye
       struck through. Both are fine drawings at 44px and both turn to
       porridge at 20 -- four curves and a diagonal inside a 20px box is
       more ink than the box holds. Six candidates were rendered at the real
       size before either was replaced.

       AND EACH ONE HAS TO STAND ALONE, because a toggle shows one state at a
       time: the pair is never seen together and cannot explain itself by
       contrast. That is what ruled out the tidiest candidate, a four-square
       grid against a single card -- side by side it reads as "many" against
       "one", and alone the single card is a rounded rectangle meaning
       nothing.
       AN OPEN EYE AND A CLOSED ONE (owner, from four pairs rendered at 20px)
       satisfies both tests at once, which no other candidate did: the two
       are the same object in two states, AND either one alone says whether
       this Skribl is on show. A four-square grid names the DESTINATION and
       reads well by itself, so it was the other strong answer; it loses
       because its off state has to change the subject, and a toggle whose
       two halves are different objects makes the person read rather than
       recognise. The words beside them still name the destination on a
       screen with room for words -- "In gallery" against "Link only". */
    eyeOpen: '<path d="M2.5 12S6.2 5.5 12 5.5 21.5 12 21.5 12 17.8 18.5 12'
           + ' 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.7"/>',
    /* A LID AND THREE LASHES, and no slash -- the slash is what wrecked the
       first draft, an eye struck through whose diagonal lay along the
       almond's own axis so the two tangled at 20px. A quadratic bow rather
       than an arc so the lid's deepest point is at the centre and the two
       ends meet the lashes cleanly. */
    eyeShut: '<path d="M3 10q9 9 18 0"/><path d="m4.4 12.4-1.6 2.6"/>'
           + '<path d="m9 15.1-.7 2.9"/><path d="m15 15.1.7 2.9"/>'
           + '<path d="m19.6 12.4 1.6 2.6"/>',
    trash: '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
         + '<path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9"/>'
       + '<path d="m17 6 2 2"/><path d="m14 9 2 2"/>'
  };

  function glyph(name) {
    return '<svg class="posted-ico" viewBox="0 0 24 24" fill="none"'
         + ' stroke="currentColor" stroke-width="1.9" stroke-linecap="round"'
         + ' stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>';
  }

  /* The label a button shows, and the one copy()/arm() swap. Wrapped so the
     feedback replaces the WORD and leaves the icon alone -- `btn.textContent =
     'Copied'` would have deleted the svg with it. */
  function lbl(text) { return '<span class="posted-lbl">' + esc(text) + '</span>'; }

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

  /* WHERE it was, not just what it was. lib/posted.js keeps the list in
     insertion order and never sorts it, so a row's position IS its index and
     restoring without one would silently reorder the list. Read from the same
     stored state byId() reads, for the same reason. */
  function indexOf(id) {
    var api = global.SkriblPosted;
    var all = (api && api.list) ? api.list() : [];
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return i;
    return 0;
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

  /* COPY, AND WHETHER IT ACTUALLY WORKED (PRESEAL-002).
   *
   * Resolves true only when the text reached the clipboard: the Clipboard API
   * resolving, or execCommand RETURNING TRUE. Both callers used to claim
   * success unconditionally -- the profile stage's button ran its "Link
   * copied" handler as both arms of .then(), and this module's own row button
   * ran it after `try { execCommand('copy') }`, which does not throw when it
   * merely returns false. Telling somebody their link is copied when it is not
   * strands the share they were making, so the answer travels back now and
   * each caller says what happened.
   *
   * One implementation, exported, because the page has two copy buttons and
   * the stage's had grown its own weaker version. */
  function copyText(text) {
    var api = global.navigator && global.navigator.clipboard;
    if (api && typeof api.writeText === 'function') {
      return api.writeText(text).then(function () { return true; },
                                      function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }

  /* execCommand needs a real selection, and a detached input is not focusable
     on iOS -- so the field is attached, read-only and off-screen rather than
     display:none, which would make it unselectable. */
  function legacyCopy(text) {
    var doc = global.document;
    var t = doc.createElement('input');
    t.setAttribute('readonly', '');
    t.value = text;
    t.style.cssText = 'position:fixed;top:-1000px;left:0;opacity:0';
    doc.body.appendChild(t);
    t.select();
    var ok = false;
    try { ok = !!doc.execCommand('copy'); } catch (e) { ok = false; }
    t.remove();
    return ok;
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

  /* ARMED, NOT confirm() (SK-AUD-014). The destructive controls here asked
     with window.confirm(): the one browser-painted dialog left in a product
     whose every other destructive act is an armed second tap (Flip's tile
     delete and Clear, this panel's own Clear list).
     There were three -- Delete, which takes the Skribl down for everyone; a
     local row's ×, which destroys the only copy of a drawing; and a keyed
     row's ×, which threw away this browser's copy of the revocation key.
     v311 took the last one out rather than keep making it safe, so two arm
     through here now and the contract is unchanged: the first tap arms the
     button, says what the second will do in its accessible name and through
     the panel's live region, and disarms itself after a few seconds; the
     second tap does it. The consequence wording is kept whole, because the
     presentation was the defect and the words were not. Returns true when
     the tap is the second. */
  function arm(btn, warning, restLabel, armedText) {
    if (btn.dataset.armed === '1') {
      clearTimeout(btn._arm);
      btn.dataset.armed = '';
      btn.classList.remove('armed');
      return true;
    }
    btn.dataset.armed = '1';
    btn.classList.add('armed');
    /* Same reason as copy()'s: write the WORD, keep the icon, and force the
       word visible while the button is armed -- an armed control that shows
       only a trash icon has not warned anybody. */
    var slot = btn.querySelector('.posted-lbl') || btn;
    if (armedText) { btn.dataset.label = slot.textContent; slot.textContent = armedText;
                     btn.classList.add('said'); }
    btn.setAttribute('aria-label', warning);
    announce(warning);
    clearTimeout(btn._arm);
    btn._arm = setTimeout(function () {
      btn.dataset.armed = '';
      btn.classList.remove('armed');
      if (armedText && btn.dataset.label) slot.textContent = btn.dataset.label;
      btn.classList.remove('said');
      btn.setAttribute('aria-label', restLabel);
    }, 4000);
    return false;
  }

  function init(opts) {
    opts = opts || {};
    var store = global.SkriblPosted;
    /* THE PANEL IS A SECTION ON A PAGE, NOT A DIALOG. "Your Skribls" was a
       drawer inside the editors until it became the profile page; the drawer's
       markup went with it and this module kept its open/close machinery, gated
       on a `role="dialog"` no live element carries. Nothing called open() or
       close() either -- every caller uses render() -- so the whole apparatus
       ran never: two listeners on ids the tree does not create, an Escape
       branch behind a false flag, and six rule-sets in posted.css that styled
       the shell. Removed together, markup, script and style. */
    var drawer = document.getElementById('postedPanel');
    if (!store || !drawer) return null;
    var source = typeof opts.source === 'function' ? opts.source : null;
    var poster = typeof opts.poster === 'function' ? opts.poster : null;
    var onSelect = typeof opts.onSelect === 'function' ? opts.onSelect : null;
    var filter = typeof opts.filter === 'function' ? opts.filter : null;
    var listEl = document.getElementById('postedList');
    var countEl = document.getElementById('postedCount');
    var searchEl = document.getElementById('postedSearch');
    var clearEl = document.getElementById('postedClear');
    var recoverEl = document.getElementById('postedRecover');
    var undoEl = document.getElementById('postedUndo');
    var undoMsgEl = document.getElementById('postedUndoMsg');
    var undoBtn = document.getElementById('postedUndoBtn');
    var undoX = document.getElementById('postedUndoX');

    /* THE ONE ACT HERE WITH NO WAY BACK ("is there a way to put the row back
       after you've taken it down? how would you ever see it again?"). Delete
       is undone by nothing and says so; Clear list asks first; but a local
       save's x destroys the only copy of a drawing, one armed tap from
       permanent, with no server behind it to ask again.

       Twelve seconds, one button, and the entry goes back where it was with
       its timestamp (store.restore). The bytes are kept for the same twelve
       seconds (store.remove's keepBlob) so the restored row is not a link to
       nothing, and dropped the moment the window closes.

       IT SERVED THE POSTED ROW'S x TOO until v311 took that control out, and
       the shelf is the one piece of it that keeps its job unchanged. `local`
       is gone from the record because there is only one kind of removal left
       to undo: an entry whose blob is this browser's to drop.

       THE ARMING STAYS. Undo is a repair and arming is a warning, and they
       answer different failures: arming stops the tap you did not mean to
       make, undo returns the one you meant and regretted. The armed tap also
       still says what it costs, because after twelve seconds it costs it. */
    var pending = null;      /* { entry, index, timer } */

    function commitUndo() {
      if (!pending) return;
      clearTimeout(pending.timer);
      store.dropBlob(pending.entry.id);
      pending = null;
      if (undoEl) undoEl.hidden = true;
    }

    function offerUndo(entry, index, word) {
      commitUndo();                       /* one shelf; the older one commits */
      pending = { entry: entry, index: index, timer: null };
      pending.timer = setTimeout(commitUndo, 12000);
      if (undoMsgEl) undoMsgEl.textContent = word;
      if (undoEl) undoEl.hidden = false;
      announce(word + ' Undo is available for a few seconds.');
    }

    /* DISMISS COMMITS, it does not merely hide. A local save's bytes are held
       for the window (store.remove's keepBlob), so a shelf that only closed
       would leave them until the timer -- and somebody who has decided should
       get the space back when they say so, not twelve seconds later. It is
       also the deterministic commit a suite can drive: the timer is a product
       choice and not a thing to wait out in a browser test. */
    if (undoX) undoX.addEventListener('click', commitUndo);

    if (undoBtn) undoBtn.addEventListener('click', function () {
      if (!pending) return;
      var p = pending;
      clearTimeout(p.timer);
      pending = null;
      if (undoEl) undoEl.hidden = true;
      var r = store.restore(p.entry, p.index);
      render();
      if (r.durable) {
        announce('Put back.');
      } else {
        /* The same failure add() reports and for the same reason: the write
           was refused, so the row is on screen and not in storage. It used to
           read out the entry's recovery key here, which was the right answer
           while a POSTED row could be undone -- that key was the thing about
           to be lost for real. A local save has no key and never had one, so
           the sentence resolved to a trailing space on the only removal this
           shelf can still be offered for. */
        announce('Could not put it back — this browser refused to store it.');
      }
    });

    function copy(text, btn) {
      /* THE LABEL, NOT THE BUTTON. This wrote btn.textContent, which was fine
         while a button was one word and deletes the icon now that it is an
         icon plus a word. `.said` forces the word visible for the moment the
         feedback is up, because at the compact tier it is hidden -- otherwise
         "Copied" would be announced and never shown. */
      var slot = btn.querySelector('.posted-lbl') || btn;
      var was = btn.dataset.label || slot.textContent;
      btn.dataset.label = was;
      // A timer per button: two quick copies on different rows would
      // otherwise leave the first stuck reading "Copied".
      function say(label, good) {
        slot.textContent = label;
        btn.classList.add('said');
        btn.classList.toggle('done', !!good);
        clearTimeout(btn._t);
        btn._t = setTimeout(function () {
          slot.textContent = btn.dataset.label;
          btn.classList.remove('done');
          btn.classList.remove('said');
        }, 1400);
      }
      copyText(text).then(function (ok) {
        if (ok) { say('Copied', true); return; }
        // The link is on the row already, so there is something to point at
        // rather than a dead end.
        say("Couldn't copy");
        announce("Couldn't copy the link — open the row's title to get it");
      });
    }

    function render() {
      var all = source ? source() : store.list();
      var q = (searchEl && searchEl.value.trim().toLowerCase()) || '';
      var hits = all.filter(function (e) {
        return (!q || (e.title || '').toLowerCase().indexOf(q) >= 0) && (!filter || filter(e));
      });
      paint(all, hits, q);
      /* AFTER THE LIST IS ON THE PAGE, NOT BEFORE IT, which is why paint() is
         a function now and this line is not where it used to be.
         onRender ran FIRST, so a host that touched the rows in it touched the
         PREVIOUS render's rows and had its work overwritten by the innerHTML
         a few lines later. /library does exactly that twice: it marks the
         playing row `active`, which silently came off on every re-render --
         pick a Skribl, then type in the search box, and the highlight is gone
         though the same Skribl is still on the stage -- and since v311 it
         also crops each thumbnail to its drawing, which simply did nothing.
         The name says when it runs; there is no reason it should have been a
         pre-render hook, and three early exits in paint() are why the call
         could not simply be moved to the end of the old body. */
      if (opts.onRender) opts.onRender(all, hits);
    }

    function paint(all, hits, q) {
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
        /* The pen or the book, for the row that has a picture to put it
           beside rather than on top of. Empty for a host listing, which
           carries no kind and must not be given one. */
        var kindGlyph = e.kind === 'flip' ? ICON_FLIP
                      : e.kind === 'pad' ? ICON_PAD : '';
        var kindMark = kindGlyph
          ? '<span class="posted-kind" aria-hidden="true">' + kindGlyph + '</span>'
          : '';
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
        // stylesheet can move them as a group, and since v311 that wrapper is
        // the whole of a posted row's controls — see the × below.
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
              'aria-label="Delete this save from this device"' +
              ' title="Delete the only copy of this drawing \u2014 undoable for a few seconds">' +
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
            /* THE PICTURE GETS ITS OWN BOX so that the clip it needs is not
               also applied to the badges beside it -- see .posted-shot in
               skribl_library.html. No poster, no wrapper: the drawer's thumb
               is a glyph tile and has nothing to clip. */
            /* THE DRAWING'S SHAPE, WHERE THE ROW KNOWS IT (v311), written
               onto the wrapper exactly as gallery.js writes it onto a card's
               box -- same attribute names, so a reader who has met one has
               met both. The PAGE decides what to do with it: this module
               renders a list and does not know how big its host draws a
               thumb. /library crops the picture to the drawing with it
               (library.js); a host that does nothing gets the stylesheet's
               band crop, which is what every row got before the store
               learned the field. */
            (poster ? '<span class="posted-shot"'
                    + (e.canvas_w && e.canvas_h
                        ? ' data-skribl-w="' + esc(e.canvas_w) + '" data-skribl-h="' + esc(e.canvas_h) + '"'
                        : '')
                    + '><img class="posted-poster" src="' + esc(poster(e.id)) + '" alt="" loading="lazy" decoding="async"></span>' : '') +
            /* THE KIND MARK MOVES TO THE WORDS WHERE THERE IS A PICTURE, and
               stays the tile's whole content where there is not.
               Over a poster it was a badge in the top-left corner, competing
               with the drawing for the same 84x63 box; in the sub line it
               stands directly in front of the fact it qualifies -- "a pen,
               replay, a day ago" reads as one statement, which a corner badge
               and a separate word do not ("move the pencil/book before
               replay/pages").
               The DRAWER has no poster at all: its 42x34 thumb IS this glyph,
               so removing it there would leave an empty tile. Same branch,
               same expression, keyed on whether a picture exists. */
            (poster ? '' : kindGlyph) +
            (e.has_audio === true ? ICON_SOUND : '') + '</span>' +
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
            /* ONCE, NOT TWICE. The gallery switch below is a button that
               both STATES this Skribl's visibility and changes it, so a row
               carrying it said "link only" in the meta line and "Link only"
               on the button two inches apart (screenshot 4). The word
               stays where there is no button — a row this browser holds no key
               for cannot change it, so something has to say it. */
            '<span class="posted-sub">' + (poster ? kindMark : '') + esc(sub) +
              ((vis && !(may && vis)) ? ' \u00b7 ' + esc(visWord) : '') + '</span>' +
          '</a>' +
          '<span class="posted-actions">' +
          /* EVERY TITLE BELOW SAYS WHAT THE LABEL DOES NOT. A tooltip on
             "Copy link" reading "Copy link" is noise that teaches people to
             ignore the next one, so each says the consequence: what is copied,
             what survives, what stops working. lib/tooltip.js moves these to
             data-tip and draws them, and suppresses itself on coarse pointers
             where there is no hover. The aria-labels are untouched — a screen
             reader gets those, and the two must not fight. */
          '<button type="button" class="posted-copy" data-url="' + esc(url) +
            '" aria-label="Copy this Skribl\u2019s share link"' +
            ' title="Copy this Skribl\u2019s share link">' + glyph('link') + lbl('Copy link') + '</button>' +
          /* SHARE, where the system has a sheet (v304): the same rule the
             post sheets follow — shown only where navigator.share exists. */
          (global.navigator && global.navigator.share
            ? '<button type="button" class="posted-share" data-url="' + esc(url) + '" data-title="' + esc(e.title || 'A Skribl') + '"' +
                ' aria-label="Share this Skribl" title="Hand the link to another app">' +
                glyph('share') + lbl('Share') + '</button>'
            : '') +
          /* THE GALLERY SWITCH (v304): in or out of the public gallery, the
             same choice the post sheet offered, changeable after the fact by
             whoever may act on the post. PATCH visibility; the record follows. */
          (may && vis
            ? '<button type="button" class="posted-gallery' + (inGallery ? ' on' : '') + '" data-gallery="' + esc(e.id) +
                '" aria-pressed="' + (inGallery ? 'true' : 'false') + '" aria-label="' +
                (inGallery ? 'In the public gallery. Tap to make it link only' : esc(offWord) + '. Tap to show it in the public gallery') + '"' +
                ' title="' + (inGallery ? 'Anyone can find this in the gallery. Tap to make it link only'
                                        : 'Only someone with the link can reach this. Tap to put it in the gallery') + '">' +
                glyph(inGallery ? 'eyeOpen' : 'eyeShut') +
                lbl(inGallery ? 'In gallery' : offWord) + '</button>'
            : '') +
          /* DELETE IS THE ONLY DESTRUCTIVE ACT ON A POSTED ROW NOW. There
             were two, and the other was a \u2715 at the row's right edge
             that removed the local ENTRY and nothing else — the Skribl
             stayed live and the link kept working.
             That \u2715 has been the hardest control on this page to explain
             since v278, when an audit called it a recovery HAZARD: it threw
             away the only handle somebody had on a post they might want to
             withdraw. v281 gave it an arming tap, v291 an undo shelf, v293 a
             34px target and a grid column of its own — four releases spent
             making a control safe rather than asking whether it earns a place
             beside a trash can that means something else entirely. Two
             remove-shaped controls in one row is a misfire waiting on a
             phone, and it is not a misfire that can be taken back.
             WHAT GOES WITH IT, said plainly because it is a real loss: a row
             this browser holds no key for can no longer be dismissed on its
             own. Clear list is the way out, and it takes the whole list.
             "Delete" appears only when this browser holds the revocation
             capability for the post (see lib/posted.js). Without it there is
             nothing honest to offer, so nothing is offered. */
          (may
            ? '<button type="button" class="posted-delete" data-delete="' +
                esc(e.id) + '" aria-label="Delete this Skribl for everyone"' +
                ' title="Take it down for everyone. The link stops working and this cannot be undone">' +
                glyph('trash') + lbl('Delete') + '</button>' +
              /* THE KEY ITSELF, offered for copying. Everything above assumes
                 this browser will still be here when the person changes their
                 mind, and an audit was right that the assumption is the weak
                 part: clearing site data, a new phone, or Safari evicting the
                 origin all end it, and no endpoint can reissue the key. This
                 is the one affordance that outlives the browser. Shown only
                 where a key exists, for the same reason Delete is. */
              (e.tok ? '<button type="button" class="posted-key" data-key="' +
                esc(e.id) + '" aria-label="Copy the recovery key for this ' +
                'Skribl" title="Copy the key that can delete this Skribl from any browser. ' +
                'Nothing can reissue it">' + glyph('key') + lbl('Copy key') + '</button>' : '')
            : '') +
          '</span>' +
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
      /* THE ONLY ✕ LEFT IS A LOCAL SAVE'S, and that one is not a
         bookkeeping act: a local save exists nowhere else, so its ✕ is
         the delete. `dataset.local` is therefore no longer the branch that
         tells two ✕s apart — it is the assertion that this is the only
         kind there is. A posted row emits no ✕ at all since v311. */
      var d = ev.target.closest('.posted-del');
      if (d && d.dataset.local) {
        /* It destroys the only copy, so it arms first — the same two-tap
           contract Flip's tile delete and Clear list use, spoken through the
           panel's live region rather than a browser confirm. */
        if (!arm(d, 'Tap again to delete this save from this device',
                 'Delete this save from this device')) return;
        var lent = byId(d.dataset.del), lidx = indexOf(d.dataset.del);
        store.remove(d.dataset.del, true);
        render();
        if (lent) offerUndo(lent, lidx, 'Deleted from this device.');
        else announce('Deleted from this device');
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
    render();
    return { render: render };
  }

  global.SkriblPostedUI = { init: init, copyText: copyText };
})(window);
