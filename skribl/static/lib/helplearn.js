/* How it works, shown: the Watch tab of the help panel, and its two tabs.
 *
 * Every card plays a REAL Skribl -- drawn through the editor with real pen
 * input by harness/tools/make_art.py and make_flip.py -- through the same
 * in-post player that plays posts (inlineplayer.js). So the Eraser card is
 * what the eraser does, and there is no second, simplified renderer to drift
 * from the real one.
 *
 * ASK'S HOME (piece two of the help, FUTURE.md 6p; lib/ask.js). How it
 * works opens on Ask: the tour, what people often ask, and every example in
 * a strip of pictures, each opening full screen with its Try it. Typed into,
 * or "Everything, by section", it shows the answers: search and every entry
 * (lib/helpsearch.js). It replaced two tabs (layout 1, FUTURE.md 6n), and
 * before them a bar that opened a drawer over a 2,700-word manual.
 *
 * NOTHING LOADS UNTIL IT IS ASKED FOR. The editor fetches no player and no
 * example until How it works opens; then an example is fetched as it comes
 * within half a screen of view. Examples play only while Watch is showing
 * and their card is on screen, silent and looping, all together (the
 * player's ambient mode: an example never stops another, see inlineplayer.js
 * play()). With reduced motion asked for, each card shows its finished
 * drawing and does not play.
 *
 * MORE ABOUT a tool takes you to its entry in Look it up, opened.
 *
 * TRY IT closes the panel and picks the tool by the editor's own route -- the
 * dock button on Pad, shelfSetTool on Flip, which also open the shape card --
 * so it can never select a tool differently from a tap on the tool itself.
 */
