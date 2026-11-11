/* A FACE FROM A DRAWING YOU ALREADY HAVE: placed in the circle, then made a
 * face of its own (after v330; the owner's "all yes" on mock A, Nov 11: "Use
 * one you made: pick a skribl, then place it in the circle", and "your face
 * is its own copy, so deleting or changing the original never empties your
 * circle").
 *
 * docs/INTEGRATION.md, "A face from a drawing you already have". A host with
 * a drawing (one of the person's skribls, fetched as any player fetches it,
 * or a .skribl file they saved) and a square the person placed on it gets a
 * NEW drawing back: square, the placed square filling it, every point moved
 * and sized to fit, its timing untouched. Posted the way a face drawn in the
 * Pad's face mode is (the same payload, with its own share card), it IS such
 * a face, so the face player, the bar's still You and a Gallery card's circle
 * need nothing new. The drawing it came from is never touched.
 *
 *   start(w, h)               the square a face starts on: the drawing's middle
 *                             square, the one a face shows today.
 *   range(w, h)               the sides a person may choose: from a quarter of
 *                             the short side (four times in) to the drawing's
 *                             diagonal (the whole drawing inside the circle,
 *                             with paper around it).
 *   clamp(sq, w, h)           that square, its side kept to the range and its
 *                             middle on the drawing.
 *   check(payload)            null, or why it cannot be a face yet: 'flip' (a
 *                             flip book), 'photo' (a picture under it), 'empty'
 *                             (nothing drawn), 'unreadable'.
 *   place(payload, sq, side)  the new drawing, `side` CSS px square.
 *   card(payload, box)        a Promise of its share card (a data URL), painted
 *                             by the in-post player's own engine in `box` (a
 *                             skribl_inline_draft box the host puts aside) and
 *                             composed by lib/postedcard.js, as an editor's is.
 *
 * WHAT TRAVELS. Points move and their sizes scale, so a line keeps its weight
 * against the drawing; time, colour, `start`, `erase`, the strokeGroups and the
 * recolours (which name points by their index) are kept, and so is the
 * background colour, which fills wherever the square reaches past the drawing.
 * Music stays behind: a face makes no sound (the face player). A photo, or a
 * picture the drawing began on, is not moved yet: check() says 'photo', and
 * the host says so kindly.
 */
