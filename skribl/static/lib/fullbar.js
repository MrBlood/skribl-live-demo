/* The full-screen bar: one transport, and the SAME one on both surfaces.
 *
 * THE BUG THIS EXISTS FOR. The owner sent two screenshots of the same feature:
 * the profile's stage full screen had a way out and no controls, the gallery's
 * tile full screen had controls and no way out, and neither looked like the
 * other. "In the end the two full screens should look identical with controls
 * present on the bottom. all the stuff should be on the bottom."
 *
 * They diverged because each page built its own. So neither page builds one
 * now: this module does, and both call it. Identical is then a property of the
 * code rather than a thing somebody keeps true by hand — the failure mode of
 * two copies is not that one is wrong today, it is that one is fixed tomorrow.
 *
 * WHY IT LIVES INSIDE THE FULLSCREENED ELEMENT. Under the real Fullscreen API
 * only the fullscreened subtree renders, so a bar that sat in the page would
 * simply be gone. It is appended to the wrapper the page fullscreens, and shown
 * only while that wrapper is up.
 *
 * WHAT IT DOES NOT DO. It does not play anything. Every control drives the
 * in-post player's own handle (play/pause/seek/setLoop/setRate and the module's
 * shared sound switch), which is the rule the profile's stage already follows:
 * the buttons are the page's, the clock is the player's. A second replay
 * implementation is the defect verify_sharedrules.py exists about.
 *
 * AND THE COMPONENT'S OWN CHROME YIELDS. The page adds `is-bare` to the player
 * (inlineplayer.css), which hides its cluster and its duration chip. Without
 * that there are two transports on screen, which is the thing being fixed. It
 * does NOT hide the idle veil: that is the play cue, not a control, and a card
 * that drops it is a black rectangle with no sign it moves.
 *
 * ===========================================================================
 * TWO CONFIGURATIONS, ONE BUILDER (v308, direction B)
 * ===========================================================================
 *
 * The owner picked the post-like card, whose footer is a transport under the
 * drawing — which is this bar, with fewer controls and no scrub row of its
 * own. Building a second one in gallery.js would contradict the paragraph
 * above within a day of writing it, so `attach` takes what varies instead:
 *
 *   full screen  restart play loop mute rate | who | exit, scrubber on its
 *                own row, shown only while the wrapper is up.
 *   card footer  play loop mute | scrubber inline | time | full, always shown.
 *
 * Everything else — what a control DOES, how it reads the player's state, the
 * rule that lit means "currently true" — is shared, which is the half that
 * actually rots when it is copied.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  /* The same three the Pad's preview row and /s/ offer. A fourth rate is a
     fourth tap to get back to 1x. */
  var RATES = [1, 2, 0.5];

  function mmss(ms) {
    if (!(ms > 0)) return '0:00';
    var t = Math.round(ms / 1000);
    return Math.floor(t / 60) + ':' + ('0' + (t % 60)).slice(-2);
  }

  function svg(paths, fill) {
    return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="' + (fill || 'none')
      + '" stroke="' + (fill ? 'none' : 'currentColor')
      + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
      + paths + '</svg>';
  }

  var ICON = {
    restart: svg('<path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>'),
    play: svg('<path d="M8 5v14l11-7z"/>', 'currentColor'),
    pause: svg('<rect x="6" y="5" width="4" height="14" rx="1"/>'
               + '<rect x="14" y="5" width="4" height="14" rx="1"/>', 'currentColor'),
    loop: svg('<path d="M17 2l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
              + '<path d="M7 22l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
    sound: svg('<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>'
               + '<path d="M19.5 5.5a9 9 0 0 1 0 13"/>'),
    muted: svg('<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M22 9l-6 6"/><path d="M16 9l6 6"/>'),
    full: svg('<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/>'
              + '<path d="M8 21H5a2 2 0 0 1-2-2v-3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>'),
    exit: svg('<path d="M8 8H5a2 2 0 0 1-2-2V3"/><path d="M16 8h3a2 2 0 0 0 2-2V3"/>'
              + '<path d="M8 16H5a2 2 0 0 0-2 2v3"/><path d="M16 16h3a2 2 0 0 1 2 2v3"/>')
  };

  function btn(cls, label, html) {
    var b = doc.createElement('button');
    b.type = 'button';
    b.className = 'skfull-btn ' + cls;
    b.setAttribute('aria-label', label);
    b.title = label;
    b.innerHTML = html;
    return b;
  }

  /* attach(wrap, opts) -> { sync, el }
   *
   *   wrap        the element the page fullscreens; the bar is appended to it
   *   opts.player function returning the in-post player handle, or null. A
   *               FUNCTION and not the handle itself: the gallery's tile has no
   *               player until somebody presses play, and the profile's stage
   *               swaps its one out every time a different row is selected.
   *   opts.meta   function returning { title, name, handle, avatar } or null
   *   opts.onExit called when the viewer asks to leave
   */
  function attach(wrap, opts) {
    opts = opts || {};
    var getPlayer = opts.player || function () { return null; };
    var getMeta = opts.meta || function () { return null; };
    /* The full-screen set is the default, so the surface that named this
       module does not have to spell itself out. */
    var want = opts.controls || ['restart', 'play', 'loop', 'mute', 'rate'];
    var ownRow = opts.scrubRow !== false;
    var showWho = opts.who !== false;

    var bar = doc.createElement('div');
    bar.className = 'skfull' + (opts.variant ? ' ' + opts.variant : '');

    /* THE SCRUBBER GETS ITS OWN ROW IN FULL SCREEN. Squeezed between the
       buttons it is a 6px target on a phone, which is not a target. On a card
       the row is shorter and it rides inline, where there is width for it. */
    var scrub = doc.createElement('div');
    scrub.className = 'skfull-scrub';
    var at = doc.createElement('span');
    at.className = 'skfull-time';
    at.textContent = '0:00';
    var track = doc.createElement('div');
    track.className = 'skfull-track';
    track.setAttribute('role', 'slider');
    track.setAttribute('aria-label', 'Position');
    var fill = doc.createElement('div');
    fill.className = 'skfull-fill';
    track.appendChild(fill);
    var dur = doc.createElement('span');
    dur.className = 'skfull-time skfull-dur';
    dur.textContent = '0:00';

    var row = doc.createElement('div');
    row.className = 'skfull-row';

    var made = {};
    made.restart = btn('skfull-restart', 'Restart', ICON.restart);
    made.play = btn('skfull-play', 'Play', ICON.play);
    made.loop = btn('skfull-loop', 'Repeat', ICON.loop);
    made.mute = btn('skfull-mute', 'Mute', ICON.sound);
    made.rate = btn('skfull-rate', 'Speed', '');
    made.rate.textContent = '1\u00d7';
    made.full = btn('skfull-full', 'Full screen', ICON.full);
    var bRestart = made.restart, bPlay = made.play, bLoop = made.loop;
    var bMute = made.mute, bRate = made.rate;

    if (ownRow) {
      scrub.appendChild(at);
      scrub.appendChild(track);
      scrub.appendChild(dur);
      bar.appendChild(scrub);
    }
    for (var i = 0; i < want.length; i++) {
      if (made[want[i]]) row.appendChild(made[want[i]]);
    }
    /* Inline: the track takes the space the meta line would have, and the one
       time shown is the DURATION, because a card is answering "how long is
       this" rather than "where am I". */
    if (!ownRow) { row.appendChild(track); row.appendChild(dur); }

    /* WHO AND WHAT, on the same bar. Full screen is the one place a viewer has
       no card around the drawing to read, so the bar carries it there — and
       does not on a card, where the head says it already. */
    var av = doc.createElement('span');
    av.className = 'skfull-av';
    av.setAttribute('aria-hidden', 'true');
    var tTitle = doc.createElement('div');
    tTitle.className = 'skfull-title';
    var tWho = doc.createElement('div');
    tWho.className = 'skfull-by';
    if (showWho) {
      var who = doc.createElement('div');
      who.className = 'skfull-who';
      var words = doc.createElement('div');
      words.className = 'skfull-words';
      words.appendChild(tTitle);
      words.appendChild(tWho);
      who.appendChild(av);
      who.appendChild(words);
      row.appendChild(who);
    }

    var bExit = null;
    if (!opts.controls || want.indexOf('exit') >= 0 || opts.onExit) {
      bExit = btn('skfull-exit', 'Leave full screen', ICON.exit);
      if (!opts.controls || want.indexOf('exit') >= 0) row.appendChild(bExit);
    }
    bar.appendChild(row);
    wrap.appendChild(bar);

    function player() { return getPlayer(); }

    function seekTo(e) {
      var pl = player();
      if (!pl) return;
      var st = pl.state();
      if (!st.totalMs) return;
      var r = track.getBoundingClientRect();
      var f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      pl.seek(st.totalMs * f);
      sync();
    }

    track.addEventListener('click', seekTo);
    if (made.full) made.full.addEventListener('click', function (e) {
      e.stopPropagation();
      if (opts.onFull) opts.onFull();
    });
    bRestart.addEventListener('click', function () {
      var pl = player();
      if (!pl) return;
      pl.seek(0);
      pl.play();
      sync();
    });
    bPlay.addEventListener('click', function () {
      var pl = player();
      if (pl) { pl.toggle(); sync(); }
    });
    bLoop.addEventListener('click', function () {
      var pl = player();
      if (!pl) return;
      pl.setLoop(!pl.looping());
      sync();
    });
    bMute.addEventListener('click', function () {
      var SI = global.SkriblInline;
      if (!SI) return;
      SI.setSoundOn(!SI.soundOn());
      sync();
    });
    bRate.addEventListener('click', function () {
      var pl = player();
      if (!pl) return;
      /* sync() RUNS WHATEVER setRate DOES, and that is what the `finally` is
       * for. It used to be the line after, so anything thrown inside --
       * setRate rebuilds the audio graph, on a context the browser is allowed
       * to take away -- skipped the repaint and left the label reading 1x over
       * a player that had already changed speed. A person pressing a control
       * that does not change is looking at a broken control whether the cause
       * is the control or the report on it, and the owner has now reported
       * "the 1x speed does not change when clicked" twice.
       *
       * (setRate no longer lets that throw escape either; both halves are
       * here because either one alone leaves the other's failure silent.) */
      var i = RATES.indexOf(pl.rate());
      try { pl.setRate(RATES[(i + 1) % RATES.length]); } finally { sync(); }
    });
    if (bExit) bExit.addEventListener('click', function () {
      if (opts.onExit) opts.onExit();
    });

    /* Every control reads the PLAYER's state rather than remembering its own.
       A control that keeps a copy is a control that lies the moment anything
       else moves the thing it is about — a replay ending, a row being swapped
       under the stage, another post claiming the page's sound. */
    function sync() {
      var pl = player();
      var st = pl ? pl.state() : null;
      var playing = !!st && st.state === 'playing';
      bPlay.innerHTML = playing ? ICON.pause : ICON.play;
      bPlay.title = playing ? 'Pause' : 'Play';
      bPlay.setAttribute('aria-label', bPlay.title);

      var loop = !!(pl && pl.looping());
      bLoop.classList.toggle('on', loop);
      bLoop.setAttribute('aria-pressed', String(loop));
      bLoop.title = loop ? 'Repeating' : 'Plays once';

      var SI = global.SkriblInline;
      var on = !!(SI && SI.soundOn());
      var has = !!(st && st.hasAudio);
      bMute.innerHTML = on ? ICON.sound : ICON.muted;
      bMute.disabled = !has;
      bMute.title = !has ? 'This Skribl has no sound' : (on ? 'Sound is on' : 'Sound is off');
      bMute.setAttribute('aria-label', bMute.title);
      bMute.setAttribute('aria-pressed', String(!on));

      var r = pl ? pl.rate() : 1;
      bRate.textContent = r === 0.5 ? '½×' : r + '×';
      bRate.title = 'Speed: ' + bRate.textContent + ' — tap to change';
      bRate.setAttribute('aria-label', bRate.title);

      var total = (st && st.totalMs) || 0;
      var el = (st && st.elapsedMs) || 0;
      fill.style.width = (total ? Math.min(1, el / total) * 100 : 0) + '%';
      at.textContent = mmss(el);
      /* A card answers "how long is this"; full screen answers "where am I",
         and shows both. */
      dur.textContent = ownRow ? mmss(total)
        : (playing || el > 0 ? mmss(el) + ' / ' + mmss(total) : mmss(total));
      track.setAttribute('aria-valuenow', String(Math.round(total ? el / total * 100 : 0)));

      if (made.full) {
        var big = !!(opts.isFull && opts.isFull());
        made.full.setAttribute('aria-pressed', String(big));
        made.full.title = big ? 'Leave full screen' : 'Full screen';
        made.full.setAttribute('aria-label', made.full.title);
      }

      if (!showWho) return;
      var m = getMeta() || {};
      tTitle.textContent = m.title || 'Untitled Skribl';
      tWho.textContent = m.name ? (m.handle ? m.name + ' · ' + m.handle : m.name)
                                : (m.handle || '');
      tWho.hidden = !tWho.textContent;
      av.textContent = '';
      av.hidden = !m.name && !m.handle;
      if (m.avatar) {
        var img = doc.createElement('img');
        img.src = m.avatar;
        img.alt = '';
        img.addEventListener('error', function () {
          img.remove();
          av.textContent = (m.name || m.handle || '?').replace('@', '').charAt(0).toUpperCase();
        });
        av.appendChild(img);
      } else if (!av.hidden) {
        av.textContent = (m.name || m.handle || '?').replace('@', '').charAt(0).toUpperCase();
      }
    }

    /* The clock moves without anybody pressing anything, so the bar follows it
       on a frame loop while it is on screen and stops dead when it is not — a
       rAF per hidden bar per tile is a feed burning battery on nothing.

       AND A BAR THAT IS ON SCREEN BUT IDLE IS THE SAME WASTE AT LOWER VOLUME.
       Full screen is one bar over one drawing and can afford every frame; a
       gallery is one bar per card and the cards are almost all stopped, so
       `running(true)` on a 24-tile grid meant 24 loops repainting the same
       0:00 sixty times a second. The loop therefore reads the player and
       chooses its own next beat: a frame while it is PLAYING, because the
       scrubber has to move smoothly, and a quarter second while it is not,
       because the only thing that changes on a stopped card is somebody else
       claiming the page's sound — which may be noticed late and must not be
       missed. Every control still calls sync() itself, so nothing a person
       does here waits on the tick. */
    var IDLE_MS = 250;
    var raf = null, tick = null;
    function beat() {
      sync();
      var pl = player();
      var st = pl ? pl.state() : null;
      if (st && st.state === 'playing') {
        tick = null;
        raf = global.requestAnimationFrame(beat);
      } else {
        raf = null;
        tick = global.setTimeout(beat, IDLE_MS);
      }
    }
    function running(on) {
      if (on) { if (!raf && !tick) beat(); return; }
      if (raf) global.cancelAnimationFrame(raf);
      if (tick) global.clearTimeout(tick);
      raf = null;
      tick = null;
    }

    /* ---- the band the bar occupies, published to the thing it sits on ----
     *
     * IN FULL SCREEN THE BAR IS NOT ALLOWED TO STAND ON THE DRAWING. It is
     * absolutely positioned at the bottom with a scrim, on the reasoning that
     * a picture reads fine under a soft gradient -- which is how a video
     * player works and is wrong here, because a drawing is the entire content
     * and its bottom edge is part of it. The owner, on a pug whose feet were
     * behind the controls: "fullscreen where the controls cover the bottom of
     * the canvas?"
     *
     * So the host reserves the bar's height as padding and the drawing is
     * centred in what is left. MEASURED AND NOT ASSUMED: the bar's height
     * moves with the safe-area inset, the scrub row, the text metrics of
     * whatever font resolved, and a hard-coded number would be right on this
     * machine and wrong on a phone with a home indicator. A ResizeObserver
     * answers with whatever the bar actually became.
     *
     * The CARD's bar does no such thing -- it is hidden in full screen, and
     * on a card the overlay is the point. Two bars share this wrapper, so the
     * card's is filtered out here rather than at the CSS, or the last one to
     * measure would win. */
    if (opts.variant !== 'skfull-card') {
      wrap.classList.add('skfull-host');
      if (global.ResizeObserver) {
        new global.ResizeObserver(function (rec) {
          var h = rec[0] ? rec[0].target.offsetHeight : 0;
          wrap.style.setProperty('--skfull-band', (h || 0) + 'px');
        }).observe(bar);
      }
    }

    sync();
    return { el: bar, sync: sync, running: running };
  }

  global.SkriblFullBar = { attach: attach, RATES: RATES };
})(window);
