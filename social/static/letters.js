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
    if (window.SocialToast) window.SocialToast.rise(text, { wait: 6000, plain: true });
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

  /* ---- THE DOORS (the pages): Write on a friend's page and on Letters'
     list of people, New letter and Write back on the two of you ---------- */
  doc.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target : null;
    if (!t) return;
    var w = t.closest('[data-lt-write]');
    if (w) { e.preventDefault(); write({ to: w.getAttribute('data-handle'), first: w.getAttribute('data-first'), from: w }); return; }
    var wb = t.closest('[data-lt-write-back]');
    if (wb) { e.preventDefault(); writeBack({ id: wb.getAttribute('data-id'), first: wb.getAttribute('data-first'), from: wb }); }
  });

  /* ---- THE TWO OF YOU ---------------------------------------------------- */
  var page = doc.querySelector('[data-letters-with]');
  if (page) twoOfYou(page);

  function post(url) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token }, body: '{}' })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; });
      }, function () { return { error: 'network' }; });
  }

  function twoOfYou(page) {
    var PAGE = {};
    Array.prototype.forEach.call(doc.querySelectorAll('[data-lt-page-said] [data-word]'), function (w) {
      PAGE[w.getAttribute('data-word')] = w.textContent;
    });
    var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    function at(attr, id) { return page.getAttribute(attr).replace('__ID__', encodeURIComponent(id)); }

    /* OPENED AS IT STARTS PLAYING, never by this page's GET: once, the first
       time the player of a letter that came to you plays (its own first draw,
       or a tap under Reduce Motion). */
    function watchOpen(sheet) {
      var box = sheet.querySelector('[data-skribl-inline]');
      if (!box) return;
      var said = false;
      function playing() {
        if (said || !box.classList.contains('is-playing')) return;
        said = true;
        sheet.removeAttribute('data-new');
        post(at('data-open', sheet.getAttribute('data-letter')));
      }
      if (window.MutationObserver) new MutationObserver(playing).observe(box, { attributes: true, attributeFilter: ['class'] });
      playing();
    }
    var fresh = Array.prototype.slice.call(page.querySelectorAll('.lt-sheet[data-new]'));
    fresh.forEach(watchOpen);
    /* IT DRAWS ITSELF THE FIRST TIME: the newest one waiting, at the
       writer's pace; then it rests (the player's own end), Watch again any
       time. Not under Reduce Motion: a tap plays it. */
    if (window.SkriblInline) {
      window.SkriblInline.mount(page);
      if (fresh.length && !(reduced && reduced.matches)) {
        var box = fresh[0].querySelector('[data-skribl-inline]');
        var p = box ? window.SkriblInline.find(box.getAttribute('data-skribl-id')) : null;
        var after = window.BloobySplash ? window.BloobySplash.after : function (fn) { fn(); };
        if (p && p.play) after(function () { fresh[0].scrollIntoView({ block: 'nearest' }); p.play(); });
      }
    }

    /* ---- A SHEET'S ⋯ -------------------------------------------------------- */
    var sheetWrap = doc.getElementById('letterSheet'), reportWrap = doc.getElementById('letterReportSheet');
    var menu = sheetWrap && window.SocialSheet ? window.SocialSheet(sheetWrap, { doorCloses: false }) : null;
    var report = reportWrap && window.SocialSheet ? window.SocialSheet(reportWrap, { doorCloses: false, ownTouch: '.post-note' }) : null;
    var on = null, opener = null;
    function sayIn(wrap, text) {
      var b = wrap.querySelector('[data-lt-say]');
      if (!b) return;
      b.textContent = text || '';
      b.hidden = !text;
    }
    page.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('[data-lt-more]') : null;
      if (!b || !menu) return;
      on = b.closest('.lt-sheet');
      opener = b;
      var mine = on.getAttribute('data-to-me') === 'no';
      sheetWrap.querySelector('[data-lt-act="take-back"]').hidden = !on.hasAttribute('data-take-back-ok');
      sheetWrap.querySelector('[data-lt-act="delete"]').hidden = on.hasAttribute('data-take-back-ok');
      sheetWrap.querySelector('[data-lt-act="report"]').hidden = mine || !on.hasAttribute('data-report-ok');
      sayIn(sheetWrap, '');
      menu.open(b);
    });
    function gone(text) {
      var s = on;
      menu.close();
      if (window.SocialToast) window.SocialToast.rise(text, { plain: true });
      if (!s) return;
      /* It folds away where it was, so nothing below it jumps (Reduce Motion:
         it goes at once). */
      if (!s.animate || (reduced && reduced.matches)) { s.remove(); return; }
      s.style.overflow = 'hidden';
      var h = s.getBoundingClientRect().height;
      var a = s.animate([{ opacity: 1, height: h + 'px' }, { opacity: 0, height: '0px', marginTop: '0px', marginBottom: '0px', paddingTop: '0px', paddingBottom: '0px' }],
                        { duration: 260, easing: 'ease' });
      a.onfinish = function () { s.remove(); };
    }
    if (sheetWrap) sheetWrap.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('[data-lt-act]') : null;
      if (!b || !on) return;
      var act = b.getAttribute('data-lt-act'), id = on.getAttribute('data-letter');
      if (act === 'block') { menu.close(); if (window.SocialSafety) window.SocialSafety.block(page.getAttribute('data-handle'), opener); return; }
      if (act === 'report') { menu.close(); sayIn(reportWrap, ''); report.open(opener); return; }
      sayIn(sheetWrap, PAGE.sending);
      post(at(act === 'take-back' ? 'data-take-back' : 'data-delete', id)).then(function (j) {
        if (j.ok) { gone(act === 'take-back' ? PAGE.taken : PAGE.deleted); return; }
        sayIn(sheetWrap, j.error === 'letter_opened' ? PAGE.opened : PAGE.failed);
        if (j.error === 'letter_opened') {
          on.removeAttribute('data-take-back-ok');
          sheetWrap.querySelector('[data-lt-act="take-back"]').hidden = true;
          sheetWrap.querySelector('[data-lt-act="delete"]').hidden = false;
        }
      });
    });
    var form = reportWrap ? reportWrap.querySelector('[data-lt-report-form]') : null;
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!on) return;
      var picked = form.querySelector('input[name="reason"]:checked');
      if (!picked) { sayIn(reportWrap, PAGE.pick); return; }   /* nothing picked for them */
      sayIn(reportWrap, PAGE.sending);
      fetch(page.getAttribute('data-report'), {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
        body: JSON.stringify({ kind: 'letter', target: on.getAttribute('data-letter'), reason: picked ? picked.value : 'other',
                               note: form.querySelector('textarea').value || null })
      }).then(function (r) { return r.status; }, function () { return 0; }).then(function (st) {
        if (st === 202) { report.close(); if (window.SocialToast) window.SocialToast.rise(PAGE.reported, { plain: true }); return; }
        sayIn(reportWrap, PAGE.failed);
      });
    });
  }

  /* What a page's own doors call (Write on a friend's page, Write back and
     New letter on the two of you), and what a check reads. */
  window.SocialLetters = {
    write: write,
    writeBack: writeBack,
    writing: function () { return now ? { to: now.to || null, id: now.id || null, first: now.first } : null; },
    isOpen: over.isOpen
  };
})();
