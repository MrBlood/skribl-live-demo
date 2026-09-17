"""The rules both surfaces read out of lib/ — holds, layering cost, stroke alpha.

verify_parity.py already guards the CONTROLS Pad and Flip share, and says why:
"they drift and nobody notices", because every other suite drives one surface.
This is the same problem one layer down. Not the controls — the RULES:

    what a `hold` means            flip.js frameHold + runPlayTimer
                                   app.js  flipHolds + flipIndexAt
    how much layering a frame may  flip.js LAYER_BUDGET
    afford                         app.js  had no ceiling at all
    what alpha a stroke carries    flip.js alphaOf
                                   app.js  parseStrokeAlpha

All three had two implementations. All three had diverged:

  * the hold: app.js's cumulative table was right, flip.js's timer took its
    delay from the page AFTER the one on screen and never wrapped its index, so
    a hold stretched the wrong page and stopped working after the first loop.
  * the ceiling: Flip's editor caps what one frame spends compositing
    see-through strokes; the player never did, so a document could play
    smoothly while authoring and stall for the viewer.
  * the alpha: flip.js's regex was unanchored and matched rgb() as well as
    rgba(), so the greedy body let the BLUE channel land in the alpha group —
    alphaOf('rgb(255,176,32)') returned 32.

The shape is always the same and it is worth naming: the EDITOR and the PLAYER
disagreeing is uniquely expensive, because nothing an author can see reveals it.
The preview is not the product.

The two mechanisms stay different where they should — the player maps a clock to
an index, the editor reschedules a timer — so what is asserted is not shared
code but that they cannot disagree about the ANSWER.

The first block is the one that actually breaks in practice: skribl_player.html
loads a handful of libs, not the editor's thirty-odd, so a new dependency is
easy to add everywhere except the surface that needs it most. That happened
twice while writing this.
"""
import json
import os
import sys
import urllib.request
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the surfaces agree.")
    raise SystemExit(77)

results = []
check = make_check(results)


def post_flip():
    """A small flip Skribl, so /s/<id> renders the real player."""
    pts = [{"x": 100 + i * 20, "y": 100, "color": "#ffffff", "size": 8,
            "t": i * 3, "erase": False, "start": i == 0} for i in range(6)]
    def frame(dy, hold):
        return {"strokes": [dict(p, y=p["y"] + dy) for p in pts],
                "strokeGroups": [len(pts)], "hold": hold}
    payload = {"title": "sharedrules", "skribl": {
        "version": 2, "schemaVersion": 2, "playbackMode": "flip", "fps": 12,
        "frames": [frame(0, 1), frame(60, 2), frame(120, 1)],
        "canvasSize": {"cssWidth": 816, "cssHeight": 612, "dpr": 1}}}
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


