// CSRF: echo the token the server issued. Empty when the deployment is
// unauthenticated, in which case no header is sent and nothing changes.
function skriblPostHeaders(){
  const h = {'Content-Type':'application/json'};
  if (window.SKRIBL_CSRF_TOKEN) { h['X-Skribl-CSRF'] = window.SKRIBL_CSRF_TOKEN; }
  return h;
}
/* =============================================================================
   Flip Mode — now speaks the Pad's native data language.
   A frame is { strokes, strokeGroups } in the PAD's exact shape: strokes is a
   FLAT point array ({x, y, color, size, t, erase, start}) and strokeGroups holds
   per-stroke point counts — identical to app.js. The autosave payload is a real
   frame-format Skribl ({schemaVersion:2, playbackMode:'flip', fps, canvasSize,
   frames}), directly consumable by the pad's normalizeSkribl()/loadSkribl().
   That's the marriage: same data, two editors.
   ========================================================================== */
const COLORS = ["#ffffff","#7c5cff","#5b8cff","#f4326f","#1bcf8f","#ffae42","#000000"]; // Pad editor palette
const DPR = Math.min(window.devicePixelRatio||1, 2);
let CW = 0, CH = 0;              // mutable since v110 — set from FLIP_SIZES[0] below
// Canvas presets. The payload has ALWAYS carried canvasSize and the player has
// always honoured it (app.js establishEditorCanvas), so this needed no format
// change at all — Flip was simply hardcoded to one of the sizes it could already
// describe.
// The table moved to lib/canvassizes.js so Pad can read the same one — see that
// file for why the dimensions are derived rather than typed. Kept under the old
// name here so every existing call site (and verify_canvas.py) reads unchanged.
const FLIP_SIZES = window.SkriblCanvasSizes.SIZES;
// The default was a second hardcoded 640x460 that had to agree with the first
// entry of FLIP_SIZES by hand. Once the presets were corrected it agreed with
// nothing, and currentSizeId() reported 'custom' on a fresh canvas.
CW = FLIP_SIZES[0].w; CH = FLIP_SIZES[0].h;

const AUTOSAVE_KEY = 'skribl_flip_autosave_v1';

const pad = document.getElementById('pad');
const ctx = pad.getContext('2d');
pad.width = CW*DPR; pad.height = CH*DPR; ctx.scale(DPR,DPR);

// Resize every layer that is CW x CH at DPR. Stroke coordinates are deliberately
// NOT rescaled: a drawing keeps its position and size on the page, and a smaller
// canvas simply crops the view rather than silently distorting artwork. The
// strokes themselves are never destroyed, so switching back restores the framing.
const MAX_CANVAS_EDGE = 4096;
function applyCanvasSize(w, h, opts){
  // Review #8: this takes cssWidth/cssHeight straight off a payload, and the old
  // guard was only `> 0`. A crafted or corrupt draft could ask for 30000x30000
  // and we would allocate four canvases that size. Bound it, and require finite
  // numbers — NaN passes every comparison silently.
  // Whole pixels only, mirroring the server rule so an imported local draft and
  // a public payload behave identically. (Review round 4, #6)
  if(!(Number.isInteger(w) && Number.isInteger(h))) return false;
  if(!(w > 0 && h > 0 && w <= MAX_CANVAS_EDGE && h <= MAX_CANVAS_EDGE)) return false;
  if(w === CW && h === CH) return false;
  CW = w; CH = h;
  const layers = [[pad, ctx], [onionCv, octx], [tmpCv, tctx], [frameCv, fctx],
                  [artCv, actx]];   // the artwork stage resizes with the rest
  for(const pair of layers){
    const cv = pair[0], c = pair[1];
    if(!cv || !c) continue;
    cv.width = CW * DPR; cv.height = CH * DPR;
    c.setTransform(DPR, 0, 0, DPR, 0, 0);      // resizing resets the transform
  }
  if(!opts || opts.silent !== true){
    sizeStage(); buildStrip(); render(); scheduleSave();
  }
  return true;
}
function currentSizeId(){
  const m = FLIP_SIZES.find(s => s.w === CW && s.h === CH);
  return m ? m.id : 'custom';
}
function fitPad(){
  const stage = document.querySelector('.flip-stage');
  const availW = stage.clientWidth - 24, availH = stage.clientHeight - 6;
  // Capped at 1, not 1.4. The backing store is CW x CH x DPR (see pad.width
  // above), so any scale above 1 stretches a fixed bitmap and softens every
  // line — at 1.10 on a 1000px window, Flip's strokes were ~10% blurrier than
  // the same drawing in Pad, which has always clamped at 1 in
  // layoutEditorCanvas(). Same authored canvas, two different sizes on screen,
  // and the larger one was the worse one.
  const scale = Math.max(0.1, Math.min(availW/CW, availH/CH, 1));
  pad.style.width = Math.round(CW*scale)+'px';
  pad.style.height = Math.round(CH*scale)+'px';
  syncGrid();
  if(ZoomView && ZoomView.isZoomed()) ZoomView.reclamp();
}
// Give the canvas stage a stable height = viewport minus the fixed chrome (header,
// toolbar, chip, strip). Drawers live in .flip-drawers (not measured here), so an
// opened drawer never changes this — the canvas stays untouched and the page scrolls.
function sizeStage(){
  const stage = document.querySelector('.flip-stage');
  const px = sel => { const el=document.querySelector(sel); return el?el.offsetHeight:0; };
  // The settings drawer takes real height when open; without it here the stage
  // keeps its full size and pushes the strip off the bottom of the screen.
  const used = px('.header') + px('.tune-shell') + px('.flip-tools') + px('.flip-chip') + px('.strip-wrap') + 30;
  stage.style.height = Math.max(220, window.innerHeight - used) + 'px';
  fitPad();
}
// Pin the grid overlay to the canvas's actual rendered box (offsetWidth/Height
// include the 1px border) instead of trusting the wrapper's size, so it always
// covers the whole canvas edge-to-edge no matter how the flex wrapper sizes.
/* The grid, drawn on a canvas rather than painted with CSS gradients.
 *
 * WHY NOT GRADIENTS. Three faults, all of them visible and none of them
 * fixable in CSS:
 *
 *  1. TOP-LEFT JUSTIFIED. A gradient repeats from the origin, so a line lands
 *     on 0% but the closing edge gets none — the grid saturated the top and
 *     left borders and stopped short of the bottom and right.
 *  2. PHANTOM LINES. Percentage stops land on fractional pixels. A 1px line at
 *     x=103.6 is rendered as two dim half-lines, so parts of the grid looked
 *     doubled and parts looked faint.
 *  3. THE INSET WAS WRONG. This function subtracted a 1px border while the pad
 *     now has 2px, so the whole grid sat a pixel off centre.
 *
 * On a canvas every line is placed on an exact DEVICE pixel with fillRect, and
 * the closing edge is drawn explicitly. Nothing is fractional, so nothing is
 * phantom.
 */
// Grid overlay via the shared lib (lib/gridoverlay.js) — same maths as before,
// now shared with Pad. Lazily bound so a page without the overlay still loads.
let _gridCtl = null;
function syncGrid(){
  if(!_gridCtl){
    const g = document.getElementById('flipGrid');
    if(!g || typeof skriblGrid !== 'function') return;
    _gridCtl = skriblGrid(pad, g);
  }
  _gridCtl.sync();
}

window.addEventListener('resize', ()=>{ sizeStage(); positionSeg(); positionToolSlider(); if(!photoPanel.hidden) positionFitSlider(); });

let frames = [ newFrame() ];
let idx = 0;
let color = "#ffffff", size = 7, erasing = false, onion = true, fps = 12;
// Onion skin depth/tint are view-only session state — deliberately NOT persisted
// or posted, so they cannot affect the payload format or the player.
let onionDepth = 1, onionTint = false;
// Motion guides: the path the drawing travels, and the SPACING between pages.
// Spacing is the whole point — even gaps read as constant speed, gaps that
// widen read as acceleration. It is the classic spacing chart, drawn for you.
// Session-only view state, like onion: never persisted, never posted, and
// never rendered into a thumbnail, an export or a shared link.
let arcGuides = false;
const ARC_WINDOW = 12;         // pages either side; bounds both cost and clutter

const ONION_ALPHAS = [0.30, 0.17, 0.10];          // nearer frame = more visible
const ONION_TINTS  = ['#ff5f6d', '#ff9f43', '#ffd76a'];   // warmer = further back
let pageClip = null;                              // copied page, for paste
// Selection tokens — see the note in app.js. Flip is more exposed than the Pad
// because it clears the input immediately, so a second pick during a slow decode
// is easy. Bumped on selection AND removal. (Review round 9, #1)
let musicSelectionSeq = 0;
let imageSelectionSeq = 0;

// Export options — session-only view state, like onion. NOT persisted or posted.
// One pair of helpers feeds GIF, WebM and MP4 so the three can never disagree
// about what "Medium" or "pages 2–5" means.
const EX_SIZES = { full: 0, medium: 480, small: 320 };   // 0 = no cap (native)
let exSize = 'full';
let exFrom = 1, exTo = 0;        // exTo 0 means "through the last page"
// Loops applies to VIDEO ONLY. A GIF sets repeat=0 — one pass that loops
// forever — so repeating its frames would inflate the file for no gain. This
// was a hardcoded 2 in both video encoders with nothing in the UI saying so,
// which is why a 5.2s animation exported as a 10s MP4 while the header still
// read 5.2s. The default stays 2: a 1.5s clip posted to a feed reads as broken
// because video players do not loop the way GIFs do.
let exLoops = 2;
function exRange(){
  const n = frames.length;
  let a = Math.max(1, Math.min(parseInt(exFrom,10) || 1, n));
  let b = exTo ? Math.max(1, Math.min(parseInt(exTo,10) || n, n)) : n;
  if(b < a){ const t = a; a = b; b = t; }               // tolerate reversed input
  return { from: a, to: b, count: b - a + 1 };
}
// Seconds for ONE pass of the selected range, holds included. Shared so the
// readout and the encoders can never disagree about the length of a file.
function exLoopSeconds(){
  const r=exRange(); let units=0;
  for(let i=r.from-1;i<=r.to-1;i++) units+=frameHold(frames[i]);
  return units/(fps||12);
}
function exDims(){
  const cap = EX_SIZES[exSize] || 0;
  const scale = cap ? Math.min(1, cap / Math.max(CW, CH)) : 1;
  return { w: Math.max(2, Math.round(CW * scale)),
           h: Math.max(2, Math.round(CH * scale)), scale: scale };
}
let bgColor = '#0d0f14', strokeOpacity = 1, smoothingAlpha = 1;   // Pad-parity draw settings
let smoothPt = null, lastRaw = null;                              // smoothing stabilizer runtime
let bgImage = null, bgImageObj = null, imageName = '';            // one background image per animation
let photoFit = 'cover', photoOpacity = 1, photoBlur = 0, photoZoom = 1;   // image adjustments
let photoOffX = 0.5, photoOffY = 0.5, photoEnabled = true, reposMode = false;
let musicData = null, audioEl = null, musicMuted = false;         // one music loop per animation
let musicEnabled = true, trimStart = 0, trimEnd = null, audioDuration = 0;   // trim/loop
const MAX_LOOP_SECONDS = 20;   // hard cap on loop length; enforced at load AND on every drag
let audioCtx = null, currentAudioBuffer = null, loopCrossfadeMs = 0;         // decoded buffer for the waveform
let zoomMag = 1, zoomFocus = 'loop', zoomCenter = null;                       // Loop Detail magnification
let musicName = '';                                                          // track filename (shown in the dropzone)
let drawing = false, curCount = 0, playing = false, playTimer = null;
let strokePointerId = null;   // the pointer that owns the stroke in progress
let ZoomView = null, pinching = false, _pinch = null;                        // canvas magnify (pinch/pan)
let redoStack = [];   // undone strokes for the current frame ({pts,count})
/* v227 Select. These live UP HERE, with the other early state, and not beside
   the functions that use them 3000 lines below. `let` is in its temporal dead
   zone until its own line executes, and setTool() runs during init — so
   declaring them next to selClear() meant the very first setTool('pen') threw
   "Cannot access 'selSpans' before initialization", which aborted the rest of
   flip.js and took the filmstrip, the tool shelf and every later handler with
   it. A `typeof` guard cannot rescue a `let`; only the declaration order can. */
let selSpans = [], selRect = null, selOrigin = null;
let selMarqueeFrom = null, selMoveFrom = null, selDx = 0, selDy = 0;
// Mirrors `drawing`/`strokePointerId`: a second pointer (a palm, a second
// finger) must not steer a drag that a different one started.
let selecting = false, selPointerId = null;
/* Move mode's state, hoisted here for the same reason as the selection's above.
   It used to sit 500 lines down, next to setMoveMode() — and syncSelBar() reads
   moveMode, while setTool() calls selClear() -> syncSelBar() during init. So the
   first setTool('pen') threw "Cannot access 'moveMode' before initialization"
   and killed the rest of the file. THIRD time this file's scattered `let` state
   has done that. State that any early code path can reach belongs up here. */
let moveMode = false, moveScope = 'one', moveDx = 0, moveDy = 0;
let moveOrigin = null, moveDragging = false, moveStart = null;
// What Cut is holding, if anything. Up here for the same reason as the rest:
// syncSelBar() reads it to decide whether Paste has a cell, and setTool()
// reaches syncSelBar() during init.
let selClipboard = null;
/* v228 transform. selMode names what the current drag is doing; selSnap holds
   the selected points' ORIGINAL x/y/size for the duration of one gesture.

   A scale or a rotation is recomputed from that snapshot on every pointer move,
   never applied on top of the last frame. Translate could get away with
   compounding deltas -- it is exact under addition -- but scale and rotation are
   not: applying a ratio to an already-scaled value, sixty times a second, walks
   the geometry away from where the finger says it should be, and a drag out and
   back does not return to where it started. */
let selMode = null, selSnap = null, selPivot = null, selRef = null;
let editIdx = 0, armedDel = -1, armedClear = false;
let drawOnMode = false, drawOnRAF = null, dFrame = 0, dFrameStartPerf = 0;   // "draw-on" replay

function newFrame(){ return { strokes: [], strokeGroups: [], hold: 1 }; }
// Per-page hold: how many base-fps slots this page occupies. ALWAYS read through
// this — never trust f.hold to exist. Pages loaded from a pre-v109 payload have no
// hold field at all and must read as 1, which is what makes the change additive.
const MAX_HOLD = 4;
function frameHold(f){
  const h = Math.round(Number(f && f.hold));
  return (isFinite(h) && h >= 1) ? Math.min(h, MAX_HOLD) : 1;
}
function totalHoldUnits(from, to){
  let u = 0;
  for(let i=from; i<=to; i++) u += frameHold(frames[i]);
  return u;
}
function frame(){ return frames[idx]; }

/* ---- strokes and strokeGroups must leave this file in step -----------------
 *
 * `strokes` is FLAT and `strokeGroups` counts the points in each stroke, and
 * the server refuses a payload where they disagree — the user sees a red box on
 * the share sheet and cannot share at all:
 *
 *   'frames[9].strokeGroups' accounts for 317 points, but the strokes array
 *   contains 318.
 *
 * A stroke IN FLIGHT is exactly that state and legitimately so: pointerdown
 * pushes its first point immediately, and the group count is not pushed until
 * endStroke. Every point is accounted for the instant the pen lifts. The bug is
 * never the in-flight state itself — it is COPYING that state somewhere it
 * outlives the stroke.
 *
 * That is what shipped: `scheduleSave` debounces 800 ms, so a stroke begun
 * within 800 ms of the previous one finishing — which is simply drawing — was
 * serialised half-captured into the autosave. Measured: 9 points against 7
 * accounted. Nothing was wrong in memory, `endStroke` pushed the group a moment
 * later, and the session shared fine. But the DRAFT was already broken, and the
 * next reload restored it verbatim: from then on the page was permanently
 * unshareable, on whichever page the timer happened to land.
 *
 * So anything that copies a frame out of live memory takes the accounted prefix
 * instead. The in-flight tail is not lost — it is still in `frames`, still
 * drawn, and still counted the moment the stroke ends; it is only excluded from
 * the SNAPSHOT, which is a moment the user did not choose. Below the point
 * where the arrays are already in step this is a no-op, which is every call
 * except the ones this exists for.
 */
/* A frame arriving from OUTSIDE live memory — an autosave written by a build
 * that had this bug, a .skribl file, a payload — may already be out of step.
 * Prevention does not help anyone who has one: their draft is on their disk
 * now, it restores unshareable, and no amount of redrawing fixes it because the
 * orphaned points are in every subsequent save.
 *
 * Here the tail is ADOPTED rather than dropped, which is the opposite of
 * balancedPair and deliberately so. In a snapshot the tail is a stroke still
 * being drawn and excluding it loses nothing. On load it is ink the user has
 * been looking at since the reload — a stroke that was captured, drawn, and
 * only ever missing its accounting. Giving it a group entry is what endStroke
 * would have done, keeps the drawing identical, and makes it undoable.
 */
function healFrame(f){
  const strokes = Array.isArray(f.strokes) ? f.strokes : [];
  const groups = Array.isArray(f.strokeGroups) ? f.strokeGroups.slice() : [];
  let n = 0;
  for(const c of groups) n += c;
  if(n === strokes.length) return { strokes: strokes, strokeGroups: groups };
  if(n < strokes.length){ groups.push(strokes.length - n); return { strokes: strokes, strokeGroups: groups }; }
  while(groups.length && n > strokes.length) n -= groups.pop();
  return { strokes: strokes.slice(0, n), strokeGroups: groups };
}

function balancedPair(f){
  const groups = (f.strokeGroups || []).slice();
  const strokes = f.strokes || [];
  let n = 0;
  for(const c of groups) n += c;
  if(n === strokes.length) return { strokes: strokes.slice(), strokeGroups: groups };
  if(n < strokes.length) return { strokes: strokes.slice(0, n), strokeGroups: groups };
  // groups claim more than exist — a truncated or hand-built payload rather
  // than an in-flight stroke. Drop whole groups from the end until they fit,
  // so what remains is describable rather than approximately right.
  while(groups.length && n > strokes.length) n -= groups.pop();
  return { strokes: strokes.slice(0, n), strokeGroups: groups };
}

/* ---- autosave: a real frame-format Skribl ---- */
let _brushLastPt = null;
// See the note on Pad's _brushWidth: pixels per POINT, not per millisecond, and
// reset at every stroke start so a long reposition does not taper the first
// segment to a hairline.
function _brushWidth(base, pos, erase){
  if(erase || !window.SkriblBrush || SkriblBrush.name() === 'pen') return base;
  const d = (_brushLastPt && pos) ? Math.hypot(pos.x-_brushLastPt.x, pos.y-_brushLastPt.y) : 0;
  return SkriblBrush.shape(base, d);
}
let _mirrorPainting = false;
let _constrainActive = false;
let flipTool = 'pen';
let shapeKind = 'line';
let _shapePrev = null, _shapeAnchor = null;   // 'pen' | 'eraser' | 'shape'; `erasing` stays the fast path
let _saveT = null;
function scheduleSave(){ clearTimeout(_saveT); showAutosaveStatus('saving'); _saveT = setTimeout(saveNow, 800); }
// media:false drops the base64 bytes but keeps photo/musicMeta, so a restore can
// rebuild everything except the files themselves and prompt the user to re-add
// them. Used only by the localStorage autosave, which has a ~5 MB quota; the
// .skribl draft download (saveDraft) still serializes the full media.
function serializeFlip(opts){
  const withMedia = !opts || opts.media !== false;
  return {
    schemaVersion: 2, version: 2,
    playbackMode: 'flip', fps: fps,
    canvasSize: { cssWidth: CW, cssHeight: CH, dpr: 1 },
    savedAt: new Date().toISOString(),
    editIdx: idx,
    mediaOmitted: ((!withMedia && !!(bgImage || musicData)) || !!(pendingPhotoMeta || pendingMusicMeta)) || undefined,
    bgImage: withMedia ? (bgImage || null) : null,
    music: withMedia ? (musicData || null) : null,
    photo: bgImage ? { fit:photoFit, opacity:photoOpacity, blur:photoBlur, zoom:photoZoom, offX:photoOffX, offY:photoOffY, enabled:photoEnabled, name:imageName } : (pendingPhotoMeta || null),
    musicMeta: musicData ? { enabled:musicEnabled, trimStart:trimStart, trimEnd:trimEnd, crossfadeMs:loopCrossfadeMs, name:musicName } : (pendingMusicMeta || null),
    frames: frames.map(f => {
      // NOT f.strokes.slice(): that is what wrote a half-captured stroke into
      // the autosave and made the next reload unshareable. See balancedPair.
      const b = balancedPair(f);
      const o = { strokes: b.strokes, strokeGroups: b.strokeGroups, background: bgColor };
      const h = frameHold(f);
      if(h > 1) o.hold = h;      // omitted at the default => payload unchanged
      return o;
    })
  };
}
// localStorage is capped at ~5 MB per origin. A background image and especially a
// music track are stored as base64 data URLs, which inflate the payload by 4/3 and
// blow that budget on their own — a 30s WAV is ~6.7 MB. So: try the full payload,
// and on a quota error fall back to saving everything EXCEPT the media bytes rather
// than losing the whole session. (The Pad never had this bug: its autosave stores
// media metadata only — see serializeAutosave() in app.js, "Metadata only — no bytes".)
function isQuotaError(e){
  return !!e && (e.name === 'QuotaExceededError' || e.code === 22 ||
                 e.name === 'NS_ERROR_DOM_QUOTA_REACHED' || e.code === 1014);
}
let _sessionOwnedDraft = false;   // set on the first non-empty save this session
function saveNow(){
  const empty = frames.length === 1 && frames[0].strokes.length === 0 && !bgImage && !musicData;
  if (empty) {
    // Only clear the slot if THIS session put real work in it — then an empty
    // state is a deliberate clear-all. A session that never owned the slot
    // must leave it alone: flushFlipDraft() runs on visibilitychange, so an
    // idle fresh tab flushes while still empty, and without this gate that
    // flush deleted whatever draft was already in storage. (Same fence as
    // Pad's sessionOwnedDraft in editor_draft.js; found by the v222 release
    // aggregate when the flush ate verify_strokegroups' planted draft.)
    if (!_sessionOwnedDraft) return;
    try { localStorage.removeItem(AUTOSAVE_KEY); } catch (_) {} return;
  }
  _sessionOwnedDraft = true;
  // v231: MEDIA BYTES NEVER GO TO localStorage. They used to, and the spill to
  // IndexedDB below only happened once the write had already FAILED — which
  // made a ~5 MB origin quota the thing standing between a user and their
  // drawing. A background photo and especially a music track are base64 data
  // URLs, inflated 4/3 by the encoding; a 30s WAV is ~6.7 MB on its own. One
  // owner-reported symptom was the Pad's autosave failing outright, because
  // Flip's draft was sitting on 2.7 MB of a shared 5 MB budget.
  //
  // So the spill is the NORMAL path now, not the emergency one: strokes and
  // media METADATA go to localStorage (small, synchronous, fast to restore),
  // media BYTES go to IndexedDB, whose quota is measured in hundreds of MB.
  // The restore side already knew how to merge the two — it was written for
  // the quota case and has been correct all along; all that changed is that it
  // is now reached on purpose rather than after a failure.
  //
  // The Pad reached the same conclusion years earlier by a different route:
  // serializeAutosave() in app.js stores "metadata only — no bytes". This is
  // Flip catching up, with the bytes kept rather than dropped.
  const hasMedia = !!(bgImage || musicData);
  // BOTH, not just the library. lib/draftstore.js loads and defines its API
  // whether or not IndexedDB exists — it reports the absence by rejecting, which
  // is asynchronous and far too late to choose a strategy. Testing only for the
  // library meant a browser with IndexedDB disabled took the spill path anyway,
  // the put rejected, and a track small enough to fit perfectly well in
  // localStorage came back as "Saved without media". verify_fix.py runs its
  // whole context with window.indexedDB undefined and caught exactly that.
  const canSpill = !!window.SkriblDraftStore && typeof indexedDB !== 'undefined';
  if (!hasMedia) {
    // Nothing to spill: the lite payload IS the full payload, so this is one
    // synchronous write and no IndexedDB round trip.
    try {
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeFlip()));
      showAutosaveStatus((pendingPhotoMeta || pendingMusicMeta) ? 'saved-no-media' : 'saved');
      return;
    } catch (e) {
      if (!isQuotaError(e)) { console.error('[skribl] autosave failed:', e); showAutosaveStatus('failed'); return; }
      // A drawing alone over quota means something else on the origin is
      // hogging it; fall through to the reclaim path at the bottom.
    }
  } else if (!canSpill) {
    // Private-mode browsers and disabled IndexedDB have nowhere to put the
    // bytes. Try the old way — the whole payload into localStorage — and let
    // the quota decide. This is the ONLY route that still attempts it.
    try {
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeFlip()));
      showAutosaveStatus('saved');
      return;
    } catch (e) {
      if (!isQuotaError(e)) { console.error('[skribl] autosave failed:', e); showAutosaveStatus('failed'); return; }
    }
  }
  // pendingPhotoMeta / pendingMusicMeta are set ONLY when the bytes fail to
  // reach IndexedDB, in the .catch below. They used to be set here,
  // unconditionally, which was right when reaching this code meant the bytes
  // had already been dropped — it is wrong now that reaching it is the normal
  // way media gets saved. Nothing visible depended on it (every re-add card is
  // guarded by `&& !bgImage` / `&& !musicData`, and the live values are still in
  // memory), but serializeFlip() reads them for `mediaOmitted`, so the FULL
  // record written below would have claimed its own bytes were missing.
  const stamp = Date.now();
  if (window.SkriblDraftStore) {
    _mediaSpillState = 'saving';
    SkriblDraftStore.put('flip:draft', { json: JSON.stringify(serializeFlip()), savedAt: stamp })
      .then(() => { _mediaSpillState = 'durable';
                    // The session IS fully recoverable now — say so. (Only if
                    // the pill still shows this save's amber; never conjure.)
                    const el = document.getElementById('autosaveStatus');
                    if (el && !el.hidden) showAutosaveStatus('saved'); })
      .catch((e3) => { _mediaSpillState = 'failed';
                       // NOW the bytes really are lost, so the next restore has
                       // to offer the re-add cards. This is the one place that
                       // is true.
                       if (bgImage) pendingPhotoMeta = { fit:photoFit, opacity:photoOpacity, blur:photoBlur,
                                                         zoom:photoZoom, offX:photoOffX, offY:photoOffY,
                                                         enabled:photoEnabled, name:imageName };
                       if (musicData) pendingMusicMeta = { enabled:musicEnabled, trimStart:trimStart,
                                                           trimEnd:trimEnd, crossfadeMs:loopCrossfadeMs,
                                                           name:musicName };
                       showAutosaveStatus('saved-no-media');
                       console.error('[skribl] media spill to IndexedDB failed:', e3); });
  } else {
    _mediaSpillState = 'failed';
  }
  try {
    const lite = serializeFlip({ media: false });
    lite.mediaInIdb = true; lite.idbSavedAt = stamp;
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(lite));
    showAutosaveStatus('saved-no-media');
  } catch (e2) {
    // Last ditch: Flip has already dropped the media bytes and the lite payload
    // STILL will not fit. Make room the same way Pad does -- sweep orphaned
    // local-save payloads first (nothing can reach those), then evict the
    // oldest saved Skribl -- and try once more before saying it failed.
    let recovered = false;
    if (window.SkriblPosted && window.SkriblPosted.reclaim) {
      try {
        const body = JSON.stringify(lite);
        if (window.SkriblPosted.reclaim(body.length)) {
          localStorage.setItem(AUTOSAVE_KEY, body);
          showAutosaveStatus('saved-no-media');
          recovered = true;
        }
      } catch (e3) { /* fall through to the honest failure below */ }
    }
    if (!recovered) {
      console.error('[skribl] autosave failed even without media:', e2);
      showAutosaveStatus('failed');
    }
  }
}
// 'none' until a quota fallback happens; then tracks whether the full payload
// made it to IndexedDB. 'failed' means the amber pill is telling the truth
// the old way: settings survive, bytes do not.
let _mediaSpillState = 'none';
// Flush NOW — the 800ms debounce must never be a loss window (review P0-2).
// saveNow() is synchronous for the localStorage half; the IndexedDB half was
// written at the last quota save and only re-runs if this flush hits quota too.
function flushFlipDraft(){ clearTimeout(_saveT); try { saveNow(); } catch(_) {} }
window.addEventListener('pagehide', flushFlipDraft);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flushFlipDraft();
});
// Autosave status pill (ported from the Pad): "Saving…" while pending, then "Saved".
function showAutosaveStatus(state){
  const el=document.getElementById('autosaveStatus'), txt=document.getElementById('autosaveStatusText'); if(!el||!txt) return;
  clearTimeout(el._hideTimer); el.hidden=false; el.classList.remove('saving','failed','partial');
  if(state==='saving'){ el.classList.add('saving'); txt.textContent='Saving…'; }
  else if(state==='failed'){ el.classList.add('failed'); txt.textContent='Autosave failed'; }
  // Drawing + all settings saved; the media files were too large for localStorage.
  // Amber, not green — the session is not fully recoverable and the user should know
  // without having to open a drawer to find out.
  else if(state==='saved-no-media'){ el.classList.add('partial'); txt.textContent='Saved without media'; }
  else { txt.textContent='Saved'; }
  requestAnimationFrame(()=>el.classList.add('show'));
  // 'failed' and 'saved-no-media' STAY UP — each describes an ongoing
  // durability problem, and a warning that fades claims it was resolved
  // (review #3). A later successful save replaces them with 'saved'.
  if(state!=='saving' && state!=='failed' && state!=='saved-no-media'){ el._hideTimer=setTimeout(()=>{ el.classList.remove('show'); setTimeout(()=>{ el.hidden=true; }, 300); }, 1600); }
}
// Export progress overlay + cancel.
let _exportAbort=false;
function exportShow(label){ _exportAbort=false; const o=document.getElementById('flipExport'); if(!o) return;
  document.getElementById('flipExportLabel').textContent=label||'Exporting…'; document.getElementById('flipExportFill').style.width='0%'; o.hidden=false; }
function exportSet(frac, label){ const f=document.getElementById('flipExportFill'); if(f) f.style.width=(Math.max(0,Math.min(1,frac))*100)+'%'; if(label){ const l=document.getElementById('flipExportLabel'); if(l) l.textContent=label; } }
function exportHide(){ const o=document.getElementById('flipExport'); if(o) o.hidden=true; }
function applyPayload(d){
  // Restore the saved canvas size first, so frames/thumbs build at the right
  // dimensions. silent: the boot path (and the caller) renders straight after.
  if(d && d.canvasSize && d.canvasSize.cssWidth && d.canvasSize.cssHeight){
    applyCanvasSize(d.canvasSize.cssWidth, d.canvasSize.cssHeight, {silent:true});
  }
  if (!d || !Array.isArray(d.frames) || !d.frames.length) return false;
  frames = d.frames.map(f => {
    if (Array.isArray(f.strokeGroups)) {
      // current pad-format frame. Healed rather than trusted: a draft written
      // mid-stroke by an older build restores permanently unshareable, and the
      // user has no way to see why or to repair it. See healFrame.
      return healFrame(f);
    }
    // migrate the old prototype shape: [{color,size,erase,pts:[{x,y}]}]
    const flat = [], groups = [];
    (Array.isArray(f.strokes) ? f.strokes : []).forEach(st => {
      const pts = st.pts || [];
      pts.forEach((p, i) => flat.push({ x: p.x, y: p.y, color: st.color, size: st.size,
        t: 0, erase: !!st.erase, start: i === 0 }));
      if (pts.length) groups.push(pts.length);
    });
    return { strokes: flat, strokeGroups: groups };
  });
  idx = Math.min(d.editIdx != null ? d.editIdx : (d.idx || 0), frames.length - 1);
  const savedBg = (d.frames[0] && d.frames[0].background) || d.background;
  if (typeof savedBg === 'string' && /^#[0-9a-f]{6}$/i.test(savedBg)) bgColor = savedBg;
  bgImage  = (typeof d.bgImage === 'string' && d.bgImage.slice(0,10) === 'data:image') ? d.bgImage : null;
  musicData = (typeof d.music === 'string' && d.music.slice(0,10) === 'data:audio') ? d.music : null;
  const ph = d.photo || {};
  // Was ['cover','contain','fill'], which rejected the 'stretch' this file
  // itself posts and silently downgraded it to 'cover'.
  photoFit = localFit(ph.fit);
  photoOpacity = typeof ph.opacity==='number' ? ph.opacity : 1;
  photoBlur = typeof ph.blur==='number' ? ph.blur : 0;
  photoZoom = typeof ph.zoom==='number' ? ph.zoom : 1;
  photoOffX = typeof ph.offX==='number' ? ph.offX : 0.5;
  photoOffY = typeof ph.offY==='number' ? ph.offY : 0.5;
  photoEnabled = ph.enabled!==false; reposMode=false;
  imageName = typeof ph.name==='string' ? ph.name : '';
  const mm = d.musicMeta || {};
  musicEnabled = mm.enabled!==false;
  trimStart = typeof mm.trimStart==='number' ? mm.trimStart : 0;
  trimEnd = typeof mm.trimEnd==='number' ? mm.trimEnd : null;
  loopCrossfadeMs = typeof mm.crossfadeMs==='number' ? mm.crossfadeMs : 0;
  musicName = typeof mm.name==='string' ? mm.name : '';
  currentAudioBuffer = null; zoomMag = 1; zoomFocus = 'loop'; zoomCenter = null;
  if (d.fps === 6 || d.fps === 12 || d.fps === 24) {
    fps = d.fps;
    [...document.querySelectorAll('#fps button')].forEach(b=>b.classList.toggle('on', +b.dataset.fps === fps));
  }
  return frames.some(f => f.strokes.length);
}
// Media the autosave had to drop (too big for localStorage). Mirrors the Pad:
// the settings survive, the bytes don't, and the drawers show a "Re-add" card.
let pendingMusicMeta = null, pendingPhotoMeta = null;
function tryRestore(){
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return false;
    const d = JSON.parse(raw);
    if (d.mediaOmitted) {
      pendingMusicMeta = (d.musicMeta && d.musicMeta.name) ? d.musicMeta : null;
      pendingPhotoMeta = (d.photo && d.photo.name) ? d.photo : null;
      // The bytes may be sitting in IndexedDB from the quota spill. Restore
      // the media-less payload synchronously below (the drawing appears at
      // once), then swap in the full payload when the async read lands — but
      // ONLY if nothing has been edited in the gap and the two records are
      // from the same save, else the fetch would overwrite live work with a
      // stale copy. On any miss, the pendingMeta re-add cards above are the
      // fallback, exactly as before.
      if (d.mediaInIdb && window.SkriblDraftStore) {
        SkriblDraftStore.get('flip:draft').then((rec) => {
          if (!rec || !rec.json) return;
          // The guard here USED to be `localStorage.getItem(KEY) !== raw` — a
          // byte comparison of the record as it was when the read started. That
          // was serviceable while this path only ran after a quota failure, and
          // it is wrong now that it is how media normally comes back: every
          // save rewrites `savedAt`, so any autosave landing in the gap made the
          // string differ and the merge was refused as "edited since". The
          // media then never returned from a restore that had done nothing
          // wrong. verify_fix.py caught it the moment the path became normal.
          //
          // What actually has to be true is narrower: nothing may overwrite
          // media the session already has. If bgImage or musicData is set by
          // the time this lands, the user has loaded something newer and these
          // bytes are stale — refuse them individually below. Identity is
          // still checked by NAME against the meta the lite record carries, so
          // a swapped file is refused and same-name bytes from one save earlier
          // are the same file.
          const full = JSON.parse(rec.json);
          // Apply MEDIA ONLY, never the frames. The lite localStorage record
          // is always the newest drawing: the pagehide flush rewrites it
          // synchronously while its IndexedDB put can die with the page — so
          // the full payload here may be one save older, and applying it
          // wholesale could revert strokes. (A savedAt-equality guard was the
          // first version of this merge; it refused that dying-flush case
          // entirely, which meant the media never came back after exactly the
          // navigation the flush exists to survive.) The bytes are the only
          // thing the lite record lacks, and their identity is checked by
          // NAME against the meta the lite record itself carries — a swapped
          // file has a different name and is refused; same-name bytes from
          // one save earlier are the same file.
          let touched = false;
          if (!musicData &&
              typeof full.music === 'string' && full.music.slice(0, 10) === 'data:audio' &&
              d.musicMeta && full.musicMeta && full.musicMeta.name === d.musicMeta.name) {
            musicData = full.music;
            pendingMusicMeta = null; touched = true;
          }
          if (!bgImage &&
              typeof full.bgImage === 'string' && full.bgImage.slice(0, 10) === 'data:image' &&
              d.photo && full.photo && full.photo.name === d.photo.name) {
            bgImage = full.bgImage;
            pendingPhotoMeta = null; touched = true;
          }
          if (!touched) return;
          // Mirror the draft-FILE load tail (loadDraftFile below): restore the
          // image OBJECT and DECODE the audio — without the decode a restored
          // draft posts the whole sample instead of the cropped loop (measured
          // there: 3,528,082 B vs 588,082 B for the same 5s loop) and shows a
          // blank waveform. Then refresh the media UI, or the drawer dots and
          // re-add cards keep describing the media-less record this replaced.
          loadBgImageObj(() => { applyBg(); render(); });
          ensureAudio();
          if (musicData) decodeForWaveform();
          fitPad(); buildStrip(); render(); sizeFill(); setBg(bgColor); syncMediaUI();
        }).catch(() => {});
      }
    }
    const ok = applyPayload(d);
    // A successful restore is taking OWNERSHIP of the slot: the session now
    // holds its content, so clearing everything and flushing empty is a
    // deliberate clear and may remove the key — even inside the first save's
    // debounce window (verify_fix TEST 5 hits exactly that window). A record
    // this function REJECTS confers nothing: the tab is still empty, still
    // doesn't own the slot, and the idle-flush fence keeps protecting it.
    if (ok) _sessionOwnedDraft = true;
    return ok;
  } catch (e) { return false; }
}
function chip(msg){
  const el = document.getElementById('flipChip');
  el.textContent = msg; el.classList.add('show');
  clearTimeout(el._t); el._t = setTimeout(()=>el.classList.remove('show'), 2200);
}

