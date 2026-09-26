/* The music drawer's zoomed loop view: which stretch of the track it shows,
 * where the two trim handles sit in it, and the waveform drawn into it.
 * ONE implementation for both editors (SK312-003, v315).
 *
 * WHY. getZoomWindow was word-for-word the same in Pad and Flip (0.99 by
 * harness/tools/editordup.py), updateZoomHandles 0.87 and drawZoomWaveform
 * 0.82 -- the same maths and the same drawing, formatted differently. Pad's
 * copy is the base. Everything here is a pure function of what the caller
 * hands in, so neither editor's state model had to change: each passes its
 * own trimStart/trimEnd/zoom state in and keeps its own globals.
 *
 * Editors only. The player loads lib/looptrim.js (the trim rules it replays
 * with) but never this -- it has no music drawer -- and Pad's copy leaving
 * app.js takes it out of the player's download too.
 */
(function (global) {
  'use strict';

  /* s: {start, end, duration, mag, center, focus} -- the loop's trim, the
   * track length, the zoom magnification, an explicit centre (a pan) or null,
   * and what the view centres on otherwise ('start' | 'end' | 'loop'). */
  function zoomWindow(s) {
    var loopDuration = Math.max(0, s.end - s.start);
    var contextSeconds = Math.max(1, Math.min(4, loopDuration * 0.25));
    var halfSpan = (loopDuration / 2 + contextSeconds) / s.mag;
    var center;
    if (s.center != null) center = s.center;
    else if (s.focus === 'start') center = s.start;
    else if (s.focus === 'end') center = s.end;
    else center = (s.start + s.end) / 2;
    var lo = halfSpan, hi = Math.max(halfSpan, s.duration - halfSpan);
    center = Math.max(lo, Math.min(center, hi));
    var start = Math.max(0, center - halfSpan);
    var end = Math.min(s.duration, center + halfSpan);
    if (end - start < 0.001) end = Math.min(s.duration, start + 0.001);
    return { start: start, end: end, duration: Math.max(0.001, end - start) };
  }

  /* The two handles as percentages of the zoom track, and whether each is in
   * view (a little slack either side so a handle at the very edge still shows). */
  function handles(trimStart, trimEnd, zw) {
    var s = ((trimStart - zw.start) / zw.duration) * 100;
    var e = ((trimEnd - zw.start) / zw.duration) * 100;
    return { startPct: s, endPct: e, startShown: s >= -2 && s <= 102, endShown: e >= -2 && e <= 102 };
  }

  /* o: {canvas, ctx, buffer, trimStart, trimEnd, crossfadeMs, zw, label,
   *     formatTime} -- draws the zoomed waveform, the loop band and its edges,
   * the crossfade zones, and writes the label. */
  function drawZoom(o) {
    var canvas = o.canvas, ctx = o.ctx, buffer = o.buffer;
    if (!buffer || !canvas) return;
    var rect = canvas.getBoundingClientRect();
    if (!rect.width) return;
    var dpr = global.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var w = rect.width, h = rect.height, mid = h / 2;
    var loopDuration = o.trimEnd - o.trimStart;
    var zw = o.zw;

    ctx.fillStyle = '#161a22';
    ctx.fillRect(0, 0, w, h);

    var data = buffer.getChannelData(0), sampleRate = buffer.sampleRate;
    var startSample = Math.max(0, Math.floor(zw.start * sampleRate));
    var endSample = Math.min(data.length, Math.floor(zw.end * sampleRate));
    var samplesPerPixel = Math.max(1, Math.floor(Math.max(1, endSample - startSample) / w));

    function columns(x0, x1) {
      for (var x = x0; x < x1; x++) {
        var sStart = startSample + x * samplesPerPixel;
        var sEnd = Math.min(sStart + samplesPerPixel, endSample);
        var min = 1, max = -1;
        for (var i = sStart; i < sEnd; i++) {
          var v = data[i] || 0;
          if (v < min) min = v;
          if (v > max) max = v;
        }
        var y1 = mid + min * mid * 0.9, y2 = mid + max * mid * 0.9;
        ctx.fillRect(x, y1, 1, Math.max(1, y2 - y1));
      }
    }

    ctx.fillStyle = '#3a4150';
    columns(0, w);

    var loopStartX = ((o.trimStart - zw.start) / zw.duration) * w;
    var loopEndX = ((o.trimEnd - zw.start) / zw.duration) * w;
    ctx.fillStyle = 'rgba(124, 92, 255, 0.2)';
    ctx.fillRect(loopStartX, 0, loopEndX - loopStartX, h);
    ctx.fillStyle = '#7c5cff';
    columns(Math.floor(loopStartX), Math.ceil(loopEndX));
    ctx.fillStyle = '#7c5cff';
    ctx.fillRect(loopStartX, 0, 2, h);
    ctx.fillRect(loopEndX - 2, 0, 2, h);

    if (o.crossfadeMs > 0 && loopDuration > 0) {
      var loopFrames = Math.floor(loopDuration * sampleRate);
      var xfadeFrames = Math.min(Math.floor((o.crossfadeMs / 1000) * sampleRate), Math.floor(loopFrames / 2));
      var xfadeW = ((xfadeFrames / sampleRate) / zw.duration) * w;
      if (xfadeW > 0) {
        var headX = loopStartX;           // fade-in: the loop tail is mixed in here
        var tailX = loopEndX - xfadeW;     // folded over the head / trimmed from the end
        ctx.fillStyle = 'rgba(255, 176, 32, 0.22)';
        ctx.fillRect(headX, 0, xfadeW, h);
        ctx.fillRect(tailX, 0, xfadeW, h);
        ctx.fillStyle = 'rgba(255, 176, 32, 0.9)';
        for (var yy = 0; yy < h; yy += 9) {
          ctx.fillRect(headX + xfadeW - 1, yy, 1.5, 5);
          ctx.fillRect(tailX, yy, 1.5, 5);
        }
      }
    }

    ctx.fillStyle = '#2e3340';
    ctx.fillRect(0, mid, w, 1);

    if (o.label && o.formatTime) {
      var xfLabel = o.crossfadeMs > 0 ? '  ·  xfade ' + o.crossfadeMs + 'ms' : '';
      o.label.textContent = o.formatTime(o.trimStart) + ' → ' + o.formatTime(o.trimEnd)
        + ' [' + loopDuration.toFixed(2) + 's]' + xfLabel;
    }
  }

  global.SkriblLoopWave = { zoomWindow: zoomWindow, handles: handles, drawZoom: drawZoom };
})(window);
