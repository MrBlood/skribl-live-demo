/* THE BLOOBY APP'S SPLASH, PLAYED (the owner, Nov 15: "make a splash screen
 * load first and show blooby. Just like the skribl with the dotted i falling
 * down. [Instead] have the blush. Fall the same way and compress then pop
 * back the exact same way. Kinda the same way Bluesky loads", "Do it on the
 * dark background. I like that with no stars", then Blooby jumping with his
 * hands thrown up, "without badge", in a stage spotlight: "All yes, B with
 * the stage spotlight"). splash-boot.js decided, before the first paint, that
 * this launch shows it (is-splashing on <html>); this plays it and lets it go.
 *
 * THE SHOW waits for its two pictures: the word's drawing (brand/
 * blooby-hello.json, the site's hello, played by Skribl's in-post player as
 * a draft) and Blooby's strip (brand/blooby-splash-jump.webp, his seven poses
 * drawn by the real Pad), fetched only here, so a browser tab never
 * downloads it. Then the light, Blooby and the word come up together (is-on,
 * social.css), and:
 * - THE FIRST TIME EVER, the word writes itself as the light comes up. Once
 *   it is up, he jumps: the Posted! card's seven poses at 1.4x their times
 *   (lib/postsheet.js JUMP_MS), squashed as he crouches, lifted from the
 *   floor and back, squashed again as he lands, his shadow smaller and
 *   fainter the higher he is; he ends with his arms up. The blush falls once
 *   the word is written: about 2.7 s in all.
 * - AFTER THAT, the word is there; once the light is up he jumps and the
 *   blush falls with him: about 1.6 s.
 * Then a moment's rest, and the splash fades into the page.
 *
 * KIND: a tap, a click or a key lets it go at once (fading, never cut);
 * under Reduce Motion the show comes up still, Blooby in his last pose and
 * the word whole, a moment, then the fade; and it never holds up a page:
 * either picture not here within LATE, or the player not there at all, and
 * it fades at once (splash-boot.js lets it go at 6 s whatever happens here).
 * It puts the browser's bar back as it goes.
 *
 * NOTHING ELSE PLAYS UNDER IT: one drawing plays at a time, and a drawing a
 * page starts by itself (Home's first visit, a post's own page, a drawing
 * answer landed on) would stop the splash's, unseen under it. Each asks
 * BloobySplash.after(fn), which runs fn at once without a splash, or as the
 * splash has gone. */