/* ---- render primitives — the pad's exact dispatch (start-flag on flat points) ---- */
function drawDot(c, x, y, col, s, erase){
  c.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
  c.beginPath(); c.arc(x,y,s/2,0,Math.PI*2); c.fillStyle = erase ? '#000' : col; c.fill();
  c.globalCompositeOperation = 'source-over';
}
function drawLine(c, x1,y1,x2,y2, col, s, erase){
  // Live mirror feedback — see the note in endStroke about why the POINTS are
  // generated there and not here.
  if(window.SkriblMirror && SkriblMirror.active() && !_mirrorPainting){
    _mirrorPainting = true;
    try {
      const _a = SkriblMirror.reflect({x:x1,y:y1}, CW, CH);
      const _b = SkriblMirror.reflect({x:x2,y:y2}, CW, CH);
      for(let _i=0;_i<_a.length;_i++) drawLine(c, _a[_i].x,_a[_i].y,_b[_i].x,_b[_i].y, col, s, erase);
    } finally { _mirrorPainting = false; }
  }
  c.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
  c.strokeStyle = erase ? '#000' : col; c.lineWidth = s; c.lineCap='round'; c.lineJoin='round';
  c.beginPath(); c.moveTo(x1,y1); c.lineTo(x2,y2); c.stroke();
  c.globalCompositeOperation = 'source-over';
}
// Alpha helpers: opacity rides inside the per-point color as rgba(). A stroke with
// alpha < 1 is drawn SOLID onto a temp layer, then composited ONCE at that alpha, so
// overlapping dots/joints within the stroke don't stack into darker blobs (the pad's
// wet/dry idea). Fully-opaque and erase strokes draw straight through as before.
function alphaOf(col){ if(typeof col==='string'){ const m=col.match(/rgba?\([^)]*,\s*([\d.]+)\s*\)/i); if(m) return parseFloat(m[1]); } return 1; }
function solidOf(col){ if(typeof col==='string'){ const m=col.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i); if(m) return 'rgb('+m[1]+', '+m[2]+', '+m[3]+')'; } return col; }
function paintSeg(c, seg, solid){
  for (let i = 0; i < seg.length; i++) {
    const p = seg[i]; const col = solid ? solidOf(p.color) : p.color;
    if (i === 0) drawDot(c, p.x, p.y, col, p.size, p.erase);
    else { const pv = seg[i-1]; drawLine(c, pv.x, pv.y, p.x, p.y, col, p.size, p.erase); }
  }
}
function paintStatic(c, strokeArr){
  let i = 0;
  while (i < strokeArr.length) {
    let j = i + 1; while (j < strokeArr.length && !strokeArr[j].start) j++;   // one stroke = start .. next start
    const seg = strokeArr.slice(i, j);
    // Stroke layers, the same setting Pad's tune row drives. Off means paint
    // straight through, so a see-through stroke compounds at its own overlaps
    // — which is exactly what the layer exists to prevent, and now visible
    // rather than a global only a console could reach.
    const _layered = (typeof window.SKRIBL_STROKE_LAYERS === 'undefined')
      || window.SKRIBL_STROKE_LAYERS !== false;
    const a = (seg[0].erase || !_layered) ? 1 : alphaOf(seg[0].color);
    if (a >= 1) { paintSeg(c, seg, false); }
    else {
      tctx.clearRect(0,0,CW,CH);
      paintSeg(tctx, seg, true);                                    // solid on the temp layer
      c.globalAlpha = a; c.drawImage(tmpCv, 0, 0, CW, CH); c.globalAlpha = 1;
    }
    i = j;
  }
}

// Offscreen layer for onion skin: the previous frame is drawn at FULL opacity here,
// then composited onto the canvas ONCE at the target alpha — so overlapping dots/joints
// don't build up into dark blobs (the pad's wet/dry compositor idea, applied to onion).
const onionCv = document.createElement('canvas');
onionCv.width = CW*DPR; onionCv.height = CH*DPR;
const octx = onionCv.getContext('2d'); octx.scale(DPR,DPR);
// Separate temp layer for per-stroke opacity compositing (kept distinct from the
// onion layer so the two never draw onto each other).
const tmpCv = document.createElement('canvas');
tmpCv.width = CW*DPR; tmpCv.height = CH*DPR;
const tctx = tmpCv.getContext('2d'); tctx.scale(DPR,DPR);
// Frame layer: a frame's strokes are drawn here (transparent), then composited over
// the backdrop — so the eraser (destination-out) reveals the background image/colour
// instead of punching a hole. Shared by the live canvas, thumbnails, and export.
const frameCv = document.createElement('canvas');
frameCv.width = CW*DPR; frameCv.height = CH*DPR;
const fctx = frameCv.getContext('2d'); fctx.scale(DPR,DPR);

/* ---- ARTWORK STAGE ------------------------------------------------------
 * What the drawing IS: backdrop, background image, and the current page's
 * strokes. Nothing else is ever composited here — not onion skin, not the
 * motion path, not spacing dots, not selection bounds, not a cursor.
 *
 * The live pad is a PRESENTATION surface: artwork with editor overlays drawn
 * on top so you can work. Anything that reads a COLOUR or produces a FILE must
 * read the artwork instead, because an overlay is a temporary aid and has no
 * business in a picked colour or a published frame.
 *
 * This exists because the eyedropper read the pad. Measured before the change:
 * draw a red ring, add a page, and sample where only the onion skin shows —
 * it returned #561317, the onion's red at reduced alpha over the backdrop, a
 * colour present nowhere in the artwork. The motion guides had the same problem
 * and were patched with a suppress-and-repaint flag; that fixed one overlay and
 * would have needed repeating for the next one. This retires the class.
 */
const artCv = document.createElement('canvas');
artCv.width = CW*DPR; artCv.height = CH*DPR;
const actx = artCv.getContext('2d'); actx.scale(DPR,DPR);

// Composite the artwork as it stands. Cheap: the same two calls render() makes,
// minus every overlay. Callers ask for it on demand rather than keeping it in
// sync, so it can never drift from what is actually on the page.
function paintArtwork(){
  // Flip paints its own backdrop (drawBackdrop already composites the photo and
  // the background colour), so the shared stage is handed a finished backdrop
  // and only needs the strokes layered on. See lib/artwork.js.
  actx.setTransform(DPR,0,0,DPR,0,0);
  actx.clearRect(0,0,CW,CH);
  drawBackdrop(actx);
  fctx.clearRect(0,0,CW,CH);
  paintStatic(fctx, frame().strokes);
  return window.SkriblArtwork.stage({
    canvas: artCv, w: CW, h: CH, dpr: DPR, bg: null, photo: null,
    strokes: frameCv, keep: true
  });
}

// Where the background image lands, honouring fit + zoom + reposition.
function photoRect(iw, ih){
  // Shared with Pad and the player via lib/photofit.js. This used to special-
  // case only 'fill', so a 'stretch' — the value THIS FILE writes into the post
  // payload — rendered as cover with no fit button active. The lib treats
  // 'fill' as an alias of 'stretch', so both spellings land in the same place.
  return window.SkriblPhotoFit.rect(iw, ih, CW, CH,
    { fit: photoFit, offX: photoOffX, offY: photoOffY, zoom: photoZoom });
}
/* Flip stores the third fit as 'fill' and posts it as 'stretch'. Incoming
 * values may use either spelling, so they are mapped to the local one at every
 * entry point rather than at the one that happened to be noticed. */
function localFit(f){
  return window.SkriblPhotoFit.normalise(f) === 'stretch' ? 'fill'
                                                          : window.SkriblPhotoFit.normalise(f);
}
function drawBackdrop(c){
  c.save();
  c.fillStyle = bgColor; c.fillRect(0,0,CW,CH);
  if (photoEnabled && bgImageObj && bgImageObj.complete && bgImageObj.naturalWidth){
    const r = photoRect(bgImageObj.naturalWidth, bgImageObj.naturalHeight);
    c.globalAlpha = photoOpacity;
    if (photoBlur > 0) c.filter = 'blur(' + photoBlur + 'px)';
    c.drawImage(bgImageObj, r.x, r.y, r.w, r.h);
    c.filter = 'none'; c.globalAlpha = 1;
  }
  c.restore();
}
function paintFrame(c, strokes){ fctx.clearRect(0,0,CW,CH); paintStatic(fctx, strokes); c.drawImage(frameCv, 0, 0, CW, CH); }
// Centre of mass of a page's ink, in canvas coordinates. Averaging the stroke
// POINTS (not their bounding box) is what makes the path track the drawing's
// weight rather than its extremes, so a wobbling outline does not throw it.
// Cheap enough to recompute per render: bounded by ARC_WINDOW pages.
function frameCentroid(f){
  const pts = f && f.strokes;
  if(!pts || !pts.length) return null;
  let sx=0, sy=0, n=0;
  for(let i=0;i<pts.length;i++){
    const p=pts[i];
    if(p && typeof p.x === 'number' && typeof p.y === 'number'){ sx+=p.x; sy+=p.y; n++; }
  }
  return n ? { x:sx/n, y:sy/n } : null;
}

function drawArcGuides(c){
  const lo = Math.max(0, idx-ARC_WINDOW), hi = Math.min(frames.length-1, idx+ARC_WINDOW);
  const pts = [];
  for(let i=lo;i<=hi;i++){
    const ct = frameCentroid(frames[i]);
    if(ct) pts.push({ i, x:ct.x, y:ct.y });
  }
  if(pts.length < 2) return;      // one page has no motion to show
  c.save();
  c.lineCap='round'; c.lineJoin='round';
  // The arc itself, drawn twice: a dark casing under a light line so it stays
  // legible on both a white page and a black one without knowing which.
  for(const pass of [{w:3.5, col:'rgba(0,0,0,0.45)'}, {w:1.5, col:'rgba(125,125,255,0.95)'}]){
    c.beginPath();
    c.moveTo(pts[0].x, pts[0].y);
    for(let k=1;k<pts.length;k++){
      // Quadratic through midpoints: a smooth arc rather than a dogleg polyline,
      // which matters because the ARC is the thing being judged.
      const a=pts[k-1], b=pts[k];
      c.quadraticCurveTo(a.x, a.y, (a.x+b.x)/2, (a.y+b.y)/2);
    }
    c.lineWidth=pass.w; c.strokeStyle=pass.col; c.stroke();
  }
  // A dot per page. The GAPS between them are the spacing chart.
  for(const p of pts){
    const here = p.i === idx;
    c.beginPath();
    c.arc(p.x, p.y, here ? 5 : 3, 0, Math.PI*2);
    c.fillStyle = here ? 'rgba(160,140,255,1)' : 'rgba(255,255,255,0.85)';
    c.strokeStyle = 'rgba(0,0,0,0.55)'; c.lineWidth = 1.5;
    c.fill(); c.stroke();
  }
  c.restore();
}

function render(){
  ctx.clearRect(0,0,CW,CH);
  drawBackdrop(ctx);
  if(onion && !playing && idx>0){
    // Furthest frame first so nearer ones layer on top. Uses onionCv/octx, which
    // were scaffolded for exactly this in v98 and had sat unused ever since —
    // keeping frameCv free for the current frame below.
    const depth = Math.min(onionDepth, idx);
    for(let k=depth; k>=1; k--){
      const prev = frames[idx-k]; if(!prev) continue;
      octx.clearRect(0,0,CW,CH);
      paintStatic(octx, prev.strokes);
      if(onionTint){
        // source-in repaints the strokes' own pixels, leaving transparent areas
        // untouched — a silhouette tint, which is what onion skinning wants.
        octx.save();
        octx.globalCompositeOperation='source-in';
        octx.fillStyle = ONION_TINTS[k-1] || ONION_TINTS[ONION_TINTS.length-1];
        octx.fillRect(0,0,CW,CH);
        octx.restore();
      }
      ctx.globalAlpha = ONION_ALPHAS[k-1] || ONION_ALPHAS[ONION_ALPHAS.length-1];
      ctx.drawImage(onionCv, 0, 0, CW, CH);
      ctx.globalAlpha = 1;
    }
  }
  paintFrame(ctx, frame().strokes);
  // Last, so the guides read on top of the drawing rather than under it. Only
  // ever on the live pad: thumbnails, exports and the player all render through
  // their own contexts, so nothing here can be baked into what is published.
  if(arcGuides && !playing) drawArcGuides(ctx);
  // Shape preview. Flip repaints the whole frame every time, so the provisional
  // outline is just drawn last — no canvas copy is needed here, unlike Pad,
  // which paints incrementally and has nothing to repaint from.
  if(_shapePrev && typeof SkriblShapes !== 'undefined'){
    const pts = SkriblShapes.points(shapeKind, _shapePrev.a, _shapePrev.b, {square:_shapePrev.sq});
    const pcol = penColorFor(color);
    for(let i=1;i<pts.length;i++) drawLine(ctx, pts[i-1].x, pts[i-1].y, pts[i].x, pts[i].y, pcol, size, false);
  }
}

/* Bind an event without letting a missing element take the rest of the file
 * down with it.
 *
 * WHY. This file had 26 unguarded `getElementById(id).addEventListener(...)`
 * chains. A null from any ONE of them throws a TypeError at the top level,
 * which aborts the remainder of the script — so every binding written after
 * the failure never happens. The share button is bound near the end, which is
 * exactly the shape of "share does nothing while everything else works".
 *
 * A missing element is now logged and skipped. The log matters: lib/report.js
 * captures console output into the report sheet, so a control that quietly
 * stops working on a device we cannot reproduce still names itself.
 */
/* Is the user typing? Every global key handler needs this, so it lives at top
 * level: it used to be declared inside the pan/zoom block, invisible to
 * anything outside it, and the flip-scrub handler below threw a
 * ReferenceError on every arrow press because of it. */
function typingTarget(el){
  return !!(el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName || '') || el.isContentEditable));
}
// Legacy name, kept so the older handler below reads unchanged. There were
// THREE copies of this predicate in this file and they did not agree — one
// omitted SELECT — which is how a keyboard shortcut fires while you are
// choosing from a dropdown.
const _typingEl = typingTarget;

function bindEl(id, ev, fn, opts){
  const el = document.getElementById(id);
  if(!el){ console.warn('[skribl] missing element for binding:', id, ev); return null; }
  el.addEventListener(ev, fn, opts);
  return el;
}

/* ---- drawing (pad-format points, with timestamps for future replay) ---- */
function pos(e){ const r=pad.getBoundingClientRect(); return { x:(e.clientX-r.left)*(CW/r.width), y:(e.clientY-r.top)*(CH/r.height) }; }

/* ---- stylus pressure ------------------------------------------------------
   Pressure scales the EXISTING per-point `size`. It is deliberately NOT a new
   field on the point.

   A `pressure` key would have round-tripped — the server does not shape-check
   points and POST preserves unknown fields — but the player renders posted
   Skribls from `size` alone, so a pressure-aware Flip would have looked one way
   in the editor and another to everybody who opened the link. Baking it into
   `size` at capture time means the player, the GIF/MP4/WebM exporters, the
   thumbnail renderer and every already-released client get it for free, and an
   old payload is still a valid new payload.

   Applied ONLY for pointerType 'pen'. Mouse reports a constant 0.5 while down
   and most touchscreens report 0 or 0.5, so honouring those would either halve
   every mouse stroke or make width depend on hardware that isn't measuring
   anything. A device with no stylus draws exactly as it did before.

   MIN keeps a feather-light touch visible: pressure 0 draws at 35% of the
   nominal width rather than vanishing. Erasing ignores pressure — a variable
   eraser is a way to leave streaks you cannot see. */
const PRESSURE_MIN = 0.35;
function sizeFor(e, base){
  if(erasing) return base;
  if(!e || e.pointerType !== 'pen') return base;
  const raw = typeof e.pressure === 'number' ? e.pressure : 0;
  // Chromium reports 0 on the first pen event of a stroke often enough that
  // trusting it would start every line at minimum width. Treat 0 as "no
  // reading yet" and fall through to the nominal size.
  // Shared curve/floor/toggle: lib/pressure.js. See the note in that file about
  // why the raw read stays per-surface.
  return (typeof SkriblPressure !== 'undefined' && SkriblPressure)
    ? SkriblPressure.sizeFrom(base, raw)
    : (raw > 0 ? base * (PRESSURE_MIN + (1 - PRESSURE_MIN) * Math.min(1, raw)) : base);
}
let reposActive=false, reposStart=null;
pad.addEventListener('contextmenu', e=>e.preventDefault());
pad.addEventListener('pointerdown', e=>{ if(playing) return; if(pinching) return;
  // Space held = grab-pan; never a stroke (v211). Guarded HERE because Flip
  // draws on pointerdown, which fires BEFORE the mousedown the pan
  // intercept listens for — so a capture-phase mousedown was always too late.
  if(window._skriblSpaceHeld && window._skriblSpaceHeld()) return;
  // A STROKE BELONGS TO ONE POINTER. A second finger, or a palm landing beside
  // a pen, fired pointerdown while a stroke was already in progress: curCount
  // was reset to 1 and its point went into the SAME strokes array, so every
  // point captured up to that moment lost its group entry. The frame then
  // serialised with more points than strokeGroups accounts for and the server
  // refused the share:
  //   'frames[9].strokeGroups' accounts for 317 points, but the strokes array
  //   contains 318.
  // Reported from the live demo; reproduced by dispatching a second pointerdown
  // mid-stroke, which gives 22 points against 1 group. isPrimary is NOT enough
  // — each pointerType has its own primary, so a pen and a palm are both
  // primary — hence the id comparison.
  //
  // The Pad cannot reach this shape at all: it accumulates into a separate
  // `currentStroke` and concatenates it with its group count in one step
  // (app.js endDraw/commitActiveStroke), so the two can never disagree. Flip
  // pushes into the shared array and counts alongside it, which is what makes
  // the guard load-bearing here and unnecessary there.
  if(drawing && e.pointerId !== strokePointerId) return;
  e.preventDefault(); disarmAll();
  if(reposMode && bgImage && photoEnabled && photoFit==='cover'){       // pan the image, don't draw
    reposActive=true; reposStart={x:e.clientX,y:e.clientY,ox:photoOffX,oy:photoOffY};
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ } return; }
  if(picking){ sampleColorAt(e); return; }   // eyedropper: pick, don't draw
  // Move mode intercepts BEFORE drawing, or dragging the artwork would lay a
  // stroke down the middle of it.
  if(moveMode){
    moveDragging = true;
    moveStart = { x:e.clientX, y:e.clientY, dx:moveDx, dy:moveDy };
    const st = document.querySelector('.flip-stage'); if(st) st.classList.add('dragging');
    pad.style.cursor = 'grabbing';
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    return;
  }
  // Select intercepts BEFORE drawing, the same place moveMode does and for the
  // same reason: dragging a selection must not also lay a stroke through it.
  if(flipTool === 'select'){
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    selecting = true; selPointerId = e.pointerId;
    selDown(pos(e));
    return;
  }
  try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
  drawing=true; strokePointerId=e.pointerId; curCount=1; redoStack.length=0; noteAction('stroke');
  // A stroke belongs to the page it STARTED on. Every later step used frame(),
  // which re-reads the current index — so changing page mid-stroke (tapping a
  // thumbnail, the pagebar, or holding an arrow to riffle) pushed the remaining
  // points and the group count onto whichever page had become current. The
  // result was one page with points and no group and another with a group and
  // no points, which the server rejects on share:
  //   'frames[0].strokeGroups' accounts for 0 points, but the strokes array
  //   contains 3.
  // Reported from the live demo on a phone; reproduced as 4 points / 0 groups.
  strokeFrame = frame();
  const p=pos(e); smoothPt={x:p.x,y:p.y}; lastRaw={x:p.x,y:p.y};
  if(flipTool==='shape'){
    // No first point and no group yet: a shape commits as one run on release,
    // so curCount stays 0 until then and endStroke pushes the real count.
    _shapeAnchor={x:p.x,y:p.y}; _shapePrev=null; curCount=0; render(); return;
  }
  _brushLastPt = null;
  const dsize = _brushWidth(sizeFor(e, _eraserSize(size, erasing)), p, erasing); const pcol = erasing ? color : penColorFor(color);
  _brushLastPt = {x:p.x, y:p.y};
  strokeFrame.strokes.push({ x:p.x, y:p.y, color: pcol, size: dsize, t: performance.now(), erase: erasing, start: true });
  render(); });
pad.addEventListener('pointermove', e=>{
  if(pinching){ return; }
  if(selecting){ if(e.pointerId === selPointerId) selMove(pos(e)); return; }
  if(moveDragging && moveStart){
    e.preventDefault();
    // Screen pixels -> canvas units, so a drag tracks the pointer exactly at
    // any zoom or display scale. Using raw clientX would move the drawing
    // faster or slower than the finger whenever the canvas is not 1:1.
    const r = pad.getBoundingClientRect();
    moveDx = moveStart.dx + (e.clientX - moveStart.x) * (CW / r.width);
    moveDy = moveStart.dy + (e.clientY - moveStart.y) * (CH / r.height);
    applyMoveOffset();
    return;
  }
  if(reposActive){ e.preventDefault(); const r=pad.getBoundingClientRect();
    photoOffX=Math.max(0,Math.min(1, reposStart.ox - (e.clientX-reposStart.x)/r.width));
    photoOffY=Math.max(0,Math.min(1, reposStart.oy - (e.clientY-reposStart.y)/r.height));
    render(); return; }
  if(!drawing) return; e.preventDefault();
  const raw=pos(e); lastRaw={x:raw.x,y:raw.y};
  let px, py;
  if(smoothingAlpha>=1 || erasing){ px=raw.x; py=raw.y; }         // no stabilizer (off, or erasing stays precise)
  if(flipTool==='shape'){
    _constrainActive = !!(e && e.shiftKey);
    _shapePrev = {a:_shapeAnchor, b:{x:raw.x,y:raw.y}, sq:_constrainActive};
    render(); return;
  }
  else { smoothPt={x: smoothPt.x+(raw.x-smoothPt.x)*smoothingAlpha, y: smoothPt.y+(raw.y-smoothPt.y)*smoothingAlpha}; px=smoothPt.x; py=smoothPt.y; }
  // Shift-to-constrain — same shared helper and same stroke-start anchor as Pad.
  _constrainActive = !!(e && e.shiftKey);
  if(_constrainActive && typeof SkriblConstrain !== 'undefined'){
    const _sf = (strokeFrame || frame()).strokes, _a = _sf.length ? _sf[_sf.length - curCount] : null;
    if(_a){ const _c = SkriblConstrain.apply(_a, {x:px,y:py}, true); px=_c.x; py=_c.y; }
  }
  curCount++; const dsize = _brushWidth(sizeFor(e, _eraserSize(size, erasing)), {x:px,y:py}, erasing); const pcol = erasing ? color : penColorFor(color); _brushLastPt = {x:px, y:py};
  (strokeFrame || frame()).strokes.push({ x:px, y:py, color: pcol, size: dsize, t: performance.now(), erase: erasing });
  render(); });
function endStroke(){
  invalidateClearUndo();   // review #4: new work invalidates a pending clear-undo
  if(reposActive){ reposActive=false; refreshAllThumbs(); scheduleSave(); return; }
  if(!drawing) return;
  // Settle: with smoothing on, the drawn point lags the finger — walk it to the real
  // release point so the stroke actually ends where the pen lifted.
  if(smoothingAlpha<1 && !erasing && smoothPt && lastRaw){
    // Carry the last captured width into the settle points. This read `size`,
    // the nominal slider value, which was invisible at constant width but with
    // pressure would snap the final few points back to full thickness — a blob
    // on the end of every tapered stroke.
    const _pts=(strokeFrame || frame()).strokes, _last=_pts.length ? _pts[_pts.length-1] : null;
    const dsize=(_last && typeof _last.size==='number') ? _last.size : size, pcol=penColorFor(color);
    for(let k=0;k<6;k++){ smoothPt={x: smoothPt.x+(lastRaw.x-smoothPt.x)*0.5, y: smoothPt.y+(lastRaw.y-smoothPt.y)*0.5};
      curCount++; (strokeFrame || frame()).strokes.push({ x:smoothPt.x, y:smoothPt.y, color:pcol, size:dsize, t:performance.now(), erase:false }); }
    render();
  }
  if(flipTool==='shape'){
    const tgt = strokeFrame || frame();
    const pts = (_shapeAnchor && _shapePrev && typeof SkriblShapes !== 'undefined')
      ? SkriblShapes.points(shapeKind, _shapeAnchor, _shapePrev.b, {square:_shapePrev.sq}) : [];
    if(pts.length > 1){
      const pcol = penColorFor(color), now = performance.now();
      for(let i=0;i<pts.length;i++) tgt.strokes.push({ x:pts[i].x, y:pts[i].y, color:pcol,
        size:size, t:now + i, erase:false, start:i===0 });
      curCount = pts.length;
    }
    _shapePrev=null; _shapeAnchor=null;
  }
  drawing=false; smoothPt=null; lastRaw=null;
  const _tgt = (strokeFrame || frame());
  _tgt.strokeGroups.push(curCount);
  // Mirrored copies, one GROUP each — never appended to the original, or the
  // replay joins the two halves with a line straight across the canvas. Flip
  // also validates that strokeGroups accounts for every point on share, so a
  // reflection that skipped its group entry would be refused outright.
  if(curCount > 0 && window.SkriblMirror && SkriblMirror.active()){
    const _src = _tgt.strokes.slice(_tgt.strokes.length - curCount);
    const _n = SkriblMirror.count();
    for(let r=0;r<_n;r++){
      for(let i=0;i<_src.length;i++){
        const m = SkriblMirror.reflect(_src[i], CW, CH)[r];
        _tgt.strokes.push(Object.assign({}, _src[i], {x:m.x, y:m.y}));
      }
      _tgt.strokeGroups.push(_src.length);
    }
    render();
  }
  curCount=0; strokeFrame=null; strokePointerId=null;
  refreshThumb(idx); updateToolState(); scheduleSave(); }
function endMoveDrag(){
  if(!moveDragging) return;
  moveDragging = false;
  const st = document.querySelector('.flip-stage'); if(st) st.classList.remove('dragging');
  if(moveMode) pad.style.cursor = 'grab';
  // Thumbs update on release, not on every pointer event: repainting 62 of
  // them per frame of a drag is what makes a move feel heavy.
  moveTargets().forEach(i=>refreshThumb(i));
}
window.addEventListener('pointerup', endMoveDrag);
window.addEventListener('pointercancel', endMoveDrag);
window.addEventListener('pointerup', endStroke);
window.addEventListener('pointercancel', endStroke);
// On window, not on the pad: releasing outside the canvas has to finish the
// drag, or the selection stays glued to the pointer. Same reason endStroke and
// endMoveDrag are bound here.
function endSelDrag(e){
  if(!selecting) return;
  if(e && e.pointerId != null && e.pointerId !== selPointerId) return;
  selecting = false; selPointerId = null;
  selUp(e ? pos(e) : { x:0, y:0 });
  selMode = null;
}
window.addEventListener('pointerup', endSelDrag);
window.addEventListener('pointercancel', endSelDrag);

/* Custom canvas cursors (pad-style). Eraser = a ring at the 3x footprint; pen = a
   ring at the brush footprint with a little crosshair. One handler swaps them; both
   hide while playing or while the eyedropper is active (which uses the OS crosshair). */
const eraserCursor = document.createElement('div');
eraserCursor.className = 'flip-eraser-cursor';
document.querySelector('.flip-wrap').appendChild(eraserCursor);
const brushCursor = document.createElement('div');
brushCursor.className = 'flip-brush-cursor';
document.querySelector('.flip-wrap').appendChild(brushCursor);
/* The brush/eraser ring trailed the ink on a phone, badly enough that a fast
 * scribble showed the ring lagging behind the line it was supposedly marking.
 * Three causes, all in here, all fixed:
 *
 *  1. IT RAN ON TOUCH. pointermove fires for touch too, so a DOM ring chased a
 *     finger that was already on the glass. It marks where the brush WILL land,
 *     which is information a mouse user needs and a finger user already has by
 *     looking at their hand — and being DOM, it can only ever arrive after the
 *     ink. Now mouse (and pen) only.
 *  2. left/top ON EVERY MOVE. Those are layout-and-paint properties, so the
 *     ring could not be composited independently of the canvas. transform is.
 *  3. getBoundingClientRect() ON EVERY EVENT. A forced synchronous layout read
 *     per pointermove, in the same frame as the stroke draw. The rect is now
 *     cached and invalidated on resize/scroll/zoom rather than re-measured
 *     thousands of times a stroke.
 */
let _padRect = null;
function _padRectCached(){
  if(!_padRect) _padRect = pad.getBoundingClientRect();
  return _padRect;
}
function invalidatePadRect(){ _padRect = null; }
window.addEventListener('resize', invalidatePadRect);
window.addEventListener('scroll', invalidatePadRect, true);
window.addEventListener('orientationchange', invalidatePadRect);

// Eraser width: the pen size times a shared multiplier (lib/erasersize.js).
// This 3 used to be written out seven times across the two editors, including
// in the two eraser-CURSOR sites, where a drifted copy would leave the ring
// lying about how much it erases. Fall back to the shipped 3 so a surface that
// somehow loads without the lib erases exactly as it always did.
function _eraserSize(size, erase) {
  return (typeof SkriblEraser !== 'undefined' && SkriblEraser)
    ? SkriblEraser.sizeFor(size, erase)
    : (erase ? size * 3 : size);
}

function moveEraserCursor(e){
  const r = _padRectCached();
  const sz = _eraserSize(size, true) * (r.width / CW);
  eraserCursor.style.width = sz + 'px'; eraserCursor.style.height = sz + 'px';
  eraserCursor.style.transform =
    'translate3d(' + (e.clientX - r.left) + 'px,' + (e.clientY - r.top) + 'px,0) translate(-50%,-50%)';
  eraserCursor.style.display = 'block';
}
function moveBrushCursor(e){
  const r = _padRectCached();
  const sz = Math.max(2, size * (r.width / CW));
  brushCursor.style.width = sz + 'px'; brushCursor.style.height = sz + 'px';
  brushCursor.style.transform =
    'translate3d(' + (e.clientX - r.left) + 'px,' + (e.clientY - r.top) + 'px,0) translate(-50%,-50%)';
  brushCursor.style.display = 'block';
}
function hideCursors(){ eraserCursor.style.display='none'; brushCursor.style.display='none'; }
pad.addEventListener('pointermove', e=>{
  // A finger is its own cursor. Anything but a mouse or pen gets nothing.
  if(e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'pen'){
    hideCursors(); return;
  }
  if(playing || picking){ hideCursors(); return; }
  if(ZoomView && ZoomView.isZoomed()){ hideCursors(); return; }   // use a normal cursor while magnified
  if(erasing){ moveEraserCursor(e); brushCursor.style.display='none'; }
  else { moveBrushCursor(e); eraserCursor.style.display='none'; }
});
pad.addEventListener('pointerleave', hideCursors);

/* ---- canvas magnify: pinch-zoom + two-finger pan + a small HUD (ported from the
   Pad). Only #zoomLayer is CSS-transformed, so pos()'s getBoundingClientRect math
   keeps mapping touches correctly. Drawing is suspended during a pinch. ---- */
