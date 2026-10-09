/* Tap to pause: a tap on an editor's canvas while its preview plays pauses it
 * where it is, and another tap carries on from there. The owner: "tapping the
 * screen while a flip/pad playing on creation canvas will pause. With ability
 * to resume with a tap.. but show icons right". Shared by the Pad (app.js) and
 * Flip (flip.js). Each editor owns its own clock, so this owns only what the
 * two must agree on: what counts as a tap, and the mark a pause leaves.
 *
 * A TAP, NOT A PRESS. One pointer, lifted within TAP_MS and TAP_SLOP px of
 * where it went down. A drag, a second finger (a pinch) or a cancelled touch
 * is not one, so nothing a gesture means elsewhere turns into a pause. The
 * canvas stays a playback surface: the editors still refuse it as a drawing
 * surface while their preview runs, paused or not.
 *
 * THE ICON IS WHAT A TAP DOES NEXT. Paused, the in-post player's paused Play
 * (inlineplayer.css .skribl-inline-play, the same round glass with a white
 * play arrow) stands in the middle of the canvas for as long as it is paused;
 * it is shown by body.playback-paused, which each editor sets and clears with
 * its own pause, resume and stop, so a stop can never leave it behind. It
 * takes no pointer events: the tap that lands on it is the canvas's.
 */
(function (global) {
  'use strict';

  var TAP_MS = 500;    // a press held longer is not a tap
  var TAP_SLOP = 10;   // nor one that moved further, in CSS px

  var PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5v14l11-7z"/></svg>';

  /* attach({ surface, host, playing, paused, pause, resume })
   *   surface  the canvas a tap lands on
   *   host     the element the glyph is centred in (the canvas's frame)
   *   playing  () => true while the preview runs, paused or not
   *   paused   () => true while it is paused
   *   pause / resume   the editor's own; each sets body.playback-paused */
  function attach(o) {
    if (!o || !o.surface || !o.host) return null;
    var glyph = document.createElement('div');
    glyph.className = 'tap-paused';
    glyph.setAttribute('aria-hidden', 'true');
    glyph.innerHTML = '<span class="tap-paused-disc">' + PLAY + '</span>';
    o.host.appendChild(glyph);

    var down = null;   // the one pointer that might become a tap
    o.surface.addEventListener('pointerdown', function (e) {
      // A second pointer while one is down is a pinch: neither is a tap.
      if (down || !o.playing() || !e.isPrimary || (e.button != null && e.button > 0)) { down = null; return; }
      down = { id: e.pointerId, x: e.clientX, y: e.clientY, t: e.timeStamp };
    });
    o.surface.addEventListener('pointermove', function (e) {
      if (down && e.pointerId === down.id &&
          (Math.abs(e.clientX - down.x) > TAP_SLOP || Math.abs(e.clientY - down.y) > TAP_SLOP)) down = null;
    });
    o.surface.addEventListener('pointerup', function (e) {
      var d = down;
      down = null;
      if (!d || e.pointerId !== d.id || !o.playing()) return;
      if (e.timeStamp - d.t > TAP_MS) return;
      if (Math.abs(e.clientX - d.x) > TAP_SLOP || Math.abs(e.clientY - d.y) > TAP_SLOP) return;
      if (o.paused()) o.resume(); else o.pause();
    });
    o.surface.addEventListener('pointercancel', function () { down = null; });
    return { glyph: glyph };
  }

  global.SkriblTapPause = { attach: attach, TAP_MS: TAP_MS, TAP_SLOP: TAP_SLOP };
})(window);
