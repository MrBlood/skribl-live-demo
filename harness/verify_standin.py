#!/usr/bin/env python3
"""The skribls.net stand-in, on the demo at /host.

The owner, looking on the live demo's /feed for Add to post's gallery tick
(Nov 10): /feed never asks, because it posts everything publicly, and the host
that does ask (examples/host_app, compose=1&gallery=1) ran only on a laptop.
"I want the stand-in." So app.py mounts it at /host, beside the demo, in the
same process, and this suite asks what that promises, through the demo's own
server:

  1. IT IS THERE, A SITE OF ITS OWN: /host is the Example host's page, and its
     Skribl is under /host/skribl.
  2. ITS COOKIES ARE ITS OWN: every cookie it sets is named skribl_host_..., its
     session only on /host, so its pretend sign-in never overwrites the demo's
     session (the demo keeps one: its demo identity's mark).
  3. ADD TO POST ASKS: its composer opens the Pad under /host with
     compose=1&gallery=1, the gallery tick there and off, the gallery caption
     opening once it is ticked (a phone).
  4. ITS POSTS ARE ITS OWN: a post made there is in its own feed, the ticked
     drawing on its own Skribls page, and not in the demo's public list (its
     own database).
  5. MORE ON ITS SKRIBLS PAGE asks only for a next page: not on screen when
     there is none, and a press then adds nothing (the owner's "it just adds
     another copy", on the live stand-in).
  6. NO TEXT FIELD ON IT MAKES A PHONE ZOOM: every one at least 16px.

What the stand-in does as a host is verify_example's, which boots it on its
own; this suite is the mount. SKRIBL_STAND_IN=0 leaves it out of the demo, and
then every row here is red, which is how it was calibrated.
"""
import math
import os
import sys
import time

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001").rstrip("/")
HOST = BASE + "/host"
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the stand-in is mounted.")
    raise SystemExit(77)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)


def draw(pg, box, turns=3, n=60):
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        t = i / float(n - 1)
        a = t * turns * 2 * math.pi
        r = 10 + t * min(box["width"], box["height"]) * 0.33
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r)
        pg.wait_for_timeout(12)
    pg.mouse.up()


def demo_ids(pg):
    """Every public id in the demo's own list (its first page holds them all here)."""
    r = pg.request.get(BASE + "/api/skribls?limit=100")
    return {i.get("id") for i in (r.json().get("items") or [])} if r.ok else None


