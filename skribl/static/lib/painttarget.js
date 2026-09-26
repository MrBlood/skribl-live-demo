/* The draw drawer's paint-target seg (Pen or Background) and the pills on
 * its segmented rows: wired once for both editors (SK312-003, v315). Both
 * were word-for-word in app.js and flip.js (1.00 by harness/tools/editordup.py).
 *
 * Paint target swaps WHICH swatch grid is shown, not what the sheet shows:
 * size, opacity and brush stay put underneath and never move.
 *
 * Editors only. The player has no drawer, and these leaving app.js take them
 * out of the player's download. Wires itself and exports nothing;
 * currentPaintTarget() in each editor reads the seg's DOM state.
 */
(function () {
  'use strict';

  var seg = document.getElementById('paintTargetSeg');
  if (seg) {
    seg.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-target]');
      if (!btn) return;
      var target = btn.dataset.target;
      seg.querySelectorAll('button').forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', String(on));
      });
      ['colorGroup', 'bgGroup'].forEach(function (id) {
        var g = document.getElementById(id);
        if (g) g.hidden = g.dataset.target !== target;
      });
      // Recent is a list of PEN colours. It sits between the two swatch grids
      // as a sibling, so it stayed on screen in Background mode and read as
      // "recent backgrounds" -- which is what it was reported as. It belongs
      // to the pen. Read the real state rather than inventing a flag:
      // lib/recentcolors.js owns this row's visibility.
      var recent = document.getElementById('recentRow');
      if (recent) {
        var swatches = document.getElementById('recentColors');
        var has = !!(swatches && swatches.children.length);
        recent.hidden = (target !== 'stroke') || !has;
      }
      if (window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
    });
    if (window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  }

  // track() rather than a one-shot place(): the drawer ships `hidden`, so at
  // init the buttons have no layout and any single call bails, leaving the
  // pill at opacity 0 -- the exact bug lib/segslider.js was written for.
  ['smoothSeg', 'brushSeg', 'shapeSeg', 'pressureSeg', 'eraserSeg'].forEach(function (id) {
    var s = document.getElementById(id);
    if (s && window.SkriblSegSlider) window.SkriblSegSlider.track(s);
  });
})();
