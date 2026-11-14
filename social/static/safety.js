/* Safety (piece 5; the owner's "all yes" on the Safety mock, Nov 12): the
 * sheets in social/_safety.html, raised through social.js's SocialSheet.
 *
 * A PERSON'S ⋯ (somebody else's profile): signed in, Mute @them first (or
 * Unmute @them; mutes.js does it, nothing asked), then Report @them, and
 * signed in Block @them. REPORT @THEM sends a person's own reasons and a note to the site's
 * queue (/report) and says thanks; nothing is taken down by it. BLOCK
 * @THEM? is asked once; once blocked, their profile says so (it reloads),
 * or from a post's ⋯ (posts.js, through window.SocialSafety.block) Home
 * says so. UNBLOCK, on a profile you blocked, lifts it and reloads; without
 * this file it is a form, and comes back to the same page.
 *
 * The words are the page's ([data-safety-words]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-safety-words] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key, vars) {
    var s = WORDS[key] || '';
    Object.keys(vars || {}).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  function tell(box, text) {
    if (!box) return;
    box.textContent = text || '';
    box.hidden = !text;
  }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';

  function send(url, body) {
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
    if (j && j.error && WORDS['s_' + j.error]) return say('s_' + j.error);
    if (j && j.status === 429) return say('s_limited');
    return say('s_failed');
  }
  function sheet(id, o) {
    var wrap = doc.getElementById(id);
    return wrap && window.SocialSheet ? { wrap: wrap, ctl: window.SocialSheet(wrap, o || { doorCloses: false }) } : null;
  }

  var person = sheet('personSheet');
  var report = sheet('personReportSheet', {
    doorCloses: false, ownTouch: '.post-note',
    first: function () { return doc.querySelector('#personReportSheet input[name=reason]:checked'); }
  });
  var block = sheet('blockSheet', {
    doorCloses: false,
    first: function () { return doc.querySelector('#blockSheet [data-make-close]:not(.make-scrim):not(.make-grip)'); }
  });
  var handle = '', opener = null;

  function titled(s, key) {
    var t = s.wrap.querySelector('[data-safety-title]');
    if (t) t.textContent = say(key, { handle: handle });
  }

  /* ---- Report @them ------------------------------------------------------- */
  function openReport(from) {
    if (!report) return;
    var form = report.wrap.querySelector('[data-report-form]');
    form.reset();
    var go = report.wrap.querySelector('[data-safety-send]');
    go.disabled = false;
    go.hidden = false;
    var c = report.wrap.querySelector('.post-sheet-acts [data-make-close]');
    if (c && c.hasAttribute('data-was')) { c.textContent = c.getAttribute('data-was'); c.removeAttribute('data-was'); }
    tell(report.wrap.querySelector('[data-safety-say]'), '');
    titled(report, 'report_title');
    report.ctl.open(from);
  }
  if (report) {
    report.wrap.querySelector('[data-report-form]').addEventListener('submit', function (e) {
      e.preventDefault();
      var go = report.wrap.querySelector('[data-safety-send]'), box = report.wrap.querySelector('[data-safety-say]');
      var picked = report.wrap.querySelector('input[name=reason]:checked');
      go.disabled = true;
      tell(box, say('s_sending'));
      send(report.wrap.getAttribute('data-report'),
           { kind: 'person', target: handle, reason: picked ? picked.value : 'other',
             note: (report.wrap.querySelector('.post-note').value || '').trim() })
        .then(function (j) {
          if (j.status === 202) {
            tell(box, say('s_reported'));
            go.hidden = true;
            var c = report.wrap.querySelector('.post-sheet-acts [data-make-close]');
            if (c) { c.setAttribute('data-was', c.textContent); c.textContent = say('s_done'); }
            return;
          }
          go.disabled = false;
          tell(box, why(j));
        });
    });
  }

  /* ---- Block @them? ------------------------------------------------------- */
  function openBlock(who, from) {
    if (!block || !who) return;
    handle = who;
    opener = from || opener;
    var b = block.wrap.querySelector('[data-safety-block]');
    b.disabled = false;
    tell(block.wrap.querySelector('[data-safety-say]'), '');
    titled(block, 'block_title');
    block.ctl.open(opener);
  }
  if (block) {
    block.wrap.querySelector('[data-safety-block]').addEventListener('click', function (e) {
      var b = e.currentTarget, box = block.wrap.querySelector('[data-safety-say]');
      b.disabled = true;
      tell(box, say('s_blocking'));
      send(block.wrap.getAttribute('data-block').replace('__H__', encodeURIComponent(handle)), {})
        .then(function (j) {
          if (j.ok) {
            /* On their profile, it now says they are blocked; anywhere else,
               Home, without them. */
            var prof = doc.querySelector('[data-profile][data-handle]');
            if (prof && prof.getAttribute('data-handle') === handle) window.location.reload();
            else window.location.assign(block.wrap.getAttribute('data-home') || '/');
            return;
          }
          b.disabled = false;
          tell(box, why(j));
        });
    });
  }

  /* ---- a person's ⋯ --------------------------------------------------------- */
  doc.addEventListener('click', function (e) {
    var m = e.target.closest('[data-person-menu]');
    if (m && person) {
      e.preventDefault();
      handle = person.wrap.getAttribute('data-handle') || '';
      opener = m;
      person.ctl.open(m);
      return;
    }
    var a = e.target.closest('[data-safety]');
    if (!a || !person || !person.wrap.contains(a)) return;
    if (a.getAttribute('data-safety') === 'mute') {
      /* Nothing asked first: the sheet goes down, its focus back on the ⋯. */
      person.ctl.close();
      if (window.SocialMute) {
        window.SocialMute.act({ handle: person.wrap.getAttribute('data-handle') || '',
                                first: person.wrap.getAttribute('data-first') || '',
                                muted: a.getAttribute('data-muted') === 'true', opener: opener });
      }
      return;
    }
    person.ctl.close(true);
    if (a.getAttribute('data-safety') === 'report-person') openReport(opener);
    else if (a.getAttribute('data-safety') === 'block') openBlock(handle, opener);
  });

  /* ---- Unblock, on a profile you blocked ------------------------------------ */
  Array.prototype.forEach.call(doc.querySelectorAll('form[data-unblock]'), function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var b = form.querySelector('button'), box = form.parentNode.querySelector('[data-safety-say]');
      if (b) b.disabled = true;
      tell(box, say('s_unblocking'));
      send(form.getAttribute('action'), {}).then(function (j) {
        if (j.ok) { window.location.reload(); return; }
        if (b) b.disabled = false;
        tell(box, why(j));
      });
    });
  });

  window.SocialSafety = { block: openBlock };
})();