(function () {
  'use strict';
  var drawer = document.getElementById('helpDrawer');
  var sheet = document.getElementById('helpWatch');
  var look = document.getElementById('helpLook');
  var tabWatch = document.getElementById('helpTabWatch');
  var tabLook = document.getElementById('helpTabLook');
  var box = sheet;
  // ASK (after v323) took the two tabs' place: Watch is Ask's home and Look it
  // up its answers, switched by what is typed (lib/ask.js) through show()
  // below. The tabs are optional, so this file still drives either markup.
  var answer = document.getElementById('askAnswer');
  if (!drawer || !sheet || !look) return;
  var scroller = drawer.querySelector('.help-drawer-inner');

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var all = Array.prototype.slice.call(sheet.querySelectorAll('.learn-card'));
  var cards = all.filter(function (c) { return c.hasAttribute('data-demo'); });
  var clips = all.filter(function (c) { return c.hasAttribute('data-clip-dark'); });
  var ready = null;
  var visible = new Set();
  var sheetOpen = false;

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

  var viewerOpen = false;
  function open() { return !drawer.hidden && sheetOpen && !viewerOpen; }

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
    // A clip that cannot be fetched or played says so, as a replay does.
    if (!v._learnErr) { v._learnErr = true; v.addEventListener('error', function () { failed(card); }); }
    v.setAttribute('src', src);
    v.preload = 'auto';
    if (!card._learnSeen) { card._learnSeen = true; if (io) io.observe(card); else visible.add(card); }
    card.classList.add('learn-ready');
    sync(card);
  }
  // Only the clips already asked for change recording; the rest are fetched
  // in the right theme when they come near the screen.
  new MutationObserver(function () {
    if (open()) clips.forEach(function (c) { if (c._learnWanted) startClip(c); });
  })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  var io = window.IntersectionObserver ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) visible.add(e.target); else visible.delete(e.target);
      sync(e.target);
    });
  }, { threshold: 0.35 }) : null;

  // The player box as the template drew it, before attach() fills it: the
  // full-screen viewer builds its own player from this.
  cards.forEach(function (c) {
    var st = c.querySelector('.learn-stage');
    if (st) c._learnPristine = st.innerHTML;
  });

  function start(card) {
    if (card._learnStarted) return card._learnLoad;
    card._learnStarted = true;
    card._learnLoad = fetch(card.getAttribute('data-demo'))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (payload) {
        card._learnPayload = payload;
        if (!payload || !window.SkriblInline) { failed(card); return; }
        var p = window.SkriblInline.attach(card.querySelector('.skribl-inline'), payload, { ambient: true });
        if (!p) { failed(card); return; }
        p.setLoop(true);
        card._learnPlayer = p;
        card.classList.add('learn-ready');
        if (io) io.observe(card); else visible.add(card);
        sync(card);
      })
      .catch(function () { failed(card); });
    return card._learnLoad;
  }

  // ---- what did not load (outside audit V319-004) ---------------------------
  // A failed example was marked with a class nothing drew, so it sat there as
  // an empty tile. The sheet's banner counts them and Retry asks again for
  // those alone -- the player script too, if that is what failed.
  var failBox = document.getElementById('learnFail');
  var failCount = document.getElementById('learnFailCount');
  var retryBtn = document.getElementById('learnRetry');
  function tellFails() {
    if (!failBox) return;
    var n = all.filter(function (c) { return c.classList.contains('learn-failed'); }).length;
    var was = !failBox.hidden;
    failBox.hidden = !n;
    failCount.textContent = !n ? '' : (n === 1 ? '1 example couldn\u2019t load.'
                                               : n + ' examples couldn\u2019t load.');
    // Retry hides the banner it is in; focus goes to the Watch tab rather
    // than to <body>.
    if (was && !n && failBox.contains(document.activeElement)) (tabWatch || document.getElementById('helpSearch')).focus({ preventScroll: true });
  }
  function failed(card) {
    card.classList.add('learn-failed');
    tellFails();
  }
  if (retryBtn) retryBtn.addEventListener('click', function () {
    var again = all.filter(function (c) { return c.classList.contains('learn-failed'); });
    if (!window.SkriblInline) ready = null;
    again.forEach(function (c) {
      c.classList.remove('learn-failed');
      if (c.hasAttribute('data-clip-dark')) {
        c.querySelector('.learn-video').removeAttribute('src');
        if (open()) startClip(c);
      } else {
        c._learnStarted = false;
        c._learnLoad = null;
      }
    });
    tellFails();
    loadPlayer().then(function () {
      again.forEach(function (c) { if (c.hasAttribute('data-demo')) { start(c); sync(c); } });
    });
  });

  // ---- loading follows the eye (outside audit V319-005) ---------------------
  // Opening the drawer used to fetch every example in it -- about 3 MB of
  // replays and clips for someone who came to watch one. An example is asked
  // for now when it comes within half a screen of the sheet's view, so what
  // opening costs is what is on screen and the row after it. Playback was
  // already tied to visibility (`io` above); this ties the fetch to it too.
  function want(card) {
    if (card._learnWanted) return;
    card._learnWanted = true;
    if (near) near.unobserve(card);
    if (card.hasAttribute('data-clip-dark')) { startClip(card); sync(card); }
    else loadPlayer().then(function () { start(card); sync(card); });
  }
  var near = window.IntersectionObserver ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting && open()) want(e.target); });
  }, { root: scroller, rootMargin: '0px 0px 50% 0px' }) : null;
  function startAll() {
    // No observer (a very old browser): everything, as before.
    if (!near) { all.forEach(want); return; }
    // unobserve first: observing a target twice is a no-op, and a sheet shut
    // before the first report would otherwise never report again.
    all.forEach(function (c) { if (!c._learnWanted) { near.unobserve(c); near.observe(c); } });
  }
  function syncAll() { cards.forEach(sync); clips.forEach(sync); }
  // To the top AT ONCE: the panel scrolls smoothly, and gliding back up past
  // every example on a change of tab or chip looked like a fault.
  function toTop() {
    if (!scroller) return;
    if (scroller.scrollTo) scroller.scrollTo({ top: 0, behavior: 'instant' });
    else scroller.scrollTop = 0;
  }

  // ---- the views: home (the examples), the answers, one answer --------------
  var view = 'home';
  function show(next, focus) {
    var was = view;
    view = next;
    sheetOpen = view === 'home';
    sheet.hidden = view !== 'home';
    look.hidden = view !== 'look';
    if (answer) answer.hidden = view !== 'answer';
    if (tabWatch && tabLook) {
      tabWatch.setAttribute('aria-selected', String(sheetOpen));
      tabLook.setAttribute('aria-selected', String(!sheetOpen));
      tabWatch.tabIndex = sheetOpen ? 0 : -1;
      tabLook.tabIndex = sheetOpen ? -1 : 0;
      if (focus) (sheetOpen ? tabWatch : tabLook).focus({ preventScroll: true });
    }
    if (view !== was) toTop();
    if (sheetOpen) startAll();
    syncAll();
    look.dispatchEvent(new CustomEvent('helptab', { bubbles: true, detail: { look: view === 'look' } }));
  }
  function showTab(watch, focus) { show(watch ? 'home' : 'look', focus); }
  if (tabWatch && tabLook) {
  tabWatch.addEventListener('click', function () { showTab(true); });
  tabLook.addEventListener('click', function () { showTab(false); });
  // A tab list's own keys: the arrows move between the tabs, Home and End to
  // either end.
  [tabWatch, tabLook].forEach(function (t) {
    t.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'Home' || e.key === 'End') {
        e.preventDefault();
        var watch = e.key === 'Home' ? true : e.key === 'End' ? false : t !== tabWatch;
        showTab(watch, true);
      }
    });
  });
  }
  // Escape closes full screen first; otherwise it is the panel's (the
  // editors' window-level Escape closes How it works).
  drawer.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (viewerOpen) { e.stopPropagation(); e.preventDefault(); closeViewer(); }
  });

  // ---- full screen ------------------------------------------------------------
  // A tap on an example opens it large (owner: "we should be allowed to click
  // ... and have it full screen"). A replay gets a player of its own, built
  // from the box the template drew; a clip, the same recording. The cards
  // pause underneath. Caught at the stage, before the player's own tap-to-
  // pause hears it.
  var viewer = document.getElementById('learnViewer');
  var vStage = document.getElementById('learnViewerStage');
  var vTitle = document.getElementById('learnViewerTitle');
  var vPlayer = null, vVideo = null, vFrom = null;
  function closeViewer() {
    if (!viewerOpen || !viewer) return;
    viewerOpen = false;
    if (vPlayer) { try { vPlayer.pause(); } catch (e) {} vPlayer = null; }
    if (vVideo) { vVideo.pause(); vVideo = null; }
    vStage.innerHTML = '';
    viewer.hidden = true;
    syncAll();
    if (drawer.hidden) return;
    if (window.SkriblModal) window.SkriblModal.close(viewer);
    else if (vFrom) vFrom.focus({ preventScroll: true });
  }
  function openViewer(card) {
    if (!viewer) return;
    var t = card.querySelector('.learn-title');
    var n = t && t.querySelector('.learn-n');
    vTitle.textContent = t ? t.textContent.slice(n ? n.textContent.length : 0).trim() : '';
    vStage.innerHTML = '';
    vStage.removeAttribute('data-shape');
    vFrom = card.querySelector('.learn-stage');
    var vTry = document.getElementById('learnViewerTry'), cTry = card.querySelector('[data-try]');
    if (vTry) {
      vTry.hidden = !cTry;
      if (cTry) { vTry.setAttribute('data-try', cTry.getAttribute('data-try')); vTry.setAttribute('aria-label', cTry.getAttribute('aria-label') || 'Try it'); }
      else vTry.removeAttribute('data-try');
    }
    viewerOpen = true;
    syncAll();
    viewer.hidden = false;
    // A dialog, like the sheet under it: Tab stays in, and closing goes back
    // to the card that opened it.
    if (window.SkriblModal) window.SkriblModal.open(viewer, vFrom);
    var close = document.getElementById('learnViewerClose');
    if (close) close.focus({ preventScroll: true });
    if (card.hasAttribute('data-clip-dark')) {
      var light = document.documentElement.getAttribute('data-theme') === 'light';
      var v = document.createElement('video');
      v.className = 'learn-viewer-video';
      v.muted = true; v.loop = true; v.playsInline = true;
      v.setAttribute('playsinline', '');
      v.setAttribute('poster', card.getAttribute(light ? 'data-poster-light' : 'data-poster-dark'));
      if (card.getAttribute('data-shape')) vStage.setAttribute('data-shape', card.getAttribute('data-shape'));
      vStage.appendChild(v);
      vVideo = v;
      if (reduce) { v.controls = true; v.preload = 'none'; v.setAttribute('src', clipSrc(card)); }
      else { v.setAttribute('src', clipSrc(card)); var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); }
      return;
    }
    vStage.innerHTML = card._learnPristine || '';
    var box = vStage.querySelector('.skribl-inline');
    loadPlayer().then(function () { return start(card); }).then(function () {
      if (!viewerOpen || !box || !card._learnPayload || !window.SkriblInline) return;
      var p = window.SkriblInline.attach(box, card._learnPayload, { ambient: true });
      if (!p) return;
      p.setLoop(true);
      vPlayer = p;
      if (!reduce) p.play();
    });
  }
  all.forEach(function (card) {
    var st = card.querySelector('.learn-stage');
    if (!st) return;
    st.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      openViewer(card);
    }, true);
    st.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openViewer(card); }
    });
  });
  if (viewer) viewer.addEventListener('click', function (e) {
    var t = e.target.closest('[data-try]');
    if (t) { tryTool(t.getAttribute('data-try')); return; }
    if (e.target.closest('[data-viewer-close]')) closeViewer();
  });

  // ---- How it works opening and closing -------------------------------------
  // Every opening starts on Ask's home, at the top.
  // A clip already fetched in one theme is swapped on opening when the theme
  // changed while How it works was shut, which is the only time it can: Theme
  // lives in the menu (owner's phone, dark, after v323: the light clip).
  function onOpenChange() {
    if (!drawer.hidden) { clips.forEach(function (c) { if (c._learnWanted) startClip(c); }); showTab(true); }
    else { closeViewer(); syncAll(); }
  }
  new MutationObserver(onOpenChange).observe(drawer, { attributes: true, attributeFilter: ['hidden'] });
  if (!drawer.hidden) onOpenChange();

  // Try it: How it works closes and the editor holds that tool. The strip's
  // cards are pictures, so it rides with the example full screen.
  function tryTool(tool) {
    closeViewer();
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
  }
  sheet.addEventListener('click', function (e) {
    var b = e.target.closest('[data-try]');
    if (b) tryTool(b.getAttribute('data-try'));
  });

  // Ask (lib/ask.js) switches the views and opens an example full screen.
  window.SkriblHelpLearn = {
    show: show,
    view: function () { return view; },
    watch: function (name) {
      var card = all.filter(function (c) { return (c.getAttribute('data-demo-name') || c.getAttribute('data-clip-name')) === name; })[0];
      if (card) openViewer(card);
      return !!card;
    }
  };
}());
