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
  /* A control reached BY KEYBOARD owns Space: a switch toggles, a button
   * presses (WAI-ARIA). Only a keyboard focus -- :focus-visible -- so a button
   * that kept focus after a mouse click still lets Space grab-pan (and, on
   * Flip, play). Shared with flip.js's Space-to-play as SkriblCanvasZoom.ownsSpace. */
  function ownsSpace(el) {
    if (!el || !el.matches) return false;
    try {
      return el.matches('button, [role=switch], [role=tab], [role=button], summary, a[href]') && el.matches(':focus-visible');
    } catch (e) { return false; }
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
    on('zoomFitBtn', 'click', function () {
      // Where the Magnify button is not on screen (a phone), Fit is also how the
      // panel goes away: back to 100%, and the controls with it.
      if (magnifyOn && !buttonShown()) setMagnify(false); else view.fit();
    });

    var magnifyBtn = doc.getElementById('magnifyBtn');
    // THE PANEL BELONGS TO THE PINCH WHERE THERE IS NO BUTTON (owner's iPhone:
    // "how to disappear the magnifier?"). A pinch turns magnify on, HUD and
    // all, but the only control that turned it OFF was #magnifyBtn -- hidden on
    // phones -- so one pinch, or a stray second finger while drawing, left the
    // panel over the drawing for the rest of the session. Without the button,
    // being back at 100% is what ends it: Fit, or a pinch back out.
    function buttonShown() { return !!(magnifyBtn && magnifyBtn.offsetParent !== null); }
    function setMagnify(onState) {
      // The button zooms the CENTRE. Aiming needs scroll or Space-drag, so say
      // so once, the first time magnify is enabled.
      if (onState && global.SkriblHints) {
        global.SkriblHints.show('magnify-pan',
          'Zoomed in. Scroll — or hold Space and drag — to move to the part you want.');
      }
      magnifyOn = onState;
      hud.hidden = !onState;
      if (onState) keepOnScreen();       // the screen may have turned since it was put away
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

    // ---- the grip: drag the HUD anywhere on the screen ---------------------
    // Owner: "It should be draggable anywhere on screen (example phone size
    // there's room to drag it outside the canvas)"; the magnifier mock, "All
    // yes". It docked to the page's four corners, so on a phone it always sat
    // on the drawing. Dropped, it stays exactly there, whole on screen, and
    // is there again next time (each editor its own spot). Until it is first
    // moved it sits in the page's corner as before. To be free of the page
    // it leaves it for the body: a fixed box inside the wrap would scroll
    // and clip with it.
    var grip = doc.getElementById('zoomGrip');
    var dragging = false, grabDX = 0, grabDY = 0, M = 4;
    var KEY = 'skribl.zoomhud.' + (wrap.classList.contains('flip-wrap') ? 'flip' : 'pad') + '.v1';
    function inside(x, y) {
      return { x: Math.max(M, Math.min(global.innerWidth - hud.offsetWidth - M, x)),
               y: Math.max(M, Math.min(global.innerHeight - hud.offsetHeight - M, y)) };
    }
    function free(x, y) {
      if (hud.parentNode !== doc.body) doc.body.appendChild(hud);
      hud.classList.add('zoom-free');
      var at = inside(x, y);
      hud.style.left = at.x + 'px';
      hud.style.top = at.y + 'px';
      hud.style.right = 'auto';
      hud.style.bottom = 'auto';
      return at;
    }
    function saved() {
      try { var v = JSON.parse(global.localStorage.getItem(KEY) || 'null'); return v && isFinite(v.x) && isFinite(v.y) ? v : null; }
      catch (e) { return null; }
    }
    function keepOnScreen() {
      if (!hud.classList.contains('zoom-free') || hud.hidden) return;
      free(parseFloat(hud.style.left) || 0, parseFloat(hud.style.top) || 0);
    }
    var spot = saved();
    if (spot) free(spot.x, spot.y);
    global.addEventListener('resize', keepOnScreen);
    function pointer(ev) {
      var t = global.SkriblEventPoint.at(ev);
      return { x: t.clientX, y: t.clientY };
    }
    function gripStart(ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var r = hud.getBoundingClientRect(), p = pointer(ev);
      grabDX = p.x - r.left;
      grabDY = p.y - r.top;
      dragging = true;
      hud.classList.add('dragging');
      free(r.left, r.top);
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
      var p = pointer(ev);
      free(p.x - grabDX, p.y - grabDY);
    }
    function gripEnd() {
      if (!dragging) return;
      dragging = false;
      hud.classList.remove('dragging');
      var at = { x: parseFloat(hud.style.left) || 0, y: parseFloat(hud.style.top) || 0 };
      try { global.localStorage.setItem(KEY, JSON.stringify(at)); } catch (e) {}
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
    // ONLY WHILE ZOOMED, on both editors: at 100% Space plays and stops (Flip
    // always, the Pad since the one Play/Stop round, owner: "all yes"), and
    // there is nothing to pan. This was an option Flip set and the Pad did not.
    var spaceHeld = false, spaceDragging = false, lastX = 0, lastY = 0;
    function spacePans() { return zoom > 1.001; }
    if (opts.keyRegistry && global.KeyRegistry) {
      global.KeyRegistry.register({ surface: opts.keyRegistry.surface, label: opts.keyRegistry.label,
        keys: ['Space'], scope: function () { return view.isZoomed(); } });
    }
    global.addEventListener('keydown', function (e) {
      if (e.code === 'Space' && !typingTarget(e.target) && !ownsSpace(e.target)) {
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
        if (magnifyOn && zoom <= 1.001 && !buttonShown()) setMagnify(false);
      };
      global.addEventListener('touchend', endPinch);
      global.addEventListener('touchcancel', endPinch);
    }

    render(false);
    return view;
  }

  global.SkriblCanvasZoom = { create: create, ownsSpace: ownsSpace };
})(window);
