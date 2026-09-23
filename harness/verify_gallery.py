"""The public gallery is opt-in, and /gallery shows exactly what was opted in.

THE CHOICE IS ONE CHECKBOX, and the suite drives it rather than the API.
`POST /api/skribls` has defaulted to `unlisted` since the listing was written;
the two editors never sent a visibility at all until v304, when each post sheet
grew "Show in the public gallery". The claim is three-sided and each side is a
pin here:

  1. UNTICKED, THE KEY IS OMITTED. Not sent as "unlisted" — left out, so the
     server's default is the one statement of what an unmarked post is. Read
     from the request body the browser actually sent, on both surfaces.
  2. TICKED, THE KEY IS "public", and the post is in GET /api/skribls.
  3. IN COMPOSE MODE THERE IS NO BOX. The host's composer decides; a control
     here would be a second answer. The MECHANISM is the element's absence,
     never a search for the words (CLAUDE.md: match the mechanism).

THE PAGE IS THE HOST'S RECIPE WITHOUT A COMPOSER (feed.js): clone the in-post
macro per item, mount, page by the listing's own cursor. So the page's pins
are about what a host would get wrong: the poster URL with the placeholder
still in it, a Load more that re-sends page one, a retry that doubles rows,
an empty state that does not say what puts something there.

Fixtures are UNIQUE PER RUN (a token in every title), because run_harness.sh
gives every suite one server and one database, and the gallery lists what
every other suite posted publicly too.
"""
import gzip
import json
import pathlib
import os
import re
import sys
import urllib.request
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the gallery works.")
    raise SystemExit(77)

results = []
check = make_check(results)
TAG = "gal" + os.urandom(4).hex()


