/* Pad grid overlay + tune drawer — editor-only wiring (v204).
 *
 * Split out of app.js for the same reason as editor_export/post: the PLAYER
 * loads app.js, and it never shows a grid or a tune drawer, so shipping this
 * wiring to every shared link is pure weight. The STATE these drive (gridOn,
 * _gridCtl) stays in app.js because layoutEditorCanvas() there reads it to keep
 * the overlay on the art during re-fit; this file only wires the controls.
 * Loaded after app.js, so its globals (canvas, gridOn, _gridCtl, _padDrawerCtl,
 * skriblGrid) are all defined.
 */
(function () {
  'use strict';
  var gridOn = false, gridCtl = null;
  var gridBtn = document.getElementById('gridBtn');
  var padGridEl = document.getElementById('padGrid');

  // syncPadGrid binds the shared controller lazily and repaints. Exposed so
  // layoutEditorCanvas() in app.js can call it on re-fit (via window).
  window._skriblSyncPadGrid = function () {
    if (!gridOn) return;                 // called on every re-fit; only paint when on
    if (!gridCtl) {
      if (!padGridEl || typeof skriblGrid !== 'function') return;
      gridCtl = skriblGrid(canvas, padGridEl);
    }
    gridCtl.sync();
  };

  if (gridBtn && padGridEl) {
    gridBtn.addEventListener('click', function () {
      gridOn = !gridOn;
      window._skriblSyncPadGrid();
      gridBtn.classList.toggle('active', gridOn);   // .onion-tint lights via .active
      padGridEl.classList.toggle('on', gridOn);
      gridBtn.setAttribute('aria-checked', String(gridOn));
      if (_renderGridDensity) _renderGridDensity();
    });
  }

  // ---- Stroke layers (v213) -------------------------------------------------
  // The wet/dry compositor was already here and already on: strokeLayersOn() in
  // app.js reads `window.SKRIBL_STROKE_LAYERS !== false`, a global with no
  // control anywhere, so the only way to see the difference was to set it by
  // hand in a console. It is what stops a low-opacity stroke compounding at its
  // own overlaps into dark beads. This row exposes it; the behaviour is
  // unchanged and still defaults ON, because `!== false` means an absent key
  // and an unparsable one both read as on.
  //
  // Read at STROKE START (startDraw sets _slActive once per stroke), so
  // toggling mid-stroke cannot split one stroke across two compositing modes.
  // Grid density — the shared setting in lib/gridoverlay.js. The seg only shows
  // while the grid is ON: a density control for an invisible grid is a control
  // whose effect you cannot see, which is how the onion-depth seg behaves too.
  function _wireGridDensity(isOnFn, repaintFn) {
    var seg = document.getElementById('gridDensitySeg');
    var group = document.getElementById('gridDensityGroup');
    if (!seg || !window.SkriblGrid) return function () {};
    function render() {
      var cur = window.SkriblGrid.density();
      var btns = seg.querySelectorAll('[data-density]');
      for (var i = 0; i < btns.length; i++) {
        btns[i].classList.toggle('on', btns[i].getAttribute('data-density') === cur);
      }
      if (group) group.hidden = !isOnFn();
    }
    seg.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-density]') : null;
      if (!b || !seg.contains(b)) return;
      window.SkriblGrid.setDensity(b.getAttribute('data-density'));
      render();
      repaintFn();
    });
    render();
    return render;
  }

  var _renderGridDensity = _wireGridDensity(
    function () { return gridOn; },
    function () { window._skriblSyncPadGrid(); });

  // Stroke layers — shared setting in lib/strokelayers.js (Flip has the same
  // row). The compositing stays per-surface; only the switch is common.
  if (window.SkriblStrokeLayers) {
    window.SkriblStrokeLayers.create({
      btn: document.getElementById('strokeLayersBtn'),
    });
  }

  // ---- Pause handling (v213) ------------------------------------------------
  // Writes through to app.js's setPauseMode(), which is what serializeSkribl()
  // posts and what the player adopts on load — so this is a property of the
  // DRAWING, not of this browser. The localStorage copy is only a default for
  // the next new drawing; a loaded draft overrides it via loadSkribl().
  var PAUSE_KEY = 'skribl_pause_mode';
  var pauseSeg = document.getElementById('pauseSeg');
  if (pauseSeg && typeof setPauseMode === 'function') {
    var startMode = 'tight';
    try {
      var savedP = localStorage.getItem(PAUSE_KEY);
      if (savedP) startMode = savedP;
    } catch (e) {}
    setPauseMode(startMode);
    var renderPause = function () {
      var cur = (typeof pauseMode !== 'undefined') ? pauseMode : 'tight';
      var btns = pauseSeg.querySelectorAll('[data-pause]');
      for (var i = 0; i < btns.length; i++) {
        btns[i].classList.toggle('on', btns[i].getAttribute('data-pause') === cur);
      }
    };
    renderPause();
    pauseSeg.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-pause]') : null;
      if (!b || !pauseSeg.contains(b)) return;
      setPauseMode(b.getAttribute('data-pause'));
      try { localStorage.setItem(PAUSE_KEY, b.getAttribute('data-pause')); } catch (e2) {}
      renderPause();
      // The duration badge and the music "Plays for ..." label are both derived
      // from the capped total, so they are stale the instant this changes.
      if (typeof updateDrawingTimeLabels === 'function') updateDrawingTimeLabels();
    });
    // A loaded draft carries its own mode; refresh the seg when the drawer opens.
    window._skriblSyncPauseSeg = renderPause;
  }


  // ---- Keyboard shortcuts (v213) --------------------------------------------
  // Pad had FOUR bound keys in total (Ctrl+Z/Y, Enter, Escape) while Flip
  // already answered to p/e for the tools. Same two editors, same tool row, one
  // of them reachable from the keyboard.
  //
  // LETTERS MATCH FLIP'S (p/e), not the b/e most drawing apps use. Consistency
  // between the two surfaces beats consistency with the rest of the world here:
  // this project's recurring bug is one editor having something the other
  // lacks, and inventing a third vocabulary would make the pair worse.
  //
  // NOT registered with lib/keyregistry.js, on purpose: verify_keys asserts the
  // registry is absent from Pad, because Pad shares app.js with the PLAYER and
  // a lib it needed would ship to every shared link. This file is editor-only,
  // so these bindings cost the player nothing.
  function _padTyping(el) {
    if (!el) return false;
    var t = (el.tagName || '').toLowerCase();
    return t === 'input' || t === 'textarea' || t === 'select' || el.isContentEditable;
  }

  function _nudgeBrush(delta) {
    var r = document.getElementById('brushSizeRange');
    if (!r) return;
    var next = Math.max(+r.min, Math.min(+r.max, (+r.value || 0) + delta));
    if (next === +r.value) return;
    r.value = String(next);
    // Dispatch rather than call a handler: the size label, the preview dot and
    // the autosave trigger all hang off this input's own 'input' event, and
    // reaching past them would update the number and none of the rest.
    r.dispatchEvent(new Event('input', { bubbles: true }));
  }

  document.addEventListener('keydown', function (e) {
    if (_padTyping(e.target)) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;   // leave Ctrl+Z and friends alone
    var k = e.key;
    if (k === 'p' || k === 'P') { if (typeof setTool === 'function') setTool('pen'); return; }
    if (k === 'e' || k === 'E') { if (typeof setTool === 'function') setTool('eraser'); return; }
    if (k === '[') { _nudgeBrush(-1); return; }
    if (k === ']') { _nudgeBrush(1); return; }
    if (k === 'g' || k === 'G') { if (gridBtn) gridBtn.click(); return; }
  });

  var tuneBtnEl = document.getElementById('tuneBtn');
  var tuneShellEl = document.getElementById('tuneShell');
  function padTuneOpen() { return !!tuneShellEl && tuneShellEl.classList.contains('open'); }
  function setPadTune(open) {
    if (!tuneBtnEl || !tuneShellEl) return;
    if (open && _padDrawerCtl) _padDrawerCtl.open(null);   // exclusive with media drawers
    tuneShellEl.classList.toggle('open', open);
    tuneShellEl.setAttribute('aria-hidden', String(!open));
    tuneBtnEl.classList.toggle('open', open);
    tuneBtnEl.setAttribute('aria-expanded', String(open));
    if (open) {
      window._skriblSyncPadGrid();
      if (window._skriblSyncPauseSeg) window._skriblSyncPauseSeg();
    }
  }
  if (tuneBtnEl) tuneBtnEl.addEventListener('click', function () { setPadTune(!padTuneOpen()); });
  // v208 (v207 review F4): let app.js close the drawer when recording starts.
  // Recording hides the Tune BUTTON (it is meaningless mid-capture), so a
  // drawer left open would have no visible opener — an expanded panel with no
  // way to see how it got there. beginRecording() calls this first.
  window._skriblClosePadTune = function () { setPadTune(false); };
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && padTuneOpen()) setPadTune(false);
  });
})();
