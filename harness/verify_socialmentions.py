#!/usr/bin/env python3
"""Mentions on the Skribl site (the map, part two, item 4; docs/SOCIAL-SITE.md
section 17; the owner's "All yes" on the mentions mock, Nov 15), through the
demo's own server, with Chromium's virtual authenticator for the site's
people.

  1. THE WORDS: who a post's words mention, and a comment's or an answer's:
     an @handle with nothing of a word or an email right before or after it,
     any case, that is somebody; a handle that is nobody stays words; ten
     people at most, the first ten, each once; every way words are written
     (a post with a drawing, a quote of words alone, an older drawing posted,
     a comment, an answer) writes them beside it, at its time; a handle that
     changes keeps the old words' link, to the person as they are now.
  2. HOW A MENTION LOOKS: a link to their page in the small violet ink
     (--accent-ink), 600, never underlined, the words' own size, on Home's
     card, a post's page, a comment, an answer and a quote's own words, phone
     and desk, light and dark; the words' box the same height with and
     without it (69px on a phone, 45 on a desk, the mock's); nobody plain;
     the words escaped; plain where the words are one link already
     (Activity's peek, a quote's small card).
  3. THE CARD'S WORDS STILL OPEN THE POST: no link of their own now; a tap on
     them opens the post, a tap on a mention opens the person and never the
     post, a drag that selects them opens nothing; phone and desk.
  4. THE LIST UNDER AN @, in the composer: from the @ on, right under the
     line (8px), placed over what is there (nothing moves), the mock's card
     and rows (52px, the face 36, the name 17px 600, the @handle 15px); the
     people you follow first, then anybody by name; narrowing as you type;
     any word of a followed person's name; nobody a block hides either way,
     nobody taken down, never yourself; four at most; a tap puts "@handle "
     in, the field keeping its focus; the keyboard's arrows, Enter, Tab and
     Esc (the sheet staying); a listbox and its options to a screen reader;
     it fades in, read on every frame, and under Reduce Motion is simply
     there; the field 16px or more.
  5. THE LIST IN A COMMENT'S BOX, AND ON A PHONE'S KEYBOARD: a desk's fold, an
     answer's too; on a phone, over a stand-in keyboard, the composer's and a
     comment's sheet's list above the keyboard, the comment's opening over the
     line where there is no room under it.
  6. WHO MAY ASK: signed out 401; four at most, each {handle, name, face} and
     nothing more, kept by nobody's cache; what is no handle's start, none;
     the limit (600 an hour), the 601st refused.
  7. ACTIVITY: "Rook mentioned you", new, the @ on his face (white on the
     follow badge's purple disc), his words in quotes, the post's small
     picture, to the post (a comment's to the comment, glowing); it lights
     the bell's dot; nobody muted (and no dot), never through a block either
     way, never yourself, never anything taken down or not shown; a comment on
     your post, or a quote of it, that mentions you is one row; gone with the
     post or the comment.
  8. DELETING, IN CODE: a post, a comment (its answers' too), a drawing on the
     site, an account (of it, by it, on what it owned); with SQLite's cascade
     off on a copy; and a drawing's comments moving into a post keep theirs.
  9. THE DATA: the chain on a populated database (the table, its seven
     indexes and its CHECK, the names' index; nothing else touched, no row
     written; back down); once a person a post or a comment; the reads on
     their indexes (SQLite's own plan); a page of Home's cards asks once.
 10. CONTRAST AND TARGETS, read off the paint: the mention on the card and on
     a comment's ground, phone and desk, light and dark (the mock's 8.26 /
     8.39 and 7.75 / 9.89); every word of the list (its highlighted row too)
     and of Activity's mention row at 4.5:1, the badge's @ at 3:1 or more;
     every target 44px or more but the mentions, links inside words (WCAG's
     inline exception), each painted where it is.
 11. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALMENTIONS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Mentions".
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
PART = os.environ.get("SOCIALMENTIONS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALMENTIONS {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence mentions work.")
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
TMP = tempfile.mkdtemp(prefix="socialmentions-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialmentions-" + secrets.token_hex(8),
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
    return f"10.{140 + _addr[0] // 250}.{_addr[0] % 250}.9"


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


def drawing(n=40, seed=0, size=(816, 612), step=30):
    """A small drawing, as the Pad's Add hands one back: `n` points `step` ms apart."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3) * (1 if n <= 60 else 60 / n), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3) * (1 if n <= 60 else 60 / n), 1),
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


# A drawing posted from the Pad on its own page (Make's Draw), as the Pad posts
# it: Skribl's API, as the person signed in, its own token from its own cookie.
PAD = """async ([title, vis, seed]) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const pts = Array.from({ length: 30 }, (_, i) => ({ x: 300 + i * 6, y: 300 + Math.sin((i + seed) / 3) * 60,
    color: '#7c5cff', size: 8, t: i * 30, start: i === 0 }));
  const r = await fetch('/api/skribls', { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) },
    body: JSON.stringify({ title, visibility: vis, version: 2, schemaVersion: 2, playbackMode: 'replay',
      canvasSize: { cssWidth: 816, cssHeight: 612 }, frames: [{ strokes: pts, strokeGroups: [pts.length] }] }) });
  const j = await r.json().catch(() => ({})); return [r.status, j.id || null]; }"""


def make_post(who, words, seed=0, payload=None, extra=None):
    """A post as the composer sends one: (its public id or None, status, answer)."""
    c = who.client()
    c.get("/social/")
    body = {"words": words}
    if payload is not False:
        body["payload"] = payload or drawing(seed=seed)
    body.update(extra or {})
    st, j = c.post_json("/social/posts", body)
    return (j.get("post") if st == 200 and isinstance(j, dict) else None), st, j


def post(who, words, seed=0):
    return make_post(who, words, seed=seed)[0]


def make_drawing(who, title, seed=0, vis="public"):
    """A drawing from the Pad (shown in the gallery when public): its skribl's public id, or None."""
    who.pg.goto(BASE + "/social/")
    st, sid = who.pg.evaluate(PAD, [title, vis, seed])
    return sid if st == 201 else None


