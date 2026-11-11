/* The face player: somebody's drawn face, still, or drawing itself once.
 *
 * (skribl/templates/skribl/_skribl_face.html is its markup, face.css its
 * look; docs/INTEGRATION.md, "A face that draws itself".) The owner's words,
 * phase 1's "all yes": "everyone's picture is a skribl they draw of
 * themselves; it draws itself once, in about four seconds (at 4×), when
 * someone opens their profile, and sits still everywhere else".
 *
 * A STILL FACE NEEDS NOTHING FROM HERE. The macro frames the face skribl's own
 * poster in the circle, in the markup, so it is right on the first paint with
 * or without this file. What this file does:
 *
 *   ONCE. A face with data-play="once" fetches its drawing (GET
 *   /api/skribls/<id>, at the address the macro wrote, never a path made
 *   here: one fetch, which counts a play as any player's does) and hands it to
 *   the in-post player's engine, SkriblInline.attach(), as an AMBIENT player:
 *   one that stops nothing when it starts and that a post starting does not
 *   stop. It plays once (no loop) at data-skribl-speed (4×), or faster where
 *   that would take longer than data-skribl-most seconds (5), so a face drawn
 *   in a minute and one drawn for an hour are both a hello of a few seconds.
 *   It starts from the empty circle (the still picture held unseen: is-held),
 *   its drawing fades in on the first frame (is-live), and it rests finished.
 *   The engine's own rule for a box scrolled out of view holds: it waits
 *   there and carries on when it is back.
 *
 *   UNDER REDUCE MOTION, NOTHING: no fetch, no play. The still picture is the
 *   face from the first paint (face.css), and it never moves.
 *
 *   WHEN THE DRAWING CANNOT BE HAD (no player on the page, a failed fetch, a
 *   drawing that never arrives), the still picture fades in where it would
 *   have drawn (is-still), never a broken box.
 *
 *   GONE. A still picture that cannot load is hidden (is-gone): the empty
 *   circle, never a broken-image glyph in somebody's face.
 *
 * Faces put in the page later: SkriblFace.mount(container), as
 * SkriblInline.mount() is for posts. Each face is started once.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  /* How long the drawing may take to be the player's (a recoloured one takes
     a moment), in frames, before the still face stands in for it. */
  var WAIT_FRAMES = 240;

  function reduced() {
    return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function stillInstead(face) {
    face.classList.add('is-still');
  }

  function watchStill(face) {
    var img = face.querySelector('.skribl-face-still');
    if (!img) return;
    function gone() { face.classList.add('is-gone'); }
    img.addEventListener('error', gone);
    if (img.complete && img.getAttribute('src') && !img.naturalWidth) gone();
  }

  function trimmed(api) {
    while (api.length && api.charAt(api.length - 1) === '/') api = api.slice(0, -1);
    return api;
  }

  /* The engine, once the page has it: the in-post player loads beside this
     file (skribl_inline_assets()), in either order, so a face waits for the
     page's own scripts before it decides the engine is not coming. */
  function withEngine(then) {
    if (global.SkriblInline && global.SkriblInline.attach) { then(global.SkriblInline); return; }
    if (doc.readyState === 'complete') { then(null); return; }
    global.addEventListener('load', function () { then(global.SkriblInline || null); });
  }

  function drawOnce(face) {
    var api = face.getAttribute('data-skribl-api') || '';
    var id = face.getAttribute('data-skribl-id') || '';
    var box = face.querySelector('.skribl-face-draw .skribl-inline');
    face.classList.add('is-held');
    withEngine(function (SI) {
      if (!SI || !global.fetch || !api || !id || !box) { stillInstead(face); return; }
      var speed = +face.getAttribute('data-skribl-speed') || 4;
      var most = +face.getAttribute('data-skribl-most') || 0;
      global.fetch(trimmed(api) + '/' + encodeURIComponent(id), { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (body) {
          /* The drawing is under `skribl` in the GET envelope, as the in-post
             player reads it (inlineplayer.js load()). */
          var p = (body && (body.skribl || body.payload)) || body;
          var player = SI.attach(box, p, { ambient: true });
          if (!player) throw new Error('not the face markup');
          var frames = 0;
          (function start() {
            var s = player.state();
            if (!s.loaded) {
              if (++frames < WAIT_FRAMES) global.requestAnimationFrame(start);
              else stillInstead(face);
              return;
            }
            var rate = speed;
            if (most > 0 && s.totalMs > 0 && s.totalMs / rate > most * 1000) rate = s.totalMs / (most * 1000);
            player.setLoop(false);
            player.setRate(rate);
            player.play();
            face.setAttribute('data-skribl-rate', String(Math.round(rate * 100) / 100));
            face.classList.add('is-live');
          })();
        })
        .catch(function () { stillInstead(face); });
    });
  }

  function mount(root) {
    var faces = (root || doc).querySelectorAll('[data-skribl-face]');
    for (var i = 0; i < faces.length; i++) {
      var face = faces[i];
      if (face._skriblFace) continue;
      face._skriblFace = true;
      watchStill(face);
      if (face.getAttribute('data-play') === 'once' && !reduced()) drawOnce(face);
    }
  }

  global.SkriblFace = { mount: mount };

  if (doc) {
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { mount(); });
    else mount();
  }
})(typeof window !== 'undefined' ? window : this);
