#!/usr/bin/env python3
"""Bookmarks on the Skribl site (the map, part two, item 2; docs/SOCIAL-SITE.md
section 17; the owner's "All yes" on the bookmarks mock, Nov 14), through the
demo's own server, with Chromium's virtual authenticator for the site's people.

  1. THE ROW IN THE ⋯ (the mock's A): "Bookmark" first in the ⋯ sheet's first
     card, above Copy link, on somebody's post on Home, on its own page, on a
     drawing's own page and on your own post, a phone and a desk; its ribbon
     drawn in our pen (the mock's line), in the row's own icon ink, its inside
     empty; its words where every row's start, 17px, the row 56px; none on
     what is taken down or kept link-only (your own); the row under a post
     unchanged, no ribbon in it.
  2. A TAP KEEPS IT: the sheet goes down, one bookmark kept, and the site's
     toast says "Bookmarked. It’s on your page, under Bookmarks." with Undo,
     beside the ribbon, never over a ⋯ (the next press); the ⋯ then says
     "Remove bookmark", its ribbon filled in the small violet ink, after a
     reload too; Remove takes it away ("Removed from your bookmarks." with
     Undo), and Undo puts it back, says so with no Undo of its own, and gives
     the ⋯ its focus. A drawing shown outside a post the same, on a desk.
  3. WHO MAY BOOKMARK: signed out, without the page's token or from another
     origin, taken down, a block either way, a post taken down, a drawing kept
     link-only, a post's drawing asked as a drawing, a body that is not a yes
     or a no: refused, nothing kept; one bookmark a person a thing; your own
     taken away whatever became of the thing; the limit (120 an hour).
  4. SIGNED OUT: the ⋯ shows Bookmark; a tap raises "Bookmark this post?"
     ("Sign in, and it’s kept for you on your page, where only you can see
     it."), Not now | Sign in, Sign in coming back to the page; Not now gives
     the ⋯ its focus back; nothing is kept; a profile's card too.
  5. NOBODY IS TOLD, AND NOTHING COUNTS THEM: the maker's Activity holds no
     row and the bell no dot; no page says how many, to the maker, the people
     who kept it, anybody else or nobody, and the site's answer says only
     whether it is yours.
  6. YOUR BOOKMARKS (your own page's tab; that it is yours alone is
     verify_socialprofile's 15): posts and drawings as Home's cards, newest
     kept first, Load more; hidden, never deleted: a block either way,
     anybody taken down, a post taken down (but your own, with its note), a
     drawing made link-only or deleted in Skribl; somebody you muted still
     there; the tab's own words when it holds nothing, and its heading.
  7. DELETING TAKES THEM, IN CODE: a post, a drawing and an account, through
     the site's own routes, and with SQLite's cascade off (on a copy).
  8. THE DATA: the chain on a populated database (the table, its indexes and
     its CHECK; back down); one bookmark a person a thing, on exactly one
     thing; the reads on their indexes (SQLite's own plan); a page of Home's
     cards asks once.
  9. CONTRAST AND TARGETS: the ribbon read off the paint, filled at 3:1 or
     more on what is painted behind it, empty too, and the toast's, phone and
     desk, light and dark; every word on the ⋯, the toast, the signed-out
     sheet and the Bookmarks tab (full and empty) at 4.5:1, every target 44px.
 10. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALBOOKMARKS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Bookmarks".
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
PART = os.environ.get("SOCIALBOOKMARKS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALBOOKMARKS {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence bookmarks work.")
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
TMP = tempfile.mkdtemp(prefix="socialbookmarks-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialbookmarks-" + secrets.token_hex(8),
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

# A landed "Liked by…": its words and names against the note's tint over the


def mark(who, on, kept=True, raw=None, token=None, origin=BASE):
    """A bookmark kept (or taken away) as the ⋯ sends one, on a post (("p",
    id)) or a drawing (("s", id)): (status, answer)."""
    c = who.client() if who is not None else Client()
    c.origin = origin
    c.get(page_of(on))
    if not c.token:
        c.get("/social/")      # a page they cannot open: the token from one they can
    return c.post_json(page_of(on) + "/bookmark", raw if raw is not None else {"bookmarked": kept}, token=token)


def marks_on(on):
    """The bookmarks kept on a post or a drawing: [handle], oldest first."""
    kind, oid = on
    if kind == "p":
        return [r[0] for r in db("select p.handle from social_bookmarks k join social_posts s on s.id = k.post_id"
                                 " join social_people p on p.id = k.person_id where s.public_id = ? order by k.id", (oid,))]
    return [r[0] for r in db("select p.handle from social_bookmarks k join social_people p on p.id = k.person_id"
                             " where k.drawing_id = ? order by k.id", (oid,))]


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


def press_mark(pg, sel="#postSheet [data-act=bookmark]", after=1000):
    """Press the Bookmark row (or Undo) and wait for the site's answer. A press
    that sends nothing reads as the row's own red, never a section that stops."""
    try:
        with pg.expect_response(lambda r: r.url.endswith("/bookmark") and r.request.method == "POST", timeout=8000):
            press(pg, sel)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(after)


def to(pg, sel, top=100):
    """Scroll so that `sel` sits `top` px from the top of the window."""
    pg.evaluate("([s, y]) => { const e = document.querySelector(s); if (e) scrollTo(0, e.getBoundingClientRect().top + scrollY - y); }",
                [sel, top])
    pg.wait_for_timeout(250)


PAGE_MENU = ".post-page > .post-row [data-post-menu]"

# THE ⋯ SHEET's rows, card by card, as they show: what each says, which it
# is, its icon (its classes, its two lines, its stroke), the inks (the row's,
# its icon's, the ribbon's inside), where its words start, their size and
# weight, its box, and whether a press lands on it; and the inks the page's
# tokens say a row should wear.
ROWS = r"""() => { const s = document.getElementById('postSheet'); if (!s) return null;
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  return { open: s.classList.contains('is-open') && !s.hidden,
    ink: probe('var(--ink)'), ink2: probe('var(--ink-2)'), accent: probe('var(--accent-ink)'),
    cards: [...s.querySelectorAll('.post-acts')].map(c => [...c.querySelectorAll('.post-act')]
      .filter(b => !b.hidden && b.getClientRects().length).map(b => {
        const ic = b.querySelector('svg'), w = b.querySelector('.mu-words b') || b.querySelector(':scope > span');
        const r = b.getBoundingClientRect(), wr = w.getBoundingClientRect(), cs = getComputedStyle(w);
        const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const fill = ic && ic.querySelector('.bm-fill'), paths = ic ? [...ic.querySelectorAll('path')] : [];
        return { name: w.textContent.trim(), act: b.getAttribute('data-act'), ic: ic ? ic.getAttribute('class') : null,
                 d: paths.map(p => p.getAttribute('d')), unit: paths.map(p => p.getAttribute('pathLength')),
                 stroke: ic ? ic.getAttribute('stroke-width') : null, marked: b.classList.contains('is-marked'),
                 color: getComputedStyle(b).color, wordColor: cs.color, icColor: ic ? getComputedStyle(ic).color : null,
                 fill: fill ? getComputedStyle(fill).fill : null, left: Math.round(wr.left * 100) / 100,
                 size: cs.fontSize, weight: cs.fontWeight, h: Math.round(r.height * 10) / 10,
                 hit: !!at && (at === b || b.contains(at)) }; })) }; }"""

# The ribbon, as _icons.html draws it (the mock's own line, bm_mock.py's D).
RIBBON = ("M 16.9,4.3 C 13.7,4.1 10.4,4.2 7.3,4.3 C 6.7,4.3 6.4,4.7 6.4,5.3 C 6.5,10.1 6.4,14.9 6.5,19.6 "
          "C 8.3,18.2 10.2,16.8 12.0,15.5 C 13.9,16.8 15.7,18.2 17.6,19.7 C 17.5,14.9 17.6,10.1 17.6,5.2 "
          "C 17.6,4.6 17.4,4.3 16.9,4.3")

