/* How it works, shown: the example cards at the top of the help panel.
 *
 * Every card plays a REAL Skribl -- one harness/tools/make_help_demos.py drew
 * by driving the editor -- through the same in-post player that plays posts
 * (inlineplayer.js). So the Eraser card is what the eraser does, and there is
 * no second, simplified renderer to drift from the real one.
 *
 * NOTHING LOADS UNTIL THE PANEL OPENS. The player, its stylesheet and the
 * examples are fetched the first time How it works is shown; an editor that
 * never opens help pays nothing for it. Examples play only while their card is
 * on screen and the panel is open, silent and looping, all together (the
 * player's ambient mode: an example never stops another, see inlineplayer.js
 * play()). With reduced motion asked for, each card shows its finished
 * drawing and does not play.
 *
 * TRY IT closes the panel and picks the tool by the editor's own route -- the
 * dock button on Pad, shelfSetTool on Flip, which also open the shape card --
 * so it can never select a tool differently from a tap on the tool itself.
 */
(function () {
  'use strict';
  var box = document.getElementById('helpLearn');
  var drawer = document.getElementById('helpDrawer');
  if (!box || !drawer) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cards = Array.prototype.slice.call(box.querySelectorAll('.learn-card[data-demo]'));
  var clips = Array.prototype.slice.call(box.querySelectorAll('.learn-card[data-clip-dark]'));
  var ready = null;
  var visible = new Set();

  function loadPlayer() {
    if (ready) return ready;
    ready = new Promise(function (done) {
      if (window.SkriblInline) { done(); return; }
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = box.getAttribute('data-player-css');
      document.head.appendChild(css);
      var js = document.createElement('script');
      js.src = box.getAttribute('data-player-js');
      js.onload = js.onerror = function () { done(); };
      document.head.appendChild(js);
    });
    return ready;
  }

  function open() { return !drawer.hidden; }

  function sync(card) {
    var v = card.querySelector('.learn-video');
    if (v) {
      if (!v.getAttribute('src')) return;
      if (open() && visible.has(card) && !reduce) { var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); }
      else v.pause();
      return;
    }
    var p = card._learnPlayer;
    if (!p || reduce) return;
    if (open() && visible.has(card)) p.play(); else p.pause();
  }

  // A screen clip matches the theme around it: lib/theme.js marks light with
  // data-theme="light" on the root, and anything else is dark.
  // H.264 where the browser has it (every iPhone, Chrome, Safari), VP9 where
  // it does not; only the one that will play is fetched.
  var h264 = (function () {
    try { return !!document.createElement('video').canPlayType('video/mp4; codecs="avc1.640028"'); }
    catch (e) { return true; }
  }());
  function clipSrc(card) {
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    return card.getAttribute('data-clip-' + (light ? 'light' : 'dark') + (h264 ? '' : '-webm'));
  }
  function startClip(card) {
    var v = card.querySelector('.learn-video');
    var src = clipSrc(card);
    if (v.getAttribute('src') === src) return;
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    // The poster is the clip's landed moment. With reduced motion it is all
    // that shows: the video is not even fetched.
    v.setAttribute('poster', card.getAttribute(light ? 'data-poster-light' : 'data-poster-dark'));
    if (reduce) { card.classList.add('learn-ready'); return; }
    v.setAttribute('src', src);
    v.preload = 'auto';
    if (!card._learnSeen) { card._learnSeen = true; if (io) io.observe(card); else visible.add(card); }
    card.classList.add('learn-ready');
    sync(card);
  }
  new MutationObserver(function () { if (open()) clips.forEach(startClip); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  var io = window.IntersectionObserver ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) visible.add(e.target); else visible.delete(e.target);
      sync(e.target);
    });
  }, { threshold: 0.35 }) : null;

  function start(card) {
    if (card._learnStarted) return;
    card._learnStarted = true;
    fetch(card.getAttribute('data-demo'))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (payload) {
        if (!payload || !window.SkriblInline) { card.classList.add('learn-failed'); return; }
        var p = window.SkriblInline.attach(card.querySelector('.skribl-inline'), payload, { ambient: true });
        if (!p) { card.classList.add('learn-failed'); return; }
        p.setLoop(true);
        card._learnPlayer = p;
        card.classList.add('learn-ready');
        if (io) io.observe(card); else visible.add(card);
        sync(card);
      })
      .catch(function () { card.classList.add('learn-failed'); });
  }

  function onOpenChange() {
    if (open()) {
      clips.forEach(startClip);
      clips.forEach(sync);
      loadPlayer().then(function () { cards.forEach(start); cards.forEach(sync); });
    } else {
      cards.forEach(sync);
      clips.forEach(sync);
    }
  }
  new MutationObserver(onOpenChange).observe(drawer, { attributes: true, attributeFilter: ['hidden'] });
  if (open()) onOpenChange();

  // While searching, the reference is what answers; the examples step aside.
  var search = document.getElementById('helpSearch');
  if (search) search.addEventListener('input', function () {
    box.hidden = !!search.value.trim();
  });

  box.addEventListener('click', function (e) {
    var b = e.target.closest('[data-try]');
    if (!b) return;
    var tool = b.getAttribute('data-try');
    var close = document.getElementById('helpClose');
    if (close) close.click();
    // After this tap has finished travelling: the shape card's dismisser hears
    // every click on the page, and would close the card this tap just opened.
    setTimeout(function () {
      if (typeof window.shelfSetTool === 'function') { window.shelfSetTool(tool); return; }
      var btn = document.querySelector('.tool-btn[data-tool="' + tool + '"]');
      // A tap on the tool you already hold opens its options instead; Try it
      // means "hold this tool", so an active one is left as it is.
      if (btn && !btn.classList.contains('active')) btn.click();
    }, 0);
  });

  window.SkriblHelpLearn = { cards: function () { return cards; }, clips: function () { return clips; } };
}());
