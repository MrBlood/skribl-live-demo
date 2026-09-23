/* Full size on the devices that have a Fullscreen API, and on the one that does not.
 *
 * THE BUG THIS EXISTS FOR. Owner, twice, from an iPhone: "i am not seeing full
 * screen on gallery or library on iphone". Both surfaces were correct and both
 * were useless there. iOS Safari implements the Fullscreen API for `<video>`
 * and for nothing else, so `document.fullscreenEnabled` is false on the phone,
 * and both pages do the right thing with that answer -- they hide the control,
 * on the standing rule that a button which cannot work should not be on screen.
 * The result is that the one device where a drawing is smallest is the one
 * device with no way to make it bigger.
 *
 * THE FALLBACK IS A CSS STATE, NOT A POLYFILL. `.is-immersive-page` pins the
 * element over the viewport and locks the page behind it. That is not the same
 * thing as full screen -- the browser chrome stays, and it cannot be, because
 * no API can take it away -- but it is the whole of what the person wanted: the
 * drawing, as big as this screen goes.
 *
 * WHY NOT ALWAYS THE CSS STATE. Real full screen is better where it exists: no
 * URL bar, no notification shade, and the OS knows the app is presenting. The
 * API is tried first and the class is what happens when it is absent or the
 * request is refused (a rejected promise, which Safari also does when the
 * gesture is not trusted).
 *
 * WHAT IT DOES NOT DO. It does not touch the thing inside the element. Callers
 * get one `onChange(on)` and decide for themselves what going big means for
 * their own content -- the gallery plays the drawing and swaps the component
 * into `is-immersive`, the profile's stage does something else. Page says WHEN,
 * component says WHAT: the division verify_inline's gate exists to keep.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  var LOCK = 'skribl-immersive';
  var ON = 'is-immersive-page';

  function fsEl() {
    return doc.fullscreenElement || doc.webkitFullscreenElement || null;
  }

  /* Whether the REAL thing is available for this element. Both halves matter:
   * a browser can expose requestFullscreen on the element and still answer
   * false to fullscreenEnabled (an iframe without allow="fullscreen" is the
   * usual case), and taking either as sufficient calls a method that throws. */
  function apiFor(el) {
    var req = el.requestFullscreen || el.webkitRequestFullscreen;
    return (doc.fullscreenEnabled || doc.webkitFullscreenEnabled) && req ? req : null;
  }

  /* The scroll lock goes on <html> AND <body>. iOS Safari honours it on one or
   * the other depending on which is the scrolling element, and a page that
   * still scrolls behind a fixed overlay is how you end up looking at a
   * drawing with somebody else's post sliding past underneath it. */
  function lock(on) {
    var root = doc.documentElement;
    if (on) { root.classList.add(LOCK); } else { root.classList.remove(LOCK); }
  }

  function attach(el, opts) {
    opts = opts || {};
    var onChange = opts.onChange || function () {};
    var usingClass = false;

    function on() { return fsEl() === el || usingClass; }

    function report() { try { onChange(on()); } catch (e) {} }

    /* One handler for both spellings and both mechanisms, so a caller never
     * has to know which one got used. */
    function fsChanged() {
      if (usingClass) return;            // not ours to report
      report();
    }

    function openClass() {
      usingClass = true;
      el.classList.add(ON);
      lock(true);
      doc.addEventListener('keydown', esc, true);
      report();
    }

    function closeClass() {
      usingClass = false;
      el.classList.remove(ON);
      lock(false);
      doc.removeEventListener('keydown', esc, true);
      report();
    }

    /* Escape leaves, because the browser is not going to do it for us here.
     * With the real API this handler is not installed at all -- the browser
     * owns the key then, and two handlers would fight over one press. */
    function esc(e) {
      if (e.key === 'Escape' || e.keyCode === 27) { e.preventDefault(); closeClass(); }
    }

    function open() {
      var req = apiFor(el);
      if (!req) { openClass(); return; }
      var p;
      try { p = req.call(el); } catch (e) { openClass(); return; }
      /* A REFUSAL IS NOT AN ERROR TO SWALLOW, it is the fallback's cue. Safari
       * rejects when the gesture is not trusted; a rejected promise left alone
       * is a button that does nothing at all. */
      if (p && p.catch) p.catch(function () { openClass(); });
    }

    function close() {
      if (usingClass) { closeClass(); return; }
      if (fsEl()) {
        var ex = doc.exitFullscreen || doc.webkitExitFullscreen;
        if (ex) { try { ex.call(doc); } catch (e) {} }
      }
    }

    doc.addEventListener('fullscreenchange', fsChanged);
    doc.addEventListener('webkitfullscreenchange', fsChanged);

    return {
      toggle: function () { if (on()) close(); else open(); },
      close: close,
      isOn: on,
      /* True when going big means the REAL thing here. The pages use it for
       * wording, never for whether to show the control -- there is always a
       * way to go big now, which is the entire point of this module. */
      isNative: function () { return !!apiFor(el); }
    };
  }

  global.SkriblImmersive = { attach: attach };
})(window);
