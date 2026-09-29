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

  /* THE PEN STARTS IN THE BRAND'S VIOLET (owner: "change the starting color
   * on the pad and flip to the purple that is pads signature color"). It is
   * --accent, the violet the signature's ink starts from, and deliberately NOT
   * one of the inks above: the palette stays the Riso set it was chosen as,
   * and a first stroke in the house colour says whose pad this is. So it is a
   * CUSTOM colour, and the custom swatch wears it and the ring (see START in
   * mount) -- the same state a colour from the picker leaves, which is what
   * it is. Both editors read it from here, so they cannot start apart. */
  var START = '#7c5cff';

  /* Builds the preset dots and puts them where the template's static ones used
   * to sit — BEFORE the custom picker and the eyedropper, which stay in the
   * markup because they are controls rather than colours. Both surfaces call
   * this, which is the point; `onPick` is the only thing they differ on, and
   * Pad passes nothing because it delegates from the group.
   */
  function mount(group, opts) {
    if (!group) return [];
    opts = opts || {};
    var start = opts.start ? String(opts.start).toLowerCase() : null;
    var before = opts.before
      || group.querySelector('.color-custom-wrap')
      || group.firstChild;
    var made = [];
    PEN.forEach(function (c, i) {
      var b = global.document.createElement('button');
      b.type = 'button';
      b.className = 'color-dot' + (c.hex === start ? ' active' : '');
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
    // START: a colour no dot names is the custom swatch's, ringed and in its
    // colour, with the picker opened on it.
    if (start && !PEN.some(function (c) { return c.hex === start; })) {
      var custom = group.querySelector('.color-custom');
      if (custom) {
        custom.style.setProperty('--custom-color', start);
        custom.classList.add('has-color', 'active');
      }
      var input = group.querySelector('.color-custom-wrap input[type="color"]');
      if (input) input.value = start;
    }
    return made;
  }

  global.SkriblPalette = { PEN: PEN, START: START, hexes: PEN.map(function (c) { return c.hex; }),
                           mount: mount };
})(window);
