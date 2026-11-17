#!/usr/bin/env python3
"""THE COMMENT THREAD, MOCKED: two levels of replies, then "Read N more
replies", which opens that reply's own page. The owner's yes, Nov 17 (the
mock: https://claude.ai/artifact/XbQmHKjA2swkoMkCwfdUjo; docs/SOCIAL-SITE.md
section 18 is the plan, DECISIONS.md the entry). Not a suite: a tool that
shoots the site's own post page with the mock's look laid over it, so the
next round (drawn replies in a thread, say) can be shot the same way.

What it does. Starts the site on a fresh database (the fixture below is
verify_socialreposts.py's: a server of its own, people signed in with
Chromium's virtual authenticator), posts Ben's drawing and a thread on it:
Eli asks; Ana and Ben answer; Eli answers Ana; Ana answers Eli; Cyd answers
Ana; and Dee comments on the post directly. Then, for a phone and a desk,
light and dark, it opens the post and lays the mock over today's page (CSS
and a little DOM; nothing in the app changes):

  thread   the bubbles (the site's card, its lilac edge and lift), an
           initial in a face not drawn yet, the count pill, the thread's
           lilac line, the post's row on every comment (Reply, Repost, Like,
           ...; "Reply" spelled out on a desk only), two levels, and under
           Eli's reply "Read 2 more replies" on the line
  reply    that reply's own page: the way to it small above (the post, the
           comment, the reply it answers), the reply as the post, its row and
           time, then its replies, two levels again
  sheet    a comment's ⋯ on a phone, "This comment": Bookmark, Copy link,
           Share..., then Report this comment (the post's own sheet, relabelled)

Run from the repository's root, with the venv's python:

    MOCK_OUT=/tmp/comments /tmp/skribl-venv/bin/python3 harness/tools/mock_comments.py

It writes MOCK_OUT/shots/rm-<phone|desk>-<light|dark>-<thread|reply>.png and
rm-phone-<light|dark>-sheet.png at 2x, and MOCK_OUT/measure.json (the room
the words have at each depth, the icons' contrast, and an @name's when a
comment has one). The times and hearts are set for the picture. About four
minutes. To mock the next thing (a drawn reply in the thread, say), post it
in the fixture with make_drawing() and lay its look over the page in SETUP.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # harness/, for assertions
from assertions import make_check
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
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
TMP = tempfile.mkdtemp(prefix="mockcomments-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="mock-comments-" + secrets.token_hex(8),
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
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=2)
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


# ================= THE COMMENTS MOCK: now, A (open, thread lines), B (bubbles) =================
import json as _json
OUT = os.environ["MOCK_OUT"]
os.makedirs(f"{OUT}/shots", exist_ok=True)

BASE_CSS = """
.cm { box-shadow: none !important; padding-top: 12px; }
.cm-answers .cm { padding-top: 10px; }
.cm-acts .icon-btn { margin-left: 0 !important; margin-right: 0 !important; }
.cm:has(> .cm-answers) > .cm-main { position: relative; }
.cm:has(> .cm-answers) > .cm-main::before { content: ""; position: absolute; left: -31px; top: 40px; bottom: 0; border-left: 2px solid var(--card-edge); }
.cm-answers > .cm { position: relative; }
.cm-answers > .cm::before { content: ""; position: absolute; left: -31px; top: 0; height: 28px; width: 23px;
  border-left: 2px solid var(--card-edge); border-bottom: 2px solid var(--card-edge); border-bottom-left-radius: 12px; }
