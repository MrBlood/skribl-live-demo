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


# THE BAND, in viewBox units of the 24x24 box.
#
# THIS IS THE SECOND VERSION OF THIS RULE, and the first one is worth knowing
# about because it was wrong in an instructive way. It was a per-AXIS band --
# width in 17.5-22.5, height in 17.0-21.0 -- derived from ten roughly square
# glyphs. Then three icons in a row turned out to be legitimately non-square and
# each needed a named exemption to pass:
#
#   Liquify  20.0 x 13.5   a warp is wide and low
#   Stamps   16.5 x 20.0   a rubber stamp is tall and narrow
#   Fill     16.0 x 21.5   a drop is a point over a round body
#
# Two exemptions were already flagged in DECISIONS v292 as the shape of a guard
# being dismantled. The third one is the answer: the per-axis floors were never
# the rule, they were a PROXY for it. What the band actually means is "occupies a
# comparable amount of the box to everything else", and none of those three is
# out of line on that -- their areas are 270, 330 and 344 against a set running
# 324 to 429.
#
# So the rule now says what it means. Area does the work, both ways; the per-axis
# limits are reduced to what they can honestly police, which is collapse in one
# dimension and overflow of the box. All three exemptions are GONE, and a rule
# that needs no special cases is a better rule than one carrying two.
MIN_AREA, MAX_AREA = 260, 450
# Collapse and overflow only. An icon may be any proportion between these.
MIN_AXIS, MAX_AXIS = 13.0, 22.5
CENTRE_TOL = 2.0

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

        print("\nHOW MUCH OF THE BOX IT OCCUPIES — the number the eye responds to")
        for i in icons:
            area = i["w"] * i["h"]
            check(f"{i['label']}: occupies its box like the rest of the set",
                  MIN_AREA <= area <= MAX_AREA,
                  f"ink {i['w']:.1f}x{i['h']:.1f}, area {area:.0f} against "
                  f"{MIN_AREA}-{MAX_AREA} — Fill shipped at 15.0x16.3 (245) and was "
                  "reported as weak; raw unscaled Lucide lands at 488 and reads "
                  "15% larger than its neighbours. Both ends are real")

        print("\nAND IS NOT COLLAPSED OR SPILLING OUT OF IT")
        for i in icons:
            check(f"{i['label']}: neither collapsed nor overflowing",
                  MIN_AXIS <= i["w"] <= MAX_AXIS and MIN_AXIS <= i["h"] <= MAX_AXIS,
                  f"{i['w']:.1f}x{i['h']:.1f} against {MIN_AXIS}-{MAX_AXIS} per axis "
                  "— area alone would pass a 13x22 splinter, and nothing may run "
                  "past the edge of a 24 box")

        print("\nOPTICALLY CENTRED — an icon adrift reads as the wrong size")
        for i in icons:
            check(f"{i['label']}: sits in the middle of its cell",
                  abs(i["cx"] - 12) <= CENTRE_TOL and abs(i["cy"] - 12) <= CENTRE_TOL + 0.6,
                  f"centre {i['cx']:.1f},{i['cy']:.1f} — a glyph pushed to one "
                  "side of a labelled cell reads as smaller than it is")

        # THE ONE THAT NAMES THE ORIGINAL REPORT. Kept separate from the band so
        # that relaxing the band later cannot quietly re-admit the exact icon
        # that prompted all of this.
        fill = next((i for i in icons if i["tool"] == "fill"), None)
        check("Fill is not the smallest icon in the tray any more",
              fill is not None and fill["w"] * fill["h"] >= MIN_AREA,
              f"{fill['w']:.1f}x{fill['h']:.1f} = {fill['w'] * fill['h']:.0f} — it "
              "shipped at 15.0x16.3 (245), the smallest here, as a hollow diamond "
              "with a 3px stub for a handle")
        smallest = min(icons, key=lambda i: i["w"] * i["h"])
        check("...and nothing else has taken its place",
              smallest["w"] * smallest["h"] >= MIN_AREA,
              f"{smallest['label']} at {smallest['w']:.1f}x{smallest['h']:.1f} "
              f"= {smallest['w'] * smallest['h']:.0f} is now the smallest here")

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
