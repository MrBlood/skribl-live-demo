#!/usr/bin/env python3
"""One name for each thing (the owner's yeses, Q1, Q2 and Q5, after v326).

  * The button that makes a .skribl file had three names: the ⋯ menu said
    Save as a file, the name box and the Post sheet said Save a backup, and
    the note after it said Draft saved. It is Save as a file everywhere now,
    then "Saved as a file", and "Opened your file" when one opens. The owner's
    rule: buttons named by what they make. (A draft opened from Your drafts
    says its own name, "Opened" and its title, as it did.)
  * The key that can take a post down was the delete key on the Post sheet
    (the owner's K1) and a recovery key in the Library. One key, one name:
    the delete key.
  * The Library's subtitle promised "the full playback controls a post keeps
    out of the way", which a post has not done since v322. It says what the
    page is for now.

Each row is red on the words before.
"""
import json
import os
import pathlib
import re
import sys
import tempfile

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the names are one.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "skribl" / "static"
TPL = ROOT / "skribl" / "templates" / "skribl"
results = []
check = make_check(results, with_detail=True)
EDITORS = (("Pad", "/", "#menuBtn", "#saveDraftItem", "#toast"),
           ("Flip", "/flip", "#moreBtn", "#miSave", "#flipChip"))
SAY = "(sel) => (document.querySelector(sel) || {}).textContent || ''"

print("\nNAMES — no second name is left where a person reads it")
# The mechanism, not the sentence around it: words inside a string literal in
# the editors' and the Library's scripts, and text in the templates outside
# their {# #} notes. A comment quoting the old name is history, not a label.
_STALE = re.compile(r"Save a backup|recovery key|Draft saved", re.I)
_found = []
for f in sorted(list(STATIC.glob("*.js")) + list((STATIC / "lib").glob("*.js"))):
    code = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$|(?<=[;,{}()])\s*//[^'\"\n]*$", "", code)
    for m in re.finditer(r"""(['"`])((?:\\.|(?!\1).)*?)\1""", code):
        if _STALE.search(m.group(2)):
            _found.append(f"{f.name}: {m.group(0)[:60]}")
for f in sorted(TPL.glob("*.html")):
    text = re.sub(r"\{#.*?#\}", "", f.read_text(encoding="utf-8"), flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for m in _STALE.finditer(text):
        _found.append(f"{f.name}: …{text[max(0, m.start() - 20):m.end() + 10]!r}")
check("no script string or template text still says Save a backup, recovery key or Draft saved",
      not _found, "; ".join(_found[:6]) or "none")

with sync_playwright() as p:
    b = p.chromium.launch()

    print("\nNAMES — Save as a file, on both editors")
    saved = {}
    for name, path, menu, item, said in EDITORS:
        ctx = b.new_context(viewport={"width": 1100, "height": 800}, accept_downloads=True)
        pg = ctx.new_page()
        browsing.goto(pg, BASE, path)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        pg.click(menu); pg.wait_for_timeout(250)
        pg.click("#openCloudDraftItem"); pg.wait_for_timeout(600)       # Save as a file lives in Your drafts
        menu_word = pg.evaluate("(s) => document.querySelector(s + ' .menu-item-text').firstChild.textContent.trim()", item)
        pg.click(item); pg.wait_for_timeout(350)
        box_word = pg.evaluate("() => document.getElementById('nameDone').textContent.trim()")
        check(f"{name}: the ⋯ menu's Save as a file opens the name box, and its button says the same",
              menu_word == "Save as a file" and box_word == "Save as a file", f"menu {menu_word!r}, the name box's button {box_word!r}")
        with pg.expect_download() as dl:
            pg.click("#nameDone")
        pg.wait_for_timeout(250)
        note = pg.evaluate(SAY, said).strip()
        check(f"{name}: and when the file is made, the note says Saved as a file", note == "Saved as a file", repr(note))
        # Kept past the context: closing it deletes what it downloaded.
        saved[name] = os.path.join(tempfile.mkdtemp(), f"{name}.skribl")
        dl.value.save_as(saved[name])
        ctx.close()

    print("\nNAMES — Opened your file, on both editors")
    for name, path, menu, item, said in EDITORS:
        pg = b.new_page(viewport={"width": 1100, "height": 800})
        browsing.goto(pg, BASE, path)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        pg.set_input_files("#draftInput", saved[name]); pg.wait_for_timeout(900)
        note = pg.evaluate(SAY, said).strip()
        check(f"{name}: opening a .skribl file says Opened your file", note == "Opened your file", repr(note))
        pg.close()

    print("\nNAMES — the delete key, in the Library")
    pg = b.new_page(viewport={"width": 1100, "height": 800})
    browsing.goto(pg, BASE, "/library")
    use = pg.evaluate("() => { const b = document.querySelector('#postedRecover .pf-some'); return b ? b.textContent.trim() : null; }")
    pg.evaluate("() => SkriblRecoveryKey.openRecover()"); pg.wait_for_timeout(250)
    rec = pg.evaluate("() => ({ title: document.getElementById('recoverTitle').textContent.trim(),"
                      " label: document.querySelector('label[for=recoverKey]').textContent.trim() })")
    pg.evaluate("() => { SkriblRecoveryKey.closeRecover(); SkriblRecoveryKey.present({ key: 'k-123', url: '/s/abc' }); }")
    pg.wait_for_timeout(250)
    shown = pg.evaluate("() => document.getElementById('reckeyTitle').textContent.trim()")
    pg.evaluate("() => { SkriblRecoveryKey.close(); SkriblRecoveryKey.confirmClear([{ id: 'a' }, { id: 'b' }], () => {}); }")
    pg.wait_for_timeout(250)
    why = pg.evaluate("() => (document.getElementById('clearKeysWhy') || {}).textContent || ''").strip()
    words = [use or "", rec["title"], rec["label"], shown, why]
    check("the Library calls the key the delete key, as the Post sheet does: the button, the way in, the label, "
          "the key shown after a post, and the guard before a clear",
          use == "Use a delete key" and rec["title"] == "Use a delete key" and rec["label"] == "Delete key"
          and shown == "Save your delete key" and "delete keys stored here" in why
          and not any("recovery" in w.lower() for w in words), str(words))
    bio = pg.evaluate("() => document.getElementById('whoBio').textContent.replace(/\\s+/g, ' ').trim()")
    check("the Library's subtitle says what the page is for",
          bio == "Everything you have posted, newest first, to watch again, share or take down.", repr(bio))
    pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
