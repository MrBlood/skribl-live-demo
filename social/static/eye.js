/* THE EYE, on your own Gallery tab (the owner's "Yes, the eye in view", Nov
 * 14; social/_gallery.html gallery_tile, social.css "THE EYE"). Each of your
 * tiles wears a small eye at its top right. One tap hides the drawing from the
 * Gallery: at once the eye crosses and says "Hidden" and the drawing fades,
 * the site is told (posts.py: /p/<id>/gallery, a post's drawing, by the site's
 * own flag on the post; /b/<id>/gallery, one shown outside a post, by its
 * visibility in Skribl), and once it has said yes the site's own toast
 * (mutes.js, window.SocialToast) says "Hidden from the Gallery" with Undo,
 * clear of the eyes, so the next tap lands on the eye it was meant for.
 * Tapped again, or Undo, and it is back: "Back in the Gallery". A refusal
 * puts the tile back as it was, and the toast says why, kindly.
 *
 * PRESSED FAST: every tap counts. The tile shows the newest wish at once; one
 * change goes to the site at a time, and when it is answered the newest wish
 * goes next if it differs, so the site ends where the last tap left it.
 *
 * Loaded on your own page alone, as the eye is drawn there alone: nobody else
 * sees it, in the page or its source.
 *
 * AND ON YOUR OWN POST'S STRIP OF DRAW-BACKS (Her say; the owner's "All yes to
 * everything", Nov 20): the same eye beside each draw-back's name hides it
 * from your post (posts.py: /p/<id>/shown) and brings it back. The eye says
 * what differs there: the word it asks in (data-eye-key, "shown"), and what
 * the toast says, which names who ("Hidden. Sam isn’t told."). Each change of
 * a tile is told to the page (a "social:eye" event on its cell), which keeps
 * its own counts (posts.js).
 *
 * The words are the page's ([data-eye-words]) and the eye's own: this file
 * says nothing of its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-eye-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';
  var EYES = '[data-eye-cell] [data-eye]';

  function post(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
                        body: JSON.stringify(body || {}) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!j || typeof j !== 'object') j = {};
          j.status = r.status;
          return j;
        });
      }, function () { return { error: 'network' }; });
  }
  function why(j) {
    if (j && j.error === 'network') return WORDS.eye_network;
    if (j && j.status === 429) return WORDS.eye_limited;
    if (j && j.status === 401) return WORDS.eye_signed_out;
    if (j && j.status === 403) return j.error === 'taken_down' ? WORDS.eye_taken_down : WORDS.eye_stale;
    if (j && j.status === 404) return WORDS.eye_gone;
    return WORDS.eye_failed;
  }
  function say(text, undo) {
    if (window.SocialToast && text) window.SocialToast.rise(text, { undo: undo || null, clear: EYES });
  }

  /* What a tile shows: hidden from the Gallery, or in it; its eye pressed
     while it is in, and its link's words saying which. */
  function show(cell, hidden) {
    var was = cell.classList.contains('is-hidden');
    cell.classList.toggle('is-hidden', hidden);
    var eye = cell.querySelector('[data-eye]'), a = cell.querySelector('[data-label-shown]');
    if (eye) eye.setAttribute('aria-pressed', hidden ? 'false' : 'true');
    var words = a && a.getAttribute(hidden ? 'data-label-hidden' : 'data-label-shown');
    if (words) a.setAttribute('aria-label', words);
    if (was !== hidden && window.CustomEvent) cell.dispatchEvent(new CustomEvent('social:eye', { bubbles: true, detail: { hidden: hidden } }));
  }

  /* `want`: in the Gallery (true) or hidden from it. */
  function act(cell, want) {
    cell.__eyeWant = want;
    show(cell, !want);
    if (!cell.__eyeBusy) send(cell);
  }
  function send(cell) {
    var eye = cell.querySelector('[data-eye]'), want = cell.__eyeWant;
    if (!eye) return;
    cell.__eyeBusy = true;
    var body = {};
    body[eye.getAttribute('data-eye-key') || 'gallery'] = want;
    post(eye.getAttribute('data-eye'), body).then(function (j) {
      cell.__eyeBusy = false;
      if (j.ok && cell.__eyeWant !== want) { send(cell); return; }
      if (j.ok) {
        if (want) say(eye.getAttribute('data-eye-back-words') || WORDS.eye_back);
        else say(eye.getAttribute('data-eye-hidden-words') || WORDS.eye_hidden, function () {
          /* Undo hands the focus back to the eye it began from. */
          if (eye.isConnected) eye.focus({ preventScroll: true });
          act(cell, true);
        });
        return;
      }
      cell.__eyeWant = !want;
      show(cell, want);
      say(why(j));
    });
  }

  doc.addEventListener('click', function (e) {
    var eye = e.target && e.target.closest ? e.target.closest(EYES) : null;
    if (!eye) return;
    var cell = eye.closest('[data-eye-cell]');
    e.preventDefault();
    act(cell, cell.classList.contains('is-hidden'));
  });
})();
