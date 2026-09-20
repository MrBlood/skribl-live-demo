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

passed = sum(1 for r in results if r[0])
print("\n" + "=" * 62 + f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
