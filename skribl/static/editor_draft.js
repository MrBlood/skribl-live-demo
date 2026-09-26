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
//                           when the file is picked, and AGAIN on any later
//                           save while that write has failed — a phone can
//                           accept a multi-megabyte put and never settle it,
//                           so the write also has a deadline (v294). "Saved
//                           without media" is therefore a failure signal
//                           about THIS save rather than a verdict carried
//                           from attach time, and it no longer fades: a
//                           durability problem is a state, not a toast. It
//                           can be acknowledged, which hides the note without
//                           pretending the media is safe.
//   the leave guard         fires on !durable rather than on media presence.
//                           A write still in flight is neither, so it gets
//                           1.5s to land before the sheet is the answer
//                           (v294); with working storage the guard then never
//                           fires, which is the direction doc's intended end
//                           state, and with broken storage it fires for
//                           exactly the work at risk. Flip has the same guard
//                           on its Skribl Pad row, for the same reason.
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

// COMPOSE MODE KEEPS NO PAD DRAFT (v315). The Pad opened from a host's composer
// is drawing an attachment, and the host holds that drawing (composehost.js).
// Sharing this slot did three wrong things: a drawing removed from the post
// came back on the next open, an unrelated Pad draft appeared inside someone's
// post, and "Add to post" left its drawing to overwrite the author's own Pad
// draft. So compose neither restores from nor writes to the slot or the media
// store — the ordinary Pad's draft is untouched by anything done in a post.
const PAD_DRAFT_OFF = (typeof window !== 'undefined' && window.SKRIBL_MODE === 'compose');

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
// The attached File itself, per slot, so a failed store write can be RETRIED
// on a later save. Until v294 the bytes went to IndexedDB exactly once, at
// attach time, and that verdict stood for the whole session: one rejected or
// hung write (WebKit on iOS can accept a multi-megabyte put and never settle
// it) was a permanent "Saved without media" over media that was loaded and in
// front of the user. Flip re-spills its whole payload on every save and heals
// by itself; the Pad's per-file write now heals the same way.
const _mediaFile = { photo: null, music: null };
// ONE WRITE OWNS A SLOT AT A TIME, and a superseded write must go quiet. The
// deadline below fires twelve seconds after a put is issued; if the file was
// removed, replaced, or the draft discarded in the meantime, that timer used
// to land on a slot it no longer described and mark it 'failed' — amber, and
// the leave guard armed, on a page with no media at all, with no way back
// because the retry needs a file the session no longer has (v294 bug check).
// Every path that ends a slot's life bumps this, and both arms check it.
const _mediaSeq = { photo: 0, music: 0 };
const MEDIA_STORE_TIMEOUT_MS = 12000;   // Flip's SPILL_TIMEOUT_MS, for the same reason
function storeMediaBytes(kind) {
  const file = _mediaFile[kind];
  if (!file || PAD_DRAFT_OFF) return;
  if (!window.SkriblDraftStore) { mediaDraft[kind] = 'failed'; return; }
  if (mediaDraft[kind] === 'saving') return;   // one write in flight at a time; a hung one is given up below
  const seq = ++_mediaSeq[kind];
  const current = () => seq === _mediaSeq[kind];
  mediaDraft[kind] = 'saving';
  // A put that never settles is not a put that is still working. Past the
  // deadline the bytes are treated as not durable — the truthful reading — and
  // the next save tries again. A late resolve is ignored: `settled` guards
  // both arms, and the retry is what confirms the bytes.
  let settled = false;
  const deadline = setTimeout(() => {
    if (settled || !current()) return;
    settled = true;
    mediaDraft[kind] = 'failed';
    _refreshMediaPill();
    console.error('[skribl] ' + kind + ' bytes: store write did not settle in ' + MEDIA_STORE_TIMEOUT_MS + 'ms');
  }, MEDIA_STORE_TIMEOUT_MS);
  SkriblDraftStore.put('pad:' + kind, {
    blob: file, name: file.name, type: file.type, savedAt: Date.now()
  }).then(() => { if (settled || !current()) return; settled = true; clearTimeout(deadline); mediaDraft[kind] = 'durable'; _refreshMediaPill(); })
    .catch((e) => { if (settled || !current()) return; settled = true; clearTimeout(deadline); mediaDraft[kind] = 'failed'; _refreshMediaPill();
                    // NAMED, because there is no console on a phone and lib/report.js
                    // carries this line: two screenshots from the owner's iPhone showed
                    // the failure and nothing about its cause (v294).
                    console.error('[skribl] ' + kind + ' bytes: store write failed: ' + _errName(e)); });
}
function _errName(e) { return e ? ((e.name || 'Error') + (e.message ? ': ' + e.message : '')) : 'unknown'; }
// For lib/report.js: the media store as this session sees it.
window.skriblMediaStoreState = () => 'photo ' + mediaDraft.photo + ', music ' + mediaDraft.music;
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

