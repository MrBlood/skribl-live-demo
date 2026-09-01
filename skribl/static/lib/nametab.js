/* The skribl NAME drawer — a title for the drawing, shared by Pad and Flip.
 *
 * WHY THIS IS A LIB. Both editors serialize a `.skribl` and both offered no
 * name for it: the Pad defaulted every draft to "Untitled Skribl" and Flip
 * named its download by the DATE, so two saves the same day collided as
 * "…date.skribl" and "…date (1).skribl". The two surfaces diverged on the same
 * missing feature — exactly the class of bug this project keeps paying for — so
 * the fix is one module both include, not two copies.
 *
 * WHERE NAMING LIVES. It opens from the ⋯ overflow menu ("Name this skribl"),
 * which drops the title strip down from the header (same grid-rows animation as
 * the Tune drawer). An earlier build hung a persistent name tab off the header's
 * lower edge; on the canvas it read as obtrusive, so naming moved into the menu
 * where the app's other document actions already live. The menu row's sub-label
 * echoes the current name so you can see it without opening the drawer.
 *
 * WHAT IT EXPOSES.
 *
 *   window.SkriblName.get()          -> the typed title, or an auto-filled
 *                                        default (name + creation time) when
 *                                        blank, so a save is never nameless.
 *   window.SkriblName.set(title)     -> push a loaded draft's title back in.
 *   window.SkriblName.filename(t)    -> a filesystem-safe "<slug>.skribl" for
 *                                        the download (no spaces/·/: to trip up
 *                                        Windows or a shell).
 *   window.SkriblName.open(opts?)    -> drop the title drawer. opts.onConfirm is
 *                                        run when the drawer's button/Enter is
 *                                        pressed (Save draft routes its save
 *                                        through here, so a draft is named as it
 *                                        is saved); opts.label sets that button's
 *                                        text ("Done" for a plain rename).
 *
 * The default is computed ONCE, so the name is stable while you edit. The menu
 * row is editor-only; the player template has no #nameItem, so init() no-ops.
 */
(function () {
  'use strict';

  // Computed FRESH at save time (get/filename), not cached: two blank saves a
  // minute apart then get distinct names. It is deliberately NOT shown in the
  // resting menu row — a live timestamp there renders differently between two
  // frames and makes any pixel comparison of the editor flaky (verify_cssplit).
  // The row shows a static "Untitled"; the auto-name surfaces as the placeholder.
  function computeDefault() {
    try {
      var d = new Date();
      var day = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      var tm = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
      return 'Skribl · ' + day + ' ' + tm;
    } catch (e) { return 'Untitled Skribl'; }
  }
  var sub = null;   // the menu row's sub-label (#nameItemSub)

  function inputEl() { return document.getElementById('skriblName'); }

  function syncLabel() {
    var el = inputEl();
    if (!el || !sub) return;
    var v = el.value.trim();
    // Static when blank — deterministic to render. The auto-name lives on save.
    sub.textContent = v || 'Untitled';
    sub.classList.toggle('empty', !v);
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
    },
    // opts = { onConfirm?, label? }. onConfirm runs when the drawer is confirmed
    // (Save draft passes its save here so the file is named as it is saved);
    // label sets the confirm button's text, defaulting to "Done" for a rename.
    open: function (opts) { API._open(opts || {}); }
  };

  // Close whichever overflow menu is open, so the drawer isn't hidden behind it.
  // Pad's menu is driven by editor_menu.js (global closeMenu); Flip's #moreMenu
  // is a plain hidden panel toggled by flip.js.
  function closeAnyMenu() {
    if (typeof window.closeMenu === 'function') { try { window.closeMenu(true); } catch (e) {} }
    var more = document.getElementById('moreMenu');
    if (more && !more.hidden) {
      more.hidden = true;
      var mb = document.getElementById('moreBtn');
      if (mb) mb.setAttribute('aria-expanded', 'false');
    }
  }

  function init() {
    var item = document.getElementById('nameItem');
    var shell = document.getElementById('nameShell');
    var el = inputEl();
    var done = document.getElementById('nameDone');
    sub = document.getElementById('nameItemSub');
    if (!item || !shell || !el) return;   // no naming on this surface (player)

    el.placeholder = computeDefault();
    var pending = null;   // a callback to run when the drawer is confirmed

    function setOpen(open) {
      shell.classList.toggle('open', open);
      shell.setAttribute('aria-hidden', String(!open));
      if (open) {
        // One drawer at a time: close Tune if it happens to be open.
        var ts = document.getElementById('tuneShell');
        if (ts && ts.classList.contains('open')) {
          ts.classList.remove('open'); ts.setAttribute('aria-hidden', 'true');
          var tb = document.getElementById('tuneBtn');
          if (tb) { tb.classList.remove('open'); tb.setAttribute('aria-expanded', 'false'); }
        }
        setTimeout(function () { el.focus(); el.select(); }, 160);
      }
    }
    API._setOpen = setOpen;

    // Open with an optional confirm callback + button label. Closes whatever
    // menu is open first, then drops the drawer.
    API._open = function (opts) {
      pending = typeof opts.onConfirm === 'function' ? opts.onConfirm : null;
      if (done) done.textContent = opts.label || 'Done';
      closeAnyMenu();
      setTimeout(function () { setOpen(true); }, 40);
    };

    // Confirm: run the pending action (e.g. the actual save), then close and
    // reset. get() already reflects the typed name, so the action sees it.
    function confirm() {
      var cb = pending;
      pending = null;
      if (done) done.textContent = 'Done';
      setOpen(false);
      if (cb) { try { cb(); } catch (e) {} }
    }
    // Cancel: close without running the pending action (Escape / click-away).
    function cancel() { pending = null; if (done) done.textContent = 'Done'; setOpen(false); }

    item.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();      // don't let the same click reach the outside-close
      API._open({});            // a plain rename: no callback, "Done" button
    });
    el.addEventListener('input', syncLabel);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); confirm(); }
      else if (e.key === 'Escape') { cancel(); }
    });
    if (done) done.addEventListener('click', confirm);
    document.addEventListener('click', function (e) {
      if (shell.classList.contains('open') && !shell.contains(e.target)) cancel();
    });
    syncLabel();
  }

  API._setOpen = function () {};   // no-op until init wires the real one
  API._open = function () {};
  window.SkriblName = API;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
