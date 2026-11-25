/* Draw back: somebody's drawing faint under your pen, so you draw with them,
 * never over them (the owner's "All yes", Nov 19, to the Draw back mock;
 * DECISIONS.md, "Draw back, mocked"). A host's composer hands the editor the
 * original (lib/composehost.js underlay, editor_compose.js), and this lays it
 * down.
 *
 * WHERE IT SITS. The canvas takes the original's shape and its ground (the
 * paper it was drawn on, Paper where it named none), so the new strokes sit
 * exactly where the old ones do: on the Pad's dark canvas the faint ink
 * vanished in the mock, which is why it opens on the original's paper. The
 * original is painted on a canvas of its own in the zoom layer, over the
 * drawing and taking no touch, as Draw along's guide is (lib/drawalong.js):
 * it zooms and pans with the drawing, and it is never part of it, never
 * recorded, posted or exported. The host's site joins the two when it posts
 * (the Skribl site's social/drawback.py), from the original as it is stored.
 *
 * HOW IT LOOKS (choice 3): in its own colours, faded, so you see what they
 * drew and always know which line is yours (about 2:1 on its paper against
 * yours, about 15:1). Each stroke is painted whole on a canvas of its own and
 * laid down faded at once, so where a line crosses itself it does not bead.
 * One button, Theirs: faint, full, hidden. A pill under the header says what
 * is happening, in Draw along's pill, until the first stroke; then it folds
 * into its Theirs button alone in the drawing's top-left corner (fold,
 * below).
 *
 * HER PICTURE AND HER MUSIC (the owner's yes, Nov 19: "only let a drawback be
 * on author's background and music"). Her photo lies under the canvas, where
 * the Pad's own photo would (a canvas of its own, never the Pad's photo, so
 * nothing of hers is recorded as his), placed by the player's own rule
 * (lib/photofit.js), at her opacity and blur; and under his lines in the
 * picture the post rests on (paintUnder). Her song is not played here: it
 * plays under both drawings in the posted draw-back, which the site joins.
 *
 * WHAT STEPS ASIDE WHILE DRAWING BACK (the owner's "All yes", Nov 19): the
 * eraser (a draw-back replays as one drawing, so an eraser over her lines
 * would erase them too: "you add, never erase"; Undo still takes back a line
 * of yours), Recolour, and the background: her paper's colour and the
 * picture and music drawer ("the original reserves the right for a
 * background", the owner's own words). Each is dimmed and, tapped, says why
 * in the editor's own toast. The eraser is held at the one switch every way
 * to it goes through (setTool: its button, its key, Tune's), so none slips by.
 *
 * Pad and Flip: one module. The Pad uses it now; drawing back on a Flip,
 * page for page, is Flip next (its own mock). */
