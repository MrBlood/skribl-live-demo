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
 * WebM, `ftyp` for MP4), a frame inside it, and no recorder error. A check of
 * the start is not a decoder; it is what tells a file from a 0-byte or garbage
 * download. fail() gets 'start' | 'empty' | 'unreadable' | a recorder error's
 * name.
 *
 * A SIGNATURE IS NOT A VIDEO (after v325). The evidence run for the v325 audit
 * caught Chromium's recorder, on a loaded machine, handing back a WebM with no
 * frame in it: it passed the signature check, downloaded, and the chip said
 * "Animation exported". Rare (once, then not in 76 more tries, 64 under load), but
 * a false success, so a finished file must now hold a frame: a block on a
 * WebM's video track, or an MP4 `mdat` with bytes in it, looked for in the
 * file's first 4 MB (a header alone is a few hundred bytes, so a file larger
 * than that is not one). Otherwise it is 'empty', and the editor says so.
 * Still not a decoder: enough to tell a video from a header.
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

  var SCAN = 4 * 1024 * 1024;

  // An EBML variable-length integer at b[i]: {v, n} (n bytes long), or null
  // past the end. `marker` keeps the length bits, as element IDs are written.
  function vint(b, i, marker) {
    if (i >= b.length) return null;
    var first = b[i], mask = 0x80, n = 1;
    while (n <= 8 && !(first & mask)) { mask >>= 1; n++; }
    if (n > 8 || i + n > b.length) return null;
    var v = marker ? first : first & (mask - 1);
    for (var k = 1; k < n; k++) v = v * 256 + b[i + k];
    return { v: v, n: n };
  }

  // Blocks on a WebM's video tracks (TrackType 1). Segment, Cluster, Tracks,
  // TrackEntry and BlockGroup are entered rather than skipped, which also
  // copes with the unknown sizes MediaRecorder writes; anything else is
  // skipped whole. The same walk verify_videoexport reads files with.
  var ENTER = { 0x18538067: 1, 0x1F43B675: 1, 0x1654AE6B: 1, 0xA0: 1 };
  function webmVideoBlocks(b) {
    var types = {}, blocks = {}, num = null, type = null, i = 0, n = 0, tn;
    function keep() { if (num !== null) types[num] = type; num = type = null; }
    while (i < b.length - 2) {
      var id = vint(b, i, true), sz = id && vint(b, i + id.n, false);
      if (!sz) break;
      var body = i + id.n + sz.n;
      if (ENTER[id.v]) { i = body; continue; }
      if (id.v === 0xAE) { keep(); i = body; continue; }                 // TrackEntry
      if (id.v === 0xD7 || id.v === 0x83) {                              // TrackNumber, TrackType
        var x = 0;
        for (var k = 0; k < sz.v && body + k < b.length; k++) x = x * 256 + b[body + k];
        if (id.v === 0xD7) num = x; else type = x;
      } else if (id.v === 0xA3 || id.v === 0xA1) {                       // SimpleBlock, Block
        keep();
        var t = vint(b, body, false);
        if (t) blocks[t.v] = (blocks[t.v] || 0) + 1;
      }
      i = body + sz.v;
    }
    keep();
    for (tn in blocks) if (types[tn] === 1) n += blocks[tn];
    return n;
  }

  // An MP4's top-level boxes, walked for an mdat with bytes in it.
  function mp4HasSamples(b) {
    var i = 0;
    while (i + 8 <= b.length) {
      var size = b[i] * 16777216 + (b[i + 1] << 16) + (b[i + 2] << 8) + b[i + 3], head = 8;
      var type = String.fromCharCode(b[i + 4], b[i + 5], b[i + 6], b[i + 7]);
      if (size === 1 && i + 16 <= b.length) {
        size = (b[i + 8] * 16777216 + (b[i + 9] << 16) + (b[i + 10] << 8) + b[i + 11]) * 4294967296
             + b[i + 12] * 16777216 + (b[i + 13] << 16) + (b[i + 14] << 8) + b[i + 15];
        head = 16;
      } else if (size === 0) size = b.length - i;                        // runs to the end of the file
      if (type === 'mdat') return size > head;
      if (size < head) return false;
      i += size;
    }
    return false;
  }

  function hasFrame(bytes, mime) {
    return /mp4/.test(mime) ? mp4HasSamples(bytes) : webmVideoBlocks(bytes) > 0;
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
      blob.slice(0, SCAN).arrayBuffer().then(function (ab) {
        var head = new Uint8Array(ab);
        if (!looksLike(head, mime)) { o.fail('unreadable'); return; }
        if (blob.size <= SCAN && !hasFrame(head, mime)) { o.fail('empty'); return; }
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
