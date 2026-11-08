/* The pen SWOOSH — the pen button drawn as the stroke it will make.
 *
 * WHY. The bottom bar used to show a generic pen glyph and, beside it, a colour
 * ring that opened the drawer. That was two controls for one question -- "what
 * will my next stroke look like?" -- and neither answered it: the glyph never
 * changed, and the ring showed the colour but not the size, the brush or the
 * opacity. A scripted drawing test on an iPhone-sized page (the owner's
 * bottom-bar work) found the colour ring was also what kept the phone row from
 * giving every control a full 44px: dropping it, and folding Image and Music
 * into one Media button, is what makes 44x44 fit at 360px.
 *
 * So the pen button carries a small canvas, painted here as a pen nib dipped in
 * the current colour, trailing a line in the current size, brush and opacity
 * (see THE NIB, below; it replaced a sample stroke on a canvas-coloured chip). Tapping the pen again opens its
 * options (the editors wire that); dragging it SIDEWAYS changes the size.
 *
 * WHAT IT EXPOSES.
 *
 *   SkriblPenSwoosh.paint(canvas, s)   s = { brush, size, color, opacity (0..1) }
 *   SkriblPenSwoosh.scrub(button, o)   o = { get(), set(v), min, max, pxPerStep,
 *                                            label(v) -> readout text }
 *   SkriblPenSwoosh.wire(o)            the two above for an editor's pen button;
 *                                      returns repaint() (see wire, below)
 *       A sideways drag of at least SLOP px changes the value by one step per
 *       pxPerStep; the click that follows the drag is swallowed, so a drag is
 *       never also a tap. A readout rides above the button while it moves.
 *
 * Brush shapes come from lib/brushes.js presets when it is loaded, so the
 * sample and the real stroke cannot disagree about how wide a marker is.
 */
