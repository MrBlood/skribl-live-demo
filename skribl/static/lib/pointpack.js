/* A LONG DRAWING, PACKED: the compact form both editors' autosaves keep their
 * points in once a drawing is long (v322 plan, step 1).
 *
 * WHY. A browser gives an origin about five million characters of
 * localStorage, shared by both editors' autosaves and every local save. Even
 * written by the rule (lib/pointwrite.js) a point is about 64 characters, so a
 * two-hour Pad drawing (about 170,000 points) is eleven million: it cannot be
 * kept, and the pill says "Storage full -- not saved" for the rest of the
 * session. Packed, the same drawing is 0.69 million characters, four a point,
 * and packing it is faster than writing it as JSON.
 *
 * WHY HERE AND NOT IN IndexedDB. IndexedDB holds hundreds of megabytes, but it
 * answers asynchronously, and on the owner's iPhone it has gone quiet with no
 * error (v317). Both editors restore their draft synchronously, as the page
 * loads, from localStorage. Packing keeps a long drawing in that storage:
 * nothing about restoring, the two-tab slot or Keep for later changes.
 *
 * BOTH EDITORS, PAST 20,000 POINTS. The Pad packs its strokes and its undone
 * strokes (editor_draft.js serializeAutosave); Flip packs page by page, and
 * only the copies that live in localStorage (flip.js packFrames). Under the
 * threshold each writes the plain JSON it always wrote.
 *
 * LOSSLESS AGAINST THE RULE. pack() keeps exactly what pointwrite writes: x,
 * y and size to 0.01, t to a whole millisecond, the colour, `start` and a true
 * `erase`. unpack() gives back points equal, key for key, to
 * SkriblPointWrite.point() of the originals. A point carrying anything else,
 * or a stroke the per-stroke fields cannot describe (two colours, a `start`
 * that is not on its first point), is not guessed at: pack() returns null and
 * the caller writes JSON as before.
 *
 * THE FORM. Per stroke: its length, its colour (an index into `pal`) and its
 * flags. Per point: the change in x, y and size (in hundredths) and in t (in
 * milliseconds) from the point before it in the stroke. Each number is
 * zigzag-coded and written as base-16384 digits, one UTF-16 code unit each,
 * offset into U+0100..U+80FF: no character JSON must escape, no surrogate,
 * nothing a browser's storage would rewrite.
 *
 *   SkriblPointPack.pack(points, groups)   -> { v, n, g, pal, s } or null
 *   SkriblPointPack.unpack(packed)         -> { points, groups } (throws if malformed)
 */
