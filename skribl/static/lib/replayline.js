/* How fast a replay runs, and the line that says what you are watching.
 *
 *   SkriblReplayLine.RATES                     the speeds offered, ¼× to 16×
 *   SkriblReplayLine.rate(choice, playMs)      a choice ('fit' or a rate) -> a number
 *   SkriblReplayLine.fromPost(v, drawnMs)      the author's pick in a post -> a choice
 *   SkriblReplayLine.drawnMs(points)           how long it took to draw
 *   SkriblReplayLine.attach(host, opts)        the line, its speed button and the speeds
 *   SkriblReplayLine.clockMap(timeline, pts)   replay ms -> the artist's ms
 *   SkriblReplayLine.scrub(bar, opts)          the drawing's shape in the bar, and dragging it
 *
 * THE OWNER'S SPEC (WORKING-AGREEMENTS.md, "Skribl Pad first"): real time,
 * time-lapse and slow motion, about ¼× to 16× plus "fit", and say what you are
 * watching -- "drawn in 47 min · watching at 8×". The owner picked, from the
 * mocks, the speed IN that line (option B): the words say how fast it is, and
 * the speed in them is the button that opens the speeds. One tap picks and
 * closes. Shared by the Pad's preview (editor_draw.js) and the player
 * (app.js), so the two cannot offer different speeds or say it differently.
 *
 * ONLY THE CLOCK IS SCALED. The stored `t` values are the artifact; a speed is
 * a way of looking at them. What the AUTHOR picks travels in the post as
 * `playSpeed` and is where a viewer STARTS, nothing more: the viewer's own
 * pick is never written anywhere but this browser's preview.
 *
 * FIT lands the whole replay in about FIT_MS, never slower than as drawn, and
 * says the real number it chose ("Fit · 94×"), so a fit is never a mystery.
 * It works on the replay's own length (playMs: the author's pause setting
 * applied), which is what the clock actually runs through.
 *
 * "DRAWN IN" IS THE ARTIST'S TIME, pauses and all: every positive gap between
 * consecutive points, uncapped. A take restarts its clock, so the gap across a
 * take boundary is not positive and adds nothing -- the time spent away
 * between takes is not time spent drawing. When the replay skips a tenth or
 * more of that (Trim or Tight on a drawing with long pauses) the line says
 * "long pauses skipped", so "drawn in 47 min" beside a 3-minute replay at 1×
 * never reads as a wrong number.
 */
