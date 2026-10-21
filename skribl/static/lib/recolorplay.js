/* A recolour in the replay (the owner's pick R2 of the recolour mock: the
 * Pad's replay shows the change when you made it).
 *
 * The Pad keeps the moment of each recolour (app.js `recolors`, made by
 * lib/recolor.js): the line (`g`, one of the drawing's strokeGroups), the
 * colour it had and took (`was`, `to`), how many points the drawing had then
 * (`n`), which gesture (`k`) and the point the colour ran from (`at`). The
 * points carry the colour they ENDED with, so every still picture is right
 * without this file. It is what every REPLAY of a Pad drawing does with the
 * moments -- the editor's Play, the link page, the in-post player and the
 * three exports -- so they cannot show them differently:
 *
 *   place(timeline, points, groups, list)
 *       after a timeline is built and untied. A recoloured line plays in the
 *       colour it was drawn in; each moment becomes two entries where it
 *       happened, one that makes the change (`rc`) and, RUN later, one where
 *       it has finished (`rcEnd`); everything after waits RUN, the time the
 *       colour takes to run along the line, as it did in the editor. Returns
 *       the timeline (a new array when there are moments, else the same one).
 *   extra(points, list)    RUN for each moment: the length a replay gains.
 *   player(o)    the engine's side of it. A replay core hands it each entry
 *       carrying `rc` instead of drawing it (on), and asks it for the run at
 *       the replay's time (tick, or compose for an export's frames).
 *   stopAll()    a repaint from the base ends whatever run is showing.
 *
 * A MOMENT COUNTS by one rule, which the server keeps too
 * (validation._payload_line, so the line under a post says the replay's
 * length): an object whose `k` is a whole number from 0 and whose `n` is a
 * whole number from 1 to the points there are. The entries with one `k` are
 * one moment, at the `n` of its first; the moments go in order of `n`, then
 * of where they first appear. Its lines PAINT only where the line is one the
 * drawing has, wholly drawn by then, and both colours read; a moment whose
 * lines do not still waits its RUN, so a replay's length never depends on
 * what paints.
 *
 * THE CHANGE IS A REPAINT, never a line drawn over the old one: a later line
 * drawn across it, an eraser's stroke through it and a see-through colour are
 * all exactly as the finished drawing has them only if the whole drawing so
 * far is painted again in its colours as of the moment. The engine owns that
 * paint (its base, its compositor); this file says what to paint.
 *
 * THE RUN shows the drawing as it was across the part of each line the
 * colour has not reached, shrinking from the point it ran from to both ends,
 * as lib/recolor.js shows it in the editor. Drawn on a canvas of its own laid
 * over the drawing, which shows the drawing as it now is everywhere else, so
 * the drawing's own canvas is hidden while it runs and never painted by it:
 * nothing a seek or a copy reads can be caught half run. An export has no
 * screen to lay one over, and draws compose() into its frames instead. Under
 * Reduce Motion the colour simply changes, and the moment is a still RUN.
 */
