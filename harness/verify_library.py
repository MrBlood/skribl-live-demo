"""The profile's Skribls tab: real posts, one payload at a time, one player.

/library used to be a MOCK. It carried its own replay engine and a table of
hand-drawn motifs, and rendered those — nothing on it had ever been posted by
anyone, while it was registered as a real route that a host mounting Skribl got
in their own URL space. README.md carried a warning saying so.

That is the shape of thing this harness exists to refuse, and the reason is not
the pretending: a page that draws its own content cannot tell you whether the
thing it previews WORKS. This suite is what replaced the warning.

THREE PROPERTIES, in the order they matter:

  1. IT PLAYS REAL POSTS. Fixtures are recorded in Pad and posted through the
     API; the page reads GET /api/skribls and plays what comes back.
  2. IT IS NOT A THIRD PLAYER. The stage is inlineplayer.js — the same one the
     feed and a host's composer use — driven through the handle it exposes.
     Three replay implementations would drift, and verify_sharedrules.py's note
     says what that costs: nothing an author can see reveals it.
  3. IT FETCHES ONE PAYLOAD AT A TIME. The grid is share-card images. Fifty
     mounted players each holding a payload is tens of megabytes for a page of
     thumbnails, which is the exact cost GET /api/skribls returns metadata to
     avoid.
"""
import json
import math
import os
import pathlib
import re
import sys
import urllib.request
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))          # the server-side seam check imports skribl

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the library works.")
    raise SystemExit(77)

results = []


check = make_check(results)


# THROUGH THE SHEET, IN ONE BROWSER CONTEXT (v304). The fixtures used to be
# posted with a fetch() evaluated in the Pad's page, marked public, and the
# library read the public listing. A profile is somebody's now: with no host
# identity, /library shows what THIS BROWSER posted, from the record
# lib/posted.js writes when the sheet's post succeeds. So the fixtures go
# through the real sheet, and every page in this suite shares one context —
# a fresh Playwright page is a fresh localStorage, which is exactly the
# "another browser" case, pinned separately below.
def post_one(ctx, title, turns=4, tick=False):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => { localStorage.removeItem('skribl_draft_v2'); if (window.SkriblHints) window.SkriblHints.hide(); }")
    box = pg.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(70):
        t = i / 70
        pg.mouse.move(cx + math.cos(t * math.pi * turns) * (25 + t * 140),
                      cy + math.sin(t * math.pi * turns) * (25 + t * 110))
        if i % 5 == 0:
            pg.wait_for_timeout(90)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    if pg.is_visible("#recordBtn"):
        pg.click("#recordBtn")
        pg.wait_for_timeout(400)
    pg.click("#postBtn")
    pg.wait_for_timeout(400)
    pg.fill("#postTitleInput", title)
    if tick:
        pg.click(".post-check")
    got = {}
    pg.on("response", lambda r: got.update(r.json()) if (r.request.method == "POST"
          and r.url.split("?")[0].endswith("/api/skribls") and r.ok) else None)
    pg.click("#postSubmitBtn")
    for _ in range(100):
        pg.wait_for_timeout(100)
        if "id" in got and not pg.evaluate("() => document.getElementById('postResult').hidden"):
            break
    pg.close()
    return got.get("id")


