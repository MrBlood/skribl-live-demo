/* THE RESTART VIEW, in More under The restart (step 2 of the music plan,
 * mocked first; the owner: "Yes on all"). THE END BESIDE THE START: on the
 * left the loop's last 0.6 seconds up to where it comes round, on the right
 * its first 0.6, and the line between them is the restart. With a smooth
 * restart the end's last moments fade out under the start, as
 * lib/audioloop.js folds them, and the dot at the bottom is how long that
 * blend is. What is drawn is what plays, Cut on silence's move included.
 *
 * A finger on the left moves the end and on the right the start, the music
 * following the finger, so the beats can be lined up across the join by eye;
 * let go, and once there is a tempo an end let go near a beat settles on it
 * (lib/musicdrawer.js: the loop detail's rule, which this took over with the
 * loop detail's job). The dot pulls the blend longer or shorter, back to the
 * line for a clean cut. A finger that moves up or down first scrolls the page.
 *
 * create(root, h) -- root is #musicRestart; h, from lib/musicdrawer.js:
 *   trim(), buffer(), hasTrack(), crossfade() (ms), tempo()
 *   cut()            how far Cut on silence moves both ends, in seconds
 *   edge(which, t)   move an end there
 *   blend(ms)        set the smooth restart's length
 *   letGo(what)      a drag that moved something is over ('start' | 'end' | 'blend')
 * Returns { draw, playhead(t), x(which, t), half() }. */
