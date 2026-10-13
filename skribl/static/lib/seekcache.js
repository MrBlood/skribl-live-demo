/* SCRUBBING STARTS NEAR WHERE YOU POINT: a few snapshots of a replay's
 * canvas, so a seek draws only what lies between the nearest one and the
 * target (v322 plan, step 3).
 *
 * WHY. Every seek on a replay -- the Pad's preview, the shared link, the
 * in-post player -- cleared the canvas and drew every point from the first one
 * to where the finger was. A two-hour drawing is about 170,000 points, and one
 * seek near its end took about 2 s on a desk and 10 s on a CPU slowed 4x, so a
 * scrub through it froze. Watching a drawing come alive has to work for the
 * artist's two-hour piece as well as the twenty-second doodle.
 *
 * WHAT. As a seek's replay passes a stroke boundary in a part of the drawing
 * that has no snapshot yet, the canvas is copied. A later seek restores the
 * latest copy at or before its target and draws on from there; a seek forward
 * from where the canvas already stands restores nothing and only draws on. The
 * first seek to a far point pays once; every seek after it is short.
 *
 * EXACT. A snapshot is the canvas's own pixels, copied by drawImage at the
 * identity transform onto a cleared canvas, and put back the same way: a copy,
 * not a resample. It is taken just before a stroke begins, when nothing is
 * half drawn -- the see-through layering a replay may use (app.js
 * makeStrokeCompositor) has nothing in flight then once it has presented, and
 * a new compositor seeded from the restored canvas carries on exactly. So a
 * seek paints what a replay from the first point paints; verify_seekcache
 * compares the pixels.
 *
 * BOUNDED. At most 64 MB of copies for one replay (about eight of a large
 * phone canvas, sixteen at most), and never closer than 4,000 points apart, so
 * a drawing under 4,000 points keeps none and seeks exactly as it always did.
 * A canvas that changes size drops them all, and the next seek starts over.
 *
 * WHERE THE CANVAS STANDS is the caller's to say, and only past the first
 * point: a player shows the finished drawing before its first Play while its
 * replay position is still zero, so position zero is never taken to mean "the
 * canvas holds nothing yet" -- a seek from there restores or starts over.
 *
 *   var cache = SkriblSeekCache.make(canvas, timeline, opts)
 *   cache.indexAt(ms)                 the first point a replay to `ms` leaves undrawn
 *   cache.start(target, current, ctx) where to draw from: the further along of `current`
 *                                     (above zero, not past `target`: where the canvas
 *                                     stands) and the nearest snapshot, which is restored
 *                                     -> { index, restored }; null: from the first point,
 *                                     on the caller's own base
 *   cache.draw(from, to, point, present)
 *                                     calls point(i) for each i in [from, to), copying the
 *                                     canvas where it wants a snapshot (after present())
 *   cache.tap(i, present)             the same copy, for a player whose own loop draws
 *
 * A PLAYER WHOSE INK IS NOT ITS CANVAS (the in-post player keeps the photo as a
 * layer of its own, which its eraser reveals) passes opts.source(), the canvas
 * to copy, and opts.put(copy), which puts one back and replaces the default
 * restore. Both are asked at the moment, so they may follow a compositor the
 * player makes again on every repaint.
 *
 * THE FIRST FAR JUMP RACES (the owner's pick A, from the mock). Copies make
 * every jump after the first short; the first one to a far part of the drawing
 * still has to draw everything up to it, and drawn at once that froze the page
 * -- the bar stuck where it was and then the picture jumped. A seek that would
 * draw more than RACE_FROM points through a part with no copy yet draws them a
 * slice a frame instead, each slice about RACE_MS long, so the page keeps
 * moving: the player puts the bar where it was pointed at once, the drawing
 * races there, and the pen dot rides along. The slices draw the same points in
 * the same order as the one long draw, and presenting between them changes
 * nothing a later present would not repaint, so it lands on the same picture.
 * A jump through parts that have their copies lands at once, as before; so
 * does any jump under RACE_FROM points, which is a minute or two of drawing.
 *
 *   cache.far(from, to)               a seek drawing [from, to) should race
 *   SkriblSeekCache.race(from, to, slice, step, done)
 *                                     calls slice(i, j) to draw [i, j) once a frame
 *                                     (it returns where it got to), step(i) after each
 *                                     slice that leaves more, done(i) when it lands
 *                                     -> { stop() }: a newer seek stops it
 */
