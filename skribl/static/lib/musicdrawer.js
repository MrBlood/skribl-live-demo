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
 * SKRIBL'S PICK is what a new song starts as: the first 20 seconds (the whole
 * song, when it is shorter), with a smooth restart. Where the editor asks for
 * it (`fitsByDefault`, the Pad), a drawing already there sets the length
 * instead, as the Pad's add always did. Not on Flip: an animation goes round
 * in a second or two, and a loop that short is a stutter -- Fit my animation
 * is one tap. The pick line says which it is, and once the loop is changed,
 * offers Back to Skribl's pick with an Undo for eight seconds.
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
 * what is HEARD, smooth restart and all: the one line says the beats, and an
 * end let go on the timeline settles where the loop is whole bars, 4, 8, 16 or
 * 32 beats (the owner: "we only ever want 4,8,16,... beats"), the end where
 * the loop comes round, so with a smooth restart the handle sits that much
 * past the beat. The loop slid along the song settles its start on a beat,
 * and - and + move a bar. The tempo is the editor's, saved with the song in
 * its drafts.
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
 *   tempo()             the song's tapped tempo { bpm, phase }, or null;
 *                       setTempo(t), kept with the song in the drafts
 *   dock()              the bar right above the drawer, which More's nudge
 *                       leaves under the pinned header (lib/drawerdetent.js)
 *
 * Returns { sync, syncCrossfade, resetView, matchDrawing, applyPick,
 * stopPreview, playhead, previewing, more, tempo }. SkriblMusicDrawer.tempoFrom(raw)
 * reads a saved tempo back, or null. Editor-only: the player has no drawer and
 * never loads this. */
