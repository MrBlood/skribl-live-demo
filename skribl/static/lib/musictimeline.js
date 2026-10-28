/* THE TIMELINE: the music drawer's one view of the loop, on the Pad and on
 * Flip, the drawing's lane above the song, the loop's two ends as handles,
 * and the whole song as one thin line under them. (Step 2 of the music plan,
 * mocked first; the owner: "Yes on all".)
 * YOUR DRAWING STAYS PUT AND THE SONG SLIDES UNDER IT.
 *
 * Above, the drawing's own lane: each stroke when it was drawn, in its own
 * ink (the Pad), or each page as long as it shows, as its own little picture,
 * numbered where there is room, and its next turns fainter (Flip: an
 * animation goes round on its own, lib/holdtiming.js plan). A dashed line
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
 * past what is on screen, while there is more song past that edge to show
 * (magnified, it slides along instead). On the
 * whole-song line the loop goes where the finger is. On the drawing nothing:
 * it stays put, and a finger there can scroll the page. Let go, and
 * lib/musicdrawer.js settles what was moved while Snap to the beat is on (an
 * end on whole bars, a start or a slid loop's start on a beat, a start let go
 * in the quiet before the music or just into it where the music begins;
 * magnified, a start stays where it is let go and the beat moves to it when
 * it is near one, so it is told where the music begins); then the view eases
 * back to its framing. The beat
 * marks glide when where a beat falls moves (beatTo).
 *
 * EACH END IS A LINE WITH A TAB AT ITS FOOT (styles.css): nothing over the
 * wave beside the line, where the music starts. The line is about 1.5px and
 * sharp, on the screen's own pixels (edge, below).
 *
 * THE FRAMING: 1.28 times the longer of the loop and the drawing, the
 * drawing counted up to three loops (a two-hour piece would make the loop a
 * sliver), with the loop's start 9% in. The view eases toward it every frame
 * (70ms to most of the way, so a settle and the reframing after it read as
 * one glide) and holds still while a finger is down, but for the widening.
 * Reduce Motion: no easing, the view is where it belongs at once.
 *
 * MAGNIFY (the owner, looking for the loop detail's: "All yes but maybe go
 * to x64?", then "stay"; then, to see the wave cross: "Like 512x?" and "All
 * yes" to the mock): - and + at the end of the name's line, 1x to 512x.
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
 * CLOSE IN, THE WAVE ITSELF. Loudness is the same above and below the middle,
 * so mirrored bars never cross it, however far in. Once a point holds under
 * 64 samples (64x for a 15s loop on a phone; 256x for a minute's), the song is
 * the wave, through a middle line at its zero, so where it crosses shows:
 * each point the samples' least and most, and under 8 a point the samples
 * themselves, joined, each a dot once they are 6px apart; past the loop
 * dimmed, as the bars are. The middle line is the timeline's guide ink at 65%,
 * 3:1 and up on both grounds in both themes (the owner chose it over a
 * quieter one): it is what a crossing is read against. Zoomed in, a start let
 * go stays where it is let go (the owner, again: exact control); the join is
 * already clean (lib/audioloop.js: a smooth restart, or Cut on silence).
 *
 * THE DRAWING IN ITS LANE (step 7 of the whole-drawer mock, from ACID's video
 * track; the owner: "All yes"). The Pad's strokes are each in their own ink,
 * its hue kept, made only as much darker (or lighter) as it takes to read 3:1
 * against the lane, as a mark must: a dark ink on the dark lane lifts, a pale
 * one on the light lane deepens, the rest as drawn. Flip's pages are each
 * their own little picture, the strip's thumbnail, its own shape kept: a page
 * as long as its picture or longer is the picture at the lane's height, one
 * centred on the page's time and the rest either side, and a shorter one the
 * whole picture, smaller, each framed in the lane's purple so a short one
 * still reads; the page's number on a small badge in the corner of a picture
 * at the lane's height.
 * Flip's lane is taller for them (h.laneHeight), and grows with the box in
 * the frame the box does.
 *
 * ZOOMED IN DEEP, THE WAVE FILLS THE BOX (the owner: yes). Where the wave
 * itself shows, it is drawn against the loudest moment in view rather than
 * the song's loudest, so a soft first note after a quiet intro, a pixel or
 * two tall against the whole song, stands as tall as the box just where a
 * start is placed. It glides there as the view does (fillTo); further out
 * the song is drawn as before, so loud and quiet still compare.
 *
 * THE TALLER BOX (the owner, with ACID's + and - for a track's height:
 * "expand it vertically too so it would become a bigger box showing more of
 * the wave"): the button after Magnify's - and + makes the box twice as tall,
 * and again puts it back. It glides (the owner, of the mock's: it "shook and
 * jerked"): its clock starts on the first frame it draws, the box moves in
 * whole pixels, the page scrolls by exactly what it grew so Hear the loop
 * stays where the thumb is (h.anchor), never so far that the timeline's top
 * goes under the header (h.ceiling), and each height is painted in the frame
 * it is laid out (the ResizeObserver, below). At once under Reduce Motion.
 * The height stays across songs and with the drawer put away.
 *
 * PINCH TO ZOOM (from Wavebox's "Zoom & Pan"; the owner: yes). Two fingers
 * on the timeline: sideways for Magnify, a rung for each doubling of the
 * distance between them; up and down for the box's height, following them,
 * up to three times as tall. Locked to whichever way they first move, and
 * two fingers, so it never fights one finger scrolling the page; a finger
 * already dragging stops where it is. On a desk, Ctrl and the wheel (a
 * trackpad's pinch sends the same) zoom in time; - and +, and the taller
 * box, stay for anyone who does not pinch.
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
 *   tempo()             { bpm, phase, bar } or null (bar: 3 for a song in
 *                       three, the dots bigger every third beat; else four)
 *   lane()              { seconds, marks: [[a, b, label?, ink?], ...], again }
 *                       (seconds; a page's number, Flip's, or a stroke's ink,
 *                       the Pad's; `again`, Flip's: { from, period } of the
 *                       part that goes round), computed when laneKey() moves
 *   laneHeight(box, base)  the lane's height in px for a box that tall
 *                       (optional; 26 without it)
 *   pageArt(n)          page n's own little picture, a canvas (optional)
 *   laneKey()           a cheap key that changes when the drawing does
 *   name(secs)          the words over the drawing's lane
 *   edge(which, t)      move an end there (during a drag)
 *   slide(start)        move the loop there, its length kept
 *   jump(start)         the same, gliding there and onto a beat (a tap on the
 *                       whole song)
 *   letGo(kind, which, zoomed)  a drag that moved something is over ('end' |
 *                       'slide'), magnified past 1x or not
 *   still()             Reduce Motion
 *   anchor()            what stays put on the screen as the box grows (Hear
 *                       the loop), or null
 *   ceiling()           where the header ends on the screen (0 if it is not
 *                       pinned): the timeline's top stays under it
 * Returns { draw, reset, focus(which), playhead(t), x(t), view(), held() }. */
