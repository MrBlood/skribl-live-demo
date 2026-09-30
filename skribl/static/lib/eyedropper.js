/* Eyedropper — the armed-state machine, shared by both editors.
 *
 * WHY ONE PATH AND NOT TWO. Pad used to call the browser's native
 * `window.EyeDropper` when present and fall back to tap-to-sample otherwise;
 * Flip only ever did tap-to-sample. That native branch is not an ALTERNATIVE
 * to the fallback, it is an EXTRA: Safari, Firefox and every browser on iOS
 * have no EyeDropper, so the in-app path has to exist regardless. Keeping both
 * meant maintaining two implementations forever and shipping two different
 * experiences behind one button depending on which browser opened it.
 *
 * It was also the wrong semantics. The native picker samples anything on the
 * screen, including other applications, when the thing being asked for is "the
 * colour of that part of my drawing". And an OS-level dialog cannot be driven
 * by the harness, so the path most desktop users took was the path no
 * assertion could reach.
 *
 * Deleting it removes a path rather than adding one. The cost is that desktop
 * Chrome loses screen-wide sampling; if that is wanted back it belongs here,
 * once, not in one editor only.
 *
 * WHAT THIS OWNS: armed/disarmed, the button's class and aria-pressed, the
 * canvas cursor, Escape, the one-shot semantics (a pick disarms), and THE
 * LENS — the armed cue and the picker, below — with its armed pill.
 * WHAT IT DOES NOT: what a surface does with the colour. Pad and Flip differ
 * there (Pad rings its custom swatch and feeds recents from its setter, Flip
 * closes its popover), so `onPick` is injected, and so is everything that
 * says WHERE the drawing is: `getPoint`, `artwork`, `dpr`, `bg`, `current`.
 *
 * THE LENS (the owner picked it, option C of three mocks). What it
 * replaced had three faults, each seen on a phone: arming veiled the colour
 * drawer, taking the armed button with it, so nothing on screen said the
 * next touch would pick (the Pad showed a 2.8s toast, Flip showed nothing);
 * the loupe floated 26px above the finger with nothing tying it to the point
 * it read; and the finger sat on the pixel being sampled.
 *
 *   ARMING IS VISIBLE. Arming puts the lens straight onto the drawing — at the
 *   last point the pen touched, else the middle of the canvas — and a pill at
 *   the top of the canvas says what to do, with a Cancel. The pill stays until
 *   the pick ends; it is announced once through a polite live region.
 *
 *   THE LENS SITS ON THE POINT IT READS. An 11-cell grid at 10x, the centre
 *   cell under a two-tone reticle IS the pixel a pick takes. The ring is split:
 *   top half the colour it will pick, bottom half the pen's current colour, so
 *   a pick that changes nothing shows one colour all the way round.
 *
 *   TOUCH: a handle hangs below the lens and the finger drags THAT, so the
 *   finger is never over what is being read. A drag anywhere on the drawing
 *   moves the lens by the finger's travel (the handle's offset, kept), a tap
 *   moves the lens to the tapped point without picking, and lifting after a
 *   drag picks. MOUSE/PEN: the lens follows the pointer, centred on it (the
 *   cursor hides over the canvas); a click picks. KEYBOARD: arrows nudge one
 *   cell, Shift+arrow ten, Enter picks — the Firefox DevTools model.
 *
 *   EDGES: the lens stays whole inside the viewport — it is fixed to the page,
 *   above the canvas card, so no editor's overflow can clip it. Against a
 *   side it slides inward; against the top it slides SIDEWAYS rather than
 *   down, because down is where the hand is. While the point is still under
 *   the lens, the grid is laid out around the point and the reticle sits ON
 *   it, off-centre; only when the lens has been carried clear of it does a
 *   small two-tone mark sit on the true point instead.
 *   The pill never covers the lens or its chip: when they come up to it, it
 *   moves to the bottom of the canvas, at full strength, because Cancel is
 *   the only way out on a phone (the eyedropper button is veiled with its
 *   drawer while armed, so "tap it again" is not a route).
 *
 *   Escape and Cancel abandon without picking; pointercancel abandons the
 *   drag in progress and puts the lens back. A second finger on the drawing
 *   is a pinch, not an aim: the drag is abandoned, the lens stays on the
 *   point of the drawing it was on while the canvas zooms, and nothing picks
 *   when the fingers lift. The editors also disarm on undo, redo, a page
 *   change, playback and a tool change, since each changes what is under it.
 *
 *   FOCUS: arming moves focus to the pill (the armed button is veiled, and
 *   focus left on it drops to <body>); ending the pick hands it back to the
 *   control that armed it, or to `focusHome` if that has gone with its drawer.
 *
 * The lens draws from the surface's COMPOSITED stage (padArtwork /
 * paintArtwork via `artwork`), and the pick reads the centre cell of the very
 * grid the lens draws, so what it shows and what it picks cannot disagree —
 * photo, background colour and strokes included, onion skin and guides
 * excluded for exactly the reason sampling excludes them. The stage is copied
 * ONCE per arm and every lens frame reads the copy: Flip's paintArtwork
 * re-rasterises the whole page (~5ms on a busy one, desktop), too much per
 * frame on a phone. `refresh()` drops the copy if a surface ever changes the
 * drawing without disarming.
 *
 * The grid and reticle are drawn in DEVICE pixels, snapped, so they are crisp
 * at 1x and 1.25x (the owner's Windows desktop), not only on a Retina screen.
 */
