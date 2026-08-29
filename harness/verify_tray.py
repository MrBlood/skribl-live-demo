"""The tool shelf must stop being a function of how many tools exist.

THE FAILURE THIS EXISTS TO PREVENT is not a bug, it is a process. Both editors'
bottom rows were holding two populations out of one width budget: the document controls
(colour, undo, redo, image, music, magnify), which are a CLOSED set, and the
mark-making tools, which are not. They shared one shelf, so every new tool
competed with undo for the same pixels and each addition became a fresh fitting
exercise across six breakpoints and two surfaces. Measured before the tray: a
fourth cell takes the pill 121 -> 158px and wraps the row at 320, 344, 360, 375,
390 and 431.

So the assertions here are mostly ONE assertion said at several widths: adding a
tool does not change the pill's width. If that ever stops being true, the tray
has failed at the only job it was built for, and the squeeze is back.

The fourth tool is registered through the surface's own register(), which is the
real extension point rather than a test seam — it is how a tool will actually be
added. Testing registration IS testing the feature. Nothing here asserts that
Select, Fill or Text exist: they do not, and the tray was never a promise that
they would.

TWO ASSERTIONS HERE ARE REGRESSION PINS for bugs this change introduced and that
the first version of this suite did not catch:

  * The chevron is a .tool-btn, so it was picked up by the binding that calls
    setTool(btn.dataset.tool) on every tool cell. It has no data-tool, so
    opening the tray called setTool(undefined) — Flip clamped that to the pen
    and merely looked fine; Pad assigns `tool` unconditionally and was left with
    no tool selected at all. Pinned as "opening the tray does not change the
    tool", on both surfaces.
  * The tray cells were styled `font: 600 10px/1 inherit`, which is an INVALID
    shorthand — the family slot does not accept `inherit` — so the whole
    declaration was dropped and the labels rendered in the UA default face.
    Pinned on the computed font-size.
"""
import sys

BASE = "http://127.0.0.1:5001"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


SURFACES = [
    # name, path, the row that must not wrap, the registry on window
    ("Pad",  "/",     ".toolbar",     "SkriblPadTools"),
    ("Flip", "/flip", ".flip-tools",  "SkriblFlipTools"),
]

# Registered under a name NEITHER surface ships, deliberately. This used to
# register 'select', which stopped meaning anything the moment v227 gave Flip a
# real Select: register() returns false for a duplicate, so the width assertions
# were comparing a shelf against itself and passing for the wrong reason.
TRIAL_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/>'
    '<path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/></svg>'
)
TRIAL = "trial"

STATE = r"""(barSel) => {
  const g = document.getElementById('toolGroup');
  const sl = document.getElementById('toolSlider');
  const tray = document.getElementById('toolTray');
  const chev = document.getElementById('toolMoreBtn');
  const act = g.querySelector('.tool-btn.active');
  const padL = parseFloat(getComputedStyle(g).paddingLeft) || 0;
  const want = act ? Math.round(act.offsetLeft - padL) : null;
  const got = sl ? Math.round(parseFloat((sl.style.transform.match(/-?[\d.]+/) || [0])[0])) : null;
  const bar = document.querySelector(barSel);
  // Absolutely positioned children (the tray, the shape popover) are overlays,
  // not row content: including them would report a wrap that is not there.
  const flow = [...bar.children].filter(e => e.offsetParent
                 && getComputedStyle(e).position !== 'absolute');
  const bs = flow.map(e => e.getBoundingClientRect());
  return {
    pill: Math.round(g.getBoundingClientRect().width),
    cells: [...g.querySelectorAll('.tool-btn')].filter(b => !b.hidden).map(b => b.id),
    active: act ? act.id : null,
    sliderOK: want === got, sliderWant: want, sliderGot: got,
    rowWrapped: (Math.max(...bs.map(b => b.bottom)) - Math.min(...bs.map(b => b.top)))
                > Math.max(...bs.map(b => b.height)) + 2,
    trayHidden: tray.hidden,
    trayCells: [...tray.querySelectorAll('.tool-tray-btn')].map(b => b.dataset.tool),
    chevHidden: chev.hidden,
    chevAria: chev.getAttribute('aria-expanded'),
    registered: (window.SkriblPadTools || window.SkriblFlipTools)
                ? (window.SkriblPadTools || window.SkriblFlipTools).list() : null,
    trayFontSize: (() => { const c = tray.querySelector('.tool-tray-btn');
                           return c ? getComputedStyle(c).fontSize : null; })(),
    trayActive: [...tray.querySelectorAll('.tool-tray-btn.active')]
                  .map(b => b.dataset.tool),
  };
}"""

