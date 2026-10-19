/* Full screen in the editors: the drawing as big as the screen goes, while it plays.
 *
 * THE OWNER, after the measured mock ("I like your picks"): the button at the
 * end of the line under the drawing -- Flip's at the end of its speed row --
 * and in full screen the controls fade a moment after the drawing starts,
 * coming back when the mouse moves or a finger taps.
 *
 * ONE MODULE, BOTH EDITORS. Each hands over its own frame, its own button,
 * what travels into the band (the Pad's scrubber and line, Flip's progress
 * and speeds), how to lay its canvas out, and its own play, pause and resume.
 * Going full screen is lib/immersive.js -- the real API, or the iPhone's
 * pinned stand-in -- and the fade is lib/chromefade.js, the rule every
 * full-screen surface keeps. Page says WHEN, editor says WHAT, as on the
 * link page.
 *
 * MOVED, NOT COPIED. Only the full-screen subtree renders, so what the band
 * needs is carried into the frame and put back where it came from on the way
 * out, as the link page carries #playerBar: one of every control, and every
 * handler bound to it stays bound.
 *
 * THE LOOK IS THE LINK PAGE'S. The frame, the band and the x are the same
 * rules (styles.css, :is(.canvas-wrap, .watch-full)), so the three are
 * recognisably one full screen and cannot drift apart.
 *
 * A TAP IS A VIDEO APP'S TAP. On a faded screen a finger's first tap only
 * brings the controls back; with them up, a tap pauses, as on the page
 * (lib/tappause.js). NOTHING DRAWS IN FULL SCREEN: it is for watching, and
 * once the drawing has stopped a press on it goes no further.
 *
 *   SkriblWatchFull.makeButton()  -> the way in, for the editor to place
 *   SkriblWatchFull.attach({ wrap, button, carry, fit, playing, paused,
 *                            play, pause, resume, canvas, photo })  -> { isOn, close }
 *
 * THE BAND TAKES ITS COLOURS FROM THE DRAWING (lib/smartfade.js, the owner's
 * "A, smart fade and yes to all" for every full screen), as the link page's
 * does: `canvas()` is the editor's drawing, and `photo()` says when a photo
 * shows under it as a picture of its own, which keeps the scrim.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  /* The link player's own glyphs (app.js ICON_PLAY_P / ICON_PAUSE_P), and
     its exit's x (skribl_player.html #playerFullExit) -- but the arrow sits
     0.58 to the left of theirs. A triangle's middle, to the eye, is halfway
     between its box and its mass (check_centring), and theirs is 0.58 right
     of the circle's: a known finding there, not carried into a new control. */
  var PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7.42 5v14l11-7z"/></svg>';
  var PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1"/>' +
    '<rect x="14" y="5" width="4" height="14" rx="1"/></svg>';
  var CLOSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';
  /* And its full-screen button's four corners (#playerFullBtn), so the way in
     looks the same on the link page and in both editors. */
  var EXPAND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/>' +
    '<path d="M8 21H5a2 2 0 0 1-2-2v-3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';

  function button(cls, html, label) {
    var b = doc.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.innerHTML = html;
    if (label) b.setAttribute('aria-label', label);
    return b;
  }

  function attach(o) {
    if (!o || !o.wrap || !o.button || !global.SkriblImmersive) return null;
    var wrap = o.wrap, carry = o.carry || [];
    wrap.classList.add('watch-full');
    var band = doc.createElement('div');
    band.className = 'player-bar watch-band';
    var row = doc.createElement('div');
    row.className = 'watch-row';
    var play = button('player-btn primary watch-play', PLAY, 'Play');
    row.appendChild(play);
    var exit = button('player-btn full-exit watch-exit', CLOSE, 'Leave full screen');
    var homes = [];

    /* Awake while it is paused, and while a menu in the band is open: never
       fade what someone is in the middle of. Once it stops -- the Pad's take
       watched to its end -- they come up and step back again, so the finished
       drawing is seen whole. Flip's play goes round until it is stopped. */
    var fade = global.SkriblChromeFade ? global.SkriblChromeFade.attach(wrap, {
      tapWakes: true,
      awake: function () { return o.paused() || !!band.querySelector('[aria-expanded="true"]'); }
    }) : null;

    var smart = global.SkriblSmartFade && o.canvas ? global.SkriblSmartFade.full(band, {
      canvas: o.canvas,
      photo: o.photo,
      glass: '.player-btn:not(.primary), .rl-speed, .full-btn',
      words: '.rl-drawn, .rl-m, .rl-skip'
    }) : null, was = null;

    function sync() {
      var running = o.playing() && !o.paused();
      play.innerHTML = running ? PAUSE : PLAY;
      play.setAttribute('aria-label', running ? 'Pause' : 'Play');
      if (fade) fade.poke();
      // A play, a pause or the end changes what lies under the band.
      if (smart && running !== was) { was = running; smart.read(); }
    }

    function onChange(on) {
      /* Focus follows the way in: into the band with it, and back to it on
         the way out from anywhere in full screen -- the x, the band, Escape --
         as a dialog hands focus back to what opened it. The browser can drop
         focus to the page as it leaves its own full screen, before this hears
         of it, so focus on nothing counts as in full screen too (v323). */
      var a = doc.activeElement;
      var had = a === o.button || (!on && (!a || a === doc.body || wrap.contains(a)));
      o.button.setAttribute('aria-pressed', '' + on);
      o.button.setAttribute('aria-label', on ? 'Leave full screen' : 'Full screen');
      if (on) {
        homes = carry.map(function (el) { return { el: el, parent: el.parentNode, next: el.nextSibling }; });
        carry.forEach(function (el) { band.appendChild(el); });
        band.appendChild(row);
        wrap.appendChild(band);
        wrap.appendChild(exit);
        sync();
        if (fade) fade.start();
      } else {
        if (fade) fade.stop();
        // Last carried, first home: each one's anchor is then back on the page,
        // even where two carried controls sit side by side.
        homes.reverse().forEach(function (h) { h.parent.insertBefore(h.el, h.next); });
        homes = [];
        if (band.parentNode) band.parentNode.removeChild(band);
        if (exit.parentNode) exit.parentNode.removeChild(exit);
      }
      o.fit(on);
      if (smart) { was = null; smart[on ? 'start' : 'stop'](); }
      // A focused element that is moved, or removed, loses focus to <body>.
      if (had) o.button.focus({ preventScroll: true });
    }

    var full = global.SkriblImmersive.attach(wrap, { onChange: onChange });
    o.button.addEventListener('click', full.toggle);
    exit.addEventListener('click', full.close);
    play.addEventListener('click', function () {
      if (!o.playing()) o.play();
      else if (o.paused()) o.resume();
      else o.pause();
      sync();
    });
    /* A finger's first tap on a faded screen only brings the controls back,
       so it can reach the speed without stopping the drawing: the fade's own
       rule (tapWakes above), every full screen's. Once they are up, a tap
       pauses as it does on the page. And nothing draws in full screen: once
       the drawing stops, a press on it goes no further. */
    wrap.addEventListener('pointerdown', function (e) {
      if (!full.isOn() || o.playing() || band.contains(e.target) || exit.contains(e.target)) return;
      e.preventDefault();
      e.stopPropagation();
    }, true);
    /* The editors say what changed with classes on <body> (replaying or
       playing, playback-paused); the band's Play follows them, whoever
       pressed what. */
    new MutationObserver(function () { if (full.isOn()) sync(); })
      .observe(doc.body, { attributes: true, attributeFilter: ['class'] });
    /* No resize listener here: each editor's own layout asks full screen
       first (app.js layoutEditorCanvas, flip.js fitPad), and those run on a
       resize and on a phone's orientationchange, which a listener here would
       miss. */

    return { isOn: full.isOn, close: full.close };
  }

  /* The way in, for an editor to place where its own line or row ends. */
  function makeButton() {
    var b = button('full-btn', EXPAND, 'Full screen');
    b.setAttribute('aria-pressed', 'false');
    return b;
  }

  global.SkriblWatchFull = { attach: attach, makeButton: makeButton };
})(window);
