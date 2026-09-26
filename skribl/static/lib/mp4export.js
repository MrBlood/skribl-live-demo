/* MP4 export through WebCodecs + the vendored mp4-muxer: one encoder pipeline
 * for both editors (SK312-003, v315). exportViaWebCodecsMp4 was ported from
 * Pad to Flip by copy (0.69 alike by harness/tools/editordup.py), and neither
 * copy had ever been run by a suite until verify_mp4 started clicking each
 * editor's real Video button.
 *
 * What is shared is everything that does not depend on WHAT is drawn: the
 * capability checks, loading the muxer, the video encoder loop, the music loop
 * tiled across the clip into the audio encoder, and the finished container.
 * Each editor keeps its own frames (Pad replays a stroke timeline, Flip steps
 * through pages), its own progress UI and its own download.
 *
 * Everything is capability-gated: prepare() returns null when WebCodecs, an
 * H.264 profile or the muxer is missing, and the caller falls back to the
 * MediaRecorder (WebM) path -- never worse than having no MP4 at all.
 *
 * Editors only; the player does not export.
 */
(function (global) {
  'use strict';

  var AVC = ['avc1.640028', 'avc1.4d0028', 'avc1.42001f', 'avc1.42e01e'];
  var FPS = 30;

  async function pickAvcCodec(w, h) {
    if (typeof VideoEncoder === 'undefined' || !VideoEncoder.isConfigSupported) return null;
    for (var i = 0; i < AVC.length; i++) {
      try {
        var r = await VideoEncoder.isConfigSupported({ codec: AVC[i], width: w, height: h, bitrate: 6000000, framerate: FPS });
        if (r && r.supported) return AVC[i];
      } catch (e) {}
    }
    return null;
  }

  async function aacSupported(sr, ch) {
    if (typeof AudioEncoder === 'undefined' || !AudioEncoder.isConfigSupported) return false;
    try {
      var r = await AudioEncoder.isConfigSupported({ codec: 'mp4a.40.2', sampleRate: sr, numberOfChannels: ch, bitrate: 128000 });
      return !!(r && r.supported);
    } catch (e) { return false; }
  }

  /* {MM, avcCodec, w, h} ready to encode, or null (no side effects). w and h
   * are rounded down to even: H.264 encoders want even dimensions. */
  async function prepare(width, height) {
    try { await global.skriblLoadVendor('mp4muxer'); } catch (e) { return null; }
    var MM = global.Mp4Muxer;
    if (!(MM && MM.Muxer && MM.ArrayBufferTarget)) return null;
    if (typeof VideoEncoder === 'undefined' || typeof VideoFrame === 'undefined') return null;
    var w = width & ~1, h = height & ~1;
    if (w < 2 || h < 2) return null;
    var avcCodec = await pickAvcCodec(w, h);
    if (!avcCodec) return null;
    return { MM: MM, avcCodec: avcCodec, w: w, h: h };
  }

  function yieldNow() { return new Promise(function (r) { setTimeout(r, 0); }); }

  /* o: { ready (from prepare), canvas (w x h, the frame source),
   *      durationSec, audio (AudioBuffer of ONE loop, or null),
   *      drawFrame(f, isLast)  paints frame f into canvas (called in order),
   *      aborted()             true to stop, progress(frac, label) }
   * Resolves to the MP4's ArrayBuffer, or null if aborted. Throws on an
   * encoder error; the caller decides the fallback. */
  async function encode(o) {
    var rd = o.ready, MM = rd.MM, w = rd.w, h = rd.h, audio = o.audio;
    var muxer = new MM.Muxer({
      target: new MM.ArrayBufferTarget(),
      video: { codec: 'avc', width: w, height: h },
      audio: audio ? { codec: 'aac', numberOfChannels: audio.numberOfChannels, sampleRate: audio.sampleRate } : undefined,
      fastStart: 'in-memory'      // moov at the front: the file plays while it downloads
    });
    var encErr = null;
    var vEnc = new VideoEncoder({ output: function (c, m) { muxer.addVideoChunk(c, m); }, error: function (e) { encErr = e; } });
    vEnc.configure({ codec: rd.avcCodec, width: w, height: h, bitrate: 6000000, framerate: FPS });
    var aEnc = null;
    if (audio) {
      aEnc = new AudioEncoder({ output: function (c, m) { muxer.addAudioChunk(c, m); }, error: function (e) { encErr = e; } });
      aEnc.configure({ codec: 'mp4a.40.2', numberOfChannels: audio.numberOfChannels, sampleRate: audio.sampleRate, bitrate: 128000 });
    }
    function close() {
      try { vEnc.close(); } catch (e) {}
      try { if (aEnc) aEnc.close(); } catch (e) {}
    }
    var videoShare = audio ? 0.8 : 1;
    try {
      var frameDurUs = 1000000 / FPS;
      var totalFrames = Math.max(1, Math.ceil(o.durationSec * FPS));
      o.progress(0, 'Encoding video…');
      for (var f = 0; f < totalFrames; f++) {
        if (o.aborted()) { close(); return null; }
        await o.drawFrame(f, f === totalFrames - 1);
        var vf = new VideoFrame(o.canvas, { timestamp: Math.round(f * frameDurUs), duration: Math.round(frameDurUs) });
        vEnc.encode(vf, { keyFrame: (f % (FPS * 2)) === 0 });
        vf.close();
        if (encErr) throw encErr;
        if (vEnc.encodeQueueSize > 8) await yieldNow();
        if ((f & 7) === 0) { o.progress((f / totalFrames) * videoShare); await yieldNow(); }
      }
      await vEnc.flush();

      // The music: ONE loop, tiled across the whole clip, in 1024-frame blocks.
      if (audio) {
        o.progress(0.82, 'Encoding audio…');
        var sr = audio.sampleRate, ch = audio.numberOfChannels, loopLen = audio.length;
        var chans = [];
        for (var c = 0; c < ch; c++) chans.push(audio.getChannelData(c));
        var totalSamples = Math.ceil(o.durationSec * sr), blk = 1024, pos = 0;
        while (pos < totalSamples) {
          if (o.aborted()) { close(); return null; }
          var n = Math.min(blk, totalSamples - pos);
          var data = new Float32Array(n * ch);          // f32-planar: [ch0…, ch1…]
          for (var k = 0; k < ch; k++) {
            var src = chans[k], off = k * n;
            for (var j = 0; j < n; j++) data[off + j] = src[(pos + j) % loopLen];
          }
          var ad = new AudioData({ format: 'f32-planar', sampleRate: sr, numberOfFrames: n, numberOfChannels: ch,
                                   timestamp: Math.round((pos / sr) * 1000000), data: data });
          aEnc.encode(ad); ad.close();
          if (encErr) throw encErr;
          pos += n;
          if ((pos % (blk * 32)) === 0) { o.progress(0.82 + (pos / totalSamples) * 0.16); await yieldNow(); }
        }
        await aEnc.flush();
      }
      if (encErr) throw encErr;
      muxer.finalize();
      o.progress(1, 'Done!');
      return muxer.target.buffer;
    } finally {
      close();
    }
  }

  global.SkriblMp4 = { pickAvcCodec: pickAvcCodec, aacSupported: aacSupported, prepare: prepare, encode: encode };
})(window);
