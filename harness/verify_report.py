"""Report a problem — the context a tester can hand over.

WHY IT EXISTS. There is no error reporting anywhere in Skribl. During a test
you learn about problems by being told, and "it didn't work" is not actionable.
Every question asked of a tester — what version, what browser, what canvas, how
many pages — is answerable by the page itself.

IT COPIES, IT DOES NOT SEND. There is no endpoint, and adding one would mean an
unauthenticated write path, storage, and someone reading it. The button says
"Copy details" for that reason. This suite asserts the copy never claims to
send, because a tester who believed it would wait for a reply that was never
coming.

AND IT MUST NOT LEAK CONTENT. Titles, captions, stroke data and audio are
excluded deliberately — a bug report should not quietly carry someone's
unpublished drawing. The assertions below seed a recognisable title and stroke
and require neither to appear.

AND EVERY WORD ON IT IS 12px OR MORE, in both editors on a phone and a desk
(the owner's "all yes" to every word at 12px, Nov 4): the details and the line
saying what is left out were 11.5 and 11px.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from skribl.core import SKRIBL_VERSION  # noqa: E402
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
SECRET_TITLE = "Zqx-private-working-title-42"

results = []


check = make_check(results, detail_on_pass=False)


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
        print(f"\nREPORT — {surface}")
        pg = b.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1400)
        check(f"{surface} loads with no JS errors", not errs, "; ".join(errs[:2]))

        check(f"{surface} publishes the report lib",
              pg.evaluate("() => !!window.SkriblReport"),
              "lib/report.js did not load")

        # Draw something with a recognisable stroke so the leak checks below
        # have something real to fail against.
        sel = "#pad" if surface == "Flip" else "#canvas"
        box = pg.locator(sel).bounding_box()
        pg.mouse.move(box["x"] + 60, box["y"] + 60)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(400)

        opener = pg.locator("[data-skribl-report]").first
        check(f"{surface} has a report entry point", opener.count() > 0)
        pg.evaluate("() => window.SkriblReport.init() && null")
        pg.evaluate("() => document.querySelector('[data-skribl-report]').click()")
        pg.wait_for_timeout(350)

        check(f"{surface}: the sheet opens", pg.is_visible("#reportDetails"))

        text = pg.inner_text("#reportDetails")
        # The REAL version, not a "v1" prefix pin — that literal matched every
        # version from v100 to v199 and then broke on the v200 bump while
        # still not proving the sheet showed the right number.
        check(f"{surface}: the version is included",
              SKRIBL_VERSION in text, repr(text[:80]))
        check(f"{surface}: the browser is included",
              "Mozilla" in text or "Chrome" in text, repr(text[:80]))
        check(f"{surface}: the canvas size is included",
              "Canvas:" in text, repr(text[:200]))
        check(f"{surface}: the point count is included",
              "Points:" in text, repr(text[:200]))
        check(f"{surface}: it reports a non-zero point count after drawing",
              any(line.startswith("Points: ") and line.split(": ")[1] != "0"
                  for line in text.splitlines()),
              repr([l for l in text.splitlines() if l.startswith("Points")]))

        # The privacy contract, asserted rather than asserted-about.
        check(f"{surface}: no stroke coordinates are included",
              '"x"' not in text and "clientX" not in text, repr(text[:200]))
        check(f"{surface}: no base64 media is included",
              "data:" not in text and "base64" not in text, repr(text[:200]))
        check(f"{surface}: the sheet says content is excluded",
              "not included" in pg.inner_text("#reportSheet").lower())

        # The button must not promise something it does not do.
        sheet_text = pg.inner_text("#reportSheet").lower()
        check(f"{surface}: the action says copy, not send",
              "copy details" in sheet_text and "send them" in sheet_text
              and "sending" not in sheet_text,
              "a button labelled Send that only copies would be a lie")

        pg.click("#reportCopy")
        pg.wait_for_timeout(300)
        check(f"{surface}: the copy button confirms",
              pg.inner_text("#reportCopy").strip().lower() in ("copied", "select and copy"),
              pg.inner_text("#reportCopy"))

        pg.click("#reportClose")
        pg.wait_for_timeout(250)
        check(f"{surface}: closing hides the sheet",
              not pg.is_visible("#reportDetails"))
        check(f"{surface}: no JS errors across the flow", not errs, "; ".join(errs[:2]))
        pg.close()

    # -----------------------------------------------------------------------
    print("\nREPORT — a title the user typed never reaches the report")
    #
    # The strongest version of the privacy check: seed a title that appears
    # nowhere else, then require it absent. A field added to collect() later
    # that happens to carry the title would fail here.
    pg = b.new_page()
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1400)
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.click("#postBtn")
    pg.wait_for_timeout(350)
    pg.fill("#postTitleInput", SECRET_TITLE)
    pg.fill("#postCaptionInput", "a caption nobody should see in a bug report")
    pg.wait_for_timeout(150)

    text = pg.evaluate("() => window.SkriblReport.collect()")
    check("the typed title is absent from the report",
          SECRET_TITLE not in text, "the report carries unpublished content")
    check("the typed caption is absent from the report",
          "nobody should see" not in text, "the report carries unpublished content")
    check("but the page count is still there",
          "Pages:" in text, repr(text))
    pg.close()

    print("\nREPORT — every word it paints at 12px or more")
    #
    # The owner's "all yes" (Nov 4): every word to 12px, one sheet per PR,
    # each with its own check that nothing painted in it is under 12px, as the
    # Post sheet has (verify_postmoment) and Export (verify_exportui section
    # 6). The type census read two here: the details (11.5px, monospace) and
    # the line under them that says what is left out (11px). Every text the
    # sheet lays out is read, in both editors on a phone and a desk, after a
    # stroke, so the details have a drawing to describe.
    SMALL12 = """() => { const out = [], S = document.getElementById('reportSheet'); let n = 0;
      const w = document.createTreeWalker(S, NodeFilter.SHOW_TEXT);
      for (let t = w.nextNode(); t; t = w.nextNode()) {
        const el = t.parentElement;
        if (!t.nodeValue.trim() || !el.getClientRects().length || getComputedStyle(el).visibility !== 'visible') continue;
        n++; const f = parseFloat(getComputedStyle(el).fontSize);
        if (f < 12) out.push((el.id ? '#' + el.id : '.' + el.classList[0]) + ' ' + f + 'px ' + JSON.stringify(t.nodeValue.trim().slice(0, 24))); }
      return { n, small: out }; }"""
    for surface, path, canvas in (("Pad", "/skribl-pad", "#canvas"), ("Flip", "/flip", "#pad")):
        for size, view in (("phone", dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)),
                           ("desk", dict(viewport={"width": 1280, "height": 900}))):
            c = b.new_context(**view)
            pg = c.new_page()
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(1400)
            box = pg.locator(canvas).bounding_box()
            pg.mouse.move(box["x"] + 60, box["y"] + 60)
            pg.mouse.down()
            pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
            pg.mouse.up()
            pg.wait_for_timeout(400)
            pg.evaluate("() => window.SkriblReport.init() && null")
            pg.evaluate("() => document.querySelector('[data-skribl-report]').click()")
            pg.wait_for_timeout(500)
            r = pg.evaluate(SMALL12)
            check(f"{surface}, {size}: nothing the Report sheet paints is under 12px",
                  r["n"] >= 5 and not r["small"], f"{r['n']} texts read; under 12px: {r['small']}")
            c.close()

    b.close()

summarise_and_exit()
