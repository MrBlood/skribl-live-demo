/* How a point is WRITTEN — the shared rule for both editors' serializers.
 *
 * WHY THIS EXISTS. A point was written exactly as JavaScript prints a double:
 *
 *   {"x":127.04332313965341,"y":99.5023777173913,"color":"#26b0ff",
 *    "size":7.343333333333333,"t":124272.30000001192,"erase":false,"start":true}
 *
 * Seventeen significant digits for a position on a 944px canvas, a brush size
 * to the femtometre, a millisecond stamp carrying float noise, and `erase`
 * spelled out on every point of every stroke to say false. Measured on a real
 * document: 123 bytes per point, where 69 carries the same picture. That is
 * over half of every Skribl anyone has ever saved.
 *
 * NOTHING HERE IS A FORMAT CHANGE. Same schema, same keys, same readers — the
 * numbers are just written at the precision the canvas can actually show, and
 * a key that is always its default is left out. `erase` is safe to omit because
 * every reader of it tests TRUTHINESS: flip.js's drawDot/drawLine take it as
 * `erase ? 'destination-out' : 'source-over'`, app.js and inlineplayer.js pass
 * it straight through to the same calls, lib/stamps.js writes `p.erase ? 1 : 0`
 * and lib/strokelayers.js reads `!p.erase`. Not one of them distinguishes
 * `false` from absent, and verify_sharedrules fails if that stops being true.
 *
 * WHY 0.01px. The canvas is at most 4096 CSS px on its longest edge and draws
 * at a device pixel ratio of at most 3, so 0.01 CSS px is a thirtieth of the
 * smallest thing a screen can show. Sub-pixel positioning survives; the noise
 * in the seventeenth digit does not. `t` rounds to whole milliseconds because
 * that is the unit replay reads it in.
 *
 * WHY AT SERIALIZE TIME, not at capture. In memory a point stays exactly what
 * the pointer reported, so drawing, undo, liquify and the transforms compose at
 * full precision and only the WRITTEN copy is rounded. Rounding on capture would
 * compound: every liquify pass would round its own output again.
 */
(function () {
  'use strict';

  var XY_DP = 2, SIZE_DP = 2;

  function round(n, dp) {
    if (typeof n !== 'number' || !isFinite(n)) return n;
    var f = Math.pow(10, dp);
    return Math.round(n * f) / f;
  }

  /* One point, tidied. Returns a NEW object — a serializer must never edit the
   * live drawing it was handed. */
  function point(p) {
    if (!p || typeof p !== 'object') return p;
    var o = {}, k;
    for (k in p) {
      if (!Object.prototype.hasOwnProperty.call(p, k)) continue;
      if (k === 'erase' && p[k] === false) continue;   // absent reads as false
      if (k === 'x' || k === 'y') o[k] = round(p[k], XY_DP);
      else if (k === 'size') o[k] = round(p[k], SIZE_DP);
      else if (k === 't') o[k] = round(p[k], 0);
      else o[k] = p[k];
    }
    return o;
  }

  /* A frames array, tidied. Frames without strokes (a recipe page) pass through
   * untouched rather than being given an empty one. */
  function frames(list) {
    if (!Array.isArray(list)) return list;
    return list.map(function (f) {
      if (!f || !Array.isArray(f.strokes)) return f;
      var o = {}, k;
      for (k in f) if (Object.prototype.hasOwnProperty.call(f, k)) o[k] = f[k];
      o.strokes = f.strokes.map(point);
      return o;
    });
  }

  window.SkriblPointWrite = { point: point, frames: frames, XY_DP: XY_DP, SIZE_DP: SIZE_DP };
})();
