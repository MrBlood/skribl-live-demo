/* THE PILL. Every pick-one control in the product slides one soft tint under
 * its selected option, and this is the one thing that places it (the owner,
 * choosing between four mocked shapes: "a on the pill").
 *
 * WHICH CONTROLS. Two sets, because they differ in what they may say:
 *
 *   SEGS    .seg, .smooth-seg, .gif-seg, .photo-fit-group -- the editors'
 *           segmented controls. The selected option is lit by a CLASS (.on or
 *           .active), and this module writes aria-pressed, the one Tab stop
 *           and the arrow keys from that class (SELECTED MEANS SELECTED,
 *           below).
 *   TRACKS  SEGS plus .seg-track -- the gallery's New / Hot, the library's
 *           tabs and filter, the page menu's Theme -- and the dock's tool
 *           group, which lib/toolshelf.js hands over. These keep their own
 *           semantics (a tablist, aria-pressed buttons their pages write), so
 *           a .seg-track is read from its aria state as well as its class and
 *           is never written to.
 *
 * THE BUG THIS EXISTS FOR. A pill is only right once its selected option has
 * been laid out, and inside a sheet or a drawer that ships `hidden` that is
 * never true at init: a one-shot call bails and the pill never appears
 * (Flip's export sheet opened with no pill on Size or Loops; Pad's canvas row
 * showed no selection until you tapped one). So a track is WATCHED rather than
 * placed:
 *   ResizeObserver   - the track or an option gains or changes size (the sheet
 *                      that holds it is shown; a label's width changes).
 *   MutationObserver - the selection changes (class, aria-pressed,
 *                      aria-selected) or an option shows, hides or arrives.
 *   window resize    - orientation change on a phone. fonts.ready: a face
 *                      that lands late changes every width.
 *
 * WHERE, TO THE SUB-PIXEL. The pill used to be placed from offsetLeft and
 * offsetWidth, which are INTEGERS, on flex options that are not: at 390px the
 * Brush row's options are 81.5px wide and the pill overhung Marker by a whole
 * pixel (three device pixels) and sat asymmetric in the track. It is placed
 * from the rendered boxes now, measured against the pill's own origin, so it
 * covers the selected option exactly whatever its width. An ancestor that
 * SCALES (a sheet's entrance) scales both boxes alike; the ratio of the
 * track's rendered width to its layout width takes it back out.
 *
 * ONE PILL, OWNED HERE. Every template track carries its pill; a track built
 * by script gets one made the first time it is watched, and never a second --
 * the Pad's draw drawer once carried two (a made one that moved and the
 * template's, stuck at opacity 0). Surfaces no longer place pills themselves:
 * they change the selection, and this follows it.
 *
 * WHAT THE PILL DOES NOT DO: paint the selection by itself. Until a pill is
 * placed (data-pill on the track) the selected option wears the same tint
 * ITSELF, in CSS -- so a track this script never reaches, on a device where the
 * measuring never lands, still shows what is chosen (owner, on an iPhone: the
 * tune drawer's options "never got that treatment"). The first placement is
 * instant, not a slide from the left edge, so the hand-over from the option's
 * own tint to the pill cannot be seen.
 */
