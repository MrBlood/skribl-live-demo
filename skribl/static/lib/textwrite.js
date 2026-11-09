/* TEXT: words that write themselves (FUTURE.md 6ab). One module for both
 * editors: the Pad (editor_text.js) and Flip (flip.js) each hand it a few
 * hooks, and everything a person meets is here, so the two cannot drift.
 *
 * WHAT A PERSON MEETS. Text is the fifth kind in Shape's picker. Pick it and
 * Text's drawer opens under the tools, as the pen's does (the owner:
 * "Shouldn't text be a drawer? Not a popup?", then yes to A3 compact): the
 * words and Write it in one row, a Style (Yours, or + Make yours; Skribl;
 * Print; Script, each written in itself), and three tiles, Size, Thickness
 * and Speed, each saying what it holds and opening its slider under it (the
 * letters' height, kept a share of the drawing and said in its px; the
 * line's width, in the pen's own px and for the words alone; 1/4x to 16x,
 * where 1x is the hand's own pace, and how long the words will take). The
 * words show in the middle of the drawing that can be seen, inside a dashed
 * box that says Drag to move; a tap on the drawing moves them there. Write it
 * puts them in: the drawer goes and the words write themselves on the
 * canvas, a stroke at a time, at the speed chosen.
 *
 * INK, NOT TYPE. Each letter becomes pen strokes, each point with its time,
 * through the same step the pen and Shape use to add a line. So the replay,
 * a posted link and every export write the words out letter by letter with
 * the code they already have; the player never learns that text exists, and
 * a viewer never needs the font. Once written the words are ink: Undo takes
 * the whole line back, the Eraser rubs it like any line, and Mirror leaves
 * it alone (mirrored words read backwards).
 *
 * HONEST TIME. The words are written in real time on the editor's own
 * clock, so the take records exactly what the person watched. Anything they
 * do while the words are writing (a press anywhere, a key) finishes the
 * words at once, each stroke keeping the time it was due, and the editor is
 * told how far ahead of its clock they ended (`skip`), so what comes next
 * comes after them.
 *
 * THE STYLES. Print and Script are single-line plotter fonts (EMS
 * Readability and EMS Allure, SIL Open Font License; fonts/OFL.txt), timed
 * as a steady hand. Skribl is the owner's own hand and Yours is the
 * person's (Your hand, editor_letters.js, kept on this device): each letter
 * at the pace it was drawn, with a pause inside a letter held to HOLD as
 * Your hand's own line holds it. A letter a hand has not drawn yet comes in
 * Print. The lettering files are loaded the first time the drawer opens
 * (harness/tools/make_textfonts.py makes them).
 *
 * THE HOOKS (attach):
 *   canvas         the element the words are written on (its box on screen)
 *   logical()      the drawing's own size, { width, height }
 *   pen()          { color, size }: the ink as the pen would lay it
 *   begin()        the words are about to be written: one Undo step, the
 *                  take armed; returns the clock's time now, in ms
 *   draw(pts, from, to)   paint points from..to of the stroke being written
 *   stroke(pts, t0)       keep one finished stroke; each point's t is from
 *                  the start of the words, so the editor's own is t0 + t
 *   end(strokes, ms, hurried)   every stroke is kept; hurried when a press
 *                  or a key finished them early (the person is already at
 *                  the next thing)
 *   skip(ms)       the words were finished early, ms ahead of the clock
 *   say(words)     a short line to the person (the editor's own toast)
 *   drawer(open)   open or close Text's drawer through the editor's own
 *                  drawers (lib/drawers.js), so it is one of them: one open
 *                  at a time, the page scrolled to show it and home after;
 *                  the editor tells the module when its drawers closed it
 *                  (SkriblText.closed)
 *   dock()         the bar right above the drawers (the drawers' grabber
 *                  and reveal keep it under the header)
 *   active()       Text is still the tool: picking another closes the drawer
 */
