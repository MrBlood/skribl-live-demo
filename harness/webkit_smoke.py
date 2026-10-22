#!/usr/bin/env python3
"""Skribl in WebKit, on an iPhone-sized screen: the engine Safari is built on.

THE OWNER'S CALL, after v328: a WebKit check on the full run GitHub makes
after each merge, built like the Firefox one (harness/firefox_smoke.py), so a
pull request stays quiet. It costs nothing (ubuntu-latest, a public
repository). The build container has no WebKit, so its first real run is CI's.

WHAT IT IS AND IS NOT. Playwright's WebKit is the WebKit engine built for
Linux, not Safari on an iPhone: it finds what WebKit itself does differently
(a script error Chromium forgives, a feature it lacks, a request it refuses),
and not what iOS does (the ringer switch, the Home Screen app, SF, touch on
glass). The owner's phone stays the word on those (docs/DEVICE-CHECKLIST.md).
Video is not asked here: this build records through a media stack an iPhone
does not have, so its answer would describe neither.

What someone opening Skribl on an iPhone meets first, read from the thing
itself, on Playwright's "iPhone 15" (its screen, scale, touch and user agent):

  * the Pad, Flip, the Gallery, the Library and a share link load and boot;
  * a stroke on each editor leaves ink: the drawing's own data, and pixels on
    its canvas that differ from its ground; the Pad's replay plays;
  * each editor posts through its own sheet, ticked public; the Pad's link
    plays and shows ink; the Gallery shows both posts; the Library lists both;
  * on every page: no script throws, nothing is logged as an error, and no
    request to Skribl fails or answers 400 or more. Warnings are printed, not
    failed. A page with any of these is saved as a full-page screenshot under
    SKRIBL_SMOKE_SHOTS (CI keeps the folder as an artifact);
  * each page's load is printed from the browser's own navigation timing:
    first byte, DOMContentLoaded and load, in ms. A baseline, not a gate.

NOT A verify_ SUITE, on purpose, as firefox_smoke.py is not: a bare run or a
seal here could only skip it, and a skip proves nothing. CI's webkit job
installs WebKit, runs this through run_harness.sh, and fails when it skipped.
"""
import math
import os
import sys
from urllib.parse import urlparse

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
HOST = urlparse(BASE).netloc
SHOTS = os.environ.get("SKRIBL_SMOKE_SHOTS", "")
results = []
check = make_check(results, with_detail=True)

# THE ENGINE IS WEBKIT. SKRIBL_SMOKE_ENGINE=chromium runs the same steps on
# Chromium with the same phone, which is how this file is checked where there
# is no WebKit: the steps must hold on the engine the battery already trusts
# before a red here can be read as WebKit's.
ENGINE = os.environ.get("SKRIBL_SMOKE_ENGINE", "webkit")
PHONE = "iPhone 15"

# INK: as firefox_smoke.py reads it, pixels of the canvas's backing store that
# differ from its own corner (its ground), sampled every fourth pixel.
INK = """(sel) => { const c = document.querySelector(sel), x = c.getContext('2d');
  const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 0; i < d.length; i += 16)
    if (Math.abs(d[i] - d[0]) + Math.abs(d[i + 1] - d[1]) + Math.abs(d[i + 2] - d[2]) + Math.abs(d[i + 3] - d[3]) > 90) n++;
  return n; }"""

# The page's load, from the browser's own navigation timing (Level 2, which
# window.performance.timing is the old spelling of): ms from the start of the
# navigation.
TIMING = """() => { const n = performance.getEntriesByType('navigation')[0];
  return n ? { firstByte: Math.round(n.responseStart), domContentLoaded: Math.round(n.domContentLoadedEventEnd),
               load: Math.round(n.loadEventEnd), bytes: n.transferSize || 0 } : null; }"""


def draw(pg, sel):
    """One long stroke: down, sixty moves, up. The pointer is a mouse even on
    the phone, as a stylus would be; touch is the device check's."""
    box = pg.locator(sel).bounding_box()
    x0, y0 = box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.4
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    for i in range(60):
        pg.mouse.move(x0 + i * box["width"] * 0.01, y0 + math.sin(i / 6) * box["height"] * 0.12)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    pg.wait_for_timeout(300)


