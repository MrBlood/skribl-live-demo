// Editor-only: draft durability — autosave, restore, media persistence, the
// leave guard, and the flush-on-navigation contract.
//
// Carved from app.js (the fifth carve, after editor_music/photo/shapes/draw):
// the player replays finished drawings and never autosaves, yet it carried all
// of this in its byte budget. Every caller outside this file was ALREADY
// typeof-guarded, which is what made the carve mechanical.
//
// WHAT THIS FILE ADDS beyond the moved code (external review P0-2/#19/#3):
//   draftRev / durableRev   every edit bumps draftRev; a successful write
//                           records durableRev. "Is this work safe" is now a
//                           comparison, never an inference from content type.
//   flushPadDraft()         synchronous write-now, called before intentional
//                           navigation and on pagehide/visibilitychange —
//                           the debounce window is no longer a loss window.
//   SkriblDraftStore        media BYTES go to IndexedDB (lib/draftstore.js)
//                           at attach time, so "Saved without media" becomes
//                           a failure signal instead of a designed limitation
//                           — and it no longer fades: a durability problem is
//                           a state, not a toast.
//   the leave guard         fires on !durable rather than on media presence.
//                           With working storage it never fires, which is the
//                           direction doc's intended end state; with broken
//                           storage it fires for exactly the work at risk.
//
// LOAD ORDER: classic script reading app.js globals (canvas, strokes, hasContent,
// photoBgImg, audioEl, pendingPhotoMeta, ...). After app.js and after
// editor_music.js/editor_photo.js, whose change handlers the media re-add path
// drives through real DataTransfer events.

// ---------- Autosave / crash recovery ----------
// Saves the DRAWING (strokes, snapshot, background) plus media *metadata*
// (filenames + settings) to localStorage — never the photo/music bytes, which
// are far too large. On reload we can restore the drawing exactly and tell the
// user which files to re-add, with their settings already in place.
const AUTOSAVE_KEY = 'skribl_autosave_v1';

// ---- The durability model (external review P0-2 / #19) ----------------------
// Every mutating edit bumps draftRev (in scheduleAutosave — the same triggers
// that always meant "something changed"). A write that SUCCEEDS records the
// revision it serialized as durableRev. "Is this work safe to walk away from"
// is then draftRev === durableRev && media durable — a comparison against what
// actually happened, never an inference from what kind of content is attached.
// The old guard asked "is media present"; localStorage disabled, full, or in a
// private mode made that answer wrong in exactly the case that mattered.
let draftRev = 0;
let durableRev = 0;
// Per-slot media durability: 'none' (nothing attached), 'saving' (IndexedDB
// write in flight), 'durable' (bytes confirmed stored), 'failed' (store
// rejected — private mode, quota, no IndexedDB). 'failed' keeps the amber
// pill up PERSISTENTLY and arms the leave guard.
const mediaDraft = { photo: 'none', music: 'none' };
// One id per page load, stamped into every record this tab writes. Autosave is
// a single slot per mode (review #20); full multi-draft arbitration needs a
// project model this tree does not have, but the cheapest and worst clobber —
// a tab with an EMPTY canvas silently deleting a draft another tab wrote after
// this one loaded — costs one comparison to refuse, so it is refused below.
const WRITER_ID = Math.random().toString(36).slice(2) + Date.now().toString(36);
const PAGE_LOADED_AT = new Date().toISOString();
// True once THIS session has written a non-empty save — i.e. the draft slot
// holds this session's work, so a later empty state is a deliberate clear.
// A session that never owned the slot must not clear it: a fresh tab flushes
// on visibilitychange (tab switch) while its canvas is still empty, and
// without this gate that flush deleted whatever draft was already in storage
// — with the restore banner still on screen offering it. Found by the v222
// release aggregate: verify_strokegroups plants a draft and reloads, and the
// flush ate the plant the same way it would eat a user's draft.
let sessionOwnedDraft = false;
function mediaDurabilityOk() {
  return mediaDraft.photo !== 'failed' && mediaDraft.music !== 'failed' &&
         mediaDraft.photo !== 'saving' && mediaDraft.music !== 'saving';
}
function draftIsDurable() { return durableRev === draftRev && mediaDurabilityOk(); }
let autosaveTimer = null;