def comment(who, on, words, answer_to=None, payload=None):
    """A comment (or an answer) as the box sends one, on a post (("p", id)) or
    a drawing (("s", id)): its public id, or None."""
    c = who.client()
    kind, oid = on
    c.get(f"/social/{kind if kind == 'p' else 'b'}/{oid}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    if payload is not None:
        body["payload"] = payload
    st, j = c.post_json(f"/social/{kind if kind == 'p' else 'b'}/{oid}/comments", body)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


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


def mentions_of(kind, oid):
    """Whom a post's (kind "p") or a comment's ("c") words mention, as kept:
    [(handle now, as typed, by, owner)], in the order written."""
    col, table = ("post_id", "social_posts") if kind == "p" else ("comment_id", "social_comments")
    return [tuple(r) for r in db(f"select p.handle, m.typed, w.handle, o.handle from social_mentions m"
                                 f" join {table} t on t.id = m.{col} join social_people p on p.id = m.person_id"
                                 f" join social_people w on w.id = m.by_id join social_people o on o.id = m.owner_id"
                                 f" where t.public_id = ? order by m.id", (oid,))]


def stamp_seen(who_handle, seconds_ago):
    """When somebody last looked at Activity, set back, in the site's own form."""
    db_write("update social_people set activity_seen_at = strftime('%Y-%m-%d %H:%M:%f000', 'now', ?) where handle_key = ?",
             (f"-{int(seconds_ago)} seconds", who_handle))


def ready(pg):
    """The page and its deferred scripts (they have all run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def card(post_id):
    return f'.post-card[data-post="{post_id}"]'


def press(pg, sel):
    """A finger on a phone (a touch phone taps), a click on a desk."""
    loc = pg.locator(sel).first
    if pg.evaluate("() => matchMedia('(pointer: coarse)').matches"):
        loc.tap(timeout=5000)
    else:
        loc.click(timeout=5000)


def to(pg, sel, top=100):
    """Scroll so that `sel` sits `top` px from the top of the window."""
    pg.evaluate("([s, y]) => { const e = document.querySelector(s); if (e) scrollTo(0, e.getBoundingClientRect().top + scrollY - y); }",
                [sel, top])
    pg.wait_for_timeout(250)


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


# A PHONE'S KEYBOARD, STOOD IN (verify_composer's own, from
# verify_socialcomments): this box has none, so the visual viewport is made to
# say one is there, as a phone's says it.
KEYBOARD = """(() => { const t = new EventTarget(); let h = null, off = 0, scale = 1;
  const vv = { get width() { return innerWidth; }, get height() { return h === null ? innerHeight : h; },
    get offsetTop() { return off; }, get offsetLeft() { return 0; }, get scale() { return scale; },
    addEventListener: (...a) => t.addEventListener(...a), removeEventListener: (...a) => t.removeEventListener(...a) };
  Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => vv });
  window.__keyboard = (px, zoom) => { scale = zoom || 1; h = innerHeight - px; off = 0; t.dispatchEvent(new Event('resize')); };
  window.__keyboardQuiet = (px) => { h = innerHeight - px; }; })();"""


_extra = [0]


def person_row(handle, name):
    """Somebody written straight into the site's table (no passkey, never
    signed in): enough of a person for a list to offer or a mention to name.
    Their id."""
    con = sqlite3.connect(DB, timeout=10)
    try:
        _extra[0] += 1
        cur = con.execute("insert into social_people (public_id, handle, handle_key, display_name, user_handle,"
                          " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, 0, 1,"
                          " strftime('%Y-%m-%d %H:%M:%f000', 'now'), strftime('%Y-%m-%d %H:%M:%f000', 'now'))",
                          (f"site:mn{_extra[0]:05d}{secrets.token_hex(4)}", handle, handle.lower(), name,
                           secrets.token_bytes(32)))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def ensure_row(handle, name):
    got = db("select id from social_people where handle_key = ?", (handle.lower(),))
    return got[0][0] if got else person_row(handle, name)


# ---- the census of words and targets (verify_sociallikes' READ) -----------------
# Every word under `sel` at 4.5:1 on what is painted behind it; every target
# 44px, but a mention: a link inside words (WCAG 2.5.8's inline exception),
# counted apart, with whether it is painted where it is.
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
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99, words: [], inline: [] };
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
    const fg = rgba(getComputedStyle(e).color); fg[3] *= op;
    const g = ground(e), col = over(fg, g), k = ratio(col, g);
    out.read++;
    out.words.push(e.textContent.trim().slice(0, 24));
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 30) + '" ' + k.toFixed(2));
  }));
  document.querySelectorAll('a[href], button, input, textarea, select, [role=button], [role=option]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    if (e.matches('input[type=radio]')) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (e.matches('a.mention')) {
      const rs = [...e.getClientRects()], at = rs.map(q => document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2));
      out.inline.push({ text: e.textContent, painted: at.every(x => !!x && (x === e || e.contains(x))) });
      return;
    }
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

# EVERY MENTION under `sel`, as it is painted: its words, where it goes, its
# ink against the small violet ink's (a probe of the token), its weight, its
# underline, its size against the words', and whether a tap at its middle
# lands on it; and the words' other @handles that are no link.
MENTIONS = r"""(sel) => { const root = document.querySelector(sel); if (!root) return null;
  root.scrollIntoView({ block: 'center' });
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  const words = root.matches('.post-words, .cm-words, .qt-words, .act-peek') ? root
    : root.querySelector('.post-words, .cm-words');
  const links = [...root.querySelectorAll('a.mention')].map(a => { const r = a.getBoundingClientRect(),
      at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2), cs = getComputedStyle(a);
    return { text: a.textContent, href: a.getAttribute('href'), color: cs.color, weight: cs.fontWeight,
             line: cs.textDecorationLine, size: cs.fontSize, lh: cs.lineHeight, hit: !!at && (at === a || a.contains(at)),
             inWords: !!words && words.contains(a) }; });
  const ws = words ? getComputedStyle(words) : null;
  return { links, accent: probe('var(--accent-ink)'), wordsTag: words ? words.tagName : null,
           wordsSize: ws ? ws.fontSize : null, wordsLh: ws ? ws.lineHeight : null,
           text: words ? words.textContent : null, html: words ? words.innerHTML : null }; }"""

# THE WORDS' BOX with the mentions and without them: a copy of the words
# beside them, its links made plain words again, measured in the same place.
HEIGHTS = r"""(sel) => { const w = document.querySelector(sel); if (!w) return null;
  const copy = w.cloneNode(true); copy.querySelectorAll('a.mention').forEach(a => a.replaceWith(document.createTextNode(a.textContent)));
  copy.style.visibility = 'hidden'; w.after(copy);
  const a = w.getBoundingClientRect().height, b = copy.getBoundingClientRect().height; copy.remove();
  return { with: Math.round(a * 100) / 100, without: Math.round(b * 100) / 100, links: w.querySelectorAll('a.mention').length }; }"""

# THE LIST beside the composer's field (or a comment box's): whether it is
# open, its rows (name, handle, height, the face's size, the inks and sizes),
# the card's own look, where it is against the field and the screen, and what
# the field says of it to a screen reader.
LIST = r"""(id) => { const l = document.getElementById(id); if (!l) return null;
  const f = document.querySelector('[aria-controls="' + id + '"]');
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  const cs = getComputedStyle(l), r = l.getBoundingClientRect(), fr = f ? f.getBoundingClientRect() : null;
  const fcs = f ? getComputedStyle(f) : null;
  const rows = [...l.querySelectorAll(':scope > li')].map(li => { const q = li.getBoundingClientRect(),
      n = li.querySelector('.mn-name'), h = li.querySelector('.mn-handle'), face = li.querySelector('.face-ring'),
      at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    return { name: n ? n.textContent : null, handle: h ? h.textContent : null, h: Math.round(q.height * 10) / 10,
             id: li.id, role: li.getAttribute('role'), sel: li.getAttribute('aria-selected'),
             face: face ? Math.round(face.getBoundingClientRect().width) : null,
             nameSize: n ? getComputedStyle(n).fontSize : null, nameWeight: n ? getComputedStyle(n).fontWeight : null,
             nameColor: n ? getComputedStyle(n).color : null, handleSize: h ? getComputedStyle(h).fontSize : null,
             handleColor: h ? getComputedStyle(h).color : null, bg: getComputedStyle(li).backgroundColor,
             hit: !!at && li.contains(at) }; });
  return { open: !l.hidden && l.classList.contains('is-open'), hidden: l.hidden, opacity: +cs.opacity,
           position: cs.position, radius: cs.borderTopLeftRadius, border: cs.borderTopColor, borderW: cs.borderTopWidth,
           bg: cs.backgroundColor, shadow: cs.boxShadow, role: l.getAttribute('role'), label: l.getAttribute('aria-label'),
           card: probe('var(--card)'), line: probe('var(--card-line)'), ink: probe('var(--ink)'), ink2: probe('var(--ink-2)'),
           tint: probe('var(--tint)'),
           box: [Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10, Math.round(r.right * 10) / 10, Math.round(r.bottom * 10) / 10],
           field: fr ? { box: [fr.left, fr.top, fr.right, fr.bottom], padTop: parseFloat(fcs.paddingTop), lh: parseFloat(fcs.lineHeight),
                         size: parseFloat(fcs.fontSize), expanded: f.getAttribute('aria-expanded'),
                         active: f.getAttribute('aria-activedescendant'), controls: f.getAttribute('aria-controls'),
                         auto: f.getAttribute('aria-autocomplete'), focused: document.activeElement === f, value: f.value } : null,
           rows, vh: innerHeight, vv: window.visualViewport ? visualViewport.height : innerHeight }; }"""

# The list's opacity on every frame from now for `ms`, into window.__mnFrames:
# [time, laid out (not hidden), opacity].
LIST_WATCH = r"""([id, ms]) => { const l = document.getElementById(id), t0 = performance.now(); window.__mnFrames = [];
  (function f() { window.__mnFrames.push([Math.round(performance.now() - t0), !l.hidden && l.getClientRects().length > 0,
                                          +getComputedStyle(l).opacity]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); })(); }"""


def wait_list(pg, list_id, open_=True, timeout=6000):
    """Until the list is open (or shut), and a moment for its fade."""
    try:
        pg.wait_for_function("([id, o]) => { const l = document.getElementById(id); if (!l) return false;"
                             " const on = !l.hidden && l.classList.contains('is-open') && l.children.length > 0;"
                             " return o ? on : !on; }", arg=[list_id, open_], timeout=timeout)
    except Exception:  # noqa: BLE001 -- not opening (or not shutting) is the row's own red
        pass
    pg.wait_for_timeout(260)


def open_composer(pg):
    """Make, the bar's on a phone and the rail's on a desk: the composer up,
    its words' field in focus."""
    press(pg, "nav.nav .tab-make")
    pg.wait_for_function("() => { const w = document.getElementById('composeSheet'); return !!w && w.classList.contains('is-open')"
                         " && document.activeElement === document.getElementById('composeWords'); }", timeout=8000)
    pg.wait_for_timeout(450)


