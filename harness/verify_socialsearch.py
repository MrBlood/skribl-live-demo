#!/usr/bin/env python3
"""Finding people on the Skribl site (the map, part two, item 5; docs/SOCIAL-SITE.md
section 17; the owner's "All yes" on the finding-people mock, Nov 15), through
the demo's own server, with Chromium's virtual authenticator for the site's
people.

  1. THE GALLERY'S BOX FINDS PEOPLE: its words ("Search people and drawings",
     its placeholder and its name to a screen reader; 16px, 44px tall); with
     a search, People first (up to three, the people you follow first, "See
     all" when there are more), then Drawings and the tiles, phone and desk;
     no search, the Gallery as it was; the pills change the drawings alone.
  2. A PERSON'S ROW: 64px, the face 44, the name 17px 600 in the first ink,
     the @handle 15px in the second, Follow 44px tall and one width with
     either word, each painted where it stands, phone and desk, light and
     dark; your own row has no Follow.
  3. A TAP: anywhere on a row but Follow opens their page (the face, the name,
     the row's ground; a touch, a click); Follow follows and the page stays,
     Following asks once ("Unfollow Pam?") and Unfollow ends it; signed out,
     Follow asks to sign in, coming back to the search as it is.
  4. WHO IS FOUND: any word of a name, never the middle of one; an @handle's
     start; case, a leading @ and accents put aside; the people you follow
     first; nobody a block hides either way, nobody taken down, signed out
     too; a mute changes nothing.
  5. SEE ALL: the people alone (?who=people), twenty a page; walked to its
     end with Load more, everybody once, none missed, in order; Load more in
     place; the address shareable and the back button kind; a new search
     there, and an emptied box keeping its rows.
  6. NAMES CHANGED: found by their new words at once, never by their old.
  7. THE PEOPLE WHO WERE HERE FIRST: `flask social words`, counted, written,
     and again writing nothing.
  8. THE READS on their indexes (SQLite's own plan), and the same few a page
     whether a search finds three people or twenty-two.
  9. KIND: a search's People part fades out and back with the tiles, changed
     only unseen, read on every frame; the page does not scroll.
 10. CONTRAST AND TARGETS: the mock's own figures (the name 16.86 / 16.56,
     the @handle 7.10 / 10.12, the headings 16.86 / 16.56 on the page
     ground), read off the paint too; every word at 4.5:1, every target
     44px, the box 16px.
 11. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALSEARCH_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Finding people".
"""
import io
import json
import math
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALSEARCH_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALSEARCH {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence finding people works.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialsearch-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialsearch-" + secrets.token_hex(8),
           SKRIBL_CSRF_PROTECT="1", SKRIBL_SOCIAL_FIRST_INVITE=FIRST, SKRIBL_STAND_IN="0",
           SKRIBL_TRUSTED_PROXIES="1", SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000")
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_DEMO_IDENTITY",
          "SKRIBL_DEMO_LOGIN_KEY", "SKRIBL_SOCIAL_HOSTS", "SKRIBL_SQLITE_FOREIGN_KEYS"):
    ENV.pop(k, None)
subprocess.run([sys.executable, "-c", "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=ENV, check=True, capture_output=True, timeout=120)
_logf = open(LOG, "w")
SERVER = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(PORT), "--no-reload"],
                          cwd=ROOT, env=ENV, stdout=_logf, stderr=subprocess.STDOUT)


def _stop():
    SERVER.terminate()
    try:
        SERVER.wait(10)
    except subprocess.TimeoutExpired:
        SERVER.kill()


import atexit  # noqa: E402
atexit.register(_stop)
for _ in range(120):
    try:
        with urllib.request.urlopen(BASE + "/api/skribls?limit=1", timeout=2) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(0.25)
else:
    print(f"server on {PORT} did not answer; {open(LOG).read()[-800:]}")
    raise SystemExit(1)

