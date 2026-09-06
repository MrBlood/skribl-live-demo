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

  Added as the record became a credential store rather than a tray, each from
  an audit finding rather than from foresight:

  6. A write that did not happen is REPORTED, not assumed (v280).
  7. The 200-entry cap governs what is rendered and never evicts a key (v280).
  8. Delete and Copy key appear only where a key is actually held (v280).
  9. A key can be handed BACK: link-or-id plus key, then take it down or
     re-adopt it into this browser (v281).
 10. Clear list cannot discard keys until an export has succeeded (v281).
 11. A 404 from DELETE is UNKNOWN, so the entry and its key survive it (v281).
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

    # THE ✕ NOW ASKS FIRST WHEN THERE IS SOMETHING TO LOSE, and that is a v279
    # behaviour change this assertion had to be taught. An audit of v278 pointed
    # out that ✕ removed the local record while the Skribl stayed live — and
    # since v279 that record also holds the only key that can delete it, so
    # discarding it silently forfeits revocation. It confirms; a token-less
    # entry still goes without friction.
    #
    # Playwright dismisses dialogs by default, so an unhandled confirm reads as
    # "cancelled" and this section failed on the real, intended behaviour. The
    # handler is what makes the assertion measure the removal rather than the
    # dialog.
    _asked = []
    pg.on("dialog", lambda d: (_asked.append(d.message), d.accept()))

    _has_tok = pg.evaluate("() => !!(window.SkriblPosted.list()[0]||{}).tok")
    pg.click("#postedList .posted-del")
    pg.wait_for_timeout(400)
    if _has_tok:
        check("removing an entry that holds the delete key warns first",
              any("key" in m.lower() for m in _asked),
              f"{_asked} — throwing the key away without saying so is what the "
              "audit called out as making recovery worse")
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

    # ---------------------------------------------------------------- v280
    print("\nCUSTODY — the cap governs history and never authorisation")
    # THE FINDING, from an adversarial audit of v279. write() truncated with
    # `list.slice(0, LIMIT)` on every call, and v279 had just put the only copy
    # of an anonymous post's revocation key in these same records. Publishing
    # the 201st Skribl silently stranded the 1st -- still live on the server,
    # no longer withdrawable by anyone. The 202nd stranded the next. This is
    # the audit's own regression test: 200 key-bearing entries, add one more,
    # prove all 201 keys survive.
    LIMIT = pd.evaluate("() => window.SkriblPosted.LIMIT")
    check("the store still declares the cap this test is about", LIMIT == 200,
          f"LIMIT is {LIMIT}; this section assumes the audited value")

    pd.evaluate("""(n) => {
        localStorage.setItem('skribl_posted_v1', '[]');
        for (var i = 0; i < n; i++) {
          window.SkriblPosted.add({ id: 'tok' + i, title: 'k' + i,
                                    kind: 'pad', tok: 'secret-' + i });
        }
      }""", LIMIT)
    kept = pd.evaluate(READ)
    check(f"{LIMIT} key-bearing posts are all held", len(kept) == LIMIT,
          f"{len(kept)} of {LIMIT}")

    pd.evaluate("""() => window.SkriblPosted.add({ id: 'overflow', title: 'the 201st',
                     kind: 'pad', tok: 'secret-overflow' })""")
    after = pd.evaluate(READ)
    check("publishing past the cap does not evict a key",
          len(after) == LIMIT + 1, f"{len(after)} entries after the {LIMIT + 1}th "
          "post — the oldest key was dropped, which is the finding")
    keys = {e.get("tok") for e in after}
    missing = [f"secret-{i}" for i in range(LIMIT) if f"secret-{i}" not in keys]
    check("every one of the original keys is still recoverable",
          not missing and "secret-overflow" in keys,
          f"{len(missing)} lost, first {missing[:3]}")

    # ...AND THE CAP STILL DOES ITS JOB for entries that authorise nothing. A
    # fix that simply removed the truncation would pass everything above and
    # let the tray grow without limit, which is the bug the cap was added for.
    pd.evaluate("""(n) => {
        localStorage.setItem('skribl_posted_v1', '[]');
        for (var i = 0; i < n + 25; i++) {
          window.SkriblPosted.add({ id: 'plain' + i, title: 'p' + i, kind: 'pad' });
        }
      }""", LIMIT)
    plain = pd.evaluate(READ)
    check("entries with no key are still capped", len(plain) == LIMIT,
          f"{len(plain)} — removing the truncation outright is not the fix")

    print("\nCUSTODY — a write that did not happen is reported, not assumed")
    # THE OTHER HALF OF THE FINDING. write() has always returned a boolean and
    # add() has always discarded it, so a browser that could not store the key
    # produced a live post and a success message. These drive the three hostile
    # states the audit named: throws-on-set, quota, and no localStorage at all.
    HOSTILE = """(mode) => {
        const proto = Object.getPrototypeOf(window.localStorage);
        const real = proto.setItem;
        proto.setItem = function () {
          const e = new Error(mode === 'quota' ? 'quota' : 'nope');
          if (mode === 'quota') e.name = 'QuotaExceededError';
          throw e;
        };
        try {
          return window.SkriblPosted.add({ id: 'hostile', title: 'h',
                                           kind: 'pad', tok: 'secret-hostile' });
        } finally { proto.setItem = real; }
      }"""
    for mode in ("throws", "quota"):
        res = pd.evaluate(HOSTILE, mode)
        check(f"{mode}: add() reports the write as not durable",
              res.get("durable") is False, repr(res.get("durable")))
        check(f"{mode}: add() hands back the key it could not keep",
              res.get("key") == "secret-hostile",
              f"{res.get('key')!r} — with no key here the caller has nothing "
              "to show the user and the post is irrevocable in silence")

    ok = pd.evaluate("""() => { localStorage.setItem('skribl_posted_v1','[]');
        return window.SkriblPosted.add({ id: 'fine', title: 'f', kind: 'pad',
                                         tok: 'secret-fine' }); }""")
    check("a write that DID happen reports durable and withholds the key",
          ok.get("durable") is True and ok.get("key") is None,
          f"durable={ok.get('durable')!r} key={ok.get('key')!r} — handing the "
          "key back on the happy path would put the recovery panel in front of "
          "every successful post")

    check("canPersist() answers true on a working store",
          pd.evaluate("() => window.SkriblPosted.canPersist()") is True)
    check("canPersist() answers false when setItem throws", pd.evaluate("""() => {
            const proto = Object.getPrototypeOf(window.localStorage);
            const real = proto.setItem;
            proto.setItem = function () { throw new Error('nope'); };
            try { return window.SkriblPosted.canPersist(); }
            finally { proto.setItem = real; } }""") is False,
          "the pre-post warning never fires, so the user is told nothing until "
          "after the irreversible part")

    print("\nCUSTODY — the tray offers the key, and offers it only where there is one")
    # Nothing tested these two buttons before v280, which is its own finding:
    # the tray's Delete is the affordance that actually invokes revocation, and
    # Copy key is the one that lets the key outlive this browser. Both are
    # conditional on holding a key, and a condition nothing checks is a
    # condition that quietly inverts.
    pd.evaluate("""() => {
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'withkey', title: 'has one',
                                  kind: 'pad', tok: 'secret-visible' });
        window.SkriblPosted.add({ id: 'nokey', title: 'has none', kind: 'pad' });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }""")
    pd.wait_for_timeout(300)

    def _row(rid, sel):
        return pd.evaluate(
            "([rid, sel]) => { const r = document.querySelector("
            "'.posted-row[data-id=\"' + rid + '\"]'); "
            "return !!(r && r.querySelector(sel)); }", [rid, sel])

    check("a post whose key this browser holds offers Copy key",
          _row("withkey", ".posted-key"),
          "the only affordance that survives cleared site data is missing")
    check("...and offers Delete", _row("withkey", ".posted-delete"))
    check("a post with no key offers NEITHER",
          not _row("nokey", ".posted-key") and not _row("nokey", ".posted-delete"),
          "offering an action that cannot be authorised is worse than "
          "offering nothing — it fails at the moment somebody needs it")

    # And the button copies the KEY, not the link. Reading the clipboard needs
    # a permission Chromium will not grant headless, so this asserts what the
    # handler was handed rather than what the OS holds.
    copied = pd.evaluate("""() => {
        let seen = null;
        const real = navigator.clipboard && navigator.clipboard.writeText;
        if (real) navigator.clipboard.writeText = t => { seen = t; return Promise.resolve(); };
        document.querySelector('.posted-row[data-id="withkey"] .posted-key').click();
        if (real) navigator.clipboard.writeText = real;
        return seen;
      }""")
    check("Copy key copies the key and not the share link",
          copied == "secret-visible",
          f"{copied!r} — a button that copies the URL under a key's label is "
          "how somebody thinks they have saved a credential and has not")

    print("\nRECOVERY — the journey the key exists for, end to end")
    # THE INVARIANT, in the words of the audit that found it missing:
    #
    #   possess the id and the key -> revoke through the product, whatever
    #   this browser happens to remember.
    #
    # v280 built the export half only. It showed the key, the tray copied it,
    # the panel said "keep it somewhere you will find it" — and nothing would
    # accept one back. A user who did exactly as told and then lost their
    # browser state held the credential and could not spend it. This section
    # is that round trip, run as ONE journey rather than as two features that
    # each pass alone: post, keep the key, DESTROY the local record, and come
    # back with nothing but the id and the key.
    made = pd.evaluate("""async (base) => {
        const r = await fetch(base, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({title: 'recover me', payload:
            {v:1, canvas:{w:100,h:100}, strokes:[]}})});
        const d = await r.json();
        return {id: d.id, tok: d.deleteToken || null};
      }""", API)
    check("an anonymous post still returns a key to keep",
          bool(made.get("id")) and bool(made.get("tok")),
          f"{made!r} — with no key there is nothing to recover with")

    # THE LOSS, made real rather than simulated: the store is emptied exactly
    # as clearing site data would leave it.
    pd.evaluate("() => localStorage.removeItem('skribl_posted_v1')")
    gone = pd.evaluate("() => window.SkriblPosted.list().length")
    check("this browser now remembers nothing about it", gone == 0, str(gone))

    # THE RETURN. Only the two things a person could still have.
    pd.evaluate("() => window.SkriblRecoveryKey.openRecover()")
    pd.wait_for_timeout(300)
    check("the product offers a way back in",
          pd.evaluate("() => !document.getElementById('recoverOverlay').hidden"),
          "no recovery surface — this is the v280 blocker")

    # A share LINK, not a bare id, because that is what somebody actually has.
    pd.fill("#recoverId", f"http://127.0.0.1:5001/s/{made['id']}")
    pd.fill("#recoverKey", made["tok"])
    pd.click("#recoverDelete")
    pd.wait_for_timeout(1200)
    said = pd.evaluate("() => document.getElementById('recoverSaid').textContent")
    check("it says the Skribl was taken down", "Taken down" in said, repr(said))

    # AND THE SERVER AGREES, which is the only opinion that counts here.
    code = pd.evaluate("""async (u) => {
        const r = await fetch(u); return r.status; }""",
        f"{API}/{made['id']}")
    check("the post is really gone from the server", code == 404, str(code))

    print("\nRECOVERY — a key that does not fit is not a deletion")
    # THE OTHER HALF OF THE SAME RULE. The server answers 404 both for "no such
    # post" and "not yours" so the API cannot be walked. v280's client read
    # that as success and dropped the local record — destroying the credential
    # for a post that was still live. Ambiguity on the server must stay
    # ambiguity in the UI.
    kept = pd.evaluate("""async (base) => {
        const r = await fetch(base, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({title: 'wrong key', payload:
            {v:1, canvas:{w:100,h:100}, strokes:[]}})});
        const d = await r.json();
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({id: d.id, url: d.url, kind: 'pad',
                                 title: 'wrong key', tok: 'not-the-right-key'});
        if (window._skriblPostedUI) window._skriblPostedUI.render();
        return d.id;
      }""", API)
    # Put the surfaces back where a user would have them: the recovery
    # dialog closed, the drawer open. The first draft clicked the row's
    # Delete with the recovery overlay still covering it and timed out on
    # an element that was present and NOT VISIBLE — a test-setup failure
    # that reads exactly like a product one.
    # ACCEPT THE CONFIRM, or this section measures nothing. The row's
    # Delete asks `confirm()` first, and Playwright auto-DISMISSES dialogs,
    # so the first version of this test clicked Delete, had the confirm
    # silently refused, never reached destroy(), and then asserted that the
    # entry was still present — which it was, for the wrong reason. It
    # passed with the 404-as-success bug fully restored. Caught by mutating
    # the code it was written for; nothing else would have shown it.
    pd.on("dialog", lambda d: d.accept())
    pd.evaluate("() => window.SkriblRecoveryKey.closeRecover()")
    pd.evaluate("() => window._skriblPostedUI && window._skriblPostedUI.open()")
    pd.wait_for_timeout(500)
    pd.click(f'.posted-row[data-id="{kept}"] .posted-delete')
    pd.wait_for_timeout(1500)
    still = pd.evaluate("() => window.SkriblPosted.list()")
    check("a wrong key does NOT remove the local entry",
          len(still) == 1 and still[0]["id"] == kept,
          f"{len(still)} entries — v280 treated the 404 as success and threw "
          "away the only key for a post that is still up")
    check("...and the key it holds is still there",
          still and still[0].get("tok") == "not-the-right-key",
          "the credential went with the entry")
    live = pd.evaluate("""async (u) => (await fetch(u)).status""", f"{API}/{kept}")
    check("...because the post really is still live", live == 200, str(live))

    print("\nRECOVERY — Clear list cannot quietly take the keys with it")
    # The single-row X has warned about credential loss since v279. The button
    # that does it to every row at once did not, which is the weaker contract
    # winning on the more destructive path.
    pd.evaluate("""() => {
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({id:'k1', title:'one', kind:'pad', tok:'key-1'});
        window.SkriblPosted.add({id:'k2', title:'two', kind:'pad', tok:'key-2'});
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }""")
    pd.wait_for_timeout(250)
    pd.click("#postedClear")
    pd.wait_for_timeout(400)
    check("clearing a list holding keys asks first",
          pd.evaluate("() => { const d = document.getElementById('clearKeysOverlay');"
                      " return !!d && !d.hidden; }"),
          "two taps and every key was gone")
    check("...and it says how many are at stake",
          "2 Skribls" in pd.evaluate(
              "() => document.getElementById('clearKeysWhy').textContent"),
          pd.evaluate("() => document.getElementById('clearKeysWhy').textContent"))
    check("...and will not clear until the keys have been exported",
          pd.evaluate("() => document.getElementById('clearKeysGo').disabled") is True,
          "'Clear anyway' was live before anything had been saved")
    check("THE KEYS ARE STILL THERE while it asks",
          pd.evaluate("() => window.SkriblPosted.list().length") == 2)

    # And the export unlocks it — with the keys in what it copied.
    copied = pd.evaluate("""async () => {
        let seen = null;
        const real = navigator.clipboard && navigator.clipboard.writeText;
        if (real) navigator.clipboard.writeText = t => { seen = t; return Promise.resolve(); };
        document.getElementById('clearKeysExport').click();
        await new Promise(r => setTimeout(r, 300));
        if (real) navigator.clipboard.writeText = real;
        return seen;
      }""")
    check("exporting hands over every key", copied and "key-1" in copied
          and "key-2" in copied, repr(copied))
    check("...and only then is clearing allowed",
          pd.evaluate("() => document.getElementById('clearKeysGo').disabled") is False,
          "export succeeded and the button stayed locked")

    print("\nRECOVERY — a pasted link is read the way people paste it")
    for raw, want in (("abc123", "abc123"),
                      ("http://x/s/abc123", "abc123"),
                      ("http://x/s/abc123?utm=1", "abc123"),
                      ("http://x/s/abc123#t=2", "abc123"),
                      ("  http://x/s/abc123/  ", "abc123"),
                      ("not a link at all", ""),
                      ("", "")):
        got = pd.evaluate("(v) => window.SkriblRecoveryKey.parseId(v)", raw)
        check(f"parseId({raw!r}) -> {want!r}", got == want, repr(got))

    pd.close()
    b.close()

