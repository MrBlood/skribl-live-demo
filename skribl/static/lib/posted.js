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
 * NO PAYLOAD IS STORED. Only id, url, title, kind, page count and a timestamp,
 * so the whole list stays a few kilobytes however many Skribls someone makes.
 * Payloads run to hundreds of kilobytes each and localStorage is a ~5MB budget
 * shared with the crash-recovery autosave, which matters far more.
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

  function write(list) {
    try {
      global.localStorage.setItem(KEY, JSON.stringify(list.slice(0, LIMIT)));
      return true;
    } catch (e) {
      // Quota, or private mode. The tray degrades to empty; posting still works.
      return false;
    }
  }

  function add(entry) {
    if (!entry || !entry.id) return read();
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
      at: Date.now()
    });
    write(list);
    return list;
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
    remove: remove,
    clear: clear,
    sweepOrphans: sweepOrphans,
    evictOldest: evictOldest,
    reclaim: reclaim,
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