function serializeAutosave() {
  let baseSnapshot = null;
  try {
    if (hasContent && strokes.length === 0) {
      baseSnapshot = canvas.toDataURL();
    } else if (preRecordSnapshot) {
      baseSnapshot = preRecordSnapshot;
    }
  } catch (e) {
    baseSnapshot = null;
  }
  // Persist the deepest undone state too — redoStack[0] is the maximal drawing
  // (most strokes). With it plus the applied strokes above, a refresh can rebuild
  // the redo stack, so undone strokes aren't lost on reload.
  let redoStrokes = null, redoStrokeGroups = null;
  if (redoStack.length) {
    const deepest = redoStack[0];
    if (deepest && deepest.strokes) {
      redoStrokes = deepest.strokes.slice();
      redoStrokeGroups = (deepest.strokeGroups || []).slice();
    }
  }
  return {
    version: 1,
    writerId: WRITER_ID,
    savedAt: new Date().toISOString(),
    baseSnapshot: baseSnapshot,
    strokes: strokes.slice(),
    strokeGroups: strokeGroups.slice(),
    redoStrokes: redoStrokes,
    redoStrokeGroups: redoStrokeGroups,
    background: { color: bgColor },
    // Metadata only — no bytes. Prefer live media; fall back to pending meta
    // (from a restore where the user hasn't re-added the file yet) so it persists.
    photoMeta: (photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
      ? { name: photoBgImg._fileName, fit: photoFit, opacity: photoOpacityVal_, blur: photoBlur_, offset: { x: photoOffsetX, y: photoOffsetY }, zoom: photoZoom }
      : (typeof pendingPhotoMeta !== 'undefined' ? pendingPhotoMeta : null),
    musicMeta: currentMusicMeta()
  };
}

// The loop numbers only mean anything once loadedmetadata/decodeAudioData has
// run. Before that `trimEnd` is still its initial 0, and an autosave landing in
// that window used to persist a zero-length "loop" — which came back on re-add
// as the 0.5s minimum-loop clamp in applyPendingMusicSettings, and rendered as
// "Loop 0:00–0:00" on the pending card. While the duration is unknown we keep a
// previously saved loop for the same file if there is one, and otherwise write
// the name with null trim values so the load-time defaults apply instead of a
// bogus loop. (Flip doesn't need this: decodeForWaveform installs its 20s
// default BEFORE applying any saved meta, so a null never reaches the clamp.)
function currentMusicMeta() {
  const prev = (typeof pendingMusicMeta !== 'undefined') ? pendingMusicMeta : null;
  if (!(audioEl && audioEl._fileName)) return prev;
  const decoded = Number.isFinite(audioDuration) && audioDuration > 0 && trimEnd > trimStart;
  if (!decoded) {
    if (prev && prev.name === audioEl._fileName) return prev;
    return { name: audioEl._fileName, trimStart: null, trimEnd: null, crossfadeMs: loopCrossfadeMs };
  }
  return { name: audioEl._fileName, trimStart: trimStart, trimEnd: trimEnd, crossfadeMs: loopCrossfadeMs };
}

function showAutosaveStatus(state) {
  const el = document.getElementById('autosaveStatus');
  const txt = document.getElementById('autosaveStatusText');
  if (!el || !txt) return;
  clearTimeout(el._hideTimer);
  el.hidden = false;
  el.classList.remove('saving', 'failed', 'partial');
  if (state === 'saving') { el.classList.add('saving'); txt.textContent = 'Saving…'; }
  // 'failed' and 'full' are both red, and the difference matters: 'full' means
  // the browser's storage for this origin is out of room and the drawing is NOT
  // saved, which the user can act on; 'failed' is anything else and they cannot.
  // They used to be one message, and that is exactly why an "Autosave failed"
  // report could not be diagnosed from the screenshot -- every possible
  // exception, including a plain TypeError in serializeAutosave(), arrived as
  // the same four words.
  else if (state === 'failed') { el.classList.add('failed'); txt.textContent = 'Autosave failed'; }
  else if (state === 'full') { el.classList.add('failed'); txt.textContent = 'Storage full — not saved'; }
  // Amber means: media is attached and its BYTES are not durably stored —
  // the IndexedDB write failed or hasn't settled (lib/draftstore.js). With a
  // working store this state is rare; when it shows, it is true, and it stays
  // up until a successful save replaces it.
  else if (state === 'saved-no-media') { el.classList.add('partial'); txt.textContent = 'Saved without media'; }
  else { txt.textContent = 'Saved'; }
  requestAnimationFrame(() => el.classList.add('show'));
  // "Saved" fades after a moment; "saving" stays until resolved. 'failed' and
  // 'saved-no-media' now STAY UP: each one describes an ONGOING durability
  // problem (storage write failed / media bytes not persisted), and a warning
  // that fades after 1.6s tells the user the problem went away when it did not
  // (external review #3: "do not hide the only warning ... when it represents
  // an ongoing durability state"). They clear when a later successful write
  // replaces them with 'saved'.
  if (state !== 'saving' && state !== 'failed' && state !== 'full' && state !== 'saved-no-media') {
    el._hideTimer = setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => { el.hidden = true; }, 300);
    }, 1600);
  }
}

