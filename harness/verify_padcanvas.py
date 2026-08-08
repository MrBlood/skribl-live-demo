"""Pad's canvas size, and the table both editors share.

THE BUG. Pad had no canvas control at all. `resizeCanvas()` called
`establishEditorCanvas(area.width, area.height)` once, from whatever the
available area happened to be on first load — so a drawing's shape depended on
how wide the browser window was. Two people drawing the same thing got
different aspect ratios; the same person got different ones on phone and
desktop; and none of it was anything a user chose. For a feed, where every card
would be a different shape, that is unworkable.

Flip has had presets since v110. Copying its table into app.js would have made
a second copy of a list that has already drifted from its own labels once, so
the table moved to lib/canvassizes.js and both surfaces read it.

WHAT PAD DOES DIFFERENTLY, and why this is not Flip's handler copied across:
Pad records stroke TIMING, and a take is a continuous performance. Flip resizes
freely because its pages are independent and coordinates are simply kept. Pad
resizing mid-take would change the space a replay is drawn into halfway through
the recording it replays. So the canvas is free while empty and locked once
there is content — refused with an explanation rather than silently ignored,
and never by destroying the recording.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — this suite needs a browser")
    summarise_and_exit()

with sync_playwright() as p:
    b = p.chromium.launch()

    # -----------------------------------------------------------------------
    print("PAD CANVAS — the shape no longer depends on the window")
    #
    # The old behaviour reproduced directly: two viewports, two shapes. This is
    # the assertion that would have caught it, and it needs two page loads at
    # different sizes — a single-viewport suite structurally cannot see it.
    shapes = []
    for w, h in ((1280, 900), (520, 900)):
        pg = b.new_page(viewport={"width": w, "height": h})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{BASE}/skribl-pad", wait_until="load")
        pg.wait_for_timeout(1400)
        check(f"Pad loads at {w}px with no JS errors", not errs, "; ".join(errs[:2]))
        shapes.append(tuple(pg.evaluate("() => [authoredW, authoredH]")))
        pg.close()

    check("the authored canvas is identical at both window widths",
          shapes[0] == shapes[1],
          f"{shapes[0]} at 1280px vs {shapes[1]} at 520px — the canvas is "
          "still inherited from the viewport")

    # -----------------------------------------------------------------------
    print("\nPAD CANVAS — one table, shared with Flip")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    perrs = []
    pg.on("pageerror", lambda e: perrs.append(str(e)))
    pg.goto(f"{BASE}/skribl-pad", wait_until="load")
    pg.wait_for_timeout(1400)

    check("the shared table is published on Pad",
          pg.evaluate("() => !!window.SkriblCanvasSizes"),
          "lib/canvassizes.js did not load")

    fp = b.new_page()
    fp.goto(f"{BASE}/flip", wait_until="load")
    fp.wait_for_timeout(1200)
    pad_sizes = pg.evaluate("() => window.SkriblCanvasSizes.SIZES")
    flip_sizes = fp.evaluate("() => FLIP_SIZES")
    check("Pad and Flip read the SAME preset list", pad_sizes == flip_sizes,
          f"{pad_sizes} vs {flip_sizes}")
    fp.close()

    check("Pad's default canvas is the first preset, not the viewport",
          tuple(pg.evaluate("() => [authoredW, authoredH]"))
          == (pad_sizes[0]["w"], pad_sizes[0]["h"]),
          str(pg.evaluate("() => [authoredW, authoredH]")))

    # The labels are written from the table at runtime; a preset renamed in the
    # table must not leave a stale label in the markup.
    labels = pg.evaluate(
        "() => [...document.querySelectorAll('#canvasSeg button')]"
        ".map(b => b.textContent.trim())")
    check("the buttons are labelled from the table, not hand-typed",
          labels == [s["label"] for s in pad_sizes], str(labels))

    # -----------------------------------------------------------------------
    print("\nPAD CANVAS — free while empty")
    pg.evaluate("() => { const m = document.getElementById('menuOverlay');"
                " if (m) { m.hidden = false; m.classList.add('open'); } }")
    pg.wait_for_timeout(250)
    check("the canvas row is visible in the menu", pg.is_visible("#canvasSeg"))

    for sid in ("tall", "square", "wide"):
        sz = next(s for s in pad_sizes if s["id"] == sid)
        pg.click(f"#canvasSeg button[data-size='{sid}']")
        pg.wait_for_timeout(300)
        check(f"selecting {sz['label']} applies {sz['w']}x{sz['h']}",
              tuple(pg.evaluate("() => [authoredW, authoredH]")) == (sz["w"], sz["h"]),
              str(pg.evaluate("() => [authoredW, authoredH]")))
        check(f"{sz['label']} marks its own button selected",
              pg.evaluate(f"() => document.querySelector("
                          f"\"#canvasSeg button[data-size='{sid}']\")"
                          ".classList.contains('on')"))

    # THE BUG THIS PINS. `.seg` lived in flip.css while `.seg-slider` — the pill
    # it positions — was in styles.css. Pad does not load flip.css, so the
    # container had no `position: relative` and the absolutely-positioned
    # slider stretched against the menu sheet, painting a purple bar down the
    # entire menu. Every functional assertion above passed on that build: the
    # buttons existed, applied sizes and marked themselves selected. Only
    # geometry sees it.
    geo = pg.evaluate("""() => {
      const seg = document.getElementById('canvasSeg');
      const pill = seg.querySelector('.seg-slider');
      const s = seg.getBoundingClientRect(), p = pill.getBoundingClientRect();
      return { positioned: getComputedStyle(seg).position !== 'static',
               segH: s.height, pillH: p.height,
               contained: p.top >= s.top - 1 && p.bottom <= s.bottom + 1
                          && p.left >= s.left - 1 && p.right <= s.right + 1 };
    }""")
    check("the segment establishes a positioning context",
          geo["positioned"],
          "the slider will position against some distant ancestor instead")
    check("the slider is contained by its own segment",
          geo["contained"],
          f"pill {round(geo['pillH'])}px tall inside a {round(geo['segH'])}px "
          "segment — it is escaping and painting over the menu")
    check("the slider is not taller than the segment",
          geo["pillH"] <= geo["segH"] + 1,
          f"{round(geo['pillH'])} vs {round(geo['segH'])}")

    # Same bug as the export sheet: Pad's menu ships `hidden`, so at init the
    # buttons have no width and the pill stayed at opacity 0 — the canvas row
    # showed no selection at all until you tapped one.
    pill = pg.evaluate("""() => {
      const g = document.getElementById('canvasSeg');
      const p = g.querySelector('.seg-slider');
      const b = g.querySelector('button.on');
      if (!p || !b) return null;
      const pr = p.getBoundingClientRect(), br = b.getBoundingClientRect();
      return { opacity: parseFloat(getComputedStyle(p).opacity),
               aligned: Math.abs(pr.left - br.left) < 3,
               width: pr.width, btnWidth: br.width };
    }""")
    check("the canvas pill is visible as soon as the menu opens",
          pill and pill["opacity"] > 0.5,
          "no selection is shown until you tap a preset")
    check("and it sits on the selected preset",
          pill and pill["aligned"] and abs(pill["width"] - pill["btnWidth"]) < 3,
          f"pill {pill and round(pill['width'])}px vs button "
          f"{pill and round(pill['btnWidth'])}px")

    check("the note reports the current dimensions",
          "\u00d7" in pg.inner_text("#canvasSegNote"),
          pg.inner_text("#canvasSegNote"))

    # -----------------------------------------------------------------------
    print("\nPAD CANVAS — locked once there is a drawing")
    #
    # Pad records stroke timing. Resizing mid-take would change the space a
    # replay is drawn into partway through the recording it replays, so the
    # canvas locks — and must REFUSE rather than silently do nothing.
    before = tuple(pg.evaluate("() => [authoredW, authoredH]"))
    pg.evaluate("() => { const m = document.getElementById('menuOverlay');"
                " if (m) { m.hidden = true; m.classList.remove('open'); } }")
    pg.wait_for_timeout(200)

    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    check("a stroke was recorded", pg.evaluate("() => hasContent") is True)

    pg.evaluate("() => { const m = document.getElementById('menuOverlay');"
                " if (m) { m.hidden = false; m.classList.add('open'); }"
                " if (typeof syncCanvasSeg === 'function') syncCanvasSeg(); }")
    pg.wait_for_timeout(250)

    check("the note says the canvas is locked",
          "lock" in pg.inner_text("#canvasSegNote").lower(),
          pg.inner_text("#canvasSegNote"))

    target = next(s for s in pad_sizes if (s["w"], s["h"]) != before)
    pg.click(f"#canvasSeg button[data-size='{target['id']}']")
    pg.wait_for_timeout(400)
    check("clicking a preset after drawing does NOT resize the canvas",
          tuple(pg.evaluate("() => [authoredW, authoredH]")) == before,
          f"{pg.evaluate('() => [authoredW, authoredH]')} — a resize mid-take "
          "changes the space a replay is drawn into")
    check("and the drawing survived the refusal",
          pg.evaluate("() => hasContent") is True,
          "content was destroyed to honour a canvas change")
    check("the selection still shows the ACTUAL size, not the click",
          pg.evaluate(f"() => document.querySelector("
                      f"\"#canvasSeg button[data-size='{target['id']}']\")"
                      ".classList.contains('on')") is False,
          "the button lit up for a size that was never applied")
    check("no JS errors across the whole flow", not perrs, "; ".join(perrs[:2]))

    pg.close()
    b.close()

summarise_and_exit()