.cm-answers > .cm:not(:last-child)::after { content: ""; position: absolute; left: -31px; top: 0; bottom: 0; border-left: 2px solid var(--card-edge); }
.face-ring.is-blank { background: var(--tint) !important; }
.face-ring.is-blank .face-blank { display: grid !important; place-items: center; width: 100%; height: 100%; color: var(--accent-ink); font-weight: 700; font-size: 16px; line-height: 1; }
.face-ring.is-blank .face-blank::before { content: attr(data-initial); }
.comments-title .cm-count { background: var(--tint); color: var(--accent-ink); font-size: 14px; font-weight: 700; padding: 2px 9px; border-radius: 999px; margin-left: 4px; line-height: 1.3; }
"""
BUBBLE_CSS = """
.cm-bubble { background: var(--card); box-shadow: 0 0 0 var(--edge, 1px) var(--card-edge), var(--card-drop); border-radius: 18px; padding: 7px 14px 9px; width: fit-content; max-width: 100%; box-sizing: border-box; }
.cm-bubble .cm-head { min-height: 0; }
.cm-bubble .cm-words { margin-top: 1px; }
.cm-acts { gap: 0; margin-left: -10px; }
.cm-acts > button { min-width: 44px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; padding: 0 10px; color: var(--ink-2); background: none; border: 0; font: inherit; font-size: 15px; font-weight: 600; }
.cm-acts .ic, .cm-acts svg { width: 18px; height: 18px; }
.cm-acts .n { font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
.cm-acts .is-liked { color: #e0245e; }
@media (max-width: 640px) { .cm-acts .cm-word { display: none; } }
"""
MORE_CSS = """
.cm-readmore { display: block !important; padding: 2px 0 6px !important; }
.cm-answers > .cm.cm-readmore::before { height: 22px; }
.rm-link { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: var(--ink-2); font-size: 15px; font-weight: 600; text-decoration: none; }
.rm-link .ic { width: 18px; height: 18px; }
.reply-ctx { margin: 4px 0 6px; }
.ctx-item { display: grid; grid-template-columns: 36px minmax(0, 1fr); column-gap: 12px; position: relative; padding-bottom: 14px; }
.ctx-item::before { content: ""; position: absolute; left: 17px; top: 40px; bottom: -2px; border-left: 2px solid var(--card-edge); }
.ctx-face { width: 36px; height: 36px; border-radius: 50%; display: block; }
.ctx-main p { margin: 2px 0 0; font-size: 15px; line-height: 1.4; color: var(--ink); }
.ctx-head { display: flex; gap: 6px; align-items: baseline; }
.ctx-head b { font-size: 15px; color: var(--ink); }
.ctx-head span { font-size: 14px; color: var(--ink-2); }
.ctx-item.is-post p { color: var(--ink-2); }
.ctx-item:last-child::before { bottom: -10px; }
.post-face, .post-face * { text-decoration: none !important; }
.post-face .face-ring.is-blank { width: 48px; height: 48px; }
.post-face .face-blank { font-size: 19px !important; }
"""

SETUP = r"""(opt) => {
  const times = {0: '25m', 1: '5h', 2: '4h', 3: '3h', 4: '2h', 5: '1h', 6: '40m'};
  const cms = [...document.querySelectorAll('.cm')];
  cms.forEach((c, i) => { const t = c.querySelector(':scope > .cm-main .cm-when'); if (t) { t.textContent = times[i] || '1h'; t.removeAttribute('data-when'); } });
  cms.forEach(c => { const f = c.querySelector(':scope > .face-ring.is-blank .face-blank'); if (f) f.setAttribute('data-initial', (c.dataset.first || '?')[0]); });
  const s = document.createElement('style'); s.id = 'mock-cm'; s.textContent = @@BASE@@ + @@BUB@@ + @@MORE@@; document.head.appendChild(s);
  const icon = (sel) => { const e = document.querySelector('.post-row ' + sel + ' svg'); return e ? e.outerHTML : ''; };
  const IC = { reply: icon('.post-count'), repost: icon('.rp-btn'), heart: icon('.lk-heart'), dots: icon('.post-more') };
  const counts = [[0, 12, 1], [0, 3, 0], [0, 1, 0], [0, 2, 0], [0, 4, 0], [0, 0, 0], [0, 6, 0]];
  cms.forEach((c, i) => {
    const acts = c.querySelector(':scope > .cm-main .cm-acts'); if (!acts) return;
    const [rp, lk, mine] = counts[i] || [0, 0, 0];
    acts.innerHTML = '<button type="button" aria-label="Reply">' + IC.reply + '<span class="cm-word">Reply</span></button>'
      + '<button type="button" aria-label="Repost">' + IC.repost + (rp ? '<span class="n">' + rp + '</span>' : '') + '</button>'
      + '<button type="button" aria-label="Like"' + (mine ? ' class="is-liked"' : '') + '>' + IC.heart + (lk ? '<span class="n">' + lk + '</span>' : '') + '</button>'
      + '<button type="button" aria-label="More">' + IC.dots + '</button>';
  });
  document.querySelectorAll('.cm-main').forEach(m => {
    const b = document.createElement('div'); b.className = 'cm-bubble';
    const parts = [...m.children].filter(x => x.matches('.cm-head, .cm-words, .cm-down, .cm-art'));
    if (!parts.length) return; m.insertBefore(b, parts[0]); parts.forEach(p => b.appendChild(p));
  });
  const top = cms.find(c => c.querySelectorAll(':scope > .cm-answers > .cm').length === 5);
  if (!top) return 'no thread';
  const [r1, r2, r3, r4, r5] = [...top.querySelectorAll(':scope > .cm-answers > .cm')];
  const nest = (parent, child) => { let ol = parent.querySelector(':scope > .cm-answers'); if (!ol) { ol = document.createElement('ol'); ol.className = 'cm-answers'; parent.appendChild(ol); } ol.appendChild(child); return ol; };
  const PLUS = '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>';
  if (opt === 'thread') {
    nest(r1, r3);
    r4.remove(); r5.remove();
    const li = document.createElement('li'); li.className = 'cm cm-readmore';
    li.innerHTML = '<a class="rm-link" href="#">' + PLUS + '<span>Read 2 more replies</span></a>';
    nest(r3, li);
    return 'ok';
  }
  // THE REPLY'S OWN PAGE: Eli's reply to Ana, as the post; the way to it above; its replies below.
  const title = document.querySelector('.top-title'); if (title) title.textContent = 'Reply';
  const art = document.querySelector('.post-page');
  art.querySelectorAll(':scope > .post-art, :scope > .liked-by, :scope > .more-from, :scope > .post-caption').forEach(e => e.hidden = true);
  const disc = (n) => '<span class="face-ring is-blank ctx-face"><span class="face-blank" data-initial="' + n + '"></span></span>';
  const item = (n, name, when, words, kind) => '<div class="ctx-item' + (kind ? ' ' + kind : '') + '">' + disc(n) + '<div class="ctx-main"><div class="ctx-head"><b>' + name + '</b><span>' + when + '</span></div><p>' + words + '</p></div></div>';
  const ctx = document.createElement('div'); ctx.className = 'reply-ctx';
  ctx.innerHTML = item('B', 'Ben Okafor', '6h', 'Morning bike ride, drawn on the train', 'is-post')
    + item('E', 'Eli Moss', '5h', 'Is this the ride along the river? I think I know that bridge.')
    + item('A', 'Ana Reyes', '4h', 'It is! I ride it on Sundays.');
  art.insertBefore(ctx, art.firstElementChild);
  const head = art.querySelector('.post-head');
  head.querySelector('.post-face').innerHTML = disc('E');
  head.querySelector('.post-name').textContent = 'Eli Moss';
  head.querySelector('.post-sub').textContent = '@eli';
  const w = art.querySelector(':scope > .post-words'); if (w) w.textContent = "Sundays? I'll look out for you.";
  const meta = art.querySelector(':scope > .post-meta'); if (meta) meta.textContent = 'Today at 5:31 AM';
  const pc = art.querySelector('.post-row .post-count'); if (pc) pc.innerHTML = IC.reply + '<span>2</span>';
  const hn = art.querySelector('.post-row .lk-heart'); if (hn) { hn.classList.remove('is-zero'); hn.innerHTML = IC.heart + '<span class="lk-n">4</span>'; }
  const ct = document.querySelector('.comments-title'); if (ct) { const n = ct.querySelector('.cm-count'); ct.childNodes.forEach(x => { if (x.nodeType === 3 && x.textContent.trim()) x.textContent = ' Replies '; }); const sp = [...ct.querySelectorAll('span')].find(x => x.textContent.trim() === 'Comments'); if (sp) sp.textContent = 'Replies'; if (n) n.textContent = '2'; }
  const list = top.parentElement;
  list.insertBefore(r4, list.firstElementChild);
  [...list.children].forEach(c => { if (c !== r4) c.remove(); });
  nest(r4, r5);
  return 'ok';
}""".replace("@@BASE@@", _json.dumps(BASE_CSS)).replace("@@BUB@@", _json.dumps(BUBBLE_CSS)).replace("@@MORE@@", _json.dumps(MORE_CSS))

MEASURE = r"""() => {
  const lum = (c) => { const v = c.slice(0, 3).map(x => x / 255).map(x => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const rgb = (s) => { const m = s.match(/color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)/); if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255]; return (s.match(/[\d.]+/g) || []).map(Number).slice(0, 3); };
  const ratio = (a, b) => { const x = lum(rgb(a)), y = lum(rgb(b)); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const page = getComputedStyle(document.body).backgroundColor;
  const bubbles = [...document.querySelectorAll('.cm-bubble')].map(b => { let d = 0, e = b.closest('.cm'); while (e && e.parentElement.closest('.cm')) { d++; e = e.parentElement.closest('.cm'); }
    const w = b.querySelector('.cm-words'), cs = w ? getComputedStyle(w) : null;
    const chars = w ? Math.floor(w.getBoundingClientRect().width / (parseFloat(cs.fontSize) * 0.5)) : null;
    return { depth: d, room: Math.round(b.parentElement.getBoundingClientRect().width), chars }; });
  const byDepth = {}; bubbles.forEach(x => { byDepth[x.depth] = byDepth[x.depth] || x; });
  const m = document.querySelector('.cm-words a'), bub = document.querySelector('.cm-bubble');
  const icon = document.querySelector('.cm-acts > button');
  return { byDepth, mention: m ? ratio(getComputedStyle(m).color, getComputedStyle(bub).backgroundColor) : null,
           icons: icon ? ratio(getComputedStyle(icon).color, page) : null }; }"""

SHEET = r"""() => {
  const btn = document.querySelector('.post-row .post-more'); if (!btn) return 'no menu'; btn.click();
  const sh = document.getElementById('postSheet'); if (!sh) return 'no sheet';
  const t = sh.querySelector('#postSheetTitle'); if (t) t.textContent = 'This comment';
  sh.querySelectorAll('.post-act').forEach(a => { const w = a.querySelector('span'); if (!w) return;
    if (a.dataset.act === 'report') w.textContent = 'Report this comment';
    if (a.dataset.act === 'delete') w.textContent = 'Delete comment';
    if (a.dataset.act === 'block' || a.classList.contains('mu-act')) a.hidden = true; });
  return 'ok'; }"""


def say_(who, post, words, answer_to=None):
    c = who.client(); c.get(f"/social/p/{post}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    st, j = c.post_json(f"/social/p/{post}/comments", body)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def section_box(pg):
    return pg.evaluate("""() => { const s = document.querySelector('.cm').closest('section') || document.querySelector('.cm-list').parentElement;
        const r = s.getBoundingClientRect(); return { x: Math.max(0, r.left - 10), y: Math.max(0, r.top - 10),
          width: Math.min(innerWidth - Math.max(0, r.left - 10), r.width + 20), height: r.height + 20 }; }""")


meas = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ben = member(b, "ben", "Ben Okafor")
    ana = member(b, "ana", "Ana Reyes")
    cyd = member(b, "cyd", "Cyd Marsh")
    dee = member(b, "dee", "Dee Park")
    eli = member(b, "eli", "Eli Moss")
    post = make_post(ben, "Morning bike ride, drawn on the train", seed=3)
    c1 = say_(eli, post, "Is this the ride along the river? I think I know that bridge.")
    r1 = say_(ana, post, "It is! I ride it on Sundays.", answer_to=c1)
    r2 = say_(ben, post, "Yes, the one by the old mill. Good eye.", answer_to=c1)
    r3 = say_(eli, post, "Sundays? I'll look out for you.", answer_to=r1)
    r4 = say_(ana, post, "I'm the one with the red bell.", answer_to=r3)
    r5 = say_(cyd, post, "I've heard that bell! Every Sunday by the mill.", answer_to=r4)
    say_(dee, post, "This made my morning. The little bell is perfect.")
    print("fixture", post, c1, r5, flush=True)
    for screen in ("phone", "desk"):
        for scheme in ("light", "dark"):
            for opt in ("thread", "reply"):
                ctx, pg = browser_as(b, ana, screen=screen, scheme=scheme)
                go(pg, f"/social/p/{post}", wait=900)
                st = pg.evaluate(SETUP, opt)
                pg.wait_for_timeout(400)
                if opt == "reply":
                    pg.evaluate("() => window.scrollTo(0, 0)")
                    pg.wait_for_timeout(250)
                    box = pg.evaluate("""() => { const a = document.querySelector('.post-page'), r = a.getBoundingClientRect(), t = document.querySelector('.top, header.top, .site-top');
                        const top = t ? Math.max(0, t.getBoundingClientRect().top) : 0;
                        let bottom = r.top; a.querySelectorAll(':scope > *:not([hidden])').forEach(e => { const b = e.getBoundingClientRect(); if (b.height) bottom = Math.max(bottom, b.bottom); });
                        return { x: Math.max(0, r.left - 10), y: top, width: Math.min(innerWidth - Math.max(0, r.left - 10), r.width + 20), height: bottom - top + 16 }; }""")
                else:
                    pg.evaluate("() => { const s = document.querySelector('.cm').closest('section') || document.querySelector('.cm-list').parentElement; s.scrollIntoView({ block: 'start' }); }")
                    pg.wait_for_timeout(250)
                    box = section_box(pg)
                vp = pg.viewport_size
                need = int(box["y"] + box["height"] + 30)
                if need > vp["height"]:
                    pg.set_viewport_size({"width": vp["width"], "height": need}); pg.wait_for_timeout(300)
                    if opt != "reply":
                        box = section_box(pg)
                pg.screenshot(path=f"{OUT}/shots/rm-{screen}-{scheme}-{opt}.png", clip=box)
                meas[f"{screen} {scheme} {opt}"] = dict(pg.evaluate(MEASURE), setup=st)
                close_ctx(ctx, pg)
            if screen == "phone":
                ctx, pg = browser_as(b, ana, screen=screen, scheme=scheme)
                go(pg, f"/social/p/{post}", wait=900)
                pg.evaluate(SETUP, "thread")
                st = pg.evaluate(SHEET)
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{OUT}/shots/rm-{screen}-{scheme}-sheet.png")
                meas[f"{screen} {scheme} sheet"] = st
                close_ctx(ctx, pg)
            print(screen, scheme, "done", flush=True)
    b.close()
open(f"{OUT}/measure.json", "w").write(_json.dumps(meas, indent=1))
print("ok")
