"""The autosave pill yields to the controls it would sit on — except when warning.

THE DEFECT. `.autosave-status` is position:fixed at bottom-left. On a phone the
tool row is ALSO at the bottom, so the pill lands squarely on it: measured on
both surfaces at every phone size, Flip's "Saved" sits on the pen button and
Pad's on its toolbar. Desktop never collides, which is why this lasted — it is
invisible on the machine it was built on.

A rule for a NEARBY case already existed: the pill fades while a drawer is open,
because "a pill covering a destructive button is worse than one you cannot see".
That rule was right and too narrow. It fixed the collision somebody noticed
rather than the general one, and CSS cannot ask whether two boxes intersect.

THE PART THAT NEEDED CARE. `failed` and `partial` (saved without media) stay on
screen deliberately — flip.js records why: "a warning that fades claims it was
resolved". Fading one because it happened to overlap would trade a cosmetic
problem for a durability one, silently, in the exact situation where the user
most needs telling. So the overlap rule applies to the reassuring states only,
and this suite spends most of its assertions on that distinction rather than on
the easy half.

The pill is pointer-events:none and always was, so none of this was ever about
blocking taps — it obscures a control without disabling it. Worth knowing when
weighing the fix, and asserted here so a later change cannot quietly make the
pill interactive and turn an overlap into a dead button.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


SET = """(state) => {
  const el = document.getElementById('autosaveStatus');
  el.hidden = false;
  el.classList.remove('saving', 'failed', 'partial', 'blocked');
  if (state) el.classList.add(state);
  el.classList.add('show');
}"""
READ = """() => {
  const el = document.getElementById('autosaveStatus');
  const r = el.getBoundingClientRect();
  let over = null;
  for (const sel of (window.SkriblPillFit ? window.SkriblPillFit.TARGETS : [])) {
    const c = document.querySelector(sel);
    if (!c) continue;
    const b = c.getBoundingClientRect();
    if (!b.width || !b.height) continue;
    if (!(r.right <= b.left || r.left >= b.right ||
          r.bottom <= b.top || r.top >= b.bottom)) { over = sel; break; }
  }
  return { blocked: el.classList.contains('blocked'),
           opacity: Math.round(parseFloat(getComputedStyle(el).opacity) * 100) / 100,
           pointer: getComputedStyle(el).pointerEvents,
           overlaps: over };
}"""

SURFACES = [("Flip", "/flip"), ("Pad", "/")]

with sync_playwright() as p:
    browser = p.chromium.launch()

    print("PILL — the library is present on both editors")
    for label, path in SURFACES:
        page = browser.new_page(viewport={"width": 393, "height": 852})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(1200)
        check(f"{label}: lib/pillfit.js is loaded",
              page.evaluate("() => !!window.SkriblPillFit"),
              "the player has no autosave and deliberately does not load it")
        check(f"{label}: the pill never intercepts taps",
              page.evaluate(READ)["pointer"] == "none",
              "it obscures a control without disabling it — and must keep doing "
              "only that, or an overlap becomes a dead button")
        page.close()

    for label, path in SURFACES:
        print(f"\nPILL [{label}] — on a phone it gets out of the way")
        page = browser.new_page(viewport={"width": 393, "height": 852})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(1300)

        page.evaluate(SET, None)
        page.wait_for_timeout(600)
        r = page.evaluate(READ)
        check(f"{label}: the pill DOES overlap a control at phone size",
              r["overlaps"] is not None,
              f"{r['overlaps']} — if this stops being true the rest of this "
              f"section proves nothing, so it is asserted rather than assumed")
        check(f"{label}: ...so 'Saved' fades out of the way",
              r["blocked"] and r["opacity"] == 0,
              f"blocked={r['blocked']} opacity={r['opacity']}")

        # THE ASSERTION THIS SUITE EXISTS FOR.
        for state, name in (("failed", "Autosave failed"), ("partial", "Saved without media")):
            page.evaluate(SET, state)
            page.wait_for_timeout(600)
            w = page.evaluate(READ)
            check(f"{label}: '{name}' stays VISIBLE even though it overlaps",
                  (not w["blocked"]) and w["opacity"] == 1,
                  f"blocked={w['blocked']} opacity={w['opacity']} — a warning "
                  f"that fades claims it was resolved; hiding it would trade a "
                  f"cosmetic problem for a durability one")
        page.close()

        print(f"PILL [{label}] — on a desktop it stays put")
        page = browser.new_page(viewport={"width": 1100, "height": 900})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(1300)
        page.evaluate(SET, None)
        page.wait_for_timeout(600)
        d = page.evaluate(READ)
        check(f"{label}: no overlap at desktop size",
              d["overlaps"] is None, f"{d['overlaps']}")
        check(f"{label}: ...so the pill shows normally",
              (not d["blocked"]) and d["opacity"] == 1,
              f"blocked={d['blocked']} opacity={d['opacity']} — the fix must not "
              f"cost the pill on the sizes where it never collided")

        # A resize is the cheapest way to be sure this is live rather than
        # decided once at load: the same page, same pill, different verdict.
        page.set_viewport_size({"width": 393, "height": 852})
        page.wait_for_timeout(700)
        page.evaluate(SET, None)
        page.wait_for_timeout(600)
        rz = page.evaluate(READ)
        check(f"{label}: shrinking the window re-decides it",
              rz["blocked"], f"blocked={rz['blocked']} — decided at load rather "
                             f"than on layout would leave a rotated phone wrong")
        page.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
