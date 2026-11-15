/* THE BLOOBY APP'S SPLASH, PLAYED (the owner, Nov 15: "make a splash screen
 * load first and show blooby. Just like the skribl with the dotted i falling
 * down. [Instead] have the blush. Fall the same way and compress then pop
 * back the exact same way. Kinda the same way Bluesky loads", then "Do it on
 * the dark background. I like that with no stars"). splash-boot.js decided,
 * before the first paint, that this launch shows it (is-splashing on <html>);
 * this plays it and lets it go.
 *
 * THE DRAWING is the site's hello made for it (brand/blooby-splash.json,
 * harness/tools/make_hello.py --splash): "blooby." in the icon's lilac, its
 * blush period falling as skribl's i-dot does (stretched as it falls,
 * squashed as it lands, popped back, settled), played by Skribl's own in-post
 * player as a draft. The first time ever, the word writes itself and the
 * blush falls (about 2.7 s); after that the word is there and only the blush
 * falls (about 1.1 s). Then a moment's rest and the splash fades into the
 * page.
 *
 * KIND: a tap, a click or a key lets it go at once (fading, never cut);
 * under Reduce Motion the finished word, still, a moment, then the fade; and
 * it never holds up a page: the drawing not here within LATE, or the player
 * not there at all, and it fades at once (splash-boot.js lets it go at 6 s
 * whatever happens here). It puts the browser's bar back as it goes.
 *
 * NOTHING ELSE PLAYS UNDER IT: one drawing plays at a time, and a drawing a
 * page starts by itself (Home's first visit, a post's own page, a drawing
 * answer landed on) would stop the splash's, unseen under it. Each asks
 * BloobySplash.after(fn), which runs fn at once without a splash, or as the
 * splash has gone. */
(function () {
  'use strict';
  var LATE = 1500, REST = 250, STILL = 700, FADE = 480;
  var root = document.documentElement;
  var waiting = [];
  var showing = root.classList.contains('is-splashing');
  window.BloobySplash = {
    showing: function () { return showing; },
    after: function (fn) { if (showing) waiting.push(fn); else fn(); },
    leave: function () { leave(); }
  };
  if (!showing) return;
  var el = document.getElementById('bloobySplash');
  var box = document.getElementById('splashBox');
  var first = root.classList.contains('is-splash-first');
  var still = false;
  try { still = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { /* moving, then */ }
  var gone = false, late = 0;

  function leave() {
    if (gone) return;
    gone = true;
    window.clearTimeout(late);
    try { window.localStorage.setItem('blooby.splash.v1', '1'); } catch (e) { /* the next one is a first too */ }
    if (el) el.classList.add('is-leaving');
    window.setTimeout(function () {
      root.classList.remove('is-splashing', 'is-splash-first');
      if (el) el.classList.remove('is-leaving');
      // The bar's grounds back, and its colour the theme's, as lib/theme.js stamps it.
      var mode = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      var metas = document.querySelectorAll('meta[name="theme-color"][data-splash-light]');
      for (var i = 0; i < metas.length; i++) {
        var m = metas[i];
        m.setAttribute('data-light', m.getAttribute('data-splash-light'));
        m.setAttribute('data-dark', m.getAttribute('data-splash-dark'));
        m.removeAttribute('data-splash-light');
        m.removeAttribute('data-splash-dark');
        if (m.getAttribute('data-' + mode)) m.setAttribute('content', m.getAttribute('data-' + mode));
      }
      showing = false;
      var run = waiting.splice(0);
      for (var j = 0; j < run.length; j++) run[j]();
    }, el ? FADE : 0);
  }

  if (!el || !box || !window.SkriblInline || !window.fetch) { leave(); return; }
  el.addEventListener('pointerdown', leave);
  document.addEventListener('keydown', leave, { once: true });
  late = window.setTimeout(leave, LATE);

  window.fetch(el.getAttribute('data-splash'), { credentials: 'same-origin' })
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (payload) {
      if (gone) return;
      var player = window.SkriblInline.attach(box, payload);
      if (!player) throw new Error('not the player\'s markup');
      (function start() {
        if (gone) return;
        var s = player.state();
        if (!s.loaded) { window.requestAnimationFrame(start); return; }
        window.clearTimeout(late);
        var total = s.totalMs;
        if (still) { player.seek(total); window.setTimeout(leave, STILL); return; }
        // After the first time, the word is there and only the blush falls:
        // the drawing from where its pages after the word begin.
        var dot = (payload.frames.length - 1) * 1000 / (payload.fps || 12);
        if (!first) player.seek(Math.max(0, total - dot));
        player.play();
        // Where it has got to, through the player's own seam (docs/INTEGRATION.md,
        // "Where the playhead is"): played through, and stopped there.
        (function watch() {
          if (gone) return;
          var h = player.playhead();
          if (!h.playing && h.ms >= total - 1) { window.setTimeout(leave, REST); return; }
          window.requestAnimationFrame(watch);
        })();
      })();
    })
    .catch(leave);
})();
