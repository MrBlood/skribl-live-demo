/* The smart fade: one reading of a drawing for every bar that lies over it.
 *
 * THE OWNER, at the Gallery card: "The fade has to be like the glass with
 * smart fade, sampling the background for the fade colors and making it
 * subtle. It's so obvious and ugly when it's wrong." Then "Smart fade is
 * good", and for every full screen, from the measured mock, "A, smart fade
 * and yes to all". The card's bar and the Gallery's and the Library's full
 * screen (lib/fullbar.js), the link page's (app.js) and the editors'
 * (lib/watchfull.js) read the drawing here and tone their controls here, so
 * no two of them can drift.
 *
 * THE DRAWING'S FOOT is its bottom eighth in 16 strips across, each strip the
 * middle value of its own pixels: a line of ink through a strip does not tint
 * it. What the canvas leaves clear is the ground painted under it.
 *
 * TONE. A control over ground that reads 115 or more (luma, of 255) wears the
 * light glass, under that the dark. Words go by what is under their own
 * letters, not their box; a name over light on one side and dark on the
 * other (a title crossing a tall drawing's edge on a desk) gets a capsule,
 * `cap`, that carries its ink over both.
 *
 * NOTHING ON A GUESS. A drawing that cannot be read keeps the scrim the bar
 * had before: another site's card, and a photo under the drawing as a picture
 * of its own (the link page's and the Pad's), which the canvas does not hold.
 *
 *   SkriblSmartFade.foot(canvas, ground) -> 16 [r, g, b], or null
 *   SkriblSmartFade.medians(px)          -> the same, from 96x12 pixels read elsewhere
 *   SkriblSmartFade.ground(el)           -> the first colour painted under el, up from it
 *   SkriblSmartFade.gradient(cols)       -> the fade's colours, left to right
 *   SkriblSmartFade.tone(el, at, words)  -> sets t-dark or t-light; { dark, mixed }
 *   SkriblSmartFade.watchTheme(host, fn) -> fn after a theme turn while host is in the page
 *   SkriblSmartFade.full(bar, o)         -> a full screen's bar: { start, read, stop }
 */
