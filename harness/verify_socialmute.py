"""Muting on the Skribl site (phase 2, mutes; docs/SOCIAL-SITE.md "Built:
mutes"), through the demo's own server, with Chromium's virtual
authenticator for the site's people. The owner's "Yes to all" on the mute
mock (Nov 13): C, quiet everywhere, and rule 3, mute and follow kept apart.

  1. WHERE YOU MUTE: "Mute @them" first in the ⋯ on somebody's page, after
     Share… and before Report and Block on their post's and drawing's ⋯, with
     its line, "Their posts, comments and likes stop reaching you. They
     aren’t told."; a closed eye in our pen, never a speaker; the row's words
     the size and weight of Report's and Block's, starting where theirs do,
     its eye centred on the other icons (painted); muted, "Unmute @them" and
     "Everything comes back, just as it was."; never on your own, never
     signed out.
  2. NOTHING ASKED FIRST: the tap mutes (kept, no sheet asks); the toast,
     "Theo is muted. They aren’t told." with Undo, a status; on a phone 12px
     above the bar, on a desk at the foot of the page in the middle of the
     column, clear of the rail; never on the ⋯ that opened it; a tap on its
     words reaches the page under it; Undo 44px to a finger; seven seconds,
     then it goes; Undo brings everything back, says so, and gives the ⋯
     its focus back.
  3. KIND, NEVER JUMPY, ON HOME, read on every frame from the tap: the card
     fades, then its room closes and the next post rises into its place,
     never going back; the toast fades in and rises, never on the bar; Undo
     the same way back; under Reduce Motion the room is put there only once
     the card can't be seen, and the toast only fades.
  4. THEIR PAGE: "You muted Theo · Unmute" under the buttons, yours alone
     (not for them, nobody else, not signed out, not in the source); their ⋯
     says Unmute; muting there opens the line, read on every frame (and under
     Reduce Motion); its Unmute unmutes and closes it; their skribls, posts
     and More from all still there.
  5. RULE 3: a mute never touches a follow: still following, the toast says
     "Theo is muted. You still follow them.", nothing changes on their side
     (their own "Followed by…"), their posts out of Following until unmute;
     unfollowing never unmutes.
  6. HOME AND EXPLORE: their posts and drawings leave Home, Everyone and
     Following, in the query (every page whole, walked with Load more);
     Explore's listing (New, Hot, a search) leaves out their drawings; their
     page's listing, their drawing's page, its link page and its payload stay
     open: a mute hides no page.
  7. THE FOLD: their comment or answer is one quiet line, "Someone you
     muted said something. Show" ("… answered."), the eye where their face
     was and the words where names start; hidden for real; the answers under
     it by others stay; the count unchanged; on your own post too; Show opens
     it for the visit, read on every frame (and under Reduce Motion); a page
     brought by Load more folds too.
  8. ACTIVITY GOES QUIET: their comments, answers, likes and follows leave
     it; a group says the rest; they never light the bell's dot (somebody
     else's comment does); unmute, and every row is back.
  9. COUNTS AND "LIKED BY…" STAY TRUE, for you too.
 10. SETTINGS: Muted just above Blocked, the Blocked panel's rows, newest
     first, its words; with nobody, its own; Unmute (a form) comes back to
     Settings saying so; somebody muted and then blocked is under Blocked
     alone, and unblocked is muted still.
 11. WHO MAY MUTE: signed out, without the token or from elsewhere: refused;
     yourself, nobody by that name, a block either way, somebody taken down:
     "gone", nothing kept; the limit (60 an hour); a refusal in the page puts
     everything back and says why.
 12. NOTHING FOR ANYBODY ELSE: signed out no row, no toast, no script; your
     own page and a blocked person's none.
 13. THE DATA: the chain on a populated database (up, its table, three
     indexes and CHECK; down; up again), one row a pair, never yourself; its
     PostgreSQL DDL read offline; the reads on their indexes; Home with no
     read a card and one read of mutes a request; deleting an account takes
     its mutes both ways, in code, with SQLite's cascade off.
 14. WORDS AND MARKS: every new word at 4.5:1 and every new mark at 3:1, each
     read two ways (its colour against what is painted behind it, and the
     pixels), the lower counting; every word on every new screen (the census);
     every new control 44px to a finger; no field under 16px; phone (touch)
     and desk, light and dark.
 15. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALMUTE_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Mute at /social".
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
from collections import Counter
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALMUTE_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALMUTE {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence muting works.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)
try:
    from PIL import Image
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r harness/requirements.txt): the painted readings need Pillow")
    raise SystemExit(77)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialmute-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialmute-" + secrets.token_hex(8),
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

# A PHONE IS A TOUCH PHONE (WORKING-AGREEMENTS): is_mobile and has_touch, the
# owner's 402 x 874. A desk, 1280 x 800, as the mock measured.
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
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
        elif form is not None:
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
        st, text, _ = self._req("GET", path)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_json(self, path, body, token=None):
        st, text, _ = self._req("POST", path, body=body,
                                headers={"X-Social-CSRF": self.token or "" if token is None else token})
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, form):
        st, text, headers = self._req("POST", path, form=form)
        return st, headers.get("Location")


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
    """A face for them, so a face on the page says whose it is: a drawing of
    theirs, kept unlisted, named as their face on their row."""
    sid = make_drawing(who, f"{who.handle}'s face", seed=seed, vis="unlisted")
    db_write("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = ?",
             (sid, who.handle.lower()))
    return sid


def say_on(who, post_id, words, answer_to=None):
    """A comment (or an answer) as the box sends one: its public id, or None."""
    c = who.client()
    c.get(f"/social/p/{post_id}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    st, j = c.post_json(f"/social/p/{post_id}/comments", body)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def like(who, post_id, liked=True):
    c = who.client()
    c.get(f"/social/p/{post_id}")
    return c.post_json(f"/social/p/{post_id}/like", {"liked": liked})[0]


def follow(who, handle, following=True):
    c = who.client()
    c.get(f"/social/@{handle}")
    return c.post_json(f"/social/@{handle}/follow", {"following": following})


def mute(who, handle, raw=None, token=None, origin=BASE, page=None):
    """A mute as the ⋯ sends one: (status, answer). Somebody signed out takes
    the token from a page that carries one for everybody."""
    c = who.client() if who is not None else Client()
    c.origin = origin
    c.get(page or f"/social/@{handle}")
    if not c.token:
        c.get("/social/")
    return c.post_json(f"/social/@{handle}/mute", raw if raw is not None else {}, token=token)


def unmute(who, handle, token=None, origin=BASE):
    c = who.client() if who is not None else Client()
    c.origin = origin
    c.get(f"/social/@{handle}")
    if not c.token:
        c.get("/social/")
    return c.post_json(f"/social/@{handle}/unmute", {}, token=token)


def block(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/block", {})[0]


def unblock(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/unblock", {})[0]


def mutes_of(muter=None, muted=None):
    """The rows kept: [(muter, muted)], oldest first."""
    q = ("select a.handle, b.handle from social_mutes m join social_people a on a.id = m.muter_id"
         " join social_people b on b.id = m.muted_id")
    where, args = [], []
    if muter:
        where.append("a.handle_key = ?")
        args.append(muter)
    if muted:
        where.append("b.handle_key = ?")
        args.append(muted)
    return db(q + (" where " + " and ".join(where) if where else "") + " order by m.id", tuple(args))


def follows_of(follower, followed):
    return db("select f.ended_at from social_follows f join social_people a on a.id = f.follower_id"
              " join social_people b on b.id = f.followed_id where a.handle_key = ? and b.handle_key = ?",
              (follower, followed))


def public_id(handle):
    got = db("select public_id from social_people where handle_key = ?", (handle,))
    return got[0][0] if got else None


def skribl_of(post_id):
    got = db("select skribl_id from social_posts where public_id = ?", (post_id,))
    return got[0][0] if got else None


def ready(pg):
    """The page and its deferred scripts (they have all run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


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


def open_sheet(pg, opener, sheet_id):
    press(pg, opener)
    pg.wait_for_function("(id) => { const w = document.getElementById(id); return !!w && w.classList.contains('is-open') && !w.hidden; }",
                         arg=sheet_id, timeout=8000)
    pg.wait_for_timeout(450)


def tap_mute(pg, row, path_end="/mute", after=0):
    """Tap a Mute (or Unmute) row and wait for the site's answer. A tap that
    sends nothing reads as the row's own red, never a section that stops."""
    try:
        with pg.expect_response(lambda r: r.url.endswith(path_end) and r.request.method == "POST", timeout=8000):
            press(pg, row)
    except Exception:  # noqa: BLE001
        pass
    if after:
        pg.wait_for_timeout(after)


# ---- what the page shows, read in the page ---------------------------------------
# A ⋯ sheet's rows, in order: what each says (its name and, for Mute, its
# line), whether it is Mute's, its icon (the pen's closed eye?), where its
# words start, their size and weight, its box, and whether a press lands.
ACTS = r"""(sel) => [...document.querySelectorAll(sel + ' .post-act')].filter(b => !b.hidden && b.getClientRects().length).map(b => {
  const ic = b.querySelector('svg'), w = b.querySelector('.mu-words b') || b.querySelector(':scope > span');
  const r = b.getBoundingClientRect(), wr = w.getBoundingClientRect(), cs = getComputedStyle(w), ir = ic.getBoundingClientRect();
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const sayEl = b.querySelector('.mu-say');
  const paths = [...ic.querySelectorAll('path')];
  return { name: w.textContent.trim(), say: sayEl ? sayEl.textContent.trim() : null, mute: b.classList.contains('mu-act'),
           muted: b.getAttribute('data-muted'), pen: ic.classList.contains('pen-ic'), paths: paths.length,
           unit: paths.every(p => p.getAttribute('pathLength') === '1'), d: paths.map(p => p.getAttribute('d')).join('|'),
           icon: [ir.left, ir.top, ir.width, ir.height], left: Math.round(wr.left * 100) / 100, size: cs.fontSize,
           weight: cs.fontWeight, h: Math.round(r.height * 10) / 10, hit: !!at && (at === b || b.contains(at)) }; })"""

# The closed eye's four strokes, as _icons.html draws them (the mock's).
EYE = ("M 3.4,7.8 C 6.1,11.7 9.0,13.3 12.0,13.3 C 15.1,13.3 17.9,11.6 20.6,7.6|M 6.6,11.1 L 5.0,13.5|"
       "M 12.0,13.4 L 11.9,16.4|M 17.4,11.0 L 19.0,13.4")

# The toast: shown, its words, Undo (shown, its box, and where a finger
# lands: its middle and 21px out each way), its box, the bar's top, whether
# a tap on its words reaches the page under it, and the live region's role.
TOAST = r"""() => { const t = document.querySelector('.mu-toast'); if (!t) return null;
  const box = t.closest('[data-mute-toasts]'), u = t.querySelector('.mu-undo'), w = t.querySelector('.mu-toast-words');
  const cs = getComputedStyle(t), r = t.getBoundingClientRect(), nav = document.querySelector('nav.nav');
  const ur = u.getBoundingClientRect(), wr = w.getBoundingClientRect(), cx = ur.left + ur.width / 2, cy = ur.top + ur.height / 2;
  const lands = [[cx, cy], [cx - 21, cy], [cx + 21, cy], [cx, cy - 21], [cx, cy + 21]].map(([x, y]) => {
    const e = document.elementFromPoint(x, y); return !!e && (e === u || u.contains(e)); });
  const under = document.elementFromPoint(wr.left + wr.width / 2, wr.top + wr.height / 2);
  return { shown: !t.hidden && t.classList.contains('is-up'), hidden: t.hidden, op: +cs.opacity, words: w.textContent.trim(),
           undo: !u.hidden, undoText: u.textContent.trim(), undoBox: [ur.width, ur.height], lands,
           box: [r.left, r.top, r.right, r.bottom], navTop: nav ? nav.getBoundingClientRect().top : null,
           role: box ? box.getAttribute('role') : null, through: !!under && !t.contains(under),
           vw: innerWidth, vh: innerHeight, focus: document.activeElement === u }; }"""

# Their page's line: its words, its box, Unmute's, the row of buttons'.
LINE = r"""() => { const l = document.querySelector('[data-mute-line]'); if (!l || !l.getClientRects().length) return null;
  const r = l.getBoundingClientRect(), u = l.querySelector('.mu-unmute'), ur = u.getBoundingClientRect();
  const acts = document.querySelector('.prof-acts').getBoundingClientRect(), cx = ur.left + ur.width / 2, cy = ur.top + ur.height / 2;
  // Where the line and the buttons ARE, not their boxes: each is a full-width
  // row, so its box is the same wherever its contents sit. The span of what
  // each holds (the eye to Unmute; the first button to the last).
  const span = (el) => { const k = [...el.children].filter(e => e.getClientRects().length).map(e => e.getBoundingClientRect());
    return [Math.min(...k.map(x => x.left)), Math.max(...k.map(x => x.right))]; };
  const [inL, inR] = span(l), [aL, aR] = span(document.querySelector('.prof-acts'));
  const lands = [[cx, cy], [cx - 21, cy], [cx + 21, cy], [cx, cy - 21], [cx, cy + 21]].map(([x, y]) => {
    const e = document.elementFromPoint(x, y); return !!e && (e === u || u.contains(e)); });
  const ic = l.querySelector('svg');
  return { words: l.textContent.replace(/\s+/g, ' ').trim(), unmute: u.textContent.trim(), label: u.getAttribute('aria-label'),
           top: r.top, mid: (inL + inR) / 2, left: inL, actsBottom: acts.bottom, actsLeft: aL,
           actsMid: (aL + aR) / 2, h: Math.round(ur.height), lands,
           eye: !!ic && ic.classList.contains('pen-ic') && ic.querySelectorAll('path').length === 4,
           op: +getComputedStyle(l).opacity }; }"""

# Every folded comment: its words, Show, the eye's box, where its words start,
# a shown comment's face and name beside it (the same level), whether the
# comment's own parts are hidden for real, and where a finger lands.
FOLDS = r"""() => [...document.querySelectorAll('.cm.is-quiet')].filter(li => li.getClientRects().length).map(li => {
  const f = li.querySelector(':scope > .cm-fold-line'), r = f.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const lands = [[cx, cy], [cx - 21, cy], [cx + 21, cy], [cx, cy - 21], [cx, cy + 21]].map(([x, y]) => {
    const e = document.elementFromPoint(x, y); return !!e && (e === f || f.contains(e)); });
  const sib = [...li.parentElement.children].find(x => x !== li && x.classList.contains('cm') && !x.classList.contains('is-quiet'));
  const face = sib ? sib.querySelector(':scope > .face-ring').getBoundingClientRect() : null;
  const name = sib ? sib.querySelector('.cm-name').getBoundingClientRect() : null;
  const eye = f.querySelector('svg').getBoundingClientRect(), words = f.querySelector('.cm-fold-words').getBoundingClientRect();
  const main = li.querySelector(':scope > .cm-main'), own = li.querySelector(':scope > .face-ring');
  const ctl = [...main.querySelectorAll('button, a')];
  const reach = ctl.filter(e => { const q = e.getBoundingClientRect(); if (!q.width) return false;
    const x = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); return !!x && (x === e || e.contains(x)); });
  return { id: li.id, words: f.textContent.replace(/\s+/g, ' ').trim(), show: (f.querySelector('.cm-show') || {}).textContent || null,
           h: Math.round(r.height * 10) / 10, lands, eyeMid: Math.round((eye.left + eye.width / 2) * 100) / 100,
           faceMid: face ? Math.round((face.left + face.width / 2) * 100) / 100 : null,
           wordsLeft: Math.round(words.left * 100) / 100, nameLeft: name ? Math.round(name.left * 100) / 100 : null,
           hidden: getComputedStyle(main).visibility === 'hidden' && (!own || getComputedStyle(own).visibility === 'hidden'),
           checked: typeof main.checkVisibility === 'function' ? !main.checkVisibility({ visibilityProperty: true }) : null,
           reached: reach.length, controls: ctl.length, answers: li.querySelectorAll(':scope > .cm-answers > .cm:not(.is-quiet)').length }; })"""

# Whether a comment shows whole: its words painted where they are.
SHOWN = r"""(id) => { const li = document.getElementById(id); if (!li) return null;
  const w = li.querySelector(':scope > .cm-main .cm-words'); if (!w) return { quiet: li.classList.contains('is-quiet') };
  const r = w.getBoundingClientRect(), at = document.elementFromPoint(r.left + Math.min(20, r.width / 2), r.top + r.height / 2);
  return { quiet: li.classList.contains('is-quiet'), fold: !!li.querySelector(':scope > .cm-fold-line'),
           painted: !!at && (at === w || w.contains(at)), op: +getComputedStyle(li.querySelector(':scope > .cm-main')).opacity,
           words: w.textContent.trim() }; }"""

# Home's feed, in order: each card's whose and what (p: a post's id, s: a drawing's).
FEED = r"""() => { const f = document.querySelector('[data-feed]'); if (!f) return null;
  const room = c => c.parentElement.classList.contains('mu-room') ? c.parentElement : c;
  return [...f.querySelectorAll('.post-card')].filter(c => c.getClientRects().length && room(c).getBoundingClientRect().height > 1)
    .map(c => c.getAttribute('data-handle') + ':' + (c.getAttribute('data-kind') === 's' ? 's:' + c.getAttribute('data-skribl')
                                                                                      : 'p:' + c.getAttribute('data-post'))); }"""

# Activity's rows: who and what, each section's.
ROWS = r"""() => [...document.querySelectorAll('.act-list')].map(ul => {
  const h = document.getElementById(ul.getAttribute('aria-labelledby'));
  return { sec: h ? h.textContent.trim() : null, rows: [...ul.querySelectorAll(':scope > li > a.act-row')].map(a =>
    a.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim()) }; })"""

DOT = r"""(sel) => { const a = document.querySelector(sel); if (!a || !a.getClientRects().length) return 'no bell';
  return !!a.querySelector('.act-dot'); }"""

# Settings' panels in order (their titles), and the Muted panel: its words and
# its rows (face, name, @handle, Unmute's box and where a finger lands).
SETTINGS = r"""() => { const titles = [...document.querySelectorAll('.panel .panel-title')].map(t => t.textContent.trim());
  const p = document.getElementById('mutedTitle'); const s = p ? p.closest('.panel') : null; if (!s) return { titles };
  // In view first: a finger can only reach what is on the screen (the first
  // person to join has Reports and Invites above it).
  s.scrollIntoView({ block: 'start' });
  const rows = [...s.querySelectorAll('.blocked-row')].map(li => { const b = li.querySelector('button'), r = b.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const lands = [[cx, cy], [cx - 21, cy], [cx + 21, cy], [cx, cy - 21], [cx, cy + 21]].map(([x, y]) => {
      const e = document.elementFromPoint(x, y); return !!e && (e === b || b.contains(e)); });
    return { name: li.querySelector('.blocked-who b').textContent.trim(), handle: li.querySelector('.blocked-who span').textContent.trim(),
             face: !!li.querySelector('.face-ring'), btn: b.textContent.trim(), label: b.getAttribute('aria-label'),
             h: Math.round(r.height), lands, form: b.closest('form') ? new URL(b.closest('form').action).pathname : null }; });
  const blocked = document.getElementById('blockedTitle').closest('.panel');
  return { titles, sub: s.querySelector('.panel-sub').textContent.trim(), rows,
           above: s.getBoundingClientRect().bottom <= blocked.getBoundingClientRect().top,
           blockedRows: [...blocked.querySelectorAll('.blocked-who span')].map(e => e.textContent.trim()),
           note: (document.querySelector('.note') || {}).textContent || null }; }"""


# ---- the motion, read on every frame (the mock's judge, frames spanned) ---------
# The reader sets window.__get; START records it on every animation frame for
# `ms` into window.__frames while the real tap happens.
START = r"""([ms]) => { window.__frames = []; const t0 = performance.now(), get = window.__get;
  const step = () => { const t = performance.now() - t0; window.__frames.push(Object.assign({ t: Math.round(t * 10) / 10 }, get()));
    if (t < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

TOAST_GET = r"""
  const toastOf = () => { const t = document.querySelector('.mu-toast');
    if (!t || t.hidden) return { top_op: 0, rise: null, tb: null };
    const cs = getComputedStyle(t), m = new DOMMatrixReadOnly(cs.transform), r = t.getBoundingClientRect();
    return { top_op: parseFloat(cs.opacity), rise: Math.round(m.f * 100) / 100, tb: [r.top, r.bottom] }; };
  const navTop = () => document.querySelector('nav.nav').getBoundingClientRect().top;
"""

# A card of theirs on Home (its room, once it has one), the next card under it.
CARD_GET = r"""([handle]) => {""" + TOAST_GET + r"""
  const card = document.querySelector('[data-feed] .post-card[data-handle="' + handle + '"]');
  let next = card.parentElement.classList.contains('mu-room') ? card.parentElement.nextElementSibling : card.nextElementSibling;
  while (next && !(next.classList.contains('post-card') && next.getAttribute('data-handle') !== handle)) next = next.nextElementSibling;
  window.__get = () => { const room = card.parentElement.classList.contains('mu-room') ? card.parentElement : card;
    const h = room.getBoundingClientRect().height, op = parseFloat(getComputedStyle(room).opacity);
    return Object.assign({ h: Math.round(h * 100) / 100, op, next: Math.round(next.getBoundingClientRect().top * 100) / 100,
                           nav: navTop() }, toastOf()); };
  return !!card && !!next; }"""

# Their page's line (its room, once it has one), and the Skribls heading under it.
LINE_GET = r"""() => {""" + TOAST_GET + r"""
  const head = document.getElementById('profSkribls');
  /* The line's room, or once it stands without one, the line with its margins
     (the room holds them both: a reader of the bare line reads a hop that
     isn't there). */
  const outer = e => { const cs = getComputedStyle(e);
    return e.getBoundingClientRect().height + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom); };
  window.__get = () => { const l = document.querySelector('.mu-line');
    const room = l && l.parentElement.classList.contains('mu-room') ? l.parentElement : l;
    return Object.assign({ h: room ? Math.round((room === l ? outer(l) : room.getBoundingClientRect().height) * 100) / 100 : 0,
                           op: room ? parseFloat(getComputedStyle(room).opacity) : 0,
                           next: Math.round(head.getBoundingClientRect().top * 100) / 100, nav: navTop() }, toastOf()); };
  return !!head; }"""

# A folded comment, Show: its height, the fold line's opacity, the comment's,
# and the next comment under it.
SHOW_GET = r"""([id]) => {
  const li = document.getElementById(id), next = li.nextElementSibling, main = li.querySelector(':scope > .cm-main');
  window.__get = () => { const f = li.querySelector(':scope > .cm-fold-line');
    return { h: Math.round(li.getBoundingClientRect().height * 100) / 100, fold: f ? parseFloat(getComputedStyle(f).opacity) : 0,
             op: parseFloat(getComputedStyle(main).opacity), next: Math.round(next.getBoundingClientRect().top * 100) / 100 }; };
  return !!next; }"""

FRAME_MS = 1000 / 60


_recorded = [0]


def record(pg, getter, args, ms, act):
    """Every animation frame for `ms` while `act` (the real tap) happens.
    SOCIALMUTE_FRAMES=<dir> keeps each recording there, as JSON, to look at."""
    ok = pg.evaluate(getter, args) if args is not None else pg.evaluate(getter)
    pg.evaluate(START, [ms])
    act()
    pg.wait_for_timeout(ms + 250)
    frames = (pg.evaluate("() => window.__frames") or []) if ok else []
    keep_in = os.environ.get("SOCIALMUTE_FRAMES")
    if keep_in:
        _recorded[0] += 1
        Path(keep_in).mkdir(parents=True, exist_ok=True)
        (Path(keep_in) / f"rec{_recorded[0]:02d}.json").write_text(json.dumps(frames))
    return frames


def steps(vals, ts):
    """The biggest share of the whole change in one display frame (a frame the
    browser dropped is the frames it spans, so a busy machine is not read as a
    jump), and on how many frames it changed."""
    pairs = [(v, t) for v, t in zip(vals, ts) if v is not None]
    if len(pairs) < 2:
        return 0.0, 0
    v0, total = pairs[0][0], pairs[-1][0] - pairs[0][0]
    if abs(total) < 1e-9:
        return 0.0, 0
    prog = [((v - v0) / total, t) for v, t in pairs]
    big = max(abs(b - a) / max(1.0, round((tb - ta) / FRAME_MS)) for (a, ta), (b, tb) in zip(prog, prog[1:]))
    moving = sum(1 for (a, _), (b, _) in zip(prog, prog[1:]) if abs(b - a) > 0.005)
    return round(big, 3), moving


def back(vals):
    """How far a thing that should only go one way ever went back, in px."""
    vals = [v for v in vals if v is not None]
    if len(vals) < 2 or abs(vals[-1] - vals[0]) < 1e-9:
        return 0
    sign = 1 if vals[-1] > vals[0] else -1
    return round(max([0] + [-(b - a) * sign for a, b in zip(vals, vals[1:])]), 2)


def hop(vals, rest=0.05, step=1.0):
    """A HOP AFTER A STOP: once a thing has started to move, rested for two
    frames or more, then moved again by more than a pixel in one frame (the
    mock's first line hopped its 8px margin after gliding: 15% of its way, so
    the per-frame rule alone let it through)."""
    vals = [v for v in vals if v is not None]
    started, still, worst = False, 0, 0.0
    for a, b in zip(vals, vals[1:]):
        d = abs(b - a)
        if d > rest:
            if started and still >= 2 and d > step:
                worst = max(worst, d)
            started, still = True, 0
        elif started:
            still += 1
    return round(worst, 2)


def unseen_at_jump(fr):
    """Under Reduce Motion a room is put there: how much of what it holds could
    be seen the frame it changed (None: it never changed)."""
    for a, b in zip(fr, fr[1:]):
        if abs(b["h"] - a["h"]) > 1:
            return min(a["op"], b["op"])
    return None


def judge_room(fr, reduced, need=8):
    """A room that opens or closes: normally its height no more than 30% of the
    way a frame over `need` frames or more, its fade no more than 35%, the next
    thing no more than 30% and never going back, no hop; under Reduce Motion
    the room put there only while what it holds can't be seen (0.05), the
    fade still no more than 35%."""
    ts = [f["t"] for f in fr]
    h_big, h_frames = steps([f["h"] for f in fr], ts)
    op_big, op_frames = steps([f["op"] for f in fr], ts)
    n_big, _ = steps([f["next"] for f in fr], ts)
    n_back = back([f["next"] for f in fr])
    h_hop = max(hop([f["h"] for f in fr]), hop([f["next"] for f in fr]))
    out = {"frames": len(fr), "room": [h_big, h_frames], "fade": [op_big, op_frames], "next": [n_big, n_back],
           "hop": h_hop, "moved": round(abs(fr[-1]["h"] - fr[0]["h"]), 1) if fr else 0}
    if reduced:
        seen = unseen_at_jump(fr)
        out["seen_when_put"] = seen
        ok = op_big <= 0.35 and op_frames >= 2 and seen is not None and seen <= 0.05 and n_back <= 0.5 and h_hop == 0
    else:
        ok = (h_big <= 0.30 and h_frames >= need and op_big <= 0.35 and op_frames >= 4 and n_big <= 0.30
              and n_back <= 0.5 and h_hop == 0)
    ok = ok and out["moved"] > 10
    out["ok"] = ok
    return out


def judge_toast(fr, reduced):
    """The toast: it fades in (no frame more than 35%, five frames or more) and,
    but under Reduce Motion, rises (no more than 35%, six frames or more, no
    hop); it never touches the bar, and ends up."""
    ts = [f["t"] for f in fr]
    op_big, op_frames = steps([f["top_op"] for f in fr], ts)
    rise = [(f["rise"], f["t"]) for f in fr if f["rise"] is not None]
    r_big, r_frames = steps([r for r, _ in rise], [t for _, t in rise])
    moved = round(max(r for r, _ in rise) - min(r for r, _ in rise), 2) if rise else 0
    over = any(f["tb"] and f["tb"][1] > f["nav"] for f in fr)
    out = {"fade": [op_big, op_frames], "rise": [r_big, r_frames], "moved": moved, "hop": hop([r for r, _ in rise]),
           "on_bar": over, "ends": fr[-1]["top_op"] if fr else None}
    if reduced:
        ok = moved == 0 and op_big <= 0.35 and op_frames >= 5 and not over and (out["ends"] or 0) >= 0.99
    else:
        ok = (op_big <= 0.35 and op_frames >= 5 and r_big <= 0.35 and r_frames >= 6 and out["hop"] == 0 and not over
              and (out["ends"] or 0) >= 0.99 and moved >= 9)
    out["ok"] = ok
    return out


def judge_show(fr, reduced):
    """Show: the room as judge_room; the fold line fades (no frame more than
    35%), and the line and the comment are never both more than half there."""
    out = judge_room(fr, reduced)
    fold_big, _ = steps([f["fold"] for f in fr], [f["t"] for f in fr])
    both = any(f["fold"] > 0.5 and f["op"] > 0.5 for f in fr)
    out.update({"fold": fold_big, "both": both})
    out["ok"] = out["ok"] and fold_big <= 0.35 and not both
    return out


# ---- the words and marks, read two ways ------------------------------------------
# Each new word and mark: its colour against the ground painted behind it,
# its layers composited; colours parsed as rgb(), rgba() and color(srgb ...)
# (0 to 1), and ANY OTHER FORM FAILS CLOSED (the likes piece found a reader
# that took the player's lilac, a color(srgb ...), for grey). A mark is its
# stroke; its box its whole icon. A sheet that is up hides the page under its
# scrim: only its own parts are read.
NEWREAD = r"""(sels) => {
  const parse = s => {
    s = (s || '').trim();
    let m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const v = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return v.length >= 3 ? [v[0], v[1], v[2], v.length > 3 ? v[3] : 1] : null; }
    m = s.match(/^color\(srgb\s+([^)]+)\)$/);
    if (m) { const v = m[1].split(/[\s\/]+/).filter(Boolean).map(Number); return v.length >= 3 ? [v[0] * 255, v[1] * 255, v[2] * 255, v.length > 3 ? v[3] : 1] : null; }
    if (s === 'transparent') return [0, 0, 0, 0];
    throw new Error('colour in a form this reader does not read: ' + s);
  };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => c[3] >= 1 ? c.slice(0, 3) : [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const ground = e => { const layers = [];
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const b = parse(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = parse(getComputedStyle(document.body).backgroundColor).slice(0, 3);
    for (let i = layers.length - 1; i >= 0; i--) g = over(layers[i], g);
    return g; };
  const out = [], open = document.querySelector('.make.is-open .make-sheet');
  for (const [sel, kind, what] of sels) {
    document.querySelectorAll(sel).forEach(e => {
      if (!e.getClientRects().length) return;
      if (open && !open.contains(e)) return;
      const r = (kind === 'mark' && e.ownerSVGElement ? e.ownerSVGElement : e).getBoundingClientRect();
      if (r.bottom < 0 || r.top > innerHeight || r.width < 1) return;
      let op = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) op *= parseFloat(getComputedStyle(n).opacity);
      if (op < 0.5) return;
      const cs = getComputedStyle(e), paint = kind === 'mark' ? (cs.stroke && cs.stroke !== 'none' ? cs.stroke : cs.fill) : cs.color;
      try {
        const g = ground(e), k = ratio(over(parse(paint), g), g);
        out.push({ what, kind, text: (e.textContent || '').trim().slice(0, 40), k: Math.round(k * 100) / 100,
                   box: [r.left, r.top, r.width, r.height] });
      } catch (err) { out.push({ what, kind, k: 0, unread: String(err.message || err), box: [r.left, r.top, r.width, r.height] }); }
    });
  }
  return out; }"""


def _lum(c):
    v = []
    for x in c[:3]:
        x /= 255
        v.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def _ratio(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def _pixels(im):
    """Every pixel, as Pillow now names it (getdata is going in Pillow 14)."""
    return im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()


def painted(im, box, dsf=1):
    """The box cut from the screenshot: the ground is its most common colour,
    the ink the pixel farthest from it (by contrast)."""
    x, y, w, h = box
    crop = im.crop((max(0, int(x * dsf)), max(0, int(y * dsf)), min(im.width, int((x + w) * dsf + 0.999)),
                    min(im.height, int((y + h) * dsf + 0.999))))
    px = list(_pixels(crop))
    if not px:
        return None
    g = Counter(px).most_common(1)[0][0]
    best = max(px, key=lambda p: _ratio(p, g))
    return round(_ratio(best, g), 2)


def read_new(pg, sels):
    """Each new word and mark on the screen, read two ways (its colour on its
    ground, and the pixels), the lower counting: [{what, kind, k, painted, low}]."""
    rows = pg.evaluate(NEWREAD, sels)
    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    for r in rows:
        p = painted(im, r["box"]) if not r.get("unread") else None
        r["painted"] = p
        r["low"] = min(r["k"], p) if p is not None else r["k"]
        r["need"] = 3.0 if r["kind"] == "mark" else 4.5
        r.pop("box", None)
    return rows


def ink_mid(pg, box):
    """The middle of what is painted in `box`, across, from the pixels (each
    pixel weighed by how far it is from the box's ground)."""
    im = Image.open(io.BytesIO(pg.screenshot(clip={"x": box[0], "y": box[1], "width": box[2], "height": box[3]},
                                             scale="css"))).convert("RGB")
    g = Counter(_pixels(im)).most_common(1)[0][0]
    xs = wsum = 0.0
    px = im.load()
    for j in range(im.height):
        for i in range(im.width):
            d = sum(abs(a - b) for a, b in zip(px[i, j], g)) / 765
            if d > 0.08:
                xs += (i + 0.5) * d
                wsum += d
    return round(box[0] + xs / wsum * box[2] / im.width, 2) if wsum else None


# Every word painted in `sel` (the page's roots by default) against what is
# painted behind it, every target and every text field (verify_sociallikes'
# census, the follow suite's band rule for a pill's option).
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
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99 };
  const roots = [...document.querySelectorAll(sel || 'main, header.top, nav.nav, .mu-toasts')];
  roots.forEach(root => root.querySelectorAll('*').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, template, ' + SKRIBLS)) return;
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
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 30) + '" ' + k.toFixed(2));
  }));
  document.querySelectorAll('a[href], button, input, textarea, select, [role=button]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, template, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    if (e.matches('input[type=radio]')) return;
    if (getComputedStyle(e).visibility === 'hidden') return;
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

# What each new word and mark is, by where it sits.
NEW_ROW = [[".mu-act .mu-words b", "word", "the row's name"], [".mu-act .mu-say", "word", "the row's line"],
           [".mu-act svg path", "mark", "the row's eye"]]
NEW_TOAST = [[".mu-toast .mu-toast-words", "word", "the toast's words"], [".mu-toast .mu-undo", "word", "the toast's Undo"],
             [".mu-toast svg path", "mark", "the toast's eye"]]
NEW_LINE = [[".mu-line .mu-line-words", "word", "the line's words"], [".mu-line .mu-dot", "word", "the line's dot"],
            [".mu-line .mu-unmute", "word", "the line's Unmute"], [".mu-line svg path", "mark", "the line's eye"]]
NEW_FOLD = [[".cm-fold-words", "word", "the fold's words"], [".cm-show", "word", "the fold's Show"],
            [".cm-fold-line svg path", "mark", "the fold's eye"]]
NEW_SET = [["#mutedTitle", "word", "Muted's title"], ["[aria-labelledby=mutedTitle] .panel-sub", "word", "Muted's line"],
           [".mu-list .blocked-who b", "word", "a muted name"], [".mu-list .blocked-who span", "word", "a muted @handle"],
           [".mu-list .btn", "word", "Settings' Unmute"]]

LIGHT_PAGE, DARK_PAGE = "rgb(251, 252, 253)", "rgb(11, 13, 18)"


def thanks(name):
    return f"{name} is muted. They aren’t told."


# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then goes
# because the code said so. And the reads, as the code sends them, planned by
# SQLite; and Home, read twice with ten more cards on it.
PROBE = r"""
import json, sys
from datetime import datetime, timezone
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Mute, Person, Post, new_public_id
    from social.accounts import delete_person
    from social import mutes as M
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    stranger = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[3])).scalar_one()
    out = {"fk": fk}
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if "social_mutes" in statement and statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        rec.clear()
        M.muted_ids(who)
        M.muted_authors(who.public_id)
        calls["ids"] = list(rec)
        out["same_read"] = len(rec) == 1
    with app.test_request_context("/social/"):
        rec.clear()
        M.muted_people(who)
        calls["people"] = list(rec)
    event.remove(db.engine, "before_cursor_execute", keep)
    plan = lambda st, params: [r[3] for r in db.session.connection().exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
    out["plans"] = {name: [x for st, params in sent for x in plan(st, params)] for name, sent in calls.items()}
    def home():
        # A request of its own, in an app context of its own: a request inside
        # this probe's would share its `g`, and every once-a-request read would
        # be found already made.
        seen = []
        def count(conn, cursor, statement, params, context, executemany):
            seen.append(statement)
        engine = db.engine
        event.listen(engine, "before_cursor_execute", count)
        with app.app_context():
            page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": sys.argv[2], "X-Forwarded-For": "10.250.1.1"})
        event.remove(engine, "before_cursor_execute", count)
        html = page.get_data(as_text=True)
        return {"status": page.status_code, "reads": len(seen), "mutes": sum(1 for s in seen if "social_mutes" in s),
                "cards": html.count('class="post-card"'), "xan": 'data-handle="xan"' in html}
    # On this copy, only Xan's and Yul's: everybody else's posts gone and drawings
    # put out of the listing, so the cards below are the ones this probe makes
    # (in a full run Home's first page is already full).
    keep_ids = [r[0] for r in db.session.execute(sa.select(Person.id).where(Person.handle_key.in_(["xan", "yul"])))]
    pubs = [r[0] for r in db.session.execute(sa.select(Person.public_id).where(Person.id.in_(keep_ids)))]
    db.session.execute(sa.delete(Post).where(Post.person_id.notin_(keep_ids)))
    db.session.execute(sa.text("update skribl_posts set visibility = 'unlisted' where user_id not in ("
                               + ", ".join(f"'{x}'" for x in pubs) + ")"))
    db.session.commit()
    home()                  # the process's first request does its one-time work
    out["home1"] = home()
    now = datetime.now(timezone.utc)
    for i in range(10):
        db.session.add(Post(public_id=new_public_id(8), person_id=stranger.id, words=f"probe {i}", skribl_id=f"probe{i}",
                            created_at=now))
    db.session.commit()
    out["home2"] = home()
    both = lambda: db.session.execute(sa.select(sa.func.count()).select_from(Mute).where(
        sa.or_(Mute.muter_id == who.id, Mute.muted_id == who.id))).scalar()
    before = both()
    delete_person(db.session, who.id)
    db.session.commit()
    out["deleted"] = [before, both()]
    print(json.dumps(out))
"""


with sync_playwright() as p:
    b = p.chromium.launch()
    # ------------------------------------------------------------------ 1
    if part(1, "where you mute: first on their page, after Share… on their post and drawing; the eye; never yours or signed out"):
        try:
            ann = someone(b, "ann", "Ann Lake")
            ben = someone(b, "ben", "Ben Lind")
            bp = make_post(ben, "Section 1, Ben's")
            bs = make_drawing(ben, "Section 1, Ben's drawing", seed=3)
            ap = make_post(ann, "Section 1, Ann's")
            SAY = "Their posts, comments and likes stop reaching you. They aren’t told."
            rows, inks = {}, {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, ann, screen=screen)
                go(pg, "/social/@ben")
                open_sheet(pg, "[data-person-menu]", "personSheet")
                rows[(screen, "person")] = pg.evaluate(ACTS, "#personSheet")
                go(pg, "/social/", wait=500)
                for kind, key in (("card", f'[data-post="{bp}"]'), ("drawing", f'[data-skribl="{bs}"][data-kind="s"]')):
                    to(pg, f".post-card{key}", 120)
                    open_sheet(pg, f".post-card{key} [data-post-menu]", "postSheet")
                    rows[(screen, kind)] = pg.evaluate(ACTS, "#postSheet")
                    if kind == "card":
                        inks[screen] = {r["name"]: ink_mid(pg, r["icon"]) for r in rows[(screen, kind)]}
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(500)
                go(pg, f"/social/p/{bp}")
                open_sheet(pg, ".top .post-more" if screen == "phone" else ".post-head .post-more", "postSheet")
                rows[(screen, "page")] = pg.evaluate(ACTS, "#postSheet")
                close_ctx(ctx, pg)
            names = {k: [r["name"] for r in v] for k, v in rows.items()}
            check("on somebody's page, signed in, the ⋯ says Mute @ben first, the gentlest, its line under it (“Their"
                  " posts, comments and likes stop reaching you. They aren’t told.”), then Report @ben and Block @ben,"
                  " on a phone and on a desk",
                  all(names[(s, "person")] == ["Mute @ben", "Report @ben", "Block @ben"]
                      and rows[(s, "person")][0]["say"] == SAY and rows[(s, "person")][0]["muted"] == "false"
                      for s in ("phone", "desk")),
                  json.dumps({s: names[(s, "person")] for s in ("phone", "desk")}))
            want = ["Copy link", "Share…", "Mute @ben", "Report this post", "Block @ben"]
            check("on their post's ⋯ (its card on Home and its own page) and their drawing's, Mute @ben comes after Copy"
                  " link and Share…, before Report and Block, so the two danger rows stay together, with its line",
                  all(names[(s, k)] == want and rows[(s, k)][2]["say"] == SAY
                      for s in ("phone", "desk") for k in ("card", "drawing", "page")),
                  json.dumps({f"{s} {k}": names[(s, k)] for s in ("phone", "desk") for k in ("card", "drawing", "page")}))
            eyes = [r for v in rows.values() for r in v if r["mute"]]
            check("its icon is a closed eye in our pen (the lid and three lashes, each one unit long), never a speaker",
                  len(eyes) == 8 and all(r["pen"] and r["paths"] == 4 and r["unit"] and r["d"] == EYE for r in eyes),
                  json.dumps([(r["pen"], r["paths"], r["unit"], r["d"][:40]) for r in eyes[:2]]))
            lined = []
            for (s, k), v in rows.items():
                m = next((r for r in v if r["mute"]), None)
                rep = next((r for r in v if r["name"].startswith("Report")), None)
                lefts = {round(r["left"], 1) for r in v}
                lined.append((s, k, m and m["size"], m and m["weight"], rep and (rep["size"], rep["weight"]),
                              len(lefts), m and m["h"], m and m["hit"]))
            ok_lines = all(sz == "17px" and wt == "600" and rp == ("17px", "600") and n == 1 and h >= 56 and hit
                           for _, _, sz, wt, rp, n, h, hit in lined)
            eye_ok = all(i.get("Mute @ben") is not None and all(abs(i["Mute @ben"] - i[n]) <= 0.5
                                                               for n in ("Copy link", "Share…", "Block @ben"))
                         for i in inks.values())
            check("its words the size and weight of Report's and Block's (17px, 600), every row's words starting on the"
                  " same pixel, the row 56px tall and painted where it stands; its eye's painted ink centred on Copy"
                  " link's, Share's and Block's icons (within 0.5px), on a phone and a desk",
                  ok_lines and eye_ok, f"{lined[:2]}; ink middles {json.dumps(inks)}")
            mute(ann, "ben")
            ctx, pg = browser_as(b, ann)
            go(pg, "/social/@ben")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            mp = pg.evaluate(ACTS, "#personSheet")
            go(pg, f"/social/p/{bp}")
            open_sheet(pg, ".top .post-more", "postSheet")
            mq = pg.evaluate(ACTS, "#postSheet")
            close_ctx(ctx, pg)
            unmute(ann, "ben")
            UN = "Everything comes back, just as it was."
            check("muted, their page's ⋯ and their post's say Unmute @ben, “Everything comes back, just as it was.”",
                  mp and mp[0]["name"] == "Unmute @ben" and mp[0]["say"] == UN and mp[0]["muted"] == "true"
                  and len(mq) == 5 and mq[2]["name"] == "Unmute @ben" and mq[2]["say"] == UN,
                  json.dumps([(r["name"], r["say"]) for r in (mp or [])[:1] + (mq or [])[2:3]]))
            ctx, pg = browser_as(b, ann)
            go(pg, "/social/", wait=500)
            to(pg, f'.post-card[data-post="{ap}"]', 120)
            open_sheet(pg, f'.post-card[data-post="{ap}"] [data-post-menu]', "postSheet")
            own_card = [r["name"] for r in pg.evaluate(ACTS, "#postSheet")]
            go(pg, "/social/@ann")
            own_page = pg.evaluate("() => ({ more: !!document.querySelector('[data-person-menu]'), rows: document.querySelectorAll('.mu-act').length })")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, None)
            go(pg, "/social/@ben")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            out_person = [r["name"] for r in pg.evaluate(ACTS, "#personSheet")]
            go(pg, f"/social/p/{bp}")
            open_sheet(pg, ".top .post-more", "postSheet")
            out_post = [r["name"] for r in pg.evaluate(ACTS, "#postSheet")]
            close_ctx(ctx, pg)
            check("never on your own post (Copy link, Share…, Delete post) nor your own page (no ⋯ at all); never"
                  " signed out (a person's ⋯ says Report @ben alone, a post's Copy link, Share…, Report this post)",
                  own_card == ["Copy link", "Share…", "Delete post"] and not own_page["more"] and own_page["rows"] == 0
                  and out_person == ["Report @ben"] and out_post == ["Copy link", "Share…", "Report this post"],
                  f"own card {own_card}; own page {own_page}; signed out {out_person} / {out_post}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "nothing asked first: the tap mutes; the toast, its words and its place; seven seconds; Undo"):
        try:
            cal = someone(b, "cal", "Cal Moss")
            dan = someone(b, "dan", "Dan Ruiz")
            eve = someone(b, "eve", "Eve Park")
            make_post(eve, "Section 2, Eve's")
            d1 = make_post(dan, "Section 2, Dan's first")
            d2 = make_post(dan, "Section 2, Dan's second")
            ctx, pg = browser_as(b, cal)
            go(pg, "/social/", wait=500)
            before = pg.evaluate(FEED)
            to(pg, f'.post-card[data-post="{d2}"]', 120)
            open_sheet(pg, f'.post-card[data-post="{d2}"] [data-post-menu]', "postSheet")
            tap_mute(pg, "#postSheet [data-act=mute]")
            pg.wait_for_function("() => { const t = document.querySelector('.mu-toast'); return t && t.classList.contains('is-up'); }",
                                 timeout=8000)
            t_up = time.time()
            pg.wait_for_timeout(1000)
            st = pg.evaluate(TOAST)
            kept = mutes_of("cal", "dan")
            asked = pg.evaluate("() => [...document.querySelectorAll('.make.is-open')].map(w => w.id)")
            after = pg.evaluate(FEED)
            check("a tap on Mute @dan mutes at once: kept by the site (one row), nothing asked (no sheet rises), and every"
                  " card of Dan's leaves Home, everybody else's where it was",
                  kept == [("cal", "dan")] and asked == [] and not any(c.startswith("dan:") for c in after)
                  and any(c.startswith("dan:") for c in before) and after == [c for c in before if not c.startswith("dan:")],
                  f"kept {kept}; sheets {asked}; dan's before {sum(c.startswith('dan:') for c in before)}, after"
                  f" {sum(c.startswith('dan:') for c in after)}")
            check("the toast rises: “Dan is muted. They aren’t told.” and Undo, in a status a screen reader hears",
                  st and st["shown"] and st["words"] == thanks("Dan") and st["undo"] and st["undoText"] == "Undo"
                  and st["role"] == "status",
                  json.dumps(st and {k: st[k] for k in ("shown", "words", "undo", "role")}))
            check("on a phone it sits 12px above the bar, never on it, 16px in from each side",
                  st and st["navTop"] is not None and abs((st["navTop"] - st["box"][3]) - 12) <= 0.5
                  and abs(st["box"][0] - 16) <= 0.5 and abs(st["box"][2] - (st["vw"] - 16)) <= 0.5,
                  json.dumps(st and {"box": st["box"], "bar": st["navTop"]}))
            check("only Undo takes a tap: a tap on its words reaches the page under it; Undo is 44px tall, and a press at"
                  " its middle and 21px out each way lands on it",
                  st and st["through"] and st["undoBox"][1] >= 44 and all(st["lands"]),
                  json.dumps(st and {k: st[k] for k in ("through", "undoBox", "lands")}))
            pg.wait_for_timeout(max(0, int((t_up + 6.5 - time.time()) * 1000)))
            at65 = pg.evaluate(TOAST)
            pg.wait_for_timeout(max(0, int((t_up + 7.9 - time.time()) * 1000)))
            at79 = pg.evaluate(TOAST)
            check("it stays seven seconds, the Pad's own time for an Undo (still up at 6.5s), then goes (gone by 7.9s)",
                  at65 and at65["shown"] and at79 and at79["hidden"],
                  f"6.5s {at65 and at65['shown']}; 7.9s hidden {at79 and at79['hidden']}")
            close_ctx(ctx, pg)
            unmute(cal, "dan")
            ctx, pg = browser_as(b, cal)
            go(pg, "/social/", wait=500)
            to(pg, f'.post-card[data-post="{d2}"]', 120)
            opener = f'.post-card[data-post="{d2}"] [data-post-menu]'
            open_sheet(pg, opener, "postSheet")
            tap_mute(pg, "#postSheet [data-act=mute]")
            pg.wait_for_function("() => { const t = document.querySelector('.mu-toast'); return t && t.classList.contains('is-up'); }",
                                 timeout=8000)
            pg.wait_for_timeout(400)
            tap_mute(pg, "[data-mute-undo]", path_end="/unmute", after=1300)
            st2 = pg.evaluate(TOAST)
            back_feed = pg.evaluate(FEED)
            focus = pg.evaluate("(s) => document.activeElement === document.querySelector(s)", opener)
            rooms = pg.evaluate("() => document.querySelectorAll('.mu-room').length")
            close_ctx(ctx, pg)
            check("Undo unmutes (nothing kept), brings every card of Dan's back where it was, says “Unmuted. Dan’s posts"
                  " are back.” with no Undo, and gives the ⋯ the mute began from its focus back",
                  mutes_of("cal", "dan") == [] and back_feed == before and rooms == 0 and st2
                  and st2["words"] == "Unmuted. Dan’s posts are back." and not st2["undo"] and focus,
                  f"kept {mutes_of('cal', 'dan')}; feed back {back_feed == before} (rooms {rooms});"
                  f" toast {st2 and (st2['words'], st2['undo'])}; focus {focus}")
            ctx, pg = browser_as(b, cal, screen="desk")
            go(pg, "/social/", wait=500)
            to(pg, f'.post-card[data-post="{d1}"]', 160)
            open_sheet(pg, f'.post-card[data-post="{d1}"] [data-post-menu]', "postSheet")
            tap_mute(pg, "#postSheet [data-act=mute]", after=1300)
            sd = pg.evaluate(TOAST)
            close_ctx(ctx, pg)
            unmute(cal, "dan")
            mid = sd and (sd["box"][0] + sd["box"][2]) / 2
            check("on a desk it sits at the foot of the page (28px up), in the middle of the column and clear of the rail;"
                  " its words let a tap through, Undo takes one",
                  sd and sd["shown"] and abs((sd["vh"] - sd["box"][3]) - 28) <= 0.5
                  and abs(mid - (248 + sd["vw"]) / 2) <= 1 and sd["box"][0] >= 248 + 16 and sd["through"] and all(sd["lands"]),
                  json.dumps(sd and {"box": sd["box"], "mid": mid, "column": (248 + sd["vw"]) / 2, "through": sd["through"]}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "kind, never jumpy, on Home: a card folds away and comes back with Undo, read on every frame"):
        try:
            fay = someone(b, "fay", "Fay Ito")
            gil = someone(b, "gil", "Gil Ruiz")
            hal = someone(b, "hal", "Hal Ames")
            # Hal's posts sit under Gil's, so the page goes on past the card, as
            # a Home does: on a page that ends under the card the browser holds
            # its bottom in place, and the posts above glide down instead.
            for i in range(3):
                make_post(hal, f"Section 3, Hal's {i}", seed=i)
            gp = make_post(gil, "Section 3, Gil's")
            got = {}
            for tag, scheme, reduced in (("light", "light", False), ("dark", "dark", False), ("reduced", "light", True)):
                unmute(fay, "gil")
                ctx, pg = browser_as(b, fay, scheme=scheme, reduced=reduced)
                go(pg, "/social/", wait=600)
                to(pg, f'.post-card[data-post="{gp}"]', 120)
                open_sheet(pg, f'.post-card[data-post="{gp}"] [data-post-menu]', "postSheet")
                fr = record(pg, CARD_GET, ["gil"], 1300, lambda: press(pg, "#postSheet [data-act=mute]"))
                got[(tag, "fold")] = judge_room(fr, reduced)
                got[(tag, "toast")] = judge_toast(fr, reduced)
                pg.wait_for_timeout(300)
                fr2 = record(pg, CARD_GET, ["gil"], 1100, lambda: press(pg, "[data-mute-undo]"))
                got[(tag, "undo")] = judge_room(fr2, reduced)
                close_ctx(ctx, pg)
            unmute(fay, "gil")
            check("muting from a card, every frame from the tap: it fades (no frame more than 35%), then its room closes"
                  " (no frame more than 30% of the way, eight frames or more) and the next post rises into its place,"
                  " never going back, nothing hopping; light and dark",
                  got[("light", "fold")]["ok"] and got[("dark", "fold")]["ok"],
                  json.dumps({k: got[(k, "fold")] for k in ("light", "dark")}))
            check("the toast fades in and rises (no frame more than 35% of either, over five and six frames or more),"
                  " never touching the bar; light and dark",
                  got[("light", "toast")]["ok"] and got[("dark", "toast")]["ok"],
                  json.dumps({k: got[(k, "toast")] for k in ("light", "dark")}))
            check("Undo brings it back the same way: its room opens (no frame more than 30%, eight frames or more), then"
                  " it fades in, the next post moving down without going back; light and dark",
                  got[("light", "undo")]["ok"] and got[("dark", "undo")]["ok"],
                  json.dumps({k: got[(k, "undo")] for k in ("light", "dark")}))
            check("under Reduce Motion nothing glides: the card fades and its room is put away only once it can't be"
                  " seen (0.05), the next post never going back; the toast only fades (0px moved); Undo puts the room"
                  " there while it can't be seen, then fades it in",
                  got[("reduced", "fold")]["ok"] and got[("reduced", "toast")]["ok"] and got[("reduced", "undo")]["ok"],
                  json.dumps({k: got[("reduced", k)] for k in ("fold", "toast", "undo")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "their page: “You muted Jay · Unmute”, yours alone, read on every frame; their ⋯ says Unmute; what you go to stays"):
        try:
            ida = someone(b, "ida", "Ida Cole")
            jay = someone(b, "jay", "Jay Dale")
            kip = someone(b, "kip", "Kip Fox")
            jp1 = make_post(jay, "Section 4, Jay's first")
            jp2 = make_post(jay, "Section 4, Jay's second")
            js = make_drawing(jay, "Section 4, Jay's drawing", seed=5)
            tok = re.compile(r'(content|value)="[A-Za-z0-9_\-]{20,}"')
            jay_c, kip_c = jay.client(), kip.client()

            def theirs():
                return [tok.sub("", jay_c.get(p)[1]) for p in ("/social/@jay", "/social/", "/social/activity")] + \
                       [tok.sub("", kip_c.get("/social/@jay")[1])]
            seen_before = theirs()
            ctx, pg = browser_as(b, ida)
            go(pg, "/social/@jay")
            more = pg.evaluate("() => { const r = document.querySelector('[data-person-menu]').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            fr = record(pg, LINE_GET, None, 1300, lambda: press(pg, "#personSheet [data-safety=mute]"))
            room, tst = judge_room(fr, False), judge_toast(fr, False)
            line = pg.evaluate(LINE)
            st = pg.evaluate(TOAST)
            clear = st and not (st["box"][0] < more[2] and st["box"][2] > more[0] and st["box"][1] < more[3] and st["box"][3] > more[1])
            seen_after = theirs()
            check("muting from their page: the sheet goes down and the line opens under the buttons, “You muted Jay ·"
                  " Unmute”, the eye in our pen, Unmute 44px to a finger; the toast rises clear of the ⋯",
                  mutes_of("ida", "jay") == [("ida", "jay")] and line and line["words"] == "You muted Jay · Unmute"
                  and line["top"] >= line["actsBottom"] and abs(line["mid"] - line["actsMid"]) <= 1 and line["eye"]
                  and line["h"] >= 44 and all(line["lands"]) and line["label"] == "Unmute @jay" and clear
                  and st["words"] == thanks("Jay"),
                  json.dumps({"line": line, "toast": st and st["box"], "more": more}))
            check("the line's room opens on every frame (no frame more than 30% of the way, eight frames or more), then it"
                  " fades in (no frame more than 35%), the Skribls heading moving down without going back, nothing"
                  " hopping; the toast as on Home",
                  room["ok"] and tst["ok"], json.dumps({"room": room, "toast": tst}))
            check("nothing changes on their side, and nobody is told: Jay's own page, his Home and his Activity, and Kip's"
                  " view of Jay's page, are the same before the mute and after it",
                  seen_before == seen_after and "You muted" not in seen_after[0],
                  f"same: {[x == y for x, y in zip(seen_before, seen_after)]}")
            go(pg, "/social/@jay", wait=1200)
            line2 = pg.evaluate(LINE)
            listed = pg.evaluate("(id) => !!document.querySelector('#skriblGallery [data-id=\"' + id + '\"]')", js)
            open_sheet(pg, "[data-person-menu]", "personSheet")
            acts = pg.evaluate(ACTS, "#personSheet")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            c = ida.client()
            pages = {p: c.get(p)[0] for p in (f"/social/p/{jp1}", f"/social/b/{js}", f"/s/{js}")}
            more_from = jp2 in c.get(f"/social/p/{jp1}")[1]
            payload = c.get_json(f"/api/skribls/{js}")[0]
            check("loaded muted, their page says so and their ⋯ says Unmute @jay first; what you go to stays: Jay's"
                  " drawing in his page's Skribls, his post's page with More from his other post, his drawing's page,"
                  " its link page and its payload",
                  line2 and line2["words"] == "You muted Jay · Unmute" and acts and acts[0]["name"] == "Unmute @jay"
                  and listed and all(v == 200 for v in pages.values()) and more_from and payload == 200,
                  f"line {line2 and line2['words']}; row {acts and acts[0]['name']}; listed {listed}; pages {pages};"
                  f" more from {more_from}; payload {payload}")
            fr3 = record(pg, LINE_GET, None, 1100, lambda: press(pg, "[data-mute-unmute]"))
            shut = judge_room(fr3, False)
            gone = pg.evaluate("() => !document.querySelector('[data-mute-line]') && !document.querySelector('.mu-room')")
            st3 = pg.evaluate(TOAST)
            open_sheet(pg, "[data-person-menu]", "personSheet")
            acts3 = pg.evaluate(ACTS, "#personSheet")
            close_ctx(ctx, pg)
            check("Unmute on the line unmutes (nothing kept): the line fades, then its room closes (no frame more than 30%"
                  " of the way), the heading moving up without going back; the toast says “Unmuted. Jay’s posts are"
                  " back.”, and the ⋯ says Mute @jay again",
                  mutes_of("ida", "jay") == [] and shut["ok"] and gone and st3 and st3["words"] == "Unmuted. Jay’s posts are back."
                  and acts3 and acts3[0]["name"] == "Mute @jay",
                  json.dumps({"shut": shut, "gone": gone, "toast": st3 and st3["words"], "row": acts3 and acts3[0]["name"]}))
            ctx, pg = browser_as(b, ida, reduced=True)
            go(pg, "/social/@jay")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            frr = record(pg, LINE_GET, None, 1300, lambda: press(pg, "#personSheet [data-safety=mute]"))
            rr, rt = judge_room(frr, True), judge_toast(frr, True)
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, ida, screen="desk")
            go(pg, "/social/@jay")
            dl = pg.evaluate(LINE)
            close_ctx(ctx, pg)
            unmute(ida, "jay")
            check("under Reduce Motion the line's room is put there while it can't be seen, then it fades in; the toast"
                  " only fades; on a desk the line starts under the buttons' left edge",
                  rr["ok"] and rt["ok"] and dl and abs(dl["left"] - dl["actsLeft"]) <= 1 and dl["top"] >= dl["actsBottom"],
                  json.dumps({"room": rr, "toast": rt, "desk": dl and (dl["left"], dl["actsLeft"])}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "rule 3: mute and follow stay apart; the toast says you still follow them; nothing changes on their side"):
        try:
            lee = someone(b, "lee", "Lee Nash")
            mox = someone(b, "mox", "Mox Orr")
            mp = make_post(mox, "Section 5, Mox's")
            follow(lee, "mox")
            ctx, pg = browser_as(b, lee)
            go(pg, "/social/@mox")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            tap_mute(pg, "#personSheet [data-safety=mute]", after=1300)
            st = pg.evaluate(TOAST)
            btn = pg.evaluate("() => { const b = document.querySelector('.fo-btn'); return b ? [b.classList.contains('is-following'), b.getAttribute('aria-label')] : null; }")
            close_ctx(ctx, pg)
            check("Lee follows Mox and mutes him: the toast says “Mox is muted. You still follow them.” with Undo; the"
                  " follow stands (kept, never ended), and his page still says Following",
                  st and st["words"] == "Mox is muted. You still follow them." and st["undo"]
                  and follows_of("lee", "mox") == [(None,)] and btn == [True, "Following Mox Orr"]
                  and mutes_of("lee", "mox") == [("lee", "mox")],
                  json.dumps({"toast": st and st["words"], "follow": follows_of("lee", "mox"), "button": btn}))
            st_m, own = mox.client().get("/social/@mox")
            m = re.search(r'class="lk-by-words">([^<]*<b>[^<]*</b>[^<]*)', own)
            check("nothing changes on Mox's side: his own page still says “Followed by Lee”",
                  st_m == 200 and m and re.sub(r"<[^>]+>", "", m.group(1)).strip() == "Followed by Lee",
                  m.group(1) if m else own[:0])
            c = lee.client()
            c.get("/social/")
            _, f1 = c.get_json("/social/feed?show=following")
            unmute(lee, "mox")
            _, f2 = c.get_json("/social/feed?show=following")
            check("Mox's posts stay out of Home's Following too, while he is muted; unmuted, they are back",
                  isinstance(f1, dict) and mp not in f1.get("html", "") and isinstance(f2, dict) and mp in f2.get("html", ""),
                  f"muted: in Following {isinstance(f1, dict) and mp in f1.get('html', '')}; unmuted:"
                  f" {isinstance(f2, dict) and mp in f2.get('html', '')}")
            mute(lee, "mox")
            follow(lee, "mox", False)
            check("unfollowing never unmutes: Lee stops following Mox and is still muting him",
                  mutes_of("lee", "mox") == [("lee", "mox")] and [e is not None for (e,) in follows_of("lee", "mox")] == [True],
                  f"mutes {mutes_of('lee', 'mox')}; follow {follows_of('lee', 'mox')}")
            unmute(lee, "mox")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "Home and Explore: their posts and drawings leave, in the query; Explore's listing; what you go to stays open"):
        try:
            nat = someone(b, "nat", "Nat Quinn")
            ozz = someone(b, "ozz", "Ozz Ray")
            pia = someone(b, "pia", "Pia Ross")
            qin = someone(b, "qin", "Qin Shaw")
            o_posts = [make_post(ozz, f"Section 6, Ozz's {i}", seed=i) for i in range(2)]
            o_draws = [make_drawing(ozz, f"Section 6 ozz drawing {i}", seed=10 + i) for i in range(2)]
            for i in range(23):
                make_post(pia, f"Section 6, Pia's {i}", seed=20 + i)
            o_posts.append(make_post(ozz, "Section 6, Ozz's last"))
            mute(nat, "ozz")
            card = re.compile(r'<article class="post-card" data-post="([^"]+)"[^>]*?data-handle="([^"]+)"[^>]*?data-kind="([ps])"')

            def walk(c, show):
                """Home's `show`, walked page after page with Load more: [(handle, key)] and each page's size."""
                c.get("/social/")
                _, j = c.get_json(f"/social/feed?show={show}")
                seen, sizes = [], []
                while isinstance(j, dict):
                    got = [(h, k + ":" + pid) for pid, h, k in card.findall(j.get("html", ""))]
                    seen += got
                    sizes.append(len(got))
                    if not j.get("next") or len(sizes) > 30:
                        break
                    _, j = c.get_json("/social/feed?before=" + urllib.parse.quote(j["next"]))
                return seen, sizes
            n_all, n_sizes = walk(nat.client(), "everyone")
            q_all, _ = walk(qin.client(), "everyone")
            check("Home's Everyone leaves out every post and drawing of somebody you muted, in its query: walked to its"
                  " end with Load more it is everybody else's in the order somebody who muted nobody sees, every page"
                  " but the last whole",
                  any(h == "ozz" for h, _ in q_all) and not any(h == "ozz" for h, _ in n_all)
                  and n_all == [x for x in q_all if x[0] != "ozz"] and all(n == 20 for n in n_sizes[:-1])
                  and len(n_sizes) >= 2,
                  f"Nat {len(n_all)} cards ({n_sizes}), Ozz's {sum(h == 'ozz' for h, _ in n_all)}; Qin {len(q_all)},"
                  f" Ozz's {sum(h == 'ozz' for h, _ in q_all)}")
            follow(nat, "ozz")
            follow(nat, "pia")
            f_all, f_sizes = walk(nat.client(), "following")
            check("Home's Following leaves them out too, though Nat follows them: none of theirs on any page, the others'"
                  " there",
                  not any(h == "ozz" for h, _ in f_all) and any(h == "pia" for h, _ in f_all),
                  f"{len(f_all)} cards over {f_sizes}; Ozz's {sum(h == 'ozz' for h, _ in f_all)}, Pia's"
                  f" {sum(h == 'pia' for h, _ in f_all)}")

            def listing(c, query):
                st, j = c.get_json("/api/skribls?limit=100" + query)
                return st, [i["id"] for i in (j.get("items") if isinstance(j, dict) else [])]
            nc, qc = nat.client(), qin.client()
            got = {q: (listing(nc, q), listing(qc, q)) for q in ("", "&sort=hot", "&q=" + urllib.parse.quote("ozz drawing"))}
            check("Explore's listing (Skribl's own, through the feed filter the host installs) leaves out their drawings,"
                  " New, Hot and a search alike, for Nat alone: Qin, who muted nobody, sees them",
                  all(st == 200 and not set(o_draws) & set(ids) for (st, ids), _ in got.values())
                  and all(set(o_draws) <= set(ids) for _, (_, ids) in got.values()),
                  json.dumps({q or "new": [len(set(o_draws) & set(a[1])), len(set(o_draws) & set(b_[1]))]
                              for q, (a, b_) in got.items()}))
            st, mine = listing(nc, "&visibility=public&user_id=" + urllib.parse.quote(public_id("ozz")))
            pages = {p: nc.get(p)[0] for p in ("/social/@ozz", f"/social/p/{o_posts[0]}", f"/social/b/{o_draws[0]}",
                                               f"/s/{o_draws[0]}")}
            # More from his first post: his three newest, his last post and both drawings (Skribl's listing,
            # narrowed to him: the feed filter told so keeps him).
            more_page = nc.get(f"/social/p/{o_posts[0]}")[1]
            more_from = all(f"/social/{k}/{x}" in more_page for k, x in (("p", o_posts[2]), ("b", o_draws[0]), ("b", o_draws[1])))
            pay = nc.get_json(f"/api/skribls/{o_draws[0]}")[0]
            check("what you go to stays open, a mute hides no page: their page's listing (narrowed to them) holds their"
                  " drawings; their page answers, and their post's page with More from them (their drawings in it), their"
                  " drawing's page, its link page and its payload",
                  st == 200 and set(o_draws) <= set(mine) and all(v == 200 for v in pages.values()) and more_from and pay == 200,
                  f"their listing {st} holds {len(set(o_draws) & set(mine))}/2; pages {pages}; more from {more_from}; payload {pay}")
            unmute(nat, "ozz")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "the fold: their comments, one quiet line with Show; hidden for real; counted; Show read on every frame"):
        try:
            rae = someone(b, "rae", "Rae Stone")
            sam = someone(b, "sam", "Sam Tate")
            tia = someone(b, "tia", "Tia Vale")
            for k, who in enumerate((rae, sam, tia)):
                give_face(who, 71 + k)
            cat = make_post(tia, "Section 7, Tia's cat")
            c1 = say_on(rae, cat, "Three whiskers on each side.")
            a1 = say_on(sam, cat, "Ha, I counted too.", answer_to=c1)
            a2 = say_on(tia, cat, "Something for Pickle to watch.", answer_to=c1)
            c2 = say_on(sam, cat, "A cat that won't sit still.")
            a3 = say_on(tia, cat, "She never does.", answer_to=c2)
            snail = make_post(rae, "Section 7, Rae's snail")
            c3 = say_on(sam, snail, "Slow and steady.")
            mute(rae, "sam")
            ctx, pg = browser_as(b, rae)
            go(pg, f"/social/p/{cat}", wait=600)
            to(pg, "#comments", 60)
            folds = {f["id"]: f for f in pg.evaluate(FOLDS)}
            count = pg.evaluate("() => (document.querySelector('[data-cm-count]') || {}).textContent")
            under = pg.evaluate(SHOWN, f"c-{a3}")
            go(pg, f"/social/p/{snail}", wait=600)
            own = {f["id"]: f for f in pg.evaluate(FOLDS)}
            go(pg, "/social/", wait=500)
            home_count = pg.evaluate("(id) => { const a = document.querySelector('.post-card[data-post=\"' + id + '\"] .post-count'); return a ? a.getAttribute('aria-label') : null; }", cat)
            fa, fc = folds.get(f"c-{a1}"), folds.get(f"c-{c2}")
            check("on a post you read, their answer is one quiet line in its place, “Someone you muted answered. Show”,"
                  " and their comment “Someone you muted said something. Show”; on your own post too",
                  fa and fa["words"] == "Someone you muted answered. Show" and fc
                  and fc["words"] == "Someone you muted said something. Show" and fa["show"] == "Show"
                  and own.get(f"c-{c3}", {}).get("words") == "Someone you muted said something. Show" and len(folds) == 2,
                  json.dumps({"answer": fa and fa["words"], "comment": fc and fc["words"], "own": [f["words"] for f in own.values()]}))
            check("the eye sits where their face was (its middle on the faces' column, within 0.5px) and the words start"
                  " where the names do (within 0.5px); the line 56px tall",
                  all(f and f["faceMid"] is not None and abs(f["eyeMid"] - f["faceMid"]) <= 0.5
                      and abs(f["wordsLeft"] - f["nameLeft"]) <= 0.5 and abs(f["h"] - 56) <= 0.5 for f in (fa, fc)),
                  json.dumps([(f["eyeMid"], f["faceMid"], f["wordsLeft"], f["nameLeft"], f["h"]) for f in (fa, fc) if f]))
            check("hidden for real: the comment's own parts can't be seen, reached or tapped (its Answer and ⋯ under the"
                  " line), and a press at the line's middle and 21px out each way lands on the line",
                  all(f and f["hidden"] and f["checked"] is not False and f["reached"] == 0 and f["controls"] >= 1
                      and all(f["lands"]) for f in (fa, fc)),
                  json.dumps([(f["hidden"], f["checked"], f["reached"], f["controls"], f["lands"]) for f in (fa, fc) if f]))
            check("the answers under their comment, by others, stay as they are (Tia's, painted); the count beside"
                  " Comments says every one, theirs too (5), and so does Home's card (5 comments)",
                  under and not under["quiet"] and under["painted"] and fc and fc["answers"] == 1 and count == "5"
                  and home_count == "5 comments",
                  f"Tia's answer {under}; count {count!r}; Home's card {home_count!r}")
            go(pg, f"/social/p/{cat}", wait=600)
            to(pg, f"#c-{a1}", 300)
            fr = record(pg, SHOW_GET, [f"c-{a1}"], 900, lambda: press(pg, f"#c-{a1} [data-cm-show]"))
            shown_j = judge_show(fr, False)
            pg.wait_for_timeout(300)
            after = pg.evaluate(SHOWN, f"c-{a1}")
            go(pg, f"/social/p/{cat}", wait=600)
            again = pg.evaluate(SHOWN, f"c-{a1}")
            close_ctx(ctx, pg)
            check("Show opens it for this visit, read on every frame: its room opens (no frame more than 30% of the way,"
                  " eight frames or more), the line fades and the answer fades in (no frame more than 35% of either),"
                  " never both more than half there at once, the next answer moving down without going back; then it is"
                  " a comment again, painted; reloaded, it is folded again",
                  shown_j["ok"] and after and not after["quiet"] and not after["fold"] and after["painted"]
                  and after["words"] == "Ha, I counted too." and again and again["quiet"],
                  json.dumps({"show": shown_j, "after": after, "reloaded": again}))
            ctx, pg = browser_as(b, rae, reduced=True)
            go(pg, f"/social/p/{cat}", wait=600)
            to(pg, f"#c-{a1}", 300)
            frr = record(pg, SHOW_GET, [f"c-{a1}"], 900, lambda: press(pg, f"#c-{a1} [data-cm-show]"))
            close_ctx(ctx, pg)
            rj = judge_show(frr, True)
            check("under Reduce Motion the room is put there while neither can be seen, and the fades remain",
                  rj["ok"], json.dumps(rj))
            long = make_post(tia, "Section 7, Tia's long one")
            old = say_on(sam, long, "The oldest thing said here.")
            for i in range(20):
                say_on(tia, long, f"Newer {i}")
            ctx, pg = browser_as(b, rae)
            go(pg, f"/social/p/{long}", wait=600)
            first = pg.evaluate("(id) => !!document.getElementById(id)", f"c-{old}")
            press(pg, "[data-cm-next]")
            pg.wait_for_function("(id) => !!document.getElementById(id)", arg=f"c-{old}", timeout=10000)
            pg.wait_for_timeout(300)
            late = pg.evaluate("(id) => { const li = document.getElementById(id); return { quiet: li.classList.contains('is-quiet'),"
                               " fit: li.style.getPropertyValue('--cm-fold-h'), words: (li.querySelector('.cm-fold-line') || {}).textContent }; }",
                               f"c-{old}")
            close_ctx(ctx, pg)
            unmute(rae, "sam")
            check("a page Load more brings folds theirs the same way, its line's room fitted to it",
                  not first and late and late["quiet"] and late["fit"] == "56px"
                  and late["words"].replace("\n", " ").strip().startswith("Someone you muted said something."),
                  json.dumps({"on the first page": first, "late": late}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "Activity goes quiet: their comments, answers, likes and follows leave it, never light the dot; unmute and all is back"):
        try:
            uma = someone(b, "uma", "Uma Vance")
            vic = someone(b, "vic", "Vic Wade")
            wes = someone(b, "wes", "Wes Young")
            up = make_post(uma, "Section 8, Uma's")
            wp = make_post(wes, "Section 8, Wes's")
            uc = say_on(uma, wp, "Uma says hi.")
            say_on(vic, up, "Vic on Uma's post.")
            say_on(vic, wp, "Vic answers Uma.", answer_to=uc)
            like(vic, up)
            like(wes, up)
            follow(vic, "uma")
            mute(uma, "vic")
            db_write("update social_people set activity_seen_at = null where handle_key = 'uma'")
            ctx, pg = browser_as(b, uma)
            go(pg, "/social/activity")
            quiet = [r for s in pg.evaluate(ROWS) for r in s["rows"]]
            go(pg, "/social/activity")
            say_on(vic, up, "Vic again, while muted.")
            go(pg, "/social/")
            dark_dot = pg.evaluate(DOT, ".top-bell")
            say_on(wes, up, "Wes says something.")
            go(pg, "/social/")
            lit = pg.evaluate(DOT, ".top-bell")
            check("Activity leaves out everything of somebody you muted: their comment on your post, their answer to you,"
                  " their like and their follow; a group they were in says the rest (“Wes liked your post”)",
                  quiet and not any("Vic" in r for r in quiet) and "Wes liked your post" in quiet,
                  json.dumps(quiet))
            check("they never light the bell's dot (their new comment on your post leaves it dark), and somebody else's"
                  " comment still lights it",
                  dark_dot is False and lit is True, f"after Vic's: {dark_dot}; after Wes's: {lit}")
            unmute(uma, "vic")
            go(pg, "/social/activity")
            back_rows = [r for s in pg.evaluate(ROWS) for r in s["rows"]]
            close_ctx(ctx, pg)
            want = ["Vic said something on your post", "Vic answered your comment", "Vic followed you"]
            check("unmute, and every row of theirs is back, as it was: nothing was deleted",
                  all(any(w in r for r in back_rows) for w in want)
                  and any(re.search(r"(Vic and Wes|Wes and Vic) liked your post", r) for r in back_rows),
                  json.dumps(back_rows))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "counts and “Liked by…” stay true, for you too"):
        try:
            xia = someone(b, "xia", "Xia Abel")
            yan = someone(b, "yan", "Yan Bird")
            zed = someone(b, "zed", "Zed Cole")
            zp = make_post(zed, "Section 9, Zed's")
            xp = make_post(xia, "Section 9, Xia's")
            like(yan, zp)
            say_on(yan, zp, "Yan on Zed's post.")
            like(yan, xp)
            follow(yan, "xia")
            mute(xia, "yan")
            ctx, pg = browser_as(b, xia)
            go(pg, "/social/", wait=500)
            card = pg.evaluate("(id) => { const c = document.querySelector('.post-card[data-post=\"' + id + '\"]'); if (!c) return null;"
                               " const n = c.querySelector('.lk-n'); return { likes: n ? n.textContent.trim() : '0',"
                               " comments: c.querySelector('.post-count').getAttribute('aria-label') }; }", zp)
            go(pg, f"/social/p/{zp}", wait=600)
            page = pg.evaluate("() => { const n = document.querySelector('.post-art .lk-n');"
                               " return { likes: n ? n.textContent.trim() : '0', comments: (document.querySelector('[data-cm-count]') || {}).textContent,"
                               " folded: document.querySelectorAll('.cm.is-quiet').length }; }")
            go(pg, f"/social/p/{xp}", wait=600)
            by = pg.evaluate("() => { const a = document.querySelector('[data-like-by]'); return a ? a.textContent.replace(/\\s+/g, ' ').trim() : null; }")
            go(pg, "/social/@xia")
            fby = pg.evaluate("() => { const a = document.querySelector('[data-follows-open]'); return a ? a.textContent.replace(/\\s+/g, ' ').trim() : null; }")
            close_ctx(ctx, pg)
            unmute(xia, "yan")
            check("counts stay true for you too: Home's card for a post they liked and said something on says 1 like and 1"
                  " comment, and its page the same (their comment folded, and counted)",
                  card == {"likes": "1", "comments": "1 comment"} and page == {"likes": "1", "comments": "1", "folded": 1},
                  json.dumps({"card": card, "page": page}))
            check("“Liked by…” and “Followed by…” on your own name them: a mute changes what reaches you, never a number",
                  by and "Yan" in by and fby and "Yan" in fby, f"liked by {by!r}; followed by {fby!r}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "Settings: Muted just above Blocked, its rows and words; Unmute comes back; muted then blocked"):
        try:
            abe = someone(b, "abe", "Abe Dunn")
            bea = someone(b, "bea", "Bea Earl")
            cyd = someone(b, "cyd", "Cyd Ford")
            dov = someone(b, "dov", "Dov Gale")
            for k, who in enumerate((bea, cyd)):
                give_face(who, 91 + k)
            mute(abe, "bea")
            time.sleep(0.05)
            mute(abe, "cyd")
            ctx, pg = browser_as(b, abe)
            go(pg, "/social/you")
            s1 = pg.evaluate(SETTINGS)
            check("Settings has Muted just above Blocked, “You see less of them. They aren’t told, and nothing changes for"
                  " them.”, the people you muted newest first in the Blocked panel's own rows: face, name, @handle and"
                  " Unmute, 44px to a finger",
                  "Muted" in s1["titles"] and s1["titles"].index("Blocked") == s1["titles"].index("Muted") + 1 and s1["above"]
                  and s1["sub"] == "You see less of them. They aren’t told, and nothing changes for them."
                  and [(r["name"], r["handle"]) for r in s1["rows"]] == [("Cyd Ford", "@cyd"), ("Bea Earl", "@bea")]
                  and all(r["face"] and r["btn"] == "Unmute" and r["h"] >= 44 and all(r["lands"]) for r in s1["rows"])
                  and s1["rows"][0]["label"] == "Unmute @cyd" and s1["rows"][0]["form"] == "/social/@cyd/unmute",
                  json.dumps(s1))
            dctx, dpg = browser_as(b, dov)
            go(dpg, "/social/you")
            s0 = dpg.evaluate(SETTINGS)
            close_ctx(dctx, dpg)
            check("with nobody muted it says so in its own words: “Nobody. If you mute someone, they’re listed here, and"
                  " you can unmute them.”",
                  s0.get("sub") == "Nobody. If you mute someone, they’re listed here, and you can unmute them."
                  and s0.get("rows") == [], json.dumps(s0))
            with pg.expect_navigation(timeout=10000):
                press(pg, ".mu-list .blocked-row:has-text('@cyd') button")
            pg.wait_for_timeout(300)
            s2 = pg.evaluate(SETTINGS)
            url = pg.url
            check("Unmute there (a form) unmutes and comes back to Settings at Muted, saying “Unmuted. Everything comes"
                  " back, just as it was.”",
                  mutes_of("abe") == [("abe", "bea")] and "note=unmuted" in url and url.endswith("#mutedTitle")
                  and (s2.get("note") or "").strip() == "Unmuted. Everything comes back, just as it was."
                  and [r["handle"] for r in s2["rows"]] == ["@bea"],
                  f"{url}; note {s2.get('note')!r}; rows {[r['handle'] for r in s2.get('rows', [])]}; kept {mutes_of('abe')}")
            block(abe, "bea")
            go(pg, "/social/you")
            s3 = pg.evaluate(SETTINGS)
            unblock(abe, "bea")
            go(pg, "/social/you")
            s4 = pg.evaluate(SETTINGS)
            close_ctx(ctx, pg)
            check("somebody muted and then blocked is listed under Blocked alone; unblocked, they are under Muted again,"
                  " muted still",
                  s3.get("rows") == [] and s3.get("blockedRows") == ["@bea"] and [r["handle"] for r in s4.get("rows", [])] == ["@bea"]
                  and s4.get("blockedRows") == [] and mutes_of("abe", "bea") == [("abe", "bea")],
                  f"blocked: muted {s3.get('rows')}, blocked {s3.get('blockedRows')}; unblocked: muted"
                  f" {[r['handle'] for r in s4.get('rows', [])]}; kept {mutes_of('abe', 'bea')}")
            unmute(abe, "bea")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "who may mute: refused and nothing kept; the limit; a refusal in the page puts everything back"):
        try:
            eli = someone(b, "eli", "Eli Hart")
            fox = someone(b, "fox", "Fox Ivey")
            gus = someone(b, "gus", "Gus Jett")
            hap = someone(b, "hap", "Hap Kerr")
            ivo = someone(b, "ivo", "Ivo Lamb")
            s1, j1 = mute(None, "fox")
            s2, j2 = mute(eli, "fox", token="")
            s3, j3 = mute(eli, "fox", origin="https://elsewhere.example")
            u1, k1 = unmute(None, "fox")
            u2, k2 = unmute(eli, "fox", token="")
            check("signed out, without the page's token, or from another origin: refused (401, 403), nothing kept;"
                  " Unmute the same",
                  s1 == 401 and j1.get("error") == "signed_out" and s2 == 403 and j2.get("error") == "stale"
                  and s3 == 403 and j3.get("error") == "stale" and u1 == 401 and u2 == 403 and mutes_of("eli") == [],
                  f"{s1} {j1}; {s2} {j2}; {s3} {j3}; unmute {u1} {u2}; kept {mutes_of('eli')}")
            s4, j4 = mute(eli, "eli")
            s5, j5 = mute(eli, "nobody_here", page="/social/")
            block(gus, "eli")
            s6, j6 = mute(eli, "gus", page="/social/")
            s7, j7 = mute(gus, "eli", page="/social/")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'ivo'")
            s8, j8 = mute(eli, "ivo", page="/social/")
            db_write("update social_people set taken_down_at = null where handle_key = 'ivo'")
            check("yourself, nobody by that name, a block either way, somebody taken down: “gone” (404), nothing kept",
                  all(st == 404 and isinstance(j, dict) and j.get("error") == "gone"
                      for st, j in ((s4, j4), (s5, j5), (s6, j6), (s7, j7), (s8, j8)))
                  and mutes_of("eli") == [] and mutes_of("gus") == [],
                  f"self {s4}; nobody {s5}; blocked {s6}/{s7}; taken down {s8}; kept {mutes_of('eli') + mutes_of('gus')}")
            c = fox.client()
            c.get("/social/@hap")
            got = [c.post_json(f"/social/@hap/{'mute' if i % 2 == 0 else 'unmute'}", {})[0] for i in range(61)]
            check("the limit: sixty mutes and unmutes an hour a person, the sixty-first refused (429), and the last kept is"
                  " the sixtieth's (an unmute)",
                  got[:60] == [200] * 60 and got[60] == 429 and mutes_of("fox", "hap") == [],
                  f"{got.count(200)} kept, then {got[60:]}; rows {mutes_of('fox', 'hap')}")
            ctx, pg = browser_as(b, hap)
            go(pg, "/social/@ivo")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            block(ivo, "hap")
            tap_mute(pg, "#personSheet [data-safety=mute]", after=1400)
            st = pg.evaluate(TOAST)
            line = pg.evaluate("() => document.querySelectorAll('[data-mute-line], .mu-room').length")
            open_sheet(pg, "[data-person-menu]", "personSheet")
            row = pg.evaluate(ACTS, "#personSheet")
            close_ctx(ctx, pg)
            check("a refusal in the page puts everything back (the line goes, the ⋯ says Mute again) and the toast says"
                  " why, kindly, with no Undo: “They aren’t here anymore. Reload the page to see what’s new.”",
                  st and st["words"] == "They aren’t here anymore. Reload the page to see what’s new." and not st["undo"]
                  and line == 0 and row and row[0]["name"] == "Mute @ivo" and mutes_of("hap") == [],
                  json.dumps({"toast": st and (st["words"], st["undo"]), "line": line, "row": row and row[0]["name"]}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "nothing of mutes for anybody else: signed out, your own page, somebody you blocked"):
        try:
            jon = someone(b, "jon", "Jon Moss")
            kai = someone(b, "kai", "Kai Nunn")
            kp = make_post(kai, "Section 12, Kai's")
            marks = ("mu-act", "data-mute-toasts", "mutes.js", "Mute @", "data-mute-line")
            nobody = Client()
            out = {p: [m for m in marks if m in nobody.get(p)[1]] for p in ("/social/", "/social/@kai", f"/social/p/{kp}")}
            check("signed out there is no mute anywhere: no row, no toast, no script, on somebody's page, a post's page"
                  " and Home", not any(out.values()), json.dumps(out))
            c = jon.client()
            own = [m for m in marks if m in c.get("/social/@jon")[1]]
            block(jon, "kai")
            blocked = [m for m in marks if m in c.get("/social/@kai")[1]]
            unblock(jon, "kai")
            home = [m for m in ("data-mute-toasts", "mutes.js") if m in c.get("/social/")[1]]
            check("your own page has none of it, nor the page of somebody you blocked (Unblock is there); signed in, Home"
                  " carries the toast and its script",
                  not own and not blocked and home == ["data-mute-toasts", "mutes.js"],
                  f"own {own}; blocked {blocked}; Home {home}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)

    # ------------------------------------------------------------------ 13
    if part(13, "the data: the chain up, down and up; one row a pair, never yourself; its PostgreSQL DDL; the reads; deleting in code"):
        try:
            mdb = os.path.join(TMP, "chain-mutes.db")
            BEFORE = "1757a4385be8"      # the chain's head before mutes (its migration's down_revision)

            def chain(*args, url=None):
                return subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", *args], cwd=ROOT,
                                      env=dict(os.environ, DATABASE_URL=url or f"sqlite:///{mdb}"), capture_output=True,
                                      text=True, timeout=180)

            def at(sql, args=()):
                con = sqlite3.connect(mdb)
                try:
                    return con.execute(sql, args).fetchall()
                finally:
                    con.close()

            up1 = chain("upgrade", BEFORE)
            con = sqlite3.connect(mdb)
            then = "2026-11-13 10:00:00"
            for i, h in ((1, "ann"), (2, "bob")):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle,"
                            " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                            (i, "site:" + h, h, h, h.title(), bytes([i]) * 32, then, then))
            con.commit()
            con.close()
            tables0 = {r[0] for r in at("select name from sqlite_master where type = 'table'")}
            up2 = chain("upgrade", "head")
            idx = {r[0]: r[1] for r in at("select name, sql from sqlite_master where type = 'index' and tbl_name = 'social_mutes'")}
            cols = [r[1] for r in at("pragma table_info(social_mutes)")]
            sql = (at("select sql from sqlite_master where name = 'social_mutes'") or [[""]])[0][0] or ""
            tables1 = {r[0] for r in at("select name from sqlite_master where type = 'table'")}
            check("the site's chain on a database with people in it adds social_mutes (who, whom, when), its three indexes"
                  " (the pair unique; whose newest first; whom) and its CHECK, touching nothing else",
                  up1.returncode == 0 and up2.returncode == 0 and cols == ["id", "muter_id", "muted_id", "created_at"]
                  and set(idx) == {"ix_social_mutes_pair", "ix_social_mutes_muter_created", "ix_social_mutes_muted_id"}
                  and "UNIQUE" in (idx.get("ix_social_mutes_pair") or "") and "ck_social_mutes_not_self" in sql
                  and tables1 - tables0 == {"social_mutes"} and at("select count(*) from social_people") == [(2,)],
                  f"up {up1.returncode}/{up2.returncode} {up2.stderr.strip().splitlines()[-1:] if up2.returncode else ''};"
                  f" cols {cols}; indexes {sorted(idx)}; new tables {sorted(tables1 - tables0)}")
            con = sqlite3.connect(mdb)
            errs = []
            for vals in ((1, 2), (1, 2), (2, 1), (1, 1)):
                try:
                    con.execute("insert into social_mutes (muter_id, muted_id, created_at) values (?, ?, ?)", vals + (then,))
                    errs.append("kept")
                except sqlite3.IntegrityError as e:
                    errs.append(str(e).split(":")[0])
            con.rollback()
            con.close()
            check("one row a pair (a second is refused, the other way round is its own pair), and nobody mutes"
                  " themselves (refused)",
                  errs == ["kept", "UNIQUE constraint failed", "kept", "CHECK constraint failed"], json.dumps(errs))
            down = chain("downgrade", BEFORE)
            gone = at("select name from sqlite_master where tbl_name = 'social_mutes'")
            stamp_down = at("select version_num from social_alembic_version")
            up3 = chain("upgrade", "head")
            back_again = {r[0] for r in at("select name from sqlite_master where tbl_name = 'social_mutes'")}
            head = subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", "heads"], cwd=ROOT,
                                  capture_output=True, text=True, timeout=60).stdout.split()[0]
            check("taken back down the chain drops the table and its indexes, every person kept, stamped where it was;"
                  " up again, it is all back at the head",
                  down.returncode == 0 and gone == [] and stamp_down == [(BEFORE,)] and up3.returncode == 0
                  and back_again == {"social_mutes", "ix_social_mutes_pair", "ix_social_mutes_muter_created", "ix_social_mutes_muted_id"}
                  and at("select version_num from social_alembic_version") == [(head,)]
                  and at("select handle from social_people order by id") == [("ann",), ("bob",)],
                  f"down {down.returncode}, left {gone}, stamped {stamp_down}; up {up3.returncode}: {sorted(back_again)}")
            pg_url = "postgresql://nobody:nothing@localhost/none"
            ddl_up = chain("upgrade", f"{BEFORE}:head", "--sql", url=pg_url)
            ddl_down = chain("downgrade", f"head:{BEFORE}", "--sql", url=pg_url)
            u, d = ddl_up.stdout, ddl_down.stdout
            want_up = ["CREATE TABLE social_mutes", "id BIGSERIAL NOT NULL", "muter_id BIGINT NOT NULL",
                       "muted_id BIGINT NOT NULL", "created_at TIMESTAMP WITH TIME ZONE NOT NULL",
                       "CONSTRAINT ck_social_mutes_not_self CHECK (muter_id <> muted_id)",
                       "FOREIGN KEY(muter_id) REFERENCES social_people (id) ON DELETE CASCADE",
                       "FOREIGN KEY(muted_id) REFERENCES social_people (id) ON DELETE CASCADE",
                       "CREATE UNIQUE INDEX ix_social_mutes_pair ON social_mutes (muter_id, muted_id)",
                       "CREATE INDEX ix_social_mutes_muter_created ON social_mutes (muter_id, created_at)",
                       "CREATE INDEX ix_social_mutes_muted_id ON social_mutes (muted_id)"]
            want_down = ["DROP INDEX ix_social_mutes_muted_id", "DROP INDEX ix_social_mutes_muter_created",
                         "DROP INDEX ix_social_mutes_pair", "DROP TABLE social_mutes"]
            check("its PostgreSQL DDL, read offline, is plain: CREATE TABLE with its CHECK and two cascading foreign keys,"
                  " three CREATE INDEX; the downgrade the reverse, and nothing else of the site's touched",
                  ddl_up.returncode == 0 and ddl_down.returncode == 0 and all(w in u for w in want_up)
                  and all(w in d for w in want_down) and u.count("CREATE TABLE") == 1 and "ALTER TABLE" not in u
                  and d.count("DROP TABLE") == 1,
                  f"up {ddl_up.returncode}, missing {[w for w in want_up if w not in u]}; down {ddl_down.returncode},"
                  f" missing {[w for w in want_down if w not in d]}")
            wyn = someone(b, "wyn", "Wyn Yale")
            xan = someone(b, "xan", "Xan Zorn")
            yul = someone(b, "yul", "Yul Abel")
            someone(b, "zia", "Zia Bond")
            make_post(xan, "Section 13, Xan's")
            make_post(yul, "Section 13, Yul's")
            mute(wyn, "xan")
            mute(yul, "wyn")
            copy = os.path.join(TMP, "probe13.db")
            src, dst = sqlite3.connect(DB, timeout=10), sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            home_as = "; ".join(f"{c['name']}={c['value']}" for c in wyn.ctx.cookies(BASE))
            probe = subprocess.run([sys.executable, "-c", PROBE, "wyn", home_as, "zia"], cwd=ROOT, capture_output=True,
                                   text=True, timeout=180,
                                   env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-600:]}
            plans = out.get("plans") or {}
            check("the reads, as the code sends them, are searches on their own indexes (SQLite's own plan): whom you muted"
                  " by the person's public id and the pair (one read, for the site's pages and the host's filter alike),"
                  " Settings' list by whose newest first with no sort of its own",
                  any("ix_social_mutes_pair (muter_id=?)" in x for x in plans.get("ids", []))
                  and any("ix_social_people_public_id (public_id=?)" in x for x in plans.get("ids", []))
                  and any("ix_social_mutes_muter_created (muter_id=?)" in x for x in plans.get("people", []))
                  and not any(x.startswith("SCAN social_mutes") or x.startswith("SCAN m") for v in plans.values() for x in v)
                  and not any("TEMP B-TREE" in x for x in plans.get("people", []))
                  and out.get("same_read") is True,
                  json.dumps(plans or out.get("err"))[:700])
            h1, h2 = out.get("home1") or {}, out.get("home2") or {}
            check("Home stays cheap: one read of mutes a request whatever it shows, and no read a card: ten more cards on"
                  " the page, the same number of reads; nothing of Xan's on it",
                  h1.get("mutes") == 1 and h2.get("mutes") == 1 and h1.get("reads") == h2.get("reads")
                  and (h2.get("cards") or 0) >= (h1.get("cards") or 0) + 10 and h1.get("xan") is False,
                  json.dumps({"home1": h1, "home2": h2, "err": out.get("err")}))
            check("deleting an account takes its mutes both ways, in code: with SQLite's cascade off, none is left",
                  out.get("fk") == 0 and out.get("deleted") == [2, 0],
                  json.dumps({k: out.get(k) for k in ("fk", "deleted", "err")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(13, exc)

    # ------------------------------------------------------------------ 14
    if part(14, "words and marks: every new word and mark, read two ways; every screen's words; 44px; phone and desk, light and dark"):
        try:
            ada = someone(b, "ada", "Ada Bloom")
            bix = someone(b, "bix", "Bix Crane")
            cob = someone(b, "cob", "Cob Dove")
            dot_ = someone(b, "dot", "Dot Ellis")
            for k, who in enumerate((ada, bix, cob, dot_)):
                give_face(who, 130 + k)
            bxp = make_post(bix, "Section 14, Bix's")
            dp = make_post(dot_, "Section 14, Dot's")
            dc = say_on(ada, dp, "Ada says hello.")
            say_on(bix, dp, "Bix answers.", answer_to=dc)
            ap = make_post(ada, "Section 14, Ada's")
            like(bix, ap)
            like(dot_, ap)
            like(cob, ap)
            follow(ada, "cob")
            news, reads, smalls, fields, taps = [], [], [], [], []
            TAPS = r"""(sels) => { const open = document.querySelector('.make.is-open .make-sheet');
              return sels.flatMap(sel => [...document.querySelectorAll(sel)].filter(b => { if (!b.getClientRects().length) return false;
                if (open && !open.contains(b)) return false; const r = b.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).map(b => {
                const r = b.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                const lands = [[cx, cy], [cx - 21, cy], [cx + 21, cy], [cx, cy - 21], [cx, cy + 21]].map(([x, y]) => {
                  const e = document.elementFromPoint(x, y); return !!e && (e === b || b.contains(e)); });
                return { sel, h: Math.round(r.height), all: lands.every(Boolean) }; })); }"""

            def look(pg, tag, where, sels, root=None, tap=None):
                news.extend((tag, where, r) for r in read_new(pg, sels))
                got = pg.evaluate(READ, root)
                reads.append((tag, where, got))
                smalls.extend(f"{tag} {where}: {x}" for x in got["small"])
                fields.extend(f"{tag} {where}: {x}" for x in got["fields"])
                if tap:
                    taps.extend((tag, where, t) for t in pg.evaluate(TAPS, tap))
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    unmute(ada, "bix")
                    unmute(ada, "cob")
                    ctx, pg = browser_as(b, ada, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=500)
                    to(pg, f'.post-card[data-post="{bxp}"]', 120)
                    open_sheet(pg, f'.post-card[data-post="{bxp}"] [data-post-menu]', "postSheet")
                    look(pg, tag, "a post's ⋯", NEW_ROW, "#postSheet", [".mu-act"])
                    tap_mute(pg, "#postSheet [data-act=mute]", after=1300)
                    look(pg, tag, "the toast", NEW_TOAST, None, [".mu-undo"])
                    go(pg, "/social/@bix", wait=600)
                    look(pg, tag, "their page, muted", NEW_LINE, None, [".mu-unmute"])
                    open_sheet(pg, "[data-person-menu]", "personSheet")
                    look(pg, tag, "their ⋯, Unmute", NEW_ROW, "#personSheet", [".mu-act"])
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(500)
                    go(pg, f"/social/p/{dp}", wait=600)
                    to(pg, "#comments", 60)
                    look(pg, tag, "the fold", NEW_FOLD, None, [".cm-fold-line"])
                    go(pg, "/social/you")
                    to(pg, "#mutedTitle", 100)
                    look(pg, tag, "Settings, Muted", NEW_SET, None, [".mu-list .btn"])
                    go(pg, "/social/@cob", wait=600)
                    open_sheet(pg, "[data-person-menu]", "personSheet")
                    look(pg, tag, "their ⋯, Mute", NEW_ROW, "#personSheet", [".mu-act"])
                    tap_mute(pg, "#personSheet [data-safety=mute]", after=1300)
                    look(pg, tag, "rule 3's toast", NEW_TOAST, None, [".mu-undo"])
                    tap_mute(pg, "[data-mute-undo]", path_end="/unmute", after=1000)
                    look(pg, tag, "the Unmuted toast", NEW_TOAST)
                    db_write("update social_people set activity_seen_at = null where handle_key = 'ada'")
                    go(pg, "/social/activity", wait=500)
                    look(pg, tag, "Activity, quiet", [])
                    close_ctx(ctx, pg)
            unmute(ada, "bix")
            for tag in ("phone/light", "phone/dark", "desk/light", "desk/dark"):
                mine = [(w, g) for t, w, g in reads if t == tag]
                check(f"every word at 4.5:1 or more on what is painted behind it, {tag}: a post's ⋯, the toast, their page"
                      " muted, their ⋯ (Unmute and Mute), the fold, Settings' Muted, rule 3's toast, the Unmuted toast,"
                      " Activity quiet",
                      len(mine) == 10 and all(g["read"] > 0 for _, g in mine) and not any(g["low"] for _, g in mine),
                      f"read {[(w, g['read'], g['lowest']) for w, g in mine]}; low {[x for _, g in mine for x in g['low']][:3]}")
            unread = [(t, w, r) for t, w, r in news if r.get("unread")]
            weak = [(t, w, r["what"], r["low"]) for t, w, r in news if not r.get("unread") and r["low"] < r["need"]]
            kinds = sorted({r["what"] for _, _, r in news})
            low = {}
            for t, _, r in news:
                k = (r["what"], t)
                low[k] = min(low.get(k, 99), r["low"])
            check("every new word at 4.5:1 or more and every new mark at 3:1 or more, each read two ways (its colour on"
                  " its ground, and the painted pixels), the lower counting, phone and desk, light and dark; a colour"
                  " the reader can't read is a red that names it",
                  len(kinds) >= 15 and not weak and not unread,
                  f"under {weak[:3]}; unread {[(t, w, r['unread']) for t, w, r in unread[:2]]}; the lowest of each, light"
                  " (phone/desk) and dark (phone/desk): "
                  + "; ".join(f"{w} " + "/".join(f"{low[(w, t)]:g}" if (w, t) in low else "-"
                                               for t in ("phone/light", "desk/light", "phone/dark", "desk/dark"))
                              for w in kinds))
            short = [(t, w, x) for t, w, x in taps if not x["all"] or x["h"] < 44]
            check("every new control 44px to a finger (a press at its middle and 21px out each way lands on it): the row,"
                  " Undo, Unmute on their page, the fold, Settings' Unmute; no target under 44px and no text field under"
                  " 16px on any of these screens",
                  len(taps) >= 32 and not short and not smalls and not fields,
                  f"{len(taps)} read; short {short[:3]}; small {smalls[:3]}; fields {fields[:3]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(14, exc)

    # ------------------------------------------------------------------ 15
    if part(15, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(15, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