(function () {
  'use strict';
  var LATE = 1500, REST = 250, STILL = 700, FADE = 480, LIGHT = 400;
  // HIS JUMP, pose by pose: [ms shown, lift (px of his box, which is BOX tall), squash across, squash up], as
  // the mock the owner said yes to: each pose is reached in nine tenths of its time (at least 60 ms), rising
  // easing out and coming down easing in, then held.
  var POSES = [[280, 0, 1.06, 0.92], [110, 24, 0.97, 1.04], [140, 70, 1.0, 1.02], [340, 96, 1.0, 1.0],
               [110, 46, 1.0, 1.02], [180, 0, 1.05, 0.94], [0, 0, 1.0, 1.0]];
  var BOX = 188, TOP = 96;
  var UP = 'cubic-bezier(.2,.7,.3,1)', DOWN = 'cubic-bezier(.6,0,.8,.4)';
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
  var jump = el && el.querySelector('.splash-jump');
  var img = jump && jump.querySelector('img');
  var shadow = el && el.querySelector('.splash-shadow');
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

  // The jump's three tracks, from POSES: his box (lift and squash), the strip (which pose: each shown from its
  // start, as a flipbook's page), and his shadow (smaller and fainter the higher he is).
  function tracks() {
    var keys = [[0, 0, 1, 1, POSES[0][1] > 0 ? UP : DOWN]], at = [], t = 0;
    for (var k = 0; k < POSES.length; k++) {
      var p = POSES[k];
      at.push(t);
      keys.push([t + Math.max(60, p[0] * 0.9), p[1], p[2], p[3], 'linear']);
      t += p[0];
      if (k < POSES.length - 1) keys.push([t, p[1], p[2], p[3], POSES[k + 1][1] > 0 ? UP : DOWN]);
    }
    var total = keys[keys.length - 1][0];
    var him = [], shade = [], strip = [];
    for (var i = 0; i < keys.length; i++) {
      var q = keys[i], off = q[0] / total, up = Math.min(1, q[1] / TOP);
      him.push({ offset: off, easing: q[4], transform: 'translateY(' + (-q[1] / BOX * 100).toFixed(3) + '%) scale(' + q[2] + ', ' + q[3] + ')' });
      shade.push({ offset: off, easing: q[4], transform: 'scale(' + (1 - 0.45 * up).toFixed(3) + ')', opacity: (1 - 0.6 * up).toFixed(3) });
    }
    for (var f = 0; f < at.length; f++) {
      strip.push({ offset: at[f] / total, easing: 'step-end', transform: 'translateX(' + (-f * 100 / POSES.length).toFixed(4) + '%)' });
    }
    strip.push({ offset: 1, transform: strip[strip.length - 1].transform });
    return { total: total, him: him, shade: shade, strip: strip };
  }

  function play(player, payload) {
    window.clearTimeout(late);
    var total = player.state().totalMs;
    if (still || !jump.animate) {
      // Still: Blooby in his last pose, the word whole, a moment, then the fade.
      el.classList.add('is-still');
      player.seek(total);
      el.classList.add('is-on');
      window.setTimeout(leave, LIGHT + STILL);
      return;
    }
    // After the first time, the word is there and only the blush falls: the drawing from where its pages after
    // the word begin.
    var dot = (payload.frames.length - 1) * 1000 / (payload.fps || 12);
    if (!first) player.seek(Math.max(0, total - dot));
    el.classList.add('is-on');
    if (first) player.play();
    var wordDone = false, jumpDone = false, ending = false;
    function maybe() {
      if (wordDone && jumpDone && !ending && !gone) { ending = true; window.setTimeout(leave, REST); }
    }
    window.setTimeout(function () {
      if (gone) return;
      if (!first) player.play();
      var tr = tracks(), opts = { duration: tr.total, fill: 'both' };
      var a = jump.animate(tr.him, opts);
      img.animate(tr.strip, opts);
      shadow.animate(tr.shade, opts);
      var landed = function () { jumpDone = true; maybe(); };
      if (a.finished) a.finished.then(landed, landed);
      window.setTimeout(landed, tr.total + 100);   // whatever becomes of the promise
    }, LIGHT);
    // Where the word has got to, through the player's own seam (docs/INTEGRATION.md, "Where the playhead
    // is"): played through, and stopped there.
    (function watch() {
      if (gone) return;
      var h = player.playhead();
      if (!h.playing && h.ms >= total - 1) { wordDone = true; maybe(); return; }
      window.requestAnimationFrame(watch);
    })();
  }

  if (!el || !box || !img || !shadow || !window.SkriblInline || !window.fetch || !window.Promise) { leave(); return; }
  el.addEventListener('pointerdown', leave);
  document.addEventListener('keydown', leave, { once: true });
  late = window.setTimeout(leave, LATE);

  var drawing = window.fetch(el.getAttribute('data-splash'), { credentials: 'same-origin' })
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  var picture = new Promise(function (ok, no) {
    img.onload = ok;
    img.onerror = function () { no(new Error('his strip did not come')); };
    img.src = img.getAttribute('data-src');
  }).then(function () { return img.decode ? img.decode().catch(function () { /* drawn as it is */ }) : null; });
  Promise.all([drawing, picture])
    .then(function (got) {
      if (gone) return;
      var payload = got[0];
      var player = window.SkriblInline.attach(box, payload);
      if (!player) throw new Error('not the player\'s markup');
      (function ready() {
        if (gone) return;
        if (!player.state().loaded) { window.requestAnimationFrame(ready); return; }
        play(player, payload);
      })();
    })
    .catch(leave);
})();
