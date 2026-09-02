"""v226/v228 — one size decision, made once, where a rule can refer to it.

WHY. `flip.css` carried eight `max-width` rules — 359, 360, 392, 400, 440, 559,
560, 640 — and `styles.css` has its own set. That is not a responsive design; it
is eight patches, each correct on the day it was written, none of them agreeing
about where "small" begins. The visible cost is in this project's own review
notes: **one pixel of resize takes Pad's toolbar from 398px to 565px**, and
560–640px gets the phone layout on a viewport with room to spare.

WHAT v226 WAS, AND WHAT v228 FINISHED. v226 was not the migration; it was the
thing the migration migrates TO — one question, one attribute, one query moved
across as proof the boundary was identical. v228 moved the rest of the BOUNDARY
queries, which is a smaller claim than "replaced the breakpoints" and worth
stating precisely: the rules that decided where compact BEGINS are gone, and
seven tiers strictly below it remain, because how a row keeps fitting inside
compact is a different question from where compact starts.

WHY THAT DISTINCTION EARNS ITS KEEP. Until v228 this suite asserted only that
SOME max-width queries survived — true of a migration 1/8 done and equally true
of one 7/8 done, and blind to the thing that actually hurt: the queries left
behind DISAGREED with the class. Three boundaries ran at once and a window from
641 to 660 hid the page bar while sizing the tool row for desktop. The check
that replaces it is structural rather than a count — nothing at or above the
boundary, so a query cannot reach the class's edge to contradict it.

THE PART WORTH TESTING HARDEST is that the migration was a NO-OP. The class is
defined at the same 640px the query used, so a rule keyed off it must produce
the same layout on both sides of the boundary as the media query did. If that
is not exactly true, the refactor smuggled in a design change.

It measures the ELEMENT, not the viewport, which is a real difference: Skribl is
a blueprint a host mounts, possibly beside its own chrome. The assertions below
cover both — the pure classifier at its boundary, and the live attribute at real
viewport widths.
"""
import os
import re
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                    # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(400)

        print("\nTHE DECISION — one threshold, named once")
        check("lib/sizeclass.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblSize") == "object",
              "a lib the template does not list is a lib that does not exist")
        check("the threshold is a named constant, not a literal in a rule",
              page.evaluate("() => SkriblSize.COMPACT_MAX") == 640,
              "changing what 'compact' means must be one edit, not eight")

        # The classifier is pure, so its boundary can be checked exactly —
        # including the fractional case a real layout produces and a media query
        # would round. 640 is compact because `max-width: 640px` included it.
        grid = page.evaluate("""() => {
          const S = window.SkriblSize;
          return [0, 320, 639, 640, 640.4, 641, 1280].map(w => [w, S.classify(w)]);
        }""")
        want = [[0, "compact"], [320, "compact"], [639, "compact"],
                [640, "compact"], [640.4, "regular"], [641, "regular"],
                [1280, "regular"]]
        check("the boundary matches the query it replaces, to the fraction",
              grid == want, str(grid))

        print("\nTHE STAMP — CSS and JS are told on the same frame")
        check("a wide window classifies as regular",
              page.evaluate("() => document.body.getAttribute('data-size')") == "regular"
              and page.evaluate("() => SkriblSize.get()") == "regular",
              page.evaluate("() => document.body.getAttribute('data-size')"))
        page.set_viewport_size({"width": 480, "height": 900})
        page.wait_for_timeout(250)
        check("narrowing restamps the root",
              page.evaluate("() => document.body.getAttribute('data-size')") == "compact")
        check("...and the JS answer agrees with the attribute",
              page.evaluate("() => SkriblSize.get()") == "compact"
              and page.evaluate("() => SkriblSize.isCompact()") is True,
              "a script and a stylesheet disagreeing is how a control ends up "
              "hidden by CSS with its keyboard handler still live")

        # The event is the seam anything non-CSS listens on, so it is exercised
        # rather than assumed. Installed BEFORE the resize that should fire it.
        page.evaluate("""() => {
          window.__sizeEvents = [];
          document.addEventListener('skribl:size',
            e => window.__sizeEvents.push(e.detail.size));
        }""")
        page.set_viewport_size({"width": 1100, "height": 900})
        page.wait_for_timeout(250)
        check("widening restamps it back",
              page.evaluate("() => document.body.getAttribute('data-size')") == "regular")
        check("...and announces the change on skribl:size",
              page.evaluate("() => window.__sizeEvents") == ["regular"],
              str(page.evaluate("() => window.__sizeEvents")))
        # One write per real change: a ResizeObserver fires on every pixel of a
        # drag, and re-stamping on each would thrash the attribute every rule in
        # the app keys off.
        page.evaluate("() => { window.__sizeEvents.length = 0; }")
        for w in (1150, 1200, 1250):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
        check("resizing WITHIN a class announces nothing",
              page.evaluate("() => window.__sizeEvents") == [],
              str(page.evaluate("() => window.__sizeEvents"))
              + " — one write per real change, not per pixel")

        print("\nTHE CONTAINER, NOT THE WINDOW — v227, deliberately")
        # The host site reserves a COLUMN for Pad and Flip, around 510px. Inside
        # a wide window that is the case that decides how this measures: a
        # viewport reading would say `regular` and lay a persistent command row
        # into a space that cannot hold one. Simulated by narrowing the ROOT
        # while the window stays wide, which is exactly the embedded shape.
        page.set_viewport_size({"width": 1400, "height": 900})
        page.wait_for_timeout(200)
        check("a wide window on its own is regular",
              page.evaluate("() => document.body.getAttribute('data-size')") == "regular")
        page.evaluate("() => { document.body.style.width = '510px'; }")
        page.wait_for_timeout(250)
        check("A 510px COLUMN IN A 1400px WINDOW IS COMPACT",
              page.evaluate("() => document.body.getAttribute('data-size')") == "compact",
              "viewport measurement would say regular here and break the layout")
        page.evaluate("() => { document.body.style.width = ''; }")
        page.wait_for_timeout(250)
        check("...and releasing the column returns it to regular",
              page.evaluate("() => document.body.getAttribute('data-size')") == "regular")

        print("\nTHE COST OF THAT, ASSERTED RATHER THAN DISCOVERED")
        # getBoundingClientRect excludes the scrollbar, so the element-measured
        # boundary sits a scrollbar-width below the viewport one. That band is
        # taken knowingly; pinning it means nobody meets it as a surprise.
        band = page.evaluate("""() => {
          const w = window.innerWidth, b = document.body.getBoundingClientRect().width;
          return { viewport: w, element: Math.round(b), gap: Math.round(w - b) };
        }""")
        check("the element is narrower than the window by the scrollbar",
              band["gap"] >= 0, str(band))

        print("\nTHE MIGRATED RULE still breaks where the class does")
        for w, expect in ((700, "compact-off"), (600, "compact-on")):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(220)
            got = page.evaluate("""() => {
              const el = document.querySelector('.flip-app .header .actions');
              return el ? getComputedStyle(el).marginLeft : null;
            }""")
            size = page.evaluate("() => document.body.getAttribute('data-size')")
            if expect == "compact-on":
                check(f"at {w}px the rule applies",
                      size == "compact" and got not in (None, "0px"),
                      f"data-size={size}, margin-left={got}")
            else:
                check(f"at {w}px it does not",
                      size == "regular", f"data-size={size}, margin-left={got}")

        # The MIGRATED rule specifically must no longer live inside a media
        # query. Not "no 640px query exists" — three others remain in this file
        # and moving them is later work; asserting their absence would make this
        # suite fail for the honest reason that the migration is incremental.
        still_queried = page.evaluate("""() => {
          const l = [...document.styleSheets].find(s =>
            (s.href || '').includes('flip.css'));
          if (!l) return 'stylesheet not found';
          try {
            return [...l.cssRules]
              .filter(r => r.conditionText)
              .flatMap(r => [...(r.cssRules || [])])
              .filter(r => (r.selectorText || '').includes('.header .actions'))
              .map(r => r.selectorText).join(' | ');
          } catch (e) { return 'unreadable: ' + e.message; }
        }""")
        check("the migrated rule no longer lives in a media query",
              still_queried == "",
              f"still inside one: {still_queried!r} — two routes to one decision "
              "is the thing being removed")

        print("\nHONEST SCOPE — what has NOT moved yet")
        left = page.evaluate("""() => {
          const l = [...document.styleSheets].find(s =>
            (s.href || '').includes('flip.css'));
          if (!l) return -1;
          try {
            return [...l.cssRules].filter(r => r.media || r.conditionText)
              .filter(r => (r.conditionText || '').includes('max-width')).length;
          } catch (e) { return -1; }
        }""")
        check("flip.css still has max-width queries, and this suite says so",
              left > 0,
              f"{left} remain — migrating them is incremental work with "
              "verify_layout as the net, not a claim this step makes")


        print("\nTHE BAND IS CLOSED — v228, the migration finished")
        # WHAT WENT WRONG, AND WHY A PASSING SUITE DID NOT SAY SO. Until v228
        # this file asserted only that SOME max-width queries remained, which is
        # true of a migration that is 1/8 done and equally true of one that is
        # 7/8 done. It could not see that the queries left behind DISAGREED with
        # the class. Three boundaries were live at once: the class at body>640,
        # `min-width:641` on the viewport, and `min-width:645` on the viewport.
        # Between them, a standalone window from 641 to 660 hid the page bar
        # (compact, by class) while sizing the tool row 44px (regular, by query)
        # — the compact surface with the desktop toolbar. Measured, not guessed:
        # 7 of 29 probed widths differed before the fix and 0 differ after.
        #
        # The structural fix is below, and it is what makes the band unable to
        # reopen: every REMAINING width query is strictly BELOW the boundary, so
        # a query can only ever refine the layout INSIDE compact. It cannot
        # contradict the class, because it cannot reach the class's edge.
        rules = page.evaluate("""() => {
          const l = [...document.styleSheets].find(s =>
            (s.href || '').includes('flip.css'));
          if (!l) return null;
          const out = [];
          const walk = (list) => { for (const r of list) {
            const c = r.conditionText || '';
            if (/(min|max)-width/.test(c)) out.push(c);
            if (r.cssRules) walk(r.cssRules);
          } };
          try { walk(l.cssRules); } catch (e) { return null; }
          return out;
        }""")
        check("flip.css's width queries are readable", rules is not None,
              "same-origin sheet; if this ever returns null the checks below go vacuous")

        MAXC = page.evaluate("() => SkriblSize.COMPACT_MAX")
        straddle = []
        for c in (rules or []):
            for kind, px in re.findall(r"(min|max)-width:\s*(\d+)px", c):
                # max-width:640 IS the boundary; min-width:641 is its other half.
                # Either one is a second opinion about where compact ends.
                if (kind == "max" and int(px) >= MAXC) or (kind == "min" and int(px) > MAXC):
                    straddle.append(c)
        check("no width query straddles the boundary any more",
              not straddle,
              f"{straddle} — a query at or above {MAXC} is a SECOND answer to the "
              "question the size class exists to answer once")
        check("and queries below it survive, so this is a narrowing not a purge",
              len(rules or []) > 0,
              f"{len(rules or [])} remain — they refine WITHIN compact, which is "
              "a different question from where compact begins")

        print("\nTHE CASCADE DID NOT MOVE — :where() carries no specificity")
        # THE HAZARD THIS PINS. flip.css resolves its phone ladder by SOURCE
        # ORDER at equal specificity; flip.css says so in a comment at the
        # max-640 block, which is later in the file than the max-560 and max-392
        # tiers and beats them for exactly that reason. Prefixing those rules
        # with a bare `[data-size]` would have raised them to (0,2,0) and let
        # them win everywhere, silently flattening the ladder on phones. The
        # prefix is `:where(...)`, which contributes ZERO, so source order still
        # decides. These widths are the ladder's rungs: if the specificity ever
        # rises, the 640 block wins and every rung below reads 3px.
        for vw, want in ((320, "2px"), (360, "3px"), (400, "3px"), (600, "3px")):
            page.set_viewport_size({"width": vw, "height": 900})
            page.wait_for_timeout(90)
            got = page.evaluate(
                "() => getComputedStyle(document.querySelector('.flip-tools')).gap")
            check(f"the phone ladder still steps at {vw}px", got == want,
                  f"gap={got}, want {want} — a flattened ladder means the migrated "
                  "rules outrank the tiers they used to lose to")

        print("\nTHE SURFACES AGREE — no width shows one and lays out the other")
        # The band walked directly. The page bar is the CLASS's surface and the
        # tool row was the QUERY's; where they disagreed, one was compact and
        # the other regular AT THE SAME WIDTH. Now they are read from the same
        # attribute, so this walks the old band and demands they match.
        for vw in (600, 639, 641, 645, 650, 660, 665, 700, 900):
            page.set_viewport_size({"width": vw, "height": 900})
            page.wait_for_timeout(90)
            st = page.evaluate("""() => ({
              size: document.body.getAttribute('data-size'),
              bar:  getComputedStyle(document.querySelector('#pagebar')).display,
              btn:  getComputedStyle(document.querySelector('.flip-tools .t-btn')).width,
            })""")
            compact = st["size"] == "compact"
            check(f"at {vw}px the bar and the tool row tell the same story",
                  (st["bar"] == "none") == compact and (st["btn"] == "36px") == compact,
                  f"data-size={st['size']}, #pagebar={st['bar']}, t-btn={st['btn']}")

        page.set_viewport_size({"width": 1280, "height": 900})
        check("no page error at any width", not errs, "; ".join(errs[:2]))
    finally:
        br.close()


