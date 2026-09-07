/* Making Web Audio audible on an iPhone whose ringer switch is off.
 *
 *   SkriblAudioSession.claim();    // from a gesture that ASKS for sound
 *   SkriblAudioSession.release();  // when nothing wants sound any more
 *
 * THE BUG THIS EXISTS FOR, in one line: on iOS, Web Audio is routed into an
 * "ambient" audio session that the hardware ringer switch silences, while an
 * <audio> element is not. So on a phone set to silent, Test Seam (a plain
 * <audio>) plays and Preview Loop (Web Audio) does not — and neither does a
 * posted Skribl's music in a feed, because inlineplayer.js is Web Audio too.
 * The owner found it on their own phone; it is not reproducible on desktop.
 *
 * WHY EVERY EXISTING GUARD MISSED IT. app.js has an elaborate hand-off for a
 * context that never unlocks — it refuses to build a source while the state is
 * 'suspended' and falls back to native <audio>. In silent mode the context
 * reaches 'running' perfectly well. It is simply inaudible. Every guard passes,
 * the native fallback is deliberately suppressed, and the result is confident
 * silence. app.js's own warning — "A source object existing is NOT the same as
 * audible playback" — turns out to apply one level further out than where it
 * was written.
 *
 * WHAT THIS DOES. Holds a silent looping <audio> element playing. That moves
 * the session from "ambient" to "playback", after which Web Audio is audible
 * regardless of the switch. It is the same trick every audio library on the web
 * ends up implementing.
 *
 * WHY IT IS CLAIMED ON A GESTURE AND NOT AT LOAD. A held session makes iOS show
 * Skribl as playing media in Control Center and on the lock screen. That is a
 * fair price for "I tapped unmute and want to hear it" and an unreasonable one
 * for "I opened a page". So claim() belongs on the tap that asks for sound, and
 * release() on the one that stops wanting it.
 *
 * OVERRIDING THE SWITCH IS A DELIBERATE PRODUCT CHOICE, and it is defensible
 * here only because sound is never automatic: the in-post player ships muted
 * and needs an explicit tap, and Preview Loop is a button somebody pressed.
 * Do not call claim() from anything that happens on its own.
 *
 * iOS ONLY. Everywhere else Web Audio already ignores the switch (there is no
 * switch), so the Control Center side effect would be pure cost.
 *
 * CONFIRMED ON A PHONE, 5 Sep 2026: the owner reported music audible in silent
 * mode on the same iPhone that found the bug. That is the only evidence there
 * can be for the OUTCOME.
 *
 * STILL NOT VERIFIABLE IN THIS HARNESS, and the confirmation does not change
 * that. Chromium on Linux has no ringer switch and no iOS audio session;
 * verify_audiosession.py pins the MECHANISM — one element, looping, playing,
 * idempotent, released, claimed and released on the right edges — and cannot
 * pin the OUTCOME. What it protects is the confirmation above: unwire this
 * module and the phone's answer silently goes stale. app.js already says the
 * same of its own iOS branches: "Desktop never showed it … including in the
 * harness." The phone is the test.
 *
 * HOLD IT ONLY WHILE SOUND IS ACTUALLY WANTED. A held session is a Control
 * Center and lock-screen entry the viewer cannot clear, so every claim needs a
 * release on the edge that stops wanting sound — Pause, the last frame, Mute.
 * The two editors' Preview Loop buttons pair them; the /s player did not, and
 * held the session from the first Play until the tab closed.
 */
(function (global) {
  'use strict';

  var el = null;
  var claimed = false;

  /* iPadOS reports itself as a Mac, so the touch count is what separates an
     iPad from a desktop Safari that has none. */
  function isIOS() {
    var nav = global.navigator;
    if (!nav) return false;
    var plat = nav.platform || '';
    return /iP(hone|od|ad)/.test(plat) ||
           (/Mac/.test(plat) && (nav.maxTouchPoints || 0) > 1);
  }

  /* A fifth of a second of silence, 8-bit mono at 8 kHz, as a data URI.
     BUILT BYTE BY BYTE FIRST, and measured: the builder cost 1,650 B served
     against this constant's ~450, and the player's JS ratchet is not a place to
     spend 1,200 B on legibility. Silence is 0x80 in unsigned 8-bit PCM; the
     clip loops, so its length only has to be long enough to hold the session. */
  var SILENT = 'data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YaAAAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA';

  var API = {
    /* Call from the gesture. Idempotent: a second tap must not stack a second
       element, which would leave one playing forever after release().

       THE FLAG FOLLOWS THE ELEMENT, NOT THE INTENTION. play() settles
       ASYNCHRONOUSLY, so a synchronous `claimed = true` records that a claim
       was ATTEMPTED and says nothing about whether the session was granted —
       active() then answers a different question from the one it is named
       for, and a caller that trusts it never retries. Two rules fix that
       without making any of this async:

         - a rejected play() clears the flag, so the next gesture retries;
         - a claim on an element that exists but is PAUSED re-plays it rather
           than returning a stale true.

       The optimistic set stays: it is what makes a double tap a no-op, and
       the reject path is the only thing that can contradict it. */
    claim: function () {
      if (!isIOS()) return false;
      if (claimed && el && !el.paused) return true;
      if (!el) {
        el = global.document.createElement('audio');
        el.loop = true;
        el.setAttribute('playsinline', '');
        el.setAttribute('aria-hidden', 'true');
        el.preload = 'auto';
        el.src = SILENT;
        el.style.display = 'none';
        global.document.body.appendChild(el);
      }
      claimed = true;
      try {
        var p = el.play();
        if (p && p.catch) p.catch(function () { claimed = false; });
      } catch (e) { claimed = false; }   /* no gesture, or the element is gone */
      return claimed;
    },

    /* The session is only worth holding while something wants sound. */
    release: function () {
      if (!claimed) return false;
      claimed = false;
      if (el) { try { el.pause(); } catch (e) {} }
      return true;
    },

    active: function () { return claimed; },
    /* For the suite: the element, or null before the first claim. */
    _element: function () { return el; },
    _isIOS: isIOS
  };

  global.SkriblAudioSession = API;
})(window);
