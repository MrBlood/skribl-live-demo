/* Recording a canvas to a video file, and refusing to call an empty one a success.
 *
 *   SkriblVideoRecord.capture(canvas, fps)        -> { stream, push(), manual }
 *   SkriblVideoRecord.music(audioBuffer, stream)  -> { start(), stop() } or null
 *   SkriblVideoRecord.record(stream, mime, opts)  -> MediaRecorder or null
 *
 * WHY THIS EXISTS: the v321 outside audit (SK-AUD-001/002/003). Both editors
 * record video with MediaRecorder where WebCodecs cannot make an MP4, and the
 * two copies had drifted: the Pad mixed its music into the stream and Flip
 * recorded the canvas alone, under an export sheet that says "Your animation,
 * with music"; Flip painted its first page once before recording started and
 * again on the first tick, so the first page played twice; and neither checked
 * what came out -- a recorder that produced nothing downloaded a 0-byte file
 * and said "exported". The parts the two must agree on live here.
 *
 * CAPTURE IS MANUAL WHERE IT CAN BE. captureStream(0) with requestFrame() puts
 * a frame in the video exactly when the caller pushes one, so a page lasts as
 * long as the caller holds it and no frame is added or dropped by a sampling
 * clock. Where requestFrame is missing it falls back to captureStream(fps),
 * which samples the canvas on its own; push() is then a no-op.
 *
 * MUSIC is the loop the post and the MP4 use -- the caller hands over the
 * trimmed, crossfaded AudioBuffer -- played on a looping source into a
 * MediaStreamDestination whose track joins the video's stream. start() is
 * called when recording starts and stop() when it ends, so the sound lines up
 * with the first frame and does not run on after the last.
 *
 * A RECORDING IS A SUCCESS ONLY IF SOMETHING CAME OUT: at least one chunk, a
 * blob with bytes in it, and the container's own signature at its start (the
 * EBML magic for WebM, `ftyp` for MP4), with no recorder error on the way. A
 * check of the start is not a decoder; it is what tells "a file" from "a
 * zero-byte or garbage download", which is the failure the audit found.
 *
 * record(stream, mime, { done(blob), fail(why), cancelled(), cancel() })
 *   done      a usable recording
 *   fail      'start' | 'empty' | 'unreadable' | a recorder error's name
 *   cancelled () => true when the person cancelled; cancel() is then called
 *              instead of either of the others
 */
(function (global) {
  'use strict';

  function capture(canvas, fps) {
    var s = canvas.captureStream(0), t = s.getVideoTracks()[0];
    if (t && typeof t.requestFrame === 'function') {
      return { stream: s, manual: true, push: function () { t.requestFrame(); } };
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
      stop: function () {
        try { if (src) src.stop(); } catch (e) {}
        try { ctx.close(); } catch (e) {}
      }
    };
  }

  function looksLike(bytes, mime) {
    if (/mp4/.test(mime)) return bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70;
    return bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3;
  }

  function record(stream, mime, o) {
    var chunks = [], error = null, rec;
    try { rec = new MediaRecorder(stream, { mimeType: mime }); }
    catch (e) { o.fail('start'); return null; }
    rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
    rec.onerror = function (e) { error = (e && e.error && e.error.name) || 'error'; };
    rec.onstop = function () {
      if (o.cancelled && o.cancelled()) { o.cancel(); return; }
      var blob = new Blob(chunks, { type: mime.split(';')[0] });
      if (error) { o.fail(error); return; }
      if (!chunks.length || !blob.size) { o.fail('empty'); return; }
      blob.slice(0, 8).arrayBuffer().then(function (ab) {
        if (looksLike(new Uint8Array(ab), mime)) o.done(blob); else o.fail('unreadable');
      }, function () { o.fail('unreadable'); });
    };
    return rec;
  }

  global.SkriblVideoRecord = { capture: capture, music: music, record: record };
})(window);