# A PHONE IS A TOUCH PHONE (WORKING-AGREEMENTS): is_mobile and has_touch.
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{150 + _addr[0] // 250}.{_addr[0] % 250}.9"


def db(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def db_write(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def cli(*args):
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", *args, "--base", BASE],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    return out.stdout.strip().splitlines()[-1] if out.returncode == 0 else None


def words_cli(*args):
    """`flask social words` on this suite's database: (exit code, what it said)."""
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", "words", *args],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=180)
    said = (out.stdout.strip().splitlines() or [""])[-1] if out.returncode == 0 else (out.stderr.strip() or out.stdout)[-300:]
    return out.returncode, said


def drawing(n=40, seed=0, size=(816, 612), step=30):
    """A small drawing, as the Pad's Add hands one back: `n` points `step` ms apart."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * step, "start": i == 0} for i in range(n)]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay",
            "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """The site's own requests, without a browser, as a signed-in person (or
    nobody)."""

    def __init__(self, cookies=None, xff=None, origin=BASE):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), _NoRedirect())
        self.xff = xff or address()
        self.origin = origin
        self.token = None
        self.cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in (cookies or []))

    def _req(self, method, path, body=None, headers=None, form=None):
        h = {"X-Forwarded-For": self.xff}
        if self.cookie_header:
            h["Cookie"] = self.cookie_header
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        if method == "POST" and self.origin:
            h["Origin"] = self.origin
        h.update(headers or {})
        req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
        try:
            with self.op.open(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)

    def get(self, path):
        st, text, _ = self._req("GET", path)
        m = re.search(r'<meta name="social-csrf" content="([^"]+)"', text)
        if m:
            self.token = m.group(1)
        return st, text

    def get_json(self, path):
        st, text, headers = self._req("GET", path, headers={"Accept": "application/json"})
        try:
            return st, json.loads(text), headers
        except ValueError:
            return st, text, headers

    def post_json(self, path, body, token=None):
        st, text, _ = self._req("POST", path, body=body,
                                headers={"X-Social-CSRF": self.token or "" if token is None else token})
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, form):
        return self._req("POST", path, form=dict(form, csrf=self.token or ""))[:2]


class Person:
    """One browser with its own passkey, from an address of its own."""

    def __init__(self, b, screen="phone", scheme="light"):
        self.xff = address()
        self.ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": self.xff},
                                 **(PHONE if screen == "phone" else DESK))
        self.ctx.add_init_script(WATCH)
        self.pg = self.ctx.new_page()
        tag = f"{screen}/{scheme}"
        self.pg.on("pageerror", lambda e: ERRS.append(f"{tag} pageerror: {e} @ {self.pg.url}"))
        self.pg.on("console", lambda m: ERRS.append(f"{tag} console {m.type}: {m.text[:160]}")
                   if m.type == "error" and "Failed to load resource" not in m.text else None)
        cdp = self.ctx.new_cdp_session(self.pg)
        cdp.send("WebAuthn.enable")
        cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
            "protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True,
            "isUserVerified": True, "automaticPresenceSimulation": True}})
        self.handle = None

    def client(self):
        return Client(cookies=self.ctx.cookies(BASE), xff=self.xff)

    def csp(self):
        try:
            return self.pg.evaluate("() => window.__csp || []")
        except Exception:
            return []


def browser_as(b, who, screen="phone", scheme="light", reduced=False, init=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **(PHONE if screen == "phone" else DESK), **kw)
    ctx.add_init_script(WATCH)
    for s in ([init] if isinstance(init, str) else (init or [])):
        ctx.add_init_script(s)
    if who:
        ctx.add_cookies([{k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly",
                                                             "sameSite", "secure", "expires")}
                         for c in who.ctx.cookies(BASE)])
    pg = ctx.new_page()
    tag = f"{screen}/{scheme}{' reduced' if reduced else ''} as {who.handle if who else 'nobody'}"
    pg.on("pageerror", lambda e: ERRS.append(f"{tag} pageerror: {e} @ {pg.url}"))
    pg.on("console", lambda m: ERRS.append(f"{tag} console {m.type}: {m.text[:160]}")
          if m.type == "error" and "Failed to load resource" not in m.text else None)
    return ctx, pg


def close_ctx(ctx, pg):
    try:
        ERRS.extend(f"csp: {v}" for v in pg.evaluate("() => window.__csp || []"))
    except Exception:
        pass
    ctx.close()


_people = {}


def member(b, handle, name):
    """Somebody who joined through an invite (the first through the first
    invite code), signed in, in a browser of their own."""
    p = Person(b)
    link = (BASE + "/social/join#" + FIRST) if not db("select id from social_people limit 1") else cli("invite")
    pg = p.pg
    pg.goto(link)
    pg.wait_for_function("() => { const c = document.querySelector('[data-link]'); return !!c && !c.classList.contains('is-checking'); }",
                         timeout=15000)
    pg.fill("#joinName", name)
    pg.fill("#joinHandle", handle)
    pg.check("#joinAge")
    with pg.expect_navigation(timeout=20000):
        pg.click("form[data-passkey] button[type=submit]")
    p.handle = handle
    _people[handle] = p
    return p


def someone(b, handle, name):
    return _people.get(handle) or member(b, handle, name)


def make_post(who, words, seed=0):
    """A post as the composer sends one: its public id, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def act(who, path, body=None):
    c = who.client()
    c.get("/social/")
    return c.post_json(path, body if body is not None else {})[0]


def follow(who, handle, on=True):
    return act(who, f"/social/@{handle}/follow", {"following": on})


def block(who, handle):
    return act(who, f"/social/@{handle}/block")


def mute(who, handle):
    return act(who, f"/social/@{handle}/mute")


def ready(pg):
    """The page and its deferred scripts (they have all run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def press(pg, loc):
    """A finger on a phone (a touch phone taps), a click on a desk."""
    if isinstance(loc, str):
        loc = pg.locator(loc).first
    if pg.evaluate("() => matchMedia('(pointer: coarse)').matches"):
        loc.tap(timeout=5000)
    else:
        loc.click(timeout=5000)


def press_at(pg, x, y):
    if pg.evaluate("() => matchMedia('(pointer: coarse)').matches"):
        pg.touchscreen.tap(x, y)
    else:
        pg.mouse.click(x, y)


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def off_paint(pg, box, ground_pt):
    """The most different pixel inside `box` against the ground at a point
    beside it (its own ground, painted), and that ground."""
    if not box:
        return None
    png = pg.screenshot(scale="device")
    im = Image.open(io.BytesIO(png)).convert("RGB")
    k = im.width / pg.viewport_size["width"]
    gpx = im.getpixel((int(ground_pt[0] * k), int(ground_pt[1] * k)))
    x0, y0, w, h = [int(v * k) for v in box]
    best = max((ratio(im.getpixel((x, y)), gpx) for x in range(x0, x0 + max(1, w)) for y in range(y0, y0 + max(1, h))
                if 0 <= x < im.width and 0 <= y < im.height), default=1)
    return {"ground": gpx, "best": round(best, 2)}


_extra = [0]


def person_row(handle, name):
    """Somebody written straight into the site's table (no passkey, never
    signed in), as the people who joined before finding people are: no ways
    of being found until `flask social words` gives them theirs. Their id."""
    con = sqlite3.connect(DB, timeout=10)
    try:
        _extra[0] += 1
        cur = con.execute("insert into social_people (public_id, handle, handle_key, display_name, user_handle,"
                          " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, 0, 1,"
                          " strftime('%Y-%m-%d %H:%M:%f000', 'now'), strftime('%Y-%m-%d %H:%M:%f000', 'now'))",
                          (f"site:fp{_extra[0]:05d}{secrets.token_hex(4)}", handle, handle.lower(), name,
                           secrets.token_bytes(32)))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def ensure_row(handle, name):
    got = db("select id from social_people where handle_key = ?", (handle.lower(),))
    return got[0][0] if got else person_row(handle, name)


# THE PEOPLE EVERY SECTION IS READ AGAINST, written straight into the table and
# then given their ways of being found by the site's own fill: "pa" finds
# Theo Park (a member, whom Mira follows) and these three; "xa" Xan Duvall by
# his first word and Ana Xavier (Mira follows her) by her last; Max Box has
# "ax" only in the middle of words; Zoë Ångström wears accents; Xia (Mira
# blocked her) and Xu (who blocked Mira) and Xee (taken down) start with x;
# Quill (Mira muted him); and "kiwi" finds twenty-two for Mira: Kiwi 07 (she
# follows him) first, Kiwi Kiwi (two words that both start with it, so twice
# in the index), Kiwi 01 to 20 but 07, 13 (blocked) and 17 (taken down), two
# called Kiwi Twin (one word for both: who joined first first, the 20th and
# 21st rows, either side of a page's end), and Rae Fruit by his @kiwifan.
ROWS = ([("pam", "Pam Lee"), ("pazr", "Paz Ruiz"), ("patti", "Patti Sun"),
         ("xduv", "Xan Duvall"), ("anax", "Ana Xavier"), ("maxbox", "Max Box"), ("zoea", "Zoë Ångström"),
         ("xiab", "Xia Block"), ("xublk", "Xu Blocker"), ("xeed", "Xee Down"), ("qmute", "Quill Mute"),
         ("kk2", "Kiwi Kiwi")]
        + [(f"kiwi{i:02d}", f"Kiwi {i:02d}") for i in range(1, 21)]
        + [("kiwitwa", "Kiwi Twin"), ("kiwitwb", "Kiwi Twin"), ("kiwifan", "Rae Fruit")])
KIWI = (["kiwi07", "kk2"] + [f"kiwi{i:02d}" for i in range(1, 21) if i not in (7, 13, 17)]
        + ["kiwitwa", "kiwitwb", "kiwifan"])
W = {}


def world(b):
    """The people above, made once, whichever section runs first: Mira (who
    looks), Theo Park and Jorge Rivas join; the rest are written straight
    into the table and filled; Mira follows, blocks and mutes; Theo posts."""
    if W:
        return W
    mira = someone(b, "mira", "Mira Lopez")
    theo = someone(b, "theo", "Theo Park")
    jorge = someone(b, "jrivas", "Jorge Rivas")
    for h, n in ROWS:
        ensure_row(h, n)
    W["fill"] = words_cli("--write")
    for h in ("theo", "anax", "kiwi07"):
        follow(mira, h)
    for h in ("xiab", "kiwi13"):
        block(mira, h)
    db_write("insert into social_blocks (blocker_id, blocked_id, created_at) select x.id, y.id,"
             " strftime('%Y-%m-%d %H:%M:%f000', 'now') from social_people x, social_people y"
             " where x.handle_key = 'xublk' and y.handle_key = 'mira'")
    db_write("update social_people set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now')"
             " where handle_key in ('xeed', 'kiwi17')")
    mute(mira, "qmute")
    W["post"] = make_post(theo, "Park bench, drawn on the spot", seed=11)
    W.update(mira=mira, theo=theo, jorge=jorge)
    return W


def rows_of(html):
    """The people in a page's (or an answer's) rows, in order: [(handle, what
    their Follow is: "follow", "following", "out" (signed out) or None (your
    own row))]."""
    out = []
    for li in re.findall(r'<li class="fp-row">(.*?)</li>', html or "", re.S):
        h = re.search(r'<a class="fp-who" href="/social/@([^"]+)"', li)
        btn = re.search(r'<button class="btn fo-btn( is-following)?"[^>]*?(data-follow-out)?[ >]', li)
        state = None
        if btn:
            state = "out" if "data-follow-out" in li else ("following" if btn.group(1) else "follow")
        out.append(("@" + h.group(1) if h else None, state))
    return out


def found(client, q, pages=False):
    """Who See all finds for `q`, walked to its end with Load more, as the
    page's own script asks: [handle, ...] (and the pages' sizes and the
    cursors, with `pages`)."""
    got, sizes, cursors = [], [], []
    st, j, _ = client.get_json("/social/explore/more?who=people&q=" + urllib.parse.quote(q))
    while isinstance(j, dict) and st == 200:
        rows = [h for h, _ in rows_of(j.get("html"))]
        got += rows
        sizes.append(len(rows))
        if not j.get("next") or len(sizes) > 20:
            break
        cursors.append(j["next"])
        st, j, _ = client.get_json("/social/explore/more?who=people&q=" + urllib.parse.quote(q)
                                   + "&before=" + urllib.parse.quote(j["next"]))
    return (got, sizes, cursors) if pages else got


def search_box(pg, words):
    """`words` typed into the Gallery's box, key by key, and the search's answer
    waited for (the swap faded back)."""
    pg.fill("[data-gal-q]", "")
    pg.focus("[data-gal-q]")
    pg.keyboard.type(words, delay=30)
    pg.wait_for_timeout(450)
    try:
        pg.wait_for_function("() => { const s = document.querySelector('[data-gal-swap]'); return !s.classList.contains('is-out')"
                             " && getComputedStyle(s).opacity === '1'; }", timeout=8000)
    except Exception:  # noqa: BLE001 -- a search that never comes back is its row's own red
        pass
    pg.wait_for_timeout(300)


# THE PEOPLE PART AND WHAT IS AROUND IT, where each is on the screen.
LAYOUT = r"""() => { const s = document.querySelector('[data-gal-swap]'); if (!s) return null;
  const y = e => e ? Math.round(e.getBoundingClientRect().top + scrollY) : null;
  const heads = [...s.querySelectorAll('h2')].map(h => [h.textContent.trim(), h.classList.contains('sr') ? 'sr' : 'seen', y(h)]);
  const rows = [...s.querySelectorAll('.fp-row')].map(li => [(li.querySelector('.fp-words span') || {}).textContent, y(li)]);
  const all = s.querySelector('.fp-all a'), tile = s.querySelector('.gal-tile'), q = document.querySelector('[data-gal-q]');
  const qr = q && q.getBoundingClientRect();
  return { heads, rows, all: all ? [all.textContent.replace(/\s+/g, ' ').trim(), all.getAttribute('href'), y(all)] : null,
           tile: y(tile), tiles: s.querySelectorAll('.gal-tile').length, title: document.title,
           h1: (document.querySelector('.page-title') || {}).textContent,
           pills: [!!document.querySelector('[data-gal-show]'), !!document.querySelector('[data-gal-sort]')],
           box: q ? [q.type, q.getAttribute('aria-label'), q.placeholder, parseFloat(getComputedStyle(q).fontSize), Math.round(qr.height), q.value] : null,
           more: (() => { const m = s.querySelector('[data-gal-next]'); return m ? !m.hidden : null; })(),
           none: [...s.querySelectorAll('[data-gal-none]')].filter(n => !n.hidden).map(n => n.getAttribute('data-gal-none')),
           path: location.pathname + location.search }; }"""

# A PERSON'S ROW, as it is laid out and painted: its height, the face, the
# name's and the @handle's sizes, weights and inks (against the page's own
# tokens, probed), Follow's size (and its width with the other word), and
# whether each is painted where it stands.
ROW = r"""(i) => { const li = document.querySelectorAll('.fp-row')[i]; if (!li) return null;
  li.scrollIntoView({ block: 'center' });
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  const r = li.getBoundingClientRect(), a = li.querySelector('.fp-who'), f = li.querySelector('.face-ring');
  const n = li.querySelector('.fp-words b'), h = li.querySelector('.fp-words span'), btn = li.querySelector('.fo-btn');
  const at = e => { if (!e) return null; const q = e.getBoundingClientRect(), x = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    return !!x && (x === e || e.contains(x)); };
  const fr = f.getBoundingClientRect(), nr = n.getBoundingClientRect(), hr = h.getBoundingClientRect(), ar = a.getBoundingClientRect();
  const rule = parseFloat(getComputedStyle(li).borderTopWidth) || 0;
  let bw = null;
  if (btn) { const w0 = btn.getBoundingClientRect().width; btn.classList.toggle('is-following');
    const w1 = btn.getBoundingClientRect().width; btn.classList.toggle('is-following'); bw = [Math.round(w0 * 10) / 10, Math.round(w1 * 10) / 10]; }
  const ns = getComputedStyle(n), hs = getComputedStyle(h);
  return { h: Math.round(r.height * 10) / 10, w: Math.round(r.width), face: [Math.round(fr.width), Math.round(fr.height), getComputedStyle(f).borderRadius],
           name: [ns.fontSize, ns.fontWeight, ns.color === probe('var(--ink)'), n.textContent],
           handle: [hs.fontSize, hs.fontWeight, hs.color === probe('var(--ink-2)'), h.textContent],
           btn: btn ? [Math.round(btn.getBoundingClientRect().height), bw] : null,
           link: [Math.round(ar.height + rule), Math.round(ar.left - r.left)], rule, wordsEnd: Math.round(Math.max(nr.right, hr.right)),
           btnStart: btn ? Math.round(btn.getBoundingClientRect().left) : null,
           painted: { face: at(f), name: at(n), handle: at(h), btn: btn ? at(btn) : null } }; }"""

# Every word under `sel` at 4.5:1 on what is painted behind it; every target
# 44px; every text field 16px (verify_socialfollow's READ: a word at opacity 0,
# the Follow button's other word, is not painted, so not read; a pill's button
# is a 44px target where a tap 21px above and below its middle lands on it).
READ = r"""(sel) => {
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => c[3] >= 1 ? c : [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const SKRIBLS = '.skribl-inline, .skribl-inline-line, #skriblGallery, .skribl-face';
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99, words: [] };
  const roots = [...document.querySelectorAll(sel || 'main, header.top, nav.nav')];
  roots.forEach(root => [root, ...root.querySelectorAll('*')].forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
    const c = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;
    let op = 1; for (let n = e; n && n !== document.documentElement; n = n.parentElement) op *= +getComputedStyle(n).opacity;
    if (op < 0.01) return;
    const fg = rgba(getComputedStyle(e).color); fg[3] *= op;
    const g = ground(e), col = over(fg, g), k = ratio(col, g);
    out.read++;
    out.words.push(e.textContent.trim().slice(0, 24));
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 30) + '" ' + k.toFixed(2));
  }));
  document.querySelectorAll('a[href], button, input, textarea, select, [role=button]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (e.matches('.fo-seg > button')) { const mid = r.left + r.width / 2, hit = d => { const x = document.elementFromPoint(mid, r.top + r.height / 2 + d);
                                           return !!x && (x === e || e.contains(x)); };
                                         if (r.width >= 44 && hit(0) && hit(-21) && hit(21)) return; }
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

