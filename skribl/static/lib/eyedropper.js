/* Eyedropper — the armed-state machine, shared by both editors.
 *
 * WHY ONE PATH AND NOT TWO. Pad used to call the browser's native
 * `window.EyeDropper` when present and fall back to tap-to-sample otherwise;
 * Flip only ever did tap-to-sample. That native branch is not an ALTERNATIVE
 * to the fallback, it is an EXTRA: Safari, Firefox and every browser on iOS
 * have no EyeDropper, so the in-app path has to exist regardless. Keeping both
 * meant maintaining two implementations forever and shipping two different
 * experiences behind one button depending on which browser opened it.
 *
 * It was also the wrong semantics. The native picker samples anything on the
 * screen, including other applications, when the thing being asked for is "the
 * colour of that part of my drawing". And an OS-level dialog cannot be driven
 * by the harness, so the path most desktop users took was the path no
 * assertion could reach.
 *
 * Deleting it removes a path rather than adding one. The cost is that desktop
 * Chrome loses screen-wide sampling; if that is wanted back it belongs here,
 * once, not in one editor only.
 *
 * WHAT THIS OWNS: armed/disarmed, the button's class and aria-pressed, the
 * canvas cursor, Escape, and the one-shot semantics (a sample disarms).
 * WHAT IT DOES NOT: reading the pixel. Pad and Flip genuinely differ there —
 * different contexts, device-pixel-ratio handling and transparent-pixel
 * fallbacks — so `onSample` is injected and each surface keeps its own.
 */
(function () {
  'use strict';

  function create(opts) {
    opts = opts || {};
    var button = opts.button || null;
    var surface = opts.surface || null;             // element that shows the cursor
    var idleCursor = opts.idleCursor || '';         // Pad restores '', Flip 'none'
    var onSample = typeof opts.onSample === 'function' ? opts.onSample : function () {};
    var onArm = typeof opts.onArm === 'function' ? opts.onArm : function () {};
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {};
    var armed = false;

    function apply() {
      if (button) {
        button.classList.toggle('picking', armed);
        // An armed mode indistinguishable from an unarmed one makes the next
        // canvas tap a surprise, and a class alone says nothing to a screen
        // reader.
        button.setAttribute('aria-pressed', armed ? 'true' : 'false');
      }
      // Inline, because setTool() writes surface.style.cursor inline and an
      // inline style beats any stylesheet rule.
      if (surface) surface.style.cursor = armed ? 'crosshair' : idleCursor;
      onChange(armed);
    }

    function setArmed(v) {
      v = !!v;
      if (v === armed) return;
      armed = v;
      apply();
      if (armed) onArm();
    }

    function toggle() { setArmed(!armed); }
    function disarm() { setArmed(false); }

    /* Call from the surface's own pointer handler when a tap lands on the
     * canvas while armed. Returns true if it consumed the event, so the
     * caller can `return` rather than also starting a stroke. */
    function handleTap(ev) {
      if (!armed) return false;
      try { onSample(ev); } catch (e) {}
      disarm();
      return true;
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && armed) { e.preventDefault(); disarm(); }
    });

    if (button) {
      button.addEventListener('click', function (e) {
        e.stopPropagation();
        toggle();
      });
    }

    apply();

    return {
      toggle: toggle,
      disarm: disarm,
      handleTap: handleTap,
      isArmed: function () { return armed; }
    };
  }

  window.SkriblEyedropper = { create: create };
}());
