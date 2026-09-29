/* The Media button and its Photo and Music tabs -- shared by Pad and Flip.

   WHY. Image and Music were two bar buttons on both editors. The bar redesign
   folded them into one Media button (with the colour ring gone, that is what
   lets every control in the phone row be 44x44), which needs three small
   behaviours, identical on both surfaces:

   - Media opens whichever of Photo and Music was used LAST, and closes it if
     either is already open.
   - A tab strip at the top of the media card -- the strip and the open drawer
     are one card (#mediaCard) -- says which one is showing and switches. The
     card itself is shown by CSS while either drawer is open, not from here,
     so a drawer never depends on this file to be seen.
   - Media's status dot MIRRORS the two tab dots, so the bar and the drawer
     cannot disagree: shown if either is, amber (pending) if either is --
     amber beats green because it is the only state that asks something of you.

   Written for Pad first (app.js) and moved here when Flip took the same bar,
   rather than copied: verify_surfaces.py exists because the two editors grew
   parallel implementations no diff shows diverging.

   The surface keeps its own drawer controller (lib/drawers.js); this only
   drives it. attach() returns { sync(name) }, which the controller's photo /
   music onOpen and onClose hooks call so the strip follows every route in. */
(function () {
  'use strict';

  function el(x) { return typeof x === 'string' ? document.getElementById(x) : x; }

  function attach(o) {
    var ctl = o.ctl, button = el(o.button), strip = el(o.strip), out = el(o.dot);
    var last = 'photo';
    var tabs = strip ? strip.querySelectorAll('[data-media-tab]') : [];

    function sync(name) {
      if (name) last = name;
      var cur = ctl ? ctl.current() : null;
      var on = cur === 'photo' || cur === 'music' ? cur : null;
      if (strip) strip.hidden = !on;
      for (var i = 0; i < tabs.length; i++) {
        tabs[i].setAttribute('aria-selected', String(tabs[i].getAttribute('data-media-tab') === on));
      }
    }

    if (button && ctl) button.addEventListener('click', function (e) {
      // Stopped so a surface's click-outside dismisser does not read the tap
      // that opened a drawer as a tap away from it.
      e.stopPropagation();
      var cur = ctl.current();
      ctl.open(cur === 'photo' || cur === 'music' ? null : last);
    });
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function (e) {
        e.stopPropagation();
        if (ctl) ctl.open(this.getAttribute('data-media-tab'));
      });
    }

    var src = (o.sources || []).map(el).filter(Boolean);
    if (out && src.length) {
      var mirror = function () {
        var shown = src.filter(function (d) { return !d.hidden; });
        out.hidden = !shown.length;
        out.classList.toggle('pending', shown.some(function (d) { return d.classList.contains('pending'); }));
      };
      src.forEach(function (d) {
        new MutationObserver(mirror).observe(d, { attributes: true, attributeFilter: ['hidden', 'class'] });
      });
      mirror();
    }
    return { sync: sync };
  }

  window.SkriblMediaTabs = { attach: attach };
})();
