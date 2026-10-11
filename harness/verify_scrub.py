"""The play scrubber's rendered shape — measured, not assumed.

This suite exists because the scrubber's geometry was UNVERIFIED. It is inset to
the canvas frame's flat bottom span and rendered as a pill (`.play-scrub` in
styles.css, `positionScrub()` in app.js), and nobody had ever seen it painted:
driving Pad through draw -> stop -> play in a harness had not been done, so the
inset and the pill were a design intention with no measurement under them.

THE MEASUREMENT ONLY COUNTS IN THE REAL SHOWN STATE. `positionScrub()` returns
early on `playScrub.hidden`, so an element forced visible with `hidden = false`
has never been positioned — it measures 0 wide and reads as a catastrophic
misalignment that is entirely an artifact of the probe. The first assertion here
is therefore the negative control: at rest the bar is genuinely not laid out, and
every later assertion runs only after a real replay has started.

Measured result on unmodified v179 (both viewports): inset 24px each side,
matching --r-frame exactly, flush to the canvas bottom, spanning wrap width less
48. The shape was correct. This suite is what keeps it that way.
"""
import math
import sys

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"

results = []


check = make_check(results)


MEASURE = """() => {
  const s = document.getElementById('playScrub');
  const wrap = document.querySelector('.canvas-wrap');
  const area = document.querySelector('.canvas-area');
  if (!s || !wrap || !area) return null;
  const cs = getComputedStyle(s);
  const sb = s.getBoundingClientRect(), wb = wrap.getBoundingClientRect();
  return {
    laidOut: s.offsetParent !== null,
    hidden: s.hidden,
    display: cs.display,
    opacity: parseFloat(cs.opacity),
    radius: parseFloat(cs.borderRadius) || 0,
    overflow: cs.overflow,
    h: sb.height, w: sb.width,
    insetLeft: sb.left - wb.left,
    insetRight: wb.right - sb.right,
    gapBelow: sb.top - wb.bottom,
    wrapW: wb.width,
    bandMid: (() => { const t = document.getElementById('toolBar').getBoundingClientRect(); return t.top + t.height / 2; })(),
    bandW: document.getElementById('toolBar').getBoundingClientRect().width,
    mid: sb.top + sb.height / 2,
    bottom: sb.bottom, vh: innerHeight,
    band: (() => { const t = document.getElementById('toolBar').getBoundingClientRect(); return [t.top, t.bottom]; })(),
    rFrame: parseFloat(getComputedStyle(document.documentElement)
                         .getPropertyValue('--r-frame')) || 0,
  };
}"""


def scribble(pg, box, n=120):
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * 120
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 20 == 0:
            pg.wait_for_timeout(30)
    pg.mouse.up()


