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
 * DOES NOT: the wet/dry stroke compositor (app.js makeStrokeCompositor). A
 *         stroke authored below 100% opacity is drawn here as overlapping
 *         stamps, so its overlaps bead darker than they do on /s/<id>. This is
 *         the one KNOWN fidelity gap and it is named here rather than left to
 *         be discovered: the compositor is ~60 lines of offscreen canvas work
 *         per stroke, and at feed scale — twenty boxes, one playing — it is not
 *         obviously worth the allocation. verify_inline.py pins the gap with an
 *         OPAQUE drawing so the pixel comparison stays meaningful; if this ever
 *         gets the compositor, that fixture is where to widen the proof.
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
 * crops it back to the drawing, using the geometry in lib/sharecard.js, which
 * is the same module editor_post.js composites the card from.
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
     * for overriding the switch at all. */
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

  /* app.js replayTimelineToCanvas, verbatim: draw every point whose playT has
   * elapsed and return the index to resume from. The `i === 0` in the start
   * test matters — the first point of a payload may carry no `start` flag at
   * all, and without it the replay opens with a line from (0,0). */
  function replayTo(ctx, timeline, from, elapsed) {
    var i = from;
    while (i < timeline.length && timeline[i].playT <= elapsed) {
      var p = timeline[i];
      if (p.start || i === 0) drawDot(ctx, p.x, p.y, p.color, p.size, p.erase);
      else {
        var prev = timeline[i - 1];
        drawLine(ctx, prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
      }
      i++;
    }
    return i;
  }

  function paintStatic(ctx, strokes) {
    for (var i = 0; i < strokes.length; i++) {
      var p = strokes[i];
      if (p.start || i === 0) drawDot(ctx, p.x, p.y, p.color, p.size, p.erase);
      else {
        var prev = strokes[i - 1];
        drawLine(ctx, prev.x, prev.y, p.x, p.y, p.color, p.size, p.erase);
      }
    }
  }

  function fmt(ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
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
    var timeline = null, flipFrames = null, flipHolds = null, flipFps = 12;
    var totalMs = 0, size = null, under = null;
    var state = 'idle';                       // idle | playing | paused
    var elapsed = 0, t0 = 0, raf = null, drawn = 0;
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
      state: function () {
        return { id: id, state: state, totalMs: totalMs,
                 elapsedMs: state === 'playing' ? elapsed + (now() - t0) : elapsed,
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
        render(elapsed, true);
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
      canvas.width = Math.round(size.w * dpr);
      canvas.height = Math.round(size.h * dpr);
      /* CSS size is the LOGICAL size; inlineplayer.css caps it at the box with
       * max-width/max-height, which preserves the aspect because a canvas is a
       * replaced element. The drawing is therefore letterboxed, never
       * stretched. */
      canvas.style.width = size.w + 'px';
      canvas.style.height = size.h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      canvas.hidden = false;

      var f0 = frames[0] || {};
      music = (f0.music && f0.music.data) ? f0.music : (payload.music || null);
      if (music && !music.data) music = null;
      el.classList.toggle('is-silent', !music);

      /* The underlay: background colour, then a photo or base snapshot. Both
       * are just an image under the strokes here — the photo's fit/opacity/blur
       * controls are authoring state the editor applies through CSS on its own
       * <img>, and reproducing that stack in a feed box is not worth a second
       * implementation of it. Cover is the fit a feed wants and the editor's
       * default. */
      under = { color: (f0.background && f0.background.color) || (payload.background || {}).color || null,
                image: null };
      var src = (f0.photo && f0.photo.data) || f0.baseSnapshot || payload.baseSnapshot || null;
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
        var H = global.SkriblHold;
        flipHolds = H ? H.table(frames) : frames.map(function () { return 1; });
        totalMs = H ? H.durationMs(flipHolds, flipFps)
                    : Math.max(1, (flipHolds.length / flipFps) * 1000);
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
        /* Cover: fill the canvas, crop the overflow, centred. */
        var iw = under.image.naturalWidth || size.w, ih = under.image.naturalHeight || size.h;
        var k = Math.max(size.w / iw, size.h / ih);
        var dw = iw * k, dh = ih * k;
        ctx.drawImage(under.image, (size.w - dw) / 2, (size.h - dh) / 2, dw, dh);
      }
    }

    /* Full repaint from zero. The incremental path below only appends, which is
     * what makes a replay cheap; anything that moves time backwards (seek,
     * loop, a resize) comes through here. */
    function render(at, full) {
      if (!payload) return;
      if (flipFrames) {
        var H = global.SkriblHold;
        var idx = H ? H.indexAt(flipHolds, flipFps, at % Math.max(1, totalMs))
                    : Math.min(flipFrames.length - 1,
                               Math.floor(at / Math.max(1, totalMs) * flipFrames.length));
        clear();
        var fr = flipFrames[idx];
        if (fr && fr.strokes && fr.strokes.length) paintStatic(ctx, fr.strokes);
        setNib(null);
      } else {
        if (full) { clear(); drawn = 0; }
        drawn = replayTo(ctx, timeline, drawn, at);
        setNib(state === 'playing' && drawn > 0 && drawn < timeline.length
               ? timeline[drawn - 1] : null);
      }
      prog.style.width = (totalMs ? Math.min(1, at / totalMs) * 100 : 0) + '%';
    }

    /* The nib rides in the BOX's coordinate space while the point is in the
     * DRAWING's, and the canvas is letterboxed between them — so this maps
     * through the two live rects rather than assuming they are the same box.
     * Getting this wrong puts the pen next to the line instead of on it, which
     * is worse than no nib at all. */
    function setNib(p) {
      if (!p) { nib.style.opacity = '0'; return; }
      var cr = canvas.getBoundingClientRect();
      var br = el.getBoundingClientRect();
      if (!cr.width || !cr.height) { nib.style.opacity = '0'; return; }
      nib.style.left = ((cr.left - br.left) + (p.x / size.w) * cr.width) + 'px';
      nib.style.top = ((cr.top - br.top) + (p.y / size.h) * cr.height) + 'px';
      nib.style.opacity = '1';
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

    function frame() {
      var at = elapsed + (now() - t0);
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
      elapsed += now() - t0;
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
