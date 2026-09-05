/* Compositing /s/<id>/card.png — the post-time half of lib/sharecard.js.
 *
 * The share card is a 1200x630 Open Graph canvas with the drawing contained
 * inside it, a margin around it and a strip at the bottom for the brand mark.
 * It is what a shared link unfurls with, and (cropped back to the drawing) what
 * an idle post shows in a feed and what a tile shows on the profile.
 *
 * EDITORS ONLY, and that is the whole reason this is not in lib/sharecard.js.
 * Same rule as lib/postedaudio.js: the player never posts, and neither does a
 * host's feed. A page embedding the in-post player needs sharecard.js's band()
 * to crop a poster and nothing else — it has no drawing to composite. Merging
 * the two put this canvas work on every feed page and blew verify_inline.py's
 * embed ratchet, which is what that ratchet is for.
 *
 * IT LIVED IN editor_post.js, WHICH IS PAD-ONLY, AND THAT WAS A REAL DEFECT.
 * flip.js has its own post path and never built a card — grep it before this
 * change and there is no payload.thumbnail anywhere in that file — so EVERY
 * Flip post fell back to the static branded og-card: on its /s/<id> unfurl, as
 * the in-post player's idle poster, and as its tile in the profile's Skribls
 * tab. Three surfaces showing an advert instead of the drawing. Same shape as
 * the bug verify_flipmeta.py records ("a whole control surface that was never
 * built on one of the two editors"), and invisible for the same reason: the
 * author who posted it never looks at their own unfurl.
 *
 * Each editor supplies its own FLAT CANVAS — the Pad flattens its live canvas
 * over the photo, Flip composites a page through drawFrameTo() — because
 * flattening is the part that genuinely differs between a recording and an
 * animation. Everything after that is one implementation.
 */
(function (global) {
  'use strict';

  function geom() {
    /* Inline fallback, as every consumer of lib/ keeps: a surface that somehow
     * loads without sharecard.js composites exactly as it always did. */
    var SC = global.SkriblShareCard;
    return SC || { CARD_W: 1200, CARD_H: 630, FOOTER: 84,
                   drawingRect: function (w, h) {
                     var aw = 1092, ah = 492;
                     var k = Math.min(aw / w, ah / h);
                     var dw = Math.round(w * k), dh = Math.round(h * k);
                     return { x: Math.round((1200 - dw) / 2),
                              y: Math.round((630 - 84 - dh) / 2), w: dw, h: dh };
                   } };
  }

  function roundRect(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  /* Compose the card. `flat` is an already-flattened canvas of the drawing —
   * ground, photo and strokes, no chrome. Returns a data URL, or null if
   * anything throws: a missing card falls back to the branded image
   * server-side, and a post must never fail over one. */
  function build(flat) {
    try {
      if (typeof document === 'undefined') return null;
      var G = geom();
      var CARD_W = G.CARD_W, CARD_H = G.CARD_H, FOOTER = G.FOOTER;
      var card = document.createElement('canvas');
      card.width = CARD_W; card.height = CARD_H;
      var c = card.getContext('2d');

      /* Ground + soft accent wash (echoes the static og-card). */
      c.fillStyle = '#0b0d12';
      c.fillRect(0, 0, CARD_W, CARD_H);
      var wash = c.createRadialGradient(CARD_W * 0.5, CARD_H * 0.28, 40,
                                        CARD_W * 0.5, CARD_H * 0.28, CARD_W * 0.7);
      wash.addColorStop(0, 'rgba(124,92,255,0.16)');
      wash.addColorStop(1, 'rgba(124,92,255,0)');
      c.fillStyle = wash;
      c.fillRect(0, 0, CARD_W, CARD_H);

      if (flat && flat.width && flat.height) {
        var r = G.drawingRect(flat.width, flat.height);
        c.save();
        roundRect(c, r.x, r.y, r.w, r.h, 18);
        c.clip();
        c.drawImage(flat, r.x, r.y, r.w, r.h);   /* flat is opaque: bg baked in */
        c.restore();
        c.lineWidth = 2;
        c.strokeStyle = 'rgba(124,92,255,0.45)';
        roundRect(c, r.x, r.y, r.w, r.h, 18);
        c.stroke();
      }

      /* Brand mark: 6-point star + wordmark, centred in the footer strip. */
      var cy = CARD_H - FOOTER / 2 + 6;
      var label = 'Skribl Pad';
      c.font = '700 30px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
      c.textBaseline = 'middle';
      var tw = c.measureText(label).width;
      var starR = 13, gap = 14;
      var x = (CARD_W - (starR * 2 + gap + tw)) / 2;
      c.save();
      c.translate(x + starR, cy);
      c.beginPath();
      for (var i = 0; i < 12; i++) {
        var ang = (Math.PI / 6) * i - Math.PI / 2;
        var rr = (i % 2 === 0) ? starR : starR * 0.42;
        var px = Math.cos(ang) * rr, py = Math.sin(ang) * rr;
        if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
      }
      c.closePath();
      var sg = c.createLinearGradient(-starR, -starR, starR, starR);
      sg.addColorStop(0, '#7c5cff');
      sg.addColorStop(1, '#5b8cff');
      c.fillStyle = sg;
      c.fill();
      c.restore();
      c.fillStyle = 'rgba(246,247,249,0.94)';
      c.textAlign = 'left';
      c.fillText(label, x + starR * 2 + gap, cy);

      /* ENCODE BOTH AND KEEP THE SMALLER, rather than deciding by content.
       *
       * This used to branch on whether the drawing had a photo: JPEG q0.92 for
       * photo cards, PNG for line art, on the stated grounds that "PNG is both
       * SMALLER and crisp" for lines. MEASURED ON THIS CARD, that is wrong by a
       * factor of sixteen — a plain spiral encodes to 451,824 B as PNG and
       * 28,062 B as JPEG q0.92.
       *
       * The reason is the accent wash above. Chromium DITHERS a canvas gradient,
       * which puts per-pixel noise across all 1,200x630 that PNG cannot
       * compress; the rule was presumably measured before the wash existed and
       * was never re-checked. It went unnoticed because a 450 KB card is not
       * wrong, only expensive — until the in-post player made this image the
       * IDLE COST OF EVERY POST IN A FEED, at which point a screenful was
       * several megabytes to show twelve thumbnails.
       *
       * So: no rule. Encode both, return the smaller, and the question cannot
       * be got wrong again by anyone reasoning about it. q0.92 rather than
       * lower because the strokes are sharp light-on-dark edges and that is
       * where JPEG rings; the /s/<id>/card.png route serves either format, and
       * has since the photo cards. Costs one extra encode at post time.
       */
      var png = card.toDataURL('image/png');
      var jpeg = card.toDataURL('image/jpeg', 0.92);
      return (jpeg && jpeg.length < png.length) ? jpeg : png;
    } catch (e) {
      return null;
    }
  }


  var api = { build: build };
  if (typeof window !== 'undefined') window.SkriblPostedCard = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