/* The pill itself — its five states, the wording, and the way out — is
   lib/autosavepill.js since v294, one owner for both editors. The Pad hands it
   the three facts only the Pad knows. Until v294 the Pad's copy said "Saved
   without media", did nothing when tapped, and with a pending record and no
   bytes reported plain green ("shouldn't they be unified?"). */
function _pendingMusicLost() {
  return !!(typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta && !(audioEl && audioEl._fileName));
}
function _pendingPhotoLost() {
  return !!(typeof pendingPhotoMeta !== 'undefined' && pendingPhotoMeta
            && !(photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName));
}
function _pendingMediaLost() { return _pendingMusicLost() || _pendingPhotoLost(); }
// A photo or a track IS a draft (v294 audit, finding 1). The empty-state test
// below asked only about ink, so a session with media and no strokes was
// "nothing meaningful": never written, never offered back, and the bytes
// already in IndexedDB became orphans. Flip has always counted media.
function _mediaPresent() {
  return !!((photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
            || (audioEl && audioEl._fileName)
            || (typeof pendingPhotoMeta !== 'undefined' && pendingPhotoMeta)
            || (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta));
}
if (window.SkriblAutosavePill) window.SkriblAutosavePill.configure({
  pending: _pendingMediaLost,
  open: () => {
    if (typeof refreshPendingCards === 'function') refreshPendingCards();
    if (typeof _padDrawerCtl !== 'undefined' && _padDrawerCtl) _padDrawerCtl.open(_pendingMusicLost() ? 'music' : 'photo');
  },
  dismiss: () => {
    pendingMusicMeta = null; pendingPhotoMeta = null;
    if (typeof refreshPendingCards === 'function') refreshPendingCards();
    scheduleAutosave();
  }
});
function showAutosaveStatus(state) {
  if (window.SkriblAutosavePill) window.SkriblAutosavePill.show(state);
}

function writeAutosave() {
  // Player mode is read-only — never mutate the editor's autosave.
  if (document.body.classList.contains('player-mode') || PAD_DRAFT_OFF) return;
  // Nothing meaningful on the canvas AND nothing undone to preserve → clear any
  // stale save. (Keep it when redo is pending, so undoing to blank then reloading
  // can still redo the undone strokes.)
  if (!hasContent && strokes.length === 0 && redoStack.length === 0 && !_mediaPresent()) {
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
    // A slot whose bytes failed to store gets another write with every save
    // (v294). The amber below is then a report on THIS save, not a verdict
    // carried from attach time.
    Object.keys(mediaDraft).forEach((kind) => { if (mediaDraft[kind] === 'failed' && _mediaFile[kind]) storeMediaBytes(kind); });
    const hasPhoto = !!((photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)
                        || (typeof pendingPhotoMeta !== 'undefined' && pendingPhotoMeta));
    const hasMusic = !!((audioEl && audioEl._fileName)
                        || (typeof pendingMusicMeta !== 'undefined' && pendingMusicMeta));
    // The amber pill used to be a designed limitation ("bytes never fit in
    // localStorage"). With IndexedDB holding the bytes it is a FAILURE signal:
    // media attached, and its store write failed or hasn't settled. When the
    // bytes are confirmed durable, the truthful pill is plain "Saved".
    // ...and amber too while a pending record has no bytes behind it: the
    // session has LOST that file, and a green light over a re-add card in a
    // shut drawer was the Pad's state until v294.
    showAutosaveStatus(((hasPhoto || hasMusic) && !mediaDurabilityOk()) || _pendingMediaLost()
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
  if (PAD_DRAFT_OFF) durableRev = draftRev;
  else try { localStorage.removeItem(AUTOSAVE_KEY); durableRev = draftRev; } catch (e) {}
  // The draft is being deliberately discarded (posted, or cleared) — the
  // media bytes belong to it and go with it.
  if (window.SkriblDraftStore && !PAD_DRAFT_OFF) {
    SkriblDraftStore.del('pad:photo').catch(() => {});
    SkriblDraftStore.del('pad:music').catch(() => {});
  }
  mediaDraft.photo = 'none'; mediaDraft.music = 'none';
  _mediaFile.photo = null; _mediaFile.music = null;
  _mediaSeq.photo++; _mediaSeq.music++;   // a write still in flight no longer describes this session
}

function readAutosave() {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    const hasDrawing = (data.strokes && data.strokes.length) || data.baseSnapshot;
    const hasMedia = (data.photoMeta && data.photoMeta.name) || (data.musicMeta && data.musicMeta.name);
    return (hasDrawing || hasMedia) ? data : null;
  } catch (e) {
    return null;
  }
}

// Reconstruct the per-stroke undo AND redo history for a restored drawing. The
// autosave persists the drawing plus the deepest undone state (the maximal stroke
// set) and how many strokes are currently applied — not the stacks themselves.
// Each rebuilt state is a stroke-boundary slice over the maximal set (pixel-less
// — see stateAt below), exactly the shape startDraw pushes live. States before
// the applied cut become the undo stack; states after it become the redo stack.
// Result — a restored Skribl undoes AND redoes stroke by stroke, identical to
// one edited this session. Undo is bounded to the last 30 (the in-session cap).
// Fully guarded: any failure falls back to the applied drawing with no history,
// never a broken stack.
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

  // States are PIXEL-LESS: {base + strokes} is the whole truth of a restored
  // drawing (renderPrefix below paints exactly that), so each state is two
  // array slices and a reference — no per-state render, no per-state
  // full-canvas snapshot. The old build rendered AND snapshotted every stroke
  // boundary: on a 1,000-stroke drawing that was 30 multi-MB canvases plus
  // 30 near-full repaints in one synchronous burst at restore time — the
  // owner's "it seemed fine until all of a sudden it just slowed down".
  // restoreHistoryState (app.js) repaints these states on undo/redo.
  const renderPrefix = (k) => clearAndRestore(() => paintStrokesStatic(maxStrokes.slice(0, starts[k])));
  const stateAt = (k) => ({
    image: null,
    base: preRecordSnapshot,
    strokes: maxStrokes.slice(0, starts[k]),
    strokeGroups: maxGroups.slice(0, k),
    hasContent: (k === 0) ? baseHasContent : true
  });

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
    unrecordedInk = false;   // the restored canvas is exactly base + strokes
    hasContent = strokes.length > 0 || !!preRecordSnapshot;
    // The pre-stroke base only counts as content if a photo was baked into it.
    rebuildHistoryForRestore(maxStrokes, maxGroups, appliedCount, !!(data.photoMeta && data.photoMeta.name));
  } else if (data.baseSnapshot) {
    // Base image with no strokes (e.g. a saved photo background): just draw it.
    // With preRecordSnapshot deliberately null, these pixels are exactly the
    // ink the stroke list can't rebuild — history states must carry snapshots
    // until the next fresh-take capture bakes them into a base.
    preRecordSnapshot = null;
    unrecordedInk = true;
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

  // The bytes are asked for next (reAddMediaFromStore, below). The route amber
  // is shown by the store lookup when it MISSES, not here: shown at this
  // moment it was a false alarm flashed on every healthy restore (v294 audit,
  // finding 3), teaching the user to ignore the real one.
  //
  // The same words Flip says, because it is the same event (v294 audit,
  // finding 5). "Drawing restored" belongs to Clear's undo, in app.js.
  showToast('Draft restored', null);
}

// ---------- Autosave wiring ----------
(function initAutosave() {
  // Player mode is read-only: no restore prompt, no autosave triggers. Covers
  // both the Flask path player (SKRIBL_MODE==='player', no hash) and the local
  // #skribl=<id> hash player.
  if ((typeof window !== 'undefined' && window.SKRIBL_MODE === 'player') ||
      /^#skribl=/.test(location.hash || '')) return;
  // ONE RESTORE MODEL, AND IT IS FLIP'S (v294 audit, finding 5; owner:
  // "Restore is your recommendation"). The Pad used to ASK — a banner offering
  // "Unsaved drawing found / Discard / Restore" — while Flip applied its draft
  // at boot and said so with a chip. The asking had a reason: the Pad's
  // autosave held strokes but not media BYTES, so a silent restore would have
  // presented a partial drawing as the whole one. The bytes come back from
  // IndexedDB since v222, so the reason is gone, and what remained was two
  // editors that felt like two products on the one screen a returning user
  // sees first.
  //
  // So: the draft is applied, the toast says "Draft restored", and the media
  // follows from the store. Discarding is Clear all in the ⋯ menu, which
  // clears the canvas, the media and the autosave — the same thing the
  // banner's Discard did, in the place a person looks for it rather than in a
  // prompt they must answer before they can draw.
  //
  // OWNERSHIP: a restore claims the slot, exactly as the banner's Restore did
  // and as Flip's tryRestore() does. A later empty canvas is then a deliberate
  // clear rather than a fresh tab's flush, which is what the fence in
  // writeAutosave() protects.
  //
  // SAFE AT PARSE TIME: app.js calls resizeCanvas() synchronously while it
  // loads, so the canvas has its real size before this file runs.
  const saved = PAD_DRAFT_OFF ? null : readAutosave();
  if (saved) {
    restoreAutosave(saved);
    sessionOwnedDraft = true;
    // Media bytes come back from IndexedDB by driving the SAME pipeline a
    // manual re-add uses: put the stored File on the real <input> and dispatch
    // a real change event. Validation, the drawer handlers, and the
    // pendingPhotoMeta/pendingMusicMeta settings-reapply wiring all run exactly
    // as if the user had picked the file — because as far as the app can tell,
    // they did. No second attach path to keep correct.
    reAddMediaFromStore('photo', 'photoInput', saved.photoMeta);
    reAddMediaFromStore('music', 'musicInput', saved.musicMeta);
    // Write a fresh autosave reflecting the restored state.
    setTimeout(writeAutosave, 200);
  }

  // Triggers: schedule an autosave whenever the drawing meaningfully changes.
  // pointerup (v315): Pad draws on Pointer Events and prevents the pointerdown,
  // so a canvas mouseup never fires after a mouse stroke.
  canvas.addEventListener('pointerup', scheduleAutosave);
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
// Bytes are written when the user picks a file, and written AGAIN on later
// saves while that write has failed (storeMediaBytes, above) — never on every
// autosave, which would be pure waste, and never on a restore, whose bytes
// came out of the store a moment ago. Capture-phase listeners see the File
// before any other handler can clear the input's value. A put that resolves
// marks the slot durable; one that rejects or hangs marks it failed, which
// keeps the amber pill up and arms the guard.

const _MEDIA_INPUTS = { photo: 'photoInput', music: 'musicInput' };
const _MEDIA_REMOVES = { photo: 'photoRemove', music: 'musicRemove' };
// Set by reAddMediaFromStore for the one change event it dispatches: the File
// on the input CAME FROM the store, so the slot is durable by definition and
// the attach pipeline's write is skipped. Until v294 a restore re-wrote a
// multi-megabyte blob that was already there — on a phone, the write that
// hangs — and sat amber for the deadline over a session that was fine.
const _fromStore = { photo: false, music: false };

function _refreshMediaPill() {
  // Only speak when a save has already spoken — this refines the pill the
  // last write showed, it never conjures one before the first save.
  const el = document.getElementById('autosaveStatus');
  if (!el || el.hidden) return;
  if (durableRev === draftRev) {
    showAutosaveStatus(mediaDurabilityOk() && !_pendingMediaLost() ? 'saved' : 'saved-no-media');
  }
}

Object.keys(_MEDIA_INPUTS).forEach((kind) => {
  const input = document.getElementById(_MEDIA_INPUTS[kind]);
  if (input) input.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    _mediaFile[kind] = file;
    if (_fromStore[kind]) { _fromStore[kind] = false; mediaDraft[kind] = 'durable'; _refreshMediaPill(); return; }
    mediaDraft[kind] = 'none';   // a fresh file is a fresh attempt, never a hung one's shadow
    storeMediaBytes(kind);
  }, true);  // capture: run even if a later handler clears the input
  const rm = document.getElementById(_MEDIA_REMOVES[kind]);
  if (rm) rm.addEventListener('click', () => {
    mediaDraft[kind] = 'none';
    _mediaFile[kind] = null;
    _mediaSeq[kind]++;   // a put still in flight is about a file that is gone
    // WRITE THE DRAFT FIRST, DELETE THE BYTES SECOND (v294 audit, finding 8).
    // The draft was rewritten by the 1.2 s debounce while the bytes went at
    // once, so a tab that died in that window came back offering a re-add card
    // for a file the user had removed. This listener is registered after
    // editor_music.js's and editor_photo.js's, so the media globals are
    // already cleared and the flush writes a record that names no file.
    flushPadDraft();
    if (window.SkriblDraftStore) SkriblDraftStore.del('pad:' + kind).catch(() => {});
  });
});

function reAddMediaFromStore(kind, inputId, meta) {
  if (!meta || !meta.name) return;
  // Every way the bytes can fail to come back ends here: the pending record
  // stays, and the pill says so and is the route to the re-add card. This is
  // the ONE place the route amber is raised on restore.
  const missed = (why) => {
    console.error('[skribl] ' + kind + ' bytes: not restored from the store: ' + why);
    showAutosaveStatus('saved-no-media');
  };
  if (!window.SkriblDraftStore) { missed('no store'); return; }
  SkriblDraftStore.get('pad:' + kind).then((rec) => {
    // The stored bytes must be THE file the metadata describes — a name
    // mismatch means the draft and the blob are from different sessions,
    // and re-attaching the wrong file is worse than the amber pill.
    if (!rec || !rec.blob) { missed('no record for ' + meta.name); return; }
    if (rec.name !== meta.name) { missed('record is ' + rec.name + ', draft wants ' + meta.name); return; }
    const input = document.getElementById(inputId);
    if (!input) { missed('no input'); return; }
    let file;
    try { file = new File([rec.blob], rec.name, { type: rec.type || rec.blob.type || '' }); }
    catch (e) { missed('File: ' + _errName(e)); return; }
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    _fromStore[kind] = true;
    input.dispatchEvent(new Event('change', { bubbles: true }));
    _fromStore[kind] = false;   // consumed by the capture listener above; never left armed
  }).catch((e) => { missed(_errName(e)); });
}

// ---------- Re-add: settings back onto a file that comes back --------------
// Carved from app.js in v294 (PR 4b): the player downloads app.js and never
// re-adds anything, and this block — with the photo re-apply that v294, 5 made
// load-based — is what pushed the player's JavaScript past its ratchet. The
// music half re-applies in editor_music.js's loadedmetadata handler
// (applyPendingMusicSettings, app.js); this is the photo half and the cards'
// buttons. Globals it reads (pendingPhotoMeta, photoBgImg, photoFit,
// refreshPendingCards, the sliders) are app.js's, as before the move.
// Reapply saved media settings when the user re-adds a file after a restore.
if (typeof pendingMusicMeta !== 'undefined') {
  const musicInputEl = document.getElementById('musicInput');
  // Music trim reapply is handled in the main loadedmetadata handler
  // (applyPendingMusicSettings) to avoid a listener-timing race.

  const photoInputEl = document.getElementById('photoInput');
  // Absent on the player, which has no photo picker.
  if (photoInputEl) photoInputEl.addEventListener('change', () => {
    if (!pendingPhotoMeta) return;
    const meta = pendingPhotoMeta;
    pendingPhotoMeta = null;
    const pCard = document.getElementById('photoPending');
    if (pCard) pCard.hidden = true;
    photoUploadBtn.hidden = false;
    // The dot stays AMBER without this. Amber means "remembered but missing —
    // re-add it"; the user has just re-added it, so it must go green. This
    // path cleared the meta and the card by hand but never the dot's .pending
    // class, and refreshPendingCards is the only function that owns it.
    refreshPendingCards();
    // WHEN THE IMAGE LOADS, not 140 ms later. Attach is async — a decode
    // check, a FileReader, normalisation — and this listener runs on the change
    // event before any of it; a timer fired before the image was showing and
    // the saved fit, opacity, blur and zoom were dropped without a word (v294
    // audit, finding 4; the music side has always re-applied in
    // loadedmetadata). The name guard keeps a stale listener from dressing a
    // different photo if this attach was refused.
    const apply = () => {
      if (!photoBgImg || photoBgImg.style.display === 'none') return;
      if (meta.fit) {
        photoFit = meta.fit;
        const fitMap = { cover: 'cover', contain: 'contain', stretch: 'fill' };
        photoBgImg.style.objectFit = fitMap[photoFit] || 'cover';
        const fitBtns = [...document.querySelectorAll('.photo-fit-btn')];
        fitBtns.forEach(b => b.classList.toggle('active', b.dataset.fit === photoFit));
        const activeIdx = fitBtns.findIndex(b => b.dataset.fit === photoFit);
        const moveSlider = () => {
          if (activeIdx < 0 || !photoFitSlider) return;
          const off = fitBtns.slice(0, activeIdx).reduce((s, b) => s + b.offsetWidth, 0);
          photoFitSlider.style.width = fitBtns[activeIdx].offsetWidth + 'px';
          photoFitSlider.style.transform = `translateX(${off}px)`;
        };
        moveSlider();
        setTimeout(moveSlider, 80);
      }
      if (meta.opacity != null) {
        photoOpacityVal_ = meta.opacity;
        photoBgImg.style.opacity = photoOpacityVal_;
        const opEl = document.getElementById('photoOpacity');
        opEl.value = Math.round(photoOpacityVal_ * 100);
        _authoringCtl('photoOpacityVal').textContent = Math.round(photoOpacityVal_ * 100) + '%';
        updateSliderFill(opEl);
      }
      if (meta.blur != null) {
        photoBlur_ = meta.blur;
        photoBgImg.style.filter = photoBlur_ > 0 ? `blur(${photoBlur_}px)` : '';
        const blEl = document.getElementById('photoBlur');
        blEl.value = photoBlur_;
        _authoringCtl('photoBlurVal').textContent = photoBlur_ + 'px';
        updateSliderFill(blEl);
      }
      if (meta.offset) {
        photoOffsetX = meta.offset.x != null ? meta.offset.x : 0.5;
        photoOffsetY = meta.offset.y != null ? meta.offset.y : 0.5;
      }
      photoZoom = clampPhotoZoom(meta.zoom);
      setZoomSliderUI();
      applyPhotoPosition();
      updateRepositionUI();
    };
    const onLoad = () => {
      photoBgImg.removeEventListener('load', onLoad);
      if (meta.name && photoBgImg._fileName !== meta.name) return;
      apply();
    };
    if (photoBgImg && photoBgImg.complete && photoBgImg.naturalWidth > 0
        && photoBgImg.style.display !== 'none' && (!meta.name || photoBgImg._fileName === meta.name)) apply();
    else if (photoBgImg) photoBgImg.addEventListener('load', onLoad);
  });

  // Pending card buttons: "Re-add" opens the file picker; "✕" dismisses.
  const mBtn = document.getElementById('musicPendingBtn');
  const mDismiss = document.getElementById('musicPendingDismiss');
  if (mBtn) mBtn.addEventListener('click', () => musicInputEl.click());
  if (mDismiss) mDismiss.addEventListener('click', () => {
    pendingMusicMeta = null;
    _authoringCtl('musicPending').hidden = true;
    musicUploadBtn.hidden = false;
    if (!audioEl) musicTabDot.hidden = true;
    scheduleAutosave();
  });

  const pBtn = document.getElementById('photoPendingBtn');
  const pDismiss = document.getElementById('photoPendingDismiss');
  if (pBtn) pBtn.addEventListener('click', () => photoInputEl.click());
  if (pDismiss) pDismiss.addEventListener('click', () => {
    pendingPhotoMeta = null;
    _authoringCtl('photoPending').hidden = true;
    photoUploadBtn.hidden = false;
    if (!photoBgImg || photoBgImg.style.display === 'none') _authoringCtl('photoTabDot').hidden = true;
    scheduleAutosave();
  });
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
  // A store write still in flight is not yet at risk and not yet safe: it gets
  // this long to land before the sheet is the answer (v294 audit, finding 6).
  // "Not durable" used to include 'saving', so the sheet opened for up to the
  // twelve-second deadline after every attach on a phone — a false alarm on
  // the common path, which teaches people to tap Leave unread.
  const GUARD_WAIT_MS = 1500;
  const writeInFlight = () => mediaDraft.photo === 'saving' || mediaDraft.music === 'saving';
  let released = false, waiting = false;   // `waiting`: a tap is polling an in-flight write
  const openSheet = () => {
    leaveSheet.hidden = false;
    const scrim = document.getElementById('leaveScrim');
    if (scrim) scrim.hidden = false;
    // The trap and the opener memory come from the shared utility; the
    // explicit focus that follows overrides its choice of first control,
    // because here the SAFE choice must be the one under the user's thumb
    // rather than whichever button the markup happens to list first.
    if (window.SkriblModal) window.SkriblModal.open(leaveSheet, flipBtn);
    leaveCancel.focus();   // focus the SAFE choice
  };
  const leave = () => { released = true; window.location.href = flipBtn.getAttribute('href'); };

  flipBtn.addEventListener('click', (e) => {
    if (released) return;
    // A SECOND TAP WHILE THE FIRST IS WAITING must not start a second decision:
    // the poll can still resolve to leave(), and it would then navigate out
    // from under the sheet this tap opened (v294 bug check).
    if (waiting) { e.preventDefault(); return; }
    if (!atRisk()) return;
    e.preventDefault();
    // Flip now lives IN the overflow menu, so that menu is open at this moment.
    // Leaving it up would stack the confirm on top of it.
    if (typeof closeMenu === 'function') closeMenu(true);
    if (writeInFlight() && !waiting) {
      waiting = true;
      const started = Date.now();
      const poll = () => {
        if (!writeInFlight() && draftIsDurable()) { waiting = false; leave(); return; }
        if (!writeInFlight() || Date.now() - started > GUARD_WAIT_MS) { waiting = false; openSheet(); return; }
        setTimeout(poll, 50);
      };
      poll();
      return;
    }
    openSheet();
  });
  const close = () => { leaveSheet.hidden = true;
    const scrim = document.getElementById('leaveScrim');
    if (scrim) scrim.hidden = true;
    if (window.SkriblModal) window.SkriblModal.close(leaveSheet); };
  leaveCancel.addEventListener('click', close);
  // Navigate directly rather than re-clicking the anchor: a synthetic click
  // re-enters this handler, and `released` is all that stops the loop.
  leaveGo.addEventListener('click', leave);
  leaveSheet.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.stopPropagation(); close(); }
  });
})();