(function () {
  'use strict';

  var STYLES = ['yours', 'skribl', 'print', 'script'];
  var LABEL = { yours: 'Yours', skribl: 'Skribl', print: 'Print', script: 'Script' };
  // Cap height, as a share of the drawing's shorter side, so one setting
  // suits every shape. EXACT CONTROL (the owner: "shouldn't we have control
  // of thickness on text editor, and font size?", then "all yes"): the Size
  // slider's stops are thousandths of it, SIZE_MIN to SIZE_MAX, and Small,
  // Medium and Large, the three buttons it replaced, are stops on it (a
  // choice of one kept from before comes back as that stop).
  var SIZES = { S: 0.045, M: 0.065, L: 0.095 };
  var SIZE_MIN = 0.025, SIZE_MAX = 0.2;
  // THICKNESS: the words' own line, in the pen's px. Until it is moved it is
  // the pen's size; once moved it is the words' alone, and the pen stays as
  // it was (the owner's pick: a real pen's line does not grow with the
  // letters, and a caption should not change the pen that draws).
  var WEIGHT_MIN = 1, WEIGHT_MAX = 34;
  // The speed slider's stops, 1/4x to 16x: 1x is the hand's own pace, and
  // 16x is a replay's own top speed. A WAY TO REALLY SPEED UP THE WORDS (the
  // owner: "you don't always want the text to be so slow (if you have a lot
  // of text, it takes forever)"; then "all yes" to A of the mock): at 4x a
  // 100-letter note in Skribl's hand took 21s, at 16x it takes 5. A stop
  // kept from before 6x is the same speed it was.
  var SPEEDS = [0.25, 1 / 3, 0.5, 2 / 3, 1, 1.5, 2, 3, 4, 6, 8, 12, 16];
  var SPEED_TEXT = ['¼×', '⅓×', '½×', '⅔×', '1×', '1½×', '2×', '3×', '4×', '6×', '8×', '12×', '16×'];
  var HAND_KEY = 'skribl.letters.v1';     // Your hand's store (editor_letters.js)
  var PREFS_KEY = 'skribl.text.v1';       // the drawer's last style, size, thickness and speed
  var WORDS_KEY = 'skribl.text.words';    // the words, for this tab (sessionStorage)
  var MAX_CHARS = 200;
  var HAND_OF = 92;                        // letters in a whole hand

  // ---- How a line is laid out, in cap heights ----
  var SIDE = 0.09, SPACE = 0.36;   // a hand's room either side of a letter, and between words (editor_letters.js)
  var LINE = 1.7;                  // baseline to baseline
  var WRAP = 0.9;                  // a line is at most this share of the drawing's width
  var DESC = 0.32;                 // below the baseline, for the box

  // ---- How it is timed at 1x, in ms ----
  var HOLD = 250;      // a hand's pause inside a letter is held to this
  var PEN = 7.5;       // a font's steady hand: cap heights a second along the line
  var LIFT = 60;       // the pen lifting to the next line of the same letter
  var NEXT = 110;      // ...to the next letter
  var WORD = 210;      // ...to the next word
  var GAP_LINE = 320;  // ...to the next line of words

  // Accented letters a hand writes from its own letter and accent (Your hand
  // draws five accents over a base letter). The rest come in Print.
  var ACCENT = { '´': 'áéóúý', '`': 'àèòù', '¨': 'äëöüÿ', '~': 'ãñõ', '¸': 'ç' };
  var BARE = { 'á': 'a', 'à': 'a', 'ä': 'a', 'ã': 'a', 'é': 'e', 'è': 'e', 'ë': 'e',
               'ó': 'o', 'ò': 'o', 'ö': 'o', 'õ': 'o', 'ú': 'u', 'ù': 'u', 'ü': 'u',
               'ý': 'y', 'ÿ': 'y', 'ñ': 'n', 'ç': 'c' };
  var AGAIN = 'etaoinsrh';   // letters a hand has a second try at ("e2")
  var QUOTES = { '‘': "'", '’': "'", '‚': "'", '„': '"', '″': '"', '′': "'", '…': '...' };

  var editor = null;        // the hooks (attach)
  var files = {};           // style -> lettering, once loaded
  var loading = {};         // style -> Promise
  var state = { style: null, size: SIZES.M, weight: null, speed: 4 };
  var anchor = null;        // where the words sit: the middle of their box, in drawing units
  // ...and where they were PUT (a press, a drag, the start). The words are
  // kept clear of the drawer from here each time, so a drawer that sits on a
  // phone's keyboard for a while moves them only while it is in the way:
  // they come back down when there is room again.
  var want = null;
  var plan = null;          // the words as strokes, at the anchor (0, 0)
  var job = null;           // the words writing themselves now

  // ---- The lettering ----
  function sheetEl() { return document.getElementById('txSheet'); }
  function urlOf(style) {
    var s = sheetEl();
    return s ? s.getAttribute('data-' + style) : null;
  }
  function undelta(a, w) {
    var out = [], prev = [], i, j;
    for (j = 0; j < w; j++) prev.push(0);
    for (i = 0; i + w <= a.length; i += w) {
      var row = [];
      for (j = 0; j < w; j++) row.push(a[i + j] + prev[j]);
      out.push(row);
      prev = row;
    }
    return out;
  }
  // A lettering file as glyphs: { lines: [[[x, y, t, w], ...], ...], adv }
  // in cap heights, y up from the baseline; a hand's x from its ink centre.
  function decode(doc) {
    var u = doc.u || 1000, g = {}, k;
    for (k in doc.g) {
      if (!Object.prototype.hasOwnProperty.call(doc.g, k)) continue;
      var raw = doc.g[k], lines = [], adv = null, start = 0;
      if (doc.kind === 'font') { adv = raw[0] / u; start = 1; }
      for (var i = start; i < raw.length; i++) {
        var pts = undelta(raw[i], doc.kind === 'hand' ? 3 : 2).map(function (p) {
          return [p[0] / u, p[1] / u, doc.kind === 'hand' ? p[2] : null, 1];
        });
        if (pts.length) lines.push(pts);
      }
      g[k] = { lines: lines, adv: adv, timed: doc.kind === 'hand' };
    }
    return { kind: doc.kind, name: doc.name, x: (doc.x || 0.7 * u) / u, adv: (doc.adv || 0) / u, g: g };
  }
  function load(style) {
    if (style === 'yours') return Promise.resolve(readHand());
    if (files[style]) return Promise.resolve(files[style]);
    if (loading[style]) return loading[style];
    var url = urlOf(style);
    if (!url || typeof fetch !== 'function') return Promise.resolve(null);
    loading[style] = fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (doc) {
      files[style] = decode(doc);
      return files[style];
    }).catch(function () {
      delete loading[style];   // a later open tries again
      return null;
    });
    return loading[style];
  }

  // YOUR HAND, read from Your hand's store each time it is asked for, so a
  // letter drawn again since is the one written. Normalised as Your hand
  // normalises it (editor_letters.js norm): cap heights, y up from the
  // letter's baseline, x from its ink centre, t as drawn, and the width each
  // point was drawn at, against the hand's usual width.
  function readHand() {
    var s = null;
    try { s = JSON.parse(localStorage.getItem(HAND_KEY) || 'null'); } catch (e) { s = null; }
    if (!s || s.v !== 1 || !s.g || typeof s.g !== 'object') return null;
    var g = {}, n = 0, widths = [], k;
    for (k in s.g) {
      if (!Object.prototype.hasOwnProperty.call(s.g, k)) continue;
      var L = s.g[k];
      if (!L || !L.p || !L.n || !L.b || !L.l || !L.p.length) continue;
      var cap = (L.l[2] - L.l[0]) * L.b[3], base = L.b[1] + L.l[2] * L.b[3];
      if (!(cap > 0)) continue;
      var lo = Infinity, hi = -Infinity, i, j, q = 0;
      for (i = 0; i < L.p.length; i++) { lo = Math.min(lo, L.p[i][0]); hi = Math.max(hi, L.p[i][0]); }
      var mid = (lo + hi) / 2, lines = [];
      for (i = 0; i < L.n.length; i++) {
        var line = [];
        for (j = 0; j < L.n[i] && q < L.p.length; j++, q++) {
          var p = L.p[q];
          line.push([(p[0] - mid) / cap, (base - p[1]) / cap, p[3], p[2] / cap]);
          widths.push(p[2] / cap);
        }
        if (line.length) lines.push(line);
      }
      if (lines.length) { g[k] = { lines: lines, adv: null, timed: true }; n++; }
    }
    if (!n) return null;
    // The width a point was drawn at against the hand's middle width: a
    // hand drawn with pressure keeps its swells and tapers at any pen size.
    widths.sort(function (a, b) { return a - b; });
    var w0 = widths[widths.length >> 1] || 1;
    for (k in g) g[k].lines.forEach(function (line) {
      line.forEach(function (p) { p[3] = w0 > 0 ? Math.max(0.35, Math.min(1.8, p[3] / w0)) : 1; });
    });
    var lines0 = s.l || [0.16, 0.334, 0.74, 0.94];
    return { kind: 'hand', name: 'Yours', count: n,
             x: (0.74 - 0.334) / (0.74 - 0.16), adv: 0, g: g, lines: lines0 };
  }
  function handCount() {
    var h = readHand();
    return h ? h.count : 0;
  }

  // ---- A letter in a style ----
  function bounds(lines) {
    var lo = Infinity, hi = -Infinity;
    lines.forEach(function (l) { l.forEach(function (p) { lo = Math.min(lo, p[0]); hi = Math.max(hi, p[0]); }); });
    return lo <= hi ? { lo: lo, hi: hi } : { lo: 0, hi: 0 };
  }
  function shifted(lines, dx, dy, dt) {
    return lines.map(function (l) {
      return l.map(function (p) { return [p[0] + dx, p[1] + dy, p[2] == null ? null : p[2] + (dt || 0), p[3]]; });
    });
  }
  // What `ch` looks like in `font`, or null. A hand's own letter first, then
  // one it can make (an accent over its own letter), else nothing: the
  // caller falls back to Print. `n` counts the times this letter has come,
  // so a hand's second try takes every other turn.
  function handGlyph(font, ch, n) {
    var g = font.g, id = ch;
    if (AGAIN.indexOf(ch) >= 0 && n % 2 === 1 && g[ch + '2']) id = ch + '2';
    if (g[id]) return { lines: g[id].lines, timed: true };
    var lower = ch.toLowerCase(), bare = BARE[lower];
    if (!bare) return null;
    var accent = null, a;
    for (a in ACCENT) if (ACCENT[a].indexOf(lower) >= 0) accent = a;
    var base = ch === lower ? bare : bare.toUpperCase();
    if (!g[base] || !accent || !g[accent]) return null;
    // The accent was drawn over a small letter; over a capital it sits a
    // capital's height up instead (a cedilla stays under).
    var up = (ch !== lower && accent !== '¸') ? 1 - font.x : 0;
    var b = g[base].lines, ab = bounds(g[accent].lines);
    var lastT = 0;
    b.forEach(function (l) { l.forEach(function (p) { if (p[2] != null) lastT = Math.max(lastT, p[2]); }); });
    var acc = shifted(g[accent].lines, -(ab.lo + ab.hi) / 2, up, lastT + LIFT);
    return { lines: b.concat(acc), timed: true };
  }
  function fontGlyph(font, ch) {
    var g = font.g[ch];
    return g ? { lines: g.lines, adv: g.adv, timed: false } : null;
  }

  // ---- The words, laid out ----
  // One line of words: each letter with its lines placed along the line,
  // x from the line's start, in cap heights, and the line's width.
  function layoutLine(text, font, print) {
    var x = 0, out = [], seen = {}, skipped = 0;
    var hand = font.kind === 'hand';
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === ' ') { x += hand ? SPACE : (fontGlyph(font, ' ') || { adv: font.adv }).adv; out.push({ space: true }); continue; }
      var n = seen[ch] || 0;
      seen[ch] = n + 1;
      var gl = hand ? handGlyph(font, ch, n) : fontGlyph(font, ch);
      var fromPrint = false;
      if (!gl && hand && print) { gl = fontGlyph(print, ch); fromPrint = !!gl; }
      if (!gl) { skipped++; continue; }
      if (hand) {
        // A hand's letters, and Print's when it stands in, are spaced by
        // their ink, as Your hand's own line spaces them.
        var b = bounds(gl.lines);
        if (!gl.lines.length) b = { lo: 0, hi: 0.3 };
        x += SIDE;
        out.push({ ch: ch, lines: shifted(gl.lines, x - b.lo, 0, 0), timed: gl.timed && !fromPrint });
        x += (b.hi - b.lo) + SIDE;
      } else {
        out.push({ ch: ch, lines: shifted(gl.lines, x, 0, 0), timed: false });
        x += gl.adv;
      }
    }
    return { glyphs: out, width: x, skipped: skipped };
  }
  // Words into lines no wider than `maxW` cap heights, breaking between
  // words, and inside a word only when it is wider than a line by itself.
  function wrap(text, font, print, maxW) {
    var words = text.split(' '), lines = [], cur = '';
    function fits(s) { return layoutLine(s, font, print).width <= maxW; }
    words.forEach(function (w) {
      var tryLine = cur ? cur + ' ' + w : w;
      if (!cur || fits(tryLine)) { cur = tryLine; }
      else { lines.push(cur); cur = w; }
      while (cur.length > 1 && !fits(cur) && cur.indexOf(' ') < 0) {
        var k = cur.length - 1;
        while (k > 1 && !fits(cur.slice(0, k))) k--;
        lines.push(cur.slice(0, k));
        cur = cur.slice(k);
      }
    });
    if (cur || !lines.length) lines.push(cur);
    return lines;
  }
  function clean(text) {
    var out = '';
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      out += QUOTES[c] != null ? QUOTES[c] : (c === '\t' || c === '\n' ? ' ' : c);
    }
    return out.replace(/ +/g, ' ').trim();
  }

  // ---- The words as strokes ----
  // The 1x clock for one letter's lines: a hand's own times, a pause held to
  // HOLD; a font's, a steady pen that eases in and out of each line.
  var EASE = (function () {
    // position along a line against time, half steady and half eased, as
    // a table to read backwards: when is the pen this far along?
    var n = 64, s = [];
    for (var i = 0; i <= n; i++) {
      var u = i / n;
      s.push(0.5 * u + 0.5 * (1 - Math.cos(Math.PI * u)) / 2);
    }
    return function (f) {
      if (f <= 0) return 0;
      if (f >= 1) return 1;
      var k = 1;
      while (k < n && s[k] < f) k++;
      var a = s[k - 1], b = s[k];
      return (k - 1 + (b > a ? (f - a) / (b - a) : 0)) / n;
    };
  })();
  function lineLen(l) {
    var L = 0;
    for (var i = 1; i < l.length; i++) L += Math.hypot(l[i][0] - l[i - 1][0], l[i][1] - l[i - 1][1]);
    return L;
  }
  function timeGlyph(gl, T) {
    // Returns lines of [x, y, t, w] with t from the words' start, and the end.
    var out = [], t = T, prevEnd = null;
    if (gl.timed) {
      var last = null, play = T;
      gl.lines.forEach(function (l) {
        var line = [];
        l.forEach(function (p) {
          var raw = p[2] == null ? 0 : p[2];
          if (last != null) play += Math.min(HOLD, Math.max(0, raw - last));
          last = raw;
          line.push([p[0], p[1], play, p[3]]);
        });
        out.push(line);
      });
      return { lines: out, end: play };
    }
    gl.lines.forEach(function (l, i) {
      if (i) t += LIFT + (prevEnd ? Math.hypot(l[0][0] - prevEnd[0], l[0][1] - prevEnd[1]) / (PEN * 2) * 1000 : 0);
      var L = lineLen(l), dur = L / PEN * 1000 + 30, acc = 0, line = [];
      l.forEach(function (p, k) {
        if (k) acc += Math.hypot(p[0] - l[k - 1][0], p[1] - l[k - 1][1]);
        line.push([p[0], p[1], t + dur * (L > 0 ? EASE(acc / L) : 0), p[3]]);
      });
      t += dur;
      prevEnd = l[l.length - 1];
      out.push(line);
    });
    return { lines: out, end: t };
  }
  // Points no further apart than `step` drawing units, the time between two
  // kept points shared out along the way, so the pen moves smoothly.
  function densify(pts, step) {
    var out = [pts[0]];
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i], d = Math.hypot(b.x - a.x, b.y - a.y);
      var n = Math.floor(d / step);
      for (var k = 1; k <= n; k++) {
        var f = k / (n + 1);
        out.push({ x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f,
                   t: a.t + (b.t - a.t) * f, w: a.w + (b.w - a.w) * f });
      }
      out.push(b);
    }
    return out;
  }
  /* THE WORDS, READY TO WRITE. text, style and size as the drawer has them;
   * `lettering` the style's file (and Print, for a hand's missing letters);
   * `canvas` the drawing's size; `pen` the ink. Points are in drawing units
   * from the middle of the words' box, so moving the words moves nothing
   * else; `ms` is how long they take at this speed. */
  // A size as a share of the drawing's shorter side: a number, or the name
  // of a stop kept from before the slider (S, M, L).
  function shareOf(size) {
    var v = typeof size === 'number' ? size : (SIZES[size] || SIZES.M);
    return Math.max(SIZE_MIN, Math.min(SIZE_MAX, v));
  }
  function weightOf(w) { return Math.max(WEIGHT_MIN, Math.min(WEIGHT_MAX, Math.round(w) || WEIGHT_MIN)); }
  function makePlan(o) {
    var font = o.font, print = o.print || null;
    if (!font) return null;
    var text = clean(o.text || '').slice(0, MAX_CHARS);
    var short = Math.min(o.canvas.width, o.canvas.height);
    var cap = Math.max(6, shareOf(o.size) * short);
    var maxW = (WRAP * o.canvas.width) / cap;
    var rows = text ? wrap(text, font, print, maxW) : [];
    var speed = SPEEDS[o.speed] || 1;
    var strokes = [], T = 0, skipped = 0, top = -1, bottom = (rows.length - 1) * LINE + DESC;
    var widest = 0;
    var laid = rows.map(function (row) { var r = layoutLine(row, font, print); widest = Math.max(widest, r.width); skipped += r.skipped; return r; });
    // The block's middle, between the first line's cap height and the last
    // line's descenders, is the anchor; each line is centred on it.
    var midY = (top + bottom) / 2;
    var step = Math.max(1.2, cap * 0.035);
    laid.forEach(function (r, li) {
      if (li) T += GAP_LINE;
      var y0 = li * LINE - midY, x0 = -r.width / 2;
      r.glyphs.forEach(function (gl, gi) {
        if (gl.space) { T += WORD - NEXT; return; }
        var timed = timeGlyph(gl, T);
        timed.lines.forEach(function (l) {
          var pts = l.map(function (p) {
            return { x: (x0 + p[0]) * cap, y: (y0 - p[1]) * cap, t: p[2], w: p[3] };
          });
          if (pts.length === 1) pts.push({ x: pts[0].x, y: pts[0].y, t: pts[0].t, w: pts[0].w });
          strokes.push(densify(pts, step));
        });
        T = timed.end + NEXT;
      });
    });
    var size = o.pen ? o.pen.size : 4, color = o.pen ? o.pen.color : '#000';
    var box = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity }, end = 0;
    strokes = strokes.map(function (pts) {
      return pts.map(function (p) {
        var t = Math.round(p.t / speed);
        end = Math.max(end, t);
        box.x0 = Math.min(box.x0, p.x); box.x1 = Math.max(box.x1, p.x);
        box.y0 = Math.min(box.y0, p.y); box.y1 = Math.max(box.y1, p.y);
        return { x: p.x, y: p.y, t: t, size: Math.round(size * p.w * 100) / 100, color: color };
      });
    });
    // The box the words are moved by is the lines', not the ink's, so it
    // does not jump as letters with tails come and go.
    var half = widest * cap / 2, pad = size / 2 + 2;
    var lineBox = { x0: -half - pad, x1: half + pad, y0: (top - midY) * cap - pad, y1: (bottom - midY) * cap + pad };
    if (strokes.length) {
      lineBox.x0 = Math.min(lineBox.x0, box.x0 - pad); lineBox.x1 = Math.max(lineBox.x1, box.x1 + pad);
      lineBox.y0 = Math.min(lineBox.y0, box.y0 - pad); lineBox.y1 = Math.max(lineBox.y1, box.y1 + pad);
    }
    return { text: text, strokes: strokes, ms: end, cap: cap, box: lineBox, skipped: skipped,
             points: strokes.reduce(function (a, s) { return a + s.length; }, 0) };
  }

  // ---- The words writing themselves ----
  // `run` paints each point when it falls due and keeps each stroke when its
  // last point has; `finish` keeps the rest at once.
  function write(p, at) {
    if (!editor || !p || !p.strokes.length) return null;
    var t0 = editor.begin();
    var strokes = p.strokes.map(function (s) {
      return s.map(function (q) { return { x: q.x + at.x, y: q.y + at.y, t: q.t, size: q.size, color: q.color }; });
    });
    var j = { si: 0, pi: 0, start: performance.now(), raf: 0, done: false };
    function advance(e) {
      while (j.si < strokes.length) {
        var pts = strokes[j.si], k = j.pi;
        while (k < pts.length && pts[k].t <= e) k++;
        if (k > j.pi) { editor.draw(pts, j.pi, k - 1); j.pi = k; }
        if (j.pi < pts.length) return;
        editor.stroke(pts, t0);
        j.si++; j.pi = 0;
      }
    }
    // HURRIED: finished by a press or a key (finish), not written out. The
    // editor is told, since the person is already at the next thing.
    function done(hurried) {
      if (j.done) return;
      j.done = true;
      cancelAnimationFrame(j.raf);
      unguard();
      job = null;
      document.body.classList.remove('text-writing');
      editor.end(strokes.length, p.ms, !!hurried);
    }
    function tick(now) {
      if (j.done) return;
      advance(now - j.start);
      if (j.si >= strokes.length) done(false);
      else j.raf = requestAnimationFrame(tick);
    }
    j.finish = function () {
      if (j.done) return;
      var ahead = p.ms - (performance.now() - j.start);
      advance(Infinity);
      if (ahead > 0 && editor.skip) editor.skip(Math.round(ahead));
      done(true);
    };
    job = j;
    document.body.classList.add('text-writing');
    guard();
    j.raf = requestAnimationFrame(tick);
    return j;
  }
  // While the words write, the next thing the person does finishes them
  // first, before it happens: a press anywhere, or a key.
  function onAnything() { if (job) job.finish(); }
  function guard() {
    document.addEventListener('pointerdown', onAnything, true);
    document.addEventListener('keydown', onAnything, true);
  }
  function unguard() {
    document.removeEventListener('pointerdown', onAnything, true);
    document.removeEventListener('keydown', onAnything, true);
  }

  // ---- Where the words are on screen ----
  // The drawing's box on screen, from the canvas's own box (a zoom scales
  // it, a border is inside it), and the scale from drawing units to it.
  function screenBox() {
    var c = editor && editor.canvas;
    if (!c) return null;
    var r = c.getBoundingClientRect(), lg = editor.logical();
    if (!r.width || !lg || !lg.width) return null;
    var cs = getComputedStyle(c), k0 = c.offsetWidth ? r.width / c.offsetWidth : 1;
    var bl = (parseFloat(cs.borderLeftWidth) || 0) * k0, bt = (parseFloat(cs.borderTopWidth) || 0) * k0;
    var w = r.width - bl - (parseFloat(cs.borderRightWidth) || 0) * k0;
    var h = r.height - bt - (parseFloat(cs.borderBottomWidth) || 0) * k0;
    return { left: r.left + bl, top: r.top + bt, k: w / lg.width, ky: h / lg.height, lg: lg };
  }
  // Keep the words inside the drawing and, while the drawer sits on a phone's
  // keyboard, above it. Under the tools it covers none of the drawing.
  function clampAnchor(a) {
    var lg = editor.logical(), b = plan ? plan.box : { x0: 0, x1: 0, y0: 0, y1: 0 };
    var x = a.x, y = a.y;
    var minX = -b.x0, maxX = lg.width - b.x1, minY = -b.y0, maxY = lg.height - b.y1;
    x = minX > maxX ? lg.width / 2 : Math.max(minX, Math.min(maxX, x));
    var sb = screenBox(), sh = sheetEl();
    if (sb && sh && !sh.hidden && sh.classList.contains('typing')) {
      // Where the drawer RESTS on the keyboard, from its layout box (a box
      // being moved paints lower, and words kept above that would end under
      // it; lib/sheetswipe.js measures a sheet the same way).
      var limit = (layoutTop(sh) - 12 - sb.top) / sb.ky - b.y1;
      if (limit < maxY) maxY = Math.max(minY, limit);
    }
    y = minY > maxY ? Math.max(lg.height / 2, minY) : Math.max(minY, Math.min(maxY, y));
    return { x: x, y: y };
  }
  function layoutTop(s) {
    var op = s.offsetParent;
    return (op ? op.getBoundingClientRect().top + op.clientTop : 0) + s.offsetTop;
  }

  // ---- The drawer steps aside ----
  // WHILE THE WORDS ARE DRAGGED THE DRAWER STEPS ASIDE (the owner, of the
  // drawer: "While you drag your words, the drawer drops down and comes back
  // when you let go", yes). On a phone a drawer slides the page up to show
  // itself, so the top of the drawing sits under the header: once a move of
  // the words is a drag, the drawer is unseen and untouched (its room kept,
  // so nothing jumps) and the page glides home, the words staying under the
  // finger as the drawing moves, so they reach the whole drawing. Let go and
  // the drawer is back, the page gliding to show it again, no further than
  // the words and Write it need (comeBack). With Reduce Motion each is simply
  // where it goes.
  var veiled = false;
  function still() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function veil(on) {
    var s = els && els.sheet, D = window.SkriblDrawerDetent;
    if (!s || on === veiled) return;
    veiled = on;
    s.classList.toggle('tx-veiled', on);
    var how = still() ? 'auto' : 'smooth';
    if (on) {
      if (document.activeElement === els.field) els.field.blur();
      // The whole drawing on screen, as Play shows it (lib/drawerdetent.js
      // revealTop), which also calls off the drawer's re-asserts of where it
      // opened: a drag begun within a second of the drawer opening had them
      // carry the page back down under the finger, 260px in one frame.
      if (D && D.revealTop) D.revealTop(editor && editor.canvas, how);
      else window.scrollTo({ top: 0, behavior: how });
      return;
    }
    if (isOpen()) comeBack(how);
  }
  // The drawer on screen again (after a drag, or the keyboard going): its end
  // at the foot of what can be seen, the words kept clear of the header, and
  // its first row, the words and Write it, on screen whatever (lib/drawerdetent.js).
  function comeBack(how) {
    var s = els && els.sheet, D = window.SkriblDrawerDetent;
    if (!s || !D || !D.revealPanelEnd) return;
    var dock = editor && editor.dock ? editor.dock() : null;
    D.revealPanelEnd(s, how || (still() ? 'auto' : 'smooth'), dock, els.place.hidden ? null : els.place, s.querySelector('.tx-top'));
  }

  // ---- The drawer ----
  var $ = function (id) { return document.getElementById(id); };
  var els = null;
  var drag = null;          // the words under a finger: where it is, and where on the words it holds them
  function bind() {
    if (els) return els;
    var s = sheetEl();
    if (!s) return null;
    els = { sheet: s, field: $('txField'), styles: $('txStyles'), under: $('txUnder'),
            note: $('txNote'), edit: $('txEdit'), size: $('txSize'), sizeOut: $('txSizeOut'),
            weight: $('txWeight'), weightOut: $('txWeightOut'), speed: $('txSpeed'),
            speedOut: $('txSpeedOut'), hint: $('txSpeedHint'), go: $('txGo'),
            skip: $('txSkip'), place: $('txPlace'), preview: $('txPreview'), spacer: $('txSpacer'),
            tiles: $('txTiles'), sizeTile: $('txSizeTile'), weightTile: $('txWeightTile'), speedTile: $('txSpeedTile') };
    readPrefs();
    els.field.setAttribute('maxlength', String(MAX_CHARS));
    els.field.addEventListener('input', function () {
      try { sessionStorage.setItem(WORDS_KEY, els.field.value); } catch (e) {}
      refresh();
    });
    els.field.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      // THE KEYBOARD'S DONE KEY PUTS IT AWAY (the owner, on the iPhone: the
      // blue tick wrote the words at once, before they were placed). Writing
      // is the Write it button; on a desk, with no keyboard to put away,
      // Enter is Write it.
      if (touchFirst()) els.field.blur(); else go();
    });
    els.field.addEventListener('focus', function () { fitKeyboard(); setTimeout(fitKeyboard, 120); });
    els.field.addEventListener('blur', function () { fitKeyboard(); setTimeout(fitKeyboard, 120); });
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', fitKeyboard);
      window.visualViewport.addEventListener('scroll', fitKeyboard);
    }
    s.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
    });
    els.styles.addEventListener('click', function (e) {
      var b = e.target.closest('[data-style]');
      if (!b) return;
      var st = b.getAttribute('data-style');
      if (st === 'yours' && !handCount()) { toHand(); return; }
      state.style = st;
      keepPrefs();
      syncStyles();
      refresh();
    });
    if (els.edit) els.edit.addEventListener('click', function (e) { e.preventDefault(); toHand(); });
    els.size.addEventListener('input', function () {
      state.size = shareOf((parseInt(els.size.value, 10) || 0) / 1000);
      keepPrefs();
      refresh();
    });
    // Moved, the words' thickness is theirs: the pen stays as it was.
    els.weight.addEventListener('input', function () {
      state.weight = weightOf(parseInt(els.weight.value, 10));
      keepPrefs();
      refresh();
    });
    els.speed.addEventListener('input', function () {
      state.speed = Math.max(0, Math.min(SPEEDS.length - 1, parseInt(els.speed.value, 10) || 0));
      keepPrefs();
      refresh();
    });
    if (typeof window.addSliderNudgers === 'function') {
      window.addSliderNudgers(els.size, { step: 5 });
      window.addSliderNudgers(els.weight, { step: 1 });
      window.addSliderNudgers(els.speed, { step: 1 });
    }
    if (els.tiles) {
      Array.prototype.forEach.call(els.tiles.querySelectorAll('.dp-tile'), function (t) {
        t.addEventListener('click', function () { showTile(t.getAttribute('data-dp')); });
      });
    }
    els.go.addEventListener('click', go);
    // A press on Write it while the words are typed keeps the field's focus
    // until the click: the keyboard going first would bring the drawer back
    // under the finger, and the press would land on whatever moved there.
    els.go.addEventListener('mousedown', function (e) { if (document.activeElement === els.field) e.preventDefault(); });
    // The drawers' grabber: a tap closes Text, a pull down closes it, as
    // every drawer's does (lib/drawerdetent.js).
    if (window.SkriblDrawerDetent) {
      window.SkriblDrawerDetent.attach(s, { close: close, dock: editor && editor.dock ? editor.dock() : null });
    }
    // The words move with a finger, a pen or a mouse, before they are ink;
    // once the move is a drag the drawer steps aside (above), and it is back
    // when the words are let go. The words stay where the finger holds them,
    // also while the page glides home under it (followLoop).
    els.place.addEventListener('pointerdown', function (e) {
      var sb = screenBox();
      if (!anchor || !sb) return;
      e.preventDefault();
      try { els.place.setPointerCapture(e.pointerId); } catch (_) {}
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY, moved: false,
               dx: (e.clientX - sb.left) / sb.k - anchor.x, dy: (e.clientY - sb.top) / sb.ky - anchor.y };
      els.place.classList.add('dragging');
    });
    els.place.addEventListener('pointermove', function (e) {
      if (!drag || e.pointerId !== drag.id) return;
      if (!drag.moved) {
        if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < 4) return;
        drag.moved = true;
        veil(true);
      }
      drag.px = e.clientX; drag.py = e.clientY;
      dragTo();
    });
    var endDrag = function (e) {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      var was = drag;
      drag = null;
      els.place.classList.remove('dragging');
      if (was.moved) veil(false);
    };
    els.place.addEventListener('pointerup', endDrag);
    els.place.addEventListener('pointercancel', endDrag);
    window.addEventListener('resize', function () { fitKeyboard(); if (isOpen() && want) { anchor = clampAnchor(want); position(); } });
    // The tiles' pictures follow the tiles' width and the theme: the tile's
    // grey and ground change with it, the ground over the tile's .15s fade,
    // so once now and once after it.
    window.addEventListener('resize', function () { paintTiles(); });
    var themed = function () { paintTiles(true); setTimeout(function () { paintTiles(true); }, 220); };
    try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themed); } catch (e) {}
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(themed).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    }
    return els;
  }
  // The words where the finger holds them, on the drawing as it is now.
  function dragTo() {
    var sb = screenBox();
    if (!drag || !sb) return;
    want = { x: (drag.px - sb.left) / sb.k - drag.dx, y: (drag.py - sb.top) / sb.ky - drag.dy };
    anchor = clampAnchor(want);
    position();
  }

  // ---- Size, Thickness and Speed: the tiles ----
  // As the pen drawer's (lib/drawtiles.js): a tap opens the tile's slider
  // right under it, joined to it; the same tile, or another, closes it. Each
  // unfolds and folds; with Reduce Motion it is simply there, or gone. The
  // drawer is told ('drawtile'), so on a phone it brings the slider on screen
  // as the pen's does (lib/drawerdetent.js).
  var tileOpen = null, folding = null;
  function panelOf(k) { return k && els.tiles ? els.tiles.querySelector('.dp-panel[data-dp="' + k + '"]') : null; }
  function finishFold() {
    if (!folding) return;
    var p = folding; folding = null;
    clearTimeout(p.__foldT);
    p.classList.remove('dp-folding');
    if (p.getAnimations) p.getAnimations().forEach(function (a) { a.cancel(); });
    var drop = function () {
      p.hidden = true;
      if (tileOpen !== p.getAttribute('data-dp')) {
        var t = els.tiles.querySelector('.dp-tile[data-dp="' + p.getAttribute('data-dp') + '"]');
        if (t) t.classList.remove('dp-open');
      }
      if (!tileOpen) els.tiles.removeAttribute('data-col');
    };
    var D = window.SkriblDrawerDetent;
    if (D && D.shrinkGently && !still()) D.shrinkGently(els.sheet, drop); else drop();
  }
  function showTile(k, instant) {
    if (!els || !els.tiles) return;
    var was = tileOpen;
    if (was === k) k = null;
    tileOpen = k;
    if (folding) finishFold();
    var tiles = els.tiles.querySelectorAll('.dp-tile'), old = panelOf(was), now = panelOf(k);
    Array.prototype.forEach.call(tiles, function (t, i) {
      var on = t.getAttribute('data-dp') === k;
      t.setAttribute('aria-expanded', String(on));
      if (on) { t.classList.add('dp-open'); els.tiles.setAttribute('data-col', String(i)); }
      else if (t.getAttribute('data-dp') !== was || k) t.classList.remove('dp-open');
    });
    if (old && k) old.hidden = true;   // one tile for another: the new one unfolds where the old one was
    if (now) {
      now.hidden = false;
      if (!instant && !still() && now.animate) {
        now.animate([{ opacity: 0, transform: 'scaleY(.92)' }, { opacity: 1, transform: 'none' }],
                    { duration: 220, easing: 'cubic-bezier(.2, .8, .2, 1)' });
      }
    }
    if (old && !k) {
      folding = old;
      if (instant || still() || !old.animate) finishFold();
      else {
        old.classList.add('dp-folding');
        old.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scaleY(.94)' }],
                    { duration: 180, easing: 'ease-in', fill: 'forwards' });
        old.__foldT = setTimeout(finishFold, 200);
      }
    }
    if (!instant) els.sheet.dispatchEvent(new CustomEvent('drawtile', { detail: { open: k } }));
  }
  function readPrefs() {
    try {
      var p = JSON.parse(localStorage.getItem(PREFS_KEY) || 'null');
      if (p && STYLES.indexOf(p.style) >= 0) state.style = p.style;
      if (p && typeof p.size === 'string' && SIZES[p.size]) state.size = SIZES[p.size];
      else if (p && typeof p.size === 'number' && p.size >= SIZE_MIN && p.size <= SIZE_MAX) state.size = p.size;
      if (p && p.weight === (p.weight | 0) && p.weight >= WEIGHT_MIN && p.weight <= WEIGHT_MAX) state.weight = p.weight;
      if (p && p.speed >= 0 && p.speed < SPEEDS.length) state.speed = p.speed | 0;
    } catch (e) {}
  }
  function keepPrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify({ style: state.style, size: state.size, weight: state.weight, speed: state.speed })); }
    catch (e) {}
  }
  // The style a person meets: theirs once they have a hand, else Skribl, and
  // whatever they last chose, when it is still there to choose.
  function styleNow() {
    var made = handCount() > 0;
    if (state.style === 'yours' && !made) return 'skribl';
    if (state.style) return state.style;
    return made ? 'yours' : 'skribl';
  }

  // ---- Each style written in itself ----
  var SVGNS = 'http://www.w3.org/2000/svg';
  function labelSVG(word, font, print) {
    var r = layoutLine(word, font, print);
    if (!r.glyphs.length) return null;
    var d = '', lo = Infinity, hi = -Infinity, top = Infinity, bot = -Infinity;
    r.glyphs.forEach(function (g) {
      if (g.space) return;
      g.lines.forEach(function (l) {
        l.forEach(function (p, i) {
          d += (i ? 'L' : 'M') + p[0].toFixed(3) + ' ' + (-p[1]).toFixed(3);
          lo = Math.min(lo, p[0]); hi = Math.max(hi, p[0]); top = Math.min(top, -p[1]); bot = Math.max(bot, -p[1]);
        });
        if (l.length === 1) d += 'l0.001 0';
      });
    });
    var svg = document.createElementNS(SVGNS, 'svg');
    var pad = 0.08, y0 = Math.min(top, -1) - pad, y1 = Math.max(bot, 0.25) + pad;
    svg.setAttribute('viewBox', (lo - pad).toFixed(3) + ' ' + y0.toFixed(3) + ' ' + (hi - lo + 2 * pad).toFixed(3) + ' ' + (y1 - y0).toFixed(3));
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    var path = document.createElementNS(SVGNS, 'path');
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.7');
    path.setAttribute('vector-effect', 'non-scaling-stroke');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path);
    return svg;
  }
  function syncStyles() {
    var cur = styleNow(), made = handCount();
    var print = files.print || null;
    Array.prototype.forEach.call(els.styles.querySelectorAll('[data-style]'), function (b) {
      var st = b.getAttribute('data-style'), on = st === cur;
      var font = st === 'yours' ? (made ? readHand() : null) : files[st];
      var face = st === 'yours' && !made ? 'make' : (font ? 'drawn' : 'word');
      b.classList.toggle('on', on);
      // + Make yours is a way to somewhere, not a choice: it says nothing
      // about being pressed.
      if (face === 'make') b.removeAttribute('aria-pressed');
      else b.setAttribute('aria-pressed', String(on));
      if (b.getAttribute('data-face') === face && face !== 'drawn') return;
      b.setAttribute('data-face', face);
      b.textContent = '';
      if (face === 'make') {
        b.setAttribute('aria-label', 'Make your own hand');
        b.title = 'Make your own hand in about 10 minutes';
        b.innerHTML = '<span class="tx-make"><b aria-hidden="true">+</b>Make yours</span>';
        return;
      }
      b.removeAttribute('title');
      b.setAttribute('aria-label', LABEL[st]);
      var svg = font ? labelSVG(LABEL[st], font, print) : null;
      if (svg) b.appendChild(svg);
      else { var w = document.createElement('span'); w.className = 'tx-word'; w.textContent = LABEL[st]; b.appendChild(w); }
    });
    // With a hand made, how many of its letters and the way back to them; with
    // none, + Make yours is the way there, and the drawer stays short.
    els.under.hidden = !made;
    els.note.textContent = made ? 'Your hand, ' + made + ' of ' + HAND_OF + ' letters' : '';
    els.hint.textContent = cur === 'yours' ? '1× is your own speed'
      : cur === 'skribl' ? '1× is Skribl’s speed' : '1× is a steady hand';
  }
  // The two dials, and what they say for this drawing: the letters' height
  // in its px (the share it is kept as suits every shape, the px is what it
  // is here) and the line's width, the pen's until the words have their own.
  function thickness() {
    if (state.weight != null) return state.weight;
    var pen = editor ? editor.pen() : null;
    return weightOf(pen ? pen.size : 4);
  }
  function syncSize() {
    var lg = editor ? editor.logical() : null, short = lg ? Math.min(lg.width, lg.height) : 0;
    var px = Math.round(state.size * short), w = thickness();
    els.size.value = String(Math.round(state.size * 1000));
    els.size.setAttribute('aria-valuetext', px + ' pixels tall');
    if (els.sizeOut) els.sizeOut.textContent = px + 'px';
    els.weight.value = String(w);
    els.weight.setAttribute('aria-valuetext', w + ' pixels');
    if (els.weightOut) els.weightOut.textContent = w + 'px';
    // ...and the tiles say the same, before they are opened.
    if (els.sizeTile) els.sizeTile.textContent = px + 'px';
    if (els.weightTile) els.weightTile.textContent = w + 'px';
    if (els.speedTile) els.speedTile.textContent = SPEED_TEXT[state.speed];
    paintTiles();
  }

  /* ---- The tiles' pictures ----
   * EACH TILE DRAWS WHAT IT HOLDS, as the pen drawer's tiles do
   * (lib/drawtiles.js), in the pen's ink. The owner, of the first pictures
   * (fixed marks: an Aa, three bars and a dial): "Size thickness speed icons
   * aren't great. Thickness is okay, but speed is not great", then "All yes"
   * to the second round's picks:
   *   Size       three A's in the words' own style: a small and a large at
   *              the ends, faint, and the words' own between them, as tall as
   *              the Size, as the pen drawer's Size shows its dots.
   *   Thickness  a line as thick as the words' own line.
   *   Speed      a snail and a rabbit with a little slider between them, its
   *              dot at the speed: a quarter by the snail, 16x by the rabbit
   *              (Apple puts a tortoise and a hare at the ends of the
   *              iPhone's speaking-speed slider; Skribl's slow one is a snail).
   * The snail, the rabbit and the slider's track are the tile's own grey;
   * what holds a value is the ink, at full strength (a see-through ink drawn
   * in short pieces would bead where they meet). An ink too near the tile's
   * ground to see is drawn over a soft edge, as the pen drawer draws a pale
   * one. A closed drawer's canvases have no size and are painted when it
   * opens (open() refreshes once it is shown). */
  /*! The snail and the rabbit below are Lucide icons, SCALED (paths otherwise
   *  unaltered; the snail's circle written as a path): lucide-static 1.37.0,
   *  ISC (c) 2026 Lucide Icons and Contributors,
   *  https://github.com/lucide-icons/lucide */
  var LUCIDE = {
    snail: ['M2 13a6 6 0 1 0 12 0 4 4 0 1 0-8 0 2 2 0 0 0 4 0', 'M18 13a8 8 0 1 1-16 0 8 8 0 1 1 16 0',
            'M2 21h12c4.4 0 8-3.6 8-8V7a2 2 0 1 0-4 0v6', 'M18 3 19.1 5.2', 'M22 3 20.9 5.2'],
    rabbit: ['M13 16a3 3 0 0 1 2.24 5', 'M18 12h.01',
             'M18 21h-8a4 4 0 0 1-4-4 7 7 0 0 1 7-7h.2L9.6 6.4a1 1 0 1 1 2.8-2.8L15.8 7h.2c3.3 0 6 2.7 6 6v1a2 2 0 0 1-2 2h-1a3 3 0 0 0-3 3',
             'M20 8.54V4a2 2 0 1 0-4 0v3', 'M7.612 12.524a3 3 0 1 0-1.6 4.3']
  };
  function rgbOf(s) {
    s = (s || '').trim();
    var m = /^#([0-9a-f]{6})$/i.exec(s);
    if (m) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)];
    m = /rgba?\(([^)]+)\)/.exec(s);
    return m ? m[1].split(',').slice(0, 3).map(function (v) { return parseFloat(v) || 0; }) : null;
  }
  function lum(c) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function css(c) { return 'rgb(' + c.map(Math.round).join(',') + ')'; }
  // `c` laid over `g` at `k`, as one opaque colour.
  function over(c, g, k) { return c.map(function (v, i) { return v * k + g[i] * (1 - k); }); }
  // The ground a tile's picture sits on: the nearest box with a solid fill.
  function groundOf(el) {
    for (; el && el.nodeType === 1; el = el.parentElement) {
      var bg = getComputedStyle(el).backgroundColor, a = /rgba\([^)]*,\s*([\d.]+)\)/.exec(bg);
      if (rgbOf(bg) && !(a && parseFloat(a[1]) < 0.5)) return rgbOf(bg);
    }
    return [255, 255, 255];
  }
  // The words' letters, as the words are written: the style's own strokes
  // and pressure, `width` the line at full pressure, `cap` a capital's
  // height, the ink's middle at x and its foot at `foot`.
  function inkOf(plan) {
    var b = { x0: Infinity, x1: -Infinity, y1: -Infinity };
    plan.strokes.forEach(function (s) { s.forEach(function (p) { b.x0 = Math.min(b.x0, p.x); b.x1 = Math.max(b.x1, p.x); b.y1 = Math.max(b.y1, p.y); }); });
    return b;
  }
  function letters(x, plan, b, cx, foot, cap, width, col, edge) {
    var k = cap / plan.cap, ox = cx - (b.x0 + b.x1) / 2 * k, oy = foot - b.y1 * k;
    [edge, col].forEach(function (c, pass) {
      if (!c) return;
      x.strokeStyle = c;
      plan.strokes.forEach(function (pts) {
        for (var i = 1; i < pts.length; i++) {
          x.lineWidth = Math.max(0.9, width * (pts[i].size || 1)) + (pass ? 0 : 2);
          x.beginPath(); x.moveTo(ox + pts[i - 1].x * k, oy + pts[i - 1].y * k); x.lineTo(ox + pts[i].x * k, oy + pts[i].y * k); x.stroke();
        }
      });
    });
  }
  function lucide(x, name, ox, oy, size, col) {
    var k = size / 24;
    x.save();
    x.translate(ox, oy); x.scale(k, k);
    x.strokeStyle = col; x.lineWidth = 1.5 / k;
    LUCIDE[name].forEach(function (d) { x.stroke(new Path2D(d)); });
    x.restore();
  }
  var tilesKey = '';
  function paintTiles(again) {
    if (!els || !els.tiles || !editor) return;
    var arts = els.tiles.querySelectorAll('canvas.tx-art');
    var st = styleNow(), font = st === 'yours' ? readHand() : files[st];
    var pen = editor.pen(), ink = rgbOf(pen && pen.color) || [124, 92, 255];
    var d = Math.min(3, window.devicePixelRatio || 1), sizes = [];
    for (var i = 0; i < arts.length; i++) sizes.push(arts[i].clientWidth + 'x' + arts[i].clientHeight);
    var grey0 = arts.length ? getComputedStyle(arts[0]).color : '';
    var key = [st, !!font, !!files.print, state.size, thickness(), state.speed, ink.join(','), grey0,
               css(arts.length ? groundOf(arts[0]) : [0, 0, 0]), sizes.join(','), d].join('|');
    if (key === tilesKey && !again) return;
    tilesKey = key;
    var A = font ? makePlan({ text: 'A', font: font, print: files.print, size: 0.1, speed: 4,
                              canvas: { width: 1000, height: 1000 }, pen: { color: '#000', size: 1 } }) : null;
    Array.prototype.forEach.call(arts, function (c) {
      var w = c.clientWidth, h = c.clientHeight;
      if (!w || !h) { tilesKey = ''; return; }   // closed: painted when it opens
      c.width = Math.round(w * d); c.height = Math.round(h * d);
      var x = c.getContext('2d');
      x.setTransform(d, 0, 0, d, 0, 0);
      x.clearRect(0, 0, w, h);
      x.lineCap = 'round'; x.lineJoin = 'round';
      var ground = groundOf(c), grey = rgbOf(getComputedStyle(c).color) || [90, 90, 100];
      var la = lum(ink), lb = lum(ground);
      var pale = (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05) < 1.6;
      var col = css(ink), edge = pale ? css(over(grey, ground, 0.35)) : null;
      var kind = c.getAttribute('data-art');
      if (kind === 'size') {
        if (!A || !A.strokes.length) return;
        var f = Math.pow(Math.max(0, (state.size - SIZE_MIN) / (SIZE_MAX - SIZE_MIN)), 0.6);
        var cap = Math.min(h - 8, 9 + 19 * f);
        var lg = editor.logical(), real = state.size * (lg ? Math.min(lg.width, lg.height) : 540);
        var faint = css(over(ink, ground, 0.35)), foot = h / 2 + 14;
        // Where they sit: a fifth, a half and four fifths of the way, as the
        // pen's dots; where a wide hand (Script's A) would run one into the
        // next, close together as a group, smaller only if they must be.
        var b = inkOf(A), r = (b.x1 - b.x0) / A.cap + 0.08, gap = 4;
        var caps = [9, cap, 27], at = [w * 0.2, w * 0.5, w * 0.8];
        var span = function (i) { return r * caps[i] / 2; };
        if (at[1] - span(1) - at[0] - span(0) < gap || at[2] - span(2) - at[1] - span(1) < gap) {
          var all = r * (caps[0] + caps[1] + caps[2]) + 2 * gap, fit = Math.min(1, (w - 4) / all);
          caps = caps.map(function (v) { return v * fit; });
          var left = (w - (r * (caps[0] + caps[1] + caps[2]) + 2 * gap)) / 2;
          at = [left + span(0), left + 2 * span(0) + gap + span(1), left + 2 * span(0) + 2 * span(1) + 2 * gap + span(2)];
        }
        letters(x, A, b, at[0], foot, caps[0], 1.4, faint, edge);
        letters(x, A, b, at[2], foot, caps[2], 2.2, faint, edge);
        letters(x, A, b, at[1], foot, caps[1], Math.max(1.2, Math.min(caps[1] * 0.2, thickness() / real * caps[1])), col, edge);
      } else if (kind === 'weight') {
        var lw = 1.5 + 0.5 * Math.min(thickness(), 30);
        [edge, col].forEach(function (cc, pass) {
          if (!cc) return;
          x.strokeStyle = cc; x.lineWidth = lw + (pass ? 0 : 2);
          x.beginPath();
          for (var j = 0; j <= 64; j++) {
            var t = j / 64, px = 10 + t * (w - 20), py = h / 2 + Math.sin(t * Math.PI * 2) * h * 0.16;
            if (j) x.lineTo(px, py); else x.moveTo(px, py);
          }
          x.stroke();
        });
      } else if (kind === 'speed') {
        var S = 18, gap = 5, run = Math.min(52, w - 2 * S - 2 * gap - 8);
        var left = w / 2 - (2 * S + 2 * gap + run) / 2;
        lucide(x, 'snail', left, h / 2 - S / 2 - 0.5, S, css(grey));
        lucide(x, 'rabbit', left + S + gap + run + gap, h / 2 - S / 2 - 1, S, css(grey));
        var t0 = left + S + gap + 2, t1 = t0 + run - 4, ty = h / 2 + 1;
        var dot = t0 + (t1 - t0) * state.speed / (SPEEDS.length - 1);
        x.lineWidth = 2.4;
        x.strokeStyle = css(over(grey, ground, 0.45));
        x.beginPath(); x.moveTo(t0, ty); x.lineTo(t1, ty); x.stroke();
        x.strokeStyle = col;
        x.beginPath(); x.moveTo(t0, ty); x.lineTo(dot, ty); x.stroke();
        if (edge) { x.fillStyle = edge; x.beginPath(); x.arc(dot, ty, 5.3, 0, Math.PI * 2); x.fill(); }
        x.fillStyle = col; x.beginPath(); x.arc(dot, ty, 4.3, 0, Math.PI * 2); x.fill();
      }
    });
  }
  function seconds(ms) {
    var s = Math.max(1, Math.round(ms / 1000));
    if (s < 60) return s + ' s';
    var m = Math.floor(s / 60), r = s % 60;
    return m + ' min' + (r ? ' ' + r + ' s' : '');
  }

  // ---- The preview ----
  function refresh() {
    if (!els || !editor) return;
    var st = styleNow();
    var font = st === 'yours' ? readHand() : files[st];
    els.speed.value = String(state.speed);
    els.speed.setAttribute('aria-valuetext', SPEED_TEXT[state.speed]);
    syncSize();
    if (!font) {
      plan = null;
      els.speedOut.textContent = SPEED_TEXT[state.speed];
      els.go.disabled = true;
      position();
      load(st).then(function (f) { if (f && isOpen()) { syncStyles(); refresh(); } });
      return;
    }
    var pen = editor.pen();
    plan = makePlan({ text: els.field.value, font: font, print: files.print, size: state.size,
                      speed: state.speed, canvas: editor.logical(), pen: { color: pen.color, size: thickness() } });
    els.go.disabled = !plan || !plan.strokes.length;
    els.speedOut.textContent = SPEED_TEXT[state.speed] + (plan && plan.strokes.length ? ' · ' + seconds(plan.ms) : '');
    if (els.skip) els.skip.hidden = !(plan && plan.skipped);
    if (want) anchor = clampAnchor(want);
    position();
  }
  // THE EMPTY CANVAS STEPS BACK while Text's words show, so the two are
  // never read through each other (the owner's Flip: "Draw page 1" under
  // the words); styles.css fades its words while the body says so, and
  // while the words write themselves (text-writing), until they are ink.
  function placing(on) { document.body.classList.toggle('text-placing', !!on); }
  function position() {
    var place = els && els.place;
    if (!place) return;
    var sb = screenBox();
    if (!plan || !plan.strokes.length || !anchor || !sb || !isOpen()) { place.hidden = true; placing(false); return; }
    var b = plan.box;
    var left = sb.left + (anchor.x + b.x0) * sb.k, top = sb.top + (anchor.y + b.y0) * sb.ky;
    var w = (b.x1 - b.x0) * sb.k, h = (b.y1 - b.y0) * sb.ky;
    place.hidden = false;
    placing(true);
    place.style.left = left + 'px';
    place.style.top = top + 'px';
    place.style.width = w + 'px';
    place.style.height = h + 'px';
    var c = els.preview, dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    var W = Math.max(1, Math.round(w * dpr)), H = Math.max(1, Math.round(h * dpr));
    if (c.width !== W || c.height !== H || c._for !== plan || c._k !== sb.k) {
      c.width = W; c.height = H; c._for = plan; c._k = sb.k;
      var x = c.getContext('2d');
      x.setTransform(dpr * sb.k, 0, 0, dpr * sb.ky, -b.x0 * dpr * sb.k, -b.y0 * dpr * sb.ky);
      x.clearRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0);
      x.lineCap = 'round'; x.lineJoin = 'round';
      plan.strokes.forEach(function (pts) {
        x.strokeStyle = pts[0].color;
        for (var i = 1; i < pts.length; i++) {
          x.lineWidth = pts[i].size;
          x.beginPath(); x.moveTo(pts[i - 1].x, pts[i - 1].y); x.lineTo(pts[i].x, pts[i].y); x.stroke();
        }
        if (pts.length === 1 || (pts.length === 2 && pts[0].x === pts[1].x && pts[0].y === pts[1].y)) {
          x.fillStyle = pts[0].color;
          x.beginPath(); x.arc(pts[0].x, pts[0].y, pts[0].size / 2, 0, Math.PI * 2); x.fill();
        }
      });
    }
  }
  // While the drawer is up, the words follow the drawing if it moves (a
  // pinch, the page scrolling, the keyboard coming up).
  // ...and the pen: a colour or size changed while the drawer is up is the
  // colour and size the words will be written in.
  var follow = 0, lastBox = '', lastPen = '';
  function followLoop() {
    if (!isOpen()) { follow = 0; return; }
    // Another tool picked (the pen, the eraser, another shape): Text's drawer
    // goes with it, as a drawer goes when another opens.
    if (editor && editor.active && !editor.active()) { follow = 0; close(); return; }
    var pen = editor ? editor.pen() : null, penKey = pen ? pen.color + '/' + pen.size : '';
    if (penKey !== lastPen) { var was = lastPen; lastPen = penKey; if (was) refresh(); }
    var sb = screenBox(), key = sb ? [sb.left, sb.top, sb.k].map(function (v) { return Math.round(v * 10); }).join(',') : '';
    // A drag: the words stay under the finger while the drawing moves under it.
    if (key !== lastBox) { lastBox = key; if (drag && drag.moved) dragTo(); else position(); }
    follow = requestAnimationFrame(followLoop);
  }

  function isOpen() { var s = sheetEl(); return !!(s && !s.hidden && s.classList.contains('open')); }
  function touchFirst() { return !!(window.matchMedia && window.matchMedia('(hover: none)').matches); }
  // THE KEYBOARD (the owner's iPhone: the bar over the keyboard covered the
  // field, so the words could not be seen as they were typed). iOS does not
  // shrink the page for its keyboard, so while the words are typed on a phone
  // the drawer leaves the page's flow and sits on what can be seen, the Post
  // sheet's own way (lib/postsheet.js), as the grabber, the words and Write
  // it (.typing), so the drawing shows above it with the words on it; its
  // room in the page is kept (#txSpacer), so nothing above it moves. Style
  // and the tiles come back with the drawer when the keyboard goes.
  // The keyboard is up when what can be seen ends well above the page's
  // bottom; the drawer is only the words while the words are typed into it
  // with a keyboard up, never merely because the field has focus.
  function fitKeyboard() {
    var s = els && els.sheet;
    if (!s) return;
    var v = window.visualViewport, phone = window.innerWidth <= 640;
    var lift = (phone && v && !s.hidden) ? Math.max(0, Math.round(window.innerHeight - (v.offsetTop + v.height))) : 0;
    var typing = lift > 80 && document.activeElement === els.field && !s.hidden;
    if (typing !== s.classList.contains('typing') && els.spacer) {
      if (typing) {
        var cs = getComputedStyle(s);
        els.spacer.style.height = (s.offsetHeight + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0)) + 'px';
      }
      els.spacer.hidden = !typing;
    }
    var was = s.classList.contains('typing');
    s.classList.toggle('typing', typing);
    s.style.bottom = typing ? lift + 'px' : '';
    s.style.maxHeight = typing ? Math.max(160, Math.round(v.height - 12)) + 'px' : '';
    if (want && isOpen()) { anchor = clampAnchor(want); position(); }
    // Back in the page from the keyboard: on screen again, where the page left it.
    if (was && !typing && isOpen()) comeBack();
  }
  /* CHOOSING TEXT OPENS THE DRAWER (the owner's "A": picking Text "just closes
     the menu", and on a finished take the tap that came next was refused).
     The words start in the middle of the drawing that can be seen; a drag, or
     a tap where they should go, moves them. The drawer is opened first, so
     "can be seen" is with it open. */
  function start() {
    if (!editor || !bind()) return;
    open();
    var sb = screenBox(), lg = editor.logical(), x = lg.width / 2, y = lg.height / 2;
    if (sb) {
      var D = window.SkriblDrawerDetent, stuck = D && D.stuckBottom ? D.stuckBottom() : 0;
      var v = window.visualViewport, vh = v && v.height ? v.height : window.innerHeight;
      var top = sb.top - revealShift();   // where the drawing settles once the drawer shows
      var l = Math.max(sb.left, 0), r = Math.min(sb.left + lg.width * sb.k, window.innerWidth);
      var t = Math.max(top, stuck, 0), b = Math.min(top + lg.height * sb.ky, vh);
      if (r > l) x = ((l + r) / 2 - sb.left) / sb.k;
      if (b > t) y = ((t + b) / 2 - top) / sb.ky;
    }
    place({ x: x, y: y }, true);
  }
  // How far the page will scroll to show the drawer, from where it is now:
  // the drawer's end at the foot of what can be seen, never the dock under
  // the header (lib/drawerdetent.js revealPanelEnd, the same sum).
  function revealShift() {
    var s = els && els.sheet;
    if (!s || s.hidden) return 0;
    var v = window.visualViewport, viewH = v && v.height ? v.height : window.innerHeight;
    var scroller = document.scrollingElement || document.documentElement;
    var r = s.getBoundingClientRect(), want = r.bottom - viewH + 8;
    var dock = editor && editor.dock ? editor.dock() : null, D = window.SkriblDrawerDetent;
    var stuck = D && D.stuckBottom ? D.stuckBottom() : 0;
    var lid = dock && dock.offsetParent !== null ? dock.getBoundingClientRect().top - 4 : r.top - 8;
    want = Math.min(want, lid - stuck);
    var max = scroller.scrollHeight - window.innerHeight - scroller.scrollTop;
    return Math.max(-scroller.scrollTop, Math.min(want, max));
  }
  /* The tap that says where the words go: it opens the drawer there, or, with
     the drawer up, moves the words there. */
  function place(pos, opening) {
    if (!editor || !bind()) return;
    if (job) job.finish();
    // A press is the person acting: the page is theirs, so a reveal still
    // settling (the drawer opening, or back from a drag) moves it no more
    // (lib/drawerdetent.js hush). Before open(), which may start its own.
    var D = window.SkriblDrawerDetent;
    if (!opening && D && D.hush) D.hush();
    want = { x: pos.x, y: pos.y };
    anchor = clampAnchor(want);
    open();
  }
  var closing = false;      // the module is closing the drawer itself
  function open() {
    var s = els.sheet;
    // Already up: the press moved the words, and that is all it did.
    if (isOpen()) { if (want) anchor = clampAnchor(want); position(); return; }
    veiled = false;
    s.classList.remove('tx-veiled', 'typing');
    if (!els.field.value) { try { els.field.value = sessionStorage.getItem(WORDS_KEY) || ''; } catch (e) {} }
    syncStyles();
    syncSize();
    showTile(null, true);
    s.classList.add('open');
    document.body.classList.add('text-open');
    // Through the editor's own drawers: one open at a time, the page brought
    // to it (and home again after).
    if (editor.drawer) editor.drawer(true); else s.hidden = false;
    // Every style's lettering, so each can be written in itself; the words'
    // own first.
    var st = styleNow();
    load(st === 'yours' ? 'print' : st).then(function () {
      load('print').then(function () { if (isOpen()) { syncStyles(); refresh(); } });
    });
    ['skribl', 'print', 'script'].forEach(function (k) {
      load(k).then(function () { if (isOpen()) syncStyles(); });
    });
    refresh();
    requestAnimationFrame(function () { if (want) { anchor = clampAnchor(want); position(); } });
    lastPen = '';
    if (!follow) follow = requestAnimationFrame(followLoop);
    try { els.field.focus({ preventScroll: true }); } catch (e) { els.field.focus(); }
  }
  // What closing leaves, whoever closed it: no words waiting, no keyboard.
  function tidy() {
    var s = els && els.sheet;
    if (!s) return;
    els.place.hidden = true;
    placing(false);
    document.body.classList.remove('text-open');
    if (document.activeElement === els.field) els.field.blur();
    s.classList.remove('open', 'typing', 'tx-veiled');
    veiled = false;
    drag = null;
    s.style.bottom = ''; s.style.maxHeight = '';
    if (els.spacer) els.spacer.hidden = true;
    showTile(null, true);
  }
  function hide(then) {
    var s = els && els.sheet;
    if (!s || !s.classList.contains('open')) { if (then) then(); return; }
    tidy();
    closing = true;
    try { if (editor && editor.drawer) editor.drawer(false); else s.hidden = true; }
    finally { closing = false; }
    if (then) then();
  }
  function close() {
    if (!els) return;
    anchor = null; want = null;
    hide(null);
  }
  // The editor's drawers closed it (another drawer opened, or the page's own
  // close): the words go with it, as Close's do.
  function closed() {
    if (closing || !els || !els.sheet.classList.contains('open')) return;
    anchor = null; want = null;
    tidy();
  }
  function go() {
    if (!els || !plan || !plan.strokes.length || !anchor) return;
    var p = plan, at = { x: anchor.x, y: anchor.y };
    anchor = null; want = null;
    // The preview goes in the frame the words start writing, so nothing
    // jumps: the drawer goes, and the ink begins where the words were.
    els.place.hidden = true;
    hide(null);
    write(p, at);
  }
  function toHand() {
    var s = sheetEl(), url = s && s.getAttribute('data-hand');
    if (!url) return;
    close();
    window.location.href = url;
  }

  // BACK FROM YOUR HAND (Write with it, editor_letters.js): the editor opens
  // with text=1, and Text is chosen the way the picker chooses it, so the
  // next tap places the words. The address loses the flag, so a reload does
  // not choose it again.
  //
  // And the style is Yours, once there is a hand to write with: they have
  // just been working on it, and the owner, back from changing letters with
  // Skribl still chosen, saw no change and thought the edit was lost. Kept
  // as a choice in the drawer is, so the next time is theirs too. The prefs
  // are read first, so the size and speed kept with it are the person's.
  function resume() {
    var q;
    try { q = new URLSearchParams(window.location.search); } catch (e) { return; }
    if (q.get('text') !== '1') return;
    q.delete('text');
    var rest = q.toString();
    try { history.replaceState(history.state, '', window.location.pathname + (rest ? '?' + rest : '') + window.location.hash); }
    catch (e) {}
    if (handCount() > 0) { readPrefs(); state.style = 'yours'; keepPrefs(); }
    setTimeout(function () {
      var b = document.querySelector('#shapeSeg [data-shape="text"]');
      if (b) b.click();
    }, 0);
  }

  window.SkriblText = {
    STYLES: STYLES.slice(), SIZES: SIZES, SPEEDS: SPEEDS.slice(), MAX_CHARS: MAX_CHARS,
    SIZE_RANGE: [SIZE_MIN, SIZE_MAX], WEIGHT_RANGE: [WEIGHT_MIN, WEIGHT_MAX],
    // For the checks: the words' size (a share of the drawing) and thickness now.
    dials: function () { return { size: state.size, weight: thickness(), own: state.weight != null }; },
    attach: function (hooks) { editor = hooks; resume(); },
    place: function (pos) { place(pos); },
    start: start,
    close: close,
    // The editor's drawers closed Text's (another drawer opened): tidy up.
    closed: closed,
    isOpen: isOpen,
    isWriting: function () { return !!job; },
    finish: function () { if (job) job.finish(); },
    load: load,
    // For the checks (verify_text): the plan the drawer would write now.
    plan: function () { return plan; },
    anchor: function () { return anchor ? { x: anchor.x, y: anchor.y } : null; },
    makePlan: makePlan,
    readHand: readHand,
  };
})();
