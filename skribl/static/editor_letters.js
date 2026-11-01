/* THE LETTER SHEET: the Pad at /skribl-pad?letters=1, a page for drawing the
 * owner's own font, one letter at a time (FUTURE.md, the Text tool; the
 * mock the owner said "All yes" to).
 *
 * WHY THE REAL PAD. A letter is drawn on the Pad's own canvas with its own
 * pen, so it is stored the way every Skribl stroke is: each point with its
 * time and its width (pressure is folded into the width). The Text tool will
 * write words in this hand at the speed it was drawn, so a letter has to be a
 * performance, not a picture, and the Pad is what records one.
 *
 * WHAT IT DOES, in the order the owner meets it:
 *   - One box at a time, 92 of them (BOXES): a-z, A-Z, 0-9, sixteen marks,
 *     five accents drawn over the owner's own base letter, and a second try
 *     at the nine commonest letters, so a word with two e's is not stamped.
 *   - Guide lines (cap height, x-height, baseline, the line descenders reach)
 *     and a faint model letter, on a canvas of their own UNDER the ink, inside
 *     the zoom layer as the grid is: a pinch moves them with the drawing, and
 *     they are never part of it.
 *   - Next keeps the letter and moves on; Back goes to the one before, with
 *     its letter on the canvas to add to; Redo clears this one, and the toast
 *     it leaves can bring it back. Finish later goes to the Pad: every stroke
 *     is kept as it is drawn, so nothing waits on a button.
 *   - Along the bottom, a line writes itself in the letters drawn so far: the
 *     pangram while the letters are drawn, then a line for each later group.
 *   - At the end the whole set is laid out on the canvas, each letter at its
 *     own speed one after another, and Post your letters posts it as any
 *     Skribl. harness/tools/letterfont.py reads a posted set back into
 *     letters, by the layout rule below.
 *
 * WHAT IT LEAVES ALONE. The owner's Pad draft (editor_draft.js keeps no draft
 * on this page, as compose keeps none), and the Pad's settings: the sheet
 * draws with the plain pen at one size, unmirrored, by shadowing the brush
 * and mirror for this page's life, never by setting them, which saves them.
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

  var PANGRAM = 'Sphinx of black quartz, judge my vow.';
  var LINE_FOR = {
    lower: PANGRAM, upper: PANGRAM,
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

  // ---- The 92 boxes, in the order they are drawn and posted ----
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
  // { v: 1, at: index on the canvas, g: { id: letter } }, a letter being
  // { p: [[x, y, width, t], ...] in canvas units with t in ms from its first
  //   point, n: points per stroke, b: [x, y, w, h] its box, l: [cap, x, base,
  //   desc] its lines, c: its colour }.
  var letterStore = readLetters();
  var storeOk = true;
  function readLetters() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (s && s.v === 1 && s.g && typeof s.g === 'object') return s;
    } catch (e) {}
    return { v: 1, at: 0, g: {} };
  }
  function keepLetters() {
    try { localStorage.setItem(KEY, JSON.stringify(letterStore)); storeOk = true; }
    catch (e) {
      // Said once, kindly: the letters on screen are fine, but a reload or
      // Finish later would lose them.
      if (storeOk && typeof showToast === 'function') {
        showToast('This browser isn’t keeping your letters, so finish in one go, or post them before you leave', topEl);
      }
      storeOk = false;
    }
  }
  function drawnCount() {
    var n = 0;
    for (var i = 0; i < BOXES.length; i++) if (letterStore.g[BOXES[i].id]) n++;
    return n;
  }
  function firstUndrawn() {
    for (var i = 0; i < BOXES.length; i++) if (!letterStore.g[BOXES[i].id]) return i;
    return -1;
  }

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

  // ---- Where the letter goes: the canvas the bars leave clear ----
  var at = 0, box = null, ended = false, lastLen = -1;
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

  // ---- The guides, the model, and the owner's own base letter under an accent ----
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
    if (!box || !w || !h || ended) return;
    var lg = getCanvasLogicalSize();
    var kx = W / lg.width, ky = H / lg.height, u = lg.width / w;   // u: canvas units per CSS px
    c.setTransform(kx, 0, 0, ky, 0, 0);
    var css = getComputedStyle(guidesEl);
    var tok = function (n, d) { return css.getPropertyValue(n).trim() || d; };
    var bx = BOXES[at], capPx = (LINES.base - LINES.cap) * box.h;
    var baseY = box.y + LINES.base * box.h, cx = box.x + box.w / 2;

    // The model: caps, figures and marks fit the cap line; lowercase, second
    // tries and accents the x-height, so ascenders reach about the cap line.
    var m = faceMetrics();
    var lowish = bx.kind === 'lower' || bx.kind === 'again' || bx.kind === 'accent';
    var fs = lowish ? (LINES.base - LINES.x) * box.h / m.x : capPx / m.cap;
    var base = bx.base && letterStore.g[bx.base];
    if (bx.kind === 'accent' && base) {
      // Over the owner's own letter: the model's accent alone (its letter
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

  // ---- The line along the bottom ----
  var SVGNS = 'http://www.w3.org/2000/svg';
  var SIDE = 0.09, SPACE = 0.36;   // in cap heights
  var writing = [];                // what the line is writing in now
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
    // An accent in cap heights from its BOX's middle, where the owner's base
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
  // so the line writes the way the letter was drawn without its long thinks.
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
  function renderLine(animateId, all) {
    writing.forEach(function (w) { w.stop = true; });
    writing = [];
    var kind = ended ? 'lower' : BOXES[at].kind;
    var text = LINE_FOR[kind] || PANGRAM;
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
      if (COMPOSED[ch]) { g = letterStore.g[COMPOSED[ch][0]]; acc = letterStore.g[COMPOSED[ch][1]]; if (!acc) g = null; }
      else g = letterStore.g[id];
      if (g) {
        var n = norm(g), lo = Infinity, hi = -Infinity;
        n.forEach(function (st) { st.forEach(function (q) { lo = Math.min(lo, q[0]); hi = Math.max(hi, q[0]); }); });
        x += SIDE;
        var dx = x - lo;
        var parts1 = [{ n: n, dx: dx, id: COMPOSED[ch] ? COMPOSED[ch][0] : id }];
        if (acc) parts1.push({ n: accentNorm(acc), dx: dx, id: COMPOSED[ch][1] });
        parts1.forEach(function (pp) { parts.push({ kind: 'ink', n: pp.n, dx: pp.dx, id: pp.id }); });
        x += (hi - lo) + SIDE;
      } else {
        var w = mctx.measureText(ch).width / unit;
        parts.push({ kind: 'text', ch: ch, x: x + SIDE * 0.5, w: w });
        x += w + SIDE;
      }
    }
    var top = -1.45, height = 1.95, width = Math.max(1, x);
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', (-0.1) + ' ' + top + ' ' + (width + 0.2) + ' ' + height);
    svg.setAttribute('width', String(Math.round((width + 0.2) * 15)));
    svg.setAttribute('height', String(Math.round(height * 15)));
    // THE SET'S LAST WORD: the whole line writes itself, letter after letter,
    // over a faint copy of itself so it never stands half empty, in about
    // four and a half seconds whatever the letters' own pace.
    var whole = all && !still(), sum = 0, rate = 1, queue = 0;
    parts.forEach(function (p) { if (p.kind === 'ink') sum += (p.total = playTimes(p.n)); });
    if (whole) rate = Math.max(2, sum / 4500);
    var inkPath = function (p, d, faint) {
      var path = document.createElementNS(SVGNS, 'path');
      path.setAttribute('fill', 'none'); path.setAttribute('stroke', 'currentColor');
      path.setAttribute('stroke-width', '1.6'); path.setAttribute('vector-effect', 'non-scaling-stroke');
      path.setAttribute('stroke-linecap', 'round'); path.setAttribute('stroke-linejoin', 'round');
      if (faint) path.setAttribute('stroke-opacity', '.22');
      else path.setAttribute('data-letter', p.id);
      path.setAttribute('d', d);
      svg.appendChild(path);
      return path;
    };
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
        inkPath(p, pathOf(p.n, p.dx), true);
        writing.push(writeIn(inkPath(p, '', false), p.n, p.dx, p.total, rate, queue));
        queue += p.total / rate + 40;
      } else if (animateId && p.id === animateId && !still() && p.total > 0) {
        writing.push(writeIn(inkPath(p, '', false), p.n, p.dx, p.total, 1, 0));
      } else {
        inkPath(p, pathOf(p.n, p.dx), false);
      }
    });
    previewEl.textContent = '';
    previewEl.appendChild(svg);
  }
  // The letter just drawn writes itself into the line, at the pace it was drawn.
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

  // ---- The words above, and what the buttons can do ----
  function renderTop() {
    var drawn = drawnCount(), n = BOXES.length;
    barFill.style.width = (100 * drawn / n).toFixed(2) + '%';
    barEl.setAttribute('aria-valuenow', String(drawn));
    if (ended) {
      titleEl.textContent = 'All your letters are drawn';
      subEl.textContent = n + ' of ' + n + ' · your font is ready';
      subEl.removeAttribute('data-at');
      return;
    }
    titleEl.textContent = 'Draw your letters';
    // Written only when it changes: the line is a live region, and a stroke
    // is not news to someone listening.
    if (subEl.getAttribute('data-at') === String(at)) return;
    subEl.setAttribute('data-at', String(at));
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
    subEl.appendChild(document.createTextNode(more + ' · ' + (at + 1) + ' of ' + n));
  }
  function renderButtons() {
    var has = !ended && strokes.length > 0;
    nextBtnEl.textContent = ended ? 'Post your letters' : 'Next';
    nextBtnEl.disabled = !ended && !has;
    backBtnEl.disabled = !ended && at === 0;
    redoBtnEl.hidden = ended;
    redoBtnEl.disabled = !has;
    laterBtnEl.hidden = ended;
  }

  // ---- Moving between letters ----
  // What was on the canvas fades as the next letter comes, rather than
  // vanishing: a copy of the ink and the guides, let go over a fifth of a
  // second (letters.css .lt-fade). Still under Reduce Motion.
  function fadeOut() {
    if (still() || !canvas.width) return;
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
  function showLetter(i, opts) {
    opts = opts || {};
    if (i >= BOXES.length) { endSheet(); return; }
    if (opts.fade !== false) fadeOut();
    ended = false;
    document.body.classList.remove('letters-done');
    at = Math.max(0, Math.min(BOXES.length - 1, i));
    letterStore.at = at;
    keepLetters();
    clearCanvas();
    endTake();
    setPen();
    var g = letterStore.g[BOXES[at].id];
    box = g ? boxOf(g) : measureBox();
    if (g) putLetterBack(g);
    else beginRecording(false);
    lastLen = strokes.length;
    syncGuides();
    renderTop();
    renderButtons();
    renderLine(opts.animate || null);
  }
  // The take a letter was drawn in ends with the letter: clearCanvas leaves
  // `recording` as it was, and a take left running would carry on into the
  // next letter's clock. Ended on an empty canvas, so it says nothing.
  function endTake() {
    if (recording && typeof endRecordingTake === 'function') endRecordingTake();
  }
  // After every stroke: the letter as it now stands goes into the store.
  function takeStroke() {
    if (ended || drawing) return;
    var n = strokes.length;
    if (n === lastLen) return;
    lastLen = n;
    var id = BOXES[at].id;
    if (n) letterStore.g[id] = packLetter(); else delete letterStore.g[id];
    keepLetters();
    renderTop();
    renderButtons();
    renderLine(null);
  }
  ['pointerup', 'pointercancel'].forEach(function (t) {
    window.addEventListener(t, function () { setTimeout(takeStroke, 0); });
  });
  setInterval(takeStroke, 700);   // a lift the page missed (lib/lostlift.js) still lands

  var cleared = null;   // what Redo took, until a new stroke begins
  function hideUndoOffer() {
    var t = $('toast');
    if (!cleared || !t) return;
    cleared = null;
    t.classList.remove('show');
    setTimeout(function () { t.hidden = true; }, 200);
  }
  canvas.addEventListener('pointerdown', hideUndoOffer, true);

  redoBtnEl.addEventListener('click', function () {
    if (ended || !strokes.length) return;
    var id = BOXES[at].id, g = letterStore.g[id] || packLetter();
    delete letterStore.g[id];
    keepLetters();
    showLetter(at);
    cleared = { id: id, g: g, at: at };
    if (typeof showToast === 'function') {
      showToast('Cleared', topEl, { label: 'Undo', onClick: function () {
        var c = cleared;
        cleared = null;
        if (!c || c.at !== at || strokes.length) return;
        letterStore.g[c.id] = c.g;
        keepLetters();
        showLetter(at, { fade: false });
      } });
    }
  });
  backBtnEl.addEventListener('click', function () {
    if (ended) { showLetter(BOXES.length - 1); return; }
    if (at > 0) showLetter(at - 1);
  });
  nextBtnEl.addEventListener('click', function () {
    if (ended) { postSet(); return; }
    takeStroke();
    if (!letterStore.g[BOXES[at].id]) return;
    var done = BOXES[at].id;
    var next = at + 1;
    if (next >= BOXES.length) {
      var gap = firstUndrawn();
      if (gap >= 0) { showLetter(gap, { animate: done }); return; }
    }
    showLetter(next, { animate: done });
  });
  laterBtnEl.addEventListener('click', function () {
    takeStroke();
    window.location.assign(window.location.pathname);
  });

  // ---- The whole set, laid out to post ----
  // THE LAYOUT RULE, which harness/tools/letterfont.py repeats to read a
  // posted set back: a grid of cells CELL_W cap heights wide and as tall as a
  // letter's box, as big as the canvas allows inside a margin of 4% of its
  // shorter side, centred. Each letter is scaled by its cap height, sits on
  // its cell's baseline, and is centred on its own ink; its width is drawn at
  // GAIN times its scale, so a line stays visible at that size, and the reader
  // divides it back out. One after another, each at the pace it was drawn,
  // GAP apart.
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
  function endSheet() {
    if (firstUndrawn() >= 0) { showLetter(firstUndrawn()); return; }
    fadeOut();
    ended = true;
    letterStore.at = BOXES.length;
    keepLetters();
    document.body.classList.add('letters-done');
    clearCanvas();
    endTake();
    var set = composeSet();
    // The set is the drawing now, as a finished take: what Post sends.
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
    renderTop();
    renderButtons();
    renderLine(null, true);
  }
  function postSet() {
    var post = $('postBtn');
    if (!post) return;
    post.hidden = false;
    post.disabled = false;
    post.click();
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
      if (ended) e.stopPropagation();
      else setTimeout(takeStroke, 0);
      return;
    }
    if (e.key === 'ArrowRight' && !nextBtnEl.disabled && !ended) { e.preventDefault(); nextBtnEl.click(); }
    else if (e.key === 'ArrowLeft' && !backBtnEl.disabled) { e.preventDefault(); backBtnEl.click(); }
    e.stopPropagation();
  }, true);

  // ---- Start: where the owner left off ----
  function relayout() {
    if (ended) { syncGuides(); return; }
    if (!strokes.length) box = measureBox();
    syncGuides();
  }
  var relayoutTimer = null;
  window.addEventListener('resize', function () { clearTimeout(relayoutTimer); relayoutTimer = setTimeout(relayout, 120); });
  if (window.ResizeObserver) new ResizeObserver(function () { clearTimeout(relayoutTimer); relayoutTimer = setTimeout(relayout, 120); }).observe(canvas);

  function startSheet() {
    var i = letterStore.at;
    if (typeof i !== 'number' || i < 0) i = 0;
    if (i >= BOXES.length) {
      if (firstUndrawn() < 0) { endSheet(); return; }
      i = firstUndrawn();
    }
    showLetter(i, { fade: false });
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
    at: function () { return at; },
    ended: function () { return ended; },
    box: function () { return box && { x: box.x, y: box.y, w: box.w, h: box.h }; },
    lines: function () { return { cap: LINES.cap, x: LINES.x, base: LINES.base, desc: LINES.desc }; },
    store: function () { return JSON.parse(JSON.stringify(letterStore)); },
    grid: gridFor,
    rule: { GAP: GAP, GAIN: GAIN, CELL_W: CELL_W }
  };
})();
