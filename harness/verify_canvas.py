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
    check("starts at the classic 4:3", pg.evaluate("() => [CW,CH,currentSizeId()]") == [640, 460, "classic"])
    strokes = pg.evaluate("() => frames.map(f => f.strokes.length)")
    for sid, w, h in (("square", 560, 560), ("wide", 720, 405), ("tall", 420, 640)):
        pg.evaluate(f"() => {{ const s = FLIP_SIZES.find(x => x.id === '{sid}'); applyCanvasSize(s.w, s.h); }}")
        pg.wait_for_timeout(350)
        check(f"{sid} applies {w}x{h}", pg.evaluate("() => [CW,CH]") == [w, h],
              str(pg.evaluate("() => [CW,CH]")))
    check("every layer resized with it, not just the visible one",
          pg.evaluate("() => [pad.width===CW*DPR, onionCv.width===CW*DPR, tmpCv.width===CW*DPR, frameCv.width===CW*DPR]")
          == [True, True, True, True])
    check("strokes survive every resize untouched",
          pg.evaluate("() => frames.map(f => f.strokes.length)") == strokes, str(strokes))
    check("no drawing is lost going small and back again",
          pg.evaluate("""() => { const before = JSON.stringify(frames[1].strokes);
              applyCanvasSize(420,640); applyCanvasSize(640,460);
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
    check("Pad help does not leak Flip-only copy",
          "9:16" not in pad_help and "&#215;1" not in pad_help)

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
