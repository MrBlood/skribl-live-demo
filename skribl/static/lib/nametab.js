/* The skribl NAME TAB — a title for the drawing, shared by Pad and Flip.
 *
 * WHY THIS IS A LIB. Both editors serialize a `.skribl` and both offered no
 * name for it: the Pad defaulted every draft to "Untitled Skribl" and Flip
 * named its download by the DATE, so two saves the same day collided as
 * "…date.skribl" and "…date (1).skribl". The two surfaces diverged on the same
 * missing feature — exactly the class of bug this project keeps paying for — so
 * the fix is one module both include, not two copies.
 *
 * WHAT IT DOES. Wires the header's name tab + drop-down title strip (the markup
 * lives in each editor template; the CSS in styles.css), and exposes:
 *
 *   window.SkriblName.get()          -> the typed title, or an auto-filled
 *                                        default (name + creation time) when
 *                                        blank, so a save is never nameless.
 *   window.SkriblName.set(title)     -> push a loaded draft's title back in.
 *   window.SkriblName.filename(t)    -> a filesystem-safe "<slug>.skribl" for
 *                                        the download (no spaces/·/: to trip up
 *                                        Windows or a shell).
 *
 * The default is computed ONCE, so the name is stable while you edit. The tab
 * is editor-only; the player template has no #nameTab, so init() no-ops there.
 */
(function () {
  'use strict';

  // Computed FRESH at save time (get/filename), not cached: two blank saves a
  // minute apart then get distinct names. It is deliberately NOT shown in the
  // resting tab — a live timestamp there renders differently between two frames
  // and makes any pixel comparison of the editor flaky (verify_cssplit). The tab
  // shows a static "Untitled"; the auto-name surfaces as the input's placeholder.
  function computeDefault() {
    try {
      var d = new Date();
      var day = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      var tm = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
      return 'Skribl · ' + day + ' ' + tm;
    } catch (e) { return 'Untitled Skribl'; }
  }
  var lbl = null;

  function inputEl() { return document.getElementById('skriblName'); }

  function syncLabel() {
    var el = inputEl();
    if (!el || !lbl) return;
    var v = el.value.trim();
    // Static when blank — deterministic to render. The auto-name lives on save.
    lbl.textContent = v || 'Untitled';
    lbl.classList.toggle('empty', !v);
  }

  var API = {
    get: function () {
      var el = inputEl();
      var v = el && el.value ? el.value.trim() : '';
      return v || computeDefault();
    },
    set: function (t) {
      var el = inputEl();
      if (el && typeof t === 'string') { el.value = t; syncLabel(); }
    },
    filename: function (t) {
      var base = String(t || API.get()).toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')   // spaces, ·, :, everything non-alnum -> -
        .replace(/^-+|-+$/g, '')       // trim leading/trailing -
        .slice(0, 60);
      return (base || 'skribl') + '.skribl';
    }
  };

  function init() {
    var tab = document.getElementById('nameTab');
    var shell = document.getElementById('nameShell');
    var el = inputEl();
    var done = document.getElementById('nameDone');
    lbl = document.getElementById('nameLbl');
    if (!tab || !shell || !el || !lbl) return;   // no tab on this surface (player)

    el.placeholder = computeDefault();

    function setOpen(open) {
      shell.classList.toggle('open', open);
      shell.setAttribute('aria-hidden', String(!open));
      tab.classList.toggle('open', open);
      tab.setAttribute('aria-expanded', String(open));
      if (open) {
        // One drawer at a time: close Tune if it happens to be open.
        var ts = document.getElementById('tuneShell');
        if (ts && ts.classList.contains('open')) {
          ts.classList.remove('open'); ts.setAttribute('aria-hidden', 'true');
          var tb = document.getElementById('tuneBtn');
          if (tb) { tb.classList.remove('open'); tb.setAttribute('aria-expanded', 'false'); }
        }
        setTimeout(function () { el.focus(); el.select(); }, 120);
      }
    }

    tab.addEventListener('click', function () { setOpen(!shell.classList.contains('open')); });
    el.addEventListener('input', syncLabel);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); setOpen(false); }
      else if (e.key === 'Escape') { setOpen(false); tab.focus(); }
    });
    if (done) done.addEventListener('click', function () { setOpen(false); });
    document.addEventListener('click', function (e) {
      if (shell.classList.contains('open') && !shell.contains(e.target) && !tab.contains(e.target)) setOpen(false);
    });
    syncLabel();
  }

  window.SkriblName = API;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