def api(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.loads(r.read().decode())


def listed_ids(limit=100):
    """Every id the public listing returns, following the cursor to the end."""
    out, cursor = [], None
    for _ in range(50):
        body = api(f"/api/skribls?limit={limit}" + (f"&cursor={cursor}" if cursor else ""))
        out += [i["id"] for i in body.get("items", [])]
        cursor = body.get("next_cursor")
        if not cursor:
            break
    return out


def post_public_api(title):
    """A hand-built public post, for the paging fixtures only — the CHOICE is
    driven through the sheets below, never through this."""
    pts = [{"x": 120 + i * 40, "y": 140 + (i % 3) * 30, "color": "#ff48b0",
            "size": 12, "t": i * 120} for i in range(12)]
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [len(pts)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["id"]


def slow_pad_post(title, seconds=6):
    """A public replay long enough to watch the pen move.

    The paging fixture above is twelve points over 1.3 s, which on a fast
    machine is done before a screenshot; the nib is only drawn WHILE a replay
    is running (`setNib(null)` the moment it finishes), so a short drawing
    gives a probe nothing to measure. This one is a diagonal across the whole
    canvas, so every axis of the mapping is exercised rather than a band in
    the middle.
    """
    n = 160
    pts = [{"x": 20 + i * (776 / (n - 1)), "y": 20 + i * (572 / (n - 1)),
            "color": "#ffffff", "size": 10, "t": i * (seconds * 1000 / (n - 1))}
           for i in range(n)]
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay",
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["id"]


def draw(pg, sel):
    box = pg.locator(sel).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx - 100, cy)
    pg.mouse.down()
    for i in range(30):
        pg.mouse.move(cx - 100 + i * 7, cy + (i % 5) * 6)
        pg.wait_for_timeout(15)
    pg.mouse.up()
    pg.wait_for_timeout(400)


def capture_post(pg):
    """The next POST /api/skribls this page makes: (request body, response json)."""
    seen = {}

    def on_req(r):
        if r.method == "POST" and re.search(r"/api/skribls$", r.url.split("?")[0]):
            # The Pad packs the body (skriblPackBody, gzip where the browser
            # can): read the bytes, not the text, and unpack them below.
            seen["body"] = r.post_data_buffer

    def on_res(r):
        if r.request.method == "POST" and re.search(r"/api/skribls$", r.url.split("?")[0]):
            try:
                seen["json"] = r.json()
            except Exception:
                seen["json"] = None
    pg.on("request", on_req)
    pg.on("response", on_res)
    return seen


def wait_post(pg, seen, ms=15000):
    for _ in range(ms // 100):
        if "json" in seen:
            break
        pg.wait_for_timeout(100)
    return seen


def body_json(seen):
    """The body as JSON, whether it went as JSON or through skriblPackBody."""
    raw = seen.get("body")
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "replace")
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def pad_post(b, title, tick):
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => localStorage.clear()")
    pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    draw(pg, "#canvas")
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    pg.click("#postBtn")
    pg.wait_for_timeout(500)
    pg.fill("#postTitleInput", title)
    present = pg.evaluate("() => !!document.getElementById('postPublicInput')")
    if tick:
        pg.click(".post-check")
    checked = pg.evaluate("() => { const e = document.getElementById('postPublicInput'); return e ? e.checked : null; }")
    seen = capture_post(pg)
    pg.click("#postSubmitBtn")
    wait_post(pg, seen)
    pg.wait_for_timeout(300)
    pg.close()
    return present, checked, body_json(seen), (seen.get("json") or {})


def flip_post(b, title, tick):
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("() => localStorage.clear()")
    pg.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    draw(pg, "#pad")
    pg.click("#postBtn")
    pg.wait_for_timeout(500)
    pg.fill("#flipShareTitle", title)
    present = pg.evaluate("() => !!document.getElementById('flipSharePublic')")
    if tick:
        pg.click(".flip-share-check")
    checked = pg.evaluate("() => { const e = document.getElementById('flipSharePublic'); return e ? e.checked : null; }")
    seen = capture_post(pg)
    pg.click("#flipShareSubmit")
    wait_post(pg, seen)
    pg.wait_for_timeout(300)
    pg.close()
    return present, checked, body_json(seen), (seen.get("json") or {})


with sync_playwright() as sp:
    b = sp.chromium.launch()

    # ------------------------------------------------------------ section 1
    print("\nGALLERY 1 — the Pad's sheet: the box at its default omits the key; ticked sends public")
    present, checked, body, res = pad_post(b, TAG + " pad plain", tick=False)
    pad_plain = res.get("id")
    check("Pad: the box is on the sheet and starts unticked", present and checked is False,
          f"present={present} checked={checked}")
    check("Pad, unticked: the body the browser sent carries NO visibility key",
          body is not None and "visibility" not in body,
          "no body captured" if body is None else f"keys: {sorted(body)[:12]}")
    check("Pad, unticked: the post was created", bool(pad_plain), str(res)[:120])
    if pad_plain:
        # UNLISTED, by its two halves: reachable by its link (a private post
        # 404s to an anonymous reader) and absent from the listing (section 3).
        try:
            st = urllib.request.urlopen(BASE + f"/api/skribls/{pad_plain}", timeout=20).status
        except Exception as exc:
            st = getattr(exc, "code", str(exc))
        check("Pad, unticked: the post is reachable by its link", st == 200, str(st))

    present, checked, body, res = pad_post(b, TAG + " pad public", tick=True)
    pad_public = res.get("id")
    check("Pad, ticked: the box reads checked", checked is True, str(checked))
    check("Pad, ticked: the body the browser sent says visibility 'public'",
          body is not None and body.get("visibility") == "public",
          "no body captured" if body is None else str(body.get("visibility")))
    check("Pad, ticked: the post was created", bool(pad_public), str(res)[:120])

    # ------------------------------------------------------------ section 2
    print("\nGALLERY 2 — Flip's sheet: the same row, the same rule")
    present, checked, body, res = flip_post(b, TAG + " flip plain", tick=False)
    flip_plain = res.get("id")
    check("Flip: the box is on the sheet and starts unticked", present and checked is False,
          f"present={present} checked={checked}")
    check("Flip, unticked: the body the browser sent carries NO visibility key",
          body is not None and "visibility" not in body,
          "no body captured" if body is None else f"keys: {sorted(body)[:12]}")
    check("Flip, unticked: the post was created", bool(flip_plain), str(res)[:120])

    present, checked, body, res = flip_post(b, TAG + " flip public", tick=True)
    flip_public = res.get("id")
    check("Flip, ticked: the body the browser sent says visibility 'public'",
          body is not None and body.get("visibility") == "public",
          "no body captured" if body is None else str(body.get("visibility")))
    check("Flip, ticked: the post was created", bool(flip_public), str(res)[:120])

    # ------------------------------------------------------------ section 3
    print("\nGALLERY 3 — the listing agrees with the sheets")
    ids = set(listed_ids())
    check("both ticked posts are in GET /api/skribls",
          bool(pad_public) and bool(flip_public) and {pad_public, flip_public} <= ids,
          f"pad={pad_public in ids} flip={flip_public in ids}")
    check("neither unticked post is",
          bool(pad_plain) and bool(flip_plain) and not ({pad_plain, flip_plain} & ids),
          f"pad={pad_plain in ids} flip={flip_plain in ids}")

    # ------------------------------------------------------------ section 4
    print("\nGALLERY 4 — compose mode renders no box: the host decides")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/skribl-pad?compose=1")
    # The element, not the words: a comment explaining the absence would
    # contain the words. And the sheet's own inputs are there, so the sheet
    # rendered and the box's absence is the box's.
    has = pg.evaluate("""() => ({ box: !!document.getElementById('postPublicInput'),
                                 title: !!document.getElementById('postTitleInput'),
                                 mode: window.SKRIBL_MODE })""")
    check("compose mode: the sheet rendered (its title field is there)", has["title"], str(has))
    check("compose mode: there is no public box in the document", not has["box"], str(has))
    pg.close()

    # ------------------------------------------------------------ section 5
    print("\nGALLERY 5 — /gallery shows the listing on the in-post player, through the macro")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(600)
    shown = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
    check("no page errors", not errs, "; ".join(errs[:2]))
    check("both ticked posts are on the page", {pad_public, flip_public} <= set(shown),
          f"{len(shown)} tiles; pad={pad_public in shown} flip={flip_public in shown}")
    check("neither unticked post is", not ({pad_plain, flip_plain} & set(shown)),
          f"pad={pad_plain in shown} flip={flip_plain in shown}")
    macro = pg.evaluate("""() => {
        const boxes = [...document.querySelectorAll('#galleryList [data-skribl-inline]')];
        const posters = boxes.map(b => b.querySelector('.skribl-inline-poster'));
        return { boxes: boxes.length,
                 tiles: document.querySelectorAll('#galleryList .tile').length,
                 placeholder: posters.filter(p => p && /__ID__/.test(p.getAttribute('src'))).length,
                 idInPoster: posters.filter((p, i) => p && p.getAttribute('src').includes(
                     encodeURIComponent(boxes[i].getAttribute('data-skribl-id')))).length,
                 mounted: boxes.filter(b => b.classList.contains('is-mounted')
                                          || b.getAttribute('data-skribl-mounted') != null
                                          || !!b.__skriblInline).length };
    }""")
    check("one macro block per tile", macro["boxes"] == macro["tiles"] and macro["tiles"] > 0, str(macro))
    check("no poster still carries the template placeholder", macro["placeholder"] == 0, str(macro))
    check("every poster URL carries its own post's id", macro["idInPoster"] == macro["boxes"], str(macro))

    # The tile plays: the real player, mounted, on the real payload.
    pg.click(f'[data-skribl-id="{pad_public}"]')
    pg.wait_for_timeout(1500)
    st = pg.evaluate("""(id) => { const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const c = el.querySelector('.skribl-inline-canvas');
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        let n = 0; for (let i = 0; i < d.length; i += 4)
          if (Math.abs(d[i]-d[0]) + Math.abs(d[i+1]-d[1]) + Math.abs(d[i+2]-d[2]) > 24) n++;
        return { playing: el.classList.contains('is-playing') || el.classList.contains('is-paused'), ink: n }; }""",
        pad_public)
    check("tapping a tile plays it on the in-post player", st["playing"], str(st))
    check("...and the drawing is on its canvas", st["ink"] > 200, f"{st['ink']} pixels")

    # THE THEME: a Skribl page, so the ground follows the app's theme, and the
    # browser chrome (the theme-color meta) follows the page.
    for theme in ("dark", "light"):
        pg.goto(BASE + "/gallery?theme=" + theme, wait_until="load")
        pg.wait_for_timeout(500)
        t = pg.evaluate("""() => { const m = document.querySelector('meta[name=theme-color]');
            const hex = c => { const r = c.match(/\\d+/g).slice(0, 3).map(Number);
                return '#' + r.map(v => v.toString(16).padStart(2, '0')).join(''); };
            return { meta: m.content.toLowerCase(), body: hex(getComputedStyle(document.body).backgroundColor),
                     attr: document.documentElement.getAttribute('data-theme') }; }""")
        check(f"{theme}: the page ground is the meta's theme colour", t["meta"] == t["body"], str(t))
    pg.close()

    # ------------------------------------------------------------ section 6
    print("\nGALLERY 6 — paging, retry and the empty state")
    # Enough public posts that the first page is full and there is a second.
    extra = [post_public_api(f"{TAG} page {i}") for i in range(26)]
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(600)
    first = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
    more_vis = pg.is_visible("#galleryMore")
    check("the first page is one page of the listing, and Load more is offered",
          len(first) == 24 and more_vis, f"{len(first)} tiles, more visible={more_vis}")
    pg.click("#galleryMore")
    pg.wait_for_timeout(1200)
    second = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
    check("Load more appends the NEXT page — no id twice", len(second) > len(first)
          and len(set(second)) == len(second), f"{len(first)} -> {len(second)}, unique={len(set(second))}")
    check("...and the new rows are ones the first page did not have",
          set(second[:len(first)]) == set(first) and not (set(second[len(first):]) & set(first)),
          f"overlap={len(set(second[len(first):]) & set(first))}")

    # RETRY FROM A CLEAN LIST: fail the listing, see the error state, lift the
    # failure, retry — one row per post, not two.
    pg.route(re.compile(r"/api/skribls(\?|$)"), lambda route: route.abort())
    pg.click("#galleryRetry") if pg.is_visible("#galleryRetry") else None
    pg.evaluate("() => document.getElementById('galleryRetry').click()")
    pg.wait_for_timeout(800)
    err_vis = pg.is_visible("#galleryError")
    check("a failed listing shows the error state with Retry", err_vis and pg.is_visible("#galleryRetry"),
          f"error visible={err_vis}")
    pg.unroute(re.compile(r"/api/skribls(\?|$)"))
    pg.click("#galleryRetry")
    pg.wait_for_timeout(1200)
    after = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
    check("Retry rebuilds the grid from a clean list — no row doubled",
          len(after) == 24 and len(set(after)) == 24 and not pg.is_visible("#galleryError"),
          f"{len(after)} tiles, unique={len(set(after))}")

    # THE EMPTY STATE, driven by an empty listing, says what puts something here.
    pg.route(re.compile(r"/api/skribls(\?|$)"),
             lambda route: route.fulfill(status=200, content_type="application/json",
                                         body=json.dumps({"items": [], "next_cursor": None})))
    pg.click("#galleryRetry") if pg.is_visible("#galleryRetry") else pg.evaluate("() => document.getElementById('galleryRetry').click()")
    pg.wait_for_timeout(800)
    empty = pg.evaluate("""() => { const e = document.getElementById('galleryEmpty');
        return { shown: !e.hidden && getComputedStyle(e).display !== 'none',
                 tiles: document.querySelectorAll('#galleryList .tile').length,
                 more: !document.getElementById('galleryMore').hidden,
                 names: [...e.querySelectorAll('b')].map(b => b.textContent.trim()) }; }""")
    check("an empty listing shows the empty state, no tiles, no Load more",
          empty["shown"] and empty["tiles"] == 0 and not empty["more"], str(empty))
    pg.unroute(re.compile(r"/api/skribls(\?|$)"))
    pg.close()

    # ------------------------------------------------------------ section 7
    print("\nGALLERY 7 — the words on the box are the words in the empty state, and the links resolve")
    # The empty state tells a person which box to tick. Read the label off each
    # sheet and the name out of the empty state, and hold them equal — so the
    # sentence cannot drift from the control it names.
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/skribl-pad")
    pad_label = pg.evaluate("() => document.querySelector('.post-check-text').firstChild.textContent.trim()")
    pad_href = pg.evaluate("() => document.getElementById('galleryItem').getAttribute('href')")
    # YOUR SKRIBLS IS THE PROFILE PAGE (v304): the menu row beside this one
    # is a link there, on both editors.
    pad_mine = pg.evaluate("() => { const a = document.getElementById('postedItem'); return [a.tagName, a.getAttribute('href')]; }")
    check("the Pad's Your Skribls row is a link to the profile",
          pad_mine[0] == "A" and (pad_mine[1] or "").endswith("/library"), str(pad_mine))
    browsing.goto(pg, BASE, "/flip")
    flip_label = pg.evaluate("() => document.querySelector('.flip-share-check .post-check-text').firstChild.textContent.trim()")
    flip_href = pg.evaluate("() => document.getElementById('miGallery').getAttribute('href')")
    flip_mine = pg.evaluate("() => { const a = document.getElementById('miPosted'); return [a.tagName, a.getAttribute('href')]; }")
    check("Flip's Your Skribls row is a link to the profile",
          flip_mine[0] == "A" and (flip_mine[1] or "").endswith("/library"), str(flip_mine))
    check("Pad and Flip label the box with the same words", pad_label == flip_label and bool(pad_label),
          f"{pad_label!r} vs {flip_label!r}")
    check("the empty state names that box by those words", pad_label in empty["names"],
          f"{empty['names']} vs {pad_label!r}")
    pg.goto(BASE + pad_href, wait_until="load")
    check("the Pad's menu row opens the gallery", pg.url.split("?")[0].endswith("/gallery"), pg.url)
    pg.goto(BASE + flip_href, wait_until="load")
    check("Flip's menu row opens the gallery", pg.url.split("?")[0].endswith("/gallery"), pg.url)
    make = pg.evaluate("() => document.getElementById('galleryMake').getAttribute('href')")
    pg.goto(BASE + make, wait_until="load")
    check("the gallery's Make one opens the Pad",
          pg.evaluate("() => !!document.getElementById('canvas') && window.SKRIBL_MODE !== 'compose'"), pg.url)
    pg.goto(BASE + f"/s/{pad_public}", wait_until="load")
    pg.wait_for_timeout(500)
    pl = pg.evaluate("() => { const a = document.getElementById('playerGalleryLink'); return a ? a.getAttribute('href') : null; }")
    check("the player links to the gallery", bool(pl) and pl.endswith("/gallery"), str(pl))
    pg.close()

    b.close()


# ---------------------------------------------------------------------------
_FS_GEOM = "() => { const t = document.querySelector('.tileStage');\n        const box = t.querySelector('.skribl-inline');\n        const c = t.querySelector('.skribl-inline-canvas');\n        const p = t.querySelector('.skribl-inline-poster');\n        const r = e => { const b = e.getBoundingClientRect();\n          return { l: Math.round(b.left), t: Math.round(b.top),\n                   w: Math.round(b.width), h: Math.round(b.height) }; };\n        const pl = box._skriblInline;\n        return { vw: innerWidth, vh: innerHeight, box: r(box), canvas: r(c),\n                 fit: getComputedStyle(c).objectFit,\n                 poster: r(p), st: pl ? pl.state() : null }; }"
_POSTER_BACK = "() => document.querySelector('.tileStage .skribl-inline-poster').getBoundingClientRect().width > 0"
print("\nGALLERY — a drawing can be watched full size")
# THE GAP (owner): the profile's stage has a fullscreen control and /s/<id> has
# one; the page where the drawings actually ARE had none, and its transport
# stays on screen while a Skribl plays, so there was no way to see one big.
#
# THE WRAPPER IS FULLSCREENED, NOT THE COMPONENT. This page's standing rule is
# that no rule of its own touches .skribl-inline, so gallery.js wraps each
# player in .tileStage and that takes the display.
with sync_playwright() as _spg:
    _bg = _spg.chromium.launch()
    _cg = _bg.new_context()
    _pg2 = _cg.new_page()
    _pg2.set_viewport_size({"width": 900, "height": 900})
    post_public_api("fullscreen fixture")
    browsing.goto(_pg2, BASE, "/gallery")
    _pg2.wait_for_timeout(1800)
    _n = _pg2.evaluate("() => document.querySelectorAll('.tile').length")
    check("there are tiles to measure", _n > 0,
          f"{_n} tiles — an empty gallery cannot fail any row below")
    # ONE CONTROL PER THING A PERSON CAN DO, and this is counted rather than
    # merely found because the defect was a SECOND one, not a missing one. The
    # card's head carried `.tileFull` from before direction B and the footer
    # carries `.skfull-full` since; both shipped, on all 24 tiles, same glyph
    # eight pixels apart. "A full-screen control exists" was green on that.
    #
    # So the count is per tile and it is an equality: a tile with two fails
    # here exactly as a tile with none does. Anything that can enter or leave
    # full size is counted -- the footer's button, a head button if one comes
    # back, and any other control whose label says "full screen" -- so the row
    # cannot be satisfied by renaming the duplicate.
    _g = _pg2.evaluate("""() => {
        const tiles = [...document.querySelectorAll('.tile')];
        const fulls = t => [...t.querySelectorAll('button')].filter(b =>
            /full screen/i.test((b.getAttribute('aria-label') || '') + ' '
                                + (b.title || '')) && b.offsetParent !== null);
        const all = tiles.flatMap(fulls);
        return {
          tiles: tiles.length,
          stages: document.querySelectorAll('.tileStage').length,
          buttons: all.length,
          perTile: [...new Set(tiles.map(t => fulls(t).length))].sort(),
          inFooter: all.filter(b => b.closest('.skfull-card')).length,
          wrapped: document.querySelectorAll('.tileStage .skribl-inline').length,
          named: all.every(b => (b.getAttribute('aria-label') || '').length > 10),
          square: all.map(b => { const r = b.getBoundingClientRect();
                  return Math.round(Math.min(r.width, r.height)); }) }; } """)
    check("every tile carries a full-screen control — exactly one",
          _g["tiles"] > 0 and _g["perTile"] == [1],
          f"{_g['buttons']} controls on {_g['tiles']} tiles, counts per tile "
          f"{_g['perTile']} — two is the defect this row exists for")
    check("...and it is the footer's, from the shared bar",
          _g["buttons"] > 0 and _g["inFooter"] == _g["buttons"],
          f"{_g['inFooter']} of {_g['buttons']} inside .skfull-card — a control "
          f"built by the page again is the divergence lib/fullbar.js ended")
    check("...and every player is inside the wrapper that takes the display",
          _g["wrapped"] == _g["tiles"],
          f"{_g['wrapped']} of {_g['tiles']} players wrapped — a player outside "
          f".tileStage has nothing to fullscreen")
    # 36 DRAWN, 44 TO A FINGER. The footer's buttons are the bar's, so they are
    # the bar's shape too: a 36px disc with a ::before band out to 44. The 44 is
    # therefore not in this rect and is not asserted from it -- verify_a11y
    # measures the band where it can be measured, by walking elementFromPoint
    # over the real element. What belongs here is the VISIBLE floor.
    check("...and each one is drawn at the visible floor and carries a name",
          _g["named"] and _g["square"] and min(_g["square"]) >= 34,
          f"smallest {min(_g['square']) if _g['square'] else 0}px drawn, "
          f"named={_g['named']} — the 44px reach is verify_a11y's row")
    # WHERE THE FULL-SIZE RULES LIVE, which is the division this page got wrong
    # once and had caught on main. The gallery owns its WRAPPER; the component
    # owns everything about itself. The first cut styled the player's poster and
    # canvas from this page's sheet -- a page hand-writing the component's
    # internals, which verify_inline forbids outright.
    #
    # Asserted as two halves rather than one, because either alone passes on the
    # broken arrangement: the page could carry a correct wrapper rule AND the
    # copies, and the component could carry the immersive rules while the page
    # still duplicated them.
    _sheet = (pathlib.Path(__file__).resolve().parent.parent
              / "skribl" / "templates" / "skribl" / "skribl_gallery.html").read_text()
    # The selector picks up whatever else shares the rule -- `:fullscreen` got
    # `.is-immersive-page` beside it when the iPhone fallback landed, and a
    # pattern that insisted on `:fullscreen {` alone went red on a correct
    # tree. What is under test is the rule BODY, so match up to the brace
    # rather than spelling out a selector list that is expected to grow.
    _wrap = re.search(r"\.tileStage:fullscreen[^{]*\{([^}]*)\}", _sheet)
    check("the gallery styles its own wrapper, and names no aspect ratio doing it",
          bool(_wrap) and not re.search(r"\d+\s*/\s*\d+", _wrap.group(1)),
          f"rule body {(_wrap.group(1).strip() if _wrap else 'MISSING')!r} — a "
          f"second copy of 16/9 here is a pair nothing gates")
    _comp = (pathlib.Path(__file__).resolve().parent.parent
             / "skribl" / "static" / "inlineplayer.css").read_text()
    check("...and the component owns what immersive MEANS for its own parts",
          ".skribl-inline.is-immersive" in _comp
          and "object-fit: contain" in _comp,
          "the immersive rules are not in inlineplayer.css — if they moved back "
          "into a page, that page is hand-writing the player's internals again")

    # WHAT FULL SIZE ACTUALLY SHOWS (owner, from the deployed gallery: "full
    # page image cuts off, then on play it doesn't go all the way to edge on
    # left"). Both halves measured, because both were wrong:
    #
    #   the box   `height: 100%` never resolved against an auto grid area, so
    #             it fell back to content size: 800x450 at the BOTTOM of a
    #             1400x900 screen.
    #   the card  the poster is the 1200x630 share card, cropped by
    #             inlineplayer.css to keep its wordmark out of frame. Right at
    #             tile size; at screen size it just cuts the picture off --
    #             measured running 151->1249 across a box of 300->1100.
    _pg2.evaluate("() => document.querySelector('.tileStage').requestFullscreen()")
    _pg2.wait_for_timeout(1800)
    _fs = _pg2.evaluate(_FS_GEOM)
    check("full screen: the box fills the display, top-left to bottom-right",
          _fs["box"]["w"] == _fs["vw"] and _fs["box"]["h"] == _fs["vh"]
          and _fs["box"]["l"] == 0 and _fs["box"]["t"] == 0,
          f"{_fs['box']} in {_fs['vw']}x{_fs['vh']} — the first draft measured "
          f"800x450 at the bottom of the screen")
    check("...and the drawing is painted on the canvas, not left as a cropped card",
          _fs["poster"]["w"] == 0 and _fs["canvas"]["w"] > 0,
          f"poster {_fs['poster']}, canvas {_fs['canvas']}")
    check("...which means the payload got loaded, because a tile has none until asked",
          bool(_fs["st"]) and _fs["st"]["loaded"],
          f"{_fs['st']} — hiding the card without loading it would have traded a "
          f"cropped picture for a black screen")
    # AND IT USES THE WHOLE DISPLAY. The box is 16:9 so a feed's tiles are all
    # one shape; holding that ratio on a screen letterboxes the drawing TWICE.
    # These fixtures are 4:3, so on a wider display the canvas should be as tall
    # as the screen and narrower than it -- never shorter than it.
    check("...and the drawing SCALES UP to the display rather than sitting at its own size",
          _fs["canvas"]["w"] == _fs["vw"] and _fs["canvas"]["h"] == _fs["vh"]
          and _fs["fit"] == "contain",
          f"canvas {_fs['canvas']} object-fit={_fs['fit']!r} in "
          f"{_fs['vw']}x{_fs['vh']} — `max-width: 100%` only ever shrinks, so an "
          f"816x612 drawing measured 816x612 on a 900x900 screen. contain is "
          f"what fits it both ways and keeps its ratio.")
    _pg2.evaluate("() => document.exitFullscreen()")
    _pg2.wait_for_timeout(600)
    check("...and leaving puts the tile back, card and all",
          _pg2.evaluate(_POSTER_BACK),
          "the tile is still showing the drawing where its poster belongs")
    _pg2.close()
    _bg.close()


# ---------------------------------------------------------------------------
print("\nGALLERY — a tile says WHAT it is, and the listing can say so without a payload")
# THE GAP (owner): "on public gallery it doesn't show a pen, book - no way to
# tell which". The listing defers `payload_json` on purpose (9.75 ms against
# 1.04 ms), so a tile could not look; v307 puts `kind` and `pages` on the post,
# written at post time by the SAME test the players use to decide it.
#
# DRIVEN THROUGH REAL POSTS of each shape, including the one with no explicit
# playbackMode, because that is the branch a second implementation would get
# wrong: more than one frame means flip, and a one-page Flip document is a
# replay, which is what every player already says about it.
_SHAPES = (("a replay", "replay", 1, "pad", 1),
           ("a flip", "flip", 6, "flip", 6),
           ("no mode, one frame", None, 1, "pad", 1),
           ("no mode, three frames", None, 3, "flip", 3))
_made = {}
for _title, _mode, _n, _wantkind, _wantpages in _SHAPES:
    _frames = [{"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0},
                            {"x": 200, "y": 150, "color": "#fff", "size": 6, "t": 120}],
                "strokeGroups": [2]} for _ in range(_n)]
    _body = {"title": _title, "version": 2, "schemaVersion": 2, "visibility": "public",
             "canvasSize": {"cssWidth": 800, "cssHeight": 600}, "frames": _frames}
    if _mode:
        _body["playbackMode"] = _mode
    _rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(_rq, timeout=20) as _r:
        _made[_title] = (json.loads(_r.read().decode())["id"], _wantkind, _wantpages)

