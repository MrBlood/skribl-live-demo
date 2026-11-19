/* BLOOBY'S SERVICE WORKER, for nudges alone (push notifications; the
 * owner's "All yes" to Blooby's Nudges, Nov 18; social/push.py). Served at
 * the site's own folder (/sw.js there), so it may speak for the site's pages.
 * It keeps nothing and fetches nothing: no page or file passes through it, so
 * the site loads exactly as it would without it.
 *
 * A NUDGE ARRIVES (push): the site sealed it for this device (push.py seal);
 * the browser has opened it, and it says {title, body, url, tag, icon,
 * badge}. It is shown at once, every time: a phone that is handed a nudge and
 * shows nothing stops being handed them (iOS says so). Its tag puts it in the
 * place of the last of the same kind on the same page, rather than stacking
 * three. The number on the icon is Activity's new count when the device
 * keeps that switch on (badge a number), and left as it is otherwise (null).
 *
 * A TAP (notificationclick) opens what it is about, the row's own link in
 * Activity: a window of the site already open goes there and comes forward,
 * else a new one opens (on an iPhone, the Home Screen app). Only the site's
 * own pages: anything else opens Home.
 *
 * The words a nudge says come from the site, Activity's own, so a nudge and
 * its row always match; nothing here says anything. */
'use strict';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });

function here(url) {
  var home = self.registration.scope;
  try {
    var u = new URL(url || home, home);
    return u.origin === self.location.origin ? u.href : home;
  } catch (err) {
    return home;
  }
}

self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = {}; }
  var shown = self.registration.showNotification(d.title || 'Blooby', {
    body: d.body || '',
    icon: d.icon || undefined,
    tag: d.tag || undefined,
    data: { url: here(d.url) }
  });
  var jobs = [shown];
  var nav = self.navigator;
  if (typeof d.badge === 'number' && nav && nav.setAppBadge) {
    jobs.push((d.badge > 0 ? nav.setAppBadge(d.badge) : nav.clearAppBadge()).catch(function () {}));
  }
  e.waitUntil(Promise.all(jobs));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = here(e.notification.data && e.notification.data.url);
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i].url === url && list[i].focus) return list[i].focus();
    }
    for (i = 0; i < list.length; i++) {
      var c = list[i];
      if (c.navigate && c.url.indexOf(self.registration.scope) === 0) {
        return c.navigate(url).then(function (w) { return w ? w.focus() : self.clients.openWindow(url); },
                                    function () { return self.clients.openWindow(url); });
      }
    }
    return self.clients.openWindow(url);
  }));
});
