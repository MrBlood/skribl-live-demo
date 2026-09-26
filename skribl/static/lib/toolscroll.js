/* The Pad toolbar on the smallest screens: one row that scrolls, and says so.
 *
 * WHY (SK312-005; owner's choice of the three mockups, v315). At 320px the
 * eight controls do not fit one row, so the toolbar wrapped: music dropped to a
 * second line and the bar grew from 56px to 92px, taken out of the drawing.
 * The owner picked the scrolling row over merging photo and music into one
 * button -- "as long as you see part of it, or it wobbles to show you then goes
 * to normal ... which may be the direction if we get more tools".
 *
 * SO, ONLY WHEN THE ROW DOES NOT FIT: the toolbar becomes a single scrolling
 * row (`.tb-scroll`), its far edge fades so the last tool reads as cut off,
 * and ONCE per page load it glides to the end and settles back -- a nudge that
 * there is more, not a tour. Where the row fits, nothing here changes a pixel.
 *
 * THE POPOVERS. The shape picker and the tool tray hang above the toolbar from
 * inside it, and a scrolling element clips its children on both axes. In
 * scroll mode they are fixed to the viewport instead, at the height this file
 * publishes as --tb-top, so the row can scroll without cutting them off.
 *
 * Reduced motion: no glide; the fade and the cut-off tool still say it.
 * A finger on the row cancels the glide -- never fight the person.
 */
(function () {
  'use strict';

  var bar = document.getElementById('toolBar');
  if (!bar) return;
  var nudged = false;
  var timers = [];

  function publishTop() {
    var r = bar.getBoundingClientRect();
    document.documentElement.style.setProperty('--tb-top', Math.round(r.top) + 'px');
  }

  function fit() {
    // Measure in scroll mode: a one-row bar that is wider than its box does not fit.
    bar.classList.add('tb-scroll');
    var overflows = bar.scrollWidth > bar.clientWidth + 1;
    if (!overflows) bar.classList.remove('tb-scroll');
    publishTop();
    return overflows;
  }

  function cancel() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function nudge() {
    if (nudged) return;
    nudged = true;
    var still = false;
    try { still = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { /* keep motion */ }
    if (still) return;
    timers.push(setTimeout(function () {
      bar.scrollTo({ left: bar.scrollWidth - bar.clientWidth, behavior: 'smooth' });
      timers.push(setTimeout(function () {
        bar.scrollTo({ left: 0, behavior: 'smooth' });
      }, 900));
    }, 700));
  }

  ['pointerdown', 'wheel', 'touchstart'].forEach(function (k) {
    bar.addEventListener(k, cancel, { passive: true });
  });
  window.addEventListener('resize', function () { fit(); });
  window.addEventListener('scroll', publishTop, { passive: true });

  function start() {
    if (fit()) nudge();
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);

  window.SkriblToolScroll = { fit: fit };
})();
