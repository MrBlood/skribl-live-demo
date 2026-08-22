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
    # `.open` matters: the desktop sheet sits at opacity 0 and scale(0.96)
    # until the overlay carries it, so a sheet revealed with `hidden = false`
    # alone is present but not interactable.
    pg.evaluate("() => { const o = document.getElementById('exportOverlay');"
                " if (o) { o.hidden = false; o.classList.add('open'); }"
                " if (typeof syncExportOptions === 'function') syncExportOptions(); }")
    pg.wait_for_timeout(400)

    check("the Size and Pages block is visible",
          pg.is_visible("#exportOptions"))

    # THE BUG. .seg-slider is opacity:0 until positioned, and positioning needs
    # the button laid out. Inside a sheet that ships `hidden` that is never true
    # at init, so a one-shot call bailed and the pill stayed invisible until an
    # unrelated event re-ran it. The sheet opened with no selection shown on
    # Size or Loops — visible on a phone, where layout lands later.
    for _seg in ("exportSizeSeg", "exportLoopsSeg"):
        pill = pg.evaluate(f"""() => {{
          const g = document.getElementById('{_seg}');
          const p = g.querySelector('.seg-slider');
          const b = g.querySelector('button.on');
          if (!p || !b) return null;
          const pr = p.getBoundingClientRect(), br = b.getBoundingClientRect();
          return {{ opacity: parseFloat(getComputedStyle(p).opacity),
                   width: pr.width, btnWidth: br.width,
                   aligned: Math.abs(pr.left - br.left) < 3 }};
        }}""")
        check(f"#{_seg} shows its pill as soon as the sheet opens",
              pill and pill["opacity"] > 0.5,
              "the pill is invisible — no selection is shown until you tap one")
        check(f"#{_seg}'s pill sits on the selected button",
              pill and pill["aligned"] and abs(pill["width"] - pill["btnWidth"]) < 3,
              f"pill {pill and round(pill['width'])}px vs button "
              f"{pill and round(pill['btnWidth'])}px")

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

    # -----------------------------------------------------------------------
    print("\nEXPORT SHEET — loop count is chosen, not assumed")
    #
    # THE BUG. Both video encoders hardcoded 2 loops with nothing in the UI
    # saying so, so a 5.2s animation exported as a 10.3s MP4 while the header
    # badge still read 5.2s. The doubling is right for a 1.5s clip and wrong
    # for a 30s one, and only the person exporting knows which they made.
    #
    # Asserted against exLoopSeconds(), the shared single-pass helper, so the
    # readout and both encoders cannot disagree about a file's length.
    # The sheet had no max-height or overflow anywhere, so a window shorter
    # than its content left the bottom controls unreachable — no scroll, no
    # scrollbar, just cut off. Found when a fourth options block pushed Loops
    # out of a 900px viewport; it applied to any short window before that.
    reach = pg.evaluate("""() => {
      const sh = document.getElementById('exportSheet');
      const el = document.getElementById('exportLoopsSeg');
      const s = getComputedStyle(sh);
      return { scrolls: /auto|scroll/.test(s.overflowY),
               overflows: sh.scrollHeight > sh.clientHeight + 1,
               inside: el.getBoundingClientRect().bottom
                       <= sh.getBoundingClientRect().bottom + sh.scrollHeight };
    }""")
    check("the export sheet can scroll when its content is taller than it",
          reach["scrolls"] or not reach["overflows"],
          "content overflows a sheet with no overflow-y — the last control is "
          "unreachable on a short window")

    pg.locator("#exportLoopsSeg").scroll_into_view_if_needed()
    pg.wait_for_timeout(150)
    one_pass = pg.evaluate("() => exLoopSeconds()")
    check("a single pass has a positive duration", one_pass > 0, str(one_pass))

    for n in (1, 3, 2):
        pg.click(f"#exportLoopsSeg button[data-loops='{n}']")
        pg.wait_for_timeout(200)
        check(f"selecting {n} loops sets exLoops",
              pg.evaluate("() => exLoops") == n,
              str(pg.evaluate("() => exLoops")))
        note = pg.inner_text("#exportLoopsNote")
        # Parse the number rather than format one: JS toFixed rounds 0.25 up
        # and Python's format rounds it down, so comparing strings fails on
        # exact halves for a reason that has nothing to do with the feature.
        shown = float(re.search(r"([\d.]+)s", note).group(1))
        check(f"the readout states the resulting length at {n} loops",
              abs(shown - one_pass * n) < 0.06,
              f"{note!r} — expected about {one_pass * n:.2f}s")

    check("2 loops is the default selection",
          pg.evaluate("() => exLoops") == 2)
    check("the readout says a GIF is unaffected",
          "loop forever" in pg.inner_text("#exportLoopsNote").lower(),
          "GIF sets repeat=0 — one pass, looping forever — so Loops does not "
          "apply to it, and the sheet must not imply otherwise")

    # Changing pages must change the stated video length too, or the two
    # controls disagree about the same file.
    # The page fields bound 'change' only, so a readout lagged until the field
    # was blurred — you typed a page number and the stated length still
    # described the previous range. Typing must update it.
    before = pg.inner_text("#exportLoopsNote")
    pg.fill("#exportTo", "2")
    pg.wait_for_timeout(250)
    check("typing a page range updates the stated video length immediately",
          pg.inner_text("#exportLoopsNote") != before,
          f"still {before!r} after typing — the readout waits for blur")
    check("and the page readout follows too",
          "2 of" in pg.inner_text("#exportRangeNote"),
          pg.inner_text("#exportRangeNote"))

    b.close()

    # -----------------------------------------------------------------------
    print("\nEXPORT SHEET — section 4: anchored to the app, at any window width")
    #
    # THE BUG. `.menu-sheet` was `position: absolute; right: 18px` inside a
    # `position: fixed; inset: 0` overlay, which anchors it to the BROWSER
    # WINDOW's right edge. The app is a 720px column centred with margin auto,
    # so on a wide window every sheet detached from the app and floated in the
    # empty gutter beside it. It looked correct at ~720px and nowhere else,
    # which is why a phone-first layout never surfaced it.
    #
    # Asserted at three widths because a single viewport is exactly what missed
    # it. The column edge is the contract, not a pixel value.
    b2 = p.chromium.launch()
    for width in (760, 1280, 1900):
        w = b2.new_page(viewport={"width": width, "height": 900})
        w.goto(f"{BASE}/flip", wait_until="load")
        w.wait_for_timeout(1200)
        w.evaluate("() => { const o = document.getElementById('exportOverlay');"
                   " if (o) { o.hidden = false; o.classList.add('open'); } }")
        w.wait_for_timeout(300)

        sheet = w.locator("#exportSheet").bounding_box()
        col = w.evaluate(
            "() => { const el = document.querySelector('.flip-app') || document.body;"
            " const r = el.getBoundingClientRect();"
            " return { left: r.left, right: r.right }; }")

        check(f"at {width}px the sheet's right edge is inside the app column",
              sheet["x"] + sheet["width"] <= col["right"] + 1,
              f"sheet ends at {round(sheet['x'] + sheet['width'])}, "
              f"column ends at {round(col['right'])} — "
              f"{round(sheet['x'] + sheet['width'] - col['right'])}px adrift")
        check(f"at {width}px the sheet's left edge is inside the app column",
              sheet["x"] >= col["left"] - 1,
              f"sheet starts at {round(sheet['x'])}, column starts at {round(col['left'])}")
        w.close()
    b2.close()

summarise_and_exit()
