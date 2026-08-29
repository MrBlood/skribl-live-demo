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

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