print("\nTRAY ICONS — a Flip is marked with the icon that means Flip")
# The tray used U+25A6 (a hatched square) for a Flip and U+270E for a Pad
# replay. The square matched nothing in the app — a Flip is identified by the
# open book that opens it from Pad's header — and the pencil leaned the
# opposite way to the Pen tool, so a Pad Skribl carried a pencil facing away
# from the one the user drew with.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pg = _b.new_page()
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
    _pg.evaluate("""() => {
      window.SkriblPosted.add({id:'ic1', url:'/s/ic1', kind:'flip', pages:9, title:'A flip'});
      window.SkriblPosted.add({id:'ic2', url:'/s/ic2', kind:'pad', pages:1, title:'A pad'});
      const d = document.getElementById('postedDrawer');
      d.hidden = false; d.classList.add('open');
      if (window._skriblPostedUI) window._skriblPostedUI.render();
    }""")
    _pg.wait_for_timeout(400)

    check("no legacy glyph characters remain in the tray",
          _pg.evaluate("() => !document.getElementById('postedList')"
                       ".textContent.match(/[\u25A6\u270E]/)"),
          "a font glyph renders at whatever weight the system font chooses")

    for _kind in ("flip", "pad"):
        check(f"a {_kind} entry uses an inline SVG icon",
              _pg.evaluate(f"() => !!document.querySelector("
                           f"'.posted-thumb-{_kind} svg')"),
              "still a text glyph")

    # The Flip icon must be the SAME path the header uses to open Flip. Compared
    # by geometry, not by eye: a different book would pass a "has an svg" check.
    _tray = _pg.evaluate("() => document.querySelector("
                         "'.posted-thumb-flip svg path').getAttribute('d')")
    _pd = _b.new_page()
    _pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    _pd.wait_for_timeout(1200)
    _hdr = _pd.evaluate("() => { const el = document.querySelector('#flipBtn svg path');"
                        " return el ? el.getAttribute('d') : null; }")
    check("the tray's Flip icon is the same book that opens Flip",
          _tray is not None and _tray == _hdr,
          f"tray {_tray!r} vs header {_hdr!r}")
    _pd.close()

    check("the tray icons render at a visible size",
          _pg.evaluate("() => [...document.querySelectorAll('.posted-thumb svg')]"
                       ".every(s => s.getBoundingClientRect().width > 10)"),
          "present but collapsed")
    _b.close()

summarise_and_exit()