function writeAutosave() {
  // Player mode is read-only — never mutate the editor's autosave.
  if (document.body.classList.contains('player-mode')) return;
  // Nothing meaningful on the canvas AND nothing undone to preserve → clear any
  // stale save. (Keep it when redo is pending, so undoing to blank then reloading
  // can still redo the undone strokes.)
  if (!hasContent && strokes.length === 0 && redoStack.length === 0) {
    try {
      // Two fences before an empty state may clear the slot:
      //   1. OWNERSHIP — this session must have written real work here first.
      //      Without it, an idle fresh tab's visibilitychange flush deleted
      //      the stored draft while the restore banner was still offering it.
      //      (Explicit discard is untouched: the banner's Discard button calls
      //      clearAutosave(), not this path.)
      //   2. LIVENESS — even an owning tab must not delete a record another
      //      tab wrote AFTER this page loaded; that is someone else's live
      //      draft, not a stale copy of ours.
      if (!sessionOwnedDraft) { durableRev = draftRev; return; }
      const raw = localStorage.getItem(AUTOSAVE_KEY);
      if (raw) {
        const rec = JSON.parse(raw);
        if (rec && rec.writerId && rec.writerId !== WRITER_ID &&
            rec.savedAt && rec.savedAt > PAGE_LOADED_AT) {
          durableRev = draftRev;  // our (empty) state needs nothing stored
          return;
        }
      }
      localStorage.removeItem(AUTOSAVE_KEY); durableRev = draftRev;
    } catch (e) {}
    return;
  }
  // Capture the revision BEFORE serializing: an edit landing between serialize
  // and the durableRev assignment must leave the draft marked not-durable.
  const rev = draftRev;
  try {
    // MAKE ROOM RATHER THAN GIVE UP. The origin's ~5MB is shared with Flip's
    // autosave and with every local save's payload, and a full store used to
    // mean the drawing in front of the user was simply not written -- for every
    // stroke, forever, however small the drawing.
    //
    // Two passes, cheapest first. SkriblPosted.reclaim() sweeps orphaned
    // payloads (unreachable: no tray entry can open them, so nothing is lost)
    // and only then evicts the OLDEST local save, which is destructive and is
    // why it is second and why it says so in the console. An old saved copy is
    // worth less than the work on screen.
    const payload = JSON.stringify(serializeAutosave());
    try {
      localStorage.setItem(AUTOSAVE_KEY, payload);
    } catch (quotaErr) {
      if (!window.SkriblPosted || !window.SkriblPosted.reclaim) throw quotaErr;
      const freed = window.SkriblPosted.reclaim(payload.length);
      if (!freed) throw quotaErr;
      console.warn('[skribl] storage was full — reclaimed',
                   Math.round(freed / 1024) + 'KB from saved Skribls to autosave this drawing');
      localStorage.setItem(AUTOSAVE_KEY, payload);   // still throws if it is not enough
    }
    durableRev = rev;
    sessionOwnedDraft = true;   // real work written: later empty = deliberate clear
    const hasPhoto = !!((photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
                        || (typeof pendingPhotoMeta !== 'undefined' && pendingPhotoMeta));
    const hasMusic = !!((audioEl && audioEl._fileName)
                        || (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta));
    // The amber pill used to be a designed limitation ("bytes never fit in
    // localStorage"). With IndexedDB holding the bytes it is a FAILURE signal:
    // media attached, and its store write failed or hasn't settled. When the
    // bytes are confirmed durable, the truthful pill is plain "Saved".
    showAutosaveStatus((hasPhoto || hasMusic) && !mediaDurabilityOk()
                       ? 'saved-no-media' : 'saved');
  } catch (e) {
    // Quota or private-mode failure — the pill says so, persistently, and
    // draftIsDurable() stays false, which is what arms the leave guard.
    //
    // TELL THE CONSOLE WHAT ACTUALLY HAPPENED. This catch covers the whole
    // expression, serializeAutosave() included, so a TypeError in there looked
    // identical to a full disk and a bug report of "autosave failed" could not
    // be told apart from "your browser is out of room". Names differ by engine
    // (QuotaExceededError on Chromium/Firefox, NS_ERROR_DOM_QUOTA_REACHED on
    // older Gecko, code 22) so the test is deliberately loose.
    const quota = e && (e.name === 'QuotaExceededError'
                        || e.name === 'NS_ERROR_DOM_QUOTA_REACHED'
                        || e.code === 22 || e.code === 1014);
    try {
      let used = 0, biggest = null, biggestLen = 0;
      for (const k of Object.keys(localStorage)) {
        const len = (localStorage.getItem(k) || '').length;
        used += len;
        if (len > biggestLen) { biggestLen = len; biggest = k; }
      }
      console.warn('[skribl] autosave failed:', e && e.name, e && e.message,
                   '| localStorage', Math.round(used / 1024) + 'KB in',
                   Object.keys(localStorage).length, 'keys | largest:',
                   biggest, Math.round(biggestLen / 1024) + 'KB');
    } catch (_) { console.warn('[skribl] autosave failed:', e && e.name, e && e.message); }
    showAutosaveStatus(quota ? 'full' : 'failed');
  }
}

// Write NOW, synchronously, and report whether the draft is durable. Called
// before intentional navigation and on pagehide/visibilitychange — the 1.2s
// debounce is a batching convenience, and it must never be a loss window
// (review P0-2: draw a stroke, tap Flip inside 1.2s, work gone).
function flushPadDraft() {
  clearTimeout(autosaveTimer);
  try { writeAutosave(); } catch (e) {}
  return draftIsDurable();
}

// Debounced: batch a flurry of edits into one write ~1.2s after activity stops.
function scheduleAutosave() {
  // Same triggers as ever, one new fact: something changed, so the draft on
  // disk no longer matches the document. draftRev is that fact as a number.
  draftRev++;
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(writeAutosave, 1200);
}

function clearAutosave() {
  clearTimeout(autosaveTimer);
  try { localStorage.removeItem(AUTOSAVE_KEY); durableRev = draftRev; } catch (e) {}
  // The draft is being deliberately discarded (posted, or cleared) — the
  // media bytes belong to it and go with it.
  if (window.SkriblDraftStore) {
    SkriblDraftStore.del('pad:photo').catch(() => {});
    SkriblDraftStore.del('pad:music').catch(() => {});
  }
  mediaDraft.photo = 'none'; mediaDraft.music = 'none';
}

function readAutosave() {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    const hasDrawing = (data.strokes && data.strokes.length) || data.baseSnapshot;
    return hasDrawing ? data : null;
  } catch (e) {
    return null;
  }
}

