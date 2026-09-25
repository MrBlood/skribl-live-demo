"""Your Skribls — the local record of what this browser has posted.

THE GAP. There are no accounts, so a share link is the only handle on a post,
and nothing told anyone to keep it. Post, close the tab, and the Skribl is
unreachable forever: the id exists on the server but the person who made it has
no way to name it. That is the first thing a tester loses, and the least
excusable, because the client already knew every id it posted.

What this suite pins, in order of how badly each would fail a user:

  1. A real post is recorded, on BOTH surfaces, with its own title.
  2. A LOCAL-ONLY save IS recorded, flagged, and drawn as "on this device" with
     nothing to send. Until the acquisition audit of v302 (SK-AUD-010) this
     said the opposite — a local save has no link, so listing it would be a
     lie — and the lie ran the other way: lib/posted.js's orphan sweep deletes
     any unindexed 'skribl_post_*' blob the next time the store is full, so an
     unlisted local save was bytes the "saved on this device" message could
     not vouch for. Listed, it survives reclaim; its × arms before it deletes.
  3. No payload is stored. Payloads run to hundreds of kilobytes and
     localStorage is a ~5MB budget shared with crash recovery, which matters
     more than this list does.
  4. Removing an entry removes the ENTRY, not the Skribl.
  5. The empty state invites rather than apologises — it is the first thing a
     new tester sees.

  Added as the record became a credential store rather than a tray, each from
  an audit finding rather than from foresight:

  6. A write that did not happen is REPORTED, not assumed (v280).
  7. The 200-entry cap bounds what is KEPT — an entry past it with no key is
     dropped from storage, not hidden — and never evicts a key (v280).
  8. Delete and Copy key appear only where a key is actually held (v280).
  9. A key can be handed BACK: link-or-id plus key, then take it down or
     re-adopt it into this browser (v281).
 10. Clear list cannot discard keys until an export has succeeded (v281).
 11. A 404 from DELETE is UNKNOWN, so the entry and its key survive it (v281).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"

results = []


check = make_check(results, detail_on_pass=False)


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


def delete_with(pid, tok):
    """DELETE /api/skribls/<pid> with the revocation key; the status code."""
    req = urllib.request.Request(f"{API}/{pid}", method="DELETE",
                                 data=json.dumps({"deleteToken": tok}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

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
    # YOUR SKRIBLS IS THE PROFILE PAGE since v304: the list, its actions and
    # its custody rules render at /library (lib/postedui.js), and the editors'
    # menu row is a link there. Same page object, so the same localStorage.
    pg.goto(f"{BASE}/library", wait_until="load")
    pg.wait_for_timeout(900)
    check("the list UI is published on the profile", pg.evaluate("() => !!window.SkriblPostedUI"))
    # THE PAGE OWNS THE EMPTY STATE on the profile (v304 proofread): the list
    # renders nothing into #postedList, and #libEmpty under it is the one
    # invitation. verify_library pins that there is exactly one.
    empty = pg.inner_text("#libEmpty")
    check("the empty state invites rather than apologises",
          "nothing here yet" in empty.lower() and "post a skribl" in empty.lower()
          and pg.inner_text("#postedList").strip() == "",
          repr(empty[:80]))
    check("the footer says this is browser-only, not an account",
          "browser" in pg.inner_text("#postedPanel").lower(),
          "someone who reads this as an account will clear site data and lose it")
    check("no clear button while the list is empty",
          not pg.is_visible("#postedClear"))
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1200)
    check("Flip's menu row is a link to the profile",
          (pg.get_attribute("#miPosted", "href") or "").endswith("/library"),
          str(pg.get_attribute("#miPosted", "href")))

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

    pg.goto(f"{BASE}/library", wait_until="load")
    pg.wait_for_timeout(900)
    check("the profile lists it", TITLE in pg.inner_text("#postedList"),
          pg.inner_text("#postedList")[:80])
    check("the count reads as one Skribl",
          "1 skribl" in pg.inner_text("#postedCount").lower(),
          pg.inner_text("#postedCount"))
    href = pg.get_attribute("#postedList a", "href")
    check("the row links to the player", "/s/" in (href or ""), str(href))

    # ---- COPY SAYS WHAT HAPPENED (PRESEAL-002) -----------------------------
    #
    # The row's Copy link ran its success handler after
    # `try { document.execCommand('copy') }`, which does NOT throw when it
    # merely returns false -- so a refused copy still read "Copied". The
    # profile stage's button had the same shape on its clipboard path. One
    # helper answers whether the text arrived now (lib/postedui.js copyText),
    # and both callers report it.
    #
    # DRIVEN ON THIS PAGE, because the rows live in THIS browser's storage: a
    # fresh page is a fresh context and an empty list, which is what the first
    # cut of this pin measured -- it reported "no row to drive" rather than
    # the behaviour, and said so instead of passing.
    _orig_clip = pg.evaluate("""() => {
        window.__origExec = document.execCommand;
        window.__origClip = Object.getOwnPropertyDescriptor(navigator, 'clipboard') ? 1 : 0;
        Object.defineProperty(navigator, 'clipboard', {
          value: { writeText: function () { return Promise.reject(new Error('denied')); } },
          configurable: true });
        document.execCommand = function () { return false; };
        return !!document.querySelector('#postedList .posted-copy'); }""")
    check("there is a row with Copy link to drive", bool(_orig_clip))
    if _orig_clip:
        pg.click("#postedList .posted-copy")
        pg.wait_for_timeout(700)
        _lbl = pg.evaluate("""() => {
            const b = document.querySelector('#postedList .posted-copy');
            return { label: b ? b.textContent : null,
                     done: b ? b.classList.contains('done') : null,
                     live: (document.getElementById('postedStatus') || {}).textContent || '' }; }""")
        check("a copy that failed does not report itself as done",
              _lbl["label"] != "Copied" and not _lbl["done"], str(_lbl))
        check("...and the row says so where a screen reader hears it",
              "couldn't copy" in _lbl["live"].lower(), str(_lbl))
    # Put the page back, so nothing after this inherits a refusing clipboard.
    pg.evaluate("""() => { document.execCommand = window.__origExec;
        delete navigator.clipboard; }""")

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — a posted row cannot be forgotten, and wears one glyph per act")
    pid = entry.get("id")

    # WHAT THIS SECTION USED TO PIN, and why the pin moved. A posted row
    # carried a ✕ that removed the local ENTRY while the Skribl stayed live —
    # and, since v279, threw away the only key that could delete it. Four
    # releases were spent making that control safe: an arming tap (v279), a
    # 34px target (v293), an undo shelf (v291), a grid column of its own.
    # v311 asked the other question instead, and the owner's answer was to
    # take it out: a row's destructive control is Delete, and there is one.
    #
    # SO THE ASSERTION INVERTS. "The first tap arms" could only ever pass
    # while the ✕ existed; what guards the ground now is its ABSENCE, which
    # is the shape CLAUDE.md asks for — a check that goes red when the thing
    # achieved is LOST, not one that goes red when the work succeeds.
    _shape = pg.evaluate("""() => {
        const rows = [...document.querySelectorAll('#postedList .posted-row')];
        return rows.map(r => ({
          id: r.getAttribute('data-id'),
          local: r.classList.contains('posted-row-local'),
          dels: r.querySelectorAll('.posted-del').length,
          deletes: r.querySelectorAll('.posted-delete').length })); }""")
    _posted = [r for r in _shape if not r["local"]]
    check("a posted row offers no ✕ to forget it with",
          bool(_posted) and all(r["dels"] == 0 for r in _posted),
          f"{_shape} — the remove-from-list ✕ came back")
    check("...and Delete is still the one destructive control it does offer",
          bool(_posted) and all(r["deletes"] == 1 for r in _posted),
          f"{_shape} — a keyed row with no Delete has nothing to take it down "
          f"with, which is the opposite failure")
    # THE WAY OUT IS NOT GONE, IT IS COARSER, and that is the cost of the
    # trade rather than an oversight: a row this browser holds no key for can
    # now only leave the list with every other row. Clear list has to be
    # there, and has to be reachable, or the trade is a dead end.
    check("...and Clear list is still there to empty the list with",
          pg.is_visible("#postedClear"),
          "the only remaining way to drop a row is gone too")

    # ONE GLYPH PER ACT, WHICH THIS ROW DID NOT MANAGE UNTIL v311. The
    # visibility toggle borrowed the chain from Copy link for its OFF state,
    # so a link-only row drew the same picture twice — once meaning "copy the
    # link", once meaning "only the link reaches this" — and on the phone
    # these icons were drawn for, neither tooltip is reachable to tell them
    # apart. Keyed by the SVG's own contents, not by a class name: two
    # buttons could always be told apart by their classes, which is exactly
    # why a duplicated PICTURE went unnoticed for seven releases.
    pg.evaluate("""() => {
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'glyphpub', title: 'In the gallery', kind: 'pad',
                                  pages: 1, tok: 'k', visibility: 'public' });
        window.SkriblPosted.add({ id: 'glyphoff', title: 'Link only', kind: 'pad',
                                  pages: 1, tok: 'k', visibility: 'unlisted' });
        if (window._skriblPostedUI) window._skriblPostedUI.render(); }""")
    pg.wait_for_timeout(300)
    _glyphs = pg.evaluate("""() => {
        const rows = [...document.querySelectorAll('#postedList .posted-row')];
        return rows.map(r => {
          const icos = [...r.querySelectorAll('.posted-actions button .posted-ico')]
            .map(i => i.innerHTML.replace(/\\s+/g, ' ').trim());
          return { id: r.getAttribute('data-id'), n: icos.length,
                   uniq: new Set(icos).size }; }); }""")
    check("both visibility states are on the page to compare (fixture)",
          len(_glyphs) == 2 and all(g["n"] >= 3 for g in _glyphs),
          f"{_glyphs} — a row with fewer than three actions cannot show the "
          f"collision this row exists to catch")
    # AND IT CATCHES AN ICON THAT IS MISSING, not only one that is repeated --
    # which is worth knowing because the missing case is the one that actually
    # happened. Rewriting the icon table to replace this pair, the trash and
    # the key went out with them; `ICONS[name]` was then undefined, both
    # buttons rendered the literal "undefined" inside their svg, and this row
    # read 4 buttons and 3 distinct glyphs exactly as it does for a duplicate.
    # Calibrated by deleting those two entries again: 128/129, this row and no
    # other. A gate written for one failure that happens to cover its
    # neighbour is worth saying out loud, because the next person will assume
    # it does not.
    check("no two actions in one row draw the same glyph",
          bool(_glyphs) and all(g["n"] == g["uniq"] for g in _glyphs),
          f"{_glyphs} — n against uniq: a row where they differ has one "
          f"picture standing for two different acts")
    # AND THE TWO ROWS DIFFER FROM EACH OTHER, which uniqueness within a row
    # does not imply: a toggle that drew the same glyph in both states would
    # pass every row above and still say nothing about which state it is in.
    _states = pg.evaluate("""() => {
        const g = (id) => { const b = document.querySelector(
            '.posted-row[data-id="' + id + '"] .posted-gallery .posted-ico');
          return b ? b.innerHTML.replace(/\\s+/g, ' ').trim() : null; };
        return { on: g('glyphpub'), off: g('glyphoff') }; }""")
    check("...and the gallery switch draws a DIFFERENT glyph in each state",
          _states["on"] and _states["off"] and _states["on"] != _states["off"],
          f"on {str(_states['on'])[:40]!r}; off {str(_states['off'])[:40]!r}")

    # NOTHING ABOVE TOUCHED THE SERVER, which is the point of a row that can
    # no longer be forgotten: the post this page was seeded from is still
    # exactly where it was.
    with urllib.request.urlopen(f"{API}/{pid}", timeout=15) as r:
        still = json.loads(r.read())
    check("and the Skribl this page was seeded from is untouched on the server",
          still.get("id") == pid)
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
        # THE ENTRY HOLDS ITS REVOCATION KEY (SK-AUD-001). sendSkribl's success
        # object carried no deleteToken until that fix, so every Pad entry ever
        # written here had tok: null and the tray showed no Delete or Copy key
        # for it — Flip's entries had them all along. Pinned by SPENDING the
        # key rather than by its presence: a key the server does not honour is
        # a string in localStorage, not a capability.
        pad_tok = pad_saved[0].get("tok")
        check("...and the revocation key the server honours",
              bool(pad_tok) and delete_with(pad_saved[0].get("id"), pad_tok) == 204,
              f"tok={str(pad_tok)[:10]!r}… (a Pad entry without a key is the pre-SK-AUD-001 tree)")

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — a LOST RESPONSE, retried, is the same post and its key is in hand (SK-AUD-001)")
    #
    # The acquisition audit of v302 read the F2 rule ("anonymous callers get no
    # idempotency") to its end: a response lost in transit left an unlisted
    # post live on the server, the retry made a second one, and the lost
    # response had carried the ONLY copy of the first post's revocation key.
    # The fix is two client-minted capabilities (lib/posted.js): a client id
    # that scopes the anonymous Idempotency-Key without reopening F2, and a
    # delete token the browser mints BEFORE the request, so the answer can be
    # lost. Run as the journey: the server commits, the browser never hears,
    # the Pad falls back to a local save, the author presses Post again.
    lost = {}

    def swallow(route):
        # The request reaches the server and is answered; the answer is
        # dropped on the floor. Exactly a lost response, not a refused request.
        if route.request.method != "POST":
            return route.continue_()
        try:
            r = route.fetch()
            lost.update(r.json())
            lost["_status"] = r.status
        except Exception as e:                       # noqa: BLE001
            lost["_err"] = str(e)
        route.abort()

    lp = b.new_context().new_page()
    lp.goto(f"{BASE}/skribl-pad", wait_until="load")
    lp.wait_for_timeout(1200)
    lp.route(f"{API}**", swallow)
    lbox = lp.locator("#canvas").bounding_box()
    lp.mouse.move(lbox["x"] + 70, lbox["y"] + 70)
    lp.mouse.down()
    lp.mouse.move(lbox["x"] + 170, lbox["y"] + 140, steps=8)
    lp.mouse.up()
    lp.wait_for_timeout(400)
    lp.click("#recordBtn")
    lp.wait_for_timeout(600)
    lp.click("#postBtn")
    lp.wait_for_timeout(500)
    lp.fill("#postTitleInput", "Lost in transit")
    lp.click("#postSubmitBtn")
    lp.wait_for_timeout(2500)
    lp.unroute(f"{API}**")
    check("the server created the post the browser never heard about",
          lost.get("_status") == 201 and bool(lost.get("id")), str(lost)[:120])
    after_loss = lp.evaluate(READ)
    check("the Pad fell back to a local save",
          len(after_loss) == 1 and str(after_loss[0].get("id", "")).startswith("local_"),
          str(after_loss)[:120])
    # THE RETRY: same drawing, same title, the sheet reopened, Post pressed again.
    lp.keyboard.press("Escape")
    lp.wait_for_timeout(500)
    lp.click("#postBtn")
    lp.wait_for_timeout(500)
    replays = []
    lp.on("response", lambda r: replays.append(r) if r.request.method == "POST"
          and r.url.startswith(API) else None)
    lp.click("#postSubmitBtn")
    lp.wait_for_timeout(2500)
    rep = None
    for r in replays:
        try:
            rep = (r.status, r.json())
        except Exception:                            # noqa: BLE001
            rep = (r.status, {})
    posted = [e for e in lp.evaluate(READ) if not e.get("local")]
    check("the retry REPLAYED to the same post (200, idempotentReplay) rather than making a second",
          rep is not None and rep[0] == 200 and rep[1].get("idempotentReplay") is True
          and rep[1].get("id") == lost.get("id"),
          f"{rep!r} vs first id {lost.get('id')} — under the mutation that drops the "
          "client scope this is a 201 with a new id: the duplicate the audit named")
    check("...and Your Skribls lists that ONE post, by the first request's id",
          len(posted) == 1 and posted[0].get("id") == lost.get("id"),
          str(posted)[:120])
    # THE KEY. A replay answers with the id alone; the key that deletes the post
    # is the one this browser minted and sent with both requests. Spent, again.
    rtok = posted[0].get("tok") if posted else None
    check("...holding the key that takes it down, though no answer ever carried one",
          bool(rtok) and delete_with(lost.get("id"), rtok) == 204,
          f"tok={str(rtok)[:10]!r}… DELETE with it must be 204 — under the mutation that "
          "stops the client minting its token, the server's copy went down with the answer")
    lp.context.close()

    # FLIP, SEPARATELY. Same fix, different surface, and a different failure
    # mode: Flip sent NO Idempotency-Key at all before SK-AUD-001, so its retry
    # was a duplicate by construction, not by a reset key. Flip keeps the sheet
    # open on a network error, so the retry is the same button pressed again.
    lost2 = {}

    def swallow2(route):
        if route.request.method != "POST":
            return route.continue_()
        try:
            r = route.fetch()
            lost2.update(r.json())
            lost2["_status"] = r.status
        except Exception as e:                       # noqa: BLE001
            lost2["_err"] = str(e)
        route.abort()

    lf = b.new_context().new_page()
    lf.goto(f"{BASE}/flip", wait_until="load")
    lf.wait_for_timeout(1400)
    lf.route(f"{API}**", swallow2)
    fbox = lf.locator("#pad").bounding_box()
    lf.mouse.move(fbox["x"] + 60, fbox["y"] + 60)
    lf.mouse.down()
    lf.mouse.move(fbox["x"] + 150, fbox["y"] + 130, steps=8)
    lf.mouse.up()
    lf.wait_for_timeout(250)
    lf.click("#postBtn")
    lf.wait_for_timeout(400)
    lf.fill("#flipShareTitle", "Lost in transit, Flip")
    lf.click("#flipShareSubmit")
    lf.wait_for_timeout(2500)
    lf.unroute(f"{API}**")
    check("Flip: the server created the post the browser never heard about",
          lost2.get("_status") == 201 and bool(lost2.get("id")), str(lost2)[:120])
    check("Flip: the sheet says the server could not be reached, and stays for the retry",
          lf.is_visible("#flipShareError") and lf.is_visible("#flipShareSubmit"),
          lf.inner_text("#flipShareError") if lf.is_visible("#flipShareError") else "no error shown")
    freplays = []
    lf.on("response", lambda r: freplays.append(r) if r.request.method == "POST"
          and r.url.startswith(API) else None)
    lf.click("#flipShareSubmit")
    lf.wait_for_timeout(2500)
    frep = None
    for r in freplays:
        try:
            frep = (r.status, r.json())
        except Exception:                            # noqa: BLE001
            frep = (r.status, {})
    fposted = lf.evaluate(READ)
    check("Flip: the retry REPLAYED to the same post (200, idempotentReplay)",
          frep is not None and frep[0] == 200 and frep[1].get("idempotentReplay") is True
          and frep[1].get("id") == lost2.get("id"),
          f"{frep!r} vs first id {lost2.get('id')} — Flip sent no key at all before SK-AUD-001")
    check("Flip: ...and Your Skribls lists that ONE post, by the first request's id",
          len(fposted) == 1 and fposted[0].get("id") == lost2.get("id"), str(fposted)[:120])
    ftok = fposted[0].get("tok") if fposted else None
    check("Flip: ...holding the key that takes it down, though no answer ever carried one",
          bool(ftok) and delete_with(lost2.get("id"), ftok) == 204,
          f"tok={str(ftok)[:10]!r}… DELETE with it must be 204")
    lf.context.close()

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — without Web Crypto no capability is minted, and none is sent (RE-AUD-001)")
    #
    # The re-audit of the remediation tier read mintSecret() and found a
    # Math.random fallback where getRandomValues was absent -- a guessable
    # revocation key called a capability. A capability fails closed: with Web
    # Crypto gone the library mints nothing, stores nothing, both editors send
    # neither header, and the SERVER mints the key and returns it, exactly as
    # it did before the client could. Pinned on the wire (the headers the POST
    # actually carried) and on the outcome (the entry holds a key the server
    # honours), on both surfaces, with Web Crypto removed at the prototype so
    # no code path can find it. The Idempotency-Key is not a capability and
    # still rides.
    NO_CRYPTO = """(() => {
      try { Object.defineProperty(Crypto.prototype, 'getRandomValues',
                                  { value: undefined, configurable: true }); } catch (e) {}
      try { localStorage.removeItem('skribl_client_v1'); } catch (e) {}
    })();"""
    CAPS = "(() => ({ tok: window.SkriblPosted.mintSecret(), cid: window.SkriblPosted.clientId(), " \
           "stored: localStorage.getItem('skribl_client_v1'), " \
           "grv: typeof crypto.getRandomValues }))()"

    def nocrypto_page(path):
        ctx = b.new_context()
        ctx.add_init_script(NO_CRYPTO)
        page = ctx.new_page()
        sent = []
        page.on("request", lambda r: sent.append(dict(r.headers))
                if r.method == "POST" and r.url.startswith(API) else None)
        page.goto(f"{BASE}{path}", wait_until="load")
        page.wait_for_timeout(1200)
        return page, sent

    def cap_pins(label, page, sent, entry):
        caps = page.evaluate(CAPS)
        check(f"{label}: the fixture really removed Web Crypto",
              caps["grv"] == "undefined", f"typeof crypto.getRandomValues = {caps['grv']}")
        check(f"{label}: mintSecret() is null, not a Math.random string",
              caps["tok"] is None, repr(caps["tok"]))
        check(f"{label}: clientId() is null and nothing was stored",
              caps["cid"] is None and caps["stored"] is None,
              f"cid={caps['cid']!r} stored={caps['stored']!r}")
        hdrs = sent[-1] if sent else {}
        check(f"{label}: the POST carried NEITHER client capability header",
              bool(sent) and "x-skribl-client" not in hdrs and "x-skribl-delete-token" not in hdrs,
              str({k: v[:12] for k, v in hdrs.items() if k.startswith("x-skribl")}) if sent else "no POST seen")
        check(f"{label}: ...but still an Idempotency-Key, which is not a capability",
              bool(sent) and bool(hdrs.get("idempotency-key")), "no key on the wire")
        tok = (entry or {}).get("tok")
        check(f"{label}: the entry holds the SERVER's key, and it takes the post down",
              bool(entry) and bool(tok) and len(tok) >= 32 and delete_with(entry.get("id"), tok) == 204,
              f"entry={str(entry)[:80]}")

    # THE PAD.
    np_, sent = nocrypto_page("/skribl-pad")
    nbox = np_.locator("#canvas").bounding_box()
    np_.mouse.move(nbox["x"] + 60, nbox["y"] + 60)
    np_.mouse.down()
    np_.mouse.move(nbox["x"] + 160, nbox["y"] + 130, steps=8)
    np_.mouse.up()
    np_.wait_for_timeout(400)
    np_.click("#recordBtn")
    np_.wait_for_timeout(600)
    np_.click("#postBtn")
    np_.wait_for_timeout(500)
    np_.fill("#postTitleInput", "No Web Crypto, Pad")
    np_.click("#postSubmitBtn")
    np_.wait_for_timeout(2500)
    nentries = [e for e in np_.evaluate(READ) if not e.get("local")]
    cap_pins("Pad", np_, sent, nentries[0] if nentries else None)
    np_.context.close()

    # FLIP.
    nf, sent2 = nocrypto_page("/flip")
    fbox2 = nf.locator("#pad").bounding_box()
    nf.mouse.move(fbox2["x"] + 60, fbox2["y"] + 60)
    nf.mouse.down()
    nf.mouse.move(fbox2["x"] + 150, fbox2["y"] + 130, steps=8)
    nf.mouse.up()
    nf.wait_for_timeout(250)
    nf.click("#postBtn")
    nf.wait_for_timeout(400)
    nf.fill("#flipShareTitle", "No Web Crypto, Flip")
    nf.click("#flipShareSubmit")
    nf.wait_for_timeout(2500)
    fentries = nf.evaluate(READ)
    cap_pins("Flip", nf, sent2, fentries[0] if fentries else None)
    nf.context.close()

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — a local-only save IS listed, on this device, and survives the sweep")
    #
    # Pad falls back to a local save when the server is unreachable — exactly
    # where a tester on a bad connection ends up — and tells them it is saved
    # on this device. This section used to pin that such a save is NOT listed,
    # because it has no link to send. SK-AUD-010 (acquisition audit of v302):
    # lib/posted.js's sweepOrphans() deletes every 'skribl_post_*' blob with no
    # index entry the next time the store is full, so the unlisted save was the
    # one thing storage pressure could remove, under a success message. It is
    # listed now, flagged, with nothing to send; the mutation that removes the
    # indexing makes the sweep delete the blob again and reddens the pin below.
    pd.evaluate("() => localStorage.setItem('skribl_posted_v1', '[]')")
    before = len(pd.evaluate(READ))
    pd.evaluate("""() => {
      if (window.SkriblPosted) window.SkriblPosted.add({ id: '', kind: 'pad' });
    }""")
    check("an entry with no id is still refused by the store",
          len(pd.evaluate(READ)) == before)

    HAS_BLOB = "(id) => !!localStorage.getItem('skribl_post_' + id)"

    def local_post(title):
        """A fresh Pad in a NEW CONTEXT, one stroke, and every POST to the API
        dying on the wire, so the composer takes its local fallback.
        A new context rather than a reload: a reload restores the previous
        page's drawing with its take finished, and a finished take LOCKS the
        canvas, so the stroke would draw nothing and Record never appear (the
        v240 fixture lesson, again)."""
        page = b.new_context().new_page()
        page.goto(f"{BASE}/skribl-pad", wait_until="load")
        page.wait_for_timeout(1200)
        page.route(f"{API}**", lambda route: route.abort()
                   if route.request.method == "POST" else route.continue_())
        box = page.locator("#canvas").bounding_box()
        page.mouse.move(box["x"] + 60, box["y"] + 60)
        page.mouse.down()
        page.mouse.move(box["x"] + 160, box["y"] + 130, steps=8)
        page.mouse.up()
        page.wait_for_timeout(400)
        page.click("#recordBtn")
        page.wait_for_timeout(600)
        page.click("#postBtn")
        page.wait_for_timeout(500)
        page.fill("#postTitleInput", title)
        page.click("#postSubmitBtn")
        page.wait_for_timeout(2500)
        page.unroute(f"{API}**")
        return page

    pd.close()
    pd = local_post("Kept on this phone")
    loc = pd.evaluate(READ)
    lid = str((loc[0] if loc else {}).get("id", ""))
    check("the local save is recorded", len(loc) == 1 and lid.startswith("local_"),
          str(loc)[:120])
    check("...flagged as local", bool(loc) and loc[0].get("local") is True,
          str((loc[0] if loc else {}).get("local")))
    check("...and its bytes are under the blob key", pd.evaluate(HAS_BLOB, lid),
          "no entry, so no id to look under" if not lid else "")
    # v315 (SK312-008): it leads with what did NOT happen, drawn as a warning,
    # and offers the way to finish -- an outside audit pointed out that people
    # scan an outcome rather than read it, and "Saved on this device only"
    # under a button called Post scans as success.
    _st = pd.evaluate("""() => ({ text: document.getElementById('postStatusLabel').textContent,
        warn: document.getElementById('postStatus').classList.contains('error'),
        retry: !document.getElementById('postSubmitBtn').hidden
               && !document.getElementById('postSubmitBtn').disabled,
        label: document.getElementById('postSubmitLabel').textContent })""")
    check("the status says NOT POSTED, then where it is, drawn as a warning",
          _st["text"].lower().startswith("not posted") and "this device" in _st["text"].lower()
          and _st["warn"], str(_st))
    check("...and the sheet offers Try again, live",
          _st["retry"] and _st["label"] == "Try again", str(_st))

    pd.goto(f"{BASE}/library", wait_until="load")
    pd.wait_for_timeout(900)
    # Counted before it is read: a missing row must FAIL by name here, not wedge
    # the run on a locator that never resolves (the v287 rule).
    rows = pd.locator("#postedList .posted-row-local")
    nrows = rows.count()
    row = rows.first.inner_text() if nrows else ""
    check("the tray shows it as a local row that says not posted, on this device only",
          nrows == 1 and "not posted" in row.lower() and "on this device" in row.lower(),
          f"{nrows} local rows; text {row[:60]!r}")
    check("...and offers nothing to send",
          nrows == 1 and pd.evaluate(
              "() => document.querySelectorAll('#postedList .posted-row-local "
              ".posted-copy, #postedList .posted-row-local .posted-delete, "
              "#postedList .posted-row-local .posted-key').length") == 0)
    check("...its link is the on-device player",
          nrows == 1 and "#skribl=" in (pd.get_attribute(
              "#postedList .posted-row-local a", "href") or ""))

    # THE ORPHAN SWEEP is the mechanism that used to delete it: an unindexed
    # 'skribl_post_*' blob is, by its definition, unreachable. Listed, it is not.
    freed = pd.evaluate("() => window.SkriblPosted.sweepOrphans()")
    check("the orphan sweep does not delete a listed local save",
          bool(lid) and pd.evaluate(HAS_BLOB, lid) and len(pd.evaluate(READ)) == 1,
          f"sweepOrphans freed {freed} bytes — under the mutation that stops "
          "indexing local saves, this is where the blob goes")

    # The × destroys the only copy, so it arms first, like the tile delete.
    if nrows == 1:
        pd.click("#postedList .posted-row-local .posted-del")
        pd.wait_for_timeout(200)
    check("one tap on the local row's × arms rather than deletes",
          nrows == 1 and len(pd.evaluate(READ)) == 1 and pd.evaluate(HAS_BLOB, lid))
    if nrows == 1 and pd.evaluate(READ):     # still there to tap (not under the arm mutation)
        pd.click("#postedList .posted-row-local .posted-del")
        pd.wait_for_timeout(300)
    # THE BYTES OUTLIVE THE TAP BY EXACTLY ONE DECISION (v307). This used to
    # assert that the second tap deleted the entry AND its bytes in the same
    # breath, which was right while the tap was final. The x is undoable for
    # twelve seconds now, and an undo that restored the entry while the payload
    # was already gone would put back a row whose link opens nothing -- so the
    # bytes are HELD for the window and dropped when it closes.
    #
    # The invariant this row has always guarded is unchanged and is asserted in
    # two halves below: a removed local save's blob never outlives the decision.
    # What moved is when the decision is made.
    check("the second tap removes the entry",
          nrows == 1 and len(pd.evaluate(READ)) == 0,
          "the entry is still in the index after an armed second tap")
    check("...and HOLDS its bytes while undo is on offer",
          nrows == 1 and pd.evaluate(HAS_BLOB, lid),
          "dropped at removal time — undo would restore a row whose link "
          "opens nothing, which is worse than no undo")
    check("...behind a shelf that says so",
          nrows == 1 and pd.evaluate(
              "() => { const u = document.getElementById('postedUndo'); "
              "return !!u && !u.hidden; }"),
          "bytes held for a window nobody was told about")
    # DISMISS IS THE COMMIT, and it is driven rather than waited out: the
    # twelve seconds are a product choice, not something to sleep through in a
    # browser test. It is also the honest affordance -- somebody who has
    # decided gets the space back when they say so.
    if nrows == 1:
        pd.click("#postedUndoX")
        pd.wait_for_timeout(200)
    check("...and dismissing the shelf deletes the bytes",
          nrows == 1 and not pd.evaluate(HAS_BLOB, lid),
          "the blob survived the decision — this is the orphan the sweep "
          "exists to collect, and it should never have been made")

    # EVICTION IS THE DISCLOSED POLICY, and it is a different thing from the
    # sweep: when the store is genuinely full, reclaim() drops the OLDEST local
    # save, entry and bytes together, so a drawing in front of the user is not
    # lost for want of room. Until local saves were indexed, evictOldest()
    # matched nothing and was dead code — the sweep was doing the evicting,
    # silently and oldest-last. Pinned from the other side: an eviction never
    # strands a blob, and the tray says the policy where the saves are listed.
    pd2 = local_post("Second local save")
    loc2 = pd2.evaluate(READ)
    lid2 = str((loc2[0] if loc2 else {}).get("id", ""))
    check("a second local save is recorded", len(loc2) == 1 and lid2.startswith("local_"))
    freed = pd2.evaluate("() => window.SkriblPosted.reclaim(1)")
    check("a full store evicts the oldest local save, entry and bytes TOGETHER",
          bool(lid2) and freed > 0 and len(pd2.evaluate(READ)) == 0
          and not pd2.evaluate(HAS_BLOB, lid2),
          f"freed {freed}; entries {len(pd2.evaluate(READ))}; "
          f"blob {pd2.evaluate(HAS_BLOB, lid2) if lid2 else 'n/a'}")
    # AND IT IS STILL DISCLOSED, somewhere a person can reach. It used to be
    # the fourth clause of a forty-six-word paragraph above the list, which on
    # a 390px phone was seven lines and 116px of caveat read before a single
    # Skribl was visible; v311 cut that note to the one sentence somebody can
    # act on while looking at the page and moved this rule into the "Your
    # Skribls" tip in How it works, beside the rest of the browser-storage
    # model. Both halves are pinned, because the failure this row guards
    # against is the policy going undisclosed -- and a move is one edit away
    # from a deletion.
    pd2.goto(f"{BASE}/library", wait_until="load")
    pd2.wait_for_timeout(900)
    foot = pd2.inner_text("#postedPanel .posted-foot-top").lower()
    check("the list still says whose browser it is and what clears it",
          "this browser" in foot and "site data" in foot, foot[:160])
    check("...in a sentence short enough to be read, not a paragraph",
          len(foot.split()) <= 24,
          f"{len(foot.split())} words: {foot[:160]}")
    pd2.goto(f"{BASE}/skribl-pad", wait_until="load")
    pd2.wait_for_timeout(1200)
    _tip = pd2.evaluate("""() => {
        const d = document.getElementById('helpDrawer'); if (!d) return null;
        const t = [...d.querySelectorAll('.help-tip')].find(
          e => /your skribl library/i.test((e.querySelector('.help-pill') || {}).textContent || ''));
        return t ? t.innerText.toLowerCase() : null; }""")
    check("...and How it works states the eviction policy in full",
          bool(_tip) and "oldest" in _tip and "full" in _tip,
          f"{str(_tip)[:200]!r} — the policy has to be written down somewhere, "
          f"and this is where the rest of the browser-storage model is")
    pd2.close()

    # -----------------------------------------------------------------------
    print("\nYOUR SKRIBLS — Try again after a device-only save: one copy, then a real post")
    # v315. Try again posts the same drawing from the same sheet. Two ways it
    # can go and both are pinned: still no server, and the retry must REPLACE
    # the device-only copy rather than add a second; the server is back, and
    # the post must SUPERSEDE the copy, bytes and all -- otherwise the library
    # keeps the same drawing twice, once as "not posted", which is the exact
    # confusion the wording change exists to remove.
    pr = local_post("Retry me")
    first = [e for e in pr.evaluate(READ) if e.get("local")]
    fid = str(first[0]["id"]) if first else ""
    check("the fixture: one device-only save to retry", len(first) == 1, str(first)[:120])
    pr.route(f"{API}**", lambda route: route.abort()
             if route.request.method == "POST" else route.continue_())
    pr.click("#postSubmitBtn")
    pr.wait_for_timeout(2500)
    pr.unroute(f"{API}**")
    again = [e for e in pr.evaluate(READ) if e.get("local")]
    check("a retry that still cannot reach the server REPLACES the copy, it does not add one",
          len(again) == 1 and str(again[0]["id"]) != fid and not pr.evaluate(HAS_BLOB, fid),
          f"{len(again)} local entries; first blob still there={pr.evaluate(HAS_BLOB, fid) if fid else None}")
    sid = str(again[0]["id"]) if again else ""
    pr.click("#postSubmitBtn")
    for _ in range(60):
        pr.wait_for_timeout(100)
        if not [e for e in pr.evaluate(READ) if e.get("local")]:
            break
    after = pr.evaluate(READ)
    check("...and one that reaches it POSTS, and the device-only copy is gone, bytes and all",
          len(after) == 1 and not after[0].get("local") and not str(after[0]["id"]).startswith("local_")
          and not pr.evaluate(HAS_BLOB, sid),
          f"{after!r}"[:200])
    check("...and the sheet says posted, not a warning",
          pr.evaluate("() => !document.getElementById('postStatus').classList.contains('error')")
          and "not posted" not in pr.inner_text("#postStatusLabel").lower(),
          pr.inner_text("#postStatusLabel"))
    pr.close()

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

    # --------------------------------------------------------------------
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

    print("\nCSRF — the destructive paths send the token the POST path sends")
    # NOT because either route consults it: bp.skribl_csrf is checked on POST
    # and nowhere else, and routes.py now says so precisely instead of implying
    # an authenticated deployment had "settled it". What keeps DELETE safe is
    # the CORS preflight plus a bearer token in the body.
    #
    # The header is sent anyway so that enforcing csrf on these routes stays a
    # one-line change rather than a breaking one — the position routes.py's
    # note takes, which is only true while the clients actually do it. This
    # assertion is what makes it true rather than intended.
    hdrs = pd.evaluate("""() => {
        window.SKRIBL_CSRF_TOKEN = 'csrf-probe-value';
        let seen = null;
        const real = window.fetch;
        window.fetch = (u, o) => { seen = (o && o.headers) || {}; return Promise.resolve(
            { ok: true, status: 200 }); };
        window.SkriblPosted.add({ id: 'csrfrow', title: 'c', kind: 'pad', tok: 'k' });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
        window._skriblPostedUI.destroyForTest
          ? window._skriblPostedUI.destroyForTest({ id: 'csrfrow', tok: 'k' }, () => {})
          : null;
        window.fetch = real;
        return seen;
      }""")
    if hdrs is None:
        # No test seam on the module; drive the real button instead. It ARMS
        # on the first tap and acts on the second (SK-AUD-014), so two clicks.
        hdrs = pd.evaluate("""() => {
            window.SKRIBL_CSRF_TOKEN = 'csrf-probe-value';
            let seen = null;
            const real = window.fetch;
            window.fetch = (u, o) => { seen = (o && o.headers) || {};
                return Promise.resolve({ ok: true, status: 200 }); };
            const b = document.querySelector('.posted-row[data-id="csrfrow"] .posted-delete');
            if (b) { b.click(); b.click(); }
            window.fetch = real;
            return seen; }""")
    check("the tray's DELETE carries X-Skribl-CSRF when the host issued one",
          isinstance(hdrs, dict) and hdrs.get("X-Skribl-CSRF") == "csrf-probe-value",
          f"{hdrs!r} — the POST path has always sent it; a DELETE that does not "
          "is what would make enforcing csrf on that route a breaking change")
    pd.evaluate("() => { delete window.SKRIBL_CSRF_TOKEN; }")

    print("\nTRAY LINKS — 'watch it' honours the host's player_target")
    # __init__.py names three paths that open the player — Pad's watch button,
    # Flip's anchor, and this tray link — and says _blank is their DEFAULT,
    # with a host passing player_target="_self" taking over. Two of the three
    # read the configured value. This one hardcoded target="_blank" until v281,
    # so an SPA rendering /s/<id> in its own shell was obeyed twice and ignored
    # here. verify_delivery covers the other two and never covered this one,
    # which is the sort of coincidence that stops looking like one.
    #
    # ASSERTED BY OVERRIDING THE GLOBAL, not by reading the source: with the
    # harness server's default the configured value IS _blank, so a hardcoded
    # _blank and a correct read are indistinguishable. Setting it to _self
    # first is what tells them apart.
    pd.evaluate("""() => {
        window.SKRIBL_PLAYER_TARGET = '_self';
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'linktarget', title: 'link',
                                  kind: 'pad', url: '/s/linktarget' });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }""")
    pd.wait_for_timeout(250)
    tgt = pd.evaluate("""() => {
        const a = document.querySelector('.posted-row[data-id="linktarget"] .posted-main');
        return a ? a.getAttribute('target') : null; }""")
    check("the tray link uses the configured player target, not a literal",
          tgt == "_self",
          f"target={tgt!r} with player_target set to _self — hardcoding _blank "
          "here overrides a host that routes the player itself")
    # ...and back to the default, so the rest of the section is unaffected.
    pd.evaluate("() => { window.SKRIBL_PLAYER_TARGET = '_blank'; }")

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

    print("\nYOUR SKRIBLS — on a phone, a row with three actions keeps its words on one line")
    # Owner, v293, from an iPhone: the one row that holds a deletion key —
    # Copy link, Delete, Copy key — starved its title column until "4 pages ·
    # 41 min ago" wrapped one word per line. Every other row has one action
    # and never showed it; this suite measured rows at a desktop width only.
    # The meta line is the thing that never yields: it stays one line, and on
    # the compact size class a row with more than one action puts its actions
    # under the title instead of beside it. Measured at 390 with a keyed row
    # and a plain one seeded side by side.
    pm = b.new_page(viewport={"width": 390, "height": 844})
    pm.goto(BASE + "/library", wait_until="load")
    pm.wait_for_timeout(900)
    pm.evaluate("""() => {
        localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'keyedrow', title: 'F.', kind: 'flip', pages: 4, tok: 'k' });
        window.SkriblPosted.add({ id: 'plainrow', title: 'Tttt', kind: 'pad' });
        if (window._skriblPostedUI) window._skriblPostedUI.render();
      }""")
    pm.wait_for_timeout(300)
    _rows = pm.evaluate("""() => {
        const out = {};
        for (const id of ['keyedrow', 'plainrow']) {
          const r = document.querySelector('.posted-row[data-id="' + id + '"]'); if (!r) { out[id] = null; continue; }
          const sub = r.querySelector('.posted-sub'), main = r.querySelector('.posted-main');
          const acts = [...r.querySelectorAll('.posted-copy, .posted-delete, .posted-key')];
          const lh = parseFloat(getComputedStyle(sub).lineHeight) || 14;
          out[id] = { subLines: Math.round(sub.getBoundingClientRect().height / lh),
                      subText: sub.textContent.trim(), actions: acts.length,
                      actionsBelow: acts.length ? Math.min(...acts.map(a => a.getBoundingClientRect().top)) >= main.getBoundingClientRect().bottom - 1 : null,
                      minActionH: acts.length ? Math.min(...acts.map(a => Math.round(a.getBoundingClientRect().height))) : null,
                      rowW: Math.round(r.getBoundingClientRect().width), overflow: r.scrollWidth > r.clientWidth + 1 }; }
        return out; }""")
    _k, _p = _rows.get("keyedrow"), _rows.get("plainrow")
    check("at 390: the keyed row's meta line is ONE line", _k and _k["subLines"] == 1, str(_k))
    check("at 390: ...and its three actions sit under the title, not beside it", _k and _k["actions"] == 3 and _k["actionsBelow"], str(_k))
    check("at 390: ...each still tall enough to tap (24px floor, a neighbour on each side)", _k and _k["minActionH"] >= 24, str(_k))
    check("at 390: the plain row keeps its one action beside the title", _p and _p["actions"] == 1 and _p["actionsBelow"] is False and _p["subLines"] == 1, str(_p))
    check("at 390: neither row overflows its box", _k and _p and not _k["overflow"] and not _p["overflow"], f"{_k} {_p}")
    pm.close()

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
    # TAP TWICE, or this section measures nothing. Delete ARMS on the first
    # tap (SK-AUD-014; it used to ask confirm(), and Playwright auto-DISMISSES
    # dialogs, so the first version of this test clicked once, had the confirm
    # silently refused, never reached destroy(), and asserted the entry was
    # still present — which it was, for the wrong reason; it passed with the
    # 404-as-success bug fully restored). The armed state is asserted on the
    # way, and a dialog appearing now is itself a failure.
    _dlg = []
    pd.on("dialog", lambda d: (_dlg.append(d.message), d.dismiss()))
    pd.evaluate("() => window.SkriblRecoveryKey.closeRecover()")
    pd.evaluate("() => window._skriblPostedUI && window._skriblPostedUI.render()")
    pd.wait_for_timeout(500)
    pd.click(f'.posted-row[data-id="{kept}"] .posted-delete')
    pd.wait_for_timeout(300)
    check("the first tap on Delete arms it and says what the second does",
          "cannot be undone" in (pd.get_attribute(
              f'.posted-row[data-id="{kept}"] .posted-delete', "aria-label") or "").lower()
          and "cannot be undone" in pd.inner_text("#postedStatus").lower()
          and not _dlg,
          f"dialogs {_dlg}; live {pd.inner_text('#postedStatus')!r}")
    if pd.locator(f'.posted-row[data-id="{kept}"] .posted-delete:not([disabled])').count():
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
    _pg.goto(f"{BASE}/library", wait_until="load")
    _pg.wait_for_timeout(1300)
    _pg.evaluate("""() => {
      window.SkriblPosted.add({id:'ic1', url:'/s/ic1', kind:'flip', pages:9, title:'A flip'});
      window.SkriblPosted.add({id:'ic2', url:'/s/ic2', kind:'pad', pages:1, title:'A pad'});
      if (window._skriblPostedUI) window._skriblPostedUI.render();
    }""")
    _pg.wait_for_timeout(400)

    check("no legacy glyph characters remain in the tray",
          _pg.evaluate("() => !document.getElementById('postedList')"
                       ".textContent.match(/[\u25A6\u270E]/)"),
          "a font glyph renders at whatever weight the system font chooses")

    # WHERE THE MARK LIVES IS PART OF THE ASSERTION. It sat on the thumb until
    # v310 and stands in front of the words now ("move the pencil/book
    # before replay/pages"), so these rows ask the ROW for its mark rather than
    # the thumb: a row that LOST the mark and a row that merely moved it read
    # the same to a thumb-only query, and only the first is a regression. The
    # row's own id says whose mark it is -- .posted-kind alone would be
    # satisfied by the other row's.
    # firstCHILD, not firstElementChild: the words beside the mark are a TEXT
    # node, so an element-only comparison finds the mark first whether it leads
    # the line or trails it. The calibration ran the mark back behind the words
    # and this row went green -- on the one thing it is here to see.
    for _kind, _id in (("flip", "ic1"), ("pad", "ic2")):
        _mark = _pg.evaluate(
            '(id) => { const r = document.querySelector('
            '    \'.posted-row[data-id="\' + id + \'"]\');'
            '  if (!r) return null;'
            '  const sub = r.querySelector(".posted-sub");'
            '  const k = r.querySelector(".posted-kind");'
            '  return { there: !!(k && k.querySelector("svg")),'
            '           inSub: !!(k && sub && sub.contains(k)),'
            '           first: !!(sub && sub.firstChild === k) }; }', _id)
        check(f"a {_kind} entry uses an inline SVG icon, in front of the words it qualifies",
              bool(_mark) and _mark["there"] and _mark["inSub"] and _mark["first"],
              f"{_mark} \u2014 still a text glyph, or back on the thumb")

    # The Flip icon must be the SAME path the header uses to open Flip. Compared
    # by geometry, not by eye: a different book would pass a "has an svg" check.
    _tray = _pg.evaluate(
        '() => { const r = document.querySelector(\'.posted-row[data-id="ic1"]\');'
        '  const el = r && r.querySelector(\'.posted-kind svg path\');'
        '  return el ? el.getAttribute(\'d\') : null; }')
    _pd = _b.new_page()
    _pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    _pd.wait_for_timeout(1200)
    _hdr = _pd.evaluate("() => { const el = document.querySelector('#flipBtn svg path');"
                        " return el ? el.getAttribute('d') : null; }")
    check("the tray's Flip icon is the same book that opens Flip",
          _tray is not None and _tray == _hdr,
          f"tray {_tray!r} vs header {_hdr!r}")
    _pd.close()

    # COUNTED, THEN MEASURED. `.posted-thumb svg` matched only the sound badge
    # once the mark moved, and an .every() over an empty list is true.
    _sizes = _pg.evaluate("() => [...document.querySelectorAll('.posted-kind svg')]"
                          ".map(s => s.getBoundingClientRect().width)")
    check("the tray icons render at a visible size",
          len(_sizes) >= 2 and all(w > 10 for w in _sizes),
          f"{_sizes} \u2014 collapsed, or not there at all")
    _b.close()

summarise_and_exit()
