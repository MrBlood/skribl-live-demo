/* The draw drawer's four tiles -- Brush, Size, Feel, Eraser -- one
 * implementation, both editors.
 *
 * WHY. Under the colour the drawer was six rows of labelled pills on Pad and
 * seven on Flip, and on a phone they hid behind a "Brush, smoothing & more"
 * button. The owner asked for the drawer to be as visual, fun and kind as the
 * ⋯ menu had become, and picked this from four mocked shapes ("In place",
 * Joined): four tiles, each a little picture of what it holds now, painted in
 * the pen's own colour; a tap opens that tile's choices right under it, joined
 * to it as one shape, and the same tile closes them. No chevron and no back
 * button -- the owner found both easy to forget and cheap-looking.
 *
 * WHAT THIS OWNS: which tile is open, the tiles' pictures and words, the
 * pictures on the choices, and the four quick sizes. WHAT IT DOES NOT: any
 * setting. Every choice inside is the control it always was -- brushes.js,
 * smoothing.js, pressure.js, erasersize.js, the editors' own size and opacity
 * handlers -- so this only listens, and paints what it hears. The quick sizes
 * set the size slider and fire its own input event, so the editor's handler
 * does the rest exactly as a drag would.
 *
 * THE PEN'S COLOUR is read where lib/recolor.js already keeps it for the
 * Recolor button (--recolor-ink on its drawing, kept in step on both editors
 * by every colour change), and a change there repaints the pictures. A colour
 * too close to the tile's own ground to see -- white ink on the light
 * theme's white tile -- is drawn with a soft edge under it, the way the
 * Recolor button handles a pale ink.
 *
 * THE DETENT. Opening a tile tells the panel (a 'drawtile' event), and
 * lib/drawerdetent.js answers on a phone: the drawer goes to full and brings
 * the open choices on screen. A drawer hidden by any route closes its tile, so
 * every open starts with four tiles, predictable.
 *
 * KIND TRANSITIONS. The choices unfold and fold away again (Web Animations) before they
 * leave, and the page never jumps as they go (SkriblDrawerDetent.shrinkGently).
 * Reduced motion: no fold, nothing moves.
 */
