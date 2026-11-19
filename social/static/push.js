/* NUDGES ON THIS DEVICE (push notifications; Blooby's Nudges, the owner's
 * "All yes", Nov 18; social/push.py, push-sw.js). On every page of somebody
 * signed in (base.html's social-push meta). It says nothing itself: the words
 * are the pages' own (activity.html's card, you.html's panel).
 *
 * EVERY PAGE: where nudges were turned on here and the page's sign-in is a
 * new one (its mark), /push/state is asked once, so this device follows the
 * sign-in, or stops being nudged for somebody no longer signed in here.
 * Where they never were, nothing at all: no service worker is made until
 * somebody turns nudges on.
 *
 * ACTIVITY'S CARD, ASKED ONCE (the owner's A): shown where this device can
 * be nudged, was never told no, is not nudged already, and nobody said Not
 * now here. Not now puts it away for good on this device (Settings keeps the
 * switches). Turn on asks the browser, from the tap (an iPhone asks only
 * then); told no, the card goes, and Settings says where to allow it. The
 * card glides open and away (social.css, the fold). Opening Activity also
 * clears the number on the icon and the nudges already shown: everything in
 * them is seen now.
 *
 * SETTINGS' PANEL shows the one state this device is in: its switches (the
 * device's own, as the permission is), Turn on, told no, or the way to the
 * Home Screen app (an iPhone or an iPad in a browser tab, where no browser
 * can be nudged); a browser that cannot be nudged shows no panel. A state
 * known at once is put there as the page is drawn; one that waits on the
 * site glides in. A switch moves at once and says so to the site; one the
 * site did not take goes back, and says so.
 *
 * TURNING ON: the browser's permission, then the service worker (push-sw.js,
 * at the site's own folder), then the browser's subscription with the site's
 * key, handed to /push/subscribe. A subscription made with another key (a
 * new SECRET_KEY) is made again. */
