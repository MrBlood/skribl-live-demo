/* A FACE'S GUIDE: in the Pad's face mode (?compose=1&face=1), a photo is a
 * guide to trace, and only the lines are kept (after v330, the owner's
 * "all yes, build A" on the Trace a photo mock, Nov 11).
 *
 * WHY. A face is a skribl the person draws of themselves, and it draws
 * itself (lib/face.js). "I can't draw myself" is the reason someone would
 * want a photo instead, and a photo as a face would sit still, be the
 * riskiest thing a site for people of 13 and over can hold, and need
 * watching. So the photo helps the hand and goes no further: it shows
 * faintly under the canvas while the person traces it, and the face they
 * keep is their own lines. The replay is their performance.
 *
 * WHAT THIS DOES, the Pad's own photo drawer doing the rest:
 *   take(file)   a photo the host's page picked (lib/composehost.js guide(),
 *                editor_compose.js's skribl:compose:guide) goes into the
 *                drawer exactly as one picked there does: the same input,
 *                the same checks, the same row.
 *   THE START    each new photo starts at GUIDE opacity, so the lines read
 *                over it from the first stroke; the drawer's Opacity, Blur
 *                and Fit stay the person's to set exactly.
 *   THE WORDS    while there is a photo, the empty canvas says the guide's
 *                words instead of the face's (the template's: the hint's
 *                data-guide-words and data-guide-sub), and the drawer's row
 *                says what the photo is for (#photoPanel's data-guide, which
 *                lib/pendingcards.js reads). The words are the template's;
 *                this file says nothing of its own.
 * WHAT IS KEPT is not decided here: editor_post.js leaves the photo out of
 * a face's drawing and its card (buildPostPayload, buildPreviewCanvas), and
 * the site that keeps the face drops a photo sent anyway.
 *
 * Face mode only: the editor's template loads this file only there, and
 * verify_player_isolation keeps it (an editor_*.js) off the player.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  if (!global.SKRIBL_FACE) return;

  /* The guide's opacity to start, in percent: the mock measured the empty
     canvas's words over a photo at this strength at 5.4:1 or better. */
  var GUIDE = 40;

  /* A photo from the host's page, into the drawer's own input: the change
     handler (editor_photo.js) checks it is a picture, reads it, shows it and
     writes the row, exactly as for a photo picked there. */
  function take(file) {
    var input = doc.getElementById('photoInput');
    if (!input || !file) return false;
    try {
      var f = (typeof File === 'function' && file instanceof File)
        ? file : new File([file], 'photo', { type: file.type || 'image/jpeg' });
      var dt = new DataTransfer();
      dt.items.add(f);
      input.files = dt.files;
    } catch (e) {
      return false;
    }
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  /* THE EMPTY CANVAS'S WORDS. The face's own words are put back as they
     were (the hand-drawn ones included) when the photo goes. */
  var hint = doc.getElementById('canvasEmptyHint');
  var kept = null;
  function words(on) {
    if (!hint || !hint.hasAttribute('data-guide-words')) return;
    if (on && !kept) {
      kept = { html: hint.innerHTML, hand: hint.classList.contains('is-hand') };
      hint.classList.remove('is-hand');
      hint.classList.add('is-guide');
      hint.textContent = '';
      /* One backing for both lines (styles.css, .face-guide-words): over a
         photo, words in the canvas's own see-through ink are as readable as
         the photo under them allows, which over dark hair or darker skin is
         not enough. */
      var box = doc.createElement('span');
      box.className = 'face-guide-words';
      var a = doc.createElement('span');
      a.textContent = hint.getAttribute('data-guide-words');
      var b = doc.createElement('span');
      b.className = 'canvas-empty-sub';
      b.textContent = hint.getAttribute('data-guide-sub') || '';
      box.appendChild(a);
      box.appendChild(b);
      hint.appendChild(box);
    } else if (!on && kept) {
      hint.innerHTML = kept.html;
      hint.classList.remove('is-guide');
      if (kept.hand) hint.classList.add('is-hand');
      kept = null;
    }
  }

  /* THE START: through the slider's own input event, so the picture, the
     number beside the slider and its fill all agree. */
  function start() {
    var s = doc.getElementById('photoOpacity');
    if (!s) return;
    s.value = String(GUIDE);
    s.dispatchEvent(new Event('input', { bubbles: true }));
  }

  /* A photo comes and goes with the row's .loaded (editor_photo.js sets it
     when one is added, by whatever way, and clears it on remove). */
  var zone = doc.getElementById('photoUploadBtn');
  if (zone) {
    var was = zone.classList.contains('loaded');
    new MutationObserver(function () {
      var now = zone.classList.contains('loaded');
      if (now === was) return;
      was = now;
      if (now) start();
      words(now);
    }).observe(zone, { attributes: true, attributeFilter: ['class'] });
    if (was) words(true);
  }

  global.SkriblFaceGuide = { take: take, GUIDE: GUIDE };
})(window);
