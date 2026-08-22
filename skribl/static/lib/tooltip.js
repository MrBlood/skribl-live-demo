/* Styled tooltips, replacing the browser's.
 *
 * WHY A LIB AND NOT CSS. A native `title` tooltip cannot be styled at all —
 * not the corners, not the colour, not the delay. It is operating-system
 * chrome. The only way to round a corner is to stop using it and draw one.
 *
 * HOW IT BEHAVES, and why each choice:
 *
 *   title -> data-tip, and the title is REMOVED. Leaving it in place shows
 *   both tooltips, ours immediately and the browser's a second later, stacked.
 *
 *   aria-label is left alone. It is what a screen reader announces; the
 *   tooltip is a visual affordance and must not fight it. Where an element has
 *   no aria-label, the tip is exposed via aria-describedby instead so the
 *   information is not sighted-only.
 *
 *   Hover AND keyboard focus. A tooltip only reachable with a mouse is not a
 *   tooltip, it is a mouse decoration.
 *
 *   Not on touch. There is no hover on a phone; a "tooltip" there fires on tap
 *   and covers the thing you just pressed. Suppressed on coarse pointers.
 *
 *   One element, reused. A node per button would be 125 of them, all
 *   positioned, all reflowing.
 */
(function (global) {
  'use strict';

  var GAP = 8;         // px between the control and the bubble
  var DELAY = 380;     // long enough not to flicker while crossing a toolbar

  var el = null, timer = null, current = null, seq = 0;

  function coarse() {
    return global.matchMedia && global.matchMedia('(pointer: coarse)').matches;
  }

  function ensure() {
    if (el) return el;
    el = document.createElement('div');
    el.className = 'skribl-tip';
    el.setAttribute('role', 'tooltip');
    el.hidden = true;
    document.body.appendChild(el);
    return el;
  }

  function place(target) {
    var tip = ensure();
    var r = target.getBoundingClientRect();
    var t = tip.getBoundingClientRect();

    // Above by default; below when there is not room, so a tooltip on the top
    // toolbar is not clipped off the window.
    var top = r.top - t.height - GAP;
    var below = false;
    if (top < 4) { top = r.bottom + GAP; below = true; }

    // Clamp horizontally rather than letting a wide tip run off the edge.
    var left = r.left + (r.width - t.width) / 2;
    left = Math.max(6, Math.min(left, global.innerWidth - t.width - 6));

    tip.style.top = Math.round(top) + 'px';
    tip.style.left = Math.round(left) + 'px';
    tip.classList.toggle('below', below);
  }

  function show(target) {
    var text = target.getAttribute('data-tip');
    if (!text) return;
    var tip = ensure();
    tip.textContent = text;
    tip.hidden = false;
    tip.classList.remove('in');
    place(target);
    // Second frame so the transition runs from the placed position rather than
    // animating across the screen from wherever the tip was last shown.
    global.requestAnimationFrame(function () {
      global.requestAnimationFrame(function () { tip.classList.add('in'); });
    });
    current = target;

    if (!target.getAttribute('aria-label') && !target.getAttribute('aria-describedby')) {
      tip.id = tip.id || 'skribl-tip-' + (++seq);
      target.setAttribute('aria-describedby', tip.id);
    }
  }

  function hide() {
    clearTimeout(timer);
    if (current) {
      if (el && current.getAttribute('aria-describedby') === el.id) {
        current.removeAttribute('aria-describedby');
      }
      current = null;
    }
    if (el) { el.classList.remove('in'); el.hidden = true; }
  }

  function adopt(root) {
    var nodes = (root || document).querySelectorAll('[title]');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var t = n.getAttribute('title');
      if (!t) continue;
      n.setAttribute('data-tip', t);
      n.removeAttribute('title');
    }
  }

  function init() {
    if (coarse()) return null;   // no hover: nothing to show
    adopt(document);

    // Delegated, so controls built later (the zoom bar, the pan slider, any
    // future drawer) are covered without re-running anything.
    document.addEventListener('mouseover', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      if (!t || t === current) return;
      clearTimeout(timer);
      timer = setTimeout(function () { show(t); }, DELAY);
    });
    document.addEventListener('mouseout', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      if (t) hide();
    });
    // Keyboard users get it immediately: they have already committed to the
    // control by tabbing to it, so a delay is just a wait.
    document.addEventListener('focusin', function (e) {
      var t = e.target.closest && e.target.closest('[data-tip]');
      if (t) show(t);
    });
    document.addEventListener('focusout', hide);
    // Any of these can move the control out from under the bubble.
    ['scroll', 'resize', 'wheel'].forEach(function (ev) {
      global.addEventListener(ev, hide, true);
    });
    document.addEventListener('click', hide, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hide();
    });

    // A MutationObserver keeps late markup (drawers rendered on open) covered.
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          var added = muts[i].addedNodes;
          for (var j = 0; j < added.length; j++) {
            if (added[j].nodeType === 1) adopt(added[j]);
          }
        }
      }).observe(document.body, { childList: true, subtree: true });
    }

    return { show: show, hide: hide, adopt: adopt };
  }

  global.SkriblTooltip = { init: init, adopt: adopt, hide: hide };
})(window);
