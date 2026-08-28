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
 * IT MEASURES THE ELEMENT, NOT THE VIEWPORT — and that is a DELIBERATE
 * BEHAVIOUR CHANGE, taken in v227 for a specific reason, not a refactor.
 *
 * The history matters because the reasoning reversed. v226 measured
 * `window.innerWidth`, on the grounds that a migration must not move the
 * boundary: the CSS `width` feature includes the scrollbar and so does
 * innerWidth, whereas `getBoundingClientRect()` on the body excludes it, so an
 * element-measured 641px viewport read ~626 and classified COMPACT where the
 * query it replaced said regular. verify_sizeclass caught that at the time and
 * the viewport won, correctly, because the claim being made was "no-op".
 *
 * THE OWNER THEN SUPPLIED THE CASE THAT SETTLES IT. The host site reserves a
 * COLUMN for Pad and Flip — around 510px, to be confirmed. Inside a 1400px
 * window that column is 510px wide, and `window.innerWidth` says 1400: the app
 * would classify REGULAR and lay out a persistent command row into a space that
 * cannot hold one. Viewport measurement is not merely less good there, it is
 * wrong in the product's primary embedding, and wrong in the direction that
 * breaks the layout rather than the direction that wastes space.
 *
 * So the question this asks is the one those eight rules always meant: does THIS
 * app have room. What it costs is the ~15px band the earlier note describes —
 * a standalone desktop window between 641 and about 655 now classifies compact
 * where a media query would say regular. That band is taken knowingly, it is
 * asserted below rather than discovered later, and the layout suite was
 * re-measured across it.
 *
 * WHILE THE MIGRATION IS PARTIAL the migrated rule and the remaining media
 * queries therefore disagree inside that band. That is the honest cost of a
 * half-finished migration and an argument for finishing it, not for measuring
 * the wrong thing in the meantime.
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

  function apply(width, quiet) {
    var next = classify(width);
    if (next === current) return;          // one write per real change
    current = next;
    if (root) root.setAttribute('data-size', next);
    // THE FIRST CLASSIFICATION DOES NOT ANNOUNCE ITSELF, and that is not a
    // nicety. `skribl:size` means "the class CHANGED"; going from nothing to a
    // value while the page is still parsing is not a change anyone can act on,
    // and acting on it is actively unsafe: flip.js is a classic script, and a
    // listener that rebuilds the strip during init reaches `updateToolState()`
    // and through it a `const` declared 250 lines further down. That threw
    // "Cannot access 'playBtn' before initialization" — the exact temporal-dead-
    // zone hazard this file's own header warns about — and took every handler
    // after it with it. The attribute is still stamped, which is all the initial
    // classification is for; the surfaces build themselves during init anyway.
    if (quiet) return;
    try {
      document.dispatchEvent(new CustomEvent('skribl:size', {
        detail: { size: next, width: width }
      }));
    } catch (e) { /* CustomEvent is ancient; never let a listener break layout */ }
  }

  function measure() {
    // The ELEMENT, so an app given a 510px column inside a 1400px window knows
    // it has 510px. See the note above for what this costs and why it is worth
    // it. Fractional on purpose: a layout landing on 640.4 is not 640.
    var w = root ? root.getBoundingClientRect().width : 0;
    if (w > 0) return w;
    // A detached or display:none root measures 0, which would stamp `compact`
    // as an answer nobody asked for. The window is the only other thing known.
    return window.innerWidth || 0;
  }

  function observe(el) {
    root = el || document.body;
    if (!root) return null;
    apply(measure(), true);        // stamp, do not announce — see apply()
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
