/* The page menu: the ••• on the gallery and the library, and what it opens.
 *
 * The markup is _skribl_page_menu.html; the button is each header's own
 * #pageMenuBtn. This file opens and closes the sheet and runs the theme
 * choice, and it owns nothing else: focus is lib/modalfocus.js's job and the
 * theme is lib/theme.js's, and both are used as they are rather than wrapped.
 *
 * WHY THE THEME IS HERE AT ALL. v313 made the library follow the stored
 * theme; before this, neither the library nor the gallery offered a way to
 * change it, so the only place to choose light was inside an editor. The
 * choice is the same key and the same three values the editors' menus write,
 * through the same module, so choosing it here is choosing it everywhere.
 *
 * WHAT THE SWITCH SHOWS is the stored CHOICE (system, dark or light), never
 * the effective mode: with System chosen on a light device the page is light
 * and the switch still says System, exactly as the editors' does.
 *
 * Escape and a tap on the scrim close it; a tap on the sheet does not.
 */
(function (global) {
  'use strict';

  function init() {
    var btn = document.getElementById('pageMenuBtn');
    var overlay = document.getElementById('pageMenuOverlay');
    var sheet = document.getElementById('pageMenu');
    if (!btn || !overlay || !sheet) return;
    var choices = [].slice.call(sheet.querySelectorAll('[data-theme]'));
    var Theme = global.SkriblTheme;
    var Modal = global.SkriblModal;

    function sync() {
      var mode = Theme ? Theme.mode() : 'system';
      choices.forEach(function (b) {
        b.setAttribute('aria-pressed', b.getAttribute('data-theme') === mode ? 'true' : 'false');
      });
    }
    function isOpen() { return !overlay.hidden; }
    function open() {
      sync();
      overlay.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      if (Modal) Modal.open(sheet, btn);
    }
    function close() {
      if (!isOpen()) return;
      overlay.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      if (Modal) Modal.close(sheet);
    }

    btn.addEventListener('click', function () { if (isOpen()) close(); else open(); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen()) { e.preventDefault(); close(); }
    });
    choices.forEach(function (b) {
      b.addEventListener('click', function () {
        if (Theme) Theme.set(b.getAttribute('data-theme'));
        sync();
      });
    });
    // Report a problem: collect with lib/report.js, copy with the one copy
    // implementation (lib/postedui.js), and say in the row which happened.
    var report = sheet.querySelector('[data-pm-report]');
    var reportSays = sheet.querySelector('[data-pm-report-status]');
    if (report && reportSays) {
      report.addEventListener('click', function () {
        var R = global.SkriblReport, P = global.SkriblPostedUI;
        if (!R || !P) { reportSays.textContent = "Couldn't collect the details on this page"; return; }
        P.copyText(R.collect()).then(function (ok) {
          reportSays.textContent = ok
            ? 'Copied — paste it into your message, with what went wrong'
            : "Couldn't copy — your browser blocked the clipboard";
        });
      });
    }
    // Another tab, or the device, changed it while the menu was open.
    if (Theme && Theme.onChange) Theme.onChange(sync);
    sync();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
