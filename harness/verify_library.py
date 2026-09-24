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
    # COUNTED, THEN MEASURED: an .every() over an empty list is TRUE, so a page
    # that rendered no pictures at all would answer this the same as one that
    # rendered them all correctly. Two of these went green on nothing for a
    # whole release elsewhere in the harness before anybody noticed.
    _posters = pg.evaluate("""() => {
        const imgs = [...document.querySelectorAll('#postedList .posted-poster')];
        return { n: imgs.length,
                 ok: imgs.every(i => /\\/s\\/[^/]+\\/poster$/.test(i.getAttribute('src'))) }; }""")
    check("every tile's picture is the poster, which is one cached image",
          _posters["n"] == tiles and _posters["ok"],
          f"{_posters} for {tiles} tiles")
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
    # WAITED FOR, not assumed. select() fetches the payload and attaches the
    # player when it arrives, so `players()` is legitimately empty for the
    # instant after the page boots. This read it immediately and passed on
    # timing alone -- until v307's reconcile moved the boot sequence by a few
    # milliseconds and it started reporting `null` for a stage that was about
    # to be perfectly fine. A race that only ever passed is not a check.
    pg.wait_for_function("""() => { const el = document.getElementById('stageBox');
        const p = window.SkriblInline && window.SkriblInline.players()
                   .filter(x => x.el === el)[0];
        return !!(p && p.state().loaded); }""", timeout=15000)
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
    # ONE PROGRESS, NOT TWO (from an iPhone, v304): the in-post player
    # draws a hairline along its bottom edge, and this page has a scrub track
    # of its own under the title. Both moving together read as two players.
    # The macro's progress=false hides the hairline -- hides, because
    # inlineplayer.js requires the element -- and the scrub is the progress.
    _bars = pg.evaluate("""() => { const p = document.querySelector('#stageBox .skribl-inline-prog');
        return { present: !!p, shown: !!p && getComputedStyle(p).display !== 'none',
                 scrub: getComputedStyle(document.getElementById('scrub')).display !== 'none' }; }""")
    check("the stage shows one progress: the scrub track, and the player's hairline is hidden",
          _bars["present"] and not _bars["shown"] and _bars["scrub"], str(_bars))
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
          "gallery" in pg.inner_text("#pVis").lower(), pg.inner_text("#pVis"))
    pg.evaluate("() => document.querySelector('.posted-row[data-id=\"%s\"] .posted-main').click()" % ids[0])
    pg.wait_for_timeout(1200)
    # ONE VOCABULARY. The row, the chip and the stage all say "link only" for
    # an unlisted post; the stage said "unlisted" until the v304 proofread.
    check("...and the other is link only, in the row's own words",
          pg.inner_text("#pVis").strip() == "link only", pg.inner_text("#pVis"))

    # ONE LINE, NOT TWO. The word lived in `.pstats` -- a block built for a
    # social-count row this page never renders -- so it sat alone under the
    # title with 10px of margin over it (owner's screenshot). Asserted as
    # "the same line box as the age", which is what the eye complained
    # about, rather than as "it is inside .prow", which a stray
    # `display: block` on the span would still satisfy.
    _line = pg.evaluate("""() => {
        const v = document.getElementById('pVis'), m = document.getElementById('pMeta');
        const vr = v.getBoundingClientRect(), mr = m.getBoundingClientRect();
        return { top: Math.round(vr.top - mr.top), left: Math.round(vr.left - mr.right),
                 w: Math.round(vr.width), inRow: !!v.closest('.prow'),
                 pstats: document.querySelectorAll('.pstats').length }; }""")
    check("the visibility word shares the meta line with the age",
          _line["w"] > 0 and _line["inRow"] and abs(_line["top"]) <= 1 and _line["left"] > 0,
          f"{_line} \u2014 wanted the same top as #pMeta and a start to its right")
    check("...and nothing is left of the block it used to sit in",
          _line["pstats"] == 0, f"{_line['pstats']} .pstats elements still in the page")

    # WHILE WE WERE IN THAT BLOCK: `.st` next door was unscoped, and the
    # only element on this page carrying that class is the one `<path
    # class="st">` inside the brand mark, which the header includes. So a
    # page stylesheet was setting `display: flex` on a shared component's
    # internal path -- the same shape of bug verify_inline caught on the
    # gallery, found by grepping for who actually uses the class rather
    # than by reading the rule. It is `.card .st` now.
    #
    # Measured on the real path, not on the source: a rule scoped to a
    # container that happens to contain the mark would read as fixed in
    # the stylesheet and still be wrong here.
    _mark_ink = pg.evaluate("""() => {
        const p = document.querySelector('.brand-mark path.st');
        if (!p) return { missing: true };
        const cs = getComputedStyle(p);
        return { display: cs.display, font: cs.fontFamily.indexOf('mono') >= 0 }; }""")
    check("no page rule reaches the brand mark's own path",
          not _mark_ink.get("missing") and _mark_ink["display"] != "flex",
          f"{_mark_ink} \u2014 an unscoped `.st` in this page's sheet matches it")

    # ---- the actions on a row, and the filter (v304) -----------------------
    print("\nLIBRARY — a row can do what the tray could, and more")
    acts = pg.evaluate("""(id) => { const r = document.querySelector('.posted-row[data-id="' + id + '"]');
        return { buttons: [...r.querySelectorAll('.posted-actions button')].map(b => b.className.split(' ')[0]),
                 share: !!r.querySelector('.posted-share'), canShare: !!navigator.share,
                 poster: !!r.querySelector('.posted-poster'),
                 badge: !!r.querySelector('.posted-sub svg'),
                 thumbKind: !!r.querySelector('.posted-thumb svg:not(.posted-sound)'),
                 gallery: (r.querySelector('.posted-gallery') || {}).textContent,
                 pressed: (r.querySelector('.posted-gallery') || {getAttribute: () => null}).getAttribute('aria-pressed') }; }""", ids[0])
    check("a keyed row offers Copy link, the gallery switch, Delete and Copy key",
          {"posted-copy", "posted-gallery", "posted-delete", "posted-key"} <= set(acts["buttons"]), str(acts["buttons"]))
    check("Share is offered exactly where the system has a share sheet", acts["share"] == acts["canShare"],
          f"share button={acts['share']} navigator.share={acts['canShare']}")
    check("the row's picture is the poster, with the kind's icon beside the words",
          acts["poster"] and acts["badge"] and not acts["thumbKind"],
          f"{acts} \u2014 the pen and the book were badges in the poster's corner, "
          f"competing with an 84x63 drawing for the same box; they stand in "
          f"front of the fact they qualify now, and the corner is the sound "
          f"badge's alone")

    # THE TWO BADGES, MEASURED (the speaker is "slightly too small"
    # and should hang off the thumb the way the drawer's 42px tile always
    # has). Three separate properties, because three separate things were
    # wrong and a single "it looks right" would pin none of them:
    #
    #   CLIP      the speaker cannot cross the thumb's corner while
    #             `.posted-thumb` carries `overflow: hidden`, so the pin
    #             here is .posted-shot -- the wrapper that took the clip
    #             off the thumb and left it on the picture, which is the
    #             only part that needs one. The overhang ITSELF is
    #             measured further down, on a row that has sound.
    #   PLACE     the kind is IN THE WORDS and no longer on the poster at
    #             all. It was a badge in the thumb's top-left corner, which
    #             is a reading of a 17px glyph against whatever the drawing
    #             happens to put behind it; in front of "replay" it is part
    #             of the sentence the row already says. Measured as being
    #             LEFT of the words rather than merely present, because a
    #             mark after them qualifies nothing.
    #
    _mark = pg.evaluate("""(id) => {
        const r = document.querySelector('.posted-row[data-id="' + id + '"]');
        const sub = r.querySelector('.posted-sub');
        const kind = sub && sub.querySelector('svg');
        const out = { shot: !!r.querySelector('.posted-shot'), shotClips: false,
                      inSub: !!kind,
                      onThumb: !!r.querySelector('.posted-thumb svg:not(.posted-sound)') };
        const sh = r.querySelector('.posted-shot');
        if (sh) out.shotClips = getComputedStyle(sh).overflow === 'hidden';
        if (kind && sub) {
          const kr = kind.getBoundingClientRect(), sr = sub.getBoundingClientRect();
          out.fromLeft = Math.round(kr.left - sr.left);
          out.width = Math.round(kr.width);
          /* the glyph has to be ON the line, not floating above or below it */
          out.centred = Math.abs((kr.top + kr.bottom) / 2
                               - (sr.top + sr.bottom) / 2) <= 3;
        }
        return out; }""", ids[1])
    check("the kind mark leads the words it qualifies, and is not on the poster",
          _mark.get("inSub") and not _mark.get("onThumb")
          and _mark.get("fromLeft") == 0 and _mark.get("centred"),
          f"{_mark} \u2014 a mark after the words qualifies nothing, and one off "
          f"the line reads as a second row")
    check("the picture carries the clip, not the thumb (.posted-shot)",
          bool(_mark.get("shot")) and bool(_mark.get("shotClips")),
          f"{_mark} \u2014 with the clip back on .posted-thumb the badge below is cut off")

    check("the unlisted post's switch reads link only, unpressed",
          acts["gallery"] == "Link only" and acts["pressed"] == "false", str(acts))

    # THE FILTER: chips narrow to the two states a post of yours can be in.
    pg.click('.chips .chip[data-filter="public"]')
    pg.wait_for_timeout(300)
    shown_pub = pg.evaluate("() => [...document.querySelectorAll('#postedList .posted-row')].map(r => r.getAttribute('data-id'))")
    pg.click('.chips .chip[data-filter="unlisted"]')
    pg.wait_for_timeout(300)
    shown_unl = pg.evaluate("() => [...document.querySelectorAll('#postedList .posted-row')].map(r => r.getAttribute('data-id'))")
    pg.click('.chips .chip[data-filter="all"]')
    pg.wait_for_timeout(300)
    check("'In the gallery' shows the ticked post and not the other", shown_pub == [ids[1]], str(shown_pub))
    check("'Link only' shows the other and not the ticked one", shown_unl == [ids[0]], str(shown_unl))

    # THE GALLERY SWITCH: PATCH visibility with the key, and the record follows.
    patched = []
    pg.on("request", lambda r: patched.append(r.url) if r.method == "PATCH" else None)
    pg.click(f'.posted-row[data-id="{ids[0]}"] .posted-gallery')
    pg.wait_for_timeout(1500)
    after = pg.evaluate("""(id) => { const r = document.querySelector('.posted-row[data-id="' + id + '"]');
        const e = JSON.parse(localStorage.getItem('skribl_posted_v1')).find(x => x.id === id);
        return { text: r.querySelector('.posted-gallery').textContent, pressed: r.querySelector('.posted-gallery').getAttribute('aria-pressed'),
                 stored: e && e.visibility, live: document.getElementById('postedStatus').textContent }; }""", ids[0])
    listed_ids_after = []
    _cur = None
    for _ in range(50):
        _u = urllib.request.urlopen(BASE + "/api/skribls?limit=100" + (f"&cursor={_cur}" if _cur else ""), timeout=20)
        _body = json.loads(_u.read().decode())
        listed_ids_after += [i["id"] for i in _body.get("items", [])]
        _cur = _body.get("next_cursor")
        if not _cur:
            break
    check("the switch PATCHes that post's visibility", any(f"/api/skribls/{ids[0]}" in u for u in patched), str(patched))
    check("...the post is in the public listing now", ids[0] in listed_ids_after)
    check("...the row and the record say in the gallery",
          after["text"] == "In gallery" and after["pressed"] == "true" and after["stored"] == "public" and "gallery" in after["live"].lower(),
          str(after))

    # DELETE, armed then done: the post is gone for everyone, the row with it.
    pg.click(f'.posted-row[data-id="{ids[1]}"] .posted-delete')
    pg.wait_for_timeout(300)
    armed = pg.evaluate("(id) => !!document.querySelector('.posted-row[data-id=\"' + id + '\"]') && "
                        "document.querySelector('.posted-row[data-id=\"' + id + '\"] .posted-delete').classList.contains('armed')", ids[1])
    check("the first tap on Delete arms it and removes nothing", armed)
    pg.click(f'.posted-row[data-id="{ids[1]}"] .posted-delete')
    pg.wait_for_timeout(1500)
    try:
        st_gone = urllib.request.urlopen(BASE + f"/api/skribls/{ids[1]}", timeout=20).status
    except urllib.error.HTTPError as e:
        st_gone = e.code
    check("the second tap deletes it for everyone (404 now) and the row is gone",
          st_gone == 404 and not pg.evaluate("(id) => !!document.querySelector('.posted-row[data-id=\"' + id + '\"]')", ids[1]),
          f"GET {st_gone}")
    ids_left = [ids[0]]

    # ---- a phone: Share on every row, and nothing runs past the edge -------
    # From an iPhone: the page ran over the right margin. The grid's
    # one column was a bare 1fr, whose minimum is its content's minimum, so a
    # row that would not shrink (a title beside its actions) widened the
    # column, the card and the page. minmax(0, 1fr) holds the column at the
    # viewport; and on a phone every row also carries Share, so a row with
    # more than one action wraps them under the title. Measured as the
    # document's scroll width, under mobile emulation with a share sheet.
    # TWO PHONES: one with a share sheet (every row wraps its actions, which
    # is the case a phone shows) and one without (a plain row keeps its one
    # action beside the title, which is the case that widened the column).
    # Both must hold; they are red under different mutations.
    for _vw, _sheet in ((320, True), (360, True), (390, True), (320, False)):
        _mctx = b.new_context(viewport={"width": _vw, "height": 844}, device_scale_factor=2,
                              is_mobile=True, has_touch=True)
        _mp = _mctx.new_page()
        # Headless Chromium has no share sheet even under mobile emulation; a
        # phone does. The module reads navigator.share, so it is given one.
        if _sheet:
            _mp.add_init_script("navigator.share = () => Promise.resolve();")
        browsing.goto(_mp, BASE, "/library")
        _mp.evaluate("""() => { localStorage.setItem('skribl_posted_v1', '[]');
            window.SkriblPosted.add({ id: 'keyedrow', url: '/s/keyedrow', title: 'Y yuh t g cc h b b', kind: 'pad', pages: 1, tok: 'k', visibility: 'public' });
            window.SkriblPosted.add({ id: 'plainrow', url: '/s/plainrow', title: 'Tttt', kind: 'flip', pages: 4 });
            if (window._skriblPostedUI) window._skriblPostedUI.render(); }""")
        _mp.wait_for_timeout(500)
        _m = _mp.evaluate("""() => ({ share: !!navigator.share,
            shares: document.querySelectorAll('#postedList .posted-share').length,
            vw: document.documentElement.clientWidth, sw: document.documentElement.scrollWidth,
            wide: [...document.querySelectorAll('.wrap *')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
                    .slice(0, 3).map(e => e.className) })""")
        _lab = f"at {_vw} on a phone {'with' if _sheet else 'without'} a share sheet"
        check(f"{_lab}: Share is on every row exactly when the system has a sheet",
              _m["share"] == _sheet and _m["shares"] == (2 if _sheet else 0), str(_m))
        check(f"{_lab}: nothing runs past the right edge",
              _m["sw"] <= _m["vw"], f"scrollWidth {_m['sw']} > viewport {_m['vw']}: {_m['wide']}")
        if _sheet:
            # A held column stops the overflow; a row that still did not wrap
            # would pay for it by squeezing its title to nothing. So on a phone
            # with a sheet, a plain row's two actions sit under the title, and
            # the title keeps its room.
            _pr = _mp.evaluate("""() => { const r = document.querySelector('.posted-row[data-id=plainrow]');
                const t = r.querySelector('.posted-main').getBoundingClientRect(), a = r.querySelector('.posted-actions').getBoundingClientRect();
                return { titleW: Math.round(t.width), below: a.top >= t.bottom - 1, actions: r.querySelectorAll('.posted-actions button').length }; }""")
            check(f"{_lab}: a plain row's two actions sit under its title, which keeps its room",
                  _pr["actions"] == 2 and _pr["below"] and _pr["titleW"] >= 120, str(_pr))
        _mctx.close()

    # ---- full screen -------------------------------------------------------
    fs_enabled = pg.evaluate("() => !!document.fullscreenEnabled")
    fs_btn = pg.evaluate("() => !document.getElementById('btnFull').hidden")
    check("the full-screen button is shown exactly where the API exists", fs_btn == fs_enabled,
          f"enabled={fs_enabled} shown={fs_btn}")
    if fs_enabled:
        pg.click("#btnFull")
        pg.wait_for_timeout(600)
        # THE CLASS LIST, NOT THE WHOLE STRING. This compared className to
        # "stageCanvasWrap" exactly, which asserts the absence of every class
        # anything might ever add -- and lib/fullbar.js adds `skfull-host` to
        # whatever it attaches to, so a change about the bar's reserved height
        # reddened a row about which element went full screen.
        fs = pg.evaluate("""() => ({ el: document.fullscreenElement ? document.fullscreenElement.className : null,
            isStage: !!(document.fullscreenElement
                        && document.fullscreenElement.classList.contains('stageCanvasWrap')),
            pressed: document.getElementById('btnFull').getAttribute('aria-pressed'),
            exitShown: getComputedStyle(document.getElementById('fullExit')).display !== 'none' })""")
        check("the stage wrap goes full screen, the button says pressed, and the way out is inside",
              fs["isStage"] and fs["pressed"] == "true" and fs["exitShown"], str(fs))
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
    # ONE EMPTY STATE, NOT TWO. lib/postedui.js renders its own "Nothing
    # posted yet" into the list, and the page renders "Nothing here yet"
    # under it; on the profile both showed, stacked, until the v304
    # proofread. The page owns it here (opts.pageEmpty), so the list renders
    # nothing. Counted as VISIBLE blocks whose text opens with "Nothing", so
    # a second message anywhere on the page fails this rather than only the
    # one that was there.
    o_nothing = other.evaluate("""() => [...document.querySelectorAll('#postedList *, #libEmpty')]
        .filter(el => /^\\s*Nothing/.test(el.textContent) && el.getClientRects().length && getComputedStyle(el).display !== 'none'
                      && !el.querySelector('p, div'))
        .map(el => el.textContent.trim().slice(0, 30))""")
    check("an empty profile says so ONCE", len(o_nothing) == 1 and not other.query_selector("#postedList .posted-empty"),
          str(o_nothing))
    other.close()

    # ---- the header points somewhere (v304 proofread) ---------------------
    print("\nLIBRARY — the header names the page and points at the gallery and the editor")
    hp = ctx.new_page()
    hp.set_viewport_size({"width": 390, "height": 844})
    browsing.goto(hp, BASE, "/library")
    hp.wait_for_timeout(400)
    head = hp.evaluate("""() => { const g = document.getElementById('libGallery'), m = document.getElementById('libMake');
        const h = el => el ? el.getBoundingClientRect().height : 0;
        return { tag: (document.querySelector('.brand .tag') || {}).textContent,
                 label: (document.querySelector('.brand') || {getAttribute: () => null}).getAttribute('aria-label'),
                 gallery: g ? g.getAttribute('href') : null, make: m ? m.getAttribute('href') : null,
                 gh: h(g), mh: h(m), ghost: !!document.querySelector('.top .ghost') }; }""")
    check("the bar says library, not player", head["tag"] == "library" and head["label"] == "Skribl library", str(head))
    check("Gallery and Make one are in the bar, pointing at /gallery and the Pad",
          (head["gallery"] or "").endswith("/gallery") and (head["make"] or "").endswith("/skribl-pad") and not head["ghost"],
          str(head))
    check("...and both answer a tap 44px tall at phone width", head["gh"] >= 44 and head["mh"] >= 44, f"{head['gh']} / {head['mh']}")
    hp.close()

    # ---- an entry from before v304 (v304 proofread; rewritten v307) --------
    # lib/posted.js recorded no visibility until v304, so a legacy entry has
    # none. It used to be ASSUMED unlisted -- the server's default, and a fair
    # guess -- and v307 stopped guessing: the reconcile asks /api/skribls/meta
    # and the row shows what the post actually is. This fixture's post is
    # PUBLIC, so the guess and the truth disagree, which is what makes it worth
    # asserting. What has not changed is the point of the section: a legacy
    # entry still gets the switch. The first cut treated it as unknown and
    # offered nothing.
    print("\nLIBRARY — a browser-kept entry from before v304 gets the switch, and its REAL state")
    legacy = b.new_page(viewport={"width": 1280, "height": 1000})
    browsing.goto(legacy, BASE, "/library")
    legacy.evaluate("""(id) => localStorage.setItem('skribl_posted_v1', JSON.stringify([
        { id: id, url: '/s/' + id, title: 'legacy entry', kind: 'pad', pages: 1, tok: 'legacy-key-abcdefghijklmnopqrstuvwxyz012345', at: Date.now() }]))""", ids[0])
    legacy.reload(wait_until="load")
    legacy.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.library")
    legacy.wait_for_timeout(1200)
    lg = legacy.evaluate("""(id) => { const r = document.querySelector('.posted-row[data-id="' + id + '"]');
        if (!r) return null;
        const g = r.querySelector('.posted-gallery');
        return { sub: r.querySelector('.posted-sub').textContent, gallery: g ? g.textContent : null,
                 pressed: g ? g.getAttribute('aria-pressed') : null, stage: document.getElementById('pVis').textContent.trim() }; }""", ids[0])
    check("the legacy entry gets the switch, reading the post's REAL state",
          bool(lg) and lg["gallery"] == "In gallery" and lg["pressed"] == "true",
          f"{lg} — this post is public; before the reconcile the row assumed "
          f"the server's default and said Link only about a Skribl anyone "
          f"could already find")
    check("...and the row does NOT also say it in words, two inches away",
          bool(lg) and "link only" not in lg["sub"] and "in the gallery" not in lg["sub"],
          f"{lg} — the switch states it and changes it; the meta line saying "
          f"the same thing is the duplication a screenshot showed")
    check("...while the stage, which has no switch, still says it in words",
          bool(lg) and lg["stage"] == "in the gallery",
          f"{lg} — drop it there and nothing on the stage says what the "
          f"Skribl's visibility is")
    legacy.close()

    # ---- THE STAGE DOES NOT STRETCH THE DRAWING (v305) ---------------------
    #
    # The owner, from the profile page: "the image in the player is stretched".
    # It was, by 216% on a 9:16 drawing: the in-post player gave its canvas a
    # definite CSS width AND height, and the box's max-width/max-height then
    # clamped each axis on its own instead of preserving the ratio. The fix is
    # in inlineplayer.css/.js and verify_inline pins it on the feed; this pins
    # it HERE, because the stage is where it was seen and because this page
    # used to carry a rule of its own (.stageCanvasWrap canvas { width: 100% })
    # that would bring the whole thing back on its own. Same surface, different
    # way to lose it -- so it gets its own assertion rather than trusting the
    # feed's.
    print("\nLIBRARY — the stage shows the drawing at its own aspect")
    _shapes = [("9:16", 450, 800), ("4:3", 816, 612)]
    for _label, _cw, _chh in _shapes:
        _sp = ctx.new_page()
        _sp.set_viewport_size({"width": 1280, "height": 1000})
        browsing.goto(_sp, BASE, "/library")
        _mk = _sp.evaluate("""async (cs) => {
            const pts = []; for (let i = 0; i < 40; i++) pts.push({ x: 30 + i * 8,
              y: 30 + i * 14, color: '#e9ecf5', size: 8, t: i * 30, start: i === 0, erase: false });
            const r = await fetch('/api/skribls', { method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ frames: [{ strokes: pts, strokeGroups: [40] }],
                canvasSize: cs, title: 'aspect ' + cs.cssWidth + 'x' + cs.cssHeight }) });
            return await r.json(); }""", {"cssWidth": _cw, "cssHeight": _chh})
        _sp.evaluate("""(e) => localStorage.setItem('skribl_posted_v1', JSON.stringify(
            [{ id: e.id, url: e.url, title: 'aspect', kind: 'pad', pages: 1,
               visibility: 'unlisted', tok: e.deleteToken || null, at: Date.now() }]))""", _mk)
        _sp.reload(wait_until="load")
        _sp.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.library")
        _sp.wait_for_timeout(2500)
        _m = _sp.evaluate("""() => {
            const c = document.querySelector('#stageBox .skribl-inline-canvas');
            if (!c || !c.width) return null;
            const r = c.getBoundingClientRect();
            const box = c.closest('.skribl-inline').getBoundingClientRect();
            return { drawn: c.width / c.height, shown: r.width / r.height,
                     w: Math.round(r.width), h: Math.round(r.height),
                     bw: Math.round(box.width), bh: Math.round(box.height) }; }""")
        _sp.close()
        check(f"the stage shows a {_label} drawing at {_label}, not at the box's shape",
              _m and abs(_m["shown"] - _m["drawn"]) < 0.02,
              f"drawn {_m['drawn']:.3f}, shown {_m['shown']:.3f} "
              f"({_m['w']}x{_m['h']} in a {_m['bw']}x{_m['bh']} box)" if _m else "no canvas on the stage")
        check(f"...and the {_label} drawing fits inside the stage",
              _m and _m["w"] <= _m["bw"] + 1 and _m["h"] <= _m["bh"] + 1,
              f"{_m['w']}x{_m['h']} in {_m['bw']}x{_m['bh']}" if _m else "no canvas on the stage")

    # ---- COPY LINK SAYS WHAT HAPPENED (PRESEAL-002) ------------------------
    #
    # The stage's button ran its "Link copied" handler as BOTH arms of
    # .then(), and again when there was no Clipboard API at all, so a refused
    # copy was reported as a completed one -- the person walks away believing
    # they hold a link they do not. Driven with the clipboard REFUSING and the
    # execCommand fallback returning false, which is the state a locked-down
    # browser or an insecure context actually presents.
    print("\nLIBRARY — Copy link does not claim a copy that did not happen")
    for _case, _stub, _want_ok in (
        # STATEMENTS, NOT AN ARROW FUNCTION. add_init_script evaluates the
        # source; an arrow function is an expression that is never called, so
        # the stub silently does not apply and the real clipboard answers.
        # Caught here by the assertion going red on a tree that was correct.
        ("the clipboard refuses and the fallback fails",
         """Object.defineProperty(navigator, 'clipboard', {
            value: { writeText: function () { return Promise.reject(new Error('denied')); } },
            configurable: true });
          document.execCommand = function () { return false; };""", False),
        ("the clipboard accepts",
         """window.__copied = null;
          Object.defineProperty(navigator, 'clipboard', {
            value: { writeText: function (t) { window.__copied = t; return Promise.resolve(); } },
            configurable: true });""", True)):
        _cp = ctx.new_page()
        _cp.set_viewport_size({"width": 1280, "height": 1000})
        _cp.add_init_script(_stub)
        browsing.goto(_cp, BASE, "/library")
        _cp.wait_for_timeout(2000)
        _cp.click("#btnShare")
        _cp.wait_for_timeout(900)
        # WHEREVER THE WORDS ARE, `title` FIRST. This page runs lib/tooltip.js on
        # a fine pointer, and since v310 the module adopts a title written AFTER
        # load as well as at it -- so this answer is in data-tip here and in
        # `title` on a phone, and for the tick after the write it is in `title`
        # either way. The assertion is about the words.
        _said = _cp.evaluate("""() => ({
            title: (b => b.title || b.getAttribute('data-tip'))(document.getElementById('btnShare')),
            label: document.getElementById('btnShare').getAttribute('aria-label'),
            native: document.getElementById('btnShare').hasAttribute('title'),
            live: (document.getElementById('postedStatus') || {}).textContent || '',
            copied: window.__copied || null })""")
        _cp.close()
        if _want_ok:
            check(f"when {_case}, it says the link is copied — and it really was",
                  "copied" in _said["title"].lower() and bool(_said["copied"]), str(_said))
            # ...IN ONE TOOLTIP. The answer is written to `title`, and this page
            # runs lib/tooltip.js: until v310 that write reinstated the browser's
            # own tooltip under the drawn one and nothing took it away again.
            check("...and it says it once, in the drawn tooltip and not a native one",
                  _said["native"] is False, f"{_said} — both tooltips would show")
        else:
            check(f"when {_case}, it does NOT say the link is copied",
                  "link copied" not in _said["title"].lower()
                  and "link copied" not in _said["label"].lower(), str(_said))
            # ...AND SAYS SO OUT LOUD. A button that silently does nothing is
            # the same dead end from a screen reader's side.
            check("...and the failure reaches the live region",
                  "couldn't copy" in _said["live"].lower(), str(_said))

    # ---- A CONTROL THAT CANNOT ACT IS NOT OFFERED (PRESEAL-005) ------------
    #
    # Play, Restart, Loop and Copy link were enabled from the first paint,
    # before any payload existed, and did nothing when pressed. Loop was the
    # clearest: it toggled its own pressed state, reporting a change it had
    # not made to a player that was not there.
    print("\nLIBRARY — the transport is dead until a Skribl is on the stage")
    _READ = """() => {
        const ids = ['btnPlay', 'btnRestart', 'btnLoop', 'btnShare'];
        const out = {};
        ids.forEach(function (i) { const b = document.getElementById(i); out[i] = b ? !!b.disabled : null; });
        out.scrub = (document.getElementById('scrub') || {}).getAttribute
                    ? document.getElementById('scrub').getAttribute('aria-disabled') : null;
        out.rows = document.querySelectorAll('#postedList .posted-row').length;
        return out; }"""
    # An EMPTY profile: a fresh context is a fresh browser list, which is the
    # state a first-time visitor lands on.
    _empty = b.new_page(viewport={"width": 1280, "height": 1000})
    browsing.goto(_empty, BASE, "/library")
    _empty.wait_for_timeout(1500)
    _st = _empty.evaluate(_READ)
    _empty.close()
    check("with nothing on the stage the transport is disabled",
          _st["rows"] == 0 and all(_st[k] for k in ("btnPlay", "btnRestart", "btnLoop", "btnShare"))
          and _st["scrub"] == "true", str(_st))
    # ...AND COMES ALIVE. Asserting only the disabled half would pass on a
    # transport that is never usable at all.
    _live = ctx.new_page()
    _live.set_viewport_size({"width": 1280, "height": 1000})
    browsing.goto(_live, BASE, "/library")
    _live.wait_for_timeout(2500)
    _st2 = _live.evaluate(_READ)
    _live.close()
    check("...and once a Skribl is loaded it is live",
          _st2["rows"] > 0 and not any(_st2[k] for k in ("btnPlay", "btnRestart", "btnLoop", "btnShare"))
          and _st2["scrub"] == "false", str(_st2))

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
    # A HOST'S PROFILE IS NOT A BROWSER'S LIST (v304 proofread). Two sentences
    # described lib/posted.js on a page that never reads it: the empty state's
    # "kept in this browser only" and the panel's footer about site data and
    # local saves. Both are gone under a host identity; the empty state itself
    # stays, because this author has nothing yet.
    hw = host.evaluate("""() => { const vis = el => !!el && !el.hidden && el.getClientRects().length > 0;
        return { empty: vis(document.getElementById('libEmpty')), local: vis(document.getElementById('libEmptyLocal')),
                 foot: vis(document.querySelector('#postedPanel .posted-foot-top')),
                 words: document.getElementById('libEmpty').innerText }; }""")
    check("an empty host profile shows the empty state without the browser-only sentence",
          hw["empty"] and not hw["local"] and "in this browser only" not in hw["words"], str(hw))
    check("...and the panel's footer about site data and local saves is not shown", not hw["foot"], str(hw))
    host.close()

    # THE HOST'S ROWS SAY ONLY WHAT THE LISTING KNOWS. The listing defers the
    # payload, so a row has no kind (the first cut called every one a
    # "replay" with a pencil on it), and an author's private post is
    # "private", not "link only" -- a private post is not reachable by link.
    # The listing is answered here with the shape GET /api/skribls returns,
    # so the branch is driven without a second host database.
    host2 = ctx.new_page()
    host2.set_viewport_size({"width": 1280, "height": 1000})
    host2.route(re.compile(r"/library$"), _as_host)
    _fake = {"items": [
        {"id": ids[1], "title": "host public", "caption": None, "has_audio": False, "views": 0,
         "user_id": "host-user-42", "visibility": "public", "created_at": "2026-09-20T10:00:00+00:00"},
        {"id": ids[0], "title": "host private", "caption": None, "has_audio": False, "views": 0,
         "user_id": "host-user-42", "visibility": "private", "created_at": "2026-09-20T09:00:00+00:00"}],
        "next_cursor": None}
    host2.route(re.compile(r"/api/skribls\?.*user_id=host-user-42"),
                lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(_fake)))
    browsing.goto(host2, BASE, "/library")
    host2.wait_for_timeout(900)
    hr = host2.evaluate("""(ids) => ids.map(id => { const r = document.querySelector('.posted-row[data-id="' + id + '"]');
        if (!r) return null;
        const g = r.querySelector('.posted-gallery');
        return { sub: r.querySelector('.posted-sub').textContent, badge: !!r.querySelector('.posted-thumb svg'),
                 gallery: g ? g.textContent : null, pressed: g ? g.getAttribute('aria-pressed') : null,
                 del: !!r.querySelector('.posted-delete') }; })""", ids)
    check("a host row does not call itself a replay or wear a kind badge it cannot know",
          all(x and "replay" not in x["sub"] and "page" not in x["sub"] and not x["badge"] for x in hr), str(hr))
    # THE SWITCH SAYS IT, ONCE (v307). These asserted the word in the meta line
    # AND on the button -- which is what the rows carried, and what the owner
    # photographed: "you say LINK ONLY or GALLERY 2 times in each".
    check("the author's private post reads Private on its switch, unpressed",
          hr[0] and hr[0]["gallery"] == "Private" and hr[0]["pressed"] == "false",
          str(hr[0]))
    check("...and the public one reads In gallery, pressed, both with Delete (the host authorises by author)",
          hr[1] and hr[1]["gallery"] == "In gallery" and hr[1]["pressed"] == "true"
          and hr[0]["del"] and hr[1]["del"], str(hr[1]))
    check("...and neither says it twice",
          hr[0] and hr[1]
          and "private" not in hr[0]["sub"] and "link only" not in hr[0]["sub"]
          and "in the gallery" not in hr[1]["sub"],
          f"{hr[0]} / {hr[1]}")
    check("...and no empty state shows over rows", not host2.evaluate("() => { const e = document.getElementById('libEmpty'); return !e.hidden; }"))
    host2.close()
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
    # From a phone: on /library the skribl mark top-left was
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