(function (global) {
  'use strict';
  var doc = global.document, N = 16, W = 6, H = 12;

  function medians(px) {
    if (!px) return null;
    var out = [];
    for (var s = 0; s < N; s++) {
      var ch = [[], [], []];
      for (var y = 0; y < H; y++) {
        for (var x = s * W; x < s * W + W; x++) {
          for (var i = 0, o = (y * N * W + x) * 4; i < 3; i++) ch[i].push(px[o + i]);
        }
      }
      out.push(ch.map(function (v) { v.sort(function (a, b) { return a - b; }); return v[v.length >> 1]; }));
    }
    return out;
  }
  /* A canvas's foot, over the ground under it. A tainted canvas throws on the
     read, and is unreadable, not black. */
  function foot(cv, under) {
    try {
      var c = doc.createElement('canvas'), g = c.getContext('2d');
      c.width = N * W; c.height = H;
      g.fillStyle = rgb(under || [255, 255, 255]);
      g.fillRect(0, 0, N * W, H);
      g.drawImage(cv, cv.width * 0.01, cv.height * 0.875, cv.width * 0.98, cv.height * 0.115, 0, 0, N * W, H);
      return medians(g.getImageData(0, 0, N * W, H).data);
    } catch (e) { return null; }
  }
  function ground(el) {
    for (var e = el; e && e.nodeType === 1; e = e.parentElement) {
      var m = getComputedStyle(e).backgroundColor.match(/[\d.]+/g);
      if (m && (m.length < 4 || +m[3] > 0.5)) return [+m[0], +m[1], +m[2]];
    }
    return [255, 255, 255];
  }
  function rgb(v) { return 'rgb(' + v[0] + ' ' + v[1] + ' ' + v[2] + ')'; }
  /* The fade's colours, left to right, each strip at its middle. */
  function gradient(cols) {
    return 'linear-gradient(to right, ' + cols.map(function (v, k) {
      return rgb(v) + ' ' + ((k + 0.5) / cols.length * 100).toFixed(1) + '%';
    }).join(', ') + ')';
  }
  function luma(v) { return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; }
  /* Light or dark by what is under a control's box, or a word's letters. */
  function tone(el, at, words) {
    var q = el.getBoundingClientRect();
    if (words) {
      var rg = doc.createRange();
      rg.selectNodeContents(el);
      var t = rg.getBoundingClientRect();
      if (t.width) q = t;
    }
    var y = (q.top + q.bottom) / 2, L = 0, c = 0, lit = 0;
    for (var x = q.left; x <= q.right; x += 2) {
      var v = luma(at(x, y));
      L += v; c++;
      if (v >= 115) lit++;
    }
    var dark = !c || L / c < 115;
    el.classList.toggle('t-dark', dark);
    el.classList.toggle('t-light', !dark);
    return { dark: dark, mixed: lit > 0 && lit < c };
  }

  /* ONE WATCH ON THE PAGE'S THEME for every bar: the ground beside a drawing
     turns with it, and a control over that ground has to turn too. A bar
     whose host has left is dropped at the next turn. */
  var watched = [], themeOn = false;
  function themed() {
    watched = watched.filter(function (w) {
      if (!w.host.isConnected) return false;
      w.fn();
      return true;
    });
  }
  function watchTheme(host, fn) {
    var w = { host: host, fn: fn };
    watched.push(w);
    if (!themeOn) {
      themeOn = true;
      if (global.MutationObserver) {
        new MutationObserver(themed).observe(doc.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      }
      var mq = global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)');
      if (mq && mq.addEventListener) mq.addEventListener('change', themed);
    }
    return function () { watched = watched.filter(function (x) { return x !== w; }); };
  }

  /* A FULL SCREEN'S BAR over its drawing. The bar sets `--fx-l`, `--fx-r` and
     `--fx-b` (where the drawing sits under it), `--fade-x` (its foot's
     colours, left to right) and `is-smart`; each control, word and name takes
     its tone. Read when full screen opens and when its state changes (a play,
     a pause, the end), never on the beat; toned again on a resize or a theme
     turn.
       o.canvas()  the canvas showing the drawing, or null
       o.contain   the drawing is letterboxed inside the canvas's box
       o.photo()   a photo shows under the drawing as a picture of its own
       o.glass     controls, toned by their box (a selector in the bar)
       o.words     words, toned by their letters
       o.caps      names, which also take the capsule where they cross */
  function full(bar, o) {
    var cols = null, on = false, ro = null, unwatch = null;
    function each(sel, fn) {
      if (!sel) return;
      var list = bar.querySelectorAll(sel);
      for (var i = 0; i < list.length; i++) if (list[i].getClientRects().length) fn(list[i]);
    }
    function off() {
      bar.classList.remove('is-smart');
      each('.t-dark, .t-light', function (el) { el.classList.remove('t-dark', 't-light', 'cap'); });
    }
    /* Where the drawing is on screen: the canvas's box, or inside it where
       object-fit: contain letterboxes it. */
    function drawn(cv) {
      var r = cv.getBoundingClientRect();
      if (!o.contain || !cv.width || !cv.height) return r;
      var s = Math.min(r.width / cv.width, r.height / cv.height), w = cv.width * s, h = cv.height * s;
      return { left: r.left + (r.width - w) / 2, right: r.left + (r.width + w) / 2,
               top: r.top + (r.height - h) / 2, bottom: r.top + (r.height + h) / 2 };
    }
    function update() {
      if (!on) return;
      var cv = o.canvas && o.canvas();
      if (!cv || !cv.width || !bar.isConnected || (o.photo && o.photo())) { cols = null; return off(); }
      var m = ground(cv), a = drawn(cv), b = bar.getBoundingClientRect();
      if (!cols) cols = foot(cv, m);
      if (!cols || !b.width || a.right - a.left < 8) return off();
      var s = bar.style, n = cols.length, w = a.right - a.left;
      s.setProperty('--fx-l', Math.max(0, a.left - b.left).toFixed(1) + 'px');
      s.setProperty('--fx-r', Math.max(0, b.right - a.right).toFixed(1) + 'px');
      s.setProperty('--fx-b', Math.max(0, b.bottom - a.bottom).toFixed(1) + 'px');
      s.setProperty('--fade-x', gradient(cols));
      bar.classList.add('is-smart');
      function at(x, y) {
        if (x < a.left || x > a.right || y < a.top || y > a.bottom) return m;
        return cols[Math.max(0, Math.min(n - 1, Math.floor((x - a.left) / w * n)))];
      }
      each(o.glass, function (el) { tone(el, at, false); });
      each(o.words, function (el) { tone(el, at, true); });
      each(o.caps, function (el) { el.classList.toggle('cap', tone(el, at, true).mixed); });
    }
    return {
      start: function () {
        if (on) return;
        on = true;
        cols = null;
        if (global.ResizeObserver) {
          ro = new ResizeObserver(update);
          ro.observe(bar);
          var cv = o.canvas && o.canvas();
          if (cv) ro.observe(cv);
        }
        unwatch = watchTheme(bar, update);
        update();
      },
      /* What shows changed (a play, a pause, the end, a page): read again. */
      read: function () { if (on) { cols = null; update(); } },
      stop: function () {
        on = false;
        if (ro) ro.disconnect();
        if (unwatch) unwatch();
        ro = unwatch = null;
        off();
      }
    };
  }

  global.SkriblSmartFade = { foot: foot, medians: medians, ground: ground, gradient: gradient,
                             tone: tone, watchTheme: watchTheme, full: full };
})(window);
