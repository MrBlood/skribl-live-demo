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
 *   EDGES: the lens stays inside the viewport. Against a side it slides
 *   inward; against the top it slides SIDEWAYS rather than down, because down
 *   is where the hand is. When that carries it off the point altogether, a
 *   small two-tone mark stays on the true point, so what is read is still
 *   shown where it is.
 *
 *   Escape, Cancel and tapping the eyedropper again abandon without picking;
 *   pointercancel abandons the drag in progress and puts the lens back.
 *
 * The lens draws from the surface's COMPOSITED stage (padArtwork /
 * paintArtwork via `artwork`), and the pick reads the centre cell of the very
 * grid the lens draws, so what it shows and what it picks cannot disagree —
 * photo, background colour and strokes included, onion skin and guides
 * excluded for exactly the reason sampling excludes them.
 */
(function () {
  'use strict';

  /* Geometry shared with the .eyedropper-lens CSS (116px): keep in step. */
  var LENS = 116, R = LENS / 2;
  var CELLS = 11, CELL = 10;       // 11 screen px across, each drawn 10x
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

  function create(opts) {
    opts = opts || {};
    var button = opts.button || null;
    var surface = opts.surface || null;             // the drawing canvas
    var idleCursor = opts.idleCursor || '';         // Pad restores '', Flip 'none'
    var onSample = typeof opts.onSample === 'function' ? opts.onSample : function () {};
    var onArm = typeof opts.onArm === 'function' ? opts.onArm : function () {};
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
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
    var ui = null;          // lens, handle, mark, chip, pill, live region: built on first arm
    var at = null;          // the lens point, as an offset (CSS px) from the surface's top-left
    var session = null;     // the active drag, or null
    var raf = 0;
    var last = null;        // where the pen last touched, in STAGE coordinates
    var lastHex = null;

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
      var pill = el('div', 'eyedropper-pill');
      pill.hidden = true;
      var text = el('span', 'eyedropper-pill-text', pill);
      var cancel = el('button', 'eyedropper-pill-cancel', pill);
      cancel.type = 'button';
      cancel.textContent = 'Cancel';
      cancel.setAttribute('aria-label', 'Cancel colour pick');
      // A fixed element is placed against its containing block, which is the
      // viewport only when no ancestor makes itself one — and on both editors
      // something does: on a 1400px desktop everything fixed here landed 10px
      // right of where it was put. So positions are written relative to this
      // probe's measured origin rather than assumed to be client coordinates.
      var probe = el('div', 'eyedropper-origin');
      probe.setAttribute('aria-hidden', 'true');
      var live = el('div', 'eyedropper-live');
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      [probe, lens, handle, mark, chip, pill, live].forEach(function (n) { document.body.appendChild(n); });

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
             chip: chip, pill: pill, text: text, cancel: cancel, live: live };
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

    /* The grid, read from the composited stage: cell (i, j) is the stage pixel
     * under screen point (C.x + i, C.y + j). One getImageData for all 121. */
    function readGrid() {
      var C = client();
      var h = (CELLS - 1) / 2;
      var art = artwork();
      var adpr = dprOf();
      var p0 = getPoint({ clientX: C.x, clientY: C.y });
      var p1 = getPoint({ clientX: C.x + 100, clientY: C.y + 100 });
      var kx = (p1.x - p0.x) / 100, ky = (p1.y - p0.y) / 100;
      var xs = [], ys = [];
      for (var i = -h; i <= h; i++) {
        xs.push(Math.floor((p0.x + i * kx) * adpr));
        ys.push(Math.floor((p0.y + i * ky) * adpr));
      }
      var x0 = xs[0], y0 = ys[0], w = xs[CELLS - 1] - x0 + 1, hh = ys[CELLS - 1] - y0 + 1;
      var bg = bgOf();
      var data = null;
      try { data = art.getContext('2d').getImageData(x0, y0, Math.max(w, 1), Math.max(hh, 1)).data; } catch (e) {}
      var cells = [];
      for (var jy = 0; jy < CELLS; jy++) {
        for (var ix = 0; ix < CELLS; ix++) {
          var X = xs[ix], Y = ys[jy], c = bg;
          if (data && X >= 0 && Y >= 0 && X < art.width && Y < art.height) {
            var k = ((Y - y0) * w + (X - x0)) * 4;
            if (data[k + 3] >= 10) c = hexOf(data, k);
          }
          cells.push(c);
        }
      }
      return { cells: cells, hex: cells[(CELLS * CELLS - 1) / 2], stage: p0 };
    }

    function drawLens(g) {
      var cv = ui.cv, ctx = ui.ctx;
      var d = window.devicePixelRatio || 1;
      var px = Math.round(LENS * d);
      if (cv.width !== px) { cv.width = px; cv.height = px; }
      ctx.setTransform(d, 0, 0, d, 0, 0);
      ctx.clearRect(0, 0, LENS, LENS);
      ctx.save();
      ctx.beginPath(); ctx.arc(R, R, WINDOW_R, 0, Math.PI * 2); ctx.clip();
      var o = R - CELL / 2 - ((CELLS - 1) / 2) * CELL;   // left/top of cell 0
      for (var j = 0; j < CELLS; j++) for (var i = 0; i < CELLS; i++) {
        ctx.fillStyle = g.cells[j * CELLS + i];
        ctx.fillRect(o + i * CELL, o + j * CELL, CELL, CELL);
      }
      ctx.strokeStyle = 'rgba(128,128,128,0.28)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (var n = 0; n <= CELLS; n++) {
        var v = o + n * CELL;
        ctx.moveTo(v, 0); ctx.lineTo(v, LENS);
        ctx.moveTo(0, v); ctx.lineTo(LENS, v);
      }
      ctx.stroke();
      // The reticle on the centre cell: dark under white, so it reads on any ink.
      var c0 = R - CELL / 2;
      ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(0,0,0,0.85)';
      ctx.strokeRect(c0, c0, CELL, CELL);
      ctx.lineWidth = 1.5; ctx.strokeStyle = '#ffffff';
      ctx.strokeRect(c0, c0, CELL, CELL);
      ctx.restore();
      // The split ring: top = what a pick takes, bottom = the pen now.
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
      drawLens(g);
      var P = client();
      var L = place(P);
      var u = ui;
      var o = u.probe.getBoundingClientRect();
      var ox = o.left, oy = o.top;
      u.lens.style.left = (L.x - R - ox) + 'px';
      u.lens.style.top = (L.y - R - oy) + 'px';
      u.lens.dataset.hex = g.hex;
      u.lens.hidden = false;
      // The mark shows only when the true point is off the lens: under it, the
      // reticle already says which cell is read, and a second target on the
      // grid would be two answers to one question.
      var displaced = Math.hypot(L.x - P.x, L.y - P.y) > R - 2;
      u.mark.hidden = !displaced;
      if (displaced) { u.mark.style.left = (P.x - ox) + 'px'; u.mark.style.top = (P.y - oy) + 'px'; }
      u.handle.hidden = mode !== 'touch';
      u.handle.style.left = (L.x - ox) + 'px';
      u.handle.style.top = (L.y + R + HANDLE_GAP + HANDLE_H / 2 - oy) + 'px';
      u.chip.textContent = g.hex.toUpperCase();
      u.chip.hidden = false;
      var ch = u.chip.offsetHeight || 22;
      var ct = L.y - R - 8 - ch;
      if (ct < MARGIN) ct = L.y + R + (mode === 'touch' ? HANDLE_GAP + HANDLE_H + 8 : 8);
      u.chip.style.left = (L.x - ox) + 'px';
      u.chip.style.top = (ct - oy) + 'px';
      placePill(L);
    }
    function schedule() { if (!raf) raf = requestAnimationFrame(render); }

    function placePill(L) {
      var u = ui, r = rect();
      u.pill.hidden = false;
      var pw = u.pill.offsetWidth, ph = u.pill.offsetHeight;
      var W = window.innerWidth;
      var cx = Math.min(Math.max(r.left + r.width / 2, pw / 2 + 8), W - pw / 2 - 8);
      var top = Math.max(r.top, 0) + 10;
      var o = u.probe.getBoundingClientRect();
      u.pill.style.left = (cx - o.left) + 'px';
      u.pill.style.top = (top - o.top) + 'px';
      // When the lens is up there too, the pill steps back rather than sit
      // over the thing being aimed at.
      if (L) {
        var nx = Math.max(cx - pw / 2, Math.min(L.x, cx + pw / 2));
        var ny = Math.max(top, Math.min(L.y, top + ph));
        var near = (L.x - nx) * (L.x - nx) + (L.y - ny) * (L.y - ny) < (R + 4) * (R + 4);
        u.pill.classList.toggle('eyedropper-pill-under', near);
      }
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
      var s = session = {
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

    function commit() {
      if (!armed || !onPick || !at) return;
      var g;
      try { g = readGrid(); } catch (e) { return; }
      onPick(g.hex, g.stage.x, g.stage.y);
      disarm();
    }

    /* Call from the surface's press handler while armed. Returns true when it
     * took the press (the caller returns instead of falling back to its
     * one-shot tap sample). */
    function beginPick(ev) {
      if (!armed || !lensOn) return false;
      if (session) return true;                       // second finger: ignore
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
        if (ui && ui.pill.contains(e.target)) return;   // Enter on Cancel cancels
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
      var r = rect();
      var W = window.innerWidth, H = window.innerHeight;
      // Where the pen last was, else the middle of the part of the canvas on screen.
      var vx0 = Math.max(r.left, 0), vx1 = Math.min(r.right, W);
      var vy0 = Math.max(r.top, 0), vy1 = Math.min(r.bottom, H);
      var x = (vx0 + vx1) / 2, y = (vy0 + vy1) / 2;
      if (last) {
        var p0 = getPoint({ clientX: r.left, clientY: r.top });
        var p1 = getPoint({ clientX: r.left + 100, clientY: r.top + 100 });
        var kx = (p1.x - p0.x) / 100, ky = (p1.y - p0.y) / 100;
        if (kx > 0 && ky > 0) { x = r.left + (last.x - p0.x) / kx; y = r.top + (last.y - p0.y) / ky; }
      }
      x = Math.min(Math.max(x, vx0), Math.max(vx1 - 1, vx0));
      y = Math.min(Math.max(y, vy0), Math.max(vy1 - 1, vy0));
      if (window.matchMedia && window.matchMedia('(hover: none)').matches) mode = 'touch';
      ui.text.textContent = copy();
      setClient(x, y);
      placePill(null);
      // Once, politely: the armed state and how to get out of it.
      var say = copy() + '. Arrow keys move the lens, Enter picks, Escape cancels.';
      ui.live.textContent = '';
      setTimeout(function () { if (armed && ui) ui.live.textContent = say; }, 60);
      window.addEventListener('pointermove', hover, true);
      window.addEventListener('keydown', keys, true);
      window.addEventListener('click', swallow, true);
      window.addEventListener('scroll', reflow, true);
      window.addEventListener('resize', reflow);
    }
    function hide() {
      if (session) session.end();
      window.removeEventListener('pointermove', hover, true);
      window.removeEventListener('keydown', keys, true);
      window.removeEventListener('click', swallow, true);
      window.removeEventListener('scroll', reflow, true);
      window.removeEventListener('resize', reflow);
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      at = null;
      if (!ui) return;
      ui.lens.hidden = ui.handle.hidden = ui.mark.hidden = ui.chip.hidden = ui.pill.hidden = true;
      ui.live.textContent = '';
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