(function (global) {
  'use strict';

  var IN = 4;   // the closest a face comes: a quarter of the short side

  function num(n) { return typeof n === 'number' && isFinite(n); }

  function sizeOf(payload) {
    var c = payload && payload.canvasSize;
    var w = c ? +c.cssWidth : NaN, h = c ? +c.cssHeight : NaN;
    return (w > 0 && h > 0 && w <= 8192 && h <= 8192) ? { w: w, h: h } : null;
  }

  /* The drawing's one frame, a legacy payload's top-level drawing as one. */
  function frameOf(payload) {
    if (!payload || typeof payload !== 'object') return null;
    if (Array.isArray(payload.frames)) return payload.frames.length === 1 ? payload.frames[0] : null;
    if (Array.isArray(payload.strokes)) {
      return { strokes: payload.strokes, strokeGroups: payload.strokeGroups, background: payload.background,
               photo: payload.photo, baseSnapshot: payload.baseSnapshot, recolors: payload.recolors };
    }
    return null;
  }

  function start(w, h) {
    var s = Math.min(w, h);
    return { x: (w - s) / 2, y: (h - s) / 2, side: s };
  }

  function range(w, h) {
    return { min: Math.min(w, h) / IN, max: Math.sqrt(w * w + h * h) };
  }

  function clamp(sq, w, h) {
    var r = range(w, h);
    var was = num(sq && sq.side) && sq.side > 0 ? sq.side : Math.min(w, h);
    var cx = (num(sq && sq.x) ? sq.x : 0) + was / 2, cy = (num(sq && sq.y) ? sq.y : 0) + was / 2;
    var side = Math.max(r.min, Math.min(r.max, was));
    cx = Math.max(0, Math.min(w, cx));
    cy = Math.max(0, Math.min(h, cy));
    return { x: cx - side / 2, y: cy - side / 2, side: side };
  }

  function check(payload) {
    if (!payload || typeof payload !== 'object') return 'unreadable';
    if (payload.playbackMode === 'flip' || (Array.isArray(payload.frames) && payload.frames.length > 1)) return 'flip';
    var f = frameOf(payload);
    if (!f || !sizeOf(payload) || !Array.isArray(f.strokes)) return 'unreadable';
    if ((f.photo && f.photo.data) || f.baseSnapshot || payload.baseSnapshot) return 'photo';
    if (!f.strokes.length) return 'empty';
    return null;
  }

  /* One point, moved and sized; written by lib/pointwrite.js's rule when the
     page has it, so a face's points are spelled as every other drawing's. */
  function moved(p, x0, y0, k) {
    var q = {}, key;
    for (key in p) if (Object.prototype.hasOwnProperty.call(p, key)) q[key] = p[key];
    if (num(p.x)) q.x = (p.x - x0) * k;
    if (num(p.y)) q.y = (p.y - y0) * k;
    if (num(p.size)) q.size = p.size * k;
    var W = global.SkriblPointWrite;
    if (W && W.point) return W.point(q);
    if (num(q.x)) q.x = Math.round(q.x * 100) / 100;
    if (num(q.y)) q.y = Math.round(q.y * 100) / 100;
    if (num(q.size)) q.size = Math.round(q.size * 100) / 100;
    return q;
  }

  function place(payload, sq, side) {
    var why = check(payload);
    if (why) throw new Error(why);
    var f = frameOf(payload);
    var out = Math.round(side) || 707;
    var k = out / sq.side, x0 = sq.x, y0 = sq.y;
    var frame = {
      strokes: f.strokes.map(function (p) { return moved(p, x0, y0, k); }),
      strokeGroups: Array.isArray(f.strokeGroups) ? f.strokeGroups.slice() : [],
      baseSnapshot: null,
      background: { color: (f.background && f.background.color) || null },
      photo: null,
      music: null
    };
    if (Array.isArray(f.recolors) && f.recolors.length) frame.recolors = f.recolors.slice();
    var made = {
      version: 2, schemaVersion: 2, playbackMode: 'replay', playSpeed: 'auto', fps: null,
      frames: [frame],
      canvasSize: { cssWidth: out, cssHeight: out, dpr: 1 }
    };
    if (typeof payload.pauseMode === 'string') made.pauseMode = payload.pauseMode;
    return made;
  }

  /* THE CARD, AS AN EDITOR MAKES ONE: the drawing painted whole by the in-post
     player's engine (its own replay of these very points, so the card is the
     face it will draw), then lib/postedcard.js's composition. The box is the
     host's, put aside off the screen; it is painted at one pixel a point. */
  function card(payload, box) {
    return new Promise(function (resolve, reject) {
      var SI = global.SkriblInline, PC = global.SkriblPostedCard;
      if (!SI || !SI.attach || !PC || !PC.build || !box) { reject(new Error('unavailable')); return; }
      var player = SI.attach(box, payload, { ambient: true, dpr: 1 });
      if (!player) { reject(new Error('unavailable')); return; }
      var waited = 0;
      (function ready() {
        var s = player.state();
        if (s.failed) { reject(new Error('failed')); return; }
        if (!s.loaded) {
          if (++waited < 240) global.requestAnimationFrame(ready);
          else reject(new Error('unavailable'));
          return;
        }
        player.seek(s.totalMs);
        var canvas = box.querySelector('.skribl-inline-canvas');
        var url = canvas ? PC.build(canvas) : null;
        if (url) resolve(url); else reject(new Error('failed'));
      })();
    });
  }

  global.SkriblFaceFrame = { start: start, range: range, clamp: clamp, check: check, place: place, card: card };
})(typeof window !== 'undefined' ? window : this);