(function (global) {
  'use strict';

  var SEGS = '.seg, .smooth-seg, .gif-seg, .photo-fit-group';
  var TRACKS = SEGS + ', .seg-track';
  var PILLS = ':scope > .seg-slider, :scope > .photo-fit-slider, :scope > .tool-slider';

  function selected(group) {
    var b = group.querySelector(':scope > button.on, :scope > button.active');
    // A seg's aria-pressed is WRITTEN from its class (below), so between a
    // click and that write it can be one option stale: a seg answers from the
    // class alone. A page track has no such writer, and its own script may
    // mark the choice by aria alone (the page menu's Theme does).
    if (b || group.matches(SEGS)) return b;
    return group.querySelector(':scope > button[aria-pressed="true"], :scope > button[aria-selected="true"]');
  }

  function pillOf(group, make) {
    var p = group.querySelector(PILLS);
    if (!p && make) {
      p = document.createElement('span');
      p.className = 'seg-slider';
      p.setAttribute('aria-hidden', 'true');
      group.insertBefore(p, group.firstChild);
    }
    return p;
  }

  function place(group) {
    if (!group) return;
    var pill = pillOf(group, false);
    if (!pill) return;
    var btn = selected(group);
    var g = group.getBoundingClientRect();
    var b = btn ? btn.getBoundingClientRect() : null;
    // No layout yet, or nothing selected (the loop view's free state): the
    // pill stands down rather than parking at a wrong position it would then
    // slide across the control from, and the CSS fallback paints any choice.
    if (!b || !b.width || !g.width) { group.removeAttribute('data-pill'); return; }
    var s = (group.offsetWidth && Math.abs(g.width - group.offsetWidth) > 1) ? g.width / group.offsetWidth : 1;
    var x = (b.left - g.left) / s - group.clientLeft - (parseFloat(getComputedStyle(pill).left) || 0);
    var w = b.width / s;
    x = Math.round(x * 100) / 100;
    w = Math.round(w * 100) / 100;
    var first = !group.hasAttribute('data-pill');
    if (first) pill.style.transition = 'none';
    if (pill.__x !== x) { pill.style.transform = 'translateX(' + x + 'px)'; pill.__x = x; }
    if (pill.__w !== w) { pill.style.width = w + 'px'; pill.__w = w; }
    if (first) {
      group.setAttribute('data-pill', '');   // the CSS fallback stands down
      void pill.offsetWidth;                 // ...at the position just written, not sliding to it
      pill.style.transition = '';
    }
  }

  function track(group) {
    if (!group || group.__segTracked) return;
    group.__segTracked = true;
    pillOf(group, true);

    var reflow = function () { place(group); };
    var ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(reflow) : null;
    var watch = function (el) { if (ro && el && el.tagName === 'BUTTON' && el.parentNode === group) ro.observe(el); };
    if (ro) {
      ro.observe(group);
      [].forEach.call(group.children, watch);
    }
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) [].forEach.call(muts[i].addedNodes || [], watch);
        reflow();
      }).observe(group, {
        subtree: true, childList: true, attributes: true,
        attributeFilter: ['class', 'hidden', 'aria-pressed', 'aria-selected']
      });
    }
    global.addEventListener('resize', reflow);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reflow);

    // Two frames, not one: the first lands before the browser has laid out a
    // sheet revealed in the same tick, which is exactly the case that failed.
    reflow();
    global.requestAnimationFrame(function () {
      reflow();
      global.requestAnimationFrame(reflow);
    });
  }

  function trackAll(root) {
    var groups = (root || document).querySelectorAll(TRACKS);
    for (var i = 0; i < groups.length; i++) track(groups[i]);
  }

  /* SELECTED MEANS SELECTED (v292; outside review of v291, SK-AUD-006).
   *
   * The draw drawer's segs carried aria-pressed and kept it in step by hand.
   * Every other seg — Speed, grid density, onion depth, Tips, Theme, Canvas,
   * export Size and Loops, the GIF background, the loop-view focus, pause and
   * speed on the Pad, the move scope on Flip — lit a class and said nothing,
   * so a screen reader heard "Playback speed, group. 6. 12. 24." and no word
   * on which. Eighteen groups, a dozen toggle sites, two editors. Fill / Fit /
   * Stretch joined them with the one pill: Flip never said which was chosen.
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
  function lit(b) { return b.classList.contains('on') || b.classList.contains('active'); }
  function syncPressed(group) {
    var btns = group.querySelectorAll('button');
    var stop = -1;
    for (var i = 0; i < btns.length; i++) {
      var want = lit(btns[i]) ? 'true' : 'false';
      if (btns[i].getAttribute('aria-pressed') !== want) btns[i].setAttribute('aria-pressed', want);
      if (stop < 0 && want === 'true' && !btns[i].disabled) stop = i;
    }
    // ONE TAB STOP PER SEG (v292; SK-AUD-007). Every option was its own Tab
    // stop, so Flip's Tune drawer alone cost a keyboard user a dozen presses
    // to cross. The selected option carries the stop (the first enabled one
    // when nothing is selected, as in a data-role="focus" group's free state)
    // and the arrows, below, move among the rest — the pattern a native
    // segmented control and a radio group both follow.
    if (stop < 0) for (var k = 0; k < btns.length; k++) if (!btns[k].disabled) { stop = k; break; }
    for (var j = 0; j < btns.length; j++) {
      var ti = j === stop ? '0' : '-1';
      if (btns[j].getAttribute('tabindex') !== ti) btns[j].setAttribute('tabindex', ti);
    }
  }
  /* Arrow keys move the selection: Left/Up to the previous enabled option,
   * Right/Down to the next, wrapping; Home and End to the ends. Moving IS
   * selecting — the option is clicked, so every seg's own handler runs and the
   * observer above moves the stop with it. */
  function onSegKey(e) {
    var b = e.target;
    if (!b || b.tagName !== 'BUTTON' || !b.closest) return;
    var g = b.closest(SEGS);
    if (!g) return;
    var all = [].slice.call(g.querySelectorAll('button'));
    var btns = [];
    for (var i = 0; i < all.length; i++) if (!all[i].disabled) btns.push(all[i]);
    var at = btns.indexOf(b);
    if (at < 0 || btns.length < 2) return;
    var to = -1;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') to = (at + 1) % btns.length;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') to = (at - 1 + btns.length) % btns.length;
    else if (e.key === 'Home') to = 0;
    else if (e.key === 'End') to = btns.length - 1;
    if (to < 0) return;
    e.preventDefault();
    btns[to].focus();
    btns[to].click();
  }
  function syncAll(root) {
    var gs = (root || document).querySelectorAll(SEGS);
    for (var i = 0; i < gs.length; i++) syncPressed(gs[i]);
  }
  function watchDocument() {
    if (global.__skriblSegPressed) return;
    global.__skriblSegPressed = true;
    syncAll();
    // EVERY TRACK GETS ITS PILL, not only the ones a surface remembered to
    // track: each editor used to track its groups one by one, and the ones
    // nobody listed -- Pad's Mirror, Pauses, Preview speed and grid density,
    // Flip's Mirror and smear weight -- showed their selection by ink alone
    // (owner, on the phone: "not bright enough to tell what's selected").
    // Tracks built later by script are picked up as they arrive, below.
    trackAll();
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
            if (n.matches && n.matches(TRACKS)) track(n);
            if (n.querySelectorAll) trackAll(n);
          }
        }
      }
    }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchDocument);
  else watchDocument();
  document.addEventListener('keydown', onSegKey);

  // attach() is track() under the name the script-built groups were given:
  // the pill it used to make is made by track() now, once.
  global.SkriblSegSlider = { track: track, trackAll: trackAll, place: place, attach: track,
                             syncPressed: syncPressed, syncAll: syncAll };
})(window);