function abortStrokeForPinch(){
  if(reposActive){ reposActive=false; return; }
  if(!drawing) return;
  const s=(strokeFrame || frame()).strokes;
  if(curCount>0 && s.length>=curCount) s.splice(s.length-curCount, curCount);
  drawing=false; curCount=0; smoothPt=null; lastRaw=null; strokeFrame=null; strokePointerId=null; render();
}
/* eventPoint / pinch helpers: lib/eventpoint.js, one implementation shared with
   Pad and the player. Written out here once and rejected by verify_surfaces.py,
   which counts names defined in both app.js and flip.js — correctly, since this
   one reads nothing but its argument. */
function _touchDist(a,b){ return Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY); }
function _touchMid(a,b){ const r=document.querySelector('.flip-wrap').getBoundingClientRect();
  return { x:(a.clientX+b.clientX)/2 - r.left, y:(a.clientY+b.clientY)/2 - r.top }; }
function beginPinch(e){
  if(playing || reposMode || !ZoomView) return;
  if(ZoomView.enabled && !ZoomView.enabled()) ZoomView.enable();   // pinch turns the magnifier on
  // The pinch's two fingers are the ones on the CANVAS, not the first two on
  // the screen, and it remembers WHICH two: _pinchMove is bound to window and
  // reads the screen-wide list, so a third contact could otherwise take a slot
  // and the gesture would be computed from a pair including a finger standing
  // still. Same fix as app.js's beginPinch.
  const own = SkriblPinch.own(e);
  if(!own || own.length<2) return;
  if(e.cancelable) e.preventDefault();
  abortStrokeForPinch(); pinching=true;
  const t0=own[0], t1=own[1];
  _pinch={ ids:[t0.identifier,t1.identifier], lastDist:_touchDist(t0,t1), lastMid:_touchMid(t0,t1) };
}
function _pinchMove(e){
  if(!pinching || !_pinch || !ZoomView) return;
  const pair=SkriblPinch.pair(e, _pinch && _pinch.ids);
  if(!pair) return;
  if(e.cancelable) e.preventDefault();
  const t0=pair[0], t1=pair[1];
  const dist=_touchDist(t0,t1), mid=_touchMid(t0,t1);
  if(_pinch.lastDist>0) ZoomView.zoomAt(dist/_pinch.lastDist, mid.x, mid.y);
  ZoomView.panBy(mid.x-_pinch.lastMid.x, mid.y-_pinch.lastMid.y);
  _pinch.lastDist=dist; _pinch.lastMid=mid;
}
// Ends when either of ITS OWN fingers lifts, not when the screen drops below
// two contacts — an unrelated resting finger must not keep the pinch alive.
function _pinchEnd(e){ if(!pinching) return; if(SkriblPinch.pair(e, _pinch && _pinch.ids)) return; pinching=false; _pinch=null; }
// targetTouches: two fingers ON THE PAD is a pinch; a finger resting elsewhere
// on the page plus one on the pad is a stroke.
pad.addEventListener('touchstart', e=>{ const t=e.targetTouches||e.touches; if(t && t.length>=2) beginPinch(e); }, {passive:false});
window.addEventListener('touchmove', _pinchMove, {passive:false});
window.addEventListener('touchend', _pinchEnd);
window.addEventListener('touchcancel', _pinchEnd);

(function initCanvasZoom(){
  const layer=document.getElementById('zoomLayer'), hud=document.getElementById('zoomHud'), flipWrap=document.querySelector('.flip-wrap');
  if(!layer || !hud || !flipWrap) return;
  const MIN=1, MAX=4, STEP=0.5; let zoom=1, panX=0, panY=0, magnifyOn=false;
  function wrapSize(){ const r=flipWrap.getBoundingClientRect(); return { w:r.width||1, h:r.height||1 }; }
  function clampPan(){ const {w,h}=wrapSize(); panX=Math.min(0,Math.max(w*(1-zoom),panX)); panY=Math.min(0,Math.max(h*(1-zoom),panY)); if(zoom<=1){panX=0;panY=0;} }
  function paint(animate){ clampPan(); layer.classList.toggle('zoom-anim',!!animate);
    layer.style.transform = zoom===1 ? '' : 'translate('+panX+'px,'+panY+'px) scale('+zoom+')';
    const v=document.getElementById('zoomVal'); if(v && !v.querySelector('input')) v.textContent=Math.round(zoom*100)+'%';
    hud.classList.toggle('zoomed', zoom>1.001);
    const zin=document.getElementById('zoomInBtn'), zout=document.getElementById('zoomOutBtn');
    if(zin) zin.disabled=zoom>=MAX-0.001; if(zout) zout.disabled=zoom<=MIN+0.001;
    pad.style.cursor = zoom>1.001 ? 'crosshair' : '';
    if(animate) setTimeout(()=>layer.classList.remove('zoom-anim'),200);
  }
  ZoomView={
    isZoomed:()=>zoom>1.001, enabled:()=>magnifyOn, enable(){ if(!magnifyOn) setMagnify(true); },
    get:()=>({zoom,panX,panY}),
    zoomAt(factor,cx,cy){ const nz=Math.min(MAX,Math.max(MIN,zoom*factor)); if(nz===zoom) return; const coordX=(cx-panX)/zoom, coordY=(cy-panY)/zoom; panX=cx-coordX*nz; panY=cy-coordY*nz; zoom=nz; paint(false); },
    panBy(dx,dy){ panX+=dx; panY+=dy; paint(false); },
    step(dir){ const {w,h}=wrapSize(); this.zoomAt((Math.min(MAX,Math.max(MIN,zoom+dir*STEP)))/zoom, w/2, h/2); paint(true); },
    fit(){ zoom=1; panX=0; panY=0; paint(true); },
    setPct(pct){ const s=wrapSize(); const target=Math.min(MAX,Math.max(MIN,(pct||0)/100)); this.zoomAt(target/zoom, s.w/2, s.h/2); paint(true); },
    reclamp(){ paint(false); }
  };
  bindEl('zoomInBtn', 'click',()=>ZoomView.step(1));
  bindEl('zoomOutBtn', 'click',()=>ZoomView.step(-1));
  bindEl('zoomFitBtn', 'click',()=>ZoomView.fit());
  const magnifyBtn=document.getElementById('magnifyBtn');
  function setMagnify(on){
    // The button zooms the CENTRE. Aiming it needs scroll or space-drag, which
    // lived only in the help drawer under a separate heading — findable only if
    // you already knew to look. Shown once, the first time magnify is enabled.
    if(on && window.SkriblHints){
      window.SkriblHints.show('magnify-pan',
        'Zoomed in. Scroll — or hold Space and drag — to move to the part you want.');
    }
    magnifyOn=on; hud.hidden=!on; if(magnifyBtn){ magnifyBtn.classList.toggle('active',on); magnifyBtn.setAttribute('aria-pressed', on?'true':'false'); } if(!on) ZoomView.fit(); }
  if(magnifyBtn) magnifyBtn.addEventListener('click',()=>setMagnify(!magnifyOn));
  // click the % to type an exact zoom
  const valEl=document.getElementById('zoomVal'); valEl.title='Click to type a zoom %';
  valEl.addEventListener('click',()=>{ if(valEl.querySelector('input')) return; const cur=Math.round(zoom*100); valEl.textContent='';
    const inp=document.createElement('input'); inp.type='text'; inp.inputMode='numeric'; inp.setAttribute('enterkeyhint','done'); inp.maxLength=4; inp.className='zoom-val-input'; inp.value=String(cur); valEl.appendChild(inp);
    const backdrop=document.createElement('div'); backdrop.className='zoom-edit-backdrop'; flipWrap.appendChild(backdrop); inp.focus(); inp.select(); let done=false;
    function commit(apply){ if(done) return; done=true; if(backdrop.parentNode) backdrop.remove(); const n=apply?parseInt(inp.value,10):NaN; if(!isNaN(n)){ ZoomView.setPct(n); } else { if(inp.parentNode) inp.remove(); paint(false); } }
    backdrop.addEventListener('pointerdown',e=>{ e.preventDefault(); commit(true); });
    inp.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); commit(true); } else if(e.key==='Escape'){ e.preventDefault(); commit(false); } });
    inp.addEventListener('blur',()=>commit(true));
  });
  window.addEventListener('resize',()=>{ if(zoom>1) paint(false); });
  // grip: drag the pill, dock to the nearest corner
  const grip=document.getElementById('zoomGrip'); let snapEl=null, dragging=false, grabDX=0, grabDY=0;
  function corners(){ const r=flipWrap.getBoundingClientRect(); const pw=hud.offsetWidth, ph=hud.offsetHeight, m=12;
    return { tl:{key:'tl',x:m,y:m}, tr:{key:'tr',x:r.width-pw-m,y:m}, bl:{key:'bl',x:m,y:r.height-ph-m}, br:{key:'br',x:r.width-pw-m,y:r.height-ph-m} }; }
  function nearestCorner(x,y){ const c=corners(); let best=null,bd=Infinity; for(const k in c){ const d=Math.hypot(x-c[k].x,y-c[k].y); if(d<bd){bd=d;best=c[k];} } return best; }
  function ptr(ev){ const t=SkriblEventPoint.at(ev); return {x:t.clientX,y:t.clientY}; }
  function gripStart(ev){ ev.preventDefault(); ev.stopPropagation(); const r=hud.getBoundingClientRect(), wrapR=flipWrap.getBoundingClientRect(), p=ptr(ev);
    grabDX=p.x-r.left; grabDY=p.y-r.top; dragging=true; hud.classList.add('dragging');
    hud.style.right='auto'; hud.style.bottom='auto'; hud.style.left=(r.left-wrapR.left)+'px'; hud.style.top=(r.top-wrapR.top)+'px';
    snapEl=document.createElement('div'); snapEl.className='zoom-snap'; snapEl.style.height=hud.offsetHeight+'px'; flipWrap.appendChild(snapEl);
    if(ev.type==='mousedown'){ window.addEventListener('mousemove',gripMove); window.addEventListener('mouseup',gripEnd); }
    else { window.addEventListener('touchmove',gripMove,{passive:false}); window.addEventListener('touchend',gripEnd); window.addEventListener('touchcancel',gripEnd); } }
  function gripMove(ev){ if(!dragging) return; ev.preventDefault(); const wrapR=flipWrap.getBoundingClientRect(), p=ptr(ev);
    let x=Math.max(0,Math.min(wrapR.width-hud.offsetWidth, p.x-wrapR.left-grabDX)), y=Math.max(0,Math.min(wrapR.height-hud.offsetHeight, p.y-wrapR.top-grabDY));
    hud.style.left=x+'px'; hud.style.top=y+'px'; const near=nearestCorner(x,y); if(snapEl){ snapEl.style.left=near.x+'px'; snapEl.style.top=near.y+'px'; } }
  function gripEnd(){ if(!dragging) return; dragging=false; hud.classList.remove('dragging');
    const x=parseFloat(hud.style.left)||0, y=parseFloat(hud.style.top)||0, near=nearestCorner(x,y);
    hud.style.left=''; hud.style.top=''; hud.style.right=''; hud.style.bottom=''; hud.setAttribute('data-corner',near.key);
    if(snapEl){ snapEl.remove(); snapEl=null; }
    window.removeEventListener('mousemove',gripMove); window.removeEventListener('mouseup',gripEnd); window.removeEventListener('touchmove',gripMove); window.removeEventListener('touchend',gripEnd); window.removeEventListener('touchcancel',gripEnd); }
  grip.addEventListener('mousedown',gripStart); grip.addEventListener('touchstart',gripStart,{passive:false});
  // wheel pans while zoomed (Shift → horizontal)
  flipWrap.addEventListener('wheel',(e)=>{ if(zoom<=1) return; e.preventDefault(); let dx=e.deltaX, dy=e.deltaY; if(e.shiftKey && dx===0){ dx=dy; dy=0; } panX-=dx; panY-=dy; paint(false); }, {passive:false});
  // hold Space and drag to grab-pan (desktop)
  let spaceHeld=false, spaceDragging=false, lastX=0, lastY=0;
  // Flip's Space has two owners by DESIGN and they are scoped to be mutually
  // exclusive: not zoomed -> play/stop (registered near the bottom of this
  // file); zoomed -> hold to grab-pan. v211 briefly dropped this scope so
  // Space+drag would stop drawing at 100% too, and verify_keys caught the
  // resulting double registration — correctly: at 100% a Space keydown was
  // then BOTH a play toggle and a pan arm. So the registry split stands, and
  // the draw-suppression (the actual owner-reported bug) lives where it
  // belongs: in the pointerdown stroke start, which refuses while Space is
  // held at ANY zoom. Pan stays a zoomed-only affordance on Flip.
  KeyRegistry.register({surface:'flip', label:'hold to grab-pan the magnified canvas',
    keys:['Space'], scope:()=>ZoomView && ZoomView.isZoomed()});
  window.addEventListener('keydown',(e)=>{ if(e.code==='Space' && !typingTarget(e.target)){ spaceHeld=true; if(ZoomView && ZoomView.isZoomed()){ e.preventDefault(); flipWrap.style.cursor=spaceDragging?'grabbing':'grab'; } } });
  window.addEventListener('keyup',(e)=>{ if(e.code==='Space'){ spaceHeld=false; spaceDragging=false; flipWrap.style.cursor=''; } });
  flipWrap.addEventListener('mousedown',(e)=>{ if(spaceHeld && ZoomView && ZoomView.isZoomed()){ spaceDragging=true; lastX=e.clientX; lastY=e.clientY; flipWrap.style.cursor='grabbing'; e.preventDefault(); e.stopPropagation(); } }, true);
  window._skriblSpaceHeld = () => spaceHeld;
  window.addEventListener('mousemove',(e)=>{ if(!spaceDragging) return; panX+=e.clientX-lastX; panY+=e.clientY-lastY; lastX=e.clientX; lastY=e.clientY; paint(false); });
  window.addEventListener('mouseup',()=>{ if(spaceDragging){ spaceDragging=false; flipWrap.style.cursor=spaceHeld?'grab':''; } });
  paint(false);
})();

/* ---- frame strip ---- */
const strip = document.getElementById('strip');
const DEL_SVG='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
function disarmAll(){
  if(armedDel >= 0){ const prev=strip.children[armedDel]; if(prev){ const pd=prev.querySelector('.del'); if(pd) pd.classList.remove('armed'); } armedDel=-1; }
  if(armedClear){ armedClear=false; const cb=document.getElementById('clear'); if(cb){ cb.classList.remove('armed'); cb.title='Delete all pages (keeps music and background)'; const cl=document.getElementById('clearLabel'); if(cl) cl.textContent='Clear all pages'; } }
}
/* ---- page toolbar (v124) --------------------------------------------------
   Acts on the SELECTED page. syncPagebar() is called from buildStrip(), which
   already runs after every mutation, so there is no second place to keep in
   step. Disabled during playback for the same reason the strip is inert then. */
const pagebar=document.getElementById('pagebar');
const pbWho=document.getElementById('pbWho'), pbLeft=document.getElementById('pbLeft'),
      pbRight=document.getElementById('pbRight'), pbCopy=document.getElementById('pbCopy'),
      pbHold=document.getElementById('pbHold'), pbDel=document.getElementById('pbDel');
// The Pad shows the recorded length beside Play; Flip can state its animation
// length exactly — total hold units over fps. Same badge, same m:ss format.
const flipDurationEl=document.getElementById('flipDuration');
// v128: the Pad counts UP in its badge while playing (editorReplayFrame ->
// formatDuration(elapsed)), then restores the total on stop. Flip showed a static
// total, so during playback there was no sense of progress. Same behaviour here,
// driven by rAF rather than the play timer so the readout is smooth regardless of
// fps and unaffected by per-page holds.
let flipElapsedRAF=null, flipPlayStart=0;
function fmtFlipSecs(secs){
  if(secs < 60) return (secs < 9.95 ? secs.toFixed(1) : Math.round(secs)) + 's';
  const m=Math.floor(secs/60), r=Math.round(secs%60);
  const mm=(r===60)?m+1:m, ss=(r===60)?0:r;
  return mm+':'+String(ss).padStart(2,'0');
}
function flipTotalSecs(){ return totalHoldUnits(0, frames.length-1)/(fps||12); }
function startFlipElapsed(){
  if(!flipDurationEl) return;
  flipPlayStart=performance.now();
  const total=flipTotalSecs();
  const tick=()=>{
    if(!playing){ flipElapsedRAF=null; return; }
    const el=(performance.now()-flipPlayStart)/1000;
    // The animation loops, so wrap rather than pinning at the total — the badge
    // tracks position within the loop, which is what a viewer is watching.
    flipDurationEl.textContent=fmtFlipSecs(total>0 ? (el % total) : el);
    flipElapsedRAF=requestAnimationFrame(tick);
  };
  flipElapsedRAF=requestAnimationFrame(tick);
}
function stopFlipElapsed(){
  if(flipElapsedRAF){ cancelAnimationFrame(flipElapsedRAF); flipElapsedRAF=null; }
  syncFlipDuration();                      // back to the total
}

function syncFlipDuration(){
  if(!flipDurationEl) return;
  if(playing) return;                      // the ticker owns the badge while playing
  // m:ss is the Pad's format because a recording runs for seconds. A flipbook
  // usually does not — 5 pages at 12fps is 0.42s, which m:ss renders as "0:00"
  // and reads as broken. Sub-minute durations show one decimal instead.
  flipDurationEl.textContent = fmtFlipSecs(flipTotalSecs());
  flipDurationEl.title=frames.length+' page'+(frames.length===1?'':'s')+' at '+(fps||12)+' fps';
}

function syncPagebar(){
  if(!pagebar) return;
  const f=frames[idx], n=frames.length;
  if(pbWho) pbWho.textContent='Page '+(idx+1)+(n>1?' / '+n:'');
  if(pbLeft) pbLeft.disabled = playing || idx===0;
  if(pbRight) pbRight.disabled = playing || idx===n-1;
  if(pbCopy) pbCopy.disabled = playing;
  if(pbDel) pbDel.disabled = playing || n<=1;
  if(pbHold){
    pbHold.disabled = playing;
    const ic=pbHold.querySelector('.pb-ic'); if(ic) ic.textContent='\u00d7'+frameHold(f);
    pbHold.classList.toggle('on', frameHold(f)>1);
  }
}
if(pbLeft) pbLeft.addEventListener('click',()=>{ if(pbLeft.disabled) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; } movePage(idx,-1); });
if(pbRight) pbRight.addEventListener('click',()=>{ if(!pbRight.disabled) movePage(idx,1); });
if(pbCopy) pbCopy.addEventListener('click',()=>{ if(pbCopy.disabled) return;
  pageClip=deepCopy(frames[idx]); buildStrip(); chip('Page copied — use ＋ Paste'); });
if(pbHold) pbHold.addEventListener('click',()=>{ if(pbHold.disabled) return;
  invalidateClearUndo(); frames[idx].hold=(frameHold(frames[idx]) % MAX_HOLD)+1;
  buildStrip(); scheduleSave(); });
if(pbDel) pbDel.addEventListener('click',()=>{ if(pbDel.disabled) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; } delFrame(idx); });

function buildStrip(){
  armedDel = -1;
  strip.innerHTML='';
  frames.forEach((f,i)=>{
    const el=document.createElement('div'); el.className='frame'+(i===idx?' on':'');
    el.innerHTML='<div class="num">'+(i+1)+'</div>'
      +'<button class="del" title="Delete frame">'+DEL_SVG+'</button>'
      + (frameHold(f)>1 ? '<div class="holdbadge">\u00d7'+frameHold(f)+'</div>' : '')
      +'<canvas></canvas>';   // per-page controls now live in #pagebar (v124)
    el.addEventListener('pointerdown',ev=>{
      if(playing) return;
      // Speak here, not only in the click handler: a real drag sets
      // _pdragSuppressClick, so the click that would have explained the
      // refusal never fires. Dragging a thumbnail during a move was the
      // one page operation that failed in complete silence.
      if(moveMode){ chip('Finish or cancel the move first'); return; }
      if(frames.length<2) return;
      if(ev.target.closest('.del')) return;
      _pdrag={ i:i, el:el, startX:ev.clientX, lastX:ev.clientX, moved:false, centers:stripTileCenters() };
    });
    el.addEventListener('click',ev=>{
      // moveOrigin is keyed by ARRAY INDEX, so selecting, adding, deleting or
      // reordering a page during a live move makes index i stop identifying
      // the page whose points were captured. commitMove() then recomputes its
      // targets from the CURRENT idx, so the undo record could name a
      // different page set from the one previewed — and a reorder could apply
      // one page's captured coordinates to another page's strokes, which is
      // state corruption rather than a visual glitch. A transform session
      // operates on a stable set of pages; the strip stays visible because it
      // is what makes a move judgeable, but it stops being operable.
      if(playing) return;
      if(moveMode){ chip('Finish or cancel the move first'); return; }
      if(_pdragSuppressClick) return;
      const del = ev.target.closest('.del');
      if(del){
        if(f.strokes.length && armedDel !== i){
          disarmAll();
          armedDel = i; del.classList.add('armed'); del.title='Tap again to delete';
          return;
        }
        delFrame(i); return;
      }
      disarmAll(); go(i);
    });
    strip.appendChild(el); drawThumb(el.querySelector('canvas'), f);
  });
  const col=document.createElement('div'); col.className='addcol';
  // Built here rather than in the template, which is why a template-wide
  // tooltip pass could not reach them. lib/tooltip.js adopts late markup via a
  // MutationObserver, so a title written here is picked up like any other.
  // v207: SVG plus, not the U+FF0B fullwidth '＋' text glyph — that character
  // renders at different weights across fonts/platforms and did not match the
  // SVG icons in the page bar beside it.
  col.innerHTML='<button class="addbtn" id="addcopy" title="Add a page that copies this one, so you can nudge and redraw"><svg class="addbtn-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Duplicate</button>'
    +'<button class="addbtn mini" id="addblank" title="Add an empty page"><svg class="addbtn-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Blank</button>'
    + (pageClip ? '<button class="addbtn mini" id="addpaste"><svg class="addbtn-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Paste</button>' : '');
  strip.appendChild(col);
  col.querySelector('#addcopy').addEventListener('click',()=>{ if(playing) return; if(moveMode){ chip('Finish or cancel the move first'); return; } addFrame(true); });
  col.querySelector('#addblank').addEventListener('click',()=>{ if(playing) return; if(moveMode){ chip('Finish or cancel the move first'); return; } addFrame(false); });
  syncPagebar();
  syncFlipDuration();
  if(typeof syncMoveLabel === 'function') syncMoveLabel();
  const pasteBtn=col.querySelector('#addpaste');
  if(pasteBtn) pasteBtn.addEventListener('click',()=>{
    if(playing || moveMode || !pageClip) return;
    invalidateClearUndo(); redoStack.length=0;
    frames.splice(idx+1,0,deepCopy(pageClip)); idx++;
    buildStrip(); render(); scheduleSave();
  });
  updateToolState();
}
function drawThumb(cv,f){ cv.width=88*DPR; cv.height=62*DPR; cv.style.background='transparent'; const c=cv.getContext('2d');
  c.setTransform(88*DPR/CW,0,0,62*DPR/CH,0,0); c.clearRect(0,0,CW,CH); drawBackdrop(c); paintFrame(c, f.strokes); }
function refreshAllThumbs(){ [...strip.children].forEach((el,i)=>{ const cv=el.querySelector('canvas'); if(cv && frames[i]) drawThumb(cv, frames[i]); }); }
function refreshThumb(i){ const el=strip.children[i]; if(el) drawThumb(el.querySelector('canvas'),frames[i]); }
// Reorder by one slot. Keeps `idx` pointing at the SAME page the user was on —
// moving a page must never silently switch which page you're drawing on.
function movePage(i,dir){
  // Below 560px the pagebar labels are hidden, so Move is two bare arrows in a
  // row that also reads "Page 62 / 64" — they look like page navigation while
  // they actually REORDER the animation. A glyph was tried and reverted: a page
  // rectangle at 11px renders as a zero. Saying it once, at the moment it
  // happens, is what a hint is for — and it names the pages so the effect is
  // legible even if you were not watching the strip.
  if(window.SkriblHints){
    const to = i + dir + 1;
    window.SkriblHints.show('page-move',
      'Moved this page to position ' + to + '. These arrows REORDER pages — '
      + 'tap a thumbnail below to change which page you are on.');
  }
  movePageTo(i, i+dir);
}
// Shared by the move buttons and by drag-to-reorder. Keeps `idx` on the SAME page
// the user was on rather than the same slot — reordering must never silently
// switch which page you're drawing on.
function movePageTo(i,j){
  if(moveMode) return;              // see the note in buildStrip's click handler
  if(i===j) return;
  if(j<0 || j>=frames.length) return;
  invalidateClearUndo(); redoStack.length=0;
  const was=frames[idx];
  const moved=frames.splice(i,1)[0];
  frames.splice(j,0,moved);
  const found=frames.indexOf(was);
  if(found>=0) idx=found;
  buildStrip(); render(); scheduleSave();
}

/* ---- drag-to-reorder ------------------------------------------------------
   Pointer-based so it works with touch and pen, not just mouse. The strip is
   NOT rebuilt mid-drag: rebuilding would destroy the element under the pointer
   and drop the gesture, so the tile is translated visually and the actual
   reorder happens once on release. A small threshold keeps ordinary taps
   (select page) working. */
let _pdrag=null, _pdragSuppressClick=false;
function stripTileCenters(){
  return [...strip.querySelectorAll('.frame')].map(el=>{
    const r=el.getBoundingClientRect(); return r.left + r.width/2;
  });
}
document.addEventListener('pointermove', ev=>{
  if(!_pdrag) return;
  const dx=ev.clientX-_pdrag.startX;
  if(!_pdrag.moved && Math.abs(dx)<6) return;
  if(!_pdrag.moved){ _pdrag.moved=true; _pdrag.el.classList.add('dragging'); }
  ev.preventDefault();
  _pdrag.el.style.transform='translateX('+dx+'px)';
});
document.addEventListener('pointerup', ()=>{
  if(!_pdrag) return;
  const d=_pdrag; _pdrag=null;
  d.el.style.transform=''; d.el.classList.remove('dragging');
  if(!d.moved) return;
  _pdragSuppressClick=true;              // don't also "select" the tile we dropped
  setTimeout(()=>{ _pdragSuppressClick=false; }, 0);
  // Insertion index = how many tile centres sit left of the pointer. Then step
  // back one if we're inserting after our own old slot, because movePageTo
  // splices the dragged page OUT before it splices it back in.
  const centers=d.centers, x=d.lastX;
  let target=0;
  for(let k=0;k<centers.length;k++){ if(x>centers[k]) target=k+1; }
  if(target>d.i) target--;
  target=Math.max(0, Math.min(frames.length-1, target));
  movePageTo(d.i, target);
});
document.addEventListener('pointermove', ev=>{ if(_pdrag) _pdrag.lastX=ev.clientX; });
document.addEventListener('pointercancel', ()=>{
  if(!_pdrag) return;
  _pdrag.el.style.transform=''; _pdrag.el.classList.remove('dragging'); _pdrag=null;
});
function deepCopy(f){ const b = balancedPair(f);
  return { strokes: b.strokes.map(p=>Object.assign({},p)), strokeGroups: b.strokeGroups, hold: frameHold(f) }; }
// buildStrip() rebuilds the strip's children, which resets its scrollLeft to 0.
// Any path that rebuilds while idx is non-zero therefore leaves the active page
// highlighted off-screen with the strip parked at page 1 — most visibly after a
// refresh, where a restored 62-page animation opened on page 62 with the strip
// showing page 1. addFrame() was the only caller that scrolled, so the fix
// existed but was never shared.
function scrollStripToActive(smooth){
  const el=strip.children[idx];
  if(!el) return;
  try{ el.scrollIntoView({behavior: smooth?'smooth':'auto', inline:'center', block:'nearest'}); }
  catch(_){ el.scrollIntoView(); }
}
function addFrame(copy){ if(moveMode) return; disarmAll(); invalidateClearUndo(); redoStack.length=0; const f=copy?deepCopy(frame()):newFrame(); frames.splice(idx+1,0,f); idx++; buildStrip(); render(); scheduleSave();
  scrollStripToActive(true); }
function delFrame(i){ if(moveMode) return; invalidateClearUndo(); redoStack.length=0; if(frames.length===1){ frames[0]=newFrame(); idx=0; }
  else { frames.splice(i,1); if(idx>=frames.length) idx=frames.length-1; else if(i<idx) idx--; }
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true); }
function go(i){ if(moveMode) return;
  // A selection is a set of INDEX RANGES into one page's strokes array. Carrying
  // it to another page would point those ranges at different artwork — the
  // frame would move strokes the marquee never touched, and on a shorter page
  // the ranges would run off the end.
  if(typeof selClear === 'function') selClear(true);
  idx=i; redoStack.length=0; buildStrip(); render(); }

/* ---- Instant flip scrub -------------------------------------------------
 * Hold a left/right key and the pages flip past like a thumb riffling paper.
 * This is the whole metaphor of the app, so it has to feel physical: fast,
 * continuous, and stoppable exactly where your eye says stop.
 *
 * It cannot go through go(). buildStrip() destroys and rebuilds every tile in
 * the strip, each with its own <canvas> and listeners, and redraws every
 * thumbnail — fine for a click, ruinous sixteen times a second, and it would
 * also throw away the thumbnails it just drew. goFast() moves the selection
 * and repaints the pad only; the strip is rebuilt ONCE when the key comes up.
 *
 * Browser key-repeat is not usable for this: the first repeat lags ~500ms and
 * the rate is an OS setting, so the same hold flips at different speeds on
 * different machines. The timer below is ours, so the feel is ours.
 */
const FLIP_HOLD_DELAY = 240;   // ms before a hold becomes a riffle
const FLIP_HOLD_STEP  = 62;    // ms between pages while held (~16/sec)
let _flipHoldT = null, _flipHoldDir = 0, _flipHoldMoved = false;

function markStripActive(){
  const tiles = strip.children;
  for(let i=0;i<tiles.length;i++){
    if(tiles[i].classList) tiles[i].classList.toggle('on', i===idx);
  }
  const el = tiles[idx];
  // Keep the current page in view, but never scroll the PAGE — 'nearest' on
  // both axes confines it to the strip's own overflow.
  if(el && el.scrollIntoView) el.scrollIntoView({ block:'nearest', inline:'nearest' });
}

function goFast(i){
  if(moveMode) return;
  idx = i;
  // Mirrors go(): navigating clears the redo stack there too. Diverging would
  // mean redo behaved differently depending on how you reached the page.
  redoStack.length = 0;
  markStripActive();
  render();
}

function stepFrame(dir){
  if(moveMode || playing) return false;
  disarmAll();          // leaving a page must cancel its armed delete
  const next = idx + dir;
  if(next < 0 || next > frames.length-1) return false;   // stop at the ends
  goFast(next);
  return true;
}

function startFlipHold(dir){
  if(_flipHoldDir === dir) return;
  endFlipHold(false);
  _flipHoldDir = dir;
  _flipHoldMoved = stepFrame(dir);        // one page immediately: a tap is a step
  _flipHoldT = setTimeout(function riffle(){
    if(!_flipHoldDir) return;
    if(stepFrame(_flipHoldDir)) _flipHoldMoved = true;
    _flipHoldT = setTimeout(riffle, FLIP_HOLD_STEP);
  }, FLIP_HOLD_DELAY);
}

function endFlipHold(rebuild){
  if(_flipHoldT){ clearTimeout(_flipHoldT); _flipHoldT = null; }
  _flipHoldDir = 0;
  if(rebuild !== false && _flipHoldMoved){
    _flipHoldMoved = false;
    buildStrip();      // once, at the end — restores per-tile state and thumbs
  }
}

// Unscoped on purpose: riffling is live whenever Flip is. The single-step
// versions that used to sit in the shortcut block below were unscoped too,
// which is exactly why both fired on one press.
KeyRegistry.register({surface:'flip', label:'hold to riffle pages',
  keys:['ArrowLeft','ArrowRight']});
