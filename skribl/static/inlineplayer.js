/* THE IN-POST PLAYER. What a Skribl looks like inside somebody else's feed.
 *
 * ===========================================================================
 * WHY THIS EXISTS SEPARATELY FROM THE PLAYER AT /s/<id>
 * ===========================================================================
 *
 * The sealed player is a PAGE: app.js plus eight shared modules, ~150 KB of
 * JavaScript, a full app shell, a transport with scrub and loop and speed, and
 * a brand moment that draws itself on load. That is right for a shared link,
 * where the Skribl is the whole reason the tab is open. It is wrong for a feed,
 * where twenty posts are on screen, nineteen of them are not Skribls, and the
 * one that is has to behave like an image that happens to move.
 *
 * ===========================================================================
 * WHAT THE STYLESHEET USED TO SAY, AND WHY IT SAYS IT HERE NOW (v308)
 * ===========================================================================
 *
 * jsstrip.py removes these comments from the response; nothing does that for
 * CSS, so every word in inlineplayer.css is downloaded by every host on every
 * page that embeds a Skribl. The file's own header has said so since the
 * poster crop landed, and 42% of it had become comments anyway. The line that
 * decides what goes where is NOT length, it is audience: a host reads that
 * stylesheet before overriding something, so the tokens, the geometry numbers
 * and the defensive declarations stay there. PRODUCT reasoning — why the
 * component behaves as it does — belongs here, and this is it.
 *
 * TWO VIEWER CONTROLS, AND ONLY TWO: mute and loop. Scrub, speed and
 * frame-step still belong on the full player at /s/<id> — a post that grows a
 * transport stops being a post — but these two are about whether the thing in
 * front of you keeps making noise and keeps moving, which is the viewer's
 * business in a way that seeking is not.
 *
 * They share one cluster at bottom left so a post has one control area rather
 * than two, and so a silent Skribl (which hides mute) does not leave a lone
 * button floating in the corner.
 *
 * LOOP IS ON BY DEFAULT, so the lit state is the RESTING state and the button
 * dims when it is switched OFF — the opposite of mute, whose resting state is
 * muted. Each reads as "what is currently true", not "what this button does".
 *
 * A SILENT SKRIBL HAS NOTHING TO MUTE, so it shows no mute button at all
 * rather than a control that does nothing. Loop stays: a silent drawing still
 * repeats.
 *
 * And the poster's arithmetic, which the stylesheet now states once instead of
 * twice: auto width keeps the card's 1200:630, making the image 2.439x the box
 * height against a 1.778x box, and the centred excess is clipped.
 *
 * So this is a second, much smaller thing, and the honest way to describe it is
 * that it is a SECOND IMPLEMENTATION of playback. This project has a name for
 * that shape and a suite for it: verify_sharedrules.py exists because "the
 * editor and the player disagreeing is uniquely expensive, since nothing an
 * author can see reveals it". A feed player that drifts from the shared link is
 * the same defect one surface further out — the author checks /s/<id>, it looks
 * right, and everyone else sees something else.
 *
 * Three things keep that from happening, in descending order of strength:
 *
 *   1. THE RULES COME OUT OF lib/. Per-page holds are read through
 *      lib/holdtiming.js — the module that exists precisely so the editor and
 *      the player cannot disagree about which page is on screen at time t. This
 *      file asks it the same question app.js asks it. The default canvas size
 *      for a payload that carries none comes from lib/canvassizes.js the same
 *      way. Neither rule is retyped here.
 *   2. WHAT IS RETYPED IS RETYPED VERBATIM, AND SAYS SO. The gap cap and the
 *      timeline build below are app.js's buildPlaybackTimeline(); the two
 *      drawing primitives are its drawDot/drawLine. Each carries a pointer to
 *      the original. They are ~30 lines in total and were NOT extracted into a
 *      lib module, deliberately: doing that adds a fetched file to the player's
 *      critical path, and verify_player_isolation.py's JS ratchet had 1,755 B
 *      of headroom when this was written. Paying that so a feed page can share
 *      thirty lines is the wrong trade.
 *   3. harness/verify_inline.py ASSERTS THE ANSWERS MATCH. It posts one real
 *      drawing, plays it in the sealed player and here, and compares the
 *      reported durations and the rendered pixels at matched offsets. That is
 *      the mechanism verify_sharedrules.py uses and the reason it is trusted:
 *      "what is asserted is not shared code but that they cannot disagree about
 *      the ANSWER."
 *
 * ===========================================================================
 * WHAT IT PLAYS, AND WHAT IT DELIBERATELY DOES NOT
 * ===========================================================================
 *
 * PLAYS:  Pad replay documents (strokes drawn over time), Flip documents (page
 *         per frame, holds honoured through lib/holdtiming.js), the background
 *         colour, a photo or base-snapshot underlay, and the posted audio loop.
 *
 * ALSO PLAYS, SINCE v279: the wet/dry stroke compositor (makeCompositor
 *         below, app.js's makeStrokeCompositor in miniature). This block said
 *         "DOES NOT" for twenty-odd releases after it did — a stroke below
 *         100% opacity is composited once here, not stamped — and ended with
 *         "if this ever gets the compositor, that fixture is where to widen
 *         the proof", which is what v279 did and this paragraph did not
 *         follow. verify_inline.py pins it by rendering the same translucent
 *         drawing twice, once with the compositor disabled at source.
 *
 * NO KNOWN FIDELITY GAP, and the last one closed is worth naming because it
 *         survived so long: until v305 the canvas was given a definite CSS
 *         width AND height, so the box's max-width/max-height clamped each
 *         axis on its own and every drawing that is not 16:9 was STRETCHED —
 *         216% on a 9:16 one. See adopt(). A gap in the SHAPE of the drawing
 *         outlived a gap in its shading because nothing measured the aspect.
 *
 * ===========================================================================
 * THE PRODUCT RULES, WHICH ARE NOT ARBITRARY
 * ===========================================================================
 *
 * ONE AT A TIME. Starting any Skribl settles every other one on the page. A
 * feed that can play two loops at once is a feed nobody scrolls twice.
 *
 * SOUND OFF BY DEFAULT, AND THE CHOICE IS THE VIEWER'S. Muted is the only
 * defensible default for media that starts on a tap in a public place, and
 * unmuting one post unmutes all of them for the session (sessionStorage, not
 * localStorage: a preference set in a feed should not follow someone into next
 * week).
 *
 * REPEATING IS ALSO THE VIEWER'S, but PER POST rather than page-wide. Sound is
 * environmental; repeating is a property of the drawing in front of you, and a
 * two-second loop you want to watch twice says nothing about the next post. On
 * by default — that is what a post did before the control existed.
 *
 * WHEN A NON-LOOPING REPLAY ENDS, THE MUSIC ENDS WITH IT. The end of the replay
 * goes through pause(), which stops the audio in the same call, so a finished
 * drawing can never be left with a loop still playing under it. Those two are
 * the only viewer controls — see inlineplayer.css.
 *
 * NOTHING FETCHES UNTIL SOMEBODY ASKS. The idle state is /s/<id>/card.png, one
 * cached image; GET /api/skribls/<id> is issued on the first play and never
 * again for that post. This is load-bearing, not an optimisation: that endpoint
 * returns the WHOLE payload, base64 audio included, and a feed that prefetched
 * twenty of those would move tens of megabytes to render thumbnails.
 *
 * IT FOLLOWS THE HOST'S THEME, WITH ITS OWN VALUES AS FALLBACKS.
 * inlineplayer.css reads a custom property for every colour and supplies a
 * literal after the comma: `var(--bg-elev, #12151c)`. A host that defines those
 * tokens gets a player that changes with it — including live, because custom
 * properties cascade from :root and a theme switch is one attribute change up
 * there. A host that defines nothing gets the literals, which is exactly what
 * the file shipped with.
 *
 * The token NAMES are the ones a feed already has — --bg-elev, --border,
 * --radius, --accent, --accent-2 — rather than skribl-prefixed ones, because a
 * prefix would mean the host had to map their palette onto ours to get any
 * benefit, and then nobody would.
 *
 * The failure this avoids is a DARK-ONLY PLAYER IN A LIGHT FEED: a black
 * rectangle among white cards, which reads as broken rather than as styled. A
 * microblog with a light/dark toggle is the normal case, not the exotic one.
 *
 * THE DRAWING ITSELF DOES NOT FOLLOW THE THEME. Its ground is the one the
 * author drew on and it is painted from the payload — the artwork is content,
 * not chrome, and recolouring it would be editing somebody's picture.
 *
 * THE POSTER IS THE SHARE CARD, CROPPED — and this is where that is explained,
 * because inlineplayer.css ships its comments to every host (jsstrip.py strips
 * a JavaScript response; nothing strips CSS) while these are stripped from
 * every response that carries them.
 *
 * /s/<id>/card.png is a 1200x630 branded card — the drawing contained inside a
 * bordered box under a "Skribl Pad" wordmark — because it was built to unfurl
 * on social scrapers, and it is the only per-post image the server has. Shown
 * whole it reads as an advert twenty times down a timeline. So the idle post
 * crops it back to the drawing. The crop is LITERALS in inlineplayer.css, not
 * a call: this page loaded lib/sharecard.js until v281 and never read
 * window.SkriblShareCard. verify_inline.py injects that module and compares
 * band() against these literals, so the arithmetic is still held to the
 * editors' — it just is not shipped to every feed page to do it.
 *
 * Vertically the crop is exact. The drawing is CONTAINED, so for any canvas not
 * wider than 2.22:1 — every preset — its height and its y are identical in
 * every card: 492 px of 630, starting at 27.
 *
 * Horizontally it cannot be exact, and 16:9 is the best available answer. The
 * drawing's width inside the card depends on its own aspect, and nothing here
 * knows that: canvasSize lives inside payload_json, and GET /api/skribls DEFERS
 * that column deliberately (a feed of payloads is hundreds of megabytes). But
 * the drawing is CENTRED in the card, so a symmetric side crop can only remove
 * the card's ground — never the picture — as long as the window is at least as
 * wide as the widest canvas a drawing can have. That is 16:9
 * (lib/canvassizes.js), so the box is 16:9. Measured on a 1:1 drawing: 22% of
 * the box is ground, against 59% for the uncropped band. A portrait 9:16
 * drawing is still mostly ground, which is what a portrait picture in a
 * landscape box is. verify_inline.py asserts the box is never narrower than the
 * widest preset, so adding a wider canvas size fails there rather than quietly
 * cutting the edges off every wide drawing in the feed.
 *
 * A tight, per-post crop wants the canvas size as a real COLUMN on the post,
 * which is a schema change and is not being made in passing here.
 *
 * THE GENERIC FALLBACK CARD IS CROPPED THE SAME WAY, deliberately. A post with
 * no stored thumbnail has /s/<id>/card.png REDIRECT to the static branded
 * og-card, and telling the two apart in the browser costs a request: the
 * redirect is invisible to an <img> (currentSrc reports the URL requested, not
 * the one that answered) and both images are 1200x630, so only a fetch that can
 * read response.redirected knows. One extra request per post, in a component
 * whose whole idle contract is "one cached image", to slightly improve a
 * fallback whose content is vertically centred anyway. Not worth it.
 *
 * ===========================================================================
 * TWO CLASSES A HOST PAGE MAY ADD: `is-bare` AND `is-immersive`
 * ===========================================================================
 *
 * The page adds the class; the component owns what it means. Both are in
 * inlineplayer.css, and the reasoning is here because CSS comments are served.
 *
 * `is-bare` — THE HOST SUPPLIES THE TRANSPORT. The component's own cluster
 * (mute, repeat) and its duration chip are hidden, because the page has drawn
 * its own; two transports over one drawing is a defect, not a choice. The
 * gallery's card footer and both full-screen bars are lib/fullbar.js driving
 * this player's handle, so this is what they add.
 *
 * IT DOES NOT HIDE THE VEIL, and it did for one commit. The veil is the dark
 * wash and the play triangle over a drawing that has not started: it is not a
 * control, it is the sentence "this moves". A host taking the BUTTONS over has
 * not taken over saying that, and the first screenshot of the post-like
 * gallery card was two dozen black rectangles under two dozen neat footers.
 *
 * ===========================================================================
 * THE IDLE POSTER, AND THE THREE GEOMETRY FACTS THE STYLESHEET USED TO CARRY
 * ===========================================================================
 *
 * A tile shows /s/<id>/poster until somebody presses play: the post's own
 * share card, or a blank canvas when it has none -- never the branded card,
 * which cropped to a drawing's band reads as a fragment of an advert (v287,
 * SK-BUG-006). The card is 1200x630 and CONTAINS the drawing, so there are
 * two ways to show one in a 16:9 box, and this player now does both:
 *
 *   NO SCRIPT, OR NO CANVAS SIZE -- the band crop, which is the stylesheet's
 *   two literals. The card is scaled to 128.0488% of the box height (630/492)
 *   and pulled up 5.4878% (27/492), which puts the wordmark and the padding
 *   outside the box. The box is 16:9 because that is the widest canvas a
 *   drawing can have (lib/canvassizes.js) and the drawing is centred in the
 *   card, so a symmetric side crop removes ground and never picture. A 1:1
 *   drawing then leaves 22% of the box as ground rather than 59%.
 *
 *   WITH THE DRAWING'S SIZE -- fitPoster(), below, which frames the card's
 *   drawingRect() exactly where the canvas will land and clips the rest away.
 *   That 22% of ground was still the CARD's ground, with the card's plate
 *   border around the picture: a frame inside a frame on every tile, which
 *   the owner photographed ("fix the share card bands too"). Idle and playing
 *   are one composition now.
 *
 * Both halves are asserted against the real lib/sharecard.js by
 * verify_inline.py, which evaluates the module rather than trusting the copy.
 *
 * `is-immersive` — THIS IS THE WHOLE SCREEN NOW. The box loses its border and
 * its radius and fills whatever contains it, the canvas is letterboxed inside
 * with object-fit, the share card goes (a crop that is right at tile size just
 * cuts the picture off at screen size) and the veil goes with it: at that size
 * the bar is unmissable and a wash over the whole picture is only dimmer art.
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
     * in a feed on a phone set to silent — this player is Web Audio (see the
     * AudioContext below). Holding a silent <audio> session makes it audible.
     * Claimed only here, on an explicit unmute, never on load: see
     * lib/audiosession.js for why that distinction is the whole justification
     * for overriding the switch at all.
     *
     * THE FEED'S CONTRACT IS DELIBERATELY DIFFERENT FROM THE /s PLAYER'S, and
     * this is the paragraph that says so rather than leaving it to be inferred.
     * The /s player holds the session only while it is AUDIBLY PLAYING, and
     * releases on Pause, the last frame and Mute. The feed holds it for as long
     * as SOUND IS ENABLED, whether or not anything is playing right now.
     *
     * Why the difference: sound here is one session-scoped preference shared by
     * every post in the list (SOUND_KEY, above), and posts start and stop as
     * you scroll. Tying the session to "is a post playing" would drop and
     * retake it on every card that scrolls in and out — a Control Center entry
     * flickering on and off down a feed — and would need a cross-player
     * refcount to know when the LAST one stopped. Tying it to the preference
     * gives one claim on unmute and one release on mute, which is also the only
     * pair of taps the viewer thinks of as turning sound on and off.
     *
     * The cost is honest and bounded: with sound on and nothing playing, iOS
     * shows Skribl as playing media. Muting clears it. If that ever needs to be
     * tightened, the refcount is the work, not a change of gesture. */
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
                 erase: s0.erase, start: s0.start, playT: 0 }];
    for (var i = 1; i < strokes.length; i++) {
      var gap = strokes[i].t - strokes[i - 1].t;
      if (gap > 0) playT += Math.min(gap, cap);
      var s = strokes[i];
      out.push({ x: s.x, y: s.y, color: s.color, size: s.size,
                 erase: s.erase, start: s.start, playT: playT });
    }
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
   * THIS USED TO BE THE ONE KNOWN FIDELITY GAP, named in this header rather
   * than left to be discovered, on the argument that ~60 lines of offscreen
   * canvas work per stroke was not obviously worth it "at feed scale — twenty
   * boxes, one playing". Two things were wrong with that.
   *
   * The scale figure was wrong: play() settles every other player, so exactly
   * ONE post is ever playing and the cost is two offscreen canvases, not
   * forty.
   *
   * And the gap was much larger than "beads at its overlaps" suggested. An
   * external review of v277 said a feed representation should not change the
   * drawing's appearance, so it was measured rather than argued.
   *
   * THE FIRST MEASUREMENT WAS CONFOUNDED AND IS RECORDED HERE BECAUSE IT WAS
   * NEARLY BELIEVED. Comparing this player against /s/<id> on the 96x96 grid
   * verify_inline.py uses gave "19.2% of cells differ, 22% less ink" — until
   * an OPAQUE control, which the compositor cannot touch, scored WORSE
   * (ink ratio 0.446). Most of that difference was the two surfaces fitting
   * the drawing to different boxes, exactly as verify_inline's own note says
   * they do. A cross-surface comparison cannot isolate this feature.
   *
   * The clean instrument is ONE surface with the feature absent. Same fixture,
   * a self-crossing stroke at 50% alpha, this player only:
   *
   *     compositor off   145,014 ink        21.7% under the canonical page
   *     compositor on    177,246 ink         4.3% under it
   *     /s/<id>          185,205 ink        (the reference)
   *
   * The residual 4.3% is that same canvas-fit difference, and the shapes now
   * agree: scalloped edges and a banded interior before, one smooth translucent
   * mark after. Side by side they WERE not the same drawing.
   *
   * IT COSTS 2,913 B SERVED, and the embed ratchet went 29,000 -> 32,000 to
   * pay for it — the largest raise that number has taken. Recorded at the
   * ratchet with this reasoning. An all-opaque payload, which is most of them,
   * allocates nothing: makeCompositor returns null and the direct path is
   * exactly what it was.
   *
   * Ported from app.js makeStrokeCompositor rather than rewritten, and it
   * draws through this file's own drawDot/drawLine so the two implementations
   * cannot drift in how a mark is shaped — only in where it is composited.
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
   * stroke at all, so an opaque drawing — which is most of them — allocates
   * nothing and takes the same path it always did. */
  function makeCompositor(visCtx, visCanvas, strokes, ratio) {
    var any = false;
    for (var i = 0; i < strokes.length; i++) {
      if (!strokes[i].erase && parseStrokeAlpha(strokes[i].color) < 1) {
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
    var dry = document.createElement('canvas');
    var wet = document.createElement('canvas');
    dry.width = wet.width = visCanvas.width;
    dry.height = wet.height = visCanvas.height;
    var dctx = dry.getContext('2d');
    var wctx = wet.getContext('2d');
    /* Seed dry with whatever is already painted — background, photo underlay. */
    dctx.setTransform(1, 0, 0, 1, 0, 0);
    dctx.drawImage(visCanvas, 0, 0);
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
        visCtx.drawImage(dry, 0, 0);
        if (wetActive) {
          visCtx.globalAlpha = wetAlpha;
          visCtx.drawImage(wet, 0, 0);
        }
        visCtx.restore();
      },
      finish: function () { if (wetActive) bakeWet(); },
    };
  }

  /* app.js replayTimelineToCanvas, verbatim: draw every point whose playT has
   * elapsed and return the index to resume from. The `i === 0` in the start
   * test matters — the first point of a payload may carry no `start` flag at
   * all, and without it the replay opens with a line from (0,0). */
  function replayTo(ctx, timeline, from, elapsed, comp) {
    var i = from;
    /* `comp` is null for an all-opaque payload — then this is the direct path
     * it always was, with no allocation and no wrapper. */
    while (i < timeline.length && timeline[i].playT <= elapsed) {
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
   * card ground and the card's own plate border showing on each side. Every
   * gallery tile was a picture inside a frame inside a card, and the owner
   * photographed it: "fix the share card bands too".
   *
   * THE POSTER NOW LANDS EXACTLY WHERE THE CANVAS WILL. Same rectangle, same
   * letterbox, so pressing play changes what moves and not where it is. That
   * is the property worth having: the idle state stops being a different
   * composition from the playing one.
   *
   * IT NEEDS THE DRAWING'S SHAPE and cannot look it up -- the listing defers
   * `payload_json` on purpose, which is why `canvas_w`/`canvas_h` are columns
   * on the post as of v309. The page writes them onto the box as
   * data-skribl-w/h; WITHOUT them nothing here runs and the stylesheet's band
   * crop stands, which is exactly what a row that predates the column gets.
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

  function fitPoster(img, w, h) {
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
    var a = dw / dh, cw = Math.min(a, BOX_A), ch = cw / a;
    /* One factor, card pixels -> box-height units, so the image scales
     * uniformly and the drawing's rect lands on the canvas's rect. */
    var k = cw / dw, st = img.style, i = PLATE_IN;
    function p(n, of) { return n / of * 100 + '%'; }
    st.width = p(CARD_W * k, BOX_A);
    st.height = p(CARD_H * k, 1);
    st.left = p((BOX_A - cw) / 2 - dx * k, BOX_A);
    st.top = p((1 - ch) / 2 - dy * k, 1);
    /* The stylesheet centres the band crop with a transform; this one is
     * positioned outright, so the transform has to go or it shifts twice. */
    st.transform = 'none';
    st.maxWidth = 'none';
    st.clipPath = 'inset(' + p(dy + i, CARD_H) + ' ' + p(CARD_W - dx - dw + i, CARD_W)
      + ' ' + p(CARD_H - dy - dh + i, CARD_H) + ' ' + p(dx + i, CARD_W)
      + ' round ' + p(PLATE_R - i, dw - i * 2) + '/' + p(PLATE_R - i, dh - i * 2) + ')';
  }

  /* ---- one box ----------------------------------------------------------- */

  function attach(el) {
    if (el._skriblInline) return el._skriblInline;

    var id = el.getAttribute('data-skribl-id');
    /* The listing endpoint, written in by the macro from url_for(). A host may
     * mount Skribl under any prefix, so the component never assembles a URL
     * from window.location or from a literal path — it appends an id to what
     * the server said the endpoint is.
     *
     * NO DEFAULT. This read used to fall back to '/api/skribls', which is the
     * exact mistake the rest of this comment describes: on a host mounted at
     * /skribl the fallback would have sent every payload fetch to a path that
     * does not exist, and quietly — the box would just show its error panel.
     * verify_seam.py scans client JS for route literals and caught it. A box
     * with no endpoint attribute cannot fetch, so it says so (see load()),
     * which is the honest failure. A DRAFT has no endpoint and needs none: it
     * is attached by payload and never loads. */
    var api = (el.getAttribute('data-skribl-api') || '').replace(/\/+$/, '');
    var canvas = el.querySelector('.skribl-inline-canvas');
    var poster = el.querySelector('.skribl-inline-poster');
    var prog = el.querySelector('.skribl-inline-prog');
    var nib = el.querySelector('.skribl-inline-nib');
    var durEl = el.querySelector('.skribl-inline-dur');
    var durText = el.querySelector('.skribl-inline-dur-text');
    var playEl = el.querySelector('.skribl-inline-play');
    var muteBtn = el.querySelector('.skribl-inline-mute');
    var loopBtn = el.querySelector('.skribl-inline-loop');
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
    var timeline = null, flipFrames = null, flipMs = null, flipFps = 12;
    var totalMs = 0, size = null, under = null;
    /* The scale ctx.setTransform is set to in adopt(), so the compositor's
       offscreen layers can match it instead of inferring it from CSS. */
    var pixelRatio = 1;
    var rate = 1;                             // the viewer's speed; see frame()
    var state = 'idle';                       // idle | playing | paused
    var elapsed = 0, t0 = 0, raf = null, drawn = 0;
    /* The page and progress this player last PAINTED, which is how
     * lib/holdtiming.js's displayAt() knows a drawing page has not yet been
     * shown whole. Null means nothing is owed a finish. */
    var lastShown = null;
    /* Rebuilt on every full repaint; null for an all-opaque payload. */
    var comp = null;
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
      toggle: function () { if (state === 'playing') pause(); else play(); },
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
      },
      rate: function () { return rate; },
      state: function () {
        /* segElapsed(), NOT `now() - t0`. The segment since the last anchor is
         * WALL time and `elapsed` is banked SCALED time, so adding the two raw
         * reports the replay running at 1x however fast it is really drawing.
         * Everything a viewer can see about the clock reads this field -- the
         * scrubber fill, the time readout, fullbar's end detection -- so at 2x
         * the drawing doubled and the bar crawled at half the true progress,
         * and the speed control looked DEAD (owner: "the 1x button on full
         * screen does nothing when pushed"). The render loop had it right all
         * along (`var at = elapsed + segElapsed()`), which is why the drawing
         * obeyed the rate and nothing else did.
         *
         * Measured, one tile, one second of wall clock at each rate:
         *     rate 1   drawing 16.66%   this field 1015ms
         *     rate 2   drawing 33.06%   this field 1006ms
         * The first probe of this bug read THIS FIELD and agreed with it. */
        return { id: id, state: state, totalMs: totalMs,
                 elapsedMs: state === 'playing' ? elapsed + segElapsed() : elapsed,
                 kind: flipFrames ? 'flip' : 'replay', hasAudio: !!music,
                 muted: !soundOn(), loaded: !!payload, failed: failed };
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
      }
    };
    players.push(me);
    el._skriblInline = me;

    function now() { return global.performance ? performance.now() : Date.now(); }

    function busy(on) {
      if (playEl) playEl.classList.toggle('is-busy', !!on);
    }

    function fail(msg) {
      failed = true;
      busy(false);
      if (errEl) { errEl.textContent = msg; errEl.hidden = false; }
    }

    function load() {
      if (payload || loading || failed) return Promise.resolve(payload);
      if (!api) {
        /* Nothing to fetch from. The macro always writes the endpoint in, so
         * this is hand-built markup missing data-skribl-api — say so rather
         * than guess a path. */
        fail("This Skribl is not wired up.");
        return Promise.resolve(null);
      }
      loading = true;
      busy(true);
      return global.fetch(api + '/' + encodeURIComponent(id),
                          { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
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
        .catch(function () {
          loading = false;
          fail("Couldn't load this Skribl.");
          return null;
        });
    }

    function adopt(p) {
      payload = p || {};
      var frames = framesOf(payload);
      size = logicalSize(payload);

      var dpr = Math.min(global.devicePixelRatio || 1, 2);
      pixelRatio = dpr;
      canvas.width = Math.round(size.w * dpr);
      canvas.height = Math.round(size.h * dpr);
      /* NO CSS SIZE IS SET, AND THAT IS THE LETTERBOX.
       *
       * This used to set canvas.style.width/height to the drawing's logical
       * size, with a comment saying max-width/max-height then preserved the
       * aspect "because a canvas is a replaced element". They do not. A
       * replaced element whose width AND height are both definite has each
       * axis clamped by its own maximum, independently -- so a 9:16 drawing
       * in the 16:9 box came out 386x217 instead of 122x217, stretched 216%,
       * and a 4:3 one by 33%. It was wrong on the feed, in the profile's
       * stage and in any host's embed, from the day this file was written;
       * the owner caught it on the profile page, where the stage is big
       * enough to see it (v305). /s/<id> was never affected -- app.js fits
       * the canvas itself.
       *
       * With both auto, the bitmap's own dimensions are the intrinsic ratio
       * and the two maximums letterbox it. Measured at 9:16, 4:3 and 1:1, at
       * desktop and phone widths, on the stage and in the feed.
       *
       * THE COMPOSITOR'S SCALE WAS THE SECOND HALF OF THIS. It derived the
       * device pixel ratio as backing/clientWidth, which was only ever the
       * true ratio while this CSS width was pinned -- and max-width was
       * already clamping it, so the offscreen layers ran ~1.94x out and every
       * see-through stroke composited at about twice its size. That inflation
       * is what carried verify_inline's ink gate over a floor calibrated on
       * it. The ratio is passed in now; see makeCompositor. */
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      canvas.hidden = false;

      var f0 = frames[0] || {};
      music = (f0.music && f0.music.data) ? f0.music : (payload.music || null);
      if (music && !music.data) music = null;
      el.classList.toggle('is-silent', !music);

      /* The underlay: background colour, then a photo or base snapshot.
       *
       * THE AUTHORED FIT TRAVELS WITH THE PHOTO, and this used to throw it
       * away. The comment here read that the fit/opacity/blur controls are
       * "authoring state the editor applies through CSS on its own <img>, and
       * reproducing that stack in a feed box is not worth a second
       * implementation of it. Cover is the fit a feed wants and the editor's
       * default." Cover is the editor's DEFAULT; it is not what the author
       * chose once they touched the control. A photo composed with Fit was
       * letterboxed in the editor and on /s/<id> and CROPPED here -- on the
       * profile stage, the feed and every host embed -- which is the owner's
       * report: "the pug in the background FIT the screen on the editor and
       * the original player. now he is cut off."
       *
       * And there is no second implementation to write: lib/photofit.js has
       * owned this geometry since the day Pad, Flip and the player each had
       * their own copy of it and one could not read what another wrote. Using
       * it is the cheap option; the expensive one was the hard-coded Math.max
       * that disagreed with two other surfaces.
       *
       * OPACITY AND BLUR TRAVEL TOO, as of v307, and this note used to say
       * they did not. The editor and /s/<id> put the photo in a real <img>
       * behind the canvas and let CSS fade and soften it; a feed box has one
       * canvas and nothing else, so the same two choices are globalAlpha and
       * ctx.filter. A photo authored at 40% painted opaque here, and one
       * authored soft painted sharp, on every host embed.
       *
       * THE BLUR RADIUS NEEDS NO CONVERSION, which is the reason it is one
       * line. ctx.filter works in user space, and the context is scaled by
       * the device pixel ratio in adopt(), so `blur(12px)` here covers the
       * same distance across the drawing as `filter: blur(12px)` on the
       * editor's img -- on a 1x screen and a 2x one alike. Writing the
       * conversion by hand is what would have made it wrong. */
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
          if (state === 'idle') renderIdle(); else render(elapsed, true);
        };
        img.src = src;
      }

      if (isFlip(payload, frames)) {
        flipFrames = frames;
        flipFps = payload.fps || 12;
        /* PER-PAGE MILLISECONDS. A page carrying `draw` replays its own
         * strokes over their recorded timing and is exempt from fps, so a page
         * is no longer a whole number of fps slots. Without the lib this
         * degrades to one slot per page, which is what it did before per-page
         * holds existed — the fallback's job is to keep a page turning, not to
         * reproduce a feature. */
        var H = global.SkriblHold;
        flipMs = H ? H.msTable(frames, flipFps)
                   : frames.map(function () { return 1000 / flipFps; });
        totalMs = H ? H.cycleMs(flipMs)
                    : Math.max(1, (frames.length / flipFps) * 1000);
      } else {
        timeline = buildTimeline(f0.strokes || [], payload.pauseMode);
        totalMs = timeline.length ? timeline[timeline.length - 1].playT : 0;
      }

      if (durText) durText.textContent = fmt(totalMs);
      if (durEl) durEl.hidden = false;
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

    /* Full repaint from zero. The incremental path below only appends, which is
     * what makes a replay cheap; anything that moves time backwards (seek,
     * loop, a resize) comes through here. */
    function render(at, full, jump) {
      if (!payload) return;
      if (flipFrames) {
        var H = global.SkriblHold;
        var cyc = at % Math.max(1, totalMs);
        /* THROUGH displayAt() WHEN PLAYING, because no instant of the live
         * clock supplies progress 1 while a drawing page is still current, and
         * that page must reach its complete recorded state before the clock
         * may leave it. `full` marks the repaints that move time backwards —
         * `jump` is a SCRUB and only a scrub: someone dragging the bar asked
         * for that page and must get it. Passing no `last` is how displayAt()
         * is told there is nothing owed, so a jump lands where it aimed. A
         * LOOP RESTART is not a jump —
         * it is the clock coming round, and the page it is leaving is owed its
         * last frame exactly as any other page turn is, which is why this
         * cannot key off `full`: the loop repaints fully too. See
         * lib/holdtiming.js. */
        var shown = H
          ? H.displayAt(flipMs, flipFrames, cyc, jump ? null : lastShown)
          : { index: Math.min(flipFrames.length - 1,
                              Math.floor(at / Math.max(1, totalMs) * flipFrames.length)),
              progress: 0 };
        lastShown = shown;
        var idx = shown.index;
        clear();
        var fr = flipFrames[idx];
        if (fr && fr.strokes && fr.strokes.length) {
          /* A DRAWING PAGE REVEALS, and dueCount() owns how much — the same
           * answer the editor and the /s/ player get, from the same module, so
           * all three agree about what a viewer sees.
           *
           * BRANCH ON THE PAGE, NOT ON THE PROGRESS. progressAt() returns 0
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
        if (full) { clear(); drawn = 0; comp = makeCompositor(ctx, canvas, timeline, pixelRatio); }
        drawn = replayTo(ctx, timeline, drawn, at, comp);
        if (comp && drawn >= timeline.length) comp.finish();
        setNib(state === 'playing' && drawn > 0 && drawn < timeline.length
               ? timeline[drawn - 1] : null);
      }
      prog.style.width = (totalMs ? Math.min(1, at / totalMs) * 100 : 0) + '%';
    }

    /* The nib rides in the BOX's coordinate space while the point is in the
     * DRAWING's, and the canvas is letterboxed between them — so this maps
     * through the two live rects rather than assuming they are the same box.
     * Getting this wrong puts the pen next to the line instead of on it, which
     * is worse than no nib at all.
     *
     * AND THE CANVAS ELEMENT IS NOT ALWAYS THE DRAWING. There are two sizing
     * models here and this used to know about one of them:
     *
     *   tile       width/height auto under max-width/max-height 100%, so the
     *              ELEMENT box is exactly the drawing and a rect is enough.
     *   immersive  width/height 100% with `object-fit: contain`, so the element
     *              box is the whole container and the bitmap is letterboxed
     *              INSIDE it. getBoundingClientRect() reports the container.
     *
     * So in full screen the nib was mapped across the screen while the line was
     * drawn across the smaller contained box, and sat up and to the left of its
     * own stroke (the owner's screenshot). `object-fit` has to stay: max-width
     * only ever SHRINKS a canvas, and full screen needs it to grow.
     *
     * The fix is to stop reading the element box and derive the CONTENT box —
     * the same arithmetic `contain` does. It reduces to the element box in tile
     * mode (there the two axes' scales are equal and both offsets are zero), so
     * one mapping now serves both, and a third sizing model cannot bring this
     * back. */
    /* AND THE NIB IS A SIZE IN THE DRAWING, NOT A SIZE ON THE SCREEN. It was
     * 8px of CSS wherever it appeared, so the same dot was a boulder on an
     * 84px library thumb and a speck on a 1280px full screen -- the one thing
     * on the surface that did not answer to how big the drawing is (owner:
     * "shouldn't the nib be scaled to the size of the player, rather than stay
     * the same size no matter where it occurs?").
     *
     * 13 units of the AUTHOR's canvas, which is 8px at the tile scale this was
     * drawn for and grows and shrinks from there. Clamped at both ends: below
     * about five pixels a dot is not a pen tip, it is dirt on the screen, and
     * above twenty-two it stops being a nib and starts being a cursor.
     *
     * ONE CUSTOM PROPERTY, and the sheet derives the ring from it with a
     * calc(). This runs on every frame of every replay, so it writes only when
     * the scale MOVES -- and it writes one value rather than three.
     *
     * THE SHEET CARRIES NO COMMENT ABOUT ANY OF THIS, and that is deliberate
     * rather than an omission: CSS comments are served to every host and
     * nothing strips them, which is that file's own standing rule. The first
     * cut explained `--nb` beside the rule and cost 264 B of somebody else's
     * bandwidth to do it. `--nb` is documented here, where the explanation is
     * free, and the rule there is three declarations a reader can follow. */
    var nibAt = -1;
    function nibSize(s) {
      if (s === nibAt) return;
      nibAt = s;
      nib.style.setProperty('--nb', Math.max(5, Math.min(22, 13 * s)) + 'px');
    }

    function setNib(p) {
      var st = nib.style;
      if (!p) { st.opacity = '0'; return; }
      var cr = canvas.getBoundingClientRect(), br = el.getBoundingClientRect();
      if (!cr.width || !cr.height) { st.opacity = '0'; return; }
      var s = Math.min(cr.width / size.w, cr.height / size.h);
      nibSize(s);
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

    function applyLoop() {
      el.classList.toggle('is-noloop', !looping);
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
      el.classList.toggle('is-muted', !on);
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
      if (failed) return;
      if (!payload) {
        load().then(function (p) { if (p) play(); });
        return;
      }
      if (state === 'playing') return;
      for (var i = 0; i < players.length; i++) if (players[i] !== me) players[i].settle();
      if (elapsed >= totalMs) elapsed = 0;
      /* Always a full repaint from zero when starting at zero — posterless, the
       * canvas is currently holding the FINISHED drawing (renderIdle), and the
       * incremental path only ever appends. */
      if (elapsed === 0) render(0, true);
      state = 'playing';
      el.classList.add('is-playing');
      el.classList.remove('is-paused');
      t0 = now();
      raf = global.requestAnimationFrame(frame);
      startAudio();
    }

    function pause() {
      if (state !== 'playing') return;
      elapsed += segElapsed();
      if (raf) global.cancelAnimationFrame(raf);
      raf = null;
      state = 'paused';
      el.classList.remove('is-playing');
      el.classList.add('is-paused');
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
      if (payload) renderIdle();
    }

    el.addEventListener('click', function (e) {
      if (muteBtn && muteBtn.contains(e.target)) return;
      if (state === 'playing') pause(); else play();
    });

    el.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
      e.preventDefault();                 /* Space scrolls the feed otherwise */
      if (state === 'playing') pause(); else play();
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

    if (poster) {
      /* A post whose card 404s (a store that lost the thumbnail, a host without
       * the card route) must not show a broken-image glyph in the feed. */
      poster.addEventListener('error', function () { poster.hidden = true; });
      /* THE DRAWING'S SHAPE, if the page knows it (v309). Absent -- an old row,
       * a payload with no canvasSize, a host that has not passed it through --
       * the stylesheet's band crop stands. See fitPoster above. */
      var pw = +el.getAttribute('data-skribl-w');
      var ph = +el.getAttribute('data-skribl-h');
      if (pw > 0 && ph > 0) fitPoster(poster, pw, ph);
    }

    applySound();
    applyLoop();
    return me;
  }

  /* ---- mounting ---------------------------------------------------------- */

  /* Off-screen posts stop. Without this, scrolling away from a playing Skribl
   * leaves it drawing and looping into a viewport nobody is looking at — the
   * battery cost of a feed autoplaying forever, paid for nothing. Guarded
   * because IntersectionObserver is the one API here a very old browser may
   * lack, and its absence should cost a behaviour, not the player. */
  var io = null;
  if (global.IntersectionObserver) {
    io = new global.IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) continue;
        var p = entries[i].target._skriblInline;
        if (p) p.settle();
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
    attach: function (el, payload) {
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
      if (p) { if (io) io.observe(el); p.adopt(payload); }
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
