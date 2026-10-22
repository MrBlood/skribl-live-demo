/* The glowing dot that rides the tip of a line while it draws itself: its
 * colour, and its picture in a file. One for the Pad and Flip (the owner,
 * after v328: Flip's pages that draw themselves had no dot anywhere, "C,
 * everywhere"), so the two editors' dots cannot drift.
 *
 * rgb(colour) is the ink the dot takes, as "r,g,b" for the sheet's --nib-rgb
 * (.player-nib): a stroke's colour is #rrggbb, #rrggbbaa (a Smear's) or
 * rgb()/rgba() (a see-through pen), and its alpha is dropped, so a faint pen
 * still gets a dot you can see. Anything else is white, as the sheet's default.
 *
 * paint(ctx, point, sx, sy) draws the same dot into a frame of a GIF or a
 * video: the bead and its halo as the stylesheet draws them, 1.9 times the
 * line's width at the file's scale (5 to 90 px), after the drawing so the
 * drawing never holds it. None while erasing: on screen that is a faint
 * hollow ring, not ink. (It was the Pad's exportNib, editor_export.js, until
 * Flip's files needed the same.) */
(function (global) {
  function rgb(color) {
    if (typeof color === 'string') {
      var hex = color.match(/^#([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?$/);
      if (hex) {
        var h = hex[1];
        return parseInt(h.slice(0, 2), 16) + ',' + parseInt(h.slice(2, 4), 16) + ',' + parseInt(h.slice(4, 6), 16);
      }
      var m = color.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
      if (m) return m[1] + ',' + m[2] + ',' + m[3];
    }
    return '255,255,255';
  }

  function paint(ctx, p, sx, sy) {
    if (!p || p.erase) return;
    var nb = Math.max(5, Math.min(90, 1.9 * (p.size || 8) * Math.min(sx, sy)));
    var x = p.x * sx, y = p.y * sy, r = nb / 2, k = nb / 14;
    var c = rgb(p.color);
    var ink = function (a) { return 'rgba(' + c + ',' + a + ')'; };
    ctx.save();
    // The halo: box-shadow 0 0 10px 2px at 0.45 is a disc 2px wider than the
    // bead, blurred by 10, and drawn only outside the bead.
    var out = r + 12 * k;
    var g = ctx.createRadialGradient(x, y, r, x, y, out);
    g.addColorStop(0, ink(0.29)); g.addColorStop(2 / 12, ink(0.22));
    g.addColorStop(7 / 12, ink(0.07)); g.addColorStop(1, ink(0));
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, out, 0, 2 * Math.PI); ctx.arc(x, y, r, 0, 2 * Math.PI, true); ctx.fill();
    // The bead: radial-gradient(circle, ink 0.95 0 30%, 0.25 60%, transparent
    // 70%), whose 100% is its box's farthest corner.
    g = ctx.createRadialGradient(x, y, 0, x, y, nb * Math.SQRT1_2);
    g.addColorStop(0, ink(0.95)); g.addColorStop(0.3, ink(0.95));
    g.addColorStop(0.6, ink(0.25)); g.addColorStop(0.7, ink(0));
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fill();
    ctx.restore();
  }

  global.SkriblNib = { rgb: rgb, paint: paint };
})(window);
