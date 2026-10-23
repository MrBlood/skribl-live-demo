/* THE MUSIC DRAWER'S CONTROLS, one copy for the Pad and for Flip.
 *
 * The owner, with Flip's Fine-tune on screen: "it needs to be the same music
 * editor on both pad and flip." The drawer's markup was already one file
 * (_skribl_music_drawer.html) and its arithmetic was already shared
 * (lib/looptrim.js, loopwave.js, zoomstep.js, audioloop.js, dragtrack.js). Its
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
 * THREE LEVELS (owner: "like 3 levels of controls. The more control you want,
 * the deeper into the controls you go... no getting rid of anything"). Simple
 * is Skribl's pick, Fit my drawing, Whole song and Play; Adjust adds the
 * typed times, Smooth restart and Hear the restart; Fine-tune is the old
 * Fine-tune re-homed (the loop detail, the steppers, Smooth restart's length)
 * with Each tap, the sync line and Lock the length. A level only shows and
 * hides: switching keeps the loop, and the level is remembered (one key for
 * both editors). Today's names, kept as ids: Trim is Adjust, Match Drawing
 * Time is Fit my drawing, Test Seam is Hear the restart, Preview Loop is Hear
 * the whole loop, Crossfade is Smooth restart's length.
 *
 * SKRIBL'S PICK is what a new song starts as: the first 20 seconds (the whole
 * song, when it is shorter), with a smooth restart. Where the editor asks for
 * it (`fitsByDefault`, the Pad), a drawing already there sets the length
 * instead, as the Pad's add always did. Not on Flip: an animation goes round
 * in a second or two, and a loop that short is a stutter -- Fit my animation
 * is one tap. The pick line says which it is, and once the loop is changed,
 * offers Back to Skribl's pick with an Undo for eight seconds.
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
 * round and round. Both sit under the strip on every level. An end moved
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
 * what is HEARD, smooth restart and all: the length line and the sync line
 * say the beats, Make it sets the end so the loop is that many, Each tap
 * gains one beat, and an end let go within a few pixels of a beat settles on
 * it (the end where the loop comes round, so with a smooth restart the handle
 * sits that much past the beat). The tempo is the editor's, saved with the
 * song in its drafts.
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
 *   view()              { mag, focus, center }; setView(v) writes those given
 *   crossfade()         in ms; setCrossfade(ms)
 *   hasTrack()          a track is loaded and its length is known
 *   refresh()           repaint the drawer (the editor's updateTrimUI)
 *   strip()             redraw the whole-track strip
 *   zoomWindow()        the loop detail's window (getZoomWindow)
 *   changed()           the editor's autosave
 *   drawingSeconds()    the drawing's length, for Fit my drawing
 *   fitsByDefault       Skribl's pick is as long as the drawing (the Pad)
 *   frameSeconds()      one frame: the Pad's video, Flip's pages a second
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
 *
 * Returns { sync, syncCrossfade, resetView, matchDrawing, applyPick,
 * stopPreview, previewing, level, tempo }. SkriblMusicDrawer.tempoFrom(raw)
 * reads a saved tempo back, or null. Editor-only: the player has no drawer and
 * never loads this. */
