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
// The palette lives in lib/palette.js and is shared with Pad. It was two
// hand-synchronised lists; the fallback here is only so a missing lib
// leaves you a pen rather than a blank row.
const COLORS = (window.SkriblPalette && window.SkriblPalette.hexes) || ["#ffffff","#141414"];
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

/* Fill's two numbers, named here rather than typed into doFill.
   TOLERANCE is how far from the tapped colour still counts as the same region.
   32 of 255 per channel absorbs the anti-aliased fringe on a drawn line without
   leaking through it; the fringe is what makes a zero-tolerance fill leave a
   halo of un-filled pixels around every stroke it meets.
   There is no row-step knob any more: rows group by their real extent, so a
   flat region costs one run however tall it is and a sloping edge costs one per
   row. Cost follows the PERIMETER rather than the area, which is both cheaper
   on ordinary shapes and exact on diagonals -- a fixed band took the union of
   its rows and drew a perforated line down every slope. */
/* How long the media spill gets before its bytes are called lost. Long enough
   that a slow phone writing several megabytes finishes honestly; short enough
   that a write which has silently died does not hold the pill on "Saving..."
   for the rest of the session. */
const SPILL_TIMEOUT_MS = 12000;

const FILL_TOLERANCE = 32;

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
  playBitmaps = null;   // captures are CW x CH composites; a resize orphans them
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
// The stage's content box — the room the canvas can actually use. The reserve
// IS the stage's CSS padding, read from computed style rather than repeated as
// literals (24/6): those went stale the moment the padding changed, in fitPad,
// in the boot best-fit pick AND in the harness mirrors of both.
function stageAvail(stage){
  const cs = getComputedStyle(stage);
  return { w: stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
           h: stage.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) };
}
function fitPad(){
  const stage = document.querySelector('.flip-stage');
  const avail = stageAvail(stage);
  const availW = avail.w, availH = avail.h;
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
/* Copied pages, for paste. An ARRAY since v226 — a single-page copy is just a
   span of one, which is why nothing downstream needed a second code path. */
let pageClip = null;
/* SPAN STATE, hoisted here for the reason spelled out above the selection's:
   flip.js is a classic script, and a `let` reached during init throws and
   silently kills every line after it. `spanAnchor` is where a range began;
   `idx` is always its other end, so a span needs exactly one extra number. */
let spanAnchor = null, _spanSweep = false, _spanHoldTimer = null;
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
/* Media the session has LOST — a photo or track whose bytes never landed, kept
   so the same file can be re-added with its settings intact. Declared UP HERE
   with the rest of the media state rather than beside tryRestore(), because
   showAutosaveStatus() reads them and it is defined, and reachable, well above
   that point. `typeof x !== 'undefined'` does NOT make that safe: typeof shields
   you from an UNDECLARED name, not from a `let` in its temporal dead zone, which
   throws exactly the same ReferenceError. This file has been bitten by that
   three times (see selClear, moveMode, the stamp shelf) and each time the fix
   was to move the declaration, not to add a guard that does not guard. */
let pendingMusicMeta = null, pendingPhotoMeta = null;
let musicEnabled = true, trimStart = 0, trimEnd = null, audioDuration = 0;   // trim/loop
const MAX_LOOP_SECONDS = 20;   // hard cap on loop length; enforced at load AND on every drag
let audioCtx = null, currentAudioBuffer = null, loopCrossfadeMs = 0;         // decoded buffer for the waveform
let zoomMag = 1, zoomFocus = 'loop', zoomCenter = null;                       // Loop Detail magnification
let musicName = '';                                                          // track filename (shown in the dropzone)
let drawing = false, curCount = 0, playing = false, playTimer = null;
// Measured cost of painting each frame, by index, kept as a running average.
// Playback subtracts it from the wait so a frame's VISIBLE duration is its
// interval — see runPlayTimer. Declared up here with the rest of the early
// state: a `let` first reached partway down this file throws during init and
// silently kills every line after it.
let framePaintMs = [];
// A per-point cost, averaged across whatever has been drawn so far, used to
// ESTIMATE a frame nobody has painted yet. Without it the correction only
// kicks in on the second time round the loop, so the very first play-through
// -- the one you actually watch after pressing the button -- still stuttered.
let msPerPoint = 0;
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
/* v236 Liquify. Up here with the rest of the early state for the fifth time of
   asking: setTool() runs during init, reads the tool registry, and anything it
   can reach must already be initialised. A `let` declared beside the liquify
   functions 2500 lines below would be in its temporal dead zone at that moment
   and would take the whole file down with it. */
let liquifying = false, liquifyPointerId = null;
let fieldActive = false, fieldPointerId = null;   // smudge / blur
let liquifyLast = null, liquifyIdx = -1;
/* A WHOLE-FRAME snapshot, not a map of touched indices, because subdividing
   INSERTS points and every index after an insertion shifts. The index-keyed
   version was correct right up until the tool started changing the length of
   the array it was indexing into. Same shape selframe already uses for mirror,
   duplicate and cut, which change the length for the same reason. */
let liquifyBefore = null, liquifyTouched = false;

// What Cut is holding, if anything. Up here for the same reason as the rest:
// syncSelBar() reads it to decide whether Paste has a cell, and setTool()
// reaches syncSelBar() during init.
let selClipboard = null;
// The stamp shelf, up here for exactly the reason above it: setTool() reaches
// syncStampPop() during init, and a `let` read before its own line throws
// rather than reading undefined. Loaded from storage below, once the libs have
// had a chance to define themselves. (See the block near doStamp().)
let stampShelf = [];
let stampArmed = -1;          // index into stampShelf, or -1 for none armed
let stampScalePct = 100;
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
// Owned by lib/holdtiming.js, which both this editor and the player read, so
// the clamp cannot drift between what you preview and what a viewer gets.
// Inline fallback for a surface that somehow loads without the lib.
const MAX_HOLD = (typeof window !== 'undefined' && window.SkriblHold)
  ? window.SkriblHold.MAX_HOLD : 4;
function frameHold(f){
  if(typeof window !== 'undefined' && window.SkriblHold) return window.SkriblHold.holdOf(f);
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
  /* HOLD SURVIVES THE ROUND TRIP, and until v241 it did not. serializeFlip
     writes `hold` whenever a page is held longer than one beat, and every
     return here rebuilt the frame as {strokes, strokeGroups} — so the value was
     written to the .skribl faithfully and thrown away on the way back in. Set a
     page to x2, save a draft, reopen it, and the timing is silently gone; the
     same path restores the AUTOSAVE, so it was lost on an ordinary reload too.
     Found while generating a demo file whose key poses were meant to be held.
     frameHold() rather than f.hold: it clamps to [1, MAX_HOLD], so a missing,
     absurd or hand-edited value lands somewhere sane instead of propagating. */
  const hold = frameHold(f);
  const strokes = Array.isArray(f.strokes) ? f.strokes : [];
  const groups = Array.isArray(f.strokeGroups) ? f.strokeGroups.slice() : [];
  let n = 0;
  for(const c of groups) n += c;
  if(n === strokes.length) return { strokes: strokes, strokeGroups: groups, hold: hold };
  if(n < strokes.length){ groups.push(strokes.length - n); return { strokes: strokes, strokeGroups: groups, hold: hold }; }
  while(groups.length && n > strokes.length) n -= groups.pop();
  return { strokes: strokes.slice(0, n), strokeGroups: groups, hold: hold };
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
/* The polygon's sides and the corner rounding, in CANVAS units for the radius
   so it means the same thing at every zoom. Defaults chosen so a first Poly
   drag draws something recognisable rather than a triangle nobody asked for. */
let shapeSides = 5, shapeRadius = 0;
let _shapePrev = null, _shapeAnchor = null;   // 'pen' | 'eraser' | 'shape'; `erasing` stays the fast path
let _saveT = null;
// Quiet autosave: the debounce no longer flashes "Saving…" on every stroke —
// an autosave that works shouldn't narrate itself. The pill speaks when the
// save LANDS ("Saved", 1.6s then gone) and for anything long or wrong: the
// media-spill paths still show "Saving…" while a multi-megabyte write is
// genuinely pending, and 'failed'/'saved-no-media' still persist.
function scheduleSave(){ clearTimeout(_saveT); _saveT = setTimeout(saveNow, 800);
  if (typeof updateFlipEmptyHint === 'function') updateFlipEmptyHint(); }
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
    title: (window.SkriblName && window.SkriblName.get()) || 'Untitled Skribl',
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
      // v238: 'saved' when this write omitted nothing AND nothing is waiting;
      // amber when a media record IS waiting to be re-added.
      //
      // THIS IS NOT A REVERT OF v235, it is the half of it that was missing.
      // v235 was answering a live report — amber sitting permanently on a
      // drawing, on every save, with no way to clear it — and it removed the
      // pill instead of the dead end. The cost showed up in verify_amber: reload
      // a session whose track genuinely never saved and it said "Saved" with the
      // track gone. Both states are the SAME state in the draft (mediaOmitted
      // set, a pending record restored, no bytes), so there is nothing here to
      // discriminate on. Either the warning is shown or the loss is silent.
      //
      // What made the old amber intolerable was never that it was wrong — it was
      // that it went nowhere. The only control that clears a pending record is
      // the re-add card, and that card measures 0x0 until its drawer is opened.
      // So the pill is now the route to it (see showAutosaveStatus below): the
      // warning is true, and one tap reaches the Re-add and Dismiss it is
      // telling you about. Dismissing clears the record, which schedules a save,
      // which reports plain 'saved' — the amber ends because the situation did.
      //
      // A pending record is checked rather than hasMedia because reaching here
      // means hasMedia is FALSE: there is no photo and no track on this page, so
      // this write really did omit nothing. The record is about media the
      // session is still missing, which is a fact about now, not about history.
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
    // A PUT THAT NEVER SETTLES IS NOT A PUT THAT IS STILL WORKING. IndexedDB on
    // iOS Safari can accept a multi-megabyte write and then neither resolve nor
    // reject it, and nothing below has a timeout of its own: the promise simply
    // never runs, _mediaSpillState stays 'saving' forever, and the pill sits on
    // "Saving..." for the rest of the session -- reported from the live demo as
    // "saving stays blinking". Every later save then re-enters this branch and
    // reports 'saving' again, so the state is not just stuck, it is sticky.
    //
    // So the spill races a deadline. Past it the bytes are treated as lost,
    // which is the truthful reading: a write that has not landed in twelve
    // seconds is not one a reload can count on. A late resolve is ignored --
    // `settled` guards both arms -- because by then the amber has already told
    // the user the truth and flipping it back to green would un-tell it.
    let settled = false;
    const spillTimer = setTimeout(() => {
      if (settled) return;
      settled = true;
      _mediaSpillState = 'failed';
      if (bgImage) pendingPhotoMeta = { fit:photoFit, opacity:photoOpacity, blur:photoBlur,
                                        zoom:photoZoom, offX:photoOffX, offY:photoOffY,
                                        enabled:photoEnabled, name:imageName };
      if (musicData) pendingMusicMeta = { enabled:musicEnabled, trimStart:trimStart,
                                          trimEnd:trimEnd, crossfadeMs:loopCrossfadeMs,
                                          name:musicName };
      showAutosaveStatus('saved-no-media');
      console.error('[skribl] media spill to IndexedDB timed out after ' + SPILL_TIMEOUT_MS + 'ms');
    }, SPILL_TIMEOUT_MS);
    SkriblDraftStore.put('flip:draft', { json: JSON.stringify(serializeFlip()), savedAt: stamp })
      .then(() => { if (settled) return; settled = true; clearTimeout(spillTimer);
                    _mediaSpillState = 'durable';
                    // The session IS fully recoverable now — say so. (Only if
                    // the pill still shows this save's amber; never conjure.)
                    const el = document.getElementById('autosaveStatus');
                    if (el && !el.hidden) showAutosaveStatus('saved'); })
      .catch((e3) => { if (settled) return; settled = true; clearTimeout(spillTimer);
                       _mediaSpillState = 'failed';
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
    // THE DRAWING IS SAFE; THE MEDIA BYTES ARE STILL IN FLIGHT. Until v229 this
    // painted the amber 'saved-no-media' unconditionally, and that is a warning
    // about a failure that has not happened and usually never will — reaching
    // this code is the NORMAL way media is saved, as the comment 80 lines up
    // says outright. Instrumented, the real sequence was:
    //     put:start bytes=4215866
    //     pill:saved-no-media      (+1ms)
    //     put:RESOLVED / pill:saved (+13ms)
    // 13ms of amber on a desktop is invisible, which is exactly why it shipped.
    // On a phone writing multiple megabytes it is visible, and if the write is
    // slow or never settles it is permanent — an amber durability warning
    // parked on a session that is fine.
    //
    // 'saving' is the honest description of a pending write, it already stays
    // up without fading, and the .then/.catch above resolve it to 'saved' or to
    // a 'saved-no-media' that is TRUE. When there is no store to spill to,
    // _mediaSpillState is already 'failed' and the amber is earned.
    showAutosaveStatus(_mediaSpillState === 'saving' ? 'saving' : 'saved-no-media');
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
          // Same reasoning as the write above: reclaiming space says nothing
          // about whether the media reached IndexedDB.
          showAutosaveStatus(_mediaSpillState === 'saving' ? 'saving' : 'saved-no-media');
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
/* Is there media the session has LOST, as opposed to media it merely could not
   make durable? Only the first has anything to re-add. */
function _pillPending(){
  return (pendingMusicMeta && !musicData) || (pendingPhotoMeta && !bgImage);
}

/* Make the pill a control, or stop it being one.
   A DIV WITH role="button" RATHER THAN A <button>, deliberately: #autosaveStatus
   is one shared element across Pad, Flip and the player, and only Flip can ever
   have media to re-add. Changing the markup would put a button that does nothing
   on the other two. The role and the tabindex are added exactly while the pill
   has somewhere to go and removed the moment it does not, which is also the
   honest answer for a screen reader — it announces a button only when there is
   one. */
let _pillBound = false;
function _pillAction(on){
  const el = document.getElementById('autosaveStatus');
  if(!el) return;
  el.classList.toggle('actionable', !!on);
  if(on){
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.setAttribute('title', 'Open the drawer holding the missing file');
  } else {
    el.removeAttribute('role'); el.removeAttribute('tabindex'); el.removeAttribute('title');
  }
  if(_pillBound) return;
  _pillBound = true;
  const go = (e) => {
    if(!el.classList.contains('actionable')) return;
    // The document-level handler below closes any open drawer on a click
    // outside it. Without this the drawer would open and shut in the same
    // event — opened here, closed by the same click still travelling upward.
    e.stopPropagation();
    e.preventDefault();
    refreshPendingCards();
    // Music first only because a session can be missing both and one drawer has
    // to come up; the other card is still one tap away and its own dot marks it.
    _flipDrawerCtl.open((pendingMusicMeta && !musicData) ? 'music' : 'photo');
  };
  el.addEventListener('click', go);
  el.addEventListener('keydown', (e) => {
    if(e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') go(e);
  });
}

function showAutosaveStatus(state){
  const el=document.getElementById('autosaveStatus'), txt=document.getElementById('autosaveStatusText'); if(!el||!txt) return;
  clearTimeout(el._hideTimer); el.hidden=false; el.classList.remove('saving','failed','partial');
  if(state==='saving'){ el.classList.add('saving'); txt.textContent='Saving…'; }
  else if(state==='failed'){ el.classList.add('failed'); txt.textContent='Autosave failed'; }
  // Drawing + all settings saved; the media files were too large for localStorage.
  // Amber, not green — the session is not fully recoverable and the user should know
  // without having to open a drawer to find out.
  //
  // TWO WORDINGS, because there are two amber situations and only one of them is
  // something the user can act on. When a pending record is waiting, the file is
  // GONE from the session and the re-add card can put it back, so the pill names
  // the action. When there is no record — a spill with no store to spill to —
  // the media is still loaded and in front of them; nothing needs re-adding, it
  // simply will not survive a reload. Offering "tap to re-add" there would send
  // them to an empty drawer.
  else if(state==='saved-no-media'){
    el.classList.add('partial');
    txt.textContent = _pillPending() ? 'Media missing — tap to re-add'
                                     : 'Saved without media';
  }
  else { txt.textContent='Saved'; }
  // THE ROUTE OUT, and the whole reason the amber is allowed back. Reapplied on
  // every call rather than bound once, because whether the pill does anything
  // changes with the state it is showing — and a control that looks tappable
  // and is not is worse than one that never offered.
  _pillAction(state === 'saved-no-media' && _pillPending());
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
  // Adopt the loaded draft's name into the tab (blank keeps the auto-default).
  if(window.SkriblName && d && d.title && !/^Untitled Skribl$/.test(d.title)) window.SkriblName.set(d.title);
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
    return { strokes: flat, strokeGroups: groups, hold: frameHold(f) };
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
  currentAudioBuffer = null; zoomMag = 1; zoomFocus = 'loop'; zoomCenter = null; if(typeof syncZoomMagStep==='function') syncZoomMagStep();
  if (d.fps === 6 || d.fps === 12 || d.fps === 24) {
    fps = d.fps;
    [...document.querySelectorAll('#fps button')].forEach(b=>b.classList.toggle('on', +b.dataset.fps === fps));
  }
  return frames.some(f => f.strokes.length);
}
// Media the autosave had to drop (too big for localStorage). Mirrors the Pad:
// the settings survive, the bytes don't, and the drawers show a "Re-add" card.
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
// The blank-page whisper (Pad's .canvas-empty-hint, same treatment): visible
// only while the document is genuinely empty — one page, no strokes, no photo.
// Re-evaluated on every scheduled save, and yanked on pointerdown so it is not
// sitting under the first stroke while it is being drawn.
function updateFlipEmptyHint(){
  const el = document.getElementById('flipEmptyHint'); if(!el) return;
  const empty = frames.length === 1
    && (!frames[0] || !frames[0].strokes || !frames[0].strokes.length)
    && !bgImage;
  el.classList.toggle('hidden', !empty);
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
/* ANCHORED, and rgba only. Unanchored `rgba?\([^)]*,\s*([\d.]+)\s*\)` also
   matched rgb(): the greedy [^)]* let the BLUE channel land in the alpha group,
   so alphaOf('rgb(255,176,32)') returned 32. Harmless for the layering decision
   it was written for — 32 is not < 1, so the stroke read as opaque, which is
   correct — and quietly wrong everywhere else. tweenFade multiplied by it and
   clamped, so an in-between of any drawing whose colours were stored as rgb()
   came out FULLY OPAQUE: a stack of solid copies with no exposure at all. Not
   reachable through Flip's own pen, which is always hex, but strokes also
   arrive from loaded .skribl files and posted payloads, and the server does not
   validate colour strings.
   app.js's parseStrokeAlpha has always been anchored. This is the same rule. */
function alphaOf(col){
  if(typeof col !== 'string') return 1;
  const m = col.match(/^rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)$/i);
  return m ? Math.max(0, Math.min(1, parseFloat(m[1]))) : 1;
}
/* The alpha a stroke carries in ANY form the payload may hold it in, including
   the 8-digit hex the in-between itself writes. Deliberately separate from
   alphaOf(): alphaOf drives the LAYERING decision, and teaching it about
   #rrggbbaa would put every in-between back on the expensive per-stroke path
   that made playback stall. This one is for composing colours, not costing
   them. */
function strokeAlphaOf(col){
  if(typeof col !== 'string') return 1;
  const h = /^#[0-9a-f]{6}([0-9a-f]{2})$/i.exec(col.trim());
  if(h) return parseInt(h[1], 16) / 255;
  return alphaOf(col);
}
function solidOf(col){ if(typeof col==='string'){ const m=col.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i); if(m) return 'rgb('+m[1]+', '+m[2]+', '+m[3]+')'; } return col; }
function paintSeg(c, seg, solid){
  for (let i = 0; i < seg.length; i++) {
    const p = seg[i]; const col = solid ? solidOf(p.color) : p.color;
    if (i === 0) drawDot(c, p.x, p.y, col, p.size, p.erase);
    else { const pv = seg[i-1]; drawLine(c, pv.x, pv.y, p.x, p.y, col, p.size, p.erase); }
  }
}
/* HOW MUCH LAYERING ONE FRAME CAN AFFORD.

   Layering costs a full-canvas round trip per translucent stroke -- clear,
   redraw, composite -- so its price is per STROKE and it scales with nothing
   the user can see. Measured at 816x612: about 1.4 ms each. A frame with a
   dozen is free; a frame with 162 spends 220 ms and cannot be played, which is
   how an in-between generated before v239 behaves. Those pages are already
   saved in people's drafts, so fixing the generator was not enough on its own.

   Past the budget the whole frame paints direct. The difference that gives up
   is beading where a stroke crosses itself -- measured at a median of 3 per
   channel and +3% ink on a real exposure, against a stall you cannot miss. The
   guard is deliberately well above anything hand-drawn: a frame would need two
   dozen separate see-through strokes to reach it, and at that point the frame
   is compositing more than it is drawing. */
const LAYER_BUDGET = 24;
function layerableCount(strokeArr){
  let n = 0, i = 0;
  while (i < strokeArr.length) {
    let j = i + 1; while (j < strokeArr.length && !strokeArr[j].start) j++;
    const p = strokeArr[i];
    if (p && !p.erase && alphaOf(p.color) < 1) n++;
    if (n > LAYER_BUDGET) return n;      // no need to count the rest
    i = j;
  }
  return n;
}

function paintStatic(c, strokeArr){
  // The ceiling lives in lib/strokelayers.js, beside the setting it qualifies,
  // so the player applies the same one. Inline fallback as elsewhere.
  const _overBudget = (typeof window !== 'undefined' && window.SkriblStrokeLayers
                       && window.SkriblStrokeLayers.overBudget)
    ? window.SkriblStrokeLayers.overBudget(strokeArr, alphaOf)
    : layerableCount(strokeArr) > LAYER_BUDGET;
  let i = 0;
  while (i < strokeArr.length) {
    let j = i + 1; while (j < strokeArr.length && !strokeArr[j].start) j++;   // one stroke = start .. next start
    const seg = strokeArr.slice(i, j);
    // Stroke layers, the same setting Pad's tune row drives. Off means paint
    // straight through, so a see-through stroke compounds at its own overlaps
    // — which is exactly what the layer exists to prevent, and now visible
    // rather than a global only a console could reach.
    const _layered = ((typeof window.SKRIBL_STROKE_LAYERS === 'undefined')
      || window.SKRIBL_STROKE_LAYERS !== false) && !_overBudget;
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
    const pts = SkriblShapes.points(shapeKind, _shapePrev.a, _shapePrev.b,
      {square:_shapePrev.sq, sides:shapeSides, radius:shapeRadius});
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
  // eyedropper: this press opens the magnifying loupe — drag to aim, release
  // picks (lib/eyedropper.js). One-shot tap sample stays as the fallback.
  if(picking){
    if(_eyedropper && _eyedropper.beginPick && _eyedropper.beginPick(e)) return;
    sampleColorAt(e); return;
  }
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
  // Liquify intercepts here too, and for the third instance of the same reason:
  // a tool that drags existing ink must not also lay new ink while it does it.
  if(flipTool === 'liquify'){
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    liquifying = true; liquifyPointerId = e.pointerId;
    redoStack.length = 0;      // a new edit invalidates the redo branch
    liquifyBegin(pos(e));
    return;
  }
  // Fill intercepts before drawing too, and for a reason the others do not
  // have: it is a TAP, not a drag. There is no stroke to lay and nothing to
  // follow the pointer, so it commits immediately and returns.
  if(flipTool === 'fill'){
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    doFill(pos(e));
    return;
  }
  // Stamp is a tap for the same reason and lands in the same place.
  if(flipTool === 'stamp'){
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    doStamp(pos(e));
    return;
  }
  // Smudge and blur intercept for Liquify's reason, stated there: a tool that
  // works on existing ink must not also lay new ink while it does it.
  if(flipTool === 'smudge' || flipTool === 'blur'){
    try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
    fieldActive = true; fieldPointerId = e.pointerId;
    redoStack.length = 0;
    fieldBegin(pos(e), flipTool === 'smudge' ? 'Smudge' : 'Blur');
    if(flipTool === 'blur'){ blurMove(pos(e)); render(); }
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
  // The shape picker is tool OPTIONS, not a dialog: the press that starts
  // your shape shoves it aside and the SAME gesture draws. Twin of the Pad
  // rule in editor_draw.js — separate copies of the picker, separate copies
  // of its manners (verify_tray says so twice on purpose). A DRAGGED pop
  // (data-moved) is pinned: veiled for just this gesture, back on release
  // (the window pointerup listener by shapePopDismiss lifts the veil).
  // BELOW every press-swallowing guard, same as Pad and for the same reason:
  // the picker steps aside only for a press that actually draws.
  { const _sp=document.getElementById('shapePop');
    if(_sp && !_sp.hidden){
      if(_sp.dataset.moved) _sp.classList.add('pop-veiled');
      else _sp.hidden=true;
    } }
  try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
  drawing=true; strokePointerId=e.pointerId; curCount=1; redoStack.length=0; noteAction('stroke');
  document.body.classList.add('stroking');   // the chrome recedes while the pen is down (flip.css)
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
  if(liquifying){
    // Guarded on pointerId like every other drag here: a palm or a second
    // finger must not steer a gesture a different pointer started.
    if(e.pointerId === liquifyPointerId){ e.preventDefault(); if(liquifyMove(pos(e))) render(); }
    return;
  }
  if(fieldActive){
    if(e.pointerId === fieldPointerId){
      e.preventDefault();
      const moved = (flipTool === 'smudge') ? smudgeMove(pos(e)) : blurMove(pos(e));
      if(moved) render();
    }
    return;
  }
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
  // Shape reads only the CURRENT position — it is a rubber band between two
  // corners, not a trail — so it takes the last sample and returns before any
  // of the per-point work below.
  if(flipTool==='shape'){
    _constrainActive = !!(e && e.shiftKey);
    _shapePrev = {a:_shapeAnchor, b:{x:raw.x,y:raw.y}, sq:_constrainActive};
    render(); return;
  }
  // EVERY SAMPLE THE BROWSER ACTUALLY CAPTURED, not just the one per frame it
  // hands to this listener. lib/inputsamples.js explains why at length; the
  // short version is that a pointermove arrives once per animation frame while
  // the digitiser samples at 120-240Hz, so a fast circle was being recorded as
  // a ~24-sided polygon and a slow one as a smooth curve. Reported from the
  // live demo in exactly those words.
  //
  // The events are passed through whole rather than reduced to coordinates:
  // sizeFor() reads pressure off the event, and taking positions from the batch
  // while taking pressure from the last event would flatten every taper.
  const _samples = (typeof SkriblInputSamples !== 'undefined')
    ? SkriblInputSamples.extract(e) : [e];
  const _mapped = [];
  for(let _i=0;_i<_samples.length;_i++){
    const _q = pos(_samples[_i]);
    _mapped.push({ ev:_samples[_i], x:_q.x, y:_q.y });
  }
  // Thinned from the last point actually COMMITTED, so the filter carries
  // across event boundaries instead of restarting every frame.
  const _kept = (typeof SkriblInputSamples !== 'undefined')
    ? SkriblInputSamples.thin(_mapped, _brushLastPt, SkriblInputSamples.MIN_DIST)
    : _mapped;
  for(let _i=0;_i<_kept.length;_i++){
    const _s = _kept[_i];
    let px, py;
    // The stabilizer, and the fix to a bug this rewrite exposed. This was:
    //     if(smoothingAlpha>=1 || erasing){ px=raw.x; py=raw.y; }
    //     if(flipTool==='shape'){ ... return; }
    //     else { smoothPt=...; px=smoothPt.x; py=smoothPt.y; }
    // where the `else` bound to the SHAPE test, not the smoothing one. So with
    // the stabilizer on, an eraser stroke had its precise point overwritten by
    // the smoothed one, directly contradicting the comment that said "erasing
    // stays precise". It was invisible at the default (stabilizer off, where
    // the smoothed point equals the raw one), which is why it survived.
    if(smoothingAlpha>=1 || erasing){ px=_s.x; py=_s.y; }
    else { smoothPt={x: smoothPt.x+(_s.x-smoothPt.x)*smoothingAlpha,
                     y: smoothPt.y+(_s.y-smoothPt.y)*smoothingAlpha};
           px=smoothPt.x; py=smoothPt.y; }
    // Shift-to-constrain — same shared helper and same stroke-start anchor as Pad.
    _constrainActive = !!(e && e.shiftKey);
    if(_constrainActive && typeof SkriblConstrain !== 'undefined'){
      const _sf = (strokeFrame || frame()).strokes, _a = _sf.length ? _sf[_sf.length - curCount] : null;
      if(_a){ const _c = SkriblConstrain.apply(_a, {x:px,y:py}, true); px=_c.x; py=_c.y; }
    }
    curCount++;
    const dsize = _brushWidth(sizeFor(_s.ev, _eraserSize(size, erasing)), {x:px,y:py}, erasing);
    const pcol = erasing ? color : penColorFor(color);
    _brushLastPt = {x:px, y:py};
    (strokeFrame || frame()).strokes.push({ x:px, y:py, color: pcol, size: dsize,
                                            t: performance.now(), erase: erasing });
  }
  // ONE render for the whole batch, not one per sample: painting is the
  // expensive half and the frame is only shown once anyway.
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
      ? SkriblShapes.points(shapeKind, _shapeAnchor, _shapePrev.b,
          {square:_shapePrev.sq, sides:shapeSides, radius:shapeRadius}) : [];
    if(pts.length > 1){
      const pcol = penColorFor(color), now = performance.now();
      for(let i=0;i<pts.length;i++) tgt.strokes.push({ x:pts[i].x, y:pts[i].y, color:pcol,
        size:size, t:now + i, erase:false, start:i===0 });
      curCount = pts.length;
    }
    _shapePrev=null; _shapeAnchor=null;
  }
  drawing=false; smoothPt=null; lastRaw=null;
  document.body.classList.remove('stroking');   // pen up: the chrome returns
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
function endLiquifyDrag(e){
  if(!liquifying) return;
  if(e && e.pointerId != null && e.pointerId !== liquifyPointerId) return;
  liquifying = false; liquifyPointerId = null;
  // liquifyEnd returns the page it committed to, which is not necessarily the
  // one on screen: releasing after a page change must refresh the thumbnail of
  // the page that actually changed.
  const at = liquifyEnd();
  if(at !== false){
    render(); refreshThumb(at); updateToolState(); scheduleSave();
  }
}
window.addEventListener('pointerup', endLiquifyDrag);
window.addEventListener('pointercancel', endLiquifyDrag);
/* Smudge and blur end the same way and for the same reasons: bound to the
   WINDOW so a release outside the canvas still finishes the gesture, and
   guarded on pointerId so a second finger cannot end someone else's drag. */
function endFieldDrag(e){
  if(!fieldActive) return;
  if(e && e.pointerId != null && e.pointerId !== fieldPointerId) return;
  fieldActive = false; fieldPointerId = null;
  const at = fieldEnd();
  if(at !== false){ render(); refreshThumb(at); updateToolState(); scheduleSave(); }
}
window.addEventListener('pointerup', endFieldDrag);
window.addEventListener('pointercancel', endFieldDrag);

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
/* Liquify's reach is WIDER than the brush paints, so it needs its own ring or
   the tool lies about what it will catch. Dashed rather than solid to say
   "influence" instead of "footprint" — a solid ring that size would read as an
   enormous brush about to lay ink. */
const liquifyCursor = document.createElement('div');
liquifyCursor.className = 'flip-liquify-cursor';
document.querySelector('.flip-wrap').appendChild(liquifyCursor);
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
function moveLiquifyCursor(e){
  const r = _padRectCached();
  const sz = liquifyRadius() * 2 * (r.width / CW);
  liquifyCursor.style.width = sz + 'px'; liquifyCursor.style.height = sz + 'px';
  liquifyCursor.style.transform =
    'translate3d(' + (e.clientX - r.left) + 'px,' + (e.clientY - r.top) + 'px,0) translate(-50%,-50%)';
  liquifyCursor.style.display = 'block';
}
/* WHICH TOOL AM I HOLDING? Until now the canvas could not answer that. Liquify
   has its dashed influence ring and the eraser its circle, but Smudge, Blur,
   Fill, Select, Stamps, Shape and Artwork ALL fell through to the pen's ring --
   seven tools wearing one cursor, so the only way to know what a drag would do
   was to remember what you last tapped.
   
   The badge is the tool's OWN icon, lifted from its shelf button rather than
   copied, so it cannot drift from the tray: there is one drawing of each tool
   and this is it. It rides beside the ring rather than replacing it, because
   the ring still says how big the brush is and that is a different question.
   Hidden while the pointer is down -- during a stroke you know what you picked,
   and a glyph following your hand across your own drawing is in the way. */
const toolBadge = document.createElement('div');
toolBadge.className = 'flip-tool-badge';
document.querySelector('.flip-wrap').appendChild(toolBadge);
let _badgeFor = null;
function syncToolBadge(){
  if(_badgeFor === flipTool) return;
  _badgeFor = flipTool;
  const btn = document.getElementById(flipTool + 'ToolBtn');
  const svg = btn && btn.querySelector('svg');
  toolBadge.innerHTML = svg ? svg.outerHTML : '';
}
function moveToolBadge(e){
  syncToolBadge();
  if(!toolBadge.innerHTML){ toolBadge.style.display='none'; return; }
  const r = pad.getBoundingClientRect();
  toolBadge.style.transform =
    'translate(' + (e.clientX - r.left + 13) + 'px,' + (e.clientY - r.top + 13) + 'px)';
  toolBadge.style.display = 'block';
}
function hideCursors(){ toolBadge.style.display='none'; eraserCursor.style.display='none'; brushCursor.style.display='none';
  liquifyCursor.style.display='none'; }
pad.addEventListener('pointermove', e=>{
  // A finger is its own cursor. Anything but a mouse or pen gets nothing.
  if(e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'pen'){
    hideCursors(); return;
  }
  if(playing || picking){ hideCursors(); return; }
  if(ZoomView && ZoomView.isZoomed()){ hideCursors(); return; }   // use a normal cursor while magnified
  if(flipTool === 'liquify'){
    moveLiquifyCursor(e); eraserCursor.style.display='none'; brushCursor.style.display='none';
  }
  else if(erasing){ moveEraserCursor(e); brushCursor.style.display='none'; liquifyCursor.style.display='none'; }
  else { moveBrushCursor(e); eraserCursor.style.display='none'; liquifyCursor.style.display='none'; }
  // The badge is orthogonal to which ring is showing: every tool gets it, and
  // it is suppressed MID-STROKE rather than mid-tool. `drawing` alone, never
  // `erasing`: that flag is set from the TOOL (line 3087, `erasing = flipTool
  // === 'eraser'`), so including it hid the eraser's badge permanently rather
  // than for the length of a stroke -- caught by the assertion that every tool
  // shows one, which is why it is written over the whole roster.
  if(drawing) toolBadge.style.display='none';
  else moveToolBadge(e);
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
  document.body.classList.remove('stroking');   // aborted stroke: the chrome returns too
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
      pbDel=document.getElementById('pbDel');
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
  /* "21/43", not "Page 21 / 43". The word cost 40px in a bar that was ALREADY
     overflowing: nowrap, and at 360 its contents measured 369px inside 340,
     so the Delete button was being clipped off the end before any of tonight's
     work went near it. In a bar whose every other control is a page operation,
     sitting directly above a filmstrip of numbered pages, "Page" is a word
     spending real estate to say what the context already says.
     The ACCESSIBLE name keeps the full sentence — terse to look at, complete to
     listen to, which is the trade a visual abbreviation should always make. */
  // With a span lit, every control here means "these pages". Nothing is added
  // or hidden — the readout and the titles change, which is the whole of the
  // affordance. A control that silently changed scope would be worse than a
  // new button; one that says so is better than both.
  const sp = pageSpan();
  const cnt = sp ? SkriblPageSpan.count(sp) : 1;
  const these = sp ? 'these ' + cnt + ' pages' : 'this page';
  if(pbWho){
    pbWho.textContent = sp ? SkriblPageSpan.label(sp) + '/' + n
                           : (idx+1) + (n>1 ? '/' + n : '');
    const say = sp ? 'Pages ' + (sp.from+1) + ' to ' + (sp.to+1) + ' of ' + n
                   : 'Page ' + (idx+1) + (n>1 ? ' of ' + n : '');
    pbWho.setAttribute('aria-label', say);
    pbWho.title = say + (sp ? ' selected — Esc to drop the range' : '');
    pbWho.classList.toggle('span', !!sp);
  }
  if(pbLeft){ pbLeft.disabled = playing || (sp ? sp.from===0 : idx===0);
    pbLeft.title = 'Move ' + these + ' left'; }
  if(pbRight){ pbRight.disabled = playing || (sp ? sp.to===n-1 : idx===n-1);
    pbRight.title = 'Move ' + these + ' right'; }
  if(pbCopy){ pbCopy.disabled = playing; pbCopy.title = 'Copy ' + these; }
  if(pbDel){ pbDel.disabled = playing || n<=1 || cnt>=n;
    pbDel.title = 'Delete ' + these; }
  // pbHold's sync block lived here until v226. It was inert the moment the
  // button left the template — every line behind an `if(pbHold)` that could
  // never be true — and dead code that cannot run is worse than dead code that
  // can: it reads as a live feature to anyone scanning the function. The hold
  // is the tile's badge now, rebuilt by buildStrip from the frame each time.
}
if(pbLeft) pbLeft.addEventListener('click',()=>{ if(pbLeft.disabled) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; } spanMove(-1); });
if(pbRight) pbRight.addEventListener('click',()=>{ if(!pbRight.disabled) spanMove(1); });
if(pbCopy) pbCopy.addEventListener('click',()=>{ if(pbCopy.disabled) return; spanCopy(); });
// pbHold retired in v226: the hold badge on the tile is the control now, and it
// was already drawn there showing the value the button was cycling.
if(pbDel) pbDel.addEventListener('click',()=>{ if(pbDel.disabled) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; } spanDelete(); });

function buildStrip(){
  armedDel = -1;
  strip.innerHTML='';
  frames.forEach((f,i)=>{
    const el=document.createElement('div'); el.className='frame'+(i===idx?' on':'');
    // A span is drawn as ONE stretch of film, not as N ticked items: the run
    // shares a single outline, rounded only at its two outer ends, and the
    // number on the leading tile becomes the range. Reading "4–7" once beats
    // reading four highlighted tiles and counting them.
    const _sp = pageSpan();
    if(_sp && SkriblPageSpan.contains(_sp, i)){
      el.classList.add('inspan');
      if(i === _sp.from) el.classList.add('span-first');
      if(i === _sp.to) el.classList.add('span-last');
    }
    const _numTxt = (_sp && i === _sp.from) ? SkriblPageSpan.label(_sp) : String(i+1);
    // THE BADGE IS THE CONTROL (v226, stage 2). It used to render only when the
    // hold was above 1, which made it a readout: there was no way to START a
    // hold from the strip, so a page-bar button existed to do it. Now it is
    // always a button — and CSS keeps a ×1 badge hidden unless the tile is the
    // active one, hovered or focused, which is exactly the rule the delete ✕
    // already follows. A page with no hold still shows nothing.
    const _h = frameHold(f);
    el.innerHTML='<div class="num">'+_numTxt+'</div>'
      +'<button class="del" title="Delete frame">'+DEL_SVG+'</button>'
      +'<button class="holdbadge'+(_h>1?'':' idle')+'" '
        +'title="Hold this page longer — tap to cycle" '
        +'aria-label="Hold page '+(i+1)+', currently '+_h+' frame'+(_h===1?'':'s')+'">'
        +'\u00d7'+_h+'</button>'
      + (_compactStrip() ? '<button class="pageops" aria-haspopup="menu" '
          + 'aria-expanded="false" title="Page actions" '
          + 'aria-label="Actions for page ' + (i+1) + '">'
          + '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
          + '<circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/>'
          + '<circle cx="19" cy="12" r="1.7"/></svg></button>' : '')
      +'<canvas></canvas>';   // per-page controls: #pagebar on regular, the ⋯ on compact
    el.addEventListener('pointerdown',ev=>{
      if(playing) return;
      // Speak here, not only in the click handler: a real drag sets
      // _pdragSuppressClick, so the click that would have explained the
      // refusal never fires. Dragging a thumbnail during a move was the
      // one page operation that failed in complete silence.
      if(moveMode){ chip('Finish or cancel the move first'); return; }
      if(frames.length<2) return;
      if(ev.target.closest('.del') || ev.target.closest('.holdbadge')
         || ev.target.closest('.pageops')) return;
      // Shift is the desktop gesture: "…through here", from wherever you are.
      if(ev.shiftKey){ ev.preventDefault(); extendSpanTo(i); return; }
      // And touch gets the same reach without a modifier key: hold still for a
      // beat, then sweep. The two gestures cannot collide because they are
      // separated by what the finger does FIRST — move within 450ms and it is a
      // reorder, stay put and it becomes a sweep. Committing on the timer
      // rather than on movement is what makes it feel decided rather than
      // ambiguous, and the tile lifts so the change of mode is visible.
      clearTimeout(_spanHoldTimer);
      _spanHoldTimer = setTimeout(()=>{
        if(!_pdrag || _pdrag.moved) return;
        _pdrag = null; _spanSweep = true;
        setSpanAnchor(i);
        if(i !== idx) extendSpanTo(i); else buildStrip();
        if(navigator.vibrate) try{ navigator.vibrate(8); }catch(_){}
      }, 450);
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
      if(_spanSweep){ _spanSweep = false; return; }   // the sweep already chose
      if(ev.target.closest('.holdbadge')){
        ev.stopPropagation();
        holdCycle(i);
        return;
      }
      const ops = ev.target.closest('.pageops');
      if(ops){
        ev.stopPropagation();
        if(i !== idx) go(i);              // act on the page you opened it from
        openPageOps(ops, i);
        return;
      }
      const del = ev.target.closest('.del');
      if(del){
        if(f.strokes.length && armedDel !== i){
          disarmAll();
          armedDel = i; del.classList.add('armed'); del.title='Tap again to delete';
          return;
        }
        delFrame(i); return;
      }
      disarmAll();
      // A plain tap means "this page", so it retires the range rather than
      // quietly keeping one the user has visually moved past — the same rule
      // the stroke selection follows for a stray tap outside its box.
      if(!ev.shiftKey) clearSpan(true);
      go(i);
    });
    strip.appendChild(el); drawThumb(el.querySelector('canvas'), f);
    // THE PASTE GHOST (v226, stage 2). A button in the add column said WHAT;
    // it could not say WHERE, and "after the current page" is a rule the user
    // had to know rather than see. A dashed tile standing in the gap the pages
    // will occupy says both at once, and it disappears with the clipboard.
    if(pageClip && pageClip.length && i === idx && !playing && !moveMode){
      const n = pageClip.length;
      const g = document.createElement('button');
      g.type = 'button';
      g.className = 'frame ghost-paste';
      g.title = 'Paste ' + (n>1 ? n + ' copied pages' : 'the copied page') + ' here';
      g.setAttribute('aria-label', g.title);
      g.innerHTML = '<span class="ghost-plus" aria-hidden="true">+</span>'
                  + (n>1 ? '<span class="ghost-n">'+n+'</span>' : '');
      g.addEventListener('click', ev => { ev.stopPropagation(); spanPaste(); });
      strip.appendChild(g);
    }
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
    +'<button class="addbtn mini" id="addtween" title="Generate the motion between this page and the next, like a long exposure"><svg class="addbtn-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 6v12"/><path d="M19 6v12" opacity=".95"/><path d="M9.5 8.5v7" opacity=".55"/><path d="M14.5 8.5v7" opacity=".3"/></svg>In-between</button>'
    ;   // Paste is no longer here — see the ghost tile in buildStrip (v226).
  // The add controls live OUTSIDE the scrolling strip, as a row above the
  // thumbnails. Inside it they were its last child, so on a long flip they
  // scrolled away from the very page they act on; pinning them to the right
  // edge fixed the reach but still spent strip width on them at every size.
  // Out here they cannot scroll away at any width, need no scrim over the
  // thumbnails sliding under them, and give the strip its full width back.
  // buildStrip() empties `strip`, which used to sweep the old column away for
  // free -- out here the previous one has to be removed explicitly.
  const stripWrap = strip.parentNode;
  const prevCol = stripWrap.querySelector(':scope > .addcol');
  if(prevCol) prevCol.remove();
  stripWrap.insertBefore(col, strip);
  col.querySelector('#addcopy').addEventListener('click',()=>{ if(playing) return; if(moveMode){ chip('Finish or cancel the move first'); return; } addFrame(true); });
  col.querySelector('#addblank').addEventListener('click',()=>{ if(playing) return; if(moveMode){ chip('Finish or cancel the move first'); return; } addFrame(false); });
  col.querySelector('#addtween').addEventListener('click', addTween);
  syncPagebar();
  syncFlipDuration();
  if(typeof syncMoveLabel === 'function') syncMoveLabel();
  updateToolState();
}
/* ESCAPE DISMISSES THE TOPMOST THING, and a page range is the least topmost.
 *
 * Every other Escape claim in this file is "some surface is open", and those are
 * mutually exclusive in practice — one sheet at a time. A page range is not: it
 * can be selected while the overflow menu, the export sheet, the tune panel or
 * the help drawer is open, and without this guard one press would both close
 * the sheet AND silently drop a selection the user had not finished with.
 * KeyRegistry.collisions() exists to catch exactly that shape, and verify_keys
 * drives it.
 *
 * Read lazily, at press time: every one of these is declared further down the
 * file than this function, which is fine to REFERENCE from a body that only runs
 * after init but would throw if evaluated now.
 */
function flipOverlayOpen(){
  try{
    if(typeof moveMode !== 'undefined' && moveMode) return true;
    const menu = document.getElementById('moreMenu');
    if(menu && !menu.hidden) return true;
    const exp = document.getElementById('exportOverlay');
    if(exp && !exp.hidden) return true;
    if(typeof tuneIsOpen === 'function' && tuneIsOpen()) return true;
    // Read through the same variable the help drawer's own Escape claim reads,
    // so the two cannot drift. It is a `const` declared far below this line, and
    // `typeof` does NOT protect a const in its temporal dead zone — it throws
    // like any other access. That is what the try/catch around this body is for:
    // called at press time it is long since initialised, and called earlier
    // (which nothing does) it answers "not open" instead of taking the file down.
    if(helpDrawer && !helpDrawer.hidden) return true;
  }catch(_){ /* a surface that does not exist on this page is not open */ }
  return false;
}

/* ---- compact page actions (v227, stage 4) ----------------------------------
 * On the compact surface the persistent page bar is gone and this menu carries
 * what it carried. The design note is explicit that this step waits on ONE
 * thing: every operation must stay reachable and announced, because a filmstrip
 * you can only operate by dragging is a filmstrip some people cannot operate.
 *
 * So it is a real <button> with aria-haspopup on a tile that is in the tab
 * order, opening a real role="menu" of real buttons. Focus moves in on open and
 * returns to the trigger on close. Nothing here is hover-only and nothing is a
 * gesture — the gestures exist alongside it for people who find them, which is
 * the whole shape of the compact/regular split.
 *
 * It is only rendered on compact. On regular the page bar is still there and a
 * second route to the same five operations would be clutter, not redundancy.
 */
function _compactStrip(){
  return !!(window.SkriblSize && SkriblSize.isCompact());
}
let _opsMenu = null, _opsTrigger = null;
function closePageOps(refocus){
  if(!_opsMenu) return;
  _opsMenu.remove(); _opsMenu = null;
  if(_opsTrigger){
    _opsTrigger.setAttribute('aria-expanded', 'false');
    if(refocus) try{ _opsTrigger.focus(); }catch(_){}
  }
  _opsTrigger = null;
}
function openPageOps(trigger, i){
  closePageOps(false);
  const sp = pageSpan();
  const many = sp && SkriblPageSpan.contains(sp, i);
  const what = many ? 'these ' + SkriblPageSpan.count(sp) + ' pages' : 'this page';
  const n = frames.length;
  const items = [
    ['Move left',  'Move ' + what + ' left',  () => spanMove(-1),
     sp ? sp.from === 0 : i === 0],
    ['Move right', 'Move ' + what + ' right', () => spanMove(1),
     sp ? sp.to === n - 1 : i === n - 1],
    ['Copy',       'Copy ' + what,            () => spanCopy(),  false],
    ['Delete',     'Delete ' + what,          () => spanDelete(),
     n <= 1 || (sp && SkriblPageSpan.count(sp) >= n)],
  ];
  const m = document.createElement('div');
  m.className = 'pageops-menu';
  m.setAttribute('role', 'menu');
  m.setAttribute('aria-label', 'Actions for ' + what);
  items.forEach(([label, title, run, disabled], k) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'pageops-item' + (label === 'Delete' ? ' danger' : '');
    b.setAttribute('role', 'menuitem');
    b.textContent = label;
    // The visible label stays short ("Move left"); the SCOPE goes in the
    // accessible name, so a screen reader hears "Move these 3 pages left" while
    // the menu stays scannable. title as well, for the pointer tooltip — note
    // lib/tooltip.js adopts [title] into data-tip and REMOVES the attribute, so
    // aria-label is also the only one of the two that survives to be read back.
    b.title = title;
    b.setAttribute('aria-label', title);
    b.disabled = !!disabled;
    b.addEventListener('click', () => { closePageOps(false); run(); });
    m.appendChild(b);
  });
  document.body.appendChild(m);
  // Anchored to the trigger and clamped to the window, so a menu opened on the
  // last tile of a scrolled strip does not hang off the edge.
  const r = trigger.getBoundingClientRect(), mr = m.getBoundingClientRect();
  let left = Math.min(r.left, window.innerWidth - mr.width - 8);
  m.style.left = Math.max(8, left) + 'px';
  m.style.top = Math.max(8, r.top - mr.height - 6) + 'px';
  trigger.setAttribute('aria-expanded', 'true');
  _opsMenu = m; _opsTrigger = trigger;
  const first = m.querySelector('.pageops-item:not(:disabled)');
  if(first) try{ first.focus(); }catch(_){}
  // Arrow keys walk the menu, Escape returns you where you were. A menu you can
  // open with the keyboard and not leave with it is worse than no menu.
  m.addEventListener('keydown', e => {
    const btns = [...m.querySelectorAll('.pageops-item:not(:disabled)')];
    const at = btns.indexOf(document.activeElement);
    if(e.key === 'Escape'){ e.preventDefault(); closePageOps(true); return; }
    if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
      e.preventDefault();
      const nx = e.key === 'ArrowDown' ? at + 1 : at - 1;
      const t = btns[(nx + btns.length) % btns.length];
      if(t) t.focus();
    }
  });
}
document.addEventListener('pointerdown', e => {
  if(_opsMenu && !e.target.closest('.pageops-menu') && !e.target.closest('.pageops')){
    closePageOps(false);
  }
});
// The strip is rebuilt when the class flips, because the ⋯ exists on one side of
// the boundary and not the other. Without this a window resized past 640 keeps
// whichever surface it happened to load with.
document.addEventListener('skribl:size', () => { closePageOps(false); buildStrip(); });

/* Keyboard. This is where a range earns its keep on desktop: shift-arrow to
   grow one, Escape to drop it, and the copy/paste pair everyone already has in
   their fingers. None of it adds a pixel of interface, which is the only reason
   a feature this size fits the direction at all.

   Registered with KeyRegistry so the shortcut sheet lists them; the handler is
   bound separately, as every other shortcut here is. */
if(window.KeyRegistry){
  KeyRegistry.register({surface:'flip', label:'select a run of pages',
    keys:['Shift+ArrowLeft','Shift+ArrowRight'], scope:()=>frames.length>1});
  KeyRegistry.register({surface:'flip', label:'drop the page range',
    keys:['Escape'], scope:()=>pageSpan()!==null && !flipOverlayOpen()});
  KeyRegistry.register({surface:'flip', label:'copy the page or range',
    keys:['Mod+c'], scope:()=>!playing});
  KeyRegistry.register({surface:'flip', label:'paste copied pages',
    keys:['Mod+v'], scope:()=>!!(pageClip && pageClip.length)});
}
document.addEventListener('keydown', e=>{
  if(playing || moveMode) return;
  // Never steal a key from a text field — the share sheet's title and caption
  // inputs live on this page, and Cmd+C in one of them must copy the TEXT.
  // typingTarget() is the existing answer to this question in this file; a
  // second copy of the same predicate is how the two drift apart.
  if(typeof typingTarget === 'function' && typingTarget(e.target)) return;
  if(e.key === 'Escape' && pageSpan() && !flipOverlayOpen()){
    e.preventDefault(); clearSpan(); render(); return;
  }
  if(e.shiftKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')){
    if(frames.length < 2) return;
    e.preventDefault();
    extendSpanTo(idx + (e.key === 'ArrowLeft' ? -1 : 1));
    return;
  }
  const mod = e.metaKey || e.ctrlKey;
  if(mod && !e.shiftKey && !e.altKey && (e.key === 'c' || e.key === 'C')){
    e.preventDefault(); spanCopy(); return;
  }
  if(mod && !e.shiftKey && !e.altKey && (e.key === 'v' || e.key === 'V')){
    if(!(pageClip && pageClip.length)) return;
    e.preventDefault(); spanPaste(); return;
  }
});

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
    // The hint has to name the control the user actually pressed. On the
    // compact surface there are no arrows — the move came from the tile's ⋯
    // menu (v227) — and a hint that describes a control the surface does not
    // have is worse than no hint: it sends the reader looking for it.
    const via = _compactStrip() ? 'This' : 'These arrows';
    window.SkriblHints.show('page-move',
      'Moved this page to position ' + to + '. ' + via + ' REORDERS pages — '
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
/* A sweep extends the span to whichever tile the finger is over. Hit-testing
   the tile under the pointer rather than accumulating dx means a sweep that
   wanders vertically off the strip and back still lands on the right pages. */
document.addEventListener('pointermove', ev=>{
  if(!_spanSweep) return;
  const el = document.elementFromPoint(ev.clientX, ev.clientY);
  const tile = el && el.closest && el.closest('#strip .frame');
  if(!tile) return;
  const i = [...strip.children].indexOf(tile);
  if(i >= 0 && i !== idx){ ev.preventDefault(); extendSpanTo(i); }
});
document.addEventListener('pointerup', ()=>{ _spanSweep = false; });
document.addEventListener('pointercancel', ()=>{ _spanSweep = false; });
document.addEventListener('pointermove', ev=>{
  if(!_pdrag) return;
  const dx=ev.clientX-_pdrag.startX;
  if(!_pdrag.moved && Math.abs(dx)<6) return;
  // Moving cancels the pending sweep: this is a reorder, decided by the finger.
  clearTimeout(_spanHoldTimer);
  if(!_pdrag.moved){ _pdrag.moved=true; _pdrag.el.classList.add('dragging'); }
  ev.preventDefault();
  _pdrag.el.style.transform='translateX('+dx+'px)';
});
document.addEventListener('pointerup', ()=>{
  clearTimeout(_spanHoldTimer);
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
  // Dropping a tile that is part of a span moves the whole run. Anything else
  // would mean dragging one page out of a selection you just made, which is
  // never the intention — and lib/pagespan owns the index arithmetic that makes
  // a rightward move land where it looks like it should.
  const sp = pageSpan();
  if(sp && SkriblPageSpan.contains(sp, d.i)){
    let before = 0;
    for(let k=0;k<centers.length;k++){ if(x>centers[k]) before=k+1; }
    const keep = idx - sp.from, n = SkriblPageSpan.count(sp);
    const moved = SkriblPageSpan.moveSpan(frames, sp, before);
    if(moved.length === frames.length){
      frames = moved;
      const landed = before <= sp.from ? before : before - n;
      setSpanAnchor(landed); idx = landed + keep;
      buildStrip(); render(); scheduleSave(); scrollStripToActive(true);
    }
    return;
  }
  if(target>d.i) target--;
  target=Math.max(0, Math.min(frames.length-1, target));
  movePageTo(d.i, target);
});
document.addEventListener('pointermove', ev=>{ if(_pdrag) _pdrag.lastX=ev.clientX; });
document.addEventListener('pointercancel', ()=>{
  clearTimeout(_spanHoldTimer);
  if(!_pdrag) return;
  _pdrag.el.style.transform=''; _pdrag.el.classList.remove('dragging'); _pdrag=null;
});
/* The app's ONE size decision. Started here, near the top, because every
   migrated CSS rule keys off the attribute it stamps — an unclassified root
   gets the compact form of all of them, which on a desktop is the 641px cliff
   this is meant to end. */
if(window.SkriblSize) SkriblSize.observe(document.body);

/* ---- page spans ------------------------------------------------------------
 * A run of pages, selected on the strip and operated on by the controls that
 * were already there. DESIGN-DIRECTION is explicit that page management is
 * direct manipulation on the film and NOT a management cluster — "the object
 * itself is manipulable" — so this adds no button. What it adds is that Copy,
 * Delete, ×hold and the two arrows mean "these pages" instead of "this page"
 * whenever more than one is lit.
 *
 * The geometry lives in lib/pagespan.js, headless and tested there. What lives
 * HERE is only the two numbers that say which pages, and the rule that keeps
 * them honest: `idx` is always one end of the span, so moving the current page
 * moves the span with it and there is no way to have a selection that does not
 * include the page you are looking at. That rule is what makes re-scoping the
 * existing controls safe rather than surprising — every one of them already
 * acted on `idx`, and it still does.
 */
function pageSpan(){
  if(spanAnchor == null || !window.SkriblPageSpan) return null;
  const s = SkriblPageSpan.normalise(spanAnchor, idx, frames.length);
  return s && s.from !== s.to ? s : null;         // one page is not a span
}
function spanOrCurrent(){
  const s = pageSpan();
  return s || { from: idx, to: idx };
}
function setSpanAnchor(a){
  spanAnchor = (a == null) ? null : Math.max(0, Math.min(frames.length - 1, a));
}
function clearSpan(quiet){
  if(spanAnchor == null) return false;
  spanAnchor = null; _spanSweep = false;
  if(!quiet){ buildStrip(); }
  return true;
}
/* Extend to `i`, anchoring at the page you are on if nothing is anchored yet.
   Shift-click reads as "…through here", which only means anything relative to
   where you already are. */
function extendSpanTo(i){
  if(playing || moveMode) return;
  if(spanAnchor == null) setSpanAnchor(idx);
  const to = Math.max(0, Math.min(frames.length - 1, i));
  if(to !== idx){ if(typeof selClear === 'function') selClear(true); idx = to; }
  buildStrip(); render(); scrollStripToActive(true);
}
function spanCopy(){
  const s = spanOrCurrent();
  pageClip = SkriblPageSpan.extract(frames, s).map(deepCopy);
  buildStrip();
  chip(pageClip.length > 1
    ? pageClip.length + ' pages copied — use ＋ Paste'
    : 'Page copied — use ＋ Paste');
}
function spanDelete(){
  const s = pageSpan();
  if(!s) return delFrame(idx);                    // unchanged single-page path
  if(SkriblPageSpan.count(s) >= frames.length){
    // Deleting every page would leave a pageless flipbook. delFrame's own
    // one-page case already answers this: reset to a single blank rather than
    // refuse, so "clear the whole thing" stays reachable.
    chip('That is every page — use Clear all');
    return;
  }
  invalidateClearUndo(); redoStack.length = 0;
  const n = SkriblPageSpan.count(s);
  frames = SkriblPageSpan.remove(frames, s);
  idx = Math.max(0, Math.min(frames.length - 1, s.from));
  clearSpan(true);
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true);
  chip(n + ' pages deleted');
}
/* Cycle the hold on ONE tile — or on the whole run, if that tile is part of a
   selected one. Scoping it to what the tile belongs to is the same rule every
   other re-scoped control follows, so tapping a badge inside a range does not
   silently break the range apart. */
function holdCycle(i){
  if(playing || moveMode) return;
  const sp = pageSpan();
  if(sp && SkriblPageSpan.contains(sp, i)) return spanHold();
  invalidateClearUndo();
  frames[i].hold = (frameHold(frames[i]) % MAX_HOLD) + 1;
  buildStrip(); scheduleSave(); syncFlipDuration();
}
function spanHold(){
  // One tap sets EVERY page in the span to the same hold, cycling from the
  // first page's value. Cycling each page independently would make the second
  // tap scatter them, which is the opposite of what selecting a range is for.
  const s = spanOrCurrent();
  invalidateClearUndo();
  const next = (frameHold(frames[s.from]) % MAX_HOLD) + 1;
  for(let i = s.from; i <= s.to; i++) frames[i].hold = next;
  buildStrip(); scheduleSave();
  if(s.from !== s.to) chip('×' + next + ' on ' + (s.to - s.from + 1) + ' pages');
}
/* Nudge the span one slot. `dir` is -1 or +1. The span keeps its selection and
   `idx` keeps its page, so holding an arrow walks a run across the film. */
function spanMove(dir){
  const s = pageSpan();
  if(!s) return movePage(idx, dir);               // unchanged single-page path
  const to = dir < 0 ? s.from - 1 : s.to + 2;     // insert before this original
  if(to < 0 || to > frames.length) return;
  const n = SkriblPageSpan.count(s), keep = idx - s.from;
  frames = SkriblPageSpan.moveSpan(frames, s, to);
  const landed = dir < 0 ? s.from - 1 : s.from + 1;
  setSpanAnchor(landed);
  idx = landed + keep;
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true);
}
function spanPaste(){
  if(playing || moveMode || !pageClip || !pageClip.length) return;
  invalidateClearUndo(); redoStack.length = 0;
  const pages = pageClip.map(deepCopy);
  frames = SkriblPageSpan.insert(frames, idx + 1, pages);
  // The pasted run lands selected. A paste you then have to re-select before
  // moving is two gestures for one intention.
  setSpanAnchor(idx + 1);
  idx = idx + pages.length;
  if(pages.length === 1) clearSpan(true);
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true);
}

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
function addFrame(copy){ if(moveMode) return; disarmAll(); invalidateClearUndo(); redoStack.length=0; clearSpan(true); const f=copy?deepCopy(frame()):newFrame(); frames.splice(idx+1,0,f); idx++; buildStrip(); render(); scheduleSave();
  scrollStripToActive(true); }
function delFrame(i){ if(moveMode) return; invalidateClearUndo(); redoStack.length=0;
  // A range is a pair of INDICES, so any page count change that this function
  // makes invalidates it. Dropping it here rather than trying to fix it up is
  // deliberate: the same reasoning the stroke selection uses when you change
  // page — a stale range would operate on artwork the user never picked.
  clearSpan(true);
  if(frames.length===1){ frames[0]=newFrame(); idx=0; }
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
  // Shift joins the modifiers this declines because Shift+Arrow now EXTENDS a
  // page range (v226). Without it both handlers ran and a single press moved
  // two pages — the range grew twice as fast as the key was pressed, which
  // reads as the selection being broken rather than as two features colliding.
  if(typingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
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

/* v262: a page is rasterised at most ONCE per playback. Repainting a generated
   in-between costs ~123ms at 4x CPU throttle (a mid-range phone) even after the
   v261 rebuild, against a 41.7ms slot at 24fps — no point budget makes
   re-rasterising the same static picture every loop fit. So the first paint of
   a heavy page is captured as a bitmap and every later visit blits it (~1ms).
   The rule — which pages earn a bitmap, the memory ceiling, the capture
   resolution — lives in lib/framebitmap.js, shared with the player, so the two
   surfaces cannot drift on it. The store lives from play() to stop() and is
   keyed by the frame OBJECT: any path that replaces a page misses safely, and
   nothing that mutates a page in place can run while playing. */
let playBitmaps = null;
/* A blit's measured cost, kept apart from framePaintMs: the moment a page is
   captured, its recorded paint cost describes a rasterisation that will never
   happen again, and feeding that stale number to the scheduler makes every
   cached loop RUSH — measured at 1.5s for a 1.92s loop, visibly fast. wait()
   asks which book the upcoming frame is in. */
let blitMs = null;
function playPaint(){
  const f = frames[idx];
  const FB = window.SkriblFrameBitmap;
  const hit = FB ? FB.get(playBitmaps, f) : null;
  if(hit){
    ctx.clearRect(0,0,CW,CH);
    ctx.drawImage(hit, 0, 0, CW, CH);
    return true;
  }
  render();
  if(FB && f && playBitmaps){
    // Captured from the visible pad AFTER its own render, so the bitmap is the
    // exact composite this playback just showed — at the resolution it was
    // shown at, which is what bounds the memory (see the lib header).
    const rect = pad.getBoundingClientRect();
    const sz = FB.captureSize(CW * DPR, CH * DPR, rect.width * DPR, rect.height * DPR);
    if(FB.wants(playBitmaps, f.strokes.length, sz.w, sz.h))
      FB.capture(playBitmaps, f, pad, sz.w, sz.h);
  }
  return false;
}
function playStep(){ if(scrubbingFrames) return;
  idx=playI%frames.length;
  const _t0 = performance.now();
  const _blit = playPaint();
  const _cost = performance.now() - _t0;
  if(_blit){
    // A blit REPLACES the frame's book entry rather than blending in: the EMA
    // exists to smooth noisy repaint costs, and a 215ms rasterisation blended
    // 60/40 with a 15ms blit stays wrong for three more loops.
    blitMs = blitMs == null ? _cost : blitMs * 0.6 + _cost * 0.4;
    framePaintMs[idx] = _cost;
  } else {
    framePaintMs[idx] = framePaintMs[idx] == null ? _cost
                                                  : framePaintMs[idx] * 0.6 + _cost * 0.4;
    const _pts = frames[idx] ? frames[idx].strokes.length : 0;
    if(_pts > 0){
      const _rate = _cost / _pts;
      msPerPoint = msPerPoint ? msPerPoint * 0.7 + _rate * 0.3 : _rate;
    }
  }
  updatePlayProgress();
  liveBadge.textContent='\u25B6 '+(idx+1)+' / '+frames.length; playI++;
}
// Was a fixed setInterval. With per-page holds each step has its own delay, so it
// re-schedules itself. playTimer holds a timeout id now — stop() clears both.
//
// The delay used to start counting from the moment a paint FINISHED, which
// means every frame stayed on screen for its own interval PLUS whatever the
// NEXT frame cost to draw. That was invisible while every page cost the same;
// a blurred in-between is ~6,000 points against a key page's 45, and measured
// at 12fps the page before each blur held 127ms against a target of 83 — half
// again as long. Watching it, that reads as the animation sticking around the
// blurred slides, which is exactly how it was reported.
//
// The clock is absolute now. Each frame is due at a running target and the wait
// is whatever is left of that target after the paint, so drawing cost comes out
// of the interval instead of being added to it.
function runPlayTimer(){
  clearInterval(playTimer); clearTimeout(playTimer);
  // A frame becomes visible when its paint COMPLETES, so its visible duration
  // is the wait plus whatever the next frame costs to draw. Scheduling a flat
  // interval therefore stretches every frame by the cost of the one after it —
  // invisible while all pages cost the same, obvious once a blurred in-between
  // (~6,000 points) sits next to a key page (45). Measured at 12fps, the page
  // before each blur held 127ms against a target of 83.
  //
  // So the wait is the interval MINUS what the upcoming paint is expected to
  // cost, and the expectation is measured rather than assumed. An earlier
  // version of this accumulated a running due-time and corrected against it,
  // which drifted: a wrong estimate was banked and the next frame inherited
  // the error. Each frame now stands on its own.
  const wait = () => {
    // playStep() has ALREADY painted and advanced playI, so the frame on screen
    // is the one before it -- and playI is never wrapped, it just grows. Both
    // of those were wrong here, in ways that hid each other:
    //   * without the -1 the delay came from the NEXT frame's hold, so a hold
    //     stretched the page BEFORE the one that declared it;
    //   * without the modulo frames[playI] is undefined from the second time
    //     round the loop, frameHold() falls back to 1, and every hold in the
    //     document is silently ignored for the whole rest of playback.
    // Measured on a 30-page flip with hold=2 on pages 12 and 23: page 11 held
    // 167.9ms and page 12 held 83.5ms on the first pass, and nothing held at
    // all on any pass after it. The shared player builds a cumulative hold
    // table and gets this right, so the editor was disagreeing with what a
    // viewer actually sees.
    const cur = (playI - 1 + frames.length) % frames.length;
    // slotMs takes the FRAME, not a hold read off it, so this cannot go back
    // to reading the hold off the wrong page — which is what it used to do.
    const d = (typeof window !== 'undefined' && window.SkriblHold)
      ? window.SkriblHold.slotMs(frames[cur], fps)
      : (1000 / fps) * frameHold(frames[cur]);
    const ni = playI % frames.length;
    // An unpainted frame is estimated from its point count at the going rate,
    // so the FIRST play-through is even too — that is the one you watch after
    // pressing the button.
    // A frame with a bitmap will BLIT, whatever its book says: its recorded
    // cost may describe the rasterisation that filled the cache, and using it
    // makes every cached loop rush. First blit of a playback has no measured
    // cost yet — a small constant beats a 200ms lie.
    const cachedNext = playBitmaps && window.SkriblFrameBitmap
      && window.SkriblFrameBitmap.get(playBitmaps, frames[ni]);
    const est = cachedNext
      ? (blitMs != null ? blitMs : 8)
      : framePaintMs[ni] != null
        ? framePaintMs[ni]
        : (frames[ni] ? frames[ni].strokes.length * msPerPoint : 0);
    return Math.max(0, d - est);
  };
  playStep();
  const step = () => { playStep(); playTimer = setTimeout(step, wait()); };
  playTimer = setTimeout(step, wait());
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
  playBitmaps = window.SkriblFrameBitmap ? window.SkriblFrameBitmap.store() : null;
  if(drawOnMode){ dFrame=0; idx=0; startDrawOnFrame(); }
  else { playI=idx; runPlayTimer(); }
}
function stop(){
  playBitmaps = null;                 // playback-scoped: freed the moment it ends
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
/*! Some tool glyphs below are Lucide icons, SCALED (paths otherwise unaltered).
 *  lucide-static 1.37.0 — ISC © 2026 Lucide Icons and Contributors
 *  https://github.com/lucide-icons/lucide  (some icons derive from Feather,
 *  MIT © 2013-2017 Cole Bemis). Currently: `paint-bucket` (Fill), `stamp`
 *  (Stamps), `waves` (Liquify), `square-dashed-mouse-pointer` (Select) and
 *  `shapes` (Shape, in the templates). Everything else here is drawn for
 *  this project.
 *
 *  WHY THEY ARE SCALED, which was not expected. This project's icon spec is
 *  Lucide's on paper — 24x24 box, 2px stroke, round caps and joins — so these
 *  should have dropped straight in. Measured, they did not: Lucide draws to the
 *  full box and both came in at 22.0-22.2 units of ink against a set that sits
 *  near 19, which is 15% larger and correspondingly heavier than the eight
 *  glyphs beside them. In a row of ten that reads as a mistake.
 *
 *  So each is scaled 0.88 about the box centre and its authored stroke raised to
 *  2.27, which lands the RENDERED stroke back on the set's 2px. The drawing is
 *  Lucide's, untouched; only its size in our box is ours. An icon is judged in
 *  the row it sits in, and consistency across the row beats fidelity to any one
 *  glyph's native scale.
 */
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
        { id: 'select', label: 'Select', btn: 'selectToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2.27" stroke-linecap="round" stroke-linejoin="round">'
              + '<g transform="translate(12 12) scale(0.88) translate(-12 -12)">'
              + '<path d="M12.034 12.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.943'
              + 'l-3.444 1.068a1 1 0 0 0-.66.66l-1.067 3.443a.5.5 0 0 1-.943.033z"/>'
              + '<path d="M5 3a2 2 0 0 0-2 2"/><path d="M19 3a2 2 0 0 1 2 2"/>'
              + '<path d="M5 21a2 2 0 0 1-2-2"/><path d="M9 3h1"/><path d="M9 21h2"/>'
              + '<path d="M14 3h1"/><path d="M3 9v1"/><path d="M21 9v2"/>'
              + '<path d="M3 14v1"/></g></svg>' },
        // LUCIDE `waves`. Still the flattest icon here by a distance and still
        // exempt from the height floor, for the same reason the hand-drawn smear
        // was: a warp is wide and low. Cleaner than the smear at 24px, which is
        // the size that decides.
        { id: 'liquify', label: 'Liquify', btn: 'liquifyToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2.13" stroke-linecap="round" stroke-linejoin="round">'
              + '<g transform="translate(12 12) scale(0.94) translate(-12 -12)">'
              + '<path d="M2 12q2.5 2 5 0t5 0 5 0 5 0"/>'
              + '<path d="M2 19q2.5 2 5 0t5 0 5 0 5 0"/>'
              + '<path d="M2 5q2.5 2 5 0t5 0 5 0 5 0"/></g></svg>' },
        // A THUMBPRINT -- Lucide's `fingerprint`, at the set's scale and stroke.
        //
        // THE HAND DID NOT SURVIVE 24px, AND THE PROBLEM WAS THE REFERENCE, not
        // the trace. The owner's reference is a hand with a thumb, curled
        // fingers and an extended index; it reads as a hand because it is drawn
        // large. Traced into a 24 box the strokes are wider than the gaps
        // between the fingers, so they fuse. Four versions were rendered at 86px
        // and at tray size -- faithful, one curl dropped, silhouette only, and
        // opened out at the set's weight -- and every one of them was a squiggle
        // at the size that matters. Simplifying further only made a simpler
        // squiggle. That is arithmetic, not craft, and no further attempt at it
        // is worth anyone's time.
        //
        // A thumbprint is the thing that DOES the smudging, it is one closed
        // form rather than five thin ones, and its concentric arcs are legible
        // at any size. It is also unmistakable against its neighbours: Liquify's
        // three waves run horizontally and Blur's halos are concentric CIRCLES,
        // where this is an arch open at the bottom.
        //
        // THE LESSON, since this slot has now taken four icons: test at 24px
        // BEFORE shipping, not at 4x. The hand that shipped was admired at 4x
        // and was never once looked at the size a person actually sees it.
        { id: 'smudge', label: 'Smudge', btn: 'smudgeToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2.27" stroke-linecap="round" stroke-linejoin="round">'
              + '<g transform="translate(12 12) scale(0.88) translate(-12 -12)">'
              + '<path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/>'
              + '<path d="M14 13.12c0 2.38 0 6.38-1 8.88"/>'
              + '<path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/>'
              + '<path d="M2 12a10 10 0 0 1 18-6"/>'
              + '<path d="M2 16h.01"/>'
              + '<path d="M21.8 16c.2-2 .131-5.354 0-6"/>'
              + '<path d="M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2"/>'
              + '<path d="M8.65 22c.21-.66.45-1.32.57-2"/>'
              + '<path d="M9 6.8a6 6 0 0 1 9 5.2v2"/></g></svg>' },
        // BLUR SHOULD LOOK BLURRY, which the concentric outlined rings it had did
        // not -- they read as a target. A filled core inside progressively larger,
        // fainter filled halos is what defocus actually looks like, and it
        // survives 24px because it has no internal edges to lose.
        //
        // The one icon in the tray that is a soft form rather than a line
        // drawing, and deliberately so: it is the only tool whose whole subject
        // is softness. Do not "tidy" it into outlined rings again.
        { id: 'blur', label: 'Blur', btn: 'blurToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              + '<circle cx="12" cy="12" r="9.2" fill="currentColor" stroke="none" opacity=".13"/>'
              + '<circle cx="12" cy="12" r="6.6" fill="currentColor" stroke="none" opacity=".22"/>'
              + '<circle cx="12" cy="12" r="4.2" fill="currentColor" stroke="none" opacity=".45"/>'
              + '<circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/></svg>' },
        // A TIPPED CAN POURING, WITH ONE DROP -- Lucide's `paint-bucket`, at the
        // set's scale and stroke.
        //
        // This slot took three hand-drawn versions before this one: a plain
        // drop, a squarish bucket, and a can traced from the owner's reference
        // with a wire handle. The traced one was the closest and still wrong --
        // its body read as a tilted diamond and the open arc of its handle read
        // as a break in the outline rather than as a wire.
        //
        // WHAT THE HAND-DRAWN ONES ALL MISSED is not shape, it is company. The
        // four icons in this tray that were never complained about -- Shape,
        // Select, Liquify, Stamps -- are Lucide, and an improvised icon beside a
        // professionally drawn set reads as improvised no matter how carefully
        // it is measured. Matching the SPEC (box, stroke, area band) is not the
        // same as matching the HAND.
        { id: 'fill', label: 'Fill', btn: 'fillToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2.27" stroke-linecap="round" stroke-linejoin="round">'
              + '<g transform="translate(12 12) scale(0.88) translate(-12 -12)">'
              + '<path d="M11 7 6 2"/>'
              + '<path d="M18.992 12H2.041"/>'
              + '<path d="M21.145 18.38A3.34 3.34 0 0 1 20 16.5a3.3 3.3 0 0 1-1.145 1.88'
              + 'c-.575.46-.855 1.02-.855 1.595A2 2 0 0 0 20 22a2 2 0 0 0 2-2.025'
              + 'c0-.58-.285-1.13-.855-1.595"/>'
              + '<path d="m8.5 4.5 2.148-2.148a1.205 1.205 0 0 1 1.704 0l7.296 7.296'
              + 'a1.205 1.205 0 0 1 0 1.704l-7.592 7.592a3.615 3.615 0 0 1-5.112 0'
              + 'l-3.888-3.888a3.615 3.615 0 0 1 0-5.112L5.67 7.33"/></g></svg>' },
        { id: 'stamp', label: 'Stamps', btn: 'stampToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2.27" stroke-linecap="round" stroke-linejoin="round">'
              + '<g transform="translate(12 12) scale(0.88) translate(-12 -12)">'
              + '<path d="M14 13V8.5C14 7 15 7 15 5a3 3 0 0 0-6 0c0 2 1 2 1 3.5V13"/>'
              + '<path d="M20 15.5a2.5 2.5 0 0 0-2.5-2.5h-11A2.5 2.5 0 0 0 4 15.5V17'
              + 'a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1z"/>'
              + '<path d="M5 22h14"/></g></svg>' },
        { id: 'artmove', label: 'Artwork', btn: 'artmoveToolBtn',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              + '<path d="M12 4v16M4 12h16M12 4l-2.5 2.5M12 4l2.5 2.5'
              + 'M12 20l-2.5-2.5M12 20l2.5-2.5M4 12l2.5-2.5M4 12l2.5 2.5'
              + 'M20 12l-2.5-2.5M20 12l-2.5 2.5"/></svg>' },
      ],
      currentTool: () => flipTool,
      slider: document.getElementById('toolSlider'),
      // THE SHAPE PICKER OPENS HERE, and it has to, because this is the only
      // point BOTH selection paths pass through. It used to live on a click
      // handler bound to '#toolGroup .tool-btn' -- the SHELF -- which was
      // complete until v227 put a tray in front of the shelf. After that,
      // choosing Shape from the tray never ran that handler, so the picker
      // never opened and Shape silently stayed on whatever kind it had:
      // 'line', for everyone who had never had Shape on the shelf. Reported
      // from the live demo as "shape is not giving a choice, just gives you
      // line".
      //
      // Toggling only when Shape was ALREADY current keeps the shelf's
      // press-again-to-close feel without making the first pick a no-op.
      setTool: (id) => {
        const was = flipTool;
        // READ THE SHELF BEFORE setTool REDERIVES IT. setTool() sets
        // stampPop.hidden from the active tool, so a toggle written after the
        // call sees false every time and can only ever CLOSE -- the shelf would
        // shut on the second tap and never come back on the third.
        const _spWas = document.getElementById('stampPop');
        const _spWasHidden = _spWas ? _spWas.hidden : true;
        setTool(id);
        const pop = document.getElementById('shapePop');
        if (pop) pop.hidden = (id !== 'shape') ? true
                            : (was === 'shape' ? !pop.hidden : false);
        // THE STAMP SHELF IS NOT HANDLED HERE, and that is the point. setTool()
        // itself derives the shelf's visibility from which tool is active, so
        // EVERY route in opens it — shelf, tray, keyboard, a call from another
        // feature — rather than the three that happen to pass through this
        // config today. The shape picker above is the version that did not, and
        // v237 is the bug report: the tray became a second route to Shape and
        // the picker stopped appearing for anyone who reached it that way.
        //
        // All that is left here is the deliberate override: tapping the tool
        // button while its own tool is already active TOGGLES the shelf, so it
        // can be put away without leaving the tool -- reported from the live
        // demo as "the stamp library doesn't go away until another tool is
        // chosen". Applied after setTool, against the state read before it.
        if (id === 'stamp' && was === 'stamp' && _spWas) {
          _spWas.hidden = !_spWasHidden;
          if (!_spWas.hidden) syncStampPop();
        }
      },
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
  // Artwork IS the move mode (v226). Entering and leaving it through the shelf
  // rather than through a page-bar toggle is the whole of the reclassification
  // — setMoveMode still owns what the mode does. The moveMode checks guard
  // against re-entering a mode already running, which would re-capture the
  // origin mid-drag and lose the offset the user had built up.
  if(flipTool === 'artmove'){ if(!moveMode) setMoveMode(true); }
  else if(moveMode) setMoveMode(false);
  // Records the MRU, re-syncs the shelf and repaints the tray's pressed state.
  if (toolShelf) toolShelf.noteUse(flipTool);
  const active = activeToolBtn();
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.toggle('active', b === active));
  positionToolSlider();
  // moveMode owns the cursor while it is running. This line used to be an
  // unconditional 'none' for the custom brush cursor, which clobbered the grab
  // cursor setMoveMode had set moments earlier in this same function once
  // Artwork became a tool — the mode was live and the canvas did not say so.
  // Fill is a TAP, so it wants a pointer rather than the custom brush ring —
  // 'none' hides the system cursor for a brush ring that fill never draws,
  // which left the canvas with no cursor at all under this tool.
  // THE SHELF IS THE STAMP TOOL'S UI, not a popover that happens to open near
  // it. Without an armed stamp the tool does nothing at all, so "which stamp is
  // loaded" has to stay on screen for as long as the tool is selected — and
  // deriving that from flipTool here, rather than toggling it at whichever call
  // site the user came through, is what makes a fourth route impossible to
  // forget. (The shape picker is toggled at a call site and that is exactly how
  // it went missing when the tray arrived; it is left as it is because its own
  // routing is settled, not because this is the same problem twice.)
  const _sp = document.getElementById('stampPop');
  if(_sp){ _sp.hidden = (flipTool !== 'stamp'); if(!_sp.hidden) syncStampPop(); }
  // Fill and Stamp are both TAPS and neither draws a brush ring, so 'none'
  // would leave the canvas with no cursor at all under them.
  pad.style.cursor = moveMode ? 'grab'
    : ((flipTool === 'fill' || flipTool === 'stamp') ? 'crosshair' : 'none');
  if(typeof eraserCursor!=='undefined' && !erasing) eraserCursor.style.display='none';
  if(typeof brushCursor!=='undefined' && erasing) brushCursor.style.display='none';
  // Each ring belongs to one tool; leaving a tool must take its ring with it,
  // or the last one drawn hangs around over the canvas until the next move.
  if(typeof liquifyCursor!=='undefined' && flipTool !== 'liquify') liquifyCursor.style.display='none';
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
if(window.SkriblPalette) window.SkriblPalette.mount(colorGroup, { before: customWrap,
  onPick:(hex)=>{ setColor(hex); closePop(); } });
// custom color picker (static markup)
// --custom-color + has-color, never an inline background: the CSS keeps the
// rainbow as a ring so the swatch still reads as the picker (Pad matches).
customInput.addEventListener('input',e=>{
  customBtn.style.setProperty('--custom-color', e.target.value);
  customBtn.classList.add('has-color');
  setColor(e.target.value);
});
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
    // Beyond tracking the armed flag: the draw popout covers nearly the whole
    // canvas on a phone, so while armed it is VEILED — visibility only, never
    // the drawer state machine, whose onClose hook would disarm the pick it
    // is making room for. It reappears the moment picking ends unpicked;
    // an actual pick still closes it for real (onPick → closePop).
    onChange: v => { picking = v;
                     drawPanel.classList.toggle('eyedropper-veiled', v); },
    // Loupe wiring: magnifies and reads the same composited artwork
    // sampleColorAt reads — onion skin and guides stay invisible to it.
    getPoint: ev => pos(ev),
    artwork: () => paintArtwork(),
    dpr: () => DPR,
    bg: () => bgColor,
    onPick: hex => { setColor(hex); addRecent(hex); closePop(); },
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
// The draw popout's half detent (phones) — twin of Pad's attach; the lib is
// shared, the close hand-off is this surface's own machine.
if (window.SkriblDrawerDetent) {
  window.SkriblDrawerDetent.attach(drawPanel, { close: () => closePop() });
}
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
  if(fromCustom || !matched){
    customBgBtn.style.setProperty('--custom-color', hex);
    customBgBtn.classList.add('has-color');
  }
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
    syncShapeKnobs();
    /* CLOSE ON A PICK ONLY WHEN THE PICK LEFT NOTHING TO SET.
       The old rule closed the popover on every pick, so choosing Poly revealed
       Sides and Corners and hid them again in the same click, and the only way
       to reach them was to open the picker a SECOND time. Reported from the
       live demo: "when you push poly it chooses it, but you have to choose it
       again to get the menu". Line and Oval still close, because nothing was
       revealed to stay open for. */
    const pop = document.getElementById('shapePop');
    if(pop && !SkriblShapes.knobs(k).length) pop.hidden = true;
  });
}

/* WHICH KNOBS APPLY TO WHICH KIND — asked of lib/shapes.js, which holds the
   only copy of that rule. Each row hides rather than greying out: a disabled
   control is still something the eye has to read and dismiss, and this popover
   is small on a phone. */
function syncShapeKnobs(){
  const sidesRow = document.getElementById('shapeSidesRow');
  const radiusRow = document.getElementById('shapeRadiusRow');
  if(sidesRow) sidesRow.hidden = !SkriblShapes.hasKnob(shapeKind, 'sides');
  if(radiusRow) radiusRow.hidden = !SkriblShapes.hasKnob(shapeKind, 'radius');
}

(function shapeKnobs(){
  const sides = document.getElementById('shapeSides');
  const sidesOut = document.getElementById('shapeSidesOut');
  const radius = document.getElementById('shapeRadius');
  const radiusOut = document.getElementById('shapeRadiusOut');
  if(sides){
    sides.value = String(shapeSides);
    if(sidesOut) sidesOut.textContent = String(shapeSides);
    sides.addEventListener('input', () => {
      shapeSides = Math.max(3, Math.min(12, parseInt(sides.value, 10) || 3));
      if(sidesOut) sidesOut.textContent = String(shapeSides);
      // A live preview is mid-drag geometry, so redraw it: changing a knob
      // while the rubber band is up should show the new shape, not the old one.
      render();
    });
  }
  if(radius){
    radius.value = String(shapeRadius);
    if(radiusOut) radiusOut.textContent = String(shapeRadius);
    radius.addEventListener('input', () => {
      shapeRadius = Math.max(0, parseInt(radius.value, 10) || 0);
      if(radiusOut) radiusOut.textContent = String(shapeRadius);
      render();
    });
  }
  syncShapeKnobs();
})();
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
  zoomMag=1; zoomFocus='loop'; zoomCenter=null; if(typeof syncZoomMagStep==='function') syncZoomMagStep();
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
  a.download=(window.SkriblName ? window.SkriblName.filename(data.title)
    : 'skribl-flip-'+new Date().toISOString().slice(0,10)+'.skribl');
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
      const cropped = window.SkriblPostedAudio.buildPostedLoopWav({ currentAudioBuffer: currentAudioBuffer, trimStart: trimStart, trimEnd: trimEnd, loopCrossfadeMs: loopCrossfadeMs });
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
  // NOT 'Background image' as the fallback: the panel already carries that
  // as its section heading, so an image with no stored name printed it twice
  // in a row. Normally this shows the file name and there is no repetition;
  // the fallback is for a restored draft that never saved one.
  photoBtnLabel.textContent = hasImg ? (imageName || 'Image added') : 'Add an image';
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
/* THE MAGNIFICATION IS A STEPPER, not a row of levels, and it climbs to 32x.
 *
 * TWO REASONS, and the second is the one that matters.
 *
 * SPACE: four cells cost 179px and forced the focus row and the zoom row onto
 * separate lines (74px of bar). A stepper is 94px and both fit on one line at
 * 390 and up -- 36px of bar. At 320 it still wraps, because Loop/Start/End is
 * 172px of the 220 available and nothing useful fits beside it; it wrapped
 * there before too.
 *
 * REACH: the finest nudge step is 0.01s, and the OLD CEILING COULD NOT RESOLVE
 * IT. On a 330px waveform at 8x, one step is 0.94px for a 20s loop and 0.39px
 * for a 60s one -- you were nudging by an amount you could not see. 32x puts a
 * step at 3.8px and 1.6px respectively. A four-cell segmented control could not
 * afford two more levels; a stepper costs nothing to extend, which is the real
 * argument for it.
 *
 * The buttons carry magnifier glyphs rather than plain minus and plus. A
 * leading magnifier next to plain signs was tried and measured 118px, which
 * puts the bar back onto two lines at 390 -- identifying the control would have
 * cost exactly the space the change was made to save.
 */
/* The ladder, the chrome and the step rule live in lib/zoomstep.js so Pad and
 * Flip cannot offer different zoom levels. Only the wiring is local. */
function syncZoomMagStep(){ window.SkriblZoomStep.sync(zoomMag); }
function stepZoomMag(dir){
  const m = window.SkriblZoomStep.next(zoomMag, dir);
  if(m === zoomMag) return;
  zoomMag = m;
  syncZoomMagStep();
  updateTrimUI();
}
(function initZoomMagControl(){ if(!zoomTrackWrap||!zoomTrackWrap.parentNode) return;
  const bar=document.createElement('div'); bar.className='zoom-mag-bar';
  bar.innerHTML='<span class="seg zoom-seg" data-role="focus" title="What the loop view centres on">'
    + '<button type="button" class="zoom-mag-btn on" data-focus="loop">Loop</button>'
    + '<button type="button" class="zoom-mag-btn" data-focus="start">Start</button>'
    + '<button type="button" class="zoom-mag-btn" data-focus="end">End</button></span>'
    + window.SkriblZoomStep.markup();
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-seg[data-role="focus"]'));
  // .on not .active: real .seg cells now; the shared slider reads .on.
  bar.addEventListener('click',(e)=>{
    const b=e.target.closest('.zoom-mag-btn');
    if(b){
      b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      if(b.dataset.focus){ zoomFocus=b.dataset.focus; zoomCenter=null; }
      updateTrimUI();
      return;
    }
    const step=e.target.closest('.mag-step-btn');
    if(step && !step.disabled) stepZoomMag(step.id === 'zoomMagIn' ? 1 : -1);
  });
  syncZoomMagStep();
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
  // The stylesheet built here at runtime moved to styles.css: it was the same
  // string in editor_photo.js, and a JS string is invisible to every colour
  // ratchet — which is why these buttons stayed dark in light mode.
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
  if(window._skriblSyncThemeToggle) window._skriblSyncThemeToggle();
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
// The sheet grabber closes the menu on tap, same as Pad's handles do.
{ const _h = moreMenu.querySelector('.menu-handle'); if (_h) _h.addEventListener('click', () => closeMenu()); }
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

// Theme switch — the SAME stored setting as Pad's. lib/theme.js owns the key
// and the <html> attribute; this is only the control that drives it.
(function(){
  const seg=document.getElementById('themeSeg');
  if(!seg || !window.SkriblTheme) return;
  function sync(){
    const mode=window.SkriblTheme.get();
    seg.querySelectorAll('button').forEach(b=>b.classList.toggle('on', b.dataset.theme===mode));
    if(window.SkriblSegSlider) window.SkriblSegSlider.place(seg);
  }
  seg.addEventListener('click',e=>{
    const b=e.target.closest('button'); if(!b || !b.dataset.theme) return;
    window.SkriblTheme.set(b.dataset.theme);
  });
  // Driven by the lib, not by the click, so a change made in another tab moves
  // this switch too — the setting is per browser, not per page.
  window.SkriblTheme.onChange(sync);
  if(window.SkriblSegSlider) window.SkriblSegSlider.track(seg);
  window._skriblSyncThemeToggle = sync;
  sync();
})();

bindEl('postBtn', 'click', openShareCompose);
bindEl('miSave', 'click',()=>{ closeMenu();
  // Name it as part of saving — the drawer's button reads "Save draft".
  if(window.SkriblName && window.SkriblName.open){ window.SkriblName.open({label:'Save draft', onConfirm:saveDraft}); }
  else { saveDraft(); } });
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
        // Container in the TITLE only; the description keeps the tradeoff.
        vTitle.textContent='Video ('+fmt+')';
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
    else { gifBtn.disabled=false; if(gifDesc) gifDesc.textContent='Your animation — loops, no sound'; if(gifToggle) gifToggle.hidden=false; }
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

/* ---------- v237: the in-between -------------------------------------------
   A GENERATED PAGE THAT LOOKS LIKE A LONG EXPOSURE.

   The reference is stop-motion: a puppet photographed while it MOVED, so one
   frame integrates the whole path between two poses. What sells it is not the
   blur -- it is that the blur is UNEVEN. The feet, which barely travelled, come
   out nearly sharp; the arms, which swung furthest, smear away to nothing.

   That gradient is the reason this can be done honestly here. Sample the motion
   between two pages at N steps and draw every step faintly: a point that hardly
   moves lays all N of its copies on top of each other and stays crisp, and a
   point that travels far spreads them along its path and goes soft. Nobody has
   to author the falloff. It is what integrating a motion MEANS, and it falls
   out of the arithmetic.

   IT IS ORDINARY STROKE DATA. No new field, no raster layer, no change the
   player has to learn -- opacity already rides inside each point's rgba() and
   the player already honours it. The generated page is a page like any other:
   editable, erasable, exportable, postable, and drawn by the replay in order.

   WHAT IT NEEDS FROM YOU is two pages whose strokes CORRESPOND -- the same
   strokes, moved. That is exactly what Duplicate then drag produces, which is
   already the way the app is used. Two freehand redraws have no correspondence
   to interpolate, and rather than guess at a pairing and produce a mess, this
   refuses and says why.

   BLURRED as of v237, and NOT via ctx.filter. The note that stood here said a
   real gaussian was one render attribute away and that the attribute was a
   contract the PLAYER would have to honour -- true, and the reason it waited.
   It turned out not to be the only way.

   The thing worth seeing is WHAT was missing. The sample sequence is already a
   smear ALONG the motion; that is what a long exposure is, and it was never the
   defect. What made it read as a stack of copies rather than something moving
   is that every ghost still ended in the crisp round cap of the brush that drew
   it: there was no softness ACROSS the motion. A blur is a radial falloff, and
   a radial falloff can be DRAWN -- each sample is emitted as a few concentric
   passes, widest and faintest first so the crisp core lands on top of its own
   halo. It costs points instead of a format contract, and every pass is an
   ordinary stroke, so a Skribl made this way opens in a player that predates
   the feature. That is the whole reason to prefer it: a format change is the
   last resort, not the first design. */

/* The point budget again, and for the same reason as liquify's: the server
   refuses a frame over MAX_POINTS_PER_FRAME (20,000), so a feature that
   MULTIPLIES a page by N can make a drawing unpostable at the moment somebody
   tries to share it. N adapts to the page instead of being a constant: a light
   page gets the full 26 samples, a heavy one gets fewer and a coarser exposure,
   and a page too heavy for even a handful says so rather than producing a
   frame the server will reject. */
const TWEEN_SAMPLES = 26;
const TWEEN_MIN_SAMPLES = 6;
const TWEEN_POINT_CAP = 14000;
/* The server also refuses a frame over MAX_GROUPS_PER_FRAME (5,000) and every
   pass of every sample is its own group, so the group count has to be budgeted
   as carefully as the point count. It was not before: a page with many short
   strokes could pass the point cap and still be unpostable. */
const TWEEN_GROUP_CAP = 4500;

/* The blur, widest and faintest FIRST -- strokes render in array order, so this
   puts the crisp core on top of its own halo. `a` scales the exposure alpha and
   `d` is a FRACTION OF THE SOFT EDGE, which is added to the brush rather than
   multiplying it.

   That distinction is the whole of v238. The first version multiplied: the
   widest pass was 3.4x the brush. On a 6px test stroke that is a 7px soft edge
   and it looked right, which is the only size it was checked at. On a 60px ball
   it is a 200px cloud -- the ball INFLATES instead of smearing, and reads as a
   lumpy blob rather than something moving fast. Motion blur does not fatten an
   object. It smears it ALONG its travel, which the sample sequence already
   does, and leaves the edge ACROSS the travel nearly sharp. So the halo has to
   be a small, near-fixed softness, and the smoothness along the path comes from
   sample COUNT, not from halo width.

   Three passes is the full falloff; a heavy page degrades to the last two, then
   to the core alone, which is exactly the unblurred exposure this feature
   started as. Degrading beats refusing. */
const TWEEN_BLUR = [ { d: 1.00, a: 0.10 }, { d: 0.66, a: 0.18 }, { d: 0.38, a: 0.32 },
                     { d: 0.17, a: 0.55 }, { d: 0.00, a: 1.00 } ];
/* How wide the soft edge is, in canvas pixels, for a given brush. Scales gently
   with the brush so a hairline does not get a disproportionate halo, and is
   bounded at both ends so a big ball gets a soft EDGE rather than a cloud. */
function tweenSoftEdge(size){ return Math.max(4, Math.min(14, size * 0.5)); }
/* Concentric passes lay more ink down than a single one, so the core is pulled
   back to keep an in-between the same weight it was before it was blurred.
   Derived by MEASURING mean ink over the lit area at two pass counts and
   solving for the denominator, not by arithmetic on the alphas: the halo
   covers more ground than the core, so the sum of the weights is not what the
   eye ends up reading. A single pass is the unblurred exposure and is left
   exactly as it was. */
/* THE HALO CANNOT CARRY A COLOUR IT HAS NO BITS FOR.

   Canvas composites through PREMULTIPLIED 8-bit alpha: a channel is stored as
   round(channel * alpha), so a blur pass at alpha 2/255 turns #ffb020's blue
   (32) into round(0.25) = 0 before any compositing happens. The blue is gone,
   and the halo around an orange ball renders RED. Measured on the canvas, not
   inferred: a plain ball reads (255,176,32) and the same ball blurred peaked at
   (240,134,2).

   Which pass survives depends on the ink, so the test has to be per-drawing:
   `channel * alpha` for the darkest channel the ink actually carries. Measured
   across three inks at nine alphas, hue holds from about 1.2 upward and is
   visibly wrong below it — and at alpha 1/255 it is wrong for EVERY ink,
   including near-white, which is worth knowing on its own.

   A zero channel is exempt: pure red has no blue to lose. */
const TWEEN_HUE_MIN = 1.2;
function darkestChannel(col){
  const m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i.exec(String(col));
  let ch;
  if(m) ch = [+m[1], +m[2], +m[3]];
  else {
    const h = /^#([0-9a-f]{6})/i.exec(String(col).trim());
    if(!h) return 255;
    ch = [parseInt(h[1].slice(0,2),16), parseInt(h[1].slice(2,4),16), parseInt(h[1].slice(4,6),16)];
  }
  const lit = ch.filter(v => v > 0);
  return lit.length ? Math.min.apply(null, lit) : 255;
}
/* The darkest channel anywhere on the page, so one saturated stroke does not
   get a broken halo just because the rest of the drawing is pale. */
function frameDarkest(f){
  let d = 255;
  for(const p of f.strokes){ const v = darkestChannel(solidOf(p.color)); if(v < d) d = v; }
  return d;
}

function tweenTrim(blur){
  if(blur.length < 2) return 1;
  let weight = 0;
  for(const b of blur) weight += b.a;
  // The "+ 0.4" that used to be here was fitted when the halo was a MULTIPLE of
  // the brush and so covered far more ground than the core. With a soft edge of
  // a few pixels the halo barely spreads, and that term made the exposure come
  // out at 0.85x the weight of an unblurred one -- visibly washed out. Measured
  // again at brush 8, 30 and 60: the plain reciprocal lands within 1%.
  return 1 / weight;
}

/* Picks the sample count first and the blur second.

   That order is the whole point. The blur's real job is filling the gaps
   BETWEEN samples -- unblurred, the exposure reads as a stack of separate
   copies, and what the halo does is close the ribbing between them. So paying
   for a richer falloff with a coarser exposure is a bad trade at any budget:
   it would leave WIDER gaps for a slightly softer halo to cover. Blur is only
   allowed to spend budget the exposure itself does not need.

   Returns null when even a bare, unblurred exposure will not fit. */
const TWEEN_GOOD_SAMPLES = 16;
/* THE SECOND CEILING: an exposure has to be PAINTED, not just posted.

   TWEEN_POINT_CAP is the server's limit -- what a frame may contain. It says
   nothing about how long that frame takes to draw, and the drawing happens once
   per appearance, inside whatever slot the document's own frame rate leaves.

   Reported from a real 46-page flip at fps 24, where 22 of the pages were
   in-betweens: each was 11,826 points (27 samples of a 438-point drawing, which
   is what the server cap allows) and measured 50ms against a 41.7ms budget.
   Every other page overran and the flip dragged. The same document at 12fps
   would have been comfortable -- 83ms is plenty for 50 -- so this was never a
   property of the in-between alone, but of the in-between AND the rate it was
   asked to play at.

   Measured on those frames, by sample count:

       27 -> 50.0ms      18 -> 30.0ms
       14 -> 23.1ms       9 -> 14.8ms

   So the budget scales with the slot: at 12fps and below the server cap binds
   and nothing changes, and above it the allowance falls in proportion. 24fps
   gets half, which put that page at 16 samples and about 26ms.

   IT NEVER CAUSES A REFUSAL. A render heuristic that turned "here is a coarser
   exposure" into "this page is too heavy for an in-between" would be trading a
   feature for a frame rate. Below TWEEN_MIN_SAMPLES the render ceiling simply
   stops applying and the page is drawn at the floor. */
function tweenRenderCap(atFps){
  const f = (typeof atFps === 'number' && atFps > 0) ? atFps : 12;
  if(f <= 12) return TWEEN_POINT_CAP;
  return Math.max(1, Math.round(TWEEN_POINT_CAP * 12 / f));
}
function tweenPlan(per, groupsPer, atFps){
  const renderCap = tweenRenderCap(typeof atFps === 'number' ? atFps : fps);
  // The most samples that fit BOTH caps at a given pass count. Groups are
  // capped separately because every pass of every sample is its own group:
  // a page of many short strokes can clear the point cap and still be
  // unpostable, which nothing checked before.
  const fit = (passes, cap) => {
    // Both are "-1" because the sample loop runs s = 0..n inclusive and so
    // emits n+1 samples. Without it the plan overshot its own budget: a
    // 150-point page planned 14,250 points against a cap of 14,000.
    const byPoints = Math.floor(cap / Math.max(1, per * passes)) - 1;
    const byGroups = Math.floor(TWEEN_GROUP_CAP / Math.max(1, groupsPer * passes)) - 1;
    return Math.min(TWEEN_SAMPLES, byPoints, byGroups);
  };
  // The SERVER cap decides whether an exposure is possible at all; the render
  // cap only decides how fine it is.
  const postable = fit(1, TWEEN_POINT_CAP);
  if(postable < TWEEN_MIN_SAMPLES) return null;
  const bare = Math.max(TWEEN_MIN_SAMPLES, Math.min(postable, fit(1, renderCap)));
  const keep = Math.min(bare, TWEEN_GOOD_SAMPLES);
  for(let passes = TWEEN_BLUR.length; passes >= 2; passes--)
    if(fit(passes, renderCap) >= keep) return { passes: passes, n: fit(passes, renderCap) };
  return { passes: 1, n: bare };
}

/* Two pages can be interpolated only if their strokes line up: same number of
   groups, same number of points in each. Returns null when they do not, and the
   caller turns that into a sentence rather than a shrug. */
/* ---------- v255: making the in-between accept HAND-DRAWN poses -------------

   WHAT REFUSED, AND WHY IT WAS TOO STRICT. tweenMismatch demanded that the two
   pages be structurally identical -- the same number of strokes AND the same
   number of points in each. That is what Duplicate-then-drag produces, and for
   that workflow it is exactly right. But drawing the next pose by hand is what
   frame-by-frame animation IS, and a redraw of the same shape lands a different
   number of points every time: a ball drawn twice came out 38 and 32, so the
   feature refused the case it is most wanted for.

   A STROKE IS A PATH, NOT A LIST OF VERTICES. Walking it at even spacing along
   its own arc length and re-emitting it gives the same shape with whatever
   vertex count you ask for. Resample both poses to a common count and they
   correspond point-for-point; the exposure arithmetic below then runs
   completely unchanged. It is not a guess at a pairing -- stroke s still pairs
   with stroke s, exactly as before -- it only stops the VERTEX counts from
   being the thing that decides.

   NO FORMAT CHANGE, and that is the point. Rasterising would have bought a real
   correspondence and cost exact scaling, which is the property this app is for.
   Interpolating polylines keeps it: an in-between made this way is ordinary
   stroke data at any zoom.

   WHAT STILL REFUSES: two pages with a DIFFERENT NUMBER OF STROKES. Pairing
   three strokes against four means deciding which one has no partner, and that
   is the guess the v237 note declined to make. It is still declined here, and
   now it is the only thing that refuses rather than one of two. */

/* One run, resampled to exactly n points by arc length. */
function tweenResample(pts, n){
  if(n < 1) return [];
  // A dot, or a run that never moved: n copies of the one point. Returning the
  // run unchanged here would leave the two pages mismatched again, which is the
  // whole bug -- and a dot is a perfectly ordinary thing to have on a page.
  if(pts.length < 2) return Array.from({ length: n }, () => Object.assign({}, pts[0]));
  const d = [0];
  let total = 0;
  for(let i = 1; i < pts.length; i++){
    total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    d.push(total);
  }
  if(!(total > 0)) return Array.from({ length: n }, () => Object.assign({}, pts[0]));
  const out = [];
  let j = 1;
  for(let k = 0; k < n; k++){
    const target = total * (n === 1 ? 0 : k / (n - 1));
    while(j < d.length - 1 && d[j] < target) j++;
    const span = d[j] - d[j - 1];
    const t = span > 0 ? (target - d[j - 1]) / span : 0;
    const pa = pts[j - 1], pb = pts[j];
    // Object.assign from the NEARER point carries colour, erase and t; only the
    // geometry is interpolated. Blending colour along a run would invent shades
    // the drawing never had.
    const q = Object.assign({}, t < 0.5 ? pa : pb);
    q.x = pa.x + (pb.x - pa.x) * t;
    q.y = pa.y + (pb.y - pa.y) * t;
    if(typeof pa.size === 'number' && typeof pb.size === 'number')
      q.size = pa.size + (pb.size - pa.size) * t;
    if(k === 0) q.start = true; else delete q.start;
    out.push(q);
  }
  return out;
}

/* Splits a frame into its runs. */
function tweenRuns(f){
  const out = [];
  let i = 0;
  for(const n of f.strokeGroups){ out.push(f.strokes.slice(i, i + n)); i += n; }
  return out;
}

/* Both pages resampled onto a shared structure. Returns {a, b} frame-shaped
   COPIES -- the user's pages are never touched, so an in-between they undo
   leaves the poses exactly as they drew them. Null when the stroke counts
   differ, which is the one case still declined. */
function tweenAlign(a, b){
  const ra = tweenRuns(a), rb = tweenRuns(b);
  if(ra.length !== rb.length) return null;
  const A = { strokes: [], strokeGroups: [] };
  const B = { strokes: [], strokeGroups: [] };
  for(let s = 0; s < ra.length; s++){
    // The denser of the two, so the pose that was drawn more carefully is the
    // one that keeps its detail.
    const n = Math.max(ra[s].length, rb[s].length);
    const pa = tweenResample(ra[s], n), pb = tweenResample(rb[s], n);
    A.strokes.push(...pa); A.strokeGroups.push(pa.length);
    B.strokes.push(...pb); B.strokeGroups.push(pb.length);
  }
  return { a: A, b: B };
}

function tweenMismatch(a, b){
  if(!a || !b) return 'two pages';
  if(!a.strokes.length || !b.strokes.length) return 'two pages with drawing on them';
  /* v255: the POINT counts are no longer part of this. They used to be, and
     that made a hand-redrawn pose refuse -- see the tweenAlign note above.
     The stroke COUNT still is: pairing three strokes against four means
     choosing which one has no partner, and that guess is still declined. */
  if(a.strokeGroups.length !== b.strokeGroups.length)
    return 'the same NUMBER of strokes on both pages — this one has '
         + a.strokeGroups.length + ', the next has ' + b.strokeGroups.length;
  return null;
}

/* Opacity rides INSIDE the colour, and the FORM it is written in is the whole
   difference between an exposure that plays and one that stalls.

   THE BUG THIS FIXES, reported from a phone: "it takes 2 seconds to play 3
   frames". paintStatic gives every translucent stroke its own offscreen layer
   -- clear a full canvas, redraw, composite it back -- to stop a see-through
   stroke beading at its own overlaps. That is right for a stroke somebody drew.
   An exposure is 27 samples of every limb, so a six-limb figure is 162
   translucent strokes and ~486 full-canvas operations PER FRAME. Measured: 221
   ms to render one in-between against a 12 fps budget of 83 ms, and worse on a
   denser drawing. The render blocks the timer, so the previous frame sits on
   screen while it works -- which is exactly what the pauses were.

   AND THE LAYERING IS WRONG FOR THIS CONTENT ANYWAY. It exists to stop a stroke
   compounding at its own overlaps; an exposure IS compounding overlaps. The
   density where samples pile up is the effect.

   So the fade is written as an 8-digit hex (#rrggbbaa) rather than rgba(). Both
   renderers decide whether to layer by matching the rgba() FUNCTION form --
   alphaOf here, parseStrokeAlpha in app.js, which is also the player's renderer
   -- and neither matches a hex. Canvas honours the alpha either way and
   accumulates it (verified: two passes of #ffffff21 over black give 33 then
   61). Result: 221 ms -> 5.6 ms, the same picture, and NOTHING else changes --
   no new field, no renderer edit, no contract for the player to learn.

   IT IS A DELIBERATE USE OF THE FORM, not an accident of one. Teaching alphaOf
   to understand hex would make exposures slow again -- not broken, just slow --
   so verify_tween pins the render cost, which is the assertion that would catch
   it. Anything a user draws still arrives as rgba() and still gets its layer. */
function tweenFade(col, mul){
  const solid = solidOf(col);
  // strokeAlphaOf, not alphaOf: an 8-digit hex is what an in-between writes, so
  // this is the path taken when someone makes an in-between OF an in-between.
  // Reading its alpha as 1 left those samples at their existing alpha, unfaded.
  const a = Math.max(0, Math.min(1, strokeAlphaOf(col) * mul));
  const hx = n => ('0' + Math.round(n).toString(16)).slice(-2);
  const m = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i.exec(solid);
  if(m) return '#' + hx(+m[1]) + hx(+m[2]) + hx(+m[3]) + hx(a * 255);
  const h = /^#([0-9a-f]{6})(?:[0-9a-f]{2})?$/i.exec(String(col).trim());
  if(h) return '#' + h[1].toLowerCase() + hx(a * 255);
  return col;
}

/* Builds the exposure between pages A and B. Returns a frame, or null with the
   reason already chipped. */
function buildTween(a, b){
  const why = tweenMismatch(a, b);
  if(why){ chip('An in-between needs ' + why); return null; }
  /* Everything below reads a.strokes / a.strokeGroups / b.strokes and pairs
     them index for index, so aligning HERE leaves all of it unchanged. The
     budget is computed on the aligned count, not the original: resampling
     takes the denser of the two runs, so the exposure can be built from more
     points than either page holds and budgeting on the source would let it
     past the server's cap. */
  const aligned = tweenAlign(a, b);
  if(!aligned){ chip('An in-between needs the same number of strokes on both pages'); return null; }
  a = aligned.a; b = aligned.b;
  const per = a.strokes.length;
  const plan = tweenPlan(per, a.strokeGroups.length);
  if(!plan){
    chip('This page is too heavy for an in-between');
    return null;
  }
  const n = plan.n;
  // The blur passes actually used: the LAST `passes` of the table, so dropping
  // one drops the widest, faintest halo and keeps the core.
  let blur = TWEEN_BLUR.slice(TWEEN_BLUR.length - plan.passes);
  // Enough per sample that the exposure sums to a readable figure, capped so a
  // short sample count does not come out as a stack of hard copies. Trimmed
  // when there is a halo carrying part of the weight.
  let fade = Math.min(0.30, Math.max(0.06, 2.6 / n)) * tweenTrim(blur);
  // Shed any pass too faint to carry this drawing's colour — see
  // TWEEN_HUE_MIN. The core is always kept: it is the drawing, not the halo.
  // Coarsening the exposure instead would trade smoothness for colour on every
  // page; this costs the halo only, and only on the pages that cannot hold one.
  const dark = frameDarkest(a);
  const keep = blur.filter((p, i) => i === blur.length - 1
                                  || fade * p.a * dark >= TWEEN_HUE_MIN);
  if(keep.length !== blur.length){
    blur = keep;
    // Fewer passes lay down less ink, so the core is re-trimmed for the set
    // that actually survived.
    fade = Math.min(0.30, Math.max(0.06, 2.6 / n)) * tweenTrim(blur);
  }
  const out = { strokes: [], strokeGroups: [], hold: 1 };
  for(let s = 0; s <= n; s++){
    const t = s / n;
    for(let p = 0; p < blur.length; p++){
      const pass = blur[p];
      let at = 0;
      for(let g = 0; g < a.strokeGroups.length; g++){
        const count = a.strokeGroups[g];
        for(let k = 0; k < count; k++){
          const pa = a.strokes[at + k], pb = b.strokes[at + k];
          const q = Object.assign({}, pa);
          q.x = pa.x + (pb.x - pa.x) * t;
          q.y = pa.y + (pb.y - pa.y) * t;
            if(typeof pa.size === 'number'){
            const base = (typeof pb.size === 'number')
              ? pa.size + (pb.size - pa.size) * t : pa.size;
            q.size = base + tweenSoftEdge(base) * pass.d;
          }
          q.color = tweenFade(pa.color, fade * pass.a);
          // Every sample is its own stroke, so `start` belongs on its first point
          // and nowhere else -- copying pa.start wholesale would mint a start
          // partway through a run, which is the shape the server rejects.
          if(k === 0) q.start = true; else delete q.start;
          // Timestamps march across the exposure so REPLAY draws it as a sweep
          // rather than flashing the whole thing into existence at once. All
          // passes of one sample share a timestamp: the halo and the core are
          // one ghost, and staggering them would replay as a pulsing edge.
          if(typeof pa.t === 'number') q.t = pa.t + (s * 8);
          out.strokes.push(q);
        }
        out.strokeGroups.push(count);
        at += count;
      }
    }
  }
  return out;
}

/* ---------- v261: rebuilding the in-betweens already on the page -----------

   v260 made the exposure's sample count depend on the document's frame rate,
   and that only reaches pages made AFTER it. The reported file had 22
   in-betweens already baked at 27 samples, which is the reason it dragged;
   deleting and re-adding each of them by hand is the fix nobody should have to
   perform 22 times.

   NOTHING MARKS A PAGE AS GENERATED, so this has to recognise one, and being
   wrong means overwriting a drawing. Three things have to agree before a page
   is touched, and a hand-drawn page fails all three:

     * every point's colour is an 8-digit hex. tweenFade is what writes those,
       and the pen never does -- it writes '#rrggbb' or an rgba().
     * the neighbours either side can actually be interpolated, which is what
       generated the page in the first place.
     * the run count is an exact MULTIPLE of the previous page's, because an
       exposure emits the whole run list once per sample per pass. A drawing
       landing on an exact multiple of its neighbour's run count AND being
       entirely 8-digit hex is not a coincidence worth worrying about.

   A page already at the right sample count is left alone, so running this twice
   costs nothing and reports honestly that there was nothing to do. */
function tweenLooksGenerated(i){
  const f = frames[i], a = frames[i - 1], b = frames[i + 1];
  if(!f || !a || !b || !f.strokes.length || !a.strokeGroups.length) return false;
  if(tweenMismatch(a, b)) return false;
  const copies = f.strokeGroups.length / a.strokeGroups.length;
  if(!Number.isInteger(copies) || copies < TWEEN_MIN_SAMPLES) return false;
  for(let k = 0; k < f.strokes.length; k++)
    if(!/^#[0-9a-f]{8}$/i.test(String(f.strokes[k].color))) return false;
  return true;
}
/* How many run-copies the CURRENT plan would emit for this page, so an
   in-between that is already right is skipped rather than rebuilt identically. */
function tweenPlannedCopies(i){
  const a = frames[i - 1];
  const plan = tweenPlan(a.strokes.length, a.strokeGroups.length, fps);
  return plan ? (plan.n + 1) * plan.passes : null;
}
function rebuildTweens(){
  if(playing) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; }
  const found = [];
  for(let i = 1; i < frames.length - 1; i++) if(tweenLooksGenerated(i)) found.push(i);
  if(!found.length){ chip('No in-betweens to rebuild'); return; }
  const stale = found.filter(i => {
    const want = tweenPlannedCopies(i);
    return want != null
        && frames[i].strokeGroups.length / frames[i - 1].strokeGroups.length !== want;
  });
  if(!stale.length){
    chip(found.length + ' in-between' + (found.length === 1 ? ' is' : 's are')
         + ' already right for ' + fps + ' fps');
    return;
  }
  invalidateClearUndo(); redoStack.length = 0;
  let done = 0, before = 0, after = 0;
  for(const i of stale){
    const t = buildTween(frames[i - 1], frames[i + 1]);
    if(!t) continue;                      // buildTween has already said why
    before += frames[i].strokes.length;
    after += t.strokes.length;
    // The page keeps its own hold EXACTLY: how long it is shown is the author's,
    // not something a rebuild gets to reset -- and a page that carried no hold
    // at all must not come back carrying one. buildTween always returns hold 1,
    // which is the same as absent to frameHold() but not the same in the file.
    if(frames[i].hold != null) t.hold = frames[i].hold; else delete t.hold;
    frames[i] = t;
    done++;
  }
  buildStrip(); render(); scheduleSave();
  if(!done){ chip('Could not rebuild those in-betweens'); return; }
  const pct = before ? Math.round((1 - after / before) * 100) : 0;
  chip('Rebuilt ' + done + ' in-between' + (done === 1 ? '' : 's')
       + (pct > 0 ? ' — ' + pct + '% lighter' : ''));
}

/* Inserts the exposure between this page and the next. */
function addTween(){
  if(playing) return;
  if(moveMode){ chip('Finish or cancel the move first'); return; }
  const a = frames[idx], b = frames[idx + 1];
  if(!b){ chip('An in-between goes BETWEEN two pages — add the next pose first'); return; }
  const t = buildTween(a, b);
  if(!t) return;
  invalidateClearUndo(); redoStack.length = 0;
  frames.splice(idx + 1, 0, t); idx++;
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true);
  chip('In-between added');
}

/* ---------- v236: liquify ----------------------------------------------------
   IT IS CALLED LIQUIFY BECAUSE IT IS NOT A SMUDGE, and the name was the second
   thing to get right. Built as "Smudge" first, which is what was asked for and
   what the mental slot is called — then renamed, because the word promises
   something this cannot do and no amount of good behaviour makes up for a
   control that lies about itself.

   The family this actually belongs to is Photoshop's Liquify > Forward Warp,
   Procreate's Liquify > Push, and Inkscape's Tweak tool in "push parts of
   paths" mode, which displaces path nodes by a distance-weighted delta exactly
   as this does. A real smudge — Photoshop's, Procreate's, Krita's Color Smudge
   engine — is COLOUR TRANSPORT: sample under the brush, carry it along the
   drag, blend it down. Blending two colours and softening a hard edge are what
   people reach for smudge to do, and this cannot do either. Not a weaker
   version: a different operation.

   AND COLOUR TRANSPORT IS NOT AVAILABLE HERE, which is the other half of the
   reason. Skribl has no bitmap to sample. A page is a list of points --
   {x, y, color, size, t, erase} -- rendered to a canvas that is thrown away and
   redrawn every frame, and that same list is what the player replays, what
   export walks and what the draft stores. Rasterising a page to blend it would
   invent a second kind of content that undo, export, the draft schema and the
   player would all have to learn, and it would kill replay outright: a
   flattened image has no stroke order left to animate.

   So this moves the GEOMETRY. Points inside the brush are dragged along with
   the pointer, weighted by how close to the centre they are, and the strokes
   bend. For a line document that is the better instrument anyway -- it moves
   the ink you drew rather than averaging it into mud, and it is lossless where
   a raster smudge is not.

   What it costs, stated plainly: no colour bleed. Two crossing strokes stay two
   crossing strokes; they bend towards each other but they do not mix. Nothing
   in this format can make them mix.

   WHAT IT KEEPS, which is the whole argument: replay (points keep their order
   and their `t`, so the animation still draws in sequence, just along a bent
   path), export, the player, the draft, and an undo that is exact. */

/* Reach, in canvas units. Tied to the brush slider so liquify needs no control
   of its own -- the row is already full, and "the size you draw with is the
   size you push with" is one less thing to explain. The multiplier makes the
   brush reach wider than it paints, because a warp that only caught the line
   directly under the cursor would feel like nothing at all. */
const LIQUIFY_REACH = 6;
function liquifyRadius(){ return Math.max(8, size * LIQUIFY_REACH); }

/* THE INK HAS TO SLIP, and this is the number that makes it.

   At full strength a point in the centre of the brush moves the entire delta —
   which lands it back in the centre for the next move event, at weight 1
   again. It rides the cursor forever, and every line the brush crosses gets
   dragged to the same single point: a hard spike, not a smear. Measured on
   three parallel lines, all three converged to one vertex.

   Below 1 the centre point moves only part of the delta, so it falls behind
   the brush; being behind, it sits further from the centre; being further, its
   weight drops; and it sheds off the back on its own. The spike becomes a
   taper. That is what dragging a finger through wet ink actually does — the
   ink lags, slides to the rim of the contact patch, and lets go. */
const LIQUIFY_STRENGTH = 0.5;

/* Firm in the middle, nothing at the rim. Linear falloff was tried first and
   reads as a SHOVE -- the whole disc lurches and the edge of the brush leaves a
   visible crease across the stroke. Squaring the parabola pulls the centre
   along and lets the rim off almost untouched, which is what dragging something
   viscous actually looks like. */
function liquifyWeight(d2, r2){
  if(d2 >= r2) return 0;
  const t = 1 - d2 / r2;
  return t * t;
}

/* One gesture's worth of originals, keyed by point index so a point caught on
   several successive moves is recorded ONCE -- at the position it had before
   the gesture started, which is the only position undo cares about. Recording
   per move would snapshot a half-dragged point and undo would land there. */
function liquifyBegin(pt){
  liquifyLast = { x: pt.x, y: pt.y };
  liquifyTouched = false;
  // A liquify stroke belongs to the page it STARTED on, and is pinned here for
  // the same reason `strokeFrame` exists: the page can change mid-gesture -- a
  // thumbnail tap, the page bar, a held arrow riffling -- and everything after
  // this point works on ONE strokes array. Re-reading frame() per move would
  // apply the back half of the drag to a different page.
  liquifyIdx = idx;
  const f = frames[liquifyIdx];
  liquifyBefore = f ? { strokes: f.strokes.map(q => Object.assign({}, q)),
                        groups: f.strokeGroups.slice() } : null;
}

function liquifyFrame(){ return frames[liquifyIdx]; }

/* ---- resolution ----------------------------------------------------------
   THE DEFECT THIS FIXES, in one sentence: this tool moves VERTICES, so a
   stroke with only two vertices inside the brush can only bend into a corner.

   Measured side by side: the same pull across a line sampled at 101 points
   gives a smooth dip, and across the same line sampled at 7 points gives a
   hard angular V. Seven points is not a pathological case -- it is what
   drawing FAST produces, and drawing fast is normal drawing. So the tool was
   quietly good on careful strokes and bad on quick ones, which is exactly
   backwards from what a expressive tool should be.

   The fix is to add resolution where the brush is about to bend something:
   split any segment passing near the brush until its pieces are short relative
   to the brush radius. Inserted points sit exactly ON the segment they split --
   measured deviation from the original polyline is 0.000000 canvas units, and
   verify_liquify asserts it rather than taking my word for it.

   WHAT IT IS NOT is bit-identical on screen, and the first version of this
   comment claimed it was. paintSeg draws every segment as its own stroke()
   call, so splitting one into pieces makes the renderer lay down two
   anti-aliased rims where there had been one, and abutting coverage does not
   composite to exactly the same alpha. Measured: +0.9% lit pixels, +0.37% ink
   mass, deltas scattered along the EDGES of lines rather than at corners. A
   line gets a hair heavier and nothing moves. That is a real difference and
   worth naming, but it is a rasteriser artifact rather than a change to the
   drawing, which is why the assertion is on the geometry and only a bounded
   tolerance on the pixels.

   THE POINT BUDGET IS NOT OPTIONAL. The server refuses a frame over
   MAX_POINTS_PER_FRAME (20,000), so a tool that inserts points can make a
   drawing unpostable -- and it would do it silently, at the moment the user
   tries to share. Subdivision stops well under that ceiling and simply
   declines to add more; the result on an already-dense page is the old
   behaviour, which was never wrong, only coarse. */
const LIQUIFY_SEG = 0.30;         // target piece length, as a fraction of the radius
const LIQUIFY_SPLIT_MAX = 12;     // per segment, so one huge line cannot explode
const LIQUIFY_POINT_CAP = 16000;  // headroom under the server's 20,000

/* Squared distance from a point to a SEGMENT, not to its endpoints. A long
   line whose ends are both far from the brush can still pass straight through
   it, and testing endpoints alone would skip exactly the segment most in need
   of splitting. */
function _segDist2(px, py, ax, ay, bx, by){
  const vx = bx - ax, vy = by - ay;
  const len2 = vx * vx + vy * vy;
  let t = len2 ? ((px - ax) * vx + (py - ay) * vy) / len2 : 0;
  t = t < 0 ? 0 : (t > 1 ? 1 : t);
  const dx = px - (ax + vx * t), dy = py - (ay + vy * t);
  return dx * dx + dy * dy;
}

function liquifySubdivide(f, px, py, r){
  if(f.strokes.length >= LIQUIFY_POINT_CAP) return false;
  const target = Math.max(2, r * LIQUIFY_SEG), target2 = target * target;
  // A little wider than the brush: a segment just outside it this frame is
  // about to be inside it on the next one, and splitting it late shows up as a
  // kink that appears halfway through the drag.
  const reach = r * 1.4, reach2 = reach * reach;
  const out = [], groups = [];
  let at = 0, changed = false;
  for(let g = 0; g < f.strokeGroups.length; g++){
    const n = f.strokeGroups[g];
    let count = 0;
    for(let k = 0; k < n; k++){
      const a = f.strokes[at + k];
      out.push(a); count++;
      if(k === n - 1) break;
      const b = f.strokes[at + k + 1];
      if(_segDist2(px, py, a.x, a.y, b.x, b.y) > reach2) continue;
      const dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
      if(d2 <= target2) continue;
      if(out.length >= LIQUIFY_POINT_CAP) continue;
      const pieces = Math.min(LIQUIFY_SPLIT_MAX,
                              Math.ceil(Math.sqrt(d2) / target));
      for(let sIdx = 1; sIdx < pieces; sIdx++){
        const t = sIdx / pieces;
        const mid = Object.assign({}, a);
        mid.x = a.x + dx * t;
        mid.y = a.y + dy * t;
        if(typeof a.size === 'number' && typeof b.size === 'number')
          mid.size = a.size + (b.size - a.size) * t;
        // Interpolated so REPLAY still draws the stroke at the pace it was
        // drawn. Copying `a.t` would stack every inserted point at one instant
        // and the line would jump rather than travel.
        if(typeof a.t === 'number' && typeof b.t === 'number')
          mid.t = a.t + (b.t - a.t) * t;
        // Only the FIRST point of a stroke carries `start`. Object.assign
        // copied it off `a`, so splitting the opening segment of a stroke would
        // have minted a second start point inside it and broken the run.
        delete mid.start;
        out.push(mid); count++; changed = true;
      }
    }
    groups.push(count);
    at += n;
  }
  if(changed){ f.strokes = out; f.strokeGroups = groups; }
  return changed;
}

/* The warp. Called per pointermove with the CURRENT point; the displacement is
   the delta since the last move, so speed comes out of the gesture for free --
   a fast drag moves the ink further than a slow one over the same distance,
   exactly as a finger through paint would.

   Only the current page is touched. Smudging every page at once is what Move
   mode's "all pages" scope is for, and conflating the two would make an
   irreversible-looking mess out of a tool people reach for casually. */
function liquifyMove(pt){
  const f = liquifyFrame(); if(!f || !liquifyLast) return false;
  const dx = pt.x - liquifyLast.x, dy = pt.y - liquifyLast.y;
  liquifyLast = { x: pt.x, y: pt.y };
  if(!dx && !dy) return false;
  const r = liquifyRadius(), r2 = r * r;
  // Resolution BEFORE displacement, every move: a segment only needs splitting
  // once, and after that this is a cheap no-op on it. Splitting after the warp
  // would bend the coarse line first and interpolate the kink.
  if(liquifySubdivide(f, pt.x, pt.y, r)) liquifyTouched = true;
  // Bounding-box reject before the distance test. A page can hold thousands of
  // points and this runs at the display rate; a hypot per point per frame is
  // the difference between a tool that tracks the finger and one that does not.
  const x0 = pt.x - r, x1 = pt.x + r, y0 = pt.y - r, y1 = pt.y + r;
  const pts = f.strokes;
  let touched = false;
  for(let i = 0; i < pts.length; i++){
    const p = pts[i];
    if(p.x < x0 || p.x > x1 || p.y < y0 || p.y > y1) continue;
    const ex = p.x - pt.x, ey = p.y - pt.y, d2 = ex * ex + ey * ey;
    const w = liquifyWeight(d2, r2);
    if(w <= 0) continue;
    p.x += dx * w * LIQUIFY_STRENGTH; p.y += dy * w * LIQUIFY_STRENGTH;
    touched = true;
  }
  if(touched) liquifyTouched = true;
  return touched;
}

/* Nothing caught -> NO undo entry. A tap with the liquify tool selected, or a
   drag across empty canvas, must not push a no-op onto the history: the next
   Undo would appear to do nothing and the stroke the user actually wanted back
   would be one press further away than they expect. */
/* ---- smudge and blur: the same sweep, two different verbs ------------------
 *
 * Both act on ink already on the page, both use a round brush with a falloff,
 * and both reuse Liquify's undo shape: a whole-frame before/after snapshot,
 * because these tools can change the LENGTH of the strokes array (smudge
 * subdivides) and an index-keyed diff cannot describe an insertion.
 *
 * SMUDGE IS NOT LIQUIFY WITH A NEW NAME, and it would have been easy to ship it
 * as one. Liquify displaces with a smooth shoulder at half strength: it warps a
 * whole region, like pushing a sheet of rubber. Smudge is a fingertip — a
 * sharper falloff and nearly full strength, so the ink right under the touch
 * comes with you and the ink a few pixels away barely moves. Same traversal,
 * genuinely different gesture.
 *
 * BLUR FADES AND WIDENS rather than convolving, because there is no raster
 * layer to convolve. lib/brushfield.js carries the reasoning and the honest
 * statement of what that cannot do. */
const SMUDGE_STRENGTH = 0.92;   // vs Liquify's 0.5 -- the ink comes with you
const SMUDGE_SHARP = 2.2;       // vs Liquify's 1 -- a fingertip, not a field
/* SMEARING, which is what makes this a smudge rather than a warp, and its
   absence is what the first version got wrong. Displacement alone IS Liquify;
   changing two constants gives you a sharper Liquify and the report said so in
   four words: "looks like liquefy".
   Real smudged paint THINS as it travels -- there is only so much pigment and
   dragging it spreads that pigment over more area. So the ink a smudge carries
   also fades toward the ground and widens, in proportion to how far it has been
   dragged. The result is a softening tail instead of a hard spike, which is the
   difference a user actually sees. Accrued per pixel travelled for the reason
   BLUR_RATE gives: per-event accrual makes the effect a property of the
   hardware. */
const SMUDGE_SMEAR = 0.010;     // per pixel travelled
/* NO MOMENTUM HERE, AND THAT IS A DECISION RATHER THAN AN OMISSION.

   In a vector deformation smudge, directional momentum is not equivalent to
   raster pigment momentum. Point coasting increases displacement contrast and
   produces spikes, so smear length is controlled through the spread/fade
   response below rather than through post-contact inertia.

   The reference form, v_new = lambda*v_old + (1-lambda)*delta displaced as
   p += v_new*S*W(d), is provably a no-op here: v is a convex combination of
   unit vectors, so |v| <= 1 and the result is at most the delta*S*W already
   applied. In a raster smudge the velocity carries a sampled colour RESERVOIR
   and the reservoir's inertia extends the smear; here the geometry IS the
   material, so there is no second thing to carry. Letting points coast after
   the brush passes does lengthen the smear and makes it POINTIER, because the
   points influenced most coast furthest and pull away from their neighbours.
   Built, measured and discarded; DECISIONS.md v257 has the numbers. */

/* HOW FAR THE SMEAR GOES, raised from 0.32 / 0.45 in v257 after rendering three
   gesture classes side by side at four settings: a single perpendicular pull,
   repeated back-and-forth rubbing across a line, and a tight curved scrub.

   0.55 / 0.9 was better than the old values in all three and 0.68 / 1.15 was
   worse in all three -- at that strength the dragged ink goes muddy against the
   dark ground and the rubbed patch reads as a blob rather than as pigment.

   JUDGED FROM RENDERS, deliberately. Two scalar metrics in this area have now
   rewarded the wrong artefact: the y-spread of the dragged points went UP for
   the coasting-momentum build that visibly turned smears into spikes, and the
   suite's own smear check is `smeared > 0`, which passes at every setting there
   is. The magnitude is asserted below so that this pair of numbers cannot
   quietly drift back.

   This is a response curve, not a mechanism: the deformation field is untouched
   and still rate-independent. */
const SMUDGE_FADE_MAX = 0.55;   // gentler than blur: it is a side effect, not the point
const SMUDGE_SPREAD_MAX = 0.9;
/* BLUR ACCUMULATES AGAINST THE PRE-DRAG SNAPSHOT, NOT AGAINST ITSELF, and that
   is a correctness point rather than a nicety.

   The obvious way -- fade each point a little on every pointermove -- makes the
   strength depend on HOW MANY EVENTS FIRED, which depends on the hardware. A
   240Hz phone would blur several times harder than a 60Hz laptop for the same
   gesture, and v230's coalesced sampling made that worse by design. Measured
   before this was fixed: one short swipe took #ffffff to rgb(87,89,92), most of
   the way to the background, in a single pass.

   So each touched point carries an accumulated weight that saturates at 1, the
   colour and size are recomputed from the point's ORIGINAL values every time,
   and -- the part that actually does the work -- the weight accrues PER PIXEL
   THE BRUSH TRAVELS rather than per event. Saturation alone is not enough: it
   bounds the maximum but a 4-event sweep still lands somewhere different from a
   40-event one until they cover the same distance. Distance is the physical
   quantity a brush actually deposits against, and it is the same number however
   often the OS sampled the finger.

   Going over the ink a second time still deepens it, because a new drag starts
   from a new snapshot. */
const BLUR_RATE = 0.012;        // per PIXEL TRAVELLED, not per event -- see below
/* BLUR_FADE_MAX and BLUR_SPREAD_MAX lived here and are gone with v256. They
   were how far one drag could push a point toward the ground and how much
   wider it could make it -- the two numbers of a tool that dimmed and fattened
   a line rather than softening it. The halo replaces both: BLUR_CORE_KEEP is
   how much contrast the core gives up, and BLUR_PASSES is the falloff. */

let _fieldIdx = -1, _fieldBefore = null, _fieldLast = null,
    _fieldTouched = false, _fieldLabel = '';
let _blurAcc = null;            // point index -> accumulated weight, this drag
let _smear = null;              // point OBJECT -> smear state, this drag

function fieldBegin(pt, label){
  // Pinned to the page the gesture STARTED on, for the reason liquifyBegin
  // spells out: the page can change mid-drag and the back half of the gesture
  // would land somewhere else.
  _fieldIdx = idx; _fieldLabel = label; _fieldTouched = false;
  _fieldLast = { x: pt.x, y: pt.y };
  _blurAcc = new Map();
  _smear = new WeakMap();
  const f = frames[_fieldIdx];
  _fieldBefore = f ? { strokes: f.strokes.map(q => Object.assign({}, q)),
                       groups: f.strokeGroups.slice() } : null;
}

const _fieldPhotoNoted = Object.create(null);
function fieldPhotoNote(label){
  const k = label || 'This';
  if(_fieldPhotoNoted[k]) return;
  _fieldPhotoNoted[k] = true;
  chip(k + ' works on your strokes, not the photo');
}
/* "Nothing was under your brush" -- said once per tool per session, on the same
   budget as the photo note beside it. Once is the right number: it is a hint
   about aim, and a person who has read it does not need it on every stray drag. */
const _fieldMissNoted = Object.create(null);   // const, like _fieldPhotoNoted beside it
function fieldMissNote(label){
  const k = label || 'This';
  if(_fieldMissNoted[k]) return;
  _fieldMissNoted[k] = true;
  chip(frame() && frame().strokes.length
       ? k + ' needs to be dragged over your lines'
       : k + ' works on lines you have drawn \u2014 draw something first');
}
function fieldEnd(){
  const at = _fieldIdx, before = _fieldBefore, f = frames[at];
  const touched = _fieldTouched, label = _fieldLabel;
  _fieldBefore = null; _fieldLast = null; _fieldIdx = -1; _fieldTouched = false;
  _blurAcc = null; _smear = null;
  // Nothing caught -> NO undo entry, the same rule liquifyEnd states: a tap on
  // empty canvas must not push a no-op the user then has to press through.
  if(!touched || !before || !f){
    // ...but SILENCE IS NOT THE SAME AS NOTHING TO SAY. v240 added a note for
    // one case, a photo showing, because the owner reported the tool looking
    // broken. The case underneath it is commoner and was left mute: a drag that
    // simply missed the ink. You aim slightly off your line, nothing happens,
    // nothing is said, and the tool reads as broken for exactly the same reason.
    // Both are now explained, the photo case first because it is the more
    // surprising of the two.
    //
    // On a PHOTO, "nothing happened" is the tool's honest limit rather
    // than an empty canvas. These tools move
    // and recolour STROKE POINTS; a photograph is not strokes, and softening it
    // would need a raster layer the frame format does not have (the long
    // version is in lib/brushfield.js). Said once per tool per session --
    // enough to explain, not enough to nag.
    if(!touched){
      if(photoShowing()) fieldPhotoNote(label);
      else fieldMissNote(label);
    }
    return false;
  }
  noteAction({ type: 'liquify', label: label, idx: at, before: before,
               after: { strokes: f.strokes.map(q => Object.assign({}, q)),
                        groups: f.strokeGroups.slice() } });
  return at;
}

function smudgeMove(pt){
  const f = frames[_fieldIdx]; if(!f || !_fieldLast) return false;
  const dx = pt.x - _fieldLast.x, dy = pt.y - _fieldLast.y;
  _fieldLast = { x: pt.x, y: pt.y };
  if(!dx && !dy) return false;
  const travel = Math.sqrt(dx * dx + dy * dy);
  const r = liquifyRadius();
  // Resolution BEFORE displacement, exactly as liquifyMove does it: a segment
  // with two vertices in the brush can only bend into a corner, and splitting
  // after the warp interpolates the kink instead of preventing it.
  //
  // NOTE the ordering hazard this creates for the smear below: subdividing
  // INSERTS points, so an index taken before the split refers to a different
  // point after it. The accumulator is therefore keyed off the CURRENT index
  // each pass and the original is read from the live point, not the snapshot --
  // the snapshot's indices stop matching the moment a segment is split.
  if(liquifySubdivide(f, pt.x, pt.y, r)) _fieldTouched = true;
  const hit = SkriblBrushField.each(f.strokes, pt.x, pt.y, r, SMUDGE_SHARP,
    (p, w) => {
      p.x += dx * w * SMUDGE_STRENGTH; p.y += dy * w * SMUDGE_STRENGTH;
      // The smear. Ink that has been dragged thins: it fades toward the ground
      // and spreads. Without this the tool is Liquify with different numbers.
      //
      // The accumulator lives in a WeakMap keyed by the POINT, not in a
      // property on it. Points are serialised wholesale into the payload and
      // copied by Object.assign for the undo snapshot, so a scratch field named
      // `_sm` would ride into every saved draft, every shared Skribl and the
      // server's validator. Keying off the object also survives
      // liquifySubdivide inserting points mid-drag, which an index cannot.
      let st = _smear.get(p);
      if(!st){ st = { acc: 0, color: p.color, size: p.size }; _smear.set(p, st); }
      st.acc = Math.min(1, st.acc + w * SMUDGE_SMEAR * travel);
      p.color = SkriblBrushField.mix(st.color, bgColor, st.acc * SMUDGE_FADE_MAX);
      p.size = st.size * (1 + st.acc * SMUDGE_SPREAD_MAX);
    });
  if(hit) _fieldTouched = true;
  return hit;
}

/* ---------- v256: blur that actually softens an edge -------------------------

   WHAT SHIPPED UNTIL NOW WAS A FADE. The old blur mixed each touched point
   toward bgColor and widened it. Measured on a vertical slice through a line:
   the feathered transition band was 5 rows before the drag and 5 rows after,
   while the peak halved and the solid core doubled. Softening an edge is the
   one thing the word promises and it did none of it -- it made the line dimmer
   and fatter, with the same knife-sharp edge, because a stroke point is drawn
   as a solid round dab and nothing about recolouring it can feather anything.

   THE VECTOR-NATIVE BLUR IS EXPANDED TRANSLUCENT COPIES. Draw the same path
   several times, widest and faintest first, so the crisp core lands on top of
   its own halo; the overlap of the passes IS the falloff. It is not a
   convolution and it cannot soften a photograph underneath -- that limit is
   unchanged and lib/brushfield.js still states it -- but on line art it reads
   as defocus, which is what the tool is for.

   THE MACHINERY ALREADY EXISTED, in the in-between: TWEEN_BLUR is this exact
   stack and has been drawing halos since v238. The blur brush was the one
   thing on the surface not using it.

   THE ALPHA IS AN 8-DIGIT HEX, and that is what makes this affordable. A halo
   written as rgba() is a translucent stroke, and paintStatic gives every
   translucent stroke its own offscreen layer -- clear, redraw, composite --
   against a LAYER_BUDGET of 24. Four passes per blurred stroke would blow that
   after six strokes and flip the whole frame to direct painting, changing how
   every other stroke on it looks. alphaOf, which is the layering test, only
   recognises rgba(), so a '#rrggbbaa' pass is budgeted as opaque while the
   canvas still renders it translucent. Measured: ten strokes drawn, five hex
   and five rgba, and the layerable count was 4.

   IT REBUILDS FROM THE PRE-DRAG SNAPSHOT ON EVERY MOVE rather than editing in
   place. That keeps the accumulate-against-the-original property BLUR_RATE
   argues for, makes the operation idempotent (going over the same ink twice in
   one drag cannot compound), and means the live preview is built by the same
   code as the committed result -- so there is nothing to jump at pointer-up.
   The hit test therefore runs against the SNAPSHOT, whose indices are stable,
   not against the frame being rebuilt underneath it. */

/* Widest and faintest first; the last entry is the core and is always kept.
   `d` is a fraction of the soft edge ADDED to the brush, never a multiple of
   it -- v238 learned that the hard way: multiplying made a 60px ball into a
   200px cloud, which inflates rather than softens. */
const BLUR_PASSES = [ { d: 1.00, a: 0.13 }, { d: 0.62, a: 0.22 },
                      { d: 0.30, a: 0.38 }, { d: 0.00, a: 1.00 } ];
/* How wide the soft edge is in canvas pixels. Same shape as tweenSoftEdge: it
   scales gently with the brush and is bounded at both ends, so a hairline does
   not get a disproportionate halo and a fat brush gets a soft EDGE rather than
   a cloud. */
/* MEASURED, not guessed. Feathered rows across a mid-line slice of a 7px line,
   before -> after one blur pass, at five multipliers:

       0.55  1 -> 4     1.8  1 -> 7      3.2  1 -> 13
       1.2   1 -> 5     2.4  1 -> 10

   2.4 takes the softened band from 1 row to 10 and puts the widest pass at
   23.8px against a 7px core -- soft, and still recognisably a line. 3.2 is a
   cloud at that size.

   THE CAP IS WHAT KEEPS v238's LESSON. Above roughly an 11px brush the
   multiplier stops mattering and the soft edge is a flat 26px, so a 24px stroke
   goes to 50 and a 60px ball to 86 -- a soft EDGE either way, never the 200px
   cloud that multiplying without a bound produced. Both were measured: at 24px
   and at 60px the feather is 16 and 14 rows and the multiplier makes no
   difference, because both are already on the cap. */
function blurSoftEdge(size){ return Math.max(6, Math.min(26, size * 2.4)); }
/* How much contrast the core gives up where the brush passed. A blurred line
   loses punch; it does not vanish. */
const BLUR_CORE_KEEP = 0.42;
/* Below this the point was barely brushed and gets no halo -- otherwise every
   drag mints a halo pass over the entire stroke it grazed. */
const BLUR_EPS = 0.02;
/* The server refuses a frame over MAX_POINTS_PER_FRAME (20,000) and
   MAX_GROUPS_PER_FRAME (5,000), and this multiplies the blurred RUNS by the
   pass count. Passes are shed rather than the blur refused: the last entry is
   the core, so shedding always drops the widest, faintest halo first and the
   worst case degrades to exactly the fade this replaced. */
const BLUR_POINT_CAP = 15000, BLUR_GROUP_CAP = 4000;
/* Samples per dab width along a halo run. Five is enough that the overlap is
   uniform rather than periodic -- which is what stops the beading -- without
   spending points nobody can see. It is also the n that the alpha compensation
   below divides by, so the two numbers are the same number on purpose. */
const BLUR_OVERLAP = 5;
function blurPasses(extraPts, extraRuns, basePts, baseRuns){
  for(let n = BLUR_PASSES.length; n > 1; n--){
    const halos = n - 1;
    if(basePts + extraPts * halos <= BLUR_POINT_CAP
       && baseRuns + extraRuns * halos <= BLUR_GROUP_CAP)
      return BLUR_PASSES.slice(BLUR_PASSES.length - n);
  }
  return BLUR_PASSES.slice(-1);
}

/* Densify a run so its dabs overlap uniformly, and pay the alpha back for the
   density. BOTH HALVES ARE REQUIRED and each one breaks without the other.

   A hex-alpha stroke is painted DIRECT -- that is the point of writing the
   alpha as hex, since the layered path is what costs LAYER_BUDGET -- and direct
   painting makes translucent ink COMPOUND where consecutive dabs overlap. A
   line of 38 points over 440px drawn at 24px wide overlaps its neighbour in a
   lens shape, and the first version of this drew a visible string of circles.
   Spacing the samples well inside the dab width makes that overlap uniform
   along the run rather than periodic, which is why the in-between's halo has
   never beaded: an exposure is dense everywhere.

   Density alone then makes it too BRIGHT -- measured, a peak of 254 and a
   ten-row core, brighter than the line it was meant to soften. n dabs of alpha
   x compositing over each other give 1 - (1-x)^n, so the per-dab alpha that
   accumulates to the intended weight is 1 - (1-T)^(1/n). Derived, not tuned,
   and n is the overlap the run ACTUALLY ended up with rather than the one it
   asked for. */
function blurDensify(seg){
  if(seg.length < 2) return seg;
  let len = 0;
  for(let k = 1; k < seg.length; k++)
    len += Math.hypot(seg[k].x - seg[k-1].x, seg[k].y - seg[k-1].y);
  if(!(len > 0)) return seg;
  const wide = seg.reduce((m, q) => Math.max(m, q.size || 0), 0);
  const want = Math.ceil(len / Math.max(1, wide / BLUR_OVERLAP)) + 1;
  if(want > seg.length) seg = tweenResample(seg, Math.min(want, seg.length * 12));
  const spacing = len / Math.max(1, seg.length - 1);
  const n = Math.max(1, Math.min(BLUR_OVERLAP * 2, wide / Math.max(0.001, spacing)));
  if(n > 1) for(const q of seg){
    const t = strokeAlphaOf(q.color);
    if(t > 0 && t < 1)
      q.color = tweenFade(q.color, (1 - Math.pow(1 - t, 1 / n)) / t);
  }
  return seg;
}

/* Rebuilds the frame from the snapshot plus the accumulated per-point weights.
   Halo passes for every blurred sub-run first, then the original runs with the
   core faded where the brush went -- array order is paint order, so the core
   lands on top of its own halo. */
function blurRebuild(f){
  const snap = _fieldBefore;
  if(!snap) return;
  const orig = snap.strokes, groups = snap.groups;
  // Contiguous stretches of brushed points, per run. A run the brush crossed in
  // two places gets two halos rather than one spanning the gap between them.
  const runs = [];
  let at = 0, extraPts = 0, extraRuns = 0;
  for(let g = 0; g < groups.length; g++){
    const count = groups[g];
    let s = -1;
    for(let k = 0; k <= count; k++){
      const acc = k < count ? (_blurAcc.get(at + k) || 0) : 0;
      if(acc > BLUR_EPS && s < 0) s = k;
      else if((acc <= BLUR_EPS || k === count) && s >= 0){
        // One point either side, so the halo does not stop dead mid-line.
        const a0 = Math.max(0, s - 1), a1 = Math.min(count - 1, k);
        runs.push({ at: at, from: a0, to: a1 });
        extraPts += (a1 - a0 + 1); extraRuns++;
        s = -1;
      }
    }
    at += count;
  }
  const passes = blurPasses(extraPts, extraRuns, orig.length, groups.length);
  const halo = passes.slice(0, passes.length - 1);
  const out = [], outG = [];
  for(let p = 0; p < halo.length; p++){
    const pass = halo[p];
    for(const r of runs){
      let seg = [];
      for(let k = r.from; k <= r.to; k++){
        const src = orig[r.at + k];
        // An eraser stroke has no colour to fade and punches a hole; haloing it
        // would smear the hole outward, which is not what softening a line means.
        if(src.erase){ seg.length = 0; break; }
        const acc = Math.min(1, _blurAcc.get(r.at + k) || 0);
        const q = Object.assign({}, src);
        const base = typeof src.size === 'number' ? src.size : 1;
        q.size = base + blurSoftEdge(base) * pass.d * acc;
        q.color = tweenFade(src.color, pass.a * acc);
        seg.push(q);
      }
      seg = blurDensify(seg);
      if(seg.length){
        seg[0].start = true;
        for(let k = 1; k < seg.length; k++) delete seg[k].start;
        out.push(...seg); outG.push(seg.length);
      }
    }
  }
  for(let g = 0, a = 0; g < groups.length; g++){
    const count = groups[g];
    let core = [], touched = false;
    for(let k = 0; k < count; k++){
      const src = orig[a + k];
      const acc = Math.min(1, _blurAcc.get(a + k) || 0);
      const q = Object.assign({}, src);
      if(acc > 0 && !src.erase){
        const base = typeof src.size === 'number' ? src.size : 1;
        q.size = base + blurSoftEdge(base) * 0.18 * acc;
        q.color = tweenFade(src.color, 1 - (1 - BLUR_CORE_KEEP) * acc);
        touched = true;
      }
      core.push(q);
    }
    /* The core is translucent where the brush went, and a translucent run beads
       at its own dab spacing exactly as a halo pass does -- this was drawn as a
       string of bright circles before the same treatment was applied to it.
       Untouched runs are left ALONE: they are the user's strokes, still opaque,
       and resampling them would rewrite geometry the blur never reached. */
    if(touched) core = blurDensify(core);
    core[0].start = true;
    for(let k = 1; k < core.length; k++) delete core[k].start;
    out.push(...core); outG.push(core.length);
    a += count;
  }
  f.strokes = out; f.strokeGroups = outG;
}

function blurMove(pt){
  const f = frames[_fieldIdx]; if(!f) return false;
  // Distance since the last sample, BEFORE _fieldLast moves. This is what makes
  // the tool's strength independent of the sample rate; see BLUR_RATE. The
  // first event of a drag has no previous point, so it gets one nominal step
  // rather than zero -- a tap should still do something.
  const dxm = _fieldLast ? (pt.x - _fieldLast.x) : 0;
  const dym = _fieldLast ? (pt.y - _fieldLast.y) : 0;
  const travel = _fieldLast ? Math.sqrt(dxm * dxm + dym * dym) : 4;
  _fieldLast = { x: pt.x, y: pt.y };
  const r = liquifyRadius();
  // No subdivision: blur does not move anything, so a coarse segment blurs just
  // as well as a fine one and splitting it would only cost points.
  //
  // THE HIT TEST RUNS AGAINST THE SNAPSHOT, not against f.strokes. blurRebuild
  // replaces the frame's arrays on every move -- it inserts halo passes ahead
  // of the original runs -- so an index taken from the live frame would refer
  // to a different point on the next event, and the accumulator is keyed by
  // index. The snapshot is the one array that does not move under it.
  if(!_fieldBefore) return false;
  const hit = SkriblBrushField.each(_fieldBefore.strokes, pt.x, pt.y, r, 1, (p, w, i) => {
    // Saturating accumulation against the ORIGINAL point. See the note on
    // BLUR_RATE: applying a delta per event makes the tool's strength a
    // property of the device's sample rate.
    _blurAcc.set(i, Math.min(1, (_blurAcc.get(i) || 0) + w * BLUR_RATE * travel));
  });
  if(hit){ _fieldTouched = true; blurRebuild(f); }
  return hit;
}

function liquifyEnd(){
  const at = liquifyIdx;
  const before = liquifyBefore;
  const f = frames[at];
  const touched = liquifyTouched;
  liquifyBefore = null; liquifyLast = null; liquifyIdx = -1; liquifyTouched = false;
  /* Nothing caught -> NO undo entry. A tap with the liquify tool selected, or a
     drag across empty canvas, must not push a no-op onto the history: the next
     Undo would appear to do nothing and the stroke the user actually wants back
     would be one press further away than they expect. */
  if(!touched || !before || !f) return false;
  // Whole-frame before/after, because subdivision changes the LENGTH of the
  // array -- an index-keyed diff cannot describe an insertion. selframe has
  // carried this shape since mirror/duplicate/cut for exactly the same reason.
  noteAction({ type: 'liquify', idx: at, before: before,
               after: { strokes: f.strokes.map(q => Object.assign({}, q)),
                        groups: f.strokeGroups.slice() } });
  return at;
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
    // THE ONE MOMENT THE STAMP BUTTON EXISTS AND THE SHELF IS STILL EMPTY.
    // Said here rather than on the shelf because this is when the control is
    // actually on screen to be pointed at -- the shelf's copy of this sentence
    // is read while the selection bar does not exist. Once per person: it is
    // an introduction, not a nag, and SkriblHints keeps that promise.
    if(selSpans.length && !stampShelf.length && window.SkriblHints){
      // LIGHT THE BUTTON UP, do not describe it. Below the "regular" size class
      // the selection bar is icons only (.pb-tx is display:none), so there is
      // no button labelled "Stamp" to tell anyone to press -- and the word
      // "Stamp" DOES appear in the tool tray, so a sentence naming it sends the
      // reader exactly where the owner went and got stuck. The spotlight works
      // at every size and in every language.
      // onHide rather than a timer of its own. The ring is what the sentence
      // MEANS by "the highlighted button", so it has to outlive the sentence or
      // match it -- and it used to go out at 6s while an action hint dwells
      // DURATION * 2, leaving six seconds of a toast pointing at nothing.
      // Tying it to the toast keeps them in step even if the dwell changes.
      // THE GLYPH COMES OUT OF THE BUTTON ITSELF. "The highlighted button" is
      // only useful if the highlight is noticed; showing the icon means the
      // sentence identifies its own subject even if the ring is missed, and
      // lifting it rather than redrawing it means the toast cannot end up
      // showing a picture of a button that no longer looks like that.
      const _sbIcon = document.querySelector('#sbStamp svg');
      window.SkriblHints.show('stamp-where',
        'saves this selection to your Stamps shelf.',
        { action: { label: 'Stamp it', onClick: () => stampSaveSelection() },
          onHide: () => unspotlightStamp(),
          icon: _sbIcon ? _sbIcon.outerHTML : '' })
        && spotlightStamp();
    }
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

/* FILL — a region, expressed as strokes, because strokes are the only thing
   this format has. lib/floodfill.js carries the geometry and the reasoning; this
   is the part that has to know about canvases, colour and undo.

   IT READS WHAT IS ON SCREEN when there is no photo, and THE STROKE LAYER when
   there is. The original rule was the first half alone -- sample the composite,
   because that is what the user is pointing at, and filling "the white part" of
   a photo has to see the photo. Sound in the abstract, and it does not survive a
   real photograph.

   A photo is texture. Adjacent pixels differ by far more than FILL_TOLERANCE
   (32) almost everywhere, so a flood seeded on one stops within a few pixels and
   covers a speck. Reported from the live demo on a drawing made over a photo:
   the tool simply appeared not to work. The tolerance cannot be raised to fix it
   either -- a value loose enough to cross photo grain is loose enough to walk
   straight through a drawn line.

   So with a photo showing, the flood runs against the background colour plus
   this frame's strokes: fill the region MY INK encloses, which is what the tool
   means when you have drawn on top of something. It is identical to the old
   behaviour when there is no photo, because then the two images are the same.

   THE COST, stated because the original comment was right that there is one:
   tapping somewhere your strokes do not enclose now floods everything up to
   them, painting over the photo. That is exactly what a tap outside a shape has
   always done on a plain background, so the model is the one users already have
   -- but it is a real change, and it is reversible in one branch below.

   DEVICE PIXELS IN, CANVAS UNITS OUT. The canvas is scaled by DPR
   (pad.width = CW*DPR with ctx.scale(DPR,DPR)), so getImageData works in device
   pixels while strokes are stored in canvas units. The seed is multiplied going
   in and every run divided coming out. Getting this wrong is invisible at
   DPR 1 -- a desktop -- and doubles every coordinate on a phone.

   SOLID COLOUR, DELIBERATELY. See the note in lib/floodfill.js: rows overlap by
   design, so a translucent fill bands at every seam, and each run is its own
   stroke, so a translucent fill of a hundred runs blows LAYER_BUDGET and flips
   the whole frame to direct painting. solidOf() avoids both.

   ONE TAP IS ONE UNDO. The fill lands as many stroke groups, which is right for
   the payload -- the player replays them as a sweep and needs no new primitive
   -- but wrong for the editor, where popping fifty groups to take back one tap
   is not undo. The actionLog already carries object entries for moves; a
   'fill' entry says how many groups the tap produced and undoStroke pops them
   together. Nothing about the saved format changes. */
/* Is a photo actually on screen? Not "is one attached" -- an attached photo with
   its toggle off, or one still decoding, is not something the user is pointing
   at. Same condition drawBackdrop() paints on, deliberately: if these two ever
   disagree, fill samples an image the screen is not showing. */
function photoShowing(){
  return !!(photoEnabled && bgImageObj && bgImageObj.complete && bgImageObj.naturalWidth);
}
let _fillCv = null, _fillCtx = null;
/* The pixels the flood runs against. Without a photo this is the pad itself, so
   nothing changes and nothing is allocated. With one, it is the background
   colour plus this frame's strokes -- built here rather than kept in step with
   render(), because a cached layer that goes stale fills the shape you drew a
   moment ago. */
function fillSourceImage(f){
  if(!photoShowing()) return ctx.getImageData(0, 0, pad.width, pad.height);
  if(!_fillCv) _fillCv = document.createElement('canvas');
  if(_fillCv.width !== pad.width || _fillCv.height !== pad.height){
    _fillCv.width = pad.width; _fillCv.height = pad.height;
    _fillCtx = _fillCv.getContext('2d');
  }
  // setTransform first: the scale below is applied every call, and without the
  // reset it would compound into DPR^n on the second fill of a session.
  _fillCtx.setTransform(1, 0, 0, 1, 0, 0);
  _fillCtx.clearRect(0, 0, _fillCv.width, _fillCv.height);
  _fillCtx.scale(DPR, DPR);
  _fillCtx.fillStyle = bgColor;
  _fillCtx.fillRect(0, 0, CW, CH);
  paintStatic(_fillCtx, f.strokes);
  return _fillCtx.getImageData(0, 0, _fillCv.width, _fillCv.height);
}
/* Past this share of the canvas, a flood has almost certainly leaked through a
   gap rather than filled a shape. Two thirds rather than a half: filling a large
   background on purpose is common, and a note that cries wolf gets ignored. */
const FILL_ESCAPE_FRACTION = 0.66;
function doFill(p){
  if(playing) return;
  if(typeof SkriblFloodFill === 'undefined'){ chip('Fill is unavailable'); return; }
  const f = frame();
  let img;
  try { img = fillSourceImage(f); }
  catch(err){ chip('Fill cannot read this canvas'); return; }
  const res = SkriblFloodFill.runs(img, p.x * DPR, p.y * DPR,
                                   { tolerance: FILL_TOLERANCE });
  if(!res.runs.length){ chip('Nothing to fill there'); return; }
  const col = solidOf(penColorFor(color));
  const now = performance.now();
  let groups = 0, t = 0;
  for(const run of res.runs){
    // Each run is drawn at ITS OWN height — that is what stops a diagonal edge
    // coming out perforated. A flat region is one thick line; a sloping edge is
    // a stack of thin ones.
    const w = SkriblFloodFill.sizeOf(run) / DPR;
    const pts = SkriblFloodFill.points(run);
    for(let i = 0; i < pts.length; i++){
      f.strokes.push({ x: pts[i].x / DPR, y: pts[i].y / DPR, color: col, size: w,
                       t: now + (t++), erase: false, start: i === 0 });
    }
    f.strokeGroups.push(pts.length);
    groups++;
  }
  redoStack.length = 0;
  actionLog.push({ type:'fill', idx: idx, groups: groups });
  if(actionLog.length > MOVE_UNDO_LIMIT * 4) actionLog.shift();
  // A FLOOD THAT TAKES MOST OF THE CANVAS IS ALMOST ALWAYS A GAP IN THE
  // OUTLINE, not what was wanted. Measured on the audit: tapping inside an open
  // L-shape added 438 points and covered the page, silently, and the owner had
  // already reported this as "still not filling completely". The area is
  // already known here -- res.runs carries it -- so the diagnosis is free.
  //
  // It is a NOTE, not a refusal. Filling the background deliberately is a real
  // thing to want, and a tool that argues with you is worse than one that
  // explains itself. Undo is the remedy and the note says so.
  // A run is {y, x0, x1, h}, so its area is its span times its height. NOT
  // sizeOf(run) * points(run).length: points are SPACED along the run rather
  // than one per pixel, so that product silently undercounts by an order of
  // magnitude and the note never fires. Measured, not assumed.
  const _canvasPx = (pad.width * pad.height) || 1;
  let _filled = 0;
  for(const run of res.runs) _filled += Math.max(0, run.x1 - run.x0) * Math.max(1, run.h);
  chip(res.truncated ? 'Filled (area was clipped)'
       : (_filled / _canvasPx > FILL_ESCAPE_FRACTION
          ? 'Filled past your lines \u2014 the outline has a gap. Undo to go back'
          : 'Filled'));
  render(); refreshThumb(idx); updateToolState(); scheduleSave();
}

/* ---- stamps -----------------------------------------------------------------
 * A stamp is the selection clipboard with the three properties an animator
 * needs and a clipboard does not have: it survives the session, there is more
 * than one of it, and it lands where you tap. lib/stamps.js holds the encoding,
 * the budget and the reasoning; this half is the wiring.
 *
 * NOTHING ENTERS THE FORMAT. A placed stamp is ordinary stroke groups, exactly
 * what selPaste() appends, so a Skribl made with stamps opens in a player that
 * predates them. That is the same choice fill and the tween made, and for the
 * same reason: a format change is the last resort.
 *
 * THE SHELF IS NOT IN THE DRAFT. It is its own localStorage key, so a stamp
 * never rides in a Skribl the user shares, and so clearing a drawing does not
 * clear the assets they built for it. It also means the shelf is subject to the
 * origin quota alongside the draft -- v231's lesson, which lib/stamps.js
 * answers with a byte budget rather than by hoping.
 */
/* Headroom under the server's MAX_POINTS_PER_FRAME (20,000) and
   MAX_GROUPS_PER_FRAME (5,000), for liquify's reason stated at length above:
   a tool that ADDS points can make a page unpostable, and it would do it
   silently, at the moment the user tries to share. */
const STAMP_POINT_CAP = 16000;
const STAMP_GROUP_CAP = 4200;

function stampsReady(){ return typeof SkriblStamps !== 'undefined'; }

function loadStampShelf(){
  stampShelf = stampsReady() ? SkriblStamps.load(null) : [];
}

/* Save the current selection into the shelf. The ONLY route in — a stamp is
   made out of a selection and there is nowhere else it could come from, which
   is why this button lives on the selection bar rather than in the shelf. */
function stampSaveSelection(){
  if(playing) return;
  if(!stampsReady()){ chip('Stamps are unavailable'); return; }
  if(!selSpans.length){ chip('Pick something first'); return; }
  const st = SkriblStamps.fromRuns(selExtract(), { at: Date.now() });
  // fromRuns returns null for an empty selection AND for one over MAX_POINTS,
  // so the two are separated here rather than reported as one vague failure.
  if(!st){ chip('That is too big for a stamp'); return; }
  const why = SkriblStamps.fits(stampShelf, st);
  if(why === 'big'){ chip('That is too big for a stamp'); return; }
  // REFUSES, does not evict. Dropping the oldest stamp to fit a new one would
  // lose work the user deliberately made, with no event they could connect it
  // to — the amber-pill failure again.
  if(why){ chip('Stamp shelf is full — delete one first'); return; }
  // Newest first: the stamp you just made is the one you are about to place.
  stampShelf.unshift(st);
  if(!SkriblStamps.store(null, stampShelf)){
    stampShelf.shift();
    chip('No room to save that stamp');
    return;
  }
  stampArmed = 0;
  syncStampPop();
  chip('Saved to stamps');
}

function stampDelete(i){
  if(i < 0 || i >= stampShelf.length) return;
  stampShelf.splice(i, 1);
  if(stampsReady()) SkriblStamps.store(null, stampShelf);
  // The armed index is a position in a list that just got shorter. Leaving it
  // alone arms whatever slid into the gap, which is a different stamp than the
  // one with the ring on it.
  if(stampArmed === i) stampArmed = -1;
  else if(stampArmed > i) stampArmed--;
  syncStampPop();
}

/* Repaint the shelf from stampShelf. The single place the list becomes markup,
   so there is no second copy of it to fall out of step. */
function syncStampPop(){
  const grid = document.getElementById('stampGrid');
  const empty = document.getElementById('stampEmpty');
  if(!grid || !stampsReady()) return;
  grid.textContent = '';
  if(empty) empty.hidden = stampShelf.length > 0;
  const ground = bgColor;
  stampShelf.forEach((st, i) => {
    const cell = document.createElement('div');
    cell.className = 'stamp-cell';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'stamp-btn';
    btn.setAttribute('aria-pressed', String(i === stampArmed));
    btn.title = 'Place this stamp — tap the page';
    btn.setAttribute('aria-label', 'Stamp ' + (i + 1) + ' of ' + stampShelf.length);
    // Backing store at 2x so the thumbnail is not soft on a retina phone, which
    // is the only device the shelf is ever really used on.
    const cvs = document.createElement('canvas');
    const box = 62, s = 2;
    cvs.width = box * s; cvs.height = box * s;
    const g = cvs.getContext('2d');
    if(g){
      g.fillStyle = ground;
      g.fillRect(0, 0, cvs.width, cvs.height);
      SkriblStamps.draw(g, st, { x:0, y:0, w:cvs.width, h:cvs.height, pad:8*s, bg:ground });
    }
    btn.appendChild(cvs);
    btn.addEventListener('click', () => {
      // Tapping the armed stamp DISARMS it, so there is a way back to "no
      // stamp loaded" without leaving the tool.
      stampArmed = (stampArmed === i) ? -1 : i;
      syncStampPop();
    });
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'stamp-del';
    del.textContent = '×';
    del.title = 'Delete this stamp';
    del.setAttribute('aria-label', 'Delete stamp ' + (i + 1));
    del.addEventListener('click', (e) => { e.stopPropagation(); stampDelete(i); });
    cell.appendChild(btn);
    cell.appendChild(del);
    grid.appendChild(cell);
  });
}

/* Place the armed stamp centred on the tap.
   ONE TAP IS ONE UNDO, the same contract doFill() states: the placement lands
   as many stroke groups, which is right for the payload and wrong for the
   editor, so the actionLog carries one entry that knows how many groups to
   pop. */
function doStamp(p){
  if(playing) return;
  if(!stampsReady()){ chip('Stamps are unavailable'); return; }
  if(stampArmed < 0 || stampArmed >= stampShelf.length){
    chip(stampShelf.length ? 'Pick a stamp first' : 'No stamps yet — select something and tap Stamp');
    return;
  }
  const st = stampShelf[stampArmed];
  const f = frame();
  const runs = SkriblStamps.toRuns(st, p.x, p.y, stampScalePct / 100, performance.now());
  let pts = 0;
  for(const r of runs) pts += r.length;
  // Checked BEFORE anything is appended. Appending and then trimming would
  // leave a half-placed stamp on the page, which is worse than not placing it.
  if(f.strokes.length + pts > STAMP_POINT_CAP
     || f.strokeGroups.length + runs.length > STAMP_GROUP_CAP){
    chip('This page is too full for that stamp');
    return;
  }
  for(const r of runs){
    for(const q of r) f.strokes.push(q);
    f.strokeGroups.push(r.length);
  }
  redoStack.length = 0;
  actionLog.push({ type:'fill', label:'Stamp', idx: idx, groups: runs.length });
  if(actionLog.length > MOVE_UNDO_LIMIT * 4) actionLog.shift();
  chip('Stamped');
  render(); refreshThumb(idx); updateToolState(); scheduleSave();
}

function undoStroke(){
  invalidateClearUndo();
  if(playing) return;
  // A FILL is one action, and this must be tested BEFORE the generic object
  // branch below — that branch pops any object entry and then assumes it is a
  // move, so a fill entry reached it, fell past every m.type check and died on
  // m.idxs.length. Order is the whole of the fix.
  if(actionLog.length && typeof actionLog[actionLog.length-1] === 'object'
     && actionLog[actionLog.length-1].type === 'fill'){
    const m = actionLog.pop();
    if(m.idx !== idx) go(m.idx);
    const tf = frame();
    const counts = tf.strokeGroups.splice(tf.strokeGroups.length - m.groups, m.groups);
    let total = 0; for(const c of counts) total += c;
    const pts = tf.strokes.splice(tf.strokes.length - total, total);
    redoStack.push({ type:'fill', label: m.label, idx: m.idx, pts: pts, counts: counts });
    // Same entry shape, two producers: a stamp placement is also "N groups
    // appended at the end, one action", so it reuses this branch rather than
    // adding a second copy of it that would drift. Only the wording differs.
    chip((m.label || 'Fill') + ' undone');
    render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
    return;
  }
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
    // selFrameRestore, not selRestore: liquify subdivides, so its before/after
    // is a whole page rather than a set of indexed coordinates. Restoring by
    // index cannot undo an insertion.
    if(m.type === 'liquify'){
      if(m.idx !== idx) go(m.idx);
      selFrameRestore(m.idx, m.before);
      redoStack.push(m);
      chip((m.label || 'Liquify') + ' undone');
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
     && redoStack[redoStack.length-1].type === 'liquify'){
    const m = redoStack.pop();
    if(m.idx !== idx) go(m.idx);
    selFrameRestore(m.idx, m.after);
    actionLog.push(m);
    chip((m.label || 'Liquify') + ' redone');
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
  if(typeof redoStack[redoStack.length-1] === 'object'
     && redoStack[redoStack.length-1].type === 'fill'){
    const m = redoStack.pop();
    if(m.idx !== idx) go(m.idx);
    const tf = frame();
    for(const p of m.pts) tf.strokes.push(p);
    for(const c of m.counts) tf.strokeGroups.push(c);
    actionLog.push({ type:'fill', label: m.label, idx: m.idx, groups: m.counts.length });
    chip((m.label || 'Fill') + ' redone');
    render(); refreshThumb(m.idx); updateToolState(); scheduleSave();
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
  // lib/toolshelf.js already routes the cells IT built through the registry's
  // setTool. Running this one too fired both, and the second call re-derived
  // what the first had toggled.
  if(b.dataset.shelfBound) return;
  // The picker is NOT opened here any more — lib/toolshelf.js already calls the
  // surface's setTool for a shelf click, so doing it in both places toggled it
  // twice and left it shut. It lives in the toolShelf config, which the tray
  // reaches too.
  setTool(b.dataset.tool);
}));
loadStampShelf();
bindEl('sbStamp', 'click', ()=>{ if(!playing) stampSaveSelection(); });
/* The empty shelf's own way forward. It switches to Select and closes itself,
   because the shelf is the wrong place to be standing: nothing can enter it
   until a selection exists, and the control that puts one there is a tool. */
bindEl('stampEmptyGo', 'click', (e)=>{ e.stopPropagation(); setTool('select'); });
/* A ring around the real control for as long as the hint is up. Removed on the
   first press as well as on the timer, so it stops the moment it is understood
   rather than continuing to shout at someone who has already acted. */
function unspotlightStamp(){
  const b = document.getElementById('sbStamp');
  if(b) b.classList.remove('pb-spot');
}
function spotlightStamp(){
  const b = document.getElementById('sbStamp');
  if(!b) return;
  b.classList.add('pb-spot');
  // No timer here: the toast owns the lifetime and calls unspotlightStamp
  // through onHide. A press still ends it early, because once the button has
  // been found the ring has done its job.
  b.addEventListener('click', unspotlightStamp, { once: true });
}
(function stampScaleKnob(){
  const sl = document.getElementById('stampScale'), out = document.getElementById('stampScaleOut');
  if(!sl) return;
  const apply = ()=>{ stampScalePct = +sl.value || 100;
                      if(out) out.textContent = stampScalePct + '%'; };
  sl.addEventListener('input', apply);
  apply();
})();
/* Escape, and NOTHING ELSE — deliberately unlike shapePopDismiss. That function
   also closes on a click outside itself, which is right for a picker you use
   once per drawing and wrong here twice over: choosing a stamp does not finish
   with the shelf (you then place it, and the shelf is the only thing saying
   which one is armed), and the click that places it lands on the canvas, which
   is "outside". A shelf that vanished on the first placement would have to be
   reopened for the second. Leaving the tool closes it; setTool() owns that. */
(function stampPopEscape(){
  const pop=document.getElementById('stampPop');
  if(!pop) return;
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&!pop.hidden) pop.hidden=true; });
})();
/* Dismiss the shape picker on a tap outside it. Closing on a PICK is decided
   in the pick handler rather than here, because the decision now depends on
   whether the chosen kind revealed a knob -- which is the picker's knowledge,
   not the dismisser's. */