(function () {
  'use strict';

  var BUDGET = 64 * 1024 * 1024;   // bytes of copies for one replay
  var MAX_SHOTS = 16;
  var MIN_GAP = 4000;              // points between copies, at least
  var RACE_FROM = 8000;            // points a seek draws at once, at most, before racing
  var RACE_MS = 24;                // ms of drawing in each frame of a race

  function make(canvas, timeline, opts) {
    var n = timeline ? timeline.length : 0;
    var source = opts && opts.source, put = opts && opts.put;
    var w, h, count, gap, slots, shots;
    function size() {
      w = canvas.width; h = canvas.height;
      count = Math.min(MAX_SHOTS, Math.floor(BUDGET / Math.max(1, w * h * 4)));
      // count + 1 stretches of the drawing; the first needs no copy (it starts
      // from the base), each later one gets the first stroke boundary in it.
      gap = Math.max(MIN_GAP, Math.ceil(n / Math.max(1, count + 1)));
      slots = {};                    // stretch number -> { index, canvas }
      shots = [];                    // the same, ascending by index
    }
    size();

    // False once, when the canvas has changed size since the copies were
    // taken: they are dropped, and nothing is known about the canvas now.
    function valid() {
      if (canvas.width === w && canvas.height === h) return true;
      size();
      return false;
    }

    function indexAt(ms) {
      var lo = 0, hi = n;
      while (lo < hi) {
        var mid = (lo + hi) >> 1;
        if (timeline[mid].playT <= ms) lo = mid + 1; else hi = mid;
      }
      return lo;
    }

    function nearest(index) {
      if (!valid()) return null;
      var best = null;
      for (var k = 0; k < shots.length && shots[k].index <= index; k++) best = shots[k];
      return best;
    }

    function restore(shot, ctx) {
      if (put) return put(shot.canvas);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(shot.canvas, 0, 0);
      ctx.restore();
    }

    // Whichever is further along: the canvas as it stands, or the nearest
    // copy. A copy is one drawImage; every point it skips is a stroke.
    function start(target, current, ctx) {
      if (!valid()) return null;
      var shot = nearest(target);
      var here = current != null && current > 0 && current <= target;
      if (here && (!shot || shot.index <= current)) return { index: current, restored: false };
      if (!shot) return null;          // from the first point, on the caller's base
      restore(shot, ctx);
      return { index: shot.index, restored: true };
    }

    // A long draw through a stretch with no copy yet: the first jump there.
    // With no room for copies at all, every long draw is one.
    function far(from, to) {
      if (to - from <= RACE_FROM) return false;
      if (!valid() || !count) return true;
      var a = Math.max(1, Math.floor(from / gap)), b = Math.min(count, Math.floor((to - 1) / gap));
      for (var k = a; k <= b; k++) if (!slots[k]) return true;
      return false;
    }

    function wants(i) {
      if (!count || i <= 0 || i >= n) return false;
      var p = timeline[i];
      if (!p || !p.start) return false;
      var slot = Math.floor(i / gap);
      return slot >= 1 && slot <= count && !slots[slot];
    }

    function take(i) {
      if (!valid()) return;
      var c = canvas.ownerDocument.createElement('canvas');
      c.width = w; c.height = h;
      c.getContext('2d').drawImage(source ? source() : canvas, 0, 0);
      var shot = { index: i, canvas: c };
      slots[Math.floor(i / gap)] = shot;
      var k = shots.length;
      while (k > 0 && shots[k - 1].index > i) k--;
      shots.splice(k, 0, shot);
    }

    // At each point a replay draws, before it: a copy, when this is the place
    // for one. A player that has its own draw loop calls this from it.
    function tap(i, present) {
      if (!wants(i)) return;
      if (present) present();
      take(i);
    }
    var lastDrawn = 0;
    function draw(from, to, point, present) {
      lastDrawn = Math.max(0, to - from);
      for (var i = from; i < to; i++) {
        tap(i, present);
        point(i);
      }
      return to;
    }

    return { indexAt: indexAt, start: start, draw: draw, tap: tap, far: far,
             // For the suite: what is held, without handing out the copies.
             held: function () { return shots.map(function (s) { return s.index; }); },
             drawn: function () { return lastDrawn; },   // points the last draw() drew
             gap: function () { return gap; }, count: function () { return count; } };
  }

  // The slices grow or shrink to take about RACE_MS each on this device, but
  // never more than double from one frame to the next, so a run of tiny
  // points cannot set up one long slice through big ones.
  function race(from, to, slice, step, done) {
    var i = from, per = 1000, live = true;
    function tick() {
      if (!live) return;
      var t = performance.now();
      i = slice(i, Math.min(to, i + per));
      per = Math.max(200, Math.min(per * 2, Math.round(per * RACE_MS / Math.max(1, performance.now() - t))));
      if (i >= to) { live = false; done(i); }
      else { step(i); requestAnimationFrame(tick); }
    }
    requestAnimationFrame(tick);
    return { stop: function () { live = false; } };
  }

  var api = { make: make, race: race, BUDGET: BUDGET, MIN_GAP: MIN_GAP };
  if (typeof window !== 'undefined') window.SkriblSeekCache = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
