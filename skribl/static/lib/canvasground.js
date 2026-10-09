/* The ground a new drawing starts on: Paper in the light theme, the dark
 * canvas in the dark one. The owner, of the mock (both editors, phone and
 * desk): "Do Paper." Shared by the Pad (editor_draft.js, editor_menu.js) and
 * Flip (flip.js); the player never loads it, because a posted Skribl carries
 * its own ground.
 *
 * WHAT THE THEME DECIDES, AND WHAT IT NEVER DOES. A drawing's ground is part
 * of the drawing: saved, posted, exported, what other people see. So the
 * theme only chooses where a NEW drawing starts (the page loading with no
 * draft to restore, and New Skribl). It never repaints a drawing: a restored
 * draft, an opened backup and a loaded post keep theirs, and the swatches
 * still offer every ground in either theme.
 *
 * A BLANK CANVAS FOLLOWS THE THEME. Switch the theme before drawing anything
 * and the empty canvas moves with it, because nothing on it was ever chosen.
 * Not once there is a stroke or a photo on it, and not once the person has
 * picked a ground: follow() moves only a canvas still on the ground start()
 * last GAVE it, and a pick, even of the swatch already lit, takes that back.
 * Comparing with the ground the old theme starts on instead would move a
 * hand-picked one that happens to match: Paper picked in the dark theme went
 * dark again after a trip to light and back. A restored draft was given
 * nothing, so it never follows. */
(function (global) {
  'use strict';

  var DARK = '#0d0f14';    // the canvas default since the first Skribl
  var PAPER = '#f6f2ea';   // the draw drawer's Paper swatch

  function groundFor(theme) { return theme === 'light' ? PAPER : DARK; }

  /* The ground this file last gave the page's canvas, or null if it has
   * given none. One editor to a page, so one value. */
  var given = null;

  /* The ground for a drawing started now, in the theme the chrome is wearing. */
  function start() {
    var T = global.SkriblTheme;
    given = groundFor(T ? T.get() : 'dark');
    return given;
  }

  /* A ground the person picks is theirs: a swatch or the custom colour. Both
   * editors build their swatches from the draw drawer's one template
   * (_skribl_draw_drawer.html), so one pair of listeners hears both. */
  if (global.document) {
    global.document.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('.bg-swatch[data-bg]')) given = null;
    }, true);
    global.document.addEventListener('input', function (e) {
      if (e.target && e.target.id === 'customBgInput') given = null;
    }, true);
  }

  /* follow({ ground, blank, set }): ground() is the canvas's colour now,
   * blank() whether there is nothing on it, set(hex) paints a new one. */
  function follow(o) {
    var T = global.SkriblTheme;
    if (!T || !T.onChange || !o) return;
    T.onChange(function (now) {
      var want = groundFor(now);
      if (!given || want === given) return;
      if (String(o.ground() || '').toLowerCase() === given && o.blank()) {
        given = want;
        o.set(want);
      }
    });
  }

  global.SkriblCanvasGround = { DARK: DARK, PAPER: PAPER, groundFor: groundFor, start: start, follow: follow };
})(window);