def post(pg, title, tick):
    """The editor's own Post sheet, ticked public: the share link it answers with."""
    pg.click("#postBtn")
    pg.wait_for_selector("#postTitleInput", state="visible", timeout=5000)
    pg.fill("#postTitleInput", title)
    pg.click(tick)
    ticked = pg.evaluate("() => document.getElementById('postPublicInput').checked")
    res = browsing.submit_post(pg)
    return ticked, res


def section(name, run, after=None):
    """Run one page's steps; a step that throws is a failed check that says
    where, so one broken page does not hide what the others found. `after`
    puts away (and photographs) a page the throw left open."""
    try:
        run()
    except Exception as e:
        check(f"{name}: every step ran", False, f"{type(e).__name__}: {str(e).splitlines()[0][:240]}")
        if after:
            after(True)


with sync_playwright() as p:
    try:
        b = getattr(p, ENGINE).launch()
    except Exception as e:   # no build of it installed: CI's job installs one
        print(f"SKIP: {ENGINE} is not installed ({str(e).splitlines()[0][:120]})")
        sys.exit(0)
    device = dict(p.devices[PHONE])
    device.pop("default_browser_type", None)
    print(f"{ENGINE} {b.version}, as {PHONE}: {device['viewport']['width']}x{device['viewport']['height']} "
          f"at {device['device_scale_factor']}x")
    ctx = b.new_context(**device)
    got = {"pad": "", "flip": ""}
    timings = []
    pages_seen = []

    def page(path):
        """Open `path` with its listeners on: what it throws, logs and fails."""
        pg = ctx.new_page()
        rec = {"path": path, "thrown": [], "errors": [], "warnings": [], "failed": [], "pg": pg}
        pg.on("pageerror", lambda e: rec["thrown"].append(str(e)[:300]))
        pg.on("console", lambda m: (rec["errors"] if m.type == "error" else rec["warnings"]).append(m.text[:300])
              if m.type in ("error", "warning") else None)
        pg.on("requestfailed", lambda r: rec["failed"].append(f"{r.method} {r.url[:160]}: {r.failure}")
              if urlparse(r.url).netloc == HOST else None)
        pg.on("response", lambda r: rec["failed"].append(f"{r.request.method} {r.url[:160]}: HTTP {r.status}")
              if r.status >= 400 and urlparse(r.url).netloc == HOST else None)
        pages_seen.append(rec)
        browsing.goto(pg, BASE, path)
        pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
        t = pg.evaluate(TIMING)
        if t:
            timings.append((path, t))
        return pg

    def done(pg, broke=False):
        """Before a page closes: if it threw, logged an error, had a request
        fail or stopped a step, keep a full-page screenshot of it as it is."""
        rec = next(r for r in pages_seen if r["pg"] is pg)
        rec["closed"] = True
        if SHOTS and (broke or rec["thrown"] or rec["errors"] or rec["failed"]):
            os.makedirs(SHOTS, exist_ok=True)
            name = rec["path"].strip("/").replace("/", "-") or "pad"
            try:
                pg.screenshot(path=os.path.join(SHOTS, f"{ENGINE}-{name}.png"), full_page=True)
                print(f"    (a screenshot of it: {ENGINE}-{name}.png)")
            except Exception as e:   # a page that never loaded may have nothing to show
                print(f"    (no screenshot of it: {type(e).__name__})")
        pg.close()

    def left_open(broke):
        for rec in pages_seen:
            if not rec.get("closed"):
                done(rec["pg"], broke)

    def pad():
        pg = page("/")
        draw(pg, "#canvas")
        pts, ink = pg.evaluate("() => strokes.length"), pg.evaluate(INK, "#canvas")
        check("the Pad boots, and a stroke is drawing data and ink on its canvas",
              pts > 10 and ink > 50, f"{pts} points, {ink} ink samples")
        pg.click("#recordBtn")
        pg.wait_for_timeout(400)
        pg.click("#playBtn")
        pg.wait_for_timeout(600)
        check("...its replay plays, with the scrubber up",
              pg.evaluate("() => playing && !document.getElementById('playScrub').hidden"))
        pg.evaluate("() => { if (playing) document.getElementById('playBtn').click(); }")
        pg.wait_for_timeout(400)
        ticked, res = post(pg, f"{ENGINE} smoke, Pad", ".post-check")
        got["pad"] = res["url"] or ""
        check("...and it posts through its own sheet, ticked public, and gets its link",
              ticked and "/s/" in got["pad"], str(res))
        done(pg)

    def flip():
        pg = page("/flip")
        draw(pg, "#pad")
        pts, ink = pg.evaluate("() => frames[0].strokes.length"), pg.evaluate(INK, "#pad")
        check("Flip boots, and a stroke is drawing data and ink on its page",
              pts > 10 and ink > 50, f"{pts} points, {ink} ink samples")
        ticked, res = post(pg, f"{ENGINE} smoke, Flip", "#postSheet .post-check")
        got["flip"] = res["url"] or ""
        check("...and it posts through its own sheet, ticked public, and gets its link",
              ticked and "/s/" in got["flip"], str(res))
        done(pg)

    def link():
        pid = got["pad"].rstrip("/").split("/")[-1]
        check("(the Pad's post gave a link to open)", bool(pid), repr(got["pad"]))
        if not pid:
            return
        pg = page("/s/" + pid)
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(1500)
        now = pg.evaluate("() => +document.getElementById('playerProgress').getAttribute('aria-valuenow')")
        ink = pg.evaluate(INK, "#canvas")
        check("the Pad's link boots and plays: its slider moves, and the drawing has ink",
              now > 0 and ink > 50, f"at {now}%, {ink} ink samples")
        done(pg)

    def pages():
        ids = [u.rstrip("/").split("/")[-1] for u in (got["pad"], got["flip"])]
        pg = page("/gallery")
        pg.wait_for_timeout(600)
        tiles = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
        check("the Gallery boots and shows both posts", all(i and i in tiles for i in ids),
              f"{len(tiles)} tiles; looking for {ids}")
        done(pg)
        pg = page("/library")
        pg.wait_for_timeout(900)
        listed = pg.inner_text("#postedList")
        check("the Library boots and lists both, in the browser that posted them",
              f"{ENGINE} smoke, Pad" in listed and f"{ENGINE} smoke, Flip" in listed, listed[:160])
        done(pg)

    print("\nTHE PAD")
    section("the Pad", pad, left_open)
    print("\nFLIP")
    section("Flip", flip, left_open)
    print("\nTHE LINK")
    section("the link", link, left_open)
    print("\nTHE GALLERY AND THE LIBRARY")
    section("the Gallery and the Library", pages, left_open)

    print("\nEVERY PAGE")
    for rec in pages_seen:
        for w in rec["warnings"][:4]:
            print(f"    {rec['path']} warned: {w}")
    check("no page threw", not any(r["thrown"] for r in pages_seen),
          "; ".join(f"{r['path']}: {t}" for r in pages_seen for t in r["thrown"][:2])[:600])
    check("no page logged an error", not any(r["errors"] for r in pages_seen),
          "; ".join(f"{r['path']}: {t}" for r in pages_seen for t in r["errors"][:2])[:600])
    check("no request to Skribl failed or answered 400 or more", not any(r["failed"] for r in pages_seen),
          "; ".join(f"{r['path']}: {t}" for r in pages_seen for t in r["failed"][:2])[:600])

    print(f"\nLOAD TIMES ({ENGINE}, {PHONE}; ms from the start of each navigation, from its own timing)")
    for path, t in timings:
        print(f"    {path:<16} first byte {t['firstByte']:>5}   DOMContentLoaded {t['domContentLoaded']:>5}   "
              f"load {t['load']:>5}   ({t['bytes']:,} B over the wire)")
    ctx.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
