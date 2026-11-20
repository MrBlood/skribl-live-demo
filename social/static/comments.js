/* Comments (phase 2; the comments mock and the owner's "all yes on both",
 * Nov 12): a post's own page, and a drawing's (post.html,
 * social/_comments.html), the same section on both: the page names its own
 * addresses (data-new, data-more, data-drop).
 *
 * THE BOX IS NOT A CARD SITTING THERE (the owner, Nov 13: "The comment needs
 * to be an icon not a card. It takes up too much room sitting there"), AND
 * ONE LINE OPENS IT (the Calm Post Page; the owner's "All yes to everything.
 * Make it smart and beautiful", Nov 20): the answer bar's "Say something…"
 * (_comments.html answer_bar), the one place to answer on the page. On a
 * phone the box rises on Make's own sheet, "Say something to Mira"; on a
 * desk it glides open over the line, in its place. Put away (the dimmed
 * page, a drag down or Esc on a phone; Esc or a press elsewhere on a desk),
 * it keeps what was typed. Signed out, the line raises "Say something?",
 * whose Sign in comes back with the box open (#say). Until Nov 20 a round
 * icon at the end of a "Comments" heading opened it, and "Say the first
 * thing" stood where the comments would be: the same thing offered three
 * times on a page with nothing on it yet.
 *
 * IN THE BOX the words grow as they are typed and say how many are left once
 * few are; Post sends them (/social/p/<id>/comments, or a drawing's
 * /social/b/<id>/comments; the page's token in X-Social-CSRF), the box goes,
 * and the new comment opens its room at the top, newest first, fades in and
 * glows a moment, the count with it. With nothing written or drawn, Post says
 * so and sends nothing.
 *
 * A DRAWING ANSWER (the mock's 6): Draw and Flip open Skribl's editor over the
 * post in compose mode (social.js's SocialPadOverlay over lib/composehost.js,
 * as Home's composer; no gallery tick: a drawing answer is unlisted). Its Add
 * hands the drawing back, and it waits in the box in Skribl's in-post player,
 * the one the comment will have, with Edit drawing (the editor again, the
 * drawing in it) and Remove, until Post sends it with the words. A comment's
 * drawing is still until tapped: posts.js plays only the post's own.
 *
 * REPLY OPENS THE SAME BOX for the comment: a phone's sheet titled "Reply to
 * Theo", Theo's words under it; on a desk under its conversation, after its
 * replies ("Reply to Theo…"), the page gliding to it if it is below the
 * screen. Reply again, Esc or a posted reply puts it away. KIND, NEVER JUMPY:
 * everything that moves glides (social.css: the sheet, the fold, a comment's
 * room), the box fades in as its room opens, and under Reduce Motion things
 * are put in place and fade.
 *
 * THE THREAD (the comment thread, step 1; the owner's yes, Nov 17), BLUESKY'S
 * WAY WITH OUR LOOK (the owner's yes, Nov 18, after reading Bluesky's own
 * thread code): a list shows the direct replies to what its page is about,
 * each with the count by its talk cloud and its conversation followed down
 * under it in the same column (below). A TAP ON ONE OPENS ITS OWN PAGE: not
 * on a link, a button or its drawing (which plays), nor when the press ends
 * a selection. ON A COMMENT'S OWN PAGE (comment.html) the box replies to
 * that comment, a new reply lands at the end of its replies (oldest first),
 * and back goes where you were.
 *
 * A COMMENT'S ⋯, "This comment" (social.js's SocialSheet, as the post's):
 * Copy link and Share… (its own page), then on your own Delete comment; on
 * somebody else's on your own post Remove from my post and Report this
 * comment; anybody else's Report this comment. Delete and Remove go at once:
 * the comment fades out, or, with replies under it, becomes its place
 * ("This comment was deleted"), gliding to its new height (becomePlace),
 * and a place with nothing left under it fades too (on its own page, the
 * page goes to what it replied to, or shows the place); Report rises as a
 * sheet of its own with a post's reasons, into the site's own queue.
 *
 * LOAD MORE brings the next page of comments in place.
 *
 * SOMEBODY YOU MUTED (mutes; the owner's C): their comment or reply is one
 * quiet line in its place, "Someone you muted said something. Show"
 * (_comments.html), its room the line's height, the comment hidden for real
 * under it. Show opens it for this visit: the line fades, the room opens to
 * the comment's own height while what is under it moves down, and the
 * comment fades in; never both more than half there at once. Under Reduce
 * Motion the room is put there while neither can be seen, and the fades
 * remain. The line's words wrap in a narrow column, and its room follows.
 *
 * OPENED AT A COMMENT (#c-<id>, a row in Activity; notifications): it glows
 * a moment in the note's tint, and a drawing answer draws itself once (below).
 *
 * The words are the page's ([data-comment-words]): this file says nothing of
 * its own. Times are said by social.js (window.SocialWhen).
 */
