/* HOW IT WORKS, the site's own page (how.html, how.py; the owner's "All yes",
 * Nov 19). Two jobs, and the words are the page's.
 *
 * THE EXAMPLES. Each box under Watch an example is Skribl's in-post player
 * (the box a post has), waiting for a drawing: this fetches each one's file
 * and hands it over (SkriblInline.attach), so it rests showing the finished
 * drawing with its play button, and a tap plays it where it sits. What the
 * button says is worked out here from the drawing itself: a Flip, how many
 * pages; a drawing, how long it took (its last point's time); the draw-back,
 * each hand's time as the page gives it (data-how-parts: the joined drawing
 * plays the first hand squeezed, so its own length is not how long it took).
 * THE FIRST ONE DRAWS ITSELF ONCE as the page opens, never under Reduce
 * Motion: the page says what the site is by doing it. If a file does not
 * come, one line says so, with Try again for those alone.
 *
 * THE DRAWING TOOLS. "The Pad" and "Flip" are links to the editor's own
 * address with ?help=1, which is where a visitor goes. Signed in, a plain
 * tap is taken here instead and the editor opens INSIDE A POST with its How
 * it works showing (compose.js, SocialComposer.editor), so nobody is sent
 * out of the site to the editor by itself; a new tab is the link's own.
 */
(function () {
  'use strict';
  var doc = document;
  var root = doc.querySelector('[data-how]');
  if (!root) return;
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still() { return !!(reduced && reduced.matches); }

  /* ---- the examples ---------------------------------------------------------- */
  var pics = Array.prototype.slice.call(root.querySelectorAll('[data-how-src]'));
  var sayBox = root.querySelector('[data-how-say]');
  var againBtn = root.querySelector('[data-how-again]');

  /* What its play button says (the player's data-skribl-line). */
  function lineOf(payload, pic) {
    var frames = (payload && payload.frames) || [];
    if (frames.length > 1) return { pages: frames.length };
    var parts = (pic.getAttribute('data-how-parts') || '').split(',').map(Number).filter(function (n) { return n > 0; });
    if (parts.length > 1) {
      return { drawn: parts.reduce(function (a, b) { return a + b; }, 0), parts: parts, people: parts.length };
    }
    var strokes = (frames[0] && frames[0].strokes) || [];
    var last = strokes.length ? +strokes[strokes.length - 1].t || 0 : 0;
    return last > 0 ? { drawn: last } : null;
  }

  function load(pic) {
    if (pic._how || pic._asking) return pic._asking || Promise.resolve(pic._how);
    pic._asking = fetch(pic.getAttribute('data-how-src'), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (payload) {
        var box = pic.querySelector('.skribl-inline');
        if (!box || !window.SkriblInline) throw new Error('no player');
        var info = lineOf(payload, pic);
        if (info) box.setAttribute('data-skribl-line', JSON.stringify(info));
        pic._how = window.SkriblInline.attach(box, payload);
        pic._asking = null;
        pic.classList.add('is-in');
        return pic._how;
      }, function (err) {
        pic._asking = null;
        throw err;
      });
    return pic._asking;
  }

  function loadAll(first) {
    if (sayBox) sayBox.hidden = true;
    var missed = 0, left = pics.length;
    pics.forEach(function (pic, i) {
      load(pic).then(function (player) {
        /* The first, once, as the page opens: the site says what it is by
           doing it. */
        if (first && i === 0 && player && player.play && !still()) player.play();
      }, function () { missed++; }).then(function () {
        left--;
        if (!left && missed && sayBox) sayBox.hidden = false;
      });
    });
  }
  if (againBtn) againBtn.addEventListener('click', function () { loadAll(false); });
  if (pics.length) loadAll(true);

  /* ---- the drawing tools: the editor inside a post, its help showing --------- */
  root.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[data-how-editor]') : null;
    if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var composer = window.SocialComposer;
    if (!composer || !composer.editor) return;
    if (composer.editor({ kind: a.getAttribute('data-how-editor'), help: true, from: a })) e.preventDefault();
  });
})();
