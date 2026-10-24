/* THE TIMELINE: the music drawer's one view of the loop, on the Pad and on
 * Flip, the drawing's lane above the song, the loop's two ends as handles,
 * and the whole song as one thin line under them. (Step 2 of the music plan,
 * mocked first; the owner: "Yes on all".)
 * YOUR DRAWING STAYS PUT AND THE SONG SLIDES UNDER IT.
 *
 * Above, the drawing's own lane: each stroke when it was drawn (the Pad), or
 * each page as long as it shows, numbered, and its next turns fainter (Flip:
 * an animation goes round on its own, lib/holdtiming.js plan). A dashed line
 * wherever the loop comes round under it. Below, the song: its waveform, the
 * loop lit, the beat once there is one (a dot on each, bigger on each bar
 * from the loop's start), a smooth restart's fold coming in at the loop's
 * end, and what lies past either end of the song dimmed. The loop's two ends
 * are handles. Under it all, the whole song as one thin line, and where the
 * loop is in it.
 *
 * It took over from the strip (the whole song, two handles, a window to
 * slide) and from the loop detail in More (a close-up of an end at 1x to 16x,
 * Loop/Start/End and Scroll), whose magnifier is the timeline's now. The
 * restart's close-up is the Restart view (lib/musicrestart.js).
 *
 * WHAT A FINGER DOES. On the song it slides the song under the drawing: both
 * ends move and the loop keeps its length. On an end it moves that end, and
 * held near the timeline's edge the view widens, smoothly, so a loop can grow
 * past what is on screen (magnified, it slides along instead). On the
 * whole-song line the loop goes where the finger is. On the drawing nothing:
 * it stays put, and a finger there can scroll the page. Let go, and
 * lib/musicdrawer.js settles what was moved while Snap to the beat is on (an
 * end on whole bars, a start or a slid loop's start on a beat; magnified, a
 * start stays where it is let go and the beat moves to it, so it is told
 * where the music begins); then the view eases back to its framing. The beat
 * marks glide when where a beat falls moves (beatTo).
 *
 * EACH END IS A LINE WITH A TAB AT ITS FOOT (styles.css): nothing over the
 * wave beside the line, where the music starts.
 *
 * THE FRAMING: 1.28 times the longer of the loop and the drawing, the
 * drawing counted up to three loops (a two-hour piece would make the loop a
 * sliver), with the loop's start 9% in. The view eases toward it every frame
 * (70ms to most of the way, so a settle and the reframing after it read as
 * one glide) and holds still while a finger is down, but for the widening.
 * Reduce Motion: no easing, the view is where it belongs at once.
 *
 * MAGNIFY (the owner, looking for the loop detail's: "All yes but maybe go
 * to x64?", then "stay"): - and + at the end of the name's line, 1x to 64x.
 * Each rung is the framing over that many with the end last touched in the
 * middle: the start, until the end is grabbed, or moved anywhere else (- and
 * +, a typed time, the Restart view: focus()). The loop never moves for it,
 * and a step glides there as any reframing does. Magnified, an end held near
 * either edge carries the view along at the zoom, as far as the end can
 * follow, so the loop can shorten past what is in view as well as grow, and a
 * slide carries the view with the end zoomed around. The zoom stays when the
 * drawer is put away; a new song (reset()) is 1x on its start. Magnified past
 * a block a column, the song is drawn from its samples (peakOf).
 *
 * A finger on the song scrolls the page if it moves up or down first
 * (touch-action: pan-y and a 6px lock), as the strip never let it: the
 * timeline is two and a half strips tall.
 *
 * create(root, h) -- root is #musicTimeline; h, from lib/musicdrawer.js:
 *   trim()              { start, end, duration }
 *   buffer()            the decoded AudioBuffer, or null
 *   hasTrack()
 *   crossfade()         ms
 *   tempo()             { bpm, phase } or null
 *   lane()              { seconds, marks: [[a, b, label?], ...], again }
 *                       (seconds; `again`, Flip's: { from, period } of the
 *                       part that goes round), computed when laneKey() moves
 *   laneKey()           a cheap key that changes when the drawing does
 *   name(secs)          the words over the drawing's lane
 *   edge(which, t)      move an end there (during a drag)
 *   slide(start)        move the loop there, its length kept
 *   jump(start)         the same, gliding there and onto a beat (a tap on the
 *                       whole song)
 *   letGo(kind, which, zoomed)  a drag that moved something is over ('end' |
 *                       'slide'), magnified past 1x or not
 *   still()             Reduce Motion
 * Returns { draw, reset, focus(which), playhead(t), x(t), view(), held() }. */