# ---------------------------------------------------------------------------
# THE ASSET LIST THIS PAGE COPIED BY HAND, and the defect that rode on it.
#
# skribl_library.html does NOT use the skribl_inline_assets() macro -- it lists
# the in-post player's scripts itself. So when lib/photofit.js joined that
# macro, this page silently did not get it, inlineplayer.js took its fallback
# branch, and the profile stage painted a centred COVER over a photo the editor
# and /s/<id> both fitted. Measured before the fix: the stage's canvas showed
# the photo's own left and right edges at 2% and 98% of its width, meaning the
# sides had been cropped away; after, those columns are the background.
#
# READ FROM THE SCRIPT TAGS, NOT FROM PROSE. A substring search for
# "photofit.js" in the template would pass on the COMMENT explaining why it is
# there -- the absence-check trap this repository has hit three times. The
# regex matches the asset call itself, and both halves of the pair are counted
# per template so a page cannot satisfy this by mentioning one of them.
print("\nASSETS — a page that runs the in-post player has what it needs")
_TPL = ROOT / "skribl" / "templates" / "skribl"
_call = lambda name: re.compile(
    r"skribl_asset\(\s*['\"]" + re.escape(name) + r"['\"]\s*\)")
_needs, _missing = [], []
for _t in sorted(_TPL.glob("*.html")):
    _src = _t.read_text(encoding="utf-8")
    if _call("inlineplayer.js").search(_src):
        _needs.append(_t.name)
        if not _call("lib/photofit.js").search(_src):
            _missing.append(_t.name)
