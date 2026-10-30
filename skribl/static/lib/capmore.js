/* A CAPTION AT TWO LINES, AND A "MORE" WHERE THERE IS MORE.
 *
 * The owner's yes on the posting mock for the gallery's cards ("two lines
 * with more"), and then for the link page and the Posted! card, after a long
 * caption shrank the drawing on one and took over the other: "words never
 * shrink the drawing". Two lines of a caption show at rest; a "more" opens
 * the rest in place, and "less" puts it back. One copy for every surface, as
 * the drawers and the full-screen bar have: two copies is the drift this
 * product keeps learning not to have. It lived in gallery.js, its first page.
 *
 * WHETHER THERE IS MORE IS ASKED OF THE WORDS, at the width they are set at:
 * their own height against two of their own lines. The same answer clamped or
 * open, and asked again whenever the box changes width (a phone turned, a
 * window dragged), so a caption that fits on a desk and not on a phone shows
 * its "more" only on the phone.
 *
 * IT GLIDES BOTH WAYS. The box eases from the height it has to the height the
 * other state has, measured with that state's own clamp, then lets go of the
 * number. A close keeps the whole text in the box while it shrinks and clamps
 * only at the end, so the lines go down with the box rather than vanishing
 * and leaving an empty box to ease. Reduce Motion: it just changes.
 *
 * The page keeps its own look: the words wear their two-line clamp in its
 * sheet (`.is-open` takes it off), and the button is the page's own element.
 */
(function (global) {
  'use strict';
  var GLIDE = 'height 0.24s cubic-bezier(0.2, 0.7, 0.2, 1)';
  var still = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)');

  // Says whether there is more; true when the answer changed.
  function sync(tc) {
    var btn = tc._more;
    if (!btn) return false;
    var cs = getComputedStyle(tc);
    var line = parseFloat(cs.lineHeight) || 21;
    var words = tc.scrollHeight - (parseFloat(cs.paddingTop) || 0) - (parseFloat(cs.paddingBottom) || 0);
    var over = words > line * 2 + 1, was = !btn.hidden;
    if (was !== over) btn.hidden = !over;
    /* The button carries the box's bottom air when it shows; the words do
       when it does not. A class on the parent, not a page-wide :has() (item 1). */
    if (tc.parentNode) tc.parentNode.classList.toggle('cap-more', over);
    return was !== over;
  }

  function toggle(tc) {
    var btn = tc._more, open = !tc._open;
    tc._open = open;
    var from = tc.getBoundingClientRect().height;
    tc.style.transition = 'none';
    tc.style.height = '';
    tc.classList.toggle('is-open', open);
    var to = tc.getBoundingClientRect().height;
    // Its height at two lines, for a page that keeps the room it gave them
    // while the rest is open (the link page's drawing keeps its size).
    tc._shut = open ? from : to;
    btn.textContent = open ? 'less' : 'more';
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? 'Show less of the caption' : 'Read more of the caption');
    var g = tc._glide = {};
    if ((still && still.matches) || Math.abs(to - from) < 1) { tc.style.transition = ''; return; }
    tc.classList.add('is-open');
    tc.style.height = from + 'px';
    void tc.offsetHeight;
    tc.style.transition = GLIDE;
    tc.style.height = to + 'px';
    var done = function (e) {
      if (e && (e.target !== tc || e.propertyName !== 'height')) return;
      tc.removeEventListener('transitionend', done);
      if (tc._glide !== g) return;
      tc._glide = null;
      tc.style.transition = '';
      tc.style.height = '';
      tc.classList.toggle('is-open', tc._open);
    };
    tc.addEventListener('transitionend', done);
    setTimeout(done, 420);
  }

  // The words and their button, shut; once per pair.
  function attach(tc, btn) {
    if (tc._more === btn) return;
    tc._more = btn;
    btn.textContent = 'more';
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Read more of the caption');
    btn.addEventListener('click', function () { toggle(tc); });
  }

  // Asks again whenever a watched box changes size; `then` hears of a change.
  function watcher(then) {
    return global.ResizeObserver ? new ResizeObserver(function (rows) {
      for (var i = 0; i < rows.length; i++) if (sync(rows[i].target) && then) then(rows[i].target);
    }) : null;
  }

  global.SkriblCapMore = { attach: attach, sync: sync, toggle: toggle, watcher: watcher };
})(window);