(function (global) {
  'use strict';

  var SPAN = 1.28, LEAD = 0.09, EASE_MS = 70, ZONE = 28, GROW = 1.4;
  // MAGNIFY: the framing over 1 to 64, around the end last touched; zoomed
  // in, an end held near either edge carries the view along (PAN views a
  // second at the edge itself) instead of widening it.
  var MAGS = [1, 2, 4, 8, 16, 32, 64], PAN = 1.6;
  var LANE = 26, GAP = 8, LOCK_PX = 6;

  // The song's loudness in blocks, once per buffer: the largest |sample|
  // over every channel, per 128 samples and then per 1,024 and 8,192, so a
  // column is a few reads at any zoom.
  var LEVELS = [128, 1024, 8192];
  function peaksOf(buffer) {
    var n = buffer.length, ch = [], c, i, k;
    for (c = 0; c < buffer.numberOfChannels; c++) ch.push(buffer.getChannelData(c));
    var base = new Float32Array(Math.ceil(n / LEVELS[0])), top = 1e-4;
    for (i = 0; i < n; i++) {
      var v = 0;
      for (c = 0; c < ch.length; c++) { var a = ch[c][i]; if (a < 0) a = -a; if (a > v) v = a; }
      k = (i / LEVELS[0]) | 0;
      if (v > base[k]) base[k] = v;
      if (v > top) top = v;
    }
    var levels = [base];
    for (var l = 1; l < LEVELS.length; l++) {
      var f = LEVELS[l] / LEVELS[l - 1], prev = levels[l - 1], next = new Float32Array(Math.ceil(prev.length / f));
      for (i = 0; i < prev.length; i++) { k = (i / f) | 0; if (prev[i] > next[k]) next[k] = prev[i]; }
      levels.push(next);
    }
    return { sr: buffer.sampleRate, levels: levels, top: top, buffer: buffer };
  }
  // The loudest over [t0, t1), 0..1 of the song's loudest.
  function peakOf(P, t0, t1) {
    var s0 = Math.max(0, t0 * P.sr), s1 = Math.max(s0 + 1, t1 * P.sr), l = 0;
    // Magnified past a block a column: the samples themselves.
    if (s1 - s0 < LEVELS[0]) {
      var b0 = P.buffer, j0 = Math.floor(s0), j1 = Math.min(b0.length, Math.ceil(s1)), top = 0;
      for (var c = 0; c < b0.numberOfChannels; c++) {
        var d = b0.getChannelData(c);
        for (var j = j0; j < j1; j++) { var a = d[j] < 0 ? -d[j] : d[j]; if (a > top) top = a; }
      }
      return top / P.top;
    }
    while (l + 1 < LEVELS.length && LEVELS[l + 1] <= s1 - s0) l++;
    var blk = LEVELS[l], arr = P.levels[l], a = Math.floor(s0 / blk), b = Math.min(arr.length, Math.ceil(s1 / blk)), m = 0;
    for (var i = a; i < b; i++) if (arr[i] > m) m = arr[i];
    return m / P.top;
  }

  function create(root, h) {
    if (!root) return null;
    var D = global.SkriblDragTrack, EP = global.SkriblEventPoint;
    var stage = root.querySelector('.mt-tl-stage'), cv = root.querySelector('.mt-tl-canvas');
    var nameEl = root.querySelector('.mt-tl-name'), whole = root.querySelector('.mt-tl-whole'), part = root.querySelector('.mt-tl-part');
    var hs = root.querySelector('.mt-tl-handle[data-which="start"]'), he = root.querySelector('.mt-tl-handle[data-which="end"]');
    var ph = root.querySelector('.music-playhead');
    var view = null, held = null, raf = 0, lastT = 0, peaks = null, lane = null, laneKey = null, laneSecs = 0;
    var mag = 1, focus = 'start', beat = null;   // beat: the tempo as its marks are painted (beatTo)
    var magOut = root.querySelector('.mt-tl-mag-btn[data-mag="-1"]'), magIn = root.querySelector('.mt-tl-mag-btn[data-mag="1"]');
    var magVal = root.querySelector('.mt-tl-mag-val'), nameBox = root.querySelector('.mt-tl-namebox');

    function rect() { return stage.getBoundingClientRect(); }
    function width() { return stage.clientWidth || 0; }
    function trim() { return h.trim(); }
    function laneNow() {
      var k = h.laneKey ? h.laneKey() : '';
      if (lane === null || k !== laneKey) { laneKey = k; lane = h.lane ? h.lane() : null; laneSecs = lane && lane.seconds > 0 ? lane.seconds : 0; }
      return lane;
    }
    // Where the view belongs for the loop as it is: its framing, or
    // magnified, that over `mag` with the end last touched in the middle.
    function target() {
      var t = trim(), L = Math.max(0.05, t.end - t.start), d = Math.min(laneSecs, 3 * L);
      var span = SPAN * Math.max(L, d);
      if (mag > 1) { span /= mag; return { v0: focused() - span / 2, span: span }; }
      return { v0: t.start - LEAD * span, span: span };
    }
    function focused() { var t = trim(); return focus === 'end' ? t.end : t.start; }
    function X(t) { return (t - view.v0) / view.span * width(); }
    function T(x) { return view.v0 + x / width() * view.span; }

    // Every frame while the view is on its way, and once otherwise. A slide
    // carries the view with the loop's start, so the song moves under the
    // finger and the drawing does not; an end held near the edge widens it;
    // otherwise it eases to where it belongs.
    function frame(now) {
      raf = 0;
      if (!h.hasTrack()) { view = null; paint(); return; }
      var goal = target(), dt = Math.min(64, Math.max(0, now - (lastT || now)));
      if (!view) view = goal;
      else if (held && held.kind === 'slide') view = mag > 1 ? { v0: focused() - held.off, span: view.span }
        : { v0: trim().start - LEAD * view.span, span: view.span };
      else if (held && held.kind === 'end') widen(now);
      else if (h.still()) view = goal;
      else {
        var k = 1 - Math.exp(-dt / EASE_MS);
        view = { v0: view.v0 + (goal.v0 - view.v0) * k, span: view.span + (goal.span - view.span) * k };
        if (Math.abs(goal.v0 - view.v0) < goal.span * 1e-4 && Math.abs(goal.span - view.span) < goal.span * 1e-4) view = goal;
      }
      var gliding = beatTo(dt);
      lastT = now;
      paint();
      // The view, for whoever reads it (the harness): the time at the left
      // edge and the seconds across, as painted.
      if (view) root.dataset.view = view.v0.toFixed(4) + ' ' + view.span.toFixed(4);
      if ((!held && view !== goal) || (held && held.kind === 'end' && held.zone) || gliding) request();
    }
    // THE BEAT MARKS GLIDE when where a beat falls moves and the tempo does
    // not (a start let go magnified becomes a beat, lib/musicdrawer.js), with
    // the view's own ease and the shorter way round, so they move as one with
    // the settle and the reframing after it. A new tempo, or none, is there at
    // once, and so is all of it under Reduce Motion. True while on the way.
    function beatTo(dt) {
      var tp = h.tempo();
      if (!tp) { beat = null; return false; }
      if (!beat || beat.bpm !== tp.bpm || h.still()) { beat = { bpm: tp.bpm, phase: tp.phase }; return false; }
      var p = 60 / tp.bpm, d = tp.phase - beat.phase;
      d -= Math.round(d / p) * p;
      if (Math.abs(d) < 1e-4) { beat = { bpm: tp.bpm, phase: tp.phase }; return false; }
      beat = { bpm: tp.bpm, phase: beat.phase + d * (1 - Math.exp(-dt / EASE_MS)) };
      return true;
    }
    function request() { if (!raf) raf = global.requestAnimationFrame(frame); }
    // The words now, the pixels on the next frame: a bubble says its end's
    // time the moment it moves (a nudge, a typed time), as the strip's did.
    function draw() { words(); if (!raf) { lastT = 0; request(); } }
    function words() {
      if (!h.hasTrack()) return;
      var t = trim();
      [[hs, t.start], [he, t.end]].forEach(function (e) {
        var bub = e[0] && e[0].querySelector('.trim-bubble');
        if (bub) { var s = clock(e[1]); if (bub.textContent !== s) bub.textContent = s; }
      });
      if (nameEl && h.name) {
        laneNow();
        var said = h.name(laneSecs);
        if (nameEl.textContent !== said) nameEl.textContent = said;
      }
    }

    // Held near the edge an end is dragged toward, the view widens, the far
    // side kept, and the end follows the finger out.
    function widen(now) {
      var w = width(), g = held, dt = Math.min(64, Math.max(0, now - (lastT || now))) / 1000;
      if (!g.zone || !(dt > 0)) return;
      if (mag > 1) {
        // Magnified: along, at the zoom, toward the edge the finger is at, as
        // far as the end can follow. Where it stops (the song's start or end,
        // the other end, the cap) the view stops with it: the end under the
        // finger, or where it is when it was already stopped, never a jump.
        var fx = Math.max(0, Math.min(w, g.x - rect().left)), was = view.v0;
        view = { v0: was + g.side * PAN * g.zone * dt * view.span, span: view.span };
        h.edge(g.which, T(fx));
        var tt = trim(), under = (g.which === 'end' ? tt.end : tt.start) - fx / w * view.span;
        view = { v0: Math.max(Math.min(was, view.v0), Math.min(Math.max(was, view.v0), under)), span: view.span };
        return;
      }
      var t = trim(), most = SPAN * Math.max(t.duration, 1);
      var grow = 1 + GROW * g.zone * dt, span = Math.min(most, view.span * grow);
      if (span === view.span) return;
      view = g.which === 'end' ? { v0: view.v0, span: span } : { v0: view.v0 + view.span - span, span: span };
      h.edge(g.which, T(Math.max(0, Math.min(w, g.x - rect().left))));
    }

    function paint() {
      var w = width(), hh = stage.clientHeight || 0, ok = h.hasTrack() && view;
      root.classList.toggle('empty', !ok);
      if (!(w > 0) || !(hh > 0)) return;      // shut: painted when it opens (sync)
      var dpr = global.devicePixelRatio || 1, W = Math.round(w * dpr), H = Math.round(hh * dpr);
      if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
      var x = cv.getContext('2d');
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.clearRect(0, 0, w, hh);
      if (!ok) return;
      // What is painted, as it is painted, for whoever asks (the harness):
      // each mark on the drawing's lane, each comes-round line, each beat.
      var drawn = root._painted = { marks: [], lines: [], beats: [], turns: 0 };
      var st = getComputedStyle(root), tok = function (n) { return st.getPropertyValue(n).trim(); };
      var acc = tok('--accent'), ink = tok('--accent-ink'), fill = tok('--accent-fill') || acc;
      var card = tok('--menu-card'), line = tok('--menu-card-line'), paper = tok('--menu-paper') || card;
      var t = trim(), s0 = t.start, s1 = t.end, L = s1 - s0, xf = Math.min(h.crossfade() / 1000, L / 2), hl = L - xf;
      var dur = t.duration, ln = laneNow(), Dd = laneSecs, sTop = LANE + GAP, sH = hh - sTop;
      function rr(a, b, c, d, r) { x.beginPath(); if (x.roundRect) x.roundRect(a, b, c, d, r); else x.rect(a, b, c, d); }

      // THE DRAWING, from the loop's start.
      var a0 = X(s0), a1 = Dd > 0 ? X(s0 + Dd) : a0;
      x.lineWidth = 1;
      if (Dd > 0) {
        rr(a0, 0.5, Math.max(8, a1 - a0), LANE - 1, 8); x.fillStyle = card; x.fill(); x.strokeStyle = line; x.stroke();
        var marks = ln && ln.marks || [], again = ln && ln.again, numbered = marks.length && marks[0].length > 2;
        // The first turn, then (Flip) the next ones, fainter, until the loop has come round.
        var turns = [[0, 0, Infinity]];
        if (again && again.period > 0) {
          for (var c = 1, o = Dd; s0 + o < s0 + hl - 0.02 && c < 64; c++, o += again.period) turns.push([c, o - again.from, s0 + hl]);
        }
        turns.forEach(function (tn) {
          var c2 = tn[0], off = tn[1], stop = tn[2], lastX = -1;
          drawn.turns = c2 + 1;
          if (c2) {
            var b0 = X(s0 + off + again.from), b1 = Math.min(X(s0 + off + again.from + again.period), X(stop));
            if (b1 - b0 < 2) return;
            rr(b0, 0.5, b1 - b0, LANE - 1, 8); x.fillStyle = card; x.fill(); x.strokeStyle = line; x.stroke();
          }
          for (var i = 0; i < marks.length; i++) {
            var m = marks[i];
            if (c2 && m[0] < again.from - 1e-9) continue;
            var A = X(s0 + off + m[0]), B = X(Math.min(s0 + off + m[1], stop));
            if (B <= A + 0.25 && c2) continue;
            if (A > w + 2) break;
            if (B < -2) continue;
            if (!numbered && A < lastX + 1) { A = lastX + 1; if (B < A) continue; }   // strokes closer than a pixel: one mark
            x.globalAlpha = c2 ? 0.45 : 1;
            x.fillStyle = numbered ? fill : acc;
            rr(A + (numbered ? 1.5 : 0), numbered ? 4 : 6, Math.max(3, B - A - (numbered ? 3 : 0)), LANE - (numbered ? 8 : 12), numbered ? 4 : 3);
            x.fill();
            drawn.marks.push([+A.toFixed(2), +B.toFixed(2), c2]);
            lastX = B;
            if (numbered && !c2 && B - A > 18) {
              x.globalAlpha = 1; x.fillStyle = '#fff'; x.font = '650 11px ' + st.fontFamily; x.textBaseline = 'middle';
              x.fillText(String(m[2]), A + 6, LANE / 2 + 0.5);
            }
          }
          x.globalAlpha = 1;
        });
        // Where the loop comes round under the drawing.
        var lines = 0;
        if (hl > 0) for (var k = 1; s0 + k * hl < s0 + Dd - 0.02 && lines < 64; k++) {
          var rx = X(s0 + k * hl);
          if (rx > w) break;
          if (hl / view.span * w < 4) break;
          x.strokeStyle = ink; x.globalAlpha = 0.8; x.setLineDash([3, 3]); x.lineWidth = 1.5;
          x.beginPath(); x.moveTo(rx, 0); x.lineTo(rx, hh); x.stroke(); x.setLineDash([]); x.globalAlpha = 1; lines++;
          drawn.lines.push(+rx.toFixed(2));
        }
      } else {
        x.setLineDash([4, 4]); rr(a0, 0.5, Math.max(40, w * 0.25), LANE - 1, 8); x.strokeStyle = line; x.stroke(); x.setLineDash([]);
      }

      // THE SONG, the loop lit.
      x.lineWidth = 1;
      rr(0.5, sTop + 0.5, w - 1, sH - 1, 10); x.fillStyle = card; x.fill(); x.strokeStyle = line; x.stroke();
      x.save(); rr(0, sTop, w, sH, 10); x.clip();
      x.fillStyle = acc; x.globalAlpha = 0.14; x.fillRect(X(s0), sTop, X(s1) - X(s0), sH); x.globalAlpha = 1;
      var buf = h.buffer();
      if (buf && (!peaks || peaks.buffer !== buf)) peaks = peaksOf(buf);
      if (peaks && peaks.buffer === buf) {
        var mid = sTop + sH / 2 + 3, room = sH / 2 - 10;
        x.fillStyle = acc;
        for (var px = 0; px < w; px += 2) {
          var u0 = T(px), u1 = T(px + 2);
          if (u1 < 0 || u0 > dur) continue;
          var v = peakOf(peaks, Math.max(0, u0), Math.min(dur, u1)), hgt = Math.max(1, v * room), inside = u1 > s0 && u0 < s1;
          x.globalAlpha = inside ? 1 : 0.3;
          x.fillRect(px, mid - hgt, 1.5, hgt * 2);
        }
        x.globalAlpha = 1;
      }
      var tp = beat;
      if (tp) {
        var p = 60 / tp.bpm, ppb = p / view.span * w, k0 = Math.round((s0 - tp.phase) / p);
        for (var kb = Math.ceil((Math.max(0, view.v0) - tp.phase) / p); tp.phase + kb * p <= Math.min(dur, view.v0 + view.span); kb++) {
          var bar = ((kb - k0) % 4 + 4) % 4 === 0;
          if (ppb < 6 && !bar) continue;
          if (ppb * 4 < 6 && ((kb - k0) % 16 + 16) % 16) continue;
          x.fillStyle = ink; x.globalAlpha = bar ? 0.9 : 0.75;
          x.beginPath(); x.arc(X(tp.phase + kb * p), sTop + 8, bar ? 2.4 : 1.7, 0, 7); x.fill();
          drawn.beats.push([+X(tp.phase + kb * p).toFixed(2), bar, +(tp.phase + kb * p).toFixed(4)]);
        }
        x.globalAlpha = 1;
      }
      if (xf > 0) {
        var gx = X(s1 - xf), g = x.createLinearGradient(gx, 0, X(s1), 0);
        g.addColorStop(0, 'rgba(124, 92, 255, 0)'); g.addColorStop(1, 'rgba(124, 92, 255, .38)');
        x.fillStyle = g; x.fillRect(gx, sTop, X(s1) - gx, sH);
      }
      x.fillStyle = paper;
      if (view.v0 < 0) { x.globalAlpha = 0.75; x.fillRect(0, sTop, X(0), sH); }
      if (view.v0 + view.span > dur) { x.globalAlpha = 0.8; x.fillRect(X(dur), sTop, w - X(dur), sH); }
      x.globalAlpha = 1;
      x.restore();

      // The handles, the words over the drawing and the whole song's line.
      words();
      [[hs, s0], [he, s1]].forEach(function (e) {
        if (!e[0]) return;
        var at = X(e[1]);
        e[0].style.transform = 'translateX(' + at.toFixed(2) + 'px)';
        e[0].classList.toggle('off', at < -12 || at > w + 12);
      });
      if (nameEl) nameEl.style.transform = 'translateX(' + Math.max(0, Math.min((nameBox ? nameBox.clientWidth : w) - nameEl.offsetWidth, a0)).toFixed(2) + 'px)';
      if (part && dur > 0) {
        part.style.left = (s0 / dur * 100).toFixed(3) + '%';
        part.style.width = 'max(4px, ' + (L / dur * 100).toFixed(3) + '%)';
      }
    }
    // A time to the hundredth, as the handles' bubbles say it: 1:04.25.
    function clock(s) {
      var c = Math.round(s * 100), hu = c % 100, w = (c - hu) / 100;
      return Math.floor(w / 60) + ':' + ('0' + (w % 60)).slice(-2) + '.' + ('0' + hu).slice(-2);
    }

    /* ---- Fingers. ---------------------------------------------------------- */
    function grab(e) {
      if (!h.hasTrack() || !view) return null;
      var pt = EP.at(e), r = rect(), y = pt.clientY - r.top, hd = e.target.closest && e.target.closest('.mt-tl-handle');
      if (!hd && y < LANE + GAP / 2) return null;                  // the drawing stays put
      var touch = e.type === 'touchstart';
      if (hd || !touch) e.preventDefault();
      var g = { kind: hd ? 'end' : 'slide', which: hd ? hd.dataset.which : null, x: pt.clientX, y0: pt.clientY,
                x0: pt.clientX, locked: !!hd || !touch, zone: 0, from: trim().start, off: focused() - view.v0 };
      if (hd) { hd.classList.add('dragging'); focus = hd.dataset.which; }
      held = g;
      root.classList.add('holding');
      return {
        move: function (cx, ev) {
          g.x = cx;
          if (!g.locked) {
            var q = EP.at(ev), dx = cx - g.x0, dy = q.clientY - g.y0;
            if (Math.abs(dy) > LOCK_PX && Math.abs(dy) > Math.abs(dx)) { g.dead = true; }
            if (Math.abs(dx) > LOCK_PX && !g.dead) g.locked = true;
            if (!g.locked) return;
          }
          if (g.dead) return;
          if (ev && ev.cancelable && ev.type === 'touchmove') ev.preventDefault();
          g.moved = true;
          var w = width(), lx = cx - rect().left;
          if (g.kind === 'end') {
            g.zone = g.which === 'end' ? Math.max(0, Math.min(1, (lx - (w - ZONE)) / ZONE)) : Math.max(0, Math.min(1, (ZONE - lx) / ZONE));
            g.side = g.which === 'end' ? 1 : -1;
            if (mag > 1) {   // either edge, magnified: the loop can shorten past what is in view too
              var zr = Math.max(0, Math.min(1, (lx - (w - ZONE)) / ZONE)), zl = Math.max(0, Math.min(1, (ZONE - lx) / ZONE));
              g.zone = Math.max(zr, zl); g.side = zr >= zl ? 1 : -1;
            }
            h.edge(g.which, T(Math.max(0, Math.min(w, lx))));
            if (g.zone) request();
          } else {
            var t = trim(), len = t.end - t.start;
            h.slide(Math.max(0, Math.min(t.duration - len, g.from - (cx - g.x0) / w * view.span)));
          }
        },
        end: function () {
          if (hd) hd.classList.remove('dragging');
          held = null;
          root.classList.remove('holding');
          // A press that moved nothing settles nothing.
          if (g.moved) h.letGo(g.kind, g.which, mag > 1);
          draw();
        }
      };
    }
    if (D && stage) D.bind(stage, grab);
    // The whole song's line: the loop goes where the finger is, its middle
    // under it. A tap glides it there, onto a beat once there is a tempo; a
    // drag follows the finger and, let go, settles as a slid loop does.
    if (D && whole) D.bind(whole, function (e) {
      if (!h.hasTrack()) return null;
      e.preventDefault();
      var g = { kind: 'slide', moved: false, x0: EP.at(e).clientX, off: view ? focused() - view.v0 : 0 };
      held = g;
      root.classList.add('holding');
      function at(cx) {
        var r = whole.getBoundingClientRect(), t = trim(), len = t.end - t.start;
        return Math.max(0, Math.min(t.duration - len, (cx - r.left) / r.width * t.duration - len / 2));
      }
      h.jump(at(g.x0));
      return {
        move: function (cx) {
          if (!g.moved && Math.abs(cx - g.x0) < 2) return;
          g.moved = true;
          h.slide(at(cx));
        },
        end: function () { held = null; root.classList.remove('holding'); if (g.moved) h.letGo('slide', null, mag > 1); draw(); }
      };
    });

    // Magnify: a step glides there as any reframing does (at once under
    // Reduce Motion); the readout says the rung, the ends stop.
    function syncMag() {
      var i = MAGS.indexOf(mag);
      if (magVal) { var w = mag + '\u00d7'; if (magVal.textContent !== w) magVal.textContent = w; }
      if (magOut) magOut.disabled = i <= 0 || !h.hasTrack();
      if (magIn) magIn.disabled = i >= MAGS.length - 1 || !h.hasTrack();
    }
    function step(dir) {
      var i = Math.max(0, Math.min(MAGS.length - 1, MAGS.indexOf(mag) + dir));
      if (MAGS[i] === mag) return;
      mag = MAGS[i];
      syncMag();
      draw();
    }
    [magOut, magIn].forEach(function (b) {
      if (b) b.addEventListener('click', function () { if (!b.disabled) step(+b.dataset.mag); });
    });
    syncMag();

    // The playhead: where the song is, on the song, while something plays.
    function playhead(t) {
      if (!ph) return;
      var w = width(), at = view && t != null ? X(t) : -1;
      ph.hidden = !(at >= 0 && at <= w);
      if (!ph.hidden) ph.style.transform = 'translateX(' + at.toFixed(2) + 'px)';
    }

    // A new layout (the sheet opened, the phone turned): paint at the new size.
    if (global.ResizeObserver && stage) new global.ResizeObserver(function () { draw(); }).observe(stage);
    // A theme switched: the tokens are read as it paints.
    if (global.matchMedia) {
      var mq = global.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', draw);
    }
    if (global.MutationObserver) new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return {
      draw: function () { syncMag(); draw(); },
      // A new song: the view starts where it belongs, not where the last was,
      // at 1x on its start.
      reset: function () { lane = null; view = null; mag = 1; focus = 'start'; beat = null; syncMag(); draw(); },
      // An end moved anywhere else (- and +, a typed time, the Restart view):
      // magnified, the view goes to it.
      focus: function (which) { if ((which === 'start' || which === 'end') && which !== focus) { focus = which; draw(); } },
      playhead: playhead,
      x: function (t) { return view ? X(t) : null; },
      view: function () { return view ? { v0: view.v0, span: view.span } : null; },
      held: function () { return held ? held.kind : null; }
    };
  }

  global.SkriblMusicTimeline = { create: create, peaksOf: peaksOf, peakOf: peakOf };
})(window);
