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
  const layers = [[pad, ctx], [onionCv, octx], [tmpCv, tctx], [frameCv, fctx]];
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
function syncGrid(){
  const g = document.getElementById('flipGrid'); if(!g) return;
  // Read the border rather than assume it. Hard-coding 1 here is what put the
  // grid a pixel off when the canvas border went to 2px.
  const b = parseFloat(getComputedStyle(pad).borderTopWidth) || 0;
  const w = Math.max(0, pad.offsetWidth  - 2*b);
  const h = Math.max(0, pad.offsetHeight - 2*b);
  g.style.left = (pad.offsetLeft + b) + 'px';
  g.style.top  = (pad.offsetTop  + b) + 'px';
  g.style.width = w + 'px';
  g.style.height = h + 'px';
  drawGrid(g, w, h);
}

function drawGrid(g, w, h){
  const dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
  const W = Math.round(w * dpr), H = Math.round(h * dpr);
  if(!W || !H) return;
  if(g.width !== W || g.height !== H){ g.width = W; g.height = H; }
  const c = g.getContext('2d');
  c.clearRect(0, 0, W, H);

  // The fine subdivision now runs at EVERY size.
  //
  // It was gated to >=560px back when the grid was CSS gradients: percentage
  // background-size put lines on fractional pixels, so at ~10px spacing the
  // fine layer rendered as an uneven wash rather than a grid. Drawing to a
  // canvas snapped to whole device pixels removed that cause, and the gate
  // outlived it — a phone was left with 43px cells and nothing between them.
  //
  // Majors stay at 8x6 so the coarse landmarks remain countable between
  // frames; the sub-cells add halves at 21.6px on a 346px phone canvas.
  const fine = true;
  const cols = 8, rows = 6;
  const line = Math.max(1, Math.round(dpr));   // whole device pixels only

  // Sub-cells first so the majors sit on top of them.
  if(fine) paint(cols*2, rows*2, 'rgba(255,255,255,.10)');
  paint(cols, rows, 'rgba(255,255,255,.26)');

  function paint(nx, ny, colour){
    c.fillStyle = colour;
    // Distribute across (W - line), not W.
    //
    // Clamping only the LAST line inward kept it on the canvas but stole its
    // width from the final cell alone: every other column measured 129-130
    // device px and the last one 126. One narrow column on the right edge is
    // exactly the kind of thing that reads as "the grid is off" without being
    // obviously wrong anywhere you can point at.
    //
    // Laying the lines out over the span that is actually available puts the
    // closing line at W - line by construction, and leaves every gap equal to
    // within rounding.
    const spanX = Math.max(1, W - line), spanY = Math.max(1, H - line);
    for(let i = 0; i <= nx; i++) c.fillRect(Math.round(i * spanX / nx), 0, line, H);
    for(let j = 0; j <= ny; j++) c.fillRect(0, Math.round(j * spanY / ny), W, line);
  }
}
window.addEventListener('resize', ()=>{ sizeStage(); positionSeg(); positionToolSlider(); if(!photoPanel.hidden) positionFitSlider(); });

let frames = [ newFrame() ];
let idx = 0;
let color = "#ffffff", size = 7, erasing = false, onion = true, fps = 12;
// Onion skin depth/tint are view-only session state — deliberately NOT persisted
// or posted, so they cannot affect the payload format or the player.
let onionDepth = 1, onionTint = false;
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
let ZoomView = null, pinching = false, _pinch = null;                        // canvas magnify (pinch/pan)
let redoStack = [];   // undone strokes for the current frame ({pts,count})
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

/* ---- autosave: a real frame-format Skribl ---- */
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
      const o = { strokes: f.strokes.slice(), strokeGroups: f.strokeGroups.slice(), background: bgColor };
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
function saveNow(){
  const empty = frames.length === 1 && frames[0].strokes.length === 0 && !bgImage && !musicData;
  if (empty) { try { localStorage.removeItem(AUTOSAVE_KEY); } catch (_) {} return; }
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeFlip()));
    // Stay amber while any media is still outstanding — a green light would claim
    // the session is fully recoverable when the files aren't in storage.
    showAutosaveStatus((pendingPhotoMeta || pendingMusicMeta) ? 'saved-no-media' : 'saved');
    return;
  } catch (e) {
    if (!isQuotaError(e)) { console.error('[skribl] autosave failed:', e); showAutosaveStatus('failed'); return; }
  }
  // Over quota — retry without the media bytes so the drawing itself still survives.
  // Remember the settings so the drawers can offer a "Re-add" card right away,
  // rather than the user only finding out after a reload.
  if (bgImage) pendingPhotoMeta = { fit:photoFit, opacity:photoOpacity, blur:photoBlur, zoom:photoZoom,
                                    offX:photoOffX, offY:photoOffY, enabled:photoEnabled, name:imageName };
  if (musicData) pendingMusicMeta = { enabled:musicEnabled, trimStart:trimStart, trimEnd:trimEnd,
                                      crossfadeMs:loopCrossfadeMs, name:musicName };
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(serializeFlip({ media: false })));
    showAutosaveStatus('saved-no-media');
  } catch (e2) {
    console.error('[skribl] autosave failed even without media:', e2);
    showAutosaveStatus('failed');
  }
}
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
  if(state!=='saving'){ el._hideTimer=setTimeout(()=>{ el.classList.remove('show'); setTimeout(()=>{ el.hidden=true; }, 300); }, 1600); }
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
      // current pad-format frame
      return { strokes: Array.isArray(f.strokes) ? f.strokes : [], strokeGroups: f.strokeGroups };
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
  photoFit = ['cover','contain','fill'].includes(ph.fit) ? ph.fit : 'cover';
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
    }
    return applyPayload(d);
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
    const a = seg[0].erase ? 1 : alphaOf(seg[0].color);
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