// Reconstruct the per-stroke undo AND redo history for a restored drawing. The
// autosave persists the drawing plus the deepest undone state (the maximal stroke
// set) and how many strokes are currently applied — not the stacks themselves,
// which are piles of full-canvas snapshots far too big to store. So we rebuild
// them here: snapshot the canvas at each stroke boundary of the maximal drawing,
// exactly as startDraw does live. States before the applied cut become the undo
// stack; states after it become the redo stack. Result — a restored Skribl undoes
// AND redoes stroke by stroke, identical to one edited this session. Undo is
// bounded to the last 30 (the in-session cap). Renders the applied state on the
// canvas as it goes. Fully guarded: any failure falls back to the applied drawing
// with no history, never a broken stack.
//   maxStrokes/maxGroups — the maximal drawing (applied + undone strokes)
//   appliedCount         — how many strokes are currently on the canvas (prefix)
function rebuildHistoryForRestore(maxStrokes, maxGroups, appliedCount, baseHasContent) {
  undoStack = [];
  redoStack = [];
  const total = maxGroups.length;
  appliedCount = Math.max(0, Math.min(appliedCount, total));
  // starts[k] = point index where stroke k begins; starts[total] = all points.
  const starts = [];
  let acc = 0;
  for (let k = 0; k <= total; k++) { starts.push(acc); if (k < total) acc += maxGroups[k]; }

  const snapshotMain = () => {
    const s = document.createElement('canvas');
    s.width = Math.max(1, canvas.width);
    s.height = Math.max(1, canvas.height);
    if (canvas.width > 0 && canvas.height > 0) s.getContext('2d').drawImage(canvas, 0, 0);
    return s;
  };
  // Render base + the first k strokes. clearAndRestore is synchronous once the
  // base image is cached, so the canvas is fully painted before we snapshot.
  const renderPrefix = (k) => clearAndRestore(() => paintStrokesStatic(maxStrokes.slice(0, starts[k])));
  const stateAt = (k) => {
    renderPrefix(k);
    return {
      image: snapshotMain(),
      strokes: maxStrokes.slice(0, starts[k]),
      strokeGroups: maxGroups.slice(0, k),
      hasContent: (k === 0) ? baseHasContent : true
    };
  };

  const build = () => {
    try {
      // Undo: the state before each applied stroke = state(0)..state(appliedCount-1),
      // capped to the most recent 30.
      const undoFirst = Math.max(0, appliedCount - 30);
      for (let k = undoFirst; k < appliedCount; k++) undoStack.push(stateAt(k));
      // Redo: the undone future states = state(appliedCount+1)..state(total), pushed
      // deepest-first so pop() yields the next redo (appliedCount+1) first.
      for (let k = total; k > appliedCount; k--) redoStack.push(stateAt(k));
    } catch (e) {
      undoStack = [];
      redoStack = [];
    }
    // Leave the applied state on the canvas as the live drawing.
    renderPrefix(appliedCount);
    undoBtn.disabled = undoStack.length === 0;
    redoBtn.disabled = redoStack.length === 0;
  };

  // Warm the base-image cache once (async only on the first load), then build the
  // snapshots synchronously inside the callback.
  clearAndRestore(build);
}

