"""Likes on the Skribl site (phase 2, likes; docs/SOCIAL-SITE.md "Built:
likes"), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. THE HEART AND THE COUNT, WHERE THEY ARE: on Home's card beside Share,
     after the comment count; on a post's page and a drawing's at the right
     end of the time-and-plays line, the line keeping its height; 44px and
     painted; the pen's heart, empty until liked, named "Like"; no number at
     zero; the count everyone's, "1 like", "2 likes".
  2. A TAP LIKES, THE SAME TAP TAKES IT BACK: pressed and counted at once,
     kept by the site, still so after a reload, taken back by the same tap;
     one like a person a thing; quick taps end where the last one left it,
     one request at a time; your own; liked on Home is liked on its page.
  3. WHO MAY LIKE: signed out, without the page's token or from elsewhere,
     taken down, a block either way, a post taken down (its maker's too), a
     drawing kept unlisted or a post's drawing asked as a drawing, a body
     that is not a yes or a no: refused, nothing kept; the limit (120 an
     hour); a refusal in the page puts the heart back and says why.
  4. COUNTED BY THE VIEWER: a like by somebody blocked either way is neither
     shown nor counted for that viewer, a like by somebody taken down for
     nobody; the maker's "Liked by…" the same.
  5. EACH LIKE KEEPS ITS MOMENT: tapped while the drawing plays, where the
     replay was (between the playhead read just before and just after the
     tap); at 4x the drawing's time, not the watcher's; still or paused, no
     moment, counted all the same; only a whole number of ms from 0 to a day
     is kept.
  6. KIND, NEVER JUMPY: liking draws the blush line round over many frames
     and fills, the heart's box never moving; taking it back fades, nothing
     un-drawing; under Reduce Motion it only fades; a count that comes fades
     in and the heart glides aside, one that goes fades first; under Reduce
     Motion nothing glides. Read on every animation frame.
  7. SIGNED OUT: the heart and its count are there; a tap raises "Like this
     drawing?" naming the maker, in a sheet's paper; Not now gives the heart
     its focus back; Sign in comes back to the same page, and the heart waits,
     nothing liked for them; a drawing's page too.
  8. "LIKED BY…", THE MAKER'S ALONE: the line's words for one, two, three
     and more, newest first, "you" first; the newest three faces; nobody else
     is shown who; the sheet (newest first, face, name, @handle, when, the
     moment where one was kept, "Only you can see who liked it."), a row to
     their page; the maker's own like says so at once, the line's room
     opening and closing.
  9. ACTIVITY: a like is a row ("Otto liked your post", their face wearing a
     small heart, the post's small picture, to "Liked by…"); likes never
     light the bell's dot, they wait under New; grouped since you last looked,
     one row a post under Earlier too; never yourself, never the hidden; a
     drawing's own page; comments still light the dot; a row lands with
     "Liked by…" glowing in the note's tint, read on every frame; the words.
 10. DELETING TAKES THEM, IN CODE: a post, a drawing and an account, through
     the site's own routes, and with SQLite's cascade off (on a copy).
 11. THE DATA: the chain on a populated database (the table, its five
     indexes, its CHECK; back down); one like a person a thing, on exactly
     one thing; the reads on their indexes (SQLite's own plan); Home's feed
     one grouped read a kind.
 12. WORDS AND MARKS: every word on Home, a post's page with "Liked by…", its
     sheet, the signed-out sheet and Activity with likes at 4.5:1 on what is
     painted behind it, every target 44px, no field under 16px, phone (touch)
     and desk, light and dark; the heart's line, empty and liked, the small
     heart and the sheet's dot at 3:1; a landed "Liked by…" on the tint.
 13. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALLIKES_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Likes at /social".
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
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALLIKES_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALLIKES {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence likes work.")
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
TMP = tempfile.mkdtemp(prefix="sociallikes-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-sociallikes-" + secrets.token_hex(8),
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


def give_face(who, seed):
    """A face for them, so a face on the page says whose it is: a drawing of
    theirs, kept unlisted, named as their face on their row. Its skribl's id."""
    sid = make_drawing(who, f"{who.handle}'s face", seed=seed, vis="unlisted")
    db_write("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = ?",
             (sid, who.handle.lower()))
    return sid


def page_of(on):
    kind, oid = on
    return f"/social/{'p' if kind == 'p' else 'b'}/{oid}"


def like(who, on, liked=True, at=None, raw=None):
    """A like (or taking it back) as the heart sends one, on a post (("p", id))
    or a drawing (("s", id)): (status, answer)."""
    c = who.client() if who is not None else Client()
    c.get(page_of(on))
    if not c.token:
        c.get("/social/")      # a page they cannot open: the token from one they can
    return c.post_json(page_of(on) + "/like", raw if raw is not None else {"liked": liked, "at_ms": at})


def likes_on(on):
    """The likes kept on a post or a drawing: [(handle, at_ms)], oldest first."""
    kind, oid = on
    if kind == "p":
        return db("select p.handle, l.at_ms from social_likes l join social_posts s on s.id = l.post_id"
                  " join social_people p on p.id = l.person_id where s.public_id = ? order by l.id", (oid,))
    return db("select p.handle, l.at_ms from social_likes l join social_people p on p.id = l.person_id"
              " where l.drawing_id = ? order by l.id", (oid,))


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


def tap_heart(pg, sel, after=250):
    """Tap a heart and wait for the site's answer. A tap that sends nothing
    reads as the row's own red, never a section that stops."""
    try:
        with pg.expect_response(lambda r: r.url.endswith("/like") and r.request.method == "POST", timeout=8000):
            pg.locator(sel).first.tap(timeout=5000)
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


def card(post):
    return f'.post-card[data-post="{post}"]'


def drawing_card(sid):
    return f'.post-card[data-skribl="{sid}"]'


# ---- what the page shows, read in the page ---------------------------------------
# A heart: its box, whether it is painted where it stands, its state, its
# name, its count, its parts' paint.
HEART = r"""(sel) => { const el = document.querySelector(sel); if (!el || !el.getClientRects().length) return null;
  const r = el.getBoundingClientRect(), svg = el.querySelector('svg.ic-heart'), n = el.querySelector('.lk-n');
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const cs = s => svg && svg.querySelector(s) ? getComputedStyle(svg.querySelector(s)) : null;
  return { w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10, left: r.left, right: r.right,
    top: r.top, bottom: r.bottom, mid: r.top + r.height / 2, hit: !!at && (at === el || el.contains(at)),
    pressed: el.getAttribute('aria-pressed'), label: el.getAttribute('aria-label'), n: n ? n.textContent.trim() : null,
    digits: /\d/.test(el.textContent), liked: el.classList.contains('is-liked'),
    pen: !!svg && svg.classList.contains('pen-ic') && svg.querySelectorAll('path[pathLength="1"]').length === 2
         && svg.querySelectorAll('path').length === 3,
    fill: cs('.ht-fill') ? +cs('.ht-fill').opacity : null, ink: cs('.ht-ink') ? +cs('.ht-ink').opacity : null,
    line: cs('.ht-line') ? +cs('.ht-line').opacity : null, lineColor: cs('.ht-line') ? cs('.ht-line').stroke : null,
    inkColor: cs('.ht-ink') ? cs('.ht-ink').stroke : null, fillColor: cs('.ht-fill') ? cs('.ht-fill').fill : null,
    like: el.getAttribute('data-like'), out: el.hasAttribute('data-like-out'), color: getComputedStyle(el).color }; }"""

# A card's foot: what is shown in it, in order, with each one's edges.
FOOT = r"""(sel) => { const f = document.querySelector(sel + ' .post-foot'); if (!f) return null;
  return [...f.children].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect();
    return { k: e.classList.contains('lk-heart') ? 'heart' : e.classList.contains('post-share') ? 'share'
              : e.classList.contains('post-count') ? 'count' : e.classList.contains('post-plays') ? 'plays' : e.tagName,
             left: Math.round(r.left * 10) / 10, right: Math.round(r.right * 10) / 10 }; }); }"""

# A post's page: the time-and-plays line, its words and its heart.
META = r"""() => { const m = document.querySelector('.post-page > .post-meta'), h = m && m.querySelector('.lk-heart');
  if (!m) return null; const r = m.getBoundingClientRect(), w = m.querySelector('.lk-meta-words');
  return { top: r.top, bottom: r.bottom, h: Math.round(r.height * 100) / 100, right: r.right,
           lh: parseFloat(getComputedStyle(m).lineHeight), words: w ? w.textContent.replace(/\s+/g, ' ').trim() : null,
           inLine: !!h && m.contains(h), last: !!h && m.lastElementChild === h }; }"""

# The maker's "Liked by…": its words, its faces (a face's still picture names
# whose it is), its size and whether it is painted.
BY = r"""() => { const a = document.querySelector('[data-like-by]'); if (!a || !a.getClientRects().length) return null;
  const r = a.getBoundingClientRect(), at = document.elementFromPoint(r.left + 40, r.top + r.height / 2);
  return { words: a.querySelector('.lk-by-words').textContent.replace(/\s+/g, ' ').trim(),
           faces: [...a.querySelectorAll('.face-ring')].map(f => { const i = f.querySelector('img.skribl-face-still');
                                                                    return i ? new URL(i.src).pathname : 'blank'; }),
           h: Math.round(r.height * 10) / 10, w: Math.round(r.width), top: r.top, bottom: r.bottom,
           hit: !!at && (at === a || a.contains(at)), id: a.id, popup: a.getAttribute('aria-haspopup') }; }"""

# The sheet of who: open, its paper, its title, its rows in order, its note.
SHEET = r"""() => { const w = document.getElementById('likeSheet'); if (!w) return null;
  const s = w.querySelector('.make-sheet');
  return { open: w.classList.contains('is-open') && !w.hidden, paper: getComputedStyle(s).backgroundColor,
    role: s.getAttribute('role'), title: (w.querySelector('.make-title') || {}).textContent,
    card: getComputedStyle(w.querySelector('.lk-list')).backgroundColor,
    rows: [...w.querySelectorAll('.lk-row')].map(a => ({ name: a.querySelector('.lk-who b').textContent.trim(),
      handle: a.querySelector('.lk-who span').textContent.trim(), href: new URL(a.href).pathname,
      when: (a.querySelector('time') || {}).textContent || null, at: a.querySelector('.lk-at')
        ? a.querySelector('.lk-at').textContent.replace(/its moment in the replay,/, '').trim() : null,
      dot: a.querySelector('.lk-mark') ? getComputedStyle(a.querySelector('.lk-mark')).backgroundColor : null,
      face: (f => f ? new URL(f.src).pathname : 'blank')(a.querySelector('img.skribl-face-still')) })),
    note: (w.querySelector('.lk-note') || {}).textContent || null }; }"""