check("every template that loads inlineplayer.js also loads lib/photofit.js",
      _needs and not _missing,
      f"loads the player: {_needs}; missing the geometry: {_missing or 'none'} "
      f"— without it the player falls back to a centred cover and crops a "
      f"photo its author fitted")

# ---------------------------------------------------------------------------
# THE STAGE'S FULL SCREEN RULE CARRIES A COPY OF THE BOX'S ASPECT RATIO.
#
# skribl_library.html sizes the fullscreened player with
# `width: min(100vw, calc(100vh * 16 / 9))`, and 16/9 there is not a property
# of the drawing -- it is .skribl-inline's own `aspect-ratio`, hard-coded in
# inlineplayer.css because 16:9 is the widest canvas lib/canvassizes.js offers
# and everything narrower letterboxes inside it. The comment beside that rule
# used to claim the player "sets it from the payload", which would have made
# the copy harmless; it does not, so the two numbers have to agree or the
# fullscreen box stops matching the player inside it.
#
# BOTH READ FROM THE DECLARATIONS, never from the prose around them: one from
# the `aspect-ratio` property, one from inside the calc().
print("\nFULL SCREEN — the stage's box matches the player's own ratio")
_css = (ROOT / "skribl" / "static" / "inlineplayer.css").read_text(encoding="utf-8")
_lib = (ROOT / "skribl" / "templates" / "skribl"
        / "skribl_library.html").read_text(encoding="utf-8")
