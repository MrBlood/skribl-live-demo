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

      var cols = 8, rows = 6;
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

  global.skriblGrid = skriblGrid;
})(window);
