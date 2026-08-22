/* Grid overlay — the alignment guides both editors draw over the canvas.
 *
 * Extracted verbatim from Flip's syncGrid/drawGrid (v204, when Grid moved into
 * the tune drawer and Pad gained it too). The maths is unchanged — every line
 * on an exact device pixel via fillRect, closing edges drawn explicitly, no
 * fractional gradient stops — because that is what made the grid stop looking
 * doubled/off-centre in the first place. The only change is that the canvas
 * and its overlay are parameters now, not the module-global `pad`/`#flipGrid`.
 *
 * skriblGrid(canvasEl, overlayEl) -> { sync() }
 *   canvasEl  - the drawing canvas the grid must cover edge to edge
 *   overlayEl - the (separate) canvas the grid paints onto
 *   sync()    - reposition + repaint; call on show, resize, and zoom change.
 *
 * Cells are 8x6 majors with half-subdivisions, sized to the canvas's rendered
 * box (offsetWidth/Height minus its real border), so the guides land on the
 * art regardless of how the flex wrapper sizes.
 */
(function (global) {
  'use strict';

  /* Density — how many major cells along the canvas's LONGER edge. `medium`
   * is 8, which reproduces the historical 8x6 exactly on a 4:3 canvas, so
   * turning the grid on looks the same as it always did until you change it.
   */
  var KEY = 'skribl_grid_density';
  var DENSITY = { fine: 12, medium: 8, coarse: 5 };
  var density = 'medium';
  try {
    var savedD = localStorage.getItem(KEY);
    if (Object.prototype.hasOwnProperty.call(DENSITY, savedD)) density = savedD;
  } catch (e) {}

  function skriblGrid(canvasEl, overlayEl) {
    if (!canvasEl || !overlayEl) return { sync: function () {} };

    function draw(w, h) {
      var dpr = Math.max(1, Math.min(3, global.devicePixelRatio || 1));
      var W = Math.round(w * dpr), H = Math.round(h * dpr);
      if (!W || !H) return;
      if (overlayEl.width !== W || overlayEl.height !== H) {
        overlayEl.width = W; overlayEl.height = H;
      }
      var c = overlayEl.getContext('2d');
      c.clearRect(0, 0, W, H);

      // CELL COUNT IS DERIVED FROM THE CANVAS ASPECT, not fixed.
      // This was `cols = 8, rows = 6` — which is 4:3, so the cells were square
      // ONLY on the `classic` preset. On `tall` (9:16) an 8x6 grid draws cells
      // about 2.4x taller than wide, which is not an alignment guide so much as
      // a distortion of one. `majors` is the count along the LONGER edge and the
      // shorter edge is scaled from the real pixel box, so cells stay square at
      // every preset. At the default density on classic this still resolves to
      // exactly 8x6, so the shipped grid is unchanged where it was already right.
      var majors = api.majors();
      var cols, rows;
      if (W >= H) { cols = majors; rows = Math.max(1, Math.round(majors * H / W)); }
      else        { rows = majors; cols = Math.max(1, Math.round(majors * W / H)); }
      var line = Math.max(1, Math.round(dpr));   // whole device pixels only

      // Sub-cells first so the majors sit on top of them.
      paint(cols * 2, rows * 2, 'rgba(255,255,255,.10)');
      paint(cols, rows, 'rgba(255,255,255,.26)');

      function paint(nx, ny, colour) {
        c.fillStyle = colour;
        // Distribute across (W - line), not W, so the closing line lands at
        // W - line by construction and every gap is equal to within rounding
        // — clamping only the last line inward stole width from one cell.
        var spanX = Math.max(1, W - line), spanY = Math.max(1, H - line);
        for (var i = 0; i <= nx; i++) c.fillRect(Math.round(i * spanX / nx), 0, line, H);
        for (var j = 0; j <= ny; j++) c.fillRect(0, Math.round(j * spanY / ny), W, line);
      }
    }

    function sync() {
      // Read the border rather than assume it — hard-coding it is what put the
      // grid a pixel off when the canvas border changed width.
      var b = parseFloat(getComputedStyle(canvasEl).borderTopWidth) || 0;
      var w = Math.max(0, canvasEl.offsetWidth - 2 * b);
      var h = Math.max(0, canvasEl.offsetHeight - 2 * b);
      overlayEl.style.left = (canvasEl.offsetLeft + b) + 'px';
      overlayEl.style.top = (canvasEl.offsetTop + b) + 'px';
      overlayEl.style.width = w + 'px';
      overlayEl.style.height = h + 'px';
      draw(w, h);
    }

    return { sync: sync };
  }

  /* The density is module state, not per-instance: both editors show one grid
   * at a time and the setting is a user preference, so an instance-local copy
   * would be a second place for it to live. setDensity() returns the applied
   * value so a caller can tell a rejected value from an accepted one.
   */
  var api = {
    DENSITIES: Object.keys(DENSITY),
    majors: function () { return DENSITY[density]; },
    density: function () { return density; },
    setDensity: function (name) {
      if (!Object.prototype.hasOwnProperty.call(DENSITY, name)) return density;
      density = name;
      try { localStorage.setItem(KEY, density); } catch (e) {}
      return density;
    }
  };

  global.skriblGrid = skriblGrid;
  global.SkriblGrid = api;
})(window);
