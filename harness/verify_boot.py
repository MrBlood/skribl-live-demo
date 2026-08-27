"""Both editor scripts must reach their last line.

THE MOST EXPENSIVE BUG IN THIS CODEBASE, measured in debugging rounds, is not a
wrong pixel or a bad transform. It is `flip.js` throwing at top level and
silently abandoning every line after the throw. The page still renders, the
markup is all there, and an arbitrary SUFFIX of the behaviour is missing — so it
presents as several unrelated features breaking at once and sends you looking at
whichever one you noticed first.

Four separate rounds in a single session, every one the same shape: a function
that runs during init (`setTool()` is the usual culprit) reaches a `let` declared
further down the file, hits its temporal dead zone, and throws "Cannot access X
before initialization". `let` and `const` do not hoist the way `function` does,
and no `typeof` guard can rescue them — only declaration order can.

So each script ends with one statement whose only job is to say it got there,
and this suite reads it. That is a more reliable detector than a page-error
listener: it also catches a throw that something swallowed, and it says WHICH
file died rather than reporting a symptom three screens away.

The suite also loads each surface twice — once empty, once restoring a draft —
because restore is a second load-time code path with its own ordering, and it is
the one that runs on a returning user rather than a fresh one.

The two surfaces differ in how a draft arrives and this suite pins that rather
than flattening it: Flip restores silently, because it persists pages, media and
background and has nothing to warn about; Pad offers a banner, because its
autosave holds strokes but NOT media bytes and a silent restore would present a
partial drawing as the whole one.
"""
import json
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


SURFACES = [
    ("Pad",  "/",     "pad"),
    ("Flip", "/flip", "flip"),
]

# A draft in each surface's own format, small but complete enough that the
# restore path actually runs rather than bailing on a missing field.
# Pad's own shape, from serializeAutosave() in editor_draft.js — version 1, a
# writerId, and `background` as an OBJECT rather than a string. A near-miss
# fixture restores nothing and the assertion below then blames the boot path for
# a bad test.
PAD_DRAFT = {
    "version": 1,
    "writerId": "verify-boot",
    "savedAt": "2026-01-01T00:00:00.000Z",
    "baseSnapshot": None,
    "strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0, "start": True},
                {"x": 90, "y": 90, "color": "#fff", "size": 6, "t": 50}],
    "strokeGroups": [2],
    "redoStrokes": None, "redoStrokeGroups": None,
    "background": {"color": "#0d0f14"},
    "photoMeta": None, "musicMeta": None,
}
FLIP_DRAFT = {
    "schemaVersion": 2, "version": 2, "playbackMode": "flip", "fps": 12,
    "canvasSize": {"cssWidth": 900, "cssHeight": 1200, "dpr": 1},
    "savedAt": "2026-01-01T00:00:00.000Z", "editIdx": 0,
    "frames": [{"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0,
                             "erase": False, "start": True},
                            {"x": 90, "y": 90, "color": "#fff", "size": 6, "t": 1,
                             "erase": False}],
                "strokeGroups": [2], "background": "#0d0f14"}],
}
KEYS = {"pad": "skribl_autosave_v1", "flip": "skribl_flip_autosave_v1"}
DRAFTS = {"pad": PAD_DRAFT, "flip": FLIP_DRAFT}

with sync_playwright() as p:
    browser = p.chromium.launch()

    for label, path, key in SURFACES:
        print(f"\nBOOT [{label}] — a clean load runs the whole file")
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        errs, console = [], []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(1200)
        boot = page.evaluate("() => (window.__skriblBoot || {})")
        check(f"{label}: the script reached its last line",
              boot.get(key) is True,
              "a top-level throw abandons every line after it — the page still "
              "renders and some suffix of the behaviour is just gone")
        check(f"{label}: no uncaught error during load", not errs, "; ".join(errs[:2]))
        check(f"{label}: no console error during load", not console, "; ".join(console[:2]))
        page.close()

        print(f"BOOT [{label}] — and so does a load that restores a draft")
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        errs, console = [], []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page.goto(BASE + path, wait_until="load")
        page.wait_for_timeout(400)
        page.evaluate("(a) => { for (const k of Object.keys(localStorage))"
                      " if (k.indexOf('skribl') === 0) localStorage.removeItem(k);"
                      " localStorage.setItem(a[0], a[1]); }",
                      [KEYS[key], json.dumps(DRAFTS[key])])
        page.reload(wait_until="load")
        page.wait_for_timeout(1400)
        boot = page.evaluate("() => (window.__skriblBoot || {})")
        check(f"{label}: the script reached its last line with a draft to restore",
              boot.get(key) is True,
              "restore is a second load-time path with its own ordering, and it "
              "is the one a returning user takes")
        check(f"{label}: no uncaught error while restoring", not errs, "; ".join(errs[:2]))

        # THE TWO SURFACES DIFFER HERE, deliberately, and pinning one shape on
        # both hides that. Flip restores its draft silently — it persists pages,
        # media and background, so there is nothing to warn about. Pad ASKS,
        # with a "Unsaved drawing found / Discard / Restore" banner, because its
        # autosave holds strokes but not media bytes and a silent restore would
        # quietly present a partial drawing as the whole one.
        if key == "pad":
            check("Pad: a draft is offered rather than applied",
                  page.evaluate("() => { const b = document.getElementById('restoreBanner');"
                                " return !!b && !b.hidden; }"),
                  "Pad's autosave holds strokes but not media bytes, so it asks")
            page.click("#restoreConfirm")
            page.wait_for_timeout(700)
        # NOT `typeof frames !== 'undefined'`. `window.frames` is the iframe
        # list and exists in every browser, so that test is always true — on
        # Flip a real top-level `let frames` shadows it and the expression
        # worked by luck, while on Pad it resolved to window.frames[0] and threw.
        expr = ("() => { try { return frames[0].strokes.length; }"
                " catch (e) { return -1; } }") if key == "flip" else (
               "() => { try { return strokes.length; } catch (e) { return -1; } }")
        strokes = page.evaluate(expr)
        check(f"{label}: the draft restores when taken",
              strokes == 2,
              f"{strokes} strokes — 0 means the draft was ignored, -1 means the "
              f"file died before the state even existed")
        check(f"{label}: still no uncaught error after restoring",
              not errs, "; ".join(errs[:2]))
        page.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
