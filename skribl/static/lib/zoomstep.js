/* The loop-detail magnification stepper — the ladder, the chrome, and the rule
 * for stepping it, in one place because Pad and Flip both draw this control.
 *
 * WHY IT IS HERE AND NOT IN looptrim.js. looptrim.js is loaded by the PLAYER
 * as well as the two editors; the player has no loop-detail panel and would be
 * paying for this markup to sit unused in its bundle.
 *
 * WHY IT IS SHARED AT ALL. The control it replaces was a four-cell segmented
 * group built from a literal HTML string in flip.js and a second literal HTML
 * string in editor_music.js. Changing it meant editing both, and nothing failed
 * if only one was edited — the surfaces would simply have offered different
 * zoom levels, which is exactly the kind of drift the owner has had to report
 * by eye before.
 *
 * THE LADDER, and why the old ceiling was a defect rather than a limit.
 *
 *     halfSpan = (loopDuration / 2 + contextSeconds) / zoomMag
 *
 * has nothing structural stopping it, and the finest nudge step the panel
 * offers is 0.01s. On a 330px waveform at 8x that step moves the marker 0.94px
 * on a 20s loop and 0.39px on a 60s one: the panel offered an adjustment you
 * could not see it make. 32x makes that same step 11.7px.
 *
 * Six rungs are affordable because a stepper costs the same whatever it counts
 * to; four LABELLED cells cost 179px and put the row onto two lines on a phone,
 * which is how a layout constraint had quietly become a functional one.
 *
 * THE GLYPHS ARE THE BUTTONS. A leading magnifier beside plain +/- signs was
 * built and measured: 118px, which wrapped the bar again at 390 and gave back
 * the whole saving. Putting the magnifier ON the two step buttons identifies
 * the control and steps it with the same pixels.
 */
(function () {
  'use strict';

  var MAGS = [1, 2, 4, 8, 16, 32];

  var GLASS = '<circle cx="11" cy="11" r="8" />'
            + '<line x1="21" x2="16.65" y1="21" y2="16.65" />';
  var MINUS = '<line x1="8" x2="14" y1="11" y2="11" />';
  var PLUS  = '<line x1="11" x2="11" y1="8" y2="14" />' + MINUS;

  /* aria-hidden: each button already carries its own aria-label, so the glyph
   * is decoration to a screen reader and announcing it would double the name. */
  function glyph(bars) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"'
      + ' stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
      + ' aria-hidden="true">' + GLASS + bars + '</svg>';
  }

  /* markup() -> the stepper, ready to concatenate into the zoom bar.
   * aria-live on the readout so stepping is announced without moving focus. */
  function markup() {
    return '<span class="mag-step" role="group" aria-label="Zoom level">'
      + '<button type="button" id="zoomMagOut" class="mag-step-btn"'
      + ' aria-label="Zoom out">' + glyph(MINUS) + '</button>'
      + '<span class="mag-step-val" id="zoomMagVal" aria-live="polite">'
      + MAGS[0] + '×</span>'
      + '<button type="button" id="zoomMagIn" class="mag-step-btn"'
      + ' aria-label="Zoom in">' + glyph(PLUS) + '</button>'
      + '</span>';
  }

  /* A magnification that is not on the ladder reads as the bottom rung rather
   * than throwing: zoomMag is a plain global on both surfaces and a stale or
   * restored value must not leave the stepper unable to move. */
  function indexOf(mag) {
    var i = MAGS.indexOf(mag);
    return i === -1 ? 0 : i;
  }

  /* next(mag, dir) -> the neighbouring rung, or the same value at the ends.
   * Returning the input unchanged at the ends is what lets a caller skip the
   * redraw when nothing moved. */
  function next(mag, dir) {
    var i = indexOf(mag) + (dir < 0 ? -1 : 1);
    return MAGS[Math.max(0, Math.min(MAGS.length - 1, i))];
  }

  /* sync(mag) — the readout and the two end-stops. Call it after every step
   * AND after every reset of zoomMag: loading new audio puts the level back to
   * 1x without going through next(), and a readout that still said 32x would
   * be describing a window that no longer exists. */
  function sync(mag) {
    var out = document.getElementById('zoomMagVal');
    var less = document.getElementById('zoomMagOut');
    var more = document.getElementById('zoomMagIn');
    if (!out || !less || !more) return;
    var i = indexOf(mag);
    out.textContent = MAGS[i] + '×';
    less.disabled = (i === 0);
    more.disabled = (i === MAGS.length - 1);
  }

  window.SkriblZoomStep = {
    MAGS: MAGS.slice(),
    markup: markup,
    next: next,
    sync: sync,
    indexOf: indexOf
  };
}());
