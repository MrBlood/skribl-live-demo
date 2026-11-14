/* THE COMPOSER (docs/SOCIAL-SITE.md section 17, part two's first piece; the
 * owner's "Yes", Nov 14, to the mock beside Bluesky's new-post screen, B,
 * and to one drawing, one conversation). _compose.html is its markup and its
 * words, compose.py its server side.
 *
 * ONE MAKE, EVERYWHERE. The bar's Make on a phone, the rail's on a desk, and
 * anything else that says it makes something ([data-make]: Activity's "Make
 * a skribl") open the composer, Make's own sheet made tall (social.js's
 * SocialSheet: it glides, a desk's card rises a little as it fades in, Reduce
 * Motion fades it where it sits; a tap outside, Esc and a swipe down put it
 * away, as Cancel does; Tab stays in it). Home's row opens the same sheet
 * ([data-compose-go]: its words with the field ready, its Draw and Flip with
 * that editor rising over the sheet). Opened, the words' field has focus, so
 * a phone's keyboard comes up with it, and the sheet rides above the keyboard.
 * Cancel keeps what is in it for as long as the page is open: the next Make
 * shows it again.
 *
 * WHAT IS ATTACHED is one thing (a post is words and one drawing), each kind
 * saying what Post sends: a drawing Draw or Flip handed back, or a draft
 * added from its editor ({payload}); one of your older drawings, shared
 * outside a post ({skribl: its id}), whose hearts and comments come with it
 * (posts.post_new). A quote post will be a kind of its own here (part two,
 * item 3), opening this same sheet with the post attached. The drawing plays
 * as soon as it is attached (never under Reduce Motion), in Skribl's
 * in-post player, the same one the post will have, with Edit drawing (a
 * drawing made here; an older one is posted as it is) and Remove. With one
 * attached, a tool says so rather than adding a second.
 *
 * POST is dim until a drawing is attached (aria-disabled: still a button, so
 * a press says what is missing, as the editors' Add does in compose mode).
 * It sends the words and the attachment to the site (/posts, the page's
 * token in X-Social-CSRF) and goes to the new post's page; nothing is posted
 * before. The characters left are said at the tools' end, 500 to start.
 *
 * YOURS, "Use one you made": the sheet's words fade out and the picker fades
 * in (and back), the sheet keeping its size, so nothing jumps; under Reduce
 * Motion the same fades, which move nothing. Its one pill (social.js's
 * SocialPill) shows your drafts or your drawings shared outside a post,
 * each list asked for the first time it is shown (/make/yours), Drawings a
 * page at a time with Load more. A draft opens in the editor that made it,
 * over the composer, with the draft on its canvas (composehost's openDraft:
 * a draft is the editor's own work, and only the editor builds what a post
 * carries); closing the editor is back in the picker, and Add to post brings
 * it back attached, the words in place under the editor as it goes. A
 * drawing is attached at once, as it is.
 *
 * The words are the page's ([data-compose-said]): this file says nothing of
 * its own.
 */
