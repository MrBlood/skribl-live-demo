/* Both ends of an anonymous author's revocation key: showing one, taking one
 * back, and standing between a bulk clear and the keys it would discard.
 *
 *   present({ key, url })        show a key the store could not keep
 *   openRecover()                take one back: link-or-id plus key
 *   confirmClear(keyed, onOk)    stand between a bulk clear and the keys
 *   warnIfVolatile(container)    warn BEFORE posting when nothing persists
 *   copy(text)  -> Promise<bool> clipboard, with a legacy fallback
 *   parseId('https://h/s/abc')   -> 'abc123'
 *   close() / closeRecover() / closeClear()
 *                                dismiss each, used by their own buttons
 *                                and by verify_a11y's modal recipes
 *
 * This block listed four of the nine until v281 — written when the module
 * only showed a key, and not grown as it gained the other end of the loop and
 * the clear guard. An incomplete usage summary is the kind that sends the
 * next reader to read the export list instead, which is where they would have
 * looked anyway if it had claimed nothing.
 *
 * EXPORT WITHOUT IMPORT IS NOT A RECOVERY STORY, which is what v280 shipped
 * and what a third audit called the release blocker. This file showed the key,
 * the tray copied it, the panel said "keep it somewhere you will find it" —
 * and nothing anywhere would accept one back. The only DELETE the product
 * could send read its token out of the local record, and the button that sent
 * it only rendered when that record already had one. So the four situations
 * the key exists for (cleared site data, origin eviction, a new device, a
 * failed write) all ended the same way: the user holds the credential and the
 * product cannot use it.
 *
 * openRecover() is the other half. Skribl id or share link, plus the key, and
 * then either withdraw the post or take custody of it again in this browser.
 * The invariant it exists to satisfy, stated as the audit stated it:
 *
 *     possess the id and the key -> revoke through the product, whatever
 *     this browser happens to remember.
 *
 * IT LIVES IN "YOUR SKRIBLS" AND NOT ON THE PLAYER PAGE. Partly a hard
 * constraint — the player's byte ratchet had six bytes of headroom — but it is
 * the right place anyway: /s/<id> is what RECIPIENTS open, and a takedown
 * affordance there teaches that holding the link is what entitles you to
 * remove it. The link is the thing the author gave away.
 *
 * WHY THIS EXISTS. v279 gave an anonymous post a 256-bit capability, returned
 * once in the create response and stored only as a SHA-256 on the server. There
 * is no endpoint that can reissue it. v279 then kept the only copy in
 * localStorage and treated the write as best-effort, so an audit found two ways
 * to publish something irrevocable and be told it went fine: a quota or
 * private-mode failure at the moment of posting, and the 200-entry cap
 * evicting an older key later. lib/posted.js closes both. This closes the one
 * neither of them can: a browser that genuinely cannot keep anything.
 *
 * THE PRINCIPLE. Storage is custody, not the credential. Every store this page
 * can reach -- localStorage, IndexedDB, Cache -- is cleared by the same user
 * action and the same Safari eviction sweep, so moving the key between them
 * buys capacity and not durability. The only custody that survives clearing
 * site data, a new phone, or an account system that does not exist yet is the
 * user holding the key themselves. So when the browser cannot keep it, we ask
 * the person to, and we make that easy rather than treating it as an error
 * message.
 *
 * IT IS CALLED A RECOVERY KEY, not a delete token, in everything the user
 * reads. Deletion is what it does today. The same secret is what a future
 * account system would accept to CLAIM the post it belongs to, and a name that
 * only means "delete" would have to be retired at exactly the moment the
 * back-catalogue depends on people still recognising it.
 *
 * WHY THIS MODULE BUILDS ITS OWN MARKUP, against the usual split where
 * templates own DOM and lib/ owns behaviour. Two surfaces need an identical
 * panel at a moment when getting it wrong is unrecoverable, and two template
 * copies of a thing that rare is two chances for one of them to drift unseen.
 * Everything it creates is inert until `present()` is called.
 *
 * IT ROUTES THROUGH SkriblModal like every other aria-modal surface, so the
 * focus contract is the shared one and verify_a11y's enumeration covers it
 * without knowing this file exists.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var node = null;

  function build() {
    if (node) return node;
    var d = doc.createElement('div');
    d.className = 'reckey-overlay';
    /* An id because verify_a11y enumerates every aria-modal surface and keys
       its interaction recipes by id. A dialog this code creates at runtime is
       exactly the kind that escapes a DOM census taken at load, so the suite
       primes it deliberately — see that section's note. */
    d.id = 'reckeyOverlay';
    d.setAttribute('role', 'dialog');
    d.setAttribute('aria-modal', 'true');
    d.setAttribute('aria-labelledby', 'reckeyTitle');
    d.hidden = true;
    d.innerHTML =
      '<div class="reckey-sheet">' +
        '<h2 id="reckeyTitle" class="reckey-title">Save your recovery key</h2>' +
        '<p class="reckey-why">Your Skribl is posted. This browser could not ' +
        'keep the key that lets you take it down again, so this is the only ' +
        'time it will be shown.</p>' +
        '<code class="reckey-value" id="reckeyValue" tabindex="0"></code>' +
        '<p class="reckey-note">Keep it somewhere you will find it. Without ' +
        'it nobody can withdraw this Skribl but the site owner.</p>' +
        '<div class="reckey-actions">' +
          '<button type="button" class="reckey-copy" id="reckeyCopy">Copy key</button>' +
          '<button type="button" class="reckey-done" id="reckeyDone">I have saved it</button>' +
        '</div>' +
        '<p class="reckey-said" id="reckeySaid" role="status" aria-live="polite"></p>' +
      '</div>';
    doc.body.appendChild(d);
    node = d;
    return d;
  }

  /* Clipboard first, execCommand second, and neither is trusted to have
     worked: the key stays on screen and selectable either way. A copy button
     that silently no-ops is how somebody loses the thing this panel exists to
     save. */
  function copy(text) {
    if (global.navigator && global.navigator.clipboard &&
        global.navigator.clipboard.writeText) {
      return global.navigator.clipboard.writeText(text).then(function () {
        return true;
      }, function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    try {
      var ta = doc.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      doc.body.appendChild(ta);
      ta.select();
      var ok = doc.execCommand && doc.execCommand('copy');
      doc.body.removeChild(ta);
      return !!ok;
    } catch (e) {
      return false;
    }
  }

  function present(opts) {
    if (!opts || !opts.key) return false;
    var d = build();
    var value = d.querySelector('#reckeyValue');
    var said = d.querySelector('#reckeySaid');
    var copyBtn = d.querySelector('#reckeyCopy');
    var doneBtn = d.querySelector('#reckeyDone');
    value.textContent = opts.key;
    said.textContent = '';

    copyBtn.onclick = function () {
      copy(opts.key).then(function (ok) {
        /* Says what happened rather than assuming. On the failure path the
           instruction has to change, because "copied" would be a lie and the
           user would leave without the key. */
        said.textContent = ok
          ? 'Copied to your clipboard.'
          : 'Could not copy automatically — select the key above and copy it.';
      });
    };
    doneBtn.onclick = function () { close(); };

    d.hidden = false;
    if (global.SkriblModal) global.SkriblModal.open(d);
    else value.focus();
    return true;
  }

  function close() {
    if (!node) return;
    node.hidden = true;
    if (global.SkriblModal) global.SkriblModal.close(node);
  }

  /* Say so BEFORE posting when this browser cannot keep anything, because a
     post is irreversible and a warning after the fact is only half useful.
     Non-blocking on purpose: a person in private mode may still want to post,
     and refusing would be deciding for them. What changes is that they know
     the key is coming and that it is theirs to keep.

     One helper rather than a notice in each sheet's markup, for the reason
     given at the head of this file: two copies of a rare warning are two
     chances for one to go stale. The caller names its own container. */
  function warnIfVolatile(container) {
    if (!container) return false;
    var warn = container.querySelector('.reckey-warn');
    var volatile_ = !(global.SkriblPosted && global.SkriblPosted.canPersist &&
                      global.SkriblPosted.canPersist());
    if (!volatile_) {
      if (warn && warn.parentNode) warn.parentNode.removeChild(warn);
      return false;
    }
    if (!warn) {
      warn = doc.createElement('p');
      warn.className = 'reckey-warn';
      warn.setAttribute('role', 'status');
      container.insertBefore(warn, container.firstChild);
    }
    warn.textContent = 'This browser cannot save anything, so it cannot keep ' +
      'the key that lets you take this Skribl down. You will be shown the key ' +
      'once after posting — save it somewhere.';
    return true;
  }

  /* ---------------------------------------------------------------- import */

  var rnode = null;

  /* A share link or a bare id. People paste what they have, and what they have
     is usually the link they sent somebody — so accepting only an id would
     fail the commonest case. Anchors and query strings are stripped; the id is
     the last non-empty path segment. Returns '' when there is nothing usable,
     so the caller can say so rather than sending a request for ''. */
  function parseId(raw) {
    var v = String(raw || '').trim();
    if (!v) return '';
    v = v.split('#')[0].split('?')[0];
    if (v.indexOf('/') !== -1) {
      var parts = v.split('/').filter(function (p) { return p !== ''; });
      v = parts.length ? parts[parts.length - 1] : '';
    }
    /* Public ids are url-safe and short; anything else is a paste accident. */
    return /^[A-Za-z0-9_-]{1,64}$/.test(v) ? v : '';
  }

  function buildRecover() {
    if (rnode) return rnode;
    var d = doc.createElement('div');
    d.className = 'reckey-overlay';
    d.id = 'recoverOverlay';
    d.setAttribute('role', 'dialog');
    d.setAttribute('aria-modal', 'true');
    d.setAttribute('aria-labelledby', 'recoverTitle');
    d.hidden = true;
    d.innerHTML =
      '<div class="reckey-sheet">' +
        '<h2 id="recoverTitle" class="reckey-title">Use a recovery key</h2>' +
        '<p class="reckey-why">For a Skribl this browser has forgotten. Paste ' +
        'its link and the key you saved.</p>' +
        '<label class="reckey-label" for="recoverId">Skribl link or ID</label>' +
        '<input class="reckey-input" id="recoverId" type="text" autocomplete="off" ' +
          'autocapitalize="off" spellcheck="false" placeholder="https://…/s/abc123">' +
        '<label class="reckey-label" for="recoverKey">Recovery key</label>' +
        '<input class="reckey-input" id="recoverKey" type="text" autocomplete="off" ' +
          'autocapitalize="off" spellcheck="false">' +
        '<div class="reckey-actions">' +
          '<button type="button" class="reckey-copy" id="recoverAdd">Add to my list</button>' +
          '<button type="button" class="reckey-done" id="recoverDelete">Take it down</button>' +
        '</div>' +
        '<p class="reckey-said" id="recoverSaid" role="status" aria-live="polite"></p>' +
        '<div class="reckey-actions">' +
          '<button type="button" class="reckey-copy" id="recoverCancel">Close</button>' +
        '</div>' +
      '</div>';
    doc.body.appendChild(d);
    rnode = d;
    return d;
  }

  function openRecover() {
    var d = buildRecover();
    var idEl = d.querySelector('#recoverId');
    var keyEl = d.querySelector('#recoverKey');
    var said = d.querySelector('#recoverSaid');
    idEl.value = ''; keyEl.value = ''; said.textContent = '';

    function inputs() {
      var id = parseId(idEl.value);
      var key = String(keyEl.value || '').trim();
      if (!id) { said.textContent = 'That does not look like a Skribl link or ID.'; return null; }
      if (!key) { said.textContent = 'Paste the recovery key you saved.'; return null; }
      return { id: id, key: key };
    }

    /* TAKE IT DOWN. The 404 rule is the same one postedui.destroy() follows and
       for the same reason: the server answers 404 both for "no such post" and
       "not yours", so it cannot be read as success. Here it is even more
       important — the user has just told us this key is the only copy. */
    d.querySelector('#recoverDelete').onclick = function () {
      var v = inputs(); if (!v) return;
      var base = global.SKRIBL_API_BASE;
      if (!base) { said.textContent = 'This Skribl is not wired up.'; return; }
      said.textContent = 'Taking it down…';
      global.fetch(base + '/' + encodeURIComponent(v.id), {
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
        body: JSON.stringify({ deleteToken: v.key })
      }).then(function (r) {
        if (r.ok) {
          /* "gone for everyone" is the unconditional promise deletion.py
             was corrected for after a v278 audit, written back into the UI
             by me and caught by reading every user-facing string as a claim.
             The LINK stops working immediately — the row is gone and
             /media/<key> authorises through associations that went with it.
             What can outlive it is cached media, for the five-minute window a
             deployment opts into with SKRIBL_PUBLIC_MEDIA_CACHE. The page
             cannot know whether that is on, so it promises the part that is
             true everywhere and does not promise the part that is not. */
          said.textContent = 'Taken down. The link stops working now.';
          if (global.SkriblPosted) global.SkriblPosted.remove(v.id);
          if (global._skriblPostedUI) global._skriblPostedUI.render();
          return;
        }
        said.textContent = r.status === 404
          ? 'That key does not open that Skribl — or it is already gone. '
            + 'Nothing was changed, and your key is still yours.'
          : 'Could not take it down — try again.';
      }).catch(function () {
        said.textContent = 'Could not reach the server.';
      });
    };

    /* ADD TO MY LIST. Recovery is not only deletion: somebody who has just
       moved browsers wants their Skribl back under management, not destroyed.
       This re-establishes custody, which is the step that makes
       export -> lose the browser -> import a round trip rather than a
       one-way door. */
    d.querySelector('#recoverAdd').onclick = function () {
      var v = inputs(); if (!v) return;
      if (!global.SkriblPosted) { said.textContent = 'This browser cannot store it.'; return; }
      var base = global.SKRIBL_PLAYER_BASE || '';
      var kept = global.SkriblPosted.add({
        id: v.id, url: base ? base + '/' + v.id : null,
        title: 'Recovered Skribl', kind: 'pad', pages: 1, tok: v.key
      });
      if (global._skriblPostedUI) global._skriblPostedUI.render();
      /* The key is NOT verified against the server here, and saying so matters:
         adding it proves nothing about whether it works. Deletion is the only
         operation that can tell, and it is destructive, so this cannot check
         on the user's behalf without doing the thing they may not want done. */
      said.textContent = kept && kept.durable
        ? 'Added to your list on this browser. The key is not checked until '
          + 'you use it.'
        : 'This browser could not store it — keep your key safe.';
    };

    d.querySelector('#recoverCancel').onclick = function () { closeRecover(); };

    d.hidden = false;
    if (global.SkriblModal) global.SkriblModal.open(d);
    else idEl.focus();
    return true;
  }

  function closeRecover() {
    if (!rnode) return;
    rnode.hidden = true;
    if (global.SkriblModal) global.SkriblModal.close(rnode);
  }

  /* ------------------------------------------------- clearing, with the keys */

  var cnode = null;

  /* EXPORT BEFORE DESTROY, and the destroy stays behind the export. The audit
     asked for "Clear anyway" to be withheld until the keys have actually been
     exported, and that is right: an unexported clear is unrecoverable and a
     two-tap affordance is not consent to that. So the button is disabled until
     a copy or a download has succeeded, and the count is stated because "17
     keys" reads differently from "your list". */
  function confirmClear(keyed, proceed) {
    if (!cnode) {
      var d = doc.createElement('div');
      d.className = 'reckey-overlay';
      d.id = 'clearKeysOverlay';
      d.setAttribute('role', 'dialog');
      d.setAttribute('aria-modal', 'true');
      d.setAttribute('aria-labelledby', 'clearKeysTitle');
      d.hidden = true;
      d.innerHTML =
        '<div class="reckey-sheet">' +
          '<h2 id="clearKeysTitle" class="reckey-title">These keys are the only copies</h2>' +
          '<p class="reckey-why" id="clearKeysWhy"></p>' +
          '<p class="reckey-note">Clearing the list does <strong>not</strong> ' +
          'delete those Skribls. It removes this browser&rsquo;s ability to ' +
          'take them down.</p>' +
          '<div class="reckey-actions">' +
            '<button type="button" class="reckey-copy" id="clearKeysExport">Copy the keys</button>' +
            '<button type="button" class="reckey-copy" id="clearKeysCancel">Cancel</button>' +
          '</div>' +
          '<p class="reckey-said" id="clearKeysSaid" role="status" aria-live="polite"></p>' +
          '<div class="reckey-actions">' +
            '<button type="button" class="reckey-done" id="clearKeysGo" disabled>Clear anyway</button>' +
          '</div>' +
        '</div>';
      doc.body.appendChild(d);
      cnode = d;
    }
    var d2 = cnode;
    var go = d2.querySelector('#clearKeysGo');
    var said = d2.querySelector('#clearKeysSaid');
    d2.querySelector('#clearKeysWhy').textContent =
      keyed.length + (keyed.length === 1
        ? ' Skribl in this list has a recovery key stored here.'
        : ' Skribls in this list have recovery keys stored here.');
    said.textContent = '';
    go.disabled = true;

    /* One line per Skribl, id and key, so it can be pasted anywhere and read
       back by a person. Not JSON: the thing being saved has to survive being
       kept in a note, and a person has to be able to see which key is which. */
    var dump = keyed.map(function (e) {
      return (e.url || e.id) + '  ' + e.tok;
    }).join('\n');

    d2.querySelector('#clearKeysExport').onclick = function () {
      copy(dump).then(function (ok) {
        said.textContent = ok
          ? 'Copied ' + keyed.length + ' key(s). Paste them somewhere safe, '
            + 'then you can clear.'
          : 'Could not copy automatically — clearing stays disabled. Copy the '
            + 'keys from Your Skribls one at a time instead.';
        /* Only a CONFIRMED copy unlocks it. A failed clipboard write that
           still enabled the button would be the same false certainty this
           release removed from the DELETE path. */
        go.disabled = !ok;
      });
    };
    d2.querySelector('#clearKeysCancel').onclick = function () { closeClear(); };
    go.onclick = function () { closeClear(); proceed(); };

    d2.hidden = false;
    if (global.SkriblModal) global.SkriblModal.open(d2);
    return true;
  }

  function closeClear() {
    if (!cnode) return;
    cnode.hidden = true;
    if (global.SkriblModal) global.SkriblModal.close(cnode);
  }

  global.SkriblRecoveryKey = {
    present: present,
    close: close,
    copy: copy,
    confirmClear: confirmClear,
    closeClear: closeClear,
    warnIfVolatile: warnIfVolatile,
    openRecover: openRecover,
    closeRecover: closeRecover,
    parseId: parseId
  };
})(window);
