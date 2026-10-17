/* The menu's Pad | Flip switch moves before it goes (owner's iPhone, after
 * v323: "when I click flip, starts loading flip and never shows the button
 * move, then boom you're in flip. It takes a while to flip back and forth
 * and it never shows the pill move"). One module for both editors' menus.
 *
 * The other editor is a plain link, so the browser left at once and the pill
 * never moved; the screen then sat still while the next editor loaded. Now a
 * tap glides the pill under the other editor and lights its name, and the
 * page goes once it has arrived: at once with reduced motion, and never when
 * the tap means a new tab (a modifier key or another button). The pill is
 * moved here, not by lib/segslider.js, which follows a selected BUTTON and
 * would put it back: the switch is marked with data-going, which it ignores.
 * The other editor's page is fetched ahead, once this one has settled, so
 * going there is quicker. Back from the other editor (the
 * page restored as it was left) puts the pill home again.
 */
(function () {
  'use strict';
  var GLIDE = 280;   // the pill's own glide is .26s (styles.css .seg-slider)
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function wire() {
    var seg = document.querySelector('.menu-editor-seg');
    if (!seg) return;
    var link = seg.querySelector('a.menu-editor');
    var here = seg.querySelector('button.menu-editor');
    if (!link || !here) return;

    link.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      var pill = seg.querySelector('.seg-slider'), a = link.getBoundingClientRect(), h = here.getBoundingClientRect();
      var s = seg.offsetWidth ? seg.getBoundingClientRect().width / seg.offsetWidth : 1;
      if (pill) {
        pill.style.transform = 'translateX(' + ((pill.__x || 0) + (a.left - h.left) / s) + 'px)';
        pill.style.width = a.width / s + 'px';
      }
      seg.setAttribute('data-going', '');
      link.setAttribute('aria-busy', 'true');
      var href = link.href;
      setTimeout(function () { window.location.assign(href); }, reduce ? 0 : GLIDE);
    });
    window.addEventListener('pageshow', function (e) {
      if (!e.persisted) return;
      seg.removeAttribute('data-going');
      link.removeAttribute('aria-busy');
      var pill = seg.querySelector('.seg-slider');
      if (pill) {
        pill.style.transform = 'translateX(' + (pill.__x || 0) + 'px)';
        pill.style.width = (pill.__w || here.getBoundingClientRect().width) + 'px';
      }
    });

    // Ahead of time, once this editor has settled: the other one's page.
    var ahead = function () {
      if (document.querySelector('link[rel="prefetch"][data-editor-ahead]')) return;
      var l = document.createElement('link');
      l.rel = 'prefetch';
      l.href = link.href;
      l.setAttribute('data-editor-ahead', '');
      document.head.appendChild(l);
    };
    if ('requestIdleCallback' in window) window.requestIdleCallback(ahead, { timeout: 6000 });
    else setTimeout(ahead, 3000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
}());
