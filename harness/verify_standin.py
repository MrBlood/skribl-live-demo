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
  5. LOAD MORE ON ITS SKRIBLS PAGE asks only for a next page: not on screen
     when there is none, and a press then adds nothing (the owner's "it just
     adds another copy", on the live stand-in; Skribl's own Load more since
     the page became Skribl's Gallery section).
  6. NO TEXT FIELD ON IT MAKES A PHONE ZOOM: every one at least 16px.
  7. ITS LOOK: it follows the device, light or dark; every word on it reads
     at 4.5:1 on what is painted behind it; and the Pad has the whole screen,
     its own close the way back.

And, since its Skribls page holds Skribl's own Gallery section (the owner's B,
after v330: "one gallery, two doors"):

  8. THE SAME CARD ON BOTH DOORS: one drawing, posted to the demo and to the
     stand-in alike, is pixel for pixel the same card (and New / Hot the same
     bar) on /gallery and on /host/skribls, phone and desk, dark and light.
  9. NOTHING LEAKS OUT: the host's own page (its header, its tabs, its
     buttons, <html> and <body>) computes the same styles and keeps the same
     markup with the section's files as without them.
 10. A REPORT FROM THE HOST IS TAKEN: ⋯, Report, a reason, Send, and the
     server answers 202; the card shows it was reported.
 11. "FROM A POST" leads to the post a drawing was posted in, and only there:
     not on a drawing made in the app, and never on the demo's own /gallery,
     which knows of no posts.
 12. THE EMPTY GALLERY NAMES ITS DOOR'S TICK: the words of the tick that door
     shows (a host's composer's, or Skribl's own Post sheet's), and the
     Library only on Skribl's own page.

