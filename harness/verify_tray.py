"""The tool shelf must stop being a function of how many tools exist.

THE FAILURE THIS EXISTS TO PREVENT is not a bug, it is a process. Flip's bottom
row was holding two populations out of one width budget: the document controls
(colour, undo, redo, image, music, magnify), which are a CLOSED set, and the
mark-making tools, which are not. They shared one shelf, so every new tool
competed with undo for the same pixels and each addition became a fresh fitting
exercise across six breakpoints and two surfaces. Measured before the tray: a
fourth cell takes the pill 121 -> 158px and wraps the row at 320, 344, 360, 375,
390 and 431.

So the assertions here are mostly ONE assertion said at several widths: adding a
tool does not change the pill's width. If that ever stops being true, the tray
has failed at the only job it was built for, and the squeeze is back.

The fourth tool is registered through window.SkriblFlipTools.register(), which
is the real extension point rather than a test seam — it is how a tool will
actually be added. Testing registration IS testing the feature. Nothing here
asserts that Select, Fill or Text exist: they do not, and the tray was never a
promise that they would.
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


SELECT_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/>'
    '<path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/></svg>'
)

STATE = r"""() => {
  const g = document.getElementById('toolGroup');
  const sl = document.getElementById('toolSlider');
  const tray = document.getElementById('toolTray');
  const chev = document.getElementById('toolMoreBtn');
  const act = g.querySelector('.tool-btn.active');
  const padL = parseFloat(getComputedStyle(g).paddingLeft) || 0;
  const want = act ? Math.round(act.offsetLeft - padL) : null;
  const got = sl ? Math.round(parseFloat((sl.style.transform.match(/-?[\d.]+/) || [0])[0])) : null;
  const bar = document.querySelector('.flip-tools');
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
    registered: window.SkriblFlipTools ? window.SkriblFlipTools.list() : null,
  };
}"""

# 320 is Display Zoom, 360 Galaxy S, 375 iPhone SE, 390 iPhone 12-15,
# 430 Pro Max, 900 desktop where the cells carry text labels.
WIDTHS = (320, 360, 375, 390, 430, 900)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    print("TRAY — the mechanism is dormant while every tool fits")
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(300)
    s = page.evaluate(STATE)
    check("the registry is exposed", s["registered"] is not None,
          "window.SkriblFlipTools is missing — a tool cannot be added without it")
    check("it holds exactly the three tools that exist",
          s["registered"] == ["pen", "eraser", "shape"], str(s["registered"]))
    check("all three keep a shelf cell",
          s["cells"] == ["penToolBtn", "eraserToolBtn", "shapeToolBtn"], str(s["cells"]))
    check("the chevron is hidden", s["chevHidden"],
          "nothing overflows with three tools, so nothing should say it does")
    check("the tray is closed", s["trayHidden"])

    print("\nTRAY — the pill's width does not move when a tool is added")
    for w in WIDTHS:
        page.set_viewport_size({"width": w, "height": 800})
        page.goto(BASE + "/flip", wait_until="load")
        page.wait_for_timeout(250)
        before = page.evaluate(STATE)
        page.evaluate("(i) => window.SkriblFlipTools.register("
                      "{id:'select', label:'Select', icon:i})", SELECT_ICON)
        page.wait_for_timeout(150)
        after = page.evaluate(STATE)
        # Desktop cells carry text labels, so swapping "Shape" for "More"
        # legitimately changes the width. Phones hide the labels: there the
        # number must not move at all, and that is the number this suite is for.
        if w >= 641:
            check(f"@{w}: the row still does not wrap with a fourth tool",
                  not after["rowWrapped"])
        else:
            check(f"@{w}: the pill is the same width with 4 tools as with 3",
                  before["pill"] == after["pill"],
                  f"{before['pill']} -> {after['pill']}px")
            check(f"@{w}: the row does not wrap", not after["rowWrapped"])
        check(f"@{w}: the shelf makes room by overflowing, not by growing",
              after["cells"] == ["penToolBtn", "eraserToolBtn", "toolMoreBtn"],
              str(after["cells"]))

    print("\nTRAY — opening, picking and dismissing")
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(250)
    page.evaluate("(i) => window.SkriblFlipTools.register("
                  "{id:'select', label:'Select', icon:i})", SELECT_ICON)
    page.wait_for_timeout(150)
    page.click("#toolMoreBtn")
    page.wait_for_timeout(250)
    s = page.evaluate(STATE)
    check("the tray opens", not s["trayHidden"])
    check("it carries a cell for every registered tool",
          s["trayCells"] == ["pen", "eraser", "shape", "select"], str(s["trayCells"]))
    check("the chevron reports it is expanded", s["chevAria"] == "true", str(s["chevAria"]))

    page.click(".tool-tray-btn[data-tool='select']")
    page.wait_for_timeout(250)
    s = page.evaluate(STATE)
    check("picking a tool closes the tray", s["trayHidden"])
    check("the picked tool is active", s["active"] == "selectToolBtn", str(s["active"]))
    check("and it is promoted onto the shelf",
          "selectToolBtn" in s["cells"],
          str(s["cells"]) + " — a tool you just chose has to be one tap away")
    check("the sliding highlight follows it onto the shelf",
          s["sliderOK"], f"want {s['sliderWant']}px, got {s['sliderGot']}px")
    check("the shelf is still three cells", len(s["cells"]) == 3, str(s["cells"]))

    page.click("#toolMoreBtn")
    page.wait_for_timeout(200)
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check("Escape closes the tray", page.evaluate(STATE)["trayHidden"],
          "it floats over the canvas, unlike the docked drawers")

    page.click("#toolMoreBtn")
    page.wait_for_timeout(200)
    page.click("#colorCurrent")
    page.wait_for_timeout(250)
    s = page.evaluate(STATE)
    check("opening another drawer closes the tray", s["trayHidden"],
          "it is registered in the drawer set, so they are mutually exclusive")

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
