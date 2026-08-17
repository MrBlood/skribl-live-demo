/* Smoothing (the stroke stabilizer) — shared by both editors.
 *
 * Small, and worth extracting anyway. The two implementations agreed on
 * everything, including the mapping from level to alpha:
 *
 *     off -> 1      low -> 0.5      high -> 0.25
 *
 * That is three magic numbers written out twice. Nothing had gone wrong yet;
 * the point is that a change to one copy would not have failed anything, and
 * "the two surfaces smooth differently" is exactly the kind of bug that gets
 * reported as "Flip feels wrong" and takes an afternoon to locate.
 *
 * The alpha is the ONLY thing shared. Repositioning the segmented pill after a
 * click is injected, because the two surfaces do it differently — Pad through
 * attachSegSlider's observers, Flip through its own positioner — and unifying
 * THAT is a separate job: slider positioning currently exists three times
 * (app.js, flip.js, and lib/segslider.js), which is the next extraction, not
 * this one.
 */
(function () {
  'use strict';

  // Lower alpha eases the drawn point further behind the raw one, so it reads
  // as smoother. 1 disables the stabilizer entirely rather than easing by a
  // factor of one, which matters: both editors branch on `alpha >= 1`.
  var ALPHA = { off: 1, low: 0.5, high: 0.25 };

  function alphaFor(level) {
    return Object.prototype.hasOwnProperty.call(ALPHA, level) ? ALPHA[level] : 1;
  }

  /* create({ seg, onChange, onRender })
   *   seg       the .seg element containing .smooth-btn children
   *   onChange  called with the new alpha whenever the level changes
   *   onRender  called after the active button moves, for pill repositioning
   */
  function create(opts) {
    opts = opts || {};
    var seg = opts.seg || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    var onRender = typeof opts.onRender === 'function' ? opts.onRender : function () {};
    if (!seg) return null;

    function select(btn) {
      var buttons = seg.querySelectorAll('.smooth-btn');
      for (var i = 0; i < buttons.length; i++) {
        // Explicit boolean. classList.toggle(name, undefined) TOGGLES rather
        // than setting, which is how two controls once read as selected at the
        // same time.
        buttons[i].classList.toggle('active', buttons[i] === btn);
      }
      onChange(alphaFor(btn && btn.dataset ? btn.dataset.smooth : 'off'));
      onRender();
    }

    seg.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.smooth-btn') : null;
      if (!btn) return;
      select(btn);
    });

    return {
      alphaFor: alphaFor,
      current: function () {
        var on = seg.querySelector('.smooth-btn.active');
        return alphaFor(on && on.dataset ? on.dataset.smooth : 'off');
      }
    };
  }

  window.SkriblSmoothing = { create: create, alphaFor: alphaFor, ALPHA: ALPHA };
}());