_listing = api("/api/skribls?limit=60")
_by_id = {i["id"]: i for i in _listing.get("items", [])}
for _title, (_id, _wantkind, _wantpages) in _made.items():
    _item = _by_id.get(_id)
    check(f"the listing says {_title!r} is a {_wantkind} of {_wantpages} page(s)",
          bool(_item) and _item.get("kind") == _wantkind and _item.get("pages") == _wantpages,
          f"listing said kind={_item.get('kind')!r} pages={_item.get('pages')!r}"
          if _item else "the post is not in the listing at all")

# AND HOW BIG THE DRAWING IS (v309), on the same row and for the same reason:
# the tile frames its idle poster onto the drawing, and the listing is the only
# place it can learn the shape without fetching the payload it deliberately
# defers.
#
# THE ABSENCE IS THE OTHER HALF. `canvasSize` is OPTIONAL in a payload -- a
# Skribl from before Pad had a size picker simply has none -- so the honest
# answer for one is null, and the component then keeps the crop it had before
# the column. Posted here as a real payload with the key left out, because
# "the listing reports the size" is satisfied by a column that reports 816x612
# for everything.
_nosize = {"title": TAG + " no canvasSize", "version": 2, "schemaVersion": 2,
           "visibility": "public",
           "frames": [{"strokes": [{"x": 5, "y": 5, "color": "#fff", "size": 4, "t": 0},
                                   {"x": 90, "y": 70, "color": "#fff", "size": 4, "t": 90}],
                       "strokeGroups": [2]}]}
_rq2 = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_nosize).encode(),
                              headers={"Content-Type": "application/json"})
