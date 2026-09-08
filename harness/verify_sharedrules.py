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
      const probe = [undefined, null, {}, {hold:null}, {hold:0}, {hold:-3},
                     {hold:1}, {hold:2}, {hold:4}, {hold:5}, {hold:99},
                     {hold:'2'}, {hold:'x'}, {hold:2.4}, {hold:2.6}];
      return { max: H.MAX_HOLD, read: probe.map(f => H.holdOf(f)),
               viaFlip: probe.map(f => frameHold(f)) }; }""")
    check("a missing, zero, negative or junk hold reads as 1",
          clamp["read"][:6] == [1, 1, 1, 1, 1, 1], str(clamp["read"][:6]))
    check("a real hold is kept and an absurd one is clamped",
          clamp["read"][6:11] == [1, 2, 4, clamp["max"], clamp["max"]],
          f"{clamp['read'][6:11]} with MAX_HOLD={clamp['max']}")
    check("a numeric string reads, a non-numeric one does not",
          clamp["read"][11] == 2 and clamp["read"][12] == 1, str(clamp["read"][11:13]))
    check("fractional holds round rather than truncate",
          clamp["read"][13] == 2 and clamp["read"][14] == 3, str(clamp["read"][13:15]))
    check("flip.js's frameHold() gives the module's answer for every input",
          clamp["viaFlip"] == clamp["read"],
          f"{clamp['viaFlip']} vs {clamp['read']} — the editor keeps a second rule")

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
                        // what the file shows at a fixed wall-clock instant
                        atHalf: H.dueCount(f, u[Math.min(u.length - 1,
                                  Math.floor((trueMs / 2) / slot))].prog),
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
        # The parity the feature promises: at the same instant of wall clock,
        # the file shows the same amount of the drawing whatever the document's
        # frame rate. Compared in POINTS revealed, within one frame's worth.
        worst, where = 0, ""
        for r in exp:
            got = [r["per"][str(rate)]["atHalf"] for rate in (6, 12, 24)]
            spread = (max(got) - min(got)) / r["per"]["6"]["points"]
            if spread > worst:
                worst, where = spread, f"{r['span']}ms span: {got} points at 6/12/24fps"
        check("halfway through, 6, 12 and 24 fps show the same amount of the drawing",
              worst < 0.12,
              f"{where} — {worst:.0%} of the page apart; a drawing page is "
              f"exempt from fps and the exported file has to honour that too")
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

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 62)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
sys.exit(0 if ok == len(results) else 1)