What the stand-in does as a host is verify_example's, which boots it on its
own; this suite is the mount. SKRIBL_STAND_IN=0 leaves it out of the demo, and
then every row here is red, which is how it was calibrated.
"""
import io
import json
import math
import os
import re
import sys
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

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
ROOT = Path(__file__).resolve().parents[1]
TAG = "standin %d" % int(time.time() * 1000)

# ---- the same card on both doors (section 8) --------------------------------
# Two pixels of a drawing at 2x, phone and desk, as the owner sees them.
SCREENS = {"phone": dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True),
           "desk": dict(viewport={"width": 1280, "height": 860}, device_scale_factor=2)}
# Both doors say the same age for a drawing posted a second apart: three days on.
LATER = "(() => { const real = Date.now; Date.now = () => real() + 3 * 86400000; })();"
# WHAT IS COMPARED IS THE ELEMENT ITSELF. Everything around it is hidden (its
# own subtree is untouched), and it is pinned at the same spot on both pages at
# the width it had where it sat. The same spot matters: a gradient's dither and
# an icon's edges follow the screen's own pixels, and the host's card sat at a
# fractional y on a phone (465.297px), so in place every pixel of it differed
# by a hair, the same card or not. And a LAYER OF ITS OWN on both pages
# (will-change): whether a pinned card got one otherwise depended on what else
# was on the page. After the suite's own posts, the phone's card was drawn from
# another origin on one door, its avatar's dither and its corners 404 pixels
# apart, while the same card on a page of two drawings matched to the pixel.
PIN = """(sels) => {
  const els = sels.map(s => document.querySelector(s));
  if (els.some(e => !e)) return null;
  const keep = new Set();
  for (const e of els) for (let n = e; n; n = n.parentElement) keep.add(n);
  for (const e of els) for (let n = e; n.parentElement; n = n.parentElement)
    for (const s of n.parentElement.children) if (!keep.has(s)) s.style.visibility = 'hidden';
  scrollTo(0, 0);
  let top = 8; const out = [];
  for (const e of els) {
    const r = e.getBoundingClientRect();
    out.push([r.width, r.height]);
    e.style.cssText += ';position:fixed;left:8px;top:' + top + 'px;margin:0;width:' + r.width + 'px;will-change:transform';
    top += Math.ceil(r.height) + 16;
  }
  return out;
}"""
# A LAYER DRAWN ON ITS OWN IS DRAWN AGAIN, on both pages, before the picture.
# The play pill's words are composited apart from the card (it blurs what is
# under it), and Chromium had kept the host's first raster of them from before
# the page settled: 1624 pixels of their edges differed on a phone, while every
# computed style, the face (Inter SemiBold, both) and every box measured the
# same, and each page drew them the same way run after run. Taking the blur off
# for two frames and putting it back makes the layer anew; with that, 0 differ.
FRESH = """(sels) => new Promise(res => {
  const ps = [];
  for (const s of sels) for (const e of document.querySelectorAll(s + ', ' + s + ' *'))
    if (getComputedStyle(e).backdropFilter !== 'none') ps.push(e);
  ps.forEach(e => { e.style.setProperty('backdrop-filter', 'none'); e.style.setProperty('-webkit-backdrop-filter', 'none'); });
  requestAnimationFrame(() => requestAnimationFrame(() => {
    ps.forEach(e => { e.style.removeProperty('backdrop-filter'); e.style.removeProperty('-webkit-backdrop-filter'); });
    requestAnimationFrame(() => requestAnimationFrame(() => res(ps.length)));
  }));
})"""


def post_public(base, api, title, caption, cookie=None):
    """One public drawing through a Skribl's own API, signed out, the same
    payload whichever door; a site with CSRF on gets its own pair back."""
    jar = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(base + api + "?limit=1", timeout=20).read()
    tok = next((k.value for k in jar if k.name == cookie), "") if cookie else ""
    pts = [{"x": round(408 + math.cos(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "y": round(306 + math.sin(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "color": "#7c5cff", "size": 6 + (i % 5), "t": i * 40, "start": i == 0} for i in range(60)]
    body = {"title": title, "caption": caption, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#101418"}}]}
    req = urllib.request.Request(base + api, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Skribl-CSRF": tok} if tok else {})})
    with op.open(req, timeout=20) as r:
        return json.loads(r.read().decode())["id"]


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

    # SECTION 8's DRAWING, posted now that section 4 has counted the demo's
    # list: one payload, through each door's own Skribl, signed out, so both
    # cards say "Anonymous" and nothing else differs. Its caption runs past
    # two lines, so its "more" is on the card too. On the stand-in it is in no
    # post, which section 11 asks about.
    same_title = TAG + " the same card"
    same_cap = ("Drawn once and posted twice, through each door's own Skribl: the long way round, so this "
                "caption needs its more to be read to the end.")
    demo_same = post_public(BASE, "/api/skribls", same_title, same_cap, cookie="skribl_csrf")
    host_same = post_public(BASE, "/host/skribl/api/skribls", same_title, same_cap, cookie="skribl_host_csrf")

    print("\nSTAND-IN 5 — Load more on the Skribls page")
    # The owner, on the live stand-in (Nov 10): "When I go to skribls and push
    # more when there is only one skribl, it just adds another copy. It will do
    # this repeatedly." The listing had no next page, the script set
    # more.hidden, `.sk-more { display:block }` beat the browser's own [hidden]
    # rule, and a press with no cursor fetched page one again and appended it.
    # The page is Skribl's Gallery section now (after v330, B), and Skribl's
    # own Load more had the second half of the same bug: its press with no
    # cursor fetched page one again too. Two rows, one per part: Load more is
    # not there without a next page, and a press of it then (a script's, a
    # stale tap's) adds nothing.
    pg.wait_for_function("() => document.querySelectorAll('#galleryList > article.tile').length >= 1"
                         " && !document.getElementById('galleryMore').disabled", timeout=15000)
    pg.wait_for_timeout(500)
    page1 = pg.request.get(HOST + "/skribl/api/skribls?limit=24&sort=new").json()
    shown = pg.evaluate("() => { const m = document.getElementById('galleryMore');"
                        " return { rects: m ? m.getClientRects().length : -1, hiddenAttr: m ? m.hidden : null }; }")
    check("Load more is not on the Skribls page when the listing has no next page",
          page1.get("next_cursor") is None and shown["hiddenAttr"] is True and shown["rects"] == 0,
          f"next_cursor {page1.get('next_cursor')!r}; Load more hidden {shown['hiddenAttr']}, painted boxes {shown['rects']}")
    TILES = "() => document.querySelectorAll('#galleryList > article.tile').length"
    n0 = pg.evaluate(TILES)
    for _ in range(2):
        pg.evaluate("() => document.getElementById('galleryMore').click()")
        pg.wait_for_timeout(1500)
    n1 = pg.evaluate(TILES)
    check("a press of Load more with no next page adds nothing (no second copy of page one)",
          n0 >= 1 and n1 == n0, f"cards {n0} before two presses, {n1} after")

    print("\nSTAND-IN 11 — \"From a post\" leads to the post, and only there")
    # The card's link back (gallery.js, from the listing's `source`, which the
    # host's source_resolver says): the drawing posted in section 4 links to
    # that post's own page, the host's /posts/<id>; a drawing in no post says
    # nothing more. The post's id is read off the host's feed, where its
    # article carries it.
    pg.goto(HOST + "/")
    pg.wait_for_timeout(600)
    pid = pg.evaluate("""(sid) => { const a = [...document.querySelectorAll('article.post')]
        .find(x => x.querySelector('[data-skribl-id="' + sid + '"]')); return a ? a.id.replace('post-', '') : null; }""", sid)
    pg.goto(HOST + "/skribls")
    pg.wait_for_function("(sid) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + sid + '\"]')",
                         arg=sid, timeout=15000)
    pg.wait_for_timeout(400)
    links = pg.evaluate("""() => [...document.querySelectorAll('#galleryList > article.tile')].map(t => {
        const a = t.querySelector('a.tfrom'); return [t.getAttribute('data-id'), a ? a.href : null, a ? a.textContent : null]; })""")
    mine = [x for x in links if x[0] == sid]
    others = [x for x in links if x[0] != sid]
    page1 = {i["id"]: i for i in (pg.request.get(HOST + "/skribl/api/skribls?limit=50").json().get("items") or [])}
    check("on the Skribls page, the card of the drawing posted in a post says \"From a post\", linking to that post",
          bool(pid) and mine and mine[0][1] == HOST + "/posts/" + pid and mine[0][2] == "From a post",
          f"its post {pid!r}; its card {mine}")
    check("...and a card whose drawing is in no post says nothing more",
          all(x[1] is None for x in others if not page1.get(x[0], {}).get("source")) and
          any(not page1.get(x[0], {}).get("source") for x in others) if others else False,
          f"{len(others)} other cards: {[x for x in others if x[1]][:3]}")
    if mine and mine[0][1]:
        pg.click(f'#galleryList > article.tile[data-id="{sid}"] a.tfrom')
        pg.wait_for_timeout(1200)
    landed = pg.evaluate("""(sid) => ({ at: location.pathname,
        posts: [...document.querySelectorAll('article.post')].map(a => a.id),
        holds: !!document.querySelector('article.post [data-skribl-id="' + sid + '"]') })""", sid)
    check("...and following it opens that post, its drawing in it",
          bool(pid) and landed["at"] == "/host/posts/" + pid and landed["posts"] == ["post-" + pid] and landed["holds"],
          json.dumps(landed))
    g_links = None
    try:
        pg.goto(BASE + "/gallery")
        pg.wait_for_function("() => document.querySelectorAll('#galleryList > article.tile').length >= 1", timeout=15000)
        pg.wait_for_timeout(600)
        g_links = pg.evaluate("() => [document.querySelectorAll('#galleryList > article.tile').length,"
                              " document.querySelectorAll('#galleryList a.tfrom').length]")
    except Exception as exc:
        g_links = str(exc)[:120]
    check("the demo's own /gallery, which knows of no posts, shows no \"From a post\" on any card",
          isinstance(g_links, list) and g_links[0] >= 1 and g_links[1] == 0, f"cards, links: {g_links}")

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

    print("\nSTAND-IN 7 — its look: both themes, every word readable, the Pad given the screen")
    # The owner's yes on the look-over (Nov 10): the stand-in follows the
    # device as the Pad inside it does; its action buttons wear Skribl's
    # action fill (white on the old #7c5cff was 4.35:1); and the host draws no
    # bar of its own over the Pad, whose own close is the way back.
    READ = """() => {
      const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      const lum = c => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                         return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
      const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
      const ground = e => { for (let n = e; n; n = n.parentElement) { const b = getComputedStyle(n).backgroundColor;
                              if (b && !/rgba\\(0, 0, 0, 0\\)|transparent/.test(b)) return rgb(b); } return [255, 255, 255]; };
      const out = { page: Math.round(lum(ground(document.body)) * 100) / 100, low: [] , read: 0 };
      // The host's own words, and on the Skribls page Skribl's Gallery
      // section's: who and when, the title, the caption and its more, From a
      // post, New and Hot, the search box's hint is the field's own.
      document.querySelectorAll('h1, .muted, nav.tabs a, .btn, .dn, .post > div, .back, ' +
          '#skriblGallery :is(.tdn, .tun, .tm, .plays, .tt, .tcap, .tcapMore, .tfrom, .tab, .state)').forEach(e => {
        if (!e.getClientRects().length || !e.textContent.trim()) return;
        const r = ratio(rgb(getComputedStyle(e).color), ground(e)); out.read++;
        if (r < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 14) + '" ' + r.toFixed(2));
      });
      return out; }"""
    looks = {}
    for scheme in ("dark", "light"):
        c3 = b.new_context(color_scheme=scheme, **PHONE)
        p3 = c3.new_page()
        p3.goto(HOST + "/")
        p3.select_option("select[name=uid]", index=0)
        p3.click("button:has-text('Sign in')")
        p3.wait_for_timeout(700)
        seen3 = {"feed": p3.evaluate(READ)}
        p3.goto(HOST + "/skribls")
        p3.wait_for_timeout(1500)
        seen3["skribls"] = p3.evaluate(READ)
        looks[scheme] = (seen3, c3, p3)
    page_ok = all(looks["dark"][0][k]["page"] < 0.05 and looks["light"][0][k]["page"] > 0.85 for k in ("feed", "skribls"))
    check("the stand-in follows the device: a dark page on a dark phone, a light one on a light phone (feed and Skribls)",
          page_ok, "; ".join(f"{sc} {k} ground luminance {v['page']}" for sc in looks for k, v in looks[sc][0].items()))
    low = [f"{sc} {k}: {x}" for sc in looks for k, v in looks[sc][0].items() for x in v["low"]]
    reads = sum(v["read"] for sc in looks for v in looks[sc][0].values())
    check("every word on the stand-in, its own and its Gallery section's, reads at 4.5:1 or more on what is"
          " painted behind it, both themes (buttons included)", reads >= 20 and not low, f"{reads} read; under 4.5: {low[:4]}")
    for scheme in ("light", "dark"):
        _, c3, p3 = looks[scheme]
        if scheme == "dark":
            p3.goto(HOST + "/")
            p3.wait_for_timeout(500)
            p3.click("#padBtn")
            p3.wait_for_function("() => { const f = document.getElementById('padFrame'); const w = f && f.contentWindow;"
                                 " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }", timeout=40000)
            p3.wait_for_timeout(800)
            top = p3.evaluate("() => [[201, 8], [380, 24], [20, 24]].map(([x, y]) => { const e = document.elementFromPoint(x, y);"
                              " return e ? (e.id || e.tagName) : null; })")
            frame_box = p3.locator("#padFrame").bounding_box()
            p3.frame_locator("#padFrame").locator("#composeCloseBtn").click()
            p3.wait_for_timeout(700)
            gone = p3.evaluate("() => document.getElementById('padOverlay').hidden")
            check("the Pad has the whole screen in the host, nothing of the host's drawn over its top,"
                  " and its own close takes you back to the post",
                  all(t == "padFrame" for t in top) and frame_box and frame_box["y"] <= 0.5
                  and frame_box["height"] >= 873 and gone,
                  f"at the top {top}; the frame {frame_box}; closed {gone}")
        c3.close()

    print("\nSTAND-IN 8 — the same card on both doors")
    # THE OWNER'S B (after v330): the Skribls tab is Skribl's own Gallery in
    # the host's frame, so a card there is the card /gallery shows, to the
    # pixel. One drawing, posted to each door's Skribl alike (above), read on
    # each: the section the host's width (its frame is narrower than
    # /gallery's page; the media queries ask the screen, which is the same),
    # both clocks three days on, the page under both the same grey, then the
    # card and the New / Hot bar pinned at the same spot (PIN, FRESH above) and
    # photographed. Phone and desk, dark and light, at 2x.
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        Image = None
        check("Pillow is here to compare the pictures", False, str(exc))

    def shoot(door, screen, scheme, width=None):
        ctx = b.new_context(color_scheme=scheme, reduced_motion="reduce", **SCREENS[screen])
        ctx.add_init_script(LATER)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errs.append(f"{door} {screen} {scheme}: {e}"))
        item = host_same if door == "host" else demo_same
        page.goto(HOST + "/skribls" if door == "host" else BASE + "/gallery")
        page.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"]')"
                               " && !document.getElementById('galleryMore').disabled", arg=item, timeout=20000)
        w = page.evaluate("() => document.getElementById('skriblGallery').getBoundingClientRect().width")
        if width:
            page.evaluate("(w) => { document.getElementById('skriblGallery').style.width = w + 'px'; }", width)
        page.add_style_tag(content="html, body { background: #777 !important; }")
        page.mouse.move(1, 1)
        page.wait_for_timeout(1200)
        sels = [f'#galleryList > article.tile[data-id="{item}"]', "#skriblGallery > .bar"]
        sizes = page.evaluate(PIN, sels)
        page.wait_for_timeout(400)
        page.evaluate(FRESH, sels)
        page.wait_for_timeout(200)
        shots = [Image.open(io.BytesIO(page.locator(s).screenshot())).convert("RGB") for s in sels] if sizes else []
        ctx.close()
        return w, sizes, shots

    for screen in ("phone", "desk"):
        for scheme in ("dark", "light"):
            if Image is None:
                break
            hw, hsz, hshots = shoot("host", screen, scheme)
            gw, gsz, gshots = shoot("gallery", screen, scheme, width=hw)
            diffs = []
            # STANDIN_PICTURES=<folder> keeps the pictures, to see what differs.
            for name, a, z in zip(("card", "bar"), gshots, hshots):
                if os.environ.get("STANDIN_PICTURES"):
                    for door, im in (("gallery", a), ("host", z)):
                        im.save(os.path.join(os.environ["STANDIN_PICTURES"], f"{screen}-{scheme}-{name}-{door}.png"))
                if a.size != z.size:
                    diffs.append(f"{name} {a.size} on /gallery, {z.size} on the host")
                    continue
                d = ImageChops.difference(a, z)
                if d.getbbox():
                    n = d.convert("L").point(lambda v: 255 if v else 0).histogram()[255]
                    diffs.append(f"{name}: {n} px differ, in {d.getbbox()}")
            check(f"one drawing is the same card, pixel for pixel, on /gallery and on /host/skribls, and New / Hot"
                  f" the same bar ({screen}, {scheme})",
                  bool(hshots) and len(gshots) == 2 and not diffs,
                  f"the host's section {hw:g}px wide; card and bar {hsz} on the host, {gsz} on /gallery; "
                  + ("; ".join(diffs) if diffs else "0 px differ"))

    print("\nSTAND-IN 9 — nothing of the section reaches the host's own page")
    # The Skribls page with the section's files, and the same page without
    # them: its HTML rewritten in the browser, every tag skribl_gallery_assets()
    # writes taken out (read off the macro itself, so a file added to it is
    # counted). Everything of the host's own -- <html>, <body>, its frame, its
    # header, its sign-in, its tabs -- must compute the same styles and keep
    # the same markup either way: the section's sheet styles nothing outside
    # its root, and its scripts (the labels, the tooltips, the pill) keep to it.
    part = (ROOT / "skribl" / "templates" / "skribl" / "_skribl_gallery_section.html").read_text(encoding="utf-8")
    start = part.index("macro skribl_gallery_assets")
    own = re.findall(r"skribl_asset\('([^']+)'\)", part[start:part.index("endmacro", start)])
    # COMPUTED, NOT RESOLVED. getComputedStyle answers some properties with
    # what layout made of them: the host's frame, `margin: 0 auto`, read 0px
    # on the feed (which loads none of the section's files) and 330px on the
    # Skribls page without them, centred at x=330 both times. The Typed OM's
    # computedStyleMap() is the style itself (auto is auto); where each element
    # of the host's sits is asked separately, as its box (only across, for the
    # three that hold the section, whose height is the section's).
    HOSTS_OWN = """() => {
      const sec = document.getElementById('skriblGallery');
      const out = [];
      for (const e of [document.documentElement, document.body, ...document.body.querySelectorAll('*')]) {
        if (sec && (e === sec || sec.contains(e))) continue;
        const st = {};
        for (const [k, v] of e.computedStyleMap()) if (!k.startsWith('--')) st[k] = v.map(String).join(' ');
        const holds = !!sec && e.contains(sec), r = e.getBoundingClientRect();
        st['(its box)'] = (holds ? [r.x, r.width] : [r.x, r.y, r.width, r.height]).join(', ');
        out.push([e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ').join('.') : ''),
                  holds ? [...e.attributes].map(a => a.name + '=' + a.value).join(' ') : e.outerHTML, st]);
      }
      return out;
    }"""
    taken = {"n": 0}

    def without(route):
        resp = route.fetch()
        html = resp.text()
        for asset in own:
            html, k = re.subn(r"<(link|script)\b[^>]*/" + re.escape(asset) + r"\?[^>]*>(</script>)?\s*", "", html)
            taken["n"] += k
        route.fulfill(response=resp, body=html)

    seen9 = {}
    for how in ("with", "without"):
        c5 = b.new_context(**SCREENS["desk"])
        p5 = c5.new_page()
        p5.on("pageerror", lambda e: errs.append(f"leak {how}: {e}"))
        if how == "without":
            p5.route(HOST + "/skribls", without)
        p5.goto(HOST + "/skribls")
        p5.wait_for_timeout(2500)
        seen9[how] = p5.evaluate(HOSTS_OWN)
        c5.close()
    moved = []
    for (wl, wm, ws), (ol, om, os_) in zip(seen9["with"], seen9["without"]):
        if wl != ol or wm != om:
            moved.append(f"{wl}: markup {wm[:90]!r} vs {om[:90]!r}")
        else:
            props = [f"{k} {ws.get(k)!r} vs {os_.get(k)!r}" for k in sorted(set(ws) | set(os_)) if ws.get(k) != os_.get(k)]
            if props:
                moved.append(f"{wl}: " + ", ".join(props[:3]))
    check("nothing of the section reaches the host's own page: with its files and without, every element of the"
          " host's computes the same style and keeps the same markup",
          taken["n"] == len(own) and len(seen9["with"]) == len(seen9["without"]) >= 10 and not moved,
          f"{len(own)} files in the macro, {taken['n']} taken out; {len(seen9['with'])} elements of the host's read; "
          + ("; ".join(moved[:3]) if moved else "none moved"))

    print("\nSTAND-IN 10 — a report from the host is taken")
    # The card's ⋯, Report, a reason, Send, from the host's own page: the token
    # the section carries (skribl_csrf(), on a page Skribl's hooks never saw)
    # and the cookie the page's response set with it are the pair the server
    # checks, so the report is taken (202), and the card says it was.
    # A NEW BROWSER THAT COMES STRAIGHT HERE. One that has been anywhere Skribl
    # answers (a post's poster on the feed) already holds a sound cookie, and
    # the page's token is that cookie's: so did this row, signed in through the
    # feed first, with the cookie for the page's token taken out (202 all the
    # same). Landing first on the Skribls page, the page's own response has to
    # set it.
    c6 = b.new_context(**SCREENS["desk"])
    p6 = c6.new_page()
    p6.on("pageerror", lambda e: errs.append(f"report: {e}"))
    answers = []
    p6.on("response", lambda r: answers.append(r.status)
          if r.request.method == "POST" and r.url.split("?")[0].endswith("/report") else None)
    p6.goto(HOST + "/skribls")
    p6.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"]')",
                         arg=host_same, timeout=15000)
    p6.wait_for_timeout(500)
    opener = f'#galleryList > article.tile[data-id="{host_same}"] .tileMore'
    p6.click(opener)
    p6.wait_for_timeout(250)
    p6.click(".cardMenu .cmReport")
    p6.wait_for_timeout(400)
    p6.click('#reportSheet input[value="copyright"]')
    p6.fill("#reportNote", "posted twice, by the stand-in's suite")
    p6.click("#reportSend")
    p6.wait_for_timeout(1500)
    said = p6.evaluate("() => document.getElementById('reportStatus').textContent")
    marked = p6.evaluate(f"() => document.querySelector('{opener}').getAttribute('data-reported')")
    p6.keyboard.press("Escape")
    p6.wait_for_timeout(500)
    p6.click(opener)
    p6.wait_for_timeout(250)
    word = p6.evaluate("() => { const i = document.querySelector('.cardMenu .cmReport'); return i ? i.textContent.trim() : null; }")
    check("a report from the host's Skribls page is taken: the server answers 202, the sheet says thanks,"
          " and the card's menu says Reported",
          answers == [202] and "thanks" in (said or "").lower() and marked == "1" and word == "Reported",
          f"answers {answers}; the sheet {said!r}; the ⋯ marked {marked!r}; the menu {word!r}")
    c6.close()

    print("\nSTAND-IN 12 — the empty Gallery names its own door's tick")
    # The owner, Nov 10 ("all yes"): the empty state says what puts a skribl
    # here in the words of the tick that door shows. Skribl's own Post sheet
    # says "Show in the public gallery" (and the Library can turn it on
    # later); a host's composer, opened with compose=1&gallery=1, says "Show
    # in the Skribls gallery", and a host's people have no Library to find.
    # Read from what each server sends: the empty state's second <b> (the
    # first is "Nothing here yet.") against the label of the tick on the
    # sheet that door opens.
    import html as _html
    import re as _re

    def _empty_words(url):
        t = pg.request.get(url).text()
        m = _re.search(r'id="galleryEmpty"[^>]*>(.*?)</p>', t, _re.S)
        bs = _re.findall(r"<b>(.*?)</b>", m.group(1), _re.S) if m else []
        return (_html.unescape(bs[1]).strip() if len(bs) > 1 else None), bool(m and "Library" in m.group(1))

    def _tick_label(url):
        t = pg.request.get(url).text()
        m = _re.search(r'<span class="post-check-text">([^<]*)<span class="post-check-sub"', t)
        return _html.unescape(m.group(1)).strip() if m else None

    feed = pg.request.get(HOST + "/").text()
    composer = _re.search(r"src:\s*\"(/[^\"]*compose=1[^\"]*)\"", feed)
    host_said, host_lib = _empty_words(HOST + "/skribls")
    host_tick = _tick_label(BASE + composer.group(1).replace("\\u0026", "&")) if composer else None
    own_said, own_lib = _empty_words(BASE + "/gallery")
    own_tick = _tick_label(BASE + "/")
    check("the empty Gallery names the tick its own door shows: the host's Skribls page its composer's"
          " (and no Library), Skribl's own /gallery its Post sheet's (and the Library)",
          bool(host_tick) and host_said == host_tick and not host_lib
          and bool(own_tick) and own_said == own_tick and own_lib,
          f"host: says {host_said!r}, its tick {host_tick!r}, Library {host_lib};"
          f" Skribl's own: says {own_said!r}, its tick {own_tick!r}, Library {own_lib}")
    check("no page errors on the stand-in", not errs, "; ".join(errs[:2]))
    c.close()
    b.close()

summarise_and_exit()