(function () {
  'use strict';
  var doc = document;
  var wrap = doc.getElementById('composeSheet');
  if (!wrap || !window.SocialSheet) return;

  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-compose-said] [data-word]'), function (w) {
    WORDS[w.getAttribute('data-word')] = w.textContent;
  });
  function say(key) { return WORDS['cmp_' + key] || ''; }
  function tell(box, text) {
    if (!box) return;
    box.textContent = text || '';
    box.hidden = !text;
  }
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still() { return !!(reduced && reduced.matches); }
  function q(sel) { return wrap.querySelector(sel); }
  function all(sel, root) { return Array.prototype.slice.call((root || wrap).querySelectorAll(sel)); }

  var write = q('[data-compose-view="write"]'), pick = q('[data-compose-view="pick"]');
  var words = q('[data-compose-words]'), left = q('[data-compose-left]');
  var postBtn = q('[data-compose-post]'), sayBox = q('[data-compose-say]');
  var draftWrap = q('[data-compose-draft]'), draftBox = draftWrap.querySelector('.skribl-inline');
  var editBtn = q('[data-compose-edit]'), removeBtn = q('[data-compose-remove]');
  var tools = all('[data-compose-open]'), yoursBtn = q('[data-compose-yours]');
  var backBtn = q('[data-compose-back]'), pill = q('[data-compose-pill]');
  var moreBtn = q('[data-compose-more]'), pickSay = q('[data-compose-pick-say]');
  var lists = {};
  all('[data-compose-list]').forEach(function (l) { lists[l.getAttribute('data-compose-list')] = l; });
  var LIMIT = +(words.getAttribute('maxlength')) || 500;

  var att = null;       // what is attached: { kind: 'payload', payload, over } or { kind: 'skribl', id }
  var player = null;    // its player (SkriblInline)
  var sending = false;
  var view = 'write';

  var openers = all('[data-make], [data-compose-go]', doc);
  var sheet = window.SocialSheet(wrap, {
    openers: openers, doorCloses: false, ownTouch: '.cmp-scroll, .cmp-lists',
    first: function () { return view === 'pick' ? backBtn : words; },
    onSettled: function () {
      /* Put away, it opens on the words next time. */
      if (view !== 'write') show('write', true);
      tell(pickSay, '');
      lift();
    }
  });

  /* ---- the words: they grow, and say how many are left ---------------------- */
  function grow() {
    words.style.height = 'auto';
    if (words.scrollHeight) words.style.height = words.scrollHeight + 'px';
    left.textContent = String(LIMIT - words.value.length);
  }
  words.addEventListener('input', grow);
  grow();

  /* ---- a phone's keyboard: the sheet's foot rides above it ------------------
     The keyboard is what the visual viewport lost at the bottom of the layout
     viewport the sheet is fixed to (iPhone's Safari shrinks only the visual
     one); a pinch's zoom is not a keyboard, so only at a scale of 1. As a
     comment's sheet does (comments.js). NOT SEEN HERE: this box has no phone
     keyboard; the suite stands one in for the visual viewport. */
  function lift() {
    var vv = window.visualViewport, kb = 0;
    if (vv && sheet.isOpen() && Math.abs((vv.scale || 1) - 1) < 0.01) {
      kb = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop));
    }
    if (kb) wrap.style.setProperty('--cmp-kb', kb + 'px');
    else wrap.style.removeProperty('--cmp-kb');
  }
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', lift);
    window.visualViewport.addEventListener('scroll', lift);
  }

  /* ---- what is attached ----------------------------------------------------- */
  function ready() {
    postBtn.setAttribute('aria-disabled', att ? 'false' : 'true');
  }
  function playIt() {
    if (player && player.play && !still()) player.play();
  }
  function attachPayload(payload, over) {
    att = { kind: 'payload', payload: payload, over: over };
    /* A draft added from the picker: the words come back under the editor as
       it goes, unseen (it still covers the sheet in this frame). */
    if (view !== 'write') show('write', true);
    shown(true);
    editBtn.hidden = false;
    player = window.SkriblInline ? window.SkriblInline.attach(draftBox, payload) : null;
    playIt();
    editBtn.focus({ preventScroll: true });
  }
  function attachSkribl(id, payload) {
    att = { kind: 'skribl', id: id };
    shown(true);
    /* AN OLDER DRAWING IS POSTED AS IT IS, so its conversation can come with
       it: nothing to edit here. */
    editBtn.hidden = true;
    player = window.SkriblInline ? window.SkriblInline.attach(draftBox, payload) : null;
    playIt();
  }
  function shown(on) {
    draftWrap.hidden = !on;
    tell(sayBox, '');
    ready();
  }
  function unattach() {
    if (att && att.over) att.over.pad.clear();
    if (player && player.pause) player.pause();
    att = null;
    player = null;
    shown(false);
  }

  editBtn.addEventListener('click', function () {
    if (att && att.over && !sending) att.over.open(editBtn);
  });
  removeBtn.addEventListener('click', function () {
    if (!att || sending) return;
    unattach();
    if (tools[0]) tools[0].focus({ preventScroll: true });
  });

  /* ---- the tools: Draw and Flip, each its editor over the sheet -------------- */
  var overs = {};
  tools.forEach(function (chip) {
    var kind = chip.getAttribute('data-compose-open');
    var over = window.SocialPadOverlay ? window.SocialPadOverlay(doc.getElementById(kind === 'flip' ? 'composeFlip' : 'composePad'), {
      openers: [chip],
      onDone: function (payload) { attachPayload(payload, over); }
    }) : null;
    overs[kind] = over;
    chip.addEventListener('click', function () {
      if (!over || sending) return;
      if (att) { tell(sayBox, say('one_drawing')); return; }
      tell(sayBox, '');
      over.open(chip);
    });
  });

  /* ---- Post ----------------------------------------------------------------- */
  function post(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
                        body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!j || typeof j !== 'object') j = {};
          j.status = r.status;
          return j;
        });
      }, function () { return { error: 'network' }; });
  }
  function why(j) {
    if (j && j.error && say(j.error)) return say(j.error);
    if (j && j.status === 413) return say('too_big');
    if (j && j.status === 429) return say('limited');
    if (j && j.status === 403) return say('stale');
    if (j && j.status === 401) return say('signed_out');
    return say('failed');
  }
  postBtn.addEventListener('click', function () {
    if (sending) return;
    if (!att) { tell(sayBox, say('no_drawing')); return; }
    sending = true;
    postBtn.setAttribute('aria-busy', 'true');
    tell(sayBox, say('posting'));
    var body = { words: words.value };
    if (att.kind === 'skribl') body.skribl = att.id;
    else body.payload = att.payload;
    post(wrap.getAttribute('data-post-new'), body).then(function (j) {
      if (j.ok && j.go) { window.location.assign(j.go); return; }
      sending = false;
      postBtn.removeAttribute('aria-busy');
      tell(sayBox, why(j));
    });
  });

  /* ---- two views, one sheet: the words, and "Use one you made" -------------- */
  /* One fades out, then the other fades in where it stood (the sheet keeps
     its size); `now`, put there unseen (the sheet has gone). Focus follows. */
  var swapping = null;
  /* `focus`: what takes focus once the next view is in (else Back, going to
     the picker, or Yours, coming back from it). */
  function show(next, now, focus) {
    if (next === view && !swapping) return;
    var from = next === 'pick' ? write : pick, to = next === 'pick' ? pick : write;
    view = next;
    if (swapping) { swapping.cancel(); swapping = null; }
    function land(out) {
      from.hidden = true;
      /* The fade out held the view at nothing ('forwards'); hidden now, it
         lets go, or it would still hold it there the next time it shows. */
      if (out) out.cancel();
      to.hidden = false;
      if (next === 'pick' && window.SocialPill) window.SocialPill.place(pill, true);
      if (now) return;
      var f = focus || (next === 'pick' ? backBtn : yoursBtn);
      if (f) f.focus({ preventScroll: true });
      if (!to.animate) return;
      swapping = to.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease' });
      swapping.onfinish = function () { swapping = null; };
    }
    if (now || !from.animate || from.hidden) { land(null); return; }
    var out = swapping = from.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, easing: 'ease', fill: 'forwards' });
    out.onfinish = function () {
      swapping = null;
      land(out);
    };
  }

  /* ---- Yours: the picker ------------------------------------------------------ */
  var asked = {};       // each list: 'asking', or 'shown'
  var next = null;      // the next page of drawings, if there is one
  function tab() {
    var b = pill.querySelector('button[aria-pressed="true"]');
    return b ? b.getAttribute('data-pick') : 'drafts';
  }
  function ask(which, before) {
    if (!before && asked[which]) return;
    asked[which] = 'asking';
    tell(pickSay, '');
    if (before) moreBtn.disabled = true;
    var url = wrap.getAttribute('data-yours') + '?tab=' + encodeURIComponent(which)
      + (before ? '&before=' + encodeURIComponent(before) : '');
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (j) {
        var list = lists[which];
        if (before) {
          var grid = list.querySelector('[data-compose-grid]');
          var box = doc.createElement('div');
          box.innerHTML = j.html || '';
          Array.prototype.slice.call(box.children).forEach(function (t) { grid.appendChild(t); });
        } else {
          list.innerHTML = j.html || '';
          if (list.animate && !list.hidden) list.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease' });
        }
        asked[which] = 'shown';
        if (which === 'drawings') next = j.next || null;
        moreBtn.disabled = false;
        moreBtn.hidden = !(tab() === 'drawings' && next);
      }, function () {
        if (!before) asked[which] = null;
        moreBtn.disabled = false;
        tell(pickSay, say('network'));
      });
  }
  function choose(which) {
    var b = pill.querySelector('button[data-pick="' + which + '"]');
    if (!b) return;
    if (window.SocialPill) window.SocialPill.choose(pill, b);
    Object.keys(lists).forEach(function (k) { lists[k].hidden = k !== which; });
    moreBtn.hidden = !(which === 'drawings' && next);
    tell(pickSay, '');
    ask(which);
  }
  yoursBtn.addEventListener('click', function () {
    if (sending) return;
    if (att) { tell(sayBox, say('one_drawing')); return; }
    tell(sayBox, '');
    show('pick');
    ask(tab());
  });
  backBtn.addEventListener('click', function () { show('write'); });
  pill.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-pick]');
    if (b) choose(b.getAttribute('data-pick'));
  });
  moreBtn.addEventListener('click', function () { if (next) ask('drawings', next); });

  /* A tile picked: a draft opens in the editor that made it, over the sheet
     (the picker under it, so closing the editor is back to the picker; Add
     to post attaches it and the words come back: attachPayload); a drawing
     is fetched as every in-post player fetches a posted one (Skribl's
     address, the composer's data-skribl-api), attached as it is, and the
     words fade back in with it under them, Remove ready. */
  var fetching = false;
  pick.addEventListener('click', function (e) {
    var d = e.target.closest('[data-pick-draft]');
    if (d) {
      var over = overs[d.getAttribute('data-kind') === 'flip' ? 'flip' : 'pad'];
      if (!over || att || sending) return;
      tell(pickSay, '');
      over.openDraft(d.getAttribute('data-pick-draft'), d);
      return;
    }
    var t = e.target.closest('[data-pick-drawing]');
    if (!t || fetching || att || sending) return;
    var id = t.getAttribute('data-pick-drawing');
    fetching = true;
    tell(pickSay, say('opening'));
    fetch(wrap.getAttribute('data-skribl-api') + '/' + encodeURIComponent(id), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (body) {
        fetching = false;
        tell(pickSay, '');
        attachSkribl(id, (body && (body.skribl || body.payload)) || body);
        show('write', false, removeBtn);
      }, function () {
        fetching = false;
        tell(pickSay, say('open_failed'));
      });
  });

  /* ---- opening it ----------------------------------------------------------- */
  openers.forEach(function (o) {
    o.addEventListener('click', function (e) {
      e.preventDefault();
      var go = o.getAttribute('data-compose-go');
      sheet.open(o);
      lift();
      grow();
      /* Home's Draw and Flip: their editor rises over the sheet. */
      if ((go === 'pad' || go === 'flip') && overs[go]) {
        if (att) { tell(sayBox, say('one_drawing')); return; }
        overs[go].open(tools.filter(function (c) { return c.getAttribute('data-compose-open') === go; })[0] || o);
      }
    });
  });

  /* What a later step reads (verify_composer), and where a quote post will
     come in: whether it is open, and what is attached. */
  window.SocialComposer = {
    open: function (from) { sheet.open(from || null); lift(); grow(); },
    isOpen: sheet.isOpen,
    attached: function () { return att ? { kind: att.kind, id: att.id || null } : null; }
  };
})();