# The signed-out sheet.
OUT = r"""() => { const w = document.getElementById('likeOutSheet'); if (!w) return null;
  const s = w.querySelector('.make-sheet'), a = w.querySelector('.post-sheet-acts a');
  return { open: w.classList.contains('is-open') && !w.hidden, paper: getComputedStyle(s).backgroundColor,
    role: s.getAttribute('role'), title: w.querySelector('.make-title').textContent.trim(),
    lede: w.querySelector('.post-lede').textContent.replace(/\s+/g, ' ').trim(),
    acts: [...w.querySelectorAll('.post-sheet-acts > *')].map(e => e.textContent.trim()),
    href: a ? new URL(a.href).pathname + new URL(a.href).search : null,
    focus: document.activeElement ? document.activeElement.textContent.trim() : null }; }"""

# The rows of Activity, each section's (verify_socialactivity's, with the badge).
ROWS = r"""() => [...document.querySelectorAll('.act-list')].map(ul => {
  const h = document.getElementById(ul.getAttribute('aria-labelledby'));
  return { sec: h ? h.textContent.trim() : null, rows: [...ul.querySelectorAll(':scope > li > a.act-row')].map(a => {
    const pic = a.querySelector('.act-pic'), mark = a.querySelector('.act-mark'), badge = a.querySelector('.act-badge');
    const faces = [...a.querySelectorAll('.face-ring')].map(f => { const i = f.querySelector('img.skribl-face-still');
                                                                   return i ? new URL(i.src).pathname : 'blank'; });
    let front = null;
    const two = a.querySelector('.act-faces');
    if (two) { const f = two.querySelector('.face-ring:last-child'), r2 = f.getBoundingClientRect(),
                     at = document.elementFromPoint(r2.left + r2.width * 0.5, r2.top + r2.height * 0.5);
               front = at && f.contains(at) ? faces[faces.length - 1] : null; }
    let b = null;
    if (badge) { const r3 = badge.getBoundingClientRect(), at3 = document.elementFromPoint(r3.left + r3.width / 2, r3.top + r3.height / 2);
                 const ink = badge.querySelector('.ht-ink'), fill = badge.querySelector('.ht-fill');
                 b = { painted: !!at3 && badge.contains(at3), w: Math.round(r3.width), ink: getComputedStyle(ink).stroke,
                       inkOp: +getComputedStyle(ink).opacity, fill: getComputedStyle(fill).fill, fillOp: +getComputedStyle(fill).opacity }; }
    return { say: a.querySelector('.act-say').textContent.replace(/\s+/g, ' ').trim(),
             peek: a.querySelector('.act-peek') ? a.querySelector('.act-peek').textContent : null,
             when: (a.querySelector('.act-when') || {}).textContent || null, faces, front, badge: b,
             pic: getComputedStyle(pic).backgroundImage, href: new URL(a.href).pathname + new URL(a.href).hash,
             isNew: a.classList.contains('is-new'), mark: getComputedStyle(mark).backgroundColor,
             h: Math.round(a.getBoundingClientRect().height * 10) / 10 }; }) }; })"""

# Whether a bell (the phone's top, or a desk's rail) wears a dot.
DOT = r"""(sel) => { const a = document.querySelector(sel); if (!a || !a.getClientRects().length) return 'no bell';
  return !!a.querySelector('.act-dot'); }"""

