"""Tooltips and first-use hints.

TOOLTIPS. A native `title` cannot be styled — not the corners, not the colour,
not the delay. It is operating-system chrome. lib/tooltip.js moves every title
to data-tip and draws a rounded bubble instead. Coverage was also patchy: 125
buttons across the templates, 33 with a tooltip, and the export, music and
image drawers had none at all.

Suppressed on coarse pointers on purpose. There is no hover on a phone, so a
"tooltip" there fires on tap and covers the control you just pressed.

HINTS. A tooltip says what a control is. Some things need "and here is how you
drive it", which is too long to hover over and wanted only once. Magnify is the
case that prompted it: the button zooms the CENTRE, and aiming it needs scroll
or space-drag, documented only in the help drawer under a separate heading.

Shown once ever, with an off switch. Turning them back on also forgets what has
been seen — otherwise the switch silently does nothing for anyone who already
dismissed them, which is a setting that lies.
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

    for surface, path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        print(f"\nTOOLTIPS — {surface}")
        pg = b.new_page(viewport={"width": 1200, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1400)
        check(f"{surface} loads with no JS errors", not errs, "; ".join(errs[:2]))

        # Leaving title in place shows BOTH tooltips, ours immediately and the
        # browser's a second later, stacked on top of each other.
        check(f"{surface}: no native title attributes remain",
              pg.evaluate("() => document.querySelectorAll('[title]').length") == 0,
              "both tooltips would show: ours at once, the browser's a second later")
        n = pg.evaluate("() => document.querySelectorAll('[data-tip]').length")
        check(f"{surface}: tooltips were adopted", n > 20, f"only {n}")

        pg.hover("#magnifyBtn" if surface == "Flip" else "#menuBtn")
        pg.wait_for_timeout(700)
        check(f"{surface}: hovering shows a tooltip", pg.is_visible(".skribl-tip"))
        radius = pg.evaluate("() => { const t = document.querySelector('.skribl-tip');"
                             " return t ? getComputedStyle(t).borderTopLeftRadius : '0px'; }")
        check(f"{surface}: the tooltip has rounded corners",
              radius not in ("0px", "", None), radius)
        box = pg.evaluate("() => { const t = document.querySelector('.skribl-tip');"
                          " const r = t.getBoundingClientRect();"
                          " return { l: r.left, r: r.right, t: r.top, b: r.bottom }; }")
        check(f"{surface}: the tooltip stays inside the window",
              box["l"] >= 0 and box["r"] <= 1200 and box["t"] >= 0 and box["b"] <= 900,
              str(box))
        pg.close()

    print("\nTOOLTIPS — the drawers that had none now have some")
    pg = b.new_page(viewport={"width": 1200, "height": 900})
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1400)
    for _id in ("exportPng", "exportGif", "zoomInBtn"):
        check(f"#{_id} has a tooltip",
              pg.evaluate(f"() => !!(document.getElementById('{_id}')"
                          f" && document.getElementById('{_id}').getAttribute('data-tip'))"),
              "the export and zoom controls had no tooltips at all")
    check("the magnify tooltip explains how to aim it",
          "space" in (pg.get_attribute("#magnifyBtn", "data-tip") or "").lower(),
          pg.get_attribute("#magnifyBtn", "data-tip"))

    print("\nTOOLTIPS — coverage, counted rather than assumed")
    # THE ACTUAL BUG. The first pass was keyed by element id, and the two
    # surfaces name the SAME controls differently — Flip has musicBtn/imageBtn,
    # Pad has musicOpenBtn/imageOpenBtn — so Flip got tooltips and Pad got
    # none. Two more (addcopy, addblank) are built in flip.js, not the
    # template, so no template-wide pass could reach them at all.
    #
    # A list of ids to check would have the same blind spot as the pass that
    # created the gap. This COUNTS what is on screen instead.
    # ICON-ONLY controls only. A tooltip on a button that already reads "Save
    # draft" or "Transparent" is noise, and noise is what makes people stop
    # reading tooltips at all — the opposite of the goal. The contract is: if a
    # control shows no words, it must say what it does on hover.
    MISSING = """() => {
      const out = [];
      document.querySelectorAll('button, a[href], input[type=range]').forEach(el => {
        if (el.getAttribute('data-tip')) return;
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return;
        // Visible text of its own is a label; a tooltip would just repeat it.
        const text = (el.textContent || '').replace(/\s+/g, '');
        if (text.length > 0) return;
        out.push(el.id || el.getAttribute('aria-label') || '(unnamed icon button)');
      });
      return out;
    }"""
    for _surface, _path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        cp = b.new_page(viewport={"width": 1200, "height": 900})
        cp.goto(BASE + _path, wait_until="load")
        cp.wait_for_timeout(1400)
        missing = cp.evaluate(MISSING)
        check(f"{_surface}: every icon-only control has a tooltip",
              not missing, "no tooltip on: " + ", ".join(missing[:8]))

        # Open the drawers too — most controls are behind one, and checking
        # only the resting screen is how the drawers ended up with zero.
        cp.evaluate("""() => {
          document.querySelectorAll('.drawer, .tool-drawer, .menu-overlay')
            .forEach(d => { d.hidden = false; d.classList.add('open'); });
        }""")
        cp.wait_for_timeout(500)
        missing2 = cp.evaluate(MISSING)
        check(f"{_surface}: icon-only controls in the drawers have tooltips too",
              not missing2, "no tooltip on: " + ", ".join(missing2[:8]))
        cp.close()

    print("\nTOOLTIPS — not on touch")
    touch = b.new_context(viewport={"width": 390, "height": 844},
                          has_touch=True, is_mobile=True)
    tp = touch.new_page()
    tp.goto(f"{BASE}/flip", wait_until="load")
    tp.wait_for_timeout(1400)
    check("a coarse pointer gets no tooltip layer",
          tp.evaluate("() => !document.querySelector('.skribl-tip')"),
          "on a phone a tooltip fires on tap and covers what you pressed")
    tp.close()
    touch.close()

    print("\nHINTS — once, and only once")
    hp = b.new_page(viewport={"width": 1100, "height": 900})
    hp.goto(f"{BASE}/flip", wait_until="load")
    hp.wait_for_timeout(1400)
    hp.click("#magnifyBtn")
    hp.wait_for_timeout(500)
    check("enabling magnify shows the hint", hp.is_visible(".skribl-hint"))
    check("and it says how to move around",
          "space" in hp.inner_text(".skribl-hint").lower(),
          hp.inner_text(".skribl-hint"))

    def shown():
        return hp.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                           " return !!h && h.classList.contains('in'); }")

    hp.reload(wait_until="load")
    hp.wait_for_timeout(1400)
    hp.click("#magnifyBtn")
    hp.wait_for_timeout(600)
    check("it does NOT show a second time", not shown(),
          "a hint that reappears is an interruption")

    hp.evaluate("() => window.SkriblHints.reset()")
    hp.reload(wait_until="load")
    hp.wait_for_timeout(1400)
    hp.click("#magnifyBtn")
    hp.wait_for_timeout(600)
    check("turning tips back on shows it again", shown(),
          "a toggle that silently does nothing is a setting that lies")

    hp.evaluate("() => { window.SkriblHints.reset(); window.SkriblHints.setEnabled(false); }")
    hp.reload(wait_until="load")
    hp.wait_for_timeout(1400)
    hp.click("#magnifyBtn")
    hp.wait_for_timeout(600)
    check("with tips off, nothing is shown", not shown())

    print("\nHINTS — the toggle is reachable and reflects its state")
    # Open through openMenu(), not by unhiding the node: the toggle re-reads
    # the stored state on open, which is the behaviour being checked.
    hp.evaluate("() => window.SkriblHints.reset()")
    hp.click("#moreBtn")
    hp.wait_for_timeout(400)
    check("the Tips toggle is in the menu", hp.is_visible("#hintSeg"))
    check("it shows On while hints are enabled",
          hp.evaluate("() => document.querySelector"
                      "(\"#hintSeg button[data-hints='on']\").classList.contains('on')"),
          "the switch does not show its own state")
    hp.click("#hintSeg button[data-hints='off']")
    hp.wait_for_timeout(300)
    check("tapping Off disables hints",
          hp.evaluate("() => window.SkriblHints.isEnabled()") is False)
    check("and the switch moves to Off",
          hp.evaluate("() => document.querySelector"
                      "(\"#hintSeg button[data-hints='off']\").classList.contains('on')"))
    print("\nHINTS — one setting, surfaced on both editors")
    # It is the SAME setting, not two. lib/hints.js stores it under one key for
    # the whole app, so off on Pad is off on Flip. Both surfaces show the
    # control because a user on Pad should not have to open Flip to reach it —
    # and two switches over one setting is only confusing if they can disagree.
    ctx = b.new_context(viewport={"width": 1100, "height": 900})
    fp = ctx.new_page()
    fp.goto(f"{BASE}/flip", wait_until="load")
    fp.wait_for_timeout(1400)
    fp.click("#moreBtn")
    fp.wait_for_timeout(400)

    heights = fp.evaluate("() => ({"
                          " tips: document.getElementById('hintSeg').getBoundingClientRect().height,"
                          " canvas: document.getElementById('canvasSeg').getBoundingClientRect().height })")
    check("the Tips and Canvas switches are the same height",
          abs(heights["tips"] - heights["canvas"]) < 1.5,
          f"tips {heights['tips']} vs canvas {heights['canvas']} — two segmented "
          "controls stacked at different heights read as a mistake")

    fp.click("#hintSeg button[data-hints='off']")
    fp.wait_for_timeout(300)
    check("turning tips off on Flip stores it",
          fp.evaluate("() => window.SkriblHints.isEnabled()") is False)

    pd = ctx.new_page()
    pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    pd.wait_for_timeout(1400)
    pd.click("#menuBtn")
    pd.wait_for_timeout(400)
    check("the Tips control is in Pad's menu too", pd.is_visible("#hintSeg"),
          "a user on Pad would have to open Flip to turn tips off")
    check("Pad reads OFF because Flip set it",
          pd.evaluate("() => document.querySelector"
                      "(\"#hintSeg button[data-hints='off']\").classList.contains('on')"),
          "the two switches disagree — that IS the confusing version")
    check("and Pad agrees with the stored value",
          pd.evaluate("() => window.SkriblHints.isEnabled()") is False)

    # Pad's magnifier centres exactly as Flip's does, so it earns the same hint
    # — under the same key, so learning it once is learning it everywhere.
    pd.evaluate("() => { window.SkriblHints.reset(); }")
    pd.reload(wait_until="load")
    pd.wait_for_timeout(1400)
    pd.click("#magnifyBtn")
    pd.wait_for_timeout(500)
    check("Pad shows the magnify hint too", pd.is_visible(".skribl-hint"),
          "Pad's magnifier centres the same way and said nothing about it")

    fp2 = ctx.new_page()
    fp2.goto(f"{BASE}/flip", wait_until="load")
    fp2.wait_for_timeout(1400)
    fp2.click("#magnifyBtn")
    fp2.wait_for_timeout(500)
    check("and Flip does NOT teach it again after Pad did",
          fp2.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                       " return !(h && h.classList.contains('in')); }"),
          "the same lesson twice, once per surface")
    ctx.close()

    hp.close()
    b.close()

summarise_and_exit()
