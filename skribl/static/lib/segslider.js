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

  /* The variant for groups built by JavaScript rather than by a template.
   * They have no markup pill, so one is CREATED, and they are positioned
   * relative to the first button rather than to a fixed 3px padding — the
   * zoom magnifier and focus groups are not `.seg` and do not share its
   * padding. This is not a duplicate of place(): different groups, different
   * offset origin, and the two must not be collapsed into one.
   *
   * app.js and flip.js each carried a byte-for-byte equivalent of this (the
   * only differences were `Array.prototype.slice` against `[].slice`, a
   * variable named `activeBtn` against `a`, and a trailing comma). Both now
   * delegate here.
   */
  function placeAttached(group) {
    if (!group) return;
    var pill = group.__segPill;
    if (!pill) return;
    var btns = [].slice.call(group.querySelectorAll('button'));
    var idx = -1;
    for (var i = 0; i < btns.length; i++) {
      // .on OR .active: the tune-drawer segs mark selection with .on, the
      // attach()-built ones (loop-detail focus/zoom) used .active. Accept both
      // so a group can be built either way (v207 moved the loop-detail bars
      // onto .on to match every other .seg in the app).
      if (btns[i].classList.contains('on') || btns[i].classList.contains('active')) idx = i;
    }
    var a = idx >= 0 ? btns[idx] : null;
    if (!a || !a.offsetWidth) { pill.style.opacity = '0'; return; }
    pill.style.width = a.offsetWidth + 'px';
    pill.style.transform = 'translateX(' + (a.offsetLeft - btns[0].offsetLeft) + 'px)';
    pill.style.opacity = '1';
  }

  function attach(group) {
    if (!group || group.__segAttached) return;
    group.__segAttached = true;
    var pill = document.createElement('div');
    pill.className = 'seg-slider';
    group.insertBefore(pill, group.firstChild);
    group.__segPill = pill;
    var reflow = function () { placeAttached(group); };
    // Active-state changes (clicks, programmatic syncing) all flip the
    // `active` class, so observing it keeps the pill in step without threading
    // a call through every code path that can change the selection.
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(reflow).observe(group, {
        subtree: true, attributes: true, attributeFilter: ['class']
      });
    }
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(reflow).observe(group);
    } else if (global.addEventListener) {
      global.addEventListener('resize', reflow);
    }
    reflow();
  }

  /* SELECTED MEANS SELECTED (v292; outside review of v291, SK-AUD-006).
   *
   * The draw drawer's segs carried aria-pressed and kept it in step by hand.
   * Every other seg — Speed, grid density, onion depth, Tips, Theme, Canvas,
   * export Size and Loops, the GIF background, the loop-view focus, pause and
   * speed on the Pad, the move scope on Flip — lit a class and said nothing,
   * so a screen reader heard "Playback speed, group. 6. 12. 24." and no word
   * on which. Eighteen groups, a dozen toggle sites, two editors.
   *
   * ONE OWNER, BY THE SAME MECHANISM THE PILL ALREADY USES: the selected
   * option is the one lit by .on or .active, and this module already watches
   * exactly that class to move the pill. So one document-level observer
   * writes aria-pressed from the class on every seg, including segs built
   * later by script and segs inside sheets that ship hidden. No toggle site
   * needs to know. A seg that manages aria-pressed itself (the draw drawer)
   * is written the same value it already holds. The attributeFilter is
   * 'class' alone, so writing aria-pressed here cannot re-enter the observer.
   *
   * verify_a11y section 4 is the census: every option carries the state,
   * exactly one is pressed per one-of-N seg (a data-role="focus" group has a
   * free state and may have none), the state agrees with the class, and it
   * follows a click.
   */
  var SEGS = '.seg, .smooth-seg, .gif-seg';
  function lit(b) { return b.classList.contains('on') || b.classList.contains('active'); }
  function syncPressed(group) {
    var btns = group.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
      var want = lit(btns[i]) ? 'true' : 'false';
      if (btns[i].getAttribute('aria-pressed') !== want) btns[i].setAttribute('aria-pressed', want);
    }
  }
  function syncAll(root) {
    var gs = (root || document).querySelectorAll(SEGS);
    for (var i = 0; i < gs.length; i++) syncPressed(gs[i]);
  }
  function watchDocument() {
    if (global.__skriblSegPressed) return;
    global.__skriblSegPressed = true;
    syncAll();
    if (typeof MutationObserver === 'undefined') return;
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i], t = m.target;
        if (!t || t.nodeType !== 1) continue;
        if (m.type === 'attributes') {
          var g = t.closest ? t.closest(SEGS) : null;
          if (g) syncPressed(g);
        } else {
          for (var j = 0; j < m.addedNodes.length; j++) {
            var n = m.addedNodes[j];
            if (n.nodeType !== 1) continue;
            if (n.matches && n.matches(SEGS)) syncPressed(n);
            else if (n.closest && n.closest(SEGS)) syncPressed(n.closest(SEGS));
            if (n.querySelectorAll) syncAll(n);
          }
        }
      }
    }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchDocument);
  else watchDocument();

  global.SkriblSegSlider = { track: track, trackAll: trackAll, place: place,
                             attach: attach, placeAttached: placeAttached,
                             syncPressed: syncPressed, syncAll: syncAll };
})(window);
