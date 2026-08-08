"""Your Skribls — the local record of what this browser has posted.

THE GAP. There are no accounts, so a share link is the only handle on a post,
and nothing told anyone to keep it. Post, close the tab, and the Skribl is
unreachable forever: the id exists on the server but the person who made it has
no way to name it. That is the first thing a tester loses, and the least
excusable, because the client already knew every id it posted.

What this suite pins, in order of how badly each would fail a user:

  1. A real post is recorded, on BOTH surfaces, with its own title.
  2. A LOCAL-ONLY save is NOT recorded. Pad falls back to a local save when the
     server is unreachable; that Skribl is not shareable, so listing it under
     links you can send would be a lie.
  3. No payload is stored. Payloads run to hundreds of kilobytes and
     localStorage is a ~5MB budget shared with crash recovery, which matters
     more than this list does.
  4. Removing an entry removes the ENTRY, not the Skribl.
  5. The empty state invites rather than apologises — it is the first thing a
     new tester sees.
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"

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

READ = "() => JSON.parse(localStorage.getItem('skribl_posted_v1') || '[]')"

with sync_playwright() as p:
    b = p.chromium.launch()

    # -----------------------------------------------------------------------
    print("YOUR SKRIBLS — the empty state a new tester sees")
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1400)
    check("Flip loads with no JS errors", not errs, "; ".join(errs[:2]))
    check("the store is published", pg.evaluate("() => !!window.SkriblPosted"))
    check("the tray UI is published", pg.evaluate("() => !!window.SkriblPostedUI"))

    pg.evaluate("() => window._skriblPostedUI.open()")
    pg.wait_for_timeout(300)
    empty = pg.inner_text("#postedList")
    check("the empty state invites rather than apologises",
          "nothing posted yet" in empty.lower() and "post" in empty.lower(),
          repr(empty[:80]))
    check("the footer says this is browser-only, not an account",
          "browser" in pg.inner_text("#postedDrawer").lower(),
          "someone who reads this as an account will clear site data and lose it")
    check("no clear button while the list is empty",
          not pg.is_visible("#postedClear"))
    pg.evaluate("() => window._skriblPostedUI.close()")

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — a real Flip post is recorded")
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(250)

    TITLE = "Walk cycle, take 2"
    pg.click("#postBtn")
    pg.wait_for_timeout(400)
    pg.fill("#flipShareTitle", TITLE)
    pg.click("#flipShareSubmit")
    pg.wait_for_selector("#flipShareUrl", state="visible", timeout=20000)
    pg.wait_for_timeout(700)

    saved = pg.evaluate(READ)
    check("the post was recorded", len(saved) == 1, str(len(saved)))
    entry = saved[0] if saved else {}
    check("with the title the user typed", entry.get("title") == TITLE,
          repr(entry.get("title")))
    check("with its id", bool(entry.get("id")), str(entry.get("id")))
    check("marked as a Flip", entry.get("kind") == "flip", str(entry.get("kind")))
    check("with its page count", entry.get("pages", 0) >= 1, str(entry.get("pages")))

    # The whole reason it is safe to keep this list.
    blob = json.dumps(entry)
    check("no payload, strokes or media were stored",
          "strokes" not in blob and "data:" not in blob and len(blob) < 400,
          f"{len(blob)} bytes — localStorage is shared with crash recovery")

    pg.evaluate("() => window._skriblPostedUI.open()")
    pg.wait_for_timeout(300)
    check("the tray lists it", TITLE in pg.inner_text("#postedList"),
          pg.inner_text("#postedList")[:80])
    check("the count reads as one Skribl",
          "1 skribl" in pg.inner_text("#postedCount").lower(),
          pg.inner_text("#postedCount"))
    href = pg.get_attribute("#postedList a", "href")
    check("the row links to the player", "/s/" in (href or ""), str(href))

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — removing an entry does not delete the Skribl")
    pid = entry.get("id")
    pg.click("#postedList .posted-del")
    pg.wait_for_timeout(300)
    check("the entry is gone from the list", pg.evaluate(READ) == [])
    with urllib.request.urlopen(f"{API}/{pid}", timeout=15) as r:
        still = json.loads(r.read())
    check("but the Skribl is still on the server",
          still.get("id") == pid,
          "removing a row must not destroy the post")
    pg.close()

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — Pad records its own posts, from the same store")
    pd = b.new_page()
    perrs = []
    pd.on("pageerror", lambda e: perrs.append(str(e)))
    pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    pd.wait_for_timeout(1500)
    check("Pad loads with no JS errors", not perrs, "; ".join(perrs[:2]))
    check("Pad reads the SAME storage key",
          pd.evaluate("() => window.SkriblPosted.KEY") == "skribl_posted_v1")

    pbox = pd.locator("#canvas").bounding_box()
    pd.mouse.move(pbox["x"] + 60, pbox["y"] + 60)
    pd.mouse.down()
    pd.mouse.move(pbox["x"] + 160, pbox["y"] + 130, steps=8)
    pd.mouse.up()
    pd.wait_for_timeout(400)

    # Pad auto-arms recording on the first stroke and hides Post until the take
    # is finished. Flip has no such state, which is why this is not symmetrical
    # with the Flip half above.
    pd.click("#recordBtn")
    pd.wait_for_timeout(600)
    check("Post appears once the take is stopped",
          pd.is_visible("#postBtn"),
          "still hidden — the recording did not finish")

    PAD_TITLE = "Signature"
    pd.click("#postBtn")
    pd.wait_for_timeout(500)
    pd.fill("#postTitleInput", PAD_TITLE)
    pd.click("#postSubmitBtn")
    pd.wait_for_timeout(2500)

    pad_saved = pd.evaluate(READ)
    check("Pad recorded its post", len(pad_saved) == 1, str(pad_saved))
    if pad_saved:
        check("marked as a Pad Skribl", pad_saved[0].get("kind") == "pad",
              str(pad_saved[0].get("kind")))
        check("with the title the user typed",
              pad_saved[0].get("title") == PAD_TITLE,
              repr(pad_saved[0].get("title")))

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — a local-only save is NOT listed as shareable")
    #
    # Pad falls back to a local save when the server is unreachable. That
    # Skribl has no link, so listing it among links you can send would be a
    # lie — and the fallback path is exactly where a tester on a bad
    # connection ends up.
    pd.evaluate("() => localStorage.setItem('skribl_posted_v1', '[]')")
    before = len(pd.evaluate(READ))
    pd.evaluate("""() => {
      if (window.SkriblPosted) window.SkriblPosted.add({ id: '', kind: 'pad' });
    }""")
    check("an entry with no id is refused by the store",
          len(pd.evaluate(READ)) == before,
          "a local-only save has no id and must not appear")

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — the store survives a hostile localStorage")
    pd.evaluate("() => localStorage.setItem('skribl_posted_v1', 'not json{')")
    check("corrupt stored data reads as an empty list, not a crash",
          pd.evaluate("() => window.SkriblPosted.list()") == [])
    pd.evaluate("() => localStorage.setItem('skribl_posted_v1', JSON.stringify({a:1}))")
    check("a non-array reads as an empty list",
          pd.evaluate("() => window.SkriblPosted.list()") == [])
    check("still no JS errors after both", not perrs, "; ".join(perrs[:2]))

    # De-duplication: reposting the same Skribl moves it up, not in twice.
    pd.evaluate("() => { localStorage.setItem('skribl_posted_v1','[]');"
                " window.SkriblPosted.add({id:'aaa', title:'first', kind:'pad'});"
                " window.SkriblPosted.add({id:'bbb', title:'second', kind:'pad'});"
                " window.SkriblPosted.add({id:'aaa', title:'first again', kind:'pad'}); }")
    dedup = pd.evaluate(READ)
    check("re-posting the same id updates in place rather than duplicating",
          len(dedup) == 2, str(len(dedup)))
    check("and moves it to the top", dedup and dedup[0]["id"] == "aaa",
          str([e["id"] for e in dedup]))

    pd.close()
    b.close()

summarise_and_exit()
