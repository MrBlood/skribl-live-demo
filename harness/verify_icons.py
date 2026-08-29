"""v239 — the tool tray's icons, measured as RENDERED rather than as authored.

THE REPORT was four words: "Fill is a weak icon." It was, and the reason was
measurable. Rendered and thresholded, Fill's ink filled 15x16 of its 24 box
where every other tool sat near 19x18 — the smallest thing in the tray — and the
bucket was a hollow diamond whose handle was a 3px stub. At tray size that reads
as a tilted square with a dot beside it.

WHAT THIS SUITE MEASURES, and why it is not the SVG source. A path's coordinates
say nothing about how much of the box the drawing occupies: stroke width, caps,
joins and fills all add ink outside the geometry, and two icons with identical
viewBoxes can differ by a third in apparent size. So each icon is rasterised
exactly as the browser paints it and the INK BOUNDING BOX is measured off the
alpha channel. That is the number a person's eye is actually responding to when
they say an icon looks weak.

WHAT IT DELIBERATELY DOES NOT ASSERT: ink COVERAGE, the share of the box that is
painted. It was measured throughout and it is a bad proxy for visual weight,
which the work proved twice. Stamps was 'fixed' from 24.3% to 19.7% coverage and
came out visibly worse, because the weight had been moved out of a solid base
bar that was holding the icon together. Two icons at the same coverage look
nothing alike when one is a thin outline over a wide area and the other is a
small solid mass. EXTENT correlated with the complaint; coverage did not.

THE LIQUIFY EXEMPTION IS THE MOST IMPORTANT THING IN THIS FILE. Liquify is the
flattest icon here by a wide margin — 13.5 tall against a ~18 norm — and that is
CORRECT. It is a smear, and a smear is wide and low. It was redrawn once to fill
the box's height, the number improved, and the result read as a caret with a
detached curl. The band below exempts it BY NAME so that the next person to run
this suite finds the reasoning instead of a failing assertion inviting them to
repeat the mistake.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                    # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# The band, in viewBox units of the 24x24 box. Derived from the icons that were
# never in question — Pen 19.3, Shape 19, Artwork 18.5, Select 18 — not invented.
MIN_W, MAX_W = 17.5, 22.5
MIN_H, MAX_H = 17.0, 21.0
CENTRE_TOL = 2.0

# Icons excused from ONE axis floor, with the reason, because a shape that is
# legitimately not square is not a defect. An exemption without a sentence is how
# a band quietly stops meaning anything, so the values are the reasoning and they
# print in the assertion's detail.
#
# BOTH ENTRIES EXIST BECAUSE THE BAND WAS WRONG ABOUT THEM, not because the icons
# were. It was derived from ten roughly square glyphs and then met two that are
# honestly not square in opposite directions.
FLAT_BY_DESIGN = {
    "Liquify": "a smear is wide and low; the tall redraw read as a caret",
}
NARROW_BY_DESIGN = {
    "Stamps": "a rubber stamp is tall and narrow; Lucide's is 18:22 and no "
              "uniform scale satisfies both the width floor and the height ceiling",
}
# THE FLOOR THAT SURVIVES BOTH EXEMPTIONS, and it is a BACKSTOP rather than the
# primary guard — the per-axis floors above do the real work. Its only job is to
# stop an axis exemption becoming a blank cheque: a glyph excused on one axis
# still has to occupy a comparable amount of the box.
#
# The margin is honestly thin and the number is stated rather than rounded to
# something that looks tidier. Liquify, legitimately flat, is 20.0x13.5 = 270 and
# is the smallest thing here that has to pass. The Fill that started all this was
# 15.0x16.3 = 245. There is not much room between those, which is exactly why
# this is the backstop and not the guard — that Fill also failed BOTH per-axis
# floors, and would have been caught with this line deleted.
MIN_AREA = 260

MEASURE = """async () => {
  const out = [];
  for (const c of document.querySelectorAll('#toolTray .tool-tray-btn')) {
    const svg = c.querySelector('svg');
    if (!svg) continue;
    const clone = svg.cloneNode(true);
    clone.setAttribute('width', '96'); clone.setAttribute('height', '96');
    const src = new XMLSerializer().serializeToString(clone).replace(/currentColor/g, '#fff');
    const img = new Image();
    await new Promise(r => { img.onload = r; img.onerror = r;
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(src); });
    const cv = document.createElement('canvas'); cv.width = 96; cv.height = 96;
    const g = cv.getContext('2d'); g.drawImage(img, 0, 0, 96, 96);
    const d = g.getImageData(0, 0, 96, 96).data;
    let x0 = 96, y0 = 96, x1 = -1, y1 = -1, sum = 0;
    for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) {
      const a = d[(y * 96 + x) * 4 + 3];
      // A threshold, not `> 0`: anti-aliasing puts a faint halo a pixel or two
      // beyond every edge, and counting it inflates every measurement equally
      // — which hides exactly the differences this is here to find.
      if (a > 10) { sum += a;
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
    out.push({ tool: c.getAttribute('data-tool'),
               label: c.querySelector('span').textContent,
               w: (x1 - x0 + 1) / 4, h: (y1 - y0 + 1) / 4,
               cx: ((x0 + x1) / 2) / 4, cy: ((y0 + y1) / 2) / 4,
               cov: (sum / 255) / 9216 * 100 });
  }
  return out;
}"""

with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(800)
        page.evaluate("() => SkriblFlipTools.buildTray()")
        page.wait_for_timeout(300)
        icons = page.evaluate(MEASURE)

        print("\nEVERY REGISTERED TOOL IS IN THE TRAY AND HAS A GLYPH")
        roster = page.evaluate("() => SkriblFlipTools.list()")
        check("every tool in the registry drew an icon",
              [i["tool"] for i in icons] == roster,
              f"{[i['tool'] for i in icons]} vs {roster} — a tool whose glyph "
              "fails to render leaves a cell with a label and nothing above it")

        print("\nINK EXTENT — the number the eye is responding to")
        for i in icons:
            flat = i["label"] in FLAT_BY_DESIGN
            narrow = i["label"] in NARROW_BY_DESIGN
            okw = (i["w"] <= MAX_W) if narrow else (MIN_W <= i["w"] <= MAX_W)
            okh = (i["h"] <= MAX_H) if flat else (MIN_H <= i["h"] <= MAX_H)
            note = ""
            if flat:   note = f"  [flat by design: {FLAT_BY_DESIGN[i['label']]}]"
            if narrow: note = f"  [narrow by design: {NARROW_BY_DESIGN[i['label']]}]"
            check(f"{i['label']}: fills its box like the rest of the set",
                  okw and okh,
                  f"ink {i['w']:.1f}x{i['h']:.1f} against w {MIN_W}-{MAX_W}, "
                  f"h {MIN_H}-{MAX_H}{note} — Fill shipped at 15.0x16.3 and was "
                  "reported as weak; that is the size this floor exists to catch")
        # Applies to EVERY icon, exempt or not.
        for i in icons:
            check(f"{i['label']}: occupies enough of the box however it is shaped",
                  i["w"] * i["h"] >= MIN_AREA,
                  f"area {i['w'] * i['h']:.0f} against a floor of {MIN_AREA} — no "
                  "axis exemption excuses an icon from being big enough overall")

        print("\nOPTICALLY CENTRED — an icon adrift reads as the wrong size")
        for i in icons:
            flat = i["label"] in FLAT_BY_DESIGN
            oky = True if flat else abs(i["cy"] - 12) <= CENTRE_TOL + 0.6
            check(f"{i['label']}: sits in the middle of its cell",
                  abs(i["cx"] - 12) <= CENTRE_TOL and oky,
                  f"centre {i['cx']:.1f},{i['cy']:.1f} — a glyph pushed to one "
                  "side of a labelled cell reads as smaller than it is")

        # THE ONE THAT NAMES THE ORIGINAL REPORT. Kept separate from the band so
        # that relaxing the band later cannot quietly re-admit the exact icon
        # that prompted all of this.
        fill = next((i for i in icons if i["tool"] == "fill"), None)
        check("Fill is not the smallest icon in the tray any more",
              fill is not None and fill["w"] >= 18.5 and fill["h"] >= 18.0,
              f"{fill['w']:.1f}x{fill['h']:.1f} — it shipped at 15.0x16.3, the "
              "smallest here, as a hollow diamond with a 3px stub for a handle")
        # Over the icons the band applies to. Including a flat-by-design icon
        # here would fail on Liquify's area every time — which is the same
        # pressure to "fix" it that the exemption exists to remove, arriving
        # through a different assertion.
        judged = [i for i in icons
                  if i["label"] not in FLAT_BY_DESIGN
                  and i["label"] not in NARROW_BY_DESIGN]
        smallest = min(judged, key=lambda i: i["w"] * i["h"])
        check("...and nothing else has taken its place",
              smallest["w"] * smallest["h"] >= MIN_W * MIN_H,
              f"{smallest['label']} at {smallest['w']:.1f}x{smallest['h']:.1f} "
              f"is now the smallest icon the band judges")

        print("\nCOVERAGE IS REPORTED, NOT ASSERTED — see the note at the top")
        cov = ", ".join(f"{i['label']} {i['cov']:.1f}%" for i in icons)
        check("the spread is recorded so a future change can be compared",
              True, cov)

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