_box = re.search(r"aspect-ratio:\s*(\d+)\s*/\s*(\d+)", _css)
_stage = re.search(r"calc\(\s*100vh\s*\*\s*(\d+)\s*/\s*(\d+)\s*\)", _lib)
check("both ratios were actually found, not defaulted",
      bool(_box) and bool(_stage),
      f"inlineplayer.css: {_box.groups() if _box else 'NOT FOUND'}; "
      f"skribl_library.html: {_stage.groups() if _stage else 'NOT FOUND'} — a "
      f"regex that matches nothing compares nothing and passes")
check("the stage's fullscreen width uses the player box's own aspect ratio",
      bool(_box) and bool(_stage) and _box.groups() == _stage.groups(),
      f"player box {_box.group(1) if _box else '?'}:{_box.group(2) if _box else '?'} "
      f"against stage rule {_stage.group(1) if _stage else '?'}:"
      f"{_stage.group(2) if _stage else '?'} — a fullscreen box of one shape "
      f"around a player of another puts ground where the drawing should be")


# ---------------------------------------------------------------------------
print("\nLIBRARY — the stage says SILENT only when it KNOWS the Skribl is silent")
# THE BUG (from /library): a Skribl WITH music was labelled SILENT.
# `lib/posted.js` stored no audio flag at all, so every browser-kept row read
# `has_audio` as undefined, and `library.js` rendered `e.has_audio ? 'with
# sound' : 'silent'` — which turns "nobody said" into a claim of silence.
#
# THREE STATES, and this drives all three, because a two-state assertion is
# what shipped the defect. The value now comes from the SERVER's own reading of
# the payload (the create response's hasAudio, the same field feed_dict
# reports), so a row and a listing cannot disagree about one post.
# THE VALUE COMES FROM THE SERVER, AND A MUTATION SAID SO. The rows below seed
# the store directly, which pins the client's three states and pins NOTHING
# about where the truth comes from: deleting `body["hasAudio"]` from the create
# response left every one of them green. So the response is asserted on its own
# terms, through a real post, one with audio bytes and one without.
_WAV = ("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAA"
        "ZGF0YQAAAAA=")