(function (global) {
  'use strict';

  var SEAM = 1.25;                         // seconds either side of the join
  var LEVELS = ['simple', 'adjust', 'fine'];
  var LEVEL_KEY = 'skribl_music_level';    // one for both editors
  var PICK_FADE_MS = 250;                  // Skribl's pick's smooth restart
  var UNDO_MS = 8000;
  var EPS = 0.0005;                        // two times are one at the thousandth
  var TAP_IDLE_MS = 2000;                  // Tap the beat settles after this long without a tap
  var SNAP_PX = 8;                         // an end let go this near a beat settles on it

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
  function seconds(s) { var w = says(s); return w.indexOf(':') >= 0 ? w : w + (w === '1' ? ' second' : ' seconds'); }
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
    var D = global.SkriblDragTrack, P = global.SkriblEventPoint, T = global.SkriblLoopTrim;
    var Z = global.SkriblZoomStep, nudgers = global.addSliderNudgers;
    var track = $('musicTrack'), wrap = $('zoomTrackWrap'), detail = $('musicDetail');
    var panel = $('musicPanel'), work = (panel && panel.dataset.work) || 'drawing';

    /* ---- The three levels, the one pill (lib/segslider.js places it). ------
     * A block shows on the levels its data-levels names; `hidden` takes it out
     * of the Tab order as well as off the screen. */
    var seg = $('fineTuneSeg'), kept = $('musicKept'), keptT = null;
    var level = 'simple';
    try { var saved = global.localStorage.getItem(LEVEL_KEY); if (LEVELS.indexOf(saved) >= 0) level = saved; } catch (e) {}
    function showLevel() {
      if (detail) {
        detail.dataset.level = level;
        detail.querySelectorAll('[data-levels]').forEach(function (el) {
          el.hidden = el.dataset.levels.split(' ').indexOf(level) < 0;
        });
      }
      if (seg) seg.querySelectorAll('button[data-level]').forEach(function (b) { b.classList.toggle('on', b.dataset.level === level); });
    }
    // Said for a moment, over the strip; it takes no taps and no room.
    function sayKept() {
      if (!kept) return;
      kept.classList.add('show');
      clearTimeout(keptT);
      keptT = setTimeout(function () { kept.classList.remove('show'); }, 2600);
    }
    showLevel();
    if (seg) seg.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-level]');
      if (!b || b.dataset.level === level) return;
      var next = b.dataset.level, shorter = LEVELS.indexOf(next) < LEVELS.indexOf(level);
      try { global.localStorage.setItem(LEVEL_KEY, next); } catch (e2) {}
      var apply = function () { level = next; showLevel(); sync(); };
      // To a smaller level the drawer is shorter; scrolled near its end, the
      // page would clamp and leap under the finger (lib/drawerdetent.js).
      var det = global.SkriblDrawerDetent;
      if (shorter && det && det.shrinkGently && detail) det.shrinkGently(detail, apply); else apply();
      sayKept();
      // Whichever canvas now shows was laid out at zero size while hidden.
      requestAnimationFrame(function () {
        h.refresh();
        h.strip();
        if (next !== 'fine') return;
        // Fine-tune's loop detail opens below the picks: bring its waveform
        // into view (a tap that seemed to do nothing was the old Fine-tune's
        // fault), but never so far that the switch just tapped goes under the
        // pinned header -- nor the dock with it (verify_ux's phone audit).
        var vh = global.visualViewport ? global.visualViewport.height : global.innerHeight;
        var top = det && det.stuckBottom ? det.stuckBottom() : 0;
        var over = wrap ? wrap.getBoundingClientRect().bottom - vh + 12 : 0;
        if (seg) over = Math.min(over, seg.getBoundingClientRect().top - top - 8);
        if (over > 0) global.scrollBy({ top: over, behavior: 'smooth' });
      });
    });

    /* ---- The loop detail's view: focus, magnification, Scroll. ----------
     * The focus group is a real .seg pill; the magnification is a stepper
     * whose markup, ladder and rule are lib/zoomstep.js's (it says why). */
    function syncFocus() {
      var f = h.view().focus;
      document.querySelectorAll('.zoom-mag-btn[data-focus]').forEach(function (b) {
        b.classList.toggle('on', f !== 'free' && b.dataset.focus === f);
      });
    }
    if (wrap && wrap.parentNode && Z) {
      var bar = document.createElement('div');
      bar.className = 'zoom-mag-bar';
      bar.innerHTML = '<span class="seg zoom-seg" data-role="focus" role="group" aria-label="Loop view focus" title="What the loop view centres on">'
        + '<button type="button" class="zoom-mag-btn on" data-focus="loop">Loop</button>'
        + '<button type="button" class="zoom-mag-btn" data-focus="start">Start</button>'
        + '<button type="button" class="zoom-mag-btn" data-focus="end">End</button></span>'
        + Z.markup();
      wrap.parentNode.insertBefore(bar, wrap);
      if (global.SkriblSegSlider) global.SkriblSegSlider.attach(bar.querySelector('.zoom-seg'));
      bar.addEventListener('click', function (e) {
        var b = e.target.closest('.zoom-mag-btn');
        if (b) {
          h.setView({ focus: b.dataset.focus, center: null });
          syncFocus();
          h.refresh();
          return;
        }
        var step = e.target.closest('.mag-step-btn');
        if (!step || step.disabled) return;
        var m = Z.next(h.view().mag, step.id === 'zoomMagIn' ? 1 : -1);
        if (m === h.view().mag) return;
        h.setView({ mag: m });
        Z.sync(m);
        h.refresh();
      });
      Z.sync(h.view().mag);
    }

    // Centre the window on `center` seconds, held inside the song. Taking the
    // view over from Loop/Start/End is 'free': no cell is lit while it is.
    function panTo(center) {
      var d = h.trim().duration, half = h.zoomWindow().duration / 2;
      h.setView({ center: Math.max(half, Math.min(center, Math.max(half, d - half))), focus: 'free' });
      syncFocus();
      h.refresh();
    }
    var pan = $('zoomPanSlider');
    function syncPan() {
      if (!pan) return;
      var d = h.trim().duration;
      if (!(d > 0)) pan.value = 500;
      else {
        var zw = h.zoomWindow();
        pan.value = Math.round(Math.max(0, Math.min(1, (zw.start + zw.end) / 2 / d)) * 1000);
      }
      fill(pan);
    }
    if (pan) {
      pan.addEventListener('input', function () {
        if (h.hasTrack()) panTo(parseInt(pan.value, 10) / 1000 * h.trim().duration);
      });
      if (nudgers) nudgers(pan, { nudgeFn: function (dir) {
        if (!h.hasTrack()) return;
        var zw = h.zoomWindow();
        panTo((zw.start + zw.end) / 2 + dir * zw.duration * 0.1);
      } });
    }
    // Drag the loop detail's waveform to pan it. A drag that starts on an edge
    // handle is the handle's (below), so the two never fight.
    if (wrap && D) D.bind(wrap, function (e) {
      if (!h.hasTrack() || e.target.closest('.zoom-handle')) return null;
      e.preventDefault();
      var rect = wrap.getBoundingClientRect(), zw = h.zoomWindow();
      var from = (zw.start + zw.end) / 2, x0 = P.at(e).clientX;
      wrap.classList.add('panning');
      return {
        move: function (x) { panTo(from - (x - x0) / rect.width * zw.duration); },
        end: function () { wrap.classList.remove('panning'); }
      };
    });
    function resetView() {
      h.setView({ mag: 1, focus: 'loop', center: null });
      if (Z) Z.sync(1);
      syncFocus();
      syncPan();
      // A new song: the last one's Undo, pick and taps are not this one's.
      forgetUndo();
      picked = null;
      taps = [];
      clearTimeout(tapT);
      tapT = null;
      tapNote = '';
    }

    /* ---- The loop's edges. ------------------------------------------------
     * On the strip a dragged edge stops at the 20 s cap ('constrain'); on the
     * loop detail, by nudge and when typed, it pushes the other edge along
     * ('slide'). Declared, not accidental: lib/looptrim.js has the reasons.
     * With Lock the length on, any edge moves the whole loop instead. Every
     * change is saved when it lands, wherever the finger is let go. */
    var locked = false;
    function setEdge(which, time, mode) {
      var t = h.trim(), n;
      if (locked) {
        var len = t.end - t.start, s = Math.max(0, Math.min(t.duration - len, t.start + time - (which === 'start' ? t.start : t.end)));
        n = { start: s, end: s + len };
      } else n = T.setHandle({ start: t.start, end: t.end, duration: t.duration }, which, time, mode);
      h.setTrim(n.start, n.end);
      touched();
      h.refresh();
    }
    function dragEdge(handle, which, rail, zoomed) {
      if (!handle || !rail || !D) return;
      D.bind(handle, function (e) {
        e.preventDefault();
        handle.classList.add('dragging');
        return {
          move: function (x) {
            var rect = rail.getBoundingClientRect(), pct = Math.max(0, Math.min(1, (x - rect.left) / rect.width));
            var zw = zoomed ? h.zoomWindow() : null;
            setEdge(which, zw ? zw.start + pct * (zw.end - zw.start) : pct * h.trim().duration, zoomed ? 'slide' : 'constrain');
          },
          end: function () { handle.classList.remove('dragging'); snap(which, rail, zoomed); h.changed(); }
        };
      });
    }
    // Let go within SNAP_PX of a beat, an end settles on it: the start on the
    // beat, the end where the loop comes round (a smooth restart's length
    // before the handle). Typed and stepped ends never snap, nor a locked loop.
    function snap(which, rail, zoomed) {
      var tp = tempo(), p = beatSecs();
      if (!tp || locked || !h.hasTrack()) return;
      var t = h.trim(), fold = Math.min(h.crossfade() / 1000, (t.end - t.start) / 2);
      var at = which === 'start' ? t.start : t.end - fold;
      var beat = tp.phase + Math.round((at - tp.phase) / p) * p;
      var span = zoomed ? h.zoomWindow().duration : t.duration;
      var px = Math.abs(beat - at) / span * rail.getBoundingClientRect().width;
      if (!(px <= SNAP_PX) || Math.abs(beat - at) < EPS) return;
      setEdge(which, which === 'start' ? beat : beat + fold, zoomed ? 'slide' : 'constrain');
    }
    dragEdge($('handleStart'), 'start', track, false);
    dragEdge($('handleEnd'), 'end', track, false);
    dragEdge($('zoomHandleStart'), 'start', wrap, true);
    dragEdge($('zoomHandleEnd'), 'end', wrap, true);
    // Drag the middle of the loop to slide it along the song, its length kept.
    // Too thin to grab ('narrow'), the edges cover it.
    var range = $('musicRange');
    if (range && track && D) D.bind(range, function (e) {
      if (!h.hasTrack() || range.classList.contains('narrow')) return null;
      e.preventDefault();
      e.stopPropagation();
      range.classList.add('dragging');
      var rect = track.getBoundingClientRect(), t = h.trim(), len = t.end - t.start;
      var grab = (P.at(e).clientX - rect.left) / rect.width * t.duration - t.start;
      return {
        move: function (x) {
          var s = Math.max(0, Math.min((x - rect.left) / rect.width * t.duration - grab, t.duration - len));
          h.setTrim(s, s + len);
          touched();
          h.refresh();
        },
        end: function () { range.classList.remove('dragging'); h.changed(); }
      };
    });

    /* ---- Each tap: what one - or + moves an end by. -----------------------
     * One frame is the editor's own (frameSeconds), so on Flip it follows the
     * pages a second; the four stay in size order, so at 6 a second the frame
     * sits past 0.1s, and the frame's name says its length. Only the edges'
     * buttons carry data-which. */
    var steps = $('musicStepSeg');
    function frameSecs() { var f = h.frameSeconds ? h.frameSeconds() : 0; return f > 0 ? f : 1 / 30; }
    function stepOf(b) { return b.dataset.step === 'frame' ? frameSecs() : b.dataset.step === 'beat' ? beatSecs() : parseFloat(b.dataset.step); }
    function stepNow() {
      var b = steps && steps.querySelector('button.on[data-step]');
      return b ? stepOf(b) : 0.1;
    }
    function syncSteps() {
      if (!steps) return;
      var bs = [].slice.call(steps.querySelectorAll('button[data-step]'));
      var by = bs.slice().sort(function (a, b) { return stepOf(a) - stepOf(b); });
      if (by.some(function (b, i) { return b !== bs[i]; })) by.forEach(function (b) { steps.appendChild(b); });
      var fr = steps.querySelector('button[data-step="frame"]');
      if (fr) { fr.title = '1 frame, 1/' + Math.round(1 / frameSecs()) + ' of a second'; fr.setAttribute('aria-label', fr.title); }
      // One beat, once there is a tempo; gone with it, the tap falls back to 0.1s.
      var bt = steps.querySelector('button[data-step="beat"]');
      if (bt) {
        var tp = tempo();
        bt.hidden = !tp;
        if (tp) { bt.title = '1 beat, ' + (60 / tp.bpm).toFixed(3) + 's at ' + tp.bpm + ' a minute'; bt.setAttribute('aria-label', bt.title); }
        else if (bt.classList.contains('on')) {
          var d = steps.querySelector('button[data-step="0.1"]');
          steps.querySelectorAll('button[data-step]').forEach(function (x) { x.classList.toggle('on', x === d); });
        }
      }
    }
    if (steps) steps.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-step]');
      if (!b) return;
      steps.querySelectorAll('button[data-step]').forEach(function (x) { x.classList.toggle('on', x === b); });
    });
    document.querySelectorAll('.nudge-btn[data-which]').forEach(function (b) {
      b.addEventListener('click', function () {
        var which = b.dataset.which, dir = parseFloat(b.dataset.amount);
        // A NaN step would corrupt the edge and make the clamp reset the loop.
        if (!h.hasTrack() || (which !== 'start' && which !== 'end') || !isFinite(dir)) return;
        var t = h.trim();
        setEdge(which, (which === 'start' ? t.start : t.end) + dir * stepNow(), 'slide');
        h.changed();
      });
    });

    // Typed times, Adjust's to the hundredth and Fine-tune's to the
    // thousandth. A time that is not one puts the loop's own time back.
    var times = [].slice.call(document.querySelectorAll('#musicDetail .mt-time'));
    function syncTimes(force) {
      var t = h.trim(), ok = h.hasTrack();
      times.forEach(function (inp) {
        if (!force && document.activeElement === inp) return;
        var v = inp.dataset.edge === 'start' ? t.start : t.end;
        inp.value = ok ? v.toFixed(inp.classList.contains('edge-readout') ? 3 : 2) : '';
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
    // The loop Skribl's pick last made. Still the loop, but no longer the pick
    // (the Pad's pick follows the drawing), it was the drawing that changed,
    // not the person: the line says so, rather than "your own loop".
    var picked = null;
    // On a new song, from each editor's add (never a restore): returns the pick.
    function applyPick() {
      var p = pickNow();
      if (!p || !h.hasTrack()) return null;
      var was = h.crossfade();
      picked = p;
      h.setTrim(p.start, p.end);
      setFade(p.ms);
      h.refresh();
      h.changed();
      if (was !== p.ms) rejoin();
      return p;
    }
    var undo = null, undoT = null;
    function forgetUndo() { undo = null; clearTimeout(undoT); }
    // Any change made here to the loop: an Undo of the way back is stale.
    function touched() { if (undo) { forgetUndo(); syncPick(); } retime(); }
    var pickLine = $('musicPickLine'), pickText = $('musicPickText');
    var back = $('musicBackPick'), undoBtn = $('musicPickUndo');
    function pickWords(p) {
      var smooth = p.ms > 0 ? ', with a smooth restart.' : '.';
      if (p.fits) return 'Skribl picked the first ' + seconds(heard(p, p.ms)) + ', as long as your ' + work + smooth;
      if (near(p.end, h.trim().duration)) return 'Skribl picked the whole song' + smooth;
      return 'Skribl picked the first ' + seconds(p.end) + smooth;
    }
    function syncPick(drawing) {
      if (!pickLine) return;
      pickLine.hidden = !h.hasTrack();
      if (pickLine.hidden) return;
      var p = pickNow(drawing), mine = !isPick(p);
      if (pickText) pickText.textContent = !mine ? (undo ? "Back to Skribl's pick." : pickWords(p))
        : isPick(picked) ? 'Your ' + work + ' has changed since Skribl picked this loop.' : "You've made your own loop.";
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

    /* ---- What the loop is, against the drawing. ---------------------------
     * Adjust's line to the hundredth; Fine-tune's, under the steppers, to the
     * thousandth and in frames, which is what Each tap's frame steps by. */
    var lenLine = $('musicLenLine'), syncLine = $('musicSyncLine');
    function against(len, secs, dp) {
      if (!(secs > 0)) return '';
      if (near(len, secs)) return 'fits your ' + work;
      var by = Math.abs(len - secs);
      return (dp ? by.toFixed(dp) + 's ' : '') + (len < secs ? 'shorter' : 'longer') + ' than your ' + work;
    }
    function syncLines(secs) {
      var t = h.trim(), ok = h.hasTrack(), len = ok ? heard(t, h.crossfade()) : 0;
      var tp = ok ? tempo() : null, nb = tp ? beatWords(len / beatSecs()) : '';
      if (lenLine) lenLine.textContent = ok ? len.toFixed(2) + 's · ' + (nb ? nb + (against(len, secs, 0) ? ' · ' + against(len, secs, 0) : '')
        : (against(len, secs, 0) || 'loop')) : '';
      if (syncLine) {
        var f = frameSecs(), n = len / f, nf = Math.abs(n - Math.round(n)) < 0.01 ? String(Math.round(n)) : n.toFixed(1);
        var rel = against(len, secs, 3);
        syncLine.textContent = ok ? 'Comes round every ' + len.toFixed(3) + 's · ' + nf + ' frames at ' + Math.round(1 / f) + ' a second'
          + (nb ? ' · ' + nb + ' at ' + tp.bpm + ' a minute' : '') + (rel ? ' · ' + rel : '') : '';
      }
    }

    /* ---- Hear the loop and Test Seam. --------------------------------------
     * Hear the loop (Preview Loop) plays the posted clip on the gapless
     * engine; where that cannot start (no unlock, now or later), the clip
     * loops on an <audio> element, and before the decode, the track itself
     * loops by hand. */
    var previewBtn = $('previewLoopBtn'), seamBtn = $('testSeamBtn');
    var playhead = $('playhead'), zoomPlayhead = $('zoomPlayhead');
    var pv = { on: false, mode: null, engine: null, el: null, tick: null, backstop: null };
    function showAt(song) {
      var d = h.trim().duration;
      if (!(d > 0)) return;
      if (playhead) { playhead.hidden = false; playhead.style.left = song / d * 100 + '%'; }
      if (zoomPlayhead && h.buffer()) {
        var zw = h.zoomWindow();
        zoomPlayhead.hidden = false;
        zoomPlayhead.style.left = Math.max(0, Math.min(100, (song - zw.start) / zw.duration * 100)) + '%';
      }
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
      if (playhead) playhead.hidden = true;
      if (zoomPlayhead) zoomPlayhead.hidden = true;
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

    /* ---- Make it N beats: the three whole counts nearest what is heard. ----
     * The start stays; the end goes where the loop is that many beats, its
     * smooth restart included. A count the song (or the 20s cap) is too short
     * for is faded, and the count the loop is, exactly, wears the one tint. */
    var make = $('musicMake'), counts = make ? [].slice.call(make.querySelectorAll('.mt-count')) : [];
    function lenFor(n) { var want = n * beatSecs(), xf = h.crossfade() / 1000; return xf <= want ? want + xf : 2 * want; }
    function syncMake() {
      if (!make) return;
      var p = beatSecs(), t = h.trim(), ok = h.hasTrack() && p > 0;
      make.hidden = !ok;
      if (!ok) return;
      var len = heard(t, h.crossfade()), r = Math.max(2, Math.round(len / p));
      var cap = Math.min(t.duration, t.start + T.MAX_LOOP_SECONDS);
      counts.forEach(function (c, i) {
        var k = r - 1 + i, l = lenFor(k);
        c.dataset.n = k;
        c.textContent = String(k);
        c.setAttribute('aria-label', 'Make it ' + k + ' beats');
        c.disabled = t.start + l > cap + EPS || l < T.MIN_LOOP_SECONDS;
        setOn(c, Math.abs(len - k * p) < 0.002, 'aria-pressed');
      });
    }
    counts.forEach(function (c) {
      c.addEventListener('click', function () {
        var k = +c.dataset.n;
        if (!h.hasTrack() || !(k > 0) || c.disabled) return;
        var t = h.trim();
        h.setTrim(t.start, t.start + lenFor(k));
        touched();
        h.refresh();
        h.changed();
      });
    });

    /* ---- The beat, marked on the strip and in the loop detail. -------------
     * A tick on every beat that stands 6px from the next (else every fourth,
     * else every sixteenth), taller every four counted from the loop's start,
     * and with a smooth restart a dashed line where the loop comes round.
     * Over the waveform and the loop's tint, under the handles. */
    function lay(host, t0, t1) {
      if (!host) return;
      var box = host.querySelector('.mt-ticks'), tp = tempo(), p = beatSecs(), w = host.clientWidth;
      if (!tp || !h.hasTrack() || !(w > 0) || !(t1 > t0)) { if (box) box.parentNode.removeChild(box); return; }
      if (!box) {
        box = document.createElement('div');
        box.className = 'mt-ticks';
        box.setAttribute('aria-hidden', 'true');
        host.insertBefore(box, host.querySelector('.music-trim-handle, .zoom-handle'));
      }
      var t = h.trim(), ppb = w * p / (t1 - t0), html = '';
      var every = ppb >= 6 ? 1 : ppb * 4 >= 6 ? 4 : ppb * 16 >= 6 ? 16 : 0;
      var k0 = Math.round((t.start - tp.phase) / p);
      if (every) for (var k = Math.ceil((t0 - tp.phase) / p); tp.phase + k * p <= t1 + 1e-9; k++) {
        if (((k - k0) % every + every) % every) continue;
        html += '<i' + (((k - k0) % 4 + 4) % 4 === 0 ? ' class="bar"' : '') + ' style="left:'
          + ((tp.phase + k * p - t0) / (t1 - t0) * 100).toFixed(3) + '%"></i>';
      }
      var fold = Math.min(h.crossfade() / 1000, (t.end - t.start) / 2);
      if (fold > 0) html += '<b style="left:' + ((t.end - fold - t0) / (t1 - t0) * 100).toFixed(3) + '%"></b>';
      if (box._html !== html) { box.innerHTML = html; box._html = html; }
    }
    function syncTicks() {
      var ok = h.hasTrack(), zw = ok && wrap && !wrap.closest('[hidden]') ? h.zoomWindow() : null;
      lay(track, 0, ok ? h.trim().duration : 0);
      lay(wrap, zw ? zw.start : 0, zw ? zw.end : 0);
    }
    var ticksRaf = 0;
    global.addEventListener('resize', function () {
      if (!ticksRaf) ticksRaf = global.requestAnimationFrame(function () { ticksRaf = 0; syncTicks(); });
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

    // Everything the drawer says, from the loop as it is: the editors call it
    // at the end of every repaint (their updateTrimUI) and when the drawing's
    // length changes. The length is one walk over every point on the Pad, so
    // it is measured once here, and not at all with no song.
    function sync() {
      var secs = h.hasTrack() ? h.drawingSeconds() : 0;
      syncPan();
      syncTimes(false);
      syncSteps();
      syncLock();
      syncPicks(secs);
      syncLines(secs);
      syncPick(secs);
      syncHear(secs);
      syncTap();
      syncMake();
      syncTicks();
    }
    sync();

    return {
      sync: sync, syncCrossfade: syncCrossfade, resetView: resetView,
      matchDrawing: matchDrawing, applyPick: applyPick, stopPreview: stopPreview,
      previewing: function () { return pv.on; },
      level: function () { return level; },
      tempo: tempo
    };
  }

  global.SkriblMusicDrawer = { wire: wire, tempoFrom: tempoFrom };
})(window);
