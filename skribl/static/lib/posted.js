/* Your Skribls — a local record of what you have posted.
 *
 * WHY IT EXISTS. There are no accounts, so a share link is the only handle on a
 * post, and nothing told anyone to keep it. Post, close the tab, and the Skribl
 * is unreachable forever — the id exists on the server but the person who made
 * it has no way to name it. That is the first thing a tester loses and the
 * least excusable, because the client already knows every id it posted.
 *
 * WHAT IT IS NOT. Not an account, not a backup, and not the server's opinion of
 * what you own. It is a list this browser kept. The UI says so plainly: someone
 * who believes this is an account will clear their site data, lose the lot, and
 * be right to blame the app. If a post is deleted server-side the entry stays
 * until it is opened and 404s — better a dead link the person can see than a
 * silent disappearance.
 *
 * NO PAYLOAD IS STORED. Only id, url, title, kind, page count, a timestamp and
 * -- since v279 -- the revocation key. Payloads run to hundreds of kilobytes
 * each and localStorage is a ~5MB budget shared with the crash-recovery
 * autosave, which matters far more.
 *
 * WHAT CHANGED IN v280, AND WHY THE OLD POLICY STOPPED BEING VALID. Everything
 * above was written when the worst case was losing a convenience list. v279 put
 * the anonymous revocation key in these same records, and an audit named the
 * consequence: the failure policy did not change when the data changed meaning.
 * Two specific ways the key was being thrown away, both silent:
 *
 *   * `write()` has always returned whether it succeeded and `add()` has always
 *     ignored it. A quota failure or private mode meant the server had created
 *     a public post and the only credential that could withdraw it was gone,
 *     with the UI reporting success.
 *   * `write()` truncated to LIMIT on every call. Publishing the 201st Skribl
 *     silently stranded the 1st -- still live, no longer revocable -- and the
 *     202nd stranded the next. Deterministic, not an edge case.
 *
 * SO THE CAP NOW APPLIES TO HISTORY AND NEVER TO AUTHORISATION. `capped()`
 * keeps the newest LIMIT entries PLUS every entry that carries a key, however
 * old. The list can therefore exceed LIMIT, deliberately: a few hundred bytes
 * per stranded credential is not a reason to strand it. Rendering is what LIMIT
 * was for and rendering is what it still governs.
 *
 * AND A FAILED WRITE IS NOW A RESULT, NOT A SHRUG. `add()` returns
 * `{list, durable, key}`; Pad and Flip show the key for the user to copy when
 * `durable` is false. That is the only custody that survives cleared site data,
 * a new phone, or Safari evicting the origin -- none of which IndexedDB would
 * have survived either, which is why this stayed in localStorage.
 */
