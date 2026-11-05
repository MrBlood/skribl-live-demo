/* A SONG'S TEXT, MADE OFF THE PAGE (the speed fixes, Nov 5; the owner: "do the
 * song speed for both editors").
 *
 * Both editors keep a song as its bytes and, beside them, as text (a data
 * URL): the post, a backup file and a saved draft carry the text. Making that
 * text from a two-minute song (21.9 MB of WAV, 29 MB of text) held the page
 * 0.3 to 0.4 s in one stretch at a slower phone's pace (this box's Chromium,
 * the CPU 4x slower), when the song was added and again when a reload brought
 * it back. In a worker (FileReaderSync) the page only takes the finished text
 * back, a copy of about 0.08 s.
 *
 * ONE VERB: SkriblSongText.of(blob) -> a promise of the blob's data URL,
 * exactly what FileReader.readAsDataURL gives, so a caller swaps one for the
 * other and nothing downstream changes. This file is its worker's script too,
 * as lib/musicears.js is. Where a worker cannot start or answer (a host's
 * policy, an old browser), the text is made on the page, as it was.
 *
 * The editors load this; the player never makes a song's text, so it must
 * not (verify_player_isolation keeps its budget).
 */
(function (global) {
  'use strict';

  // In the worker: the blob's text, and back.
  if (typeof document === 'undefined' && typeof global.importScripts === 'function') {
    global.onmessage = function (e) {
      var d = e.data || {};
      try { global.postMessage({ id: d.id, text: new global.FileReaderSync().readAsDataURL(d.blob) }); }
      catch (err) { global.postMessage({ id: d.id, error: String((err && err.message) || err) }); }
    };
    return;
  }

  var SELF = typeof document !== 'undefined' && document.currentScript ? document.currentScript.src : null;
  var worker = null, broken = false, seq = 0, waiting = {};
  var ANSWER_MS = 20000;   // a two-minute song is under a second there, at a slower phone's pace

  // The text made here, as FileReader always made it.
  function onPage(blob) {
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () { resolve(String(r.result)); };
      r.onerror = function () { reject(r.error || new Error('could not read the song')); };
      r.readAsDataURL(blob);
    });
  }
  // A worker that will not do: everything asked of it is made here instead,
  // and nothing more is asked of one.
  function giveUp() {
    broken = true;
    if (worker) { try { worker.terminate(); } catch (e) {} worker = null; }
    var asked = waiting; waiting = {};
    Object.keys(asked).forEach(function (id) { clearTimeout(asked[id].timer); onPage(asked[id].blob).then(asked[id].ok, asked[id].fail); });
  }
  function start() {
    if (worker || broken) return worker;
    if (!SELF || typeof global.Worker !== 'function') { broken = true; return null; }
    try { worker = new global.Worker(SELF); } catch (e) { broken = true; worker = null; return null; }
    worker.onmessage = function (e) {
      var d = e.data || {}, w = waiting[d.id];
      if (!w) return;
      delete waiting[d.id]; clearTimeout(w.timer);
      if (typeof d.text === 'string') w.ok(d.text);
      else onPage(w.blob).then(w.ok, w.fail);   // the worker could not: here, as before
    };
    worker.onerror = function (e) { if (e && e.preventDefault) e.preventDefault(); giveUp(); };
    return worker;
  }
  function of(blob) {
    var w = start();
    if (!w) return onPage(blob);
    return new Promise(function (resolve, reject) {
      var id = ++seq;
      // NOTHING HERE WAITS FOREVER: a worker that has not answered in time
      // has the text made here (the editors wait on it before a post).
      var timer = setTimeout(function () {
        if (!waiting[id]) return;
        delete waiting[id];
        onPage(blob).then(resolve, reject);
      }, ANSWER_MS);
      waiting[id] = { blob: blob, ok: resolve, fail: reject, timer: timer };
      try { w.postMessage({ id: id, blob: blob }); }
      catch (e) { clearTimeout(timer); delete waiting[id]; onPage(blob).then(resolve, reject); }
    });
  }

  global.SkriblSongText = { of: of, onPage: onPage };
})(typeof self !== 'undefined' ? self : this);
