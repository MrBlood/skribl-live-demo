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

  /* A UNIFORM SEE-THROUGH RUN IS ONE PATH, NOT A DOT PLUS A LINE PER SEGMENT.
   *
   * This is the v225 beading again, in the one place neither the layer above
   * nor the player's compositor reaches. A run drawn the naive way issues a
   * fill and then a stroke() per segment, and each one composites against the
   * last: where the round caps overlap -- which on a polyline is EVERYWHERE --
   * translucent ink stacks. Measured on a Motion Smear ghost written at alpha
   * 46/255: the pixels came out at 83, and the trail wore a ladder of bright
   * bands the owner spotted in a render.
   *
   * The layer fixes this by compositing the run once, and costs a full-canvas
   * round trip to do it -- which is why generated pages are kept off it, and
   * why both surfaces' LAYERING parsers deliberately cannot read the 8-digit
   * hex a smear writes. A single canvas path buys the same thing for nothing:
   * one path cannot stack against itself, and it is FEWER calls than the
   * per-segment walk, not more.
   *
   * It only applies where every point of the run shares a colour and a width.
   * That is exactly true of a generated ghost and exactly false of a hand-drawn
   * stroke, whose width follows pressure -- so the strokes that need the layer
   * still get it, and this never silently flattens one.
   *
   * Returns the run's alpha when it can be drawn as one path, 0 when it cannot.
   * `alphaFn` is the caller's parser, as with overBudget -- but this one MUST
   * see every form the alpha can arrive in, including that hex. Passing a
   * layering parser here disables the fast path rather than breaking it. */
  function uniformRun(seg, alphaFn) {
    if (!seg || seg.length < 2) return 0;
    var p = seg[0];
    if (p.erase) return 0;
    var a = alphaFn(p.color);
    if (!(a < 1)) return 0;
    for (var i = 1; i < seg.length; i++) {
      var q = seg[i];
      if (q.erase || q.color !== p.color || q.size !== p.size) return 0;
    }
    return a;
  }

  var api = { enabled: enabled, setEnabled: setEnabled, create: create,
              BUDGET: BUDGET, overBudget: overBudget, uniformRun: uniformRun };
  if (typeof window !== 'undefined') window.SkriblStrokeLayers = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