window.addEventListener('keydown', e=>{
  if(typingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
  const dir = e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0;
  if(!dir) return;
  e.preventDefault();
  startFlipHold(dir);
});
window.addEventListener('keyup', e=>{
  if(e.key === 'ArrowLeft' || e.key === 'ArrowRight') endFlipHold(true);
});
// A hold must not survive the tab losing focus: keyup never arrives, and the
// riffle would keep running against a page nobody is looking at.
window.addEventListener('blur', ()=> endFlipHold(true));

/* ---- flip playback ---- */
const playBtn=document.getElementById('play');
const liveBadge=document.querySelector('.flip-live');
function updateToolState(){
  playBtn.disabled = drawOnMode ? (frames.length<1 || !frame().strokes.length) : frames.length < 2;
  playBtn.title = playBtn.disabled ? (drawOnMode ? 'Draw something to replay' : 'Add a second page to flip') : (drawOnMode ? 'Watch it draw itself' : 'Flip through the pages');
  // v126: hide the whole control until there is something to play, matching the
  // Pad (playWrap.hidden = !recorded). Showing "Flip it · 0:00" on a one-page
  // animation advertises an action that cannot run. Reuses playBtn.disabled
  // rather than restating the condition, so the two can never disagree — but
  // never hide it mid-playback, which would yank the Stop button out from under
  // the user.
  const _pw = document.getElementById('flipPlayWrap');
  if(_pw) _pw.hidden = playBtn.disabled && !playing;
  if(typeof syncFlipDuration==='function') syncFlipDuration();
  const undoB=document.getElementById('undo');
  undoB.disabled = frame().strokeGroups.length === 0
    && !(actionLog.length && typeof actionLog[actionLog.length-1] === 'object');
  undoB.style.opacity = undoB.disabled ? .38 : 1;
  const redoB=document.getElementById('redo');
  redoB.disabled = redoStack.length === 0;
  redoB.style.opacity = redoB.disabled ? .38 : 1;
}
const flipPlayer=document.getElementById('flipPlayer'), flipProgress=document.getElementById('flipProgress'), flipProgressFill=document.getElementById('flipProgressFill');
const drawOnBtn=document.getElementById('drawOnBtn');
let scrubbingFrames=false, playI=0;
function updatePlayProgress(){ if(flipProgressFill && frames.length) flipProgressFill.style.width=(((idx+1)/frames.length)*100)+'%'; }

// --- draw-on replay: reveal each frame's strokes over their recorded timing ---
function renderPartial(f, count){ ctx.clearRect(0,0,CW,CH); drawBackdrop(ctx); paintFrame(ctx, count>=f.strokes.length ? f.strokes : f.strokes.slice(0, Math.max(0,count))); }
function drawOnParams(f){ const p=f.strokes; if(!p.length) return {span:0, dur:Math.max(160,1000/fps), t0:0}; const t0=p[0].t; const span=Math.max(1, p[p.length-1].t - t0); return {span, dur:Math.min(2200, Math.max(320, span)), t0}; }
function startDrawOnFrame(){ dFrameStartPerf=performance.now(); drawOnTick(); }
function drawOnTick(){
  if(!playing || scrubbingFrames) return;
  const f=frames[dFrame]; if(!f){ stop(); return; }
  const {span,dur,t0}=drawOnParams(f);
  const e=performance.now()-dFrameStartPerf;
  if(!f.strokes.length){ renderPartial(f,0); }
  else { const revealMs=(e/dur)*span; let count=0; while(count<f.strokes.length && (f.strokes[count].t - t0)<=revealMs) count++; renderPartial(f, count); }
  liveBadge.textContent='\u270E '+(dFrame+1)+' / '+frames.length;
  if(flipProgressFill && frames.length){ flipProgressFill.style.width=(((dFrame+Math.max(0,Math.min(1,e/dur)))/frames.length)*100)+'%'; }
  if(e>=dur){ renderPartial(f, f.strokes.length); advanceDrawOn(); return; }
  drawOnRAF=requestAnimationFrame(drawOnTick);
}
function advanceDrawOn(){ dFrame=(dFrame+1)%frames.length; idx=dFrame; startDrawOnFrame(); }   // preview loops

function playStep(){ if(scrubbingFrames) return;
  idx=playI%frames.length; render(); updatePlayProgress();
  liveBadge.textContent='\u25B6 '+(idx+1)+' / '+frames.length; playI++;
}
// Was a fixed setInterval. With per-page holds each step has its own delay, so it
// re-schedules itself. playTimer holds a timeout id now — stop() clears both.
function runPlayTimer(){
  clearInterval(playTimer); clearTimeout(playTimer);
  playStep();
  const step = () => {
    playStep();
    playTimer = setTimeout(step, (1000/fps) * frameHold(frames[playI]));
  };
  playTimer = setTimeout(step, (1000/fps) * frameHold(frames[playI]));
}
function play(){
  if(playing) return;
  if(drawOnMode ? (frames.length<1 || !frame().strokes.length) : frames.length<2) return;
  disarmAll(); editIdx = idx;
  if(ZoomView && ZoomView.isZoomed()) ZoomView.fit();       // play at 100% so frames aren't cropped
  playing=true; document.body.classList.add('playing');
  playBtn.classList.add('playing'); playBtn.querySelector('span').textContent='Stop';
  if(flipPlayer){ flipPlayer.hidden=false; requestAnimationFrame(()=>flipPlayer.classList.add('show')); }
  startMusic();
  startFlipElapsed();
  if(drawOnMode){ dFrame=0; idx=0; startDrawOnFrame(); }
  else { playI=idx; runPlayTimer(); }
}
function stop(){
  playing=false; document.body.classList.remove('playing');
  playBtn.classList.remove('playing'); playBtn.querySelector('span').textContent='Flip it';
  clearInterval(playTimer); playTimer=null; if(drawOnRAF) cancelAnimationFrame(drawOnRAF); drawOnRAF=null;
  stopMusic(); scrubbingFrames=false;
  stopFlipElapsed();
  if(flipPlayer){ flipPlayer.classList.remove('show'); flipPlayer.hidden=true; }
  idx = Math.min(editIdx, frames.length-1);
  buildStrip(); render();
}
playBtn.addEventListener('click',()=> playing?stop():play());
drawOnBtn.addEventListener('click',()=>{ if(playing) stop(); drawOnMode=!drawOnMode; drawOnBtn.classList.toggle('on',drawOnMode); drawOnBtn.setAttribute('aria-checked',String(drawOnMode)); updateToolState(); chip(drawOnMode?'Draw-on replay: on':'Draw-on replay: off'); });
// scrub through frames (drag to preview any frame)
function scrubToFrac(frac){ const n=frames.length; if(!n) return; frac=Math.max(0,Math.min(1,frac)); idx=Math.min(n-1, Math.round(frac*(n-1)));
  if(drawOnMode){ dFrame=idx; renderPartial(frames[dFrame], frames[dFrame].strokes.length); dFrameStartPerf=performance.now(); if(flipProgressFill) flipProgressFill.style.width=(((idx+1)/n)*100)+'%'; }
  else { playI=idx; render(); updatePlayProgress(); }
  liveBadge.textContent=(drawOnMode?'\u270E ':'\u25B6 ')+(idx+1)+' / '+n; }
flipProgress.addEventListener('pointerdown',e=>{ scrubbingFrames=true; try{flipProgress.setPointerCapture(e.pointerId);}catch(_){} const r=flipProgress.getBoundingClientRect(); scrubToFrac((e.clientX-r.left)/r.width); });
flipProgress.addEventListener('pointermove',e=>{ if(!scrubbingFrames) return; const r=flipProgress.getBoundingClientRect(); scrubToFrac((e.clientX-r.left)/r.width); });
function endFrameScrub(){ if(!scrubbingFrames) return; scrubbingFrames=false; if(playing && drawOnMode){ dFrameStartPerf=performance.now(); drawOnTick(); } }
flipProgress.addEventListener('pointerup',endFrameScrub);
flipProgress.addEventListener('pointercancel',endFrameScrub);

/* ---- tools: the Pad editor's Draw menu (colors + brush), wired to Flip state ---- */
const colorCurrent=document.getElementById('colorCurrent');
const colorCurrentCore=document.getElementById('colorCurrentCore');
const drawPanel=document.getElementById('drawPanel');   // the shared .tab-panel drawer
const colorGroup=document.getElementById('colorGroup');
const recentRow=document.getElementById('recentRow');
const recentColorsEl=document.getElementById('recentColors');
const customWrap=colorGroup.querySelector('.color-custom-wrap');
const customInput=document.getElementById('customColorInput');
const customBtn=document.getElementById('customColorBtn');
const eyedropperBtn=document.getElementById('eyedropperBtn');
let recentColors=[], picking=false;
try{ const r=JSON.parse(localStorage.getItem('skribl_recent_colors')||'[]'); if(Array.isArray(r)) recentColors=r.filter(c=>/^#[0-9a-f]{6}$/i.test(c)).slice(0,6); }catch(_){ }

function setColor(hex){
  // Shared with Pad via lib/colorselect.js. This used to accept ANY string:
  // an invalid value became the pen colour and the canvas painted with
  // nothing, and '#FF0000' did not match the '#ff0000' swatch. The `!!` note
  // below is now inside the lib, where both editors get it.
  const sel = window.SkriblColorSelect
    && window.SkriblColorSelect.apply(colorGroup, hex);
  if(!sel) return;
  hex = sel.hex;
  color=hex;
  // The ring lives on .color-ring; writing the colour to the BUTTON would sit
  // on top of it as an inline style and paint the spectrum out entirely.
  if (colorCurrentCore) colorCurrentCore.style.background=hex;
  // !! is load-bearing. The custom swatch has no data-color, so this expression
  // was `undefined && ...` -> undefined, and classList.toggle(name, undefined)
  // is treated as NO second argument — which TOGGLES instead of forcing off. So
  // every colour change flipped the custom swatch's highlight, leaving two
  // swatches ringed at once and the wrong one appearing selected.
  setTool('pen');   // picking a colour returns you to the pen, like the Pad
}
/* ---------- v226: the tool shelf and its overflow tray --------------------
   The mechanics live in lib/toolshelf.js and are shared with Pad — see that
   file's header for why the row needed this at all. What stays here is what is
   genuinely Flip's: which tools exist, and how a tool is applied.

   WITH THREE TOOLS NOTHING CHANGES. 3 <= SHELF_MAX, so all three keep their
   cells, the chevron stays hidden and the tray is never built. */
const SHELF_MAX = 3;
const toolMoreBtn = document.getElementById('toolMoreBtn');
const toolTray = document.getElementById('toolTray');
const toolShelf = (typeof window !== 'undefined' && window.SkriblToolShelf)
  ? window.SkriblToolShelf.create({
      group: document.getElementById('toolGroup'),
      moreBtn: toolMoreBtn,
      tray: toolTray,
      shelfMax: SHELF_MAX,
      tools: [
        { id: 'pen',    label: 'Pen',    btn: 'penToolBtn' },
        { id: 'eraser', label: 'Eraser', btn: 'eraserToolBtn' },
        { id: 'shape',  label: 'Shape',  btn: 'shapeToolBtn' },
        // v227. The fourth tool, and the first to arrive through the tray
        // rather than through a fitting exercise: the shelf drops to
        // [most recent][next][chevron] on its own and the row does not move.
        { id: 'select', label: 'Select', btn: 'selectToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              + '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/>'
              + '<path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/>'
              + '<circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/></svg>' },
      ],
      currentTool: () => flipTool,
      slider: document.getElementById('toolSlider'),
      setTool: (id) => setTool(id),
      closeTray: () => { if (_flipDrawerCtl) _flipDrawerCtl.open(null); },
    })
  : null;
window.SkriblFlipTools = toolShelf;

/* Pen / eraser toggle — the Pad's segmented control with the sliding accent pill. */
function activeToolBtn(){
  // Was a three-way ternary over hard-coded ids. Reads the registry now, so a
  // registered tool gets its highlight without touching this function.
  return (toolShelf && toolShelf.btnFor(flipTool)) || document.getElementById('penToolBtn');
}
/* Delegates to lib/toolshelf.js. The body moved there because Pad computed the
   SAME thing, having independently fixed the same two bugs — a two-button
   assumption and a double subtraction of the group's offsetLeft. Kept as a named
   function because six call sites read better than six `toolShelf &&` guards. */
function positionToolSlider(){
  if (toolShelf) toolShelf.placeSlider();
}
// One call at init is not enough on a phone: the bar is often laid out later and
// the pill ends up measured against zero widths. Same treatment Pad got.
(function keepToolSliderPlaced(){
  const grp=document.getElementById('toolGroup');
  if(!grp) return;
  const replace=()=>positionToolSlider();
  if(typeof ResizeObserver!=='undefined') new ResizeObserver(replace).observe(grp);
  window.addEventListener('resize',replace);
  window.addEventListener('orientationchange',replace);
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(replace);
})();
function setTool(t){
  // Was `(t === 'eraser' || t === 'shape') ? t : 'pen'`, which is a hard-coded
  // roster: a registered tool fell through to the pen and the tray looked
  // broken. The registry decides now, and the fallback still lands on the pen,
  // so an unknown id is a no-op rather than an undefined tool.
  flipTool = (toolShelf && toolShelf.has(t)) ? t : 'pen';
  erasing = (flipTool === 'eraser');
  // Leaving Select drops the selection: an invisible selection that a later
  // drag would move is worse than making the user re-pick.
  if(flipTool !== 'select') selClear();
  // Records the MRU, re-syncs the shelf and repaints the tray's pressed state.
  if (toolShelf) toolShelf.noteUse(flipTool);
  const active = activeToolBtn();
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.toggle('active', b === active));
  positionToolSlider();
  pad.style.cursor='none';
  if(typeof eraserCursor!=='undefined' && !erasing) eraserCursor.style.display='none';
  if(typeof brushCursor!=='undefined' && erasing) brushCursor.style.display='none';
  if(picking) setPicking(false);
}
// Shared with Pad via lib/recentcolors.js. closePop() stays here: Flip's
// colour popover sits over the canvas, so leaving it open after a pick would
// cover the drawing. That is layout, and layout is not what gets shared.
let _recent = null;
function _initRecent(){
  if(_recent || !window.SkriblRecentColors) return;
  _recent = window.SkriblRecentColors.create({
    wrap: recentColorsEl,
    row: recentRow,
    onPick: hex => { setColor(hex); closePop(); },
    onChange: list => { recentColors = list; },
  });
}
function addRecent(hex){ _initRecent(); if(_recent) _recent.add(hex); }
function renderRecent(){ _initRecent(); if(_recent) _recent.render(); }
// preset dots — inserted before the static custom picker + eyedropper (Pad order)
COLORS.forEach(col=>{ const b=document.createElement('button'); b.type='button'; b.className='color-dot'; b.style.background=col; b.dataset.color=col;
  if(col==='#000000') b.style.borderColor='#3a4150';
  b.setAttribute('aria-label', col);
  b.addEventListener('click',()=>{ setColor(col); closePop(); }); colorGroup.insertBefore(b, customWrap); });
// custom color picker (static markup)
customInput.addEventListener('input',e=>{ customBtn.style.background=e.target.value; setColor(e.target.value); });
customInput.addEventListener('change',e=>{ addRecent(e.target.value); });

// eyedropper — click to arm, then click the canvas to sample a pixel's colour
// Shared with Pad via lib/eyedropper.js — the arming, the cursor, Escape and
// the one-shot semantics. Reading the pixel stays here: the two surfaces
// genuinely differ on context, DPR and what a transparent pixel means.
let _eyedropper = null;
function _initEyedropper(){
  if(_eyedropper || !window.SkriblEyedropper) return;
  _eyedropper = window.SkriblEyedropper.create({
    button: eyedropperBtn,
    surface: pad,
    idleCursor: 'none',
    onArm: () => hideCursors(),
    onChange: v => { picking = v; },
  });
}
function setPicking(v){ _initEyedropper(); if(_eyedropper){ v ? (!picking && _eyedropper.toggle()) : _eyedropper.disarm(); } }
function sampleColorAt(e){
  // Reads the ARTWORK, never the pad. The pad carries onion skin and motion
  // guides, and sampling those returned colours that exist nowhere in the
  // drawing — a ghost of the previous page, or the guide's own violet.
  try{
    const art = paintArtwork();
    const p=pos(e); const dx=Math.round(p.x*DPR), dy=Math.round(p.y*DPR);
    const d=art.getContext('2d').getImageData(dx,dy,1,1).data;
    const hex = d[3] < 10 ? bgColor
      : '#'+[d[0],d[1],d[2]].map(v=>v.toString(16).padStart(2,'0')).join('');
    setColor(hex); addRecent(hex);
  }catch(_){ }
  setPicking(false); closePop();
}
_initEyedropper();   // the lib binds the button's own click handler

const photoPanel=document.getElementById('photoPanel'), musicPanel=document.getElementById('musicPanel');
const imageBtn=document.getElementById('imageBtn'), musicBtn=document.getElementById('musicBtn');
// The exclusive-open machine is lib/drawers.js (shared with Pad); Flip keeps
// its hooks — eyedropper cancel on draw close, syncMediaUI on media open, the
// two slider re-positioners — and its reveal. The old openPop/closePop/
// openPhoto/openMusic/hidePhoto/hideMusic/closeMediaDrawers octet collapses to
// wrappers so every existing call site reads unchanged.
const _flipDrawerCtl = skriblDrawers({
  panels: {
    draw:  { panel: drawPanel, button: colorCurrent, aria: true,
             onOpen(){ requestAnimationFrame(positionSmoothSeg); },
             onClose(){ if(picking) setPicking(false); } },
    photo: { panel: photoPanel, button: imageBtn, openClass: 'open', aria: true,
             onOpen(){ syncMediaUI(); requestAnimationFrame(positionFitSlider); } },
    music: { panel: musicPanel, button: musicBtn, openClass: 'open', aria: true,
             onOpen(){ syncMediaUI(); } },
    // The tray joins the drawer set so it is mutually exclusive with colour,
    // photo and music — opening it closes them, and vice versa. Rebuilt on
    // every open; see toolShelf.buildTray().
    tools: { panel: toolTray, button: toolMoreBtn, openClass: 'open', aria: true,
             onOpen(){ if(toolShelf){ toolShelf.buildTray(); toolShelf.sync(); } } }
  },
  reveal(open, name){
    if(!open) return;
    // The tray is anchored above the toolbar, not docked below it in flow, so
    // scrolling it into view would drag the canvas off screen to reveal a panel
    // that was already fully visible.
    if(name === 'tools') return;
    // block:'end', not 'nearest'. 'nearest' scrolls the MINIMUM amount, so a
    // drawer that is already partly on screen gets no scroll at all — which on a
    // phone left the colour swatches and the eyedropper permanently sliced by the
    // bottom edge, under Safari's toolbar. 'end' brings the drawer's bottom to
    // the viewport bottom, and the safe-area padding on .flip-drawers keeps it
    // clear of the browser chrome once it gets there.
    requestAnimationFrame(()=>{ try{ open.scrollIntoView({behavior:'smooth', block:'end'}); }catch(_){ open.scrollIntoView(); }
      if(currentAudioBuffer && open===musicPanel) requestZoomWaveformDraw(); });
  }
});
// Only the wrappers with live callers survive the collapse: closePop for the
// swatch/eyedropper pick handlers, hidePhoto/hideMusic for the outside-click
// dismisser below. openPop/openPhoto/openMusic/closeMediaDrawers/refitDrawer
// had no remaining callers once the buttons went through toggle().
function closePop(){ if(_flipDrawerCtl.isOpen('draw')) _flipDrawerCtl.open(null); }
function hidePhoto(){ if(_flipDrawerCtl.isOpen('photo')) _flipDrawerCtl.open(null); }
function hideMusic(){ if(_flipDrawerCtl.isOpen('music')) _flipDrawerCtl.open(null); }
colorCurrent.addEventListener('click',e=>{ e.stopPropagation(); _flipDrawerCtl.toggle('draw'); });
// Guarded deliberately. These were briefly unguarded while image/music were
// merged into one control, and the resulting TypeError at load killed every
// line of flip.js after them. The buttons are back, but the guard stays: a
// null check costs nothing and a missing element should never take down a file.
if (imageBtn) imageBtn.addEventListener('click',e=>{ e.stopPropagation(); _flipDrawerCtl.toggle('photo'); });
if (musicBtn) musicBtn.addEventListener('click',e=>{ e.stopPropagation(); _flipDrawerCtl.toggle('music'); });
if (toolMoreBtn) toolMoreBtn.addEventListener('click',e=>{ e.stopPropagation(); _flipDrawerCtl.toggle('tools'); });
function hideToolTray(){ if(_flipDrawerCtl.isOpen('tools')) _flipDrawerCtl.open(null); }
document.addEventListener('click',e=>{ const t=e.target;
  // The file inputs (#imageInput/#musicInput/#draftInput) live at the PAGE
  // ROOT on Flip, outside the drawer panels (the shared drawer partials omit
  // them for Flip and this template supplies its own). When the OS file dialog
  // returns, the browser can dispatch click/focus on that input — a target
  // that is neither inside the panel nor the button, so this handler read it
  // as "clicked outside" and slammed the drawer shut the instant a file was
  // chosen. Pad never hit this: its inputs sit INSIDE the drawer partial.
  // (v206) Ignore the file inputs here.
  if(t.closest('input[type=file]')) return;
  if(!drawPanel.hidden  && !t.closest('#drawPanel')  && !t.closest('#colorCurrent')) closePop();
  if(!photoPanel.hidden && !t.closest('#photoPanel') && !t.closest('#imageBtn')) hidePhoto();
  if(!musicPanel.hidden && !t.closest('#musicPanel') && !t.closest('#musicBtn')) hideMusic();
  if(toolTray && !toolTray.hidden && !t.closest('#toolTray') && !t.closest('#toolMoreBtn')) hideToolTray();
});
// Escape closes the tray. The drawers below the row are dismissed by tapping
// away from them, which is natural for a docked panel; the tray floats over the
// canvas, so the key that closes every other overlay should close it too.
document.addEventListener('keydown', e => { if(e.key === 'Escape') hideToolTray(); });
// First paint: with three tools this only hides the chevron, which the template
// already ships hidden. It is here so the shelf is correct from the registry
// rather than from the markup happening to agree with it.
if (toolShelf) toolShelf.sync();
renderRecent(); setColor(color);
const sizeEl=document.getElementById('size'), sizeVal=document.getElementById('sizeVal'), brushDot=document.getElementById('brushSizeDot');
function sizeFill(){ const min=+sizeEl.min,max=+sizeEl.max; sizeEl.style.setProperty('--slider-fill', ((sizeEl.value-min)/(max-min)*100)+'%');
  sizeVal.textContent=sizeEl.value+'px';
  const d=Math.min(+sizeEl.value,26); if(brushDot){ brushDot.style.width=d+'px'; brushDot.style.height=d+'px'; } }
sizeEl.addEventListener('input',()=>{ size=+sizeEl.value; sizeFill(); });

/* ---- opacity: rides inside the per-stroke color as rgba() (Pad parity) ---- */
function penColorFor(hex){
  // Brush presets shape opacity here, exactly as on Pad, so every caller that
  // already asks for the pen colour picks the brush up.
  if(window.SkriblBrush && SkriblBrush.name() !== 'pen') return SkriblBrush.colorFor(hex, strokeOpacity);
  if(strokeOpacity>=1) return hex;                 // 100% keeps the plain hex
  const h=(hex||'#ffffff').replace('#',''); const r=parseInt(h.slice(0,2),16),g=parseInt(h.slice(2,4),16),b=parseInt(h.slice(4,6),16);
  return 'rgba('+r+', '+g+', '+b+', '+strokeOpacity+')';
}
const opacitySlider=document.getElementById('opacitySlider'), opacityVal=document.getElementById('opacityVal');
function opacityFill(){ const v=+opacitySlider.value; opacitySlider.style.setProperty('--slider-fill', ((v-10)/90*100)+'%'); opacityVal.textContent=v+'%'; }
opacitySlider.addEventListener('input',()=>{ strokeOpacity=(+opacitySlider.value)/100; opacityFill(); });
opacityFill();

/* ---- background: painted into the canvas backdrop; the eraser reveals it ---- */
const bgGroup=document.getElementById('bgGroup');
const customBgInput=document.getElementById('customBgInput'), customBgBtn=document.getElementById('customBgBtn');
function applyBg(){ pad.style.backgroundColor = bgColor; pad.style.backgroundImage = 'none'; render(); refreshAllThumbs(); }
function setBg(hex, fromCustom){
  if(!/^#[0-9a-f]{6}$/i.test(hex||'')) return;
  bgColor=hex; applyBg();
  let matched=false;
  [...bgGroup.querySelectorAll('.bg-swatch')].forEach(s=>{
    if(s.classList.contains('bg-custom')) return;
    const on = s.dataset.bg && s.dataset.bg.toLowerCase()===hex.toLowerCase();
    s.classList.toggle('active', on); if(on) matched=true;
  });
  customBgBtn.classList.toggle('active', !matched);
  if(fromCustom || !matched){ customBgBtn.style.background=hex; }
  scheduleSave();
}
bgGroup.addEventListener('click',e=>{ const b=e.target.closest('.bg-swatch'); if(!b||b.classList.contains('bg-custom')) return; setBg(b.dataset.bg,false); });
customBgInput.addEventListener('input',e=>{ setBg(e.target.value,true); });

/* ---- smoothing: stabilizer strength baked into the captured points (Pad parity) ---- */
const smoothSeg=document.getElementById('smoothSeg');
// Was a private copy of what lib/segslider.js does. Two implementations of
// one behaviour is how the two surfaces drift, and this was the easy one.
function positionSmoothSeg(){ if (window.SkriblSegSlider) window.SkriblSegSlider.place(smoothSeg); }
// Shared with Pad via lib/smoothing.js. positionSmoothSeg stays injected:
// slider positioning exists three times in this codebase (here, app.js and
// lib/segslider.js) and consolidating it is its own extraction.
if(window.SkriblSmoothing){
  window.SkriblSmoothing.create({
    seg: smoothSeg,
    onChange: a => { smoothingAlpha = a; },
    onRender: () => positionSmoothSeg(),
  });
}
// Eraser width — same shared module, same one copy of the multiplier.
if(window.SkriblEraser){
  window.SkriblEraser.create({
    seg: document.getElementById('eraserSeg'),
  });
}
if(window.SkriblMirror){ window.SkriblMirror.create({
  seg: document.getElementById('mirrorSeg'),
  onChange: () => { if(typeof render === 'function') render(); } }); }
const _flipShapeSeg = document.getElementById('shapeSeg');
if(_flipShapeSeg && window.SkriblShapes){
  _flipShapeSeg.addEventListener('click', e=>{
    const b = e.target.closest('[data-shape]'); if(!b || !_flipShapeSeg.contains(b)) return;
    const k = b.getAttribute('data-shape');
    if(SkriblShapes.KINDS.indexOf(k) === -1) return;
    shapeKind = k;
    _flipShapeSeg.querySelectorAll('[data-shape]').forEach(x=>{
      const on = x===b; x.classList.toggle('on', on); x.classList.toggle('active', on);
      x.setAttribute('aria-pressed', String(on)); });
    setTool('shape');
  });
}
if(window.SkriblBrush){ window.SkriblBrush.create({ seg: document.getElementById('brushSeg') }); }
if(window.SkriblPressure){
  window.SkriblPressure.create({ seg: document.getElementById('pressureSeg') });
}
if(window.SkriblStrokeLayers){
  // Flip composites whole strokes on repaint, so the change is invisible until
  // the frame is redrawn — unlike Pad, where the next stroke shows it.
  window.SkriblStrokeLayers.create({
    btn: document.getElementById('strokeLayersBtn'),
    onChange: () => { if(typeof render === 'function') render(); },
  });
}

/* =====================================================================
   "More" menu: background image, music loop, save/load draft, export.
   One background and one music loop per animation (both stored in the
   draft/autosave so they round-trip). Kept self-contained and lean.
   ===================================================================== */

/* Composite a full frame (backdrop + strokes) onto a CW×CH context — used by both
   PNG and WebM export. Same path as the live canvas and thumbnails. */
function drawFrameTo(c, f){ drawBackdrop(c); paintFrame(c, f.strokes); }

/* ---- background image ---- */
const imageInput=document.getElementById('imageInput');
// The image-selection token has to reach THROUGH the Image load. It guarded
// validation and the FileReader, but stopped there — so once A's reader had
// passed, selecting B and having B's Image finish FIRST left bgImageObj (what
// the canvas draws) as A while bgImage and the serialized payload were B.
// Reproduced with A=40x40 and B=120x120: rendered 40, serialized B. Preview and
// posted content disagreeing is worse than either being wrong, because nothing
// on screen says so.
//
// The callback still runs on a superseded load — callers use it to re-render,
// and skipping it would strand whatever the current image is unpainted. Only
// the ASSIGNMENT is guarded.
function loadBgImageObj(cb){
  if(!bgImage){ bgImageObj=null; if(cb)cb(); return; }
  const _seq=imageSelectionSeq;
  const im=new Image();
  im.onload=()=>{ if(_seq===imageSelectionSeq) bgImageObj=im; if(cb)cb(); };
  im.onerror=()=>{ if(_seq===imageSelectionSeq) bgImageObj=null; if(cb)cb(); };
  im.src=bgImage;
}
function redrawAll(){ render(); refreshAllThumbs(); }
function setBgImage(dataURL){ bgImage=dataURL; photoEnabled=true; photoFit='cover'; photoOpacity=1; photoBlur=0; photoZoom=1; photoOffX=0.5; photoOffY=0.5; reposMode=false;
  // Re-adding a file the autosave had to drop — restore its saved framing rather
  // than the defaults above. (Keeps the newly picked filename, not the old one.)
  if(pendingPhotoMeta){ const m=pendingPhotoMeta;
    if(m.fit) photoFit=localFit(m.fit);   // accepted ANY string before
    if(typeof m.opacity==='number') photoOpacity=m.opacity;
    if(typeof m.blur==='number') photoBlur=m.blur;
    if(typeof m.zoom==='number') photoZoom=m.zoom;
    if(typeof m.offX==='number') photoOffX=m.offX;
    if(typeof m.offY==='number') photoOffY=m.offY;
    photoEnabled = m.enabled!==false;
    pendingPhotoMeta=null; }
  loadBgImageObj(()=>{ redrawAll(); }); syncMediaUI(); scheduleSave(); }
function removeBgImage(){ bgImage=null; bgImageObj=null; imageName=''; reposMode=false; pendingPhotoMeta=null; redrawAll(); syncMediaUI(); scheduleSave(); }
imageInput.addEventListener('change',async e=>{ const file=e.target.files&&e.target.files[0]; e.target.value='';
  const _seq=++imageSelectionSeq; if(!file) return;
  const _de=await skriblDecodeCheckImage(file);
  if(_seq!==imageSelectionSeq) return;            // superseded or removed mid-decode
  if(_de){ chip(_de); return; }
  imageName=file.name||'';
  // Round 10, #2: the token guard used to stop at the decode await, leaving
  // FileReader unguarded — a slower read could still overwrite a newer choice,
  // or restore an image after removal. Carried through every async stage now.
  const r=new FileReader();
  r.onload=()=>{ if(_seq!==imageSelectionSeq) return; setBgImage(String(r.result)); };
  r.onerror=()=>{ if(_seq!==imageSelectionSeq) return; chip('That image could not be read.'); };
  r.readAsDataURL(file); });

/* ---- music loop (Pad's music component: waveform, trim, loop detail) ---- */
const musicInput=document.getElementById('musicInput');
function dataURLToArrayBuffer(u){ const b64=(u||'').split(',')[1]||''; const bin=atob(b64); const n=bin.length; const a=new Uint8Array(n); for(let i=0;i<n;i++) a[i]=bin.charCodeAt(i); return a.buffer; }
// Media may arrive as a base64 data URL (inline storage) or as a plain URL
// (object storage). This was the ONLY place either client cracked a data URL
// open structurally, so it is the only place that had to learn the difference —
// everywhere else assigns the value to a src or fetches it, and both forms work
// there unchanged.
function mediaToArrayBuffer(u){
  if (typeof u === 'string' && u.slice(0,5) === 'data:') {
    return Promise.resolve(dataURLToArrayBuffer(u));
  }
  return fetch(u, { credentials: 'same-origin' }).then(r => {
    if (!r.ok) { throw new Error('media fetch failed: ' + r.status); }
    return r.arrayBuffer();
  });
}
function decodeForWaveform(){
  // Same race as Pad's, and worse here: this writes audioDuration and the trim
  // window as well as the buffer, so a superseded decode landing last rewrote
  // the loop to the OLD track's length. Reproduced with A=3.00s and B=9.00s:
  // after B landed and then A, everything read 3.00s again.
  const _seq = musicSelectionSeq;
  if(!musicData){ currentAudioBuffer=null; return; }
  try{ if(!audioCtx) audioCtx = new (window.AudioContext||window.webkitAudioContext)(); }catch(_){ return; }
  try{
    // v211 (v210 review F2): retained so shareSkribl can await it — see Pad.
    window._skriblDecodePending = mediaToArrayBuffer(musicData).then(ab => audioCtx.decodeAudioData(ab)).then(buf=>{
      if(_seq !== musicSelectionSeq) return;      // superseded while decoding
      currentAudioBuffer=buf; audioDuration=buf.duration;
      // Default the loop to the FIRST 20s, not the whole file (matches the Pad's
      // loadedmetadata handler and the cap every drag handler enforces). Setting
      // audioDuration here was what made updateTrimUI's 20s default unreachable.
      if(trimEnd==null || trimEnd>audioDuration) trimEnd=Math.min(audioDuration, trimStart+MAX_LOOP_SECONDS);
      // Re-adding a track the autosave had to drop — reapply its saved loop.
      if(pendingMusicMeta){ const m=pendingMusicMeta;
        if(typeof m.trimStart==='number') trimStart=Math.max(0, Math.min(m.trimStart, audioDuration));
        if(typeof m.trimEnd==='number')   trimEnd=Math.min(m.trimEnd, audioDuration);
        trimEnd=Math.max(trimStart+0.5, Math.min(trimEnd, audioDuration));
        if(typeof m.crossfadeMs==='number') loopCrossfadeMs=m.crossfadeMs;
        musicEnabled = m.enabled!==false;
        pendingMusicMeta=null;
        if(typeof setCrossfadeUI==='function') setCrossfadeUI(); }
      drawWaveform(buf); requestZoomWaveformDraw(); updateZoomHandles(); updateTrimUI(); syncMusicUI(); syncMediaUI();
    // Only the CURRENT decode clears the shared flag — an older completion
    // clearing it tells shareSkribl (line ~2097 awaits this) that nothing is
    // decoding while a newer decode is still in flight.
    }).catch(()=>{}).finally(()=>{ if(_seq===musicSelectionSeq) window._skriblDecodePending=null; });
  }catch(_){}
}
function ensureAudio(){
  if(musicData && !audioEl){
    audioEl=new Audio(musicData); audioEl.loop=false;
    audioEl.addEventListener('loadedmetadata',()=>{ if(!audioDuration && isFinite(audioEl.duration)) audioDuration=audioEl.duration;
      if(trimEnd==null || trimEnd>audioDuration) trimEnd=Math.min(audioDuration, trimStart+MAX_LOOP_SECONDS); updateTrimUI(); syncMusicUI(); });
    audioEl.addEventListener('timeupdate',()=>{ const end=trimEnd!=null?trimEnd:audioDuration;
      if(end && audioEl.currentTime >= end-0.02){ audioEl.currentTime=trimStart; } });
  }
  if(audioEl) audioEl.muted=musicMuted;
}
function setMusic(dataURL){ musicData=dataURL; if(audioEl){ try{audioEl.pause();}catch(_){}} audioEl=null;
  musicEnabled=true; musicMuted=false; trimStart=0; trimEnd=null; audioDuration=0; loopCrossfadeMs=0; currentAudioBuffer=null;
  zoomMag=1; zoomFocus='loop'; zoomCenter=null;
  ensureAudio(); decodeForWaveform(); syncMediaUI(); scheduleSave(); }
function removeMusic(){ musicSelectionSeq++; if(typeof stopLoopPreview==='function') stopLoopPreview(); if(audioEl){ try{audioEl.pause();}catch(_){}} audioEl=null;
  musicData=null; musicName=''; currentAudioBuffer=null; loopCrossfadeMs=0; pendingMusicMeta=null;
  try{ waveformCtx.clearRect(0,0,waveformCanvas.width,waveformCanvas.height); zoomWaveformCtx.clearRect(0,0,zoomWaveformCanvas.width,zoomWaveformCanvas.height); }catch(_){}
  if(typeof setCrossfadeUI==='function') setCrossfadeUI();
  syncMediaUI(); scheduleSave(); }
function startMusicNative(){ ensureAudio(); if(audioEl){ try{ audioEl.currentTime=trimStart; audioEl.play().catch(()=>{}); }catch(_){}} }
function startMusic(){ if(!musicEnabled || musicMuted) return;
  if(startWebAudioLoop(startMusicNative)) return;               // gapless path; native reachable on async unlock failure
  startMusicNative(); }
function stopMusic(){ stopWebAudioLoop(); if(audioEl){ try{ audioEl.pause(); }catch(_){}} }
musicInput.addEventListener('change',async e=>{ const file=e.target.files&&e.target.files[0]; e.target.value='';
  const _seq=++musicSelectionSeq; if(!file) return;
  const _de=await skriblDecodeCheckAudio(file);
  if(_seq!==musicSelectionSeq) return;            // superseded or removed mid-decode
  if(_de){ chip(_de); return; }
  musicName=file.name||'';
  const r=new FileReader();
  r.onload=()=>{ if(_seq!==musicSelectionSeq) return; setMusic(String(r.result)); };
  r.onerror=()=>{ if(_seq!==musicSelectionSeq) return; chip('That audio could not be read.'); };
  r.readAsDataURL(file); });

/* ---- gapless + crossfaded loop engine (Web Audio, ported from the Pad) --------
   Plays the trimmed [trimStart,trimEnd] region as an AudioBufferSourceNode with
   loop=true — scheduled on the audio hardware clock, so it's sample-accurate and
   never clicks or drifts. With a crossfade set, the loop's tail is equal-power
   folded over its head so the wrap is two originally-adjacent samples (smooth). */
let _waLoopSource=null, _waLoopStartCtx=0, _waLoopDuration=0;
function buildLoopChannels(buffer, startFrame, frames, xfadeFrames) { return window.SkriblAudioLoop.buildLoopChannels(buffer, startFrame, frames, xfadeFrames); }
function buildLoopAudioBuffer() { return window.SkriblAudioLoop.buildLoopAudioBuffer({ currentAudioBuffer: currentAudioBuffer, audioCtx: audioCtx, trimStart: trimStart, trimEnd: trimEnd, loopCrossfadeMs: loopCrossfadeMs }); }
// Crop to the loop for posting (same encoder the Pad uses). Post-only — the
// draft keeps the full sample so the loop can still be re-trimmed.
function buildTrimmedLoopWav() { return window.SkriblAudioLoop.buildTrimmedLoopWav({ currentAudioBuffer: currentAudioBuffer, trimStart: trimStart, trimEnd: trimEnd, loopCrossfadeMs: loopCrossfadeMs }); }
// v211 (v210 review F1): Flip kept the PRE-FIX shape Pad moved away from —
// fire-and-forget resume(), then construct and start a source on a context
// that may still be suspended, and return true, which suppressed the callers'
// native <audio> fallback. A source object existing is not proof of sound;
// this exact class is what silenced shared links on the owner's iPhone. Same
// contract as Pad now: no source is constructed until the context reports
// 'running'; a generation counter stops a late start after Stop; and when
// the unlock rejects, never settles (iOS leaves resume() pending), or lands
// on a context that still isn't running, `onFail` fires so the caller can
// hand off to native <audio> ASYNCHRONOUSLY. Returns true meaning "the Web
// Audio path was taken and will either play or call onFail" — never "sound".
let _waGen=0;
function stopWebAudioLoop(){ _waGen++; if(_waLoopSource){ try{_waLoopSource.stop();}catch(e){} try{_waLoopSource.disconnect();}catch(e){} _waLoopSource=null; } }
function startWebAudioLoop(onFail){
  if(!audioCtx || !currentAudioBuffer) return false;
  const buf=buildLoopAudioBuffer(); if(!buf) return false;
  stopWebAudioLoop();
  const gen=++_waGen;
  const go=()=>{
    if(gen!==_waGen || !audioCtx || audioCtx.state!=='running') return false;
    const src=audioCtx.createBufferSource(); src.buffer=buf; src.loop=true; src.loopStart=0; src.loopEnd=buf.duration;
    src.connect(audioCtx.destination);
    try{ src.start(); }catch(e){ return false; }
    _waLoopSource=src; _waLoopStartCtx=audioCtx.currentTime; _waLoopDuration=buf.duration; return true;
  };
  const fail=(why)=>{ if(gen!==_waGen) return; _waGen++; if(onFail){ const f=onFail; onFail=null; console.warn('skribl: web audio unavailable — '+why); f(); } };
  if(audioCtx.state==='running') return go();
  let p=null; try{ p=audioCtx.resume(); }catch(e){ fail('resume threw'); return false; }
  if(p && p.then){
    let settled=false;
    p.then(()=>{ settled=true; if(!go()) fail('context not running after resume'); },
           (e)=>{ settled=true; fail('resume rejected: '+((e&&e.message)||e)); });
    setTimeout(()=>{ if(!settled && !_waLoopSource) fail('resume never settled'); }, 600);
  } else if(!go()){ fail('synchronous resume did not reach running'); return false; }
  return true;
}
// Current playback position inside [trimStart,trimEnd], whichever engine is live.
function loopPosition(){
  if(_waLoopSource && _waLoopDuration>0 && audioCtx){ const e=((audioCtx.currentTime-_waLoopStartCtx)%_waLoopDuration); return trimStart+e; }
  if(audioEl) return audioEl.currentTime;
  return trimStart;
}

/* ---- save / load draft as a .skribl file (same format the Pad reads) ---- */
function saveDraft(){
  const data=serializeFlip();
  const blob=new Blob([JSON.stringify(data)], { type:'application/json' });
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='skribl-flip-'+new Date().toISOString().slice(0,10)+'.skribl';
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
  chip('Draft saved');
}
const draftInput=document.getElementById('draftInput');
function loadDraftFile(file){
  const r=new FileReader();
  r.onload=()=>{ try{
      const d=JSON.parse(String(r.result));
      if(!d || !Array.isArray(d.frames) || !d.frames.length){ chip('Not a valid Skribl'); return; }
      // A Pad .skribl (playbackMode 'replay') shares the {frames} container but
      // is a single-canvas replay, not a flipbook; it loaded here as a lone
      // 1-page 'animation' with no error. Refuse it with directions instead.
      if(d.playbackMode==='replay'){ chip('That\u2019s a Pad Skribl \u2014 open it in Skribl Pad'); return; }
      if(audioEl){ try{audioEl.pause();}catch(_){}} audioEl=null; musicMuted=false;
      // Same reasoning as Pad's loadSkribl generation token: a draft load is a
      // NEW document, so an image or track selected moments earlier must not
      // complete into it. Bumping both sequences invalidates anything in flight.
      //
      // UNPINNED — DEFENCE IN DEPTH, NOT DEMONSTRATED BEHAVIOUR. Removing these
      // two increments reddens nothing in verify_tools: no scenario drives a
      // selection that is still in flight when a draft file is opened. The
      // model is right and this is the second of the two guards v214 shipped
      // without evidence (the other is loadSkribl's deferred writeAutosave
      // guard in app.js). Do not read it as tested, and do not delete it
      // assuming the suite would catch it — it would not.
      const ok=applyPayload(d);            // sets frames/bgColor/bgImage/musicData/fps directly
      invalidateClearUndo();
      loadBgImageObj(()=>{ applyBg(); render(); });
      ensureAudio();
      // DECODE, or a restored draft is not the same thing as a fresh selection.
      // applyPayload() clears currentAudioBuffer, and ensureAudio() only builds
      // the <audio> element — so this path restored musicData and a trim window
      // with no decoded buffer behind them. The boot/autosave path at the
      // bottom of this file has always called decodeForWaveform(); only the
      // draft-FILE path was missing it.
      //
      // The visible half is a blank waveform. The costly half is the post:
      // buildSharePayload() crops to the loop ONLY when currentAudioBuffer
      // exists and otherwise warns and ships the whole sample. Measured on a
      // 30s track trimmed to a 5s loop — 588,082 B posted after a fresh
      // selection against 3,528,082 B after restoring the same draft, both
      // claiming the same 5s loop.
      if (musicData) decodeForWaveform();
      fitPad(); buildStrip(); render(); sizeFill(); setBg(bgColor); syncMediaUI();
      try{ localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeFlip())); }catch(_){ }  // best-effort
      chip(ok?'Draft loaded':'Loaded');
    }catch(err){ chip('Could not read file'); }
  };
  r.readAsText(file);
}
draftInput.addEventListener('change',e=>{ const file=e.target.files&&e.target.files[0]; e.target.value=''; if(file) loadDraftFile(file); });

/* ---- export: PNG (current frame) + WebM (the loop) ---- */
function download(blob, name){ const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href), 4000); }

