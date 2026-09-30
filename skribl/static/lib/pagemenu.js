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
 *
 * WHERE IT OPENS. On a phone it is a bottom sheet; from 641px up it is a
 * popover under the ••• (pagemenu.css), and the header it hangs from is
 * sticky, so its place is read off the button each time it opens -- 8px below
 * it, right edges flush -- and again if the window changes size while open.
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
    // Easing away counts as closed, so a quick second tap reopens it.
    function isOpen() { return !overlay.hidden && !sheet._slideT; }
    function place() {
      var r = btn.getBoundingClientRect();
      overlay.style.setProperty('--pm-top', Math.round(r.bottom + 8) + 'px');
      overlay.style.setProperty('--pm-right', Math.max(0, document.documentElement.clientWidth - r.right) + 'px');
    }
    function open() {
      sync();
      if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.cancelSlide(sheet);
      overlay.classList.remove('closing');
      place();
      overlay.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      if (Modal) Modal.open(sheet, btn);
    }
    function close() {
      if (!isOpen()) return;
      btn.setAttribute('aria-expanded', 'false');
      if (Modal) Modal.close(sheet);
      // Eases down with its dim, then hides (lib/sheetswipe.js).
      // The dim is the overlay's ::before, so it fades by class, not by fadeBg.
      var gone = function () { overlay.hidden = true; overlay.classList.remove('closing'); };
      overlay.classList.add('closing');
      if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.slideOut(sheet, { done: gone });
      else gone();
    }

    btn.addEventListener('click', function () { if (isOpen()) close(); else open(); });
    global.addEventListener('resize', function () { if (!overlay.hidden) place(); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    // The grabber closes on a tap, and the sheet swipes down (lib/sheetswipe.js).
    // It used to be a picture of a handle that did nothing.
    if (global.SkriblSheetSwipe) global.SkriblSheetSwipe.attach(sheet, { handle: sheet.querySelector('.pm-grab'), close: close });
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