with sync_playwright() as p:
    browser = p.chromium.launch()

    print("EVERY SURFACE LOADS THE MODULES — the player's lib list is the short "
          "one, and it is the one that must not miss")
    surfaces = [("flip editor", "/flip"), ("pad editor", "/")]
    posted = None
    try:
        posted = post_flip()
        surfaces.append(("player", posted["url"]))
    except Exception as exc:
        print(f"  (could not post: {type(exc).__name__}: {exc})")
    check("a flip Skribl was posted, so the PLAYER is exercised too",
          posted is not None,
          "without it this suite only proves the editors agree with each other")

    for label, path in surfaces:
        pg = browser.new_page(viewport={"width": 1000, "height": 860})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1400)
        got = pg.evaluate("""() => ({
            hold: !!(window.SkriblHold && window.SkriblHold.holdOf),
            layers: !!(window.SkriblStrokeLayers && window.SkriblStrokeLayers.overBudget) })""")
        check(f"{label} loads lib/holdtiming.js", got["hold"],
              f"window.SkriblHold is undefined at {path} — this surface is "
              f"running its own copy of the hold rule")
        check(f"{label} loads lib/strokelayers.js with the budget", got["layers"],
              f"no overBudget() at {path} — this surface has no ceiling on "
              f"what one frame may spend compositing")
        check(f"{label} has no JS errors", not errs, "; ".join(errs[:2]))
        pg.close()

    pg = browser.new_page(viewport={"width": 1000, "height": 860})
    perrs = []
    pg.on("pageerror", lambda e: perrs.append(str(e)))
    browsing.goto(pg, BASE, "/flip")

    # ---- holds: the editor's timer vs the player's clock ------------------
    print("\nA HOLD MEANS THE SAME THING ON BOTH — swept over tables and rates")
    swept = pg.evaluate("""() => {
      const H = window.SkriblHold;
      if (!H) return null;
      // A page carrying `draw` is EXEMPT FROM fps and lasts its own stroke
      // span, so the sweep covers both kinds. `d` marks a drawing page; its
      // strokes are shaped to a known span so the expected window is knowable.
      const mkDraw = ms => ({ draw: true, strokes: [{t:0},{t:ms}] });
      const CASES = [[[1,1,1],12],[[1,2,1,3,1],12],[[4,1,4],8],[[2],12],
                     [[1,3],30],[[1,1,4,1],24],[[3,3,3],12],[[1,2,3,4,1],15],
                     [[1,'d1200',1],12],[['d600'],24],[[2,'d900',3,'d400'],6],
                     [['d2000','d320'],30]];
      const rows = [];
      for (const [hs, fps] of CASES) {
        const frames = hs.map(h => typeof h === 'string'
          ? mkDraw(parseInt(h.slice(1), 10)) : ({ hold: h }));
        const ms = H.msTable(frames, fps);
        let acc = 0, worst = 0, order = true;
        for (let i = 0; i < ms.length; i++) {
          const start = acc, end = acc + ms[i];
          // pageMs IS the window the clock keeps that page for — the editor's
          // timer and the player's clock reading the same number is the whole
          // point of this module.
          const diff = Math.abs(H.pageMs(frames[i], fps) - (end - start));
          if (diff > worst) worst = diff;
          if (H.indexAtMs(ms, start + 0.001) !== i) order = false;
          if (H.indexAtMs(ms, (start + end) / 2) !== i) order = false;
          if (H.indexAtMs(ms, end - 0.001) !== i) order = false;
          acc += ms[i];
        }
        rows.push({ hs, fps, worst, order, dur: H.cycleMs(ms),
                    sum: ms.reduce((a, b) => a + b, 0) });
      }
      return rows; }""")
    check("the swept comparison ran", swept is not None, "window.SkriblHold missing")
    if swept:
        _d = [f"{r['hs']}@{r['fps']}fps off by {r['worst']:.3f}ms"
              for r in swept if r["worst"] > 1e-9]
        check("the editor's slot length equals the player's clock window, exactly",
              not _d, "; ".join(_d[:4]))
        _o = [f"{r['hs']}@{r['fps']}fps" for r in swept if not r["order"]]
        check("and the clock stays on that page for the whole window",
              not _o, "page changes inside its own slot at: " + ", ".join(_o[:4]))
        _u = [f"{r['hs']}@{r['fps']}" for r in swept
              if abs(r["dur"] - r["sum"]) > 1e-9]
        check("a cycle lasts exactly its hold units at the frame rate", not _u, ", ".join(_u[:4]))
        check("the sweep covered several rates, not just 12fps",
              len(set(r["fps"] for r in swept)) >= 4,
              f"only {len(set(r['fps'] for r in swept))} rates")

    print("\nTHE CLAMP — one definition, read defensively")
    clamp = pg.evaluate("""() => {
      const H = window.SkriblHold;
      const M = H.MAX_HOLD;
      const probe = [undefined, null, {}, {hold:null}, {hold:0}, {hold:-3},
                     {hold:1}, {hold:2}, {hold:M}, {hold:M+1}, {hold:99},
                     {hold:'2'}, {hold:'x'}, {hold:2.4}, {hold:2.6}];
      return { max: H.MAX_HOLD, read: probe.map(f => H.holdOf(f)),
               viaFlip: probe.map(f => frameHold(f)) }; }""")
    check("a missing, zero, negative or junk hold reads as 1",
          clamp["read"][:6] == [1, 1, 1, 1, 1, 1], str(clamp["read"][:6]))
    check("a real hold is kept and an absurd one is clamped",
          clamp["read"][6:11] == [1, 2, clamp["max"], clamp["max"], clamp["max"]],
          f"{clamp['read'][6:11]} with MAX_HOLD={clamp['max']}")
    check("a numeric string reads, a non-numeric one does not",
          clamp["read"][11] == 2 and clamp["read"][12] == 1, str(clamp["read"][11:13]))
    check("fractional holds round rather than truncate",
          clamp["read"][13] == 2 and clamp["read"][14] == 3, str(clamp["read"][13:15]))
    check("flip.js's frameHold() gives the module's answer for every input",
          clamp["viaFlip"] == clamp["read"],
          f"{clamp['viaFlip']} vs {clamp['read']} — the editor keeps a second rule")

    # ---- and the SERVER reads the same ceiling ----------------------------
    # The suite's own thesis, one layer further out: the editor and the player
    # disagreeing is expensive because nothing an author can see reveals it.
    # Neither does the editor and the SERVER disagreeing. The server took a hold
    # of 8 while every client clamped at 4, so a payload could post cleanly and
    # then play at half the duration it was written with, silently and forever.
    # Two independent literals in two languages with nothing tying them: the
    # same shape as the three divergences in this file's opening note.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from skribl import validation as _V
    def _accepts(h):
        return _V._validate_payload_complexity({
            "schemaVersion": 2, "version": 2, "playbackMode": "flip", "fps": 24,
            "canvasSize": {"cssWidth": 944, "cssHeight": 531, "dpr": 1},
            "frames": [{"strokes": [{"x": 10, "y": 10, "color": "#ffffff",
                                     "size": 5, "t": 0, "erase": False,
                                     "start": True}],
                        "strokeGroups": [1], "hold": h}]}) is None
    _cmax = clamp["max"]
    check("the server's hold ceiling is the one the clients actually obey",
          _V.MAX_HOLD == _cmax,
          f"server accepts up to {_V.MAX_HOLD}, clients clamp at {_cmax}")
    # Stated as behaviour and not as a number, so it still means something if
    # both ceilings move together later.
    _mute = [h for h in range(1, _V.MAX_HOLD + 1) if _accepts(h) and h > _cmax]
    check("no hold the server accepts is one a client would silently shorten",
          not _mute,
          f"holds {_mute} post cleanly and play as x{_cmax}")
    check("the ceiling itself posts, and one past it does not",
          _accepts(_cmax) and not _accepts(_V.MAX_HOLD + 1),
          f"accepts x{_cmax}: {_accepts(_cmax)}, "
          f"accepts x{_V.MAX_HOLD + 1}: {_accepts(_V.MAX_HOLD + 1)}")

    # ---- HOW A POINT IS WRITTEN -------------------------------------------
    print("\nHOW A POINT IS WRITTEN — the same spelling on both surfaces")
    pw = pg.evaluate("""() => {
      const W = window.SkriblPointWrite;
      const src = [{ x: 127.04332313965341, y: 99.5023777173913, color: '#26b0ff',
                     size: 7.343333333333333, t: 124272.30000001192,
                     erase: false, start: true },
                   { x: 3.14159265358979, y: 2.71828182845904, color: '#ffffff',
                     size: 2.0000000001, t: 8.999999, erase: true }];
      const one = { strokes: src, strokeGroups: [2] };
      const out = W.frames([one])[0];
      const raw = JSON.stringify(one), tidy = JSON.stringify(out);
      return { raw: raw.length, tidy: tidy.length,
               kept: out.strokes[0], eraser: out.strokes[1],
               dx: Math.abs(out.strokes[0].x - src[0].x),
               dy: Math.abs(out.strokes[0].y - src[0].y),
               mutated: src[0].erase === false && src[0].x === 127.04332313965341,
               norecipe: JSON.stringify(W.frames([{gen:{k:'smear'}}])[0]) }; }""")
    check("writing a point costs fewer bytes than printing a double",
          pw["tidy"] < pw["raw"], f'{pw["tidy"]} vs {pw["raw"]} bytes')
    # The saving is worth nothing if it moves the drawing. 0.01px is a thirtieth
    # of a device pixel at the largest canvas and dpr this app allows.
    check("...and no point moves as much as a hundredth of a pixel",
          pw["dx"] <= 0.005 and pw["dy"] <= 0.005, f'dx {pw["dx"]}, dy {pw["dy"]}')
    check("a false erase is left out, a true one is kept",
          not ("erase" in pw["kept"]) and pw["eraser"]["erase"] is True,
          f'{pw["kept"]} / {pw["eraser"]}')
    check("every other field survives untouched",
          pw["kept"]["color"] == "#26b0ff" and pw["kept"]["start"] is True,
          str(pw["kept"]))
    # A serializer that edits the live drawing would round the artwork itself,
    # and every later liquify pass would round its own output again.
    check("the live drawing is not edited by being written",
          pw["mutated"], "serializing mutated the frame it was handed")
    check("a page with no strokes passes through rather than gaining an empty one",
          '"gen"' in pw["norecipe"] and '"strokes"' not in pw["norecipe"],
          pw["norecipe"])
    # THE OMISSION IS ONLY SAFE WHILE EVERY READER TESTS TRUTHINESS. Asserted
    # against the readers themselves, not against a memory of having checked.
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _bad = []
    for _n in ("app.js", "flip.js", "inlineplayer.js",
               "lib/stamps.js", "lib/strokelayers.js"):
        _path = os.path.join(_root, "skribl", "static", *_n.split("/"))
        if not os.path.exists(_path):
            _bad.append(_n + " (missing)"); continue
        with open(_path) as _fh: _src = _fh.read()
        for _pat in ("erase === false", "erase !== false", "erase === undefined",
                     "'erase' in ", '"erase" in '):
            if _pat in _src: _bad.append(f"{_n}: {_pat}")
    check("no reader distinguishes erase:false from erase absent",
          not _bad, "; ".join(_bad[:3]))

    # BOTH PAINTERS TAKE THE UNIFORM-RUN PATH, OR ONE OF THEM BEADS.
    #
    # A Motion Smear ghost is see-through and its alpha rides in an 8-digit hex.
    # Both surfaces' LAYERING parsers match rgba() only, deliberately -- a
    # generated page on a per-stroke round trip is the stall v239 fixed -- so no
    # compositor sees a ghost, and painted dot-then-line-per-segment it stacks
    # against itself at every joint: written at 46/255 it painted at 83.
    # verify_beading measures that in PIXELS on the two surfaces a test page can
    # reach: Flip, and app.js's paintStrokesStatic, which draws the Pad and the
    # sealed /s/ player both. The in-post player's painter is module-private and
    # reachable from no test page, and the players are exactly where this project
    # keeps finding the second copy of a fixed bug -- so every surface is pinned
    # here too, at the source, which is the mechanism: the call has to be there.
    # MATCHED ON THE CALL, HANDED THE HEX-AWARE PARSER -- which is one pattern,
    # not two, and that matters. The first draft of this check looked for
    # "uniformRun(seg," and PASSED on a tree with the player's call deleted:
    # each file carries an inline FALLBACK whose declaration reads
    # `function uniformRun(seg, alphaFn)`, so the search found the definition of
    # the thing it was checking for the use of. A mutation said so; nothing else
    # would have. The call site hands in the surface's hex-aware alpha by name,
    # and no declaration anywhere spells that.
    _paint = []
    for _n, _alpha in (("flip.js", "strokeAlphaOf"),
                       ("inlineplayer.js", "anyStrokeAlpha"),
                       ("app.js", "anyStrokeAlpha")):
        _path = os.path.join(_root, "skribl", "static", _n)
        with open(_path) as _fh: _src = _fh.read()
        if f"(seg, {_alpha})" not in _src:
            _paint.append(f"{_n}: no uniform-run test handed {_alpha}")
    check("all three painters route a uniform see-through run through one path",
          not _paint, "; ".join(_paint))

    print("\nEDGES")
    # The ms API, same edges. A page is denominated in milliseconds now, so the
    # tables these are handed are ms rather than slots — the questions are
    # unchanged: does time before the start land on page 0, does time past the
    # end land on the last page, does an empty document divide by zero, and
    # does an absurd frame rate fall back rather than returning Infinity.
    edge = pg.evaluate("""() => { const H = window.SkriblHold;
      const ms = H.msTable([{hold:1},{hold:2},{hold:1}], 12); return {
        before: H.indexAtMs(ms,-500), after: H.indexAtMs(ms,1e9),
        empty: H.indexAtMs([],10), emptyDur: H.cycleMs([]),
        zeroFps: H.pageMs({hold:2},0), negFps: H.pageMs({hold:2},-5),
        nanFps: H.pageMs({hold:2},NaN), twelve: H.pageMs({hold:2},12),
        // A drawing page ignores the frame rate entirely — that IS its edge.
        drawAt6: H.pageMs({draw:true,strokes:[{t:0},{t:900}]},6),
        drawAt60: H.pageMs({draw:true,strokes:[{t:0},{t:900}]},60),
        drawEmpty: H.pageMs({draw:true,strokes:[]},12) }; }""")
    check("time before the start lands on the first page", edge["before"] == 0, str(edge["before"]))
    check("time past the end lands on the last page", edge["after"] == 2, str(edge["after"]))
    check("an empty document does not divide by zero",
          edge["empty"] == 0 and edge["emptyDur"] >= 1, str(edge))
    check("a missing or absurd frame rate falls back instead of returning Infinity",
          edge["zeroFps"] == edge["twelve"] and edge["negFps"] == edge["twelve"]
          and edge["nanFps"] == edge["twelve"], str(edge))
    check("a DRAWING page is exempt from the frame rate — same span at 6 and 60",
          edge["drawAt6"] == edge["drawAt60"] == 900,
          f"{edge['drawAt6']} vs {edge['drawAt60']} — a page that draws itself "
          f"lasts as long as its strokes took, whatever the document's fps")
    check("...and a drawing page with no strokes still occupies time",
          edge["drawEmpty"] >= 320,
          f"{edge['drawEmpty']} — a zero-length page is one the clock skips")

    print("\n" + "PROGRESS -> STROKES: ONE ANSWER, THREE CLASSES")
    # dueCount() exists because four renderers each turned progress into a
    # stroke count and disagreed at the ends of the range. The classes are the
    # contract; everything downstream is asserted against them.
    due = pg.evaluate("""() => { const H = window.SkriblHold;
      const f = { draw:true, strokes:[{t:0},{t:100},{t:200},{t:300},{t:400}] };
      return {
        zero: H.dueCount(f, 0), neg: H.dueCount(f, -1),
        nan: H.dueCount(f, NaN), undef: H.dueCount(f, undefined),
        tiny: H.dueCount(f, 1e-9), half: H.dueCount(f, 0.5),
        nearly: H.dueCount(f, 0.999), one: H.dueCount(f, 1),
        over: H.dueCount(f, 2),
        empty: H.dueCount({draw:true, strokes:[]}, 0.5),
        nul: H.dueCount(null, 0.5) }; }""")
    check("progress 0 reveals NOTHING", due["zero"] == 0, str(due["zero"]))
    check("a negative, NaN or missing progress is the start of the page, not the end",
          due["neg"] == due["nan"] == due["undef"] == 0,
          f"{due['neg']} / {due['nan']} / {due['undef']} — a clock that has not "
          f"produced a reading yet must not reveal the finished drawing")
    check("progress 1 reveals EVERY point", due["one"] == 5, str(due["one"]))
    check("progress past 1 does not overrun the stroke list",
          due["over"] == 5, str(due["over"]))
    check("a progress between them reveals a PREFIX, and it grows",
          0 < due["tiny"] <= due["half"] <= due["nearly"] < 5,
          f"{due['tiny']} / {due['half']} / {due['nearly']}")
    check("an empty or missing page reveals nothing rather than throwing",
          due["empty"] == 0 and due["nul"] == 0, str(due))

    print("\n" + "THE COMPOSITION: A PAGE REACHES ITS END BEFORE IT YIELDS")
    # pageMs() and dueCount() were each right and together could never show a
    # drawing page finished. indexAtMs() owns a page over [start, end), so the
    # clock leaves at exactly the instant progress would reach 1, and dueCount
    # releases the last point only AT 1. The 26th point of a 26-point page was
    # never due while that page was up. The invariant is about the composition,
    # not any one of the three, so it is asserted by stepping a clock.
    comp = pg.evaluate("""() => {
      const H = window.SkriblHold;
      const pts = []; for (let i = 0; i < 26; i++) pts.push({ t: i * 46 });
      const draw = { draw: true, strokes: pts };
      const frames = [draw, { hold: 1 }];
      const ms = H.msTable(frames, 6);
      const step = 1000 / 60;
      const run = guarded => {
        let last = null, sawComplete = false, sawPrefix = false,
            completeBeforeTurn = false, turned = false, mono = true, prev = 0,
            turns = 0;
        for (let e = 0; e <= 1600; e += step) {
          const d = guarded ? H.displayAt(ms, frames, e, last)
                            : { index: H.indexAtMs(ms, e),
                                progress: H.progressAt(ms, frames, e) };
          const n = H.dueCount(frames[d.index], d.progress);
          if (d.index === 0) {
            if (turned) turns++;            // came back round: a second visit
            if (n < prev) mono = false;
            prev = n;
            if (n === 26) sawComplete = true;
            else if (n > 0) sawPrefix = true;
          } else if (!turned) {
            turned = true;
            completeBeforeTurn = sawComplete;
          }
          last = d;
        }
        return { sawComplete, sawPrefix, completeBeforeTurn, mono, turned,
                 revisits: turns };
      };
      return { guarded: run(true), bare: run(false) }; }""")
    check("the composition sweep ran", bool(comp), "SkriblHold missing")
    if comp:
        g, bare = comp["guarded"], comp["bare"]
        check("a drawing page REACHES its complete recorded state on the live "
              "clock", g["sawComplete"],
              "no stepped instant showed every point while the page was current")
        check("...and does so BEFORE the clock moves to the next page",
              g["completeBeforeTurn"],
              "the page turned first — its last stroke would never be seen")
        check("...having shown a prefix first, so it revealed rather than "
              "appearing whole", g["sawPrefix"])
        check("...and the reveal never goes backwards", g["mono"])
        check("...and the guard yields rather than holding the page forever",
              g["turned"], "the clock never reached the second page")
        # The known-bad case, in the same run, so the assertion above cannot
        # quietly become vacuous: indexAtMs+progressAt alone must NOT get there.
        check("stated as the defect it fixes: indexAtMs and progressAt alone "
              "never reach the complete state",
              not bare["sawComplete"] and bare["sawPrefix"],
              f"unguarded sweep reported {bare} — if this ever shows complete, "
              f"the guard is no longer what is producing the terminal state and "
              f"the assertions above have stopped meaning anything")

    print("\n" + "EXPORT SAMPLES THE MILLISECOND TIMELINE, NOT THE fps GRID")
    # A drawing page is exempt from fps. The exporter must tick in the document
    # frame rate anyway — a file has frames — so the question is whether the
    # PAGE's duration survives that. It did not: the step count was rounded and
    # the progress was then spread over the rounded count, so the same page ran
    # 500 ms at 6 fps and 417 ms at 12 and 24, and at the shorter rates the last
    # strokes never appeared. Measured across every rate the editor offers.
    ep = browser.new_page(viewport={"width": 1000, "height": 860})
    eerrs = []
    ep.on("pageerror", lambda e: eerrs.append(str(e)))
    browsing.goto(ep, BASE, "/flip")
    exp = ep.evaluate("""() => {
      const H = window.SkriblHold;
      const mk = span => { const pts = [];
        const step = Math.max(1, Math.round(span / 20));
        for (let t = 0; t <= span; t += step) pts.push({ x:0, y:0, t: t });
        return { draw: true, strokes: pts, strokeGroups: [pts.length] }; };
      const SPANS = [320, 450, 700, 1000, 1234, 3333];
      const rows = [];
      const keepFrames = frames, keepFps = fps;
      for (const span of SPANS) {
        const f = mk(span);
        frames = [f];
        const trueMs = H.pageMs(f, 12);        // exempt from fps by definition
        const per = {};
        for (const rate of [6, 12, 24]) {
          fps = rate;
          const u = exportUnits(0, 0);
          const slot = 1000 / rate;
          per[rate] = { dur: u.length * slot, slot: slot,
                        first: u[0].prog, last: u[u.length - 1].prog,
                        mono: u.every((x, i) => i === 0 || x.prog >= u[i-1].prog),
                        // Unit k is on screen until (k+1)*slot. THE PROGRESS
                        // IT CARRIES MUST BE THE PROGRESS THAT INSTANT HAS
                        // REACHED on the page's own millisecond timeline —
                        // that is what "samples the ms timeline" means, and
                        // what denominating it in rounded slots destroyed.
                        drift: Math.max.apply(null, u.map((x, k) =>
                          Math.abs(x.prog - Math.min(1, ((k + 1) * slot) / trueMs)))),
                        points: f.strokes.length };
        }
        rows.push({ span: span, trueMs: trueMs, per: per });
      }
      frames = keepFrames; fps = keepFps;
      return rows; }""")
    check("the export sweep ran", bool(exp), "exportUnits or frames unreachable")
    if exp:
        short = [f"{r['span']}ms at {rate}fps ran {r['per'][str(rate)]['dur']:.0f}"
                 f" against {r['trueMs']:.0f}"
                 for r in exp for rate in (6, 12, 24)
                 if r["per"][str(rate)]["dur"] < r["trueMs"] - 1e-6]
        check("an exported drawing page is never SHORTER than its own duration",
              not short, "; ".join(short[:3]) + " — the missing time is the "
              "end of the drawing, so the file loses its last strokes")
        over = [(r["per"][str(rate)]["dur"] - r["trueMs"]) / r["per"][str(rate)]["slot"]
                for r in exp for rate in (6, 12, 24)]
        check("...and never longer than it by a whole frame",
              max(over) < 1.0,
              f"worst overrun {max(over):.3f} of a frame — whole frames cannot "
              f"land on an arbitrary millisecond, but the residue is the "
              f"encoder's floor and nothing more")
        ends = [r["per"][str(rate)]["last"] for r in exp for rate in (6, 12, 24)]
        check("the last exported frame of a drawing page is the COMPLETE page",
              all(abs(e - 1) < 1e-9 for e in ends), f"lowest {min(ends)}")
        check("progress never goes backwards within a page",
              all(r["per"][str(rate)]["mono"] for r in exp for rate in (6, 12, 24)))
        firsts = [r["per"][str(rate)]["first"] for r in exp for rate in (6, 12, 24)]
        check("the first exported frame is a prefix, not the finished page",
              all(0 < f < 1 for f in firsts),
              f"highest {max(firsts)} — a first frame at 1 is the old bug, "
              f"where a one-step page opened finished")
        # THE PARITY THE FEATURE PROMISES, stated where it can actually be
        # held. Two rates cannot show the same thing at the same instant to
        # better than a frame — a file has frames, and the coarser rate's is
        # wider. What CAN hold at every rate is that each exported frame
        # carries the progress the page's own millisecond timeline had reached
        # when that frame went up. Re-denominating the page in rounded slots
        # broke exactly this: progress was spread over however many steps the
        # rounding produced, so it ran ahead of, or behind, the real drawing.
        worst, where = 0.0, ""
        for r in exp:
            for rate in (6, 12, 24):
                d = r["per"][str(rate)]["drift"]
                if d > worst:
                    worst, where = d, f"{r['span']}ms span at {rate}fps"
        check("every exported frame carries the progress its own instant has "
              "reached on the millisecond timeline",
              worst < 0.01,
              f"{where} is off by {worst:.1%} of the page — the file's reveal "
              f"is running on the fps grid rather than on the page's own clock")
        # And the consequence a viewer would actually notice: the same page
        # runs for the same length of time at every rate, to within the
        # coarsest frame the editor offers.
        durs = [(r["span"], [r["per"][str(rate)]["dur"] for rate in (6, 12, 24)])
                for r in exp]
        wide = [f"{sp}ms span exports as {[round(d) for d in ds]}"
                for sp, ds in durs if max(ds) - min(ds) > 1000 / 6 + 1e-6]
        check("...so one page runs the same length at 6, 12 and 24 fps, within "
              "a frame of the slowest",
              not wide, "; ".join(wide[:3]))
    check("no JS errors while sweeping export units", not eerrs, "; ".join(eerrs[:2]))
    ep.close()

    # ---- the layering ceiling ---------------------------------------------
    print("\nTHE LAYERING CEILING — the same budget on both surfaces")
    budget = pg.evaluate("""() => {
      const S = window.SkriblStrokeLayers;
      const mk = (n, alpha) => { const out = [];
        for (let k = 0; k < n; k++) for (let i = 0; i < 3; i++)
          out.push({ x: i*10, y: k*4, color: alpha, size: 6, erase: false, start: i === 0 });
        return out; };
      const a = c => (typeof alphaOf === 'function' ? alphaOf(c) : 1);
      return { budget: S.BUDGET,
               few:   S.overBudget(mk(5,  'rgba(255,255,255,0.3)'), a),
               atCap: S.overBudget(mk(S.BUDGET, 'rgba(255,255,255,0.3)'), a),
               many:  S.overBudget(mk(S.BUDGET + 40, 'rgba(255,255,255,0.3)'), a),
               opaque:S.overBudget(mk(400, '#ffffff'), a),
               erased:S.overBudget(mk(400, 'rgba(255,255,255,0.3)').map(p => (p.erase = true, p)), a),
               empty: S.overBudget([], a) }; }""")
    check("a handful of see-through strokes is affordable", budget["few"] is False, str(budget))
    check("the budget itself is not over budget", budget["atCap"] is False,
          f"{budget['budget']} strokes already trips the {budget['budget']} budget")
    check("far too many is not", budget["many"] is True, str(budget["many"]))
    check("opaque strokes never count against it — they are not layered",
          budget["opaque"] is False, "400 opaque strokes read as over budget")
    check("nor do erase strokes, which are never layered either",
          budget["erased"] is False, "erase strokes counted against the budget")
    check("an empty frame is affordable", budget["empty"] is False, "")

    # The checks above prove the MODULE is right and loaded. They do NOT prove
    # each surface calls it, which is a different claim: a ceiling nobody
    # consults is not a ceiling.
    #
    # This is a SOURCE check, and deliberately so. The behavioural version was
    # attempted first and does not work on this canvas: Pad's draw path strips a
    # colour's alpha and leans on a globalAlpha that is 1 outside a live stroke,
    # so a see-through stroke renders solid whether it was layered or not, and
    # layered and un-layered frames are pixel-identical. Rather than assert
    # something weaker and call it behavioural, this asserts the wiring — which
    # is the regression that actually happens, someone deleting the call.
    print("\nAND EACH SURFACE CONSULTS IT — structural, see the note in the source")
    import re as _re
    for _file, _label in (("flip.js", "Flip editor"), ("app.js", "player + Pad")):
        try:
            with urllib.request.urlopen(BASE + "/static/skribl/" + _file, timeout=20) as _r:
                _src = _r.read().decode("utf-8", "replace")
        except Exception as _e:
            check(f"{_label}'s source could be read", False, f"{type(_e).__name__}: {_e}")
            continue
        check(f"{_label} asks the shared module about the layering budget",
              "SkriblStrokeLayers" in _src and "overBudget" in _src,
              f"{_file} never calls overBudget() — it either has no ceiling or "
              f"keeps a private one")
        check(f"{_label} reads the hold rule from the shared module",
              "SkriblHold" in _src,
              f"{_file} never touches window.SkriblHold")

    # ---- what alpha a stroke carries --------------------------------------
    print("\nSTROKE ALPHA — every form a payload may hold a colour in")
    col = pg.evaluate("""() => {
      const forms = ['rgb(10, 20, 30)', 'rgb(255,176,32)', 'rgba(1,2,3,0.4)',
                     '#ffb020', '#FFB020', '#ffb02080', 'rgba(255,176,32,0.5)',
                     'nonsense', ''];
      return forms.map(c => ({ c, alphaOf: alphaOf(c),
                               strokeAlpha: +strokeAlphaOf(c).toFixed(3),
                               fade: tweenFade(c, 0.04) })); }""")
    _by = {r["c"]: r for r in col}
    check("rgb() is not read as translucent — its BLUE channel is not an alpha",
          _by["rgb(255,176,32)"]["alphaOf"] == 1,
          f"alphaOf returned {_by['rgb(255,176,32)']['alphaOf']}; unanchored, the "
          f"greedy body lets the last channel land in the alpha group")
    check("and an in-between of an rgb() drawing actually fades",
          _by["rgb(255,176,32)"]["fade"].lower().endswith("0a"),
          f"tweenFade gave {_by['rgb(255,176,32)']['fade']} — ff means a stack "
          f"of fully opaque copies, no exposure at all")
    check("rgba() alpha is read", _by["rgba(1,2,3,0.4)"]["alphaOf"] == 0.4,
          str(_by["rgba(1,2,3,0.4)"]["alphaOf"]))
    check("an 8-digit hex carries an alpha for COMPOSING",
          _by["#ffb02080"]["strokeAlpha"] == 0.502, str(_by["#ffb02080"]))
    check("...but not for COSTING — teaching alphaOf about it would put every "
          "in-between back on the expensive path",
          _by["#ffb02080"]["alphaOf"] == 1, str(_by["#ffb02080"]["alphaOf"]))
    check("the two ways of writing the same colour agree",
          _by["#ffb02080"]["fade"] == _by["rgba(255,176,32,0.5)"]["fade"],
          f"{_by['#ffb02080']['fade']} vs {_by['rgba(255,176,32,0.5)']['fade']}")
    check("hex case does not matter",
          _by["#ffb020"]["fade"] == _by["#FFB020"]["fade"],
          f"{_by['#ffb020']['fade']} vs {_by['#FFB020']['fade']}")
    check("an unparsable colour is passed through untouched rather than mangled",
          _by["nonsense"]["fade"] == "nonsense" and _by[""]["fade"] == "",
          str([_by["nonsense"]["fade"], _by[""]["fade"]]))

    check("no JS errors across the whole suite", not perrs, "; ".join(perrs[:2]))
    pg.close()
    browser.close()

