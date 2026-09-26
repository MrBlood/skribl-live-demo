/* The canvas magnifier: zoom, pan, the HUD, its grip, wheel and Space-drag.
 * ONE implementation for both editors (SK312-003, v315).
 *
 * WHY. This was the largest duplicate between Pad and Flip -- ~2,600 tokens a
 * side at 0.90 similarity by harness/tools/editordup.py -- and it could not be
 * merged while the two editors drew on different input models. #233 put Pad on
 * Pointer Events, as Flip; after that the copies differed only in the few
 * things a surface legitimately owns, which are OPTIONS below. Pad's copy was
 * the richer one and is the base: Pad is the product, Flip the developing one.
 *
 * WHAT A SURFACE OWNS (create()'s options):
 *   wrap                the element the zoom layer sits in (Pad .canvas-wrap,
 *                       Flip .flip-wrap); pans, the HUD and the grip live in it
 *   onPaint(zoom)       called on every repaint (Flip: crosshair while zoomed)
 *   panToast            a one-time "Scroll or Space-drag" toast the first time
 *                       a fine pointer zooms in (Pad)
 *   spaceOnlyWhenZoomed Space pans only while zoomed, because at 100% Space
 *                       belongs to someone else (Flip: play/stop). Pad owns
 *                       Space at any zoom.
 *   keyRegistry         {surface, label}: register the Space pan with the
 *                       shared KeyRegistry, scoped to "zoomed" (Flip)
 *   pinch               the two-finger gesture (v315, the second merge):
 *                       {surface, canStart(), onStart(), set(on)} -- the
 *                       element two fingers land on, whether a pinch may
 *                       begin now, how to abort the stroke the first finger
 *                       began, and the editor's own `pinching` flag, which
 *                       its stroke code reads.
 *
 * The editors only -- the player has no #zoomLayer and does not load this.
 * create() returns the object both editors already called ZoomView, with the
 * same methods; nothing that reads ZoomView changed.
 *
 * The grip still binds mouse/touch, exactly as both copies did: it is a small
 * drag on its own element, not a drawing surface, and moving it to pointer
 * events is its own change with its own verification.
 */
