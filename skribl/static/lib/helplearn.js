/* How it works, shown: the examples drawer in the help panel.
 *
 * Every card plays a REAL Skribl -- drawn through the editor with real pen
 * input by harness/tools/make_art.py and make_flip.py -- through the same
 * in-post player that plays posts (inlineplayer.js). So the Eraser card is
 * what the eraser does, and there is no second, simplified renderer to drift
 * from the real one.
 *
 * THE PAGE SHOWS ONE BAR. "Watch it work" (#learnPeek) opens a drawer of
 * every example (#learnSheet), with chips to show one group; the reference
 * below the bar stays where it was. The owner asked for it ("it fills the page
 * and seems like a lot of stuff") with many more examples coming.
 *
 * NOTHING LOADS UNTIL IT IS ASKED FOR. Opening How it works fetches the bar's
 * three small previews; the player, its stylesheet and the examples are
 * fetched the first time the drawer opens. Examples play only while the
 * drawer is open and their card is on screen, silent and looping, all
 * together (the player's ambient mode: an example never stops another, see
 * inlineplayer.js play()). With reduced motion asked for, each card shows its
 * finished drawing and does not play.
 *
 * THE DRAWER CLOSES like every sheet: a tap on its grip or a pull down, the
 * scrim, its close button, or Escape -- which closes the drawer and leaves How
 * it works open. Closing How it works closes it too.
 *
 * TRY IT closes the panel and picks the tool by the editor's own route -- the
 * dock button on Pad, shelfSetTool on Flip, which also open the shape card --
 * so it can never select a tool differently from a tap on the tool itself.
 */
(function () {
  'use strict';
  var box = document.getElementById('helpLearn');
  var drawer = document.getElementById('helpDrawer');
  var sheet = document.getElementById('learnSheet');
  var peek = document.getElementById('learnPeek');
  if (!box || !drawer || !sheet || !peek) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var all = Array.prototype.slice.call(sheet.querySelectorAll('.learn-card'));
  var cards = all.filter(function (c) { return c.hasAttribute('data-demo'); });
  var clips = all.filter(function (c) { return c.hasAttribute('data-clip-dark'); });
  var ready = null;
  var visible = new Set();
  var sheetOpen = false;

  // The bar says how many there are, counted here, never typed.
  var count = document.getElementById('learnPeekCount');
  if (count) count.textContent = all.length + ' short examples';

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
    return card._learnLoad;
  }

  function startAll() {
    clips.forEach(startClip);
    clips.forEach(sync);
    loadPlayer().then(function () { cards.forEach(start); cards.forEach(sync); });
  }
  function syncAll() { cards.forEach(sync); clips.forEach(sync); }

  // ---- the drawer ----------------------------------------------------------
  var panel = sheet.querySelector('.learn-sheet-panel');
  var hideTimer = 0;
  // Reduced motion: the drawer appears and goes without gliding. Set here, not
  // in styles.css, whose reduced-motion blocks the player's stylesheet carries.
  if (reduce) {
    if (panel) panel.style.transition = 'none';
    var scrim = sheet.querySelector('.learn-scrim');
    if (scrim) scrim.style.transition = 'none';
  }
  function openSheet() {
    if (sheetOpen) return;
    clearTimeout(hideTimer);
    sheetOpen = true;
    sheet.hidden = false;
    void sheet.offsetWidth;            // let it lay out closed, then glide up
    sheet.classList.add('open');
    peek.setAttribute('aria-expanded', 'true');
    /* A LAYER OVER A DIALOG IS A DIALOG (outside audit V319-002). This was a
       region, so nothing kept Tab in it and the third press reached How it
       works' own Close underneath. The modal owner traps Tab and remembers
       the way back; focus then goes to the heading, as it always has. */
    if (window.SkriblModal) window.SkriblModal.open(sheet, peek);
    var title = document.getElementById('learnSheetTitle');
    if (title) title.focus({ preventScroll: true });
    startAll();
  }
  function closeSheet(instant) {
    if (!sheetOpen) return;
    sheetOpen = false;
    sheet.classList.remove('open');
    if (panel) panel.style.transform = '';
    peek.setAttribute('aria-expanded', 'false');
    syncAll();
    var done = function () { if (!sheetOpen) sheet.hidden = true; };
    clearTimeout(hideTimer);
    if (instant || reduce) done(); else hideTimer = setTimeout(done, 300);
    if (!drawer.hidden && sheet.contains(document.activeElement)) {
      if (window.SkriblModal) window.SkriblModal.close(sheet);
      else peek.focus({ preventScroll: true });
    }
  }
  peek.addEventListener('click', openSheet);
  sheet.addEventListener('click', function (e) {
    if (e.target.closest('[data-learn-close]') && !dragged) closeSheet();
    dragged = false;
  });
  // Escape closes the drawer and leaves How it works open: caught inside the
  // panel, before the editors' window-level Escape that closes the panel.
  drawer.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (viewerOpen) { e.stopPropagation(); e.preventDefault(); closeViewer(); return; }
    if (sheetOpen) { e.stopPropagation(); e.preventDefault(); closeSheet(); }
  });
  // A pull down on the grip closes it, as every sheet's grabber does.
  var grip = document.getElementById('learnGrip');
  var y0 = null, dy = 0, dragged = false;
  if (grip && panel) {
    grip.addEventListener('pointerdown', function (e) {
      y0 = e.clientY; dy = 0; dragged = false;
      try { grip.setPointerCapture(e.pointerId); } catch (err) {}
    });
    grip.addEventListener('pointermove', function (e) {
      if (y0 == null) return;
      dy = Math.max(0, e.clientY - y0);
      if (dy > 6) { dragged = true; panel.style.transition = 'none'; panel.style.transform = 'translateY(' + dy + 'px)'; }
    });
    var end = function () {
      if (y0 == null) return;
      y0 = null;
      panel.style.transition = '';
      if (dragged && dy > 70) { dragged = false; closeSheet(); }
      else panel.style.transform = '';
    };
    grip.addEventListener('pointerup', end);
    grip.addEventListener('pointercancel', end);
  }

  // Chips show one group, or all.
  sheet.querySelectorAll('.learn-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var f = chip.getAttribute('data-filter');
      sheet.querySelectorAll('.learn-chip').forEach(function (c) { c.setAttribute('aria-pressed', String(c === chip)); });
      all.forEach(function (c) { c.hidden = f !== 'all' && c.getAttribute('data-group') !== f; });
      var sc = sheet.querySelector('.learn-sheet-scroll');
      if (sc) sc.scrollTop = 0;
    });
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
    if (e.target.closest('[data-viewer-close]')) closeViewer();
  });

  // ---- How it works opening and closing -------------------------------------
  function onOpenChange() {
    if (!drawer.hidden) {
      box.querySelectorAll('img[data-src]').forEach(function (im) {
        if (!im.getAttribute('src')) im.setAttribute('src', im.getAttribute('data-src'));
      });
    } else {
      closeViewer();
      closeSheet(true);
    }
    syncAll();
  }
  new MutationObserver(onOpenChange).observe(drawer, { attributes: true, attributeFilter: ['hidden'] });
  if (!drawer.hidden) onOpenChange();

  // While searching, the reference is what answers; the examples step aside.
  var search = document.getElementById('helpSearch');
  if (search) search.addEventListener('input', function () {
    box.hidden = !!search.value.trim();
    if (box.hidden) closeSheet(true);
  });

  sheet.addEventListener('click', function (e) {
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

}());