(function (global) {
  'use strict';

  var RATES = [0.25, 0.5, 1, 2, 4, 8, 16];
  var FIT_MS = 30000;    // Fit: the whole replay in about this long
  var AUTO_MS = 60000;   // Auto: as drawn under a minute of drawing, Fit over it

  function rate(choice, playMs) {
    return choice === 'fit' ? Math.max(1, (playMs || 0) / FIT_MS) : choice;
  }

  /* The post's `playSpeed`: 'auto', 'drawn', 'fit' or one of RATES. Anything
     else, and a post from before it existed, plays as drawn -- which is
     exactly how every post played until now. */
  function fromPost(v, drawnMs) {
    if (v === 'fit' || RATES.indexOf(v) >= 0) return v;
    return v === 'auto' && drawnMs > AUTO_MS ? 'fit' : 1;
  }

  function drawnMs(pts) {
    var ms = 0;
    for (var i = 1; i < (pts ? pts.length : 0); i++) {
      var g = pts[i].t - pts[i - 1].t;
      if (g > 0) ms += g;
    }
    return ms;
  }

  function words(ms) {
    var s = Math.round(ms / 1000), m = Math.round(ms / 60000);
    return s < 60 ? Math.max(1, s) + ' sec'
      : m < 60 ? m + ' min'
      : Math.floor(m / 60) + ' hr' + (m % 60 ? ' ' + m % 60 + ' min' : '');
  }

  function label(r) {
    return r === 0.25 ? '¼×' : r === 0.5 ? '½×'
      : (r < 10 ? Math.round(r * 10) / 10 : Math.round(r)) + '×';
  }

  var CARET = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5"/></svg>';
  var n = 0;

  /* attach(host, { choice, pick, playMs, drawnMs, fit, compact })
   *   choice()   the current choice ('fit' or a rate)
   *   pick(c)    the caller applies a new choice (re-anchoring its own clock)
   *   playMs()   the replay's length at 1×, for Fit and its number
   *   drawnMs()  the artist's time, or null where it means nothing (a Flip)
   *   fit        false to leave Fit out (a Flip loops; it has no "whole")
   *   compact    true for the speed button and its chips alone, no sentence
   *              (a desk header, beside Play: the owner's D1)
   * Returns { update, close }. The caller calls update() whenever the
   * drawing or the choice changes under it. */
  function attach(host, o) {
    if (!host || !o) return null;
    var id = 'rl' + (++n);
    host.classList.add('replay-line');
    var sp = '<button type="button" class="rl-speed" aria-expanded="false" aria-controls="' + id +
      '"><span></span>' + CARET + '</button>';
    host.innerHTML = (o.compact ? sp : '<span class="rl-text"><span class="rl-drawn"></span>watching at ' + sp +
      '<span class="rl-skip">long pauses skipped</span></span>') +
      '<span class="rl-chips" id="' + id + '" role="group" aria-label="Speed" hidden>' +
      RATES.map(function (r) { return '<button type="button" data-r="' + r + '">' + label(r) + '</button>'; }).join('') +
      (o.fit === false ? '' : '<button type="button" data-r="fit" title="The whole replay in about 30 seconds">Fit</button>') +
      '</span>';
    var btn = host.querySelector('.rl-speed'), chips = host.querySelector('.rl-chips');
    var drawn = host.querySelector('.rl-drawn'), skip = host.querySelector('.rl-skip');

    function open(on) {
      chips.hidden = !on;
      btn.setAttribute('aria-expanded', '' + on);
      host.classList.toggle('open', on);
    }
    function update() {
      var c = o.choice(), p = o.playMs(), d = o.drawnMs ? o.drawnMs() : null;
      btn.firstChild.textContent = (c === 'fit' ? 'Fit · ' : '') + label(rate(c, p));
      // Alone, the button says what it is as well as what it is at.
      if (o.compact) btn.setAttribute('aria-label', 'Replay speed, ' + btn.firstChild.textContent);
      if (drawn) drawn.innerHTML = d ? 'Drawn in <b>' + words(d) + '</b> · ' : '';
      if (skip) skip.hidden = !(d && d - p >= d / 10 && d - p >= 1000);
      chips.querySelectorAll('button').forEach(function (b) {
        b.setAttribute('aria-pressed', '' + (b.dataset.r === String(c)));
      });
    }
    btn.addEventListener('click', function () { open(chips.hidden); });
    chips.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      o.pick(b.dataset.r === 'fit' ? 'fit' : +b.dataset.r);
      update();
      open(false);
      btn.focus();
    });
    host.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !chips.hidden) { open(false); btn.focus(); e.stopPropagation(); }
    });
    document.addEventListener('pointerdown', function (e) {
      if (!chips.hidden && !host.contains(e.target)) open(false);
    });
    update();
    return { update: update, close: function () { open(false); } };
  }

  /* THE ARTIST'S CLOCK. A replay runs through the pauses the author kept and
     skips the rest, so its milliseconds are not the artist's. This maps one
     to the other: each point's replay time (timeline[k].playT) against its
     drawing time (the positive gaps so far, as drawnMs() counts them), and
     between two points it moves in proportion, so a squeezed 40-minute pause
     passes in its 50ms instead of jumping. */
  function clockMap(tl, pts) {
    var d = [0], acc = 0, k;
    for (k = 1; k < tl.length; k++) {
      var g = pts[tl[k].i].t - pts[tl[k - 1].i].t;
      d.push(acc += g > 0 ? g : 0);
    }
    return function (ms) {
      var lo = 0, hi = tl.length - 1;
      if (hi < 1 || ms >= tl[hi].playT) return acc;
      while (lo < hi - 1) { k = (lo + hi) >> 1; if (tl[k].playT <= ms) lo = k; else hi = k; }
      var span = tl[hi].playT - tl[lo].playT;
      return d[lo] + (span > 0 ? (d[hi] - d[lo]) * (ms - tl[lo].playT) / span : 0);
    };
  }
  function clock(ms) {
    var s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
    return (h ? h + ':' + (m < 10 ? '0' : '') : '') + m + ':' + (s % 60 < 10 ? '0' : '') + s % 60;
  }

  /* THE SCRUBBER (the owner's pick S3 from the mocks).
   *
   * THE DRAWING'S SHAPE IN THE BAR: one column per few pixels, as tall as the
   * ink laid down in that stretch of the replay, flat where the artist
   * paused. An outline, a fill and the details read as shapes you can aim at,
   * and on a two-hour piece that is the difference between finding the moment
   * the face went in and guessing. Played columns are the accent; the rest
   * are the accent faded. Painted in the bar's own `color`, so the theme is
   * styles.css's business and not this file's.
   *
   * THE ARTIST'S CLOCK IN A BUBBLE while dragging, so "where am I" is
   * answered in the time the line talks in.
   *
   * FINE SCRUB: slide the finger up off the bar and the same movement covers
   * half, then a quarter, of the replay (iPhone video does this). A press
   * jumps to where it lands; after that every move is RELATIVE, which is what
   * makes the slower pace possible at all.
   *
   * AND THE DRAWING ITSELF: drag(surface) makes a sideways drag anywhere on
   * the drawing scrub too, the whole width for the whole replay, under the
   * thumb on a phone. More than 10px sideways is a drag; less is left alone
   * so a tap still pauses (lib/tappause.js draws the same line).
   *
   * scrub(bar, { points, total, map, frac, seek, start, end })
   *   points()  the timeline (each with x, y, playT, start)
   *   total()   the replay's length at 1x
   *   map()     clockMap() for it, or null (a Flip: no artist's clock)
   *   frac()    where the replay is, 0..1
   *   seek(f)   show the drawing at f
   *   start()   a drag began (hold the replay); end() it ended
   * Returns { paint(f), reset(), drag(surface, on) }. */
  var FINE = [[110, 0.25], [48, 0.5]];
  function scrub(bar, o) {
    if (!bar || !o) return null;
    bar.classList.add('rl-scrub');
    var cv = document.createElement('canvas'), tip = document.createElement('span'),
        head = document.createElement('span');
    cv.className = 'rl-strip'; tip.className = 'rl-bubble'; head.className = 'rl-head';
    [cv, head, tip].forEach(function (e) { e.setAttribute('aria-hidden', 'true'); bar.appendChild(e); });
    var cols = null, drawnCol = -2, drag = null;

    function bin() {
      var tl = o.points() || [], T = o.total() || 1, w = bar.clientWidth;
      var n = Math.max(12, Math.round(w / 5)), c = new Array(n).fill(0), mx = 0, k;
      for (k = 1; k < tl.length; k++) {
        if (tl[k].start) continue;
        var j = Math.min(n - 1, Math.floor(tl[k].playT / T * n));
        c[j] += Math.hypot(tl[k].x - tl[k - 1].x, tl[k].y - tl[k - 1].y);
      }
      for (k = 0; k < n; k++) mx = Math.max(mx, c[k]);
      // No ink to show (a Flip, whose pages are not a stroke timeline): an
      // even track, so the played part still reads.
      cols = c.map(function (v) { return mx ? (v ? Math.sqrt(v / mx) : 0) : 0.2; });
      drawnCol = -2;
    }
    function paint(f) {
      if (!cols) bin();
      var dpr = Math.min(2, window.devicePixelRatio || 1), w = bar.clientWidth, h = bar.clientHeight;
      if (!w || !h) return;
      f = Math.max(0, Math.min(1, f));
      head.style.left = f * 100 + '%';   // the playhead moves smoothly; the columns step
      var n = cols.length, at = Math.round(f * n);
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
        cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); drawnCol = -2;
      }
      if (at === drawnCol) return;   // only when the playhead crosses a column
      drawnCol = at;
      var x = cv.getContext('2d'), cw = cv.width / n, H = cv.height;
      x.clearRect(0, 0, cv.width, H);
      x.fillStyle = getComputedStyle(bar).color;
      for (var k = 0; k < n; k++) {
        if (!cols[k]) continue;
        var ch = Math.max(2 * dpr, (0.15 + 0.85 * cols[k]) * H * 0.78);
        x.globalAlpha = k < at ? 1 : 0.36;
        x.fillRect(k * cw + cw * 0.2, (H - ch) / 2, cw * 0.6, ch);
      }
    }
    function say(f, fine) {
      var T = o.total() || 0, m = o.map && o.map();
      tip.textContent = clock(m ? m(f * T) : f * T) + (fine < 1 ? '  · fine ' + label(fine) : '');
      tip.style.left = f * 100 + '%';
    }
    function begin(e, f) {
      drag = { x: e.clientX, f: f, id: e.pointerId };
      bar.classList.add('dragging');
      o.start();
      move(e);
    }
    function move(e) {
      if (!drag || e.pointerId !== drag.id) return;
      var r = bar.getBoundingClientRect(), up = r.top - e.clientY, fine = 1;
      FINE.forEach(function (p) { if (fine === 1 && up > p[0] && drag.bar) fine = p[1]; });
      drag.f = Math.max(0, Math.min(1, drag.f + (e.clientX - drag.x) / (drag.w || r.width) * fine));
      drag.x = e.clientX;
      o.seek(drag.f); paint(drag.f); say(drag.f, fine);
    }
    function finish(e) {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      drag = null;
      bar.classList.remove('dragging');
      o.end();
    }
    bar.addEventListener('pointerdown', function (e) {
      if (e.button > 0) return;
      try { bar.setPointerCapture(e.pointerId); } catch (_) {}
      var r = bar.getBoundingClientRect();
      e.preventDefault();
      begin(e, Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
      drag.bar = true;
    });
    bar.addEventListener('pointermove', move);
    bar.addEventListener('pointerup', finish);
    bar.addEventListener('pointercancel', finish);

    function dragOn(surface, on) {
      var down = null;
      surface.addEventListener('pointerdown', function (e) {
        down = on() && !e.button ? { x: e.clientX, y: e.clientY, id: e.pointerId } : null;
      });
      surface.addEventListener('pointermove', function (e) {
        if (drag && drag.id === e.pointerId && !drag.bar) return move(e);
        if (!down || e.pointerId !== down.id || Math.abs(e.clientX - down.x) <= 10
            || Math.abs(e.clientX - down.x) < Math.abs(e.clientY - down.y)) return;
        try { surface.setPointerCapture(e.pointerId); } catch (_) {}
        var d = down; down = null;
        begin({ clientX: d.x, pointerId: d.id }, o.frac());
        drag.w = surface.getBoundingClientRect().width;
        move(e);
      });
      ['pointerup', 'pointercancel'].forEach(function (t) {
        surface.addEventListener(t, function (e) { down = null; if (drag && !drag.bar) finish(e); });
      });
    }
    return { paint: paint, reset: function () { cols = null; }, drag: dragOn };
  }

  global.SkriblReplayLine = {
    RATES: RATES, FIT_MS: FIT_MS, rate: rate, fromPost: fromPost,
    drawnMs: drawnMs, words: words, label: label, attach: attach,
    clockMap: clockMap, clock: clock, scrub: scrub
  };
})(window);
