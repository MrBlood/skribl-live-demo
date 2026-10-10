/* - and + beside a range slider, for exact steps a slider alone cannot land
 * on with a finger. ONE COPY for both editors: the Pad's (app.js) and Flip's
 * (flip.js) had drifted -- Flip's buttons had no names for a screen reader, no
 * press-and-hold, and stepped past the slider's ends. This is the Pad's.
 *
 *   addSliderNudgers(input, { step, nudgeFn })
 *     step      a fixed step (default: the input's own step, or 1)
 *     nudgeFn   custom behaviour, called with -1 or +1 (the Loop Detail pan)
 *
 * Each press steps the value (press-and-hold repeats) and dispatches a native
 * 'input' event, so every listener (value label, track fill, autosave) fires
 * unchanged. The buttons show the app's drawn marks (lib/marks.js).
 */
function addSliderNudgers(input, opts) {
  opts = opts || {};
  if (!input || input.dataset.nudged) return;
  input.dataset.nudged = '1';
  var parent = input.parentNode;
  var wrap = document.createElement('div');
  wrap.className = 'slider-nudge-wrap';
  parent.insertBefore(wrap, input);
  var minus = document.createElement('button');
  var plus = document.createElement('button');
  minus.type = plus.type = 'button';
  minus.className = plus.className = 'slider-nudge-btn';
  var M = window.SkriblMarks;
  if (M) { M.into(minus, 'minus', '−'); M.into(plus, 'plus', '+'); }
  else { minus.textContent = '−'; plus.textContent = '+'; }
  minus.setAttribute('aria-label', 'Decrease');
  plus.setAttribute('aria-label', 'Increase');
  wrap.appendChild(minus);
  wrap.appendChild(input);   // move the slider between the buttons
  wrap.appendChild(plus);
  var step = opts.step != null ? opts.step : (parseFloat(input.step) || 1);
  function apply(dir) {
    if (opts.nudgeFn) { opts.nudgeFn(dir); return; }
    var min = parseFloat(input.min) || 0;
    var maxRaw = parseFloat(input.max);
    var max = isFinite(maxRaw) ? maxRaw : Infinity;
    var next = (parseFloat(input.value) || 0) + dir * step;
    next = Math.max(min, Math.min(next, max));
    next = Math.round(next / step) * step;
    input.value = next;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function bind(btn, dir) {
    var holdTimer = null, repeat = null;
    var start = function (e) {
      e.preventDefault();
      apply(dir);
      holdTimer = setTimeout(function () { repeat = setInterval(function () { apply(dir); }, 90); }, 350);
    };
    var end = function () { clearTimeout(holdTimer); if (repeat) clearInterval(repeat); repeat = null; };
    btn.addEventListener('mousedown', start);
    btn.addEventListener('touchstart', start, { passive: false });
    btn.addEventListener('mouseup', end);
    btn.addEventListener('mouseleave', end);
    btn.addEventListener('touchend', end);
    btn.addEventListener('touchcancel', end);
    // A keyboard press (Enter, Space) has no mousedown: one step per click.
    btn.addEventListener('click', function (e) { if (e.detail === 0) apply(dir); });
  }
  bind(minus, -1);
  bind(plus, 1);
}