(function (global) {
  'use strict';

  var SPAN = 1.28, LEAD = 0.09, EASE_MS = 70, ZONE = 28, GROW = 1.4, FADE_MS = 200;
  // MAGNIFY: the framing over 1 to 512, around the end last touched; zoomed
  // in, an end held near either edge carries the view along (PAN views a
  // second at the edge itself) instead of widening it. Under WAVE_AT samples a
  // point, the wave itself; under LINE_AT, the samples joined (below).
  var MAGS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512], PAN = 1.6, WAVE_AT = 64, LINE_AT = 8;
  var LANE = 26, GAP = 8, LOCK_PX = 6;
  // THE TALLER BOX: its glide, and as tall as a pinch takes it. Ctrl and the
  // wheel: a mouse's notch is a rung, a trackpad's pinch a rung each
  // WHEEL_STEP of its small deltas, as soon as one gesture adds up to it.
  var TALL_MS = 220, TALLEST = 3, WHEEL_STEP = 35;

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

  // THE LOOP'S EDGE LINE IS SHARP (the owner's pick in the whole-drawer
  // mock, "1.5px sharp", over 3px, 2px and a 1.5px left between the screen's
  // pixels): about 1.5px, rounded to the screen's own pixels (3 on a 2x
  // phone, 2 on a desk, 5 on a 3x phone), and laid on whole ones, so it is
  // one even line and never a blur across two. Where, for a line centred on
  // x: its left and its width in CSS px, `off` how far the box it is drawn in
  // sits from the screen's left (the screen's pixels count from there; 0 in
  // a canvas, whose own pixels are the screen's). The timeline's handles and
  // the copy under the header (lib/musicdrawer.js) draw theirs with it.
  function edge(x, dpr, off) {
    dpr = dpr || 1; off = off || 0;
    var w = Math.max(1, Math.round(1.5 * dpr)) / dpr;
    return [Math.round((off + x - w / 2) * dpr) / dpr - off, w];
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
    var beatIn = 1;                              // and how far its marks have faded in
    var magOut = root.querySelector('.mt-tl-mag-btn[data-mag="-1"]'), magIn = root.querySelector('.mt-tl-mag-btn[data-mag="1"]');
    var magVal = root.querySelector('.mt-tl-mag-val'), nameBox = root.querySelector('.mt-tl-namebox');
    var tallBtn = root.querySelector('.mt-tl-tall'), baseH = 0, tallTo = 0, tallRaf = 0;
    var gain = 0;   // the level the wave is drawn against (fillTo)
    var laneH = LANE;   // the drawing's lane as painted (h.laneHeight)
    // The rung's words take the widest rung's room (the CSS reads it here),
    // so - and + stay where they are as it steps.
    if (magVal) magVal.setAttribute('data-widest', MAGS[MAGS.length - 1] + '\u00d7');

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
      var gliding = beatTo(dt), filling = fillTo(dt);
      lastT = now;
      paint();
      // The view, for whoever reads it (the harness): the time at the left
      // edge and the seconds across, as painted, to the microsecond (at 512x
      // a phone's view is a few milliseconds across).
      if (view) root.dataset.view = view.v0.toFixed(6) + ' ' + view.span.toFixed(6);
      if ((!held && view !== goal) || (held && held.kind === 'end' && held.zone) || gliding || filling) request();
    }
    // ZOOMED IN DEEP, THE WAVE FILLS THE BOX (above): the level the wave is
    // drawn against eases to the loudest in view where the wave itself shows,
    // and to the song's loudest further out, with the view's own ease; at
    // once under Reduce Motion. True while on the way.
    function fillTo(dt) {
      var goal = fillGoal();
      if (!goal) { gain = 0; return false; }
      if (!gain || h.still()) { gain = goal; return false; }
      gain += (goal - gain) * (1 - Math.exp(-dt / EASE_MS));
      if (Math.abs(gain - goal) <= goal * 0.01) { gain = goal; return false; }
      return true;
    }
    function fillGoal() {
      var buf = h.buffer(), w = width();
      if (!buf || !peaks || peaks.buffer !== buf || !view || !(w > 0)) return 0;
      var sr = peaks.sr;
      if (view.span / w * sr >= WAVE_AT) return peaks.top;
      // As the wave is drawn: both channels as one (their mean).
      var d0 = buf.getChannelData(0), d1 = buf.numberOfChannels > 1 ? buf.getChannelData(1) : null, m = 0;
      for (var j = Math.max(0, Math.floor(view.v0 * sr)), j1 = Math.min(buf.length, Math.ceil((view.v0 + view.span) * sr)); j < j1; j++) {
        var v = d1 ? (d0[j] + d1[j]) / 2 : d0[j];
        if (v < 0) v = -v;
        if (v > m) m = v;
      }
      // A little room over the loudest; never so far up that a hush fills it.
      return Math.max(m * 1.08, peaks.top * 0.02);
    }
    // THE BEAT MARKS GLIDE when where a beat falls moves and the tempo does
    // not (a start let go magnified becomes a beat, lib/musicdrawer.js), with
    // the view's own ease and the shorter way round, so they move as one with
    // the settle and the reframing after it. A tempo moved by a 32nd or less
    // (an end let go magnified sets it, lib/musicdrawer.js, by an eighth of a
    // beat over 4 at most) glides too: each mark to its own new place, the
    // one the new beat counts from (the loop's start) staying put, so the
    // marks draw in to the end rather than jumping there. A new tempo is
    // there at once; a beat where there was none (one heard,
    // lib/musicears.js, as the loop glides to its pick, or the first one
    // tapped) fades in over FADE_MS rather than appearing in one frame. All
    // of it at once under Reduce Motion. True while on the way.
    function beatTo(dt) {
      var tp = h.tempo();
      if (!tp) { beat = null; return false; }
      if (!beat) { beat = { bpm: tp.bpm, phase: tp.phase }; beatIn = h.still() ? 1 : 0; return beatIn < 1; }
      if (beatIn < 1) { beatIn = h.still() ? 1 : Math.min(1, beatIn + dt / FADE_MS); if (beatIn < 1) { beat = { bpm: tp.bpm, phase: tp.phase }; return true; } }
      var p = 60 / tp.bpm, p0 = 60 / beat.bpm, k = 1 - Math.exp(-dt / EASE_MS);
      if (h.still() || Math.abs(p - p0) > p0 / 32 + 1e-5) { beat = { bpm: tp.bpm, phase: tp.phase }; return false; }
      if (beat.bpm !== tp.bpm) {
        // The old beat nearest where the new one counts from, and from there
        // the beat's length and its place together, so beat n of the old is
        // beat n of the new all the way; there once no mark in the song is a
        // tenth of a millisecond off.
        var a0 = beat.phase + Math.round((tp.phase - beat.phase) / p0) * p0, pk = p0 + (p - p0) * k, ak = a0 + (tp.phase - a0) * k;
        var far = (Math.abs(tp.phase) + trim().duration) / p + 1;
        if (Math.abs(pk - p) * far + Math.abs(ak - tp.phase) < 1e-4) { beat = { bpm: tp.bpm, phase: tp.phase }; return false; }
        beat = { bpm: 60 / pk, phase: ak };
        return true;
      }
      var d = tp.phase - beat.phase;
      d -= Math.round(d / p) * p;
      if (Math.abs(d) < 1e-4) { beat = { bpm: tp.bpm, phase: tp.phase }; return false; }
      beat = { bpm: tp.bpm, phase: beat.phase + d * k };
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
    // side kept, and the end follows the finger out. Not where that edge
    // already shows the song's start (or end): there is nothing past it, and
    // on a phone at 1x the song's start sits inside the edge's zone, so a
    // start held near where the music begins ran off to 0:00 (the owner: "It
    // snaps back to empty space").
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
      if (g.which === 'end' ? view.v0 + view.span >= t.duration : view.v0 <= 0) return;
      var grow = 1 + GROW * g.zone * dt, span = Math.min(most, view.span * grow);
      if (span === view.span) return;
      view = g.which === 'end' ? { v0: view.v0, span: span } : { v0: view.v0 + view.span - span, span: span };
      h.edge(g.which, T(Math.max(0, Math.min(w, g.x - rect().left))));
    }

    // A STROKE'S OWN INK ON THE LANE (above): its own hue kept, darker on a
    // light lane and lighter on a dark one (the way the lane's words are), a
    // fiftieth at a time until it reads 3:1 against the lane, and no further;
    // mixed toward the words instead, a yellow went olive. Worked out once
    // for each ink on each lane; a theme switched is a new lane.
    var inkMemo = {}, inkLane = '';
    function rgb(c) {
      var p = document.createElement('i');
      p.style.color = c; p.style.display = 'none'; root.appendChild(p);
      var said = global.getComputedStyle(p).color, n = (said.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);
      root.removeChild(p);
      return /^color\(/.test(said) ? n.map(function (v) { return v * 255; }) : n;
    }
    function lum(c) {
      return c.reduce(function (s, v, k) { v /= 255; v = v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); return s + [0.2126, 0.7152, 0.0722][k] * v; }, 0);
    }
    function contrast(a, b) { var p = lum(a), q = lum(b); return (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05); }
    // Where a 1px line lies on whole device pixels, nearest v.
    function crisp(v, dpr) { return (Math.round(v * dpr - dpr / 2) + dpr / 2) / dpr; }
    function hsl(c) {
      var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, hi = Math.max(r, g, b), lo = Math.min(r, g, b), d = hi - lo, l = (hi + lo) / 2, hu = 0;
      if (d) { hu = hi === r ? (g - b) / d : hi === g ? (b - r) / d + 2 : (r - g) / d + 4; hu = (hu * 60 + 360) % 360; }
      return [hu, d ? d / (1 - Math.abs(2 * l - 1)) : 0, l];
    }
    function fromHsl(hu, sa, l) {
      var c = (1 - Math.abs(2 * l - 1)) * sa, q = c * (1 - Math.abs((hu / 60) % 2 - 1)), m = l - c / 2;
      return [[c, q, 0], [q, c, 0], [0, c, q], [0, q, c], [q, 0, c], [c, 0, q]][Math.floor(hu / 60) % 6].map(function (v) { return Math.round((v + m) * 255); });
    }
    function laneInk(c, card, words) {
      if (card + '|' + words !== inkLane) { inkLane = card + '|' + words; inkMemo = { lane: rgb(card), words: rgb(words) }; }
      var key = 'k' + c;
      if (!inkMemo[key]) {
        var from = rgb(c), out = from, f = hsl(from), way = lum(inkMemo.words) < lum(inkMemo.lane) ? -1 : 1;
        for (var k = 1; k <= 50 && contrast(out, inkMemo.lane) < 3; k++) out = fromHsl(f[0], f[1], Math.max(0, Math.min(1, f[2] + way * k / 50)));
        inkMemo[key] = 'rgb(' + out.join(', ') + ')';
      }
      return inkMemo[key];
    }

    function paint() {
      var w = width(), hh = stage.clientHeight || 0, ok = h.hasTrack() && view;
      root.classList.toggle('empty', !ok);
      if (!(w > 0) || !(hh > 0)) return;      // shut: painted when it opens (sync)
      // The lane's height for the box as tall as it is now, in this frame,
      // and the handles' tops below it (styles.css reads --tl-lane).
      var lh = h.laneHeight ? Math.round(h.laneHeight(hh, base() || hh)) : LANE;
      if (lh !== laneH || !root.style.getPropertyValue('--tl-lane')) { laneH = lh; root.style.setProperty('--tl-lane', lh + 'px'); }
      var dpr = global.devicePixelRatio || 1, W = Math.round(w * dpr), H = Math.round(hh * dpr);
      if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
      var x = cv.getContext('2d');
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.clearRect(0, 0, w, hh);
      if (!ok) return;
      // What is painted, as it is painted, for whoever asks (the harness):
      // each mark on the drawing's lane, each comes-round line, each beat.
      var drawn = root._painted = { marks: [], lines: [], beats: [], boxes: [], turns: 0, beatIn: beatIn, lane: laneH, art: 0, tile: 0 };
      var st = getComputedStyle(root), tok = function (n) { return st.getPropertyValue(n).trim(); };
      var acc = tok('--accent'), ink = tok('--accent-ink'), fill = tok('--accent-fill') || acc;
      var card = tok('--menu-card'), line = tok('--menu-card-line'), paper = tok('--menu-paper') || card, strong = tok('--text-strong');
      var t = trim(), s0 = t.start, s1 = t.end, L = s1 - s0, xf = Math.min(h.crossfade() / 1000, L / 2), hl = L - xf;
      var dur = t.duration, ln = laneNow(), Dd = laneSecs, sTop = laneH + GAP, sH = hh - sTop;
      function rr(a, b, c, d, r) { x.beginPath(); if (x.roundRect) x.roundRect(a, b, c, d, r); else x.rect(a, b, c, d); }
      // CLOSE IN, THE WAVE ITSELF (above): both channels as one (their mean),
      // through the middle line at its zero, so where it crosses shows.
      function wave(sr, spp, mid, room) {
        var d0 = buf.getChannelData(0), d1 = buf.numberOfChannels > 1 ? buf.getChannelData(1) : null, n = buf.length, top = gain || peaks.top;
        var at = function (j) { return d1 ? (d0[j] + d1[j]) / 2 : d0[j]; };
        var xs0 = X(s0), xs1 = X(s1), j;
        drawn.song = spp < LINE_AT ? 'samples' : 'wave'; drawn.zero = +mid.toFixed(2); drawn.top = +top.toFixed(6);
        x.save();
        x.fillStyle = ink; x.globalAlpha = 0.65; x.fillRect(0, mid - 0.5, w, 1);
        x.fillStyle = acc;
        if (spp >= LINE_AT) {
          // Each point, the samples' least and most.
          for (var px = 0; px < w; px++) {
            var u0 = T(px), u1 = T(px + 1);
            if (u1 < 0 || u0 > dur) continue;
            var j0 = Math.max(0, Math.floor(u0 * sr)), j1 = Math.min(n, Math.ceil(u1 * sr)), lo = Infinity, hi = -Infinity;
            for (j = j0; j < j1; j++) { var v = at(j); if (v < lo) lo = v; if (v > hi) hi = v; }
            if (!(hi >= lo)) continue;
            x.globalAlpha = u1 > s0 && u0 < s1 ? 1 : 0.3;
            x.fillRect(px, mid - hi / top * room, 1, Math.max(1, (hi - lo) / top * room));
          }
        } else {
          // The samples themselves, joined; each a dot once 6px apart.
          var ja = Math.max(0, Math.floor(T(0) * sr) - 1), jb = Math.min(n - 1, Math.ceil(T(w) * sr) + 1);
          var path = function () {
            x.beginPath();
            for (var k = ja; k <= jb; k++) { if (k === ja) x.moveTo(X(k / sr), mid - at(k) / top * room); else x.lineTo(X(k / sr), mid - at(k) / top * room); }
            x.stroke();
          };
          x.strokeStyle = acc; x.lineWidth = 1.5; x.lineJoin = 'round';
          x.globalAlpha = 0.3; path();
          x.save(); x.beginPath(); x.rect(xs0, sTop, xs1 - xs0, sH); x.clip(); x.globalAlpha = 1; path(); x.restore();
          if (1 / spp >= 6) for (j = ja; j <= jb; j++) {
            var dx = X(j / sr);
            x.globalAlpha = dx >= xs0 && dx <= xs1 ? 1 : 0.3;
            x.beginPath(); x.arc(dx, mid - at(j) / top * room, 1.6, 0, 7); x.fill();
          }
        }
        x.restore();
      }

      // THE DRAWING, from the loop's start, in a box of its own: as much of
      // it as is in view, so where it runs past the timeline's edge it ends
      // there rounded, as the song's box under it does, not cut flat at the
      // canvas's edge; and its marks inside it, a dot at the drawing's very
      // end (drawn 60ms wide, so it can be seen) moved back to fit (the
      // owner: "things not fitting in the container").
      var a0 = X(s0), a1 = Dd > 0 ? X(s0 + Dd) : a0;
      x.lineWidth = 1;
      var laneBox = function (l, r) {
        var bl = Math.max(0.5, l), br = Math.min(w - 0.5, r);
        if (br - bl < 2) return null;
        rr(bl, 0.5, br - bl, laneH - 1, 8); x.fillStyle = card; x.fill(); x.strokeStyle = line; x.stroke();
        drawn.boxes.push([+bl.toFixed(2), +br.toFixed(2)]);
        return [bl, br];
      };
      if (Dd > 0) {
        var first = laneBox(a0, Math.max(a1, a0 + 8));
        var marks = ln && ln.marks || [], again = ln && ln.again, numbered = marks.length && marks[0][2] != null;
        // The first turn, then (Flip) the next ones, fainter, until the loop has come round.
        var turns = [[0, 0, Infinity]];
        if (again && again.period > 0) {
          for (var c = 1, o = Dd; s0 + o < s0 + hl - 0.02 && c < 64; c++, o += again.period) turns.push([c, o - again.from, s0 + hl]);
        }
        turns.forEach(function (tn) {
          var c2 = tn[0], off = tn[1], stop = tn[2], lastX = -1, box = first, end = a1;
          drawn.turns = c2 + 1;
          if (c2) {
            var b0 = X(s0 + off + again.from), b1 = Math.min(X(s0 + off + again.from + again.period), X(stop));
            if (b1 - b0 < 2) return;
            box = laneBox(b0, b1); end = b1;
          }
          if (!box) return;   // none of this turn is in view
          x.save(); rr(box[0], 0.5, box[1] - box[0], laneH - 1, 8); x.clip();
          for (var i = 0; i < marks.length; i++) {
            var m = marks[i];
            if (c2 && m[0] < again.from - 1e-9) continue;
            var A = X(s0 + off + m[0]), B = X(Math.min(s0 + off + m[1], stop));
            if (B <= A + 0.25 && c2) continue;
            // Painted at least 3px wide (a page's mark 6, inset 1.5 each
            // side): one that would end past the drawing moves back to end
            // on it.
            var over = Math.max(B, A + (numbered ? 6 : 3)) - end;
            if (over > 0) { A -= over; B -= over; }
            if (A > w + 2) break;
            if (B < -2) continue;
            if (!numbered && A < lastX + 1) { A = lastX + 1; if (B < A) continue; }   // strokes closer than a pixel: one mark
            x.globalAlpha = c2 ? 0.45 : 1;
            var art = numbered && h.pageArt ? h.pageArt(m[2]) : null;
            var py = 4;
            if (art && art.width && art.height) {
              // A PAGE AS ITS OWN LITTLE PICTURE (above), its own shape kept:
              // as long as its picture or longer, the picture at the lane's
              // height, one centred on the page's time and the rest either
              // side; shorter, the whole picture, smaller, so where things
              // are on the page still reads.
              var pl = A + 1.5, pw = Math.max(3, B - A - 3), ph = laneH - 8, tw = ph * art.width / art.height, sh = ph;
              if (pw >= tw) {
                var tx = pl + (pw - tw) / 2; tx -= Math.ceil((tx - pl) / tw) * tw;
                x.save(); rr(pl, 4, pw, ph, 4); x.clip();
                for (; tx < pl + pw; tx += tw) x.drawImage(art, tx, 4, tw, ph);
                x.restore();
              } else {
                sh = pw * art.height / art.width; py = 4 + (ph - sh) / 2;
                x.save(); rr(pl, py, pw, sh, 3); x.clip(); x.drawImage(art, pl, py, pw, sh); x.restore();
              }
              // Framed in the lane's purple, on the screen's own pixels so it
              // is crisp (as the loop's edges are): a short page's picture is
              // small, and its frame is what shows it is there.
              var fl = crisp(pl, dpr), ft = crisp(py, dpr);
              rr(fl, ft, crisp(pl + pw, dpr) - fl, crisp(py + sh, dpr) - ft, sh < ph ? 3 : 4); x.strokeStyle = ink; x.stroke();
              drawn.art++; drawn.tile = +tw.toFixed(2);
            } else {
              x.fillStyle = numbered ? fill : m[3] ? laneInk(m[3], card, strong) : acc;
              rr(A + (numbered ? 1.5 : 0), numbered ? 4 : 6, Math.max(3, B - A - (numbered ? 3 : 0)), laneH - (numbered ? 8 : 12), numbered ? 4 : 3);
              x.fill();
            }
            drawn.marks.push([+A.toFixed(2), +B.toFixed(2), c2]);
            lastX = B;
            if (numbered && !c2 && (art ? pw >= tw : B - A > 18)) {
              x.globalAlpha = 1; x.textBaseline = 'middle';
              if (art) {
                // Its number on a small badge in the picture's corner, where
                // the page is its picture at the lane's height (on a smaller
                // one the badge would hide most of it).
                x.font = '650 10px ' + st.fontFamily;
                var nb = x.measureText(String(m[2])).width + 8;
                rr(A + 3.5, 6.5, nb, 13, 6.5); x.fillStyle = fill; x.fill();
                x.fillStyle = '#fff'; x.fillText(String(m[2]), A + 7.5, 13.5);
              } else {
                x.font = '650 11px ' + st.fontFamily; x.fillStyle = '#fff'; x.fillText(String(m[2]), A + 6, laneH / 2 + 0.5);
              }
            }
          }
          x.restore();
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
        x.setLineDash([4, 4]); rr(a0, 0.5, Math.max(40, w * 0.25), laneH - 1, 8); x.strokeStyle = line; x.stroke(); x.setLineDash([]);
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
        var sr = peaks.sr, spp = view.span / w * sr;
        if (spp < WAVE_AT) wave(sr, spp, mid, room);
        else {
          drawn.song = 'loudness';
          for (var px = 0; px < w; px += 2) {
            var u0 = T(px), u1 = T(px + 2);
            if (u1 < 0 || u0 > dur) continue;
            var v = peakOf(peaks, Math.max(0, u0), Math.min(dur, u1)), hgt = Math.max(1, v * room), inside = u1 > s0 && u0 < s1;
            x.globalAlpha = inside ? 1 : 0.3;
            x.fillRect(px, mid - hgt, 1.5, hgt * 2);
          }
        }
        x.globalAlpha = 1;
      }
      var tp = beat;
      if (tp) {
        var p = 60 / tp.bpm, ppb = p / view.span * w, k0 = Math.round((s0 - tp.phase) / p), nb = (h.tempo() || {}).bar === 3 ? 3 : 4;
        for (var kb = Math.ceil((Math.max(0, view.v0) - tp.phase) / p); tp.phase + kb * p <= Math.min(dur, view.v0 + view.span); kb++) {
          var bar = ((kb - k0) % nb + nb) % nb === 0;
          if (ppb < 6 && !bar) continue;
          if (ppb * nb < 6 && ((kb - k0) % (4 * nb) + 4 * nb) % (4 * nb)) continue;
          x.fillStyle = ink; x.globalAlpha = (bar ? 0.9 : 0.75) * beatIn;
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

      // THE LOOP'S TWO EDGES, painted here, on the screen's own pixels (edge,
      // above), over the song: a box laid on them as the handle's line was
      // is snapped to whole CSS pixels first and then moved by its handle's
      // fraction, so a 1.5px line came out 2px wide and soft at both sides.
      // Each handle's tab (over the canvas) sits on its line's foot.
      x.fillStyle = acc;
      drawn.edges = [s0, s1].map(function (s) {
        var ln = edge(X(s), dpr, 0);
        if (ln[0] + ln[1] > 0 && ln[0] < w) x.fillRect(ln[0], sTop, ln[1], sH);
        return ln;
      });

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
      if (e.touches && e.touches.length > 1) return pinch(e);
      var pt = EP.at(e), r = rect(), y = pt.clientY - r.top, hd = e.target.closest && e.target.closest('.mt-tl-handle');
      if (!hd && y < laneH + GAP / 2) return null;                 // the drawing stays put
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
    // PINCH TO ZOOM (above): the second finger down on the timeline. The
    // one already down stops where it is; then sideways is Magnify's rungs,
    // the nearest to the fingers' spread (twice as far apart, one rung in),
    // and up and down the box's height, following them.
    function spread(ev) {
      var a = ev.touches[0], b = ev.touches[1];
      return [Math.max(20, Math.abs(a.clientX - b.clientX)), Math.max(20, Math.abs(a.clientY - b.clientY))];
    }
    function pinch(e) {
      if (held) { held.dead = true; held = null; root.classList.remove('holding'); }
      e.preventDefault();
      var s0 = spread(e), i0 = MAGS.indexOf(mag), h0 = stage.getBoundingClientRect().height, axis = null;
      return {
        move: function (cx, ev) {
          if (!ev || !ev.touches || ev.touches.length < 2) return;
          if (ev.cancelable) ev.preventDefault();
          var s = spread(ev), rx = s[0] / s0[0], ry = s[1] / s0[1];
          if (!axis && (Math.abs(rx - 1) > 0.08 || Math.abs(ry - 1) > 0.08)) axis = Math.abs(rx - 1) >= Math.abs(ry - 1) ? 'x' : 'y';
          if (axis === 'x') {
            var i = Math.max(0, Math.min(MAGS.length - 1, i0 + Math.round(Math.log(rx) / Math.LN2)));
            if (MAGS[i] !== mag) { mag = MAGS[i]; syncMag(); draw(); }
          } else if (axis === 'y') tall(h0 * ry, false);
        },
        end: function () { draw(); }
      };
    }
    if (D && stage) D.bind(stage, grab);
    // Ctrl and the wheel on a desk, or a trackpad's pinch: Magnify's rungs.
    var wheelSum = 0, wheelAt = -1e9;
    if (stage) stage.addEventListener('wheel', function (e) {
      if (!e.ctrlKey || !h.hasTrack() || !view) return;
      e.preventDefault();
      if (e.timeStamp - wheelAt > 300) wheelSum = 0;
      wheelAt = e.timeStamp;
      wheelSum += e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      if (Math.abs(wheelSum) >= WHEEL_STEP) { step(wheelSum < 0 ? 1 : -1); wheelSum = 0; }
    }, { passive: false });
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

    // THE TALLER BOX (above). The box's own height is the stylesheet's; any
    // other is set on it, in whole pixels.
    function base() {
      if (!baseH && !stage.style.height) baseH = stage.getBoundingClientRect().height;
      return baseH;
    }
    function heightNow() { return stage.getBoundingClientRect().height; }
    function syncTall() {
      if (!tallBtn) return;
      var b = base(), on = b > 0 && (tallTo || heightNow()) > b + 0.5;
      if (tallBtn.getAttribute('aria-pressed') !== String(on)) tallBtn.setAttribute('aria-pressed', String(on));
      tallBtn.disabled = !h.hasTrack();
    }
    // To `to` px: gliding (a tap), Hear the loop kept where it is on the
    // screen; or at once (a pinch, which the box follows as the fingers do).
    function tall(to, glide) {
      var b = base();
      if (!(b > 0)) return;
      to = Math.round(Math.max(b, Math.min(TALLEST * b, to)));
      if (tallRaf) global.cancelAnimationFrame(tallRaf);
      var from = Math.round(heightNow()), D = glide && !h.still() ? TALL_MS : 0, start = null;
      var anchor = glide && h.anchor ? h.anchor() : null;
      tallTo = to;
      syncTall();
      function frameTall(now) {
        tallRaf = 0;
        // The clock starts on the first frame it draws: one taken before it
        // ran that frame backwards, and the mock's box shrank before it grew.
        if (start === null) start = now;
        var f = D ? Math.min(1, (now - start) / D) : 1, e = 1 - Math.pow(1 - f, 3);
        var hh = Math.round(from + (to - from) * e);
        if (hh !== Math.round(heightNow())) {
          var y0 = anchor && anchor.offsetParent !== null ? anchor.getBoundingClientRect().top : null, top0 = root.getBoundingClientRect().top;
          stage.style.height = hh === b ? '' : hh + 'px';
          if (y0 !== null) {
            // Scrolled by exactly what Hear moved, read off Hear itself (a
            // scroll that waited for half a pixel of drift shook it); growing,
            // never so far that the timeline's top goes under the header.
            var dy = anchor.getBoundingClientRect().top - y0;
            if (dy > 0) dy = Math.min(dy, Math.max(0, Math.floor(top0 - (h.ceiling ? h.ceiling() : 0) - 4)));
            if (dy) global.scrollBy(0, dy);
          }
        }
        if (f < 1) tallRaf = global.requestAnimationFrame(frameTall);
        else { tallTo = 0; syncTall(); }
      }
      tallRaf = global.requestAnimationFrame(frameTall);
    }
    if (tallBtn) tallBtn.addEventListener('click', function () {
      var b = base();
      if (tallBtn.disabled || !(b > 0)) return;
      tall((tallTo || heightNow()) > b + 0.5 ? b : 2 * b, true);
    });
    syncTall();

    // The playhead: where the song is, on the song, while something plays.
    function playhead(t) {
      if (!ph) return;
      var w = width(), at = view && t != null ? X(t) : -1;
      ph.hidden = !(at >= 0 && at <= w);
      if (!ph.hidden) ph.style.transform = 'translateX(' + at.toFixed(2) + 'px)';
    }

    // THE BEAT LIGHTS AS IT IS HEARD (the owner's pick in the whole-drawer
    // mock): while Hear the loop plays, lib/musicdrawer.js asks for each beat
    // as it reaches the ear, and a light over its dot glows, bigger on a bar,
    // and fades. Web Animations, so Reduce Motion is honoured here (it fades,
    // with no swell) and the player's sheet carries no keyframes for a drawer
    // it never has. What it lit last, for whoever asks (the harness): root._lit.
    var lit = null;
    function pulse(t, bar) {
      if (!view || !stage) return;
      var w = width(), at = X(t);
      if (!(at >= -6 && at <= w + 6)) return;
      if (!lit) { lit = document.createElement('span'); lit.className = 'mt-tl-lit'; lit.setAttribute('aria-hidden', 'true'); stage.appendChild(lit); }
      lit.classList.toggle('bar', !!bar);
      lit.style.left = at.toFixed(2) + 'px';
      lit.style.top = (laneH + GAP + 8) + 'px';
      if (lit.getAnimations) lit.getAnimations().forEach(function (a) { a.cancel(); });
      var still = h.still && h.still();
      if (lit.animate) {
        lit.animate(still ? [{ opacity: 1 }, { opacity: 0 }]
          : [{ opacity: 1, transform: 'scale(1.5)' }, { opacity: 0.85, offset: 0.6 }, { opacity: 0, transform: 'scale(1)' }],
          { duration: 450, easing: still ? 'linear' : 'cubic-bezier(.2, .8, .2, 1)' });
      }
      var was = root._lit;
      root._lit = { n: (was ? was.n : 0) + 1, x: +at.toFixed(2), bar: !!bar, t: +t.toFixed(4), at: global.performance ? global.performance.now() : 0 };
    }

    // A new layout (the sheet opened, the phone turned, the box taller):
    // painted at the new size in the frame it is laid out, for the observer
    // runs after layout and before the frame is shown. Asked for the next
    // frame, every frame of the taller box's glide showed the one before
    // stretched to fit (the owner: it "shook").
    if (global.ResizeObserver && stage) new global.ResizeObserver(function () { if (view) { words(); paint(); } else draw(); }).observe(stage);
    // A theme switched: the tokens are read as it paints.
    if (global.matchMedia) {
      var mq = global.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', draw);
    }
    if (global.MutationObserver) new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return {
      draw: function () { syncMag(); syncTall(); draw(); },
      // A new song: the view starts where it belongs, not where the last was,
      // at 1x on its start.
      reset: function () { lane = null; view = null; mag = 1; focus = 'start'; beat = null; syncMag(); draw(); },
      // An end moved anywhere else (- and +, a typed time, the Restart view):
      // magnified, the view goes to it.
      focus: function (which) { if ((which === 'start' || which === 'end') && which !== focus) { focus = which; draw(); } },
      playhead: playhead,
      pulse: pulse,
      x: function (t) { return view ? X(t) : null; },
      view: function () { return view ? { v0: view.v0, span: view.span } : null; },
      held: function () { return held ? held.kind : null; },
      // The song's levels as painted (peaksOf), for where it is silent.
      peaks: function () { return peaks; }
    };
  }

  global.SkriblMusicTimeline = { create: create, peaksOf: peaksOf, peakOf: peakOf, edge: edge };
})(window);
