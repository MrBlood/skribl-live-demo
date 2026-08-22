"""v109 — drag-to-reorder, and per-page hold (the first payload-format change).

`hold` is the first new payload field since the frame format itself, so the whole
suite is built around one rule: **it must be additive in both directions.**

  - A page with no `hold` reads as 1, so every Skribl posted before v109 plays
    exactly as it always did.
  - `hold` is written ONLY when it is greater than 1, so an animation with no
    holds serialises to the same bytes as before — asserted below by comparing a
    real payload against the pre-v109 shape.
  - A v109 payload opened by an older player degrades to uniform timing rather
    than breaking, because an unknown field is simply ignored.

Timing is verified off the GIF byte stream: per-frame delays are readable there,
which makes the exported file the oracle for what "hold" actually means. A state
check would prove nothing about the encoders.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def gif_delays(b):
    """Per-frame delay (centiseconds) in order, straight out of the file."""
    flags = b[10]
    pos = 13
    if flags & 0x80:
        pos += 3 * 2 ** ((flags & 7) + 1)
    delays, pending = [], None
    while pos < len(b):
        blk = b[pos]
        if blk == 0x21:
            label = b[pos + 1]
            pos += 2
            size = b[pos]
            data = b[pos + 1:pos + 1 + size]
            pos += 1 + size
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
            if label == 0xF9:
                pending = data[1] | (data[2] << 8)
        elif blk == 0x2C:
            lf = b[pos + 9]
            pos += 10
            if lf & 0x80:
                pos += 3 * 2 ** ((lf & 7) + 1)
            pos += 1
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
            delays.append(pending)
            pending = None
        else:
            break
    return delays


def draw(pg, x0, n=10):
    b = pg.locator("#pad").bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + 90)
    pg.mouse.down()
    for i in range(n):
        pg.mouse.move(b["x"] + x0 + i * 7, b["y"] + 95)
    pg.mouse.up()
    pg.wait_for_timeout(80)


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(900)
    for i in range(3):
        pg.evaluate("() => addFrame()")
        draw(pg, 70 + i * 25, 8 + i * 5)
    total = pg.evaluate("() => frames.length")

    print("\nDRAG-TO-REORDER")
    before = pg.evaluate("() => frames.map(f => f.strokes.length)")
    tiles = pg.locator("#strip .frame")
    src = tiles.nth(total - 1).bounding_box()
    dst = tiles.nth(1).bounding_box()
    pg.mouse.move(src["x"] + src["width"] / 2, src["y"] + src["height"] / 2)
    pg.mouse.down()
    for k in range(12):
        pg.mouse.move(src["x"] + src["width"] / 2 + (dst["x"] - src["x"]) * (k + 1) / 12,
                      src["y"] + src["height"] / 2)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    after = pg.evaluate("() => frames.map(f => f.strokes.length)")
    check("dragging the last page onto slot 2 moves it there",
          after[1] == before[-1] and len(after) == len(before), f"{before} -> {after}")
    check("the dragged page stays selected", pg.evaluate("() => idx") == 1,
          f"idx={pg.evaluate('() => idx')}")
    order = pg.evaluate("() => frames.map(f => f.strokes.length)")
    tiles.nth(2).click()
    pg.wait_for_timeout(250)
    check("a plain tap still selects instead of reordering",
          pg.evaluate("() => frames.map(f => f.strokes.length)") == order
          and pg.evaluate("() => idx") == 2)

    print("\nHOLD — defaults and clamping (read defensively, never trusted)")
    check("a page with no hold field reads as 1",
          pg.evaluate("() => frameHold({strokes:[],strokeGroups:[]})") == 1)
    check("hold 0 clamps up to 1", pg.evaluate("() => frameHold({hold:0})") == 1)
    check("a negative hold clamps to 1", pg.evaluate("() => frameHold({hold:-3})") == 1)
    check("garbage clamps to 1", pg.evaluate("() => frameHold({hold:'banana'})") == 1)
    check("an absurd hold clamps down to MAX_HOLD",
          pg.evaluate("() => frameHold({hold:999})") == pg.evaluate("() => MAX_HOLD"))
    check("null frame is safe", pg.evaluate("() => frameHold(null)") == 1)

    print("\nHOLD — the UI cycles and shows it")
    pg.evaluate("() => { go(0); }")
    pg.wait_for_timeout(200)
    seq = []
    for _ in range(5):
        pg.click("#pbHold")          # v124: hold moved to the page toolbar
        pg.wait_for_timeout(180)
        seq.append(pg.evaluate("() => frameHold(frames[0])"))
    check("the toolbar Hold button cycles 2,3,4 then wraps to 1", seq == [2, 3, 4, 1, 2], str(seq))
    check("a held page shows a badge without hovering",
          pg.evaluate("() => !!strip.children[0].querySelector('.holdbadge')"))
    pg.evaluate("() => { frames[0].hold = 1; buildStrip(); }")
    pg.wait_for_timeout(150)
    check("no badge at the default hold",
          pg.evaluate("() => !strip.children[0].querySelector('.holdbadge')"))

    print("\nPAYLOAD — additive in both directions")
    plain = pg.evaluate("() => JSON.stringify(serializeFlip({media:false}))")
    check("with no holds, the payload contains no 'hold' key at all",
          '"hold"' not in plain, "hold present" if '"hold"' in plain else "clean")
    pg.evaluate("() => { frames[1].hold = 3; buildStrip(); }")
    pg.wait_for_timeout(150)
    held = pg.evaluate("() => JSON.parse(JSON.stringify(serializeFlip({media:false}))).frames.map(f => f.hold)")
    check("a held page writes hold, the others stay absent",
          held[1] == 3 and held[0] is None and held[2] is None, str(held))
    check("frame shape is otherwise unchanged",
          pg.evaluate("""() => { const f=serializeFlip({media:false}).frames[0];
              return ['strokes','strokeGroups','background'].every(k => k in f); }"""))
    check("copy/paste carries the hold with the page",
          pg.evaluate("() => { const c = deepCopy(frames[1]); return frameHold(c); }") == 3)

    print("\nTIMING — read out of the exported GIF, not off the state")
    fps = pg.evaluate("() => fps")
    base_cs = round(round(1000 / fps) / 10)
    pg.evaluate("() => { frames.forEach(f => f.hold = 1); frames[1].hold = 3; buildStrip(); }")
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(400)
    with pg.expect_download(timeout=60000) as dl:
        pg.click("#exportGif")
    delays = gif_delays(open(dl.value.path(), "rb").read())
    check("one delay per page", len(delays) == total, f"{len(delays)} vs {total}")
    check("the held page lasts 3x the others",
          delays[1] == base_cs * 3 and delays[0] == base_cs,
          f"{delays} (base {base_cs}cs)")
    check("total GIF duration grows by exactly the extra holds",
          sum(delays) == base_cs * (total + 2), f"sum {sum(delays)}cs")

    print("\nPLAYER — a held Skribl plays; a pre-v109 one is untouched")
    # Posted through the API rather than the UI so the check is deterministic and
    # doesn't depend on the share flow's timing.
    def post(frames_payload):
        r = ctx.request.post(BASE + "/api/skribls", data={
            "title": "hold harness", "playbackMode": "flip", "fps": 12,
            "canvasSize": {"cssWidth": 640, "cssHeight": 460, "dpr": 1},
            "frames": frames_payload})
        return r.json().get("id")

    stroke = [{"x": 40, "y": 40}, {"x": 200, "y": 120}]
    held_id = post([{"strokes": stroke, "strokeGroups": [2]},
                    {"strokes": stroke, "strokeGroups": [2], "hold": 3},
                    {"strokes": stroke, "strokeGroups": [2]}])
    old_id = post([{"strokes": stroke, "strokeGroups": [2]},
                   {"strokes": stroke, "strokeGroups": [2]},
                   {"strokes": stroke, "strokeGroups": [2]}])
    check("a payload carrying hold is accepted by the API", bool(held_id), str(held_id))
    check("a pre-v109 payload (no hold anywhere) is still accepted", bool(old_id), str(old_id))

    for label, pid in (("held", held_id), ("pre-v109", old_id)):
        player = ctx.new_page()
        perrs = []
        player.on("pageerror", lambda e, _p=perrs: _p.append(str(e)))
        player.goto(f"{BASE}/s/{pid}", wait_until="load")
        player.wait_for_timeout(1800)
        check(f"the {label} Skribl loads in the player with no errors",
              not perrs, "; ".join(perrs[:2]))
        check(f"the {label} Skribl renders its frames",
              player.evaluate("() => !!document.getElementById('canvas')"))
        player.close()

    check("no Flip page errors across the whole feature", not errs, "; ".join(errs[:2]))

    br.close()

print("\nPAGE BAR — the icon-only bar still says what each button does")
# Below 560px every .pb-tx label is hidden, which left "×1" bare and left Move
# as two unlabelled arrows in a bar that also reads "Page 10 / 12" — so they
# looked like page navigation while actually reordering the animation. Checked
# at a PHONE viewport, because at 1280px the labels are present and every
# assertion below would pass for the wrong reason.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _errs = []
    _pg.on("pageerror", lambda e: _errs.append(str(e)))
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
    _pg.evaluate("() => { addFrame(false); addFrame(false); }")
    _pg.wait_for_timeout(400)

    check("labels really are hidden at phone width",
          _pg.evaluate("() => getComputedStyle("
                       "document.querySelector('#pbHold .pb-tx')).display") == "none",
          "this section proves nothing if the labels are visible")

    check("#pbHold carries a repeat glyph when its label is hidden",
          _pg.evaluate("() => !!document.querySelector('#pbHold .pb-glyph svg')"),
          "a bare count is not self-explanatory")
    check("#pbHold's glyph is actually rendered",
          _pg.evaluate("() => { const g = document.querySelector('#pbHold .pb-glyph');"
                       " return g && g.offsetParent !== null"
                       " && g.getBoundingClientRect().width > 4; }"),
          "present in markup but not laid out")

    # The Move buttons carry ONLY an arrow. A page RECTANGLE was once added
    # beside the arrow and reverted — at 11px a tiny rect renders as a zero, so
    # the buttons read "◀ 0". v207 replaced the ◀/▶ TEXT arrows with SVG
    # chevrons (so the page bar is uniformly SVG, no mixed text/SVG glyphs);
    # the chevron IS the arrow, not an extra glyph. Pin the real concern: no
    # <rect> in the Move glyph, and the arrow is a single chevron path.
    for _id in ("pbLeft", "pbRight"):
        _g = _pg.evaluate(f"""() => {{ const g = document.querySelector('#{_id} .pb-glyph svg'); if (!g) return null;
            return {{ rects: g.querySelectorAll('rect').length, paths: g.querySelectorAll('path').length }}; }}""")
        check(f"#{_id} glyph is a chevron arrow, not a page rectangle that reads as a zero",
              _g is not None and _g["rects"] == 0 and _g["paths"] == 1,
              f"{_g} — a <rect> here renders as a 0 at this size")
        check(f"#{_id} still names its action for assistive tech",
              "move" in (_pg.get_attribute(f"#{_id}", "aria-label") or "").lower(),
              _pg.get_attribute(f"#{_id}", "aria-label"))

    # flip.js rewrites .pb-ic's textContent on every render. A glyph placed
    # inside it would survive the first paint and vanish on the first page
    # change — which is exactly the kind of bug a single-state check misses.
    _pg.click("#pbHold")
    _pg.wait_for_timeout(250)
    # pbLeft, not pbRight: two addFrame() calls leave idx on the LAST page, so
    # "move right" is correctly disabled there and Playwright waits forever.
    _pg.click("#pbLeft")
    _pg.wait_for_timeout(250)
    _pg.evaluate("() => { idx = 0; buildStrip(); render(); }")
    _pg.wait_for_timeout(300)
    check("the repeat glyph survives re-renders and page changes",
          _pg.evaluate("() => !!document.querySelector('#pbHold .pb-glyph svg')"),
          "a glyph inside .pb-ic is wiped when flip.js rewrites its textContent")

    check("the hold count still reads as a multiplier",
          "\u00d7" in _pg.inner_text("#pbHold"), _pg.inner_text("#pbHold"))
    check("aria-label still names the action for screen readers",
          "move" in (_pg.get_attribute("#pbLeft", "aria-label") or "").lower(),
          _pg.get_attribute("#pbLeft", "aria-label"))
    check("no JS errors at phone width", not _errs, "; ".join(_errs[:2]))
    _b.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
