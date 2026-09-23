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
 * (inlineplayer.css), which hides its cluster, its duration chip and its idle
 * veil. Without that there are two transports on screen, which is the thing
 * being fixed.
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

    var bar = doc.createElement('div');
    bar.className = 'skfull';

    /* THE SCRUBBER GETS ITS OWN ROW. Squeezed between the buttons it is a 6px
       target on a phone, which is not a target. */
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
    scrub.appendChild(at);
    scrub.appendChild(track);
    scrub.appendChild(dur);
    bar.appendChild(scrub);

    var row = doc.createElement('div');
    row.className = 'skfull-row';

    var bRestart = btn('skfull-restart', 'Restart', ICON.restart);
    var bPlay = btn('skfull-play', 'Play', ICON.play);
    var bLoop = btn('skfull-loop', 'Repeat', ICON.loop);
    var bMute = btn('skfull-mute', 'Mute', ICON.sound);
    var bRate = btn('skfull-rate', 'Speed', '');
    bRate.textContent = '1×';
    row.appendChild(bRestart);
    row.appendChild(bPlay);
    row.appendChild(bLoop);
    row.appendChild(bMute);
    row.appendChild(bRate);

    /* WHO AND WHAT, on the same bar. Full screen is the one place a viewer has
       no card around the drawing to read, so the bar carries it. */
    var who = doc.createElement('div');
    who.className = 'skfull-who';
    var av = doc.createElement('span');
    av.className = 'skfull-av';
    av.setAttribute('aria-hidden', 'true');
    var words = doc.createElement('div');
    words.className = 'skfull-words';
    var tTitle = doc.createElement('div');
    tTitle.className = 'skfull-title';
    var tWho = doc.createElement('div');
    tWho.className = 'skfull-by';
    words.appendChild(tTitle);
    words.appendChild(tWho);
    who.appendChild(av);
    who.appendChild(words);
    row.appendChild(who);

    var bExit = btn('skfull-exit', 'Leave full screen', ICON.exit);
    row.appendChild(bExit);
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
      var i = RATES.indexOf(pl.rate());
      pl.setRate(RATES[(i + 1) % RATES.length]);
      sync();
    });
    bExit.addEventListener('click', function () {
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
      dur.textContent = mmss(total);
      track.setAttribute('aria-valuenow', String(Math.round(total ? el / total * 100 : 0)));

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
       rAF per hidden bar per tile is a feed burning battery on nothing. */
    var raf = null;
    function loop() {
      sync();
      raf = global.requestAnimationFrame(loop);
    }
    function running(on) {
      if (on && !raf) loop();
      if (!on && raf) { global.cancelAnimationFrame(raf); raf = null; }
    }

    sync();
    return { el: bar, sync: sync, running: running };
  }

  global.SkriblFullBar = { attach: attach, RATES: RATES };
})(window);
