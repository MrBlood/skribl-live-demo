/* Skribl's service worker: the editors open with no signal, and never open old.
 *
 * Rendered by the /sw.js route so the page URLs below are url_for's, wherever
 * the blueprint is mounted. Registered by lib/offline.js.
 *
 * WHAT IT ANSWERS, AND NOTHING ELSE. Two kinds of request:
 *
 *   * A NAVIGATION TO ONE OF THE PAGES BELOW (Pad, Flip, the library):
 *     NETWORK FIRST, ALWAYS. The page is fetched every time there is any
 *     network, and only a fetch that FAILS is answered from the copy kept the
 *     last time it worked. There is no timeout and no "cache first, update in
 *     the background": a phone with a signal is never shown yesterday's page,
 *     which is the one way an offline cache strands someone on an old build
 *     (WORKING-AGREEMENTS: "it doesn't show on my phone" is a stale page until
 *     proven otherwise -- this must not become a second source of those).
 *
 *   * A STATIC FILE CARRYING ITS CONTENT HASH (?v=..., asset_url): cache
 *     first. The hash is the content, so a cached copy cannot be out of date;
 *     a new build has new URLs. When a new copy of a file is stored, older
 *     hashes of the same file are dropped once no kept page names them, so
 *     the cache holds what the kept pages need and nothing older.
 *
 * Everything else -- the API, posts, media, the shared player, any page of a
 * host that mounted Skribl at its root -- is not answered here at all, so it
 * reaches the network exactly as it would with no worker.
 *
 * Opened offline, a page that was never opened online gets a short page saying
 * so rather than the browser's error. Drafts live in the browser already
 * (localStorage and IndexedDB), so a drawing started offline is kept; posting
 * waits for a signal, and says so through the editors' own error handling.
 */
'use strict';

var PAGES = {{ pages | tojson }};
var STATIC = {{ static_prefix | tojson }};
var PAGE_CACHE = 'skribl-pages-v1';
var FILE_CACHE = 'skribl-files-v1';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) {
      return k.indexOf('skribl-') === 0 && k !== PAGE_CACHE && k !== FILE_CACHE;
    }).map(function (k) { return caches.delete(k); }));
  }));
});

function isPage(url) { return PAGES.indexOf(url.pathname) >= 0; }
function isHashedFile(url) {
  return url.pathname.indexOf(STATIC) === 0 && url.searchParams.has('v');
}

var OFFLINE_PAGE = '<!doctype html><html lang="en"><head><meta charset="utf-8">'
  + '<meta name="viewport" content="width=device-width, initial-scale=1">'
  + '<title>Skribl · offline</title><style>'
  + 'body{margin:0;min-height:100vh;display:grid;place-items:center;'
  + 'background:#0d0f14;color:#e8eaf0;font:16px/1.5 system-ui,sans-serif;text-align:center;padding:0 24px}'
  + 'h1{font-size:20px;margin:0 0 6px}p{margin:0;color:#9aa2b1}</style></head><body><div>'
  + '<h1>You’re offline</h1><p>This page opens without a signal once it has been opened with one.'
  + ' Reconnect and try again.</p></div></body></html>';

function page(req) {
  return fetch(req).then(function (res) {
    if (res && res.ok) {
      var copy = res.clone();
      caches.open(PAGE_CACHE).then(function (c) { return c.put(req.url, copy); });
    }
    return res;
  }, function () {
    return caches.open(PAGE_CACHE).then(function (c) { return c.match(req.url); })
      .then(function (hit) {
        return hit || new Response(OFFLINE_PAGE, {
          status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      });
  });
}

/* EVERY FILE A KEPT PAGE STILL NAMES (v321 preflight, PF-007). An older copy
 * of a file used to be dropped the moment a newer one was stored -- and the
 * newer one arrives when ANY page is opened on a new build. Open Pad and Flip,
 * deploy, open only the Pad: Flip's kept page still named the old styles.css
 * and lib/theme.js, the worker had dropped them, and offline Flip opened as
 * bare HTML once the browser's own cache no longer held them. So an older
 * copy goes only when no kept page names it any more. Read from the kept
 * pages themselves, once per burst of stores rather than once per file. */
var wantedOnce = null;
function wanted() {
  if (wantedOnce) return wantedOnce;
  var named = new RegExp(STATIC.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    + '[^"\'\\s)<>]+\\?v=[0-9a-f]+', 'g');
  wantedOnce = caches.open(PAGE_CACHE).then(function (pc) {
    return pc.keys().then(function (reqs) {
      return Promise.all(reqs.map(function (r) {
        return pc.match(r).then(function (res) { return res ? res.text() : ''; });
      }));
    });
  }).then(function (texts) {
    var keep = {};
    texts.forEach(function (t) {
      (t.match(named) || []).forEach(function (u) {
        keep[new URL(u, self.location.origin).href] = true;
      });
    });
    return keep;
  }, function () { return {}; });
  setTimeout(function () { wantedOnce = null; }, 2000);
  return wantedOnce;
}

function file(req) {
  return caches.open(FILE_CACHE).then(function (c) {
    return c.match(req.url).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.ok) {
          var path = new URL(req.url).pathname;
          var copy = res.clone();
          Promise.all([c.keys(), wanted()]).then(function (got) {
            var keys = got[0], keep = got[1];
            keys.forEach(function (k) {
              if (new URL(k.url).pathname === path && k.url !== req.url && !keep[k.url]) c.delete(k);
            });
            return c.put(req.url, copy);
          });
        }
        return res;
      });
    });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (req.mode === 'navigate' && isPage(url)) { e.respondWith(page(req)); return; }
  if (isHashedFile(url)) { e.respondWith(file(req)); return; }
});