(function (global) {
  'use strict';

  var KEY = 'skribl_posted_v1';
  var LIMIT = 200;

  function read() {
    try {
      var raw = global.localStorage.getItem(KEY);
      if (!raw) return [];
      var list = JSON.parse(raw);
      return Array.isArray(list) ? list.filter(function (e) { return e && e.id; }) : [];
    } catch (e) {
      // A corrupt or unavailable store must not take the editor down with it.
      return [];
    }
  }

  /* The cap, applied so that it can never cost anyone a credential.
     Keeps the newest LIMIT entries and, beyond them, every entry still holding
     a revocation key. `list.slice(0, LIMIT)` -- what this replaced -- treated
     an authorisation secret and a row in a tray as the same kind of thing. */
  function capped(list) {
    var keep = [];
    for (var i = 0; i < list.length; i++) {
      if (i < LIMIT || (list[i] && list[i].tok)) keep.push(list[i]);
    }
    return keep;
  }

  function write(list) {
    var body = JSON.stringify(capped(list));
    try {
      global.localStorage.setItem(KEY, body);
      return true;
    } catch (e) {
      /* Quota, or private mode. Before v280 this returned false into a caller
         that ignored it. Now: try to buy room the free way -- orphaned payload
         blobs are the usual hog and nothing can reach them -- and retry once.
         Only if THAT fails is the write genuinely not durable, and the caller
         is told so rather than left believing the key was kept. */
      try {
        sweepOrphans();
        global.localStorage.setItem(KEY, body);
        return true;
      } catch (e2) {
        return false;
      }
    }
  }

  /* Ask, before creating server state, whether this browser can keep anything.
     Private mode and a full origin both answer no, and both are worth knowing
     BEFORE a post exists that needs a key kept for it. Cheap: one tiny write
     and a remove. */
  function canPersist() {
    var probe = KEY + '__probe';
    try {
      global.localStorage.setItem(probe, '1');
      global.localStorage.removeItem(probe);
      return true;
    } catch (e) {
      return false;
    }
  }

  function add(entry) {
    if (!entry || !entry.id) return { list: read(), durable: false, key: null };
    var list = read();
    // De-duplicate on id: re-posting the same Skribl should move it to the top,
    // not appear twice with two timestamps.
    list = list.filter(function (e) { return e.id !== entry.id; });
    list.unshift({
      id: String(entry.id),
      url: entry.url || null,
      title: (entry.title || '').slice(0, 80),
      kind: entry.kind === 'flip' ? 'flip' : 'pad',
      pages: Math.max(1, parseInt(entry.pages, 10) || 1),
      /* THE REVOCATION CAPABILITY. The server returns it once in the create
         response and stores only its SHA-256; there is no endpoint that can
         reissue it.
         This used to say "the only copy of it that will ever exist" and that
         losing this entry meant the Skribl could no longer be withdrawn. Both
         were true until v281, which added the other half of the loop: the key
         can be copied out and handed back through Your Skribls, so this entry
         is now the CONVENIENT copy rather than the only one. Losing it still
         costs the Skribl if no copy was kept, which is why the UI says so
         before you publish rather than after.
         Absent for a post made under a host that authenticated its author —
         that one is revoked by ownership. */
      tok: typeof entry.tok === 'string' && entry.tok ? entry.tok : null,
      at: Date.now()
    });
    /* THE RETURN SHAPE IS THE FINDING. `add()` used to return the list and
       drop `write()`'s answer on the floor, so a caller could not distinguish
       "kept" from "lost" and neither Pad nor Flip tried. Three fields, because
       the operation genuinely has three things to say: what to render, whether
       it survived, and -- when it did not -- the secret the user must be given
       a chance to copy, because nothing else in the system still holds it. */
    var durable = write(list);
    return { list: list, durable: durable, key: durable ? null : (entry.tok || null) };
  }

  // A local save's BYTES live under 'skribl_post_<id>', written by
  // saveLocalFallback() in editor_post.js. This index is metadata only.
  var BLOB = 'skribl_post_';

  function dropBlob(id) {
    try { global.localStorage.removeItem(BLOB + id); } catch (e) {}
  }

  function remove(id) {
    var list = read().filter(function (e) { return e.id !== id; });
    write(list);
    // ...AND THE PAYLOAD. Removing only the index entry left a multi-megabyte
    // blob behind that nothing could ever open again -- not listed, not
    // reachable at #skribl=<id>, and still holding its share of a ~5MB origin
    // quota. Deleting from the tray and watching storage stay full is exactly
    // how this was found.
    dropBlob(id);
    return list;
  }

  function clear() {
    var list = read();
    try { global.localStorage.removeItem(KEY); } catch (e) {}
    list.forEach(function (e) { dropBlob(e.id); });
    // Clearing the list is also the moment to collect anything already orphaned
    // by the old remove().
    sweepOrphans();
    return [];
  }

  // Delete every 'skribl_post_*' blob with no entry in the index. Those are
  // unreachable by definition -- the tray is the only route to one -- so this
  // frees space without losing anything the user can still get at.
  // Returns the number of BYTES reclaimed.
  function sweepOrphans() {
    var keep = {}, freed = 0;
    read().forEach(function (e) { keep[BLOB + e.id] = 1; });
    try {
      Object.keys(global.localStorage).forEach(function (k) {
        if (k.indexOf(BLOB) !== 0 || keep[k]) return;
        freed += (global.localStorage.getItem(k) || '').length;
        global.localStorage.removeItem(k);
      });
    } catch (e) {}
    return freed;
  }

  // Last resort, and destructive on purpose: drop the OLDEST local save,
  // payload and index entry together. Only called when the store is genuinely
  // full and a drawing is about to be lost for want of room -- an old saved
  // copy is worth less than the work in front of the user. Returns bytes freed,
  // or 0 when there is nothing left to give.
  function evictOldest() {
    var list = read();
    var locals = list.filter(function (e) { return String(e.id).indexOf('local_') === 0; });
    if (!locals.length) return 0;
    var victim = locals[locals.length - 1];          // the list is newest-first
    var freed = 0;
    try { freed = (global.localStorage.getItem(BLOB + victim.id) || '').length; } catch (e) {}
    dropBlob(victim.id);
    write(list.filter(function (e) { return e.id !== victim.id; }));
    return freed;
  }

  // One call for "make room": sweep first (free), evict only if that was not
  // enough (destructive). Callers pass how many bytes they need.
  function reclaim(needBytes) {
    var freed = sweepOrphans();
    while (freed < (needBytes || 0)) {
      var got = evictOldest();
      if (!got) break;
      freed += got;
    }
    return freed;
  }

  // Relative time, coarse on purpose. "3 days ago" is what someone needs to
  // find a thing again; a timestamp to the minute is noise in a list.
  function ago(ms) {
    var s = Math.max(0, (Date.now() - ms) / 1000);
    if (s < 90) return 'just now';
    var m = s / 60;
    if (m < 60) return Math.round(m) + ' min ago';
    var h = m / 60;
    if (h < 24) return Math.round(h) + (Math.round(h) === 1 ? ' hour ago' : ' hours ago');
    var d = h / 24;
    if (d < 7) return Math.round(d) + (Math.round(d) === 1 ? ' day ago' : ' days ago');
    if (d < 14) return 'last week';
    return Math.round(d / 7) + ' weeks ago';
  }

  function absolute(url) {
    if (!url) return '';
    return /^https?:/i.test(url) ? url : (global.location.origin + url);
  }

  global.SkriblPosted = {
    KEY: KEY,
    list: read,
    add: add,
    capped: capped,
    canPersist: canPersist,
    remove: remove,
    clear: clear,
    sweepOrphans: sweepOrphans,
    evictOldest: evictOldest,
    reclaim: reclaim,
    LIMIT: LIMIT,
    ago: ago,
    absolute: absolute
  };
})(window);