/* ---- Share: post the Skribl to /api/skribls (the Pad's endpoint) and open the
   real player at /s/<id> — where loop / mute / restart / progress live. The post
   body matches the Pad's frame-format (media on frame 0, one frame per page). ---- */
let sharing=false;
function buildSharePayload(){
  let music0=(musicData && musicEnabled) ? { data:musicData, name:musicName||null, trimStart:trimStart, trimEnd:(trimEnd!=null?trimEnd:audioDuration), crossfadeMs:loopCrossfadeMs } : null;
  // Crop music down to just the loop for posting, exactly as the Pad does — a
  // 42s file trimmed to an 8s loop was posting all 42s. The cropped clip IS the
  // loop, so trimStart/trimEnd become 0..loopLen and crossfadeMs is dropped (the
  // fold is already baked in; re-applying it at playback would double it).
  // Falls back to the full sample if the decoded buffer isn't ready or encoding
  // fails, so a post never breaks here.
  if (music0 && music0.data && !currentAudioBuffer) console.warn('skribl: music not decoded at post time — posting the full sample');
  if (music0 && music0.data && currentAudioBuffer) {
    try {
      const cropped = buildTrimmedLoopWav();
      if (cropped) music0 = { data: cropped.dataUrl, name: music0.name, trimStart: 0, trimEnd: cropped.duration, crossfadeMs: 0 };
    } catch (e) { console.warn('skribl: loop crop failed, posting the full sample', e); }
  }
  const photo0=bgImage ? { data:bgImage, name:imageName||null, fit:(photoFit==='fill'?'stretch':photoFit), opacity:photoOpacity, blur:photoBlur, offset:{x:photoOffX,y:photoOffY}, zoom:photoZoom } : null;
  const outFrames=frames.map((f,i)=>({ strokes:f.strokes, strokeGroups:f.strokeGroups, baseSnapshot:null, background:{color:bgColor}, photo:i===0?photo0:null, music:i===0?music0:null }));
  // Title/caption come from the compose sheet. This was hardcoded to
  // 'Flip animation' with no caption, so every Flip post arrived at the platform
  // with an identical, meaningless title. The server truncates at 80/300 and
  // substitutes 'Untitled Skribl' for an empty title, so sending '' is safe.
  const _t=document.getElementById('flipShareTitle');
  const _c=document.getElementById('flipShareCaption');
  return { version:2, schemaVersion:2, playbackMode: frames.length>1?'flip':'replay', fps:fps, frames:outFrames, canvasSize:{cssWidth:CW,cssHeight:CH,dpr:1},
           title: (_t ? _t.value : '').trim(), caption: (_c ? _c.value : '').trim() };
}
async function shareSkribl(){
  if(sharing) return;
  const empty = frames.length===1 && !frames[0].strokes.length && !bgImage;
  if(empty){ chip('Draw something to share'); return; }
  if(playing) stop();
  sharing=true; chip('Posting…');
  try{
    // Feature-detected: compression must never be able to break posting.
    // See the note at the matching call site in editor_post.js.
    // v211 (v210 review F2): decode is part of post readiness — see Pad's submit().
    if(window._skriblDecodePending){ try{ await window._skriblDecodePending; }catch(_){} }
    const _body=JSON.stringify(buildSharePayload());
    const _p=(typeof skriblPackBody==='function')
      ? await skriblPackBody(_body, skriblPostHeaders())
      : { body:_body, headers:skriblPostHeaders() };
    const res=await fetch(window.SKRIBL_API_BASE,{ method:'POST', headers:_p.headers, body:_p.body });
    let data={}; try{ data=await res.json(); }catch(_){}
    if(!res.ok){
      // 5xx is the server's fault and 4xx is usually the user's; saying which
      // is the difference between "try again" and "change something". A 500
      // here was an unreachable database, and the old transient chip made that
      // look like the button doing nothing.
      const why = data.error || (res.status >= 500
        ? 'The server could not save it (error ' + res.status + '). Your Skribl is safe here — try again in a moment.'
        : 'The server refused it (error ' + res.status + '). Your Skribl is safe here — nothing was lost.');
      showShareError(why); chip('Share failed'); sharing=false; return;
    }
    const url=location.origin + (data.url || (window.SKRIBL_PLAYER_BASE+'/'+data.id));
    // Record it locally. Without accounts the link is the only handle on a
    // post, and closing the tab used to lose it permanently.
    if(window.SkriblPosted){
      const _t=document.getElementById('flipShareTitle');
      window.SkriblPosted.add({ id:data.id, url:data.url, kind:'flip',
        pages:frames.length, title:(_t?_t.value:'').trim() });
      if(window._skriblPostedUI) window._skriblPostedUI.render();
    }
    showShareResult(url);
  }catch(err){
    console.error('[skribl] Share failed:', err);
    showShareError('Could not reach the server. Check your connection — your Skribl is still here.');
    chip('Share failed');
  }
  sharing=false;
}
function showShareError(msg){
  const el=document.getElementById('flipShareError');
  if(el){ el.textContent=msg; el.hidden=false; }
}
function clearShareError(){
  const el=document.getElementById('flipShareError');
  if(el){ el.textContent=''; el.hidden=true; }
}
function showShareResult(url){
  const m=document.getElementById('flipShare'), inp=document.getElementById('flipShareUrl'), open=document.getElementById('flipShareOpen');
  const compose=document.getElementById('flipShareCompose'), result=document.getElementById('flipShareResult');
  if(compose) compose.hidden=true;
  if(result) result.hidden=false;
  if(inp) inp.value=url; if(open) open.href=url; if(m) m.hidden=false;
}

/* ---- compose step ---------------------------------------------------------
   The emptiness check lives HERE, before the sheet opens, so a user is not
   asked for a title and then told there is nothing to share. shareSkribl()
   keeps its own check because it is still reachable directly. ---------------*/
function openShareCompose(){
  // Never fail silently. Every early return below used to leave the user
  // tapping a button that did nothing, with no way to tell whether the app was
  // busy, refusing, or broken.
  if(sharing){ chip('Still posting…'); return; }
  const empty = frames.length===1 && !frames[0].strokes.length && !bgImage;
  if(empty){ chip('Draw something to share'); return; }
  if(playing) stop();
  const m=document.getElementById('flipShare');
  const compose=document.getElementById('flipShareCompose'), result=document.getElementById('flipShareResult');
  if(!m){
    // The sheet is missing entirely. Say so rather than appear dead, and name
    // it in the console so lib/report.js carries it off the device.
    console.error('[skribl] #flipShare is missing — cannot open the share sheet');
    chip('Share is unavailable — please reload');
    return;
  }
  if(compose) compose.hidden=false;
  if(result) result.hidden=true;
  clearShareError();
  m.hidden=false;
  const t=document.getElementById('flipShareTitle');
  if(t) setTimeout(()=>{ try{ t.focus(); }catch(_){ } }, 30);
}
const _shareCap=document.getElementById('flipShareCaption');
const _shareCount=document.getElementById('flipShareCount');
if(_shareCap && _shareCount){
  const _sync=()=>{ _shareCount.textContent=_shareCap.value.length+' / 280'; };
  _shareCap.addEventListener('input', _sync); _sync();
}
const _shareSubmit=document.getElementById('flipShareSubmit');
if(_shareSubmit) _shareSubmit.addEventListener('click', shareSkribl);
const _shareCancel=document.getElementById('flipShareCancel');
if(_shareCancel) _shareCancel.addEventListener('click',()=>{ document.getElementById('flipShare').hidden=true; });
// Enter in the title field submits; the caption is a textarea and keeps newlines.
const _shareTitle=document.getElementById('flipShareTitle');
if(_shareTitle) _shareTitle.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); shareSkribl(); } });

bindEl('flipShareClose', 'click',()=>{ document.getElementById('flipShare').hidden=true; });
bindEl('flipShare', 'click',e=>{ if(e.target.id==='flipShare') e.currentTarget.hidden=true; });
bindEl('flipShareCopy', 'click',async()=>{
  const url=document.getElementById('flipShareUrl').value;
  try{ await navigator.clipboard.writeText(url); chip('Link copied'); }
  catch(_){ const inp=document.getElementById('flipShareUrl'); inp.focus(); inp.select(); try{ document.execCommand('copy'); chip('Link copied'); }catch(e){ chip('Select the link and copy'); } }
});
function exportPNG(){
  const cv=document.createElement('canvas'); cv.width=CW; cv.height=CH; const c=cv.getContext('2d');
  drawFrameTo(c, frame());
  cv.toBlob(b=>{ if(b) download(b, 'skribl-frame-'+(idx+1)+'.png'); }, 'image/png');
}
let exporting=false;
function exportWebM(){
  if(exporting) return;
  if(frames.length<2){ chip('Add a page or two first'); return; }
  if(typeof MediaRecorder==='undefined' || !HTMLCanvasElement.prototype.captureStream){ chip('Video export not supported here'); return; }
  exporting=true; exportShow('Recording WebM…');
  const _d=exDims(), _r=exRange();
  const cv=document.createElement('canvas'); cv.width=_d.w; cv.height=_d.h; const c=cv.getContext('2d');
  // drawFrameTo paints in CW/CH coordinates, so scale the context once rather
  // than touching every draw call.
  c.setTransform(_d.w/CW, 0, 0, _d.h/CH, 0, 0);
  const stream=cv.captureStream(fps);
  const types=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'];
  const mime=types.find(t=>MediaRecorder.isTypeSupported(t))||'video/webm';
  let rec; try{ rec=new MediaRecorder(stream,{mimeType:mime}); }catch(_){ exporting=false; exportHide(); chip('Video export failed'); return; }
  const chunks=[]; rec.ondataavailable=ev=>{ if(ev.data && ev.data.size) chunks.push(ev.data); };
  rec.onstop=()=>{ exporting=false; if(_exportAbort){ exportHide(); chip('Export cancelled'); return; } const blob=new Blob(chunks,{type:'video/webm'}); download(blob,'skribl-animation.webm'); exportSet(1,'Done!'); setTimeout(exportHide,500); chip('Animation exported'); };
  drawFrameTo(c, frames[_r.from-1]); rec.start();
  // Tick in base-fps units, not pages, so a held page simply occupies more ticks.
  const _units=[]; for(let i=_r.from-1;i<=_r.to-1;i++){ for(let k=0;k<frameHold(frames[i]);k++) _units.push(i); }
  const loops=exLoops, total=_units.length*loops; let n=0;   // from the export sheet; see exLoops
  const iv=setInterval(()=>{ if(_exportAbort){ clearInterval(iv); try{rec.stop();}catch(_){ exporting=false; exportHide(); } return; }
    drawFrameTo(c, frames[_units[n%_units.length]]); n++; exportSet(n/total); if(n>=total){ clearInterval(iv); setTimeout(()=>{ try{rec.stop();}catch(_){ exporting=false; exportHide(); } }, Math.ceil(1000/fps)+40); } }, 1000/fps);
}
async function exportGIF(){
  try{ await skriblLoadVendor('gifenc'); }
  catch(e){ chip('GIF encoder didn\u2019t load — check your connection'); return; }
  const G=window.gifenc;
  if(!(G && G.GIFEncoder && G.quantize && G.applyPalette)){ chip('GIF export needs gifenc.min.js'); return; }
  if(exporting) return; if(!frames.length){ chip('Draw something first'); return; }
  exporting=true; exportShow('Rendering GIF…');
  try{
    // Size now comes from the export sheet. Before v108 this was a hardcoded
    // 480px cap with no way out; 'full' is the new default, so a GIF is native
    // resolution unless the user asks for smaller.
    const _d=exDims(); const outW=_d.w, outH=_d.h;
    const r=exRange();
    const full=document.createElement('canvas'); full.width=CW; full.height=CH; const fc=full.getContext('2d');
    const out=document.createElement('canvas'); out.width=outW; out.height=outH; const octx=out.getContext('2d');
    const enc=G.GIFEncoder();
    // GIF stores delay in centiseconds. Rounding ms->cs per frame made a held
    // page drift (3 x 83ms = 249ms -> 25cs, not 24), so quantise to whole
    // centiseconds FIRST and multiply after. Identical output at hold 1.
    const csBase=Math.max(1, Math.round(100/fps)); const delay=csBase*10;
    // GIF background toggle (shared export sheet): 'transparent' keys out the bg
    // for crisp 1-bit-alpha line art; 'color' bakes the pad background as before.
    const transparent=(gifBgMode==='transparent');
    const fmt=transparent?'rgba4444':'rgb565';
    for(let i=r.from-1;i<=r.to-1;i++){
      if(_exportAbort){ exportHide(); chip('Export cancelled'); exporting=false; return; }
      if(transparent){ fc.clearRect(0,0,CW,CH); paintFrame(fc, frames[i].strokes); }  // strokes only, on transparent
      else { drawFrameTo(fc, frames[i]); }
      octx.clearRect(0,0,outW,outH); octx.drawImage(full,0,0,outW,outH);
      const img=octx.getImageData(0,0,outW,outH);
      const palette=G.quantize(img.data,256,{format:fmt, oneBitAlpha:transparent});
      const index=G.applyPalette(img.data,palette,fmt);
      const opts={palette,delay:delay*frameHold(frames[i])}; if(i===r.from-1) opts.repeat=0;   // loop forever
      if(transparent){ let tIdx=palette.findIndex(c=>c.length>3&&c[3]===0); if(tIdx<0) tIdx=0; opts.transparent=true; opts.transparentIndex=tIdx; opts.dispose=2; }
      enc.writeFrame(index,outW,outH,opts);
      exportSet((i-(r.from-1)+1)/r.count);
      if((i&1)===0) await new Promise(r=>setTimeout(r,0));               // yield so the UI stays responsive
    }
    enc.finish();
    download(new Blob([enc.bytes()],{type:'image/gif'}),'skribl-flip.gif');
    exportSet(1,'Done!'); setTimeout(exportHide,500); chip('GIF exported');
  }catch(err){ console.error('GIF export failed:', err); exportHide(); chip('GIF export failed'); }
  exporting=false;
}

/* ---- MP4 export via WebCodecs + mp4-muxer (ported from the Pad). Real H.264/AAC,
   with the trimmed/crossfaded music loop tiled across the clip. Capability-gated:
   returns false (clean) if WebCodecs/muxer/codecs are missing, so exportVideo()
   falls back to the WebM (MediaRecorder) path — never worse than before. ---- */
async function pickAvcCodec(w,h){
  if(typeof VideoEncoder==='undefined' || !VideoEncoder.isConfigSupported) return null;
  for(const c of ['avc1.640028','avc1.4d0028','avc1.42001f','avc1.42e01e']){
    try{ const r=await VideoEncoder.isConfigSupported({codec:c,width:w,height:h,bitrate:6000000,framerate:30}); if(r&&r.supported) return c; }catch(e){}
  }
  return null;
}
async function aacSupported(sr,ch){
  if(typeof AudioEncoder==='undefined' || !AudioEncoder.isConfigSupported) return false;
  try{ const r=await AudioEncoder.isConfigSupported({codec:'mp4a.40.2',sampleRate:sr,numberOfChannels:ch,bitrate:128000}); return !!(r&&r.supported); }catch(e){ return false; }
}
async function exportViaWebCodecsMp4(){
  try{ await skriblLoadVendor('mp4muxer'); }catch(e){ return false; }
  const MM=window.Mp4Muxer;
  if(!(MM && MM.Muxer && MM.ArrayBufferTarget)) return false;
  if(typeof VideoEncoder==='undefined' || typeof VideoFrame==='undefined') return false;
  const _d=exDims(), _r=exRange();
  const w=_d.w&~1, h=_d.h&~1; if(w<2||h<2) return false;   // encoders want even dims
  const avcCodec=await pickAvcCodec(w,h); if(!avcCodec) return false;
  if(frames.length<1) return false;
  // Audio: the trimmed/crossfaded loop from the music engine, if music is on.
  const hasAudio = !!musicData && musicEnabled && !musicMuted && !!currentAudioBuffer;
  let audioBuf=null, useAudio=false;
  if(hasAudio){
    try{ audioBuf = buildLoopAudioBuffer(); if(audioBuf) useAudio = await aacSupported(audioBuf.sampleRate, audioBuf.numberOfChannels); }
    catch(e){ audioBuf=null; useAudio=false; }
    if(!useAudio) return false;   // don't ship a silent MP4 — let WebM keep the audio
  }
  if(exporting) return true; exporting=true; exportShow('Encoding video…');
  try{
    const muxer=new MM.Muxer({ target:new MM.ArrayBufferTarget(),
      video:{codec:'avc',width:w,height:h},
      audio: useAudio ? {codec:'aac',numberOfChannels:audioBuf.numberOfChannels,sampleRate:audioBuf.sampleRate} : undefined,
      fastStart:'in-memory' });
    let encErr=null;
    const vEnc=new VideoEncoder({ output:(c,m)=>muxer.addVideoChunk(c,m), error:(e)=>{encErr=e;} });
    vEnc.configure({ codec:avcCodec, width:w, height:h, bitrate:6000000, framerate:30 });
    let aEnc=null;
    if(useAudio){ aEnc=new AudioEncoder({ output:(c,m)=>muxer.addAudioChunk(c,m), error:(e)=>{encErr=e;} });
      aEnc.configure({ codec:'mp4a.40.2', numberOfChannels:audioBuf.numberOfChannels, sampleRate:audioBuf.sampleRate, bitrate:128000 }); }
    const rec=document.createElement('canvas'); rec.width=w; rec.height=h; const rctx=rec.getContext('2d');
    rctx.setTransform(w/CW, 0, 0, h/CH, 0, 0);   // same reason as the WebM path
    const encFps=30, frameDurUs=1000000/encFps;
    const loops = frames.length>1 ? exLoops : 1;              // from the export sheet; a single page has nothing to loop
    const _units=[]; for(let i=_r.from-1;i<=_r.to-1;i++){ for(let k=0;k<frameHold(frames[i]);k++) _units.push(i); }
    const totalSec=(_units.length/fps)*loops;
    const totalFrames=Math.max(1, Math.ceil(totalSec*encFps));
    for(let f=0; f<totalFrames; f++){
      if(_exportAbort){ try{vEnc.close();}catch(e){} try{if(aEnc)aEnc.close();}catch(e){} exportHide(); chip('Export cancelled'); exporting=false; return true; }
      const animIdx=_units[Math.floor((f/encFps)*fps)%_units.length];
      drawFrameTo(rctx, frames[animIdx]);
      const vf=new VideoFrame(rec, { timestamp:Math.round(f*frameDurUs), duration:Math.round(frameDurUs) });
      vEnc.encode(vf, { keyFrame:(f%(encFps*2))===0 }); vf.close();
      if(encErr) throw encErr;
      if(vEnc.encodeQueueSize>8) await new Promise(r=>setTimeout(r,0));
      else if((f&7)===0){ exportSet((f/totalFrames)*(useAudio?0.8:1)); await new Promise(r=>setTimeout(r,0)); }
    }
    await vEnc.flush();
    if(useAudio && aEnc){
      exportSet(0.82,'Encoding audio…');
      const sr=audioBuf.sampleRate, ch=audioBuf.numberOfChannels, loopLen=audioBuf.length;
      const chans=[]; for(let c=0;c<ch;c++) chans.push(audioBuf.getChannelData(c));
      const totalSamples=Math.ceil(totalSec*sr), blk=1024; let pos=0;
      while(pos<totalSamples){ const n=Math.min(blk, totalSamples-pos); const data=new Float32Array(n*ch);
        for(let c=0;c<ch;c++){ const src=chans[c], off=c*n; for(let k=0;k<n;k++){ data[off+k]=src[(pos+k)%loopLen]; } }
        const ad=new AudioData({ format:'f32-planar', sampleRate:sr, numberOfFrames:n, numberOfChannels:ch, timestamp:Math.round((pos/sr)*1000000), data });
        aEnc.encode(ad); ad.close(); if(encErr) throw encErr; pos+=n;
        if((pos%(blk*32))===0){ exportSet(0.82+(pos/totalSamples)*0.16); await new Promise(r=>setTimeout(r,0)); }
      }
      await aEnc.flush();
    }
    if(encErr) throw encErr;
    muxer.finalize();
    download(new Blob([muxer.target.buffer],{type:'video/mp4'}),'skribl-flip.mp4');
    try{vEnc.close();}catch(e){} try{if(aEnc)aEnc.close();}catch(e){}
    exportSet(1,'Done!'); setTimeout(exportHide,500); chip('MP4 exported'); exporting=false; return true;
  }catch(err){ console.error('WebCodecs MP4 export failed:', err); exportHide(); chip('MP4 failed — using WebM'); exporting=false; return false; }
}
// Video export entry: try a real MP4 (with audio) first, else the WebM fallback.
// Mirrors exportVideo()'s decision WITHOUT side effects, so the export sheet can
// name the format the user will actually receive. The Pad has had this since it
// shipped; Flip did not, so "Video" silently produced WebM on any browser without
// WebCodecs H.264 — the user picked one thing and got another.
// Cheap on purpose: no loop buffer is built. aacSupported() only needs the sample
// rate and channel count, which the trimmed loop inherits from currentAudioBuffer.
async function expectedVideoFormat(){
  try{
    // Label only — do NOT load the muxer here. This runs when the export sheet
    // opens; fetching 32 KB to choose between the words "MP4" and "WebM" would
    // just move the cost from every page load to every sheet open. Presence of
    // the deployed URL answers it. exportViaWebCodecsMp4() loads for real.
    if(!(window.Mp4Muxer || (window.SKRIBL_VENDOR && window.SKRIBL_VENDOR.mp4muxer))) return 'WebM';
    if(typeof VideoEncoder==='undefined' || typeof VideoFrame==='undefined') return 'WebM';
    const w=CW&~1, h=CH&~1; if(w<2||h<2) return 'WebM';
    if(!(await pickAvcCodec(w,h))) return 'WebM';
    // Music on? MP4 needs AAC as well, or exportViaWebCodecsMp4 bails to WebM
    // rather than ship a silent MP4 — so the label must bail the same way.
    const hasAudio = !!musicData && musicEnabled && !musicMuted && !!currentAudioBuffer;
    if(hasAudio && !(await aacSupported(currentAudioBuffer.sampleRate, currentAudioBuffer.numberOfChannels))) return 'WebM';
    return 'MP4';
  }catch(e){ return 'WebM'; }
}

async function exportVideo(){
  if(exporting) return;
  if(frames.length<2){ chip('Add a page or two first'); return; }
  if(previewingLoop) stopLoopPreview();
  const okMp4 = await exportViaWebCodecsMp4();
  if(!okMp4) exportWebM();
}

/* ---- menu open/close + item wiring + state sync ---- */
const moreBtn=document.getElementById('moreBtn'), moreMenu=document.getElementById('moreMenu');
// Canvas size picker. Lives in the ⋯ menu because it is a document property, not
// a tool. Disabled during playback so the stage can't resize mid-animation.
const canvasSeg=document.getElementById('canvasSeg');
function positionCanvasSeg(){
  if(!canvasSeg) return;
  const a=canvasSeg.querySelector('button.on'), pill=canvasSeg.querySelector('.seg-slider');
  if(!a||!pill||!a.offsetWidth) return;
  pill.style.width=a.offsetWidth+'px';
  pill.style.transform='translateX('+(a.offsetLeft-3)+'px)';
  pill.style.opacity=1;
}
function syncCanvasSeg(){
  if(!canvasSeg) return;
  const id=currentSizeId();
  [...canvasSeg.querySelectorAll('button')].forEach(b=>b.classList.toggle('on', b.dataset.size===id));
  requestAnimationFrame(positionCanvasSeg);
}
if(canvasSeg) canvasSeg.addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b || playing) return;
  const preset=FLIP_SIZES.find(x=>x.id===b.dataset.size); if(!preset) return;
  if(applyCanvasSize(preset.w, preset.h)) chip('Canvas '+preset.label+' \u00b7 drawings keep their position');
  syncCanvasSeg();
});
if(moreBtn) moreBtn.addEventListener('click', ()=>requestAnimationFrame(syncCanvasSeg));
// --- media drawer controls ---
const photoUploadBtn=document.getElementById('photoUploadBtn'), photoBtnLabel=document.getElementById('photoBtnLabel'), photoToggle=document.getElementById('photoToggle'), photoRemove=document.getElementById('photoRemove');
const photoDetail=document.getElementById('photoDetail'), photoNote=document.getElementById('photoNote');
const photoFitGroup=document.getElementById('photoFitGroup'), photoFitSlider=document.getElementById('photoFitSlider');
const repositionBtn=document.getElementById('repositionBtn'), repositionHint=document.getElementById('repositionHint');
const photoZoomRow=document.getElementById('photoZoomRow'), photoZoomEl=document.getElementById('photoZoom'), photoZoomVal=document.getElementById('photoZoomVal');
const photoOpacityEl=document.getElementById('photoOpacity'), photoOpacityVal=document.getElementById('photoOpacityVal');
const photoBlurEl=document.getElementById('photoBlur'), photoBlurVal=document.getElementById('photoBlurVal');
const resetPhotoBtn=document.getElementById('resetPhotoBtn');
function fmtTime(s){ s=Math.max(0,s||0); const m=Math.floor(s/60), ss=Math.floor(s%60); return m+':'+String(ss).padStart(2,'0'); }
function setFill(el){ const mn=+el.min,mx=+el.max; el.style.setProperty('--slider-fill', (mx>mn?((+el.value-mn)/(mx-mn)*100):0)+'%'); }
function positionFitSlider(){ const btns=[...photoFitGroup.querySelectorAll('.photo-fit-btn')]; const a=photoFitGroup.querySelector('.photo-fit-btn.active');
  if(!a||!btns.length||!photoFitSlider||!a.offsetWidth) return;
  photoFitSlider.style.width=a.offsetWidth+'px'; photoFitSlider.style.transform='translateX('+(a.offsetLeft-btns[0].offsetLeft)+'px)'; }

const photoTabDot=document.getElementById('photoTabDot'), musicTabDot=document.getElementById('musicTabDot');
function syncPhotoUI(){
  const hasImg=!!bgImage;
  photoUploadBtn.classList.toggle('loaded', hasImg);
  photoBtnLabel.textContent = hasImg ? (imageName || 'Background image') : 'Add an image';
  photoRemove.hidden=!hasImg; photoNote.hidden=hasImg; photoDetail.hidden=!hasImg;
  photoToggle.classList.toggle('on', photoEnabled); photoToggle.setAttribute('aria-checked', String(photoEnabled));
  photoTabDot.hidden = !hasImg;                                                       // green dot when an image is set
  // Compared through the shared normaliser, not by string equality: this row's
  // third button is data-fit="fill" on Flip and data-fit="stretch" on Pad, so a
  // raw === left NO button active whenever photoFit held the other spelling.
  const _pf = window.SkriblPhotoFit.normalise(photoFit);
  [...photoFitGroup.querySelectorAll('.photo-fit-btn')].forEach(b=>b.classList.toggle('active', !!(window.SkriblPhotoFit.normalise(b.dataset.fit)===_pf)));
  const isCover = photoFit==='cover';
  photoZoomRow.style.display = isCover ? '' : 'none';
  repositionBtn.style.display = isCover ? '' : 'none';
  if(!isCover){ reposMode=false; }
  repositionBtn.classList.toggle('active', reposMode); repositionBtn.setAttribute('aria-pressed', String(reposMode));
  repositionHint.hidden = !reposMode || !hasImg;
  photoZoomEl.value=Math.round(photoZoom*100); photoZoomVal.textContent=Math.round(photoZoom*100)+'%'; setFill(photoZoomEl);
  photoOpacityEl.value=Math.round(photoOpacity*100); photoOpacityVal.textContent=Math.round(photoOpacity*100)+'%'; setFill(photoOpacityEl);
  photoBlurEl.value=photoBlur; photoBlurVal.textContent=photoBlur+'px'; setFill(photoBlurEl);
  positionFitSlider();
}
function syncMusicUI(){
  const hasMus=!!musicData;
  musicUploadBtn.classList.toggle('loaded', hasMus);
  musicBtnLabel.textContent = hasMus ? (musicName || 'Music loop') : 'Add music';
  musicRemove.hidden = !hasMus;
  musicToggle.classList.toggle('on', musicEnabled); musicToggle.setAttribute('aria-checked', String(musicEnabled));
  musicDetail.hidden = !hasMus;
  musicNote.hidden = hasMus;
  musicTabDot.hidden = !hasMus;
  if(hasMus) updateTrimUI();
}
function syncMediaUI(){ syncPhotoUI(); syncMusicUI(); refreshPendingCards(); }

