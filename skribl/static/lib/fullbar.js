/* The full-screen bar: one transport, and the SAME one on both surfaces.
 *
 * Neither page builds its own; both call this. The failure mode of two copies
 * is not that one is wrong today, it is that one is fixed tomorrow.
 *
 * IT MUST LIVE INSIDE THE FULLSCREENED ELEMENT. Under the real Fullscreen API
 * only that subtree renders, so a bar sitting in the page would simply be gone.
 *
 * IT PLAYS NOTHING. Every control drives the in-post player's own handle
 * (play/pause/seek/setLoop/setRate and the shared sound switch): the buttons
 * are the page's, the clock is the player's. A second replay implementation is
 * the defect verify_sharedrules.py exists about.
 *
 * THE COMPONENT'S OWN CHROME YIELDS. The page adds `is-bare` to the player,
 * hiding its cluster and duration chip, or there are two transports on screen.
 * It does NOT hide the idle veil: that is the play cue, not a control, and a
 * card without it is a black rectangle with no sign it moves.
 *
 * TWO CONFIGURATIONS. `attach` takes what varies:
 *
 *   card footer  play loop mute | scrubber inline | time | full, always shown.
 *   full screen  the link page's band (band() below): its scrubber, clock,
 *                words and buttons, the x, and who drew it in the corner,
 *                shown only while the wrapper is up.
 *
 * What a control DOES, how it reads the player and the rule that lit means
 * "currently true" are the same in both, which is the half that rots when it
 * is copied.
 */