(function () {
  'use strict';
  var doc = document, win = window, nav = win.navigator;
  var meta = doc.querySelector('meta[name="social-push"]');
  if (!meta) return;
  var tokenMeta = doc.querySelector('meta[name="social-csrf"]');
  var token = tokenMeta ? tokenMeta.getAttribute('content') : '';
  var KEY = meta.getAttribute('content') || '';
  var MARK = meta.getAttribute('data-mark') || '';
  var SW = meta.getAttribute('data-sw');
  var SCOPE = meta.getAttribute('data-scope');
  var LATER = 'blooby.push.later', SEEN = 'blooby.push.mark';
  var can = 'serviceWorker' in nav && 'PushManager' in win && 'Notification' in win;
  var reduce = false;
  try { reduce = win.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { /* none */ }

  function kept(k) { try { return win.localStorage.getItem(k); } catch (e) { return null; } }
  function keep(k, v) { try { win.localStorage.setItem(k, v); } catch (e) { /* this visit only */ } }

  function post(path, body) {
    return fetch(SCOPE + path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': token },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw j;
        return j;
      }, function () { throw {}; });
    });
  }

  function bytes(b64) {
    var s = b64.replace(/-/g, '+').replace(/_/g, '/');
    s += '===='.slice(0, (4 - s.length % 4) % 4);
    var raw = win.atob(s), out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  /* Made with the site's key, as far as the browser says. */
  function ours(sub) {
    var k = sub && sub.options && sub.options.applicationServerKey;
    if (!k) return true;
    var a = new Uint8Array(k), b = bytes(KEY);
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
    return true;
  }

  function apple() {
    return /iP(hone|od|ad)/.test(nav.userAgent || '') || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
  }
  function installed() {
    var s = nav.standalone === true;
    try { s = s || win.matchMedia('(display-mode: standalone)').matches; } catch (e) { /* none */ }
    return s;
  }
  /* What this device is called: phone, tablet or computer. */
  function called() {
    if (apple()) return /iP(hone|od)/.test(nav.userAgent || '') ? 'phone' : 'tablet';
    var coarse = false;
    try { coarse = win.matchMedia('(pointer: coarse)').matches; } catch (e) { /* none */ }
    if (!coarse) return 'computer';
    return Math.min(win.screen.width || 0, win.screen.height || 0) >= 600 ? 'tablet' : 'phone';
  }
  function name(root) {
    var w = called(), spans = root.querySelectorAll('[data-push-device]');
    for (var i = 0; i < spans.length; i++) spans[i].textContent = spans[i].getAttribute('data-' + w) || spans[i].textContent;
  }
  function say(root, which) {
    var p = root.querySelector('.push-said');
    if (p) p.textContent = which ? (p.getAttribute('data-' + which) || '') : '';
  }

  /* This device's subscription, where nudges were turned on here: {reg, sub}, or null. */
  function mine() {
    if (!can || Notification.permission !== 'granted') return Promise.resolve(null);
    return nav.serviceWorker.getRegistration(SCOPE).then(function (reg) {
      if (!reg) return null;
      return reg.pushManager.getSubscription().then(function (sub) { return sub ? { reg: reg, sub: sub } : null; });
    }).catch(function () { return null; });
  }

  /* What the site keeps for it, with this sign-in: its switches, or null. */
  function state(d) {
    if (!d) {
      keep(SEEN, MARK);
      return Promise.resolve(null);
    }
    return post('push/state', { endpoint: d.sub.endpoint }).then(function (j) {
      keep(SEEN, MARK);
      return j.on || null;
    });
  }

  /* Turn nudges on here: {on, sub}, or {told} where the browser was not
     allowed. Asked from a tap, the permission first. */
  function turnOn() {
    var asked;
    if (Notification.permission === 'granted') {
      asked = Promise.resolve('granted');
    } else {
      asked = new Promise(function (res) {
        var p = Notification.requestPermission(res);
        if (p && p.then) p.then(res, function () { res('default'); });
      });
    }
    return asked.then(function (perm) {
      if (perm !== 'granted') return { told: perm };
      return nav.serviceWorker.register(SW, { scope: SCOPE }).then(function () {
        return nav.serviceWorker.ready;
      }).then(function (reg) {
        return reg.pushManager.getSubscription().then(function (old) {
          if (old && ours(old)) return old;
          return (old ? old.unsubscribe() : Promise.resolve(true)).then(function () {
            return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytes(KEY) });
          });
        });
      }).then(function (sub) {
        return post('push/subscribe', sub.toJSON()).then(function (j) {
          keep(SEEN, MARK);
          return { on: j.on, sub: sub };
        });
      });
    });
  }

  /* THE FOLD: open glides the room open and the card in; shut, the reverse
     (social.css). Under Reduce Motion it is put in place, or away, at once. */
  function settle(fold, prop, then) {
    if (reduce) { then(); return; }
    var over = false, timer = 0;
    function end(e) {
      if (e && (e.target !== fold.firstElementChild && e.target !== fold)) return;
      if (e && e.propertyName !== prop) return;
      if (over) return;
      over = true;
      fold.removeEventListener('transitionend', end);
      clearTimeout(timer);
      then();
    }
    fold.addEventListener('transitionend', end);
    timer = setTimeout(end, 520);
  }
  /* now: put there as the page is first drawn (a state known at once),
     never gliding in under the person's eyes. */
  function open(fold, now) {
    fold.hidden = false;
    if (now) {
      fold.classList.add('is-now', 'is-open', 'is-still');
      void fold.offsetHeight;
      fold.classList.remove('is-now');
      return;
    }
    void fold.offsetHeight;
    fold.classList.add('is-open');
    settle(fold, 'grid-template-rows', function () { if (fold.classList.contains('is-open')) fold.classList.add('is-still'); });
  }
  function shut(fold, then) {
    fold.classList.remove('is-still', 'is-open');
    settle(fold, 'grid-template-rows', function () {
      if (!fold.classList.contains('is-open')) fold.hidden = true;
      if (then) then();
    });
  }
  /* What the card holds changes, and its room glides to the new height. */
  function resize(fold, change) {
    var inner = fold.firstElementChild;
    var from = inner.getBoundingClientRect().height;
    change();
    var to = inner.getBoundingClientRect().height;
    if (reduce || fold.hidden || Math.abs(to - from) < 1) return;
    fold.classList.remove('is-still');
    inner.style.height = from + 'px';
    void inner.offsetHeight;
    inner.style.transition = 'height 0.32s cubic-bezier(0.2, 0.8, 0.2, 1)';
    inner.style.height = to + 'px';
    settle(fold, 'height', function () {
      inner.style.height = '';
      inner.style.transition = '';
      if (fold.classList.contains('is-open')) fold.classList.add('is-still');
    });
  }
  /* Focus that was in a card going away goes on to what is next. */
  function onward(fold, next) {
    if (fold.contains(doc.activeElement) && next) next.focus();
  }

  // ---- Activity ---------------------------------------------------------------

  var ask = doc.querySelector('[data-push-ask]');
  if (ask) {
    // Everything in the nudges already shown is seen now, as Activity marks it.
    if (nav.clearAppBadge) nav.clearAppBadge().catch(function () { /* none */ });
    if (can && Notification.permission === 'granted') {
      nav.serviceWorker.getRegistration(SCOPE).then(function (reg) {
        if (reg && reg.getNotifications) {
          return reg.getNotifications().then(function (list) { list.forEach(function (n) { n.close(); }); });
        }
      }).catch(function () { /* none */ });
    }
    var later = ask.querySelector('[data-push-later]'), turn = ask.querySelector('[data-push-on]');
    var next = function () { return doc.querySelector('.act-row, .act-empty .btn'); };
    later.addEventListener('click', function () {
      keep(LATER, '1');
      onward(ask, next());
      shut(ask);
    });
    turn.addEventListener('click', function () {
      if (turn.getAttribute('aria-busy') === 'true') return;
      turn.setAttribute('aria-busy', 'true');
      say(ask, null);
      turnOn().then(function (r) {
        turn.removeAttribute('aria-busy');
        if (r.told === 'default') return;      // the browser's question was closed unanswered
        onward(ask, next());
        shut(ask);
      }, function () {
        turn.removeAttribute('aria-busy');
        say(ask, 'failed');
      });
    });
    if (can && Notification.permission !== 'denied' && kept(LATER) !== '1') {
      name(ask);
      if (Notification.permission === 'default') {
        open(ask);
      } else {
        mine().then(state).then(function (on) { if (!on) open(ask); }, function () { /* asked again next time */ });
      }
    }
  }

  // ---- Settings -----------------------------------------------------------------

  var panel = doc.querySelector('[data-push-panel]');
  var device = null;

  /* Theme's pill under the pressed choice (you.js's place, for these rows). */
  function place(sw, first) {
    var pill = sw.querySelector('.theme-pill');
    var on = sw.querySelector('button[aria-pressed="true"]');
    var g = sw.getBoundingClientRect(), b = on ? on.getBoundingClientRect() : null;
    if (!pill || !b || !b.width || !g.width) { sw.removeAttribute('data-pill'); return; }
    var x = Math.round((b.left - g.left - sw.clientLeft - (parseFloat(getComputedStyle(pill).left) || 0)) * 100) / 100;
    if (first) pill.style.transition = 'opacity 0.18s ease';
    pill.style.transform = 'translateX(' + x + 'px)';
    pill.style.width = (Math.round(b.width * 100) / 100) + 'px';
    if (first) {
      sw.setAttribute('data-pill', '');
      void pill.offsetWidth;
      pill.style.transition = '';
    }
  }
  function press(sw, choice, first) {
    var bs = sw.querySelectorAll('button[data-choice]');
    for (var i = 0; i < bs.length; i++) bs[i].setAttribute('aria-pressed', bs[i].getAttribute('data-choice') === choice ? 'true' : 'false');
    place(sw, first);
  }
  function switches(on, first) {
    var sws = panel.querySelectorAll('[data-push-kind]');
    for (var i = 0; i < sws.length; i++) press(sws[i], on[sws[i].getAttribute('data-push-kind')] ? 'on' : 'off', first);
  }
  function show(which) {
    var parts = panel.querySelectorAll('[data-push-when]');
    for (var i = 0; i < parts.length; i++) parts[i].hidden = parts[i].getAttribute('data-push-when') !== which;
  }
  function becomes(which, on, now) {
    var first = panel.hidden;
    if (first) {
      show(which);
      open(panel, now);
    } else {
      resize(panel, function () { show(which); });
    }
    if (on) switches(on, true);
  }

  if (panel) {
    name(panel);
    if (!can) {
      // A browser that cannot be nudged has nothing to show here, but an
      // iPhone or an iPad in a browser tab: there nudges come to the Home
      // Screen app.
      if (apple() && !installed()) becomes('install', null, true);
    } else if (Notification.permission === 'denied') {
      becomes('denied', null, true);
    } else {
      mine().then(function (d) {
        return state(d).then(function (on) {
          if (on) {
            device = d;
            becomes('on', on);
          } else {
            becomes('off');
          }
        });
      }).catch(function () { becomes('off'); });
    }
    var turnHere = panel.querySelector('[data-push-on]');
    turnHere.addEventListener('click', function () {
      if (turnHere.getAttribute('aria-busy') === 'true') return;
      turnHere.setAttribute('aria-busy', 'true');
      say(panel, null);
      turnOn().then(function (r) {
        turnHere.removeAttribute('aria-busy');
        if (r.told) {
          if (r.told === 'denied') becomes('denied');
          return;
        }
        device = { sub: r.sub };
        keep(LATER, '1');
        becomes('on', r.on);
        var first = panel.querySelector('[data-push-kind] button[aria-pressed="true"]');
        if (first) first.focus();
      }, function () {
        turnHere.removeAttribute('aria-busy');
        say(panel, 'failed');
      });
    });
    panel.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-push-kind] > button[data-choice]') : null;
      if (!b || !device || b.getAttribute('aria-pressed') === 'true') return;
      var sw = b.parentElement, kind = sw.getAttribute('data-push-kind');
      var was = sw.querySelector('button[aria-pressed="true"]');
      var want = b.getAttribute('data-choice') === 'on';
      press(sw, b.getAttribute('data-choice'));
      say(panel, null);
      post('push/prefs', { endpoint: device.sub.endpoint, kind: kind, on: want }).then(function () {
        if (kind === 'badge' && !want && nav.clearAppBadge) nav.clearAppBadge().catch(function () { /* none */ });
      }, function (j) {
        if (j && j.error === 'gone') {
          device = null;
          becomes('off');
          return;
        }
        press(sw, was ? was.getAttribute('data-choice') : (want ? 'off' : 'on'));
        say(panel, 'failed');
      });
    });
    var home = panel.querySelector('[data-push-home]'), steps = doc.getElementById('homeSteps');
    if (home && steps && win.SocialSheet) {
      var stepsApi = win.SocialSheet(steps, { first: function () { return steps.querySelector('.btn-primary'); } });
      home.addEventListener('click', function () {
        var icon = steps.querySelector('img');
        if (icon) icon.loading = 'eager';
        stepsApi.open(home);
      });
    }
    win.addEventListener('resize', function () {
      if (panel.hidden) return;
      var sws = panel.querySelectorAll('[data-push-kind]');
      for (var i = 0; i < sws.length; i++) place(sws[i], false);
    });
  }

  // ---- every other page: the device follows the sign-in ----------------------------

  if (!ask && !panel && can && Notification.permission === 'granted' && kept(SEEN) !== MARK) {
    mine().then(state).catch(function () { /* asked again next page */ });
  }
})();