with urllib.request.urlopen(_rq2, timeout=20) as _r2:
    _nosize_id = json.loads(_r2.read().decode())["id"]

_listing2 = api("/api/skribls?limit=60")
_by_id2 = {i["id"]: i for i in _listing2.get("items", [])}
_sized = _by_id2.get(next(iter(_made.values()))[0]) or {}
_unsized = _by_id2.get(_nosize_id) or {}
check("the listing carries the drawing's size, so a tile can frame its poster",
      _sized.get("canvas_w") == 800 and _sized.get("canvas_h") == 600,
      f"canvas_w={_sized.get('canvas_w')!r} canvas_h={_sized.get('canvas_h')!r} "
      f"\u2014 posted at 800x600; without this the tile shows the share card's "
      f"own ground and plate border either side of the drawing")
check("...and answers null for a payload that never said, rather than guessing",
      _unsized.get("id") == _nosize_id
      and _unsized.get("canvas_w") is None and _unsized.get("canvas_h") is None,
      f"{ {k: _unsized.get(k) for k in ('id', 'canvas_w', 'canvas_h')} } \u2014 a "
      f"guessed 4:3 would frame the picture WRONGLY, which is worse than framing "
      f"it widely; the component keeps the band crop on a null")

with sync_playwright() as _spk:
    _bk = _spk.chromium.launch()
    _pk = _bk.new_context().new_page()
    _pk.set_viewport_size({"width": 1100, "height": 1100})
    browsing.goto(_pk, BASE, "/gallery")
    _pk.wait_for_timeout(2000)
    _marks = _pk.evaluate("""() => { const m = {};
        document.querySelectorAll('.tile').forEach(t => {
          m[t.getAttribute('data-id')] = {
            kind: !!t.querySelector('.tileKind'),
            sr: (t.querySelector('.tileSr') || {}).textContent || '' }; });
        return m; }""")
    for _title, (_id, _wantkind, _wantpages) in _made.items():
        _m = _marks.get(_id)
        _word = f"{_wantpages} pages" if _wantkind == "flip" and _wantpages > 1 else (
            "a flip" if _wantkind == "flip" else "a replay")
        check(f"...and the tile for {_title!r} carries a mark saying so",
              bool(_m) and _m["kind"] and _word in _m["sr"],
              f"mark={_m['kind'] if _m else '?'} sr={(_m or {}).get('sr')!r}, wanted {_word!r}")
    # THE MARKS ARE DECORATION AND THE WORDS ARE THE CONTENT. Two unlabelled
    # glyphs would tell a screen reader nothing, so the badges are aria-hidden
    # and .tileSr carries the sentence. Asserted because it is the half that
    # cannot be seen to be missing.
    _a11y = _pk.evaluate("""() => ({
        hidden: [...document.querySelectorAll('.tileMarks')]
                  .every(m => m.getAttribute('aria-hidden') === 'true'),
        marks: document.querySelectorAll('.tileMarks').length,
        offscreen: [...document.querySelectorAll('.tileSr')].every(s => {
                     const r = s.getBoundingClientRect(); return r.width <= 2 && r.height <= 2; }) })""")
    check("the marks are decoration (aria-hidden) and the words are text a reader gets",
          _a11y["marks"] > 0 and _a11y["hidden"] and _a11y["offscreen"],
          f"{_a11y} — a visible .tileSr would print the sentence twice, and an "
          f"unhidden glyph would announce as an empty image")
    # ...AND NEITHER MARK SITS ON A CONTROL. The kind badge was placed at
    # bottom left because that is where the profile's row puts it -- but a
    # row has nothing underneath, and a tile has the in-post player, whose
    # control cluster is at left 9 / bottom 9. So the pen or the book was
    # drawn on top of play, mute and loop on every tile (owner's
    # screenshot). Both badges moved to the top edge.
    #
    # ASSERTED AS AN INTERSECTION OF THE TWO LIVE RECTS, not as "the badge
    # is at the top": the overlap is the defect and the corner is only the
    # current fix, so a later change that moves the transport instead
    # should fail this too. The cluster is measured while it is invisible
    # (opacity 0 until hover or play), which is fine -- opacity does not
    # move a box, and a control that is one hover away from visible is one
    # hover away from being covered.
    _over = _pk.evaluate("""() => {
        const hit = (a, b) => !(a.right <= b.left || b.right <= a.left ||
                                a.bottom <= b.top || b.bottom <= a.top);
        const out = { pairs: 0, over: [] };
        document.querySelectorAll('.tile').forEach(t => {
          const c = t.querySelector('.skribl-inline-controls');
          if (!c) return;
          const cr = c.getBoundingClientRect();
          if (!cr.width || !cr.height) return;
          t.querySelectorAll('.tileMark').forEach(k => {
            const kr = k.getBoundingClientRect();
            if (!kr.width) return;
            out.pairs++;
            if (hit(kr, cr)) out.over.push(t.getAttribute('data-id') + '/' +
                                           (k.getAttribute('class') || ''));
          });
        });
        return out; }""")
    # THE PREMISE MOVED, SO THE ASSERTION DID (v308, direction B). This used to
    # measure a badge against the component's own control cluster, because the
    # cluster sat at bottom left OF THE DRAWING and the pen landed on the play
    # button. On a post-like card the transport is a FOOTER under the drawing
    # and the component's own cluster is hidden (`is-bare`), so there is no
    # pair left to overlap -- which is why this went to zero pairs rather than
    # to zero overlaps.
    #
    # Zero pairs is the old assertion passing vacuously, so it is replaced
    # rather than relaxed: what is true now, and worth keeping true, is that
    # NOTHING a viewer presses is inside the drawing. That is the stronger
    # claim -- it fails if any control moves back onto the picture, whichever
    # control it is.
    _inside = _pk.evaluate("""() => {
        const out = { tiles: 0, inArt: [] };
        document.querySelectorAll('.tile').forEach(t => {
          const st = t.querySelector('.tileStage');
          if (!st) return;
          out.tiles++;
          const sr = st.getBoundingClientRect();
          t.querySelectorAll('button, a[href]').forEach(c => {
            if (!st.contains(c)) return;
            /* the way out of full screen is allowed to be over the art: it is
               the one control with nowhere else to live */
            if (c.classList.contains('tileExit')) return;
            const r = c.getBoundingClientRect();
            if (r.width && r.height) out.inArt.push(c.className.split(' ')[0]);
          });
        });
        return out; }""")
    check("nothing a viewer presses sits inside the drawing",
          _inside["tiles"] > 0 and not _inside["inArt"],
          f"{_inside['tiles']} tiles measured, controls inside the art: "
          f"{sorted(set(_inside['inArt']))} \u2014 the transport is a footer now, "
          f"and the pen on the play button is what that move was for")
    # TOOLTIPS, which this page had none of (owner). The module is loaded and
    # started here; it moves every `title` to `data-tip` and draws its own.
    # Asserted on data-tip, not on `title`, because the module REMOVES the
    # title -- so a page that loaded the sheet and not the module would still
    # have titles and would fail this, which is the point.
    _tips = _pk.evaluate("""() => ({
        started: !!window.SkriblTooltip,
        tabs: [...document.querySelectorAll('.tab')].every(b => !!b.getAttribute('data-tip')),
        reports: [...document.querySelectorAll('.report')].every(b => !!b.getAttribute('data-tip')),
        leftovers: document.querySelectorAll('.tab[title], .report[title]').length })""")
    check("the gallery draws tooltips: every tab and every Report carries one",
          _tips["started"] and _tips["tabs"] and _tips["reports"],
          str(_tips))
    check("...and the native title is gone, so the browser's own does not stack under it",
          _tips["leftovers"] == 0,
          f"{_tips['leftovers']} controls still carry a title attribute")
    _pk.close()
    _bk.close()

