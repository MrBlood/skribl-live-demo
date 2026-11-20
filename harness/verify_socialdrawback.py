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
  8. WHAT A DRAW-BACK SAYS: each hand's own drawing time on its line, who
     and the whole on its play button.
  9. THE PEN'S LINE: Draw back's wave is the pen's line (--brand) and its
     pen the ink of where it sits, on a card's row, a post's own row, the
     draw-backs' title, "Draw back" in words and Activity's badge, read off
     what is painted, 3:1 or more against its ground; on the pill that rises
     when a replay ends (the action's fill) the wave stays white.
 10. No page errors, no console errors and no CSP violations.

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


def browser_as(b, who, screen="phone", scheme="light", reduced=False, dpr=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    shape = dict(PHONE if screen == "phone" else DESK)
    if dpr:
        shape["device_scale_factor"] = dpr      # a line's own colour needs whole pixels of it (section 9)
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **shape, **kw)
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


def red_png():
    import io as _io
    from PIL import Image as _Image
    buf = _io.BytesIO()
    _Image.new("RGB", (64, 48), (230, 40, 60)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def short_wav():
    import struct
    n = 800
    data = b"".join(struct.pack("<h", (i % 40 - 20) * 400) for i in range(n))
    head = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
            + b"data" + struct.pack("<I", len(data)))
    return "data:audio/wav;base64," + base64.b64encode(head + data).decode()


def on_photo_with_music(seed=50):
    d = drawing(n=24, seed=seed)
    d["frames"][0]["photo"] = {"data": red_png(), "fit": "cover", "opacity": 1, "blur": 0, "offset": {"x": 0.5, "y": 0.5}, "zoom": 1}
    d["frames"][0]["music"] = {"data": short_wav(), "name": None, "trimStart": 0, "trimEnd": 0}
    return d


def media_of(payload):
    """A drawing's photo and song as stored: [photo, song], each its data."""
    f0 = ((payload or {}).get("frames") or [{}])[0]
    return [(f0.get(slot) or {}).get("data") if isinstance(f0.get(slot), dict) else None for slot in ("photo", "music")]


# WHERE THE SITE KEEPS MEDIA APART (SKRIBL_MEDIA_BACKEND=local or s3: a
# deployed site may), a stored drawing names its photo and song by key, and a
# draw-back reads them back from the store as data to post them again
# (skribl.read_payload's inline_media). Checked in a process of its own, on a
# database and a store of its own, with no site in between: on SQLite the
# site's own reads hold the lock the store's claim commits under, and a post
# with media then answers busy, which is a property of SQLite beside a store,
# not of draw back (docs/NEXT-SESSION.md). The server above keeps media in
# the drawing, as the live site does.
STORE = r"""
import base64, json, sys
import sqlalchemy as sa
from app import app, db
from skribl import create_post, read_payload
from social.drawback import drawable, join
inp = json.load(open(sys.argv[1]))
def data(payload, slot):
    v = ((payload.get("frames") or [{}])[0]).get(slot)
    return v.get("data") if isinstance(v, dict) else None
def raw(d):
    return base64.b64decode(d.split(",", 1)[1]) if isinstance(d, str) and d.startswith("data:") else None
def kept(pid):
    return json.loads(db.session.execute(sa.text("select payload_json from skribl_posts where public_id = :p"), {"p": pid}).scalar())
out = {}
with app.app_context():
    db.create_all()
    with app.test_request_context("/"):
        a = create_post(dict(inp["orig"], visibility="unlisted"), author_id="site:ana")
        db.session.commit()
        out["hers"] = [data(kept(a.public_id), s) for s in ("photo", "music")]
        got = read_payload(a.public_id, inline_media=True)
        out["read"] = [raw(data(got, s)) == raw(data(inp["orig"], s)) for s in ("photo", "music")]
        out["drawable"] = drawable(got)
        db.session.commit()
        b = create_post(dict(join(got, inp["answer"]), visibility="unlisted"), author_id="site:theo")
        db.session.commit()
        out["back"] = [data(kept(b.public_id), s) for s in ("photo", "music")]
print(json.dumps(out))
"""


def store_probe(orig, ans):
    """STORE, run on its own database and store: what it found."""
    d = tempfile.mkdtemp(prefix="store-", dir=TMP)
    with open(os.path.join(d, "in.json"), "w") as f:
        json.dump({"orig": orig, "answer": ans}, f)
    env = dict(ENV, DATABASE_URL=f"sqlite:///{os.path.join(d, 'store.db')}", SKRIBL_MEDIA_BACKEND="local",
               SKRIBL_MEDIA_ROOT=os.path.join(d, "media"))
    r = subprocess.run([sys.executable, "-c", STORE, os.path.join(d, "in.json")], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (r.stderr or r.stdout)[-600:]}


def answer(n=30, seed=3, size=(816, 612)):
    """The strokes an answer hands back: the Pad's drawing, on the original's shape."""
    d = drawing(n=n, seed=seed, size=size)
    d["frames"][0]["background"] = {"color": "#f6f2ea"}
    return d


def post_payload(who, words, payload):
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": payload})
    if not (st == 200 and isinstance(j, dict)):
        print(f"  (post_payload {words!r}: {st} {str(j)[:200]})")
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
            # THE AUTHOR'S BACKGROUND AND MUSIC (the owner's yes, Nov 19): her photo
            # and song come with it.
            ph = post_payload(ana, "Section 1, on a photo with music", on_photo_with_music())
            stp, jp = draw_back(theo, ph, answer(n=12, seed=51))
            rb, ro = stored((jp or {}).get("post") if isinstance(jp, dict) else None), stored(ph)
            kb, ko = media_of((rb or {}).get("payload")), media_of((ro or {}).get("payload"))
            check("a drawing on a photo with music can be drawn back on: the draw-back keeps her photo and her song",
                  stp == 200 and all(isinstance(v, str) and v.startswith("data:") for v in ko) and kb == ko,
                  json.dumps({"status": stp, "err": (jp or {}).get("error") if isinstance(jp, dict) else jp,
                              "back": [v and v[:30] for v in kb], "hers": [v and v[:30] for v in ko]}))
            sp = store_probe(on_photo_with_music(), answer(n=12, seed=51))
            keyed = [isinstance(v, str) and not v.startswith("data:") and len(v.split("?")[0].rsplit("/", 1)[-1].split(".")[0]) == 64
                     for v in sp.get("hers") or [None, None]]
            check("where media is kept apart in a store, her photo and song are read back from it as they were and"
                  " posted again: the draw-back names the very same stored files (each named by its content)",
                  all(keyed) and sp.get("read") == [True, True] and sp.get("drawable") is None
                  and sp.get("back") == sp.get("hers"), json.dumps(sp)[:600])
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
                "nothing": draw_back(theo, "nosuchpost00", answer()),
                "quote": draw_back(theo, cat, answer(), quote=cat),
            }
            said = {k: (v[0], (v[1] or {}).get("error") if isinstance(v[1], dict) else v[1], (v[1] or {}).get("why") if isinstance(v[1], dict) else None)
                    for k, v in got.items()}
            check("refused, saying why: an answer drawn on another shape (drawback_shape), a Flip of two pages"
                  " (drawback_unsupported: pages), a post not there (drawback_gone), and a draw-back beside a quote"
                  " (one_drawing); a drawing on a photo is not refused (the author's background, the owner's yes)",
                  said == {"shape": (400, "drawback_shape", None), "flip": (400, "drawback_unsupported", "pages"),
                           "nothing": (404, "drawback_gone", None), "quote": (400, "one_drawing", None)} and fl and photo,
                  json.dumps(said))
            # A PICTURE UNDER HIS ANSWER (the owner's first try, Nov 19: "I tried
            # to put a picture in the background"): refused saying it is his,
            # and the composer has words that say what to take out.
            mine_ph = answer()
            mine_ph["frames"][0]["photo"] = {"data": PNG, "fit": "cover"}
            yp = draw_back(theo, cat, mine_ph)
            theirs = got["flip"]
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
            check("a picture under HIS answer is refused saying it is his (why photo, on yours), a Flip of hers saying it"
                  " is hers (on theirs); and the composer has words for each thing of his it can't carry, saying what"
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
            check("no pen on a Flip of two pages, nor for somebody signed out (the card's row as it was); a drawing made"
                  " on a photo has one (the author's background, the owner's yes), and so has a draw-back's own card (a jam)",
                  all(v["flip"] and v["flip"]["pen"] is None and v["photo"] and v["photo"]["pen"]
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
                  const f = document.querySelector('.post-page .post-face'), his = f && f.querySelector(':scope > .face-ring'),
                        hers = f && f.querySelector('.db-face .face-ring');
                  const hr = his && his.getBoundingClientRect(), sr = hers && hers.getBoundingClientRect();
                  const mid = hr && document.elementFromPoint(hr.left + hr.width / 2, hr.top + hr.height / 2);
                  const letter = e => { const b = e && e.querySelector('.face-blank.has-initial'); return b ? [b.textContent.trim(), getComputedStyle(b).fontSize] : null; };
                  return { on: l ? l.textContent.replace(/\\s+/g, ' ').trim() : null, href: a ? new URL(a.href).pathname : null,
                           hit: !!at && !!a && a.contains(at), face: !!hers, letters: [letter(his), letter(hers)],
                           faces: hr && sr ? { his: Math.round(hr.width), hers: Math.round(sr.width), middleHis: !!mid && !mid.closest('.db-face'),
                                               foot: sr.left >= hr.left + hr.width / 2 - 1 && sr.top >= hr.top + hr.height / 2 - 1,
                                               ring: (() => { const pr = document.createElement('i'); pr.style.color = 'var(--page)'; document.body.appendChild(pr);
                                                 const ground = getComputedStyle(pr).color; pr.remove();
                                                 return getComputedStyle(f.querySelector('.db-face')).boxShadow.startsWith(ground); })() } : null }; }""")
                close_ctx(ctx, pg)
            check("a draw-back's own page says it too, under its header: \"Drew back on Ana’s\", her post the link, painted"
                  " where it stands, her face small at the foot of his (phone and desk)",
                  all({k: v[k] for k in ("on", "href", "hit", "face")} == {"on": "Drew back on Ana’s", "href": f"/social/p/{cat}", "hit": True, "face": True}
                      for v in page.values()), json.dumps(page))
            # READ WHERE IT IS PAINTED (the owner's walkthrough, Nov 19): the row
            # above asked only whether her face was there, and it was, as big
            # as his and lying over it: "Theo Lin", wearing Ana's face.
            check("on that page his face is the one you see (48px, and what is painted at its middle is his), hers half its"
                  " size (24px) at its foot, ringed in the page's own ground, as the card's is in the card's (phone and desk)",
                  all(v.get("faces") == {"his": 48, "hers": 24, "middleHis": True, "foot": True, "ring": True} for v in page.values()),
                  json.dumps({k: v.get("faces") for k, v in page.items()}))
            # A FACE NOT DRAWN YET SHOWS ITS INITIAL (the walkthrough's mocks,
            # choice 9, the owner's "all yes", Nov 19), his and hers: two blank
            # lilac circles, one on the other, said nothing about who.
            check("neither has drawn a face yet, and each disc says whose it is: his initial at 19px in his 48px disc, hers"
                  " at 11px in her 24px one (phone and desk)",
                  all(v.get("letters") == [["T", "19px"], ["A", "11px"]] for v in page.values()),
                  json.dumps({k: v.get("letters") for k, v in page.items()}))
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
            over = fr.evaluate("""() => { const t = document.getElementById('toast').getBoundingClientRect(), p = document.querySelector('.db-pill').getBoundingClientRect();
              return { hit: t.top < p.bottom && t.bottom > p.top && t.left < p.right && t.right > p.left, toast: [Math.round(t.top), Math.round(t.bottom)],
                       pill: [Math.round(p.top), Math.round(p.bottom)], shown: getComputedStyle(document.getElementById('toast')).visibility !== 'hidden' && t.height > 0 }; }""")
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
            check("what the eraser says does not land on the pill: it sits under \"Drawing back on Ana’s\" and its Theirs"
                  " button, never over them",
                  over and over["shown"] and not over["hit"] and over["toast"][0] >= over["pill"][1], json.dumps(over))
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
            says = pg.evaluate("() => { const b = document.querySelector('[data-compose-post]'), r = b.getBoundingClientRect(); return [b.textContent.trim(), r.right <= innerWidth, Math.round(r.height)]; }")
            with pg.expect_navigation(timeout=20000):
                pg.click("[data-compose-post]")
            pg.wait_for_timeout(600)
            landed = urllib.parse.urlparse(pg.url).path
            pg.wait_for_timeout(400)
            poster = pg.evaluate("() => { const i = document.querySelector('.post-page .skribl-inline-poster'); return i ? i.getAttribute('src') : null; }")
            # A post of your own, after: the button is "Post" again.
            pg.locator("nav.nav .tab-make").first.tap()
            pg.wait_for_timeout(700)
            plain = pg.evaluate("() => document.querySelector('[data-compose-post]').textContent.trim()")
            close_ctx(ctx, pg)
            check("the composer's button says what it makes: \"Post draw-back\" while drawing back (whole on a phone, 44px),"
                  " and \"Post\" for a post of your own",
                  says[0] == "Post draw-back" and says[1] and says[2] >= 44 and plain == "Post", f"{says}; then {plain!r}")
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
            # ON YOUR OWN DRAWING the composer and the Pad say so (the owner,
            # Nov 19: "it's Mr. Blood's drawing (mine) and a drawback on my own
            # drawing"), never "on Theo's".
            mine4 = post_payload(theo, "Section 4, Theo's own", CAT)
            ctx, pg = browser_as(b, theo)
            home(pg)
            pen4 = f'.post-card[data-post="{mine4}"] .db-pen'
            pg.locator(pen4).scroll_into_view_if_needed()
            pg.click(pen4)
            fe4 = pg.wait_for_selector("#composePad .facepad-frame", state="attached", timeout=15000)
            pg.wait_for_function("() => document.querySelector('#composePad').classList.contains('is-ready')", timeout=30000)
            fr4 = fe4.content_frame()
            fr4.wait_for_function("() => !!window.SkriblDrawBack && !!SkriblDrawBack.state()", timeout=15000)
            own_pill = fr4.evaluate("() => document.querySelector('.db-pill .db-where').textContent")
            own_line = pg.evaluate("() => { const l = document.querySelector('[data-compose-backline]'); return l && !l.hidden ? l.textContent : null; }")
            close_ctx(ctx, pg)
            # ON A SLOW LINE (main's red after #989, sqlite 6/6: "section 4 ran
            # to its end: Timeout 15000ms"). The Pad said it was ready as its
            # compose script ran, with scripts still to come after it in the
            # page: Draw back's own, and the one that sets the paper
            # (editor_draft.js). When one arrived a moment later, the host's
            # answer (her drawing) reached a Pad that could not take it yet
            # and was dropped, and the Pad opened on blank paper under
            # "Drawing back on Ana’s". Here both are held back a second and a
            # half, as a phone on a slow line would have them.
            ctx, pg = browser_as(b, theo)
            held = []
            def late(route):
                held.append(route.request.url.rsplit("/", 1)[-1].split("?")[0])
                time.sleep(1.5)
                route.continue_()
            ctx.route("**/lib/drawback.js*", late)
            ctx.route("**/editor_draft.js*", late)
            home(pg)
            pg.locator(pen4).scroll_into_view_if_needed()
            pg.click(pen4)
            fe6 = pg.wait_for_selector("#composePad .facepad-frame", state="attached", timeout=15000)
            pg.wait_for_function("() => document.querySelector('#composePad').classList.contains('is-ready')", timeout=30000)
            fr6 = fe6.content_frame()
            try:
                fr6.wait_for_function("() => !!window.SkriblDrawBack && !!SkriblDrawBack.state()", timeout=8000)
                pg.wait_for_timeout(300)
                slow = fr6.evaluate("() => ({ strokes: SkriblDrawBack.state().strokes, guide: !!document.querySelector('.db-under'), pill: !!document.querySelector('.db-pill'), ground: String(bgColor).toLowerCase() })")
            except Exception:  # noqa: BLE001 -- her drawing never laid down is this row's red
                slow = fr6.evaluate("() => ({ strokes: 0, guide: !!document.querySelector('.db-under'), pill: !!document.querySelector('.db-pill'), module: !!window.SkriblDrawBack })")
            close_ctx(ctx, pg)
            check("on a slow line (Draw back's own script and the paper's a second and a half late) her drawing is still laid"
                  " under the pen, on her paper: the Pad says it is ready only once every script of its own has run",
                  sorted(held) == ["drawback.js", "editor_draft.js"] and slow.get("strokes", 0) > 0 and slow["guide"] and slow["pill"]
                  and slow.get("ground") == "#f6f2ea", json.dumps({"held": held, **slow}))
            # HER PHOTO UNDER THE PEN (the owner's yes, Nov 19).
            ph4 = post_payload(ana, "Section 4, on a photo with music", on_photo_with_music(seed=52))
            ctx, pg = browser_as(b, theo)
            home(pg)
            pen5 = f'.post-card[data-post="{ph4}"] .db-pen'
            pg.locator(pen5).scroll_into_view_if_needed()
            pg.click(pen5)
            fe5 = pg.wait_for_selector("#composePad .facepad-frame", state="attached", timeout=15000)
            pg.wait_for_function("() => document.querySelector('#composePad').classList.contains('is-ready')", timeout=30000)
            fr5 = fe5.content_frame()
            fr5.wait_for_function("() => !!window.SkriblDrawBack && !!SkriblDrawBack.state()", timeout=15000)
            pg.wait_for_timeout(600)
            under = fr5.evaluate("""() => { const p = document.querySelector('.db-photo'), c = document.getElementById('canvas');
              if (!p) return null; const d = p.getContext('2d').getImageData(Math.round(p.width / 2), Math.round(p.height / 2), 1, 1).data;
              return { rgb: [d[0], d[1], d[2]], below: !!(p.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING),
                       same: Math.abs(p.offsetWidth - c.offsetWidth) < 0.5, mine: !!(document.getElementById('photoBgImg') || {})._draftData }; }""")
            # A line of his, Done and Add: the composer's preview plays the two
            # as they will post, on her photo (compose.js joined).
            box5 = fr5.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return [r.left, r.top, r.width]; }")
            fb5 = fe5.bounding_box()
            k5 = box5[2] / 816
            x0, y0 = fb5["x"] + box5[0] + 700 * k5, fb5["y"] + box5[1] + 500 * k5
            pg.mouse.move(x0, y0)
            pg.mouse.down()
            for s_ in range(1, 10):
                pg.mouse.move(x0 + s_ * 3 * k5, y0 + (s_ % 3) * 5 * k5)
            pg.mouse.up()
            pg.wait_for_timeout(150)
            fr5.click("#recordBtn")
            pg.wait_for_timeout(500)
            fr5.click("#postBtn")
            pg.wait_for_timeout(600)
            sub5 = fr5.query_selector("#postSubmitBtn")
            if sub5 and sub5.is_visible():
                sub5.click()
            pg.wait_for_function("() => !!window.SocialComposer.attached()", timeout=20000)
            pg.wait_for_timeout(1200)
            red = pg.evaluate("""() => { const c = document.querySelector('[data-compose-draft] .skribl-inline canvas'); if (!c) return null;
              const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0, all = 0;
              for (let i = 0; i < d.length; i += 4 * 97) { all++; if (d[i] > 180 && d[i + 1] < 90 && d[i + 2] < 110) n++; }
              return all ? Math.round(n / all * 100) / 100 : 0; }""")
            # Posted, it rests on a picture of both on her photo (paintUnder).
            with pg.expect_navigation(timeout=20000):
                pg.click("[data-compose-post]")
            pg.wait_for_timeout(600)
            poster5 = pg.evaluate("() => { const i = document.querySelector('.post-page .skribl-inline-poster'); return i ? i.getAttribute('src') : null; }")
            close_ctx(ctx, pg)
            red_card = None
            try:
                with urllib.request.urlopen(BASE + poster5 if poster5 and poster5.startswith("/") else (poster5 or ""), timeout=20) as r:
                    raw5 = r.read()
                from PIL import Image
                import io
                im5 = Image.open(io.BytesIO(raw5)).convert("RGB")
                k_ = im5.width / 1200
                px5 = im5.load()
                n5 = all5 = 0
                for y in range(int(200 * k_), int(430 * k_), 3):
                    for x in range(int(480 * k_), int(720 * k_), 3):
                        all5 += 1
                        r_, g_, b_ = px5[x, y]
                        if r_ > 180 and g_ < 90 and b_ < 110:
                            n5 += 1
                red_card = round(n5 / all5, 2) if all5 else 0
            except Exception as exc:  # noqa: BLE001 -- no picture is this row's red
                red_card = str(exc)[:80]
            check("on a drawing with a photo, her photo lies under the pen, under the canvas where the Pad's own would,"
                  " as big as the drawing, never the Pad's own photo (nothing of hers recorded as his)",
                  under and under["rgb"][0] > 180 and under["rgb"][1] < 90 and under["below"] and under["same"] and not under["mine"],
                  json.dumps(under))
            check("drawn, Done and Add: the composer's preview plays the two on her photo, as they will post",
                  isinstance(red, (int, float)) and red > 0.5, f"share of the preview that is her photo's red: {red}")
            check("posted, the draw-back rests on a picture of the two on her photo",
                  isinstance(red_card, (int, float)) and red_card > 0.5, f"poster {poster5}; share of its middle that is her photo's red: {red_card}")
            check("on your own drawing the composer and the Pad's pill say \"Drawing back on your own drawing\"",
                  own_pill == "Drawing back on your own drawing" and own_line == "Drawing back on your own drawing",
                  json.dumps({"pill": own_pill, "line": own_line}))
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
            # The row's words as they are said: what a face not drawn yet shows (its
            # initial, hidden from a screen reader: _post.html face) is no word of the row's.
            rows = pg.evaluate("""() => [...document.querySelectorAll('.act-row')].map(a => ({
              text: (() => { const c = a.cloneNode(true); c.querySelectorAll('[aria-hidden="true"]').forEach(e => e.remove());
                             return c.textContent.replace(/\\s+/g, ' ').trim(); })(),
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
                       wide: document.documentElement.scrollWidth <= innerWidth,
                       lefts: [s.querySelector('.db-title'), s.querySelector('.db-tile')].map(e => Math.round(e.getBoundingClientRect().left * 10) / 10),
                       scrolls: (r => r.scrollWidth > r.clientWidth + 1)(s.querySelector('.db-row')) }; }"""
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
            check("a strip long enough to scroll (three on a phone) keeps the page's gutter: its first drawing starts where"
                  " its title does, never on the screen's edge",
                  seen["ana"] and seen["ana"]["scrolls"] and abs(seen["ana"]["lefts"][0] - seen["ana"]["lefts"][1]) < 0.6
                  and seen["ana"]["lefts"][0] >= 15.5, json.dumps({k: [v["lefts"], v["scrolls"]] for k, v in seen.items() if v}))
            check("behind a block (Theo blocked Lea) Lea's is not on the strip Theo sees: \"2 draw-backs\"",
                  bst == 200 and seen["theo"] and seen["theo"]["title"] == "2 draw-backs" and seen["theo"]["tiles"] == want[1:],
                  json.dumps(seen["theo"]))
            # "DRAW BACK", IN WORDS, AT THE END OF THEIR LINE (the walkthrough's
            # mocks, choice 3, the owner's "all yes", Nov 19). Approved at the end
            # of the row of buttons, it ran 10px past the drawing's edge once the
            # row had counts and was cut off on a desk; here it ends where the
            # line does, which on a phone is the drawing's edge. THE ROW IS NOT
            # TOUCHED: its pen and count stay.
            WORD = """() => { const s = document.querySelector('.post-page .db-strip'), b = s && s.querySelector('.db-word');
              const art = document.querySelector('.post-page .post-art').getBoundingClientRect();
              const row = [...document.querySelectorAll('.post-page > .post-row > *')].map(e => e.classList.contains('db-pen') ? 'pen ' + e.textContent.trim()
                            : e.classList.contains('rp-btn') ? 'repost' : e.classList.contains('post-more') ? 'more' : e.classList.contains('lk-heart') || e.querySelector('.lk-heart') ? 'heart' : 'comments');
              if (!b) return { strip: !!s, there: false, row, title: s ? s.querySelector('.db-title').innerText.trim() : null, tiles: s ? !!s.querySelector('.db-row') : false };
              const r = b.getBoundingClientRect(), cs = getComputedStyle(b), t = s.querySelector('.db-title').getBoundingClientRect(), sr = s.getBoundingClientRect();
              const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { strip: true, there: true, says: b.textContent.trim(), icon: !!b.querySelector('svg'), h: Math.round(r.height * 10) / 10, font: cs.fontSize, weight: cs.fontWeight,
                       painted: !!at && b.contains(at), lineEnd: Math.round((sr.right - r.right) * 10) / 10, artEdge: Math.round((art.right - r.right) * 10) / 10,
                       sameLine: Math.abs((r.top + r.height / 2) - (t.top + t.height / 2)) < 1.5, clear: r.left >= t.right + 7.5,
                       title: s.querySelector('.db-title').innerText.trim(), tiles: !!s.querySelector('.db-row'), row,
                       wide: document.documentElement.scrollWidth <= innerWidth,
                       attrs: [b.getAttribute('data-drawback'), b.getAttribute('data-drawback-first'), b.hasAttribute('data-drawback-own')] }; }"""
            words = {}
            for who, screen in ((theo, "phone"), (theo, "desk"), (ana, "phone")):
                ctx, pg = browser_as(b, who, screen=screen)
                pg.goto(BASE + f"/social/p/{cat}")
                ready(pg)
                words[f"{who.handle} {screen}"] = pg.evaluate(WORD)
                if who is theo and screen == "phone" and words[f"{who.handle} {screen}"].get("there"):
                    pg.evaluate("() => document.querySelector('.db-word').scrollIntoView({ block: 'center' })")
                    pg.wait_for_timeout(200)
                    pg.click(".post-page .db-word")
                    try:
                        pg.wait_for_function("() => window.SocialComposer && !!SocialComposer.drawingBack()", timeout=10000)
                        words["tapped"] = pg.evaluate("() => SocialComposer.drawingBack()")
                    except Exception as exc:  # noqa: BLE001
                        words["tapped"] = {"stopped": str(exc).splitlines()[0][:120]}
                close_ctx(ctx, pg)
            wt, wd, wa = words["theo phone"], words["theo desk"], words["ana phone"]
            check("at the end of the draw-backs' line, \"Draw back\" in words with its pen: the site's second button (44px,"
                  " 15px, 600), painted, on the count's own line and clear of it, ending where the line ends (a phone and a"
                  " desk), which on a phone is the drawing's edge; nothing past the screen",
                  all(w.get("there") and w["says"] == "Draw back" and w["icon"] and w["h"] >= 44 and w["font"] == "15px" and w["weight"] == "600"
                      and w["painted"] and w["sameLine"] and w["clear"] and abs(w["lineEnd"]) <= 1 and w["wide"] for w in (wt, wd, wa))
                  and abs(wt.get("artEdge", 99)) <= 1 and wt["title"] == "2 draw-backs" and wa["title"] == "3 draw-backs",
                  json.dumps({k: v for k, v in words.items() if k != "tapped"})[:900])
            check("the row of buttons above it is not touched: comments, repost, heart, the pen with its count, and ⋯",
                  wt.get("row") == ["comments", "repost", "heart", "pen 2", "more"] and wa.get("row") == ["comments", "repost", "heart", "pen 3", "more"],
                  json.dumps({"theo": wt.get("row"), "ana": wa.get("row")}))
            check("a tap on the words is the pen's own: the composer opens drawing back on hers; on her own post it says so"
                  " (your own drawing)",
                  (words.get("tapped") or {}).get("id") == cat and wt.get("attrs") == [cat, "Ana", False] and wa.get("attrs") == [cat, "Ana", True],
                  json.dumps({"tapped": words.get("tapped"), "theo": wt.get("attrs"), "ana": wa.get("attrs")}))
            # THE LINE IS THERE FROM THE START, so the words always have a home;
            # and where it cannot be done there are no words, and with nothing
            # drawn back no line either: signed out, and a Flip of two pages.
            fresh = post_payload(ana, "Section 6, nobody has drawn back on this", drawing(n=24, seed=61))
            pages2 = dict(drawing(n=12, seed=62))
            pages2["frames"] = [dict(pages2["frames"][0]), dict(pages2["frames"][0])]
            pages2["playbackMode"], pages2["fps"] = "flip", 8
            flipped = post_payload(ana, "Section 6, a Flip of two pages", pages2)
            zero = {}
            for key, who, post in (("fresh", theo, fresh), ("signed out", None, fresh), ("a Flip", theo, flipped)):
                ctx, pg = browser_as(b, who)
                pg.goto(BASE + f"/social/p/{post}")
                ready(pg)
                zero[key] = pg.evaluate(WORD)
                close_ctx(ctx, pg)
            check("on a drawing nobody has drawn back on, the line is there from the start: \"No draw-backs yet\" and Draw"
                  " back at its end, no row of drawings under it; signed out, or on a Flip of two pages (which can't be"
                  " drawn back on yet), no words and no line",
                  bool(fresh) and bool(flipped) and zero["fresh"].get("there") and zero["fresh"]["title"] == "No draw-backs yet"
                  and not zero["fresh"]["tiles"] and abs(zero["fresh"].get("lineEnd", 99)) <= 1 and zero["fresh"].get("h", 0) >= 44
                  and zero["signed out"] == {"strip": False, "there": False, "row": zero["signed out"]["row"], "title": None, "tiles": False}
                  and "pen" not in " ".join(zero["signed out"]["row"])
                  and zero["a Flip"].get("strip") is False and zero["a Flip"].get("there") is False,
                  json.dumps(zero)[:900])
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

    # ------------------------------------------------------------------ 8
    # WHAT A DRAW-BACK SAYS OF ITSELF (the walkthrough's mocks, choice 6; the
    # owner's "all yes", Nov 19). Its line and its play button said "drawn in
    # 8 sec" under a cat that took 15: they counted the joined drawing, in
    # which hers plays squeezed to three seconds. Each hand's own drawing time
    # is kept when a draw-back is made, and the line says them, the play
    # button who and the whole. The expected words are worked out here from
    # the drawings themselves, never from the site's own sum.
    if part(8, "what a draw-back says: each hand's time on its line, who and the whole on its play button"):
        try:
            def drew(payload):
                pts = payload["frames"][0]["strokes"]
                return sum(max(0, q["t"] - p["t"]) for p, q in zip(pts, pts[1:]))

            def secs(ms):
                return max(1, int(ms / 1000 + 0.5))

            def slow(payload, ms):
                """The same answer, drawn slower: its points `ms` apart."""
                for i, pt in enumerate(payload["frames"][0]["strokes"]):
                    pt["t"] = i * ms
                return payload

            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            ori = someone(b, "ori", "Ori Vance")
            nia = someone(b, "nia", "Nia Brandt")
            pid = {h: db("select id from social_people where handle_key = ?", (h,))[0][0] for h in ("ana", "theo", "ori")}
            cat = post_payload(ana, "Section 8, the cat", CAT)
            c_s = secs(drew(CAT))
            his = slow(answer(n=40, seed=81), 130)                      # 39 gaps of 130ms: 5 sec
            back = (draw_back(theo, cat, his)[1] or {}).get("post")
            row = db("select hands_json from social_posts where public_id = ?", (back or "",))
            kept = json.loads(row[0][0]) if row and row[0][0] else None
            check("a draw-back keeps whose hands it holds and how long each drew, in whole seconds, hers first: read from"
                  " the two drawings before hers is squeezed",
                  bool(cat) and bool(back) and c_s >= 10 and kept == [[pid["ana"], c_s * 1000], [pid["theo"], 5000]],
                  f"kept {kept}; the cat took {drew(CAT)}ms, his {drew(his)}ms")
            CARD = """(post) => { const c = document.querySelector('.post-card[data-post="' + post + '"]'); if (!c) return null;
              const box = c.querySelector('[data-skribl-inline]'), play = box.querySelector('.skribl-inline-play');
              const pr = play.getBoundingClientRect(), br = box.getBoundingClientRect();
              return { words: play.textContent.trim(), name: box.getAttribute('aria-label'), inside: pr.left >= br.left && pr.right <= br.right,
                       on: (c.querySelector('.post-on') || {}).textContent || null }; }"""
            LINE = """() => { const l = document.querySelector('.post-page > .post-art .skribl-inline-line'), d = l && l.querySelector('.rl-drawn'), k = l && l.querySelector('.rl-skip');
              return { drawn: d ? d.textContent.replace(/\\s+/g, ' ').trim() : null, skip: k ? !k.hidden && k.getClientRects().length > 0 : null }; }"""
            ctx, pg = browser_as(b, ori)
            home(pg)
            pg.evaluate("""(p) => { const c = document.querySelector('.post-card[data-post="' + p + '"]'); if (c) c.scrollIntoView({ block: 'center' }); }""", back)
            pg.wait_for_timeout(500)
            card = pg.evaluate(CARD, back)
            pg.goto(BASE + f"/social/p/{back}")
            ready(pg)
            pg.wait_for_timeout(1500)
            line = pg.evaluate(LINE)
            pg.goto(BASE + "/social/explore")
            pg.wait_for_timeout(800)
            tile = pg.evaluate("""(p) => { const t = document.querySelector('.gal-tile[data-post="' + p + '"]'); if (!t) return null;
              return { says: (t.querySelector('.gal-dur span') || {}).textContent || '', label: t.getAttribute('aria-label') }; }""", back)
            close_ctx(ctx, pg)
            both = f"{c_s + 5} sec"
            check(f"its card's play button says who and the whole: \"Ana + Theo · {both}\" (its name too), inside the drawing;"
                  " never the joined drawing's own time, in which hers plays squeezed",
                  card and card["words"] == f"Ana + Theo · {both}" and card["name"].endswith(f", Ana + Theo · {both}") and card["inside"],
                  json.dumps(card))
            check(f"on its own page its line says each hand's own time, \"Drawn in {c_s} sec + 5 sec\", and nothing about"
                  " pauses skipped; and its Gallery tile says the whole",
                  line["drawn"] == f"Drawn in {c_s} sec + 5 sec ·" and line["skip"] is False
                  and tile and tile["says"].strip() == both and f"drawn in {both}" in (tile["label"] or ""),
                  json.dumps({"line": line, "tile": tile}))
            # A JAM: a draw-back on a draw-back holds every hand before it.
            hers2 = slow(answer(n=31, seed=82), 300)                    # 30 gaps of 300ms: 9 sec
            jam = (draw_back(ori, back, hers2)[1] or {}).get("post")
            jrow = db("select hands_json from social_posts where public_id = ?", (jam or "",))
            jkept = json.loads(jrow[0][0]) if jrow and jrow[0][0] else None
            # ON YOUR OWN DRAWING: two sittings, one person: nobody to name.
            own = (draw_back(ana, cat, slow(answer(n=11, seed=83), 300))[1] or {}).get("post")   # 3 sec
            # SOMEBODY WHO BLOCKED HER is not told whose hand the first is.
            nc = nia.client()
            nc.get("/social/")
            bst, _ = nc.post_json("/social/@ana/block", {})
            seen = {}
            for who, key in ((theo, "theo"), (nia, "nia")):
                ctx, pg = browser_as(b, who)
                home(pg)
                pg.wait_for_timeout(500)
                seen[key] = {k: pg.evaluate(CARD, v) for k, v in (("back", back), ("jam", jam), ("own", own))}
                if key == "theo":
                    pg.goto(BASE + f"/social/p/{jam}")
                    ready(pg)
                    pg.wait_for_timeout(1500)
                    seen["jam line"] = pg.evaluate(LINE)
                    pg.goto(BASE + f"/social/p/{own}")
                    ready(pg)
                    pg.wait_for_timeout(1500)
                    seen["own line"] = pg.evaluate(LINE)
                close_ctx(ctx, pg)
            check(f"a jam holds every hand: three kept, its play button \"Ana + Theo + Ori · {c_s + 14} sec\", its line"
                  f" \"Drawn in {c_s} sec + 5 sec + 9 sec\"",
                  bool(jam) and jkept == [[pid["ana"], c_s * 1000], [pid["theo"], 5000], [pid["ori"], 9000]]
                  and (seen["theo"]["jam"] or {}).get("words") == f"Ana + Theo + Ori · {c_s + 14} sec"
                  and seen["jam line"]["drawn"] == f"Drawn in {c_s} sec + 5 sec + 9 sec ·",
                  json.dumps({"kept": jkept, "card": seen["theo"].get("jam"), "line": seen.get("jam line")}))
            check(f"on your own drawing there is nobody else to name: the play button says \"drawn in {c_s + 3} sec\", the"
                  f" line the two sittings, \"Drawn in {c_s} sec + 3 sec\"",
                  bool(own) and (seen["theo"]["own"] or {}).get("words") == f"drawn in {c_s + 3} sec"
                  and seen["own line"]["drawn"] == f"Drawn in {c_s} sec + 3 sec ·",
                  json.dumps({"card": seen["theo"].get("own"), "line": seen.get("own line")}))
            check("to somebody who blocked her, nobody is named: his card says \"Drew back on a drawing\" and its play button"
                  f" the time alone, \"drawn in {both}\", still the hands' own",
                  bst == 200 and (seen["nia"]["back"] or {}).get("words") == f"drawn in {both}"
                  and "Ana" not in ((seen["nia"]["back"] or {}).get("on") or "Ana"),
                  json.dumps(seen["nia"].get("back")))
            # A QUOTE OF IT says the same whole, in the small card.
            qc = ori.client()
            qc.get("/social/")
            qst, qj = qc.post_json("/social/posts", {"words": "Section 8, look at these two", "quote": back})
            quoted = qj.get("post") if qst == 200 and isinstance(qj, dict) else None
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + f"/social/p/{quoted}")
            ready(pg)
            qsays = pg.evaluate("() => { const q = document.querySelector('.qt-card'); return q ? q.textContent.replace(/\\s+/g, ' ') : null; }")
            close_ctx(ctx, pg)
            check(f"a quote of it says the same whole in its small card: \"drawn in {both}\"",
                  bool(quoted) and f"drawn in {both}" in (qsays or ""), f"{qst}; {qsays}")
            # FROM BEFORE THE HANDS WERE KEPT: said from the two drawings' stored
            # lines while hers is there; once it is gone, what its drawing says.
            db_write("update social_posts set hands_json = null where public_id = ?", (back,))
            ctx, pg = browser_as(b, ori)
            home(pg)
            pg.wait_for_timeout(500)
            before = pg.evaluate(CARD, back)
            close_ctx(ctx, pg)
            ac = ana.client()
            ac.get(f"/social/p/{cat}")
            dst, _ = ac.post_json(f"/social/p/{cat}/delete", {})
            ctx, pg = browser_as(b, ori)
            home(pg)
            pg.wait_for_timeout(500)
            after = pg.evaluate(CARD, back)
            jam_after = pg.evaluate(CARD, jam)
            close_ctx(ctx, pg)
            joined = secs(min(played(CAT["frames"][0]["strokes"])[-1], 3000) + 50 + drew(his))
            check(f"a draw-back from before its hands were kept says them from the two drawings' own lines while hers is there"
                  f" (\"Ana + Theo · {both}\"); once hers is gone it says what its drawing says (\"drawn in {joined} sec\"),"
                  " as it did; and the jam, whose hands are kept and whose own original is still there, says its three"
                  " hands as before",
                  (before or {}).get("words") == f"Ana + Theo · {both}" and dst == 200
                  and (after or {}).get("words") == f"drawn in {joined} sec"
                  and (jam_after or {}).get("words") == f"Ana + Theo + Ori · {c_s + 14} sec",
                  json.dumps({"before": before, "deleted": dst, "after": after, "the jam": jam_after}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    # THE LINE THE PEN DRAWS, IN COLOUR (the owner's own idea, and "All yes",
    # Nov 19: "a nice touch that accentuates our purpose is coloring the line
    # under the pencil signature purple"). Draw back's icon is a pen and the
    # little wave it draws: the wave wears --brand, the pen's line under the
    # chosen tab, and the pen stays in the ink of where it sits. ONE MACRO,
    # SIX PLACES, AND ONE OF THEM IS THE ACTION'S FILL: the pill that rises
    # when a replay ends is the fill itself, where the pen's purple would be a
    # wave nobody sees, so there it stays the button's own white. Read twice
    # each: what the page computes, and what is painted (the colour most of
    # the wave's own band is, on a screen of three pixels to one, where a
    # 1.3px line has whole pixels of itself).
    if part(9, "the pen's line: the pen's purple wherever Draw back's pen is drawn, white on the action's fill"):
        try:
            import io
            from PIL import Image

            def lum(c):
                v = [x / 255 for x in c[:3]]
                v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
                return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

            def ratio(a, c):
                hi, lo = max(lum(a), lum(c)), min(lum(a), lum(c))
                return round((hi + 0.05) / (lo + 0.05), 2)

            def far(a, c):
                return max(abs(x - y) for x, y in zip(a[:3], c[:3]))

            def rgb(css):
                return [round(float(x)) for x in re.findall(r"[\d.]+", css or "")[:3]]

            PEN = """(sel) => { const svg = document.querySelector(sel); if (!svg) return null;
              const p = svg.querySelectorAll('path'), probe = document.createElement('i');
              probe.style.color = 'var(--brand)'; document.body.appendChild(probe);
              const brand = getComputedStyle(probe).color; probe.remove();
              return { paths: p.length, pen: getComputedStyle(p[0]).stroke, line: getComputedStyle(p[p.length - 1]).stroke,
                       ink: getComputedStyle(svg).color, brand, h: svg.getBoundingClientRect().height }; }"""

            def read(pg, sel):
                """What the page computes for the icon at `sel`, and what is
                painted: its ground (the colour most of its box is), the
                wave's colour (the colour most of the wave's own band is,
                the ground apart) and the pen's (the same, above the wave)."""
                got = pg.evaluate(PEN, sel)
                if not got:
                    return None
                pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", sel)
                pg.wait_for_timeout(350)
                im = Image.open(io.BytesIO(pg.locator(sel).first.screenshot(animations="disabled"))).convert("RGB")
                w, h = im.size
                ground = max(im.getcolors(w * h))[1]

                def most(top, bottom):
                    band = [(n, c) for n, c in im.crop((0, round(h * top), w, round(h * bottom))).getcolors(w * h)
                            if far(c, ground) > 24]
                    return list(max(band)[1]) if band else None
                # The wave runs from 18.9 to 20.3 of the icon's 24, a line 2
                # wide: 17.9 to 21.3. The pen ends at 17.5 with its line.
                wave, pen = most(18.4 / 24, 20.9 / 24), most(4 / 24, 15 / 24)
                got.update(ground=list(ground), wave=wave, penPaint=pen,
                           ratio=ratio(wave, ground) if wave else None)
                return got

            ana = someone(b, "ana", "Ana Ruiz")
            theo = someone(b, "theo", "Theo Lin")
            cat = post_payload(ana, "Section 9, the cat", drawing(n=20, seed=41))
            back = (draw_back(theo, cat, answer(n=10, seed=42))[1] or {}).get("post")
            card = f'.post-card[data-post="{cat}"]'
            seen = {}
            for scheme in ("light", "dark"):
                got = seen[scheme] = {}
                # A card's row, and the pill when its replay ends.
                ctx, pg = browser_as(b, theo, scheme=scheme, dpr=3)
                home(pg)
                pg.locator(card).scroll_into_view_if_needed()
                got["a card's row"] = read(pg, card + " .post-row .db-pen svg")
                pg.click(card + " .skribl-inline-play")
                pg.wait_for_function("(s) => !!document.querySelector(s + ' .db-end.is-up')", arg=card, timeout=20000)
                pg.wait_for_timeout(400)
                got["the pill when a replay ends"] = read(pg, card + " .db-end .db-go svg")
                close_ctx(ctx, pg)
                # Her post's own page: its row, the draw-backs' title, the words.
                ctx, pg = browser_as(b, theo, scheme=scheme, dpr=3)
                open_post(pg, cat)
                got["a post's own row"] = read(pg, ".post-page > .post-row .db-pen svg")
                got["the draw-backs' title"] = read(pg, ".db-title svg")
                got["Draw back in words"] = read(pg, ".db-word svg")
                close_ctx(ctx, pg)
                # Her Activity: his draw-back's badge.
                ctx, pg = browser_as(b, ana, scheme=scheme, dpr=3)
                pg.goto(BASE + "/social/activity")
                ready(pg)
                pg.wait_for_timeout(400)
                got["Activity's badge"] = read(pg, ".db-badge svg")
                close_ctx(ctx, pg)
            PAGE = ("a card's row", "a post's own row", "the draw-backs' title", "Draw back in words", "Activity's badge")
            PILL = "the pill when a replay ends"

            def purple(v):
                """The wave is the pen's line, computed and painted; the pen is
                the ink of where it sits, computed and painted, and not the
                wave's colour (so the two can be told apart at all)."""
                return bool(v and v["paths"] == 2 and v["line"] == v["brand"] and v["pen"] == v["ink"] and v["pen"] != v["brand"]
                            and v["wave"] and far(v["wave"], rgb(v["brand"])) <= 6
                            and v["penPaint"] and far(v["penPaint"], rgb(v["ink"])) <= 6)

            def short(v):
                return v and {k: v[k] for k in ("line", "pen", "brand", "wave", "penPaint", "ground", "ratio")}
            bad_a = {f"{s}: {k}": short(seen[s].get(k)) for s in seen for k in PAGE if not purple(seen[s].get(k))}
            check("Draw back's wave is the pen's line (--brand) and its pen the ink of where it sits: on a card's row, a"
                  " post's own row, the draw-backs' title, \"Draw back\" in words and Activity's badge, computed and painted"
                  " (light and dark)", not bad_a and all(len(seen[s]) == 6 for s in seen),
                  json.dumps(bad_a or {k: short(v) for k, v in seen["light"].items() if k in PAGE})[:700])
            low = {f"{s}: {k}": (seen[s].get(k) or {}).get("ratio") for s in seen for k in PAGE
                   if not ((seen[s].get(k) or {}).get("ratio") or 0) >= 3.0}
            check("the wave as painted is 3:1 or more against the ground painted behind it, in each of those five (light and"
                  " dark): a drawn line somebody is meant to see", not low,
                  json.dumps(low or {f"{s}: {k}": seen[s][k]["ratio"] for s in seen for k in PAGE}))

            def white(v):
                """On the fill the wave is the button's own ink with its pen,
                computed and painted, and that ink is not the pen's purple."""
                return bool(v and v["line"] == v["ink"] and v["pen"] == v["ink"] and v["ink"] != v["brand"]
                            and v["wave"] and far(v["wave"], rgb(v["ink"])) <= 6 and (v["ratio"] or 0) >= 3.0)
            check("on the pill that rises when a replay ends, the action's fill, the wave stays the button's own ink with"
                  " its pen (white), painted so and 3:1 or more: the pen's purple on that fill is a wave nobody sees"
                  " (light and dark)", all(white(seen[s].get(PILL)) for s in seen),
                  json.dumps({s: short(seen[s].get(PILL)) for s in seen}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ----------------------------------------------------------------- 10
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
