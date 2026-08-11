/* Colour selection — the part both editors must agree on.
 *
 * WHAT IS SHARED: validating a hex, normalising its case, and marking exactly
 * one preset swatch active. Pad rejected anything that was not /^#[0-9a-f]{6}$/
 * and lower-cased it; Flip did neither, so `setColor('nonsense')` set the pen to
 * a string the canvas cannot paint with, and '#FF0000' and '#ff0000' were two
 * different colours to the swatch comparison even though they are one colour.
 *
 * WHAT IS NOT SHARED: what a surface DOES with the result. Pad shows the
 * current colour on a custom swatch and an <input type=color>; Flip shows it on
 * the popover trigger. Pad feeds recents from inside its setter; Flip feeds them
 * from the custom input and the eyedropper. Those are real differences in how
 * the two surfaces are built, so they stay where they are and this returns
 * enough for each to do its own thing.
 *
 * The `matched === null` case is why this returns an object rather than a
 * boolean: the caller needs to know a colour was NOT one of the presets, which
 * is what makes it a custom colour worth remembering.
 */
(function () {
  'use strict';

  var HEX = /^#[0-9a-f]{6}$/;

  function normalise(hex) {
    hex = String(hex == null ? '' : hex).trim().toLowerCase();
    return HEX.test(hex) ? hex : null;
  }

  /* apply(group, hex) -> { hex, matched } | null
   *
   * `group` is the element holding .color-dot buttons. Returns null and changes
   * nothing if the colour is not a colour — refusing is the point, and a
   * half-applied selection is worse than none.
   */
  function apply(group, hex) {
    var c = normalise(hex);
    if (!c) return null;
    var matched = null;
    if (group) {
      var dots = group.querySelectorAll('.color-dot');
      for (var i = 0; i < dots.length; i++) {
        var d = dots[i];
        // An explicit boolean. classList.toggle(name, undefined) is treated as
        // no second argument and TOGGLES, and the custom swatch has no
        // data-color — which once left two swatches ringed at the same time.
        var isMatch = !!(d.dataset && d.dataset.color
                         && d.dataset.color.toLowerCase() === c);
        if (isMatch) matched = d;
        d.classList.toggle('active', isMatch);
      }
    }
    return { hex: c, matched: matched };
  }

  window.SkriblColorSelect = { apply: apply, normalise: normalise };
}());
