/* The card on the button: help where the question is (owner, after v323:
 * "Can we combine them so we get the best, most helpful yet unobtrusive?",
 * then "All yes" to the button cards mock). Piece one of the help in four
 * layers (FUTURE.md 6p): the card, holding and resting, the name tags and
 * the first-time note. One module for the Pad and Flip.
 *
 * ONE CARD EVERYWHERE. A button's card is its name, one kind sentence, its
 * example drawing itself when it has one (the same real Skribl How it works
 * plays, through the same in-post player; a phone recording for Photo and
 * music and Post), More (How it works, searched for it) and Got it.
 *
 * HOW IT OPENS. On a touch screen, hold the button about half a second
 * (HOLD); a quick tap is still a tap, a finger that moves is a drag, and the
 * lift after the card opens does not also press the button. With a mouse,
 * rest on the button about a second (REST) and move away to close: the
 * button's own tooltip (lib/tooltip.js) names it first, and the card grows
 * out of that pause, the tooltip stepping aside while it shows. "?" puts a
 * name tag on every button; a tag opens that button's card, from the
 * keyboard too. How it works' "Name every button" does the same.
 *
 * HOLDING KEEPS EVERY JOB IT ALREADY HAS (owner: "how will that affect
 * buttons you hold already like moving pages on flip?"). A Flip page (hold,
 * then drag to move it), the slider - and + (hold repeats) and the x1 badge
 * are TAG-ONLY: holding them does what it always did, and their card opens
 * from their name tag. The Pages card says how to move a page.
 *
 * THE FIRST-TIME NOTE says so once, ever, on a page of its own, and not on
 * the visit Blooby says hi (lib/hello.js): one welcome at a time.
 *
 * AUTOMATION NEVER MEETS ANY OF THIS unless it asks (window.__skriblLearnForce,
 * set before the page loads), as with the hello: a card that opened when a
 * suite rested on a button would be in every measurement's way.
 * verify_learncard asks. SkriblLearnCard.open/close/tags/note are the API.
 */
