/* Draw along: a drawing from the little book, laid faintly on your own
 * canvas one stroke at a time, for you to trace at your pace (owner, after
 * v323: the little book mock, "Yes to all as long as it's kind"; FUTURE.md
 * 6p). One module for the Pad and Flip (on Flip, the page you are on).
 *
 * THE REPLAY IS THE PERFORMANCE: the guide is the example's real strokes in
 * the order its artist drew them. What you have traced is your own ink; the
 * NEXT stroke is drawn darker, with a dot where it starts; the rest wait,
 * faint.
 *
 * KIND. It never judges a line: any stroke you draw on the page counts, and
 * the next one shows. No timer. Skip moves on a stroke, Done (or Escape)
 * puts the guide away and keeps what you drew. The guide is its own canvas
 * in the zoom layer (so it zooms and pans with the drawing), never part of
 * the drawing: not recorded, posted or exported.
 */
(function () {
  'use strict';
  var NAMES = { cat: 'the cat' };
  var cache = {};
  var run = null;

  function target() { return document.getElementById('canvas') || document.getElementById('pad'); }
  function strokesOf(payload) {
    var out = [], cur = null, pts = (payload && payload.frames && payload.frames[0] && payload.frames[0].strokes) || [];
    pts.forEach(function (p) {
      if (p.start || !cur) { cur = []; out.push(cur); }
      cur.push(p);
    });
    return out;
  }
  function css(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function paint() {
    if (!run) return;
    var cv = target(), g = run.guide;
    if (!cv) return;
    var w = cv.offsetWidth, h = cv.offsetHeight, dpr = window.devicePixelRatio || 1;
    g.style.left = cv.offsetLeft + 'px';
    g.style.top = cv.offsetTop + 'px';
    g.style.width = w + 'px';
    g.style.height = h + 'px';
    g.width = Math.round(w * dpr);
    g.height = Math.round(h * dpr);
    var c = g.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    var W = run.size.w, H = run.size.h;
    var s = Math.min(w / W, h / H) * 0.92, ox = (w - W * s) / 2, oy = (h - H * s) / 2;
    var accent = css('--accent', '#7c5cff'), ink = css('--text-primary', '#11161e');
    var halo = css('--menu-card', '#ffffff');
    c.lineCap = 'round';
    c.lineJoin = 'round';
    function line(st, width, colour, alpha) {
      c.globalAlpha = alpha;
      c.strokeStyle = colour;
      for (var j = 1; j < st.length; j++) {
        c.beginPath();
        c.moveTo(ox + st[j - 1].x * s, oy + st[j - 1].y * s);
        c.lineTo(ox + st[j].x * s, oy + st[j].y * s);
        c.lineWidth = width(st[j]);
        c.stroke();
      }
    }
    run.strokes.forEach(function (st, k) {
      if (k <= run.k) return;
      line(st, function (p) { return Math.max(1.2, p.size * s * 0.8); }, accent, 0.3);
    });
    var nx = run.strokes[run.k];
    if (nx) {
      // The next stroke on a halo of the card's colour, so it shows on any
      // background colour the drawing has.
      line(nx, function (p) { return Math.max(3, p.size * s * 1.1) + 4; }, halo, 0.85);
      line(nx, function (p) { return Math.max(3, p.size * s * 1.1); }, ink, 0.9);
      var p0 = nx[0];
      c.globalAlpha = 1;
      c.fillStyle = accent;
      c.beginPath(); c.arc(ox + p0.x * s, oy + p0.y * s, 7, 0, Math.PI * 2); c.fill();
      c.strokeStyle = '#fff'; c.lineWidth = 2.5;
      c.beginPath(); c.arc(ox + p0.x * s, oy + p0.y * s, 7, 0, Math.PI * 2); c.stroke();
    }
    c.globalAlpha = 1;
  }
  function say() {
    if (!run) return;
    var n = run.strokes.length;
    if (run.k >= n) {
      // Short enough for a phone's pill, which cannot wrap (192px there: "You
      // drew the cat. Press Play to watch it." was cut off mid-word), and
      // Flip's next step is a second page, since one page has no Play.
      run.where.textContent = document.getElementById('strip') ? 'You drew it! Tap Duplicate.' : 'You drew it! Tap Play.';
      run.skip.hidden = true;
    } else {
      run.where.textContent = run.name + ' · ' + (run.k + 1) + ' of ' + n;
    }
  }
  function advance() {
    if (!run || run.k >= run.strokes.length) return;
    run.k++;
    say();
    paint();
  }
  function place() {
    if (!run) return;
    var head = document.querySelector('.header');
    var b = head ? head.getBoundingClientRect().bottom : 0;
    run.pill.style.top = Math.max(8, b + 8) + 'px';
  }

  function stop() {
    if (!run) return;
    run.guide.remove();
    run.pill.remove();
    document.body.classList.remove('drawalong');
    window.removeEventListener('resize', run.onResize);
    document.removeEventListener('pointerdown', run.onDown, true);
    document.removeEventListener('pointerup', run.onUp, true);
    document.removeEventListener('pointercancel', run.onUp, true);
    document.removeEventListener('keydown', run.onKey, true);
    run = null;
  }

  function start(name) {
    stop();
    // Its own address on the little book (both editors), else the example's.
    var book = document.getElementById('bookRoot');
    var card = document.querySelector('#helpWatch .learn-card[data-demo-name="' + name + '"]');
    var url = (book && book.getAttribute('data-along-' + name)) || (card && card.getAttribute('data-demo'));
    var cv = target();
    if (!url || !cv) return false;
    if (!cache[url]) cache[url] = fetch(url).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    cache[url].then(function (payload) {
      var strokes = strokesOf(payload);
      if (!strokes.length) return;
      var size = (payload.canvasSize && payload.canvasSize.cssWidth) ? { w: payload.canvasSize.cssWidth, h: payload.canvasSize.cssHeight } : { w: 816, h: 612 };
      var guide = document.createElement('canvas');
      guide.className = 'da-guide';
      guide.setAttribute('aria-hidden', 'true');
      cv.parentNode.insertBefore(guide, cv.nextSibling);
      var pill = document.createElement('div');
      pill.className = 'da-pill';
      pill.setAttribute('role', 'region');
      pill.setAttribute('aria-label', 'Draw along');
      pill.innerHTML = '<b>Draw along</b><span class="da-where" aria-live="polite"></span>'
        + '<button type="button" class="da-skip">Skip</button><button type="button" class="da-done">Done</button>';
      document.body.appendChild(pill);
      document.body.classList.add('drawalong');
      var down = null;
      run = {
        name: NAMES[name] || name, strokes: strokes, size: size, k: 0, guide: guide, pill: pill,
        where: pill.querySelector('.da-where'), skip: pill.querySelector('.da-skip'),
        onResize: function () { place(); paint(); },
        // Any stroke on the page counts: down on the drawing, up after moving.
        onDown: function (e) {
          down = (e.isPrimary && (e.target === cv || e.target === guide)) ? { x: e.clientX, y: e.clientY, d: 0 } : null;
          if (down) document.addEventListener('pointermove', move, true);
        },
        onUp: function (e) {
          document.removeEventListener('pointermove', move, true);
          if (down && down.d > 6 && e.type === 'pointerup') setTimeout(advance, 60);
          down = null;
        },
        onKey: function (e) { if (e.key === 'Escape' && run) { e.preventDefault(); stop(); } }
      };
      function move(e) { if (down) down.d = Math.max(down.d, Math.hypot(e.clientX - down.x, e.clientY - down.y)); }
      run.skip.addEventListener('click', advance);
      pill.querySelector('.da-done').addEventListener('click', stop);
      window.addEventListener('resize', run.onResize);
      document.addEventListener('pointerdown', run.onDown, true);
      document.addEventListener('pointerup', run.onUp, true);
      document.addEventListener('pointercancel', run.onUp, true);
      document.addEventListener('keydown', run.onKey, true);
      say();
      place();
      paint();
    });
    return true;
  }

  window.SkriblDrawAlong = {
    start: start, stop: stop, skip: advance,
    state: function () { return run ? { k: run.k, n: run.strokes.length } : null; }
  };
}());
