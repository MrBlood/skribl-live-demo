#!/usr/bin/env python3
"""Draw back at /social (the owner's "All yes", Nov 19, to the Draw back
mock; DECISIONS.md, "Draw back, mocked"): answering a drawing by drawing
with it. Its own server and database, people who joined through invites,
each in a browser with a virtual passkey.

  1. THE JOIN, ON THE SERVER: a draw-back's drawing is the original's
     strokes first, as they play, squeezed to about three seconds when longer,
     then the answer's at its own pace; on the original's shape and ground,
     the answer's pause rule; its row says what it draws back on and whose.
     A long original is squeezed; a short one plays as it is.
  2. WHAT IS REFUSED: an answer drawn on another shape, a Flip of more than
     one page, a drawing on a photo, one that is gone or behind a block, a
     draw-back beside a quote; signed out the original is not handed over;
     the route hands the composer the original, as Skribl serves it.
  3. THE CARD: the pen after the heart, 44px to a finger, "Draw back" and
     how many; none signed out, none on a Flip, none on a drawing made on a
     photo (the post's `undrawable`, read when it was posted); a draw-back's
     own card has one (a jam); a draw-back's card says
     "Drew back on Ana’s" (her post the link, 44px tall), her face small at
     the foot of his; once her post is gone, "Drew back on a drawing".
  4. THE WHOLE WAY, IN A BROWSER: the pen opens the composer and the Pad
     over it, on her shape and paper, her drawing faint under the pen in its
     own colours (painted where her strokes are, laid down at 0.32), the
     pill "Drawing back on Ana’s"; Theirs goes faint, full, hidden and round
     again; drawn, Done, Add and Post land on the new post, whose drawing
     holds hers and then his.
  5. ACTIVITY: "Theo drew back on your drawing", new, his words, Draw
     back's pen on his face, opening his draw-back; none from somebody she
     muted, none of her own; the nudge's words, under Replies.
  6. HER POST'S STRIP: "3 draw-backs", newest first, each its drawing and
     who, opening its page; behind a block, not on the strip.
  7. WHEN A REPLAY ENDS: "Watch again" and "Draw back" in the drawing's own
     box, 12px above its foot, 44px, the box's replay mark aside; Watch
     again plays it and they go; Draw back opens the composer on hers.
  9. No page errors, no console errors and no CSP violations.

SOCIALDRAWBACK_PART=<n>[,<m>] runs those sections only (calibration). Every
row was shown red by breaking one part and green as built: DECISIONS.md,
"Draw back, step 1".
"""
import base64
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "harness" / "tools"))
PART = os.environ.get("SOCIALDRAWBACK_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALDRAWBACK {n} — {label}")
    return True


def steps(fn):
    """A row's steps: (what they gave, None), or ({}, what stopped them), so a
    control that is not there fails its own row and the next row still runs."""
    try:
        return fn(), None
    except Exception as exc:  # noqa: BLE001
        return {}, (str(exc).splitlines() or [repr(exc)])[0][:160]


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a sheet
    that never rose) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence Draw back works.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)


import artdraw  # noqa: E402  -- a real pen in the real Pad (harness/tools)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialdrawback-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialdrawback-" + secrets.token_hex(8),
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

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{80 + _addr[0] // 250}.{_addr[0] % 250}.9"


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


def drawing(n=40, seed=0, size=(816, 612)):
    """A small drawing, as the Pad's Add hands one back."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * 30, "start": i == 0} for i in range(n)]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay",
            "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """The site's own requests, without a browser, as a signed-in person."""

    def __init__(self, cookies=None, xff=None, origin=BASE):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), _NoRedirect())
        self.xff = xff or address()
        self.origin = origin
        self.token = None
        self.cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in (cookies or []))

    def _req(self, method, path, body=None, headers=None, raw=None):
        h = {"X-Forwarded-For": self.xff}
        if self.cookie_header:
            h["Cookie"] = self.cookie_header
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if raw is not None:
            data = raw
            h["Content-Type"] = "application/json"
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

    def get_json(self, path):
        st, text = self._req("GET", path)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_json(self, path, body, token=True, raw=None):
        h = {"X-Social-CSRF": self.token} if token is True else ({"X-Social-CSRF": token} if token else {})
        st, text = self._req("POST", path, body=body, headers=h, raw=raw)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text


class Person:
    """One browser with its own passkey, from an address of its own."""

    def __init__(self, b, screen="phone", scheme="light", reduced=False):
        self.xff = address()
        kw = {"reduced_motion": "reduce"} if reduced else {}
        self.ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": self.xff},
                                 **(PHONE if screen == "phone" else DESK), **kw)
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


def browser_as(b, who, screen="phone", scheme="light", reduced=False):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **(PHONE if screen == "phone" else DESK), **kw)
    ctx.add_init_script(WATCH)
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


def member(b, handle, name, **kw):
    """Somebody who joined through an invite (the first through the first
    invite code), signed in, in a browser of their own."""
    p = Person(b, **kw)
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


def someone(b, handle, name, **kw):
    return _people.get(handle) or member(b, handle, name, **kw)


def admin(b):
    """The run's admin: the first person it made (the site makes its first
    person its admin), or Juno when it has made nobody yet."""
    got = db("select handle from social_people where is_admin order by id limit 1")
    if got:
        return _people[got[0][0]]
    return someone(b, "juno", "Juno Park")