(function () {
  'use strict';

  var SLOP = 6;

  function preset(name) {
    var B = window.SkriblBrush;
    if (B && B.PRESETS && B.PRESETS[name]) return B.PRESETS[name];
    return { width: 1, alpha: 1, taper: 0 };
  }

  /* THE NIB (owner, on the old sample stroke in a canvas-coloured chip: "the
   * swoosh looks generic... cheesy and cheap"). The button is now a solid
   * fountain-pen nib -- slit and breather hole, a thin collar -- with its tip
   * dipped in the current ink, the ink running up the slit into the hole, and
   * the short line it has just drawn trailing off the tip. Colour, size (the
   * line's width), brush and opacity still show; the chip behind it is gone,
   * so it sits on the dock like every other tool.
   *
   * The nib itself is drawn in the button's --pen-nib (styles.css): text ink,
   * dimmer when another tool is selected, and it follows the theme. Units
   * below are px at the 50x36 button; the nib points down its own +y axis and
   * is turned 45deg so the tip points down-left. */
  var NIB = 'M -3.9 -7 L 3.9 -7 L 5.3 0.8 C 4.6 5.4 2.3 9.8 0 14.4 C -2.3 9.8 -4.6 5.4 -5.3 0.8 Z';
  var COLLAR = 'M -4.4 -10.6 L 4.4 -10.6 L 4.4 -8.3 L -4.4 -8.3 Z';
  var TIP = 14.4;

  function paint(c, s) {
    if (!c || !c.getContext) return;
    var dpr = window.devicePixelRatio || 1;
    var w = c.clientWidth || 50, h = c.clientHeight || 36;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    }
    var x = c.getContext('2d');
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    x.clearRect(0, 0, w, h);
    var ink = s.color || '#ffffff';
    var nibInk = '';
    try { nibInk = getComputedStyle(c).getPropertyValue('--pen-nib').trim(); } catch (e) {}
    var p = preset(s.brush || 'pen');
    var op = typeof s.opacity === 'number' ? s.opacity : 1;
    var cx = w * 0.64, cy = h * 0.40;

    // The line just drawn, off the tip: width follows size (capped, so a
    // size-30 marker is still a line and not a slab), plus the brush's look.
    var tx = cx - TIP / Math.SQRT2, ty = cy + TIP / Math.SQRT2;
    var width = Math.max(1.2, Math.min((s.size || 5) * p.width * 0.4, 4));
    x.save();
    x.globalAlpha = Math.max(0.15, op * p.alpha);
    x.strokeStyle = ink; x.lineCap = 'round'; x.lineJoin = 'round'; x.lineWidth = width;
    if ((s.brush || '') === 'airbrush') { x.shadowColor = ink; x.shadowBlur = Math.min(width * 1.6, 8); x.globalAlpha = Math.max(0.3, op * 0.6); }
    if ((s.brush || '') === 'pencil') x.setLineDash([2.2, 1.3]);
    x.beginPath(); x.moveTo(tx, ty);
    x.bezierCurveTo(tx - 6, ty + 3, tx - 10, ty - 3, tx - 17, ty);
    x.stroke();
    x.restore();

    // The nib, its dipped tip, and the ink up the slit into the hole.
    var body = new Path2D(NIB), collar = new Path2D(COLLAR);
    x.save();
    x.translate(cx, cy); x.rotate(Math.PI / 4);
    x.fillStyle = nibInk || '#f1f2f6';
    x.fill(body); x.fill(collar);
    x.save(); x.clip(body);
    x.fillStyle = ink; x.fillRect(-7, 9.6, 14, 6);
    x.strokeStyle = ink; x.lineWidth = 1.25; x.lineCap = 'butt';
    x.beginPath(); x.moveTo(0, 2.6); x.lineTo(0, TIP + 1); x.stroke();
    x.restore();
    x.fillStyle = ink;
    x.beginPath(); x.arc(0, 1.6, 1.75, 0, Math.PI * 2); x.fill();
    x.restore();
  }

  var bubble = null;
  function readout(btn, text) {
    if (!bubble) {
      bubble = document.createElement('div');
      bubble.className = 'swoosh-readout';
      bubble.setAttribute('aria-hidden', 'true');
      document.body.appendChild(bubble);
    }
    if (text == null) { bubble.classList.remove('on'); return; }
    var r = btn.getBoundingClientRect();
    bubble.textContent = text;
    bubble.style.left = (r.left + r.width / 2) + 'px';
    bubble.style.top = (r.top - 10) + 'px';
    bubble.classList.add('on');
  }

  function scrub(btn, o) {
    if (!btn || btn._swooshScrub) return;
    btn._swooshScrub = true;
    var st = null, swallow = false;
    btn.addEventListener('pointerdown', function (e) {
      if (e.button !== undefined && e.button > 0) return;
      st = { x0: e.clientX, v0: o.get(), id: e.pointerId, moved: false };
    });
    window.addEventListener('pointermove', function (e) {
      if (!st || e.pointerId !== st.id) return;
      var dx = e.clientX - st.x0;
      if (!st.moved && Math.abs(dx) < SLOP) return;
      if (!st.moved) { st.moved = true; try { btn.setPointerCapture(st.id); } catch (_) {} }
      var v = Math.max(o.min, Math.min(o.max, Math.round(st.v0 + dx / o.pxPerStep)));
      if (v !== o.get()) o.set(v);
      readout(btn, o.label ? o.label(o.get()) : String(o.get()));
      e.preventDefault();
    }, { passive: false });
    function end(e) {
      if (!st || (e && e.pointerId !== st.id)) return;
      if (st.moved) swallow = true;
      st = null;
      readout(btn, null);
    }
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
    // A drag is not a tap: the click that trails it would otherwise run the
    // button's own handler (select the pen / open its options).
    btn.addEventListener('click', function (e) {
      if (!swallow) return;
      swallow = false;
      e.stopImmediatePropagation(); e.preventDefault();
    }, true);
  }

  /* wire(o): the whole pen button, for an editor.
   *   o = { canvas, button, range,        -- ids or elements
   *         state() -> the paint() settings, read fresh on every repaint,
   *         scope   -- selector: an input/click/change inside it repaints }
   * Returns repaint(), coalesced to one paint per frame. Size, brush, opacity
   * and the canvas colour are each changed through some control in the draw
   * drawer; rather than hook every one, any input or click in `scope` repaints.
   * A drag on the button moves `range` through its own input event, so the
   * size has one path whichever control moved it. Shared by Pad and Flip. */
  function wire(o) {
    var byId = function (x) { return typeof x === 'string' ? document.getElementById(x) : x; };
    var canvas = byId(o.canvas), button = byId(o.button), range = byId(o.range);
    var frame = 0;
    function repaint() {
      if (frame) return;
      frame = requestAnimationFrame(function () { frame = 0; paint(canvas, o.state()); });
    }
    ['input', 'click', 'change'].forEach(function (ev) {
      document.addEventListener(ev, function (e) {
        if (e.target && e.target.closest && e.target.closest(o.scope)) repaint();
      });
    });
    window.addEventListener('resize', repaint);
    // The nib's colour comes from CSS: it changes with the theme and when
    // another tool is selected (a keyboard shortcut is not a click in scope).
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(repaint).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
      if (button) new MutationObserver(repaint).observe(button, { attributes: true, attributeFilter: ['class'] });
    }
    try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint); } catch (e) {}
    if (button && range) scrub(button, {
      get: function () { return +range.value; },
      min: +range.min || 1, max: +range.max || 30, pxPerStep: 6,
      set: function (v) { range.value = v; range.dispatchEvent(new Event('input', { bubbles: true })); repaint(); },
      label: function (v) { return 'Size ' + v; }
    });
    repaint();
    return repaint;
  }

  /* THE PEN HOPS WHEN YOU HAD TO WAIT FOR IT (the owner's "calm open": "it
   * has to be subtle cuz it happens a lot"; then "Yes calm"). An open that
   * takes a while is the one moment worth a word that the editor is ready,
   * so the pen gives one tiny hop then: up 5px, a hair below, home, in under
   * half a second. On an everyday open (the files already on the device, the
   * editor ready in a fraction of a second) nothing moves at all. The same on
   * the Pad and Flip, both of which carry this file.
   *
   * READY is DOMContentLoaded: it fires once every deferred script has run,
   * and each editor's last one sets its boot mark (__skriblBoot) as it ends.
   * A WAIT is that moment more than WAIT ms after the page began.
   * NOT: under Reduce Motion; while the first-open hello is up (it is the
   * welcome there, and your words write themselves as it goes); once a stroke
   * has begun. Automation never meets it unless it asks
   * (window.__skriblHopForce, as the hello and the snail), so no measurement
   * elsewhere catches the button in the air; window.__skriblHopWait sets the
   * wait for a check of it. */
  var WAIT = 1000;
  function hop() {
    var b = document.getElementById('penToolBtn');
    if (!b || !b.animate) return;
    if (navigator.webdriver && window.__skriblHopForce !== true) return;
    var wait = typeof window.__skriblHopWait === 'number' ? window.__skriblHopWait : WAIT;
    if (performance.now() <= wait) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    // The hello is coming when the head said so and its element is still here (lib/hello.js).
    if (document.documentElement.hasAttribute('data-hello-comes') && document.getElementById('skriblHello')) return;
    if (document.body && document.body.classList.contains('stroking')) return;
    b.animate([{ translate: '0 0' }, { translate: '0 -5px', offset: 0.38 }, { translate: '0 1px', offset: 0.72 }, { translate: '0 0' }],
              { duration: 380, easing: 'cubic-bezier(.3,.7,.4,1)' });
  }
  // A deferred script runs before DOMContentLoaded (the page is 'interactive' by then, not 'loading').
  if (document.readyState !== 'complete') document.addEventListener('DOMContentLoaded', hop, { once: true });

  window.SkriblPenSwoosh = { paint: paint, scrub: scrub, wire: wire };
})();