(function (global) {
  'use strict';

  var W = 0.6, MAX_BLEND = 0.5, LOCK_PX = 6;

  function create(root, h) {
    if (!root) return null;
    var D = global.SkriblDragTrack, EP = global.SkriblEventPoint, TL = global.SkriblMusicTimeline;
    var cv = root.querySelector('.mt-rv-canvas'), dot = root.querySelector('.mt-rv-dot'), ph = root.querySelector('.music-playhead');
    var raf = 0, peaks = null;

    // The two windows: where the end comes round and where the start begins,
    // as heard (the fold, or the cut's move).
    function ends() {
      var t = h.trim(), L = t.end - t.start, xf = Math.min(h.crossfade() / 1000, L / 2), d = xf > 0 ? 0 : (h.cut ? h.cut() : 0);
      return { e: t.end - xf + d, s: t.start + d, xf: xf, L: L, t: t };
    }
    function half() { return (root.clientWidth || 0) / 2; }
    // A song time on its side of the line, in px from the left.
    function xOf(which, t) {
      var g = ends(), w2 = half();
      return which === 'end' ? (t - (g.e - W)) / W * w2 : w2 + (t - g.s) / W * w2;
    }

    function request() { if (!raf) raf = global.requestAnimationFrame(paint); }
    function paint() {
      raf = 0;
      var w = root.clientWidth || 0, hh = root.clientHeight || 0;
      if (!(w > 0) || !(hh > 0) || !cv) return;      // shut: painted when More opens
      var dpr = global.devicePixelRatio || 1, Wd = Math.round(w * dpr), Hd = Math.round(hh * dpr);
      if (cv.width !== Wd || cv.height !== Hd) { cv.width = Wd; cv.height = Hd; }
      var x = cv.getContext('2d');
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.clearRect(0, 0, w, hh);
      var buf = h.buffer();
      if (!h.hasTrack() || !buf || !TL) { place(null); return; }
      if (!peaks || peaks.buffer !== buf) peaks = TL.peaksOf(buf);
      var st = getComputedStyle(root), tok = function (n) { return st.getPropertyValue(n).trim(); };
      var acc = tok('--accent'), ink = tok('--accent-ink');
      var g = ends(), w2 = w / 2, dur = g.t.duration, mid = hh / 2 + 6, room = hh / 2 - 22;
      // What is painted, for whoever asks (the harness): the two windows and
      // each beat on either side.
      var drawn = root._painted = { end: [g.e - W, g.e], start: [g.s, g.s + W], beats: [], blend: g.xf };
      var bx = g.xf > 0 ? Math.min(w, w2 + g.xf / W * w2) : w2;
      if (g.xf > 0) {
        var gr = x.createLinearGradient(w2, 0, bx, 0);
        gr.addColorStop(0, 'rgba(124, 92, 255, .30)'); gr.addColorStop(1, 'rgba(124, 92, 255, 0)');
        x.fillStyle = gr; x.fillRect(w2, 0, bx - w2, hh);
      }
      function col(px, t0, t1, a) {
        if (t1 < 0 || t0 > dur) return;
        var v = TL.peakOf(peaks, Math.max(0, t0), Math.min(dur, t1)) * a, hgt = Math.max(1, v * room);
        x.fillRect(px, mid - hgt, 1.5, hgt * 2);
      }
      x.fillStyle = acc;
      var i, step = W / w2 * 2;
      for (i = 0; i < w2 - 1; i += 2) col(i, g.e - W + i / w2 * W, g.e - W + i / w2 * W + step, 1);
      for (i = Math.ceil(w2); i < w; i += 2) col(i, g.s + (i - w2) / w2 * W, g.s + (i - w2) / w2 * W + step, 1);
      // The end's last moments, folded over the start, fading out.
      if (g.xf > 0) {
        x.fillStyle = ink; x.globalAlpha = 0.45;
        for (i = Math.ceil(w2); i < bx; i += 2) col(i, g.e + (i - w2) / w2 * W, g.e + (i - w2) / w2 * W + step, 1 - (i - w2) / Math.max(1, bx - w2));
        x.globalAlpha = 1;
      }
      // The beat, on both sides: a dashed line and a dot on each.
      var tp = h.tempo();
      if (tp) {
        var p = 60 / tp.bpm;
        [['end', g.e - W, g.e], ['start', g.s, g.s + W]].forEach(function (sd) {
          for (var k = Math.ceil((sd[1] - tp.phase) / p - 1e-9); tp.phase + k * p <= sd[2] + 1e-9; k++) {
            var px = xOf(sd[0], tp.phase + k * p);
            if (px < 2 || px > w - 2 || Math.abs(px - w2) < 1.5) continue;
            x.strokeStyle = ink; x.globalAlpha = 0.5; x.lineWidth = 1; x.setLineDash([2, 3]);
            x.beginPath(); x.moveTo(px, 26); x.lineTo(px, hh - 6); x.stroke(); x.setLineDash([]);
            x.globalAlpha = 0.95; x.fillStyle = ink; x.beginPath(); x.arc(px, 26, 2.6, 0, 7); x.fill(); x.globalAlpha = 1;
            drawn.beats.push([sd[0], +px.toFixed(2), +(tp.phase + k * p).toFixed(4)]);
          }
        });
      }
      // Where it comes round.
      x.fillStyle = ink; x.fillRect(w2 - 1, 0, 2, hh);
      if (g.xf > 0) { x.fillStyle = acc; x.fillRect(bx - 1, 30, 2, hh - 44); }
      place(bx);
    }
    function place(bx) {
      if (!dot) return;
      dot.hidden = bx == null;
      if (bx != null) dot.style.transform = 'translateX(' + bx.toFixed(2) + 'px)';
    }

    /* ---- Fingers. ---------------------------------------------------------- */
    if (D) D.bind(root, function (e) {
      if (!h.hasTrack() || !h.buffer()) return null;
      var pt = EP.at(e), r = root.getBoundingClientRect(), onDot = !!(dot && e.target.closest && e.target.closest('.mt-rv-dot'));
      var touch = e.type === 'touchstart';
      if (onDot || !touch) e.preventDefault();
      var g0 = ends(), w2 = r.width / 2;
      var what = onDot ? 'blend' : pt.clientX - r.left < w2 ? 'end' : 'start';
      var g = { x0: pt.clientX, y0: pt.clientY, locked: onDot || !touch, dead: false, moved: false,
                from: what === 'end' ? g0.t.end : g0.t.start };
      if (onDot) dot.classList.add('dragging');
      root.classList.add('holding');
      return {
        move: function (cx, ev) {
          if (!g.locked) {
            var q = EP.at(ev), dx = cx - g.x0, dy = q.clientY - g.y0;
            if (Math.abs(dy) > LOCK_PX && Math.abs(dy) > Math.abs(dx)) g.dead = true;
            if (Math.abs(dx) > LOCK_PX && !g.dead) g.locked = true;
            if (!g.locked) return;
          }
          if (g.dead) return;
          if (ev && ev.cancelable && ev.type === 'touchmove') ev.preventDefault();
          g.moved = true;
          var rr = root.getBoundingClientRect(), hw = rr.width / 2;
          if (what === 'blend') {
            var most = Math.min(MAX_BLEND, ends().L / 2);
            var s = Math.max(0, Math.min(most, (cx - rr.left - hw) / hw * W));
            h.blend(Math.round(s * 1000 / 5) * 5);
          } else h.edge(what, g.from - (cx - g.x0) / hw * W);
        },
        end: function () {
          if (dot) dot.classList.remove('dragging');
          root.classList.remove('holding');
          if (g.moved) h.letGo(what);
          request();
        }
      };
    });

    function playhead(t) {
      if (!ph) return;
      var g = ends(), at = null;
      if (t != null && h.hasTrack()) {
        if (t >= g.e - W && t <= g.e) at = xOf('end', t);
        else if (t >= g.s && t <= g.s + W) at = xOf('start', t);
      }
      ph.hidden = at == null;
      if (at != null) ph.style.transform = 'translateX(' + at.toFixed(2) + 'px)';
    }

    if (global.ResizeObserver) new global.ResizeObserver(function () { request(); }).observe(root);
    if (global.matchMedia) {
      var mq = global.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', request);
    }
    if (global.MutationObserver) new MutationObserver(request).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return { draw: request, playhead: playhead, x: xOf, half: half, window: W };
  }

  global.SkriblMusicRestart = { create: create, WINDOW: W };
})(window);