# ============================================================================
# THE GLYPHS IN THE ACTION BARS ARE BIG ENOUGH TO READ
#
# Reported from the live demo: "those icons are so small. Do they have to be so
# small?" They did not. Measured before the change: 13x13 inside a 38x38 button
# -- over 12px of empty padding on every side -- and the same 13px at EVERY
# width, while the tool tray beside it draws at 21px.
#
# WIDTH WAS NEVER THE CONSTRAINT, which is the part worth pinning: at 430px the
# six selection-bar buttons used 228 of 410px, and at 320px 198 of 300. So the
# assertions below check three separate things, because fixing one at the cost
# of another is the likely regression:
#
#   * the glyph is drawn large enough to recognise;
#   * the 44px tap band --tap-grow builds is UNCHANGED (a bigger drawing must
#     not have come out of the button box);
#   * the bar still fits on one row at the narrowest width.
# ============================================================================
print("\nGLYPH SIZE — the action bars are readable, still 44px, still one row")
with sync_playwright() as _gp:
    _gb = _gp.chromium.launch()
    try:
        for _w in (320, 390, 430, 900):
            gp = _gb.new_page(viewport={"width": _w, "height": 900})
            gp.goto(BASE + "/flip", wait_until="load")
            gp.wait_for_timeout(1200)
            gp.evaluate("() => setTool('pen')")
            gbox = gp.eval_on_selector(
                "#pad", "e => { const r = e.getBoundingClientRect();"
                " return { x: r.x, y: r.y }; }")
            gp.mouse.move(gbox["x"] + 30, gbox["y"] + 40)
            gp.mouse.down()
            for i in range(1, 10):
                gp.mouse.move(gbox["x"] + 30 + i * 10, gbox["y"] + 40 + i * 5)
            gp.mouse.up()
            gp.wait_for_timeout(250)
            gp.evaluate("() => setTool('select')")
            gp.mouse.move(gbox["x"] + 15, gbox["y"] + 25)
            gp.mouse.down()
            for i in range(1, 10):
                gp.mouse.move(gbox["x"] + 15 + i * 13, gbox["y"] + 25 + i * 7)
            gp.mouse.up()
            gp.wait_for_timeout(500)

            m = gp.evaluate(
                "() => { const bar = document.getElementById('selbar');"
                " const bs = [...bar.querySelectorAll('.pb')].filter(x => x.offsetParent);"
                " const tops = new Set(bs.map(x => Math.round("
                "   x.getBoundingClientRect().top)));"
                " const b = document.getElementById('sbStamp');"
                " const g = b.querySelector('svg');"
                " const grow = parseFloat(getComputedStyle(b)"
                "   .getPropertyValue('--tap-grow')) || 0;"
                " const r = b.getBoundingClientRect();"
                " let used = 0; bs.forEach(x => used += x.getBoundingClientRect().width);"
                " return { rows: tops.size,"
                "          glyph: Math.round(g.getBoundingClientRect().width),"
                "          tapW: Math.round(r.width + grow * 2),"
                "          tapH: Math.round(r.height + grow * 2),"
                "          used: Math.round(used),"
                "          bar: Math.round(bar.getBoundingClientRect().width) }; }")

            check(f"@{_w}: the selection-bar glyph is big enough to read",
                  m["glyph"] >= 16,
                  f"{m['glyph']}px — it shipped at 13 inside a 38px button while "
                  "the tool tray beside it drew at 21")
            check(f"@{_w}: ...and the 44px tap band is untouched",
                  m["tapW"] >= 44 and m["tapH"] >= 44,
                  f"{m['tapW']}x{m['tapH']} — a bigger drawing must not have been "
                  "paid for out of the button box")
            check(f"@{_w}: ...and the bar is still one row",
                  m["rows"] == 1,
                  f"{m['rows']} rows, {m['used']}/{m['bar']}px used — the room was "
                  "always there, and it has to stay there")
            gp.close()
    finally:
        _gb.close()


