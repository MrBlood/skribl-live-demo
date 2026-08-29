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
 * IT LIFTS RATHER THAN HIDES (v229), AND THE FIRST VERSION HAD THIS WRONG.
 * The original remedy for the collision was to fade the pill out. On a desktop
 * that fires almost never. On a phone the pill's fixed bottom-left corner
 * overlaps the tool row at EVERY size — this file's own header says so — so
 * the remedy ran every single time and the reassuring "Saved" was never
 * visible on a phone AT ALL. The bug report was exactly that: "on pad I'm not
 * seeing saved at all on autosave."
 *
 * Worse, it interacted. Warnings are exempt from fading (below), so the only
 * pill state a phone user could ever see was an amber warning; the green
 * "Saved" that should have replaced it was hidden by this file. A stuck
 * warning was the DESIGNED behaviour of the two mechanisms combined, and
 * neither was wrong on its own.
 *
 * So the pill now moves above the bars it would cover and only falls back to
 * fading when there is no room above to move into. Hiding a status was always
 * the second-best answer to "these two things overlap".
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
     editors; anything not present on a surface is skipped.
     `.addcol` is Flip's Duplicate/Blank/In-between row. It joined the list when
     lifting the pill off the tool row landed it on those buttons instead —
     clearing one bar is not the job, clearing the stack is.

     `#toolTray` and `#shapePop` are POPOVERS rather than bars, and they were
     missed for exactly that reason: this list read as "the bottom chrome" when
     what it means is "anything the pill must not cover". A photo from the live
     demo showed "Saving…" parked squarely on the Pen cell of an open tray.
     They are tall, so lifting usually cannot clear them and the pill fades
     instead — which is right: a transient status has no business competing
     with a menu the user just opened, and a WARNING still refuses to fade. */
  var TARGETS = ['.flip-tools', '.toolbar', '#pagebar', '#selbar', '#strip',
                 '.addcol', '#toolTray', '#shapePop', '#stampPop'];
  var WARNING = ['failed', 'partial'];

  function isWarning(el) {
    for (var i = 0; i < WARNING.length; i++)
      if (el.classList.contains(WARNING[i])) return true;
    return false;
  }

  /* Gap left between the pill and whatever it clears. */
  var GAP = 8;

  /* WRITE ONLY WHAT CHANGES, and this is not a micro-optimisation — it is what
   * stops this file spinning forever. `classList.remove()` sets the class
   * attribute even when the token was not there, and setting an attribute fires
   * a MutationObserver record even when the value is identical. This file
   * observes the pill's own class attribute, so every unconditional write fed
   * itself: rAF -> sync -> write -> mutation -> rAF, at frame rate, on an idle
   * page with the pill HIDDEN. Measured on a phone viewport, 3 seconds after
   * everything had settled: 133 mutations before this guard existed, 364 once
   * lifting added two more unconditional writes per pass, and 0 after. A
   * drawing app that keeps a requestAnimationFrame loop alive while nothing is
   * happening is spending someone's battery to do nothing at all.
   */
  function setFlag(el, name, on) {
    if (el.classList.contains(name) === on) return;
    if (on) el.classList.add(name); else el.classList.remove(name);
  }

  function setLift(el, px) {
    var want = px > 0 ? px + 'px' : '';
    if (el.style.getPropertyValue('--pill-lift') === want) return;
    if (want) el.style.setProperty('--pill-lift', want);
    else el.style.removeProperty('--pill-lift');
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

  function currentLift(el) {
    var v = parseFloat(el.style.getPropertyValue('--pill-lift'));
    return v > 0 ? v : 0;
  }

  /* The lift that clears every bottom bar the pill shares a column with.
   *
   * COMPUTED ABSOLUTELY, NOT INCREMENTALLY, and that is what keeps it stable.
   * This runs from a MutationObserver on the pill's own class attribute, so a
   * relative nudge ("move up by the current overlap") would re-enter, measure
   * the moved pill, nudge again and oscillate. Instead it derives where the
   * pill's bottom edge SHOULD be and lifts by the difference from where the
   * un-lifted pill sits, so applying the answer twice gives the same answer.
   */
  function wantLift(el) {
    var r = el.getBoundingClientRect();
    if (!r.width || !r.height) return 0;
    var lift = currentLift(el);
    var unliftedBottom = r.bottom + lift;
    var half = (global.innerHeight || 0) / 2;
    var top = Infinity;
    for (var i = 0; i < TARGETS.length; i++) {
      var c = global.document.querySelector(TARGETS[i]);
      if (!c) continue;
      var b = c.getBoundingClientRect();
      if (!b.width || !b.height) continue;
      // Bottom-anchored bars only. A bar in the upper half of the screen is
      // not what a bottom-left pill collides with, and lifting to clear one
      // would send the pill off the top.
      if (b.bottom < half) continue;
      // Same column, or it is not in the way at all.
      if (r.right <= b.left || r.left >= b.right) continue;
      if (b.top < top) top = b.top;
    }
    if (top === Infinity) return 0;
    return Math.max(0, unliftedBottom - (top - GAP));
  }

  function sync(el) {
    // Measured only while it is actually up: getBoundingClientRect forces
    // layout, and this must not do that on every scroll of an idle page.
    if (el.hidden || !el.classList.contains('show')) {
      setFlag(el, 'blocked', false);
      setFlag(el, 'lifted', false);
      setLift(el, 0);
      return;
    }
    var lift = wantLift(el);
    var r = el.getBoundingClientRect();
    // Room above to move into? The pill's top once lifted, from its un-lifted
    // position, must stay on screen.
    var liftedTop = (r.top + currentLift(el)) - lift;
    if (lift > 0 && liftedTop >= GAP) {
      setLift(el, lift);
      setFlag(el, 'lifted', true);
      setFlag(el, 'blocked', false);
      return;
    }
    setFlag(el, 'lifted', false);
    setLift(el, 0);
    // No room to lift into: fall back to the original remedy, which still
    // never applies to a warning.
    setFlag(el, 'blocked', !isWarning(el) && hits(el));
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
      // sync() writes `class` and `style`, which is what this observes. The
      // rAF coalescing below already collapses a burst into one pass, and
      // wantLift() is idempotent, so the loop settles after one extra frame
      // instead of running away — but only because the lift is absolute. Keep
      // it that way; a relative nudge here spins forever.
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