// The Draw/Image/Music drawers are shared partials, so Flip already HAS the Pad's
// #musicPending / #photoPending re-add cards in its DOM — it just never drove them.
// Runs last inside syncMediaUI, because syncPhotoUI/syncMusicUI reset the tab dots.
function fmtLoopTime(sec){ const m=Math.floor(sec/60), s=Math.floor(sec%60); return m+':'+String(s).padStart(2,'0'); }
function refreshPendingCards(){
  const mCard=document.getElementById('musicPending'), pCard=document.getElementById('photoPending');
  const mUp=document.getElementById('musicUploadBtn'), pUp=document.getElementById('photoUploadBtn');
  const mDot=document.getElementById('musicTabDot'),  pDot=document.getElementById('photoTabDot');
  if(mCard){
    if(pendingMusicMeta && !musicData){
      document.getElementById('musicPendingName').textContent = pendingMusicMeta.name || 'Your track';
      let meta='Loop saved';
      if(pendingMusicMeta.trimStart!=null && pendingMusicMeta.trimEnd!=null){
        const len=pendingMusicMeta.trimEnd-pendingMusicMeta.trimStart;
        meta='Loop '+fmtLoopTime(pendingMusicMeta.trimStart)+'–'+fmtLoopTime(pendingMusicMeta.trimEnd)+' · '+len.toFixed(1)+'s';
      }
      document.getElementById('musicPendingMeta').textContent=meta;
      mCard.hidden=false; if(mUp) mUp.hidden=true;
      if(mDot){ mDot.hidden=false; mDot.classList.add('pending'); }
    } else {
      mCard.hidden=true; if(mUp) mUp.hidden=false;
      // Restore hidden, not just the class. The branch above sets hidden=false
      // for the pending dot; dropping only 'pending' here left a VISIBLE dot
      // with no pending styling — which renders in the "has media" green —
      // until syncMusicUI() next ran and hid it. Dismissing the re-add card
      // turned the dot green, and opening the drawer made it vanish.
      if(mDot){ mDot.classList.remove('pending'); mDot.hidden = !musicData; }
    }
  }
  if(pCard){
    if(pendingPhotoMeta && !bgImage){
      document.getElementById('photoPendingName').textContent = pendingPhotoMeta.name || 'Your image';
      const parts=[];
      if(pendingPhotoMeta.fit) parts.push({cover:'Fill',contain:'Fit',fill:'Stretch',stretch:'Stretch'}[pendingPhotoMeta.fit] || pendingPhotoMeta.fit);
      if(pendingPhotoMeta.opacity!=null) parts.push(Math.round(pendingPhotoMeta.opacity*100)+'% opacity');
      if(pendingPhotoMeta.blur) parts.push(pendingPhotoMeta.blur+'px blur');
      if(pendingPhotoMeta.zoom && pendingPhotoMeta.zoom!==1) parts.push(Math.round(pendingPhotoMeta.zoom*100)+'% zoom');
      document.getElementById('photoPendingMeta').textContent = parts.length ? parts.join(' · ') : 'Adjustments saved';
      pCard.hidden=false; if(pUp) pUp.hidden=true;
      if(pDot){ pDot.hidden=false; pDot.classList.add('pending'); }
    } else {
      pCard.hidden=true; if(pUp) pUp.hidden=false;
      // Same as the music dot above: restore hidden, not just the class.
      if(pDot){ pDot.classList.remove('pending'); pDot.hidden = !bgImage; }
    }
  }
}

// image controls
photoUploadBtn.addEventListener('click',(e)=>{ if(e.target.closest('.dropzone-remove')||e.target.closest('.layer-toggle')) return; if(!photoUploadBtn.classList.contains('loaded')) imageInput.click(); });
photoRemove.addEventListener('click',(e)=>{ e.stopPropagation(); imageSelectionSeq++; removeBgImage(); });
photoToggle.addEventListener('click',(e)=>{ e.stopPropagation(); photoEnabled=!photoEnabled; redrawAll(); syncPhotoUI(); scheduleSave(); });
photoFitGroup.addEventListener('click',e=>{ const b=e.target.closest('.photo-fit-btn'); if(!b) return; photoFit=b.dataset.fit; redrawAll(); syncPhotoUI(); scheduleSave(); });
repositionBtn.addEventListener('click',()=>{ if(photoFit!=='cover') return; reposMode=!reposMode; syncPhotoUI(); });
photoZoomEl.addEventListener('input',()=>{ photoZoom=(+photoZoomEl.value)/100; photoZoomVal.textContent=photoZoomEl.value+'%'; setFill(photoZoomEl); redrawAll(); scheduleSave(); });
photoOpacityEl.addEventListener('input',()=>{ photoOpacity=(+photoOpacityEl.value)/100; photoOpacityVal.textContent=photoOpacityEl.value+'%'; setFill(photoOpacityEl); redrawAll(); scheduleSave(); });
photoBlurEl.addEventListener('input',()=>{ photoBlur=+photoBlurEl.value; photoBlurVal.textContent=photoBlur+'px'; setFill(photoBlurEl); redrawAll(); scheduleSave(); });
resetPhotoBtn.addEventListener('click',()=>{ photoFit='cover'; photoOpacity=1; photoBlur=0; photoZoom=1; photoOffX=0.5; photoOffY=0.5; reposMode=false; photoEnabled=true; redrawAll(); syncPhotoUI(); scheduleSave(); });

// ===== music component (ported from the Pad: waveform + trim + Loop Detail) =====
const musicUploadBtn=document.getElementById('musicUploadBtn'), musicBtnLabel=document.getElementById('musicBtnLabel');
const musicDetail=document.getElementById('musicDetail'), musicToggle=document.getElementById('musicToggle'), musicRemove=document.getElementById('musicRemove');
const musicNote=document.getElementById('musicNote');
const musicTrack=document.getElementById('musicTrack'), musicRange=document.getElementById('musicRange');
const handleStart=document.getElementById('handleStart'), handleEnd=document.getElementById('handleEnd');
const trimStartLabel=document.getElementById('trimStartLabel'), trimEndLabel=document.getElementById('trimEndLabel'), trimDurLabel=document.getElementById('trimDurLabel');
const bubbleStart=document.getElementById('bubbleStart'), bubbleEnd=document.getElementById('bubbleEnd'), playhead=document.getElementById('playhead');
const waveformCanvas=document.getElementById('waveformCanvas'), waveformCtx=waveformCanvas.getContext('2d');
const zoomWaveformCanvas=document.getElementById('zoomWaveformCanvas'), zoomWaveformCtx=zoomWaveformCanvas.getContext('2d');
const loopZoomLabel=document.getElementById('loopZoomLabel'), loopSummary=document.getElementById('loopSummary'), zoomPlayhead=document.getElementById('zoomPlayhead');
const zoomHandleStart=document.getElementById('zoomHandleStart'), zoomHandleEnd=document.getElementById('zoomHandleEnd'), zoomTrackWrap=document.getElementById('zoomTrackWrap');
const startReadout=document.getElementById('startReadout'), endReadout=document.getElementById('endReadout');
const matchDrawingBtn=document.getElementById('matchDrawingBtn'), testSeamBtn=document.getElementById('testSeamBtn'), previewLoopBtn=document.getElementById('previewLoopBtn');
const nudgeStepLabel=document.getElementById('nudgeStepLabel'), nudgeStepFinerBtn=document.getElementById('nudgeStepFiner'), nudgeStepCoarserBtn=document.getElementById('nudgeStepCoarser');
const updateSliderFill = setFill;
function formatTimeH(sec){ let total=Math.round(sec*100); const hh=total%100; total=(total-hh)/100; const s=total%60; const m=Math.floor(total/60); return m+':'+String(s).padStart(2,'0')+'.'+String(hh).padStart(2,'0'); }

function updateTrimUI(){
  if(!Number.isFinite(audioDuration) || audioDuration<=0) return;
  if(!Number.isFinite(trimStart)) trimStart=0;
  if(trimEnd==null || !Number.isFinite(trimEnd)) trimEnd=Math.min(audioDuration, trimStart+Math.min(MAX_LOOP_SECONDS,audioDuration));
  const minLoop=0.01;
  trimStart=Math.max(0, Math.min(trimStart, Math.max(0,audioDuration-minLoop)));
  trimEnd=Math.max(trimStart+minLoop, Math.min(trimEnd, audioDuration));
  // Single choke point for the cap: every path (load, draft restore, re-add,
  // drag) lands here, so the <=20s invariant can't be bypassed by any of them.
  if(trimEnd-trimStart>window.SkriblLoopTrim.MAX_LOOP_SECONDS) trimEnd=trimStart+window.SkriblLoopTrim.MAX_LOOP_SECONDS;
  const startPct=(trimStart/audioDuration)*100, endPct=(trimEnd/audioDuration)*100;
  handleStart.style.left=startPct+'%'; handleEnd.style.left=endPct+'%';
  musicRange.style.left=startPct+'%'; musicRange.style.width=(endPct-startPct)+'%';
  const rangePx=((endPct-startPct)/100)*musicTrack.getBoundingClientRect().width;
  musicRange.classList.toggle('narrow', rangePx<40);
  trimStartLabel.textContent=fmtTime(0); trimEndLabel.textContent=fmtTime(audioDuration);
  trimDurLabel.textContent=formatTimeH(trimEnd-trimStart)+' selected';
  if(bubbleStart) bubbleStart.textContent=formatTimeH(trimStart);
  if(bubbleEnd) bubbleEnd.textContent=formatTimeH(trimEnd);
  if(startReadout) startReadout.textContent=trimStart.toFixed(2)+'s';
  if(endReadout) endReadout.textContent=trimEnd.toFixed(2)+'s';
  const dur=trimEnd-trimStart;
  if(loopSummary) loopSummary.textContent='Loop: '+formatTimeH(trimStart)+' \u2192 '+formatTimeH(trimEnd)+' [' + dur.toFixed(2)+'s]';
  requestZoomWaveformDraw(); updateZoomHandles(); if(typeof updateZoomPanSlider==='function') updateZoomPanSlider();
}

function getZoomWindow(){
  const loopDuration=Math.max(0, trimEnd-trimStart);
  const contextSeconds=Math.max(1, Math.min(4, loopDuration*0.25));
  const halfSpan=(loopDuration/2+contextSeconds)/zoomMag;
  let center;
  if(zoomCenter!=null) center=zoomCenter;
  else if(zoomFocus==='start') center=trimStart;
  else if(zoomFocus==='end') center=trimEnd;
  else center=(trimStart+trimEnd)/2;
  const lo=halfSpan, hi=Math.max(halfSpan, audioDuration-halfSpan);
  center=Math.max(lo, Math.min(center, hi));
  let start=Math.max(0, center-halfSpan), end=Math.min(audioDuration, center+halfSpan);
  if(end-start<0.001) end=Math.min(audioDuration, start+0.001);
  return { start, end, duration: Math.max(0.001, end-start) };
}
function syncZoomFocusButtons(){ document.querySelectorAll('.zoom-mag-btn[data-focus]').forEach(b=>{ b.classList.toggle('active', zoomFocus!=='free' && b.dataset.focus===zoomFocus); }); }
function updateZoomHandles(){
  if(!zoomTrackWrap||!zoomHandleStart||!zoomHandleEnd) return;
  if(!Number.isFinite(audioDuration)||audioDuration<=0) return;
  const zw=getZoomWindow(), startPct=((trimStart-zw.start)/zw.duration)*100, endPct=((trimEnd-zw.start)/zw.duration)*100;
  zoomHandleStart.style.left=startPct+'%'; zoomHandleEnd.style.left=endPct+'%';
  zoomHandleStart.hidden=!(startPct>=-2&&startPct<=102); zoomHandleEnd.hidden=!(endPct>=-2&&endPct<=102);
}
let zoomDrawPending=false;
function requestZoomWaveformDraw(){ if(zoomDrawPending) return; zoomDrawPending=true; requestAnimationFrame(()=>{ zoomDrawPending=false; if(currentAudioBuffer) drawWaveform(currentAudioBuffer); drawZoomWaveform(); }); }
function drawWaveform(audioBuffer){
  // Same guard as Pad's copy, for the same reason — see the long comment on
  // app.js's drawWaveform. A 0-wide rect CLEARS the bitmap and paints nothing,
  // and drawZoomWaveform() below has always had this line while this one did
  // not, which is why Loop Detail rendered and the strip above it did not.
  // Flip recovers more often than Pad (requestZoomWaveformDraw repaints BOTH
  // canvases and reveal() calls it on music open), so the window here is
  // narrower — but the unguarded wipe is identical, and a repaint that lands
  // while the panel is still mid-animation reintroduces it.
  if(!audioBuffer||!musicTrack||!waveformCanvas) return;
  const rect=musicTrack.getBoundingClientRect(); if(!rect.width) return;
  waveformCanvas.width=rect.width; waveformCanvas.height=rect.height;
  const data=audioBuffer.getChannelData(0); const samples=waveformCanvas.width||1; const blockSize=Math.max(1,Math.floor(data.length/samples));
  const h=waveformCanvas.height, mid=h/2; waveformCtx.clearRect(0,0,waveformCanvas.width,h); waveformCtx.fillStyle='#3a4150';
  for(let i=0;i<samples;i++){ const s=i*blockSize; let mn=1,mx=-1; for(let j=0;j<blockSize;j++){ const v=data[s+j]||0; if(v<mn)mn=v; if(v>mx)mx=v; } const y1=mid+mn*mid*0.85, y2=mid+mx*mid*0.85; waveformCtx.fillRect(i,y1,1,Math.max(1,y2-y1)); }
}
function drawZoomWaveform(){
  if(!currentAudioBuffer||!zoomWaveformCanvas) return;
  const rect=zoomWaveformCanvas.getBoundingClientRect(); if(!rect.width) return;
  const dpr=window.devicePixelRatio||1; zoomWaveformCanvas.width=Math.round(rect.width*dpr); zoomWaveformCanvas.height=Math.round(rect.height*dpr);
  zoomWaveformCtx.setTransform(dpr,0,0,dpr,0,0); const w=rect.width, h=rect.height, mid=h/2;
  const loopDuration=trimEnd-trimStart, zw=getZoomWindow(), zst=zw.start, zdur=zw.duration;
  zoomWaveformCtx.fillStyle='#161a22'; zoomWaveformCtx.fillRect(0,0,w,h);
  const data=currentAudioBuffer.getChannelData(0), sr=currentAudioBuffer.sampleRate;
  const startSample=Math.max(0,Math.floor(zst*sr)), endSample=Math.min(data.length,Math.floor(zw.end*sr));
  const totalSamples=Math.max(1,endSample-startSample), spp=Math.max(1,Math.floor(totalSamples/w));
  zoomWaveformCtx.fillStyle='#3a4150';
  for(let x=0;x<w;x++){ const a=startSample+x*spp, b=Math.min(a+spp,endSample); let mn=1,mx=-1; for(let i=a;i<b;i++){ const v=data[i]||0; if(v<mn)mn=v; if(v>mx)mx=v; } zoomWaveformCtx.fillRect(x, mid+mn*mid*0.9, 1, Math.max(1,(mid+mx*mid*0.9)-(mid+mn*mid*0.9))); }
  const lsX=((trimStart-zst)/zdur)*w, leX=((trimEnd-zst)/zdur)*w;
  zoomWaveformCtx.fillStyle='rgba(124,92,255,0.2)'; zoomWaveformCtx.fillRect(lsX,0,leX-lsX,h);
  zoomWaveformCtx.fillStyle='#7c5cff';
  for(let x=Math.floor(lsX);x<Math.ceil(leX);x++){ const a=startSample+x*spp, b=Math.min(a+spp,endSample); let mn=1,mx=-1; for(let i=a;i<b;i++){ const v=data[i]||0; if(v<mn)mn=v; if(v>mx)mx=v; } zoomWaveformCtx.fillRect(x, mid+mn*mid*0.9, 1, Math.max(1,(mid+mx*mid*0.9)-(mid+mn*mid*0.9))); }
  zoomWaveformCtx.fillStyle='#7c5cff'; zoomWaveformCtx.fillRect(lsX,0,2,h); zoomWaveformCtx.fillRect(leX-2,0,2,h);
  if(loopCrossfadeMs>0 && loopDuration>0){ const loopFrames=Math.floor(loopDuration*sr); const xf=Math.min(Math.floor((loopCrossfadeMs/1000)*sr), Math.floor(loopFrames/2)); const xfW=((xf/sr)/zdur)*w;
    if(xfW>0){ const headX=lsX, tailX=leX-xfW; zoomWaveformCtx.fillStyle='rgba(255,176,32,0.22)'; zoomWaveformCtx.fillRect(headX,0,xfW,h); zoomWaveformCtx.fillRect(tailX,0,xfW,h); zoomWaveformCtx.fillStyle='rgba(255,176,32,0.9)'; for(let yy=0;yy<h;yy+=9){ zoomWaveformCtx.fillRect(headX+xfW-1,yy,1.5,5); zoomWaveformCtx.fillRect(tailX,yy,1.5,5); } } }
  zoomWaveformCtx.fillStyle='#2e3340'; zoomWaveformCtx.fillRect(0,mid,w,1);
  if(loopZoomLabel){ const xfL=loopCrossfadeMs>0?('  \u00b7  xfade '+loopCrossfadeMs+'ms'):''; loopZoomLabel.textContent=formatTimeH(trimStart)+' \u2192 '+formatTimeH(trimEnd)+' ['+loopDuration.toFixed(2)+'s]'+xfL; }
}

function dragHandle(handle, isStart){
  function cx(e){ return SkriblEventPoint.at(e).clientX; }
  function onStart(e){ e.preventDefault(); handle.classList.add('dragging');
    function onMove(ev){ const rect=musicTrack.getBoundingClientRect(); let pct=(cx(ev)-rect.left)/rect.width; pct=Math.max(0,Math.min(1,pct)); const time=pct*audioDuration;
      // Shared with Pad via lib/looptrim.js. 'constrain': the handle being
      // dragged stops at the cap and the other end stays where the user put it.
      const _t=window.SkriblLoopTrim.setHandle({start:trimStart,end:trimEnd,duration:audioDuration}, isStart?'start':'end', time, 'constrain');
      trimStart=_t.start; trimEnd=_t.end;
      updateTrimUI(); scheduleSave(); }
    function onEnd(){ handle.classList.remove('dragging'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); window.removeEventListener('touchcancel',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd); window.addEventListener('touchcancel',onEnd);
  }
  handle.addEventListener('mousedown',onStart); handle.addEventListener('touchstart',onStart,{passive:false});
}
dragHandle(handleStart,true); dragHandle(handleEnd,false);
function dragRangeWindow(rangeEl){
  function cx(e){ return SkriblEventPoint.at(e).clientX; }
  function onStart(e){ if(!audioEl||!(audioDuration>0)) return; if(rangeEl.classList.contains('narrow')) return; e.preventDefault(); e.stopPropagation(); rangeEl.classList.add('dragging');
    const rect=musicTrack.getBoundingClientRect(); const loopLength=trimEnd-trimStart; const grabTime=(cx(e)-rect.left)/rect.width*audioDuration; const grabOffset=grabTime-trimStart;
    function onMove(ev){ const time=(cx(ev)-rect.left)/rect.width*audioDuration; let ns=time-grabOffset; ns=Math.max(0,Math.min(ns,audioDuration-loopLength)); trimStart=ns; trimEnd=ns+loopLength; updateTrimUI(); }
    function onEnd(){ rangeEl.classList.remove('dragging'); scheduleSave(); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); window.removeEventListener('touchcancel',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd); window.addEventListener('touchcancel',onEnd);
  }
  rangeEl.addEventListener('mousedown',onStart); rangeEl.addEventListener('touchstart',onStart,{passive:false});
}
dragRangeWindow(musicRange);
function dragZoomHandle(handle, isStart){
  function onStart(e){ e.preventDefault(); handle.classList.add('dragging');
    function onMove(ev){ const clientX=SkriblEventPoint.at(ev).clientX; const rect=zoomTrackWrap.getBoundingClientRect(); const pct=Math.max(0,Math.min(1,(clientX-rect.left)/rect.width)); const zw=getZoomWindow(); const time=zw.start+pct*(zw.end-zw.start);
      // 'slide': the zoom track pushes the OTHER end to hold the cap. That
      // differs from the main track above — declared, not accidental; see the
      // module header.
      const _t=window.SkriblLoopTrim.setHandle({start:trimStart,end:trimEnd,duration:audioDuration}, isStart?'start':'end', time, 'slide');
      trimStart=_t.start; trimEnd=_t.end;
      updateTrimUI(); scheduleSave(); }
    function onEnd(){ handle.classList.remove('dragging'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); window.removeEventListener('touchcancel',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd); window.addEventListener('touchcancel',onEnd);
  }
  handle.addEventListener('mousedown',onStart); handle.addEventListener('touchstart',onStart,{passive:false});
}
dragZoomHandle(zoomHandleStart,true); dragZoomHandle(zoomHandleEnd,false);

// seg-slider pill for the zoom mag/focus groups
function positionSegSlider(group){ if(window.SkriblSegSlider) window.SkriblSegSlider.placeAttached(group); }
// Both editors carried an equivalent of this; it lives in lib/segslider.js now.
function attachSegSlider(group){ if(window.SkriblSegSlider) window.SkriblSegSlider.attach(group); }
(function initZoomMagControl(){ if(!zoomTrackWrap||!zoomTrackWrap.parentNode) return;
  const bar=document.createElement('div'); bar.className='zoom-mag-bar';
  // v207: real .seg pill sliders + a magnifier glyph on the zoom group (matches Pad).
  bar.innerHTML='<span class="seg zoom-seg" data-role="focus" title="What the loop view centres on"><button type="button" class="zoom-mag-btn on" data-focus="loop">Loop</button><button type="button" class="zoom-mag-btn" data-focus="start">Start</button><button type="button" class="zoom-mag-btn" data-focus="end">End</button></span>'+'<span class="zoom-mag-wrap"><span class="seg zoom-seg" data-role="mag" title="Zoom level" role="group" aria-label="Zoom level"><button type="button" class="zoom-mag-btn on" data-mag="1">1&times;</button><button type="button" class="zoom-mag-btn" data-mag="2">2&times;</button><button type="button" class="zoom-mag-btn" data-mag="4">4&times;</button><button type="button" class="zoom-mag-btn" data-mag="8">8&times;</button></span></span>';
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-seg[data-role="focus"]')); attachSegSlider(bar.querySelector('.zoom-seg[data-role="mag"]'));
  // .on not .active: real .seg cells now; the shared slider reads .on.
  bar.addEventListener('click',(e)=>{ const b=e.target.closest('.zoom-mag-btn'); if(!b) return; b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x=>x.classList.remove('on')); b.classList.add('on'); if(b.dataset.focus){ zoomFocus=b.dataset.focus; zoomCenter=null; } if(b.dataset.mag) zoomMag=parseFloat(b.dataset.mag)||1; updateTrimUI(); });
  // v207: shell + cells come from styles.css .seg; only bar layout + the magnifier glyph here.
  const style=document.createElement('style'); style.textContent='.zoom-mag-bar{display:flex;gap:10px;justify-content:space-between;align-items:center;margin:8px 0 6px;flex-wrap:wrap}.zoom-mag-wrap{display:inline-flex;align-items:center;gap:8px}'; document.head.appendChild(style);
})();
bindEl('fineTuneToggle', 'click',()=>{ const body=document.getElementById('fineTuneBody'); const t=document.getElementById('fineTuneToggle'); const open=body.hidden; body.hidden=!open; t.setAttribute('aria-expanded', open?'true':'false'); if(open){ requestAnimationFrame(()=>{ updateTrimUI(); document.querySelectorAll('.zoom-seg').forEach(g=>positionSegSlider(g)); }); } });

// nudge fine-tune
const nudgeSteps=[0.01,0.02,0.05,0.1]; let nudgeStepIdx=3;
function updateNudgeStepLabel(){ nudgeStepLabel.textContent=nudgeSteps[nudgeStepIdx]+'s'; nudgeStepFinerBtn.disabled=nudgeStepIdx===0; nudgeStepCoarserBtn.disabled=nudgeStepIdx===nudgeSteps.length-1; }
nudgeStepFinerBtn.addEventListener('click',()=>{ nudgeStepIdx=Math.max(0,nudgeStepIdx-1); updateNudgeStepLabel(); });
nudgeStepCoarserBtn.addEventListener('click',()=>{ nudgeStepIdx=Math.min(nudgeSteps.length-1,nudgeStepIdx+1); updateNudgeStepLabel(); });
function nudgeTrim(which, direction){ if(!audioEl) return; if((which!=='start'&&which!=='end')||!Number.isFinite(direction)) return; const amount=direction*nudgeSteps[nudgeStepIdx];
  const _n=window.SkriblLoopTrim.setHandle({start:trimStart,end:trimEnd,duration:audioDuration}, which, (which==='start'?trimStart:trimEnd)+amount, 'slide');
  trimStart=_n.start; trimEnd=_n.end; updateTrimUI(); scheduleSave(); }
document.querySelectorAll('.nudge-btn[data-which]').forEach(btn=>{ btn.addEventListener('click',()=>nudgeTrim(btn.dataset.which, parseFloat(btn.dataset.amount))); });
updateNudgeStepLabel();

// Match Drawing Time — set loop length to the animation runtime
function setLoopToDrawingLength(){ if(!audioEl || !(audioDuration>0)) return; const drawingSeconds=frames.length/fps; const loopLength=window.SkriblLoopTrim.loopLength(drawingSeconds,audioDuration); trimEnd=trimStart+loopLength; if(trimEnd>audioDuration){ trimEnd=audioDuration; trimStart=Math.max(0,trimEnd-loopLength); } updateTrimUI(); scheduleSave(); }
matchDrawingBtn.addEventListener('click', setLoopToDrawingLength);

// preview loop + test seam (seek-based on the <audio> element)
let previewingLoop=false, previewLoopTimer=null, seamStopTimer=null, _previewWA=false;
function stopLoopPreview(){ previewingLoop=false; _previewWA=false;
  if(!playing){ stopWebAudioLoop(); if(audioEl){ try{audioEl.pause();}catch(_){}} }
  if(previewLoopTimer) clearInterval(previewLoopTimer); if(seamStopTimer) clearTimeout(seamStopTimer); previewLoopTimer=null; seamStopTimer=null;
  if(playhead) playhead.hidden=true; if(zoomPlayhead) zoomPlayhead.hidden=true; if(previewLoopBtn) previewLoopBtn.textContent='Preview Loop'; }
function previewTick(){ if(!previewingLoop) return;
  if(!_previewWA){ if(!audioEl) return; if(audioEl.currentTime>=trimEnd-0.05){ audioEl.currentTime=trimStart; audioEl.play().catch(()=>{}); } }
  const st=loopPosition();
  const pct=(st/audioDuration)*100; if(playhead){ playhead.hidden=false; playhead.style.left=pct+'%'; }
  if(zoomPlayhead && currentAudioBuffer){ const zw=getZoomWindow(); const zp=((st-zw.start)/zw.duration)*100; zoomPlayhead.hidden=false; zoomPlayhead.style.left=Math.max(0,Math.min(100,zp))+'%'; } }
function startLoopPreviewNative(){ if(!previewingLoop) return; _previewWA=false; ensureAudio(); if(!audioEl){ stopLoopPreview(); return; } try{ audioEl.muted=false; audioEl.currentTime=trimStart; audioEl.play().catch(()=>{}); }catch(_){} }
function startLoopPreview(){
  previewingLoop=true; previewLoopBtn.textContent='Stop Preview';
  if(startWebAudioLoop(startLoopPreviewNative)){ _previewWA=true; }           // gapless; native reachable on async unlock failure
  else startLoopPreviewNative();
  previewLoopTimer=setInterval(previewTick,30);
}
previewLoopBtn.addEventListener('click',()=>{ if(previewingLoop) stopLoopPreview(); else startLoopPreview(); });
testSeamBtn.addEventListener('click',()=>{ stopLoopPreview(); previewingLoop=true; previewLoopBtn.textContent='Stop Preview';
  // The gapless engine already loops seamlessly; play ~2 loops so you can hear the wrap (and the crossfade, if set).
  const seamNative=()=>{ if(!previewingLoop) return; _previewWA=false; ensureAudio(); if(!audioEl){ stopLoopPreview(); return; }
    const seamStart=Math.max(trimStart, trimEnd-1.25); try{ audioEl.muted=false; audioEl.currentTime=seamStart; audioEl.play().catch(()=>{}); }catch(_){}
    if(!previewLoopTimer) previewLoopTimer=setInterval(previewTick,30);
    const runFor=(trimEnd-seamStart)+Math.min(1.25, trimEnd-trimStart)+0.4; if(seamStopTimer) clearTimeout(seamStopTimer); seamStopTimer=setTimeout(stopLoopPreview, runFor*1000); };
  if(startWebAudioLoop(seamNative)){ _previewWA=true; previewLoopTimer=setInterval(previewTick,30);
    seamStopTimer=setTimeout(stopLoopPreview, Math.min((trimEnd-trimStart)*2+0.4, 12)*1000); return; }
  seamNative(); });

// Loop Detail scroll + crossfade (injected, like the Pad)
function updateZoomPanSlider(){ const s=document.getElementById('zoomPanSlider'); if(!s) return; if(!(audioDuration>0)){ s.value=500; return; } const zw=getZoomWindow(); const c=(zw.start+zw.end)/2; s.value=Math.round(Math.max(0,Math.min(1,c/audioDuration))*1000); updateSliderFill(s); }
function dragZoomPan(wrap){ if(!wrap) return; const cx=(e)=>SkriblEventPoint.at(e).clientX;
  function onStart(e){ if(!audioEl||!(audioDuration>0)) return; if(e.target.closest('.zoom-handle')) return; e.preventDefault(); const rect=wrap.getBoundingClientRect(); const zw=getZoomWindow(); const sc=(zw.start+zw.end)/2; const winDur=zw.duration; const sx=cx(e); wrap.classList.add('panning');
    function onMove(ev){ const dx=cx(ev)-sx; const dt=-(dx/rect.width)*winDur; const half=winDur/2; const lo=half, hi=Math.max(half,audioDuration-half); zoomCenter=Math.max(lo,Math.min(sc+dt,hi)); zoomFocus='free'; syncZoomFocusButtons(); updateTrimUI(); }
    function onEnd(){ wrap.classList.remove('panning'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); window.removeEventListener('touchcancel',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd); window.addEventListener('touchcancel',onEnd); }
  wrap.addEventListener('mousedown',onStart); wrap.addEventListener('touchstart',onStart,{passive:false});
}
function addSliderNudgers(el, opts){ opts=opts||{}; const wrap=document.createElement('span'); wrap.className='slider-nudge-wrap'; el.parentNode.insertBefore(wrap, el); wrap.appendChild(el);
  const mk=(txt,dir)=>{ const b=document.createElement('button'); b.type='button'; b.className='slider-nudge-btn'; b.textContent=txt; b.addEventListener('click',()=>{ if(opts.nudgeFn){ opts.nudgeFn(dir); } else { const step=opts.step||1; el.value=(+el.value)+dir*step; el.dispatchEvent(new Event('input',{bubbles:true})); } }); return b; };
  wrap.insertBefore(mk('\u2212',-1), el); wrap.appendChild(mk('+',1)); }
function setCrossfadeUI(){ const s=document.getElementById('crossfadeSlider'), v=document.getElementById('crossfadeVal'); if(s){ s.value=loopCrossfadeMs; updateSliderFill(s); } if(v) v.textContent=loopCrossfadeMs>0?(loopCrossfadeMs+' ms'):'Off'; }
(function initSliderExtras(){
  const style=document.createElement('style'); style.textContent='.slider-nudge-wrap{display:flex;align-items:center;gap:6px;flex:1;min-width:0}.slider-nudge-wrap input[type=range]{flex:1;min-width:0}.slider-nudge-btn{flex:none;width:26px;height:26px;padding:0;border:0;border-radius:7px;background:#232734;color:#c8cede;font-size:16px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;user-select:none;transition:background .12s}.slider-nudge-btn:hover{background:#2c3140}.slider-nudge-btn:active{background:var(--accent);color:#fff}.zoom-pan-row,.crossfade-row{display:flex;align-items:center;gap:10px;margin:8px 0 2px}.zoom-pan-label,.crossfade-label{font-size:12px;color:#8a93a6;flex:none;min-width:64px}.crossfade-val{font-size:12px;color:#c8cede;flex:none;min-width:38px;text-align:right}#zoomTrackWrap{cursor:grab}#zoomTrackWrap.panning{cursor:grabbing}'; document.head.appendChild(style);
  const zoomWrap=document.getElementById('zoomTrackWrap');
  if(zoomWrap){ const panRow=document.createElement('div'); panRow.className='zoom-pan-row'; panRow.innerHTML='<span class="zoom-pan-label">Scroll</span><input type="range" id="zoomPanSlider" class="slider" min="0" max="1000" value="500" step="1" aria-label="Scroll the loop detail view">'; zoomWrap.insertAdjacentElement('afterend', panRow);
    const ps=document.getElementById('zoomPanSlider'); ps.addEventListener('input',()=>{ if(!(audioDuration>0)) return; zoomCenter=(parseInt(ps.value,10)/1000)*audioDuration; zoomFocus='free'; syncZoomFocusButtons(); updateTrimUI(); });
    addSliderNudgers(ps,{ nudgeFn:(dir)=>{ if(!(audioDuration>0)) return; const zw=getZoomWindow(); const c=(zw.start+zw.end)/2; const half=zw.duration/2; const lo=half, hi=Math.max(half,audioDuration-half); zoomCenter=Math.max(lo,Math.min(c+dir*zw.duration*0.1,hi)); zoomFocus='free'; syncZoomFocusButtons(); updateTrimUI(); } });
    dragZoomPan(zoomWrap); }
  const finePanel=document.querySelector('.finetune-panel'); const cfRow=document.createElement('div'); cfRow.className='crossfade-row'; cfRow.innerHTML='<span class="crossfade-label">Crossfade</span><input type="range" id="crossfadeSlider" class="slider" min="0" max="500" value="0" step="5" aria-label="Loop crossfade length"><span class="crossfade-val" id="crossfadeVal">Off</span>';
  if(finePanel) finePanel.insertAdjacentElement('afterend', cfRow);
  const cf=document.getElementById('crossfadeSlider'); if(cf){ cf.addEventListener('input',()=>{ loopCrossfadeMs=parseInt(cf.value,10)||0; setCrossfadeUI(); updateTrimUI(); scheduleSave(); if((previewingLoop&&_previewWA)||_waLoopSource) startWebAudioLoop(); }); addSliderNudgers(cf,{step:5}); setCrossfadeUI(); }
})();

// upload / toggle / remove
musicUploadBtn.addEventListener('click',(e)=>{ if(e.target.closest('.dropzone-remove')||e.target.closest('.layer-toggle')) return; if(!musicUploadBtn.classList.contains('loaded')) musicInput.click(); });
musicToggle.addEventListener('click',(e)=>{ e.stopPropagation(); musicEnabled=!musicEnabled; if(!musicEnabled) stopMusic(); else if(playing) startMusic(); syncMusicUI(); scheduleSave(); });
musicRemove.addEventListener('click',(e)=>{ e.stopPropagation(); removeMusic(); });

// overflow menu (save/load/export)
const moreScrim=document.getElementById('moreScrim');
// Shared with Pad via lib/postedui.js — neither editor carries a copy.
window._skriblPostedUI = window.SkriblPostedUI ? window.SkriblPostedUI.init() : null;
{ const _mi=document.getElementById('miPosted');
  if(_mi) _mi.addEventListener('click', ()=>{ closeMenu(); if(window._skriblPostedUI) window._skriblPostedUI.open(); }); }
function openMenu(){ if(window._skriblSyncHintToggle) window._skriblSyncHintToggle();
  moreMenu.hidden=false; if(moreScrim) moreScrim.hidden=false; moreBtn.classList.add('on'); moreBtn.setAttribute('aria-expanded','true'); }
function closeMenu(){ moreMenu.hidden=true; if(moreScrim) moreScrim.hidden=true; moreBtn.classList.remove('on'); moreBtn.setAttribute('aria-expanded','false'); document.dispatchEvent(new CustomEvent('skribl:menu-closed')); }
moreBtn.addEventListener('click',e=>{ e.stopPropagation(); (moreMenu.hidden?openMenu:closeMenu)(); });
document.addEventListener('click',e=>{ if(!moreMenu.hidden && !e.target.closest('#moreMenu') && !e.target.closest('#moreBtn')) closeMenu(); });
// Escape closes it too. Every other dismissible surface here already does this
// — the export sheet, the tune panel, the help drawer, and Pad's own menu — so
// this menu was the only one that trapped you. It mattered less before it had
// a scrim; now a full-screen dim with no keyboard exit is a dead end.
KeyRegistry.register({surface:'flip', label:'close the overflow menu',
  keys:['Escape'], scope:()=>!moreMenu.hidden});
document.addEventListener('keydown',e=>{ if(e.key==='Escape' && !moreMenu.hidden) closeMenu(); });
// And the scrim is a click target in its own right: dimming the page implies
// tapping the dim area dismisses it, which the document handler above only
// achieves incidentally.
if(moreScrim) moreScrim.addEventListener('click',()=>closeMenu());
// Bound as early as the function exists, not near the end of the file. Even
// with bindEl() guarding each lookup, a throw ANYWHERE above here would still
// have prevented this line from running — and share doing nothing is the worst
// failure in the app, because it is the whole point of it.
// Tips toggle. Turning them back ON also forgets what has been seen, or the
// switch would silently do nothing for anyone who had already dismissed them.
(function(){
  const seg=document.getElementById('hintSeg');
  if(!seg || !window.SkriblHints) return;
  function sync(){
    const on=window.SkriblHints.isEnabled();
    seg.querySelectorAll('button').forEach(b=>b.classList.toggle('on', (b.dataset.hints==='on')===on));
    if(window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  }
  seg.addEventListener('click',e=>{
    const b=e.target.closest('button'); if(!b) return;
    if(b.dataset.hints==='on') window.SkriblHints.reset();
    else window.SkriblHints.setEnabled(false);
    sync();
  });
  if(window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  // Re-read on every open, not once at load. The stored state can change from
  // anywhere — another tab, a reset — and a switch showing the opposite of
  // what is stored is worse than no switch.
  window._skriblSyncHintToggle = sync;
  sync();
})();

bindEl('postBtn', 'click', openShareCompose);
bindEl('miSave', 'click',()=>{ closeMenu(); saveDraft(); });
bindEl('miLoad', 'click',()=>{ closeMenu(); draftInput.click(); });
/* ---- Export sheet: the Pad's shared chooser (_skribl_export.html), wired to
   Flip's existing encoders. The menu's "Export…" opens it; each format runs the
   same proven export fn (which keeps its own #flipExport progress overlay). The
   GIF background segment (Background color | Transparent) sets gifBgMode, which
   exportGIF() honours. Mirrors app.js's openExport/closeExport semantics. ---- */
let gifBgMode='color';   // 'color' | 'transparent'
let _exFmtToken=0;       // invalidates in-flight format probes when the sheet reopens
const exportOverlay=document.getElementById('exportOverlay');
const exportSheet=document.getElementById('exportSheet');
let _exCloseT=null;
function openExportSheet(){
  closeMenu();
  const single=frames.length<2;
  const vBtn=document.getElementById('exportVideo'), vDesc=document.getElementById('exportVideoDesc');
  const vTitle=vBtn?vBtn.querySelector('.export-opt-title'):null;
  if(vBtn){
    vBtn.disabled=single;
    const baseDesc = (musicData&&musicEnabled)?'Your animation, with music':'Your animation';
    if(vDesc) vDesc.textContent = single ? 'Add a page or two to export a video' : baseDesc;
    if(vTitle) vTitle.textContent='Video';
    if(!single && vTitle){
      // Async probe. _exFmtToken guards against a stale result landing after the
      // sheet was closed and reopened in a different state.
      const token = ++_exFmtToken;
      expectedVideoFormat().then(fmt=>{
        if(token!==_exFmtToken) return;
        vTitle.textContent='Video ('+fmt+')';
        if(vDesc) vDesc.textContent = baseDesc + (fmt==='MP4' ? ' · MP4 (H.264)' : ' · WebM');
      }).catch(()=>{});
    }
  }
  const gifBtn=document.getElementById('exportGif'), gifDesc=document.getElementById('exportGifDesc'), gifToggle=document.getElementById('exportGifToggle');
  // Availability is 'the server has the file', not 'it is already in memory':
  // gifenc is fetched on the click now. See _skribl_vendor.html.
  const gifReady=!!(window.gifenc && window.gifenc.GIFEncoder)
    || !!(window.SKRIBL_VENDOR && window.SKRIBL_VENDOR.gifenc);
  if(gifBtn){
    if(single){ gifBtn.disabled=true; if(gifDesc) gifDesc.textContent='Add a page or two to export a GIF'; if(gifToggle) gifToggle.hidden=true; }
    else if(!gifReady){ gifBtn.disabled=true; if(gifDesc) gifDesc.textContent='GIF encoder didn\u2019t load — try reloading'; if(gifToggle) gifToggle.hidden=true; }
    else { gifBtn.disabled=false; if(gifDesc) gifDesc.textContent='Your animation, looping · silent'; if(gifToggle) gifToggle.hidden=false; }
  }
  syncExportOptions();
  clearTimeout(_exCloseT);
  exportOverlay.hidden=false;
  requestAnimationFrame(()=>{ exportOverlay.classList.add('open');
    if(gifToggle && !gifToggle.hidden){ const seg=gifToggle.querySelector('.gif-seg'); if(seg) requestAnimationFrame(()=>positionSegSlider(seg)); }
  });
}
// Export options UI. Page numbers are 1-based and clamped on every edit, so the
// inputs can never hold a range the encoders would have to defend against —
// exRange() still clamps as a backstop, since it is the shared contract.
const exSizeSeg=document.getElementById('exportSizeSeg');
const exFromEl=document.getElementById('exportFrom');
const exToEl=document.getElementById('exportTo');
const exNoteEl=document.getElementById('exportRangeNote');
const exLoopsSeg=document.getElementById('exportLoopsSeg');
const exLoopsNote=document.getElementById('exportLoopsNote');
const exDimEl=document.getElementById('exportDimNote');
function positionSeg(seg){
  if(!seg) return;
  const a=seg.querySelector('button.on'), pill=seg.querySelector('.seg-slider');
  if(!a||!pill||!a.offsetWidth) return;
  pill.style.width=a.offsetWidth+'px';
  pill.style.transform='translateX('+(a.offsetLeft-3)+'px)';
  pill.style.opacity=1;
}
// Was hardcoded to the Size segment; the Loops segment needs the identical
// treatment, and a second copy of the same six lines is how they drift.
// Delegates to the shared tracker: a one-shot call cannot work for a control
// inside a sheet that ships `hidden`, because its buttons have no width until
// the sheet is shown, and positionSeg() bails in that case leaving the pill at
// opacity 0. Kept as a named function so every existing call site stands.
const _segTrack = (window.SkriblSegSlider && window.SkriblSegSlider.track) || null;
function positionExSeg(){
  if(_segTrack){ _segTrack(exSizeSeg); _segTrack(exLoopsSeg); _segTrack(canvasSegEl); return; }
  positionSeg(exSizeSeg); positionSeg(exLoopsSeg);
}
const canvasSegEl = document.getElementById('canvasSeg');
function syncExportOptions(){
  const n=frames.length;
  if(!exToEl||!exFromEl) return;
  if(!exTo || exTo>n) exTo=n;
  const r=exRange();
  exFrom=r.from; exTo=r.to;
  exFromEl.max=n; exToEl.max=n;
  exFromEl.value=r.from; exToEl.value=r.to;
  // Two readouts, each under the control it describes. These were one combined
  // string under Pages, which put the output dimensions — the thing Size
  // changes — beneath the wrong control, and read as a fragment once it wrapped.
  if(exDimEl){ const d=exDims(); exDimEl.textContent = d.w+' \u00d7 '+d.h; }
  if(exLoopsNote){
    const one=exLoopSeconds(), tot=one*exLoops;
    // State the resulting length, because the header badge shows ONE pass and
    // the file has always contained more than that.
    exLoopsNote.textContent = (frames.length>1)
      ? (tot.toFixed(1)+'s of video \u00b7 GIFs loop forever')
      : ('Single page \u2014 nothing to loop');
  }
  if(exLoopsSeg) exLoopsSeg.querySelectorAll('button').forEach(b=>{
    b.classList.toggle('on', +b.dataset.loops===exLoops); });
  if(exNoteEl){
    exNoteEl.textContent = (r.count===n)
      ? ('All '+n+' page'+(n===1?'':'s'))
      : (r.count+' of '+n+' page'+(n===1?'':'s'));
  }
  requestAnimationFrame(positionExSeg);
}
function onExRangeInput(){
  exFrom=parseInt(exFromEl.value,10)||1;
  exTo=parseInt(exToEl.value,10)||frames.length;
  syncExportOptions();
}
if(exFromEl) exFromEl.addEventListener('change', onExRangeInput);
if(exToEl) exToEl.addEventListener('change', onExRangeInput);
// 'change' alone means the readouts lag until the field is blurred — you type
// a page number and the stated length still describes the old range. 'input'
// refreshes the READOUTS only: syncExportOptions() clamps and rewrites the
// field values, which mid-typing would fight the user (typing "1" toward "12"
// would be rewritten to the maximum on the first keystroke). Clamping stays on
// 'change', where the user has finished.
function refreshExReadouts(){
  const r=exRange();
  if(exDimEl){ const d=exDims(); exDimEl.textContent = d.w+' \u00d7 '+d.h; }
  if(exNoteEl){
    exNoteEl.textContent = (r.count===frames.length)
      ? ('All '+frames.length+' page'+(frames.length===1?'':'s'))
      : (r.count+' of '+frames.length+' page'+(frames.length===1?'':'s'));
  }
  if(exLoopsNote && frames.length>1){
    let units=0; for(let i=r.from-1;i<=r.to-1;i++) units+=frameHold(frames[i]);
    exLoopsNote.textContent=((units/(fps||12))*exLoops).toFixed(1)+'s of video \u00b7 GIFs loop forever';
  }
}
function onExRangeLive(){
  exFrom=parseInt(exFromEl.value,10)||1;
  exTo=parseInt(exToEl.value,10)||frames.length;
  refreshExReadouts();
}
if(exFromEl) exFromEl.addEventListener('input', onExRangeLive);
if(exToEl) exToEl.addEventListener('input', onExRangeLive);
if(exSizeSeg) exSizeSeg.addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b) return;
  exSize=b.dataset.size;
  [...exSizeSeg.querySelectorAll('button')].forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  syncExportOptions();
});
if(exLoopsSeg) exLoopsSeg.addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b) return;
  // Clamp rather than trust the attribute: a stray data-loops would otherwise
  // reach the encoders and produce a file of arbitrary length.
  const n=parseInt(b.dataset.loops,10);
  exLoops = (n>=1 && n<=3) ? n : 2;
  [...exLoopsSeg.querySelectorAll('button')].forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  syncExportOptions();
});