(function (global) {
  'use strict';

  var SEAM = 1.25;                         // seconds either side of the join
  var LEVEL_KEY = 'skribl_music_level';    // one for both editors: 'fine' is More open
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
  // in the song, in seconds. Anything else is no tempo.
  function tempoFrom(t) {
    var bpm = t ? +t.bpm : NaN, ph = t ? +t.phase : NaN;
    return bpm >= 30 && bpm <= 300 && isFinite(ph) ? { bpm: bpm, phase: ph } : null;
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
     * Whether it is open is remembered, one key for both editors: 'fine' (it
     * was Fine-tune) is open, anything else closed, the old Adjust too.
     * #musicDetail's data-level says which, set before More shows or hides,
     * so lib/drawerdetent.js does not follow it as a song landing. `hidden`
     * takes what More holds out of the Tab order as well as off the screen. */
    var moreBtn = $('fineTuneToggle'), moreBody = $('fineTuneBody');
    var open = false, folding = false, foldT = null;
    try { open = global.localStorage.getItem(LEVEL_KEY) === 'fine'; } catch (e) {}
    function still() { return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
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
      try { global.localStorage.setItem(LEVEL_KEY, open ? 'fine' : 'simple'); } catch (e2) {}
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
      // as lib/drawerdetent.js caps the drawer's own reveals. With the
      // timeline the drawer is tall enough on a phone that More's tile alone
      // let Fit my drawing and Whole song pass under the header (verify_ux's
      // phone audit).
      requestAnimationFrame(function () {
        h.refresh();
        if (rv) rv.draw();
        if (!moreBody || !moreBtn) return;
        var det = global.SkriblDrawerDetent;
        var vh = global.visualViewport ? global.visualViewport.height : global.innerHeight;
        var top = det && det.stuckBottom ? det.stuckBottom() : 0;
        var over = Math.min(moreBody.getBoundingClientRect().bottom - vh + 12, moreBtn.getBoundingClientRect().top - top - 8);
        var bar = h.dock ? h.dock() : null;
        if (bar && bar.offsetParent !== null) over = Math.min(over, bar.getBoundingClientRect().top - top - 4);
        if (over > 0) global.scrollBy({ top: over, behavior: 'smooth' });
      });
    }
    showMore();
    if (moreBtn) moreBtn.addEventListener('click', function () { setMore(!open); });

    // A new song: the timeline starts where it belongs, and the last song's
    // Undo and taps are not this one's.
    function resetView() {
      if (tl) tl.reset();
      forgetUndo();
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
    var locked = false, glideRaf = 0;
    function stopGlide() { if (glideRaf) { global.cancelAnimationFrame(glideRaf); glideRaf = 0; } }
    function setEdge(which, time, mode) {
      stopGlide();
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
    function glideTo(s1, e1) {
      stopGlide();
      var t = h.trim(), s0 = t.start, e0 = t.end, t0 = global.performance.now();
      function step(now) {
        var k = still() ? 1 : Math.min(1, Math.max(0, now - t0) / GLIDE_MS), q = 1 - Math.pow(1 - k, 3);
        h.setTrim(s0 + (s1 - s0) * q, e0 + (e1 - e0) * q);
        h.refresh();
        if (k < 1) { glideRaf = global.requestAnimationFrame(step); return; }
        glideRaf = 0;
        touched();
        h.changed();
      }
      step(t0);
    }
    // With a tempo, an end let go on the timeline settles where the loop is
    // whole bars: of 4, 8, 16 and 32 beats, the count nearest what the finger
    // left that the song and the 20s cap have room for, the other end kept.
    // In the Restart view, a close-up (`pxPerSec`, its scale), an end let go
    // within SNAP_PX of a beat settles on it instead: the loop detail's rule,
    // which the Restart view took over. Either way the end is where the loop
    // comes round, a smooth restart's length before the handle. Typed and
    // stepped ends never settle, nor a locked loop.
    function snap(which, pxPerSec) {
      var tp = tempo(), p = beatSecs();
      if (!tp || locked || !h.hasTrack()) return;
      var t = h.trim(), fold = Math.min(h.crossfade() / 1000, (t.end - t.start) / 2), n;
      if (!pxPerSec) {
        var len = heard(t, h.crossfade()), best = 0;
        var room = Math.min(T.MAX_LOOP_SECONDS, which === 'end' ? t.duration - t.start : t.end);
        BARS.forEach(function (k) {
          var l = lenFor(k);
          if (l > room + EPS || l < T.MIN_LOOP_SECONDS - EPS) return;
          if (!best || Math.abs(len - k * p) < Math.abs(len - best * p)) best = k;
        });
        if (!best || Math.abs(len - best * p) < EPS) return;
        n = T.setHandle({ start: t.start, end: t.end, duration: t.duration }, which,
          which === 'end' ? t.start + lenFor(best) : t.end - lenFor(best), 'constrain');
      } else {
        var at = which === 'start' ? t.start : t.end - fold;
        var beat = tp.phase + Math.round((at - tp.phase) / p) * p;
        if (!(Math.abs(beat - at) * pxPerSec <= SNAP_PX) || Math.abs(beat - at) < EPS) return;
        n = T.setHandle({ start: t.start, end: t.end, duration: t.duration }, which, which === 'start' ? beat : beat + fold, 'slide');
      }
      glideTo(n.start, n.end);
    }
    // Where a loop of `len` starting near `start` starts on a beat: the
    // nearest beat, or at either end of the song the one on the side there is
    // room. `start` itself without a tempo, or with no room either side.
    function beatFor(start, len) {
      var tp = tempo(), p = beatSecs(), d = h.trim().duration;
      if (!tp) return start;
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
      letGo: function (kind, which) { if (kind === 'end') snap(which, 0); else onBeat(); h.changed(); }
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

    /* ---- - and +: 0.1s a press, or a bar once there is a tempo. ----------
     * Each button's name says which, and so does the line under them (it was
     * Each tap, with five steps to choose from). Only the edges' buttons carry
     * data-which. */
    var nudges = [].slice.call(document.querySelectorAll('.nudge-btn[data-which]')), stepLine = $('musicStepLine');
    function stepNow() { var p = beatSecs(); return p > 0 ? 4 * p : 0.1; }
    function syncSteps() {
      var p = beatSecs();
      nudges.forEach(function (b) {
        var w = (b.dataset.which === 'start' ? 'Start' : 'End') + ' of loop, ' + (p > 0 ? 'a bar ' : '0.1s ')
          + (parseFloat(b.dataset.amount) > 0 ? 'later' : 'earlier');
        if (b.getAttribute('aria-label') !== w) b.setAttribute('aria-label', w);
      });
      if (stepLine) stepLine.textContent = !h.hasTrack() ? '' : p > 0 ? '\u2212 and + move a bar, ' + (4 * p).toFixed(2) + 's.' : '\u2212 and + move 0.1s.';
    }
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
    // `drawing`: the drawing's length when the caller has it (sync, below).
    function pickNow(drawing) {
      var d = h.trim().duration;
      if (!(d > 0)) return null;
      var secs = !h.fitsByDefault ? 0 : drawing != null ? drawing : h.drawingSeconds(), ms, end;
      if (secs > 0) { ms = fadeFor(secs); end = T.loopLength(secs + ms / 1000, d); }
      else { end = Math.min(d, T.MAX_LOOP_SECONDS); ms = fadeFor(end); }
      return { start: 0, end: end, ms: ms, fits: secs > 0 && near(heard({ start: 0, end: end }, ms), secs) };
    }
    function isPick(p) {
      var t = h.trim();
      return !!p && near(t.start, p.start) && near(t.end, p.end) && h.crossfade() === p.ms;
    }
    // On a new song, from each editor's add (never a restore): returns the pick.
    function applyPick() {
      var p = pickNow();
      if (!p || !h.hasTrack()) return null;
      var was = h.crossfade();
      stopGlide();
      h.setTrim(p.start, p.end);
      setFade(p.ms);
      h.refresh();
      h.changed();
      if (was !== p.ms) rejoin();
      return p;
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
      var mine = !isPick(pickNow(secs));
      if (pickTag) pickTag.hidden = mine;
      if (back) back.hidden = !mine;
      if (undoBtn) undoBtn.hidden = mine || !undo;
    }
    if (back) back.addEventListener('click', function () {
      var t = h.trim(), was = { start: t.start, end: t.end, ms: h.crossfade() };
      if (!applyPick()) return;
      undo = was;
      clearTimeout(undoT);
      undoT = setTimeout(function () { undo = null; syncPick(); }, UNDO_MS);
      sync();
      if (undoBtn) undoBtn.focus();   // where the button was: focus is not lost
    });
    if (undoBtn) undoBtn.addEventListener('click', function () {
      if (!undo) return;
      var u = undo, was = h.crossfade();
      forgetUndo();
      stopGlide();
      h.setTrim(u.start, u.end);
      setFade(u.ms);
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
        if (h.setTempo) h.setTempo({ bpm: bpm, phase: Math.round(ph * 10000) / 10000 });
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
        : tapNote || (tp ? '<b>' + tp.bpm + ' beats a minute</b> · tap again to change it'
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
      // Smooth restart's switch, words and length too: Flip's draft and file
      // opens set the loop's smooth restart and repainted only the rest, so
      // the line said 19.75s under a switch that said Off (the owner's phone).
      syncCrossfade();
      syncTimes(false);
      syncSteps();
      syncLock();
      syncPicks(secs);
      syncPick(secs);
      syncHear(secs);
      syncTap();
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
