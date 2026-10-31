/* Recolor: a line already drawn takes a new colour (the owner, of the mock:
 * "I love the recolor too", every choice yes). ONE module for both editors:
 * the hit-test, the colour rule, the run of colour along the line, and the
 * bar the mode wears. What a change DOES to a drawing stays with each editor
 * (the Pad's undo stack and its replay's record of the moment; Flip's page
 * and its action log), so `begin`, `apply` and `end` are injected.
 *
 * THE MODE. Recolor sits in the colour drawer beside the eyedropper, its
 * mirror: the eyedropper takes a colour FROM the drawing, this gives one TO
 * it. Tapping it closes the drawer, and the bar under the canvas (the dock's
 * row, which it takes while the mode is on, the way Flip's Select bar takes
 * the page bar's) says what to do beside the colour, with Undo and Done.
 * Nothing sits on the drawing being tapped. The colour is the pen's: its dot
 * opens the drawer to change it, and a pick there closes the drawer again,
 * because the next thing wanted is the drawing.
 *
 * A LINE is one movement of the pen, the group the editors already keep, so a
 * tap takes a whole line and never half of one. A Flip fill is many groups
 * (one per band, lib/floodfill.js) laid in one tap; its bands are read as one
 * line (lineOf), or a tap on a fill would recolour one stripe of it. An
 * eraser's line is not a line of ink and is never hit.
 *
 * A TAP recolours the line under it; a DRAG recolours each line it crosses,
 * once. Either is one step of the editor's undo. Nothing changes on the press
 * itself: a tap takes effect as it lifts and a drag once it has travelled
 * SLOP, so the first finger of a pinch recolours nothing.
 *
 * THE COLOUR RUNS ALONG THE LINE from the finger (RUN ms, both ends at once),
 * drawn on a canvas of its own laid over the drawing: the editor repaints the
 * drawing once with the new colour, and the overlay shows the drawing as it
 * was across the part of the line the colour has not reached yet, shrinking
 * to nothing. The editor's canvas is never painted by this file, so nothing
 * it paints meanwhile can be painted over, and the overlay holds the artwork
 * (lib/artwork.js: backdrop, photo and ink), so a see-through line shows its
 * old colour exactly. Under Reduce Motion the colour simply changes.
 *
 * THE COLOUR KEEPS THE LINE'S OWN OPACITY (tint): a marker line stays a
 * marker line in the new colour, in whichever form its colour was written.
 *
 * AIMING AT A THIN LINE (the owner: "the recolor should have the same
 * magnifier as color picker, but just so you can pick the stroke"; the lens
 * mock, "All yes"). A finger hides a 2px whisker and its neighbours, so a
 * finger that HOLDS STILL (HOLD ms, within SLOP) brings up a lens just above
 * it: the drawing at ZOOM times, from the same composited picture the run
 * draws from, the line under the finger LIT, a small ring on the point, and
 * the eyedropper's split ring saying before and after (the line's colour now
 * above, the pen's below). Sliding chooses another line; lifting gives the
 * lit line the colour; a second finger, or a cancel, changes nothing. Near
 * the top of the screen the lens stands beside the finger instead. A quick
 * tap and a drag that moves at once are what they always were. With a mouse
 * or a pen that hovers, nothing hides the line, so there is no lens: the
 * line the pointer would catch lights up as it moves (the same light). It
 * goes by what is pointing, not by the device. The eyedropper keeps its own
 * 10x lens; this one shows lines, not pixels (at 10x a whisker is one row of
 * cells, and which whisker is unknowable).
 *
 * THE BAR HAS REDO BESIDE UNDO (the owner, with the lens): both press the
 * editor's own, and each is off when the editor's is.
 */
