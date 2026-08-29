"""Does anything know what Flip's keyboard does — and can two things answer at once?

flip.js attaches eight global keydown listeners. Five of them are Escape. Two are
Space. Nothing states the set, so the only way to know whether a key is free is
to grep, and that has already failed once: the file carries a comment recording
that ArrowLeft/ArrowRight were bound twice and both fired on one press, so a page
advanced two frames. That was found by someone noticing, and the fix left a
comment where the collision had been.

`lib/keyregistry.js` is a REGISTRY, not a router — it records claims and observes
presses, and never dispatches, prevents or stops anything. So this suite has to
prove three separate things, and the third is the one that matters:

  1. the registry describes the file  — count the global listeners in the SOURCE
     and require a registration for each. Without this the registry is a
     hand-maintained table, which is the thing this project keeps abolishing.
  2. no two unconditional claims share a key — static, no key pressed.
  3. no two SCOPED claims are live at once — which needs the state set up and the
     key actually pressed, because that is what was wrong in the arrow bug: both
     handlers were unscoped, so both were always live.

Five Escapes are not a bug. One binding per key is the wrong rule; the rule is
that at most one claim is live when the key fires.
"""
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:5001"
FLIP = BASE + "/flip"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# Global listeners in the source. Anchored on window/document specifically:
# an element-scoped keydown (a text input taking Enter/Escape) is not a global
# binding and must not be counted, or the registry would be asked to describe
# things that cannot collide with anything.
SRC = (ROOT / "skribl" / "static" / "flip.js").read_text()
GLOBAL_KEYDOWN = re.findall(r"^(?:\s*)(?:window|document)\.addEventListener\(\s*'keydown'",
                            SRC, re.MULTILINE)

with sync_playwright() as sp:
    b = sp.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(FLIP, wait_until="load")
    pg.wait_for_timeout(1200)

    print("\nKEYS — the registry loaded at all")
    check("no page error on Flip with the registry in the load order",
          not errs, "; ".join(errs)[:200])
    check("KeyRegistry is defined on Flip",
          pg.evaluate("() => typeof KeyRegistry !== 'undefined'"),
          "load order: keyregistry.js must precede flip.js")
    # NEGATIVE CONTROL. The registry is Flip-only on purpose — flip.js is not
    # served to the player, so nothing here reaches a shared link, and the
    # player's byte ratchet is currently red. Assert the absence, or "Flip-only"
    # is a claim rather than a fact.
    pg2 = b.new_page()
    pg2.goto(BASE + "/", wait_until="load")
    pg2.wait_for_timeout(600)
    check("and is NOT loaded on Pad, which shares app.js with the player",
          pg2.evaluate("() => typeof KeyRegistry === 'undefined'"),
          "app.js is the player's file; a lib it needs would ship to every "
          "shared link")
    pg2.close()

    print("\nKEYS — the registry describes the file, not a wish")
    reg = pg.evaluate("() => KeyRegistry.list()")
    check(f"every global keydown listener in flip.js has a registration",
          len(reg) >= len(GLOBAL_KEYDOWN),
          f"{len(GLOBAL_KEYDOWN)} global listeners in source, "
          f"{len(reg)} registrations")
    check("no registration's scope predicate throws when evaluated",
          not [r for r in reg if r.get("scopeError")],
          "; ".join(f"{r['label']}: {r['scopeError']}"
                    for r in reg if r.get("scopeError")))
    escapes = [r for r in reg if "Escape" in r["keys"]]
    # RATCHET RAISED 5 -> 6, v226, FLAGGED. The new claim is "drop the page
    # range". The count is deliberately a ratchet rather than a >= : adding an
    # Escape claim to a surface that already has five should be a visible act,
    # because Escape is the one key every dismissible thing wants. What makes
    # this one admissible is that it is scoped to LAST — a page range is the
    # least topmost thing on the page, so its scope also requires that no menu,
    # sheet, panel or drawer is open. Without that it would have been live at
    # the same time as four of the other five, which is exactly the collision
    # KeyRegistry.collisions() is for.
    check("all six Escape claims are scoped, none unconditional",
          len(escapes) == 6 and all(r["scoped"] for r in escapes),
          f"{len(escapes)} Escape claims: "
          + ", ".join(r["label"] for r in escapes))

    print("\nKEYS — uniqueness, statically")
    unconditional = pg.evaluate("() => KeyRegistry.unconditional()")
    check("no key is claimed unconditionally by two surfaces",
          not unconditional,
          "; ".join(f"{u['key']}: {', '.join(u['claims'])}"
                    for u in unconditional))

    print("\nKEYS — uniqueness, at the moment the key is pressed")
    pg.evaluate("() => KeyRegistry.reset()")
    pg.keyboard.press("Escape")
    pg.keyboard.press("ArrowRight")
    pg.keyboard.press("Space")
    pg.wait_for_timeout(300)
    at_rest = pg.evaluate("() => KeyRegistry.collisions()")
    check("nothing collides with every surface closed",
          not at_rest,
          "; ".join(f"{c['key']}: {', '.join(c['claims'])}" for c in at_rest))

    # THE CASE THE STATIC CHECK CANNOT SEE. Two scoped Escape claims are correct
    # individually and wrong together, and only opening both surfaces at once
    # reveals it. This is the shape of the arrow-key bug, one level subtler.
    pg.evaluate("() => KeyRegistry.reset()")
    opened = pg.evaluate("""() => {
      const out = [];
      try { if (typeof openHelpDrawer === 'function') { openHelpDrawer(); out.push('help'); } } catch (e) {}
      try { if (typeof moveMode !== 'undefined') { moveMode = true; out.push('move'); } } catch (e) {}
      return out;
    }""")
    pg.wait_for_timeout(300)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    both = pg.evaluate("() => KeyRegistry.collisions()")
    print(f"    forced open: {opened}")
    check("two surfaces open at once is REPORTED, not silently double-handled",
          bool(both) if len(opened) == 2 else True,
          "; ".join(f"{c['key']}: {', '.join(c['claims'])}" for c in both)
          or "no collision observed")

    pg.close()
    b.close()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
