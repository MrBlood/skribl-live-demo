/* A person's profile (social/templates/social/profile.html), and Edit
 * profile (edit.html): phase 1, piece 3.
 *
 * DRAW YOUR FACE. The real Pad, over your profile, in its face mode
 * (?compose=1&face=1: it starts square and says it is your face), through
 * Skribl's own host-side lifecycle, lib/composehost.js (docs/INTEGRATION.md,
 * "Drawing one from your own composer"): the frame's address is set on the
 * first open and never in the page, a drawing reopened is the one it handed
 * back, and messages are checked by origin both ways. The Pad posts nothing:
 * "Use this face" hands the drawing back, and this sends it to the site
 * (/you/face, the site's token in X-Social-CSRF), which keeps it as your
 * face, and the page comes back with it drawing itself. A face that does not
 * save says why, kindly, and the drawing is still there to try again.
 *
 * KIND, NEVER JUMPY. The Pad glides up over the page and back down (a desk's
 * card rises a little as it fades in); under Reduce Motion it fades where it
 * sits (social.css). Nothing here sets a position on a timer: the stylesheet
 * moves it, and this says open or closed and hides it once it has gone.
 * While it is up, the page behind is inert and still, and closing gives
 * focus back to the button that opened it. The Pad brings its own ×.
 *
 * SHARE: the device's own share sheet where there is one, else the link
 * copied, and said; where the clipboard is refused, the link is said to copy
 * by hand. EDIT PROFILE: how much of a bio is left, as it is typed.
 *
 * The words are the page's ([data-word]): this file says nothing of its own.
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
  var box = doc.querySelector('[data-say]');
  function show(text) {
    if (!box) return;
    box.textContent = text || '';
    box.hidden = !text;
  }

  /* ---- share ---------------------------------------------------------- */
  var page = doc.querySelector('[data-profile]');
  var shareBtn = doc.querySelector('[data-share]');
  if (page && shareBtn) {
    shareBtn.addEventListener('click', function () {
      var url = page.getAttribute('data-share-url');
      var title = page.getAttribute('data-share-title');
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () { /* closed: nothing to say */ });
        return;
      }
      function byHand() { show(say('copy_by_hand', { url: url })); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { show(say('copied')); }, byHand);
      } else {
        byHand();
      }
    });
  }

  /* ---- edit profile: the bio's count ------------------------------------ */
  var bio = doc.getElementById('editBio');
  var count = doc.querySelector('[data-bio-count]');
  if (bio && count) {
    var limit = +bio.getAttribute('maxlength') || 160;
    var counted = function () { count.textContent = Math.max(0, limit - bio.value.length) + ' left.'; };
    bio.addEventListener('input', counted);
    counted();
  }

  /* ---- draw your face ---------------------------------------------------- */
  var wrap = doc.getElementById('facePad');
  if (!wrap || !window.SkriblComposeHost) return;
  var frame = wrap.querySelector('.facepad-frame');
  var scrim = wrap.querySelector('.facepad-scrim');
  var openers = doc.querySelectorAll('[data-face-open]');
  var behind = [doc.querySelector('body > .top'), doc.querySelector('body > .nav'), doc.getElementById('main')];
  /* Longer than the slowest glide (the scrim's), in case its transitionend
     never comes (a tab put in the background mid-glide, say). */
  var SETTLE_MS = 450;
  var from = null, timer = 0, open = false, saving = false;

  function mark(on) {
    Array.prototype.forEach.call(openers, function (b) {
      if (b.hasAttribute('aria-expanded')) b.setAttribute('aria-expanded', on ? 'true' : 'false');
    });
    behind.forEach(function (el) {
      if (!el) return;
      if (on) el.setAttribute('inert', ''); else el.removeAttribute('inert');
    });
  }

  function settle() {
    if (open) return;
    clearTimeout(timer);
    wrap.hidden = true;
    wrap.classList.remove('is-closing');
    doc.body.classList.remove('facepad-open');
  }

  var pad = window.SkriblComposeHost.create({
    frame: frame,
    src: wrap.getAttribute('data-compose'),
    onOpen: function () {
      if (open) return;
      open = true;
      clearTimeout(timer);
      wrap.classList.remove('is-closing');
      wrap.hidden = false;
      doc.body.classList.add('facepad-open');
      /* Read a size, so the glide starts from where the sheet rests closed. */
      void wrap.offsetHeight;
      wrap.classList.add('is-open');
      mark(true);
      try { frame.focus({ preventScroll: true }); } catch (e) { /* not focusable yet */ }
    },
    onClose: function () {
      if (!open) return;
      open = false;
      wrap.classList.add('is-closing');
      wrap.classList.remove('is-open');
      mark(false);
      if (from && from.getClientRects().length && from.focus) from.focus({ preventScroll: true });
      from = null;
      clearTimeout(timer);
      timer = setTimeout(settle, SETTLE_MS);
    },
    onReady: function () { wrap.classList.add('is-ready'); },
    onDone: function (payload) { keep(payload); }
  });

  if (scrim) {
    scrim.addEventListener('transitionend', function (e) { if (e.target === scrim && !open) settle(); });
    /* A tap beside a desk's card puts the Pad away; the drawing stays in it. */
    scrim.addEventListener('click', function () { pad.close(); });
  }
  Array.prototype.forEach.call(openers, function (b) {
    b.addEventListener('click', function (e) {
      e.preventDefault();
      if (saving) return;
      show('');
      from = b.tagName === 'BUTTON' ? b : doc.querySelector('button[data-face-open]');
      pad.open();
    });
  });

  function why(j) {
    if (!j) return say('failed');
    if (j.error === 'rejected' && j.message) return j.message;
    if (j.status === 413) return say('too_big');
    if (j.status === 429) return say('limited');
    if (j.status === 403) return say('stale');
    if (j.status === 401) return say('signed_out');
    if (j.error === 'network') return say('network');
    return say('failed');
  }

  function busy(on) {
    saving = on;
    Array.prototype.forEach.call(openers, function (b) {
      if (b.tagName === 'BUTTON') { b.disabled = on; b.setAttribute('aria-busy', on ? 'true' : 'false'); }
    });
  }

  function keep(payload) {
    busy(true);
    show(say('saving'));
    fetch(wrap.getAttribute('data-save'), {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
      body: JSON.stringify({ payload: payload })
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!j || typeof j !== 'object') j = {};
        j.status = r.status;
        return j;
      });
    }, function () { return { error: 'network' }; }).then(function (j) {
      if (j.ok && j.go) { window.location.assign(j.go); return; }
      busy(false);
      show(why(j));
    });
  }
})();