with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(**PHONE)
    pg = c.new_page()
    errs, set_cookies = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def _cookies(r):
        if not r.url.startswith(HOST):
            return
        for h in r.headers_array():
            if h["name"].lower() == "set-cookie":
                parts = [s.strip() for s in h["value"].split(";")]
                path = next((s.split("=", 1)[1] for s in parts[1:] if s.lower().startswith("path=")), "/")
                set_cookies.append((parts[0].split("=", 1)[0], path))
    pg.on("response", _cookies)

    print("\nSTAND-IN 1 — it is there, a site of its own")
    before = demo_ids(pg)
    resp = pg.goto(HOST + "/")
    title = pg.title()
    assets = pg.evaluate("() => [...document.querySelectorAll('script[src], link[href]')]"
                         ".map(e => e.getAttribute('src') || e.getAttribute('href'))"
                         ".filter(u => u.indexOf('/skribl/') >= 0)")
    there = check("the stand-in answers at /host, the Example host's own page, its Skribl under /host/skribl",
                  resp is not None and resp.status == 200 and "Example host" in title
                  and bool(assets) and all(u.startswith("/host/skribl/") for u in assets),
                  f"status {resp.status if resp else None}, title {title!r}, Skribl's files {assets[:3]}")
    if not there:   # nothing further can be asked of a stand-in that is not there
        c.close()
        b.close()
        summarise_and_exit()

    print("\nSTAND-IN 3 — Add to post asks")
    pg.select_option("select[name=uid]", index=0)
    pg.click("button:has-text('Sign in')")
    pg.wait_for_timeout(800)
    pg.click("#padBtn")
    pg.wait_for_function("() => { const f = document.getElementById('padFrame'); const w = f && f.contentWindow;"
                         " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }", timeout=30000)
    pg.wait_for_timeout(800)
    src = pg.evaluate("() => document.getElementById('padFrame').getAttribute('src')")
    fr = pg.frame_locator("#padFrame")
    draw(pg, fr.locator("#canvas").bounding_box())
    pg.wait_for_timeout(400)
    fr.locator("#recordBtn").click()
    pg.wait_for_timeout(700)
    fr.locator("#postBtn").click()
    pg.wait_for_timeout(1200)
    SHEET = """() => { const box = document.getElementById('postPublicInput'), cap = document.getElementById('postCaptionInput');
        return { box: !!box, on: box ? box.checked : null, caption: !!(cap && cap.getClientRects().length) }; }"""
    off = fr.locator("body").evaluate(SHEET)
    if off["box"]:   # a sheet that does not ask has no tick to press; the row says so
        fr.locator("label.post-check").click()
        pg.wait_for_timeout(900)
    on = fr.locator("body").evaluate(SHEET)
    check("Add to post asks: the Pad opens under /host with compose=1&gallery=1, the gallery tick there and off,"
          " the gallery caption opening once it is ticked (phone)",
          bool(src) and src.startswith("/host/skribl/") and "compose=1" in src and "gallery=1" in src
          and off["box"] and off["on"] is False and not off["caption"] and on["on"] is True and on["caption"],
          f"the frame {src!r}; off {off}; ticked {on}")

    print("\nSTAND-IN 4 — its posts are its own")
    word = "stand-in %d" % int(time.time() * 1000)
    fr.locator("#postSubmitBtn").click()
    pg.wait_for_timeout(3000)
    pg.fill("#body", word)
    pg.click("#postBtn")
    pg.wait_for_url(HOST + "/", timeout=20000)
    pg.wait_for_timeout(1500)
    sid = pg.evaluate("""(w) => { const a = [...document.querySelectorAll('article.post')].find(x => x.textContent.indexOf(w) >= 0);
        const box = a && a.querySelector('[data-skribl-id]'); return box ? box.getAttribute('data-skribl-id') : null; }""", word)
    pg.goto(HOST + "/skribls")
    try:
        pg.wait_for_selector(f'[data-skribl-id="{sid}"]', timeout=15000)
        tiled = True
    except Exception:
        tiled = False
    after = demo_ids(pg)
    check("a post made there is the stand-in's: in its own feed with its drawing, the ticked drawing on its own"
          " Skribls page, and not in the demo's public list",
          bool(sid) and tiled and before is not None and after is not None and sid not in after and after == before,
          f"its drawing {sid!r}; on its Skribls page {tiled}; the demo's list {len(before or [])} before,"
          f" {len(after or [])} after, holding it {bool(after) and sid in after}")

    print("\nSTAND-IN 5 — More on the Skribls page")
    # The owner, on the live stand-in (Nov 10): "When I go to skribls and push
    # more when there is only one skribl, it just adds another copy. It will do
    # this repeatedly." The listing had no next page, the script set
    # more.hidden, `.sk-more { display:block }` beat the browser's own [hidden]
    # rule, and a press with no cursor fetched page one again and appended it.
    # Two rows, one per part of the fix: More is not there without a next
    # page, and a press of it then (a script's, a stale tap's) adds nothing.
    pg.wait_for_timeout(800)
    page1 = pg.request.get(HOST + "/skribl/api/skribls?limit=24&sort=new").json()
    shown = pg.evaluate("() => { const m = document.getElementById('skMore');"
                        " return { rects: m ? m.getClientRects().length : -1, hiddenAttr: m ? m.hidden : null }; }")
    check("More is not on the Skribls page when the listing has no next page",
          page1.get("next_cursor") is None and shown["hiddenAttr"] is True and shown["rects"] == 0,
          f"next_cursor {page1.get('next_cursor')!r}; More hidden {shown['hiddenAttr']}, painted boxes {shown['rects']}")
    TILES = "() => document.querySelectorAll('#skGrid .sk-card').length"
    n0 = pg.evaluate(TILES)
    for _ in range(2):
        pg.evaluate("() => document.getElementById('skMore').click()")
        pg.wait_for_timeout(1500)
    n1 = pg.evaluate(TILES)
    check("a press of More with no next page adds nothing (no second copy of page one)",
          n0 >= 1 and n1 == n0, f"tiles {n0} before two presses, {n1} after")

    print("\nSTAND-IN 2 — its cookies are its own")
    jar = sorted((k["name"], k["path"]) for k in c.cookies())
    named = sorted(set(set_cookies))
    session = [path for name, path in named if name == "skribl_host_session"]
    check("its cookies are its own: every one it sets is named skribl_host_..., its session only on /host,"
          " so the demo's own session is never touched",
          bool(named) and all(n.startswith("skribl_host_") for n, _ in named) and session and all(s == "/host" for s in session)
          and all(n.startswith("skribl_host_") for n, _ in jar),
          f"set {named}; the browser holds {jar}")

    print("\nSTAND-IN 6 — no text control makes a phone zoom")
    # A text control under 16px makes iOS magnify the page when it is tapped
    # (WORKING-AGREEMENTS; verify_a11y 11b asks it of Skribl's own pages).
    # The look-over found the stand-in's sign-in picker and its composer's
    # "Say something" box at the page's 15px. Read on a touch phone, signed
    # out and signed in, on every page of the host, fields built later too.
    FIELDS = """() => [...document.querySelectorAll('input, textarea, select')].filter(e => {
        const t = (e.type || '').toLowerCase();
        return !['hidden', 'checkbox', 'radio', 'range', 'button', 'submit', 'reset', 'color', 'file', 'image'].includes(t);
      }).map(e => [location.pathname + ' ' + (e.id || e.name || e.tagName.toLowerCase()), parseFloat(getComputedStyle(e).fontSize)])"""
    c2 = b.new_context(**PHONE)
    p2 = c2.new_page()
    seen = []
    p2.goto(HOST + "/")
    seen += p2.evaluate(FIELDS)
    p2.select_option("select[name=uid]", index=0)
    p2.click("button:has-text('Sign in')")
    p2.wait_for_timeout(800)
    for path in ("/", "/skribls", "/posts/1"):
        p2.goto(HOST + path)
        p2.wait_for_timeout(600)
        seen += p2.evaluate(FIELDS)
    small = [f"{k} {v:g}px" for k, v in seen if v < 16]
    check("every text field on the stand-in is at least 16px, so a phone never zooms on a tap",
          len(seen) >= 3 and not small, f"{len(seen)} fields read; under 16px: {small}")
    c2.close()
    check("no page errors on the stand-in", not errs, "; ".join(errs[:2]))
    c.close()
    b.close()

summarise_and_exit()
