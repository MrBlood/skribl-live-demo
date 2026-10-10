/* The video both editors make where WebCodecs cannot make an MP4: ONE exporter.
 *
 *   SkriblVideoRecord.recordVideo({
 *     canvas,          the canvas each frame is painted on
 *     fps,             frames a second
 *     frames,          how many frames
 *     draw(k),         paint frame k (0-based) on the canvas
 *     music,           the AudioBuffer to carry, or null for none
 *     progress(f),     0..1 as frames go in
 *     cancelled(),     true once the person cancels
 *     done(blob, ext, info), fail(why), cancel()
 *   })  -> true when recording started, false when it could not
 *
 * WHY ONE. The v321 outside audit (SK-AUD-001/002/003) found the two editors'
 * MediaRecorder fallbacks had drifted: the Pad mixed its music into the stream
 * and Flip recorded the canvas alone, under an export sheet that says "Your
 * animation, with music" -- and Flip took that path exactly when the music was
 * on and the browser could not encode AAC for the MP4, so turning the music on
 * was what lost it. Flip also painted its first page before recording started
 * and again on the first tick (three pages decoded as four), and neither
 * checked what came out: a recorder that produced nothing downloaded a 0-byte
 * file and said "exported". Two copies are how it drifted, so there is one
 * now. Each editor says only what is its own: how many frames, how to paint
 * one, and which loop to play under them. The MP4 path is shared already
 * (lib/mp4export.js).
 *
 * ONE FRAME PER TICK, PUSHED. captureStream(0) with requestFrame() puts a frame
 * in the video exactly when one is pushed, so frame 0 goes in once the
 * recorder runs, then one per tick, and nothing is added or dropped by a
 * sampling clock. The stop waits one more tick so the last frame keeps its
 * time. Where requestFrame is missing it falls back to captureStream(fps),
 * which samples the canvas itself.
 *
 * THE MUSIC is the loop the post and the MP4 use (the trimmed, crossfaded
 * buffer), played on a looping source into a MediaStreamDestination whose
 * track joins the stream; it starts with the recorder and stops with it. If it
 * cannot be added, info.withoutMusic is true and the editor says so.
 *
 * A RECORDING IS A SUCCESS ONLY IF SOMETHING CAME OUT: at least one chunk, a
 * blob with bytes in it, the container's own signature at its start (EBML for
 * WebM, `ftyp` for MP4) and no recorder error. A check of the start is not a
 * decoder; it is what tells a file from a 0-byte or garbage download. fail()
 * gets 'start' | 'empty' | 'unreadable' | a recorder error's name.
 */
(function (global) {
  'use strict';

  var TYPES = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9',
               'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];

  function capture(canvas, fps) {
    var s = canvas.captureStream(0), t = s.getVideoTracks()[0];
    if (t && typeof t.requestFrame === 'function') {
      return { stream: s, manual: true, push: function () { try { t.requestFrame(); } catch (e) {} } };
    }
    if (t) t.stop();
    return { stream: canvas.captureStream(fps), manual: false, push: function () {} };
  }

  function music(buffer, stream) {
    if (!buffer) return null;
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) return null;
    var ctx, dest, src;
    try {
      ctx = new AC();
      dest = ctx.createMediaStreamDestination();
      dest.stream.getAudioTracks().forEach(function (t) { stream.addTrack(t); });
    } catch (e) { return null; }
    return {
      start: function () {
        try {
          if (ctx.state === 'suspended') ctx.resume();
          src = ctx.createBufferSource();
          src.buffer = buffer; src.loop = true;
          src.connect(dest);
          src.start();
        } catch (e) {}
      },
      // Called from the stop AND the recorder's own onstop; once is enough,
      // and a second close() rejects ("Cannot close a closed AudioContext").
      stop: function () {
        if (!ctx) return;
        try { if (src) src.stop(); } catch (e) {}
        var c = ctx; ctx = null;
        try { var p = c.close(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      }
    };
  }

  function looksLike(bytes, mime) {
    if (/mp4/.test(mime)) return bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70;
    return bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3;
  }

  function recordVideo(o) {
    if (typeof MediaRecorder === 'undefined' || !o.canvas.captureStream) { o.fail('start'); return false; }
    var mime = TYPES.filter(function (t) { return MediaRecorder.isTypeSupported(t); })[0];
    if (!mime) { o.fail('start'); return false; }
    var cap = capture(o.canvas, o.fps), bed = music(o.music, cap.stream);
    var chunks = [], error = null, rec, iv = null, k = 0;
    var end = function () { if (iv) clearInterval(iv); iv = null; if (bed) bed.stop(); };
    try { rec = new MediaRecorder(cap.stream, { mimeType: mime }); }
    catch (e) { end(); o.fail('start'); return false; }
    rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
    rec.onerror = function (e) { error = (e && e.error && e.error.name) || 'error'; };
    rec.onstop = function () {
      end();
      if (o.cancelled && o.cancelled()) { o.cancel(); return; }
      var type = mime.split(';')[0], blob = new Blob(chunks, { type: type });
      if (error) { o.fail(error); return; }
      if (!chunks.length || !blob.size) { o.fail('empty'); return; }
      blob.slice(0, 8).arrayBuffer().then(function (ab) {
        if (!looksLike(new Uint8Array(ab), mime)) { o.fail('unreadable'); return; }
        o.done(blob, /mp4/.test(type) ? 'mp4' : 'webm', { withoutMusic: !!o.music && !bed });
      }, function () { o.fail('unreadable'); });
    };
    var stop = function () { end(); try { rec.stop(); } catch (e) { o.fail('error'); } };
    var tick = function () { o.draw(k); cap.push(); k++; if (o.progress) o.progress(k / o.frames); };
    if (!cap.manual) o.draw(0);   // auto capture samples whatever is there from the start
    rec.start();
    if (bed) bed.start();
    tick();
    iv = setInterval(function () {
      if (o.cancelled && o.cancelled()) { stop(); return; }
      if (k >= o.frames) { stop(); return; }   // one tick after the last frame: it keeps its time
      tick();
    }, 1000 / o.fps);
    return true;
  }

  global.SkriblVideoRecord = { recordVideo: recordVideo };
})(window);
