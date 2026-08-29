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
  el.classList.remove('saving', 'failed', 'partial', 'blocked', 'lifted');
  el.style.removeProperty('--pill-lift');
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
  // What the pill WOULD hit if it were not lifted. The precondition of this
  // whole section is that a phone collides; once the fix lifts the pill clear,
  // measuring the live rect can no longer show that, and a precondition that
  // quietly stops being checkable is how a section starts proving nothing.
  const lift = parseFloat(el.style.getPropertyValue('--pill-lift')) || 0;
  const u = { left: r.left, right: r.right, top: r.top + lift, bottom: r.bottom + lift };
  let uOver = null;
  for (const sel of (window.SkriblPillFit ? window.SkriblPillFit.TARGETS : [])) {
    const c = document.querySelector(sel);
    if (!c) continue;
    const b = c.getBoundingClientRect();
    if (!b.width || !b.height) continue;
    if (!(u.right <= b.left || u.left >= b.right ||
          u.bottom <= b.top || u.top >= b.bottom)) { uOver = sel; break; }
  }
  return { blocked: el.classList.contains('blocked'),
           lifted: el.classList.contains('lifted'),
           lift: lift,
           opacity: Math.round(parseFloat(getComputedStyle(el).opacity) * 100) / 100,
           pointer: getComputedStyle(el).pointerEvents,
           overlaps: over,
           overlapsUnlifted: uOver };
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
        check(f"{label}: the pill WOULD overlap a control at phone size",
              r["overlapsUnlifted"] is not None,
              f"{r['overlapsUnlifted']} — if this stops being true the rest of "
              f"this section proves nothing, so it is asserted rather than "
              f"assumed. Measured un-lifted on purpose: the fix moves the pill "
              f"clear, so the live rect no longer shows the collision it exists "
              f"to solve")
        # ⚑ CHANGED IN v229, DELIBERATELY, AND IT IS A BEHAVIOUR CHANGE.
        # This used to assert `blocked and opacity == 0` — that fading was the
        # correct answer to the collision. It is not, and the bug report proves
        # it: on a phone the collision is PERMANENT, so the remedy ran every
        # time and the reassuring "Saved" was never visible on a phone at all.
        # The user's words were "on pad I'm not seeing saved at all on
        # autosave". The invariant worth holding was never "it fades"; it is
        # "it does not cover a control" — which lifting satisfies while still
        # telling the user their work is safe.
        check(f"{label}: ...so 'Saved' lifts clear instead of vanishing",
              r["lifted"] and r["lift"] > 0 and r["opacity"] == 1
              and r["overlaps"] is None,
              f"lifted={r['lifted']} lift={r['lift']} opacity={r['opacity']} "
              f"overlaps={r['overlaps']} — a status that hides itself on every "
              f"phone is a status that does not exist")

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
              rz["lifted"] and rz["overlaps"] is None,
              f"lifted={rz['lifted']} overlaps={rz['overlaps']} — decided at "
              f"load rather than on layout would leave a rotated phone wrong")
        page.close()

    print("\nPILL — the fitter settles instead of spinning")
    # WHY. sync() writes the pill's class and style; this library OBSERVES the
    # pill's class attribute. `classList.remove()` sets the attribute even when
    # the token was absent, and setting an attribute fires a MutationObserver
    # record even when the value does not change — so every unconditional write
    # fed the observer, which scheduled another frame, forever. Measured on a
    # phone viewport three seconds after everything had settled, with the pill
    # HIDDEN: 133 mutations before the guard, 364 once lifting added two more
    # writes per pass, 0-3 after. A drawing app holding a requestAnimationFrame
    # loop open while nothing happens is spending a phone battery on nothing.
    #
    # The threshold is deliberately not zero: the pill's own fade-out is a real
    # transition and lands in this window. It IS far below frame rate, which is
    # the only thing that distinguishes settled from spinning.
    for label, path in SURFACES:
        page = browser.new_page(viewport={"width": 393, "height": 852})
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(1300)
        page.evaluate(SET, None)
        page.wait_for_timeout(2500)          # let it show, settle and fade
        page.evaluate("""() => { window.__mut = 0;
          new MutationObserver(ms => { window.__mut += ms.length; })
            .observe(document.getElementById('autosaveStatus'),
                     { attributes: true, attributeFilter: ['class', 'style'] }); }""")
        page.wait_for_timeout(3000)          # three QUIET seconds
        n = page.evaluate("() => window.__mut")
        check(f"{label}: the pill stops being written to when nothing changes",
              n < 20,
              f"{n} attribute writes in 3 idle seconds — anything near frame "
              f"rate (180+) is sync() feeding its own MutationObserver")
        page.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
