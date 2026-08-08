/* Canvas presets — the one table both editors read.
 *
 * WHY IT IS SHARED. Flip has had a size picker since v110; Pad had none and
 * called establishEditorCanvas() with whatever the viewport happened to be on
 * first load. A drawing's shape therefore depended on how wide the browser
 * window was, so two people drawing the same thing got different aspect ratios
 * and the same person got different ones on phone and desktop. For a feed that
 * is unworkable — every card a different shape — and it is not something a user
 * chose, so it cannot be defended as a feature.
 *
 * Copying Flip's table into app.js would have made a second copy of a list that
 * has already drifted from its own labels once. This is the copy.
 *
 * DIMENSIONS ARE DERIVED FROM THE RATIO, never typed alongside it. Two of the
 * four used to disagree with their own name: '4:3' was 640x460 (1.391 — off by
 * 4.3%) and '9:16' was 420x640 (0.656 — off by 16.7%, nearer 2:3). Each size is
 * now an integer MULTIPLE of its ratio, so the label is exact by construction
 * rather than by rounding.
 *
 * k targets a common AREA rather than a common long edge. Equal area is what
 * keeps payload size and export time comparable between presets; a constant
 * long edge would make 1:1 78% more pixels than 16:9 for no reason a user
 * could see.
 *
 * Existing drawings are unaffected by any change here — every payload carries
 * its own canvasSize and the player honours it.
 */
(function (global) {
  'use strict';

  var TARGET_PX = 300000;

  function make(id, label, wr, hr) {
    var k = Math.max(1, Math.round(Math.sqrt(TARGET_PX / (wr * hr))));
    return { id: id, label: label, w: wr * k, h: hr * k, wr: wr, hr: hr };
  }

  var SIZES = [
    make('classic', '4:3', 4, 3),
    make('wide', '16:9', 16, 9),
    make('square', '1:1', 1, 1),
    make('tall', '9:16', 9, 16)
  ];

  // A canvas that matches no preset is 'custom', not the nearest one. Every
  // Skribl authored before Pad had a picker is a custom size, and quietly
  // relabelling it as a preset would misreport what it actually is.
  function idFor(w, h) {
    for (var i = 0; i < SIZES.length; i++) {
      if (SIZES[i].w === w && SIZES[i].h === h) return SIZES[i].id;
    }
    return 'custom';
  }

  function byId(id) {
    for (var i = 0; i < SIZES.length; i++) if (SIZES[i].id === id) return SIZES[i];
    return null;
  }

  // The preset closest in SHAPE to an arbitrary canvas. Used only to preselect
  // a sensible entry when a legacy drawing is opened — never to change it.
  function nearest(w, h) {
    if (!w || !h) return SIZES[0];
    var r = w / h, best = SIZES[0], bestErr = Infinity;
    for (var i = 0; i < SIZES.length; i++) {
      var err = Math.abs(Math.log(r / (SIZES[i].w / SIZES[i].h)));
      if (err < bestErr) { bestErr = err; best = SIZES[i]; }
    }
    return best;
  }

  global.SkriblCanvasSizes = {
    SIZES: SIZES,
    DEFAULT: SIZES[0],
    idFor: idFor,
    byId: byId,
    nearest: nearest
  };
})(window);
