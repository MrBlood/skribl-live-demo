"""The "How it works" help sheet, checked against the app it describes.

WHY THIS EXISTS. Three user-visible changes shipped in v142-v144 — Flip's
title/caption compose step, stylus pressure, and the export sheet's options —
and the help drawer described none of them. It still told Flip users that Post
gives them "a link", the sentence the Pad version had already outgrown.

Help text is the easiest thing in a project to leave behind, because nothing
breaks when it is wrong. This project has the matching precedent in code: the
editor's hardcoded version string drifted NINE releases before anyone noticed.

Two guards:

  1. Every accordion's "N tips" badge equals the number of items rendered
     inside it. Counted in a BROWSER, not in the source — the template carries
     both arms of every `{% if is_flip %}`, so a source count is wrong by
     construction and a guard that is wrong by construction is worse than none.
  2. Each shipped feature has a phrase in the help that could only be there if
     someone updated it.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — this suite needs a browser")
    summarise_and_exit()

COUNTS = """() => {
  const out = [];
  document.querySelectorAll('.accordion-header').forEach(h => {
    const badge = h.querySelector('.accordion-count');
    const title = h.querySelector('.accordion-title');
    if (!badge) return;
    let body = h.nextElementSibling;
    while (body && !body.classList.contains('accordion-body')) body = body.nextElementSibling;
    const inner = body ? body.querySelectorAll('.help-tip, .help-step').length : -1;
    out.push({ title: title ? title.textContent.trim() : '?',
               stated: badge.textContent.trim(), actual: inner });
  });
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()

    for surface, path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        print(f"\nHELP — {surface}: the badges match what is inside them")
        pg = b.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1400)
        check(f"{surface} loads with no JS errors", not errs, "; ".join(errs[:2]))

        rows = pg.evaluate(COUNTS)
        check(f"{surface}'s help sheet has accordions to check", len(rows) > 0,
              "found none — the selector is wrong, not the page")

        for row in rows:
            stated = "".join(c for c in row["stated"] if c.isdigit())
            stated = int(stated) if stated else -1
            check(f"{surface} · {row['title']}: badge says {stated}, "
                  f"contains {row['actual']}",
                  stated == row["actual"],
                  "the badge is derived from the DOM by lib/helpsearch.js — a "
                  "mismatch means the lib did not run, not that someone "
                  "mistyped a number")
        pg.close()

    print("\nHELP — the shipped features are actually described")
    pg = b.new_page()
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1400)
    # textContent, not innerText: the drawer ships closed with every accordion
    # collapsed, so innerText returns only what is on screen and every check
    # below would fail for a reason that has nothing to do with the help copy.
    text = pg.evaluate(
        "() => (document.getElementById('helpDrawer') || document.body)"
        ".textContent.toLowerCase()")

    check("Flip's help says Post asks for a title",
          "title" in text and "caption" in text,
          "Flip's Post step said only 'a link' while Pad's already said "
          "'title and caption' — the same asymmetry the feature fixed")
    check("the help describes stylus pressure",
          "pressure" in text and ("pencil" in text or "ipad" in text),
          "pressure ships on both editors and is documented nowhere")
    check("the help says a mouse is unaffected by pressure",
          "one width" in text or "mouse" in text,
          "without this a mouse user reads pressure as broken")
    check("the help describes the GIF background choice",
          "transparent" in text,
          "Solid/Transparent is a visible control with no explanation")
    check("the help states Size and Pages do not apply to PNG",
          "png" in text and ("current page" in text or "full size" in text),
          "the sheet says 'applies to video and GIF'; the help should agree")
    pg.close()

    # -----------------------------------------------------------------------
    print("\nHELP — search, on both surfaces")
    #
    # 46 entries across 7 sections is past the point where an accordion alone
    # is findable. These assert the behaviours that make search worth having,
    # not merely that a field exists: cross-section reach, a real empty state,
    # and highlighting that survives repeated keystrokes.
    for surface, path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        sp = b.new_page()
        serrs = []
        sp.on("pageerror", lambda e: serrs.append(str(e)))
        sp.goto(BASE + path, wait_until="load")
        sp.wait_for_timeout(1400)
        sp.evaluate("() => { const d = document.getElementById('helpDrawer');"
                    " if (d) { d.hidden = false; d.classList.add('open'); } }")
        sp.wait_for_timeout(250)

        check(f"{surface}: the shared search lib is published",
              sp.evaluate("() => !!window.SkriblHelpSearch"),
              "lib/helpsearch.js did not load — both editors fall back to a "
              "plain accordion")
        check(f"{surface}: the search field is present",
              sp.is_visible("#helpSearch"))

        base_count = sp.inner_text("#helpSearchCount")
        check(f"{surface}: the count states a total before any query",
              "entries" in base_count and "sections" in base_count,
              repr(base_count))

        # "loop" appears in Music, Frames and Export — one query reaching three
        # sections is the thing an accordion structurally cannot do.
        sp.fill("#helpSearch", "loop")
        sp.wait_for_timeout(250)
        open_sections = sp.evaluate(
            "() => [...document.querySelectorAll('#helpDrawer .accordion-header')]"
            ".filter(h => !h.hidden).length")
        check(f"{surface}: 'loop' reaches more than one section",
              open_sections > 1, f"{open_sections} section(s) matched")
        check(f"{surface}: matches are highlighted",
              sp.evaluate("() => document.querySelectorAll('#helpDrawer mark.help-hit').length") > 0)
        check(f"{surface}: the count switches to matches",
              " of " in sp.inner_text("#helpSearchCount"),
              repr(sp.inner_text("#helpSearchCount")))

        # Highlighting rewrites innerHTML. If the original is not cached, marks
        # nest and compound on every keystroke — the bug this guards.
        for q in ("l", "lo", "loo", "loop", "loo", "lo"):
            sp.fill("#helpSearch", q)
            sp.wait_for_timeout(80)
        nested = sp.evaluate(
            "() => document.querySelectorAll('#helpDrawer mark.help-hit mark').length")
        check(f"{surface}: repeated typing does not nest highlights",
              nested == 0, f"{nested} nested marks — the original HTML is not cached")

        sp.fill("#helpSearch", "zzzznothing")
        sp.wait_for_timeout(250)
        check(f"{surface}: a no-match query shows the empty state",
              sp.is_visible("#helpEmpty"))
        check(f"{surface}: no sections remain visible on no match",
              sp.evaluate("() => [...document.querySelectorAll("
                          "'#helpDrawer .accordion-header')].filter(h => !h.hidden).length") == 0)

        sp.fill("#helpSearch", "")
        sp.wait_for_timeout(250)
        check(f"{surface}: clearing restores every entry",
              sp.inner_text("#helpSearchCount") == base_count,
              f"{sp.inner_text('#helpSearchCount')!r} vs {base_count!r}")
        check(f"{surface}: clearing removes every highlight",
              sp.evaluate("() => document.querySelectorAll("
                          "'#helpDrawer mark.help-hit').length") == 0)
        check(f"{surface}: the empty state is hidden again",
              not sp.is_visible("#helpEmpty"))
        check(f"{surface}: no JS errors during the whole search flow",
              not serrs, "; ".join(serrs[:2]))
        sp.close()

    b.close()

summarise_and_exit()
