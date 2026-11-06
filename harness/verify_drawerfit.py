#!/usr/bin/env python3
"""The canvas is the size it would be with every drawer shut, whenever it is fit: Pad and Flip.

THE OWNER, Nov 6, on a desk: a saved draft opened with the music drawer open
"shrinks because of open drawer, then when closed drawer - it stays small",
and a new 4:3 Pad "just never goes back to be as big as it can be so it sits
small in the middle of the screen". Opening a drawer only scrolls the page and
the canvas keeps its size; but a fit that ran while one was open (a draft or a
New Skribl laid out, the window resized, a phone's toolbar sliding away) gave
the canvas only the room the drawer left, and nothing fit it again when the
drawer closed: 423 px of 682 on a 1536 x 864 desk with the music drawer open,
331 with Tune, 204 of 378 on a phone with Tune. Flip's stage came out 24px
short with a drawer open (the room under a drawer's last row it wears only
then) and stayed so.

WHAT IS ASKED, AND HOW IT IS READ (the canvas's own box, before and after)
  * THE PAD: a draft opened with the music drawer open keeps the canvas its
    full size, and closing the drawer leaves it there; the window resized with
    the music drawer, the draw drawer or Tune open keeps it, desk and phone.
  * FLIP: the window resized with the music or the draw drawer open keeps the
    canvas its size, and closing the drawer leaves it there.
"""
import os
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the canvas keeps its size.")
    raise SystemExit(77)
import browsing  # noqa: E402

DESK = {"width": 1536, "height": 864}
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
BOX = "(sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }"


def page(b, route, opts=None):
    c = b.new_context(**(opts or {"viewport": DESK}))
    q = c.new_page()
    browsing.goto(q, BASE, route)
    q.wait_for_timeout(800)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    return c, q


def jiggle(q, w, h):
    """A fit, as a window resized and put back runs one."""
    q.set_viewport_size({"width": w - 20, "height": h - 4})
    q.wait_for_timeout(450)
    q.set_viewport_size({"width": w, "height": h})
    q.wait_for_timeout(600)


with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("\nTHE PAD")
    c, q = page(b, "/")
    full = q.evaluate(BOX, "#canvas")
    q.mouse.move(400, 300)
    q.mouse.down()
    q.mouse.move(500, 340, steps=10)
    q.mouse.up()
    q.wait_for_timeout(300)
    q.evaluate("() => { if (recording) recordBtn.click(); }")
    q.wait_for_timeout(300)
    draft = q.evaluate("() => JSON.stringify(serializeSkribl())")
    browsing.pad_drawer(q, "music")
    q.wait_for_timeout(400)
    q.evaluate("(p) => loadSkribl(JSON.parse(p))", draft)
    q.wait_for_timeout(800)
    opened = q.evaluate(BOX, "#canvas")
    browsing.pad_drawer_close(q)
    q.wait_for_timeout(700)
    shut = q.evaluate(BOX, "#canvas")
    check("a draft opened with the music drawer open keeps the canvas its full size, and closing the drawer leaves it there",
          opened == full and shut == full, f"fresh {full}, the draft opened {opened}, the drawer shut {shut}")
    for name in ("music", "draw"):
        browsing.pad_drawer(q, name)
        q.wait_for_timeout(400)
        jiggle(q, DESK["width"], DESK["height"])
        during = q.evaluate(BOX, "#canvas")
        browsing.pad_drawer_close(q)
        q.wait_for_timeout(700)
        after = q.evaluate(BOX, "#canvas")
        check(f"the window resized with the {name} drawer open keeps the canvas, and so does shutting it",
              during == full and after == full, f"fresh {full}, resized with it open {during}, shut {after}")
    q.click("#tuneBtn")
    q.wait_for_timeout(700)
    jiggle(q, DESK["width"], DESK["height"])
    during = q.evaluate(BOX, "#canvas")
    q.click("#tuneBtn")
    q.wait_for_timeout(800)
    after = q.evaluate(BOX, "#canvas")
    check("the window resized with Tune open keeps the canvas, and so does shutting Tune (a desk)",
          during == full and after == full, f"fresh {full}, resized with Tune open {during}, shut {after}")
    c.close()

    c, q = page(b, "/", PHONE)
    full = q.evaluate(BOX, "#canvas")
    q.click("#tuneBtn")
    q.wait_for_timeout(700)
    jiggle(q, 402, 874)
    during = q.evaluate(BOX, "#canvas")
    q.click("#tuneBtn")
    q.wait_for_timeout(800)
    after = q.evaluate(BOX, "#canvas")
    check("...and on a phone, Tune open through a fit (a toolbar sliding) keeps the canvas",
          during == full and after == full, f"fresh {full}, with Tune open {during}, shut {after}")
    c.close()

    print("\nFLIP")
    c, q = page(b, "/flip")
    full = q.evaluate(BOX, "#pad")
    for name in ("music", "draw"):
        browsing.pad_drawer(q, name)
        q.wait_for_timeout(400)
        jiggle(q, DESK["width"], DESK["height"])
        during = q.evaluate(BOX, "#pad")
        browsing.pad_drawer_close(q)
        q.wait_for_timeout(700)
        after = q.evaluate(BOX, "#pad")
        check(f"Flip: the window resized with the {name} drawer open keeps the canvas, and so does shutting it",
              during == full and after == full, f"fresh {full}, resized with it open {during}, shut {after}")
    c.close()
    b.close()

summarise_and_exit()
