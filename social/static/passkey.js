/* The site's passkey ceremonies (social/accounts.py; docs/SOCIAL-SITE.md,
 * phase 1, piece 2): sign in, join, a recovery link, and adding another.
 *
 * Each is two posts around the browser's own passkey prompt:
 *
 *     POST <data-options>   -> {options}   the challenge, for this browser
 *     navigator.credentials.get() / .create()
 *     POST <data-verify>    -> {ok, go}    checked, then signed in
 *
 * Both posts are JSON with this page's token in X-Social-CSRF (the server
 * also checks their Origin). The bytes WebAuthn wants are base64url both
 * ways, converted here by hand, so it works in browsers that predate
 * PublicKeyCredential.parseCreationOptionsFromJSON.
 *
 * THE WORDS ARE THE PAGE'S (_passkey_words.html): this file says nothing of
 * its own. Every failure says what to do next and blames nobody. While the
 * prompt is up the button says it is waiting and cannot be pressed twice.
 * A join form's fields are checked as each is left, the message clears as
 * soon as the field changes, and the server has the last word.
 *
 * A LINK'S CODE IS AFTER THE # (/social/join#code, /social/recover#code), so
 * it reaches no server log. A link page ([data-link]) reads it, posts it to
 * the page's check address, and then either fades its form in (a recovery
 * link names whose account it is for) or shows the kind "doesn't work
 * anymore" card in its place; the code then rides in the body of each step.
 */
