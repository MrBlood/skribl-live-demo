/* Light/dark chrome — the stored setting, and the one place that applies it.
 *
 * WHAT IS THEMED. The CHROME only: header, toolbars, drawers, sheets, menus.
 * The canvas is not, ever. A drawing's ground is part of the drawing — it is
 * exported, it is posted, it is what other people see — so a UI preference
 * must not repaint it. That is why styles.css excludes #0d0f14 (the canvas
 * default) from the palette entirely, and why verify_surfaces' colour ratchet
 * excludes it too: it is the document's colour, not the app's.
 *
 * THREE CHOICES, ONE EFFECTIVE MODE (v292; outside review of v291,
 * SK-AUD-014, reversing v232). The stored CHOICE is system, dark or light,
 * and nothing stored means system. The EFFECTIVE mode is dark or light: a
 * choice of system resolves through `prefers-color-scheme`, and the two
 * explicit choices ignore it. v232 made light opt-in and dark the default
 * for everyone, because the palette was drawn dark and a media rule would
 * have flipped every light-desktop user overnight; the owner reversed that
 * on the review's platform-fit point — people expect an app to follow the
 * appearance they set — and the explicit choices are what keep the dark
 * identity available to anyone who wants it whatever their OS says.
 *
 * STILL NO `@media (prefers-color-scheme)` BLOCK IN THE STYLESHEET, and that
 * is the same decision for a different reason: the light ramp is one block
 * keyed on data-theme="light", and a media rule would be a second copy of it
 * to drift. The resolution happens HERE and in the inline boot, which stamp
 * the attribute; the CSS has one ramp and one switch.
 *
 * WHY THE FLASH MATTERS. The setting lives in localStorage, which no CSS can
 * read, so the attribute has to be stamped on <html> before first paint or a
 * light-mode user gets a dark frame for one frame on every navigation. That is
 * what _skribl_theme_boot.html does inline in <head>; this file is the same
 * logic for everything that runs afterwards. Keep the two in agreement — the
 * KEY and the values are the contract between them.
 *
 * FAILS QUIET. localStorage throws on ACCESS in Safari's private mode, not
 * merely on write. Every read and write here is wrapped, and the fallback is
 * dark, which is the app as it has always looked.
 */
(function (global) {
  'use strict';

  var KEY = 'skribl_theme_v1';
  var DARK = 'dark', LIGHT = 'light', SYSTEM = 'system';

  function read() {
    try { return global.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(v) {
    try { global.localStorage.setItem(KEY, v); return true; } catch (e) { return false; }
  }

  /* The CHOICE: what is stored, with anything unrecognised — a stale value, a
   * hand-edited key, a future theme this build does not have — reading as
   * system, so the app is never left with an unstyled or half-styled frame. */
  function mode() {
    var v = read();
    return v === LIGHT || v === DARK ? v : SYSTEM;
  }
  function osLight() {
    try { return !!(global.matchMedia && global.matchMedia('(prefers-color-scheme: light)').matches); }
    catch (e) { return false; }
  }
  /* The EFFECTIVE mode: what the chrome wears right now. */
  function get() {
    var m = mode();
    if (m === SYSTEM) return osLight() ? LIGHT : DARK;
    return m;
  }

  function apply(mode) {
    var root = global.document && global.document.documentElement;
    if (!root) return mode;
    if (mode === LIGHT) root.setAttribute('data-theme', LIGHT);
    else root.removeAttribute('data-theme');
    return mode;
  }

  /* The listener list is what keeps two controls on the same page honest: Pad
   * and Flip each show one switch, but a theme can also be set from another
   * tab, and a switch reading the opposite of what is stored is worse than no
   * switch at all. */
  var listeners = [];

  function notify() {
    var m = get();
    for (var i = 0; i < listeners.length; i++) {
      try { listeners[i](m); } catch (e) { /* one bad listener is not a theme failure */ }
    }
  }
  function set(choice) {
    var c = (choice === LIGHT || choice === DARK) ? choice : SYSTEM;
    write(c);
    apply(get());
    notify();
    return c;
  }

  /* The OS changed its mind while a system-following page was open: follow
   * it. An explicit choice ignores this by construction (get() never reads
   * the OS for one). */
  try {
    var mq = global.matchMedia && global.matchMedia('(prefers-color-scheme: light)');
    if (mq && mq.addEventListener) mq.addEventListener('change', function () { if (mode() === SYSTEM) { apply(get()); notify(); } });
  } catch (e) { /* no matchMedia: system reads as dark, which is what it always was */ }

  function onChange(fn) {
    if (typeof fn === 'function') listeners.push(fn);
  }

  /* Another tab changed it. The storage event does not fire in the tab that
   * wrote, so this cannot loop. */
  if (global.addEventListener) {
    global.addEventListener('storage', function (e) {
      if (!e || e.key !== KEY) return;
      apply(get());
      notify();
    });
  }

  /* Idempotent with the inline boot script: both stamp the same attribute from
   * the same key, so running this after it changes nothing. It is here so the
   * theme is still correct on a page that forgot the boot script. */
  apply(get());

  global.SkriblTheme = {
    KEY: KEY,
    DARK: DARK,
    LIGHT: LIGHT,
    SYSTEM: SYSTEM,
    get: get,       // effective: dark | light
    mode: mode,     // the choice: system | dark | light
    set: set,
    apply: apply,
    isLight: function () { return get() === LIGHT; },
    onChange: onChange
  };
})(window);
