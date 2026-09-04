/* What a POST stores, which is deliberately not what an EXPORT downloads.
 *
 * A posted loop is at most MAX_LOOP_SECONDS long (lib/looptrim.js) and plays
 * under a drawing. Stored as source-rate STEREO it is the single largest term
 * in a music-bearing payload_json row — an order of magnitude over the strokes
 * — and those rows sit inline in Postgres, so the audio term is the practical
 * ceiling on how many posts the database holds. Downmixing to mono halves it,
 * exactly, for a background loop nobody is listening to in stereo.
 *
 * ================= 22.05 kHz WAS TRIED, MEASURED, AND REVERTED =============
 *
 * The obvious next step is to halve it again by resampling to 22.05 kHz. It was
 * implemented, including a wrapping box filter so the loop's last sample
 * averages across the join. DO NOT DO IT AGAIN. It puts an audible click on
 * every loop repeat, and the click is not in this file:
 *
 *   mono @ source rate   verify_audio.py seam 1.32x the mid-loop delta   PASS
 *   mono @ 22.05 kHz     verify_audio.py seam 12.36x                     FAIL
 *
 * `decodeAudioData` resamples a clip whose rate differs from the AudioContext's
 * (44.1 kHz on the player) and its edge handling pads with zeros, so the
 * decoded buffer's end no longer joins its start — which is the whole game for
 * something played with `loop = true`. Proof that the fault is downstream of
 * this file rather than in the filter: adding the wrap left the seam figure
 * byte-identical at 0.13114, and dropping the resample restored the exact
 * pre-change 1.32x. A compressed codec would hit the same wall from the other
 * side, plus Opus-in-WebM does not decode on iOS Safari before 17.4, where it
 * fails silently as a Skribl with no music.
 *
 * So: mono, at whatever rate the source already is. A certain 2x, no playback
 * risk anywhere, and verify_audio.py's seam assertion is what stops the 22.05
 * kHz idea coming back without anyone noticing.
 *
 * EXPORTS DO NOT USE THIS. buildTrimmedLoopWav (lib/audioloop.js) stays full
 * width for the export paths in editor_export.js — that file is a download the
 * user keeps, where bytes are not the constraint and a downmix would be audible
 * damage. verify_loopcap.py asserts the two bakes DIFFER, so they cannot
 * quietly converge back into one.
 *
 * WHY THIS IS NOT IN lib/audioloop.js. The player loads audioloop.js — it
 * builds the playback loop — and the player never posts. Putting this there
 * cost the player code it can never execute and blew
 * verify_player_isolation.py's byte ratchet on the first run. Same reasoning as
 * the note in lib/eventpoint.js about the pinch helpers: this file is loaded by
 * skribl_editor.html and skribl_flip.html and by nothing else.
 *
 * NO PER-SURFACE SHIM, deliberately. The obvious shape is a one-line
 * buildPostedLoopWav() in app.js and the same line in flip.js, and that is a
 * 61st name defined in both editors — which verify_surfaces.py ratchets against
 * precisely because every such pair is a fix that has to be made twice. Both
 * post paths call this module directly instead.
 */
(function (global) {
  'use strict';

  function downmixToMono(channels, frames) {
    var n = channels.length;
    if (n === 1) return channels[0];
    var out = new Float32Array(frames);
    for (var i = 0; i < frames; i++) {
      var sum = 0;
      for (var c = 0; c < n; c++) sum += channels[c][i] || 0;
      out[i] = sum / n;
    }
    return out;
  }

  // Same window and the same crossfade fold as buildTrimmedLoopWav — it shares
  // audioloop's loopChannels() so the two bakes can never disagree about WHICH
  // audio the loop is — then mono, at the source's own sample rate.
  function buildPostedLoopWav(state) {
    var AL = global.SkriblAudioLoop;
    var lc = AL.loopChannels(state);
    if (!lc) return null;
    var mono = downmixToMono(lc.channels, lc.frames);
    return { dataUrl: AL.encodeWavFromChannels([mono], lc.sampleRate),
             duration: mono.length / lc.sampleRate };
  }

  var api = {
    downmixToMono: downmixToMono,
    buildPostedLoopWav: buildPostedLoopWav
  };
  if (typeof window !== 'undefined') window.SkriblPostedAudio = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
