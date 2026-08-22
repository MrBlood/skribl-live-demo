/* Brushes — presets expressed entirely through per-point size and colour.
 *
 * NO PAYLOAD FIELD, for the same reason shapes and mirror have none. The player
 * replays {x, y, color, size, t, start, erase} by calling drawLine with the
 * stored colour and width; it has no notion of a brush and must not need one. A
 * brush therefore SHAPES the numbers as the stroke is captured, and the result
 * replays identically on a player that has never heard of this file.
 *
 * That constraint is what makes the preset list honest. Anything a brush wants
 * to do that cannot be said in a width and an rgba() — texture, scatter, dual
 * tone, blend modes — is not available, and pretending otherwise would mean a
 * schema change and new rendering in the player.
 *
 * WHAT EACH PRESET ACTUALLY DOES:
 *
 *   pen       Unchanged: the width you set, the opacity you set. The default,
 *             and byte-identical to the behaviour before this file existed.
 *   marker    Wider and slightly translucent, constant width. Reads as a felt
 *             tip because overlaps stay flat — which is exactly what the
 *             stroke-layer compositor already guarantees for a translucent
 *             stroke, so the two features cooperate rather than fight.
 *   pencil    Thinner, and TAPERED BY SPEED: a fast segment draws lighter and
 *             narrower, a slow one darker and fuller. That is the one property
 *             here that needs the stroke's motion rather than just its
 *             settings, and it is why shape(...) takes a speed.
 *   airbrush  Much wider and much fainter. Builds up by overlapping passes,
 *             which again relies on the stroke layer to keep one pass even.
 *
 * SPEED IS MEASURED IN PIXELS PER POINT, not per millisecond. Point spacing is
 * what the eye reads as "drawn fast", and it is available on every surface
 * without a clock — Pad captures on mouse/touch move and Flip on pointermove,
 * at whatever rate the device reports, so a millisecond-based taper would draw
 * differently on a 60Hz and a 120Hz screen for the same gesture.
 */
(function () {
  'use strict';

  var KEY = 'skribl_brush';

  var PRESETS = {
    pen:      { width: 1.0,  alpha: 1.0,  taper: 0 },
    marker:   { width: 1.55, alpha: 0.72, taper: 0 },
    pencil:   { width: 0.62, alpha: 0.9,  taper: 0.55 },
    airbrush: { width: 2.6,  alpha: 0.22, taper: 0.15 }
  };
  var NAMES = ['pen', 'marker', 'pencil', 'airbrush'];
  var current = 'pen';

  try {
    var saved = localStorage.getItem(KEY);
    if (NAMES.indexOf(saved) !== -1) current = saved;
  } catch (e) {}

  function name() { return current; }
  function preset() { return PRESETS[current] || PRESETS.pen; }

  function setBrush(n) {
    if (NAMES.indexOf(n) === -1) return current;
    current = n;
    try { localStorage.setItem(KEY, current); } catch (e) {}
    return current;
  }

  /* shape(base, speedPx) -> the width to capture for this point.
   *
   * `speedPx` is the distance from the previous captured point. The taper is
   * clamped: a stroke that never drops below half width still reads as a
   * pencil, whereas an unclamped taper vanishes on a fast flick and leaves a
   * gap in the middle of a line, which looks like dropped input rather than
   * expression.
   */
  function shape(base, speedPx) {
    var p = preset();
    var w = base * p.width;
    if (p.taper > 0 && speedPx > 0) {
      var fast = Math.min(1, speedPx / 28);        // 28px between points ~ a quick flick
      w *= (1 - p.taper * fast);
    }
    return Math.max(0.5, w);
  }

  /* alphaFor(strokeOpacity) -> the opacity to capture, combining the user's
   * opacity slider with the brush's own. Multiplied, not replaced: a user who
   * has set 40% opacity and picks the airbrush wants fainter still, not the
   * airbrush's 22% overriding their choice.
   */
  function alphaFor(strokeOpacity) {
    var a = (typeof strokeOpacity === 'number' ? strokeOpacity : 1) * preset().alpha;
    return Math.max(0.02, Math.min(1, a));
  }

  /* colorFor(hex, strokeOpacity) -> '#rrggbb' or 'rgba(...)', matching exactly
   * what penColorFor() already produces, so stored colours stay in the two
   * shapes the rest of the code (parseStrokeAlpha, solidStrokeColor, the nib
   * tint) already parses.
   */
  function colorFor(hex, strokeOpacity) {
    var a = alphaFor(strokeOpacity);
    if (a >= 1) return hex;
    var h = (hex || '#ffffff').replace('#', '');
    var r = parseInt(h.slice(0, 2), 16),
        g = parseInt(h.slice(2, 4), 16),
        b = parseInt(h.slice(4, 6), 16);
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + a + ')';
  }

  function create(opts) {
    opts = opts || {};
    var seg = opts.seg || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    if (!seg) return null;
    function render() {
      var btns = seg.querySelectorAll('[data-brush]');
      for (var i = 0; i < btns.length; i++) {
        var on = btns[i].getAttribute('data-brush') === current;
        btns[i].classList.toggle('active', on);
        btns[i].classList.toggle('on', on);
        btns[i].setAttribute('aria-pressed', String(on));
      }
    }
    seg.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-brush]') : null;
      if (!b || !seg.contains(b)) return;
      setBrush(b.getAttribute('data-brush'));
      render();
      onChange(current);
    });
    render();
    return { render: render, name: name };
  }

  var api = {
    NAMES: NAMES.slice(), PRESETS: PRESETS,
    name: name, setBrush: setBrush, preset: preset,
    shape: shape, alphaFor: alphaFor, colorFor: colorFor, create: create
  };
  if (typeof window !== 'undefined') window.SkriblBrush = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