(function shapePopDismiss(){
  const pop=document.getElementById('shapePop');
  if(!pop) return;
  document.addEventListener('click',e=>{
    if(pop.hidden) return;
    // Dragged means pinned (lib/popdrag.js sets data-moved): a pop the user
    // positioned stops auto-dismissing. Escape and tool switches still close.
    if(pop.dataset.moved) return;
    if(e.target.closest('#shapePop')||e.target.closest('#shapeToolBtn')) return;
    pop.hidden=true;
  });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&!pop.hidden) pop.hidden=true; });
  // The grip that makes the pop movable at all. Shared with Pad.
  if(window.SkriblPopDrag) window.SkriblPopDrag.attach(pop, pop.querySelector('.pop-grip'));
  // The other half of the pinned-pop veil in the pointerdown handler: ANY
  // release lifts it, so no draw path can leave the panel invisible.
  const _unveil=()=>pop.classList.remove('pop-veiled');
  window.addEventListener('pointerup', _unveil, true);
  window.addEventListener('pointercancel', _unveil, true);
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
  // Done and Cancel end the mode without going through the shelf, so the shelf
  // has to be told — otherwise Artwork stays lit over a canvas that is no
  // longer in move mode. No recursion: moveMode is already false by here, so
  // setTool's own `else if(moveMode)` branch does nothing.
  if(!on && typeof flipTool !== 'undefined' && flipTool === 'artmove') setTool('pen');
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

