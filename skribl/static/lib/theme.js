/* Light/dark chrome — the stored setting, and the one place that applies it.
 *
 * WHAT IS THEMED. The CHROME only: header, toolbars, drawers, sheets, menus.
 * The canvas is not, ever. A drawing's ground is part of the drawing — it is
 * exported, it is posted, it is what other people see — so a UI preference
 * must not repaint it. That is why styles.css excludes #0d0f14 (the canvas
 * default) from the palette entirely, and why verify_surfaces' colour ratchet
 * excludes it too: it is the document's colour, not the app's.
 *
 * OPT-IN, NOT SYSTEM-FOLLOWING. There is deliberately no
 * `@media (prefers-color-scheme: light)` block in the stylesheet. Skribl is a
 * dark app by design — the whole palette, the brand marks, the accent purple
 * were all drawn against the dark ground — and honouring the OS would have
 * silently flipped every user on a light desktop to a theme nobody had chosen.
 * Light is a setting someone turns on.
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
  var DARK = 'dark', LIGHT = 'light';

  function read() {
    try { return global.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(v) {
    try { global.localStorage.setItem(KEY, v); return true; } catch (e) { return false; }
  }

  /* Anything unrecognised — a stale value, a hand-edited key, a future theme
   * this build does not have — resolves to dark rather than to nothing, so the
   * app is never left with an unstyled or half-styled frame. */
  function get() {
    return read() === LIGHT ? LIGHT : DARK;
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

  function set(mode) {
    var m = (mode === LIGHT) ? LIGHT : DARK;
    write(m);
    apply(m);
    for (var i = 0; i < listeners.length; i++) {
      try { listeners[i](m); } catch (e) { /* one bad listener is not a theme failure */ }
    }
    return m;
  }

  function onChange(fn) {
    if (typeof fn === 'function') listeners.push(fn);
  }

  /* Another tab changed it. The storage event does not fire in the tab that
   * wrote, so this cannot loop. */
  if (global.addEventListener) {
    global.addEventListener('storage', function (e) {
      if (!e || e.key !== KEY) return;
      var m = get();
      apply(m);
      for (var i = 0; i < listeners.length; i++) {
        try { listeners[i](m); } catch (err) { /* as above */ }
      }
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
    get: get,
    set: set,
    apply: apply,
    isLight: function () { return get() === LIGHT; },
    onChange: onChange
  };
})(window);