def _post_sound(title, music):
    _frame = {"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0, "start": True},
                          {"x": 200, "y": 150, "color": "#fff", "size": 6, "t": 120}],
              "strokeGroups": [2], "background": {"color": "#101418"}}
    if music:
        _frame["music"] = {"data": _WAV, "name": "a.wav"}
    _body = {"title": title, "version": 2, "schemaVersion": 2, "playbackMode": "replay",
             "canvasSize": {"cssWidth": 800, "cssHeight": 600}, "frames": [_frame]}
    _rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(_rq, timeout=20) as _r:
        return json.loads(_r.read().decode())


_withsnd = _post_sound("sound: yes", True)
_nosnd = _post_sound("sound: no", False)
check("the create response says a post WITH audio bytes has sound",
      _withsnd.get("hasAudio") is True,
      f"hasAudio={_withsnd.get('hasAudio')!r} — the client has no other way to "
      f"know, and guessing is what put SILENT on a Skribl with music")
check("...and says a post WITHOUT them does not",
      _nosnd.get("hasAudio") is False,
      f"hasAudio={_nosnd.get('hasAudio')!r} — a response that always says True "
      f"would pass the row above and be just as wrong")

with sync_playwright() as _sp3:
    _b3 = _sp3.chromium.launch()
    _c3 = _b3.new_context()
    _p3 = _c3.new_page()
    _p3.set_viewport_size({"width": 1280, "height": 1000})
    browsing.goto(_p3, BASE, "/library")
    _p3.evaluate("""() => { localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'sndYes', url: '/s/sndYes', title: 'Has music',
          kind: 'pad', pages: 1, tok: 'k', visibility: 'public', has_audio: true });
        window.SkriblPosted.add({ id: 'sndNo', url: '/s/sndNo', title: 'No music',
          kind: 'pad', pages: 1, tok: 'k', visibility: 'unlisted', has_audio: false });
        window.SkriblPosted.add({ id: 'sndUnk', url: '/s/sndUnk', title: 'Never said',
          kind: 'pad', pages: 1, tok: 'k', visibility: 'unlisted' }); }""")
    _p3.reload(wait_until="load")
    _p3.wait_for_timeout(1500)
    # THE STORE KEEPS THE THIRD STATE. `!!entry.has_audio` at either end
    # collapses "no" and "nobody said" into one false, which is the defect.
    _kept = _p3.evaluate("() => { const m = {}; "
                         "window.SkriblPosted.list().forEach(e => { m[e.id] = e.has_audio; }); "
                         "return m; }")
    check("the store keeps sound as three states, not two",
          _kept.get("sndYes") is True and _kept.get("sndNo") is False
          and _kept.get("sndUnk") is None,
          f"stored {_kept} — null is 'nobody said' and must not become false")
    for _id, _title, _want in (("sndYes", "Has music", "with sound"),
                               ("sndNo", "No music", "silent"),
                               ("sndUnk", "Never said", "")):
        _p3.evaluate("""(t) => [...document.querySelectorAll('.posted-title')]
            .find(e => e.textContent === t).closest('.posted-main').click()""", _title)
        _p3.wait_for_timeout(700)
        _said = _p3.evaluate("() => (document.getElementById('pKind') || {}).textContent")
        check(f"the stage says {_want or '(nothing)'!r} for a Skribl whose sound is "
              + {"with sound": "known to be there", "silent": "known to be absent"}
                .get(_want, "UNKNOWN"),
              (_said or "").strip() == _want,
              f"said {(_said or '').strip()!r}, wanted {_want!r}")
    # AND THE BADGE FOLLOWS THE SAME RULE. A note on a row whose sound is
    # unknown would be the same lie in a different corner.
    _badges = _p3.evaluate("""() => { const m = {};
        document.querySelectorAll('.posted-row').forEach(r => {
          m[r.getAttribute('data-id')] = !!r.querySelector('.posted-sound'); });
        return m; }""")
    check("the sound badge is drawn on the known-yes row and on neither other",
          _badges.get("sndYes") is True and _badges.get("sndNo") is False
          and _badges.get("sndUnk") is False,
          f"badges {_badges}")
    # AND IT HANGS OFF THE CORNER, WHICH IS READ BY PAINTING AND NOT BY
    # ARITHMETIC. A rect says where the box WOULD be and says nothing
    # about the ancestor clipping it -- which is exactly the defect, since
    # the badge's rect was already outside the thumb while `overflow:
    # hidden` on `.posted-thumb` cut it off. So the assertion probes a
    # point OUTSIDE the thumb and inside the badge's circle and asks the
    # document what is painted there.
    _over = _p3.evaluate("""() => {
        const r = document.querySelector('.posted-row[data-id="sndYes"]');
        const th = r.querySelector('.posted-thumb');
        const snd = r.querySelector('.posted-thumb svg.posted-sound');
        if (!th || !snd) return { missing: true };
        const tr = th.getBoundingClientRect(), sr = snd.getBoundingClientRect();
        const el = document.elementFromPoint(tr.right + 3, tr.top - 3);
        return { w: Math.round(sr.width),
                 outRight: Math.round(sr.right - tr.right),
                 outTop: Math.round(tr.top - sr.top),
                 hit: !!(el && (el === snd || (el.closest && el.closest('svg.posted-sound')))),
                 hitWas: el ? (el.tagName + '.' + (el.getAttribute('class') || '')) : null }; }""")
    # AND IT IS THE PRODUCT'S OWN COLOUR. `#7ee2a8` was the only green
    # anywhere in this tree, so the one badge left on the poster read as a
    # status light -- something reporting health -- rather than as a property
    # of the Skribl ("leave speaker, but make it a different color
    # (purple maybe?)"). Compared against the RESOLVED accent rather than a
    # literal, so the row survives the palette moving and still fails a
    # hard-coded colour that merely happens to match it today.
    _sndc = _p3.evaluate("""() => {
        const s = document.querySelector(".posted-thumb svg.posted-sound");
        if (!s) return { missing: true };
        const probe = document.createElement("span");
        probe.style.color = "var(--accent)";
        document.body.appendChild(probe);
        const want = getComputedStyle(probe).color;
        probe.remove();
        return { got: getComputedStyle(s).color, want: want }; }""")
    check("...and is drawn in the accent, not in the one green",
          not _sndc.get("missing") and _sndc["got"] == _sndc["want"],
          f"{_sndc} \u2014 a green pip beside a drawing is a status light, and "
          f"having sound is not a state of health")

    check("the sound badge is bigger than the kind badge it used to match",
          not _over.get("missing") and _over["w"] >= 20,
          f"{_over} \u2014 wanted 20px or more; it was 18, the kind badge's size")
    check("...and it hangs off the thumb's corner, and is PAINTED there",
          not _over.get("missing") and _over["outRight"] > 0 and _over["outTop"] > 0
          and _over["hit"] is True,
          f"{_over} \u2014 a rect outside the thumb with nothing painted in it "
          f"is a badge an ancestor is still clipping")
    _p3.close()
    _b3.close()


