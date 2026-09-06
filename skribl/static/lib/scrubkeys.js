/* Keyboard operation and live value for the three playback scrubbers.
 *
 *   SkriblScrub.attach(el, { seek: frac => …, frac: () => 0..1 });
 *   SkriblScrub.sync(el, 0.42);   // after every frame that moves the position
 *
 * WHY THIS EXISTS. An accessibility audit of v278 found all three players
 * pointer-exclusive. Pad and Flip declared `role="slider"` with
 * `aria-valuemin`/`aria-valuemax` and then supplied no `tabindex`, no
 * `aria-valuenow` and not one key handler — so the markup claimed a control
 * that could not be focused, could not be operated, and never reported where
 * it was. The shared /s/<id> player did not even claim it: a bare div with
 * mousedown/touchstart. Seeking was mouse-or-touch or nothing, on every
 * surface, including the one strangers get sent a link to.
 *
 * ROLE=SLIDER IS A PROMISE. Declaring it and stopping there is worse than
 * leaving the div undecorated, because a screen reader then announces a slider
 * to somebody who cannot move it. This file is the rest of that promise:
 * focusable, arrow/Home/End/PageUp/PageDown operable, and a value that is kept
 * current rather than declared once.
 *
 * WHY NOT <input type="range">, which is the obvious answer. Three surfaces
 * already style a div-and-fill to match their own chrome, and the swap would
 * be a visual rewrite of all three plus their pixel comparisons, to reach the
 * same place. The div route needs exactly what is below, and it is small.
 *
 * PERCENT, NOT SECONDS. The value range is 0-100 because that is what the
 * existing aria-valuemin/max already declared and what every caller has to
 * hand; `aria-valuetext` carries the human form so a screen reader says
 * "42 percent" rather than a bare number with no unit.
 */
(function (global) {
  'use strict';

  /* One arrow press. 2% is a compromise measured against the shortest
     drawings this plays: a 2-second Skribl steps 40ms, which is finer than a
     pointer drag can reliably hit, while a 60-second one steps 1.2s and is
     still crossable without holding the key down for a minute. Page steps are
     five of those. */
  var STEP = 2;
  var PAGE = 10;

  function clamp(v) { return v < 0 ? 0 : (v > 100 ? 100 : v); }

  function attach(el, opts) {
    if (!el || !opts || typeof opts.seek !== 'function') return;
    if (el._skriblScrub) return;                 /* idempotent */
    el._skriblScrub = true;

    /* The attributes the markup claimed but never supplied. Set here rather
       than in the templates so a surface cannot declare the role without
       getting the behaviour — the exact split that produced the finding. */
    el.setAttribute('role', 'slider');
    el.setAttribute('tabindex', '0');
    if (!el.hasAttribute('aria-valuemin')) el.setAttribute('aria-valuemin', '0');
    if (!el.hasAttribute('aria-valuemax')) el.setAttribute('aria-valuemax', '100');
    sync(el, typeof opts.frac === 'function' ? opts.frac() : 0);

    el.addEventListener('keydown', function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      var now = (typeof opts.frac === 'function' ? opts.frac() : 0) * 100;
      var next = null;
      switch (e.key) {
        case 'ArrowRight': case 'ArrowUp':   next = now + STEP; break;
        case 'ArrowLeft':  case 'ArrowDown': next = now - STEP; break;
        case 'PageUp':                       next = now + PAGE; break;
        case 'PageDown':                     next = now - PAGE; break;
        case 'Home':                         next = 0; break;
        case 'End':                          next = 100; break;
        default: return;
      }
      /* preventDefault ONLY once a key is handled: Home/End/PageUp scroll the
         page otherwise, and swallowing every key would trap Tab as well. */
      e.preventDefault();
      next = clamp(next);
      opts.seek(next / 100);
      sync(el, next / 100);
    });
  }

  /* Called from the render loop. Cheap enough to run per frame — two attribute
     writes — and it has to, because a value that is only set on keypress is
     wrong the moment playback moves on its own. */
  function sync(el, frac) {
    if (!el) return;
    var pct = Math.round(clamp((frac || 0) * 100));
    el.setAttribute('aria-valuenow', String(pct));
    el.setAttribute('aria-valuetext', pct + '%');
  }

  global.SkriblScrub = { attach: attach, sync: sync, STEP: STEP };
})(window);
