/* Stylus pressure — the curve, the floor, and the on/off, shared by both editors.
 *
 * `PRESSURE_MIN = 0.35` and the line that uses it existed twice, once per
 * surface, identically:
 *
 *     base * (PRESSURE_MIN + (1 - PRESSURE_MIN) * Math.min(1, raw))
 *
 * Same shape as the eraser multiplier and MAX_LOOP_SECONDS before it: nothing
 * had gone wrong, but a change to one copy would have failed nothing, and
 * "the pen feels different on Flip" is a bug that costs an afternoon to find.
 *
 * WHAT IS DELIBERATELY *NOT* SHARED: reading the raw value off the event. The
 * two editors bind different event families — Pad uses mouse/touch and reads
 * `touch.touchType === 'stylus'` with `touch.force` (an iOS extension), Flip
 * uses Pointer Events and reads `e.pressure`. Code written for one is dead in
 * the other, silently, so each surface keeps its own extraction and passes the
 * number here. Only the curve and the setting are common.
 *
 * The toggle matters beyond taste: the stylus path is unverified on real
 * hardware (no Touch constructor supports `touchType`, so an Apple Pencil
 * stroke cannot be synthesised in Chromium), which makes an off switch the
 * escape hatch if a device reports pressure badly.
 */
(function () {
  'use strict';

  var KEY = 'skribl_pressure';
  // The lightest touch still draws at 35% of the nominal width rather than
  // vanishing. Kept as the floor of the curve, not a separate clamp.
  var PRESSURE_MIN = 0.35;
  var enabled = true;

  try { enabled = localStorage.getItem(KEY) !== 'off'; } catch (e) {}

  function isEnabled() { return enabled; }

  function setEnabled(on) {
    enabled = !!on;
    try { localStorage.setItem(KEY, enabled ? 'on' : 'off'); } catch (e) {}
    return enabled;
  }

  /* sizeFrom(base, raw)
   *   base  the nominal brush width
   *   raw   0..1 from the device, or 0/undefined when there is no reading
   *
   * A stylus commonly reports 0 on the FIRST event of a stroke. That is "no
   * reading yet", not a feather touch — treating it literally starts every
   * line at minimum width, which both surfaces had already learned separately.
   */
  function sizeFrom(base, raw) {
    if (!enabled) return base;
    if (!(raw > 0)) return base;
    return base * (PRESSURE_MIN + (1 - PRESSURE_MIN) * Math.min(1, raw));
  }

  /* create({ seg, onChange }) — wires a two-button seg carrying
   * data-pressure="on|off". Returns null when absent, like every lib here.
   */
  function create(opts) {
    opts = opts || {};
    var seg = opts.seg || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    if (!seg) return null;

    function render() {
      var btns = seg.querySelectorAll('[data-pressure]');
      for (var i = 0; i < btns.length; i++) {
        var on = (btns[i].getAttribute('data-pressure') === 'on') === enabled;
        btns[i].classList.toggle('active', on);
        btns[i].classList.toggle('on', on);
        btns[i].setAttribute('aria-pressed', String(on));
      }
    }

    seg.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-pressure]') : null;
      if (!b || !seg.contains(b)) return;
      setEnabled(b.getAttribute('data-pressure') === 'on');
      render();
      onChange(enabled);
    });

    render();
    return { render: render };
  }

  var api = {
    PRESSURE_MIN: PRESSURE_MIN,
    enabled: isEnabled,
    setEnabled: setEnabled,
    sizeFrom: sizeFrom,
    create: create
  };

  if (typeof window !== 'undefined') window.SkriblPressure = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
