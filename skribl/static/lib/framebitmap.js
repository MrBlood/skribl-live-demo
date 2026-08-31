/* Frame bitmaps — a painted page is rasterised once per playback, shared rule.
 *
 * WHY THIS EXISTS. A generated in-between is thousands of stroke points, and
 * both playback surfaces repainted every one of them on every visit: the Flip
 * editor's play loop repaints the frame each tick, and the player repaints on
 * every frame CHANGE (v259's memo only stopped it repainting the frame already
 * on screen). Measured at 4x CPU throttle — roughly a mid-range phone — one
 * 11,826-point in-between costs ~215ms against a 41.7ms slot at 24fps, and the
 * owner's 46-page file took 6.2s to play a 1.92s loop. Thinning the exposure
 * (v260/v261) reduces that to ~123ms, which is better and still three times
 * the slot: no point budget can make re-rasterising the same static picture
 * every loop fit a phone. The picture does not change; painting it more than
 * once per playback is the bug.
 *
 * So a frame's first paint is captured as a bitmap and every later visit is a
 * single drawImage (~1ms at the same throttle). The first loop costs exactly
 * what it does today and fills the cache as it goes; every loop after it plays
 * on time. This file owns the RULE — when a frame earns a bitmap, how much
 * memory playback may hold, what resolution a capture is taken at — so the
 * editor and the player cannot drift apart on it. The capture and blit calls
 * stay with each surface, whose canvases and transforms differ for real
 * reasons.
 *
 * THE MEMORY CEILING IS THE POINT. Bitmaps are how canvases die on phones: a
 * 46-page document captured at a 2x backing store would hold ~180MB, which is
 * past the canvas budget of a low-end phone. Three rules keep it bounded:
 *
 *   * only a frame worth caching is cached. A 438-point key page repaints in
 *     single-digit milliseconds; spending 2MB to save that is a bad trade.
 *     MIN_POINTS draws that line.
 *   * captures are taken at the resolution the frame is DISPLAYED at, capped
 *     by the backing store. On a desktop showing the canvas 1:1 the capture is
 *     the backing store and the blit is pixel-identical; on a phone showing an
 *     816px page in a 360px column the capture holds only the pixels anyone
 *     can see.
 *   * a hard byte budget. Past it, frames simply paint direct — slower, never
 *     broken. Capture failure (canvas allocation is allowed to fail under
 *     memory pressure) closes the store the same way.
 */
(function () {
  'use strict';

  // Below this many points a frame repaints faster than a capture would pay
  // back. Chosen against the measured slope (~0.018ms/point at 4x throttle):
  // 1500 points is ~27ms throttled, about where a repaint starts to threaten
  // a 24fps slot.
  var MIN_POINTS = 1500;

  // Total bytes of capture a store may hold. 64MB is ~40 display-resolution
  // phone captures or ~8 full 2x-backing desktop ones — enough for any real
  // document on the surface it is playing on, and comfortably inside the
  // canvas memory a low-end phone will actually grant.
  var MAX_BYTES = 64 * 1024 * 1024;

  /* A store lives for ONE playback (editor) or one loaded document (player).
     Keys are the caller's — the editor keys by frame object so any replaced
     page misses safely; the player keys by index because its frames are
     immutable for the life of the page. */
  function store() {
    return { map: new Map(), bytes: 0, closed: false };
  }

  /* Capture resolution: the displayed size when smaller than the backing
     store, the backing store otherwise — never upscaled, never zero. */
  function captureSize(backW, backH, dispW, dispH) {
    var w = Math.max(1, Math.min(Math.round(backW), Math.round(dispW || backW)));
    var h = Math.max(1, Math.round(w * (backH / backW)));
    return { w: w, h: h };
  }

  function wants(s, pointCount, w, h) {
    return !!s && !s.closed && pointCount >= MIN_POINTS
        && s.bytes + w * h * 4 <= MAX_BYTES;
  }

  /* Copy what srcCanvas currently shows into a new bitmap under `key`.
     Returns the bitmap, or null — and a null CLOSES the store, because a
     failed canvas allocation means memory is the problem and asking again
     every frame would make it worse. */
  function capture(s, key, srcCanvas, w, h) {
    if (!s || s.closed) return null;
    try {
      var cv = document.createElement('canvas');
      cv.width = w; cv.height = h;
      var c = cv.getContext('2d');
      if (!c) throw new Error('no 2d context');
      c.drawImage(srcCanvas, 0, 0, w, h);
      s.map.set(key, cv);
      s.bytes += w * h * 4;
      return cv;
    } catch (e) {
      s.closed = true;
      return null;
    }
  }

  function get(s, key) {
    return (s && s.map.get(key)) || null;
  }

  window.SkriblFrameBitmap = {
    MIN_POINTS: MIN_POINTS,
    MAX_BYTES: MAX_BYTES,
    store: store,
    captureSize: captureSize,
    wants: wants,
    capture: capture,
    get: get
  };
})();
