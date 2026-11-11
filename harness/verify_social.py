#!/usr/bin/env python3
"""The site's frame, at /social (docs/SOCIAL-SITE.md, phase 1, piece 1).

The owner's "all yes" on phase 1's mocks (Nov 10): A, Sketchbook; a bar
along the bottom of a phone and a rail down the left of a desk; Make as a
small sheet with two doors, Draw and Flip; and a first visit where Blooby
draws his card above the newest skribls. social/ is that frame, plugged into
the demo's own app beside Skribl (one Skribl, shared), and this suite asks
what it promises, through the demo's own server:

  1. IT IS THERE, AND ONLY WHEN WANTED: /social answers with the site's page;
     SKRIBL_SOCIAL=0 leaves it out, and a site that cannot start is logged
     and left out, the demo's own pages answering either way.
  2. THE BAR AND THE RAIL: on a touch phone the bar holds Home, Explore,
     Make and Sign in (You once signed in, piece 2: verify_socialauth), and
     on a desk the rail holds the wordmark and the same four; the
     page you are on carries the pen's line (painted, not merely there);
     every target is 44px or more; nothing of the frame covers the page; and
     no id is on a page twice.
  3. MAKE: the sheet opens from the bar on a phone, the rail on a desk and
     Home's button; its doors are Skribl's own Pad and Flip (url_for's own
     addresses, and they open); a door picked, Esc, a tap outside, a tap on
     its grip and a swipe down close it, giving focus back, and Tab stays
     inside it meanwhile; the page the back button keeps comes back with it
     closed; it glides, read on every frame, never a jump, up and down; under
     Reduce Motion it does not move, opening or closing.
  4. THE FIRST VISIT: Blooby's card plays in Skribl's real player, ink
     appearing over time; under Reduce Motion it rests, finished; and the
     newest public skribls are under it (one is posted through the API).
  5. EXPLORE holds Skribl's own Gallery section, and a card in it plays.
  6. EVERY WORD OF THE SITE'S OWN reads at 4.5:1 or more on what is painted
     behind it: phone and desk, light and dark, the Make sheet included.
  7. NO PAGE ERRORS AND NO CSP ERRORS on the site's pages, Make and the
     first visit's player running, and through Draw's door into the Pad and
     back.
  8. THE LAYERS: no module under skribl/ imports social; social/ imports
     from skribl only documented public names (create_post and delete_post
     with their exceptions, since piece 3's faces); its templates reach only
     the Skribl partials docs/INTEGRATION.md documents (the face player's
     among them since piece 3); and every Skribl file it names is there.
  9. THE EMPTY GALLERY'S WORDS: the site's Home and Explore name the tick on
     the Pad's own Post sheet, and the Library (the site's Make opens
     Skribl's own editors), not a host composer's.

SOCIAL_PART=<n> runs one section (calibration). Every row was shown red by
breaking one part of the site and green as built: DECISIONS.md, "The site's
frame at /social".
"""
import ast
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001").rstrip("/")
SITE = BASE + "/social"
ROOT = Path(__file__).resolve().parents[1]
PART = os.environ.get("SOCIAL_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIAL {n} — {label}")
    return True


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the site is mounted.")
    raise SystemExit(77)
try:
    from PIL import Image
except ImportError:      # declared in harness/requirements.txt; the row that needs it fails, saying so
    Image = None

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
TAG = "social %d" % int(time.time() * 1000)


# ---- the demo's own app, asked in a process of its own ----------------------
# The site as the demo mounts it, and Skribl's own addresses for the Pad and
# Flip, from url_for: what the doors must open. A temporary database and no
# stand-in, so nothing here touches a file the server under test uses.
APP = r"""
import json, sys
{prelude}
from flask import url_for
from app import app
c = app.test_client()
with app.test_request_context():
    pad, flip = url_for("skribl.skribl_editor"), url_for("skribl.skribl_flip")
print("RESULT " + json.dumps({{"social": c.get("/social/").status_code,
    "explore": c.get("/social/explore").status_code, "pad": c.get(pad).status_code,
    "flip": c.get(flip).status_code, "mounted": "social" in app.blueprints,
    "pad_url": pad, "flip_url": flip}}))
"""


def ask_app(env=None, prelude=""):
    with tempfile.TemporaryDirectory() as tmp:
        e = dict(os.environ)
        e.update({"DATABASE_URL": "sqlite:///" + os.path.join(tmp, "social.db"),
                  "SKRIBL_STAND_IN": "0", "SECRET_KEY": "verify-social-only", "SKRIBL_ALLOW_SQLITE": "1"})
        e.update(env or {})
        out = subprocess.run([sys.executable, "-c", APP.format(prelude=prelude)], cwd=ROOT, env=e,
                             capture_output=True, text=True, timeout=120)
    got = next((json.loads(ln[7:]) for ln in out.stdout.splitlines() if ln.startswith("RESULT ")), None)
    return got, out.stderr