(function () {
  'use strict';

  var V = 1;
  var BASE = 0x0100;          // first code unit used: no control characters, no '"' or '\\'
  var DIGIT = 1 << 14;        // 16384 values a digit; a digit at or past it says "more follow"
  // The highest unit written is BASE + 2 * DIGIT - 1 = U+80FF, below the
  // surrogates (U+D800..U+DFFF).
  var KEYS = { x: 1, y: 1, size: 1, t: 1, color: 1, start: 1, erase: 1 };

  function zig(v) { return v >= 0 ? v * 2 : -v * 2 - 1; }
  function unzig(u) { return u % 2 ? -(u + 1) / 2 : u / 2; }

  // A stroke's points: same colour, same erase, a `start` only on the first,
  // nothing but the rule's keys, finite numbers. Anything else: not packable.
  function fits(points, from, len) {
    var p0 = points[from];
    if (!p0 || typeof p0.color !== 'string') return false;
    var erase = !!p0.erase;
    for (var j = 0; j < len; j++) {
      var p = points[from + j];
      if (!p || typeof p !== 'object') return false;
      for (var k in p) {
        if (!Object.prototype.hasOwnProperty.call(p, k)) continue;
        if (!KEYS[k]) return false;
      }
      if (!isFinite(p.x) || !isFinite(p.y) || !isFinite(p.size) || !isFinite(p.t)) return false;
      if (typeof p.x !== 'number' || typeof p.y !== 'number' || typeof p.size !== 'number' || typeof p.t !== 'number') return false;
      if (p.color !== p0.color || !!p.erase !== erase) return false;
      // An absent erase and a false one pack alike, as every reader takes them
      // (verify_sharedrules); only a value that is neither is refused.
      if (typeof p.erase !== 'undefined' && typeof p.erase !== 'boolean') return false;
      if ('start' in p && (p.start !== true || j !== 0)) return false;
    }
    return true;
  }

  function pack(points, groups) {
    if (!Array.isArray(points) || !Array.isArray(groups)) return null;
    var total = 0;
    for (var gi = 0; gi < groups.length; gi++) {
      var g = groups[gi];
      if (typeof g !== 'number' || g < 0 || g !== Math.floor(g)) return null;
      total += g;
    }
    if (total !== points.length) return null;
    var units = [], pal = [], palIx = {}, at = 0;
    function put(v) {
      var u = zig(v);
      while (u >= DIGIT) { units.push(BASE + DIGIT + (u % DIGIT)); u = Math.floor(u / DIGIT); }
      units.push(BASE + u);
    }
    for (gi = 0; gi < groups.length; gi++) {
      var len = groups[gi];
      put(len);
      if (!len) continue;
      if (!fits(points, at, len)) return null;
      var p0 = points[at], c = palIx[p0.color];
      if (c === undefined) { c = pal.length; pal.push(p0.color); palIx[p0.color] = c; }
      put(c);
      put((p0.erase ? 1 : 0) | (p0.start === true ? 2 : 0));
      var px = 0, py = 0, ps = 0, pt = 0;
      for (var j = 0; j < len; j++, at++) {
        var p = points[at];
        var X = Math.round(p.x * 100), Y = Math.round(p.y * 100), S = Math.round(p.size * 100), T = Math.round(p.t);
        put(X - px); put(Y - py); put(S - ps); put(T - pt);
        px = X; py = Y; ps = S; pt = T;
      }
    }
    var s = '';
    for (var k = 0; k < units.length; k += 8192) s += String.fromCharCode.apply(null, units.slice(k, k + 8192));
    return { v: V, n: points.length, g: groups.length, pal: pal, s: s };
  }

  function unpack(pk) {
    if (!pk || pk.v !== V || typeof pk.s !== 'string' || !Array.isArray(pk.pal)) throw new Error('not a packed drawing');
    var s = pk.s, at = 0, end = s.length;
    function get() {
      var u = 0, mul = 1, c;
      for (;;) {
        if (at >= end) throw new Error('packed drawing ends early');
        c = s.charCodeAt(at++) - BASE;
        if (c < 0 || c >= 2 * DIGIT) throw new Error('packed drawing holds a foreign character');
        if (c < DIGIT) break;
        u += (c - DIGIT) * mul; mul *= DIGIT;
      }
      return unzig(u + c * mul);
    }
    var points = [], groups = [];
    for (var gi = 0; gi < pk.g; gi++) {
      var len = get();
      groups.push(len);
      if (!len) continue;
      var color = pk.pal[get()], flags = get();
      if (typeof color !== 'string') throw new Error('packed drawing names a colour it does not hold');
      var px = 0, py = 0, ps = 0, pt = 0;
      for (var j = 0; j < len; j++) {
        px += get(); py += get(); ps += get(); pt += get();
        var o = { x: px / 100, y: py / 100, color: color, size: ps / 100, t: pt };
        if (j === 0 && (flags & 2)) o.start = true;
        if (flags & 1) o.erase = true;
        points.push(o);
      }
    }
    if (at !== end || points.length !== pk.n) throw new Error('packed drawing does not add up');
    return { points: points, groups: groups };
  }

  window.SkriblPointPack = { pack: pack, unpack: unpack, V: V };
})();
