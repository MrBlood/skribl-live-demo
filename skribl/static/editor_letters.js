/* YOUR HAND: the Pad at /skribl-pad?letters=1, where a person draws their own
 * hand, one letter at a time, and changes it whenever they like (FUTURE.md
 * 6ab; the owner's "All yes" to the letter sheet, then "Yes to all" to every
 * person having their own hand, then "Yes" to the Your hand mock).
 *
 * WHY THE REAL PAD. A letter is drawn on the Pad's own canvas with its own
 * pen, so it is stored the way every Skribl stroke is: each point with its
 * time and its width (pressure is folded into the width). Text will write
 * words in this hand at the speed it was drawn, so a letter has to be a
 * performance, not a picture, and the Pad is what records one.
 *
 * WHAT A PERSON MEETS, in order:
 *   - THE START, for someone with no letters yet: what happens, how long it
 *     takes, Start with a, and Open a copy.
 *   - THE LETTERS, one at a time: the first 30 (a to z and . , ! ?), then,
 *     when they like, the other 62 (capitals, numbers, the other marks, five
 *     accents drawn over their own base letter, and a second try at the nine
 *     commonest letters, so a word with two e's is not stamped). Guide lines
 *     and a faint model under the ink, inside the zoom layer as the grid is.
 *     Next keeps the letter and moves on; Back goes to the one before, with
 *     its letter on the canvas to add to; Redo clears this one, and its toast
 *     can bring it back. Finish later goes to the Pad: every stroke is kept as
 *     it is drawn. Along the bottom, a line writes itself in the letters
 *     drawn so far.
 *   - READY, after the 30: Add the rest, or Done.
 *   - THE TILES (Your hand): every letter, drawn ones in ink and the rest
 *     faint with a +. Tap one to draw it again (the old one faint behind it;
 *     Cancel keeps it, Done keeps the new one) or to add it. Save a copy, Open
 *     a copy, Start over (with Undo) and Post your letters along the bottom.
 *
 * WHERE IT LIVES. On this device, in localStorage (KEY), like a draft; a copy
 * is a file. Words written with it are ink in their drawing, so a viewer never
 * needs the hand.
 *
 * WHAT IT LEAVES ALONE. The Pad's draft (editor_draft.js keeps no draft on
 * this page, as compose keeps none), and the Pad's settings: the sheet draws
 * with the plain pen at one size, unmirrored, by shadowing the brush and
 * mirror for this page's life, never by setting them, which saves them.
 *
 * A CLASSIC SCRIPT, LOADED LAST: it reads the Pad's globals (strokes,
 * strokeGroups, recording, startTime...) and calls its functions
 * (clearCanvas, beginRecording, paintStrokesStatic) as editor_draw.js does.
 */
