/* Draft media persistence — the bytes localStorage cannot hold.
 *
 * localStorage caps at ~5 MB per origin, which is why Pad's autosave stored
 * media METADATA only and Flip's dropped media on QuotaExceededError. Both
 * were honest about it (the amber "Saved without media" pill) — but honest
 * data loss is still data loss, and DESIGN-DIRECTION.md names durable drafts
 * as a prerequisite. IndexedDB has an origin quota in the hundreds of MB, so a
 * photo and an audio track fit without ceremony.
 *
 * DELIBERATELY TINY. Four verbs over one object store (put, get, del, keys),
 * promises throughout, no schema beyond "value at key". Keys are namespaced by
 * surface ('pad:photo', 'pad:music', 'flip:draft', 'saved:*') so nothing can
 * collide. Values are plain objects with metadata; a top-level Blob or File in
 * one is stored as its bytes and type and comes back a Blob (BYTES, NOT BLOBS
 * below), so callers put and get Blobs as they always did.
 *
 * FAILURE IS A RESULT, NOT AN EXCEPTION PATH. Private-mode browsers, disabled
 * IndexedDB, and quota pressure all surface as a rejected promise; every
 * caller treats rejection as "not durable" and says so in the UI. No silent
 * catch — the paLoopBuffer lesson (a swallowed error made "threw" and
 * "returned null" identical to every caller for three builds) applies to
 * storage twice over.
 *
 * The editors and the Library load this; the player must not — it never
 * writes a draft, and the player budget is a ratchet. verify_player_isolation
 * guards the payload.
 */