// pbArt's binding is gone with the button: Artwork is a tool now, reached from
// the tool shelf like every other one. (v226, stage 1.)
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
bindEl('miRebuildTweens', 'click',()=>{ closeMenu(); rebuildTweens(); });
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
updateFlipEmptyHint();
// Yank the whisper the moment a stroke starts, so it is not sitting under it.
pad.addEventListener('pointerdown', () => {
  const _eh = document.getElementById('flipEmptyHint');
  if (_eh) _eh.classList.add('hidden');
}, { passive: true });
// A fresh document (nothing restored) starts on the preset that displays
// LARGEST in this device's stage — portrait phones get 9:16 instead of a 4:3
// letterbox floating in dead space; same rule as Pad's resizeCanvas(). Silent:
// sizing an empty page is not a draft worth claiming the autosave slot for.
// Measured AFTER sizeStage() above so the stage height is real, with the same
// 24/6px margins fitPad() reserves.
if(!restored && window.SkriblCanvasSizes && window.SkriblCanvasSizes.bestFor){
  const _st = document.querySelector('.flip-stage');
  if(_st && _st.clientWidth > 50 && _st.clientHeight > 50){
    const _avail = stageAvail(_st);
    const _best = window.SkriblCanvasSizes.bestFor(_avail.w, _avail.h);
    if(applyCanvasSize(_best.w, _best.h, {silent:true})){
      sizeStage(); buildStrip(); render(); syncCanvasSeg();
    }
  }
}
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
    { anchor: 'top-right',
      action: { label: 'How it works \u2192', onClick: function () { if (typeof openHelpDrawer === 'function') openHelpDrawer(); } } });
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

/* ---------- boot marker: the last statement in this file --------------------
   Its only job is to prove that this file reached its end. flip.js and app.js
   are classic scripts of several thousand lines, and a throw ANYWHERE at top
   level silently abandons every line after it — the page keeps rendering, the
   markup is all there, and some arbitrary suffix of the behaviour is simply
   missing. That failure mode cost four separate debugging rounds in one
   session, every one of them a `let` declared below a function that setTool()
   reaches during init, and every one of them presenting as several unrelated
   features breaking at once.

   verify_boot.py asserts this flag. It is the cheapest possible check for the
   most expensive possible bug, and unlike a page-error listener it also catches
   the case where something swallowed the throw. Keep it last. */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { flip: true });