(function (global) {
  'use strict';

  var doc = global.document;

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
    restart: svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>'),
    play: svg('<path d="M8 5v14l11-7z"/>', 'currentColor'),
    pause: svg('<rect x="6" y="5" width="4" height="14" rx="1"/>'
               + '<rect x="14" y="5" width="4" height="14" rx="1"/>', 'currentColor'),
    loop: svg('<path d="M17 2l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
              + '<path d="M7 22l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
    sound: svg('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>'
               + '<path d="M19 5a9 9 0 0 1 0 14"/>'),
    muted: svg('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="m16 9 5 6"/><path d="m21 9-5 6"/>'),
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

  /* WRITE ONLY WHAT CHANGED. Not a micro-optimisation: it is why the speed
   * button did not answer a press.
   *
   * `sync()` runs on a FRAME while the drawing plays. `innerHTML =` and
   * `textContent =` REPLACE a node's children even when the value is
   * identical, so assigning unconditionally rebuilt every button ~67 times a
   * second. A PRESS WHOSE ELEMENT IS REMOVED AND RE-INSERTED BETWEEN THE
   * MOUSEDOWN AND THE MOUSEUP PRODUCES NO CLICK -- the node keeps its
   * listeners, so pointerdown and pointerup still arrive and only the click
   * goes missing.
   *
   * Titles cost twice: `lib/tooltip.js` watches the `title` attribute, so
   * unconditional writes woke its observer every frame to move the same
   * string to `data-tip` and strip it, which sync then restored. */
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

  /* What the listing said about the drawing's sound: true, false, or null
     where it said nothing. Read once per box. */
  function listed(pl) {
    var box = pl && pl.el;
    if (!box) return null;
    if (box._skSound === undefined) {
      var info = null;
      try { info = JSON.parse(box.getAttribute('data-skribl-line') || 'null'); } catch (e) { info = null; }
      box._skSound = info && typeof info.sound === 'boolean' ? info.sound : null;
    }
    return box._skSound;
  }

  /* attach(wrap, opts) -> { sync, el, running }
   *
   *   wrap         the element the page fullscreens; the bar is appended to it
   *   opts.player  function returning the in-post player handle, or null. A
   *                FUNCTION and not the handle itself: the gallery's tile has
   *                no player until somebody presses play, and the profile's
   *                stage swaps its one out every time a different row is
   *                selected.
   *   opts.variant 'skfull-card' for the card's row (with opts.controls,
   *                opts.onFull and opts.isFull); anything else is full screen
   *   opts.meta    full screen: function returning { title, name, handle }
   *   opts.onExit  full screen: called when the viewer asks to leave
   */
  function attach(wrap, opts) {
    opts = opts || {};
    if (opts.variant !== 'skfull-card') return band(wrap, opts);
    var getPlayer = opts.player || function () { return null; };
    var want = opts.controls || ['play', 'loop', 'mute', 'full'];

    var bar = doc.createElement('div');
    bar.className = 'skfull' + (opts.variant ? ' ' + opts.variant : '');

    var track = doc.createElement('div');
    track.className = 'skfull-track';
    track.setAttribute('aria-label', 'Scrub');   // its role, focus and keys: SkriblScrub, below
    var fill = doc.createElement('div');
    fill.className = 'skfull-fill';
    track.appendChild(fill);
    var dur = doc.createElement('span');
    dur.className = 'skfull-time skfull-dur';
    dur.textContent = '0:00';

    var row = doc.createElement('div');
    row.className = 'skfull-row';

    var made = {};
    made.play = btn('skfull-play', 'Play', ICON.play);
    made.loop = btn('skfull-loop', 'Loop', ICON.loop);
    made.mute = btn('skfull-mute', 'Mute', ICON.sound);
    made.full = btn('skfull-full', 'Full screen', ICON.full);
    var bPlay = made.play, bLoop = made.loop;
    var bMute = made.mute;

    for (var i = 0; i < want.length; i++) {
      if (made[want[i]]) row.appendChild(made[want[i]]);
    }
    /* Inline: the track takes the space the meta line would have, and the one
       time shown is the DURATION, because a card is answering "how long is
       this" rather than "where am I". */
    row.appendChild(track);
    row.appendChild(dur);

    bar.appendChild(row);
    wrap.appendChild(bar);

    function player() { return getPlayer(); }

    /* THE CARD'S FADE TAKES ITS COLOURS FROM THE DRAWING (the owner's pick A
       after v326: "The fade has to be like the glass with smart fade,
       sampling the background for the fade colors and making it subtle. It's
       so obvious and ugly when it's wrong"). The fixed near-black scrim turned
       a pale drawing's empty paper grey by 6.7:1 under the controls, spread a
       dark band onto the card's edges, and left the time at 2.6:1 there.

       - THE FADE LIES ON THE DRAWING ONLY, inside its edge and round corners
         (area() below), in the drawing's own colours: its foot read in
         strips across (ground()), so on empty paper it cannot be seen and it
         only softens ink that runs under the controls. Painted as a
         rectangle, the paper filled the card's colour in the drawing's
         corners and they read square and grey; beside the drawing the card's
         own colour needs no fade at all.
       - EACH GLASS CONTROL TAKES THE TONE OF WHAT IS UNDER IT, light glass on
         a pale ground and dark on a dark one, as the play pill's does: the
         drawing where it is over the drawing, the card's own colour where it
         is not (a tall drawing on a desk card is narrower than the row).
       - WHERE THE DRAWING CAN HOLD THE ROW (a phone's tall card), the row sits
         4px inside it, not 3px out over the card's edge, where the time's
         last figure took the drawing's ink over the edge's colour.

       READ ON EVENTS, NEVER ON THE BEAT: when the card or the canvas becomes
       what is showing, when the stage resizes, when the page's theme turns.
       A drawing that cannot be read keeps the scrim: `is-smart` is never set
       on a guess. The reading and the tones are lib/smartfade.js's, which
       every bar over a drawing shares; the card's own geometry (its plate,
       its round corners, its row) is here. */
    var S = global.SkriblSmartFade;
    var smart = smartFade();
    function smartFade() {
      var box = null, cv = null, img = null, cols = null, from = '', asked = false, ro = null, mo = null, unwatch = null,
          on = false, was;
      function off() { bar.classList.remove('is-smart'); }
      /* THE DRAWING'S FOOT: its bottom eighth in 16 strips across, each strip
         the middle value of its own pixels, so a line of ink through it does
         not tint it. Off the canvas while it shows, which IS the drawing;
         before, off the card image, through the player's reader of it
         (inlineplayer.js readCard), the play pill's glass's too. Null until
         there is something to read. */
      function ground(pl) {
        if (!S) return null;
        return cv && !cv.hidden ? S.foot(cv) : S.medians(pl.read(0.01, 0.875, 0.98, 0.115, 96, 12));
      }
      /* WHERE THE DRAWING IS on screen, and the round of its two bottom
         corners: the canvas while it shows; before, the card image's crop of
         it, where fitPoster left the drawing's rectangle on the image
         (`_d`, in the card's pixels) and the plate's own round, scaled; each
         inside the box's rounded edge. */
      function area(pl) {
        var b = box.getBoundingClientRect(), cs = getComputedStyle(box), bw = parseFloat(cs.borderBottomWidth) || 0,
            R = Math.max(0, (parseFloat(cs.borderBottomLeftRadius) || 0) - bw), r, f, rad = 0;
        if (cv && !cv.hidden) r = f = cv.getBoundingClientRect();
        else if (img && img._d && img.naturalWidth && pl.card) {
          var p = img.getBoundingClientRect(), s = p.width / pl.card[0], d = img._d, i = pl.card[2];
          r = { left: p.left + (d[0] + i) * s, right: p.left + (d[0] + d[2] - i) * s,
                top: p.top + (d[1] + i) * s, bottom: p.top + (d[1] + d[3] - i) * s };
          /* The drawing's FRAME, the plate's inset aside: where the canvas
             will be (fitPoster lands it there), so the row placed from it
             does not move at the first tap. */
          f = { left: p.left + d[0] * s, right: p.left + (d[0] + d[2]) * s };
          rad = (pl.card[1] - i) * s;
        } else return null;
        var x0 = Math.max(r.left, b.left + bw), x1 = Math.min(r.right, b.right - bw), y1 = Math.min(r.bottom, b.bottom - bw);
        function round(x, edge) { return Math.abs(x - edge) < 1.5 && Math.abs(y1 - b.bottom + bw) < 1.5 ? Math.max(R, rad) : rad; }
        return { left: x0, right: x1, top: Math.max(r.top, b.top + bw), bottom: y1,
                 rl: round(x0, b.left + bw), rr: round(x1, b.right - bw),
                 fl: Math.max(f.left, b.left + bw), fr: Math.min(f.right, b.right - bw) };
      }
      function update() {
        var pl = player();
        if (!S || !pl || !pl.read || !wrap.isConnected) return off();
        if (pl.el !== box) {
          box = pl.el; cv = box.querySelector('.skribl-inline-canvas'); img = box.querySelector('.skribl-inline-poster');
          cols = null; asked = false;
          if (mo) mo.disconnect();
          if (cv && global.MutationObserver) {
            mo = new MutationObserver(update);
            mo.observe(cv, { attributes: true, attributeFilter: ['hidden'] });
          }
          if (ro) ro.observe(box);
        }
        /* The canvas once it is the one showing, the card before: what the
           eye sees under the bar, which for a post without its card are not
           the same drawing. */
        var src = cv && !cv.hidden ? 'canvas' : 'card';
        if (src !== from) { from = src; cols = null; asked = false; }
        if (!cols && !asked) {
          asked = true;
          cols = ground(pl);
          /* A card image still on its way: read when it lands. One that
             cannot be read stays unasked until what shows changes. */
          if (cols) asked = false;
          else if (src === 'card' && img && !img.naturalWidth) {
            img.addEventListener('load', function () { asked = false; update(); }, { once: true });
          }
        }
        if (!cols) return off();
        var a = area(pl), b = bar.getBoundingClientRect();
        if (!a || !b.width || a.right - a.left < 8) return off();
        /* What the card shows beside the drawing: the first ground painted
           under it, up from the box. */
        var n = cols.length, w = a.right - a.left, m = S.ground(box), s = bar.style;
        s.setProperty('--fx-l', (a.left - b.left).toFixed(1) + 'px');
        s.setProperty('--fx-r', (b.right - a.right).toFixed(1) + 'px');
        s.setProperty('--fx-b', Math.max(0, b.bottom - a.bottom).toFixed(1) + 'px');
        s.setProperty('--fx-rl', a.rl.toFixed(1) + 'px');
        s.setProperty('--fx-rr', a.rr.toFixed(1) + 'px');
        s.setProperty('--fade-x', S.gradient(cols));
        var need = 0, shown = 0, kids = row.children, gap = parseFloat(getComputedStyle(row).columnGap) || 0;
        for (var i = 0; i < kids.length; i++) {
          if (!kids[i].getClientRects().length) continue;
          need += kids[i] === track ? 48 : kids[i].getBoundingClientRect().width;
          shown++;
        }
        var fits = a.fr - a.fl - 8 >= need + gap * Math.max(0, shown - 1);
        s.setProperty('--row-l', fits ? (a.fl - b.left + 4).toFixed(1) + 'px' : '0px');
        s.setProperty('--row-r', fits ? (b.right - a.fr + 4).toFixed(1) + 'px' : '0px');
        bar.classList.add('is-smart');
        /* After the row has moved: what is under each control now. */
        function under(x, y) {
          if (x < a.left || x > a.right || y < a.top || y > a.bottom) return m;
          return cols[Math.max(0, Math.min(n - 1, Math.floor((x - a.left) / w * n)))];
        }
        var glass = [made.loop, made.mute, made.full, track, dur];
        for (var j = 0; j < glass.length; j++) {
          if (glass[j] && glass[j].isConnected) S.tone(glass[j], under, false);
        }
      }
      return {
        /* From the beat until the player is there; the gallery mounts the
           players after it has built the cards. */
        start: function (state) {
          /* A play, a pause or an end is when a canvas first has its ground
             painted (a photo under the drawing arrives late): read again. */
          if (on && state !== was) { was = state; cols = null; asked = false; update(); }
          if (on || !player()) return;
          on = true;
          was = state;
          if (global.ResizeObserver) { ro = new ResizeObserver(update); ro.observe(wrap); }
          if (S) unwatch = S.watchTheme(wrap, update);
          update();
        },
        /* The row changed under the fade (Mute stepped aside): the row's
           place and each control's tone are read again. */
        relayout: function () { if (on) update(); },
        /* The host has left (a search or a sort rebuilds the grid): its
           watches go, and so does its place in the theme's list. */
        stop: function () {
          if (ro) ro.disconnect();
          if (mo) mo.disconnect();
          if (unwatch) unwatch();
          ro = mo = unwatch = null;
        }
      };
    }

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
    // A SLIDER THAT MOVES (after v326, the viewing pages' review): the track
    // said role=slider and Tab passed it by, and no key moved it. The keyboard
    // half every other scrubber here has (lib/scrubkeys.js, loaded wherever
    // this bar is), named Scrub as they are.
    if (global.SkriblScrub) global.SkriblScrub.attach(track, {
      seek: function (f) { var pl = player(), st = pl && pl.state(); if (st && st.totalMs) { pl.seek(st.totalMs * f); sync(); } },
      frac: function () { var pl = player(), st = pl && pl.state(); return st && st.totalMs ? Math.min(1, st.elapsedMs / st.totalMs) : 0; }
    });
    if (made.full) made.full.addEventListener('click', function (e) {
      e.stopPropagation();
      if (opts.onFull) opts.onFull();
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

    /* Every control reads the PLAYER's state rather than remembering its own.
       A control that keeps a copy is a control that lies the moment anything
       else moves the thing it is about — a replay ending, a row being swapped
       under the stage, another post claiming the page's sound. */

    function sync() {
      var pl = player();
      var st = pl ? pl.state() : null;
      if (smart && pl) smart.start(st && st.state);
      /* A play, a pause or the end changes what lies under the bar. */
      var playing = !!st && st.state === 'playing';
      /* PUBLISHED TO THE HOST, because a surface may want to style itself on
         it -- the card narrows its hover reveal to a drawing that is NOT
         playing, so a playing one is the transport's own to show and hide.
         Guarded rather than written every beat: this runs on a rAF while a
         drawing plays, and an unconditional write is the churn the speed
         button was lost to. classList.toggle would not mutate the token list
         here, but reading the flag first also keeps this off the hot path. */
      if (wrap._skPlaying !== playing) {
        wrap._skPlaying = playing;
        wrap.classList.toggle('is-playing', playing);
      }
      setHTML(bPlay, playing ? ICON.pause : ICON.play);
      label(bPlay, playing ? 'Pause' : 'Play');

      var loop = !!(pl && pl.looping());
      bLoop.classList.toggle('on', loop);
      attr(bLoop, 'aria-pressed', String(loop));
      // NAMED AS EVERY OTHER LOOP AND MUTE ARE (after v326, the viewing pages'
      // review): the card said "Repeat" and "Sound is on" where its own full
      // screen, the link page and the Library say Loop and Mute / Unmute, and
      // "Sound is off, pressed" read oddly. The state words stay in the tip.
      title(bLoop, loop ? 'Repeating' : 'Plays once');

      var SI = global.SkriblInline;
      var on = !!(SI && SI.soundOn());
      // Before it has loaded, the listing says whether it has sound (as for
      // `silent` below): a card with sound read "This Skribl has no sound",
      // pressed and greyed, until its first play.
      var has = st && st.loaded ? !!st.hasAudio : listed(pl) === true;
      /* MUTE STEPS ASIDE ON A SILENT DRAWING (the owner: yes, after the
         card's fade). Greyed out on every silent card it was a control with
         nothing to act on. Known from the listing before the drawing loads
         (`sound` on the box's data-skribl-line), so the row does not change
         at the first tap; from the drawing itself once it has. Where neither
         has said, it stays, greyed, as before. */
      var silent = st && st.loaded ? !has : listed(pl) === false;
      if (bMute.hidden !== silent) {
        bMute.hidden = silent;
        if (smart) smart.relayout();
      }
      setHTML(bMute, on ? ICON.sound : ICON.muted);
      if (bMute.disabled !== !has) bMute.disabled = !has;
      title(bMute, !has ? 'This Skribl has no sound' : (on ? 'Sound is on' : 'Sound is off'));
      attr(bMute, 'aria-label', !has ? 'This Skribl has no sound' : (on ? 'Mute' : 'Unmute'));
      attr(bMute, 'aria-pressed', String(!on));

      var total = (st && st.totalMs) || 0;
      var el = (st && st.elapsedMs) || 0;
      var w = (total ? Math.min(1, el / total) * 100 : 0) + '%';
      if (fill.style.width !== w) fill.style.width = w;
      /* A card answers "how long is this", and where it is once it plays. */
      setText(dur, playing || el > 0 ? mmss(el) + ' / ' + mmss(total) : mmss(total));
      if (global.SkriblScrub) global.SkriblScrub.sync(track, total ? el / total : 0);
      else attr(track, 'aria-valuenow', String(Math.round(total ? el / total * 100 : 0)));

      if (made.full) {
        var big = !!(opts.isFull && opts.isFull());
        attr(made.full, 'aria-pressed', String(big));
        label(made.full, big ? 'Leave full screen' : 'Full screen');
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
    var raf = null, tick = null, hosted = false;
    function beat() {
      /* A BAR WHOSE HOST HAS LEFT THE DOCUMENT STOPS ITSELF, and without this
         nothing ever stops it. The beat reschedules from inside itself, so a
         card discarded by the grid -- every search, every sort change, the
         gallery empties `list` and builds new tiles -- keeps a quarter-second
         timer alive for the life of the PAGE, reading state off a detached
         tree that can then never be collected. Nobody calls running(false) on
         the way out, and asking every caller to remember is the kind of
         bookkeeping that is correct once and wrong after the next surface is
         added.

         Measured on the gallery, 24 tiles on screen throughout: 6 timer calls
         per visible card per 1.5s before a reset, 30 after four of them --
         five grids' worth of beats, four of them invisible.

         `isConnected`, not a flag: it is the browser's own answer and cannot
         drift from the truth. Full screen does NOT detach -- lib/immersive.js
         goes through the Fullscreen API and a class, never a reparent -- so
         this only ever fires on a host that has really gone, and the callers
         that toggle running() for a scene still own that.

         AND IT HAS TO HAVE BEEN CONNECTED FIRST. attach() runs while the tile
         is still being assembled -- the gallery builds the whole card and puts
         it in the grid afterwards -- so a bare `!isConnected` is TRUE on the
         very first beat and stops every bar before it has run once. Measured
         that way: 0 timers for 24 visible cards, the scrubber and the play
         icon frozen on all of them. Latch on the first connected beat instead,
         so a host that has not arrived yet keeps its idle beat and only a host
         that has LEFT stops. */
      if (wrap) {
        if (wrap.isConnected) hosted = true;
        else if (hosted) { running(false); if (smart) smart.stop(); return; }
      }
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

    sync();
    return { el: bar, sync: sync, running: running };
  }

  /* ONE FULL SCREEN, EVERYWHERE (the owner: "why can't the gallery player
     look like the others? with the same scrubber and all?", then "All yes"
     to the mock). The Gallery's and the Library's full screen is the link
     page's: its band, its x and the drawing's own ground out to the screen's
     edges.

     THE MARKUP is the link page's (_skribl_player_controls.html), built here.
     THE RULES are styles.css's own: they reach these two pages as
     fullband.css, which harness/tools/cssgraph.py emits from styles.css the
     way it emits player.css, so they are written once and verify_seam
     holds the copy to its source. THE SCRUBBER that shows the drawing's
     shape and THE WORDS with every speed are the in-post player's own line
     (inlineplayer.js band()), on its own clock.

     What these pages have that the link page does not is who drew it: that
     sits in the top corner across from the x, in the buttons' glass, and
     steps back with them.

     band(wrap, opts) -> { el, sync, running }, as attach()'s. */
  var CLOSE = svg('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>');
  function pbtn(cls, name, html) {
    var b = doc.createElement('button');
    b.type = 'button';
    b.className = 'player-btn' + (cls ? ' ' + cls : '');
    b.setAttribute('aria-label', name);
    b.innerHTML = html;
    return b;
  }
  function band(wrap, opts) {
    var getPlayer = opts.player || function () { return null; };
    var getMeta = opts.meta || function () { return null; };
    function player() { return getPlayer(); }
    var S = global.SkriblSmartFade, RL = global.SkriblReplayLine;
    /* `.watch-full` is the frame every full screen's rules name
       (styles.css, `:is(.canvas-wrap, .watch-full)`): the link page's is
       .canvas-wrap, the editors' and these pages' .watch-full. */
    wrap.classList.add('watch-full', 'skfull-host');

    var bar = doc.createElement('div');
    bar.className = 'player-bar';
    bar.hidden = true;
    var time = doc.createElement('div');
    time.className = 'player-time';
    time.setAttribute('aria-hidden', 'true');
    var at = doc.createElement('span'), dur = doc.createElement('span');
    at.textContent = dur.textContent = '0:00';
    time.appendChild(at);
    time.appendChild(dur);
    var row = doc.createElement('div');
    row.className = 'player-controls';
    var bRestart = pbtn('', 'Restart', ICON.restart), bPlay = pbtn('primary', 'Play', ICON.play),
        bLoop = pbtn('active', 'Loop', ICON.loop), bMute = pbtn('', 'Mute', ICON.sound),
        bFull = pbtn('', 'Leave full screen', ICON.full);
    bLoop.setAttribute('aria-pressed', 'true');
    bMute.setAttribute('aria-pressed', 'false');
    bMute.hidden = true;
    bFull.setAttribute('aria-pressed', 'true');
    [bRestart, bPlay, bLoop, bMute, bFull].forEach(function (b) { row.appendChild(b); });
    bar.appendChild(time);
    bar.appendChild(row);
    var x = pbtn('full-exit', 'Leave full screen', CLOSE);
    var who = doc.createElement('div');
    who.className = 'fb-who';
    who.hidden = true;
    var wTitle = doc.createElement('b'), wBy = doc.createElement('span');
    who.appendChild(wTitle);
    who.appendChild(wBy);
    wrap.appendChild(bar);
    wrap.appendChild(x);
    wrap.appendChild(who);

    /* THE SCRUBBER AND THE WORDS ARE THE PLAYER'S, so a new player (the
       Library puts one on its stage for each row) gets new ones: fresh
       nodes, so the last player's hold on the old ones goes with them. */
    var prog = null, words = null, wired = null;
    function wire(pl) {
      if (!pl || pl === wired) return;
      wired = pl;
      if (prog) prog.remove();
      if (words) words.remove();
      prog = doc.createElement('div');
      prog.className = 'player-progress';
      prog.setAttribute('aria-label', 'Scrub');
      prog.innerHTML = '<div class="player-progress-fill"></div>';
      words = doc.createElement('div');
      bar.insertBefore(prog, time);
      bar.insertBefore(words, row);
      if (!(pl.band && pl.band(prog, words))) prog.hidden = words.hidden = true;
    }

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
      if (pl) { pl.setLoop(!pl.looping()); sync(); }
    });
    bMute.addEventListener('click', function () {
      var SI = global.SkriblInline;
      if (SI) { SI.setSoundOn(!SI.soundOn()); sync(); }
    });
    [bFull, x].forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        if (opts.onExit) opts.onExit();
      });
    });

    /* THE BAND STEPS BACK WHILE IT PLAYS, the x and the name with it
       (lib/chromefade.js; the owner's picks for every full screen). */
    var fade = global.SkriblChromeFade ? global.SkriblChromeFade.attach(wrap, { tapWakes: true, awake: function () {
      var st = player() && player().state();
      // ...and never while a menu of its own is open (the speeds), as the
      // link page's band keeps itself up (after v326, the viewing pages'
      // review: the open speeds faded away with the rest).
      return !st || (st.state !== 'playing' && !(st.totalMs && st.elapsedMs >= st.totalMs))
        || !!bar.querySelector('[aria-expanded="true"]');
    } }) : null, fadePlaying = null;
    /* ITS COLOURS FROM THE DRAWING (lib/smartfade.js), toned as the link
       page's are: the same controls, the same words. */
    var smart = S ? S.full(bar, {
      canvas: function () {
        var pl = player(), c = pl && pl.el && pl.el.querySelector('.skribl-inline-canvas');
        return c && !c.hidden ? c : null;
      },
      contain: true,
      glass: '.player-btn:not(.primary), .rl-speed',
      words: '.player-time > span, .rl-drawn, .rl-m, .rl-skip'
    }) : null, smartWas = null;

    /* THE DRAWING'S GROUND TO THE SCREEN'S EDGES, as the link page paints
       its frame: one picture, not a drawing in a box. The name in the corner
       wears the glass for that ground. */
    var groundWas;
    function ground(g) {
      if (g === groundWas) return;
      groundWas = g;
      wrap.style.backgroundColor = g || '';
      var v = g && S ? S.ground(wrap) : null;
      var light = !!v && 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2] >= 115;
      who.classList.toggle('t-light', light);
      who.classList.toggle('t-dark', !light);
    }

    var on = false;
    function sync() {
      var pl = player();
      wire(pl);
      var st = pl ? pl.state() : null;
      var playing = !!st && st.state === 'playing';
      if (wrap._skPlaying !== playing) {
        wrap._skPlaying = playing;
        wrap.classList.toggle('is-playing', playing);
      }
      setHTML(bPlay, playing ? ICON.pause : ICON.play);
      attr(bPlay, 'aria-label', playing ? 'Pause' : 'Play');
      if (fade && fadePlaying !== playing) { fadePlaying = playing; fade.poke(); }
      /* A play, a pause or the end changes what lies under the band. */
      if (smart && on && st && st.state !== smartWas) { smartWas = st.state; smart.read(); }

      var loop = !!(pl && pl.looping());
      bLoop.classList.toggle('active', loop);
      attr(bLoop, 'aria-pressed', String(loop));

      /* Mute steps aside on a silent drawing, as on the card and the link
         page; the listing says so before the drawing loads. */
      var SI = global.SkriblInline, muted = !(SI && SI.soundOn()), has = !!(st && st.hasAudio);
      var silent = st && st.loaded ? !has : listed(pl) !== true;
      if (bMute.hidden !== silent) bMute.hidden = silent;
      setHTML(bMute, muted ? ICON.muted : ICON.sound);
      attr(bMute, 'aria-label', muted ? 'Unmute' : 'Mute');
      attr(bMute, 'aria-pressed', String(muted));

      var c = pl && pl.clock ? pl.clock() : null;
      if (c && RL) {
        setText(at, RL.clock(c.at));
        setText(dur, RL.clock(c.dur));
      }
      if (on) ground(pl && pl.ground ? pl.ground() : null);

      var m = getMeta() || {};
      setText(wTitle, m.title || 'Untitled Skribl');
      setText(wBy, m.name ? (m.handle ? m.name + ' · ' + m.handle : m.name) : (m.handle || ''));
      if (wBy.hidden !== !wBy.textContent) wBy.hidden = !wBy.textContent;
    }

    /* A frame while it plays, so the clock under the scrubber moves with
       the drawing; a quarter second while it does not. Only while it is on
       screen, and never once the host has left. */
    var raf = null, tick = null;
    function beat() {
      if (!wrap.isConnected) { running(false); return; }
      sync();
      var st = player() && player().state();
      if (st && st.state === 'playing') {
        tick = null;
        raf = global.requestAnimationFrame(beat);
      } else {
        raf = null;
        tick = global.setTimeout(beat, 250);
      }
    }
    function running(want) {
      on = !!want;
      bar.hidden = who.hidden = !on;
      if (fade) fade[on ? 'start' : 'stop']();
      if (smart) { smartWas = null; smart[on ? 'start' : 'stop'](); }
      if (on) { if (!raf && !tick) beat(); return; }
      ground(null);
      if (raf) global.cancelAnimationFrame(raf);
      if (tick) global.clearTimeout(tick);
      raf = tick = null;
    }

    sync();
    return { el: bar, sync: sync, running: running };
  }

  global.SkriblFullBar = { attach: attach };
})(window);
