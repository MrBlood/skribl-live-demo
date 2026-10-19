/* THE IN-POST PLAYER. What a Skribl looks like inside somebody else's feed.
 *
 * WHY IT IS NOT THE PLAYER AT /s/<id>
 * -----------------------------------
 * That one is a PAGE: app.js plus eight shared modules, a full app shell, a
 * transport with scrub and loop and speed. Right for a shared link, where the
 * Skribl is the whole reason the tab is open; wrong for a feed, where twenty
 * posts are on screen and the one that is a Skribl has to behave like an image
 * that happens to move.
 *
 * So this is a SECOND IMPLEMENTATION of playback, and the editor and the
 * player disagreeing is uniquely expensive because nothing an author can see
 * reveals it. Three things keep them together, in descending order of strength:
 *
 *   1. THE RULES COME OUT OF lib/. Per-page holds through lib/holdtiming.js,
 *      the default canvas size through lib/canvassizes.js. Neither is retyped.
 *   2. WHAT IS RETYPED IS RETYPED VERBATIM AND SAYS SO. The gap cap and the
 *      timeline build are app.js's buildPlaybackTimeline(); the two drawing
 *      primitives are its drawDot/drawLine. Each carries a pointer to the
 *      original. They were deliberately NOT extracted: a lib module adds a
 *      fetched file to the player's critical path, which is the wrong price
 *      for thirty shared lines.
 *   3. harness/verify_inline.py ASSERTS THE ANSWERS MATCH. It posts one real
 *      drawing, plays it in the sealed player and here, and compares reported
 *      durations and rendered pixels at matched offsets. What is asserted is
 *      not shared code but that the two cannot disagree about the ANSWER.
 *
 * WHY THE PRODUCT REASONING IS HERE AND NOT IN inlineplayer.css
 * ------------------------------------------------------------
 * jsstrip.py removes these comments from the response; nothing does that for
 * CSS, so every word of that stylesheet is downloaded by every host on every
 * page that embeds a Skribl. The line is AUDIENCE, not length: a host reads
 * the stylesheet before overriding something, so tokens, geometry numbers and
 * defensive declarations stay there. Why the component behaves as it does
 * belongs here.
 *
 * WHAT MOVED HERE FROM THE STYLESHEET'S HEADER (v315), to pay for the title
 * line under the player without raising the embed ratchet: inlineplayer.css is
 * NOT styles.css and NOT player.css, and it is outside harness/tools/
 * cssgraph.py's graph entirely (that tool derives player.css from
 * styles.css). Its two poster literals, 128.0488% and -5.4878%, are 630/492
 * and 27/492 from lib/sharecard.js band(); they are the no-script fallback,
 * because this file reframes the poster onto the drawing itself wherever the
 * page knows the drawing's size, and verify_inline.py asserts both against
 * the real module.
 *
 * WHAT IT PLAYS
 * -------------
 * Pad replay documents, Flip documents (holds through lib/holdtiming.js), the
 * background colour, a photo or base-snapshot underlay, the posted audio loop,
 * and the wet/dry stroke compositor (makeCompositor below, app.js's
 * makeStrokeCompositor in miniature) so a stroke below 100% opacity is
 * composited once rather than stamped.
 *
 * THE PRODUCT RULES
 * -----------------
 * A POST GREW A WAY TO WATCH IT (v322, the owner: "bring Pad's watching
 * experience into the post ... it's critical"; "all yes"). This said, until
 * then, that a post gets two controls and no transport -- "a post that grows a
 * transport stops being a post". The owner decided the opposite, for the
 * reason Pad exists: the drawing is a performance, and watching it is the
 * point. So under the drawing, never on it, sits the Pad's own line --
 * lib/replayline.js, the module the Pad and /s/<id> use, so a post cannot
 * offer other speeds or say them differently:
 *
 *   THE SCRUBBER, in the drawing's shape (a Flip: one segment per page), and
 *   "Drawn in 15 sec · watching at 1×" (a Flip: "12 pages · watching at 1×"),
 *   the speed in it the button that opens the speeds.
 *   ALWAYS THERE, at rest too, so a post is the same height before and after
 *   the first tap and the feed under the thumb never jumps. The numbers and
 *   the shape at rest are the post's `line` (validation._payload_line), read
 *   from the listing, because NOTHING FETCHES UNTIL SOMEBODY ASKS (below).
 *   MUTE AND LOOP MOVED INTO IT, off the drawing, with the time badge and the
 *   progress hairline gone: the line says both. A tap on the drawing still
 *   pauses and carries on, with the play button showing while it is paused.
 *
 * The box takes the drawing's shape there too (the macro's canvas size), so a
 * 4:3 drawing has no bars beside it, and a tall drawing is narrowed to fit a
 * screen (70vh, at most 640px tall) rather than given bars. A surface with its
 * own transport leaves the line out (line=false: the gallery's cards) and
 * keeps the old 16:9 box with its mute and loop on it, as a draft does.
 *
 * THE STYLESHEET'S SIDE OF IT, said here with the rest of the reasoning, so
 * the sheet stays values a host can read before overriding one. The play
 * button is white with a 2px purple edge and no shadow -- the owner's v4,
 * the one that read on paper, on a dark canvas and on purple ink without
 * darkening anything -- in fixed colours, because it sits on the drawing,
 * not on the host's page. The line takes the host's text colour; its quiet
 * words are quiet by OPACITY (and take no taps: an opacity layer sits over
 * the speed's finger area otherwise; the whole words row takes none, so the
 * scrubber's and loop's reach is theirs where it meets the row, and only the
 * speed and its chips opt back in), never by a colour mixed from
 * currentColor, because Chrome left such a mix stale when a host switched
 * theme after load (the light page showed the dark page's words, white on
 * white). For the same reason the speed and lit loop take the page's text on
 * an accent tint rather than an accent mixed toward it: the tint carries the
 * colour, and the words read on any page, whichever theme it has switched
 * to. Every control in the line is 44px to a finger by an invisible
 * ::before/::after, and its speeds open upward over the scrubber, closing on
 * a pick.
 *
 * LOOP IS ON BY DEFAULT, so the lit state is the RESTING state and the button
 * dims when switched OFF -- the opposite of mute, whose resting state is muted.
 * Each reads as "what is currently true", not "what this button does".
 *
 * ONE AT A TIME. Starting any Skribl settles every other one on the page. A
 * feed that can play two loops at once is a feed nobody scrolls twice.
 *
 * SOUND OFF BY DEFAULT, AND THE CHOICE IS THE VIEWER'S. Unmuting one post
 * unmutes all of them for the session -- sessionStorage, not localStorage: a
 * preference set in a feed should not follow someone into next week. Repeating
 * is the viewer's too but PER POST: sound is environmental, repeating is a
 * property of the drawing in front of you.
 *
 * WHEN A NON-LOOPING REPLAY ENDS, THE MUSIC ENDS WITH IT. The end of the
 * replay goes through pause(), which stops the audio in the same call, so a
 * finished drawing can never be left with a loop still playing under it.
 *
 * NOTHING FETCHES UNTIL SOMEBODY ASKS. The idle state is /s/<id>/card.png, one
 * cached image; GET /api/skribls/<id> is issued on the first play and never
 * again for that post. Load-bearing, not an optimisation: that endpoint returns
 * the WHOLE payload, base64 audio included, and a feed that prefetched twenty
 * of those would move tens of megabytes to render thumbnails.
 *
 * IT FOLLOWS THE HOST'S THEME, WITH ITS OWN VALUES AS FALLBACKS.
 * inlineplayer.css reads a custom property for every colour and supplies a
 * literal after the comma: `var(--bg-elev, #12151c)`. A host that defines those
 * tokens gets a player that changes with it, live, because custom properties
 * cascade from :root. The token NAMES are the ones a feed already has --
 * --bg-elev, --border, --radius, --accent, --accent-2 -- rather than
 * skribl-prefixed ones, because a prefix would mean mapping their palette onto
 * ours to get any benefit, and then nobody would. The failure this avoids is a
 * dark-only player in a light feed: a black rectangle among white cards reads
 * as broken rather than as styled.
 *
 * THE DRAWING ITSELF DOES NOT FOLLOW THE THEME. Its ground is the one the
 * author drew on and it is painted from the payload -- the artwork is content,
 * not chrome, and recolouring it would be editing somebody's picture.
 *
 * THE IDLE POSTER
 * ---------------
 * A tile shows /s/<id>/poster: the post's own share card, or a blank canvas
 * when it has none -- never the branded card, which cropped to a drawing's band
 * reads as a fragment of an advert. The card is 1200x630 and CONTAINS the
 * drawing, so there are two ways to show one in a 16:9 box and this player does
 * both:
 *
 *   NO SCRIPT, OR NO CANVAS SIZE -- the band crop, which is the stylesheet's
 *   two literals: the card scaled to 128.0488% of box height (630/492) and
 *   pulled up 5.4878% (27/492), putting the wordmark and padding outside the
 *   box. Vertically that is exact, because for any canvas not wider than
 *   2.22:1 -- every preset -- the drawing's height and y are identical in every
 *   card. Horizontally it cannot be: the drawing's width inside the card
 *   depends on its own aspect and nothing here knows it (canvasSize lives
 *   inside payload_json, and GET /api/skribls DEFERS that column deliberately).
 *   But the drawing is CENTRED, so a symmetric side crop removes only ground as
 *   long as the box is at least as wide as the widest canvas a drawing can
 *   have. That is 16:9 (lib/canvassizes.js), so the box is 16:9, and
 *   verify_inline.py asserts the box is never narrower than the widest preset
 *   -- adding a wider canvas size fails there rather than quietly cutting the
 *   edges off every wide drawing in the feed.
 *
 *   WITH THE DRAWING'S SIZE -- fitPoster(), below, which frames the card's
 *   drawingRect() exactly where the canvas will land and clips the rest away.
 *   The remaining ground was still the CARD's ground, with its plate border
 *   around the picture: a frame inside a frame on every tile. Idle and playing
 *   are one composition now.
 *
 * The crop is LITERALS in inlineplayer.css rather than a call into
 * lib/sharecard.js, so that module is not shipped to every feed page;
 * verify_inline.py injects it and compares band() and drawingRect() against
 * these literals, so the arithmetic is still held to the editors'.
 *
 * THE GENERIC FALLBACK CARD IS CROPPED THE SAME WAY, deliberately. A post with
 * no stored thumbnail has /s/<id>/card.png REDIRECT to the static branded
 * og-card, and telling the two apart in the browser costs a request: the
 * redirect is invisible to an <img> (currentSrc reports the URL requested, not
 * the one that answered) and both are 1200x630, so only a fetch that can read
 * response.redirected knows. One extra request per post, in a component whose
 * whole idle contract is "one cached image", to slightly improve a fallback
 * whose content is vertically centred anyway.
 *
 * THE CANVAS GETS ONE DEFINITE AXIS, NEVER TWO. Give it a CSS width AND height
 * and the box's max-width/max-height clamp each axis on its own, stretching
 * every drawing that is not 16:9 -- 216% on a 9:16 one. See adopt().
 *
 * THREE CLASSES A HOST PAGE MAY ADD
 * ---------------------------------
 * The page adds the class; the component owns what it means.
 *
 * `is-bare` -- THE HOST SUPPLIES THE TRANSPORT. The component's own cluster
 * (mute, repeat) and its duration chip are hidden, because the page has drawn
 * its own; two transports over one drawing is a defect, not a choice. The
 * gallery's card footer and both full-screen bars are lib/fullbar.js driving
 * this player's handle, so this is what they add.
 *
 * IT DOES NOT HIDE THE VEIL. The veil is the dark wash and the play triangle
 * over a drawing that has not started: it is not a control, it is the sentence
 * "this moves". A host taking the BUTTONS over has not taken over saying that,
 * and hiding it turns the gallery into two dozen black rectangles under two
 * dozen neat footers.
 *
 * `is-immersive` -- THIS IS THE WHOLE SCREEN NOW. The box loses its border and
 * radius and fills whatever contains it, the canvas is letterboxed inside with
 * object-fit, the share card goes (a crop that is right at tile size just cuts
 * the picture off at screen size) and the veil goes with it: at that size the
 * bar is unmissable and a wash over the whole picture is only dimmer art.
 *
 * `is-plain` -- THE PERSON LOOKING AT IT DREW IT. A draft in its author's
 * composer: the wash and the big Play go, because they hid which drawing was
 * attached, and the duration chip takes a play mark so "this moves" is still
 * said. skribl_inline_draft(plain=true) adds it (owner, mock P1).
 */