(function () {
  'use strict';

  var DB_NAME = 'skribl-drafts', STORE = 'media', VERSION = 1;
  var dbPromise = null;
  var liveDb = null;   // the connection dbPromise currently stands for

  /* NOTHING HERE MAY WAIT FOREVER (v317). The owner's iPhone: the drafts sheet
     said "Loading…" and nothing came, drafts "seem to go away", and a photo
     the Pad had kept came back as "Media missing". All three read this store,
     and every one of its promises settled only if IndexedDB fired an event.
     WebKit does not always: a connection can die while the page is in the
     background with no close event, and an open() can sit unanswered until
     something nudges it. So: a deadline on the open and on every request, a
     connection that has died or timed out is dropped and the next call opens
     a fresh one, and a request that finds its connection closed gets exactly
     one retry on a fresh one. A deadline turns a hang into the rejection
     every caller already handles as "not durable". */
  var OPEN_MS = 4000, OP_MS = 8000;
  // A WRITE'S deadline is for a hang, not for a slow phone: a multi-MB photo
  // on iOS can take longer than a read ever should, and the callers keep their
  // own, shorter patience (the Pad's MEDIA_STORE_TIMEOUT_MS, 12 s) for what
  // the person sees. An inner 8 s cut-off reported bytes as failed that went
  // on to commit (v317 review).
  var WRITE_MS = 30000;

  function deadline(p, ms) {
    return new Promise(function (resolve, reject) {
      var t = setTimeout(function () {
        var e = new Error("This browser's storage did not answer.");
        e.skriblTimeout = true;
        reject(e);
      }, ms);
      p.then(function (v) { clearTimeout(t); resolve(v); },
             function (e) { clearTimeout(t); reject(e); });
    });
  }

  function open() {
    if (dbPromise) return dbPromise;
    var timedOut = false, kick = null;
    var raw = new Promise(function (resolve, reject) {
      if (typeof indexedDB === 'undefined') {
        reject(new Error('IndexedDB unavailable'));
        return;
      }
      var req = indexedDB.open(DB_NAME, VERSION);
      /* THE NUDGE. WebKit has shipped builds where the first open() of a
         session never answers until another IndexedDB call is made; asking
         for the database list is the harmless call that wakes it. Stops the
         moment the open settles. */
      if (typeof indexedDB.databases === 'function') {
        kick = setInterval(function () { try { indexedDB.databases(); } catch (e) {} }, 100);
      }
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(STORE)) {
          req.result.createObjectStore(STORE);
        }
      };
      req.onsuccess = function () {
        var db = req.result;
        if (timedOut) { try { db.close(); } catch (e) {} return; }
        // Another tab upgrading the schema, or the browser closing the
        // connection under us: drop the handle so the next call reopens.
        // Each handler forgets THIS connection only: a late event from an old,
        // dead one must not drop the healthy one that replaced it (v317 review).
        db.onversionchange = function () {
          try { db.close(); } catch (e) {}
          if (liveDb === db) { liveDb = null; dbPromise = null; }
        };
        db.onclose = function () { if (liveDb === db) { liveDb = null; dbPromise = null; } };
        liveDb = db;
        resolve(db);
      };
      req.onerror = function () { reject(req.error || new Error('IndexedDB open failed')); };
      req.onblocked = function () { reject(new Error('IndexedDB open blocked')); };
    });
    dbPromise = deadline(raw, OPEN_MS).then(function (db) {
      clearInterval(kick);
      return db;
    }, function (e) {
      timedOut = true;
      clearInterval(kick);
      dbPromise = null;
      throw e;
    });
    return dbPromise;
  }

  /* One request in one transaction, with the deadline, and one retry when the
     connection turns out to be dead (db.transaction throws InvalidStateError
     on a closed connection -- the background case above).

     ONLY A DEAD CONNECTION IS DROPPED (v317 review). A full disk, a value that
     will not clone, a refused write: those are answers from a connection that
     works, and dropping it for them opened a fresh one per failure and left
     every old one open. A connection that is dropped is closed. */
  function drop(db) {
    if (!db) return;
    if (liveDb === db) { liveDb = null; dbPromise = null; }
    try { db.close(); } catch (e) {}
  }
  function op(mode, body) {
    var used = null;   // the connection this attempt ran on, the one to drop
    function once() {
      return open().then(function (db) {
        used = db;
        return deadline(new Promise(function (resolve, reject) {
          var tx = db.transaction(STORE, mode);
          body(tx.objectStore(STORE), tx, resolve, reject);
        }), mode === 'readwrite' ? WRITE_MS : OP_MS);
      });
    }
    return once().catch(function (e) {
      if (e && e.name === 'InvalidStateError') { drop(used); return once(); }
      if (e && e.skriblTimeout) drop(used);
      throw e;
    });
  }

  /* BYTES, NOT BLOBS (v317). WebKit has a long record of failing to store
     Blob and File values in IndexedDB -- in the in-app browsers above all,
     and Chrome on iOS is one -- and the owner's iPhone kept restoring
     drawings with "Media missing". An ArrayBuffer is plain data every engine
     stores. A record's top-level Blobs go in as their bytes and their type and
     come back out as Blobs, so no caller changes; a record written before
     this still holds a real Blob, and still reads back as one. */
  function toBytes(blob) {
    if (typeof blob.arrayBuffer === 'function') return blob.arrayBuffer();
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () { resolve(r.result); };
      r.onerror = function () { reject(r.error || new Error('could not read the file')); };
      r.readAsArrayBuffer(blob);
    });
  }
  function pack(value) {
    if (!value || typeof value !== 'object' || typeof Blob === 'undefined') return Promise.resolve(value);
    var keys = Object.keys(value).filter(function (k) { return value[k] instanceof Blob; });
    if (!keys.length) return Promise.resolve(value);
    var out = Object.assign({}, value);
    return Promise.all(keys.map(function (k) {
      return toBytes(value[k]).then(function (buf) {
        out[k] = { __skriblBytes: buf, type: value[k].type || '' };
      });
    })).then(function () { return out; });
  }
  function unpack(value) {
    if (!value || typeof value !== 'object') return value;
    Object.keys(value).forEach(function (k) {
      var v = value[k];
      if (v && typeof v === 'object' && v.__skriblBytes) value[k] = new Blob([v.__skriblBytes], { type: v.type || '' });
    });
    return value;
  }

  /* ONE KEY, ONE QUEUE (third review). put() reads a Blob's bytes BEFORE it
     opens its transaction, so a del() issued after it opened first, and the
     put then wrote back what had just been removed: a photo taken off the
     page stayed in the store. Writes to the same key now run in the order
     they were asked for. Each waits only on the one before it, and every op
     has a deadline, so a queue cannot stall for longer than one write. */
  var tail = {};
  function inOrder(key, run) {
    var next = (tail[key] || Promise.resolve()).then(run, run);
    var settled = next.then(function () {}, function () {});
    tail[key] = settled;
    settled.then(function () { if (tail[key] === settled) delete tail[key]; });
    return next;
  }

  function put(key, value) {
    return inOrder(key, function () {
      return pack(value).then(function (packed) { return putRaw(key, packed); });
    });
  }
  function putRaw(key, value) {
    return op('readwrite', function (store, tx, resolve, reject) {
      store.put(value, key);
      // Resolve on transaction COMPLETE, not request success — a request can
      // succeed and the transaction still abort on quota at commit time,
      // which is exactly the moment "durable" must not have been reported.
      tx.oncomplete = function () { resolve(true); };
      tx.onerror = function () { reject(tx.error || new Error('put failed')); };
      tx.onabort = function () { reject(tx.error || new Error('put aborted')); };
    });
  }

  function get(key) {
    return op('readonly', function (store, tx, resolve, reject) {
      var req = store.get(key);
      req.onsuccess = function () { resolve(req.result); };  // undefined = absent
      req.onerror = function () { reject(req.error || new Error('get failed')); };
    }).then(unpack);
  }

  function del(key) {
    return inOrder(key, function () {
      return op('readwrite', function (store, tx, resolve, reject) {
        store.delete(key);
        tx.oncomplete = function () { resolve(true); };
        tx.onerror = function () { reject(tx.error || new Error('delete failed')); };
        tx.onabort = function () { reject(tx.error || new Error('delete aborted')); };
      });
    });
  }

  /* Every key in the store. For the saved-drafts list to find a draft its
     index lost (lib/savedrafts.js, v317). getAllKeys where it exists, a key
     cursor where it does not. */
  function keys() {
    return op('readonly', function (store, tx, resolve, reject) {
      if (typeof store.getAllKeys === 'function') {
        var r = store.getAllKeys();
        r.onsuccess = function () { resolve(r.result || []); };
        r.onerror = function () { reject(r.error || new Error('keys failed')); };
        return;
      }
      var out = [], c = (store.openKeyCursor || store.openCursor).call(store);
      c.onsuccess = function () {
        var cur = c.result;
        if (cur) { out.push(cur.key); cur.continue(); } else resolve(out);
      };
      c.onerror = function () { reject(c.error || new Error('keys failed')); };
    });
  }

  var api = { put: put, get: get, del: del, keys: keys };
  if (typeof window !== 'undefined') window.SkriblDraftStore = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
