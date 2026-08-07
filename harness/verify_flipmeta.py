"""Flip's share metadata: the title and caption a user actually typed.

THE BUG THIS REPRODUCES. `buildSharePayload()` in flip.js ended with a literal
`title:'Flip animation'` and sent no caption at all. Every Skribl shared from
Flip therefore arrived carrying the same meaningless title and an empty caption
— visible in production as `'title': 'Flip animation', 'caption': ''`. The Pad
has had `postTitleInput` and `postCaptionInput` since v131; Flip's template had
neither, so this was not a bug in the sense of code doing the wrong thing. It
was a whole control surface that was never built on one of the two editors.

Section 1 is source-only and is the regression guard: the literal must not come
back, and the payload builder must read the two inputs. It costs no browser.

Section 2 drives a real browser through the flow end to end — type a title and
a caption, share, then read the post back off the API and assert the values
survived. Asserting on the request body alone would prove only that the client
sent something; the round trip is what proves a user's words reach the platform.

Section 3 covers the empty case, because the compose step introduces a way to
share with nothing typed, and the server's substitution ('Untitled Skribl') is
what stops that becoming a blank row.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _layout import STATIC_DIR, template  # noqa: E402

results = []


def check(name, ok, detail=""):
    """`detail` here explains a FAILURE, so it is printed only on one.

    Suites in this harness pass a captured value as `detail` and print it
    either way. These details are diagnoses rather than values, and a PASS
    printing "the literal is back" reads as a failure to anyone scanning the
    log — which is exactly the kind of contradictory output round 6 found in
    the run stanza.
    """
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------------------
print("FLIP METADATA — section 1: the regression guard, source only")

flip_js = os.path.join(STATIC_DIR, "flip.js")
with open(flip_js, encoding="utf-8") as fh:
    src = fh.read()

# The exact literal that shipped. Matched loosely on quoting/spacing so that
# reintroducing it in any form is caught, not just the original formatting.
check("the hardcoded 'Flip animation' title is gone from flip.js",
      not re.search(r"title\s*:\s*['\"]Flip animation['\"]", src),
      "the literal is back — every Flip share would carry the same title again")

check("buildSharePayload reads the title input",
      "flipShareTitle" in src, "flip.js never reads #flipShareTitle")
check("buildSharePayload reads the caption input",
      "flipShareCaption" in src, "flip.js never reads #flipShareCaption")

# A caption key that is never sent is the half of the bug that is easy to miss:
# the title is visible, an absent caption just looks like the user wrote none.
check("the share payload carries a caption key",
      re.search(r"caption\s*:", src) is not None,
      "no caption is sent, so the field can never be populated from Flip")

with open(template("skribl_flip.html"), encoding="utf-8") as fh:
    markup = fh.read()
for _id in ("flipShareTitle", "flipShareCaption", "flipShareSubmit",
            "flipShareCompose", "flipShareResult"):
    check(f"the Flip template carries #{_id}", f'id="{_id}"' in markup)

# The compose step must not be able to appear as a fait accompli: the result
# pane starts hidden, or a user would see a stale link above the fields.
check("the result pane starts hidden",
      re.search(r'id="flipShareResult"[^>]*\shidden', markup) is not None,
      "the previous share's link would show above the compose fields")


# ---------------------------------------------------------------------------
print("\nFLIP METADATA — section 2: a real browser, end to end")

TITLE = "Bouncing ball, take 3"
CAPTION = "Squash on frames 4-6. Timing still feels late on the recovery."


def fetch(pid):
    with urllib.request.urlopen(f"{API}/{pid}", timeout=15) as r:
        return json.loads(r.read())


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — section 2 needs a browser")
    summarise_and_exit()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    posted_bodies = []

    def _capture(route):
        req = route.request
        if req.method == "POST":
            try:
                posted_bodies.append(json.loads(req.post_data or "{}"))
            except Exception:
                posted_bodies.append({})
        route.continue_()

    pg.route("**/api/skribls", _capture)

    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1500)
    check("Flip loads with no JS errors", not errors, "; ".join(errors[:2]))

    # Draw one stroke, or the emptiness check refuses to open the sheet.
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)

    pg.click("#postBtn")
    pg.wait_for_timeout(400)
    check("the Share button opens the compose step, not an immediate post",
          pg.is_visible("#flipShareTitle") and not posted_bodies,
          f"{len(posted_bodies)} post(s) fired before the user typed anything")

    pg.fill("#flipShareTitle", TITLE)
    pg.fill("#flipShareCaption", CAPTION)
    pg.wait_for_timeout(100)
    check("the caption counter tracks what was typed",
          pg.inner_text("#flipShareCount").startswith(str(len(CAPTION))),
          pg.inner_text("#flipShareCount"))

    pg.click("#flipShareSubmit")
    pg.wait_for_selector("#flipShareUrl", state="visible", timeout=20000)
    pg.wait_for_timeout(600)

    check("exactly one post was made", len(posted_bodies) == 1, str(len(posted_bodies)))
    body = posted_bodies[0] if posted_bodies else {}
    check("the request body carries the typed title",
          body.get("title") == TITLE, repr(body.get("title")))
    check("the request body carries the typed caption",
          body.get("caption") == CAPTION, repr(body.get("caption")))

    url = pg.input_value("#flipShareUrl")
    check("the result pane shows a player link", "/s/" in url, url)
    check("the compose pane is hidden once the link exists",
          not pg.is_visible("#flipShareTitle"))

    pid = url.rstrip("/").rsplit("/", 1)[-1]
    stored = fetch(pid)
    check("the stored post's title is what the user typed",
          stored.get("title") == TITLE, repr(stored.get("title")))
    check("the stored post's caption is what the user typed",
          stored.get("caption") == CAPTION, repr(stored.get("caption")))
    check("and it is not the old hardcoded string",
          stored.get("title") != "Flip animation", repr(stored.get("title")))

    # -----------------------------------------------------------------------
    print("\nFLIP METADATA — section 3: sharing with nothing typed")

    posted_bodies.clear()
    pg2 = b.new_page()
    pg2.route("**/api/skribls", _capture)
    pg2.goto(f"{BASE}/flip", wait_until="load")
    pg2.wait_for_timeout(1500)
    box = pg2.locator("#pad").bounding_box()
    pg2.mouse.move(box["x"] + 70, box["y"] + 70)
    pg2.mouse.down()
    pg2.mouse.move(box["x"] + 160, box["y"] + 140, steps=8)
    pg2.mouse.up()
    pg2.wait_for_timeout(200)
    pg2.click("#postBtn")
    pg2.wait_for_timeout(300)
    pg2.click("#flipShareSubmit")
    pg2.wait_for_selector("#flipShareUrl", state="visible", timeout=20000)
    pg2.wait_for_timeout(600)

    body2 = posted_bodies[0] if posted_bodies else {}
    check("an untouched title is sent as empty, not as a placeholder",
          body2.get("title") == "", repr(body2.get("title")))
    url2 = pg2.input_value("#flipShareUrl")
    stored2 = fetch(url2.rstrip("/").rsplit("/", 1)[-1])
    check("the server substitutes 'Untitled Skribl' for an empty title",
          stored2.get("title") == "Untitled Skribl", repr(stored2.get("title")))
    check("an untyped caption stores as empty, not null",
          stored2.get("caption") == "", repr(stored2.get("caption")))

    b.close()

summarise_and_exit()
