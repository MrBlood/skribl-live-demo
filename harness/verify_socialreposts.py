#!/usr/bin/env python3
"""Reposts and quote posts on the Skribl site (the map, part two, item 3;
docs/SOCIAL-SITE.md section 17; the owner's "All yes" on the reposts mock,
Nov 14), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. THE ROW: comment · repost · heart · ⋯ · Open › on Home's card (a post's
     page and a drawing's without Open ›), Share gone from it (Share… and Copy
     link in the ⋯); the repost 44px, the mock's arrows at 20px in the row's
     ink, how many reposts and quotes beside them, none at zero; lit in the
     small violet ink once yours; three counts in the hundreds fitting a 402px
     touch phone, read off the paint, in the page's face, in DejaVu Sans, and in
     Inter, Liberation Sans and FreeSans where the box has them.
  2. THE SHEET: a tap raises #repostSheet, the ⋯'s shape, one card: Repost
     ("Show it to the people who follow you") and Quote ("Repost it with your
     own words, or a drawing"), the arrows and the bar's Make pencil; once
     yours, Undo repost ("Take it off your page and your followers’ Home"); a
     drawing shown outside a post, Quote alone; signed out, "Repost this
     post?"; it rises gliding, read on every frame.
  3. A TAP REPOSTS: the sheet goes down, the repost lights and its count moves
     at once, before the site answers, and after a reload; its count fades
     in and the button grows round the arrows while the heart moves along,
     read on every frame (Reduce Motion: no glide); Undo repost; taps made
     while one is asked end where the last says; no toast.
  4. WHO MAY REPOST OR QUOTE: signed out, no token, another origin, taken
     down, a block either way, a post taken down or not there, a body that
     is not a yes or a no: refused, nothing made; one repost a person a post;
     your own post too; your own repost undone whatever became of the post;
     the limit (120 an hour); a quote of what may not be quoted, of two
     things, or of nothing but nothing: refused.
  5. HOME'S FOLLOWING: a repost by somebody you follow shows the original's
     card with "Mira Lopez reposted" inside it at its top, its own hearts and
     comments; Everyone shows posts only; the same post twice in a page once,
     the newest; yours "You reposted"; nobody muted, nothing a block hides,
     nothing taken down; Load more, none twice and none missed.
  6. A POSTS TAB: their posts and reposts merged, newest first, the line on
     each repost ("You reposted" on your own page); Load more.
  7. QUOTE POSTS: your card with the original small inside it (its author's
     name and @handle, its words two lines at most, its drawing as the
     Gallery's still picture painted with "drawn in"), one link to the
     original; a quote with its own drawing; a drawing's quote; the original
     gone, hidden by a block, or taken down: "This post is gone."; the quote's
     own page; the original's count, reposts and quotes. A quote of a quote
     shows the drawing it leads to, however deep (A, Nov 16), until a post
     its viewer may not see; and Make shows it as the post will.
  8. ACTIVITY: "Mira reposted your post" (to the post), "Rook quoted your
     post" (to the quote, its words under it); Undo repost takes its row
     away; nobody muted; neither lights the bell's dot.
  9. DELETING, IN CODE: a post with reposts and quotes (the quotes stay,
     saying it is gone), a drawing, an account; and with SQLite's cascade off
     on a copy.
 10. THE DATA: the chain on a populated database (the table, the columns,
     their indexes and CHECKs; one head; back down); one repost a person a
     post; the CHECKs hold; the reads on their indexes; a page of Home's cards
     asks once.
 11. CONTRAST AND TARGETS: the "reposted" line and the lit arrows read off
     the paint, phone and desk, light and dark; every word on the sheet, the
     signed-out sheet and a quote's small card (and its gone words) at 4.5:1,
     every target 44px; inside a post's card the quote a well (D2).
 13. JUST A BORDER: on the site's pages, phone and desk, light and dark, no
     box with something in it is set apart from what it sits on by its line
     alone (the owner's question, Nov 16).
 12. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALREPOSTS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Reposts and quote posts".
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
PART = os.environ.get("SOCIALREPOSTS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALREPOSTS {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence reposts work.")
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
TMP = tempfile.mkdtemp(prefix="socialreposts-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialreposts-" + secrets.token_hex(8),
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
    return f"10.{120 + _addr[0] // 250}.{_addr[0] % 250}.9"


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
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def get(self, path):
        st, text = self._req("GET", path)
        m = re.search(r'<meta name="social-csrf" content="([^"]+)"', text)
        if m:
            self.token = m.group(1)
        return st, text

    def post_json(self, path, body, token=None):
        st, text = self._req("POST", path, body=body, headers={"X-Social-CSRF": self.token or "" if token is None else token})
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, form):
        return self._req("POST", path, form=dict(form, csrf=self.token or ""))


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


def make_post(who, words, seed=0, payload=None):
    """A post as Home's composer sends one: its public id, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": payload or drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def make_drawing(who, title, seed=0, vis="public"):
    """A drawing from the Pad (shown in the gallery when public): its skribl's public id, or None."""
    who.pg.goto(BASE + "/social/")
    st, sid = who.pg.evaluate(PAD, [title, vis, seed])
    return sid if st == 201 else None


def page_of(on):
    kind, oid = on
    return f"/social/{'p' if kind == 'p' else 'b'}/{oid}"