(function () {
  'use strict';
  var doc = document;
  var meta = doc.querySelector('meta[name="social-csrf"]');
  var token = meta ? meta.getAttribute('content') : '';
  var words = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-word]'), function (w) {
    words[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key, vars) {
    var s = words[key] || words.failed || '';
    Object.keys(vars || {}).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }

  function toBuf(s) {
    s = String(s).replace(/-/g, '+').replace(/_/g, '/');
    while (s.length % 4) s += '=';
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out.buffer;
  }
  function toB64u(buf) {
    var b = new Uint8Array(buf), s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function withIds(list) {
    return (list || []).map(function (c) {
      var o = {}; Object.keys(c).forEach(function (k) { o[k] = c[k]; });
      o.id = toBuf(c.id);
      return o;
    });
  }
  function creation(o) {
    var p = {}; Object.keys(o).forEach(function (k) { p[k] = o[k]; });
    p.challenge = toBuf(o.challenge);
    p.user = { id: toBuf(o.user.id), name: o.user.name, displayName: o.user.displayName };
    if (o.excludeCredentials) p.excludeCredentials = withIds(o.excludeCredentials);
    return p;
  }
  function request(o) {
    var p = {}; Object.keys(o).forEach(function (k) { p[k] = o[k]; });
    p.challenge = toBuf(o.challenge);
    if (o.allowCredentials) p.allowCredentials = withIds(o.allowCredentials);
    return p;
  }
  function extensions(c) {
    try { return c.getClientExtensionResults ? c.getClientExtensionResults() : {}; } catch (e) { return {}; }
  }
  function made(c) {
    var r = c.response;
    return { id: c.id, rawId: toB64u(c.rawId), type: c.type,
             authenticatorAttachment: c.authenticatorAttachment || null,
             clientExtensionResults: extensions(c),
             response: { clientDataJSON: toB64u(r.clientDataJSON),
                         attestationObject: toB64u(r.attestationObject),
                         transports: r.getTransports ? r.getTransports() : [] } };
  }
  function signed(c) {
    var r = c.response;
    return { id: c.id, rawId: toB64u(c.rawId), type: c.type,
             authenticatorAttachment: c.authenticatorAttachment || null,
             clientExtensionResults: extensions(c),
             response: { clientDataJSON: toB64u(r.clientDataJSON),
                         authenticatorData: toB64u(r.authenticatorData),
                         signature: toB64u(r.signature),
                         userHandle: r.userHandle ? toB64u(r.userHandle) : null } };
  }

  function post(url, body) {
    return fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
      body: JSON.stringify(body || {})
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!j || typeof j !== 'object') j = {};
        j.status = r.status;
        return j;
      });
    }, function () { return { error: 'network' }; });
  }

  function why(j) {
    if (!j) return 'failed';
    if (j.status === 429) return 'limited';
    if (j.status === 403) return 'stale';
    if (j.status === 503) return 'resting';
    return j.error || 'failed';
  }

  function show(box, text) {
    if (!box) return;
    box.textContent = text || '';
    box.hidden = !text;
  }

  function busy(btn, on) {
    if (!btn) return;
    btn.disabled = !!on;
    btn.setAttribute('aria-busy', on ? 'true' : 'false');
  }

  /* A join form's own fields: shown under each, its input marked. */
  function fieldError(form, name, key, vars) {
    var box = form.querySelector('[data-err="' + name + '"]');
    var input = form.querySelector('[name="' + name + '"]');
    if (box) show(box, key ? say(key, vars) : '');
    if (input) {
      if (key) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
    }
    return input;
  }

  function checkField(form, name) {
    var input = form.querySelector('[name="' + name + '"]');
    if (!input) return null;
    var v = input.type === 'checkbox' ? input.checked : input.value.trim();
    if (name === 'name') {
      if (!v) return 'name_empty';
      if (v.length > 40) return 'name_long';
    } else if (name === 'handle') {
      if (!/^@?[A-Za-z][A-Za-z0-9_]{2,19}$/.test(v)) return 'handle_shape';
    } else if (name === 'age13') {
      if (!v) return 'age';
    }
    return null;
  }

  function ceremony(el) {
    var kind = el.getAttribute('data-passkey');
    var form = el.tagName === 'FORM' ? el : null;
    var btn = form ? form.querySelector('button[type="submit"]') : el;
    var box = (form || el.parentNode).querySelector('[data-say]');
    var body = {};
    if (form) {
      var first = null;
      ['name', 'handle', 'age13'].forEach(function (n) {
        var key = checkField(form, n);
        var input = fieldError(form, n, key);
        if (key && !first) first = input;
      });
      if (first) { first.focus(); return; }
      body = { name: form.elements.name.value, handle: form.elements.handle.value.trim().replace(/^@/, ''),
               age13: !!form.elements.age13.checked };
    }
    var getting = kind === 'signin';
    if (linkCode) body.code = linkCode;
    busy(btn, true);
    show(box, say('working'));
    post(el.getAttribute('data-options'), body).then(function (j) {
      if (!j.options) throw j;
      var asked = getting ? navigator.credentials.get({ publicKey: request(j.options) })
                          : navigator.credentials.create({ publicKey: creation(j.options) });
      return asked.then(function (c) {
        if (!c) throw { error: 'cancelled' };
        var answer = { credential: getting ? signed(c) : made(c), next: el.getAttribute('data-next') || '' };
        if (linkCode) answer.code = linkCode;
        return post(el.getAttribute('data-verify'), answer);
      }, function (e) {
        throw { error: e && e.name === 'InvalidStateError' ? 'already' : 'cancelled' };
      });
    }).then(function (j) {
      if (!j.ok || !j.go) throw j;
      show(box, say('done'));
      window.location.assign(j.go);
    }).catch(function (j) {
      busy(btn, false);
      if (j && j.error === 'gone' && card) { linkGone(); return; }
      if (j && j.error === 'fields' && form) {
        show(box, '');
        var firstBad = null;
        Object.keys(j.fields || {}).forEach(function (n) {
          var input = fieldError(form, n, j.fields[n], { handle: body.handle || '' });
          if (!firstBad) firstBad = input;
        });
        if (firstBad) firstBad.focus();
        return;
      }
      /* On the sign-in page, a passkey not picked is most often a person
         with no passkey here yet (the owner's first evening, Nov 10): the
         words say where joining starts, not only "try again". */
      var key = why(j);
      if (getting && key === 'cancelled' && words.cancelled_signin) key = 'cancelled_signin';
      show(box, say(key));
    });
  }

  /* A link page: the code after the #, checked before the form is shown. */
  var card = doc.querySelector('[data-link]');
  var linkCode = '';
  function linkGone() {
    var ok = card.querySelector('[data-link-ok]'), gone = card.querySelector('[data-link-gone]');
    if (ok) ok.hidden = true;
    if (gone) gone.hidden = false;
    card.setAttribute('aria-labelledby', 'goneTitle');
    card.classList.remove('is-checking');
  }
  if (card) {
    /* Another link opened in this tab changes only what follows the #, and
       a page does not load again for that: this one does, and checks it. */
    window.addEventListener('hashchange', function () { window.location.reload(); });
    try { linkCode = decodeURIComponent(window.location.hash.replace(/^#/, '')); } catch (e) { linkCode = ''; }
    if (!linkCode || linkCode.length > 200 || !window.fetch) {
      linkGone();
    } else {
      post(card.getAttribute('data-link'), { code: linkCode }).then(function (j) {
        if (!j.ok) {
          if (j.status === 404 || j.error === 'gone') { linkGone(); return; }
          /* Not a verdict on the link (busy, stale, resting): the form
             shows, and its own button says what is wrong when pressed. */
          var box = card.querySelector('[data-say]');
          show(box, say(why(j)));
        }
        if (j.first) { var f = card.querySelector('[data-link-first]'); if (f) f.hidden = false; }
        if (j.handle) { var h = card.querySelector('[data-link-handle]'); if (h) h.textContent = '@' + j.handle; }
        card.classList.remove('is-checking');
      });
    }
  }

  var ready = !!(window.PublicKeyCredential && navigator.credentials && window.fetch);
  Array.prototype.forEach.call(doc.querySelectorAll('[data-passkey]'), function (el) {
    if (!ready) {
      var box = (el.tagName === 'FORM' ? el : el.parentNode).querySelector('[data-say]');
      show(box, say('unsupported'));
      return;
    }
    if (el.tagName === 'FORM') {
      el.addEventListener('submit', function (e) { e.preventDefault(); ceremony(el); });
      /* Checked as each field is left; the message goes as soon as it changes. */
      ['name', 'handle', 'age13'].forEach(function (n) {
        var input = el.querySelector('[name="' + n + '"]');
        if (!input) return;
        input.addEventListener(input.type === 'checkbox' ? 'change' : 'blur', function () {
          if (input.type !== 'checkbox' && !input.value.trim()) return;
          fieldError(el, n, checkField(el, n));
        });
        input.addEventListener('input', function () { fieldError(el, n, null); });
      });
    } else {
      el.addEventListener('click', function () { ceremony(el); });
    }
  });
})();
