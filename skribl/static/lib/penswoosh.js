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
 * So the pen button carries a small canvas, painted here as a sample stroke in
 * the current colour, size, brush and opacity, on the current canvas colour --
 * what you see is what the next stroke will be. Tapping the pen again opens its
 * options (the editors wire that); dragging it SIDEWAYS changes the size.
 *
 * WHAT IT EXPOSES.
 *
 *   SkriblPenSwoosh.paint(canvas, s)   s = { brush, size, color, opacity (0..1), bg }
 *   SkriblPenSwoosh.scrub(button, o)   o = { get(), set(v), min, max, pxPerStep,
 *                                            label(v) -> readout text }
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

  function paint(c, s) {
    if (!c || !c.getContext) return;
    var dpr = window.devicePixelRatio || 1;
    var w = c.clientWidth || 56, h = c.clientHeight || 28;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    }
    var x = c.getContext('2d');
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    x.clearRect(0, 0, w, h);
    x.fillStyle = s.bg || '#0d0f14';
    x.fillRect(0, 0, w, h);
    var p = preset(s.brush || 'pen');
    var op = typeof s.opacity === 'number' ? s.opacity : 1;
    // The sample is a picture of the stroke, not the stroke at 1:1 -- a size-30
    // marker would fill the button. Width follows size up to a cap, so small
    // and large still read as small and large.
    var width = Math.max(1.4, Math.min((s.size || 5) * p.width, h * 0.55) * 0.8);
    x.save();
    x.globalAlpha = Math.max(0.12, op * p.alpha);
    x.strokeStyle = s.color || '#ffffff';
    x.lineCap = 'round'; x.lineJoin = 'round';
    x.lineWidth = width;
    if ((s.brush || '') === 'airbrush') { x.shadowColor = s.color || '#fff'; x.shadowBlur = Math.min(width * 1.6, 12); x.globalAlpha = Math.max(0.3, op * 0.6); }
    if ((s.brush || '') === 'pencil') x.setLineDash([2.2, 1.3]);
    x.beginPath();
    x.moveTo(w * 0.14, h * 0.66);
    x.bezierCurveTo(w * 0.36, h * 0.04, w * 0.58, h * 0.98, w * 0.86, h * 0.34);
    x.stroke();
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

  window.SkriblPenSwoosh = { paint: paint, scrub: scrub };
})();
