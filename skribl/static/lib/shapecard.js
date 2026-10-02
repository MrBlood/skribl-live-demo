/* The shape card -- the picker that opens above the Shape tool -- one
 * implementation, both editors.
 *
 * THE GRIP CLOSES IT. The pill at the top used to DRAG the card, and a dragged
 * card was pinned: taps outside no longer closed it, and it hid only while a
 * finger was down and came back on lift. On a phone the pill reads as every
 * sheet's grabber -- pull down to put it away -- so a person pulling it to
 * close it pinned it instead, over the drawing, with nothing left to close it
 * but another tool (owner: "the menu is weird about how it goes away"). A tap
 * on the pill, or a pull down past 24px, closes the card now, as the sheets'
 * grabbers do. The reason the drag existed -- starting a shape under the card
 * -- is already met: the press that starts a shape closes it (editor_draw.js,
 * flip.js), and tapping Shape brings it back with the same settings.
 *
 * WHAT THE KNOBS DO, SHOWN. "Corners 8" said neither what it rounded nor by
 * how much (owner: "what is corners vs sides?"). The knob is Rounding now,
 * reads Sharp at 0, and a small live shape under the sliders redraws as either
 * moves. It is drawn by lib/shapes.js -- the same points the canvas draws -- so
 * the preview cannot disagree with the stroke it promises. Radius is in canvas
 * pixels; the preview stands for a shape PREVIEW_SPAN px across, scaled into
 * its 64px box, so 8 looks like 8 does on a shape that size.
 */
(function () {
  'use strict';

  var PREVIEW_SPAN = 120;

  function radiusText(v) {
    return (+v || 0) > 0 ? String(+v) : 'Sharp';
  }

  function attach(pop, close) {
    if (!pop) return;
    var grip = pop.querySelector('.pop-grip');
    var seg = pop.querySelector('#shapeSeg');
    var sides = pop.querySelector('#shapeSides');
    var radius = pop.querySelector('#shapeRadius');
    var radiusOut = pop.querySelector('#shapeRadiusOut');
    var box = pop.querySelector('.shape-preview');
    var line = box && box.querySelector('polyline');
    close = close || function () { pop.hidden = true; };

    function kind() {
      var on = seg && seg.querySelector('[data-shape][aria-pressed="true"]');
      return on ? on.getAttribute('data-shape') : 'line';
    }

    function draw() {
      if (radiusOut && radius) radiusOut.textContent = radiusText(radius.value);
      if (!box || !line || !window.SkriblShapes) return;
      var k = kind();
      box.hidden = !window.SkriblShapes.hasKnob(k, 'radius');
      if (box.hidden) return;
      var s = 48 / PREVIEW_SPAN;
      var a = k === 'rect' ? { x: 4, y: 14 } : { x: 8, y: 8 };
      var b = k === 'rect' ? { x: 60, y: 50 } : { x: 56, y: 56 };
      var pts = window.SkriblShapes.points(k, a, b, {
        sides: sides ? +sides.value : 5,
        radius: (radius ? +radius.value : 0) * s
      });
      line.setAttribute('points', pts.map(function (p) {
        return p.x.toFixed(1) + ',' + p.y.toFixed(1);
      }).join(' '));
    }
    // After the editors' own handlers, whatever order they were bound in.
    function soon() { requestAnimationFrame(draw); }
    if (sides) sides.addEventListener('input', soon);
    if (radius) radius.addEventListener('input', soon);
    if (seg) seg.addEventListener('click', soon);
    new MutationObserver(function () { if (!pop.hidden) soon(); })
      .observe(pop, { attributes: true, attributeFilter: ['hidden'] });
    soon();

    if (!grip) return;
    var pid = null, sy = 0, done = false;
    grip.addEventListener('pointerdown', function (e) {
      // The outside-click dismisser and the canvas must not see this press.
      e.preventDefault();
      e.stopPropagation();
      pid = e.pointerId; sy = e.clientY; done = false;
      try { grip.setPointerCapture(e.pointerId); } catch (err) {}
    });
    grip.addEventListener('pointermove', function (e) {
      if (e.pointerId !== pid || done) return;
      if (e.clientY - sy > 24) { done = true; close(); }
    });
    grip.addEventListener('pointerup', function (e) {
      if (e.pointerId !== pid) return;
      pid = null;
      if (!done) close();
    });
    grip.addEventListener('pointercancel', function (e) {
      if (e.pointerId === pid) pid = null;
    });
  }

  window.SkriblShapeCard = { attach: attach, radiusText: radiusText };
}());
