/* Draft media persistence — the bytes localStorage cannot hold.
 *
 * localStorage caps at ~5 MB per origin, which is why Pad's autosave stored
 * media METADATA only and Flip's dropped media on QuotaExceededError. Both
 * were honest about it (the amber "Saved without media" pill) — but honest
 * data loss is still data loss, and DESIGN-DIRECTION.md names durable drafts
 * as a prerequisite. IndexedDB stores Blobs natively with an origin quota in
 * the hundreds of MB, so a photo and an audio track fit without ceremony.
 *
 * DELIBERATELY TINY. Three verbs over one object store, promises throughout,
 * no schema beyond "value at key". Keys are namespaced by surface ('pad:photo',
 * 'pad:music', 'flip:draft') so the two editors cannot collide. Values are
 * plain objects carrying a Blob/File plus metadata — structured clone handles
 * both.
 *
 * FAILURE IS A RESULT, NOT AN EXCEPTION PATH. Private-mode browsers, disabled
 * IndexedDB, and quota pressure all surface as a rejected promise; every
 * caller treats rejection as "not durable" and says so in the UI. No silent
 * catch — the paLoopBuffer lesson (a swallowed error made "threw" and
 * "returned null" identical to every caller for three builds) applies to
 * storage twice over.
 *
 * The editors load this; the player must not — it never writes a draft, and
 * the player budget is a ratchet. verify_player_isolation guards the payload.
 */
(function () {
  'use strict';

  var DB_NAME = 'skribl-drafts', STORE = 'media', VERSION = 1;
  var dbPromise = null;

  function open() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise(function (resolve, reject) {
      if (typeof indexedDB === 'undefined') {
        reject(new Error('IndexedDB unavailable'));
        return;
      }
      var req = indexedDB.open(DB_NAME, VERSION);
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(STORE)) {
          req.result.createObjectStore(STORE);
        }
      };
      req.onsuccess = function () {
        // If another tab upgrades the schema later, drop our handle so the
        // next call reopens rather than erroring forever on a closed DB.
        req.result.onversionchange = function () {
          try { req.result.close(); } catch (e) {}
          dbPromise = null;
        };
        resolve(req.result);
      };
      req.onerror = function () { dbPromise = null; reject(req.error || new Error('IndexedDB open failed')); };
      req.onblocked = function () { dbPromise = null; reject(new Error('IndexedDB open blocked')); };
    });
    return dbPromise;
  }

  function put(key, value) {
    return open().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(value, key);
        // Resolve on transaction COMPLETE, not request success — a request can
        // succeed and the transaction still abort on quota at commit time,
        // which is exactly the moment "durable" must not have been reported.
        tx.oncomplete = function () { resolve(true); };
        tx.onerror = function () { reject(tx.error || new Error('put failed')); };
        tx.onabort = function () { reject(tx.error || new Error('put aborted')); };
      });
    });
  }

  function get(key) {
    return open().then(function (db) {
      return new Promise(function (resolve, reject) {
        var req = db.transaction(STORE, 'readonly').objectStore(STORE).get(key);
        req.onsuccess = function () { resolve(req.result); };  // undefined = absent
        req.onerror = function () { reject(req.error || new Error('get failed')); };
      });
    });
  }

  function del(key) {
    return open().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(key);
        tx.oncomplete = function () { resolve(true); };
        tx.onerror = function () { reject(tx.error || new Error('delete failed')); };
        tx.onabort = function () { reject(tx.error || new Error('delete aborted')); };
      });
    });
  }

  var api = { put: put, get: get, del: del };
  if (typeof window !== 'undefined') window.SkriblDraftStore = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