# ============================================================================
# SLIDERS ARE GRABBABLE, AND GROWING THEM MOVED NOTHING
#
# They shipped 22px tall against Apple's 44pt minimum -- half. A range input
# cannot use the --tap-grow ::before the buttons use, because pseudo-elements do
# not render on <input>, so the element itself is 44 and negative margins hand
# the 22 back to the flow. Two things therefore have to hold at once, and each
# is the other's likely regression: the box that receives a press is 44, and
# the space the control occupies is still 22.
#
# FOUR SLIDERS ARE DELIBERATELY LEFT SHORT and carry .slider-tight. A 44px box
# on those overlaps a neighbouring control -- photoZoom vs Reposition by 11px,
# shapeSides vs Corners by 5-7, shapeSides vs the kind buttons by 1-7 -- and
# where two hit areas overlap the winner is DOM order, so growing them would
# move a tap target rather than enlarge it. They are pinned here so the
# exception stays a decision instead of becoming an oversight.
# ============================================================================
# THE BAND SAMPLER, shared by every hit check below rather than pasted into
# each one. A 44px BOX IS NOT A 44px TARGET: size alone says nothing about who
# receives the press. For each id it samples a 3x3 grid across the band the
# control WOULD have at 44 -- so a still-tight 22px slider is measured over the
# 44 it is not using -- and asks elementFromPoint who would get each tap.
HIT_JS = (
"(ids) => { const out = {};"
                " for (const id of ids) {"
                "   const s = document.getElementById(id);"
                "   if (!s) { out[id] = null; continue; }"
                "   const r = s.getBoundingClientRect();"
                "   if (!r.height) { out[id] = null; continue; }"
                "   const pad = Math.max(0, (44 - r.height) / 2);"
                "   const xs = [r.left + 8, r.left + r.width / 2, r.right - 8];"
                "   const ys = [r.top - pad + 1, r.top + r.height / 2,"
                "               r.bottom + pad - 1];"
                "   let mine = 0, total = 0; const steal = {};"
                "   for (const y of ys) for (const x of xs) {"
                "     const el = document.elementFromPoint(x, y); total++;"
                "     if (!el) { mine++; continue; }"
                "     if (el === s || s.contains(el) || el.contains(s)) { mine++; continue; }"
                "     const act = el.closest('button,input,a,[role=button]');"
                "     if (!act) { mine++; continue; }"
                "     const k = act.id || act.className.toString().trim().split(/\\s+/)[0]"
                "               || act.tagName;"
                "     steal[k] = (steal[k] || 0) + 1; }"
                "   out[id] = { mine, total, steal }; }"
                " return out; }"
)

