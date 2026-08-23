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
    This WAS a failing assertion. On the sealed v214 tree the recording state
    needed 396px against 355 available at 375px, and this section existed to
    reproduce that. Moving Flip Mode into the overflow menu freed 40px, which is
    more than the overage, so it now PASSES with +124px of slack at 375px.
    The section stays: it is the regression test for a bug that was real, and
    the header is the part of this layout with the least room to give.

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
import base64
import pathlib
import tempfile

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

# One row, measured. A wrapped bar is a taller bar.
ONE_ROW_MAX_PX = 80

# The decided minimum touch target. This is the ONLY place the number lives.
# It is 34 because that is what ships today, not because 34 is defensible —
# raising it is a deliberate edit here, which is the point of pinning it.
MIN_TOUCH_PX = 34

# THE WIDTH POLICY, pinned here so it cannot drift back into folklore.
#
#   360px is the DESIGN TARGET — the narrowest width the layout must serve
#   properly, on one row, with nothing shrunk past the decided floor. It is a
#   very common Android width, so a two-row bar there is not a rare fallback.
#
#   320px is the SAFETY NET — not a design target. It is Display Zoom on a
#   modern iPhone, an accessibility setting rather than a legacy device, so it
#   must DEGRADE rather than break: wrap to a taller bar, clip nothing, spill
#   nothing off the page. A layout that survives 320 without breaking components
#   or spilling text works anywhere.
FIT_WIDTHS = [360, 375, 390, 393, 402, 430, 440, 600, 641, 768]
DEGRADE_WIDTHS = [320]

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


