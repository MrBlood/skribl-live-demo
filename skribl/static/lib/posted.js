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

  function remove(id) {
    var list = read().filter(function (e) { return e.id !== id; });
    write(list);
    return list;
  }

  function clear() {
    try { global.localStorage.removeItem(KEY); } catch (e) {}
    return [];
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
    ago: ago,
    absolute: absolute
  };
})(window);