def post_public(title, caption):
    """One public drawing through the demo's own API, signed out; a demo with
    CSRF on gets its own pair back first."""
    jar = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(BASE + "/api/skribls?limit=1", timeout=20).read()
    tok = next((k.value for k in jar if k.name == "skribl_csrf"), "")
    pts = [{"x": round(408 + math.cos(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "y": round(306 + math.sin(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "color": "#7c5cff", "size": 6 + (i % 5), "t": i * 40, "start": i == 0} for i in range(60)]
    body = {"title": title, "caption": caption, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#101418"}}]}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Skribl-CSRF": tok} if tok else {})})
    with op.open(req, timeout=20) as r:
        return json.loads(r.read().decode())["id"]


# ---- what the page paints, read in the page ----------------------------------
# PAINTED, NOT PLACED (WORKING-AGREEMENTS): an element counts as shown where
# document.elementFromPoint finds it, or something inside it.
PEN = """(sel) => { const s = document.querySelector(sel); if (!s) return { painted: false, hits: 0 };
  const r = s.getBoundingClientRect(); if (!r.width || !r.height) return { painted: false, hits: 0 };
  let hits = 0;
  for (let i = 1; i < 10; i++) for (let j = 1; j < 10; j++) {
    const e = document.elementFromPoint(r.left + r.width * i / 10, r.top + r.height * j / 10);
    if (e && (e === s || s.contains(e))) { hits++; break; } }
  return { painted: hits >= 5, hits: hits }; }"""
BAR = """() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')].filter(e => e.getClientRects().length)
  .map(e => { const r = e.getBoundingClientRect(), c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { name: (e.getAttribute('aria-label') || e.textContent).trim().replace(/\\s+/g, ' '), cls: e.className,
             current: e.getAttribute('aria-current'), w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10,
             hit: !!c && (c === e || e.contains(c)) }; })"""
# The page's own content against the frame: on a phone, Home's two buttons at
# rest and the foot of the page's column scrolled to the end, above the bar;
# on a desk, the column's left edge beside the rail.
COVER_PHONE = """() => new Promise(res => {
  const hit = (e) => { const r = e.getBoundingClientRect(), c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                       return !!c && (c === e || e.contains(c)); };
  const cta = [...document.querySelectorAll('.cta > *')].map(hit);
  scrollTo(0, document.documentElement.scrollHeight);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const col = document.querySelector('main .col').getBoundingClientRect(), nav = document.querySelector('nav.nav').getBoundingClientRect();
    const y = col.bottom - 4, c = document.elementFromPoint(col.left + col.width / 2, y);
    res({ cta: cta, foot: Math.round(y), barTop: Math.round(nav.top), inMain: !!c && !!c.closest('main'),
          what: c ? (c.id || c.className || c.tagName) : null }); })); })"""
# Every id the page holds, and those it holds more than once.
TWICE = """() => { const n = {}; document.querySelectorAll('[id]').forEach(e => { n[e.id] = (n[e.id] || 0) + 1; });
  return Object.keys(n).filter(k => n[k] > 1); }"""
COVER_DESK = """() => { const m = document.querySelector('main .col').getBoundingClientRect();
  return [120, 400, 700].map(y => { const c = document.elementFromPoint(m.left + 6, y);
    return { y: y, x: Math.round(m.left + 6), inMain: !!c && !!c.closest('main'), what: c ? (c.id || c.className || c.tagName) : null }; }); }"""

# THE MAKE SHEET'S PLACE ON EVERY ANIMATION FRAME, from the press that opens
# or closes it until it has long settled (verify_glide's way: read in the page,
# once a frame, never from a recording that drops frames).
GLIDE = """([sel, ms]) => new Promise(res => { const s = document.querySelector('#makeSheet .make-sheet'), out = [];
  const t0 = performance.now(); if (sel === 'Escape') document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  else document.querySelector(sel).click();
  (function f() { const w = document.getElementById('makeSheet'); const r = s.getBoundingClientRect();
    out.push([Math.round(r.top * 10) / 10, +getComputedStyle(s).opacity, w.hidden]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""
SHEET = """() => { const w = document.getElementById('makeSheet'), s = w.querySelector('.make-sheet'), a = document.activeElement;
  const r = s.getBoundingClientRect();
  return { open: !w.hidden && w.classList.contains('is-open'), hidden: w.hidden, role: s.getAttribute('role'),
           modal: s.getAttribute('aria-modal'), focusIn: !!a && s.contains(a), focus: a ? (a.className || a.tagName) : null,
           expanded: [...document.querySelectorAll('[data-make]')].map(b => b.getAttribute('aria-expanded')),
           inert: ['body > .top', 'body > .nav', '#main'].map(q => document.querySelector(q).hasAttribute('inert')),
           doors: [...s.querySelectorAll('a.make-door')].map(d => [d.querySelector('b').textContent, d.getAttribute('href')]),
           top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right),
           opacity: +getComputedStyle(s).opacity }; }"""
# A finger on the sheet: down 60px from its top, moved by each of `dys` in
# turn, `every` ms apart, and lifted. Slow enough to be a drag, not a flick.
TOUCH = """([dys, every]) => new Promise(res => { const s = document.querySelector('#makeSheet .make-sheet'), r = s.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + 60;
  const fire = (type, yy) => { const t = new Touch({ identifier: 7, target: s, clientX: x, clientY: yy });
    const end = type === 'touchend';
    s.dispatchEvent(new TouchEvent(type, { touches: end ? [] : [t], targetTouches: end ? [] : [t], changedTouches: [t],
                                           bubbles: true, cancelable: true, view: window })); };
  fire('touchstart', y);
  let i = 0;
  (function step() { if (i < dys.length) { fire('touchmove', y + dys[i++]); setTimeout(step, every); }
                     else { fire('touchend', y + dys[dys.length - 1]); setTimeout(res, 700); } })(); })"""


def glide(frames, rest, start):
    """The tops of the frames read: did it start where it rests closed, end
    where it rests open, move on many frames, one way, and never jump?"""
    tops = [f[0] for f in frames]
    travel = abs(start - rest)
    steps = [b - a for a, b in zip(tops, tops[1:])]
    big = max((abs(s) for s in steps), default=0)
    way = [s for s in steps if s != 0]
    one_way = all(s < 0 for s in way) if start > rest else all(s > 0 for s in way)
    return {"from": tops[0], "to": tops[-1], "positions": len(set(tops)), "biggest step": round(big, 1),
            "travel": round(travel, 1), "one way": one_way}


# The site's own words, and what each reads against. THE GROUND IS COMPOSITED:
# a translucent bar or button is laid over what is under it in the page, up
# to the first opaque ground (the page's, at the latest).
READ = """() => {
  const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const out = { page: Math.round(lum(ground(document.body)) * 100) / 100, read: [], low: [] };
  document.querySelectorAll('.nav .tab-name, .hello-title, .lede, .cta .btn, .fine, .sec, .page-title, .page-sub, '
                            + '.make-title, .make-words b, .make-words span, .make-cancel').forEach(e => {
    if (!e.getClientRects().length || !e.textContent.trim()) return;
    const r = e.getBoundingClientRect(), c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;          // not painted where it is
    const k = ratio(rgba(getComputedStyle(e).color), ground(e));
    out.read.push(e.textContent.trim().slice(0, 18) + ' ' + k.toFixed(2));
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 18) + '" ' + k.toFixed(2));
  });
  return out; }"""

# The card's own ink, read off its canvas: every 4th pixel that is not the
# card's paper ground (#e6dfd1), which is the drawing's own background.
INK = """() => { const e = document.getElementById('helloCard'), p = e && e._skriblInline, c = e && e.querySelector('canvas');
  if (!p || !c || !c.width || c.hidden) return null;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 0; i < d.length; i += 16) if (Math.abs(d[i] - 230) + Math.abs(d[i + 1] - 223) + Math.abs(d[i + 2] - 209) > 40) n++;
  const s = p.state(); return { ink: n, state: s.state, at: Math.round(s.elapsedMs), kind: s.kind, loaded: s.loaded }; }"""
TRACE = """([ms, every]) => new Promise(res => { const out = [], t0 = performance.now(), read = %s;
  (function f() { out.push(read()); if (performance.now() - t0 < ms) setTimeout(f, every); else res(out); })(); })""" % INK


def painted_ink(png):
    """The card's ink as PAINTED on the screen (a photograph of the box, not
    the canvas's own bitmap): every 2nd pixel that is a colour (the card's
    lilac, its gold) or a dark line (Blooby's outline). The card's paper, the
    page and the grey a box shows before its drawing arrives are none of them."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    px = im.load()
    n = 0
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            r, g, bl = px[x, y]
            if max(r, g, bl) - min(r, g, bl) > 60 or (r + g + bl) < 240:
                n += 1
    return n


def first_visit(ctx):
    """Blooby's card, read from the moment it is in the player until it has
    run a while."""
    pg = ctx.new_page()
    pg.goto(SITE + "/", wait_until="domcontentloaded")
    try:
        pg.wait_for_function("() => { const e = document.getElementById('helloCard'); return !!(e && e._skriblInline && e._skriblInline.state().loaded); }",
                             timeout=30000)
    except Exception:
        return pg, [], None, False         # the card never reached the player: every row on it says so
    trace = pg.evaluate(TRACE, [4000, 200])
    label = pg.evaluate("() => document.getElementById('helloCard').getAttribute('aria-label')")
    shown = pg.evaluate("() => { const a = document.querySelector('.hello-art'); return !a.hidden && a.classList.contains('is-ready')"
                        " && +getComputedStyle(a.querySelector('.hello-fade')).opacity > 0.99; }")
    return pg, trace, label, shown


def fresh(pg, path):
    """A page of the site, loaded anew: each step of a section starts here."""
    pg.goto(SITE + path)
    pg.wait_for_timeout(400)


def press(pg, sel):
    """A button's own click, without waiting for it to be pressable: a step
    must be able to find that it is not."""
    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.click(); }", sel)


