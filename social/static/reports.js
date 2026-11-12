/* Your Reports (piece 5; social/reports.html): an admin's page. Open it lifts
 * the blur from a card for a child's safety, shows its words in place of
 * "Hidden until you open it.", and offers Keep it beside Take it down; and the
 * times are said in the person's own ("3m", "2h"). Both answers are forms, so
 * without this file they still work; the card then stays as it is, and Take it
 * down is the one answer offered for such a card.
 */
(function () {
  'use strict';
  var doc = document;
  Array.prototype.forEach.call(doc.querySelectorAll('[data-unveil]'), function (b) {
    b.addEventListener('click', function () {
      var card = b.closest('[data-rep]');
      if (!card) return;
      Array.prototype.forEach.call(card.querySelectorAll('[data-veil]'), function (v) { v.classList.remove('is-veiled'); });
      Array.prototype.forEach.call(card.querySelectorAll('[data-veil-hide]'), function (v) { v.hidden = true; });
      Array.prototype.forEach.call(card.querySelectorAll('[data-kept], [data-veil-link], [data-veil-show]'), function (f) { f.hidden = false; });
      b.hidden = true;
      var keep = card.querySelector('[data-kept] button');
      if (keep) keep.focus();
    });
  });
  var now = Date.now();
  Array.prototype.forEach.call(doc.querySelectorAll('time[data-when="ago"]'), function (t) {
    var d = new Date(t.getAttribute('datetime'));
    if (isNaN(d)) return;
    var mins = Math.floor((now - d) / 60000);
    if (mins < 1) t.textContent = 'just now';
    else if (mins < 60) t.textContent = mins + 'm ago';
    else if (mins < 1440) t.textContent = Math.floor(mins / 60) + 'h ago';
    else if (mins < 10080) t.textContent = Math.floor(mins / 1440) + 'd ago';
  });
})();