(function () {
  'use strict';
  if (window.SKRIBL_LETTERS !== true) return;

  var KEY = 'skribl.letters.v1';
  // WHERE THE GUIDES SIT in a letter's box, as fractions of its height. The
  // x-height is 0.70 of the cap height, about where every common sans puts
  // it, so the faint model fits its lines in any face (the mock's 0.44 put the
  // model's x-height far above the line). A stored letter keeps the lines it
  // was drawn to (`l`), so these can change without moving a letter.
  var LINES = { cap: 0.16, x: 0.334, base: 0.74, desc: 0.94 };
  var PEN = { color: '#7c5cff', size: 6 };
  var GAP = 300;     // ms between one letter and the next in the posted set
  var GAIN = 5;      // posted width per drawn width, at the posted scale
  var CELL_W = 1.4;  // a posted letter's cell, in cap heights (its height is the box's)
  var FAM = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  var FILE_TYPE = 'skribl-hand';

  var PANGRAM = 'Sphinx of black quartz, judge my vow.';
  var LINE_FOR = {
    lower: PANGRAM, upper: PANGRAM, quick: PANGRAM,
    digit: '0123456789',
    mark: '. , ! ? \' " - : ; ( ) & @ # / +',
    accent: 'é è ü ñ ç',
    again: 'ee tt aa oo ii nn ss rr hh'
  };
  var NAMES = { '.': 'full stop', ',': 'comma', '!': 'exclamation mark', '?': 'question mark',
    '\'': 'apostrophe', '"': 'quotation mark', '-': 'hyphen', ':': 'colon', ';': 'semicolon',
    '(': 'opening bracket', ')': 'closing bracket', '&': 'ampersand', '@': 'at sign', '#': 'hash',
    '/': 'slash', '+': 'plus', '´': 'acute accent', '`': 'grave accent', '¨': 'diaeresis',
    '~': 'tilde', '¸': 'cedilla' };
  // Skribl's own hello, for the start (the owner's h, e, l and o, simplified).
  var HELLO = {"h":[[[-0.197,0.997,0],[-0.229,0.555,192],[-0.291,0.052,342],[-0.275,0.17,442],[-0.186,0.494,525],[-0.137,0.618,559],[-0.071,0.683,592],[0.046,0.692,658],[0.135,0.639,692],[0.2,0.578,725],[0.251,0.51,759],[0.285,0.421,792],[0.288,0.253,842],[0.205,0.019,892],[0.202,-0.073,942]]],"e":[[[-0.392,0.372,0],[-0.317,0.35,109],[-0.049,0.371,193],[0.156,0.37,259],[0.229,0.356,326],[0.198,0.359,409],[0.145,0.408,459],[-0.018,0.623,559],[-0.083,0.656,592],[-0.163,0.648,626],[-0.275,0.547,659],[-0.317,0.487,676],[-0.373,0.366,710],[-0.389,0.203,759],[-0.345,0.138,793],[-0.201,0.031,843],[-0.078,-0.015,893],[0.094,-0.049,943],[0.176,-0.049,976],[0.222,-0.012,993],[0.272,0.074,1009],[0.392,0.348,1092]]],"l":[[[0.027,1.001,0],[0.017,0.767,93],[-0.025,0.437,160],[-0.019,0.048,243]]],"o":[[[0.126,0.627,0],[0.087,0.677,26],[0.114,0.643,26],[0.087,0.677,26],[0.05,0.692,59],[-0.036,0.701,126],[-0.166,0.602,176],[-0.285,0.458,226],[-0.322,0.364,243],[-0.321,0.259,293],[-0.254,0.182,326],[-0.155,0.121,359],[0.026,0.076,409],[0.182,0.075,443],[0.253,0.128,476],[0.305,0.235,509],[0.322,0.34,543],[0.324,0.544,576],[0.303,0.646,593],[0.257,0.745,626],[0.198,0.786,643],[0.129,0.787,659],[-0.018,0.687,693]]]};

  // ---- The 92 boxes, in the order they are POSTED (harness/tools/letterfont.py
  // reads a posted set by this order; it never changes) ----
  var BOXES = [];
  function addBox(id, ch, kind, model, base) {
    BOXES.push({ id: id, ch: ch, kind: kind, model: model || ch, base: base || null });
  }
  'abcdefghijklmnopqrstuvwxyz'.split('').forEach(function (c) { addBox(c, c, 'lower'); });
  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(function (c) { addBox(c, c, 'upper'); });
  '0123456789'.split('').forEach(function (c) { addBox(c, c, 'digit'); });
  '.,!?\'"-:;()&@#/+'.split('').forEach(function (c) { addBox(c, c, 'mark'); });
  [['´', 'é', 'e'], ['`', 'è', 'e'], ['¨', 'ü', 'u'],
   ['~', 'ñ', 'n'], ['¸', 'ç', 'c']].forEach(function (a) { addBox(a[0], a[0], 'accent', a[1], a[2]); });
  'etaoinsrh'.split('').forEach(function (c) { addBox(c + '2', c, 'again'); });
  var BY_ID = {};
  BOXES.forEach(function (b, i) { BY_ID[b.id] = i; });
  // ...and the order they are DRAWN in: the 30 to start, then the rest.
  var QUICK = 'abcdefghijklmnopqrstuvwxyz'.split('').concat(['.', ',', '!', '?']);
  var ORDER = QUICK.map(function (id) { return BY_ID[id]; });
  BOXES.forEach(function (b, i) { if (QUICK.indexOf(b.id) < 0) ORDER.push(i); });
  var GROUPS = [['Letters', 'abcdefghijklmnopqrstuvwxyz'.split('')], ['Marks', ['.', ',', '!', '?']],
    ['Capitals', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')], ['Numbers', '0123456789'.split('')],
    ['More marks', ['\'', '"', '-', ':', ';', '(', ')', '&', '@', '#', '/', '+']],
    ['Accents', ['´', '`', '¨', '~', '¸']], ['Second tries', 'etaoinsrh'.split('').map(function (c) { return c + '2'; })]];
  // The composed accented letters the accent line shows: base + accent box.
  var COMPOSED = { 'é': ['e', '´'], 'è': ['e', '`'], 'ü': ['u', '¨'],
                   'ñ': ['n', '~'], 'ç': ['c', '¸'] };

  var $ = function (id) { return document.getElementById(id); };
  var topEl = $('ltTop'), footEl = $('ltFoot'), subEl = $('ltSub'), titleEl = $('ltTitle');
  var barEl = $('ltBar'), barFill = $('ltBarFill'), previewEl = $('ltPreview');
  var redoBtnEl = $('ltRedo'), backBtnEl = $('ltBack'), nextBtnEl = $('ltNext'), laterBtnEl = $('ltLater');
  var guidesEl = $('ltGuides');
  if (!topEl || !footEl || !guidesEl || typeof clearCanvas !== 'function') return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  function still() { return !!(reduce && reduce.matches); }

  // ---- The store: every letter, kept as it is drawn ----
  // { v: 1, o: 2, at: the letter on the canvas (a BOXES index), mode: 'seq'
  //   while the letters are being drawn in order or 'tiles' once someone has
  //   the tiles, r: the Ready page has been seen, g: { id: letter } }, a
  //   letter being { p: [[x, y, width, t], ...] in canvas units with t in ms
  //   from its first point, n: points per stroke, b: [x, y, w, h] its box,
  //   l: [cap, x, base, desc] its lines, c: its colour }. A store from before
  //   the order changed (no `o`) is read as it stands and placed again.
  var letterStore = readLetters();
  var storeOk = true;
  function readLetters() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (s && s.v === 1 && s.g && typeof s.g === 'object') {
        if (s.o !== 2) { s.o = 2; s.mode = 'seq'; s.at = null; }
        return s;
      }
    } catch (e) {}
    return { v: 1, o: 2, at: null, mode: 'seq', g: {} };
  }
  function keepLetters() {
    try { localStorage.setItem(KEY, JSON.stringify(letterStore)); storeOk = true; }
    catch (e) {
      // Said once, kindly: the letters on screen are fine, but a reload or
      // Finish later would lose them.
      if (storeOk && typeof showToast === 'function') {
        showToast('This browser isn’t keeping your letters. Save a copy before you leave', topEl);
      }
      storeOk = false;
    }
  }
  function has(id) { return !!letterStore.g[id]; }
  function drawnCount() {
    var n = 0;
    for (var i = 0; i < BOXES.length; i++) if (has(BOXES[i].id)) n++;
    return n;
  }
  function quickDone() { return QUICK.every(has); }
  // The next letter to draw, in drawing order, after `pos` (an ORDER index),
  // then from the start; -1 when every letter is drawn.
  function nextUndrawn(pos) {
    for (var k = 1; k <= ORDER.length; k++) {
      var i = ORDER[(pos + k) % ORDER.length];
      if (!has(BOXES[i].id)) return i;
    }
    return -1;
  }
  function firstUndrawn() { return nextUndrawn(ORDER.length - 1); }

  // ---- The pen: plain, one size, unmirrored, whatever the Pad was set to ----
  // Shadowed on the module objects for this page's life only: setBrush and
  // setMode would SAVE the choice, and the owner's Pad would come back plain.
  if (window.SkriblBrush) {
    var penPreset = SkriblBrush.PRESETS && SkriblBrush.PRESETS.pen;
    SkriblBrush.name = function () { return 'pen'; };
    if (penPreset) SkriblBrush.preset = function () { return penPreset; };
  }
  if (window.SkriblMirror) {
    SkriblMirror.active = function () { return false; };
    SkriblMirror.count = function () { return 0; };
    SkriblMirror.reflect = function () { return []; };
  }
  function setPen() {
    tool = 'pen';
    color = PEN.color;
    size = PEN.size;
    strokeOpacity = 1;
  }

  // ---- What is on screen ----
  // view: 'start' | 'draw' | 'ready' | 'tiles' | 'set'. On 'draw', mode is
  // 'seq' (the letters in order) or 'one' (one letter from the tiles; `old` is
  // the letter it had, kept until Done, and `pending` what has been drawn).
  var view = null, mode = 'seq', at = 0, box = null, lastLen = -1;
  var old = null, pending = null;
  function r2(n) { return Math.round(n * 100) / 100; }
  // The canvas's own box on screen, untransformed: a pinch scales the zoom
  // layer, not the wrap, so this is the drawing's place at fit.
  function canvasScreenBox() {
    var wrap = canvasWrap.getBoundingClientRect();
    var b = parseFloat(getComputedStyle(canvas).borderTopWidth) || 0;
    return { left: wrap.left + canvas.offsetLeft + b, top: wrap.top + canvas.offsetTop + b,
             width: canvas.offsetWidth - 2 * b, height: canvas.offsetHeight - 2 * b };
  }
  function measureBox() {
    var r = canvasScreenBox(), lg = getCanvasLogicalSize();
    if (!r.width || !r.height) return null;
    var sx = lg.width / r.width, sy = lg.height / r.height;
    var top = Math.max(r.top, topEl.getBoundingClientRect().bottom) + 24;
    var bottom = Math.min(r.top + r.height, footEl.getBoundingClientRect().top) - 18;
    var left = r.left + 10, right = r.left + r.width - 10;
    if (bottom - top < 120) { top = r.top + 12; bottom = r.top + r.height - 12; }
    return { x: (left - r.left) * sx, y: (top - r.top) * sy, w: (right - left) * sx, h: (bottom - top) * sy };
  }
  function boxOf(g) { return { x: g.b[0], y: g.b[1], w: g.b[2], h: g.b[3] }; }

  // ---- A letter in and out of the Pad ----
  function packLetter() {
    if (!strokes.length) return null;
    var t0 = strokes[0].t || 0, p = [];
    for (var i = 0; i < strokes.length; i++) {
      var q = strokes[i];
      p.push([r2(q.x), r2(q.y), r2(q.size), Math.max(0, Math.round((q.t || 0) - t0))]);
    }
    return { p: p, n: strokeGroups.slice(), b: [r2(box.x), r2(box.y), r2(box.w), r2(box.h)],
             l: [LINES.cap, LINES.x, LINES.base, LINES.desc], c: strokes[0].color };
  }
  function unpackLetter(g) {
    var out = [], k = 0;
    for (var s = 0; s < g.n.length; s++) {
      for (var j = 0; j < g.n[s]; j++, k++) {
        var q = g.p[k];
        var pt = { x: q[0], y: q[1], color: g.c, size: q[2], t: q[3], erase: false };
        if (j === 0) pt.start = true;
        out.push(pt);
      }
    }
    return out;
  }
  // A stored letter back on the canvas, still recording, so a stroke added
  // to it lands after its last one, not at its start.
  function putLetterBack(g) {
    strokes = unpackLetter(g);
    strokeGroups = g.n.slice();
    hasContent = true;
    paintStrokesStatic(strokes);
    beginRecording(true);
    var last = strokes.length ? strokes[strokes.length - 1].t : 0;
    startTime = Date.now() - (last + 600);
    updateEmptyHint();
  }

  // ---- The guides, the model, and a letter faint behind ----
  var mctx = document.createElement('canvas').getContext('2d');
  var fontM = null;
  function faceMetrics() {
    if (fontM) return fontM;
    mctx.font = '300 100px ' + FAM;
    var H = mctx.measureText('H'), X = mctx.measureText('x');
    fontM = { cap: (H.actualBoundingBoxAscent || 70) / 100, x: (X.actualBoundingBoxAscent || 52) / 100 };
    return fontM;
  }
  function inkSpan(g) {
    var lo = Infinity, hi = -Infinity;
    for (var i = 0; i < g.p.length; i++) { lo = Math.min(lo, g.p[i][0]); hi = Math.max(hi, g.p[i][0]); }
    return { lo: lo, hi: hi, mid: (lo + hi) / 2 };
  }
  function capOf(g) { return (g.l[2] - g.l[0]) * g.b[3]; }
  function baseOf(g) { return g.b[1] + g.l[2] * g.b[3]; }

  function syncGuides() {
    var b = parseFloat(getComputedStyle(canvas).borderTopWidth) || 0;
    var w = Math.max(0, canvas.offsetWidth - 2 * b), h = Math.max(0, canvas.offsetHeight - 2 * b);
    guidesEl.style.left = (canvas.offsetLeft + b) + 'px';
    guidesEl.style.top = (canvas.offsetTop + b) + 'px';
    guidesEl.style.width = w + 'px';
    guidesEl.style.height = h + 'px';
    var dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    var W = Math.round(w * dpr), H = Math.round(h * dpr);
    if (guidesEl.width !== W || guidesEl.height !== H) { guidesEl.width = W; guidesEl.height = H; }
    var c = guidesEl.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, W, H);
    if (!box || !w || !h || view !== 'draw') return;
    var lg = getCanvasLogicalSize();
    var kx = W / lg.width, ky = H / lg.height, u = lg.width / w;   // u: canvas units per CSS px
    c.setTransform(kx, 0, 0, ky, 0, 0);
    var css = getComputedStyle(guidesEl);
    var tok = function (n, d) { return css.getPropertyValue(n).trim() || d; };
    var bx = BOXES[at], capPx = (LINES.base - LINES.cap) * box.h;
    var baseY = box.y + LINES.base * box.h, cx = box.x + box.w / 2;

    if (mode === 'one' && old) {
      // Drawing a letter again: the one it had, faint behind, is the model.
      ghostLetter(c, old, cx, baseY, capPx, tok('--lt-ghost', 'rgba(124,92,255,.38)'));
    } else {
      // The model: caps, figures and marks fit the cap line; lowercase, second
      // tries and accents the x-height, so ascenders reach about the cap line.
      var m = faceMetrics();
      var lowish = bx.kind === 'lower' || bx.kind === 'again' || bx.kind === 'accent';
      var fs = lowish ? (LINES.base - LINES.x) * box.h / m.x : capPx / m.cap;
      var base = bx.base && letterStore.g[bx.base];
      if (bx.kind === 'accent' && base) {
        // Over the person's own letter: the model's accent alone (its letter
        // knocked out of it), and their letter faint where the accent goes on.
        var off = document.createElement('canvas');
        off.width = W; off.height = H;
        var oc = off.getContext('2d');
        oc.setTransform(kx, 0, 0, ky, 0, 0);
        oc.font = '300 ' + fs + 'px ' + FAM;
        oc.textAlign = 'center'; oc.textBaseline = 'alphabetic';
        oc.fillStyle = tok('--lt-model', 'rgba(124,92,255,.11)');
        oc.fillText(bx.model, cx, baseY);
        oc.globalCompositeOperation = 'destination-out';
        oc.fillStyle = '#000';
        oc.lineWidth = fs * 0.06; oc.strokeStyle = '#000';
        oc.fillText(bx.base, cx, baseY);
        oc.strokeText(bx.base, cx, baseY);
        c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(off, 0, 0); c.restore();
        ghostLetter(c, base, cx, baseY, capPx, tok('--lt-ghost', 'rgba(124,92,255,.38)'));
      } else {
        c.font = '300 ' + fs + 'px ' + FAM;
        c.textAlign = 'center'; c.textBaseline = 'alphabetic';
        c.fillStyle = tok('--lt-model', 'rgba(124,92,255,.11)');
        c.fillText(bx.model, cx, baseY);
      }
    }

    // The lines: dashed, the baseline solid and a little stronger.
    var x0 = box.x, x1 = box.x + box.w;
    [['cap', 0], ['x', 0], ['desc', 0], ['base', 1]].forEach(function (ln) {
      var y = box.y + LINES[ln[0]] * box.h;
      c.beginPath();
      c.setLineDash(ln[1] ? [] : [5 * u, 4 * u]);
      c.lineWidth = (ln[1] ? 2 : 1.5) * u;
      c.strokeStyle = ln[1] ? tok('--lt-base', 'rgba(124,92,255,.62)') : tok('--lt-line', 'rgba(124,92,255,.45)');
      c.moveTo(x0, y); c.lineTo(x1, y);
      c.stroke();
    });
    c.setLineDash([]);
  }
  // A stored letter drawn faint, scaled to this box by its cap height and
  // centred on its own ink.
  function ghostLetter(c, g, cx, baseY, capPx, ink) {
    var s = capPx / capOf(g), mid = inkSpan(g).mid, gb = baseOf(g), k = 0;
    c.strokeStyle = ink; c.lineCap = 'round'; c.lineJoin = 'round';
    for (var si = 0; si < g.n.length; si++) {
      c.beginPath();
      for (var j = 0; j < g.n[si]; j++, k++) {
        var q = g.p[k], X = cx + (q[0] - mid) * s, Y = baseY + (q[1] - gb) * s;
        if (!j) c.moveTo(X, Y); else c.lineTo(X, Y);
      }
      c.lineWidth = Math.max(1, (g.p[k - 1] ? g.p[k - 1][2] : PEN.size) * s);
      c.stroke();
    }
  }

  // ---- Lines of letters: the line along the bottom, the tiles, the start ----
  var SVGNS = 'http://www.w3.org/2000/svg';
  var SIDE = 0.09, SPACE = 0.36;   // in cap heights
  var writing = [];                // what is writing itself now
  function norm(g) {
    // A letter in cap heights, y up from its baseline, x from its ink centre.
    var cap = capOf(g), gb = baseOf(g), mid = inkSpan(g).mid, k = 0, out = [];
    for (var s = 0; s < g.n.length; s++) {
      var st = [];
      for (var j = 0; j < g.n[s]; j++, k++) {
        var q = g.p[k];
        st.push([(q[0] - mid) / cap, (gb - q[1]) / cap, q[3]]);
      }
      out.push(st);
    }
    return out;
  }
  function accentNorm(g) {
    // An accent in cap heights from its BOX's middle, where the person's base
    // letter sat, centred on its ink, while they drew it.
    var cap = capOf(g), gb = baseOf(g), mid = g.b[0] + g.b[2] / 2, k = 0, out = [];
    for (var s = 0; s < g.n.length; s++) {
      var st = [];
      for (var j = 0; j < g.n[s]; j++, k++) st.push([(g.p[k][0] - mid) / cap, (gb - g.p[k][1]) / cap, g.p[k][3]]);
      out.push(st);
    }
    return out;
  }
  function pathOf(strokesN, dx, upTo) {
    var d = '';
    for (var s = 0; s < strokesN.length; s++) {
      var st = strokesN[s], seg = '';
      for (var j = 0; j < st.length; j++) {
        if (upTo != null && st[j][3] > upTo) break;
        seg += (j ? 'L' : 'M') + (dx + st[j][0]).toFixed(3) + ' ' + (-st[j][1]).toFixed(3);
      }
      if (seg.indexOf('L') < 0 && seg) seg += 'l0.001 0';   // a dot is a dot
      d += seg;
    }
    return d;
  }
  // When each point is written, with every pause held to a quarter second,
  // so a letter writes the way it was drawn without its long thinks.
  function playTimes(strokesN) {
    var last = null, play = 0;
    strokesN.forEach(function (st) {
      st.forEach(function (q) {
        if (last != null) play += Math.min(250, Math.max(0, q[2] - last));
        last = q[2];
        q[3] = play;
      });
    });
    return play;
  }
  function svgPath(svg, d, faint, id) {
    var path = document.createElementNS(SVGNS, 'path');
    path.setAttribute('fill', 'none'); path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.6'); path.setAttribute('vector-effect', 'non-scaling-stroke');
    path.setAttribute('stroke-linecap', 'round'); path.setAttribute('stroke-linejoin', 'round');
    if (faint) path.setAttribute('stroke-opacity', '.22');
    else if (id) path.setAttribute('data-letter', id);
    path.setAttribute('d', d);
    svg.appendChild(path);
    return path;
  }
  // A line of words in the person's letters, the letters not yet drawn in the
  // page's face, faint. o: { kind, animateId, all, capPx, letters }.
  function lineSVG(text, o) {
    o = o || {};
    var kind = o.kind || 'lower', letters = o.letters || letterStore.g;
    var m = faceMetrics(), fs = 1 / m.cap;
    mctx.font = '300 100px ' + FAM;
    var unit = 100 * m.cap;   // px per cap height at 100px
    var x = 0, parts = [], seen = {};
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === ' ') { x += SPACE; continue; }
      var id = ch, g = null, acc = null;
      if (kind === 'again' && seen[ch]) id = ch + '2';
      seen[ch] = true;
      if (COMPOSED[ch]) { g = letters[COMPOSED[ch][0]]; acc = letters[COMPOSED[ch][1]]; if (!acc) g = null; }
      else g = letters[id];
      if (g) {
        var n = o.normed ? g : norm(g), lo = Infinity, hi = -Infinity;
        n.forEach(function (st) { st.forEach(function (q) { lo = Math.min(lo, q[0]); hi = Math.max(hi, q[0]); }); });
        x += SIDE;
        var dx = x - lo;
        parts.push({ kind: 'ink', n: n, dx: dx, id: COMPOSED[ch] ? COMPOSED[ch][0] : id });
        if (acc) parts.push({ kind: 'ink', n: accentNorm(acc), dx: dx, id: COMPOSED[ch][1] });
        x += (hi - lo) + SIDE;
      } else {
        var w = mctx.measureText(ch).width / unit;
        parts.push({ kind: 'text', ch: ch, x: x + SIDE * 0.5, w: w });
        x += w + SIDE;
      }
    }
    var top = -1.45, height = 1.95, width = Math.max(1, x), capPx = o.capPx || 15;
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', (-0.1) + ' ' + top + ' ' + (width + 0.2) + ' ' + height);
    svg.setAttribute('width', String(Math.round((width + 0.2) * capPx)));
    svg.setAttribute('height', String(Math.round(height * capPx)));
    // THE SET'S LAST WORD: the whole line writes itself, letter after letter,
    // over a faint copy of itself so it never stands half empty, in about
    // four and a half seconds whatever the letters' own pace.
    var whole = o.all && !still(), sum = 0, rate = 1, queue = 0;
    parts.forEach(function (p) { if (p.kind === 'ink') sum += (p.total = playTimes(p.n)); });
    if (whole) rate = Math.max(2, sum / 4500);
    parts.forEach(function (p) {
      if (p.kind === 'text') {
        var t = document.createElementNS(SVGNS, 'text');
        t.setAttribute('x', p.x.toFixed(3)); t.setAttribute('y', '0');
        t.setAttribute('font-size', fs.toFixed(4)); t.setAttribute('font-weight', '300');
        t.setAttribute('font-family', FAM); t.setAttribute('fill', 'currentColor');
        t.setAttribute('fill-opacity', '.3');
        t.textContent = p.ch;
        svg.appendChild(t);
        return;
      }
      if (whole) {
        // A dot takes no time to draw, but still waits its turn.
        svgPath(svg, pathOf(p.n, p.dx), true);
        writing.push(writeIn(svgPath(svg, '', false, p.id), p.n, p.dx, p.total, rate, queue));
        queue += p.total / rate + 40;
      } else if (o.animateId && p.id === o.animateId && !still() && p.total > 0) {
        writing.push(writeIn(svgPath(svg, '', false, p.id), p.n, p.dx, p.total, 1, 0));
      } else {
        svgPath(svg, pathOf(p.n, p.dx), false, p.id);
      }
    });
    return svg;
  }
  function stopWriting() {
    writing.forEach(function (w) { w.stop = true; });
    writing = [];
  }
  // The line along the bottom of the sheet: the pangram while the letters
  // are drawn, then the line for the group being drawn.
  function renderLine(animateId) {
    stopWriting();
    var kind = view === 'draw' ? BOXES[at].kind : 'lower';
    previewEl.textContent = '';
    previewEl.appendChild(lineSVG(LINE_FOR[kind] || PANGRAM, { kind: kind, animateId: animateId }));
  }
  // A letter writes itself, at the pace it was drawn (times `rate`).
  function writeIn(path, n, dx, total, rate, delay) {
    var job = { stop: false }, t0 = performance.now() + (delay || 0);
    (function frame(now) {
      if (job.stop) { path.setAttribute('d', pathOf(n, dx)); return; }
      var e = ((now || performance.now()) - t0) * (rate || 1);
      if (e >= total) { path.setAttribute('d', pathOf(n, dx)); return; }
      path.setAttribute('d', e > 0 ? pathOf(n, dx, e) : '');
      requestAnimationFrame(frame);
    })(performance.now());
    return job;
  }

  // ---- The words above the canvas, and what the buttons can do ----
  function renderTop() {
    var drawn = drawnCount(), n = BOXES.length;
    var quick = mode === 'seq' && !quickDone();
    var whole = quick ? QUICK.length : n;
    var count = quick ? QUICK.filter(has).length : drawn;
    barFill.style.width = (100 * count / whole).toFixed(2) + '%';
    barEl.setAttribute('aria-valuemax', String(whole));
    barEl.setAttribute('aria-valuenow', String(count));
    barEl.hidden = mode === 'one';
    laterBtnEl.hidden = mode === 'one';
    titleEl.textContent = mode === 'one' ? 'Your hand' : 'Draw your letters';
    // Written only when it changes: the line is a live region, and a stroke
    // is not news to someone listening.
    var key = mode + ':' + at + ':' + whole + ':' + (old ? 1 : 0);
    if (subEl.getAttribute('data-at') === key) return;
    subEl.setAttribute('data-at', key);
    var bx = BOXES[at], b = document.createElement('b');
    b.textContent = bx.ch;
    subEl.textContent = '';
    subEl.appendChild(b);
    if (NAMES[bx.ch] && bx.kind !== 'again') {
      var name = document.createElement('span');
      name.className = 'vis-hidden';
      name.textContent = ' ' + NAMES[bx.ch];
      subEl.appendChild(name);
    }
    var more = bx.kind === 'again' ? ' · second try'
      : bx.kind === 'accent' ? ' · the accent in ' + bx.model : '';
    var where = mode === 'one' ? (old ? ' · draw it again' : ' · add it')
      : ' · ' + (ORDER.indexOf(at) + 1) + ' of ' + whole;
    subEl.appendChild(document.createTextNode(more + where));
  }
  function renderButtons() {
    var drew = strokes.length > 0;
    if (mode === 'one') {
      backBtnEl.textContent = 'Cancel';
      backBtnEl.disabled = false;
      nextBtnEl.textContent = 'Done';
      nextBtnEl.disabled = !drew;
    } else {
      backBtnEl.textContent = 'Back';
      backBtnEl.disabled = ORDER.indexOf(at) === 0;
      nextBtnEl.textContent = 'Next';
      nextBtnEl.disabled = !drew;
    }
    redoBtnEl.disabled = !drew;
  }

  // ---- Moving between letters ----
  // What was on the canvas fades as the next letter comes, rather than
  // vanishing: a copy of the ink and the guides, let go over a fifth of a
  // second (letters.css .lt-fade). Still under Reduce Motion.
  function fadeOut() {
    if (still() || !canvas.width || view !== 'draw') return;
    var f = document.createElement('canvas');
    f.className = 'lt-fade';
    f.width = guidesEl.width || canvas.width; f.height = guidesEl.height || canvas.height;
    f.style.left = guidesEl.style.left; f.style.top = guidesEl.style.top;
    f.style.width = guidesEl.style.width; f.style.height = guidesEl.style.height;
    var c = f.getContext('2d');
    try { c.drawImage(guidesEl, 0, 0, f.width, f.height); c.drawImage(canvas, 0, 0, f.width, f.height); } catch (e) { return; }
    guidesEl.parentNode.appendChild(f);
    requestAnimationFrame(function () { requestAnimationFrame(function () { f.style.opacity = '0'; }); });
    setTimeout(function () { if (f.parentNode) f.parentNode.removeChild(f); }, 400);
  }
  // The take a letter was drawn in ends with the letter: clearCanvas leaves
  // `recording` as it was, and a take left running would carry on into the
  // next letter's clock. Ended on an empty canvas, so it says nothing.
  function endTake() {
    if (recording && typeof endRecordingTake === 'function') endRecordingTake();
  }
  function showLetter(i, opts) {
    opts = opts || {};
    if (opts.fade !== false) fadeOut();
    closePage();
    view = 'draw';
    mode = opts.mode || 'seq';
    document.body.classList.remove('letters-done');
    at = Math.max(0, Math.min(BOXES.length - 1, i));
    if (mode === 'seq') { letterStore.at = at; letterStore.mode = 'seq'; keepLetters(); }
    clearCanvas();
    endTake();
    setPen();
    var g = mode === 'seq' ? letterStore.g[BOXES[at].id] : null;
    box = g ? boxOf(g) : measureBox();
    if (g) putLetterBack(g);
    else beginRecording(false);
    lastLen = strokes.length;
    syncGuides();
    renderTop();
    renderButtons();
    renderLine(opts.animate || null);
  }
  // After every stroke: the letter as it now stands goes into the store, or,
  // drawing one again, into `pending` until Done.
  function takeStroke() {
    if (view !== 'draw' || drawing) return;
    var n = strokes.length;
    if (n === lastLen) return;
    lastLen = n;
    var id = BOXES[at].id;
    if (mode === 'one') {
      pending = n ? packLetter() : null;
    } else {
      if (n) letterStore.g[id] = packLetter(); else delete letterStore.g[id];
      keepLetters();
    }
    renderTop();
    renderButtons();
    renderLine(null);
  }
  ['pointerup', 'pointercancel'].forEach(function (t) {
    window.addEventListener(t, function () { setTimeout(takeStroke, 0); });
  });
  setInterval(takeStroke, 700);   // a lift the page missed (lib/lostlift.js) still lands

  // ---- Toasts that can be undone ----
  var cleared = null;   // what Redo took, until a new stroke begins
  function hideToast() {
    var t = $('toast');
    if (!t) return;
    t.classList.remove('show');
    setTimeout(function () { t.hidden = true; }, 200);
  }
  function hideUndoOffer() {
    if (!cleared) return;
    cleared = null;
    hideToast();
  }
  canvas.addEventListener('pointerdown', hideUndoOffer, true);
  function offerUndo(words, anchor, undo) {
    if (typeof showToast === 'function') showToast(words, anchor, { label: 'Undo', onClick: undo });
  }

  redoBtnEl.addEventListener('click', function () {
    if (view !== 'draw' || !strokes.length) return;
    if (mode === 'one') {
      // Drawing one again: only the new strokes go; the old letter is still
      // the one kept until Done.
      pending = null;
      showLetter(at, { mode: 'one' });
      return;
    }
    var id = BOXES[at].id, g = letterStore.g[id] || packLetter();
    delete letterStore.g[id];
    keepLetters();
    showLetter(at);
    cleared = { id: id, g: g, at: at };
    offerUndo('Cleared', topEl, function () {
      var c = cleared;
      cleared = null;
      if (!c || c.at !== at || strokes.length) return;
      letterStore.g[c.id] = c.g;
      keepLetters();
      showLetter(at, { fade: false });
    });
  });
  backBtnEl.addEventListener('click', function () {
    if (view !== 'draw') return;
    if (mode === 'one') { old = null; pending = null; showTiles(); return; }   // Cancel: the letter keeps what it had
    var p = ORDER.indexOf(at);
    if (p > 0) showLetter(ORDER[p - 1]);
  });
  nextBtnEl.addEventListener('click', function () {
    if (view !== 'draw') return;
    takeStroke();
    var id = BOXES[at].id;
    if (mode === 'one') {
      if (!pending) return;
      letterStore.g[id] = pending;
      keepLetters();
      old = null; pending = null;
      showTiles({ animate: id });
      return;
    }
    if (!has(id)) return;
    // The 30 just finished: Ready, once.
    if (quickDone() && !letterStore.r) {
      letterStore.r = true;
      keepLetters();
      fadeOut();
      showReady();
      return;
    }
    var next = nextUndrawn(ORDER.indexOf(at));
    if (next < 0) { fadeOut(); showTiles({ all: true }); return; }
    showLetter(next, { animate: id });
  });
  laterBtnEl.addEventListener('click', function () {
    takeStroke();
    window.location.assign(window.location.pathname);
  });

  // ---- The pages: the start, Ready, and the tiles ----
  var pageEl = null;
  function closePage() {
    if (pageEl && pageEl.parentNode) pageEl.parentNode.removeChild(pageEl);
    pageEl = null;
    document.body.classList.remove('lt-paged');
  }
  function openPage(name, title, sub, cls) {
    closePage();
    stopWriting();
    endTake();
    view = name;
    old = null; pending = null;
    pageEl = document.createElement('section');
    pageEl.className = 'lt-page' + (cls ? ' ' + cls : '');
    pageEl.setAttribute('aria-labelledby', 'ltPageTitle');
    var head = document.createElement('div');
    head.className = 'lt-ptop';
    head.innerHTML = '<div class="lt-phead"><h2 class="lt-ptitle" id="ltPageTitle"></h2><p class="lt-psub" id="ltPageSub"></p></div>';
    head.querySelector('.lt-ptitle').textContent = title;
    head.querySelector('.lt-psub').textContent = sub;
    pageEl.appendChild(head);
    document.body.appendChild(pageEl);
    document.body.classList.add('lt-paged');
    return pageEl;
  }
  function button(label, cls, onClick) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.textContent = label;
    b.addEventListener('click', onClick);
    return b;
  }
  function leave() { window.location.assign(window.location.pathname); }

  function showStart() {
    var p = openPage('start', 'Your hand', 'Text that writes the way you write', 'lt-mid');
    p.querySelector('.lt-ptop').appendChild(button('Close', 'lt-pdone', leave));
    var body = document.createElement('div');
    body.className = 'lt-pbody lt-intro';
    var hero = document.createElement('div');
    hero.className = 'lt-hero';
    var hello = {};
    Object.keys(HELLO).forEach(function (k) { hello[k] = HELLO[k].map(function (st) { return st.map(function (q) { return q.slice(); }); }); });
    hero.appendChild(lineSVG('hello', { letters: hello, normed: true, capPx: 44, all: true }));
    body.appendChild(hero);
    body.insertAdjacentHTML('beforeend',
      '<p>Draw each letter once, the way you write it. Then Text writes your words in your hand, at your own speed.</p>'
      + '<ol class="lt-steps"><li><i>1</i><span><b>30 letters to start:</b> a to z and . , ! ? About 10 minutes.</span></li>'
      + '<li><i>2</i><span><b>The rest when you like:</b> capitals, numbers and marks.</span></li>'
      + '<li><i>3</i><span><b>Change any letter later,</b> by tapping it.</span></li></ol>'
      + '<p class="lt-small">Your letters stay on this device. Save a copy to keep them safe.</p>');
    p.appendChild(body);
    var foot = document.createElement('div');
    foot.className = 'lt-pfoot';
    foot.appendChild(button('Start with a', 'lt-primary', function () {
      letterStore.mode = 'seq';
      showLetter(ORDER[0], { fade: false });
    }));
    var quiet = document.createElement('div');
    quiet.className = 'lt-quiet';
    quiet.appendChild(button('Open a copy', 'lt-link', openCopy));
    foot.appendChild(quiet);
    p.appendChild(foot);
  }

  function showReady() {
    var p = openPage('ready', 'Your hand is ready', QUICK.length + ' letters · the rest whenever you like', 'lt-mid');
    var body = document.createElement('div');
    body.className = 'lt-pbody lt-intro';
    var hero = document.createElement('div');
    hero.className = 'lt-hero';
    hero.appendChild(lineSVG('Sphinx of black', { capPx: 34, all: true }));
    hero.appendChild(lineSVG('quartz, judge my vow.', { capPx: 34, all: true }));
    body.appendChild(hero);
    body.insertAdjacentHTML('beforeend', '<p>That’s your hand. Capitals, numbers and the other marks aren’t drawn yet, like the S above. Add them whenever you like.</p>');
    p.appendChild(body);
    var foot = document.createElement('div');
    foot.className = 'lt-pfoot';
    var two = document.createElement('div');
    two.className = 'lt-two';
    two.appendChild(button('Add the rest · ' + (BOXES.length - drawnCount()), 'lt-second', addRest));
    two.appendChild(button('Done', 'lt-primary', function () { showTiles(); }));
    foot.appendChild(two);
    p.appendChild(foot);
  }
  function addRest() {
    var i = firstUndrawn();
    if (i < 0) { showTiles(); return; }
    letterStore.mode = 'seq';
    showLetter(i, { fade: false });
  }

  function tileSVG(g) {
    var n = norm(g), lo = Infinity, hi = -Infinity;
    n.forEach(function (st) { st.forEach(function (q) { lo = Math.min(lo, q[0]); hi = Math.max(hi, q[0]); }); });
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '-0.75 -1.3 1.5 1.75');
    svg.setAttribute('width', '33'); svg.setAttribute('height', '39');
    svg.setAttribute('aria-hidden', 'true');
    var path = svgPath(svg, pathOf(n, -(lo + hi) / 2), false);
    path.setAttribute('stroke-width', '1.5');
    return svg;
  }
  function showTiles(opts) {
    opts = opts || {};
    letterStore.mode = 'tiles';
    keepLetters();
    var n = drawnCount();
    var p = openPage('tiles', 'Your hand', n + ' of ' + BOXES.length + ' · tap a letter to draw it again');
    p.querySelector('.lt-ptop').appendChild(button('Done', 'lt-pdone', leave));
    var body = document.createElement('div');
    body.className = 'lt-pbody';
    GROUPS.forEach(function (gr) {
      var ids = gr[1], got = ids.filter(has).length;
      var h = document.createElement('h3');
      h.className = 'lt-gh';
      h.textContent = gr[0];
      var count = document.createElement('span');
      count.textContent = got + ' of ' + ids.length;
      h.appendChild(count);
      body.appendChild(h);
      var grid = document.createElement('div');
      grid.className = 'lt-tiles';
      ids.forEach(function (id) {
        var bx = BOXES[BY_ID[id]], on = has(id);
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'lt-tile' + (on ? '' : ' empty');
        b.setAttribute('data-id', id);
        var label = (NAMES[bx.ch] && bx.kind !== 'again' ? NAMES[bx.ch] : bx.ch) + (bx.kind === 'again' ? ', second try' : '');
        b.setAttribute('aria-label', (on ? 'Draw ' + label + ' again' : 'Add ' + label));
        if (on) b.appendChild(tileSVG(letterStore.g[id]));
        else { var s = document.createElement('span'); s.className = 'lt-tch'; s.setAttribute('aria-hidden', 'true'); s.textContent = bx.kind === 'accent' ? bx.model : bx.ch; b.appendChild(s); }
        b.addEventListener('click', function () { drawOne(id); });
        grid.appendChild(b);
      });
      body.appendChild(grid);
    });
    p.appendChild(body);
    var foot = document.createElement('div');
    foot.className = 'lt-pfoot';
    var line = document.createElement('div');
    line.className = 'lt-pline';
    line.setAttribute('aria-hidden', 'true');
    line.appendChild(lineSVG(PANGRAM, { capPx: 15, all: !!opts.all, animateId: opts.animate || null }));
    foot.appendChild(line);
    if (n < BOXES.length) foot.appendChild(button('Add the rest · ' + (BOXES.length - n), 'lt-primary', addRest));
    var quiet = document.createElement('div');
    quiet.className = 'lt-quiet';
    quiet.appendChild(button('Save a copy', 'lt-link', saveCopy));
    quiet.appendChild(button('Open a copy', 'lt-link', openCopy));
    quiet.appendChild(button('Start over', 'lt-link', startOver));
    quiet.appendChild(button('Post your letters', 'lt-link', postSet));
    foot.appendChild(quiet);
    p.appendChild(foot);
    if (opts.scroll) body.scrollTop = opts.scroll;
  }
  function drawOne(id) {
    var g = letterStore.g[id] || null;
    closePage();
    old = g;            // the letter it has, kept until Done
    pending = null;
    showLetter(BY_ID[id], { mode: 'one', fade: false });
  }

  // ---- A copy: a file of the letters, to keep or to open on another device ----
  function saveCopy() {
    var data = JSON.stringify({ type: FILE_TYPE, v: 1, g: letterStore.g });
    // A plain download, as the Pad's own Save as a file is: Safari shows a
    // JSON file instead of saving it.
    var blob = new Blob([data], { type: 'application/octet-stream' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'my-hand.skriblhand';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    if (typeof showToast === 'function') showToast('Saved a copy of your hand', pageEl && pageEl.querySelector('.lt-ptop'));
  }
  // What a copy may hold: known letters, each a sane run of points.
  function validHand(o) {
    if (!o || o.type !== FILE_TYPE || o.v !== 1 || !o.g || typeof o.g !== 'object') return null;
    var g = {}, num = function (v) { return typeof v === 'number' && isFinite(v); };
    var ids = Object.keys(o.g);
    if (!ids.length) return null;
    for (var i = 0; i < ids.length; i++) {
      var id = ids[i], L = o.g[id];
      if (!(id in BY_ID) || !L || !Array.isArray(L.p) || !Array.isArray(L.n) || !L.p.length || L.p.length > 20000) return null;
      var sum = 0;
      for (var k = 0; k < L.n.length; k++) { if (!(L.n[k] > 0) || L.n[k] !== Math.floor(L.n[k])) return null; sum += L.n[k]; }
      if (sum !== L.p.length) return null;
      for (var j = 0; j < L.p.length; j++) { var q = L.p[j]; if (!Array.isArray(q) || q.length !== 4 || !q.every(num)) return null; }
      if (!Array.isArray(L.b) || L.b.length !== 4 || !L.b.every(num) || !(L.b[3] > 0)) return null;
      if (!Array.isArray(L.l) || L.l.length !== 4 || !L.l.every(num) || !(L.l[2] > L.l[0])) return null;
      g[id] = { p: L.p, n: L.n, b: L.b, l: L.l, c: /^#[0-9a-f]{6}$/i.test(L.c || '') ? L.c : PEN.color };
    }
    return g;
  }
  var fileIn = document.createElement('input');
  fileIn.type = 'file';
  fileIn.id = 'ltOpenCopy';
  fileIn.accept = '.skriblhand,application/octet-stream,application/json,text/plain,text/*';
  fileIn.hidden = true;
  fileIn.setAttribute('aria-label', 'Open a copy of your hand');
  document.body.appendChild(fileIn);
  function openCopy() { fileIn.value = ''; fileIn.click(); }
  fileIn.addEventListener('change', function () {
    var f = fileIn.files && fileIn.files[0];
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var g = null;
      try { g = validHand(JSON.parse(String(rd.result))); } catch (e) { g = null; }
      if (!g) {
        if (typeof showToast === 'function') showToast('That file isn’t a copy of a hand from Skribl. Nothing was changed', pageEl && pageEl.querySelector('.lt-ptop'));
        return;
      }
      var before = JSON.parse(JSON.stringify(letterStore));
      letterStore.g = g;
      letterStore.r = true;
      showTiles();
      offerUndo('Opened your copy', pageEl && pageEl.querySelector('.lt-ptop'), function () {
        letterStore = before;
        keepLetters();
        if (drawnCount()) showTiles(); else showStart();
      });
    };
    rd.readAsText(f);
  });
  function startOver() {
    var before = JSON.parse(JSON.stringify(letterStore));
    letterStore = { v: 1, o: 2, at: null, mode: 'seq', g: {} };
    keepLetters();
    showStart();
    offerUndo('Your letters are cleared', pageEl && pageEl.querySelector('.lt-ptop'), function () {
      letterStore = before;
      keepLetters();
      showTiles();
    });
  }

  // ---- The set, laid out to post ----
  // THE LAYOUT RULE, which harness/tools/letterfont.py repeats to read a
  // posted set back: a grid of cells CELL_W cap heights wide and as tall as a
  // letter's box, as big as the canvas allows inside a margin of 4% of its
  // shorter side, centred, one cell for each of the 92 in the posted order (a
  // letter not drawn yet leaves its cell empty). Each letter is scaled by its
  // cap height, sits on its cell's baseline, and is centred on its own ink;
  // its width is drawn at GAIN times its scale, so a line stays visible at
  // that size, and the reader divides it back out. One after another, each at
  // the pace it was drawn, GAP apart.
  function gridFor(W, H, n) {
    var cellH = 1 / (LINES.base - LINES.cap), m = 0.04 * Math.min(W, H), best = null;
    for (var cols = 1; cols <= n; cols++) {
      var rows = Math.ceil(n / cols);
      var cap = Math.min((W - 2 * m) / (cols * CELL_W), (H - 2 * m) / (rows * cellH));
      if (!best || cap > best.cap + 1e-9) best = { cols: cols, rows: rows, cap: cap };
    }
    best.cellH = cellH;
    best.x0 = (W - best.cols * CELL_W * best.cap) / 2;
    best.y0 = (H - best.rows * cellH * best.cap) / 2;
    return best;
  }
  function composeSet() {
    var lg = getCanvasLogicalSize(), W = Math.round(lg.width), H = Math.round(lg.height);
    var L = gridFor(W, H, BOXES.length), pts = [], groups = [], T = 0;
    BOXES.forEach(function (bx, i) {
      var g = letterStore.g[bx.id];
      if (!g) return;
      var col = i % L.cols, row = Math.floor(i / L.cols);
      var cx = L.x0 + (col + 0.5) * CELL_W * L.cap;
      var baseY = L.y0 + (row + LINES.base) * L.cellH * L.cap;
      var s = L.cap / capOf(g), mid = inkSpan(g).mid, gb = baseOf(g), k = 0, last = 0;
      for (var si = 0; si < g.n.length; si++) {
        for (var j = 0; j < g.n[si]; j++, k++) {
          var q = g.p[k];
          var pt = { x: cx + (q[0] - mid) * s, y: baseY + (q[1] - gb) * s, color: g.c,
                     size: q[2] * s * GAIN, t: T + q[3], erase: false };
          if (j === 0) pt.start = true;
          pts.push(pt);
          last = q[3];
        }
        groups.push(g.n[si]);
      }
      T += last + GAP;
    });
    return { pts: pts, groups: groups };
  }
  // Post your letters: the set on the canvas as a finished drawing, and the
  // post sheet over it; when the sheet goes, the tiles come back.
  function postSet() {
    if (!drawnCount()) return;
    var scroll = pageEl && pageEl.querySelector('.lt-pbody') ? pageEl.querySelector('.lt-pbody').scrollTop : 0;
    closePage();
    view = 'set';
    document.body.classList.add('letters-done');
    clearCanvas();
    endTake();
    var set = composeSet();
    preRecordSnapshot = null;
    strokes = set.pts;
    strokeGroups = set.groups;
    hasContent = true;
    recorded = true;
    finishedRecording = true;
    paintStrokesStatic(strokes);
    updateEmptyHint();
    if (window.SkriblName) SkriblName.set('My letters');
    box = null;
    syncGuides();
    var post = $('postBtn'), overlay = $('postOverlay');
    if (!post || !overlay) return;
    post.hidden = false;
    post.disabled = false;
    post.click();
    var watch = new MutationObserver(function () {
      if (!overlay.hidden) return;
      watch.disconnect();
      document.body.classList.remove('letters-done');
      clearCanvas();
      showTiles({ scroll: scroll });
    });
    setTimeout(function () { watch.observe(overlay, { attributes: true, attributeFilter: ['hidden'] }); }, 400);
  }

  // ---- Keys: the sheet's own, and the Pad's undo, and nothing else ----
  // The Pad's letter keys reach what this page has put away or fixed: e is
  // the eraser, [ and ] the pen's size, Space the pan. They stop here. Undo
  // and redo pass (Ctrl or Cmd with Z or Y): they take back the last stroke
  // of this letter, and its store follows (takeStroke). Typing in a field and
  // the post sheet are left alone; a button's own Enter and Space still work.
  window.addEventListener('keydown', function (e) {
    var t = e.target;
    if (t && t.closest && (t.closest('input, textarea, select, [contenteditable]') ||
        t.closest('#postOverlay, [role="dialog"]'))) return;
    var k = (e.key || '').toLowerCase();
    if ((e.ctrlKey || e.metaKey) && !e.altKey && (k === 'z' || k === 'y')) {
      if (view !== 'draw') e.stopPropagation();
      else setTimeout(takeStroke, 0);
      return;
    }
    if (view === 'draw' && e.key === 'ArrowRight' && !nextBtnEl.disabled) { e.preventDefault(); nextBtnEl.click(); }
    else if (view === 'draw' && e.key === 'ArrowLeft' && !backBtnEl.disabled) { e.preventDefault(); backBtnEl.click(); }
    e.stopPropagation();
  }, true);

  // ---- Start: where the person left off ----
  function relayout() {
    if (view !== 'draw') { syncGuides(); return; }
    if (!strokes.length) box = measureBox();
    syncGuides();
  }
  var relayoutTimer = null;
  window.addEventListener('resize', function () { clearTimeout(relayoutTimer); relayoutTimer = setTimeout(relayout, 120); });
  if (window.ResizeObserver) new ResizeObserver(function () { clearTimeout(relayoutTimer); relayoutTimer = setTimeout(relayout, 120); }).observe(canvas);

  function startSheet() {
    if (!drawnCount()) { showStart(); return; }
    if (letterStore.mode === 'seq') {
      var i = letterStore.at;
      if (typeof i !== 'number' || i < 0 || i >= BOXES.length) i = firstUndrawn();
      if (i >= 0) { showLetter(i, { fade: false }); return; }
    }
    showTiles();
  }
  // Once the page has laid out (fonts in, the canvas at its size), so the
  // box the first letter gets is the box it keeps.
  function whenLaidOut(fn) {
    var go = function () { requestAnimationFrame(function () { requestAnimationFrame(fn); }); };
    if (document.readyState === 'complete') go(); else window.addEventListener('load', go, { once: true });
  }
  whenLaidOut(startSheet);

  // For the harness: the sheet's state and its two rules, read, never driven.
  window.SkriblLetters = {
    boxes: function () { return BOXES.map(function (b) { return { id: b.id, ch: b.ch, kind: b.kind }; }); },
    order: function () { return ORDER.map(function (i) { return BOXES[i].id; }); },
    view: function () { return view; },
    mode: function () { return mode; },
    at: function () { return at; },
    ended: function () { return view === 'set'; },
    box: function () { return view === 'draw' && box ? { x: box.x, y: box.y, w: box.w, h: box.h } : null; },
    lines: function () { return { cap: LINES.cap, x: LINES.x, base: LINES.base, desc: LINES.desc }; },
    store: function () { return JSON.parse(JSON.stringify(letterStore)); },
    grid: gridFor,
    rule: { GAP: GAP, GAIN: GAIN, CELL_W: CELL_W }
  };
})();