// Where the background image lands, honouring fit + zoom + reposition.
function photoRect(iw, ih){
  if (photoFit === 'fill') return { x:0, y:0, w:CW, h:CH };
  let s = photoFit === 'contain' ? Math.min(CW/iw, CH/ih) : Math.max(CW/iw, CH/ih) * photoZoom;
  const w = iw*s, h = ih*s;
  const x = photoFit === 'contain' ? (CW-w)/2 : (CW-w)*photoOffX;
  const y = photoFit === 'contain' ? (CH-h)/2 : (CH-h)*photoOffY;
  return { x, y, w, h };
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
  if(!(raw > 0)) return base;
  return base * (PRESSURE_MIN + (1 - PRESSURE_MIN) * Math.min(1, raw));
}
let reposActive=false, reposStart=null;
pad.addEventListener('contextmenu', e=>e.preventDefault());
pad.addEventListener('pointerdown', e=>{ if(playing) return; if(pinching) return; e.preventDefault(); disarmAll();
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
  try{ pad.setPointerCapture(e.pointerId); }catch(_){ }
  drawing=true; curCount=1; redoStack.length=0; noteAction('stroke');
  const p=pos(e); smoothPt={x:p.x,y:p.y}; lastRaw={x:p.x,y:p.y};
  const dsize = sizeFor(e, erasing ? size*3 : size); const pcol = erasing ? color : penColorFor(color);
  frame().strokes.push({ x:p.x, y:p.y, color: pcol, size: dsize, t: performance.now(), erase: erasing, start: true });
  render(); });
