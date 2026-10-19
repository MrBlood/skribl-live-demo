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
 * TWO CONFIGURATIONS, ONE BUILDER. `attach` takes what varies:
 *
 *   full screen  restart play loop mute rate | who | exit, scrubber on its
 *                own row, shown only while the wrapper is up.
 *   card footer  play loop mute | scrubber inline | time | full, always shown.
 *
 * Everything else — what a control DOES, how it reads the player, the rule
 * that lit means "currently true" — is shared, which is the half that rots
 * when it is copied.
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
       press, so an untouched bar steps from whatever the player reports. See
       the rate handler for why reading the player alone cannot advance. */
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

    /* THE BAR STEPS BACK WHILE IT PLAYS (lib/chromefade.js; the owner's picks
       for every full screen): after a quiet spell it fades with the page's x,
       and a move, a key or a tap brings it back -- a finger's first tap on a
       faded screen only that. Up while the drawing is paused part-way or not
       started; finished, it comes up as the drawing ends and steps back again,
       so the finished drawing is seen whole. running() is the page's word that
       full screen opened or closed; never on a card. */
    var fade = opts.variant !== 'skfull-card' && global.SkriblChromeFade
      ? global.SkriblChromeFade.attach(wrap, { tapWakes: true, awake: function () {
          var st = player() && player().state();
          return !st || (st.state !== 'playing' && !(st.totalMs && st.elapsedMs >= st.totalMs));
        } }) : null;
    var fadePlaying = null;

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
       on a guess. */
    var smart = opts.variant === 'skfull-card' ? smartFade() : null;
    function smartFade() {
      var box = null, cv = null, img = null, cols = null, from = '', asked = false, ro = null, mo = null, on = false, was;
      function off() { bar.classList.remove('is-smart'); }
      /* THE DRAWING'S FOOT: its bottom eighth in 16 strips across, each strip
         the middle value of its own pixels, so a line of ink through it does
         not tint it. Off the canvas while it shows, which IS the drawing;
         before, off the card image, through the player's reader of it
         (inlineplayer.js readCard), the play pill's glass's too. Null until
         there is something to read. */
      function ground(pl) {
        var n = 16, w = 6, h = 12, px = null, out = [];
        if (cv && !cv.hidden) {
          try {
            var c = doc.createElement('canvas'), g = c.getContext('2d');
            c.width = n * w; c.height = h;
            g.fillStyle = '#fff'; g.fillRect(0, 0, n * w, h);
            g.drawImage(cv, cv.width * 0.01, cv.height * 0.875, cv.width * 0.98, cv.height * 0.115, 0, 0, n * w, h);
            px = g.getImageData(0, 0, n * w, h).data;
          } catch (e) { px = null; }
        } else px = pl.read(0.01, 0.875, 0.98, 0.115, n * w, h);
        if (!px) return null;
        for (var s = 0; s < n; s++) {
          var ch = [[], [], []];
          for (var y = 0; y < h; y++) {
            for (var x = s * w; x < s * w + w; x++) {
              for (var i = 0, o = (y * n * w + x) * 4; i < 3; i++) ch[i].push(px[o + i]);
            }
          }
          out.push(ch.map(function (v) { v.sort(function (a, b) { return a - b; }); return v[v.length >> 1]; }));
        }
        return out;
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
      function rgb(v) { return 'rgb(' + v[0] + ' ' + v[1] + ' ' + v[2] + ')'; }
      function luma(v) { return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; }
      /* What the card shows beside the drawing: the first ground painted
         under it, up from the box. */
      function mat() {
        for (var e = box; e && e.nodeType === 1; e = e.parentElement) {
          var m = getComputedStyle(e).backgroundColor.match(/[\d.]+/g);
          if (m && (m.length < 4 || +m[3] > 0.5)) return [+m[0], +m[1], +m[2]];
        }
        return [255, 255, 255];
      }
      function update() {
        var pl = player();
        if (!pl || !pl.read || !wrap.isConnected) return off();
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
        var n = cols.length, w = a.right - a.left, m = mat(), s = bar.style;
        s.setProperty('--fx-l', (a.left - b.left).toFixed(1) + 'px');
        s.setProperty('--fx-r', (b.right - a.right).toFixed(1) + 'px');
        s.setProperty('--fx-b', Math.max(0, b.bottom - a.bottom).toFixed(1) + 'px');
        s.setProperty('--fx-rl', a.rl.toFixed(1) + 'px');
        s.setProperty('--fx-rr', a.rr.toFixed(1) + 'px');
        s.setProperty('--fade-x', 'linear-gradient(to right, ' + cols.map(function (v, k) {
          return rgb(v) + ' ' + ((k + 0.5) / n * 100).toFixed(1) + '%';
        }).join(', ') + ')');
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
          var el = glass[j];
          if (!el || !el.isConnected) continue;
          var q = el.getBoundingClientRect(), y = (q.top + q.bottom) / 2, L = 0, c = 0;
          for (var x = q.left; x <= q.right; x += 2) { L += luma(under(x, y)); c++; }
          var dark = !c || L / c < 115;
          el.classList.toggle('t-dark', dark);
          el.classList.toggle('t-light', !dark);
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
          watchTheme();
          smartCards.push({ wrap: wrap, update: update });
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
          ro = mo = null;
          smartCards = smartCards.filter(function (c) { return c.wrap !== wrap; });
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
      /* THE REPAINT IS IN A `finally`. setRate rebuilds the audio graph on an
       * AudioContext the browser may take away; a throw from in there must not
       * skip the repaint and leave the label reading a speed the player is no
       * longer running. setRate does not let that throw escape either -- either
       * half alone leaves the other's failure silent. */
      /* THE STEP COMES FROM WHAT THIS CONTROL LAST ASKED FOR WHENEVER THE
       * PLAYER DISAGREES WITH IT.
       *
       * Stepping from `pl.rate()` is right only while the handle answering is
       * the one the last press wrote to. When it is not -- a player rebuilt
       * under the bar, a handle swapped for another card's -- the read comes
       * back at the default and the cycle recomputes the SAME next value every
       * press, so the speed sticks. An UNKNOWN rate is worse: indexOf gives
       * -1, (-1 + 1) % 3 is 0, so every press asks for 1x and a control
       * already at 1x looks dead.
       *
       * `wanted` is NOT a cached copy for display -- the label below still
       * reads the player, so it cannot lie about the speed being run. It is
       * this control's memory of its own last request, which is the one thing
       * the player cannot tell it. */
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

    function sync() {
      var pl = player();
      var st = pl ? pl.state() : null;
      if (smart && pl) smart.start(st && st.state);
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
      if (fade && fadePlaying !== playing) { fadePlaying = playing; fade.poke(); }

      var loop = !!(pl && pl.looping());
      bLoop.classList.toggle('on', loop);
      attr(bLoop, 'aria-pressed', String(loop));
      title(bLoop, loop ? 'Repeating' : 'Plays once');

      var SI = global.SkriblInline;
      var on = !!(SI && SI.soundOn());
      var has = !!(st && st.hasAudio);
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
      label(bMute, !has ? 'This Skribl has no sound' : (on ? 'Sound is on' : 'Sound is off'));
      attr(bMute, 'aria-pressed', String(!on));

      var r = pl ? pl.rate() : 1;
      /* An author's start can be any of ¼× to 16×, or a Fit's own number
         (3.4×), so the label rounds rather than printing 3.4333×. */
      setText(bRate, r === 0.5 ? '½×' : r === 0.25 ? '¼×' : Math.round(r * 10) / 10 + '×');
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
      /* THE AVATAR IS REBUILT ONLY WHEN THE PERSON CHANGES. On a bar that
         syncs per frame, rebuilding means a NEW <img> with a new src and a new
         error listener sixty times a second for a picture that never changed.
         The key is what the avatar is FOR: while that string holds, the node
         already on screen is correct. */
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
      if (fade) fade[on ? 'start' : 'stop']();
      if (on) { if (!raf && !tick) beat(); return; }
      if (raf) global.cancelAnimationFrame(raf);
      if (tick) global.clearTimeout(tick);
      raf = null;
      tick = null;
    }

    /* THE HOST IS MARKED for the sheet's fade (fullbar.css). The bar used to
       reserve its own measured height on it, a band under the drawing, after a
       pug whose feet were behind the controls; with the bar away while it
       plays, the drawing has the whole screen, and the bar lies over its foot
       only while someone is using it. The card's bar is not the host's: it is
       hidden in full screen. */
    if (opts.variant !== 'skfull-card') wrap.classList.add('skfull-host');

    sync();
    return { el: bar, sync: sync, running: running };
  }

  /* ONE WATCH ON THE PAGE'S THEME for every card's fade: the card's own
     colour beside a narrow drawing turns with it, and a control over it has
     to turn too. A card whose host has left is dropped on the next turn. */
  var smartCards = [], themeWatched = false;
  function themed() {
    smartCards = smartCards.filter(function (c) {
      if (!c.wrap.isConnected) return false;
      c.update();
      return true;
    });
  }
  function watchTheme() {
    if (themeWatched) return;
    themeWatched = true;
    if (global.MutationObserver) {
      new MutationObserver(themed).observe(doc.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    }
    var mq = global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)');
    if (mq && mq.addEventListener) mq.addEventListener('change', themed);
  }

  global.SkriblFullBar = { attach: attach, RATES: RATES };
})(window);
