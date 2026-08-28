"""v226 — one size decision, made once, where a rule can refer to it.

WHY. `flip.css` carries eight `max-width` rules — 359, 360, 392, 400, 440, 559,
560, 640 — and `styles.css` has its own set. That is not a responsive design; it
is eight patches, each correct on the day it was written, none of them agreeing
about where "small" begins. The visible cost is in this project's own review
notes: **one pixel of resize takes Pad's toolbar from 398px to 565px**, and
560–640px gets the phone layout on a viewport with room to spare.

WHAT THIS STEP IS, AND IS NOT. It is not the migration. It is the thing the
migration migrates TO: `lib/sizeclass.js` asks one question, stamps one
attribute, and one existing query has been moved onto it as proof that the
boundary is identical. The other seven move one at a time with `verify_layout`
as the net. Stating that plainly matters — a refactor announced as "replace the
breakpoints" and delivered as "add a class" is the kind of quiet narrowing this
project has a suite for.

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

        print("\nTHE MIGRATION WAS A NO-OP — the whole claim of this step")
        # `.flip-app .header .actions { margin-left: auto }` moved from a
        # max-width query to the size class. Same boundary, so the computed
        # style must break at exactly the same place it used to.
        for w, expect in ((641, "compact-off"), (640, "compact-on")):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(220)
            got = page.evaluate("""() => {
              const el = document.querySelector('.flip-app .header .actions');
              return el ? getComputedStyle(el).marginLeft : null;
            }""")
            size = page.evaluate("() => document.body.getAttribute('data-size')")
            if expect == "compact-on":
                check(f"at {w}px the rule applies, as the media query did",
                      size == "compact" and got not in (None, "0px"),
                      f"data-size={size}, margin-left={got}")
            else:
                check(f"at {w}px it does not, as the media query did not",
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

        page.set_viewport_size({"width": 1280, "height": 900})
        check("no page error at any width", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
