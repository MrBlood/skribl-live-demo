/* Stamps — the clipboard, but named, persistent and multi-slot.
 *
 * WHAT A STAMP IS. Exactly what the selection clipboard already holds: runs of
 * points in the frame format, `{x, y, color, size, t, erase, start}`. Nothing
 * new enters the format, nothing the player has to learn. The three things a
 * stamp adds to a clipboard are the three things an animator actually needs:
 * it SURVIVES the session, there is more than ONE of it, and it is placed where
 * you tap rather than back where it was cut from.
 *
 * WHY IT IS NORMALISED TO ITS OWN CENTRE. A clipboard entry carries absolute
 * canvas coordinates, which is right for paste — "put it back" — and useless
 * for a stamp, which is placed somewhere new every time. Storing points
 * relative to the selection's bounding-box centre makes the tap point the
 * obvious anchor, and it makes the stamp independent of the canvas it was
 * captured on: Flip has several page sizes and a stamp taken on one has to land
 * sensibly on another.
 *
 * WHY THE ENCODING IS NOT JUST JSON.stringify OF THE POINTS. localStorage is
 * ONE ~5 MB budget for the whole origin, and v231 has the scar: Flip's draft
 * grew to 2.7 MB of it and the Pad's autosave started failing — a feature
 * starving an unrelated feature through a shared resource neither of them
 * mentions. A stamp shelf is exactly the shape of thing that does that again,
 * because it only ever grows: every stamp you save stays until you delete it.
 *
 * So three defences, in order of how much they matter:
 *   1. A TOTAL BYTE BUDGET (MAX_BYTES), not just a slot count. Slots are a
 *      proxy for size and a bad one — one traced outline is worth fifty
 *      doodles.
 *   2. A COMPACT ENCODING, so the budget buys more stamps. Points go into a
 *      flat number array with a colour table rather than an array of objects:
 *      `[x, y, size, colourIndex, erase]` repeating. Measured on real
 *      selections this is around a quarter of the JSON-of-objects size, and
 *      the win is entirely in not repeating seven key names per point.
 *   3. IT REFUSES RATHER THAN EVICTS. A full shelf says so and the save does
 *      not happen. Silently dropping the oldest stamp to fit a new one is the
 *      amber-pill failure over again — the user's work disappearing with no
 *      event they can connect it to. A stamp is something they deliberately
 *      made; losing it needs to be their decision.
 *
 * TWO FIELDS ARE DROPPED ON PURPOSE and both are recovered at place time.
 * `start` is derivable — it is true for the first point of a run and false for
 * the rest, which is how every producer in this project already writes it.
 * `t` is a RECORDING TIMESTAMP, and carrying one across sessions is worse than
 * useless: it would place a stroke in the timeline of a drawing that no longer
 * exists. Placement stamps a fresh monotonic `t`, the same thing doFill() does
 * for the runs it emits.
 *
 * THIS FILE KNOWS NOTHING ABOUT FRAMES, pages or tools. It takes runs of points
 * and gives runs of points back. That is not tidiness for its own sake: the Pad
 * and Flip hold the same point format and a helper that reached for `frame()`
 * would be adoptable by exactly one of them. (v235 learned that the hard way
 * with a shared test helper that turned out to be Pad-only.)
 */
