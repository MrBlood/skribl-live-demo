"""Following on the Skribl site (phase 2, follows; docs/SOCIAL-SITE.md "Built:
follows"), through the demo's own server, with Chromium's virtual
authenticator for the site's people. The owner's "Yes to all" on the follow
mock, B (Nov 13): who follows whom is yours alone.

  1. THE BUTTON, WHERE IT IS: first in the row on somebody's page, before
     Share and ⋯ (on a desk the same row, beside their face); Follow in the
     action's purple, a plus in our pen, 44px, named "Follow <name>"; never on
     your own page, nor on somebody you blocked; there signed out; never on a
     card.
  2. A TAP FOLLOWS, AND ASKS ONCE TO STOP: Following at once and kept by the
     site, still so after a reload; as wide as Following either way, so
     nothing beside it moves (phone and desk); a tap on Following raises
     "Unfollow <first>?" (Unfollow the big button, Keep following beside it);
     Keep following keeps it; Unfollow ends it; following again keeps the
     first time.
  3. WHO MAY FOLLOW: signed out, without the token or from elsewhere, taken
     down, yourself, nobody by that name, a block either way, somebody taken
     down, a body that is not a yes or a no: refused, nothing kept; the limit
     (60 an hour); a refusal in the page puts the button back and says why;
     Home's pick, its guards.
  4. YOURS ALONE: nothing of follows on somebody else's page, not in the page
     and not in its source; your own page's "Followed by…" (every name up to
     three, else two and how many more; the newest three faces), "You
     follow…" before anybody follows you, no line with nobody either way;
     counted by the viewer (somebody taken down is in no line and no list).
  5. THE LISTS: Make's own sheet in its paper, the one pill, Followers and
     Following newest first with when, "Only you can see…", a row to their
     page; the sheet keeps its height between them; #followers and
     #following open it on that list.
  6. KIND, NEVER JUMPY (the button), read on every frame: following fades the
     fill and the words and draws the check, nothing moving; unfollowing
     fades, nothing un-drawing; under Reduce Motion only fades.
  7. HOME'S PILL: Following | Everyone under the composer, the Gallery's pill
     value for value, 44px to a finger; opens on Everyone before you follow
     anybody and on Following after; your pick kept for the account, on
     another device too; the switch read on every frame (the pill glides,
     the posts fade, change while unseen and fade back, the page doesn't
     scroll); under Reduce Motion the pill is put there and the posts fade.
  8. FOLLOWING NEVER RUNS OUT: the people you follow and you, posts and
     drawings, newest first, nothing else; then "You're caught up…" with its
     check and Fresh from everyone, everybody else's, nothing twice; Load more
     carries on through both; following nobody, the kind card and everyone's;
     somebody taken down is in nobody's Following.
  9. ACTIVITY: "Mira followed you", the face wearing a small Follow (the
     action's purple, a white plus), no picture; grouped since you last
     looked ("… and 2 others", "… and …"); one person opens their page,
     several open who follows you; under Earlier a day's follows one row;
     following again never new twice, a follow taken back no row; follows
     never light the bell's dot; the heading's and the empty page's words.
 10. SIGNED OUT: Follow raises "Follow <first>?" in a sheet's paper; Not now
     gives Follow its focus back; Sign in comes back to the page, where
     Follow waits, nothing pressed.
 11. BLOCKS: a block ends a follow both ways and none can begin while it
     stands; lifting it brings none back.
 12. THE DATA: the chain on a populated database (the table, its three
     indexes, its CHECK, Home's pick; back down); one row a pair, never
     yourself; the reads on their indexes (SQLite's own plan); Home's
     Following with no read a card; deleting an account takes its follows
     both ways in code, with SQLite's cascade off.
 13. WORDS AND MARKS: every word on every new screen at 4.5:1 on what is
     painted behind it, every mark at 3:1, every target 44px to a finger, no
     field under 16px, phone (touch) and desk, light and dark.
 14. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALFOLLOW_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Following at /social".
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
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALFOLLOW_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALFOLLOW {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence following works.")
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
TMP = tempfile.mkdtemp(prefix="socialfollow-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialfollow-" + secrets.token_hex(8),
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

    def post_json(self, path, body, token=None):
        st, text = self._req("POST", path, body=body, headers={"X-Social-CSRF": self.token or "" if token is None else token})
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
    theirs, kept unlisted, named as their face on their row. Its skribl's id."""
    sid = make_drawing(who, f"{who.handle}'s face", seed=seed, vis="unlisted")
    db_write("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = ?",
             (sid, who.handle.lower()))
    return sid


def follow(who, handle, following=True, raw=None, token=None, origin=BASE):
    """A follow (or taking it back) as the button sends one: (status, answer)."""
    c = who.client() if who is not None else Client()
    c.origin = origin
    c.get(f"/social/@{handle}")
    if not c.token:
        c.get("/social/")      # a page they cannot open: the token from one they can
    return c.post_json(f"/social/@{handle}/follow", raw if raw is not None else {"following": following}, token=token)


def pick(who, show, raw=None, token=None, page="/social/"):
    """Home's pill, as it keeps a pick: (status, answer). Somebody signed out
    takes the token from a page that carries one for everybody (`page`)."""
    c = who.client() if who is not None else Client()
    c.get(page)
    return c.post_json("/social/home/show", raw if raw is not None else {"show": show}, token=token)


def follows_of(handle=None, of=None):
    """The rows kept: [(follower, followed, created_at, ended_at)], oldest first."""
    q = ("select a.handle, b.handle, f.created_at, f.ended_at from social_follows f"
         " join social_people a on a.id = f.follower_id join social_people b on b.id = f.followed_id")
    where, args = [], []
    if handle:
        where.append("a.handle_key = ?")
        args.append(handle)
    if of:
        where.append("b.handle_key = ?")
        args.append(of)
    return db(q + (" where " + " and ".join(where) if where else "") + " order by f.id", tuple(args))


