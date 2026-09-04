/* /s/<id>/card.png: WHERE THE DRAWING SITS INSIDE IT.
 *
 * The share card is a 1200x630 Open Graph canvas with the drawing CONTAINED
 * inside it — a 54 px margin, an 84 px strip at the bottom for the brand mark —
 * composited client-side at post time and sent as payload.thumbnail. It is what
 * a shared link unfurls with, and (cropped back to the drawing) what an idle
 * post shows in a feed and what a tile shows on the profile.
 *
 * IT LIVED IN editor_post.js, WHICH IS PAD-ONLY, AND THAT WAS A REAL DEFECT.
 * flip.js has its own post path and never built one — grep it before this
 * change and there is no payload.thumbnail anywhere in that file — so EVERY
 * Flip post fell back to the static branded og-card: on its /s/<id> unfurl, as
 * the in-post player's idle poster, and as its tile in the profile's Skribls
 * tab. Three surfaces showing an advert instead of the drawing. Same shape as
 * the bug verify_flipmeta.py records ("a whole control surface that was never
 * built on one of the two editors"), and invisible for the same reason: the
 * author who posted it never looks at their own unfurl.
 *
 * So the builder is shared — but it is NOT IN THIS FILE. It is in
 * lib/postedcard.js, which only the two editors load, for the same reason
 * lib/postedaudio.js is separate: THE READER OF THIS MODULE IS NOT THE WRITER.
 * A host embedding the in-post player needs band() to crop a poster and nothing
 * else; it never composites a card, because it never posts. Putting the
 * composite here put 2 KB of canvas work on every feed page in the world and
 * blew verify_inline.py's embed ratchet on the first run — which is exactly the
 * job that ratchet has.
 *
 * What stays here is the geometry, because BOTH sides need it: postedcard.js to
 * place the drawing, inlineplayer.css to crop it back out.
 *
 * The in-post player made a second consumer. A feed post's idle state is that
 * card, and a card is the wrong thing to put in a feed — it is a drawing inside
 * a bordered box under a "Skribl Pad" wordmark, which is right for a link
 * unfurl and reads as an advert twenty times down a timeline. So the in-post
 * player CROPS the card back to just the drawing's band, and to do that it has
 * to know exactly where editor_post.js put it.
 *
 * Two files computing the same rectangle from four numbers each is the shape
 * this project has been bitten by repeatedly (see lib/holdtiming.js's header for
 * the version of it that shipped a real bug). So the numbers live here and both
 * read them. If the card's layout changes, the crop follows; if someone changes
 * only one, verify_inline.py fails.
 *
 * THE BAND IS VERTICAL ONLY, and that is a limitation rather than a choice. The
 * drawing is contained, so its HEIGHT is fixed for any drawing not wider than
 * areaW/areaH (2.22:1) — every canvas preset qualifies — and lands at the same
 * y for all of them. Its WIDTH depends on the drawing's own aspect, which the
 * feed listing does not carry: canvasSize lives inside payload_json, and
 * GET /api/skribls DEFERS that column on purpose (a feed of payloads is
 * hundreds of megabytes). So the crop takes the full width and the drawing sits
 * centred in it with the card's own dark ground either side, which reads as
 * letterboxing. A host that knows its posts' shape can do better; doing it here
 * needs the canvas size as a real column, not a JSON field.
 */
(function (global) {
  'use strict';

  var CARD_W = 1200, CARD_H = 630;   // the Open Graph aspect
  var PAD = 54;                      // margin around the contained drawing
  var FOOTER = 84;                   // strip reserved for the brand mark

  var AREA_W = CARD_W - PAD * 2;
  var AREA_H = CARD_H - PAD - FOOTER;

  /* The drawing's rectangle inside the card, for a drawing of w x h. Mirrors
   * editor_post.js buildShareCardDataURL() exactly, including its rounding. */
  function drawingRect(w, h) {
    if (!(w > 0 && h > 0)) return { x: PAD, y: PAD, w: AREA_W, h: AREA_H };
    var scale = Math.min(AREA_W / w, AREA_H / h);
    var dw = Math.round(w * scale), dh = Math.round(h * scale);
    return { x: Math.round((CARD_W - dw) / 2),
             y: Math.round((CARD_H - FOOTER - dh) / 2),
             w: dw, h: dh };
  }

  /* The full-width band the drawing occupies, for every drawing that fits the
   * area by height — which is every canvas preset. Expressed as fractions of
   * the card so a stylesheet can use them directly. */
  function band() {
    var y = (CARD_H - FOOTER - AREA_H) / 2;
    return { top: y / CARD_H, height: AREA_H / CARD_H,
             /* What an <img> stretched to the box's width must be scaled to,
              * and shifted by, for that band to fill the box. */
             scale: CARD_H / AREA_H, offset: y / AREA_H,
             aspect: CARD_W / AREA_H };
  }

  var api = { CARD_W: CARD_W, CARD_H: CARD_H, PAD: PAD, FOOTER: FOOTER,
              AREA_W: AREA_W, AREA_H: AREA_H,
              drawingRect: drawingRect, band: band };
  if (typeof window !== 'undefined') window.SkriblShareCard = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
