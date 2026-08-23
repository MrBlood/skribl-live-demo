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
let menuCloseTimer = null;

function openMenu() {
  clearTimeout(menuCloseTimer);
  updateClearVisibility();
  // Re-read the stored state on every open. It is shared with Flip and can be
  // changed in another tab, and a switch showing the opposite of what is
  // stored is worse than no switch.
  if (window._skriblSyncHintToggle) window._skriblSyncHintToggle();
  menuOverlay.hidden = false;
  requestAnimationFrame(() => menuOverlay.classList.add('open'));
}

function closeMenu(instant) {
  menuOverlay.classList.remove('open');
  clearTimeout(menuCloseTimer);
  if (instant) {
    menuOverlay.hidden = true;   // dismiss with no slide (e.g. when opening another panel)
  } else {
    menuCloseTimer = setTimeout(() => { menuOverlay.hidden = true; }, 350);
  }
}

menuBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  if (menuOverlay.hidden) openMenu(); else closeMenu();
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
function resetAll() {
  clearCanvas();
  const mr = document.getElementById('musicRemove');
  if (mr && !mr.hidden) mr.click();
  const pr = document.getElementById('photoRemove');
  if (pr && !pr.hidden) pr.click();
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
  let snap = null;
  if (mediaBusy === 0) {
    try { snap = serializeSkribl(); } catch (err) { snap = null; }
  }
  resetAll();
  if (!snap) return;
  showToast('Cleared everything', null, {
    label: 'Undo',
    onClick: () => {
      try {
        loadSkribl(snap);
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
  const label = item.querySelector('span');
  const disarm = () => { armed = false; item.classList.remove('armed'); if (label) label.textContent = 'Clear all'; };
  item.addEventListener('click', () => {
    if (recording) { showToast('Stop recording before clearing', item); return; }
    if (!armed) {
      armed = true;
      item.classList.add('armed');
      if (label) label.textContent = 'Tap again to clear all';
      clearTimeout(armTimer);
      armTimer = setTimeout(disarm, 3000);
      return;   // keep the menu open for the confirm tap
    }
    clearTimeout(armTimer);
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
    // v107: Undo now offers Redo, and Redo re-offers Undo — so the clear becomes a
    // toggle you can flip either way, rather than the one-shot restore v106 had.
    // Redo simply re-runs this same function, which re-snapshots the restored
    // document; no second snapshot is stored and the two can never fall out of sync.
    clearAllWithUndo();
    closeMenu();
  });
})();

bindEl('saveDraftItem', 'click', () => {
  saveDraft();
  closeMenu();
});

bindEl('loadDraftItem', 'click', () => {
  document.getElementById('draftInput').click();
  closeMenu();
});

// Swipe-to-dismiss + tap-to-close on the mobile sheet handle
(function setupSheetGestures() {
  const sheet = document.getElementById('menuSheet');
  const handle = sheet ? sheet.querySelector('.menu-handle') : null;
  if (!sheet) return;

  let dragStartY = 0;
  let dragging = false;
  let currentY = 0;

  function onTouchStart(e) {
    // Only engage drag from the top region of the sheet (handle + header area)
    const touchY = SkriblEventPoint.at(e).clientY;
    const rect = sheet.getBoundingClientRect();
    if (touchY - rect.top > 60) return; // only near the top
    dragging = true;
    dragStartY = touchY;
    currentY = 0;
    sheet.style.transition = 'none';
  }

  function onTouchMove(e) {
    if (!dragging) return;
    currentY = Math.max(0, SkriblEventPoint.at(e).clientY - dragStartY);
    sheet.style.transform = `translateY(${currentY}px)`;
  }

  function onTouchEnd() {
    if (!dragging) return;
    dragging = false;
    sheet.style.transition = '';
    sheet.style.transform = '';
    if (currentY > 80) {
      closeMenu();
    }
  }

  // A CANCELLED swipe resets, it does not COMMIT. onTouchEnd closes the menu
  // when the drag passed 80px, so wiring touchcancel straight to it would let a
  // gesture the OS took away finish the dismissal the user never completed —
  // the opposite of what cancellation means. This resets the same state and
  // stops there.
  //
  // Without it the sheet kept `transition: none` and its translateY, and the
  // next touch carried on dragging a swipe that was already over: reproduced at
  // translateY(50px) -> translateY(90px) after the cancel.
  function onTouchCancel() {
    if (!dragging) return;
    dragging = false;
    currentY = 0;
    sheet.style.transition = '';
    sheet.style.transform = '';
  }

  sheet.addEventListener('touchstart', onTouchStart, { passive: true });
  sheet.addEventListener('touchmove', onTouchMove, { passive: true });
  sheet.addEventListener('touchend', onTouchEnd);
  sheet.addEventListener('touchcancel', onTouchCancel);

  // Tap the handle to close
  if (handle) {
    handle.addEventListener('click', (e) => {
      e.stopPropagation();
      closeMenu();
    });
  }
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
  const { width: cw, height: ch } = getCanvasLogicalSize();
  redoStack.push(makeHistoryState());
  redoBtn.disabled = false;
  const prev = undoStack.pop();
  // Synchronous restore from the snapshot canvas (see makeHistoryState).
  // save/restore + explicit source-over/alpha guards against a stale
  // 'destination-out' left on the ctx by a just-finished eraser stroke,
  // which would make this drawImage erase instead of paint.
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(prev.image, 0, 0, cw, ch);
  ctx.restore();
  strokes = prev.strokes.slice();
  strokeGroups = prev.strokeGroups.slice();
  syncStateAfterHistoryChange(prev.hasContent === undefined ? strokes.length > 0 : prev.hasContent);
  if (undoStack.length === 0) undoBtn.disabled = true;
});

redoBtn.addEventListener('click', () => {
  if (redoStack.length === 0) return;
  const { width: cw, height: ch } = getCanvasLogicalSize();
  undoStack.push(makeHistoryState());
  undoBtn.disabled = false;
  const next = redoStack.pop();
  // Synchronous restore from the snapshot canvas — same pattern as undo.
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, cw, ch);
  ctx.drawImage(next.image, 0, 0, cw, ch);
  ctx.restore();
  strokes = next.strokes.slice();
  strokeGroups = next.strokeGroups.slice();
  syncStateAfterHistoryChange(next.hasContent === undefined ? strokes.length > 0 : next.hasContent);
  if (redoStack.length === 0) redoBtn.disabled = true;
});

const helpBtn = document.getElementById('helpBtn');       // legacy header button (now null in editor)
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
  });
}

if (helpBtn) helpBtn.addEventListener('click', openHelpDrawer);
if (helpItem) helpItem.addEventListener('click', () => { closeMenu(true); openHelpDrawer(); });

function closeHelpDrawer() {
  clearTimeout(helpCloseTimer);
  // Drop focus off the trigger so its :focus-visible ring doesn't linger (Escape).
  if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
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