print("\nSLIDERS — 44px of grab, 22px of layout, and four measured exceptions")
_knob_look = {}
with sync_playwright() as _sl:
    _slb = _sl.chromium.launch()
    try:
        for _path, _name, _ctl in (("/flip", "Flip", "_flipDrawerCtl"),
                                   ("/", "Pad", "_padDrawerCtl")):
            lp = _slb.new_page(viewport={"width": 430, "height": 950})
            lp.goto(BASE + _path, wait_until="load")
            lp.wait_for_timeout(1200)
            lp.evaluate(f"() => {_ctl}.open('draw')")
            lp.wait_for_timeout(450)
            lp.evaluate("() => { setTool('shape'); shapeKind = 'poly';"
                        " syncShapeKnobs();"
                        " document.getElementById('shapePop').hidden = false; }")
            lp.wait_for_timeout(400)
            found = lp.evaluate(
                "() => [...document.querySelectorAll('input[type=range]')]"
                ".map(s => { const b = s.getBoundingClientRect();"
                "  const cs = getComputedStyle(s);"
                "  return { id: s.id, on: b.height > 0,"
                "           box: Math.round(b.height),"
                "           flow: Math.round(b.height + parseFloat(cs.marginTop)"
                "                 + parseFloat(cs.marginBottom)),"
                "           tight: s.classList.contains('slider-tight'),"
                "           cls: s.className }; })"
                ".filter(x => x.on)")
            check(f"{_name}: there are sliders laid out to check",
                  len(found) > 0, "an empty set passes everything below")
            check(f"{_name}: every slider carries the shared class",
                  all("slider" in f["cls"] for f in found),
                  str([f["id"] for f in found if "slider" not in f["cls"]]))
            grown = [f for f in found if not f["tight"]]
            tight = [f for f in found if f["tight"]]
            check(f"{_name}: a slider without the tight opt-out gives 44px of grab",
                  all(f["box"] >= 44 for f in grown),
                  str([(f["id"], f["box"]) for f in grown if f["box"] < 44])
                  + " — 22px is half the 44pt minimum")
            check(f"{_name}: ...and still occupies only 22px of layout",
                  all(f["flow"] == 22 for f in grown),
                  str([(f["id"], f["flow"]) for f in grown if f["flow"] != 22])
                  + " — the drawers already reach the bottom of a phone; a "
                  "taller control has to come out of the negative margin, not "
                  "out of the page")
            check(f"{_name}: the marked exceptions are still 22 and unmoved",
                  all(f["box"] == 22 and f["flow"] == 22 for f in tight),
                  str([(f["id"], f["box"], f["flow"]) for f in tight]))

            # A 44px BOX IS NOT A 44px TARGET. Size alone says nothing about who
            # actually receives the press: the shape knobs were grown and still
            # lost points to the kind buttons above and to each other, because
            # the rows were 6px apart. And the first fix for that went into
            # flip.css, which Pad does not load -- Flip read 9/9 while Pad read
            # 4/9, and a size check passed both. So this samples the band and
            # asks elementFromPoint who would get the tap.
            # Put any hint away first. A toast is transient and dismissible and
            # its action button legitimately takes the pointer, so leaving one up
            # measures the wrong thing -- the question here is whether the RESTING
            # layout hands each slider its own band.
            # REMOVE it, do not click it. Clicking bubbled to shapePopDismiss --
            # a click outside #shapePop closes the picker -- so Flip's two checks
            # found no rect and skipped silently while Pad's still ran. A check
            # that disappears is worse than one that fails.
            lp.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                        " if (h) h.remove(); }")
            lp.wait_for_timeout(200)
            hit = lp.evaluate(HIT_JS, ["shapeSides", "shapeRadius"])
            check(f"{_name}: both knobs are on screen for the hit test",
                  all(v is not None for v in hit.values()),
                  f"{[k for k, v in hit.items() if v is None]} had no rect — the "
                  "picker closed, so the checks below would have vanished rather "
                  "than failed")
            for _k, _v in hit.items():
                if not _v:
                    continue
                check(f"{_name}: every point across {_k}'s band reaches {_k}",
                      _v["mine"] == _v["total"],
                      f"{_v['mine']}/{_v['total']} — stolen by "
                      + (str(_v["steal"]) or "nothing")
                      + "; the row spacing lives in styles.css because BOTH "
                        "surfaces render this markup")
            # THE IMAGE DRAWER, which is where two of the four exceptions lived.
            # photoZoom and photoBlur carried .slider-tight because a 44px box on
            # them overlapped a neighbour, and the note in styles.css said the fix
            # was row spacing. v258 did that -- 22px between sliders, which is
            # exactly the two 11px overhangs, plus clearance above the first and
            # below the last -- so both now take a full band and are checked here
            # by the same elementFromPoint sampling as the shape knobs.
            #
            # WHAT THIS CAUGHT, and it was Pad-only: at 12px spacing Pad measured
            # photoZoom 6/9 (3 points taken by photoOpacity) and photoBlur 3/9
            # (3 by photoOpacity, 3 by resetPhotoBtn), while FLIP read 9/9 for
            # both. A size-only check passed both surfaces, and the surface that
            # was broken was the one nobody was looking at.
            #
            # The panel is forced open the way this suite already forces
            # #shapePop open: #photoDetail is hidden until an image is loaded,
            # and the question here is the RESTING GEOMETRY of the rows, not the
            # upload path. The "laid out to check" guard below is what stops a
            # panel that failed to open from passing everything silently.
            lp.evaluate(f"() => {_ctl}.open('photo')")
            lp.wait_for_timeout(400)
            # THE HINT STAYS HIDDEN, because that is the resting state: it is
            # display:none until Reposition is pressed. Measuring with it shown
            # was the first version of this and it tested the wrong layout --
            # with the hint present, the thing 11px above the Zoom row is a
            # paragraph, and the sampler counts a non-interactive element as
            # "mine" because no tap is stolen. Hidden, the neighbour is the
            # reposition BUTTON, which is a real pointer target. Removing the
            # clearance passed the suite in the shown state and fails in this one.
            lp.evaluate("""() => {
                const d = document.getElementById('photoDetail'); if (d) d.hidden = false;
                const z = document.getElementById('photoZoomRow'); if (z) z.hidden = false;
                const r = document.getElementById('repositionBtn'); if (r) r.hidden = false;
                const h = document.getElementById('repositionHint'); if (h) h.hidden = true; }""")
            lp.wait_for_timeout(350)
            lp.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                        " if (h) h.remove(); }")
            _photo_ids = ["photoZoom", "photoOpacity", "photoBlur"]
            _ph = lp.evaluate(HIT_JS, _photo_ids)
            check(f"{_name}: the image drawer's sliders are laid out to check",
                  all(_ph.get(i) for i in _photo_ids),
                  f"{[i for i in _photo_ids if not _ph.get(i)]} had no rect — the "
                  "panel did not open, so every check below would vanish rather "
                  "than fail")
            _pbox = lp.evaluate(
                "(ids) => ids.map(id => { const s = document.getElementById(id);"
                " if (!s) return [id, null];"
                " const r = s.getBoundingClientRect(); const cs = getComputedStyle(s);"
                " return [id, { box: Math.round(r.height),"
                "   flow: Math.round(r.height + parseFloat(cs.marginTop)"
                "         + parseFloat(cs.marginBottom)),"
                "   tight: s.classList.contains('slider-tight') }]; })", _photo_ids)
            check(f"{_name}: no image slider is still opted out of the band",
                  all(v and not v["tight"] for _, v in _pbox),
                  f"{_pbox} — .slider-tight was the marker for 'we know this one "
                  "is too small'; the spacing that made it necessary is gone")
            check(f"{_name}: each image slider gives 44px of grab for 22px of layout",
                  all(v and v["box"] >= 44 and v["flow"] == 22 for _, v in _pbox),
                  f"{_pbox} — a taller control has to come out of the negative "
                  "margin, not out of the page")
            # AND THE NEIGHBOURS KEEP THEIR OWN AREA, which is the half the
            # sampler cannot see from the slider's side. `pad` is (44 - height)/2,
            # so for a slider that is ALREADY 44 it is zero and the grid stays
            # inside the slider's own box -- the check can only ever find the
            # slider. When a band does overlap a button the slider wins, because
            # it paints later, so the control that loses points is the BUTTON.
            # That is precisely what the .slider-tight note meant by "growing
            # them would silently move a tap target rather than enlarge it", and
            # asserting it from the slider's side alone would have missed it:
            # removing the clearance above the Zoom row passed every check above
            # and fails here.
            _nb = lp.evaluate(HIT_JS, ["repositionBtn", "resetPhotoBtn"])
            for _k, _v in _nb.items():
                if not _v:
                    continue
                check(f"{_name}: {_k} keeps its own tap area",
                      _v["mine"] == _v["total"],
                      f"{_v['mine']}/{_v['total']} — stolen by "
                      + (str(_v["steal"]) or "nothing")
                      + "; a slider band that reaches into a button does not "
                        "enlarge anything, it hands the button's edge away")

            for _k in _photo_ids:
                _v = _ph.get(_k)
                if not _v:
                    continue
                check(f"{_name}: every point across {_k}'s band reaches {_k}",
                      _v["mine"] == _v["total"],
                      f"{_v['mine']}/{_v['total']} — stolen by "
                      + (str(_v["steal"]) or "nothing")
                      + f"; before the spacing, Pad read 6/9 here for photoZoom "
                        f"and 3/9 for photoBlur while Flip read 9/9 for both")
            # HOW THE ROW IS DRAWN, captured per surface and compared below.
            # The knob rules lived in flip.css, which Pad does not load, so Pad
            # rendered these rows completely unstyled from the day the knobs
            # shipped -- label below the slider instead of beside it, at the
            # wrong size and case. Nothing caught it: the markup was identical,
            # so a structural check passed, and both surfaces had the same tap
            # targets once the spacing moved, so the size checks passed too.
            _knob_look[_name] = lp.evaluate(
                "() => { const r = document.getElementById('shapeSidesRow');"
                " if (!r) return null;"
                " const l = r.querySelector('label'), i = r.querySelector('input');"
                " const cs = getComputedStyle(r), cl = getComputedStyle(l);"
                " return { display: cs.display, labelSize: cl.fontSize,"
                "          labelCase: cl.textTransform,"
                "          sameRow: Math.abs(l.getBoundingClientRect().top"
                "                   - i.getBoundingClientRect().top) < 24 }; }")
            lp.close()
    finally:
        _slb.close()

