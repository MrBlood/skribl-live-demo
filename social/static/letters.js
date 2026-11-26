/* DRAWN LETTERS, WRITTEN IN THE PAD (docs/SOCIAL-SITE.md section 44; the
 * owner's yes, Nov 26, A for all six). _compose.html holds the overlay and the
 * words; letters.py the rules.
 *
 *   SocialLetters.write({ to: handle, first: name, from: what was pressed })
 *   SocialLetters.writeBack({ id: a letter, first, from })
 *
 * OPENED THE WAY DRAW BACK OPENS IT: the Pad over the page (social.js's
 * SocialPadOverlay over lib/composehost.js), its button saying Send and its
 * pill whom it is for ("A letter to Ana · only the two of you see it";
 * composehost say). Writing back, the letter is read from the site
 * (/letters/<id>/write-back: its recipient's alone) and laid faint under the
 * pen (composehost underlay), Draw back's pill saying "Writing back to Ana".
 * The picture and music drawer and the door to Flip step aside, dimmed and
 * saying why: no photos or music at first, and the Pad first.
 *
 * SEND, WITH NO SHEET BETWEEN: what the Pad hands back goes straight to
 * /letters ({to} or {written_on}, and the drawing), and the page goes to the
 * two of you. A letter has no typed words: what it says is drawn.
 *
 * NOTHING IS LOST. A send that does not go says why in the site's toast and
 * keeps the drawing: Write (or Write back) again opens the Pad with it.
 *
 * Pad and Flip: the Pad only. A Flip letter is next, on the list; Skribl's
 * own part (the button's word, the pill, what steps aside) serves both
 * editors already (editor_compose.js). */
(function () {
  'use strict';
  var doc = document;
  var wrap = doc.getElementById('letterPad');
  if (!wrap || !window.SocialPadOverlay) return;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-letter-said] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key) { return WORDS['lt_' + key] || ''; }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';

  /* What the Pad is writing now: { to } or { id }, with `first` for its pill. */
  var now = null, sending = false, asking = false;
  function same(a, b) { return !!a && !!b && a.to === b.to && a.id === b.id; }

  function tell(text) {
    if (!text) return;
    if (window.SocialToast) window.SocialToast.rise(text, { wait: 6000 });
  }
  function why(j) {
    if (j && j.error === 'letter_unsupported' && say('why_' + j.why)) return say('why_' + j.why);
    if (j && j.error && say(j.error)) return say(j.error);
    if (j && j.status === 413) return say('too_big');
    if (j && j.status === 429) return say('limited');
    if (j && j.status === 403) return say('stale');
    if (j && j.status === 401) return say('signed_out');
    return say('failed');
  }
  function aside() { return { media: say('media'), editor: say('editor') }; }

  var over = window.SocialPadOverlay(wrap, {
    onDone: function (payload) { send(payload); }
  });
  if (!over) return;

  function send(payload) {
    if (sending || !now || !payload) return;
    sending = true;
    var body = { payload: payload };
    if (now.id) body.written_on = now.id;
    else body.to = now.to;
    tell(say('sending'));
    fetch(wrap.getAttribute('data-send'), {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!j || typeof j !== 'object') j = {};
        j.status = r.status;
        return j;
      });
    }, function () { return { error: 'network' }; }).then(function (j) {
      sending = false;
      if (j.ok && j.go) {
        /* Sent: the drawing is the letter now, never offered again. */
        over.pad.clear();
        now = null;
        window.location.assign(j.go);
        return;
      }
      tell(why(j));
    });
  }

  /* write({to, first, from}): fresh paper, to `to`. The same letter opened
     again (after a send that did not go) comes back with its drawing. */
  function write(o) {
    if (sending || asking || !o || !o.to) return;
    var next = { to: String(o.to), first: String(o.first || o.to) };
    if (!same(now, next)) {
      over.pad.clear();
      now = next;
    }
    over.pad.say({ button: say('send'), lead: say('letter'), rest: say('to').replace('{first}', now.first), aside: aside() });
    over.open(o.from || null);
  }

  /* writeBack({id, first, from}): their letter faint under the pen. */
  function writeBack(o) {
    if (sending || asking || !o || !o.id) return;
    var next = { id: String(o.id), first: String(o.first || '') };
    if (same(now, next) && over.pad.payload()) {
      /* Back to a letter whose send did not go: as it was left. */
      over.open(o.from || null);
      return;
    }
    asking = true;
    fetch(wrap.getAttribute('data-write-back').replace('__ID__', encodeURIComponent(next.id)), { credentials: 'same-origin' })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; });
      }, function () { return { error: 'network' }; })
      .then(function (j) {
        asking = false;
        if (!j || !j.payload) { tell(why(j)); return; }
        over.pad.clear();
        next.first = j.first || next.first;
        now = next;
        over.pad.say({ button: say('send'), lead: say('back'), rest: say('to').replace('{first}', next.first), aside: aside() });
        over.underlay({ payload: j.payload, first: next.first }, o.from || null);
      });
  }

  /* What a page's own doors call (part three: Write on a friend's page,
     Write back and New letter on the two of you), and what a check reads. */
  window.SocialLetters = {
    write: write,
    writeBack: writeBack,
    writing: function () { return now ? { to: now.to || null, id: now.id || null, first: now.first } : null; },
    isOpen: over.isOpen
  };
})();