# ---------------------------------------------------------------------------
print("\nLIBRARY — deleting a local save is reversible, and the page says what its controls cost")
# THE GAP : "is there a way to put the row back after you've taken it
# down? how would you ever see it again?" There was not.
#
# IT WAS ASKED ABOUT THE POSTED ROW'S x, which v311 removed outright — the
# owner's answer to four releases of making that control safe. The shelf it
# produced did not go with it, because the removal it now covers is the worse
# one: a LOCAL save exists nowhere but this browser, so its x destroys the only
# copy of a drawing and no server can be asked again. Same shelf, same twelve
# seconds, driven here through the control that still exists.
#
# THE INDEX IS THE ASSERTION, not just the presence. `add()` unshifts and
# stamps a fresh timestamp, so undoing with it would move the row to the top of
# the list and relabel a drawing from last week as saved just now. This removes
# the MIDDLE of three and requires the middle back, with its own date.
with sync_playwright() as _sp4:
    _b4 = _sp4.chromium.launch()
    _p4 = _b4.new_context().new_page()
    _p4.set_viewport_size({"width": 1280, "height": 1000})
    browsing.goto(_p4, BASE, "/library")
    _p4.evaluate("""() => { localStorage.setItem('skribl_posted_v1', '[]');
        for (const id of ['u1', 'u2', 'u3']) localStorage.setItem('skribl_post_' + id, '{"frames":[]}');
        window.SkriblPosted.add({ id: 'u3', url: '/p#skribl=u3', title: 'Third', kind: 'pad', pages: 1, local: true });
        window.SkriblPosted.add({ id: 'u2', url: '/p#skribl=u2', title: 'Second', kind: 'flip', pages: 4, local: true });
        window.SkriblPosted.add({ id: 'u1', url: '/p#skribl=u1', title: 'First', kind: 'pad', pages: 1, local: true }); }""")
    _p4.reload(wait_until="load")
    _p4.wait_for_timeout(1200)
    _ids = lambda: _p4.evaluate("() => window.SkriblPosted.list().map(e => e.id).join(',')")
    check("three rows, u2 in the middle (fixture)", _ids() == "u1,u2,u3", _ids())
    _was = _p4.evaluate("() => (window.SkriblPosted.list().find(e => e.id === 'u2') || {}).at")
    # Armed, so two taps -- the warning stays, because arming stops the tap you
    # did not mean and undo returns the one you meant and regretted.
    _p4.evaluate("""() => { const b = [...document.querySelectorAll('.posted-row')]
        .find(r => r.getAttribute('data-id') === 'u2').querySelector('.posted-del');
        b.click(); b.click(); }""")
    _p4.wait_for_timeout(400)
    check("the x removes the row", _ids() == "u1,u3", _ids())
    _shelf = _p4.evaluate("""() => { const u = document.getElementById('postedUndo');
        return { shown: !!u && !u.hidden,
                 msg: (document.getElementById('postedUndoMsg') || {}).textContent || '' }; }""")
    check("...and an undo shelf appears saying what happened",
          _shelf["shown"] and "Deleted" in _shelf["msg"],
          f"{_shelf} — an undo nobody can see is a shortcut for people who "
          f"already know it is there")
    _p4.click("#postedUndoBtn")
    _p4.wait_for_timeout(400)
    check("Undo puts it back WHERE IT WAS, not at the top",
          _ids() == "u1,u2,u3",
          f"{_ids()} — add() would have made this u2,u1,u3")
    check("...with the date it was carrying, not a fresh one",
          _p4.evaluate("() => (window.SkriblPosted.list().find(e => e.id === 'u2') || {}).at") == _was,
          "add() restamps; a row put back as 'just now' is a row that lies "
          "about when the drawing was made")
    check("...and the shelf goes away",
          _p4.evaluate("() => document.getElementById('postedUndo').hidden"),
          "a shelf offering to undo something already undone")
    # THE BLOB SURVIVES THE WINDOW. A local save's bytes live under
    # 'skribl_post_<id>'; dropping them at removal time would make undo restore
    # a row whose link opens nothing.
    _p4.evaluate("""() => { localStorage.setItem('skribl_posted_v1', '[]');
        localStorage.setItem('skribl_post_loc1', '{"frames":[]}');
        window.SkriblPosted.add({ id: 'loc1', url: '/x#skribl=loc1', title: 'On this device',
                                  kind: 'pad', pages: 1, local: true }); }""")
    _p4.reload(wait_until="load")
    _p4.wait_for_timeout(1000)
    _p4.evaluate("""() => { const b = document.querySelector('.posted-row .posted-del');
        b.click(); b.click(); }""")
    _p4.wait_for_timeout(400)
    check("a local save's BYTES are kept while its undo is offered",
          _p4.evaluate("() => localStorage.getItem('skribl_post_loc1') !== null"),
          "undo would restore a row whose link opens nothing")
    _p4.click("#postedUndoBtn")
    _p4.wait_for_timeout(400)
    check("...and undo brings back the row and the bytes together",
          _p4.evaluate("() => window.SkriblPosted.list().length") == 1
          and _p4.evaluate("() => localStorage.getItem('skribl_post_loc1') !== null"),
          "the entry is back but the payload is gone")

    # THE ROW'S PICTURE IS THE DRAWING, NOT THE CARD (v311). The poster is the
    # 1200x630 share card; the stylesheet framed it at 128% and pulled it up so
    # the wordmark band fell outside the box, which hides the branding and
    # shows whatever the card had in the middle. On an 84x63 tile that made a
    # 16:9 Skribl a stamp between two slabs of plate — the state the owner was
    # looking at when they asked whether the page looked right.
    #
    # ASSERTED AS A COVERING, which is what "cropped to the drawing" MEANS and
    # is a question geometry can answer honestly: map the drawing's rectangle
    # (lib/sharecard.js drawingRect, in card pixels) through wherever the image
    # actually landed, and require it to reach every edge of the thumb. A
    # letterboxed tile fails on the axis the bands are on. And require it not
    # to overshoot on BOTH axes: a cover is the smallest scale that reaches,
    # so one axis has to land flush, and a check that only asked "does it
    # reach" would pass on an image blown up to any size at all.
    #
    # THE FIXTURE IS 9:16 AND THAT IS THE WHOLE CALIBRATION. The band crop
    # scales the card so its 492px drawing BAND fills the thumb's height and
    # centres it, which for a drawing at least as wide as the thumb (4:3 and
    # 16:9, two of the four presets) lands on exactly the same pixels the new
    # crop does -- both rows below pass on the OLD code with either of those.
    # The two that do not are `square` and `tall`: a 9:16 Skribl came out 35px
    # wide in an 84px box with 24px of plate down each side. Written against a
    # 16:9 fixture first, all four rows here went green on the band crop, which
    # is the vacuous pass CLAUDE.md says to go looking for before believing an
    # instrument.
    _p4.evaluate("""() => { localStorage.setItem('skribl_posted_v1', '[]');
        window.SkriblPosted.add({ id: 'wide1', url: '/s/wide1', title: 'Tall', kind: 'pad', pages: 1 });
        window.SkriblPosted.add({ id: 'noshape', url: '/s/noshape', title: 'Unknown shape', kind: 'pad', pages: 1 });
        window.SkriblPosted.update('wide1', { canvas_w: 531, canvas_h: 944 }); }""")
    _p4.reload(wait_until="load")
    _p4.wait_for_timeout(1400)
    _crop = _p4.evaluate("""() => {
        const CARD_W = 1200, CARD_H = 630, AREA_W = 1092, AREA_H = 492, FOOT = 84;
        const out = {};
        for (const id of ['wide1', 'noshape']) {
          const r = document.querySelector('.posted-row[data-id="' + id + '"]');
          const shot = r && r.querySelector('.posted-shot');
          const img = r && r.querySelector('.posted-poster');
          if (!shot || !img) { out[id] = null; continue; }
          const sb = shot.getBoundingClientRect(), ib = img.getBoundingClientRect();
          const w = +shot.getAttribute('data-skribl-w'), h = +shot.getAttribute('data-skribl-h');
          const e = { shaped: !!(w > 0 && h > 0), inline: img.style.width !== '',
                      boxW: Math.round(sb.width), boxH: Math.round(sb.height) };
          if (e.shaped) {
            const sc = Math.min(AREA_W / w, AREA_H / h);
            const dw = Math.round(w * sc), dh = Math.round(h * sc);
            const dx = Math.round((CARD_W - dw) / 2), dy = Math.round((CARD_H - FOOT - dh) / 2);
            const L = ib.left + ib.width * dx / CARD_W, R = ib.left + ib.width * (dx + dw) / CARD_W;
            const T = ib.top + ib.height * dy / CARD_H,  B = ib.top + ib.height * (dy + dh) / CARD_H;
            e.coversX = L <= sb.left + 0.5 && R >= sb.right - 0.5;
            e.coversY = T <= sb.top + 0.5 && B >= sb.bottom - 0.5;
            e.slackX = +(R - L - sb.width).toFixed(1);
            e.slackY = +(B - T - sb.height).toFixed(1);
          }
          out[id] = e; }
        return out; }""")
    _wide, _none = _crop.get("wide1"), _crop.get("noshape")
    check("a row that knows its drawing's shape says so on the picture's wrapper",
          bool(_wide) and _wide["shaped"] and _wide["inline"],
          f"{_crop} — without data-skribl-w/h on .posted-shot, library.js has "
          f"nothing to crop with and the band crop stands")
    check("...and the drawing covers the thumbnail on both axes",
          bool(_wide) and _wide.get("coversX") and _wide.get("coversY"),
          f"{_wide} — a False here is the letterbox: the drawing does not "
          f"reach one pair of edges, so what does is plate")
    check("...at the smallest scale that reaches, so one axis lands flush",
          bool(_wide) and min(abs(_wide.get("slackX", 99)),
                              abs(_wide.get("slackY", 99))) < 1.5,
          f"slack {_wide} — both axes overshooting means the picture was "
          f"simply enlarged, not fitted")
    check("...and a row whose shape nothing has said keeps the band crop",
          bool(_none) and not _none["shaped"] and not _none["inline"],
          f"{_none} — fitShots must leave an unshaped row's picture alone "
          f"rather than crop it to a guess")

    # TOOLTIPS, which this page had none of . Asserted on data-tip
    # rather than on `title`, because the module REMOVES the title -- so a page
    # that loaded the sheet and not the module would still have titles and
    # would fail this, which is the point.
    _tips = _p4.evaluate("""() => ({
        started: !!window.SkriblTooltip,
        chips: [...document.querySelectorAll('.chip')].every(b => !!b.getAttribute('data-tip')),
        foot: ['postedRecover', 'postedClear']
                .every(id => !!(document.getElementById(id) || {}).getAttribute
                             && !!document.getElementById(id).getAttribute('data-tip')),
        leftovers: document.querySelectorAll('.chip[title], #postedRecover[title], #postedClear[title]').length })""")
    check("the profile draws tooltips: every filter chip and both foot buttons carry one",
          _tips["started"] and _tips["chips"] and _tips["foot"], str(_tips))
    check("...and the native title is gone, so the browser's own does not stack under it",
          _tips["leftovers"] == 0,
          f"{_tips['leftovers']} controls still carry a title attribute")
    _p4.close()
    _b4.close()


