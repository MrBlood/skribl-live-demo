/* Mirror drawing — reflect each point across the canvas centre, shared by both.
 *
 * A mirrored stroke is drawn as ORDINARY POINTS, exactly like the shape tool:
 * no payload field, no player change, and the reflection replays as a second
 * stroke drawn alongside the first. The player never learns mirroring exists.
 *
 * MODES. `off`, `vertical` (a left/right mirror across the vertical centre
 * line, which is what people mean by "symmetry" nine times in ten),
 * `horizontal`, and `both` (four-way, i.e. a quadrant kaleidoscope).
 *
 * The axis is the CANVAS centre, not the stroke's start. A mirror anchored to
 * wherever you happened to touch down is not a mirror — the two halves drift
 * apart as you draw, and the result cannot be made symmetrical on purpose.
 * Canvas centre also means the axis is stable across strokes, which is the
 * whole point when the figure is built from several of them.
 *
 * Reflections are emitted as SEPARATE strokes, not interleaved into one. A
 * single stroke containing both the original and its mirror would draw a
 * connecting line straight across the canvas between the two halves the moment
 * the replay joins consecutive points — the same class of bug as the stray
 * line, and it would be baked into the payload rather than a live-draw
 * artifact. One group per reflection keeps every segment local to its own half.
 */
(function () {
  'use strict';

  var MODES = ['off', 'vertical', 'horizontal', 'both'];
  var KEY = 'skribl_mirror';
  var mode = 'off';

  try {
    var saved = localStorage.getItem(KEY);
    if (MODES.indexOf(saved) !== -1) mode = saved;
  } catch (e) {}

  function getMode() { return mode; }

  function setMode(m) {
    if (MODES.indexOf(m) === -1) return mode;
    mode = m;
    try { localStorage.setItem(KEY, mode); } catch (e) {}
    return mode;
  }

  function active() { return mode !== 'off'; }

  /* reflect(pt, w, h) -> array of reflected {x, y}, EXCLUDING the original.
   * Empty when mirroring is off, so a caller can loop over it unconditionally.
   */
  function reflect(pt, w, h) {
    if (mode === 'off' || !pt) return [];
    var out = [];
    if (mode === 'vertical' || mode === 'both') out.push({ x: w - pt.x, y: pt.y });
    if (mode === 'horizontal' || mode === 'both') out.push({ x: pt.x, y: h - pt.y });
    if (mode === 'both') out.push({ x: w - pt.x, y: h - pt.y });
    return out;
  }

  /* count() — how many reflections a point produces, for callers that need to
   * size buffers or count groups before generating anything.
   */
  function count() {
    return mode === 'off' ? 0 : (mode === 'both' ? 3 : 1);
  }

  /* create({ seg, onChange }) — wires a seg of [data-mirror] buttons. */
  function create(opts) {
    opts = opts || {};
    var seg = opts.seg || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    if (!seg) return null;

    function render() {
      var btns = seg.querySelectorAll('[data-mirror]');
      for (var i = 0; i < btns.length; i++) {
        var on = btns[i].getAttribute('data-mirror') === mode;
        btns[i].classList.toggle('active', on);
        btns[i].classList.toggle('on', on);
        btns[i].setAttribute('aria-pressed', String(on));
      }
    }

    seg.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-mirror]') : null;
      if (!b || !seg.contains(b)) return;
      setMode(b.getAttribute('data-mirror'));
      render();
      onChange(mode);
    });

    render();
    return { render: render, mode: getMode };
  }

  var api = {
    MODES: MODES.slice(),
    mode: getMode, setMode: setMode, active: active,
    reflect: reflect, count: count, create: create
  };
  if (typeof window !== 'undefined') window.SkriblMirror = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
