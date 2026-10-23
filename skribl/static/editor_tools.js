// Editor-only: the tool shelf's "More" drawer and everything wired inside it.
//
// Carved out of app.js at the v277 review. The block is 4,928 B of source that
// the PLAYER downloaded, parsed and then did nothing with — every branch in it
// is guarded on an element or a lib that the player template does not have:
//
//   smoothSeg  + lib/smoothing.js      brushSeg   + lib/brushes.js
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
  // three magic numbers written out twice. These four are picture choices in
  // the draw drawer's tiles now (lib/drawtiles.js), not pill tracks: NOT handed
  // to attachSegSlider, whose pill, with no track to sit in, painted a column
  // of tint down the whole page under the chosen tile. lib/segslider.js still
  // writes their aria-pressed and gives each its one Tab stop (.dp-choices).
  // The drawer's four tiles (Brush, Size, Feel, Eraser), shared with Flip via
  // lib/drawtiles.js. Here, not in app.js: the player loads app.js and has no drawer.
  if (window.SkriblDrawTiles) window.SkriblDrawTiles.attach(document.getElementById('drawPanel'));
  const smoothSeg = document.getElementById('smoothSeg');
  if (smoothSeg && window.SkriblSmoothing) {
    window.SkriblSmoothing.create({
      seg: smoothSeg,
      onChange: a => { smoothingAlpha = a; },
    });
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
  }

  const brushSeg = document.getElementById('brushSeg');
  if (brushSeg && window.SkriblBrush) {
    window.SkriblBrush.create({ seg: brushSeg });
  }

  const pressureSeg = document.getElementById('pressureSeg');
  if (pressureSeg && window.SkriblPressure) {
    window.SkriblPressure.create({ seg: pressureSeg });
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
      // No toast: the lens lands on the drawing and the armed pill stays until
      // the pick ends (lib/eyedropper.js) — a 2.8s toast was the only cue.
      // pickingColor is read by the pointer handler and by two teardown paths.
      // While armed, the open colour drawer steps aside (lib/drawerdetent.js
      // veil) so the whole canvas is back on screen to pick from -- Flip's
      // popout does the same through the same helper.
      onChange: v => {
        pickingColor = v;
        const dp = document.getElementById('drawPanel');
        if (window.SkriblDrawerDetent && dp) window.SkriblDrawerDetent.veil(dp, v && !dp.hidden);
        // Every disarm (Cancel and Escape too, which bypass stopPicking) puts
        // the lock/eraser/normal cursor cue back rather than the lib's blank.
        if (!v) updateCanvasLockCue();
      },
      focusHome: () => document.getElementById('penToolBtn'),
      // Lens wiring: the lib magnifies and reads the SAME composited stage
      // sampleColorAt reads, so the ring shows what a pick will take.
      getPoint: ev => getPos(ev),
      artwork: () => padArtwork(),
      dpr: () => window.devicePixelRatio || 1,
      bg: () => bgColor,
      current: () => color,        // the lens ring's bottom half
      // stopPicking, not just the lib's disarm: it also restores the
      // lock/eraser/normal cursor cue, same as the tap path.
      // A pick closes the drawer, as Flip's does: the colour is chosen and the
      // canvas it came from is what the artist wants to see next.
      onPick: hex => { setPenColor(hex); stopPicking(); if (typeof openDrawer === 'function') openDrawer(null); },
    });
  }

  // RECOLOR (lib/recolor.js, shared with Flip): a line already drawn takes
  // the pen's colour. The lib owns the mode, the bar in the dock's row and
  // the colour running along the line; what a change does to the drawing is
  // the Pad's own, here.
  //
  //   ONE UNDO STEP A GESTURE, on the stack a stroke uses (begin). The
  //   recoloured points are REPLACED, never edited: a history state holds the
  //   point objects themselves (makeHistoryState slices the array), so an
  //   edit in place would edit the undo state too -- Select's lesson, written
  //   at SkriblSelectTool's first move in editor_draw.js.
  //
  //   THE MOMENT IS KEPT (recolors, app.js): which line, the colour it had and
  //   took, how many points the drawing had then, which gesture it was (`k`,
  //   counting from 0: the lines one drag crossed share it, and two taps with
  //   nothing drawn between them do not), the point the colour ran from and,
  //   while a take records, its clock. That is what lets a replay
  //   show the change when it was made rather than as if the line had always
  //   been that colour (the owner's pick, R2 of the mock). v219 took Select
  //   off the Pad because it moved recorded points and the replay drew them
  //   in their new place at their old time; this is the same kind of edit,
  //   with its time kept.
  //
  //   ALLOWED ON A FINISHED TAKE, as the eyedropper is: it adds no ink, so the
  //   drawing stays exactly its base and its recorded lines.
  const recolorBtn = document.getElementById('recolorBtn');
  if (recolorBtn && window.SkriblRecolor) {
    let gesture = -1;   // this gesture's `k`, set by begin()
    window.SkriblPadRecolor = window.SkriblRecolor.create({
      button: recolorBtn,
      dock: document.getElementById('toolBar'),
      surface: canvas,
      color: () => color,
      lines: () => ({ pts: strokes, groups: strokeGroups }),
      point: ev => getPos(ev),
      unit: () => canvas.width / (getCanvasLogicalSize().width || 1),
      art: () => padArtwork(),
      begin: () => {
        undoStack.push(makeHistoryState());
        if (undoStack.length > 30) undoStack.shift();
        undoBtn.disabled = false;
        redoStack = [];
        redoBtn.disabled = true;
        const last = recolors[recolors.length - 1];
        gesture = last && Number.isInteger(last.k) ? last.k + 1 : 0;
      },
      apply: (g0, g1, hex, at) => {
        let a = 0, changed = false;
        for (let g = 0; g < g0; g++) a += strokeGroups[g];
        for (let g = g0; g <= g1; g++) {
          const n = strokeGroups[g], was = strokes[a] ? strokes[a].color : null;
          let here = false;
          for (let i = a; i < a + n; i++) {
            const c = SkriblRecolor.tint(strokes[i].color, hex);
            if (c !== strokes[i].color) { strokes[i] = Object.assign({}, strokes[i], { color: c }); here = true; }
          }
          if (here) {
            const r = { g: g, n: strokes.length, k: gesture, at: Math.max(0, Math.min(n - 1, at - a)), was: was, to: strokes[a].color };
            if (recording) r.t = Date.now() - startTime;
            recolors.push(r);
            changed = true;
          }
          a += n;
        }
        return changed;
      },
      repaint: () => clearAndRestore(() => paintStrokesStatic(strokes)),
      end: () => { if (typeof scheduleAutosave === 'function') scheduleAutosave(); },
      undoButton: undoBtn,
      openColors: () => openDrawer('draw'),
      closeColors: () => openDrawer(null),
      colorsOpen: () => !!(_padDrawerCtl && _padDrawerCtl.isOpen('draw')),
      focusHome: () => document.getElementById('penToolBtn'),
      // On: the drawer goes (the drawing is what is wanted next), a colour
      // pick or a photo drag gives way, and the pen is the tool, since Done
      // goes back to it. Off: the lock, eraser or pen cursor comes back.
      onChange: on => {
        if (on) {
          if (pickingColor) stopPicking();
          if (typeof exitReposition === 'function') exitReposition();
          openDrawer(null);
          if (tool !== 'pen') setTool('pen');
        } else {
          updateCanvasLockCue();
        }
      },
    });
  }

  const clearDrawerBtn = document.getElementById('clearDrawerBtn');
  if (clearDrawerBtn) {
    let armed = false, armTimer = null;
    const label = clearDrawerBtn.querySelector('span');
    const disarm = () => { armed = false; clearDrawerBtn.classList.remove('armed'); if (label) label.textContent = 'Clear drawing'; };
    clearDrawerBtn.addEventListener('click', () => {
      if (recording) { showToast('Tap Done to finish this take first', clearDrawerBtn); return; }
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
      // The drawing goes and the photo and the music stay (clearCanvas keeps
      // media), so the autosave is rewritten, not dropped: dropping it took
      // their bytes with it (after v326, the Pad review).
      if (typeof scheduleAutosave === 'function') scheduleAutosave();
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
