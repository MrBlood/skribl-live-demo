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

  var api = { enabled: enabled, setEnabled: setEnabled, create: create };
  if (typeof window !== 'undefined') window.SkriblStrokeLayers = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
