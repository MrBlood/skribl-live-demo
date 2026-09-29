/* The pen palette — one list, both editors.
 *
 * WHY IT IS A LIBRARY. It was two lists: seven <button>s written into
 * _skribl_draw_drawer.html for Pad, and a COLORS array at the top of flip.js
 * for Flip, holding the same seven hexes in the same order by hand. Nothing
 * compared them. Changing the palette meant changing both, and the failure
 * mode of forgetting one is not an error — it is two editors that quietly
 * offer different colours, which nobody notices until someone switches
 * surfaces mid-drawing.
 *
 * THE COLOURS. These are Risograph inks, near enough: fluorescent pink, hot
 * orange, acid yellow, a printed green and a federal blue, plus paper white
 * and a toner black. That is the palette small-press zines are actually
 * printed with, and it is a deliberate replacement for what was here before —
 * a purple and a blue lifted straight from the UI accent, a mint green and a
 * muddy amber. A drawing palette that matches the chrome is a palette that was
 * never chosen.
 *
 * Riso inks are spot colours, so they are saturated in a way screen palettes
 * usually are not, and they were mixed to sit on paper rather than to pass a
 * contrast check. They are strongest on the dark grounds the background
 * swatches default to — acid yellow on white is nearly nothing, which is true
 * of the ink as well.
 *
 * `dark` marks a swatch that needs a visible rim: a near-black dot on a
 * near-black drawer is an empty hole. The rim is a CSS concern (it has to
 * follow the theme), so this only says WHICH, never what colour.
 */
(function (global) {
  'use strict';

  var PEN = [
    { hex: '#ffffff', name: 'Paper white' },
    { hex: '#ff48b0', name: 'Fluoro pink' },
    { hex: '#ff6c2f', name: 'Hot orange' },
    { hex: '#ffe800', name: 'Acid yellow' },
    { hex: '#00a95c', name: 'Ink green' },
    { hex: '#0078bf', name: 'Ink blue' },
    { hex: '#141414', name: 'Toner black', dark: true }
  ];

  /* Builds the preset dots and puts them where the template's static ones used
   * to sit — BEFORE the custom picker and the eyedropper, which stay in the
   * markup because they are controls rather than colours. Both surfaces call
   * this, which is the point; `onPick` is the only thing they differ on, and
   * Pad passes nothing because it delegates from the group.
   */
  function mount(group, opts) {
    if (!group) return [];
    opts = opts || {};
    var before = opts.before
      || group.querySelector('.color-custom-wrap')
      || group.firstChild;
    var made = [];
    PEN.forEach(function (c, i) {
      var b = global.document.createElement('button');
      b.type = 'button';
      b.className = 'color-dot' + (i === 0 && opts.selectFirst ? ' active' : '');
      b.style.background = c.hex;
      b.dataset.color = c.hex;
      if (c.dark) b.dataset.ink = 'dark';
      b.setAttribute('aria-label', c.name);
      if (typeof opts.onPick === 'function') {
        b.addEventListener('click', function () { opts.onPick(c.hex, b); });
      }
      group.insertBefore(b, before);
      made.push(b);
    });
    return made;
  }

  global.SkriblPalette = { PEN: PEN, hexes: PEN.map(function (c) { return c.hex; }),
                           mount: mount };
})(window);