(function () {
  'use strict';
  var FAINT = 0.32;
  var STATES = [
    { key: 'faint', alpha: FAINT, word: 'Theirs: faint' },
    { key: 'full', alpha: 1, word: 'Theirs: full' },
    { key: 'hidden', alpha: 0, word: 'Theirs: hidden' }
  ];
  var run = null;

  function target() { return document.getElementById('canvas') || document.getElementById('pad'); }
  function strokesOf(payload) {
    var out = [], cur = null;
    var f0 = payload && payload.frames && payload.frames[0];
    var pts = (f0 && f0.strokes) || (payload && payload.strokes) || [];
    pts.forEach(function (p) {
      if (!p || typeof p.x !== 'number' || typeof p.y !== 'number') return;
      if (p.start || !cur) { cur = []; out.push(cur); }
      cur.push(p);
    });
    return out;
  }
  function photoOf(payload) {
    var f0 = payload && payload.frames && payload.frames[0];
    var ph = (f0 && f0.photo && f0.photo.data) ? f0.photo : (payload && payload.photo && payload.photo.data) ? payload.photo : null;
    return ph && typeof ph.data === 'string' ? ph : null;
  }
  /* Her photo on `ctx`, `w` x `h` pixels, as the player lays it. */
  function lay(ctx, w, h) {
    var ph = run && run.photo, img = run && run.photoImg;
    if (!ph || !img || !img.complete || !img.naturalWidth) return;
    var F = window.SkriblPhotoFit;
    var off = ph.offset || {};
    var r = F ? F.rect(img.naturalWidth, img.naturalHeight, w, h, { fit: ph.fit, zoom: ph.zoom, offX: off.x, offY: off.y })
              : { x: 0, y: 0, w: w, h: h };
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = typeof ph.opacity === 'number' ? Math.max(0, Math.min(1, ph.opacity)) : 1;
    var blur = Number(ph.blur) || 0;
    if (blur > 0 && 'filter' in ctx) ctx.filter = 'blur(' + (blur * w / run.size.w) + 'px)';
    ctx.drawImage(img, r.x, r.y, r.w, r.h);
    ctx.restore();
  }
  function paintPhoto() {
    if (!run || !run.photoCanvas) return;
    var cv = target(), g = run.photoCanvas;
    if (!cv) return;
    var w = cv.offsetWidth, h = cv.offsetHeight, dpr = window.devicePixelRatio || 1;
    g.style.left = cv.offsetLeft + 'px';
    g.style.top = cv.offsetTop + 'px';
    g.style.width = w + 'px';
    g.style.height = h + 'px';
    g.width = Math.max(1, Math.round(w * dpr));
    g.height = Math.max(1, Math.round(h * dpr));
    var c = g.getContext('2d');
    c.clearRect(0, 0, g.width, g.height);
    lay(c, g.width, g.height);
  }

  function groundOf(payload) {
    var f0 = payload && payload.frames && payload.frames[0];
    var c = (f0 && f0.background && f0.background.color) || (payload && payload.background && payload.background.color);
    if (typeof c === 'string' && /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(c)) return c;
    return window.SkriblCanvasGround ? window.SkriblCanvasGround.PAPER : '#f6f2ea';
  }

  function paint() {
    if (!run) return;
    var cv = target(), g = run.guide;
    if (!cv) return;
    var w = cv.offsetWidth, h = cv.offsetHeight, dpr = window.devicePixelRatio || 1;
    g.style.left = cv.offsetLeft + 'px';
    g.style.top = cv.offsetTop + 'px';
    g.style.width = w + 'px';
    g.style.height = h + 'px';
    var bw = Math.max(1, Math.round(w * dpr)), bh = Math.max(1, Math.round(h * dpr));
    g.width = bw;
    g.height = bh;
    var c = g.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, bw, bh);
    var a = STATES[run.state].alpha;
    if (!a) return;
    // The original, opaque, on a canvas of its own, then laid down at once.
    var o = run.off || (run.off = document.createElement('canvas'));
    o.width = bw;
    o.height = bh;
    var oc = o.getContext('2d');
    ink(oc, (w / run.size.w) * dpr);
    c.globalAlpha = a;
    c.drawImage(o, 0, 0);
    c.globalAlpha = 1;
  }

  /* Her strokes, opaque, at `s` canvas pixels to one of hers. */
  function ink(ctx, s) {
    ctx.save();
    ctx.setTransform(s, 0, 0, s, 0, 0);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    run.strokes.forEach(function (st) {
      for (var j = 0; j < st.length; j++) {
        var p = st[j], q = j ? st[j - 1] : p;
        if (p.erase) continue;
        ctx.strokeStyle = p.color || '#1f1b2e';
        ctx.lineWidth = Math.max(0.6, p.size || 4);
        ctx.beginPath();
        ctx.moveTo(q.x, q.y);
        ctx.lineTo(p.x + (q === p ? 0.01 : 0), p.y);
        ctx.stroke();
      }
    });
    ctx.restore();
  }

  /* THE PICTURE A DRAW-BACK RESTS ON (editor_post.js buildPreviewCanvas):
     her drawing whole, whatever Theirs is showing, under his lines, as the
     site posts the two (social/drawback.py). Without it the card was his
     lines alone, and the site's join kept no picture at all: a draw-back
     rested as an empty box until played (the owner, Nov 19: "there's no
     image on the drawbacks"). `w`: the drawing's own pixels across. */
  function paintUnder(ctx, w) {
    if (!run || !ctx || !w) return false;
    lay(ctx, w, w * run.size.h / run.size.w);
    ink(ctx, w / run.size.w);
    return true;
  }

  function place() {
    if (!run) return;
    if (run.folded) { corner(); return; }
    var head = document.querySelector('.header');
    var b = head ? head.getBoundingClientRect().bottom : 0;
    run.pill.style.top = Math.max(8, b + 8) + 'px';
  }

  /* ---- the pill folds at the first stroke ---------------------------------- */
  /* THE OWNER'S B, Nov 24 ("Four Small Picks" 1: "Can we click/toggle the
     theirs icon in upper left"; Nov 23: "the drawing back on someone's
     drawing toast never goes away when drawing back so you can't draw there
     (under it)"). The pill's words say what is happening until the first
     stroke; then it folds into its Theirs button alone, 44px and round, in
     the drawing's top-left corner, where a click or a tap still cycles
     faint, full and hidden. It glides there: the words fade, then the button
     travels and settles round. It lives in the canvas's area, placed from
     the drawing's frame as the play bar is (app.js positionScrub), so it
     rides the page with the drawing; never under the header, never past the
     drawing's foot. Under Reduce Motion it fades out where it was and in
     where it lands. */
  var INSET = 10, CHIP = 44;
  function frameOf() {
    var cv = target();
    var wrap = cv && cv.closest ? cv.closest('.canvas-wrap') : null;
    return wrap && wrap.parentNode ? { wrap: wrap, area: wrap.parentNode } : null;
  }
  function corner() {
    var f = run && run.folded && frameOf();
    if (!f) return;
    var a = f.area.getBoundingClientRect(), w = f.wrap.getBoundingClientRect();
    var head = document.querySelector('.header'), hb = head ? head.getBoundingClientRect().bottom : 0;
    var top = Math.min(Math.max(w.top + INSET, hb + INSET), Math.max(w.top + INSET, w.bottom - CHIP - INSET));
    run.pill.style.left = Math.round(w.left - a.left + INSET) + 'px';
    run.pill.style.top = Math.round(top - a.top) + 'px';
  }
  function still() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function fold() {
    var f = run && !run.folded && frameOf();
    if (!f) return;
    var r = run, p = r.pill, words = p.querySelector('.db-where');
    r.folded = true;
    window.addEventListener('scroll', r.onScroll, { passive: true });
    function land() {
      if (run !== r) return;
      // Where it was, its button at the right end inside the pill's padding,
      // so the glide starts exactly there.
      var from = p.getBoundingClientRect(), pad = getComputedStyle(p).paddingRight;
      p.classList.add('db-folded');
      f.area.appendChild(p);
      corner();
      if (!p.animate) return;
      if (still()) { p.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 160, easing: 'ease' }); return; }
      var to = p.getBoundingClientRect(), a = f.area.getBoundingClientRect();
      p.animate([{ left: (from.left - a.left) + 'px', top: (from.top - a.top) + 'px', width: from.width + 'px',
                   height: from.height + 'px', paddingRight: pad, borderRadius: (from.height / 2) + 'px' },
                 { left: (to.left - a.left) + 'px', top: (to.top - a.top) + 'px', width: to.width + 'px',
                   height: to.height + 'px', paddingRight: '0px', borderRadius: (to.height / 2) + 'px' }],
                { duration: 420, easing: 'cubic-bezier(.37, 0, .63, 1)' });
    }
    if (!p.animate) { land(); return; }
    var out = still() ? p.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, easing: 'ease', fill: 'forwards' })
                      : words.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, easing: 'ease', fill: 'forwards' });
    out.onfinish = function () { land(); out.cancel(); };
  }

  function say() {
    if (!run) return;
    var st = STATES[run.state];
    run.btn.setAttribute('aria-label', st.word);
    run.btn.setAttribute('data-state', st.key);
    run.btn.title = st.word;
    document.body.setAttribute('data-drawback', st.key);
  }

  /* ---- what steps aside --------------------------------------------------- */
  var guarded = false;
  function tell(words, near) {
    if (typeof window.showToast === 'function') window.showToast(words, near || null);
    else if (typeof window.chip === 'function') window.chip(words);
  }
  function hers() { return run && run.own ? 'the original\u2019s' : run && run.first ? run.first + '\u2019s' : 'theirs'; }
  var ASIDE = [
    { sel: '#recolorBtn', words: function () { return 'Recolour is off while drawing back.'; } },
    { sel: '.bg-swatch[data-bg], #customBgBtn, #customBgInput', words: function () { return 'The background is ' + hers() + '.'; } },
    { sel: '#mediaOpenBtn', words: function () { return 'The background and music are ' + hers() + '.'; } }
  ];
  function guard() {
    if (guarded) return;
    guarded = true;
    if (typeof window.setTool === 'function') {
      var real = window.setTool;
      window.setTool = function (t) {
        if (run && t === 'eraser') {
          tell('The eraser is off while drawing back. Undo takes back your last line.',
               document.getElementById('eraserToolBtn'));
          return;
        }
        return real.apply(this, arguments);
      };
    }
    ['click', 'input', 'pointerdown'].forEach(function (type) {
      document.addEventListener(type, function (e) {
        if (!run || !e.target || !e.target.closest) return;
        for (var i = 0; i < ASIDE.length; i++) {
          var hit = e.target.closest(ASIDE[i].sel);
          if (!hit) continue;
          e.preventDefault();
          e.stopImmediatePropagation();
          if (type === 'click') tell(ASIDE[i].words(), hit);
          return;
        }
      }, true);
    });
  }

  function stop() {
    if (!run) return;
    if (run.photoCanvas) run.photoCanvas.remove();
    run.guide.remove();
    run.pill.remove();
    document.body.classList.remove('drawback');
    document.body.removeAttribute('data-drawback');
    window.removeEventListener('resize', run.onResize);
    window.removeEventListener('scroll', run.onScroll);
    document.removeEventListener('pointerdown', run.onDown, true);
    document.removeEventListener('pointermove', run.onMove, true);
    document.removeEventListener('pointerup', run.onUp, true);
    document.removeEventListener('pointercancel', run.onUp, true);
    if (run.ro) run.ro.disconnect();
    run = null;
  }

  /* take({ payload, first, own }): `payload` the original, as its player is
     handed it; `first` its maker's first name, for the pill; `own` when it is
     the person's own drawing ("Drawing back on your own drawing"). */
  function take(o) {
    var payload = o && o.payload;
    var cv = target();
    if (!payload || !cv) return false;
    stop();
    var cs = payload.canvasSize || {};
    var size = (cs.cssWidth && cs.cssHeight) ? { w: +cs.cssWidth, h: +cs.cssHeight } : { w: 816, h: 612 };
    // Her shape and her paper, before anything is drawn (app.js, editor_draft.js).
    if (typeof establishEditorCanvas === 'function') {
      establishEditorCanvas(size.w, size.h);
      if (typeof layoutEditorCanvas === 'function') layoutEditorCanvas();
      if (window.growBeforePaint) window.growBeforePaint();
      if (window.syncCanvasSeg) window.syncCanvasSeg();
    }
    if (typeof setCanvasGround === 'function') setCanvasGround(groundOf(payload));
    cv = target();
    var guide = document.createElement('canvas');
    guide.className = 'da-guide db-under';
    guide.setAttribute('aria-hidden', 'true');
    cv.parentNode.insertBefore(guide, cv.nextSibling);
    var first = String((o && o.first) || '').slice(0, 40);
    var pill = document.createElement('div');
    pill.className = 'da-pill db-pill';
    pill.setAttribute('role', 'region');
    pill.setAttribute('aria-label', 'Drawing back');
    var words = document.createElement('span');
    words.className = 'da-where db-where';
    var b = document.createElement('b');
    b.textContent = 'Drawing back';
    words.appendChild(b);
    // On your own drawing: "Drawing back on your own drawing" (the owner,
    // Nov 19: "it's Mr. Blood's drawing (mine)").
    words.appendChild(document.createTextNode(o && o.own ? ' on your own drawing' : first ? ' on ' + first + '’s' : ''));
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'da-skip db-theirs';
    btn.innerHTML = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false">'
      + '<circle cx="10" cy="10" r="7.25" fill="none" stroke="currentColor" stroke-width="1.8"/>'
      + '<path class="db-half" d="M10 2.75a7.25 7.25 0 0 1 0 14.5z" fill="currentColor"/></svg><span>Theirs</span>';
    pill.appendChild(words);
    pill.appendChild(btn);
    document.body.appendChild(pill);
    document.body.classList.add('drawback');
    run = { strokes: strokesOf(payload), size: size, guide: guide, pill: pill, btn: btn, state: 0, off: null,
            first: first, own: !!(o && o.own), folded: false,
            onResize: function () { place(); paint(); paintPhoto(); }, onScroll: function () { corner(); } };
    // THE FIRST STROKE folds the pill (fold, above): down on the drawing and
    // up after moving, as Draw along counts one (lib/drawalong.js); a pinch
    // that takes the finger away is no stroke.
    var down = null;
    run.onDown = function (e) {
      down = (run && !run.folded && e.isPrimary && e.target === target()) ? { x: e.clientX, y: e.clientY, d: 0 } : null;
    };
    run.onMove = function (e) {
      if (down && e.isPrimary) down.d = Math.max(down.d, Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y));
    };
    run.onUp = function (e) {
      var was = down;
      down = null;
      if (was && was.d > 6 && e.type === 'pointerup') fold();
    };
    document.addEventListener('pointerdown', run.onDown, true);
    document.addEventListener('pointermove', run.onMove, true);
    document.addEventListener('pointerup', run.onUp, true);
    document.addEventListener('pointercancel', run.onUp, true);
    // HER PHOTO, under the canvas where the Pad's own would lie.
    var ph = photoOf(payload);
    if (ph) {
      var pc = document.createElement('canvas');
      pc.className = 'photo-bg-img db-photo';
      pc.setAttribute('aria-hidden', 'true');
      cv.parentNode.insertBefore(pc, cv);
      run.photo = ph;
      run.photoCanvas = pc;
      run.photoImg = new Image();
      run.photoImg.onload = function () { if (run && run.photoCanvas === pc) paintPhoto(); };
      run.photoImg.src = ph.data;
    }
    guard();
    // What the editor says goes under the pill, never over it (lib/drawalong.js).
    if (window.SkriblDrawAlong && window.SkriblDrawAlong.keepNotesClear) window.SkriblDrawAlong.keepNotesClear();
    // If the eraser was in hand, the pen takes over.
    if (typeof tool !== 'undefined' && tool === 'eraser' && typeof window.setTool === 'function') window.setTool('pen');
    btn.addEventListener('click', function () {
      if (!run) return;
      run.state = (run.state + 1) % STATES.length;
      say();
      paint();
    });
    window.addEventListener('resize', run.onResize);
    // The canvas changes size as the Pad lays itself out (zoom, a phone
    // turned): the original follows it.
    if (window.ResizeObserver) {
      run.ro = new ResizeObserver(function () { paint(); paintPhoto(); place(); });
      run.ro.observe(cv);
      // ...and the folded button its corner, as the drawing's area changes.
      var fa = frameOf();
      if (fa) run.ro.observe(fa.area);
    }
    say();
    place();
    paint();
    return true;
  }

  window.SkriblDrawBack = {
    take: take, stop: stop, paintUnder: paintUnder,
    state: function () { return run ? { theirs: STATES[run.state].key, strokes: run.strokes.length, size: run.size, photo: !!run.photo } : null; }
  };
}());