# THE TOAST: up, its words, Undo shown, which icon it wears (the ribbon, or
# the eye), and whether the ⋯ sheet has gone down.
TOAST = r"""() => { const t = document.querySelector('.mu-toast'); if (!t) return null;
  const vis = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).display !== 'none';
  const u = t.querySelector('[data-mute-undo]'), s = document.getElementById('postSheet');
  return { up: !t.hidden && t.classList.contains('is-up'), words: t.querySelector('[data-mute-said]').textContent,
           undo: !!u && !u.hidden && vis(u), ribbon: vis(t.querySelector('.ic-mark')),
           eye: [...t.querySelectorAll('svg.ic:not(.ic-mark)')].some(vis),
           sheetDown: !s || !s.classList.contains('is-open') }; }"""

# Where the toast is, and whether it covers any of `sel` in view: by its box,
# and by what is painted at each one's middle with the toast made
# hit-testable (its words take no tap, so elementFromPoint would look through
# them as a tap does); how far it rose above its own place (--mu-lift).
CLEAR_OF = """(sel) => { const t = document.querySelector('.mu-toast'), box = document.querySelector('.mu-toasts');
  const r = t.getBoundingClientRect(); t.style.pointerEvents = 'auto';
  const out = { toast: [Math.round(r.top), Math.round(r.bottom), Math.round(r.left), Math.round(r.right)], vh: innerHeight,
    lifted: parseFloat(getComputedStyle(box).getPropertyValue('--mu-lift')) || 0, under: [], covered: [], seen: 0,
    words: t.querySelector('[data-mute-said]').textContent };
  document.querySelectorAll(sel).forEach(e => { if (!e.getClientRects().length) return; const q = e.getBoundingClientRect();
    if (q.bottom <= 0 || q.top >= innerHeight) return; out.seen++;
    if (q.bottom > r.top && q.top < r.bottom && q.right > r.left && q.left < r.right) out.under.push(Math.round(q.top));
    const at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    if (at && at.closest('.mu-toast')) out.covered.push(Math.round(q.top)); });
  t.style.pointerEvents = '';
  return out; }"""

# What a tab's panel holds, in order: each card's post (a drawing's card says
# b-<its id>) and where it opens; whether Load more is there; its words when
# empty; its heading; and the chosen tab.
PANEL = r"""() => { const p = document.querySelector('[data-prof-panel]'); if (!p) return null;
  const items = [...p.querySelectorAll('[data-prof-list] > .post-card')];
  const more = p.querySelector('[data-prof-next]'), none = p.querySelector('[data-prof-none]');
  const c = document.querySelector('[data-prof-tabs] a[aria-current]');
  return { tab: p.getAttribute('data-tab'), chosen: c ? c.getAttribute('data-tab') : null,
    ids: items.map(e => e.getAttribute('data-post')), urls: items.map(e => e.getAttribute('data-url')),
    notes: items.filter(e => e.querySelector('.post-down')).map(e => e.getAttribute('data-post')),
    marked: items.filter(e => e.hasAttribute('data-marked')).length,
    more: !!more && !more.hidden, none: none && !none.hidden ? none.innerText.replace(/\s+/g, ' ').trim() : null,
    heading: (p.querySelector('h2.sr') || {}).textContent || null, at: location.pathname }; }"""

# The ribbon in a row of the ⋯ (by its action), its box, and the row's own
# ground behind it, for reading off the paint.
RIBBON_BOX = r"""(sel) => { const ic = document.querySelector(sel + ' svg.ic-mark'); if (!ic) return null;
  const r = ic.getBoundingClientRect(), row = ic.closest('.post-act, .mu-toast').getBoundingClientRect();
  return { x: r.left, y: r.top, w: r.width, h: r.height, row: [row.left, row.top, row.width, row.height] }; }"""


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def ribbon_paint(pg, sel):
    """The ribbon read off the paint: the pixels inside its box against the
    ground painted just beside it (in the same row, 8px before the icon): how
    far the most different reaches (its line, or its inside when filled,
    3:1 at least either way), and, read at its middle (inside the ribbon's
    line), what its inside paints. None when it is not there."""
    box = pg.evaluate(RIBBON_BOX, sel)
    if not box or Image is None:
        return None
    s = 2
    png = pg.screenshot(clip={"x": max(0, box["x"] - 10), "y": box["y"], "width": box["w"] + 12, "height": box["h"]},
                        scale="device")
    im = Image.open(io.BytesIO(png)).convert("RGB")
    k = im.width / (box["w"] + 12)
    ground = im.getpixel((int(2 * k), int(box["h"] / 2 * k)))
    x0 = int((box["x"] - max(0, box["x"] - 10)) * k)
    px = [im.getpixel((x, y)) for x in range(x0, min(im.width, x0 + int(box["w"] * k))) for y in range(im.height)]
    best = max((ratio(p, ground) for p in px), default=1)
    mid = im.getpixel((x0 + int(box["w"] * k / 2), int(box["h"] * k * 0.42)))
    return {"ground": ground, "best": round(best, 2), "mid": mid, "mid_k": round(ratio(mid, ground), 2)}


# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then goes
# because the code said so. And the reads, as the code sends them, planned
# by SQLite, and how many reads of the bookmarks a page of Home's cards makes.
PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Bookmark, Person, Post
    from social.accounts import delete_person
    from social.posts import drop_post
    from social import bookmarks as B
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    post_id, person, lister, home_as = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    row = db.session.execute(sa.select(Post).where(Post.public_id == post_id)).scalar_one()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == person)).scalar_one()
    me = db.session.execute(sa.select(Person).where(Person.handle_key == lister)).scalar_one()
    author = db.session.get(Person, row.person_id)
    n = lambda w: db.session.execute(sa.select(sa.func.count()).select_from(Bookmark).where(w)).scalar()
    out = {"fk": fk}
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if "social_bookmarks" in statement and statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        for name, call in (("list", lambda: B.marked_page(me)),
                           ("marked", lambda: B.marked(me, posts=[row.id], drawings=["nothing"]))):
            rec.clear()
            call()
            calls[name] = list(rec)
    event.remove(db.engine, "before_cursor_execute", keep)
    conn = db.session.connection()
    out["plans"] = {name: [r[3] for st, params in sent
                           for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
                    for name, sent in calls.items()}
    out["sent"] = {name: len(sent) for name, sent in calls.items()}
    seen = []
    def count(conn, cursor, statement, *a):
        if "social_bookmarks" in statement:
            seen.append(statement.split()[0])
    event.listen(db.engine, "before_cursor_execute", count)
    page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": home_as, "X-Forwarded-For": "10.250.1.2"})
    event.remove(db.engine, "before_cursor_execute", count)
    out["reads"] = seen
    out["cards"] = page.get_data(as_text=True).count('class="post-card"')
    before = n(Bookmark.post_id == row.id)
    drop_post(author.public_id, row)
    db.session.commit()
    out["post"] = [before, n(Bookmark.post_id == row.id)]
    kept, owned = n(Bookmark.person_id == who.id), n(Bookmark.owner_id == who.id)
    delete_person(db.session, who.id)
    db.session.commit()
    out["person"] = [kept, owned, n(Bookmark.person_id == who.id), n(Bookmark.owner_id == who.id)]
    print(json.dumps(out))
"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the row in the ⋯: Bookmark first, its ribbon in our pen; none on what is taken down; the row under a post"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            p1 = make_post(pia, "Section 1, Pia's")
            d1 = make_drawing(pia, "Section 1, Pia's drawing", seed=11)
            k1 = make_post(kai, "Section 1, Kai's own")
            rows = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, kai, screen=screen)
                go(pg, "/social/", wait=500)
                to(pg, card(p1), 120)
                open_sheet(pg, card(p1) + " [data-post-menu]")
                rows[(screen, "their card")] = pg.evaluate(ROWS)
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(500)
                to(pg, card(k1), 120)
                open_sheet(pg, card(k1) + " [data-post-menu]")
                rows[(screen, "your own card")] = pg.evaluate(ROWS)
                go(pg, f"/social/p/{p1}")
                open_sheet(pg, PAGE_MENU)
                rows[(screen, "a post's page")] = pg.evaluate(ROWS)
                go(pg, f"/social/b/{d1}")
                open_sheet(pg, PAGE_MENU)
                rows[(screen, "a drawing's page")] = pg.evaluate(ROWS)
                close_ctx(ctx, pg)
            firsts = {f"{s} {k}": [r["name"] for r in (v or {}).get("cards", [[]])[0]] for (s, k), v in rows.items()}
            check("Bookmark first in the ⋯'s first card, above Copy link: somebody's post on Home, on its own page, a"
                  " drawing on its own page, and your own post, on a phone and a desk",
                  len(rows) == 8 and all(v and v["cards"] and [r["name"] for r in v["cards"][0]][:2] == ["Bookmark", "Copy link"]
                                         and v["cards"][0][0]["act"] == "bookmark" for v in rows.values()),
                  json.dumps(firsts)[:700])
            looks = []
            for (s, k), v in rows.items():
                if not (v and v["cards"] and v["cards"][0]):
                    looks.append((s, k, "no rows"))
                    continue
                bm, cp = v["cards"][0][0], v["cards"][0][1]
                lefts = {round(r["left"], 1) for c in v["cards"] for r in c}
                ok = ("ic-mark" in (bm["ic"] or "") and "pen-ic" in (bm["ic"] or "") and bm["d"] == [RIBBON, RIBBON]
                      and bm["unit"] == [None, "1"] and bm["stroke"] == "2.1" and not bm["marked"]
                      and bm["icColor"] == v["ink2"] == cp["icColor"] and bm["fill"] in ("none", None)
                      and bm["wordColor"] == v["ink"] and bm["size"] == "17px" and bm["weight"] == "600"
                      and len(lefts) == 1 and bm["h"] >= 56 and bm["hit"])
                if not ok:
                    looks.append((s, k, {x: bm.get(x) for x in ("ic", "unit", "stroke", "marked", "icColor", "fill",
                                                                "wordColor", "size", "weight", "h", "hit")}, v["ink2"], len(lefts)))
            check("its ribbon drawn in our pen (the mock's line: its inside and the line itself, one unit long, 2.1"
                  " wide), in the row's own icon ink (Copy link's), its inside empty; \"Bookmark\" in the row's ink,"
                  " 17px 600, starting where every row's words start; the row 56px tall and painted where it stands",
                  len(rows) == 8 and not looks, json.dumps(looks)[:700])
            # NONE ON WHAT IS TAKEN DOWN OR KEPT LINK-ONLY (its maker alone sees it).
            t1 = make_post(kai, "Section 1, Kai's, to be taken down")
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (t1,))
            l1 = make_drawing(kai, "Section 1, Kai's link-only drawing", seed=12, vis="unlisted")
            downs = {}
            ctx, pg = browser_as(b, kai)
            go(pg, f"/social/p/{t1}")
            downs["taken down"] = (pg.evaluate("() => !!document.querySelector('.post-page .post-down')"), None)
            open_sheet(pg, PAGE_MENU)
            downs["taken down"] = (downs["taken down"][0], [r["name"] for r in pg.evaluate(ROWS)["cards"][0]])
            go(pg, f"/social/b/{l1}")
            open_sheet(pg, PAGE_MENU)
            downs["link-only"] = (True, [r["name"] for r in pg.evaluate(ROWS)["cards"][0]])
            close_ctx(ctx, pg)
            check("none on what is taken down (your own post, shown you with its note) or kept link-only (your own"
                  " drawing hidden from the Gallery): their ⋯ starts at Copy link, as the heart is not there either",
                  downs["taken down"][0] and all(v[1] and v[1][0] == "Copy link" and "Bookmark" not in v[1]
                                                 for v in downs.values()),
                  json.dumps(downs))
            ctx, pg = browser_as(b, kai)
            go(pg, "/social/", wait=500)
            to(pg, card(p1), 120)
            row = pg.evaluate("(s) => [...document.querySelector(s + ' .post-row').children].map(k => [...k.classList].find(c => /^(post|lk|rp)-/.test(c)))"
                              " .concat([document.querySelectorAll(s + ' .post-row .ic-mark').length + ' ribbons'])", card(p1))
            close_ctx(ctx, pg)
            # (Since reposts, the reposts mock, Nov 14: the repost where Share was, after the 💬, Share in the ⋯.)
            check("the row under a post as it is: 💬, the repost, the heart, the ⋯ and Open ›, and no ribbon in it",
                  row == ["post-count", "rp-btn", "lk-heart", "post-more", "post-open", "0 ribbons"], json.dumps(row))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "a tap keeps it: the toast with Undo; Remove bookmark, its ribbon filled; Undo; a drawing's too"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            p2 = make_post(pia, "Section 2, Pia's")
            make_post(pia, "Section 2, Pia's next, so the first sits lower")
            d2 = make_drawing(pia, "Section 2, Pia's drawing", seed=21)
            ctx, pg = browser_as(b, kai, screen="phone", scheme="light")
            go(pg, "/social/", wait=500)
            # Its ⋯ low on the screen, just where the toast rises: the next
            # press is the one the toast must keep clear of.
            pg.evaluate("(s) => { const m = document.querySelector(s + ' [data-post-menu]'); const r = m.getBoundingClientRect();"
                        " scrollBy(0, r.top - (innerHeight - 77 - 44)); }", card(p2))
            pg.wait_for_timeout(300)
            open_sheet(pg, card(p2) + " [data-post-menu]")
            press_mark(pg)
            t_kept = pg.evaluate(TOAST)
            clear = pg.evaluate(CLEAR_OF, "[data-post-menu]")
            kept = marks_on(("p", p2))
            owner = db("select o.handle from social_bookmarks k join social_people o on o.id = k.owner_id"
                       " join social_posts s on s.id = k.post_id where s.public_id = ?", (p2,))
            card_marked = pg.evaluate("(s) => document.querySelector(s).hasAttribute('data-marked')", card(p2))
            open_sheet(pg, card(p2) + " [data-post-menu]")
            again = pg.evaluate(ROWS)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            pg.reload()
            ready(pg)
            pg.wait_for_timeout(400)
            to(pg, card(p2), 120)
            open_sheet(pg, card(p2) + " [data-post-menu]")
            reloaded = pg.evaluate(ROWS)
            press_mark(pg)
            t_gone = pg.evaluate(TOAST)
            gone = marks_on(("p", p2))
            press_mark(pg, ".mu-toast [data-mute-undo]")
            t_undo = pg.evaluate(TOAST)
            back = marks_on(("p", p2))
            focus = pg.evaluate("(s) => document.activeElement === document.querySelector(s + ' [data-post-menu]')", card(p2))
            close_ctx(ctx, pg)
            ADDED, REMOVED = "Bookmarked. It’s on your page, under Bookmarks.", "Removed from your bookmarks."
            check("a tap on Bookmark keeps it: the sheet goes down, the site keeps one bookmark (Kai's, on Pia's post,"
                  " hers), and the site's toast says “Bookmarked. It’s on your page, under Bookmarks.” with Undo, beside"
                  " the ribbon (not the eye)",
                  kept == ["kai"] and owner == [("pia",)] and t_kept and t_kept["up"] and t_kept["words"] == ADDED
                  and t_kept["undo"] and t_kept["ribbon"] and not t_kept["eye"] and t_kept["sheetDown"],
                  f"kept {kept} owner {owner}; toast {t_kept}")
            check("the toast never covers a ⋯, the next press: the card's ⋯ that sat where it rises stays clear of it",
                  clear["seen"] >= 1 and not clear["covered"] and not clear["under"] and clear["lifted"] > 0,
                  json.dumps(clear))
            fr = lambda v: (v or {}).get("cards", [[{}]])[0][0] if (v or {}).get("cards") and v["cards"][0] else {}
            a0, r0 = fr(again), fr(reloaded)
            check("the ⋯ then says Remove bookmark, its ribbon filled in the small violet ink (--accent-ink), its words"
                  " the row's own; the card says so at once (data-marked), and after a reload too",
                  card_marked and all(x.get("name") == "Remove bookmark" and x.get("marked") and x.get("icColor") == v["accent"]
                                      and x.get("fill") == v["accent"] and x.get("wordColor") == v["ink"]
                                      for x, v in ((a0, again), (r0, reloaded))),
                  json.dumps({"card": card_marked, "again": a0, "reloaded": r0})[:700])
            check("Remove bookmark takes it away, the toast saying “Removed from your bookmarks.” with Undo; Undo puts"
                  " it back, saying “Bookmarked…” with no Undo of its own, and gives the ⋯ its focus",
                  gone == [] and t_gone and t_gone["words"] == REMOVED and t_gone["undo"] and t_gone["ribbon"]
                  and back == ["kai"] and t_undo and t_undo["up"] and t_undo["words"] == ADDED and not t_undo["undo"]
                  and focus,
                  f"gone {gone} {t_gone}; back {back} {t_undo}; focus {focus}")
            # A DRAWING SHOWN OUTSIDE A POST, on its own page, on a desk in dark.
            ctx, pg = browser_as(b, kai, screen="desk", scheme="dark")
            go(pg, f"/social/b/{d2}")
            open_sheet(pg, PAGE_MENU)
            press_mark(pg)
            dt1 = pg.evaluate(TOAST)
            dk = db("select post_id, drawing_id from social_bookmarks where drawing_id = ?", (d2,))
            open_sheet(pg, PAGE_MENU)
            dagain = fr(pg.evaluate(ROWS))
            press_mark(pg)
            dgone = marks_on(("s", d2))
            press_mark(pg, ".mu-toast [data-mute-undo]")
            dback = marks_on(("s", d2))
            close_ctx(ctx, pg)
            check("a drawing shown outside a post, on its own page on a desk in dark: kept on the drawing (its id, no"
                  " post), the toast the same, the ⋯ then Remove bookmark, taken away, and back by Undo",
                  dk == [(None, d2)] and dt1 and dt1["words"] == ADDED and dt1["undo"] and dt1["ribbon"]
                  and dagain.get("name") == "Remove bookmark" and dagain.get("marked") and dgone == [] and dback == ["kai"],
                  f"kept {dk}; toast {dt1}; again {dagain.get('name')}; gone {dgone}; back {dback}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "who may bookmark: refused and nothing kept; once a person a thing; your own taken away; the limit"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            kai = someone(b, "kai", "Kai Moss")
            lux = someone(b, "lux", "Lux Nairn")
            moe = someone(b, "moe", "Moe Reyes")
            ned = someone(b, "ned", "Ned Sato")
            p3 = make_post(pia, "Section 3, Pia's")
            d3 = make_drawing(pia, "Section 3, Pia's drawing", seed=31)
            l3 = make_drawing(pia, "Section 3, Pia's link-only drawing", seed=32, vis="unlisted")
            t3 = make_post(pia, "Section 3, Pia's, taken down")
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (t3,))
            got = {}
            got["signed out"] = mark(None, ("p", p3))
            got["no token"] = mark(kai, ("p", p3), token="")
            got["another origin"] = mark(kai, ("p", p3), origin="https://elsewhere.example")
            block(pia, "lux")                    # Pia blocked Lux
            block(moe, "pia")                    # Moe blocked Pia
            got["blocked by its maker"] = mark(lux, ("p", p3))
            got["its maker blocked"] = mark(moe, ("p", p3))
            got["a post taken down"] = mark(kai, ("p", t3))
            got["a drawing kept link-only"] = mark(kai, ("s", l3))
            got["a post's drawing, as a drawing"] = mark(kai, ("s", skribl_of(p3)))
            got["your own post, taken down"] = mark(pia, ("p", t3))
            got["your own drawing, kept link-only"] = mark(pia, ("s", l3))
            got["not a yes or a no"] = mark(kai, ("p", p3), raw={"bookmarked": "yes"})
            got["nothing said"] = mark(kai, ("p", p3), raw={})
            refused = {k: (v[0], (v[1] or {}).get("error") if isinstance(v[1], dict) else str(v[1])[:30]) for k, v in got.items()}
            left = marks_on(("p", p3)) + marks_on(("p", t3)) + marks_on(("s", l3)) + marks_on(("s", skribl_of(p3)))
            want = {"signed out": (401, "signed_out"), "no token": (403, "stale"), "another origin": (403, "stale"),
                    "blocked by its maker": (404, "gone"), "its maker blocked": (404, "gone"),
                    "a post taken down": (404, "gone"), "a drawing kept link-only": (404, "gone"),
                    "a post's drawing, as a drawing": (404, "gone"), "your own post, taken down": (404, "gone"),
                    "your own drawing, kept link-only": (404, "gone"), "not a yes or a no": (400, "bad"),
                    "nothing said": (400, "bad")}
            check("refused, and nothing kept: signed out (401), without the page's token or from another origin (403),"
                  " a block either way, a post taken down, a drawing kept link-only, a post's drawing asked as a"
                  " drawing, and your own post taken down or drawing kept link-only, which you alone see and which take"
                  " nothing new, as a like (404, as their pages are), and a body that is not a yes or a no (400)",
                  refused == want and left == [], f"{refused}; kept {left}")
            once = [mark(kai, ("p", p3))[0], mark(kai, ("p", p3))[0], mark(kai, ("s", d3))[0], mark(kai, ("s", d3))[0]]
            n_once = (marks_on(("p", p3)), marks_on(("s", d3)))
            off = [mark(kai, ("p", p3), kept=False), mark(kai, ("p", p3), kept=False)]
            answer = off[0][1] if isinstance(off[0][1], dict) else {}
            check("one bookmark a person a thing: kept twice is one (a post's and a drawing's), taken away twice is"
                  " none, and the site answers with whether it is yours, nothing more",
                  once == [200] * 4 and n_once == (["kai"], ["kai"]) and [o[0] for o in off] == [200, 200]
                  and marks_on(("p", p3)) == [] and sorted(answer) == ["bookmarked", "ok"] and answer["bookmarked"] is False,
                  f"{once} {n_once}; off {[(o[0], o[1]) for o in off]}")
            # YOUR OWN, TAKEN AWAY WHATEVER BECAME OF IT: kept, then its maker
            # blocks you, the post is taken down, and you are taken down.
            p3b = make_post(pia, "Section 3, Pia's second")
            mark(ned, ("p", p3b))
            mark(ned, ("s", d3))
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'ned'")
            nk = mark(ned, ("p", p3), kept=True)
            n_off = mark(ned, ("p", p3b), kept=False)
            db_write("update social_people set taken_down_at = null where handle_key = 'ned'")
            mark(ned, ("p", p3b))
            block(pia, "ned")
            n_off2 = mark(ned, ("p", p3b), kept=False)
            n_off3 = mark(ned, ("s", d3), kept=False)
            nothing = mark(kai, ("p", "nosuchpost00"), kept=False)
            check("taken down, nothing new is kept (403); but your own is always yours to take away, by its address,"
                  " whatever became of the thing (you taken down, a block since); one never kept on what is not there"
                  " is gone (404)",
                  nk[0] == 403 and (nk[1] or {}).get("error") == "taken_down" and n_off[0] == 200 and n_off2[0] == 200
                  and n_off3[0] == 200 and marks_on(("p", p3b)) == [] and "ned" not in marks_on(("s", d3))
                  and nothing[0] == 404,
                  f"kept {nk}; off {n_off[0]} {n_off2[0]} {n_off3[0]}; left {marks_on(('p', p3b))} {marks_on(('s', d3))};"
                  f" nothing {nothing[0]}")
            # THE LIMIT: 120 an hour, a person, keeping and taking away alike.
            ozzy = someone(b, "ozzy", "Ozzy Tate")
            c = ozzy.client()
            c.get(f"/social/p/{p3}")
            codes = []
            for i in range(125):
                st, _ = c.post_json(f"/social/p/{p3}/bookmark", {"bookmarked": i % 2 == 0})
                codes.append(st)
                if st == 429:
                    break
            check("the limit: 120 a person an hour, keeping and taking away alike, then 429 and nothing kept",
                  codes[:120] == [200] * 120 and codes[120:] == [429] and "ozzy" not in marks_on(("p", p3)),
                  f"{len(codes)} asked, first refusal at {codes.index(429) + 1 if 429 in codes else None}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "signed out: Bookmark in the ⋯ raises the small sheet that says how; Sign in comes back; nothing kept"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            p4 = make_post(pia, "Section 4, Pia's")
            before = db("select count(*) from social_bookmarks")[0][0]
            outs = {}
            for screen, path, opener in (("phone", f"/social/p/{p4}", PAGE_MENU),
                                         ("desk", "/social/@pia", card(p4) + " [data-post-menu]")):
                ctx, pg = browser_as(b, None, screen=screen)
                go(pg, path)
                if path.startswith("/social/@"):
                    to(pg, card(p4), 120)
                open_sheet(pg, opener)
                first = [r["name"] for r in pg.evaluate(ROWS)["cards"][0]][:1]
                press(pg, "#postSheet [data-act=bookmark]")
                pg.wait_for_timeout(800)
                sheet = pg.evaluate("""() => { const w = document.getElementById('bookmarkOutSheet'); if (!w) return null;
                  const a = w.querySelector('a.btn'), u = new URL(a.href);
                  return { open: w.classList.contains('is-open') && !w.hidden, menu: document.getElementById('postSheet').classList.contains('is-open'),
                    title: w.querySelector('h2').textContent, lede: w.querySelector('.post-lede').textContent,
                    buttons: [...w.querySelectorAll('.post-sheet-acts .btn')].map(e => e.textContent.trim()),
                    signin: [u.pathname, u.searchParams.get('next')], paper: getComputedStyle(w.querySelector('.make-sheet')).backgroundColor,
                    focus: document.activeElement && document.activeElement.textContent.trim() }; }""")
                if sheet and sheet["open"]:
                    press(pg, "#bookmarkOutSheet .post-sheet-acts [data-make-close]")
                pg.wait_for_timeout(700)
                back = pg.evaluate("(s) => { const w = document.getElementById('bookmarkOutSheet');"
                                   " return { open: !!w && w.classList.contains('is-open'), focus: document.activeElement === document.querySelector(s) }; }",
                                   opener)
                outs[screen] = {"first": first, "sheet": sheet, "back": back, "path": path}
                close_ctx(ctx, pg)
            after = db("select count(*) from social_bookmarks")[0][0]
            nxt = lambda pth: ["/social/signin", pth]
            check("signed out, the ⋯ shows Bookmark first; a tap raises “Bookmark this post?” in a sheet's paper (“Sign"
                  " in, and it’s kept for you on your page, where only you can see it.”), Not now | Sign in, focus on Not"
                  " now, the ⋯ gone down: on a post's page (a phone) and a profile's card (a desk)",
                  all(o["first"] == ["Bookmark"] and o["sheet"] and o["sheet"]["open"] and not o["sheet"]["menu"]
                      and o["sheet"]["title"] == "Bookmark this post?"
                      and o["sheet"]["lede"] == "Sign in, and it’s kept for you on your page, where only you can see it."
                      and o["sheet"]["buttons"] == ["Not now", "Sign in"] and o["sheet"]["focus"] == "Not now"
                      for o in outs.values()) and len(outs) == 2,
                  json.dumps(outs)[:800])
            check("Sign in comes back to the page it was asked from; Not now closes the sheet and gives the ⋯ its focus"
                  " back; nothing is kept for anybody",
                  len(outs) == 2 and all(o["sheet"] and o["sheet"]["open"] and o["sheet"]["signin"] == nxt(o["path"])
                                         and not o["back"]["open"] and o["back"]["focus"] for o in outs.values())
                  and after == before,
                  f"{[(o['sheet'] or {}).get('signin') for o in outs.values()]} want {[nxt(o['path']) for o in outs.values()]};"
                  f" back {[o['back'] for o in outs.values()]}; kept {before} -> {after}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "nobody is told and nothing counts them: no Activity row, no dot, no number in any page"):
        try:
            rae = someone(b, "rae", "Rae Ueda")
            sam = someone(b, "sam", "Sam Voss")
            tia = someone(b, "tia", "Tia West")
            p5 = make_post(rae, "Section 5, Rae's")
            d5 = make_drawing(rae, "Section 5, Rae's drawing", seed=51)
            rc = rae.client()
            st_a, act0 = rc.get("/social/activity")
            rows0 = act0.count('class="act-row')
            mark(sam, ("p", p5))
            mark(tia, ("p", p5))
            mark(sam, ("s", d5))
            st_b, act1 = rc.get("/social/activity")
            _, home1 = rc.get("/social/")
            srcs = {}
            for name, cl in (("Rae, its maker", rae.client()), ("Sam, who kept it", sam.client()),
                             ("Tia, who kept it", tia.client()), ("nobody", Client())):
                for path in (f"/social/p/{p5}", f"/social/b/{d5}", "/social/@rae"):
                    srcs[(name, path)] = cl.get(path)[1]
            def counted(src):
                txt = re.sub(r"<[^>]+>", " ", src)
                return re.findall(r"\d+\s+(?:bookmark|save)s?\b|bookmark(?:ed)?\s+by\b|\bdata-bookmarks?=", txt + " " + src, re.I)
            counts = {f"{k[0]} {k[1]}": counted(v) for k, v in srcs.items() if counted(v)}
            marked_in = {f"{k[0]} {k[1]}": v.count("data-marked") for k, v in srcs.items()}
            mine_only = all(n == 0 for (who, path), n in ((k, srcs[k].count("data-marked")) for k in srcs)
                            if who in ("Rae, its maker", "nobody")) and all(
                srcs[(w, f"/social/p/{p5}")].count("data-marked") == 1 for w in ("Sam, who kept it", "Tia, who kept it"))
            check("nobody is told: the maker's Activity holds no row more for it (posts and drawings kept by two people)"
                  " and the bell wears no dot",
                  st_a == 200 and st_b == 200 and act1.count('class="act-row') == rows0 and "act-dot" not in home1,
                  f"rows {rows0} -> {act1.count('class=\"act-row')}; dot {'act-dot' in home1}")
            check("nothing counts them: no page says how many, to its maker, the two who kept it, anybody else or nobody"
                  " (its page, the drawing's, the maker's profile); each page says only whether it is the viewer's own"
                  " (Sam's and Tia's, theirs; the maker's and nobody's, nothing)",
                  not counts and mine_only, f"counts {counts}; marked {marked_in}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "your Bookmarks: newest kept first, posts and drawings, Load more; hidden, never deleted; the muted kept"):
        try:
            bea = someone(b, "bea", "Bea Young")
            dov = someone(b, "dov", "Dov Abel")
            eli = someone(b, "eli", "Eli Banks")
            fay = someone(b, "fay", "Fay Cole")
            gus = someone(b, "gus", "Gus Dunn")
            hal = someone(b, "hal", "Hal Ekman")
            ivy = someone(b, "ivy", "Ivy Ford")
            pa = make_post(dov, "Section 6, Dov's")
            pt = make_post(dov, "Section 6, Dov's, to be taken down")
            pb = make_post(hal, "Section 6, Hal's (muted)")
            pe = make_post(eli, "Section 6, Eli's (Bea blocks him)")
            pf = make_post(fay, "Section 6, Fay's (she blocks Bea)")
            pg_ = make_post(gus, "Section 6, Gus's (taken down)")
            po = make_post(bea, "Section 6, Bea's own, taken down")
            dd = make_drawing(ivy, "Section 6, Ivy's drawing", seed=61)
            dl = make_drawing(ivy, "Section 6, Ivy's, made link-only", seed=62)
            dx = make_drawing(ivy, "Section 6, Ivy's, deleted in Skribl", seed=63)
            order = [("p", po), ("s", dd), ("p", pb), ("p", pa), ("p", pe), ("p", pf), ("p", pg_), ("p", pt),
                     ("s", dl), ("s", dx)]
            kept = [mark(bea, on)[0] for on in order]
            # Their moments, newest first in the order above, a minute apart,
            # written as the site writes a time (its microseconds too).
            for i, (kind, oid) in enumerate(order):
                when = f"2026-11-14 12:{59 - i:02d}:00.000000"
                if kind == "p":
                    db_write("update social_bookmarks set created_at = ? where post_id = (select id from social_posts"
                             " where public_id = ?) and person_id = (select id from social_people where handle_key = 'bea')",
                             (when, oid))
                else:
                    db_write("update social_bookmarks set created_at = ? where drawing_id = ? and person_id ="
                             " (select id from social_people where handle_key = 'bea')", (when, oid))
            db_write("update social_posts set taken_down_at = datetime('now') where public_id in (?, ?)", (pt, po))
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'gus'")
            block(bea, "eli")
            block(fay, "bea")
            mc = bea.client()
            mc.get("/social/@hal")
            mc.post_json("/social/@hal/mute", {})
            # Ivy hides one from the Gallery (link-only) and deletes another in
            # Skribl's own Library, not through the site: their rows stay.
            ic_ = ivy.client()
            ic_.get(f"/social/b/{dl}")
            st_l, _ = ic_.post_json(f"/social/b/{dl}/gallery", {"gallery": False})
            ivy.pg.goto(BASE + "/social/")
            st_x = ivy.pg.evaluate("""async (id) => { await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
              const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
              const r = await fetch('/api/skribls/' + id, { method: 'DELETE', credentials: 'same-origin',
                headers: { 'X-Skribl-CSRF': decodeURIComponent(tok) } }); return r.status; }""", dx)
            ctx, pg = browser_as(b, bea, screen="phone")
            go(pg, "/social/@bea/bookmarks", wait=500)
            got = pg.evaluate(PANEL)
            close_ctx(ctx, pg)
            want = [po, "b-" + dd, pb, pa]
            check("your Bookmarks, on your own page's tab: what you kept as Home's cards, posts and a drawing shown"
                  " outside a post (its card opening its own page), newest kept first",
                  kept == [200] * 10 and got and got["tab"] == "bookmarks" and got["chosen"] == "bookmarks"
                  and got["ids"] == want and got["urls"][1] == f"/social/b/{dd}" and got["marked"] == len(want)
                  and got["heading"] == "Your bookmarks",
                  f"kept {kept}; got {got and got['ids']} want {want}; urls {got and got['urls']}; marked"
                  f" {got and got['marked']}; heading {got and got['heading']}")
            left = db("select count(*) from social_bookmarks where person_id = (select id from social_people where"
                      " handle_key = 'bea')")[0][0]
            check("hidden, never deleted: a post by somebody you blocked and by somebody who blocked you, by somebody"
                  " taken down, a post taken down, a drawing made link-only and one deleted in Skribl are not in it,"
                  " and their bookmarks are still kept; your own post taken down is, with its note",
                  got and not ({pe, pf, pg_, pt, "b-" + dl, "b-" + dx} & set(got["ids"])) and left == 10
                  and got["notes"] == [po] and st_l == 200 and st_x in (200, 204),
                  f"ids {got and got['ids']}; kept {left}; notes {got and got['notes']}; link-only {st_l}; deleted {st_x}")
            check("somebody you muted stays: you chose it (Hal's post is there)", got and pb in got["ids"],
                  json.dumps(got and got["ids"]))
            # LOAD MORE: twenty-three kept, twenty a page.
            joy = someone(b, "joy", "Joy Grant")
            many = [make_post(dov, f"Section 6, Dov's {i}", seed=600 + i) for i in range(23)]
            for i, pid in enumerate(many):
                mark(joy, ("p", pid))
                db_write("update social_bookmarks set created_at = ? where post_id = (select id from social_posts"
                         " where public_id = ?) and person_id = (select id from social_people where handle_key = 'joy')",
                         (f"2026-11-14 10:{i:02d}:00.000000", pid))
            ctx, pg = browser_as(b, joy, screen="desk")
            go(pg, "/social/@joy/bookmarks", wait=500)
            first = pg.evaluate(PANEL)
            # Load more, when there is one to press (none is the row's own red).
            if first and first["more"]:
                pg.click("[data-prof-next]")
                try:
                    pg.wait_for_function("() => document.querySelectorAll('[data-prof-list] > .post-card').length > 20",
                                         timeout=10000)
                except Exception:  # noqa: BLE001 -- nothing more come is the row's red
                    pass
                pg.wait_for_timeout(300)
            second = pg.evaluate(PANEL)
            close_ctx(ctx, pg)
            check("Load more: twenty a page, then the rest in place, newest kept first, none twice, then no Load more",
                  first and first["ids"] == list(reversed(many))[:20] and first["more"]
                  and second["ids"] == list(reversed(many)) and not second["more"],
                  f"first {len(first['ids']) if first else None} more {first and first['more']}; then"
                  f" {len(second['ids']) if second else None} more {second and second['more']}")
            kit = someone(b, "kit", "Kit Hale")
            ctx, pg = browser_as(b, kit)
            go(pg, "/social/@kit/bookmarks")
            empty = pg.evaluate(PANEL)
            close_ctx(ctx, pg)
            check("with nothing kept, the tab's own words: “Nothing bookmarked yet. Tap ⋯ on a post you want to come back"
                  " to, then Bookmark, and it’s kept here. Only you can see your bookmarks.”, and its heading for a"
                  " screen reader, “Your bookmarks”",
                  empty and empty["ids"] == [] and empty["none"] == ("Nothing bookmarked yet. Tap ⋯ on a post you want to"
                                                                     " come back to, then Bookmark, and it’s kept here."
                                                                     " Only you can see your bookmarks.")
                  and empty["heading"] == "Your bookmarks" and not empty["more"],
                  json.dumps(empty))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "deleting takes the bookmarks, in code: a post, a drawing, an account"):
        try:
            ora = someone(b, "ora", "Ora Penn")
            pip = someone(b, "pip", "Pip Rand")
            p7 = make_post(ora, "Section 7, Ora's")
            d7 = make_drawing(ora, "Section 7, Ora's drawing", seed=71)
            mark(pip, ("p", p7))
            mark(ora, ("p", p7))
            mark(pip, ("s", d7))
            c = ora.client()
            c.get(f"/social/p/{p7}")
            sd, _ = c.post_json(f"/social/p/{p7}/delete", {})
            c.get(f"/social/b/{d7}")
            sdd, _ = c.post_json(f"/social/b/{d7}/delete", {})
            left7 = db("select post_id, drawing_id from social_bookmarks where owner_id = (select id from social_people"
                       " where handle_key = 'ora')")
            check("a post deleted through its ⋯ goes with its bookmarks, and a drawing deleted from its own page with"
                  " its bookmarks (a drawing's have no cascade under them: only the code takes them)",
                  sd == 200 and sdd == 200 and left7 == [] and marks_on(("s", d7)) == [], f"{sd} {sdd}; left {left7}")
            qua = someone(b, "qua", "Qua Senn")
            rex = someone(b, "rex", "Rex Tam")
            p7b = make_post(rex, "Section 7, Rex's")
            p7c = make_post(qua, "Section 7, Qua's")
            mark(qua, ("p", p7b))
            mark(rex, ("p", p7c))
            c = qua.client()
            c.get("/social/you/delete")
            st, _ = c.post_form("/social/you/delete", {"confirm": "qua"})
            orphans = db("select count(*) from social_bookmarks k where k.person_id not in (select id from social_people)"
                         " or k.owner_id not in (select id from social_people)")
            check("an account deleted goes with its bookmarks and every bookmark on what it made",
                  st == 200 and orphans == [(0,)] and marks_on(("p", p7b)) == [], f"{st}; orphans {orphans}")
            # With the cascade off, on a copy: the code alone.
            sly = someone(b, "sly", "Sly Uhl")
            tex = someone(b, "tex", "Tex Vo")
            p7d = make_post(sly, "Section 7, Sly's")
            p7e = make_post(tex, "Section 7, Tex's")
            d7t = make_drawing(tex, "Section 7, Tex's drawing", seed=72)
            d7s = make_drawing(sly, "Section 7, Sly's drawing", seed=73)
            mark(tex, ("p", p7d))
            mark(sly, ("p", p7d))
            mark(sly, ("p", p7e))        # theirs, on what somebody else made
            mark(sly, ("s", d7t))        # theirs, on a drawing no post takes with it
            mark(tex, ("s", d7s))        # on what they made that no post takes with it
            copy = os.path.join(TMP, "probe.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            home_as = "; ".join(f"{c['name']}={c['value']}" for c in sly.ctx.cookies(BASE))
            probe = subprocess.run([sys.executable, "-c", PROBE, p7d, "sly", "sly", home_as], cwd=ROOT, capture_output=True,
                                   text=True, timeout=180,
                                   env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out7 = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out7 = {"err": (probe.stderr or probe.stdout)[-600:]}
            PROBED = out7
            check("with SQLite's cascade off (SKRIBL_SQLITE_FOREIGN_KEYS=0, on a copy) a post goes with its bookmarks,"
                  " by the code (posts.drop_post)",
                  out7.get("fk") == 0 and out7.get("post") == [2, 0],
                  json.dumps({k: v for k, v in out7.items() if k != "plans"})[:400])
            check("...and an account with its bookmarks (one on somebody else's post, one on somebody's drawing) and"
                  " every bookmark on what it made (one on a drawing no post takes with it), by the code"
                  " (accounts.delete_person)",
                  bool(out7.get("person")) and out7["person"][0] >= 2 and out7["person"][1] >= 1 and out7["person"][2:] == [0, 0],
                  json.dumps(out7.get("person") or out7.get("err")))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "the data: the chain on a populated database; one a person a thing; the reads on their indexes"):
        try:
            mdb = os.path.join(TMP, "chain-bookmarks.db")
            # The chain's head before bookmarks (their migration's
            # down_revision), and the bookmarks' own migration.
            BEFORE, MARKS = "9b1e6c3d5a72", "224902330f2a"

            def chain(*args):
                return subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", *args], cwd=ROOT,
                                      env=dict(os.environ, DATABASE_URL=f"sqlite:///{mdb}"), capture_output=True,
                                      text=True, timeout=180)

            def at(sql, args=()):
                con = sqlite3.connect(mdb)
                try:
                    return con.execute(sql, args).fetchall()
                finally:
                    con.close()

            up1 = chain("upgrade", BEFORE)
            con = sqlite3.connect(mdb)
            then = "2026-11-14 10:00:00"
            for i, h in ((1, "ann"), (2, "bob")):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle,"
                            " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                            (i, "site:" + h, h, h, h.title(), bytes([i]) * 32, then, then))
            con.execute("insert into social_posts (id, public_id, person_id, words, skribl_id, created_at)"
                        " values (10, 'P1', 1, 'hi', 'S1', ?)", (then,))
            con.execute("insert into social_likes (post_id, owner_id, person_id, created_at) values (10, 1, 2, ?)", (then,))
            con.commit()
            con.close()
            others = lambda: (at("select * from social_people order by id"), at("select * from social_posts"),
                              at("select * from social_likes"))
            was = others()
            up2 = chain("upgrade", MARKS)
            # At its own revision (the reposts' migration follows it since Nov 14):
            # what the chain stamps, not the chain's head.
            heads = [r[0] for r in at("select version_num from social_alembic_version")]
            idx = {r[0]: r[1] for r in at("select name, sql from sqlite_master where type = 'index' and tbl_name = 'social_bookmarks'")}
            cols = [r[1] for r in at("pragma table_info(social_bookmarks)")]
            sql = (at("select sql from sqlite_master where name = 'social_bookmarks'") or [[""]])[0][0] or ""
            want_idx = {"ix_social_bookmarks_person_post": "(person_id, post_id)",
                        "ix_social_bookmarks_person_drawing": "(person_id, drawing_id)",
                        "ix_social_bookmarks_person_created": "(person_id, created_at)",
                        "ix_social_bookmarks_post_id": "(post_id)", "ix_social_bookmarks_drawing_id": "(drawing_id)",
                        "ix_social_bookmarks_owner_id": "(owner_id)"}
            idx_ok = set(idx) == set(want_idx) and all(want_idx[n] in (idx[n] or "") for n in want_idx) and \
                "UNIQUE" in (idx.get("ix_social_bookmarks_person_post") or "") and \
                "UNIQUE" in (idx.get("ix_social_bookmarks_person_drawing") or "")
            check("the site's chain on a database with people, posts and likes in it adds social_bookmarks (on a post or a"
                  " drawing, whose, who, when), its six indexes (once a person a thing, yours newest first, a post's, a"
                  " drawing's, whose) and its CHECK, at its own revision, touching nothing else",
                  up1.returncode == 0 and up2.returncode == 0 and heads == [MARKS]
                  and cols == ["id", "post_id", "drawing_id", "owner_id", "person_id", "created_at"] and idx_ok
                  and "ck_social_bookmarks_on_one" in sql and "ON DELETE CASCADE" in sql and others() == was,
                  f"{up1.returncode} {up2.returncode} heads {heads}; cols {cols}; idx {sorted(idx)}; check"
                  f" {'ck_social_bookmarks_on_one' in sql}; untouched {others() == was}")
            con = sqlite3.connect(mdb)
            con.execute("insert into social_bookmarks (post_id, owner_id, person_id, created_at) values (10, 1, 2, ?)", (then,))
            con.commit()
            refused = []
            for name, q in (("the same post again", "insert into social_bookmarks (post_id, owner_id, person_id, created_at) values (10, 1, 2, '2026-11-14')"),
                            ("on nothing", "insert into social_bookmarks (owner_id, person_id, created_at) values (1, 2, '2026-11-14')"),
                            ("on both", "insert into social_bookmarks (post_id, drawing_id, owner_id, person_id, created_at) values (10, 'S9', 1, 2, '2026-11-14')")):
                try:
                    con.execute(q)
                    refused.append((name, False))
                except sqlite3.IntegrityError:
                    refused.append((name, True))
            con.execute("insert into social_bookmarks (drawing_id, owner_id, person_id, created_at) values ('S2', 1, 2, ?)", (then,))
            try:
                con.execute("insert into social_bookmarks (drawing_id, owner_id, person_id, created_at) values ('S2', 1, 2, ?)", (then,))
                refused.append(("the same drawing again", False))
            except sqlite3.IntegrityError:
                refused.append(("the same drawing again", True))
            con.rollback()
            con.close()
            down = chain("downgrade", BEFORE)
            gone = at("select name from sqlite_master where name like 'social_bookmarks%' or name like 'ix_social_bookmarks%'")
            check("one bookmark a person a thing (a post's, a drawing's), on exactly one thing (never nothing, never"
                  " both); and back down, the table and its indexes gone, nothing else touched",
                  all(ok for _, ok in refused) and len(refused) == 4 and down.returncode == 0 and gone == []
                  and others() == was,
                  f"{refused}; down {down.returncode} left {gone}")
            # The reads, as the code makes them, planned by SQLite (section 7's
            # probe, on a copy of this suite's own database).
            if "PROBED" not in globals():
                sly = someone(b, "sly8", "Sly Eight")
                tex = someone(b, "tex8", "Tex Eight")
                p8 = make_post(sly, "Section 8, Sly's")
                p8b = make_post(tex, "Section 8, Tex's")
                mark(sly, ("p", p8b))
                mark(tex, ("p", p8))
                copy = os.path.join(TMP, "probe8.db")
                src = sqlite3.connect(DB, timeout=10)
                dst = sqlite3.connect(copy)
                src.backup(dst)
                src.close()
                dst.close()
                home_as = "; ".join(f"{c['name']}={c['value']}" for c in sly.ctx.cookies(BASE))
                probe = subprocess.run([sys.executable, "-c", PROBE, p8, "sly8", "sly8", home_as], cwd=ROOT,
                                       capture_output=True, text=True, timeout=180,
                                       env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
                try:
                    PROBED = json.loads(probe.stdout.strip().splitlines()[-1])
                except Exception:  # noqa: BLE001
                    PROBED = {"err": (probe.stderr or probe.stdout)[-600:]}
            plans = PROBED.get("plans") or {}
            listed = " | ".join(plans.get("list", []))
            asked = " | ".join(plans.get("marked", []))
            check("the reads on their indexes, as SQLite plans them: your Bookmarks on yours, newest first"
                  " (ix_social_bookmarks_person_created), and which of a page's cards are yours on the pair's"
                  " (ix_social_bookmarks_person_post, _person_drawing), one read a kind",
                  "ix_social_bookmarks_person_created" in listed and "ix_social_bookmarks_person_post" in asked
                  and "ix_social_bookmarks_person_drawing" in asked and (PROBED.get("sent") or {}).get("list") == 1
                  and (PROBED.get("sent") or {}).get("marked") == 2,
                  json.dumps({"plans": plans, "sent": PROBED.get("sent"), "err": PROBED.get("err")})[:700])
            check("a page of Home's cards asks which are yours once, whatever how many",
                  (PROBED.get("cards") or 0) >= 2 and PROBED.get("reads") == ["SELECT"],
                  json.dumps({"cards": PROBED.get("cards"), "reads": PROBED.get("reads")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "contrast and targets: the ribbon off the paint; every word at 4.5:1; every target 44px"):
        try:
            uma = someone(b, "uma", "Uma Ilse")
            val = someone(b, "val", "Val Jory")
            p9 = make_post(uma, "Section 9, Uma's, kept")
            p9b = make_post(uma, "Section 9, Uma's, not kept")
            mark(val, ("p", p9))
            paints, lows, smalls, reads = {}, [], [], {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    got = []
                    ctx, pg = browser_as(b, val, screen=screen, scheme=scheme)
                    go(pg, f"/social/p/{p9}")
                    open_sheet(pg, PAGE_MENU)
                    paints[(tag, "filled")] = ribbon_paint(pg, "#postSheet [data-act=bookmark]")
                    got.append(("the ⋯, Remove bookmark", pg.evaluate(READ, "#postSheet")))
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(500)
                    go(pg, f"/social/p/{p9b}")
                    open_sheet(pg, PAGE_MENU)
                    paints[(tag, "empty")] = ribbon_paint(pg, "#postSheet [data-act=bookmark]")
                    got.append(("the ⋯, Bookmark", pg.evaluate(READ, "#postSheet")))
                    press_mark(pg, after=1100)
                    paints[(tag, "the toast's")] = ribbon_paint(pg, ".mu-toast")
                    # Its words take no tap (a tap reaches the page under
                    # them), so the census, which asks what is painted where
                    # a word is, reads them made hit-testable for the moment.
                    pg.evaluate("() => document.querySelectorAll('.mu-toast, .mu-toast *').forEach(e => e.style.pointerEvents = 'auto')")
                    got.append(("the toast", pg.evaluate(READ, ".mu-toasts")))
                    pg.evaluate("() => document.querySelectorAll('.mu-toast, .mu-toast *').forEach(e => e.style.pointerEvents = '')")
                    press_mark(pg, ".mu-toast [data-mute-undo]", after=400)
                    go(pg, "/social/@val/bookmarks", wait=500)
                    got.append(("your Bookmarks", pg.evaluate(READ)))
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, uma, screen=screen, scheme=scheme)
                    go(pg, "/social/@uma/bookmarks")
                    got.append(("your Bookmarks, empty", pg.evaluate(READ)))
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, None, screen=screen, scheme=scheme)
                    go(pg, f"/social/p/{p9}")
                    open_sheet(pg, PAGE_MENU)
                    press(pg, "#postSheet [data-act=bookmark]")
                    pg.wait_for_timeout(800)
                    got.append(("the signed-out sheet", pg.evaluate(READ, "#bookmarkOutSheet")))
                    close_ctx(ctx, pg)
                    reads[tag] = [(w, r["read"], r["lowest"]) for w, r in got]
                    lows += [f"{tag} {w}: {x}" for w, r in got for x in r["low"]]
                    smalls += [f"{tag} {w}: {x}" for w, r in got for x in r["small"]]
                    check(f"every word at 4.5:1 or more on what is painted behind it, {tag}: the ⋯ (Bookmark, and"
                          " Remove bookmark), the toast, your Bookmarks full and empty, the signed-out sheet",
                          all(r["read"] > 0 for _, r in got) and not any(r["low"] for _, r in got)
                          and dict((w, n) for w, n, _ in reads[tag]).get("the toast") == 2,
                          f"read {reads[tag]}; low {[x for _, r in got for x in r['low']][:3]}")
            check("every target 44px or more, on all of them", not smalls, f"small {smalls[:4]}")
            weak = {f"{k[0]} {k[1]}": v for k, v in paints.items() if not v or v["best"] < 3
                    or (k[1] == "filled" and v["mid_k"] < 3) or (k[1] == "empty" and v["mid_k"] > 1.2)}
            check("the ribbon read off the paint, 3:1 or more on what is painted behind it, phone and desk, light and"
                  " dark: filled (Remove bookmark), its inside too; empty (Bookmark), its inside the row's own ground;"
                  " and the toast's",
                  len(paints) == 12 and not weak,
                  json.dumps({f"{k[0]} {k[1]}": v and [v["best"], v["mid_k"]] for k, v in paints.items()})[:700])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