(function () {
  'use strict';

  var VERSION = 1;
  /* 12 slots is a shelf you can see at once on a 320px phone in a 4x3 grid.
     More than that and picking one becomes scrolling and searching, which is
     the point at which a stamp shelf wants naming and folders and stops being
     the small thing it is worth being. */
  var MAX_SLOTS = 12;
  /* Roughly a tenth of the origin's ~5 MB, and the ceiling is on the ENCODED
     shelf rather than on any one stamp, because the failure being prevented is
     the total. */
  var MAX_BYTES = 512 * 1024;
  /* One stamp cannot be more than a third of the shelf. Without this a single
     traced photograph fills the budget and every later save is refused for a
     reason that points at the shelf rather than at the stamp that ate it. */
  var MAX_POINTS = 6000;

  function _bboxOf(runs) {
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, n = 0;
    for (var i = 0; i < runs.length; i++) {
      for (var j = 0; j < runs[i].length; j++) {
        var p = runs[i][j];
        if (!p || typeof p.x !== 'number' || typeof p.y !== 'number') continue;
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
        n++;
      }
    }
    if (!n) return null;
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY, n: n };
  }

  function _r(v, places) {
    var m = Math.pow(10, places);
    return Math.round(v * m) / m;
  }

  /* Runs of frame points -> a stamp, with every coordinate relative to the
     bounding-box CENTRE. Returns null for an empty or unusable selection rather
     than an empty stamp: a slot holding nothing is a slot the user has to work
     out the meaning of. */
  function fromRuns(runs, meta) {
    if (!runs || !runs.length) return null;
    var bb = _bboxOf(runs);
    if (!bb) return null;
    if (bb.n > MAX_POINTS) return null;
    var cx = bb.x + bb.w / 2, cy = bb.y + bb.h / 2;
    var cols = [], index = {}, out = [];
    for (var i = 0; i < runs.length; i++) {
      var flat = [];
      for (var j = 0; j < runs[i].length; j++) {
        var p = runs[i][j];
        if (!p || typeof p.x !== 'number' || typeof p.y !== 'number') continue;
        var c = typeof p.color === 'string' ? p.color : '#000000';
        if (!(c in index)) { index[c] = cols.length; cols.push(c); }
        // 1dp on position and 2dp on size. Below that the rounding is visible
        // as a wobble on a placed stamp; above it the digits are payload for
        // sub-pixel differences no rasteriser resolves.
        flat.push(_r(p.x - cx, 1), _r(p.y - cy, 1),
                  _r(typeof p.size === 'number' ? p.size : 1, 2),
                  index[c], p.erase ? 1 : 0);
      }
      if (flat.length) out.push(flat);
    }
    if (!out.length) return null;
    var st = { v: VERSION, w: _r(bb.w, 1), h: _r(bb.h, 1), n: bb.n,
               at: (meta && meta.at) || Date.now(), c: cols, r: out };
    if (meta && meta.name) st.name = String(meta.name).slice(0, 40);
    return st;
  }

  /* A stamp -> runs of frame points centred on (cx, cy). `scale` multiplies the
     offsets AND the stroke sizes, because a drawing shrunk to half its size has
     half-width lines; scaling only the geometry gives you the same drawing with
     a marker twice as thick, which reads as a different stamp. */
  function toRuns(stamp, cx, cy, scale, t0) {
    if (!stamp || !stamp.r) return [];
    var s = (typeof scale === 'number' && scale > 0) ? scale : 1;
    var t = (typeof t0 === 'number') ? t0 : 0;
    var cols = stamp.c || [], out = [];
    for (var i = 0; i < stamp.r.length; i++) {
      var flat = stamp.r[i], pts = [];
      for (var k = 0; k + 4 < flat.length; k += 5) {
        pts.push({ x: cx + flat[k] * s, y: cy + flat[k + 1] * s,
                   color: cols[flat[k + 3]] || '#000000',
                   size: Math.max(0.5, flat[k + 2] * s),
                   t: t++, erase: !!flat[k + 4], start: k === 0 });
      }
      if (pts.length) out.push(pts);
    }
    return out;
  }

  function pointsIn(stamp) {
    if (!stamp || !stamp.r) return 0;
    var n = 0;
    for (var i = 0; i < stamp.r.length; i++) n += stamp.r[i].length / 5;
    return n;
  }

  /* Would this shelf still fit if `stamp` joined it? Returns a reason string on
     refusal rather than a bare false — the caller has to be able to tell the
     user WHICH ceiling they hit, and "full" and "too big" have different
     remedies. */
  function fits(list, stamp) {
    if (!stamp) return 'empty';
    if (pointsIn(stamp) > MAX_POINTS) return 'big';
    if (list.length >= MAX_SLOTS) return 'full';
    if (JSON.stringify(list.concat([stamp])).length > MAX_BYTES) return 'full';
    return null;
  }

  /* A shelf out of whatever the storage slot actually held, which after a
     downgrade, a half-written value or a hand-edited devtools session may be
     anything at all. Bad entries are dropped one at a time, so one corrupt
     stamp costs its own slot and not the shelf. */
  function decode(raw) {
    var arr;
    try { arr = JSON.parse(raw); } catch (_) { return []; }
    if (!Array.isArray(arr)) return [];
    var out = [];
    for (var i = 0; i < arr.length && out.length < MAX_SLOTS; i++) {
      var s = arr[i];
      if (!s || s.v !== VERSION || !Array.isArray(s.r) || !Array.isArray(s.c)) continue;
      if (!s.r.length) continue;
      out.push(s);
    }
    return out;
  }

  /* Reads and writes go through here so the KEY is stated once. The write
     reports quota failure by returning false instead of throwing: a stamp shelf
     that cannot be written is a disappointment, and the draft it shares an
     origin with is the thing that must not be taken down with it. */
  var KEY = 'skribl_stamps';

  function load(storage) {
    try { return decode((storage || window.localStorage).getItem(KEY) || '[]'); }
    catch (_) { return []; }
  }

  function store(storage, list) {
    try { (storage || window.localStorage).setItem(KEY, JSON.stringify(list)); return true; }
    catch (_) { return false; }
  }

  /* Paint a stamp into a 2D context, fitted to a box. Used for the shelf's
     thumbnails, which are the only label a stamp gets — a hand-drawn asset is
     recognised by sight, and asking for a name at save time is a keyboard on a
     phone in the middle of drawing.
     This mirrors paintSeg()'s opaque path deliberately: per-point colour, per
     point size, round caps. A thumbnail drawn by different rules than the pad
     is a thumbnail that lies about what you are about to place. */
  function draw(g, stamp, box) {
    if (!g || !stamp || !stamp.r) return;
    var pad = (box.pad === undefined) ? 3 : box.pad;
    var w = Math.max(1, box.w - pad * 2), h = Math.max(1, box.h - pad * 2);
    // A dot has zero extent in one or both axes; falling back to 1 keeps the
    // scale finite instead of painting it at infinity.
    var s = Math.min(w / Math.max(1, stamp.w), h / Math.max(1, stamp.h));
    if (!isFinite(s) || s <= 0) s = 1;
    var cx = box.x + box.w / 2, cy = box.y + box.h / 2;
    var cols = stamp.c || [];
    g.save();
    g.lineCap = 'round';
    g.lineJoin = 'round';
    for (var i = 0; i < stamp.r.length; i++) {
      var flat = stamp.r[i];
      for (var k = 5; k + 4 < flat.length; k += 5) {
        // An erased point in a stamp is drawn as the GROUND, not skipped and
        // not composited out: a thumbnail has no layers under it to erase.
        g.strokeStyle = flat[k + 4] ? (box.bg || '#ffffff') : (cols[flat[k + 3]] || '#000000');
        g.lineWidth = Math.max(0.6, flat[k + 2] * s);
        g.beginPath();
        g.moveTo(cx + flat[k - 5] * s, cy + flat[k - 4] * s);
        g.lineTo(cx + flat[k] * s, cy + flat[k + 1] * s);
        g.stroke();
      }
      // A one-point run is a dot, and a moveTo/lineTo pair of the same point
      // draws nothing at all under some rasterisers. Give it its cap.
      if (flat.length === 5) {
        g.strokeStyle = flat[4] ? (box.bg || '#ffffff') : (cols[flat[3]] || '#000000');
        g.lineWidth = Math.max(0.6, flat[2] * s);
        g.beginPath();
        g.moveTo(cx + flat[0] * s, cy + flat[1] * s);
        g.lineTo(cx + flat[0] * s + 0.01, cy + flat[1] * s);
        g.stroke();
      }
    }
    g.restore();
  }

  var api = { VERSION: VERSION, MAX_SLOTS: MAX_SLOTS, MAX_BYTES: MAX_BYTES,
              MAX_POINTS: MAX_POINTS, KEY: KEY,
              fromRuns: fromRuns, toRuns: toRuns, pointsIn: pointsIn,
              fits: fits, decode: decode, load: load, store: store, draw: draw };
  if (typeof window !== 'undefined') window.SkriblStamps = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