function restoreAutosave(data) {
  clearCanvas();
  if (data.background && data.background.color) {
    bgColor = data.background.color;
    canvasWrap.style.backgroundColor = bgColor;
    document.querySelectorAll('.bg-swatch').forEach(b => b.classList.toggle('active', b.dataset.bg === bgColor));
  }
  updateVignette();
  strokes = (data.strokes || []).slice();
  strokeGroups = (data.strokeGroups || []).slice();

  const { width: cw, height: ch } = getCanvasLogicalSize();
  // The autosave stores the *applied* strokes in strokes/strokeGroups and, if any
  // strokes were undone (redo pending), the *maximal* drawing in redoStrokes/
  // redoStrokeGroups. Rebuild both stacks around the applied cut so undo AND redo
  // survive the refresh.
  const hasRedo = !!(data.redoStrokes && data.redoStrokes.length);
  const maxStrokes = hasRedo ? data.redoStrokes.slice() : strokes.slice();
  const maxGroups = (hasRedo && data.redoStrokeGroups) ? data.redoStrokeGroups.slice() : strokeGroups.slice();
  const appliedCount = strokeGroups.length;   // strokes currently on canvas (a prefix of maximal)
  if (strokes.length || hasRedo) {
    preRecordSnapshot = data.baseSnapshot || null;
    hasContent = strokes.length > 0 || !!preRecordSnapshot;
    // The pre-stroke base only counts as content if a photo was baked into it.
    rebuildHistoryForRestore(maxStrokes, maxGroups, appliedCount, !!(data.photoMeta && data.photoMeta.name));
  } else if (data.baseSnapshot) {
    // Base image with no strokes (e.g. a saved photo background): just draw it.
    preRecordSnapshot = null;
    const baseImg = new Image();
    baseImg.onload = () => { ctx.drawImage(baseImg, 0, 0, cw, ch); };
    baseImg.src = data.baseSnapshot;
    hasContent = true;
  }
  if (strokes.length) {
    hasContent = true;
    recorded = true;
    finishedRecording = true;
    playWrap.hidden = false;
    postBtn.hidden = false;
    // v269 changed Post's posture: it ships in the header DISABLED from first
    // paint and every path that produces a postable take clears the flag. This
    // path predates that and only un-hid the button — which was the whole
    // reveal back when Post was hidden-until-take — so a restored drawing sat
    // behind a dimmed Post until the user recorded a NEW take on top of it.
    // Reported from the live demo the day v269 shipped.
    postBtn.disabled = false;
    updateDrawingTimeLabels();
    durationBadge.hidden = false;
  } else if (data.baseSnapshot) {
    hasContent = true;
  }
  updateEmptyHint();
  updateCanvasLockCue();
  updateClearVisibility();

  // Set pending media and show the placeholder cards with their saved settings.
  pendingMusicMeta = (data.musicMeta && data.musicMeta.name) ? data.musicMeta : null;
  pendingPhotoMeta = (data.photoMeta && data.photoMeta.name) ? data.photoMeta : null;
  refreshPendingCards();

  const hadMedia = pendingMusicMeta || pendingPhotoMeta;
  showToast(hadMedia ? 'Restored — re-add your media below' : 'Drawing restored', null);
}

