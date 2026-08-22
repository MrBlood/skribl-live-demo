"""Rendered geometry for the header and tool row — the class of defect no
attribute check can see.

WHY THIS IS A NEW SUITE. verify_tools.py is at 125 assertions and ~30 browser
launches, past the split trigger. More to the point, every assertion here is
about LAYOUT, and layout is the one thing this project has repeatedly got wrong
while every attribute passed: the v213 record pill wrapped, Pad wrapped at
320px, and the harness was green throughout.

THE RULE THIS SUITE ENFORCES ON ITSELF. Measure what the browser laid out,
never what the CSS was told to do. Flex shrinks controls before anything
overflows, so summing child widths reports room that is not there; and an
element can be `hidden` in every sense the DOM reports while still occupying
space. So: getBoundingClientRect, scrollWidth against clientWidth, and
offsetParent — not computed styles, not class lists.

SECTION 1 — the row fits on one line at every supported width.
    Pad WRAPPED at 320px (bar 113px tall against 68px) and Flip OVERFLOWED by
    16px, and neither was caught. The height IS the assertion: a wrapped bar is
    a taller bar, and that is measurable where "did it wrap" is not.

SECTION 2 — the header fits in every state, including mid-recording.
    Measured on the sealed v214 tree, the recording state needs 396px against
    355 available at 375px. It is over budget on every phone TODAY. This
    section reproduces that as a failing assertion first.

SECTION 3 — touch targets.
    The mobile stylesheet sets .tool-open to 36px below 640px and the smallest
    control renders at 34px. That is below the 44px the docs assume. This
    section does not assert 44 — that is a product decision, not a fact — it
    asserts the floor the project has DECIDED on, so the number lives in one
    place and changing it is deliberate.

SECTION 4 — the Flip navigation guard.
    Asserts the URL after the click, not the sheet. A sheet appearing proves a
    sheet appeared; only the URL proves the work survived.

Requires a running server. Run it like the other browser suites:
    ./harness/run_harness.sh verify_layout.py
"""
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

# One row, measured. A wrapped bar is a taller bar.
ONE_ROW_MAX_PX = 80

# The decided minimum touch target. This is the ONLY place the number lives.
# It is 34 because that is what ships today, not because 34 is defensible —
# raising it is a deliberate edit here, which is the point of pinning it.
MIN_TOUCH_PX = 34

# Widths the project supports. 320 is Display Zoom on a modern iPhone, not a
# legacy device, so it is expected to WRAP gracefully rather than fit.
FIT_WIDTHS = [375, 390, 393, 402, 430, 440, 600, 641, 768]
DEGRADE_WIDTHS = [320]

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


GEOMETRY = """() => {
  const bar = document.querySelector('.toolbar');
  if (!bar) return null;
  const r = bar.getBoundingClientRect();
  // offsetParent, not the hidden property: an explicit display defeats [hidden],
  // and this codebase has been bitten by that three times.
  const controls = [...bar.querySelectorAll('.tool-btn, .tool-open, .undo-btn')]
      .filter(e => e.offsetParent !== null)
      .map(e => ({ id: e.id, w: +e.getBoundingClientRect().width.toFixed(1) }));
  return {
    height: +r.height.toFixed(1),
    width:  +r.width.toFixed(1),
    overflow: bar.scrollWidth - bar.clientWidth,
    controls,
    smallest: controls.length ? Math.min(...controls.map(c => c.w)) : 0
  };
}"""

HEADER_GEOMETRY = """() => {
  const h = document.querySelector('.header');
  const a = document.querySelector('.actions');
  if (!h || !a) return null;
  const cs = getComputedStyle(h);
  const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const brand = h.querySelector('.brand');
  const brandW = (brand && brand.offsetParent) ? brand.getBoundingClientRect().width : 0;
  return {
    height: +h.getBoundingClientRect().height.toFixed(1),
    available: +h.getBoundingClientRect().width.toFixed(1),
    // Intrinsic need, not the flexed width: .actions stretches to fill, which
    // hides overflow until a child clips. Sum what the children actually want.
    needed: +(brandW + a.scrollWidth + pad).toFixed(1),
    overflow: h.scrollWidth - h.clientWidth
  };
}"""


