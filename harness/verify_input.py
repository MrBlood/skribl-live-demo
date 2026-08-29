"""v230 — the input samples the handler was throwing away.

THE REPORT, from the live demo: "when I draw circles fast we get a lot of
straight line segments that make a curve. Drawing slowly smoothes it out."

THE CAUSE IS ARITHMETIC, NOT FEEL. A `pointermove` listener receives at most one
event per animation frame. The digitiser samples at 120-240Hz and the browser
stashes what it batched in `getCoalescedEvents()`, which nothing in this project
called. So every stroke was recorded at ~60Hz regardless of hardware: a circle
drawn in 0.4s becomes ~24 points, and paintSeg() joins consecutive points with
drawLine(), so it renders as a 24-sided polygon. The same circle over 2s gets
~120 points and looks smooth.

WHAT THIS SUITE CAN AND CANNOT SEE, said plainly because it changes what the
assertions are worth. Playwright's synthetic pointer events are not coalesced —
`getCoalescedEvents()` returns the single event — so the harness CANNOT observe
the extra samples arriving. Asserting "a fast circle now has more points" here
would pass on a build with the fix ripped out, which is the exact failure mode
this project keeps rediscovering.

So this tests the part that IS observable and the part that carries the risk:
the thinning rule, on the pure function, at the boundaries that matter. The
filter is what makes the fix affordable, and it is where a regression would be
silent — too aggressive and the curve comes back faceted, too lax and a fast
stroke eats the frame's point budget.
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
        page.wait_for_timeout(700)

        print("\nTHE LIB")
        check("lib/inputsamples.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblInputSamples") == "object",
              "a lib the template does not list is a lib that does not exist")
        check("extract() falls back to the event itself",
              page.evaluate("() => SkriblInputSamples.extract({}).length") == 1,
              "older Safari has no getCoalescedEvents; the stroke must degrade "
              "to today's behaviour rather than vanish")
        check("...and an empty batch does too",
              page.evaluate("""() => SkriblInputSamples.extract(
                  { getCoalescedEvents: () => [] }).length""") == 1,
              "some engines return an empty list rather than omitting the method")

        print("\nTHE THINNING IS SELF-BALANCING — that is the whole design")
        # A slow finger at 240Hz emits samples a fraction of a pixel apart: they
        # cost payload and change no pixel, so nearly all should go. A fast one
        # emits samples far apart: those are the curvature that was being lost,
        # so all should survive. One rule, opposite behaviour, no mode switch.
        r = page.evaluate("""() => {
          const S = window.SkriblInputSamples;
          const slow = []; for (let i = 0; i < 40; i++) slow.push({ x: i * 0.3, y: 0 });
          const fast = []; for (let i = 0; i < 8;  i++) fast.push({ x: i * 20,  y: 0 });
          const keptSlow = S.thin(slow, null, S.MIN_DIST);
          const keptFast = S.thin(fast, null, S.MIN_DIST);
          return { slowIn: slow.length, slowKept: keptSlow.length,
                   fastIn: fast.length, fastKept: keptFast.length,
                   slowLast: keptSlow[keptSlow.length - 1].x,
                   trueLast: slow[slow.length - 1].x };
        }""")
        check("a SLOW stroke's dense samples are mostly dropped",
              r["slowKept"] < r["slowIn"] / 3,
              f"{r['slowKept']} of {r['slowIn']} kept — without this, every "
              "stroke costs several times what it does today for no visible gain")
        check("a FAST stroke's sparse samples ALL survive",
              r["fastKept"] == r["fastIn"],
              f"{r['fastKept']} of {r['fastIn']} — these are the points whose "
              "absence is the reported bug; thinning them away restores it")
        check("the final sample is always kept",
              r["slowLast"] == r["trueLast"],
              f"{r['slowLast']} vs {r['trueLast']} — dropping it makes the ink "
              "lag the finger by up to one threshold, forever")

        # Thinning measures from the last point COMMITTED, not the last seen, or
        # a slow drift of sub-threshold steps is discarded entirely and the
        # stroke stops moving while the finger does not.
        drift = page.evaluate("""() => {
          const S = window.SkriblInputSamples;
          const pts = []; for (let i = 1; i <= 10; i++) pts.push({ x: i * 0.5, y: 0 });
          return S.thin(pts, { x: 0, y: 0 }, 1.5).length;
        }""")
        check("a sub-threshold drift still advances the stroke",
              drift >= 3,
              f"{drift} of 10 kept — measured from the previous SAMPLE rather "
              "than the last kept one, every step is under threshold and the "
              "whole drift disappears")

        print("\nERASING STAYS PRECISE — the bug the rewrite exposed")
        # The handler read:
        #     if (smoothingAlpha >= 1 || erasing) { px = raw.x; ... }
        #     if (flipTool === 'shape') { ... return; }
        #     else { smoothPt = ...; px = smoothPt.x; ... }
        # so the `else` bound to the SHAPE test. With the stabilizer on, an
        # eraser stroke had its precise point overwritten by the smoothed one —
        # contradicting the comment on the line above it. Invisible at the
        # default, where the smoothed point equals the raw one.
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(700)
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        page.evaluate("() => { smoothingAlpha = 0.25; setTool('eraser'); }")
        page.mouse.move(cx - 60, cy)
        page.mouse.down()
        page.mouse.move(cx + 60, cy)
        page.mouse.move(cx + 60, cy + 40)
        page.mouse.up()
        page.wait_for_timeout(400)
        land = page.evaluate("""() => {
          const f = frame(); const s = f.strokes;
          if (!s.length) return null;
          const last = s[s.length - 1];
          return { x: last.x, y: last.y, raw: lastRaw, erase: last.erase };
        }""")
        # CANVAS units, not CSS pixels. pos() scales by CW/rect.width — the
        # element is displayed at a different size than its coordinate space,
        # and comparing the two spaces makes every axis wrong by the same
        # ratio, which reads as a lag and is not one.
        expect = page.evaluate("([x,y]) => { const r = pad.getBoundingClientRect();"
                               " return { x: (x - r.left) * CW / r.width,"
                               "          y: (y - r.top) * CH / r.height }; }",
                               [cx + 60, cy + 40])
        ok = (land is not None
              and abs(land["x"] - expect["x"]) < 2.5
              and abs(land["y"] - expect["y"]) < 2.5)
        check("with the stabilizer ON, an eraser point lands where the pointer is",
              ok,
              f"{land} vs pointer {expect} — a lagged point here means the "
              "stabilizer is being applied to the eraser, which the code says "
              "in a comment that it does not do")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
