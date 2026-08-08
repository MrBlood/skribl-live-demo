/* Keeps a .seg-slider pill aligned to the selected button in a .seg group.
 *
 * THE BUG THIS EXISTS FOR. .seg-slider is `opacity: 0` until something
 * positions it, and positioning needs the button laid out — `offsetWidth > 0`.
 * Inside a sheet or menu that ships `hidden`, that is never true at init, so a
 * one-shot call bails and the pill stays invisible until an unrelated event
 * happens to re-run it. Symptom: Flip's export sheet opened with no pill on
 * Size or Loops, and Pad's canvas row showed no selection until you tapped
 * one — on a phone, where the sheet is laid out later than on desktop.
 *
 * `attachSegSlider` in app.js already solved this for the DYNAMICALLY built
 * zoom/magnify groups using MutationObserver + ResizeObserver. The groups
 * written directly into templates never got the same treatment. This is that
 * treatment, shared, for both.
 *
 * Reposition triggers, all three needed:
 *   ResizeObserver   - fires when the group gains layout, i.e. when the sheet
 *                      that contains it is finally shown. This is the one that
 *                      actually fixes the reported bug.
 *   MutationObserver - the selected button is marked by a class, and the app
 *                      changes it without telling us.
 *   window resize    - orientation change on a phone.
 */
(function (global) {
  'use strict';

  function selected(group) {
    return group.querySelector('button.on') || group.querySelector('button.active');
  }

  function place(group) {
    var pill = group.querySelector('.seg-slider');
    var btn = selected(group);
    if (!pill) return;
    // No layout yet: leave the pill hidden rather than parking it at a wrong
    // position that would then animate across the control when layout arrives.
    if (!btn || !btn.offsetWidth) { pill.style.opacity = '0'; return; }
    pill.style.width = btn.offsetWidth + 'px';
    pill.style.transform = 'translateX(' + (btn.offsetLeft - 3) + 'px)';
    pill.style.opacity = '1';
  }

  function track(group) {
    if (!group || group.__segTracked) return;
    group.__segTracked = true;

    var reflow = function () { place(group); };

    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(reflow).observe(group);
    }
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(reflow).observe(group, {
        subtree: true, attributes: true, attributeFilter: ['class']
      });
    }
    global.addEventListener('resize', reflow);

    // Two frames, not one: the first lands before the browser has laid out a
    // sheet revealed in the same tick, which is exactly the case that failed.
    reflow();
    global.requestAnimationFrame(function () {
      reflow();
      global.requestAnimationFrame(reflow);
    });
  }

  function trackAll(root) {
    var groups = (root || document).querySelectorAll('.seg');
    for (var i = 0; i < groups.length; i++) track(groups[i]);
  }

  global.SkriblSegSlider = { track: track, trackAll: trackAll, place: place };
})(window);
