/* Eraser size — shared by both editors.
 *
 * The eraser was three times the pen, and that 3 was written out SEVEN times:
 *
 *     app.js  640  startDraw        pressureSize(e, erase ? size * 3 : size, erase)
 *     app.js  672  continueDraw     pressureSize(e, erase ? size * 3 : size, erase)
 *     app.js  700  snapStrokeToFinal            (erase ? size * 3 : size)
 *     app.js 2533  eraser cursor    size * 3 * scale
 *     flip.js 785  stroke start     sizeFor(e, erasing ? size*3 : size)
 *     flip.js 810  stroke continue  sizeFor(e, erasing ? size*3 : size)
 *     flip.js 884  eraser cursor    size * 3 * (r.width / CW)
 *
 * Same shape as MAX_LOOP_SECONDS before lib/looptrim.js: a constant duplicated
 * across both surfaces with nothing forcing the copies to agree, so changing
 * the eraser meant seven edits and missing one failed nothing. Note the two
 * CURSOR sites — those are the ones that would silently drift out of step and
 * leave the ring lying about how much it erases, which is worse than a wrong
 * number because the user is aiming with it.
 *
 * The multiplier is now a SETTING rather than a constant (default 3, unchanged),
 * so this module owns both the value and its persistence. Both editors read it
 * through sizeFor(); neither stores a copy.
 */
(function () {
  'use strict';

  var KEY = 'skribl_eraser_mult';
  var ALLOWED = [2, 3, 5];          // the seg's choices; 3 is the shipped default
  var DEFAULT = 3;
  var mult = DEFAULT;

  try {
    var raw = parseFloat(localStorage.getItem(KEY));
    if (ALLOWED.indexOf(raw) !== -1) mult = raw;
  } catch (e) {}

  function eraserMult() { return mult; }

  function setEraserMult(n) {
    n = parseFloat(n);
    if (ALLOWED.indexOf(n) === -1) return mult;    // unknown value: keep the current one
    mult = n;
    try { localStorage.setItem(KEY, String(mult)); } catch (e) {}
    return mult;
  }

  /* sizeFor(size, erase) — the ONE place the pen/eraser branch lives.
   * Callers pass their nominal brush size and whether this is an erase stroke.
   */
  function sizeFor(size, erase) {
    return erase ? size * mult : size;
  }

  /* create({ seg, onChange }) — wires a segmented control whose buttons carry
   * data-eraser="<n>". Returns null when the seg is absent, like every other
   * lib here, so a surface without the markup is simply untouched.
   */
  function create(opts) {
    opts = opts || {};
    var seg = opts.seg || null;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    if (!seg) return null;

    function render() {
      var buttons = seg.querySelectorAll('[data-eraser]');
      for (var i = 0; i < buttons.length; i++) {
        var on = parseFloat(buttons[i].getAttribute('data-eraser')) === mult;
        buttons[i].classList.toggle('active', on);
        buttons[i].classList.toggle('on', on);     // Flip's segs light via .on
        buttons[i].setAttribute('aria-pressed', String(on));
      }
    }

    seg.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('[data-eraser]') : null;
      if (!btn || !seg.contains(btn)) return;
      setEraserMult(btn.getAttribute('data-eraser'));
      render();
      onChange(mult);
    });

    render();
    return { render: render, value: eraserMult };
  }

  var api = {
    DEFAULT: DEFAULT,
    ALLOWED: ALLOWED.slice(),
    eraserMult: eraserMult,
    setEraserMult: setEraserMult,
    sizeFor: sizeFor,
    create: create
  };

  if (typeof window !== 'undefined') window.SkriblEraser = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
