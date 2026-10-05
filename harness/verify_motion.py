"""No one-frame jumps: what changes on screen in response to a tap, changes over time.

The owner, on the motion review: "No snaps, smooth transitions are good." A
recorded survey of both editors found a dozen places where a whole panel, the
header's contents or the page itself moved in a single frame. This suite pins
each one that was fixed, by the property that was fixed.

THE INSTRUMENT IS THE PAGE'S OWN FRAME CLOCK, NOT A VIDEO. The survey was first
run on Playwright's screen recording, and that recording DROPS FRAMES while the
page is busy -- the first stroke starts a take, which is exactly then -- so a
fade measured at 60fps in the page showed up on video as a one-frame cut. A
video would go red on a smooth tree. So every assertion here samples computed
style once per requestAnimationFrame, inside the page, and asks how many frames
sat BETWEEN the before and after values. A cut has none. A transition has
several; at least two are required, which a 0.15s fade clears even when a
loaded runner gives it only a handful of frames.

A RECT IS NOT A PAINT, and nothing here needs one: each assertion is about how
a value moves over time, never about whether something is visible.

Calibrated red, per component, against: the header's fade-through removed (the
mark and the readout each), the scrub bar's allow-discrete removed, the Media
card's opacity transition removed, the drawer contents' fade removed, the page
height hold removed (Pad and Flip each), Flip's scroll home put back to
'auto', the popovers' transition removed, the
Flip menu dim's animation removed, and the pill put back on its spring.
"""
import re, sys, math
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []
check = make_check(results)

# Samples [selector, what] once per frame for `ms`, into window.__mo. Started
# without awaiting, so the action under test runs while it records.
SAMPLER = """([probes, ms]) => { window.__mo = null; const out = []; const t0 = performance.now();
  const read = ([sel, what]) => {
    if (what === 'replaying') return document.body.classList.contains('replaying');
    const e = document.querySelector(sel); if (!e) return null;
    const c = getComputedStyle(e);
    if (what === 'top') return e.getBoundingClientRect().top;
    if (what === 'display') return c.display;
    if (what === 'fillAlpha') { const m = c.backgroundColor.match(/[\\d.]+/g);
      return !m ? 0 : (m.length > 3 ? +m[3] : 1); }
    return parseFloat(c[what]); };
  (function tick(t) { out.push(probes.map(read)); if (t - t0 < ms) requestAnimationFrame(tick); else window.__mo = out; })(t0); }"""


def record(pg, probes, ms, action):
    pg.evaluate(SAMPLER, [probes, ms])
    action()
    pg.wait_for_function("() => window.__mo !== null", timeout=ms + 10000)
    return pg.evaluate("window.__mo")


def between(vals, a, b, margin=0.05):
    """Frames strictly between a and b: zero for a cut."""
    lo, hi = min(a, b) + margin, max(a, b) - margin
    return sum(1 for v in vals if isinstance(v, (int, float)) and lo < v < hi)


def phone(b, **kw):
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                        has_touch=True, color_scheme="dark", **kw)
    return ctx, ctx.new_page()


def open_editor(pg, path):
    browsing.goto(pg, BASE, path)
    pg.wait_for_timeout(1200)
    pg.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    pg.wait_for_timeout(400)


