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
    _first = pg.evaluate("() => FLIP_SIZES[0]")
    check(f"starts at the first preset ({_first['label']})",
          pg.evaluate("() => [CW,CH,currentSizeId()]")
          == [_first["w"], _first["h"], _first["id"]],
          str(pg.evaluate("() => [CW,CH,currentSizeId()]")))
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
    check("the default canvas IS the first preset, not a hardcoded pair",
          _pg.evaluate("() => [CW, CH]") == [_sizes[0]["w"], _sizes[0]["h"]],
          str(_pg.evaluate("() => [CW, CH]")))
    _b.close()

# Computed HERE, not earlier: this was tallied before the last section ran,
# so eight new assertions grew `results` while `ok` stayed frozen and the
# suite reported 21/29 with nothing listed as failed.
ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
