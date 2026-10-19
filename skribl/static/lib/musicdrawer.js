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
 *   drawingSeconds()    the drawing's length, for Match Drawing Time
 *   audio()             the track's <audio> element, or null
 *   buffer()            the decoded AudioBuffer, or null
 *   loop                the gapless engine: start(onFail, offset), stop(),
 *                       playing(), elapsed()
 *   clip()              the baked loop { dataUrl, duration }, or null
 *   playing()           the drawing is playing (Play)
 *   setPreviewing(b)    the editor's own flag, which its Play and stop read
 *   enabled()           the music switch; setEnabled(b)
 *   musicOn()           Play's music, joining the drawing where it is
 *   musicOff()          Play's music, stopped
 *   syncRow()           redraw the file row and its switch
 *
 * Returns { syncPan, syncCrossfade, resetView, matchDrawing, stopPreview,
 * previewing }. Editor-only: the player has no drawer and never loads this. */
(function (global) {
  'use strict';

  var SEAM = 1.25;                         // seconds either side of the join
  var STEPS = [0.01, 0.02, 0.05, 0.1];     // the nudge's step sizes, in seconds

  function fill(el) {
    var mn = +el.min, mx = +el.max;
    el.style.setProperty('--slider-fill', (mx > mn ? (+el.value - mn) / (mx - mn) * 100 : 0) + '%');
  }

  function wire(h) {
    var $ = function (id) { return document.getElementById(id); };
    var D = global.SkriblDragTrack, P = global.SkriblEventPoint, T = global.SkriblLoopTrim;
    var Z = global.SkriblZoomStep, nudgers = global.addSliderNudgers;
    var track = $('musicTrack'), wrap = $('zoomTrackWrap');

    /* ---- Trim | Fine-tune, the one pill (lib/segslider.js places it). ----
     * Fine-tune swaps the trim strip for the loop detail IN PLACE; it used to
     * open below the fold behind a quiet row, and a tap seemed to do nothing. */
    var seg = $('fineTuneSeg'), body = $('fineTuneBody');
    if (seg && body) seg.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      var fine = b.id === 'fineTuneToggle';
      var apply = function () {
        seg.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x === b); });
        body.hidden = !fine;
        seg.parentElement.classList.toggle('ft-on', fine);
      };
      // Back to Trim the drawer is ~290px shorter; scrolled near its end, the
      // page would clamp and leap under the finger (lib/drawerdetent.js).
      var det = global.SkriblDrawerDetent;
      if (!fine && det && det.shrinkGently) det.shrinkGently(seg.parentElement, apply); else apply();
      // Whichever canvas now shows was laid out at zero size while hidden.
      requestAnimationFrame(function () {
        h.refresh();
        if (!fine) { h.strip(); return; }
        // Just the waveform into view, not the drawer's whole end: that tucked
        // the dock under the pinned header (verify_ux's phone audit).
        var vh = global.visualViewport ? global.visualViewport.height : global.innerHeight;
        var over = wrap ? wrap.getBoundingClientRect().bottom - vh + 12 : 0;
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
    }

    /* ---- The loop's edges. ------------------------------------------------
     * On the strip a dragged edge stops at the 20 s cap ('constrain'); on the
     * loop detail, and by nudge, it pushes the other edge along ('slide').
     * Declared, not accidental: lib/looptrim.js has the reasons. Every change
     * is saved when it lands, wherever the finger is let go. */
    function setEdge(which, time, mode) {
      var t = h.trim(), n = T.setHandle({ start: t.start, end: t.end, duration: t.duration }, which, time, mode);
      h.setTrim(n.start, n.end);
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
          end: function () { handle.classList.remove('dragging'); h.changed(); }
        };
      });
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
          h.refresh();
        },
        end: function () { range.classList.remove('dragging'); h.changed(); }
      };
    });
    // The nudges, and their step. Only the edges' buttons carry data-which, so
    // the step's own - and + (also .nudge-btn) never move an edge.
    var stepAt = STEPS.length - 1;
    var stepLabel = $('nudgeStepLabel'), finer = $('nudgeStepFiner'), coarser = $('nudgeStepCoarser');
    function syncStep() {
      if (stepLabel) stepLabel.textContent = STEPS[stepAt] + 's';
      if (finer) finer.disabled = stepAt === 0;
      if (coarser) coarser.disabled = stepAt === STEPS.length - 1;
    }
    if (finer) finer.addEventListener('click', function () { stepAt = Math.max(0, stepAt - 1); syncStep(); });
    if (coarser) coarser.addEventListener('click', function () { stepAt = Math.min(STEPS.length - 1, stepAt + 1); syncStep(); });
    document.querySelectorAll('.nudge-btn[data-which]').forEach(function (b) {
      b.addEventListener('click', function () {
        var which = b.dataset.which, dir = parseFloat(b.dataset.amount);
        // A NaN step would corrupt the edge and make the clamp reset the loop.
        if (!h.hasTrack() || (which !== 'start' && which !== 'end') || !isFinite(dir)) return;
        var t = h.trim();
        setEdge(which, (which === 'start' ? t.start : t.end) + dir * STEPS[stepAt], 'slide');
        h.changed();
      });
    });
    syncStep();

    // Match Drawing Time: the loop as long as the drawing, its start kept
    // unless that would run it past the song's end.
    function matchDrawing() {
      var secs = h.drawingSeconds();
      if (!h.hasTrack() || !(secs > 0)) return false;
      var t = h.trim(), len = T.loopLength(secs, t.duration), s = t.start, e = s + len;
      if (e > t.duration) { e = t.duration; s = Math.max(0, e - len); }
      h.setTrim(s, e);
      h.refresh();
      h.changed();
      return true;
    }
    var match = $('matchDrawingBtn');
    if (match) match.addEventListener('click', matchDrawing);

    /* ---- Preview Loop and Test Seam. --------------------------------------
     * Preview Loop plays the posted clip on the gapless engine; where that
     * cannot start (no unlock, now or later), the clip loops on an <audio>
     * element, and before the decode, the track itself loops by hand. */
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
      if (previewBtn) previewBtn.textContent = 'Preview Loop';
    }
    function begin(mode) {
      stopPreview();
      // Claimed before any resume (verify_audiosession section 8's order).
      if (global.SkriblAudioSession) global.SkriblAudioSession.claim();
      pv.on = true;
      pv.mode = mode;
      h.setPreviewing(true);
      if (previewBtn) previewBtn.textContent = 'Stop Preview';
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
      if (pv.on) stopPreview(); else startLoop(0);
    });
    if (seamBtn) seamBtn.addEventListener('click', startSeam);

    /* ---- Crossfade: the clip's join, folded over its head. -----------------
     * Whatever is playing takes the new join: the gapless engine from where it
     * had got to (Play's music too), an element's clip from the top. */
    var cf = $('crossfadeSlider'), cfVal = $('crossfadeVal');
    function syncCrossfade() {
      var ms = h.crossfade();
      if (cf) { cf.value = ms; fill(cf); }
      if (cfVal) cfVal.textContent = ms > 0 ? ms + ' ms' : 'Off';
    }
    function rejoin() {
      if (pv.on) {
        if (pv.mode === 'seam') startSeam();
        else if (pv.engine === 'wa' && h.loop.playing()) h.loop.start(function () { if (pv.on) loopNative(); }, h.loop.elapsed());
        else startLoop(0);
      } else if (h.loop.playing()) h.loop.start(null, h.loop.elapsed());
    }
    if (cf) {
      cf.addEventListener('input', function () {
        h.setCrossfade(parseInt(cf.value, 10) || 0);
        syncCrossfade();
        h.refresh();          // the amber crossfade bands follow the slider
        h.changed();
        rejoin();
      });
      if (nudgers) nudgers(cf, { step: 5 });
      syncCrossfade();
    }

    /* ---- The music switch, in the file row. --------------------------------
     * Off is silence now: Play's music and any preview. On again while the
     * drawing plays, the music comes back. A preview is a request of its own,
     * so Preview Loop and Test Seam still play while the switch is off. */
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

    return {
      syncPan: syncPan, syncCrossfade: syncCrossfade, resetView: resetView,
      matchDrawing: matchDrawing, stopPreview: stopPreview,
      previewing: function () { return pv.on; }
    };
  }

  global.SkriblMusicDrawer = { wire: wire };
})(window);
