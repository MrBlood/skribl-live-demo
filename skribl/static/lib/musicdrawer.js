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
 * THE VIEW AND ITS FOUR DOORS (the owner, of the mock: "I like D", then
 * "All yes" to the whole drawer). The view is the timeline, the one line
 * under it and the pair that plays; under them Length, Beat, Restart and
 * Exact times, the draw drawer's four tiles, each saying what it is set to
 * and opening its group in place, one at a time: Length, Skribl's pick, Fit
 * my drawing and Whole song with the beats and Lock the length; Beat, Tap
 * the beat and Snap to the beat; Restart, the restart (with the Restart
 * view) and Cut on silence; Exact times, the loop's two times. The doors
 * only show and hide. They were More (the owner: "The music drawer is so
 * complicated... we'll need to streamline it"), one card over all four, and
 * before it three levels, Simple, Adjust and Fine-tune, and before them Trim
 * and Fine-tune. Today's names, kept as ids: Match Drawing Time is Fit my
 * drawing, Test Seam is Hear the restart, Preview Loop is Hear the loop,
 * Crossfade is Smooth restart's length.
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
 * and a loop that short is a stutter -- Fit my animation is one tap. In the
 * Length door Skribl's pick is lit while the loop is it, and once the loop
 * is changed, a tap on it is the way back (to the heard one, with its beat),
 * with an Undo for eight seconds, which brings back the loop and the beat
 * that were there. Its tile says which it is.
 *
 * THE ONE LINE says how long the loop is, in beats once there is a tempo,
 * and against the drawing. It was three: the pick line, Adjust's length
 * line, and Fine-tune's sync line; until the doors, Skribl's pick or the
 * way back to it sat at its end.
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
 * round and round. Both sit under the timeline, a door open or not. An end moved
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
 * that much past the beat. Zoomed in, an end let go near whole bars stays,
 * and the beat changes to make them exact (THE END SETS THE TEMPO, at snap
 * below), with a note and its Undo. The Beat door's tile says where the
 * beat came from: heard, tapped, or by hand from the end. The loop slid along the
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
 *                       when Snap to the beat is off, heard: true when
 *                       Skribl heard it and by: 'end' when the loop's end
 *                       set it, or null; setTempo(t), kept with the song in
 *                       the drafts
 *   say(words, action)  optional: a note, with action { label, onClick } a
 *                       button in it (the Pad's toast, Flip's chip)
 *   dock()              the bar right above the drawer, which a door's
 *                       nudge leaves under the pinned header while the
 *                       door's first control still shows
 *                       (lib/drawerdetent.js)
 *
 * Returns { sync, syncCrossfade, resetView, matchDrawing, applyPick,
 * stopPreview, playhead, previewing, door, tempo }. SkriblMusicDrawer.tempoFrom(raw)
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
  // turned off for it, heard: true when Skribl heard it (lib/musicears.js)
  // rather than taps, and by: 'end' when the loop's end set it (snap, zoomed
  // in). Anything else is no tempo.
  function tempoFrom(t) {
    var bpm = t ? +t.bpm : NaN, ph = t ? +t.phase : NaN;
    if (!(bpm >= 30 && bpm <= 300 && isFinite(ph))) return null;
    var out = { bpm: bpm, phase: ph };
    if (t.snap === false) out.snap = false;
    if (t.heard === true) out.heard = true;
    if (t.by === 'end') out.by = 'end';
    return out;
  }
  // A copy of a tempo, every field kept, for a change to one of them.
  function copyOf(tp) { var o = {}; for (var key in tp) o[key] = tp[key]; return o; }
  // Beats a minute as said: whole, as heard or tapped; to the tenth when the
  // end set it, which is rarely whole ("83.4").
  function bpmSays(tp) { return tp.by === 'end' ? (Math.round(tp.bpm * 10) / 10).toFixed(1) : String(Math.round(tp.bpm)); }
  // Where the beat came from, as the Beat door's tile says it.
  function bpmFrom(tp) { return tp.by === 'end' ? 'by hand' : tp.heard ? 'heard' : 'tapped'; }
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

    /* ---- THE FOUR DOORS: Length, Beat, Restart and Exact times, in place. --
     * One open at a time. A door unfolds joined to its tile and folds away
     * again as the draw drawer's tiles do (lib/drawtiles.js), at once under
     * Reduce Motion; one door for another, the new one unfolds where the old
     * one was. The drawer gets shorter only gently: scrolled near its end,
     * the page would clamp and leap under the finger (lib/drawerdetent.js
     * shrinkGently), so a door folds away before it leaves, and one swapped
     * for a shorter one swaps inside the same hold.
     * THE DOORS START CLOSED, EVERY TIME: on a load, and whenever the music
     * panel is put away, so the drawer opens on its one view, short enough
     * for a phone (as More did: the owner, finding it open from an old
     * Fine-tune, "More starts open"; then the pick, always closed). Nothing
     * remembers them. #musicDetail's data-door says which is open, set
     * before a door shows or hides, so lib/drawerdetent.js does not follow it
     * as a song landing. `hidden` takes what a closed door holds out of the
     * Tab order as well as off the screen. */
    var doorsRoot = $('musicDoors');
    var tiles = doorsRoot ? [].slice.call(doorsRoot.querySelectorAll('.dp-tile[data-dp]')) : [];
    var door = {};
    tiles.forEach(function (t) { door[t.dataset.dp] = { tile: t, panel: $(t.getAttribute('aria-controls')) }; });
    var open = null, folding = null, foldT = null;
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
    function showDoors() {
      if (detail) detail.dataset.door = open || 'none';
      tiles.forEach(function (t) {
        var k = t.dataset.dp, p = door[k].panel;
        t.setAttribute('aria-expanded', String(k === open));
        t.classList.toggle('dp-open', k === open || k === folding);
        if (p && k !== folding) p.hidden = k !== open;
      });
      var at = open || folding;
      if (doorsRoot) {
        if (at) doorsRoot.setAttribute('data-col', String(tiles.indexOf(door[at].tile)));
        else doorsRoot.removeAttribute('data-col');
      }
      doorWords();
    }
    function stopFold(p) {
      clearTimeout(foldT);
      if (!p) return;
      p.classList.remove('dp-folding');
      if (p.getAnimations) p.getAnimations().forEach(function (a) { a.cancel(); });
    }
    function finishFold() {
      if (!folding) return;
      stopFold(door[folding].panel);
      var drop = function () { folding = null; showDoors(); sync(); };
      var det = global.SkriblDrawerDetent;
      if (det && det.shrinkGently && detail) det.shrinkGently(detail, drop); else drop();
    }
    function setDoor(k) {
      if (k === open) return;
      if (folding) finishFold();
      var was = open, det = global.SkriblDrawerDetent;
      open = k;
      if (!k) {
        // Closing: it folds away joined to its tile, then leaves.
        folding = was;
        showDoors();
        var old = door[was].panel;
        if (!old || still() || !old.animate) { finishFold(); return; }
        old.classList.add('dp-folding');
        old.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scaleY(.94)' }],
                    { duration: 180, easing: 'ease-in', fill: 'forwards' });
        foldT = setTimeout(finishFold, 200);
        return;
      }
      if (was && det && det.shrinkGently && detail) det.shrinkGently(detail, showDoors); else showDoors();
      sync();
      var body = door[k].panel, tile = door[k].tile;
      if (body && !still() && body.animate) {
        body.animate([{ opacity: 0, transform: 'scaleY(.92)' }, { opacity: 1, transform: 'none' }],
                     { duration: 220, easing: 'cubic-bezier(.2, .8, .2, 1)' });
      }
      // The Restart view's canvas was laid out at zero size while hidden.
      // Then bring what opened into view (a tap that seemed to do nothing
      // was the old Fine-tune's fault), but never so far that the tiles go
      // under the pinned header -- nor the bar above the drawer, the
      // editor's dock(), as lib/drawerdetent.js caps the drawer's own
      // reveals, unless that would leave even the door's first control below
      // the screen, a tap that seems to do nothing again: then the first
      // control wins. With the timeline the drawer is tall enough for both to
      // bind: More's tile alone let Fit my drawing and Whole song pass under
      // the header on an 844px phone (verify_ux's phone audit), and the bar
      // alone left Smooth restart below a 664px one (verify_sheetswipe).
      requestAnimationFrame(function () {
        h.refresh();
        if (rv) rv.draw();
        if (!body || !tile || open !== k) return;
        var vh = global.visualViewport ? global.visualViewport.height : global.innerHeight;
        var top = det && det.stuckBottom ? det.stuckBottom() : 0;
        var over = Math.min(body.getBoundingClientRect().bottom - vh + 12, tile.getBoundingClientRect().top - top - 8);
        var bar = h.dock ? h.dock() : null, first = body.querySelector('button:not([hidden]), input, select, textarea');
        if (bar && bar.offsetParent !== null) {
          var need = first ? first.getBoundingClientRect().bottom - vh + 12 : 0;
          over = Math.min(over, Math.max(bar.getBoundingClientRect().top - top - 4, need));
        }
        if (over > 0) global.scrollBy({ top: over, behavior: still() ? 'auto' : 'smooth' });
      });
    }
    tiles.forEach(function (t) {
      t.addEventListener('click', function () { setDoor(open === t.dataset.dp ? null : t.dataset.dp); });
    });
    // Put away (the drawer closed, or Photo picked), the door closes with
    // it, at once: nothing of it is on the screen to fold.
    if (panel && global.MutationObserver) new global.MutationObserver(function () {
      if (!panel.hidden || !(open || folding)) return;
      stopFold(door[folding || open].panel);
      open = folding = null;
      showDoors();
    }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });

    /* What each door says it is set to, on its tile, and its name for a
     * screen reader, which has Skribl's mark in words: "Length, Skribl's
     * pick, 8 beats". Length, the loop's length, as the one line counts it
     * (as its card says while the loop is Skribl's pick, whose mark is on the
     * tile's picture then); Beat, the tempo and where it came from ("120 ·
     * heard", tapped, or by hand from the loop's end), where a phone's tile
     * has room for both, else the tempo alone as it was ("120 bpm"; the
     * door's own line always says where it came from), or that Skribl is
     * listening for one; Restart, Smooth or Clean cut; Exact, the loop's two
     * times, as precisely as the tile has room for: to the hundredth, the
     * tenth or the second, so on a phone a time past ten seconds loses its
     * hundredths rather than its end. Each word fits a 390px phone's tile. */
    var NAMES = { length: 'Length', beat: 'Beat', restart: 'Restart', exact: 'Exact times' };
    var lengthSpark = $('musicLengthSpark'), tileRoom = {}, fitsMemo = {};
    function room(tile) {
      var w = tile.clientWidth, cs = global.getComputedStyle(tile);
      return w - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    }
    // Whether `s` fits `v`'s room: measured once for each shape of words
    // (every digit is as wide as any other) and each width of tile.
    function fitsIn(v, s, r) {
      var key = s.replace(/\d/g, '0') + '@' + Math.round(r);
      if (!(key in fitsMemo)) {
        var was = v.textContent;
        v.textContent = s;
        fitsMemo[key] = v.scrollWidth <= r + 0.5;
        v.textContent = was;
      }
      return fitsMemo[key];
    }
    function timesFor(v, tile, a, b) {
      var r = tileRoom[tile.dataset.dp] || (tileRoom[tile.dataset.dp] = room(tile)), s = '';
      for (var d = 2; d >= 0; d--) {
        s = a.toFixed(d) + '\u2013' + b.toFixed(d);
        if (!(r > 0) || fitsIn(v, s, r)) break;
      }
      return s;
    }
    function tempoFor(v, tile, tp) {
      var r = tileRoom[tile.dataset.dp] || (tileRoom[tile.dataset.dp] = room(tile)), n = bpmSays(tp);
      var all = [n + ' \u00b7 ' + bpmFrom(tp), n + ' bpm'];
      for (var i = 0; i < all.length; i++) if (!(r > 0) || fitsIn(v, all[i], r)) return all[i];
      return n;
    }
    global.addEventListener('resize', function () { tileRoom = {}; fitsMemo = {}; });
    function doorWords() {
      if (!tiles.length) return;
      var ok = h.hasTrack(), t = h.trim(), tp = tempo(), lit = lengthLit(), spark = ok && lit === 'pick';
      if (lengthSpark && lengthSpark.hidden !== !spark) lengthSpark.hidden = !spark;
      tiles.forEach(function (tile) {
        var k = tile.dataset.dp, v = tile.querySelector('.dp-v'), w = '';
        if (!v) return;
        if (ok && k === 'length') w = spark && pickSub ? pickSub.textContent : lengthOf(loopNow(), h.crossfade(), tp);
        else if (ok && k === 'beat') w = tp ? tempoFor(v, tile, tp) : ears ? 'Listening' : 'Tap it';
        else if (ok && k === 'restart') w = h.crossfade() > 0 ? 'Smooth' : 'Clean cut';
        else if (ok && k === 'exact') w = timesFor(v, tile, t.start, t.end);
        if (v.textContent !== w) v.textContent = w;
        // Read aloud, the beat in words rather than its dot: "120 beats a minute, heard".
        var said = ok && k === 'beat' && tp ? bpmSays(tp) + ' beats a minute, ' + bpmFrom(tp) : w;
        var name = NAMES[k] + (k === 'length' && spark ? ", Skribl's pick" : '') + (said ? ', ' + said : '') + (open === k ? '. Tap to close' : '');
        if (tile.getAttribute('aria-label') !== name) tile.setAttribute('aria-label', name);
      });
    }

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
    // Skribl's pick and Beats go by, so neither changes its mind on the way.
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
     *     every mark would leave its drum. The tempo keeps its beats a minute,
     *     and where they came from (heard, tapped or the end's): every beat,
     *     bar and snap after counts from that start, and the end follows as
     *     above. Tapped again, the beat is the taps' own;
     *   the end on whole bars the same way, counted from the start wherever
     *     it is: dragging the end never moves a start you have set;
     *   magnified, THE END SETS THE TEMPO (from the Wizard's "click the end
     *     of the first bar"; of the mock, "All yes"): an end let go within an
     *     eighth of a beat of 4, 8, 16 or 32 beats stays, and the beat
     *     becomes the one that makes the loop exactly that many, counted
     *     from its start and heard to where it comes round (a smooth
     *     restart's length before the handle). A live band or an old record
     *     between whole tempos can be matched: tapped, a tempo is whole beats
     *     a minute. It is by: 'end', to the thousandth, no longer the one
     *     heard; a note says so, and its Undo puts the beat back. Further
     *     off, it settles as above.
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
        if (zoomed && h.setTempo && Math.abs(t.start - on) <= p / 8) {
          var ns = copyOf(tp);
          ns.phase = Math.round(s * 10000) / 10000;
          h.setTempo(ns);
        }
        k = barsFor(heard({ start: s, end: t.end }, h.crossfade()), t.duration - s);
        // No whole bars fit from that beat: the start settles alone.
        n = k ? { start: s, end: s + lenFor(k) } : T.setHandle(state, 'start', s, 'constrain');
      } else if (!pxPerSec) {
        // The loop stays as it is, so the room it needs is already there.
        var hz = heard(t, h.crossfade()), kz = 0;
        if (zoomed && h.setTempo) BARS.forEach(function (c) { if (Math.abs(hz - c * p) <= p / 8) kz = c; });
        var bpm = kz ? Math.round(60 * kz / hz * 1000) / 1000 : 0;
        if (kz && Math.abs(hz - kz * p) > EPS && bpm >= 30 && bpm <= 300) {
          var nt = copyOf(tp);
          nt.bpm = bpm; nt.phase = t.start; nt.by = 'end'; delete nt.heard;
          h.setTempo(nt);
          h.refresh();
          endSaid(tp, nt, kz);
          return;
        }
        k = barsFor(hz, t.duration - t.start);
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
    // What the end's tempo says, and the way back: Undo puts the beat back as
    // it was (heard, tapped or an end's), the end staying where it was let
    // go, unless the beat has changed again since.
    function endSaid(was, now, k) {
      if (!h.say) return;
      h.say('The beat fits your loop now: ' + bpmSays(now) + ' a minute, ' + k + ' beats.', {
        label: 'Undo',
        onClick: function () {
          var cur = tempo();
          if (!cur || cur.bpm !== now.bpm || cur.phase !== now.phase) return;
          h.setTempo(was);
          h.refresh();
          h.changed();
        }
      });
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

    /* ---- The Restart view (lib/musicrestart.js), in the Restart door: the
     * end beside the start. Its sides move the ends as the loop detail's
     * handles did, and its dot is the smooth restart's length. ------------ */
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

    /* ---- THE TIMELINE FOLLOWS YOU (the owner, of Exact times: "what it edits
     * is out of view on phone, right?"; of the mock, B; of its first strips,
     * "the loop is too small", twice; then "Yeah"). While the timeline is
     * scrolled up under the header, a copy of it stays there, the drawer's
     * width: the loop and a little of the song either side (a seventh of its
     * length or a beat, whichever is more), the beat marked as the timeline
     * marks it, the two ends, and the one line's length and beats. A press
     * moves an end at once; then the copy eases to frame the new loop, as the
     * timeline eases to its framing when an end is let go. It glides in and
     * away, at once under Reduce Motion, and a tap on it takes the page back
     * up to the timeline. It is fixed to the screen, so it moves to the
     * page's end: a fixed box inside a drawer that transforms rides with it. */
    var follow = $('musicFollow'), fwWords = $('musicFollowWords'), fwCv = $('musicFollowCanvas'), tlRoot = $('musicTimeline');
    var fwOn = false, fwView = null, fwRaf = 0, fwLast = 0, fwPeaks = null;
    if (follow && follow.parentNode !== document.body) document.body.appendChild(follow);
    function headerFoot() { var D = global.SkriblDrawerDetent; return D && D.stuckBottom ? D.stuckBottom() : 0; }
    function fwFrame(t, p) {
      var m = Math.max((t.end - t.start) / 7, p || 0.5), v0 = Math.max(0, t.start - m), v1 = Math.min(t.duration, t.end + m);
      return [v0, Math.max(0.01, v1 - v0)];
    }
    // One frame of the copy; true while it is still easing to its framing.
    function fwDraw(dt) {
      var t = h.trim(), tp = tempo(), p = tp ? 60 / tp.bpm : 0, len = heard(t, h.crossfade());
      var html = '<b>' + len.toFixed(2) + 's</b>' + (p > 0 ? ' · ' + beatWords(len / p) : '');
      if (fwWords && fwWords._html !== html) { fwWords.innerHTML = html; fwWords._html = html; }
      var w = fwCv ? fwCv.clientWidth : 0, hh = fwCv ? fwCv.clientHeight : 0, dpr = global.devicePixelRatio || 1;
      if (!(w > 0) || !(hh > 0)) return false;
      if (fwCv.width !== Math.round(w * dpr) || fwCv.height !== Math.round(hh * dpr)) { fwCv.width = Math.round(w * dpr); fwCv.height = Math.round(hh * dpr); }
      var want = fwFrame(t, p);
      if (!fwView || still()) fwView = want.slice();
      else { var e = 1 - Math.exp(-(dt || 16) / 110); fwView[0] += (want[0] - fwView[0]) * e; fwView[1] += (want[1] - fwView[1]) * e; }
      var easing = Math.abs(want[0] - fwView[0]) > 1e-4 || Math.abs(want[1] - fwView[1]) > 1e-4;
      if (!easing) fwView = want.slice();
      var v0 = fwView[0], span = fwView[1], X = function (s) { return (s - v0) / span * w; };
      var st = global.getComputedStyle(follow), tok = function (n) { return st.getPropertyValue(n).trim(); };
      var acc = tok('--accent'), ink = tok('--accent-ink'), line = tok('--menu-card-line'), paper = tok('--menu-paper');
      var x = fwCv.getContext('2d');
      function rr(a, b, c, d, r) { x.beginPath(); if (x.roundRect) x.roundRect(a, b, c, d, r); else x.rect(a, b, c, d); }
      x.setTransform(dpr, 0, 0, dpr, 0, 0);
      x.clearRect(0, 0, w, hh);
      rr(0.5, 0.5, w - 1, hh - 1, 10); x.fillStyle = paper; x.fill(); x.strokeStyle = line; x.lineWidth = 1; x.stroke();
      x.save(); rr(0, 0, w, hh, 10); x.clip();
      x.fillStyle = acc; x.globalAlpha = 0.16; x.fillRect(X(t.start), 0, X(t.end) - X(t.start), hh); x.globalAlpha = 1;
      // The song as the timeline draws it, from its own peaks.
      var MT = global.SkriblMusicTimeline, buf = h.buffer && h.buffer(), P = (tl && tl.peaks && tl.peaks()) || fwPeaks;
      if (MT && buf && (!P || P.buffer !== buf)) P = fwPeaks = MT.peaksOf(buf);
      if (P) {
        for (var px = 0; px < w; px += 2) {
          var u0 = v0 + px / w * span, u1 = v0 + (px + 2) / w * span;
          if (u1 < 0 || u0 > t.duration) continue;
          var v = MT.peakOf(P, Math.max(0, u0), Math.min(t.duration, u1)), hg = Math.max(1, v * (hh / 2 - 12));
          x.globalAlpha = u1 > t.start && u0 < t.end ? 1 : 0.3;
          x.fillRect(px, hh / 2 + 2 - hg, 1.5, hg * 2);
        }
      }
      // The beat, as the timeline marks it: bigger on each bar from the loop's start.
      if (p > 0) {
        var k0 = Math.round((t.start - tp.phase) / p);
        x.fillStyle = ink;
        for (var kb = Math.ceil((v0 - tp.phase) / p); tp.phase + kb * p <= v0 + span; kb++) {
          var bar = ((kb - k0) % 4 + 4) % 4 === 0;
          x.globalAlpha = bar ? 0.9 : 0.6;
          x.beginPath(); x.arc(X(tp.phase + kb * p), 8, bar ? 2.6 : 1.8, 0, 7); x.fill();
        }
      }
      // The two ends, each with its tab at the foot, as the timeline's: the
      // line as sharp as its (SkriblMusicTimeline.edge), on the canvas's pixels.
      x.globalAlpha = 1; x.fillStyle = acc;
      var edges = [t.start, t.end].map(function (s) {
        var ln = MT && MT.edge ? MT.edge(X(s), dpr, 0) : [Math.round(X(s)) - 1, 2], mid = ln[0] + ln[1] / 2;
        x.fillRect(ln[0], 0, ln[1], hh);
        rr(mid - 7, hh - 10, 14, 10, 4); x.fill();
        return ln;
      });
      x.restore();
      // What is painted, for whoever asks (the harness): the framing, the ends, the words.
      follow._painted = { view: [v0, span], start: X(t.start), end: X(t.end), edges: edges, width: w, words: fwWords ? fwWords.textContent : '' };
      return easing;
    }
    function fwStep(now) {
      fwRaf = 0;
      if (!fwOn) return;
      var dt = fwLast ? Math.min(64, now - fwLast) : 16;
      fwLast = now;
      if (fwDraw(dt)) fwRaf = global.requestAnimationFrame(fwStep);
    }
    // Shown while the timeline is laid out (the drawer open on a song) and
    // above the header's foot; placed under the header, the card's width.
    // A fixed box's left counts from where the page's scrollbar gutter ends
    // (styles.css, scrollbar-gutter: 10px in on this box's desk, more on
    // Windows), not from the screen's edge: that offset is measured, so the
    // copy sits on the card wherever the gutter is.
    function fwPlace() {
      if (!follow || !tlRoot) return;
      var foot = headerFoot(), r = tlRoot.getBoundingClientRect();
      var want = !!h.hasTrack() && tlRoot.offsetParent !== null && r.height > 0 && r.bottom < foot + 4;
      if (want) {
        var card = tlRoot.closest('.media-card') || tlRoot.parentElement, c = card.getBoundingClientRect();
        var gutter = follow.getBoundingClientRect().left - (parseFloat(global.getComputedStyle(follow).left) || 0);
        follow.style.left = (c.left - gutter) + 'px'; follow.style.width = c.width + 'px'; follow.style.top = foot + 'px';
      }
      if (want !== fwOn) {
        fwOn = want;
        if (want) fwView = null;
        follow.classList.toggle('on', want);   // hidden, it is out of reach and unread (visibility)
      }
      if (fwOn && !fwRaf) { fwLast = 0; fwRaf = global.requestAnimationFrame(fwStep); }
    }
    // Placed again on any scroll (the page's, or a drawer's own), a new
    // screen size, and the timeline or the card changing size: a drawer
    // closing takes the timeline out of the layout without a scroll.
    if (follow && tlRoot) {
      follow.addEventListener('click', function () { tlRoot.scrollIntoView({ block: 'center', behavior: still() ? 'auto' : 'smooth' }); });
      document.addEventListener('scroll', fwPlace, { passive: true, capture: true });
      global.addEventListener('resize', fwPlace);
      if (global.visualViewport) global.visualViewport.addEventListener('resize', fwPlace);
      if (global.ResizeObserver) {
        var fwRo = new global.ResizeObserver(fwPlace);
        fwRo.observe(tlRoot);
        if (tlRoot.closest('.media-card')) fwRo.observe(tlRoot.closest('.media-card'));
      }
    }

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
    // the pick is left as it is (the way back goes to the heard one).
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
    function touched() { stopGlide(); if (undo) { forgetUndo(); syncLength(); } retime(); }
    /* ---- The one line: "4.00s · 8 beats · fits your drawing". What is heard
     * each time round, to the hundredth; the beats once there is a tempo;
     * against the drawing once there is one. A loop that was the pick and is
     * not now, because the drawing changed, says only that: shorter or longer
     * than the drawing, and the Length door has the way back. Nobody is told
     * they did something. `secs`: the drawing's length. */
    var pickLine = $('musicPickLine'), pickText = $('musicPickText');
    function against(len, secs) {
      if (!(secs > 0)) return '';
      if (near(len, secs)) return 'fits your ' + work;
      return (len < secs ? 'shorter' : 'longer') + ' than your ' + work;
    }
    function syncLine(secs) {
      if (!pickLine) return;
      pickLine.hidden = !h.hasTrack();
      if (pickLine.hidden) return;
      var len = heard(h.trim(), h.crossfade()), p = beatSecs(), beats = p > 0 ? beatWords(len / p) : '', vs = against(len, secs);
      // what it is against the drawing in a span of its own: on a narrow
      // phone it takes its own row, whatever it says (styles.css)
      var html = '<b>' + len.toFixed(2) + 's</b>' + (beats ? ' · ' + beats : '')
        + (vs ? '<span class="mt-pick-vs"><span class="mt-pick-sep"> · </span>' + vs + '</span>' : beats ? '' : ' loop');
      if (pickText && pickText._html !== html) { pickText.innerHTML = html; pickText._html = html; }
    }

    /* ---- LENGTH: Skribl's pick, Fit my drawing and Whole song. ------------
     * The draw drawer's three choices in the Length door, the one the loop is
     * lit, as the door's tile says. Where two are the same loop (the Pad's
     * pick without ears is as long as the drawing, a short song's is the
     * whole song) the one pressed last is lit, so a press always answers;
     * otherwise Skribl's pick before Fit before Whole song. One is lit at a
     * time, and the one line says the rest. Each says what it makes:
     * the pick its length, in beats when the beat is Skribl's, and lit, the
     * loop's own (a count tapped on Beats is Skribl's pick for that many
     * beats); Fit the drawing's; Whole song the song's, or its first 20s.
     * While a song a draft brought back is heard again, the pick waits,
     * listening: until then it is the one without ears.
     * Fit my drawing: what is heard as long as the drawing, its start kept
     * unless that would run it past the song's end (it was Match Drawing
     * Time). Whole song: the song from its top, or the longest loop there is
     * when the song is longer than that. */
    var pickCard = $('musicPickCard'), pickSub = $('musicPickSub'), undoBtn = $('musicPickUndo');
    var fit = $('matchDrawingBtn'), fitSub = $('musicFitSub');
    var whole = $('musicWholeBtn'), wholeName = $('musicWholeName'), wholeSub = $('musicWholeSub');
    // `chosen`: the card pressed last, lit while it is still the loop, for
    // the song it was pressed on.
    var litNow = null, chosen = null, chosenFor = null;
    function lengthLit() { return litNow; }
    function choose(k) { chosen = k; chosenFor = h.buffer ? h.buffer() : null; }
    // A loop's length heard, in beats of `tp`, or in seconds.
    function lengthOf(t, ms, tp) {
      var len = heard(t, ms);
      return tp && tp.bpm > 0 ? beatWords(len * tp.bpm / 60) : says(len) + 's';
    }
    function lit(el, on) {
      if (!el) return;
      if (el.classList.contains('active') !== on) el.classList.toggle('active', on);
      el.setAttribute('aria-pressed', String(on));
    }
    function syncLength(secs) {
      var t = h.trim(), ok = h.hasTrack(), d = t.duration, ms = h.crossfade();
      if (secs == null) secs = ok ? h.drawingSeconds() : 0;
      syncLine(secs);
      var longest = Math.min(d, T.MAX_LOOP_SECONDS), P = ok ? pickNow(secs) : null, hold = !!ears && !pickedNew;
      var is = { pick: !hold && (isPick(P) || isPick(beatsPick)), fit: secs > 0 && near(heard(t, ms), secs),
                 whole: near(t.start, 0) && near(t.end, longest) };
      var c = chosen && chosenFor === (h.buffer ? h.buffer() : null) ? chosen : null;
      litNow = !ok ? null : c && is[c] ? c
        : is.pick ? 'pick' : is.fit ? 'fit' : is.whole ? 'whole' : null;
      if (pickCard) {
        pickCard.disabled = !ok || hold || !P;
        lit(pickCard, litNow === 'pick');
        var tp = tempo(), w = !ok ? '' : hold ? 'Listening\u2026'
          : litNow === 'pick' ? lengthOf(loopNow(), ms, tp && tp.heard ? tp : null)
          : P ? lengthOf(P, P.ms, P.tempo || null) : '';
        if (pickSub && pickSub.textContent !== w) pickSub.textContent = w;
      }
      if (fit) {
        fit.disabled = !ok || !(secs > 0);
        lit(fit, litNow === 'fit');
        if (fitSub) fitSub.textContent = secs > 0 ? says(secs) + 's' : "once you've drawn";
      }
      if (whole) {
        whole.disabled = !ok;
        lit(whole, litNow === 'whole');
        var all = ok && d <= T.MAX_LOOP_SECONDS + EPS;
        if (wholeName) wholeName.textContent = all || !ok ? 'Whole song' : 'Longest loop';
        if (wholeSub) wholeSub.textContent = !ok ? '' : all ? says(d) + 's' : 'the first ' + says(longest) + 's';
      }
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
      undoT = setTimeout(function () { undo = null; syncLength(); }, UNDO_MS);
      sync();
    }
    // The way back: Skribl's pick, tapped while the loop is not it. The card
    // stays where it is, and the Undo shows under the beats.
    if (pickCard) pickCard.addEventListener('click', function () {
      if (pickCard.disabled || litNow === 'pick') return;
      var was = state(), p = h.hasTrack() ? pickNow() : null;
      if (!p) return;
      choose('pick');
      // the loop is the pick already (pressed after Whole song on a short
      // song): it lights, and there is nothing to undo
      if (isPick(p) || isPick(beatsPick)) { sync(); return; }
      setPick(p);
      remember(was);
    });
    if (undoBtn) undoBtn.addEventListener('click', function () {
      if (!undo) return;
      var u = undo, was = h.crossfade();
      forgetUndo();
      chosen = null;
      stopGlide();
      h.setTrim(u.start, u.end);
      setFade(u.ms);
      if (h.setTempo && u.tempo !== (h.tempo ? h.tempo() : null)) h.setTempo(u.tempo);
      beatsPick = u.pick;
      h.refresh();
      h.changed();
      if (was !== u.ms) rejoin();
      sync();
      // The Undo goes as it is used: focus is not lost, it goes to the way back.
      if (pickCard && !pickCard.disabled) pickCard.focus();
    });

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
    if (fit) fit.addEventListener('click', function () { if (matchDrawing()) { choose('fit'); sync(); } });
    if (whole) whole.addEventListener('click', function () {
      if (!h.hasTrack()) return;
      choose('whole');
      h.setTrim(0, Math.min(h.trim().duration, T.MAX_LOOP_SECONDS));
      touched();
      h.refresh();
      h.changed();
    });

    /* ---- Hear the loop and Test Seam. --------------------------------------
     * Hear the loop (Preview Loop) plays the posted clip on the gapless
     * engine; where that cannot start (no unlock, now or later), the clip
     * loops on an <audio> element, and before the decode, the track itself
     * loops by hand. */
    var previewBtn = $('previewLoopBtn'), seamBtn = $('testSeamBtn');
    var pv = { on: false, mode: null, engine: null, el: null, tick: null, backstop: null };
    // The click and the lit beat (below): whether it clicks, the beats already
    // sent (by the audio clock's millisecond), and the last half second of
    // beats set, each with its tick and its light.
    var clickBtn = $('musicClickBtn'), clickOn = false, beatDone = {}, beatClip = null, beatsSet = [];
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
      beatsOff();
      beatsSet = [];
      pv.from = null;
      beatDone = {};
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
      syncClick();
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
        if (pv.on && pv.mode === 'loop' && pv.engine === 'wa') { h.loop.start(function () { if (pv.on) loopNative(); }, 0); beatsAgain(0); }
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
        every(function () { if (h.loop.playing()) { showAt(h.trim().start + h.loop.elapsed()); beats(); } });
        beatsAgain(offset);
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

    /* ---- The click, and the beat lit as it is heard (the owner's picks in
     * the whole-drawer mock, FUTURE.md 6s). The click: a soft tick on each
     * beat while Hear the loop plays, in one pill with it (a third button in
     * the pair pushed "Play with my drawing" out of its own on a phone), off
     * at first and never in a post or a file: its own sound, straight to the
     * speakers. Each beat's dot on the timeline lights as it reaches the ear,
     * bigger on a bar, the click on or off. Both keep the loop's own audio
     * clock, so they never drift from it: every 30ms (the playhead's tick),
     * the beats due in the next 160ms of what plays, each tick set to the
     * sample and each light to when it is heard (the context's own record of
     * what the speakers play, or the clock less the time the sound takes to
     * reach the ear). A bar is every four beats from the loop's start, as the
     * timeline draws them. The loop's first beat falls in the moment the
     * engine starts ahead of its sound (lib/audioloop.js LEAD), and it waits
     * for the music: it ticks as the music starts, not 30ms before it (the
     * drawer works out when that is: where the start began in the clip, its
     * top by the loop's clock, and LEAD, kept for the harness on the click
     * as _soundFrom). What
     * is set ahead is called off when the loop stops or starts again, and the
     * ticks when the click goes off, so nothing sounds or lights for a loop
     * no longer playing; and no beat is set within a tenth of a second of the
     * last, so a loop started again just after it came round (its timer late)
     * does not tick its first beat twice. On the gapless engine only: the
     * fallbacks have no clock to keep. */
    function syncClick() {
      if (!clickBtn) return;
      var can = h.hasTrack() && !!tempo();
      if (clickBtn.disabled !== !can) clickBtn.disabled = !can;
      var on = String(clickOn);
      if (clickBtn.getAttribute('aria-pressed') !== on) clickBtn.setAttribute('aria-pressed', on);
    }
    if (clickBtn) clickBtn.addEventListener('click', function () {
      clickOn = !clickOn;
      var c = h.loop.ctx ? h.loop.ctx() : null;
      if (!clickOn) beatsOff(true);
      // On while the loop plays: the beats already set ahead (lit, not yet
      // ticked) tick too, so the click starts on the very next beat.
      else if (c && c.state === 'running') beatsSet.forEach(function (x) { if (!x.tick && x.when > c.currentTime + 0.005) x.tick = tick(c, x.when, x.bar); });
      syncClick();
      if (c && c.state === 'suspended' && c.resume) { try { c.resume(); } catch (e) {} }
    });
    // One tick, at `at` on the audio clock: a short sine, higher on a bar.
    function tick(c, at, bar) {
      try {
        var o = c.createOscillator(), g = c.createGain();
        o.type = 'sine';
        o.frequency.setValueAtTime(bar ? 1568 : 1175, at);
        g.gain.setValueAtTime(0.0001, at);
        g.gain.exponentialRampToValueAtTime(bar ? 0.3 : 0.2, at + 0.002);
        g.gain.exponentialRampToValueAtTime(0.0001, at + 0.055);
        o.connect(g); g.connect(c.destination);
        o.start(at); o.stop(at + 0.07);
        return { o: o, g: g, at: at };
      } catch (e) { return null; }
    }
    // The beats set ahead, called off (their lights kept when only the click
    // went off); one already sounding stands.
    function beatsOff(keepLights) {
      var c = h.loop.ctx ? h.loop.ctx() : null, now = c ? c.currentTime : 0;
      beatsSet = beatsSet.filter(function (x) {
        if (x.when <= now) return true;
        if (x.tick) { try { x.tick.g.disconnect(); x.tick.o.stop(0); } catch (e) {} x.tick = null; }
        if (!keepLights && x.lit) { clearTimeout(x.lit); x.lit = null; }
        return !!x.lit;
      });
    }
    // The loop started, or started again `off` seconds into the clip: what
    // was set ahead was for the loop before, and the first beat may be due
    // as its sound begins.
    function beatsAgain(off) { beatsOff(); beatDone = {}; beatClip = null; pv.from = null; pv.off = off || 0; beats(); }
    function beats() {
      var c = h.loop.ctx ? h.loop.ctx() : null, tp = tempo();
      if (!pv.on || pv.mode !== 'loop' || pv.engine !== 'wa' || !c || c.state !== 'running' || !tp || !h.loop.playing()) return;
      var dur = h.loop.duration ? h.loop.duration() : 0;
      if (!(dur > 0)) return;
      // What plays starts where Cut on silence moved the loop's start to:
      // worked out once for each loop, not each tick.
      var t = h.trim(), key = t.start + '|' + t.end + '|' + h.crossfade() + '|' + !!(h.cut && h.cut());
      if (!beatClip || beatClip.key !== key) beatClip = { key: key, start: t.start + cutNow() };
      var p = 60 / tp.bpm, clip0 = beatClip.start, now = c.currentTime, base = now - h.loop.elapsed();
      var lead = (global.SkriblAudioLoop && global.SkriblAudioLoop.LEAD) || 0.03;
      if (pv.from == null) pv.from = base + (pv.off || 0) + lead;      // this start's sound began
      var s0 = pv.from;
      if (clickBtn) clickBtn._soundFrom = s0;
      var k0 = Math.round((t.start - tp.phase) / p), k1 = Math.ceil((clip0 - tp.phase) / p - 1e-6);
      beatsSet = beatsSet.filter(function (x) { return x.when > now - 0.5; });
      var last = beatsSet.length ? beatsSet[beatsSet.length - 1].when : -1;
      for (var pass = 0; pass < 2; pass++) {
        for (var k = k1; k < k1 + 4096; k++) {
          var u = tp.phase + k * p - clip0;
          if (u >= dur - 1e-4) break;
          var at = base + pass * dur + u, when = at;
          // The first beat, set as the music starts: only while it is still
          // to start (it is long past, and forgotten, later in the pass).
          if (at < s0 && at > s0 - lead - 0.004) { if (now > s0 + 0.004) continue; when = Math.max(s0, now); }
          if (when < now - 0.004 || when > now + 0.16 || when - last < 0.1) continue;
          var id = Math.round(at * 1000);
          if (beatDone[id] || beatDone[id - 1] || beatDone[id + 1]) continue;
          beatDone[id] = 1;
          var bar = ((k - k0) % 4 + 4) % 4 === 0, set = { when: when, bar: bar, tick: null, lit: null };
          if (clickOn) set.tick = tick(c, when, bar);
          if (tl && tl.pulse) light(set, tp.phase + k * p, bar, heardIn(c, when, now));
          beatsSet.push(set); last = when;
        }
      }
      var old = Math.round((now - 2) * 1000);
      for (var kk in beatDone) if (+kk < old) delete beatDone[kk];
    }
    // How long until `at` on the audio clock reaches the ear, in ms: from the
    // context's record of what its speakers play now, else the clock less the
    // time the sound takes to reach the ear.
    function heardIn(c, at, now) {
      var ts = c.getOutputTimestamp ? c.getOutputTimestamp() : null, perf = global.performance;
      if (ts && ts.contextTime > 0 && ts.performanceTime > 0 && perf) return Math.max(0, ts.performanceTime + (at - ts.contextTime) * 1000 - perf.now());
      return Math.max(0, (at + (h.loop.latency ? h.loop.latency() : 0) - now) * 1000);
    }
    // A beat's light, `ms` from now: asked again as it comes due, from what
    // the speakers play then (twice at most), so a first guess made as the
    // sound began, before the context's record of it settled, is not early.
    function light(x, song, bar, ms) {
      var tries = 0;
      x.lit = setTimeout(function due() {
        if (!(pv.on && pv.mode === 'loop')) return;
        var c = h.loop.ctx ? h.loop.ctx() : null, left = c ? heardIn(c, x.when, c.currentTime) : 0;
        if (left > 3 && tries++ < 2) { x.lit = setTimeout(due, left); return; }
        x.lit = null;
        tl.pulse(song, bar);
      }, ms);
    }

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
        : tapNote || (tp ? '<b>' + bpmSays(tp) + ' beats a minute</b>'
            + (tp.by === 'end' ? ', set by the loop\u2019s end \u00b7 tap to change it'
              : tp.heard ? ', heard by Skribl \u00b7 tap to change it' : ' \u00b7 tap again to change it')
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
     * intuitive"). In the Length door, under its three choices, once there
     * is a beat, heard or tapped: of 4, 8, 16 and 32, the counts the 20s cap
     * and the song have room for, the loop's own lit, none while it is not
     * whole bars. A count tapped while the loop is Skribl's (its card lit),
     * with ears, is Skribl's pick for
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
        choose('pick');
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
      // Where the beat came from goes with it, heard or set by the end.
      var n = copyOf(tp);
      if (tp.snap !== false) n.snap = false; else delete n.snap;
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
        else if (pv.engine === 'wa' && h.loop.playing()) { var at = h.loop.elapsed(); h.loop.start(function () { if (pv.on) loopNative(); }, at); beatsAgain(at); }
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
      // again. Not heard again, the pick itself offered the way back
      // ("Back to Skribl's pick", then), and that went to the song's first
      // 20 seconds, 40.8 beats from 0:00.
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
      syncLength(secs);
      syncBeats();
      syncHear(secs);
      syncTap();
      syncSnap();
      syncCut();
      syncRvHint();
      doorWords();
      if (tl) tl.draw();
      if (rv) rv.draw();
      fwPlace();
    }
    sync();

    return {
      sync: sync, syncCrossfade: syncCrossfade, resetView: resetView,
      matchDrawing: matchDrawing, applyPick: applyPick, stopPreview: stopPreview,
      // Play's music: where the song is (song seconds), or null to hide it.
      playhead: function (t) { if (t == null) { if (tl) tl.playhead(null); if (rv) rv.playhead(null); } else showAt(t); },
      previewing: function () { return pv.on; },
      door: function () { return open; },
      tempo: tempo
    };
  }

  global.SkriblMusicDrawer = { wire: wire, tempoFrom: tempoFrom };
})(window);