with sync_playwright() as sp:
    b = sp.chromium.launch()

    # UNIQUE PER RUN. run_harness.sh gives one server and one database to every
    # suite in an invocation, so the search assertion below was matching
    # verify_inline.py's "Harness fixture A" as well as this suite's own — two
    # tiles where it wanted one, intermittently, depending on which suites ran.
    # Exactly the cross-suite state START-HERE.md warns passes the seal and
    # fails CI. A token nothing else can produce makes the query this suite's.
    tag = "lib" + os.urandom(4).hex()
    ctx = b.new_context()
    # alpha stays unlisted (the box at its default); beta is ticked public.
    ids = [post_one(ctx, tag + " alpha", 4), post_one(ctx, tag + " beta", 2, tick=True)]
    if not all(ids):
        check("two skribls posted through the sheet (fixture)", False, str(ids))
        print("\n" + "=" * 62 + "\n0/1 passed")
        sys.exit(1)
    check("two skribls posted through the sheet (fixture)", True, ", ".join(ids))

    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1280, "height": 1000})
    errs = []
    payload_reqs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: payload_reqs.append(r.url)
          if re.search(r"/api/skribls/[A-Za-z0-9_-]+$", r.url) else None)
    browsing.goto(pg, BASE, "/library")

    tiles = pg.evaluate("() => document.querySelectorAll('#postedList .posted-row').length")
    check("the grid is built from real posts, not from demo motifs",
          tiles >= 2, f"{tiles} tiles")
    check("no page errors", not errs, "; ".join(errs[:2]))

    # ONE PAYLOAD, for the one drawing on the stage. Not one per tile.
    check("only the selected Skribl's payload is fetched",
          len(payload_reqs) == 1,
          f"{len(payload_reqs)} payload fetch(es) for {tiles} tiles: "
          f"{payload_reqs}")
    check("every tile's picture is the poster, which is one cached image",
          pg.evaluate("""() => [...document.querySelectorAll('#postedList .posted-poster')]
             .every(i => /\\/s\\/[^/]+\\/poster$/.test(i.getAttribute('src')))"""))
    # FOLLOWED, not read. These fixtures are posted through serializeSkribl()
    # and carry no thumbnail, so whatever the tile's src is, the bytes that
    # arrive are the server's fallback — and the fallback used to be the
    # branded 1200x630 share card, which every tile then showed cropped to
    # "ibl Pad / that replay in time with music" (v287 audit SK-BUG-006). fetch()
    # exposes the URL a redirect landed on; an <img> does not.
    _landed = pg.evaluate("""async () => {
        const img = document.querySelector('#postedList .posted-poster');
        const r = await fetch(img.getAttribute('src'));
        return r.url; }""")
    check("a tile with no thumbnail does NOT land on the branded share card",
          "og-card" not in _landed, f"landed on {_landed}")

    # ---- the stage IS the in-post player -----------------------------------
    st = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline && window.SkriblInline.players()
                   .filter(x => x.el === el)[0];
        return p ? p.state() : null; }""")
    check("the stage is an inlineplayer instance, not a second replay engine",
          st is not None and st["loaded"] is True, json.dumps(st))
    check("it loaded a real drawing with a real duration",
          st and st["totalMs"] > 300, f"totalMs={st and st['totalMs']}")

    title0 = pg.inner_text("#pTitle")
    check("the newest Skribl is on the stage", title0.strip() != "—", title0)

    # ---- the transport -----------------------------------------------------
    pg.click("#btnPlay")
    pg.wait_for_timeout(900)
    moving = pg.evaluate("""() => ({
        frac: parseFloat(document.getElementById('scrubFill').style.width) || 0,
        label: document.getElementById('tElapsed').textContent })""")
    check("play advances the scrub and the clock",
          0 < moving["frac"] < 100 and not moving["label"].startswith("0:00 /"),
          json.dumps(moving))
    # The transport reads the PLAYER's clock. Two clocks is two answers to "how
    # far through is it", and the one on screen would be the wrong one.
    live = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline.players().filter(x => x.el === el)[0].state();
        const shown = parseFloat(document.getElementById('scrubFill').style.width) || 0;
        return { player: p.totalMs ? p.elapsedMs / p.totalMs * 100 : 0, shown: shown }; }""")
    check("the scrub shows the player's own clock rather than one of its own",
          abs(live["player"] - live["shown"]) < 12,
          f"player {live['player']:.1f}% vs shown {live['shown']:.1f}%")

    pg.click("#btnPlay")
    pg.wait_for_timeout(500)
    paused = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0]
                 .state().state; }""")
    check("play/pause is a toggle", paused == "paused", paused)

    pg.click("#btnRestart")
    pg.wait_for_timeout(300)
    pg.click("#btnPlay")            # restart plays; this pauses it again
    pg.wait_for_timeout(200)
    restarted = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0]
                 .state().elapsedMs; }""")
    check("restart goes back to the beginning",
          restarted < 900, f"elapsedMs={restarted:.0f}")

    # Scrub: click three-quarters along and the player must be there.
    pg.evaluate("""() => {
        const s = document.getElementById('scrub');
        const r = s.getBoundingClientRect();
        s.dispatchEvent(new MouseEvent('click', {
          clientX: r.left + r.width * 0.75, clientY: r.top + r.height / 2,
          bubbles: true })); }""")
    pg.wait_for_timeout(300)
    sought = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline.players().filter(x => x.el === el)[0].state();
        return p.totalMs ? p.elapsedMs / p.totalMs : -1; }""")
    check("the scrub track seeks the drawing",
          0.6 < sought < 0.9, f"landed at {sought:.2f} of the replay")

    # A post has no loop toggle (inlineplayer.css says why); a page ABOUT one
    # does, because somebody looking at a single drawing may want it to stop.
    pg.click("#btnLoop")
    pg.wait_for_timeout(100)
    pg.click("#btnRestart")
    pg.wait_for_timeout(4000)
    ended = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0].state(); }""")
    check("with loop off the replay stops at the end instead of going round",
          ended["state"] != "playing"
          and ended["elapsedMs"] >= ended["totalMs"] - 60,
          json.dumps(ended))

    # ---- picking another one -----------------------------------------------
    before = len(payload_reqs)
    pg.evaluate("() => document.querySelectorAll('#postedList .posted-row .posted-main')[1].click()")
    pg.wait_for_timeout(2500)
    title1 = pg.inner_text("#pTitle")
    check("picking a tile puts that Skribl on the stage",
          title1.strip() != title0.strip(), f"{title0.strip()!r} -> {title1.strip()!r}")
    check("and fetches exactly one more payload",
          len(payload_reqs) == before + 1,
          f"{len(payload_reqs) - before} fetch(es)")

    # ---- search says what it is doing --------------------------------------
    pg.fill("#postedSearch", tag + " alpha")
    # WAIT FOR THE FILTER, do not sleep at it. The grid re-renders on `input`,
    # and a fixed pause raced it: this read 2 tiles on one run and 1 on the next
    # with the same code, which is a flaky assertion rather than a finding.
    try:
        pg.wait_for_function(
            "() => document.querySelectorAll('#postedList .posted-row').length === 1",
            timeout=4000)
    except Exception:
        pass
    filtered = pg.evaluate("() => document.querySelectorAll('#postedList .posted-row').length")
    typed = pg.evaluate("() => document.getElementById('postedSearch').value")
    foot = pg.inner_text("#libFoot")
    check("the search filters the grid", filtered == 1,
          f"{filtered} tiles for {typed!r}")
    # The footer names WHAT is being filtered: "your N" for a browser's list
    # (all of it is on the page), "the N loaded so far" for a host's paged
    # listing. A box that looked like it searched everything would lie.
    check("and says what it is filtering, with the count",
          re.search(r"Filtering (your|the) \d+", foot) is not None,
          f"{foot!r} — the API has no search, so the footer must say what "
          f"population the box filters")
    # The unfiltered footer read "Newest first, from GET /api/skribls." and the
    # bio spoke of "the transport a post does not get". A visitor is not the
    # reader of a route table: no method-plus-path token in the page's visible
    # text, in either footer state. Red on v287.
    pg.fill("#postedSearch", "")
    pg.wait_for_timeout(300)
    _visible = pg.evaluate("() => document.body.innerText")
    check("the library's visible text names no endpoint",
          not re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", _visible),
          (re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/\S*", _visible) or [""])[0]
          if re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", _visible) else "")

    # ---- WHOSE skribls these are (v304) -------------------------------------
    print("\nLIBRARY — a profile is somebody's")
    on_page = pg.evaluate("() => [...document.querySelectorAll('#postedList .posted-row')].map(c => c.getAttribute('data-id'))")
    listed = []
    _cur = None
    for _ in range(50):
        _u = urllib.request.urlopen(BASE + "/api/skribls?limit=100" + (f"&cursor={_cur}" if _cur else ""), timeout=20)
        _body = json.loads(_u.read().decode())
        listed += [i["id"] for i in _body.get("items", [])]
        _cur = _body.get("next_cursor")
        if not _cur:
            break
    check("newest first: the post made last is the first tile", on_page[:1] == [ids[1]], str(on_page))
    check("the unlisted post is on this browser's profile", ids[0] in on_page, str(on_page))
    check("...and NOT in the public listing the gallery reads", ids[0] not in listed)
    check("the ticked post is on the profile and in the listing", ids[1] in on_page and ids[1] in listed)
    check("nothing on the profile is a post this browser did not make",
          set(on_page) <= set(ids), f"extra: {sorted(set(on_page) - set(ids))}")
    pg.evaluate("() => document.querySelector('.posted-row[data-id=\"%s\"] .posted-main').click()" % ids[1])
    pg.wait_for_timeout(1200)
    check("the stage says the ticked one is in the gallery",
          "gallery" in pg.inner_text("#pStats").lower(), pg.inner_text("#pStats"))
    pg.evaluate("() => document.querySelector('.posted-row[data-id=\"%s\"] .posted-main').click()" % ids[0])
    pg.wait_for_timeout(1200)
    check("...and the other is unlisted", pg.inner_text("#pStats").strip() == "unlisted", pg.inner_text("#pStats"))

    # ---- full screen -------------------------------------------------------
    fs_enabled = pg.evaluate("() => !!document.fullscreenEnabled")
    fs_btn = pg.evaluate("() => !document.getElementById('btnFull').hidden")
    check("the full-screen button is shown exactly where the API exists", fs_btn == fs_enabled,
          f"enabled={fs_enabled} shown={fs_btn}")
    if fs_enabled:
        pg.click("#btnFull")
        pg.wait_for_timeout(600)
        fs = pg.evaluate("""() => ({ el: document.fullscreenElement ? document.fullscreenElement.className : null,
            pressed: document.getElementById('btnFull').getAttribute('aria-pressed'),
            exitShown: getComputedStyle(document.getElementById('fullExit')).display !== 'none' })""")
        check("the stage wrap goes full screen, the button says pressed, and the way out is inside",
              fs["el"] == "stageCanvasWrap" and fs["pressed"] == "true" and fs["exitShown"], str(fs))
        pg.click("#fullExit")
        pg.wait_for_timeout(600)
        fs2 = pg.evaluate("""() => ({ el: document.fullscreenElement,
            pressed: document.getElementById('btnFull').getAttribute('aria-pressed'),
            exitShown: getComputedStyle(document.getElementById('fullExit')).display !== 'none' })""")
        check("the in-frame control leaves full screen and the button follows the document",
              fs2["el"] is None and fs2["pressed"] == "false" and not fs2["exitShown"], str(fs2))
    pg.close()

    # ANOTHER BROWSER: a fresh context is a fresh localStorage, and a profile
    # that showed this one's posts to it would be the public listing again.
    other = b.new_page(viewport={"width": 1280, "height": 1000})
    browsing.goto(other, BASE, "/library")
    o_tiles = other.evaluate("() => document.querySelectorAll('#postedList .posted-row').length")
    o_empty = other.evaluate("""() => { const e = document.getElementById('libEmpty');
        return { shown: !e.hidden && getComputedStyle(e).display !== 'none', words: e.innerText }; }""")
    check("another browser sees none of them", o_tiles == 0, f"{o_tiles} tiles")
    check("...and the empty state says what this list is",
          o_empty["shown"] and "in this browser only" in o_empty["words"] and "not an account" in o_empty["words"],
          str(o_empty))
    other.close()

    # A HOST WITH ACCOUNTS: data-skribl-me set means the listing's author
    # filter, and the browser's list is ignored. The attribute is what the
    # server renders from create_blueprint(current_user_id=...) — pinned on
    # the server side below — and here it is stamped onto the body before the
    # page's script runs, so the branch is driven on the real page.
    host = ctx.new_page()
    host.set_viewport_size({"width": 1280, "height": 1000})
    # The page as the server would render it for that user: the attribute the
    # seam below proves the server emits, swapped into the real response so
    # the page's own script takes the host branch.
    def _as_host(route):
        r = route.fetch()
        route.fulfill(response=r, body=r.text().replace('data-skribl-me=""', 'data-skribl-me="host-user-42"', 1))
    host.route(re.compile(r"/library$"), _as_host)
    listing_reqs = []
    host.on("request", lambda r: listing_reqs.append(r.url) if re.search(r"/api/skribls\?", r.url) else None)
    browsing.goto(host, BASE, "/library")
    host.wait_for_timeout(800)
    h_tiles = host.evaluate("() => [...document.querySelectorAll('#postedList .posted-row')].map(c => c.getAttribute('data-id'))")
    check("with a host identity the page asks the listing for that author",
          any("user_id=host-user-42" in u for u in listing_reqs), str(listing_reqs))
    check("...and the browser's own list is not shown",
          not (set(h_tiles) & set(ids)), f"{h_tiles}")
    host.close()
    ctx.close()

    # THE SERVER SIDE OF THE SEAM: the attribute comes from the blueprint's
    # current_user_id, and is empty when there is none.
    from flask import Flask
    import skribl
    for _uid, _want in ((lambda: "u-1", 'data-skribl-me="u-1"'), (None, 'data-skribl-me=""')):
        _a = Flask(__name__)
        _a.config["SECRET_KEY"] = "harness-library"
        _bp = skribl.create_blueprint(session=False, current_user_id=_uid, csrf=False)
        _a.register_blueprint(_bp)
        _html = _a.test_client().get("/library").get_data(as_text=True)
        check(f"/library renders {_want} for current_user_id={'set' if _uid else 'none'}",
              _want in _html)

    # ---- the source gates --------------------------------------------------
    src = (ROOT / "skribl" / "static" / "library.js").read_text(encoding="utf-8")
    check("library.js contains no replay loop of its own",
          "requestAnimationFrame" not in src,
          "the stage is inlineplayer.js; a second rAF loop here would be a "
          "third implementation of playback")
    check("it drives the shared player through the exposed handle",
          "SkriblInline.attach" in src and ".seek(" in src and ".setLoop(" in src)
    # KEYSET, not offset. list_skribls() is explicit about why: OFFSET makes the
    # database walk and discard every skipped row, and a post created mid-scroll
    # shifts every later page.
    # A PARAMETER, not the word. Both of these gates were substring searches
    # first and both passed on their own prose — this file's header names the
    # motifs it replaced, and the paging comment explains why OFFSET is wrong.
    # That is the failure a v273 gate already made once (it searched for
    # "Pillow" and matched a comment mentioning it), so: match the syntax.
    check("paging uses the cursor the server hands back, never an offset",
          "next_cursor" in src and "cursor=" in src and "offset=" not in src)
    # And the DOCS, which described this page as demo tiles for as long as it
    # was one. A page that stops lying while its documentation keeps saying the
    # old thing has moved the lie, not removed it.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    integration = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
    stale = [n for n, t in (("README.md", readme), ("docs/INTEGRATION.md", integration))
             if "demo tiles" in t or "demo drawings" in t
             or "self-contained demo" in t.lower()]
    check("no document still calls /library a page of demo tiles",
          not stale, ", ".join(stale))

    print("\nBRAND — the mark is drawn in the accent on every page that carries it")
    # Owner, v294, from a phone: on /library the skribl mark top-left was
    # BLACK on the dark ground. The mark is one partial stroked with a
    # gradient whose two stops carry .brand-grad-a / .brand-grad-b, and those
    # classes are coloured only in styles.css. The library inlines its own
    # stylesheet (host-independent, CSP-safe) and never carried the two rules,
    # so the stops fell to the SVG default. Keyed by ROUTE: one partial is not
    # one paint. The reference is what `color: var(--accent)` computes to on
    # the same page, read from a probe element, so a page that lacks the token
    # fails the same way a page that lacks the rule does.
    GRAD = """() => { const a = document.querySelector('.brand-grad-a'), b2 = document.querySelector('.brand-grad-b');
      if (!a || !b2) return null;
      const probe = document.createElement('i'); probe.style.color = 'var(--accent)'; document.body.appendChild(probe);
      const probe2 = document.createElement('i'); probe2.style.color = 'var(--accent-2)'; document.body.appendChild(probe2);
      const out = { a: getComputedStyle(a).stopColor, b: getComputedStyle(b2).stopColor,
                    accent: getComputedStyle(probe).color, accent2: getComputedStyle(probe2).color };
      probe.remove(); probe2.remove(); return out; }"""
    for _route in ("/", "/flip", f"/s/{ids[0]}", "/library"):
        _bp = b.new_page(viewport={"width": 390, "height": 844})
        browsing.goto(_bp, BASE, _route)
        _bp.wait_for_timeout(500)
        _g = _bp.evaluate(GRAD)
        check(f"{_route}: the brand mark is on the page", bool(_g),
              "both gradient stops found" if _g else "no .brand-grad-a/.brand-grad-b stops found")
        if _g:
            check(f"{_route}: its gradient runs accent to accent-2, not the SVG default black",
                  _g["a"] == _g["accent"] and _g["b"] == _g["accent2"] and _g["a"] != "rgb(0, 0, 0)",
                  f"stops {_g['a']} -> {_g['b']}; accent {_g['accent']} -> {_g['accent2']}")
        _bp.close()

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
