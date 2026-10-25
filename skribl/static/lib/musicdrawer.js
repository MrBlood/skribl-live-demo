/* THE MUSIC DRAWER'S CONTROLS, one copy for the Pad and for Flip.
 *
 * The owner, with Flip's Fine-tune on screen: "it needs to be the same music
 * editor on both pad and flip." The drawer's markup was already one file
 * (_skribl_music_drawer.html) and its arithmetic was already shared
 * (lib/looptrim.js, audioloop.js, dragtrack.js, and since step 2 the
 * timeline and the Restart view, lib/musictimeline.js and musicrestart.js). Its
 * WIRING was not: every control below was written out twice, in
 * editor_music.js, editor_photo.js and app.js for the Pad and in flip.js for
 * Flip, and the copies had drifted:
 *
 *   - Crossfade carried a playing preview over to the new seam on Flip; on
 *     the Pad the preview kept the old seam until it was stopped.
 *   - Test Seam played the seam on the Pad (the loop's last 1.25 s, the join,
 *     its first 1.25 s) and the loop from its top, twice, on Flip. With a
 *     crossfade set, the Pad played the whole clip three times instead.
 *   - Preview Loop had a middle step on the Pad, the baked clip looping on an
 *     <audio> element, that Flip lacked: Flip fell straight back to the raw
 *     track, wrapped by a timer, where no crossfade is heard.
 *   - Flip saved the trim on every drag. The Pad saved on a mouseup or a
 *     touchend ON the strip, so a drag let go past its end was never saved.
 *   - Match Drawing Time counted Flip's pages at one frame each: no holds, no
 *     drawing pages, no loops.
 *   - The music switch, off, silenced Flip's Play. On the Pad it paused the
 *     <audio> element only, while the gapless loop and any preview played on;
 *     on again, mid-Play, Flip's music came back and the Pad's did not.
 *
 * Each now does what the better side did, once.
 *
 * ONE VIEW, AND MORE (owner: "The music drawer is so complicated... we'll
 * need to streamline it"). The view is the timeline (step 2; it was the
 * strip), the one line under it, the pair that plays, Fit my drawing and
 * Whole song; More opens the rest in place: the restart (with the Restart
 * view), the beat, exact times and how it loops (Cut on silence, Lock the
 * length). It was three
 * levels, Simple, Adjust and Fine-tune, and before them Trim and Fine-tune;
 * More only shows and hides, and whether it is open is remembered (one key
 * for both editors). Today's names, kept as ids: Fine-tune is More, Match
 * Drawing Time is Fit my drawing, Test Seam is Hear the restart, Preview Loop
 * is Hear the loop, Crossfade is Smooth restart's length.
 *
 * SKRIBL'S PICK is what a new song starts as. Skribl listens first
 * (lib/musicears.js; step 3 of the music plan, "the part that loops best, on
 * the beat"; the mock and the owner: "all yes"). With a steady beat the loop
 * starts on a bar, in played music, where it comes round smoothly (of joins
 * as good, the first: usually where the beat comes in), and is whole bars,
 * 4, 8, 16 or 32 beats: where the editor asks for the drawing's length
 * (`fitsByDefault`, the Pad), the count nearest the drawing (the owner's
 * pick; Fit my drawing makes it exact), else the most that fit the 20s. The
 * beat heard is the song's beat at once, marked heard, so the beat count,
 * Snap to the beat and "a bar" use it and the beat line says "heard by
 * Skribl"; a tap makes it the taps'. Until it has listened (it reads a few
 * milliseconds at a time, and the beat line says "Listening for the beat…"),
 * and for a song with no steady beat, the pick is what it was before ears:
 * the first 20 seconds (the whole song, when it is shorter), or on the Pad
 * a drawing already there sets the length, with a smooth restart. Heard, the
 * loop glides to the new pick, the beat's marks fading in, only if nothing
 * was changed meanwhile: a loop moved or a beat tapped is left as it is.
 * A song a draft brings back keeps its loop and is not listened to. Not on
 * Flip for the drawing's length: an animation goes round in a second or two,
 * and a loop that short is a stutter -- Fit my animation is one tap. The
 * pick line says which it is, and once the loop is changed, offers Back to
 * Skribl's pick (the heard one, with its beat) with an Undo for eight
 * seconds, which brings back the loop and the beat that were there.
 *
 * THE ONE LINE says how long the loop is, in beats once there is a tempo,
 * against the drawing, and then Skribl's pick or the way back to it. It was
 * three: the pick line, Adjust's length line, and Fine-tune's sync line.
 *
 * A SMOOTH RESTART MAKES THE LOOP SHORTER. The crossfade folds the loop's end
 * over its start (lib/audioloop.js), so what is heard comes round sooner than
 * the stretch selected, by the crossfade's length. "Fits your drawing", the
 * lengths the lines say and Fit my drawing all count what is heard. Match
 * Drawing Time did not, so with a crossfade set it fell short of the drawing.
 *
 * THE PAIR THAT PLAYS (owner: "How do I test the loop without having it show
 * me drawing?"): Play with my drawing presses the editor's Play, and Hear the
 * loop (it was Preview Loop, then Hear the whole loop) plays the music alone,
 * round and round. Both sit under the strip, More open or not. An end moved
 * while the loop plays is heard from its next time round: the gapless engine
 * starts the new loop where the old one comes round.
 *
 * TAP THE BEAT (owner: "to know how many beats are in the loop, so I'm not at
 * 7 or 9 when I want 8"). Tapped along with Hear the loop, which the first tap
 * starts, so every tap is timed against the loop as posted at its own speed.
 * The tempo is the middle of the gaps between taps, to the nearest whole beat
 * a minute (most music is), and where a beat falls is the taps' own, read off
 * the song's clock less the time the sound takes to reach the ear, so the
 * marks sit on what was heard. Then every count is of
 * what is HEARD, smooth restart and all: the one line says the beats, and,
 * with Snap to the beat on, a start let go on the timeline lands on a beat
 * (let go in the quiet before the music or just into it, where the music
 * begins; zoomed in, it stays, and the beat moves to it when it is near one)
 * and the loop on whole bars,
 * 4, 8, 16 or 32 beats (the owner: "we only ever want 4,8,16,... beats"), the
 * end where the loop comes round, so with a smooth restart the handle sits
 * that much past the beat. The loop slid along the
 * song starts on a beat, and - and + move a bar unless another step is
 * picked. Off, nothing settles. The tempo is the editor's, saved with the
 * song in its drafts, and the switch with it.
 *
 * TEST SEAM IS AN <audio> ELEMENT, played inside the tap. On a phone set to
 * silent that is the one that is heard (verify_audiosession's first note),
 * and it is why Test Seam worked on the owner's iPhone before Preview Loop
 * did. It plays the baked clip, the posted loop itself, so the join heard is
 * the join posted, crossfade and all; until the track has decoded it plays the
 * track, wrapped at the loop's end by hand.
 *
 * WHAT STAYS IN EACH EDITOR: its state and its media. The trim, zoom and
 * crossfade numbers are the editors' own variables (the Pad's player reads them
 * through app.js, where a binding declared here would not exist); this reads
 * and writes them only through the hooks below. The file row's add and remove
 * stay too, tied to each editor's media, and so does how each editor's Play
 * plays music: the Pad's follows the replay's speed, Flip's keeps its own pace
 * and loops (the owner's F1 pick).
 *
 * wire(h), with the editor's own hooks:
 *   trim()              { start, end, duration } in seconds
 *   setTrim(start, end)
 *   crossfade()         in ms; setCrossfade(ms)
 *   cut()               Cut on silence is on; setCut(b), kept in the drafts
 *   hasTrack()          a track is loaded and its length is known
 *   refresh()           repaint the drawer (the editor's updateTrimUI)
 *   lane()              the drawing's lane on the timeline, and laneKey(),
 *                       which moves when the drawing does (lib/musictimeline.js)
 *   changed()           the editor's autosave
 *   drawingSeconds()    the drawing's length, for Fit my drawing
 *   fitsByDefault       Skribl's pick is as long as the drawing (the Pad)
 *   fitted()            optional: Skribl has listened and the loop is as
 *                       long as the drawing (the Pad's toast says so)
 *   playButton()        the editor's Play, which Play with my drawing presses
 *   audio()             the track's <audio> element, or null
 *   buffer()            the decoded AudioBuffer, or null
 *   loop                the gapless engine: start(onFail, offset), stop(),
 *                       playing(), elapsed(), duration(), latency()
 *   clip()              the baked loop { dataUrl, duration }, or null
 *   playing()           the drawing is playing (Play)
 *   setPreviewing(b)    the editor's own flag, which its Play and stop read
 *   enabled()           the music switch; setEnabled(b)
 *   musicOn()           Play's music, joining the drawing where it is
 *   musicOff()          Play's music, stopped
 *   syncRow()           redraw the file row and its switch
 *   tempo()             the song's tempo { bpm, phase }, with snap: false
 *                       when Snap to the beat is off and heard: true when
 *                       Skribl heard it, or null; setTempo(t), kept with
 *                       the song in the drafts
 *   dock()              the bar right above the drawer, which More's nudge
 *                       leaves under the pinned header while More's first
 *                       control still shows (lib/drawerdetent.js)
 *
 * Returns { sync, syncCrossfade, resetView, matchDrawing, applyPick,
 * stopPreview, playhead, previewing, more, tempo }. SkriblMusicDrawer.tempoFrom(raw)
 * reads a saved tempo back, or null. Editor-only: the player has no drawer and
 * never loads this. */
