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
 * picked a ground: follow() moves only a canvas still on the ground the
 * theme it is leaving gave it, so a ground picked by hand is never the one it
 * looks for. */
(function (global) {
  'use strict';

  var DARK = '#0d0f14';    // the canvas default since the first Skribl
  var PAPER = '#f6f2ea';   // the draw drawer's Paper swatch

  function groundFor(theme) { return theme === 'light' ? PAPER : DARK; }

  /* The ground for a drawing started now, in the theme the chrome is wearing. */
  function start() {
    var T = global.SkriblTheme;
    return groundFor(T ? T.get() : 'dark');
  }

  /* follow({ ground, blank, set }): ground() is the canvas's colour now,
   * blank() whether there is nothing on it, set(hex) paints a new one. */
  function follow(o) {
    var T = global.SkriblTheme;
    if (!T || !T.onChange || !o) return;
    var was = T.get();
    T.onChange(function (now) {
      var left = groundFor(was);
      was = now;
      if (now === undefined || groundFor(now) === left) return;
      if (String(o.ground() || '').toLowerCase() === left && o.blank()) o.set(groundFor(now));
    });
  }

  global.SkriblCanvasGround = { DARK: DARK, PAPER: PAPER, groundFor: groundFor, start: start, follow: follow };
})(window);
