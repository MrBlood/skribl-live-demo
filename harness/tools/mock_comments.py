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

MOCK_ROUND=drawings shoots the next round instead (Drawings in the Thread,
Nov 17: https://claude.ai/artifact/BsQKU7AnAeDfAxxGNXCJyc): the same thread
with real drawings in it, from artworks.py (the owner's cat and pug, How it
works' cottage and snail), each made as the Pad records one (artdraw's hand
and pressure) and given the still picture an editor makes as it posts
(lib/faceframe.js card(), on the person's own page); today's look, A (the
drawing 150px in its bubble) and B (as wide as the bubble's room), a drawn
reply's own page with a drawing's still on the way to it, and the pictures
for two smaller questions: deleting a reply that has replies (today, all go;
or its place stays) and replying at the second level ("Read 3 more replies"
glowing). It writes MOCK_OUT/shots/dr-<phone|desk>-<light|dark>-<opt>.png and
measure.json (each drawing's size and room, its paper against what is behind
it, the words' contrasts).

MOCK_ROUND=world shoots step 3's (A Comment Shared, Nov 17:
https://claude.ai/artifact/4XKrYxE3894YErstqr88NW): a comment away from its
thread, when nothing in the app reposts, quotes or keeps one yet, so today's
own cards are made over in the page. On Dee's Home (Following), Ana's repost
of Ben's post becomes her repost of Eli's comment, and Ana's cat, posted as a
stand-in, her drawn reply reposted by Cyd; Cyd's quote of Ben's post quotes
Eli's comment; on Dee's Bookmarks, her bookmark of Ben's post keeps Eli's
comment. Today's look, then A (the way to it above, as on the comment's own
page) and B (alone, with "On Ben's post" or "Reply to Eli" under its name).
It writes MOCK_OUT/shots/w<o|q|b>-<phone|desk>-<light|dark>-<now|a|b>.png and
measure.json (the small words' contrast, the cards' heights, the way's faces
over the card's).

MOCK_ROUND=tree shoots the fold (The Folded Thread, Nov 17:
https://claude.ai/artifact/3mefzDKSCqWZ2PuSFMhTVZ), from the owner's "We
don't want the whole tree visible until someone selects the reply": the
post's page as step 1 built it, then A (each conversation folded to "Read N
replies", opening the comment's own page) and B (the same fold, opening in
place, shown open on Eli's with "Hide replies"), and the page A opens. It
writes MOCK_OUT/shots/tr-<phone|desk>-<light|dark>-<now|a|b|page>.png and
measure.json (the list's height, the links' words).

MOCK_ROUND=count shoots the count by the talk cloud (Count by the Talk
Cloud, Nov 17: https://claude.ai/artifact/5JATdGYwfEGASbpGxjBDr3), from the
owner's "You only need to show the replies not the nested 5 replies. Click
on the reply and it shows you the nested tree. First reply just has count
by the talk cloud": today's "Read N replies" on the thread's line beside A
(the line gone, the count in the comment's own row beside its talk cloud),
under a post and on a comment's own page. It writes
MOCK_OUT/shots/ct-<list|page>-<phone|desk>-<light|dark>-<now|a>.png and
measure.json (the list's height, each row's parts, the count's contrast).

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
  const times = window.__mockTimes || {0: '25m', 1: '5h', 2: '4h', 3: '3h', 4: '2h', 5: '1h', 6: '40m'};
  const cms = [...document.querySelectorAll('.cm')];
  cms.forEach((c, i) => { const t = c.querySelector(':scope > .cm-main .cm-when'); if (t) { t.textContent = times[i] || '1h'; t.removeAttribute('data-when'); } });
  cms.forEach(c => { const f = c.querySelector(':scope > .face-ring.is-blank .face-blank'); if (f) f.setAttribute('data-initial', (c.dataset.first || '?')[0]); });
  const s = document.createElement('style'); s.id = 'mock-cm'; s.textContent = @@BASE@@ + @@BUB@@ + @@MORE@@; document.head.appendChild(s);
  const icon = (sel) => { const e = document.querySelector('.post-row ' + sel + ' svg'); return e ? e.outerHTML : ''; };
  const IC = { reply: icon('.post-count'), repost: icon('.rp-btn'), heart: icon('.lk-heart'), dots: icon('.post-more') };
  const counts = window.__mockCounts || [[0, 12, 1], [0, 3, 0], [0, 1, 0], [0, 2, 0], [0, 4, 0], [0, 0, 0], [0, 6, 0]];
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


def say_(who, post, words, answer_to=None, payload=None):
    c = who.client(); c.get(f"/social/p/{post}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    if payload is not None:
        body["payload"] = payload
    st, j = c.post_json(f"/social/p/{post}/comments", body)
    if st != 200:
        print("say_ refused", st, str(j)[:200], flush=True)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def section_box(pg):
    return pg.evaluate("""() => { const s = document.querySelector('.cm').closest('section') || document.querySelector('.cm-list').parentElement;
        const r = s.getBoundingClientRect(); return { x: Math.max(0, r.left - 10), y: Math.max(0, r.top - 10),
          width: Math.min(innerWidth - Math.max(0, r.left - 10), r.width + 20), height: r.height + 20 }; }""")


meas = {}


def round_replies(b):
    """The yes (Read More Replies): the thread, a reply's own page, and a
    comment's sheet."""
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


# ================= THE DRAWINGS ROUND: a drawn reply in the thread, on its own page, in the way to it =================
# The owner, at the yes: "not sure how you'll handle drawings in there". The
# same thread, its drawings real ones from artworks.py (the owner's cat and
# pug, How it works' cottage and snail), each with the still picture an
# editor makes as it posts; and the three smaller questions the build needs.
sys.path.insert(0, str(ROOT / "harness" / "tools"))


def art_payload(strokes, seed=1, every=2, ground="#f6f2ea", size=(816, 612)):
    """A drawing from artworks.py as the Pad records one: artdraw.plan()'s
    hand (its timing and its pressure), every `every`th sample of the
    stylus's 240 a second, each point's size the brush's under that pressure
    (lib/pressure.js: 35% at the lightest touch), and a pause between strokes
    as a hand lifts and moves (handmotion.pause). Posted straight to the API
    it has no still picture; with_card() gives it the one an editor makes."""
    import artdraw
    import handmotion
    planned = artdraw.plan(strokes, seed=seed)
    pts, groups, t0, prev = [], [], 0.0, None
    for i, (st, sp) in enumerate(zip(strokes, planned)):
        sp = sp[::every] if len(sp) > 2 * every else sp
        if prev is not None:
            t0 += handmotion.pause(prev, sp[0][:2], seed=seed * 7 + i)
        last = None
        for k, (x, y, ms, pr) in enumerate(sp):
            t = int(round(t0 + ms))
            if last is not None and t <= last:
                t = last + 1
            last = t
            pts.append({"x": round(x, 1), "y": round(y, 1), "color": st.color,
                        "size": round(st.size * (0.35 + 0.65 * pr), 2), "t": t, "start": k == 0})
        groups.append(len(sp))
        t0 = last
        prev = sp[-1][:2]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "playSpeed": "auto",
            "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
            "frames": [{"strokes": pts, "strokeGroups": groups, "background": {"color": ground}}]}


CARD = r"""async (payload) => {
  const maker = document.querySelector('[data-skribl-face-maker]');
  if (!maker || !window.SkriblFaceFrame) return 'no maker';
  const box = maker.querySelector('.skribl-inline');
  const w = payload.canvasSize.cssWidth, h = payload.canvasSize.cssHeight;
  for (const e of [maker, box]) { e.style.width = w + 'px'; e.style.height = h + 'px'; }
  try { return await SkriblFaceFrame.card(payload, box); } catch (e) { return 'error ' + e.message; }
}"""


def with_card(who, payload):
    """The payload with the still picture an editor makes as it posts
    (lib/faceframe.js card(): the in-post player's own engine paints the
    drawing whole, lib/postedcard.js composes the card), made on the
    person's own page, which carries the face maker's box."""
    who.pg.goto(BASE + f"/social/@{who.handle}")
    who.pg.wait_for_function("() => document.readyState === 'complete' && !!window.SkriblFaceFrame && !!window.SkriblInline",
                             timeout=15000)
    url = who.pg.evaluate(CARD, payload)
    if not (isinstance(url, str) and url.startswith("data:image/")):
        print("no card:", str(url)[:120], flush=True)
        return payload
    return dict(payload, thumbnail=url)


STYLE = "(css) => { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); return 'ok'; }"

NOW_TIMES = r"""() => {
  const times = {0: '25m', 1: '5h', 2: '4h', 3: '3h', 4: '2h', 5: '1h', 6: '40m'};
  [...document.querySelectorAll('.cm')].forEach((c, i) => { const t = c.querySelector(':scope > .cm-main .cm-when'); if (t) { t.textContent = times[i] || '1h'; t.removeAttribute('data-when'); } });
  return 'ok'; }"""

# A drawn reply in its bubble: A, the 150px it is today, under its words;
# B, as wide as the bubble's room.
ART_CSS = {
    "a": ".cm-bubble .cm-art { width: 150px; max-width: 100%; margin: 8px 0 3px; }",
    "b": ".cm-bubble:has(> .cm-art) { width: 100%; } .cm-bubble .cm-art { width: 100%; margin: 8px 0 3px; }",
}
GONE_CSS = """
.cm-gone-face { display: block; width: 36px; height: 36px; border-radius: 50%; box-sizing: border-box; box-shadow: inset 0 0 0 1.5px var(--card-edge); }
.cm-gone { margin: 0; min-height: 36px; display: flex; align-items: center; color: var(--ink-2); font-size: 15px; line-height: 1.3; }
.ctx-item.has-pic { grid-template-columns: 36px minmax(0, 1fr) auto; }
.ctx-pic { position: relative; display: block; overflow: hidden; border-radius: 8px; align-self: start; margin: 2px 0 0 4px;
  background: var(--draw-wait, #fff); box-shadow: 0 0 0 var(--edge, 1px) var(--draw-edge, var(--card-edge)); }
.ctx-pic img { position: absolute; display: block; max-width: none; height: auto; }
/* The landing's tint, on the link itself: the line's curve is the row's ::before. */
.rm-link.is-glow { background: var(--tint); border-radius: 14px; padding: 0 14px 0 10px; margin-left: -10px; }
"""

# Deleting Ana's reply, which has Eli's drawn reply under it: today it goes
# with everything under it; or its place stays, quietly, and theirs stay.
GONE = r"""(how) => {
  const c1 = [...document.querySelectorAll('.cm-list > .cm')].find(c => c.querySelector(':scope > .cm-answers'));
  const r1 = c1 && c1.querySelector(':scope > .cm-answers > .cm');
  if (!r1) return 'no reply';
  if (how === 'goes') { r1.remove(); return 'ok'; }
  r1.classList.add('is-gone');
  const face = r1.querySelector(':scope > .face-ring');
  if (face) face.outerHTML = '<span class="cm-gone-face" aria-hidden="true"></span>';
  const main = r1.querySelector(':scope > .cm-main');
  main.innerHTML = '<p class="cm-gone">This reply was deleted</p>';
  return 'ok'; }"""

# Replying at the second level: the new reply is past the thread's two
# levels, so it joins "Read N more replies", which counts it and glows.
DEEP = r"""() => {
  const li = document.querySelector('.cm-readmore'); if (!li) return 'no read more';
  li.querySelector('.rm-link span').textContent = 'Read 3 more replies';
  li.querySelector('.rm-link').classList.add('is-glow');
  return 'ok'; }"""

# A DRAWN REPLY'S OWN PAGE, shot from a post that is that reply (Eli's, the
# pug, with its two replies under it): the way to it above, small, each
# drawing in it a still picture beside its words, cropped from its card as
# the in-post player crops its poster (lib/sharecard.js drawingRect).
PAGE_D = r"""(way) => {
  const title = document.querySelector('.top-title'); if (title) title.textContent = 'Reply';
  const art = document.querySelector('.post-page');
  art.querySelectorAll(':scope > .liked-by, :scope > .more-from').forEach(e => e.hidden = true);
  const cap = art.querySelector('.post-caption'); if (cap) cap.hidden = true;
  const disc = (n) => '<span class="face-ring is-blank ctx-face"><span class="face-blank" data-initial="' + n + '"></span></span>';
  const pic = (sid) => { if (!sid) return '';
    const W = 816, H = 612, s = Math.min(1092 / W, 492 / H), dw = Math.round(W * s), dh = Math.round(H * s);
    const x = Math.round((1200 - dw) / 2), y = Math.round((630 - 84 - dh) / 2), bh = 48, k = bh / dh, bw = Math.round(dw * k);
    return '<span class="ctx-pic" style="width:' + bw + 'px;height:' + bh + 'px"><img alt="" src="/s/' + sid + '/poster" style="width:'
      + (1200 * k).toFixed(2) + 'px;left:' + (-x * k).toFixed(2) + 'px;top:' + (-y * k).toFixed(2) + 'px"></span>'; };
  const item = (it) => '<div class="ctx-item' + (it.kind ? ' ' + it.kind : '') + (it.pic ? ' has-pic' : '') + '">' + disc(it.n)
    + '<div class="ctx-main"><div class="ctx-head"><b>' + it.name + '</b><span>' + it.when + '</span></div>'
    + (it.words ? '<p>' + it.words + '</p>' : '') + '</div>' + pic(it.pic) + '</div>';
  const ctx = document.createElement('div'); ctx.className = 'reply-ctx'; ctx.innerHTML = way.map(item).join('');
  art.insertBefore(ctx, art.firstElementChild);
  const head = art.querySelector('.post-head');
  head.querySelector('.post-face').innerHTML = disc('E');
  const meta = art.querySelector(':scope > .post-meta'); if (meta) meta.textContent = 'Today at 6:12 AM';
  const icon = (sel) => { const e = document.querySelector('.cm-acts ' + sel + ' svg') || document.querySelector('.post-row ' + sel + ' svg'); return e ? e.outerHTML : ''; };
  const pc = art.querySelector('.post-row .post-count'); if (pc) { const svg = pc.querySelector('svg'); pc.innerHTML = (svg ? svg.outerHTML : '') + '<span>2</span>'; }
  const hn = art.querySelector('.post-row .lk-heart'); if (hn) { const svg = hn.querySelector('svg'); hn.classList.remove('is-zero'); hn.innerHTML = (svg ? svg.outerHTML : '') + '<span class="lk-n">4</span>'; }
  const ct = document.querySelector('.comments-title'); if (ct) { const n = ct.querySelector('.cm-count'); const sp = [...ct.querySelectorAll('span')].find(x => x.textContent.trim() === 'Comments'); if (sp) sp.textContent = 'Replies'; if (n) { n.hidden = false; n.textContent = '2'; } }
  return 'ok'; }"""

MEASURE_D = r"""() => {
  const lum = (c) => { const v = c.slice(0, 3).map(x => x / 255).map(x => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const rgb = (s) => { const m = s.match(/color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)/); if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255]; return (s.match(/[\d.]+/g) || []).map(Number).slice(0, 3); };
  const ratio = (a, b) => { const x = lum(rgb(a)), y = lum(rgb(b)); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const page = getComputedStyle(document.body).backgroundColor;
  const out = { arts: [], gone: null, pics: [], page };
  document.querySelectorAll('.cm-art').forEach(a => {
    let d = 0, e = a.closest('.cm'); while (e && e.parentElement.closest('.cm')) { d++; e = e.parentElement.closest('.cm'); }
    const r = a.getBoundingClientRect(), bub = a.closest('.cm-bubble'), box = a.querySelector('.skribl-inline');
    const holder = bub || a.closest('.cm-main');
    out.arts.push({ depth: d, w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10,
      room: holder ? Math.round(holder.parentElement.getBoundingClientRect().width) : null,
      behind: bub ? getComputedStyle(bub).backgroundColor : page,
      paper_vs_behind: ratio('rgb(246, 242, 234)', bub ? getComputedStyle(bub).backgroundColor : page),
      ring: box ? getComputedStyle(box).boxShadow.slice(0, 80) : null });
  });
  const g = document.querySelector('.cm-gone'); if (g) out.gone = ratio(getComputedStyle(g).color, page);
  document.querySelectorAll('.ctx-pic').forEach(p => { const r = p.getBoundingClientRect(); out.pics.push([Math.round(r.width), Math.round(r.height)]); });
  const rm = document.querySelector('.rm-link'); if (rm) out.readmore = ratio(getComputedStyle(rm).color, page);
  return out; }"""

PAGE_BOX = """() => { const a = document.querySelector('.post-page'), r = a.getBoundingClientRect(), t = document.querySelector('.top, header.top, .site-top');
    const top = t ? Math.max(0, t.getBoundingClientRect().top) : 0;
    let bottom = r.top; a.querySelectorAll(':scope > *:not([hidden])').forEach(e => { const b = e.getBoundingClientRect(); if (b.height) bottom = Math.max(bottom, b.bottom); });
    return { x: Math.max(0, r.left - 10), y: top, width: Math.min(innerWidth - Math.max(0, r.left - 10), r.width + 20), height: bottom - top + 16 }; }"""


def snap(pg, name, kind):
    """The comments section (kind "thread"), or the whole post page from the
    top bar down ("page"), the window grown to hold it, at 2x."""
    if kind == "page":
        pg.evaluate("() => window.scrollTo(0, 0)")
        pg.wait_for_timeout(250)
        box = pg.evaluate(PAGE_BOX)
    else:
        pg.evaluate("() => { const s = document.querySelector('.cm').closest('section') || document.querySelector('.cm-list').parentElement; s.scrollIntoView({ block: 'start' }); }")
        pg.wait_for_timeout(250)
        box = section_box(pg)
    vp = pg.viewport_size
    need = int(box["y"] + box["height"] + 30)
    if need > vp["height"]:
        pg.set_viewport_size({"width": vp["width"], "height": need})
        pg.wait_for_timeout(300)
        box = pg.evaluate(PAGE_BOX) if kind == "page" else section_box(pg)
    pg.screenshot(path=f"{OUT}/shots/{name}.png", clip=box)


def round_drawings(b):
    """Drawings in a thread: today's look, then the plan (A: 150px in its
    bubble; B: as wide as the bubble's room), a drawn reply's own page with
    the way to it, and the smaller questions' pictures (deleting a reply
    with replies under it; replying at the second level)."""
    import artworks
    ben = member(b, "ben", "Ben Okafor")
    ana = member(b, "ana", "Ana Reyes")
    cyd = member(b, "cyd", "Cyd Marsh")
    dee = member(b, "dee", "Dee Park")
    eli = member(b, "eli", "Eli Moss")
    scene = with_card(ben, art_payload(artworks.scene(), seed=2))
    cat = with_card(ana, art_payload(artworks.cat(), seed=3))
    pug = with_card(eli, art_payload(artworks.pug(), seed=4))
    snail = with_card(dee, art_payload(artworks.snail(), seed=5))
    print("payloads", {k: len(json.dumps(v)) for k, v in (("scene", scene), ("cat", cat), ("pug", pug), ("snail", snail))},
          flush=True)
    post = make_post(ben, "Morning ride past the old cottage, drawn on the train", payload=scene)
    c1 = say_(eli, post, "Is that the cottage by the river? I think I know it.")
    r1 = say_(ana, post, "It is! Our cat lives there.", answer_to=c1, payload=cat)
    say_(ben, post, "Yes, the one by the old mill. Good eye.", answer_to=c1)
    r3 = say_(eli, post, "Then she needs a friend.", answer_to=r1, payload=pug)
    r4 = say_(ana, post, "Ha! They'd be best friends.", answer_to=r3)
    say_(cyd, post, "I'd watch that cartoon every Sunday.", answer_to=r4)
    say_(dee, post, "", payload=snail)
    own = make_post(eli, "Then she needs a friend.", payload=pug)
    a1 = say_(ana, own, "Ha! They'd be best friends.")
    say_(cyd, own, "I'd watch that cartoon every Sunday.", answer_to=a1)
    print("fixture", post, own, flush=True)

    def sid(cid):
        got = db("select skribl_id from social_comments where public_id = ?", (cid or "",))
        return got[0][0] if got else None
    way = [{"n": "B", "name": "Ben Okafor", "when": "6h", "words": "Morning ride past the old cottage, drawn on the train",
            "pic": skribl_of(post), "kind": "is-post"},
           {"n": "E", "name": "Eli Moss", "when": "5h", "words": "Is that the cottage by the river? I think I know it.",
            "pic": None},
           {"n": "A", "name": "Ana Reyes", "when": "4h", "words": "It is! Our cat lives there.", "pic": sid(r1)}]
    for screen in ("phone", "desk"):
        for scheme in ("light", "dark"):
            for opt in ("now", "a", "b", "goes", "keeps", "deep"):
                ctx, pg = browser_as(b, ana, screen=screen, scheme=scheme)
                go(pg, f"/social/p/{post}", wait=900)
                if opt == "now":
                    st = pg.evaluate(NOW_TIMES)
                else:
                    st = pg.evaluate(SETUP, "thread")
                    pg.evaluate(STYLE, ART_CSS["b" if opt == "b" else "a"] + GONE_CSS)
                    if opt in ("goes", "keeps"):
                        st = pg.evaluate(GONE, opt)
                    elif opt == "deep":
                        st = pg.evaluate(DEEP)
                pg.wait_for_timeout(500)
                snap(pg, f"dr-{screen}-{scheme}-{opt}", "thread")
                meas[f"{screen} {scheme} {opt}"] = dict(pg.evaluate(MEASURE_D), setup=st)
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, ana, screen=screen, scheme=scheme, reduced=True)
            go(pg, f"/social/p/{own}", wait=1200)
            pg.evaluate("() => { window.__mockTimes = {0: '1h', 1: '40m'}; window.__mockCounts = [[0, 0, 0], [0, 6, 0]]; }")
            pg.evaluate(SETUP, "thread")
            pg.evaluate(STYLE, ART_CSS["a"] + GONE_CSS)
            st = pg.evaluate(PAGE_D, way)
            pg.wait_for_timeout(900)
            snap(pg, f"dr-{screen}-{scheme}-page", "page")
            meas[f"{screen} {scheme} page"] = dict(pg.evaluate(MEASURE_D), setup=st)
            close_ctx(ctx, pg)
            print(screen, scheme, "done", flush=True)


# ================= STEP 3: A COMMENT OUT IN THE WORLD (repost, quote, bookmark) =================
# Nothing in the app reposts, quotes or keeps a comment yet, so the cards are
# today's own, made over: the repost of Ben's post becomes Ana's repost of
# Eli's comment; Ana's cat, posted as a stand-in, becomes her drawn reply
# reposted by Cyd (its player is the post's own, so it plays as a post's);
# Cyd's quote of Ben's post quotes Eli's comment; Dee's bookmark of Ben's
# post keeps Eli's comment. A: the way to it above (the post, small, its
# still beside it; for a reply the comment too), joined by the thread's line
# to the comment, as on its own page. B: the comment alone, a line under its
# name saying what it is on ("On Ben's post", "Reply to Eli").
WORLD_CSS = """
.post-card .cm-way { margin: 0 0 4px; }
.post-card .cm-way-link { grid-template-columns: 44px minmax(0, 1fr) auto; }
.post-card .cm-way-link > :first-child { justify-self: center; }
.post-card .cm-way-item::before { left: 21px; }
.post-card .cm-way-item:last-child::before { bottom: -4px; }
.mock-to { display: flex; align-items: center; gap: 8px; margin: 10px 0 -4px; color: var(--ink-2); font-size: 14px; font-weight: 600; line-height: 1.3; }
.mock-to .ic { flex: none; width: 16px; height: 16px; margin-left: 14px; margin-right: 6px; }
.qt-on { display: block; margin-top: 2px; color: var(--ink-2); font-size: 14px; }
.nav { visibility: hidden !important; }
"""

WORLD = r"""async (d) => {
  const parse = async (path) => new DOMParser().parseFromString(await (await fetch(path, { credentials: 'same-origin' })).text(), 'text/html');
  const card = (id) => document.querySelector('.post-card[data-post="' + id + '"]');
  const time = (el, t) => { if (el) { el.textContent = t; el.removeAttribute('data-when'); } };
  const row = (c, n) => {
    const put = (el, cls, k) => { if (!el) return; let s = el.querySelector(cls ? '.' + cls : 'span');
      if (k) { if (!s) { s = document.createElement('span'); if (cls) s.className = cls; el.appendChild(s); } s.textContent = k; el.classList.remove('is-zero'); }
      else if (s) s.remove(); };
    put(c.querySelector('.post-row .post-count'), '', n[0]); put(c.querySelector('.post-row .rp-btn'), 'rp-n', n[1]);
    put(c.querySelector('.post-row .lk-heart'), 'lk-n', n[2]); };
  const s = document.createElement('style'); s.textContent = d.css; document.head.appendChild(s);
  const out = {};
  const c1 = card(d.repost), c2 = card(d.stand), q = card(d.quote), mk = card(d.mark);
  if (c1) { time(c1.querySelector('.post-head time'), '6h'); row(c1, [3, 2, 12]); }
  if (q) { time(q.querySelector('.post-head time'), '1h'); time(q.querySelector('.qt-card time'), '6h'); row(q, [0, 0, 3]); }
  if (mk) { time(mk.querySelector('.post-head time'), '6h'); row(mk, [3, 2, 12]); }
  if (c2) c2.hidden = d.opt === 'now';
  if (d.opt === 'now') return { cards: [!!c1, !!c2, !!q, !!mk] };
  const [p1, pr] = await Promise.all([parse('/social/c/' + d.c1), parse('/social/c/' + d.r1)]);
  const icon = (sel) => { const e = document.querySelector(sel + ' svg'); return e ? e.outerHTML : ''; };
  // THE COMMENT, MADE OVER FROM A CARD: its face, name, @handle, time, words, row.
  const become = (c, page, who) => {
    const face = page.querySelector('.post-head .post-face');
    const f = c.querySelector('.post-head .post-face');
    if (face && f && who.blank) f.innerHTML = face.innerHTML;
    const nm = c.querySelector('.post-head .post-name'); if (nm) { nm.textContent = who.name; nm.href = '/social/@' + who.handle; }
    const sub = c.querySelector('.post-head .post-sub');
    if (sub) { const w = sub.querySelector('.post-when'); sub.firstChild.textContent = '@' + who.handle + ' · ';
      if (w) { w.href = '/social/c/' + who.id; time(w.querySelector('time'), who.when); } }
    if (who.words !== undefined) { const pw = c.querySelector('.post-words'); if (pw) pw.textContent = who.words; }
    if (who.noArt) c.querySelectorAll('.post-art, .qt-card').forEach(e => e.remove());
    const open = c.querySelector('.post-open'); if (open) open.href = '/social/c/' + who.id;
    row(c, who.row);
  };
  const way = (c, page) => { const w = page.querySelector('.cm-way'); if (!w) return;
    const n = document.importNode(w, true); n.querySelectorAll('time').forEach((t, i) => time(t, d.wayTimes[i] || '6h'));
    c.insertBefore(n, c.querySelector('.post-head')); };
  const to = (c, words) => { const p = document.createElement('p'); p.className = 'mock-to';
    p.innerHTML = icon('.post-row .post-count') + '<span>' + words + '</span>';
    c.querySelector('.post-head').after(p); };
  const eli = { name: 'Eli Moss', handle: 'eli', id: d.c1, when: '5h', blank: true, noArt: true,
                words: 'Is that the cottage by the river? I think I know it.', row: [2, 1, 4] };
  if (c1) { become(c1, p1, eli); if (d.opt === 'a') way(c1, p1); else to(c1, "On Ben’s post"); }
  if (c2) {
    const fc = pr.querySelector('.post-head .post-face'), f2 = c2.querySelector('.post-head .post-face');
    if (fc && f2) f2.innerHTML = fc.innerHTML;
    const by = c1 && c1.querySelector('.rp-by');
    if (by) { const n = by.cloneNode(true); n.querySelector('span').textContent = 'Cyd Marsh reposted'; c2.prepend(n); }
    time(c2.querySelector('.post-head time'), '4h');
    const open = c2.querySelector('.post-open'); if (open) open.href = '/social/c/' + d.r1;
    row(c2, [1, 1, 9]);
    if (d.opt === 'a') way(c2, pr); else to(c2, 'Reply to Eli');
  }
  if (mk) { become(mk, p1, eli); if (d.opt === 'a') way(mk, p1); else to(mk, "On Ben’s post"); }
  if (q) {
    const qc = q.querySelector('.qt-card');
    if (qc) { qc.href = '/social/c/' + d.c1; qc.querySelector('.qt-name').textContent = 'Eli Moss';
      const sub = qc.querySelector('.qt-sub'); sub.firstChild.textContent = '@eli · '; time(sub.querySelector('time'), '5h');
      const on = document.createElement('span'); on.className = 'qt-on'; on.textContent = "On Ben’s post";
      qc.querySelector('.qt-head').after(on);
      const qw = qc.querySelector('.qt-words'); if (qw) qw.textContent = eli.words;
      const pic = qc.querySelector('.qt-pic'); if (pic) pic.remove(); }
  }
  out.cards = [!!c1, !!c2, !!q, !!mk];
  return out; }"""

WORLD_MEASURE = r"""() => {
  const lum = (c) => { const m = c.match(/[\d.]+/g).map(Number); const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const ground = (el) => { for (let e = el; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor; if (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) return bg; } return 'rgb(255, 255, 255)'; };
  const read = (sel) => { const e = document.querySelector(sel); if (!e) return null; const cs = getComputedStyle(e);
    return { ratio: ratio(cs.color, ground(e)), size: cs.fontSize, weight: cs.fontWeight }; };
  const h = (sel) => { const e = document.querySelector(sel); return e ? Math.round(e.getBoundingClientRect().height) : null; };
  const cards = [...document.querySelectorAll('.feed .post-card:not([hidden]), .post-card:not([hidden])')];
  const face = document.querySelector('.post-card .post-head .post-face');
  const wayFace = document.querySelector('.post-card .cm-way-link > :first-child');
  const centre = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return Math.round((r.left + r.width / 2) * 10) / 10; };
  return { reposted: read('.post-card .rp-by span'), wayWords: read('.post-card .cm-way-item:first-child .cm-way-words'),
           wayName: read('.post-card .cm-way-head b'), wayTime: read('.post-card .cm-way-head time'), to: read('.post-card .mock-to span'),
           quoteOn: read('.qt-card .qt-on'), quoteWords: read('.qt-card .qt-words'),
           heights: cards.slice(0, 4).map(c => Math.round(c.getBoundingClientRect().height)),
           centres: { face: centre(face), wayFace: centre(wayFace) } }; }"""


def world_box(pg, sels):
    """The box round the cards `sels` names (the first to the last), with a margin."""
    return pg.evaluate("""(sels) => { const els = sels.map(s => document.querySelector(s)).filter(e => e && !e.hidden);
      if (!els.length) return null; const rs = els.map(e => e.getBoundingClientRect());
      const top = Math.min(...rs.map(r => r.top)), bottom = Math.max(...rs.map(r => r.bottom));
      const left = Math.min(...rs.map(r => r.left)), right = Math.max(...rs.map(r => r.right));
      return { x: Math.max(0, left - 12), y: Math.max(0, top - 12), width: Math.min(innerWidth, right + 12) - Math.max(0, left - 12), height: bottom - top + 24 }; }""", sels)


def shoot_world(pg, name, sels):
    pg.evaluate(f"() => document.querySelector({json.dumps(sels[0])})?.scrollIntoView({{ block: 'start' }})")
    pg.wait_for_timeout(300)
    box = world_box(pg, sels)
    if not box:
        print("nothing to shoot for", name, flush=True)
        return
    vp = pg.viewport_size
    need = int(box["y"] + box["height"] + 30)
    if need > vp["height"]:
        pg.set_viewport_size({"width": vp["width"], "height": need})
        pg.wait_for_timeout(400)
        pg.evaluate(f"() => document.querySelector({json.dumps(sels[0])})?.scrollIntoView({{ block: 'start' }})")
        pg.wait_for_timeout(200)
        box = world_box(pg, sels)
    pg.screenshot(path=f"{OUT}/shots/{name}.png", clip=box)


def round_world(b):
    """Step 3, a comment out in the world: on Home's Following (reposted),
    quoted, and kept in Your Bookmarks; today's look, then A (the way to it
    above) and B (alone, with what it is on)."""
    import artworks
    ben = member(b, "ben", "Ben Okafor")
    ana = member(b, "ana", "Ana Reyes")
    cyd = member(b, "cyd", "Cyd Marsh")
    dee = member(b, "dee", "Dee Park")
    eli = member(b, "eli", "Eli Moss")
    scene = with_card(ben, art_payload(artworks.scene(), seed=2))
    cat = with_card(ana, art_payload(artworks.cat(), seed=3))
    post = make_post(ben, "Morning ride past the old cottage, drawn on the train", payload=scene)
    c1 = say_(eli, post, "Is that the cottage by the river? I think I know it.")
    r1 = say_(ana, post, "It is! Our cat lives there.", answer_to=c1, payload=cat)
    say_(ben, post, "Yes, the one by the old mill. Good eye.", answer_to=c1)
    stand = make_post(ana, "It is! Our cat lives there.", payload=cat)
    dc = dee.client()
    dc.get("/social/")
    for h in ("ana", "cyd"):
        print("follow", h, dc.post_json(f"/social/@{h}/follow", {"following": True})[0], flush=True)
    print("home", dc.post_json("/social/home/show", {"show": "following"})[0], flush=True)
    ac = ana.client()
    ac.get(f"/social/p/{post}")
    print("repost", ac.post_json(f"/social/p/{post}/repost", {"reposted": True})[0], flush=True)
    cc = cyd.client()
    cc.get("/social/")
    st, j = cc.post_json("/social/posts", {"words": "This made my morning", "quote": post})
    quote = j.get("post") if st == 200 and isinstance(j, dict) else None
    print("quote", st, quote, flush=True)
    dc.get(f"/social/p/{post}")
    print("bookmark", dc.post_json(f"/social/p/{post}/bookmark", {"bookmarked": True})[0], flush=True)
    data = {"repost": post, "stand": stand, "quote": quote, "mark": post, "c1": c1, "r1": r1,
            "wayTimes": ["6h", "5h"], "css": WORLD_CSS}
    for screen in ("phone", "desk"):
        for scheme in ("light", "dark"):
            for opt in ("now", "a", "b"):
                ctx, pg = browser_as(b, dee, screen=screen, scheme=scheme, reduced=True)
                go(pg, "/social/", wait=1200)
                st = pg.evaluate(WORLD, dict(data, opt=opt, mark="-"))
                pg.wait_for_timeout(900)
                shoot_world(pg, f"wo-{screen}-{scheme}-{opt}", [f'.post-card[data-post="{post}"]', f'.post-card[data-post="{stand}"]'])
                meas[f"{screen} {scheme} {opt} feed"] = dict(pg.evaluate(WORLD_MEASURE), setup=st)
                if quote:
                    shoot_world(pg, f"wq-{screen}-{scheme}-{opt}", [f'.post-card[data-post="{quote}"]'])
                close_ctx(ctx, pg)
                if screen == "phone":
                    ctx, pg = browser_as(b, dee, screen=screen, scheme=scheme, reduced=True)
                    go(pg, "/social/@dee/bookmarks", wait=1200)
                    st = pg.evaluate(WORLD, dict(data, opt=opt, repost="-", stand="-", quote="-"))
                    pg.wait_for_timeout(700)
                    shoot_world(pg, f"wb-{screen}-{scheme}-{opt}", [f'.post-card[data-post="{post}"]'])
                    meas[f"{screen} {scheme} {opt} bookmarks"] = dict(pg.evaluate(WORLD_MEASURE), setup=st)
                    close_ctx(ctx, pg)
            print(screen, scheme, "done", flush=True)


# ================= THE TREE FOLDED: comments only until one is chosen =================
# The owner, Nov 17, at the step 1 answers: "We don't want the whole tree
# visible until someone selects the reply. It just shows replies then if
# reply is clicked you see all the subs." On the page as step 1 built it:
# today (two levels, then "Read N more replies"); A, each conversation folded
# to "Read N replies", which opens that comment's own page (as built: the
# way, it, every reply under it, two levels again); B, the same fold, which
# unfolds in place instead (shown unfolded on the first, "Hide replies" at
# its end).
TREE = r"""([opt, unfold]) => {
  const svg = (document.querySelector('.rm-link svg') || {}).outerHTML || '';
  const minus = svg.replace(/M12 8v8/, '');
  const row = (words, href, icon) => { const l = document.createElement('li'); l.className = 'cm-rm';
    l.innerHTML = '<a class="rm-link" href="' + href + '">' + icon + '<span>' + words + '</span></a>'; return l; };
  const out = [];
  [...document.querySelectorAll('.cm-list > li.cm')].forEach((li) => {
    const ans = li.querySelector(':scope > .cm-answers'); if (!ans) return;
    const n = ans.querySelectorAll('li.cm:not(.is-gone)').length
      + [...ans.querySelectorAll('.cm-rm')].reduce((a, r) => a + (+r.dataset.n || 0), 0);
    out.push(n);
    if (opt === 'b' && li.id === 'c-' + unfold) { ans.appendChild(row('Hide replies', '#', minus)); return; }
    ans.innerHTML = '';
    ans.appendChild(row('Read ' + n + (n === 1 ? ' reply' : ' replies'), '/social/c/' + li.id.replace(/^c-/, ''), svg));
  });
  return out; }"""

TREE_MEASURE = r"""() => { const s = document.querySelector('.cm-list'); const r = s.getBoundingClientRect();
  const rm = document.querySelector('.rm-link'); return { list: Math.round(r.height), links: [...document.querySelectorAll('.rm-link span')].map(e => e.textContent),
  linkH: rm ? Math.round(rm.getBoundingClientRect().height) : null }; }"""


def round_tree(b):
    """The tree folded: today, A (folded, opening the comment's own page),
    B (folded, unfolding in place); and the page A opens."""
    import artworks
    ben = member(b, "ben", "Ben Okafor")
    ana = member(b, "ana", "Ana Reyes")
    cyd = member(b, "cyd", "Cyd Marsh")
    dee = member(b, "dee", "Dee Park")
    eli = member(b, "eli", "Eli Moss")
    scene = with_card(ben, art_payload(artworks.scene(), seed=2))
    cat = with_card(ana, art_payload(artworks.cat(), seed=3))
    snail = with_card(dee, art_payload(artworks.snail(), seed=5))
    post = make_post(ben, "Morning ride past the old cottage, drawn on the train", payload=scene)
    c1 = say_(eli, post, "Is that the cottage by the river? I think I know it.")
    r1 = say_(ana, post, "It is! Our cat lives there.", answer_to=c1, payload=cat)
    r2 = say_(ben, post, "Yes, the one by the old mill. Good eye.", answer_to=c1)
    r3 = say_(eli, post, "Then she needs a friend.", answer_to=r1)
    r4 = say_(ana, post, "Ha! They'd be best friends.", answer_to=r3)
    r5 = say_(cyd, post, "I'd watch that cartoon every Sunday.", answer_to=r4)
    c2 = say_(cyd, post, "Love the little curl of smoke from the chimney.")
    r6 = say_(ben, post, "Thank you! It took three tries.", answer_to=c2)
    c3 = say_(dee, post, "", payload=snail)
    print("fixture", post, c1, c2, flush=True)
    when = {c1: "5h", r1: "4h", r2: "4h", r3: "3h", r4: "2h", r5: "1h", c2: "2h", r6: "1h", c3: "25m"}
    for screen in ("phone", "desk"):
        for scheme in ("light", "dark"):
            for opt in ("now", "a", "b"):
                ctx, pg = browser_as(b, dee, screen=screen, scheme=scheme, reduced=True)
                go(pg, f"/social/p/{post}", wait=900)
                pg.evaluate("""(m) => { for (const [id, t] of Object.entries(m)) { const li = document.getElementById('c-' + id);
                  const w = li && li.querySelector(':scope > .cm-main .cm-when'); if (w) w.textContent = t; } }""", when)
                pg.evaluate(STYLE, ".nav { visibility: hidden !important; }")
                st = pg.evaluate(TREE, [opt, c1]) if opt != "now" else None
                pg.wait_for_timeout(400)
                snap(pg, f"tr-{screen}-{scheme}-{opt}", "thread")
                meas[f"{screen} {scheme} {opt}"] = dict(pg.evaluate(TREE_MEASURE), setup=st)
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, dee, screen=screen, scheme=scheme, reduced=True)
            go(pg, f"/social/c/{c1}", wait=1200)
            pg.evaluate("""(m) => { for (const [id, t] of Object.entries(m)) { const li = document.getElementById('c-' + id);
              const w = li && li.querySelector(':scope > .cm-main .cm-when'); if (w) w.textContent = t; }
              const way = document.querySelector('.cm-way-head time'); if (way) way.textContent = '6h';
              const at = document.querySelector('.post-meta time'); if (at) at.textContent = 'Nov 17 at 2:12 PM'; }""", when)
            pg.evaluate(STYLE, ".nav { visibility: hidden !important; }")
            snap(pg, f"tr-{screen}-{scheme}-page", "page")
            close_ctx(ctx, pg)
            print(screen, scheme, "done", flush=True)


# ================= THE COUNT BY THE TALK CLOUD (the owner, Nov 17, after step 3) =================
# "You only need to show the replies not the nested 5 replies. Click on the
# reply and it shows you the nested tree. First reply just has count by the
# talk cloud." Today a comment with replies under it carries "Read N
# replies" on the thread's lilac line; A takes that line away and puts the
# count in the comment's own row, beside its talk cloud, as a post's row
# says how many comments ("💬 5"; on a desk the word Reply gives way to the
# count, and stays at none). A tap on the comment still opens its page.
COUNT = r"""(opt) => {
  const out = [];
  document.querySelectorAll('.cm').forEach(li => {
    const ans = li.querySelector(':scope > .cm-answers'), rm = ans && ans.querySelector('.cm-rm');
    if (!rm) return;
    const n = rm.getAttribute('data-n');
    out.push([li.id, n]);
    if (opt === 'now') return;
    ans.remove();
    const b = li.querySelector(':scope > .cm-main .cm-act[data-cm-answer]');
    if (b && !b.querySelector('.cm-n')) { const c = document.createElement('span'); c.className = 'cm-n'; c.textContent = n;
      b.querySelector('svg').after(c); b.setAttribute('aria-label', n + (n === '1' ? ' reply' : ' replies') + ' · Reply'); }
  });
  return out; }"""
COUNT_CSS = """
.cm-act .cm-n { font-variant-numeric: tabular-nums; }
.cm-act:has(.cm-n) .cm-word { display: none; }
.nav { visibility: hidden !important; }
"""
COUNT_MEASURE = r"""() => {
  const lum = (c) => { const m = c.match(/[\d.]+/g).map(Number); const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const ground = (el) => { for (let e = el; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor; if (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) return bg; } return 'rgb(255, 255, 255)'; };
  const list = document.querySelector('.cm-list'), n = document.querySelector('.cm-act .cm-n');
  const rows = [...document.querySelectorAll('.cm-list > .cm')].map(li => [...li.querySelectorAll(':scope > .cm-main .cm-acts > *')]
    .filter(e => e.getClientRects().length).map(e => e.textContent.trim() || e.getAttribute('aria-label')));
  return { listH: list ? Math.round(list.getBoundingClientRect().height) : null, rows,
           count: n ? { ratio: ratio(getComputedStyle(n).color, ground(n)), size: getComputedStyle(n).fontSize } : null }; }"""


def round_count(b):
    """The count by the talk cloud: today (Read N replies on the line) and A
    (the count in the row), the post's list and a comment's own page."""
    import artworks
    ben = member(b, "ben", "Ben Okafor")
    ana = member(b, "ana", "Ana Reyes")
    cyd = member(b, "cyd", "Cyd Marsh")
    dee = member(b, "dee", "Dee Park")
    eli = member(b, "eli", "Eli Moss")
    scene = with_card(ben, art_payload(artworks.scene(), seed=2))
    cat = with_card(ana, art_payload(artworks.cat(), seed=3))
    post = make_post(ben, "Morning ride past the old cottage, drawn on the train", payload=scene)
    c1 = say_(eli, post, "Is that the cottage by the river? I think I know it.")
    r1 = say_(ana, post, "It is! Our cat lives there.", answer_to=c1, payload=cat)
    r2 = say_(ben, post, "Yes, the one by the old mill. Good eye.", answer_to=c1)
    r3 = say_(eli, post, "Then she needs a friend.", answer_to=r1)
    r4 = say_(ana, post, "Ha! They'd be best friends.", answer_to=r3)
    r5 = say_(cyd, post, "I'd watch that cartoon every Sunday.", answer_to=r4)
    c2 = say_(cyd, post, "Love the little curl of smoke from the chimney.")
    r6 = say_(ben, post, "Thank you! It took three tries.", answer_to=c2)
    print("fixture", post, c1, c2, flush=True)
    when = {c1: "5h", r1: "4h", r2: "4h", r3: "3h", r4: "2h", r5: "1h", c2: "2h", r6: "1h"}
    TIMES = """(m) => { for (const [id, t] of Object.entries(m)) { const li = document.getElementById('c-' + id);
      const w = li && li.querySelector(':scope > .cm-main .cm-when'); if (w) w.textContent = t; }
      const way = document.querySelector('.cm-way-head time'); if (way) way.textContent = '6h';
      const at = document.querySelector('.post-meta time'); if (at) at.textContent = 'Nov 17 at 2:12 PM'; }"""
    for screen in ("phone", "desk"):
        for scheme in ("light", "dark"):
            for where, path, kind in (("list", f"/social/p/{post}", "thread"), ("page", f"/social/c/{c1}", "page")):
                for opt in ("now", "a"):
                    ctx, pg = browser_as(b, dee, screen=screen, scheme=scheme, reduced=True)
                    go(pg, path, wait=1000)
                    pg.evaluate(TIMES, when)
                    pg.evaluate(STYLE, COUNT_CSS)
                    st = pg.evaluate(COUNT, opt)
                    pg.wait_for_timeout(400)
                    snap(pg, f"ct-{where}-{screen}-{scheme}-{opt}", kind)
                    meas[f"{where} {screen} {scheme} {opt}"] = dict(pg.evaluate(COUNT_MEASURE), setup=st)
                    close_ctx(ctx, pg)
            print(screen, scheme, "done", flush=True)


ROUND = os.environ.get("MOCK_ROUND", "replies")
with sync_playwright() as p:
    b = p.chromium.launch()
    {"drawings": round_drawings, "world": round_world, "tree": round_tree, "count": round_count}.get(ROUND, round_replies)(b)
    b.close()
open(f"{OUT}/measure.json", "w").write(_json.dumps(meas, indent=1))
if ERRS:
    print("page errors:", *ERRS[:12], sep="\n  ")
print("ok")