(function () {
  'use strict';
  var doc = document;
  var root = doc.querySelector('[data-comments]');
  if (!root) return;
  /* A COMMENT'S OWN PAGE (comment.html): the comment it is about, and whose
     replies stand where a post's comments do. Its box replies to it. */
  var subject = root.getAttribute('data-subject') || '';
  var subjectEl = subject ? doc.querySelector('[data-cm-subject]') : null;
  var WORDS = {};
  Array.prototype.forEach.call(doc.querySelectorAll('[data-comment-words] [data-word]'), function (w) {
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

  function answered(p) {
    return p.then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!j || typeof j !== 'object') j = {};
        j.status = r.status;
        return j;
      });
    }, function () { return { error: 'network' }; });
  }
  function send(url, body) {
    return answered(fetch(url, { method: 'POST', credentials: 'same-origin',
                                 headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
                                 body: JSON.stringify(body || {}) }));
  }
  function get(url) {
    return answered(fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } }));
  }
  function why(j) {
    if (j && j.error === 'rejected' && j.message) return j.message;
    if (j && j.error && WORDS['c_' + j.error]) return say('c_' + j.error);
    if (j && j.status === 413) return say('c_too_big');
    if (j && j.status === 429) return say('c_limited');
    if (j && j.status === 403) return say('c_stale');
    if (j && j.status === 401) return say('c_signed_out');
    if (j && j.status === 404) return say('c_gone');
    return say('c_failed');
  }

  /* THE ANSWER BAR (_comments.html answer_bar): the one place to answer, in
     the page and outside the comments' own section; `home` is the room it
     shares with the box on a desk. */
  var bar = doc.querySelector('[data-ans-bar]');
  var home = bar ? bar.parentNode : null;
  var list = root.querySelector('[data-cm-list]');
  var labelEl = root.querySelector('[data-cm-head]');
  var countEl = root.querySelector('[data-cm-count]');
  var nounEl = root.querySelector('[data-cm-noun]');
  var pageSay = root.querySelector('[data-cm-page-say]');
  /* HOW MANY, IN THE SMALL LABEL ("7 comments"), AND NO LABEL AT NONE (the
     Calm Post Page): its number and its noun, one or many. It fades in as
     the first one comes; as the last one goes it fades with it and leaves
     once that one's room has closed, so nothing under it is moved twice. */
  var labelOff = 0;
  function setCount(n) {
    if (!countEl || typeof n !== 'number') return;
    countEl.textContent = String(n);
    if (nounEl) nounEl.textContent = nounEl.getAttribute(n === 1 ? 'data-one' : 'data-many') || nounEl.textContent;
    if (!labelEl) return;
    clearTimeout(labelOff);
    if (n) {
      labelEl.classList.remove('is-going');
      if (labelEl.hidden) { labelEl.hidden = false; labelEl.classList.add('is-new'); }
      return;
    }
    if (labelEl.hidden) return;
    labelEl.classList.remove('is-new');
    labelEl.classList.add('is-going');
    labelOff = setTimeout(function () { labelEl.hidden = true; labelEl.classList.remove('is-going'); }, 420);
  }
  /* HOW MANY, after one came or went: the server's count of the post's or
     the drawing's (`n`); on a comment's own page its own replies, counted
     here by `by`, and the count in its row with them. */
  function counted(n, by) {
    if (!subjectEl) { setCount(n); return; }
    var now = Math.max(0, (+(countEl && countEl.textContent) || 0) + by);
    setCount(now);
    var row = subjectEl.querySelector(':scope > .cm-row .post-count');
    if (!row) return;
    var c = row.querySelector('span');
    if (!c && now) { c = doc.createElement('span'); row.appendChild(c); }
    if (c) { if (now) c.textContent = String(now); else row.removeChild(c); }
  }
  /* ---- BLUESKY'S WAY, OUR LOOK (the owner's yes, Nov 18) --------------------
     A comment in a list says how many replies are under it beside its talk
     cloud, and under it its conversation is followed down in the same
     column (_comments.html chain_of; comments.py _chains): its first reply,
     the first reply to that, ten deep, then "Read N more replies". A tap on
     a comment opens its own page. A reply posted continues the conversation
     where it is followed down to the one it answers; anywhere else the
     count by that one's talk cloud takes it and glows. Posting and deleting
     answer every count on the way up (j.counts). */
  var CHAIN_MAX = 10;
  function plural(n, one, many) { return n === 1 ? say(one) : say(many, { n: n }); }
  function proto(name) {
    var t = doc.querySelector('template[' + name + ']');
    return t ? t.content.firstElementChild.cloneNode(true) : null;
  }
  /* HOW MANY, after a reply came or went: beside its talk cloud, in its
     Reply's name, and in a "Read N more replies" after it. */
  function tallyTo(li, n) {
    if (n) li.setAttribute('data-replies', String(n)); else li.removeAttribute('data-replies');
    var acts = li.querySelector(':scope > .cm-main > .cm-acts');
    var host = acts && (acts.querySelector('[data-cm-answer]') || acts.querySelector('.cm-tally'));
    if (host) {
      var c = host.querySelector('.cm-n');
      if (n && !c && !host.classList.contains('cm-tally')) {
        c = proto('data-cm-n-proto');
        host.insertBefore(c, host.querySelector('.cm-word'));
      }
      if (c) { if (n) c.textContent = String(n); else c.parentNode.removeChild(c); }
      if (host.hasAttribute('data-cm-answer')) {
        if (n) host.setAttribute('aria-label', plural(n, 'c_reply_one', 'c_reply_many'));
        else host.removeAttribute('aria-label');
      }
    }
    var rm = li.nextElementSibling;
    if (rm && rm.classList.contains('cm-rm') && rm.getAttribute('data-rm') === li.getAttribute('data-comment')) {
      if (n) {
        rm.setAttribute('data-n', String(n));
        rm.querySelector('[data-rm-words]').textContent = plural(n, 'c_more_one', 'c_more_many');
      } else rm.parentNode.removeChild(rm);
    }
  }
  function recount(counts) {
    Object.keys(counts || {}).forEach(function (id) {
      var li = doc.getElementById('c-' + id);
      if (li) tallyTo(li, +counts[id] || 0);
    });
  }
  /* A count that just took a reply glows a moment in the landing's tint
     (social.css, .is-glow). */
  function glowCount(li) {
    var acts = li.querySelector(':scope > .cm-main > .cm-acts');
    var c = acts && acts.querySelector('[data-cm-answer], .cm-tally');
    if (!c) return;
    c.classList.add('is-glow');
    setTimeout(function () { c.classList.remove('is-glow'); }, GLOW_MS);
  }
  /* WHERE A REPLY TO `top` CONTINUES ITS CONVERSATION: right under it,
     where the conversation is followed down to it (a comment in the list,
     or the last of the conversation under one), it is its first reply (no
     other under it: `first`), and there is room for one more (ten deep);
     null anywhere else, where its count says it instead. */
  function landing(top, first) {
    if (!first || top.classList.contains('is-gone')) return null;
    if (top.parentNode === list) {
      if (top.querySelector(':scope > .cm-chain')) return null;
      var ol = doc.createElement('ol');
      ol.className = 'cm-chain';
      top.insertBefore(ol, fold && fold.parentNode === top ? fold : null);
      return { parent: ol, before: null };
    }
    var chain = top.parentNode;
    if (!chain || !chain.classList || !chain.classList.contains('cm-chain') || top.nextElementSibling) return null;
    if (chain.querySelectorAll(':scope > .cm').length >= CHAIN_MAX) return null;
    return { parent: chain, before: null };
  }
  /* What arrives later is said as what was there: its times, and its
     drawing's player (still until tapped, as Skribl asks of a feed that adds
     posts later). */
  function settle(el) {
    if (window.SocialWhen) window.SocialWhen(el);
    if (window.SkriblInline) window.SkriblInline.mount(el);
    fitQuiet(el);
  }

  /* ---- SOMEBODY YOU MUTED: one quiet line, and Show -------------------------- */
  /* The fold's room is its line's height, which grows when its words wrap. */
  function fitQuiet(el) {
    var all = el.matches && el.matches('.cm.is-quiet') ? [el] : [];
    Array.prototype.forEach.call(el.querySelectorAll ? el.querySelectorAll('.cm.is-quiet') : [], function (li) { all.push(li); });
    all.forEach(function (li) {
      var f = li.querySelector(':scope > .cm-fold-line');
      if (f) li.style.setProperty('--cm-fold-h', Math.ceil(f.getBoundingClientRect().height) + 'px');
    });
  }
  var refit = 0;
  window.addEventListener('resize', function () {
    cancelAnimationFrame(refit);
    refit = requestAnimationFrame(function () { fitQuiet(root); });
  });
  var EASE = 'cubic-bezier(0.4, 0, 0.2, 1)';
  /* SHOW: the line fades (0.16s), the room opens to the comment's own height
     (0.34s from 0.06s) and the comment fades in (from 0.18s). Once open, the
     line goes and the comment is a comment again; the focus, if it was on
     the line, goes to the comment's first control. */
  function show(li) {
    var f = li.querySelector(':scope > .cm-fold-line');
    var main = li.querySelector(':scope > .cm-main'), face = li.querySelector(':scope > .face-ring');
    if (!f || !main || li.hasAttribute('data-showing')) return;
    li.setAttribute('data-showing', '');
    var had = doc.activeElement === f;
    var was = main.getBoundingClientRect().height;
    main.style.height = 'auto';
    var h = main.getBoundingClientRect().height;
    main.style.height = was + 'px';
    void main.offsetHeight;
    var rm = still(), fade = rm ? 'opacity 0.22s ease 0.16s' : 'opacity 0.24s ease 0.18s';
    main.style.transition = (rm ? 'height 0s linear 0.16s' : 'height 0.34s ' + EASE + ' 0.06s') + ', ' + fade;
    if (face) face.style.transition = fade;
    f.style.transition = 'opacity 0.16s ease';
    main.style.height = h + 'px';
    f.style.opacity = '0';
    f.style.pointerEvents = 'none';
    [face, main].forEach(function (x) { if (x) { x.style.visibility = 'visible'; x.style.opacity = '1'; } });
    var done = false, t = 0;
    function end() {
      if (done) return;
      done = true;
      clearTimeout(t);
      main.removeEventListener('transitionend', on);
      if (f.parentNode) f.parentNode.removeChild(f);
      li.classList.remove('is-quiet');
      li.removeAttribute('data-showing');
      li.style.removeProperty('--cm-fold-h');
      [face, main].forEach(function (x) {
        if (!x) return;
        ['height', 'transition', 'visibility', 'opacity'].forEach(function (k) { x.style.removeProperty(k); });
      });
      if (had) {
        var next = main.querySelector('.cm-acts button');
        if (next) next.focus({ preventScroll: true });
      }
    }
    function on(e) { if (e.target === main && e.propertyName === 'opacity') end(); }
    main.addEventListener('transitionend', on);
    t = setTimeout(end, 800);
  }
  fitQuiet(root);

  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still() { return !!(reduced && reduced.matches); }
  var desk = window.matchMedia ? window.matchMedia('(min-width: 900px)') : null;
  function onDesk() { return !!(desk && desk.matches); }

  /* WHERE IT CAN BE SEEN: something below what the screen shows (above a
     phone's bar, and the answer bar standing on it) is glided to, never
     jumped to; under Reduce Motion the page is simply put there. */
  function reveal(el) {
    var r = el.getBoundingClientRect(), floor = window.innerHeight;
    var nav = doc.querySelector('body > .nav');
    if (nav) {
      var b = nav.getBoundingClientRect();
      if (b.top > floor / 2) floor = b.top;           // a phone's bar along the bottom
    }
    if (bar && !onDesk()) floor = Math.min(floor, bar.getBoundingClientRect().top);
    var over = r.bottom - (floor - 12);
    if (over > 0) window.scrollBy({ top: Math.min(over, r.top - 12), behavior: still() ? 'auto' : 'smooth' });
  }

  /* A GLIDE'S END: `fn` once `el`'s `prop` has finished moving, or a little
     after it should have (its transitionend may never come: a tab put in the
     background mid-glide). Under Reduce Motion nothing glides: at once, and
     null. Otherwise it answers a way to call it off. */
  function after(el, prop, ms, fn) {
    if (still()) { fn(); return null; }
    var done = false, t = 0;
    function on(e) { if (e.target === el && e.propertyName === prop) end(); }
    function off() { done = true; clearTimeout(t); el.removeEventListener('transitionend', on); }
    function end() { if (done) return; off(); fn(); }
    el.addEventListener('transitionend', on);
    t = setTimeout(end, ms);
    return off;
  }

  /* ---- THE BOX, FOLDED AWAY BEHIND THE ANSWER BAR'S LINE -------------------------
     The comment box is not a card sitting there (the owner, Nov 13: "It takes
     up too much room sitting there"); the answer bar's line, "Say
     something…", opens it (the Calm Post Page, Nov 20). One box, wherever it
     opens, keeping what was typed for as long as the page is open:
     - A PHONE: a tap on the line raises Make's own sheet with the box on it,
       its field ready to type in, "Say something to Mira"; Answer raises it
       as "Answer Theo", Theo's words in a line under it. A tap on the dimmed
       page, a drag down or Esc puts it away (social.js's SocialSheet). On a
       phone's keyboard it rides above it.
     - A DESK: a click glides the box open in the line's own place (the fold,
       in the room the two share: social.css .ans), what is under it sliding
       down while it fades in and the line fades away under it: the line
       becomes the box. Esc or a press anywhere else folds it away, and the
       line is back. Answer glides it open under that conversation instead
       ("Answer Theo…"), and the page glides to it if it is below the
       screen. Open in one place and asked for in another, it folds away
       there first, then opens.
     - POSTED: the box goes (the sheet glides down, or the fold folds away) as
       the new comment opens its room, fades in and glows a moment in the
       landing's tint (Activity's), which then fades. On a desk the two move in
       step, so what is under them moves only by how much taller or shorter the
       comment is than the box. */
  var box = doc.querySelector('[data-cm-box]');
  var fold = doc.querySelector('[data-cm-fold]');
  var foldIn = fold ? fold.querySelector('.cm-fold-in') : null;
  /* What opens the box for something new: the answer bar's line (`icon`,
     its name from when it was one), and on a comment's own page the Reply
     in that comment's row. */
  var sayers = Array.prototype.slice.call(doc.querySelectorAll('[data-cm-new]'));
  var icon = bar ? bar.querySelector('.cm-say') : null;
  var words = box ? box.querySelector('[data-cm-words]') : null;
  var label = box ? box.querySelector('[data-cm-label]') : null;
  var left = box ? box.querySelector('[data-cm-left]') : null;
  var postBtn = box ? box.querySelector('[data-cm-post]') : null;
  var sayBox = box ? box.querySelector('[data-cm-say]') : null;
  var hint = words ? words.getAttribute('placeholder') : '';
  var LIMIT = words ? (+words.getAttribute('maxlength') || 500) : 500;
  var answering = null;      // { id, btn }: what the box answers, if anything
  var sending = false;
  var draftWrap = box ? box.querySelector('[data-cm-draft]') : null;
  var draftBox = draftWrap ? draftWrap.querySelector('.skribl-inline') : null;
  var chips = box ? Array.prototype.slice.call(box.querySelectorAll('[data-cm-open]')) : [];
  var draft = null;          // { payload, over }

  var sheetWrap = box ? doc.getElementById('commentBoxSheet') : null;
  var slot = sheetWrap ? sheetWrap.querySelector('[data-cm-slot]') : null;
  var sheetTitle = sheetWrap ? sheetWrap.querySelector('[data-cm-sheet-title]') : null;
  var homeTitle = sheetTitle ? sheetTitle.textContent : '';
  var quote = sheetWrap ? sheetWrap.querySelector('[data-cm-quote]') : null;
  var sheetOpeners = [];
  var sheetAfter = null;     // what waits for the sheet to have gone (emptying a posted box)
  var sheet = sheetWrap && window.SocialSheet ? window.SocialSheet(sheetWrap, {
    openers: sheetOpeners, doorCloses: false, ownTouch: '.composer-words, .composer-draft',
    first: function () { return words; },
    onSettled: function () {
      if (sheet.isOpen()) return;
      answering = null;
      lift();
      var then = sheetAfter;
      sheetAfter = null;
      if (then) then();
    }
  }) : null;

  function grow() {
    if (!words) return;
    words.style.height = 'auto';
    if (words.scrollHeight) words.style.height = words.scrollHeight + 'px';   // none while folded away
    var n = LIMIT - words.value.length;
    left.textContent = n <= 100 ? say('c_left', { n: n }) : '';
    holdPost();
  }
  if (words) { words.addEventListener('input', grow); grow(); }
  /* AN @ TYPED shows the list of people under the line (mentions.js), as in
     the composer; it travels with the box, to a phone's sheet or a desk's
     fold. */
  if (words && window.SocialMentions) window.SocialMentions(words, box.querySelector('#cmMentions'));

  function pressed(btn, on) { if (btn) btn.setAttribute('aria-expanded', on ? 'true' : 'false'); }
  /* The conversation a comment or a reply is in: the comment at the top of
     its thread, however deep the reply. */
  function topOf(li) {
    var t = li;
    while (t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('cm-chain')) t = t.parentNode.closest('.cm');
    return t;
  }

  /* Whom the box says something to: a new comment ("Say something to Mira"),
     or a reply to `li` ("Reply to Theo", and Theo's words under it); on a
     comment's own page, a new one replies to that comment. */
  function aim(li) {
    if (!li && subjectEl) li = subjectEl;
    var name = li ? li.getAttribute('data-first') || '' : '';
    words.setAttribute('placeholder', li ? say('c_answer', { name: name }) : hint);
    label.textContent = li ? say('c_answer_label', { name: name }) : say('c_say');
    if (sheetTitle) sheetTitle.textContent = li ? say('c_answer_label', { name: name }) : homeTitle;
    if (quote) {
      var w = !li ? null : li === subjectEl ? li.querySelector(':scope > .post-words')
        : li.querySelector(':scope > .cm-main .cm-words');
      var text = w ? w.textContent.replace(/\s+/g, ' ').trim() : '';
      quote.textContent = text ? say('c_quote', { words: text }) : '';
      quote.hidden = !text;
    }
  }

  /* The box where this screen opens it: a phone's sheet, or a desk's fold. */
  function house() {
    var want = onDesk() || !slot ? foldIn : slot;
    if (want && box.parentNode !== want) want.appendChild(box);
  }

  /* What the bar's line (and a comment's own Reply) open, said to a screen
     reader as such: a phone's dialog, or a desk's fold. */
  function named() {
    sayers.forEach(function (b) {
      if (onDesk()) { b.removeAttribute('aria-haspopup'); b.setAttribute('aria-controls', 'commentFold'); }
      else { b.setAttribute('aria-haspopup', 'dialog'); b.setAttribute('aria-controls', 'commentBoxSheet'); }
    });
  }
  if (box) named();

  /* ---- a phone: the sheet --------------------------------------------------- */
  /* ON A PHONE'S KEYBOARD the sheet rides above it: social.js's
     SocialKeyboard reads it (--cm-kb), and reads it again until it rests, as
     the composer's does (compose.js). */
  var keyboard = sheet && window.SocialKeyboard
    ? window.SocialKeyboard(sheetWrap, 'cm-kb', function () { return sheet.isOpen(); }) : null;
  function lift() { if (keyboard) keyboard.watch(); }

  /* The sheet, for a new comment (`li` none) or an answer to `li`; `btns`
     are marked as what opened it, the first takes focus back after. */
  function rise(li, btns) {
    if (!sheet || sheet.isOpen()) return;
    house();
    var to = li || subjectEl;
    answering = to ? { id: to.getAttribute('data-comment'), btn: btns[0] } : null;
    aim(li);
    tell(sayBox, '');
    sheetOpeners.length = 0;
    btns.forEach(function (b) { if (b) sheetOpeners.push(b); });
    sheet.open(btns[0]);
    grow();
    lift();
  }

  /* ---- a desk: the fold ----------------------------------------------------- */
  var at = null;             // where the fold is open: `root` (at home, in the bar's place) or a comment's li
  var closing = false;       // folding away, from where it still is
  var foldOff = null;        // calls off the fold's glide under way
  var afterFold = null;      // what to do once it has folded away (open it elsewhere)
  /* The fold's home is the room it shares with the answer bar (.ans): open
     there, the bar's line fades away under the box (social.css). */
  function placeOf() { return fold.parentNode === home ? root : fold.parentNode; }
  function placeFold(top) {
    if (top) { if (fold.parentNode !== top) top.appendChild(fold); }
    else if (fold.parentNode !== home) home.appendChild(fold);
  }

  /* The fold glides open in the bar's place (`top` none) or under the
     conversation `top`, its field ready to type in; once open, if it is below
     the screen, the page glides to it. */
  function unfold(top) {
    var where = top || root;
    if (at === where) return;
    if (at) { afterFold = function () { unfold(top); }; shutFold('quick'); return; }
    if (closing && placeOf() !== where) { afterFold = function () { unfold(top); }; return; }
    /* Folded, or folding away from this very place (the glide turns round). */
    if (foldOff) foldOff();
    foldOff = null;
    closing = false;
    afterFold = null;
    house();
    placeFold(top);
    fold.classList.remove('is-quick', 'is-still');
    foldIn.hidden = false;           // laid out again: folded, it is not
    void fold.offsetHeight;          // the glide starts from where it is
    fold.classList.add('is-open');
    at = where;
    words.focus({ preventScroll: true });
    grow();
    foldOff = after(fold, 'grid-template-rows', 500, function () {
      foldOff = null;
      if (at !== where) return;
      fold.classList.add('is-still');
      reveal(box);
    });
  }

  /* The fold folds away where it is: `quick` (0.24s) when it is put away, or
     'posted', in step with a comment arriving (0.32s, as the comment opens its
     room). Folded, it goes back home, unseen, and then `done`. */
  function shutFold(how, done) {
    if (!at) { if (done) done(); return; }
    if (foldOff) foldOff();
    fold.classList.remove('is-still');
    fold.classList.toggle('is-quick', how === 'quick');
    fold.classList.remove('is-open');
    at = null;
    closing = true;
    foldOff = after(fold, 'grid-template-rows', 500, function () {
      foldOff = null;
      closing = false;
      fold.classList.remove('is-quick');
      placeFold(null);
      foldIn.hidden = true;          // folded away: not laid out, so nothing reads it as shown
      if (done) done();
      var next = afterFold;
      afterFold = null;
      if (next) next();
    });
  }

  /* Put the box away, keeping its words: what it answered is answered no more,
     and focus, if it was in the box, goes back to what opened it (`stay`: a
     press elsewhere, where the browser puts focus itself). */
  function putAway(stay) {
    var was = answering;
    answering = null;
    afterFold = null;
    pressed(was && was.btn, false);
    pressed(icon, false);
    var inside = !stay && box.contains(doc.activeElement);
    shutFold('quick');
    if (inside) {
      var back = was && was.btn && was.btn.isConnected ? was.btn : icon;
      if (back) back.focus({ preventScroll: true });
    }
  }

  /* ---- the ways in ------------------------------------------------------------ */
  /* The bar's line, or a comment's own Reply: something new. On a desk,
     asked again while the box is open at home (the Reply in a comment's own
     row: the line itself is under the box then), it is put away. */
  function sayNew(btn) {
    if (!box || sending) return;
    if (!onDesk()) { rise(null, btn === icon ? [icon] : [btn, icon]); return; }
    if (at === root) { putAway(); return; }
    if (answering) pressed(answering.btn, false);
    answering = subjectEl ? { id: subject, btn: btn } : null;
    aim(null);
    tell(sayBox, '');
    pressed(icon, true);
    unfold(null);
  }

  /* Answer, on a comment or an answer: the box answers it, under its
     conversation. On a desk, Answer again puts it away. */
  function answer(li, btn) {
    if (!box || sending) return;
    if (!onDesk()) { rise(li, [btn]); return; }
    var top = topOf(li), id = li.getAttribute('data-comment');
    if (at === top && answering && answering.id === id) { putAway(); return; }
    if (answering) pressed(answering.btn, false);
    pressed(icon, false);
    answering = { id: id, btn: btn };
    aim(li);
    tell(sayBox, '');
    pressed(btn, true);
    if (at === top) { words.focus({ preventScroll: true }); return; }
    unfold(top);
  }

  if (box) {
    /* A DESK'S FOLD GOES on Esc, and on a press anywhere else on the page: not
       on what opens it, and not on a sheet or the editor over the page (Draw
       and Flip open the Pad above it, and the drawing comes back into it). */
    doc.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !at || sending || !onDesk()) return;
      if (doc.querySelector('.make.is-open, .facepad.is-open')) return;
      e.preventDefault();
      putAway();
    });
    doc.addEventListener('pointerdown', function (e) {
      if (!at || sending || !onDesk()) return;
      var t = e.target;
      if (!t || !t.closest || fold.contains(t)) return;
      if (t.closest('[data-cm-new], [data-cm-answer], .make, .facepad')) return;
      putAway(true);
    }, true);
    /* A window widened into a desk, or narrowed into a phone: whatever is
       open is put away, its words kept. */
    if (desk && desk.addEventListener) {
      desk.addEventListener('change', function () {
        if (sheet && sheet.isOpen()) sheet.close(true);
        if (at) putAway();
        named();
      });
    }
  }

  /* ---- a drawing answer: the editor over the post, the drawing in the box -- */
  function attach(payload, over) {
    draft = { payload: payload, over: over };
    draftWrap.hidden = false;
    if (draftBox && window.SkriblInline) window.SkriblInline.attach(draftBox, payload);
    chips.forEach(function (c) { c.hidden = true; });
    tell(sayBox, '');
    var edit = box.querySelector('[data-cm-edit]');
    if (edit) edit.focus({ preventScroll: true });
  }
  function unattach(focus) {
    if (draft && draft.over) draft.over.pad.clear();
    draft = null;
    if (draftWrap) draftWrap.hidden = true;
    chips.forEach(function (c) { c.hidden = false; });
    if (focus && chips[0]) chips[0].focus({ preventScroll: true });
  }
  chips.forEach(function (chip) {
    var wrap = doc.getElementById(chip.getAttribute('data-cm-open') === 'flip' ? 'commentFlip' : 'commentPad');
    var over = window.SocialPadOverlay ? window.SocialPadOverlay(wrap, {
      openers: [chip],
      onDone: function (payload) { attach(payload, over); }
    }) : null;
    chip.addEventListener('click', function () {
      if (!over || sending) return;
      tell(sayBox, '');
      over.open(chip);
    });
  });
  if (box && draftWrap) {
    box.querySelector('[data-cm-edit]').addEventListener('click', function (e) {
      if (draft && draft.over && !sending) draft.over.open(e.currentTarget);
    });
    box.querySelector('[data-cm-remove]').addEventListener('click', function () {
      if (!draft || sending) return;
      unattach(true);
    });
  }

  /* ---- posted: the box goes, and the comment comes ---------------------------- */
  /* `li` opens its room in `parent` before `before`, fading in, while what is
     under it slides down. It is laid out whole from the start and shown from
     its top down (a clip), a negative margin under it giving its room back a
     frame at a time (social.css, .is-growing), so nothing inside it moves.
     `extra`: room its arrival adds beyond its own height that the caller
     knows of; what the stylesheet adds is measured here (below), and both
     are given back too, so nothing steps. Under
     Reduce Motion it is put in place and fades in. `out`: how far its
     edges reach past its box (10px, the landing's tint). */
  function arrive(li, parent, before, extra, then, out) {
    var x = '-' + (out || 10) + 'px';
    li.style.opacity = '0';
    li.style.clipPath = 'inset(0 ' + x + ' 100% ' + x + ')';
    var was = parent.getBoundingClientRect().height;
    parent.insertBefore(li, before);
    /* Settled before it is measured: its times said as the page says them
       ("now" for the server's day) can take a line off a narrow head. */
    settle(li);
    var h = li.getBoundingClientRect().height;     // to the fraction: a whole pixel would step
    /* WHAT ELSE ITS ARRIVAL ADDS, MEASURED: the room before a new conversation
       (social.css: 18px on a comment that follows another, so on the one this
       pushes down, or on this one at a list's end). The list grows by that as
       well as by the comment, and it is given back with it. Left out, what
       was under a new comment stepped 18px in one frame and then glided. */
    extra = (extra || 0) + Math.max(0, parent.getBoundingClientRect().height - was - h);
    if (still()) li.style.clipPath = '';
    else {
      li.style.marginBottom = -(h + extra) + 'px';
      li.style.clipPath = 'inset(0 ' + x + ' ' + h + 'px ' + x + ')';
    }
    void li.offsetHeight;            // where it starts
    li.classList.add('is-growing');
    li.style.marginBottom = '';
    if (!still()) li.style.clipPath = 'inset(0 ' + x + ' 0px ' + x + ')';
    li.style.opacity = '';
    function done() {
      li.classList.remove('is-growing');
      li.style.clipPath = '';
      if (then) then();
    }
    if (still()) setTimeout(done, 300);   // its fade in, under Reduce Motion
    else after(li, 'margin-bottom', 600, done);
  }

  /* POSTING IS SAID WHERE IT TAKES NO ROOM: Post says "Posting…" (dimmed, as
     a button at work is), and the box's line says it to a screen reader only.
     A line that came and went there made everything under the box jump twice
     as it went. What goes wrong is still said in the box, which stays. */
  var postWord = postBtn ? postBtn.textContent : '';
  /* Post as wide as its longer word (social.css says why): measured once the
     box is laid out, then held as its least width. */
  function holdPost() {
    if (!postBtn || postBtn.style.minWidth) return;
    var was = postBtn.textContent;
    postBtn.textContent = say('c_posting');
    var w = postBtn.getBoundingClientRect().width;
    postBtn.textContent = was;
    if (w > 0) postBtn.style.minWidth = Math.ceil(w) + 'px';
  }
  function busy(on) {
    postBtn.disabled = on;
    postBtn.textContent = on ? say('c_posting') : postWord;
    sayBox.classList.toggle('sr', on);
    tell(sayBox, on ? say('c_posting') : '');
  }

  if (box) {
    postBtn.addEventListener('click', function () {
      if (sending) return;
      if (!words.value.trim() && !draft) { tell(sayBox, say('c_empty')); return; }
      sending = true;
      busy(true);
      var body = { words: words.value };
      if (draft) body.payload = draft.payload;
      if (answering) body.answer_to = answering.id;
      send(root.getAttribute('data-new'), body).then(function (j) {
        if (!(j.ok && j.html)) { sending = false; busy(false); tell(sayBox, why(j)); return; }
        /* Emptied once it has gone: the box keeps what was sent while it
           goes, so it never changes size on its way (two lines of words
           becoming one, or a drawing taken out, would make what is under it
           jump); until then Post stays at work. */
        function tidy() {
          sending = false;
          busy(false);
          words.value = '';
          grow();
          if (draft) unattach(false);
        }
        var holder = doc.createElement('div');
        holder.innerHTML = j.html;
        var li = holder.querySelector('.cm');
        if (!li) { tidy(); return; }
        var top = j.under ? doc.getElementById('c-' + j.under) : null;
        /* A REPLY TO ONE IN THE LIST OR IN A CONVERSATION UNDER ONE
           (Bluesky's way): every count on its way says it (j.counts); it
           continues the conversation where that is followed down to the
           one it answers, glowing there; anywhere else the count by that
           one's talk cloud took it and glows. */
        var under = !!top;
        var was = answering;
        answering = null;
        afterFold = null;
        pressed(was && was.btn, false);
        pressed(icon, false);
        /* The box goes as the comment comes: the sheet glides down, or the
           fold folds away in step with it. */
        if (sheet && sheet.isOpen()) { sheetAfter = tidy; sheet.close(true); }
        else if (!at) tidy();
        if (under) {
          recount(j.counts);
          var spot = landing(top, (+(j.counts || {})[j.under] || 0) === 1);
          if (spot) {
            arrive(li, spot.parent, spot.before, 0, function () { reveal(li); });
            glow(li);
          } else glowCount(top);
          if (at) shutFold('posted', tidy);
          counted(j.count, 1);
          var back = spot ? li.querySelector('[data-cm-answer]') : was && was.btn;
          if (back && doc.contains(back)) back.focus({ preventScroll: true });
          return;
        }
        if (subject && j.under === subject) {
          /* On a comment's own page its replies are oldest first: a new one
             lands at the end, and the page glides to it. */
          arrive(li, list, null, 0, function () { reveal(li); });
        } else {
          /* A new comment lands at the top of the list, newest first. */
          arrive(li, list, list.firstChild, 0);
        }
        if (at) shutFold('posted', tidy);
        counted(j.count, 1);
        glow(li);
        var next = subject && j.under === subject ? li.querySelector('[data-cm-answer]') : icon;
        if (next) next.focus({ preventScroll: true });
      });
    });
  }

  /* ---- signed out: the bar's line is there for everybody ---------------------- */
  var outWrap = box ? null : doc.getElementById('commentOutSheet');
  var out = outWrap && window.SocialSheet ? window.SocialSheet(outWrap, {
    openers: sayers, doorCloses: false,
    first: function () { return outWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;

  /* ---- THE ROW'S TALK CLOUD, ON A POST'S OWN PAGE ----------------------------
     It is a way down to the comments (_post.html post_row). With none there
     is nothing to go down to, and its own name then is "Comment": it opens
     the box, as the bar's line does (signed out, "Say something?"), so a tap
     on it is never a tap that does nothing. */
  var cloud = !subjectEl && icon ? doc.querySelector('.post-page > .post-row a.post-count') : null;
  if (cloud) {
    cloud.addEventListener('click', function (e) {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (list.querySelector(':scope > .cm')) return;
      e.preventDefault();
      icon.click();
    });
  }

  /* ---- a link: copied, or the device's own share sheet ------------------- */
  function absolute(url) { return new URL(url, window.location.href).href; }
  function copy(url, box) {
    function byHand() { tell(box, say('c_copy_by_hand', { url: url })); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () { tell(box, say('c_copied')); }, byHand);
    } else byHand();
  }

  /* ---- BACK GOES WHERE YOU WERE (a comment's own page): the page you came
     from on this site, as the browser's own back; come from anywhere else,
     the link's own address, what it is on. */
  var back = doc.querySelector('[data-cm-back]');
  if (back) {
    back.addEventListener('click', function (e) {
      var from = doc.referrer || '';
      if (from.indexOf(window.location.origin + '/') !== 0 || window.history.length < 2) return;
      e.preventDefault();
      window.history.back();
    });
  }

  /* ---- a comment's ⋯ ------------------------------------------------------ */
  var menuWrap = doc.getElementById('commentSheet');
  var reportWrap = doc.getElementById('commentReportSheet');
  function firstAct(wrap) {
    return function () {
      return Array.prototype.filter.call(wrap.querySelectorAll('.post-act'), function (b) { return !b.hidden; })[0] || null;
    };
  }
  var menu = menuWrap && window.SocialSheet ? window.SocialSheet(menuWrap, { doorCloses: false, first: firstAct(menuWrap) }) : null;
  var report = reportWrap && window.SocialSheet
    ? window.SocialSheet(reportWrap, { doorCloses: false, ownTouch: '.post-note',
                                       first: function () { return reportWrap.querySelector('input[name=reason]:checked'); } })
    : null;
  var current = null, opener = null;

  /* THE CLICKS: the comments' own, the answer bar's line, and on a
     comment's own page the Reply and ⋯ under that comment, which sit above
     the comments. */
  doc.addEventListener('click', function (e) {
    if (!e.target || !e.target.closest) return;
    if (!root.contains(e.target) && !(subjectEl && subjectEl.contains(e.target)) && !(bar && bar.contains(e.target))) return;
    var q = e.target.closest('[data-cm-show]');
    if (q) {
      e.preventDefault();
      show(q.closest('.cm'));
      return;
    }
    var a = e.target.closest('[data-cm-answer]');
    if (a && box) {
      e.preventDefault();
      answer(a.closest('.cm'), a);
      return;
    }
    var n = e.target.closest('[data-cm-new]');
    if (n) {
      e.preventDefault();
      if (box) sayNew(n);
      else if (out) out.open(n);
      return;
    }
    /* A TAP ON A COMMENT OPENS ITS OWN PAGE (Bluesky's way: the whole reply
       is a way to it), as a post's card opens the post: on its bubble, or a
       place's words, but not on a link, a button or the drawing (which
       plays), nor a press that ends a selection of its words. */
    var bub = e.target.closest('.cm-bubble, .cm.is-gone > .cm-main');
    if (bub && !e.target.closest('a, button, input, textarea, .cm-art') && !e.defaultPrevented) {
      var sel = window.getSelection && window.getSelection();
      var to = bub.closest('.cm');
      if (to && to.getAttribute('data-url') && !(sel && !sel.isCollapsed && bub.contains(sel.anchorNode))) {
        window.location.assign(to.getAttribute('data-url'));
        return;
      }
    }
    var m = e.target.closest('[data-cm-menu]');
    if (m && menu) {
      e.preventDefault();
      var li = m.closest('.cm') || m.closest('[data-cm-subject]');
      current = { li: li, id: li.getAttribute('data-comment'), first: li.getAttribute('data-first') || '',
                  mine: li.hasAttribute('data-mine'), url: absolute(li.getAttribute('data-url') || ''),
                  page: li === subjectEl };
      opener = m;
      var postMine = root.hasAttribute('data-post-mine');
      /* BOOKMARK (the comment thread, step 3): Bookmark, or Remove bookmark
         with its ribbon filled, as the comment says; none where it can't be
         shared, nor without the post's own (posts.js, window.SocialMark). */
      var bm = menuWrap.querySelector('[data-cm-act=bookmark]');
      if (bm) {
        var kept = li.hasAttribute('data-marked');
        bm.hidden = !li.hasAttribute('data-markable') || !window.SocialMark;
        bm.classList.toggle('is-marked', kept);
        bm.querySelector('[data-bm-words]').textContent = say(kept ? 'c_bm_remove' : 'c_bm_add');
      }
      menuWrap.querySelector('[data-cm-act=delete]').hidden = !current.mine;
      menuWrap.querySelector('[data-cm-act=remove]').hidden = current.mine || !postMine;
      menuWrap.querySelector('[data-cm-act=report]').hidden = current.mine;
      tell(menuWrap.querySelector('[data-cm-sheet-say]'), '');
      Array.prototype.forEach.call(menuWrap.querySelectorAll('.post-act'), function (b) { b.disabled = false; });
      menu.open(m);
    }
  });

  /* A COMMENT THAT KEEPS ITS PLACE: its face becomes an empty ring and its
     bubble and row one quiet line, "This reply was deleted"; what hangs
     under it stays where it is. Its own part fades (0.16s), then its room
     glides to the line's height while the line fades in, so what is under
     it moves up kindly. Under Reduce Motion the line is put there and
     fades in. */
  function becomePlace(li, words) {
    var face = li.querySelector(':scope > .face-ring'), main = li.querySelector(':scope > .cm-main');
    if (!main) return;
    if (fold && li.contains(fold)) putAway();
    var parts = [face, main].filter(Boolean);
    function swap() {
      var from = main.getBoundingClientRect().height;
      var ring = doc.createElement('span');
      ring.className = 'cm-gone-face';
      ring.setAttribute('aria-hidden', 'true');
      var line = doc.createElement('p');
      line.className = 'cm-gone';
      line.textContent = words;
      li.classList.add('is-gone');
      li.removeAttribute('data-mine');
      li.removeAttribute('data-first');
      if (face) face.replaceWith(ring);
      main.textContent = '';
      main.appendChild(line);
      main.style.removeProperty('opacity');
      main.style.removeProperty('transition');
      var to = main.getBoundingClientRect().height;
      line.style.opacity = '0';
      if (!still()) { main.style.height = from + 'px'; main.style.overflow = 'hidden'; }
      void main.offsetHeight;
      line.style.transition = 'opacity 0.24s ease ' + (still() ? '0s' : '0.08s');
      line.style.opacity = '1';
      if (still()) return;
      main.style.transition = 'height 0.32s ' + EASE;
      main.style.height = to + 'px';
      after(main, 'height', 600, function () {
        ['height', 'overflow', 'transition'].forEach(function (k) { main.style.removeProperty(k); });
      });
    }
    if (still()) { swap(); return; }
    parts.forEach(function (x) { x.style.transition = 'opacity 0.16s ease'; x.style.opacity = '0'; });
    setTimeout(swap, 170);
  }

  /* A comment that goes fades first. The box, open in its conversation, is
     put away as it goes (its words kept); and the last one gone, "Say the
     first thing" comes back where the comments were. A conversation under
     a comment left with nothing in it goes with it, so no line hangs there. */
  function drop(li) {
    if (fold && li.contains(fold)) putAway();
    li.classList.add('is-going');
    var gone = false;
    function off() {
      if (gone) return;
      gone = true;
      var ol = li.parentNode;
      if (ol) ol.removeChild(li);
      if (ol && ol.classList.contains('cm-chain') && !ol.querySelector(':scope > .cm') && ol.parentNode) {
        ol.parentNode.removeChild(ol);
      }
    }
    li.addEventListener('transitionend', function (e) { if (e.target === li) off(); });
    setTimeout(off, 400);
  }

  if (menuWrap) {
    menuWrap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-cm-act]');
      if (!b || !current) return;
      var act = b.getAttribute('data-cm-act'), sayIt = menuWrap.querySelector('[data-cm-sheet-say]');
      /* COPY LINK AND SHARE…: the comment's own page, as a post's are its
         own (posts.js says them the same way). */
      if (act === 'copy') { copy(current.url, sayIt); return; }
      /* BOOKMARK: nothing asked first, as a post's: the sheet goes down, the
         toast says so with Undo, focus back on the ⋯ (signed out, the small
         sheet that says how). */
      if (act === 'bookmark' && window.SocialMark) {
        menu.close(!!window.SocialMark.out);
        window.SocialMark.act(current.li, opener);
        return;
      }
      if (act === 'share') {
        if (navigator.share) navigator.share({ url: current.url }).catch(function () { /* closed: nothing to say */ });
        else copy(current.url, sayIt);
        return;
      }
      if (act === 'report' && report) {
        menu.close(true);
        var form = reportWrap.querySelector('[data-report-form]');
        form.reset();
        var go = reportWrap.querySelector('[data-cm-report-send]');
        go.disabled = false;
        go.hidden = false;
        var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
        if (c && c.hasAttribute('data-was')) { c.textContent = c.getAttribute('data-was'); c.removeAttribute('data-was'); }
        tell(reportWrap.querySelector('[data-cm-report-say]'), '');
        report.open(opener);
        return;
      }
      /* Delete comment, or Remove from my post: one route, gone at once. */
      b.disabled = true;
      tell(sayIt, say('c_deleting'));
      var li = current.li;
      send(root.getAttribute('data-drop').replace('__ID__', encodeURIComponent(current.id)), {}).then(function (j) {
        b.disabled = false;
        if (!j.ok) { tell(sayIt, why(j)); return; }
        tell(sayIt, '');
        menu.close(true);
        /* ON ITS OWN PAGE the comment is the page: it went, so the page goes
           to what it replied to (or what it was on). */
        if (current.page) {
          if (j.place) window.location.reload();
          else window.location.assign(subjectEl.getAttribute('data-up') || '/');
          return;
        }
        /* ITS PLACE STAYS when replies hang under it (the owner's yes, Nov
           17): they stay where they are; with none, it goes. Either way it
           alone stops being counted; a place it leaves with nothing under
           it goes with it. */
        counted(j.count, -1);
        if (j.place) becomePlace(li, j.words || '');
        else drop(li);
        (j.dropped || []).forEach(function (id) { var x = doc.getElementById('c-' + id); if (x) drop(x); });
        recount(j.counts);
      });
    });
  }

  if (reportWrap) {
    reportWrap.querySelector('[data-report-form]').addEventListener('submit', function (e) {
      e.preventDefault();
      if (!current) return;
      var go = reportWrap.querySelector('[data-cm-report-send]'), sayIt = reportWrap.querySelector('[data-cm-report-say]');
      var picked = reportWrap.querySelector('input[name=reason]:checked');
      go.disabled = true;
      tell(sayIt, say('c_sending'));
      send(reportWrap.getAttribute('data-report'),
           { kind: 'comment', target: current.id, reason: picked ? picked.value : 'other',
             note: (reportWrap.querySelector('.post-note').value || '').trim() })
        .then(function (j) {
          if (j.status === 202) {
            tell(sayIt, say('c_reported'));
            go.hidden = true;
            var c = reportWrap.querySelector('.post-sheet-acts [data-make-close]');
            if (c) { c.setAttribute('data-was', c.textContent); c.textContent = say('c_done'); }
            return;
          }
          go.disabled = false;
          tell(sayIt, j.status === 429 ? say('c_report_limited') : why(j));
        });
    });
  }

  /* ---- Load more ------------------------------------------------------------ */
  var more = root.querySelector('[data-cm-next]');
  /* The next page in place: a promise of whether one came. */
  function loadMore() {
    var next = more ? more.getAttribute('data-cm-next') : '';
    if (!next) return Promise.resolve(false);
    more.disabled = true;
    return fetch(root.getAttribute('data-more') + '?before=' + encodeURIComponent(next), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (j) {
        var holder = doc.createElement('div');
        holder.innerHTML = j.html || '';
        Array.prototype.slice.call(holder.children).forEach(function (li) { list.appendChild(li); settle(li); });
        if (j.next) more.setAttribute('data-cm-next', j.next);
        else { more.setAttribute('data-cm-next', ''); more.hidden = true; }
        more.disabled = false;
        return true;
      }, function () {
        more.disabled = false;
        tell(pageSay, say('c_network'));
        return false;
      });
  }
  if (more) more.addEventListener('click', function () { loadMore(); });

  /* ---- OPENED AT A COMMENT (#c-<id>: a row in Activity; notifications) ------
     The comment glows a moment in the note's tint, then the tint fades over a
     second and a half (social.css, .cm.is-landed: the comment alone, its own
     height, not the answers under it). A drawing answer draws itself once,
     sound off, as a post's drawing starts on its own page, and the post's own
     waits (one plays at a time); at any other comment the post's own plays,
     as it always does (posts.js, window.SocialPlayOwn). One on a later page is
     brought in with Load more, a page at a time, and the page glides to it.
     UNDER REDUCE MOTION nothing moves or plays: the page is put there, and the
     tint fades where it sits. */
  var GLOW_MS = 900, FADE_MS = 1500, LAND_PAGES = 10;
  function playOwn() { if (window.SocialPlayOwn) window.SocialPlayOwn(); }
  function glow(li) {
    var main = li.querySelector(':scope > .cm-main');
    if (main) {
      var own = main.getBoundingClientRect().bottom - li.getBoundingClientRect().top + 2;
      li.style.setProperty('--cm-own', Math.max(0, Math.round(own)) + 'px');
    }
    li.classList.add('is-landed');
    var done = false;
    function end() {
      if (done) return;
      done = true;
      li.classList.remove('is-landed', 'is-fading');
      li.style.removeProperty('--cm-own');
    }
    setTimeout(function () {
      li.classList.add('is-fading');
      li.addEventListener('transitionend', function (e) { if (e.target === li && e.pseudoElement === '::before') end(); });
      setTimeout(end, FADE_MS + 400);
    }, GLOW_MS);
  }
  function drawOnce(art) {
    if (still() || !window.SkriblInline) return;
    var players = window.SkriblInline.mount(art);
    /* Not under the Blooby app's splash (splash.js): it draws as that goes. */
    var after = window.BloobySplash ? window.BloobySplash.after : function (fn) { fn(); };
    if (players && players[0] && players[0].play) after(function () { players[0].play(); });
  }
  function landed(li, brought) {
    if (brought) li.scrollIntoView({ block: 'center', behavior: still() ? 'auto' : 'smooth' });
    glow(li);
    var art = li.querySelector(':scope > .cm-main .cm-art');
    if (art) drawOnce(art); else playOwn();
  }
  (function land() {
    var m = /^#(c-[A-Za-z0-9_-]+)$/.exec(window.location.hash || '');
    if (!m) return;
    var pages = 0;
    (function look() {
      var li = doc.getElementById(m[1]);
      if (li && li.classList.contains('cm')) { landed(li, pages > 0); return; }
      if (pages >= LAND_PAGES || !more || !more.getAttribute('data-cm-next')) { playOwn(); return; }
      pages++;
      loadMore().then(function (got) { if (got) look(); else playOwn(); });
    })();
  })();

  /* ---- SIGNED IN FROM "Say something?" (#say) ---------------------------------
     Sign in comes back here with the box open, ready: a phone's sheet, a
     desk's fold. Nothing is posted until Post. On an iPhone the keyboard
     waits for a tap in the field (Safari raises it only for a tap). The
     address loses its #say, so a reload is just the page. */
  if (window.location.hash === '#say') {
    try { window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search); }
    catch (e) { /* the address keeps it; the box opens all the same */ }
    if (box) sayNew(icon);
  }
})();