(function (global) {
  'use strict';

  var SEAM = 1.25;                         // seconds either side of the join
  var PICK_FADE_MS = 250;                  // Skribl's pick's smooth restart
  var UNDO_MS = 8000;
  var EPS = 0.0005;                        // two times are one at the thousandth
  var TAP_IDLE_MS = 2000;                  // Tap the beat settles after this long without a tap
  var SNAP_PX = 8;                         // in the loop detail, an end let go this near a beat settles on it
  var BARS = [4, 8, 16, 32];               // the beats a loop settles on: 1, 2, 4 or 8 bars
  var GLIDE_MS = 200;                      // a settle glides there

  function fill(el) {
    var mn = +el.min, mx = +el.max;
    el.style.setProperty('--slider-fill', (mx > mn ? (+el.value - mn) / (mx - mn) * 100 : 0) + '%');
  }
  function near(a, b) { return Math.abs(a - b) < EPS; }
  // What is heard each time round: the stretch selected, less the crossfade,
  // which lib/audioloop.js caps at half of it.
  function heard(t, ms) {
    var len = t.end - t.start;
    return len - Math.min(Math.max(0, ms) / 1000, len / 2);
  }
  // "8", "8.4", "1:12": a length the way a person says it. Rounded from the
  // hundredths the lines show, as a person rounds what they read: 4.448 was
  // "4.4 seconds" over a line saying 4.45s, which reads as two lengths.
  function says(s) {
    s = Math.round(s * 100) / 100;
    if (s >= 59.95) {
      var m = Math.floor(Math.round(s) / 60), r = Math.round(s) % 60;
      return m + ':' + (r < 10 ? '0' : '') + r;
    }
    var t = Math.round(s * 10 + 1e-9) / 10;
    return Math.abs(t - Math.round(t)) < 0.05 ? String(Math.round(t)) : t.toFixed(1);
  }
  // A tempo as saved: { bpm, phase } -- beats a minute, and where a beat falls
  // in the song, in seconds -- with snap: false once Snap to the beat is
  // turned off for it, and heard: true when Skribl heard it (lib/musicears.js)
  // rather than taps. Anything else is no tempo.
  function tempoFrom(t) {
    var bpm = t ? +t.bpm : NaN, ph = t ? +t.phase : NaN;
    if (!(bpm >= 30 && bpm <= 300 && isFinite(ph))) return null;
    var out = { bpm: bpm, phase: ph };
    if (t.snap === false) out.snap = false;
    if (t.heard === true) out.heard = true;
    return out;
  }
  // "8 beats", "8.8 beats", "1 beat": whole when it is within a twentieth.
  function beatWords(n) {
    var w = Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1);
    return w + (w === '1' ? ' beat' : ' beats');
  }
  function median(xs) {
    if (!xs.length) return 0;
    var v = xs.slice().sort(function (a, b) { return a - b; }), m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  }
  // A verb over what it plays: the pair's two lines (spans .tp-k and .tp-v).
  function twoLines(el, k, v) {
    if (!el) return;
    var a = el.querySelector('.tp-k'), b = el.querySelector('.tp-v');
    if (a && a.textContent !== k) a.textContent = k;
    if (b && b.textContent !== v) b.textContent = v;
  }
  // A typed time: 12.345, 12,345, 12.3s or 1:02.5. Anything else is null.
  function parseTime(v) {
    var s = String(v == null ? '' : v).trim().replace(/s$/i, '').replace(',', '.');
    var m = /^(\d+):(\d+(?:\.\d*)?)$/.exec(s);
    var n = m ? (+m[1]) * 60 + parseFloat(m[2]) : (/^\d*\.?\d+$|^\d+\.$/.test(s) ? parseFloat(s) : NaN);
    return isFinite(n) ? n : null;
  }
  function setOn(el, on, attr) {
    if (!el) return;
    el.classList.toggle('on', on);
    el.setAttribute(attr || 'aria-checked', String(on));
  }

  function wire(h) {
    var $ = function (id) { return document.getElementById(id); };
    var T = global.SkriblLoopTrim, nudgers = global.addSliderNudgers;
    var detail = $('musicDetail');
    var panel = $('musicPanel'), work = (panel && panel.dataset.work) || 'drawing';

    /* ---- More: the rest of the drawer, in place. ---------------------------
     * It unfolds joined to its tile and folds away again as the draw drawer's
     * tiles do (lib/drawtiles.js), at once under Reduce Motion, and the drawer
     * gets shorter only once the fold is done, gently: scrolled near its end,
     * the page would clamp and leap under the finger (lib/drawerdetent.js).
     * MORE STARTS CLOSED, EVERY TIME: on a load, and whenever the music panel
     * is put away, so the drawer opens on its one view, short enough for a
     * phone (the owner, finding it open from an old Fine-tune: "More starts
     * open"; then the pick, always closed). Nothing remembers it.
     * #musicDetail's data-level says which, set before More shows or hides,
     * so lib/drawerdetent.js does not follow it as a song landing. `hidden`
     * takes what More holds out of the Tab order as well as off the screen. */
    var moreBtn = $('fineTuneToggle'), moreBody = $('fineTuneBody');
    var open = false, folding = false, foldT = null;
    function still() { return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    // What shows once there is a beat (Snap to the beat, and a bar in Each
    // press) opens out from nothing, across ('x') or down, rather than
    // pushing what is around it aside in one frame; at once under Reduce
    // Motion, and when it is not on the screen to see.
    function glideIn(el, axis) {
      if (!el || still() || !el.animate || !el.offsetParent) return;
      var cs = global.getComputedStyle(el), from = { opacity: 0 }, to = { opacity: 1 };
      (axis === 'x' ? ['width', 'minWidth', 'paddingLeft', 'paddingRight'] : ['height', 'paddingTop', 'paddingBottom'])
        .forEach(function (k) { from[k] = '0px'; to[k] = cs[k]; });
      el.style.overflow = 'hidden';
      var an = el.animate([from, to], { duration: 240, easing: 'cubic-bezier(.2, .8, .2, 1)' });
      an.onfinish = an.oncancel = function () { el.style.overflow = ''; };
    }
    function showMore() {
      if (detail) detail.dataset.level = open ? 'fine' : 'simple';
      if (moreBtn) {
        moreBtn.setAttribute('aria-expanded', String(open));
        moreBtn.classList.toggle('open', open || folding);
      }
      if (moreBody && !folding) moreBody.hidden = !open;
    }
    function finishFold() {
      if (!folding) return;
      clearTimeout(foldT);
      if (moreBody) {
        moreBody.classList.remove('mt-folding');
        if (moreBody.getAnimations) moreBody.getAnimations().forEach(function (a) { a.cancel(); });
      }
      var drop = function () { folding = false; showMore(); sync(); };
      var det = global.SkriblDrawerDetent;
      if (det && det.shrinkGently && detail) det.shrinkGently(detail, drop); else drop();
    }
    function setMore(next) {
      if (next === open) return;
      if (folding) finishFold();
      open = next;
      if (!open) {
        folding = true;
        showMore();
        if (!moreBody || still() || !moreBody.animate) { finishFold(); return; }
        moreBody.classList.add('mt-folding');
        moreBody.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scaleY(.94)' }],
                         { duration: 180, easing: 'ease-in', fill: 'forwards' });
        foldT = setTimeout(finishFold, 200);
        return;
      }
      showMore();
      sync();
      if (moreBody && !still() && moreBody.animate) {
        moreBody.animate([{ opacity: 0, transform: 'scaleY(.92)' }, { opacity: 1, transform: 'none' }],
                         { duration: 220, easing: 'cubic-bezier(.2, .8, .2, 1)' });
      }
      // The Restart view's canvas was laid out at zero size while hidden.
      // Then bring what opened into view (a tap that seemed to do nothing was
      // the old Fine-tune's fault), but never so far that More goes under the
      // pinned header -- nor the bar above the drawer, the editor's dock(),
      // as lib/drawerdetent.js caps the drawer's own reveals, unless that
      // would leave even More's first control below the screen, a tap that
      // seems to do nothing again: then the first control wins. With the
      // timeline the drawer is tall enough for both to bind: More's tile
      // alone let Fit my drawing and Whole song pass under the header on an
      // 844px phone (verify_ux's phone audit), and the bar alone left Smooth
      // restart below a 664px one (verify_sheetswipe).
      requestAnimationFrame(function () {
        h.refresh();
        if (rv) rv.draw();
        if (!moreBody || !moreBtn) return;
        var det = global.SkriblDrawerDetent;
        var vh = global.visualViewport ? global.visualViewport.height : global.innerHeight;
        var top = det && det.stuckBottom ? det.stuckBottom() : 0;
        var over = Math.min(moreBody.getBoundingClientRect().bottom - vh + 12, moreBtn.getBoundingClientRect().top - top - 8);
        var bar = h.dock ? h.dock() : null, first = moreBody.querySelector('button, input, select, textarea');
        if (bar && bar.offsetParent !== null) {
          var need = first ? first.getBoundingClientRect().bottom - vh + 12 : 0;
          over = Math.min(over, Math.max(bar.getBoundingClientRect().top - top - 4, need));
        }
        if (over > 0) global.scrollBy({ top: over, behavior: 'smooth' });
      });
    }
    showMore();
    if (moreBtn) moreBtn.addEventListener('click', function () { setMore(!open); });
    // Put away (the drawer closed, or Photo picked), More closes with it, at
    // once: nothing of it is on the screen to fold.
    if (panel && global.MutationObserver) new global.MutationObserver(function () {
      if (!panel.hidden || !(open || folding)) return;
      clearTimeout(foldT);
      if (moreBody) {
        moreBody.classList.remove('mt-folding');
        if (moreBody.getAnimations) moreBody.getAnimations().forEach(function (a) { a.cancel(); });
      }
      open = folding = false;
      showMore();
    }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });

    // A new song: the timeline starts where it belongs, and the last song's
    // Undo and taps are not this one's.
    function resetView() {
      if (tl) tl.reset();
      forgetUndo();
      stepPick = null;
      taps = [];
      clearTimeout(tapT);
      tapT = null;
      tapNote = '';
    }

    /* ---- The loop's edges. ------------------------------------------------
     * On the timeline a dragged end stops at the 20 s cap ('constrain'); in
     * the Restart view, by nudge and when typed, it pushes the other end along
     * ('slide'). Declared, not accidental: lib/looptrim.js has the reasons.
     * With Lock the length on, any end moves the whole loop instead. Every
     * change is saved when it lands, wherever the finger is let go. */
    var locked = false, glideRaf = 0, aim = null;
    function stopGlide() { if (glideRaf) { global.cancelAnimationFrame(glideRaf); glideRaf = 0; } aim = null; }
    // The loop as it is, or where it lands while a settle glides there: what
    // the tag and Beats go by, so neither changes its mind on the way.
    function loopNow() { var t = h.trim(); return aim ? { start: aim[0], end: aim[1], duration: t.duration } : t; }
    function setEdge(which, time, mode) {
      stopGlide();
      if (tl && tl.focus) tl.focus(which);
      var t = h.trim(), n;
      if (locked) {
        var len = t.end - t.start, s = Math.max(0, Math.min(t.duration - len, t.start + time - (which === 'start' ? t.start : t.end)));
        n = { start: s, end: s + len };
      } else n = T.setHandle({ start: t.start, end: t.end, duration: t.duration }, which, time, mode);
      h.setTrim(n.start, n.end);
      touched();
      h.refresh();
    }
    // The loop slid along the song, its length kept.
    function slideTo(start) {
      var t = h.trim(), len = t.end - t.start, s = Math.max(0, Math.min(t.duration - len, start));
      stopGlide();
      h.setTrim(s, s + len);
      touched();
      h.refresh();
    }
    // A settle glides there, both ends together, frame by frame so the
    // timeline, its handles and the one line move as one; at once under
    // Reduce Motion. Saved when it lands.
    function glideTo(s1, e1, then) {
      stopGlide();
      var t = h.trim(), s0 = t.start, e0 = t.end, t0 = global.performance.now();
      aim = [s1, e1];
      function step(now) {
        var k = still() ? 1 : Math.min(1, Math.max(0, now - t0) / GLIDE_MS), q = 1 - Math.pow(1 - k, 3);
        h.setTrim(s0 + (s1 - s0) * q, e0 + (e1 - e0) * q);
        h.refresh();
        if (k < 1) { glideRaf = global.requestAnimationFrame(step); return; }
        glideRaf = 0;
        touched();
        h.changed();
        if (then) then();
      }
      step(t0);
    }
    /* SNAP TO THE BEAT (the owner, a song with a quiet start: "it ends up
     * putting the beat in the middle rather than in the right spot. Can I no
     * longer freely adjust start and end?"; then the picks, "if they let me
     * set the starting point. I need a free set so it's not all automatic").
     * With a tempo and the switch under The beat on, an end let go on the
     * timeline settles:
     *   the start on the nearest beat, and the end follows so the loop is
     *     whole bars: of 4, 8, 16 and 32 beats, the count nearest what the
     *     finger left that the song and the 20s cap have room for;
     *   where the music begins after a silence instead (soundAt), the beat
     *     kept, when the start is let go in that silence and the music is
     *     nearer than the beat, or the beat is in a silence, or the start is
     *     let go up to half a beat into the music: a song's first sound is
     *     often a lead-in, between beats, and the nearest beat was in the
     *     dead air before it (the owner: "how do I move the start to the
     *     start of sound? It snaps back to empty space"; of the mock, "All
     *     yes"). A sound that begins within an eighth of a beat of one lands
     *     on that beat, so music on the beat settles as it did, and between
     *     two sounds on beats the nearer one is kept. Whole bars from a
     *     lead-in come round to the same place in the beat, so the loop
     *     still keeps it;
     *   magnified, the start where it is let go, and when that is within an
     *     eighth of a beat of one, a beat falls there (the owner, zoomed in on
     *     where the music begins: "how do I tell it where the beginning is?
     *     When I take it to the beginning it just snaps to a different spot";
     *     of the mock, "All yes"). A tapped beat is rarely on the music to the
     *     hundredth (on the mock's song, 45ms off), and zoomed in the note can
     *     be seen. Further off, a lead-in, the beat stays where it was, or
     *     every mark would leave its drum. The tempo keeps its beats a minute;
     *     every beat, bar and snap after counts from that start, and the end
     *     follows as above. Tapped again, the beat is the taps' own;
     *   the end on whole bars the same way, counted from the start wherever
     *     it is: dragging the end never moves a start you have set.
     * In the Restart view, a close-up (`pxPerSec`, its scale), an end let go
     * within SNAP_PX of a beat settles on it instead: the loop detail's rule,
     * which the Restart view took over. The loop slid along the song, or sent
     * by a tap on the whole song, starts on a beat (beatFor). Either way the
     * end is where the loop comes round, a smooth restart's length before the
     * handle. The switch off, nothing settles. Typed and stepped ends never
     * do, nor a locked loop's. */
    function snapOn() { var tp = tempo(); return !!tp && tp.snap !== false; }
    // Where a start let go at `t` lands instead of the nearest beat `on`, or
    // null: where the music begins after a silence, when `t` is in the
    // silence and the music is nearer than `on`, or when `on` is in it, or
    // when `t` is up to half a beat into the music. A sound that begins
    // within an eighth of a beat of one lands on that beat, so music on the
    // beat snaps as it did. A silence is a hundredth of the song's loudest
    // (-40dB) or less on every channel for HUSH or more, or from the song's
    // own start, read off the samples: a level's blocks reach past a silence's
    // edge, and a beat where the music stops would read as sound.
    var QUIET = 0.01, HUSH = 0.15, STEP = 0.01;
    function soundAt(t, on, tp) {
      var MT = global.SkriblMusicTimeline, buf = h.buffer && h.buffer();
      if (!MT || !buf) return null;
      var P = (tl && tl.peaks && tl.peaks()) || null;
      if (!P || P.buffer !== buf) P = MT.peaksOf(buf);
      var sr = buf.sampleRate, n = buf.length, dur = buf.duration, p = 60 / tp.bpm, low = QUIET * P.top, ch = [], o = null, b, j;
      for (j = 0; j < buf.numberOfChannels; j++) ch.push(buf.getChannelData(j));
      var hit = function (i) { for (var c = 0; c < ch.length; c++) if (ch[c][i] >= low || ch[c][i] <= -low) return true; return false; };
      var loud = function (x) {
        for (var i = Math.max(0, Math.floor(x * sr)), e = Math.min(n, Math.ceil((x + STEP) * sr)); i < e; i++) if (hit(i)) return true;
        return false;
      };
      // The silence holding x, from where it began to where the sound comes, or null.
      var hush = function (x) {
        x = Math.max(0, x);
        if (loud(x)) return null;
        var a = x, e = x;
        while (e < dur && !loud(e)) e += STEP;
        while (a > 0 && !loud(a - STEP)) a -= STEP;
        return e < dur && (a <= 0 || e - a >= HUSH) ? e : null;
      };
      var mine = hush(t);
      if (mine != null && Math.abs(mine - t) < Math.abs(on - t)) o = mine;
      else if (loud(t)) {
        for (b = t; b > 0 && t - b <= p / 2 && loud(b - STEP); b -= STEP);
        if (t - b <= p / 2 && (b <= 0 || hush(b - STEP) != null)) o = b;
      }
      if (o == null) o = hush(on);
      if (o == null) return null;
      // To the sample: the first that sounds from where the walk stopped.
      for (j = Math.max(0, Math.floor(o * sr)); j < n && !hit(j); j++);
      o = j / sr;
      var q = tp.phase + Math.round((o - tp.phase) / p) * p;
      return Math.abs(o - q) <= p / 8 && q >= 0 ? q : o;
    }
    // Of 4, 8, 16 and 32 beats, the count nearest `len` heard that `room`
    // seconds hold, or 0.
    function barsFor(len, room) {
      var p = beatSecs(), best = 0;
      BARS.forEach(function (k) {
        var l = lenFor(k);
        if (l > Math.min(T.MAX_LOOP_SECONDS, room) + EPS || l < T.MIN_LOOP_SECONDS - EPS) return;
        if (!best || Math.abs(len - k * p) < Math.abs(len - best * p)) best = k;
      });
      return best;
    }
    function snap(which, pxPerSec, zoomed) {
      if (!snapOn() || locked || !h.hasTrack()) return;
      var tp = tempo(), p = beatSecs(), t = h.trim(), n, k;
      var state = { start: t.start, end: t.end, duration: t.duration };
      if (!pxPerSec && which === 'start') {
        var on = tp.phase + Math.round((t.start - tp.phase) / p) * p, first = zoomed ? null : soundAt(t.start, on, tp);
        var s = zoomed ? t.start : first != null ? first : on;
        if (s < -EPS) s += p;
        s = Math.max(0, s);
        if (zoomed && h.setTempo && Math.abs(t.start - on) <= p / 8) h.setTempo({ bpm: tp.bpm, phase: Math.round(s * 10000) / 10000 });
        k = barsFor(heard({ start: s, end: t.end }, h.crossfade()), t.duration - s);
        // No whole bars fit from that beat: the start settles alone.
        n = k ? { start: s, end: s + lenFor(k) } : T.setHandle(state, 'start', s, 'constrain');
      } else if (!pxPerSec) {
        k = barsFor(heard(t, h.crossfade()), t.duration - t.start);
        if (!k) return;
        n = T.setHandle(state, 'end', t.start + lenFor(k), 'constrain');
      } else {
        var fold = Math.min(h.crossfade() / 1000, (t.end - t.start) / 2);
        var at = which === 'start' ? t.start : t.end - fold;
        var beat = tp.phase + Math.round((at - tp.phase) / p) * p;
        if (!(Math.abs(beat - at) * pxPerSec <= SNAP_PX)) return;
        n = T.setHandle(state, which, which === 'start' ? beat : beat + fold, 'slide');
      }
      if (near(n.start, t.start) && near(n.end, t.end)) return;
      glideTo(n.start, n.end);
    }
    // Where a loop of `len` starting near `start` starts on a beat: the
    // nearest beat, or at either end of the song the one on the side there is
    // room. `start` itself with the switch off or no tempo, or with no room
    // either side.
    function beatFor(start, len) {
      var tp = tempo(), p = beatSecs(), d = h.trim().duration;
      if (!snapOn()) return start;
      var beat = tp.phase + Math.round((start - tp.phase) / p) * p;
      if (beat + len > d + EPS) beat -= p;
      if (beat < -EPS) beat += p;
      return beat < -EPS || beat + len > d + EPS ? start : Math.max(0, beat);
    }
    // A slid loop, let go: with a tempo its start settles on the nearest beat.
    function onBeat() {
      if (!h.hasTrack()) return;
      var t = h.trim(), len = t.end - t.start, beat = beatFor(t.start, len);
      if (Math.abs(beat - t.start) < EPS) return;
      glideTo(beat, beat + len);
    }

    /* ---- The timeline (lib/musictimeline.js): the drawing stays put and the
     * song slides under it. Its ends are the loop's; let go, they settle as
     * above. ---------------------------------------------------------------- */
    function laneName(secs) {
      var w = work === 'animation' ? 'Your animation' : 'Your drawing';
      return w + ' \u00b7 ' + (secs > 0 ? says(secs) + 's' : 'nothing drawn yet');
    }
    var tl = global.SkriblMusicTimeline ? global.SkriblMusicTimeline.create($('musicTimeline'), {
      trim: h.trim, buffer: h.buffer, hasTrack: h.hasTrack, crossfade: h.crossfade, tempo: tempo,
      lane: h.lane, laneKey: h.laneKey, name: laneName, still: still,
      edge: function (which, t) { setEdge(which, t, 'constrain'); },
      slide: slideTo,
      // A tap on the whole song: the loop glides there, starting on a beat.
      jump: function (start) {
        var t = h.trim(), len = t.end - t.start, s0 = beatFor(Math.max(0, Math.min(t.duration - len, start)), len);
        glideTo(s0, s0 + len);
      },
      letGo: function (kind, which, zoomed) { if (kind === 'end') snap(which, 0, zoomed); else onBeat(); h.changed(); }
    }) : null;

    /* ---- The Restart view (lib/musicrestart.js), in More: the end beside the
     * start. Its sides move the ends as the loop detail's handles did, and
     * its dot is the smooth restart's length. ------------------------------ */
    var rv = global.SkriblMusicRestart ? global.SkriblMusicRestart.create($('musicRestart'), {
      trim: h.trim, buffer: h.buffer, hasTrack: h.hasTrack, crossfade: h.crossfade, tempo: tempo,
      cut: cutNow,
      edge: function (which, t) { setEdge(which, t, 'slide'); },
      blend: function (ms) { setFade(ms); touched(); h.refresh(); },
      letGo: function (what) {
        if (what === 'blend') { h.changed(); rejoin(); return; }
        snap(what, rv.half() / rv.window);
        h.changed();
      }
    }) : null;

    /* ---- - and +: how far each press moves. --------------------------------
     * One pill under the times, Each press: 0.01s, 0.1s, and a bar once there
     * is a tempo, opening out beside them (the owner, asking how to change the
     * step after it went automatic; it had been Each tap, with five steps).
     * Faded until then, as a dimmed button is, it read 2.5:1 (verify_onepill).
     * Untouched it is a bar while Snap to the beat is on, and today's step,
     * 0.1s, otherwise; a new song starts untouched. Each button's name says
     * the step too. Only the edges' buttons carry data-which. */
    var nudges = [].slice.call(document.querySelectorAll('.nudge-btn[data-which]'));
    var stepSeg = $('musicStepSeg'), stepBtns = stepSeg ? [].slice.call(stepSeg.querySelectorAll('button[data-step]')) : [];
    var stepPick = null;   // null untouched, else '0.01', '0.1' or 'bar'
    function stepKey() {
      if (stepPick === '0.01' || stepPick === '0.1') return stepPick;
      if (stepPick === 'bar') return beatSecs() > 0 ? 'bar' : '0.1';
      return snapOn() ? 'bar' : '0.1';
    }
    function stepNow() { var k = stepKey(); return k === 'bar' ? 4 * beatSecs() : parseFloat(k); }
    function syncSteps() {
      var p = beatSecs(), k = stepKey();
      nudges.forEach(function (b) {
        var w = (b.dataset.which === 'start' ? 'Start' : 'End') + ' of loop, ' + (k === 'bar' ? 'a bar' : k + 's') + ' '
          + (parseFloat(b.dataset.amount) > 0 ? 'later' : 'earlier');
        if (b.getAttribute('aria-label') !== w) b.setAttribute('aria-label', w);
      });
      stepBtns.forEach(function (b) {
        var on = b.dataset.step === k, gone = b.dataset.step === 'bar' && !(p > 0);
        if (b.classList.contains('on') !== on) b.classList.toggle('on', on);
        if (b.hidden !== gone) { b.hidden = b.disabled = gone; if (!gone) glideIn(b, 'x'); }
        var t = b.dataset.step === 'bar' && !gone ? 'A bar, ' + (4 * p).toFixed(2) + 's' : '';
        if ((b.getAttribute('title') || '') !== t) { if (t) b.setAttribute('title', t); else b.removeAttribute('title'); }
      });
    }
    stepBtns.forEach(function (b) {
      b.addEventListener('click', function () {
        if (b.disabled) return;
        stepPick = b.dataset.step;
        syncSteps();
      });
    });
    nudges.forEach(function (b) {
      b.addEventListener('click', function () {
        var which = b.dataset.which, dir = parseFloat(b.dataset.amount);
        // A NaN step would corrupt the edge and make the clamp reset the loop.
        if (!h.hasTrack() || (which !== 'start' && which !== 'end') || !isFinite(dir)) return;
        var t = h.trim();
        setEdge(which, (which === 'start' ? t.start : t.end) + dir * stepNow(), 'slide');
        h.changed();
      });
    });

    // Typed times, to the thousandth. A time that is not one puts the loop's
    // own time back.
    var times = [].slice.call(document.querySelectorAll('#musicDetail .mt-time'));
    function syncTimes(force) {
      var t = h.trim(), ok = h.hasTrack();
      times.forEach(function (inp) {
        if (!force && document.activeElement === inp) return;
        inp.value = ok ? (inp.dataset.edge === 'start' ? t.start : t.end).toFixed(3) : '';
      });
    }
    times.forEach(function (inp) {
      inp.addEventListener('change', function () {
        var v = parseTime(inp.value);
        if (h.hasTrack() && v != null) { setEdge(inp.dataset.edge, v, 'slide'); h.changed(); }
        syncTimes(true);
      });
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); inp.blur(); } });
    });

    var lock = $('musicLock'), lockSub = $('musicLockSub');
    function syncLock() {
      setOn(lock, locked);
      if (lockSub) lockSub.textContent = locked
        ? 'On: moving one end moves the other, so the loop stays ' + (h.trim().end - h.trim().start).toFixed(3) + 's.'
        : 'When on, moving one end moves the other.';
    }
    if (lock) lock.addEventListener('click', function () { locked = !locked; syncLock(); });

    /* ---- Skribl's pick, and the way back to it. ---------------------------- */
    function fadeFor(len) { return Math.max(0, Math.min(PICK_FADE_MS, Math.floor(len * 1000 / 4 / 5) * 5)); }
    // EARS (lib/musicears.js): what Skribl heard in a new song, once. `earsHeard`
    // is null until it has listened, and false when there is no steady beat.
    // `pickedNew` is the pick a new song started on, while the loop is still it,
    // and `beatsPick` the one Beats made (below).
    var ears = null, earsFor = null, earsHeard = null, earsKey = '', earsPick = null, pickedNew = null, beatsPick = null;
    function listenTo(buf) {
      if (!global.SkriblEars || !buf || buf === earsFor) return;
      if (ears) ears.cancel();
      earsFor = buf; earsHeard = null; earsKey = ''; beatsPick = null;
      ears = global.SkriblEars.listen(buf, function (H) {
        ears = null;
        if (earsFor !== buf) return;
        earsHeard = global.SkriblEars.steady(H) ? H : false;
        heardIt();
      });
      syncTap();
    }
    function forgetEars() {
      if (ears) ears.cancel();
      ears = null; earsFor = null; earsHeard = null; earsKey = ''; earsPick = null; pickedNew = null; beatsPick = null;
    }
    // Skribl's pick with ears, for the drawing's length as it is: whole bars
    // nearest it on the Pad (the owner's pick), the longest that fits otherwise.
    function earsPickFor(secs, d) {
      if (!earsHeard) return null;
      var key = secs.toFixed(3) + '|' + d.toFixed(3);
      if (key !== earsKey) {
        earsKey = key;
        earsPick = global.SkriblEars.pick(earsHeard, { duration: d, target: secs > 0 ? secs : T.MAX_LOOP_SECONDS,
          maxLoop: T.MAX_LOOP_SECONDS, minLoop: T.MIN_LOOP_SECONDS, fadeMs: PICK_FADE_MS });
      }
      return earsPick;
    }
    function fromEars(P, secs) {
      return { start: P.start, end: P.end, ms: PICK_FADE_MS, fits: secs > 0 && near(P.heard, secs),
               tempo: { bpm: Math.round(P.bpm * 1000) / 1000, phase: Math.round(P.phase * 10000) / 10000, heard: true } };
    }
    // `drawing`: the drawing's length when the caller has it (sync, below).
    function pickNow(drawing) {
      var d = h.trim().duration;
      if (!(d > 0)) return null;
      var secs = !h.fitsByDefault ? 0 : drawing != null ? drawing : h.drawingSeconds(), ms, end;
      var P = earsPickFor(secs, d);
      if (P) return fromEars(P, secs);
      if (secs > 0) { ms = fadeFor(secs); end = T.loopLength(secs + ms / 1000, d); }
      else { end = Math.min(d, T.MAX_LOOP_SECONDS); ms = fadeFor(end); }
      return { start: 0, end: end, ms: ms, fits: secs > 0 && near(heard({ start: 0, end: end }, ms), secs) };
    }
    // The loop's length in whole bars of the beat, 4, 8, 16 or 32, or 0.
    function countOf() {
      var p = beatSecs();
      if (!(p > 0) || !h.hasTrack()) return 0;
      var n = heard(loopNow(), h.crossfade()) / p, c = Math.round(n);
      return BARS.indexOf(c) >= 0 && Math.abs(n - c) < 0.01 ? c : 0;
    }
    function isPick(p) {
      var t = loopNow();
      return !!p && near(t.start, p.start) && near(t.end, p.end) && h.crossfade() === p.ms;
    }
    // A pick, set: the loop, its smooth restart, and with ears the beat heard.
    function setPick(p) {
      var was = h.crossfade();
      stopGlide();
      h.setTrim(p.start, p.end);
      setFade(p.ms);
      if (p.tempo && h.setTempo) h.setTempo(p.tempo);
      h.refresh();
      h.changed();
      if (was !== p.ms) rejoin();
    }
    // On a new song, from each editor's add (never a restore): today's pick at
    // once, and Skribl listens. Until it has, nothing says the loop fits
    // (the Pad's toast): with a beat it becomes whole bars.
    function applyPick() {
      forgetEars();
      var p = pickNow();
      if (!p || !h.hasTrack()) return null;
      setPick(p);
      pickedNew = p;
      if (!global.SkriblEars) return p;
      if (h.buffer && h.buffer()) listenTo(h.buffer());
      return { start: p.start, end: p.end, ms: p.ms, fits: false };
    }
    // Heard: the loop glides to the pick with ears, and the beat is the one
    // heard, if nothing changed meanwhile. A loop moved or a beat tapped, and
    // the pick is left as it is (Back to Skribl's pick goes to the heard one).
    function heardIt() {
      var tp = tempo(), p = pickedNew && isPick(pickedNew) && !(tp && !tp.heard) ? pickNow() : null;
      if (p && p.tempo) {
        pickedNew = p;
        if (h.setTempo) h.setTempo(p.tempo);
        setFade(p.ms);
        glideTo(p.start, p.end);
      }
      // what applyPick held back: the loop is as long as the drawing
      if (p && p.fits && h.fitted) h.fitted();
      sync();
    }
    var undo = null, undoT = null;
    function forgetUndo() { undo = null; clearTimeout(undoT); }
    // Any change made here to the loop: an Undo of the way back is stale, and
    // a settle still gliding would undo the change.
    function touched() { stopGlide(); if (undo) { forgetUndo(); syncPick(); } retime(); }
    /* ---- The one line: "4.00s · 8 beats · fits your drawing", then Skribl's
     * pick, or the way back to it. What is heard each time round, to the
     * hundredth; the beats once there is a tempo; against the drawing once
     * there is one. A loop that was the pick and is not now, because the
     * drawing changed, says only that: shorter or longer than the drawing,
     * and the way back. Nobody is told they did something. `secs`: the
     * drawing's length when the caller has it (sync, below). */
    var pickLine = $('musicPickLine'), pickText = $('musicPickText'), pickTag = $('musicPickTag');
    var back = $('musicBackPick'), undoBtn = $('musicPickUndo');
    function against(len, secs) {
      if (!(secs > 0)) return '';
      if (near(len, secs)) return 'fits your ' + work;
      return (len < secs ? 'shorter' : 'longer') + ' than your ' + work;
    }
    function syncPick(secs) {
      if (!pickLine) return;
      pickLine.hidden = !h.hasTrack();
      if (pickLine.hidden) return;
      if (secs == null) secs = h.drawingSeconds();
      var len = heard(h.trim(), h.crossfade()), p = beatSecs();
      var rest = [p > 0 ? beatWords(len / p) : '', against(len, secs)].filter(Boolean);
      var html = '<b>' + len.toFixed(2) + 's</b>' + (rest.length ? ' · ' + rest.join(' · ') : ' loop');
      if (pickText && pickText._html !== html) { pickText.innerHTML = html; pickText._html = html; }
      // While a song brought back is heard again, neither: until then the
      // pick is the one without ears.
      var mine = !isPick(pickNow(secs)) && !isPick(beatsPick), hold = !!ears && !pickedNew;
      if (pickTag) pickTag.hidden = mine || hold;
      if (back) back.hidden = !mine || !!undo || hold;
      if (undoBtn) undoBtn.hidden = !undo;
    }
    // The loop as Undo puts it back, and what a change that offers Undo
    // leaves to undo, for UNDO_MS.
    function state() {
      var t = loopNow();
      return { start: t.start, end: t.end, ms: h.crossfade(), tempo: h.tempo ? h.tempo() : null, pick: beatsPick };
    }
    function remember(was) {
      undo = was;
      clearTimeout(undoT);
      undoT = setTimeout(function () { undo = null; syncPick(); }, UNDO_MS);
      sync();
    }
    if (back) back.addEventListener('click', function () {
      var was = state(), p = h.hasTrack() ? pickNow() : null;
      if (!p) return;
      setPick(p);
      remember(was);
      if (undoBtn) undoBtn.focus();   // where the button was: focus is not lost
    });
    if (undoBtn) undoBtn.addEventListener('click', function () {
      if (!undo) return;
      var u = undo, was = h.crossfade();
      forgetUndo();
      stopGlide();
      h.setTrim(u.start, u.end);
      setFade(u.ms);
      if (h.setTempo && u.tempo !== (h.tempo ? h.tempo() : null)) h.setTempo(u.tempo);
      beatsPick = u.pick;
      h.refresh();
      h.changed();
      if (was !== u.ms) rejoin();
      sync();
      if (back && !back.hidden) back.focus();
    });

    /* ---- Fit my drawing and Whole song. -----------------------------------
     * Fit my drawing: what is heard as long as the drawing, its start kept
     * unless that would run it past the song's end (it was Match Drawing
     * Time). Whole song: the song from its top, or the longest loop there is
     * when the song is longer than that. Each wears the one tint while the
     * loop is what it makes. */
    function matchDrawing() {
      var secs = h.drawingSeconds();
      if (!h.hasTrack() || !(secs > 0)) return false;
      var t = h.trim(), len = T.loopLength(secs + h.crossfade() / 1000, t.duration), s = t.start, e = s + len;
      if (e > t.duration) { e = t.duration; s = Math.max(0, e - len); }
      h.setTrim(s, e);
      touched();
      h.refresh();
      h.changed();
      return true;
    }
    var fit = $('matchDrawingBtn'), fitSub = $('musicFitSub');
    var whole = $('musicWholeBtn'), wholeName = $('musicWholeName'), wholeSub = $('musicWholeSub');
    if (fit) fit.addEventListener('click', matchDrawing);
    if (whole) whole.addEventListener('click', function () {
      if (!h.hasTrack()) return;
      h.setTrim(0, Math.min(h.trim().duration, T.MAX_LOOP_SECONDS));
      touched();
      h.refresh();
      h.changed();
    });
    function syncPicks(secs) {
      var t = h.trim(), ok = h.hasTrack(), d = t.duration;
      var longest = Math.min(d, T.MAX_LOOP_SECONDS);
      if (fit) {
        fit.disabled = !ok || !(secs > 0);
        setOn(fit, ok && secs > 0 && near(heard(t, h.crossfade()), secs), 'aria-pressed');
        if (fitSub) fitSub.textContent = secs > 0 ? says(secs) + 's' : "once you've drawn";
      }
      if (whole) {
        whole.disabled = !ok;
        setOn(whole, ok && near(t.start, 0) && near(t.end, longest), 'aria-pressed');
        var all = ok && d <= T.MAX_LOOP_SECONDS + EPS;
        if (wholeName) wholeName.textContent = all || !ok ? 'Whole song' : 'Longest loop';
        if (wholeSub) wholeSub.textContent = !ok ? '' : all ? says(d) + 's' : 'the first ' + says(longest) + 's';
      }
    }

    /* ---- Hear the loop and Test Seam. --------------------------------------
     * Hear the loop (Preview Loop) plays the posted clip on the gapless
     * engine; where that cannot start (no unlock, now or later), the clip
     * loops on an <audio> element, and before the decode, the track itself
     * loops by hand. */
    var previewBtn = $('previewLoopBtn'), seamBtn = $('testSeamBtn');
    var pv = { on: false, mode: null, engine: null, el: null, tick: null, backstop: null };
    // Where the song is, on the timeline and in the Restart view.
    function showAt(song) {
      if (!(h.trim().duration > 0)) return;
      if (tl) tl.playhead(song);
      if (rv) rv.playhead(song);
    }
    function every(fn) { if (pv.tick) clearInterval(pv.tick); pv.tick = setInterval(function () { if (pv.on) fn(); }, 30); }
    function stopPreview() {
      pv.on = false;
      clearTimeout(retimeT);
      retimeT = null;
      h.setPreviewing(false);
      if (pv.tick) clearInterval(pv.tick);
      if (pv.backstop) clearTimeout(pv.backstop);
      pv.tick = pv.backstop = null;
      if (pv.el) { try { pv.el.pause(); } catch (e) {} pv.el = null; }
      // Play's own music still needs the engine, the element and the iOS
      // playback session (lib/audiosession.js): only an idle drawing lets go.
      if (!h.playing()) {
        h.loop.stop();
        var a = h.audio();
        if (a) { try { a.pause(); } catch (e) {} }
        if (global.SkriblAudioSession) global.SkriblAudioSession.release();
      }
      pv.mode = pv.engine = null;
      if (tl) tl.playhead(null);
      if (rv) rv.playhead(null);
      syncHear();
    }
    function begin(mode) {
      stopPreview();
      // Claimed before any resume (verify_audiosession section 8's order).
      if (global.SkriblAudioSession) global.SkriblAudioSession.claim();
      pv.on = true;
      pv.mode = mode;
      h.setPreviewing(true);
      syncHear();
    }
    // Whichever started what plays says Stop, and only that one. `secs`: the
    // drawing's length when the caller has measured it (sync, below).
    function syncHear(secs) {
      var looping = pv.on && pv.mode === 'loop';
      if (previewBtn) {
        twoLines(previewBtn, looping ? 'Stop' : 'Hear', 'the loop');
        previewBtn.classList.toggle('playing', looping);
        previewBtn.disabled = !h.hasTrack();
      }
      if (seamBtn) seamBtn.textContent = pv.on && pv.mode === 'seam' ? 'Stop' : 'Hear the restart';
      syncPlay(secs);
    }
    // An end moved while the loop plays: the new loop starts where this one
    // comes round, on the gapless engine (the clip on an element keeps its
    // loop until it is heard again: a new element outside a tap may not play).
    var retimeT = null;
    function retime() {
      if (!pv.on || pv.mode !== 'loop' || pv.engine !== 'wa' || !h.loop.playing()) return;
      var dur = h.loop.duration ? h.loop.duration() : 0;
      if (!(dur > 0)) return;
      clearTimeout(retimeT);
      retimeT = setTimeout(function () {
        retimeT = null;
        if (pv.on && pv.mode === 'loop' && pv.engine === 'wa') h.loop.start(function () { if (pv.on) loopNative(); }, 0);
      }, Math.max(0, (dur - h.loop.elapsed()) * 1000 - 10));
    }
    function baked() { return h.buffer() ? h.clip() : null; }
    // The baked clip `c` on its own element, from `at` seconds into it.
    function clipElement(c, at) {
      var a = new Audio(c.dataUrl);
      a.loop = true;
      // Before its metadata this sets where playback starts, which is the
      // point: play() has to be called inside the tap.
      if (at > 0) { try { a.currentTime = at; } catch (e) {} }
      a.play().catch(function () {});
      pv.el = a;
      pv.engine = 'clip';
      return a;
    }
    function loopNative() {
      if (!pv.on) return;
      var c = baked();
      if (c) {
        var el = clipElement(c, 0);
        every(function () { showAt(h.trim().start + el.currentTime); });
        return;
      }
      var a = h.audio();
      if (!a) { stopPreview(); return; }
      pv.engine = 'track';
      try { a.muted = false; a.currentTime = h.trim().start; } catch (e) {}
      a.play().catch(function () {});
      every(function () {
        var t = h.trim();
        if (a.currentTime >= t.end - 0.05) { a.currentTime = t.start; a.play().catch(function () {}); }
        showAt(a.currentTime);
      });
    }
    function startLoop(offset) {
      if (!h.hasTrack()) return;
      begin('loop');
      var handedOff = false;
      var fallback = function () {
        if (handedOff || !pv.on || pv.mode !== 'loop') return;
        handedOff = true;
        loopNative();
      };
      if (h.loop.start(fallback, offset || 0)) {
        pv.engine = 'wa';
        every(function () { if (h.loop.playing()) showAt(h.trim().start + h.loop.elapsed()); });
        return;
      }
      fallback();
    }
    function startSeam() {
      if (!h.hasTrack()) return;
      begin('seam');
      var t = h.trim(), c = baked();
      var lead = Math.min(SEAM, c ? c.duration : t.end - t.start);
      var wrapped = false, last = -1;
      // A stop that does not wait on the clip coming round, should it never play.
      pv.backstop = setTimeout(stopPreview, (2 * lead + 3) * 1000);
      if (c) {
        var el = clipElement(c, Math.max(0, c.duration - lead));
        every(function () {
          var now = el.currentTime;
          if (now + 0.25 < last) wrapped = true;          // it came round
          last = now;
          showAt(h.trim().start + now);
          if (wrapped && now >= lead) stopPreview();
        });
        return;
      }
      var a = h.audio();
      if (!a) { stopPreview(); return; }
      pv.engine = 'track';
      try { a.muted = false; a.currentTime = Math.max(t.start, t.end - lead); } catch (e) {}
      a.play().catch(function () {});
      every(function () {
        var tr = h.trim();
        if (!wrapped && a.currentTime >= tr.end - 0.05) { wrapped = true; a.currentTime = tr.start; }
        showAt(a.currentTime);
        if (wrapped && a.currentTime >= tr.start + lead) stopPreview();
      });
    }
    if (previewBtn) previewBtn.addEventListener('click', function () {
      if (pv.on && pv.mode === 'loop') stopPreview(); else startLoop(0);
    });
    if (seamBtn) seamBtn.addEventListener('click', function () {
      if (pv.on && pv.mode === 'seam') stopPreview(); else startSeam();
    });

    /* ---- Play with my drawing. ---------------------------------------------
     * The editor's own Play, so the drawing replays with its music exactly as
     * Play plays it (and Play shows the whole drawing, lib/drawerdetent.js
     * revealTop). It follows the editor's Play however that is pressed. With
     * nothing to replay it waits, as Fit my drawing does: Hear the loop,
     * beside it, plays the music on its own. */
    var play = $('musicPlayBtn');
    function drawn(secs) {
      var b = h.playButton ? h.playButton() : null;
      return b && !b.disabled && (secs != null ? secs : h.drawingSeconds()) > 0 ? b : null;
    }
    function syncPlay(secs) {
      if (!play) return;
      var b = drawn(secs), on = h.playing();
      play.disabled = !h.hasTrack() || (!b && !on);
      play.classList.toggle('playing', on);
      twoLines(play, on ? 'Stop' : 'Play', (on ? 'the ' : 'with my ') + work);
    }
    if (play) play.addEventListener('click', function () {
      var b = drawn();
      if (h.playing()) { var pb = h.playButton && h.playButton(); if (pb) pb.click(); }
      else if (b) { if (pv.on) stopPreview(); b.click(); }
      syncPlay();
    });
    var pb0 = h.playButton ? h.playButton() : null;
    if (pb0 && global.MutationObserver) new MutationObserver(function () { syncPlay(); }).observe(pb0, { attributes: true, attributeFilter: ['class', 'disabled'] });
    // A drawing begun while the drawer was shut: say so when it opens.
    if (panel && global.MutationObserver) new MutationObserver(function () { if (!panel.hidden) sync(); })
      .observe(panel, { attributes: true, attributeFilter: ['hidden'] });

    /* ---- Tap the beat. -----------------------------------------------------
     * Four taps or more, along with Hear the loop; the first tap starts it
     * when it is quiet, and is not counted (it is the start, not a beat). Two
     * seconds without a tap and it settles on the tempo, to the nearest whole
     * beat a minute; tapped again later, it listens again from the start. */
    var tapBtn = $('musicTapBtn'), tapWords = $('musicTapWords'), tempoLine = $('musicTempo');
    var taps = [], tapT = null, tapNote = '';
    function tempo() { return tempoFrom(h.tempo ? h.tempo() : null); }
    function beatSecs() { var tp = tempo(); return tp ? 60 / tp.bpm : 0; }
    // The stretch selected for n beats heard: n of them and the smooth
    // restart's length, or twice n when the restart is longer than that
    // (lib/audioloop.js caps the fold at half the loop).
    function lenFor(n) { var want = n * beatSecs(), xf = h.crossfade() / 1000; return xf <= want ? want + xf : 2 * want; }
    // Where the loop has got to, in the song's seconds, as heard while Hear
    // the loop plays: on the gapless engine, the audio clock less the time the
    // sound takes to reach the ear (a phone's speaker, more with Bluetooth), so
    // the beat marked is the beat tapped to.
    function songNow() {
      if (!pv.on || pv.mode !== 'loop') return null;
      var t = h.trim(), a = h.audio();
      if (pv.engine === 'wa' && h.loop.playing()) return t.start + h.loop.elapsed() - (h.loop.latency ? h.loop.latency() : 0);
      if (pv.engine === 'clip' && pv.el) return t.start + pv.el.currentTime;
      if (pv.engine === 'track' && a) return a.currentTime;
      return null;
    }
    // The gaps a person keeps time with: a fifth of a second to two.
    function gapsOf(ts) {
      var g = [];
      for (var i = 1; i < ts.length; i++) {
        var d = (ts[i].at - ts[i - 1].at) / 1000;
        if (d >= 0.2 && d <= 2) g.push(d);
      }
      return g;
    }
    // One beat, from the gaps: the middle gap finds it, so a stray tap cannot
    // move it, and the gaps near the middle one, averaged, settle it.
    function beatOf(ts) {
      var g = gapsOf(ts), m = median(g), near = g.filter(function (d) { return d >= m * 0.8 && d <= m * 1.25; });
      return near.length ? near.reduce(function (a, d) { return a + d; }, 0) / near.length : m;
    }
    function settle() {
      tapT = null;
      var m = beatOf(taps);
      if (taps.length >= 4 && m > 0) {
        var bpm = Math.round(60 / m), p = 60 / bpm, x = 0, y = 0, n = 0, run = [];
        // Where a beat falls: each tap's place in its beat, averaged round the
        // circle, over the taps since the loop last came round (a loop that is
        // not a whole number of beats puts its next time round's beats elsewhere).
        taps.forEach(function (tp) {
          if (tp.song == null) return;
          if (run.length && tp.song < run[run.length - 1].song) run = [];
          run.push(tp);
        });
        run.forEach(function (tp) { var a = 2 * Math.PI * tp.song / p; x += Math.cos(a); y += Math.sin(a); n++; });
        var ph = n ? ((Math.atan2(y, x) / (2 * Math.PI)) * p + p) % p : 0;
        var next = { bpm: bpm, phase: Math.round(ph * 10000) / 10000 };
        if (tempo() && !snapOn()) next.snap = false;      // tapped again, the switch stays as it was
        if (h.setTempo) h.setTempo(next);
        tapNote = '';
        h.changed();
      } else tapNote = taps.length ? 'Four taps or more, in time with the music.' : '';
      taps = [];
      sync();
    }
    // Every line here is two lines at most on a phone, as tall as the tap
    // itself: the tap stays put under a finger while its words change.
    function syncTap() {
      if (!tapBtn) return;
      var listening = !!tapT, tp = tempo(), m = beatOf(taps);
      tapBtn.classList.toggle('tapping', listening);
      tapBtn.disabled = !h.hasTrack();
      if (tapWords) tapWords.textContent = listening ? 'Keep tapping' : 'Tap the beat';
      if (!tempoLine) return;
      var html = listening
        ? (taps.length >= 2 && m > 0 ? taps.length + ' taps, about <b>' + Math.round(60 / m) + '</b> a minute' : 'Keep tapping along with the beat.')
        : tapNote || (tp ? '<b>' + Math.round(tp.bpm) + ' beats a minute</b>'
            + (tp.heard ? ', heard by Skribl \u00b7 tap to change it' : ' \u00b7 tap again to change it')
          : ears ? 'Listening for the beat\u2026'
          : earsHeard === false ? 'Skribl didn\u2019t hear a steady beat. Tap along with the music to count one.'
          : 'Tap along with the music to count its beats.');
      if (tempoLine._html !== html) { tempoLine.innerHTML = html; tempoLine._html = html; }
    }
    if (tapBtn) tapBtn.addEventListener('click', function () {
      if (!h.hasTrack()) return;
      clearTimeout(tapT);
      tapT = setTimeout(settle, TAP_IDLE_MS);
      tapNote = '';
      if (!(pv.on && pv.mode === 'loop')) {
        // The first tap starts the loop from its top; a drawing that was
        // playing gives way to it.
        if (h.playing()) { var pb = h.playButton && h.playButton(); if (pb) pb.click(); }
        taps = [];
        startLoop(0);
      } else taps.push({ at: global.performance.now(), song: songNow() });
      syncTap();
    });

    /* ---- Beats: how many beats the loop is (the owner: "There should be
     * ways to have skribl pick 4 or 8 16 32"; of the mock, "All yes if it's
     * intuitive"). Under the one line once there is a beat, heard or tapped:
     * of 4, 8, 16 and 32, the counts the 20s cap and the song have room for,
     * the loop's own lit, none while it is not whole bars. A count tapped
     * while the loop is Skribl's (the tag), with ears, is Skribl's pick for
     * that many beats where the loop is: the smoothest stretch inside it
     * when shorter, around it when longer, starting on a bar, and the start
     * kept when it is as good. (Picked from the whole song, 8 beats of a
     * test song moved the loop from 4.2s to 23.5s: not what a tap on 8
     * means.) Otherwise the start stays where it is and the loop is that
     * many beats from it, moved back by whole beats only where the song ends
     * first. The loop glides there, and Undo puts it back. */
    var beatsRow = $('musicBeatsRow'), beatsSeg = $('musicBeatsSeg');
    function ours() {
      var tp = tempo();
      return !!earsHeard && !!tp && !!tp.heard && (isPick(pickNow()) || isPick(beatsPick));
    }
    function repick(c, t) {
      var now = heard(t, h.crossfade()), want = c * earsHeard.period, a = t.start + now - want;
      var P = global.SkriblEars.pick(earsHeard, { duration: t.duration, target: want, maxLoop: T.MAX_LOOP_SECONDS,
        minLoop: T.MIN_LOOP_SECONDS, fadeMs: PICK_FADE_MS, from: Math.max(0, Math.min(t.start, a)), to: Math.max(t.start, a), near: t.start });
      return P && P.beats === c ? fromEars(P, 0) : null;
    }
    function roomFor(c) {
      var p = beatSecs(), xf = h.crossfade() / 1000;
      return p > 0 && c * p + xf <= Math.min(T.MAX_LOOP_SECONDS, h.trim().duration) + EPS;
    }
    function syncBeats() {
      if (!beatsRow || !beatsSeg) return;
      var tp = h.hasTrack() ? tempo() : null, c = countOf(), any = false, btns = beatsSeg.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var n = +btns[i].dataset.beats, fit = !!tp && roomFor(n);
        if (btns[i].hidden !== !fit) btns[i].hidden = btns[i].disabled = !fit;
        any = any || fit;
        btns[i].classList.toggle('on', fit && n === c);
      }
      if (beatsRow.hidden !== !any) { beatsRow.hidden = !any; if (any) glideIn(beatsRow, 'y'); }
    }
    if (beatsSeg) beatsSeg.addEventListener('click', function (ev) {
      var b = ev.target && ev.target.closest && ev.target.closest('button[data-beats]'), c = b ? +b.dataset.beats : 0;
      if (!b || b.disabled || !h.hasTrack() || !tempo() || c === countOf()) return;
      var t = loopNow(), was = state(), P = ours() ? repick(c, t) : null, s, e;
      if (P) {
        // a pick's smooth restart, which what is playing takes at once
        if (h.crossfade() !== P.ms) { setFade(P.ms); rejoin(); }
        if (h.setTempo) h.setTempo(P.tempo);
        s = P.start; e = P.end;
        beatsPick = { start: s, end: e, ms: P.ms };
      } else {
        var p = beatSecs(), len = lenFor(c);
        s = t.start;
        if (s + len > t.duration + EPS) s = Math.max(0, s - Math.ceil((s + len - t.duration) / p - 1e-9) * p);
        e = s + len;
      }
      glideTo(s, e, function () { remember(was); });
    });

    // Snap to the beat, under the tap once there is a tempo, on to start and
    // kept with it in the drafts (SNAP TO THE BEAT, above, has what it does).
    var snapRow = $('musicSnapRow'), snapSw = $('musicSnap'), snapSub = $('musicSnapSub');
    function syncSnap() {
      if (!snapRow) return;
      var tp = tempo(), on = snapOn();
      if (snapRow.hidden !== !tp) { snapRow.hidden = !tp; if (tp) glideIn(snapRow, 'y'); }
      setOn(snapSw, on);
      var w = on ? 'The start you drag lands on a beat, or where the music starts, and the loop on whole bars. Zoomed in, it stays where you put it, and the beat follows.'
        : 'Ends stay exactly where you let them go.';
      if (snapSub && snapSub.textContent !== w) snapSub.textContent = w;
    }
    if (snapSw) snapSw.addEventListener('click', function () {
      var tp = tempo();
      if (!tp || !h.setTempo) return;
      var n = { bpm: tp.bpm, phase: tp.phase };
      if (tp.snap !== false) n.snap = false;
      if (tp.heard) n.heard = true;
      h.setTempo(n);
      h.changed();
      sync();
    });

    /* ---- Smooth restart: the clip's join, folded over its head. ------------
     * The switch turns it on at its last length (Skribl's pick's, until one is
     * set); Fine-tune's Length sets it, today's Crossfade. Whatever is playing
     * takes the new join: the gapless engine from where it had got to (Play's
     * music too), an element's clip from the top. */
    var cf = $('crossfadeSlider'), cfVal = $('crossfadeVal');
    var smooth = $('musicSmooth'), smoothSub = $('musicSmoothSub'), lastFade = PICK_FADE_MS;
    function setFade(ms) {
      h.setCrossfade(ms);
      if (ms > 0) lastFade = ms;
      syncCrossfade();
    }
    function syncCrossfade() {
      var ms = h.crossfade(), s = (ms / 1000).toFixed(2) + 's';
      if (cf) { cf.value = ms; fill(cf); }
      if (cfVal) cfVal.textContent = ms > 0 ? s : 'Off';
      setOn(smooth, ms > 0);
      if (smoothSub) smoothSub.textContent = ms > 0
        ? 'The end fades into the start over ' + s + ', which makes the loop ' + s + ' shorter.'
        : 'A clean cut back to the start.';
    }
    function rejoin() {
      clearTimeout(retimeT);
      retimeT = null;
      if (pv.on) {
        if (pv.mode === 'seam') startSeam();
        else if (pv.engine === 'wa' && h.loop.playing()) h.loop.start(function () { if (pv.on) loopNative(); }, h.loop.elapsed());
        else startLoop(0);
      } else if (h.loop.playing()) h.loop.start(null, h.loop.elapsed());
    }
    function fadeTo(ms) {
      setFade(ms);
      touched();
      h.refresh();          // the amber crossfade bands follow it
      h.changed();
      rejoin();
    }
    if (cf) {
      cf.addEventListener('input', function () { fadeTo(parseInt(cf.value, 10) || 0); });
      if (nudgers) nudgers(cf, { step: 5 });
    }
    if (smooth) smooth.addEventListener('click', function () {
      if (h.hasTrack()) fadeTo(h.crossfade() > 0 ? 0 : lastFade);
    });
    syncCrossfade();

    /* ---- Cut on silence (lib/audioloop.js cutFrames). ----------------------
     * A clean cut clicks where the loop's last sample jumps to its first. On,
     * both ends move together, a few thousandths at most, to where the end
     * runs into the start without the jump; the loop keeps its length, so
     * Fit my drawing and whole bars stay exact. On for a new song. Its words
     * say what it moved, from the same arithmetic as the bake; with a smooth
     * restart there is nothing to cut, and they say that. Whatever plays
     * takes the new cut, as a new smooth restart does. */
    var cutSw = $('musicCut'), cutSub = $('musicCutSub');
    function cutNow() {
      var AL = global.SkriblAudioLoop, t = h.trim();
      if (!AL || !AL.cutSeconds || !h.cut || !h.cut() || !h.buffer()) return 0;
      return AL.cutSeconds({ currentAudioBuffer: h.buffer(), trimStart: t.start, trimEnd: t.end, loopCrossfadeMs: h.crossfade(), cut: true });
    }
    function syncCut() {
      if (!cutSw) return;
      var on = !!(h.cut && h.cut()), d = on ? cutNow() : 0, words;
      setOn(cutSw, on);
      cutSw.disabled = !h.hasTrack();
      if (!on) words = 'Each end cuts exactly where it is set.';
      else if (h.crossfade() > 0) words = 'For a clean cut: with Smooth restart on, the restart is already smooth.';
      else if (!h.buffer()) words = 'The two ends move together to where the loop joins without a click.';
      else if (d === 0) words = 'The end already runs into the start without a click.';
      else words = 'Both ends move ' + (Math.abs(d) < EPS ? 'under a thousandth of a second' : Math.abs(d).toFixed(3) + 's') + ' '
        + (d > 0 ? 'later' : 'earlier') + ', to where the end runs into the start without a click.';
      if (cutSub && cutSub.textContent !== words) cutSub.textContent = words;
    }
    if (cutSw) cutSw.addEventListener('click', function () {
      if (!h.hasTrack() || !h.setCut) return;
      h.setCut(!h.cut());
      touched();
      h.refresh();
      h.changed();
      rejoin();
    });

    /* ---- The music switch, in the file row. --------------------------------
     * Off is silence now: Play's music and any preview. On again while the
     * drawing plays, the music comes back. A preview is a request of its own,
     * so Hear the whole loop and Hear the restart still play while the switch
     * is off. */
    var sw = $('musicToggle');
    if (sw) sw.addEventListener('click', function (e) {
      e.stopPropagation();          // the row behind it would open the picker
      var on = !h.enabled();
      h.setEnabled(on);
      if (!on) { stopPreview(); h.musicOff(); }
      else if (h.playing()) h.musicOn();
      h.syncRow();
      h.changed();
    });

    // The Restart view's hint: the beats to line up once there is a tempo,
    // the music itself before.
    var rvHint = $('musicRvHint');
    function syncRvHint() {
      if (!rvHint) return;
      var w = (tempo() ? 'Line the beats up across the middle: drag either side.' : 'Drag either side to line the music up across the middle.')
        + ' Pull the dot to blend them.';
      if (rvHint.textContent !== w) rvHint.textContent = w;
    }

    // Everything the drawer says, from the loop as it is: the editors call it
    // at the end of every repaint (their updateTrimUI) and when the drawing's
    // length changes. The length is one walk over every point on the Pad, so
    // it is measured once here, and not at all with no song.
    function sync() {
      var secs = h.hasTrack() ? h.drawingSeconds() : 0;
      // The Pad picks when the song's length is known, before it is decoded:
      // the ears start once it is (Flip picks after). A song a draft brings
      // back with a beat Skribl heard is heard again, quietly: its loop and
      // its beat stay as kept (heardIt moves only a new song's pick), and
      // Skribl's pick, the way back to it and Beats know the heard pick
      // again. Not heard again, the pick itself said "Back to Skribl's pick",
      // and that went to the song's first 20 seconds, 40.8 beats from 0:00.
      if (!h.hasTrack()) { if (earsFor || pickedNew) forgetEars(); }
      else if (h.buffer) {
        var buf = h.buffer(), kept = tempo();
        if (buf && buf !== earsFor && (pickedNew || (kept && kept.heard))) listenTo(buf);
      }
      // Smooth restart's switch, words and length too: Flip's draft and file
      // opens set the loop's smooth restart and repainted only the rest, so
      // the line said 19.75s under a switch that said Off (the owner's phone).
      syncCrossfade();
      syncTimes(false);
      syncSteps();
      syncLock();
      syncPicks(secs);
      syncPick(secs);
      syncBeats();
      syncHear(secs);
      syncTap();
      syncSnap();
      syncCut();
      syncRvHint();
      if (tl) tl.draw();
      if (rv) rv.draw();
    }
    sync();

    return {
      sync: sync, syncCrossfade: syncCrossfade, resetView: resetView,
      matchDrawing: matchDrawing, applyPick: applyPick, stopPreview: stopPreview,
      // Play's music: where the song is (song seconds), or null to hide it.
      playhead: function (t) { if (t == null) { if (tl) tl.playhead(null); if (rv) rv.playhead(null); } else showAt(t); },
      previewing: function () { return pv.on; },
      more: function () { return open; },
      tempo: tempo
    };
  }

  global.SkriblMusicDrawer = { wire: wire, tempoFrom: tempoFrom };
})(window);