GEOMETRY = """() => {
  // '.toolbar, .flip-tools' — BOTH, and the omission here was a real bug in this
  // suite rather than in the product. Pad's bar is `.toolbar`; Flip's is
  // `.flip-tools`. Section 2's REACH_Q below already used the compound selector,
  // this one did not, and so section 1 returned null on every Flip width and
  // reported "found a toolbar: False" ten times over. Nothing caught it because
  // this suite was written during the v219 build and the build was never run —
  // which is the whole argument for running one before sealing.
  const bar = document.querySelector('.toolbar, .flip-tools');
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
    # The two surfaces degrade DIFFERENTLY, and both are legitimate. Pad wraps to
    # a taller bar. Flip sets `flex-wrap: nowrap; overflow-x: auto` below 560px
    # deliberately — its own comment says "keep the bottom tool row on ONE line
    # on phones (music was wrapping)" — so it scrolls instead.
    #
    # What matters is not WHICH, but that every control stays REACHABLE and the
    # page never spills sideways. An earlier version asserted `overflow <= 0`,
    # which forbade Flip's scroll row and would have failed a deliberate design
    # decision as though it were a defect.
    REACH_Q = (
        "() => {"
        "  const bar = document.querySelector('.toolbar, .flip-tools');"
        "  if (!bar) return null;"
        "  const cs = getComputedStyle(bar);"
        "  const over = bar.scrollWidth - bar.clientWidth;"
        "  const scrollable = cs.overflowX === 'auto' || cs.overflowX === 'scroll';"
        "  bar.scrollLeft = bar.scrollWidth;"
        "  const kids = [...bar.children].filter(e => e.offsetParent);"
        "  const last = kids[kids.length - 1].getBoundingClientRect();"
        "  const box = bar.getBoundingClientRect();"
        "  bar.scrollLeft = 0;"
        "  return { over, scrollable, lastReachable: last.right <= box.right + 2 };"
        "}"
    )
    for w in DEGRADE_WIDTHS:
        for surface, path in (("Pad", "/"), ("Flip", "/flip")):
            pg = ctx.new_page()
            pg.set_viewport_size({"width": w, "height": 800})
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(150)
            r = pg.evaluate(REACH_Q)
            pg.close()
            if r is None:
                check(f"{surface} @{w}px — found a toolbar", False)
                continue
            # Either it fits/wraps (no overflow), or it overflows into a scroller
            # whose end you can actually reach.
            reachable = r["over"] <= 0 or (r["scrollable"] and r["lastReachable"])
            how = "wraps" if r["over"] <= 0 else "scrolls"
            check(f"{surface} @{w}px keeps every control reachable ({how})",
                  reachable,
                  "overflowing without a scroller hides controls with no cue")
            # The whole point of the safety net: nothing spills off the page.
            pg = ctx.new_page()
            pg.set_viewport_size({"width": w, "height": 800})
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(120)
            spill = pg.evaluate("() => document.documentElement.scrollWidth "
                                "- document.documentElement.clientWidth")
            pg.close()
            check(f"{surface} @{w}px does not spill horizontally",
                  spill <= 0, f"page is {spill}px wider than the viewport")

    # ------------------------------------------------------------ section 2
    print("\nLAYOUT 2 — the header fits in every state")

    def draw_a_stroke(pg):
        """Put the editor into a state that has content, the way a user would."""
        # '#canvas, #pad' — Pad's drawing surface is #canvas and Flip's is #pad.
        # This read #pad only, and section 2 measures Pad, so every header state
        # that needed content on the canvas timed out waiting for an element that
        # is not on that page. Same root cause as the GEOMETRY selector above: a
        # suite written against one surface and never executed against either.
        box = pg.locator("#canvas, #pad").first.bounding_box()
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

    # TWO THINGS IN THIS SECTION WERE WRITTEN AGAINST A TREE THAT NEVER SHIPPED,
    # and both only surfaced when the suite was first executed. Read before
    # editing.
    #
    # 1. #flipBtn is no longer in the header. v219 moved Flip Mode into the •••
    #    menu with a subtitle, so a bare click times out waiting for an element
    #    that is not visible. The menu has to be opened first — which is also
    #    what a user does, so the test got MORE faithful, not less.
    #
    # 2. The guard fires on ATTACHED MEDIA, not on any drawing. app.js is
    #    explicit that the first version fired on `recording || hasContent ||
    #    recorded` and was deliberately narrowed to `photoBg ||
    #    currentAudioBuffer`, because Pad's autosave keeps strokes and does NOT
    #    keep media bytes — so a stroke is not at risk and a confirm about it is
    #    a confirm that is usually wrong. This section asserted the REJECTED
    #    version: draw a stroke, expect a dialog. Pinning a design that was
    #    considered and turned down is worse than not pinning it, because it
    #    reads as a regression the next time someone gets it right.
    #
    # So: strokes alone must navigate freely, and an attached image must confirm.
    # Both directions are asserted, because a guard that never fires and a guard
    # that always fires fail this section identically if only one is checked.
    def open_flip_entry(pg):
        pg.click("#menuBtn")
        pg.wait_for_timeout(250)
        pg.click("#flipBtn")
        pg.wait_for_timeout(300)

    # A 1x1 PNG is enough: the guard reads whether photoBg is set, not what it is.
    _PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    _png_path = pathlib.Path(tempfile.gettempdir()) / "skribl_layout_probe.png"
    _png_path.write_bytes(_PNG)

    # Empty canvas: the guard must NOT fire. A dialog that appears when there is
    # nothing to lose teaches people to dismiss it unread.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    open_flip_entry(pg)
    check("empty canvas — Flip navigates with no confirm",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # Strokes only: still no confirm. Pad's autosave keeps strokes, so there is
    # nothing to lose and the guard is correct to stay silent.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    open_flip_entry(pg)
    check("strokes but no media — Flip still navigates (autosave keeps strokes)",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # With media attached: the click must NOT navigate. Media bytes are the thing
    # localStorage cannot hold, so this is the case where work is genuinely lost.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    pg.set_input_files("#photoInput", str(_png_path))
    pg.wait_for_timeout(700)
    before = pg.url
    open_flip_entry(pg)
    check("with attached media — Flip does not navigate",
          pg.url == before,
          f"navigated to {pg.url} — media that autosave cannot hold was discarded")
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
    # Via the ••• menu again: the guard closes that menu when it fires, so the
    # second approach starts from the same closed state as the first.
    open_flip_entry(pg)
    pg.click("#leaveGo")
    pg.wait_for_timeout(400)
    check("'Leave' navigates to Flip", "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # Both surfaces — but NOT the same behaviour, and this is the one place in
    # the file where parity is the wrong instinct.
    #
    # The rule of thumb is sound: most v213 bugs were one surface having a fix
    # the other lacked. It does not apply here, and the ORIGINAL detail string
    # below said so while the assertion contradicted it — it read "the guard is
    # Pad-only", which is exactly right and was written as a failure message.
    #
    # Flip has no leave-guard DELIBERATELY. It persists pages, music and the
    # background image, so nothing is at risk when you leave and a confirm could
    # only ever be a false alarm — the same reasoning that narrowed Pad's guard
    # to attached media. Pad needs one only because its autosave cannot hold
    # media bytes. So the asymmetry is the design, and when durable drafts land
    # the correct outcome is Pad losing its guard too, not Flip gaining one.
    #
    # Pinned in that direction: Flip must navigate FREELY. If someone later adds
    # a confirm here in the name of consistency, this fails and sends them to
    # this comment.
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
        check("Flip — leaving navigates freely; Flip persists its work, so a confirm would be a false alarm",
              "/flip" not in pg.url,
              f"stayed on {pg.url} — a guard appeared on the surface that does not need one")
    pg.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# The failure has to travel through the channel run_harness.sh actually reads.
# Eight suites printed their failures and exited 0, and the runner recorded them
# as ok. Printing it is not reporting it.
sys.exit(1 if bad else 0)
