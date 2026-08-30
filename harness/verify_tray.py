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


PAD_ROWS = """() => ({
    sides: !document.getElementById("shapeSidesRow").hidden,
    radius: !document.getElementById("shapeRadiusRow").hidden })"""

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
        #
        # ⚑ RATCHET RAISED, v238, FLAGGED FOR THE OWNER. Flip gains a tenth
        # entry, "stamp", and this one IS a new capability: a persistent,
        # multi-slot, tap-to-place clipboard. It adds nothing to the saved
        # format — a placed stamp is ordinary stroke groups — but it does add a
        # thing the product can do, so the edit is the cost this ratchet is for.
        expected = ["pen", "eraser", "shape"] if surface == "Pad" \
            else ["pen", "eraser", "shape", "select", "liquify", "smudge", "blur", "fill",
            "stamp", "artmove"]
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
          kinds == ["line", "rect", "ellipse", "poly"], str(kinds))
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
    # ---- the polygon and the corner knob, on the pure geometry -------------
    print("\nSHAPES [lib] — the fourth kind, and the knob that clamps itself")
    geo = page.evaluate("""() => {
      const S = window.SkriblShapes;
      const A = {x:0, y:0}, B = {x:100, y:100};
      const bbox = (pts) => { let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
        for (const p of pts) { x0=Math.min(x0,p.x); x1=Math.max(x1,p.x);
                               y0=Math.min(y0,p.y); y1=Math.max(y1,p.y); }
        return {x0,y0,x1,y1}; };
      const tri = S.points('poly', A, B, {sides:3});
      const hex = S.points('poly', A, B, {sides:6});
      const sq  = S.points('rect', A, B, {});
      const rnd = S.points('rect', A, B, {radius:25});
      const mad = S.points('rect', A, B, {radius:9999});
      // A polygon's first point is its TOP vertex, so a triangle points up.
      const t0 = tri[0];
      return { triTop: {x: Math.round(t0.x), y: Math.round(t0.y)},
               triBox: bbox(tri), hexBox: bbox(hex),
               kinds: S.KINDS,
               sqN: sq.length, rndN: rnd.length, madN: mad.length,
               madBox: bbox(mad),
               low: S.points('poly', A, B, {sides:1}).length,
               high: S.points('poly', A, B, {sides:99}).length };
    }""")
    check("Flip: 'poly' is a registered kind", "poly" in geo["kinds"], str(geo["kinds"]))
    check("Flip: a triangle points UP",
          geo["triTop"]["y"] == 0 and 45 <= geo["triTop"]["x"] <= 55,
          f"first vertex {geo['triTop']} — an unrotated polygon starts at 0 "
          "radians and gives a triangle lying on its side, which is not what "
          "anyone means by 'triangle'")
    check("Flip: sides actually change the shape",
          geo["triBox"]["y1"] < geo["hexBox"]["y1"],
          f"tri {geo['triBox']} vs hex {geo['hexBox']} — an inscribed triangle "
          "cannot reach the bottom of the box and a hexagon can")
    check("Flip: rounding changes a rectangle's outline",
          geo["rndN"] != geo["sqN"], f"{geo['sqN']} -> {geo['rndN']} points")
    # THE KNOB HAS TO CLAMP ITSELF. A slider that lets someone ask for more
    # rounding than an edge can give folds the shape through itself, and the
    # value that does it differs with every drag size — so it cannot be a
    # max on the input. Clamped in the geometry, the slider simply stops
    # having an effect, which is what running a control to its end should do.
    check("Flip: an absurd radius clamps instead of folding the shape",
          geo["madN"] > 8
          and geo["madBox"]["x0"] >= -1 and geo["madBox"]["x1"] <= 101
          and geo["madBox"]["y0"] >= -1 and geo["madBox"]["y1"] <= 101,
          f"{geo['madN']} pts, box {geo['madBox']} — radius 9999 on a 100px box")
    check("Flip: sides clamp at both ends rather than degenerating",
          geo["low"] > 8 and geo["high"] > 8,
          f"sides=1 -> {geo['low']} pts, sides=99 -> {geo['high']} pts")

    # WHICH KINDS OFFER WHICH KNOB is one rule with two consumers — the rows
    # syncShapeKnobs hides, and the picker deciding whether a pick left
    # anything worth staying open for — on two surfaces. It lives in the lib
    # so there is one copy; asserted here on the lib so a surface that starts
    # restating it has something to disagree with.
    kn = page.evaluate("""() => {
        const S = window.SkriblShapes;
        const out = {};
        for (const k of S.KINDS) out[k] = S.knobs(k);
        out.mutable = (S.knobs("poly").push("bogus"), S.knobs("poly"));
        return out;
    }""")
    check("Flip: the lib says which knobs each kind has",
          {k: kn[k] for k in ("line", "rect", "ellipse", "poly")}
          == {"line": [], "rect": ["radius"], "ellipse": [], "poly": ["sides", "radius"]},
          str(kn))
    check("Flip: and hands out a copy, so a caller cannot edit the rule "
          "out from under the other caller",
          kn["mutable"] == ["sides", "radius"], str(kn["mutable"]))

    # The knobs are only shown where they mean something.
    page.click("#toolMoreBtn")
    page.wait_for_timeout(250)
    page.click(".tool-tray-btn[data-tool='shape']")
    page.wait_for_timeout(350)
    rows = lambda: page.evaluate("""() => ({
        sides: !document.getElementById('shapeSidesRow').hidden,
        radius: !document.getElementById('shapeRadiusRow').hidden })""")
    page.click("#shapeSeg [data-shape='line']")
    page.wait_for_timeout(250)
    check("Flip: a line offers neither knob", rows() == {"sides": False, "radius": False},
          str(rows()))
    if hidden():
        page.click("#toolMoreBtn"); page.wait_for_timeout(250)
        page.click(".tool-tray-btn[data-tool='shape']"); page.wait_for_timeout(350)
    page.click("#shapeSeg [data-shape='poly']")
    page.wait_for_timeout(250)
    check("Flip: a polygon offers both", rows() == {"sides": True, "radius": True},
          f"{rows()} — a control you cannot use is still one to read past")

    # REPORTED FROM THE LIVE DEMO: "when you push poly it chooses it, but you
    # have to choose it again to get the menu". The picker closed on EVERY
    # pick, including the two picks that reveal a knob — so Sides and Corners
    # were revealed and hidden in the same click, and the only way to reach
    # them was to reopen the picker you had just used.
    #
    # The rule is now derived from what the pick DID rather than from the fact
    # that a pick happened: if choosing this kind left a knob on screen, the
    # picker stays up, because that knob is the reason it is still needed.
    check("Flip: picking Poly LEAVES the picker open, so the knobs it just "
          "revealed are reachable without opening it a second time",
          hidden() is False,
          "closing on a pick throws away the rows syncShapeKnobs just showed")
    sides = page.evaluate("""() => {
        const el = document.getElementById("shapeSides");
        const r = el.getBoundingClientRect();
        const top = document.elementFromPoint(r.left + r.width / 2,
                                              r.top + r.height / 2);
        return { onScreen: r.width > 0 && r.height > 0,
                 reachable: !!(top && (top === el || el.contains(top))) };
    }""")
    check("Flip: and the Sides slider is actually hittable where it is drawn, "
          "not merely un-hidden underneath something else",
          sides == {"onScreen": True, "reachable": True}, str(sides))

    # The counterpart, and the half that must NOT regress: a kind with nothing
    # left to set has no reason to keep the picker over the canvas.
    if hidden():
        page.click("#toolMoreBtn"); page.wait_for_timeout(250)
        page.click(".tool-tray-btn[data-tool='shape']"); page.wait_for_timeout(350)
    page.click("#shapeSeg [data-shape='line']")
    page.wait_for_timeout(250)
    check("Flip: picking Line still closes it — nothing was revealed to stay "
          "open for", hidden() is True,
          "a picker with no knobs left to offer is finished on the pick")

    # Reopen only if the pick above actually closed it. Written this way so a
    # regression that leaves the picker open fails the assertion ABOVE rather
    # than timing out here on a button the tray is covering — a mutation that
    # crashes the suite is a mutation nobody can read the result of.
    if hidden():
        page.click("#toolMoreBtn"); page.wait_for_timeout(250)
        page.click(".tool-tray-btn[data-tool='shape']"); page.wait_for_timeout(350)
    page.click("#shapeSeg [data-shape='poly']"); page.wait_for_timeout(250)
    page.click("#toolMoreBtn"); page.wait_for_timeout(250)
    page.click(".tool-tray-btn[data-tool='pen']"); page.wait_for_timeout(400)
    check("Flip: leaving Shape closes the picker",
          hidden() is True, "a chooser for a tool you are no longer using")
    page.close()

    # ---- and the same rule on Pad -----------------------------------------
    # SAID TWICE ON PURPOSE. The two surfaces carry SEPARATE copies of both the
    # pick handler and the dismisser, so a fix to one is not a fix to the
    # other, and this bug was reported against only one of them. Asserting it
    # on Pad alone would have let the copy drift straight back.
    print("\nSHAPES [Pad] — the same picker, the same rule, a second copy")
    pad = browser.new_page(viewport={"width": 1200, "height": 950})
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(1000)
    phidden = lambda: pad.evaluate("() => document.getElementById('shapePop').hidden")
    prows = lambda: pad.evaluate(PAD_ROWS)
    pad.click("#shapeToolBtn")
    pad.wait_for_timeout(400)
    check("Pad: choosing Shape opens its kind picker", phidden() is False,
          "the picker is how a kind gets chosen at all")
    if phidden():
        pad.click("#shapeToolBtn"); pad.wait_for_timeout(350)
    pad.click("#shapeSeg [data-shape='poly']")
    pad.wait_for_timeout(300)
    check("Pad: picking Poly reveals both knobs AND leaves them on screen",
          prows() == {"sides": True, "radius": True} and phidden() is False,
          f"rows={prows()}, hidden={phidden()}")
    if phidden():
        pad.click("#shapeToolBtn"); pad.wait_for_timeout(350)
    pad.click("#shapeSeg [data-shape='ellipse']")
    pad.wait_for_timeout(300)
    check("Pad: picking Oval closes it — no knob was left to stay open for",
          prows() == {"sides": False, "radius": False} and phidden() is True,
          f"rows={prows()}, hidden={phidden()}")
    pad.close()

    # ---- no control is left to the browser's own painting -----------------
    # REPORTED FROM THE LIVE DEMO: "the new sliders are for light theme".
    #
    # Sides, Corners and stamp Size were added without class="slider", so the
    # shared custom track never applied and the UA painted its own -- and a UA
    # control takes the page's color-scheme, which was never declared, so it
    # defaulted to LIGHT. A white track inside a near-black popover.
    #
    # Asserted over EVERY range input rather than the three that were wrong,
    # because the bug is "a new slider forgot the class" and the next one will
    # forget it too. appearance:none is what .slider sets and what the UA does
    # not, so it distinguishes a styled control from a painted one.
    print("\nTHEME — every range input is ours, not the browser's")
    for _name, _path in (("Pad", "/"), ("Flip", "/flip")):
        tp = browser.new_page(viewport={"width": 1200, "height": 950})
        tp.goto(BASE + _path, wait_until="load")
        tp.wait_for_timeout(900)
        info = tp.evaluate("""() => {
            const els = [...document.querySelectorAll('input[type="range"]')];
            const bare = els.filter(el => {
                const a = getComputedStyle(el).appearance;
                return a !== "none";
            }).map(el => el.id || el.className || "(anonymous)");
            return { total: els.length, bare,
                     scheme: getComputedStyle(document.documentElement).colorScheme };
        }""")
        check(f"{_name}: there are range inputs to check at all",
              info["total"] > 0,
              "an empty set would make the next assertion vacuous")
        check(f"{_name}: every range input carries the shared slider styling",
              info["bare"] == [],
              f"{info['bare']} fall back to the UA control out of {info['total']}")
        check(f"{_name}: the document declares a dark color-scheme, so anything "
              "the UA does paint defaults dark rather than light",
              info["scheme"] == "dark", f"color-scheme: {info['scheme']}")
        # And the opt-in light theme has to say so too, or a light-mode user
        # gets the mirror image of this bug.
        tp.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        tp.wait_for_timeout(150)
        check(f"{_name}: and it flips to light when the light theme is chosen",
              tp.evaluate("() => getComputedStyle(document.documentElement).colorScheme")
              == "light",
              "a dark color-scheme under a light theme paints dark widgets on white")
        tp.close()

    # ---- every tool the surface ships is explained in How it works --------
    # THE GAP THIS CLOSES. Five of Flip's ten tools -- Select, Smudge, Blur,
    # Fill and Stamps -- had no help entry at all, and two of the five were
    # worse than missing: the Background image section has controls named
    # "Fill / Fit / Stretch" and "Blur", so the help SEARCH answered a query
    # about either tool with a confident paragraph about framing a photo. A
    # reader gets an answer, it is the wrong one, and they stop looking.
    #
    # Matched on data-help-tool rather than on the label text, for exactly that
    # reason: a text match would have paired both tools with the image controls
    # and reported full coverage. The attribute is the link, and it can only be
    # written deliberately.
    #
    # Asserted against the REGISTRY, which is where a tool is declared, so a
    # tool added without a help entry fails here rather than shipping mute.
    print("\nHELP — no tool ships without an explanation")
    for _name, _path, _reg in (("Pad", "/", "SkriblPadTools"),
                               ("Flip", "/flip", "SkriblFlipTools")):
        hp = browser.new_page(viewport={"width": 1200, "height": 950})
        hp.goto(BASE + _path, wait_until="load")
        hp.wait_for_timeout(900)
        cov = hp.evaluate("""(reg) => {
            const ids = window[reg].list();   // list() returns ids, not objects
            const documented = [...document.querySelectorAll("[data-help-tool]")]
                .map(el => el.getAttribute("data-help-tool"));
            return { ids,
                     missing: ids.filter(i => !documented.includes(i)),
                     orphan: documented.filter(d => !ids.includes(d)),
                     empty: documented.filter(d => {
                         const el = document.querySelector(
                             '[data-help-tool="' + d + '"] .help-desc');
                         return !el || el.textContent.trim().length < 40;
                     }) };
        }""", _reg)
        check(f"{_name}: the registry has tools to document",
              len(cov["ids"]) > 0, "an empty roster would pass vacuously")
        check(f"{_name}: every tool on this surface has a How it works entry",
              cov["missing"] == [],
              f"undocumented: {cov['missing']} of {cov['ids']}")
        check(f"{_name}: and no entry describes a tool this surface does not "
              "ship", cov["orphan"] == [],
              f"{cov['orphan']} — a Flip-only tool explained on Pad sends the "
              "reader looking for a button that is not there")
        check(f"{_name}: each entry actually says something",
              cov["empty"] == [],
              f"{cov['empty']} have under 40 characters of description — a pill "
              "with no text would satisfy the check above and explain nothing")
        hp.close()

    # ---- the canvas says which tool is live -------------------------------
    # SEVEN TOOLS WORE ONE CURSOR. Liquify has its dashed influence ring and
    # the eraser its circle; Smudge, Blur, Fill, Select, Stamps, Shape and
    # Artwork all fell through to the PEN's ring, so the only way to know what
    # a drag was about to do was to remember what you last tapped. Asked
    # directly by the owner: "are you showing the tool being used so I know
    # which tool I am using?"
    #
    # The badge is lifted from the tool's own shelf button rather than copied,
    # so the assertion is not "a badge appears" but "the badge is THIS tool's
    # glyph" -- a single shared icon would satisfy the weaker version and tell
    # the user nothing. Checked against the registry so a new tool cannot ship
    # without one.
    print("\nCURSOR — the badge names the tool under your hand")
    bp = browser.new_page(viewport={"width": 1280, "height": 900})
    bp.goto(BASE + "/flip", wait_until="load")
    bp.wait_for_timeout(1100)
    pb = bp.eval_on_selector("#pad", "e => { const r = e.getBoundingClientRect();"
                             " return { x: r.x, y: r.y, w: r.width, h: r.height }; }")
    roster = bp.evaluate("() => SkriblFlipTools.list()")
    seen = {}
    for tid in roster:
        bp.evaluate("(t) => setTool(t)", tid)
        bp.mouse.move(pb["x"] + pb["w"] * 0.5, pb["y"] + pb["h"] * 0.5)
        bp.wait_for_timeout(160)
        got = bp.evaluate("""(t) => {
            const b = document.querySelector(".flip-tool-badge");
            const shelf = document.getElementById(t + "ToolBtn");
            const bs = b && b.querySelector("svg");
            const ss = shelf && shelf.querySelector("svg");
            return { shown: b && b.style.display === "block",
                     mine: !!(bs && ss && bs.innerHTML === ss.innerHTML),
                     ink: bs ? bs.innerHTML.length : 0 };
        }""", tid)
        seen[tid] = got
    check("every tool shows a cursor badge",
          all(v["shown"] for v in seen.values()),
          str({k: v["shown"] for k, v in seen.items() if not v["shown"]}))
    check("and it is THAT tool's own glyph, not one shared badge",
          all(v["mine"] for v in seen.values()),
          str({k: v for k, v in seen.items() if not v["mine"]}))
    check("the glyphs are actually distinct from one another",
          len({bp.evaluate("(t) => { const s = document.getElementById(t + 'ToolBtn')"
                           ".querySelector('svg'); return s ? s.innerHTML : ''; }", t)
               for t in roster}) == len(roster),
          "two tools drawing the same glyph would pass the check above and "
          "still leave the user unable to tell them apart")
    # It must get out of the way while you are actually drawing.
    bp.evaluate("() => setTool('pen')")
    bp.mouse.move(pb["x"] + 100, pb["y"] + 100)
    bp.mouse.down()
    bp.mouse.move(pb["x"] + 200, pb["y"] + 160)
    bp.wait_for_timeout(120)
    mid = bp.evaluate("() => document.querySelector('.flip-tool-badge')"
                      ".style.display === 'block'")
    bp.mouse.up()
    bp.wait_for_timeout(150)
    check("the badge hides while a stroke is being drawn",
          mid is False,
          "a glyph trailing your hand across your own drawing is in the way")
    bp.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
