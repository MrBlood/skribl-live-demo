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
    });
  }

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
    if (open) window._skriblSyncPadGrid();
  }
  if (tuneBtnEl) tuneBtnEl.addEventListener('click', function () { setPadTune(!padTuneOpen()); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && padTuneOpen()) setPadTune(false);
  });
})();
