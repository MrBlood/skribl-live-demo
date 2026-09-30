// Editor-only: the overflow menu, clear-all, sheet gestures, help drawer.
//
// Lifted VERBATIM out of app.js. The player has no menu button, no clear-all and
// no help drawer, but it was downloading this and RUNNING initClearAllMenu() and
// setupSheetGestures() on every shared link to attach handlers to elements it
// never paints.
//
// BOUNDARY. The obvious cut — the whole span from the "Overflow menu" comment to
// the next section — was WRONG: it swallowed initBrandFit(), whose inner fit()
// the player genuinely executes (the header brand collapses on the player too).
// Chrome's coverage profile reports function NAMES, so a nested fit() inside
// initBrandFit is indistinguishable from any other fit() until you look. The cut
// stops at 1784, before initBrandFit begins.
//
// The only name referenced from outside is closeMenu, and that call site already
// guards with `typeof closeMenu === 'function'` — so it is inert on the player
// rather than a thrown error.
//
// LOAD ORDER MATTERS: classic script, reads globals app.js declares. Keep it
// after app.js, and out of skribl_player.html.
// ---------- Overflow menu ----------
const menuBtn = document.getElementById('menuBtn');
const menuOverlay = document.getElementById('menuOverlay');
// The dialog node itself, at module scope. setupSheetGestures() below has
// its own local `sheet`; referencing that from openMenu/closeMenu would be
// a ReferenceError, so the focus calls need this binding.
const menuSheet = document.getElementById('menuSheet');
let menuCloseTimer = null;

function openMenu() {
  clearTimeout(menuCloseTimer);
  if (window.SkriblSheetSwipe) window.SkriblSheetSwipe.cancelSlide(menuSheet);   // reopened mid-close: from where it is
  updateClearVisibility();
  // Re-read the stored state on every open. It is shared with Flip and can be
  // changed in another tab, and a switch showing the opposite of what is
  // stored is worse than no switch.
  if (window._skriblSyncHintToggle) window._skriblSyncHintToggle();
  if (window._skriblSyncThemeToggle) window._skriblSyncThemeToggle();
  menuOverlay.hidden = false;
  if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');   // the popup contract (v292): the opener says so
  requestAnimationFrame(() => {
    menuOverlay.classList.add('open');
    // AFTER the unhide, or focus() lands on a hidden node and does nothing.
    // The sheet declares aria-modal="true" and until now did nothing about
    // focus at all — see lib/modalfocus.js.
    if (window.SkriblModal) window.SkriblModal.open(menuSheet, menuBtn);
  });
}

function closeMenu(instant) {
  menuOverlay.classList.remove('open');
  if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
  if (window._skriblDisarmClearAll) window._skriblDisarmClearAll();   // a closed menu holds no armed confirmation
  clearTimeout(menuCloseTimer);
  // Return focus to whatever opened it. Before this, closing left focus
  // wherever it had been when the sheet appeared — usually nowhere.
  if (window.SkriblModal) window.SkriblModal.close(menuSheet);
  if (instant) {
    menuOverlay.hidden = true;   // dismiss with no slide (e.g. when opening another panel)
  } else {
    menuCloseTimer = setTimeout(() => { menuOverlay.hidden = true; }, 350);
  }
}

menuBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  // A menu easing away is closed, so a second tap brings it back (as Flip's
  // and the page menus do, v317). The overlay stays unhidden for the slide.
  if (!menuOverlay.classList.contains('open')) openMenu(); else closeMenu();
});

menuOverlay.addEventListener('click', (e) => {
  // Close if the tap is not inside the sheet itself
  if (!e.target.closest('.menu-sheet')) closeMenu();
});