def measure(ctx, path, width, height=800, evaluate=GEOMETRY, prepare=None):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": width, "height": height})
    pg.goto(BASE + path, wait_until="load")
    if prepare:
        prepare(pg)
    pg.wait_for_timeout(120)          # let fitBrand() and any layout JS settle
    out = pg.evaluate(evaluate)
    pg.close()
    return out


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()

    # ------------------------------------------------------------ section 1
    print("\nLAYOUT 1 — the tool row is one line at every supported width")

    for surface, path in (("Pad", "/"), ("Flip", "/flip")):
        for w in FIT_WIDTHS:
            g = measure(ctx, path, w)
            if g is None:
                check(f"{surface} @{w}px — found a toolbar", False)
                continue
            check(f"{surface} @{w}px is one row",
                  g["height"] <= ONE_ROW_MAX_PX,
                  f"bar {g['height']}px tall, {len(g['controls'])} controls")
            check(f"{surface} @{w}px does not clip",
                  g["overflow"] <= 0,
                  f"scrollWidth exceeds clientWidth by {g['overflow']}px")

    # 320px is Display Zoom, an accessibility setting. It is not a design
    # target, but it must DEGRADE rather than clip: a taller bar is honest,
    # a clipped one hides controls with no cue that anything is missing.
    for w in DEGRADE_WIDTHS:
        g = measure(ctx, "/", w)
        check(f"Pad @{w}px degrades by wrapping, never by clipping",
              g is not None and g["overflow"] <= 0,
              "clipping hides controls silently; wrapping does not")

    # ------------------------------------------------------------ section 2
    print("\nLAYOUT 2 — the header fits in every state")

    def draw_a_stroke(pg):
        """Put the editor into a state that has content, the way a user would."""
        box = pg.locator("#pad").bounding_box()
        pg.mouse.move(box["x"] + 40, box["y"] + 40)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 120, box["y"] + 90, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(150)

    def stop_the_take(pg):
        draw_a_stroke(pg)
        pg.click("#recordBtn")            # ends the take; Play/Post/duration appear
        pg.wait_for_timeout(200)

    STATES = (("idle", None), ("recording", draw_a_stroke), ("review", stop_the_take))

    for state, prepare in STATES:
        for w in (375, 390, 393, 430):
            h = measure(ctx, "/", w, evaluate=HEADER_GEOMETRY, prepare=prepare)
            if h is None:
                check(f"header @{w}px in {state} — found a header", False)
                continue
            slack = h["available"] - h["needed"]
            check(f"header @{w}px fits in {state}",
                  slack >= 0,
                  f"needs {h['needed']:.0f}px, has {h['available']:.0f}px "
                  f"({slack:+.0f}px)")
            # A header that fits by wrapping is not a header that fits. The
            # v213 report was a wrapped record pill, and height is how that
            # shows up in a measurement.
            check(f"header @{w}px in {state} stays one row",
                  h["height"] <= ONE_ROW_MAX_PX,
                  f"{h['height']}px tall")

    # ------------------------------------------------------------ section 3
    print("\nLAYOUT 3 — touch targets hold the decided floor")

    for surface, path in (("Pad", "/"), ("Flip", "/flip")):
        for w in (375, 393, 430):
            g = measure(ctx, path, w)
            if not g or not g["controls"]:
                check(f"{surface} @{w}px — found controls to measure", False)
                continue
            worst = min(g["controls"], key=lambda c: c["w"])
            check(f"{surface} @{w}px every control >= {MIN_TOUCH_PX}px",
                  g["smallest"] >= MIN_TOUCH_PX,
                  f"smallest is {worst['id'] or '(unnamed)'} at {worst['w']}px")

    # ------------------------------------------------------------ section 4
    print("\nLAYOUT 4 — leaving Pad cannot silently discard work")

    # Empty canvas: the guard must NOT fire. A dialog that appears when there is
    # nothing to lose teaches people to dismiss it unread.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    pg.click("#flipBtn")
    pg.wait_for_timeout(300)
    check("empty canvas — Flip navigates with no confirm",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # With work on the canvas: the click must NOT navigate. This is the
    # assertion that fails on the sealed v214 tree, which is the point of it.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    before = pg.url
    pg.click("#flipBtn")
    pg.wait_for_timeout(300)
    check("with unposted work — Flip does not navigate",
          pg.url == before,
          f"navigated to {pg.url} — unposted work was discarded")
    sheet = pg.locator("#leaveSheet")
    check("with unposted work — a confirm is shown",
          sheet.count() > 0 and sheet.is_visible())
    # The safe choice takes focus, so a stray Enter or a mis-tap keeps the work.
    focused = pg.evaluate("() => document.activeElement && document.activeElement.id")
    check("the confirm focuses the safe choice", focused == "leaveCancel",
          f"focus is on {focused!r}")

    # Cancel keeps you here.
    pg.click("#leaveCancel")
    pg.wait_for_timeout(200)
    check("'Keep drawing' stays on Pad", pg.url == before, f"landed on {pg.url}")

    # Confirm lets you out — a guard that traps you is its own bug.
    pg.click("#flipBtn")
    pg.wait_for_timeout(200)
    pg.click("#leaveGo")
    pg.wait_for_timeout(400)
    check("'Leave' navigates to Flip", "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # Both surfaces. Every fix in this codebase has to be made twice, and most
    # bugs in the v213 session were one surface having a fix the other lacked.
    pg = ctx.new_page()
    pg.goto(BASE + "/flip", wait_until="load")
    back = pg.locator("#padBtn, .pad-btn, a[href='/']").first
    if back.count() == 0:
        check("Flip has a link back to Pad to guard", False,
              "no back-link found — update this selector if it was renamed")
    else:
        box = pg.locator("#flipCanvas, canvas").first.bounding_box()
        if box:
            pg.mouse.move(box["x"] + 40, box["y"] + 40)
            pg.mouse.down(); pg.mouse.move(box["x"] + 110, box["y"] + 80, steps=6); pg.mouse.up()
            pg.wait_for_timeout(150)
        before = pg.url
        back.click()
        pg.wait_for_timeout(300)
        check("Flip — leaving with unposted work does not navigate",
              pg.url == before,
              f"navigated to {pg.url} — the guard is Pad-only")
    pg.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# The failure has to travel through the channel run_harness.sh actually reads.
# Eight suites printed their failures and exited 0, and the runner recorded them
# as ok. Printing it is not reporting it.
sys.exit(1 if bad else 0)
