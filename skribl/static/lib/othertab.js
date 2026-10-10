/* ANOTHER TAB SAVED OVER THIS ONE (v321 preflight, PF-008; the owner's call).
 *
 * Two tabs of one editor share one autosave slot, and the last to write wins,
 * silently, both ways: tab A draws, tab B draws, and a new tab restores B's
 * drawing while A is told nothing. Only the EMPTY-tab clobber was refused
 * before (review #20). This does not change who wins; it says so, in the tab
 * that just lost the slot, and offers to take it back.
 *
 * The browser fires `storage` in every OTHER tab of the origin when one writes
 * localStorage, never in the tab that wrote -- which is exactly "another tab".
 * A removal (posted, New Skribl) is not a takeover and says nothing, and a tab
 * with no work of its own has nothing to lose and says nothing.
 *
 *   SkriblOtherTab.watch(key, { hasWork: fn, keep: fn })
 */
(function (global) {
  'use strict';
  var doc = global.document;

  function watch(key, opts) {
    opts = opts || {};
    var bar = null;

    function hide() { if (bar) bar.hidden = true; }
    function build() {
      bar = doc.createElement('div');
      bar.className = 'othertab';
      bar.setAttribute('role', 'status');
      bar.setAttribute('aria-live', 'polite');
      var words = doc.createElement('span');
      words.className = 'othertab-words';
      words.textContent = 'Another tab saved a drawing over this one. The newest save is the one that opens next time.';
      var keep = doc.createElement('button');
      keep.type = 'button';
      keep.className = 'othertab-keep';
      keep.textContent = 'Keep this one';
      keep.addEventListener('click', function () {
        hide();
        if (typeof opts.keep === 'function') opts.keep();
      });
      var x = doc.createElement('button');
      x.type = 'button';
      x.className = 'othertab-x';
      x.setAttribute('aria-label', 'Dismiss');
      x.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
        + 'stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
      x.addEventListener('click', hide);
      bar.appendChild(words);
      bar.appendChild(keep);
      bar.appendChild(x);
      doc.body.appendChild(bar);
    }

    global.addEventListener('storage', function (e) {
      if (e.key !== key || e.newValue == null) return;
      try { if (e.storageArea && e.storageArea !== global.localStorage) return; } catch (_) { return; }
      if (typeof opts.hasWork === 'function' && !opts.hasWork()) return;
      if (!bar) build();
      bar.hidden = false;
    });
    return { hide: hide, isShown: function () { return !!bar && !bar.hidden; } };
  }

  global.SkriblOtherTab = { watch: watch };
})(window);
