/* You and Invites (social/templates/social/you.html, invites.html).
 *
 * TIMES IN THE PERSON'S OWN ZONE (docs/SOCIAL-SITE.md, section 3, rule 13):
 * the server writes each time as a UTC stamp on a <time>, and its plain UTC
 * day for a page without scripts; this writes it again as the person's own
 * clock says it ("Nov 10", or "Nov 10, 4:31 PM" where the hour matters).
 *
 * COPY LINK: a new invite link is shown once, in a field; the button copies
 * it and says so for a moment ("Copied", the button's own data-copied), and
 * where the clipboard is not allowed the link is selected for copying by hand.
 *
 * THE THEME (Settings, after v330; the owner's "Yes to all", Nov 13): Pad's
 * switch, for Blooby, Pad and Flip. The choice is Skribl's own, read and set
 * only through SkriblTheme (lib/theme.js, on every page of the site, with its
 * head boot): this presses what is kept (System when nothing is), puts the
 * pill under it, and on a tap sets the choice INSIDE A VIEW TRANSITION, so
 * the page cross-fades from the theme it was in to the new one in the site's
 * 0.28s (social.css) while the pill slides there in Pad's 0.26s. Under Reduce
 * Motion the page still fades and the pill is put there. A browser without
 * view transitions changes at once.
 *
 * A TAP DURING THE FADE IS KEPT. While a view transition runs the browser
 * shows a picture of the page, and a tap lands on the page itself (<html>),
 * not on the switch: so a tap there is matched to the choice under it, and a
 * choice made while the page fades waits for that fade to end and then fades
 * again, so the page never jumps from half way.
 *
 * A CHOICE MADE ELSEWHERE (another tab, or the Pad over a page of the site):
 * SkriblTheme hears it and says so, and the switch moves to it.
 */
(function () {
  'use strict';
  var doc = document;
  var day = null, dayYear = null, hour = null;
  try {
    day = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' });
    dayYear = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    hour = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  } catch (e) { /* the server's UTC day stays */ }
  if (day) {
    var thisYear = new Date().getFullYear();
    Array.prototype.forEach.call(doc.querySelectorAll('time[datetime]'), function (t) {
      var d = new Date(t.getAttribute('datetime'));
      if (isNaN(d.getTime())) return;
      /* This year's days without the year, as people say them. */
      t.textContent = (t.hasAttribute('data-time') ? hour : d.getFullYear() === thisYear ? day : dayYear).format(d);
    });
  }

  Array.prototype.forEach.call(doc.querySelectorAll('[data-copy]'), function (btn) {
    var field = doc.getElementById(btn.getAttribute('data-copy'));
    if (!field) return;
    var label = btn.textContent, timer = 0;
    btn.addEventListener('click', function () {
      function done() {
        btn.textContent = btn.getAttribute('data-copied') || label;
        clearTimeout(timer);
        timer = setTimeout(function () { btn.textContent = label; }, 2000);
      }
      function byHand() { field.focus(); field.select(); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(field.value).then(done, byHand);
      } else {
        byHand();
      }
    });
  });

  var T = window.SkriblTheme, sw = doc.querySelector('[data-theme-switch]');
  if (!T || !sw) return;
  var pill = sw.querySelector('.theme-pill');
  var opts = Array.prototype.slice.call(sw.querySelectorAll('button[data-choice]'));
  var fading = null, waiting = null;

  /* The pill under the pressed choice, from the rendered boxes to the
     hundredth of a pixel (as the site's other pill is placed, follows.js).
     The first time it fades in where it belongs; after that it slides. */
  function place(first) {
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
  function show(choice, first) {
    opts.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-choice') === choice ? 'true' : 'false'); });
    place(first);
  }
  function choose(choice) {
    if (fading) { waiting = choice; return; }
    if (choice === T.mode()) return;
    var go = function () { T.set(choice); show(T.mode(), false); };
    if (!doc.startViewTransition) { go(); return; }
    var vt = doc.startViewTransition(go);
    fading = vt;
    var done = function () {
      fading = null;
      var next = waiting;
      waiting = null;
      if (next) choose(next);
    };
    vt.finished.then(done, done);
  }

  show(T.mode(), true);
  T.onChange(function () { if (!fading) show(T.mode(), false); });
  sw.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button[data-choice]') : null;
    if (b) choose(b.getAttribute('data-choice'));
  });
  doc.addEventListener('click', function (e) {
    if (!fading || e.target !== doc.documentElement) return;
    for (var i = 0; i < opts.length; i++) {
      var r = opts[i].getBoundingClientRect();
      if (e.clientX >= r.left && e.clientX < r.right && e.clientY >= r.top && e.clientY < r.bottom) {
        choose(opts[i].getAttribute('data-choice'));
        return;
      }
    }
  });
  /* Brought back whole by the back button (social.js puts the page in the
     theme chosen meanwhile): the switch says that choice. */
  window.addEventListener('pageshow', function (e) { if (e.persisted) show(T.mode(), true); });
})();
