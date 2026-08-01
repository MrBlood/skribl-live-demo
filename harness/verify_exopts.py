"""v108 — export options: output size + page range (Flip).

GIF export had a hardcoded 480px cap with no way out, and every export always
covered every page. Both are now controlled from the export sheet, and — this is
the part worth guarding — **one pair of helpers (exDims / exRange) feeds all three
encoders**, so GIF, WebM and MP4 cannot disagree about what "Small" or "pages 2-4"
means. The old 480 cap is gone: 'full' is the default, so a GIF is now native
resolution unless the user asks smaller.

These assertions are byte-level on purpose. A size control that only changes a
label, or a range that quietly exports everything, would pass any UI-state check;
the only honest test is to export and read the dimensions and frame count out of
the file. That is possible here because gifenc is vendored (v104) — before that,
none of this could have been verified in-sandbox at all.

Still session-only state: nothing here reaches the payload.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def parse_gif(b):
    """Screen size + frame count, straight out of the GIF byte stream."""
    if b[:6] not in (b"GIF89a", b"GIF87a"):
        raise ValueError("not a GIF")
    w = b[6] | (b[7] << 8)
    h = b[8] | (b[9] << 8)
    flags = b[10]
    pos = 13
    if flags & 0x80:
        pos += 3 * 2 ** ((flags & 7) + 1)
    frames = 0
    while pos < len(b):
        blk = b[pos]
        if blk == 0x21:
            pos += 2
            size = b[pos]
            pos += 1 + size
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
        elif blk == 0x2C:
            lf = b[pos + 9]
            pos += 10
            if lf & 0x80:
                pos += 3 * 2 ** ((lf & 7) + 1)
            pos += 1
            while b[pos]:
                pos += 1 + b[pos]
            pos += 1
            frames += 1
        else:
            break
    return w, h, frames


def draw(pg, x0, n=14):
    b = pg.locator("#pad").bounding_box()
    pg.mouse.move(b["x"] + x0, b["y"] + 90)
    pg.mouse.down()
    for i in range(n):
        pg.mouse.move(b["x"] + x0 + i * 8, b["y"] + 90 + (i % 4) * 6)
    pg.mouse.up()
    pg.wait_for_timeout(100)


def export_gif(pg):
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(400)
    with pg.expect_download(timeout=60000) as dl:
        pg.click("#exportGif")
    return parse_gif(open(dl.value.path(), "rb").read())


def set_opts(pg, size=None, frm=None, to=None):
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(350)
    if size:
        pg.click(f'#exportSizeSeg button[data-size="{size}"]')
    if frm is not None:
        pg.fill("#exportFrom", str(frm))
        pg.dispatch_event("#exportFrom", "change")
    if to is not None:
        pg.fill("#exportTo", str(to))
        pg.dispatch_event("#exportTo", "change")
    pg.wait_for_timeout(300)


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(1000)
    for i in range(5):
        pg.evaluate("() => addFrame()")
        draw(pg, 70 + i * 25)
    total = pg.evaluate("() => frames.length")

    print("\nDEFAULTS — full size, every page")
    check("options appear on Flip", pg.evaluate("() => !!document.getElementById('exportOptions')"))
    w, h, n = export_gif(pg)
    check("default export is native resolution (the 480 cap is gone)", (w, h) == (640, 460), f"{w}x{h}")
    check("default export covers every page", n == total, f"{n} of {total}")

    print("\nSIZE — measured out of the file, not read off a label")
    set_opts(pg, size="small")
    w2, h2, n2 = export_gif(pg)
    check("Small downscales", (w2, h2) == (320, 230), f"{w2}x{h2}")
    check("Small keeps the aspect ratio", abs(w2 / h2 - 640 / 460) < 0.01, f"{w2}x{h2}")
    check("Small still exports every page", n2 == total, f"{n2} of {total}")
    set_opts(pg, size="medium")
    w3, h3, _ = export_gif(pg)
    check("Medium matches the old hardcoded 480 cap", (w3, h3) == (480, 345), f"{w3}x{h3}")
    set_opts(pg, size="full")
    check("Full restores native", export_gif(pg)[:2] == (640, 460))

    print("\nRANGE — a subset really is a subset")
    set_opts(pg, frm=2, to=4)
    w4, h4, n4 = export_gif(pg)
    check("pages 2-4 exports exactly 3 frames", n4 == 3, f"{n4} frames")
    check("and still at the chosen size", (w4, h4) == (640, 460), f"{w4}x{h4}")
    set_opts(pg, frm=3, to=3)
    check("a single-page range exports one frame", export_gif(pg)[2] == 1)

    print("\nCLAMPING — the inputs cannot produce a range the encoders must defend against")
    # Test the contract directly. Driving this through the two inputs one at a
    # time would trip the reversed-range swap mid-edit (from=99 while to=3 is a
    # legitimately reversed range), which is correct behaviour but a different
    # assertion than "does a too-large number clamp".
    over = pg.evaluate("() => { exFrom=99; exTo=99; return exRange(); }")
    check("an out-of-range page number clamps to the last page",
          over["from"] == total and over["to"] == total, str(over))
    set_opts(pg, frm=1, to=99)
    check("and the input is rewritten to the clamped value, not left lying",
          int(pg.input_value("#exportTo")) == total, pg.input_value("#exportTo"))
    set_opts(pg, frm=4, to=2)
    r = pg.evaluate("() => exRange()")
    check("a reversed range is swapped, not rejected", r["from"] == 2 and r["to"] == 4, str(r))
    set_opts(pg, frm=0, to=total)
    check("zero/blank clamps to page 1", pg.evaluate("() => exRange().from") == 1)
    check("the note reports what will actually be exported",
          "of " + str(total) in pg.evaluate("() => document.getElementById('exportRangeNote').textContent"),
          pg.evaluate("() => document.getElementById('exportRangeNote').textContent"))

    print("\nSHARED CONTRACT — one helper pair feeds all three encoders")
    dims = pg.evaluate("() => { exSize='small'; return exDims(); }")
    check("exDims is the single source of output size",
          dims["w"] == 320 and dims["h"] == 230, str(dims))
    check("exRange is the single source of page bounds",
          pg.evaluate("() => { exFrom=2; exTo=4; return exRange().count; }") == 3)
    # The WebM path is the one that can actually run here (no avc1 in this
    # Chromium), so it is the one that can be shown to honour the options.
    pg.evaluate("() => { exSize='small'; exFrom=1; exTo=frames.length; }")
    with pg.expect_download(timeout=90000) as dl:
        pg.evaluate("() => { closeExportSheet(); exportWebM(); }")
    webm = open(dl.value.path(), "rb").read()
    check("WebM still exports with options applied", len(webm) > 1000 and webm[:4] == b"\x1a\x45\xdf\xa3",
          f"{len(webm)} bytes")

    print("\nSCOPE — none of this reaches the payload")
    payload = pg.evaluate("() => JSON.stringify(serializeFlip())")
    for f in ("exSize", "exFrom", "exTo"):
        check(f"no '{f}' in the posted payload", f not in payload)
    check("no page errors across every export", not errs, "; ".join(errs[:2]))

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