// ---------- Autosave wiring ----------
(function initAutosave() {
  // Player mode is read-only: no restore prompt, no autosave triggers. Covers
  // both the Flask path player (SKRIBL_MODE==='player', no hash) and the local
  // #skribl=<id> hash player.
  if ((typeof window !== 'undefined' && window.SKRIBL_MODE === 'player') ||
      /^#skribl=/.test(location.hash || '')) return;
  const banner = document.getElementById('restoreBanner');
  const sub = document.getElementById('restoreSub');
  const confirmBtn = document.getElementById('restoreConfirm');
  const discardBtn = document.getElementById('restoreDiscard');
  let bannerTimer = null;

  function hideBanner() {
    banner.classList.remove('show');
    bannerTimer = setTimeout(() => { banner.hidden = true; }, 400);
  }

  // On load: if there's a saved drawing, offer to restore it.
  const saved = readAutosave();
  if (saved) {
    const bits = [];
    if (saved.savedAt) {
      try {
        const d = new Date(saved.savedAt);
        bits.push(d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }));
      } catch (e) {}
    }
    const media = [];
    if (saved.musicMeta && saved.musicMeta.name) media.push('music');
    if (saved.photoMeta && saved.photoMeta.name) media.push('photo');
    if (media.length) bits.push(media.join(' + ') + ' to re-add');
    sub.textContent = bits.join(' · ') || 'From your last session';

    banner.hidden = false;
    requestAnimationFrame(() => banner.classList.add('show'));

    confirmBtn.addEventListener('click', () => {
      restoreAutosave(saved);
      // Confirming the restore is taking OWNERSHIP of the slot (same rule as
      // Flip's tryRestore): the session now holds this content, so a later
      // empty state is a deliberate clear. An unclaimed banner confers
      // nothing — the idle-flush fence keeps protecting the record.
      sessionOwnedDraft = true;
      hideBanner();
      // Media bytes come back from IndexedDB by driving the SAME pipeline a
      // manual re-add uses: put the stored File on the real <input> and
      // dispatch a real change event. Validation, the drawer handlers, and the
      // pendingPhotoMeta/pendingMusicMeta settings-reapply wiring in app.js
      // all run exactly as if the user had picked the file — because as far as
      // the app can tell, they did. No second attach path to keep correct.
      reAddMediaFromStore('photo', 'photoInput', saved.photoMeta);
      reAddMediaFromStore('music', 'musicInput', saved.musicMeta);
      // Write a fresh autosave reflecting the restored state, so reloading
      // again doesn't re-show this same prompt.
      setTimeout(writeAutosave, 200);
    });
    discardBtn.addEventListener('click', () => {
      clearAutosave();
      hideBanner();
    });
  }

  // Triggers: schedule an autosave whenever the drawing meaningfully changes.
  canvas.addEventListener('mouseup', scheduleAutosave);
  canvas.addEventListener('touchend', scheduleAutosave);
  // Authoring controls, absent from the player's template. bindEl() already
  // exists for exactly this and null-checks; these three predate it.
  bindEl('recordBtn', 'click', scheduleAutosave);
  bindEl('undoBtn', 'click', scheduleAutosave);
  bindEl('redoBtn', 'click', scheduleAutosave);
  bindEl('bgGroup', 'click', scheduleAutosave);
  customBgInput.addEventListener('input', scheduleAutosave);

  // Media triggers — so adding/adjusting music or photo is captured too.
  bindEl('musicInput', 'change', scheduleAutosave);
  bindEl('photoInput', 'change', scheduleAutosave);
  bindEl('musicRemove', 'click', scheduleAutosave);
  bindEl('photoRemove', 'click', scheduleAutosave);
  bindEl('photoOpacity', 'input', scheduleAutosave);
  bindEl('photoBlur', 'input', scheduleAutosave);
  // Loop changes: trim handles, nudges, match-drawing, zoom handles all funnel
  // through updateTrimUI → so trigger autosave from the music track interactions.
  musicTrack.addEventListener('mouseup', scheduleAutosave);
  musicTrack.addEventListener('touchend', scheduleAutosave);
  if (zoomTrackWrap) {
    zoomTrackWrap.addEventListener('mouseup', scheduleAutosave);
    zoomTrackWrap.addEventListener('touchend', scheduleAutosave);
  }
  document.querySelectorAll('.nudge-btn').forEach(b => b.addEventListener('click', scheduleAutosave));
  matchDrawingBtn.addEventListener('click', scheduleAutosave);
  document.querySelectorAll('.photo-fit-btn').forEach(b => b.addEventListener('click', scheduleAutosave));
})();