// Full reset for the overflow menu's "Clear all": the drawing AND the music,
// photo, and background all back to a fresh start. Reuses each item's existing
// removal (via its own control) so behavior can't drift from the single-item
// remove buttons. clearCanvas() intentionally keeps media, so we clear those
// explicitly here, then return the background to the default swatch.
// The drawers' bins ask before they remove (lib/pendingcards.js): a plain
// click() would only arm them. "New Skribl" has already asked, on its own
// two-tap arm, so it goes through removeNow -- the same control and every
// listener on it, past the question.
function resetAll() {
  clearCanvas();
  const _rm = (kind) => {
    const b = document.getElementById(kind + 'Remove');
    if (!b || b.hidden) return;
    if (window.SkriblPendingCards && window.SkriblPendingCards.removeNow) window.SkriblPendingCards.removeNow(kind);
    else b.click();
  };
  _rm('music');
  _rm('photo');
  bgColor = '#0d0f14';
  document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b.dataset.bg === '#0d0f14'));
  canvasWrap.style.backgroundColor = bgColor;
  if (typeof updateVignette === 'function') updateVignette();
  if (typeof clearAutosave === 'function') clearAutosave();
}

// Clear everything, then offer a one-tap way back. Snapshotting goes through the
// SAME serialize/apply pair the draft and autosave paths use (serializeSkribl /
// loadSkribl), so media returns too and there is no parallel restore logic.
// Skipped while mediaBusy > 0 — the same guard saveDraft() uses — because the
// snapshot would capture a half-loaded photo or track. The clear still happens in
// that case, just without the undo offer.
function clearAllWithUndo() {
  // A new Skribl is a new draft: the next Save must not overwrite the old one.
  const prevDraft = window.SkriblSavedDrafts ? window.SkriblSavedDrafts.forget() : null;
  let snap = null;
  if (mediaBusy === 0) {
    try { snap = serializeSkribl(); } catch (err) { snap = null; }
  }
  resetAll();
  const prevName = window.SkriblName && window.SkriblName.reset ? window.SkriblName.reset() : null;
  if (!snap) return;
  showToast('New Skribl', null, {
    label: 'Undo',
    onClick: () => {
      try {
        loadSkribl(snap);
        if (window.SkriblName) window.SkriblName.restore(prevName);   // its names come back with it
        if (window.SkriblSavedDrafts) window.SkriblSavedDrafts.resume(prevDraft);   // and its saved draft
        showToast('Restored', null, { label: 'Redo', onClick: clearAllWithUndo });
      } catch (err) {
        showToast('Couldn\u2019t restore that', null);
      }
    }
  });
}

// "Clear all" wipes music/photo too, so it's the most destructive action —
// guarded with the same two-tap arm as the drawer's Clear drawing. The first tap
// arms (menu stays open for the confirm); the second clears everything.
(function initClearAllMenu() {
  const item = document.getElementById('clearMenuItem');
  if (!item) return;
  let armed = false, armTimer = null;
  const label = item.querySelector('.new-label');
  const disarm = () => { clearTimeout(armTimer); armed = false; item.classList.remove('armed'); if (label) label.textContent = 'New Skribl'; };
  // THE ARM HOLDS UNTIL THE PERSON LEAVES IT, not for three seconds (v292;
  // outside review of v291, SK-AUD-018): it disarms when the menu closes, when
  // focus leaves the item, and on a long safety net. A destructive action
  // should not be a race against a timer — a slow second tap met a disarmed
  // button and armed it again. And the armed label is SPOKEN, through the live
  // region the template carries for it, not only shown.
  const announce = (text) => { const st = document.getElementById('confirmStatus'); if (st) { st.textContent = ''; st.textContent = text; } };
  window._skriblDisarmClearAll = disarm;
  item.addEventListener('focusout', () => { if (armed) disarm(); });
  item.addEventListener('click', () => {
    if (recording) { showToast('Stop recording before starting a new one', item); return; }
    if (!armed) {
      armed = true;
      item.classList.add('armed');
      if (label) label.textContent = 'Tap again to start over';
      announce('Tap again to start over');
      clearTimeout(armTimer);
      armTimer = setTimeout(disarm, 20000);
      return;   // keep the menu open for the confirm tap
    }
    disarm();
    // "Clear all" wipes strokes, music, photo AND the background — then calls
    // clearAutosave(), so even the recovery copy is gone. The two-tap arm above
    // guards against the accidental tap, but nothing could undo a deliberate one.
    // Snapshot the whole document first, through the SAME serialize the draft and
    // autosave paths use, and offer a one-tap restore via loadSkribl(). Reusing
    // that pair means media comes back too, with no parallel restore logic.
    // Skipped while media is still being prepared (mediaBusy), because the
    // snapshot would capture a half-loaded photo or track — same guard saveDraft
    // uses. In that case the clear still happens, just without the undo offer.
    // Undo now offers Redo, and Redo re-offers Undo — so the clear becomes a
    // toggle you can flip either way, rather than the one-shot restore v106 had.
    // Redo simply re-runs this same function, which re-snapshots the restored
    // document; no second snapshot is stored and the two can never fall out of sync.
    clearAllWithUndo();
    closeMenu();
  });
})();