check("the shape knob rows were measured on both surfaces",
      _knob_look.get("Flip") and _knob_look.get("Pad"),
      f"{ {k: bool(v) for k, v in _knob_look.items()} } — a missing surface "
      "would make the comparison below vacuous")
if _knob_look.get("Flip") and _knob_look.get("Pad"):
    check("Pad and Flip draw the shape knobs the same way",
          _knob_look["Flip"] == _knob_look["Pad"],
          f"Flip {_knob_look['Flip']} vs Pad {_knob_look['Pad']} — these rules "
          "belong in styles.css; in flip.css they reach one surface and the "
          "other renders the same markup unstyled")
    check("...and the row is a row, not a stack",
          _knob_look["Flip"]["sameRow"] and _knob_look["Flip"]["display"] == "flex",
          str(_knob_look["Flip"]) + " — an unstyled .shape-knob is a block, "
          "which puts the label under the slider")


# ============================================================================
# HOW BIG THE SLIDER LOOKS, which is not how big it is to tap
#
# v250 made the hit box 44px and the control went on looking exactly as small as
# before, because the thumb was still 16px on a 4px track. Reported as "brush
# size and opacity seem small still" -- a fair complaint about a fix that was
# measured on the wrong property. The two are independent and BOTH are asserted:
# the hit checks above cover reach, this covers appearance.
#
# MEASURED IN PIXELS, not from computed style: getComputedStyle(el,
# '::-webkit-slider-thumb') returns the HOST element's box (260x44 here), so it
# cannot see the thumb at all. Screenshotting the control and reading ink height
# per column gives the thumb as the tallest column and the track as the median.
# ============================================================================
print("\nSLIDER APPEARANCE — the thumb and track are big enough to see")
try:
    from PIL import Image as _Img
