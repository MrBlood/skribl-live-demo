"""Activity on the Skribl site (phase 2, notifications; docs/SOCIAL-SITE.md
"Built: notifications"), through the demo's own server, with Chromium's
virtual authenticator for the site's people.

  1. THE BELL AND THE RAIL: signed in, a phone's Home and Explore (the bar's
     Gallery) have a bell drawn in our pen at the top right, where Sign in
     sits signed out (44px, painted, to Activity); the bar keeps its four
     places; signed out, a post's page and a profile have none; a desk's rail
     has Activity after the Gallery, lit on its own page (the bell filled, the pen's line); with
     nothing new, no dot anywhere.
  2. THE DOT: something new rings a dot on the bell's shoulder, painted, in
     --new-dot (#e64a78 on light, Blooby's blush on dark), 3:1 or more on its
     ground and ringed in the page's own; on a desk's rail on every page; the
     bell's line 3:1 or more; once Activity is opened, gone; on Activity's
     own page the rail's fades, and a tap on the bell fades it, read on
     every frame.
  3. EACH KIND OF ROW: "said something on your post" (on a post, and on a
     drawing shown outside a post), "answered your comment", "answered with a
     drawing", "drew something on your post": the face, the time as comments
     say it, the words in quotes (two lines at most), the small picture (the
     drawing, or the post's), and the link to the comment on its page.
  4. GROUPING: several since you last looked on one post are one row ("Lou
     and 2 others", "Kai and Jon"), the newest face in front, the newest
     words, the newest opened; answers to your comment the same; a drawing
     its own row; an answer to your answer reaches you; Earlier a row each.
  5. NEW, EARLIER, SEEN ON OPEN: New then Earlier, a dot on each new row;
     opening Activity marks everything seen (the row's time, the bell's dot
     gone, next time Earlier); rows that were new keep their dot while you
     are there.
  6. NEVER IN THE LIST: yourself; a block either way; a person or a comment
     taken down; a comment deleted or removed; an answer under a comment
     hidden from you; anything on a post taken down or a drawing deleted in
     the Library; and the dot agrees.
  7. THE LINK LANDS: a tap on a row opens its comment on its page, in view;
     it glows in the note's tint, the comment alone, and the tint fades, read
     on every frame, nothing moving; on a later page of comments, Load more
     brings it and the page glides there; on a drawing's page too; under
     Reduce Motion it is put there and the tint fades where it sits.
  8. THE DRAW-ONCE: a drawing answer opened from Activity draws itself once,
     sound off, and the post's own waits; at words the post's own plays; under
     Reduce Motion nothing plays.
  9. THE EMPTY STATE: Blooby as his Home Screen icon, "Nothing new yet", the
     words, and Make a skribl, which opens Make's sheet.
 10. WORDS AND TARGETS: every word on Activity (a list, and the empty page)
     at 4.5:1 on what is painted behind it, every target 44px, the rows 76px,
     the dots and the bell's line 3:1; a landed comment's words on the tint;
     phone (touch) and desk, light and dark.
 11. THE DATA: the chain on a populated database (whom each answer answers
     filled from the comment it sits under; the indexes; and back down); the
     bell's two reads on their indexes (the code's own query, planned by
     SQLite); an account deleted with the cascade off leaves answers to it
     answering nobody, in code; an answer keeps whom it answers.
 12. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALACTIVITY_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Activity at /social".
"""
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
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALACTIVITY_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALACTIVITY {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence Activity works.")
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
TMP = tempfile.mkdtemp(prefix="socialactivity-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialactivity-" + secrets.token_hex(8),
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
    return f"10.{90 + _addr[0] // 250}.{_addr[0] % 250}.7"


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

    def _req(self, method, path, body=None, headers=None):
        h = {"X-Forwarded-For": self.xff}
        if self.cookie_header:
            h["Cookie"] = self.cookie_header
        data = None
        if body is not None:
            data = json.dumps(body).encode()
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

    def post_json(self, path, body):
        st, text = self._req("POST", path, body=body, headers={"X-Social-CSRF": self.token or ""})
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text


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
    if init:
        ctx.add_init_script(init)
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
# Deleted in the Library, as its author: Skribl's own DELETE, not the site's.
LIBRARY_DELETE = """async (id) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const r = await fetch('/api/skribls/' + id, { method: 'DELETE', credentials: 'same-origin',
    headers: { 'X-Skribl-CSRF': decodeURIComponent(tok) } });
  return r.status; }"""


def make_post(who, words, seed=0):
    """A post as Home's composer sends one: its public id, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def make_drawing(who, title, seed=0, vis="public"):
    """A drawing from the Pad (shown in the gallery when public): its skribl's public id, or None."""
    who.pg.goto(BASE + "/social/")
    st, sid = who.pg.evaluate(PAD, [title, vis, seed])
    return sid if st == 201 else None


def give_face(who, seed):
    """A face for them, so a row's face says whose it is: a drawing of theirs,
    kept unlisted, named as their face on their row (the face player's still
    picture is its poster). Its skribl's id."""
    sid = make_drawing(who, f"{who.handle}'s face", seed=seed, vis="unlisted")
    db_write("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = ?",
             (sid, who.handle.lower()))
    return sid


def comment(who, on, words, answer_to=None, payload=None):
    """A comment (or an answer, or a drawing) as the box sends one, on a post
    (("p", id)) or a drawing (("s", id)): its public id, or None."""
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


def delete_comment(who, cid):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/c/{cid}/delete", {})[0]


def block(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/block", {})[0]


def skribl_of(post):
    got = db("select skribl_id from social_posts where public_id = ?", (post or "",))
    return got[0][0] if got else None


def skribl_of_comment(cid):
    got = db("select skribl_id from social_comments where public_id = ?", (cid or "",))
    return got[0][0] if got else None


def seen_at(handle):
    got = db("select activity_seen_at from social_people where handle_key = ?", (handle.lower(),))
    return got[0][0] if got else None


def ready(pg):
    """The page and its deferred scripts (they have all run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


# ---- what the page shows, read in the page ---------------------------------------
# The rows of Activity, each section's: what it says, its words, when, its
# faces (a face's still picture names whose it is), its small picture, its
# link, whether it is new and its dot's paint, and its size.
ROWS = r"""() => [...document.querySelectorAll('.act-list')].map(ul => {
  const h = document.getElementById(ul.getAttribute('aria-labelledby'));
  return { sec: h ? h.textContent.trim() : null, rows: [...ul.querySelectorAll(':scope > li > a.act-row')].map(a => {
    const peek = a.querySelector('.act-peek'), when = a.querySelector('.act-when'), pic = a.querySelector('.act-pic'),
          mark = a.querySelector('.act-mark');
    const faces = [...a.querySelectorAll('.face-ring')].map(f => { const i = f.querySelector('img.skribl-face-still');
                                                                   return i ? new URL(i.src).pathname : 'blank'; });
    const pr = pic.getBoundingClientRect(), r = a.getBoundingClientRect();
    let lines = null;
    if (peek) { const lh = parseFloat(getComputedStyle(peek).lineHeight), ph = peek.getBoundingClientRect().height;
                lines = { n: Math.round(ph / lh * 100) / 100, cut: peek.scrollHeight > peek.clientHeight + 1 }; }
    let front = null;
    const two = a.querySelector('.act-faces');
    if (two) { const f = two.querySelector('.face-ring:last-child'), r2 = f.getBoundingClientRect(),
                     at = document.elementFromPoint(r2.left + r2.width * 0.7, r2.top + r2.height * 0.7);
               front = at && f.contains(at) ? faces[faces.length - 1] : null; }
    return { say: a.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim(), peek: peek ? peek.textContent : null,
             lines, when: when ? when.textContent.trim() : null, faces, front,
             pic: getComputedStyle(pic).backgroundImage, pw: Math.round(pr.width), ph: Math.round(pr.height),
             href: new URL(a.href).pathname + new URL(a.href).hash, isNew: a.classList.contains('is-new'),
             mark: getComputedStyle(mark).backgroundColor, h: Math.round(r.height * 10) / 10,
             sr: (a.querySelector('.sr') || {}).textContent || null }; }) }; })"""

# A bell (the phone's top, or the rail's Activity): its box, whether it is
# painted where it stands, its icon, its name, its line against its ground;
# and its dot, when it has one: its paint, its colours and its contrast.
BELL = r"""(sel) => { const a = document.querySelector(sel); if (!a || !a.getClientRects().length) return null;
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ratio = (x, y) => { const p = lum(x), q = lum(y); return Math.round((Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05) * 100) / 100; };
  // A colour as it is painted: folded over its ground by its own alpha (a faint line reads faint).
  const over = (c, g) => c[3] >= 1 ? c : [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const r = a.getBoundingClientRect(), svg = a.querySelector('svg.ic-bell');
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const g = ground(a), top = document.querySelector('body > .top').getBoundingClientRect();
  const out = { w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10, right: Math.round(innerWidth - r.right),
    mid: Math.round((r.top + r.height / 2 - (top.top + top.height / 2)) * 10) / 10,
    label: a.getAttribute('aria-label'), href: new URL(a.href).pathname, hit: !!at && (at === a || a.contains(at)),
    pen: !!svg && svg.classList.contains('pen-ic'), filled: !!svg && !!svg.querySelector('path[fill="currentColor"]'),
    current: a.getAttribute('aria-current'), line: svg ? ratio(over(rgba(getComputedStyle(svg).color), g), g) : null, dot: null,
    underline: !!a.querySelector('.tab-name .pen-line') };
  const d = a.querySelector('.act-dot');
  if (d) { const dr = d.getBoundingClientRect(), cs = getComputedStyle(d);
    const hit = document.elementFromPoint(dr.left + dr.width / 2, dr.top + dr.height / 2);
    out.dot = { fill: cs.fill, stroke: cs.stroke, opacity: +cs.opacity, painted: hit === d, k: ratio(over(rgba(cs.fill), g), g),
                page: getComputedStyle(document.body).backgroundColor, going: d.classList.contains('is-going') }; }
  return out; }"""

# The bar's places (a phone) or the rail's (a desk), those shown, in order.
PLACES = """() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')].filter(e => e.getClientRects().length)
  .map(e => e.classList.contains('brand') ? 'brand' : e.classList.contains('tab-activity') ? 'Activity'
       : e.classList.contains('tab-make') ? 'Make' : e.classList.contains('tab-you') ? 'You'
       : (e.querySelector('.tab-name') || e).textContent.trim())"""

# From the page's first frame: the place it is scrolled to, and the comment
# the address names (#c-<id>): there, glowing (is-landed), its tint's opacity,
# colour and height; and every bell dot's opacity. Read on every animation
# frame for five seconds, from an init script, so a page's first frames are
# read too (verify_glide's way: never a recording that drops frames).
FRAMES = r"""window.__frames = [];
(function () { const t0 = performance.now(); const step = () => {
  const m = /^#(c-[A-Za-z0-9_-]+)$/.exec(location.hash || ''); const li = m ? document.getElementById(m[1]) : null;
  const f = { t: Math.round(performance.now() - t0), y: Math.round(scrollY * 10) / 10, there: !!li, landed: false };
  if (li && li.classList.contains('is-landed')) { const cs = getComputedStyle(li, '::before');
    Object.assign(f, { landed: true, op: +cs.opacity, bg: cs.backgroundColor, h: parseFloat(cs.height) }); }
  const d = document.querySelector('.act-dot'); if (d) f.dot = +getComputedStyle(d).opacity;
  window.__frames.push(f);
  if (performance.now() - t0 < 5000) requestAnimationFrame(step); };
  requestAnimationFrame(step); })();"""

# EVERY PLAY ASKED FOR, from the page's start: the player's mount (what posts.js
# and comments.js call) is wrapped as the player's own script sets it, so each
# player they get back records its play() (a post's own started and stopped a
# moment later by another is a start all the same, which states sampled
# afterwards cannot see).
PLAYS = """window.__plays = [];
(function () { let api;
  Object.defineProperty(window, 'SkriblInline', { configurable: true, get() { return api; }, set(v) {
    api = v; if (!v || v.__wrapped) return; const mount = v.mount;
    v.mount = function () { const ps = mount.apply(this, arguments) || [];
      ps.forEach(p => { if (p.__hooked) return; p.__hooked = true; const play = p.play;
        p.play = function () { try { window.__plays.push(p.state().id); } catch (e) { window.__plays.push('?'); }
                               return play.apply(this, arguments); }; });
      return ps; };
    v.__wrapped = true; } }); })();"""

STATES = """() => (window.SkriblInline ? SkriblInline.players() : []).map(p => { const s = p.state();
  return { id: s.id, state: s.state, ms: Math.round(s.elapsedMs || 0), muted: s.muted }; })"""

# Every word painted in the page's roots against what is painted behind it,
# every target and every text field (verify_socialcomments' census).
READ = r"""(sel) => {
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
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

# A comment's words, name and time against the note's tint over the page (a
# landed comment: the tint is its ::before, which the census cannot see).
ON_TINT = r"""(id) => { const li = document.getElementById('c-' + id); if (!li) return null;
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; };
  const tint = rgba(getComputedStyle(li, '::before').backgroundColor), page = rgba(getComputedStyle(document.body).backgroundColor);
  if (!tint || !li.classList.contains('is-landed')) return { landed: false };
  const g = over(tint, page);
  const k = sel => { const e = li.querySelector(':scope > .cm-main ' + sel); return e ? ratio(over(rgba(getComputedStyle(e).color), g), g) : null; };
  return { landed: true, words: k('.cm-words'), name: k('.cm-name'), when: k('.cm-when'), answer: k('[data-cm-answer]') }; }"""


def tap_row(pg, words):
    """Tap the row whose quote is these words (found by what it says, never by
    its link, so a wrong link fails its own row) and wait for where it goes."""
    row = pg.locator("a.act-row", has_text=words).first
    with pg.expect_navigation():
        row.tap()


def section_named(secs, name):
    return next((s["rows"] for s in secs if s["sec"] == name), [])


def poster(sid):
    return f"/s/{sid}/poster"


def glide_of(ys):
    """How the page moved over frames: the frames it moved on, its largest
    step and the whole way (a snap goes the whole way in one frame)."""
    steps = [abs(b - a) for a, b in zip(ys, ys[1:])]
    return {"frames": len([s for s in steps if s > 0.5]), "step": max(steps or [0]), "way": abs(ys[-1] - ys[0]) if ys else 0}


def faded(ops):
    """Frames shown part-way between whole and gone."""
    return len([o for o in ops if o is not None and 0.03 < o < 0.97])


LIGHT_DOT, DARK_DOT = "rgb(230, 74, 120)", "rgb(255, 111, 145)"
LIGHT_PAGE, DARK_PAGE = "rgb(251, 252, 253)", "rgb(11, 13, 18)"
TINT = {"light": "rgba(124, 92, 255, 0.12)", "dark": "rgba(124, 92, 255, 0.18)"}

# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what changes then
# changes because the code said so. And the bell's two reads, as the code
# builds them, planned by SQLite.
PROBE = r"""
import json, sys, types
from datetime import datetime, timezone
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
app = create_app()
with app.app_context():
    from social.models import Comment, Person
    from social.accounts import delete_person
    from social.activity import _query
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    handle = sys.argv[1]
    who = db.session.execute(sa.select(Person).where(Person.handle_key == handle)).scalar_one()
    answers = [r[0] for r in db.session.execute(sa.select(Comment.public_id).where(Comment.to_person_id == who.id,
                                                                                    Comment.person_id != who.id,
                                                                                    Comment.owner_id != who.id))]
    me = types.SimpleNamespace(id=who.id, public_id=who.public_id)
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plans = []
    for which in (Comment.owner_id == who.id, Comment.to_person_id == who.id):
        sql = str(_query(me, frozenset({-1}), which, since, 20).compile(dialect=sqlite.dialect(),
                                                                       compile_kwargs={"literal_binds": True}))
        plans.append([r[3] for r in db.session.execute(sa.text("EXPLAIN QUERY PLAN " + sql))])
    delete_person(db.session, who.id)
    db.session.commit()
    left = db.session.execute(sa.select(Comment.public_id, Comment.to_person_id).where(Comment.public_id.in_(answers or ["-"]))).all()
    print(json.dumps({"fk": fk, "answers": len(answers), "left": [[p, t] for p, t in left], "plans": plans}))
"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the bell and the rail: where they are, and no dot with nothing new"):
        try:
            ann = someone(b, "ann", "Ann Lee")
            post = make_post(ann, "Section 1, a quiet snail", seed=11)
            got = {}
            ctx, pg = browser_as(b, ann)
            for page, path in (("home", "/social/"), ("explore", "/social/explore")):
                go(pg, path)
                got[page] = {"bell": pg.evaluate(BELL, ".top-bell"), "bar": pg.evaluate(PLACES)}
            go(pg, f"/social/p/{post}")
            got["post"] = pg.evaluate(BELL, ".top-bell")
            go(pg, "/social/@ann")
            got["profile"] = pg.evaluate(BELL, ".top-bell")
            go(pg, "/social/activity")
            got["activity bar"] = pg.evaluate("() => [...document.querySelectorAll('nav.nav [aria-current]')].filter(e => e.getClientRects().length).length")
            close_ctx(ctx, pg)
            nctx, npg = browser_as(b, None)
            go(npg, "/social/explore")
            signed_out = {"bell": npg.evaluate(BELL, ".top-bell"),
                          "signin": npg.evaluate("() => { const a = document.querySelector('.top-signin'); if (!a) return null;"
                                                 " const r = a.getBoundingClientRect(), t = document.querySelector('body > .top').getBoundingClientRect();"
                                                 " return { right: Math.round(innerWidth - r.right), mid: Math.round((r.top + r.height / 2 - (t.top + t.height / 2)) * 10) / 10 }; }")}
            close_ctx(nctx, npg)
            dctx, dpg = browser_as(b, ann, screen="desk")
            go(dpg, "/social/")
            desk = {"rail": dpg.evaluate(PLACES), "act": dpg.evaluate(BELL, "nav.nav .tab-activity"),
                    "top": dpg.evaluate(BELL, ".top-bell")}
            go(dpg, "/social/activity")
            desk["lit"] = dpg.evaluate(BELL, "nav.nav .tab-activity")
            desk["current"] = dpg.evaluate("() => [...document.querySelectorAll('nav.nav [aria-current]')].map(e => e.className)")
            close_ctx(dctx, dpg)
            bells = [got["home"]["bell"], got["explore"]["bell"]]
            check("signed in, a phone's Home and the Gallery (Explore) have the bell at the top right, where Sign in sits"
                  " signed out: a 44px link to Activity, painted, drawn in our pen (not filled), named Activity, on the"
                  " top's middle; the bar keeps its four places (Home, Gallery, Make, You)",
                  all(x and x["w"] >= 44 and x["h"] >= 44 and x["hit"] and x["pen"] and not x["filled"]
                      and x["href"] == "/social/activity" and x["label"] == "Activity" and x["right"] <= 16
                      and abs(x["mid"]) <= 1 for x in bells)
                  and signed_out["signin"] and signed_out["signin"]["right"] <= 16 and abs(signed_out["signin"]["mid"]) <= 1
                  and got["home"]["bar"] == ["Home", "Gallery", "Make", "You"]
                  and got["explore"]["bar"] == ["Home", "Gallery", "Make", "You"],
                  f"bells {bells}; signed out's Sign in {signed_out['signin']}; bars {got['home']['bar']} / {got['explore']['bar']}")
            check("signed out there is no bell (Sign in stays there), and a post's page and a profile have none (their tops"
                  " say their own)",
                  signed_out["bell"] is None and got["post"] is None and got["profile"] is None,
                  f"signed out {signed_out['bell']}; post {got['post']}; profile {got['profile']}")
            check("on a desk the rail has Activity after the Gallery (its bell drawn, a 52px row to Activity), and the"
                  " phone's top is not shown",
                  desk["rail"] == ["brand", "Home", "Gallery", "Activity", "Make", "Settings", "You"] and desk["act"]
                  and desk["act"]["pen"] and not desk["act"]["filled"] and desk["act"]["h"] >= 52
                  and desk["act"]["href"] == "/social/activity" and desk["act"]["hit"] and desk["top"] is None,
                  f"rail {desk['rail']}; Activity {desk['act']}; top {desk['top']}")
            check("on Activity's own page its place is lit on a desk (the bell filled, the pen's line under its name, the"
                  " page you are on), a phone's bar marks no place, and with nothing new there is no dot anywhere",
                  desk["lit"] and desk["lit"]["filled"] and desk["lit"]["underline"] and desk["lit"]["current"] == "page"
                  and desk["current"] == ["tab tab-activity"] and got["activity bar"] == 0
                  and all(x and x["dot"] is None for x in bells + [desk["act"], desk["lit"]]),
                  f"lit {desk['lit']}; current {desk['current']}; phone's bar marks {got['activity bar']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "the dot: painted in --new-dot, light and dark, on the rail everywhere; gone once looked; it fades"):
        try:
            bea = someone(b, "bea", "Bea Holt")
            cyd = someone(b, "cyd", "Cyd Moss")
            post = make_post(bea, "Section 2, a kite", seed=21)
            comment(cyd, ("p", post), "Section 2, what a kite")
            seen = {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, bea, scheme=scheme)
                for page, path in (("home", "/social/"), ("explore", "/social/explore")):
                    go(pg, path)
                    seen[("phone", scheme, page)] = pg.evaluate(BELL, ".top-bell")
                close_ctx(ctx, pg)
                dctx, dpg = browser_as(b, bea, screen="desk", scheme=scheme)
                for page, path in (("home", "/social/"), ("post", f"/social/p/{post}"), ("profile", "/social/@cyd")):
                    go(dpg, path)
                    seen[("desk", scheme, page)] = dpg.evaluate(BELL, "nav.nav .tab-activity")
                close_ctx(dctx, dpg)
            want = {"light": (LIGHT_DOT, LIGHT_PAGE), "dark": (DARK_DOT, DARK_PAGE)}
            dots = {" ".join(k): (v or {}).get("dot") for k, v in seen.items()}
            check("something new rings a dot on the bell's shoulder, painted where it stands, in --new-dot (#e64a78 on"
                  " light, Blooby's own blush on dark), 3:1 or more on its ground and ringed in the page's own; the bell"
                  " says \"Activity, something new\": a phone's Home and Explore",
                  all(seen[("phone", s, pg_)] and seen[("phone", s, pg_)]["dot"]
                      and seen[("phone", s, pg_)]["dot"]["painted"] and seen[("phone", s, pg_)]["dot"]["fill"] == want[s][0]
                      and seen[("phone", s, pg_)]["dot"]["stroke"] == want[s][1] and seen[("phone", s, pg_)]["dot"]["k"] >= 3
                      and seen[("phone", s, pg_)]["dot"]["opacity"] == 1
                      and seen[("phone", s, pg_)]["label"] == "Activity, something new"
                      for s in ("light", "dark") for pg_ in ("home", "explore")),
                  json.dumps({k: d for k, d in dots.items() if k.startswith("phone")}))
            check("on a desk the rail's Activity wears the same dot on every page (Home, a post's page, a profile), named"
                  " so, light and dark",
                  all(seen[("desk", s, pg_)] and seen[("desk", s, pg_)]["dot"] and seen[("desk", s, pg_)]["dot"]["painted"]
                      and seen[("desk", s, pg_)]["dot"]["fill"] == want[s][0] and seen[("desk", s, pg_)]["dot"]["k"] >= 3
                      and seen[("desk", s, pg_)]["label"] == "Activity, something new"
                      for s in ("light", "dark") for pg_ in ("home", "post", "profile")),
                  json.dumps({k: d for k, d in dots.items() if k.startswith("desk")}))
            lines = {" ".join(k): (v or {}).get("line") for k, v in seen.items()}
            check("the bell's line reads 3:1 or more on its ground, at the top and in the rail, light and dark",
                  all(x is not None and x >= 3 for x in lines.values()), json.dumps(lines))
            # Opened: the dot goes. On the desk's Activity page the rail's fades
            # once the page is there, read on every frame from its first.
            dctx, dpg = browser_as(b, bea, screen="desk", init=FRAMES)
            go(dpg, "/social/activity", wait=2600)
            rail_frames = dpg.evaluate("() => window.__frames.map(f => f.dot)")
            stamped = seen_at("bea")
            go(dpg, "/social/")
            after_desk = dpg.evaluate(BELL, "nav.nav .tab-activity")
            close_ctx(dctx, dpg)
            ctx, pg = browser_as(b, bea)
            go(pg, "/social/")
            after_phone = pg.evaluate(BELL, ".top-bell")
            close_ctx(ctx, pg)
            ops = [o for o in rail_frames if o is not None]
            check("once Activity is opened the dot is gone (the bell plain, named Activity, on a phone and a desk), and on"
                  " Activity's own page the rail's dot fades away, a fade over frames, never a snap",
                  stamped is not None and after_desk and after_desk["dot"] is None and after_phone
                  and after_phone["dot"] is None and after_phone["label"] == "Activity"
                  and ops and ops[0] >= 0.97 and ops[-1] <= 0.03 and faded(ops) >= 4,
                  f"seen {stamped}; desk {after_desk and after_desk['dot']}; phone {after_phone and after_phone['dot']};"
                  f" rail dot frames {len(ops)}, part-way {faded(ops)}, first {ops[:2]} last {ops[-2:]}")
            # A tap on the bell lets the dot go as Activity opens: read on every
            # frame, with the way there held back so the page stays to be read.
            comment(cyd, ("p", post), "Section 2, and again")
            ctx, pg = browser_as(b, bea)
            go(pg, "/social/")
            before = pg.evaluate(BELL, ".top-bell")
            pg.evaluate("""() => { document.addEventListener('click', e => { if (e.target.closest('.top-bell')) e.preventDefault(); }, true);
              window.__dots = []; const d = document.querySelector('.top-bell .act-dot'), t0 = performance.now();
              const step = () => { window.__dots.push(+getComputedStyle(d).opacity); if (performance.now() - t0 < 1400) requestAnimationFrame(step); };
              requestAnimationFrame(step); }""")
            pg.wait_for_timeout(150)
            pg.tap(".top-bell")
            pg.wait_for_timeout(1400)
            tap_ops = pg.evaluate("() => window.__dots")
            seen_class = pg.evaluate("() => document.querySelector('.top-bell').classList.contains('is-seen')")
            close_ctx(ctx, pg)
            check("a tap on the bell fades its dot while Activity opens (so a page brought back whole has it gone), over"
                  " frames, never a snap",
                  before and before["dot"] and seen_class and tap_ops and tap_ops[0] >= 0.97 and tap_ops[-1] <= 0.03
                  and faded(tap_ops) >= 4,
                  f"is-seen {seen_class}; frames {len(tap_ops)}, part-way {faded(tap_ops)}, last {tap_ops[-2:]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "each kind of row: the words, the face, when, the quote, the picture, the link"):
        try:
            dan = someone(b, "dan", "Dan Reyes")
            eli = someone(b, "eli", "Eli Moss")
            fay = someone(b, "fay", "Fay Lind")
            gus = someone(b, "gus", "Gus Hart")
            hal = someone(b, "hal", "Hal Ito")
            eli_face = give_face(eli, 31)
            pst = make_post(dan, "Section 3, a snail", seed=32)
            pst2 = make_post(dan, "Section 3, a cottage", seed=33)
            sid = make_drawing(dan, "Section 3, a wave", seed=34)
            q = make_post(gus, "Section 3, Gus's cat", seed=35)
            c_said = comment(eli, ("p", pst), "That spiral is so good.")
            c_drew = comment(gus, ("p", pst), "", payload=drawing(seed=36))
            c_dan = comment(dan, ("p", q), "Three whiskers on each side.")
            c_ans = comment(fay, ("p", q), "Ha, I counted too.", answer_to=c_dan)
            c_ansd = comment(hal, ("p", q), "For you", answer_to=c_dan, payload=drawing(seed=37))
            c_on_s = comment(eli, ("s", sid), "That wave!")
            long = ("This cottage makes me want to walk up that hill at dusk and knock on the door and ask whoever lives"
                    " there for a cup of tea and a long talk about the mountains behind it, the thin ones far away.")
            c_long = comment(fay, ("p", pst2), long)
            ctx, pg = browser_as(b, dan)
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            rows = {r["href"].split("#c-")[-1]: r for s in secs for r in s["rows"]}
            want = {
                c_said: ("Eli said something on your post", f"/social/p/{pst}#c-{c_said}", skribl_of(pst), "“That spiral is so good.”"),
                c_drew: ("Gus drew something on your post", f"/social/p/{pst}#c-{c_drew}", skribl_of_comment(c_drew), None),
                c_ans: ("Fay answered your comment", f"/social/p/{q}#c-{c_ans}", skribl_of(q), "“Ha, I counted too.”"),
                c_ansd: ("Hal answered with a drawing", f"/social/p/{q}#c-{c_ansd}", skribl_of_comment(c_ansd), "“For you”"),
                c_on_s: ("Eli said something on your post", f"/social/b/{sid}#c-{c_on_s}", sid, "“That wave!”"),
            }
            bad = {}
            for cid, (say_, href, pic, peek) in want.items():
                r = rows.get(cid)
                if (not r or r["say"] != say_ or r["href"] != href or not r["isNew"] or r["sr"] != "New: "
                        or not re.fullmatch(r"now|\d+m", r["when"] or "")):
                    bad[cid] = r and {k: r[k] for k in ("say", "href", "when", "isNew", "sr")}
            faces = {"eli": rows.get(c_said, {}).get("faces"), "eli on the drawing": rows.get(c_on_s, {}).get("faces"),
                     "fay": rows.get(c_ans, {}).get("faces")}
            check("each kind of row says who and what in the mock's words (\"Eli said something on your post\", \"Fay"
                  " answered your comment\", \"Hal answered with a drawing\", \"Gus drew something on your post\"), with"
                  " their face, when as comments say it (\"now\", \"5m\"), New for a screen reader, and one link to the"
                  " comment on its page, a post's or a drawing's",
                  not bad and len(rows) == 6 and faces["eli"] == [poster(eli_face)]
                  and faces["eli on the drawing"] == [poster(eli_face)] and faces["fay"] == ["blank"],
                  f"wrong {bad}; rows {len(rows)}; faces {faces}")
            peeks = {cid: rows.get(cid, {}).get("peek") for cid in want}
            lng = rows.get(c_long, {})
            check("their words under it in quotes, two lines at most (a long one cut at two), and none for a drawing"
                  " alone",
                  all(peeks[cid] == want[cid][3] for cid in want)
                  and lng.get("lines") and 1.9 <= lng["lines"]["n"] <= 2.1 and lng["lines"]["cut"]
                  and (lng.get("peek") or "").startswith("“This cottage"),
                  f"quotes {peeks}; the long one {lng.get('lines')}")
            pics = {cid: rows.get(cid, {}).get("pic") for cid in want}
            check("the small picture is the drawing they answered with or drew, or else the post's (or the drawing's),"
                  " cut from its poster, 52px",
                  all(pics[cid] and poster(want[cid][2]) in pics[cid] for cid in want)
                  and all(rows[cid]["pw"] == 52 and rows[cid]["ph"] == 52 for cid in want if cid in rows),
                  json.dumps(pics))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "grouping: several since you last looked are one row; answers the same; a drawing its own; Earlier each"):
        try:
            ivy = someone(b, "ivy", "Ivy Chen")
            jon = someone(b, "jon", "Jon Park")
            kai = someone(b, "kai", "Kai Dunn")
            lou = someone(b, "lou", "Lou Grant")
            moe = someone(b, "moe", "Moe Diaz")
            fj, fk, fl = give_face(jon, 41), give_face(kai, 42), give_face(lou, 43)
            r1 = make_post(ivy, "Section 4, three on one", seed=44)
            r2 = make_post(ivy, "Section 4, two on one", seed=45)
            m1 = make_post(moe, "Section 4, Moe's", seed=46)
            m2 = make_post(moe, "Section 4, Moe's second", seed=47)
            g1 = [comment(jon, ("p", r1), "Jon on r1"), comment(kai, ("p", r1), "Kai on r1"),
                  comment(lou, ("p", r1), "Lou on r1, the newest")]
            comment(jon, ("p", r2), "Jon on r2")
            k2 = comment(kai, ("p", r2), "Kai on r2")
            mine = comment(ivy, ("p", m1), "Ivy on Moe's")
            comment(jon, ("p", m1), "Jon answers Ivy", answer_to=mine)
            k_ans = comment(kai, ("p", m1), "Kai answers Ivy", answer_to=mine)
            l_drw = comment(lou, ("p", m1), "A drawing for Ivy", answer_to=mine, payload=drawing(seed=48))
            moe_top = comment(moe, ("p", m2), "Moe's own words")
            ivy_ans = comment(ivy, ("p", m2), "Ivy answers Moe", answer_to=moe_top)
            j_to_ivy = comment(jon, ("p", m2), "Jon answers Ivy's answer", answer_to=ivy_ans)
            ctx, pg = browser_as(b, ivy)
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            new = section_named(secs, "New")
            by = {r["href"]: r for r in new}
            row1 = by.get(f"/social/p/{r1}#c-{g1[2]}")
            check("three since you last looked on one post are one row: \"Lou and 2 others said something on your post\","
                  " the newest face in front and the next behind, the newest words, opening the newest",
                  row1 is not None and row1["say"] == "Lou and 2 others said something on your post"
                  and row1["faces"] == [poster(fk), poster(fl)] and row1["front"] == poster(fl)
                  and row1["peek"] == "“Lou on r1, the newest”"
                  and not any(r["href"].endswith(g1[0]) or r["href"].endswith(g1[1]) for r in new),
                  f"{row1}; New: {[r['say'] for r in new]}")
            row2 = by.get(f"/social/p/{r2}#c-{k2}")
            row3 = by.get(f"/social/p/{m1}#c-{k_ans}")
            row4 = by.get(f"/social/p/{m1}#c-{l_drw}")
            check("two are \"Kai and Jon\"; answers to your comment from two people are one row (\"Kai and Jon answered"
                  " your comment\", opening the newest); a drawing answer beside them keeps its own row",
                  row2 is not None and row2["say"] == "Kai and Jon said something on your post"
                  and row3 is not None and row3["say"] == "Kai and Jon answered your comment"
                  and row4 is not None and row4["say"] == "Lou answered with a drawing" and row4["faces"] == [poster(fl)],
                  f"two {row2 and row2['say']}; answers {row3 and row3['say']}; drawing {row4 and row4['say']};"
                  f" New: {[r['say'] for r in new]}")
            row5 = by.get(f"/social/p/{m2}#c-{j_to_ivy}")
            to = db("select t.handle, par.public_id from social_comments c join social_people t on t.id = c.to_person_id"
                    " join social_comments par on par.id = c.parent_id where c.public_id = ?", (j_to_ivy or "",))
            check("an answer to your answer (it sits under somebody else's comment, one level deep) reaches you as \"Jon"
                  " answered your comment\": its row keeps whom it answers",
                  row5 is not None and row5["say"] == "Jon answered your comment" and to == [("ivy", moe_top)],
                  f"row {row5 and row5['say']}; whom and under {to}")
            go(pg, "/social/activity")
            again = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            early = section_named(again, "Earlier")
            r1_rows = [r["say"] for r in early if r["href"].startswith(f"/social/p/{r1}#")]
            check("once looked, Earlier keeps a row for each, as it was said (no \"and 2 others\" there), and nothing is new",
                  sorted(r1_rows) == ["Jon said something on your post", "Kai said something on your post",
                                      "Lou said something on your post"]
                  and not section_named(again, "New") and not any(" others" in r["say"] or " and " in r["say"] for r in early),
                  f"r1 under Earlier {r1_rows}; New {section_named(again, 'New')[:1]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "new and earlier, seen on open"):
        try:
            ned = someone(b, "ned", "Ned Shaw")
            ola = someone(b, "ola", "Ola Berg")
            pia = someone(b, "pia", "Pia Ruiz")
            post = make_post(ned, "Section 5, a boat", seed=51)
            c1 = comment(ola, ("p", post), "Section 5, the first")
            before = seen_at("ned")
            ctx, pg = browser_as(b, ned)
            go(pg, "/social/activity")
            first = pg.evaluate(ROWS)
            stamped = seen_at("ned")
            pg.wait_for_timeout(1500)
            still = pg.evaluate(ROWS)
            c2 = comment(pia, ("p", post), "Section 5, the second")
            go(pg, "/social/activity")
            second = pg.evaluate(ROWS)
            go(pg, "/social/")
            bell = pg.evaluate(BELL, ".top-bell")
            go(pg, "/social/activity")
            third = pg.evaluate(ROWS)
            close_ctx(ctx, pg)
            new2, early2 = section_named(second, "New"), section_named(second, "Earlier")
            check("New then Earlier: a dot on each new row (in --new-dot) and none on an earlier one, newest first in each",
                  [s["sec"] for s in second] == ["New", "Earlier"]
                  and [r["href"] for r in new2] == [f"/social/p/{post}#c-{c2}"]
                  and [r["href"] for r in early2] == [f"/social/p/{post}#c-{c1}"]
                  and all(r["isNew"] and r["mark"] == LIGHT_DOT for r in new2)
                  and all(not r["isNew"] and r["mark"] in ("rgba(0, 0, 0, 0)", "transparent") for r in early2),
                  f"{[(s['sec'], [(r['say'], r['isNew'], r['mark']) for r in s['rows']]) for s in second]}")
            check("opening Activity marks everything seen: their row keeps when, the bell has no dot after, and next time"
                  " what was new sits under Earlier",
                  before is None and stamped is not None and bell and bell["dot"] is None
                  and [s["sec"] for s in third] == ["Earlier"]
                  and [r["href"].split("#c-")[1] for r in section_named(third, "Earlier")] == [c2, c1],
                  f"seen {before} -> {stamped}; bell's dot {bell and bell['dot']}; next time {[s['sec'] for s in third]}")
            check("rows that were new keep their dot while you are there",
                  [s["sec"] for s in first] == ["New"] and [s["sec"] for s in still] == ["New"]
                  and all(r["isNew"] and r["mark"] == LIGHT_DOT for r in section_named(still, "New")),
                  f"at first {[s['sec'] for s in first]}; after a moment {[(s['sec'], [r['mark'] for r in s['rows']]) for s in still]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "never in the list: yourself, the hidden, the taken down, the deleted, the gone; the dot agrees"):
        try:
            qin = someone(b, "qin", "Qin Hale")
            names = {"ray": "Ray Cole", "sal": "Sal Vega", "tia": "Tia Ross", "uma": "Uma Pratt", "vic": "Vic Lowe",
                     "wes": "Wes Baird", "yuri": "Yuri Kahn", "zed": "Zed Okoro", "abe": "Abe Nash", "cora": "Cora Fenn",
                     "eve": "Eve Platt", "gil": "Gil Marsh"}
            pp = {h: someone(b, h, n) for h, n in names.items()}
            post = make_post(qin, "Section 6, a lighthouse", seed=61)
            own = comment(qin, ("p", post), "Qin on her own post")
            own_ans = comment(qin, ("p", post), "Qin answers herself", answer_to=own)
            ray_c = comment(pp["ray"], ("p", post), "Ray, soon blocked")
            yuri_c = comment(pp["yuri"], ("p", post), "Yuri, under Ray's", answer_to=ray_c)
            sal_c = comment(pp["sal"], ("p", post), "Sal, who will block Qin")
            tia_c = comment(pp["tia"], ("p", post), "Tia, soon taken down")
            uma_c = comment(pp["uma"], ("p", post), "Uma, this one taken down")
            vic_c = comment(pp["vic"], ("p", post), "Vic, deleting this")
            wes_c = comment(pp["wes"], ("p", post), "Wes, removed by Qin")
            zpost = make_post(pp["zed"], "Section 6, Zed's", seed=62)
            on_z = comment(qin, ("p", zpost), "Qin on Zed's")
            abe_c = comment(pp["abe"], ("p", zpost), "Abe answers Qin", answer_to=on_z)
            dsid = make_drawing(pp["cora"], "Section 6, Cora's drawing", seed=63)
            on_d = comment(qin, ("s", dsid), "Qin on Cora's drawing")
            eve_c = comment(pp["eve"], ("s", dsid), "Eve answers Qin", answer_to=on_d)
            gil_c = comment(pp["gil"], ("p", post), "Gil, who stays")
            # Read under Earlier, where each comment is a row of its own (New
            # groups them): the first look marks them seen.
            ctx, pg = browser_as(b, qin)
            go(pg, "/social/activity")
            go(pg, "/social/activity")
            all_there = {r["href"].split("#c-")[-1] for s in pg.evaluate(ROWS) for r in s["rows"]}
            # Then each is hidden, taken down, deleted or gone.
            block(qin, "ray")
            block(pp["sal"], "qin")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'tia'")
            db_write("update social_comments set taken_down_at = datetime('now') where public_id = ?", (uma_c,))
            vic_del = delete_comment(pp["vic"], vic_c)
            wes_del = delete_comment(qin, wes_c)
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (zpost,))
            cora_del = pp["cora"].pg.evaluate(LIBRARY_DELETE, dsid)
            go(pg, "/social/activity")
            left = {r["href"].split("#c-")[-1] for s in pg.evaluate(ROWS) for r in s["rows"]}
            check("before anything is hidden every one of them is a row (the instrument sees them), and yourself never is:"
                  " neither your own comment nor your answer to it",
                  {ray_c, yuri_c, sal_c, tia_c, uma_c, vic_c, wes_c, abe_c, eve_c, gil_c} <= all_there
                  and own not in all_there and own_ans not in all_there and own not in left and own_ans not in left,
                  f"rows before {len(all_there)}; missing {sorted({ray_c, yuri_c, sal_c, tia_c, uma_c, vic_c, wes_c, abe_c, eve_c, gil_c} - all_there)}")
            check("a block either way hides its row: neither the person you blocked nor one who blocked you, nor an answer"
                  " under a comment by either (the page shows neither)",
                  ray_c not in left and sal_c not in left and yuri_c not in left and gil_c in left,
                  f"ray {ray_c in left}, sal {sal_c in left}, yuri under ray {yuri_c in left}, gil {gil_c in left}")
            check("taken down hides it: a person taken down, and a comment taken down",
                  tia_c not in left and uma_c not in left, f"tia {tia_c in left}, uma's comment {uma_c in left}")
            check("deleted is gone: a comment its author deleted, and one you removed from your post",
                  vic_del == 200 and wes_del == 200 and vic_c not in left and wes_c not in left,
                  f"deleted {vic_del}/{wes_del}; vic {vic_c in left}, wes {wes_c in left}")
            check("an answer to you on a post since taken down, or on a drawing deleted in the Library, goes with its page",
                  cora_del in (200, 204) and abe_c not in left and eve_c not in left,
                  f"Library delete {cora_del}; abe {abe_c in left}, eve {eve_c in left}")
            # THE DOT AGREES: with only what is hidden new, no dot; with one that
            # is shown, a dot; with only an answer on a drawing gone, none. As if
            # never looked, everything is new.
            db_write("update social_people set activity_seen_at = null where handle_key = 'qin'")
            go(pg, "/social/")
            with_gil = pg.evaluate(BELL, ".top-bell")
            delete_comment(pp["gil"], gil_c)
            db_write("update social_people set activity_seen_at = null where handle_key = 'qin'")
            go(pg, "/social/")
            hidden_only = pg.evaluate(BELL, ".top-bell")
            close_ctx(ctx, pg)
            check("the dot agrees: something shown is new, a dot; with only what is hidden, taken down, deleted or gone new,"
                  " no dot (an answer on a drawing whose page is gone among them)",
                  with_gil and with_gil["dot"] is not None and hidden_only and hidden_only["dot"] is None,
                  f"with Gil's {with_gil and with_gil['dot']}; hidden only {hidden_only and hidden_only['dot']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "the link lands: in view, it glows and the tint fades; Load more and a glide; Reduce Motion still"):
        try:
            ike = someone(b, "ike", "Ike Moon")
            jem = someone(b, "jem", "Jem Fox")
            kit = someone(b, "kit", "Kit Vale")
            post = make_post(ike, "Section 7, a lantern", seed=71)
            # Older comments under it, so the page could move either way: a landing
            # that moves the page is then seen moving.
            for i in range(5):
                comment(kit, ("p", post), f"Section 7, an older one {i}")
            target = comment(jem, ("p", post), "Section 7, look at the light on the water")
            comment(ike, ("p", post), "Thank you, Jem!", answer_to=target)
            ctx, pg = browser_as(b, ike, init=FRAMES)
            go(pg, "/social/activity")
            tap_row(pg, "look at the light on the water")
            pg.wait_for_timeout(3600)
            frames = pg.evaluate("() => window.__frames")
            where = pg.evaluate("""(id) => { const li = document.getElementById('c-' + id);
              if (!li) return { url: location.pathname + location.hash, seen: false, painted: false, li: 0, own: 0 };
              const r = li.getBoundingClientRect();
              const w = li.querySelector(':scope > .cm-main .cm-words').getBoundingClientRect(),
                    at = document.elementFromPoint(w.left + 8, w.top + w.height / 2),
                    main = li.querySelector(':scope > .cm-main').getBoundingClientRect(), bar = document.querySelector('body > .nav').getBoundingClientRect();
              return { url: location.pathname + location.hash, top: Math.round(r.top), seen: r.top >= 0 && w.bottom <= bar.top,
                       painted: !!at && li.contains(at), li: Math.round(r.height), own: Math.round(main.bottom - r.top + 2) }; }""", target)
            close_ctx(ctx, pg)
            lit = [f for f in frames if f["landed"]]
            ops = [f["op"] for f in lit]
            # While it glows (the browser's own jump to the address's comment, as
            # the page arrives, can come a frame after the comment is there).
            ys = [f["y"] for f in lit]
            check("a tap on a row opens its comment on its page (#c-<id>), in view above the bar and painted there",
                  where["url"] == f"/social/p/{post}#c-{target}" and where["seen"] and where["painted"],
                  json.dumps(where))
            check("it glows a moment in the note's tint (the comment alone, not the answer under it) and the tint fades,"
                  " read on every frame: whole at first, part-way over many frames, gone; nothing moves meanwhile",
                  lit and lit[0]["bg"] == TINT["light"] and ops[0] >= 0.97 and faded(ops) >= 8
                  and max(abs(a - b) for a, b in zip(ops, ops[1:])) <= 0.25 and not frames[-1]["landed"]
                  and abs(lit[0]["h"] - where["own"]) <= 2 and where["li"] - where["own"] >= 30
                  and glide_of(ys)["frames"] == 0,
                  f"lit {len(lit)} frames, first {lit[:1]}, part-way {faded(ops)}; tint {lit[0]['h'] if lit else None}px for"
                  f" its own {where['own']} of {where['li']}; moved on {glide_of(ys)['frames']} frames")
            # A COMMENT ON A LATER PAGE: twenty-one newer ones push it past the first.
            for i in range(21):
                comment(kit if i % 2 else jem, ("p", post), f"Section 7, a newer one {i}")
            ctx, pg = browser_as(b, ike, init=FRAMES)
            pg.goto(BASE + f"/social/p/{post}#c-{target}")
            ready(pg)
            pg.wait_for_timeout(4200)
            frames = pg.evaluate("() => window.__frames")
            far = pg.evaluate("""(id) => { const li = document.getElementById('c-' + id); if (!li) return null; const r = li.getBoundingClientRect();
              return { mid: Math.round(r.top + Math.min(r.height, innerHeight) / 2), h: innerHeight,
                       count: document.querySelectorAll('[data-cm-list] > .cm').length }; }""", target)
            close_ctx(ctx, pg)
            ys = [f["y"] for f in frames]
            g = glide_of(ys)
            check("a comment on a later page of comments is brought in with Load more, and the page glides to it (several"
                  " frames, none carrying three quarters of the way), then it glows",
                  far and far["count"] > 20 and 0 < far["mid"] < far["h"] and g["way"] > 200 and g["frames"] >= 3
                  and g["step"] <= 0.75 * g["way"] and any(f["landed"] for f in frames),
                  f"{far}; glide {g}; landed {any(f['landed'] for f in frames)}")
            # ...and on a drawing's own page, the same.
            sid = make_drawing(ike, "Section 7, a drawing", seed=72)
            on_s = comment(kit, ("s", sid), "Section 7, on the drawing")
            ctx, pg = browser_as(b, ike, init=FRAMES)
            go(pg, "/social/activity")
            tap_row(pg, "Section 7, on the drawing")
            pg.wait_for_timeout(1500)
            frames = pg.evaluate("() => window.__frames")
            url = pg.evaluate("() => location.pathname + location.hash")
            close_ctx(ctx, pg)
            check("a comment on a drawing shown outside a post opens on the drawing's own page, and glows there too",
                  url == f"/social/b/{sid}#c-{on_s}" and any(f["landed"] and f["op"] >= 0.97 for f in frames),
                  f"{url}; landed {[f.get('op') for f in frames if f['landed']][:3]}")
            # UNDER REDUCE MOTION: put there, and the tint fades where it sits.
            ctx, pg = browser_as(b, ike, reduced=True, init=FRAMES)
            pg.goto(BASE + f"/social/p/{post}#c-{target}")
            ready(pg)
            pg.wait_for_timeout(4200)
            frames = pg.evaluate("() => window.__frames")
            close_ctx(ctx, pg)
            ys = [f["y"] for f in frames]
            g = glide_of(ys)
            ops = [f["op"] for f in frames if f["landed"]]
            check("under Reduce Motion it is put there at once (no glide) and the tint fades where it sits (still a fade:"
                  " part-way over frames), nothing else moving",
                  g["way"] > 200 and g["frames"] <= 1 and ops and faded(ops) >= 8,
                  f"moved {g}; tint frames {len(ops)}, part-way {faded(ops)}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "the draw-once: a drawing answer opened from Activity draws itself; the post's own waits"):
        try:
            max_ = someone(b, "max", "Max Bell")
            nia = someone(b, "nia", "Nia Cole")
            rex = someone(b, "rex", "Rex Hill")
            post = make_post(max_, "Section 8, a tree", seed=81)
            mine = comment(max_, ("p", post), "Section 8, Max asks for a drawing")
            drawn = comment(nia, ("p", post), "Here you go", answer_to=mine, payload=drawing(n=60, seed=82))
            words = comment(rex, ("p", post), "Section 8, words alone")
            own_sk, drawn_sk = skribl_of(post), skribl_of_comment(drawn)

            def watch(pg, ms=4500):
                end, seen = time.time() + ms / 1000, []
                while time.time() < end:
                    seen.append({s["id"]: s for s in pg.evaluate(STATES)})
                    pg.wait_for_timeout(250)
                return seen

            ctx, pg = browser_as(b, max_, init=PLAYS)
            go(pg, "/social/activity")
            tap_row(pg, "Here you go")
            ready(pg)
            at_drawing = watch(pg)
            asked = pg.evaluate("() => window.__plays")
            sound = pg.evaluate("() => window.SkriblInline ? SkriblInline.soundOn() : null")
            close_ctx(ctx, pg)
            played = lambda seen, sk: any(s.get(sk, {}).get("state") == "playing" or s.get(sk, {}).get("ms", 0) > 0 for s in seen)  # noqa: E731
            check("a drawing answer opened from Activity draws itself once when you land, sound off, and the post's own"
                  " drawing waits (one plays at a time: it is never asked to)",
                  played(at_drawing, drawn_sk) and asked == [drawn_sk] and not played(at_drawing, own_sk)
                  and sound is False and all(s.get(drawn_sk, {}).get("muted", True) for s in at_drawing),
                  f"asked {asked}; answer {[s.get(drawn_sk, {}).get('state') for s in at_drawing][:8]}; post's"
                  f" {[s.get(own_sk, {}).get('state') for s in at_drawing][:4]}; sound {sound}")
            ctx, pg = browser_as(b, max_, init=PLAYS)
            go(pg, "/social/activity")
            tap_row(pg, "Section 8, words alone")
            ready(pg)
            at_words = watch(pg)
            asked = pg.evaluate("() => window.__plays")
            close_ctx(ctx, pg)
            check("opened at a comment of words, the post's own drawing plays as on any visit, and no comment's does",
                  played(at_words, own_sk) and asked == [own_sk] and not played(at_words, drawn_sk),
                  f"asked {asked}; post's {[s.get(own_sk, {}).get('state') for s in at_words][:6]}; answer's"
                  f" {[s.get(drawn_sk, {}).get('state') for s in at_words][:4]}")
            ctx, pg = browser_as(b, max_, reduced=True, init=PLAYS)
            pg.goto(BASE + f"/social/p/{post}#c-{drawn}")
            ready(pg)
            calm = watch(pg, 3000)
            asked = pg.evaluate("() => window.__plays")
            close_ctx(ctx, pg)
            check("under Reduce Motion nothing plays: neither the drawing answer nor the post's own is asked to",
                  calm and asked == [] and not played(calm, drawn_sk) and not played(calm, own_sk),
                  f"asked {asked}; {[{k: v['state'] for k, v in s.items()} for s in calm[-1:]]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "the empty state: Blooby's icon, Nothing new yet, and Make a skribl"):
        try:
            sky = someone(b, "sky", "Sky Rowe")
            got = {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, sky, screen=screen)
                go(pg, "/social/activity")
                got[screen] = pg.evaluate("""() => { const s = document.querySelector('.act-empty'); if (!s) return null;
                  const i = s.querySelector('img.si-icon'), ir = i ? i.getBoundingClientRect() : { left: 0, top: 0, width: 0, height: 0 },
                        b = s.querySelector('.btn'), br = b.getBoundingClientRect(),
                        at = i ? document.elementFromPoint(ir.left + ir.width / 2, ir.top + ir.height / 2) : null;
                  return { icon: i ? new URL(i.src).pathname.split('/').pop() : null, w: ir.width, h: ir.height, painted: !!i && at === i,
                           title: s.querySelector('.act-empty-title').textContent, words: s.querySelector('.act-empty-words').textContent,
                           button: b.textContent.trim(), bh: br.height, lists: document.querySelectorAll('.act-list, .act-sec').length }; }""")
                if screen == "phone":
                    pg.tap(".act-empty .btn")
                else:
                    pg.click(".act-empty .btn")
                pg.wait_for_timeout(600)
                got[screen]["sheet"] = pg.evaluate("() => { const m = document.getElementById('makeSheet');"
                                                   " return !!m && !m.hidden && m.classList.contains('is-open')"
                                                   " && [...m.querySelectorAll('.make-door b')].map(x => x.textContent); }")
                close_ctx(ctx, pg)
            want = {"icon": "apple-touch-icon.png", "title": "Nothing new yet",
                    # likes (the likes mock) and follows (the follow mock): both are in Activity too
                    "words": "When someone follows you, likes your post, says something on it, or answers you, you’ll see it here.",
                    "button": "Make a skribl"}
            check("with nothing yet: Blooby as his Home Screen icon (64px, painted), \"Nothing new yet\", the words, and"
                  " Make a skribl (52px); no New, no Earlier; phone and desk",
                  all(got[s] and all(got[s][k] == v for k, v in want.items()) and got[s]["w"] == 64 and got[s]["h"] == 64
                      and got[s]["painted"] and got[s]["bh"] >= 52 and got[s]["lists"] == 0 for s in ("phone", "desk")),
                  json.dumps({s: {k: v for k, v in (got[s] or {}).items() if k != 'sheet'} for s in got}))
            check("Make a skribl opens Make's own sheet, Draw and Flip in it (a tap on a phone, a click on a desk)",
                  all(got[s]["sheet"] == ["Draw", "Flip"] for s in ("phone", "desk")),
                  f"{got['phone']['sheet']} / {got['desk']['sheet']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "words and targets: Activity, the bell and a landed comment; phone and desk, light and dark"):
        try:
            tom = someone(b, "tom", "Tom Ash")
            jem = someone(b, "jem", "Jem Fox")
            kit = someone(b, "kit", "Kit Vale")
            sky = someone(b, "sky", "Sky Rowe")
            post = make_post(tom, "Section 10, a bridge", seed=101)
            old = comment(kit, ("p", post), "Section 10, an earlier one about the bridge's long shadow at noon")
            db_write("update social_people set activity_seen_at = datetime('now', '+1 second') where handle_key = 'tom'")
            time.sleep(1.2)
            mine = comment(tom, ("p", post), "Section 10, Tom asks")
            comment(jem, ("p", post), "Section 10, the bridge!")
            comment(kit, ("p", post), "Section 10, and the river under it")
            comment(jem, ("p", post), "A drawing back", answer_to=mine, payload=drawing(seed=102))
            land = comment(kit, ("p", post), "Section 10, I answer you", answer_to=mine)
            seen, rows, dots, tints = {}, {}, {}, {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    db_write("update social_people set activity_seen_at = (select created_at from social_comments"
                             " where public_id = ?) where handle_key = 'tom'", (old,))
                    ctx, pg = browser_as(b, tom, screen=screen, scheme=scheme)
                    go(pg, "/social/")
                    seen[(screen, scheme, "home")] = pg.evaluate(READ, "header.top, nav.nav")
                    dots[(screen, scheme, "bell")] = pg.evaluate(BELL, ".top-bell" if screen == "phone" else "nav.nav .tab-activity")
                    go(pg, "/social/activity")
                    seen[(screen, scheme, "activity")] = pg.evaluate(READ, "main, header.top, nav.nav")
                    secs = pg.evaluate(ROWS)
                    rows[(screen, scheme)] = [(r["h"], r["isNew"], r["mark"]) for s in secs for r in s["rows"]]
                    dots[(screen, scheme, "row")] = pg.evaluate(r"""() => { const m = document.querySelector('.act-row.is-new .act-mark');
                      if (!m) return null; const rgba = s => { const v = (s.match(/[\d.]+/g) || []).map(Number); return v.length > 3 ? v : v.concat([1]); };
                      const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
                      const g = rgba(getComputedStyle(document.body).backgroundColor), c = rgba(getComputedStyle(m).backgroundColor),
                            a = [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
                      const p = lum(a), q = lum(g); return Math.round((Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05) * 100) / 100; }""")
                    pg.goto(BASE + f"/social/p/{post}#c-{land}")
                    ready(pg)
                    pg.wait_for_timeout(250)
                    tints[(screen, scheme)] = pg.evaluate(ON_TINT, land)
                    close_ctx(ctx, pg)
                    ectx, epg = browser_as(b, sky, screen=screen, scheme=scheme)
                    go(epg, "/social/activity")
                    seen[(screen, scheme, "empty")] = epg.evaluate(READ, "main, header.top, nav.nav")
                    close_ctx(ectx, epg)
            low = [(" ".join(k), v["low"]) for k, v in seen.items() if v["low"]]
            small = [(" ".join(k), v["small"]) for k, v in seen.items() if v["small"]]
            fields = [(" ".join(k), v["fields"]) for k, v in seen.items() if v["fields"]]
            lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
            # What the census must have read (it keeps a word as its element's
            # first 24 characters): each row's say, the sections, the empty page's.
            musts = {"activity": ("New", "Earlier", "Kit and Jem said something on your post", "Kit answered your comment",
                                  "Jem answered with a drawing", "Kit said something on your post"),
                     "empty": ("Nothing new yet", "Make a skribl")}
            missing = [(" ".join(k), w) for k, v in seen.items() for w in musts.get(k[2], ())
                       if not any(x == w or (len(w) > 22 and x[:22] == w[:22]) for x in v["words"])]
            short = {f"{k[0]} {k[1]}": [h for h, _, _ in v if h < 76] for k, v in rows.items()}
            check("every word on Activity (a list with New and Earlier, and the empty page) and on the chrome with the bell"
                  " reads at 4.5:1 or more on what is painted behind it, every target is 44px or more each way, the rows"
                  " 76px; phone (touch) and desk, light and dark",
                  not low and not small and not fields and not missing and not any(short.values())
                  and all(v["read"] >= 3 for v in seen.values()) and all(len(v) >= 4 for v in rows.values()),
                  f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small:"
                  f" {small[:3]}; fields {fields[:2]}; not read {missing[:3]}; rows under 76px {short}")
            ks = {" ".join(k): (v["dot"]["k"] if v and v.get("dot") else None) if k[2] == "bell" else v for k, v in dots.items()}
            lines = {" ".join(k): v["line"] for k, v in dots.items() if k[2] == "bell" and v}
            check("the dot (the bell's and each new row's) and the bell's line read 3:1 or more on their ground, light"
                  " and dark",
                  all(v is not None and v >= 3 for v in ks.values()) and len(lines) == 4
                  and all(v >= 3 for v in lines.values()),
                  f"dots {ks}; lines {lines}")
            check("a landed comment's words, name, time and Answer read 4.5:1 or more on the tint, phone and desk, light"
                  " and dark",
                  all(v and v.get("landed") and all(v[k] is not None and v[k] >= 4.5 for k in ("words", "name", "when", "answer"))
                      for v in tints.values()),
                  json.dumps({" ".join(k): v for k, v in tints.items()}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "the data: the chain on a populated database; the bell's reads on their indexes; deleting in code"):
        try:
            mdb = os.path.join(TMP, "chain-activity.db")
            # The chain's head before Activity (its migration's down_revision).
            BEFORE = "ded60afbc86d"

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
            then = "2026-11-12 10:00:00"
            for i, h in ((1, "ann"), (2, "bob"), (3, "cy")):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle,"
                            " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                            (i, "site:" + h, h, h, h.title(), bytes([i]) * 32, then, then))
            con.execute("insert into social_posts (id, public_id, person_id, words, skribl_id, created_at)"
                        " values (10, 'P1', 1, 'hi', 'S1', ?)", (then,))
            for row in ((100, "C1", 2, None), (101, "C2", 1, 100), (102, "C3", 3, 100)):
                con.execute("insert into social_comments (id, public_id, post_id, owner_id, person_id, parent_id, words,"
                            " created_at) values (?, ?, 10, 1, ?, ?, 'x', ?)", row + (then,))
            con.commit()
            con.close()
            up2 = chain("upgrade", "head")
            filled = at("select public_id, to_person_id from social_comments order by id")
            idx = {r[0] for r in at("select name from sqlite_master where type = 'index' and tbl_name = 'social_comments'")}
            cols = {r[1] for r in at("pragma table_info(social_people)")}
            check("the site's chain on a database with comments in it: every answer answers the author of the comment it"
                  " sits under, a comment nobody; the person's row keeps when they last looked (empty); the comments are"
                  " indexed by whose (owner_id, created_at) and by whom (to_person_id, created_at), the owner's own index"
                  " folded into the first",
                  up1.returncode == 0 and up2.returncode == 0 and filled == [("C1", None), ("C2", 2), ("C3", 2)]
                  and "activity_seen_at" in cols and {"ix_social_comments_owner_created", "ix_social_comments_to_created"} <= idx
                  and "ix_social_comments_owner_id" not in idx,
                  f"up {up1.returncode}/{up2.returncode} {up2.stderr.strip().splitlines()[-1:] if up2.returncode else ''};"
                  f" rows {filled}; indexes {sorted(i for i in idx if 'owner' in i or 'to_' in i)}")
            down = chain("downgrade", BEFORE)
            idx2 = {r[0] for r in at("select name from sqlite_master where type = 'index' and tbl_name = 'social_comments'")}
            ccols = {r[1] for r in at("pragma table_info(social_comments)")}
            pcols = {r[1] for r in at("pragma table_info(social_people)")}
            kept = at("select public_id from social_comments order by id")
            check("taken back down, the chain drops what it added and puts the owner's own index back, every comment kept",
                  down.returncode == 0 and "to_person_id" not in ccols and "activity_seen_at" not in pcols
                  and "ix_social_comments_owner_id" in idx2 and not ({"ix_social_comments_owner_created",
                                                                       "ix_social_comments_to_created"} & idx2)
                  and kept == [("C1",), ("C2",), ("C3",)],
                  f"down {down.returncode} {down.stderr.strip().splitlines()[-1:] if down.returncode else ''};"
                  f" indexes {sorted(i for i in idx2 if 'owner' in i or 'to_' in i)}; kept {kept}")
            # On the suite's own database: an answer keeps whom it answers, and
            # an account deleted with the cascade off leaves answers to it
            # answering nobody, by the code.
            uli = someone(b, "uli", "Uli Berg")
            vin = someone(b, "vin", "Vin Shaw")
            xan = someone(b, "xan", "Xan Roe")
            vpost = make_post(vin, "Section 11, Vin's", seed=111)
            u_top = comment(uli, ("p", vpost), "Section 11, Uli's")
            x_ans = comment(xan, ("p", vpost), "Section 11, Xan answers Uli", answer_to=u_top)
            v_ans = comment(vin, ("p", vpost), "Section 11, Vin answers Xan's answer", answer_to=x_ans)
            whom = dict(db("select c.public_id, t.handle from social_comments c left join social_people t"
                           " on t.id = c.to_person_id where c.public_id in (?, ?, ?)", (u_top, x_ans, v_ans)))
            check("an answer keeps whom it answers, an answer to an answer too (the comment it sits under is somebody"
                  " else's), and a comment answers nobody",
                  whom == {u_top: None, x_ans: "uli", v_ans: "xan"}, json.dumps(whom))
            copy = os.path.join(TMP, "probe.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            probe = subprocess.run([sys.executable, "-c", PROBE, "xan"], cwd=ROOT, capture_output=True, text=True,
                                   timeout=180, env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-400:]}
            plans = out.get("plans") or [[], []]
            check("the bell's two reads, as the code builds them, are each one search on its own index, newest first since"
                  " they last looked (SQLite's own plan): (owner_id, created_at) and (to_person_id, created_at)",
                  any("ix_social_comments_owner_created (owner_id=? AND created_at>?)" in s for s in plans[0])
                  and any("ix_social_comments_to_created (to_person_id=? AND created_at>?)" in s for s in plans[1])
                  and not any(s.startswith("SCAN") or "TEMP B-TREE" in s for s in plans[0] + plans[1]),
                  json.dumps(plans))
            check("deleting an account, with SQLite's cascade off (SKRIBL_SQLITE_FOREIGN_KEYS=0, on a copy), leaves the"
                  " answers to it by people who stay, answering nobody: in code, not by the cascade",
                  out.get("fk") == 0 and out.get("answers", 0) >= 1 and out.get("left")
                  and all(t is None for _, t in out["left"]) and len(out["left"]) == out["answers"],
                  json.dumps({k: v for k, v in out.items() if k != "plans"}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

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