// ---------- Media bytes: IndexedDB capture, removal, and restore ----------
// Bytes are stored ONCE, at attach time — they only change when the user picks
// a different file, so writing them on every autosave would be pure waste.
// Capture-phase listeners see the File before any other handler can clear the
// input's value. A put that resolves marks the slot durable; a put that
// rejects marks it failed, which keeps the amber pill up and arms the guard.

const _MEDIA_INPUTS = { photo: 'photoInput', music: 'musicInput' };
const _MEDIA_REMOVES = { photo: 'photoRemove', music: 'musicRemove' };

function _refreshMediaPill() {
  // Only speak when a save has already spoken — this refines the pill the
  // last write showed, it never conjures one before the first save.
  const el = document.getElementById('autosaveStatus');
  if (!el || el.hidden) return;
  if (durableRev === draftRev) {
    showAutosaveStatus(mediaDurabilityOk() ? 'saved' : 'saved-no-media');
  }
}

Object.keys(_MEDIA_INPUTS).forEach((kind) => {
  const input = document.getElementById(_MEDIA_INPUTS[kind]);
  if (input) input.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!window.SkriblDraftStore) { mediaDraft[kind] = 'failed'; return; }
    mediaDraft[kind] = 'saving';
    SkriblDraftStore.put('pad:' + kind, {
      blob: file, name: file.name, type: file.type, savedAt: Date.now()
    }).then(() => { mediaDraft[kind] = 'durable'; _refreshMediaPill(); })
      .catch(() => { mediaDraft[kind] = 'failed'; _refreshMediaPill(); });
  }, true);  // capture: run even if a later handler clears the input
  const rm = document.getElementById(_MEDIA_REMOVES[kind]);
  if (rm) rm.addEventListener('click', () => {
    mediaDraft[kind] = 'none';
    if (window.SkriblDraftStore) SkriblDraftStore.del('pad:' + kind).catch(() => {});
  });
});

