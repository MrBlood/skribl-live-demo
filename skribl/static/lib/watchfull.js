/* Full screen in the editors: the drawing as big as the screen goes, while it plays.
 *
 * THE OWNER, after the measured mock ("I like your picks"): the button at the
 * end of the line under the drawing -- Flip's at the end of its speed row --
 * and in full screen the controls fade a moment after the drawing starts,
 * coming back when the mouse moves or a finger taps; a tap still pauses.
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
 * NOTHING DRAWS IN FULL SCREEN. It is for watching. While the drawing plays
 * a tap pauses it, as on the page (lib/tappause.js); once it has finished, a
 * press on it wakes the controls and goes no further.
 *
 *   SkriblWatchFull.makeButton()  -> the way in, for the editor to place
 *   SkriblWatchFull.attach({ wrap, button, carry, fit, playing, paused,
 *                            play, pause, resume })  -> { isOn, close }
 */
(function (global) {
  'use strict';

  var doc = global.document;
  /* The link player's own glyphs (app.js ICON_PLAY_P / ICON_PAUSE_P), and
     its exit's x (skribl_player.html #playerFullExit). */
  var PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>';
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

    /* Awake while it is not running -- finished or paused -- and while a menu
       in the band is open: never fade what someone is in the middle of. */
    var fade = global.SkriblChromeFade ? global.SkriblChromeFade.attach(wrap, {
      awake: function () { return !o.playing() || o.paused() || !!band.querySelector('[aria-expanded="true"]'); }
    }) : null;

    function sync() {
      var running = o.playing() && !o.paused();
      play.innerHTML = running ? PAUSE : PLAY;
      play.setAttribute('aria-label', running ? 'Pause' : 'Play');
      if (fade) fade.poke();
    }

    function onChange(on) {
      var had = doc.activeElement === o.button;
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
        homes.forEach(function (h) { h.parent.insertBefore(h.el, h.next); });
        homes = [];
        if (band.parentNode) band.parentNode.removeChild(band);
        if (exit.parentNode) exit.parentNode.removeChild(exit);
      }
      o.fit(on);
      /* A focused element that is moved loses focus to <body>; the button
         someone just pressed keeps it, wherever it now sits. */
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
    global.addEventListener('resize', function () { if (full.isOn()) o.fit(true); });

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
