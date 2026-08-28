/* One size decision, made once, for the whole app.
 *
 * WHY THIS EXISTS. flip.css alone carries eight `max-width` rules — 359, 360,
 * 392, 400, 440, 559, 560, 640 — and styles.css has its own set. That is not a
 * responsive design; it is eight patches, each correct on the day it was
 * written, none of them agreeing about where "small" begins. The visible cost
 * is recorded in this project's own review notes: **one pixel of resize takes
 * Pad's toolbar from 398px to 565px**, and 560–640px gets the phone layout on a
 * viewport with room to spare.
 *
 * The fix those notes ask for is size classes rather than a pixel breakpoint,
 * and the honest first step is to make the DECISION exist somewhere a rule can
 * refer to. Migrating the existing queries onto it is incremental work with
 * verify_layout.py as the safety net; this file is what they migrate TO.
 *
 * IT MEASURES THE VIEWPORT, DELIBERATELY, AND THAT IS NOT THE OBVIOUS CHOICE.
 * The interesting question is whether THIS app has room, not how wide the
 * window is — Skribl is a blueprint a host mounts, possibly beside its own
 * chrome — so the first version measured the root element. verify_sizeclass
 * caught what that costs: `getBoundingClientRect()` on the body excludes the
 * scrollbar, so a 641px viewport measured ~626 and classified COMPACT where the
 * media query it replaces said regular. The boundary moved by ~15px.
 *
 * A migration that moves the boundary is not a migration; it is a design change
 * wearing a refactor's clothes, and this project has a suite for that habit.
 * The `width` media feature includes the scrollbar and so does
 * `window.innerWidth`, so measuring the viewport makes the migrated rules
 * behave identically — which is the entire claim of this step.
 *
 * Container-awareness is still the better long-run answer, and it is a
 * BEHAVIOUR CHANGE to be taken deliberately once the rules have moved: at that
 * point the boundary shifts for embedded hosts on purpose, with the layout
 * suite re-measured, rather than silently on the way past.
 *
 * ONE THRESHOLD, NAMED ONCE. 640 is not a new opinion: it is the boundary the
 * existing rules already used, so migrating a query onto this class is a no-op
 * in behaviour rather than a redesign smuggled in as a refactor. Changing what
 * "compact" means is now one edit here instead of eight edits spread across two
 * stylesheets, which is the entire point.
 *
 * WHAT CONSUMES IT. CSS reads `[data-size="compact"]`; JS reads
 * SkriblSize.get() or listens for `skribl:size`. Both are told on the same
 * frame, so a script and a stylesheet can never disagree about which one the
 * app is in — which is exactly how a control ends up hidden by CSS while its
 * keyboard handler is still live.
 */
(function () {
  'use strict';

  /* The width at which a persistent command row stops fitting. See the note
     above: this is the boundary the old rules already used. */
  var COMPACT_MAX = 640;

  var current = null;
  var root = null;
  var ro = null;

  function classify(width) {
    return width > COMPACT_MAX ? 'regular' : 'compact';
  }

  function apply(width) {
    var next = classify(width);
    if (next === current) return;          // one write per real change
    current = next;
    if (root) root.setAttribute('data-size', next);
    try {
      document.dispatchEvent(new CustomEvent('skribl:size', {
        detail: { size: next, width: width }
      }));
    } catch (e) { /* CustomEvent is ancient; never let a listener break layout */ }
  }

  function measure() {
    // innerWidth, not the root's rect: see the note above. It is the number the
    // `width` media feature uses, scrollbar included, so every rule migrated
    // onto this class breaks at exactly the pixel it always did.
    var w = window.innerWidth || 0;
    if (w > 0) return w;
    // Only if the window cannot answer — a detached document in a test harness,
    // say — fall back to the element, which is better than classifying zero.
    return root ? root.getBoundingClientRect().width : 0;
  }

  function observe(el) {
    root = el || document.body;
    if (!root) return null;
    apply(measure());
    if (typeof ResizeObserver === 'function') {
      if (ro) ro.disconnect();
      ro = new ResizeObserver(function () { apply(measure()); });
      ro.observe(root);
    } else {
      // No ResizeObserver: the window is the only signal available, which is
      // the media-query behaviour this replaces — degraded, not broken.
      window.addEventListener('resize', function () { apply(measure()); });
    }
    return current;
  }

  var api = {
    COMPACT_MAX: COMPACT_MAX,
    observe: observe,
    get: function () { return current; },
    isCompact: function () { return current === 'compact'; },
    /* Exposed for tests: classify a width without touching the DOM, so the
       rule can be checked at boundaries that are awkward to resize a real
       browser to. */
    classify: classify
  };
  if (typeof window !== 'undefined') window.SkriblSize = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
