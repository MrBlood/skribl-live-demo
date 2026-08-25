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


def dismiss_intro(page):
    """Clear the v204 Flip intro toast (key 'flip-intro') and any visible hint.

    That toast fires once on Flip load; these per-hint tests target OTHER hints
    (magnify, page-move), so the intro must be out of the way — dismissed AND
    marked seen — or it sits in front of the hint under test. Marking it seen
    (not a blanket reset) preserves whatever else the test has set up.
    """
    page.evaluate("""() => {
        try {
            var raw = localStorage.getItem('skribl_hints_seen_v1');
            var o = raw ? JSON.parse(raw) : {};
            o['flip-intro'] = 1;
            localStorage.setItem('skribl_hints_seen_v1', JSON.stringify(o));
        } catch (e) {}
        var h = document.querySelector('.skribl-hint');
        if (h) { h.classList.remove('in'); h.hidden = true; }
    }""")


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

        # '#imageBtn' on Flip, NOT '#magnifyBtn'. This suite hovered a control
        # that does not exist on that surface and hung for 30s waiting for it.
        # v219 restored Magnify to PAD's toolbar at 641px+ ("a phone has pinch,
        # a mouse has nothing") and Flip's toolbar was reordered without one, so
        # `#magnifyBtn` is in skribl_editor.html only; flip.js still binds it
        # defensively behind `if(magnifyBtn)`, which is why nothing else noticed.
        #
        # Whether Flip SHOULD have a desktop magnify is a live product question
        # by v219's own argument, and it is flagged rather than answered here —
        # a tooltip suite is not the place to decide it. This assertion is about
        # tooltips, so it hovers any real tooltip-bearing control on the surface.
        # v224: #imageBtn is gone -- image and music merged into #mediaOpenBtn,
        # which both surfaces now carry and which has a title of its own.
        pg.hover("#mediaOpenBtn" if surface == "Flip" else "#menuBtn")
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
    # Magnify lives on PAD only — see the note at the hover assertion above — so
    # this is checked on the surface that has it rather than on Flip, where the
    # locator hung for 30s waiting for a button that is not in the template.
    _pgp = b.new_page(viewport={"width": 1200, "height": 900})
    _pgp.goto(f"{BASE}/skribl-pad", wait_until="load")
    _pgp.wait_for_timeout(1400)
    _mag = _pgp.get_attribute("#magnifyBtn", "data-tip")
    check("the magnify tooltip explains how to aim it",
          "space" in (_mag or "").lower(), _mag)
    _pgp.close()

    print("\nTOOLTIPS — coverage, counted rather than assumed")
    # THE ACTUAL BUG. The first pass was keyed by element id, and the two
    # surfaces name the SAME controls differently — Flip had musicBtn/imageBtn,
    # Pad had musicOpenBtn/imageOpenBtn — so Flip got tooltips and Pad got
    # none. (v224 merged all four into one #mediaOpenBtn shared by both, which
    # removes this particular divergence but not the lesson.) Two more (addcopy, addblank) are built in flip.js, not the
    # template, so no template-wide pass could reach them at all.
    #
    # A list of ids to check would have the same blind spot as the pass that
    # created the gap. This COUNTS what is on screen instead.
    # ICON-ONLY controls only. A tooltip on a button that already reads "Save
    # draft" or "Transparent" is noise, and noise is what makes people stop
    # reading tooltips at all — the opposite of the goal. The contract is: if a
    # control shows no words, it must say what it does on hover.
    MISSING = r"""() => {
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
    # PAD, not Flip: this whole block drives #magnifyBtn, which is in Pad's
    # template only (see the note at the first hover assertion). It ran against
    # /flip and hung. The hint machinery it tests is shared, so moving the
    # surface changes nothing it is asserting.
    hp = b.new_page(viewport={"width": 1100, "height": 900})
    hp.goto(f"{BASE}/skribl-pad", wait_until="load")
    hp.wait_for_timeout(1400)
    dismiss_intro(hp)                 # v204 Flip intro toast is not what this tests
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

    print("\nHINTS — the page-move hint, and where a hint sits")
    # Below 560px the pagebar labels are hidden, so Move is two bare arrows in a
    # row that also reads "Page 62 / 64" — they look like navigation while they
    # REORDER the animation. A page glyph was tried and reverted: at 11px a
    # rounded rect renders as a zero. A hint says it once, when it happens.
    mp = b.new_page(viewport={"width": 390, "height": 844})
    mp.goto(f"{BASE}/flip", wait_until="load")
    mp.wait_for_timeout(1300)
    mp.evaluate("() => window.SkriblHints.reset()")
    dismiss_intro(mp)                 # reset re-arms flip-intro; this tests page-move
    mp.evaluate("() => { addFrame(true); addFrame(true); }")
    mp.wait_for_timeout(400)
    mp.click("#pbLeft")
    mp.wait_for_timeout(450)
    check("moving a page explains what the arrows do", mp.is_visible(".skribl-hint"))
    _txt = mp.inner_text(".skribl-hint").lower()
    check("the hint says the arrows REORDER", "reorder" in _txt, _txt)
    check("and points at the thumbnails for changing page",
          "thumbnail" in _txt, _txt)

    # It must not cover the filmstrip it just told you to tap. At bottom:96px
    # it landed squarely on the strip — Flip's bottom chrome is ~230px tall and
    # Pad's is ~90, so no single bottom offset clears both.
    _overlap = mp.evaluate("""() => {
      const h = document.querySelector('.skribl-hint').getBoundingClientRect();
      const s = document.querySelector('.strip-wrap, #strip');
      if (!s) return null;
      const r = s.getBoundingClientRect();
      return !(h.bottom < r.top || h.top > r.bottom);
    }""")
    check("the hint does not cover the filmstrip", _overlap is False,
          "it covers the thumbnails it tells you to tap")
    mp.close()

    print("\nHINTS — the toggle is reachable and reflects its state")
    # Open through openMenu(), not by unhiding the node: the toggle re-reads
    # the stored state on open, which is the behaviour being checked.
    hp.evaluate("() => window.SkriblHints.reset()")
    # '#menuBtn, #moreBtn' — the overflow menu is #menuBtn on Pad and #moreBtn on
    # Flip. That is the exact id divergence this file's own coverage comment
    # describes (musicBtn/musicOpenBtn), and it bit here the moment this block
    # moved to Pad. `fp` below stays on #moreBtn because it really is on Flip.
    hp.locator("#menuBtn, #moreBtn").first.click()
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
    widths = fp.evaluate("() => ({"
                         " tips: document.getElementById('hintSeg').getBoundingClientRect().width,"
                         " canvas: document.getElementById('canvasSeg').getBoundingClientRect().width,"
                         " gap: document.getElementById('hintSeg').getBoundingClientRect().left"
                         "      - document.querySelectorAll('.flip-menu-row .fm-label')[0]"
                         "        .getBoundingClientRect().right })")
    check("the Tips and Canvas switches are the same width",
          abs(widths["tips"] - widths["canvas"]) < 2,
          f"tips {round(widths['tips'])} vs canvas {round(widths['canvas'])}")
    # Two right-aligned switches of different widths left a 99px hole after the
    # word "Tips" while "Canvas" sat snug against its own.
    check("the Tips label is not stranded from its switch",
          widths["gap"] < 48, f"{round(widths['gap'])}px gap")

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
    # Flip shows a one-time intro toast on load (v204, key 'flip-intro'), a
    # DIFFERENT hint than magnify-pan. Dismiss it and assert on the magnify
    # TEXT — the intent is that magnify-pan is not taught twice across
    # surfaces, not that Flip is silent on load.
    dismiss_intro(fp2)
    # Flip has no #magnifyBtn to click — Magnify is on Pad's toolbar only (see
    # the note at the first hover assertion). Its magnify HINT code is still
    # there: flip.js calls SkriblHints.show('magnify-pan', ...) exactly as app.js
    # does. So this drives the mechanism the assertion is actually about — the
    # shared seen-key — instead of a button that is not on the page. If the key
    # were per-surface rather than shared, this show() would display the hint and
    # the check below would fail, which is the regression it exists to catch.
    fp2.evaluate("() => window.SkriblHints.show('magnify-pan',"
                 " 'Zoom centres — scroll or hold Space and drag to aim it.')")
    fp2.wait_for_timeout(500)
    check("and Flip does NOT teach it again after Pad did",
          fp2.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                       " return !(h && h.classList.contains('in')"
                       " && /magnif|zoom|scroll|space/i.test(h.textContent)); }"),
          "the same lesson twice, once per surface")
    ctx.close()

    hp.close()
    b.close()

summarise_and_exit()