(function () {
  'use strict';

  var BR = { pen: { w: 1, a: 1 }, marker: { w: 2.2, a: 0.7 }, pencil: { w: 0.55, a: 0.85 }, airbrush: { w: 2.6, a: 0.28 } };
  var JITTER = { off: 2.4, low: 1, high: 0 };
  var PANEL_ID = { brush: 'dpBrush', size: 'dpSize', feel: 'dpFeel', eraser: 'dpEraser' };

  function still() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function rgbOf(s) {
    s = (s || '').trim();
    var m = /^#([0-9a-f]{6})$/i.exec(s);
    if (m) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)];
    m = /rgba?\(([^)]+)\)/.exec(s);
    if (m) return m[1].split(',').slice(0, 3).map(function (v) { return parseFloat(v) || 0; });
    return null;
  }
  function lum(c) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }

  function attach(panel) {
    if (!panel) return;
    var root = panel.querySelector('.dp');
    if (!root || root.__dpAttached) return;
    root.__dpAttached = true;
    var tiles = [].slice.call(root.querySelectorAll('.dp-tile'));
    var size = panel.querySelector('#brushSizeRange, #size');
    var opacity = panel.querySelector('#opacitySlider');
    var inkEl = panel.querySelector('#recolorBtn .rc-inks');
    var open = null, folding = null;

    function pick(sel) { var b = panel.querySelector(sel); return b || null; }
    function state() {
      var b = pick('#brushSeg .active'), s = pick('#smoothSeg .active'), p = pick('#pressureSeg .active'), e = pick('#eraserSeg .active');
      return {
        brush: (b && b.getAttribute('data-brush')) || 'pen',
        brushName: b ? b.querySelector('.dp-k').textContent : 'Pen',
        size: size ? +size.value : 5,
        opacity: opacity ? +opacity.value : 100,
        smooth: (s && s.getAttribute('data-smooth')) || 'off',
        pressure: (p && p.getAttribute('data-pressure')) || 'on',
        eraser: e ? +e.getAttribute('data-eraser') : 3
      };
    }
    function ink() {
      var v = inkEl ? getComputedStyle(inkEl).getPropertyValue('--recolor-ink') : '';
      return rgbOf(v) ? v.trim() : '#7c5cff';
    }

    // ---------- the painter: one wave, drawn the way each brush draws
    function prep(c) {
      var d = Math.min(3, window.devicePixelRatio || 1), w = c.clientWidth, h = c.clientHeight;
      if (!w || !h) return null;
      var W = Math.round(w * d), H = Math.round(h * d);
      if (c.width !== W) c.width = W;
      if (c.height !== H) c.height = H;
      var x = c.getContext('2d');
      x.setTransform(1, 0, 0, 1, 0, 0);
      x.clearRect(0, 0, W, H);
      x.setTransform(d, 0, 0, d, 0, 0);
      return { x: x, w: w, h: h };
    }
    function groundOf(c) {
      for (var el = c; el && el.nodeType === 1; el = el.parentElement) {
        var bg = rgbOf(getComputedStyle(el).backgroundColor);
        var a = /rgba\([^)]*,\s*([\d.]+)\)/.exec(getComputedStyle(el).backgroundColor);
        if (bg && !(a && parseFloat(a[1]) < 0.5)) return bg;
      }
      return [255, 255, 255];
    }
    function seg(x, a, b, w, alpha, brush, color, grain) {
      x.save();
      x.strokeStyle = color; x.lineCap = 'round'; x.lineJoin = 'round';
      x.globalAlpha = alpha * (brush === 'pencil' ? (0.55 + 0.45 * grain) : 1);
      if (brush === 'airbrush') { x.shadowColor = color; x.shadowBlur = w * 1.1; }
      x.lineWidth = Math.max(0.7, w);
      x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(b[0], b[1]); x.stroke();
      x.restore();
    }
    function wave(c, o, S, color, pale) {
      var g = prep(c); if (!g) return;
      var x = g.x, w = g.w, h = g.h, brush = o.brush || S.brush, sz = o.size || 4, n = 64, pts = [], i;
      for (i = 0; i <= n; i++) {
        var t = i / n, y = h / 2 + Math.sin(t * Math.PI * 2) * h * (o.amp || 0.22);
        if (o.jitter) y += (Math.sin(i * 7.3) + Math.sin(i * 3.1 + 1)) * o.jitter;
        pts.push([8 + t * (w - 16), y, t]);
      }
      function width(i) {
        var t = pts[i][2];
        var k = o.taper === 'press' ? (0.12 + 1.5 * Math.pow(Math.sin(Math.PI * t), 2))
          : o.taper === 'even' ? 1 : (brush === 'pen' ? 0.6 + 0.4 * Math.sin(Math.PI * t) : 1);
        return BR[brush].w * sz * k;
      }
      // A pale ink on a pale tile: a soft edge first, so the line still reads.
      if (pale) for (i = 1; i < pts.length; i++) seg(x, pts[i - 1], pts[i], width(i) + 2, 0.35, 'pen', pale, 1);
      for (i = 1; i < pts.length; i++) {
        seg(x, pts[i - 1], pts[i], width(i), BR[brush].a * (o.alpha == null ? 1 : o.alpha), brush, color, Math.pow(Math.sin(i * 2.7), 2));
      }
    }
    function dots(c, S, color, pale) {
      var g = prep(c); if (!g) return;
      var x = g.x, w = g.w, h = g.h;
      [[w * 0.2, 1.6, 0.35], [w * 0.8, Math.min(h / 2 - 1, 9), 0.35], [w * 0.5, Math.min(h / 2 - 1, Math.max(2, S.size / 2 + 1.5)), 1]].forEach(function (d) {
        if (pale) { x.globalAlpha = 0.35; x.fillStyle = pale; x.beginPath(); x.arc(d[0], h / 2, d[1] + 1, 0, 7); x.fill(); }
        x.globalAlpha = d[2]; x.fillStyle = color; x.beginPath(); x.arc(d[0], h / 2, d[1], 0, 7); x.fill();
      });
    }
    function ring(c, S, mult) {
      var g = prep(c); if (!g) return;
      var x = g.x, w = g.w, h = g.h, r = Math.min(h / 2 - 2, (S.size * mult) / 2 + 2);
      x.strokeStyle = getComputedStyle(c).color; x.lineWidth = 1.5; x.setLineDash([3, 2]);
      x.beginPath(); x.arc(w / 2, h / 2, r, 0, 7); x.stroke();
    }
    function paint(scope) {
      var S = state(), color = ink(), rgb = rgbOf(color);
      var arts = (scope || root).querySelectorAll('canvas.dp-art');
      for (var i = 0; i < arts.length; i++) {
        var c = arts[i];
        if (!c.clientWidth) continue;   // in a closed panel: painted when it opens
        var a = (c.getAttribute('data-art') || '').split(':'), kind = a[0], arg = a[1];
        var ground = groundOf(c), la = lum(rgb), lb = lum(ground);
        var pale = (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05) < 1.6 ? getComputedStyle(c).color : null;
        if (kind === 'brush' && arg) wave(c, { brush: arg, size: 4 }, S, color, pale);
        else if (kind === 'brush') wave(c, { size: Math.min(S.size, 7) * 0.7 + 1.5, alpha: S.opacity / 100 }, S, color, pale);
        else if (kind === 'size' && arg) wave(c, { brush: 'pen', size: +arg * 0.5, amp: 0.14, taper: 'even' }, S, color, pale);
        else if (kind === 'size') dots(c, S, color, pale);
        else if (kind === 'feel') wave(c, { brush: 'pen', size: 3.2, taper: S.pressure === 'on' ? 'press' : 'even', jitter: JITTER[S.smooth] * 0.7 }, S, color, pale);
        else if (kind === 'smooth') wave(c, { brush: 'pen', size: 2.6, jitter: JITTER[arg] }, S, color, pale);
        else if (kind === 'press') wave(c, { brush: 'pen', size: 3.2, taper: arg === 'on' ? 'press' : 'even', amp: 0.16 }, S, color, pale);
        else if (kind === 'eraser') ring(c, S, +(arg || S.eraser));
        else if (kind === 'opacity') wave(c, { brush: 'pen', size: 4, alpha: S.opacity / 100, amp: 0.18, taper: 'even' }, S, color, pale);
      }
    }

    // ---------- the words on the tiles, and the quick sizes' state
    // Feel in the panel's own words, short enough for a phone's tile ("Smooth
    // high" was cut at 402px; the owner's pick, A).
    var SMOOTH = { off: 'As drawn', low: 'Steadier', high: 'Smooth' };
    function words() {
      var S = state();
      var v = {
        brush: S.brushName,
        size: S.size + 'px' + (S.opacity < 100 ? ' · ' + S.opacity + '%' : ''),
        feel: SMOOTH[S.smooth] || SMOOTH.off,
        eraser: S.eraser + '× pen'
      };
      var NAME = { brush: 'Brush', size: 'Size', feel: 'Feel', eraser: 'Eraser' };
      tiles.forEach(function (t) {
        var k = t.getAttribute('data-dp'), el = t.querySelector('.dp-v');
        if (el && el.textContent !== v[k]) el.textContent = v[k];
        t.setAttribute('aria-label', NAME[k] + ', ' + v[k] + (open === k ? '. Tap to close' : ''));
      });
      var quick = root.querySelectorAll('[data-size]');
      for (var i = 0; i < quick.length; i++) quick[i].classList.toggle('active', +quick[i].getAttribute('data-size') === S.size);
    }
    var queued = false;
    function refresh() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; words(); paint(); });
    }

    // ---------- open and close
    function col(k) { return tiles.map(function (t) { return t.getAttribute('data-dp'); }).indexOf(k); }
    function panelOf(k) { return k ? document.getElementById(PANEL_ID[k]) : null; }
    function finishFold() {
      if (!folding) return;
      var p = folding; folding = null;
      clearTimeout(p.__foldT);
      p.classList.remove('dp-folding');
      if (p.getAnimations) p.getAnimations().forEach(function (a) { a.cancel(); });
      var drop = function () {
        p.hidden = true;
        tiles.forEach(function (t) { if (t.getAttribute('data-dp') === p.getAttribute('data-dp')) t.classList.remove('dp-open'); });
        if (!open) root.removeAttribute('data-col');
      };
      if (window.SkriblDrawerDetent && window.SkriblDrawerDetent.shrinkGently) window.SkriblDrawerDetent.shrinkGently(panel, drop);
      else drop();
    }
    function show(k, instant) {
      var was = open;
      if (was === k) k = null;
      open = k;
      if (folding) finishFold();
      var old = panelOf(was), now = panelOf(k);
      tiles.forEach(function (t) {
        var on = t.getAttribute('data-dp') === k;
        t.setAttribute('aria-expanded', String(on));
        if (on) t.classList.add('dp-open');
        else if (t.getAttribute('data-dp') !== was || k) t.classList.remove('dp-open');
      });
      if (old && k) old.hidden = true;   // one tile for another: the new one unfolds where the old one was
      if (now) {
        root.setAttribute('data-col', String(col(k)));
        now.hidden = false;
        paint(now);
        if (!instant && !still() && now.animate) {
          now.animate([{ opacity: 0, transform: 'scaleY(.92)' }, { opacity: 1, transform: 'none' }],
                      { duration: 220, easing: 'cubic-bezier(.2, .8, .2, 1)' });
        }
      }
      if (old && !k) {
        // Closing: fold away first, then leave; at once under reduced motion.
        if (instant || still()) { folding = old; finishFold(); }
        else {
          folding = old;
          old.classList.add('dp-folding');
          if (old.animate) old.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scaleY(.94)' }],
                                       { duration: 180, easing: 'ease-in', fill: 'forwards' });
          old.__foldT = setTimeout(finishFold, 200);
        }
      }
      words();
      if (!instant) panel.dispatchEvent(new CustomEvent('drawtile', { detail: { open: k } }));
    }
    tiles.forEach(function (t) {
      t.addEventListener('click', function () { show(t.getAttribute('data-dp')); });
    });

    // ---------- the quick sizes
    // Only a quick size in this drawer counts. Flip's <body> carries a
    // data-size of its own (lib/sizeclass.js, "compact"), and a tap anywhere
    // else in the tiles found it: the size read as NaN and the pen went to the
    // slider's middle, 18px.
    root.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-size]') : null;
      if (!b || !root.contains(b) || !size) return;
      var v = Math.max(+size.min || 1, Math.min(+size.max || 30, +b.getAttribute('data-size')));
      size.value = String(v);
      size.dispatchEvent(new Event('input', { bubbles: true }));
      size.dispatchEvent(new Event('change', { bubbles: true }));
      refresh();
    });

    // ---------- listening
    [size, opacity].forEach(function (el) { if (el) { el.addEventListener('input', refresh); el.addEventListener('change', refresh); } });
    if (typeof MutationObserver !== 'undefined') {
      var groups = panel.querySelectorAll('#brushSeg, #smoothSeg, #pressureSeg, #eraserSeg');
      var mo = new MutationObserver(refresh);
      for (var i = 0; i < groups.length; i++) mo.observe(groups[i], { subtree: true, attributes: true, attributeFilter: ['class'] });
      if (inkEl) mo.observe(inkEl, { attributes: true, attributeFilter: ['style', 'class'] });
      new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      // A drawer hidden by ANY route closes its tile; shown, it repaints
      // (a draft restored while it was shut set its controls without events).
      new MutationObserver(function () {
        if (panel.hidden) { if (open) show(open, true); finishFold(); }
        else refresh();
      }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
    }
    try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', refresh); } catch (e) {}
    window.addEventListener('resize', refresh);
    refresh();

    root.__dp = { show: show, open: function () { return open; }, paint: paint, refresh: refresh };
  }

  // Each editor attaches it to its own #drawPanel, beside the detent.
  window.SkriblDrawTiles = { attach: attach };
}());
