"""v232 — Smudge and Blur: the same sweep, two different verbs.

WHY BLUR NEARLY DID NOT EXIST. A frame is `{strokes, strokeGroups}` — a flat
array of `{x, y, color, size, t, erase, start}`. Liquify works because
displacement is expressible in a format made of points. You cannot blur a
polyline by moving its points, there is no raster layer to convolve, and adding
one is a format change the player must honour.

The way through is a detail of `paintStatic()`: a stroke whose FIRST point is
opaque is painted by `paintSeg` with each point's OWN colour and OWN size. So
per-point colour is honoured, and blur becomes sayable in this format — fade a
point toward the ground it sits on and widen it. It reads as defocus on line
art and the player renders it identically, because the player runs the same
paint path.

WHAT IT IS NOT, asserted here so nobody later mistakes it for a raster blur: it
cannot soften a photograph underneath, and it fades toward the page's background
colour rather than toward whatever is actually behind the line.

THE ASSERTION THAT MATTERS MOST is the one about sample rate. The obvious
implementation fades a little on every pointermove, which makes the tool's
strength a property of the HARDWARE — a 240Hz phone blurs several times harder
than a 60Hz laptop for the same gesture, and v230's coalesced sampling made that
worse on purpose. Measured before it was fixed, one short swipe took #ffffff to
rgb(87,89,92).

Saturating the accumulation was the obvious repair and it was NOT enough — it
bounds the maximum while a 4-event sweep still lands somewhere different from a
40-event one. What fixes it is accruing per PIXEL TRAVELLED: distance is the
quantity a brush physically deposits against, and it is the same number however
often the OS sampled the finger. Measured across that change, the gap between a
4-event and a 40-event sweep went from 117/255 to 6/255.

All of which is invisible in a screenshot, and is the thing most likely to be
"simplified" back out by someone who reads the accumulator as ceremony.
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


SNAP = """() => { const f = frame();
  return { pts: f.strokes.length, groups: f.strokeGroups.length,
           xs: f.strokes.map(p => Math.round(p.x * 10) / 10),
           ys: f.strokes.map(p => Math.round(p.y * 10) / 10),
           sizes: f.strokes.map(p => p.size),
           cols: f.strokes.map(p => p.color) }; }"""


def line(page, cx, cy):
    page.mouse.move(cx - 90, cy)
    page.mouse.down()
    for i in range(1, 10):
        page.mouse.move(cx - 90 + i * 20, cy)
    page.mouse.up()
    page.wait_for_timeout(300)


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(700)

        print("\nTHE LIB — arithmetic three tools share")
        check("lib/brushfield.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblBrushField") == "object",
              "a lib the template does not list is a lib that does not exist")
        for tool in ("smudge", "blur"):
            check(f"{tool} is in Flip's tool registry",
                  tool in page.evaluate("() => SkriblFlipTools.list()"),
                  str(page.evaluate("() => SkriblFlipTools.list()")))

        # Falloff. Sharpness is what separates Smudge from Liquify: same
        # traversal, a fingertip instead of a field.
        w = page.evaluate("""() => {
          const B = window.SkriblBrushField;
          return { centre: B.weight(0, 100, 1), edge: B.weight(100, 100, 1),
                   outside: B.weight(400, 100, 1),
                   soft: B.weight(25, 100, 1), sharp: B.weight(25, 100, 2.2) };
        }""")
        check("the falloff is 1 at the centre and 0 at the rim",
              w["centre"] == 1 and w["edge"] == 0 and w["outside"] == 0,
              str(w))
        check("a sharper falloff concentrates the effect under the touch",
              w["sharp"] < w["soft"],
              f"sharp={w['sharp']:.3f} soft={w['soft']:.3f} — this is the whole "
              "difference between Smudge and Liquify; equal, they are one tool "
              "shipped twice")

        # The colour mixer has to survive every form a colour takes here, and
        # refuse the ones it does not understand rather than guessing black.
        mixed = page.evaluate("""() => {
          const B = window.SkriblBrushField;
          return { hex: B.mix('#ffffff', '#000000', 0.5),
                   keepsAlpha: B.mix('rgba(255, 0, 0, 0.4)', '#000000', 0.5),
                   junk: B.mix('not-a-colour', '#000000', 0.5),
                   zero: B.mix('#ffffff', '#000000', 0) };
        }""")
        check("it mixes hex toward a target",
              mixed["hex"] == "rgb(128, 128, 128)", str(mixed["hex"]))
        check("...preserves an alpha the stroke already carried",
              "0.4" in mixed["keepsAlpha"],
              f"{mixed['keepsAlpha']} — blur must not quietly make a "
              "see-through stroke opaque")
        check("...and leaves a colour it cannot parse alone",
              mixed["junk"] == "not-a-colour",
              f"{mixed['junk']} — a parser that guesses turns one bad string "
              "into a silhouette")

        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

        print("\nSMUDGE — it moves ink and does not lay any")
        line(page, cx, cy)
        before = page.evaluate(SNAP)
        page.evaluate("() => setTool('smudge')")
        page.wait_for_timeout(200)
        page.mouse.move(cx, cy)
        page.mouse.down()
        for i in range(1, 7):
            page.mouse.move(cx, cy - i * 8)
        page.mouse.up()
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        check("smudge displaces points that were under the brush",
              after["ys"] != before["ys"],
              "nothing moved — the sweep did not reach the ink")
        check("...and subdivides so the pull curves instead of kinking",
              after["pts"] > before["pts"],
              f"{before['pts']} -> {after['pts']} points; two vertices in a "
              "brush can only bend into a corner")
        check("smudge lays NO new stroke of its own",
              after["groups"] == before["groups"],
              f"{before['groups']} -> {after['groups']} groups — a tool that "
              "works on existing ink must not also draw")
        # THE REPORT THAT SENT THIS BACK: "3rd is smudge. Looks like liquefy."
        # It did, because it WAS — displacement with two constants changed. Real
        # smudged paint thins as it travels: there is only so much pigment and
        # dragging spreads it over more area. So smudge also fades and widens
        # what it carries, which is the difference a user actually sees.
        smeared = sum(1 for a, q in zip(after["cols"], before["cols"]) if a != q)
        check("smudge SMEARS as well as displacing",
              smeared > 0,
              f"{smeared} points recoloured — displacement alone is Liquify, "
              "and changing its constants gives you a sharper Liquify, not a "
              "different tool")

        # The smear needs per-point scratch state, and points are serialised
        # wholesale into every saved draft and shared Skribl. A scratch field
        # parked on the point would ride into the payload and past the server's
        # validator; it lives in a WeakMap keyed by the point instead.
        keys = page.evaluate("() => Object.keys(frame().strokes[2] || {})")
        check("smudge leaves no scratch fields on the points",
              all(not k.startswith("_") for k in keys),
              f"{keys} — a point is a payload field, not a scratchpad")

        page.evaluate("() => undoStroke()")
        page.wait_for_timeout(400)
        u = page.evaluate(SNAP)
        check("one undo restores the frame exactly",
              u["xs"] == before["xs"] and u["ys"] == before["ys"]
              and u["pts"] == before["pts"] and u["cols"] == before["cols"],
              "the snapshot undo has to cover the inserted points AND the smear")

        print("\nBLUR — fades and widens, because it cannot convolve")
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        line(page, cx, cy)
        before = page.evaluate(SNAP)
        page.evaluate("() => setTool('blur')")
        page.wait_for_timeout(200)
        page.mouse.move(cx - 40, cy)
        page.mouse.down()
        for i in range(1, 6):
            page.mouse.move(cx - 40 + i * 12, cy)
        page.mouse.up()
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        grew = sum(1 for a, q in zip(after["sizes"], before["sizes"]) if a > q)
        faded = sum(1 for a, q in zip(after["cols"], before["cols"]) if a != q)
        check("blur widens the points it touches", grew > 0, f"{grew} widened")
        check("...and fades them toward the ground", faded > 0, f"{faded} recoloured")
        check("blur adds and removes NO points",
              after["pts"] == before["pts"] and after["groups"] == before["groups"],
              f"{before['pts']}/{before['groups']} -> {after['pts']}/{after['groups']} "
              "— it recolours in place; splitting would cost points and blow "
              "LAYER_BUDGET on translucent strokes")

        # THE ONE THAT WOULD ROT SILENTLY. One long sweep and one short one over
        # the same ink must land in the same place, or the tool's strength is a
        # property of the device's sample rate.
        rates = page.evaluate("""async () => {
          const run = (steps) => {
            localStorage.clear();
            frames.length = 0; frames.push({strokes: [], strokeGroups: [], hold: 1});
            idx = 0;
            const f = frame(), now = performance.now();
            for (let i = 0; i < 10; i++)
              f.strokes.push({ x: 100 + i * 12, y: 200, color: '#ffffff',
                               size: 6, t: now + i, erase: false, start: i === 0 });
            f.strokeGroups.push(10);
            setTool('blur');
            fieldBegin({ x: 100, y: 200 }, 'Blur');
            for (let k = 1; k <= steps; k++)
              blurMove({ x: 100 + (220 * k / steps), y: 200 });
            fieldEnd();
            return f.strokes[4].color;
          };
          return { few: run(4), many: run(40) };
        }""")
        import re as _re
        def _chan(c):
            return [int(v) for v in _re.findall(r"\d+", c)[:3]]
        gap = max(abs(a - b) for a, b in zip(_chan(rates["few"]), _chan(rates["many"])))
        # NOT exact equality, and the tolerance is doing real work rather than
        # papering over a miss. Weight varies across the brush, so integrating
        # it from 4 samples cannot equal integrating it from 40 — that residual
        # is arithmetic, not a bug. Measured: 117/255 apart when the accrual was
        # per EVENT, 6/255 apart once it was per pixel travelled. A threshold of
        # 16 accepts the sampling residual and still fails the real defect by a
        # factor of seven.
        check("a fast sweep and a slow one converge on the same blur",
              gap <= 16,
              f"4 events -> {rates['few']}, 40 events -> {rates['many']}, "
              f"largest channel gap {gap} — a per-EVENT delta makes a 240Hz "
              "phone blur several times harder than a 60Hz laptop for the same "
              "gesture, and v230's coalesced sampling raised that rate on "
              "purpose. Accrue per pixel travelled instead.")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