(function (global) {
  'use strict';

  var RUN = 380;   // ms of replay for a new colour to run the length of a line

  /* ---- colour ------------------------------------------------------------ */

  // '#rrggbb' for any colour a point is written in, or null.
  function hexOf(c) {
    var s = typeof c === 'string' ? c.trim() : '', m;
    if ((m = /^#([0-9a-f]{6})([0-9a-f]{2})?$/i.exec(s))) return '#' + m[1].toLowerCase();
    if ((m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*[\d.]+\s*)?\)$/i.exec(s))) {
      var h = '#';
      for (var i = 1; i < 4; i++) h += ('0' + Math.max(0, Math.min(255, Math.round(+m[i]))).toString(16)).slice(-2);
      return h;
    }
    return null;
  }

  /* `hex` in the form and at the opacity of `old`: '#rrggbb' for a solid
     line, 'rgba(r, g, b, a)' as the Pad's opacity and brushes write it,
     '#rrggbbaa' as a Motion Smear does. lib/recolor.js gives a line its new
     colour by this rule, so the replay's colours are the editor's. */
  function tint(old, hex) {
    var h = hexOf(hex);
    if (!h) return old;
    var s = typeof old === 'string' ? old.trim() : '', m;
    if ((m = /^#[0-9a-f]{6}([0-9a-f]{2})$/i.exec(s))) return h + m[1].toLowerCase();
    if ((m = /^rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)$/i.exec(s))) {
      return 'rgba(' + parseInt(h.slice(1, 3), 16) + ', ' + parseInt(h.slice(3, 5), 16) + ', ' +
        parseInt(h.slice(5, 7), 16) + ', ' + m[1] + ')';
    }
    return h;
  }

  /* ---- the moments ------------------------------------------------------- */

  function whole(v, lo, hi) {
    return typeof v === 'number' && isFinite(v) && Math.floor(v) === v && v >= lo && v <= hi;
  }

  function moments(points, list) {
    var out = [], byK = {};
    if (!Array.isArray(list) || !points || !points.length) return out;
    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      if (!e || typeof e !== 'object' || Array.isArray(e)) continue;
      if (!whole(e.k, 0, Infinity) || !whole(e.n, 1, points.length)) continue;
      var m = byK['k' + e.k];
      if (!m) { m = byK['k' + e.k] = { n: e.n, first: i, lines: [] }; out.push(m); }
      m.lines.push(e);
    }
    out.sort(function (a, b) { return a.n - b.n || a.first - b.first; });
    return out;
  }

  function extra(points, list) { return moments(points, list).length * RUN; }

  /* What each moment paints, and the colour each recoloured line had when it
     was drawn (the `was` of its first moment). */
  function plan(points, groups, list) {
    var ms = moments(points, list);
    if (!ms.length) return null;
    var st = [0], at = 0, first = {}, gs = Array.isArray(groups) ? groups : [];
    for (var g = 0; g < gs.length; g++) { at += Math.max(0, gs[g] | 0); st.push(Math.min(at, points.length)); }
    for (var mi = 0; mi < ms.length; mi++) {
      var m = ms[mi];
      m.paint = [];
      for (var j = 0; j < m.lines.length; j++) {
        var e = m.lines[j], to = hexOf(e.to), was = hexOf(e.was);
        if (!whole(e.g, 0, gs.length - 1) || !to || !was) continue;
        var a = st[e.g], b = st[e.g + 1];
        if (b <= a || b > m.n) continue;
        if (!(e.g in first)) first[e.g] = was;
        m.paint.push({ g: e.g, a: a, b: b, from: a + Math.max(0, Math.min(b - a - 1, e.at | 0)), hex: to });
      }
    }
    return { ms: ms, st: st, first: first, points: points };
  }

  function recoloured(p, hex) {
    var c = tint(p.color, hex);
    if (c === p.color) return p;
    var q = {};
    for (var k in p) q[k] = p[k];
    q.color = c;
    return q;
  }

  /* The drawing as it stood just after moment `mi`: its points up to then,
     each recoloured line in the colour that moment left it. */
  function after(P, mi) {
    var pts = P.points, m = P.ms[mi], out = pts.slice(0, m.n), now = {}, g, i;
    for (var j = 0; j <= mi; j++) P.ms[j].paint.forEach(function (l) { now[l.g] = l.hex; });
    for (g in P.first) {
      var hex = now[g] || P.first[g], b = Math.min(P.st[+g + 1], m.n);
      for (i = P.st[g]; i < b; i++) out[i] = recoloured(pts[i], hex);
    }
    return out;
  }

  function place(tl, points, groups, list) {
    var P = tl && tl.length ? plan(points, groups, list) : null;
    if (!P) return tl;
    var pos = [], j, g, i;
    for (j = 0; j < tl.length; j++) pos[tl[j].i] = j;
    for (g in P.first) {
      for (i = P.st[g]; i < P.st[+g + 1]; i++) {
        var e = tl[pos[i]];
        if (e) e.color = tint(points[i].color, P.first[g]);
      }
    }
    var out = [], mi = 0, shift = 0;
    for (j = 0; j <= tl.length; j++) {
      var at = j < tl.length ? tl[j].i : points.length;
      while (mi < P.ms.length && P.ms[mi].n <= at) {
        var m = P.ms[mi], prev = out[out.length - 1], T = prev ? prev.playT : 0;
        var l = m.paint[0], o = l ? recoloured(points[l.from], l.hex) : (prev || points[m.n - 1]);
        for (var end = 0; end < 2; end++) {
          out.push({ x: o.x, y: o.y, color: o.color, size: o.size, erase: false, start: true,
                     playT: T + end * RUN, i: m.n - 1, rc: m, rcAt: mi, rcEnd: !!end, rcPlan: P, rcPos: out.length });
        }
        shift += RUN;
        mi++;
        // A line never runs on from a moment's mark.
        if (j < tl.length) tl[j].start = true;
      }
      if (j < tl.length) { tl[j].playT += shift; out.push(tl[j]); }
    }
    return out;
  }

  /* ---- the run ----------------------------------------------------------- */

  var live = [];

  function reduced() {
    try { return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    catch (e) { return false; }
  }

  function copyOf(c) {
    var k = global.document.createElement('canvas');
    k.width = c.width; k.height = c.height;
    k.getContext('2d').drawImage(c, 0, 0);
    return k;
  }

  // A line as the run reads it: its points, and the arc length to each.
  function runOf(pts, l) {
    var P = [], cum = [0];
    for (var i = l.a; i < l.b; i++) {
      P.push({ x: pts[i].x, y: pts[i].y, w: pts[i].size || 1 });
      if (P.length > 1) { var q = P[P.length - 2], r = P[P.length - 1]; cum.push(cum[cum.length - 1] + Math.hypot(r.x - q.x, r.y - q.y)); }
    }
    var s0 = cum[l.from - l.a] || 0, total = cum[cum.length - 1];
    return { P: P, cum: cum, s0: s0, span: Math.max(s0, total - s0) };
  }

  /* The part of each line the colour has not reached at `e` (0..1), each
     segment at its own width and a device pixel more each side, round-capped
     as the painters cap it: quick, then gentle, as the editor's run eases. */
  function unreached(c, runs, e, pad) {
    c.lineCap = 'round'; c.lineJoin = 'round';
    c.strokeStyle = c.fillStyle = '#000';
    var reach = 1 - Math.pow(1 - e, 3);
    runs.forEach(function (r) {
      var P = r.P, cum = r.cum, total = cum[cum.length - 1], d = reach * r.span;
      if (P.length === 1) {
        if (e < 0.5) { c.beginPath(); c.arc(P[0].x, P[0].y, P[0].w / 2 + pad, 0, Math.PI * 2); c.fill(); }
        return;
      }
      [[0, r.s0 - d], [r.s0 + d, total]].forEach(function (s) {
        if (s[1] <= s[0]) return;
        for (var i = 0; i + 1 < P.length; i++) {
          var a = cum[i], b = cum[i + 1];
          if (b < s[0] || a > s[1]) continue;
          var p = P[i], q = P[i + 1], L = b - a || 1;
          var u = Math.max(0, (s[0] - a) / L), v = Math.min(1, (s[1] - a) / L);
          c.lineWidth = Math.max(p.w, q.w) + 2 * pad;
          c.beginPath();
          c.moveTo(p.x + (q.x - p.x) * u, p.y + (q.y - p.y) * u);
          c.lineTo(p.x + (q.x - p.x) * v, p.y + (q.y - p.y) * v);
          c.stroke();
        }
      });
    });
  }

  /* o:
       canvas            the canvas the replay draws on
       unit()            its backing px per drawing unit
       repaint(pts, comp)  paint the canvas as just these points on its base,
                         leaving `comp` (the replay core's compositor, if
                         any) holding exactly that
       overlay           false for an export: no canvas laid over anything */
  function player(o) {
    var cur = null, view = null, scratch = null, hidden = null, api;

    function frame(target, e) {
      var c = o.canvas, k = o.unit() || 1, w = c.width, h = c.height;
      if (!scratch) scratch = global.document.createElement('canvas');
      if (scratch.width !== w || scratch.height !== h) { scratch.width = w; scratch.height = h; }
      if (target.width !== w || target.height !== h) { target.width = w; target.height = h; }
      var s = scratch.getContext('2d'), t = target.getContext('2d');
      // What was there, inside the part not reached...
      s.setTransform(1, 0, 0, 1, 0, 0); s.globalCompositeOperation = 'source-over';
      s.clearRect(0, 0, w, h);
      s.setTransform(k, 0, 0, k, 0, 0); unreached(s, cur.runs, e, 1 / k);
      s.setTransform(1, 0, 0, 1, 0, 0); s.globalCompositeOperation = 'source-in';
      s.drawImage(cur.before, 0, 0, w, h);
      s.globalCompositeOperation = 'source-over';
      // ...over the drawing as it now is, with that part cut out of it.
      t.setTransform(1, 0, 0, 1, 0, 0); t.globalCompositeOperation = 'source-over'; t.globalAlpha = 1;
      t.clearRect(0, 0, w, h);
      t.drawImage(c, 0, 0);
      t.globalCompositeOperation = 'destination-out';
      t.setTransform(k, 0, 0, k, 0, 0); unreached(t, cur.runs, e, 1 / k);
      t.setTransform(1, 0, 0, 1, 0, 0); t.globalCompositeOperation = 'source-over';
      t.drawImage(scratch, 0, 0);
      return target;
    }

    // Laid exactly where the canvas paints: its own box inside its border, in
    // the parent that transforms it (as lib/gridoverlay.js lays the grid), and
    // with the canvas's own transform and fit, which is how the in-post
    // player centres its canvas and letterboxes it in full screen.
    function lay() {
      var c = o.canvas, cs = global.getComputedStyle(c);
      var bl = parseFloat(cs.borderLeftWidth) || 0, bt = parseFloat(cs.borderTopWidth) || 0;
      if (!view) {
        view = global.document.createElement('canvas');
        view.className = 'recolor-run';
        view.setAttribute('aria-hidden', 'true');
      }
      if (view.parentNode !== c.parentNode || view.previousSibling !== c) c.parentNode.insertBefore(view, c.nextSibling);
      var s = view.style, org = String(cs.transformOrigin).split(' ');
      s.position = 'absolute';
      s.pointerEvents = 'none';
      s.margin = '0';
      s.maxWidth = s.maxHeight = 'none';
      // An absolute canvas (the in-post player's, at 50%) is placed by its
      // used left and top, which keep the fraction offsetLeft rounds away: a
      // run half a pixel off its drawing would hop back as it ends.
      var abs = cs.position === 'absolute' && cs.left !== 'auto' && cs.top !== 'auto';
      s.left = ((abs ? parseFloat(cs.left) + (parseFloat(cs.marginLeft) || 0) : c.offsetLeft) + bl) + 'px';
      s.top = ((abs ? parseFloat(cs.top) + (parseFloat(cs.marginTop) || 0) : c.offsetTop) + bt) + 'px';
      // ...and sized by its used size, fraction and all, for the same reason.
      var w = parseFloat(cs.width) || c.clientWidth, h = parseFloat(cs.height) || c.clientHeight;
      if (cs.boxSizing === 'border-box') {
        w -= bl + (parseFloat(cs.borderRightWidth) || 0) + (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
        h -= bt + (parseFloat(cs.borderBottomWidth) || 0) + (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
      }
      s.width = Math.max(0, w) + 'px';
      s.height = Math.max(0, h) + 'px';
      s.transform = cs.transform === 'none' ? '' : cs.transform;
      s.transformOrigin = ((parseFloat(org[0]) || 0) - bl) + 'px ' + ((parseFloat(org[1]) || 0) - bt) + 'px';
      s.objectFit = cs.objectFit;
      s.objectPosition = cs.objectPosition;
      s.zIndex = cs.zIndex === 'auto' ? '' : cs.zIndex;
      if (hidden === null) {
        hidden = { o: c.style.opacity, t: c.style.transition };
        c.style.transition = 'none';
        c.style.opacity = '0';
      }
    }

    function end() {
      cur = null;
      if (hidden !== null) { o.canvas.style.opacity = hidden.o; o.canvas.style.transition = hidden.t; hidden = null; }
      if (view && view.parentNode) view.parentNode.removeChild(view);
      var i = live.indexOf(api);
      if (i >= 0) live.splice(i, 1);
    }

    function on(p, comp) {
      end();
      if (p.rcEnd) return;
      var P = p.rcPlan, m = p.rc, before = null;
      if (m.paint.length && !reduced()) {
        if (comp && comp.present) comp.present();   // what the screen shows, the stroke in progress too
        try { before = copyOf(o.canvas); } catch (e) { before = null; }
      }
      o.repaint(after(P, p.rcAt), comp);
      if (!before) return;
      cur = { t: p.playT, pos: p.rcPos, before: before, runs: m.paint.map(function (l) { return runOf(P.points, l); }) };
      live.push(api);
    }

    function at(ms) {
      if (!cur) return -1;
      var e = (ms - cur.t) / RUN;
      if (!(e >= 0 && e < 1)) { end(); return -1; }
      return e;
    }

    api = {
      on: on,
      stop: end,
      // A seek that goes on drawing from entry `i`: a run whose moment is
      // drawn again from there ends (it starts again when it is), and one
      // already behind the canvas carries on, so a scrub through it glides.
      from: function (i) { if (cur && cur.pos >= i) end(); },
      running: function () { return !!cur; },
      // The run on screen at the replay's time `ms`.
      tick: function (ms) {
        var e = at(ms);
        if (e < 0 || o.overlay === false) return;
        lay();
        frame(view, e);
      },
      // An export's frame at `ms`: the canvas to draw in place of the
      // drawing's, or null when no colour is running.
      compose: function (ms) {
        var e = at(ms);
        if (e < 0) return null;
        if (!view) view = global.document.createElement('canvas');
        return frame(view, e);
      }
    };
    return api;
  }

  function stopAll() { live.slice().forEach(function (r) { r.stop(); }); }

  global.SkriblRecolorPlay = {
    RUN: RUN, hexOf: hexOf, tint: tint, moments: moments, extra: extra,
    place: place, player: player, stopAll: stopAll,
    // lib/recolor.js's run in the editor reads a line and draws its part not
    // reached as the replay does: one shape for the colour running.
    line: function (pts, from) { return runOf(pts, { a: 0, b: pts.length, from: Math.max(0, Math.min(pts.length - 1, from | 0)) }); },
    unreached: unreached
  };
})(typeof window !== 'undefined' ? window : this);
