"""No sheet should ever scroll sideways.

Reported from the live demo as "why does this have sliders?" — the post composer
showed a horizontal scrollbar AND a vertical one on a desktop window. Two
separate causes, both of which are the same shape: a value copied into an
override without the value it was paired with.

  HORIZONTAL. `.post-submit` had `width: calc(100% - 20px)` beside
  `margin: 2px 10px 6px`. Those two numbers have to be kept in step by hand, and
  the desktop override (`#postSheet .post-submit`) changed the margin to 12px
  and left the width alone. The button then measured 100% + 4px and the sheet
  overflowed by exactly four pixels, at EVERY desktop viewport — it was not a
  narrow-window edge case. Measured before the fix: scrollWidth 462 against
  clientWidth 458, with no child element extending past the sheet's right edge,
  which is why eyeballing the layout found nothing.

  WHY FOUR PIXELS WERE VISIBLE AT ALL. `.menu-sheet` sets `overflow-y: auto` so
  a tall sheet can scroll. Per spec, when one axis is not `visible` the other
  computes from `visible` to `auto` — so `overflow-x` became `auto` even though
  nobody wrote it anywhere in either stylesheet. A four-pixel overflow that
  would otherwise have been ignored got a scrollbar instead.

  VERTICAL. `.menu-sheet` also sets `max-height: calc(100dvh - 88px)`, where 88
  is the corner dropdown's geometry: 64px of `top` plus 24px of clearance.
  #postSheet is a CENTRED modal that sets `top: auto`, so it was reserving 64
  pixels it does not use and scrolling that much sooner than it had to.

THE ASSERTION IS THE GENERAL RULE, not the two fixes. A sheet whose content is
wider than its own scroll box is always a bug — there is nothing in any of these
dialogs a user should scroll horizontally to reach — so this checks the invariant
on every sheet it can open, at four viewports, rather than checking that one
button is 414 pixels wide. Vertical overflow is NOT asserted the same way: a
sheet taller than a short window is supposed to scroll. What is asserted there is
that the tallest sheet fits in a window it comfortably should.
"""
import math
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORT = 5016
BASE = f"http://127.0.0.1:{PORT}"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


FIT = """(id) => {
  const s = document.getElementById(id);
  if (!s) return null;
  const r = s.getBoundingClientRect();
  if (!s.offsetParent && getComputedStyle(s).position !== 'fixed') return null;
  if (r.width < 40) return null;                 // not laid out; see the gate
  // Name the widest child, so a failure says WHAT overflowed rather than only
  // that something did. Measured against the padding box, which is what
  // scrollWidth is relative to.
  const bl = parseFloat(getComputedStyle(s).borderLeftWidth) || 0;
  let worst = null;
  for (const el of s.querySelectorAll('*')) {
    const er = el.getBoundingClientRect();
    const rel = er.right - (r.left + bl);
    if (!worst || rel > worst.rel) {
      worst = {rel: Math.round(rel),
               what: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')};
    }
  }
  return {w: Math.round(r.width), h: Math.round(r.height),
          scrollW: s.scrollWidth, clientW: s.clientWidth,
          scrollH: s.scrollHeight, clientH: s.clientHeight,
          overflowX: getComputedStyle(s).overflowX, worst};
}"""

env = dict(os.environ, DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/sheets.db",
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           SECRET_KEY="harness-sheetfit")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    sys.exit("SKIP: instance did not start.")


def author(pg):
    """Draw a real take, because both sheets refuse to open without content."""
    box = pg.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(30):
        a, r = (i / 30) * math.pi * 3, 20 + (i / 30) * 110
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 10 == 0:
            pg.wait_for_timeout(80)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)


VIEWPORTS = [(1280, 900), (1138, 1401), (1280, 700), (390, 844)]

try:
    with sync_playwright() as sp:
        b = sp.chromium.launch()

        print("\nSHEET FIT — nothing is reachable only by scrolling sideways")
        measured = 0
        for vw, vh in VIEWPORTS:
            pg = b.new_page(viewport={"width": vw, "height": vh})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/", wait_until="load")
            pg.wait_for_timeout(900)
            author(pg)

            for trigger, sheet_id, label in (("#postBtn", "postSheet", "post composer"),
                                             ("#menuBtn >> then >> #exportItem",
                                              "exportSheet", "export sheet")):
                try:
                    # The export sheet has no top-level button: it opens from the
                    # overflow menu, so the trigger is two clicks. Spelled out
                    # rather than guessed — an #exportBtn that does not exist
                    # fails silently through the except below and the sheet is
                    # never measured, which is exactly what happened the first
                    # time this suite ran.
                    for step in trigger.split(" >> then >> "):
                        pg.click(step, timeout=3000)
                        pg.wait_for_timeout(350)
                except Exception:
                    continue
                pg.wait_for_timeout(700)
                m = pg.evaluate(FIT, sheet_id)
                if not m:
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(300)
                    continue
                measured += 1
                check(f"{label} at {vw}x{vh} does not scroll sideways",
                      m["scrollW"] <= m["clientW"],
                      f"scrollWidth {m['scrollW']} vs clientWidth {m['clientW']}"
                      + (f"; widest child {m['worst']['what']} reaches "
                         f"{m['worst']['rel']}" if m["worst"] else ""))
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(400)

            check(f"no uncaught error at {vw}x{vh}", not errs, "; ".join(errs)[:160])
            pg.close()

        # GATE. Every assertion above is skipped silently if a sheet never opens
        # or never lays out, and a run of zero measurements would report a clean
        # pass. Say how many were actually taken.
        check("FIXTURE GATE: sheets were actually opened and measured",
              measured >= 2 * len(VIEWPORTS),
              f"{measured} measurements across {len(VIEWPORTS)} viewports "
              f"— expected both sheets at each")

        print("\nSHEET FIT — the composer fits a window it should fit")
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(BASE + "/", wait_until="load")
        pg.wait_for_timeout(900)
        author(pg)
        pg.click("#postBtn")
        pg.wait_for_timeout(700)
        m = pg.evaluate(FIT, "postSheet")
        # Not "never scrolls vertically" — a short window SHOULD scroll. The
        # claim is that the centred modal stops reserving the corner dropdown's
        # 64px of `top`, which is what made it scroll early.
        check("the post composer does not scroll vertically at 1280x800",
              m and m["scrollH"] <= m["clientH"],
              f"content {m and m['scrollH']} in {m and m['clientH']}")
        pg.close()
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