# ---------------------------------------------------------------------------
# THE CARD: who made it, and the caption over the drawing (v308)
#
# WHY THE LISTING IS INTERCEPTED. Skribl has no user table, so this demo's
# every post has user_id NULL and the server can never put an author on a tile
# here -- verify_hostseams drives the API side with a real resolver. What is
# under test on THIS side is the renderer: given an author, does the card draw
# one, and given none, does it draw nothing. Rewriting the one response is the
# only way to ask that question of the real page, and it keeps the two halves
# pinned separately rather than through one end-to-end fixture that would go
# green if either half alone worked.
print("\nGALLERY — the card says who made it, and hides the words until asked")
with sync_playwright() as _spa:
    _ba = _spa.chromium.launch()
    _pa = _ba.new_context().new_page()
    _pa.set_viewport_size({"width": 1100, "height": 1000})

    _AUTHOR = {"id": "7", "display_name": "Mr. B", "username": "bigballbaron",
               "avatar_url": BASE + "/static/skribl/icon-192.png",
               "url": "https://example.test/u/bigballbaron", "verified": True}
    # A HOSTILE URL IN A HOST-SUPPLIED FIELD. `author.url` becomes an href on
    # something people click, and the resolver is the host's function reading
    # the host's database -- so it is not trusted to hold a web address.
    _EVIL = {"id": "9", "display_name": "Clicky", "username": "clicky",
             "url": "javascript:window.__pwned = 1"}

    def _inject(route):
        r = route.fetch()
        try:
            data = r.json()
        except Exception:
            route.fulfill(response=r)
            return
        items = data.get("items") or []
        for i, item in enumerate(items):
            if i == 0:
                item["author"] = dict(_AUTHOR)
                # LONG ON PURPOSE. The first fixture was one line, so the
                # clamp folded nothing and opening it changed no height -- the
                # probe could not tell a working toggle from a dead one, and
                # said so: shut 28, open 28.
                item["caption"] = ('a description long enough to need more than two lines on a card this wide, so that the clamp has something to fold and the toggle has something to unfold, which a one-line caption cannot show')
                # A PLAY COUNT, so the narrow-tier row below has something to
                # stand down. The listing's own fixtures post with 0 views and
                # gallery.js draws no count at all for those -- against which
                # "the count is hidden at 390" is green on a page that never
                # had one.
                item["views"] = 42
            elif i == 1:
                item["author"] = dict(_EVIL)
                # SHORT ON PURPOSE, and it is the other half of the toggle
                # rows below: a caption the clamp does not fold is the case
                # where the control must NOT be drawn, and without one on the
                # page "the toggle appears where it is needed" passes on a
                # grid that draws it everywhere.
                item["caption"] = "one short line"
            # every other row keeps NO author, which is the absence case
        route.fulfill(response=r, json=data)

    _pa.route("**/api/skribls?*", _inject)
    browsing.goto(_pa, BASE, "/gallery")
    _pa.wait_for_timeout(2200)

    _card = _pa.evaluate("""() => {
        const t = document.querySelectorAll('.tile');
        const a = t[0] && t[0].querySelector('.tauth');
        const img = a && a.querySelector('.tavatar img');
        return {
          tiles: t.length,
          has: !!a, tag: a ? a.tagName : null, href: a ? (a.getAttribute('href') || '') : '',
          dn: a ? (a.querySelector('.tdn') || {}).textContent : null,
          un: a ? (a.querySelector('.tun') || {}).textContent : null,
          tick: !!(a && a.querySelector('.tverified')),
          avatar: img ? img.getAttribute('src') : null,
          /* the block sits between the head and the drawing, which is where
             the owner asked for it ("at the top under the title") */
          inHead: !!(a && a.closest('.thead')),
          titleInNames: !!(a && a.querySelector('.tnames .tt')),
          aboveStage: !!(a && t[0].querySelector('.tileStage') &&
            a.getBoundingClientRect().bottom <= t[0].querySelector('.tileStage').getBoundingClientRect().top + 1),
          solos: document.querySelectorAll('.tsolo').length,
          /* and the tiles with no author draw no block at all */
          blocks: document.querySelectorAll('.tauth').length,
        }; }""")
    check("the fixture really produced a grid to measure",
          _card["tiles"] >= 3, f"{_card['tiles']} tiles — fewer than three and "
          f"the absence assertion below has nothing to be absent from")
    check("a described author is drawn on the card: name, @handle, avatar, tick",
          _card["has"] and _card["dn"] == "Mr. B" and _card["un"] == "@bigballbaron"
          and _card["tick"] and (_card["avatar"] or "").endswith("icon-192.png"),
          str(_card) + " \u2014 a null avatar can also mean the image 404'd: the "
          "element's own onerror swaps it for an initial, which is the fallback "
          "working and the fixture wrong")
    check("...at the top of the card, with the title under the name",
          _card["inHead"] and _card["titleInNames"] and _card["aboveStage"],
          f"{_card} \u2014 direction B: who first, then what, the way a post head "
          f"reads; the title used to share a flex row with the time and two buttons")
    check("...and a post with no author draws NO author block",
          _card["blocks"] == 2 and _card["solos"] == _card["tiles"] - 2,
          f"{_card['blocks']} .tauth blocks and {_card['solos']} unattributed "
          f"heads out of {_card['tiles']} tiles \u2014 `.tauth` means somebody is "
          f"named, which is what makes its absence readable; the unattributed "
          f"card uses `.tsolo` so it cannot borrow the meaning")

    _evil = _pa.evaluate("""() => {
        const a = [...document.querySelectorAll('.tauth')]
                    .find(x => (x.textContent || '').indexOf('clicky') >= 0);
        return { found: !!a, tag: a ? a.tagName : null,
                 href: a ? (a.getAttribute('href') || '') : '' }; }""")
    check("a javascript: author URL never becomes an href",
          _evil["found"] and _evil["tag"] == "DIV" and not _evil["href"],
          f"{_evil} — the name still renders, as plain text; only the link is refused")

    # THE CAPTION, OVER THE DRAWING. Asserted by PAINT and geometry, not by
    # the class alone: `opacity` is what hides it (the text stays in the
    # accessibility tree), so "hidden" here means a computed opacity of 0.
    # THE CAPTION CAME OFF THE ART (v308, direction B). It was a scrim over
    # the drawing because a poster-first card had nowhere else to put it; a
    # post-like card has room for words, so it is text under the title,
    # clamped to two lines, and the toggle EXPANDS it rather than revealing
    # it.
    #
    # WHAT THE OLD ASSERTIONS WERE PROTECTING SURVIVES, and it is worth
    # saying which part: the text had to stay in the accessibility tree at
    # all times, which is why the scrim used `opacity` and never `display`.
    # A clamp keeps that for free -- the text is present, and a reader that
    # does not paint is not affected by a line limit. What goes is the
    # hover branch, because nothing is hidden any more.
    _cap = _pa.evaluate("""() => {
        const t = document.querySelector('.tile');
        const cap = t.querySelector('.tcap');
        const st = t.querySelector('.tileStage');
        const btn = t.querySelector('.tileCapBtn');
        if (!cap || !st || !btn) return { missing: !cap ? 'cap' : (!st ? 'stage' : 'btn') };
        const cr = cap.getBoundingClientRect(), sr = st.getBoundingClientRect();
        const cs = getComputedStyle(cap);
        const shut = Math.round(cr.height);
        btn.click();
        const open = Math.round(cap.getBoundingClientRect().height);
        const pressed = btn.getAttribute('aria-pressed');
        btn.click();
        return { text: cap.textContent,
                 aboveStage: cr.bottom <= sr.top + 1,
                 clamp: cs.webkitLineClamp || cs.lineClamp,
                 display: cs.display, visibility: cs.visibility,
                 hidden: cap.hasAttribute('hidden'),
                 shut: shut, open: open, pressed: pressed,
                 shutAgain: Math.round(cap.getBoundingClientRect().height) }; }""")
    check("the caption is text under the title, not a scrim on the drawing",
          not _cap.get("missing") and _cap["aboveStage"]
          and _cap["text"].startswith("a description long enough"),
          f"{_cap} \u2014 nothing needs to sit on the picture once the card has"
          f" somewhere to put words")
    check("...clamped at rest, and the toggle opens it and shuts it again",
          not _cap.get("missing") and _cap["clamp"] in ("2", 2)
          and _cap["open"] > _cap["shut"] and _cap["shutAgain"] == _cap["shut"],
          f"{_cap} \u2014 a clamp that never opens is a description nobody can"
          f" finish reading")
    check("...and the toggle says which state it is in",
          _cap.get("pressed") == "true", str(_cap))

    # The expander, both cards at once, and the clamp's real height.
    MORE_JS = """() => {
        const t = [...document.querySelectorAll('.tile')];
        const one = t[0], two = t[1];
        const btn = one && one.querySelector('.tileCapBtn');
        const cap = one && one.querySelector('.tcap');
        if (!btn || !cap) return { missing: true };
        const r = btn.getBoundingClientRect(), cr = cap.getBoundingClientRect();
        const line = parseFloat(getComputedStyle(cap).lineHeight);
        const b2 = two && two.querySelector('.tileCapBtn');
        const c2 = two && two.querySelector('.tcap');
        return {
          shown: getComputedStyle(btn).display,
          word: (btn.textContent || '').trim(),
          inHead: !!btn.closest('.thead'),
          afterCap: cap.nextElementSibling === btn,
          reach: Math.round(r.height) >= 34,
          capH: Math.round(cr.height), line: Math.round(line),
          shortShown: b2 ? getComputedStyle(b2).display : 'no-btn',
          shortClipped: c2 ? c2.scrollHeight > c2.clientHeight + 1 : null }; }"""

    _more = _pa.evaluate(MORE_JS)
    # WHERE THE EXPANDER LIVES, AND WHERE IT DOES NOT. It was a glyph in the
    # head beside Report, which cost 44px of the row the display NAME is in --
    # the row below measures what that cost. It is a word under the sentence
    # now, and the head is the name's again.
    check("the caption's expander is a word under the caption, not a glyph in the head",
          not _more.get("missing") and _more["shown"] != "none"
          and _more["word"].lower() == "show more"
          and _more["afterCap"] and not _more["inHead"],
          f"{_more} \u2014 a speech bubble beside Report does not say 'there is "
          f"more of this sentence'; two words under the sentence do")
    # AND ONLY WHERE THE CLAMP ACTUALLY BITES. Tile 1's caption is one line,
    # so its control must not exist -- asserted on a DIFFERENT card from the
    # row above, because "it is drawn" and "it is drawn only when needed" are
    # two claims and one page can satisfy the first while failing the second.
    check("...and it is absent on a caption the clamp does not fold",
          not _more.get("missing") and _more["shortClipped"] is False
          and _more["shortShown"] in ("none", "no-btn"),
          f"{_more} \u2014 every captioned card used to carry a button that "
          f"expanded nothing, which is a control that lies about there being more")
    # THE CLAMP DOES NOT LEAK. `overflow: hidden` clips at the PADDING box, so
    # a padding-bottom is clipped region the third line shows through: the card
    # rendered two lines, an ellipsis, and a third line sliced in half. Two
    # lines of text is the whole box, within a pixel of rounding.
    check("...and the clamped caption is exactly two lines tall, with nothing under them",
          not _more.get("missing")
          and abs(_more["capH"] - 2 * _more["line"]) <= 2,
          f"{_more} \u2014 {_more.get('capH')}px against {2 * _more.get('line', 0)}px "
          f"for two lines: anything more is a line bleeding through the clip")

    # THE NAME IS NEVER APPROXIMATE. A clipped handle still reads as a handle;
    # a clipped display name reads as a different person. Measured at 390,
    # which is where the head's row is genuinely full, and on the card that
    # ALSO carries a caption and its expander -- the crowded case, not the
    # roomy one.
    _pa.set_viewport_size({"width": 390, "height": 900})
    _pa.wait_for_timeout(400)
    _narrow = _pa.evaluate("""() => {
        const t = document.querySelector('.tile');
        const dn = t.querySelector('.tdn'), un = t.querySelector('.tun');
        const plays = t.querySelector('.plays');
        const head = t.querySelector('.thead');
        return { w: window.innerWidth,
                 dnCut: dn.scrollWidth > dn.clientWidth + 1,
                 dnText: dn.textContent,
                 unThere: !!un,
                 plays: plays ? getComputedStyle(plays).display : 'absent',
                 slack: Math.round(head.getBoundingClientRect().width)
                        - [...head.children].reduce((a, e) =>
                            a + e.getBoundingClientRect().width, 0) }; }""")
    check("at 390 the display name is not ellipsised",
          _narrow["w"] == 390 and _narrow["dnCut"] is False,
          f"{_narrow} \u2014 `margin-left: auto` on the time ate the free space "
          f"before the name could have it, and this said 'Mr\u2026'")
    check("...because the count stood down, not because the head had room to spare",
          _narrow["plays"] == "none" and _narrow["unThere"],
          f"{_narrow} \u2014 if the row still fits with the count in it, this "
          f"tier is not doing anything and the next long name will clip again")
    _pa.set_viewport_size({"width": 1100, "height": 1000})
    _pa.wait_for_timeout(300)

    # ---- THE FOOTER IS THE FULL-SCREEN BAR AT CARD SIZE (v308) ------------
    # Direction B puts the transport under the drawing. Rather than write a
    # second one in gallery.js -- which would contradict lib/fullbar.js's
    # reason for existing within a day of it landing -- the card calls the
    # SAME builder with a different control list.
    #
    # ASSERTED AS "the same class of thing, configured differently": the
    # footer's controls carry the module's own `skfull-` names, so a card that
    # grew a hand-rolled transport would fail this even if it looked right.
    _foot = _pa.evaluate("""() => {
        const tiles = [...document.querySelectorAll('.tile')];
        const t = tiles[0];
        const f = t.querySelector('.skfull-card');
        if (!f) return { missing: true, withFoot: 0, tiles: tiles.length };
        const st = t.querySelector('.tileStage');
        const box = t.querySelector('.skribl-inline');
        return {
          tiles: tiles.length,
          withFoot: tiles.filter(x => x.querySelector('.skfull-card')).length,
          btns: [...f.querySelectorAll('.skfull-btn')].map(b => b.className.split(' ')[1]),
          track: !!f.querySelector('.skfull-track'),
          belowArt: !!(st && f.getBoundingClientRect().top
                       >= st.getBoundingClientRect().bottom - 1),
          bare: !!(box && box.classList.contains('is-bare')),
          ownDur: (() => { const d = t.querySelector('.skribl-inline-dur');
                           return d ? getComputedStyle(d).display : 'absent'; })(),
          /* the full-screen bar's own row must NOT be showing on a card */
          fullBars: t.querySelectorAll('.skfull:not(.skfull-card)').length }; }""")
    check("every card carries the transport, under the drawing",
          not _foot.get("missing") and _foot["withFoot"] == _foot["tiles"]
          and _foot["belowArt"] and _foot["track"],
          f"{_foot} \u2014 direction B is a footer, not a scrim")
    check("...built by lib/fullbar.js, not hand-rolled beside it",
          not _foot.get("missing")
          and _foot["btns"] == ['skfull-play', 'skfull-loop', 'skfull-mute', 'skfull-full'],
          f"{_foot} \u2014 the `skfull-` names are the module's; a card that grew "
          f"its own transport would fail here even looking identical")
    check("...and the component's own chrome yields to it on a card too",
          not _foot.get("missing") and _foot["bare"]
          and _foot["ownDur"] in ("none", "absent"),
          f"{_foot} \u2014 two transports on one drawing is the defect, in a grid "
          f"as much as in full screen")

    # Counts each footer's own DOM rewrites over a window; see the rows that use it.
    PACE_JS = """(ms) => new Promise(res => {
        const foots = [...document.querySelectorAll('.tile .skfull-card')];
        const counts = foots.map(() => 0);
        const obs = foots.map((f, i) => {
          const o = new MutationObserver(recs => { counts[i] += recs.length ? 1 : 0; });
          o.observe(f, { subtree: true, childList: true,
                         attributes: true, characterData: true });
          return o; });
        setTimeout(() => {
          obs.forEach(o => o.disconnect());
          res({ tiles: foots.length,
                worst: counts.length ? Math.max.apply(null, counts) : 0,
                total: counts.reduce((a, b) => a + b, 0) }); }, ms); })"""
    # AN IDLE GRID IS NOT A RUNNING ONE, and this row is the reason the card's
    # loop paces itself. lib/fullbar.js follows the clock on a frame loop, which
    # is right for ONE bar over ONE drawing in full screen and wrong for a
    # gallery, where `running(true)` on every card meant a rAF per card
    # repainting the same 0:00 sixty times a second. The module's own comment
    # already said a hidden bar must not cost a frame; a visible-but-stopped
    # one costs the same and was not covered.
    #
    # MEASURED AS WORK DONE, not as which timer was used. Each sync() rewrites
    # the footer's glyphs, its fill width and its clock, so a MutationObserver
    # over the footers counts syncs directly and does not care whether the next
    # beat came from rAF or setTimeout — a later rewrite that keeps rAF but
    # skips the writes would still be cheap, and should still pass.
    PACE_MS = 800
    _pace = _pa.evaluate(PACE_JS, PACE_MS)
    _budget = max(2, round(PACE_MS / 250.0) + 2)
    check("a grid of stopped cards paces its bars instead of running them",
          _pace["tiles"] > 0 and _pace["worst"] <= _budget,
          f"busiest footer rewrote itself {_pace['worst']} times in {PACE_MS} ms "
          f"across {_pace['tiles']} cards (budget {_budget}) — a frame loop is "
          f"~{round(PACE_MS * 0.06)} and is what this row exists to catch")
    check("...and they are still following it, not stopped dead",
          _pace["total"] > 0,
          f"{_pace} — a bar that never syncs cannot notice another post "
          f"claiming the page's sound, and would pass the row above trivially")

    # WHERE THE POSTER IS PAINTED, scanned rather than read off its rect --
    # `clip-path` is the one property that makes a rect a lie by construction,
    # so getBoundingClientRect() reports the whole card whatever is visible.
    # elementFromPoint answers what is actually hit, and a clipped region does
    # not hit. Walk the box's centre row and centre column for the first and
    # last point that lands on the poster.
    FRAME_JS = """() => {
        /* THE FIRST TILE THAT KNOWS ITS SIZE, not simply the first tile. The
           grid also carries posts whose payload never said -- the suite posts
           one deliberately -- and those keep the band crop by design, so
           measuring tile 0 blindly measures whichever fixture happens to be
           newest. (It did: the unsized fixture landed first and reddened these
           rows, which is the known-bad case arriving for free.) */
        const tiles = [...document.querySelectorAll('.tile')];
        const n = tiles.findIndex(x => x.querySelector('[data-skribl-w]'));
        const t = tiles[n < 0 ? 0 : n];
        const box = t.querySelector('.skribl-inline');
        const r = box.getBoundingClientRect();
        const cy = Math.round(r.top + r.height / 2);
        const cx = Math.round(r.left + r.width / 2);
        const on = (x, y) => { const e = document.elementFromPoint(x, y);
          return !!(e && e.classList.contains('skribl-inline-poster')); };
        let l = null, rr = null, tp = null, bt = null;
        for (let x = Math.ceil(r.left); x < r.right; x++) if (on(x, cy)) { l = x; break; }
        for (let x = Math.floor(r.right) - 1; x >= r.left; x--) if (on(x, cy)) { rr = x; break; }
        for (let y = Math.ceil(r.top); y < r.bottom; y++) if (on(cx, y)) { tp = y; break; }
        for (let y = Math.floor(r.bottom) - 1; y >= r.top; y--) if (on(cx, y)) { bt = y; break; }
        return { n: n, w: box.getAttribute('data-skribl-w'),
                 h: box.getAttribute('data-skribl-h'),
                 box: [Math.round(r.width), Math.round(r.height)],
                 painted: l === null ? null
                   : [l - Math.round(r.left), tp - Math.round(r.top),
                      rr - l + 1, bt - tp + 1] }; }"""

    CANVAS_JS = """(n) => {
        const t = document.querySelectorAll('.tile')[n];
        const box = t.querySelector('.skribl-inline');
        const cv = t.querySelector('.skribl-inline-canvas');
        const br = box.getBoundingClientRect(), cr = cv.getBoundingClientRect();
        return { hidden: cv.hasAttribute('hidden'),
                 rect: [Math.round(cr.left - br.left), Math.round(cr.top - br.top),
                        Math.round(cr.width), Math.round(cr.height)] }; }"""

    # The idle play cue, read three ways at once; see the rows that use it.
    CUE_JS = """() => {
        const t = document.querySelector('.tile');
        const box = t && t.querySelector('.skribl-inline');
        const veil = t && t.querySelector('.skribl-inline-veil');
        const disc = t && t.querySelector('.skribl-inline-play');
        if (!box || !veil || !disc) return { missing: true };
        const r = disc.getBoundingClientRect();
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top + r.height / 2);
        const hit = document.elementFromPoint(cx, cy);
        return {
          shownVeil: getComputedStyle(veil).display,
          shownDisc: getComputedStyle(disc).display,
          opacity: +getComputedStyle(veil).opacity,
          w: Math.round(r.width), h: Math.round(r.height),
          playing: box.classList.contains('is-playing'),
          bare: box.classList.contains('is-bare'),
          underIt: !!(hit && box.contains(hit)) }; }"""
    # AND THE DRAWING STILL SAYS IT MOVES. `is-bare` means the host supplies
    # the TRANSPORT; it briefly meant the host supplies the idle veil too, and
    # the veil is not a control -- it is the wash and the play triangle that
    # tell a person a still picture is a recording. The first screenshot of
    # direction B was 24 black rectangles under 24 neat footers.
    #
    # NOT ASSERTED FROM THE RECT ALONE (a rect is not a paint, and this tree
    # has been fooled by one before). The veil is pointer-events: none, so
    # elementFromPoint cannot return it and cannot be the whole instrument
    # either. Three facts together: the disc is DISPLAYED, the veil is not
    # transparent, and the point it is drawn at is inside this tile's own
    # player rather than behind the footer or the next card.
    _cue = _pa.evaluate(CUE_JS)
    check("an idle card still shows the play cue over the drawing",
          not _cue.get("missing") and _cue["shownVeil"] != "none"
          and _cue["shownDisc"] != "none" and _cue["opacity"] > 0.5
          and _cue["w"] >= 40 and _cue["h"] >= 40 and _cue["underIt"],
          f"{_cue} — `is-bare` takes the buttons, never the affordance: "
          f"without it a card is a black rectangle that looks broken")
    check("...and it is the BARE card being measured, not a card without one",
          not _cue.get("missing") and _cue["bare"] and not _cue["playing"],
          f"{_cue} — a card that never went bare would pass the row above "
          f"while saying nothing about the class that hid the veil")

    # ---- THE IDLE POSTER IS THE DRAWING, NOT THE CARD AROUND IT (v309) ----
    #
    # A tile shows the share card until somebody presses play, and the card
    # CONTAINS the drawing: a 4:3 drawing sits in a 656px picture in the middle
    # of a 1200px card, so the old band crop left 110px of card ground and the
    # card's own plate border on each side. A picture inside a frame inside a
    # card, on every tile (owner: "fix the share card bands too").
    #
    # ASSERTED AS AGREEMENT WITH THE CANVAS, not against remembered numbers.
    # The claim worth pinning is not "the poster is 284px wide", which changes
    # with the column width; it is that the poster lands where the drawing will
    # -- so the measurement is taken twice on the same tile, idle and playing,
    # and the two are compared. A band crop fails this by a mile: it paints the
    # full width of the box.
    _frame = _pa.evaluate(FRAME_JS)
    check("the tile knows the drawing's size, so there is something to frame",
          _frame["w"] and _frame["h"],
          f"{_frame} \u2014 without data-skribl-w/h the component keeps the band "
          f"crop, and every row below would be measuring the old behaviour")
    _pa.evaluate("(n) => document.querySelectorAll('.tile')[n]"
                 ".querySelector('.skfull-play').click()", _frame["n"])
    _pa.wait_for_timeout(1200)
    _cv = _pa.evaluate(CANVAS_JS, _frame["n"])
    check("...and the canvas is up, so there is something to compare it to",
          not _cv["hidden"] and _cv["rect"][2] > 0 and _cv["rect"][3] > 0,
          f"{_cv} \u2014 a hidden canvas has a zero rect and everything agrees "
          f"with nothing")
    _dev = ([abs(a - b) for a, b in zip(_frame["painted"], _cv["rect"])]
            if _frame["painted"] else None)
    # The tolerance is the PLATE: fitPoster insets the clip by PLATE_LW so the
    # card's accent hairline does not survive into the tile, which costs the
    # drawing its outermost card pixel on each edge. At tile size that is 2-3
    # device pixels, and it is the only difference there should be.
    check("the idle poster is painted where the drawing will be, not where the card is",
          _frame["painted"] and _dev and max(_dev) <= 6,
          f"poster painted {_frame['painted']} against canvas {_cv['rect']}, "
          f"worst edge off by {max(_dev) if _dev else 'n/a'}px \u2014 the band crop "
          f"paints the whole box width and fails this by ~{_frame['box'][0] - _cv['rect'][2]}px")
    # PUT THE TILE BACK. The rows above had to press play to have a canvas to
    # compare against, and the block below presses play itself and asserts the
    # result is 'playing' -- on a tile already running, that click is a pause.
    _pa.evaluate("""(n) => { const t = document.querySelectorAll('.tile')[n];
        const pl = (t.querySelector('.skribl-inline') || {})._skriblInline;
        if (pl) { pl.pause(); pl.seek(0); } }""", _frame["n"])
    _pa.wait_for_timeout(300)

    # THE CARD'S FOOTER DRIVES THE PLAYER, the same way the full-screen bar
    # does and for the same reason: a control that keeps its own state lies
    # the moment anything else moves the thing it is about.
    _pa.evaluate("() => document.querySelector('.tile .skfull-play').click()")
    _pa.wait_for_timeout(700)
    _fdrive = _pa.evaluate("""() => {
        const t = document.querySelector('.tile');
        const pl = (t.querySelector('.skribl-inline') || {})._skriblInline;
        const f = t.querySelector('.skfull-card');
        if (!pl) return { noPlayer: true };
        const st = pl.state();
        const loopBefore = pl.looping();
        f.querySelector('.skfull-loop').click();
        return { state: st.state, loaded: st.loaded,
                 loopBefore: loopBefore, loopAfter: pl.looping(),
                 lit: f.querySelector('.skfull-loop').classList.contains('on') }; }""")
    check("pressing play on a card plays THAT card's drawing",
          not _fdrive.get("noPlayer") and _fdrive["state"] == "playing"
          and _fdrive["loaded"],
          f"{_fdrive} \u2014 the footer holds no state of its own; it asks the "
          f"player, which is what keeps it honest when a replay ends by itself")
    check("...and repeat reads what is true of the player",
          not _fdrive.get("noPlayer")
          and _fdrive["loopAfter"] != _fdrive["loopBefore"]
          and _fdrive["lit"] == _fdrive["loopAfter"], str(_fdrive))

    # A CAPTION A READER CANNOT GET TO IS WORSE THAN ONE THAT TAKES A HOVER,
    # and that was the whole argument for `opacity` over `display` when this
    # was a scrim. A line clamp keeps it: the text is in the tree whole, and
    # a reader that does not paint is not affected by a limit on lines.
    _a11ycap = _pa.evaluate("""() => {
        const cap = document.querySelector('.tile .tcap');
        const cs = getComputedStyle(cap);
        return { display: cs.display, visibility: cs.visibility,
                 hidden: cap.hasAttribute('hidden'),
                 chars: (cap.textContent || '').length }; }""")
    check("the clamped caption is still the WHOLE text a screen reader reaches",
          _a11ycap["display"] != "none" and _a11ycap["visibility"] != "hidden"
          and not _a11ycap["hidden"]
          and _a11ycap["chars"] == len('a description long enough to need more than two lines on a card this wide, so that the clamp has something to fold and the toggle has something to unfold, which a one-line caption cannot show'),
          f"{_a11ycap} \u2014 a clamp hides lines, never characters; truncating the"
          f" TEXT would read as a shorter description rather than a folded one")

    _pa.close()
    _ba.close()