# A word's own ink against what it sits on, the mock's way (fp_mock.py's
# CONTRAST): its colour against the first painted ground up its parents.
CALC = r"""(sel) => { const el = document.querySelector(sel); if (!el) return null;
  el.scrollIntoView({ block: 'center' });
  const rgb = s => s.match(/[\d.]+/g).slice(0, 3).map(Number);
  const lum = c => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  let bg = el, b = 'rgba(0, 0, 0, 0)'; while (bg && (b = getComputedStyle(bg).backgroundColor) && /rgba\(.*, 0\)$/.test(b)) bg = bg.parentElement;
  const f = rgb(getComputedStyle(el).color), k = rgb(b), L1 = lum(f), L2 = lum(k);
  const r = el.getBoundingClientRect(), t = document.createRange(); t.selectNodeContents(el); const g = t.getBoundingClientRect();
  return { ratio: Math.round(100 * (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)) / 100, ink: getComputedStyle(el).color, ground: b,
           box: [g.left, g.top, g.width, g.height], beside: [Math.max(1, r.left - 4), r.top + r.height / 2] }; }"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the Gallery's box finds people: its words; People first, up to three, See all, then Drawings;"
               " no search as before; the pills change the drawings alone"):
        try:
            w = world(b)
            mira = w["mira"]
            lay = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, mira, screen, "light")
                go(pg, "/social/explore?q=pa", wait=500)
                lay[(screen, "pa")] = pg.evaluate(LAYOUT)
                go(pg, "/social/explore", wait=500)
                lay[(screen, "none")] = pg.evaluate(LAYOUT)
                go(pg, "/social/explore?q=pa&show=following&sort=hot", wait=500)
                lay[(screen, "pills")] = pg.evaluate(LAYOUT)
                close_ctx(ctx, pg)
            boxes = {" ".join(k): v and v["box"] for k, v in lay.items()}
            check("the Gallery's box says \"Search people and drawings\", its placeholder and its name to a screen"
                  " reader alike, 16px or more and 44px tall, phone and desk",
                  all(v and v[:3] == ["search", "Search people and drawings", "Search people and drawings"]
                      and v[3] >= 16 and v[4] >= 44 for v in boxes.values()), json.dumps(boxes))
            three = ["@theo", "@pam", "@patti"]
            order = {}
            for screen in ("phone", "desk"):
                v = lay[(screen, "pa")] or {}
                hs = v.get("heads") or []
                ys = ([hs[0][2]] if hs else []) + [r[1] for r in v.get("rows") or []] + ([v["all"][2]] if v.get("all") else []) \
                    + ([hs[1][2]] if len(hs) > 1 else []) + [v.get("tile")]
                order[screen] = {"heads": [h[:2] for h in hs], "rows": [r[0] for r in v.get("rows") or []],
                                 "all": (v.get("all") or [None, None])[:2], "tiles": v.get("tiles"),
                                 "down": all(isinstance(a, int) and isinstance(c, int) and a < c for a, c in zip(ys, ys[1:]))
                                 and len(ys) == 7}
            check("with a search, People comes first: its heading, up to three people (Theo Park first, whom Mira"
                  " follows, then Pam Lee and Patti Sun), \"See all\" since there are more (to the people alone,"
                  " ?q=pa&who=people), then the \"Drawings\" heading and the tiles, top to bottom, phone and desk",
                  all(o["heads"] == [["People", "seen"], ["Drawings", "seen"]] and o["rows"] == three
                      and o["all"] == ["See all people›", "/social/explore?q=pa&who=people"] and o["tiles"] >= 1
                      and o["down"] for o in order.values()) and len(order) == 2, json.dumps(order))
            plain = {s: lay[(s, "none")] for s in ("phone", "desk")}
            check("no search, the Gallery as it was: no People, no \"See all\", the drawings' heading for a screen"
                  " reader alone, then the tiles",
                  all(v and v["heads"] == [["Drawings", "sr", v["heads"][0][2]]] and not v["rows"] and not v["all"]
                      and v["tiles"] >= 1 for v in plain.values()), json.dumps(plain))
            pills = {s: [r[0] for r in (lay[(s, "pills")] or {}).get("rows") or []] for s in ("phone", "desk")}
            check("the pills change the drawings alone: at Following and Hot, People is the same three, followed first",
                  all(v == three for v in pills.values()), json.dumps(pills))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "a person's row: 64px, the face 44, the name 17px 600, the @handle 15px, Follow 44px tall and one"
               " width; painted where it stands; your own row has no Follow"):
        try:
            w = world(b)
            mira = w["mira"]
            rows = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    ctx, pg = browser_as(b, mira, screen, scheme)
                    go(pg, "/social/explore?q=pa", wait=500)
                    rows[(screen, scheme)] = [pg.evaluate(ROW, i) for i in range(3)]
                    go(pg, "/social/explore?q=mira", wait=500)
                    rows[(screen, scheme, "mine")] = [pg.evaluate(ROW, 0), pg.evaluate("() => document.querySelectorAll('.fp-row').length")]
                    close_ctx(ctx, pg)
            ok = {}
            for k, rs in rows.items():
                if len(k) == 3:
                    continue
                ok[" ".join(k)] = all(r and r["h"] == 64 and r["face"] == [44, 44, "50%"]
                                      and r["name"][:3] == ["17px", "600", True] and r["handle"][:3] == ["15px", "400", True]
                                      and r["btn"] and r["btn"][0] == 44 and r["btn"][1][0] == r["btn"][1][1]
                                      and r["link"] == [64, 0] and r["wordsEnd"] <= r["btnStart"] for r in rs)
            check("each row 64px: the face 44px round, the name 17px 600 in the first ink, the @handle 15px in the"
                  " second, the row's link its whole height (under the card's 1px rule between two rows) from its"
                  " start, the words ending before Follow, and Follow"
                  " 44px tall and one width with \"Follow\" and \"Following\" (both words in one cell, as on a"
                  " profile); phone and desk, light and dark",
                  len(ok) == 4 and all(ok.values()), json.dumps({"ok": ok, "first": rows.get(("phone", "light"), [None])[0]})[:900])
            painted = {" ".join(k): [r and r["painted"] for r in rs] for k, rs in rows.items() if len(k) == 2}
            check("...each painted where it stands: the face, the name, the @handle and Follow are what is under their"
                  " own middles, on every row",
                  len(painted) == 4 and all(p and all(p.values()) for v in painted.values() for p in v), json.dumps(painted)[:700])
            mine = {" ".join(k[:2]): rs for k, rs in rows.items() if len(k) == 3}
            check("your own row has no Follow, as your own page has none: Mira finds herself (\"mira\"), her row 64px"
                  " and one link, nothing at its end",
                  len(mine) == 4 and all(v[1] == 1 and v[0] and v[0]["btn"] is None and v[0]["h"] == 64
                                          and v[0]["handle"][3] == "@mira" for v in mine.values()),
                  json.dumps({k: [v[1], v[0] and v[0]["btn"], v[0] and v[0]["h"]] for k, v in mine.items()}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "a tap: anywhere on a row but Follow opens their page; Follow follows and the page stays; Following"
               " asks once; signed out, Follow asks to sign in"):
        try:
            w = world(b)
            mira = w["mira"]
            opened = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, mira, screen, "light")
                for where in ("face", "name", "ground"):
                    go(pg, "/social/explore?q=pa", wait=400)
                    pt = pg.evaluate("""(where) => { const li = document.querySelectorAll('.fp-row')[1]; li.scrollIntoView({ block: 'center' });
                      const f = li.querySelector('.face-ring').getBoundingClientRect(), n = li.querySelector('.fp-words b').getBoundingClientRect(),
                            w = li.querySelector('.fp-words').getBoundingClientRect(), b = li.querySelector('.fo-btn').getBoundingClientRect(),
                            r = li.getBoundingClientRect();
                      if (where === 'face') return [f.left + f.width / 2, f.top + f.height / 2];
                      if (where === 'name') return [n.left + n.width / 2, n.top + n.height / 2];
                      return [(w.right + b.left) / 2, r.top + r.height / 2]; }""", where)
                    try:
                        with pg.expect_navigation(timeout=6000):
                            press_at(pg, pt[0], pt[1])
                        pg.wait_for_timeout(200)
                    except Exception:  # noqa: BLE001 -- staying put is the row's own red
                        pass
                    opened[f"{screen} {where}"] = urllib.parse.urlparse(pg.url).path
                close_ctx(ctx, pg)
            check("a tap anywhere on a row but Follow opens their page: on the face, on the name, on the row's ground"
                  " between the words and Follow (a touch on a phone, a click on a desk)",
                  len(opened) == 6 and all(v == "/social/@pam" for v in opened.values()), json.dumps(opened))
            # FOLLOW, AS ON THEIR PAGE: the second row's (Pam's) Follow, on a phone.
            fo = {}
            ctx, pg = browser_as(b, mira, "phone", "light")
            go(pg, "/social/explore?q=pa", wait=500)
            btn = pg.locator(".fp-row").nth(1).locator(".fo-btn")
            before = db("select count(*) from social_follows f join social_people a on a.id = f.follower_id join social_people"
                        " o on o.id = f.followed_id where a.handle_key = 'mira' and o.handle_key = 'pam' and f.ended_at is null")[0][0]
            press(pg, btn)
            pg.wait_for_timeout(900)
            fo["after"] = pg.evaluate("""() => [...document.querySelectorAll('.fp-row')].map(li => { const b = li.querySelector('.fo-btn');
              return [li.querySelector('.fp-words span').textContent, b ? b.classList.contains('is-following') : null, b ? b.getAttribute('aria-label') : null]; })""")
            fo["path"] = urllib.parse.urlparse(pg.url).path + "?" + urllib.parse.urlparse(pg.url).query
            fo["db"] = db("select count(*) from social_follows f join social_people a on a.id = f.follower_id join social_people"
                          " o on o.id = f.followed_id where a.handle_key = 'mira' and o.handle_key = 'pam' and f.ended_at is null")[0][0]
            press(pg, btn)
            pg.wait_for_timeout(600)
            fo["sheet"] = pg.evaluate("""() => { const w = document.getElementById('unfollowSheet');
              return w ? [w.classList.contains('is-open'), (w.querySelector('.make-title') || {}).textContent, (w.querySelector('.post-lede') || {}).textContent] : null; }""")
            press(pg, "#unfollowSheet [data-unfollow]")
            pg.wait_for_timeout(900)
            fo["back"] = pg.evaluate("() => { const b = document.querySelectorAll('.fp-row')[1].querySelector('.fo-btn'); return [b.classList.contains('is-following'), b.getAttribute('aria-label')]; }")
            fo["db2"] = db("select count(*) from social_follows f join social_people a on a.id = f.follower_id join social_people"
                           " o on o.id = f.followed_id where a.handle_key = 'mira' and o.handle_key = 'pam' and f.ended_at is null")[0][0]
            close_ctx(ctx, pg)
            check("a tap on Follow follows them and the page stays: Pam's button turns to Following (\"Following Pam"
                  " Lee\"), the others as they were, the site keeps it, the address the same",
                  before == 0 and fo["db"] == 1 and fo["path"] == "/social/explore?q=pa"
                  and fo["after"] == [["@theo", True, "Following Theo Park"], ["@pam", True, "Following Pam Lee"],
                                      ["@patti", False, "Follow Patti Sun"]], json.dumps(fo))
            check("a tap on Following asks once, the sheet naming the row's person (\"Unfollow Pam?\", \"You’ll still"
                  " see Pam’s posts under Everyone. They aren’t told.\"), and Unfollow ends it, the button back to Follow",
                  fo["sheet"] and fo["sheet"][0] and fo["sheet"][1] == "Unfollow Pam?"
                  and fo["sheet"][2] == "You’ll still see Pam’s posts under Everyone. They aren’t told."
                  and fo["back"] == [False, "Follow Pam Lee"] and fo["db2"] == 0, json.dumps(fo))
            # SIGNED OUT: a search typed in the box, then Follow.
            ctx, pg = browser_as(b, None, "phone", "light")
            go(pg, "/social/explore", wait=400)
            search_box(pg, "pa")
            out = {"rows": [h for h, _ in rows_of(pg.evaluate("() => document.querySelector('[data-gal-swap]').innerHTML"))]}
            press(pg, pg.locator(".fp-row").nth(0).locator(".fo-btn"))
            pg.wait_for_timeout(600)
            out["sheet"] = pg.evaluate("""() => { const w = document.getElementById('followOutSheet'); if (!w) return null;
              const a = w.querySelector('.post-sheet-acts a'); return [w.classList.contains('is-open'), (w.querySelector('.make-title') || {}).textContent,
              (w.querySelector('.post-lede') || {}).textContent, a ? a.getAttribute('href') : null]; }""")
            out["kept"] = db("select count(*) from social_follows f join social_people o on o.id = f.followed_id where o.handle_key = 'pam'"
                             " and f.ended_at is null")[0][0]
            close_ctx(ctx, pg)
            check("signed out, the search finds people too, and Follow raises \"Follow Pam?\" (\"Sign in, and Pam’s new"
                  " posts show first on your Home.\"), Sign in coming back to the search as it is now"
                  " (next=/social/explore?q=pa, typed after the page came); nothing followed",
                  out["rows"] == ["@pam", "@theo", "@patti"] and out["sheet"] and out["sheet"][0]
                  and out["sheet"][1] == "Follow Pam?" and out["sheet"][2] == "Sign in, and Pam’s new posts show first on your Home."
                  and out["sheet"][3] == "/social/signin?next=" + urllib.parse.quote("/social/explore?q=pa", safe="")
                  and out["kept"] == 0, json.dumps(out))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "who is found: any word of a name, never mid-word; an @handle's start; case, @ and accents put aside;"
               " the people you follow first; nobody a block hides, nobody taken down; a mute changes nothing"):
        try:
            w = world(b)
            mc = w["mira"].client()
            anon = Client()
            got = {q: found(mc, q) for q in ("xa", "box", "theo pa", "ax", "ar", "x", "qui")}
            nobody = {q: found(anon, q) for q in ("xa", "xdu", "@xduv", "@XDU", "XAN", "zoe", "angst", "Ång", "x")}
            check("any word of a name: \"xa\" finds Ana Xavier by her last word and Xan Duvall by his first, \"box\" Max"
                  " Box, \"theo pa\" Theo Park; never the middle of a word: \"ax\" and \"ar\" find nobody (Max Box, Theo"
                  " Park and @anax hold them only inside a word)",
                  got["xa"] == ["@anax", "@xduv"] and got["box"] == ["@maxbox"] and got["theo pa"] == ["@theo"]
                  and got["ax"] == [] and got["ar"] == [], json.dumps(got))
            check("an @handle's start (\"xdu\", \"@xduv\": Xan Duvall), case and a leading @ put aside (\"@XDU\","
                  " \"XAN\"), and accents (\"zoe\", \"angst\" and \"Ång\" find Zoë Ångström)",
                  all(nobody[q] == ["@xduv"] for q in ("xdu", "@xduv", "@XDU", "XAN"))
                  and all(nobody[q] == ["@zoea"] for q in ("zoe", "angst", "Ång")), json.dumps(nobody))
            check("the people Mira follows first: \"xa\" gives Ana Xavier (followed) before Xan Duvall, though Xan's"
                  " word comes first, as it does for somebody signed out",
                  got["xa"] == ["@anax", "@xduv"] and nobody["xa"] == ["@xduv", "@anax"], json.dumps([got["xa"], nobody["xa"]]))
            check("nobody a block hides, either way, and nobody taken down: \"x\" gives Mira Ana Xavier and Xan Duvall"
                  " alone (not Xia, whom she blocked, Xu, who blocked her, or Xee, taken down); signed out, Xia and Xu"
                  " are there (a block is between two people), and Xee still not",
                  got["x"] == ["@anax", "@xduv"] and nobody["x"] == ["@xduv", "@anax", "@xiab", "@xublk"],
                  json.dumps([got["x"], nobody["x"]]))
            check("a mute changes nothing here: Quill, whom Mira muted, is found (\"qui\"): their page stays open to"
                  " her, as it always has", got["qui"] == ["@qmute"], json.dumps(got["qui"]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "See all: the people alone, twenty a page; walked to its end, everybody once, none missed, in order;"
               " Load more in place; the address and the back button; a new search there"):
        try:
            w = world(b)
            mira = w["mira"]
            ctx, pg = browser_as(b, mira, "desk", "light")
            # The search typed into the Gallery's box, as a person types it: its
            # address follows it (replaced, not a new step back).
            go(pg, "/social/explore", wait=500)
            search_box(pg, "kiwi")
            first = pg.evaluate(LAYOUT)
            with pg.expect_navigation(timeout=8000):
                pg.click(".fp-all a")
            ready(pg)
            pg.wait_for_timeout(400)
            alone = pg.evaluate(LAYOUT)
            check("See all is this page asked for the people alone (?q=kiwi&who=people): its heading \"People\", the"
                  " box holding the search, no pills (they change drawings), the first twenty and Load more",
                  first and [r[0] for r in first["rows"]] == ["@kiwi07", "@kk2", "@kiwi01"]
                  and alone and alone["path"] == "/social/explore?q=kiwi&who=people" and alone["h1"] == "People"
                  and alone["title"] == "People · Blooby" and alone["box"][5] == "kiwi" and alone["pills"] == [False, False]
                  and len(alone["rows"]) == 20 and alone["more"] is True and not alone["tiles"],
                  json.dumps({"first": first and first["rows"], "alone": alone and {k: alone[k] for k in
                              ("path", "h1", "title", "pills", "more")}, "n": alone and len(alone["rows"])}))
            # LOAD MORE, IN PLACE.
            pg.evaluate("() => document.querySelector('[data-gal-next]').scrollIntoView({ block: 'center' })")
            pg.wait_for_timeout(300)
            tops0 = pg.evaluate("() => [...document.querySelectorAll('.fp-row')].map(li => Math.round(li.getBoundingClientRect().top + scrollY))")
            y0 = pg.evaluate("() => scrollY")
            pg.click("[data-gal-next]")
            pg.wait_for_function("() => document.querySelectorAll('.fp-row').length > 20", timeout=8000)
            pg.wait_for_timeout(400)
            tops1 = pg.evaluate("() => [...document.querySelectorAll('.fp-row')].map(li => Math.round(li.getBoundingClientRect().top + scrollY))")
            after = pg.evaluate(LAYOUT)
            y1 = pg.evaluate("() => scrollY")
            check("Load more brings the next rows in place: the twenty already there do not move, the page stays where"
                  " it was, the two more follow them, and the button goes (there are no more)",
                  tops1[:20] == tops0 and len(tops1) == 22 and tops1[20] > tops0[-1] and y1 == y0
                  and after["more"] is False and [r[0] for r in after["rows"]][20:] == ["@kiwitwb", "@kiwifan"],
                  json.dumps({"same": tops1[:20] == tops0, "n": len(tops1), "more": after["more"], "y": [y0, y1],
                              "tops": [tops0[-1:], tops1[19:]], "last": [r[0] for r in after["rows"]][18:]}))
            # THE BACK BUTTON: to the Gallery's search as it was left.
            pg.go_back()
            ready(pg)
            pg.wait_for_timeout(500)
            back = pg.evaluate(LAYOUT)
            check("the back button goes back to the Gallery's search as it was left, typed: ?q=kiwi, the box holding"
                  " it, People (Kiwi 07 first) and then Drawings",
                  back and back["path"] == "/social/explore?q=kiwi" and back["box"][5] == "kiwi"
                  and [r[0] for r in back["rows"]] == ["@kiwi07", "@kk2", "@kiwi01"] and back["heads"][1][:2] == ["Drawings", "seen"],
                  json.dumps(back and {k: back[k] for k in ("path", "rows", "heads")}))
            # A NEW SEARCH ON SEE ALL, and an emptied box.
            go(pg, "/social/explore?q=kiwi&who=people", wait=400)
            search_box(pg, "kiwi t")
            twins = pg.evaluate(LAYOUT)
            pg.fill("[data-gal-q]", "")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(900)
            emptied = pg.evaluate(LAYOUT)
            close_ctx(ctx, pg)
            check("a new search on See all brings its own rows and its own address (\"kiwi t\": the two Kiwi Twins);"
                  " an emptied box keeps the rows it has (nothing to find), and the address with them",
                  twins and [r[0] for r in twins["rows"]] == ["@kiwitwa", "@kiwitwb"]
                  and twins["path"] == "/social/explore?q=kiwi%20t&who=people" and twins["more"] is False
                  and emptied and [r[0] for r in emptied["rows"]] == ["@kiwitwa", "@kiwitwb"]
                  and emptied["path"] == twins["path"] and not emptied["tiles"],
                  json.dumps({"twins": twins and [twins["rows"], twins["path"]],
                              "emptied": emptied and [emptied["rows"], emptied["path"], emptied["tiles"]]}))
            # WALKED TO ITS END, as the page's own Load more asks.
            walked, sizes, cursors = found(mira.client(), "kiwi", pages=True)
            people_there = {r[0] for r in db("select handle_key from social_people where handle_key like 'kiwi%' or handle_key = 'kk2'")}
            check("walked to its end with Load more (twenty, then two), every person \"kiwi\" finds, once each, none"
                  " missed: Kiwi 07 first (Mira follows him), Kiwi Kiwi (two of his words start with it, shown once),"
                  " then by the word that found them, the two Kiwi Twins either side of the page's end, Rae Fruit by"
                  " his @kiwifan; never Kiwi 13 (blocked) or 17 (taken down); every one of them in the site's table",
                  ["@" + h for h in KIWI] == walked and sizes == [20, 2] and len(set(walked)) == len(walked)
                  and set(KIWI) <= people_there and all(len(c) <= 400 and not re.search(r"\d{3,}", c) for c in cursors),
                  json.dumps({"got": walked, "sizes": sizes, "cursors": cursors}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "a name changed is found by its new words at once, never by its old"):
        try:
            w = world(b)
            jorge, mc = w["jorge"], w["mira"].client()
            before = {q: found(mc, q) for q in ("jorge", "rivas", "jri")}
            jc = jorge.client()
            jc.get("/social/you/edit")
            st, _ = jc.post_form("/social/you/edit", {"name": "Lola Brooks", "bio": ""})
            after = {q: found(mc, q) for q in ("jorge", "rivas", "jri", "brooks", "lola")}
            check("a name changed in Edit profile is found by its new words at once and never by its old: Jorge Rivas,"
                  " now Lola Brooks, is found by \"brooks\" and \"lola\", and by \"jorge\" and \"rivas\" no more; her"
                  " @handle still finds her",
                  before == {"jorge": ["@jrivas"], "rivas": ["@jrivas"], "jri": ["@jrivas"]} and st == 303
                  and after == {"jorge": [], "rivas": [], "jri": ["@jrivas"], "brooks": ["@jrivas"], "lola": ["@jrivas"]},
                  json.dumps({"before": before, "status": st, "after": after}))
            # A WAY KEPT FROM AN OLD NAME (written straight in, as a stale row would be) finds nobody.
            db_write("insert into social_people_words (person_id, word_key) select id, 'ivan stale' from social_people"
                     " where handle_key = 'jrivas'")
            stale = {q: found(mc, q) for q in ("ivan", "ivan stale")}
            check("...and a key that is not one of her ways now (written straight into the table, as one kept from an"
                  " old name would be) finds nobody: a search shows a person only by their name and handle as they are",
                  stale == {"ivan": [], "ivan stale": []}, json.dumps(stale))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "the people who were here first: `flask social words` counts them, gives them theirs, and again"
               " writes nothing"):
        try:
            w = world(b)
            mc = w["mira"].client()
            for h, n in (("yash", "Yarrow Ash"), ("boyarrow", "Bo Yarrow"), ("yyarrow", "Yan Yarrow")):
                ensure_row(h, n)
            unseen = found(mc, "yarrow")
            dry = words_cli()
            wrote = words_cli("--write")
            seen = found(mc, "yarrow")
            n_words = db("select count(*) from social_people_words")[0][0]
            again = words_cli("--write")
            n_again = db("select count(*) from social_people_words")[0][0]
            check("people written straight into the site's table, as those who joined before finding people are, are"
                  " found by nobody; `flask social words` says how many have no ways yet (3), and with --write gives"
                  " them theirs: then \"yarrow\" finds all three, by a first word and by later ones",
                  w["fill"][0] == 0 and unseen == [] and dry == (0, "words: 3 people have no ways of being found yet (run it"
                                                                     " with --write to give them theirs)")
                  and wrote == (0, "words: 3 people given their ways of being found; 0 left")
                  and seen == ["@boyarrow", "@yyarrow", "@yash"],
                  json.dumps({"world": w["fill"], "unseen": unseen, "dry": dry, "wrote": wrote, "seen": seen}))
            check("run again, it writes nothing and changes nothing: nobody is without theirs (the ways read exactly"
                  " as they were)", again == (0, "words: 0 people given their ways of being found; 0 left") and n_again == n_words,
                  json.dumps({"again": again, "rows": [n_words, n_again]}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    # The reads as the code sends them, planned by SQLite; and how many reads of
    # the people's ways each page makes (cookies: a signed-in viewer's).
    READS = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Person
    from social import people as P
    me = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/explore"):
        for name, call in (("the people you follow", lambda: P.followed(me, "kiwi")),
                           ("everybody else", lambda: P.others(me, "kiwi")),
                           ("signed out", lambda: P.others(None, "kiwi"))):
            rec.clear()
            call()
            calls[name] = [(st, pr) for st, pr in rec if "social_blocks" not in st]
    event.remove(db.engine, "before_cursor_execute", keep)
    conn = db.session.connection()
    plans = {name: [r[3] for st, params in sent for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
             for name, sent in calls.items()}
    seen = []
    def count(conn, cursor, statement, *a):
        if "social_people_words" in statement:
            seen.append(" ".join(statement.split())[:80])
    client = app.test_client(use_cookies=False)
    h = {"Cookie": sys.argv[2], "X-Forwarded-For": "10.250.1.5"}
    pages = {}
    nxt = None
    for name, path in (("the Gallery, pa", "/social/explore?q=pa"), ("the Gallery, kiwi", "/social/explore?q=kiwi"),
                       ("See all, kiwi", "/social/explore?q=kiwi&who=people"),
                       ("Load more, kiwi", "/social/explore/more?q=kiwi&who=people&before="),
                       ("a search typed, kiwi", "/social/explore/more?q=kiwi")):
        if path.endswith("before="):
            first = client.get("/social/explore/more?q=kiwi&who=people", headers=h).get_json()
            path += first["next"]
        seen.clear()
        event.listen(db.engine, "before_cursor_execute", count)
        r = client.get(path, headers=h)
        event.remove(db.engine, "before_cursor_execute", count)
        body = r.get_data(as_text=True)
        if r.is_json:
            body = (r.get_json().get("html") or "") + (r.get_json().get("people") or "")
        pages[name] = [len(seen), body.count('class="fp-row"'), r.status_code]
    print(json.dumps({"plans": plans, "sent": {k: len(v) for k, v in calls.items()}, "pages": pages}))
"""

    if part(8, "the reads on their indexes (SQLite's own plan), and the same few a page whether a search finds three"
               " people or twenty-two"):
        try:
            w = world(b)
            cookie = "; ".join(f"{c_['name']}={c_['value']}" for c_ in w["mira"].ctx.cookies(BASE))
            out = subprocess.run([sys.executable, "-c", READS, "mira", cookie], cwd=ROOT, env=ENV, capture_output=True,
                                 text=True, timeout=180)
            got = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else {"err": out.stderr[-600:]}
            plans = got.get("plans", {})
            on = {"the people you follow": ["ix_social_follows_", "ix_social_people_words_person"],
                  "everybody else": ["ix_social_people_words_key", "ix_social_follows_pair"],
                  "signed out": ["ix_social_people_words_key"]}
            missing = {k: [ix for ix in v if not any(ix in line for line in plans.get(k, []))] for k, v in on.items()}
            scans = {k: [line for line in v if re.match(r"SCAN (social_people|social_people_words|social_follows)\b", line)]
                     for k, v in plans.items()}
            check("the reads on their indexes (SQLite's own plan): the people you follow through your follows and each"
                  " one's ways (ix_social_people_words_person); everybody else on the ways' own index"
                  " (ix_social_people_words_key), whom you follow asked of the pair's; never a scan of the people, the"
                  " ways or the follows",
                  len(plans) == 3 and not any(missing.values()) and not any(scans.values())
                  and got.get("sent") == {"the people you follow": 1, "everybody else": 1, "signed out": 1},
                  json.dumps({"missing": missing, "scans": scans, "sent": got.get("sent"), "plans": plans,
                              "err": got.get("err")})[:1200])
            pages = got.get("pages", {})
            check("the same few reads a page whether a search finds three people or twenty-two: the Gallery with"
                  " People (\"pa\", \"kiwi\"), See all's first twenty, its Load more, and a search typed in the box each"
                  " read the people's ways twice at most",
                  len(pages) == 5 and all(v[0] <= 2 and v[2] == 200 for v in pages.values())
                  and pages["the Gallery, pa"][0] == pages["the Gallery, kiwi"][0] and pages["See all, kiwi"][1] == 20
                  and pages["Load more, kiwi"][1] == 2 and pages["the Gallery, kiwi"][1] == 3
                  and pages["a search typed, kiwi"][1] == 3,
                  json.dumps(pages))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    # Every frame from now for `ms`, into window.__fpFrames: [time, the swap's
    # opacity, the People part's first person (or none), the page's scroll].
    FRAMES = r"""(ms) => { const s = document.querySelector('[data-gal-swap]'), t0 = performance.now(); window.__fpFrames = [];
      (function f() { const r = s.querySelector('.fp-row .fp-words span');
        window.__fpFrames.push([Math.round(performance.now() - t0), +getComputedStyle(s).opacity, r ? r.textContent : null, scrollY]);
        if (performance.now() - t0 < ms) requestAnimationFrame(f); })(); }"""

    if part(9, "kind: a search's People part fades out and back with the tiles, changed only unseen, on every frame;"
               " the page does not scroll"):
        try:
            w = world(b)
            seen = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, w["mira"], screen, "light")
                go(pg, "/social/explore", wait=500)
                pg.focus("[data-gal-q]")
                pg.wait_for_timeout(200)
                y0 = pg.evaluate("() => scrollY")
                pg.evaluate(FRAMES, 2200)
                pg.keyboard.type("kiwi", delay=25)
                pg.wait_for_timeout(2300)
                seen[screen] = (y0, pg.evaluate("() => window.__fpFrames"))
                close_ctx(ctx, pg)
            res = {}
            for screen, (y0, fr) in seen.items():
                came = next((i for i, f in enumerate(fr) if f[2] == "@kiwi07"), None)
                out_ = [f[1] for f in fr[:came]] if came is not None else []
                back_ = [f[1] for f in fr[came:]] if came is not None else []
                res[screen] = {"came_at": fr[came][1] if came is not None else None,
                               "fading": sum(1 for o in out_ if 0.02 < o < 0.98), "rising": sum(1 for o in back_ if 0.02 < o < 0.98),
                               "ends": back_[-1] if back_ else None, "scroll": sorted({f[3] for f in fr}), "at": y0}
            check("a search typed in the box: the tiles and the People part fade out together over several frames, the"
                  " people change only once they cannot be seen (under 5% when Kiwi 07 first shows), and fade back up"
                  " over several frames to whole; the page does not scroll (phone and desk)",
                  len(res) == 2 and all(r["came_at"] is not None and r["came_at"] < 0.05 and r["fading"] >= 2
                                        and r["rising"] >= 2 and r["ends"] == 1 and r["scroll"] == [r["at"]] for r in res.values()),
                  json.dumps(res))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "contrast and targets: the mock's own figures, off the paint too; every word at 4.5:1, every target"
                " 44px, the box 16px"):
        try:
            w = world(b)
            calcs, paints, reads, lows, smalls, fields = {}, {}, {}, [], [], []
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen} {scheme}"
                    for who, path, name in ((w["mira"], "/social/explore?q=pa", "the Gallery, signed in"),
                                            (None, "/social/explore?q=pa", "the Gallery, signed out"),
                                            (w["mira"], "/social/explore?q=kiwi&who=people", "See all")):
                        ctx, pg = browser_as(b, who, screen, scheme)
                        go(pg, path, wait=500)
                        if name == "the Gallery, signed in":
                            for part_, sel in (("name", ".fp-row .fp-words b"), ("handle", ".fp-row .fp-words span"),
                                               ("people", "#fpPeople"), ("drawings", ".fp-box h2.fp-sec:not(#fpPeople)")):
                                c_ = pg.evaluate(CALC, sel)
                                calcs[(tag, part_)] = c_ and c_["ratio"]
                                paints[(tag, part_)] = off_paint(pg, c_ and c_["box"], c_ and c_["beside"])
                            pg.evaluate("() => scrollTo(0, 0)")
                            pg.wait_for_timeout(150)
                        got = pg.evaluate(READ, "main")
                        reads[(tag, name)] = [got["read"], got["lowest"]]
                        lows += [f"{tag} {name}: {x}" for x in got["low"]]
                        smalls += [f"{tag} {name}: {x}" for x in got["small"]]
                        fields += [f"{tag} {name}: {x}" for x in got["fields"]]
                        pg.evaluate("() => { const m = document.querySelector('[data-gal-next]'); if (m && !m.hidden) m.scrollIntoView({ block: 'center' }); }")
                        pg.wait_for_timeout(150)
                        got = pg.evaluate(READ, "main")
                        smalls += [f"{tag} {name} (lower): {x}" for x in got["small"]]
                        lows += [f"{tag} {name} (lower): {x}" for x in got["low"]]
                        close_ctx(ctx, pg)
            mock = {"light": {"name": 16.86, "handle": 7.1, "people": 16.86, "drawings": 16.86},
                    "dark": {"name": 16.56, "handle": 10.12, "people": 16.56, "drawings": 16.56}}
            off = {" ".join(k): v for k, v in calcs.items() if v != mock[k[0].split()[1]][k[1]]}
            check("the mock's own figures, phone and desk: the name 16.86:1 light and 16.56:1 dark on the page's"
                  " ground, the @handle 7.10 and 10.12, the \"People\" and \"Drawings\" headings 16.86 and 16.56",
                  len(calcs) == 16 and not off, json.dumps({"off": off, "all": {" ".join(k): v for k, v in calcs.items()}})[:700])
            check("...and read off the paint: the name, the @handle and both headings 4.5:1 or more against the ground"
                  " beside them, phone and desk, light and dark",
                  len(paints) == 16 and all(v and v["best"] >= 4.5 for v in paints.values()),
                  json.dumps({" ".join(k): v and v["best"] for k, v in paints.items()}))
            check("every word on the Gallery with its People (signed in and out) and on See all at 4.5:1 or more on what"
                  " is painted behind it, every target 44px or more (a row's link, Follow, See all, Load more), the box"
                  " 16px or more; phone and desk, light and dark",
                  len(reads) == 12 and all(v[0] >= 10 for v in reads.values()) and not lows and not smalls and not fields,
                  f"low {lows[:4]}; small {smalls[:4]}; fields {fields[:3]}; read {json.dumps({' / '.join(k): v for k, v in reads.items()})[:400]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