(function () {
  'use strict';

  var RUN = 380;      // ms for a new colour to run the length of a line (lib/recolorplay.js RUN)
  var SLOP = 8;       // CSS px a press travels before it is a drag
  var SLACK = 10;     // CSS px of finger around a line that still hits it
  var STEP = 4;       // CSS px between the hit-tests along a drag
  var HOLD = 330;     // ms a finger stays within SLOP before the lens comes up
  var ZOOM = 3;       // the lens shows the drawing this many times larger
  var LENS_R = 53, RING_W = 5.5;   // its window and split ring (the eyedropper's sizes)
  var TIP = 22, GAP = 14;          // a fingertip's radius, and the lens's clearance above it (CSS px)
  var MARGIN = 6;                  // the lens keeps this far from the viewport's edge
  var GLOW = 'rgba(124, 92, 255, 0.34)';   // the light, over the artwork: theme-free, as the lenses are

  /* ---- colour ------------------------------------------------------------ */

  /* `hex` in the form and at the opacity of `old` (lib/recolorplay.js tint,
     the one rule: every replay recolours a line by it too). */
  function tint(old, hex) { return window.SkriblRecolorPlay.tint(old, hex); }

  /* ---- lines ------------------------------------------------------------- */

  /* What the hit-test reads, built once a gesture: where each group starts and
     the box it covers, widened by its widest point. */
  function index(pts, groups) {
    var st = [0], box = [], at = 0;
    for (var g = 0; g < groups.length; g++) {
      var n = groups[g] | 0, x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, w = 0;
      for (var i = at; i < at + n && i < pts.length; i++) {
        var p = pts[i];
        if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x;
        if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y;
        if ((p.size || 0) > w) w = p.size || 0;
      }
      at += n;
      st.push(at);
      box.push(n ? [x0 - w / 2, y0 - w / 2, x1 + w / 2, y1 + w / 2] : null);
    }
    return { pts: pts, st: st, box: box };
  }

  /* The line under (x, y), in drawing units: the topmost whose ink covers it,
     else the nearest within `slack`. Returns { g, i }: the group and the
     point the colour runs from. */
  function hit(ix, x, y, slack) {
    var pts = ix.pts, st = ix.st, top = null, near = null, nearD = Infinity;
    for (var g = 0; g + 1 < st.length; g++) {
      var a = st[g], b = Math.min(st[g + 1], pts.length), bx = ix.box[g];
      if (b <= a || !bx || pts[a].erase) continue;
      if (x < bx[0] - slack || x > bx[2] + slack || y < bx[1] - slack || y > bx[3] + slack) continue;
      var best = Infinity, at = a;
      if (b - a === 1) {
        best = Math.hypot(pts[a].x - x, pts[a].y - y) - (pts[a].size || 1) / 2;
      } else {
        for (var i = a; i + 1 < b; i++) {
          var p = pts[i], q = pts[i + 1], dx = q.x - p.x, dy = q.y - p.y, L = dx * dx + dy * dy, t = 0;
          if (L > 0) { t = ((x - p.x) * dx + (y - p.y) * dy) / L; t = t < 0 ? 0 : t > 1 ? 1 : t; }
          var ex = p.x + t * dx - x, ey = p.y + t * dy - y;
          var d = Math.sqrt(ex * ex + ey * ey) - Math.max(p.size || 1, q.size || 1) / 2;
          if (d < best) { best = d; at = t < 0.5 ? i : i + 1; }
        }
      }
      if (best <= 0) top = { g: g, i: at };                 // later groups lie on top
      else if (best <= slack && best < nearD) { nearD = best; near = { g: g, i: at }; }
    }
    return top || near;
  }

  /* A fill's bands are one line: each a level run (lib/floodfill.js), the
     next starting a millisecond after the last ended (flip.js doFill stamps
     them that way), in one colour. Returns [first, last] group. */
  function level(ix, g) {
    var pts = ix.pts, a = ix.st[g], b = ix.st[g + 1];
    for (var i = a + 1; i < b; i++) if (Math.abs(pts[i].y - pts[a].y) > 0.01) return false;
    return b > a;
  }
  function joined(ix, g) {           // does group g + 1 continue group g's fill?
    var pts = ix.pts, z = pts[ix.st[g + 1] - 1], f = pts[ix.st[g + 1]];
    return !!z && !!f && z.color === f.color && Math.abs((f.t - z.t) - 1) < 0.01 && level(ix, g) && level(ix, g + 1);
  }
  function lineOf(ix, g) {
    var g0 = g, g1 = g, last = ix.st.length - 2;
    while (g0 > 0 && joined(ix, g0 - 1)) g0--;
    while (g1 < last && joined(ix, g1)) g1++;
    return [g0, g1];
  }

  /* ---- the run ----------------------------------------------------------- */

  /* opts: canvas (the editor's drawing canvas), art() (lib/artwork.js's stage
     for it, at its backing size), unit() (backing px per drawing unit). */
  function runner(opts) {
    var cv = null, before = null, runs = [], raf = 0;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function layer() {
      var c = opts.canvas;
      if (!cv) {
        cv = document.createElement('canvas');
        cv.className = 'recolor-run';
        cv.setAttribute('aria-hidden', 'true');
      }
      if (cv.parentNode !== c.parentNode) c.parentNode.insertBefore(cv, c.nextSibling);
      // Where the grid overlay goes (lib/gridoverlay.js): the canvas's own
      // box inside its border, in the parent the zoom transforms.
      var b = parseFloat(getComputedStyle(c).borderTopWidth) || 0;
      var s = cv.style;
      s.left = (c.offsetLeft + b) + 'px';
      s.top = (c.offsetTop + b) + 'px';
      s.width = Math.max(0, c.offsetWidth - 2 * b) + 'px';
      s.height = Math.max(0, c.offsetHeight - 2 * b) + 'px';
      if (cv.width !== c.width || cv.height !== c.height) { cv.width = c.width; cv.height = c.height; }
      return cv;
    }

    /* The drawing as it is now, before a change: called before the editor
       applies one. Kept while any run is going, so a line hit mid-run is
       still shown as it was. */
    function hold() {
      if (reduce || before) return;
      try {
        var a = opts.art();
        before = document.createElement('canvas');
        before.width = a.width; before.height = a.height;
        before.getContext('2d').drawImage(a, 0, 0);
      } catch (e) { before = null; }
    }

    /* A run along the points of one line, its colour starting at point
       `at`: lib/recolorplay.js reads the line by arc length, so the colour
       moves at an even pace however the points were spaced, and draws the
       part not reached the way every replay draws it. */
    function add(pts, at) {
      if (reduce || !before || !pts.length) return;
      var r = window.SkriblRecolorPlay.line(pts, at);
      r.t0 = performance.now();
      runs.push(r);
      if (!raf) raf = requestAnimationFrame(tick);
    }

    function tick(now) {
      raf = 0;
      runs = runs.filter(function (r) { return now - r.t0 < RUN; });
      var c = cv && cv.getContext('2d');
      if (!runs.length || !before) { stop(); return; }
      layer();
      c = cv.getContext('2d');
      var k = opts.unit();
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.globalCompositeOperation = 'source-over';
      c.clearRect(0, 0, cv.width, cv.height);
      c.setTransform(k, 0, 0, k, 0, 0);
      runs.forEach(function (r) {
        window.SkriblRecolorPlay.unreached(c, [r], Math.min(1, (now - r.t0) / RUN), 1 / k);
      });
      // What was there, inside the part the colour has not reached.
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.globalCompositeOperation = 'source-in';
      c.drawImage(before, 0, 0, cv.width, cv.height);
      c.globalCompositeOperation = 'source-over';
      raf = requestAnimationFrame(tick);
    }

    /* Every run ends where it is going: the editor's drawing already shows
       it. For anything that changes the drawing under a run. */
    function stop() {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      runs = [];
      before = null;
      if (cv) {
        cv.getContext('2d').clearRect(0, 0, cv.width, cv.height);
        if (cv.parentNode) cv.parentNode.removeChild(cv);
      }
    }

    return { hold: hold, add: add, stop: stop, running: function () { return runs.length > 0; } };
  }

  /* ---- the mode ---------------------------------------------------------- */

  var UNDO_SVG = '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-1"/></svg>';
  var REDO_SVG = '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h1"/></svg>';

  function nameOf(hex) {
    var P = window.SkriblPalette && window.SkriblPalette.PEN;
    if (P) for (var i = 0; i < P.length; i++) if (P[i].hex.toLowerCase() === String(hex).toLowerCase()) return P[i].name;
    return String(hex).toUpperCase();
  }

  /* opts:
       button       the drawer's Recolor button
       dock         the dock whose row the bar takes
       surface      the drawing canvas
       color()      the pen's colour, '#rrggbb'
       lines()      { pts, groups } of the drawing (the page, on Flip)
       point(ev)    a pointer event in drawing units
       unit()       backing px per drawing unit
       art()        lib/artwork.js's stage of the drawing
       begin()      before the first change of a gesture (the undo step)
       apply(g0, g1, color, at)  give groups g0..g1 `color` (tinted), the run
                    starting at point `at`; true if anything changed
       repaint()    paint the drawing as it now is
       end()        after the last change of a gesture
       undoButton   the editor's Undo: the bar's presses it, and is off with it
       redoButton   the editor's Redo, the same way
       openColors()/colorsOpen()/closeColors()  the colour drawer
       focusHome()  where focus goes if what armed the mode has gone
       onChange(on) after the mode turns on or off */
  function create(o) {
    var armed = false, session = null, ix = null, bar = null, live = null, back = null, shown = null;
    var run = runner({ canvas: o.surface, art: o.art, unit: o.unit });
    var touchFirst = !!(window.matchMedia && window.matchMedia('(hover: none)').matches);
    var hix = null, hoverAt = null, hoverRaf = 0;          // the hover's lines, and where the pointer is
    var lightCv = null, lit = null, lens = null;
    var lightMask = document.createElement('canvas'), lensMask = document.createElement('canvas');

    // Drawing units a CSS pixel, for the finger's slack: the canvas is shown
    // fitted, zoomed or both.
    function perCss() {
      var r = o.surface.getBoundingClientRect();
      return r.width ? (o.surface.width / (o.unit() || 1)) / r.width : 1;
    }

    /* ---- the light: the line a press would take, lit ---- */

    // Laid over the drawing as the run's canvas is (and with it, in the
    // parent the zoom transforms), at the drawing's backing size.
    function lightLayer() {
      var c = o.surface;
      if (!lightCv) {
        lightCv = document.createElement('canvas');
        lightCv.className = 'recolor-light';
        lightCv.setAttribute('aria-hidden', 'true');
      }
      if (lightCv.parentNode !== c.parentNode) c.parentNode.insertBefore(lightCv, c.nextSibling);
      var b = parseFloat(getComputedStyle(c).borderTopWidth) || 0, s = lightCv.style;
      s.left = (c.offsetLeft + b) + 'px';
      s.top = (c.offsetTop + b) + 'px';
      s.width = Math.max(0, c.offsetWidth - 2 * b) + 'px';
      s.height = Math.max(0, c.offsetHeight - 2 * b) + 'px';
      if (lightCv.width !== c.width || lightCv.height !== c.height) { lightCv.width = c.width; lightCv.height = c.height; }
      return lightCv;
    }
    // Groups g0..g1 with `extra` drawing units round them. The line's own
    // footprint (`each`) goes segment by segment at each point's width, which
    // only an opaque mask may do; a see-through light is one path a group at
    // its widest, or every joint where two segments overlap shows as a bead.
    function strokeLine(x, L, g0, g1, extra, colour, each) {
      x.strokeStyle = x.fillStyle = colour;
      for (var g = g0; g <= g1; g++) {
        var a = L.st[g], z = Math.min(L.st[g + 1], L.pts.length), w = 0, i;
        if (z - a === 1) {
          var p0 = L.pts[a];
          x.beginPath(); x.arc(p0.x, p0.y, ((p0.size || 1) + extra) / 2, 0, 2 * Math.PI); x.fill();
          continue;
        }
        if (each) {
          for (i = a; i + 1 < z; i++) {
            var p = L.pts[i], q = L.pts[i + 1];
            x.beginPath(); x.moveTo(p.x, p.y); x.lineTo(q.x, q.y);
            x.lineWidth = Math.max(p.size || 1, q.size || 1) + extra;
            x.stroke();
          }
          continue;
        }
        x.beginPath();
        for (i = a; i < z; i++) {
          var r = L.pts[i];
          if (i === a) x.moveTo(r.x, r.y); else x.lineTo(r.x, r.y);
          if ((r.size || 1) > w) w = r.size || 1;
        }
        x.lineWidth = w + extra;
        x.stroke();
      }
    }
    // The light round a line, then the line over it as the screen shows it
    // (its footprint cut from `art`, drawn with the same transform `t`):
    // on the drawing's own layer, and again inside the lens at its size.
    // `u` is drawing units a CSS pixel of the place it is drawn.
    function lightUp(x, L, line, u, art, t, maskCv) {
      x.save();
      x.setTransform(t[0], 0, 0, t[0], t[1], t[2]);
      x.lineCap = x.lineJoin = 'round';
      strokeLine(x, L, line[0], line[1], 14 * u, GLOW);
      strokeLine(x, L, line[0], line[1], 5 * u, 'rgba(255, 255, 255, 0.9)');
      x.restore();
      if (!art) return;
      if (maskCv.width !== x.canvas.width || maskCv.height !== x.canvas.height) { maskCv.width = x.canvas.width; maskCv.height = x.canvas.height; }
      var m = maskCv.getContext('2d');
      m.setTransform(1, 0, 0, 1, 0, 0);
      m.globalCompositeOperation = 'source-over';
      m.clearRect(0, 0, maskCv.width, maskCv.height);
      m.setTransform(t[0], 0, 0, t[0], t[1], t[2]);
      m.lineCap = m.lineJoin = 'round';
      strokeLine(m, L, line[0], line[1], 0, '#000', true);
      m.setTransform(1, 0, 0, 1, 0, 0);
      m.globalCompositeOperation = 'source-in';
      art(m);
      m.globalCompositeOperation = 'source-over';
      x.save();
      x.setTransform(1, 0, 0, 1, 0, 0);
      x.drawImage(maskCv, 0, 0);
      x.restore();
    }
    /* Light `line` ([g0, g1] of L), or none. A glow and a white rim round
       it, and the line itself over them AS THE SCREEN SHOWS IT: its
       footprint filled from the composited picture, so a part rubbed out
       stays rubbed out and a line crossing it stays on top. */
    function light(line, L) {
      if (line && lit && line[0] === lit[0] && line[1] === lit[1]) return;
      lit = line ? [line[0], line[1]] : null;
      if (!line) {
        if (lightCv) {
          lightCv.getContext('2d').clearRect(0, 0, lightCv.width, lightCv.height);
          if (lightCv.parentNode) lightCv.parentNode.removeChild(lightCv);
        }
        return;
      }
      var cv = lightLayer(), x = cv.getContext('2d');
      x.setTransform(1, 0, 0, 1, 0, 0);
      x.clearRect(0, 0, cv.width, cv.height);
      lightUp(x, L, line, perCss(), function (m) {
        try { var a = o.art(); m.drawImage(a, 0, 0, m.canvas.width, m.canvas.height); } catch (e) {}
      }, [o.unit(), 0, 0], lightMask);
    }

    /* ---- the lens: hold still to aim ---- */

    // The drawing's own box on the page (inside its border), as shown.
    function shownBox() {
      var c = o.surface, r = c.getBoundingClientRect(), b = parseFloat(getComputedStyle(c).borderTopWidth) || 0;
      var s = c.offsetWidth ? r.width / c.offsetWidth : 1;
      return { left: r.left + b * s, top: r.top + b * s, width: r.width - 2 * b * s, height: r.height - 2 * b * s };
    }
    // Part of `img` into the lens. A source rect partly off the picture is
    // cut to it, and the destination with it: Safari draws nothing at all
    // for a source rect that reaches past an image's edge.
    function blit(x, img, sx, sy, sw, sh, dx, dy, dw, dh) {
      if (!img || !img.width) return;
      var kx = dw / sw, ky = dh / sh;
      var x0 = Math.max(0, sx), y0 = Math.max(0, sy), x1 = Math.min(img.width, sx + sw), y1 = Math.min(img.height, sy + sh);
      if (x1 <= x0 || y1 <= y0) return;
      x.drawImage(img, x0, y0, x1 - x0, y1 - y0, dx + (x0 - sx) * kx, dy + (y0 - sy) * ky, (x1 - x0) * kx, (y1 - y0) * ky);
    }
    // Where the lens stands for a finger at (fx, fy): above it, clear of the
    // fingertip; near the top of the screen, beside it. Its centre.
    function lensAt(fx, fy) {
      var reach = LENS_R + RING_W, off = reach + TIP + GAP;
      var W = window.innerWidth, H = window.innerHeight;
      var cx = Math.max(reach + MARGIN, Math.min(W - reach - MARGIN, fx)), cy = fy - off;
      if (cy - reach < MARGIN) {
        cy = Math.max(reach + MARGIN, Math.min(H - reach - MARGIN, fy));
        cx = fx + off + reach <= W - MARGIN ? fx + off : fx - off;
      }
      return { x: cx, y: cy };
    }
    function hideLens() { if (lens) lens.hidden = true; }
    function drawLens(p, h, art) {
      if (!lens) {
        lens = el('div', 'recolor-lens');
        lens.setAttribute('aria-hidden', 'true');
        lens._cv = el('canvas', '', lens);
        document.body.appendChild(lens);
      }
      var reach = LENS_R + RING_W, D = 2 * reach + 2, c0 = D / 2, at = lensAt(p.cx, p.cy);
      var dpr = window.devicePixelRatio || 1, cv = lens._cv, n = Math.round(D * dpr);
      lens.hidden = false;
      lens.style.left = (at.x - c0) + 'px';
      lens.style.top = (at.y - c0) + 'px';
      lens.style.width = lens.style.height = D + 'px';
      if (cv.width !== n) { cv.width = n; cv.height = n; }
      var x = cv.getContext('2d');
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.clearRect(0, 0, D, D);
      x.save();
      x.beginPath(); x.arc(c0, c0, LENS_R, 0, 2 * Math.PI); x.clip();
      x.fillStyle = 'rgb(128, 128, 128)';
      x.fillRect(0, 0, D, D);
      // The drawing round the point, ZOOM times larger, the light over it.
      var B = shownBox(), bx = o.surface.width / (B.width || 1), by = o.surface.height / (B.height || 1), half = LENS_R / ZOOM;
      var sx = (p.cx - B.left - half) * bx, sy = (p.cy - B.top - half) * by, sw = 2 * half * bx, sh = 2 * half * by;
      blit(x, art, sx, sy, sw, sh, c0 - LENS_R, c0 - LENS_R, 2 * LENS_R, 2 * LENS_R);
      // The light at the lens's own size (its glow as wide here as on the
      // drawing), the drawing's units ZOOM times larger round the point.
      if (lit && ix) {
        var k = ZOOM / perCss();
        lightUp(x, ix, lit, perCss() / ZOOM, function (m) {
          m.setTransform(dpr, 0, 0, dpr, 0, 0);
          blit(m, art, sx, sy, sw, sh, c0 - LENS_R, c0 - LENS_R, 2 * LENS_R, 2 * LENS_R);
        }, [dpr * k, dpr * (c0 - p.x * k), dpr * (c0 - p.y * k)], lensMask);
      }
      x.restore();
      // The point the finger is on: a small ring, light over dark.
      x.lineWidth = 2.5; x.strokeStyle = 'rgba(255, 255, 255, 0.95)';
      x.beginPath(); x.arc(c0, c0, 7, 0, 2 * Math.PI); x.stroke();
      x.lineWidth = 1.2; x.strokeStyle = 'rgba(31, 27, 46, 0.9)';
      x.beginPath(); x.arc(c0, c0, 7, 0, 2 * Math.PI); x.stroke();
      // Before and after: the line's colour now above, the pen's below (no
      // line, a quiet grey above).
      var now = h && ix && ix.pts[h.i] ? ix.pts[h.i].color : 'rgb(150, 150, 150)';
      x.lineWidth = RING_W;
      x.strokeStyle = now;
      x.beginPath(); x.arc(c0, c0, LENS_R + RING_W / 2, Math.PI, 2 * Math.PI); x.stroke();
      x.strokeStyle = (o.color && o.color()) || '#7c5cff';
      x.beginPath(); x.arc(c0, c0, LENS_R + RING_W / 2, 0, Math.PI); x.stroke();
      x.lineWidth = 1; x.strokeStyle = 'rgba(0, 0, 0, 0.22)';
      x.beginPath(); x.arc(c0, c0, LENS_R + RING_W + 0.5, 0, 2 * Math.PI); x.stroke();
    }

    /* ---- the hover: a mouse, or a pen that hovers, lights what it would take ---- */
    function hover(e) {
      if (!armed || session || e.pointerType === 'touch' || e.buttons) return;
      hoverAt = where(e);
      if (!hoverRaf) hoverRaf = requestAnimationFrame(hoverTick);
    }
    function hoverTick() {
      hoverRaf = 0;
      if (!armed || session || !hoverAt) return;
      if (!hix) { var L = o.lines(); hix = index(L.pts || [], L.groups || []); }
      var h = hit(hix, hoverAt.x, hoverAt.y, SLACK * perCss());
      light(h ? lineOf(hix, h.g) : null, hix);
    }
    function unhover() {
      hoverAt = null;
      if (hoverRaf) { cancelAnimationFrame(hoverRaf); hoverRaf = 0; }
      if (!session) light(null);
    }
    if (o.surface) {
      o.surface.addEventListener('pointermove', hover);
      o.surface.addEventListener('pointerleave', unhover);
    }

    function el(tag, cls, parent) {
      var e = document.createElement(tag);
      if (cls) e.className = cls;
      if (parent) parent.appendChild(e);
      return e;
    }
    function build() {
      if (bar) return bar;
      bar = el('div', 'recolor-bar');
      bar.setAttribute('role', 'toolbar');
      bar.setAttribute('aria-label', 'Recolor');
      // Out of reach while the mode is off; shown and hidden by the dock's
      // class (styles.css), so it can fade rather than appear.
      bar.inert = true;
      var swatch = el('button', 'recolor-swatch', bar);
      swatch.type = 'button';
      el('span', 'recolor-dot', swatch);
      var say = el('span', 'recolor-say', bar);
      say.textContent = touchFirst ? 'Tap a line, or hold to aim' : 'Tap a line to recolor';
      var undo = el('button', 'recolor-undo', bar);
      undo.type = 'button';
      undo.title = 'Undo';
      undo.setAttribute('aria-label', 'Undo');
      undo.innerHTML = UNDO_SVG;
      var redo = el('button', 'recolor-redo', bar);
      redo.type = 'button';
      redo.title = 'Redo';
      redo.setAttribute('aria-label', 'Redo');
      redo.innerHTML = REDO_SVG;
      var done = el('button', 'recolor-done', bar);
      done.type = 'button';
      done.textContent = 'Done';
      swatch.addEventListener('click', function (e) {
        e.stopPropagation();
        if (o.colorsOpen && o.colorsOpen()) { if (o.closeColors) o.closeColors(); }
        else if (o.openColors) o.openColors();
      });
      undo.addEventListener('click', function (e) {
        e.stopPropagation();
        run.stop();
        if (o.undoButton && !o.undoButton.disabled) o.undoButton.click();
      });
      redo.addEventListener('click', function (e) {
        e.stopPropagation();
        run.stop();
        if (o.redoButton && !o.redoButton.disabled) o.redoButton.click();
      });
      // The editor's Undo and Redo say when there is nothing to take back or
      // put back, from every path that changes them (a key included); these
      // follow.
      if (window.MutationObserver) {
        [o.undoButton, o.redoButton].forEach(function (btn) {
          if (btn) new MutationObserver(sync).observe(btn, { attributes: true, attributeFilter: ['disabled'] });
        });
      }
      done.addEventListener('click', function (e) { e.stopPropagation(); disarm(); });
      live = el('div', 'vis-hidden', bar);
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      (o.dock || document.body).appendChild(bar);
      bar._swatch = swatch; bar._dot = swatch.firstChild; bar._undo = undo; bar._redo = redo; bar._done = done;
      return bar;
    }
    function say(text) {
      if (!live) return;
      live.textContent = '';
      setTimeout(function () { if (live) live.textContent = text; }, 60);
    }

    /* The bar's colour and Undo, as they are now. A colour picked while the
       mode is on closes the drawer: the next thing wanted is the drawing. The
       editors call this from the one place every colour change passes (the
       pen's swoosh).
       THE MODE'S CROSSHAIR IS THE STYLESHEETS' (body.recoloring, styles.css
       and flip.css), not written here: a colour pick also sets the pen's own
       cursor inline, 'none' on Flip for the ring the mode puts away, and Flip
       set it after this did, so the pointer vanished over the canvas "as soon
       as I change the color" (the owner). A rule over the inline cursor
       cannot lose to the order things are called in. */
    function sync() {
      inkButton((o.color && o.color()) || '#7c5cff');
      if (!bar) return;
      var hex = (o.color && o.color()) || '#7c5cff';
      bar._dot.style.background = hex;
      bar._swatch.setAttribute('aria-label', 'Color: ' + nameOf(hex) + '. Change it');
      bar._swatch.title = 'Change the color';
      bar._undo.disabled = !o.undoButton || !!o.undoButton.disabled;
      bar._redo.disabled = !o.redoButton || !!o.redoButton.disabled;
      if (armed && shown && shown !== hex && o.colorsOpen && o.colorsOpen() && o.closeColors) o.closeColors();
      shown = hex;
    }

    function setArmed(v) {
      v = !!v;
      if (v === armed) return;
      armed = v;
      if (session) end(false);
      run.stop();
      hix = null;
      unhover();
      hideLens();
      build();
      if (o.button) {
        o.button.classList.toggle('picking', armed);
        o.button.setAttribute('aria-pressed', armed ? 'true' : 'false');
      }
      if (o.dock) o.dock.classList.toggle('is-recoloring', armed);
      document.body.classList.toggle('recoloring', armed);
      bar.inert = !armed;
      // The editor first (it closes the drawer and holds the pen; off, it puts
      // its tool's cursor back), then the bar.
      if (o.onChange) o.onChange(armed);
      shown = null;
      sync();
      if (armed) {
        var a = document.activeElement;
        back = (a && a !== document.body) ? a : null;
        window.addEventListener('keydown', keys, true);
        // After the drawer has closed, so focus lands on what is showing.
        setTimeout(function () {
          if (armed && bar && !bar.contains(document.activeElement)) {
            try { bar._done.focus({ preventScroll: true }); } catch (e) {}
          }
        }, 0);
        say(touchFirst ? 'Recolor is on. Tap a line to give it the pen’s color, or hold still to aim at a thin one. Done goes back to the pen.'
          : 'Recolor is on. The line under the pointer lights up; click it to give it the pen’s color. Done goes back to the pen.');
      } else {
        window.removeEventListener('keydown', keys, true);
        var had = bar.contains(document.activeElement);
        setTimeout(function () {
          if (armed || !(had || document.activeElement === document.body)) return;
          var to = [back, o.button, o.focusHome && o.focusHome()].filter(function (e) {
            return e && e.isConnected && !e.disabled && (e.offsetWidth || e.offsetHeight);
          })[0];
          if (to) { try { to.focus({ preventScroll: true }); } catch (e) {} }
        }, 0);
        back = null;
      }
    }
    function arm() { setArmed(true); }
    function disarm() { setArmed(false); }

    function keys(e) {
      if (!armed || e.key !== 'Escape') return;
      if (o.colorsOpen && o.colorsOpen()) return;   // the drawer's own Escape closes it first
      e.preventDefault();
      disarm();
    }

    /* ---- the gesture ---- */
    function where(e) {
      var p = o.point(e);
      return { x: p.x, y: p.y, cx: e.clientX, cy: e.clientY };
    }
    function same(s, e) { return e.pointerId == null || s.id == null || e.pointerId === s.id; }

    /* From the surface's own press handler while the mode is on: true when it
       took the press. */
    function press(e) {
      if (!armed) return false;
      if (e.pointerType === 'mouse' && e.button > 0) return true;
      if (session) {                       // a second finger: a pinch, not a line
        if (!same(session, e)) end(true);
        return true;
      }
      if (o.colorsOpen && o.colorsOpen()) { if (o.closeColors) o.closeColors(); return true; }
      var L = o.lines();
      ix = index(L.pts || [], L.groups || []);
      var at = where(e);
      unhover();
      session = { id: e.pointerId, from: at, last: at, moved: false, changed: false, touched: {}, aim: null, art: null, hold: 0 };
      // A finger, or a pen, that stays where it went down aims (the lens);
      // a mouse never needs to.
      if (e.pointerType !== 'mouse') session.hold = setTimeout(aimStart, HOLD);
      window.addEventListener('pointermove', move, true);
      window.addEventListener('pointerup', up, true);
      window.addEventListener('pointercancel', cancel, true);
      return true;
    }
    /* Held still: the lens comes up over the point, and the line under it
       lights. The picture is taken once: nothing changes while aiming. */
    function aimStart() {
      var s = session;
      if (!s || s.moved || !armed) return;
      s.hold = 0;
      try {
        var a = o.art();
        s.art = document.createElement('canvas');
        s.art.width = a.width; s.art.height = a.height;
        s.art.getContext('2d').drawImage(a, 0, 0);
      } catch (e) { s.art = null; }
      s.aim = s.last;
      aimAt(s.last);
      say('Aiming. Lift to recolor the lit line.');
    }
    function aimAt(p) {
      var s = session;
      if (!s || !ix) return;
      var h = hit(ix, p.x, p.y, SLACK * perCss());
      s.aim = p;
      light(h ? lineOf(ix, h.g) : null, ix);
      drawLens(p, h, s.art);
    }
    function aimStop() {
      hideLens();
      light(null);
    }
    function move(e) {
      var s = session;
      if (!s || !same(s, e)) return;
      if (s.aim) {                         // aiming: the lens and the light follow; nothing changes yet
        s.last = where(e);
        aimAt(s.last);
        if (e.cancelable) e.preventDefault();
        return;
      }
      if (!s.moved && Math.hypot(e.clientX - s.from.cx, e.clientY - s.from.cy) < SLOP) return;
      if (!s.moved) { clearTimeout(s.hold); s.hold = 0; s.moved = true; tryAt(s.from); }
      var to = where(e), n = Math.max(1, Math.ceil(Math.hypot(to.cx - s.last.cx, to.cy - s.last.cy) / STEP));
      for (var k = 1; k <= n; k++) {
        tryAt({ x: s.last.x + (to.x - s.last.x) * k / n, y: s.last.y + (to.y - s.last.y) * k / n });
      }
      s.last = to;
      if (e.cancelable) e.preventDefault();
    }
    function up(e) {
      var s = session;
      if (!s || !same(s, e)) return;
      clearTimeout(s.hold);
      if (s.aim) {                         // let go: the lit line takes the colour
        var p = s.aim;
        aimStop();
        tryAt(p);
      } else if (!s.moved) {
        tryAt(s.from);
      }
      end(false);
    }
    function cancel(e) { if (session && same(session, e)) end(false); }
    function end(pinch) {
      var s = session;
      session = null;
      window.removeEventListener('pointermove', move, true);
      window.removeEventListener('pointerup', up, true);
      window.removeEventListener('pointercancel', cancel, true);
      if (!s) return;
      clearTimeout(s.hold);
      if (s.aim) aimStop();                // a second finger, or a cancel, while aiming: nothing changes
      if (pinch && s.aim) return;
      if (pinch && !s.moved) return;
      if (s.changed) {
        if (o.end) o.end();
        sync();
        say('Recolored');
      }
    }

    function tryAt(p) {
      var s = session;
      if (!s || !ix) return;
      var h = hit(ix, p.x, p.y, SLACK * perCss());
      if (!h) return;
      var line = lineOf(ix, h.g);
      if (s.touched[line[0]]) return;
      var hex = o.color(), pts = ix.pts, a = ix.st[line[0]], b = ix.st[line[1] + 1];
      var change = false;
      for (var i = a; i < b && !change; i++) if (tint(pts[i].color, hex) !== pts[i].color) change = true;
      for (var g = line[0]; g <= line[1]; g++) s.touched[g] = true;
      if (!change) return;
      if (!s.changed && o.begin) o.begin();
      run.hold();
      if (!o.apply(line[0], line[1], hex, h.i)) return;
      s.changed = true;
      hix = null;
      // The lines as they now stand: the editor may have put new point
      // objects in place of the old.
      ix.pts = o.lines().pts;
      o.repaint();
      run.add(ix.pts.slice(a, b), h.i - a);
    }

    if (o.button) {
      o.button.addEventListener('click', function (e) {
        e.stopPropagation();
        setArmed(!armed);
      });
      o.button.setAttribute('aria-pressed', 'false');
    }

    return {
      arm: arm,
      disarm: disarm,
      isArmed: function () { return armed; },
      press: press,
      sync: sync,
      // The drawing changed under the mode (undo, a page, a load): any run
      // ends where it was going, and the light is read again when next asked.
      settle: function () { run.stop(); hix = null; if (!session) light(null); },
      // For the harness and the owner's screenshots, read-only: whether a
      // finger is aiming, the line lit ([g0, g1]) and the lens's box.
      aimState: function () {
        var r = lens && !lens.hidden ? lens.getBoundingClientRect() : null;
        return { aiming: !!(session && session.aim), lit: lit ? lit.slice() : null,
                 lens: r ? { left: r.left, top: r.top, width: r.width, height: r.height } : null };
      },
      // For a change made outside the mode (Flip's Select bar): hold() the
      // drawing before it, repaint after it, then ran() the lines it changed,
      // each from its middle.
      hold: function () { run.hold(); },
      ran: function (lines) {
        (lines || []).forEach(function (pts) { run.add(pts, pts.length >> 1); });
      }
    };
  }

  /* THE BUTTON'S DROP TAKES THE PEN'S COLOUR (the owner, after v329, C of the
   * mock; styles.css .rc-inks says what is drawn). Each editor calls sync() on
   * every pen colour change, so every .rc-inks drawing (the button, and
   * Recolor's tip in How it works) is given the colour here, and .rc-pale
   * where that colour is under 3:1 against the first painted ground behind it,
   * which outlines it in the button's grey. Asked again when the theme
   * changes: one colour can read on one ground and not the other. */
  var lastInk = null;
  function rgbOf(str) {
    var m = String(str).match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+))?/);
    return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] == null ? 1 : +m[4] } : null;
  }
  function lum(c) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }
  function groundOf(el) {
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      var c = rgbOf(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.5) return c;
    }
    return { r: 255, g: 255, b: 255 };
  }
  function inkButton(hex) {
    if (/^#[0-9a-f]{6}$/i.test(hex || '')) lastInk = hex.toLowerCase();
    if (!lastInk) return;
    var ink = { r: parseInt(lastInk.slice(1, 3), 16), g: parseInt(lastInk.slice(3, 5), 16), b: parseInt(lastInk.slice(5, 7), 16) };
    var drawings = document.querySelectorAll('.rc-inks');
    for (var i = 0; i < drawings.length; i++) {
      var el = drawings[i], a = lum(ink), b = lum(groundOf(el));
      el.style.setProperty('--recolor-ink', lastInk);
      el.classList.toggle('rc-pale', (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) < 3);
    }
  }
  (function () {
    var again = function () { requestAnimationFrame(function () { inkButton(null); }); };
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(again).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    }
    try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', again); } catch (e) {}
  })();

  window.SkriblRecolor = { RUN: RUN, tint: tint, index: index, hit: hit, lineOf: lineOf, runner: runner, create: create };
}());