with sync_playwright() as b_ctx:
    b = b_ctx.chromium.launch()

    for label, vw, vh in [("desktop", 1280, 900), ("phone", 390, 844)]:
        print(f"\nPAD — {label} {vw}x{vh}")
        pg = b.new_page(viewport={"width": vw, "height": vh})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(pg, BASE, "/")
        pg.evaluate("() => localStorage.clear()")

        # --- negative control -------------------------------------------------
        rest = pg.evaluate(MEASURE)
        check(f"[{label}] at rest the bar is genuinely not laid out",
              rest is not None and rest["laidOut"] is False and rest["hidden"] is True
              and rest["display"] == "none",
              "positionScrub() returns early on hidden, so anything measured here "
              "is an artifact — this is the state a forced show would report from")

        # --- drive it into the real shown state -------------------------------
        box = pg.locator("#canvas").bounding_box()
        scribble(pg, box)
        pg.wait_for_timeout(600)
        pg.click("#recordBtn")          # stop the take
        pg.wait_for_timeout(400)
        pg.click("#playBtn")
        # MID-REPLAY IS A STATE, NOT A DELAY. Pad replays cap each recorded gap
        # at 50ms, so this scribble replays in well under a second and a fixed
        # 500ms could land after hideScrub() on a fast machine. Take the
        # measurement the first frame the bar is fully shown; if it never is,
        # measure anyway so the check below reports what was there.
        try:
            m = pg.wait_for_function(
                f"() => {{ const m = ({MEASURE})(); "
                f"return (m && m.laidOut && m.w > 0 && m.opacity === 1) ? m : null; }}",
                timeout=5000).json_value()
        except PWTimeout:
            m = pg.evaluate(MEASURE)

        # This one gates every assertion after it. If the replay never started,
        # the bar reads 0 wide and the inset comparisons below would compare
        # 0 against 0 and pass vacuously — a symmetric zero is the signature of
        # a broken probe, not of agreement.
        shown = m is not None and m["laidOut"] and m["w"] > 0
        check(f"[{label}] a real replay shows the bar",
              shown and m["opacity"] == 1 and m["display"] == "block",
              f"laidOut={m and m['laidOut']}, w={m and round(m['w'], 1)}, "
              f"opacity={m and m['opacity']}")
        if not shown:
            check(f"[{label}] geometry measurable", False,
                  "replay did not start — later assertions skipped rather than "
                  "reported against an unpositioned element")
            print(f"   page errors: {errs}")
            pg.close()
            continue

        # --- the geometry itself ---------------------------------------------
        check(f"[{label}] inset equally at both ends",
              abs(m["insetLeft"] - m["insetRight"]) <= 1,
              f"left={round(m['insetLeft'], 2)}, right={round(m['insetRight'], 2)}")

        if label == "phone":
            # v316 (owner, iPhone): on a phone the toolbar fades for a replay but
            # keeps its band, and a bar on the canvas rim left that band EMPTY
            # under it. The phone's scrubber lives in the band instead —
            # centred on it, toolbar-wide less 16px each side. The rim contract
            # below is the desktop's, where the toolbar is not a thumb zone.
            # Then the owner's pick B: low in that band, 24px clear of the
            # screen's foot (the swipe-home strip), so the words above it have
            # room (verify_replayspeed ROOM TO BREATHE has the words' side).
            want = min(m["band"][1], m["vh"] - 24)
            check(f"[{label}] it sits low in the faded toolbar's band, 24px clear of the screen's foot",
                  abs(m["bottom"] - want) <= 1 and m["bottom"] - m["h"] >= m["band"][0] - 1,
                  f"bar bottom {round(m['bottom'], 1)} vs {round(want, 1)}; band {m['band']}")
            check(f"[{label}] it spans the toolbar's band, 16px in from each end",
                  abs(m["w"] - (m["bandW"] - 32)) <= 1.5,
                  f"w={round(m['w'], 1)}, band={round(m['bandW'], 1)}")
        else:
            check(f"[{label}] the inset is the frame's corner radius, read from the token",
                  abs(m["insetLeft"] - m["rFrame"]) <= 1,
                  f"inset={round(m['insetLeft'], 2)} vs --r-frame={m['rFrame']} — "
                  "a hard-coded inset would drift the moment the token moved")

            check(f"[{label}] it spans the flat bottom span, not the full width",
                  abs(m["w"] - (m["wrapW"] - 2 * m["rFrame"])) <= 1.5,
                  f"w={round(m['w'], 1)}, wrap={round(m['wrapW'], 1)} — spanning the "
                  "full width puts the ends past where the frame has curved away")

            check(f"[{label}] it hangs flush from the canvas bottom",
                  abs(m["gapBelow"]) <= 1,
                  f"gap={round(m['gapBelow'], 2)}px")

        # THE DRAWING'S SHAPE IN THE BAR (the owner's replay pick S3): a
        # rounded bar 30px tall that the strip fills edge to edge, painted --
        # not a 5px hairline. On a phone 18px (pick B: room for the words). Painted is read off the strip's own pixels: a
        # canvas sized right and left blank is the failure this is for.
        strip = pg.evaluate("""() => { const s = document.getElementById('playScrub'), c = s.querySelector('canvas.rl-strip');
            if (!c) return null; const r = c.getBoundingClientRect(), b = s.getBoundingClientRect();
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let ink = 0;
            for (let i = 3; i < d.length; i += 4) if (d[i] > 0) ink++;
            return { w: r.width, bw: b.width, ink }; }""")
        tall = 18 if label == "phone" else 30
        check(f"[{label}] it is a rounded bar of the drawing's shape: {tall}px tall, the strip filling it, and painted",
              abs(m["h"] - tall) <= 0.5 and m["radius"] >= 6 and strip is not None
              and abs(strip["w"] - strip["bw"]) <= 1 and strip["ink"] > 100,
              f"height={m['h']}, radius={m['radius']}, strip={strip}")

        check(f"[{label}] no page errors during replay", not errs, str(errs[:3]))
        pg.close()

    # --- the player carries it too -------------------------------------------
    # app.js serves the player, so the scrubber's CSS and positioning have to
    # arrive on that template as well. This is the class of omission that left
    # the player throwing on window.SkriblLoopTrim.
    print("\nPLAYER")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    perrs = []
    pg.on("pageerror", lambda e: perrs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    has_rules = pg.evaluate("""() => {
        let n = 0;
        for (const sh of document.styleSheets) {
          let rules; try { rules = sh.cssRules; } catch (e) { continue; }
          for (const r of rules) if (r.selectorText && r.selectorText.includes('.play-scrub')) n++;
        }
        return n; }""")
    check("the scrubber's rules are in a real stylesheet, not injected at runtime",
          has_rules >= 2,
          f"{has_rules} matching rules — grep both stylesheets AND injected "
          "<style> before believing a component has no rules")
    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for ok, _ in results if ok)
print(f"{passed}/{len(results)} passed")
if passed != len(results):
    print("FAILED: " + "; ".join(n for ok, n in results if not ok))
sys.exit(0 if passed == len(results) else 1)