# ---------------------------------------------------------------------------
print("\nLIBRARY — the browser's own rows are backfilled, and the row says each thing once")
# WHAT THE PAGE SHOWED: a library with no pen, no book and no sound note on
# anything they had actually posted. Rendering was right and the DATA was old --
# `kind`, `pages` and `has_audio` were each added after posts were already being
# made, so every row this browser wrote before them reads undefined, and a
# client that renders an unknown honestly shows nothing. The migration
# backfilled the database; this is the browser's half.
_WAVB = ("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAAC"
         "ABAAZGF0YQAAAAA=")


def _mkpost(title, mode, n, music, vis):
    _fr = []
    for _i in range(n):
        _f = {"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0},
                          {"x": 200, "y": 150, "color": "#fff", "size": 6, "t": 99}],
              "strokeGroups": [2]}
        if music and _i == 0:
            _f["music"] = {"data": _WAVB, "name": "a.wav"}
        _fr.append(_f)
    _b = {"title": title, "version": 2, "schemaVersion": 2, "visibility": vis,
          "canvasSize": {"cssWidth": 800, "cssHeight": 600}, "frames": _fr}
    if mode:
        _b["playbackMode"] = mode
    _rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_b).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(_rq, timeout=20) as _r:
        return json.loads(_r.read().decode())["id"]


_oldsnd = _mkpost("old, with music", "replay", 1, True, "unlisted")
_oldflip = _mkpost("old flip", "flip", 6, False, "unlisted")

# An entry shaped the way a pre-v307 one is: the three fields simply absent.
_STRIP = """(ids) => { localStorage.setItem('skribl_posted_v1', '[]');
    ids.forEach(function (id, i) {
      window.SkriblPosted.add({ id: id, url: '/s/' + id, title: 'Row ' + i, tok: 'k' + i });
    });
    var l = JSON.parse(localStorage.getItem('skribl_posted_v1'));
    l.forEach(function (x) { delete x.kind; delete x.pages; delete x.has_audio;
                             delete x.visibility; });
    localStorage.setItem('skribl_posted_v1', JSON.stringify(l)); }"""

with sync_playwright() as _sp5:
    _b5 = _sp5.chromium.launch()
    _p5 = _b5.new_context().new_page()
    _p5.set_viewport_size({"width": 1280, "height": 1000})
    browsing.goto(_p5, BASE, "/library")
    _p5.wait_for_timeout(400)
    _p5.evaluate(_STRIP, [_oldsnd, _oldflip])
    _pre = _p5.evaluate("() => window.SkriblPosted.list()"
                        ".map(e => [e.kind, e.pages, e.has_audio]) ")
    check("the fixture really is a pre-backfill list (all three fields absent)",
          all(v is None for row in _pre for v in row),
          f"{_pre} — if the fixture already carried them, every row below "
          f"would pass without the reconcile doing anything")
    _p5.reload(wait_until="load")
    _p5.wait_for_timeout(2500)
    _post = _p5.evaluate("() => { const m = {}; window.SkriblPosted.list()"
                         ".forEach(e => { m[e.id] = [e.kind, e.pages, e.has_audio]; }); return m; }")
    check("the reconcile fills in what the server knows",
          _post.get(_oldsnd) == ["pad", 1, True]
          and _post.get(_oldflip) == ["flip", 6, False],
          f"{_post} — these rows are what the owner's library was full of")
    _seen = _p5.evaluate("""() => { const m = {};
        document.querySelectorAll('.posted-row').forEach(r => {
          m[r.getAttribute('data-id')] = {
            sub: (r.querySelector('.posted-sub') || {}).textContent || '',
            snd: !!r.querySelector('.posted-sound') }; });
        return m; }""")
    check("...so the row finally says what it is",
          "replay" in _seen.get(_oldsnd, {}).get("sub", "")
          and "6 pages" in _seen.get(_oldflip, {}).get("sub", ""),
          str(_seen))
    check("...and the sound badge appears on the one with music, and only that one",
          _seen.get(_oldsnd, {}).get("snd") is True
          and _seen.get(_oldflip, {}).get("snd") is False,
          str(_seen))

    # THE EMPTY PILL. Blanking the text left the pill's border and padding on
    # screen -- a ghost under the title with nothing in it (owner's screenshot).
    _p5.evaluate("""(id) => [...document.querySelectorAll('.posted-row')]
        .find(r => r.getAttribute('data-id') === id)
        .querySelector('.posted-main').click()""", _oldsnd)
    _p5.wait_for_timeout(600)
    check("a known sound shows the pill", 
          not _p5.evaluate("() => document.getElementById('pKind').hidden")
          and _p5.evaluate("() => document.getElementById('pKind').textContent") == "with sound",
          _p5.evaluate("() => document.getElementById('pKind').textContent"))
    # STILL UNKNOWN AFTER THE RECONCILE, which is the case that keeps this
    # reachable: a row whose post the server does not have — deleted, or from
    # another deployment. The reconcile asks and gets nothing back, so the
    # field stays unknown and the stage must still not draw a bordered box
    # with nothing in it. (A local save is the other such row and cannot be
    # used here: its title NAVIGATES rather than selecting.)
    _p5.evaluate("""() => { localStorage.setItem('skribl_posted_v1', JSON.stringify(
        [{ id: 'gonefromsrv', url: '/s/gonefromsrv', title: 'No longer there',
           kind: 'pad', pages: 1, at: Date.now() }])); }""")
    _p5.reload(wait_until="load")
    _p5.wait_for_timeout(2000)
    _p5.evaluate("() => document.querySelector('.posted-row .posted-main').click()")
    _p5.wait_for_timeout(500)
    _ghost = _p5.evaluate("""() => { const k = document.getElementById('pKind');
        const r = k.getBoundingClientRect();
        return { hidden: k.hidden, text: k.textContent, w: Math.round(r.width),
                 h: Math.round(r.height) }; }""")
    check("an UNKNOWN sound shows no pill at all — not an empty one",
          _ghost["hidden"] and _ghost["w"] == 0 and _ghost["h"] == 0,
          f"{_ghost} — a local save has no server post to ask, so this is still "
          f"reachable after the reconcile, and a bordered box with nothing in "
          f"it is what a screenshot showed")
    _p5.close()
    _b5.close()