def block(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/block", {})[0]


def unblock(who, handle):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/@{handle}/unblock", {})[0]


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


def tap_follow(pg, after=300):
    """Tap Follow (click it, on a desk) and wait for the site's answer. A tap
    that sends nothing reads as the row's own red, never a section that stops."""
    try:
        with pg.expect_response(lambda r: r.url.endswith("/follow") and r.request.method == "POST", timeout=8000):
            press(pg, ".fo-btn")
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(after)


def tap_to(pg, loc, timeout=10000):
    """Tap something that should open a page, and wait for it: one that does
    not go anywhere reads as the row's own red."""
    try:
        with pg.expect_navigation(timeout=timeout):
            loc.tap(timeout=5000)
    except Exception:  # noqa: BLE001
        pass


def handle_of(pid):
    got = db("select p.handle from social_posts s join social_people p on p.id = s.person_id where s.public_id = ?", (pid or "",))
    return got[0][0] if got else None


# ---- what the page shows, read in the page ---------------------------------------
# A profile's row of buttons, in order: what each is and its box.
ROW = r"""() => { const acts = document.querySelector('.prof-acts'); if (!acts) return null;
  return [...acts.children].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect();
    return { what: e.matches('.fo-btn') ? 'follow' : e.matches('[data-share]') ? 'share' : e.matches('[data-person-menu]') ? 'more'
             : e.matches('[href$="/you/edit"]') ? 'edit' : e.matches('[data-face-sheet]') ? 'face'
             : e.matches('[aria-label=Settings]') ? 'gear' : e.tagName.toLowerCase(),
             x: Math.round(r.left * 100) / 100, y: Math.round(r.top * 100) / 100, w: Math.round(r.width * 100) / 100,
             h: Math.round(r.height * 100) / 100 }; }); }"""

# The Follow button: its state, its name, its words, its paint and its box.
FBTN = r"""() => { const b = document.querySelector('.fo-btn'); if (!b || !b.getClientRects().length) return null;
  const r = b.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const off = b.querySelector('.fo-off'), on = b.querySelector('.fo-on'), chk = b.querySelector('.fo-on svg path');
  const plus = b.querySelector('.fo-off svg'), cs = getComputedStyle(b), face = document.querySelector('.prof-face');
  const fr = face ? face.getBoundingClientRect() : null, onw = on.getBoundingClientRect().width, offw = off.getBoundingClientRect().width;
  return { x: r.left, y: r.top, w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
    label: b.getAttribute('aria-label'), following: b.classList.contains('is-following'), popup: b.getAttribute('aria-haspopup'),
    hit: !!at && (at === b || b.contains(at)), bg: cs.backgroundColor, color: cs.color, shadow: cs.boxShadow !== 'none',
    offOp: +getComputedStyle(off).opacity, onOp: +getComputedStyle(on).opacity,
    dash: chk ? parseFloat(getComputedStyle(chk).strokeDashoffset) : null, arr: chk ? getComputedStyle(chk).strokeDasharray : null,
    plus: !!plus && plus.classList.contains('pen-ic') && plus.querySelectorAll('path[pathLength="1"]').length === 2,
    check: !!chk && chk.getAttribute('pathLength') === '1' && chk.closest('svg').classList.contains('pen-ic'),
    words: [off.textContent.trim(), on.textContent.trim()], wide: Math.round((Math.max(onw, offw) + 38) * 100) / 100,
    onWider: onw >= offw, follow: b.getAttribute('data-follow'), out: b.hasAttribute('data-follow-out'),
    face: fr ? { right: fr.right, top: fr.top, bottom: fr.bottom } : null }; }"""

# Your own page's line: its words, its faces (a face's still picture names whose
# it is), and whether it is painted where it stands.
LINE = r"""() => { const a = document.querySelector('[data-follows-open]'); if (!a || !a.getClientRects().length) return null;
  const r = a.getBoundingClientRect(), at = document.elementFromPoint(r.left + 40, r.top + r.height / 2);
  return { words: a.querySelector('.lk-by-words').textContent.replace(/\s+/g, ' ').trim(), tab: a.getAttribute('data-follows-open'),
           faces: [...a.querySelectorAll('.face-ring')].map(f => { const i = f.querySelector('img.skribl-face-still');
                                                                    return i ? new URL(i.src).pathname : 'blank'; }),
           h: Math.round(r.height * 10) / 10, hit: !!at && (at === a || a.contains(at)), popup: a.getAttribute('aria-haspopup') }; }"""

# A sheet: open, its paper, its title, its words, its buttons (in order, and
# which is the action), where Sign in goes, and what has focus.
SHEET = r"""(id) => { const w = document.getElementById(id); if (!w) return null;
  const s = w.querySelector('.make-sheet'), a = w.querySelector('.post-sheet-acts a'), r = s.getBoundingClientRect();
  return { open: w.classList.contains('is-open') && !w.hidden, paper: getComputedStyle(s).backgroundColor,
    role: s.getAttribute('role'), modal: s.getAttribute('aria-modal'), title: w.querySelector('.make-title').textContent.trim(),
    lede: (w.querySelector('.post-lede') || {}).textContent ? w.querySelector('.post-lede').textContent.replace(/\s+/g, ' ').trim() : null,
    acts: [...w.querySelectorAll('.post-sheet-acts > *')].map(e => [e.textContent.trim(), e.classList.contains('btn-primary'),
                                                                    Math.round(e.getBoundingClientRect().height)]),
    href: a ? new URL(a.href).pathname + new URL(a.href).search : null, h: Math.round(r.height * 10) / 10,
    focus: document.activeElement ? (document.activeElement.textContent || '').trim() : null }; }"""

# The lists: open, the pill (which is pressed), each list's rows in order, which
# list is shown, the note, and the sheet's height.
LISTS = r"""() => { const w = document.getElementById('followsSheet'); if (!w) return null;
  const s = w.querySelector('.make-sheet'), seg = w.querySelector('.fo-seg');
  const list = k => { const ul = w.querySelector('[data-list="' + k + '"]'); const cs = getComputedStyle(ul);
    return { shown: cs.visibility === 'visible' && +cs.opacity > 0.99, card: cs.backgroundColor,
      rows: [...ul.querySelectorAll('.lk-row')].map(a => ({ name: a.querySelector('.lk-who b').textContent.trim(),
        handle: a.querySelector('.lk-who span').textContent.trim(), href: new URL(a.href).pathname,
        when: (a.querySelector('time') || {}).textContent || null, iso: (a.querySelector('time') || {}).dateTime || null })),
      empty: (ul.querySelector('.fo-empty') || {}).textContent || null }; };
  return { open: w.classList.contains('is-open') && !w.hidden, paper: getComputedStyle(s).backgroundColor,
    title: w.querySelector('.make-title').textContent.trim(), h: Math.round(s.getBoundingClientRect().height * 10) / 10,
    pressed: (seg.querySelector('button[aria-pressed="true"]') || {}).textContent || null,
    pill: [...seg.querySelectorAll('button')].map(b => b.textContent.trim()),
    followers: list('followers'), following: list('following'),
    note: (w.querySelector('.lk-note') || {}).textContent || null,
    focus: document.activeElement ? (document.activeElement.textContent || '').trim() : null }; }"""

# A pill: where it is, its paint, which option is pressed, whether its tint is
# placed under that option, and each option's box, paint and reach (a press at
# its middle and 21px above and below lands on it: 44px to a finger).
PILL = r"""(sel) => { const seg = document.querySelector(sel); if (!seg || !seg.getClientRects().length) return null;
  const r = seg.getBoundingClientRect(), sl = seg.querySelector('.fo-slider'), sr = sl.getBoundingClientRect();
  const on = seg.querySelector('button[aria-pressed="true"]'), onr = on ? on.getBoundingClientRect() : null, cs = getComputedStyle(seg);
  return { top: r.top, bottom: r.bottom, left: r.left, w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
    bg: cs.backgroundColor, line: cs.borderTopColor, radius: cs.borderTopLeftRadius, placed: seg.hasAttribute('data-pill'),
    pressed: on ? on.textContent.trim() : null, tint: getComputedStyle(sl).backgroundColor, tintOp: +getComputedStyle(sl).opacity,
    under: !!onr && Math.abs(sr.left - onr.left) < 0.6 && Math.abs(sr.width - onr.width) < 0.6 && sr.height > 30,
    buttons: [...seg.querySelectorAll('button')].map(b => { const q = b.getBoundingClientRect(), mid = q.left + q.width / 2;
      const hit = d => { const e = document.elementFromPoint(mid, q.top + q.height / 2 + d); return !!e && (e === b || b.contains(e)); };
      const bs = getComputedStyle(b);
      return { words: b.textContent.trim(), w: Math.round(q.width * 100) / 100, h: Math.round(q.height * 100) / 100,
               color: bs.color, size: bs.fontSize, weight: bs.fontWeight, pressed: b.getAttribute('aria-pressed'),
               reach: hit(0) && hit(-21) && hit(21) }; }) }; }"""

# Home's feed, in order: each card (p: a post's id, s: a drawing's), and what
# Following says between them.
FEED = r"""() => { const f = document.querySelector('[data-feed]'); if (!f) return null;
  return [...f.children].map(e => e.matches('.post-card') ? (e.getAttribute('data-kind') === 's' ? 's:' + e.getAttribute('data-skribl')
                                                                                                 : 'p:' + e.getAttribute('data-post'))
    : e.matches('.fo-caught') ? 'caught' : e.matches('.fo-fresh') ? 'fresh' : e.matches('.fo-none') ? 'none' : e.tagName.toLowerCase()); }"""

# What Following says between its cards: the caught-up line (its check in the
# pen), the heading, and the kind card for somebody who follows nobody.
EXTRAS = r"""() => { const c = document.querySelector('.fo-caught'), h = document.querySelector('.fo-fresh'), n = document.querySelector('.fo-none');
  return { caught: c ? c.textContent.replace(/\s+/g, ' ').trim() : null,
    check: c ? !!c.querySelector('svg.pen-ic') && c.querySelectorAll('svg path[pathLength="1"]').length === 2 : null,
    fresh: h ? [h.tagName, h.textContent.trim()] : null,
    none: n ? { title: n.querySelector('h2').textContent.trim(), words: n.querySelector('p').textContent.replace(/\s+/g, ' ').trim(),
                btn: n.querySelector('.btn').textContent.trim(), href: new URL(n.querySelector('.btn').href).pathname } : null,
    more: (b => b && !b.hidden ? b.getAttribute('data-feed-next') : null)(document.querySelector('[data-feed-next]')) }; }"""

# The rows of Activity, each section's, with the small Follow on a follow's face.
ROWS = r"""() => [...document.querySelectorAll('.act-list')].map(ul => {
  const h = document.getElementById(ul.getAttribute('aria-labelledby'));
  return { sec: h ? h.textContent.trim() : null, rows: [...ul.querySelectorAll(':scope > li > a.act-row')].map(a => {
    const pic = a.querySelector('.act-pic'), badge = a.querySelector('.fo-badge'), disc = badge && badge.querySelector('.fo-disc');
    let d = null;
    if (disc) { const q = disc.getBoundingClientRect(), at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
                const p = disc.querySelector('svg path');
                d = { painted: !!at && badge.contains(at), w: Math.round(q.width), bg: getComputedStyle(disc).backgroundColor,
                      plus: p ? getComputedStyle(p).stroke : null, pen: !!disc.querySelector('svg.pen-ic') }; }
    return { say: a.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim(),
             when: (a.querySelector('.act-when') || {}).textContent || null, faces: a.querySelectorAll('.face-ring').length,
             follow: !!badge, disc: d, pic: getComputedStyle(pic).visibility,
             href: new URL(a.href).pathname + new URL(a.href).hash, isNew: a.classList.contains('is-new') }; }) }; })"""

# Whether a bell (the phone's top, or a desk's rail) wears a dot.
DOT = r"""(sel) => { const a = document.querySelector(sel); if (!a || !a.getClientRects().length) return 'no bell';
  return !!a.querySelector('.act-dot'); }"""

# Every animation frame for `ms` from now: the Follow button's paint and the
# boxes of it and what is beside it.
BFRAMES = r"""([ms]) => { window.__ff = []; const b = document.querySelector('.fo-btn'), t0 = performance.now();
  const share = document.querySelector('.prof-acts [data-share]'), more = document.querySelector('.prof-acts [data-person-menu]');
  const box = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; };
  const step = () => { const p = b.querySelector('.fo-on svg path'), pc = getComputedStyle(p);
    window.__ff.push({ t: Math.round(performance.now() - t0), b: box(b), share: share ? box(share) : null, more: more ? box(more) : null,
      bg: getComputedStyle(b).backgroundColor, off: +getComputedStyle(b.querySelector('.fo-off')).opacity,
      on: +getComputedStyle(b.querySelector('.fo-on')).opacity, dash: parseFloat(pc.strokeDashoffset), arr: pc.strokeDasharray });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# Every animation frame for `ms` from now: Home's pill's tint, the posts'
# opacity, which posts are there, and where the page is scrolled.
PFRAMES = r"""([ms]) => { window.__pf = []; const seg = document.querySelector('[data-home-pill]'), sl = seg.querySelector('.fo-slider');
  const swap = document.querySelector('[data-feed-swap]'), feed = document.querySelector('[data-feed]'), t0 = performance.now();
  const sig = () => [...feed.children].slice(0, 4).map(e => e.getAttribute('data-post') || e.className).join('|') + '#' + feed.children.length;
  const step = () => { const r = sl.getBoundingClientRect();
    window.__pf.push({ t: Math.round(performance.now() - t0), x: r.left, w: r.width, op: +getComputedStyle(swap).opacity, sig: sig(),
                       y: window.scrollY });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# Every animation frame for `ms` from now: the lists' pill's tint, each list's
# opacity, and the sheet's height.
LFRAMES = r"""([ms]) => { window.__lf = []; const w = document.getElementById('followsSheet'), sl = w.querySelector('.fo-slider');
  const s = w.querySelector('.make-sheet'), t0 = performance.now(), op = k => +getComputedStyle(w.querySelector('[data-list="' + k + '"]')).opacity;
  const step = () => { const r = sl.getBoundingClientRect(), q = s.getBoundingClientRect();
    window.__lf.push({ t: Math.round(performance.now() - t0), x: r.left, a: op('followers'), b: op('following'), top: q.top, h: q.height });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# Every word painted in `sel` (the page's roots by default) against what is
# painted behind it, every target and every text field (verify_sociallikes'
# census). A pill's option is 44px to a finger when a press at its middle and
# 21px above and below lands on it (its band reaches past its 36px).
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
    if (e.matches('input[type=radio]')) return;
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

# A pill's chosen option on its tint: the tint is a sibling under it, which the
# census's ground (its ancestors) cannot see, so it is laid over the track here.
PILL_INK = r"""(sel) => { const seg = document.querySelector(sel); if (!seg || !seg.getClientRects().length) return null;
  const KNOWN = /^(rgba?\(|color\(srgb )/;
  const rgba = s => { if (!KNOWN.test(s)) return null; const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; };
  let g = [255, 255, 255]; const layers = [];
  for (let n = seg; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor); if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
  for (let i = layers.length - 1; i >= 0; i--) g = over(layers[i], g);
  const tint = rgba(getComputedStyle(seg.querySelector('.fo-slider')).backgroundColor), on = seg.querySelector('button[aria-pressed="true"]');
  const off = seg.querySelector('button[aria-pressed="false"]');
  if (!tint || !on) return { unread: true };
  const t = over(tint, g);
  return { on: ratio(rgba(getComputedStyle(on).color), t), off: off ? ratio(rgba(getComputedStyle(off).color), g) : null }; }"""

# Each new mark's line against what is painted behind it: Follow's plus (white
# on the purple), Following's check, the caught-up check, Activity's small
# Follow (its disc on the page's ground, and its white plus on the disc). A
# colour in a form it cannot read is a red mark that says so, never a guess.
MARKS = r"""() => {
  const KNOWN = /^(rgba?\(|color\(srgb )/;
  const rgba = s => { if (!KNOWN.test(s)) return null;
    const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => c[3] >= 1 ? c : [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; };
  let unread = null;
  const read = s => { const c = rgba(s); if (!c && !unread) unread = s; return c; };
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = read(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const out = [];
  const put = (what, fg, g) => { out.push(unread || !fg ? { what, k: 0, unread: unread || 'no colour' } : { what, k: ratio(over(fg, g), g) }); unread = null; };
  const shown = e => !!e && e.getClientRects().length && +getComputedStyle(e).opacity > 0.99;
  document.querySelectorAll('.fo-btn').forEach(b => { if (!b.getClientRects().length) return;
    const f = b.classList.contains('is-following'), span = b.querySelector(f ? '.fo-on' : '.fo-off');
    if (!shown(span)) return;
    put(f ? 'check' : 'plus', read(getComputedStyle(span.querySelector('svg path')).stroke), ground(b)); });
  document.querySelectorAll('.fo-caught svg').forEach(s => { if (!s.getClientRects().length) return;
    put('caught', read(getComputedStyle(s.querySelector('path')).stroke), ground(s.parentElement)); });
  document.querySelectorAll('.fo-disc').forEach(d => { if (!d.getClientRects().length) return;
    put('disc', read(getComputedStyle(d).backgroundColor), ground(d.parentElement));
    put('disc plus', read(getComputedStyle(d.querySelector('svg path')).stroke), ground(d)); });
  return out; }"""


def colour(css):
    """A colour as Chrome writes it (rgb(), rgba(), or color(srgb ...) in 0 to 1): [r, g, b, a], or None."""
    m = [float(v) for v in re.findall(r"[\d.]+", css or "")]
    if not m or not (css.startswith("rgb") or css.startswith("color(srgb")):
        return None
    k = 255 if css.startswith("color(srgb") else 1
    return [m[0] * k, m[1] * k, m[2] * k, m[3] if len(m) > 3 else 1.0]


def steps_of(vals):
    """How a value changed over frames, as shares of the whole change: the
    frames it changed on, and its biggest step."""
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return {"frames": 0, "step": 0.0, "way": 0.0}
    way = abs(vals[-1] - vals[0])
    steps = [abs(b - a) for a, b in zip(vals, vals[1:])]
    if way < 1e-6:
        return {"frames": 0, "step": 0.0, "way": 0.0}
    return {"frames": len([s for s in steps if s / way > 0.005]), "step": round(max(steps) / way, 3), "way": round(way, 3)}


def colour_steps(cs):
    """steps_of() for colours: each frame's distance from the first, as a share of the last's."""
    cs = [colour(c) for c in cs]
    cs = [c for c in cs if c]
    if len(cs) < 2:
        return {"frames": 0, "step": 0.0, "way": 0.0}
    d = lambda a, b: math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)) + ((a[3] - b[3]) * 255) ** 2)
    whole = d(cs[0], cs[-1])
    if whole < 1e-6:
        return {"frames": 0, "step": 0.0, "way": 0.0}
    steps = [d(a, b) / whole for a, b in zip(cs, cs[1:])]
    return {"frames": len([s for s in steps if s > 0.005]), "step": round(max(steps), 3), "way": round(whole, 1)}


def moved(fs, keys=("b", "share", "more")):
    """The most any of these boxes moved or changed size from the first frame, in px."""
    most = 0.0
    for k in keys:
        boxes = [f[k] for f in fs if f.get(k)]
        if boxes:
            most = max(most, max(abs(x - y) for box in boxes for x, y in zip(box, boxes[0])))
    return round(most, 2)


def judge_button(fs, reduced=False, to=True):
    """A tap read on every frame (BFRAMES): nothing moved; the fill and the
    words changed over frames, none more than 35% of the way at once; following,
    the check drew over six frames or more, none more than 35% (under Reduce
    Motion there at once, with nothing to draw); unfollowing, it never un-drew
    while it could be seen."""
    fill, off, on = colour_steps([f["bg"] for f in fs]), steps_of([f["off"] for f in fs]), steps_of([f["on"] for f in fs])
    dash = steps_of([f["dash"] for f in fs])
    out = {"moved": moved(fs), "fill": fill, "off": off, "on": on, "dash": dash, "frames": len(fs),
           "arr": fs[-1]["arr"] if fs else None}
    ok = (out["moved"] == 0 and fill["way"] > 0 and fill["step"] <= 0.35 and fill["frames"] >= 4
          and off["way"] > 0.9 and off["step"] <= 0.35 and on["way"] > 0.9 and on["step"] <= 0.35)
    if to and not reduced:
        ok = ok and dash["way"] > 0.9 and dash["frames"] >= 6 and dash["step"] <= 0.35
    elif to and reduced:
        ok = ok and out["arr"] == "none"
    else:
        # Unfollowing: while the check can be seen (its word above 0.05), it is whole.
        ok = ok and all(f["dash"] < 0.01 or f["on"] <= 0.05 or f["arr"] == "none" for f in fs)
    out["ok"] = ok
    return out


def judge_pill(fs, reduced=False):
    """A tap on Home's pill read on every frame (PFRAMES): the tint glided (over
    eight frames or more, none more than 30% of the way), or under Reduce
    Motion was put there; the posts faded (no frame more than 35%), changed
    only while they could not be seen (0.05 or less), after the tint had
    started; the page did not scroll."""
    xs = [f["x"] for f in fs]
    glide = steps_of(xs)
    fade = steps_of([f["op"] for f in fs[:max(1, next((i for i, f in enumerate(fs) if f["op"] > 0.99 and i > 2
                                                      and any(g["op"] < 0.05 for g in fs[:i])), len(fs)))]])
    ops = [f["op"] for f in fs]
    biggest = round(max([abs(b - a) for a, b in zip(ops, ops[1:])] or [0]), 3)
    change = next((i for i in range(1, len(fs)) if fs[i]["sig"] != fs[i - 1]["sig"]), None)
    started = change is not None and any(abs(fs[j]["x"] - fs[0]["x"]) > 0.3 for j in range(0, change + 1))
    out = {"glide": glide, "fade_step": biggest, "seen_when_changed": fs[change]["op"] if change is not None else None,
           "started_first": started, "scrolled": round(max(abs(f["y"] - fs[0]["y"]) for f in fs), 2) if fs else None,
           "frames": len(fs), "back": fs[-1]["op"] if fs else None}
    ok = (change is not None and out["seen_when_changed"] <= 0.05 and biggest <= 0.35 and out["scrolled"] == 0
          and out["back"] > 0.99 and glide["way"] > 10)
    if reduced:
        ok = ok and glide["frames"] <= 1
    else:
        ok = ok and glide["frames"] >= 8 and glide["step"] <= 0.30 and started
    out["ok"] = ok
    del fade
    return out


LIGHT_PAGE, DARK_PAGE = "rgb(251, 252, 253)", "rgb(11, 13, 18)"
SHEET_PAPER = {"light": "rgb(243, 240, 255)", "dark": "rgb(23, 20, 42)"}
FILL, WHITE = "rgb(109, 76, 240)", "rgb(255, 255, 255)"
BTN2 = {"light": "rgb(255, 255, 255)", "dark": "rgba(167, 146, 255, 0.1)"}
CARD = {"light": "rgb(255, 255, 255)", "dark": "rgb(35, 30, 59)"}
CARD_LINE = {"light": "rgba(124, 92, 255, 0.34)", "dark": "rgba(167, 146, 255, 0.12)"}
PILL_ON = {"light": "rgb(63, 39, 168)", "dark": "rgb(212, 201, 255)"}
PILL_OFF = {"light": "rgb(63, 71, 86)", "dark": "rgb(183, 191, 204)"}
TINT = "rgba(124, 92, 255, 0.22)"



# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then goes
# because the code said so. And the reads, as the code sends them, planned by
# SQLite; and Home's Following, read twice with ten more cards in it.
PROBE = r"""
import json, sys
from datetime import datetime, timezone
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Follow, Person, Post, new_public_id
    from social.accounts import delete_person
    from social import follows as F
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    other = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[2])).scalar_one()
    stranger = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[4])).scalar_one()
    out = {"fk": fk}
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if "social_follows" in statement and statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        for name, call in (("followers", lambda: F.people(who, "followers")), ("following", lambda: F.people(who, "following")),
                           ("count", lambda: F.how_many(who, "followers")), ("is", lambda: F.is_following(who, other)),
                           ("circle", lambda: F.circle(who)), ("activity", lambda: F.of_me(who, frozenset({-1})))):
            rec.clear()
            call()
            calls[name] = list(rec)
    event.remove(db.engine, "before_cursor_execute", keep)
    plan = lambda st, params: [r[3] for r in db.session.connection().exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
    out["plans"] = {name: [x for st, params in sent for x in plan(st, params)] for name, sent in calls.items()}
    def home():
        seen = []
        def count(conn, cursor, statement, params, context, executemany):
            seen.append((statement, params))
        event.listen(db.engine, "before_cursor_execute", count)
        page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": sys.argv[3], "X-Forwarded-For": "10.250.1.1"})
        event.remove(db.engine, "before_cursor_execute", count)
        html = page.get_data(as_text=True)
        posts = [(st, pr) for st, pr in seen if "FROM social_posts" in st and "social_follows" in st]
        return {"reads": len(seen), "cards": html.count('class="post-card"'), "caught": "fo-caught" in html,
                "posts_plan": [x for st, pr in posts[:1] for x in plan(st, pr)]}
    # On this copy, only theirs: everybody else's posts gone and drawings put
    # out of the listing, so the cards below are the ones this probe makes.
    circle = [who.id] + [r[0] for r in db.session.execute(sa.select(Follow.followed_id).where(Follow.follower_id == who.id))]
    pubs = [r[0] for r in db.session.execute(sa.select(Person.public_id).where(Person.id.in_(circle)))]
    db.session.execute(sa.delete(Post).where(Post.person_id.notin_(circle)))
    db.session.execute(sa.text("update skribl_posts set visibility = 'unlisted' where user_id not in ("
                               + ", ".join(f"'{p}'" for p in pubs) + ")"))
    db.session.commit()
    home()                  # the process's first request does its one-time work
    out["home1"] = home()
    # Ten more cards, by somebody they don't follow (rows alone: a card whose
    # drawing is not there still renders), so Following's pages read the same.
    now = datetime.now(timezone.utc)
    for i in range(10):
        db.session.add(Post(public_id=new_public_id(8), person_id=stranger.id, words=f"probe {i}", skribl_id=f"probe{i}",
                            created_at=now))
    db.session.commit()
    out["home2"] = home()
    both = lambda: db.session.execute(sa.select(sa.func.count()).select_from(Follow).where(
        sa.or_(Follow.follower_id == who.id, Follow.followed_id == who.id))).scalar()
    before = both()
    delete_person(db.session, who.id)
    db.session.commit()
    out["deleted"] = [before, both()]
    print(json.dumps(out))
"""

with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the button, where it is: first in the row on somebody's page; never yours, never blocked; signed out too"):
        try:
            ann = someone(b, "ann", "Ann Lake")
            ben = someone(b, "ben", "Ben Lind")
            cyd = someone(b, "cyd", "Cyd Park")
            give_face(ben, 11)
            make_post(ben, "Section 1, Ben's")
            rows, btns = {}, {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, ann, screen=screen)
                go(pg, "/social/@ben")
                rows[screen], btns[screen] = pg.evaluate(ROW), pg.evaluate(FBTN)
                close_ctx(ctx, pg)
            ph, dk = btns["phone"], btns["desk"]
            check("on somebody's page Follow is first in the row, before Share and ⋯, on a phone and on a desk, where"
                  " the row sits beside their face",
                  [r["what"] for r in rows["phone"] or []] == ["follow", "share", "more"]
                  and [r["what"] for r in rows["desk"] or []] == ["follow", "share", "more"]
                  and dk and dk["face"] and dk["x"] > dk["face"]["right"]
                  and dk["face"]["top"] < dk["y"] < dk["face"]["bottom"],
                  f"phone {[r['what'] for r in rows['phone'] or []]}; desk {[r['what'] for r in rows['desk'] or []]};"
                  f" desk button at {dk and (round(dk['x']), round(dk['y']))}, face {dk and dk['face']}")
            check("it is the action: the action's purple with white on it and its drop, a plus drawn in our pen (two"
                  " strokes, each one unit long), 44px tall, painted where it stands, named 'Follow Ben Lind', not yet"
                  " following, its words Follow and Following",
                  all(x and x["bg"] == FILL and x["color"] == WHITE and x["shadow"] and x["plus"] and x["h"] == 44
                      and x["hit"] and x["label"] == "Follow Ben Lind" and not x["following"] and x["popup"] is None
                      and x["words"] == ["Follow", "Following"] and x["follow"] == "/social/@ben/follow"
                      for x in (ph, dk)),
                  json.dumps({k: (ph or {}).get(k) for k in ("bg", "color", "shadow", "plus", "h", "hit", "label", "following", "words")}))
            ctx, pg = browser_as(b, ann)
            go(pg, "/social/@ann")
            own_row, own_btn = pg.evaluate(ROW), pg.evaluate(FBTN)
            block(ann, "cyd")
            go(pg, "/social/@cyd")
            blocked_btn = pg.evaluate(FBTN)
            unblocked = pg.evaluate("() => !!document.querySelector('.prof-unblock')")
            go(pg, "/social/")
            on_cards = pg.evaluate("() => ({ n: document.querySelectorAll('.post-card').length,"
                                   " follow: document.querySelectorAll('.post-card .fo-btn, .post-card [data-follow]').length,"
                                   " words: /Follow back|Follows you/.test(document.body.innerText) })")
            close_ctx(ctx, pg)
            check("never on your own page (Edit profile leads the row there), never on somebody you blocked (Unblock is"
                  " there instead), and never on a card on Home: no 'Follow back', no 'Follows you'",
                  own_btn is None and [r["what"] for r in own_row or []][:1] == ["edit"] and blocked_btn is None and unblocked
                  and on_cards["n"] >= 1 and on_cards["follow"] == 0 and not on_cards["words"],
                  f"own {[r['what'] for r in own_row or []]}; blocked {blocked_btn and blocked_btn['label']}, unblock {unblocked};"
                  f" cards {on_cards}")
            ctx, pg = browser_as(b, None)
            go(pg, "/social/@ben")
            out = pg.evaluate(FBTN)
            close_ctx(ctx, pg)
            check("signed out it is there all the same, named the same, asking for a sheet rather than the site",
                  out and out["out"] and out["follow"] is None and out["label"] == "Follow Ben Lind" and out["bg"] == FILL,
                  json.dumps(out and {k: out[k] for k in ("out", "follow", "label", "bg")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "a tap follows, and asks once to stop: Following at once, kept; nothing moves; the sheet; following again"):
        try:
            dee = someone(b, "dee", "Dee Holt")
            eli = someone(b, "eli", "Eli Moss")
            ctx, pg = browser_as(b, dee)
            go(pg, "/social/@eli")
            row0, b0 = pg.evaluate(ROW), pg.evaluate(FBTN)
            tap_follow(pg, after=700)
            row1, b1 = pg.evaluate(ROW), pg.evaluate(FBTN)
            kept = follows_of("dee", "eli")
            go(pg, "/social/@eli")
            b2 = pg.evaluate(FBTN)
            check("a tap on Follow makes it Following at once, named 'Following Eli Moss', a tap now raising a sheet;"
                  " the site keeps it (one row, standing), and it is still so after a reload",
                  b1 and b1["following"] and b1["label"] == "Following Eli Moss" and b1["popup"] == "dialog"
                  and b1["bg"] == BTN2["light"] and b1["offOp"] == 0 and b1["onOp"] == 1 and b1["check"]
                  and len(kept) == 1 and kept[0][3] is None and b2 and b2["following"] and b2["dash"] == 0,
                  f"after {b1 and (b1['following'], b1['label'], b1['popup'], b1['bg'])}; kept {kept};"
                  f" reloaded {b2 and (b2['following'], b2['dash'])}")
            same = (row0 and row1 and [r["x"] for r in row0][1:] == [r["x"] for r in row1][1:]
                    and b0 and b1 and b0["w"] == b1["w"] == b0["wide"] and b0["onWider"])
            dctx, dpg = browser_as(b, dee, screen="desk")
            go(dpg, "/social/@eli")
            drow1, dw1 = dpg.evaluate(ROW), dpg.evaluate(FBTN)
            close_ctx(dctx, dpg)
            check("as wide as Following either way (both words in one place), so nothing beside it moves: Share and ⋯"
                  " where they were, on a phone and a desk",
                  same and dw1 and dw1["w"] == dw1["wide"] and [r["what"] for r in drow1] == ["follow", "share", "more"],
                  f"phone xs {row0 and [r['x'] for r in row0]} then {row1 and [r['x'] for r in row1]}; widths"
                  f" {b0 and b0['w']}/{b1 and b1['w']} (Following's {b0 and b0['wide']}); desk {dw1 and (dw1['w'], dw1['wide'])}")
            pg.locator(".fo-btn").tap()
            pg.wait_for_timeout(700)
            s = pg.evaluate(SHEET, "unfollowSheet")
            check("a tap on Following raises a small sheet, Make's own in its paper: 'Unfollow Eli?', 'You’ll still see"
                  " Eli’s drawings under Everyone. They aren’t told.', Keep following beside Unfollow, the big button"
                  " (the action), its focus on Keep following",
                  s and s["open"] and s["role"] == "dialog" and s["modal"] == "true" and s["paper"] == SHEET_PAPER["light"]
                  and s["title"] == "Unfollow Eli?"
                  and s["lede"] == "You’ll still see Eli’s drawings under Everyone. They aren’t told."
                  and [a[:2] for a in s["acts"]] == [["Keep following", False], ["Unfollow", True]]
                  and all(a[2] >= 52 for a in s["acts"]) and s["focus"] == "Keep following",
                  json.dumps(s))
            pg.locator("#unfollowSheet .post-sheet-acts [data-make-close]").tap()
            pg.wait_for_timeout(700)
            kept_on = pg.evaluate(FBTN)
            back = pg.evaluate("() => !!document.activeElement && document.activeElement.classList.contains('fo-btn')")
            check("Keep following puts it away and gives Following its focus back; still following",
                  kept_on and kept_on["following"] and back and follows_of("dee", "eli")[0][3] is None,
                  f"following {kept_on and kept_on['following']}, focus back {back}")
            first = follows_of("dee", "eli")[0][2]
            pg.locator(".fo-btn").tap()
            pg.wait_for_timeout(600)
            try:
                with pg.expect_response(lambda r: r.url.endswith("/follow") and r.request.method == "POST", timeout=8000):
                    pg.locator("#unfollowSheet [data-unfollow]").tap(timeout=5000)
            except Exception:  # noqa: BLE001
                pass
            pg.wait_for_timeout(700)
            gone = pg.evaluate(FBTN)
            ended = follows_of("dee", "eli")
            go(pg, "/social/@eli")
            gone2 = pg.evaluate(FBTN)
            check("Unfollow puts it away and the button back to Follow (named 'Follow Eli Moss', the action's purple);"
                  " the site keeps that it ended, and after a reload it is Follow",
                  gone and not gone["following"] and gone["label"] == "Follow Eli Moss" and gone["bg"] == FILL
                  and gone["popup"] is None and len(ended) == 1 and ended[0][3] is not None
                  and gone2 and not gone2["following"],
                  f"{gone and (gone['following'], gone['label'], gone['bg'])}; kept {ended}; reloaded {gone2 and gone2['following']}")
            tap_follow(pg, after=500)
            again = follows_of("dee", "eli")
            close_ctx(ctx, pg)
            check("following again keeps the first time (one row, standing again, the same created_at), so Activity has"
                  " nothing new to say",
                  len(again) == 1 and again[0][3] is None and again[0][2] == first, f"{again}; first {first}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "who may follow: refused and nothing kept; the limit; a refusal in the page puts the button back"):
        try:
            fay = someone(b, "fay", "Fay Ito")
            gil = someone(b, "gil", "Gil Ruiz")
            hal = someone(b, "hal", "Hal Ames")
            ivy = someone(b, "ivy", "Ivy Cole")
            s1, j1 = follow(None, "gil")
            c = fay.client()
            c.get("/social/@gil")
            s2, j2 = c.post_json("/social/@gil/follow", {"following": True}, token="")
            s3, j3 = follow(fay, "gil", origin="https://elsewhere.example")
            check("signed out, without the page's token, or from another origin: refused (401, 403), nothing kept",
                  s1 == 401 and j1.get("error") == "signed_out" and s2 == 403 and j2.get("error") == "stale"
                  and s3 == 403 and j3.get("error") == "stale" and follows_of("fay") == [],
                  f"{s1} {j1}; {s2} {j2}; {s3} {j3}; kept {follows_of('fay')}")
            s4, j4 = follow(fay, "fay")
            s5, j5 = follow(fay, "nobody_here")
            block(hal, "fay")
            s6, j6 = follow(fay, "hal")
            s7, j7 = follow(hal, "fay")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'ivy'")
            s8, j8 = follow(fay, "ivy")
            check("yourself, nobody by that name, a block either way, somebody taken down: 'gone' (404), nothing kept",
                  all(st == 404 and j.get("error") == "gone" for st, j in ((s4, j4), (s5, j5), (s6, j6), (s7, j7), (s8, j8)))
                  and follows_of("fay") == [] and follows_of("hal") == [],
                  f"self {s4}; nobody {s5}; blocked {s6}/{s7}; taken down {s8}; kept {follows_of('fay') + follows_of('hal')}")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'gil'")
            s9, j9 = follow(gil, "fay")
            db_write("update social_people set taken_down_at = null where handle_key = 'gil'")
            s10, j10 = follow(fay, "gil", raw={"following": "yes"})
            s11, j11 = follow(fay, "gil", raw=["following"])
            check("somebody taken down follows nobody (403, taken_down); a body that is not a yes or a no is refused"
                  " (400); nothing kept",
                  s9 == 403 and j9.get("error") == "taken_down" and s10 == 400 and s11 == 400
                  and follows_of("gil") == [] and follows_of("fay") == [],
                  f"{s9} {j9}; {s10} {j10}; {s11}")
            jon = someone(b, "jon", "Jon Park")
            cj = jon.client()
            cj.get("/social/@gil")
            got = [cj.post_json("/social/@gil/follow", {"following": i % 2 == 0})[0] for i in range(61)]
            check("the limit: sixty follows and unfollows an hour a person, the sixty-first refused (429), and the last"
                  " kept is the sixtieth's",
                  got[:60] == [200] * 60 and got[60] == 429 and len(follows_of("jon", "gil")) == 1
                  and follows_of("jon", "gil")[0][3] is not None,
                  f"{got.count(200)} kept, then {got[60:]}; row {follows_of('jon', 'gil')}")
            ctx, pg = browser_as(b, fay)
            go(pg, "/social/@gil")
            block(gil, "fay")
            tap_follow(pg, after=700)
            back = pg.evaluate(FBTN)
            said = pg.evaluate("() => { const s = document.querySelector('[data-say]'); return s && !s.hidden ? s.textContent : null; }")
            close_ctx(ctx, pg)
            check("a refusal in the page puts the button back (Follow, named so) and says why, kindly: 'They aren’t"
                  " here anymore. Reload the page to see what’s new.'",
                  back and not back["following"] and back["label"] == "Follow Gil Ruiz"
                  and said == "They aren’t here anymore. Reload the page to see what’s new." and follows_of("fay") == [],
                  f"{back and (back['following'], back['label'])}; said {said!r}")
            k1, h1 = pick(None, "everyone", page="/social/@fay")
            k2, h2 = pick(fay, "everyone", token="")
            k3, h3 = pick(fay, "nobody")
            k4, h4 = pick(fay, "everyone")
            kept_pick = db("select home_feed from social_people where handle_key = 'fay'")
            check("Home's pick: signed out (401), without the token (403) or anything but following or everyone (400)"
                  " refused; a good one kept for the account",
                  k1 == 401 and k2 == 403 and k3 == 400 and k4 == 200 and h4.get("show") == "everyone"
                  and kept_pick == [("everyone",)],
                  f"{k1} {k2} {k3} {k4} {h4}; kept {kept_pick}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "yours alone: nothing on somebody else's page; your own line, in names; counted by the viewer"):
        try:
            kim = someone(b, "kim", "Kim Bryn")
            lou = someone(b, "lou", "Lou Dale")
            mae = someone(b, "mae", "Mae Fox")
            ned = someone(b, "ned", "Ned Gray")
            oli = someone(b, "oli", "Oli Hart")
            for who in (lou, mae, ned, oli):
                give_face(who, 40 + len(who.handle) + ord(who.handle[0]))
            for who in (lou, mae, ned, oli):
                follow(who, "kim")
                time.sleep(0.02)
            follow(kim, "lou")
            st, page = lou.client().get("/social/@kim")
            stn, pagen = Client().get("/social/@kim")
            leaks = [w for w in ("Followed by", "You follow", "followsSheet", "data-follows-open", "fo-by", "@mae", "@ned",
                                 "@oli", "Mae Fox", "Ned Gray", "Oli Hart", "follower") if w in page or w in pagen]
            check("on somebody else's page nothing of follows but Follow or Following: no line, no count, no list, none"
                  " of who follows them, not in the page and not in its source, signed in or out",
                  st == 200 and stn == 200 and not leaks and "Following Kim Bryn" in page and "Follow Kim Bryn" in pagen,
                  f"{st}/{stn}; found {leaks}")
            ctx, pg = browser_as(b, kim)
            go(pg, "/social/@kim")
            line4 = pg.evaluate(LINE)
            faces = {h: f"/social/s/{db('select face_id from social_people where handle_key = ?', (h,))[0][0]}/still"
                     for h in ("oli", "ned", "mae")}
            check("your own page says who, in names, the twin of 'Liked by…': 'Followed by Oli, Ned and 2 others',"
                  " newest first, with the newest three faces, a 44px way to the lists",
                  line4 and line4["words"] == "Followed by Oli, Ned and 2 others" and line4["tab"] == "followers"
                  and len(line4["faces"]) == 3 and line4["h"] >= 44 and line4["hit"] and line4["popup"] == "dialog",
                  json.dumps(line4))
            check("...the faces are theirs, newest first",
                  line4 and [f.rsplit("/", 2)[-2] if f != "blank" else f for f in line4["faces"]]
                  == [faces[h].rsplit("/", 2)[-2] for h in ("oli", "ned", "mae")],
                  f"{line4 and line4['faces']} want {[faces[h] for h in ('oli', 'ned', 'mae')]}")
            follow(ned, "kim", False)
            follow(oli, "kim", False)
            go(pg, "/social/@kim")
            three = pg.evaluate(LINE)
            follow(mae, "kim", False)
            go(pg, "/social/@kim")
            two = pg.evaluate(LINE)
            check("every name up to three, else two and how many more: 'Followed by Mae and Lou', then 'Followed by Lou'",
                  three and three["words"] == "Followed by Mae and Lou" and two and two["words"] == "Followed by Lou",
                  f"{three and three['words']}; {two and two['words']}")
            follow(lou, "kim", False)
            follow(kim, "mae")
            go(pg, "/social/@kim")
            mine = pg.evaluate(LINE)
            for who in ("lou", "mae"):
                follow(kim, who, False)
            go(pg, "/social/@kim")
            nothing = pg.evaluate(LINE)
            sheet_there = pg.evaluate("() => !!document.getElementById('followsSheet')")
            check("before anybody follows you it says whom you follow ('You follow Mae and Lou'), and with nobody either"
                  " way there is no line at all, so nothing ever says zero",
                  mine and mine["words"] == "You follow Mae and Lou" and mine["tab"] == "following"
                  and nothing is None and not sheet_there,
                  f"{mine and mine['words']}; then {nothing}; sheet {sheet_there}")
            for who in (lou, mae, ned):
                follow(who, "kim")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'ned'")
            go(pg, "/social/@kim")
            counted = pg.evaluate(LINE)
            pg.locator("[data-follows-open]").tap()
            pg.wait_for_timeout(700)
            listed = pg.evaluate(LISTS)
            db_write("update social_people set taken_down_at = null where handle_key = 'ned'")
            close_ctx(ctx, pg)
            check("counted by the viewer: somebody taken down is in no line and no list ('Followed by Mae and Lou', Ned"
                  " left out)",
                  counted and counted["words"] == "Followed by Mae and Lou" and listed
                  and [r["handle"] for r in listed["followers"]["rows"]] == ["@mae", "@lou"],
                  f"{counted and counted['words']}; listed {listed and [r['handle'] for r in listed['followers']['rows']]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "the lists: Make's sheet, the one pill, newest first with when; a row to their page; #followers"):
        try:
            pia = someone(b, "pia", "Pia Lund")
            qua = someone(b, "qua", "Qua Nye")
            rik = someone(b, "rik", "Rik Oto")
            sol = someone(b, "sol", "Sol Penn")
            for who in (qua, rik, sol):
                follow(who, "pia")
                time.sleep(0.02)
            follow(pia, "rik")
            ctx, pg = browser_as(b, pia)
            go(pg, "/social/@pia")
            pg.locator("[data-follows-open]").tap()
            pg.wait_for_timeout(800)
            l5 = pg.evaluate(LISTS)
            pill5 = pg.evaluate(PILL, "#followsSheet .fo-seg")
            check("the line opens Make's own sheet in its paper (--menu-paper), titled with your handle: the one pill,"
                  " Followers | Following, on Followers, its tint under it; the people on one card",
                  l5 and l5["open"] and l5["paper"] == SHEET_PAPER["light"] and l5["title"] == "@pia"
                  and l5["pill"] == ["Followers", "Following"] and l5["pressed"] == "Followers"
                  and l5["followers"]["shown"] and not l5["following"]["shown"] and l5["followers"]["card"] == CARD["light"]
                  and pill5 and pill5["under"] and pill5["placed"],
                  json.dumps({k: (l5 or {}).get(k) for k in ("open", "paper", "title", "pill", "pressed")})
                  + f"; under {pill5 and pill5['under']}")
            rows = (l5 or {}).get("followers", {}).get("rows", [])
            check("who follows you, newest first: face, name, @handle and when ('now', in your own time), each a way"
                  " to their page; and under them 'Only you can see who follows you, and who you follow.'",
                  [r["handle"] for r in rows] == ["@sol", "@rik", "@qua"] and [r["name"] for r in rows] == ["Sol Penn", "Rik Oto", "Qua Nye"]
                  and all(r["when"] == "now" and r["iso"] for r in rows) and [r["href"] for r in rows] == ["/social/@sol", "/social/@rik", "/social/@qua"]
                  and l5["note"] == "Only you can see who follows you, and who you follow.",
                  json.dumps(rows) + f"; note {l5 and l5['note']!r}")
            h0 = l5 and l5["h"]
            pg.locator("#followsSheet .fo-seg button[data-tab=following]").tap()
            pg.wait_for_timeout(700)
            l6 = pg.evaluate(LISTS)
            check("Following shows whom you follow, the pill on it, the other list put away, and the sheet keeps its"
                  " height", l6 and l6["pressed"] == "Following" and l6["following"]["shown"] and not l6["followers"]["shown"]
                  and [r["handle"] for r in l6["following"]["rows"]] == ["@rik"] and l6["h"] == h0,
                  f"{l6 and (l6['pressed'], [r['handle'] for r in l6['following']['rows']], l6['h'])} from {h0}")
            tap_to(pg, pg.locator("#followsSheet [data-list=following] .lk-row").first)
            landed = urllib.parse.urlparse(pg.url).path
            check("a row opens their page (where you unfollow, too)", landed == "/social/@rik", landed)
            go(pg, "/social/@pia#followers", wait=900)
            at_f = pg.evaluate(LISTS)
            go(pg, "/social/")
            go(pg, "/social/@pia#following", wait=900)
            at_g = pg.evaluate(LISTS)
            close_ctx(ctx, pg)
            check("opened at #followers (a follow row in Activity) the sheet rises on Followers; at #following, on"
                  " Following",
                  at_f and at_f["open"] and at_f["pressed"] == "Followers" and at_f["followers"]["shown"]
                  and at_g and at_g["open"] and at_g["pressed"] == "Following" and at_g["following"]["shown"],
                  f"{at_f and (at_f['open'], at_f['pressed'])}; {at_g and (at_g['open'], at_g['pressed'])}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "kind, never jumpy: the button fades and draws, nothing moves; unfollowing fades; Reduce Motion fades"):
        try:
            tom = someone(b, "tom", "Tom Quin")
            uma = someone(b, "uma", "Uma Roth")
            got = {}
            for scheme in ("light", "dark"):
                for reduced in (False, True):
                    tag = f"{scheme}{' reduced' if reduced else ''}"
                    follow(tom, "uma", False)
                    ctx, pg = browser_as(b, tom, scheme=scheme, reduced=reduced)
                    go(pg, "/social/@uma", wait=500)
                    pg.evaluate(BFRAMES, [900])
                    pg.locator(".fo-btn").tap()
                    pg.wait_for_timeout(1300)
                    on = judge_button(pg.evaluate("() => window.__ff"), reduced=reduced, to=True)
                    pg.locator(".fo-btn").tap()
                    pg.wait_for_timeout(800)
                    pg.evaluate(BFRAMES, [900])
                    pg.locator("#unfollowSheet [data-unfollow]").tap()
                    pg.wait_for_timeout(1300)
                    off = judge_button(pg.evaluate("() => window.__ff"), reduced=reduced, to=False)
                    got[tag] = (on, off)
                    close_ctx(ctx, pg)
            brief = {t: [{k: v for k, v in x.items() if k in ("moved", "fill", "on", "dash", "frames", "arr", "ok")} for x in pair]
                     for t, pair in got.items()}
            check("following, read on every frame (light and dark): nothing moves, not the button and not Share or ⋯;"
                  " the purple fades to the quiet button and the words cross over, no frame doing more than 35% of either;"
                  " the check draws itself in our pen over six frames or more, no frame more than 35% of it",
                  all(got[t][0]["ok"] for t in ("light", "dark")), json.dumps({t: brief[t][0] for t in ("light", "dark")}))
            check("unfollowing fades back the same way, nothing moving and nothing un-drawing while it can be seen",
                  all(got[t][1]["ok"] for t in ("light", "dark")), json.dumps({t: brief[t][1] for t in ("light", "dark")}))
            check("under Reduce Motion it only fades, both ways: the check there at once, nothing drawn, nothing moved",
                  all(got[t][0]["ok"] and got[t][1]["ok"] for t in ("light reduced", "dark reduced")),
                  json.dumps({t: brief[t] for t in ("light reduced", "dark reduced")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "Home's pill: under the composer, the Gallery's own; Everyone, then Following; the pick kept; the switch read on every frame"):
        try:
            vic = someone(b, "vic", "Vic Bell")
            wes = someone(b, "wes", "Wes Cruz")
            xia = someone(b, "xia", "Xia Dunn")
            for i in range(3):
                make_post(wes, f"Section 7, Wes's {i}", seed=70 + i)
                make_post(xia, f"Section 7, Xia's {i}", seed=80 + i)
            ctx, pg = browser_as(b, vic)
            go(pg, "/social/")
            before = pg.evaluate(PILL, "[data-home-pill]")
            follow(vic, "wes")
            go(pg, "/social/")
            after = pg.evaluate(PILL, "[data-home-pill]")
            where = pg.evaluate("""() => { const c = document.querySelector('[data-composer]').getBoundingClientRect(),
              p = document.querySelector('[data-home-pill]').getBoundingClientRect(), f = document.querySelector('[data-feed] > *').getBoundingClientRect();
              return { composer: c.bottom, top: p.top, bottom: p.bottom, first: f.top }; }""")
            check("Home opens on Everyone before you follow anybody, and on Following once you do",
                  before and before["pressed"] == "Everyone" and after and after["pressed"] == "Following",
                  f"{before and before['pressed']} then {after and after['pressed']}")
            check("the pill sits under the composer, over the posts: the Gallery's New / Hot value for value (44px, the"
                  " card's ground and line, 12px round, the tint rgba(124, 92, 255, 0.22) under the chosen one, 13px words"
                  " at 600, the chosen one's ink and the other's), each option 44px to a finger",
                  after and where["composer"] < where["top"] and where["bottom"] < where["first"]
                  and after["h"] == 44 and after["bg"] == CARD["light"] and after["line"] == CARD_LINE["light"]
                  and after["radius"] == "12px" and after["tint"] == TINT and after["tintOp"] == 1 and after["under"]
                  and [x["words"] for x in after["buttons"]] == ["Following", "Everyone"]
                  and all(x["size"] == "13px" and x["weight"] == "600" and x["reach"] and x["w"] >= 44 for x in after["buttons"])
                  and after["buttons"][0]["color"] == PILL_ON["light"] and after["buttons"][1]["color"] == PILL_OFF["light"],
                  json.dumps({"where": where, "pill": after}))
            pg.locator("[data-home-pill] button[data-show=everyone]").tap()
            pg.wait_for_timeout(1200)
            kept = db("select home_feed from social_people where handle_key = 'vic'")
            showing = pg.evaluate(FEED)
            dctx, dpg = browser_as(b, vic, screen="desk")
            go(dpg, "/social/")
            there = dpg.evaluate(PILL, "[data-home-pill]")
            close_ctx(dctx, dpg)
            pg.locator("[data-home-pill] button[data-show=following]").tap()
            pg.wait_for_timeout(1200)
            kept2 = db("select home_feed from social_people where handle_key = 'vic'")
            close_ctx(ctx, pg)
            check("your pick is kept for the account: a tap on Everyone shows everyone's and keeps it, so another device"
                  " (a desk) opens Home on Everyone; a tap on Following keeps that",
                  kept == [("everyone",)] and there and there["pressed"] == "Everyone" and "caught" not in (showing or [])
                  and kept2 == [("following",)],
                  f"kept {kept} then {kept2}; the desk's {there and there['pressed']}; shown {showing and showing[:3]}")
            got = {}
            for scheme in ("light", "dark"):
                for reduced in (False, True):
                    tag = f"{scheme}{' reduced' if reduced else ''}"
                    pick(vic, "following")
                    ctx, pg = browser_as(b, vic, scheme=scheme, reduced=reduced)
                    go(pg, "/social/", wait=600)
                    y = pg.evaluate("() => { const p = document.querySelector('[data-home-pill]'); const y = Math.max(0, p.getBoundingClientRect().top + scrollY - 160); scrollTo(0, y); return scrollY; }")
                    pg.wait_for_timeout(300)
                    pg.evaluate(PFRAMES, [1500])
                    pg.locator("[data-home-pill] button[data-show=everyone]").tap()
                    pg.wait_for_timeout(1900)
                    got[tag] = dict(judge_pill(pg.evaluate("() => window.__pf"), reduced=reduced), at=y)
                    close_ctx(ctx, pg)
            check("the switch, read on every frame from the tap (light and dark, the page scrolled down to the pill): the"
                  " pill glides (eight frames or more, none more than 30% of the way) and starts before the posts change;"
                  " the posts fade (none more than 35%), change only while they can't be seen (0.05 or less), and fade"
                  " back; the page doesn't scroll",
                  all(got[t]["ok"] and got[t]["at"] > 0 for t in ("light", "dark")),
                  json.dumps({t: got[t] for t in ("light", "dark")}))
            check("under Reduce Motion the pill is put there, as the site's pills are, and the posts only fade, changing"
                  " while unseen; the page doesn't scroll",
                  all(got[t]["ok"] for t in ("light reduced", "dark reduced")),
                  json.dumps({t: got[t] for t in ("light reduced", "dark reduced")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "Following never runs out: yours and theirs, newest first; caught up; Fresh from everyone; Load more; nobody yet"):
        try:
            yan = someone(b, "yan", "Yan Egan")
            zed = someone(b, "zed", "Zed Ford")
            abe = someone(b, "abe", "Abe Gold")
            cas = someone(b, "cas", "Cas Hale")
            seq = []
            for who, kind, i in ((cas, "p", 0), (zed, "p", 0), (abe, "p", 0), (cas, "s", 0), (zed, "s", 0), (yan, "p", 0),
                                 (cas, "p", 1), (zed, "p", 1)):
                if kind == "p":
                    seq.append((who.handle, "p:" + (make_post(who, f"Section 8, {who.handle}'s {i}", seed=90 + i) or "")))
                else:
                    seq.append((who.handle, "s:" + (make_drawing(who, f"Section 8, {who.handle}'s drawing", seed=95 + i) or "")))
                time.sleep(0.03)
            follow(yan, "zed")
            follow(yan, "abe")
            ctx, pg = browser_as(b, yan)
            go(pg, "/social/", wait=600)
            feed8 = pg.evaluate(FEED)
            ex8 = pg.evaluate(EXTRAS)
            newest = list(reversed(seq))
            circle = [k for h, k in newest if h in ("yan", "zed", "abe")]
            rest = [k for h, k in newest if h == "cas"]
            mine = [x for x in (feed8 or []) if x in circle]
            check("Following is the people you follow and you, posts and drawings alike, newest first, nothing else"
                  " before the line",
                  feed8 and feed8[:len(circle)] == circle and mine == circle,
                  f"got {feed8}; want {circle} then {rest}")
            check("then 'You’re caught up with the people you follow.' with its check drawn in our pen, then 'Fresh from"
                  " everyone' (a heading) and everybody else's, newest first, nothing twice",
                  feed8 and feed8[len(circle):len(circle) + 2] == ["caught", "fresh"]
                  and [x for x in feed8[len(circle) + 2:] if x.startswith(("p:", "s:"))][:len(rest)] == rest
                  and len(feed8) == len(set(feed8)) and ex8["caught"] == "You’re caught up with the people you follow."
                  and ex8["check"] and ex8["fresh"] == ["H2", "Fresh from everyone"],
                  f"{feed8}; {ex8}")
            pg.locator("[data-home-pill] button[data-show=everyone]").tap()
            pg.wait_for_timeout(1300)
            every = pg.evaluate(FEED)
            check("Everyone is everyone's, newest first, as Home was",
                  every and [x for x in every if x in circle + rest] == [k for _, k in newest] and "caught" not in every,
                  f"{every}")
            pick(yan, "following")
            for i in range(21):
                make_post(zed, f"Section 8, Zed's page {i}", seed=200 + i)
            go(pg, "/social/", wait=600)
            first_page = pg.evaluate(FEED)
            cursor = pg.evaluate(EXTRAS)["more"]
            for _ in range(4):
                nxt = pg.evaluate("() => { const b = document.querySelector('[data-feed-next]'); return !!b && !b.hidden; }")
                if not nxt:
                    break
                n0 = pg.evaluate("() => document.querySelectorAll('[data-feed] > *').length")
                pg.locator("[data-feed-next]").click()
                pg.wait_for_function("(n) => document.querySelectorAll('[data-feed] > *').length > n", arg=n0, timeout=15000)
                pg.wait_for_timeout(400)
            walked = pg.evaluate(FEED)
            zeds = [x for x in walked if x.startswith(("p:", "s:")) and x in circle or x not in rest]
            cut = walked.index("caught") if "caught" in walked else -1
            check("Load more carries on: a first page of twenty of theirs (its cursor Following's own), then the rest of"
                  " theirs, then the line and everybody else's, nothing twice and nothing missed",
                  len([x for x in first_page if x.startswith(("p:", "s:"))]) == 20 and "caught" not in first_page
                  and (cursor or "").startswith("f.") and cut > 20 and walked[cut + 1] == "fresh"
                  and all(x in walked[cut:] for x in rest) and all(x in walked[:cut] for x in circle)
                  and len(walked) == len(set(walked)),
                  f"first {len(first_page)} (cursor {cursor and cursor[:2]}); walked {len(walked)}, line at {cut}; {walked[cut - 1:cut + 4] if cut > 0 else walked[-4:]}")
            del zeds
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'abe'")
            go(pg, "/social/", wait=500)
            down = pg.evaluate(FEED)
            db_write("update social_people set taken_down_at = null where handle_key = 'abe'")
            close_ctx(ctx, pg)
            abes = [k for h, k in seq if h == "abe"]
            check("somebody taken down is in nobody's Following (nor anywhere on Home)",
                  down and not any(a in down for a in abes), f"{abes} in {down[:6] if down else down}")
            dan = someone(b, "dan", "Dan Ivey")
            dp = make_post(dan, "Section 8, Dan's first")
            pick(dan, "following")
            ctx, pg = browser_as(b, dan)
            go(pg, "/social/", wait=600)
            lone = pg.evaluate(FEED)
            ex_l = pg.evaluate(EXTRAS)
            pill_l = pg.evaluate(PILL, "[data-home-pill]")
            close_ctx(ctx, pg)
            check("somebody who follows nobody and is on Following sees a kind card, 'You’re not following anyone yet',"
                  " how, and Look around (to Explore), then Fresh from everyone and everyone's, their own among them",
                  lone and lone[:2] == ["none", "fresh"] and ("p:" + (dp or "")) in lone and pill_l["pressed"] == "Following"
                  and ex_l["none"] == {"title": "You’re not following anyone yet",
                                       "words": "Tap Follow on someone’s page, and their new drawings show up here first. Until then, here’s everyone’s.",
                                       "btn": "Look around", "href": "/social/explore"},
                  f"{lone and lone[:4]}; {ex_l['none']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "Activity: who followed you, grouped since you last looked; a day a row under Earlier; never the bell's dot"):
        try:
            ivo = someone(b, "ivo", "Ivo Jung")
            jai = someone(b, "jai", "Jai Kerr")
            kat = someone(b, "kat", "Kat Lowe")
            lev = someone(b, "lev", "Lev Marr")
            give_face(jai, 91)
            give_face(lev, 93)
            ip = make_post(ivo, "Section 9, Ivo's")
            for who in (jai, kat, lev):
                follow(who, "ivo")
                time.sleep(0.03)
            ctx, pg = browser_as(b, ivo)
            go(pg, "/social/")
            bell = pg.evaluate(DOT, ".top-bell")
            go(pg, "/social/activity")
            first = pg.evaluate(ROWS)
            row = next((r for sec in first for r in sec["rows"] if r["follow"]), None)
            check("a follow is a row like a like's, under New: 'Lev and 2 others followed you', the newest face in front,"
                  " wearing a small Follow (the action's purple, a white plus in our pen, painted), no picture; several"
                  " open who follows you (your own page, #followers)",
                  first and first[0]["sec"] == "New" and row and row["say"] == "Lev and 2 others followed you"
                  and row["isNew"] and row["faces"] == 2 and row["disc"] and row["disc"]["painted"] and row["disc"]["pen"]
                  and row["disc"]["bg"] == FILL and row["disc"]["plus"] == WHITE and row["disc"]["w"] == 18
                  and row["pic"] == "hidden" and row["href"] == "/social/@ivo#followers",
                  json.dumps(first))
            check("follows never light the bell's dot: three new follows, and the bell is quiet",
                  bell is False, f"dot {bell}")
            mia = someone(b, "mia", "Mia Nash")
            follow(mia, "ivo")
            go(pg, "/social/activity")
            one = pg.evaluate(ROWS)
            nel = someone(b, "nel", "Nel Ortiz")
            ole = someone(b, "ole", "Ole Pratt")
            follow(nel, "ivo")
            time.sleep(0.03)
            follow(ole, "ivo")
            go(pg, "/social/activity")
            two = pg.evaluate(ROWS)
            one_new = [r for sec in one if sec["sec"] == "New" for r in sec["rows"]]
            two_new = [r for sec in two if sec["sec"] == "New" for r in sec["rows"]]
            check("since you last looked: one follow says one name and opens their page ('Mia followed you', to @mia);"
                  " two say both ('Ole and Nel followed you'); what you saw before sits under Earlier",
                  [(r["say"], r["href"]) for r in one_new] == [("Mia followed you", "/social/@mia")]
                  and [r["say"] for r in two_new] == ["Ole and Nel followed you"]
                  and any(sec["sec"] == "Earlier" for sec in two),
                  f"one {[(r['say'], r['href']) for r in one_new]}; two {[r['say'] for r in two_new]}")
            ago = lambda h: (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S.%f")
            for h, hours in (("jai", 2), ("kat", 20), ("lev", 72), ("mia", 100), ("nel", 101), ("ole", 101.5)):
                db_write("update social_follows set created_at = ? where follower_id = (select id from social_people"
                         " where handle_key = ?) and followed_id = (select id from social_people where handle_key = 'ivo')",
                         (ago(hours), h))
            go(pg, "/social/activity")
            earlier = [r["say"] for sec in pg.evaluate(ROWS) if sec["sec"] == "Earlier" for r in sec["rows"] if r["follow"]]
            check("under Earlier a day's follows stay one row (those within a day of the newest of them), newest first:"
                  " 'Jai and Kat', 'Lev', 'Mia and 2 others'",
                  earlier == ["Jai and Kat followed you", "Lev followed you", "Mia and 2 others followed you"], f"{earlier}")
            follow(lev, "ivo", False)
            follow(lev, "ivo")
            follow(nel, "ivo", False)
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'kat'")
            go(pg, "/social/activity")
            after = pg.evaluate(ROWS)
            db_write("update social_people set taken_down_at = null where handle_key = 'kat'")
            new_after = [r["say"] for sec in after if sec["sec"] == "New" for r in sec["rows"] if r["follow"]]
            all_after = [r["say"] for sec in after for r in sec["rows"] if r["follow"]]
            check("following again is never new twice (Lev's row stays under Earlier, at its first time); a follow taken"
                  " back has no row (Nel), and nobody hidden is in one (Kat, taken down)",
                  new_after == [] and all_after == ["Jai followed you", "Lev followed you", "Mia and Ole followed you"],
                  f"new {new_after}; all {all_after}")
            jay = make_post(jai, "Section 9, Jai's, a comment to come")
            del jay
            cm = jai.client()
            cm.get(f"/social/p/{ip}")
            cst, _ = cm.post_json(f"/social/p/{ip}/comments", {"words": "Love this one."})
            go(pg, "/social/")
            lit = pg.evaluate(DOT, ".top-bell")
            check("...while a comment, as before, does light it (the bell can say something new)",
                  cst in (200, 201) and lit is True, f"comment {cst}; dot {lit}")
            go(pg, "/social/activity")
            tap_to(pg, pg.locator("a.act-row[href='/social/@ivo#followers']").first)
            pg.wait_for_timeout(900)
            landed = (urllib.parse.urlparse(pg.url).path, pg.evaluate(LISTS))
            go(pg, "/social/activity")
            tap_to(pg, pg.locator("a.act-row[href='/social/@lev']").first)
            one_to = urllib.parse.urlparse(pg.url).path
            sub = None
            go(pg, "/social/activity")
            dctx, dpg = browser_as(b, ivo, screen="desk")
            go(dpg, "/social/activity")
            sub = dpg.evaluate("() => (document.querySelector('.act-head .page-sub') || {}).textContent || null")
            close_ctx(dctx, dpg)
            close_ctx(ctx, pg)
            check("a row for several lands on your own page with who follows you open, on Followers; a row for one,"
                  " on their page",
                  landed[0] == "/social/@ivo" and landed[1] and landed[1]["open"] and landed[1]["pressed"] == "Followers"
                  and one_to == "/social/@lev",
                  f"several to {landed[0]} open {landed[1] and (landed[1]['open'], landed[1]['pressed'])}; one to {one_to}")
            quiet = someone(b, "ray", "Ray Quist")
            qctx, qpg = browser_as(b, quiet, screen="desk")
            go(qpg, "/social/activity")
            empty = qpg.evaluate("() => (document.querySelector('.act-empty-words') || {}).textContent || null")
            close_ctx(qctx, qpg)
            check("Activity's words say follows: 'Who followed you, liked your posts or said something on them, and who"
                  " answered you.', and with nothing yet 'When someone follows you, likes your post, says something on it,"
                  " or answers you, you’ll see it here.'",
                  sub == "Who followed you, liked your posts or said something on them, and who answered you."
                  and empty == "When someone follows you, likes your post, says something on it, or answers you, you’ll see it here.",
                  f"{sub!r}; {empty!r}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "signed out: Follow raises the sheet that says how; Not now; Sign in comes back, nothing pressed"):
        try:
            sia = someone(b, "sia", "Sia Rowe")
            tal = someone(b, "tal", "Tal Shaw")
            ctx, pg = browser_as(b, None)
            go(pg, "/social/@sia")
            pg.locator(".fo-btn").tap()
            pg.wait_for_timeout(700)
            o = pg.evaluate(SHEET, "followOutSheet")
            check("signed out, a tap on Follow raises the small sheet the heart uses, in a sheet's paper: 'Follow Sia?',"
                  " 'Sign in, and Sia’s new drawings show first on your Home.', Not now and Sign in (the action)",
                  o and o["open"] and o["role"] == "dialog" and o["paper"] == SHEET_PAPER["light"] and o["title"] == "Follow Sia?"
                  and o["lede"] == "Sign in, and Sia’s new drawings show first on your Home."
                  and [a[:2] for a in o["acts"]] == [["Not now", False], ["Sign in", True]],
                  json.dumps(o))
            pg.locator("#followOutSheet .post-sheet-acts [data-make-close]").tap()
            pg.wait_for_timeout(700)
            o2 = pg.evaluate(SHEET, "followOutSheet")
            back = pg.evaluate("() => !!document.activeElement && document.activeElement.classList.contains('fo-btn')")
            close_ctx(ctx, pg)
            check("Not now puts it away and gives Follow its focus back; Sign in goes to signing in, with this page to come"
                  " back to; nothing is kept",
                  o2 and not o2["open"] and back and o and o["href"] == "/social/signin?next=/social/@sia"
                  and follows_of(of="sia") == [],
                  f"open {o2 and o2['open']}; focus {back}; to {o and o['href']}")
            tpg = tal.pg
            tpg.goto(BASE + "/social/you")
            with tpg.expect_navigation(timeout=15000):
                tpg.click("form[action$='/social/signout'] button", timeout=5000)
            go(tpg, "/social/@sia")
            tpg.locator(".fo-btn").tap()
            tpg.wait_for_timeout(700)
            tap_to(tpg, tpg.locator("#followOutSheet .post-sheet-acts a"))
            try:
                with tpg.expect_navigation(timeout=20000):
                    tpg.click("[data-passkey=signin]", timeout=5000)
                ready(tpg)
            except Exception:  # noqa: BLE001 -- not landing is the row's red
                pass
            tpg.wait_for_timeout(1200)
            landed = urllib.parse.urlparse(tpg.url).path
            fb = tpg.evaluate(FBTN)
            check("signed in from there, they land on the same page, where Follow waits: not following, nothing kept for"
                  " them",
                  landed == "/social/@sia" and fb and not fb["following"] and fb["follow"] == "/social/@sia/follow"
                  and follows_of("tal") == [],
                  f"landed {landed}; {fb and (fb['following'], fb['follow'])}; kept {follows_of('tal')}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "blocks: a block ends a follow both ways and keeps it from coming back; lifting it restores nothing"):
        try:
            una = someone(b, "una", "Una Toll")
            van = someone(b, "van", "Van Udo")
            follow(una, "van")
            follow(van, "una")
            both = len(follows_of("una", "van")) + len(follows_of("van", "una"))
            st = block(una, "van")
            gone = follows_of("una", "van") + follows_of("van", "una")
            s1, _ = follow(una, "van")
            s2, _ = follow(van, "una")
            check("a block ends a follow both ways (the rows go), and neither can follow the other while it stands",
                  both == 2 and st == 200 and gone == [] and s1 == 404 and s2 == 404
                  and follows_of("una", "van") + follows_of("van", "una") == [],
                  f"before {both}; block {st}; left {gone}; then {s1}/{s2}")
            ub = unblock(una, "van")
            back = follows_of("una", "van") + follows_of("van", "una")
            ctx, pg = browser_as(b, una)
            go(pg, "/social/@van")
            fb = pg.evaluate(FBTN)
            close_ctx(ctx, pg)
            check("lifting the block brings no follow back: Follow, not Following, either way",
                  ub == 200 and back == [] and fb and not fb["following"], f"unblock {ub}; rows {back}; {fb and fb['following']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "the data: the chain on a populated database; one row a pair, never yourself; the reads; deleting in code"):
        try:
            mdb = os.path.join(TMP, "chain-follows.db")
            # The chain's head before follows (its migration's down_revision).
            BEFORE = "a81c5c4dde3a"

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
            then = "2026-11-13 10:00:00"
            for i, h in ((1, "ann"), (2, "bob")):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle,"
                            " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                            (i, "site:" + h, h, h, h.title(), bytes([i]) * 32, then, then))
            con.commit()
            con.close()
            up2 = chain("upgrade", "head")
            idx = {r[0]: r[1] for r in at("select name, sql from sqlite_master where type = 'index' and tbl_name = 'social_follows'")}
            cols = [r[1] for r in at("pragma table_info(social_follows)")]
            sql = (at("select sql from sqlite_master where name = 'social_follows'") or [[""]])[0][0] or ""
            people = [r[1] for r in at("pragma table_info(social_people)")]
            check("the site's chain on a database with people in it adds social_follows (who, whom, when first, when it"
                  " ended), its three indexes (the pair unique; whom a person follows and who follows a person, newest"
                  " first) and its CHECK, and Home's pick on the person, touching nothing else",
                  up1.returncode == 0 and up2.returncode == 0
                  and cols == ["id", "follower_id", "followed_id", "created_at", "ended_at"]
                  and set(idx) == {"ix_social_follows_pair", "ix_social_follows_follower_created", "ix_social_follows_followed_created"}
                  and "UNIQUE" in (idx.get("ix_social_follows_pair") or "") and "ck_social_follows_not_self" in sql
                  and "home_feed" in people and at("select count(*) from social_people") == [(2,)],
                  f"up {up1.returncode}/{up2.returncode} {up2.stderr.strip().splitlines()[-1:] if up2.returncode else ''};"
                  f" cols {cols}; indexes {sorted(idx)}; people {people[-3:]}")
            con = sqlite3.connect(mdb)
            errs = []
            for vals in ((1, 2), (1, 2), (2, 1), (1, 1)):
                try:
                    con.execute("insert into social_follows (follower_id, followed_id, created_at) values (?, ?, ?)", vals + (then,))
                    errs.append("kept")
                except sqlite3.IntegrityError as e:
                    errs.append(str(e).split(":")[0])
            con.rollback()
            con.close()
            check("one row a pair (a second is refused, the other way round is its own pair), and nobody follows"
                  " themselves (refused)",
                  errs == ["kept", "UNIQUE constraint failed", "kept", "CHECK constraint failed"], json.dumps(errs))
            down = chain("downgrade", BEFORE)
            gone = at("select name from sqlite_master where tbl_name = 'social_follows'")
            people2 = [r[1] for r in at("pragma table_info(social_people)")]
            check("taken back down, the chain drops the table, its indexes and Home's pick, every person kept",
                  down.returncode == 0 and gone == [] and "home_feed" not in people2
                  and at("select handle from social_people order by id") == [("ann",), ("bob",)],
                  f"down {down.returncode} {down.stderr.strip().splitlines()[-1:] if down.returncode else ''}; left {gone}")
            wyn = someone(b, "wyn", "Wyn Yale")
            xan = someone(b, "xan", "Xan Zorn")
            yul = someone(b, "yul", "Yul Abel")
            someone(b, "zia", "Zia Bond")
            for who in (xan, yul):
                follow(wyn, who.handle)
                follow(who, "wyn")
            make_post(xan, "Section 12, Xan's")
            make_post(yul, "Section 12, Yul's")
            make_post(wyn, "Section 12, Wyn's")
            copy = os.path.join(TMP, "probe12.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            home_as = "; ".join(f"{c['name']}={c['value']}" for c in wyn.ctx.cookies(BASE))
            probe = subprocess.run([sys.executable, "-c", PROBE, "wyn", "xan", home_as, "zia"], cwd=ROOT, capture_output=True,
                                   text=True, timeout=180,
                                   env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-600:]}
            plans = out.get("plans") or {}
            flat = [x for v in plans.values() for x in v]
            check("the reads, as the code sends them, are searches on their own indexes (SQLite's own plan): who follows"
                  " you and how many by whom, newest first; whom you follow by who; whether you follow somebody by the"
                  " pair; Activity's by whom",
                  any("ix_social_follows_followed_created (followed_id=?)" in x for x in plans.get("followers", []))
                  and any("ix_social_follows_follower_created (follower_id=?)" in x for x in plans.get("following", []))
                  and any("(followed_id=?)" in x and "social_follows" in x for x in plans.get("count", []))
                  and any("ix_social_follows_pair (follower_id=? AND followed_id=?)" in x for x in plans.get("is", []))
                  and any("(follower_id=?)" in x for x in plans.get("circle", []))
                  and any("ix_social_follows_followed_created (followed_id=?)" in x for x in plans.get("activity", []))
                  and not any(x.startswith("SCAN social_follows") for x in flat)
                  and not any("TEMP B-TREE" in x for k in ("followers", "following", "activity") for x in plans.get(k, [])),
                  json.dumps(plans or out.get("err"))[:700])
            h1, h2 = out.get("home1") or {}, out.get("home2") or {}
            check("Home's Following is one read of posts (the people you follow as a subquery, on the posts' own"
                  " indexes) and no read a card: ten more cards on the page, the same number of reads",
                  h1.get("caught") and h2.get("caught") and (h2.get("cards") or 0) >= (h1.get("cards") or 0) + 10
                  and h1.get("reads") == h2.get("reads") and h1.get("posts_plan")
                  and not any(x.startswith("SCAN social_posts") and "INDEX" not in x for x in h1.get("posts_plan") or [])
                  and any("social_follows" in x for x in h1.get("posts_plan") or []),
                  json.dumps({"home1": h1, "home2": h2, "err": out.get("err")})[:700])
            check("deleting an account takes its follows both ways, in code: with SQLite's cascade off, none is left",
                  out.get("fk") == 0 and out.get("deleted") and out["deleted"][0] == 4 and out["deleted"][1] == 0,
                  json.dumps({k: out.get(k) for k in ("fk", "deleted", "err")}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)

    # ------------------------------------------------------------------ 13
    if part(13, "words and marks: every new screen, phone and desk, light and dark"):
        try:
            ada = someone(b, "ada", "Ada Bloom")
            bex = someone(b, "bex", "Bex Crane")
            cid = someone(b, "cid", "Cid Dove")
            dot = someone(b, "dot", "Dot Ellis")
            for who in (ada, bex, cid):
                give_face(who, 130 + len(who.handle) + ord(who.handle[1]))
            make_post(bex, "Section 13, Bex's")
            make_post(cid, "Section 13, Cid's")
            make_post(dot, "Section 13, Dot's")
            follow(ada, "bex")
            follow(bex, "ada")
            follow(cid, "ada")
            pick(dot, "following")
            lows, smalls, fields, marks, inks, read = [], [], [], [], [], 0
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    got = []
                    follow(ada, "cid", False)
                    ctx, pg = browser_as(b, ada, screen=screen, scheme=scheme)
                    go(pg, "/social/@cid")
                    got.append(("somebody's page", pg.evaluate(READ)))
                    marks += [(tag, "Follow", m) for m in pg.evaluate(MARKS)]
                    tap_follow(pg, after=900)
                    got.append(("Following", pg.evaluate(READ)))
                    marks += [(tag, "Following", m) for m in pg.evaluate(MARKS)]
                    press(pg, ".fo-btn")
                    pg.wait_for_timeout(800)
                    got.append(("the unfollow sheet", pg.evaluate(READ, "#unfollowSheet")))
                    go(pg, "/social/@ada")
                    got.append(("your own page", pg.evaluate(READ)))
                    press(pg, "[data-follows-open]")
                    pg.wait_for_timeout(800)
                    got.append(("the lists, Followers", pg.evaluate(READ, "#followsSheet")))
                    inks.append((tag, "the lists' pill", pg.evaluate(PILL_INK, "#followsSheet .fo-seg")))
                    press(pg, "#followsSheet .fo-seg button[data-tab=following]")
                    pg.wait_for_timeout(800)
                    got.append(("the lists, Following", pg.evaluate(READ, "#followsSheet")))
                    go(pg, "/social/", wait=600)
                    got.append(("Home on Following", pg.evaluate(READ)))
                    inks.append((tag, "Home's pill", pg.evaluate(PILL_INK, "[data-home-pill]")))
                    pg.evaluate("() => { const c = document.querySelector('.fo-caught'); if (c) scrollTo(0, c.getBoundingClientRect().top + scrollY - innerHeight / 2); }")
                    pg.wait_for_timeout(400)
                    got.append(("Home, caught up", pg.evaluate(READ)))
                    marks += [(tag, "caught up", m) for m in pg.evaluate(MARKS)]
                    db_write("update social_people set activity_seen_at = null where handle_key = 'ada'")
                    go(pg, "/social/activity")
                    got.append(("Activity", pg.evaluate(READ)))
                    marks += [(tag, "Activity", m) for m in pg.evaluate(MARKS)]
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, dot, screen=screen, scheme=scheme)
                    go(pg, "/social/", wait=600)
                    got.append(("Home, following nobody", pg.evaluate(READ)))
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, None, screen=screen, scheme=scheme)
                    go(pg, "/social/@cid")
                    press(pg, ".fo-btn")
                    pg.wait_for_timeout(800)
                    got.append(("the signed-out sheet", pg.evaluate(READ, "#followOutSheet")))
                    close_ctx(ctx, pg)
                    for where, r in got:
                        read += r["read"]
                        lows += [f"{tag} {where}: {x}" for x in r["low"]]
                        smalls += [f"{tag} {where}: {x}" for x in r["small"]]
                        fields += [f"{tag} {where}: {x}" for x in r["fields"]]
                    check(f"every word at 4.5:1 or more on what is painted behind it, {tag}: somebody's page (Follow, then"
                          " Following), the unfollow sheet, your own page with its line, the lists (both), Home on"
                          " Following (the pill, caught up, Fresh from everyone), following nobody, Activity with follows,"
                          " the signed-out sheet",
                          all(r["read"] > 0 for _, r in got) and not any(r["low"] for _, r in got),
                          f"read {[(w, r['read'], r['lowest']) for w, r in got]}; low {[x for _, r in got for x in r['low']][:3]}")
            check("every target 44px or more to a finger (a pill's option by its band) and no text field under 16px, on"
                  " all of them", not smalls and not fields, f"small {smalls[:4]}; fields {fields[:3]}")
            kinds = {m["what"] for _, _, m in marks}
            weak = [(t, w, m) for t, w, m in marks if m["k"] < 3]
            check("every new mark at 3:1 or more on what is painted behind it, light and dark: Follow's plus, Following's"
                  " check, the caught-up check, Activity's small Follow on the page and its white plus",
                  {"plus", "check", "caught", "disc", "disc plus"} <= kinds and not weak,
                  f"kinds {sorted(kinds)}; under {weak[:3]}; lowest {min((m['k'] for _, _, m in marks), default=None)}")
            check("each pill's chosen option on its tint, and the other on the track, at 4.5:1 or more, light and dark",
                  len(inks) == 8 and all(i and not i.get("unread") and i["on"] >= 4.5 and i["off"] >= 4.5 for _, _, i in inks),
                  json.dumps(inks))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(13, exc)

    # ------------------------------------------------------------------ 14
    if part(14, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(14, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