function closeExportSheet(){ exportOverlay.classList.remove('open'); _exCloseT=setTimeout(()=>{ exportOverlay.hidden=true; },350); }
bindEl('miExport', 'click', openExportSheet);
exportOverlay.addEventListener('click', e=>{ if(!e.target.closest('.menu-sheet')) closeExportSheet(); });
KeyRegistry.register({surface:'flip', label:'close the export sheet',
  keys:['Escape'], scope:()=>!exportOverlay.hidden});
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && !exportOverlay.hidden) closeExportSheet(); });
const _exHandle = exportSheet ? exportSheet.querySelector('.menu-handle') : null;
if(_exHandle) _exHandle.addEventListener('click', e=>{ e.stopPropagation(); closeExportSheet(); });
bindEl('exportPng', 'click',()=>{ closeExportSheet(); exportPNG(); });
bindEl('exportVideo', 'click',e=>{ if(e.currentTarget.disabled) return; closeExportSheet(); exportVideo(); });
bindEl('exportGif', 'click',e=>{ if(e.currentTarget.disabled) return; closeExportSheet(); exportGIF(); });
(function(){ const gifToggle=document.getElementById('exportGifToggle'); if(!gifToggle) return;
  gifToggle.querySelectorAll('.gif-seg-btn').forEach(btn=>{ btn.addEventListener('click',()=>{ gifBgMode=btn.getAttribute('data-gif-bg')||'color'; gifToggle.querySelectorAll('.gif-seg-btn').forEach(b=>b.classList.toggle('active', b===btn)); }); });
  const gifSeg=gifToggle.querySelector('.gif-seg'); if(gifSeg) attachSegSlider(gifSeg);
})();

/* ---- move artwork ---------------------------------------------------------
 * Translating a page is exactly reversible, so undo stores the INVERSE OFFSET
 * rather than a snapshot of the strokes. A 62-page animation would otherwise
 * cost a full copy of every affected page per move; an offset costs two
 * numbers, and it cannot drift because applying -dx,-dy is the exact inverse
 * of +dx,+dy on the same points.
 *
 * actionLog records the ORDER of undoable actions so a move and a stroke can
 * interleave. Without it, undo after "draw, move" would pop the stroke and
 * leave the move — undoing something the user did not do last.
 */
let actionLog = [];          // 'stroke' | {type:'move', idxs, dx, dy}
const MOVE_UNDO_LIMIT = 60;

function translateFrames(idxs, dx, dy){
  if(!dx && !dy) return;
  for(const i of idxs){
    const f = frames[i]; if(!f) continue;
    for(const pt of f.strokes){ pt.x += dx; pt.y += dy; }
  }
}
/* ---------- v227: Select — marquee a subset of THIS page, then drag it ------
   Ported from Pad's SkriblSelectTool (editor_draw.js), which v219 left in place
   with its button removed. The geometry is the shared lib/selection.js; what is
   Flip's is where the points live and how the operation is undone.

   WHY IT IS SAFE HERE AND WAS NOT ON PAD. v219 pulled Select from Pad because
   Pad records a timed performance: moving points that are already recorded made
   replay draw a stroke at its NEW position at its OLD timestamp. Flip has no
   timeline within a page — playback reveals strokes in index order — so moving
   a point changes only where it is, never when. Flip's own Move mode has
   translated whole pages this way since v213.

   UNDO IS AN OPERATION, NOT A SNAPSHOT, and that is the whole reason this port
   is short. Pad had to clone the selected point objects BEFORE snapshotting or
   `strokes.slice()` aliased them and Ctrl+Z silently restored the moved
   position. Flip's actionLog stores what was done, so undoing a selection move
   is the same translation with the sign flipped — there is nothing to alias. */

/* Translate ONLY the points the selection covers. translateFrames() moves whole
   pages; this is the same operation narrowed to index ranges, and it is what
   both the live drag and undo/redo go through so they cannot disagree. */
function translateSpans(frameIdx, spans, dx, dy){
  if(!dx && !dy) return;
  const f = frames[frameIdx]; if(!f) return;
  for(const [a, b] of spans){
    for(let i = a; i < b && i < f.strokes.length; i++){
      f.strokes[i].x += dx; f.strokes[i].y += dy;
    }
  }
}

/* Handles are sized in SCREEN pixels and drawn in canvas units, so they stay
   finger-sized whatever the canvas resolution or the zoom. pos() already uses
   this ratio to turn a client point into a canvas point. */
function selCanvasPx(px){
  const r = pad.getBoundingClientRect();
  return r.width ? px * CW / r.width : px;
}

function selHandles(){
  const b = selBounds(); if(!b) return null;
  const m = selCanvasPx(6);
  const x0 = b.x - m, y0 = b.y - m, x1 = b.x + b.w + m, y1 = b.y + b.h + m;
  return {
    box: { x:x0, y:y0, w:x1 - x0, h:y1 - y0 },
    // Corners only, and the scale they drive is UNIFORM. A point carries one
    // scalar `size`, so a non-uniform scale has no honest answer for stroke
    // weight -- widen a drawing horizontally and the strokes would have to be
    // thicker on the verticals than the horizontals, which one number per point
    // cannot express. Edge handles are left out rather than shipped lying.
    corners: [ { id:'nw', x:x0, y:y0 }, { id:'ne', x:x1, y:y0 },
               { id:'se', x:x1, y:y1 }, { id:'sw', x:x0, y:y1 } ],
    rotate: { x:(x0 + x1) / 2, y:y0 - selCanvasPx(26) },
    centre: { x:(x0 + x1) / 2, y:(y0 + y1) / 2 }
  };
}
function selHandleAt(pt){
  const h = selHandles(); if(!h) return null;
  const r = selCanvasPx(15);           // generous: a corner square is 5px drawn
  for(const c of h.corners){
    if(Math.abs(pt.x - c.x) <= r && Math.abs(pt.y - c.y) <= r) return { kind:'scale', corner:c, h };
  }
  if(Math.hypot(pt.x - h.rotate.x, pt.y - h.rotate.y) <= r) return { kind:'rotate', h };
  return null;
}

/* One gesture's worth of originals. Captured on pointerdown and thrown away on
   release, so nothing here has to survive a page change or a save. */
function selCapture(){
  const f = frame(); selSnap = [];
  for(const [a, b] of selSpans){
    for(let i = a; i < b && i < f.strokes.length; i++){
      const p = f.strokes[i];
      selSnap.push({ i, x:p.x, y:p.y, size:p.size });
    }
  }
}
/* Rotate about the pivot, then scale about it, writing from the snapshot. `size`
   is multiplied by the scale so a shrunk selection gets thinner strokes rather
   than the same weight on smaller artwork -- the per-point `size` field is what
   makes that possible, and it is why scale is worth having at all. */
function selApply(scale, angle){
  if(!selSnap || !selPivot) return;
  const f = frame(), cos = Math.cos(angle), sin = Math.sin(angle);
  for(const o of selSnap){
    const p = f.strokes[o.i]; if(!p) continue;
    const dx = o.x - selPivot.x, dy = o.y - selPivot.y;
    p.x = selPivot.x + (dx * cos - dy * sin) * scale;
    p.y = selPivot.y + (dx * sin + dy * cos) * scale;
    if(o.size != null) p.size = o.size * scale;
  }
}
function selSnapAfter(){
  const f = frame();
  return selSnap.map(o => { const p = f.strokes[o.i];
    return { i:o.i, x:p.x, y:p.y, size:p.size }; });
}
/* Restores exact coordinates rather than inverting the transform. A translate is
   exact under negation, which is why selmove stores dx/dy and flips the sign;
   a scale is not -- dividing by a ratio does not always land back on the
   original float, and repeated undo/redo would drift. Spans are one or two
   strokes, so the snapshot costs tens of points. */
function selRestore(pts){
  const f = frame();
  for(const o of pts){ const p = f.strokes[o.i]; if(!p) continue;
    p.x = o.x; p.y = o.y; if(o.size != null) p.size = o.size; }
}

/* ---------- v229: mirror, duplicate, cut and paste -------------------------
   All four rewrite one page's strokes wholesale rather than editing in place,
   and all four share ONE undo shape: a before/after pair of that page's strokes
   and strokeGroups.

   selmove negates its dx/dy and a transform restores coordinates, because both
   leave the arrays the same length. These do not: duplicate appends groups, cut
   splices them out, and paste appends. Undoing an index-range edit whose indices
   have since moved is exactly the class of bug this codebase keeps finding, so
   the entry carries the arrays instead of the arithmetic. One page's points is
   the same order of magnitude the redo stack already holds. */
function selFrameSnap(){
  const f = frame();
  return { strokes: f.strokes.map(p => Object.assign({}, p)),
           groups: f.strokeGroups.slice() };
}
function selFrameRestore(i, snap){
  const f = frames[i]; if(!f) return;
  f.strokes = snap.strokes.map(p => Object.assign({}, p));
  f.strokeGroups = snap.groups.slice();
}
function selCommitFrame(before, label){
  redoStack.length = 0;
  noteAction({ type:'selframe', idx, before, after: selFrameSnap(), label });
  refreshThumb(idx); scheduleSave(); updateToolState();
}

/* Mirror about the selection's own centre, so the artwork flips where it sits
   rather than jumping across the page. `size` is untouched: a reflection does
   not change how thick a line is, only which way it points. */
function selMirror(axis){
  if(!selSpans.length) return;
  const b = selBounds(); if(!b) return;
  const before = selFrameSnap();
  const cx = b.x + b.w / 2, cy = b.y + b.h / 2, f = frame();
  for(const [a, z] of selSpans){
    for(let i = a; i < z && i < f.strokes.length; i++){
      const p = f.strokes[i];
      if(axis === 'h') p.x = 2 * cx - p.x; else p.y = 2 * cy - p.y;
    }
  }
  selCommitFrame(before, 'Flip');
  chip(axis === 'h' ? 'Flipped left to right' : 'Flipped top to bottom');
  selRender(null);
}

/* The selected strokes, as whole groups, in document order. Shared by duplicate
   and cut so the two cannot disagree about what "the selection" is. */
function selExtract(){
  const f = frame(), out = [];
  for(const [a, z] of selSpans){
    const pts = [];
    for(let i = a; i < z && i < f.strokes.length; i++) pts.push(Object.assign({}, f.strokes[i]));
    if(pts.length) out.push(pts);
  }
  return out;
}
/* Where a run of appended groups lands, so the copy can be selected immediately.
   Appending keeps the runs contiguous at the end of the array, which is what
   makes these spans a simple walk. */
function selSpansForAppended(runs){
  const f = frame();
  let at = f.strokes.length - runs.reduce((n, r) => n + r.length, 0);
  return runs.map(r => { const s = [at, at + r.length]; at += r.length; return s; });
}
function selAppend(runs){
  const f = frame();
  for(const pts of runs){
    for(const p of pts) f.strokes.push(Object.assign({}, p));
    f.strokeGroups.push(pts.length);
  }
}

function selDuplicate(){
  if(!selSpans.length) return;
  const before = selFrameSnap();
  const off = selCanvasPx(12);
  const runs = selExtract().map(r => r.map(p => Object.assign({}, p, { x:p.x + off, y:p.y + off })));
  selAppend(runs);
  // Select the COPY, not the original: the next thing you do after duplicating
  // is move the new one, and leaving the original selected would move that
  // instead — silently, because the two are sitting on top of each other.
  selSpans = selSpansForAppended(runs);
  selCommitFrame(before, 'Duplicate');
  chip('Duplicated');
  selRender(null);
}

/* Cut removes AND remembers. Without the clipboard this would be Delete wearing
   the wrong name — and a flipbook's real use for cut is taking artwork off one
   page and putting it on the next, which needs somewhere for it to wait.
   (selClipboard is declared with the early state; syncSelBar() reads it and
   setTool() reaches syncSelBar() during init.) */
function selCut(){
  if(!selSpans.length) return;
  const before = selFrameSnap();
  selClipboard = selExtract();
  const f = frame();
  // Back to front: splicing a lower range first would shift every range above
  // it, and the ranges came from a walk over the array as it was.
  const spans = selSpans.slice().sort((a, b) => b[0] - a[0]);
  for(const [a, z] of spans){
    const n = z - a;
    f.strokes.splice(a, n);
    // strokeGroups is a run-length list, not indices: find the run that starts
    // at `a` by walking the cumulative count.
    let cum = 0;
    for(let g = 0; g < f.strokeGroups.length; g++){
      if(cum === a && f.strokeGroups[g] === n){ f.strokeGroups.splice(g, 1); break; }
      cum += f.strokeGroups[g];
    }
  }
  selSpans = []; selRect = null;
  selCommitFrame(before, 'Cut');
  syncSelBar();
  chip('Cut — paste it on any page');
  selRender(null);
}
function selPaste(){
  if(!selClipboard || !selClipboard.length) return;
  const before = selFrameSnap();
  selAppend(selClipboard);
  selSpans = selSpansForAppended(selClipboard);
  selCommitFrame(before, 'Paste');
  chip('Pasted');
  selRender(null);
}

/* Shown exactly while there is a selection, and it REPLACES the page bar — the
   pattern setMoveMode() established. Five more actions do not fit on a 320px
   phone as extra chrome; they fit as a different job for the same row. */
function syncSelBar(){
  const on = selSpans.length > 0;
  const pb = document.getElementById('pagebar'), sb = document.getElementById('selbar');
  // Move mode owns the row when it is active, and it is mutually exclusive with
  // Select — so never take the row from it.
  if(moveMode){ if(sb) sb.hidden = true; return; }
  if(sb) sb.hidden = !on;
  if(pb) pb.hidden = on;
  const who = document.getElementById('sbWho');
  if(who && on) who.textContent = selSpans.length === 1 ? '1 stroke' : selSpans.length + ' strokes';
  const paste = document.getElementById('sbPaste');
  // Paste is hidden until there is something to paste, rather than shown
  // disabled: a disabled control on a bar this tight is a cell of dead width.
  if(paste) paste.hidden = !(selClipboard && selClipboard.length);
}

function selBounds(){
  const f = frame();
  if(!selSpans.length || !window.SkriblSelect) return null;
  const pts = [];
  for(const [a, b] of selSpans){
    for(let i = a; i < b && i < f.strokes.length; i++) pts.push(f.strokes[i]);
  }
  if(!pts.length) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for(const p of pts){
    if(p.x < minX) minX = p.x; if(p.y < minY) minY = p.y;
    if(p.x > maxX) maxX = p.x; if(p.y > maxY) maxY = p.y;
  }
  return { x:minX, y:minY, w:maxX - minX, h:maxY - minY };
}

/* The dashed frame is painted straight onto the pad AFTER render(), because
   render() clears the canvas. Every path that changes the selection therefore
   goes through selRender() rather than render(), the same shape Pad's
   selRepaint() has. */
function selOutline(r, dashed){
  if(!r) return;
  ctx.save();
  ctx.setLineDash(dashed ? [6, 5] : []);
  ctx.strokeStyle = 'rgba(124,92,255,0.95)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(r.x, r.y, r.w, r.h);
  ctx.restore();
}
/* The frame, its four corner grips and the rotate grip. Painted onto the pad
   after render(), which clears the canvas — so every path that changes the
   selection goes through selRender() rather than render(). */
function selChrome(){
  const h = selHandles(); if(!h) return;
  selOutline(h.box, true);
  const s = selCanvasPx(5), lw = selCanvasPx(1.5);
  ctx.save();
  ctx.strokeStyle = 'rgba(124,92,255,0.95)';
  ctx.fillStyle = '#06070a';
  ctx.lineWidth = lw;
  for(const c of h.corners){
    ctx.beginPath(); ctx.rect(c.x - s, c.y - s, s * 2, s * 2);
    ctx.fill(); ctx.stroke();
  }
  // The rotate grip sits above the box on a short stem, so it reads as attached
  // to the selection rather than as a fifth corner floating near it.
  ctx.beginPath();
  ctx.moveTo(h.centre.x, h.box.y); ctx.lineTo(h.rotate.x, h.rotate.y + s);
  ctx.stroke();
  ctx.beginPath(); ctx.arc(h.rotate.x, h.rotate.y, s + selCanvasPx(0.5), 0, Math.PI * 2);
  ctx.fill(); ctx.stroke();
  ctx.restore();
}
function selRender(marquee){
  render();
  if(marquee){ selOutline(marquee, true); return; }
  if(selSpans.length) selChrome();
}
function selClear(quiet){
  const had = selSpans.length > 0;
  selSpans = []; selRect = null; selOrigin = null; selDx = selDy = 0;
  selMarqueeFrom = null; selMoveFrom = null;
  selMode = null; selSnap = null; selPivot = null; selRef = null;
  if(typeof syncSelBar === 'function') syncSelBar();
  // Only repaint if there was something to erase. setTool() calls this on EVERY
  // tool change, and repainting the page to remove a marquee that was never
  // there is pure cost — the same guard Pad's selClear() carries.
  if(had && !quiet) render();
}

function selDown(pt){
  // Handles are tested FIRST and they sit outside the bounds box, so an
  // inside-the-box test run first would never reach them.
  const hit = selSpans.length ? selHandleAt(pt) : null;
  if(hit){
    selCapture();
    if(hit.kind === 'scale'){
      selMode = 'scale';
      // Pivot is the corner diagonally opposite the one being dragged, so the
      // rest of the selection stays put and the drag reads as pulling that
      // corner rather than as the whole thing sliding.
      const opp = { nw:'se', ne:'sw', se:'nw', sw:'ne' }[hit.corner.id];
      selPivot = hit.h.corners.find(c => c.id === opp);
      selRef = Math.hypot(hit.corner.x - selPivot.x, hit.corner.y - selPivot.y) || 1;
    } else {
      selMode = 'rotate';
      selPivot = hit.h.centre;
      selRef = Math.atan2(pt.y - selPivot.y, pt.x - selPivot.x);
    }
    return;
  }
  const b = selBounds();
  // Inside the current selection: start a move. Anywhere else: start a new
  // marquee, which DISCARDS the old selection — a stray tap keeping a selection
  // the user has visually moved on from is worse than making them re-pick.
  if(b && pt.x >= b.x - 8 && pt.x <= b.x + b.w + 8 &&
          pt.y >= b.y - 8 && pt.y <= b.y + b.h + 8){
    selMode = 'move';
    selMoveFrom = { x:pt.x, y:pt.y };
    selMarqueeFrom = null;
    selDx = selDy = 0;
  } else {
    selMode = 'marquee';
    selMarqueeFrom = { x:pt.x, y:pt.y };
    selMoveFrom = null;
    selSpans = []; selRect = null; selDx = selDy = 0;
    render();
  }
}
function selMove(pt){
  if(selMode === 'scale'){
    // 0.05 rather than 0 — a selection dragged through its own pivot would
    // otherwise collapse to a point with no way back, since every subsequent
    // ratio multiplies zero.
    const d = Math.hypot(pt.x - selPivot.x, pt.y - selPivot.y);
    selApply(Math.max(0.05, d / selRef), 0);
    selRender(null);
    return;
  }
  if(selMode === 'rotate'){
    selApply(1, Math.atan2(pt.y - selPivot.y, pt.x - selPivot.x) - selRef);
    selRender(null);
    return;
  }
  if(selMarqueeFrom){
    selRender(window.SkriblSelect
      ? SkriblSelect.rect(selMarqueeFrom, pt)
      : null);
    return;
  }
  if(selMoveFrom && selSpans.length){
    // Translate by the DELTA since the last move event, so the points carry the
    // running position and nothing has to be restored from an origin copy.
    const ndx = pt.x - selMoveFrom.x, ndy = pt.y - selMoveFrom.y;
    translateSpans(idx, selSpans, ndx - selDx, ndy - selDy);
    selDx = ndx; selDy = ndy;
    selRender(null);
  }
}
function selUp(pt){
  if(selMode === 'scale' || selMode === 'rotate'){
    const before = selSnap, after = selSnapAfter();
    selMode = null; selSnap = null; selPivot = null; selRef = null;
    const changed = after.some((a, i) =>
      a.x !== before[i].x || a.y !== before[i].y || a.size !== before[i].size);
    if(changed){
      redoStack.length = 0;
      noteAction({ type:'seltransform', idx, before, after });
      refreshThumb(idx); scheduleSave(); updateToolState();
    }
    selRender(null);
    return;
  }
  if(selMarqueeFrom){
    const r = window.SkriblSelect ? SkriblSelect.rect(selMarqueeFrom, pt) : null;
    selMarqueeFrom = null;
    const f = frame();
    if(r && window.SkriblSelect){
      // groupsIn returns GROUP indices; spans turns those into [start, end)
      // ranges over `strokes`. Whole strokes, never half of one — a marquee
      // clipping a stroke in the middle would move a fragment and leave the
      // rest, which is not what a box round some artwork means.
      const groups = SkriblSelect.groupsIn(f.strokes, f.strokeGroups, r);
      selSpans = groups.length ? SkriblSelect.spans(f.strokeGroups, groups) : [];
      selRect = selSpans.length ? r : null;
    }
    syncSelBar();
    selRender(null);
    if(selSpans.length) chip(selSpans.length === 1 ? '1 stroke selected'
                                                  : selSpans.length + ' strokes selected');
    return;
  }
  if(selMoveFrom){
    selMoveFrom = null;
    if(selDx || selDy){
      redoStack.length = 0;
      noteAction({ type:'selmove', idx, spans: selSpans.map(s => s.slice()),
                   dx: selDx, dy: selDy });
      refreshThumb(idx); scheduleSave(); updateToolState();
    }
    selDx = selDy = 0;
    selRender(null);
  }
}