bindEl('saveDraftItem', 'click', () => {
  closeMenu();
  // Name it as part of saving: the drawer opens with the current/auto name and
  // its button reads "Save a backup" — confirming runs the actual download.
  if (window.SkriblName && window.SkriblName.open) {
    window.SkriblName.open({ label: 'Save a backup', onConfirm: saveDraft });
  } else {
    saveDraft();
  }
});

bindEl('loadDraftItem', 'click', () => {
  document.getElementById('draftInput').click();
  closeMenu();
});

// Swipe down or tap the grabber to close: lib/sheetswipe.js, the same gesture
// every bottom sheet has (v317). This sheet had its own, passive, so the page
// scrolled -- and at its top, reloaded -- under the finger doing the swipe.
(function setupSheetGestures() {
  const sheet = document.getElementById('menuSheet');
  if (!sheet || !window.SkriblSheetSwipe) return;
  window.SkriblSheetSwipe.attach(sheet, { handle: sheet.querySelector('.menu-handle'), close: closeMenu });
})();

// Close menu on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !menuOverlay.hidden) closeMenu();
  if (e.key === 'Escape' && helpDrawer && !helpDrawer.hidden) closeHelpDrawer();

  // Undo / redo shortcuts (desktop). Ignore while typing in a field.
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '') ||
                 (e.target && e.target.isContentEditable);
  if (!typing && (e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    if (e.shiftKey) { if (!redoBtn.disabled) redoBtn.click(); }
    else { if (!undoBtn.disabled) undoBtn.click(); }
  } else if (!typing && (e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
    e.preventDefault();
    if (!redoBtn.disabled) redoBtn.click();
  }
});

undoBtn.addEventListener('click', () => {
  if (undoStack.length === 0) return;
  if (pickingColor) stopPicking();   // the drawing under the lens is about to change
  redoStack.push(makeHistoryState());
  redoBtn.disabled = false;
  const prev = undoStack.pop();
  // Pixel states restore their snapshot; ordinary states repaint base +
  // strokes — see restoreHistoryState (app.js) for why both are exact.
  restoreHistoryState(prev);
  strokes = prev.strokes.slice();
  strokeGroups = prev.strokeGroups.slice();
  syncStateAfterHistoryChange(prev.hasContent === undefined ? strokes.length > 0 : prev.hasContent);
  if (undoStack.length === 0) undoBtn.disabled = true;
});

redoBtn.addEventListener('click', () => {
  if (redoStack.length === 0) return;
  if (pickingColor) stopPicking();   // the drawing under the lens is about to change
  undoStack.push(makeHistoryState());
  undoBtn.disabled = false;
  const next = redoStack.pop();
  // Same restore as undo — pixel state or base + strokes repaint.
  restoreHistoryState(next);
  strokes = next.strokes.slice();
  strokeGroups = next.strokeGroups.slice();
  syncStateAfterHistoryChange(next.hasContent === undefined ? strokes.length > 0 : next.hasContent);
  if (redoStack.length === 0) redoBtn.disabled = true;
});