def make_post(who, words, seed=0):
    """A post as Home's composer sends one: its public id, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def say(who, post, words, answer_to=None):
    """A comment (or an answer) as the box sends one: (status, answer)."""
    c = who.client()
    c.get(f"/social/p/{post}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    return c.post_json(f"/social/p/{post}/comments", body)


def said(who, post, words, answer_to=None):
    st, j = say(who, post, words, answer_to)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def pid_of(handle):
    got = db("select id, public_id from social_people where handle_key = ?", (handle.lower(),))
    return got[0] if got else (None, None)


def post_id(public_id):
    got = db("select id from social_posts where public_id = ?", (public_id,))
    return got[0][0] if got else None


def status(pg, path):
    r = pg.goto(BASE + path)
    pg.wait_for_timeout(300)
    return r.status if r else None


def ready(pg):
    pg.wait_for_function("() => !!window.SocialSheet && !!window.SocialWhen && document.readyState === 'complete'",
                         timeout=15000)


def open_post(pg, post):
    pg.goto(BASE + f"/social/p/{post}")
    ready(pg)
    pg.wait_for_timeout(300)


# ---- a drawing shown outside a post (sections 20 to 28) --------------------------
# A drawing posted from the Pad on its own page (Make's Draw), as the Pad posts
# it: Skribl's API, as the person signed in, its own token from its own cookie
# (verify_socialposts section 9's).
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
# Deleted in the Library, as its author: Skribl's own DELETE, not the site's.
LIBRARY_DELETE = """async (id) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const r = await fetch('/api/skribls/' + id, { method: 'DELETE', credentials: 'same-origin',
    headers: { 'X-Skribl-CSRF': decodeURIComponent(tok) } });
  return r.status; }"""


def make_drawing(who, title, seed=0, vis="public"):
    """A drawing from the Pad, shown in the gallery: its skribl's public id, or None."""
    who.pg.goto(BASE + "/social/")
    st, sid = who.pg.evaluate(PAD, [title, vis, seed])
    return sid if st == 201 else None


def say_on(who, sid, words, answer_to=None, payload=None):
    """A comment on a drawing (or an answer, or a drawing answer) as the box
    sends one: (status, answer)."""
    c = who.client()
    c.get(f"/social/b/{sid}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    if payload is not None:
        body["payload"] = payload
    return c.post_json(f"/social/b/{sid}/comments", body)


def said_on(who, sid, words, answer_to=None, payload=None):
    st, j = say_on(who, sid, words, answer_to, payload)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def open_drawing(pg, sid):
    pg.goto(BASE + f"/social/b/{sid}")
    ready(pg)
    pg.wait_for_timeout(300)


def on_row(cid):
    """What a comment's row says it is on: (post_id, drawing_id, owner's handle, parent's public id)."""
    got = db("select c.post_id, c.drawing_id, o.handle, p.public_id from social_comments c"
             " join social_people o on o.id = c.owner_id left join social_comments p on p.id = c.parent_id"
             " where c.public_id = ?", (cid or "",))
    return got[0] if got else None



# ---- draw back's own -------------------------------------------------------------
CAT = json.loads((ROOT / "skribl/static/help/demos/cat.json").read_text())
# A 1x1 PNG, for a drawing on a photo.
PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAA"
       "AABJRU5ErkJggg==")


def answer(n=30, seed=3, size=(816, 612)):
    """The strokes an answer hands back: the Pad's drawing, on the original's shape."""
    d = drawing(n=n, seed=seed, size=size)
    d["frames"][0]["background"] = {"color": "#f6f2ea"}
    return d


def post_payload(who, words, payload):
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": payload})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def draw_back(who, on, payload, **extra):
    """A draw-back as the composer sends one: (status, answer)."""
    c = who.client()
    c.get("/social/")
    return c.post_json("/social/posts", dict({"words": "", "payload": payload, "draw_back": on}, **extra))


def stored(post):
    """A post's row (is_drawback, drawn_on_id, drawn_on_owner_id) and its drawing as Skribl stored it."""
    got = db("select p.is_drawback, p.drawn_on_id, p.drawn_on_owner_id, s.payload_json from social_posts p"
             " left join skribl_posts s on s.public_id = p.skribl_id where p.public_id = ?", (post or "",))
    if not got:
        return None
    r = got[0]
    return {"is_drawback": bool(r[0]), "on": r[1], "owner": r[2], "payload": json.loads(r[3]) if r[3] else None}


def played(points, cap=50):
    out, at = [], 0
    for i, p in enumerate(points):
        if i:
            g = p["t"] - points[i - 1]["t"]
            if g > 0:
                at += g if cap is None else min(g, cap)
        out.append(at)
    return out


def xy(points):
    return [(round(p["x"], 2), round(p["y"], 2)) for p in points]


# The card's pen, its credit and its faces, as `pg` sees the card for `post`.
CARD = """(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'); if (!c) return null;
  c.scrollIntoView({ block: 'center' });
  const row = c.querySelector('.post-row'), pen = row.querySelector('.db-pen');
  const kids = [...row.children].map(e => e.classList.contains('db-pen') ? 'pen' : e.classList.contains('post-count') ? 'comment'
    : e.classList.contains('rp-btn') ? 'repost' : e.classList.contains('lk-heart') ? 'heart' : e.classList.contains('post-more') ? 'more' : e.className);
  const on = c.querySelector('.post-on'), who = on && on.querySelector('.post-on-who');
  const r = pen && pen.getBoundingClientRect(), wr = who && who.getBoundingClientRect();
  const at = r && document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return { kids, pen: pen ? { w: r.width, h: r.height, label: pen.getAttribute('aria-label'), icon: !!pen.querySelector('svg'),
                              hit: !!at && pen.contains(at), n: (pen.querySelector('span') || {}).textContent || null } : null,
           on: on ? on.textContent.replace(/\\s+/g, ' ').trim() : null,
           who: who ? { href: new URL(who.href).pathname, h: wr.height,
                        hit: (() => { const e = document.elementFromPoint(wr.left + wr.width / 2, wr.top + wr.height / 2); return !!e && who.contains(e); })() } : null,
           face: !!c.querySelector('.post-face .db-face .face-ring') }; }"""