(function () {
  'use strict';
  var HOLD = 500, MOVE = 10, REST = 1000, GRACE = 250;
  var NOTE_KEY = 'skribl.learncard.note.v1';
  var force = window.__skriblLearnForce === true;
  var live = force || !navigator.webdriver;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var touchFirst = window.matchMedia && window.matchMedia('(hover: none)').matches;

  // name, sentence, example (demo: a real Skribl from How it works; clip: a
  // phone recording), the How it works search that More opens, and tagOnly
  // where holding already does something.
  var CARDS = [
    { sel: '#penToolBtn', name: 'Pen', tag: 'Pen', demo: 'pen',
      line: 'Press harder for a thicker line. Tap Pen again for colour and brush; drag sideways for size.' },
    { sel: '#eraserToolBtn', name: 'Eraser', tag: 'Eraser', demo: 'eraser',
      line: 'Rubs out what you drew, and the replay shows it rubbing out.' },
    { sel: '#shapeToolBtn', name: 'Shapes', tag: 'Shapes', demo: 'shape', more: 'Shape',
      line: 'Straight lines, rectangles, ovals and polygons. Tap again to pick which.' },
    { sel: '#toolMoreBtn', name: 'More tools', tag: 'More tools', more: 'Fill',
      line: 'Fill, blur, smudge, select, stamp and more, for this page.' },
    { sel: '#undoBtn, #undo', name: 'Undo', tag: 'Undo', line: 'Takes back your last stroke. Redo puts it back.' },
    { sel: '#redoBtn, #redo', name: 'Redo', tag: 'Redo', more: 'Undo', line: 'Puts back what Undo took away.' },
    { sel: '#mediaOpenBtn', name: 'Photo and music', tag: 'Photo and music', clip: 'photo', more: 'Music',
      line: 'A photo under your drawing, or a song that loops while it plays.' },
    { sel: '#postBtn', name: 'Post', tag: 'Post', clip: 'post',
      line: 'Get a link anyone can open to watch your drawing draw itself.' },
    { sel: '#tuneBtn', name: 'Tune', tag: 'Tune', more: 'Grid',
      line: 'Grid, mirror, pauses, and how fast Play shows your drawing.' },
    { sel: '#menuBtn, #moreBtn', name: 'Menu', tag: 'Menu', more: 'Export',
      line: 'New, Save, Export, your drafts, and help.' },
    { sel: '#addcopy', name: 'Duplicate', tag: 'Duplicate', demo: 'flip-wave',
      line: 'A new page that starts as a copy of this one. Nudge it and redraw: that’s animation.' },
    { sel: '#addblank', name: 'Blank', tag: 'Blank', more: 'Duplicate', line: 'A new empty page after this one.' },
    { sel: '#addinbetween', name: 'Tween', tag: 'Tween', line: 'Draws one page halfway between this page and the next.' },
    { sel: '#addtween', name: 'Smear', tag: 'Smear', line: 'Shows the movement between two drawings, like a long exposure.' },
    { sel: '#strip .frame', name: 'Pages', tag: 'Pages', tagOnly: true, more: 'Reorder',
      line: 'Tap a page to open it. Hold a page, then drag to move it.' },
    { sel: '.holdbadge', name: 'How long a page stays', tag: 'Page time', tagOnly: true, more: 'Hold',
      line: 'Tap ×1 to keep this page on screen longer: ×2, ×3, ×4.' },
    { sel: '.slider-nudge-btn', name: 'Slider steps', tag: 'Steps', tagOnly: true, more: 'Size',
      line: 'Each tap on − or + nudges the value; hold to keep going.' }
  ];

  function shown(el) {
    if (!el || !el.getClientRects().length || el.closest('[hidden], [inert]')) return false;
    var r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return false;
    var at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    // A disabled button (Undo with nothing to undo) takes no pointer, so the
    // point lands on what holds it; it is still there to be named.
    return !!at && (at === el || el.contains(at) || at.closest('.lc-card, .lc-tag') !== null
                    || (el.disabled && at.contains(el)));
  }
  function specFor(el) {
    for (var i = 0; i < CARDS.length; i++) {
      var hit = el.closest && el.closest(CARDS[i].sel);
      if (hit) return { spec: CARDS[i], el: hit };
    }
    return null;
  }

  // ---- the example ----------------------------------------------------------
  var watch = document.getElementById('helpWatch');
  var ready = null, payloads = {};
  function loadPlayer() {
    if (ready) return ready;
    ready = new Promise(function (done) {
      if (window.SkriblInline || !watch) { done(); return; }
      var css = document.createElement('link');
      css.rel = 'stylesheet'; css.href = watch.getAttribute('data-player-css');
      document.head.appendChild(css);
      var js = document.createElement('script');
      js.src = watch.getAttribute('data-player-js');
      js.onload = js.onerror = function () { done(); };
      document.head.appendChild(js);
    });
    return ready;
  }
  var h264 = (function () {
    try { return !!document.createElement('video').canPlayType('video/mp4; codecs="avc1.640028"'); } catch (e) { return true; }
  }());
  function picture(spec, box) {
    if (!watch) return null;
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    if (spec.clip) {
      var src = watch.querySelector('.learn-clip[data-clip-name="' + spec.clip + '"]');
      if (!src) return null;
      var frame = document.createElement('div'); frame.className = 'lc-phone';
      var v = document.createElement('video');
      v.muted = true; v.loop = true; v.playsInline = true; v.setAttribute('playsinline', ''); v.setAttribute('aria-hidden', 'true');
      v.poster = src.getAttribute(light ? 'data-poster-light' : 'data-poster-dark');
      if (!reduce) { v.src = src.getAttribute('data-clip-' + (light ? 'light' : 'dark') + (h264 ? '' : '-webm')); v.autoplay = true; }
      frame.appendChild(v); box.appendChild(frame);
      return { stop: function () { v.pause(); v.removeAttribute('src'); } };
    }
    if (!spec.demo) return null;
    var card = watch.querySelector('.learn-card[data-demo-name="' + spec.demo + '"]');
    if (!card) return null;
    var stage = document.createElement('div'); stage.className = 'lc-stage';
    stage.innerHTML = card._learnPristine || card.querySelector('.learn-stage').innerHTML;
    box.appendChild(stage);
    var state = { p: null, gone: false };
    var url = card.getAttribute('data-demo');
    loadPlayer().then(function () {
      if (payloads[url]) return payloads[url];
      payloads[url] = fetch(url).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
      return payloads[url];
    }).then(function (payload) {
      if (state.gone || !payload || !window.SkriblInline) return;
      var p = window.SkriblInline.attach(stage.querySelector('.skribl-inline'), payload, { ambient: true });
      if (!p) return;
      p.setLoop(true); state.p = p;
      if (!reduce) p.play();
    });
    return { stop: function () { state.gone = true; if (state.p) state.p.pause(); } };
  }

  // ---- the card -------------------------------------------------------------
  var cardEl = null, current = null, leaveTimer = null;
  function more(spec) {
    close(false);
    if (typeof window.openHelpDrawer !== 'function') return;
    window.openHelpDrawer();
    var look = document.getElementById('helpTabLook'), q = document.getElementById('helpSearch');
    setTimeout(function () {
      if (look) look.click();
      if (q) { q.value = spec.more || spec.name; q.dispatchEvent(new Event('input', { bubbles: true })); }
    }, 60);
  }
  function place(el) {
    var b = el.getBoundingClientRect();
    var w = cardEl.offsetWidth, h = cardEl.offsetHeight;
    var above = b.top - h - 14 >= 8 || b.bottom + h + 14 > innerHeight - 8;
    var left = Math.max(12, Math.min(innerWidth - w - 12, b.left + b.width / 2 - w / 2));
    cardEl.style.left = left + 'px';
    cardEl.style.top = Math.max(8, above ? b.top - h - 14 : b.bottom + 14) + 'px';
    cardEl.classList.toggle('lc-below', !above);
    cardEl.style.setProperty('--lc-ax', Math.max(18, Math.min(w - 18, b.left + b.width / 2 - left)) + 'px');
  }
  function open(target, how) {
    var hit = typeof target === 'string' ? specFor(document.querySelector(target) || document.body) : specFor(target);
    if (!hit) return false;
    close(false);
    var spec = hit.spec, el = hit.el;
    var desk = how === 'rest';
    cardEl = document.createElement('div');
    cardEl.className = 'lc-card';
    cardEl.setAttribute('role', 'dialog');
    cardEl.setAttribute('aria-labelledby', 'lcTitle');
    var pic = document.createElement('div'); pic.className = 'lc-pic';
    var body = document.createElement('div'); body.className = 'lc-body';
    body.innerHTML = '<p class="lc-t" id="lcTitle"></p><p class="lc-line"></p><div class="lc-foot">'
      + '<button type="button" class="lc-more">More</button>'
      + (desk ? '<span class="lc-hint">Move away to close</span>' : '<button type="button" class="lc-ok">Got it</button>')
      + '</div>';
    body.querySelector('.lc-t').textContent = spec.name;
    body.querySelector('.lc-line').textContent = spec.line;
    cardEl.appendChild(pic); cardEl.appendChild(body);
    document.body.appendChild(cardEl);
    var ex = picture(spec, pic);
    if (!ex) pic.remove();
    current = { spec: spec, el: el, how: how, ex: ex };
    el.classList.add('lc-target');
    document.body.classList.add('lc-open');
    place(el);
    body.querySelector('.lc-more').addEventListener('click', function () { more(spec); });
    var ok = body.querySelector('.lc-ok');
    if (ok) ok.addEventListener('click', function () { close(true); });
    if (desk) {
      cardEl.addEventListener('pointerenter', function () { clearTimeout(leaveTimer); });
      cardEl.addEventListener('pointerleave', leaveSoon);
    } else if (ok) {
      ok.focus({ preventScroll: true });
    }
    return true;
  }
  function close(refocus) {
    clearTimeout(leaveTimer);
    cancelRest();
    if (!cardEl) return;
    if (current && current.ex) current.ex.stop();
    if (current) current.el.classList.remove('lc-target');
    var back = current && refocus && current.how !== 'rest' ? current.el : null;
    cardEl.remove(); cardEl = null; current = null;
    if (!tagLayer) document.body.classList.remove('lc-open');
    if (back && shown(back)) back.focus({ preventScroll: true });
  }
  function leaveSoon() {
    clearTimeout(leaveTimer);
    leaveTimer = setTimeout(function () { if (current && current.how === 'rest') close(false); }, GRACE);
  }

  // ---- holding (touch) -----------------------------------------------------
  var hold = null, swallowUntil = 0;
  document.addEventListener('pointerdown', function (e) {
    if (!live) return;
    if (cardEl && !cardEl.contains(e.target) && !(current && current.el.contains(e.target))) close(false);
    if (e.pointerType === 'mouse') { cancelRest(); return; }
    var hit = specFor(e.target);
    if (!hit || hit.spec.tagOnly || hit.el.disabled) return;
    var x = e.clientX, y = e.clientY, id = e.pointerId;
    clearTimeout(hold && hold.t);
    hold = { id: id, x: x, y: y, t: setTimeout(function () {
      hold = null;
      if (open(hit.el, 'hold')) swallowUntil = Date.now() + 1500;
    }, HOLD) };
  }, true);
  document.addEventListener('pointermove', function (e) {
    if (hold && e.pointerId === hold.id && Math.hypot(e.clientX - hold.x, e.clientY - hold.y) > MOVE) { clearTimeout(hold.t); hold = null; }
  }, true);
  function endHold(e) {
    if (hold && e.pointerId === hold.id) { clearTimeout(hold.t); hold = null; }
  }
  document.addEventListener('pointerup', endHold, true);
  document.addEventListener('pointercancel', endHold, true);
  // The lift after a card opened is not a press: its click is swallowed once.
  document.addEventListener('click', function (e) {
    if (swallowUntil && Date.now() < swallowUntil && current && current.el.contains(e.target)) {
      e.preventDefault(); e.stopImmediatePropagation(); swallowUntil = 0;
    }
  }, true);
  // No system callout or context menu on a button that holds a card.
  document.addEventListener('contextmenu', function (e) {
    var hit = live && specFor(e.target);
    if (hit && !hit.spec.tagOnly) e.preventDefault();
  }, true);

  // ---- resting (mouse) -------------------------------------------------------
  var rest = null;
  function cancelRest() {
    if (!rest) return;
    clearTimeout(rest.t);
    rest = null;
  }
  document.addEventListener('pointerover', function (e) {
    if (!live || e.pointerType !== 'mouse' || document.body.classList.contains('stroking')) return;
    var hit = specFor(e.target);
    if (!hit) return;
    if (current && current.el === hit.el) { clearTimeout(leaveTimer); return; }
    if (rest && rest.el === hit.el) return;
    cancelRest();
    rest = { el: hit.el, t: setTimeout(function () { if (rest && rest.el === hit.el) open(hit.el, 'rest'); }, REST) };
  }, true);
  document.addEventListener('pointerout', function (e) {
    if (!rest && !(current && current.how === 'rest')) return;
    var from = specFor(e.target), to = e.relatedTarget;
    if (rest && from && from.el === rest.el && !(to && rest.el.contains(to))) cancelRest();
    if (current && current.how === 'rest' && from && from.el === current.el && !(to && (current.el.contains(to) || (cardEl && cardEl.contains(to))))) leaveSoon();
  }, true);

  // ---- the name tags ---------------------------------------------------------
  var tagLayer = null;
  function tags(on) {
    if (on === undefined) on = !tagLayer;
    if (tagLayer) { tagLayer.remove(); tagLayer = null; }
    if (!on) { if (!cardEl) document.body.classList.remove('lc-open'); return false; }
    close(false);
    tagLayer = document.createElement('div');
    tagLayer.className = 'lc-tags';
    var placed = [];
    CARDS.forEach(function (spec) {
      var el = Array.prototype.find.call(document.querySelectorAll(spec.sel), shown);
      if (!el) return;
      var t = document.createElement('button');
      t.type = 'button'; t.className = 'lc-tag'; t.textContent = spec.tag;
      t.setAttribute('aria-label', 'What is ' + spec.name + '?');
      t.addEventListener('click', function () { tags(false); open(el, 'tag'); });
      tagLayer.appendChild(t);
      placed.push({ t: t, el: el });
    });
    var banner = document.createElement('div');
    banner.className = 'lc-banner';
    banner.innerHTML = '<div><p class="lc-t"></p><p class="lc-line"></p></div><button type="button" class="lc-ok">Done</button>';
    banner.querySelector('.lc-t').textContent = 'Tap a name to learn it';
    banner.querySelector('.lc-line').textContent = touchFirst ? 'Or hold any button, any time.' : 'Or rest on any button. ? shows the names.';
    banner.querySelector('.lc-ok').addEventListener('click', function () { tags(false); });
    tagLayer.appendChild(banner);
    document.body.appendChild(tagLayer);
    document.body.classList.add('lc-open');
    // Each tag above its button (below, for the header's), then nudged up a
    // row while it overlaps one already placed.
    var rects = [];
    placed.forEach(function (p) {
      var b = p.el.getBoundingClientRect(), w = p.t.offsetWidth, h = p.t.offsetHeight;
      var below = b.top < innerHeight / 3;
      var left = Math.max(6, Math.min(innerWidth - w - 6, b.left + b.width / 2 - w / 2));
      var top = below ? b.bottom + 6 : b.top - h - 6;
      for (var k = 0; k < 6; k++) {
        var hitR = rects.some(function (r) { return left < r.r + 4 && left + w + 4 > r.l && top < r.b + 3 && top + h + 3 > r.t; });
        if (!hitR) break;
        top += below ? h + 4 : -(h + 4);
      }
      p.t.style.left = left + 'px'; p.t.style.top = top + 'px';
      rects.push({ l: left, r: left + w, t: top, b: top + h });
    });
    var first = tagLayer.querySelector('.lc-tag');
    if (first && !touchFirst) first.focus({ preventScroll: true });
    return true;
  }

  // ---- the first-time note -------------------------------------------------
  function note(forceShow) {
    try { if (!forceShow && localStorage.getItem(NOTE_KEY) === '1') return false; } catch (e) { return false; }
    var dock = document.getElementById('penToolBtn');
    if (!dock) return false;
    var n = document.createElement('div');
    n.className = 'lc-note'; n.setAttribute('role', 'status');
    n.innerHTML = '<span class="lc-note-ic" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="8" cy="8" r="1.5"/></svg></span><p class="lc-line"></p><button type="button" class="lc-ok">Got it</button>';
    n.querySelector('.lc-line').textContent = touchFirst ? 'Hold any button to see what it does.'
      : 'Rest on any button to see what it does. Press ? to name them all.';
    var done = function () { try { localStorage.setItem(NOTE_KEY, '1'); } catch (e) {} n.remove(); };
    n.querySelector('.lc-ok').addEventListener('click', done);
    document.body.appendChild(n);
    var b = dock.getBoundingClientRect();
    n.style.top = Math.max(8, b.top - n.offsetHeight - 12) + 'px';
    return true;
  }

  // ---- keys, and getting out of the way --------------------------------------
  document.addEventListener('keydown', function (e) {
    if (!live) return;
    if (e.key === 'Escape') {
      if (cardEl) { close(true); e.stopPropagation(); }
      else if (tagLayer) { tags(false); e.stopPropagation(); }
      return;
    }
    if (e.key !== '?' || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if (document.querySelector('[aria-modal="true"]:not([hidden])') && !document.getElementById('helpDrawer').hidden) return;
    e.preventDefault();
    tags();
  }, true);
  window.addEventListener('resize', function () { close(false); if (tagLayer) tags(false); });

  var namesBtn = document.getElementById('learnNames');
  if (namesBtn) {
    var sub = namesBtn.querySelector('.learn-names-sub');
    if (sub && !touchFirst) sub.textContent = 'Or rest on any button, or press ?';
    namesBtn.addEventListener('click', function () {
      if (typeof window.closeHelpDrawer === 'function') window.closeHelpDrawer();
      setTimeout(function () { tags(true); }, 420);
    });
  }

  if (live && window.top === window && !/[?&]compose=1\b/.test(location.search)) {
    var helloComing = false;
    try { helloComing = !!document.getElementById('skriblHello') && localStorage.getItem('skribl.hello.v1') !== '1'
                        && window.matchMedia('(hover: none) and (pointer: coarse)').matches; } catch (e) {}
    if (!helloComing) setTimeout(function () { note(false); }, 1500);
  }

  window.SkriblLearnCard = {
    open: function (t) { return open(t, 'tag'); }, close: function () { close(false); },
    tags: tags, note: note, cards: CARDS,
    isOpen: function () { return !!cardEl; }
  };
}());