def stroke(pg, dy=0):
    box = pg.locator("#canvas").bounding_box()
    x, y = box["x"] + 90, box["y"] + 180 + dy
    pg.mouse.move(x, y); pg.mouse.down()
    for i in range(25):
        pg.mouse.move(x + i * 6, y + 18 * math.sin(i / 5)); pg.wait_for_timeout(12)
    pg.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nTHE FIRST STROKE (Pad, phone) — a fade-through, not a cut")
    ctx, pg = phone(b)
    open_editor(pg, "/skribl-pad")
    rows = record(pg, [[".header > .brand", "opacity"], ["#recIndicator", "opacity"],
                       [".header > .brand", "display"]], 900, lambda: stroke(pg))
    brand = [r[0] for r in rows if r[2] != "none"]
    check("the mark and the controls fade out over several frames",
          between(brand, 1, 0) >= 2, f"{between(brand, 1, 0)} frames between")
    check("...and are gone once they have", rows[-1][2] == "none", rows[-1][2])
    rec = [r[1] for r in rows]
    check("the take's readout fades in over several frames",
          between(rec, 0, 1) >= 2 and rec[-1] > 0.95, f"{between(rec, 0, 1)} frames between, ends {rec[-1]}")

    print("\nAFTER THE TAKE — what the header gains fades in")
    stroke(pg, 60); pg.wait_for_timeout(500)
    rows = record(pg, [["#playWrap", "opacity"]], 700, lambda: pg.click("#recordBtn"))
    play = [r[0] for r in rows if r[0] is not None]
    check("Play arrives over several frames", between(play, 0, 1) >= 2,
          f"{between(play, 0, 1)} frames between")

    print("\nA DRAWER SWAP — Pen's drawer to Media")
    if pg.evaluate("() => document.getElementById('drawPanel').hidden"):
        pg.click("#penToolBtn")
    pg.wait_for_timeout(700)
    pen_open = pg.evaluate("() => !document.getElementById('drawPanel').hidden")
    rows = record(pg, [[".media-card > .media-tabs", "opacity"], [".media-card", "display"]], 600,
                  lambda: pg.click("#mediaOpenBtn"))
    tabs = [r[0] for r in rows if r[1] != "none"]
    check("Pen's drawer was open, so this is the swap", pen_open)
    check("the Media card's contents fade in rather than appearing whole",
          bool(tabs) and tabs[0] < 0.5 and between(tabs, 0, 1) >= 2,
          f"first {tabs[:1]}, {between(tabs, 0, 1)} frames between")

    print("\nTHE END OF A REPLAY — the scrub bar and the card return calmly")
    pg.wait_for_timeout(600)
    rows = record(pg, [[".play-scrub", "opacity"], ["#mediaCard", "opacity"], [None, "replaying"]],
                  4500, lambda: pg.click("#playBtn"))
    ends = [i for i in range(1, len(rows)) if rows[i - 1][2] and not rows[i][2]]
    after = rows[ends[0]:] if ends else []
    check("the replay ran and ended inside the window", bool(ends), f"{len(rows)} frames")
    scrub = [r[0] for r in after if r[0] is not None]
    check("the scrub bar fades out as it stands",
          between(scrub, 1, 0) >= 2, f"{between(scrub, 1, 0)} frames between")
    # The card is the colour block: opaque, no backdrop-filter, so it recedes
    # by its own opacity (the glass card dropped its fill instead).
    card = [r[1] for r in after if r[1] is not None]
    check("the Media card comes back over several frames",
          bool(card) and card[0] < 0.5 and card[-1] > 0.95 and between(card, 0, 1) >= 2,
          f"first {card[:1]}, last {card[-1:]}, {between(card, 0, 1)} frames between")

    print("\nPOPOVERS — the shape picker")
    pg.click("#mediaOpenBtn"); pg.wait_for_timeout(700)
    rows = record(pg, [["#shapePop", "opacity"], ["#shapePop", "display"]], 500,
                  lambda: pg.click("#shapeToolBtn"))
    sp = [r[0] for r in rows if r[1] != "none"]
    check("the shape picker opens over several frames", between(sp, 0, 1) >= 2,
          f"{between(sp, 0, 1)} frames between")
    rows = record(pg, [["#shapePop", "opacity"], ["#shapePop", "display"]], 500,
                  lambda: pg.keyboard.press("Escape"))
    sp = [r[0] for r in rows if r[1] != "none"]
    check("...and closes over several frames", between(sp, 1, 0) >= 2,
          f"{between(sp, 1, 0)} frames between")
    ctx.close()

    def drawer_close(path, bar):
        ctx, pg = phone(b)
        open_editor(pg, path)
        pg.click("#mediaOpenBtn"); pg.wait_for_timeout(1200)
        scrolled = pg.evaluate("scrollY")
        rows = record(pg, [[bar, "top"]], 900, lambda: pg.click("#mediaOpenBtn"))
        tops = [r[0] for r in rows]
        ctx.close()
        return scrolled, tops

    for name, path, bar in (("Pad", "/skribl-pad", "#toolBar"), ("Flip", "/flip", ".flip-tools")):
        print(f"\nCLOSING THE LAST DRAWER ({name}) — the page glides home")
        scrolled, tops = drawer_close(path, bar)
        check(f"{name}: opening Media scrolled the page, so closing it has somewhere to go",
              scrolled > 40, f"scrollY {scrolled}")
        mid = between(tops, tops[0], tops[-1], 20)
        check(f"{name}: the tool row passes through several positions on its way down, never one jump",
              abs(tops[-1] - tops[0]) > 40 and mid >= 3, f"{tops[0]:.0f} -> {tops[-1]:.0f}, {mid} frames between")

    print("\nFLIP — the tool tray and the menu's dim")
    ctx, pg = phone(b)
    open_editor(pg, "/flip")
    rows = record(pg, [["#toolTray", "opacity"]], 500, lambda: pg.click("#toolMoreBtn"))
    tt = [r[0] for r in rows if r[0] is not None]
    check("the tool tray opens over several frames", between(tt, 0, 1) >= 2,
          f"{between(tt, 0, 1)} frames between")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
    rows = record(pg, [["#moreScrim", "opacity"], ["#moreScrim", "display"]], 600, lambda: pg.click("#moreBtn"))
    sc = [r[0] for r in rows if r[1] != "none"]
    check("the menu's dim comes up over several frames", bool(sc) and between(sc, 0, 1) >= 2,
          f"{between(sc, 0, 1) if sc else 0} frames between")
    ctx.close()

    print("\nTHE PILL — calm, with no overshoot")
    ctx, pg = phone(b)
    open_editor(pg, "/skribl-pad")
    tr = pg.evaluate("""() => { const c = getComputedStyle(document.querySelector('.tool-slider'));
        return [c.transitionProperty, c.transitionDuration, c.transitionTimingFunction]; }""")
    props = [x.strip() for x in tr[0].split(",")]
    durs = [float(x.strip()[:-1]) for x in tr[1].split(",")]
    funcs = re.findall(r"cubic-bezier\(([^)]*)\)|(ease(?:-in-out|-in|-out)?|linear)", tr[2])
    moves = [i for i, pr in enumerate(props) if pr in ("transform", "width")]
    check("the pill moves in 0.3s or less", moves and all(durs[i] <= 0.3 for i in moves), str(tr))
    ys = []
    for f in funcs:
        if f[0]:
            pts = [float(v) for v in f[0].split(",")]
            ys += [pts[1], pts[3]]
    check("...and never past where it is going (no control point above 1)",
          all(0 <= y <= 1 for y in ys), str(tr[2]))
    ctx.close()
    b.close()

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("  FAILURES: " + ", ".join(r[1] for r in bad) if bad else ""))
sys.exit(1 if bad else 0)