# ---------------------------------------------------------------------------
# FULL SIZE ON A PHONE (v308)
#
# WHAT IS SIMULATED AND WHY IT HAS TO BE. iOS Safari implements the Fullscreen
# API for `<video>` and nothing else, and this page did the right thing with
# that answer -- it hid the control, on the rule that a button which cannot
# work should not be on screen. The result was the owner's "i am not seeing
# full screen on gallery or library on iphone": the device where a drawing is
# smallest was the device with no way to make it bigger.
#
# The harness browser HAS the API, so the phone's case is unreachable without
# taking it away. The init script removes exactly what lib/immersive.js probes
# -- both `*fullscreenEnabled` flags and both request methods -- before any
# page script runs. That is the real fork, not an approximation of it.
print("\nGALLERY — full size on a browser with no Fullscreen API")
with sync_playwright() as _spi:
    _bi = _spi.chromium.launch()
    _pi = _bi.new_context().new_page()
    _pi.set_viewport_size({"width": 390, "height": 844})
    # STATEMENTS, NOT A FUNCTION EXPRESSION. add_init_script takes script
    # SOURCE and runs it; `() => {...}` is source that evaluates to a function
    # nobody calls, so the first draft neutered nothing and the page kept its
    # API. It still went green on every row below -- because headless Chromium
    # REJECTS requestFullscreen without a trusted gesture, and the rejection
    # path lands in the same fallback. Two ways in, one of them tested by
    # accident; the flag check above is what caught it.
    _pi.add_init_script("""
      try { Object.defineProperty(document, 'fullscreenEnabled',
        { configurable: true, get: function () { return false; } }); } catch (e) {}
      try { Object.defineProperty(document, 'webkitFullscreenEnabled',
        { configurable: true, get: function () { return false; } }); } catch (e) {}
      try { delete Element.prototype.requestFullscreen; } catch (e) {}
      try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {}
    """)
    # Newest first, so this is tile 0 and the rows below know which drawing
    # they are watching rather than taking whatever the grid happened to hold.
    _slow = slow_pad_post("a pen you can follow")
    browsing.goto(_pi, BASE, "/gallery")
    _pi.wait_for_timeout(2200)

    _has = _pi.evaluate("""() => ({
        api: !!(document.fullscreenEnabled || document.webkitFullscreenEnabled),
        tiles: document.querySelectorAll('.tile').length,
        buttons: document.querySelectorAll('.tile .skfull-card .skfull-full').length,
        exits: document.querySelectorAll('.tileExit').length })""")
    check("the simulation is real: this page believes it has no Fullscreen API",
          _has["api"] is False,
          f"{_has} \u2014 with the API still present every row below would be "
          f"testing the path that already worked")
    check("...and every tile still offers full size",
          _has["tiles"] > 0 and _has["buttons"] == _has["tiles"],
          f"{_has} \u2014 this is the iPhone, where the control used to be absent")
    check("...each with a way back out inside the drawing",
          _has["exits"] == _has["tiles"],
          f"{_has} \u2014 in the fallback the page is still the page, and nothing "
          f"but this button leaves it: no Escape from the browser, no system gesture")

    _pi.evaluate("() => document.querySelector('.tile .skfull-card .skfull-full').click()")
    _pi.wait_for_timeout(700)
    _big = _pi.evaluate("""() => {
        const st = document.querySelector('.tile .tileStage');
        const r = st.getBoundingClientRect();
        const box = st.querySelector('.skribl-inline');
        return { w: Math.round(r.width), h: Math.round(r.height),
                 vw: window.innerWidth, vh: window.innerHeight,
                 left: Math.round(r.left), top: Math.round(r.top),
                 pinned: getComputedStyle(st).position,
                 immersive: !!(box && box.classList.contains('is-immersive')),
                 locked: getComputedStyle(document.documentElement).overflow,
                 exitSeen: getComputedStyle(st.querySelector('.tileExit')).display }; }""")
    # MEASURED AGAINST THE VIEWPORT, not against the class. `position: fixed`
    # is resolved against the nearest ancestor with a transform, a filter or
    # containment rather than against the viewport, so a tile inside a
    # transformed card would carry the class and sit in a 300px box. The only
    # honest question is how big it actually got.
    check("pressing it puts the drawing over the whole viewport",
          _big["pinned"] == "fixed" and _big["left"] == 0 and _big["top"] == 0
          and abs(_big["w"] - _big["vw"]) <= 1 and abs(_big["h"] - _big["vh"]) <= 2,
          f"{_big} \u2014 a transformed or contained ancestor turns `fixed` into "
          f"`absolute` and this is what catches it")
    check("...the component is told what immersive means for its own parts",
          _big["immersive"] is True,
          f"{_big} \u2014 the page says WHEN and inlineplayer.css says WHAT")
    check("...the page behind it cannot scroll",
          _big["locked"] == "hidden",
          f"{_big} \u2014 somebody else's post sliding past under a full-size "
          f"drawing is worse than no full size at all")
    check("...and the way out is on screen",
          _big["exitSeen"] == "grid", str(_big))

    # ---- THE PEN IS ON THE LINE (v308) ------------------------------------
    # Owner's screenshot, gallery full screen: the nib sat up and to the left
    # of the stroke it was drawing. setNib() mapped the point through
    # canvas.getBoundingClientRect(), which IS the drawing in a tile
    # (width/height auto under max-width 100%) and is the whole container in
    # immersive (width/height 100% + object-fit: contain, bitmap letterboxed
    # inside). So the nib was spread across the screen while the line was drawn
    # across the contained box.
    #
    # ASSERTED AGAINST THE CONTENT BOX, DERIVED FROM THE ASPECT RATIO -- which
    # is what `contain` is DEFINED to do, not a copy of what the code does. A
    # test that recomputed the implementation's formula would agree with it
    # whatever it said.
    #
    # THE PROBE PROVES ITSELF FIRST. On a 390x844 phone a 16:9 drawing is
    # letterboxed to about 219px of a 844px box, so the element box is ~625px
    # taller than the content box and the two predictions are nowhere near each
    # other. If that gap were small the rows below could not tell a fixed nib
    # from a broken one, so the gap is asserted before the nib is.
    _nib = _pi.evaluate("""async () => {
        const st = document.querySelector('.tile .tileStage');
        const cv = st.querySelector('.skribl-inline-canvas');
        const nb = st.querySelector('.skribl-inline-nib');
        if (!cv || !nb) return { missing: !cv ? 'canvas' : 'nib' };
        const ar = cv.width / cv.height;            /* the drawing's own shape */
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));
        const out = { ar: Math.round(ar * 100) / 100, samples: [], outside: 0,
                      gap: 0, hidden: 0 };
        for (let i = 0; i < 14; i++) {
          await sleep(120);
          const cr = cv.getBoundingClientRect();
          const nr = nb.getBoundingClientRect();
          if (!cr.width || !cr.height) continue;
          /* the content box `contain` paints into */
          const cw = Math.min(cr.width, cr.height * ar);
          const ch = Math.min(cr.height, cr.width / ar);
          const cx = cr.left + (cr.width - cw) / 2;
          const cy = cr.top + (cr.height - ch) / 2;
          /* BEFORE the visibility gate: the probe's own validity is a fact
             about the LAYOUT and must be measurable even on a frame where the
             nib happens to be hidden. Measuring it after cost a run. */
          out.gap = Math.max(out.gap, Math.round(cr.height - ch), Math.round(cr.width - cw));
          if (getComputedStyle(nb).opacity === '0') { out.hidden++; continue; }
          const nx = nr.left + nr.width / 2, ny = nr.top + nr.height / 2;
          const ok = nx >= cx - 2 && nx <= cx + cw + 2 && ny >= cy - 2 && ny <= cy + ch + 2;
          if (!ok) out.outside++;
          out.samples.push([Math.round(nx - cx), Math.round(ny - cy),
                            Math.round(cw), Math.round(ch), ok ? 1 : 0]);
        }
        return out; }""")
    check("the probe can tell a fixed nib from a broken one",
          not _nib.get("missing") and _nib["gap"] >= 200,
          f"{_nib.get('gap')}px between the element box and the content box "
          f"\u2014 under a letterbox this thin the two mappings agree and the "
          f"row below would pass on the defect")
    check("the nib is drawn ON the drawing, not across the whole screen",
          not _nib.get("missing") and len(_nib["samples"]) >= 4
          and _nib["outside"] == 0,
          f"{_nib.get('outside')} of {len(_nib.get('samples', []))} samples "
          f"outside the drawing\u2019s content box ({_nib.get('hidden')} frames "
          f"with the nib hidden); [dx, dy, w, h, ok] = "
          f"{_nib.get('samples', [])[:6]}")

    # ---- ONE BAR, AND IT IS THE PROFILE'S BAR (v308) ----------------------
    # Owner, holding two screenshots of the same feature: "the two full screens
    # should look identical with controls present on the bottom. all the stuff
    # should be on the bottom." They diverged because each page built its own,
    # so neither builds one now -- lib/fullbar.js does, and both call it.
    #
    # THE CONTROL SET IS SPELLED OUT rather than counted. A count passes on the
    # wrong six. verify_library asserts the SAME list against the profile's
    # stage, so a change to the module reddens both together and a change to
    # one PAGE reddens only that one, which is the distinction worth keeping.
    _bar = _pi.evaluate("""() => {
        const st = document.querySelector('.tile .tileStage');
        const bar = st.querySelector('.skfull');
        const box = st.querySelector('.skribl-inline');
        const marks = st.querySelector('.tileMarks');
        if (!bar) return { missing: true };
        const br = bar.getBoundingClientRect(), sr = st.getBoundingClientRect();
        return {
          shown: getComputedStyle(bar).display,
          btns: [...bar.querySelectorAll('.skfull-btn')].map(b => b.className.split(' ')[1]),
          bare: !!(box && box.classList.contains('is-bare')),
          ownControls: box ? getComputedStyle(box.querySelector('.skribl-inline-controls')).display : '?',
          ownDur: box ? getComputedStyle(box.querySelector('.skribl-inline-dur')).display : '?',
          marks: marks ? getComputedStyle(marks).display : 'no-marks',
          atBottom: Math.round(sr.bottom - br.bottom),
          scrubOwnRow: (() => {
            const t = bar.querySelector('.skfull-track');
            const p = bar.querySelector('.skfull-play');
            return !!(t && p && t.getBoundingClientRect().bottom
                      <= p.getBoundingClientRect().top + 1);
          })(),
          title: (bar.querySelector('.skfull-title') || {}).textContent }; }""")
    check("full screen carries one bar, at the bottom, with the agreed controls",
          not _bar.get("missing") and _bar["shown"] == "flex"
          and _bar["btns"] == ['skfull-restart', 'skfull-play', 'skfull-loop', 'skfull-mute',
                'skfull-rate', 'skfull-exit']
          and _bar["atBottom"] <= 1, str(_bar))
    check("...the component's own transport yields to it",
          not _bar.get("missing") and _bar["bare"]
          and _bar["ownControls"] == "none" and _bar["ownDur"] == "none",
          f"{_bar} \u2014 two transports on one drawing is the screenshot this "
          f"change is about")
    check("...nothing is drawn over the art but the way out",
          not _bar.get("missing") and _bar["marks"] == "none",
          f"{_bar} \u2014 'which of these is which' is a question you have in a "
          f"GRID, and the owner photographed a pen and a speaker over a "
          f"full-screen drawing")
    check("...and the scrubber has its own row above the buttons",
          not _bar.get("missing") and _bar["scrubOwnRow"],
          f"{_bar} \u2014 squeezed between the buttons it is a 6px target on a "
          f"phone, which is not a target")

    # THE BAR DRIVES THE PLAYER, rather than keeping a state of its own. Pause
    # through the bar and the PLAYER has to be paused, not merely the icon.
    _pi.evaluate("() => document.querySelector('.skfull-play').click()")
    _pi.wait_for_timeout(400)
    _drive = _pi.evaluate("""() => {
        const st = document.querySelector('.tile .tileStage');
        const pl = st.querySelector('.skribl-inline')._skriblInline;
        const bar = st.querySelector('.skfull');
        const before = pl.state().state;
        const r0 = pl.rate();
        bar.querySelector('.skfull-rate').click();
        const r1 = pl.rate();
        const label = bar.querySelector('.skfull-rate').textContent;
        bar.querySelector('.skfull-loop').click();
        return { paused: before, r0: r0, r1: r1, label: label,
                 loop: pl.looping(),
                 lit: bar.querySelector('.skfull-loop').classList.contains('on') }; }""")
    check("the bar drives the player: pause pauses it, speed changes its rate",
          _drive["paused"] == "paused" and _drive["r0"] == 1
          and _drive["r1"] == 2 and _drive["label"] == "2\u00d7",
          f"{_drive} \u2014 a bar that moved its own icon and left the clock alone "
          f"is the defect this could most easily have shipped with")
    check("...and repeat reads what is TRUE, not what the button would do",
          _drive["lit"] == _drive["loop"],
          f"{_drive} \u2014 lit is the resting state, the same reading the "
          f"component's own loop button uses")

    _pi.evaluate("() => document.querySelector('.tile .tileExit').click()")
    _pi.wait_for_timeout(600)

    # ...AND THE SAME FORMULA IN A TILE, which is the claim the fix actually
    # makes: one mapping for both sizing models. In a tile the element box IS
    # the drawing, so the content box and the element box coincide and NO
    # mutation of setNib can be caught here -- the two mappings agree by
    # construction. Said plainly because a reader could otherwise take this row
    # for a second pin on the same defect. What it guards is the REDUCTION: if
    # the formula is ever "simplified" in a way that stops collapsing to the
    # element box when the scales match, a tile's pen goes wrong and this is
    # what notices.
    _pi.evaluate("() => { const b = document.querySelector('.tile .skribl-inline');"
                 " if (b && b._skriblInline) b._skriblInline.play(); }")
    _tile = _pi.evaluate("""async () => {
        const st = document.querySelector('.tile .tileStage');
        const cv = st.querySelector('.skribl-inline-canvas');
        const nb = st.querySelector('.skribl-inline-nib');
        if (!cv || !nb) return { missing: true };
        const ar = cv.width / cv.height;
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));
        const out = { samples: 0, outside: 0, gap: 0 };
        for (let i = 0; i < 10; i++) {
          await sleep(120);
          const cr = cv.getBoundingClientRect(), nr = nb.getBoundingClientRect();
          if (!cr.width || !cr.height) continue;
          const cw = Math.min(cr.width, cr.height * ar);
          const ch = Math.min(cr.height, cr.width / ar);
          out.gap = Math.max(out.gap, Math.round(cr.height - ch), Math.round(cr.width - cw));
          if (getComputedStyle(nb).opacity === '0') continue;
          const cx = cr.left + (cr.width - cw) / 2, cy = cr.top + (cr.height - ch) / 2;
          const nx = nr.left + nr.width / 2, ny = nr.top + nr.height / 2;
          out.samples++;
          if (!(nx >= cx - 2 && nx <= cx + cw + 2 && ny >= cy - 2 && ny <= cy + ch + 2))
            out.outside++;
        }
        return out; }""")
    check("...and on a tile, where the element box IS the drawing",
          not _tile.get("missing") and _tile["samples"] >= 3
          and _tile["outside"] == 0 and _tile["gap"] <= 2,
          f"{_tile} \u2014 a gap above zero here would mean the tile has started "
          f"letterboxing too, and this row would be measuring the other case")
    _back = _pi.evaluate("""() => {
        const st = document.querySelector('.tile .tileStage');
        const box = st.querySelector('.skribl-inline');
        return { pinned: getComputedStyle(st).position,
                 locked: getComputedStyle(document.documentElement).overflow,
                 immersive: !!(box && box.classList.contains('is-immersive')),
                 w: Math.round(st.getBoundingClientRect().width) }; }""")
    check("leaving puts the tile back, the scroll back, and the component back",
          _back["pinned"] != "fixed" and _back["locked"] != "hidden"
          and _back["immersive"] is False and _back["w"] < 390,
          f"{_back} \u2014 a page left locked is a page nobody can use again")
    _pi.close()
    _bi.close()

passed = sum(1 for r in results if r[0])
print("\n" + "=" * 62 + f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
