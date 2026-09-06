/* The one surface that shows an anonymous author their revocation key.
 *
 *   SkriblRecoveryKey.present({ key: '...', url: '...' });   // storage failed
 *   SkriblRecoveryKey.copy(key)  -> Promise<boolean>
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

  global.SkriblRecoveryKey = {
    present: present,
    close: close,
    copy: copy,
    warnIfVolatile: warnIfVolatile
  };
})(window);
