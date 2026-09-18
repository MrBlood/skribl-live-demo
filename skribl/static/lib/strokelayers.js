/* Stroke layers — the see-through-stroke compositor's on/off, shared by both.
 *
 * Both editors already had the BEHAVIOUR, implemented separately: Pad's wet/dry
 * compositor (guarded by `window.SKRIBL_STROKE_LAYERS !== false`) and Flip's
 * per-stroke alpha layer in paintStatic(). Neither had a control, so the only
 * way to see what either did was to set a global by hand in a console.
 *
 * What is shared is the SETTING and its persistence, not the compositing. The
 * two implementations differ for real reasons — Pad composites live as you draw
 * (there is a stroke in progress), Flip composites whole strokes on repaint
 * (there is a frame to rebuild) — so unifying them would be a rewrite, not an
 * extraction. Both read the same `window.SKRIBL_STROKE_LAYERS`, which is the
 * one fact that has to agree.
 *
 * Default ON: `!== false` means an absent key and an unparsable one both read
 * as on, so a first visit composites exactly as it always did.
 */
(function () {
  'use strict';

  var KEY = 'skribl_stroke_layers';
  var on = true;

  try { on = localStorage.getItem(KEY) !== 'off'; } catch (e) {}

  function apply() {
    if (typeof window !== 'undefined') window.SKRIBL_STROKE_LAYERS = on;
  }
  apply();

  function enabled() { return on; }

  function setEnabled(v) {
    on = !!v;
    apply();
    try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch (e) {}
    return on;
  }

  /* create({ btn, onChange }) — wires a role="switch" button. Returns null when
   * absent, like every lib here, so a surface without the markup is untouched.
   */
  function create(opts) {
    opts = opts || {};
    var btn = opts.btn || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    if (!btn) return null;

    function render() {
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-checked', String(on));
    }

    btn.addEventListener('click', function () {
      setEnabled(!on);
      render();
      onChange(on);
    });

    render();
    return { render: render, enabled: enabled };
  }

  /* HOW MUCH LAYERING ONE FRAME CAN AFFORD.
   *
   * Layering costs a full-canvas round trip per see-through stroke. One or a
   * dozen is nothing; a few hundred is a frame that composites more than it
   * draws, and Flip playback stalled on exactly that. Flip grew a ceiling for
   * it; the PLAYER did not, so a document could play smoothly in the editor
   * and stall for a viewer — the same surfaces-disagree shape as the hold bug.
   *
   * Counting stops as soon as the budget is exceeded: the answer past that
   * point is "too many", and a long frame should not pay to learn how many.
   *
   * `alphaFn` is passed in because the two surfaces reach their alpha through
   * their own parsers. It must return < 1 only for a stroke that would
   * actually be layered. */
  var BUDGET = 24;

  function overBudget(strokeArr, alphaFn) {
    if (!strokeArr || !strokeArr.length) return false;
    var n = 0, i = 0, j, p;
    while (i < strokeArr.length) {
      j = i + 1;
      while (j < strokeArr.length && !strokeArr[j].start) j++;
      p = strokeArr[i];
      if (p && !p.erase && alphaFn(p.color) < 1) n++;
      if (n > BUDGET) return true;
      i = j;
    }
    return false;
  }

  /* A UNIFORM SEE-THROUGH RUN IS ONE PATH, not a dot plus a line per segment:
   * drawn per segment it composites against itself wherever the round caps
   * overlap, which on a polyline is everywhere, and a smear ghost written at
   * alpha 46/255 painted at 83. One path cannot stack against itself and is
   * FEWER calls than the walk, so unlike the layer above it needs no budget.
   * Only for a run of one colour and one width -- true of a generated ghost,
   * false of a pressure stroke, which still gets the layer. Returns the run's
   * alpha, or 0. `alphaFn` must read every form the alpha arrives in, the
   * 8-digit hex included; a LAYERING parser here disables this rather than
   * breaking it. flip.js paintSeg carries the full reasoning -- it is not in
   * any byte budget and this file is in two. */
  function uniformRun(seg, alphaFn) {
    var p = seg[0], a, i, q;
    if (seg.length < 2 || p.erase || !((a = alphaFn(p.color)) < 1)) return 0;
    for (i = 1; i < seg.length; i++) { q = seg[i];
      if (q.erase || q.color !== p.color || q.size !== p.size) return 0; }
    return a;
  }

  /* THE OTHER QUESTION, AND IT IS NOT THE SAME ONE. uniformRun above asks "can
   * this be ONE path?" -- which needs one colour and one width. Compositing
   * asks something narrower: "is there ONE alpha?" A run can fail the first
   * and pass the second, and that gap is where a smudged generated page lives.
   *
   * Measured on a smeared ring after a 60-step smudge: the touched runs carry
   * 3 to 5 distinct colours and 11 to 17 distinct SIZES -- SMUDGE_SPREAD_MAX
   * widens every point by its own accumulator -- while alphaMin and alphaMax
   * are equal to four decimals in every one of them. mix() preserves the
   * hex-8 alpha, so the drag moves pigment and width and never opacity.
   *
   * It matters because the fallback walk draws each segment separately, and
   * translucent round caps COMPOUND where they meet. Same fixture, a run
   * written at alpha 0.0314 -- a single path would paint 8:
   *
   *     midpoint between vertices   11.2     (1.4x, caps overlapping along the run)
   *     at the vertices             15.1     (1.9x, two caps on one point)
   *
   * That 35% ripple at the vertex spacing IS the mesh a smudge leaves on a
   * Motion Smear. A uniform alpha is exactly the licence to draw the run
   * solid on a layer and composite it once, which cannot compound at all. */
  function uniformAlpha(seg, alphaFn) {
    var p, a, i, q;
    if (!seg || seg.length < 2) return 0;
    p = seg[0];
    if (p.erase) return 0;
    a = alphaFn(p.color);
    if (!(a < 1)) return 0;
    for (i = 1; i < seg.length; i++) { q = seg[i];
      if (q.erase || alphaFn(q.color) !== a) return 0; }
    return a;
  }

  var api = { enabled: enabled, setEnabled: setEnabled, create: create,
              BUDGET: BUDGET, overBudget: overBudget, uniformRun: uniformRun,
              uniformAlpha: uniformAlpha };
  if (typeof window !== 'undefined') window.SkriblStrokeLayers = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