# ---------------------------------------------------------------------------
# FULL SIZE ON A PHONE (v308) -- the stage's half of the same fix.
#
# The gallery's tile and this page's stage are one product to the person using
# them, and they were both hidden on the same device for the same reason: iOS
# Safari has a Fullscreen API for `<video>` and nothing else, so
# `document.fullscreenEnabled` is false and both pages correctly hid a control
# that could not work. The init script takes the API away here too -- it is the
# only way to reach the phone's path from a browser that has one.
#
# THE TWO SURFACES ARE ASSERTED SEPARATELY AND DIFFERENTLY, per the standing
# rule: a shared fix does not mean a shared assertion. The gallery's stage is
# built per tile in JS and its exit control had to be CREATED; this one is in
# the template and already existed, so what is in doubt here is whether the
# control is OFFERED at all -- it used to be `hidden` outright on a phone.
print("\nLIBRARY — full size on a browser with no Fullscreen API")
with sync_playwright() as _spf:
    _bf = _spf.chromium.launch()
    _pf = _bf.new_context().new_page()
    _pf.set_viewport_size({"width": 390, "height": 844})
    _pf.add_init_script("""
      try { Object.defineProperty(document, 'fullscreenEnabled',
        { configurable: true, get: function () { return false; } }); } catch (e) {}
      try { Object.defineProperty(document, 'webkitFullscreenEnabled',
        { configurable: true, get: function () { return false; } }); } catch (e) {}
      try { delete Element.prototype.requestFullscreen; } catch (e) {}
      try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {}
    """)
    browsing.goto(_pf, BASE, "/library")
    _pf.wait_for_timeout(1800)
    _off = _pf.evaluate("""() => ({
        api: !!(document.fullscreenEnabled || document.webkitFullscreenEnabled),
        offered: !document.getElementById('btnFull').hidden })""")
    check("the simulation is real: the profile believes it has no Fullscreen API",
          _off["api"] is False,
          f"{_off} \u2014 with the API present this row tests the path that worked")
    check("...and the stage still OFFERS full size",
          _off["offered"] is True,
          f"{_off} \u2014 this control was `hidden` on a phone, which is the "
          f"owner's 'i am not seeing full screen on gallery or library on iphone'")

    _pf.evaluate("() => document.getElementById('btnFull').click()")
    _pf.wait_for_timeout(700)
    _big = _pf.evaluate("""() => {
        const w = document.querySelector('.stageCanvasWrap');
        const r = w.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height),
                 vw: window.innerWidth, vh: window.innerHeight,
                 left: Math.round(r.left), top: Math.round(r.top),
                 pinned: getComputedStyle(w).position,
                 locked: getComputedStyle(document.documentElement).overflow,
                 exit: getComputedStyle(document.getElementById('fullExit')).display,
                 pressed: document.getElementById('btnFull').getAttribute('aria-pressed') }; }""")
    # AGAINST THE VIEWPORT, not against the class: `position: fixed` resolves
    # against the nearest transformed, filtered or contained ancestor rather
    # than the viewport, and this stage sits inside a `position: sticky` panel
    # with `overflow: hidden` -- neither of which should trap it, which is
    # exactly the kind of "should" worth measuring.
    check("pressing it puts the stage over the whole viewport",
          _big["pinned"] == "fixed" and _big["left"] == 0 and _big["top"] == 0
          and abs(_big["w"] - _big["vw"]) <= 1 and abs(_big["h"] - _big["vh"]) <= 2,
          f"{_big} \u2014 the sticky panel around this one has `overflow: hidden`, "
          f"and a fixed child escaping it is the thing under test")
    check("...with the way out on screen and the control saying where it is",
          _big["exit"] == "grid" and _big["pressed"] == "true", str(_big))
    check("...and the page behind it cannot scroll",
          _big["locked"] == "hidden", str(_big))

    # ---- THE SAME BAR THE GALLERY'S TILE GETS (v308) ----------------------
    # Owner, holding a screenshot of each: this page's full screen had a way
    # out and no controls, the gallery's had controls and no way out, and
    # neither looked like the other. "In the end the two full screens should
    # look identical with controls present on the bottom."
    #
    # THE LIST IS SPELLED OUT AND IT IS THE SAME LITERAL verify_gallery USES.
    # That is the point: a change to lib/fullbar.js reddens both suites
    # together, and a change to one PAGE reddens only that one. A count, or
    # each suite asserting "whatever this page renders", could not tell those
    # two apart -- and "they drifted" is the defect, not "one is wrong".
    _lbar = _pf.evaluate("""() => {
        const w = document.querySelector('.stageCanvasWrap');
        const bar = w.querySelector('.skfull');
        const box = w.querySelector('.skribl-inline');
        if (!bar) return { missing: true };
        const br = bar.getBoundingClientRect(), wr = w.getBoundingClientRect();
        const t = bar.querySelector('.skfull-track');
        const p = bar.querySelector('.skfull-play');
        return {
          shown: getComputedStyle(bar).display,
          btns: [...bar.querySelectorAll('.skfull-btn')].map(b => b.className.split(' ')[1]),
          bare: !!(box && box.classList.contains('is-bare')),
          /* ABSENT IS A REAL ANSWER HERE, not a probe failure. The stage
             attaches the player with its own transport already supplied, so
             this embed is built without a control cluster at all -- which is
             why the owner's screenshot of THIS full screen had no controls
             while the gallery's had two sets. Either way what matters is that
             the component is not showing a second transport. */
          ownControls: !box ? 'no-box'
            : (box.querySelector('.skribl-inline-controls')
               ? getComputedStyle(box.querySelector('.skribl-inline-controls')).display
               : 'absent'),
          atBottom: Math.round(wr.bottom - br.bottom),
          scrubOwnRow: !!(t && p && t.getBoundingClientRect().bottom
                          <= p.getBoundingClientRect().top + 1) }; }""")
    check("the profile's full screen carries the SAME bar as the gallery's tile",
          not _lbar.get("missing") and _lbar["shown"] == "flex"
          and _lbar["btns"] == ['skfull-restart', 'skfull-play', 'skfull-loop',
                                'skfull-mute', 'skfull-rate', 'skfull-exit'],
          f"{_lbar} \u2014 this literal is the one verify_gallery asserts; the "
          f"two surfaces drifting apart is the defect, not either being wrong")
    check("...at the bottom, scrubber on its own row, component's transport yielding",
          not _lbar.get("missing") and _lbar["atBottom"] <= 1
          and _lbar["scrubOwnRow"] and _lbar["bare"]
          and _lbar["ownControls"] in ("none", "absent"), str(_lbar))

    _pf.evaluate("() => document.getElementById('fullExit').click()")
    _pf.wait_for_timeout(600)
    _back = _pf.evaluate("""() => ({
        pinned: getComputedStyle(document.querySelector('.stageCanvasWrap')).position,
        locked: getComputedStyle(document.documentElement).overflow,
        pressed: document.getElementById('btnFull').getAttribute('aria-pressed') })""")
    check("leaving puts the stage back and unlocks the page",
          _back["pinned"] != "fixed" and _back["locked"] != "hidden"
          and _back["pressed"] == "false",
          f"{_back} \u2014 a page left locked is a page nobody can use again")
    _pf.close()
    _bf.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
