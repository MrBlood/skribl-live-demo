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
})();
