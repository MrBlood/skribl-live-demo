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
 * away, as Cancel does; Tab stays in it). Home has no box of its own (the
 * owner, Nov 14: "Why not make as way to post?"): Make is the way to post.
 * Opened, the words' field has focus, so
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
 * A QUOTE (reposts; the owner's "All yes", Nov 14): the repost sheet's Quote
 * opens this sheet through window.SocialComposer.quote, the post (or a
 * drawing shown outside a post, or since the comment thread's step 3 a
 * comment or a reply) small under the words, which say "Add your words, or
 * draw something…"; a drawing added sits between them. Words alone are
 * enough (the original brings its drawing), so POST wakes once there are
 * words or a drawing, and sends what it quotes ({quote: the post's
 * address}, {quote_drawing: the drawing's id}, or {quote_comment: the
 * comment's address}) with them. Make opens the sheet without the quote: a
 * quote is the Quote door's.
 *
 * POST is dim until there are words or a drawing (aria-disabled: still a
 * button, so a press says what is missing, as the editors' Add does in
 * compose mode). WORDS ALONE ARE A POST (the owner's "I like your pick",
 * Nov 16, to A on the words-only mock), as they are a comment.
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
 * MENTIONS (the owner's "All yes", Nov 15): an @ typed in the words shows the
 * list of people under the line, mentions.js's, as in a comment's box.
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
  var quoted = null;    // what is quoted: { kind: 'p' (a post), 's' (a drawing) or 'c' (a comment), id }
  var back = null;      // DRAW BACK: what is drawn back on, { id, first, payload } (drawBack below)
  var quoteBox = q('[data-compose-quote]');
  var player = null;    // its player (SkriblInline)
  var sending = false;
  var view = 'write';

  var openers = all('[data-make]', doc);
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
  words.addEventListener('input', function () { grow(); ready(); });
  grow();

  /* ---- an @ typed: the list of people under the line (mentions.js) ------- */
  if (window.SocialMentions) window.SocialMentions(words, q('#composeMentions'));

  /* ---- a phone's keyboard: the sheet's foot rides above it ------------------
     social.js's SocialKeyboard reads it (--cmp-kb), and reads it again until
     it rests, as a comment's sheet does (comments.js). */
  var keyboard = window.SocialKeyboard(wrap, 'cmp-kb', function () { return sheet.isOpen(); });
  function lift() { keyboard.watch(); }

  /* ---- what is attached ----------------------------------------------------- */
  /* Ready to post: a drawing; or quoting, words or a drawing. */
  function can() {
    if (back) return !!att;
    return !!att || !!words.value.trim();
  }
  function ready() {
    postBtn.setAttribute('aria-disabled', can() ? 'false' : 'true');
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
    /* A draw-back plays as it will be posted: theirs, then yours (the site
       joins the two when it posts: drawback.py; joined() is its preview). */
    var shows = back && back.payload ? joined(back.payload, payload) : payload;
    player = window.SkriblInline ? window.SkriblInline.attach(draftBox, shows) : null;
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
      /* Drawing back, Draw opens the Pad with theirs under the pen again. */
      if (back && back.payload && kind === 'pad') { over.underlay({ payload: back.payload, first: back.first }, chip); return; }
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
    /* A draw-back that can't be joined yet because of something in YOUR
       drawing says what and how to fix it (Edit drawing, take it out). */
    if (j && j.error === 'drawback_unsupported' && j.on === 'yours' && say('drawback_' + j.why)) return say('drawback_' + j.why);
    if (j && j.error && say(j.error)) return say(j.error);
    if (j && j.status === 413) return say('too_big');
    if (j && j.status === 429) return say('limited');
    if (j && j.status === 403) return say('stale');
    if (j && j.status === 401) return say('signed_out');
    return say('failed');
  }
  postBtn.addEventListener('click', function () {
    if (sending) return;
    if (!can()) { tell(sayBox, say(back ? 'drawback_empty' : quoted ? 'quote_empty' : 'empty')); return; }
    sending = true;
    postBtn.setAttribute('aria-busy', 'true');
    tell(sayBox, say('posting'));
    var body = { words: words.value };
    if (att && att.kind === 'skribl') body.skribl = att.id;
    else if (att) body.payload = att.payload;
    if (quoted) body[quoted.kind === 's' ? 'quote_drawing' : quoted.kind === 'c' ? 'quote_comment' : 'quote'] = quoted.id;
    if (back) body.draw_back = back.id;
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

  /* ---- a quote: the post small under the words ------------------------------- */
  function setQuote(next, html) {
    quoted = next;
    quoteBox.innerHTML = next ? html : '';
    quoteBox.hidden = !next;
    if (next && window.SocialWhen) window.SocialWhen(quoteBox);
    words.setAttribute('placeholder', say(next ? 'say_quote' : 'say'));
    tell(sayBox, '');
    ready();
  }

  /* ---- draw back: theirs faint under your pen -------------------------------- */
  /* The preview of what the site will post (social/drawback.py join, which
     is the one that counts): theirs as it plays, squeezed to about three
     seconds, then yours at your pace, on their shape and paper. */
  var OVERTURE = 3000, CAPS = { keep: Infinity, trim: 250, tight: 50 };
  function joined(orig, mine) {
    var of = (orig.frames && orig.frames[0]) || {}, mf = (mine.frames && mine.frames[0]) || {};
    var op = of.strokes || [], mp = mf.strokes || [];
    var cap = CAPS[orig.pauseMode] || CAPS.tight, at = 0, times = [];
    op.forEach(function (p, i) {
      if (i) { var g = (p.t || 0) - (op[i - 1].t || 0); if (g > 0) at += Math.min(g, cap); }
      times.push(at);
    });
    var k = at > 0 ? Math.min(1, OVERTURE / at) : 1, out = [];
    op.forEach(function (p, i) { var c = Object.assign({}, p); c.t = Math.round(times[i] * k); out.push(c); });
    var t = (out.length ? out[out.length - 1].t : 0) + CAPS.tight;
    mp.forEach(function (p, i) {
      if (i) { var g = (p.t || 0) - (mp[i - 1].t || 0); if (g > 0) t += g; }
      var c = Object.assign({}, p); c.t = Math.round(t); if (!i) c.start = true; out.push(c);
    });
    return Object.assign({}, mine, { canvasSize: orig.canvasSize,
      frames: [Object.assign({}, mf, { strokes: out, strokeGroups: [], background: of.background || null,
                                       photo: null, music: null })] });
  }
  function drawingBack(next) {
    back = next;
    tools.forEach(function (chip) { chip.hidden = !!next && chip.getAttribute('data-compose-open') !== 'pad'; });
    if (yoursBtn) yoursBtn.hidden = !!next;
    /* "Drawing back on Ana’s", at the sheet's top, over the words. */
    var line = q('[data-compose-backline]');
    if (line) {
      line.textContent = '';
      if (next) {
        line.appendChild(doc.createTextNode(say('drawback_on') + ' '));
        var b = doc.createElement('b');
        b.textContent = next.first + '\u2019s';
        line.appendChild(b);
      }
      line.hidden = !next;
    }
    words.setAttribute('placeholder', say(next ? 'say_drawback' : quoted ? 'say_quote' : 'say'));
    ready();
  }
  /* drawBack({ id, first, from }): a post's address and its maker's first
     name (posts.js, the row's pen). The sheet opens, then the Pad over it
     with their drawing under the pen, read from the site (/p/<id>/drawback:
     open to you as a like asks, and one that can be drawn back on). */
  var asking = false;
  function drawBack(o) {
    if (sending || asking || !o || !o.id) return;
    if (att) unattach();
    if (quoted) setQuote(null);
    if (view !== 'write') show('write', true);
    drawingBack({ id: o.id, first: o.first || '', payload: null });
    sheet.open(o.from || null);
    lift();
    grow();
    asking = true;
    tell(sayBox, say('opening'));
    fetch(wrap.getAttribute('data-drawback-url').replace('__ID__', encodeURIComponent(o.id)), { credentials: 'same-origin' })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; });
      }, function () { return { error: 'network' }; })
      .then(function (j) {
        asking = false;
        if (!back || back.id !== o.id) return;
        if (!j || !j.payload) { tell(sayBox, why(j)); return; }
        tell(sayBox, '');
        back.payload = j.payload;
        if (j.first) back.first = j.first;
        if (overs.pad) overs.pad.underlay({ payload: back.payload, first: back.first }, o.from || null);
      });
  }

  /* ---- opening it ----------------------------------------------------------- */
  openers.forEach(function (o) {
    o.addEventListener('click', function (e) {
      e.preventDefault();
      /* Make is a post of your own: no quote, nothing drawn back on. */
      if (back && !sending) { if (att) unattach(); drawingBack(null); }
      if (quoted && !sending) setQuote(null);
      sheet.open(o);
      lift();
      grow();
    });
  });

  /* What a later step reads (verify_composer), and where a quote comes in
     (posts.js, the repost sheet's Quote): whether it is open, what is
     attached and what is quoted. quote({kind, id, html, from}): `kind` 'p'
     (a post), 's' (a drawing) or 'c' (a comment: the comment thread, step
     3), `html` it small (the site's /p/<id>/quoted, /b/..., /c/...), `from`
     what takes focus back. */
  window.SocialComposer = {
    open: function (from) { sheet.open(from || null); lift(); grow(); },
    drawBack: drawBack,
    drawingBack: function () { return back ? { id: back.id, first: back.first, ready: !!back.payload } : null; },
    quote: function (o) {
      if (sending || !o || !o.id) return;
      if (back) { if (att) unattach(); drawingBack(null); }
      if (view !== 'write') show('write', true);
      setQuote({ kind: o.kind === 's' || o.kind === 'c' ? o.kind : 'p', id: o.id }, o.html || '');
      sheet.open(o.from || null);
      lift();
      grow();
    },
    isOpen: sheet.isOpen,
    attached: function () { return att ? { kind: att.kind, id: att.id || null } : null; },
    quoted: function () { return quoted ? { kind: quoted.kind, id: quoted.id } : null; }
  };
})();