# ------------------------------------------------------------------ v299
# THE FALLBACK BRANCH, WHICH NOTHING HAD EVER EXECUTED.
#
# Every lib call site in this tree carries an inline fallback for "a surface
# that somehow loads without the module", and the whole point of this suite is
# that a rule with two copies and nothing forcing them to agree WILL drift. The
# fallbacks were exempt from that: every assertion above evaluates
# window.SkriblHold, so the lib-present path is pinned to the byte and the
# lib-absent path was pinned by nothing at all.
#
# It had drifted. flip.js fell back to MAX_HOLD = 4 and app.js clamped with a
# bare Math.min(h, 4), while holdtiming.js and validation.py both said 8. Those
# are not the same number by a factor of two, and 4 is the PRE-SUBDIVISION
# ceiling: carving a document doubles every hold, so a page the artist holds x4
# stores as 8. On a surface loading without the lib, every such page clamped
# back to 4 and the flip played at half its length -- which is, word for word,
# the failure the block above says it exists to prevent.
#
# Blocking the request is the only way to reach this branch: the fallback is
# chosen at load time by `window.SkriblHold` being absent, so nothing short of
# the module not arriving exercises it.
with sync_playwright() as _p2:
    _b2 = _p2.chromium.launch()
    _np = _b2.new_page(viewport={"width": 1000, "height": 860})
    _np.route("**/lib/holdtiming.js*", lambda r: r.abort())
    browsing.goto(_np, BASE, "/flip")
    _np.wait_for_timeout(600)
    _fb = _np.evaluate("""() => ({
      libGone: typeof window.SkriblHold,
      max: (typeof MAX_HOLD === 'number') ? MAX_HOLD : null,
      uiMax: (typeof UI_MAX_HOLD === 'number') ? UI_MAX_HOLD : null,
      // The clamp as the editor actually applies it, not the constant alone.
      clamped: [1, 2, 4, 8, 9, 99].map(h => frameHold({ hold: h }))
    })""")
    check("the lib is genuinely absent for this probe",
          _fb["libGone"] == "undefined",
          f"typeof window.SkriblHold = {_fb['libGone']!r} — if the module still "
          f"loaded, everything below is measuring the lib again")
    check("the editor's fallback ceiling is the one the lib and server carry",
          _fb["max"] == _V.MAX_HOLD,
          f"fallback MAX_HOLD={_fb['max']}, lib and server say {_V.MAX_HOLD} — "
          f"a subdivided page stores x8 and would clamp back to x{_fb['max']}, "
          f"playing at half the length the artist set")
    check("...and it clamps stored holds to that, not to the badge's range",
          _fb["clamped"] == [1, 2, 4, _V.MAX_HOLD, _V.MAX_HOLD, _V.MAX_HOLD],
          f"{_fb['clamped']} — x8 is a real stored value, not an absurd one")
    # The badge is a DIFFERENT number that really is 4, and conflating the two
    # is how the storage ceiling got written as 4 in the first place.
    check("the badge's range is separate, and still 4",
          _fb["uiMax"] == 4,
          f"UI_MAX_HOLD={_fb['uiMax']} — what a person cycles through is not "
          f"what the format stores")

    # The player's own fallback, which is a second copy on a second surface.
    # THE PAD, not Flip: app.js is the Pad's script and the player's, and it is
    # app.js that carries the player's inline clamp. /flip loads flip.js.
    _pp = _b2.new_page(viewport={"width": 1000, "height": 860})
    _pp.route("**/lib/holdtiming.js*", lambda r: r.abort())
    browsing.goto(_pp, BASE, "/")
    _pp.wait_for_timeout(400)
    # The URL is read off the page's own <script> tags rather than written out
    # here, so a change to the static mount point cannot leave this silently
    # fetching nothing. /static/skribl/app.js today, and not this check's
    # business tomorrow.
    _src = _pp.evaluate("""async () => {
      const s = [...document.scripts].map(t => t.src)
                  .find(u => /\\/app\\.js(\\?|$)/.test(u || ''));
      if (!s) return '';
      const r = await fetch(s);
      return await r.text(); }""")
    _pp.close(); _np.close(); _b2.close()
    # Source-read, and deliberately: the player's fallback is inside a closure
    # the page never exposes, so there is no window symbol to evaluate. Matched
    # on the clamp EXPRESSION rather than on a bare number, so a comment
    # mentioning 4 cannot satisfy it.
    import re as _re
    _m = _re.search(r"Math\.min\(h,\s*(\d+)\)", _src)
    check("the player's inline clamp carries the same ceiling",
          _m is not None and int(_m.group(1)) == _V.MAX_HOLD,
          f"app.js clamps at {_m.group(1) if _m else 'no match'} against "
          f"{_V.MAX_HOLD} — the same drift, on the surface with no lib to "
          f"correct it")

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 62)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
sys.exit(0 if ok == len(results) else 1)
