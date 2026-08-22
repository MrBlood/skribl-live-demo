/* media_validation.js — one owner for media format policy and byte verification.
 *
 * Previously duplicated verbatim in app.js and flip.js with a "change both"
 * comment. This review history already contains several policy-drift bugs
 * (client vs server MIME lists, extension fallbacks missing formats the picker
 * advertised), so two copies of a security- and UX-sensitive check was a bug
 * waiting to happen. Loaded by the Pad, the Player and Flip before their main
 * script.
 *
 * MUST stay in step with ALLOWED_AUDIO_SUBTYPES / ALLOWED_IMAGE_SUBTYPES in
 * app.py. verify_review.py diffs the two and fails if they drift.
 */
(function (global) {
  'use strict';

  var AUDIO_MIMES = new Set([
    'audio/wav', 'audio/x-wav', 'audio/wave', 'audio/vnd.wave', 'audio/mpeg',
    'audio/mp3', 'audio/mp4', 'audio/x-m4a', 'audio/m4a', 'audio/aac', 'audio/ogg',
    'audio/opus', 'audio/webm', 'audio/flac', 'audio/x-flac'
  ]);
  var IMAGE_MIMES = new Set([
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'
  ]);

  // Extension fallback for the very common case of an EMPTY file.type:
  // drag-and-drop, unusual OS associations, privacy-hardened browsers and some
  // platform file providers all produce it.
  var AUDIO_EXTENSIONS = /\.(mp3|m4a|mp4|wav|ogg|opus|aac|flac|webm)$/i;
  var IMAGE_EXTENSIONS = /\.(jpe?g|png|gif|webp)$/i;

  // How long to wait for the browser to make up its mind about a file.
  var DECODE_TIMEOUT_MS = 10000;

  var MSG = {
    image: 'That image could not be opened — it may be damaged, or a format this browser cannot read.',
    audio: 'That audio could not be played — it may be damaged, or a format this browser cannot read.',
    imageSlow: 'That image took too long to check. Please try another file.',
    audioSlow: 'That audio took too long to check. Please try another file.',
    notAudio: 'That file type is not supported for audio.',
    pickAudio: 'Please choose an audio file (mp3, m4a, wav, flac, ogg, webm).'
  };

  // The extension is a FALLBACK, not an alternative: song.mp3 declaring image/png
  // must not be accepted as audio just because the name matches.
  function hasUsableMime(file) {
    return !!file.type && file.type.toLowerCase() !== 'application/octet-stream';
  }

  function validateAudioFile(file) {
    if (!file) return 'No file selected.';
    if (hasUsableMime(file)) {
      return AUDIO_MIMES.has(file.type.toLowerCase()) ? null : MSG.notAudio;
    }
    return AUDIO_EXTENSIONS.test(file.name || '') ? null : MSG.pickAudio;
  }

  function isImageFile(file) {
    if (!file) return false;
    if (hasUsableMime(file)) return IMAGE_MIMES.has(file.type.toLowerCase());
    return IMAGE_EXTENSIONS.test(file.name || '');
  }

  /* Byte verification.
   *
   * FAIL CLOSED on timeout, deliberately (review round 9, #2). The earlier
   * version resolved success after 6s so a stalled decode was *accepted*, which
   * made "bytes are verified before acceptance" untrue on exactly the pathological
   * input the check exists for. A file the browser cannot resolve within
   * DECODE_TIMEOUT_MS is now refused with a message saying so.
   *
   * These establish that the browser can OPEN the file. They do not establish
   * safe dimensions, decompression cost, semantic content, or server-side trust.
   */

  // createImageBitmap asks the browser to decode the image without adding it to
  // the document or running our normalization/re-encode path. It is cheaper than
  // drawing or re-encoding — not merely a header sniff.
  function decodeCheckImage(file) {
    return new Promise(function (resolve) {
      var done = false;
      var timer = null;
      // Round 10, #4: the timeout path used to resolve without releasing the
      // fallback's object URL — and the timeout fires precisely when the <img>
      // emits neither event, so the URL leaked exactly when it mattered. Every
      // completion path now runs the same cleanup hook.
      var cleanup = null;
      function finish(msg) {
        if (done) return;
        done = true;
        if (timer) clearTimeout(timer);
        if (cleanup) { try { cleanup(); } catch (_) {} cleanup = null; }
        resolve(msg);
      }
      timer = setTimeout(function () { finish(MSG.imageSlow); }, DECODE_TIMEOUT_MS);

      if (typeof createImageBitmap === 'function') {
        createImageBitmap(file).then(function (bm) {
          // If we already timed out, the caller has moved on — release the
          // bitmap rather than leaking it. createImageBitmap has no universal
          // abort, so the work cannot be cancelled, only discarded.
          if (done) { if (bm && bm.close) bm.close(); return; }
          if (bm && bm.close) bm.close();
          finish(null);
        }).catch(function () { finish(MSG.image); });
        return;
      }
      var url = URL.createObjectURL(file);
      var img = new Image();
      var revoked = false;
      cleanup = function () {
        img.onload = null;
        img.onerror = null;
        try { img.removeAttribute('src'); } catch (_) {}
        if (!revoked) { revoked = true; URL.revokeObjectURL(url); }
      };
      img.onload = function () { finish(img.naturalWidth > 0 ? null : MSG.image); };
      img.onerror = function () { finish(MSG.image); };
      img.src = url;
    });
  }

  // <audio> loadedmetadata rather than decodeAudioData: the question is "can this
  // browser open it at all", not "give me the samples".
  function decodeCheckAudio(file) {
    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file);
      var a = document.createElement('audio');
      a.preload = 'metadata';
      var done = false;
      var timer = null;
      function finish(msg) {
        if (done) return;
        done = true;
        if (timer) clearTimeout(timer);      // don't leave a timer per selection
        a.onloadedmetadata = null;
        a.onerror = null;
        try { a.removeAttribute('src'); a.load(); } catch (_) {}
        URL.revokeObjectURL(url);
        resolve(msg);
      }
      a.onloadedmetadata = function () { finish(null); };
      a.onerror = function () { finish(MSG.audio); };
      timer = setTimeout(function () { finish(MSG.audioSlow); }, DECODE_TIMEOUT_MS);
      a.src = url;
    });
  }

  global.SkriblMedia = {
    AUDIO_MIMES: AUDIO_MIMES,
    IMAGE_MIMES: IMAGE_MIMES,
    AUDIO_EXTENSIONS: AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS: IMAGE_EXTENSIONS,
    DECODE_TIMEOUT_MS: DECODE_TIMEOUT_MS,
    MSG: MSG,
    hasUsableMime: hasUsableMime,
    validateAudioFile: validateAudioFile,
    isImageFile: isImageFile,
    decodeCheckImage: decodeCheckImage,
    decodeCheckAudio: decodeCheckAudio
  };

  // Back-compat aliases so existing call sites keep working unchanged.
  global.SKRIBL_AUDIO_MIMES = AUDIO_MIMES;
  global.SKRIBL_IMAGE_MIMES = IMAGE_MIMES;
  global.SKRIBL_AUDIO_EXTENSIONS = AUDIO_EXTENSIONS;
  global.SKRIBL_IMAGE_EXTENSIONS = IMAGE_EXTENSIONS;
  global.skriblHasUsableMime = hasUsableMime;
  global.skriblDecodeCheckImage = decodeCheckImage;
  global.skriblDecodeCheckAudio = decodeCheckAudio;
})(window);
