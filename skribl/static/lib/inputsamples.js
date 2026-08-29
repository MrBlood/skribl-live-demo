/* The points the browser already captured and the handler was throwing away.
 *
 * THE DEFECT, REPORTED FROM THE LIVE DEMO. "When I draw circles fast we get a
 * lot of straight line segments that make a curve. Drawing slowly smoothes it
 * out." Both halves of that are exactly right, and the cause is not the drawing.
 *
 * A `pointermove` listener receives AT MOST ONE EVENT PER ANIMATION FRAME. The
 * digitiser samples far faster than that — 120Hz to 240Hz on a modern phone or
 * tablet — and the browser stashes the samples it batched inside
 * `event.getCoalescedEvents()`. Nothing in this project ever called it, so every
 * stroke was sampled at ~60Hz no matter what the hardware offered.
 *
 * That makes the speed dependence arithmetic rather than feel: a circle drawn in
 * 0.4s gets about 24 points and renders as a 24-sided polygon, because
 * paintSeg() joins consecutive points with drawLine() and nothing interpolates.
 * The same circle over 2s gets ~120 points and looks smooth. The user was not
 * drawing worse when going fast; they were being sampled less.
 *
 * WHY THINNING IS PART OF THE FIX AND NOT A COMPROMISE. Keeping every coalesced
 * sample would multiply point counts several-fold against a server limit of
 * 20,000 points per frame, and most of those points would be worthless: a slowly
 * moving finger at 240Hz produces samples a fraction of a pixel apart, which
 * cost payload and change no pixel.
 *
 * A minimum-distance filter is SELF-BALANCING, which is the property worth
 * noticing. Draw slowly and the samples are dense, so nearly all are dropped and
 * the point count lands about where it does today. Draw fast and the samples are
 * far apart, so they all survive — which is precisely the case that was starved.
 * The filter spends points where curvature is actually being lost and nowhere
 * else. That is the "curve without the bloat".
 *
 * PRESSURE RIDES ALONG. The samples are real PointerEvents, so each carries its
 * own `pressure`. Extracting positions but reading pressure from the final event
 * would flatten every taper onto one value across the whole batch, which is
 * worse than not doing this at all — the caller gets events, not coordinates.
 */
(function () {
  'use strict';

  /* Canvas pixels. Below this a sample changes no pixel a human can see, and a
     240Hz digitiser under a slow finger emits a great many of them. */
  var MIN_DIST = 1.5;
  /* A burst guard in the spirit of shapes.js MAX_POINTS. A frame that stalls
     can deliver a very long coalesced list; a stroke should not be able to
     spend its whole point budget recovering from one hitch. */
  var MAX_PER_EVENT = 48;

  /* The real input samples behind one pointermove, newest last.
     Falls back to the event itself wherever getCoalescedEvents is missing
     (older Safari) or returns nothing — degraded to today's behaviour, never
     broken. */
  function extract(e) {
    if (!e) return [];
    var list = null;
    try {
      if (typeof e.getCoalescedEvents === 'function') list = e.getCoalescedEvents();
    } catch (_) { list = null; }
    if (!list || !list.length) return [e];
    if (list.length > MAX_PER_EVENT) {
      // Keep the newest: they are the ones nearest where the finger actually is.
      list = Array.prototype.slice.call(list, list.length - MAX_PER_EVENT);
    }
    return list;
  }

  /* Drop samples closer together than minDist, measured from the last sample
     KEPT rather than the previous sample seen — otherwise a slow drift of
     sub-threshold steps is discarded entirely and the stroke stops moving.
     `from` is the last point already committed by the caller (or null at the
     start of a stroke), so thinning carries across event boundaries instead of
     restarting every frame.
     The final sample is always kept: it is where the pointer IS, and dropping
     it makes the ink lag the finger. */
  function thin(pts, from, minDist) {
    var d = (minDist === undefined) ? MIN_DIST : minDist;
    var out = [], last = from || null;
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      var isLast = (i === pts.length - 1);
      if (last) {
        var dx = p.x - last.x, dy = p.y - last.y;
        if (!isLast && (dx * dx + dy * dy) < d * d) continue;
      }
      out.push(p);
      last = p;
    }
    return out;
  }

  var api = { MIN_DIST: MIN_DIST, MAX_PER_EVENT: MAX_PER_EVENT,
              extract: extract, thin: thin };
  if (typeof window !== 'undefined') window.SkriblInputSamples = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