function reAddMediaFromStore(kind, inputId, meta) {
  if (!window.SkriblDraftStore || !meta || !meta.name) return;
  SkriblDraftStore.get('pad:' + kind).then((rec) => {
    // The stored bytes must be THE file the metadata describes — a name
    // mismatch means the draft and the blob are from different sessions,
    // and re-attaching the wrong file is worse than the amber pill.
    if (!rec || !rec.blob || rec.name !== meta.name) return;
    const input = document.getElementById(inputId);
    if (!input) return;
    let file;
    try { file = new File([rec.blob], rec.name, { type: rec.type || rec.blob.type || '' }); }
    catch (e) { return; }
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }).catch(() => {});
}

// ---------- Flush on leave: the debounce is never a loss window ----------
// pagehide covers reload, tab close, and real navigation; visibilitychange
// covers mobile app-switch and the lifecycle states where pagehide is not
// guaranteed to run. Both are best-effort by nature — which is exactly why the
// IN-APP navigation path (the guard above and the Flip link) flushes
// explicitly and can still stop the user; these two are the net under it.
window.addEventListener('pagehide', () => { flushPadDraft(); });
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flushPadDraft();
});

// Flip was a bare <a href>, so leaving Pad was a plain navigation with nothing
// in its way: one tap and an unposted drawing was gone. Deliberately NOT
// beforeunload — that fires on reload and tab-close too, where the browser
// shows its own untranslatable string and cannot say WHICH work is at risk.
(function guardFlipNavigation() {
  const flipBtn     = document.getElementById('flipBtn');
  const leaveSheet  = document.getElementById('leaveSheet');
  const leaveGo     = document.getElementById('leaveGo');
  const leaveCancel = document.getElementById('leaveCancel');
  if (!flipBtn || !leaveSheet || !leaveGo || !leaveCancel) return;

  // Guard what is ACTUALLY at risk — which is now a MEASURED fact, not an
  // inference from content type. History of this predicate, because each form
  // was wrong in a way the next one fixed:
  //   v1: recording || hasContent — fired on work that was never at risk, so
  //       people learned to dismiss it without reading.
  //   v2: photoBg || currentAudioBuffer — right while media bytes COULDN'T be
  //       stored, and wrong twice once they could: it kept warning after
  //       IndexedDB made media durable, and it stayed SILENT when localStorage
  //       itself was broken and the drawing was the thing at risk (external
  //       review #19: "navigation safety is keyed to 'media present', not to
  //       whether the current revision is actually durable").
  //   v3 (this): flush synchronously, then ask whether the flush left the
  //       draft durable. With working storage the guard never fires — the
  //       direction doc's intended end state. With broken storage it fires
  //       for exactly the work that would be lost.
  const atRisk = () => !flushPadDraft();
  let released = false;

  flipBtn.addEventListener('click', (e) => {
    if (released || !atRisk()) return;
    e.preventDefault();
    // Flip now lives IN the overflow menu, so that menu is open at this moment.
    // Leaving it up would stack the confirm on top of it.
    if (typeof closeMenu === 'function') closeMenu(true);
    leaveSheet.hidden = false;
    const scrim = document.getElementById('leaveScrim');
    if (scrim) scrim.hidden = false;
    leaveCancel.focus();   // focus the SAFE choice
  });
  const close = () => { leaveSheet.hidden = true;
    const scrim = document.getElementById('leaveScrim');
    if (scrim) scrim.hidden = true; };
  leaveCancel.addEventListener('click', close);
  leaveGo.addEventListener('click', () => {
    released = true;
    // Navigate directly rather than re-clicking the anchor: a synthetic click
    // re-enters this handler, and `released` is all that stops the loop.
    window.location.href = flipBtn.getAttribute('href');
  });
  leaveSheet.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.stopPropagation(); close(); }
  });
})();
