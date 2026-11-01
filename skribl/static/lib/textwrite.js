/* TEXT: words that write themselves (FUTURE.md 6ab). One module for both
 * editors: the Pad (editor_text.js) and Flip (flip.js) each hand it a few
 * hooks, and everything a person meets is here, so the two cannot drift.
 *
 * WHAT A PERSON MEETS. Text is the fifth kind in Shape's picker. Pick it,
 * tap where the words go, and the typing sheet rises: the words, a Style
 * (Yours, or + Make yours; Skribl; Print; Script, each written in itself),
 * a Size (S, M, L: the height of the letters, in the pen's colour and
 * thickness) and a Speed (1/4x to 4x; 1x is the hand's own pace, and the
 * sheet says how long the words will take). The words show where the tap
 * was, above the sheet, inside a dashed box that says Drag to move. Write it
 * puts them in: the sheet goes and the words write themselves on the canvas,
 * a stroke at a time, at the speed chosen.
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
 * Print. The lettering files are loaded the first time the sheet opens
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
 *   end(strokes, ms)      every stroke is kept
 *   skip(ms)       the words were finished early, ms ahead of the clock
 *   say(words)     a short line to the person (the editor's own toast)
 */
(function () {
  'use strict';

  var STYLES = ['yours', 'skribl', 'print', 'script'];
  var LABEL = { yours: 'Yours', skribl: 'Skribl', print: 'Print', script: 'Script' };
  // Cap height, as a share of the drawing's shorter side.
  var SIZES = { S: 0.045, M: 0.065, L: 0.095 };
  // The speed slider's stops: 1x is the middle, 1/4x and 4x the ends.
  var SPEEDS = [0.25, 1 / 3, 0.5, 2 / 3, 1, 1.5, 2, 3, 4];
  var SPEED_TEXT = ['¼×', '⅓×', '½×', '⅔×', '1×', '1½×', '2×', '3×', '4×'];
  var HAND_KEY = 'skribl.letters.v1';     // Your hand's store (editor_letters.js)
  var PREFS_KEY = 'skribl.text.v1';       // the sheet's last style, size and speed
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
  var state = { style: null, size: 'M', speed: 4 };
  var anchor = null;        // where the words sit: the middle of their box, in drawing units
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
  /* THE WORDS, READY TO WRITE. text, style and size as the sheet has them;
   * `lettering` the style's file (and Print, for a hand's missing letters);
   * `canvas` the drawing's size; `pen` the ink. Points are in drawing units
   * from the middle of the words' box, so moving the words moves nothing
   * else; `ms` is how long they take at this speed. */
  function makePlan(o) {
    var font = o.font, print = o.print || null;
    if (!font) return null;
    var text = clean(o.text || '').slice(0, MAX_CHARS);
    var short = Math.min(o.canvas.width, o.canvas.height);
    var cap = Math.max(6, (SIZES[o.size] || SIZES.M) * short);
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
    function done() {
      if (j.done) return;
      j.done = true;
      cancelAnimationFrame(j.raf);
      unguard();
      job = null;
      document.body.classList.remove('text-writing');
      editor.end(strokes.length, p.ms);
    }
    function tick(now) {
      if (j.done) return;
      advance(now - j.start);
      if (j.si >= strokes.length) done();
      else j.raf = requestAnimationFrame(tick);
    }
    j.finish = function () {
      if (j.done) return;
      var ahead = p.ms - (performance.now() - j.start);
      advance(Infinity);
      if (ahead > 0 && editor.skip) editor.skip(Math.round(ahead));
      done();
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
  // Keep the words inside the drawing and, while the sheet is up, above it.
  function clampAnchor(a) {
    var lg = editor.logical(), b = plan ? plan.box : { x0: 0, x1: 0, y0: 0, y1: 0 };
    var x = a.x, y = a.y;
    var minX = -b.x0, maxX = lg.width - b.x1, minY = -b.y0, maxY = lg.height - b.y1;
    x = minX > maxX ? lg.width / 2 : Math.max(minX, Math.min(maxX, x));
    var sb = screenBox(), sh = sheetEl();
    if (sb && sh && !sh.hidden) {
      var top = sh.getBoundingClientRect().top - 12;
      var limit = (top - sb.top) / sb.ky - b.y1;
      if (limit < maxY) maxY = Math.max(minY, limit);
    }
    y = minY > maxY ? Math.max(lg.height / 2, minY) : Math.max(minY, Math.min(maxY, y));
    return { x: x, y: y };
  }

  // ---- The sheet ----
  var $ = function (id) { return document.getElementById(id); };
  var els = null;
  function bind() {
    if (els) return els;
    var s = sheetEl();
    if (!s) return null;
    els = { sheet: s, field: $('txField'), styles: $('txStyles'), under: $('txUnder'),
            note: $('txNote'), edit: $('txEdit'), size: $('txSize'), speed: $('txSpeed'),
            speedOut: $('txSpeedOut'), hint: $('txSpeedHint'), go: $('txGo'), close: $('txClose'),
            skip: $('txSkip'), place: $('txPlace'), preview: $('txPreview') };
    readPrefs();
    els.field.setAttribute('maxlength', String(MAX_CHARS));
    els.field.addEventListener('input', function () {
      try { sessionStorage.setItem(WORDS_KEY, els.field.value); } catch (e) {}
      refresh();
    });
    els.field.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); go(); }
    });
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
    els.size.addEventListener('click', function (e) {
      var b = e.target.closest('[data-size]');
      if (!b) return;
      state.size = b.getAttribute('data-size');
      keepPrefs();
      syncSize();
      refresh();
    });
    els.speed.addEventListener('input', function () {
      state.speed = Math.max(0, Math.min(SPEEDS.length - 1, parseInt(els.speed.value, 10) || 0));
      keepPrefs();
      refresh();
    });
    if (typeof window.addSliderNudgers === 'function') window.addSliderNudgers(els.speed, { step: 1 });
    els.go.addEventListener('click', go);
    els.close.addEventListener('click', close);
    if (window.SkriblSheetSwipe) {
      window.SkriblSheetSwipe.attach(s, { handle: s.querySelector('.tx-grab'), close: close });
    }
    // The words move with a finger, a pen or a mouse, before they are ink.
    var drag = null;
    els.place.addEventListener('pointerdown', function (e) {
      if (!anchor) return;
      e.preventDefault();
      try { els.place.setPointerCapture(e.pointerId); } catch (_) {}
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, a: { x: anchor.x, y: anchor.y } };
      els.place.classList.add('dragging');
    });
    els.place.addEventListener('pointermove', function (e) {
      if (!drag || e.pointerId !== drag.id) return;
      var sb = screenBox();
      if (!sb) return;
      anchor = clampAnchor({ x: drag.a.x + (e.clientX - drag.x) / sb.k, y: drag.a.y + (e.clientY - drag.y) / sb.ky });
      position();
    });
    var endDrag = function (e) {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      drag = null;
      els.place.classList.remove('dragging');
    };
    els.place.addEventListener('pointerup', endDrag);
    els.place.addEventListener('pointercancel', endDrag);
    window.addEventListener('resize', function () { if (isOpen()) { anchor = clampAnchor(anchor); position(); } });
    return els;
  }
  function readPrefs() {
    try {
      var p = JSON.parse(localStorage.getItem(PREFS_KEY) || 'null');
      if (p && STYLES.indexOf(p.style) >= 0) state.style = p.style;
      if (p && SIZES[p.size]) state.size = p.size;
      if (p && p.speed >= 0 && p.speed < SPEEDS.length) state.speed = p.speed | 0;
    } catch (e) {}
  }
  function keepPrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify({ style: state.style, size: state.size, speed: state.speed })); }
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
      var want = st === 'yours' && !made ? 'make' : (font ? 'drawn' : 'word');
      b.classList.toggle('on', on);
      // + Make yours is a way to somewhere, not a choice: it says nothing
      // about being pressed.
      if (want === 'make') b.removeAttribute('aria-pressed');
      else b.setAttribute('aria-pressed', String(on));
      if (b.getAttribute('data-face') === want && want !== 'drawn') return;
      b.setAttribute('data-face', want);
      b.textContent = '';
      if (want === 'make') {
        b.setAttribute('aria-label', 'Make your own hand');
        b.innerHTML = '<span class="tx-make"><b aria-hidden="true">+</b>Make yours</span>';
        return;
      }
      b.setAttribute('aria-label', LABEL[st]);
      var svg = font ? labelSVG(LABEL[st], font, print) : null;
      if (svg) b.appendChild(svg);
      else { var w = document.createElement('span'); w.className = 'tx-word'; w.textContent = LABEL[st]; b.appendChild(w); }
    });
    if (made) {
      els.note.textContent = 'Your hand, ' + made + ' of ' + HAND_OF + ' letters';
      if (els.edit) els.edit.hidden = false;
    } else {
      els.note.textContent = 'Make your own hand in about 10 minutes.';
      if (els.edit) els.edit.hidden = true;
    }
    els.hint.textContent = cur === 'yours' ? '1× is your own speed'
      : cur === 'skribl' ? '1× is Skribl’s speed' : '1× is a steady hand';
  }
  function syncSize() {
    Array.prototype.forEach.call(els.size.querySelectorAll('[data-size]'), function (b) {
      var on = b.getAttribute('data-size') === state.size;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', String(on));
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
    if (!font) {
      plan = null;
      els.speedOut.textContent = SPEED_TEXT[state.speed];
      els.go.disabled = true;
      position();
      load(st).then(function (f) { if (f && isOpen()) { syncStyles(); refresh(); } });
      return;
    }
    plan = makePlan({ text: els.field.value, font: font, print: files.print, size: state.size,
                      speed: state.speed, canvas: editor.logical(), pen: editor.pen() });
    els.go.disabled = !plan || !plan.strokes.length;
    els.speedOut.textContent = SPEED_TEXT[state.speed] + (plan && plan.strokes.length ? ' · ' + seconds(plan.ms) : '');
    if (els.skip) els.skip.hidden = !(plan && plan.skipped);
    if (anchor) anchor = clampAnchor(anchor);
    position();
  }
  function position() {
    var place = els && els.place;
    if (!place) return;
    var sb = screenBox();
    if (!plan || !plan.strokes.length || !anchor || !sb || !isOpen()) { place.hidden = true; return; }
    var b = plan.box;
    var left = sb.left + (anchor.x + b.x0) * sb.k, top = sb.top + (anchor.y + b.y0) * sb.ky;
    var w = (b.x1 - b.x0) * sb.k, h = (b.y1 - b.y0) * sb.ky;
    place.hidden = false;
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
  // While the sheet is up, the words follow the drawing if it moves (a
  // pinch, the page scrolling, the keyboard coming up).
  var follow = 0, lastBox = '';
  function followLoop() {
    if (!isOpen()) { follow = 0; return; }
    var sb = screenBox(), key = sb ? [sb.left, sb.top, sb.k].map(function (v) { return Math.round(v * 10); }).join(',') : '';
    if (key !== lastBox) { lastBox = key; position(); }
    follow = requestAnimationFrame(followLoop);
  }

  function isOpen() { var s = sheetEl(); return !!(s && !s.hidden && s.classList.contains('open')); }
  /* The tap that says where the words go. */
  function place(pos) {
    if (!editor || !bind()) return;
    if (job) job.finish();
    anchor = { x: pos.x, y: pos.y };
    open();
  }
  function open() {
    var s = els.sheet;
    if (!els.field.value) { try { els.field.value = sessionStorage.getItem(WORDS_KEY) || ''; } catch (e) {} }
    syncStyles();
    syncSize();
    s.hidden = false;
    document.body.classList.add('text-open');
    void s.offsetHeight;
    s.classList.add('open');
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
    // After the sheet has its height, so the words can sit above it.
    requestAnimationFrame(function () { if (anchor) { anchor = clampAnchor(anchor); position(); } });
    if (!follow) follow = requestAnimationFrame(followLoop);
    try { els.field.focus({ preventScroll: true }); } catch (e) { els.field.focus(); }
  }
  function hide(then) {
    var s = els.sheet;
    if (!s || s.hidden) { if (then) then(); return; }
    els.place.hidden = true;
    document.body.classList.remove('text-open');
    if (document.activeElement === els.field) els.field.blur();
    var finish = function () { s.hidden = true; s.classList.remove('open'); if (then) then(); };
    if (window.SkriblSheetSwipe && window.SkriblSheetSwipe.isBottomSheet(s)) {
      window.SkriblSheetSwipe.slideOut(s, { done: finish });
      return;
    }
    s.classList.remove('open');
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { s.hidden = true; if (then) then(); return; }
    setTimeout(function () { if (!s.classList.contains('open')) s.hidden = true; if (then) then(); }, 260);
  }
  function close() {
    if (!els) return;
    anchor = null;
    hide(null);
  }
  function go() {
    if (!els || !plan || !plan.strokes.length || !anchor) return;
    var p = plan, at = { x: anchor.x, y: anchor.y };
    anchor = null;
    // The preview goes in the frame the words start writing, so nothing
    // jumps: the sheet slides away, and the ink begins where the words were.
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
  function resume() {
    var q;
    try { q = new URLSearchParams(window.location.search); } catch (e) { return; }
    if (q.get('text') !== '1') return;
    q.delete('text');
    var rest = q.toString();
    try { history.replaceState(history.state, '', window.location.pathname + (rest ? '?' + rest : '') + window.location.hash); }
    catch (e) {}
    setTimeout(function () {
      var b = document.querySelector('#shapeSeg [data-shape="text"]');
      if (b) b.click();
      if (editor && editor.say) editor.say('Tap where your words go');
    }, 0);
  }

  window.SkriblText = {
    STYLES: STYLES.slice(), SIZES: SIZES, SPEEDS: SPEEDS.slice(), MAX_CHARS: MAX_CHARS,
    attach: function (hooks) { editor = hooks; resume(); },
    place: place,
    close: close,
    isOpen: isOpen,
    isWriting: function () { return !!job; },
    finish: function () { if (job) job.finish(); },
    load: load,
    // For the checks (verify_text): the plan the sheet would write now.
    plan: function () { return plan; },
    anchor: function () { return anchor ? { x: anchor.x, y: anchor.y } : null; },
    makePlan: makePlan,
    readHand: readHand,
  };
})();
