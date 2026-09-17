/* Two rows per case: the corpus as authored (uniform sampling), and the same
   drawing as a hand would have recorded it -- every run independently
   resampled at 3-18px per point, seeded per case so a re-run repeats.

   AND SINCE v300, A VERDICT. Through v295-v299 this corpus answered "did the
   render change?" and never "is the render right?", which an outside review of
   v299 called a photo album, correctly. Each case now carries expectations
   (see cases.js) and the sheet says PASS or FAIL in its own corner.

   THE EXPECTATIONS ARE COMPUTED FROM THE POSES, not typed into the case. Both
   rows draw the same geometry at different densities, so a number written into
   a case could only ever be true of one of them -- and telling a correct
   hand-sampled render from a broken one is the whole reason the second row
   exists. */
window.__RUN = function(ci){
  const cs = window.__CASES[ci];
  const chips = [];
  window.chip = function(m){ chips.push(m); };
  try { chip = function(m){ chips.push(m); }; } catch(e){}

  // ---- deterministic per-case hand sampling --------------------------------
  const seeded = (s) => () => (s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  function handFrame(f, rnd){
    const out = { strokes: [], strokeGroups: [], hold: f.hold };
    let at = 0, t = 0;
    for (const g of f.strokeGroups) {
      const r = f.strokes.slice(at, at + g); at += g;
      // A TAP has no length to resample along, and every hand records it the
      // same way: one point. Walking it as a polyline read past the end.
      if (r.length < 2) {
        const q = Object.assign({}, r[0]); q.t = t; t += 16; q.start = true;
        out.strokes.push(q); out.strokeGroups.push(1); continue;
      }
      // Arc length of this run, then a spacing this "hand" used for it.
      let L = 0;
      for (let i = 1; i < r.length; i++) L += Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
      const step = 3 + rnd() * 15;                       // 3-18px per point
      const n = Math.max(2, Math.round(L / step) + 1);
      const d = [0];
      for (let i = 1; i < r.length; i++)
        d.push(d[i-1] + Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y));
      const pts = [];
      for (let k = 0; k < n; k++) {
        const target = (d[d.length-1]) * (n === 1 ? 0 : k / (n - 1));
        let j = 1;
        while (j < d.length - 1 && d[j] < target) j++;
        const span = d[j] - d[j-1], u = span > 0 ? (target - d[j-1]) / span : 0;
        const a = r[j-1], b = r[j];
        const q = Object.assign({}, u < 0.5 ? a : b);
        q.x = a.x + (b.x - a.x) * u; q.y = a.y + (b.y - a.y) * u;
        q.t = t; t += 16;
        if (k === 0) q.start = true; else delete q.start;
        pts.push(q);
      }
      out.strokes.push(...pts); out.strokeGroups.push(pts.length);
    }
    return out;
  }

  // ---- one variant: drive both buttons, record what came out ---------------
  function variant(A, B){
    const rec = {};
    const reset = () => {
      frames = [JSON.parse(JSON.stringify(A)), JSON.parse(JSON.stringify(B))];
      idx = 0; fps = 12; subdiv = 1; selSpans = [];
      try { actionLog.length = 0; redoStack.length = 0; } catch(e){}
      try { buildStrip(); render(); } catch(e){ chips.push('BUILD ' + e.message); }
    };
    // Correspondence, read straight off the matcher, before either button runs.
    try {
      const ra = tweenVisible(A).ink, rb = tweenVisible(B).ink;
      rec.pairing = tweenMatch(ra, rb).map(m => m ? m.j : null);
      rec.runsA = ra.length; rec.runsB = rb.length;
    } catch(e){ rec.pairing = 'THREW: ' + e.message; }

    reset();
    const n0 = frames.length;
    let ib = null; rec.ibErr = null;
    try { addInbetween(); } catch(e){ rec.ibErr = e.message; }
    if (frames.length > n0) ib = JSON.parse(JSON.stringify(frames[1]));
    rec.ibChips = chips.slice(); chips.length = 0;
    rec.ibPts = ib ? ib.strokes.length : 0;
    rec.ibRuns = ib ? ib.strokeGroups.length : 0;
    rec.ibHolds = ib ? [frames[0].hold, frames[1].hold] : null;

    reset();
    let tw = null; rec.twErr = null;
    try { addTween(); } catch(e){ rec.twErr = e.message; }
    if (frames.length > n0) tw = JSON.parse(JSON.stringify(frames[1]));
    rec.twChips = chips.slice(); chips.length = 0;
    rec.twPts = tw ? tw.strokes.length : 0;
    rec.twRuns = tw ? tw.strokeGroups.length : 0;
    /* GEOMETRY, not just counts. Point counts cannot see a change that moves
       points -- which is exactly what the rotation fit and the residual walk
       do -- so every generated page also reports its arc length per run, its
       centroid, its bounding box and a positional digest. */
    const geom = (f) => {
      if (!f) return null;
      let at = 0, L = 0, per = [];
      for (const g of f.strokeGroups) {
        const r = f.strokes.slice(at, at + g); at += g;
        let l = 0;
        for (let i = 1; i < r.length; i++) l += Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
        per.push(Math.round(l * 10) / 10); L += l;
      }
      // ARC-WEIGHTED, alongside the point mean. The mean of the samples moves
      // when the same drawing is recorded more densely in one place; the
      // middle of the INK does not, and an expectation has to hold on both
      // rows or it is a statement about the recording rather than the drawing.
      let at2 = 0, tot = 0, ax = 0, ay = 0, ers = 0;
      for (const g of f.strokeGroups) {
        const r = f.strokes.slice(at2, at2 + g); at2 += g;
        if (r[0] && r[0].erase) ers++;
        if (r.length < 2) { ax += r[0].x * 1; ay += r[0].y * 1; tot += 1; continue; }
        for (let i = 1; i < r.length; i++) {
          const d = Math.hypot(r[i].x-r[i-1].x, r[i].y-r[i-1].y);
          tot += d; ax += (r[i].x+r[i-1].x)/2 * d; ay += (r[i].y+r[i-1].y)/2 * d;
        }
      }
      const n = f.strokes.length || 1;
      let cx = 0, cy = 0, minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9, h = 0;
      for (const p of f.strokes) {
        cx += p.x / n; cy += p.y / n;
        minx = Math.min(minx, p.x); maxx = Math.max(maxx, p.x);
        miny = Math.min(miny, p.y); maxy = Math.max(maxy, p.y);
        h = (h * 31 + Math.round(p.x * 4)) | 0; h = (h * 31 + Math.round(p.y * 4)) | 0;
      }
      const r1 = (v) => Math.round(v * 10) / 10;
      return { len: r1(L), perRun: per, cx: r1(cx), cy: r1(cy),
               acx: r1(tot > 0 ? ax/tot : cx), acy: r1(tot > 0 ? ay/tot : cy),
               erasers: ers, runs: f.strokeGroups.length,
               bbox: [minx, miny, maxx, maxy].map(r1), hash: h };
    };
    rec.ibGeom = geom(ib); rec.twGeom = geom(tw);
    rec.aGeom = geom(A); rec.bGeom = geom(B);

    /* ---- THE ORACLE ------------------------------------------------------
       Until v300 this corpus answered "did it change?" and never "is it
       right?" -- an outside review of v299 called it a photo album, which it
       was. Each case now carries expectations, and they are stated against
       the POSES rather than against numbers typed into the case, so the same
       expectation holds on the uniform row and on the hand-sampled one.

       Deliberately a handful of shapes, not a language. The suites are where
       a gate belongs; this says whether a render is worth looking at. */
    const E = {
      made: () => ({ name: 'an in-between was produced',
        ok: !!ib && !rec.ibErr, got: rec.ibErr || (ib ? 'made' : 'refused') }),
      // NOT "inside the canvas": this corpus deliberately authors shapes larger
      // than the default page, so that bound failed six correct renders before
      // it was calibrated. What it is for is ink flung off to 1.04e17 by a fit
      // divided by float dust, and the honest bound on a pose BETWEEN two
      // others is the ground those two already stand on.
      onCanvas: (m) => () => { m = m === undefined ? 80 : m;
        const nm = 'the ink stays within reach of the two poses';
        if (!ib) return { name: nm, ok: false, got: 'no page' };
        const a = rec.aGeom.bbox, c = rec.bGeom.bbox, b = rec.ibGeom.bbox;
        const lo = [Math.min(a[0],c[0]) - m, Math.min(a[1],c[1]) - m];
        const hi = [Math.max(a[2],c[2]) + m, Math.max(a[3],c[3]) + m];
        return { name: nm,
                 ok: b[0] >= lo[0] && b[1] >= lo[1] && b[2] <= hi[0] && b[3] <= hi[1],
                 got: `${b.join(',')} against ${lo.concat(hi).join(',')}` }; },
      mid: (tol) => () => { tol = tol || 6;
        if (!ib) return { name: 'the ink sits half way between the poses', ok: false, got: 'no page' };
        const wx = (rec.aGeom.acx + rec.bGeom.acx)/2, wy = (rec.aGeom.acy + rec.bGeom.acy)/2;
        const dx = rec.ibGeom.acx - wx, dy = rec.ibGeom.acy - wy;
        return { name: 'the ink sits half way between the poses',
                 ok: Math.hypot(dx, dy) <= tol,
                 got: `(${rec.ibGeom.acx},${rec.ibGeom.acy}) want (${Math.round(wx*10)/10},${Math.round(wy*10)/10})` }; },
      len: (pct) => () => { pct = pct || 8;
        if (!ib) return { name: 'it spends the ink the poses spend', ok: false, got: 'no page' };
        const want = (rec.aGeom.len + rec.bGeom.len)/2;
        const off = want > 0 ? Math.abs(rec.ibGeom.len - want)/want*100 : 0;
        return { name: 'it spends the ink the poses spend',
                 ok: off <= pct, got: `${rec.ibGeom.len} vs ${Math.round(want*10)/10} (${off.toFixed(1)}%)` }; },
      runs: (n) => () => ({ name: `it carries ${n} run${n===1?'':'s'}`,
        ok: !!ib && rec.ibGeom.runs === n, got: ib ? String(rec.ibGeom.runs) : 'no page' }),
      erasers: (n) => () => ({ name: `it carries ${n} eraser${n===1?'':'s'}`,
        ok: !!ib && rec.ibGeom.erasers === n, got: ib ? String(rec.ibGeom.erasers) : 'no page' }),
      pairs: (want) => () => ({ name: 'each stroke found its own partner',
        ok: JSON.stringify(rec.pairing) === JSON.stringify(want),
        got: JSON.stringify(rec.pairing) }),
      holds: (sum) => () => { if (!rec.ibHolds) return { name: 'the pair lands in the middle of the interval', ok: false, got: 'no page' };
        const [a, g] = rec.ibHolds;
        return { name: 'the pair lands in the middle of the interval',
                 ok: Math.abs(a - g) <= 1 && a + g === sum, got: `${a}+${g} of ${sum}` }; },
    };
    const want = [E.made, E.onCanvas()].concat((cs.expect || function(){ return []; })(E));
    rec.oracle = want.map(fn => { try { return fn(); }
                                  catch(e){ return { name: 'expectation', ok: false, got: 'THREW ' + e.message }; } });
    rec.verdict = rec.oracle.every(r => r.ok) ? 'PASS' : 'FAIL';
    return { rec: rec, ib: ib, tw: tw };
  }

  const rnd = seeded(9001 + ci * 7919);
  const hA = handFrame(cs.a, rnd), hB = handFrame(cs.b, rnd);
  const base = variant(cs.a, cs.b);
  const hand = variant(hA, hB);

  // ---- render: two rows of four ------------------------------------------
  const PW = 330, PAD = 10, HEAD = 46, LAB = 26, ROW = PW + LAB + PAD;
  const cols = 4;
  const lines = [];
  [['uniform', base.rec], ['hand-sampled', hand.rec]].forEach(([tag, r]) => {
    r.oracle.forEach(x => lines.push((x.ok ? '\u2713 ' : '\u2717 ') + tag + ': ' + x.name + ' \u2014 ' + x.got));
  });
  const FOOT = 14 + lines.length * 15;
  const out = document.createElement('canvas');
  out.width = cols*PW + (cols+1)*PAD;
  out.height = HEAD + 2*ROW + PAD + FOOT;
  const o = out.getContext('2d');
  o.fillStyle = '#e9e9ec'; o.fillRect(0,0,out.width,out.height);
  o.fillStyle = '#111'; o.font = 'bold 20px sans-serif';
  o.fillText(cs.id + '  ' + cs.name, PAD, 26);
  o.font = '14px sans-serif'; o.fillStyle = '#444';
  o.fillText(cs.note, PAD, 42);
  const bad = base.rec.verdict === 'FAIL' || hand.rec.verdict === 'FAIL';
  o.fillStyle = bad ? '#b00020' : '#127a3a';
  o.font = 'bold 20px sans-serif';
  const vt = bad ? 'FAIL' : 'PASS';
  o.fillText(vt, out.width - PAD - o.measureText(vt).width, 26);

  const tmp = document.createElement('canvas'); tmp.width = CW; tmp.height = CH;
  const tc = tmp.getContext('2d');
  function panel(frame, label, col, row, tint){
    const x = PAD + col*(PW+PAD), y = HEAD + PAD + row*ROW;
    tc.setTransform(1,0,0,1,0,0);
    tc.fillStyle = '#ffffff'; tc.fillRect(0,0,CW,CH);
    if (frame) { try { paintStatic(tc, frame.strokes); } catch(e){
      tc.fillStyle='#c00'; tc.font='28px sans-serif'; tc.fillText('paint threw: '+e.message, 20, 60); } }
    else { tc.fillStyle='#fbe9e9'; tc.fillRect(0,0,CW,CH);
           tc.fillStyle='#a00'; tc.font='34px sans-serif'; tc.fillText('NOT PRODUCED', 60, CH/2); }
    o.drawImage(tmp, x, y, PW, PW);
    o.strokeStyle = tint || '#999'; o.lineWidth = tint ? 3 : 1;
    o.strokeRect(x+0.5, y+0.5, PW-1, PW-1);
    o.fillStyle = '#111'; o.font = 'bold 13px sans-serif';
    let sub = label;
    if (frame) sub += '  (' + frame.strokes.length + ' pts, ' + frame.strokeGroups.length + ' runs)';
    o.fillText(sub, x, y + PW + 16);
  }
  const rows = [[cs.a, cs.b, base, 'uniform'], [hA, hB, hand, 'hand-sampled']];
  rows.forEach(([A, B, v, tag], i) => {
    panel(A,     'A ' + tag, 0, i, '#2a7');
    panel(v.ib,  'IN-BETWEEN' + (v.rec.ibErr ? ' THREW: '+v.rec.ibErr : ''), 1, i, '#c50');
    panel(v.tw,  'MOTION SMEAR' + (v.rec.twErr ? ' THREW: '+v.rec.twErr : ''), 2, i, '#05a');
    panel(B,     'B ' + tag, 3, i, '#2a7');
  });

  o.font = '13px monospace';
  lines.forEach((t, i) => {
    o.fillStyle = t[0] === '\u2713' ? '#127a3a' : '#b00020';
    o.fillText(t, PAD, HEAD + 2*ROW + PAD + 14 + i*15);
  });

  return { id: cs.id, name: cs.name, png: out.toDataURL('image/png'),
           verdict: bad ? 'FAIL' : 'PASS',
           oracle: { uniform: base.rec.oracle, hand: hand.rec.oracle },
           base: base.rec, hand: hand.rec };
};
