// Editor-only: the tool shelf's "More" drawer and everything wired inside it.
//
// Carved out of app.js at the v277 review. The block is 4,928 B of source that
// the PLAYER downloaded, parsed and then did nothing with — every branch in it
// is guarded on an element or a lib that the player template does not have:
//
//   smoothSeg  + lib/smoothing.js      brushSeg   + lib/brush.js
//   eraserSeg  + lib/erasersize.js     pressureSeg + lib/pressure.js
//   eyedropperBtn + lib/eyedropper.js  clearDrawerBtn
//
// (The block also carried a dead #moreToggle handler, bound to an id no
// template has. Removed rather than moved — see the note at the top of the
// function.)
//
// The player loads NONE of those six libs (verified: 0 hits for each in
// skribl_player.html), so every `if (x && window.SkriblX)` was already false
// there and the recent-colours restore at the foot already no-opped —
// _initRecent() returns early without window.SkriblRecentColors. Moving it is
// therefore behaviour-preserving for the player by construction, not by an
// argument about reachability.
//
// WHY NOW. The v277 review's finding 5 said 600 B was not meaningful headroom
// "particularly while the audio-session behavior still needs lifecycle work",
// and finding 1 was that lifecycle work. Fixing finding 1 pushed the player's
// JS to 153,251 B against a 153,000 ratchet — the review's prediction, landing
// inside the same change that proved it. The reviewer also said not to solve it
// by raising the target, which is the right call: this file is the repayment.
//
// SAME RULE AS editor_music.js AND editor_photo.js: this moves only STATEMENTS.
// It declares nothing. It reads and assigns globals app.js declares
// (recentColors, _eyedropper, bgColor, recording, hasContent, clearBackup) and
// calls its functions (attachSegSlider, updateEraserCursor, showToast,
// setPenColor, stopPicking, getPos, padArtwork, makeHistoryState, clearCanvas,
// clearAutosave, updateClearUndoBtn, renderRecent). Top-level let/const live in
// the shared global lexical environment, so a later classic script reaches
// them — the same mechanism editor_shapes.js documents.
//
// LOAD ORDER: after app.js, and out of skribl_player.html.

(function initMoreTools() {
  // THE #moreToggle HANDLER THAT USED TO OPEN THIS BLOCK IS GONE. It bound a
  // click on an element that NO TEMPLATE HAS — grep the tree: `moreToggle`
  // appeared in app.js and nowhere else, so `if (moreToggle && moreDrawer)`
  // had been false on every load for as long as the id has been missing. The
  // drawer it claimed to open is shown by CSS.
  //
  // It survived because the isolation gate that would notice this counts ids
  // the EDITOR has and the PLAYER lacks; an id neither template has is
  // invisible to it. Found only because carving the block meant reading it.
  const opacitySlider = document.getElementById('opacitySlider');
  const opacityVal = document.getElementById('opacityVal');
  if (opacitySlider) {
    opacitySlider.addEventListener('input', () => {
      const v = parseInt(opacitySlider.value, 10);
      strokeOpacity = v / 100;
      if (opacityVal) opacityVal.textContent = v + '%';
      if (typeof updateSliderFill === 'function') updateSliderFill(opacitySlider);
    });
    if (typeof updateSliderFill === 'function') updateSliderFill(opacitySlider);
  }

  // Shared with Flip via lib/smoothing.js — the level-to-alpha mapping was
  // three magic numbers written out twice. Pill positioning stays here because
  // Pad and Flip do it differently; see the note in that file.
  const smoothSeg = document.getElementById('smoothSeg');
  if (smoothSeg && window.SkriblSmoothing) {
    window.SkriblSmoothing.create({
      seg: smoothSeg,
      onChange: a => { smoothingAlpha = a; },
    });
    attachSegSlider(smoothSeg);
  }

  // Eraser width — the shared multiplier (lib/erasersize.js). Repainting the
  // cursor on change matters: the ring is what the user aims with, so a size
  // that only took effect on the next stroke would be a cursor that lies.
  const eraserSeg = document.getElementById('eraserSeg');
  if (eraserSeg && window.SkriblEraser) {
    window.SkriblEraser.create({
      seg: eraserSeg,
      onChange: () => { if (typeof updateEraserCursor === 'function') updateEraserCursor(); },
    });
    attachSegSlider(eraserSeg);
  }

  const brushSeg = document.getElementById('brushSeg');
  if (brushSeg && window.SkriblBrush) {
    window.SkriblBrush.create({ seg: brushSeg });
    attachSegSlider(brushSeg);
  }

  const pressureSeg = document.getElementById('pressureSeg');
  if (pressureSeg && window.SkriblPressure) {
    window.SkriblPressure.create({ seg: pressureSeg });
    attachSegSlider(pressureSeg);
  }

  // Shared with Flip via lib/eyedropper.js. The native window.EyeDropper
  // branch that used to live here is GONE: it existed only on Chromium, so the
  // tap-to-sample path had to exist anyway, and keeping both shipped two
  // different experiences behind one button. See the note in that file.
  const eyedropperBtn = document.getElementById('eyedropperBtn');
  if (eyedropperBtn && window.SkriblEyedropper) {
    _eyedropper = window.SkriblEyedropper.create({
      button: eyedropperBtn,
      surface: canvas,
      idleCursor: '',
      onArm: () => showToast('Touch the canvas — drag to aim, release to pick', eyedropperBtn),
      // pickingColor is read by the pointer handler and by two teardown paths.
      onChange: v => { pickingColor = v; },
      // Loupe wiring: the lib magnifies and reads the SAME composited stage
      // sampleColorAt reads, so the ring shows what release will pick.
      getPoint: ev => getPos(ev),
      artwork: () => padArtwork(),
      dpr: () => window.devicePixelRatio || 1,
      bg: () => bgColor,
      // stopPicking, not just the lib's disarm: it also restores the
      // lock/eraser/normal cursor cue, same as the tap path.
      onPick: hex => { setPenColor(hex); stopPicking(); },
    });
  }

  const clearDrawerBtn = document.getElementById('clearDrawerBtn');
  if (clearDrawerBtn) {
    let armed = false, armTimer = null;
    const label = clearDrawerBtn.querySelector('span');
    const disarm = () => { armed = false; clearDrawerBtn.classList.remove('armed'); if (label) label.textContent = 'Clear drawing'; };
    clearDrawerBtn.addEventListener('click', () => {
      if (recording) { showToast('Stop recording before clearing', clearDrawerBtn); return; }
      if (!armed) {
        armed = true;
        clearDrawerBtn.classList.add('armed');
        if (label) label.textContent = 'Tap again to clear drawing';
        clearTimeout(armTimer);
        armTimer = setTimeout(disarm, 3000);
        return;
      }
      clearTimeout(armTimer);
      disarm();
      const _clearSnap = hasContent ? makeHistoryState() : null;
      clearCanvas();
      if (typeof clearAutosave === 'function') clearAutosave();
      clearBackup = _clearSnap; updateClearUndoBtn();
    });
  }

  // Restore recent colors from a previous session.
  try {
    const saved = JSON.parse(localStorage.getItem('skribl_recent_colors') || '[]');
    if (Array.isArray(saved)) {
      recentColors = saved.filter(c => /^#[0-9a-f]{6}$/.test(c)).slice(0, 6);
      renderRecent();
    }
  } catch (e) {}
})();