(function (global) {
  'use strict';

  function typingTarget(el) {
    return !!(el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable));
  }

  function create(opts) {
    opts = opts || {};
    var doc = global.document;
    var layer = doc.getElementById('zoomLayer');
    var hud = doc.getElementById('zoomHud');
    var wrap = opts.wrap;
    if (!layer || !hud || !wrap) return null;

    var MIN = 1, MAX = 4, STEP = 0.5;
    var zoom = 1, panX = 0, panY = 0;
    var magnifyOn = false;   // the magnifier toggle gates the whole feature
    var view;

    function wrapSize() {
      var r = wrap.getBoundingClientRect();
      return { w: r.width || 1, h: r.height || 1 };
    }
    function clampPan() {
      var s = wrapSize();
      panX = Math.min(0, Math.max(s.w * (1 - zoom), panX));
      panY = Math.min(0, Math.max(s.h * (1 - zoom), panY));
      if (zoom <= 1) { panX = 0; panY = 0; }
    }

    var finePointer = !!(global.matchMedia && global.matchMedia('(pointer: fine)').matches);
    var panHintShown = false;
    function maybePanHint() {
      if (!opts.panToast || panHintShown || !finePointer || zoom <= 1.001) return;
      panHintShown = true;
      if (typeof global.showToast === 'function') global.showToast('Scroll or Space-drag to move around', null);
    }

    function render(animate) {
      clampPan();
      layer.classList.toggle('zoom-anim', !!animate);
      layer.style.transform = zoom === 1 ? '' : 'translate(' + panX + 'px,' + panY + 'px) scale(' + zoom + ')';
      var val = doc.getElementById('zoomVal');
      if (val) val.textContent = Math.round(zoom * 100) + '%';
      hud.classList.toggle('zoomed', zoom > 1.001);
      var zin = doc.getElementById('zoomInBtn');
      var zout = doc.getElementById('zoomOutBtn');
      if (zin) zin.disabled = zoom >= MAX - 0.001;
      if (zout) zout.disabled = zoom <= MIN + 0.001;
      if (animate) setTimeout(function () { layer.classList.remove('zoom-anim'); }, 200);
      if (opts.onPaint) opts.onPaint(zoom);
      maybePanHint();
    }

    view = {
      isZoomed: function () { return zoom > 1.001; },
      enabled: function () { return magnifyOn; },
      enable: function () { if (!magnifyOn) setMagnify(true); },
      get: function () { return { zoom: zoom, panX: panX, panY: panY }; },
      zoomAt: function (factor, cx, cy) {
        var nz = Math.min(MAX, Math.max(MIN, zoom * factor));
        if (nz === zoom) return;
        var coordX = (cx - panX) / zoom, coordY = (cy - panY) / zoom;
        panX = cx - coordX * nz;
        panY = cy - coordY * nz;
        zoom = nz;
        render(false);
      },
      panBy: function (dx, dy) { panX += dx; panY += dy; render(false); },
      step: function (dir) {
        var s = wrapSize();
        var nz = Math.min(MAX, Math.max(MIN, zoom + dir * STEP));
        this.zoomAt(nz / zoom, s.w / 2, s.h / 2);
        render(true);
      },
      fit: function () { zoom = 1; panX = 0; panY = 0; render(true); },
      setPct: function (pct) {
        var s = wrapSize();
        var target = Math.min(MAX, Math.max(MIN, (pct || 0) / 100));
        this.zoomAt(target / zoom, s.w / 2, s.h / 2);
        render(true);
      },
      // Re-apply the pan limits after the wrap changed size (Flip calls it).
      reclamp: function () { render(false); }
    };

    function on(id, type, fn) { var el = doc.getElementById(id); if (el) el.addEventListener(type, fn); }
    on('zoomInBtn', 'click', function () { view.step(1); });
    on('zoomOutBtn', 'click', function () { view.step(-1); });
    on('zoomFitBtn', 'click', function () { view.fit(); });

    var magnifyBtn = doc.getElementById('magnifyBtn');
    function setMagnify(onState) {
      // The button zooms the CENTRE. Aiming needs scroll or Space-drag, so say
      // so once, the first time magnify is enabled.
      if (onState && global.SkriblHints) {
        global.SkriblHints.show('magnify-pan',
          'Zoomed in. Scroll — or hold Space and drag — to move to the part you want.');
      }
      magnifyOn = onState;
      hud.hidden = !onState;
      if (magnifyBtn) {
        magnifyBtn.classList.toggle('active', onState);
        magnifyBtn.setAttribute('aria-pressed', onState ? 'true' : 'false');
      }
      if (!onState) view.fit();     // back to 100% when the controls are hidden
    }
    if (magnifyBtn) magnifyBtn.addEventListener('click', function () { setMagnify(!magnifyOn); });
    global._skriblRevealZoomHud = function () { if (!magnifyOn) setMagnify(true); };

    // Click the % to type an exact zoom. A text input at 16px (styles.css,
    // .zoom-val-input) so iOS does not magnify the page -- verify_a11y 11b.
    var valEl = doc.getElementById('zoomVal');
    if (valEl) {
      valEl.title = 'Click to type a zoom %';
      valEl.addEventListener('click', function () {
        if (valEl.querySelector('input')) return;               // already editing
        var cur = Math.round(zoom * 100);
        valEl.textContent = '';
        var inp = doc.createElement('input');
        inp.type = 'text';
        inp.inputMode = 'numeric';
        inp.setAttribute('enterkeyhint', 'done');
        inp.maxLength = 4;
        inp.className = 'zoom-val-input';
        inp.value = String(cur);
        valEl.appendChild(inp);
        var backdrop = doc.createElement('div');
        backdrop.className = 'zoom-edit-backdrop';
        wrap.appendChild(backdrop);
        inp.focus();
        inp.select();
        var done = false;
        function commit(apply) {
          if (done) return;
          done = true;
          if (backdrop.parentNode) backdrop.remove();
          var n = apply ? parseInt(inp.value, 10) : NaN;
          if (!isNaN(n)) {
            view.setPct(n);            // render() rewrites the label, dropping the input
          } else {
            if (inp.parentNode) inp.remove();
            render(false);             // restore the "N%" label unchanged
          }
        }
        backdrop.addEventListener('pointerdown', function (e) { e.preventDefault(); commit(true); });
        inp.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') { e.preventDefault(); commit(true); }
          else if (e.key === 'Escape') { e.preventDefault(); commit(false); }
        });
        inp.addEventListener('blur', function () { commit(true); });
      });
    }

    global.addEventListener('resize', function () { if (zoom > 1) render(false); });

    // ---- the grip: drag the HUD, dock it to the nearest corner --------------
    var grip = doc.getElementById('zoomGrip');
    var snapEl = null, dragging = false, grabDX = 0, grabDY = 0;
    function corners() {
      var r = wrap.getBoundingClientRect();
      var pw = hud.offsetWidth, ph = hud.offsetHeight, m = 12;
      return {
        tl: { key: 'tl', x: m, y: m },
        tr: { key: 'tr', x: r.width - pw - m, y: m },
        bl: { key: 'bl', x: m, y: r.height - ph - m },
        br: { key: 'br', x: r.width - pw - m, y: r.height - ph - m }
      };
    }
    function nearestCorner(x, y) {
      var c = corners(), best = null, bd = Infinity;
      for (var k in c) {
        var d = Math.hypot(x - c[k].x, y - c[k].y);
        if (d < bd) { bd = d; best = c[k]; }
      }
      return best;
    }
    function pointer(ev) {
      var t = global.SkriblEventPoint.at(ev);
      return { x: t.clientX, y: t.clientY };
    }
    function gripStart(ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var r = hud.getBoundingClientRect(), wrapR = wrap.getBoundingClientRect(), p = pointer(ev);
      grabDX = p.x - r.left;
      grabDY = p.y - r.top;
      dragging = true;
      hud.classList.add('dragging');
      hud.style.right = 'auto';
      hud.style.bottom = 'auto';
      hud.style.left = (r.left - wrapR.left) + 'px';
      hud.style.top = (r.top - wrapR.top) + 'px';
      snapEl = doc.createElement('div');
      snapEl.className = 'zoom-snap';
      snapEl.style.height = hud.offsetHeight + 'px';
      wrap.appendChild(snapEl);
      if (ev.type === 'mousedown') {
        global.addEventListener('mousemove', gripMove);
        global.addEventListener('mouseup', gripEnd);
      } else {
        global.addEventListener('touchmove', gripMove, { passive: false });
        global.addEventListener('touchend', gripEnd);
        global.addEventListener('touchcancel', gripEnd);
      }
    }
    function gripMove(ev) {
      if (!dragging) return;
      ev.preventDefault();
      var wrapR = wrap.getBoundingClientRect(), p = pointer(ev);
      var x = Math.max(0, Math.min(wrapR.width - hud.offsetWidth, p.x - wrapR.left - grabDX));
      var y = Math.max(0, Math.min(wrapR.height - hud.offsetHeight, p.y - wrapR.top - grabDY));
      hud.style.left = x + 'px';
      hud.style.top = y + 'px';
      var near = nearestCorner(x, y);
      if (snapEl) { snapEl.style.left = near.x + 'px'; snapEl.style.top = near.y + 'px'; }
    }
    function gripEnd() {
      if (!dragging) return;
      dragging = false;
      hud.classList.remove('dragging');
      var x = parseFloat(hud.style.left) || 0, y = parseFloat(hud.style.top) || 0;
      var near = nearestCorner(x, y);
      hud.style.left = ''; hud.style.top = ''; hud.style.right = ''; hud.style.bottom = '';
      hud.setAttribute('data-corner', near.key);
      if (snapEl) { snapEl.remove(); snapEl = null; }
      global.removeEventListener('mousemove', gripMove);
      global.removeEventListener('mouseup', gripEnd);
      global.removeEventListener('touchmove', gripMove);
      global.removeEventListener('touchend', gripEnd);
      global.removeEventListener('touchcancel', gripEnd);
    }
    if (grip) {
      grip.addEventListener('mousedown', gripStart);
      grip.addEventListener('touchstart', gripStart, { passive: false });
    }

    // ---- wheel pans while zoomed (Shift turns vertical into horizontal) -----
    wrap.addEventListener('wheel', function (e) {
      if (zoom <= 1) return;
      e.preventDefault();
      var dx = e.deltaX, dy = e.deltaY;
      if (e.shiftKey && dx === 0) { dx = dy; dy = 0; }
      panX -= dx; panY -= dy;
      render(false);
    }, { passive: false });

    // ---- hold Space and drag to grab-pan (desktop) ---------------------------
    var spaceHeld = false, spaceDragging = false, lastX = 0, lastY = 0;
    function spacePans() { return !opts.spaceOnlyWhenZoomed || zoom > 1.001; }
    if (opts.keyRegistry && global.KeyRegistry) {
      global.KeyRegistry.register({ surface: opts.keyRegistry.surface, label: opts.keyRegistry.label,
        keys: ['Space'], scope: function () { return view.isZoomed(); } });
    }
    global.addEventListener('keydown', function (e) {
      if (e.code === 'Space' && !typingTarget(e.target)) {
        spaceHeld = true;
        if (spacePans()) {
          wrap.style.cursor = spaceDragging ? 'grabbing' : 'grab';
          e.preventDefault();               // no page scroll / button activation
        }
      }
    });
    global.addEventListener('keyup', function (e) {
      if (e.code === 'Space') { spaceHeld = false; spaceDragging = false; wrap.style.cursor = ''; }
    });
    // Capture phase, so a Space-drag claims the mousedown. The stroke starts on
    // pointerdown (before this) and refuses on its own while Space is held --
    // via _skriblSpaceHeld below -- which is what keeps it from drawing.
    wrap.addEventListener('mousedown', function (e) {
      if (spaceHeld && spacePans()) {
        spaceDragging = true; lastX = e.clientX; lastY = e.clientY;
        wrap.style.cursor = 'grabbing';
        e.preventDefault(); e.stopPropagation();
      }
    }, true);
    global._skriblSpaceHeld = function () { return spaceHeld; };
    global.addEventListener('mousemove', function (e) {
      if (!spaceDragging) return;
      panX += e.clientX - lastX; panY += e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      render(false);
    });
    global.addEventListener('mouseup', function () {
      if (spaceDragging) { spaceDragging = false; wrap.style.cursor = spaceHeld ? 'grab' : ''; }
    });

    // ---- the pinch: two fingers on the drawing magnify and pan it ----------
    // Two fingers ON THE SURFACE (targetTouches -- a thumb resting on the
    // header is not the second finger), remembered by identifier so a third
    // contact cannot take a slot, and ended as soon as either of ITS OWN
    // fingers lifts. A single remaining finger does not resume drawing; the
    // person lifts and taps again. lib/pinchgesture.js holds the pair logic.
    var P = opts.pinch, pinch = null;
    function touchMid(a, b) {
      var r = wrap.getBoundingClientRect();
      return { x: (a.clientX + b.clientX) / 2 - r.left, y: (a.clientY + b.clientY) / 2 - r.top };
    }
    function touchDist(a, b) { return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); }
    view.beginPinch = function (e) {
      if (!P || (P.canStart && !P.canStart())) return;
      var own = global.SkriblPinch && global.SkriblPinch.own(e);
      if (!own || own.length < 2) return;
      if (e.cancelable) e.preventDefault();
      // The magnifier comes on with the pinch, HUD and all -- a pinch should
      // never feel dead -- and only once it is known to BE a pinch.
      view.enable();
      if (P.onStart) P.onStart();
      if (P.set) P.set(true);
      var t0 = own[0], t1 = own[1];
      pinch = { ids: [t0.identifier, t1.identifier], lastDist: touchDist(t0, t1), lastMid: touchMid(t0, t1) };
    };
    if (P && P.surface) {
      P.surface.addEventListener('touchstart', function (e) {
        var t = e.targetTouches || e.touches;
        if (t && t.length >= 2) view.beginPinch(e);
      }, { passive: false });
      global.addEventListener('touchmove', function (e) {
        if (!pinch) return;
        var pair = global.SkriblPinch.pair(e, pinch.ids);
        if (!pair) return;
        if (e.cancelable) e.preventDefault();
        var dist = touchDist(pair[0], pair[1]), mid = touchMid(pair[0], pair[1]);
        if (pinch.lastDist > 0) view.zoomAt(dist / pinch.lastDist, mid.x, mid.y);   // about the midpoint
        view.panBy(mid.x - pinch.lastMid.x, mid.y - pinch.lastMid.y);               // two-finger pan
        pinch.lastDist = dist;
        pinch.lastMid = mid;
      }, { passive: false });
      var endPinch = function (e) {
        if (!pinch) return;
        if (global.SkriblPinch.pair(e, pinch.ids)) return;
        pinch = null;
        if (P.set) P.set(false);
      };
      global.addEventListener('touchend', endPinch);
      global.addEventListener('touchcancel', endPinch);
    }

    render(false);
    return view;
  }

  global.SkriblCanvasZoom = { create: create };
})(window);
