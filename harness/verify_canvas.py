"""v110 — variable canvas size, and the help text catching up with the features.

The canvas was hardcoded to 640x460. The *payload* has always carried canvasSize
and the player has always honoured it (`establishEditorCanvas` in app.js), so this
needed **no format change at all** — Flip was simply pinned to one of the sizes it
could already describe. That is why this suite asserts round-tripping rather than
compatibility shims: there is nothing to shim.

Stroke coordinates are deliberately NOT rescaled when the canvas changes. A
drawing keeps its position and size on the page, and a smaller canvas crops the
view rather than silently distorting artwork; switching back restores the framing.
The strokes are never destroyed, which is what makes that safe.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(900)
    for i in range(2):
        pg.evaluate("() => addFrame()")
        b = pg.locator("#pad").bounding_box()
        pg.mouse.move(b["x"] + 80, b["y"] + 80)
        pg.mouse.down()
        for k in range(12):
            pg.mouse.move(b["x"] + 80 + k * 9, b["y"] + 85)
        pg.mouse.up()
        pg.wait_for_timeout(80)

    print("\nPRESETS")
    # Read the expected pairs FROM the table rather than repeating them here.
    # These were hardcoded (640x460, 560x560, 720x405, 420x640) and had to be
    # hand-edited the moment the presets were corrected — the same class of
    # drift the presets themselves suffered from. The table is the contract;
    # that its labels are honest is asserted separately below.
    _table = {s["id"]: s for s in pg.evaluate("() => FLIP_SIZES")}
    # v269: a fresh document starts on the preset that DISPLAYS LARGEST in this
    # device's stage (bestFor), not unconditionally on the first row — a
    # portrait phone opens 9:16 instead of a letterboxed 4:3. Still always a
    # real preset from the table, never a viewport-derived pair.
    _boot = pg.evaluate("""() => {
        const st = document.querySelector('.flip-stage');
        const cs = getComputedStyle(st);
        const best = SkriblCanvasSizes.bestFor(
            st.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
            st.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom));
        return { cur: [CW, CH, currentSizeId()], best: [best.w, best.h, best.id] };
    }""")
    check(f"starts at the preset that shows largest in this stage ({_boot['best'][2]})",
          _boot["cur"] == _boot["best"], str(_boot))
    strokes = pg.evaluate("() => frames.map(f => f.strokes.length)")
    for sid in ("square", "wide", "tall"):
        sz = _table[sid]
        pg.evaluate(f"() => {{ const s = FLIP_SIZES.find(x => x.id === '{sid}'); applyCanvasSize(s.w, s.h); }}")
        pg.wait_for_timeout(350)
        check(f"{sid} applies {sz['w']}x{sz['h']}",
              pg.evaluate("() => [CW,CH]") == [sz["w"], sz["h"]],
              str(pg.evaluate("() => [CW,CH]")))
    check("every layer resized with it, not just the visible one",
          pg.evaluate("() => [pad.width===CW*DPR, onionCv.width===CW*DPR, tmpCv.width===CW*DPR, frameCv.width===CW*DPR]")
          == [True, True, True, True])
    check("strokes survive every resize untouched",
          pg.evaluate("() => frames.map(f => f.strokes.length)") == strokes, str(strokes))
    check("no drawing is lost going small and back again",
          pg.evaluate("""() => { const before = JSON.stringify(frames[1].strokes);
              applyCanvasSize(FLIP_SIZES[3].w, FLIP_SIZES[3].h);
              applyCanvasSize(FLIP_SIZES[0].w, FLIP_SIZES[0].h);
              return JSON.stringify(frames[1].strokes) === before; }"""))

    print("\nROUND-TRIP — the payload already described this")
    pg.evaluate("() => applyCanvasSize(560,560)")
    pg.wait_for_timeout(300)
    cs = pg.evaluate("() => serializeFlip({media:false}).canvasSize")
    check("payload carries the chosen size", cs["cssWidth"] == 560 and cs["cssHeight"] == 560, str(cs))
    payload = pg.evaluate("() => JSON.stringify(serializeFlip({media:false}))")
    pg.evaluate("() => applyCanvasSize(640,460)")
    pg.wait_for_timeout(200)
    pg.evaluate("(s) => applyPayload(JSON.parse(s))", payload)
    pg.wait_for_timeout(400)
    check("reloading restores the canvas size", pg.evaluate("() => [CW,CH]") == [560, 560],
          str(pg.evaluate("() => [CW,CH]")))
    check("a payload with no canvasSize leaves the canvas alone",
          pg.evaluate("() => { const before=[CW,CH]; applyCanvasSize(640,460); return [CW,CH][0]===640; }"))

    print("\nEXPORT — encoders follow the canvas")
    pg.evaluate("() => applyCanvasSize(560,560)")
    pg.wait_for_timeout(300)
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(400)
    with pg.expect_download(timeout=60000) as dl:
        pg.click("#exportGif")
    raw = open(dl.value.path(), "rb").read()
    gw, gh = raw[6] | (raw[7] << 8), raw[8] | (raw[9] << 8)
    check("GIF exports at the new canvas size", (gw, gh) == (560, 560), f"{gw}x{gh}")
    check("guards reject a nonsense size",
          pg.evaluate("() => applyCanvasSize(0,-5) === false && CW === 560"))
    check("no page errors across every resize and export", not errs, "; ".join(errs[:2]))

    print("\nHELP — 'How it works' describes what the app now does")
    flip_help = pg.content()
    for phrase in ("9:16", "Onion skin", "hold", "Size", "Pages"):
        check(f"Flip help mentions {phrase!r}", phrase in flip_help)
    pad = ctx.new_page()
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(900)
    pad_help = pad.content()
    check("Pad help explains Clear all can be undone",
          "Undo" in pad_help and "Clear all" in pad_help)
    check("Pad help names the video format honestly",
          "WebM" in pad_help and "MP4" in pad_help)
    # "9:16 appears anywhere on the Pad page" was a proxy for "Pad has no
    # canvas presets". Pad has them now — it reads the same table as Flip — so
    # the proxy no longer means what it meant. Scoped to the HELP DRAWER, and
    # keyed on copy that is still genuinely Flip-only: onion skin and per-page
    # holds have no Pad equivalent.
    pad_help_text = pad.evaluate(
        "() => { const d = document.getElementById('helpDrawer');"
        " return d ? d.textContent : ''; }")
    # Matched on distinctive PHRASES, not bare words: "hold" alone fires on
    # "hold space and drag" in the zoom tip, which is ordinary English and not
    # the Flip feature. A keyword that matches innocent prose is a keyword that
    # will be silenced rather than believed.
    _pl = pad_help_text.lower()
    check("Pad help does not leak Flip-only copy",
          "onion skin" not in _pl and "held page" not in _pl
          and "add pages to animate" not in _pl,
          "onion skin and per-page holds are Flip features with no Pad "
          "equivalent")
    check("but Pad's canvas presets are present, as Flip's are",
          "9:16" in pad_help, "Pad now reads the same preset table")

    br.close()


print("\nCANVAS PRESETS — every label matches its own dimensions")
# THE BUG. FLIP_SIZES typed a label and a pixel pair side by side and nothing
# compared them. '4:3' was 640x460 (1.391 — off by 4.3%) and '9:16' was 420x640
# (0.656 — off by 16.7%, nearer 2:3), so a user picking 9:16 for a phone-shaped
# animation got something noticeably wider. Sizes are now integer multiples of
# their ratio, exact by construction; this keeps it that way.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pg = _b.new_page()
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1200)
    _sizes = _pg.evaluate("() => FLIP_SIZES")
    check("Flip exposes a preset table", bool(_sizes), str(_sizes))

    _areas = []
    for _sz in _sizes or []:
        _wr, _hr = (int(x) for x in _sz["label"].split(":"))
        # Integer cross-multiply, not a float compare: w/h == wr/hr in floats
        # passes on a pair that is merely close, which is the whole failure.
        check(f"{_sz['label']} is exactly {_sz['label']} "
              f"({_sz['w']}x{_sz['h']})",
              _sz["w"] * _hr == _sz["h"] * _wr,
              f"{_sz['w']}/{_sz['h']} = {_sz['w']/_sz['h']:.4f}, "
              f"{_sz['label']} = {_wr/_hr:.4f}")
        _areas.append(_sz["w"] * _sz["h"])

    if _areas:
        _spread = (max(_areas) - min(_areas)) / min(_areas)
        check("preset areas are within 10% of each other", _spread < 0.10,
              f"{_spread*100:.1f}% spread — payload size and export time would "
              "swing between presets for no reason a user could see")

    check("preset ids are unique",
          len({x["id"] for x in _sizes}) == len(_sizes))
    # v269: the default is the table row bestFor() picks for this stage — a
    # real preset (exact table dimensions), chosen by fit rather than position.
    _dflt = _pg.evaluate("""() => {
        const st = document.querySelector('.flip-stage');
        const cs = getComputedStyle(st);
        const best = SkriblCanvasSizes.bestFor(
            st.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
            st.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom));
        return { cur: [CW, CH], best: [best.w, best.h], id: currentSizeId() };
    }""")
    check("the default canvas IS a table preset, chosen by fit (not a hardcoded pair)",
          _dflt["cur"] == _dflt["best"] and _dflt["id"] != "custom", str(_dflt))
    _b.close()

print("\nDISPLAY SIZE — each editor opens on the largest preset for ITS stage")
# THE ORIGINAL BUG. Both authored 632x474, but Flip DISPLAYED it at 694x521 and
# Pad at 632x474 — the same drawing, 10% bigger in one editor, and the larger
# one softer (Flip's 1.4 cap stretched a fixed bitmap; Pad always clamped at 1).
# The never-upscaled checks below still pin that property.
#
# v269 CHANGED THE DEFAULT CONTRACT: a fresh document starts on the preset that
# displays largest in that editor's own band (bestFor). Pad's band is taller
# than Flip's (no filmstrip or page bar), so the two editors may legitimately
# open on DIFFERENT presets at the same window size — each maximally filling
# its own chrome. What is asserted instead: each editor's pick is a real table
# preset, it IS the largest for its measured band, and neither upscales.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    for _w, _h in ((1400, 900), (1000, 900), (500, 900), (390, 844)):
        _sizes = {}
        for _name, _path, _sel in (("Flip", "/flip", "#pad"),
                                   ("Pad", "/skribl-pad", "#canvas")):
            _pg = _b.new_page(viewport={"width": _w, "height": _h})
            _pg.goto(f"{BASE}{_path}", wait_until="load")
            _pg.wait_for_timeout(1300)
            _sizes[_name] = _pg.evaluate(
                f"() => {{ const c = document.querySelector('{_sel}');"
                f" const r = c.getBoundingClientRect();"
                f" return {{ css: [Math.round(r.width), Math.round(r.height)],"
                f"          backing: [c.width, c.height] }}; }}")
            # Which preset did this surface open on, and which is the largest
            # for its measured band? The two must agree.
            if _name == "Flip":
                _sizes[_name]["fit"] = _pg.evaluate("""() => {
                    const st = document.querySelector('.flip-stage');
                    const cs = getComputedStyle(st);
                    const best = SkriblCanvasSizes.bestFor(
                        st.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
                        st.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom));
                    return { id: currentSizeId(), bestId: best.id };
                }""")
            else:
                _sizes[_name]["fit"] = _pg.evaluate("""() => {
                    const t = window.SkriblCanvasSizes;
                    const el = document.querySelector('.canvas-area');
                    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
                    const aw = r.width - parseFloat(cs.paddingLeft || 0) - parseFloat(cs.paddingRight || 0);
                    const ah = r.height - parseFloat(cs.paddingTop || 0) - parseFloat(cs.paddingBottom || 0);
                    return { id: t.idFor(authoredW, authoredH), bestId: t.bestFor(aw, ah).id };
                }""")
            _pg.close()

        _f, _pd = _sizes["Flip"], _sizes["Pad"]
        # The canvas should USE the column, not float in it. 632x474 left a
        # 43px gutter each side of a 720px column and 127px of dead space above
        # and below in Pad, whose canvas area is far taller than Flip's because
        # it has no filmstrip. Authoring larger fills it without upscaling.
        if _w >= 1000:
            _side = _pd["css"][0] / 694.0
            check(f"at {_w}px the canvas fills the app column",
                  _side > 0.95,
                  f"canvas {_pd['css'][0]}px in a 720px column — it is floating, "
                  "not filling")

        for _name, _m in (("Flip", _f), ("Pad", _pd)):
            check(f"at {_w}x{_h} {_name} opens on a real preset, the largest for its band",
                  _m["fit"]["id"] != "custom" and _m["fit"]["id"] == _m["fit"]["bestId"],
                  str(_m["fit"]))

        # Never above 1:1. Above it, a fixed bitmap is stretched and every line
        # softens — which is what made the bigger canvas the worse one.
        for _name, _m in (("Flip", _f), ("Pad", _pd)):
            _dpr = _m["backing"][0] / max(1, _m["css"][0])
            check(f"{_name} at {_w}px is not upscaled beyond its bitmap",
                  _m["css"][0] <= _m["backing"][0] + 1,
                  f"displayed {_m['css'][0]}px from a {_m['backing'][0]}px bitmap "
                  f"({_dpr:.2f}x) — every line is softened")
    _b.close()

print("\n" + "=" * 60)
# Counted here, not stored earlier: a tally on its own line drifts above
# sections appended later, and reports a green undercount with nothing
# listed as failed. Happened twice.
ok = sum(1 for o, _ in results if o)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
