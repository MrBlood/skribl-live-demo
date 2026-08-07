"""The export sheet's Size and Pages controls.

THE BUG THIS REPRODUCES. `.export-opt-row`, `.export-optlbl`, `.export-num`,
`.export-dash` and `.export-rangenote` appeared in `_skribl_export.html` and had
NO rule anywhere in the tree — not in styles.css, not in flip.css. The markup
shipped and fell back to browser defaults: bare number spinners, a raw en-dash
between them, and one flex row that wrapped so the readout "62 of 62 · 640×460"
landed orphaned on a line of its own.

Nothing caught it because nothing could. The harness asserted behaviour and
source seams; a class that exists in markup and nowhere in CSS is neither. This
suite adds that check generally — every class the export sheet uses must be
defined somewhere a page actually loads — so the next unstyled control is a
failure rather than a screenshot.

It also pins the two content decisions, both of which were wrong before:

  * the output dimensions belong under SIZE, the control that changes them,
    not appended to the page-range readout
  * the readouts are sentences ("All 62 pages"), not fragments ("62 of 62 ·")
"""
import os
import re
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _layout import STATIC_DIR, template  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


print("EXPORT SHEET — section 1: every class in the markup has a rule")

with open(template("_skribl_export.html"), encoding="utf-8") as fh:
    markup = fh.read()

css = ""
for name in ("styles.css", "flip.css"):
    with open(os.path.join(STATIC_DIR, name), encoding="utf-8") as fh:
        css += fh.read()

classes = set()
for attr in re.findall(r'class="([^"{}]+)"', markup):
    classes.update(c for c in attr.split() if c)

undefined = sorted(c for c in classes if f".{c}" not in css)
check("no class in the export sheet is undefined in CSS",
      not undefined,
      "unstyled, so the browser falls back to defaults: " + ", ".join(undefined))

# The five that actually shipped unstyled, pinned by name. The sweep above would
# catch them, but naming them keeps the regression legible in the log.
for c in ("export-optlbl", "export-num", "export-dash", "export-optnote",
          "export-optblock"):
    check(f".{c} has a rule", f".{c}" in css)

check("the number inputs suppress their spinners",
      "-webkit-inner-spin-button" in css,
      "spinners steal width from a two-field row")

print("\nEXPORT SHEET — section 2: what the controls say")

check("the page separator is a word, not a bare dash",
      ">to<" in markup.replace(" ", "").replace("\n", ""),
      "an en-dash between two unlabelled number fields is not a label")
check("the scope of Size and Pages is stated",
      "export-optscope" in markup and "video and GIF" in markup,
      "PNG ignores both, and the format buttons export on click, so nothing "
      "else tells the user which formats these affect")
check("the GIF background options read as opposites",
      ">Solid<" in markup and ">Transparent<" in markup,
      "'Background color' vs 'Transparent' is a category against a value")
check("the GIF background group is labelled",
      'id="exportGifBgLbl"' in markup)
check("the data-gif-bg values are unchanged",
      'data-gif-bg="color"' in markup and 'data-gif-bg="transparent"' in markup,
      "app.js and flip.js bind on these, not on the label text")

with open(os.path.join(STATIC_DIR, "flip.js"), encoding="utf-8") as fh:
    flip_src = fh.read()
check("the dimensions readout is separate from the page readout",
      "exportDimNote" in flip_src,
      "dimensions were appended to the page range, under the wrong control")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — section 3 needs a browser")
    summarise_and_exit()

print("\nEXPORT SHEET — section 3: rendered, in a real browser")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 420, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1500)
    check("Flip loads with no JS errors", not errs, "; ".join(errs[:2]))

    # Add a couple of pages so the range readout has something to say.
    pg.evaluate("() => { if (typeof addFrame === 'function') { addFrame(); addFrame(); } }")
    pg.evaluate("() => { const o = document.getElementById('exportOverlay');"
                " if (o) o.hidden = false;"
                " if (typeof syncExportOptions === 'function') syncExportOptions(); }")
    pg.wait_for_timeout(400)

    check("the Size and Pages block is visible",
          pg.is_visible("#exportOptions"))

    dim = pg.inner_text("#exportDimNote").strip()
    rng = pg.inner_text("#exportRangeNote").strip()
    check("the dimensions readout shows a WxH", "×" in dim, repr(dim))
    check("the page readout is a sentence, not a fragment",
          "page" in rng.lower() and "·" not in rng, repr(rng))
    check("a full range reads as 'All N pages'",
          rng.lower().startswith("all"), repr(rng))

    # The layout failure was a wrapped row. Assert the two number fields share
    # one line and the readout sits BELOW them, which is what wrapping broke.
    box_from = pg.locator("#exportFrom").bounding_box()
    box_to = pg.locator("#exportTo").bounding_box()
    box_note = pg.locator("#exportRangeNote").bounding_box()
    check("both page fields sit on the same line",
          abs(box_from["y"] - box_to["y"]) < 2,
          f"{box_from['y']} vs {box_to['y']}")
    check("the page readout sits below the fields, not beside them",
          box_note["y"] > box_from["y"] + box_from["height"] - 2,
          f"note y={box_note['y']} field bottom={box_from['y'] + box_from['height']}")
    check("the two page fields are equal width",
          abs(box_from["width"] - box_to["width"]) < 2,
          f"{box_from['width']} vs {box_to['width']}")

    sheet = pg.locator("#exportSheet").bounding_box()
    check("nothing overflows the sheet horizontally",
          box_to["x"] + box_to["width"] <= sheet["x"] + sheet["width"] + 1,
          "the range row is wider than the sheet")

    # The dimensions must sit under Size, not under Pages — the whole point of
    # moving it. Assert position, not just presence.
    box_seg = pg.locator("#exportSizeSeg").bounding_box()
    box_dim = pg.locator("#exportDimNote").bounding_box()
    check("the dimensions readout sits under the Size control",
          box_dim["y"] > box_seg["y"] and box_dim["y"] < box_from["y"],
          f"dim y={box_dim['y']} size y={box_seg['y']} pages y={box_from['y']}")

    b.close()

summarise_and_exit()
