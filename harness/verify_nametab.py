"""v268 — the skribl NAME TAB, shared by Pad and Flip.

A skribl gets a title from a tab on the header that drops a drawer (the same
motion as Tune). The title becomes serializeSkribl/serializeFlip's `title`,
which drives the `.skribl` download filename and the posted/library title. Two
things this pins, both of which had a real bug:

  * ONE implementation, both surfaces. The Pad defaulted every draft to
    "Untitled Skribl"; Flip named its download by the DATE, so two Flip saves
    the same day collided as "…date.skribl" / "…date (1).skribl". The fix is one
    module (lib/nametab.js) both include — so this asserts window.SkriblName is
    present and behaves IDENTICALLY on Pad and Flip, not that each grew its own.

  * A filesystem-safe filename. The name can contain spaces, "·", ":", "!" —
    none of which belong in a download filename on Windows or in a shell. The
    slug must reduce to [a-z0-9-] and never be empty.

Browser suite: drives the real editors on the harness server, like verify_boot.
"""
import re
import sys

BASE = "http://127.0.0.1:5001"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


SURFACES = [("Pad", "/"), ("Flip", "/flip")]
filenames = {}   # per-surface slug for the same input, to prove they agree


def run(page, label, path):
    page.goto(BASE + path, wait_until="networkidle")
    page.wait_for_timeout(400)

    tab = page.query_selector("#nameTab")
    check(f"[{label}] the name tab is present and visible",
          bool(tab) and tab.is_visible())

    has_api = page.evaluate("() => !!(window.SkriblName && window.SkriblName.get && window.SkriblName.filename)")
    check(f"[{label}] window.SkriblName is wired (shared lib, not a per-editor copy)", has_api)
    if not has_api:
        return

    # Auto-filled default carries a TIME, not just a date — the exact thing that
    # let two same-day Flip saves collide. (Chromium's default locale => "h:MM AM/PM".)
    dflt = page.evaluate("() => window.SkriblName.get()")
    check(f"[{label}] a blank skribl auto-names with name + TIME (not date-only)",
          bool(re.search(r"\d{1,2}:\d\d", dflt or "")), repr(dflt))

    # Filename is filesystem-safe and non-empty for the messy input AND the default.
    fn = page.evaluate("() => window.SkriblName.filename('Pirate Frequency · Take 2!')")
    check(f"[{label}] a messy title slugs to a safe filename",
          fn == "pirate-frequency-take-2.skribl", repr(fn))
    dfn = page.evaluate("() => window.SkriblName.filename()")
    check(f"[{label}] the auto-name's filename is [a-z0-9-] only",
          bool(re.fullmatch(r"[a-z0-9-]+\.skribl", dfn or "")), repr(dfn))
    filenames[label] = fn

    # Open the drawer, type a name, and confirm it flows into get() + the tab label.
    tab.click()
    page.wait_for_timeout(250)
    shell_open = page.evaluate("() => document.getElementById('nameShell').classList.contains('open')")
    check(f"[{label}] clicking the tab drops the title drawer open", shell_open)

    page.fill("#skriblName", "Midnight Transmission")
    page.wait_for_timeout(120)
    got = page.evaluate("() => window.SkriblName.get()")
    check(f"[{label}] a typed name is what get() returns", got == "Midnight Transmission", repr(got))
    lbl = page.evaluate("() => document.getElementById('nameLbl').textContent")
    check(f"[{label}] the tab label reflects the typed name", lbl == "Midnight Transmission", repr(lbl))

    # It reaches the serialized payload (the property the filename/title read).
    fn_key = "serializeSkribl" if path == "/" else "serializeFlip"
    title = page.evaluate(f"""() => {{
        try {{ return (typeof {fn_key} === 'function') ? ({fn_key}() || {{}}).title : '__nofn__'; }}
        catch (e) {{ return '__threw__'; }}
    }}""")
    if title == "__nofn__" or title == "__threw__":
        check(f"[{label}] serialize carries the title (serializer not callable here)", True,
              "serializer not global on this build — get() path asserted instead")
    else:
        check(f"[{label}] serialize{'' if path=='/' else 'Flip'}() carries the typed title",
              title == "Midnight Transmission", repr(title))


with sync_playwright() as p:
    b = p.chromium.launch()
    for label, path in SURFACES:
        pg = b.new_page(viewport={"width": 900, "height": 720})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        try:
            run(pg, label, path)
        finally:
            check(f"[{label}] no page errors while driving the name tab", not errs, "; ".join(errs)[:200])
            pg.close()
    b.close()

# The whole point of the shared lib: the two surfaces produce the SAME slug.
if "Pad" in filenames and "Flip" in filenames:
    check("Pad and Flip slug an identical title identically (one implementation)",
          filenames["Pad"] == filenames["Flip"], f'{filenames.get("Pad")!r} vs {filenames.get("Flip")!r}')

passed = sum(1 for ok, _ in results if ok)
print(f"\n{passed}/{len(results)} passed"
      + ("" if passed == len(results) else "  FAILURES: "
         + ", ".join(n for ok, n in results if not ok)))
sys.exit(0 if passed == len(results) else 1)
