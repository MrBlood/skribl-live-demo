/* Home's first visit: BLOOBY DRAWS HIS CARD (social/templates/social/home.html).
 *
 * The card is How it works' own example, a real Flip: the card drawn on its
 * first page, then Blooby on the pages kept over it, waving for ever. It is
 * played by Skribl's in-post player as a DRAFT (docs/INTEGRATION.md: the
 * draft macro, then SkriblInline.attach(el, payload)), so it needs no post in
 * anybody's database and plays exactly as it plays everywhere else.
 *
 * IT STARTS BY ITSELF, silently (it has no sound), and like any skribl a tap
 * pauses it and another goes on; one drawing plays at a time, so a card
 * started below takes over from it. UNDER REDUCE MOTION it does not start:
 * a draft at rest shows its finished drawing, the card with Blooby on it.
 *
 * KIND, NEVER JUMPY: the box waits, hidden, in room already made for the
 * card's shape (social.css .hello-art) and fades in once the drawing is in
 * it. If the drawing cannot be had, the room goes, and the words move up
 * rather than sit under an empty box.
 */
(function () {
  'use strict';
  var art = document.querySelector('[data-hello]');
  /* Not drawn at all (the sign-in page's card is a desk's only): nothing to
     fetch or play. */
  if (!art || !art.getClientRects().length) return;
  var box = document.getElementById('helloCard');
  function gone() { art.hidden = true; }
  if (!box || !window.SkriblInline || !window.fetch) { gone(); return; }
  var still = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* The box is the control, as a posted skribl's is: named, and reachable by
     the keyboard. The player turns "Play ..." into "Pause ..." while it plays. */
  box.setAttribute('role', 'button');
  box.setAttribute('tabindex', '0');
  box.setAttribute('aria-label', art.getAttribute('data-hello-label') || 'Play');

  fetch(art.getAttribute('data-hello'), { credentials: 'same-origin' })
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (payload) {
      var player = window.SkriblInline.attach(box, payload);
      if (!player) throw new Error('not the player\'s markup');
      art.classList.add('is-ready');
      if (still) return;
      /* The drawing is the player's once it has taken it in (a recoloured
         one takes a moment); play() before then would ask a draft for a post
         it does not have. */
      var tries = 0;
      (function start() {
        if (player.state().loaded) { player.play(); return; }
        if (++tries < 120) window.requestAnimationFrame(start);
      })();
    })
    .catch(gone);
})();
