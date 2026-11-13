/* Comments (phase 2; the comments mock and the owner's "all yes on both",
 * Nov 12): a post's own page, and a drawing's (post.html,
 * social/_comments.html), the same section on both: the page names its own
 * addresses (data-new, data-more, data-drop).
 *
 * THE BOX IS AN ICON (the owner, Nov 13: "The comment needs to be an icon not
 * a card. It takes up too much room sitting there"; "Yes to all" to the
 * mock's choices). A round icon at the end of the "Comments" heading opens
 * the one box: on a phone it rises on Make's own sheet, "Say something to
 * Mira"; on a desk it glides open under the heading, the icon lit. Put away
 * (the dimmed page, a drag down or Esc on a phone; a second click, Esc or a
 * press elsewhere on a desk), it keeps what was typed. With no comments yet,
 * "Say the first thing" stands where they will be and opens it too. Signed
 * out, the icon raises "Say something?", whose Sign in comes back with the
 * box open (#say).
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
 * ANSWER OPENS THE SAME BOX for the comment: a phone's sheet titled "Answer
 * Theo", Theo's words under it; on a desk under its conversation, after its
 * answers ("Answer Theo…"), the page gliding to it if it is below the
 * screen. Answer again, Esc or a posted answer puts it away. An answer to an
 * answer sits under the same comment (the server says which). KIND, NEVER
 * JUMPY: everything that moves glides (social.css: the sheet, the fold, a
 * comment's room), the box fades in as its room opens, and under Reduce
 * Motion things are put in place and fade.
 *
 * A COMMENT'S ⋯ (social.js's SocialSheet, as the post's): Your comment:
 * Delete comment; somebody else's on your own post: Remove from my post and
 * Report comment; anybody else's: Report comment. Delete and Remove go at
 * once, the comment fading out with its answers; Report rises as a sheet of
 * its own with a post's reasons, into the site's own queue.
 *
 * LOAD MORE brings the next page of comments in place.
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
    if (j && j.error === 'rejected' && j.message) return j.message;
    if (j && j.error && WORDS['c_' + j.error]) return say('c_' + j.error);
    if (j && j.status === 413) return say('c_too_big');
    if (j && j.status === 429) return say('c_limited');
    if (j && j.status === 403) return say('c_stale');
    if (j && j.status === 401) return say('c_signed_out');
    if (j && j.status === 404) return say('c_gone');
    return say('c_failed');
  }

  var head = root.querySelector('.comments-head');
  var list = root.querySelector('[data-cm-list]');
  var countEl = root.querySelector('[data-cm-count]');
  var pageSay = root.querySelector('[data-cm-page-say]');
  function setCount(n) {
    if (!countEl || typeof n !== 'number') return;
    countEl.textContent = String(n);
    countEl.hidden = !n;
  }
  /* What arrives later is said as what was there: its times, and its
     drawing's player (still until tapped, as Skribl asks of a feed that adds
     posts later). */
  function settle(el) {
    if (window.SocialWhen) window.SocialWhen(el);
    if (window.SkriblInline) window.SkriblInline.mount(el);
  }

  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still() { return !!(reduced && reduced.matches); }
  var desk = window.matchMedia ? window.matchMedia('(min-width: 900px)') : null;
  function onDesk() { return !!(desk && desk.matches); }

  /* WHERE IT CAN BE SEEN: something below what the screen shows (above a
     phone's bar) is glided to, never jumped to; under Reduce Motion the page
     is simply put there. */
  function reveal(el) {
    var r = el.getBoundingClientRect(), floor = window.innerHeight;
    var bar = doc.querySelector('body > .nav');
    if (bar) {
      var b = bar.getBoundingClientRect();
      if (b.top > floor / 2) floor = b.top;           // a phone's bar along the bottom
    }
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

  /* ---- THE BOX, FOLDED AWAY BEHIND THE ICON ------------------------------------
     The comment box is an icon (the owner, Nov 13: "The comment needs to be an
     icon not a card. It takes up too much room sitting there"; "Yes to all").
     One box, wherever it opens, keeping what was typed for as long as the page
     is open:
     - A PHONE: a tap on the icon (or on "Say the first thing") raises Make's
       own sheet with the box on it, its field ready to type in, "Say something
       to Mira"; Answer raises it as "Answer Theo", Theo's words in a line under
       it. A tap on the dimmed page, a drag down or Esc puts it away
       (social.js's SocialSheet). On a phone's keyboard it rides above it.
     - A DESK: a click glides the box open under the heading (the fold), what
       is under it sliding down while it fades in, the icon lit; a second
       click, Esc or a press anywhere else folds it away. Answer glides it open
       under that conversation instead ("Answer Theo…"), and the page glides
       to it if it is below the screen. Open in one place and asked for in
       another, it folds away there first, then opens.
     - POSTED: the box goes (the sheet glides down, or the fold folds away) as
       the new comment opens its room, fades in and glows a moment in the
       landing's tint (Activity's), which then fades. On a desk the two move in
       step, so what is under them moves only by how much taller or shorter the
       comment is than the box. */
  var box = root.querySelector('[data-cm-box]');
  var fold = root.querySelector('[data-cm-fold]');
  var foldIn = fold ? fold.querySelector('.cm-fold-in') : null;
  var firstFold = root.querySelector('[data-cm-first-fold]');
  var sayers = Array.prototype.slice.call(root.querySelectorAll('[data-cm-new]'));
  var icon = root.querySelector('.cm-say');
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
  }
  if (words) { words.addEventListener('input', grow); grow(); }

  function pressed(btn, on) { if (btn) btn.setAttribute('aria-expanded', on ? 'true' : 'false'); }
  /* The comment a comment sits under: itself, or the one its answers hang from. */
  function topOf(li) {
    return li.parentNode && li.parentNode.classList.contains('cm-answers') ? li.parentNode.closest('.cm') : li;
  }

  /* Whom the box says something to: a new comment ("Say something to Mira"),
     or an answer to `li` ("Answer Theo", and Theo's words under it). */
  function aim(li) {
    var name = li ? li.getAttribute('data-first') || '' : '';
    words.setAttribute('placeholder', li ? say('c_answer', { name: name }) : hint);
    label.textContent = li ? say('c_answer_label', { name: name }) : say('c_say');
    if (sheetTitle) sheetTitle.textContent = li ? say('c_answer_label', { name: name }) : homeTitle;
    if (quote) {
      var w = li ? li.querySelector(':scope > .cm-main > .cm-words') : null;
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

  /* What the icon (and "Say the first thing") open, said to a screen reader
     as such: a phone's dialog, or a desk's fold. */
  function named() {
    sayers.forEach(function (b) {
      if (onDesk()) { b.removeAttribute('aria-haspopup'); b.setAttribute('aria-controls', 'commentFold'); }
      else { b.setAttribute('aria-haspopup', 'dialog'); b.setAttribute('aria-controls', 'commentBoxSheet'); }
    });
  }
  if (box) named();

  /* ---- a phone: the sheet --------------------------------------------------- */
  /* ON A PHONE'S KEYBOARD the sheet rides above it: the keyboard is what the
     visual viewport lost at the bottom of the layout viewport the sheet is
     fixed to (iPhone's Safari shrinks only the visual one). A pinch's zoom is
     not a keyboard, so only at a scale of 1. NOT SEEN HERE: this box has no
     phone keyboard; the suite stands one in for the visual viewport. */
  function lift() {
    if (!sheetWrap) return;
    var vv = window.visualViewport, kb = 0;
    if (vv && sheet && sheet.isOpen() && Math.abs((vv.scale || 1) - 1) < 0.01) {
      kb = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop));
    }
    if (kb) sheetWrap.style.setProperty('--cm-kb', kb + 'px');
    else sheetWrap.style.removeProperty('--cm-kb');
  }
  if (sheetWrap && window.visualViewport) {
    window.visualViewport.addEventListener('resize', lift);
    window.visualViewport.addEventListener('scroll', lift);
  }

  /* The sheet, for a new comment (`li` none) or an answer to `li`; `btns`
     are marked as what opened it, the first takes focus back after. */
  function rise(li, btns) {
    if (!sheet || sheet.isOpen()) return;
    house();
    answering = li ? { id: li.getAttribute('data-comment'), btn: btns[0] } : null;
    aim(li);
    tell(sayBox, '');
    sheetOpeners.length = 0;
    btns.forEach(function (b) { if (b) sheetOpeners.push(b); });
    sheet.open(btns[0]);
    grow();
    lift();
  }

  /* ---- a desk: the fold ----------------------------------------------------- */
  var at = null;             // where the fold is open: `root` (under the heading) or a comment's li
  var closing = false;       // folding away, from where it still is
  var foldOff = null;        // calls off the fold's glide under way
  var afterFold = null;      // what to do once it has folded away (open it elsewhere)
  function placeOf() { return fold.parentNode === root ? root : fold.parentNode; }
  function placeFold(top) {
    if (top) { if (fold.parentNode !== top) top.appendChild(fold); }
    else if (head.nextElementSibling !== fold) root.insertBefore(fold, head.nextSibling);
  }

  /* "Say the first thing" stands where the comments will be while there are
     none, unless the box is open under the heading in its place. It folds in
     step with the box: `quick` as the box folds away quickly. */
  var firstOff = null;
  var firstIn = firstFold ? firstFold.querySelector('.cm-fold-in') : null;
  function syncFirst(quick) {
    if (!firstFold) return;
    var want = !list.querySelector(':scope > .cm') && !(at === root && onDesk());
    if (firstFold.classList.contains('is-open') === want) return;
    if (firstOff) firstOff();
    firstFold.classList.remove('is-still');
    firstFold.classList.toggle('is-quick', !!quick);
    if (want) { firstIn.hidden = false; void firstFold.offsetHeight; }   // laid out, then it opens
    firstFold.classList.toggle('is-open', want);
    firstOff = after(firstFold, 'grid-template-rows', 500, function () {
      firstOff = null;
      firstFold.classList.remove('is-quick');
      if (firstFold.classList.contains('is-open')) firstFold.classList.add('is-still');
      else firstIn.hidden = true;
    });
  }

  /* The fold glides open under the heading (`top` none) or under the
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
    syncFirst(false);
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
     room). Folded, it goes back under the heading, unseen, and then `done`. */
  function shutFold(how, done) {
    if (!at) { if (done) done(); return; }
    if (foldOff) foldOff();
    fold.classList.remove('is-still');
    fold.classList.toggle('is-quick', how === 'quick');
    fold.classList.remove('is-open');
    at = null;
    closing = true;
    syncFirst(how === 'quick');
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
  /* The icon, or "Say the first thing": a new comment. On a desk a second
     click on the icon puts it away. */
  function sayNew(btn) {
    if (!box || sending) return;
    if (!onDesk()) { rise(null, btn === icon ? [icon] : [btn, icon]); return; }
    if (at === root) { putAway(); return; }
    if (answering) pressed(answering.btn, false);
    answering = null;
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
     `extra`: the rule its arrival gives the comment after it (one that stops
     being first takes its rule back), given back too, so nothing steps. Under
     Reduce Motion it is put in place and fades in. */
  function arrive(li, parent, before, extra, then) {
    li.style.opacity = '0';
    li.style.clipPath = 'inset(0 -10px 100% -10px)';
    parent.insertBefore(li, before);
    var h = li.getBoundingClientRect().height;     // to the fraction: a whole pixel would step
    if (still()) li.style.clipPath = '';
    else {
      li.style.marginBottom = -(h + extra) + 'px';
      li.style.clipPath = 'inset(0 -10px ' + h + 'px -10px)';
    }
    void li.offsetHeight;            // where it starts
    li.classList.add('is-growing');
    li.style.marginBottom = '';
    if (!still()) li.style.clipPath = 'inset(0 -10px 0px -10px)';
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
        var was = answering;
        answering = null;
        afterFold = null;
        pressed(was && was.btn, false);
        pressed(icon, false);
        /* The box goes as the comment comes: the sheet glides down, or the
           fold folds away in step with it. */
        if (sheet && sheet.isOpen()) { sheetAfter = tidy; sheet.close(true); }
        else if (!at) tidy();
        if (top) {
          var ans = top.querySelector(':scope > .cm-answers');
          if (!ans) {
            ans = doc.createElement('ol');
            ans.className = 'cm-answers';
            top.insertBefore(ans, fold && fold.parentNode === top ? fold : null);
          }
          /* An answer lands at the end of its conversation, which can be below
             the screen: once it is in place the page glides to it. */
          arrive(li, ans, null, 0, function () { reveal(li); });
        } else {
          /* A new comment lands right under the icon that was pressed, so
             nothing else needs to move. */
          arrive(li, list, list.firstChild, list.querySelector(':scope > .cm') ? 1 : 0);
        }
        settle(li);
        if (at) shutFold('posted', tidy);
        else syncFirst(false);
        setCount(j.count);
        glow(li);
        var next = top ? li.querySelector('[data-cm-answer]') : icon;
        if (next) next.focus({ preventScroll: true });
      });
    });
  }

  /* ---- signed out: the icon is there for everybody ---------------------------- */
  var outWrap = box ? null : doc.getElementById('commentOutSheet');
  var out = outWrap && window.SocialSheet ? window.SocialSheet(outWrap, {
    openers: sayers, doorCloses: false,
    first: function () { return outWrap.querySelector('.post-sheet-acts [data-make-close]'); }
  }) : null;

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

  root.addEventListener('click', function (e) {
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
    var m = e.target.closest('[data-cm-menu]');
    if (m && menu) {
      e.preventDefault();
      var li = m.closest('.cm');
      current = { li: li, id: li.getAttribute('data-comment'), first: li.getAttribute('data-first') || '',
                  mine: li.hasAttribute('data-mine') };
      opener = m;
      var postMine = root.hasAttribute('data-post-mine');
      menuWrap.querySelector('#commentSheetTitle').textContent =
        current.mine ? say('c_yours') : say('c_theirs', { name: current.first });
      menuWrap.querySelector('[data-cm-act=delete]').hidden = !current.mine;
      menuWrap.querySelector('[data-cm-act=remove]').hidden = current.mine || !postMine;
      menuWrap.querySelector('[data-cm-act=report]').hidden = current.mine;
      tell(menuWrap.querySelector('[data-cm-sheet-say]'), '');
      Array.prototype.forEach.call(menuWrap.querySelectorAll('.post-act'), function (b) { b.disabled = false; });
      menu.open(m);
    }
  });

  /* A comment that goes fades first. The box, open in its conversation, is
     put away as it goes (its words kept); and the last one gone, "Say the
     first thing" comes back where the comments were. */
  function drop(li) {
    if (fold && li.contains(fold)) putAway();
    li.classList.add('is-going');
    var gone = false;
    function off() {
      if (gone) return;
      gone = true;
      if (li.parentNode) li.parentNode.removeChild(li);
      syncFirst(false);
    }
    li.addEventListener('transitionend', function (e) { if (e.target === li) off(); });
    setTimeout(off, 400);
  }

  if (menuWrap) {
    menuWrap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-cm-act]');
      if (!b || !current) return;
      var act = b.getAttribute('data-cm-act'), sayIt = menuWrap.querySelector('[data-cm-sheet-say]');
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
        setCount(j.count);
        drop(li);
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
    if (players && players[0] && players[0].play) players[0].play();
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