with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []

    # ------------------------------------------------------------------ 1
    if part(1, "it is there, and only when wanted"):
        c = b.new_context(**PHONE)
        pg = c.new_page()
        resp = pg.goto(SITE)
        shape = pg.evaluate("""() => ({ at: location.pathname, title: document.title,
            nav: !!document.querySelector('nav.nav'), make: !!document.getElementById('makeSheet'),
            sheet: [...document.querySelectorAll('link[rel=stylesheet]')].map(l => new URL(l.href).pathname) })""")
        check("/social answers with the site's own page: its frame, its Make sheet and its own stylesheet",
              resp is not None and resp.status == 200 and shape["at"] == "/social/" and shape["title"] == "Skribl"
              and shape["nav"] and shape["make"] and "/social/static/social.css" in shape["sheet"],
              f"status {resp.status if resp else None}; {json.dumps(shape)[:240]}")
        c.close()
        mounted, _ = ask_app()
        off, _ = ask_app({"SKRIBL_SOCIAL": "0"})
        broken, said = ask_app(prelude="sys.modules['social'] = None   # the package cannot be imported")
        check("the demo's own app mounts the site: /social/ and /social/explore 200, the Pad and Flip 200",
              bool(mounted) and mounted["mounted"] and mounted["social"] == 200 and mounted["explore"] == 200
              and mounted["pad"] == 200 and mounted["flip"] == 200, json.dumps(mounted))
        check("SKRIBL_SOCIAL=0 leaves the site out (404), and the Pad and Flip answer as before",
              bool(off) and not off["mounted"] and off["social"] == 404 and off["explore"] == 404
              and off["pad"] == 200 and off["flip"] == 200, json.dumps(off))
        check("a site that cannot start is logged and left out: 404, the demo's own pages answering",
              bool(broken) and not broken["mounted"] and broken["social"] == 404 and broken["pad"] == 200
              and "the site at /social did not start" in said,
              f"{json.dumps(broken)}; log: {said.strip().splitlines()[0] if said.strip() else ''!r}")
        DOORS = (mounted or {}).get("pad_url"), (mounted or {}).get("flip_url")
    else:
        got, _ = ask_app() if (not PART or "3" in PART.split(",")) else (None, "")
        DOORS = (got or {}).get("pad_url"), (got or {}).get("flip_url")

    # ------------------------------------------------------------------ 2
    if part(2, "the bar on a phone, the rail on a desk"):
        seen, twice = {}, {}
        for screen, ctx in (("phone", PHONE), ("desk", DESK)):
            c = b.new_context(**ctx)
            pg = c.new_page()
            for page in ("home", "explore"):
                pg.goto(SITE + ("/" if page == "home" else "/explore"))
                pg.wait_for_timeout(500)
                items = pg.evaluate(BAR)
                pens = {name: pg.evaluate(PEN, f'nav.nav a[href$="{href}"] .pen-line')
                        for name, href in (("Home", "/social/"), ("Explore", "/social/explore"))}
                top = pg.evaluate("() => { const a = document.querySelector('body > .top .brand'); if (!a || !a.getClientRects().length) return null;"
                                  " const r = a.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }")
                seen[(screen, page)] = (items, pens, top)
                twice[(screen, page)] = pg.evaluate(TWICE)
            pg.goto(SITE + "/")
            pg.wait_for_timeout(500)
            cover = pg.evaluate(COVER_PHONE if screen == "phone" else COVER_DESK)
            seen[(screen, "cover")] = cover
            c.close()

        def names(screen, page):
            return [i["name"] for i in seen[(screen, page)][0]]
        ph, dk = names("phone", "home"), names("desk", "home")
        # Signed out, You's place says Sign in (piece 2, as the approved mock
        # has it); You itself, signed in, is verify_socialauth's to hold.
        check("on a touch phone the bar holds Home, Explore, Make and Sign in, and nothing else (You's place,"
              " before sign-in)",
              ph == ["Home", "Explore", "Make", "Sign in"] and seen[("phone", "home")][2] is not None,
              f"the bar {ph}; the wordmark at the top {seen[('phone', 'home')][2]}")
        check("on a desk the rail holds the wordmark, Home, Explore, Make and Sign in, and nothing else",
              dk == ["Skribl, home", "Home", "Explore", "Make", "Sign in"] and seen[("desk", "home")][2] is None,
              f"the rail {dk}; the phone's wordmark {seen[('desk', 'home')][2]}")
        marks = []
        for screen in ("phone", "desk"):
            for page, here in (("home", "Home"), ("explore", "Explore")):
                items, pens, _ = seen[(screen, page)]
                cur = [i["name"] for i in items if i["current"] == "page"]
                lines = {n: v["painted"] for n, v in pens.items()}
                ok = cur == [here] and lines[here] and not any(v for n, v in lines.items() if n != here)
                marks.append((ok, f"{screen} {page}: current {cur}, pen's line painted {lines}"))
        check("the page you are on is marked, and only it: aria-current and the pen's line painted under its name"
              " (phone and desk, Home and Explore)", all(m[0] for m in marks), "; ".join(m[1] for m in marks))
        small = [f"{s} {i['name']} {i['w']}x{i['h']}" for s in ("phone", "desk") for pg_ in ("home", "explore")
                 for i in seen[(s, pg_)][0] if i["w"] < 44 or i["h"] < 44]
        top = seen[("phone", "home")][2]
        if top and (top[0] < 44 or top[1] < 44):
            small.append(f"phone wordmark {top}")
        unhit = [f"{s} {i['name']}" for s in ("phone", "desk") for pg_ in ("home", "explore")
                 for i in seen[(s, pg_)][0] if not i["hit"]]
        check("every target in the bar and the rail is 44px or more, and painted where it is (phone and desk)",
              not small and not unhit, f"under 44px: {small}; not on top where they sit: {unhit}")
        pc, dc = seen[("phone", "cover")], seen[("desk", "cover")]
        check("nothing of the frame covers the page: on a phone Home's buttons at rest and the column's foot"
              " above the bar at the end of the page; on a desk the column's edge beside the rail",
              all(pc["cta"]) and len(pc["cta"]) == 2 and pc["inMain"] and pc["foot"] < pc["barTop"]
              and all(d["inMain"] for d in dc), f"phone {json.dumps(pc)}; desk {json.dumps(dc)}")
        dup = {f"{s} {pg_}": v for (s, pg_), v in twice.items() if v}
        check("no id is on a page of the site twice (the two wordmarks' gradients have one each), phone and desk",
              len(twice) == 4 and not dup, f"repeated: {dup}")

    # ------------------------------------------------------------------ 3
    if part(3, "Make: two doors into Skribl's Pad and Flip"):
        # EACH STEP FROM A PAGE OF ITS OWN, freshly loaded: a part that fails
        # (a sheet that will not close) must show red in its own row and not
        # leave the next step pressing at a page it has made inert.
        c = b.new_context(**PHONE)
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(f"make: {e}"))
        fresh(pg, "/")
        frames = pg.evaluate(GLIDE, [".nav .tab-make", 900])
        opened = pg.evaluate(SHEET)
        up = glide(frames, opened["top"], 874)
        check("on a phone the bar's Make opens the sheet: a modal dialog, focus inside it, the page behind inert",
              opened["open"] and opened["role"] == "dialog" and opened["modal"] == "true" and opened["focusIn"]
              and "true" in opened["expanded"] and all(opened["inert"]) and opened["bottom"] == 874,
              json.dumps({k: opened[k] for k in ("open", "role", "modal", "focus", "expanded", "inert", "top", "bottom")}))
        pad_url, flip_url = DOORS
        doors = opened["doors"]
        check("its two doors are Skribl's own: Draw to the Pad, Flip to Flip, at url_for's own addresses",
              bool(pad_url) and doors == [["Draw", pad_url], ["Flip", flip_url]], f"doors {doors}; url_for {DOORS}")
        check("it glides up: from below the screen to where it rests, on many frames, one way, never a jump",
              up["from"] >= 873 and abs(up["to"] - opened["top"]) <= 0.5 and up["positions"] >= 8 and up["one way"]
              and up["biggest step"] <= 0.3 * up["travel"], json.dumps(up))
        frames = pg.evaluate(GLIDE, ["Escape", 900])
        shut = pg.evaluate(SHEET)
        down = glide([f for f in frames if not f[2]], 874, opened["top"])
        check("Esc closes it, gliding down the same way, and gives focus back to the bar's Make",
              shut["hidden"] and not shut["open"] and shut["focus"] == "tab tab-make" and "true" not in shut["expanded"]
              and not any(shut["inert"]) and down["positions"] >= 6 and down["one way"]
              and down["biggest step"] <= 0.35 * down["travel"], f"{json.dumps(down)}; focus {shut['focus']}")
        # Tab stays inside, both ways round: from the first door (where opening
        # puts focus) forward past Cancel back to Draw, and backward past Draw
        # to Cancel. Nothing behind the sheet takes a turn.
        fresh(pg, "/explore")
        press(pg, ".nav .tab-make")
        pg.wait_for_timeout(600)
        FOCUSED = """() => { const a = document.activeElement, s = document.querySelector('#makeSheet .make-sheet');
          if (!a || !s.contains(a)) return a ? a.tagName : null;
          const b = a.querySelector('b'); return (b ? b.textContent : a.textContent).trim(); }"""
        ring = []
        for key in ("Tab", "Tab", "Tab", "Tab", "Shift+Tab", "Shift+Tab"):
            pg.keyboard.press(key)
            ring.append(pg.evaluate(FOCUSED))
        check("Tab stays inside it, both ways round: Flip, Cancel, Draw, Flip, then back to Draw and Cancel",
              ring == ["Flip", "Cancel", "Draw", "Flip", "Draw", "Cancel"], f"focus went {ring}")
        closers = {}
        for how in ("outside", "grip", "swipe"):
            fresh(pg, "/explore")
            press(pg, ".nav .tab-make")
            pg.wait_for_timeout(600)
            try:
                if how == "outside":
                    pg.mouse.click(200, 120)
                elif how == "grip":
                    pg.click("#makeSheet .make-grip", timeout=3000)
                else:
                    pg.evaluate(TOUCH, [[12, 40, 90, 160, 220], 90])
            except Exception as exc:
                closers[how + " (could not)"] = str(exc).splitlines()[0][:80]
            pg.wait_for_timeout(700)
            closers[how] = pg.evaluate(SHEET)["hidden"]
        fresh(pg, "/explore")
        press(pg, ".nav .tab-make")
        pg.wait_for_timeout(600)
        pg.evaluate(TOUCH, [[10, 16, 20], 90])
        held = pg.evaluate(SHEET)
        check("a tap outside it, a tap on its grip and a swipe down each close it; a short drag lets it glide back up",
              all(v is True for v in closers.values()) and held["open"] and held["top"] == opened["top"],
              f"closed: {closers}; after a short drag open {held['open']} at {held['top']} (rests at {opened['top']})")
        # Home's own Make a skribl, and a door picked. The sheet goes down as
        # the door opens Skribl's Pad, so the page a phone's back button brings
        # back whole has it closed. Read twice: with the door's navigation held
        # back, the sheet as the door leaves it; and through the door and back
        # in a browser that keeps pages for the back button, as a phone's does.
        # (Playwright starts its headless shell with that cache switched off,
        # and there the page came back new, and closed, whatever the door did;
        # Chromium's own build, the cache allowed, keeps it.)
        fresh(pg, "/")
        press(pg, ".cta [data-make]")
        pg.wait_for_timeout(600)
        from_home = pg.evaluate(SHEET)
        pg.evaluate("""() => new Promise(res => {
            const hold = e => { if (e.target.closest('.make-door')) e.preventDefault(); };
            document.addEventListener('click', hold, true);
            const d = document.querySelector('#makeSheet a.make-door'); if (d) d.click();
            setTimeout(() => { document.removeEventListener('click', hold, true); res(); }, 700); })""")
        picked = pg.evaluate(SHEET)
        c.close()
        landed, back, kept = None, None, None
        try:
            kb = p.chromium.launch(channel="chromium", ignore_default_args=["--disable-back-forward-cache"])
        except Exception as exc:
            kb, landed = None, {"no Chromium build to keep pages with": str(exc).splitlines()[0][:80]}
        if kb is not None:
            kc = kb.new_context(**PHONE)
            kc.add_init_script("addEventListener('pageshow', e => { if (e.persisted) window.__kept = true; });")
            q = kc.new_page()
            q.on("pageerror", lambda e: errs.append(f"make, the kept page: {e}"))
            try:
                fresh(q, "/")
                press(q, ".cta [data-make]")
                q.wait_for_timeout(600)
                with q.expect_navigation(timeout=30000):
                    q.click("#makeSheet a.make-door >> nth=0", timeout=5000)
                landed = q.evaluate("() => ({ at: location.pathname,"
                                    " pad: document.title === 'Skribl Pad' && !!document.getElementById('canvas') })")
                # A page the cache gives back fires no load: wait for the commit.
                q.go_back(wait_until="commit")
                q.wait_for_timeout(1200)
                back = q.evaluate(SHEET)
                kept = q.evaluate("() => !!window.__kept")
            except Exception as exc:
                landed = {"could not": str(exc).splitlines()[0][:80]}
            kb.close()
        check("Home's Make a skribl opens it too; a door picked closes it as Draw opens Skribl's Pad, and the page"
              " the back button keeps comes back with it closed",
              from_home["open"] and picked["hidden"] and bool(landed) and landed.get("at") == pad_url
              and landed.get("pad") and bool(back) and back["hidden"] and kept,
              f"from Home {from_home['open']}; a door picked, hidden {picked['hidden']}; Draw landed {landed};"
              f" back, kept by the browser {kept}, hidden {back and back['hidden']}")
        c = b.new_context(**DESK)
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(f"make desk: {e}"))
        fresh(pg, "/explore")
        press(pg, ".nav .tab-make")
        pg.wait_for_timeout(600)
        desk = pg.evaluate(SHEET)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(600)
        desk_shut = pg.evaluate(SHEET)
        mid = (desk["left"] + desk["right"]) / 2, (desk["top"] + desk["bottom"]) / 2
        check("on a desk the rail's Make opens the same choice, a card in the middle of the screen, and Esc closes it",
              desk["open"] and desk["focusIn"] and desk["doors"] == doors and abs(mid[0] - 640) <= 2
              and abs(mid[1] - 430) <= 2 and desk_shut["hidden"] and desk_shut["focus"] == "tab tab-make",
              f"open {desk['open']}, centre {mid}, doors {desk['doors']}; after Esc hidden {desk_shut['hidden']}, focus {desk_shut['focus']}")
        flip_door = dict(desk["doors"]).get("Flip") or "/nowhere"
        flip_page = pg.request.get(BASE + flip_door)
        flip_title = re.search(r"<title>([^<]*)", flip_page.text()) if flip_page.ok else None
        check("Flip's door opens Skribl's Flip", bool(flip_title) and flip_title.group(1).strip() == "Skribl · Flip",
              f"{flip_door} -> {flip_page.status}, titled {flip_title.group(1) if flip_title else None!r}")
        c.close()
        c = b.new_context(reduced_motion="reduce", **PHONE)
        pg = c.new_page()
        fresh(pg, "/")
        frames = pg.evaluate(GLIDE, [".nav .tab-make", 700])
        still = pg.evaluate(SHEET)
        gone = pg.evaluate(GLIDE, ["Escape", 700])
        # Read on every frame, opening AND closing: where it is while it can
        # be seen at all, and how its opacity goes (a fade has many steps).
        # Opening alone could not fail: with only opacity transitioned, the
        # sheet stands where it rests from the first frame either way; it is
        # on the way out that it would drop off the bottom in one frame.
        seen_up = sorted({f[0] for f in frames})
        seen_down = [f for f in gone if not f[2] and f[1] > 0.02]
        tops_down = sorted({f[0] for f in seen_down})
        fades = (len({round(f[1], 2) for f in frames}), len({round(f[1], 2) for f in seen_down}))
        check("under Reduce Motion it does not move: it fades in where it rests, and fades out there, every frame",
              still["open"] and len(seen_up) == 1 and abs(seen_up[0] - still["top"]) <= 0.5 and frames[-1][1] >= 0.99
              and tops_down == seen_up and min(fades) >= 3,
              f"opening, its tops {seen_up[:4]}; closing, its tops while seen {tops_down[:4]}; rests at {still['top']};"
              f" opacities in the fades {fades}")
        c.close()

    # ------------------------------------------------------------------ 4
    if part(4, "the first visit: Blooby draws his card, the newest skribls under it"):
        newest = post_public(TAG + " the newest", "Posted by verify_social, to be first under Blooby.")
        c = b.new_context(**PHONE)
        pg, trace, label, shown = first_visit(c)
        pg.on("pageerror", lambda e: errs.append(f"first visit: {e}"))
        moving = [t for t in trace if t and t["state"] == "playing"]
        check("Blooby's card starts by itself in Skribl's own player: a Flip, playing from the first read on,"
              " its clock running, shown, and named for what a tap does (Pause)",
              bool(trace) and len(moving) == len(trace) and moving[0]["kind"] == "flip"
              and moving[-1]["at"] - moving[0]["at"] >= 2500 and shown and (label or "").startswith("Pause"),
              f"{len(moving)} of {len(trace)} reads playing; clock {moving[0]['at'] if moving else None} ->"
              f" {moving[-1]['at'] if moving else None} ms; shown {shown}; named {label!r}")
        # The drawing coming in, PHOTOGRAPHED, from the start of its replay
        # (put back there and played on: how soon after arriving the first
        # read happens depends on the machine; the replay's start does not).
        # At a quarter of its speed, the player's own slowest, and for four
        # seconds of the clock however long each picture takes: the card's
        # coloured strokes come in between a quarter and half a second of its
        # replay at 1x, and a slower machine takes longer over each picture,
        # so a fixed count of pictures could all fall before them.
        playing_max = max((t["ink"] for t in trace if t), default=0)
        inks = []
        if Image is not None and trace:
            pg.evaluate("() => { const p = document.getElementById('helloCard')._skriblInline; p.seek(0); p.setRate(0.25); p.play(); }")
            until = time.time() + 4.0
            while time.time() < until and len(inks) < 40:
                inks.append(painted_ink(pg.locator("#helloCard").screenshot()))
                pg.wait_for_timeout(60)
        rises = sum(1 for a, z in zip(inks, inks[1:]) if z > a)
        check("...and its ink appears over time, as painted: from its start the card comes in, picture after picture",
              len(inks) >= 6 and inks[0] < 0.1 * max(inks) and max(inks) > 4000 and rises >= 2,
              f"ink painted {inks}; rose on {rises} pictures" if inks
              else ("Pillow is not here (harness/requirements.txt)" if Image is None else "no card in the player to watch"))
        try:
            pg.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"]')",
                                 arg=newest, timeout=20000)
        except Exception:
            pass                           # the row below says what is there instead
        under = pg.evaluate("""(id) => { const s = document.getElementById('skriblGallery');
            const h = document.querySelector('main .sec'), first = s && s.querySelector('#galleryList > article.tile');
            return { section: !!s, heading: h ? h.textContent.trim() : null, first: first ? first.getAttribute('data-id') : null,
                     below: !!(h && s && (h.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING)),
                     sections: document.querySelectorAll('[data-skribl-gallery]').length }; }""", newest)
        check("under it, the newest public skribls: Skribl's own Gallery section, the drawing just posted first",
              under["section"] and under["sections"] == 1 and under["first"] == newest and under["below"]
              and under["heading"] == "Fresh from everyone", json.dumps(under))
        c.close()
        c = b.new_context(reduced_motion="reduce", **PHONE)
        pg = c.new_page()
        pg.goto(SITE + "/", wait_until="domcontentloaded")
        try:
            pg.wait_for_function("() => { const e = document.getElementById('helloCard'); return !!(e && e._skriblInline && e._skriblInline.state().loaded); }",
                                 timeout=30000)
        except Exception:
            pass                           # INK reads null, and the row says so
        pg.wait_for_timeout(500)
        rest = [pg.evaluate(INK)]
        pics = [painted_ink(pg.locator("#helloCard").screenshot())] if Image is not None else []
        pg.wait_for_timeout(1500)
        rest.append(pg.evaluate(INK))
        if Image is not None:
            pics.append(painted_ink(pg.locator("#helloCard").screenshot()))
        check("under Reduce Motion it does not start: it rests, finished, the card with Blooby on it,"
              " painted and still",
              all(r and r["state"] == "idle" and r["at"] == 0 for r in rest) and rest[0]["ink"] == rest[1]["ink"]
              and rest[0]["ink"] >= 0.98 * playing_max and len(pics) == 2 and pics[0] == pics[1] and pics[0] > 4000,
              f"{rest}; the playing card's most ink {playing_max}; painted {pics}")
        c.close()

    # ------------------------------------------------------------------ 5
    if part(5, "Explore holds Skribl's own Gallery, and a card plays"):
        sid = post_public(TAG + " to explore", "Posted by verify_social, to be played on Explore.")
        c = b.new_context(**PHONE)
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(f"explore: {e}"))
        pg.goto(SITE + "/explore")
        try:
            pg.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"]')",
                                 arg=sid, timeout=20000)
        except Exception:
            pass                           # the rows below say what is there instead
        sec = pg.evaluate("""() => { const s = document.getElementById('skriblGallery');
            return { section: !!s && s.hasAttribute('data-skribl-gallery'), sorts: [...(s ? s.querySelectorAll('[data-sort]') : [])].map(t => t.textContent.trim()),
                     search: !!document.getElementById('galleryQ'), sheet: !!document.getElementById('reportSheet'),
                     title: (document.querySelector('.page-title') || {}).textContent }; }""")
        check("Explore holds Skribl's own Gallery section: New and Hot, the search box, the report sheet",
              sec["section"] and sec["sorts"] == ["New", "Hot"] and sec["search"] and sec["sheet"]
              and sec["title"] == "Explore", json.dumps(sec))
        box = f'#galleryList > article.tile[data-id="{sid}"] [data-skribl-inline]'
        try:
            pg.click(box, timeout=5000)
        except Exception:
            pass                           # no card to press: the row below reads nothing playing
        reads = []
        for _ in range(4):
            pg.wait_for_timeout(450)
            reads.append(pg.evaluate("""(sel) => { const e = document.querySelector(sel), p = e && e._skriblInline, c = e && e.querySelector('canvas');
                if (!p || !c || c.hidden || !c.width) return null; const s = p.state();
                const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
                for (let i = 0; i < d.length; i += 16) if (d[i] > 90 && d[i + 2] > 180) n++;
                return { state: s.state, at: Math.round(s.elapsedMs), ink: n }; }""", box))
        ok = all(reads) and all(r["state"] == "playing" for r in reads[:2]) and reads[1]["at"] > reads[0]["at"] \
            and max(r["ink"] for r in reads) > reads[0]["ink"]
        check("a card there plays when tapped: its clock runs and its ink comes in", ok, json.dumps(reads))
        c.close()

    # ------------------------------------------------------------------ 6
    if part(6, "every word of the site's own reads at 4.5:1"):
        looks = {}
        for screen, ctx in (("phone", PHONE), ("desk", DESK)):
            for scheme in ("light", "dark"):
                c = b.new_context(color_scheme=scheme, reduced_motion="reduce", **ctx)
                pg = c.new_page()
                pg.goto(SITE + "/")
                pg.wait_for_timeout(700)
                looks[(screen, scheme, "home")] = pg.evaluate(READ)
                pg.click(".nav .tab-make")
                pg.wait_for_timeout(500)
                looks[(screen, scheme, "make")] = pg.evaluate(READ)
                pg.keyboard.press("Escape")
                pg.goto(SITE + "/explore")
                pg.wait_for_timeout(700)
                looks[(screen, scheme, "explore")] = pg.evaluate(READ)
                c.close()
        grounds = {k: v["page"] for k, v in looks.items() if k[2] == "home"}
        check("the site follows the device: a dark page on a dark screen, a light one on a light screen",
              all((v < 0.05) if k[1] == "dark" else (v > 0.9) for k, v in grounds.items()),
              "; ".join(f"{k[0]} {k[1]} {v}" for k, v in grounds.items()))
        low = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["low"]]
        reads = sum(len(v["read"]) for v in looks.values())
        lowest = min((float(x.rsplit(" ", 1)[1]), f"{k[0]} {k[1]} {k[2]} {x}") for k, v in looks.items() for x in v["read"]) \
            if reads else (0, "nothing read")
        check("every word of the site's own reads at 4.5:1 or more on what is painted behind it: phone and desk,"
              " light and dark, Home, Explore and the Make sheet", reads >= 60 and not low,
              f"{reads} read, the lowest {lowest[1]}; under 4.5: {low[:4]}")

    # ------------------------------------------------------------------ 7
    if part(7, "no page errors, no CSP errors"):
        WATCH = "document.addEventListener('securitypolicyviolation', e => (window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));"
        noted = []
        for screen, ctx in (("phone", PHONE), ("desk", DESK)):
            c = b.new_context(**ctx)
            c.add_init_script(WATCH)
            pg = c.new_page()
            pg.on("pageerror", lambda e, s=screen: noted.append(f"{s} pageerror: {e}"))
            pg.on("console", lambda m, s=screen: noted.append(f"{s} console {m.type}: {m.text[:160]}")
                  if m.type in ("error", "warning") else None)
            for path in ("/", "/explore"):
                pg.goto(SITE + path)
                pg.wait_for_timeout(1500)
                pg.click(".nav .tab-make")
                pg.wait_for_timeout(500)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(500)
                v = pg.evaluate("() => window.__csp || []")
                noted += [f"{screen} {path} violation: {x}" for x in v]
            # Through a door into Skribl's Pad and back: the way between the
            # site and Skribl's own pages is the site's too.
            press(pg, ".nav .tab-make")
            pg.wait_for_timeout(500)
            try:
                with pg.expect_navigation(timeout=30000):
                    pg.click("#makeSheet a.make-door >> nth=0", timeout=5000)
                pg.wait_for_timeout(1200)
                pg.go_back()
                pg.wait_for_timeout(1200)
            except Exception as exc:
                noted.append(f"{screen} could not go through Draw's door and back: {str(exc).splitlines()[0][:100]}")
            noted += [f"{screen} back from the Pad, violation: {x}" for x in pg.evaluate("() => window.__csp || []")]
            heads = pg.request.get(SITE + "/").headers
            c.close()
        check("no page errors, no console errors and no CSP violations on the site's pages, phone and desk,"
              " the first visit playing, Make opened, and through Draw's door into the Pad and back",
              not noted, "; ".join(noted[:3]))
        pol = heads.get("content-security-policy", "")
        check("the site's pages carry a policy with no inline script allowed: script-src 'self' alone",
              "script-src 'self';" in pol + ";" and "unsafe-inline" not in pol.split("script-src", 1)[1].split(";", 1)[0]
              and "nonce-" not in pol, pol[:160])

    # ------------------------------------------------------------------ 8
    if part(8, "the layers: Skribl never imports the site, the site reaches only Skribl's public seams"):
        def imports(path):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            out = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    out += [(a.name, None) for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    out += [(node.module, a.name) for a in node.names]
                elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "skribl":
                    out.append(("skribl." + node.attr, "(attribute)"))
            return out
        skribl_py = sorted((ROOT / "skribl").rglob("*.py"))
        upward = [f"{p.relative_to(ROOT)}: {m}" for p in skribl_py for m, _ in imports(p)
                  if m == "social" or m.startswith("social.")]
        check("no module under skribl/ imports social (read from the source, not from a running app)",
              len(skribl_py) >= 20 and not upward, f"{len(skribl_py)} modules read; {upward[:3]}")
        tree = ast.parse((ROOT / "skribl" / "__init__.py").read_text(encoding="utf-8"))
        public = next((ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(getattr(t, "id", None) == "__all__" for t in n.targets)), [])
        guide = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
        documented = {n for n in public if n in guide}
        social_py = sorted((ROOT / "social").rglob("*.py"))
        reached = [(p, m, n) for p in social_py for m, n in imports(p) if m == "skribl" or m.startswith("skribl.")]
        stray = [f"{p.relative_to(ROOT)}: {m}{'.' + n if n and n != '(attribute)' else ''}" for p, m, n in reached
                 if not ((m == "skribl" and (n is None or n in documented))
                         or (m.startswith("skribl.") and n == "(attribute)" and m[7:] in documented))]
        check("social/ imports from skribl only names it documents (skribl.__all__, in docs/INTEGRATION.md)",
              len(social_py) >= 1 and not stray,
              f"{len(social_py)} modules read; it imports {sorted({m + ('.' + n if n and n != '(attribute)' else '') for _, m, n in reached}) or 'nothing from skribl'};"
              f" undocumented: {stray}")
        # THE TEMPLATES' WAY IN, the same rule: the Skribl partials the site's
        # pages import or include are the ones the guide documents for a
        # host, and each macro it imports from one is named there too.
        SEAMS = {"skribl/_skribl_inline_player.html", "skribl/_skribl_gallery_section.html",
                 "skribl/_skribl_brand_mark.html", "skribl/_skribl_face.html"}
        tpl_out, files, asked = [], set(), []
        for t in sorted((ROOT / "social" / "templates").rglob("*.html")):
            body = re.sub(r"\{#.*?#\}", "", t.read_text(encoding="utf-8"), flags=re.S)
            for kind, name, names in re.findall(r"\{%-?\s*(from|import|include)\s+['\"]([^'\"]+)['\"](?:\s+import\s+([^%]+))?", body):
                if not name.startswith("skribl/"):
                    continue
                asked.append(name)
                macros = [x.strip() for x in (names or "").split(",") if x.strip()]
                if name not in SEAMS or name not in guide or any(m not in guide for m in macros):
                    tpl_out.append(f"{t.name}: {kind} {name} {macros}")
            files |= set(re.findall(r"skribl_asset\(\s*['\"]([^'\"]+)['\"]\s*\)", body))
        missing = sorted(f for f in files if not (ROOT / "skribl" / "static" / f).is_file())
        check("the site's templates reach Skribl only through the partials docs/INTEGRATION.md documents"
              " (the player's, the Gallery section's, the signature's, the face player's), with documented macros",
              asked and not tpl_out, f"reached {sorted(set(asked))}; undocumented: {tpl_out}")
        check("every Skribl file the site names (skribl_asset) is there",
              files and not missing, f"{sorted(files)}; missing {missing}")

    if part(9, "the empty Gallery names the tick the site's people see"):
        # The site's Make opens Skribl's own Pad and Flip, so its people post
        # from Skribl's own Post sheet: the Gallery's empty state names that
        # sheet's tick, "Show in the public gallery", and the Library that can
        # turn it on later, not a host composer's "Show in the Skribls
        # gallery" (verify_standin section 12 holds a host's). The macro's
        # `door` says which; the site passes door='app'. Read from what the
        # server sends: the empty state's second <b> (the first is "Nothing
        # here yet.") against the label of the tick on the Pad's Post sheet.
        import html as _html

        def _fetch(url):
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.read().decode("utf-8", "replace")

        def _empty_words(url):
            m = re.search(r'id="galleryEmpty"[^>]*>(.*?)</p>', _fetch(url), re.S)
            bs = re.findall(r"<b>(.*?)</b>", m.group(1), re.S) if m else []
            return (_html.unescape(bs[1]).strip() if len(bs) > 1 else None), bool(m and "Library" in m.group(1))

        pad_page = _fetch(BASE + "/")
        tick = re.search(r'<span class="post-check-text">([^<]*)<span class="post-check-sub"', pad_page)
        tick = _html.unescape(tick.group(1)).strip() if tick else None
        said = {path: _empty_words(SITE + path) for path in ("/", "/explore")}
        check("the empty Gallery on the site's Home and Explore names the tick on the Pad's Post sheet,"
              " and the Library",
              bool(tick) and all(w == tick and lib for w, lib in said.values()),
              f"the Pad's tick {tick!r}; " + "; ".join(f"{p}: {w!r}, Library {lib}" for p, (w, lib) in said.items()))

    check("no page errors on the site's pages", not errs, "; ".join(errs[:2]))
    b.close()

summarise_and_exit()