def block(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/block", {})[0]


def skribl_of(post):
    got = db("select skribl_id from social_posts where public_id = ?", (post or "",))
    return got[0][0] if got else None


def ready(pg):
    """The page and its deferred scripts (they have all run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def card(post):
    return f'.post-card[data-post="{post}"]'


# ---- the census of words and targets (verify_sociallikes' READ) -----------------
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
  roots.forEach(root => root.querySelectorAll('*').forEach(e => {
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
  document.querySelectorAll('a[href], button, input, textarea, select, [role=button]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    if (e.matches('input[type=radio]')) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

# ---- reposts: the site's own requests -------------------------------------------

def repost(who, post, on=True, raw=None, token=None, origin=BASE):
    """A repost made (or undone) as the sheet sends one: (status, answer)."""
    c = who.client() if who is not None else Client()
    c.origin = origin
    c.get(f"/social/p/{post}")
    if not c.token:
        c.get("/social/")      # a page they cannot open: the token from one they can
    return c.post_json(f"/social/p/{post}/repost", raw if raw is not None else {"reposted": on}, token=token)


def quote(who, words, post=None, drawing=None, payload=None, extra=None):
    """A quote as the composer sends one: (its address or None, status, answer)."""
    c = who.client()
    c.get("/social/")
    body = {"words": words}
    if post is not None:
        body["quote"] = post
    if drawing is not None:
        body["quote_drawing"] = drawing
    if payload is not None:
        body["payload"] = payload
    body.update(extra or {})
    st, j = c.post_json("/social/posts", body)
    return (j.get("post") if st == 200 and isinstance(j, dict) else None), st, j


def with_poster(payload):
    """A drawing as the Pad hands one back with its share card's picture (the
    poster every tile shows: a 1200 x 630 PNG, the drawing's purple on its
    paper), so a still picture has something of the drawing's own to paint."""
    import base64
    from PIL import ImageDraw
    im = Image.new("RGB", (1200, 630), (246, 242, 234))
    d = ImageDraw.Draw(im)
    d.line([(180, 420), (360, 180), (560, 400), (760, 160), (1000, 420)], fill=(124, 92, 255), width=26)
    d.ellipse((840, 90, 960, 210), fill=(124, 92, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return dict(payload, thumbnail="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())


def act(who, path, body=None):
    c = who.client()
    c.get("/social/")
    return c.post_json(path, body if body is not None else {})[0]


def follow(who, handle, on=True):
    return act(who, f"/social/@{handle}/follow", {"following": on})


def mute(who, handle):
    return act(who, f"/social/@{handle}/mute")


def reposts_of(post):
    """Who reposted a post: [handle], oldest first."""
    return [r[0] for r in db("select p.handle from social_reposts r join social_posts s on s.id = r.post_id"
                             " join social_people p on p.id = r.person_id where s.public_id = ? order by r.id", (post,))]


def quote_row(post):
    """A post's quote columns: (is_quote, quoted post's address, quoted drawing, quoted owner's handle, skribl_id)."""
    got = db("select s.is_quote, o.public_id, s.quoted_drawing_id, p.handle, s.skribl_id from social_posts s"
             " left join social_posts o on o.id = s.quoted_post_id left join social_people p on p.id = s.quoted_owner_id"
             " where s.public_id = ?", (post,))
    return tuple(got[0]) if got else None


def stamp(post, seconds_ago):
    """A post's time set back, in the site's own form (microseconds, as it writes them)."""
    db_write("update social_posts set created_at = strftime('%Y-%m-%d %H:%M:%f000', 'now', ?) where public_id = ?",
             (f"-{int(seconds_ago)} seconds", post))


def stamp_repost(post, handle, seconds_ago):
    db_write("update social_reposts set created_at = strftime('%Y-%m-%d %H:%M:%f000', 'now', ?) where post_id ="
             " (select id from social_posts where public_id = ?) and person_id = (select id from social_people where"
             " handle_key = ?)", (f"-{int(seconds_ago)} seconds", post, handle))


_extras = [0]


def extras(n):
    """`n` people written straight into the site's table (no passkey, never
    signed in): enough hearts, comments and reposts for counts in the
    hundreds. Their ids."""
    con = sqlite3.connect(DB, timeout=10)
    try:
        ids = []
        for _ in range(n):
            _extras[0] += 1
            k = _extras[0]
            cur = con.execute("insert into social_people (public_id, handle, handle_key, display_name, user_handle,"
                              " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, 0, 1,"
                              " strftime('%Y-%m-%d %H:%M:%f000', 'now'), strftime('%Y-%m-%d %H:%M:%f000', 'now'))",
                              (f"site:extra{k:05d}{secrets.token_hex(4)}", f"x{k:05d}", f"x{k:05d}", f"Extra {k}",
                               secrets.token_bytes(32)))
            ids.append(cur.lastrowid)
        con.commit()
        return ids
    finally:
        con.close()


def pile_on(post, n_comments, n_likes, n_reposts):
    """Counts in the hundreds on a post, written straight into the tables."""
    pid, owner = db("select id, person_id from social_posts where public_id = ?", (post,))[0]
    people = extras(max(n_likes, n_reposts, n_comments))
    con = sqlite3.connect(DB, timeout=10)
    try:
        now = "strftime('%Y-%m-%d %H:%M:%f000', 'now')"
        for i in people[:n_comments]:
            con.execute(f"insert into social_comments (public_id, post_id, owner_id, person_id, words, created_at)"
                        f" values (?, ?, ?, ?, 'hello', {now})", (secrets.token_urlsafe(8), pid, owner, i))
        for i in people[:n_likes]:
            con.execute(f"insert into social_likes (post_id, owner_id, person_id, created_at) values (?, ?, ?, {now})",
                        (pid, owner, i))
        for i in people[:n_reposts]:
            con.execute(f"insert into social_reposts (person_id, post_id, owner_id, created_at) values (?, ?, ?, {now})",
                        (i, pid, owner))
        con.commit()
    finally:
        con.close()


# ---- what a page shows -----------------------------------------------------------

# THE ROW under a post in `sel` (a card, or a page): its parts in order, and
# the repost's own reading: its box, its icon (the arrows' four lines, its
# size), its inks against the tokens', its count, its name, whether it is lit.
ROW = r"""(sel) => { const root = document.querySelector(sel); if (!root) return null;
  const row = root.querySelector(':scope > .post-row') || root.querySelector('.post-row'); if (!row) return null;
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  const name = e => e.classList.contains('post-count') ? 'comment' : e.classList.contains('rp-btn') ? 'repost'
    : e.classList.contains('lk-heart') ? 'heart' : e.classList.contains('post-share') ? 'share'
    : e.classList.contains('post-more') ? 'more' : e.classList.contains('post-open') ? 'open' : e.className;
  const out = { kids: [...row.children].filter(e => e.getClientRects().length).map(name), ink2: probe('var(--ink-2)'),
                accent: probe('var(--accent-ink)'), rp: null,
                menu: [...document.querySelectorAll('#postSheet .post-act')].map(b => b.getAttribute('data-act')) };
  const b = row.querySelector('.rp-btn'); if (!b) return out;
  const r = b.getBoundingClientRect(), svg = b.querySelector('svg'), n = b.querySelector('.rp-n');
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  out.rp = { w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10, left: r.left,
    icon: svg ? Math.round(svg.getBoundingClientRect().width * 10) / 10 : null,
    iconLeft: svg ? Math.round((svg.getBoundingClientRect().left - r.left) * 10) / 10 : null,
    d: svg ? [...svg.querySelectorAll('path')].map(p => p.getAttribute('d')) : [],
    color: getComputedStyle(b).color, icColor: svg ? getComputedStyle(svg).color : null,
    nColor: n ? getComputedStyle(n).color : null, n: n ? n.textContent.trim() : null, size: n ? getComputedStyle(n).fontSize : null,
    on: b.classList.contains('is-on'), label: b.getAttribute('aria-label'), popup: b.getAttribute('aria-haspopup'),
    controls: b.getAttribute('aria-controls'), hit: !!at && (at === b || b.contains(at)) };
  return out; }"""

# The arrows, as _icons.html draws them (the mock's own lines, rp_mock.py's RP).
ARROWS = ["M16.5 3l3 3-3 3", "M4.5 11.5V10a4 4 0 0 1 4-4h11", "M7.5 21l-3-3 3-3", "M19.5 12.5V14a4 4 0 0 1-4 4h-11"]

# THE FEED in `sel`'s list, in order: each card's post, whose it is, the line
# at its top (its words, where it sits, its type), and its small card.
FEED = r"""(sel) => { const list = document.querySelector(sel || '[data-feed]'); if (!list) return null;
  return [...list.querySelectorAll(':scope > .post-card')].map(c => { const by = c.querySelector(':scope > .rp-by');
    const head = c.querySelector(':scope > .post-head'), q = c.querySelector(':scope > .qt-card');
    const cr = c.getBoundingClientRect();
    return { post: c.getAttribute('data-post'), who: c.getAttribute('data-handle'),
      by: by ? by.textContent.replace(/\s+/g, ' ').trim() : null,
      byFirst: !!by && c.firstElementChild === by, byInside: !!by && by.getBoundingClientRect().top >= cr.top
        && by.getBoundingClientRect().bottom <= (head ? head.getBoundingClientRect().top + 1 : cr.bottom),
      quote: q ? { gone: q.classList.contains('is-gone'), href: q.getAttribute('href'), text: q.innerText.replace(/\s+/g, ' ').trim() } : null,
      art: !!c.querySelector(':scope > .post-art'), n: (c.querySelector('.rp-n') || {}).textContent || null }; }); }"""

# THE REPOST SHEET: open, its title, its rows as they show (name, what it does,
# icon lines, sizes, inks, box), and whether the ⋯'s sheet stayed down.
SHEET = r"""() => { const s = document.getElementById('repostSheet'); if (!s) return null;
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  return { open: s.classList.contains('is-open') && !s.hidden, title: (s.querySelector('h2') || {}).textContent,
    cards: s.querySelectorAll('.post-acts').length, ink: probe('var(--ink)'), ink2: probe('var(--ink-2)'),
    menuDown: !document.getElementById('postSheet') || !document.getElementById('postSheet').classList.contains('is-open'),
    rows: [...s.querySelectorAll('.post-act')].filter(b => !b.hidden && b.getClientRects().length).map(b => {
      const nm = b.querySelector('.mu-words b'), sy = b.querySelector('.mu-say'), ic = b.querySelector('svg');
      const r = b.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return { act: b.getAttribute('data-rp'), name: nm.textContent.trim(), say: sy.textContent.trim(),
        d: ic ? [...ic.querySelectorAll('path')].map(p => p.getAttribute('d')) : [],
        nameSize: getComputedStyle(nm).fontSize, nameWeight: getComputedStyle(nm).fontWeight, nameColor: getComputedStyle(nm).color,
        saySize: getComputedStyle(sy).fontSize, sayColor: getComputedStyle(sy).color,
        h: Math.round(r.height * 10) / 10, hit: !!at && (at === b || b.contains(at)) }; }) }; }"""

# The bar's Make pencil (the Quote row's icon is it).
PEN = "() => [...document.querySelectorAll('.tab-make svg path')].map(p => p.getAttribute('d'))"


def open_rp(pg, sel):
    """Press a repost (`sel`) and wait for its sheet to be up."""
    press(pg, sel)
    pg.wait_for_function("() => { const w = document.getElementById('repostSheet'); return !!w && w.classList.contains('is-open') && !w.hidden; }",
                         timeout=8000)
    pg.wait_for_timeout(450)


def press_rp_row(pg, act="repost", after=900):
    """Press a row of the repost sheet and wait for the site's answer (a press
    that sends nothing reads as the row's own red, never a stopped section)."""
    try:
        with pg.expect_response(lambda r: r.url.endswith("/repost") and r.request.method == "POST", timeout=8000):
            press(pg, f'#repostSheet [data-rp="{act}"]')
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(after)


def press(pg, sel):
    """A finger on a phone (a touch phone taps), a click on a desk."""
    loc = pg.locator(sel).first
    if pg.evaluate("() => matchMedia('(pointer: coarse)').matches"):
        loc.tap(timeout=5000)
    else:
        loc.click(timeout=5000)


def open_sheet(pg, opener, sheet_id="postSheet"):
    press(pg, opener)
    pg.wait_for_function("(id) => { const w = document.getElementById(id); return !!w && w.classList.contains('is-open') && !w.hidden; }",
                         arg=sheet_id, timeout=8000)
    pg.wait_for_timeout(450)


def to(pg, sel, top=100):
    """Scroll so that `sel` sits `top` px from the top of the window."""
    pg.evaluate("([s, y]) => { const e = document.querySelector(s); if (e) scrollTo(0, e.getBoundingClientRect().top + scrollY - y); }",
                [sel, top])
    pg.wait_for_timeout(250)


PAGE_ROW = ".post-page > .post-row"


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


#: The faces the row is read in besides the page's own: DejaVu Sans is wider
#: than any face the app is drawn in on a device, and the one CI draws in
#: (system-ui on Linux); Inter has SF's widths, near the owner's iPhone;
#: Liberation Sans and FreeSans have Arial's and Helvetica's (the page's own
#: stack names both), and CI has them where it has no Inter. A face the box
#: has not got is left out, so its fallback is not read twice.
FACES = ["DejaVu Sans", "Inter", "Liberation Sans", "FreeSans"]
FACE = """(f) => { let s = document.getElementById('rpFace');
  if (!s) { s = document.createElement('style'); s.id = 'rpFace'; document.head.appendChild(s); }
  s.textContent = f ? '.post-row, .post-row * { font-family: "' + f + '", sans-serif !important; }' : ''; }"""

# A card's row, its parts' boxes and the card's own inside, for reading off
# the paint; and whether the page runs past a phone's screen.
ROW_BOXES = r"""(sel) => { const c = document.querySelector(sel), row = c && c.querySelector('.post-row'); if (!row) return null;
  const cr = c.getBoundingClientRect(), cs = getComputedStyle(c), rr = row.getBoundingClientRect();
  return { card: [cr.left + parseFloat(cs.borderLeftWidth), cr.right - parseFloat(cs.borderRightWidth)],
    row: [rr.left, rr.top, rr.width, rr.height], vw: innerWidth, scale: visualViewport ? visualViewport.scale : 1,
    sw: document.documentElement.scrollWidth,
    kids: [...row.children].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect();
      return { k: e.className.split(' ')[0], l: r.left, r: r.right, w: r.width, h: r.height,
               n: (e.querySelector('.rp-n, .lk-n, span') || {}).textContent || '' }; }) }; }"""


def row_paint(pg, sel):
    """The row read off the paint (`sel` its card): the columns where anything
    but the card's own ground is painted, as each part's own ink: [left,
    right] of each part's ink (CSS px), what is painted outside every part's
    box, and the card's inside, its parts' boxes, the page's widths."""
    bx = pg.evaluate(ROW_BOXES, sel)
    if not bx or Image is None:
        return None
    x0, y0, w, h = bx["row"]
    clip = {"x": max(0, bx["card"][0] - 12), "y": y0 + 4, "width": min(bx["vw"], bx["card"][1] + 12) - max(0, bx["card"][0] - 12),
            "height": max(8, h - 8)}
    im = Image.open(io.BytesIO(pg.screenshot(clip=clip, scale="device"))).convert("RGB")
    k = im.width / clip["width"]
    px = im.load()
    # The card's own ground, and the page's beside it (outside the card).
    grounds = [px[int((bx["card"][0] - clip["x"] + 3) * k), im.height // 2], px[1, im.height // 2]]

    def painted(c):
        return all(max(abs(a - g) for a, g in zip(c, gr)) > 48 for gr in grounds)
    cols = [any(painted(px[x, y]) for y in range(im.height)) for x in range(im.width)]
    # The card's own hairline at each side is the card, not ink.
    edge = [bx["card"][0] - 1, bx["card"][1]]
    ink = [clip["x"] + x / k for x, on in enumerate(cols) if on]
    ink = [x for x in ink if min(abs(x - e) for e in edge) > 1.2]
    parts = []
    for kid in bx["kids"]:
        mine = [x for x in ink if kid["l"] - 0.5 <= x <= kid["r"] + 0.5]
        parts.append({"k": kid["k"], "n": kid["n"].strip(), "box": [round(kid["l"], 1), round(kid["r"], 1)],
                      "w": round(kid["w"], 1), "h": round(kid["h"], 1),
                      "ink": [round(min(mine), 1), round(max(mine) + 1 / k, 1)] if mine else None})
    stray = [round(x, 1) for x in ink if not any(kid["l"] - 0.5 <= x <= kid["r"] + 0.5 for kid in bx["kids"])]
    return {"parts": parts, "stray": stray[:6], "card": [round(v, 1) for v in bx["card"]], "vw": bx["vw"],
            "scale": bx["scale"], "sw": bx["sw"]}


def fits(rp, own_box=True):
    """The row as the phone paints it fits: every part's ink inside the card,
    8px or more of ground between two parts' ink, every part 44px to a
    finger, the page not past the screen; and in a face a device draws in
    (`own_box`), every part's ink inside its own box too (in DejaVu Sans,
    wider than any of those, a count may run a few pixels into the room
    beside it, as the bookmarks' tabs may draw closer there)."""
    if not rp or any(p["ink"] is None for p in rp["parts"]):
        return False
    inside = all(rp["card"][0] <= p["ink"][0] and p["ink"][1] <= rp["card"][1] for p in rp["parts"])
    past = [x for x in rp["stray"] if not (rp["card"][0] <= x <= rp["card"][1])]
    gaps = [b["ink"][0] - a["ink"][1] for a, b in zip(rp["parts"], rp["parts"][1:])]
    return (inside and not past and (not own_box or not rp["stray"]) and min(gaps) >= 8
            and all(p["w"] >= 44 and p["h"] >= 44 for p in rp["parts"]) and rp["sw"] <= rp["vw"] and abs(rp["scale"] - 1) < 0.001)


# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then goes
# because the code said so.
PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Person, Post, Repost
    from social.accounts import delete_person
    from social.posts import drop_post
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    post_id, person, quote_id = sys.argv[1], sys.argv[2], sys.argv[3]
    row = db.session.execute(sa.select(Post).where(Post.public_id == post_id)).scalar_one()
    pid = row.id
    who = db.session.execute(sa.select(Person).where(Person.handle_key == person)).scalar_one()
    author = db.session.get(Person, row.person_id)
    n = lambda w: db.session.execute(sa.select(sa.func.count()).select_from(Repost).where(w)).scalar()
    out = {"fk": fk}
    before = n(Repost.post_id == pid)
    drop_post(author.public_id, row)
    db.session.commit()
    q = db.session.execute(sa.select(Post.is_quote, Post.quoted_post_id).where(Post.public_id == quote_id)).one()
    out["post"] = [before, n(Repost.post_id == pid)]
    out["quote"] = [bool(q[0]), q[1]]
    made, owned = n(Repost.person_id == who.id), n(Repost.owner_id == who.id)
    delete_person(db.session, who.id)
    db.session.commit()
    out["person"] = [made, owned, n(Repost.person_id == who.id), n(Repost.owner_id == who.id)]
    print(json.dumps(out))
"""

# The reads as the code sends them, planned by SQLite; and how many reads of
# the reposts a page of Home's cards makes (cookies: a signed-in viewer's).
READS = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Person, Post
    from social import activity as A, reposts as R
    me = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    posts = [r[0] for r in db.session.execute(sa.select(Post.id).limit(20)).all()]
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        for name, call in (("stats", lambda: R.stats(me, posts=posts, drawings=["nothing"])),
                           ("their posts tab", lambda: R.reposts_before(None, 20, me, person=me)),
                           ("activity reposts", lambda: A._reposts(me, frozenset(), None)),
                           ("activity quotes", lambda: A._quotes(me, frozenset()))):
            rec.clear()
            call()
            calls[name] = list(rec)
    event.remove(db.engine, "before_cursor_execute", keep)
    conn = db.session.connection()
    plans = {name: [r[3] for st, params in sent for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
             for name, sent in calls.items()}
    seen = []
    def count(conn, cursor, statement, *a):
        if "social_reposts" in statement or "GROUP BY social_posts.quoted_" in statement:
            seen.append(" ".join(statement.split())[:90])
    event.listen(db.engine, "before_cursor_execute", count)
    page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": sys.argv[2], "X-Forwarded-For": "10.250.1.3"})
    event.remove(db.engine, "before_cursor_execute", count)
    print(json.dumps({"plans": plans, "sent": {k: len(v) for k, v in calls.items()}, "reads": seen,
                      "cards": page.get_data(as_text=True).count('class="post-card"')}))
"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the row: comment · repost · heart · ⋯ · Open ›, Share in the ⋯; the repost's count, lit once yours;"
               " three counts in the hundreds on a phone"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            p1 = make_post(pia, "Section 1, Pia's")
            d1 = make_drawing(pia, "Section 1, Pia's drawing", seed=11)
            z1 = make_post(pia, "Section 1, Pia's, nobody's repost")
            st, ans = repost(kai, p1)
            seen = {}
            for screen in ("phone", "desk"):
                for who in (kai, pia):
                    ctx, pg = browser_as(b, who, screen=screen)
                    go(pg, "/social/", wait=500)
                    to(pg, card(p1) + " .post-row", 300)
                    seen[(screen, who.handle, "card")] = pg.evaluate(ROW, card(p1))
                    to(pg, card(z1) + " .post-row", 300)
                    seen[(screen, who.handle, "zero")] = pg.evaluate(ROW, card(z1))
                    go(pg, f"/social/p/{p1}")
                    seen[(screen, who.handle, "page")] = pg.evaluate(ROW, ".post-page")
                    go(pg, f"/social/b/{d1}")
                    seen[(screen, who.handle, "drawing")] = pg.evaluate(ROW, ".post-page")
                    close_ctx(ctx, pg)
            kids = {" ".join(k): (v or {}).get("kids") for k, v in seen.items()}
            check("the row: comment · repost · heart · ⋯ · Open › on Home's card; a post's page and a drawing's the"
                  " same without Open ›; Share gone from it, and Share… and Copy link in the ⋯ (phone and desk, Kai"
                  " and Pia)",
                  len(seen) == 16 and all(v and v["kids"] == (["comment", "repost", "heart", "more", "open"]
                                                              if k[2] in ("card", "zero") else ["comment", "repost", "heart", "more"])
                                          and {"share", "copy"} <= set(v["menu"]) for k, v in seen.items()),
                  json.dumps(kids)[:700])
            looks = []
            for k, v in seen.items():
                r = (v or {}).get("rp") or {}
                if not (r.get("h") == 44 and r.get("w", 0) >= 44 and r.get("icon") == 20 and r.get("iconLeft") == 10
                        and r.get("d") == ARROWS and r.get("popup") == "dialog" and r.get("controls") == "repostSheet"
                        and r.get("hit")):
                    looks.append((" ".join(k), {x: r.get(x) for x in ("h", "w", "icon", "iconLeft", "popup", "controls", "hit")}))
            check("the repost 44px to a finger, the mock's two arrows (its four lines) at 20px, 10px in, as the heart"
                  " and the comments sit; it raises the repost sheet (aria-haspopup dialog, #repostSheet) and is"
                  " painted where it stands", st == 200 and not looks, json.dumps(looks)[:600])
            counts = {" ".join(k): [(v or {}).get("rp", {}).get(x) for x in ("n", "on", "label")] for k, v in seen.items()}
            ok_n = all(v and v["rp"] and v["rp"]["n"] == "1" and v["rp"]["size"] == "15px"
                       for k, v in seen.items() if k[2] in ("card", "page"))
            ok_zero = all(v and v["rp"] and v["rp"]["n"] is None and v["rp"]["label"] == "Repost" and not v["rp"]["on"]
                          for k, v in seen.items() if k[2] in ("zero", "drawing"))
            check("how many reposts and quotes beside the arrows, 15px, for everybody (1, Kai's); none at zero, its name"
                  " \"Repost\" alone (a post nobody reposted; a drawing nobody quoted)", ok_n and ok_zero,
                  json.dumps(counts)[:700])
            lit = all(v["rp"]["on"] and v["rp"]["color"] == v["accent"] == v["rp"]["icColor"] == v["rp"]["nColor"]
                      and v["rp"]["label"] == "Reposted, 1 repost"
                      for k, v in seen.items() if k[1] == "kai" and k[2] in ("card", "page"))
            unlit = all(not v["rp"]["on"] and v["rp"]["color"] == v["ink2"] == v["rp"]["icColor"] == v["rp"]["nColor"]
                        and v["rp"]["label"] == "Repost, 1 repost"
                        for k, v in seen.items() if k[1] == "pia" and k[2] in ("card", "page"))
            check("lit once the repost is yours: the arrows and the count in the small violet ink (--accent-ink),"
                  " \"Reposted, 1 repost\"; anybody else's in the row's ink (--ink-2), \"Repost, 1 repost\"",
                  lit and unlit, json.dumps({" ".join(k): [seen[k]["rp"]["color"], seen[k]["accent"], seen[k]["ink2"]]
                                             for k in seen if k[2] == "card" and seen[k] and seen[k]["rp"]})[:600])
            # THREE COUNTS IN THE HUNDREDS on a 402px touch phone, read off the paint.
            h1 = make_post(pia, "Section 1, a busy one")
            pile_on(h1, 120, 130, 140)
            fit, wide = {}, {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, kai, screen="phone", scheme=scheme)
                go(pg, "/social/", wait=500)
                to(pg, card(h1) + " .post-row", 300)
                faces = ["the page's own"] + pg.evaluate("""(faces) => faces.filter((f) => { const x = document.createElement('canvas').getContext('2d'), t = '120 130 140 Open';
                  x.font = '15px monospace'; const a = x.measureText(t).width; x.font = '15px "' + f + '", monospace'; return Math.abs(x.measureText(t).width - a) > 0.5; })""", FACES)
                # THE PAGE'S OWN FACE IS DEJAVU SANS where the system's face is
                # (CI's Linux): it is read by the face drawn, not by its name.
                own_wide = pg.evaluate("""() => { const x = document.createElement('canvas').getContext('2d'), t = '120 130 140 Open';
                  x.font = '15px ' + getComputedStyle(document.querySelector('.post-row')).fontFamily; const a = x.measureText(t).width;
                  x.font = '15px "DejaVu Sans"'; return Math.abs(x.measureText(t).width - a) < 0.5; }""")
                for f in faces:
                    pg.evaluate(FACE, None if f == "the page's own" else f)
                    pg.wait_for_timeout(250)
                    fit[(scheme, f)] = row_paint(pg, card(h1))
                    wide[(scheme, f)] = f == "DejaVu Sans" or (f == "the page's own" and own_wide)
                pg.evaluate(FACE, None)
                close_ctx(ctx, pg)
            check("three counts in the hundreds (120 comments, 140 reposts, 130 hearts) fit a 402px touch phone, read off"
                  " the paint, light and dark, in the page's own face and in DejaVu Sans, Inter, Liberation Sans and"
                  " FreeSans where the box has them: every part's ink inside the card (in its own box, but in DejaVu"
                  " Sans, the page's own face too where it is drawn in that), 8px or more of ground between two parts'"
                  " ink, Open › whole, every part 44px, nothing past the screen",
                  len(fit) >= 4 and all(fits(v, own_box=not wide[k]) for k, v in fit.items())
                  and all([q["n"] for q in v["parts"][:3]] == ["120", "140", "130"] for v in fit.values() if v),
                  json.dumps({" ".join(k): v and {"wide": wide[k], "gaps": [round(bb["ink"][0] - a["ink"][1], 1) for a, bb in zip(v["parts"], v["parts"][1:])
                                                          if a["ink"] and bb["ink"]],
                                                 "open": v["parts"][-1]["ink"], "card": v["card"], "stray": v["stray"],
                                                 "w": [q["w"] for q in v["parts"]]} for k, v in fit.items()})[:900])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "the sheet: Repost and Quote; Undo repost once yours; a drawing's, Quote alone; signed out; it glides"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            p2 = make_post(pia, "Section 2, Pia's")
            d2 = make_drawing(pia, "Section 2, Pia's drawing", seed=21)
            sheets, pens = {}, {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, kai, screen=screen, scheme="dark" if screen == "desk" else "light")
                go(pg, "/social/", wait=500)
                pens[screen] = pg.evaluate(PEN)
                to(pg, card(p2), 140)
                open_rp(pg, card(p2) + " .rp-btn")
                sheets[(screen, "a post")] = pg.evaluate(SHEET)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(500)
                repost(kai, p2)
                go(pg, "/social/", wait=500)
                to(pg, card(p2), 140)
                open_rp(pg, card(p2) + " .rp-btn")
                sheets[(screen, "yours")] = pg.evaluate(SHEET)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(500)
                repost(kai, p2, on=False)
                go(pg, f"/social/b/{d2}")
                open_rp(pg, PAGE_ROW + " .rp-btn")
                sheets[(screen, "a drawing")] = pg.evaluate(SHEET)
                close_ctx(ctx, pg)
            names = {" ".join(k): [(r["name"], r["say"]) for r in (v or {}).get("rows", [])] for k, v in sheets.items()}
            want = {"a post": [("Repost", "Show it to the people who follow you"),
                               ("Quote", "Repost it with your own words, or a drawing")],
                    "yours": [("Undo repost", "Take it off your page and your followers’ Home"),
                              ("Quote", "Repost it with your own words, or a drawing")],
                    "a drawing": [("Quote", "Repost it with your own words, or a drawing")]}
            check("a tap raises the repost sheet, \"Repost\", one card: Repost (\"Show it to the people who follow"
                  " you\") and Quote (\"Repost it with your own words, or a drawing\"); once yours, Undo repost (\"Take"
                  " it off your page and your followers’ Home\"); a drawing shown outside a post, Quote alone; the ⋯'s"
                  " own sheet staying down (phone and desk)",
                  len(sheets) == 6 and all(v and v["open"] and v["title"] == "Repost" and v["cards"] == 1 and v["menuDown"]
                                           and [(r["name"], r["say"]) for r in v["rows"]] == want[k[1]]
                                           for k, v in sheets.items()),
                  json.dumps(names)[:700])
            looks = []
            for k, v in sheets.items():
                for r in (v or {}).get("rows", []):
                    icon = ARROWS if r["act"] == "repost" else pens[k[0]]
                    if not (r["d"] == icon and r["nameSize"] == "17px" and r["nameWeight"] == "600" and r["nameColor"] == v["ink"]
                            and r["saySize"] == "15px" and r["sayColor"] == v["ink2"] and r["h"] >= 56 and r["hit"]):
                        looks.append((" ".join(k), r["act"], {x: r[x] for x in ("nameSize", "nameWeight", "saySize", "h", "hit")}))
            check("each row the ⋯'s own with the mute row's two lines: its name 17px 600 in the ink, what it does 15px in"
                  " the second ink, 56px or more, painted where it stands; Repost's icon the arrows, Quote's the bar's"
                  " Make pencil", pens.get("phone") and not looks, json.dumps(looks)[:600])
            # SIGNED OUT: the small sheet that says how; nothing is done.
            out = {}
            ctx, pg = browser_as(b, None)
            go(pg, f"/social/p/{p2}")
            out["door"] = pg.evaluate("() => { const b = document.querySelector('.post-page > .post-row .rp-btn');"
                                      " return b ? [b.hasAttribute('data-repost-out'), b.getAttribute('aria-controls')] : null; }")
            press(pg, PAGE_ROW + " .rp-btn")
            pg.wait_for_timeout(700)
            out["sheet"] = pg.evaluate("""() => { const s = document.getElementById('repostOutSheet'); if (!s) return null;
              const a = s.querySelector('a.btn'); return { open: s.classList.contains('is-open') && !s.hidden,
              title: s.querySelector('h2').textContent, lede: s.querySelector('.post-lede').textContent,
              acts: [...s.querySelectorAll('.post-sheet-acts > *')].map(e => e.textContent.trim()),
              next: a ? new URL(a.href).searchParams.get('next') : null,
              focus: document.activeElement ? document.activeElement.textContent.trim() : null }; }""")
            close_ctx(ctx, pg)
            check("signed out, the repost raises \"Repost this post?\" (\"Sign in to show it to the people who follow"
                  " you, or quote it with your own words.\"), Not now | Sign in, Sign in coming back to the page, Not"
                  " now in focus; nothing reposted",
                  out["door"] == [True, "repostOutSheet"] and (out["sheet"] or {}).get("open")
                  and out["sheet"]["title"] == "Repost this post?"
                  and out["sheet"]["lede"] == "Sign in to show it to the people who follow you, or quote it with your own words."
                  and out["sheet"]["acts"] == ["Not now", "Sign in"] and out["sheet"]["next"] == f"/social/p/{p2}"
                  and out["sheet"]["focus"] == "Not now" and reposts_of(p2) == [],
                  json.dumps(out))
            # IT GLIDES, read on every frame: up from below the screen (a phone),
            # never a jump; under Reduce Motion it fades where it sits.
            glides = {}
            for reduced in (False, True):
                ctx, pg = browser_as(b, kai, reduced=reduced)
                go(pg, "/social/", wait=500)
                to(pg, card(p2), 140)
                pg.evaluate("""() => { window.__sf = []; const s = document.querySelector('#repostSheet .make-sheet'), t0 = performance.now();
                  const step = () => { const r = s.getBoundingClientRect(), w = document.getElementById('repostSheet');
                    window.__sf.push({ t: performance.now() - t0, top: r.top, o: +getComputedStyle(s).opacity, shown: !w.hidden });
                    if (performance.now() - t0 < 900) requestAnimationFrame(step); }; requestAnimationFrame(step); }""")
                press(pg, card(p2) + " .rp-btn")
                pg.wait_for_timeout(1000)
                fr = [f for f in pg.evaluate("() => window.__sf") if f["shown"]]
                tops = [f["top"] for f in fr]
                glides[reduced] = {"n": len(fr), "first": round(tops[0], 1) if tops else None, "last": round(tops[-1], 1) if tops else None,
                                   "jump": round(max((a - b_ for a, b_ in zip(tops, tops[1:])), default=0), 1),
                                   "up": all(b_ <= a + 0.5 for a, b_ in zip(tops, tops[1:])),
                                   "moved": round((tops[0] - tops[-1]) if tops else 0, 1)}
                close_ctx(ctx, pg)
            g0, g1 = glides[False], glides[True]
            check("it rises gliding, read on every frame: from below to where it rests, only ever up, no frame more than"
                  " a fifth of the way at once; under Reduce Motion it does not move (it fades where it sits)",
                  g0["n"] >= 8 and g0["up"] and g0["moved"] > 100 and g0["jump"] <= g0["moved"] / 5
                  and g1["n"] >= 2 and abs(g1["moved"]) < 1, json.dumps(glides))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "a tap reposts: lit and counted at once, the count's glide on every frame; Undo repost; quick taps"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            p3 = make_post(pia, "Section 3, Pia's")
            FRAMES = r"""(sel) => { window.__rf = []; const c = document.querySelector(sel), t0 = performance.now();
              const step = () => { const b = c.querySelector('.rp-btn'), h = c.querySelector('.lk-heart'), n = b.querySelector('.rp-n');
                window.__rf.push({ t: performance.now() - t0, w: b.getBoundingClientRect().width, heart: h.getBoundingClientRect().left,
                                   o: n ? +getComputedStyle(n).opacity : null, on: b.classList.contains('is-on') });
                if (performance.now() - t0 < 900) requestAnimationFrame(step); }; requestAnimationFrame(step); }"""
            STATE = r"""(sel) => { const b = document.querySelector(sel + ' .rp-btn'), n = b && b.querySelector('.rp-n');
              const t = document.querySelector('.mu-toast');
              return { on: !!b && b.classList.contains('is-on'), n: n ? n.textContent.trim() : null, label: b && b.getAttribute('aria-label'),
                       sheet: document.getElementById('repostSheet').classList.contains('is-open'),
                       focus: document.activeElement === b, toast: !!t && !t.hidden && t.classList.contains('is-up') }; }"""
            ctx, pg = browser_as(b, kai)
            go(pg, "/social/", wait=500)
            to(pg, card(p3), 160)
            held = []
            pg.route("**/repost", lambda r: held.append(r))
            open_rp(pg, card(p3) + " .rp-btn")
            pg.evaluate(FRAMES, card(p3))
            press(pg, '#repostSheet [data-rp="repost"]')
            pg.wait_for_timeout(500)
            early = pg.evaluate(STATE, card(p3))
            frames = pg.evaluate("() => window.__rf")
            early["asked"], early["db"] = len(held), reposts_of(p3)
            for r in held:
                r.continue_()
            pg.unroute("**/repost")
            pg.wait_for_timeout(900)
            after = pg.evaluate(STATE, card(p3))
            after["db"] = reposts_of(p3)
            check("Repost: the sheet goes down and the focus back on the repost; it lights and says 1 at once, before"
                  " the site has answered; then the site keeps it (one repost, Kai's), and no toast",
                  early["on"] and early["n"] == "1" and not early["sheet"] and early["focus"] and early["asked"] == 1
                  and early["db"] == [] and after["on"] and after["n"] == "1" and after["label"] == "Reposted, 1 repost"
                  and after["db"] == ["kai"] and not after["toast"], json.dumps([early, after]))
            ws = [f["w"] for f in frames]
            hs = [f["heart"] for f in frames]
            os_ = [f["o"] for f in frames if f["o"] is not None]
            grew = ws[-1] - ws[0] if ws else 0
            steps = [b_ - a for a, b_ in zip(ws, ws[1:]) if abs(b_ - a) > 0.01]
            hop = max((abs(b_ - a) for a, b_ in zip(hs, hs[1:])), default=0)
            check("KIND, NEVER JUMPY, read on every frame: the count fades in (from under half) as the button grows"
                  " round the arrows over several frames, only ever wider, the heart moving along with it, never more"
                  " than a third of the way in one frame",
                  grew > 4 and len(steps) >= 4 and all(s_ > 0 for s_ in steps) and hop <= grew / 3 and os_ and os_[0] < 0.5
                  and os_[-1] == 1, json.dumps({"grew": round(grew, 1), "steps": len(steps), "hop": round(hop, 1),
                                                "o": [round(x, 2) for x in os_[:3]] + [os_[-1] if os_ else None]}))
            go(pg, "/social/", wait=500)
            again = pg.evaluate(STATE, card(p3))
            to(pg, card(p3), 160)
            open_rp(pg, card(p3) + " .rp-btn")
            pg.evaluate(FRAMES, card(p3))
            press_rp_row(pg, "repost", after=1000)
            undone = pg.evaluate(STATE, card(p3))
            fr2 = pg.evaluate("() => window.__rf")
            undone["db"] = reposts_of(p3)
            w2 = [f["w"] for f in fr2]
            check("after a reload still lit and 1; Undo repost puts it back: unlit, its count fading and the button"
                  " closing round the arrows, nobody's repost left",
                  again["on"] and again["n"] == "1" and not undone["on"] and undone["n"] is None
                  and undone["label"] == "Repost" and undone["db"] == [] and w2 and w2[0] - w2[-1] > 4,
                  json.dumps([again, undone, round(w2[0] - w2[-1], 1) if w2 else None]))
            # TAPS WHILE ONE IS ASKED end where the last says.
            held = []
            pg.route("**/repost", lambda r: held.append(r))
            open_rp(pg, card(p3) + " .rp-btn")
            press(pg, '#repostSheet [data-rp="repost"]')
            pg.wait_for_timeout(450)
            open_rp(pg, card(p3) + " .rp-btn")
            mid_words = pg.evaluate("() => document.querySelector('#repostSheet [data-rp-name]').textContent")
            press(pg, '#repostSheet [data-rp="repost"]')
            pg.wait_for_timeout(450)
            asked_first = len(held)
            for r in held:
                r.continue_()
            pg.wait_for_timeout(700)
            for r in held[asked_first:]:
                r.continue_()
            pg.wait_for_timeout(700)
            pg.unroute("**/repost")
            pg.wait_for_timeout(600)
            last = pg.evaluate(STATE, card(p3))
            last["db"], last["asked"] = reposts_of(p3), len(held)
            close_ctx(ctx, pg)
            check("a second tap while the first is asked (Undo repost, the sheet saying so at once) is where it ends:"
                  " one request at a time, then the next; unlit, and no repost kept",
                  mid_words == "Undo repost" and asked_first == 1 and not last["on"] and last["n"] is None and last["db"] == [],
                  json.dumps([mid_words, asked_first, last]))
            # UNDER REDUCE MOTION nothing grows: the count fades where it sits.
            ctx, pg = browser_as(b, kai, reduced=True)
            go(pg, "/social/", wait=500)
            to(pg, card(p3), 160)
            open_rp(pg, card(p3) + " .rp-btn")
            pg.evaluate(FRAMES, card(p3))
            press_rp_row(pg, "repost", after=1000)
            fr3 = pg.evaluate("() => window.__rf")
            close_ctx(ctx, pg)
            w3 = [f["w"] for f in fr3]
            moves = [b_ - a for a, b_ in zip(w3, w3[1:]) if abs(b_ - a) > 0.01]
            o3 = [f["o"] for f in fr3 if f["o"] is not None]
            check("under Reduce Motion the button takes its new width at once (one frame), and the count fades in",
                  len(moves) == 1 and o3 and o3[0] < 0.5 and o3[-1] == 1, json.dumps({"moves": moves, "o": o3[:3]}))
            repost(kai, p3, on=False)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "who may repost or quote: signed in, the token, open to them, once; your own undone; the limit"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            ola = someone(b, "ola", "Ola Berg")
            p4 = make_post(pia, "Section 4, Pia's")
            d4 = make_drawing(pia, "Section 4, Pia's drawing", seed=41)
            l4 = make_drawing(pia, "Section 4, Pia's link-only drawing", seed=42, vis="unlisted")
            t4 = make_post(pia, "Section 4, Pia's, taken down")
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (t4,))
            o4 = make_post(ola, "Section 4, Ola's, who blocks Kai")
            block(ola, "kai")
            k4 = make_post(kai, "Section 4, Kai's own")
            got = {"signed out": repost(None, p4), "no token": repost(kai, p4, token=""),
                   "another origin": repost(kai, p4, origin="https://elsewhere.example"),
                   "taken down": repost(kai, t4), "a block (they blocked him)": repost(kai, o4),
                   "not there": repost(kai, "nothing0000"), "not a yes or a no": repost(kai, p4, raw={"reposted": "yes"})}
            want = {"signed out": 401, "no token": 403, "another origin": 403, "taken down": 404,
                    "a block (they blocked him)": 404, "not there": 404, "not a yes or a no": 400}
            check("refused, nothing reposted: signed out 401; no token, another origin 403; a post taken down, a post"
                  " whose maker blocked him, one not there 404; a body not a yes or a no 400",
                  all(got[k][0] == v for k, v in want.items()) and reposts_of(p4) == [] and reposts_of(t4) == []
                  and reposts_of(o4) == [], json.dumps({k: v[0] for k, v in got.items()}))
            r1, r2 = repost(kai, p4), repost(kai, p4)
            own = repost(kai, k4)
            check("one repost a person a post: twice is still one, and the answer says only {ok, reposted, n}; your"
                  " own post too",
                  r1[0] == 200 and r2[0] == 200 and r1[1] == {"ok": True, "reposted": True, "n": 1}
                  and r2[1] == {"ok": True, "reposted": True, "n": 1} and reposts_of(p4) == ["kai"]
                  and own[0] == 200 and reposts_of(k4) == ["kai"], json.dumps([r1, r2, own]))
            # Taken down: nothing new; your own undone whatever became of the post since.
            db_write("update social_people set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where handle_key = 'kai'")
            down_new = repost(kai, make_post(pia, "Section 4, Pia's next"))
            db_write("update social_people set taken_down_at = null where handle_key = 'kai'")
            block(pia, "kai")
            undo_blocked = repost(kai, p4, on=False)
            check("taken down, nothing new (403); your own repost undone even once a block stands between you (200),"
                  " none left", down_new[0] == 403 and undo_blocked[0] == 200 and reposts_of(p4) == [],
                  json.dumps([down_new, undo_blocked]))
            act(pia, "/social/@kai/unblock")
            # QUOTES: what may be quoted is what may be reposted (a drawing too).
            qs = {"a drawing kept link-only": quote(kai, "q", drawing=l4), "a post taken down": quote(kai, "q", post=t4),
                  "a post whose maker blocked him": quote(kai, "q", post=o4), "two at once": quote(kai, "q", post=p4, drawing=d4),
                  "words alone, none": quote(kai, "", post=p4), "not there": quote(kai, "q", post="nothing0000")}
            want_q = {"a drawing kept link-only": 404, "a post taken down": 404, "a post whose maker blocked him": 404,
                      "two at once": 400, "words alone, none": 400, "not there": 404}
            fine = quote(kai, "Kai's words on it", post=p4)
            fine_d = quote(kai, "Kai's words on a drawing", drawing=d4)
            check("a quote of what may not be quoted refused (link-only, taken down, a block, not there 404), of two"
                  " things 400, of nothing with no words 400; of a post and of a drawing shown outside a post, made",
                  all(qs[k][1] == v for k, v in want_q.items()) and fine[0] and fine_d[0]
                  and quote_row(fine[0])[:4] == (1, p4, None, "pia") and quote_row(fine[0])[4] is None
                  and quote_row(fine_d[0])[:4] == (1, None, d4, "pia"),
                  json.dumps({k: v[1:] for k, v in qs.items()}) + f" made {quote_row(fine[0]) if fine[0] else None}")
            # THE LIMIT: 120 an hour, making and undoing alike.
            lia = someone(b, "lia", "Lia Holm")
            c = lia.client()
            c.get(f"/social/p/{p4}")
            codes = [c.post_json(f"/social/p/{p4}/repost", {"reposted": i % 2 == 0})[0] for i in range(125)]
            check("the limit: 120 an hour, making and undoing alike, then refused (429)",
                  429 not in codes[:120] and set(codes[120:]) == {429},
                  f"first 429 at {codes.index(429) if 429 in codes else None}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "Home's Following: a repost inside the original's card, its line; Everyone posts only; once a page;"
               " yours; muted, blocked, taken down; Load more"):
        try:
            juno = someone(b, "juno", "Juno")
            mira = someone(b, "mira", "Mira Lopez")
            theo = someone(b, "theo", "Theo Park")
            vic = someone(b, "vic", "Vic Hale")
            j1 = make_post(juno, "Section 5, Juno's first")
            stamp(j1, 3600)
            follow(vic, "mira")
            repost(mira, j1)
            act(juno, f"/social/p/{j1}/like", {"liked": True})
            LINE = r"""(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'), l = c && c.querySelector(':scope > .rp-by');
              if (!l) return null; const s = getComputedStyle(l), ic = l.querySelector('svg');
              return { color: s.color, size: s.fontSize, weight: s.fontWeight, icon: ic ? Math.round(ic.getBoundingClientRect().width) : null,
                       d: ic ? [...ic.querySelectorAll('path')].map(p => p.getAttribute('d')) : [],
                       ink2: (() => { const e = document.createElement('i'); e.style.color = 'var(--ink-2)'; document.body.append(e); const v = getComputedStyle(e).color; e.remove(); return v; })(),
                       likes: (c.querySelector('.lk-heart .lk-n') || {}).textContent || null }; }"""
            EVERYONE = r"""async () => { const r = await fetch('/social/feed?show=everyone', { credentials: 'same-origin' }); const j = await r.json();
              const box = document.createElement('div'); box.innerHTML = j.html;
              return [...box.querySelectorAll('.post-card')].map(c => [c.getAttribute('data-post'), !!c.querySelector('.rp-by')]); }"""
            ctx, pg = browser_as(b, vic)
            go(pg, "/social/", wait=600)
            feed = pg.evaluate(FEED)
            line = pg.evaluate(LINE, j1)
            every = pg.evaluate(EVERYONE)
            close_ctx(ctx, pg)
            mine = [c for c in feed if c["post"] == j1]
            check("Home's Following for somebody who follows Mira: Juno's post, Juno's own card (her face, her words,"
                  " her hearts: 1), with \"Mira Lopez reposted\" inside it at its top, before its header; once",
                  len(mine) == 1 and mine[0]["who"] == "juno" and mine[0]["by"] == "Mira Lopez reposted"
                  and mine[0]["byFirst"] and mine[0]["byInside"] and (line or {}).get("likes") == "1",
                  json.dumps([mine, line and line.get("likes")]))
            check("the line as the mock has it: the @handle's ink (--ink-2), 14px 600, the arrows 16px",
                  line and line["color"] == line["ink2"] and line["size"] == "14px" and line["weight"] == "600"
                  and line["icon"] == 16 and line["d"] == ARROWS, json.dumps(line))
            check("Everyone shows posts only: Juno's post as her post, no line on any card",
                  [x for x in every if x[0] == j1] == [[j1, False]] and not any(x[1] for x in every), json.dumps(every[:8]))
            # ONCE A PAGE, THE NEWEST; and YOURS.
            wes = someone(b, "wes", "Wes Doyle")
            j2 = make_post(juno, "Section 5, Juno's second")
            t2 = make_post(theo, "Section 5, Theo's")
            stamp(j2, 7200)
            stamp(t2, 5400)
            for h in ("mira", "juno", "theo"):
                follow(wes, h)
            repost(mira, j2)
            stamp_repost(j2, "mira", 1800)
            repost(theo, j2)
            stamp_repost(j2, "theo", 900)
            repost(wes, t2)
            ctx, pg = browser_as(b, wes)
            go(pg, "/social/", wait=600)
            feed = pg.evaluate(FEED)
            close_ctx(ctx, pg)
            js = [c for c in feed if c["post"] == j2]
            ts = [c for c in feed if c["post"] == t2]
            check("the same post twice in one page shows once, the newest: Juno's (Wes follows her) reposted by Mira and"
                  " then Theo is one card, \"Theo Park reposted\"; your own repost of Theo's post one card, \"You"
                  " reposted\"",
                  len(js) == 1 and js[0]["by"] == "Theo Park reposted" and len(ts) == 1 and ts[0]["by"] == "You reposted",
                  json.dumps([js, ts]))
            # NOBODY MUTED, NOTHING A BLOCK HIDES, NOTHING TAKEN DOWN OR DELETED.
            uma = someone(b, "uma", "Uma Reyes")
            nel = someone(b, "nel", "Nel Cho")
            bea = someone(b, "bea", "Bea Ng")
            follow(uma, "mira")
            follow(uma, "theo")
            m3 = make_post(juno, "Section 5, Juno's, reposted by Mira, whom Uma mutes")
            n3 = make_post(nel, "Section 5, Nel's, whom Uma mutes, reposted by Theo")
            b3 = make_post(bea, "Section 5, Bea's, who blocks Uma, reposted by Theo")
            k3 = make_post(juno, "Section 5, Juno's, taken down, reposted by Theo")
            g3 = make_post(juno, "Section 5, Juno's, deleted, reposted by Theo")
            o3 = make_post(juno, "Section 5, Juno's, reposted by Theo, the one that shows")
            for pid in (m3, n3, b3, k3, g3, o3):
                stamp(pid, 4000)
            repost(mira, m3)
            for pid in (n3, b3, k3, g3, o3):
                repost(theo, pid)
            mute(uma, "mira")
            mute(uma, "nel")
            block(bea, "uma")
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (k3,))
            c = juno.client()
            c.get(f"/social/p/{g3}")
            c.post_json(f"/social/p/{g3}/delete", {})
            PARTS = r"""() => { let part = 'following';
              return [...document.querySelector('[data-feed]').children].map(c => {
                if (c.classList.contains('fo-caught')) { part = 'fresh'; return null; }
                if (!c.classList.contains('post-card')) return null;
                const by = c.querySelector(':scope > .rp-by'); return [c.getAttribute('data-post'), by ? by.textContent.trim() : null, part]; })
                .filter(Boolean); }"""
            ctx, pg = browser_as(b, uma)
            go(pg, "/social/", wait=600)
            feed = pg.evaluate(PARTS)
            close_ctx(ctx, pg)
            ids = [c[0] for c in feed]
            check("not on Home: a repost by somebody you muted (Juno's post only as her own, in Fresh from everyone, no"
                  " line), a repost of a muted person's post, of a post whose maker blocked you, of a post taken down or"
                  " deleted; the rest as ever (Theo's repost of Juno's, in the people you follow)",
                  not ({n3, b3, k3, g3} & set(ids)) and all(c[1] is None and c[2] == "fresh" for c in feed if c[0] == m3)
                  and [c[1:] for c in feed if c[0] == o3] == [["Theo Park reposted", "following"]], json.dumps(feed[:14]))
            # LOAD MORE: posts and reposts under one cursor, none twice, none missed,
            # and two reposts at the very same moment across the page's end (Home's
            # order at one moment: a repost's place by its post's address).
            from datetime import datetime, timedelta, timezone
            lou = someone(b, "lou", "Lou Park")
            max_ = someone(b, "max", "Max Ruiz")
            follow(lou, "max")
            now_ = datetime.now(timezone.utc)

            def at_(k):
                return (now_ - timedelta(seconds=100000 + k * 600)).strftime("%Y-%m-%d %H:%M:%S.%f")
            seq = []
            for k in range(1, 27):
                if k in (20, 21) or (k < 20 and k % 2 == 0):
                    pj = make_post(juno, f"Section 5, Juno's {k}, for Max to repost")
                    db_write("update social_posts set created_at = ? where public_id = ?", (at_(300 + k), pj))
                    repost(max_, pj)
                    seq.append(["r", pj, at_(20) if k in (20, 21) else at_(k)])
                    db_write("update social_reposts set created_at = ? where post_id = (select id from social_posts where"
                             " public_id = ?) and person_id = (select id from social_people where handle_key = 'max')",
                             (seq[-1][2], pj))
                else:
                    pm = make_post(max_, f"Section 5, Max's {k}")
                    seq.append(["p", pm, at_(k)])
                    db_write("update social_posts set created_at = ? where public_id = ?", (at_(k), pm))
            tie = sorted([x[1] for x in seq[19:21]], reverse=True)
            want_order = [x[1] for x in seq[:19]] + tie + [x[1] for x in seq[21:]]
            shared = [x[1] for x in seq if x[0] == "r"]
            PAGES = r"""async () => { const out = []; let next = null, n = 0;
              const read = (html) => { const box = document.createElement('div'); box.innerHTML = html;
                return [...box.children].map(c => c.classList.contains('post-card') ? [c.getAttribute('data-post'),
                  (c.querySelector(':scope > .rp-by') || {}).textContent || null] : ['~' + (c.className || c.tagName)]); };
              out.push(read(document.querySelector('[data-feed]').innerHTML));
              next = document.querySelector('[data-feed-next]').getAttribute('data-feed-next');
              while (next && n++ < 6) { const r = await fetch('/social/feed?before=' + encodeURIComponent(next), { credentials: 'same-origin' });
                const j = await r.json(); out.push(read(j.html)); next = j.next; }
              return out; }"""
            ctx, pg = browser_as(b, lou)
            go(pg, "/social/", wait=600)
            pages = pg.evaluate(PAGES)
            close_ctx(ctx, pg)
            flat = [x for pg_ in pages for x in pg_]
            cut = next((i for i, x in enumerate(flat) if x[0] == "~fo-caught"), len(flat))
            follow_part = [x for x in flat[:cut] if not x[0].startswith("~")]
            ids_f = [x[0] for x in follow_part]
            first = [x for x in pages[0] if not x[0].startswith("~")] if pages else []
            check("Load more: Lou's Following, Max's fifteen posts and eleven reposts, newest first under one cursor, a page"
                  " of twenty then the rest, none twice and none missed, each repost with its line; two reposts at the"
                  " very same moment across the page's end, one each side",
                  len(pages) >= 2 and ids_f == want_order and len(first) == 20 and first[-1][0] == tie[0]
                  and all((x[1] or "").strip() == ("Max Ruiz reposted" if x[0] in shared else "") for x in follow_part),
                  json.dumps({"pages": [len(x) for x in pages], "tie": [t_[:4] for t_ in tie],
                              "got": [x[0][:4] for x in follow_part], "want": [w[:4] for w in want_order]})[:900])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "a Posts tab: posts and reposts merged, newest first, the line; yours \"You reposted\"; Load more"):
        try:
            juno = someone(b, "juno", "Juno")
            zoe = someone(b, "zoe", "Zoe Quinn")
            vic = someone(b, "vic", "Vic Hale")
            bea = someone(b, "bea", "Bea Ng")
            own, shared = [], []
            for i in range(14):
                pz = make_post(zoe, f"Section 6, Zoe's {i}")
                stamp(pz, 50000 + i * 600)
                own.append(pz)
            for i in range(10):
                pj = make_post(juno, f"Section 6, Juno's {i}, for Zoe to repost")
                stamp(pj, 90000)
                repost(zoe, pj)
                stamp_repost(pj, "zoe", 50000 + i * 1200 + 300)
                shared.append(pj)
            hid_b = make_post(bea, "Section 6, Bea's, who blocks Vic")
            hid_t = make_post(juno, "Section 6, Juno's, taken down")
            repost(zoe, hid_b)
            repost(zoe, hid_t)
            block(bea, "vic")
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (hid_t,))
            TAB = r"""async (handle) => { const read = (root) => [...root.querySelectorAll('.post-card')].map(c => {
                const by = c.querySelector(':scope > .rp-by'); return [c.getAttribute('data-post'), by ? by.textContent.trim() : null]; });
              const out = [read(document.querySelector('[data-prof-list]'))];
              let next = document.querySelector('[data-prof-next]').getAttribute('data-prof-next'), n = 0;
              while (next && n++ < 6) { const r = await fetch('/social/@' + handle + '/more?tab=posts&before=' + encodeURIComponent(next), { credentials: 'same-origin' });
                const j = await r.json(); const box = document.createElement('div'); box.innerHTML = j.html; out.push(read(box)); next = j.next; }
              return out; }"""
            seen = {}
            for who in (vic, zoe):
                ctx, pg = browser_as(b, who)
                go(pg, "/social/@zoe", wait=600)
                seen[who.handle] = pg.evaluate(TAB, "zoe")
                close_ctx(ctx, pg)
            times = sorted([(50000 + i * 600, pid) for i, pid in enumerate(own)]
                           + [(50000 + i * 1200 + 300, pid) for i, pid in enumerate(shared)])
            want = [pid for _, pid in times]
            ok = {}
            for h, pages in seen.items():
                flat = [x for pg_ in pages for x in pg_]
                line = "You reposted" if h == "zoe" else "Zoe Quinn reposted"
                # Bea blocked Vic, not Zoe: her own page shows her newest repost, of Bea's post.
                want_h = ([hid_b] if h == "zoe" else []) + want
                ok[h] = (len(pages) >= 2 and [x[0] for x in flat] == want_h
                         and all(x[1] == (line if x[0] in shared + [hid_b] else None) for x in flat))
            check("Zoe's Posts tab, to Vic and to herself: her fourteen posts and ten reposts merged, newest first, over"
                  " two pages with Load more, none twice and none missed; each repost with its line (\"Zoe Quinn"
                  " reposted\" to Vic, \"You reposted\" to her); a repost of a post taken down, or of a post whose maker"
                  " blocked the one looking, not there",
                  all(ok.values()) and len(ok) == 2,
                  json.dumps({h: [[x[0][:4], x[1]] for pg_ in v for x in pg_][:30] for h, v in seen.items()})[:800])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "quote posts: the original small inside, painted, one link; with a drawing; a drawing's; gone; the count"):
        try:
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            kai = someone(b, "kai", "Kai Moss")
            ivy = someone(b, "ivy", "Ivy Moss")
            j7 = make_post(juno, "My first one here!", payload=with_poster(drawing(seed=70)))
            q7, st, _ = quote(rook, "The way the tree leans into the hill. Look at this one.", post=j7)
            long7 = make_post(juno, "A long one. " + "The hill goes on and on and the tree keeps leaning into it. " * 6)
            ql, _, _ = quote(rook, "Too long to read in full", post=long7)
            qd, _, _ = quote(rook, "With a drawing of my own", post=j7, payload=drawing(seed=71))
            d7 = make_drawing(juno, "Section 7, Juno's drawing", seed=72)
            qs, _, _ = quote(rook, "Quoting a drawing", drawing=d7)
            SMALL = r"""(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"], .post-page[data-post="' + post + '"]');
              if (!c) return null; const q = c.querySelector(':scope > .qt-card'); if (!q) return { none: true };
              const img = q.querySelector('.qt-pic img'), w = q.querySelector('.qt-words'), dur = q.querySelector('.qt-dur');
              const pr = q.querySelector('.qt-pic') ? q.querySelector('.qt-pic').getBoundingClientRect() : null;
              const art = c.querySelector(':scope > .post-art');
              return { tag: q.tagName, href: q.getAttribute('href'), gone: q.classList.contains('is-gone'), text: q.innerText.replace(/\s+/g, ' ').trim(),
                name: (q.querySelector('.qt-name') || {}).textContent || null, sub: (q.querySelector('.qt-sub') || {}).textContent || null,
                words: w ? w.textContent : null, lines: w ? Math.round(w.getBoundingClientRect().height / parseFloat(getComputedStyle(w).lineHeight) * 10) / 10 : null,
                clamped: w ? w.scrollHeight > w.clientHeight + 1 : null, img: img ? [img.complete, img.naturalWidth] : null,
                pic: pr ? [pr.left, pr.top, pr.width, pr.height] : null, dur: dur ? dur.textContent.trim() : null,
                art: !!art, artBefore: !!art && !!(art.compareDocumentPosition(q) & Node.DOCUMENT_POSITION_FOLLOWING),
                ownWords: (c.querySelector('.post-words') || {}).textContent || null }; }"""
            ctx, pg = browser_as(b, kai)
            go(pg, "/social/", wait=900)
            got = {k: pg.evaluate(SMALL, v) for k, v in (("words", q7), ("long", ql), ("drawing", qd), ("of a drawing", qs))}
            to(pg, card(q7) + " .qt-card", 160)
            pg.wait_for_timeout(600)
            g = got["words"] = pg.evaluate(SMALL, q7)
            painted = None
            if g and g.get("pic"):
                x, y, w_, h_ = g["pic"]
                im = Image.open(io.BytesIO(pg.screenshot(clip={"x": x + 4, "y": y + 4, "width": w_ - 8, "height": h_ * 0.6}))).convert("RGB")
                cols = im.getcolors(maxcolors=100000) or []
                purple = sum(n for n, c in cols if c[2] > c[1] + 60 and c[2] > 150)
                painted = {"colours": len(cols), "purple": purple}
            check("a quote of words alone: Rook's own card (his words, no drawing of his own) with Juno's post small"
                  " inside it, one link to her post: her name and @handle, her words, her drawing as the Gallery's still"
                  " picture painted (its poster loaded, the drawing's own purple on the screen), its ▶ saying \"drawn"
                  " in\"",
                  st == 200 and g and g.get("tag") == "A" and g.get("href") == f"/social/p/{j7}" and g.get("name") == "Juno"
                  and (g.get("sub") or "").startswith("@juno") and g.get("words") == "My first one here!" and not g.get("art")
                  and g.get("img") and g["img"][0] and g["img"][1] > 0 and (g.get("dur") or "").startswith("drawn in ")
                  and g.get("ownWords") == "The way the tree leans into the hill. Look at this one."
                  and painted and painted["colours"] > 20 and painted["purple"] > 30,
                  json.dumps([g, painted])[:700])
            gl = got["long"]
            check("its words two lines at most: a long post's are cut at two", gl and gl.get("lines") is not None
                  and gl["lines"] <= 2.05 and gl.get("clamped"), json.dumps(gl)[:300])
            gd, gs = got["drawing"], got["of a drawing"]
            check("a quote with a drawing of its own: the drawing first, playing in Skribl's player, then the original"
                  " small; a quote of a drawing shown outside a post: small, one link to its own page",
                  gd and gd.get("art") and gd.get("artBefore") and gd.get("href") == f"/social/p/{j7}"
                  and gs and gs.get("href") == f"/social/b/{d7}" and gs.get("img") and gs["img"][1] > 0,
                  json.dumps([gd, gs])[:600])
            # A TAP OPENS THE ORIGINAL.
            landed = None
            if pg.evaluate("(s) => !!document.querySelector(s)", card(q7) + " .qt-card .qt-words"):
                to(pg, card(q7) + " .qt-card", 160)
                with pg.expect_navigation(timeout=8000):
                    press(pg, card(q7) + " .qt-card .qt-words")
                landed = urllib.parse.urlparse(pg.url).path
            close_ctx(ctx, pg)
            check("a tap on the small card opens the original's page (not the quote's)", landed == f"/social/p/{j7}", landed)
            # THE ORIGINAL'S COUNT: reposts and quotes.
            repost(kai, j7)
            ctx, pg = browser_as(b, ivy)
            go(pg, f"/social/p/{j7}")
            n7 = pg.evaluate(ROW, ".post-page")
            close_ctx(ctx, pg)
            check("the original's row counts its reposts and quotes: Kai's repost and Rook's two quotes, 3",
                  n7 and n7["rp"] and n7["rp"]["n"] == "3", json.dumps(n7 and n7["rp"]))
            # GONE: deleted, hidden by a block, taken down.
            j8 = make_post(juno, "Section 7, Juno's, to be deleted")
            q8, _, _ = quote(rook, "Quoting one that goes", post=j8)
            j9 = make_post(ivy, "Section 7, Ivy's, who blocks Kai")
            q9, _, _ = quote(rook, "Quoting Ivy's", post=j9)
            j10 = make_post(juno, "Section 7, Juno's, taken down")
            q10, _, _ = quote(rook, "Quoting one taken down", post=j10)
            c = juno.client()
            c.get(f"/social/p/{j8}")
            c.post_json(f"/social/p/{j8}/delete", {})
            block(ivy, "kai")
            db_write("update social_posts set taken_down_at = strftime('%Y-%m-%d %H:%M:%f000', 'now') where public_id = ?", (j10,))
            gone = {}
            ctx, pg = browser_as(b, kai)
            for k, v in (("deleted", q8), ("a block", q9), ("taken down", q10)):
                go(pg, f"/social/p/{v}")
                gone[k] = pg.evaluate(SMALL, v)
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, rook)
            go(pg, f"/social/p/{q9}")
            gone["a block, to Rook"] = pg.evaluate(SMALL, q9)
            close_ctx(ctx, pg)
            check("a quote outlives what it quotes: deleted, hidden from Kai by a block, or taken down, its small card"
                  " says \"This post is gone.\" and nothing more, no link; to Rook, whom nobody blocked, Ivy's post as"
                  " ever; the quote itself still a quote",
                  all(v and v.get("gone") and v["tag"] == "P" and v["href"] is None and v["text"] == "This post is gone."
                      for k, v in gone.items() if k != "a block, to Rook")
                  and (gone["a block, to Rook"] or {}).get("href") == f"/social/p/{j9}"
                  and quote_row(q8)[:2] == (1, None), json.dumps(gone)[:700])
            # THE QUOTE'S OWN PAGE, on a desk: the original small where a drawing would be.
            ctx, pg = browser_as(b, kai, screen="desk")
            go(pg, f"/social/p/{q7}")
            place = pg.evaluate("""() => { const q = document.querySelector('.post-page > .qt-card'), h = document.querySelector('.post-page > .post-head');
              if (!q || !h) return null; const a = q.getBoundingClientRect(), b = h.getBoundingClientRect();
              return { left: a.left < b.left, beside: a.right <= b.left, top: Math.round(a.top - b.top), auto: document.querySelector('.post-page').hasAttribute('data-autoplay') }; }""")
            close_ctx(ctx, pg)
            check("the quote's own page holds the original small; on a desk, a quote of words alone has it where the"
                  " drawing would be, beside the words, and nothing plays by itself",
                  place and place["left"] and place["beside"] and not place["auto"], json.dumps(place))
            # A QUOTE SHOWS THE DRAWING IT LEADS TO, HOWEVER DEEP (the owner's "all yes"
            # to "Just a Border", Nov 16, A): Theo's quote of Mr. Bloob's quote of Hello
            # showed Mr. Bloob's words alone. Lark and Moth quote quotes; Ivy (who
            # blocked Kai) sits in the middle of one chain.
            lark = someone(b, "lark", "Lark Day")
            moth = someone(b, "moth", "Moth Rey")
            c1, _, _ = quote(lark, "Lark quotes Rook's quote of a drawing", post=qs)
            c2, _, _ = quote(moth, "Moth quotes Lark's", post=c1)
            c3, _, _ = quote(lark, "Lark quotes Rook's quote of Juno's post", post=q7)
            c6, _, _ = quote(ivy, "Ivy quotes Rook's quote of a drawing", post=qs)
            c7, _, _ = quote(lark, "Lark quotes Ivy's", post=c6)
            c8, _, _ = quote(moth, "Moth quotes Lark's quote of Ivy's", post=c7)
            leads = {}
            ctx, pg = browser_as(b, kai)
            for k, v in (("2 deep, a drawing", c1), ("3 deep, a drawing", c2), ("2 deep, a post's drawing", c3),
                         ("through Ivy, to Kai", c8)):
                go(pg, f"/social/p/{v}")
                leads[k] = pg.evaluate(SMALL, v)
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, rook)
            go(pg, f"/social/p/{c8}")
            leads["through Ivy, to Rook"] = pg.evaluate(SMALL, c8)
            close_ctx(ctx, pg)
            pic = lambda g: bool(g and g.get("img") and g["img"][0] and g["img"][1] > 0 and (g.get("dur") or "").startswith("drawn in "))
            check("a quote of a quote shows the drawing it leads to, as a picture, as a quote of a drawing shows it"
                  " (the owner's \"all yes\", Nov 16, A): Lark's quote of Rook's quote of Juno's drawing, Moth's a quote"
                  " further, and Lark's quote of Rook's quote of Juno's post (her post's drawing), each its picture"
                  " painted with \"drawn in\", the small card still the quoted post's, one link to it",
                  pic(leads["2 deep, a drawing"]) and leads["2 deep, a drawing"].get("href") == f"/social/p/{qs}"
                  and pic(leads["3 deep, a drawing"]) and leads["3 deep, a drawing"].get("href") == f"/social/p/{c1}"
                  and pic(leads["2 deep, a post's drawing"]) and leads["2 deep, a post's drawing"].get("href") == f"/social/p/{q7}",
                  json.dumps(leads)[:900])
            check("...and the chain ends at a post its viewer may not see: Moth's quote of Lark's quote of Ivy's shows"
                  " Kai, whom Ivy blocked, Lark's words and no drawing; Rook, whom nobody blocked, the drawing",
                  leads["through Ivy, to Kai"] and not leads["through Ivy, to Kai"].get("img")
                  and leads["through Ivy, to Kai"].get("words") == "Lark quotes Ivy's"
                  and pic(leads["through Ivy, to Rook"]),
                  json.dumps({k: leads[k] for k in ("through Ivy, to Kai", "through Ivy, to Rook")})[:700])
            st_q, raw = moth.client().get(f"/social/p/{qs}/quoted")
            try:
                made = json.loads(raw).get("html") or ""
            except ValueError:
                made = ""
            check("...and Make shows it as the post will: Quote on Rook's quote of a drawing opens Make with the"
                  " drawing in its small card",
                  st_q == 200 and "qt-pic" in made and f"/{d7}/" in made, f"{st_q} {made[:300]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "Activity: reposted your post (to the post), quoted your post (to the quote); Undo takes it; muted; no dot"):
        try:
            ada = someone(b, "ada", "Ada Kim")
            mira = someone(b, "mira", "Mira Lopez")
            rook = someone(b, "rook", "Rook")
            nel = someone(b, "nel", "Nel Cho")
            a8 = make_post(ada, "Section 8, Ada's")
            ctx, pg = browser_as(b, ada)
            go(pg, "/social/activity", wait=400)        # seen: everything before is old now
            close_ctx(ctx, pg)
            repost(mira, a8)
            q8, _, _ = quote(rook, "Rook's words on Ada's", post=a8)
            ROWS = r"""() => [...document.querySelectorAll('.act-row')].map(r => ({ say: r.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim(),
              href: r.getAttribute('href'), peek: (r.querySelector('.act-peek') || {}).textContent || null, isNew: r.classList.contains('is-new'),
              badge: !!r.querySelector('.rp-badge svg'), pic: !!r.querySelector('.act-pic[style*="background-image"]') }))"""
            DOT = "() => { const b = document.querySelector('.top-bell'); return b ? b.getAttribute('aria-label') : null; }"
            ctx, pg = browser_as(b, ada)
            go(pg, "/social/", wait=400)
            dot = pg.evaluate(DOT)
            go(pg, "/social/activity", wait=400)
            rows = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            rp = [r for r in rows if r["say"] == "Mira reposted your post"]
            qt = [r for r in rows if r["say"] == "Rook quoted your post"]
            check("Ada's Activity: \"Mira reposted your post\", new, wearing the arrows, the post's small picture, to her"
                  " post; \"Rook quoted your post\", his words under it in quotes, to his quote",
                  len(rp) == 1 and rp[0]["href"] == f"/social/p/{a8}" and rp[0]["isNew"] and rp[0]["badge"] and rp[0]["pic"]
                  and len(qt) == 1 and qt[0]["href"] == f"/social/p/{q8}" and qt[0]["peek"] == "“Rook’s words on Ada’s”".replace("’", "'")
                  and qt[0]["badge"], json.dumps(rows)[:700])
            check("neither lights the bell's dot (nothing to answer)", dot == "Activity", dot)
            repost(nel, a8)
            ctx, pg = browser_as(b, ada)
            go(pg, "/social/activity", wait=400)
            rows2 = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            repost(mira, a8, on=False)
            mute(ada, "rook")
            ctx, pg = browser_as(b, ada)
            go(pg, "/social/activity", wait=400)
            rows3 = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            says2 = [r["say"] for r in rows2]
            says3 = [r["say"] for r in rows3]
            check("several since she last looked on one post are one row (\"Nel and Mira reposted your post\"); Undo"
                  " repost takes Mira's away (\"Nel reposted your post\"), and Rook, muted, leaves it",
                  any(s_ in ("Nel and Mira reposted your post", "Mira and Nel reposted your post", "Nel reposted your post")
                      for s_ in says2) and "Nel reposted your post" in says3 and not any("Mira" in s_ and "reposted" in s_ for s_ in says3)
                  and not any("Rook" in s_ for s_ in says3), json.dumps([says2, says3]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "deleting, in code: a post (its reposts go, its quotes say it is gone), a drawing, an account; cascade off"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            ola = someone(b, "ola", "Ola Berg")
            p9 = make_post(pia, "Section 9, Pia's")
            repost(kai, p9)
            repost(ola, p9)
            q9, _, _ = quote(kai, "Kai on Pia's", post=p9)
            d9 = make_drawing(pia, "Section 9, Pia's drawing", seed=91)
            qd9, _, _ = quote(ola, "Ola on Pia's drawing", drawing=d9)
            before = (reposts_of(p9), quote_row(q9)[:4], quote_row(qd9)[:4])
            c = pia.client()
            c.get(f"/social/p/{p9}")
            st1 = c.post_json(f"/social/p/{p9}/delete", {})[0]
            c.get(f"/social/b/{d9}")
            st2 = c.post_json(f"/social/b/{d9}/delete", {})[0]
            after = (db("select count(*) from social_reposts r join social_posts s on s.id = r.post_id where s.public_id = ?", (p9,))[0][0],
                     quote_row(q9)[:4], quote_row(qd9)[:4])
            check("deleting a post through its route takes its reposts, and its quotes let go of it (still quotes,"
                  " their small card saying it is gone); a drawing deleted through the site, its quotes the same",
                  st1 == 200 and st2 == 200 and before[0] == ["kai", "ola"] and before[1] == (1, p9, None, "pia")
                  and before[2] == (1, None, d9, "pia") and after == (0, (1, None, None, None), (1, None, None, None)),
                  json.dumps([before, after]))
            # AN ACCOUNT: its reposts, every repost of what it owned, the quotes of what it owned let go.
            gus = someone(b, "gus", "Gus Lee")
            g9 = make_post(gus, "Section 9, Gus's")
            repost(gus, make_post(pia, "Section 9, Pia's, Gus reposts"))
            repost(kai, g9)
            qg, _, _ = quote(kai, "Kai on Gus's", post=g9)
            gid = db("select id from social_people where handle_key = 'gus'")[0][0]
            had = (db("select count(*) from social_reposts where person_id = ? or owner_id = ?", (gid, gid))[0][0],)
            gc = gus.client()
            gc.get("/social/you/delete")
            gst = gc.post_form("/social/you/delete", {"confirm": "gus"})[0]
            left = (db("select count(*) from social_reposts where person_id = ? or owner_id = ?", (gid, gid))[0][0],
                    quote_row(qg)[:4], bool(db("select 1 from social_people where id = ?", (gid,))))
            check("deleting an account takes its reposts and every repost of what it owned, and the quotes of what it"
                  " owned let go of it", had[0] == 2 and left[0] == 0 and left[1] == (1, None, None, None) and not left[2],
                  json.dumps([gst, had, left]))
            # WITH SQLITE'S CASCADE OFF, on a copy: what goes, goes because the code said so.
            hal = someone(b, "hal", "Hal Ruiz")
            h9 = make_post(hal, "Section 9, Hal's, for the copy")
            repost(kai, h9)
            repost(pia, h9)
            qh, _, _ = quote(pia, "Pia on Hal's", post=h9)
            repost(hal, make_post(kai, "Section 9, Kai's, Hal reposts"))
            copy = os.path.join(TMP, "cascade-off.db")
            con = sqlite3.connect(DB)
            con.execute("vacuum into ?", (copy,))
            con.close()
            env = dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0")
            out = subprocess.run([sys.executable, "-c", PROBE, h9, "hal", qh], cwd=ROOT, env=env, capture_output=True,
                                 text=True, timeout=180)
            got = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else {"err": out.stderr[-600:]}
            check("with SQLite's cascade off (a copy): a post's reposts (2, then 0) and its quote let go; an account's"
                  " reposts and every repost of what it owned (1 and 0, then none), each by the code alone",
                  got.get("fk") == 0 and got.get("post") == [2, 0] and got.get("quote") == [True, None]
                  and got.get("person") == [1, 0, 0, 0], json.dumps(got)[:600])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "the data: the chain on a populated database, its CHECKs, one head; the reads on their indexes; asked once"):
        try:
            def alembic(dbfile, *args):
                env = dict(os.environ, DATABASE_URL=f"sqlite:///{dbfile}")
                return subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", *args], cwd=ROOT, env=env,
                                      capture_output=True, text=True, timeout=180)
            heads = subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", "heads"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=60).stdout.split()
            # The reposts' own revision, after the bookmarks', on the chain (the
            # mentions' follows it since Nov 15: the chain is read at the
            # reposts' revision, what it stamps there, never at its head).
            hist = subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", "history", "-r",
                                   "224902330f2a:3e7b508ff939"], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
            chain = os.path.join(TMP, "chain.db")
            want_idx_all = {"ix_social_reposts_person_post", "ix_social_reposts_person_created", "ix_social_reposts_post_id",
                            "ix_social_reposts_owner_created", "ix_social_posts_quoted_post_id",
                            "ix_social_posts_quoted_drawing_id", "ix_social_posts_quoted_owner_created"}
            a1 = alembic(chain, "upgrade", "224902330f2a")
            con = sqlite3.connect(chain)
            con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle, is_admin,"
                        " session_gen, age_confirmed_at, created_at) values (1, 'site:one', 'one', 'one', 'One', x'00', 0, 1,"
                        " '2026-11-01 10:00:00.000000', '2026-11-01 10:00:00.000000')")
            for i in range(3):
                con.execute("insert into social_posts (public_id, person_id, words, skribl_id, created_at) values (?, 1, ?, ?,"
                            " '2026-11-02 10:00:00.000000')", (f"post{i:07d}", f"words {i}", f"sk{i}"))
            con.execute("insert into social_likes (post_id, owner_id, person_id, created_at) values (1, 1, 1, '2026-11-03 10:00:00.000000')")
            con.commit()
            con.close()
            a2 = alembic(chain, "upgrade", "3e7b508ff939")
            con = sqlite3.connect(chain)
            cols = {r[1]: (r[2], r[3]) for r in con.execute("pragma table_info(social_posts)")}
            rows = con.execute("select public_id, skribl_id, is_quote, quoted_post_id, quoted_drawing_id, quoted_owner_id"
                               " from social_posts order by id").fetchall()
            likes = con.execute("select count(*) from social_likes").fetchone()[0]
            idx = {r[0] for r in con.execute("select name from sqlite_master where type='index' and"
                                            " tbl_name in ('social_posts', 'social_reposts')")}
            sql = con.execute("select sql from sqlite_master where name = 'social_posts'").fetchone()[0]
            rcols = [r[1] for r in con.execute("pragma table_info(social_reposts)")]
            stamp_ = con.execute("select version_num from social_alembic_version").fetchall()
            refused = {}
            for name, stmt in (("a post with no drawing that is no quote",
                                "insert into social_posts (public_id, person_id, words, skribl_id, created_at) values"
                                " ('nodrawing00', 1, 'w', null, '2026-11-04')"),
                               ("a quote of a post and a drawing at once",
                                "insert into social_posts (public_id, person_id, words, skribl_id, is_quote, quoted_post_id,"
                                " quoted_drawing_id, created_at) values ('bothquoted0', 1, 'w', null, 1, 1, 'sk9', '2026-11-04')"),
                               ("one repost twice", "insert into social_reposts (person_id, post_id, owner_id, created_at)"
                                " values (1, 1, 1, '2026-11-04'), (1, 1, 1, '2026-11-05')")):
                try:
                    con.execute(stmt)
                    refused[name] = False
                except sqlite3.IntegrityError:
                    refused[name] = True
            con.execute("insert into social_posts (public_id, person_id, words, skribl_id, is_quote, quoted_post_id,"
                        " quoted_owner_id, created_at) values ('wordsquote0', 1, 'just words', null, 1, 1, 1, '2026-11-04')")
            con.commit()
            con.close()
            down_blocked = alembic(chain, "downgrade", "224902330f2a")
            con = sqlite3.connect(chain)
            whole = ({r[0] for r in con.execute("select name from sqlite_master where type='index' and tbl_name"
                                                " in ('social_posts', 'social_reposts')")} >= want_idx_all
                     and not con.execute("select 1 from sqlite_master where name like '_alembic_tmp%'").fetchone())
            con.execute("delete from social_posts where public_id = 'wordsquote0'")
            con.commit()
            con.close()
            a3 = alembic(chain, "downgrade", "224902330f2a")
            con = sqlite3.connect(chain)
            back = {r[1] for r in con.execute("pragma table_info(social_posts)")}
            back_rows = con.execute("select count(*) from social_posts").fetchone()[0]
            gone = not con.execute("select 1 from sqlite_master where name = 'social_reposts'").fetchone()
            con.close()
            want_idx = want_idx_all
            check("the chain on a populated database: one head, the reposts' revision on it (3e7b508ff939, after the"
                  " bookmarks'), read at it; up, every post"
                  " kept as it was (its drawing, none a quote), the table social_reposts (person, post, owner, when)"
                  " with its four indexes, the posts' four columns with their three indexes and both CHECKs, skribl_id"
                  " no longer required; nothing else touched",
                  len(heads) == 2 and heads[1] == "(head)" and "224902330f2a -> 3e7b508ff939" in hist
                  and a1.returncode == 0 and a2.returncode == 0
                  and rows == [(f"post{i:07d}", f"sk{i}", 0, None, None, None) for i in range(3)] and likes == 1
                  and want_idx <= idx and cols.get("skribl_id") == ("VARCHAR(32)", 0) and cols.get("is_quote", ("", 0))[1] == 1
                  and "ck_social_posts_drawn_or_quote" in sql and "ck_social_posts_quotes_one" in sql
                  and rcols == ["id", "person_id", "post_id", "owner_id", "created_at"] and stamp_ == [("3e7b508ff939",)],
                  json.dumps({"heads": heads, "rows": rows, "missing": sorted(want_idx - idx), "cols": {k: cols.get(k) for k in
                              ("skribl_id", "is_quote", "quoted_post_id", "quoted_drawing_id", "quoted_owner_id")}})[:700])
            check("the CHECKs and the pair hold: a post with no drawing that is no quote, a quote of two things at once,"
                  " one repost twice: refused", all(refused.values()) and len(refused) == 3, json.dumps(refused))
            check("back down: refused while a quote of words alone is there, saying so before it changes anything (the"
                  " table whole, nothing half done; nothing deletes a post), then, without it, the columns and the table"
                  " gone and every post kept",
                  down_blocked.returncode != 0 and "quotes of words alone" in down_blocked.stderr and whole
                  and a3.returncode == 0 and gone and back_rows == 3
                  and not ({"is_quote", "quoted_post_id", "quoted_drawing_id", "quoted_owner_id"} & back),
                  f"blocked exit {down_blocked.returncode}; {a3.returncode} {a3.stderr.strip().splitlines()[-1:]}; cols {sorted(back)}")
            # THE READS, on their indexes; and Home's cards asking once.
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            ola = someone(b, "ola", "Ola Berg")
            for i in range(8):
                repost(kai, make_post(ola, f"Section 10, Ola's {i}, Kai reposts"))
            for i in range(22):
                make_post(pia, f"Section 10, Pia's {i}")
            follow(kai, "pia")
            cookie = "; ".join(f"{c_['name']}={c_['value']}" for c_ in kai.ctx.cookies(BASE))
            out = subprocess.run([sys.executable, "-c", READS, "kai", cookie], cwd=ROOT, env=ENV, capture_output=True,
                                 text=True, timeout=180)
            got = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else {"err": out.stderr[-600:]}
            plans = got.get("plans", {})
            on = {"stats": ["ix_social_reposts_post_id", "ix_social_posts_quoted_post_id", "ix_social_posts_quoted_drawing_id"],
                  "their posts tab": ["ix_social_reposts_person_created"],
                  "activity reposts": ["ix_social_reposts_owner_created"],
                  "activity quotes": ["ix_social_posts_quoted_owner_created"]}
            missing = {k: [ix for ix in v if not any(ix in line for line in plans.get(k, []))] for k, v in on.items()}
            check("the reads on their indexes (SQLite's own plan): a page's counts on a post's reposts and its quotes and"
                  " a drawing's, a Posts tab's reposts on the person's own, Activity's on whose",
                  plans and not any(missing.values()), json.dumps({"missing": missing, "plans": plans})[:800])
            reads = got.get("reads", [])
            check("a page of Home's Following (twenty cards) asks for its reposts once: one read of them for the feed,"
                  " one for the counts, one for the quotes' counts, never one a card",
                  got.get("cards", 0) >= 20 and len(reads) <= 3, json.dumps(got.get("reads"))[:500] + f" cards {got.get('cards')}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "contrast and targets: the line and the lit arrows off the paint; every word at 4.5:1; every target 44px"):
        try:
            juno = someone(b, "juno", "Juno")
            mira = someone(b, "mira", "Mira Lopez")
            rook = someone(b, "rook", "Rook")
            cal = someone(b, "cal", "Cal Ito")
            j11 = make_post(juno, "Section 11, Juno's")
            gone11 = make_post(juno, "Section 11, Juno's, to be deleted")
            follow(cal, "mira")
            follow(cal, "rook")
            repost(mira, j11)
            repost(cal, j11)
            q11, _, _ = quote(rook, "Section 11, Rook's quote", post=j11)
            qg11, _, _ = quote(rook, "Section 11, Rook's quote of one gone", post=gone11)
            c = juno.client()
            c.get(f"/social/p/{gone11}")
            c.post_json(f"/social/p/{gone11}/delete", {})
            # Each read where it is painted: the line, and the card's own ground
            # just before its words (between the arrows and them); the lit
            # arrows, and the ground just before the repost's own box.
            BOXES = r"""([post, what]) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'); if (!c) return null;
              const e = what === 'line' ? c.querySelector(':scope > .rp-by span') : c.querySelector('.post-row .rp-btn.is-on svg');
              if (!e) return null; const r = e.getBoundingClientRect();
              const g = what === 'line' ? [r.left - 4, r.top + r.height / 2] : [c.querySelector('.post-row .rp-btn').getBoundingClientRect().left + 3, r.top + r.height / 2];
              return { box: [r.left, r.top, r.width, r.height], ground: g, seen: r.top >= 0 && r.bottom <= innerHeight }; }"""

            def off_paint(pg, box, ground_pt):
                """The most different pixel inside `box` against the card's own
                ground (a point of it), and that ground."""
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
            # A point of the quote's own ground inside its line (6px in, under its
            # corner's curve), what is painted there (the card, nothing over it), the
            # card's colour as the page resolves --card, and the page's ground beside it.
            QT_AT = r"""() => { const q = document.querySelector('.post-page > .qt-card'); if (!q) return null;
              const r = q.getBoundingClientRect(), x = r.left + 24, y = r.top + 6, hit = document.elementFromPoint(x, y);
              return { pt: [x, y], beside: [Math.max(1, r.left - 6), r.top + r.height / 2], hit: hit === q,
                       card: getComputedStyle(document.documentElement).getPropertyValue('--card').trim(),
                       seen: r.top >= 0 && r.top + 12 <= innerHeight }; }"""

            def qt_fill(pg):
                at = pg.evaluate(QT_AT)
                if not at or not at["seen"]:
                    return at
                im = Image.open(io.BytesIO(pg.screenshot(scale="device"))).convert("RGB")
                k = im.width / pg.viewport_size["width"]
                px = im.getpixel((int(at["pt"][0] * k), int(at["pt"][1] * k)))
                gd = im.getpixel((int(at["beside"][0] * k), int(at["beside"][1] * k)))
                h = at["card"].lstrip("#")
                want = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else None
                return {"hit": at["hit"], "painted": px, "card": want, "ground": gd,
                        "on_ground": round(ratio(px, gd), 2)}
            # INSIDE A POST'S CARD, A WELL (the owner's "d2 is good", Nov 16): a point
            # of the quote's own ground inside it (6px in, under its corner's curve),
            # the post card's ground just beside it, the well the page's --page with
            # 6% of Skribl's lilac (#7c5cff), and what could draw a line round it.
            QT_WELL = r"""(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'); if (!c) return null;
              const q = c.querySelector(':scope > .qt-card'); if (!q) return null;
              const r = q.getBoundingClientRect(), cs = getComputedStyle(q), x = r.left + 24, y = r.top + 6;
              return { pt: [x, y], beside: [r.left - 4, r.top + r.height / 2], hit: document.elementFromPoint(x, y) === q,
                       page: getComputedStyle(document.documentElement).getPropertyValue('--page').trim(),
                       shadow: cs.boxShadow, border: cs.borderTopColor,
                       seen: r.top >= 0 && r.top + 12 <= innerHeight && r.left >= 6 }; }"""
            def qt_well(pg, post):
                at = pg.evaluate(QT_WELL, post)
                if not at or not at["seen"]:
                    return at
                im = Image.open(io.BytesIO(pg.screenshot(scale="device"))).convert("RGB")
                k = im.width / pg.viewport_size["width"]
                px = im.getpixel((int(at["pt"][0] * k), int(at["pt"][1] * k)))
                gd = im.getpixel((int(at["beside"][0] * k), int(at["beside"][1] * k)))
                h = at["page"].lstrip("#")
                page = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else None
                want = tuple(round(0.06 * a + 0.94 * p) for a, p in zip((124, 92, 255), page)) if page else None
                return {"hit": at["hit"], "painted": px, "want": want, "card": gd, "on_card": round(ratio(px, gd), 2),
                        "shadow": at["shadow"], "border": at["border"]}
            paints, lows, smalls, reads, fills, wells = {}, [], [], {}, {}, {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen} {scheme}"
                    ctx, pg = browser_as(b, cal, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=700)
                    to(pg, card(j11), 160)
                    pg.wait_for_timeout(300)
                    bx = pg.evaluate(BOXES, [j11, "line"])
                    paints[(tag, "line")] = off_paint(pg, bx and bx["seen"] and bx["box"], bx and bx["ground"])
                    to(pg, card(j11) + " .post-row", 300)
                    pg.wait_for_timeout(300)
                    bx = pg.evaluate(BOXES, [j11, "icon"])
                    paints[(tag, "lit arrows")] = off_paint(pg, bx and bx["seen"] and bx["box"], bx and bx["ground"])
                    got = [("the card with its line", pg.evaluate(READ, card(j11)))]
                    to(pg, card(q11), 160)
                    got.append(("a quote's small card", pg.evaluate(READ, card(q11))))
                    wells[tag] = qt_well(pg, q11)
                    to(pg, card(qg11), 160)
                    got.append(("a gone one's", pg.evaluate(READ, card(qg11))))
                    to(pg, card(j11), 160)
                    open_rp(pg, card(j11) + " .rp-btn")
                    got.append(("the repost sheet", pg.evaluate(READ, "#repostSheet")))
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, None, screen=screen, scheme=scheme)
                    go(pg, f"/social/p/{j11}")
                    press(pg, PAGE_ROW + " .rp-btn")
                    pg.wait_for_timeout(800)
                    got.append(("the signed-out sheet", pg.evaluate(READ, "#repostOutSheet")))
                    # THE QUOTE ON ITS OWN PAGE, a card (the owner's "Yes to B", Nov 15): its
                    # words on it, and the card's colour read off the paint inside its line.
                    go(pg, f"/social/p/{q11}")
                    to(pg, ".post-page > .qt-card", 120)
                    got.append(("a quote on its own page", pg.evaluate(READ, ".post-page > .qt-card")))
                    fills[tag] = qt_fill(pg)
                    close_ctx(ctx, pg)
                    reads[tag] = [(w, r["read"], r["lowest"]) for w, r in got]
                    lows += [f"{tag} {w}: {x}" for w, r in got for x in r["low"]]
                    smalls += [f"{tag} {w}: {x}" for w, r in got for x in r["small"]]
            check("the \"reposted\" line read off the paint, 4.5:1 or more on the card it is painted on, phone and desk,"
                  " light and dark (the @handle's ink: the mock's 7.56 light, 8.59 dark)",
                  all(v and v["best"] >= 4.5 for k, v in paints.items() if k[1] == "line") and len(paints) == 8,
                  json.dumps({" ".join(k): v and v["best"] for k, v in paints.items() if k[1] == "line"}))
            check("the lit arrows read off the paint, 3:1 or more on the card (the small violet ink: the mock's 8.26 light,"
                  " 8.39 dark; the action's purple would be 2.99 on the dark card)",
                  all(v and v["best"] >= 3 for k, v in paints.items() if k[1] == "lit arrows"),
                  json.dumps({" ".join(k): v and v["best"] for k, v in paints.items() if k[1] == "lit arrows"}))
            check("every word at 4.5:1 or more on what is painted behind it, phone and desk, light and dark: a repost's"
                  " card with its line, a quote's small card, a gone one's words, the repost sheet, the signed-out sheet,"
                  " a quote on its own page",
                  len(reads) == 4 and all(n > 0 for v in reads.values() for _, n, _ in v) and not lows,
                  f"low {lows[:4]}; read {json.dumps(reads)[:500]}")
            check("every target 44px or more, on all of them", not smalls, f"small {smalls[:4]}")
            check("a quote on its post's own page is a card: the card's own colour painted inside its line, nothing"
                  " over it, phone and desk, light and dark (on the page's ground, not an outline)",
                  len(fills) == 4 and all(v and v.get("hit") and v.get("card")
                                          and all(abs(a - c) <= 3 for a, c in zip(v["painted"], v["card"]))
                                          for v in fills.values()),
                  json.dumps(fills))
            check("inside a post's card on Home, a quote's small card is a well (the owner's \"d2 is good\", Nov 16):"
                  " the page's ground touched with lilac painted inside it, set apart from the post's card by its"
                  " colour alone (1.08:1 or more against the card's ground beside it: the mock's 1.14 light, 1.12"
                  " dark), and no line round it, phone and desk, light and dark",
                  len(wells) == 4 and all(v and v.get("hit") and v.get("want")
                                          and all(abs(a - c) <= 3 for a, c in zip(v["painted"], v["want"]))
                                          and v["on_card"] >= 1.08 and v["shadow"] == "none"
                                          and v["border"] in ("rgba(0, 0, 0, 0)", "transparent")
                                          for v in wells.values()),
                  json.dumps(wells))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 13
    if part(13, "just a border: no box on the site is set apart from what it sits on by its line alone"):
        try:
            # The owner, Nov 16: "are there any other places where you just have a
            # border around something with the same color as the background that it
            # is sitting in (so there's no way to differentiate it?) like the quote
            # repost?" A census of every box with something in it (words or a
            # picture) and a line round it (a ring, or a border on two sides or
            # more): its fill against the ground that shows round it (past any
            # wrapper its own size) must differ by 1.08:1 or more. Not counted: a box
            # with a soft lift (its shadow sets it apart), one on a drawing or a
            # picture (its ground is what the picture paints), a picture's own box
            # (the picture four fifths of it or more; and a drawing's plate,
            # .gal-pic, whose ground is the drawing's own paper by plate_ground,
            # cropped to the drawing so a sparse one sits small in it), a dashed
            # outline (an "add" place is an outline), and fields.
            JUST = r"""(where) => {
              const rgba = s => { if (!s) return null; const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
                return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
              const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                                 return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
              const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
              const fill = e => { const layers = [];
                for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
                  if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
                let g = [255, 255, 255];
                for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
                return g; };
              const shadows = s => [...(s || '').matchAll(/(rgba?\([^)]*\)|color\([^)]*\))\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+([\d.]+)px(?:\s+(-?[\d.]+)px)?/g)]
                .map(m => ({ c: rgba(m[1]), blur: parseFloat(m[4]), spread: parseFloat(m[5] || '0'), x: parseFloat(m[2]), y: parseFloat(m[3]) }));
              const SKIP = new Set(['INPUT', 'TEXTAREA', 'SELECT', 'IMG', 'CANVAS', 'VIDEO', 'svg', 'path', 'HR', 'OPTION']);
              const name = e => e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
              const out = [];
              for (const e of document.querySelectorAll('body *')) {
                if (SKIP.has(e.tagName) || !e.getClientRects().length || e.closest('[hidden]')) continue;
                const r = e.getBoundingClientRect(); if (r.width < 40 || r.height < 28) continue;
                const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
                const sh = shadows(cs.boxShadow);
                if (sh.some(s => s.c && s.c[3] > 0.04 && s.blur > 0)) continue;
                const bw = ['Top', 'Right', 'Bottom', 'Left'].map(s => parseFloat(cs['border' + s + 'Width']) || 0);
                const bc = ['Top', 'Right', 'Bottom', 'Left'].map(s => rgba(cs['border' + s + 'Color']));
                const dashed = /dashed|dotted/.test(cs.borderTopStyle);
                const sides = dashed ? 0 : bw.map((w, i) => w > 0 && bc[i] && bc[i][3] > 0.02).filter(Boolean).length;
                const ring = sh.some(s => s.c && s.c[3] > 0.02 && s.blur === 0 && s.x === 0 && s.y === 0 && s.spread > 0);
                if (sides < 2 && !ring) continue;
                const same = (a, b) => { const x = a.getBoundingClientRect(), y = b.getBoundingClientRect();
                  return Math.abs(x.left - y.left) < 2 && Math.abs(x.top - y.top) < 2 && Math.abs(x.right - y.right) < 2 && Math.abs(x.bottom - y.bottom) < 2; };
                let g = e.parentElement;
                while (g && g !== document.body && same(g, e)) g = g.parentElement;
                const covers = m => { const q = m.getBoundingClientRect(); return q.left <= r.left + 1 && q.top <= r.top + 1 && q.right >= r.right - 1 && q.bottom >= r.bottom - 1; };
                if (e.matches('.gal-pic') || [...e.querySelectorAll('canvas, img, video')].some(m => { const q = m.getBoundingClientRect(); return q.width * q.height >= 0.8 * r.width * r.height; })) continue;
                if ([...(g || document.body).querySelectorAll('canvas, img, video')].some(m => !e.contains(m) && covers(m))) continue;
                const text = (e.innerText || '').replace(/\s+/g, ' ').trim();
                const pic = !!e.querySelector('img, canvas, video, .skribl-inline');
                if (!text && !pic) continue;
                const apart = ratio(fill(e), g ? fill(g) : [255, 255, 255]);
                if (apart >= 1.08) continue;
                out.push(where + ': ' + name(e) + ' "' + text.slice(0, 28) + '" ' + apart.toFixed(2) + ':1');
              }
              return out; }"""
            juno = someone(b, "juno", "Juno")
            rook = someone(b, "rook", "Rook")
            mira = someone(b, "mira", "Mira Lopez")
            kai = someone(b, "kai", "Kai Moss")
            j13 = make_post(juno, "Section 13, Juno's drawing", payload=with_poster(drawing(seed=130)))
            jt13 = make_post(juno, "Section 13, Juno's, with comments", seed=131)
            q13, _, _ = quote(rook, "Section 13, Rook quotes Juno's", post=j13)
            d13 = make_drawing(juno, "Section 13, a drawing", seed=132)
            qd13, _, _ = quote(rook, "Section 13, Rook quotes a drawing", drawing=d13)
            qq13, _, _ = quote(mira, "Section 13, Mira quotes Rook's quote", post=qd13)
            gone13 = make_post(juno, "Section 13, to be deleted", seed=133)
            qg13, _, _ = quote(rook, "Section 13, Rook quotes one gone", post=gone13)
            c = juno.client()
            c.get(f"/social/p/{gone13}")
            c.post_json(f"/social/p/{gone13}/delete", {})
            repost(mira, j13)
            pile_on(jt13, 3, 2, 0)
            for h in ("juno", "rook", "mira"):
                follow(kai, h)
            follow(juno, "kai")
            found, seen = [], 0
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen} {scheme}"
                    ctx, pg = browser_as(b, kai, screen=screen, scheme=scheme)
                    for path_ in ("/social/", f"/social/p/{jt13}", f"/social/p/{qq13}", "/social/@rook", "/social/you",
                                  "/social/explore", "/social/explore?q=juno&who=people"):
                        go(pg, path_, wait=700)
                        found += pg.evaluate(JUST, f"{tag} {path_}")
                        seen += 1
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, juno, screen=screen, scheme=scheme)
                    go(pg, "/social/activity", wait=900)
                    found += pg.evaluate(JUST, f"{tag} /social/activity")
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, None, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=900)
                    found += pg.evaluate(JUST, f"{tag} signed out /social/")
                    close_ctx(ctx, pg)
                    seen += 2
            check("just a border: on Home, a post, a quote of a quote, a person, Settings, the Gallery, people search,"
                  " Activity and signed-out Home, phone and desk, light and dark, no box with something in it is set"
                  " apart from what it sits on by its line alone (its fill 1.08:1 or more from its ground, or a lift)",
                  seen == 36 and not found, f"{len(found)} on {seen} pages: {found[:6]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(13, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
