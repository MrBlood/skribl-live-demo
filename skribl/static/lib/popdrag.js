/* Draggable tool popovers — one grip, both editors.
 *
 * WHY. The shape picker anchors above its tool and stays open while a kind
 * has knobs to offer, which means it stands on the exact patch of canvas
 * under the toolbar (owner: "those kind of menus should have a corner you
 * can grab and move so you can start a shape under them"). A press on the
 * canvas already shoves it aside for that one gesture; this is the other
 * half — grab the pill at its top and put the panel where it isn't in the
 * way, then keep adjusting Sides between shapes.
 *
 * MOVED MEANS PINNED. An anchored popover is transient: the press that
 * starts a shape hides it, an outside click hides it. The moment someone
 * DRAGS it they have said "I want this on screen" — so a moved pop stops
 * auto-dismissing (its `data-moved` is the flag the dismissers read) and
 * behaves like a floating palette. It still closes on Escape, on switching
 * tools, and on toggling its own tool button. Premium apps draw the same
 * line: a popover you have repositioned is a panel, not a tooltip.
 *
 * HOW IT MOVES. The pop's stylesheet transform keeps its anchor centering
 * (`translateX(-50%)`) and appends `translate(var(--pop-dx), --pop-dy)`;
 * the drag writes only the two variables, so dragging composes with the
 * anchoring instead of fighting it. Clamped to the viewport with a 4px
 * margin. Hiding the pop clears the variables and the flag via a
 * MutationObserver, so every fresh open is anchored and transient again —
 * a panel parked somewhere last week is a panel lost.
 */
(function () {
  'use strict';

  function attach(pop, grip) {
    if (!pop || !grip) return;
    var active = false, pid = null, sx = 0, sy = 0, bx = 0, by = 0;

    function readVar(name) {
      return parseFloat(pop.style.getPropertyValue(name)) || 0;
    }

    function setOffset(dx, dy) {
      pop.style.setProperty('--pop-dx', dx + 'px');
      pop.style.setProperty('--pop-dy', dy + 'px');
      // Clamp AFTER applying: the rect already includes the anchor transform,
      // so correcting from the visible position handles any anchoring.
      var r = pop.getBoundingClientRect();
      var fx = 0, fy = 0;
      if (r.left < 4) fx = 4 - r.left;
      else if (r.right > window.innerWidth - 4) fx = window.innerWidth - 4 - r.right;
      if (r.top < 4) fy = 4 - r.top;
      else if (r.bottom > window.innerHeight - 4) fy = window.innerHeight - 4 - r.bottom;
      if (fx || fy) {
        pop.style.setProperty('--pop-dx', (dx + fx) + 'px');
        pop.style.setProperty('--pop-dy', (dy + fy) + 'px');
      }
    }

    grip.addEventListener('pointerdown', function (e) {
      // stopPropagation: the grip lives inside a dialog whose outside-click
      // dismissers and canvas handlers must not see this press.
      e.preventDefault();
      e.stopPropagation();
      active = true; pid = e.pointerId;
      sx = e.clientX; sy = e.clientY;
      bx = readVar('--pop-dx'); by = readVar('--pop-dy');
      try { grip.setPointerCapture(e.pointerId); } catch (err) {}
    });
    grip.addEventListener('pointermove', function (e) {
      if (!active || e.pointerId !== pid) return;
      var dx = bx + (e.clientX - sx), dy = by + (e.clientY - sy);
      setOffset(dx, dy);
      // A real drag, not a tap on the pill: only then does the pop pin.
      if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 6) {
        pop.dataset.moved = '1';
      }
    });
    function end(e) {
      if (active && e.pointerId === pid) { active = false; pid = null; }
    }
    grip.addEventListener('pointerup', end);
    grip.addEventListener('pointercancel', end);

    new MutationObserver(function () {
      if (pop.hidden) {
        pop.style.removeProperty('--pop-dx');
        pop.style.removeProperty('--pop-dy');
        delete pop.dataset.moved;
        // A pop hidden mid-gesture must not reopen invisible.
        pop.classList.remove('pop-veiled');
      }
    }).observe(pop, { attributes: true, attributeFilter: ['hidden'] });
  }

  window.SkriblPopDrag = { attach: attach };
}());