def handles(rows):
    return [(r or {}).get("handle") for r in rows or []]


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the words: who a post's or a comment's words mention; boundaries, case, nobody, ten at most;"
               " every way words are written; a handle that changes keeps the link"):
        try:
            mira = someone(b, "mira", "Mira Lopez")
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            pip = someone(b, "pip", "Pip")
            # BOUNDARIES: an @ in an email or right after a letter, an @ after an
            # @, a handle running on into _ or a letter, a handle that is nobody,
            # one too short to be anybody's: none of them; any case; once each.
            w1 = ("Hi @Juno! mail@rook.com, x@rook, @@rook, @rook_ and @rookie, @nobodyhere, @ro, (@pip) and"
                  " @JUNO again.")
            p1, st1, _ = make_post(mira, w1, seed=11)
            got1 = mentions_of("p", p1)
            check("an @handle that is somebody, with nothing of a word or an email right before or after it, in any"
                  " case, each once in the order first typed, as typed (\"Juno\"), by whom and whose: an email"
                  " (mail@rook.com), x@rook, @@rook, @rook_ and @rookie, a handle that is nobody and one too short"
                  " are words",
                  st1 == 200 and got1 == [("juno", "Juno", "mira", "mira"), ("pip", "pip", "mira", "mira")],
                  json.dumps([st1, got1]))
            # TEN AT MOST: twelve distinct people named, one twice, and one nobody
            # among them: the first ten people, in order.
            twelve = [f"mn1x{i:02d}" for i in range(12)]
            for h in twelve:
                ensure_row(h, f"Twelve {h[-2:]}")
            w2 = " ".join(["@" + twelve[0], "@nobody_at_all"] + ["@" + h for h in twelve[1:]] + ["@" + twelve[3]])
            p2, st2, _ = make_post(mira, w2, seed=12)
            got2 = [g[0] for g in mentions_of("p", p2)]
            check("ten people at most in one post, the first ten distinct in order (a handle that is nobody not"
                  " among them, one named twice counted once); the eleventh and twelfth are words",
                  st2 == 200 and got2 == twelve[:10], json.dumps([st2, got2]))
            # EVERY WAY WORDS ARE WRITTEN: a quote of words alone, an older
            # drawing posted through Yours, a comment, an answer; each at its own
            # time; a post refused writes none.
            q1, stq, _ = make_post(juno, "Quoting this for @Rook", payload=False, extra={"quote": p1})
            sid = make_drawing(rook, "Section 1, Rook's drawing", seed=13)
            o1, sto, _ = make_post(rook, "An old one, posted now, for @pip", payload=False, extra={"skribl": sid})
            c1 = comment(juno, ("p", p1), "@rook have you seen this?")
            a1 = comment(rook, ("p", p1), "Yes! @pip and @mira too", answer_to=c1)
            long_ = "@juno " + "a" * 500
            bad, stb, _ = make_post(mira, long_, seed=14)
            before_bad = db("select count(*) from social_mentions")[0][0]
            got = {"quote": mentions_of("p", q1), "older": mentions_of("p", o1), "comment": mentions_of("c", c1),
                   "answer": mentions_of("c", a1)}
            times = db("select count(*) from social_mentions m join social_posts t on t.id = m.post_id"
                       " where t.public_id in (?, ?, ?, ?) and m.created_at = t.created_at", (p1, q1, o1, p2))[0][0]
            ctimes = db("select count(*) from social_mentions m join social_comments t on t.id = m.comment_id"
                        " where t.public_id in (?, ?) and m.created_at = t.created_at", (c1, a1))[0][0]
            check("every way words are written writes their mentions beside them, at their own time: a quote of words"
                  " alone (\"@Rook\"), an older drawing posted through Yours, a comment and an answer (whose they"
                  " are: the post's maker's); a post refused (too long) writes none",
                  stq == 200 and sto == 200 and stb == 400 and bad is None
                  and got == {"quote": [("rook", "Rook", "juno", "juno")], "older": [("pip", "pip", "rook", "rook")],
                              "comment": [("rook", "rook", "juno", "mira")],
                              "answer": [("pip", "pip", "rook", "mira"), ("mira", "mira", "rook", "mira")]}
                  and times == 2 + 1 + 1 + 10 and ctimes == 3
                  and db("select count(*) from social_mentions where typed = 'juno' and post_id is null and comment_id"
                         " is null")[0][0] == 0,
                  json.dumps([stq, sto, stb, got, times, ctimes, before_bad]))
            # A HANDLE THAT CHANGES: the old words keep their spelling, and the
            # link goes to the person as they are now.
            jid = db("select id from social_people where handle_key = 'juno'")[0][0]
            db_write("update social_people set handle = 'junebug', handle_key = 'junebug' where id = ?", (jid,))
            c = mira.client()
            st_p, page = c.get(f"/social/p/{p1}")
            db_write("update social_people set handle = 'juno', handle_key = 'juno' where id = ?", (jid,))
            found = re.findall(r'<a class="mention" href="([^"]+)">([^<]+)</a>', page)
            check("a handle that changes keeps the link: the old words still say \"@Juno\" as typed, and it opens"
                  " the person's page as it is now (/social/@junebug)",
                  st_p == 200 and found[:1] == [("/social/@junebug", "@Juno")] and ("/social/@pip", "@pip") in found,
                  json.dumps([st_p, found]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "how a mention looks: violet, 600, no underline, a link to their page; nothing moves; nobody plain;"
               " the words escaped; plain where the words are one link"):
        try:
            mira = someone(b, "mira", "Mira Lopez")
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            # The mock's own words, on Rook's post; a comment and an answer; a
            # quote's own words; and words that look like markup.
            w = "Skull study, outline first. @juno, your hat was the idea!"
            p2 = post(rook, w, seed=21)
            c2 = comment(rook, ("p", p2), "@juno look at the timing on this!")
            a2 = comment(juno, ("p", p2), "Ha, @rook, I will", answer_to=c2)
            q2, _, _ = make_post(juno, "Love this @rook", payload=False, extra={"quote": p2})
            m2 = post(mira, "<b>bold</b> & <i>not</i> @juno, and @nobodyhere", seed=22)
            seen, heights, bad = {}, {}, []
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    ctx, pg = browser_as(b, mira, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=500)
                    to(pg, card(p2), 160)
                    seen[(tag, "card")] = pg.evaluate(MENTIONS, card(p2))
                    heights[(tag, "card")] = pg.evaluate(HEIGHTS, card(p2) + " .post-words")
                    to(pg, card(q2), 160)
                    seen[(tag, "quote")] = pg.evaluate(MENTIONS, card(q2))
                    seen[(tag, "quote small")] = pg.evaluate("(s) => { const q = document.querySelector(s + ' .qt-card');"
                                                             " return q ? { links: q.querySelectorAll('a.mention').length,"
                                                             " words: (q.querySelector('.qt-words') || {}).textContent || '' } : null; }",
                                                             card(q2))
                    to(pg, card(m2), 160)
                    seen[(tag, "markup")] = pg.evaluate(MENTIONS, card(m2))
                    go(pg, f"/social/p/{p2}", wait=500)
                    seen[(tag, "page")] = pg.evaluate(MENTIONS, ".post-page > .post-words")
                    heights[(tag, "page")] = pg.evaluate(HEIGHTS, ".post-page > .post-words")
                    seen[(tag, "comment")] = pg.evaluate(MENTIONS, f"#c-{c2} > .cm-main")
                    seen[(tag, "answer")] = pg.evaluate(MENTIONS, f"#c-{a2} > .cm-main")
                    heights[(tag, "comment")] = pg.evaluate(HEIGHTS, f"#c-{c2} > .cm-main .cm-words")
                    close_ctx(ctx, pg)
            want = {"card": [("@juno", "/social/@juno")], "page": [("@juno", "/social/@juno")],
                    "comment": [("@juno", "/social/@juno")], "answer": [("@rook", "/social/@rook")],
                    "quote": [("@rook", "/social/@rook")], "markup": [("@juno", "/social/@juno")]}
            for (tag, where), s in seen.items():
                if where == "quote small":
                    continue
                links = (s or {}).get("links") or []
                if [(x["text"], x["href"]) for x in links] != want[where]:
                    bad.append(f"{tag} {where}: {[(x['text'], x['href']) for x in links]}")
                    continue
                for x in links:
                    if not (x["color"] == s["accent"] and x["weight"] == "600" and x["line"] == "none"
                            and x["size"] == s["wordsSize"] and x["lh"] == s["wordsLh"] and x["hit"] and x["inWords"]):
                        bad.append(f"{tag} {where}: {x} accent {s['accent']} words {s['wordsSize']}/{s['wordsLh']}")
            check("an @handle that is somebody is a link to their page in the small violet ink (--accent-ink), 600,"
                  " never underlined, the words' own size and line, painted where it is: on Home's card, a post's"
                  " page, a comment, an answer and a quote's own words; phone and desk, light and dark",
                  len(seen) == 4 * 7 and not bad, f"{bad[:4]}; read {len(seen)}")
            moved = {"/".join(k): v for k, v in heights.items() if not v or v["links"] != 1 or abs(v["with"] - v["without"]) > 0.01}
            check("nothing else in the words moves: the words' box is the same height with the link and without it"
                  " (the card's, the page's and a comment's; the mock's 69px on a phone, 45 on a desk for the card)",
                  len(heights) == 12 and not moved,
                  json.dumps({"moved": moved, "card": {k[0]: v and v["with"] for k, v in heights.items() if k[1] == "card"}}))
            mk = [s for (t, k), s in seen.items() if k == "markup"]
            small = [s for (t, k), s in seen.items() if k == "quote small"]
            check("a handle that is nobody stays words, and the words are escaped as words (<b>bold</b> shows as"
                  " typed, nothing of it markup); a quote's small card (one link to the original) keeps its words"
                  " plain",
                  len(mk) == 4 and all(s["text"] == "<b>bold</b> & <i>not</i> @juno, and @nobodyhere"
                                       and "<b>" not in s["html"] and "&lt;b&gt;" in s["html"] for s in mk)
                  and len(small) == 4 and all(s and s["links"] == 0 and "@juno" in s["words"] for s in small),
                  json.dumps([mk[:1], small[:1]])[:600])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "a card's words still open the post; a mention opens the person, never the post; a selection nothing"):
        try:
            mira = someone(b, "mira", "Mira Lopez")
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            p3 = post(rook, "Tap these words, or tap @juno to meet her", seed=31)
            SPOT = r"""([key, what]) => { const c = document.querySelector('.post-card[data-post="' + key + '"]'); if (!c) return null;
              c.scrollIntoView({ block: 'center' }); const w = c.querySelector('.post-words');
              const text = (root, needle) => { const t = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                for (let n = t.nextNode(); n; n = t.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
                  const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g.getBoundingClientRect(); } }
                return null; };
              const r = what === 'mention' ? w.querySelector('a.mention').getBoundingClientRect() : text(w, 'these words');
              const x = r.left + r.width / 2, y = r.top + r.height / 2, e = document.elementFromPoint(x, y);
              return { xy: [x, y], tag: w.tagName, on: e ? (e.closest('a') ? e.closest('a').getAttribute('href') : 'words') : null }; }"""
            res = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, mira, screen=screen)
                r = res[screen] = {}
                try:
                    for what in ("words", "mention"):
                        go(pg, "/social/", wait=400)
                        got = pg.evaluate(SPOT, [p3, what])
                        (pg.touchscreen.tap if screen == "phone" else pg.mouse.click)(*got["xy"])
                        try:
                            pg.wait_for_function("() => location.pathname !== '/social/'", timeout=3000)
                        except Exception:  # noqa: BLE001 -- staying is an answer
                            pass
                        pg.wait_for_timeout(250)
                        r[what] = (got["tag"], got["on"], pg.evaluate("() => location.pathname"))
                    if screen == "desk":
                        go(pg, "/social/", wait=400)
                        ends = pg.evaluate("""(key) => { const c = document.querySelector('.post-card[data-post="' + key + '"]');
                          c.scrollIntoView({ block: 'center' }); const w = c.querySelector('.post-words'), n = w.firstChild;
                          const g = document.createRange(); g.setStart(n, 0); g.setEnd(n, 1); const a = g.getBoundingClientRect();
                          const m = w.querySelector('a.mention').getBoundingClientRect();
                          return [a.left + 1, a.top + a.height / 2, m.left + m.width / 2, m.top + m.height / 2]; }""", p3)
                        pg.mouse.move(ends[0], ends[1])
                        pg.mouse.down()
                        pg.mouse.move(ends[2], ends[3], steps=12)
                        pg.mouse.up()
                        pg.wait_for_timeout(600)
                        r["select"] = (pg.evaluate("() => String(getSelection())"), pg.evaluate("() => location.pathname"))
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is its rows' red
                    r["stopped"] = str(exc).splitlines()[0][:160]
                close_ctx(ctx, pg)
            page = f"/social/p/{p3}"
            check("a card's words are no link of their own now (a paragraph), and a tap on them opens the post, as the"
                  " card's ground does: a touch on a phone, a click on a desk",
                  all(r.get("words") == ("P", "words", page) for r in res.values()), json.dumps(res))
            check("a tap on a mention in them opens that person's page, never the post: phone and desk",
                  all(r.get("mention") == ("P", "/social/@juno", "/social/@juno") for r in res.values()), json.dumps(res))
            sel = res.get("desk", {}).get("select") or ("", None)
            check("pressing on the words and pulling to the mention selects them and opens nothing, the post or the"
                  " person (desk)",
                  sel[0].startswith("Tap these words") and sel[1] == "/social/", json.dumps(sel))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    def list_people():
        """The people the list is read against (section 4 on; section 5's too):
        Mira follows Theo Park and Pip; strangers whose names or handles start
        with v (five, so four show), one a block hides each way and one taken
        down; Paz Ruiz, whose name sorts before Theo Park's; Bo Lund, whose
        handle (rainbo) starts with what his name does not."""
        mira = someone(b, "mira", "Mira Lopez")
        for h, n in (("theo", "Theo Park"), ("pip", "Pip"), ("valerie", "Val"), ("veev", "Vee"), ("vera", "Vera Quill"),
                     ("vexx", "Vex"), ("victran", "Vic Tran"), ("vikstone", "Vik Stone"), ("violane", "Vio Lane"),
                     ("vinmoss", "Vin Moss"), ("pazr", "Paz Ruiz"), ("rainbo", "Bo Lund")):
            ensure_row(h, n)
        follow(mira, "theo")
        follow(mira, "pip")
        block(mira, "vikstone")
        if not db("select 1 from social_blocks b join social_people x on x.id = b.blocker_id join social_people y"
                  " on y.id = b.blocked_id where x.handle_key = 'violane' and y.handle_key = 'mira'"):
            db_write("insert into social_blocks (blocker_id, blocked_id, created_at) select x.id, y.id,"
                     " strftime('%Y-%m-%d %H:%M:%f000', 'now') from social_people x, social_people y"
                     " where x.handle_key = 'violane' and y.handle_key = 'mira'")
        db_write("update social_people set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where handle_key = 'vinmoss'")
        return mira

    def typed(pg, words, list_id="composeMentions", field="#composeWords", open_=True):
        """`words` typed into an empty field, key by key; then the list (open or shut)."""
        pg.fill(field, "")
        pg.focus(field)
        pg.keyboard.type(words, delay=25)
        wait_list(pg, list_id, open_)
        return pg.evaluate(LIST, list_id)

    if part(4, "the list under an @, in the composer: under the line, nothing moves; followed first, then by name;"
               " narrowing; nobody hidden; four at most; a tap, the keys; a listbox; it fades in"):
        try:
            mira = list_people()
            # The "@" alone: the two Mira follows by name, then the first two
            # others by name, read from the site's own table as the owner said
            # it (nobody a block hides either way, nobody taken down, never her).
            others = db("select handle, display_name from social_people p where taken_down_at is null and handle_key"
                        " <> 'mira' and handle_key not in ('theo', 'pip') and id not in (select blocked_id from"
                        " social_blocks b join social_people m on m.id = b.blocker_id where m.handle_key = 'mira') and"
                        " id not in (select blocker_id from social_blocks b join social_people m on m.id = b.blocked_id"
                        " where m.handle_key = 'mira')")
            others = sorted(others, key=lambda r: (r[1].lower(), r[0].lower()))
            want_at = ["@pip", "@theo"] + ["@" + h for h, _ in others[:2]]
            ctx, pg = browser_as(b, mira, screen="phone", scheme="light")
            go(pg, "/social/", wait=400)
            open_composer(pg)
            before = pg.evaluate("() => { const t = document.querySelector('#composeSheet .cmp-tools').getBoundingClientRect(),"
                                 " s = document.querySelector('#composeSheet .cmp-scroll'); return [t.top, t.bottom, s.scrollHeight]; }")
            pg.evaluate(LIST_WATCH, ["composeMentions", 1600])
            at_ = typed(pg, "@")
            frames = pg.evaluate("() => window.__mnFrames")
            after = pg.evaluate("() => { const t = document.querySelector('#composeSheet .cmp-tools').getBoundingClientRect(),"
                                " s = document.querySelector('#composeSheet .cmp-scroll'); return [t.top, t.bottom, s.scrollHeight]; }")
            f = (at_ or {}).get("field") or {}
            line_bottom = f.get("box", [0, 0])[1] + f.get("padTop", 0) + f.get("lh", 0)
            two = typed(pg, "first line\n@")
            f2 = (two or {}).get("field") or {}
            line2 = f2.get("box", [0, 0])[1] + f2.get("padTop", 0) + 2 * f2.get("lh", 0)
            rows = (at_ or {}).get("rows") or []
            check("from the @ on, the list opens right under the line being typed (8px under it, on the first line"
                  " and on the second), placed over what is there: the sheet's tools and its words' room do not move",
                  bool(at_) and at_["open"] and at_["position"] == "absolute" and abs(at_["box"][1] - (line_bottom + 8)) <= 1.5
                  and bool(two) and two["open"] and abs(two["box"][1] - (line2 + 8)) <= 1.5 and before == after,
                  json.dumps({"top": at_ and at_["box"][1], "line": line_bottom, "second": two and two["box"][1],
                              "line2": line2, "before": before, "after": after}))
            check("the people Mira follows first (Pip, Theo Park), then anybody by name (the two first by name of"
                  " everybody else, read from the site's table), four rows at most",
                  handles(rows) == want_at, json.dumps({"got": handles(rows), "want": want_at}))
            look = at_ or {}
            row_ok = rows and all(r["h"] == 52 and r["face"] == 36 and r["nameSize"] == "17px" and r["nameWeight"] == "600"
                                  and r["nameColor"] == look["ink"] and r["handleSize"] == "15px"
                                  and r["handleColor"] == look["ink2"] and r["hit"] and r["role"] == "option" for r in rows)
            check("the mock's card and rows: --card, its edge --card-line (1px), 16px round, a drop; each row 52px, the"
                  " face 36px, the name 17px 600 in the first ink, the @handle 15px in the second, painted where it is",
                  bool(row_ok) and look["bg"] == look["card"] and look["border"] == look["line"] and look["borderW"] == "1px"
                  and look["radius"] == "16px" and look["shadow"] not in ("none", ""),
                  json.dumps({k: look.get(k) for k in ("bg", "card", "border", "line", "borderW", "radius", "shadow")})
                  + " " + json.dumps(rows[:1]))
            check("to a screen reader: a listbox of options, named; the field says it is open (aria-expanded), which it"
                  " controls and which row is highlighted (aria-activedescendant, the first); the field 16px or more",
                  look.get("role") == "listbox" and look.get("label") == "People to mention" and f.get("expanded") == "true"
                  and f.get("controls") == "composeMentions" and f.get("auto") == "list" and bool(rows)
                  and f.get("active") == rows[0]["id"] and rows[0]["sel"] == "true"
                  and all(r["sel"] == "false" for r in rows[1:]) and f.get("size", 0) >= 16 and f.get("focused"),
                  json.dumps(f))
            # NARROWING, AND WHO IS NEVER IN IT.
            seen = {}
            for words in ("@pa", "@v", "@ve", "@ver", "@vi", "@rai", "@mi"):
                got = typed(pg, words, open_=words != "@mi")
                seen[words] = handles((got or {}).get("rows")) if got and got["open"] else []
            check("as you type it narrows: \"@pa\" Theo Park first (any word of a name you follow), then Paz Ruiz;"
                  " \"@v\" four of five; \"@ve\" three; \"@ver\" one; a handle's start (\"@rai\", Bo Lund)",
                  seen["@pa"] == ["@theo", "@pazr"] and seen["@v"] == ["@valerie", "@veev", "@vera", "@vexx"]
                  and seen["@ve"] == ["@veev", "@vera", "@vexx"] and seen["@ver"] == ["@vera"] and seen["@rai"] == ["@rainbo"],
                  json.dumps(seen))
            check("nobody a block hides, either way (Vik Stone, whom Mira blocked; Vio Lane, who blocked her),"
                  " nobody taken down (Vin Moss), never herself (\"@mi\": nobody, the list shut)",
                  seen["@vi"] == ["@victran"] and seen["@mi"] == [], json.dumps({k: seen[k] for k in ("@vi", "@mi")}))
            # A TAP: "@vera " in, the field keeping its focus (and a phone its keyboard).
            got = typed(pg, "Hi @ver")
            pg.locator("#composeMentions .mn-row").first.tap(timeout=5000)
            pg.wait_for_timeout(400)
            tapped = pg.evaluate(LIST, "composeMentions")
            tf = (tapped or {}).get("field") or {}
            caret = pg.evaluate("() => { const f = document.getElementById('composeWords'); return [f.selectionStart, f.selectionEnd]; }")
            check("a tap on a row puts \"@vera \" in where \"@ver\" was typed, the caret after it, the field keeping its"
                  " focus; the list shuts and the field says so",
                  tf.get("value") == "Hi @vera " and caret == [9, 9] and tf.get("focused") and not tapped["open"]
                  and tf.get("expanded") == "false" and not tf.get("active"),
                  json.dumps([tf.get("value"), caret, tf.get("focused"), tapped and tapped["open"], tf.get("expanded")]))
            ups = [fr for fr in frames if fr[1]]
            close_ctx(ctx, pg)
            check("it fades in (read on every frame from the @): laid out first nearly clear, then rising over several"
                  " frames to whole, never a jump",
                  len(ups) >= 3 and ups[0][2] < 0.6 and ups[-1][2] == 1
                  and sum(1 for fr in ups if 0 < fr[2] < 1) >= 2
                  and all(b_[2] >= a_[2] - 1e-6 for a_, b_ in zip(ups, ups[1:])),
                  json.dumps(ups[:8]))
            # THE KEYS, on a desk: the arrows move the highlight, Enter and Tab
            # put it in, Esc shuts the list and leaves the sheet; the list stays
            # shut for that @, and a new @ opens it again.
            ctx, pg = browser_as(b, mira, screen="desk", scheme="dark")
            go(pg, "/social/", wait=400)
            open_composer(pg)
            k1 = typed(pg, "Hello @v")
            pg.keyboard.press("ArrowDown")
            pg.wait_for_timeout(120)
            k2 = pg.evaluate(LIST, "composeMentions")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(350)
            k3 = pg.evaluate(LIST, "composeMentions")
            typed(pg, "@ver")
            pg.keyboard.press("Tab")
            pg.wait_for_timeout(350)
            k4 = pg.evaluate(LIST, "composeMentions")
            typed(pg, "@v")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(350)
            k5 = pg.evaluate(LIST, "composeMentions")
            sheet_up = pg.evaluate("() => document.getElementById('composeSheet').classList.contains('is-open')")
            pg.keyboard.type("e", delay=25)
            pg.wait_for_timeout(700)
            k6 = pg.evaluate(LIST, "composeMentions")
            pg.keyboard.type(" @v", delay=25)
            wait_list(pg, "composeMentions", True)
            k7 = pg.evaluate(LIST, "composeMentions")
            close_ctx(ctx, pg)
            r2 = (k2 or {}).get("rows") or []
            check("the keys, on a desk: Down highlights the next row (aria-selected, aria-activedescendant), Enter puts it"
                  " in (\"Hello @veev \"), and Tab the highlighted one (\"@vera \"), the field keeping its focus",
                  bool(k1) and k1["open"] and len(r2) >= 2 and r2[1]["sel"] == "true" and k2["field"]["active"] == r2[1]["id"]
                  and k3["field"]["value"] == "Hello @veev " and not k3["open"] and k3["field"]["focused"]
                  and k4["field"]["value"] == "@vera " and k4["field"]["focused"],
                  json.dumps([k3 and k3["field"]["value"], k4 and k4["field"]["value"], r2[1:2]]))
            check("Esc shuts the list and nothing else (the sheet stays, the field keeps its focus); it stays shut for"
                  " that @ as more is typed, and a new @ opens it again",
                  bool(k5) and not k5["open"] and sheet_up and k5["field"]["focused"] and k5["field"]["expanded"] == "false"
                  and bool(k6) and not k6["open"] and bool(k7) and k7["open"],
                  json.dumps([k5 and k5["open"], sheet_up, k6 and k6["open"], k7 and k7["open"]]))
            # UNDER REDUCE MOTION it is simply there: whole from its first frame.
            ctx, pg = browser_as(b, mira, screen="phone", scheme="light", reduced=True)
            go(pg, "/social/", wait=400)
            open_composer(pg)
            pg.evaluate(LIST_WATCH, ["composeMentions", 1200])
            still = typed(pg, "@v")
            frames = pg.evaluate("() => window.__mnFrames")
            close_ctx(ctx, pg)
            ups = [fr for fr in frames if fr[1]]
            check("under Reduce Motion no fade: from its first frame the list is whole",
                  bool(still) and still["open"] and len(ups) >= 1 and all(fr[2] == 1 for fr in ups), json.dumps(ups[:4]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "the list in a comment's box (a desk's fold, an answer's) and above a phone's keyboard (the composer's,"
               " a comment's sheet's)"):
        try:
            mira = list_people()
            rook = someone(b, "rook", "Rook")
            p5 = post(rook, "Section 5, Rook's", seed=51)
            c5 = comment(rook, ("p", p5), "Section 5, Rook says something first")
            # A DESK'S FOLD, and an answer's.
            ctx, pg = browser_as(b, mira, screen="desk", scheme="light")
            go(pg, f"/social/p/{p5}", wait=500)
            pg.click(".comments-head .cm-say")
            pg.wait_for_function("() => document.activeElement === document.getElementById('cmWords')", timeout=6000)
            pg.wait_for_timeout(500)
            d1 = typed(pg, "@ve", list_id="cmMentions", field="#cmWords")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(350)
            d2 = pg.evaluate(LIST, "cmMentions")
            fold_open = pg.evaluate("() => document.querySelector('[data-cm-fold]').classList.contains('is-open')")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(600)
            pg.click(f"#c-{c5} [data-cm-answer]")
            pg.wait_for_function("() => document.activeElement === document.getElementById('cmWords')", timeout=6000)
            pg.wait_for_timeout(500)
            d3 = typed(pg, "@vic", list_id="cmMentions", field="#cmWords")
            pg.click("#cmMentions .mn-row")
            pg.wait_for_timeout(350)
            d4 = pg.evaluate(LIST, "cmMentions")
            in_answer = pg.evaluate("(id) => !!document.querySelector('#c-' + id + ' #cmWords')", c5)
            close_ctx(ctx, pg)
            f1 = (d1 or {}).get("field") or {}
            check("in a comment's box on a desk (the fold under the heading): the list under the line, Enter puts"
                  " \"@veev \" in, the box staying open",
                  bool(d1) and d1["open"] and handles(d1["rows"]) == ["@veev", "@vera", "@vexx"]
                  and abs(d1["box"][1] - (f1["box"][1] + f1["padTop"] + f1["lh"] + 8)) <= 1.5
                  and d2["field"]["value"] == "@veev " and fold_open and d2["field"]["focused"],
                  json.dumps([d1 and d1["box"], f1.get("box"), d2 and d2["field"]["value"], fold_open]))
            check("answering (the fold under the conversation): the list again, a click on its row puts \"@victran \" in,"
                  " the field keeping its focus",
                  bool(d3) and d3["open"] and handles(d3["rows"]) == ["@victran"] and in_answer
                  and d4["field"]["value"] == "@victran " and d4["field"]["focused"] and not d4["open"],
                  json.dumps([d3 and handles(d3["rows"]), in_answer, d4 and d4["field"]["value"]]))
            # ON A PHONE'S KEYBOARD, STOOD IN: the composer's list above it; a
            # comment's sheet sits on the keyboard, so its list opens over the
            # line, above the keyboard too.
            ctx, pg = browser_as(b, mira, screen="phone", scheme="dark", init=KEYBOARD)
            go(pg, "/social/", wait=400)
            open_composer(pg)
            pg.evaluate("() => window.__keyboard(336)")
            pg.wait_for_timeout(900)
            k1 = typed(pg, "@v")
            go(pg, f"/social/p/{p5}", wait=500)
            press(pg, ".comments-head .cm-say")
            pg.wait_for_function("() => document.activeElement === document.getElementById('cmWords')", timeout=6000)
            pg.evaluate("() => window.__keyboard(336)")
            pg.wait_for_timeout(900)
            k2 = typed(pg, "@v", list_id="cmMentions", field="#cmWords")
            sheet = pg.evaluate("() => { const r = document.querySelector('#commentBoxSheet .make-sheet').getBoundingClientRect();"
                                " return [r.top, r.bottom]; }")
            close_ctx(ctx, pg)
            fk = (k2 or {}).get("field") or {}
            check("on a phone over its keyboard (stood in, 336px): the composer's list ends above the keyboard",
                  bool(k1) and k1["open"] and k1["box"][3] <= k1["vh"] - 336 + 0.5 and k1["box"][1] >= 0,
                  json.dumps(k1 and {"box": k1["box"], "vh": k1["vh"]}))
            check("...and a comment's sheet, riding on the keyboard, has no room under its line: its list opens over"
                  " the line (8px above it), above the keyboard and on the screen",
                  bool(k2) and k2["open"] and k2["box"][3] <= k2["vh"] - 336 + 0.5 and k2["box"][1] >= 0
                  and abs(k2["box"][3] - (fk["box"][1] + fk["padTop"] - 8)) <= 1.5 and sheet[1] <= k2["vh"] - 336 + 1,
                  json.dumps(k2 and {"box": k2["box"], "vh": k2["vh"], "field": fk.get("box"), "sheet": sheet}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "who may ask: signed in; four at most, handle, name and face alone; nobody's cache; the limit"):
        try:
            mira = list_people()
            lim = someone(b, "lim", "Lim Park")
            st_out, j_out, _ = Client().get_json("/social/people/suggest?q=v")
            c = mira.client()
            st_in, j_in, h_in = c.get_json("/social/people/suggest?q=v")
            st_at, j_at, _ = c.get_json("/social/people/suggest?q=%40ve")
            st_no, j_no, _ = c.get_json("/social/people/suggest?q=9x")
            st_lg, j_lg, _ = c.get_json("/social/people/suggest?q=" + "v" * 21)
            people = (j_in or {}).get("people") if isinstance(j_in, dict) else None
            check("signed out, nobody is offered (401); signed in, four at most, each its handle, its name and its face"
                  " (the site's own face markup) and nothing more, kept by no shared cache",
                  st_out == 401 and st_in == 200 and isinstance(people, list) and 1 <= len(people) <= 4
                  and all(set(x) == {"handle", "name", "face"} and "face-ring" in x["face"] for x in people)
                  and set(j_in) == {"people"} and "no-store" in (h_in.get("Cache-Control") or ""),
                  json.dumps([st_out, st_in, people[:1] if people else people, h_in.get("Cache-Control")])[:500])
            check("what follows the @ may be written with it (\"@ve\"); what is no handle's start (\"9x\", 21 letters)"
                  " is nobody",
                  st_at == 200 and [x["handle"] for x in j_at["people"]] == ["veev", "vera", "vexx"]
                  and st_no == 200 and j_no["people"] == [] and st_lg == 200 and j_lg["people"] == [],
                  json.dumps([st_at, j_at if not isinstance(j_at, dict) else [x["handle"] for x in j_at.get("people", [])],
                              st_no, j_no, st_lg]))
            lc = lim.client()
            codes = [lc.get_json("/social/people/suggest?q=" + ("ab"[i % 2]))[0] for i in range(601)]
            check("the site's limit, 600 an hour a person: the 601st is refused (429), and nothing before it",
                  codes[:600] == [200] * 600 and codes[600] == 429, f"{codes.count(200)} answered, last {codes[-3:]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    # Activity's rows as they show, the bell's word, and a comment landed on.
    ROWS = r"""() => [...document.querySelectorAll('.act-list')].map(ul => {
      const h = document.getElementById(ul.getAttribute('aria-labelledby'));
      return { sec: h ? h.textContent.trim() : null, rows: [...ul.querySelectorAll(':scope > li > a.act-row')].map(a => {
        const peek = a.querySelector('.act-peek'), pic = a.querySelector('.act-pic'), at = a.querySelector('.mn-at'),
              disc = a.querySelector('.mn-badge > .fo-disc');
        return { say: a.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim(), href: a.getAttribute('href'),
                 peek: peek ? peek.textContent : null, peekLinks: peek ? peek.querySelectorAll('a').length : 0,
                 isNew: a.classList.contains('is-new'), pic: pic ? pic.getAttribute('style') || '' : '',
                 badge: at ? { text: at.textContent, color: getComputedStyle(at).color, weight: getComputedStyle(at).fontWeight,
                               disc: getComputedStyle(disc).backgroundColor } : null }; }) }; })"""
    BELL = "() => { const b = document.querySelector('.top-bell'); return b ? b.getAttribute('aria-label') : null; }"
    FILL = """() => { const e = document.createElement('i'); e.style.color = 'var(--fill)'; document.body.append(e);
      const v = getComputedStyle(e).color; e.remove(); return v; }"""

    def activity(who, screen="phone"):
        """(Home's bell before, Activity's rows) for `who`; opening it marks it seen."""
        ctx, pg = browser_as(b, who, screen=screen)
        go(pg, "/social/", wait=300)
        bell = pg.evaluate(BELL)
        go(pg, "/social/activity", wait=300)
        rows = [r for s in pg.evaluate(ROWS) for r in s["rows"]]
        fill = pg.evaluate(FILL)
        close_ctx(ctx, pg)
        return bell, rows, fill

    if part(7, "Activity: \"Rook mentioned you\" (the @ on his face, his words, to the post or the comment); it lights"
               " the dot; nobody muted, no block, never yourself, nothing taken down; one row, not two; gone with it"):
        try:
            ada = someone(b, "ada", "Ada Kim")
            rook = someone(b, "rook", "Rook")
            bea = someone(b, "bea", "Bea Lund")
            activity(ada)                                   # seen: everything before is old now
            r7 = post(rook, "Look what @ada drew yesterday", seed=71)
            b7 = post(bea, "Section 7, Bea's", seed=72)
            c7 = comment(rook, ("p", b7), "@ada you have to see this")
            bell, rows, fill = activity(ada)
            m = [r for r in rows if r["say"] == "Rook mentioned you"]
            want = {f"/social/p/{r7}": "“Look what @ada drew yesterday”", f"/social/p/{b7}#c-{c7}": "“@ada you have to see this”"}
            sk7 = db("select skribl_id from social_posts where public_id = ?", (r7,))[0][0]
            check("Ada's Activity: \"Rook mentioned you\", a row each, new, his words under it in quotes (plain: the row"
                  " is one link), to the post or to the comment on its page; the post's small picture",
                  len(m) == 2 and {r["href"]: r["peek"] for r in m} == want and all(r["isNew"] and r["peekLinks"] == 0 for r in m)
                  and any(sk7 in r["pic"] for r in m if r["href"] == f"/social/p/{r7}"), json.dumps(rows)[:800])
            check("his face wears an @: white, 700, on the follow badge's purple disc (--fill)",
                  len(m) == 2 and all(r["badge"] and r["badge"]["text"] == "@" and r["badge"]["color"] == "rgb(255, 255, 255)"
                                      and r["badge"]["weight"] == "700" and r["badge"]["disc"] == fill for r in m),
                  json.dumps([r["badge"] for r in m]))
            check("a mention lights the bell's dot, as a comment does (\"Activity, something new\")",
                  bell == "Activity, something new", bell)
            # IT LANDS: the comment's row opens the comment on its page, glowing.
            ctx, pg = browser_as(b, ada)
            go(pg, "/social/activity", wait=300)
            pg.locator(f'a.act-row[href$="#c-{c7}"]').first.tap(timeout=5000)
            try:
                pg.wait_for_function("(id) => { const li = document.getElementById('c-' + id); return !!li && li.classList.contains('is-landed'); }",
                                     arg=c7, timeout=6000)
            except Exception:  # noqa: BLE001 -- not glowing is the row's red
                pass
            landed = pg.evaluate("(id) => { const li = document.getElementById('c-' + id); if (!li) return null; const r = li.getBoundingClientRect();"
                                 " return { url: location.pathname + location.hash, glow: li.classList.contains('is-landed'),"
                                 " seen: r.top >= 0 && r.top < innerHeight }; }", c7)
            close_ctx(ctx, pg)
            check("the comment's row lands on the comment on its page, in view, glowing as a comment's row does",
                  bool(landed) and landed["url"] == f"/social/p/{b7}#c-{c7}" and landed["glow"] and landed["seen"],
                  json.dumps(landed))
            # NEVER: from somebody muted (nor the dot), through a block either
            # way, from yourself, about anything taken down or not shown.
            nel = someone(b, "nel", "Nel Cho")
            oz = someone(b, "ozzy", "Oz Park")
            pat = someone(b, "pat", "Pat Ruiz")
            mute(ada, "nel")
            block(ada, "ozzy")
            block(pat, "ada")
            activity(ada)
            post(nel, "@ada from Nel, muted", seed=73)
            post(oz, "@ada from Oz, blocked", seed=74)
            post(pat, "@ada from Pat, who blocked her", seed=75)
            post(ada, "Me, @ada, to myself", seed=76)
            gone = post(rook, "@ada a post to be taken down", seed=77)
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (gone,))
            under = post(bea, "Section 7, Bea's, to be taken down", seed=78)
            cu = comment(rook, ("p", under), "@ada on a post taken down")
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (under,))
            bell2, rows2, _ = activity(ada)
            says2 = [r["say"] for r in rows2 if r["isNew"]]
            check("never from somebody muted (quiet, and no dot), through a block either way, from herself, or about a"
                  " post taken down or a comment under one: nothing new, and the bell dark",
                  says2 == [] and bell2 == "Activity" and bool(cu), json.dumps([says2, bell2]))
            # ONE ROW, NOT TWO: a comment on her post, an answer to her, a quote
            # of her post, each mentioning her too.
            a7 = post(ada, "Section 7, Ada's own", seed=79)
            ca = comment(rook, ("p", a7), "@ada this is lovely")
            cb = comment(ada, ("p", b7), "Thanks!", answer_to=c7)
            ans = comment(rook, ("p", b7), "@ada you're welcome", answer_to=cb)
            q7, _, _ = make_post(rook, "Quoting @ada", payload=False, extra={"quote": a7})
            bell3, rows3, _ = activity(ada)
            says3 = sorted((r["say"], r["href"]) for r in rows3 if r["isNew"])
            check("one row, not two: a comment on her post that mentions her is the comment's row (\"said something"
                  " on your post\"), an answer to her the answer's, a quote of her post the quote's; and the dot is lit",
                  says3 == sorted([("Rook said something on your post", f"/social/p/{a7}#c-{ca}"),
                                   ("Rook answered your comment", f"/social/p/{b7}#c-{ans}"),
                                   ("Rook quoted your post", f"/social/p/{q7}")]) and bell3 == "Activity, something new",
                  json.dumps([says3, bell3]))
            # GONE WITH IT: the post deleted, the comment deleted.
            rc = rook.client()
            rc.get(f"/social/p/{r7}")
            st_d = rc.post_json(f"/social/p/{r7}/delete", {})[0]
            rc.get(f"/social/p/{b7}")
            st_c = rc.post_json(f"/social/c/{c7}/delete", {})[0]
            _, rows4, _ = activity(ada)
            check("gone with what said it: the post deleted, the comment deleted, and their rows with them",
                  st_d == 200 and st_c == 200 and not any(r["say"] == "Rook mentioned you" for r in rows4),
                  json.dumps([st_d, st_c, [r["say"] for r in rows4]]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    # On a copy of the database, the site's code with SQLite's cascade OFF
    # (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then
    # goes because the code said so.
    PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Comment, Mention, Person, Post
    from social.accounts import delete_person
    from social.comments import drop_comments
    from social.posts import drop_post
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    post_id, comment_id, person = sys.argv[1], sys.argv[2], sys.argv[3]
    n = lambda w: db.session.execute(sa.select(sa.func.count()).select_from(Mention).where(w)).scalar()
    row = db.session.execute(sa.select(Post).where(Post.public_id == post_id)).scalar_one()
    pid = row.id
    before = n(Mention.post_id == pid)
    drop_post(db.session.get(Person, row.person_id).public_id, row)
    db.session.commit()
    out = {"fk": fk, "post": [before, n(Mention.post_id == pid)]}
    c = db.session.execute(sa.select(Comment).where(Comment.public_id == comment_id)).scalar_one()
    cid = c.id
    under = [r[0] for r in db.session.execute(sa.select(Comment.id).where(Comment.parent_id == cid))]
    before = n(Mention.comment_id.in_([cid] + under))
    drop_comments([cid])
    db.session.commit()
    out["comment"] = [before, n(Mention.comment_id.in_([cid] + under))]
    who = db.session.execute(sa.select(Person).where(Person.handle_key == person)).scalar_one()
    mine = sa.or_(Mention.person_id == who.id, Mention.by_id == who.id, Mention.owner_id == who.id)
    before = n(mine)
    delete_person(db.session, who.id)
    db.session.commit()
    out["person"] = [before, n(mine)]
    print(json.dumps(out))
"""

    if part(8, "deleting, in code: a post, a comment and its answers, a drawing on the site, an account; cascade off;"
               " a drawing's comments moving into a post keep theirs"):
        try:
            gus = someone(b, "gus", "Gus Hart")
            hal = someone(b, "hal", "Hal Ito")
            ivy = someone(b, "ivy", "Ivy Cole")

            def count(sql, args=()):
                return db("select count(*) from social_mentions m " + sql, args)[0][0]
            g1 = post(gus, "@hal and @ivy, a post to delete", seed=81)
            g2 = post(gus, "Section 8, Gus's", seed=82)
            k1 = comment(hal, ("p", g2), "@ivy a comment to delete")
            k2 = comment(ivy, ("p", g2), "@gus an answer under it", answer_to=k1)
            gd = make_drawing(gus, "Section 8, Gus's drawing", seed=83)
            k3 = comment(hal, ("s", gd), "@ivy on the drawing")
            had = (count("join social_posts t on t.id = m.post_id where t.public_id = ?", (g1,)),
                   count("join social_comments t on t.id = m.comment_id where t.public_id in (?, ?)", (k1, k2)),
                   count("join social_comments t on t.id = m.comment_id where t.public_id = ?", (k3,)))
            gc = gus.client()
            gc.get(f"/social/p/{g1}")
            s1 = gc.post_json(f"/social/p/{g1}/delete", {})[0]
            hc = hal.client()
            hc.get(f"/social/p/{g2}")
            s2 = hc.post_json(f"/social/c/{k1}/delete", {})[0]
            gc.get(f"/social/b/{gd}")
            s3 = gc.post_json(f"/social/b/{gd}/delete", {})[0]
            left = db("select count(*) from social_mentions m left join social_posts t on t.id = m.post_id left join"
                      " social_comments c on c.id = m.comment_id where (m.post_id is not null and t.id is null) or"
                      " (m.comment_id is not null and c.id is null)")[0][0]
            check("deleting a post takes its mentions; deleting a comment takes its mentions and its answers'; a"
                  " drawing deleted through the site takes its comments' (each through its own route)",
                  had == (2, 2, 1) and (s1, s2, s3) == (200, 200, 200) and left == 0
                  and count("where m.typed in ('hal', 'ivy', 'gus') and (m.post_id in (select id from social_posts where"
                            " public_id = ?) or m.comment_id in (select id from social_comments where public_id in (?, ?, ?)))",
                            (g1, k1, k2, k3)) == 0,
                  json.dumps([had, [s1, s2, s3], left]))
            # AN ACCOUNT: every mention of it, by it, and on what it owned.
            jo = someone(b, "joss", "Jo Bell")
            j1 = post(jo, "Section 8, Jo's", seed=84)
            post(gus, "Section 8, @joss named", seed=85)
            post(jo, "Section 8, Jo names @gus", seed=86)
            comment(hal, ("p", j1), "@ivy on Jo's post")
            jid = db("select id from social_people where handle_key = 'joss'")[0][0]
            had_j = count("where m.person_id = ? or m.by_id = ? or m.owner_id = ?", (jid, jid, jid))
            jc = jo.client()
            jc.get("/social/you/delete")
            sj = jc.post_form("/social/you/delete", {"confirm": "joss"})[0]
            left_j = count("where m.person_id = ? or m.by_id = ? or m.owner_id = ?", (jid, jid, jid))
            check("deleting an account takes every mention of it, every one it wrote and every one on what it owned",
                  had_j == 3 and left_j == 0 and not db("select 1 from social_people where id = ?", (jid,)),
                  json.dumps([sj, had_j, left_j]))
            # WITH SQLITE'S CASCADE OFF, on a copy: what goes goes by the code.
            kim = someone(b, "kim", "Kim Ash")
            h1 = post(hal, "@ivy and @gus, for the copy", seed=87)
            h2 = post(hal, "Section 8, Hal's other", seed=88)
            hk = comment(ivy, ("p", h2), "@gus for the copy")
            comment(gus, ("p", h2), "@ivy under it", answer_to=hk)
            post(kim, "@hal from Kim", seed=89)
            post(hal, "@kim from Hal", seed=90)
            copy = os.path.join(TMP, "cascade-off.db")
            con = sqlite3.connect(DB)
            con.execute("vacuum into ?", (copy,))
            con.close()
            env = dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0")
            out = subprocess.run([sys.executable, "-c", PROBE, h1, hk, "kim"], cwd=ROOT, env=env, capture_output=True,
                                 text=True, timeout=180)
            got = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else {"err": out.stderr[-600:]}
            check("with SQLite's cascade off (a copy): a post's mentions (2, then 0), a comment's and its answer's"
                  " (2, then 0), an account's of it, by it and on what it owned (2, then 0), each by the code alone",
                  got.get("fk") == 0 and got.get("post") == [2, 0] and got.get("comment") == [2, 0]
                  and got.get("person") == [2, 0], json.dumps(got)[:600])
            # ONE DRAWING, ONE CONVERSATION: a drawing's comment that mentions
            # somebody moves into the post with it, its mention with it, and
            # Activity's row lands on the post.
            ivy_seen = activity(ivy)
            kd = make_drawing(kim, "Section 8, Kim's drawing", seed=91)
            km = comment(hal, ("s", kd), "@ivy before it was a post")
            kp, sk, _ = make_post(kim, "Kim's drawing, a post now", payload=False, extra={"skribl": kd})
            moved = db("select t.post_id is not null, t.drawing_id from social_comments t join social_mentions m on"
                       " m.comment_id = t.id where t.public_id = ?", (km,))
            _, rows_i, _ = activity(ivy)
            hit = [r["href"] for r in rows_i if r["say"] == "Hal mentioned you" and km in r["href"]]
            check("a drawing's comment that mentions somebody moves into the post with the drawing, its mention with it,"
                  " and Activity's row lands on the post",
                  sk == 200 and moved == [(1, None)] and hit == [f"/social/p/{kp}#c-{km}"] and bool(ivy_seen),
                  json.dumps([sk, moved, hit]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    # The reads as the code sends them, planned by SQLite; and how many reads of
    # the cards' mentions a page of Home's cards makes (cookies: a signed-in
    # viewer's).
    READS = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Comment, Person, Post
    from social import activity as A, mentions as M
    me = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    posts = [r[0] for r in db.session.execute(sa.select(Post.id).limit(20)).all()]
    comments = [r[0] for r in db.session.execute(sa.select(Comment.id).limit(20)).all()]
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        for name, call in (("the cards' links", lambda: M.links(posts=posts)),
                           ("the comments' links", lambda: M.links(comments=comments)),
                           ("activity's mentions", lambda: A._mentions(me, frozenset({-1}), quiet=frozenset({-2}))),
                           ("the list, an @ alone", lambda: M.suggest(me, "")),
                           ("the list, @v", lambda: M.suggest(me, "v"))):
            rec.clear()
            call()
            calls[name] = [(st, pr) for st, pr in rec if "social_blocks" not in st and "taken_down_at IS NOT NULL" not in st]
    event.remove(db.engine, "before_cursor_execute", keep)
    conn = db.session.connection()
    plans = {name: [r[3] for st, params in sent for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
             for name, sent in calls.items()}
    seen = []
    def count(conn, cursor, statement, *a):
        if "social_mentions.typed, social_people.handle" in statement:
            seen.append(" ".join(statement.split())[:90])
    event.listen(db.engine, "before_cursor_execute", count)
    page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": sys.argv[2], "X-Forwarded-For": "10.250.1.4"})
    event.remove(db.engine, "before_cursor_execute", count)
    print(json.dumps({"plans": plans, "sent": {k: len(v) for k, v in calls.items()}, "reads": seen,
                      "cards": page.get_data(as_text=True).count('class="post-card"'),
                      "links": page.get_data(as_text=True).count('class="mention"')}))
"""

    if part(9, "the data: the chain on a populated database, its CHECK, once a person a thing; the reads on their"
               " indexes; a page of Home's cards asks once"):
        try:
            def alembic(dbfile, *args):
                env = dict(os.environ, DATABASE_URL=f"sqlite:///{dbfile}")
                return subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", *args], cwd=ROOT, env=env,
                                      capture_output=True, text=True, timeout=180)
            heads = subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", "heads"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=60).stdout.split()
            chain = os.path.join(TMP, "chain.db")
            want_idx = {"ix_social_mentions_person_post", "ix_social_mentions_person_comment",
                        "ix_social_mentions_person_created", "ix_social_mentions_post_id", "ix_social_mentions_comment_id",
                        "ix_social_mentions_by_id", "ix_social_mentions_owner_id"}
            a1 = alembic(chain, "upgrade", "3e7b508ff939")
            con = sqlite3.connect(chain)
            for i, (h, n) in enumerate((("one", "One Ash"), ("two", "Two Birch")), start=1):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle, is_admin,"
                            " session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1,"
                            " '2026-11-01 10:00:00.000000', '2026-11-01 10:00:00.000000')", (i, f"site:{h}", h, h, n, bytes([i])))
            con.execute("insert into social_posts (id, public_id, person_id, words, skribl_id, created_at) values (1, 'post0000001',"
                        " 1, 'Old words for @two', 'sk1', '2026-11-02 10:00:00.000000')")
            con.execute("insert into social_comments (id, public_id, post_id, owner_id, person_id, words, created_at) values"
                        " (1, 'comment0001', 1, 1, 2, 'And @one back', '2026-11-02 11:00:00.000000')")
            con.commit()
            con.close()
            a2 = alembic(chain, "upgrade", "head")
            con = sqlite3.connect(chain)
            cols = [r[1] for r in con.execute("pragma table_info(social_mentions)")]
            idx = {r[0] for r in con.execute("select name from sqlite_master where type='index' and tbl_name = 'social_mentions'")}
            name_idx = con.execute("select sql from sqlite_master where name = 'ix_social_people_name_key'").fetchone()
            sql = (con.execute("select sql from sqlite_master where name = 'social_mentions'").fetchone() or [""])[0]
            rows = con.execute("select count(*) from social_mentions").fetchone()[0]
            kept = (con.execute("select words from social_posts").fetchall(), con.execute("select words from social_comments").fetchall())
            stamp_ = con.execute("select version_num from social_alembic_version").fetchall()
            refused = {}
            for nm, stmt in (("in neither a post nor a comment", "insert into social_mentions (person_id, by_id, owner_id, typed,"
                              " created_at) values (2, 1, 1, 'two', '2026-11-04')"),
                             ("in a post and a comment at once", "insert into social_mentions (person_id, by_id, post_id,"
                              " comment_id, owner_id, typed, created_at) values (2, 1, 1, 1, 1, 'two', '2026-11-04')"),
                             ("one person twice in one post", "insert into social_mentions (person_id, by_id, post_id, owner_id,"
                              " typed, created_at) values (2, 1, 1, 1, 'two', '2026-11-04'), (2, 1, 1, 1, 'Two', '2026-11-04')"),
                             ("one person twice in one comment", "insert into social_mentions (person_id, by_id, comment_id,"
                              " owner_id, typed, created_at) values (1, 2, 1, 1, 'one', '2026-11-04'), (1, 2, 1, 1, 'one',"
                              " '2026-11-04')")):
                try:
                    con.execute(stmt)
                    refused[nm] = False
                except sqlite3.IntegrityError:
                    refused[nm] = True
            con.rollback()
            con.close()
            a3 = alembic(chain, "downgrade", "3e7b508ff939")
            con = sqlite3.connect(chain)
            gone = (not con.execute("select 1 from sqlite_master where name = 'social_mentions'").fetchone()
                    and not con.execute("select 1 from sqlite_master where name = 'ix_social_people_name_key'").fetchone())
            back = (con.execute("select words from social_posts").fetchall(), con.execute("select words from social_comments").fetchall())
            con.close()
            check("the chain on a populated database: one head (6dc6c4054756, after the reposts'); up, the table"
                  " social_mentions (who, by whom, in a post or a comment, whose, as typed, when) with its CHECK and its"
                  " seven indexes, and the names' index on social_people; no row written (old words with an @ in them"
                  " stay words), every post and comment as it was",
                  heads == ["6dc6c4054756", "(head)"] and a1.returncode == 0 and a2.returncode == 0
                  and cols == ["id", "person_id", "by_id", "post_id", "comment_id", "owner_id", "typed", "created_at"]
                  and want_idx <= idx and bool(name_idx) and "lower(display_name)" in name_idx[0]
                  and "ck_social_mentions_on_one" in sql and rows == 0 and stamp_ == [("6dc6c4054756",)]
                  and kept == ([("Old words for @two",)], [("And @one back",)]),
                  json.dumps({"heads": heads, "cols": cols, "missing": sorted(want_idx - idx), "name": name_idx,
                              "rows": rows, "a2": a2.stderr[-300:] if a2.returncode else ""}))
            check("the CHECK and the pairs hold: a mention in neither a post nor a comment, in both at once, one person"
                  " twice in one post or in one comment: refused", all(refused.values()) and len(refused) == 4,
                  json.dumps(refused))
            check("back down, the table and the names' index are gone and every post and comment kept",
                  a3.returncode == 0 and gone and back == kept, f"{a3.returncode} {a3.stderr.strip().splitlines()[-1:]}")
            # THE READS, on their indexes; and Home's cards asking once.
            mira = list_people()
            pia = someone(b, "pia", "Pia Lund")
            for i in range(22):
                post(pia, f"Section 9, Pia's {i}, for @mira and @pip", seed=900 + i)
            cookie = "; ".join(f"{c_['name']}={c_['value']}" for c_ in mira.ctx.cookies(BASE))
            out = subprocess.run([sys.executable, "-c", READS, "mira", cookie], cwd=ROOT, env=ENV, capture_output=True,
                                 text=True, timeout=180)
            got = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else {"err": out.stderr[-600:]}
            plans = got.get("plans", {})
            on = {"the cards' links": ["ix_social_mentions_post_id"],
                  "the comments' links": ["ix_social_mentions_comment_id"],
                  "activity's mentions": ["ix_social_mentions_person_created"],
                  "the list, an @ alone": ["ix_social_follows_", "ix_social_people_handle_key", "ix_social_people_name_key"],
                  "the list, @v": ["ix_social_follows_", "ix_social_people_handle_key", "ix_social_people_name_key"]}
            missing = {k: [ix for ix in v if not any(ix in line for line in plans.get(k, []))] for k, v in on.items()}
            scans = {k: [line for line in v if re.match(r"SCAN (social_mentions|social_people)\b", line)] for k, v in plans.items()}
            check("the reads on their indexes (SQLite's own plan): the links in a page's cards and in its comments, a"
                  " post's and a comment's own; Activity's on the person's own, newest first; the list's on your"
                  " follows, the handles' own and the names', never a scan of the people or the mentions",
                  plans and not any(missing.values()) and not any(scans.values()),
                  json.dumps({"missing": missing, "scans": scans, "plans": plans})[:900])
            check("a page of Home's cards (twenty, every one naming somebody) reads their mentions once, and shows them",
                  got.get("cards", 0) >= 20 and len(got.get("reads", [])) == 1 and got.get("links", 0) >= 20,
                  json.dumps({k: got.get(k) for k in ("cards", "reads", "links", "err")})[:500])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "contrast and targets: the mention off the paint on the card and a comment's ground; the list's words;"
                " Activity's row and its @; every target 44px but the mentions inside words"):
        try:
            mira = list_people()
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            p10 = post(rook, "Skull study, outline first. @juno, your hat was the idea!", seed=101)
            c10 = comment(rook, ("p", p10), "@juno look at the timing on this!")
            # Each mention read where it is painted: its own box against the
            # ground just before it (the card's, or a comment's, the page's).
            BOX = r"""(sel) => { const a = document.querySelector(sel); if (!a) return null; a.scrollIntoView({ block: 'center' });
              const r = a.getClientRects()[0]; return { box: [r.left, r.top, r.width, r.height], ground: [r.left - 3, r.top + r.height / 2] }; }"""
            CALC = r"""(sel) => { const a = document.querySelector(sel); if (!a) return null;
              const rgb = s => s.match(/[\d.]+/g).slice(0, 3).map(Number);
              const lum = c => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                                 return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
              let g = a, bg = 'rgba(0, 0, 0, 0)'; while (g && (bg = getComputedStyle(g).backgroundColor) && /rgba\(.*, 0\)$/.test(bg)) g = g.parentElement;
              const x = lum(rgb(getComputedStyle(a).color)), y = lum(rgb(bg));
              return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; }"""
            paints, calcs, lows, smalls, inline, reads, fields = {}, {}, [], [], [], {}, []
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen} {scheme}"
                    ctx, pg = browser_as(b, mira, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=600)
                    sel = card(p10) + " .post-words a.mention"
                    bx = pg.evaluate(BOX, sel)
                    pg.wait_for_timeout(300)
                    bx = pg.evaluate(BOX, sel)
                    paints[(tag, "card")] = off_paint(pg, bx and bx["box"], bx and bx["ground"])
                    calcs[(tag, "card")] = pg.evaluate(CALC, sel)
                    got = [("Home's card", pg.evaluate(READ, card(p10)))]
                    open_composer(pg)
                    lst = typed(pg, "@v")
                    got.append(("the list", pg.evaluate(READ, "#composeMentions")))
                    pg.keyboard.press("ArrowDown")
                    pg.wait_for_timeout(150)
                    got.append(("the list, a row highlighted", pg.evaluate(READ, "#composeMentions")))
                    fields.append((tag, (lst or {}).get("field", {}).get("size")))
                    go(pg, f"/social/p/{p10}", wait=600)
                    sel = f"#c-{c10} .cm-words a.mention"
                    bx = pg.evaluate(BOX, sel)
                    pg.wait_for_timeout(300)
                    bx = pg.evaluate(BOX, sel)
                    paints[(tag, "comment")] = off_paint(pg, bx and bx["box"], bx and bx["ground"])
                    calcs[(tag, "comment")] = pg.evaluate(CALC, sel)
                    got.append(("a post's page and its comments", pg.evaluate(READ, ".post-page")))
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, juno, screen=screen, scheme=scheme)
                    go(pg, "/social/activity", wait=500)
                    row = "a.act-row[href*='" + p10 + "']"
                    to(pg, row, 160)
                    got.append(("Activity's mention rows", pg.evaluate(READ, ".act-list")))
                    calcs[(tag, "badge")] = pg.evaluate(CALC, row + " .mn-at") if pg.evaluate("(s) => !!document.querySelector(s)", row + " .mn-at") else None
                    bx = pg.evaluate(r"""(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
                      return { box: [r.left + 4, r.top + 3, r.width - 8, r.height - 6], ground: [r.left + 2.5, r.top + r.height / 2] }; }""",
                                     row + " .mn-at")
                    paints[(tag, "badge")] = off_paint(pg, bx and bx["box"], bx and bx["ground"])
                    close_ctx(ctx, pg)
                    reads[tag] = [(w, r["read"], r["lowest"]) for w, r in got]
                    lows += [f"{tag} {w}: {x}" for w, r in got for x in r["low"]]
                    smalls += [f"{tag} {w}: {x}" for w, r in got for x in r["small"]]
                    inline += [(tag, w, x) for w, r in got for x in r["inline"]]
            mock = {("light", "card"): 8.26, ("dark", "card"): 8.39, ("light", "comment"): 7.75, ("dark", "comment"): 9.89}
            off = {" ".join(k): v for k, v in calcs.items() if k[1] in ("card", "comment")
                   and v != mock[(k[0].split()[1], k[1])]}
            check("the mention's ink is the mock's, against what it sits on: 8.26:1 on the card light, 8.39 dark; 7.75 on"
                  " a comment's ground light, 9.89 dark; phone and desk",
                  len([k for k in calcs if k[1] in ("card", "comment")]) == 8 and not off, json.dumps({"off": off}))
            check("...and read off the paint, 4.5:1 or more against the ground beside it, on the card and on a"
                  " comment's ground, phone and desk, light and dark",
                  all(v and v["best"] >= 4.5 for k, v in paints.items() if k[1] in ("card", "comment"))
                  and len([k for k in paints if k[1] in ("card", "comment")]) == 8,
                  json.dumps({" ".join(k): v and v["best"] for k, v in paints.items() if k[1] != "badge"}))
            check("every word at 4.5:1 or more on what is painted behind it, phone and desk, light and dark: Home's card"
                  " with its mention, the list (its highlighted row too), a post's page and its comments, Activity's"
                  " mention rows; the field 16px or more",
                  len(reads) == 4 and all(n > 0 for v in reads.values() for _, n, _ in v) and not lows
                  and all(s and s >= 16 for _, s in fields), f"low {lows[:4]}; read {json.dumps(reads)[:500]}; fields {fields}")
            check("Activity's @ on the purple disc: white on --fill, 5.33:1 computed (the mock's), and 3:1 or more off"
                  " the paint",
                  all(calcs.get((t, "badge")) == 5.33 for t in reads) and all(v and v["best"] >= 3 for k, v in paints.items() if k[1] == "badge"),
                  json.dumps({" ".join(k): [calcs.get(k), v and v["best"]] for k, v in paints.items() if k[1] == "badge"}))
            check("every target 44px or more, but the mentions: links inside words (WCAG 2.5.8's inline exception), each"
                  " painted where it is",
                  not smalls and len(inline) >= 8 and all(x["painted"] for _, _, x in inline),
                  f"small {smalls[:4]}; mentions {[(t, w, x) for t, w, x in inline if not x['painted']][:3]} of {len(inline)}")
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