const helpItem = document.getElementById('helpItem');     // "How it works" — moved into the ⋯ menu
const helpDrawer = document.getElementById('helpDrawer');
const helpClose = document.getElementById('helpClose');
const helpBackdrop = document.getElementById('helpBackdrop');

let helpCloseTimer = null;

function openHelpDrawer() {
  clearTimeout(helpCloseTimer);
  document.documentElement.classList.add('help-open');   // lock page scroll (one scrollbar)
  helpDrawer.hidden = false;
  helpDrawer.classList.remove('closing');
  requestAnimationFrame(() => {
    helpDrawer.classList.add('open');
    // aria-modal="true" is declared on this node; this is the half that makes
    // it true. See lib/modalfocus.js.
    if (window.SkriblModal) window.SkriblModal.open(helpDrawer);
  });
}

if (helpItem) helpItem.addEventListener('click', () => { closeMenu(true); openHelpDrawer(); });

function closeHelpDrawer() {
  clearTimeout(helpCloseTimer);
  // WAS blur(). That does drop the lingering :focus-visible ring, and it also
  // drops focus on <body> — the user's place in the page is gone and the next
  // Tab starts from the top. Returning focus to the opener achieves the ring's
  // purpose (it moves off whatever had it) without the cost.
  if (window.SkriblModal) window.SkriblModal.close(helpDrawer);
  helpDrawer.classList.add('closing');
  helpDrawer.classList.remove('open');
  helpCloseTimer = setTimeout(() => {
    helpDrawer.hidden = true;
    helpDrawer.classList.remove('closing');
    document.documentElement.classList.remove('help-open');   // restore page scroll after it's gone
  }, 250);
}

helpClose.addEventListener('click', closeHelpDrawer);
helpBackdrop.addEventListener('click', closeHelpDrawer);

// Show the "Skribl Pad" wordmark whenever the header has room for it, and drop
// to logo-only when it doesn't (after a take, while recording, on tiny screens)
// — measured, not a fixed breakpoint, so it adapts to every state and width.


// Saved drafts (v316): ⋯ "Save draft" / "Open a draft…". lib/savedrafts.js owns
// the list and the storage; the Pad hands it its own serialise and load, the
// same pair a .skribl backup uses. A Flip draft opens in Flip, through the
// Flip Mode row's own link (so a composer session stays one).
document.addEventListener('DOMContentLoaded', function () {
  if (!window.SkriblSavedDrafts) return;
  window.SkriblSavedDrafts.init({
    kind: 'pad',
    serialize: function () { return serializeSkribl(); },
    load: function (d) { loadSkribl(d); },
    // A photo or a track on its own is work too: replacing it asks first, and
    // it can be saved (v317 review).
    // ...and so is media still on its way: a pending record, a restore still
    // reading the store, a photo still decoding. Counting only what had landed
    // let a draft opened from the Library replace the autosaved photo mid-
    // restore without asking (v317 review).
    hasContent: function () {
      return !!(hasContent || (typeof strokes !== 'undefined' && strokes.length)
                || (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
                || (audioEl && audioEl._fileName)
                || (typeof _mediaPresent === 'function' && _mediaPresent())
                || (typeof _inFlight !== 'undefined' && _inFlight.photo)
                || (typeof _restoring !== 'undefined' && (_restoring.photo || _restoring.music)));
    },
    // A photo or track still being read: its name is already the new file's
    // and its bytes are still the old one's (third review).
    busy: function () {
      return !!((typeof mediaBusy !== 'undefined' && mediaBusy > 0)
                || (typeof _inFlight !== 'undefined' && _inFlight.photo)
                || (typeof _restoring !== 'undefined' && (_restoring.photo || _restoring.music)));
    },
    thumbnail: function () { return window.skriblPreviewCanvas ? window.skriblPreviewCanvas() : document.getElementById('canvas'); },
    otherUrl: function () { var a = document.getElementById('flipBtn'); return a ? a.getAttribute('href') : null; },
    closeMenu: function () { if (typeof closeMenu === 'function') closeMenu(true); },
    toast: function (m) { showToast(m, document.getElementById('menuBtn')); }
  });
});
