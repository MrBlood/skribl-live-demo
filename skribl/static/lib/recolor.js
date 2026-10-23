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
 */
(function () {
  'use strict';

  var RUN = 380;      // ms for a new colour to run the length of a line (lib/recolorplay.js RUN)
  var SLOP = 8;       // CSS px a press travels before it is a drag
  var SLACK = 10;     // CSS px of finger around a line that still hits it
  var STEP = 4;       // CSS px between the hit-tests along a drag

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
       openColors()/colorsOpen()/closeColors()  the colour drawer
       focusHome()  where focus goes if what armed the mode has gone
       onChange(on) after the mode turns on or off */
  function create(o) {
    var armed = false, session = null, ix = null, bar = null, live = null, back = null, shown = null;
    var run = runner({ canvas: o.surface, art: o.art, unit: o.unit });

    // Drawing units a CSS pixel, for the finger's slack: the canvas is shown
    // fitted, zoomed or both.
    function perCss() {
      var r = o.surface.getBoundingClientRect();
      return r.width ? (o.surface.width / (o.unit() || 1)) / r.width : 1;
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
      say.textContent = 'Tap a line to recolor';
      var undo = el('button', 'recolor-undo', bar);
      undo.type = 'button';
      undo.title = 'Undo';
      undo.setAttribute('aria-label', 'Undo');
      undo.innerHTML = UNDO_SVG;
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
      // The editor's Undo says when there is nothing to take back, from every
      // path that changes it (a keyboard undo included); this one follows.
      if (o.undoButton && window.MutationObserver) {
        new MutationObserver(sync).observe(o.undoButton, { attributes: true, attributeFilter: ['disabled'] });
      }
      done.addEventListener('click', function (e) { e.stopPropagation(); disarm(); });
      live = el('div', 'vis-hidden', bar);
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      (o.dock || document.body).appendChild(bar);
      bar._swatch = swatch; bar._dot = swatch.firstChild; bar._undo = undo; bar._done = done;
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
      if (armed && shown && shown !== hex && o.colorsOpen && o.colorsOpen() && o.closeColors) o.closeColors();
      shown = hex;
    }

    function setArmed(v) {
      v = !!v;
      if (v === armed) return;
      armed = v;
      if (session) end(false);
      run.stop();
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
        say('Recolor is on. Tap a line to give it the pen’s color. Done goes back to the pen.');
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
      session = { id: e.pointerId, from: at, last: at, moved: false, changed: false, touched: {} };
      window.addEventListener('pointermove', move, true);
      window.addEventListener('pointerup', up, true);
      window.addEventListener('pointercancel', cancel, true);
      return true;
    }
    function move(e) {
      var s = session;
      if (!s || !same(s, e)) return;
      if (!s.moved && Math.hypot(e.clientX - s.from.cx, e.clientY - s.from.cy) < SLOP) return;
      if (!s.moved) { s.moved = true; tryAt(s.from); }
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
      if (!s.moved) tryAt(s.from);
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
      // ends where it was going.
      settle: function () { run.stop(); },
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
