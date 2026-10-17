/* The little book: what Ask's "New here?" opens (owner, after v323: the
 * little book mock, "Yes to all as long as it's kind"; piece three of the
 * help in four layers, FUTURE.md 6p). One module for the Pad and Flip.
 *
 * ONE IDEA A PAGE. Each page has its real example playing (a Skribl
 * replaying the way it was drawn, or a phone recording for the buttons,
 * through lib/learncard.js's picture()), a title and one sentence. A drawing
 * page has Draw along (lib/drawalong.js). Next and Back, a swipe, or the
 * arrow keys turn the pages; the last says Start drawing.
 *
 * KIND, as the owner asked. It never opens by itself. Closing it (the x,
 * Escape, a tap outside) goes back to How it works, where it was opened
 * from; nothing is lost and nothing is asked. A sheet that fits its page on
 * a phone, so the drawing stays in view above it; a dialog on a desk.
 */
(function () {
  'use strict';
  var root = document.getElementById('bookRoot');
  if (!root) return;
  var isFlip = !!document.getElementById('strip');
  var sheet = root.querySelector('.bk');
  var pic = document.getElementById('bkPic');
  var kick = document.getElementById('bkKick');
  var title = document.getElementById('bkTitle');
  var line = document.getElementById('bkLine');
  var along = document.getElementById('bkAlong');
  var dots = document.getElementById('bkDots');
  var back = document.getElementById('bkBack');
  var next = document.getElementById('bkNext');

  var PAGES = isFlip ? [
    { t: 'This is Skribl Flip', s: 'Pages that flip into an animation, played the way you drew them.', demo: 'flip-blooby-card' },
    { t: 'Draw a page', s: 'Press harder for a thicker line. Tap Pen again for colour and brush.', demo: 'pen', along: 'cat' },
    { t: 'Make it move', s: 'Duplicate the page, nudge the drawing, redraw it. Play, and it moves.', demo: 'flip-wave' },
    { t: 'Add a song', s: 'A song under your Flip, looping the part you pick.', clip: 'music' },
    { t: 'Share it', s: 'Post it for a link anyone can open.', clip: 'post' }
  ] : [
    { t: 'This is Skribl Pad', s: 'Everything you draw plays back the way you drew it: every line, at your speed.', demo: 'blooby-card' },
    { t: 'Draw', s: 'Press harder for a thicker line. Tap Pen again for colour and brush.', demo: 'cat', along: 'cat' },
    { t: 'Watch it come alive', s: 'Play it at a quarter speed, or sixteen times faster to see an hour in a minute.', clip: 'speed' },
    { t: 'Rubbing out is part of the show', s: 'The eraser plays back too. Undo takes back a stroke; nothing is lost.', demo: 'eraser' },
    { t: 'Add a song', s: 'A song under your drawing, looping the part you pick.', clip: 'music' },
    { t: 'Share it', s: 'Post it for a link anyone can open to watch it draw itself.', clip: 'post' }
  ];
  var at = 0, example = null, from = null;

  dots.innerHTML = PAGES.map(function () { return '<i></i>'; }).join('');

  function show(i) {
    at = Math.max(0, Math.min(PAGES.length - 1, i));
    var pg = PAGES[at];
    if (example) { example.stop(); example = null; }
    pic.innerHTML = '';
    var lc = window.SkriblLearnCard;
    example = (lc && lc.picture) ? lc.picture({ demo: pg.demo, clip: pg.clip }, pic) : null;
    pic.hidden = !example;
    kick.textContent = 'New here? · ' + (at + 1) + ' of ' + PAGES.length;
    title.textContent = pg.t;
    line.textContent = pg.s;
    along.hidden = !pg.along || !window.SkriblDrawAlong;
    back.hidden = at === 0;
    next.textContent = at === PAGES.length - 1 ? 'Start drawing' : 'Next';
    Array.prototype.forEach.call(dots.children, function (d, k) { d.classList.toggle('on', k === at); });
  }
  function open() {
    if (typeof window.closeHelpDrawer === 'function') window.closeHelpDrawer();
    if (window.SkriblHints) window.SkriblHints.hide();
    root.hidden = false;
    show(0);
    requestAnimationFrame(function () { root.classList.add('open'); });
    if (window.SkriblModal) window.SkriblModal.open(root);
    next.focus({ preventScroll: true });
  }
  // How it ends: 'back' returns to How it works, where the book was opened
  // from; 'draw' leaves the drawing in front of you.
  function close(how) {
    if (root.hidden) return;
    if (example) { example.stop(); example = null; }
    root.classList.remove('open');
    root.hidden = true;
    if (window.SkriblModal) window.SkriblModal.close(root);
    if (how === 'back' && typeof window.openHelpDrawer === 'function') window.openHelpDrawer();
  }

  next.addEventListener('click', function () {
    if (at === PAGES.length - 1) close('draw'); else show(at + 1);
  });
  back.addEventListener('click', function () { show(at - 1); });
  along.addEventListener('click', function () {
    var pg = PAGES[at];
    close('draw');
    if (window.SkriblDrawAlong) window.SkriblDrawAlong.start(pg.along);
  });
  root.addEventListener('click', function (e) {
    if (e.target.closest('[data-book-close]')) close('back');
  });
  root.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close('back'); }
    else if (e.key === 'ArrowRight' && !e.target.closest('input')) { e.preventDefault(); if (at < PAGES.length - 1) show(at + 1); }
    else if (e.key === 'ArrowLeft' && !e.target.closest('input')) { e.preventDefault(); show(at - 1); }
  });
  // A swipe sideways turns the page.
  sheet.addEventListener('pointerdown', function (e) { from = { x: e.clientX, y: e.clientY }; });
  sheet.addEventListener('pointerup', function (e) {
    if (!from) return;
    var dx = e.clientX - from.x, dy = e.clientY - from.y;
    from = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > 1.5 * Math.abs(dy)) show(at + (dx < 0 ? 1 : -1));
  });

  window.SkriblBook = { open: open, close: close, page: function () { return at; }, pages: PAGES.length };
}());
