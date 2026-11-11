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
 * YOUR FACE (after v330, the owner's "all yes" on mock A, Nov 11). Change my
 * face (Add your face before there is one, and the empty circle) raises one
 * sheet, Make's own (social.js, window.SocialSheet), with three doors: Draw a
 * new one, which puts the sheet away and opens the Pad above; Trace a photo;
 * and Use one you made, which leads on inside it, a step at a time:
 *
 *   TRACE A PHOTO (the owner's "all yes, build A", Nov 11): the device's own
 *   photo picker, then the Pad above with the photo faint under its canvas,
 *   a guide to trace (Skribl's composehost guide() and editor_face.js). Only
 *   the lines are kept: the Pad leaves the photo out of the face and its
 *   card, and the site drops one sent anyway (profiles.py).
 *
 *   PICK: your skribls from Skribl's own listing, yours alone (GET the
 *   listing with your user id: the link-only ones too), newest first, paged
 *   by its cursor; Pad drawings only (a face is one, and plays once), never
 *   the face you have; each tile the drawing cropped from its own card, as a
 *   Gallery tile is. Or Open a file..., a .skribl file you saved, read here.
 *
 *   PLACE: the drawing (fetched as any player fetches it, or the file's) in
 *   the in-post player's engine, under the circle. Drag it (a finger, the
 *   pointer, or the arrow keys); size it with the slider or a pinch. It
 *   starts on the drawing's middle square, the face a drawing has today.
 *
 *   USE THIS FACE: Skribl's lib/faceframe.js makes it a face of its own, a
 *   square drawing with the placed square filling it, and paints its card;
 *   it is kept exactly as a drawn face is (/you/face). The drawing it came
 *   from is never changed.
 *
 * What cannot be a face yet (a Flip, a drawing with a picture under it) is
 * said kindly where it was picked, and the picker stays.
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
  var padApi = drawYourFace();
  yourFace(padApi);

  function drawYourFace() {
  var wrap = doc.getElementById('facePad');
  if (!wrap || !window.SkriblComposeHost) return null;
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
      /* Focus comes back to the button the person pressed, or, from Your
         face's door (the sheet is gone by then), to the button that raised
         the sheet. */
      from = b.closest('#faceSheet') || b.tagName !== 'BUTTON' ? doc.querySelector('button[data-face-sheet]') : b;
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
    Array.prototype.forEach.call(doc.querySelectorAll('button[data-face-open], button[data-face-trace], button[data-face-sheet], button[data-face-use]'), function (b) {
      b.disabled = on; b.setAttribute('aria-busy', on ? 'true' : 'false');
    });
  }

  /* Keep `payload` as the face, saying how it goes in `tell` (the profile's
     own line, or the sheet's while it is up). */
  function keep(payload, tell) {
    var said = tell || show;
    busy(true);
    said(say('saving'));
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
      said(why(j));
    });
  }

  /* A PHOTO TO TRACE (Your face's Trace a photo): the Pad over the page, the
     photo under its canvas as a guide (Skribl's composehost guide(), its
     editor_face.js); what comes back on Use this face is the lines alone,
     kept as any drawn face is. Focus comes back to the button that raised
     the sheet. */
  function trace(file) {
    if (saving || !file) return;
    show('');
    from = doc.querySelector('button[data-face-sheet]');
    pad.guide(file);
  }

  return { keep: keep, busy: busy, trace: trace, isSaving: function () { return saving; } };
  }


  /* ---- your face: two doors, a skribl you made, placed --------------------- */
  function yourFace(padApi) {
    var wrap = doc.getElementById('faceSheet');
    if (!wrap || !window.SocialSheet) return;
    var F = window.SkriblFaceFrame;
    var sheet = wrap.querySelector('.make-sheet');
    var openers = doc.querySelectorAll('[data-face-sheet]');
    var steps = Array.prototype.slice.call(wrap.querySelectorAll('.face-step'));
    var grid = wrap.querySelector('[data-face-grid]');
    var none = wrap.querySelector('[data-face-none]');
    var more = wrap.querySelector('[data-face-more]');
    var input = wrap.querySelector('[data-face-input]');
    var stage = wrap.querySelector('[data-face-stage]');
    var art = wrap.querySelector('[data-face-art]');
    var artBox = art ? art.querySelector('.skribl-inline') : null;
    var slider = wrap.querySelector('[data-face-size]');
    var maker = doc.querySelector('[data-skribl-face-maker] .skribl-inline');
    var listUrl = wrap.getAttribute('data-list') || '';
    var api = (wrap.getAttribute('data-skribl') || '').replace(/\/+$/, '');
    var posterTpl = wrap.getAttribute('data-poster') || '';
    var me = wrap.getAttribute('data-me') || '';
    var current = wrap.getAttribute('data-face') || '';
    var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    /* A face's square, as the Pad's face mode draws one. */
    var SIDE = 707;
    /* The circle is 88% of the stage (social.css, .face-ring). */
    var RING = 0.88;
    var cursor = null, listed = false, loading = false;
    var drawing = null, sq = null, W = 0, H = 0, startSide = 0;

    var ctl = window.SocialSheet(wrap, {
      openers: openers,
      doorCloses: false,
      ownTouch: '.face-scroll, .face-stage, .face-size',
      first: function () { return firstIn(currentStep()); },
      onSettled: function () { go('doors', true); }
    });

    function stepEl(name) { return wrap.querySelector('.face-step[data-step="' + name + '"]'); }
    function currentStep() { return steps.filter(function (s) { return !s.hidden; })[0] || steps[0]; }
    function firstIn(step) {
      return step ? step.querySelector('.face-tile, .make-door, [data-face-stage], button:not([disabled])') : null;
    }
    function sayIn(name, text) {
      var step = stepEl(name), box = step && step.querySelector('[data-face-say]');
      if (!box || (box.textContent === (text || '') && box.hidden === !text)) return;
      regrow(function () {
        box.textContent = text || '';
        box.hidden = !text;
      });
    }

    /* NOTHING ON THIS SHEET JUMPS. Whatever changes its height (a step, the
       list arriving, a line said) glides it from the height it had to the one
       it now needs, from wherever a glide already under way has reached;
       under Reduce Motion the height is simply the new one. */
    var glideOff = null;
    function glideHeight(h0, h1) {
      if (glideOff) glideOff();
      sheet.style.height = h0 + 'px';
      void sheet.offsetHeight;
      sheet.classList.add('is-resizing');
      sheet.style.height = h1 + 'px';
      var timer = 0;
      function off() { sheet.removeEventListener('transitionend', done); clearTimeout(timer); glideOff = null; }
      function done(e) {
        if (e && (e.target !== sheet || e.propertyName !== 'height')) return;
        off();
        sheet.classList.remove('is-resizing');
        sheet.style.height = '';
      }
      glideOff = off;
      timer = setTimeout(done, 420);
      sheet.addEventListener('transitionend', done);
    }
    function regrow(change) {
      var live = ctl.isOpen() && !wrap.hidden && !(reduced && reduced.matches);
      var h0 = live ? sheet.getBoundingClientRect().height : 0;
      change();
      if (!live) return;
      var held = sheet.style.height;
      sheet.style.height = '';
      var h1 = sheet.offsetHeight;
      sheet.style.height = held;
      if (Math.abs(h1 - h0) > 1) glideHeight(h0, h1);
    }

    /* ONE SHEET, A STEP AT A TIME: the new step fades in as the sheet glides
       to its height, and focus goes to its first control. `quiet`: the sheet
       is closed, so nothing is shown. */
    function go(name, quiet) {
      var next = stepEl(name), cur = currentStep();
      if (!next) return;
      if (next !== cur) {
        var swap = function () {
          steps.forEach(function (s) { s.hidden = s !== next; s.classList.remove('is-in'); });
          ['pick', 'place'].forEach(function (n) {
            var box = stepEl(n) && stepEl(n).querySelector('[data-face-say]');
            if (box) { box.textContent = ''; box.hidden = true; }
          });
        };
        if (!quiet && ctl.isOpen()) { regrow(swap); next.classList.add('is-in'); } else swap();
      }
      if (!quiet && ctl.isOpen()) {
        var first = firstIn(next);
        if (first) first.focus({ preventScroll: true });
      }
      if (name === 'place') fit();
    }
    /* The picker waits a moment for the list, so its step arrives at its own
       height; a slow list glides the sheet again when it comes. */
    function openPicker() {
      if (listed || !listUrl) { go('pick'); return; }
      var went = false;
      var timer = setTimeout(function () { if (!went) { went = true; go('pick'); } }, 350);
      list(false, function () { clearTimeout(timer); if (!went) { went = true; go('pick'); } });
    }

    Array.prototype.forEach.call(openers, function (b) {
      b.addEventListener('click', function (e) {
        e.preventDefault();
        if (padApi && padApi.isSaving()) return;
        go('doors', true);
        ctl.open(b.tagName === 'BUTTON' ? b : doc.querySelector('button[data-face-sheet]'));
      });
    });
    wrap.addEventListener('click', function (e) {
      var to = e.target.closest('[data-face-go]');
      if (!to) return;
      var name = to.getAttribute('data-face-go');
      if (name === 'pick') openPicker(); else go(name);
    });
    /* Draw a new one: this sheet goes FIRST (the capture runs before the
       door's own handler), so the page it hands back is the page the Pad
       then makes inert; the Pad opens above, and takes focus. */
    wrap.addEventListener('click', function (e) {
      if (e.target.closest('[data-face-open]')) ctl.close(true);
    }, true);

    /* TRACE A PHOTO: the press opens the device's own photo picker (only a
       press on this page can); a photo picked puts the sheet away and opens
       the Pad above with it to trace. Picking nothing leaves the sheet as it
       was; a file that is not a photo is said, and the sheet stays. */
    var photo = wrap.querySelector('[data-face-photo]');
    var traceDoor = wrap.querySelector('[data-face-trace]');
    if (traceDoor && photo && padApi) {
      traceDoor.addEventListener('click', function () {
        if (padApi.isSaving()) return;
        sayIn('doors', '');
        photo.value = '';
        photo.click();
      });
      photo.addEventListener('change', function () {
        var f = photo.files && photo.files[0];
        photo.value = '';
        if (!f) return;
        if (!/^image\/(jpeg|png|gif|webp)$/.test(f.type || '')) { sayIn('doors', say('not_photo')); return; }
        ctl.close(true);
        padApi.trace(f);
      });
    }

    /* ---- pick -------------------------------------------------------------- */
    /* A drawing, contained in its tile: the drawing's own rectangle cut from
       its card (lib/sharecard.js drawingRect, 3 card pixels in from the
       plate's hairline, as a face's frame is), as shares of a 4:3 tile. */
    function tileFrame(w, h) {
      var SC = window.SkriblShareCard;
      if (!SC || !SC.drawingRect || !(w > 0 && h > 0)) return null;
      var r = SC.drawingRect(w, h), x = r.x + 3, y = r.y + 3, rw = r.w - 6, rh = r.h - 6;
      if (!(rw > 0 && rh > 0)) return null;
      var A = 4 / 3, a = rw / rh, box;
      if (a >= A) box = { w: 100, h: 100 * A / a, l: 0 };
      else box = { w: 100 * a / A, h: 100, l: 0 };
      box.l = (100 - box.w) / 2;
      box.t = (100 - box.h) / 2;
      return { box: box, img: { w: 1200 / rw * 100, l: -x / rw * 100, t: -y / rh * 100 } };
    }
    function pct(n) { return n.toFixed(4) + '%'; }
    function tile(it) {
      var b = doc.createElement('button');
      b.type = 'button';
      b.className = 'face-tile';
      var pic = doc.createElement('span');
      pic.className = 'face-pic';
      var fr = tileFrame(+it.canvas_w, +it.canvas_h);
      if (fr && posterTpl && /^[A-Za-z0-9_-]{1,64}$/.test(it.id || '')) {
        var inner = doc.createElement('span');
        inner.className = 'face-pic-in';
        inner.style.left = pct(fr.box.l); inner.style.top = pct(fr.box.t);
        inner.style.width = pct(fr.box.w); inner.style.height = pct(fr.box.h);
        var img = doc.createElement('img');
        img.alt = '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.src = posterTpl.replace('__ID__', encodeURIComponent(it.id));
        img.style.width = pct(fr.img.w); img.style.left = pct(fr.img.l); img.style.top = pct(fr.img.t);
        inner.appendChild(img);
        pic.appendChild(inner);
      }
      var name = doc.createElement('b');
      name.textContent = it.title || 'Untitled Skribl';
      b.appendChild(pic);
      b.appendChild(name);
      b.addEventListener('click', function () { pickPosted(it.id); });
      return b;
    }
    /* Yours, from Skribl's own listing: with your own user id it lists the
       link-only ones too. A face is a Pad drawing, and never the one you have. */
    function list(append, done) {
      if (loading || !listUrl || !me) { if (done) done(); return; }
      loading = true;
      fetch(listUrl + '?limit=24&user_id=' + encodeURIComponent(me) + (append && cursor ? '&cursor=' + encodeURIComponent(cursor) : ''),
            { credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (body) {
          loading = false;
          listed = true;
          regrow(function () {
            if (!append) grid.textContent = '';
            ((body && body.items) || []).forEach(function (it) {
              if (!it || (it.kind && it.kind !== 'pad') || it.id === current) return;
              grid.appendChild(tile(it));
            });
            cursor = (body && body.next_cursor) || null;
            more.hidden = !cursor;
            none.hidden = grid.children.length > 0 || !!cursor;
          });
          if (done) done();
        }, function () {
          loading = false;
          if (done) done();
          sayIn('pick', say('list_failed'));
        });
    }
    more.addEventListener('click', function () { list(true); });

    /* inspect(), not check(): a drawing made in the Pad carries the blank its
       first take began on, and only a look at it tells that from a picture
       (lib/faceframe.js). Only the latest pick is answered. */
    var asked = 0;
    function ready(p, where) {
      if (!F) { sayIn(where, say('unreadable')); return; }
      var mine = ++asked;
      F.inspect(p).then(function (why) {
        if (mine !== asked) return;
        if (why) { sayIn(where, say(why)); return; }
        sayIn(where, '');
        place(p);
      });
    }
    function pickPosted(id) {
      if (!api) return;
      sayIn('pick', say('opening'));
      fetch(api + '/' + encodeURIComponent(id), { credentials: 'same-origin' })
        .then(function (r) {
          if (r.status === 404) throw new Error('gone');
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (body) { ready((body && (body.skribl || body.payload)) || body, 'pick'); })
        .catch(function (e) { sayIn('pick', say(e && e.message === 'gone' ? 'gone' : 'open_failed')); });
    }
    wrap.querySelector('[data-face-file]').addEventListener('click', function () { input.click(); });
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      input.value = '';
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        var p;
        try { p = JSON.parse(reader.result); } catch (e) { sayIn('pick', say('unreadable')); return; }
        ready(p, 'pick');
      };
      reader.onerror = function () { sayIn('pick', say('unreadable')); };
      reader.readAsText(file);
    });

    /* ---- place ------------------------------------------------------------- */
    /* THE DRAWING UNDER THE CIRCLE, painted whole by the in-post player's
       engine. `sq` is the square of the drawing the circle shows, in the
       drawing's own pixels; it starts on the middle square (the face a
       drawing has today) and lib/faceframe.js keeps it in range. */
    function place(p) {
      drawing = p;
      W = +p.canvasSize.cssWidth;
      H = +p.canvasSize.cssHeight;
      sq = F.start(W, H);
      startSide = sq.side;
      go('place');
      if (artBox && window.SkriblInline) {
        var player = window.SkriblInline.attach(artBox, p, { ambient: true });
        var waited = 0;
        (function whole() {
          if (!player) return;
          var s = player.state();
          if (!s.loaded) { if (++waited < 240) window.requestAnimationFrame(whole); return; }
          player.seek(s.totalMs);
        })();
      }
      fit();
    }
    function fit() {
      if (!sq || !stage || !art) return;
      var S = stage.clientWidth;
      if (!S) return;
      var D = S * RING, m = (S - D) / 2, k = D / sq.side;
      art.style.left = (m - sq.x * k) + 'px';
      art.style.top = (m - sq.y * k) + 'px';
      art.style.width = (W * k) + 'px';
      art.style.height = (H * k) + 'px';
      if (slider) {
        var r = F.range(W, H), lo = Math.log(r.max), hi = Math.log(r.min);
        slider.value = String(Math.round(1000 * (Math.log(sq.side) - lo) / (hi - lo)));
        slider.setAttribute('aria-valuetext', Math.round(100 * startSide / sq.side) + '%');
      }
    }
    function moveBy(dx, dy) {
      var k = (stage.clientWidth * RING) / sq.side;
      sq = F.clamp({ x: sq.x - dx / k, y: sq.y - dy / k, side: sq.side }, W, H);
      fit();
    }
    function sizeTo(side) {
      var cx = sq.x + sq.side / 2, cy = sq.y + sq.side / 2;
      sq = F.clamp({ x: cx - side / 2, y: cy - side / 2, side: side }, W, H);
      fit();
    }
    if (slider) slider.addEventListener('input', function () {
      if (!sq) return;
      var r = F.range(W, H), lo = Math.log(r.max), hi = Math.log(r.min);
      sizeTo(Math.exp(lo + (hi - lo) * (+slider.value / 1000)));
    });
    /* A finger or the pointer drags it; two fingers size it, as a pinch does. */
    var held = {};
    function heldIds() { return Object.keys(held); }
    stage.addEventListener('pointerdown', function (e) {
      if (!sq) return;
      e.preventDefault();
      try { stage.setPointerCapture(e.pointerId); } catch (err) { /* not capturable */ }
      held[e.pointerId] = { x: e.clientX, y: e.clientY };
      stage.classList.add('is-moving');
    });
    stage.addEventListener('pointermove', function (e) {
      var p = held[e.pointerId];
      if (!p || !sq) return;
      var ids = heldIds();
      if (ids.length >= 2) {
        var other = held[ids[0] === String(e.pointerId) ? ids[1] : ids[0]];
        var d0 = Math.hypot(p.x - other.x, p.y - other.y), d1 = Math.hypot(e.clientX - other.x, e.clientY - other.y);
        if (d0 > 0 && d1 > 0) sizeTo(sq.side * d0 / d1);
      } else {
        moveBy(e.clientX - p.x, e.clientY - p.y);
      }
      p.x = e.clientX;
      p.y = e.clientY;
    });
    function letGo(e) {
      delete held[e.pointerId];
      if (!heldIds().length) stage.classList.remove('is-moving');
    }
    stage.addEventListener('pointerup', letGo);
    stage.addEventListener('pointercancel', letGo);
    /* The keyboard: the arrow keys move it (a bigger step with Shift); + and -
       size it, as the slider does. */
    stage.addEventListener('keydown', function (e) {
      if (!sq) return;
      var step = e.shiftKey ? 32 : 8, dx = 0, dy = 0;
      if (e.key === 'ArrowLeft') dx = -step;
      else if (e.key === 'ArrowRight') dx = step;
      else if (e.key === 'ArrowUp') dy = -step;
      else if (e.key === 'ArrowDown') dy = step;
      else if (e.key === '+' || e.key === '=') { e.preventDefault(); sizeTo(sq.side / 1.1); return; }
      else if (e.key === '-' || e.key === '_') { e.preventDefault(); sizeTo(sq.side * 1.1); return; }
      else return;
      e.preventDefault();
      moveBy(dx, dy);
    });
    window.addEventListener('resize', fit);

    /* ---- use this face ----------------------------------------------------- */
    wrap.querySelector('[data-face-use]').addEventListener('click', function () {
      if (!drawing || !sq || !F) return;
      if (!padApi || !maker) { sayIn('place', say('failed')); return; }
      if (padApi.isSaving()) return;
      var made;
      try { made = F.place(drawing, sq, SIDE); } catch (err) { sayIn('place', say(err && err.message === 'photo' ? 'photo' : 'failed')); return; }
      padApi.busy(true);
      sayIn('place', say('making'));
      F.card(made, maker).then(function (url) {
        made.thumbnail = url;
        padApi.keep(made, function (text) { sayIn('place', text); });
      }, function () {
        padApi.busy(false);
        sayIn('place', say('failed'));
      });
    });
  }
})();