pad.addEventListener('pointermove', e=>{
  if(pinching){ return; }
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
  else { smoothPt={x: smoothPt.x+(raw.x-smoothPt.x)*smoothingAlpha, y: smoothPt.y+(raw.y-smoothPt.y)*smoothingAlpha}; px=smoothPt.x; py=smoothPt.y; }
  curCount++; const dsize = sizeFor(e, erasing ? size*3 : size); const pcol = erasing ? color : penColorFor(color);
  frame().strokes.push({ x:px, y:py, color: pcol, size: dsize, t: performance.now(), erase: erasing });
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
    const _pts=frame().strokes, _last=_pts.length ? _pts[_pts.length-1] : null;
    const dsize=(_last && typeof _last.size==='number') ? _last.size : size, pcol=penColorFor(color);
    for(let k=0;k<6;k++){ smoothPt={x: smoothPt.x+(lastRaw.x-smoothPt.x)*0.5, y: smoothPt.y+(lastRaw.y-smoothPt.y)*0.5};
      curCount++; frame().strokes.push({ x:smoothPt.x, y:smoothPt.y, color:pcol, size:dsize, t:performance.now(), erase:false }); }
    render();
  }
  drawing=false; smoothPt=null; lastRaw=null;
  frame().strokeGroups.push(curCount); curCount=0;
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

/* Custom canvas cursors (pad-style). Eraser = a ring at the 3x footprint; pen = a
   ring at the brush footprint with a little crosshair. One handler swaps them; both
   hide while playing or while the eyedropper is active (which uses the OS crosshair). */
const eraserCursor = document.createElement('div');
eraserCursor.className = 'flip-eraser-cursor';
document.querySelector('.flip-wrap').appendChild(eraserCursor);
const brushCursor = document.createElement('div');
brushCursor.className = 'flip-brush-cursor';
document.querySelector('.flip-wrap').appendChild(brushCursor);
function moveEraserCursor(e){
  const r = pad.getBoundingClientRect();
  const scale = r.width / CW;
  const sz = size * 3 * scale;
  eraserCursor.style.width = sz + 'px'; eraserCursor.style.height = sz + 'px';
  eraserCursor.style.left = (e.clientX - r.left) + 'px';
  eraserCursor.style.top  = (e.clientY - r.top) + 'px';
  eraserCursor.style.display = 'block';
}
function moveBrushCursor(e){
  const r = pad.getBoundingClientRect();
  const scale = r.width / CW;
  const sz = Math.max(2, size * scale);
  brushCursor.style.width = sz + 'px'; brushCursor.style.height = sz + 'px';
  brushCursor.style.left = (e.clientX - r.left) + 'px';
  brushCursor.style.top  = (e.clientY - r.top) + 'px';
  brushCursor.style.display = 'block';
}
function hideCursors(){ eraserCursor.style.display='none'; brushCursor.style.display='none'; }
pad.addEventListener('pointermove', e=>{
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
  const s=frame().strokes; if(curCount>0 && s.length>=curCount) s.splice(s.length-curCount, curCount);
  drawing=false; curCount=0; smoothPt=null; lastRaw=null; render();
}
function _touchDist(a,b){ return Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY); }
function _touchMid(a,b){ const r=document.querySelector('.flip-wrap').getBoundingClientRect();
  return { x:(a.clientX+b.clientX)/2 - r.left, y:(a.clientY+b.clientY)/2 - r.top }; }
function beginPinch(e){
  if(playing || reposMode || !ZoomView) return;
  if(ZoomView.enabled && !ZoomView.enabled()) ZoomView.enable();   // pinch turns the magnifier on
  if(!e.touches || e.touches.length<2) return;
  if(e.cancelable) e.preventDefault();
  abortStrokeForPinch(); pinching=true;
  const t0=e.touches[0], t1=e.touches[1];
  _pinch={ lastDist:_touchDist(t0,t1), lastMid:_touchMid(t0,t1) };
}
function _pinchMove(e){
  if(!pinching || !_pinch || !ZoomView) return;
  if(!e.touches || e.touches.length<2) return;
  if(e.cancelable) e.preventDefault();
  const t0=e.touches[0], t1=e.touches[1];
  const dist=_touchDist(t0,t1), mid=_touchMid(t0,t1);
  if(_pinch.lastDist>0) ZoomView.zoomAt(dist/_pinch.lastDist, mid.x, mid.y);
  ZoomView.panBy(mid.x-_pinch.lastMid.x, mid.y-_pinch.lastMid.y);
  _pinch.lastDist=dist; _pinch.lastMid=mid;
}
function _pinchEnd(e){ if(!pinching) return; if(e.touches && e.touches.length>=2) return; pinching=false; _pinch=null; }
pad.addEventListener('touchstart', e=>{ if(e.touches && e.touches.length>=2) beginPinch(e); }, {passive:false});
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
  function ptr(ev){ const t=ev.touches?ev.touches[0]:ev; return {x:t.clientX,y:t.clientY}; }
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
  function typingTarget(el){ return el && (el.tagName==='INPUT'||el.tagName==='TEXTAREA'||el.isContentEditable); }
  window.addEventListener('keydown',(e)=>{ if(e.code==='Space' && !typingTarget(e.target)){ spaceHeld=true; if(zoom>1){ e.preventDefault(); flipWrap.style.cursor=spaceDragging?'grabbing':'grab'; } } });
  window.addEventListener('keyup',(e)=>{ if(e.code==='Space'){ spaceHeld=false; spaceDragging=false; flipWrap.style.cursor=''; } });
  flipWrap.addEventListener('mousedown',(e)=>{ if(spaceHeld && zoom>1){ spaceDragging=true; lastX=e.clientX; lastY=e.clientY; flipWrap.style.cursor='grabbing'; e.preventDefault(); e.stopPropagation(); } }, true);
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
if(pbLeft) pbLeft.addEventListener('click',()=>{ if(!pbLeft.disabled) movePage(idx,-1); });
if(pbRight) pbRight.addEventListener('click',()=>{ if(!pbRight.disabled) movePage(idx,1); });
if(pbCopy) pbCopy.addEventListener('click',()=>{ if(pbCopy.disabled) return;
  pageClip=deepCopy(frames[idx]); buildStrip(); chip('Page copied — use ＋ Paste'); });
if(pbHold) pbHold.addEventListener('click',()=>{ if(pbHold.disabled) return;
  invalidateClearUndo(); frames[idx].hold=(frameHold(frames[idx]) % MAX_HOLD)+1;
  buildStrip(); scheduleSave(); });
if(pbDel) pbDel.addEventListener('click',()=>{ if(!pbDel.disabled) delFrame(idx); });

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
      if(playing || frames.length<2) return;
      if(ev.target.closest('.del')) return;
      _pdrag={ i:i, el:el, startX:ev.clientX, lastX:ev.clientX, moved:false, centers:stripTileCenters() };
    });
    el.addEventListener('click',ev=>{
      if(playing) return;
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
  col.innerHTML='<button class="addbtn" id="addcopy" title="Add a page that copies this one, so you can nudge and redraw">＋ Page</button>'
    +'<button class="addbtn mini" id="addblank" title="Add an empty page">＋ Blank</button>'
    + (pageClip ? '<button class="addbtn mini" id="addpaste">＋ Paste</button>' : '');
  strip.appendChild(col);
  col.querySelector('#addcopy').addEventListener('click',()=>{ if(!playing) addFrame(true); });
  col.querySelector('#addblank').addEventListener('click',()=>{ if(!playing) addFrame(false); });
  syncPagebar();
  syncFlipDuration();
  const pasteBtn=col.querySelector('#addpaste');
  if(pasteBtn) pasteBtn.addEventListener('click',()=>{
    if(playing || !pageClip) return;
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
function deepCopy(f){ return { strokes: f.strokes.map(p=>Object.assign({},p)), strokeGroups: f.strokeGroups.slice(), hold: frameHold(f) }; }
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
function addFrame(copy){ disarmAll(); invalidateClearUndo(); redoStack.length=0; const f=copy?deepCopy(frame()):newFrame(); frames.splice(idx+1,0,f); idx++; buildStrip(); render(); scheduleSave();
  scrollStripToActive(true); }
function delFrame(i){ invalidateClearUndo(); redoStack.length=0; if(frames.length===1){ frames[0]=newFrame(); idx=0; }
  else { frames.splice(i,1); if(idx>=frames.length) idx=frames.length-1; else if(i<idx) idx--; }
  buildStrip(); render(); scheduleSave(); scrollStripToActive(true); }
function go(i){ idx=i; redoStack.length=0; buildStrip(); render(); }

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
  color=hex;
  colorCurrent.style.background=hex;
  // !! is load-bearing. The custom swatch has no data-color, so this expression
  // was `undefined && ...` -> undefined, and classList.toggle(name, undefined)
  // is treated as NO second argument — which TOGGLES instead of forcing off. So
  // every colour change flipped the custom swatch's highlight, leaving two
  // swatches ringed at once and the wrong one appearing selected.
  [...colorGroup.querySelectorAll('.color-dot')].forEach(d=>d.classList.toggle('active',
    !!(d.dataset.color && d.dataset.color.toLowerCase()===hex.toLowerCase())));
  setTool('pen');   // picking a colour returns you to the pen, like the Pad
}
/* Pen / eraser toggle — the Pad's segmented control with the sliding accent pill. */
function positionToolSlider(){
  const pen=document.getElementById('penToolBtn'), er=document.getElementById('eraserToolBtn'), sl=document.getElementById('toolSlider');
  if(!pen||!er||!sl) return; const active = erasing ? er : pen;
  sl.style.width = active.offsetWidth+'px';
  sl.style.transform = erasing ? 'translateX('+pen.offsetWidth+'px)' : 'translateX(0)';
}
function setTool(t){
  erasing = (t === 'eraser');
  const pen=document.getElementById('penToolBtn'), er=document.getElementById('eraserToolBtn');
  if(pen&&er){ pen.classList.toggle('active', !erasing); er.classList.toggle('active', erasing); }
  positionToolSlider();
  pad.style.cursor='none';
  if(typeof eraserCursor!=='undefined' && !erasing) eraserCursor.style.display='none';
  if(typeof brushCursor!=='undefined' && erasing) brushCursor.style.display='none';
  if(picking) setPicking(false);
}
function addRecent(hex){
  recentColors=[hex, ...recentColors.filter(c=>c.toLowerCase()!==hex.toLowerCase())].slice(0,6);
  try{ localStorage.setItem('skribl_recent_colors', JSON.stringify(recentColors)); }catch(_){ }
  renderRecent();
}
function renderRecent(){
  recentColorsEl.innerHTML='';
  recentColors.forEach(hex=>{ const b=document.createElement('button'); b.type='button'; b.className='recent-swatch'; b.style.background=hex;
    b.title=hex; b.addEventListener('click',()=>{ setColor(hex); closePop(); }); recentColorsEl.appendChild(b); });
  recentRow.hidden = recentColors.length===0;
}
// preset dots — inserted before the static custom picker + eyedropper (Pad order)
COLORS.forEach(col=>{ const b=document.createElement('button'); b.type='button'; b.className='color-dot'; b.style.background=col; b.dataset.color=col;
  if(col==='#000000') b.style.borderColor='#3a4150';
  b.setAttribute('aria-label', col);
  b.addEventListener('click',()=>{ setColor(col); closePop(); }); colorGroup.insertBefore(b, customWrap); });
// custom color picker (static markup)
customInput.addEventListener('input',e=>{ customBtn.style.background=e.target.value; setColor(e.target.value); });
customInput.addEventListener('change',e=>{ addRecent(e.target.value); });

// eyedropper — click to arm, then click the canvas to sample a pixel's colour
function setPicking(v){ picking=v; eyedropperBtn.classList.toggle('picking',picking); pad.style.cursor = picking ? 'crosshair' : 'none';
  if(picking) hideCursors(); }
function sampleColorAt(e){
  try{
    const p=pos(e); const dx=Math.round(p.x*DPR), dy=Math.round(p.y*DPR);
    const d=ctx.getImageData(dx,dy,1,1).data;
    const hex = d[3] < 10 ? bgColor
      : '#'+[d[0],d[1],d[2]].map(v=>v.toString(16).padStart(2,'0')).join('');
    setColor(hex); addRecent(hex);
  }catch(_){ }
  setPicking(false); closePop();
}
eyedropperBtn.addEventListener('click',e=>{ e.stopPropagation(); setPicking(!picking); });

const photoPanel=document.getElementById('photoPanel'), musicPanel=document.getElementById('musicPanel');
const imageBtn=document.getElementById('imageBtn'), musicBtn=document.getElementById('musicBtn');
function hidePhoto(){ photoPanel.hidden=true; imageBtn.classList.remove('open'); imageBtn.setAttribute('aria-expanded','false'); refitDrawer(); }
function hideMusic(){ musicPanel.hidden=true; musicBtn.classList.remove('open'); musicBtn.setAttribute('aria-expanded','false'); refitDrawer(); }
function closeMediaDrawers(){ hidePhoto(); hideMusic(); }
function refitDrawer(){
  const open = !drawPanel.hidden ? drawPanel : (!photoPanel.hidden ? photoPanel : (!musicPanel.hidden ? musicPanel : null));
  if(!open) return;
  // block:'end', not 'nearest'. 'nearest' scrolls the MINIMUM amount, so a
  // drawer that is already partly on screen gets no scroll at all — which on a
  // phone left the colour swatches and the eyedropper permanently sliced by the
  // bottom edge, under Safari's toolbar. 'end' brings the drawer's bottom to
  // the viewport bottom, and the safe-area padding on .flip-drawers keeps it
  // clear of the browser chrome once it gets there.
  requestAnimationFrame(()=>{ try{ open.scrollIntoView({behavior:'smooth', block:'end'}); }catch(_){ open.scrollIntoView(); }
    if(currentAudioBuffer && open===musicPanel) requestZoomWaveformDraw(); });
}
function openPop(){ closeMediaDrawers(); drawPanel.hidden=false; colorCurrent.setAttribute('aria-expanded','true'); refitDrawer(); requestAnimationFrame(positionSmoothSeg); }
function closePop(){ drawPanel.hidden=true; colorCurrent.setAttribute('aria-expanded','false'); if(picking) setPicking(false); refitDrawer(); }
function openPhoto(){ closePop(); hideMusic(); photoPanel.hidden=false; imageBtn.classList.add('open'); imageBtn.setAttribute('aria-expanded','true'); syncMediaUI(); refitDrawer(); requestAnimationFrame(positionFitSlider); }
function openMusic(){ closePop(); hidePhoto(); musicPanel.hidden=false; musicBtn.classList.add('open'); musicBtn.setAttribute('aria-expanded','true'); syncMediaUI(); refitDrawer(); }
colorCurrent.addEventListener('click',e=>{ e.stopPropagation(); (drawPanel.hidden?openPop:closePop)(); });
imageBtn.addEventListener('click',e=>{ e.stopPropagation(); (photoPanel.hidden?openPhoto:hidePhoto)(); });
musicBtn.addEventListener('click',e=>{ e.stopPropagation(); (musicPanel.hidden?openMusic:hideMusic)(); });
document.addEventListener('click',e=>{ const t=e.target;
  if(!drawPanel.hidden  && !t.closest('#drawPanel')  && !t.closest('#colorCurrent')) closePop();
  if(!photoPanel.hidden && !t.closest('#photoPanel') && !t.closest('#imageBtn')) hidePhoto();
  if(!musicPanel.hidden && !t.closest('#musicPanel') && !t.closest('#musicBtn')) hideMusic();
});
renderRecent(); setColor(color);
const sizeEl=document.getElementById('size'), sizeVal=document.getElementById('sizeVal'), brushDot=document.getElementById('brushSizeDot');
function sizeFill(){ const min=+sizeEl.min,max=+sizeEl.max; sizeEl.style.setProperty('--slider-fill', ((sizeEl.value-min)/(max-min)*100)+'%');
  sizeVal.textContent=sizeEl.value+'px';
  const d=Math.min(+sizeEl.value,26); if(brushDot){ brushDot.style.width=d+'px'; brushDot.style.height=d+'px'; } }
sizeEl.addEventListener('input',()=>{ size=+sizeEl.value; sizeFill(); });

/* ---- opacity: rides inside the per-stroke color as rgba() (Pad parity) ---- */
function penColorFor(hex){
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
function positionSmoothSeg(){ const active=smoothSeg.querySelector('.smooth-btn.active'), pill=smoothSeg.querySelector('.seg-slider');
  if(!active||!pill) return; pill.style.width=active.offsetWidth+'px'; pill.style.transform='translateX('+(active.offsetLeft-3)+'px)'; pill.style.opacity=1; }
smoothSeg.addEventListener('click',e=>{ const b=e.target.closest('.smooth-btn'); if(!b) return;
  const lvl=b.dataset.smooth; smoothingAlpha = lvl==='high' ? 0.25 : lvl==='low' ? 0.5 : 1;
  smoothSeg.querySelectorAll('.smooth-btn').forEach(x=>x.classList.toggle('active', x===b)); positionSmoothSeg(); });

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
function loadBgImageObj(cb){ if(!bgImage){ bgImageObj=null; if(cb)cb(); return; } const im=new Image(); im.onload=()=>{ bgImageObj=im; if(cb)cb(); }; im.onerror=()=>{ bgImageObj=null; if(cb)cb(); }; im.src=bgImage; }
function redrawAll(){ render(); refreshAllThumbs(); }
function setBgImage(dataURL){ bgImage=dataURL; photoEnabled=true; photoFit='cover'; photoOpacity=1; photoBlur=0; photoZoom=1; photoOffX=0.5; photoOffY=0.5; reposMode=false;
  // Re-adding a file the autosave had to drop — restore its saved framing rather
  // than the defaults above. (Keeps the newly picked filename, not the old one.)
  if(pendingPhotoMeta){ const m=pendingPhotoMeta;
    if(m.fit) photoFit=m.fit;
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
  if(!musicData){ currentAudioBuffer=null; return; }
  try{ if(!audioCtx) audioCtx = new (window.AudioContext||window.webkitAudioContext)(); }catch(_){ return; }
  try{
    mediaToArrayBuffer(musicData).then(ab => audioCtx.decodeAudioData(ab)).then(buf=>{
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
    }).catch(()=>{});
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
function startMusic(){ if(!musicEnabled || musicMuted) return;
  if(startWebAudioLoop()) return;                               // gapless path
  ensureAudio(); if(audioEl){ try{ audioEl.currentTime=trimStart; audioEl.play().catch(()=>{}); }catch(_){}} }
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
function stopWebAudioLoop(){ if(_waLoopSource){ try{_waLoopSource.stop();}catch(e){} try{_waLoopSource.disconnect();}catch(e){} _waLoopSource=null; } }
function startWebAudioLoop(){
  if(!audioCtx || !currentAudioBuffer) return false;
  const buf=buildLoopAudioBuffer(); if(!buf) return false;
  stopWebAudioLoop();
  if(audioCtx.state==='suspended'){ try{ audioCtx.resume(); }catch(e){} }
  const src=audioCtx.createBufferSource(); src.buffer=buf; src.loop=true; src.loopStart=0; src.loopEnd=buf.duration;
  src.connect(audioCtx.destination);
  try{ src.start(); }catch(e){ return false; }
  _waLoopSource=src; _waLoopStartCtx=audioCtx.currentTime; _waLoopDuration=buf.duration; return true;
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
      if(audioEl){ try{audioEl.pause();}catch(_){}} audioEl=null; musicMuted=false;
      const ok=applyPayload(d);            // sets frames/bgColor/bgImage/musicData/fps directly
      invalidateClearUndo();
      loadBgImageObj(()=>{ applyBg(); render(); });
      ensureAudio();
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
  if (music0 && music0.data && currentAudioBuffer) {
    try {
      const cropped = buildTrimmedLoopWav();
      if (cropped) music0 = { data: cropped.dataUrl, name: music0.name, trimStart: 0, trimEnd: cropped.duration };
    } catch (e) { /* keep the full-sample music0 */ }
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
    const res=await fetch(window.SKRIBL_API_BASE,{ method:'POST', headers:skriblPostHeaders(), body:JSON.stringify(buildSharePayload()) });
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
    const MM=window.Mp4Muxer;
    if(!(MM && MM.Muxer && MM.ArrayBufferTarget)) return 'WebM';
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
  [...photoFitGroup.querySelectorAll('.photo-fit-btn')].forEach(b=>b.classList.toggle('active', b.dataset.fit===photoFit));
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
  if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimEnd=trimStart+MAX_LOOP_SECONDS;
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
  const rect=musicTrack.getBoundingClientRect(); waveformCanvas.width=rect.width; waveformCanvas.height=rect.height;
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
  function cx(e){ return e.touches?e.touches[0].clientX:e.clientX; }
  function onStart(e){ e.preventDefault(); handle.classList.add('dragging');
    function onMove(ev){ const rect=musicTrack.getBoundingClientRect(); let pct=(cx(ev)-rect.left)/rect.width; pct=Math.max(0,Math.min(1,pct)); const time=pct*audioDuration;
      if(isStart){ trimStart=Math.min(time,trimEnd-0.5); trimStart=Math.max(0,trimStart); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimStart=trimEnd-MAX_LOOP_SECONDS; }
      else { trimEnd=Math.max(time,trimStart+0.5); trimEnd=Math.min(audioDuration,trimEnd); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimEnd=trimStart+MAX_LOOP_SECONDS; }
      updateTrimUI(); scheduleSave(); }
    function onEnd(){ handle.classList.remove('dragging'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd);
  }
  handle.addEventListener('mousedown',onStart); handle.addEventListener('touchstart',onStart,{passive:false});
}
dragHandle(handleStart,true); dragHandle(handleEnd,false);
function dragRangeWindow(rangeEl){
  function cx(e){ return e.touches?e.touches[0].clientX:e.clientX; }
  function onStart(e){ if(!audioEl||!(audioDuration>0)) return; if(rangeEl.classList.contains('narrow')) return; e.preventDefault(); e.stopPropagation(); rangeEl.classList.add('dragging');
    const rect=musicTrack.getBoundingClientRect(); const loopLength=trimEnd-trimStart; const grabTime=(cx(e)-rect.left)/rect.width*audioDuration; const grabOffset=grabTime-trimStart;
    function onMove(ev){ const time=(cx(ev)-rect.left)/rect.width*audioDuration; let ns=time-grabOffset; ns=Math.max(0,Math.min(ns,audioDuration-loopLength)); trimStart=ns; trimEnd=ns+loopLength; updateTrimUI(); }
    function onEnd(){ rangeEl.classList.remove('dragging'); scheduleSave(); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd);
  }
  rangeEl.addEventListener('mousedown',onStart); rangeEl.addEventListener('touchstart',onStart,{passive:false});
}
dragRangeWindow(musicRange);
function dragZoomHandle(handle, isStart){
  function onStart(e){ e.preventDefault(); handle.classList.add('dragging');
    function onMove(ev){ const clientX=ev.touches?ev.touches[0].clientX:ev.clientX; const rect=zoomTrackWrap.getBoundingClientRect(); const pct=Math.max(0,Math.min(1,(clientX-rect.left)/rect.width)); const zw=getZoomWindow(); const time=zw.start+pct*(zw.end-zw.start);
      if(isStart){ trimStart=Math.max(0,Math.min(time,trimEnd-0.5)); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimEnd=trimStart+MAX_LOOP_SECONDS; }
      else { trimEnd=Math.min(audioDuration,Math.max(time,trimStart+0.5)); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimStart=trimEnd-MAX_LOOP_SECONDS; }
      updateTrimUI(); scheduleSave(); }
    function onEnd(){ handle.classList.remove('dragging'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd);
  }
  handle.addEventListener('mousedown',onStart); handle.addEventListener('touchstart',onStart,{passive:false});
}
dragZoomHandle(zoomHandleStart,true); dragZoomHandle(zoomHandleEnd,false);

// seg-slider pill for the zoom mag/focus groups
function positionSegSlider(group){ if(!group) return; const pill=group.__segPill; if(!pill) return; const btns=[].slice.call(group.querySelectorAll('button')); let idx=-1; for(let i=0;i<btns.length;i++){ if(btns[i].classList.contains('active')) idx=i; } const a=idx>=0?btns[idx]:null; if(!a||!a.offsetWidth){ pill.style.opacity='0'; return; } const off=a.offsetLeft-btns[0].offsetLeft; pill.style.width=a.offsetWidth+'px'; pill.style.transform='translateX('+off+'px)'; pill.style.opacity='1'; }
function attachSegSlider(group){ if(!group||group.__segAttached) return; group.__segAttached=true; const pill=document.createElement('div'); pill.className='seg-slider'; group.insertBefore(pill, group.firstChild); group.__segPill=pill; const reflow=()=>positionSegSlider(group); if(typeof MutationObserver!=='undefined'){ new MutationObserver(reflow).observe(group,{subtree:true,attributes:true,attributeFilter:['class']}); } if(typeof ResizeObserver!=='undefined'){ new ResizeObserver(reflow).observe(group); } else if(window.addEventListener){ window.addEventListener('resize',reflow); } reflow(); }
(function initZoomMagControl(){ if(!zoomTrackWrap||!zoomTrackWrap.parentNode) return;
  const bar=document.createElement('div'); bar.className='zoom-mag-bar';
  bar.innerHTML='<div class="zoom-mag-group" data-role="focus"><button type="button" class="zoom-mag-btn active" data-focus="loop">Loop</button><button type="button" class="zoom-mag-btn" data-focus="start">Start</button><button type="button" class="zoom-mag-btn" data-focus="end">End</button></div>'+
    '<div class="zoom-mag-group" data-role="mag"><button type="button" class="zoom-mag-btn active" data-mag="1">1&times;</button><button type="button" class="zoom-mag-btn" data-mag="2">2&times;</button><button type="button" class="zoom-mag-btn" data-mag="4">4&times;</button><button type="button" class="zoom-mag-btn" data-mag="8">8&times;</button></div>';
  zoomTrackWrap.parentNode.insertBefore(bar, zoomTrackWrap);
  attachSegSlider(bar.querySelector('.zoom-mag-group[data-role="focus"]')); attachSegSlider(bar.querySelector('.zoom-mag-group[data-role="mag"]'));
  bar.addEventListener('click',(e)=>{ const b=e.target.closest('.zoom-mag-btn'); if(!b) return; b.parentNode.querySelectorAll('.zoom-mag-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); if(b.dataset.focus){ zoomFocus=b.dataset.focus; zoomCenter=null; } if(b.dataset.mag) zoomMag=parseFloat(b.dataset.mag)||1; updateTrimUI(); });
  const style=document.createElement('style'); style.textContent='.zoom-mag-bar{display:flex;gap:10px;justify-content:space-between;align-items:center;margin:8px 0 6px;flex-wrap:wrap}.zoom-mag-group{position:relative;overflow:hidden;display:inline-flex;gap:2px;background:#13161c;border:1px solid rgba(255,255,255,.055);border-radius:8px;padding:3px}.zoom-mag-btn{position:relative;z-index:1;appearance:none;-webkit-appearance:none;border:0;background:transparent;color:#8a93a6;font:inherit;font-size:12px;line-height:1;padding:5px 9px;border-radius:6px;cursor:pointer;transition:color .12s}.zoom-mag-btn:hover{color:#c8cede}.zoom-mag-btn.active{color:#fff}'; document.head.appendChild(style);
})();
bindEl('fineTuneToggle', 'click',()=>{ const body=document.getElementById('fineTuneBody'); const t=document.getElementById('fineTuneToggle'); const open=body.hidden; body.hidden=!open; t.setAttribute('aria-expanded', open?'true':'false'); if(open){ requestAnimationFrame(()=>{ updateTrimUI(); document.querySelectorAll('.zoom-mag-group').forEach(g=>positionSegSlider(g)); }); } });

// nudge fine-tune
const nudgeSteps=[0.01,0.02,0.05,0.1]; let nudgeStepIdx=3;
function updateNudgeStepLabel(){ nudgeStepLabel.textContent=nudgeSteps[nudgeStepIdx]+'s'; nudgeStepFinerBtn.disabled=nudgeStepIdx===0; nudgeStepCoarserBtn.disabled=nudgeStepIdx===nudgeSteps.length-1; }
nudgeStepFinerBtn.addEventListener('click',()=>{ nudgeStepIdx=Math.max(0,nudgeStepIdx-1); updateNudgeStepLabel(); });
nudgeStepCoarserBtn.addEventListener('click',()=>{ nudgeStepIdx=Math.min(nudgeSteps.length-1,nudgeStepIdx+1); updateNudgeStepLabel(); });
function nudgeTrim(which, direction){ if(!audioEl) return; if((which!=='start'&&which!=='end')||!Number.isFinite(direction)) return; const amount=direction*nudgeSteps[nudgeStepIdx];
  if(which==='start'){ trimStart=Math.max(0,Math.min(trimStart+amount,trimEnd-0.5)); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimEnd=trimStart+MAX_LOOP_SECONDS; } else { trimEnd=Math.min(audioDuration,Math.max(trimEnd+amount,trimStart+0.5)); if(trimEnd-trimStart>MAX_LOOP_SECONDS) trimStart=trimEnd-MAX_LOOP_SECONDS; } updateTrimUI(); scheduleSave(); }
document.querySelectorAll('.nudge-btn[data-which]').forEach(btn=>{ btn.addEventListener('click',()=>nudgeTrim(btn.dataset.which, parseFloat(btn.dataset.amount))); });
updateNudgeStepLabel();

// Match Drawing Time — set loop length to the animation runtime
function setLoopToDrawingLength(){ if(!audioEl || !(audioDuration>0)) return; const drawingSeconds=frames.length/fps; const loopLength=Math.min(MAX_LOOP_SECONDS,Math.max(0.5,Math.min(drawingSeconds,audioDuration))); trimEnd=trimStart+loopLength; if(trimEnd>audioDuration){ trimEnd=audioDuration; trimStart=Math.max(0,trimEnd-loopLength); } updateTrimUI(); scheduleSave(); }
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
function startLoopPreview(){
  previewingLoop=true; previewLoopBtn.textContent='Stop Preview';
  if(startWebAudioLoop()){ _previewWA=true; }                                  // gapless, real crossfade
  else { _previewWA=false; ensureAudio(); if(!audioEl){ stopLoopPreview(); return; } try{ audioEl.muted=false; audioEl.currentTime=trimStart; audioEl.play().catch(()=>{}); }catch(_){} }
  previewLoopTimer=setInterval(previewTick,30);
}
previewLoopBtn.addEventListener('click',()=>{ if(previewingLoop) stopLoopPreview(); else startLoopPreview(); });
testSeamBtn.addEventListener('click',()=>{ stopLoopPreview(); previewingLoop=true; previewLoopBtn.textContent='Stop Preview';
  // The gapless engine already loops seamlessly; play ~2 loops so you can hear the wrap (and the crossfade, if set).
  if(startWebAudioLoop()){ _previewWA=true; previewLoopTimer=setInterval(previewTick,30);
    seamStopTimer=setTimeout(stopLoopPreview, Math.min((trimEnd-trimStart)*2+0.4, 12)*1000); return; }
  _previewWA=false; ensureAudio(); if(!audioEl){ stopLoopPreview(); return; }
  const seamStart=Math.max(trimStart, trimEnd-1.25); try{ audioEl.muted=false; audioEl.currentTime=seamStart; audioEl.play().catch(()=>{}); }catch(_){} previewLoopTimer=setInterval(previewTick,30);
  const runFor=(trimEnd-seamStart)+Math.min(1.25, trimEnd-trimStart)+0.4; seamStopTimer=setTimeout(stopLoopPreview, runFor*1000); });

// Loop Detail scroll + crossfade (injected, like the Pad)
function updateZoomPanSlider(){ const s=document.getElementById('zoomPanSlider'); if(!s) return; if(!(audioDuration>0)){ s.value=500; return; } const zw=getZoomWindow(); const c=(zw.start+zw.end)/2; s.value=Math.round(Math.max(0,Math.min(1,c/audioDuration))*1000); updateSliderFill(s); }
function dragZoomPan(wrap){ if(!wrap) return; const cx=(e)=>(e.touches?e.touches[0].clientX:e.clientX);
  function onStart(e){ if(!audioEl||!(audioDuration>0)) return; if(e.target.closest('.zoom-handle')) return; e.preventDefault(); const rect=wrap.getBoundingClientRect(); const zw=getZoomWindow(); const sc=(zw.start+zw.end)/2; const winDur=zw.duration; const sx=cx(e); wrap.classList.add('panning');
    function onMove(ev){ const dx=cx(ev)-sx; const dt=-(dx/rect.width)*winDur; const half=winDur/2; const lo=half, hi=Math.max(half,audioDuration-half); zoomCenter=Math.max(lo,Math.min(sc+dt,hi)); zoomFocus='free'; syncZoomFocusButtons(); updateTrimUI(); }
    function onEnd(){ wrap.classList.remove('panning'); window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onEnd); window.removeEventListener('touchmove',onMove); window.removeEventListener('touchend',onEnd); }
    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onEnd); window.addEventListener('touchmove',onMove,{passive:false}); window.addEventListener('touchend',onEnd); }
  wrap.addEventListener('mousedown',onStart); wrap.addEventListener('touchstart',onStart,{passive:false});
}
function addSliderNudgers(el, opts){ opts=opts||{}; const wrap=document.createElement('span'); wrap.className='slider-nudge-wrap'; el.parentNode.insertBefore(wrap, el); wrap.appendChild(el);
  const mk=(txt,dir)=>{ const b=document.createElement('button'); b.type='button'; b.className='slider-nudge-btn'; b.textContent=txt; b.addEventListener('click',()=>{ if(opts.nudgeFn){ opts.nudgeFn(dir); } else { const step=opts.step||1; el.value=(+el.value)+dir*step; el.dispatchEvent(new Event('input',{bubbles:true})); } }); return b; };
  wrap.insertBefore(mk('\u2212',-1), el); wrap.appendChild(mk('+',1)); }
function setCrossfadeUI(){ const s=document.getElementById('crossfadeSlider'), v=document.getElementById('crossfadeVal'); if(s){ s.value=loopCrossfadeMs; updateSliderFill(s); } if(v) v.textContent=loopCrossfadeMs>0?(loopCrossfadeMs+' ms'):'Off'; }
(function initSliderExtras(){
  const style=document.createElement('style'); style.textContent='.slider-nudge-wrap{display:flex;align-items:center;gap:6px;flex:1;min-width:0}.slider-nudge-wrap input[type=range]{flex:1;min-width:0}.slider-nudge-btn{flex:none;width:26px;height:26px;padding:0;border:0;border-radius:7px;background:#232734;color:#c8cede;font-size:16px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;user-select:none;transition:background .12s}.slider-nudge-btn:hover{background:#2c3140}.slider-nudge-btn:active{background:#7c5cff;color:#fff}.zoom-pan-row,.crossfade-row{display:flex;align-items:center;gap:10px;margin:8px 0 2px}.zoom-pan-label,.crossfade-label{font-size:12px;color:#8a93a6;flex:none;min-width:64px}.crossfade-val{font-size:12px;color:#c8cede;flex:none;min-width:38px;text-align:right}#zoomTrackWrap{cursor:grab}#zoomTrackWrap.panning{cursor:grabbing}'; document.head.appendChild(style);
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
function closeMenu(){ moreMenu.hidden=true; if(moreScrim) moreScrim.hidden=true; moreBtn.classList.remove('on'); moreBtn.setAttribute('aria-expanded','false'); }
moreBtn.addEventListener('click',e=>{ e.stopPropagation(); (moreMenu.hidden?openMenu:closeMenu)(); });
document.addEventListener('click',e=>{ if(!moreMenu.hidden && !e.target.closest('#moreMenu') && !e.target.closest('#moreBtn')) closeMenu(); });
// Escape closes it too. Every other dismissible surface here already does this
// — the export sheet, the tune panel, the help drawer, and Pad's own menu — so
// this menu was the only one that trapped you. It mattered less before it had
// a scrim; now a full-screen dim with no keyboard exit is a dead end.
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
  const gifReady=(typeof window.gifenc!=='undefined' && window.gifenc.GIFEncoder);
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
    translateFrames(m.idxs, -m.dx, -m.dy);
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
  const f = frame(); const item = redoStack.pop();
  for(const p of item.pts) f.strokes.push(p);
  f.strokeGroups.push(item.count);
  render(); refreshThumb(idx); updateToolState(); scheduleSave();
}
document.querySelectorAll('#toolGroup .tool-btn').forEach(b=>b.addEventListener('click',()=>{ if(!playing) setTool(b.dataset.tool); }));
/* ---- move-artwork mode ----------------------------------------------------
 * Enter from the page bar, drag on the canvas, Done commits.
 *
 * The offset is applied to a WORKING COPY of the original points, not
 * accumulated onto the live ones: accumulating would round-trip the
 * coordinates on every pointer event and drift the drawing a fraction at a
 * time over a long drag. Reset is then simply "offset zero".
 */
let moveMode = false, moveScope = 'one', moveDx = 0, moveDy = 0;
let moveOrigin = null, moveDragging = false, moveStart = null;

function moveTargets(){
  if(moveScope === 'after'){
    const out = []; for(let i = idx; i < frames.length; i++) out.push(i); return out;
  }
  return [idx];
}
function captureMoveOrigin(){
  moveOrigin = new Map();
  for(const i of moveTargets()) moveOrigin.set(i, frames[i].strokes.map(p => ({x:p.x, y:p.y})));
}
function applyMoveOffset(){
  if(!moveOrigin) return;
  for(const [i, pts] of moveOrigin){
    const f = frames[i]; if(!f) continue;
    for(let k = 0; k < f.strokes.length && k < pts.length; k++){
      f.strokes[k].x = pts[k].x + moveDx;
      f.strokes[k].y = pts[k].y + moveDy;
    }
  }
  const off = document.getElementById('mbOffset');
  if(off) off.textContent = Math.round(moveDx) + ', ' + Math.round(moveDy);
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
    // Re-capture: the set of pages being moved just changed, and the current
    // offset must apply to the new set from their ORIGINAL positions.
    const dx = moveDx, dy = moveDy;
    captureMoveOrigin(); moveDx = dx; moveDy = dy; applyMoveOffset();
  });
})();
// Escape cancels rather than commits. A drag you did not mean is undone by
// leaving, which is what Escape means everywhere else in this app.
document.addEventListener('keydown', e=>{ if(e.key === 'Escape' && moveMode) cancelMove(); });

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
const gridEl=document.getElementById('flipGrid'), gridBtn=document.getElementById('gridBtn');
let grid=false;
gridBtn.addEventListener('click',()=>{ grid=!grid; if(grid) syncGrid(); gridBtn.classList.toggle('on',grid); gridEl.classList.toggle('on',grid); gridBtn.setAttribute('aria-checked',String(grid)); });
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
document.addEventListener('keydown',e=>{ if(e.key==='Escape' && tuneIsOpen()) setTune(false); });

const onionEl=document.getElementById('onion');
const onionGroup=document.getElementById('onionGroup');
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
function _typingEl(el){ return el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName||'') || el.isContentEditable); }
window.addEventListener('keydown', e=>{
  if(_typingEl(e.target)) return;
  if((e.ctrlKey||e.metaKey) && (e.key.toLowerCase()==='y' || (e.shiftKey && e.key.toLowerCase()==='z'))){ e.preventDefault(); redoStroke(); return; }
  if((e.ctrlKey||e.metaKey) && !e.shiftKey && e.key.toLowerCase()==='z'){ e.preventDefault(); undoStroke(); return; }
  // Space = play / stop (when not magnified — Space pans the zoomed canvas instead).
  if((e.code==='Space' || e.key===' ') && !(ZoomView && ZoomView.isZoomed())){ e.preventDefault(); playing?stop():play(); return; }
  if(playing) return;
  if(e.key==='ArrowLeft'  && idx>0){ disarmAll(); go(idx-1); }
  if(e.key==='ArrowRight' && idx<frames.length-1){ disarmAll(); go(idx+1); }
  if(e.key==='p' || e.key==='P'){ setTool('pen'); }
  if(e.key==='e' || e.key==='E'){ setTool('eraser'); }
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
helpClose.addEventListener('click', closeHelpDrawer);
helpBackdrop.addEventListener('click', closeHelpDrawer);
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
window.addEventListener('load', ()=>{ sizeStage(); positionSeg(); positionToolSlider(); });

// Report sheet — shared via lib/report.js so the two editors collect the same
// context. Null-safe: without the lib the menu item simply does nothing.
if (window.SkriblReport) window.SkriblReport.init();

// Styled tooltips. Native `title` cannot be rounded; this swaps them out.
if (window.SkriblTooltip) window.SkriblTooltip.init();