def home(pg):
    pg.goto(BASE + "/social/?tab=everyone")
    ready(pg)
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the join, on the server: hers first, squeezed; his at his pace; her shape and ground"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            cat = post_payload(ana, "Section 1, the cat", CAT)
            mine = answer(n=30, seed=3)
            st, j = draw_back(theo, cat, mine)
            back = j.get("post") if isinstance(j, dict) else None
            row, orig = stored(back), stored(cat)
            pts = (((row or {}).get("payload") or {}).get("frames") or [{}])[0].get("strokes") or []
            ops, aps = CAT["frames"][0]["strokes"], mine["frames"][0]["strokes"]
            head, tail = pts[:len(ops)], pts[len(ops):]
            total = played(ops, 50)[-1]
            want = [round(t * 3000 / total) for t in played(ops, 50)]
            check("a draw-back's drawing is hers, then his: her 726 points first in her order, then his 30 in his",
                  st == 200 and len(pts) == len(ops) + len(aps) and xy(head) == xy(ops) and xy(tail) == xy(aps),
                  f"status {st} {j if st != 200 else ''}; {len(pts)} points")
            check("hers plays first, squeezed to three seconds (she plays for %.1fs as she drew it): each of her points"
                  " at its played time, scaled" % (total / 1000),
                  total > 3000 and [q["t"] for q in head] == want and head[-1]["t"] == 3000,
                  f"last of hers at {head[-1]['t'] if head else None}; first five {[q['t'] for q in head[:5]]} want {want[:5]}")
            gaps = [b_["t"] - a_["t"] for a_, b_ in zip(aps, aps[1:])]
            check("...then his at his own pace, one beat (50ms) after her last point, every gap his own, his first a pen-down",
                  tail and tail[0]["t"] == head[-1]["t"] + 50 and [b_["t"] - a_["t"] for a_, b_ in zip(tail, tail[1:])] == gaps
                  and tail[0].get("start") is True,
                  f"his first at {tail[0]['t'] if tail else None}; gaps {[b_['t'] - a_['t'] for a_, b_ in zip(tail, tail[1:])][:4]}")
            pl = (row or {}).get("payload") or {}
            of = ((orig or {}).get("payload") or {}).get("frames", [{}])[0]
            check("on her shape and her ground (as Skribl stored hers), with his pause rule; her takes, then his",
                  pl.get("canvasSize", {}).get("cssWidth") == 816 and pl.get("canvasSize", {}).get("cssHeight") == 612
                  and pl.get("frames", [{}])[0].get("background") == of.get("background") and of.get("background")
                  and pl.get("frames", [{}])[0].get("strokeGroups") == (of.get("strokeGroups") or []) + [len(aps)],
                  json.dumps({k: pl.get(k) for k in ("canvasSize", "pauseMode")})
                  + f" ground {pl.get('frames', [{}])[0].get('background')} groups {pl.get('frames', [{}])[0].get('strokeGroups')}")
            ana_id, cat_id = pid_of("ana")[0], post_id(cat)
            check("its row says it is a draw-back, on her post, and whose that is",
                  row and row["is_drawback"] and row["on"] == cat_id and row["owner"] == ana_id, json.dumps(
                      {k: (row or {}).get(k) for k in ("is_drawback", "on", "owner")}))
            # A JAM: a draw-back on a draw-back, here by its own maker (the owner's
            # first try on the live site, Nov 19), and by the first artist.
            jams = {}
            for who, seed in ((theo, 13), (ana, 14)):
                st3, j3 = draw_back(who, back, answer(n=8, seed=seed))
                r3 = stored((j3 or {}).get("post") if isinstance(j3, dict) else None) or {}
                p3 = ((r3.get("payload") or {}).get("frames") or [{}])[0].get("strokes") or []
                jams[who.handle] = (st3, len(p3), xy(p3[:len(pts)]) == xy(pts), r3.get("on") == post_id(back),
                                    (j3 or {}).get("error") if isinstance(j3, dict) else j3)
            check("a draw-back can be drawn back on (a jam), by its own maker or anyone: the whole of it first (both"
                  " hands), then the new one, on its row",
                  all(v[0] == 200 and v[1] == len(pts) + 8 and v[2] and v[3] for v in jams.values()), json.dumps(jams))
            # A short original plays as she drew it: nothing to squeeze.
            short = post_payload(ana, "Section 1, short", drawing(n=20, seed=5))
            st2, j2 = draw_back(theo, short, answer(n=10, seed=6))
            pts2 = ((stored(j2.get("post") if isinstance(j2, dict) else None) or {}).get("payload") or {}).get("frames", [{}])[0].get("strokes") or []
            sops = drawing(n=20, seed=5)["frames"][0]["strokes"]
            check("a short original (under three seconds) plays as she drew it, nothing squeezed",
                  st2 == 200 and [q["t"] for q in pts2[:20]] == played(sops, 50), f"{[q['t'] for q in pts2[:6]]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "what is refused, and what the composer is handed"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            kim = someone(b, "kim", "Kim Ode")
            cat = post_payload(ana, "Section 2, the cat", CAT)
            flip = drawing(n=20, seed=7)
            flip["playbackMode"] = "flip"
            flip["frames"] = [flip["frames"][0], dict(flip["frames"][0])]
            flip["fps"] = 8
            fl = post_payload(ana, "Section 2, a flip", flip)
            ph = drawing(n=20, seed=8)
            ph["frames"][0]["photo"] = {"data": PNG, "fit": "cover"}
            photo = post_payload(ana, "Section 2, on a photo", ph)
            got = {
                "shape": draw_back(theo, cat, answer(size=(612, 816))),
                "flip": draw_back(theo, fl, answer()),
                "photo": draw_back(theo, photo, answer()),
                "nothing": draw_back(theo, "nosuchpost00", answer()),
                "quote": draw_back(theo, cat, answer(), quote=cat),
            }
            said = {k: (v[0], (v[1] or {}).get("error") if isinstance(v[1], dict) else v[1], (v[1] or {}).get("why") if isinstance(v[1], dict) else None)
                    for k, v in got.items()}
            check("refused, saying why: an answer drawn on another shape (drawback_shape), a Flip of two pages and a"
                  " drawing on a photo (drawback_unsupported: pages, photo), a post not there (drawback_gone), and a"
                  " draw-back beside a quote (one_drawing)",
                  said == {"shape": (400, "drawback_shape", None), "flip": (400, "drawback_unsupported", "pages"),
                           "photo": (400, "drawback_unsupported", "photo"), "nothing": (404, "drawback_gone", None),
                           "quote": (400, "one_drawing", None)} and fl and photo,
                  json.dumps(said))
            # A PICTURE UNDER HIS ANSWER (the owner's first try, Nov 19: "I tried
            # to put a picture in the background"): refused saying it is his,
            # and the composer has words that say what to take out.
            mine_ph = answer()
            mine_ph["frames"][0]["photo"] = {"data": PNG, "fit": "cover"}
            yp = draw_back(theo, cat, mine_ph)
            theirs = got["photo"]
            # ERASING IN HIS (the owner's "All yes", Nov 19: the eraser is off
            # while drawing back; the server holds the line too).
            mine_er = answer()
            mine_er["frames"][0]["strokes"][5]["erase"] = True
            er = draw_back(theo, cat, mine_er)
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/")
            ready(pg)
            words = pg.evaluate("""() => Object.fromEntries(['photo', 'music', 'recolors', 'erase'].map(k => [k,
              (document.querySelector('[data-compose-said] [data-word="cmp_drawback_' + k + '"]') || {}).textContent || null]))""")
            close_ctx(ctx, pg)
            check("a picture under HIS answer is refused saying it is his (why photo, on yours), hers on a photo saying it"
                  " is hers (on theirs); and the composer has words for each thing of his it can't carry yet, saying what"
                  " to take out",
                  yp[0] == 400 and (yp[1] or {}).get("why") == "photo" and (yp[1] or {}).get("on") == "yours"
                  and (theirs[1] or {}).get("on") == "theirs"
                  and all(w and "Edit drawing" in w for w in words.values()),
                  json.dumps({"yours": yp, "theirs": theirs[1], "words": words})[:500])
            check("an answer with erasing in it is refused (why erase, on yours): a draw-back replays as one drawing, so"
                  " his eraser would erase hers too",
                  er[0] == 400 and (er[1] or {}).get("why") == "erase" and (er[1] or {}).get("on") == "yours", json.dumps(er))
            # Behind a block, either way, the original is not there.
            c = ana.client()
            c.get("/social/")
            bst, _ = c.post_json("/social/@kim/block", {})
            blocked = draw_back(kim, cat, answer())
            kc = kim.client()
            r_blocked = kc.get_json(f"/social/p/{cat}/drawback")
            check("behind a block (Ana blocked Kim) her drawing is not Kim's to draw back on, nor handed over: as gone"
                  " as one never made",
                  bst == 200 and blocked[0] == 404 and (blocked[1] or {}).get("error") == "drawback_gone"
                  and r_blocked[0] == 404, f"block {bst}; post {blocked}; route {r_blocked[0]}")
            tc = theo.client()
            r_ok = tc.get_json(f"/social/p/{cat}/drawback")
            r_out = Client().get_json(f"/social/p/{cat}/drawback")
            r_flip = tc.get_json(f"/social/p/{fl}/drawback")
            okp = r_ok[1] if isinstance(r_ok[1], dict) else {}
            check("the composer is handed her drawing as Skribl serves it (her points, her shape) and her first name;"
                  " signed out nothing (401), a Flip of two pages refused with why (400)",
                  r_ok[0] == 200 and xy((okp.get("payload") or {}).get("frames", [{}])[0].get("strokes") or []) == xy(CAT["frames"][0]["strokes"])
                  and (okp.get("payload") or {}).get("canvasSize", {}).get("cssWidth") == 816 and okp.get("first") == "Ana"
                  and r_out[0] == 401 and r_flip[0] == 400 and (r_flip[1] or {}).get("why") == "pages",
                  f"{r_ok[0]} first {okp.get('first')}; signed out {r_out[0]}; flip {r_flip}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "the card: the pen and its count; the credit and her face; once she goes"):
        # (Signed out, the post's own page: Home asks a stranger to sign in.)
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            cat = post_payload(ana, "Section 3, the cat", CAT)
            flip = drawing(n=20, seed=9)
            flip["playbackMode"] = "flip"
            flip["frames"] = [flip["frames"][0], dict(flip["frames"][0])]
            flip["fps"] = 8
            fl = post_payload(ana, "Section 3, a flip", flip)
            ph = drawing(n=20, seed=10)
            ph["frames"][0]["photo"] = {"data": PNG, "fit": "cover"}
            photo = post_payload(ana, "Section 3, on a photo", ph)
            st, j = draw_back(theo, cat, answer())
            back = (j or {}).get("post")
            seen = {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, theo, scheme=scheme)
                home(pg)
                seen[scheme] = {"cat": pg.evaluate(CARD, cat), "flip": pg.evaluate(CARD, fl), "back": pg.evaluate(CARD, back),
                                "photo": pg.evaluate(CARD, photo)}
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, None)
            pg.goto(BASE + f"/social/p/{cat}")
            ready(pg)
            out = pg.evaluate("""() => { const r = document.querySelector('.post-page > .post-row'); return r && {
              kids: [...r.children].map(e => e.classList.contains('db-pen') ? 'pen' : e.className.split(' ')[0]), pen: null }; }""")
            close_ctx(ctx, pg)
            ok = all(v["cat"] and v["cat"]["kids"] == ["comment", "repost", "heart", "pen", "more"] and v["cat"]["pen"]
                     and v["cat"]["pen"]["w"] >= 44 and v["cat"]["pen"]["h"] == 44 and v["cat"]["pen"]["hit"]
                     and v["cat"]["pen"]["icon"] and v["cat"]["pen"]["label"] == "Draw back, 1 draw-back"
                     and v["cat"]["pen"]["n"] == "1" for v in seen.values())
            check("on Home's card the pen sits after the heart, 44px to a finger and painted where it stands, named"
                  " \"Draw back, 1 draw-back\" with its count beside it (light and dark)",
                  st == 200 and ok, json.dumps({k: v["cat"] for k, v in seen.items()})[:600])
            # A draw-back can itself be drawn back on (a jam): its card has the pen.
            check("no pen on a Flip of two pages, nor on a drawing made on a photo (read when it was posted), nor for"
                  " somebody signed out (the card's row as it was); a draw-back's own card has one (a jam)",
                  all(v["flip"] and v["flip"]["pen"] is None and v["photo"] and v["photo"]["pen"] is None
                      and v["back"] and v["back"]["pen"] for v in seen.values()) and out and out["pen"] is None
                  and "pen" not in out["kids"] and len(out["kids"]) == 4,
                  json.dumps({"flip": seen["light"]["flip"] and seen["light"]["flip"]["kids"],
                              "photo": seen["light"]["photo"] and seen["light"]["photo"]["kids"], "out": out and out["kids"]}))
            bk = seen["light"]["back"] or {}
            check("a draw-back's card says \"Drew back on Ana’s\" under his name, her name the link to her post, 44px tall"
                  " and painted where it stands, and her face small at the foot of his (light and dark)",
                  all((v["back"] or {}).get("on") == "Drew back on Ana’s" and (v["back"] or {}).get("face")
                      and ((v["back"] or {}).get("who") or {}).get("href") == f"/social/p/{cat}"
                      and ((v["back"] or {}).get("who") or {}).get("h", 0) >= 44 and ((v["back"] or {}).get("who") or {}).get("hit")
                      for v in seen.values()),
                  json.dumps(bk)[:500])
            # ITS OWN PAGE SAYS SO TOO (the owner, Nov 19, from the Gallery: "it
            # shows the new drawing, but not that it's a drawback").
            page = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, theo, screen=screen)
                pg.goto(BASE + f"/social/p/{back}")
                ready(pg)
                page[screen] = pg.evaluate("""() => { const l = document.querySelector('.post-page .post-on'), a = l && l.querySelector('.post-on-who');
                  const r = a && a.getBoundingClientRect(), at = r && document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  return { on: l ? l.textContent.replace(/\\s+/g, ' ').trim() : null, href: a ? new URL(a.href).pathname : null,
                           hit: !!at && !!a && a.contains(at), face: !!document.querySelector('.post-page .post-face .db-face .face-ring') }; }""")
                close_ctx(ctx, pg)
            check("a draw-back's own page says it too, under its header: \"Drew back on Ana’s\", her post the link, painted"
                  " where it stands, her face small at the foot of his (phone and desk)",
                  all(v == {"on": "Drew back on Ana’s", "href": f"/social/p/{cat}", "hit": True, "face": True} for v in page.values()),
                  json.dumps(page))
            # ON YOUR OWN DRAWING (the owner's "All yes", Nov 19): "Drew back on
            # their own drawing", the link to it, one face. AND A NAME THAT
            # STARTS WITH A TITLE is said whole: "Dr. Kai Moss", never "Dr.".
            mine3 = post_payload(theo, "Section 3, Theo's own", CAT)
            own = (draw_back(theo, mine3, answer(n=10, seed=40))[1] or {}).get("post")
            kai = someone(b, "drkai", "Dr. Kai Moss")
            k1 = post_payload(kai, "Section 3, Dr. Kai's first", CAT)
            post_payload(kai, "Section 3, Dr. Kai's second", drawing(n=20, seed=41))
            onkai = (draw_back(theo, k1, answer(n=10, seed=42))[1] or {}).get("post")
            ctx, pg = browser_as(b, theo)
            home(pg)
            own_card, kai_card = pg.evaluate(CARD, own), pg.evaluate(CARD, onkai)
            pg.goto(BASE + f"/social/p/{k1}")
            ready(pg)
            more = pg.evaluate("() => (document.querySelector('#moreTitle') || {}).textContent || null")
            close_ctx(ctx, pg)
            check("a draw-back on its maker's own drawing says \"Drew back on their own drawing\", the link to it, and one"
                  " face (never their own twice)",
                  own_card and own_card["on"] == "Drew back on their own drawing" and not own_card["face"]
                  and (own_card["who"] or {}).get("href") == f"/social/p/{mine3}", json.dumps(own_card))
            check("a name that starts with a title is said whole: \"Drew back on Dr. Kai Moss’s\" and \"More from Dr. Kai"
                  " Moss\", never \"Dr.\"",
                  kai_card and kai_card["on"] == "Drew back on Dr. Kai Moss’s" and more == "More from Dr. Kai Moss",
                  json.dumps({"card": kai_card and kai_card["on"], "more": more}))
            c = ana.client()
            c.get("/social/")
            dst, _ = c.post_json(f"/social/p/{cat}/delete", {})
            ctx, pg = browser_as(b, theo)
            home(pg)
            after = pg.evaluate(CARD, back)
            close_ctx(ctx, pg)
            row = stored(back)
            check("once her post is gone his plays on, both hands in it, and says \"Drew back on a drawing\", no link and"
                  " no face of hers",
                  dst == 200 and after and after["on"] == "Drew back on a drawing" and after["who"] is None and not after["face"]
                  and row and row["on"] is None and len(row["payload"]["frames"][0]["strokes"]) == len(CAT["frames"][0]["strokes"]) + 30,
                  f"delete {dst}; {after}; row on {row and row['on']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "the whole way: the pen, the Pad on her shape and paper, hers faint, Theirs, drawn and posted"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            cat = post_payload(ana, "Section 4, the cat", CAT)
            ctx, pg = browser_as(b, theo)
            home(pg)
            pen = f'.post-card[data-post="{cat}"] .db-pen'
            pg.locator(pen).scroll_into_view_if_needed()
            pg.click(pen)
            fe = pg.wait_for_selector("#composePad .facepad-frame", state="attached", timeout=15000)
            pg.wait_for_function("() => document.querySelector('#composePad').classList.contains('is-ready')", timeout=30000)
            fr = fe.content_frame()
            fr.wait_for_function("() => !!window.SkriblDrawBack && !!SkriblDrawBack.state()", timeout=15000)
            pg.wait_for_timeout(500)
            # A point in the middle of one of her thick strokes, and one far from any.
            thick = next(q for q in CAT["frames"][0]["strokes"] if q.get("size", 0) >= 6 and not q.get("start"))
            SAMPLE = """([x, y]) => { const g = document.querySelector('.db-under'), c = document.getElementById('canvas');
              const k = g.width / c.offsetWidth * c.offsetWidth / 816;
              return g.getContext('2d').getImageData(Math.round(x * k), Math.round(y * k), 1, 1).data[3]; }"""
            def alphas():
                return [fr.evaluate(SAMPLE, [thick["x"], thick["y"]]), fr.evaluate(SAMPLE, [800, 20])]
            look = fr.evaluate("""() => { const c = document.getElementById('canvas'), g = document.querySelector('.db-under');
              const p = document.querySelector('.db-pill'), b = p && p.querySelector('.db-theirs');
              return { size: getCanvasLogicalSize(), ground: String(bgColor).toLowerCase(),
                       same: !!g && Math.abs(g.offsetWidth - c.offsetWidth) < 0.5 && Math.abs(g.offsetLeft - c.offsetLeft) < 0.5
                             && Math.abs(g.offsetTop - c.offsetTop) < 0.5 && g.parentNode === c.parentNode,
                       touch: g ? getComputedStyle(g).pointerEvents : null,
                       pill: p ? p.querySelector('.db-where').textContent : null,
                       btn: b ? { h: b.getBoundingClientRect().height, label: b.getAttribute('aria-label') } : null }; }""")
            faint = alphas()
            check("the pen opens the composer and the Pad over it on her shape (816x612) and paper (#f6f2ea, she named"
                  " none), her drawing on a canvas of its own exactly over the drawing, taking no touch; the pill says"
                  " \"Drawing back on Ana’s\", Theirs 44px",
                  look["size"] == {"width": 816, "height": 612} and look["ground"] == "#f6f2ea" and look["same"]
                  and look["touch"] == "none" and look["pill"] == "Drawing back on Ana’s" and look["btn"]
                  and look["btn"]["h"] >= 44 and look["btn"]["label"] == "Theirs: faint",
                  json.dumps(look))
            check("hers faint, in her own colours: painted where her strokes are, laid down at 0.32 (one coat, no"
                  " beading), nothing where she drew nothing",
                  abs(faint[0] - round(0.32 * 255)) <= 3 and faint[1] == 0, f"alpha on her line {faint[0]}, off it {faint[1]}")
            cycle = []
            for _ in range(3):
                fr.click(".db-theirs")
                pg.wait_for_timeout(150)
                cycle.append((fr.evaluate("() => SkriblDrawBack.state().theirs"), alphas()[0],
                              fr.evaluate("() => document.querySelector('.db-theirs').getAttribute('aria-label')")))
            check("Theirs goes full, hidden and back to faint, its name saying which",
                  [c_[0] for c_ in cycle] == ["full", "hidden", "faint"] and cycle[0][1] == 255 and cycle[1][1] == 0
                  and abs(cycle[2][1] - 82) <= 3 and [c_[2] for c_ in cycle] == ["Theirs: full", "Theirs: hidden", "Theirs: faint"],
                  json.dumps(cycle))
            # WHAT STEPS ASIDE (the owner's "All yes", Nov 19): the eraser, the
            # picture and music, Recolour; each says why, in the editor's toast.
            aside = {}
            fr.click("#eraserToolBtn")
            pg.wait_for_timeout(150)
            aside["eraser"] = fr.evaluate("() => [tool, document.getElementById('toast').textContent]")
            fr.click("#mediaOpenBtn")
            pg.wait_for_timeout(150)
            aside["media"] = fr.evaluate("() => [document.getElementById('mediaOpenBtn').getAttribute('aria-expanded'), document.getElementById('toast').textContent]")
            fr.evaluate("() => document.getElementById('recolorBtn').click()")
            pg.wait_for_timeout(150)
            aside["recolor"] = fr.evaluate("() => document.getElementById('toast').textContent")
            aside["dim"] = fr.evaluate("() => ['eraserToolBtn', 'mediaOpenBtn'].map(i => getComputedStyle(document.getElementById(i)).opacity)")
            check("while drawing back the eraser stays aside (the pen stays in hand: \"The eraser is off while drawing back."
                  " Undo takes back your last line.\"), the picture and music drawer stays shut (\"The background and music"
                  " are Ana’s.\"), and Recolour says it is off; each dimmed",
                  aside["eraser"] == ["pen", "The eraser is off while drawing back. Undo takes back your last line."]
                  and aside["media"] == ["false", "The background and music are Ana’s."]
                  and aside["recolor"] == "Recolour is off while drawing back." and aside["dim"] == ["0.4", "0.4"],
                  json.dumps(aside))
            box = fr.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return [r.left, r.top, r.width]; }")
            fb = fe.bounding_box()
            k = box[2] / 816
            for i in range(3):
                x0, y0 = fb["x"] + box[0] + (640 + i * 30) * k, fb["y"] + box[1] + 120 * k
                pg.mouse.move(x0, y0)
                pg.mouse.down()
                for s_ in range(1, 12):
                    pg.mouse.move(x0 + s_ * 3 * k, y0 + (s_ % 4) * 6 * k)
                pg.mouse.up()
                pg.wait_for_timeout(120)
            fr.click("#recordBtn")
            pg.wait_for_timeout(500)
            fr.click("#postBtn")
            pg.wait_for_timeout(600)
            sub = fr.query_selector("#postSubmitBtn")
            if sub and sub.is_visible():
                sub.click()
            pg.wait_for_function("() => !!window.SocialComposer.attached()", timeout=20000)
            line = pg.evaluate("() => { const l = document.querySelector('[data-compose-backline]'); return l && !l.hidden ? l.textContent : null; }")
            with pg.expect_navigation(timeout=20000):
                pg.click("[data-compose-post]")
            pg.wait_for_timeout(600)
            landed = urllib.parse.urlparse(pg.url).path
            pg.wait_for_timeout(400)
            poster = pg.evaluate("() => { const i = document.querySelector('.post-page .skribl-inline-poster'); return i ? i.getAttribute('src') : null; }")
            close_ctx(ctx, pg)
            row = stored(landed.rsplit("/", 1)[-1])
            pts = ((row or {}).get("payload") or {}).get("frames", [{}])[0].get("strokes") or []
            check("drawn, Done, Add and Post (the sheet saying \"Drawing back on Ana’s\" at its top): it lands on the new"
                  " post, a draw-back on hers, whose drawing holds her 726 points and then his",
                  line == "Drawing back on Ana’s" and landed.startswith("/social/p/") and row and row["is_drawback"]
                  and row["on"] == post_id(cat) and len(pts) > 726 and xy(pts[:726]) == xy(CAT["frames"][0]["strokes"]),
                  f"line {line!r}; landed {landed}; {len(pts)} points")
            # THE PICTURE IT RESTS ON (the owner, Nov 19: "there's no image on
            # the drawbacks"): the poster is the Pad's card, her drawing under
            # his. Read off the picture: her dark ink where her cat is (the
            # card's drawing area, 1200 x 630, the cat's left half), where his
            # strokes never went (he drew right of x 640).
            dark, kind = 0, None
            try:
                with urllib.request.urlopen(BASE + poster if poster and poster.startswith("/") else (poster or ""), timeout=20) as r:
                    kind = r.headers.get("Content-Type")
                    raw = r.read()
                from PIL import Image
                import io
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                k = im.width / 1200
                px = im.load()
                for y in range(int(120 * k), int(470 * k)):
                    for x in range(int(380 * k), int(560 * k)):
                        r_, g_, b_ = px[x, y]
                        if r_ < 90 and g_ < 90 and b_ < 110:
                            dark += 1
            except Exception as exc:  # noqa: BLE001 -- no picture is this row's red
                kind = kind or str(exc)[:80]
            check("the posted draw-back rests on a picture of both: its poster is the Pad's card, her ink there where her"
                  " cat is (his lines were drawn elsewhere), never the blank stand-in",
                  dark > 150 and kind and "svg" not in kind, f"poster {poster}; {kind}; {dark} dark pixels in her cat's half")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "Activity: her row, the dot, the nudge's words; nobody muted, never your own"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            mo = someone(b, "mona", "Mona Vale")
            cat = post_payload(ana, "Section 5, the cat", CAT)
            # Ana mutes Mona: her draw-back is no row of Ana's.
            c = ana.client()
            c.get("/social/")
            mst, _ = c.post_json("/social/@mona/mute", {})
            draw_back(mo, cat, answer(n=12, seed=11))
            st, j = draw_back(theo, cat, answer())
            back = (j or {}).get("post")
            mine = draw_back(ana, cat, answer(n=8, seed=12))     # her own, on her own: never a row of hers
            # Asked before she looks: what a nudge says is what is new.
            NUDGE = r"""
import json, sys
from datetime import timedelta
from app import create_app
app = create_app()
with app.test_request_context("/social/"):
    from social.models import Person, utcnow
    from social.push import nudges_for
    import sqlalchemy as sa
    from social.security import site
    me = site().session().execute(sa.select(Person).where(Person.handle_key == "ana")).scalar_one()
    got = nudges_for(me, utcnow() - timedelta(minutes=10), {"replies"})
    print(json.dumps([[p["title"], p["body"], p["url"], sorted(sw)] for p, sw, _ in got]))
"""
            probe = subprocess.run([sys.executable, "-c", NUDGE], cwd=ROOT, capture_output=True, text=True, timeout=180, env=ENV)
            try:
                nudged = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                nudged = probe.stderr[-300:]
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/")
            ready(pg)
            pg.goto(BASE + "/social/activity")
            ready(pg)
            rows = pg.evaluate("""() => [...document.querySelectorAll('.act-row')].map(a => ({ text: a.innerText.replace(/\\s+/g, ' ').trim(),
              href: new URL(a.href).pathname, badge: !!a.querySelector('.db-badge svg'), isNew: a.classList.contains('is-new') }))""")
            close_ctx(ctx, pg)
            # Only this section's: earlier sections drew back on Ana's too.
            db_rows = [r for r in rows if "drew back on your drawing" in r["text"] and r["href"] == f"/social/p/{back}"]
            others = [r for r in rows if "drew back on your drawing" in r["text"] and r["text"].startswith(("Mona", "New: Mona", "Ana", "New: Ana"))]
            check("Ana's Activity has Theo's draw-back, new: \"Theo drew back on your drawing\", Draw back's"
                  " pen on his face, opening his draw-back; none of Mona, whom she muted, and none of her own",
                  st == 200 and mst == 200 and len(db_rows) == 1 and not others
                  and db_rows[0]["text"].startswith("New: Theo drew back on your drawing")
                  and db_rows[0]["href"] == f"/social/p/{back}" and db_rows[0]["badge"] and db_rows[0]["isNew"],
                  json.dumps(rows)[:500])
            check("it nudges as a reply does (Replies): \"Theo drew back on your drawing\", and with no words of his"
                  " \"Tap to watch yours, then theirs.\", to his draw-back",
                  isinstance(nudged, list) and any(n[0] == "Theo drew back on your drawing" and n[2].endswith(f"/social/p/{back}")
                                                   and n[1] == "Tap to watch yours, then theirs." and n[3] == ["replies"]
                                                   for n in nudged),
                  json.dumps(nudged)[:400])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "her post's strip: how many, newest first, each opening its draw-back; nothing a block hides"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            uma = someone(b, "uma", "Uma Sato")
            # (Lea: nobody Ana blocked; Kim is blocked by Ana in section 2.)
            kim = someone(b, "lea", "Lea Fox")
            cat = post_payload(ana, "Section 6, the cat", CAT)
            first = (draw_back(theo, cat, answer(n=10, seed=21))[1] or {}).get("post")
            time.sleep(0.02)
            second = (draw_back(uma, cat, answer(n=10, seed=22))[1] or {}).get("post")
            time.sleep(0.02)
            third = (draw_back(kim, cat, answer(n=10, seed=23))[1] or {}).get("post")
            # Theo blocks Lea: hers is not on the strip Theo sees.
            c = theo.client()
            c.get("/social/")
            bst, _ = c.post_json("/social/@lea/block", {})
            STRIP = """() => { const s = document.querySelector('.db-strip'); if (!s) return null;
              return { title: s.querySelector('.db-title').innerText.trim(), icon: !!s.querySelector('.db-title svg'),
                       tiles: [...s.querySelectorAll('.db-tile')].map(t => [new URL(t.href).pathname, t.querySelector('.db-by').textContent,
                                                                           !!t.querySelector('.more-plate img')]),
                       wide: document.documentElement.scrollWidth <= innerWidth }; }"""
            seen = {}
            for who in (ana, theo):
                ctx, pg = browser_as(b, who)
                pg.goto(BASE + f"/social/p/{cat}")
                ready(pg)
                seen[who.handle] = pg.evaluate(STRIP)
                close_ctx(ctx, pg)
            want = [[f"/social/p/{x}", n, True] for x, n in ((third, "Lea"), (second, "Uma"), (first, "Theo"))]
            check("on her post, under the row: \"3 draw-backs\" with Draw back's pen, then each draw-back's drawing and who"
                  " drew back, newest first, each opening its own page; nothing past the screen",
                  seen["ana"] and seen["ana"]["title"] == "3 draw-backs" and seen["ana"]["icon"] and seen["ana"]["tiles"] == want
                  and seen["ana"]["wide"], json.dumps(seen["ana"]))
            check("behind a block (Theo blocked Lea) Lea's is not on the strip Theo sees: \"2 draw-backs\"",
                  bst == 200 and seen["theo"] and seen["theo"]["title"] == "2 draw-backs" and seen["theo"]["tiles"] == want[1:],
                  json.dumps(seen["theo"]))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "when a replay ends: Watch again and Draw back at the drawing's foot; they go as it plays"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            short = post_payload(ana, "Section 7, short", drawing(n=20, seed=31))
            END = """(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'); if (!c) return null;
              const e = c.querySelector('.db-end'), box = c.querySelector('[data-skribl-inline]');
              if (!e) return { none: true };
              const cv = box.querySelector('canvas, img'), cr = cv.getBoundingClientRect();
              return { up: e.classList.contains('is-up'), parent: e.parentElement === box,
                       buttons: [...e.querySelectorAll('button')].map(b => { const r = b.getBoundingClientRect();
                         const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                         return { words: b.textContent.trim(), h: r.height, inside: r.bottom <= cr.bottom - 11.5 && r.top >= cr.top,
                                  hit: !!at && b.contains(at), font: getComputedStyle(b).fontFamily }; }),
                       playAside: getComputedStyle(c.querySelector('.skribl-inline-play')).visibility }; }"""
            seen = {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, theo, scheme=scheme)
                home(pg)
                sel = f'.post-card[data-post="{short}"]'
                pg.locator(sel).scroll_into_view_if_needed()
                pg.click(sel + " .skribl-inline-play")
                pg.wait_for_function("(s) => !!document.querySelector(s + ' .db-end.is-up')", arg=sel, timeout=20000)
                pg.wait_for_timeout(300)
                seen[scheme] = pg.evaluate(END, short)
                if scheme == "light":
                    pg.click(sel + " .db-again")
                    pg.wait_for_timeout(250)
                    seen["again"] = {"gone": pg.evaluate("(s) => !document.querySelector(s + ' .db-end')", sel),
                                     "playing": pg.evaluate("(s) => document.querySelector(s + ' [data-skribl-inline]').classList.contains('is-playing')", sel)}
                    pg.wait_for_function("(s) => !!document.querySelector(s + ' .db-end.is-up')", arg=sel, timeout=20000)
                    pg.click(sel + " .db-go")
                    pg.wait_for_function("() => window.SocialComposer && !!SocialComposer.drawingBack()", timeout=10000)
                    seen["go"] = pg.evaluate("() => SocialComposer.drawingBack()")
                close_ctx(ctx, pg)
            ok = all(v and v.get("up") and v.get("parent") and [x["words"] for x in v["buttons"]] == ["Watch again", "Draw back"]
                     and all(x["h"] >= 44 and x["inside"] and x["hit"] and "monospace" not in x["font"] for x in v["buttons"])
                     and v["playAside"] == "hidden" for v in (seen["light"], seen["dark"]))
            check("when a replay ends, \"Watch again\" and \"Draw back\" rise in the drawing's own box, 12px or more above"
                  " its foot, 44px each, painted where they stand, in the site's face; the box's own replay mark aside"
                  " (light and dark)", ok, json.dumps({k: seen.get(k) for k in ("light", "dark")})[:600])
            check("Watch again plays it again and they go; Draw back opens the composer drawing back on hers",
                  seen.get("again") == {"gone": True, "playing": True} and (seen.get("go") or {}).get("id") == short,
                  json.dumps({k: seen.get(k) for k in ("again", "go")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