(function () {
  'use strict';

  /* Geometry shared with the .eyedropper-lens CSS (116px): keep in step. */
  var LENS = 116, R = LENS / 2;
  var CELLS = 11, CELL = 10;       // 11 screen px across, each drawn 10x
  // Cells READ per side: 23, so the grid still fills the window when the
  // reticle is drawn off-centre over the true point (see render()).
  var READ = 23;
  var REACH = R - 4;               // how far off-centre the reticle may sit
  var RING_R = 55.5, RING_W = 5;   // the split ring, 53..58
  var WINDOW_R = 53;               // the grid shows inside this radius
  var MARGIN = 6;                  // lens and chip keep this far from the viewport edge
  var HANDLE_GAP = 4, HANDLE_H = 20;
  var TAP_SLOP = 8;                // a touch that travels less than this is a tap

  function el(tag, cls, parent) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (parent) parent.appendChild(e);
    return e;
  }

  function hexOf(d, i) {
    return '#' + [d[i], d[i + 1], d[i + 2]].map(function (v) {
      return v.toString(16).padStart(2, '0');
    }).join('');
  }

  /* The palette's name for a hex, for the pick announcement; else the hex. */
  function nameOf(hex) {
    var P = window.SkriblPalette && window.SkriblPalette.PEN;
    if (P) for (var i = 0; i < P.length; i++) if (P[i].hex.toLowerCase() === hex) return P[i].name;
    return hex.toUpperCase();
  }

  function visible(e) {
    if (!e || !e.isConnected || e.disabled) return false;
    if (typeof e.checkVisibility === 'function') return e.checkVisibility({ visibilityProperty: true });
    return !!(e.offsetWidth || e.offsetHeight) && getComputedStyle(e).visibility !== 'hidden';
  }

  function overlaps(a, b, pad) {
    pad = pad || 0;
    return a.l < b.r + pad && b.l < a.r + pad && a.t < b.b + pad && b.t < a.b + pad;
  }

  function create(opts) {
    opts = opts || {};
    var button = opts.button || null;
    var surface = opts.surface || null;             // the drawing canvas
    var idleCursor = opts.idleCursor || '';         // Pad restores '', Flip 'none'
    var onSample = typeof opts.onSample === 'function' ? opts.onSample : function () {};
    var onArm = typeof opts.onArm === 'function' ? opts.onArm : function () {};
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    // Where focus goes when the pick ends and the control that armed it has
    // gone with its drawer (a pick closes the drawer on both editors).
    var focusHome = typeof opts.focusHome === 'function' ? opts.focusHome : function () { return null; };
    // Lens wiring — all present enables the lens; without them beginPick()
    // declines and the surface's one-shot tap path runs.
    var getPoint = typeof opts.getPoint === 'function' ? opts.getPoint : null;
    var artwork = typeof opts.artwork === 'function' ? opts.artwork : null;
    var dprOf = typeof opts.dpr === 'function' ? opts.dpr : function () { return window.devicePixelRatio || 1; };
    var bgOf = typeof opts.bg === 'function' ? opts.bg : function () { return '#000000'; };
    var currentOf = typeof opts.current === 'function' ? opts.current : function () { return null; };
    var onPick = typeof opts.onPick === 'function' ? opts.onPick : null;
    var lensOn = !!(getPoint && artwork && onPick && surface);

    var armed = false;
    var mode = 'mouse';     // 'touch' | 'mouse' — which copy the pill wears, whether the handle shows
    var ui = null;          // lens, handle, mark, chip, pill: built on first arm
    var live = null;        // the polite live region: built up front, so it exists before it speaks
    var at = null;          // the lens point, as an offset (CSS px) from the surface's top-left
    var session = null;     // the active drag, or null
    var raf = 0;
    var last = null;        // where the pen last touched, in STAGE coordinates
    var lastHex = null;
    var snap = null;        // the composited stage, copied once per arm
    var fingers = {};       // touch pointers down while armed (id -> true)
    var pinchAt = null;     // while a pinch is on: the STAGE point the lens stays on
    var returnFocus = null; // the control focus goes back to when the pick ends

    /* ---- the live region --------------------------------------------------- */
    // Created with the lib, not on first arm: a region inserted just before it
    // first changes is often missed (VoiceOver on iOS).
    function makeLive() {
      if (live || !document.body) return;
      live = el('div', 'eyedropper-live', document.body);
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
    }
    if (lensOn) {
      if (document.body) makeLive();
      else document.addEventListener('DOMContentLoaded', makeLive);
    }
    function say(text) {
      makeLive();
      if (!live) return;
      live.textContent = '';
      setTimeout(function () { if (live) live.textContent = text; }, 60);
    }

    /* ---- where the pen last was ----------------------------------------- */
    if (surface) {
      var tracking = false;
      // Stage, not client, coordinates: opening the colour drawer to reach the
      // eyedropper can move or resize the canvas, and the point the pen last
      // touched is a point in the DRAWING.
      var note = function (e) {
        if (!getPoint) return;
        try { last = getPoint({ clientX: e.clientX, clientY: e.clientY }); } catch (err) {}
      };
      surface.addEventListener('pointerdown', function (e) {
        if (armed) return;
        tracking = true; note(e);
      }, true);
      window.addEventListener('pointermove', function (e) { if (tracking && !armed) note(e); }, true);
      window.addEventListener('pointerup', function () { tracking = false; }, true);
      window.addEventListener('pointercancel', function () { tracking = false; }, true);
    }

    /* ---- the DOM ---------------------------------------------------------- */
    function build() {
      if (ui) return ui;
      makeLive();
      var pill = el('div', 'eyedropper-pill');
      pill.hidden = true;
      // Focus lands here on arm (see FOCUS in the header): a named group, so a
      // screen reader says what it is, and arrows and Enter drive the lens.
      pill.tabIndex = -1;
      pill.setAttribute('role', 'group');
      pill.setAttribute('aria-label', 'Colour picker');
      var text = el('span', 'eyedropper-pill-text', pill);
      var cancel = el('button', 'eyedropper-pill-cancel', pill);
      cancel.type = 'button';
      cancel.textContent = 'Cancel';
      cancel.setAttribute('aria-label', 'Cancel colour pick');
      var lens = el('div', 'eyedropper-lens');
      lens.hidden = true;
      lens.setAttribute('aria-hidden', 'true');
      var cv = el('canvas', '', lens);
      var handle = el('div', 'eyedropper-lens-handle');
      handle.hidden = true;
      handle.setAttribute('aria-hidden', 'true');
      var mark = el('div', 'eyedropper-lens-mark');
      mark.hidden = true;
      mark.setAttribute('aria-hidden', 'true');
      var chip = el('div', 'eyedropper-lens-chip');
      chip.hidden = true;
      chip.setAttribute('aria-hidden', 'true');
      // A fixed element is placed against its containing block, which is the
      // viewport only when no ancestor makes itself one — and on both editors
      // something does: on a 1400px desktop everything fixed here landed 10px
      // right of where it was put. So positions are written relative to this
      // probe's measured origin rather than assumed to be client coordinates.
      var probe = el('div', 'eyedropper-origin');
      probe.setAttribute('aria-hidden', 'true');
      // Document order is paint order at one z-index: the pill first, so the
      // lens, its mark and its chip are never under it.
      [probe, pill, lens, handle, mark, chip].forEach(function (n) { document.body.appendChild(n); });

      // The pill's controls must not reach the page's outside-click handlers:
      // the drawer they would close is the one the abandoned pick gives back.
      ['pointerdown', 'mousedown', 'touchstart'].forEach(function (t) {
        pill.addEventListener(t, function (e) { e.stopPropagation(); });
      });
      cancel.addEventListener('click', function (e) { e.stopPropagation(); disarm(); });
      handle.addEventListener('pointerdown', function (e) {
        if (!armed || session) return;
        e.preventDefault(); e.stopPropagation();
        if (e.pointerType === 'touch') setMode('touch');
        startSession(e, 'handle');
      });
      ['mousedown', 'touchstart'].forEach(function (t) {
        handle.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true });
      });

      ui = { probe: probe, lens: lens, cv: cv, ctx: cv.getContext('2d'), handle: handle, mark: mark,
             chip: chip, pill: pill, text: text, cancel: cancel };
      return ui;
    }

    /* ---- geometry --------------------------------------------------------- */
    function rect() { return surface.getBoundingClientRect(); }
    // The lens point in client coordinates, snapped to the centre of a screen
    // pixel so the centre cell is exactly one pixel of what is on screen.
    function client() {
      var r = rect();
      return { x: Math.floor(r.left + at.x) + 0.5, y: Math.floor(r.top + at.y) + 0.5 };
    }
    function setClient(x, y) {
      var r = rect();
      at = { x: Math.min(Math.max(x - r.left, 0), Math.max(r.width - 1, 0)),
             y: Math.min(Math.max(y - r.top, 0), Math.max(r.height - 1, 0)) };
      schedule();
    }
    function nudge(dx, dy) { var c = client(); setClient(c.x + dx, c.y + dy); }
    // The part of the canvas that is on screen, in client px.
    function onScreen() {
      var r = rect(), W = window.innerWidth, H = window.innerHeight;
      return { l: Math.max(r.left, 0), r: Math.min(r.right, W), t: Math.max(r.top, 0), b: Math.min(r.bottom, H) };
    }
    // A STAGE point back to client px (getPoint's inverse, from two samples),
    // held inside the visible canvas.
    function setStage(S) {
      var r = rect(), v = onScreen();
      var p0 = getPoint({ clientX: r.left, clientY: r.top });
      var p1 = getPoint({ clientX: r.left + 100, clientY: r.top + 100 });
      var kx = (p1.x - p0.x) / 100, ky = (p1.y - p0.y) / 100;
      var x = (v.l + v.r) / 2, y = (v.t + v.b) / 2;
      if (S && kx > 0 && ky > 0) { x = r.left + (S.x - p0.x) / kx; y = r.top + (S.y - p0.y) / ky; }
      setClient(Math.min(Math.max(x, v.l), Math.max(v.r - 1, v.l)),
                Math.min(Math.max(y, v.t), Math.max(v.b - 1, v.t)));
    }

    /* The composited stage, copied once per arm (see the header). */
    function stage() {
      if (snap) return snap;
      var a = artwork();
      var c = document.createElement('canvas');
      c.width = a.width; c.height = a.height;
      var g = c.getContext('2d', { willReadFrequently: true });
      g.drawImage(a, 0, 0);
      snap = { cv: c, g: g };
      return snap;
    }

    /* The grid, read from the composited stage: cell (i, j) is the stage pixel
     * under screen point (C.x + i, C.y + j). One getImageData for all of it. */
    function readGrid() {
      var C = client();
      var h = (READ - 1) / 2;
      var art = stage();
      var adpr = dprOf();
      var p0 = getPoint({ clientX: C.x, clientY: C.y });
      var p1 = getPoint({ clientX: C.x + 100, clientY: C.y + 100 });
      var kx = (p1.x - p0.x) / 100, ky = (p1.y - p0.y) / 100;
      var xs = [], ys = [];
      for (var i = -h; i <= h; i++) {
        xs.push(Math.floor((p0.x + i * kx) * adpr));
        ys.push(Math.floor((p0.y + i * ky) * adpr));
      }
      var x0 = xs[0], y0 = ys[0], w = xs[READ - 1] - x0 + 1, hh = ys[READ - 1] - y0 + 1;
      var bg = bgOf();
      var data = null;
      try { data = art.g.getImageData(x0, y0, Math.max(w, 1), Math.max(hh, 1)).data; } catch (e) {}
      var cells = [];
      for (var jy = 0; jy < READ; jy++) {
        for (var ix = 0; ix < READ; ix++) {
          var X = xs[ix], Y = ys[jy], c = bg;
          if (data && X >= 0 && Y >= 0 && X < art.cv.width && Y < art.cv.height) {
            var k = ((Y - y0) * w + (X - x0)) * 4;
            if (data[k + 3] >= 10) c = hexOf(data, k);
          }
          cells.push(c);
        }
      }
      return { cells: cells, hex: cells[(READ * READ - 1) / 2], stage: p0 };
    }

    /* A square ring of width w just inside the device-px box [x0,x1)x[y0,y1). */
    function frame(ctx, x0, y0, x1, y1, w, color) {
      ctx.fillStyle = color;
      ctx.fillRect(x0, y0, x1 - x0, w);
      ctx.fillRect(x0, y1 - w, x1 - x0, w);
      ctx.fillRect(x0, y0 + w, w, y1 - y0 - 2 * w);
      ctx.fillRect(x1 - w, y0 + w, w, y1 - y0 - 2 * w);
    }

    /* (dx, dy): where the true point is relative to the lens centre, when the
     * viewport has pushed the lens off it. The grid is laid out around THAT
     * spot, so the reticle sits over the very pixel it reads, not beside a
     * mark that says where it really is. */
    function drawLens(g, dx, dy) {
      var cv = ui.cv, ctx = ui.ctx;
      var px = Math.round(LENS * (window.devicePixelRatio || 1));
      if (cv.width !== px) { cv.width = px; cv.height = px; }
      var D = px / LENS;                               // device px per CSS px, as drawn
      var snapTo = function (v) { return Math.round(v * D); };
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, px, px);
      ctx.save();
      ctx.beginPath(); ctx.arc(R * D, R * D, WINDOW_R * D, 0, Math.PI * 2); ctx.clip();
      // Cells and lines on whole device pixels: at 1x or 1.25x a line at a
      // fractional position smears across two pixels at half contrast.
      var h = (READ - 1) / 2;
      var ox = R + dx - CELL / 2 - h * CELL, oy = R + dy - CELL / 2 - h * CELL;   // cell 0's corner (CSS px)
      var bx = [], by = [];
      for (var n = 0; n <= READ; n++) { bx.push(snapTo(ox + n * CELL)); by.push(snapTo(oy + n * CELL)); }
      for (var j = 0; j < READ; j++) for (var i = 0; i < READ; i++) {
        if (bx[i + 1] < 0 || by[j + 1] < 0 || bx[i] > px || by[j] > px) continue;
        ctx.fillStyle = g.cells[j * READ + i];
        ctx.fillRect(bx[i], by[j], bx[i + 1] - bx[i], by[j + 1] - by[j]);
      }
      var lw = Math.max(1, Math.round(D / 2));
      ctx.fillStyle = 'rgba(128,128,128,0.28)';
      for (var m = 0; m <= READ; m++) {
        ctx.fillRect(bx[m], 0, lw, px);
        ctx.fillRect(0, by[m], px, lw);
      }
      ctx.restore();
      // The split ring: top = what a pick takes, bottom = the pen now.
      ctx.setTransform(D, 0, 0, D, 0, 0);
      var cur = currentOf() || g.hex;
      ctx.lineWidth = RING_W;
      ctx.strokeStyle = g.hex;
      ctx.beginPath(); ctx.arc(R, R, RING_R, Math.PI, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = cur;
      ctx.beginPath(); ctx.arc(R, R, RING_R, 0, Math.PI); ctx.stroke();
      // A thin neutral edge either side, so a ring the colour of the drawing
      // under it still has an outline.
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(0,0,0,0.45)';
      ctx.beginPath(); ctx.arc(R, R, R - 0.5, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.55)';
      ctx.beginPath(); ctx.arc(R, R, WINDOW_R, 0, Math.PI * 2); ctx.stroke();
      // The reticle on the read cell, dark / white / dark, each band whole
      // device pixels and all OUTSIDE the cell but a hairline, so the cell a
      // pick takes stays readable at its own colour. Last, and unclipped, so
      // a reticle pushed out toward the rim still shows whole over the ring.
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      var x0 = bx[h], x1 = bx[h + 1], y0 = by[h], y1 = by[h + 1];
      var u = Math.max(1, Math.round(D));
      frame(ctx, x0 - 2 * u, y0 - 2 * u, x1 + 2 * u, y1 + 2 * u, u, 'rgba(0,0,0,0.85)');
      frame(ctx, x0 - u, y0 - u, x1 + u, y1 + u, u, '#ffffff');
      frame(ctx, x0, y0, x1, y1, Math.max(1, Math.round(D / 2)), 'rgba(0,0,0,0.6)');
    }

    /* Where the lens goes for the point P: on it, unless the viewport says
     * otherwise. Sides slide it inward; the top slides it sideways, never
     * down, because below the lens is the handle and the hand. */
    function place(P) {
      var W = window.innerWidth, H = window.innerHeight;
      var below = mode === 'touch' ? HANDLE_GAP + HANDLE_H + 10 : 0;
      var L = { x: P.x, y: P.y };
      if (L.y - R < MARGIN) {
        L.y = MARGIN + R;
        var side = P.x < W / 2 ? 1 : -1;
        L.x = P.x + side * (R + 14);
      }
      if (L.y + R + below > H - MARGIN) L.y = Math.max(MARGIN + R, H - MARGIN - R - below);
      L.x = Math.min(Math.max(L.x, MARGIN + R), Math.max(W - MARGIN - R, MARGIN + R));
      return L;
    }

    function render() {
      raf = 0;
      if (!armed || !ui || !at) return;
      var g;
      try { g = readGrid(); } catch (e) { return; }
      lastHex = g.hex;
      var P = client();
      var L = place(P);
      // Pushed off the point but still over it: the reticle goes onto the
      // point. Pushed clear of it (the top edge slides the lens sideways):
      // reticle centred, and the mark on the true point.
      var dx = P.x - L.x, dy = P.y - L.y, off = Math.hypot(dx, dy) > REACH;
      drawLens(g, off ? 0 : dx, off ? 0 : dy);
      var u = ui;
      var o = u.probe.getBoundingClientRect();
      var ox = o.left, oy = o.top;
      var W = window.innerWidth, H = window.innerHeight;
      u.lens.style.left = (L.x - R - ox) + 'px';
      u.lens.style.top = (L.y - R - oy) + 'px';
      u.lens.dataset.hex = g.hex;
      u.lens.hidden = false;
      u.mark.hidden = !off;
      if (off) { u.mark.style.left = (P.x - ox) + 'px'; u.mark.style.top = (P.y - oy) + 'px'; }
      var touch = mode === 'touch';
      u.handle.hidden = !touch;
      u.handle.style.left = (L.x - ox) + 'px';
      u.handle.style.top = (L.y + R + HANDLE_GAP + HANDLE_H / 2 - oy) + 'px';
      var lensBox = { l: L.x - R, r: L.x + R, t: L.y - R, b: L.y + R + (touch ? HANDLE_GAP + HANDLE_H + 12 : 0) };

      u.chip.textContent = g.hex.toUpperCase();
      u.chip.hidden = false;
      var cw = u.chip.offsetWidth || 72, ch = u.chip.offsetHeight || 22;
      var chipAt = function (cx, top) { return { x: cx, top: top, box: { l: cx - cw / 2, r: cx + cw / 2, t: top, b: top + ch } }; };
      var inView = function (c) { return c.box.l >= MARGIN && c.box.r <= W - MARGIN && c.box.t >= MARGIN && c.box.b <= H - MARGIN; };
      var above = chipAt(L.x, L.y - R - 8 - ch);

      // The pill: top of the visible canvas, unless the lens (with its handle)
      // or the chip above it would meet it there; then the bottom.
      var pill = placePill([lensBox].concat(inView(above) ? [above.box] : []));

      // The chip: above the lens, else beside it (away from the nearer edge),
      // else — mouse only, where no hand is — below. Never on the pill.
      var sideFirst = L.x < W / 2 ? 1 : -1;
      var cands = [above,
                   chipAt(L.x + sideFirst * (R + 8 + cw / 2), L.y - ch / 2),
                   chipAt(L.x - sideFirst * (R + 8 + cw / 2), L.y - ch / 2)];
      if (!touch) cands.push(chipAt(L.x, L.y + R + 8));
      var c = null;
      for (var k = 0; k < cands.length && !c; k++) {
        if (inView(cands[k]) && !overlaps(cands[k].box, pill, 4)) c = cands[k];
      }
      if (!c) c = chipAt(Math.min(Math.max(L.x, MARGIN + cw / 2), W - MARGIN - cw / 2), Math.max(MARGIN, above.top));
      u.chip.style.left = (c.x - ox) + 'px';
      u.chip.style.top = (c.top - oy) + 'px';
    }
    function schedule() { if (!raf) raf = requestAnimationFrame(render); }

    /* Places the pill and returns its box. Never faded: Cancel is the way out. */
    function placePill(avoid) {
      var u = ui, v = onScreen();
      u.pill.hidden = false;
      var pw = u.pill.offsetWidth, ph = u.pill.offsetHeight;
      var W = window.innerWidth;
      var cx = Math.min(Math.max((v.l + v.r) / 2, pw / 2 + 8), W - pw / 2 - 8);
      var boxAt = function (top) { return { l: cx - pw / 2, r: cx + pw / 2, t: top, b: top + ph }; };
      var hits = function (bx) { return avoid.some(function (a) { return overlaps(a, bx, 6); }); };
      var box = boxAt(v.t + 10);
      if (hits(box)) {
        var low = boxAt(v.b - 10 - ph);
        if (!hits(low) && low.t > box.b) box = low;
      }
      var o = u.probe.getBoundingClientRect();
      u.pill.style.left = (cx - o.left) + 'px';
      u.pill.style.top = (box.t - o.top) + 'px';
      u.pill.classList.toggle('eyedropper-pill-low', box.t > v.t + 10);
      return box;
    }

    function copy() {
      return mode === 'touch' ? 'Drag the lens to pick' : 'Click your drawing to pick a colour';
    }
    function setMode(m) {
      if (m === mode) return;
      mode = m;
      if (ui) ui.text.textContent = copy();
      schedule();
    }

    /* ---- the drag --------------------------------------------------------- */
    function sameSourceAs(ev) {
      return function (e) {
        if (ev.pointerId != null && e.pointerId != null) return e.pointerId === ev.pointerId;
        return e.isPrimary !== false;
      };
    }
    function pointOf(e) {
      var t = (e.touches && e.touches.length) ? e.touches[0]
            : (e.changedTouches && e.changedTouches.length) ? e.changedTouches[0] : e;
      return { x: t.clientX, y: t.clientY };
    }

    /* kind: 'handle' (drag the handle; lift picks), 'touch' (a finger on the
     * drawing: a drag moves the lens by its travel and lift picks, a tap moves
     * the lens there and does not), 'mouse' (lens under the pointer; release
     * picks). The session listens on WINDOW, capture phase, for POINTER events:
     * Pad's press may come from a handler whose event has no pointerId to
     * capture with, window sees the stream wherever the finger wanders, and
     * capture means no stopPropagation between here and the surface can
     * starve the lens. */
    function startSession(ev, kind) {
      var same = sameSourceAs(ev);
      var F0 = pointOf(ev);
      var C0 = client();
      var before = { x: at.x, y: at.y };
      var from = null;
      try { from = getPoint({ clientX: C0.x, clientY: C0.y }); } catch (e) {}
      var s = session = {
        kind: kind,
        same: same,
        moved: false,
        move: function (e) {
          if (!same(e)) return;
          var F = { x: e.clientX, y: e.clientY };
          if (kind === 'mouse') { setClient(F.x, F.y); s.moved = true; return; }
          if (!s.moved && Math.hypot(F.x - F0.x, F.y - F0.y) < TAP_SLOP) return;
          s.moved = true;
          setClient(C0.x + (F.x - F0.x), C0.y + (F.y - F0.y));
          if (e.cancelable) e.preventDefault();
        },
        up: function (e) {
          if (!same(e)) return;
          if (kind === 'touch' && !s.moved) {      // a tap: move there, do not pick
            end();
            setClient(F0.x, F0.y);
            return;
          }
          end();
          commit();
        },
        cancel: function (e) {
          if (!same(e)) return;
          end();
          at = before; schedule();
        },
        // A second finger while a finger on the DRAWING aims is a pinch: the
        // aim is abandoned, and the lens rides the zoom on the point it was on.
        // (A second finger while the HANDLE is held is ignored: the handle
        // is unambiguous.)
        pinch: function () {
          end();
          pinchAt = from;
          follow();
        }
      };
      function end() {
        if (session !== s) return;
        session = null;
        window.removeEventListener('pointermove', s.move, true);
        window.removeEventListener('pointerup', s.up, true);
        window.removeEventListener('pointercancel', s.cancel, true);
      }
      s.end = end;
      window.addEventListener('pointermove', s.move, true);
      window.addEventListener('pointerup', s.up, true);
      window.addEventListener('pointercancel', s.cancel, true);
      if (kind === 'mouse') setClient(F0.x, F0.y);
    }

    /* While fingers are down after a pinch, keep the lens on its stage point
     * as the canvas zooms and pans under it; settle when the last one lifts. */
    function follow() {
      if (!armed || !pinchAt) { pinchAt = null; return; }
      setStage(pinchAt);
      if (Object.keys(fingers).length) requestAnimationFrame(follow);
      else pinchAt = null;
    }
    function fingerDown(e) {
      if (e.pointerType !== 'touch') return;
      fingers[e.pointerId] = true;
      if (session && session.kind === 'touch' && !session.same(e)) session.pinch();
    }
    function fingerUp(e) { if (e.pointerType === 'touch') delete fingers[e.pointerId]; }

    function commit() {
      if (!armed || !onPick || !at) return;
      var g;
      try { g = readGrid(); } catch (e) { return; }
      onPick(g.hex, g.stage.x, g.stage.y);
      disarm();
      say('Picked ' + nameOf(g.hex));
    }

    /* Call from the surface's press handler while armed. Returns true when it
     * took the press (the caller returns instead of falling back to its
     * one-shot tap sample). */
    function beginPick(ev) {
      if (!armed || !lensOn) return false;
      // Only the primary button aims: a right-click is swallowed, not a pick.
      if (ev.pointerType === 'mouse' && ev.button > 0) return true;
      if (session) {                                   // a second finger
        if (session.kind === 'touch' && !session.same(ev)) session.pinch();
        return true;
      }
      if (pinchAt) return true;                        // the pinch's fingers are still down
      build();
      var touch = ev.pointerType === 'touch' || /^touch/.test(ev.type || '');
      setMode(touch ? 'touch' : 'mouse');
      if (!at) { var p = pointOf(ev); setClient(p.x, p.y); }
      startSession(ev, touch ? 'touch' : 'mouse');
      return true;
    }

    /* ---- while armed: hover, keys, scroll ---------------------------------- */
    function onsurface(t) {
      if (!t || !surface) return false;
      if (t === surface || surface.contains(t)) return true;
      var host = surface.parentElement;
      return !!(host && t.tagName === 'CANVAS' && host.contains(t));
    }
    function hover(e) {
      if (session || !armed) return;
      if (e.pointerType === 'touch') return;
      setMode('mouse');
      if (onsurface(e.target)) setClient(e.clientX, e.clientY);
    }
    function editable(t) {
      return !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
    }
    function keys(e) {
      if (!armed || session || editable(e.target)) return;
      var step = e.shiftKey ? 10 : 1, d = null;
      if (e.key === 'ArrowLeft') d = [-step, 0];
      else if (e.key === 'ArrowRight') d = [step, 0];
      else if (e.key === 'ArrowUp') d = [0, -step];
      else if (e.key === 'ArrowDown') d = [0, step];
      if (d) { e.preventDefault(); e.stopPropagation(); nudge(d[0], d[1]); return; }
      if (e.key === 'Enter') {
        // Enter on Cancel cancels, and Enter on any other control the user
        // has tabbed to is that control's; anywhere else, Enter picks.
        var t = e.target;
        if (ui && t === ui.cancel) return;
        if (t && t !== button && !(ui && t === ui.pill) && t.closest && t.closest('button, a[href], [role="button"], summary')) return;
        e.preventDefault(); e.stopPropagation();
        commit();
      }
    }
    function reflow() { schedule(); }
    // A tap on the drawing while armed moves the lens; the click that follows
    // it must not reach the page's outside-click dismissers, which would close
    // the (veiled) colour drawer and, through its close hook, disarm the pick
    // the tap was aiming.
    function swallow(e) {
      if (!armed) return;
      if (onsurface(e.target) || (ui && (ui.lens.contains(e.target) || ui.handle.contains(e.target)))) {
        e.stopPropagation();
      }
    }

    function show() {
      build();
      snap = null;
      fingers = {};
      if (window.matchMedia && window.matchMedia('(hover: none)').matches) mode = 'touch';
      ui.text.textContent = copy();
      // Where the pen last was, else the middle of the part of the canvas on screen.
      setStage(last);
      // Focus to the pill: the control that armed the pick is veiled with its
      // drawer, and focus on a hidden control falls to <body>.
      var a = document.activeElement;
      returnFocus = (a && a !== document.body && !ui.pill.contains(a)) ? a : null;
      ui.pill.hidden = false;
      try { ui.pill.focus({ preventScroll: true }); } catch (e) {}
      // Once, politely: the armed state and how to get out of it.
      say(copy() + '. Arrow keys move the lens, Enter picks, Escape cancels.');
      window.addEventListener('pointermove', hover, true);
      window.addEventListener('pointerdown', fingerDown, true);
      window.addEventListener('pointerup', fingerUp, true);
      window.addEventListener('pointercancel', fingerUp, true);
      window.addEventListener('keydown', keys, true);
      window.addEventListener('click', swallow, true);
      window.addEventListener('scroll', reflow, true);
      window.addEventListener('resize', reflow);
    }
    function hide() {
      if (session) session.end();
      pinchAt = null;
      snap = null;
      window.removeEventListener('pointermove', hover, true);
      window.removeEventListener('pointerdown', fingerDown, true);
      window.removeEventListener('pointerup', fingerUp, true);
      window.removeEventListener('pointercancel', fingerUp, true);
      window.removeEventListener('keydown', keys, true);
      window.removeEventListener('click', swallow, true);
      window.removeEventListener('scroll', reflow, true);
      window.removeEventListener('resize', reflow);
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      at = null;
      if (live) live.textContent = '';
      if (!ui) return;
      var hadFocus = ui.pill.contains(document.activeElement);
      ui.lens.hidden = ui.handle.hidden = ui.mark.hidden = ui.chip.hidden = ui.pill.hidden = true;
      // Focus back once the surface has settled (the veil lifts in onChange;
      // a pick may close the drawer after that), and only if it is lost.
      var back = returnFocus;
      returnFocus = null;
      setTimeout(function () {
        var now = document.activeElement;
        if (armed || !(hadFocus || !now || now === document.body)) return;
        var to = [back, button, focusHome()].filter(visible)[0];
        if (to) { try { to.focus({ preventScroll: true }); } catch (e) {} }
      }, 0);
    }

    function apply() {
      if (button) {
        button.classList.toggle('picking', armed);
        // An armed mode indistinguishable from an unarmed one makes the next
        // canvas tap a surprise, and a class alone says nothing to a screen
        // reader.
        button.setAttribute('aria-pressed', armed ? 'true' : 'false');
      }
      // Inline, because setTool() writes surface.style.cursor inline and an
      // inline style beats any stylesheet rule. With the lens the lens IS the
      // cursor, so the pointer hides over the canvas; without it, a crosshair.
      if (surface) surface.style.cursor = armed ? (lensOn ? 'none' : 'crosshair') : idleCursor;
      onChange(armed);
    }

    function setArmed(v, via) {
      v = !!v;
      if (v === armed) return;
      armed = v;
      if (armed && via && via.pointerType) mode = via.pointerType === 'touch' ? 'touch' : 'mouse';
      // Disarming mid-drag (Escape, drawer closing) abandons the pick: the
      // lens goes and nothing commits.
      if (!armed) hide();
      apply();
      if (armed) { if (lensOn) show(); onArm(); }
    }

    function toggle(via) { setArmed(!armed, via); }
    function disarm() { setArmed(false); }

    /* Call from the surface's own pointer handler when a tap lands on the
     * canvas while armed and the lens is not wired. Returns true if it
     * consumed the event, so the caller can `return` rather than also
     * starting a stroke. */
    function handleTap(ev) {
      if (!armed) return false;
      try { onSample(ev); } catch (e) {}
      disarm();
      return true;
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && armed) { e.preventDefault(); disarm(); }
    });

    if (button) {
      button.addEventListener('click', function (e) {
        e.stopPropagation();
        toggle(e);
      });
    }

    apply();

    return {
      toggle: toggle,
      disarm: disarm,
      handleTap: handleTap,
      beginPick: beginPick,
      isArmed: function () { return armed; },
      // The drawing changed under an armed lens: read it again.
      refresh: function () { snap = null; if (armed) schedule(); },
      // For the harness and the owner's screenshots: where the lens reads
      // (client px) and what it would pick. Read-only.
      lensState: function () {
        if (!armed || !at || !ui) return null;
        var c = client(), p = getPoint({ clientX: c.x, clientY: c.y });
        return { x: c.x, y: c.y, hex: lastHex, mode: mode, stage: { x: p.x, y: p.y },
                 last: last ? { x: last.x, y: last.y } : null };
      }
    };
  }

  window.SkriblEyedropper = { create: create };
}());