# Every animation frame for `ms` from now: a heart's parts' paint and its icon's box.
HSAMPLE = r"""([sel, ms]) => { window.__hf = []; const el = document.querySelector(sel); const t0 = performance.now();
  const step = () => { const svg = el.querySelector('svg.ic-heart'), r = svg.getBoundingClientRect();
    const g = s => getComputedStyle(svg.querySelector(s)), n = el.querySelector('.lk-n');
    window.__hf.push({ t: Math.round(performance.now() - t0), off: parseFloat(g('.ht-ink').strokeDashoffset),
      dash: g('.ht-ink').strokeDasharray, ink: +g('.ht-ink').opacity, fill: +g('.ht-fill').opacity,
      line: +g('.ht-line').opacity, x: r.left, y: r.top, w: r.width, h: r.height,
      n: n ? +getComputedStyle(n).opacity : null, tf: getComputedStyle(svg).transform });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# Every animation frame for `ms` from now: the maker's line's box and paint.
BSAMPLE = r"""(ms) => { window.__bf = []; const t0 = performance.now();
  const step = () => { const a = document.querySelector('[data-like-by]'), c = document.querySelector('.post-actions');
    const f = { t: Math.round(performance.now() - t0), there: !!a, acts: c ? c.getBoundingClientRect().top : null };
    if (a) { const r = a.getBoundingClientRect(); f.h = r.height; f.op = +getComputedStyle(a).opacity; }
    window.__bf.push(f);
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# From the page's first frame, landing at "Liked by…" (#liked): there, in
# view, glowing (is-landed), its tint's opacity and colour, and where it is.
LANDING = r"""window.__lf = [];
(function () { const t0 = performance.now(); const step = () => {
  const a = document.getElementById('liked');
  const f = { t: Math.round(performance.now() - t0), there: !!a, landed: false };
  if (a) { const r = a.getBoundingClientRect(); f.top = Math.round(r.top * 10) / 10; f.bottom = r.bottom;
    if (a.classList.contains('is-landed')) { const cs = getComputedStyle(a, '::before');
      Object.assign(f, { landed: true, op: +cs.opacity, bg: cs.backgroundColor }); } }
  window.__lf.push(f);
  if (performance.now() - t0 < 4500) requestAnimationFrame(step); };
  requestAnimationFrame(step); })();"""

# How many like requests are out at once, and what each said.
FETCHES = r"""window.__lk = { now: 0, max: 0, sent: [] };
(function () { const f = window.fetch;
  window.fetch = function (u, o) { if (!String(u).endsWith('/like')) return f.apply(this, arguments);
    window.__lk.now++; window.__lk.max = Math.max(window.__lk.max, window.__lk.now);
    try { window.__lk.sent.push(JSON.parse(o.body)); } catch (e) { window.__lk.sent.push(null); }
    return f.apply(this, arguments).finally(() => { window.__lk.now--; }); }; })();"""

# Where the page's own drawing is, through the seam the site reads.
PLAYHEAD = r"""() => { const art = document.querySelector('.post-page > .post-art');
  const p = art && window.SkriblInline ? SkriblInline.mount(art)[0] : null; return p ? p.playhead() : null; }"""

# Every word painted in the page's roots against what is painted behind it,
# every target and every text field (verify_socialcomments' census), in `sel`.
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

# A landed "Liked by…": its words and names against the note's tint over the
# page (the tint is its ::before, which the census cannot see).
LK_TINT = r"""() => { const a = document.getElementById('liked'); if (!a || !a.classList.contains('is-landed')) return null;
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (x, y) => { const p = lum(x), q = lum(y); return Math.round((Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05) * 100) / 100; };
  const tint = rgba(getComputedStyle(a, '::before').backgroundColor), page = rgba(getComputedStyle(document.body).backgroundColor);
  const g = over(tint, page), k = e => e ? ratio(over(rgba(getComputedStyle(e).color), g), g) : null;
  return { tint: getComputedStyle(a, '::before').backgroundColor, words: k(a.querySelector('.lk-by-words')),
           name: k(a.querySelector('.lk-by-words b')) }; }"""

# A mark's line against what is painted behind its box: the hearts (empty,
# liked; on a card or a page), Activity's small heart, the sheet's dot.
MARKS = r"""() => {
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => c[3] >= 1 ? c : [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; };
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const out = [];
  document.querySelectorAll('.lk-heart, .act-badge').forEach(h => { if (!h.getClientRects().length) return;
    const svg = h.querySelector('svg.ic-heart'); if (!svg) return;
    const liked = h.classList.contains('is-liked') || h.classList.contains('act-badge');
    const p = svg.querySelector(liked ? '.ht-ink' : '.ht-line'), cs = getComputedStyle(p), g = ground(h);
    const c = rgba(cs.stroke); if (!c) return; c[3] *= +cs.opacity;
    out.push({ what: (h.classList.contains('act-badge') ? 'badge' : h.classList.contains('lk-foot') ? 'card' : 'page')
                     + (liked ? ' liked' : ' empty'), k: ratio(over(c, g), g) }); });
  document.querySelectorAll('#likeSheet:not([hidden]) .lk-mark').forEach(d => { const g = ground(d.parentElement);
    out.push({ what: 'sheet dot', k: ratio(rgba(getComputedStyle(d).backgroundColor), g) }); });
  return out; }"""


def faded(ops):
    """Frames shown part-way between whole and gone."""
    return len([o for o in ops if o is not None and 0.03 < o < 0.97])


def glide_of(xs):
    """How a thing moved over frames: the frames it moved on, its largest step,
    and the whole way (a snap goes the whole way in one frame)."""
    steps = [abs(b - a) for a, b in zip(xs, xs[1:])]
    return {"frames": len([s for s in steps if s > 0.3]), "step": round(max(steps or [0]), 2),
            "way": round(abs(xs[-1] - xs[0]), 2) if xs else 0}


def spread(fs, key):
    vals = [f[key] for f in fs]
    return round(max(vals) - min(vals), 2) if vals else 0


LIGHT_PAGE, DARK_PAGE = "rgb(251, 252, 253)", "rgb(11, 13, 18)"
SHEET_PAPER = {"light": "rgb(243, 240, 255)", "dark": "rgb(23, 20, 42)"}
ROW_BG = {"light": "rgb(255, 255, 255)", "dark": "rgb(35, 30, 59)"}
HEART_INK = {"light": "rgb(230, 74, 120)", "dark": "rgb(255, 111, 145)"}
BLUSH = "rgb(255, 111, 145)"
INK2 = {"light": "rgb(75, 85, 99)", "dark": "rgb(183, 191, 204)"}
TINT = {"light": "rgba(124, 92, 255, 0.12)", "dark": "rgba(124, 92, 255, 0.18)"}

# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): what goes then goes
# because the code said so. And the reads, as the code sends them, planned
# by SQLite, and how many reads of the likes a page of Home's cards makes.
PROBE = r"""
import json, re, sys
from datetime import datetime, timezone
from app import create_app, db
import sqlalchemy as sa
from sqlalchemy import event
app = create_app()
with app.app_context():
    from social.models import Like, Person, Post
    from social.accounts import delete_person
    from social.posts import drop_post
    from social import likes as L
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    post_id, person = sys.argv[1], sys.argv[2]
    row = db.session.execute(sa.select(Post).where(Post.public_id == post_id)).scalar_one()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == person)).scalar_one()
    author = db.session.execute(sa.select(Person).where(Person.id == row.person_id)).scalar_one()
    out = {"fk": fk}
    # The reads, as the code makes them (every statement on the likes it
    # sends, with what it sends), planned by SQLite: a page's counts, who
    # liked one, and Activity's.
    rec = []
    def keep(conn, cursor, statement, params, context, executemany):
        if "social_likes" in statement and statement.lstrip().upper().startswith("SELECT"):
            rec.append((statement, params))
    event.listen(db.engine, "before_cursor_execute", keep)
    calls = {}
    with app.test_request_context("/social/"):
        from social.comments import On
        from social.activity import _likes
        for name, call in (("stats", lambda: L.stats(author, posts=[row.id, row.id + 1])),
                           ("who", lambda: L.who(On(author, post=row), author)),
                           ("activity", lambda: _likes(author, frozenset({-1}), datetime(2026, 1, 1, tzinfo=timezone.utc)))):
            rec.clear()
            call()
            calls[name] = list(rec)
    event.remove(db.engine, "before_cursor_execute", keep)
    conn = db.session.connection()
    out["plans"] = {name: [r[3] for st, params in sent
                           for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + st, params).fetchall()]
                    for name, sent in calls.items()}
    out["sent"] = {name: len(sent) for name, sent in calls.items()}
    # Home, as the person whose cookie this is: how many reads of the likes
    # a page of its cards makes.
    seen = []
    def count(conn, cursor, statement, *a):
        if "social_likes" in statement:
            seen.append(statement.split()[0])
    event.listen(db.engine, "before_cursor_execute", count)
    page = app.test_client(use_cookies=False).get("/social/", headers={"Cookie": sys.argv[3], "X-Forwarded-For": "10.250.1.1"})
    event.remove(db.engine, "before_cursor_execute", count)
    html = page.get_data(as_text=True)
    out["reads"] = seen
    out["cards"] = html.count('class="post-card"')
    out["kinds"] = sorted(set(re.findall(r'data-like="/social/([pb])/', html)))
    # Deleting, with the cascade off: a post with its likes; an account with
    # its likes and every like on what it owned.
    before = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.post_id == row.id)).scalar()
    drop_post(author.public_id, row)
    db.session.commit()
    after = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.post_id == row.id)).scalar()
    out["post"] = [before, after]
    gave = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.person_id == who.id)).scalar()
    owned = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.owner_id == who.id)).scalar()
    delete_person(db.session, who.id)
    db.session.commit()
    gave2 = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.person_id == who.id)).scalar()
    owned2 = db.session.execute(sa.select(sa.func.count()).select_from(Like).where(Like.owner_id == who.id)).scalar()
    out["person"] = [gave, owned, gave2, owned2]
    print(json.dumps(out))
"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the heart and the count, where they are: Home's card, a post's page, a drawing's page"):
        try:
            ann = someone(b, "ann", "Ann Lake")
            bea = someone(b, "bea", "Bea Moss")
            cyd = someone(b, "cyd", "Cyd Park")
            dov = someone(b, "dov", "Dov Reyes")
            p1 = make_post(ann, "Section 1, Ann's")
            d1 = make_drawing(ann, "Section 1, Ann's drawing", seed=11)
            ctx, pg = browser_as(b, bea)
            go(pg, "/social/")
            pg.locator(card(p1) + " .lk-heart").scroll_into_view_if_needed()
            pg.wait_for_timeout(200)
            foot = pg.evaluate(FOOT, card(p1))
            h = pg.evaluate(HEART, card(p1) + " .lk-heart")
            ks = [f["k"] for f in foot or []]
            hi = ks.index("heart") if "heart" in ks else -1
            gap = foot[hi + 1]["left"] - foot[hi]["right"] if 0 <= hi < len(ks) - 1 else None
            check("on Home's card the heart sits in the foot after the comment count, beside Share and nothing between"
                  " them; 44px each way, painted where it stands",
                  ks[-2:] == ["heart", "share"] and ks.index("count") < hi and gap is not None and -1 <= gap <= 4
                  and h and h["w"] >= 44 and h["h"] >= 44 and h["hit"],
                  f"foot {ks}, gap {gap}; heart {h and (h['w'], h['h'], h['hit'])}")
            check("with nothing liked it stays empty and says so: not pressed, named 'Like', no number at zero; the"
                  " pen's heart (one line drawn round), its blush and ink hidden, its line the words' second ink",
                  h and h["pressed"] == "false" and h["label"] == "Like" and h["n"] is None and not h["digits"]
                  and h["pen"] and h["fill"] == 0 and h["ink"] == 0 and h["line"] == 1
                  and h["lineColor"] == INK2["light"] and not h["liked"],
                  json.dumps({k: h.get(k) for k in ("pressed", "label", "n", "pen", "fill", "ink", "line", "lineColor")} if h else None))
            go(pg, f"/social/p/{p1}")
            m = pg.evaluate(META)
            hp = pg.evaluate(HEART, ".post-page > .post-meta .lk-heart")
            check("on a post's page the heart sits at the right end of the time-and-plays line, riding in the 12px"
                  " either side of it: the line keeps its one line's height; 44px, painted",
                  m and hp and m["inLine"] and m["last"] and abs(m["h"] - m["lh"]) < 0.6 and m["top"] <= hp["mid"] <= m["bottom"]
                  and hp["right"] >= m["right"] - 1 and hp["w"] >= 44 and hp["h"] >= 44 and hp["hit"]
                  and hp["pressed"] == "false" and hp["label"] == "Like" and hp["n"] is None,
                  f"meta {m and (m['h'], m['lh'], m['words'])}; heart {hp and (hp['w'], hp['h'], hp['hit'], round(hp['mid'], 1), round(hp['right'], 1))}"
                  f" vs line {m and (round(m['top'], 1), round(m['bottom'], 1), round(m['right'], 1))}")
            go(pg, f"/social/b/{d1}")
            m2 = pg.evaluate(META)
            hd = pg.evaluate(HEART, ".post-page > .post-meta .lk-heart")
            check("on a drawing's own page (/social/b/<id>) the same heart in the same place, to its own like",
                  m2 and hd and m2["inLine"] and m2["last"] and abs(m2["h"] - m2["lh"]) < 0.6 and hd["hit"] and hd["w"] >= 44
                  and hd["like"] == f"/social/b/{d1}/like" and hd["label"] == "Like",
                  f"meta {m2 and (m2['h'], m2['lh'])}; heart {hd and (hd['w'], hd['hit'], hd['like'])}")
            st1, _ = like(cyd, ("p", p1))
            go(pg, "/social/")
            one = pg.evaluate(HEART, card(p1) + " .lk-heart")
            like(dov, ("p", p1))
            go(pg, "/social/")
            two = pg.evaluate(HEART, card(p1) + " .lk-heart")
            check("the count is everyone's: once somebody else likes it a viewer sees 1 beside a heart still empty for"
                  " them ('Like, 1 like'), then 2 ('Like, 2 likes')",
                  st1 == 200 and one and one["n"] == "1" and one["pressed"] == "false" and one["label"] == "Like, 1 like"
                  and not one["liked"] and two and two["n"] == "2" and two["label"] == "Like, 2 likes",
                  f"{one and (one['n'], one['pressed'], one['label'])} then {two and (two['n'], two['label'])}")
            close_ctx(ctx, pg)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "a tap likes, the same tap takes it back; one like a person a thing; one request at a time"):
        try:
            cal = someone(b, "cal", "Cal Ito")
            dee = someone(b, "dee", "Dee Holt")
            p2 = make_post(cal, "Section 2, Cal's")
            p2b = make_post(cal, "Section 2, Cal's second")
            ctx, pg = browser_as(b, dee, init=FETCHES)
            go(pg, f"/social/p/{p2}")
            sel = ".post-page > .post-meta .lk-heart"
            tap_heart(pg, sel)
            h = pg.evaluate(HEART, sel)
            kept = likes_on(("p", p2))
            check("a tap on the heart likes it: pressed, named 'Liked, 1 like', 1 beside it, and the site keeps one"
                  " like, theirs",
                  h and h["pressed"] == "true" and h["liked"] and h["label"] == "Liked, 1 like" and h["n"] == "1"
                  and [k[0] for k in kept] == ["dee"],
                  f"{h and (h['pressed'], h['label'], h['n'])}; kept {kept}")
            go(pg, f"/social/p/{p2}")
            h2 = pg.evaluate(HEART, sel)
            check("it is still liked when the page comes again: the site's word, not the page's",
                  h2 and h2["pressed"] == "true" and h2["n"] == "1" and h2["fill"] == 1 and h2["ink"] == 1,
                  f"{h2 and (h2['pressed'], h2['n'], h2['fill'], h2['ink'])}")
            tap_heart(pg, sel)
            h3 = pg.evaluate(HEART, sel)
            pg.wait_for_timeout(400)
            h3b = pg.evaluate(HEART, sel)
            check("the same tap takes it back: not pressed, 'Like', no number, and the like is gone",
                  h3 and h3["pressed"] == "false" and h3["label"] == "Like" and h3b and h3b["n"] is None
                  and likes_on(("p", p2)) == [],
                  f"{h3 and (h3['pressed'], h3['label'])}, then {h3b and h3b['n']}; kept {likes_on(('p', p2))}")
            sa1, j1 = like(dee, ("p", p2))
            sa2, j2 = like(dee, ("p", p2))
            check("one like a person a thing: liked twice, one is kept and the count says 1",
                  sa1 == 200 and sa2 == 200 and j2.get("liked") is True and j2.get("count") == 1
                  and len(likes_on(("p", p2))) == 1,
                  f"{sa1} {sa2} {j2}; kept {likes_on(('p', p2))}")
            like(dee, ("p", p2), liked=False)
            go(pg, f"/social/p/{p2}")
            pg.evaluate("() => { window.__lk.max = 0; window.__lk.sent = []; }")
            pg.evaluate("(s) => { const h = document.querySelector(s); h.click(); h.click(); h.click(); }", sel)
            pg.wait_for_timeout(1500)
            three = pg.evaluate(HEART, sel)
            lk3 = pg.evaluate("() => window.__lk")
            kept3 = likes_on(("p", p2))
            pg.evaluate("() => { window.__lk.max = 0; window.__lk.sent = []; }")
            pg.evaluate("(s) => { const h = document.querySelector(s); h.click(); h.click(); }", sel)
            pg.wait_for_timeout(1500)
            two = pg.evaluate(HEART, sel)
            lk2 = pg.evaluate("() => window.__lk")
            kept2 = likes_on(("p", p2))
            check("quick taps end where the last one left it, one request out at a time: three from nothing leave it"
                  " liked (one like kept, the site told once); two more leave it liked as it was (the site told both, in"
                  " order)",
                  three and three["pressed"] == "true" and len(kept3) == 1 and lk3["max"] == 1 and len(lk3["sent"]) == 1
                  and two and two["pressed"] == "true" and len(kept2) == 1 and lk2["max"] == 1
                  and [x and x["liked"] for x in lk2["sent"]] == [False, True],
                  f"three: {three and three['pressed']} kept {len(kept3)} out at once {lk3['max']} sent {lk3['sent']};"
                  f" two: {two and two['pressed']} kept {len(kept2)} out at once {lk2['max']} sent {lk2['sent']}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, cal)
            go(pg, f"/social/p/{p2}")
            tap_heart(pg, sel)
            mine = pg.evaluate(HEART, sel)
            check("you may like your own: its maker's tap likes it",
                  mine and mine["pressed"] == "true" and mine["n"] == "2" and [k[0] for k in likes_on(("p", p2))] == ["dee", "cal"],
                  f"{mine and mine['pressed']}; kept {likes_on(('p', p2))}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, dee)
            go(pg, "/social/")
            pg.locator(card(p2b) + " .lk-heart").scroll_into_view_if_needed()
            tap_heart(pg, card(p2b) + " .lk-heart")
            go(pg, f"/social/p/{p2b}")
            there = pg.evaluate(HEART, sel)
            check("liked on Home's card, it is liked on its own page too",
                  there and there["pressed"] == "true" and there["n"] == "1",
                  f"{there and (there['pressed'], there['n'])}")
            close_ctx(ctx, pg)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "who may like: refused and nothing kept; the limit; a refusal in the page puts the heart back"):
        try:
            eli = someone(b, "eli", "Eli Vance")
            fay = someone(b, "fay", "Fay Dunn")
            gus = someone(b, "gus", "Gus Lowe")
            hal = someone(b, "hal", "Hal Cole")
            ivy = someone(b, "ivy", "Ivy Nash")
            lim = someone(b, "lim", "Lim Soto")
            p3 = make_post(eli, "Section 3, Eli's")
            p3d = make_post(eli, "Section 3, Eli's, taken down")
            d3u = make_drawing(eli, "Section 3, Eli's, unlisted", seed=31, vis="unlisted")
            anon = Client()
            anon.get(f"/social/p/{p3}")
            sa_, ja = anon.post_json(f"/social/p/{p3}/like", {"liked": True})
            check("signed out, a like is refused (401, signed_out), and nothing is kept",
                  sa_ == 401 and isinstance(ja, dict) and ja.get("error") == "signed_out" and likes_on(("p", p3)) == [],
                  f"{sa_} {ja}")
            c = fay.client()
            c.get(f"/social/p/{p3}")
            s1, j1 = c.post_json(f"/social/p/{p3}/like", {"liked": True}, token="")
            c2 = Client(cookies=fay.ctx.cookies(BASE), xff=fay.xff, origin="https://elsewhere.example")
            c2.get(f"/social/p/{p3}")
            s2, j2 = c2.post_json(f"/social/p/{p3}/like", {"liked": True})
            check("without the page's token, or from another site, a like is refused as stale (403), nothing kept",
                  s1 == 403 and s2 == 403 and isinstance(j1, dict) and j1.get("error") == "stale"
                  and isinstance(j2, dict) and j2.get("error") == "stale" and likes_on(("p", p3)) == [],
                  f"{s1} {j1}; {s2} {j2}")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'gus'")
            s3, j3 = like(gus, ("p", p3))
            check("somebody taken down cannot like (403, taken_down), nothing kept",
                  s3 == 403 and isinstance(j3, dict) and j3.get("error") == "taken_down" and likes_on(("p", p3)) == [],
                  f"{s3} {j3}")
            block(hal, "eli")
            block(eli, "ivy")
            s4, j4 = like(hal, ("p", p3))
            s5, j5 = like(ivy, ("p", p3))
            check("a block either way closes it: liking the post of somebody you blocked, or who blocked you, is"
                  " refused as gone (404), nothing kept",
                  s4 == 404 and s5 == 404 and j4.get("error") == "gone" and j5.get("error") == "gone"
                  and likes_on(("p", p3)) == [],
                  f"{s4} {j4}; {s5} {j5}")
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (p3d,))
            s6, _ = like(fay, ("p", p3d))
            s7, _ = like(eli, ("p", p3d))
            ctx, pg = browser_as(b, eli)
            go(pg, "/social/")
            down_card = pg.evaluate(HEART, card(p3d) + " .lk-heart")
            down_shown = pg.evaluate("(s) => !!document.querySelector(s)", card(p3d))
            go(pg, f"/social/p/{p3d}")
            down_page = pg.evaluate("() => !!document.querySelector('.lk-heart, [data-like-by]')")
            close_ctx(ctx, pg)
            check("a post taken down takes no likes from anybody, its maker included (404), and shows its maker no"
                  " heart, on Home's card or its page",
                  s6 == 404 and s7 == 404 and likes_on(("p", p3d)) == [] and down_shown and down_card is None
                  and not down_page,
                  f"{s6} {s7}; card shown {down_shown}, heart {down_card}; on its page {down_page}")
            s8, _ = like(fay, ("s", d3u))
            s9, _ = like(fay, ("s", skribl_of(p3)))
            check("a drawing kept unlisted, and a post's own drawing asked as a drawing, take no likes (404)",
                  s8 == 404 and s9 == 404 and likes_on(("s", d3u)) == [] and likes_on(("s", skribl_of(p3))) == [],
                  f"{s8} {s9}")
            s10, j10 = like(fay, ("p", p3), raw={})
            s11, j11 = like(fay, ("p", p3), raw={"liked": "yes"})
            check("a like that is not a yes or a no is refused (400), nothing kept",
                  s10 == 400 and s11 == 400 and likes_on(("p", p3)) == [], f"{s10} {j10}; {s11} {j11}")
            c = lim.client()
            c.get(f"/social/p/{p3}")
            codes = [c.post_json(f"/social/p/{p3}/like", {"liked": i % 2 == 0})[0] for i in range(120)]
            s12, j12 = c.post_json(f"/social/p/{p3}/like", {"liked": True})
            check("likes are limited a person: 120 an hour, likes and taking back alike, then 429 (limited), nothing kept",
                  codes.count(200) == 120 and s12 == 429 and isinstance(j12, dict) and j12.get("error") == "limited"
                  and all(k[0] != "lim" for k in likes_on(("p", p3))),
                  f"{codes.count(200)} answered 200, then {s12} {j12}")
            ctx, pg = browser_as(b, fay)
            go(pg, f"/social/p/{p3}")
            block(eli, "fay")
            sel = ".post-page > .post-meta .lk-heart"
            tap_heart(pg, sel, after=700)
            back = pg.evaluate(HEART, sel)
            said = pg.evaluate("() => { const s = document.querySelector('[data-page-say]'); return s && !s.hidden ? s.textContent : null; }")
            close_ctx(ctx, pg)
            check("refused in the page (blocked after it opened), the heart goes back and the page says why, kindly",
                  back and back["pressed"] == "false" and back["n"] is None
                  and said == "That isn’t here anymore. Reload the page to see what’s new." and likes_on(("p", p3)) == [],
                  f"{back and (back['pressed'], back['n'])}; said {said!r}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "counted by the viewer: a block either way, and anybody taken down, neither shown nor counted"):
        try:
            joy = someone(b, "joy", "Joy Marsh")
            kim = someone(b, "kim", "Kim Ford")
            lee = someone(b, "lee", "Lee Hart")
            moe = someone(b, "moe", "Moe Quinn")
            nia = someone(b, "nia", "Nia Shaw")
            oli = someone(b, "oli", "Oli West")
            p4 = make_post(joy, "Section 4, Joy's")
            for who in (kim, lee, moe):
                like(who, ("p", p4))

            def n_for(who):
                ctx, pg = browser_as(b, who)
                go(pg, "/social/")
                h1 = pg.evaluate(HEART, card(p4) + " .lk-heart")
                go(pg, f"/social/p/{p4}")
                h2 = pg.evaluate(HEART, ".post-page > .post-meta .lk-heart")
                by = pg.evaluate(BY)
                close_ctx(ctx, pg)
                return (h1 and h1["n"], h2 and h2["n"], by and by["words"])

            block(nia, "kim")
            seen_nia, seen_oli = n_for(nia), n_for(oli)
            check("a like by somebody the viewer blocked is neither shown nor counted for them, on Home's card and the"
                  " post's page; everybody else counts it",
                  seen_nia[:2] == ("2", "2") and seen_oli[:2] == ("3", "3"), f"nia {seen_nia}; oli {seen_oli}")
            block(moe, "nia")
            seen_nia2 = n_for(nia)
            check("a like by somebody who blocked the viewer, the same",
                  seen_nia2[:2] == ("1", "1"), f"nia {seen_nia2}")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'lee'")
            seen_oli2 = n_for(oli)
            anon_n = re.search(r'class="lk-n">(\d+)<', Client().get(f"/social/p/{p4}")[1])
            check("a like by somebody taken down counts for nobody, signed out included",
                  seen_oli2[:2] == ("2", "2") and anon_n and anon_n.group(1) == "2",
                  f"oli {seen_oli2}; signed out {anon_n and anon_n.group(1)}")
            block(joy, "kim")
            seen_jo = n_for(joy)
            check("its maker's count and 'Liked by…' leave out the same people (a block, a takedown)",
                  seen_jo == ("1", "1", "Liked by Moe"), f"joy {seen_jo}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "each like keeps its moment: where the replay was while it played, on the drawing's clock"):
        try:
            pat = someone(b, "pat", "Pat Lin")
            quin = someone(b, "quin", "Quin Roy")
            rui = someone(b, "rui", "Rui Sol")
            sid_ = someone(b, "sid", "Sid Kerr")
            # Six seconds of drawing, so a tap lands well inside it.
            long_ = drawing(n=200, seed=5, step=30)
            p5 = make_post(pat, "Section 5, Pat's slow one", payload=long_)
            p5b = make_post(pat, "Section 5, Pat's second", payload=long_)
            sel = ".post-page > .post-meta .lk-heart"
            ctx, pg = browser_as(b, quin)
            go(pg, f"/social/p/{p5}", wait=0)
            pg.wait_for_function("() => { const art = document.querySelector('.post-page > .post-art');"
                                 " const p = art && window.SkriblInline && SkriblInline.mount(art)[0];"
                                 " return !!p && p.playhead().playing && p.playhead().ms > 600; }", timeout=15000)
            before = pg.evaluate(PLAYHEAD)
            pg.locator(sel).tap()
            after = pg.evaluate(PLAYHEAD)
            pg.wait_for_timeout(700)
            kept = likes_on(("p", p5))
            at = kept[0][1] if kept else None
            check("tapped while the post's drawing plays on its page, the like keeps where the replay was: between the"
                  " playhead read just before the tap and just after",
                  before and after and before["playing"] and at is not None and before["ms"] - 1 <= at <= after["ms"] + 1,
                  f"before {before}, kept {at}, after {after}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, rui)
            go(pg, f"/social/p/{p5b}", wait=0)
            pg.wait_for_function("() => { const art = document.querySelector('.post-page > .post-art');"
                                 " const p = art && window.SkriblInline && SkriblInline.mount(art)[0];"
                                 " return !!p && p.state().loaded; }", timeout=15000)
            pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.seek(0); p.setRate(4); window.__t0 = performance.now(); p.play(); }")
            pg.wait_for_timeout(400)
            before4, wall = pg.evaluate("() => [(" + PLAYHEAD + ")(), performance.now() - window.__t0]")
            pg.locator(sel).tap()
            after4 = pg.evaluate(PLAYHEAD)
            pg.wait_for_timeout(700)
            kept4 = likes_on(("p", p5b))
            at4 = kept4[0][1] if kept4 else None
            check("watched at 4x, the moment is the drawing's, not the watcher's: between the reads either side of the"
                  " tap, and well past the time spent watching",
                  at4 is not None and before4 and after4 and before4["ms"] - 1 <= at4 <= after4["ms"] + 1
                  and at4 >= 2 * wall,
                  f"before {before4} ({round(wall)} ms watched), kept {at4}, after {after4}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, sid_)
            go(pg, "/social/")
            pg.locator(card(p5) + " .lk-heart").scroll_into_view_if_needed()
            tap_heart(pg, card(p5) + " .lk-heart")
            still_at = [k for k in likes_on(("p", p5)) if k[0] == "sid"]
            go(pg, f"/social/p/{p5b}", wait=0)
            pg.wait_for_function("() => { const art = document.querySelector('.post-page > .post-art');"
                                 " const p = art && window.SkriblInline && SkriblInline.mount(art)[0];"
                                 " return !!p && p.playhead().playing && p.playhead().ms > 300; }", timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            paused = pg.evaluate(PLAYHEAD)
            tap_heart(pg, sel)
            paused_at = [k for k in likes_on(("p", p5b)) if k[0] == "sid"]
            close_ctx(ctx, pg)
            check("tapped while it is still (Home's card before Play) or paused, a like keeps no moment, and counts all"
                  " the same",
                  still_at == [("sid", None)] and paused and not paused["playing"] and paused["ms"] > 0
                  and paused_at == [("sid", None)] and len(likes_on(("p", p5))) == 2,
                  f"still {still_at}; paused at {paused} kept {paused_at}")
            ups = []
            for raw, want in ((-5, None), (10 ** 12, None), ("1200", None), (True, None), (1234.6, 1235), (0, 0),
                              (24 * 3600 * 1000, 24 * 3600 * 1000), (24 * 3600 * 1000 + 1, None)):
                like(sid_, ("p", p5), liked=False)
                like(sid_, ("p", p5), raw={"liked": True, "at_ms": raw})
                got = [k[1] for k in likes_on(("p", p5)) if k[0] == "sid"]
                ups.append((raw, want, got))
            check("the site keeps only a moment it can: a whole number of ms from 0 to a day (rounded); anything else is"
                  " no moment, the like kept all the same",
                  all(got == [want] for _, want, got in ups), json.dumps(ups))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "kind, never jumpy: the heart draws and fills, fades back; the count fades, the heart glides"):
        try:
            rae = someone(b, "rae", "Rae Oaks")
            sam = someone(b, "sam", "Sam Pike")
            tam = someone(b, "tam", "Tam Gray")
            p6 = make_post(rae, "Section 6, Rae's")
            p6z = make_post(rae, "Section 6, Rae's, nobody's yet")
            p6r = make_post(rae, "Section 6, Rae's, for Reduce Motion")
            like(tam, ("p", p6))
            like(tam, ("p", p6r))
            sel = ".post-page > .post-meta .lk-heart"

            def frames(pg, ms=900):
                pg.locator(sel).scroll_into_view_if_needed()
                pg.wait_for_timeout(200)
                pg.evaluate(HSAMPLE, [sel, ms])
                pg.wait_for_timeout(60)
                pg.locator(sel).tap()
                pg.wait_for_timeout(ms + 200)
                return pg.evaluate("() => window.__hf")

            ctx, pg = browser_as(b, sam)
            go(pg, f"/social/p/{p6}")
            fs = frames(pg)
            offs = [f["off"] for f in fs]
            steps = [abs(q - p) for p, q in zip(offs, offs[1:])]
            end = fs[-1] if fs else {}
            check("liked, the blush line draws itself round over many frames (none carries a third of it), the blush"
                  " fills behind it and the grey line fades under it; the heart's box never grows or moves",
                  len([o for o in offs if 0.02 < o < 0.98]) >= 8 and max(steps or [1]) <= 0.34
                  and faded([f["fill"] for f in fs]) >= 3 and faded([f["line"] for f in fs]) >= 3
                  and end.get("off") == 0 and end.get("fill") == 1 and end.get("line") == 0 and end.get("ink") == 1
                  and all(spread(fs, k) < 0.5 for k in ("x", "y", "w", "h")),
                  f"{len(fs)} frames: drawing on {len([o for o in offs if 0.02 < o < 0.98])}, biggest {round(max(steps or [0]), 3)};"
                  f" fill {faded([f['fill'] for f in fs])}, line {faded([f['line'] for f in fs])} part-way;"
                  f" box moved {[spread(fs, k) for k in ('x', 'y', 'w', 'h')]}")
            fs = frames(pg)
            moving = [f for f in fs if 0.03 < f["ink"] < 0.97]
            gone_at = next((f["t"] for f in fs if f["ink"] < 0.01 and f["fill"] < 0.01 and f["line"] > 0.99), None)
            start_at = next((f["t"] for f in fs if f["ink"] < 0.99), None)
            check("taken back, the blush and its line fade in about a fifth of a second, nothing un-drawing (the line"
                  " whole while it fades), and the grey line comes back; the box never moves",
                  len(moving) >= 3 and all(f["off"] < 0.01 for f in fs if f["ink"] > 0.05)
                  and faded([f["fill"] for f in fs]) >= 3 and faded([f["line"] for f in fs]) >= 3
                  and gone_at is not None and start_at is not None and gone_at - start_at <= 450
                  and all(spread(fs, k) < 0.5 for k in ("x", "y", "w", "h")),
                  f"fading on {len(moving)} frames, un-drawn while showing {[f['off'] for f in fs if f['ink'] > 0.05 and f['off'] >= 0.01][:3]};"
                  f" gone in {gone_at and start_at is not None and gone_at - start_at} ms")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, sam, reduced=True)
            go(pg, f"/social/p/{p6r}")
            fs = frames(pg)
            shown = [f for f in fs if f["ink"] > 0.03]
            check("under Reduce Motion nothing draws: the blush line is whole from its first frame and fades in where it"
                  " sits, the box never moving",
                  faded([f["ink"] for f in fs]) >= 2 and shown and all(f["dash"] == "none" or f["off"] < 0.01 for f in shown)
                  and fs[-1]["ink"] == 1 and all(spread(fs, k) < 0.5 for k in ("x", "y", "w", "h")),
                  f"fading in on {faded([f['ink'] for f in fs])} frames; dash {shown and shown[0]['dash']} off {shown and shown[0]['off']}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, sam)
            go(pg, f"/social/p/{p6z}")
            fs = frames(pg)
            g = glide_of([f["x"] for f in fs])
            ns = [f["n"] for f in fs if f["n"] is not None]
            fs2 = frames(pg)
            g2 = glide_of([f["x"] for f in fs2])
            ns2 = [f["n"] for f in fs2 if f["n"] is not None]
            first_move = next((i for i, f in enumerate(fs2) if abs(f["x"] - fs2[0]["x"]) > 0.3), None)
            first_fade = next((i for i, f in enumerate(fs2) if f["n"] is not None and f["n"] < 0.97), None)
            check("a count that comes fades in, and the heart glides aside for it (no frame carries half the way); one"
                  " that goes fades first, then the heart glides back",
                  faded(ns) >= 2 and g["way"] >= 6 and g["frames"] >= 4 and g["step"] <= 0.5 * g["way"]
                  and faded(ns2) >= 2 and g2["way"] >= 6 and g2["frames"] >= 4 and g2["step"] <= 0.5 * g2["way"]
                  and first_fade is not None and first_move is not None and first_fade < first_move,
                  f"comes: fading {faded(ns)}, glide {g}; goes: fading {faded(ns2)}, glide {g2},"
                  f" fade from frame {first_fade}, move from {first_move}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, tam, reduced=True)
            go(pg, f"/social/p/{p6z}")
            fs = frames(pg)
            ns = [f["n"] for f in fs if f["n"] is not None]
            close_ctx(ctx, pg)
            check("under Reduce Motion a count that comes fades in, and nothing glides: the heart takes its place",
                  faded(ns) >= 2 and all(f["tf"] == "none" for f in fs),
                  f"fading {faded(ns)}; transforms {sorted({f['tf'] for f in fs})[:2]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "signed out: the heart is there; a tap raises the sheet that says how; Sign in comes back"):
        try:
            tia = someone(b, "tia", "Tia Ruiz")
            uma = someone(b, "uma", "Uma Vale")
            vee = someone(b, "vee", "Vee Ames")
            p7 = make_post(tia, "Section 7, Tia's")
            d7 = make_drawing(tia, "Section 7, Tia's drawing", seed=71)
            like(vee, ("p", p7))
            ctx, pg = browser_as(b, None)
            go(pg, f"/social/p/{p7}")
            sel = ".post-page > .post-meta .lk-heart"
            h = pg.evaluate(HEART, sel)
            check("signed out, the heart is there with its count, not pressed, and it asks for a sheet",
                  h and h["pressed"] == "false" and h["n"] == "1" and h["out"] and h["like"] is None and h["hit"],
                  f"{h and (h['pressed'], h['n'], h['out'], h['hit'])}")
            pg.locator(sel).tap()
            pg.wait_for_timeout(600)
            o = pg.evaluate(OUT)
            check("a tap raises the small sheet, in a sheet's paper: 'Like this drawing?', 'Sign in, and a tap on the"
                  " heart lets Tia know you like it.', Not now and Sign in",
                  o and o["open"] and o["role"] == "dialog" and o["paper"] == SHEET_PAPER["light"]
                  and o["title"] == "Like this drawing?"
                  and o["lede"] == "Sign in, and a tap on the heart lets Tia know you like it."
                  and o["acts"] == ["Not now", "Sign in"],
                  json.dumps(o))
            pg.locator("#likeOutSheet .post-sheet-acts [data-make-close]").tap()
            pg.wait_for_timeout(700)
            o2 = pg.evaluate(OUT)
            back = pg.evaluate("() => document.activeElement && document.activeElement.classList.contains('lk-heart')")
            check("Not now puts it away and gives the heart its focus back; nothing is liked",
                  o2 and not o2["open"] and back and len(likes_on(("p", p7))) == 1, f"open {o2 and o2['open']}, focus on the heart {back}")
            check("Sign in goes to signing in, with this page to come back to",
                  o and o["href"] == f"/social/signin?next=/social/p/{p7}", f"{o and o['href']}")
            go(pg, f"/social/b/{d7}")
            pg.locator(sel).tap()
            pg.wait_for_timeout(600)
            od = pg.evaluate(OUT)
            close_ctx(ctx, pg)
            check("on a drawing's own page too, naming its maker, and coming back to it",
                  od and od["open"] and od["lede"] == "Sign in, and a tap on the heart lets Tia know you like it."
                  and od["href"] == f"/social/signin?next=/social/b/{d7}", json.dumps(od))
            # Uma, signed out in her own browser (her passkey is in it), taps the
            # heart, then Sign in, then her passkey.
            upg = uma.pg
            upg.goto(BASE + "/social/you")
            with upg.expect_navigation(timeout=15000):
                upg.click("form[action$='/social/signout'] button", timeout=5000)
            go(upg, f"/social/p/{p7}")
            upg.locator(sel).tap()
            upg.wait_for_timeout(600)
            tap_to(upg, upg.locator("#likeOutSheet .post-sheet-acts a"))
            try:
                with upg.expect_navigation(timeout=20000):
                    upg.click("[data-passkey=signin]", timeout=5000)
                ready(upg)
            except Exception:  # noqa: BLE001 -- not landing is the row's red
                pass
            upg.wait_for_timeout(1200)
            landed = urllib.parse.urlparse(upg.url).path
            hu = upg.evaluate(HEART, sel)
            check("signed in from there, they land on the same page, and the heart waits: not pressed, nothing liked for"
                  " them",
                  landed == f"/social/p/{p7}" and hu and hu["pressed"] == "false" and hu["like"]
                  and all(k[0] != "uma" for k in likes_on(("p", p7))),
                  f"landed {landed}; heart {hu and (hu['pressed'], hu['like'])}; kept {likes_on(('p', p7))}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "'Liked by…', the maker's alone: its words, faces and sheet; nobody else is shown who"):
        try:
            vic = someone(b, "vic", "Vic Bryn")
            likers = [someone(b, h, n) for h, n in (("wes", "Wes Abel"), ("xia", "Xia Chen"), ("yan", "Yan Dray"),
                                                    ("zed", "Zed Eck"), ("abe", "Abe Finch"))]
            faces = {who.handle: give_face(who, 80 + i) for i, who in enumerate(likers)}
            p8 = make_post(vic, "Section 8, Vic's")
            p8z = make_post(vic, "Section 8, Vic's, nobody's yet")
            moments = {"wes": 6000, "xia": None, "yan": 72500, "zed": 3723000, "abe": 0}
            said = []
            ctx, pg = browser_as(b, vic)
            for who in likers:
                like(who, ("p", p8), at=moments[who.handle])
                db_write("update social_likes set created_at = datetime('now', ?) where person_id ="
                         " (select id from social_people where handle_key = ?)",
                         (f"-{10 - len(said)} minutes", who.handle))
                go(pg, f"/social/p/{p8}")
                by = pg.evaluate(BY)
                said.append(by and by["words"])
            check("its maker sees 'Liked by…' under the time-and-plays line, newest first: 'Liked by Wes', 'Liked by Xia"
                  " and Wes', 'Liked by Yan, Xia and Wes', then two names and how many more",
                  said == ["Liked by Wes", "Liked by Xia and Wes", "Liked by Yan, Xia and Wes",
                           "Liked by Zed, Yan and 2 others", "Liked by Abe, Zed and 3 others"], json.dumps(said))
            by = pg.evaluate(BY)
            m = pg.evaluate(META)
            check("the newest three faces, theirs, and the whole line one target (44px tall, painted) under the line,"
                  " opening a sheet",
                  by and by["faces"] == [f"/s/{faces[h]}/poster" for h in ("abe", "zed", "yan")] and by["h"] >= 44
                  and by["hit"] and by["popup"] == "dialog" and by["id"] == "liked" and m and by["top"] >= m["bottom"],
                  json.dumps(by))
            pg.locator("[data-like-by]").tap()
            pg.wait_for_timeout(700)
            sh = pg.evaluate(SHEET)
            want = [("Abe Finch", "@abe", "0:00"), ("Zed Eck", "@zed", "1:02:03"), ("Yan Dray", "@yan", "1:12"),
                    ("Xia Chen", "@xia", None), ("Wes Abel", "@wes", "0:06")]
            check("the sheet of who, Make's own (its paper, the people on one card): 'Liked by', newest first, each with"
                  " their face, name, @handle and when, and the moment their heart landed where one was kept, its dot"
                  " the heart's blush; 'Only you can see who liked it.'",
                  sh and sh["open"] and sh["role"] == "dialog" and sh["paper"] == SHEET_PAPER["light"]
                  and sh["card"] == ROW_BG["light"] and sh["title"] == "Liked by"
                  and [(r["name"], r["handle"], r["at"]) for r in sh["rows"]] == want
                  and all(r["when"] for r in sh["rows"]) and all((r["dot"] == HEART_INK["light"]) == (r["at"] is not None) for r in sh["rows"])
                  and [r["face"] for r in sh["rows"]] == [f"/s/{faces[h]}/poster" for h in ("abe", "zed", "yan", "xia", "wes")]
                  and sh["note"] == "Only you can see who liked it.",
                  json.dumps(sh)[:600])
            tap_to(pg, pg.locator("#likeSheet .lk-row").first)
            check("a row opens their page", urllib.parse.urlparse(pg.url).path == "/social/@abe", pg.url)
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, likers[0])
            go(pg, f"/social/p/{p8}")
            html = pg.content()
            other = pg.evaluate("() => ({ by: !!document.querySelector('[data-like-by]'), sheet: !!document.getElementById('likeSheet') })")
            close_ctx(ctx, pg)
            names = [n for n in ("@xia", "@yan", "@zed", "@abe", "Xia", "Yan Dray", "Zed Eck", "Abe Finch") if n in html]
            check("nobody else is shown who: on a liker's own view there is no 'Liked by…', no sheet of who, and none of"
                  " the others' names or handles anywhere in the page",
                  not other["by"] and not other["sheet"] and not names, f"{other}; names in the page {names}")
            ctx, pg = browser_as(b, vic)
            go(pg, f"/social/p/{p8}")
            sel = ".post-page > .post-meta .lk-heart"
            tap_heart(pg, sel)
            by1 = pg.evaluate(BY)
            pg.locator("[data-like-by]").tap()
            pg.wait_for_timeout(600)
            rows1 = [r["handle"] for r in (pg.evaluate(SHEET) or {}).get("rows", [])]
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            tap_heart(pg, sel)
            by2 = pg.evaluate(BY)
            rows2 = [r["handle"] for r in (pg.evaluate(SHEET) or {}).get("rows", [])]
            check("its maker's own like says so at once, 'you' first, and their row is in the sheet; taken back, gone"
                  " again, with no reload",
                  by1 and by1["words"] == "Liked by you, Abe and 4 others" and rows1[:1] == ["@vic"]
                  and by2 and by2["words"] == "Liked by Abe, Zed and 3 others" and "@vic" not in rows2,
                  f"{by1 and by1['words']} {rows1[:2]}; {by2 and by2['words']} {rows2[:2]}")
            go(pg, f"/social/p/{p8z}")
            none_yet = pg.evaluate(BY)
            pg.locator(sel).scroll_into_view_if_needed()
            pg.evaluate(BSAMPLE, 900)
            tap_heart(pg, sel, after=1100)
            bf = pg.evaluate("() => window.__bf")
            came = pg.evaluate(BY)
            hs = [f["h"] for f in bf if f.get("there")]
            acts = glide_of([f["acts"] for f in bf if f["acts"] is not None])
            check("where nobody has liked it its maker sees no line; their own first like brings 'Liked by you', its"
                  " room opening over many frames (what is under it glides down, never in one frame)",
                  none_yet is None and came and came["words"] == "Liked by you" and len(set(round(x) for x in hs)) >= 4
                  and acts["way"] >= 30 and acts["frames"] >= 4 and acts["step"] <= 0.5 * acts["way"],
                  f"before {none_yet}; after {came and came['words']}; heights {len(set(round(x) for x in hs))}; under it {acts}")
            pg.evaluate(BSAMPLE, 900)
            tap_heart(pg, sel, after=1100)
            bf = pg.evaluate("() => window.__bf")
            acts2 = glide_of([f["acts"] for f in bf if f["acts"] is not None])
            went = pg.evaluate(BY)
            close_ctx(ctx, pg)
            check("taken back, the line's room closes the same way and the line is gone",
                  went is None and acts2["way"] >= 30 and acts2["frames"] >= 4 and acts2["step"] <= 0.5 * acts2["way"],
                  f"after {went}; under it {acts2}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "Activity: a like is a row; likes never light the dot; grouped; Earlier one a post; the landing"):
        try:
            nell = someone(b, "nell", "Nell Ward")
            otto = someone(b, "otto", "Otto Lund")
            piet = someone(b, "piet", "Piet Mol")
            rosa = someone(b, "rosa", "Rosa Vidal")
            sven = someone(b, "sven", "Sven Aho")
            fo, fp, fr = give_face(otto, 91), give_face(piet, 92), give_face(rosa, 93)
            p9a = make_post(nell, "Section 9, Nell's first")
            p9b = make_post(nell, "Section 9, Nell's second")
            d9 = make_drawing(nell, "Section 9, Nell's drawing", seed=94)
            ctx, pg = browser_as(b, nell)
            go(pg, "/social/activity")       # nothing yet: seen from now
            like(otto, ("p", p9a))
            go(pg, "/social/")
            bell = pg.evaluate(DOT, "a.top-bell")
            close_ctx(ctx, pg)
            dctx, dpg = browser_as(b, nell, screen="desk")
            go(dpg, "/social/")
            rail = dpg.evaluate(DOT, "nav.nav a.tab-activity")
            close_ctx(dctx, dpg)
            check("a like never lights the bell's dot: with only a like new, no dot on a phone's bell nor a desk's rail",
                  bell is False and rail is False, f"bell {bell}, rail {rail}")
            ctx, pg = browser_as(b, nell)
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            new = next((s["rows"] for s in secs if s["sec"] == "New"), [])
            r0 = new[0] if new else {}
            check("it waits in Activity under New, with its own dot: 'Otto liked your post', when, their face wearing a"
                  " small liked heart (painted), the post's small picture, and no words of its own",
                  len(new) == 1 and r0.get("say") == "Otto liked your post" and r0.get("isNew")
                  and r0.get("mark") == HEART_INK["light"] and r0.get("when") and r0.get("faces") == [f"/s/{fo}/poster"]
                  and r0.get("badge") and r0["badge"]["painted"] and r0["badge"]["ink"] == HEART_INK["light"]
                  and r0["badge"]["fill"] == BLUSH and r0["badge"]["inkOp"] == 1 and r0["badge"]["fillOp"] == 1
                  and f"/s/{skribl_of(p9a)}/poster" in (r0.get("pic") or "") and r0.get("peek") is None,
                  json.dumps(r0)[:400])
            check("the row opens the post at 'Liked by…' (#liked)", r0.get("href") == f"/social/p/{p9a}#liked", r0.get("href"))
            like(piet, ("p", p9a))
            like(rosa, ("p", p9a))
            like(sven, ("p", p9b))
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            new = next((s["rows"] for s in secs if s["sec"] == "New"), [])
            earlier = next((s["rows"] for s in secs if s["sec"] == "Earlier"), [])
            ra = next((r for r in new if r["href"].startswith(f"/social/p/{p9a}")), {})
            check("several since you last looked on one post are one row, the newest face in front ('Rosa and Piet liked"
                  " your post'); another post its own row; what came before under Earlier",
                  ra.get("say") == "Rosa and Piet liked your post" and ra.get("front") == f"/s/{fr}/poster"
                  and sorted(ra.get("faces") or []) == sorted([f"/s/{fr}/poster", f"/s/{fp}/poster"])
                  and any(r["say"] == "Sven liked your post" for r in new)
                  and [r["say"] for r in earlier] == ["Otto liked your post"],
                  f"new {[r['say'] for r in new]} front {ra.get('front')}; earlier {[r['say'] for r in earlier]}")
            like(nell, ("p", p9a))
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            new = next((s["rows"] for s in secs if s["sec"] == "New"), [])
            earlier = next((s["rows"] for s in secs if s["sec"] == "Earlier"), [])
            check("a like says no words, so Earlier keeps likes one row a post too ('Rosa and 2 others liked your post');"
                  " and you never see yourself, your own like on your own post in no row and no count",
                  [r["say"] for r in earlier if r["href"].startswith(f"/social/p/{p9a}#liked")] == ["Rosa and 2 others liked your post"]
                  and not any("Nell" in r["say"] for r in new + earlier) and not any(r["href"].startswith(f"/social/p/{p9a}#liked") for r in new),
                  f"new {[r['say'] for r in new]}; earlier {[r['say'] for r in earlier]}")
            block(nell, "sven")
            like(otto, ("s", d9))
            go(pg, "/social/activity")
            secs = pg.evaluate(ROWS)
            every = [r for s in secs for r in s["rows"]]
            dr = next((r for r in every if r["href"].startswith(f"/social/b/{d9}")), {})
            check("somebody hidden from you is in no row: blocked, Sven's like is gone from the list",
                  not any("Sven" in r["say"] for r in every), json.dumps([r["say"] for r in every]))
            check("a like on a drawing shown outside a post is a row too, opening its own page at 'Liked by…'",
                  dr.get("say") == "Otto liked your post" and dr.get("href") == f"/social/b/{d9}#liked"
                  and f"/s/{d9}/poster" in (dr.get("pic") or ""), json.dumps(dr)[:300])
            c = piet.client()
            c.get(f"/social/p/{p9b}")
            c.post_json(f"/social/p/{p9b}/comments", {"words": "Section 9, Piet says something"})
            go(pg, "/social/")
            lit = pg.evaluate(DOT, "a.top-bell")
            close_ctx(ctx, pg)
            check("comments still light the dot: something said is new", lit is True, f"bell {lit}")
            ctx, pg = browser_as(b, nell, init=LANDING)
            go(pg, "/social/activity")
            row = pg.locator("a.act-row", has_text="liked your post").first
            href = row.get_attribute("href")
            tap_to(pg, row)
            try:
                ready(pg)
            except Exception:  # noqa: BLE001
                pass
            pg.wait_for_timeout(4200)
            lf = pg.evaluate("() => window.__lf")
            vh = pg.evaluate("() => innerHeight")
            close_ctx(ctx, pg)
            landed = [f for f in lf if f.get("landed")]
            ops = [f["op"] for f in landed]
            # Where it sits while its tint fades (the page's own jump to the
            # address's #liked, as it arrives, is the browser's, not a motion).
            tops = [f["top"] for f in landed if 0.03 < f["op"] < 0.97]
            check("a like row lands on the post with 'Liked by…' in view, glowing in the note's tint, then the tint fades"
                  " over many frames where it sits, nothing moving",
                  href and href.endswith("#liked") and landed and landed[0]["bg"] == TINT["light"]
                  and faded(ops) >= 8 and ops[-1] < 0.05 and tops and 0 <= tops[-1] and landed[-1]["bottom"] <= vh
                  and spread([{"t": t} for t in tops], "t") < 0.5,
                  f"{href}; landed {len(landed)} frames, tint {landed and landed[0]['bg']}, fading {faded(ops)},"
                  f" last {ops and ops[-1]}; at {tops and tops[-1]} of {vh}, moved {spread([{'t': t} for t in tops], 't')}")
            ctx, pg = browser_as(b, nell, reduced=True, init=LANDING)
            go(pg, f"/social/p/{p9a}#liked", wait=4200)
            lf = pg.evaluate("() => window.__lf")
            close_ctx(ctx, pg)
            landed = [f for f in lf if f.get("landed")]
            tops = [f["top"] for f in landed if 0.03 < f["op"] < 0.97]
            check("under Reduce Motion it lands the same: the tint fades where it sits, nothing moving",
                  landed and faded([f["op"] for f in landed]) >= 8 and tops and spread([{"t": t} for t in tops], "t") < 0.5
                  and 0 <= tops[-1] and landed[-1]["bottom"] <= 874,
                  f"fading {faded([f['op'] for f in landed])}; moved {spread([{'t': t} for t in tops], 't')}")
            ctx, pg = browser_as(b, nell, screen="desk")
            go(pg, "/social/activity")
            sub = pg.evaluate("() => document.querySelector('.act-head .page-sub').textContent")
            close_ctx(ctx, pg)
            fresh = someone(b, "wren", "Wren Ash")
            ctx, pg = browser_as(b, fresh)
            go(pg, "/social/activity")
            empty = pg.evaluate("() => (document.querySelector('.act-empty-words') || {}).textContent")
            close_ctx(ctx, pg)
            check("Activity's words say likes: 'Who liked your posts or said something on them, and who answered you.',"
                  " and with nothing yet 'When someone likes your post, says something on it, or answers you, you’ll see"
                  " it here.'",
                  sub == "Who liked your posts or said something on them, and who answered you."
                  and empty == "When someone likes your post, says something on it, or answers you, you’ll see it here.",
                  f"{sub!r}; {empty!r}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "deleting takes the likes, in code: a post, a drawing, an account"):
        try:
            ora = someone(b, "ora", "Ora Penn")
            pip = someone(b, "pip", "Pip Rand")
            p10 = make_post(ora, "Section 10, Ora's")
            d10 = make_drawing(ora, "Section 10, Ora's drawing", seed=101)
            like(pip, ("p", p10))
            like(ora, ("p", p10))
            like(pip, ("s", d10))
            c = ora.client()
            c.get(f"/social/p/{p10}")
            sd, _ = c.post_json(f"/social/p/{p10}/delete", {})
            c.get(f"/social/b/{d10}")
            sdd, _ = c.post_json(f"/social/b/{d10}/delete", {})
            check("a post deleted through its ⋯ goes with its likes, and a drawing deleted from its own page with its"
                  " likes (a drawing's likes have no cascade under them: only the code takes them)",
                  sd == 200 and sdd == 200 and db("select count(*) from social_likes l join social_people p on"
                                                   " p.id = l.owner_id where p.handle_key = 'ora'") == [(0,)],
                  f"{sd} {sdd}; left {db('select post_id, drawing_id from social_likes where owner_id = (select id from social_people where handle_key = ?)', ('ora',))}")
            qua = someone(b, "qua", "Qua Senn")
            rex = someone(b, "rex", "Rex Tam")
            p10b = make_post(rex, "Section 10, Rex's")
            p10c = make_post(qua, "Section 10, Qua's")
            like(qua, ("p", p10b))
            like(rex, ("p", p10c))
            c = qua.client()
            c.get("/social/you/delete")
            st, _ = c.post_form("/social/you/delete", {"confirm": "qua"})
            left = db("select count(*) from social_likes l where l.person_id not in (select id from social_people)"
                      " or l.owner_id not in (select id from social_people)")
            check("an account deleted goes with its likes and every like on what it made",
                  st == 200 and left == [(0,)] and likes_on(("p", p10b)) == [], f"{st}; left {left}")
            # With the cascade off, on a copy: the code alone.
            sly = someone(b, "sly", "Sly Uhl")
            tex = someone(b, "tex", "Tex Vo")
            p10d = make_post(sly, "Section 10, Sly's")
            p10f = make_post(sly, "Section 10, Sly's second")
            p10e = make_post(tex, "Section 10, Tex's")
            d10t = make_drawing(tex, "Section 10, Tex's drawing", seed=102)
            like(tex, ("p", p10d))
            like(sly, ("p", p10d))
            like(sly, ("p", p10e))
            like(tex, ("p", p10e))
            like(tex, ("p", p10f))       # theirs, on what somebody else made
            like(sly, ("s", d10t))       # on what they made that no post takes with it
            copy = os.path.join(TMP, "probe.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            home_as = "; ".join(f"{c['name']}={c['value']}" for c in sly.ctx.cookies(BASE))
            probe = subprocess.run([sys.executable, "-c", PROBE, p10d, "tex", home_as], cwd=ROOT, capture_output=True, text=True,
                                   timeout=180, env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-600:]}
            PROBED = out
            check("with SQLite's cascade off (SKRIBL_SQLITE_FOREIGN_KEYS=0, on a copy) a post goes with its likes, by"
                  " the code (posts.drop_post)",
                  out.get("fk") == 0 and out.get("post") and out["post"][0] == 2 and out["post"][1] == 0,
                  json.dumps({k: v for k, v in out.items() if k != "plans"})[:400])
            check("...and an account with its likes (one on somebody else's post) and every like on what it made (one on"
                  " a drawing no post takes with it), by the code (accounts.delete_person)",
                  out.get("person") and out["person"][0] >= 2 and out["person"][1] >= 2 and out["person"][2:] == [0, 0],
                  json.dumps(out.get("person") or out.get("err")))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "the data: the chain on a populated database; one like a person a thing; the reads on their indexes"):
        try:
            mdb = os.path.join(TMP, "chain-likes.db")
            # The chain's head before likes (its migration's down_revision).
            BEFORE = "c276c1445bc1"

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
            con.execute("insert into social_posts (id, public_id, person_id, words, skribl_id, created_at)"
                        " values (10, 'P1', 1, 'hi', 'S1', ?)", (then,))
            con.commit()
            con.close()
            up2 = chain("upgrade", "head")
            idx = {r[0]: r[1] for r in at("select name, sql from sqlite_master where type = 'index' and tbl_name = 'social_likes'")}
            cols = [r[1] for r in at("pragma table_info(social_likes)")]
            sql = (at("select sql from sqlite_master where name = 'social_likes'") or [[""]])[0][0] or ""
            check("the site's chain on a database with people and posts in it adds social_likes (who, on a post or a"
                  " drawing, whose, when in the replay, when), its five indexes and its CHECK, touching nothing else",
                  up1.returncode == 0 and up2.returncode == 0
                  and cols == ["id", "post_id", "drawing_id", "owner_id", "person_id", "at_ms", "created_at"]
                  and set(idx) == {"ix_social_likes_person_post", "ix_social_likes_person_drawing", "ix_social_likes_post_created",
                                   "ix_social_likes_drawing_created", "ix_social_likes_owner_created"}
                  and "UNIQUE" in (idx.get("ix_social_likes_person_post") or "") and "UNIQUE" in (idx.get("ix_social_likes_person_drawing") or "")
                  and "ck_social_likes_on_one" in sql and at("select count(*) from social_posts") == [(1,)],
                  f"up {up1.returncode}/{up2.returncode} {up2.stderr.strip().splitlines()[-1:] if up2.returncode else ''};"
                  f" cols {cols}; indexes {sorted(idx)}")
            con = sqlite3.connect(mdb)
            errs = []
            for vals in ((1, 10, None), (1, 10, None), (2, 10, "S9"), (2, None, None)):
                try:
                    con.execute("insert into social_likes (person_id, post_id, drawing_id, owner_id, created_at)"
                                " values (?, ?, ?, 1, ?)", vals + (then,))
                    errs.append("kept")
                except sqlite3.IntegrityError as e:
                    errs.append(str(e).split(":")[0])
            con.rollback()
            con.close()
            check("one like a person a thing (a second is refused), and a like is on exactly one thing (both, or neither,"
                  " refused)", errs == ["kept", "UNIQUE constraint failed", "CHECK constraint failed", "CHECK constraint failed"],
                  json.dumps(errs))
            down = chain("downgrade", BEFORE)
            gone = at("select name from sqlite_master where tbl_name = 'social_likes'")
            check("taken back down, the chain drops the table and its indexes, every post kept",
                  down.returncode == 0 and gone == [] and at("select public_id from social_posts") == [("P1",)],
                  f"down {down.returncode} {down.stderr.strip().splitlines()[-1:] if down.returncode else ''}; left {gone}")
            out = locals().get("PROBED") or {}
            if not out:
                ova = someone(b, "ova", "Ova Ruhr")
                pex = someone(b, "pex", "Pex Iles")
                p11 = make_post(ova, "Section 11, Ova's")
                like(pex, ("p", p11))
                like(ova, ("p", p11))
                for i in range(6):
                    make_post(ova, f"Section 11, Ova's {i}")
                make_drawing(ova, "Section 11, Ova's drawing", seed=111)
                copy = os.path.join(TMP, "probe11.db")
                src = sqlite3.connect(DB, timeout=10)
                dst = sqlite3.connect(copy)
                src.backup(dst)
                src.close()
                dst.close()
                home_as = "; ".join(f"{c['name']}={c['value']}" for c in ova.ctx.cookies(BASE))
                probe = subprocess.run([sys.executable, "-c", PROBE, p11, "pex", home_as], cwd=ROOT, capture_output=True, text=True,
                                       timeout=180, env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
                try:
                    out = json.loads(probe.stdout.strip().splitlines()[-1])
                except Exception:  # noqa: BLE001
                    out = {"err": (probe.stderr or probe.stdout)[-600:]}
            plans = out.get("plans") or {}
            check("the reads, as the code sends them, are searches on their own indexes (SQLite's own plan): a page's"
                  " counts and who liked one by the thing, Activity's by whose and when (since you last looked, and"
                  " before)",
                  any("ix_social_likes_post_created (post_id=?)" in s for s in plans.get("stats", []))
                  and any("ix_social_likes_post_created (post_id=?)" in s for s in plans.get("who", []))
                  and any("ix_social_likes_owner_created (owner_id=? AND created_at>?)" in s for s in plans.get("activity", []))
                  and any("ix_social_likes_owner_created (owner_id=? AND created_at<?)" in s for s in plans.get("activity", []))
                  and not any(s.startswith("SCAN social_likes") for v in plans.values() for s in v),
                  json.dumps(plans or out.get("err"))[:600])
            check("Home's feed asks for its cards' likes once a kind: a page of posts and drawings, two grouped reads",
                  out.get("reads") == ["SELECT", "SELECT"] and (out.get("cards") or 0) >= 5 and out.get("kinds") == ["b", "p"],
                  json.dumps({k: out.get(k) for k in ("reads", "cards", "kinds", "err")})[:400])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "words and marks: every page with likes, phone and desk, light and dark"):
        try:
            una = someone(b, "una", "Una Bell")
            vid = someone(b, "vid", "Vid Cruz")
            wyn = someone(b, "wyn", "Wyn Dale")
            give_face(vid, 121)
            p12 = make_post(una, "Section 12, Una's")
            p12b = make_post(vid, "Section 12, Vid's")
            make_post(wyn, "Section 12, Wyn's, nobody's yet")
            like(vid, ("p", p12), at=4200)
            like(wyn, ("p", p12))
            like(una, ("p", p12))
            like(una, ("p", p12b))
            lows, smalls, fields, marks, read, tints = [], [], [], [], 0, []
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    got = []
                    ctx, pg = browser_as(b, una, screen=screen, scheme=scheme)
                    go(pg, "/social/")
                    pg.locator(card(p12b)).scroll_into_view_if_needed()
                    pg.wait_for_timeout(200)
                    got.append(("Home", pg.evaluate(READ)))
                    marks += [(tag, "Home", m) for m in pg.evaluate(MARKS)]
                    go(pg, f"/social/p/{p12}#liked", wait=200)
                    tints.append((tag, pg.evaluate(LK_TINT)))
                    pg.wait_for_timeout(3000)
                    got.append(("a post's page", pg.evaluate(READ)))
                    marks += [(tag, "post", m) for m in pg.evaluate(MARKS)]
                    pg.locator("[data-like-by]").click()
                    pg.wait_for_timeout(700)
                    got.append(("the sheet of who", pg.evaluate(READ, "#likeSheet")))
                    marks += [(tag, "sheet", m) for m in pg.evaluate(MARKS) if m["what"] == "sheet dot"]
                    go(pg, "/social/activity")
                    got.append(("Activity", pg.evaluate(READ)))
                    marks += [(tag, "Activity", m) for m in pg.evaluate(MARKS)]
                    close_ctx(ctx, pg)
                    ctx, pg = browser_as(b, None, screen=screen, scheme=scheme)
                    go(pg, f"/social/p/{p12}")
                    pg.locator(".post-page > .post-meta .lk-heart").click()
                    pg.wait_for_timeout(700)
                    got.append(("the signed-out sheet", pg.evaluate(READ, "#likeOutSheet")))
                    marks += [(tag, "signed out", m) for m in pg.evaluate(MARKS)]
                    close_ctx(ctx, pg)
                    for where, r in got:
                        read += r["read"]
                        lows += [f"{tag} {where}: {x}" for x in r["low"]]
                        smalls += [f"{tag} {where}: {x}" for x in r["small"]]
                        fields += [f"{tag} {where}: {x}" for x in r["fields"]]
                    check(f"every word at 4.5:1 or more on what is painted behind it, {tag}: Home, a post's page with"
                          " 'Liked by…' (landed), its sheet, Activity with likes, the signed-out sheet",
                          all(r["read"] > 0 for _, r in got) and not any(r["low"] for _, r in got),
                          f"read {[(w, r['read'], r['lowest']) for w, r in got]}; low {[x for _, r in got for x in r['low']][:3]}")
            check("every target 44px or more and no text field under 16px, on all of them",
                  not smalls and not fields, f"small {smalls[:4]}; fields {fields[:3]}")
            kinds = {m["what"] for _, _, m in marks}
            weak = [(t, w, m) for t, w, m in marks if m["k"] < 3]
            check("the heart's marks at 3:1 or more on their ground, light and dark: empty and liked, on a card and a"
                  " page; Activity's small heart; the sheet's dot",
                  {"card empty", "card liked", "page empty", "page liked", "badge liked", "sheet dot"} <= kinds and not weak,
                  f"kinds {sorted(kinds)}; under 3:1 {weak[:3]}; lowest {min((m['k'] for _, _, m in marks), default=None)}")
            check("a landed 'Liked by…' reads 4.5:1 or more on the note's tint, its names and its words, light and dark",
                  len(tints) == 4 and all(t and t["words"] >= 4.5 and t["name"] and t["name"] >= 4.5 for _, t in tints),
                  json.dumps(tints))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)

    # ------------------------------------------------------------------ 13
    if part(13, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(13, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