function noteAction(entry){
  actionLog.push(entry);
  if(actionLog.length > MOVE_UNDO_LIMIT * 4) actionLog.shift();
}

function undoStroke(){
  invalidateClearUndo();
  if(playing) return;
  // A move is undone only if it was the LAST thing done. Popping strokes past
  // a move would silently leave the move in place.
  if(actionLog.length && typeof actionLog[actionLog.length-1] === 'object'){
    const m = actionLog.pop();
    // A selection move touches index ranges on ONE page; a Move-mode move
    // touches whole pages. The object branch used to assume the second, so
    // undoing a selection drag would have translated the entire page.
    if(m.type === 'selmove'){
      translateSpans(m.idx, m.spans, -m.dx, -m.dy);
      redoStack.push(m);
      chip('Selection move undone');
      render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
      return;
    }
    // A transform restores COORDINATES rather than inverting itself. Negating a
    // translate is exact; dividing by a scale ratio is not, and repeated
    // undo/redo would walk the artwork away from where it started.
    if(m.type === 'selframe'){
      if(m.idx !== idx) go(m.idx);
      selFrameRestore(m.idx, m.before);
      selSpans = []; selRect = null; syncSelBar();
      redoStack.push(m);
      chip((m.label || 'Edit') + ' undone');
      render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
      return;
    }
    if(m.type === 'seltransform'){
      const at = idx; if(m.idx !== at) go(m.idx);
      selRestore(m.before);
      redoStack.push(m);
      chip('Transform undone');
      render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
      return;
    }
    translateFrames(m.idxs, -m.dx, -m.dy);
    // A move joined the undo history, so it owes a redo. Without this the
    // button stayed stroke-only: undoing a move left redoStack holding some
    // older stroke, so pressing Redo resurrected a stroke from two operations
    // ago instead of restoring the move.
    redoStack.push(m);
    // Named because it is NOT a stroke. Undo is trusted when it is obvious what
    // it just did, and a page translation vanishing is far less legible than a
    // stroke vanishing — especially when it undoes across several pages.
    chip(m.idxs.length > 1 ? 'Move undone on ' + m.idxs.length + ' pages' : 'Move undone');
    render(); m.idxs.forEach(i=>refreshThumb(i)); updateToolState(); scheduleSave();
    return;
  }
  const f = frame(); if(!f.strokeGroups.length) return;
  if(actionLog.length) actionLog.pop();
  const n = f.strokeGroups.pop();
  const removed = f.strokes.splice(f.strokes.length - n, n);
  redoStack.push({ pts: removed, count: n });
  render(); refreshThumb(idx); updateToolState(); scheduleSave();
}
function redoStroke(){
  invalidateClearUndo();
  if(playing || !redoStack.length) return;
  if(typeof redoStack[redoStack.length-1] === 'object'
     && redoStack[redoStack.length-1].type === 'selframe'){
    const m = redoStack.pop();
    if(m.idx !== idx) go(m.idx);
    selFrameRestore(m.idx, m.after);
    selSpans = []; selRect = null; syncSelBar();
    actionLog.push(m);
    chip((m.label || 'Edit') + ' redone');
    render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
    return;
  }
  if(typeof redoStack[redoStack.length-1] === 'object'
     && redoStack[redoStack.length-1].type === 'seltransform'){
    const m = redoStack.pop();
    if(m.idx !== idx) go(m.idx);
    selRestore(m.after);
    actionLog.push(m);
    chip('Transform redone');
    render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
    return;
  }
  if(typeof redoStack[redoStack.length-1] === 'object'
     && redoStack[redoStack.length-1].type === 'selmove'){
    const m = redoStack.pop();
    translateSpans(m.idx, m.spans, m.dx, m.dy);
    actionLog.push(m);
    chip('Selection move redone');
    render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
    return;
  }
  if(typeof redoStack[redoStack.length-1] === 'object'
     && redoStack[redoStack.length-1].type === 'move'){
    const m = redoStack.pop();
    translateFrames(m.idxs, m.dx, m.dy);
    actionLog.push(m);            // back on the history it came off
    chip(m.idxs.length > 1 ? 'Move redone on ' + m.idxs.length + ' pages' : 'Move redone');
    render(); m.idxs.forEach(i=>refreshThumb(i)); updateToolState(); scheduleSave();
    return;
  }
  const f = frame(); const item = redoStack.pop();
  for(const p of item.pts) f.strokes.push(p);
  f.strokeGroups.push(item.count);
  render(); refreshThumb(idx); updateToolState(); scheduleSave();
}
document.querySelectorAll('#toolGroup .tool-btn').forEach(b=>b.addEventListener('click',()=>{
  if(playing) return;
  // The chevron is a .tool-btn so it inherits the pill's shape, but it is NOT a
  // tool: it carries no data-tool. Without this guard clicking it called
  // setTool(undefined), which the clamp turned into setTool('pen') — so opening
  // the tray silently switched you back to the pen.
  if(!b.dataset.tool) return;
  setTool(b.dataset.tool);
  const pop=document.getElementById('shapePop');
  if(pop) pop.hidden = (b.dataset.tool!=='shape') ? true : !pop.hidden;
}));
(function shapePopDismiss(){
  const pop=document.getElementById('shapePop');
  if(!pop) return;
  pop.addEventListener('click',e=>{ if(e.target.closest('[data-shape]')) pop.hidden=true; });
  document.addEventListener('click',e=>{
    if(pop.hidden) return;
    if(e.target.closest('#shapePop')||e.target.closest('#shapeToolBtn')) return;
    pop.hidden=true;
  });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&!pop.hidden) pop.hidden=true; });
})();
/* ---- move-artwork mode ----------------------------------------------------
 * Enter from the page bar, drag on the canvas, Done commits.
 *
 * The offset is applied to a WORKING COPY of the original points, not
 * accumulated onto the live ones: accumulating would round-trip the
 * coordinates on every pointer event and drift the drawing a fraction at a
 * time over a long drag. Reset is then simply "offset zero".
 */
/* Declared with the other early state; see the note there. */

function moveTargets(){
  if(moveScope === 'after'){
    const out = []; for(let i = idx; i < frames.length; i++) out.push(i); return out;
  }
  return [idx];
}
function captureMoveOrigin(){
  // EVERY page, ONCE, for the life of the session — not just the pages
  // currently in scope. The old version captured only the target set and was
  // called again whenever scope changed, which re-read points that had already
  // been translated by the live preview: the canonical original and the live
  // preview are the same array only while the offset is zero. Switching scope
  // after a +40 drag therefore captured `original + 40` as the new origin and
  // applied +40 to it, landing the current page on +80 while pages newly in
  // scope got +40 — the two no longer sharing a translation, and the readout
  // still saying 40. A session-wide snapshot cannot express that bug: there is
  // exactly one origin per page and it is never re-derived from a preview.
  moveOrigin = new Map();
  for(let i = 0; i < frames.length; i++){
    moveOrigin.set(i, frames[i].strokes.map(p => ({x:p.x, y:p.y})));
  }
}
function syncMoveLabel(){
  // Both the label and the filmstrip highlight read moveTargets(), the same
  // function the transform itself uses, so neither can drift from what is
  // actually moving. A scope preview that disagrees with the operation is
  // worse than none.
  const who = document.getElementById('mbWho');
  const t = moveMode ? moveTargets() : [];
  if(who && t.length){
    who.textContent = t.length === 1
      ? 'Page ' + (t[0] + 1)
      : 'Pages ' + (t[0] + 1) + '\u2013' + (t[t.length - 1] + 1);
  }
  // The strip shows scope far better than any label can, and costs no width in
  // a bar that is already tight at 320px.
  const set = new Set(t);
  strip.querySelectorAll('.frame').forEach((el, i) => {
    el.classList.toggle('in-scope', moveMode && set.has(i));
  });
}
function applyMoveOffset(){
  if(!moveOrigin) return;
  const targets = new Set(moveTargets());
  for(const [i, pts] of moveOrigin){
    const f = frames[i]; if(!f) continue;
    // Pages OUT of scope are restored to their originals rather than left
    // wherever a previous scope setting put them, so narrowing the scope is as
    // exact as widening it.
    const dx = targets.has(i) ? moveDx : 0;
    const dy = targets.has(i) ? moveDy : 0;
    for(let k = 0; k < f.strokes.length && k < pts.length; k++){
      f.strokes[k].x = pts[k].x + dx;
      f.strokes[k].y = pts[k].y + dy;
    }
  }
  const off = document.getElementById('mbOffset');
  if(off) off.textContent = Math.round(moveDx) + ', ' + Math.round(moveDy);
  syncMoveLabel();
  render();
}
function setMoveMode(on){
  if(on && playing) return;
  moveMode = on;
  moveDx = moveDy = 0; moveDragging = false;
  const stage = document.querySelector('.flip-stage');
  if(stage){ stage.classList.toggle('moving', on); stage.classList.remove('dragging'); }
  // Set inline, because setTool() sets pad.style.cursor='none' inline for the
  // custom brush cursor and an inline style beats any stylesheet rule however
  // specific. '' hands control back to the CSS when leaving.
  pad.style.cursor = on ? 'grab' : 'none';
  const pb = document.getElementById('pagebar'), mb = document.getElementById('movebar');
  if(pb) pb.hidden = on;
  if(mb) mb.hidden = !on;
  // Leaving the mode with the entry box open would strand an input over a bar
  // that is no longer there — and its blur handler would then commit into a
  // move that had already ended.
  if(typeof closeOffsetEntry === 'function') closeOffsetEntry();
  document.body.classList.toggle('move-locked', on);
  syncMoveLabel();
  if(on){
    captureMoveOrigin();
    const off = document.getElementById('mbOffset'); if(off) off.textContent = '0, 0';
    if(window.SkriblSegSlider) window.SkriblSegSlider.track(document.getElementById('mbScope'));
    // Onion is what makes a move judgeable — you are lining this page up
    // against the one beneath. Say so rather than silently forcing it on.
    if(window.SkriblHints){
      window.SkriblHints.show('move-artwork', onion
        ? 'Drag anywhere to move this page\u2019s drawing. The faint page beneath is your reference.'
        : 'Drag anywhere to move this page\u2019s drawing. Turn on the stacked-sheets button to see the page beneath while you line it up.');
    }
  } else {
    moveOrigin = null;
  }
  updateToolState();
}
function commitMove(){
  if(!moveMode) return;
  const dx = moveDx, dy = moveDy, idxs = moveTargets();
  if(dx || dy){
    redoStack.length = 0;
    noteAction({ type:'move', idxs, dx, dy });
    idxs.forEach(i => refreshThumb(i));
    scheduleSave();
  }
  setMoveMode(false);
}
function cancelMove(){
  if(!moveMode) return;
  moveDx = moveDy = 0; applyMoveOffset();
  setMoveMode(false);
}

bindEl('pbArt', 'click', ()=>{ disarmAll(); setMoveMode(!moveMode); });
bindEl('mbDone', 'click', ()=>{ commitMove(); });
bindEl('mbReset', 'click', ()=>{ moveDx = moveDy = 0; applyMoveOffset(); });
(function(){
  const seg = document.getElementById('mbScope');
  if(!seg) return;
  seg.addEventListener('click', e=>{
    const b = e.target.closest('button'); if(!b) return;
    moveScope = b.dataset.scope === 'after' ? 'after' : 'one';
    seg.querySelectorAll('button').forEach(x=>x.classList.toggle('on', x === b));
    if(window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
    // No re-capture. The snapshot already holds every page's original, so
    // changing scope only changes which of them receive the offset; pages
    // leaving the set are restored by applyMoveOffset itself.
    applyMoveOffset();
  });
})();
// Escape cancels rather than commits. A drag you did not mean is undone by
// leaving, which is what Escape means everywhere else in this app.
KeyRegistry.register({surface:'flip', label:'cancel Move artwork',
  keys:['Escape'], scope:()=>moveMode});
document.addEventListener('keydown', e=>{ if(e.key === 'Escape' && moveMode) cancelMove(); });
bindEl('sbFlipH', 'click', ()=>{ if(!playing) selMirror('h'); });
bindEl('sbFlipV', 'click', ()=>{ if(!playing) selMirror('v'); });
bindEl('sbDup',   'click', ()=>{ if(!playing) selDuplicate(); });
bindEl('sbCut',   'click', ()=>{ if(!playing) selCut(); });
bindEl('sbPaste', 'click', ()=>{ if(!playing) selPaste(); });
// Done drops the selection but stays on the tool: the common next move is to
// pick something else, not to go back to the pen.
bindEl('sbDone',  'click', ()=>{ selClear(); selRender(null); });
// The bar borrows the page bar's row, so entering Move mode has to take it back
// — otherwise both would claim the row and the last one to render would win.
if(typeof setMoveMode === 'function'){
  const _setMoveMode = setMoveMode;
  setMoveMode = function(on){ if(on) selClear(); _setMoveMode(on); syncSelBar(); };
}
// The first sync happens on load, NOT here. syncSelBar() reads moveMode, whose
// `let` runs later in this file — calling it at this line threw "Cannot access
// 'moveMode' before initialization" and killed everything after it, which is the
// second time this file's scattered `let` state has done exactly that. Anything
// that touches state declared further down belongs in the load handler.


/* ---- typing an exact offset ----------------------------------------------
 * Dragging answers "about there"; typing answers "exactly 40 across". Both
 * write the same two numbers, so this needs no new state: moveDx/moveDy are
 * already absolute offsets from the captured origin, and applyMoveOffset()
 * recomputes from that origin every time. Setting them directly is therefore
 * exactly equivalent to having dragged to that position — the same Reset, the
 * same Done, and the same single inverse-offset undo entry.
 */
function closeOffsetEntry(){
  const view = document.getElementById('mbOffset');
  const input = document.getElementById('mbOffsetInput');
  if(!view || !input || input.hidden) return;
  input.hidden = true; view.hidden = false;
}
function parseOffsetEntry(text){
  // "40, -12" / "40 -12" / "40,-12". Rejects anything else rather than
  // salvaging a number out of it: a half-understood entry that silently moves
  // the drawing somewhere unintended is worse than no move at all.
  const m = String(text).match(/^\s*(-?\d+(?:\.\d+)?)\s*(?:,|\s)\s*(-?\d+(?:\.\d+)?)\s*$/);
  return m ? { x: parseFloat(m[1]), y: parseFloat(m[2]) } : null;
}
(function(){
  const view = document.getElementById('mbOffset');
  const input = document.getElementById('mbOffsetInput');
  if(!view || !input) return;

  function openEntry(){
    if(!moveMode || playing) return;
    input.value = Math.round(moveDx) + ', ' + Math.round(moveDy);
    view.hidden = true; input.hidden = false;
    input.focus(); input.select();
  }
  function commitEntry(){
    if(input.hidden) return;
    const v = parseOffsetEntry(input.value);
    if(v){
      moveDx = v.x; moveDy = v.y;
      applyMoveOffset();                      // rewrites the readout itself
    } else if(input.value.trim() !== ''){
      // Say so rather than silently keeping the old offset.
      input.classList.add('bad');
      setTimeout(()=>input.classList.remove('bad'), 700);
    }
    closeOffsetEntry();
  }

  view.addEventListener('click', openEntry);
  input.addEventListener('keydown', e=>{
    if(e.key === 'Enter'){ e.preventDefault(); commitEntry(); }
    else if(e.key === 'Escape'){
      // stopPropagation, or the document-level Escape handler above cancels the
      // whole move — abandoning a typo would throw away the drag as well.
      e.preventDefault(); e.stopPropagation();
      closeOffsetEntry();
    }
  });
  input.addEventListener('blur', commitEntry);
})();

bindEl('undo', 'click',()=>{ disarmAll(); undoStroke(); });
bindEl('redo', 'click',()=>{ disarmAll(); redoStroke(); });
/* Delete-all lives in the draw menu now; destructive → same two-tap arm as frame delete. */
// CLEAR SEMANTICS (review #5/#9), stated once here because the old code did
// neither thing consistently: **Clear removes PAGES ONLY.** Music, background
// image, colour, fps and all media settings are deliberately untouched, which is
// what the live editor already did — the bug was that it then DELETED the
// autosave, so a reload silently lost media that had visibly survived the clear.
// Clear now rewrites the autosave instead, so persisted state always matches what
// is on screen. The snapshot is therefore frames-only BY DESIGN, and named for
// what it holds rather than "full animation", which it never was.
let clearFramesBackup=null;
// Review #4: the backup used to survive any amount of later work, so undoing a
// clear could silently destroy a whole new animation. Every mutation that changes
// page content or order now drops it.
function invalidateClearUndo(){
  if(!clearFramesBackup) return;
  clearFramesBackup=null;
  const cu=document.getElementById('clearUndo'); if(cu) cu.disabled=true;
}
bindEl('clear', 'click',e=>{
  if(playing) return;
  const empty = frames.length===1 && frames[0].strokes.length===0;
  if(empty) return;                                  // nothing to delete
  const lbl=document.getElementById('clearLabel');
  if(!armedClear){ disarmAll(); armedClear=true; e.currentTarget.classList.add('armed'); if(lbl) lbl.textContent='Tap again to clear pages'; e.currentTarget.title='Tap again to delete all pages'; return; }
  armedClear=false; e.currentTarget.classList.remove('armed'); if(lbl) lbl.textContent='Clear all pages'; e.currentTarget.title='Delete all pages (keeps music and background)';
  clearFramesBackup = { frames: frames.map(deepCopy), idx: idx };   // pages only — see note above
  frames=[newFrame()]; idx=0; redoStack.length=0;
  buildStrip(); render(); updateToolState();
  scheduleSave();   // persist the cleared state instead of deleting the draft
  const cu=document.getElementById('clearUndo'); if(cu) cu.disabled=false;
});
bindEl('clearUndo', 'click',()=>{
  if(!clearFramesBackup) return;
  disarmAll();
  frames = clearFramesBackup.frames.map(deepCopy);
  idx = Math.min(clearFramesBackup.idx, frames.length-1);
  clearFramesBackup=null; redoStack.length=0;
  document.getElementById('clearUndo').disabled=true;
  buildStrip(); render(); updateToolState(); scheduleSave();
  chip('Animation restored');
});

// Grid density — the shared setting in lib/gridoverlay.js. The seg only shows
// while the grid is ON: a density control for an invisible grid is a control
// whose effect you cannot see, which is how the onion-depth seg behaves too.
function _wireGridDensity(isOnFn, repaintFn) {
  var seg = document.getElementById('gridDensitySeg');
  var group = document.getElementById('gridDensityGroup');
  if (!seg || !window.SkriblGrid) return function () {};
  function render() {
    var cur = window.SkriblGrid.density();
    var btns = seg.querySelectorAll('[data-density]');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('on', btns[i].getAttribute('data-density') === cur);
    }
    if (group) group.hidden = !isOnFn();
  }
  seg.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-density]') : null;
    if (!b || !seg.contains(b)) return;
    window.SkriblGrid.setDensity(b.getAttribute('data-density'));
    render();
    repaintFn();
  });
  render();
  return render;
}
const gridEl=document.getElementById('flipGrid'), gridBtn=document.getElementById('gridBtn');
let grid=false;
const _renderFlipGridDensity = _wireGridDensity(function(){ return grid; }, function(){ syncGrid(); });
// 'active', not 'on' (v206): the button is an .onion-tint toggle and that
// family lights on .active — motion guides and onion tint both use it. Grid
// kept its pre-tune-drawer 'on' class when it moved into the drawer (v204),
// so the overlay drew but the button never lit. gridEl (the overlay canvas)
// still uses .on — that is its own display class, unrelated to the button.
gridBtn.addEventListener('click',()=>{ grid=!grid; if(grid) syncGrid(); gridBtn.classList.toggle('active',grid); gridEl.classList.toggle('on',grid); gridBtn.setAttribute('aria-checked',String(grid)); _renderFlipGridDensity(); });
// v129: the settings drawer. Kept deliberately dumb — it only shows/hides; every
// control inside keeps its existing handler, so behaviour is unchanged.
const tuneBtn=document.getElementById('tuneBtn'), tunePanel=document.getElementById('tunePanel');
const tuneShell=document.getElementById('tuneShell');
function tuneIsOpen(){ return !!tuneShell && tuneShell.classList.contains('open'); }
function setTune(open){
  if(!tuneBtn||!tuneShell) return;
  tuneShell.classList.toggle('open', open);
  tuneShell.setAttribute('aria-hidden', String(!open));
  tuneBtn.classList.toggle('open', open);
  tuneBtn.setAttribute('aria-expanded', String(open));
  if(open) requestAnimationFrame(()=>{ positionSeg(); positionOnionSeg(); });
  // The stage must give back the drawer's height. Resize on every frame of the
  // transition so the canvas shrinks WITH the reveal instead of snapping at the
  // end — a mid-animation jump is what makes a drawer feel cheap.
  const t0=performance.now();
  const follow=()=>{ sizeStage(); if(performance.now()-t0 < 320) requestAnimationFrame(follow); };
  requestAnimationFrame(follow);
}
if(tuneBtn) tuneBtn.addEventListener('click',()=>setTune(!tuneIsOpen()));
// Escape closes it, like every other transient surface here.
KeyRegistry.register({surface:'flip', label:'close the tune panel',
  keys:['Escape'], scope:()=>tuneIsOpen()});
document.addEventListener('keydown',e=>{ if(e.key==='Escape' && tuneIsOpen()) setTune(false); });

const onionEl=document.getElementById('onion');
const onionGroup=document.getElementById('onionGroup');
// Motion guides toggle. Bound through bindEl for the reason documented there:
// an unguarded getElementById().addEventListener() chain that hits a null takes
// out every binding written after it.
bindEl('arcGuideBtn','click',function(){
  arcGuides = !arcGuides;
  this.setAttribute('aria-checked', arcGuides ? 'true' : 'false');
  // 'active', not 'on': .onion-tint's lit state is styled as .active (the ◐
  // tint button beside Onion skin uses the same class). Toggling 'on' here
  // flipped a class nothing styles, so the guides drew on the canvas while
  // the switch looked permanently off.
  this.classList.toggle('active', arcGuides);
  render();
});

const onionSeg=document.getElementById('onionDepthSeg');
const onionTintBtn=document.getElementById('onionTintBtn');
function positionOnionSeg(){
  if(!onionSeg) return;
  const a=onionSeg.querySelector('button.on'), pill=onionSeg.querySelector('.seg-slider');
  if(!a||!pill||!a.offsetWidth) return;
  pill.style.width=a.offsetWidth+'px';
  pill.style.transform='translateX('+(a.offsetLeft-3)+'px)';
  pill.style.opacity=1;
}
if(onionSeg) onionSeg.addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return;
  onionDepth=+b.dataset.depth;
  [...onionSeg.querySelectorAll('button')].forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); positionOnionSeg(); render();
});
if(onionTintBtn) onionTintBtn.addEventListener('click',()=>{
  onionTint=!onionTint;
  onionTintBtn.classList.toggle('active',onionTint);
  onionTintBtn.setAttribute('aria-checked',String(onionTint));
  render();
});
function setOnion(v){ onion=v; onionEl.classList.toggle('active',onion); onionEl.setAttribute('aria-checked',String(onion));
  // In the drawer the depth/tint controls stay put and the row dims when onion is
  // off — hiding them would make the panel jump height as you toggle.
  if(onionGroup) onionGroup.hidden=false;
  const row=document.getElementById('tuneOnionRow');
  if(row) row.classList.toggle('muted', !onion);
  if(onion) requestAnimationFrame(positionOnionSeg);
  render(); }
onionEl.addEventListener('click',()=>setOnion(!onion));
onionEl.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); setOnion(!onion); } });

/* ---- keyboard ---- */
KeyRegistry.register({surface:'flip', label:'undo', keys:['Mod+z']});
KeyRegistry.register({surface:'flip', label:'redo', keys:['Mod+y','Mod+Shift+z']});
KeyRegistry.register({surface:'flip', label:'play / stop', keys:['Space'],
  scope:()=>!(ZoomView && ZoomView.isZoomed())});
KeyRegistry.register({surface:'flip', label:'pen / eraser', keys:['p','e'],
  scope:()=>!playing && !moveMode});
KeyRegistry.register({surface:'flip', label:'brush size', keys:['[',']'],
  scope:()=>!playing && !moveMode});
KeyRegistry.register({surface:'flip', label:'grid', keys:['g'],
  scope:()=>!playing && !moveMode});
window.addEventListener('keydown', e=>{
  if(_typingEl(e.target)) return;
  if((e.ctrlKey||e.metaKey) && (e.key.toLowerCase()==='y' || (e.shiftKey && e.key.toLowerCase()==='z'))){ e.preventDefault(); redoStroke(); return; }
  if((e.ctrlKey||e.metaKey) && !e.shiftKey && e.key.toLowerCase()==='z'){ e.preventDefault(); undoStroke(); return; }
  // Space = play / stop (when not magnified — Space pans the zoomed canvas instead).
  if((e.code==='Space' || e.key===' ') && !(ZoomView && ZoomView.isZoomed())){ e.preventDefault(); playing?stop():play(); return; }
  if(playing || moveMode) return;   // page identity must not shift mid-move
  // ArrowLeft/ArrowRight are handled by the flip-scrub block above, which adds
  // hold-to-riffle. Leaving the single-step versions here as well meant BOTH
  // fired on one press and the page advanced twice.
  if(e.key==='p' || e.key==='P'){ setTool('pen'); }
  if(e.key==='e' || e.key==='E'){ setTool('eraser'); }
  // Brush size and grid, matching Pad. Dispatched as an 'input' event rather
  // than set-and-call: the value label, the fill and the autosave all hang off
  // this input's own event, and reaching past them would move the number alone.
  if(e.key==='[' || e.key===']'){
    const r=document.getElementById('size');
    if(r){ const next=Math.max(+r.min, Math.min(+r.max, (+r.value||0) + (e.key===']'?1:-1)));
      if(next!==+r.value){ r.value=String(next); r.dispatchEvent(new Event('input',{bubbles:true})); } }
  }
  if(e.key==='g' || e.key==='G'){ if(gridBtn) gridBtn.click(); }
});
bindEl('flipExportCancel', 'click',()=>{ _exportAbort=true; });

/* ---- fps segmented control ---- */
const fpsGroup=document.getElementById('fps');
function positionSeg(){ const active=fpsGroup.querySelector('button.on'); const pill=fpsGroup.querySelector('.seg-slider');
  if(!active||!pill) return; pill.style.width=active.offsetWidth+'px'; pill.style.transform='translateX('+(active.offsetLeft-3)+'px)'; pill.style.opacity=1; }
fpsGroup.addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b)return;
  fps=+b.dataset.fps; [...fpsGroup.querySelectorAll('button')].forEach(x=>x.classList.remove('on')); b.classList.add('on');
  positionSeg(); scheduleSave(); syncFlipDuration(); if(playing){ stop(); play(); } });


/* ---- help drawer (How Flip works) — same component as the Pad ---- */
const helpDrawer=document.getElementById('helpDrawer'), helpClose=document.getElementById('helpClose'), helpBackdrop=document.getElementById('helpBackdrop');
let helpCloseTimer=null;
function openHelpDrawer(){ clearTimeout(helpCloseTimer); document.documentElement.classList.add('help-open'); helpDrawer.hidden=false; helpDrawer.classList.remove('closing'); requestAnimationFrame(()=>helpDrawer.classList.add('open')); }
function closeHelpDrawer(){ clearTimeout(helpCloseTimer); if(document.activeElement && document.activeElement.blur) document.activeElement.blur(); helpDrawer.classList.add('closing'); helpDrawer.classList.remove('open');
  helpCloseTimer=setTimeout(()=>{ helpDrawer.hidden=true; helpDrawer.classList.remove('closing'); document.documentElement.classList.remove('help-open'); }, 250); }
bindEl('miInfo', 'click',()=>{ closeMenu(); openHelpDrawer(); });
// Clear all pages from the ... menu (v206). Same two-tap arm as the Pad's Clear
// all: first tap arms (menu stays open for the confirm), second tap clears.
// Delegates to the draw-drawer #clear button so it inherits the frames backup +
// Clear-undo. Auto-disarms after 3s or when the menu closes.
(function(){
  const item=document.getElementById('miClearAll'); if(!item) return;
  const label=item.querySelector('.mi-tx'); let armed=false, t=null;
  const disarm=()=>{ armed=false; item.classList.remove('armed'); if(label) label.textContent='Clear all pages'; };
  item.addEventListener('click',e=>{ e.stopPropagation();
    if(playing) return;
    const empty = frames.length===1 && frames[0].strokes.length===0;
    if(empty){ chip('Nothing to clear'); closeMenu(); return; }
    if(!armed){ armed=true; item.classList.add('armed'); if(label) label.textContent='Tap again to clear all pages'; clearTimeout(t); t=setTimeout(disarm,3000); return; }
    clearTimeout(t); disarm(); closeMenu();
    // fire the drawer's clear twice: once to arm it, once to execute — the
    // drawer button owns backup/undo, so we go THROUGH it rather than copy it.
    const cb=document.getElementById('clear'); if(cb){ cb.click(); cb.click(); }
  });
  document.addEventListener('skribl:menu-closed', disarm);
})();
helpClose.addEventListener('click', closeHelpDrawer);
helpBackdrop.addEventListener('click', closeHelpDrawer);
KeyRegistry.register({surface:'flip', label:'close the help drawer',
  keys:['Escape'], scope:()=>!helpDrawer.hidden});
window.addEventListener('keydown',e=>{ if(e.key==='Escape' && !helpDrawer.hidden) closeHelpDrawer(); });
// Accordion sections — tap a header to expand/collapse (multiple can be open).
// Help search — shared via lib/helpsearch.js so the two editors cannot
// drift. Safe if the lib is absent: the accordions keep working.
if (window.SkriblHelpSearch) window.SkriblHelpSearch.init();

document.querySelectorAll('#helpDrawer .accordion-header').forEach(header=>{
  header.addEventListener('click',()=>{ const body=header.nextElementSibling; const isOpen=header.classList.toggle('open');
    header.setAttribute('aria-expanded', isOpen?'true':'false');
    if(body && body.classList.contains('accordion-body')) body.classList.toggle('open', isOpen); });
});

/* ---- boot ---- */
const restored = tryRestore();
onionEl.classList.toggle('active', onion); onionEl.setAttribute('aria-checked', String(onion));
if(onionGroup){ onionGroup.hidden=false; const _r=document.getElementById('tuneOnionRow'); if(_r) _r.classList.toggle('muted', !onion); }
syncCanvasSeg();
sizeStage(); buildStrip(); render(); sizeFill(); setBg(bgColor);
// A restored draft reopens on the page it was left on, so the strip must start
// there too. Not smooth: on boot an animated scroll from page 1 to page 62 is a
// second of the strip flying past for no reason. rAF because buildStrip() has
// only just inserted the tiles and their widths are not laid out yet.
requestAnimationFrame(()=>scrollStripToActive(false));
// Intro toast (v204) — replaces the crammed .flip-hint footer that forced the
// page to scroll on load. Shown once ever via SkriblHints (honours the Tips
// toggle, persists 'seen', fails quiet), dismissable by click.
if (window.SkriblHints) {
  // Short, timed toast + a tap-through to the full guide (v206). The long
  // v205 panel tried to explain everything inline and got in the way; this
  // says the one essential thing and offers the rest one tap away.
  // Owner: just the link, no explanatory sentence — the guide is one tap away.
  window.SkriblHints.show('flip-intro',
    'New here?',
    { action: { label: 'How it works \u2192', onClick: function () { if (typeof openHelpDrawer === 'function') openHelpDrawer(); } } });
}
loadBgImageObj(()=>{ applyBg(); render(); });   // re-hydrate a restored background image
ensureAudio(); syncMediaUI();
if (musicData) { decodeForWaveform(); if (typeof setCrossfadeUI==='function') setCrossfadeUI(); }
// Re-add buttons reopen the same file pickers; dismiss forgets the saved settings.
// Wired here (end of script) so every element const above is initialised, and
// null-guarded so a surface without the cards can't abort the script.
{ const bind=(id,fn)=>{ const el=document.getElementById(id); if(el) el.addEventListener('click',fn); };
  bind('musicPendingBtn', ()=>musicInput.click());
  bind('photoPendingBtn', ()=>imageInput.click());
  bind('musicPendingDismiss', ()=>{ pendingMusicMeta=null; refreshPendingCards(); scheduleSave(); });
  bind('photoPendingDismiss', ()=>{ pendingPhotoMeta=null; refreshPendingCards(); scheduleSave(); }); }
refreshPendingCards();

if (restored) chip('Draft restored');
requestAnimationFrame(positionSeg);
window.addEventListener('load', ()=>{ sizeStage(); positionSeg(); positionToolSlider(); syncSelBar(); });

// Report sheet — shared via lib/report.js so the two editors collect the same
// context. Null-safe: without the lib the menu item simply does nothing.
if (window.SkriblReport) window.SkriblReport.init();

// Styled tooltips. Native `title` cannot be rounded; this swaps them out.
if (window.SkriblTooltip) window.SkriblTooltip.init();

/* ===================================================================
   v215 — parity block. Every fix in this codebase has to be made twice,
   and most bugs in the v213 session were one surface having a fix the
   other lacked. This is the Flip half.
   =================================================================== */


(function initPaintTarget(){
  const seg=document.getElementById('paintTargetSeg');
  if(!seg) return;
  seg.addEventListener('click',e=>{
    const btn=e.target.closest('button[data-target]');
    if(!btn) return;
    const target=btn.dataset.target;
    seg.querySelectorAll('button').forEach(b=>{
      const on=b===btn;
      b.classList.toggle('active', !!on);
      b.setAttribute('aria-pressed', String(!!on));
    });
    ['colorGroup','bgGroup'].forEach(id=>{
      const g=document.getElementById(id);
      if(g) g.hidden = g.dataset.target!==target;
    });
    // Recent is a list of PEN colours. It sits between the two swatch grids as a
    // sibling, so it stayed on screen in Background mode and read as "recent
    // backgrounds" — which is what it was reported as. It belongs to the pen.
    const recent = document.getElementById('recentRow');
    if (recent) {
      // Read the real state rather than inventing a flag: lib/recentcolors.js
      // owns this row's visibility, and a parallel copy would drift from it.
      const swatches = document.getElementById('recentColors');
      const has = !!(swatches && swatches.children.length);
      recent.hidden = (target !== 'stroke') || !has;
    }
    if(window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  });
  if(window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
})();

(function trackDrawerSegs(){
  ['smoothSeg','brushSeg','shapeSeg','pressureSeg','eraserSeg'].forEach(id=>{
    const seg=document.getElementById(id);
    if(seg&&window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  });
})();


// NO NAVIGATION GUARD ON FLIP, deliberately. Flip persists pages, music and the
// background image, so leaving for Pad loses nothing and a confirm here would be
// a prompt that is always wrong. Pad needs one because its autosave holds
// strokes but NOT media bytes — see the note on atRisk() in app.js.
