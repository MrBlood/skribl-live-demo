#!/usr/bin/env python3
"""The Post title starts from the drawing's name, on both editors (the owner's
yes, Q3).

A drawing named in Your drafts reached the Post sheet with an empty title, so
it was named twice or posted as Untitled Skribl. The sheet is one module for
both editors (lib/postsheet.js), and this drives each the same way:

  * an unnamed drawing's title stays empty: the date name a blank drawing
    saves under is not a name a person gave;
  * a named drawing's title starts with its name, and follows a rename;
  * the next drawing after New Skribl does not carry the last one's name;
  * words typed in the title box are the person's and stay;
  * a box emptied by hand stays empty, until the drawing's name changes.

The rows that fill were red before; the rows that keep pin the kind half.
"""
import os
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the title follows the name.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
ED = {"Pad": ("/", "#menuBtn", "#clearMenuItem", "#canvas"), "Flip": ("/flip", "#moreBtn", "#miClearAll", "#pad")}


def stroke(pg, sel):
    r = pg.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return { x: b.x, y: b.y }; }", sel)
    pg.mouse.move(r["x"] + 60, r["y"] + 60); pg.mouse.down()
    for k in range(12):
        pg.mouse.move(r["x"] + 60 + k * 9, r["y"] + 60 + k * 4); pg.wait_for_timeout(16)
    pg.mouse.up(); pg.wait_for_timeout(300)
    if sel == "#canvas":
        # The Pad records from the first stroke and keeps Post and New Skribl
        # back until the take is done, as verify_posted says.
        pg.click("#recordBtn"); pg.wait_for_timeout(600)


def title(pg):
    """Open the Post sheet, read its title box, and close it again."""
    pg.click("#postBtn"); pg.wait_for_timeout(450)
    v = pg.evaluate("() => document.getElementById('postTitleInput').value")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(350)
    return v


def name(pg, t):
    pg.evaluate("(t) => window.SkriblName.set(t)", t)


with sync_playwright() as p:
    b = p.chromium.launch()
    for ed, (path, menu, start, canvas) in ED.items():
        print(f"\nTHE POST TITLE STARTS FROM THE NAME — {ed}")
        pg = b.new_page(viewport={"width": 1100, "height": 820})
        errs = []
        pg.on("pageerror", lambda x: errs.append(str(x)))
        browsing.goto(pg, BASE, path)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        stroke(pg, canvas)

        got = title(pg)
        check(f"{ed}: an unnamed drawing's title stays empty, not its date name", got == "", repr(got))
        name(pg, "Moon cat")
        got = title(pg)
        check(f"{ed}: a named drawing's title starts with its name", got == "Moon cat", repr(got))
        name(pg, "Moon cat, again")
        got = title(pg)
        check(f"{ed}: ...and follows a rename, while the box holds only what the sheet put there",
              got == "Moon cat, again", repr(got))

        pg.click(menu); pg.wait_for_timeout(300)
        pg.click("#menuNewTile"); pg.wait_for_timeout(300)
        pg.click(start); pg.wait_for_timeout(500)
        stroke(pg, canvas)
        got = title(pg)
        check(f"{ed}: after New Skribl, the next drawing does not carry the last one's name", got == "", repr(got))
        name(pg, "Dog")
        got = title(pg)
        check(f"{ed}: ...and the next drawing's name is its title", got == "Dog", repr(got))

        pg.click("#postBtn"); pg.wait_for_timeout(450)
        pg.fill("#postTitleInput", "My own words")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(350)
        name(pg, "Dog, renamed")
        got = title(pg)
        check(f"{ed}: words typed in the title box stay, whatever the drawing is called", got == "My own words", repr(got))

        pg.click("#postBtn"); pg.wait_for_timeout(450)
        pg.fill("#postTitleInput", "")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(350)
        got = title(pg)
        check(f"{ed}: a box emptied by hand stays empty when the sheet opens again", got == "", repr(got))
        name(pg, "Dog, at last")
        got = title(pg)
        check(f"{ed}: ...until the drawing's name changes", got == "Dog, at last", repr(got))

        check(f"{ed}: no page errors", not errs, "; ".join(errs[:2]))
        pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