except ImportError:
    check("Pillow is available to measure what is drawn", False,
          "install Pillow; this check reads pixels")
    _Img = None
if _Img:
    with sync_playwright() as _ap:
        _ab = _ap.chromium.launch()
        try:
            for _path, _name, _ctl, _sid in (("/flip", "Flip", "_flipDrawerCtl", "size"),
                                             ("/", "Pad", "_padDrawerCtl", "brushSizeRange")):
                ap = _ab.new_page(viewport={"width": 430, "height": 950})
                ap.goto(BASE + _path, wait_until="load")
                ap.wait_for_timeout(1200)
                ap.evaluate(f"() => {_ctl}.open('draw')")
                ap.wait_for_timeout(700)
                # The draw drawer opens at the HALF detent at compact widths
                # (colour only — lib/drawerdetent.js), and the slider under
                # measure lives in the full state. Take the path a user does:
                # the "Brush, smoothing & more" button. Desktop-width runs
                # find it display:none and skip the click.
                ap.evaluate("() => { const m = document.getElementById('drawerDetentMore');"
                            " if (m && getComputedStyle(m).display !== 'none') m.click(); }")
                ap.wait_for_timeout(400)
                # Push the thumb to the end so it cannot sit under the label or
                # off the captured strip.
                ap.evaluate("(id) => { const s = document.getElementById(id);"
                            " s.value = s.max;"
                            " s.dispatchEvent(new Event('input', { bubbles: true })); }", _sid)
                ap.wait_for_timeout(250)
                el = ap.query_selector("#" + _sid)
                bb = el.bounding_box() if el else None
                check(f"{_name}: the brush-size slider is on screen to measure",
                      bb is not None and bb["height"] > 0, str(bb))
                if not bb:
                    ap.close(); continue
                shot = f"/tmp/skribl-slider-{_name.lower()}.png"
                ap.screenshot(path=shot, clip={"x": bb["x"], "y": bb["y"] - 6,
                                               "width": bb["width"],
                                               "height": bb["height"] + 12})
                im = _Img.open(shot).convert("L")
                w, h = im.size
                px = im.load()
                heights = []
                for x in range(w):
                    col = [y for y in range(h) if px[x, y] > 70]
                    heights.append((max(col) - min(col) + 1) if col else 0)
                nz = sorted(v for v in heights if v > 0)
                thumb = max(heights) if heights else 0
                track = nz[len(nz) // 2] if nz else 0
                check(f"{_name}: the thumb is large enough to see and aim at",
                      thumb >= 20,
                      f"{thumb}px tall — it shipped at 16 on a 4px track, which "
                      "is about half the thumb iOS draws, and a 44px hit box "
                      "does nothing for how big it LOOKS")
                check(f"{_name}: the track is thick enough to read the fill",
                      track >= 5,
                      f"{track}px — on Opacity the filled portion IS the value, "
                      "and at 4px it was a hairline")
                check(f"{_name}: ...and the thumb still fits inside the 44px band",
                      thumb <= 40,
                      f"{thumb}px — a thumb that fills the hit box leaves no "
                      "room to see the track it rides on")
                ap.close()
        finally:
            _ab.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