# 320 is Display Zoom, 360 Galaxy S, 375 iPhone SE, 390 iPhone 12-15,
# 430 Pro Max, 900 desktop where the cells carry text labels.
WIDTHS = (320, 360, 375, 390, 430, 900)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for surface, path, bar, api in SURFACES:
        print(f"\nTRAY [{surface}] — the registry describes what the row has")
        page.set_viewport_size({"width": 390, "height": 800})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(350)
        s = page.evaluate(STATE, bar)
        check(f"{surface}: the registry is exposed", s["registered"] is not None,
              f"window.{api} is missing — a tool cannot be added without it")
        baseline = s["registered"] or []
        # The rosters differ ON PURPOSE and this is where that is recorded.
        # v219 removed Select from Pad because Pad replays on recorded
        # timestamps; v227 added it to Flip, which reveals strokes in index
        # order. verify_select.py carries the reasoning.
        #
        # v236 added Liquify, to Flip only, on the same division: it edits the
        # GEOMETRY of strokes already on the page, which is an editing move
        # rather than a recording one. (Built and briefly shipped in this branch
        # as "Smudge"; renamed before it ever reached main, because the word
        # promises colour blending and this moves geometry.) This equality is deliberately exact so
        # that adding a tool cannot happen quietly — a new tool is a change to
        # what the product IS, and it should cost somebody a deliberate edit
        # here rather than slipping in behind a `>=`.
        #
        # ⚑ RATCHET RAISED, v226, FLAGGED FOR THE OWNER. Flip gains a sixth
        # entry, "artmove" — and it is NOT a new capability. Move artwork has
        # shipped since v124; it lived in the PAGE BAR, a row about pages,
        # holding the one control there that moves the drawing rather than the
        # page. Reclassifying it is a filing correction. The roster is still
        # what the product IS, and it did just change, so this edit is the cost
        # the comment above intends — but read it as a control moving house,
        # not as a new tool.
        expected = ["pen", "eraser", "shape"] if surface == "Pad" \
            else ["pen", "eraser", "shape", "select", "liquify", "fill", "artmove"]
        check(f"{surface}: the roster is exactly what this surface ships",
              baseline == expected, f"{baseline} against {expected}")
        if len(baseline) <= 3:
            check(f"{surface}: every tool keeps a shelf cell",
                  s["cells"] == ["penToolBtn", "eraserToolBtn", "shapeToolBtn"],
                  str(s["cells"]))
            check(f"{surface}: the chevron is hidden", s["chevHidden"],
                  "nothing overflows at three tools, so nothing should say it does")
        else:
            check(f"{surface}: the shelf overflows rather than growing",
                  len(s["cells"]) == 3 and s["cells"][-1] == "toolMoreBtn",
                  str(s["cells"]))
            check(f"{surface}: the chevron is shown", not s["chevHidden"],
                  f"{len(baseline)} tools against a 3-cell shelf")
        check(f"{surface}: the tray is closed", s["trayHidden"])

        print(f"\nTRAY [{surface}] — the pill's width does not move when a tool is added")
        for w in WIDTHS:
            page.set_viewport_size({"width": w, "height": 800})
            page.goto(BASE + path, wait_until="load")
            page.wait_for_timeout(250)
            before = page.evaluate(STATE, bar)
            ok = page.evaluate("(a) => window[a[0]].register("
                               "{id:a[2], label:'Trial', icon:a[1]})",
                               [api, TRIAL_ICON, TRIAL])
            page.wait_for_timeout(150)
            after = page.evaluate(STATE, bar)
            # Desktop cells carry text labels, so swapping "Shape" for "More"
            # legitimately changes the width. Phones hide the labels: there the
            # number must not move at all, and that is what this suite is for.
            if w < 641:
                check(f"{surface} @{w}: the pill is the same width with 4 tools as with 3",
                      before["pill"] == after["pill"],
                      f"{before['pill']} -> {after['pill']}px")
            # Pad's row already wraps at 320 with three tools; what must not
            # change is whether adding a tool makes it worse.
            check(f"{surface} @{w}: adding a tool does not start a new row",
                  after["rowWrapped"] == before["rowWrapped"],
                  f"wrapped {before['rowWrapped']} -> {after['rowWrapped']}")
            check(f"{surface} @{w}: registering a tool succeeds", ok,
                  "register() returns false for a duplicate id — TRIAL must be "
                  "a name neither surface ships")
            check(f"{surface} @{w}: the shelf makes room by overflowing, not by growing",
                  len(after["cells"]) == 3 and after["cells"][-1] == "toolMoreBtn",
                  str(after["cells"]))

        print(f"\nTRAY [{surface}] — opening, picking and dismissing")
        page.set_viewport_size({"width": 390, "height": 800})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(250)
        page.evaluate("(a) => window[a[0]].register("
                      "{id:a[2], label:'Trial', icon:a[1]})", [api, TRIAL_ICON, TRIAL])
        page.wait_for_timeout(150)
        tool_before = page.evaluate(STATE, bar)["active"]
        page.click("#toolMoreBtn")
        page.wait_for_timeout(300)
        s = page.evaluate(STATE, bar)
        check(f"{surface}: the tray opens", not s["trayHidden"])
        check(f"{surface}: it carries a cell for every registered tool",
              s["trayCells"] == baseline + [TRIAL], str(s["trayCells"]))
        check(f"{surface}: the chevron reports it is expanded",
              s["chevAria"] == "true", str(s["chevAria"]))
        # REGRESSION PIN. The chevron is a .tool-btn and was caught by the
        # binding that calls setTool(btn.dataset.tool) on every tool cell. It
        # carries no data-tool, so opening the tray called setTool(undefined):
        # Flip clamped that to the pen and looked fine, Pad was left with no
        # tool at all.
        check(f"{surface}: opening the tray does not change the tool",
              s["active"] == tool_before, f"{tool_before} -> {s['active']}")
        check(f"{surface}: the current tool is marked in the tray",
              s["trayActive"] == ["pen"], str(s["trayActive"]))
        # REGRESSION PIN. `font: 600 10px/1 inherit` is an invalid shorthand --
        # the family slot does not accept `inherit` -- so the whole declaration
        # was dropped and the labels rendered in the UA default face.
        check(f"{surface}: the tray labels take the sheet's type, not the UA's",
              s["trayFontSize"] == "10px", str(s["trayFontSize"]))

        page.click(f".tool-tray-btn[data-tool='{TRIAL}']")
        page.wait_for_timeout(300)
        s = page.evaluate(STATE, bar)
        check(f"{surface}: picking a tool closes the tray", s["trayHidden"])
        check(f"{surface}: and it is promoted onto the shelf",
              f"{TRIAL}ToolBtn" in s["cells"],
              str(s["cells"]) + " — a tool you just chose has to be one tap away")
        check(f"{surface}: the sliding highlight is on a visible cell",
              s["sliderOK"], f"want {s['sliderWant']}px, got {s['sliderGot']}px")
        check(f"{surface}: the shelf is still three cells", len(s["cells"]) == 3, str(s["cells"]))

        page.click("#toolMoreBtn")
        page.wait_for_timeout(200)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check(f"{surface}: Escape closes the tray", page.evaluate(STATE, bar)["trayHidden"],
              "it floats over the canvas, unlike the docked drawers")

        page.click("#toolMoreBtn")
        page.wait_for_timeout(200)
        page.click("#colorOpenBtn" if surface == "Pad" else "#colorCurrent")
        page.wait_for_timeout(300)
        check(f"{surface}: opening another drawer closes the tray",
              page.evaluate(STATE, bar)["trayHidden"],
              "it is registered in the drawer set, so they are mutually exclusive")

    # ---- a tool with its OWN chooser must still get to show it -------------
    print("\nTRAY [Flip] — picking a tool from the tray runs its follow-on UI")
    # THE REGRESSION THIS CATCHES, which shipped in v227 and was reported from
    # the live demo three versions later as "shape is not giving a choice, just
    # gives you line".
    #
    # Shape has a kind picker (line / rect / oval). It was opened by a click
    # handler bound to '#toolGroup .tool-btn' — the SHELF — which was complete
    # right up until this tray was put in FRONT of the shelf. After that,
    # choosing Shape from the tray never ran that handler, the picker never
    # opened, and Shape silently used whatever kind it already had: 'line', for
    # everyone who had never happened to have Shape sitting on the shelf.
    #
    # The general shape of the bug is worth more than the instance: adding a
    # SECOND route to an action leaves any side effect attached to the first
    # route silently unreachable from the second. The fix put it where both
    # routes converge. This asserts the tray route specifically, because the
    # shelf route never broke and testing it proves nothing.
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(1100)
    hidden = lambda: page.evaluate("() => document.getElementById('shapePop').hidden")
    check("Flip: the shape picker starts closed", hidden() is True,
          "it opens on selection, not on load")
    page.click("#toolMoreBtn")
    page.wait_for_timeout(300)
    page.click(".tool-tray-btn[data-tool='shape']")
    page.wait_for_timeout(400)
    check("Flip: choosing Shape FROM THE TRAY opens its kind picker",
          hidden() is False,
          "the tray is a second route to setTool; a side effect wired only to "
          "the shelf is unreachable from it")
    kinds = page.evaluate(
        "() => [...document.querySelectorAll('#shapeSeg [data-shape]')].map(b => b.dataset.shape)")
    check("Flip: and it offers every kind, not just the current one",
          kinds == ["line", "rect", "ellipse"], str(kinds))
    page.click("#shapeSeg [data-shape='ellipse']")
    page.wait_for_timeout(300)
    check("Flip: choosing a kind takes effect and closes the picker",
          page.evaluate("() => shapeKind") == "ellipse" and hidden() is True,
          f"shapeKind={page.evaluate('() => shapeKind')}, hidden={hidden()}")
    # Selecting something else must put the picker away, or it hangs over the
    # canvas under a tool it has nothing to do with.
    page.evaluate("() => SkriblFlipTools.list()")
    page.click("#toolMoreBtn")
    page.wait_for_timeout(300)
    page.click(".tool-tray-btn[data-tool='pen']")
    page.wait_for_timeout(400)
    check("Flip: leaving Shape closes the picker",
          hidden() is True, "a chooser for a tool you are no longer using")
    page.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