// ---------------------------------------------------------------------------
// skriblPackBody(body) -> { body, headers }
//
// Gzip a post body when the browser can. Shared by Pad (editor_post.js) and
// Flip (flip.js), both of which load this file before their own.
//
// Measured: a photo-plus-music post is ~2.4 MB of JSON, almost all of it base64
// media, and the server handles it in ~33 ms. The wait a user feels on Post is
// upload transfer. Gzipped that body is ~32 KB, so this is worth roughly two
// orders of magnitude more than anything on the response side.
//
// Feature-detected and never required. CompressionStream is absent on older
// Safari, and the server treats Content-Encoding as optional, so a browser
// without it and a client that predates this both post exactly as before.
async function skriblPackBody(body, headers) {
  const out = Object.assign({}, headers || {});
  const size = (body && body.length) || 0;
  if (typeof CompressionStream !== 'function' || size <= 4096) {
    return { body: body, headers: out };
  }
  try {
    const packed = await new Response(
      new Blob([body]).stream().pipeThrough(new CompressionStream('gzip'))
    ).arrayBuffer();
    if (packed.byteLength >= size) return { body: body, headers: out };
    out['Content-Encoding'] = 'gzip';
    return { body: packed, headers: out };
  } catch (err) {
    // Compression is an optimisation; never let it cost a post.
    console.warn('skriblPackBody: compression unavailable, sending plain —', err);
    return { body: body, headers: out };
  }
}
