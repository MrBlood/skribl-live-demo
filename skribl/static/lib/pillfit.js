/* The autosave pill yields to the controls it would sit on.
 *
 * THE DEFECT. `.autosave-status` is position:fixed at bottom-left. On a phone
 * the tool row is ALSO at the bottom, so the pill lands squarely on it —
 * measured on both surfaces at every phone size: Flip's "Saved" sits on the pen
 * button, Pad's on its toolbar. Desktop never collides, which is why this
 * survived: it is invisible on the machine it was built on.
 *
 * There was already a rule for a NEARBY case — the pill fades while a drawer is
 * open, because "a pill covering a destructive button is worse than one you
 * cannot see". That rule was right and too narrow: it fixed the case somebody
 * noticed and not the general one. CSS cannot ask whether two boxes intersect,
 * so the general case needs this.
 *
 * IT IS PURELY VISUAL. The pill is pointer-events:none, so it has never
 * intercepted a tap — it obscures the button without disabling it. That lowers
 * the stakes and does not remove them: a control you cannot see is a control
 * you do not press.
 *
 * A WARNING IS NEVER FADED, and this is the part worth being careful about.
 * `failed` and `partial` (saved without media) deliberately stay on screen —
 * flip.js says why: "a warning that fades claims it was resolved". Hiding one
 * because it happens to overlap would trade a cosmetic problem for a durability
 * one, silently, in exactly the situation where the user most needs telling.
 * So overlap fades the reassuring states only; a warning keeps its place and
 * accepts the collision.
 *
 * Shared rather than written twice: both editors show the same pill from their
 * own showAutosaveStatus(), and verify_surfaces counts the names those two files
 * define in common. A lib is one implementation and no new divergence. The
 * player has no autosave and does not load this.
 */
(function (global) {
  'use strict';

  /* What the pill must not cover. Bottom-anchored control surfaces on both
     editors; anything not present on a surface is skipped. */
  var TARGETS = ['.flip-tools', '.toolbar', '#pagebar', '#selbar', '#strip'];
  var WARNING = ['failed', 'partial'];

  function isWarning(el) {
    for (var i = 0; i < WARNING.length; i++)
      if (el.classList.contains(WARNING[i])) return true;
    return false;
  }

  function hits(el) {
    var r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    for (var i = 0; i < TARGETS.length; i++) {
      var c = global.document.querySelector(TARGETS[i]);
      if (!c) continue;
      var b = c.getBoundingClientRect();
      if (!b.width || !b.height) continue;      // hidden bars have no box
      if (!(r.right <= b.left || r.left >= b.right ||
            r.bottom <= b.top || r.top >= b.bottom)) return true;
    }
    return false;
  }

  function sync(el) {
    // Measured only while it is actually up: getBoundingClientRect forces
    // layout, and this must not do that on every scroll of an idle page.
    if (el.hidden || !el.classList.contains('show')) {
      el.classList.remove('blocked');
      return;
    }
    el.classList.toggle('blocked', !isWarning(el) && hits(el));
  }

  function watch(el) {
    if (!el || el.__pillFit) return;
    el.__pillFit = true;
    var pending = false;
    var soon = function () {
      if (pending) return;
      pending = true;
      global.requestAnimationFrame(function () { pending = false; sync(el); });
    };
    // The pill is shown by adding a class and hidden by [hidden]; watching the
    // attributes is what lets this stay out of both surfaces' save code.
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(soon).observe(el, {
        attributes: true, attributeFilter: ['class', 'hidden']
      });
    }
    global.addEventListener('resize', soon);
    global.addEventListener('orientationchange', soon);
    global.addEventListener('scroll', soon, true);
    // A drawer opening moves the bars under the pill without touching the pill.
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(soon);
      for (var i = 0; i < TARGETS.length; i++) {
        var c = global.document.querySelector(TARGETS[i]);
        if (c) ro.observe(c);
      }
    }
    soon();
  }

  function init() {
    watch(global.document.getElementById('autosaveStatus'));
  }

  if (global.document.readyState === 'loading')
    global.document.addEventListener('DOMContentLoaded', init);
  else init();

  global.SkriblPillFit = { watch: watch, sync: sync, TARGETS: TARGETS };
})(window);
