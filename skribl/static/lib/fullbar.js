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
    /* The speed this control last ASKED for, per bar. Null until the first
       press, so an untouched bar steps from whatever the player reports and
       nothing changes for the surfaces that were already working. See the
       rate handler for why a control that reads only the player cannot
       advance when the player stops agreeing with it. */
    var wanted = null;

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
      /* THE STEP IS TAKEN FROM WHAT THIS CONTROL LAST ASKED FOR WHENEVER THE
       * PLAYER DISAGREES WITH IT, and that is the third report's fix.
       *
       * Reading `pl.rate()` and stepping from it is correct only while the
       * handle answering is the one the last press wrote to. When it is not
       * -- a player rebuilt under the bar, a handle swapped for another card's
       * -- the read comes back at the default and the cycle recomputes the
       * SAME next value every press. That is exactly the owner's third
       * report, in all three of its shapes: "goes to 2x and sticks at 2x"
       * (read says 1, so 2 every time), "got one to ½x and it stays there",
       * and "in the gallery it does nothing at all" -- because an UNKNOWN
       * rate gives indexOf -1, and (-1 + 1) % 3 is 0, so every press asks for
       * 1x and a control already at 1x looks dead. Three symptoms, one cause.
       *
       * It could not be reproduced here: Chromium, touch or click, one tile
       * or eight, cycles 1 → 2 → ½ → 1 and calls setRate exactly once per tap.
       * The reports are from iOS Safari and this container has no WebKit to
       * drive, so this hardens the failure rather than having watched it.
       *
       * `wanted` is NOT a copy of the player's state for display -- the label
       * below still reads the player, so it cannot lie about the speed being
       * run. It is only this control's memory of its own last request, which
       * is the one thing the player cannot tell it. */
      var now = pl.rate();
      var from = (wanted !== null && now !== wanted) ? wanted : now;
      var i = RATES.indexOf(from);
      if (i < 0) i = RATES.indexOf(wanted);   // still unknown: our own last ask
      if (i < 0) i = 0;                       // first press on a strange rate
      wanted = RATES[(i + 1) % RATES.length];
      try { pl.setRate(wanted); } finally { sync(); }
    });
    if (bExit) bExit.addEventListener('click', function () {
      if (opts.onExit) opts.onExit();
    });

    /* Every control reads the PLAYER's state rather than remembering its own.
       A control that keeps a copy is a control that lies the moment anything
       else moves the thing it is about — a replay ending, a row being swapped
       under the stage, another post claiming the page's sound. */
    /* WRITE ONLY WHAT CHANGED, and this is not a micro-optimisation -- it is
       why the speed button did not answer a press.
     *
     * `sync()` runs on a FRAME while the drawing plays, and it used to assign
     * every label, icon and title unconditionally. `innerHTML =` and
     * `textContent =` REPLACE a node's children even when the new value is
     * identical, so the bar tore its own buttons apart and rebuilt them about
     * 67 times a second. Measured on a playing card: 1,750 DOM mutation
     * records per second, 134 rebuilds of the play and mute buttons in two
     * seconds, and the rate button's own contents replaced under the pointer.
     *
     * A press whose element is removed and re-inserted between the mousedown
     * and the mouseup produces NO CLICK -- the node keeps its listeners, so
     * pointerdown and pointerup still arrive, which is exactly what the
     * owner's console showed: six down/up pairs in a row with no click
     * between them, then one that got through. "It works sometimes" is what a
     * race against a 60Hz rebuild looks like from the outside.
     *
     * The title writes had a second cost: `lib/tooltip.js` watches the
     * `title` attribute, so 345 title writes a second woke its observer 345
     * times a second to move the same string to `data-tip` and strip it
     * again, which sync then restored on the next frame. The two modules were
     * fighting each other at frame rate.
     *
     * So: compare first, assign only on a difference. The bar reads the same
     * and stops rebuilding itself. */
    /* COMPARING AGAINST THE DOM IS NOT ENOUGH, and both exceptions cost a
       frame's worth of rebuilding until they were found by measuring again
       after the first attempt:

       `innerHTML` RE-SERIALISES. The value read back is the browser's own
       spelling of the markup -- attribute order and self-closing tags
       normalised -- so `el.innerHTML !== ICON.play` was true every time for an
       icon that had not changed, and the guard rebuilt exactly what it was
       meant to protect. Remember the string we SET instead.

       AND THE TITLE IS NOT OURS ALONE. `lib/tooltip.js` moves `title` to
       `data-tip` and removes it, on purpose, so the native bubble cannot
       stack under the drawn one -- which means `el.title` reads back empty
       for a title that is perfectly current, and a DOM comparison re-set it
       on every frame, waking that module's observer to strip it again. The
       two were fighting at frame rate. Comparing against our own last value
       ends it, and updating `data-tip` where tooltip has taken over keeps the
       drawn bubble honest. */
    function setHTML(el, html) {
      if (el._skHTML === html) return;
      el._skHTML = html;
      el.innerHTML = html;
    }
    function setText(el, txt) { if (el.textContent !== txt) el.textContent = txt; }
    function attr(el, name, val) {
      if (el.getAttribute(name) !== val) el.setAttribute(name, val);
    }
    function title(el, txt) {
      if (el._skTitle === txt) return;
      el._skTitle = txt;
      if (el.hasAttribute('data-tip')) el.setAttribute('data-tip', txt);
      else el.title = txt;
    }
    /* Title and aria-label travel together everywhere in this bar. */
    function label(el, txt) { title(el, txt); attr(el, 'aria-label', txt); }

    function sync() {
      var pl = player();
      var st = pl ? pl.state() : null;
      var playing = !!st && st.state === 'playing';
      setHTML(bPlay, playing ? ICON.pause : ICON.play);
      label(bPlay, playing ? 'Pause' : 'Play');

      var loop = !!(pl && pl.looping());
      bLoop.classList.toggle('on', loop);
      attr(bLoop, 'aria-pressed', String(loop));
      title(bLoop, loop ? 'Repeating' : 'Plays once');

      var SI = global.SkriblInline;
      var on = !!(SI && SI.soundOn());
      var has = !!(st && st.hasAudio);
      setHTML(bMute, on ? ICON.sound : ICON.muted);
      if (bMute.disabled !== !has) bMute.disabled = !has;
      label(bMute, !has ? 'This Skribl has no sound' : (on ? 'Sound is on' : 'Sound is off'));
      attr(bMute, 'aria-pressed', String(!on));

      var r = pl ? pl.rate() : 1;
      setText(bRate, r === 0.5 ? '½×' : r + '×');
      label(bRate, 'Speed: ' + bRate.textContent + ' — tap to change');

      var total = (st && st.totalMs) || 0;
      var el = (st && st.elapsedMs) || 0;
      var w = (total ? Math.min(1, el / total) * 100 : 0) + '%';
      if (fill.style.width !== w) fill.style.width = w;
      setText(at, mmss(el));
      /* A card answers "how long is this"; full screen answers "where am I",
         and shows both. */
      setText(dur, ownRow ? mmss(total)
        : (playing || el > 0 ? mmss(el) + ' / ' + mmss(total) : mmss(total)));
      attr(track, 'aria-valuenow', String(Math.round(total ? el / total * 100 : 0)));

      if (made.full) {
        var big = !!(opts.isFull && opts.isFull());
        attr(made.full, 'aria-pressed', String(big));
        label(made.full, big ? 'Leave full screen' : 'Full screen');
      }

      if (!showWho) return;
      var m = getMeta() || {};
      setText(tTitle, m.title || 'Untitled Skribl');
      setText(tWho, m.name ? (m.handle ? m.name + ' · ' + m.handle : m.name)
                           : (m.handle || ''));
      if (tWho.hidden !== !tWho.textContent) tWho.hidden = !tWho.textContent;
      var wantHidden = !m.name && !m.handle;
      if (av.hidden !== wantHidden) av.hidden = wantHidden;
      /* THE AVATAR IS REBUILT ONLY WHEN THE PERSON CHANGES. It used to be
         emptied and re-made on every call -- and on a bar that syncs per
         frame that is a NEW <img> element, with a new src and a new error
         listener, sixty times a second for a picture that never changed.
         The key is what the avatar is FOR: this person's face. While that
         string holds, the node already on screen is correct. */
      var key = (m.avatar || '') + '|' + (m.name || '') + '|' + (m.handle || '');
      if (av._skKey !== key) {
        av._skKey = key;
        av.textContent = '';
        if (m.avatar) {
          var img = doc.createElement('img');
          img.src = m.avatar;
          img.alt = '';
          img.addEventListener('error', function () {
            img.remove();
            av.textContent = (m.name || m.handle || '?').replace('@', '').charAt(0).toUpperCase();
          });
          av.appendChild(img);
        } else if (!wantHidden) {
          av.textContent = (m.name || m.handle || '?').replace('@', '').charAt(0).toUpperCase();
        }
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