(function (global) {
  'use strict';

  var doc = global.document;

  /* Every mounted box, so one can settle the others. Module-level and not
   * per-mount: a host may call mount() again after inserting more posts, and
   * the new arrivals must still stop the ones already playing. */
  var players = [];

  /* ONE AudioContext for the whole page. Browsers cap them (Chrome at six per
   * frame) and a feed can mount fifty boxes; one per box would silently stop
   * producing sound partway down the page, which is exactly the kind of failure
   * that looks like "the audio is broken sometimes". Only one Skribl plays at a
   * time, so one context is also all that is ever needed. */
  var audioCtx = null;

  var SOUND_KEY = 'skribl.inline.sound';

  function soundOn() {
    try { return global.sessionStorage.getItem(SOUND_KEY) === '1'; }
    catch (e) { return false; }        // private mode, or a host that blocks it
  }

  function setSoundOn(on) {
    try { global.sessionStorage.setItem(SOUND_KEY, on ? '1' : '0'); } catch (e) {}
    /* THE UNMUTE TAP IS THE GESTURE. On iOS the ringer switch silences Web
     * Audio but not an <audio> element, so a posted Skribl's music is inaudible
     * in a feed on a phone set to silent -- this player is Web Audio (see the
     * AudioContext below). Holding a silent <audio> session makes it audible.
     * Claimed only here, on an explicit unmute, never on load: see
     * lib/audiosession.js for why that distinction is the whole justification
     * for overriding the switch at all.
     *
     * THE FEED'S CONTRACT IS DELIBERATELY DIFFERENT FROM THE /s PLAYER'S. That
     * one holds the session only while it is AUDIBLY PLAYING and releases on
     * pause, the last frame and mute. The feed holds it for as long as SOUND IS
     * ENABLED, whether or not anything is playing: sound here is one
     * session-scoped preference shared by every post (SOUND_KEY, above) and
     * posts start and stop as you scroll, so tying the session to "is a post
     * playing" would drop and retake it on every card that scrolls past -- a
     * Control Center entry flickering down a feed -- and would need a
     * cross-player refcount to know when the LAST one stopped. Tying it to the
     * preference gives one claim on unmute and one release on mute, which is
     * the only pair of taps the viewer thinks of as sound on and off.
     *
     * The cost is bounded: with sound on and nothing playing, iOS shows Skribl
     * as playing media. Muting clears it. Tightening that is the refcount, not
     * a change of gesture. */
    if (global.SkriblAudioSession) {
      if (on) global.SkriblAudioSession.claim();
      else global.SkriblAudioSession.release();
    }
    for (var i = 0; i < players.length; i++) players[i].applySound();
  }

  /* ---- payload reading ---------------------------------------------------
   * normalizeSkribl() in app.js does more than this (it mirrors the current
   * frame's media to the top level for the editor's benefit). A player only
   * needs the two questions below answered, so this reads the payload rather
   * than rewriting it. */

  function framesOf(payload) {
    if (payload && Array.isArray(payload.frames) && payload.frames.length) return payload.frames;
    /* Legacy Skribl: the drawing lives at the top level. Wrapping it in one
     * frame is what app.js does, and it means everything below has exactly one
     * shape to handle. */
    return [{
      strokes: (payload && payload.strokes) || [],
      background: (payload && payload.background) || null,
      photo: (payload && payload.photo) || null,
      baseSnapshot: (payload && payload.baseSnapshot) || null,
      music: (payload && payload.music) || null
    }];
  }

  function isFlip(payload, frames) {
    /* Same test as app.js: an explicit playbackMode wins, otherwise more than
     * one frame means flip. A one-page Flip document replays as a still, which
     * is what it is. */
    if (payload && payload.playbackMode) return payload.playbackMode === 'flip';
    return frames.length > 1;
  }

  function logicalSize(payload) {
    var cs = payload && payload.canvasSize;
    if (cs && cs.cssWidth > 0 && cs.cssHeight > 0) {
      return { w: cs.cssWidth, h: cs.cssHeight };
    }
    /* No canvasSize: a Skribl authored before Pad had a size picker. The full
     * player derives one from the viewport, which a feed box cannot do
     * meaningfully — so take the shared default rather than inventing a second
     * answer. Inline fallback for a page that somehow loads without the lib,
     * matching how every other consumer of lib/ reads it. */
    var CS = global.SkriblCanvasSizes;
    if (CS && CS.DEFAULT) return { w: CS.DEFAULT.w, h: CS.DEFAULT.h };
    return { w: 816, h: 612 };
  }

  /* PAUSE_CAPS and the timeline build are app.js's, verbatim (app.js
   * PAUSE_CAPS / buildPlaybackTimeline). A payload carries the pauseMode it was
   * authored under so it replays the way it was posted rather than the way this
   * browser happens to be set — the same reason loadSkribl() adopts it. */
  var PAUSE_CAPS = { keep: Infinity, trim: 250, tight: 50 };

  function buildTimeline(strokes, pauseMode) {
    if (!strokes || !strokes.length) return [];
    var cap = Object.prototype.hasOwnProperty.call(PAUSE_CAPS, pauseMode)
      ? PAUSE_CAPS[pauseMode] : PAUSE_CAPS.tight;
    var playT = 0;
    var s0 = strokes[0];
    var out = [{ x: s0.x, y: s0.y, color: s0.color, size: s0.size,
                 erase: s0.erase, start: s0.start, playT: 0, i: 0 }];
    for (var i = 1; i < strokes.length; i++) {
      var gap = strokes[i].t - strokes[i - 1].t;
      if (gap > 0) playT += Math.min(gap, cap);
      var s = strokes[i];
      out.push({ x: s.x, y: s.y, color: s.color, size: s.size,
                 erase: s.erase, start: s.start, playT: playT, i: i });
    }
    /* Points that arrived in one bundle play one after another, not at once:
     * lib/holdtiming.js untie(), the rule the editors' replays share. */
    if (global.SkriblHold) global.SkriblHold.untie(out);
    return out;
  }

  /* ---- drawing -----------------------------------------------------------
   * app.js drawDot / drawLine, minus the mirror painting (an authoring
   * affordance — the reflections are committed as real points before a payload
   * is ever serialised, so a replay must NOT re-mirror them or it draws each
   * reflection twice). */

  function drawDot(ctx, x, y, color, size, erase) {
    ctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
    ctx.beginPath();
    ctx.arc(x, y, size / 2, 0, Math.PI * 2);
    ctx.fillStyle = erase ? 'rgba(0,0,0,1)' : color;
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
  }

  function drawLine(ctx, x1, y1, x2, y2, color, size, erase) {
    ctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over';
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = erase ? 'rgba(0,0,0,1)' : color;
    ctx.lineWidth = size;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }

  /* ---- the wet/dry compositor -------------------------------------------
   * A stroke below 100% opacity is ONE translucent mark, not a row of
   * translucent stamps. Drawn the naive way, every stamp composites against
   * the last and the overlaps accumulate: the edges scallop and the interior
   * bands. This keeps the in-progress stroke on its own opaque WET layer and
   * bakes it down at the stroke's alpha when the stroke ends, so overlaps
   * inside one stroke do not stack.
   *
   * A CROSS-SURFACE COMPARISON CANNOT MEASURE THIS. Scoring this player
   * against /s/<id> on verify_inline.py's 96x96 grid reports a large
   * difference, but an OPAQUE control -- which the compositor cannot touch --
   * scores worse still: most of it is the two surfaces fitting the drawing to
   * different boxes, exactly as verify_inline's own note says they do. The
   * clean instrument is ONE surface with the feature absent, which is how the
   * suite pins it: same translucent fixture, compositor disabled at source.
   *
   * An all-opaque payload, which is most of them, allocates nothing:
   * makeCompositor returns null and the direct path is what it was.
   *
   * Ported from app.js makeStrokeCompositor rather than rewritten, and it
   * draws through this file's own drawDot/drawLine so the two implementations
   * cannot drift in how a mark is shaped -- only in where it is composited.
   */
  function parseStrokeAlpha(c) {
    if (typeof c !== 'string') return 1;
    var m = c.match(/^rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)$/i);
    return m ? Math.max(0, Math.min(1, parseFloat(m[1]))) : 1;
  }

  /* The alpha in any form, the 8-digit hex a Motion Smear writes included.
   * NOT parseStrokeAlpha: that one decides the wet layer, and teaching it this
   * hex would put every generated page on a per-stroke round trip. */
  function anyStrokeAlpha(c) {
    var h = typeof c === 'string' && /^#[0-9a-f]{6}([0-9a-f]{2})$/i.exec(c.trim());
    return h ? parseInt(h[1], 16) / 255 : parseStrokeAlpha(c);
  }

  function solidStrokeColor(c) {
    if (typeof c !== 'string') return c;
    var m = c.match(/^rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*[\d.]+\s*\)$/i);
    return m ? 'rgb(' + m[1] + ', ' + m[2] + ', ' + m[3] + ')' : c;
  }

  /* Wraps a visible context. Returns null when the payload has no translucent
   * stroke and no eraser stroke, so an opaque drawing — which is most of them —
   * allocates nothing and takes the same path it always did.
   *
   * AN ERASER STROKE NEEDS A LAYER OF ITS OWN TOO. It is drawn
   * destination-out, and the background colour or photo is painted into the
   * same canvas, so on the direct path an erase cut through the background as
   * well and showed whatever was behind the player: the box's own dark ground
   * in a feed, the library, the gallery, an embed. A light drawing with an
   * eraser stroke replayed with black lines where the eraser went (the owner
   * saw it on How it works' Eraser card). The editor and /s/<id> keep the
   * background BEHIND the canvas, so an erase reveals it; here the background
   * is kept as a base layer under the ink, which is the same thing. */
  function makeCompositor(visCtx, visCanvas, strokes, ratio) {
    var any = false;
    for (var i = 0; i < strokes.length; i++) {
      if (strokes[i].erase || parseStrokeAlpha(strokes[i].color) < 1) {
        any = true;
        break;
      }
    }
    if (!any) return null;

    /* THE SCALE THE VISIBLE CONTEXT IS ALREADY USING, handed in by the
     * caller. This used to be derived as backing/clientWidth, which happened
     * to equal the device pixel ratio only while the canvas's CSS width was
     * pinned to the drawing's logical size. It is not any more -- the canvas
     * letterboxes at its intrinsic ratio (inlineplayer.css) -- so a derived
     * figure would be the display scale, not the transform's, and every
     * see-through stroke would composite at the wrong size. The offscreen
     * layers must match ctx.setTransform in adopt(), so they take the same
     * number rather than a second opinion about it. */
    var dpr = ratio || (visCanvas.width / (visCanvas.clientWidth || visCanvas.width)) || 1;
    var base = document.createElement('canvas');
    var dry = document.createElement('canvas');
    var wet = document.createElement('canvas');
    base.width = dry.width = wet.width = visCanvas.width;
    base.height = dry.height = wet.height = visCanvas.height;
    var dctx = dry.getContext('2d');
    var wctx = wet.getContext('2d');
    /* The base is whatever is already painted -- background, photo underlay --
     * and the ink goes on a clear layer above it, so an erase reveals the
     * base rather than cutting through it. */
    base.getContext('2d').drawImage(visCanvas, 0, 0);
    dctx.setTransform(1, 0, 0, 1, 0, 0);
    dctx.scale(dpr, dpr);
    wctx.setTransform(1, 0, 0, 1, 0, 0);
    wctx.scale(dpr, dpr);
    var lgW = visCanvas.width / dpr, lgH = visCanvas.height / dpr;
    var wetActive = false, wetAlpha = 1;

    function bakeWet() {
      dctx.save();
      dctx.setTransform(1, 0, 0, 1, 0, 0);
      dctx.globalAlpha = wetAlpha;
      dctx.drawImage(wet, 0, 0);
      dctx.restore();
      wctx.clearRect(0, 0, lgW, lgH);
      wetActive = false;
      wetAlpha = 1;
    }

    return {
      dot: function (x, y, color, size, erase) {
        if (wetActive) bakeWet();
        var a = erase ? 1 : parseStrokeAlpha(color);
        if (!erase && a < 1) {
          wetActive = true;
          wetAlpha = a;
          wctx.clearRect(0, 0, lgW, lgH);
          drawDot(wctx, x, y, solidStrokeColor(color), size, false);
        } else {
          drawDot(dctx, x, y, color, size, erase);
        }
      },
      line: function (x1, y1, x2, y2, color, size, erase) {
        if (wetActive) {
          drawLine(wctx, x1, y1, x2, y2, solidStrokeColor(color), size, false);
        } else {
          drawLine(dctx, x1, y1, x2, y2, color, size, erase);
        }
      },
      /* Called once per frame. The wet layer is drawn ON TOP at its alpha
       * rather than baked, so a stroke still in progress reads correctly
       * without being committed early. */
      present: function () {
        visCtx.save();
        visCtx.setTransform(1, 0, 0, 1, 0, 0);
        visCtx.globalAlpha = 1;
        visCtx.clearRect(0, 0, visCanvas.width, visCanvas.height);
        visCtx.drawImage(base, 0, 0);
        visCtx.drawImage(dry, 0, 0);
        if (wetActive) {
          visCtx.globalAlpha = wetAlpha;
          visCtx.drawImage(wet, 0, 0);
        }
        visCtx.restore();
      },
      finish: function () { if (wetActive) bakeWet(); },
      /* The ink layer, for lib/seekcache.js to copy (after finish(), at a
       * stroke boundary, so nothing is half drawn), and seed() to start a
       * fresh compositor from such a copy. The photo stays the base. */
      dry: dry,
      seed: function (copy) {
        dctx.save();
        dctx.setTransform(1, 0, 0, 1, 0, 0);
        dctx.drawImage(copy, 0, 0);
        dctx.restore();
      },
    };
  }

  /* app.js replayTimelineToCanvas, verbatim: draw every point whose playT has
   * elapsed and return the index to resume from. The `i === 0` in the start
   * test matters — the first point of a payload may carry no `start` flag at
   * all, and without it the replay opens with a line from (0,0). */
  function replayTo(ctx, timeline, from, elapsed, comp, cache) {
    var i = from;
    /* `comp` is null for an all-opaque payload — then this is the direct path
     * it always was, with no allocation and no wrapper. `cache` is
     * lib/seekcache.js, which copies the ink at a stroke boundary on the way. */
    while (i < timeline.length && timeline[i].playT <= elapsed) {
      if (cache) cache.tap(i, comp && comp.finish);
      var p = timeline[i];
      var prev = i > 0 ? timeline[i - 1] : null;
      var st = p.start || i === 0;
      if (comp) {
        if (st) comp.dot(p.x, p.y, p.color, p.size, p.erase);
        else comp.line(prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
      } else if (st) {
        drawDot(ctx, p.x, p.y, p.color, p.size, p.erase);
      } else {
        drawLine(ctx, prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
      }
      i++;
    }
    if (comp) comp.present();
    return i;
  }

  /* Inline fallback for lib/strokelayers.js's uniformRun, as for every lib. */
  function uniformRun(seg, alphaFn) {
    var p = seg[0], a, i, q;
    if (seg.length < 2 || p.erase || !((a = alphaFn(p.color)) < 1)) return 0;
    for (i = 1; i < seg.length; i++) { q = seg[i];
      if (q.erase || q.color !== p.color || q.size !== p.size) return 0; }
    return a;
  }

  function paintStatic(ctx, strokes, canvas, ratio) {
    /* The idle poster and every non-replay repaint come through here, so the
     * compositor has to be on this path too — otherwise a post looks right
     * while playing and wrong the moment it settles. */
    var comp = canvas ? makeCompositor(ctx, canvas, strokes, ratio) : null;
    var fn = (typeof window !== 'undefined' && window.SkriblStrokeLayers
              && window.SkriblStrokeLayers.uniformRun)
      ? window.SkriblStrokeLayers.uniformRun : uniformRun;
    var i = 0, j, k, seg, p, prev;
    while (i < strokes.length) {
      /* One run = a start flag to the next; `i === 0` as replayTo allows. */
      j = i + 1;
      while (j < strokes.length && !strokes[j].start) j++;
      seg = strokes.slice(i, j);
      p = seg[0];
      /* ONE PATH when the run can take it -- see lib/strokelayers.js. A smear's
       * ghosts are the case the compositor cannot reach, their alpha being hex. */
      if (!comp && fn(seg, anyStrokeAlpha)) {
        ctx.strokeStyle = p.color; ctx.lineWidth = p.size;
        ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        ctx.beginPath(); ctx.moveTo(p.x, p.y);
        for (k = 1; k < seg.length; k++) ctx.lineTo(seg[k].x, seg[k].y);
        ctx.stroke();
      } else for (k = i; k < j; k++) {
        p = strokes[k];
        prev = strokes[k - 1];
        if (p.start || k === 0) {
          if (comp) comp.dot(p.x, p.y, p.color, p.size, p.erase);
          else drawDot(ctx, p.x, p.y, p.color, p.size, p.erase);
        } else if (comp) comp.line(prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
        else drawLine(ctx, prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
      }
      i = j;
    }
    if (comp) { comp.finish(); comp.present(); }
  }

  /* A post's stored shape (validation._payload_line): one base-36 digit per
   * column, 0 for none, the square root already taken -> 0..1 columns, which
   * the scrubber pools to its own width (lib/replayline.js `shape`). */
  function shapeOf(t) {
    if (typeof t !== 'string' || !/^[0-9a-z]+$/.test(t)) return null;
    return t.split('').map(function (c) { return parseInt(c, 36) / 35; });
  }

  function fmt(ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
  }

  /* ---- the poster, framed where the canvas will be ------------------------ */

  /* THE CARD CONTAINS THE DRAWING, which is the whole problem this solves.
   *
   * A tile shows the share card until somebody presses play. The card is
   * 1200x630 with the drawing CONTAINED inside it -- so a 4:3 drawing sits in
   * a 656px-wide picture in the middle of a 1200px card, and the stylesheet's
   * band crop (which removes the brand strip and nothing else) leaves 110px of
   * card ground and the card's own plate border showing on each side: a
   * picture inside a frame inside a card, on every tile.
   *
   * THE POSTER NOW LANDS EXACTLY WHERE THE CANVAS WILL. Same rectangle, same
   * letterbox, so pressing play changes what moves and not where it is.
   *
   * IT NEEDS THE DRAWING'S SHAPE and cannot look it up -- the listing defers
   * `payload_json` on purpose, which is why `canvas_w`/`canvas_h` are columns
   * on the post. The page writes them onto the box as data-skribl-w/h;
   * WITHOUT them nothing here runs and the stylesheet's band crop stands,
   * which is what a row predating the column gets.
   *
   * THE ARITHMETIC IS lib/sharecard.js drawingRect(), inlined rather than
   * imported for the reason the macro's own note gives: a page that only
   * DISPLAYS Skribls is not charged for loading the module that COMPOSES the
   * card. verify_inline.py evaluates the real module against these literals,
   * so the copy cannot drift without a suite going red.
   */
  /* The card, in card pixels. AREA_W/AREA_H are CARD_W - PAD*2 and
   * CARD_H - PAD - FOOTER with PAD 54 and FOOTER 84; written out rather than
   * derived because every byte of this file is downloaded by every host. */
  var CARD_W = 1200, CARD_H = 630, AREA_W = 1092, AREA_H = 492, FOOT = 84;
  /* The box's own aspect, from .skribl-inline's `aspect-ratio: 16 / 9` -- the
   * widest canvas a drawing can have (lib/canvassizes.js). Every percentage
   * below resolves against the box, so this is the one shape they assume.
   * PLATE_R / PLATE_IN are lib/sharecard.js's PLATE_R and PLATE_LW. */
  var BOX_A = 16 / 9, PLATE_R = 18, PLATE_IN = 2;

  function fitPoster(img, w, h, boxA) {
    /* Where the card put the drawing: drawingRect(), rounding included --
     * matching the card's own rounding is what makes one scale factor exact
     * on both axes below. */
    var sc = Math.min(AREA_W / w, AREA_H / h);
    var dw = Math.round(w * sc), dh = Math.round(h * sc);
    if (!(dw > 0 && dh > 0)) return;
    var dx = Math.round((CARD_W - dw) / 2), dy = Math.round((CARD_H - FOOT - dh) / 2);
    /* Where the CANVAS will be, in units of the box's HEIGHT. The component
     * letterboxes it, so whichever axis runs out first decides: cw is the
     * width, ch the height, and ch = cw / a covers both cases at once. */
    var A = boxA || BOX_A, a = dw / dh, cw = Math.min(a, A), ch = cw / a;
    /* One factor, card pixels -> box-height units, so the image scales
     * uniformly and the drawing's rect lands on the canvas's rect. */
    var k = cw / dw, st = img.style, i = PLATE_IN;
    function p(n, of) { return n / of * 100 + '%'; }
    st.width = p(CARD_W * k, A);
    st.height = p(CARD_H * k, 1);
    st.left = p((A - cw) / 2 - dx * k, A);
    st.top = p((1 - ch) / 2 - dy * k, 1);
    /* The stylesheet centres the band crop with a transform; this one is
     * positioned outright, so the transform has to go or it shifts twice. */
    st.transform = 'none';
    st.maxWidth = 'none';
    img._d = [dx, dy, dw, dh];       // where the drawing is, for tone()
    var bx = img.parentNode.style;   // the drawing's corner, for .is-says
    bx.setProperty('--sx', p((A - cw) / 2, A)); bx.setProperty('--sy', p((1 - ch) / 2, 1));
    /* The corner is a share of the IMAGE, which is the whole card, because
     * that is what inset()'s radius resolves against like its four edges. As
     * a share of the drawing it stretched by the card's width over the
     * drawing's: a tall one's came out 87 x 26 px for the card's 20 round. */
    st.clipPath = 'inset(' + p(dy + i, CARD_H) + ' ' + p(CARD_W - dx - dw + i, CARD_W)
      + ' ' + p(CARD_H - dy - dh + i, CARD_H) + ' ' + p(dx + i, CARD_W)
      + ' round ' + p(PLATE_R - i, CARD_W) + '/' + p(PLATE_R - i, CARD_H) + ')';
  }

  /* ---- one box ----------------------------------------------------------- */

  function attach(el) {
    if (el._skriblInline) return el._skriblInline;

    var id = el.getAttribute('data-skribl-id');
    /* The listing endpoint, written in by the macro from url_for(). A host may
     * mount Skribl under any prefix, so the component never assembles a URL
     * from window.location or from a literal path -- it appends an id to what
     * the server said the endpoint is.
     *
     * NO DEFAULT. A fallback of '/api/skribls' sends every payload fetch on a
     * host mounted at /skribl to a path that does not exist, and quietly: the
     * box just shows its error panel. A box with no endpoint attribute cannot
     * fetch, so it says so (see load()). A DRAFT has no endpoint and needs
     * none: it is attached by payload and never loads. */
    var api = (el.getAttribute('data-skribl-api') || '').replace(/\/+$/, '');
    var canvas = el.querySelector('.skribl-inline-canvas');
    var poster = el.querySelector('.skribl-inline-poster');
    var prog = el.querySelector('.skribl-inline-prog');
    var nib = el.querySelector('.skribl-inline-nib');
    var durEl = el.querySelector('.skribl-inline-dur');
    var durText = el.querySelector('.skribl-inline-dur-text');
    var playEl = el.querySelector('.skribl-inline-play');
    /* THE LINE UNDER THE DRAWING (v322): the macro's next sibling, holding the
     * scrubber, the words and -- off the drawing now -- mute and loop. */
    var line = el.nextElementSibling;
    if (!line || !line.classList.contains('skribl-inline-line')) line = null;
    function q(sel) { return el.querySelector(sel) || (line && line.querySelector(sel)); }
    var muteBtn = q('.skribl-inline-mute');
    var loopBtn = q('.skribl-inline-loop');
    var errEl = el.querySelector('.skribl-inline-err');
    /* An id is NOT required — a draft's skribl is attached by payload and has
     * none (api.attach below). The canvas and the two chrome elements are, and
     * their absence means this is not the macro's markup. */
    if (!canvas || !prog || !nib) return null;

    var ctx = canvas.getContext('2d');
    /* WHAT "IDLE" LOOKS LIKE depends on whether there is a poster behind the
     * canvas. A posted skribl has one — the cropped share card — so the canvas
     * can sit at time zero underneath it. A DRAFT in a host's composer has no
     * poster (nothing is published, so there is no card), and time zero is a
     * blank rectangle: the composer showed an empty box where the drawing was
     * meant to be. Posterless, idle is the FINISHED drawing. */
    var hasPoster = !!poster;
    var payload = null, loading = false, failed = false;
    var timeline, flipFrames, flipFps = 12, flipPlan;
    var totalMs = 0, size = null, under = null;
    /* NOT `under`, which is the background colour and photo (adopt). This is
       the PAGE underneath (lib/holdtiming.js underOf) and its one painting. */
    var underPage, underPageCv;
    /* The scale ctx.setTransform is set to in adopt(), so the compositor's
       offscreen layers can match it instead of inferring it from CSS. */
    var pixelRatio = 1;
    var rate = 1;                             // the viewer's speed; see frame()
    /* What the speed button says: 'fit' or a rate. `rate` is what it comes
     * to; `picked` is the viewer having chosen, which the drawing arriving
     * must not undo. */
    var choice = 1, picked = false;
    var RL = global.SkriblReplayLine, lineUI = null, scrubUI = null, bar = null;
    var info = null, pagesN = 0, shapeCols = null, drawnMs = null, held = false, pendingF = null;
    var clockFn = null;   // replay ms -> the artist's, for the scrubber's bubble
    var state = 'idle';                       // idle | playing | paused
    var elapsed = 0, t0 = 0, raf = null, drawn = 0;
    /* The page and progress this player last PAINTED, which is how
     * lib/holdtiming.js's displayAt() knows a drawing page has not yet been
     * shown whole. Unset, or null after adopt(), means nothing is owed a
     * finish. */
    var lastShown;
    /* Rebuilt on every full repaint; null for an all-opaque payload. */
    var comp = null;
    /* lib/seekcache.js for this document's replay: made on its first full
     * repaint, dropped when the document or its underlay changes. */
    var seekCache = null, drewFrom = 0;
    /* A far first jump racing there (lib/seekcache.js race(), the owner's
     * pick A): any repaint stops it. Play pressed meanwhile waits for it to
     * land (`queued`), and says it is playing, as it will be. */
    var racer = null, queued = false;
    var buffer = null, srcNode = null, gainNode = null, decoding = false;
    var music = null;
    /* PER POST, unlike mute, and that asymmetry is deliberate. Sound is
     * environmental — someone in a quiet room wants it off for the whole feed,
     * so unmuting one post unmutes them all. Repeating is a property of THIS
     * drawing: a two-second loop you want to watch again is not a statement
     * about the next post. So this is per instance and not remembered; the
     * default is on, which is what a post did before there was a control. */
    var looping = true;

    var me = {
      el: el,
      settle: settle,
      applySound: applySound,
      /* Read by verify_inline.py. A player that can only be checked by looking
       * at it is a player nothing can hold to a number. */
      adopt: function (p) { adopt(p); },
      /* TRANSPORT, for a surface that is allowed one. A post is not — see
       * inlineplayer.css — but the profile's Skribls tab is a page ABOUT the
       * drawings, where scrubbing and restarting are the point. It drives this
       * player rather than being a third replay implementation; the buttons are
       * the host's, the clock is still this one. */
      play: play,
      pause: pause,
      toggle: function () { if (state === 'playing' || queued) pause(); else play(); },
      /* Posts loop: a still frame at the end of a two-second replay reads as
       * broken, and a Flip document IS a loop. A library stage can offer the
       * choice, because somebody looking at one drawing on purpose may want it
       * to stop. */
      setLoop: function (on) { setLooping(on); },
      looping: function () { return looping; },
      /* Changing rate mid-play RE-ANCHORS the clock: `elapsed` is scaled time
       * already banked and `t0` is a wall-clock instant, so the new rate must
       * not be applied retroactively to the segment so far or the drawing
       * jumps. Bank at the old rate, then restart both clocks. */
      setRate: function (r) {
        r = +r;
        if (!(r > 0)) return rate;
        choice = r; picked = true;
        if (lineUI) lineUI.update();
        return applyRate(r);
      },
      rate: function () { return rate; },
      state: function () {
        /* segElapsed(), NOT `now() - t0`. The segment since the last anchor is
         * WALL time and `elapsed` is banked SCALED time, so adding the two raw
         * reports the replay running at 1x however fast it is really drawing.
         * Everything a viewer can see about the clock reads this field -- the
         * scrubber fill, the time readout, fullbar's end detection -- so at 2x
         * the drawing doubles and the bar crawls at half the true progress,
         * and the speed control looks DEAD. The render loop reads
         * `elapsed + segElapsed()`, which is why the drawing obeys the rate
         * even when nothing else does. A probe that reads THIS field instead
         * of the pixels agrees with the bug. */
        return { id: id, state: queued ? 'playing' : state, totalMs: totalMs, racing: !!racer,
                 elapsedMs: state === 'playing' ? elapsed + segElapsed() : elapsed,
                 kind: flipFrames ? 'flip' : 'replay', hasAudio: !!music,
                 muted: !soundOn(), loaded: !!payload, failed: !!failed,
                 /* lib/seekcache.js: the copies held, and the points drawn
                 * since the last full repaint, so the suite can see where a
                 * seek started. */
                 copies: seekCache ? seekCache.held().length : 0,
                 drawnLast: drawn - drewFrom,
                 stretch: seekCache ? seekCache.gap() : 0 };
      },
      /* Also for the suite: freeze the drawing at an exact offset so the two
       * players can be compared at the SAME point in the replay rather than at
       * whatever moment two rAF loops happen to land on. */
      seek: function (ms) {
        if (!payload) return false;
        pause();
        elapsed = Math.max(0, Math.min(ms, totalMs));
        render(elapsed, true, true);
        return true;
      },
      /* THE DRAWING'S FOOT, for a bar laid over it (lib/fullbar.js's card):
       * its bottom eighth in n strips across, each strip the middle value of
       * its own pixels, so a line of ink through it does not tint it. Null
       * until there is something to read; `then` runs when the card loads. */
      ground: function (n, then) {
        if (poster && !poster.naturalWidth && !(payload && !canvas.hidden)) {
          if (then) poster.addEventListener('load', function () { then(); }, { once: true });
          return null;
        }
        var w = 6, h = 12, px = readArea(0.01, 0.875, 0.98, 0.115, n * w, h), out = [];
        if (!px) return null;
        for (var s = 0; s < n; s++) {
          var ch = [[], [], []];
          for (var y = 0; y < h; y++) for (var x = s * w; x < s * w + w; x++)
            for (var i = 0, o = (y * n * w + x) * 4; i < 3; i++) ch[i].push(px[o + i]);
          out.push(ch.map(function (v) { v.sort(function (a, b) { return a - b; }); return v[v.length >> 1]; }));
        }
        return out;
      },
      /* Where the drawing is on screen now, and the round of its two bottom
       * corners, for the same bar, which keeps its fade inside them: the
       * canvas while it shows, else the card's crop of it (the plate's own
       * corner), each within this box's rounded edge. */
      area: function () {
        var b = el.getBoundingClientRect(), cs = getComputedStyle(el), bw = parseFloat(cs.borderBottomWidth) || 0,
            R = Math.max(0, (parseFloat(cs.borderBottomLeftRadius) || 0) - bw), r, rad = 0;
        if (payload && !canvas.hidden) r = canvas.getBoundingClientRect();
        else if (poster && poster._d && poster.naturalWidth) {
          var p = poster.getBoundingClientRect(), s = p.width / CARD_W, d = poster._d, i = PLATE_IN;
          r = { left: p.left + (d[0] + i) * s, right: p.left + (d[0] + d[2] - i) * s,
                top: p.top + (d[1] + i) * s, bottom: p.top + (d[1] + d[3] - i) * s };
          rad = (PLATE_R - i) * s;
        } else return null;
        var x0 = Math.max(r.left, b.left + bw), x1 = Math.min(r.right, b.right - bw),
            y1 = Math.min(r.bottom, b.bottom - bw);
        function round(x, edge) { return Math.abs(x - edge) < 1.5 && Math.abs(y1 - b.bottom + bw) < 1.5 ? Math.max(R, rad) : rad; }
        return { left: x0, right: x1, top: Math.max(r.top, b.top + bw), bottom: y1,
                 rl: round(x0, b.left + bw), rr: round(x1, b.right - bw) };
      }
    };
    players.push(me);
    el._skriblInline = me;

    function now() { return global.performance ? performance.now() : Date.now(); }

    /* THE CLOCK AT A NEW SPEED -- setRate's, and the speed button's. */
    function applyRate(r) {
      if (state === 'playing') { elapsed += segElapsed(); t0 = now(); }
      rate = r;
      /* The drawing's speed is already changed by the line above; the audio
       * graph is a second, weaker thing. It is rebuilt on an AudioContext
       * the browser is allowed to take away, and a throw from in here used
       * to escape setRate with the new rate already applied -- so the caller
       * never got its return, never repainted, and the control reported a
       * speed the player was no longer running at. Silence is a degradation
       * and a lying label is a bug, which is the same order of preference
       * the decode path states a few hundred lines down. */
      if (state === 'playing') { try { startAudio(); } catch (e) {} }
      return rate;
    }

    function busy(on) {
      if (playEl) playEl.classList.toggle('is-busy', !!on);
    }

    /* A DRAWING THAT CAN'T BE SHOWN SAYS SO KINDLY (the owner's pick after
     * v322, from a mock on skribls.net's own Home page). It was a black box,
     * red words in the code face and a Play that did nothing. Now the box keeps
     * the page's ground and type (inlineplayer.css, .is-failed) and says one
     * of two things, because the API answers one of two ways. A 404 is final:
     * the drawing was deleted, or is no longer this viewer's to see, and the
     * API never says which (routes.py: 404, not 403) -- so it says the drawing
     * isn't here anymore and asks for nothing. Anything else (offline, a 500,
     * a dropped connection) is worth another try, and a tap tries. "Drawing",
     * not "Skribl": on skribls.net every post is a Skribl, and "couldn't load
     * this Skribl" reads as the whole post failing. */
    var label = el.getAttribute('aria-label');
    var FAIL_WORDS = { gone: ['This drawing isn’t here anymore.'],
                       retry: ['Couldn’t load this drawing.', 'Tap to try again.'],
                       unwired: ['This Skribl is not wired up.'] };
    function fail(kind) {
      failed = kind;
      busy(false);
      var words = FAIL_WORDS[kind];
      el.classList.add('is-failed');
      el.classList.toggle('is-retry', kind === 'retry');
      if (line) line.classList.add('is-failed');
      el.setAttribute('aria-label', words.join(' '));
      if (errEl) {
        errEl.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20c2.5-.5 4-2 6-4.5"/>' +
          '<path d="M14.5 5.5l4 4L10 18l-4.5.5.5-4.5z"/><path d="M13 7l4 4"/></svg>';
        for (var i = 0; i < words.length; i++) {
          var s = document.createElement('span'); s.textContent = words[i]; errEl.appendChild(s);
        }
        errEl.hidden = false;
      }
    }

    function unfail() {
      failed = false;
      el.classList.remove('is-failed', 'is-retry');
      if (line) line.classList.remove('is-failed');
      el.setAttribute('aria-label', label);
      if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    }

    function load() {
      if (payload || loading || failed) return Promise.resolve(payload);
      if (!api) {
        /* Nothing to fetch from. The macro always writes the endpoint in, so
         * this is hand-built markup missing data-skribl-api — say so rather
         * than guess a path. */
        fail('unwired');
        return Promise.resolve(null);
      }
      loading = true;
      busy(true);
      return global.fetch(api + '/' + encodeURIComponent(id),
                          { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) { var e = new Error('HTTP ' + r.status); e.status = r.status; throw e; }
          return r.json();
        })
        .then(function (body) {
          /* The drawing lives under `skribl` in the GET envelope — the same
           * key app.js reads, and NOT `payload`, which is what the database
           * column is called and what this file assumed first: the box played
           * a zero-length nothing and reported totalMs 0. A host proxy that
           * hands back the drawing bare still works. */
          adopt((body && (body.skribl || body.payload)) || body);
          loading = false;
          busy(false);
          return payload;
        })
        .catch(function (e) {
          loading = false;
          fail(e && (e.status === 404 || e.status === 410) ? 'gone' : 'retry');
          return null;
        });
    }

    function adopt(p) {
      payload = p || {};
      seekCache = null;
      var frames = framesOf(payload);
      size = logicalSize(payload);

      /* At most 2 pixels a point: a feed holds many players and a third
       * pixel is half again the memory and paint for each. One player alone
       * on the screen may ask for its screen's own (attach's maxDpr): Blooby's
       * hello on a 3x phone, which at 2 drew soft. */
      var dpr = Math.min(global.devicePixelRatio || 1, me.maxDpr || 2);
      pixelRatio = dpr;
      canvas.width = Math.round(size.w * dpr);
      canvas.height = Math.round(size.h * dpr);
      /* NO CSS SIZE IS SET, AND THAT IS THE LETTERBOX. Setting
       * canvas.style.width/height to the drawing's logical size does NOT let
       * max-width/max-height preserve the aspect: a replaced element whose
       * width AND height are both definite has each axis clamped by its own
       * maximum, independently -- so a 9:16 drawing in the 16:9 box comes out
       * stretched 216%, and a 4:3 one by 33%, on the feed, on the profile
       * stage and in any host's embed. (/s/<id> is unaffected: app.js fits the
       * canvas itself.) With both auto, the bitmap's own dimensions are the
       * intrinsic ratio and the two maximums letterbox it.
       *
       * THE COMPOSITOR'S SCALE IS THE SECOND HALF OF THIS. Deriving the device
       * pixel ratio as backing/clientWidth is only the true ratio while a CSS
       * width is pinned; with max-width clamping, the offscreen layers run
       * ~1.94x out and every see-through stroke composites at about twice its
       * size -- inflation large enough to carry verify_inline's ink gate over
       * a floor calibrated on it. The ratio is passed in; see makeCompositor. */
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      canvas.hidden = false;

      var f0 = frames[0] || {};
      music = (f0.music && f0.music.data) ? f0.music : (payload.music || null);
      if (music && !music.data) music = null;
      mark('is-silent', !music);
      drawnMs = clockFn = null;

      /* The underlay: background colour, then a photo or base snapshot.
       *
       * THE AUTHORED FIT TRAVELS WITH THE PHOTO. Cover is the editor's
       * DEFAULT, not what the author chose once they touched the control: hard
       * -coding it letterboxes a Fit photo in the editor and on /s/<id> and
       * CROPS it here. And there is no second implementation to write --
       * lib/photofit.js has owned this geometry since Pad, Flip and the player
       * each had their own copy and one could not read what another wrote.
       *
       * OPACITY AND BLUR TRAVEL TOO. The editor and /s/<id> put the photo in a
       * real <img> behind the canvas and let CSS fade and soften it; a feed box
       * has one canvas and nothing else, so the same two choices are
       * globalAlpha and ctx.filter.
       *
       * THE BLUR RADIUS NEEDS NO CONVERSION, which is why it is one line.
       * ctx.filter works in user space and the context is scaled by the device
       * pixel ratio in adopt(), so `blur(12px)` here covers the same distance
       * across the drawing as `filter: blur(12px)` on the editor's img, on a 1x
       * screen and a 2x one alike. Writing the conversion by hand is what would
       * make it wrong. */
      under = { color: (f0.background && f0.background.color) || (payload.background || {}).color || null,
                image: null, fit: null, offX: 0.5, offY: 0.5, zoom: 1, op: 1, bl: 0 };
      var ph = f0.photo || null;
      if (ph && ph.data) {
        /* Only a PHOTO carries a fit. A base snapshot is already the canvas's
         * own size and shape, so every mode agrees on it and the default
         * stands. */
        under.fit = ph.fit;
        var off = ph.offset || {};
        if (off.x != null) under.offX = off.x;
        if (off.y != null) under.offY = off.y;
        if (ph.zoom != null) under.zoom = ph.zoom;
        if (ph.opacity != null) under.op = ph.opacity;
        if (ph.blur != null) under.bl = ph.blur;
      }
      var src = (ph && ph.data) || f0.baseSnapshot || payload.baseSnapshot || null;
      if (src) {
        var img = new global.Image();
        /* THE REPAINT MUST NOT MOVE TIME. This used to be render(elapsed, true)
         * unconditionally, and `elapsed` is 0 while idle — so on a drawing with
         * a photo or a base snapshot, the underlay finishing its decode wiped
         * whatever was on screen and repainted the FIRST frame. On a posted
         * skribl the poster hides that; on a draft in a host's composer, where
         * idle is the finished drawing, it left an empty box where the drawing
         * had just been. Route through the same idle rule instead. */
        img.onload = function () {
          under.image = img;
          seekCache = null;   // its copies hold the canvas from before the photo
          if (state === 'idle') renderIdle(); else render(elapsed, true);
        };
        img.src = src;
      }

      /* EVERY DOCUMENT STARTS FROM NOTHING. The library's stage adopts one
       * Skribl after another into this same player, and render() picks its
       * painter by flipFrames: a Flip's frames, plan and page underneath, left
       * over from the last one, made a replay adopted after it play the
       * Flip's pages in the replay's box on the replay's clock (the owner:
       * Skater Girl's clock running under the Blooby card, cut off at her
       * canvas's edge). underPageCv is painted again at this backing store's
       * size, on first use. */
      flipFrames = flipPlan = underPage = underPageCv = lastShown = null;
      if (isFlip(payload, frames)) {
        flipFrames = frames;
        flipFps = payload.fps || 12;
        /* PER-PAGE MILLISECONDS. A page carrying `draw` replays its own
         * strokes over their recorded timing and is exempt from fps, so a page
         * is no longer a whole number of fps slots. Without the lib this
         * degrades to one slot per page, which is what it did before per-page
         * holds existed — the fallback's job is to keep a page turning, not to
         * reproduce a feature. */
        /* THE PLAY ORDER (lib/holdtiming.js plan), looped stretch or not:
         * one path for every Flip, and totalMs is one pass of it. A loop the
         * lib does not accept is ignored. */
        var H = global.SkriblHold;
        flipPlan = (H && H.plan) ? H.plan(frames, flipFps, payload.loop) : null;
        totalMs = flipPlan ? flipPlan.cycle : Math.max(1, (frames.length / flipFps) * 1000);
        /* A Flip has no author's speed (a post swapped in before it may have
         * set one); a viewer's pick stands, unless it was Fit, which a loop
         * has no whole to fit. */
        if (!picked || choice === 'fit') choice = 1;
        rate = choice;
        underPage = (H && H.underOf) ? H.underOf(payload.under, frames.length) : null;
      } else {
        timeline = buildTimeline(f0.strokes || [], payload.pauseMode);
        totalMs = timeline.length ? timeline[timeline.length - 1].playT : 0;
        /* WHERE A VIEWER STARTS: the author's pick, `playSpeed`. The same
         * rule as lib/replayline.js fromPost() -- 'fit' or 'auto' over a
         * minute of drawing lands the whole replay in about 30 seconds and
         * never slower than as drawn; a listed rate is that rate; anything
         * else, and every post from before it existed, plays as drawn --
         * written out here rather than loaded, to stay off a host's byte
         * budget. "A minute of drawing" is the artist's time: every positive
         * gap between points, uncapped. */
        var ps = payload.playSpeed, st = f0.strokes || [], dm = 0;
        for (var k = 1; k < st.length; k++) if (st[k].t > st[k - 1].t) dm += st[k].t - st[k - 1].t;
        drawnMs = dm;
        if (RL && timeline.length > 1) clockFn = RL.clockMap(timeline, st);
        /* A speed the viewer picked before the drawing arrived is theirs. */
        if (!picked) choice = ps === 'fit' || (ps === 'auto' && dm > 60000) ? 'fit'
          : [0.25, 0.5, 1, 2, 4, 8, 16].indexOf(ps) >= 0 ? ps : 1;
        rate = choice === 'fit' ? Math.max(1, totalMs / 30000) : choice;
      }

      if (durText) durText.textContent = fmt(totalMs);
      if (durEl) durEl.hidden = false;
      if (lineUI) {
        lineUI.update();
        var fitB = line.querySelector('[data-r="fit"]');
        if (fitB) fitB.hidden = !!flipFrames;
      }
      if (scrubUI) scrubUI.reset();
      renderIdle();
    }

    function renderIdle() {
      render(hasPoster ? 0 : totalMs, true);
      /* render() sets the hairline from the time it drew, and posterless idle
       * draws the END of the replay — which left a full-width progress bar on a
       * post that has not been played. Idle is not "finished". */
      prog.style.width = '0';
    }

    /* ---- rendering ------------------------------------------------------ */

    function clear() {
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
      if (under && under.color) {
        ctx.fillStyle = under.color;
        ctx.fillRect(0, 0, size.w, size.h);
      }
      if (under && under.image) {
        /* THE SAME GEOMETRY THE EDITORS AND THE EXPORT USE — one module, so a
         * photo cannot land in three places on three surfaces. The fallback is
         * the old centred cover, kept only for the case where the module did
         * not load: a drawing that renders slightly wrong beats a box that
         * renders nothing. */
        var iw = under.image.naturalWidth || size.w, ih = under.image.naturalHeight || size.h;
        var PF = global.SkriblPhotoFit;
        /* SAY SO RATHER THAN QUIETLY GUESS. The fallback below is the old
         * centred cover, and when the profile stage turned out not to load
         * this module the fallback rendered a cropped photo in silence -- a
         * fail-open guard written the same day three others were closed for
         * failing open. A host who omits the module now gets a warning naming
         * it; the templates in this tree are held to it by verify_library.py,
         * which reads the script tags rather than trusting this comment. */
        if (!PF && !global.__skriblPhotoFitWarned) {
          global.__skriblPhotoFitWarned = true;
          if (global.console && console.warn) {
            console.warn('skribl: lib/photofit.js is not loaded; the ' +
                         'background photo will be centred and cropped ' +
                         'instead of using the fit its author chose.');
          }
        }
        /* Set around BOTH branches, so the fallback cannot quietly paint a
           photo at full strength while the module path fades it. Restored
           unconditionally: a filter or an alpha left on leaks into the ink
           drawn immediately after it, which is a far worse defect than the
           one this fixes. */
        ctx.globalAlpha = under.op;
        if (under.bl > 0) ctx.filter = 'blur(' + under.bl + 'px)';
        if (PF) {
          var r = PF.rect(iw, ih, size.w, size.h,
                          { fit: under.fit, offX: under.offX,
                            offY: under.offY, zoom: under.zoom });
          ctx.drawImage(under.image, r.x, r.y, r.w, r.h);
        } else {
          var k = Math.max(size.w / iw, size.h / ih);
          var dw = iw * k, dh = ih * k;
          ctx.drawImage(under.image, (size.w - dw) / 2, (size.h - dh) / 2, dw, dh);
        }
        ctx.globalAlpha = 1;
        ctx.filter = 'none';
      }
    }

    /* What a copy is, and how one comes back: the compositor's ink layer when
     * there is one (the photo stays its base, which an eraser reveals), else
     * the whole canvas. */
    function seekSource() { return comp ? comp.dry : canvas; }
    function seekPut(copy) {
      clear();
      comp = makeCompositor(ctx, canvas, timeline, pixelRatio);
      if (comp) { comp.seed(copy); return; }
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(copy, 0, 0);
      ctx.restore();
    }
    /* Full repaint from zero. The incremental path below only appends, which is
     * what makes a replay cheap; anything that moves time backwards (seek,
     * loop, a resize) comes through here. */
    function render(at, full, jump) {
      if (!payload) return;
      if (racer) { racer.stop(); racer = null; }
      if (flipFrames) {
        var H = global.SkriblHold;
        /* THROUGH displayAt() WHEN PLAYING, because no instant of the live
         * clock supplies progress 1 while a drawing page is still current, and
         * that page must reach its complete recorded state before the clock
         * may leave it. `jump` is a SCRUB and only a scrub: someone dragging
         * the bar asked for that page and must get it, and passing no `last`
         * is how displayAt() is told there is nothing owed. A LOOP RESTART is
         * not a jump -- it is the clock coming round, and the page it leaves
         * is owed its last frame as any page turn is, which is why this cannot
         * key off `full`: the loop repaints fully too. See lib/holdtiming.js. */
        var shown = flipPlan
          ? H.displayAt(flipPlan, flipFrames, at, jump ? null : lastShown)
          : { index: Math.min(flipFrames.length - 1,
                              Math.floor(at / Math.max(1, totalMs) * flipFrames.length)),
              progress: 0 };
        lastShown = shown;
        var idx = shown.index;
        clear();
        /* THE PAGE UNDERNEATH: painted ONCE, offscreen, through the same
         * painter, then one drawImage a frame -- a card of thousands of points
         * is not repainted sixty times a second on a phone. It goes between
         * the photo and the page, so it is part of the base a page's eraser
         * reveals (makeCompositor), never ink it cuts. */
        if (underPage && idx >= underPage.from && idx <= underPage.to) {
          if (!underPageCv) {
            var fu = flipFrames[underPage.page];
            underPageCv = global.document.createElement('canvas');
            underPageCv.width = canvas.width; underPageCv.height = canvas.height;
            var uctx = underPageCv.getContext('2d');
            uctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
            if (fu && fu.strokes && fu.strokes.length) paintStatic(uctx, fu.strokes, underPageCv, pixelRatio);
          }
          ctx.save();
          ctx.setTransform(1, 0, 0, 1, 0, 0);
          ctx.drawImage(underPageCv, 0, 0);
          ctx.restore();
        }
        var fr = flipFrames[idx];
        if (fr && fr.strokes && fr.strokes.length) {
          /* A DRAWING PAGE REVEALS, and dueCount() owns how much — the same
           * answer the editor and the /s/ player get, from the same module, so
           * all three agree about what a viewer sees.
           *
           * BRANCH ON THE PAGE, NOT ON THE PROGRESS. displayAt() returns 0
           * for two different pages: a still one, which has no progress, and a
           * drawing one at the instant it starts. Testing `progress > 0` read
           * the first frame of every reveal as still and painted the FINISHED
           * picture, which then wiped and redrew from nothing — while the same
           * page revealed cleanly in the editor and in /s/. drawOf() is the
           * question actually being asked.
           *
           * DO NOT NAME A LOCAL `prog` IN HERE: that is the progress ELEMENT
           * of this closure (see below), and `var` is function-scoped, so a
           * local by that name shadows it for the whole of render() —
           * including the replay branch, which then threw on undefined.style
           * and was swallowed by the load path's catch as "Couldn't load this
           * Skribl". A flip-only edit broke every REPLAY post on the feed. */
          if (H && H.drawOf(fr)) {
            var n = H.dueCount(fr, shown.progress);
            if (n) paintStatic(ctx, fr.strokes.slice(0, n), canvas, pixelRatio);
          } else {
            paintStatic(ctx, fr.strokes, canvas, pixelRatio);
          }
        }
        setNib(null);
      } else {
        /* THE COMPOSITOR HAS TO OUTLIVE THE FRAME. The replay path is
         * incremental — it appends the points that have come due and leaves
         * the rest of the canvas alone, which is what makes it cheap — so a
         * compositor built per frame would re-seed its dry layer from the
         * visible canvas every time and bake the in-progress stroke on every
         * tick, which is the beading it exists to prevent. Built once per full
         * repaint, and `full` is exactly the set of things that move time
         * backwards: start, seek, loop, resize. */
        if (full) {
          /* FROM THE NEAREST COPY, NOT FROM ZERO (lib/seekcache.js, the v322
           * plan's step 3 for the editors and /s/<id>). A scrub may carry on
           * from where the canvas stands; anything else that repaints starts
           * from a copy at or before `at`, or from nothing as it always did. */
          var SC = global.SkriblSeekCache;
          if (SC && !seekCache && timeline.length) seekCache = SC.make(canvas, timeline, { source: seekSource, put: seekPut });
          var s = seekCache && seekCache.start(seekCache.indexAt(at), jump && drawn > 0 ? drawn : null, ctx);
          if (s) drawn = s.index;   // put() rebuilt the compositor if it restored a copy
          else { clear(); drawn = 0; comp = makeCompositor(ctx, canvas, timeline, pixelRatio); }
          drewFrom = drawn;
          /* A FAR FIRST JUMP RACES THERE, a slice a frame, through the same
           * replayTo to the same points; the bar and the line say where it is
           * going at once (below). Only a jump: an idle poster, a resize or a
           * loop repaints at once, as it always did. */
          var to = jump && seekCache ? seekCache.indexAt(at) : 0;
          if (to && seekCache.far(drawn, to)) {
            racer = SC.race(drawn, to, function (i, j) {
              return (drawn = replayTo(ctx, timeline, i, j < to ? timeline[j - 1].playT : at, comp, seekCache));
            }, function () {}, landed);
          }
        }
        if (!racer) {
          drawn = replayTo(ctx, timeline, drawn, at, comp, seekCache);
          if (comp && drawn >= timeline.length) comp.finish();
        }
        setNib(state === 'playing' && drawn > 0 && drawn < timeline.length
               ? timeline[drawn - 1] : null);
      }
      prog.style.width = (totalMs ? Math.min(1, at / totalMs) * 100 : 0) + '%';
      paintLine();
    }

    function landed() {
      racer = null;
      if (queued) { queued = false; play(); }
    }
    /* What the box shows: playing, or paused. */
    function look(on) {
      if (size) canvas.hidden = false;
      el.classList.toggle('is-playing', on);
      el.classList.toggle('is-paused', !on);
    }

    /* ---- the line ------------------------------------------------------- */

    function paintLine() {
      if (!scrubUI) return;
      var f = frac();
      scrubUI.paint(f);
      if (global.SkriblScrub) global.SkriblScrub.sync(bar, f);
    }

    function curMs() { return state === 'playing' ? elapsed + segElapsed() : elapsed; }

    /* WHERE THE REPLAY IS, 0..1, as the scrubber shows it. A replay is its
     * clock over its length. A FLIP IS ITS PAGES: one equal segment each, the
     * playhead moving through a page's segment as that page's time passes,
     * because a page is what a viewer aims at and a held page or a long
     * drawing page would otherwise squeeze the rest to slivers. A forever
     * loop's clock wraps inside its stretch (lib/holdtiming.js), so its
     * playhead circles those pages and never goes back to page 1. */
    function frac() {
      if (!payload || !totalMs) return 0;
      var t = curMs();
      if (!flipFrames || !flipPlan) return Math.max(0, Math.min(1, t / totalMs));
      var P = flipPlan, n = flipFrames.length;
      if (P.forever && t >= P.introMs) t = P.introMs + ((t - P.introMs) % P.stretchMs);
      else if (t >= P.cycle) return 1;
      var lo = 0, hi = P.slots.length - 1;
      while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (P.starts[mid] <= t) lo = mid; else hi = mid - 1; }
      var i = P.slots[lo] | 0;
      return Math.max(0, Math.min(1, (i + Math.min(1, (t - P.starts[lo]) / (P.ms[i] || 1))) / n));
    }

    /* ...and back: a place on the scrubber -> the clock. A Flip's page plays
     * from its first slot; a page a forever loop never reaches lands on the
     * last one that plays. */
    function msAt(f) {
      f = Math.max(0, Math.min(1, f));
      if (!flipFrames || !flipPlan) return f * totalMs;
      var P = flipPlan, n = flipFrames.length, pg = Math.min(n - 1, Math.floor(f * n));
      var s = P.slots.indexOf(pg), into = f * n - pg;
      if (s < 0) { for (s = P.slots.length - 1; s > 0 && P.slots[s] > pg; s--); into = 1; }
      return Math.min(P.starts[s] + into * (P.ms[P.slots[s]] || 0), Math.max(0, totalMs - 1));
    }

    /* A DRAG ON THE SCRUBBER: hold the replay, show each place asked for,
     * carry on from the last one if it was playing. The drawing may not be
     * here yet -- a viewer can grab the line of a post nobody has played --
     * so the first touch asks for it and the last place is shown when it
     * comes. A poster gives way to the canvas as soon as there is a place. */
    function scrubStart() {
      held = state === 'playing' || queued;
      if (held) pause();
      if (!payload) load().then(function (p) { if (p && pendingF != null) scrubTo(pendingF); });
    }
    function scrubTo(f) {
      if (!payload) { pendingF = f; return; }
      pendingF = null;
      if (state === 'playing') pause();
      if (state === 'idle') { state = 'paused'; el.classList.add('is-paused'); }
      elapsed = msAt(f);
      render(elapsed, true, true);
    }
    function scrubEnd() {
      if (held) { held = false; play(); }
    }

    /* A FLIP'S PAGES IN THE SCRUBBER, equal widths: a page is what a viewer
     * aims at, and a held page or a long drawing page would otherwise squeeze
     * the rest to slivers. Played pages are solid, the one on screen fills to
     * the playhead, the rest are faded like unplayed columns. Painted here,
     * through lib/replayline.js's `draw` hook, so the Pad and /s/<id> do not
     * carry it. A replay answers false and gets the module's columns. */
    function pageCount() { return flipFrames ? flipFrames.length : payload ? 0 : pagesN; }
    function drawPages(x, f, W, H, dpr) {
      var n = pageCount();
      if (!n) return false;
      var at = f * W, g = Math.min(3 * dpr, W / n * 0.25), sw = (W - g * (n - 1)) / n,
          h = Math.round(H * 0.44), y = (H - h) / 2, r = Math.min(3 * dpr, sw / 2, h / 2);
      function seg(sx, a) {
        x.globalAlpha = a;
        x.beginPath();
        if (x.roundRect) x.roundRect(sx, y, sw, h, r); else x.rect(sx, y, sw, h);
        x.fill();
      }
      for (var p = 0; p < n; p++) {
        var sx = p * (sw + g), fill = Math.max(0, Math.min(sw, at - sx));
        seg(sx, 0.36);
        if (fill > 0) { x.save(); x.beginPath(); x.rect(sx, 0, fill, H); x.clip(); seg(sx, 1); x.restore(); }
      }
    }

    function pick(c) {
      choice = c; picked = true;
      applyRate(c === 'fit' ? Math.max(1, (payload ? totalMs : info && info.play || 0) / 30000) : +c || 1);
    }

    /* The nib rides in the BOX's coordinate space while the point is in the
     * DRAWING's, and the canvas is letterboxed between them, so this maps
     * through the live rects rather than assuming they are the same box.
     * Getting it wrong puts the pen next to the line instead of on it.
     *
     * AND THE CANVAS ELEMENT IS NOT ALWAYS THE DRAWING. Two sizing models:
     *
     *   tile       width/height auto under max-width/max-height 100%, so the
     *              ELEMENT box is exactly the drawing and a rect is enough.
     *   immersive  width/height 100% with `object-fit: contain`, so the element
     *              box is the whole container and the bitmap is letterboxed
     *              INSIDE it. getBoundingClientRect() reports the container.
     *
     * Read the element box in immersive and the nib is mapped across the whole
     * screen while the line is drawn across the smaller contained box, so it
     * sits up and to the left of its own stroke. `object-fit` has to stay:
     * max-width only ever SHRINKS a canvas and full screen needs it to grow.
     * So derive the CONTENT box instead -- the same arithmetic `contain` does.
     * It reduces to the element box in tile mode (equal scales, zero offsets),
     * so one mapping serves both and a third sizing model cannot break it. */
    /* THE NIB IS A SIZE IN THE PEN. A fixed 8px of CSS is a boulder on an 84px
     * library thumb and a speck on a 1280px full screen; scaling it by the
     * drawing's scale alone makes a ball in full screen. A nib is the tip of a
     * pen, so its size is the PEN's size rendered: `p.size * s` is exactly how
     * wide the stroke it is drawing comes out on this screen, and a little over
     * that is a tip leading its own line. It answers to the scale (a thumb
     * renders the stroke small, so the bead is small) and to the pen, and it
     * cannot be out of proportion with the line it is making because it is
     * DEFINED against that line.
     *
     * THE CLAMP IS A GUARD, NOT A RANGE. A ceiling low enough to be a range
     * catches ordinary big pens -- a 22px pen renders 32px wide in full screen
     * -- and hands back a bead SMALLER than its own stroke, which is the rule
     * broken by the thing protecting it. A rule defined against the stroke does
     * not need protecting from big strokes. The floor is what earns its place:
     * a hairline on an 84px thumb renders under two pixels, and a two-pixel dot
     * is dirt on the screen. The ceiling is only so a pathological payload
     * cannot paint the whole card.
     *
     * Applied only when it MOVES: this runs on every frame of every replay and
     * the pen changes at a stroke boundary, not at a frame. */
    var nibAt = -1;
    function nibSize(w) {
      if (w === nibAt) return;
      nibAt = w;
      nib.style.setProperty('--nb', Math.max(4, Math.min(64, 1.4 * w)) + 'px');
    }

    function setNib(p) {
      var st = nib.style;
      if (!p) { st.opacity = '0'; return; }
      var cr = canvas.getBoundingClientRect(), br = el.getBoundingClientRect();
      if (!cr.width || !cr.height) { st.opacity = '0'; return; }
      var s = Math.min(cr.width / size.w, cr.height / size.h);
      nibSize((p.size || 8) * s);
      /* THE NIB TAKES THE INK IT IS LAYING DOWN. A white dot whatever colour
       * the pen is reads as a cursor hovering over the drawing rather than as
       * the pen making it, and the shared-link player has tinted its bead since
       * it was written (app.js's nibRGB).
       *
       * The colour goes in raw and the SHEET handles the awkward part: a stroke
       * may carry alpha, and a half-transparent bead over a dark canvas is
       * barely there. inlineplayer.css lays the ink over an opaque white base,
       * so a faint pen gives a pale nib rather than a ghost -- the same intent
       * as the other player's alpha strip, without a colour parser in a file a
       * host pays for by the byte.
       *
       * AND THE INK NEEDS SEPARATING FROM ITSELF. A tip the colour of the
       * stroke under it disappears into that stroke and reads as a slightly
       * thicker bit of line. A hard two-tone hairline separates them and looks
       * like a cursor doing it; a BLURRED halo of the same ink adds light over
       * the stroke instead of drawing a line across it, so the tip is the
       * brightest point on its own line and nothing foreign was introduced to
       * make it so.
       *
       * AND IT HAS TO BLOOM PAST THE STROKE TO DO ANY OF THAT. 6px of blur at
       * 55% on a 12px stroke of the same colour is invisible -- rendered and
       * looked at, not reasoned about. 8px of blur and 3px of spread at 90%
       * puts the glow's edge outside the line it is ending. Below that it is
       * not a glow, it is the stroke.
       *
       * Erasing keeps the neutral bead: there is no ink to take. */
      st.setProperty('--nib-c', (!p.erase && p.color) || '#fff');
      st.left = cr.left - br.left + (cr.width - size.w * s) / 2 + p.x * s + 'px';
      st.top = cr.top - br.top + (cr.height - size.h * s) / 2 + p.y * s + 'px';
      st.opacity = '1';
    }

    /* ---- audio ---------------------------------------------------------- */

    function ensureCtx() {
      if (audioCtx) return audioCtx;
      var AC = global.AudioContext || global.webkitAudioContext;
      if (!AC) return null;
      try { audioCtx = new AC(); } catch (e) { audioCtx = null; }
      return audioCtx;
    }

    function startAudio() {
      if (!music || !music.data) return;
      var ac = ensureCtx();
      if (!ac) return;
      if (ac.state === 'suspended' && ac.resume) ac.resume();
      if (!buffer) {
        if (decoding) return;
        decoding = true;
        global.fetch(music.data)
          .then(function (r) { return r.arrayBuffer(); })
          .then(function (ab) { return ac.decodeAudioData(ab); })
          .then(function (b) {
            decoding = false;
            buffer = b;
            if (state === 'playing') startAudio();
          })
          /* A Skribl whose audio will not decode still plays. Silence is a
           * degradation; a dead box is a bug. */
          .catch(function () { decoding = false; });
        return;
      }
      stopAudio();
      /* loop = true on the buffer source, NOT <audio loop>: the posted clip IS
       * the loop (editor_post.js bakes the trim and folds the crossfade in at
       * post time), and a media element's loop leaves an audible gap at the
       * join that the whole seam assertion in verify_audio.py exists to keep
       * out. The clip is at its source rate and the context is at the device
       * rate, so decodeAudioData may resample — see the 22.05 kHz note in
       * lib/postedaudio.js for why that matters and why the clip is not
       * downsampled before it gets here. */
      srcNode = ac.createBufferSource();
      srcNode.buffer = buffer;
      srcNode.loop = true;
      /* A clip at its own rate under a 2x drawing drifts a whole take out of
       * sync, and a drawing that finishes while its music is halfway through is
       * worse to watch than a chipmunk. One playback's rate; the stored clip is
       * untouched. */
      try { srcNode.playbackRate.value = rate; } catch (e) {}
      gainNode = ac.createGain();
      gainNode.gain.value = soundOn() ? 1 : 0;
      srcNode.connect(gainNode);
      gainNode.connect(ac.destination);
      srcNode.start(0);
    }

    function stopAudio() {
      if (srcNode) { try { srcNode.stop(0); } catch (e) {} try { srcNode.disconnect(); } catch (e) {} }
      if (gainNode) { try { gainNode.disconnect(); } catch (e) {} }
      srcNode = gainNode = null;
    }

    /* A state class goes on the box AND the line, which holds the controls
     * the class styles now (v322). */
    function mark(c, on) {
      el.classList.toggle(c, on);
      if (line) line.classList.toggle(c, on);
    }

    function applyLoop() {
      mark('is-noloop', !looping);
      if (!loopBtn) return;
      loopBtn.setAttribute('aria-pressed', looping ? 'true' : 'false');
      loopBtn.setAttribute('aria-label', looping ? 'Stop repeating' : 'Repeat');
      loopBtn.title = looping ? 'Repeating' : 'Plays once';
    }

    function setLooping(on) {
      looping = !!on;
      applyLoop();
      /* Turning it back ON while the replay is sitting finished starts it
       * again — otherwise the button appears to do nothing until the next tap,
       * which reads as broken. */
      if (looping && state !== 'playing' && elapsed >= totalMs && totalMs) {
        elapsed = 0;
        play();
      }
    }

    function applySound() {
      var on = soundOn();
      mark('is-muted', !on);
      if (muteBtn) {
        muteBtn.setAttribute('aria-pressed', on ? 'false' : 'true');
        muteBtn.setAttribute('aria-label', on ? 'Mute' : 'Unmute');
        muteBtn.title = on ? 'Sound is on' : 'Sound is off';
      }
      if (gainNode) gainNode.gain.value = on ? 1 : 0;
    }

    /* ---- transport ------------------------------------------------------ */

    /* THE VIEWER'S SPEED, and only the CLOCK is scaled -- the stored `t` values
     * are the artifact and are never touched, so watching slowly cannot rewrite
     * the timing somebody drew. Everything downstream (the flip hold table, the
     * stroke timeline, the progress fraction) keeps working off the scaled
     * elapsed without knowing a rate exists, which is the same shape app.js
     * uses for the Pad's preview and for /s/.
     *
     * Per PLAYER, not per page: a feed scrolls past twenty of these and a rate
     * chosen on one is not a statement about the next. The full-screen bar is
     * where it is offered (lib/fullbar.js); a post in a feed still has two
     * controls and no transport. */
    function segElapsed() { return (now() - t0) * rate; }

    function frame() {
      var at = elapsed + segElapsed();
      /* A FOREVER loop never ends and never starts over: past one pass the
       * clock wraps inside the stretch, whatever this post's loop switch says
       * (the stretch is meant to keep going for as long as it is on screen). */
      if (flipPlan && flipPlan.forever && at >= totalMs) {
        elapsed = flipPlan.introMs + ((at - flipPlan.introMs) % flipPlan.stretchMs);
        t0 = now();
        render(elapsed, false);
        raf = global.requestAnimationFrame(frame);
        return;
      }
      if (at >= totalMs) {
        /* Both kinds loop by DEFAULT, for different reasons: a Flip document IS
         * a loop, and a Pad replay that stopped dead on the finished drawing
         * reads as a broken GIF. The viewer can turn it off per post. */
        if (!looping) {
          render(totalMs, false);
          /* WHEN THE DRAWING STOPS, THE MUSIC STOPS. pause() takes the audio
           * down with the replay — one call, so the two cannot come apart —
           * and that coupling is the whole point of routing the end of a
           * non-looping replay through it rather than just cancelling the rAF.
           * A loop still playing under a drawing that has finished is a post
           * that will not shut up, which is worse than one that never started.
           */
          pause();
          /* Settled at the END, not back at the start: someone who asked it not
           * to loop wants to look at the finished drawing. pause() computes
           * elapsed from the clock, so pin it after. */
          elapsed = totalMs;
          return;
        }
        elapsed = 0;
        t0 = now();
        render(0, true);
        raf = global.requestAnimationFrame(frame);
        return;
      }
      render(at, false);
      raf = global.requestAnimationFrame(frame);
    }

    function play() {
      if (failed === 'retry') unfail();
      if (failed) return;
      if (!payload) {
        load().then(function (p) { if (p) play(); });
        return;
      }
      if (state === 'playing') return;
      /* One post plays at a time. An AMBIENT player (How it works' silent
       * examples, attach(el, p, { ambient: true })) is outside that rule both
       * ways: it stops nothing when it starts, and a post starting does not
       * stop it, so a panel of examples can loop together. */
      if (!me.ambient) for (var i = 0; i < players.length; i++) if (players[i] !== me && !players[i].ambient) players[i].settle();
      /* Mid-race the drawing is not where it was pointed yet, and the first
       * frame would draw the rest of the way at once: the freeze the race is
       * there to avoid. The box says it plays now, the sound is unlocked now,
       * inside the tap, and landed() comes back here. */
      if (racer) {
        queued = true;
        if (state === 'idle') state = 'paused';
        look(true);
        if (music) { var ac = ensureCtx(); if (ac && ac.resume) ac.resume(); }
        return;
      }
      if (elapsed >= totalMs) elapsed = 0;
      /* Always a full repaint from zero when starting at zero — posterless, the
       * canvas is currently holding the FINISHED drawing (renderIdle), and the
       * incremental path only ever appends. */
      if (elapsed === 0) render(0, true);
      state = 'playing';
      look(true);
      t0 = now();
      raf = global.requestAnimationFrame(frame);
      startAudio();
    }

    function pause() {
      if (queued) { queued = false; look(false); }
      if (state !== 'playing') return;
      elapsed += segElapsed();
      if (raf) global.cancelAnimationFrame(raf);
      raf = null;
      state = 'paused';
      look(false);
      setNib(null);
      stopAudio();
    }

    /* Settle is not pause: a post the viewer scrolled past, or one displaced by
     * another, goes back to being a post — poster showing, progress at zero —
     * rather than sitting frozen mid-stroke behind a play button. */
    function settle() {
      if (state === 'idle') return;
      pause();
      state = 'idle';
      elapsed = 0;
      el.classList.remove('is-paused');
      prog.style.width = '0';
      /* Back to rest, the card on top: the canvas at time zero is the blank
       * page (the owner's iPhone: "scrolled out of sight then come back and
       * blank screen"). look() brings it back on the next play. */
      if (hasPoster) canvas.hidden = true;
      if (payload) renderIdle();
    }

    el.addEventListener('click', function (e) {
      /* A tap on the player is the player's. skribls.net makes a whole post a
         link (article[data-href]) and exempts only a, button, video, audio and
         .video-embed; this box is a div, so the tap started playback and then
         navigated to the post page (v316, the real profile page). */
      e.stopPropagation();
      if (muteBtn && muteBtn.contains(e.target)) return;
      me.toggle();
    });

    el.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
      e.preventDefault();                 /* Space scrolls the feed otherwise */
      me.toggle();
    });

    if (muteBtn) {
      muteBtn.addEventListener('click', function (e) {
        e.stopPropagation();              /* not a play/pause tap */
        setSoundOn(!soundOn());
      });
    }

    if (loopBtn) {
      loopBtn.addEventListener('click', function (e) {
        e.stopPropagation();              /* not a play/pause tap */
        setLooping(!looping);
      });
    }

    /* THE DRAWING'S SHAPE, if the page knows it (v309). Absent -- an old row,
     * a payload with no canvasSize, a host that has not passed it through --
     * the box stays 16:9 and the stylesheet's band crop stands. A POST (the
     * box with a line) TAKES THAT SHAPE (v322): no bars beside the drawing,
     * and the poster's drawing fills it. The macro writes the same when it
     * is given the size; a page that clones it fills the size in after.
     * me.shape(on) switches later, framing the poster again (gallery.js). */
    var pw = +el.getAttribute('data-skribl-w');
    var ph = +el.getAttribute('data-skribl-h');
    me.shape = function (on) {
      var s = el.style, ok = pw > 0 && ph > 0;
      on = !!on && ok;
      s.aspectRatio = on ? pw + '/' + ph : '';
      s.setProperty('--skribl-ar', on ? (pw / ph).toFixed(5) : '');
      el.classList.toggle('is-shaped', on);
      if (poster && ok) fitPoster(poster, pw, ph, on ? pw / ph : 0);
    };
    /* A post whose card 404s (a store that lost the thumbnail, a host without
     * the card route) must not show a broken-image glyph in the feed. */
    if (poster) poster.addEventListener('error', function () { poster.hidden = true; });
    me.shape(line);

    /* THE LINE, built once its module is here. Before the drawing arrives it
     * says what the listing said (`line` and `pages`) and shows the stored
     * shape; after, it reads the drawing, and keeps the stored shape so the
     * bars under the thumb do not change at the first tap. */
    try { info = JSON.parse(el.getAttribute('data-skribl-line') || 'null'); } catch (e) { info = null; }
    if (!info || typeof info !== 'object') info = null;
    /* No line under it (the Gallery's cards): the play button says it. */
    var says = !line && RL && info && playEl && (info.pages > 1 ? info.pages + ' pages' : info.drawn > 0 ? 'drawn in ' + RL.words(info.drawn) : '');
    if (says) { playEl.insertAdjacentHTML('beforeend', '<span>' + says + '</span>'); mark('is-says', true); tone(); }
    /* THE PILL IS GLASS, and the glass is dark or light by the drawing under
     * it (the owner's pick D after v324): the card's lower-left, where the
     * pill sits, read off the card already on screen. A card that cannot be
     * read (another origin's, say) keeps the light glass. */
    function tone() {
      if (!poster) return;
      if (!poster.naturalWidth) { poster.addEventListener('load', tone, { once: true }); return; }
      var px = readArea(0, 0.7, 0.5, 0.3, 8, 8), L = 0;
      if (!px) return;   // tainted or unreadable: the light glass
      for (var j = 0; j < px.length; j += 4) L += 0.2126 * px[j] + 0.7152 * px[j + 1] + 0.0722 * px[j + 2];
      mark('is-says-dark', L / 64 < 115);
    }
    /* THE DRAWING, READ: a box of it (shares of the drawing's own rectangle)
     * into a cw x ch sample on white, as a see-through drawing shows. Off the
     * canvas while it is the one showing, else off the card already on
     * screen; null when there is nothing to read yet, or it cannot be read
     * (another origin's). The pill's glass and the card's fade both look
     * here (ground() below), so the two cannot read one drawing two ways. */
    function readArea(x, y, w, h, cw, ch) {
      var live = payload && !canvas.hidden, src = live ? canvas : poster;
      if (!src || !(live || src.naturalWidth)) return null;
      try {
        var d = live ? [0, 0, canvas.width, canvas.height] : poster._d || [0, 0, CARD_W, CARD_H],
            k = live ? 1 : poster.naturalWidth / CARD_W, c = doc.createElement('canvas'), g;
        c.width = cw; c.height = ch;
        g = c.getContext('2d');
        g.fillStyle = '#fff'; g.fillRect(0, 0, cw, ch);
        g.drawImage(src, (d[0] + d[2] * x) * k, (d[1] + d[3] * y) * k, d[2] * w * k, d[3] * h * k, 0, 0, cw, ch);
        return g.getImageData(0, 0, cw, ch).data;
      } catch (e) { return null; }
    }
    if (line && RL) {
      pagesN = info && info.pages > 1 ? info.pages | 0 : 0;
      shapeCols = info && shapeOf(info.shape);
      /* The listing knows whether there is sound, so mute holds its place
       * from the first paint and the row does not change at the first tap. */
      if (info && typeof info.sound === 'boolean') mark('is-silent', !info.sound);
      if (info) { choice = RL.fromPost(info.speed, info.drawn); rate = RL.rate(choice, info.play); }
      bar = line.querySelector('.skribl-inline-scrub');
      var say = line.querySelector('.skribl-inline-say');
      if (bar) {
        scrubUI = RL.scrub(bar, {
          points: function () { return (!flipFrames && timeline) || []; },
          total: function () { return payload ? totalMs : info ? info.play : 0; },
          map: function () { return clockFn; },
          frac: frac, seek: scrubTo, start: scrubStart, end: scrubEnd,
          shape: function () { return shapeCols; },
          draw: drawPages,
          tip: function (f) { var n = pageCount(); return n ? 'Page ' + Math.min(n, Math.floor(f * n) + 1) + ' of ' + n : ''; }
        });
        if (global.SkriblScrub) global.SkriblScrub.attach(bar, { seek: function (f) { scrubStart(); scrubTo(f); scrubEnd(); }, frac: frac });
      }
      if (say) {
        lineUI = RL.attach(say, {
          choice: function () { return choice; },
          pick: pick,
          playMs: function () { return payload ? totalMs : info ? info.play : 0; },
          drawnMs: function () { return payload ? drawnMs : info ? info.drawn : null; },
          lead: function () {
            var n = flipFrames ? flipFrames.length : payload ? 0 : pagesN;
            return n > 1 ? '<b>' + n + ' pages</b><span class="rl-m"> · </span>' : '';
          }
        });
        var fit0 = say.querySelector('[data-r="fit"]');
        if (fit0) fit0.hidden = pagesN > 1;
      }
      /* A tap on the line is the line's: a host that makes the whole post a
       * link must not navigate on a scrub or a speed. */
      line.addEventListener('click', function (e) { e.stopPropagation(); });
      line.classList.add('is-on');
      paintLine();
      /* At rest nothing else paints it, so a line laid out late (a host
       * revealing the post, a font arriving) paints when its size lands. */
      if (bar && global.ResizeObserver) new global.ResizeObserver(function () { paintLine(); }).observe(bar);
    }

    applySound();
    applyLoop();
    return me;
  }

  /* ---- mounting ---------------------------------------------------------- */

  /* Off-screen posts pause, and carry on when they come back. Without the
   * pause, scrolling away from a playing Skribl leaves it drawing and looping
   * into a viewport nobody is looking at — the battery cost of a feed
   * autoplaying forever, paid for nothing. It PAUSED rather than reset until
   * after v324: it was settled back to the start, and the owner scrolled a
   * drawing past and lost it ("It goes away even if it's playing and I scroll
   * it out of view"). A post another one stopped meanwhile stays stopped.
   * Guarded because IntersectionObserver is the one API here a very old
   * browser may lack, and its absence should cost a behaviour, not the
   * player. */
  var io = null;
  if (global.IntersectionObserver) {
    io = new global.IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var p = entries[i].target._skriblInline;
        if (!p) continue;
        if (!entries[i].isIntersecting) {
          if (p.state().state === 'playing') { p.pause(); p.away = 1; }
        } else if (p.away) {
          p.away = 0;
          if (p.state().state === 'paused') p.play();
        }
      }
    }, { threshold: 0.1 });
  }

  function mount(root) {
    var scope = root || doc;
    /* Only boxes that name a post. A draft's box carries data-skribl-inline
     * too — api.attach put it there — but no id, and re-mounting it would give
     * it a second player object for the same element. attach() guards against
     * that with _skriblInline, but the selector is the honest place to say
     * mount() is for POSTED skribls. */
    var found = scope.querySelectorAll('[data-skribl-inline][data-skribl-id]');
    var out = [];
    for (var i = 0; i < found.length; i++) {
      var p = attach(found[i]);
      if (p) { out.push(p); if (io) io.observe(found[i]); }
    }
    return out;
  }

  var api = {
    mount: mount,
    /* A DRAFT'S SKRIBL, which has no id because it is not posted yet.
     *
     * The host's composer holds a payload (editor_compose.js hands it back) and
     * has to show it inline while the author is still writing the post. Showing
     * a thumbnail there and the real player after posting means the composer is
     * previewing something other than what it will publish — the "preview is
     * not the product" failure this project keeps finding. So the same player
     * takes the payload directly: no id, no poster, no fetch, everything else
     * identical because it is the same code path from adopt() down.
     */
    attach: function (el, payload, opts) {
      el.setAttribute('data-skribl-inline', '');
      /* No id means load() can never run, which is the point: there is nothing
       * on the server to fetch. */
      el.removeAttribute('data-skribl-id');
      /* A draft has no card to show, so the poster element is removed rather
       * than hidden — attach() then knows this box is posterless and paints the
       * finished drawing as its idle state. */
      var poster = el.querySelector('.skribl-inline-poster');
      if (poster) poster.parentNode.removeChild(poster);
      var p = attach(el);
      if (p) { p.ambient = !!(opts && opts.ambient); p.maxDpr = (opts && opts.maxDpr) || 0; if (io) io.observe(el); p.adopt(payload); }
      return p;
    },
    stopAll: function () { for (var i = 0; i < players.length; i++) players[i].settle(); },
    soundOn: soundOn,
    setSoundOn: setSoundOn,
    /* verify_inline.py drives the page through this rather than through the
     * DOM, so an assertion names a state and not a class name. */
    players: function () { return players; },
    find: function (id) {
      if (!id) return null;      /* a draft has no id; do not match nulls */
      for (var i = 0; i < players.length; i++) {
        if (players[i].state().id === id) return players[i];
      }
      return null;
    }
  };
  global.SkriblInline = api;

  if (doc) {
    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', function () { mount(); });
    } else {
      mount();
    }
  }
})(typeof window !== 'undefined' ? window : this);
