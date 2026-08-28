"""v227 — the compact surface drops the row, and loses nothing.

STAGE 4 of the filmstrip plan, and the one that needed a decision. The design
note's own condition for shipping it was not visual: **every operation must stay
reachable and announced**, because a filmstrip you can only operate by dragging
is a filmstrip some people cannot operate at all. This suite is that condition,
written down.

WHAT CHANGES, AND ONLY HERE. On compact the persistent page bar is hidden and
the active tile carries a ⋯ that opens the same operations. On regular the bar
stays exactly as it was — that was the owner's correction to the first draft of
the design note, which had proposed hiding it everywhere: buttons are good on a
big screen, and gestures teach nobody. Both halves are asserted, because a
change scoped to one surface is only correct if it left the other alone.

THE ACCESSIBILITY ASSERTIONS ARE THE POINT. A ⋯ that only appears on hover, or
a menu that traps focus, would pass every visual check and fail the actual
requirement. So: the trigger is a real button with aria-haspopup, the menu is a
role="menu" of real buttons, focus moves in on open, arrows walk it, Escape
returns focus to the trigger, and the items are not smaller targets than the
.pb buttons they replace.
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


def seed(page, n=5):
    page.evaluate("""(n) => {
      frames.length = 0;
      for (let i = 0; i < n; i++) {
        frames.push({ strokes: [{x: i, y: i, color: '#fff', size: 4, t: 0, start: true}],
                      strokeGroups: [1], hold: 1 });
      }
      idx = 2; spanAnchor = null; pageClip = null;
      redoStack.length = 0; buildStrip(); render();
    }""", n)


def order(page):
    return page.evaluate("() => frames.map(f => f.strokes[0].x)")


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1100, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(400)

        print("\nREGULAR — the row stays, and nothing was added beside it")
        seed(page)
        check("the app is regular at 1100px",
              page.evaluate("() => document.body.getAttribute('data-size')") == "regular")
        check("the page bar is present and visible",
              page.evaluate("() => { const b = document.getElementById('pagebar');"
                            " return !!b && getComputedStyle(b).display !== 'none'; }"))
        check("NO tile carries a ⋯ on the regular surface",
              page.evaluate("() => document.querySelectorAll('#strip .pageops').length") == 0,
              "a second route to the same five operations is clutter, not redundancy")

        print("\nCOMPACT — the row goes")
        page.set_viewport_size({"width": 420, "height": 820})
        page.wait_for_timeout(350)
        check("the app is compact at 420px",
              page.evaluate("() => document.body.getAttribute('data-size')") == "compact")
        check("the page bar is hidden",
              page.evaluate("() => getComputedStyle("
                            "document.getElementById('pagebar')).display") == "none")
        check("the strip rebuilt itself when the class flipped",
              page.evaluate("() => document.querySelectorAll('#strip .pageops').length") > 0,
              "without this a window resized past the boundary keeps the surface "
              "it happened to load with")

        print("\nREACHABLE — the condition this stage waited on")
        trig = page.locator("#strip .frame.on .pageops")
        check("the active tile's ⋯ is a real, visible button",
              trig.is_visible() and page.evaluate(
                  "() => document.querySelector('#strip .frame.on .pageops').tagName") == "BUTTON")
        check("...announced as opening a menu",
              page.evaluate("() => { const b = document.querySelector("
                            "'#strip .frame.on .pageops');"
                            " return b.getAttribute('aria-haspopup'); }") == "menu")
        check("...and named for the page it acts on",
              "page 3" in (page.evaluate(
                  "() => document.querySelector('#strip .frame.on .pageops')"
                  ".getAttribute('aria-label')") or "").lower(),
              page.evaluate("() => document.querySelector('#strip .frame.on .pageops')"
                            ".getAttribute('aria-label')"))
        check("it is reachable by keyboard, not hover-only",
              page.evaluate("""() => {
                const b = document.querySelector('#strip .frame.on .pageops');
                b.focus();
                return document.activeElement === b
                       && getComputedStyle(b).display !== 'none';
              }"""),
              "a control that appears only under a pointer is one keyboard users "
              "do not have")

        print("\nTHE MENU — announced, walkable, escapable")
        trig.click()
        page.wait_for_timeout(200)
        check("a role=menu opens", page.evaluate(
            "() => { const m = document.querySelector('.pageops-menu');"
            " return m && m.getAttribute('role'); }") == "menu")
        check("...the trigger says it is open",
              page.evaluate("() => document.querySelector('#strip .frame.on .pageops')"
                            ".getAttribute('aria-expanded')") == "true")
        check("...it holds real menuitems, not divs",
              page.evaluate("""() => {
                const it = [...document.querySelectorAll('.pageops-item')];
                return it.length >= 4 && it.every(b => b.tagName === 'BUTTON'
                       && b.getAttribute('role') === 'menuitem');
              }"""))
        check("...every operation the row carried is here",
              sorted(page.evaluate(
                  "() => [...document.querySelectorAll('.pageops-item')]"
                  ".map(b => b.textContent.trim())"))
              == ["Copy", "Delete", "Move left", "Move right"],
              str(page.evaluate("() => [...document.querySelectorAll('.pageops-item')]"
                                ".map(b => b.textContent.trim())")))
        check("...focus moved INTO the menu on open",
              page.evaluate("() => document.activeElement"
                            ".classList.contains('pageops-item')"),
              "a menu you open with the keyboard and land outside of is not open")
        check("...its targets are no smaller than the .pb buttons it replaces",
              page.evaluate("""() => [...document.querySelectorAll('.pageops-item')]
                  .every(b => b.getBoundingClientRect().height >= 38)"""),
              "the compact surface must not be a harder target than the row")
        first = page.evaluate("() => document.activeElement.textContent.trim()")
        page.keyboard.press("ArrowDown")
        check("arrows walk it",
              page.evaluate("() => document.activeElement.textContent.trim()") != first,
              f"{first} -> {page.evaluate('() => document.activeElement.textContent.trim()')}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape closes it",
              page.evaluate("() => !document.querySelector('.pageops-menu')"))
        check("...and returns focus to the trigger",
              page.evaluate("() => document.activeElement"
                            ".classList.contains('pageops')"),
              "leaving focus on a removed node strands a keyboard user at the "
              "top of the document")

        print("\nAND IT ACTUALLY OPERATES — reachable is not the same as working")
        seed(page)
        page.wait_for_timeout(150)
        before = order(page)
        page.locator("#strip .frame.on .pageops").click()
        page.wait_for_timeout(180)
        page.locator(".pageops-item", has_text="Move left").click()
        page.wait_for_timeout(220)
        check("Move left from the menu reorders the pages",
              order(page) != before and order(page) == [0, 2, 1, 3, 4],
              f"{before} -> {order(page)} (page 2 swaps with the one on its left)")
        check("...and the menu closed behind it",
              page.evaluate("() => !document.querySelector('.pageops-menu')"))

        seed(page)
        page.wait_for_timeout(150)
        page.locator("#strip .frame.on .pageops").click()
        page.wait_for_timeout(180)
        page.locator(".pageops-item", has_text="Delete").click()
        page.wait_for_timeout(220)
        check("Delete from the menu removes the page",
              order(page) == [0, 1, 3, 4], str(order(page)))

        print("\nSCOPE — the menu speaks for a run when there is one")
        seed(page)
        page.evaluate("() => { spanAnchor = 0; idx = 2; buildStrip(); }")
        page.wait_for_timeout(150)
        page.locator("#strip .frame.on .pageops").click()
        page.wait_for_timeout(180)
        _diag = page.evaluate("""() => ({
          span: JSON.stringify(pageSpan()), idx: idx, anchor: spanAnchor,
          menu: !!document.querySelector('.pageops-menu'),
          titles: [...document.querySelectorAll('.pageops-item')]
                    .map(b => b.getAttribute('aria-label'))
        })""")
        # aria-label, not title: lib/tooltip.js adopts every [title] into data-tip
        # and removes the attribute, so the accessible name is both the right
        # place for the scope and the only one that survives to be asserted.
        check("with a range selected the items say 'these 3 pages'",
              any("these 3 pages" in t for t in _diag["titles"]),
              str(_diag))
        page.keyboard.press("Escape")

        print("\nBACK TO REGULAR — the other surface was left alone")
        page.set_viewport_size({"width": 1100, "height": 900})
        page.wait_for_timeout(350)
        check("the page bar is back",
              page.evaluate("() => getComputedStyle("
                            "document.getElementById('pagebar')).display") != "none")
        check("and the ⋯ is gone again",
              page.evaluate("() => document.querySelectorAll('#strip .pageops').length") == 0)
        check("no page error at any width", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
