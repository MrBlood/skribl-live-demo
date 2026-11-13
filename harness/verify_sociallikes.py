"""Likes on the Skribl site (phase 2, likes; docs/SOCIAL-SITE.md "Built:
likes"), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. THE HEART AND THE COUNT, WHERE THEY ARE (the owner's way 3): a pill at
     the start of the line under the drawing, on Home's cards and on a post's
     page and a drawing's, the player's lead: in the loop button's dress (32px,
     its lilac and ink), a 44px tap area clear of the speed chip's, the
     scrubber giving it room and nothing else moving (the foot and the
     time-and-plays line as they were); the pen's heart, empty until liked,
     named "Like"; no number at zero; the count everyone's, "1 like", "2
     likes".
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
     in and the pill grows to it, the scrubber giving up its room over many
     frames, one that goes fades first; under Reduce Motion nothing glides.
     Read on every animation frame.
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
     and desk, light and dark; the heart's line on the pill's lilac, empty and
     liked, the small heart and the sheet's dot at 3:1, the pill's count at
     4.5:1; a landed "Liked by…" on the tint; and the heart on the line as
     built on every one of them (the census leaves Skribl's line, the heart's
     place now, to Skribl's own suites, so it is read here as section 1 reads
     it).
 13. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last, after
     14 and 15).
 14. THE DOTS ON THE LINE (part 2, the owner's D, "All yes, b"): one 5px dot
     a like at its moment, where the drawing's line puts it (where its
     playhead is at that moment), on a post's page and Home's card, a phone
     and a desk; likes together one dot a step redder, two then three or
     more; (b)'s colours, each 3:1 on what is painted behind it, read off the
     screen, light and dark; no dot for a like with no moment or by anybody
     hidden from the viewer; the page sends moments and how many, never who;
     nothing taken down has dots; your own dot follows your heart, fading in
     and out; a dot takes no tap (the scrubber under it does); nothing else
     moves for them.
 15. THE HEARTS THAT RISE: as the replay reaches a dot a heart rises from it,
     read on every frame (fades in, about 30px over many frames, never grows,
     gone in a second; the dot stays), the deeper blush in both themes at
     3:1 on the drawing's paper and the page; one from a redder dot; under
     Reduce Motion a glow and 0px moved; no heart on a scrub; calm at 16x on
     a busy drawing (three in the air at most, a third of a second apart,
     never late); nothing else on the card moves; a heart takes no tap.

SOCIALLIKES_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Likes at /social".
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


PAGE_HEART = ".post-page > .post-art .lk-heart"


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

# A card's foot: what is shown in it, in order.
FOOT = r"""(sel) => { const f = document.querySelector(sel + ' .post-foot'); if (!f) return null;
  return [...f.children].filter(e => e.getClientRects().length).map(e =>
    e.classList.contains('lk-heart') ? 'heart' : e.classList.contains('post-share') ? 'share'
    : e.classList.contains('post-count') ? 'count' : e.classList.contains('post-plays') ? 'plays' : e.tagName); }"""

# The line under a drawing (the player's), in `sel`: what its row holds, in
# order; the heart's box beside the loop button's, their dress, the room the
# scrubber gives; the heart's tap area (its ::after) and the speed chip's
# (its ::before), and whether a press lands on the heart at the edges of its
# own; and the line's height.
LINE = r"""(sel) => { const root = document.querySelector(sel); if (!root) return null;
  const line = root.querySelector('.skribl-inline-line'), row = line && line.querySelector('.skribl-inline-row');
  if (!row) return null;
  const heart = row.querySelector('.lk-heart'), scrub = row.querySelector('.skribl-inline-scrub'),
        loop = row.querySelector('.skribl-inline-loop'), speed = line.querySelector('.rl-speed');
  const kids = [...row.children].filter(e => e.getClientRects().length).map(e => e.classList.contains('skribl-inline-lead')
    ? (e.querySelector('.lk-heart') ? 'heart' : 'lead') : e.classList.contains('skribl-inline-scrub') ? 'scrub'
    : e.classList.contains('skribl-inline-controls') ? 'controls' : e.className);
  const box = e => { const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                                                                   w: r.width, h: r.height }; };
  const grown = (r, cs) => ({ left: r.left - -parseFloat(cs.left), right: r.right + -parseFloat(cs.right),
                              top: r.top - -parseFloat(cs.top), bottom: r.bottom + -parseFloat(cs.bottom) });
  const out = { kids, line: Math.round(line.getBoundingClientRect().height * 100) / 100, heart: null };
  if (!heart) return out;
  const h = box(heart), s = box(scrub), l = loop ? box(loop) : null, hc = getComputedStyle(heart), lc = loop ? getComputedStyle(loop) : null;
  const tap = grown(h, getComputedStyle(heart, '::after'));
  const hits = (x, y) => { const e = document.elementFromPoint(x, y); return !!e && (e === heart || heart.contains(e)); };
  const cx = (h.left + h.right) / 2;
  let sp = null;
  if (speed && speed.getClientRects().length) { const st = grown(box(speed), getComputedStyle(speed, '::before'));
    sp = { tap: st, apart: tap.right <= st.left || st.right <= tap.left || tap.bottom <= st.top || st.bottom <= tap.top }; }
  out.heart = { h: Math.round(h.h * 100) / 100, w: Math.round(h.w * 100) / 100, loopH: l && Math.round(l.h * 100) / 100,
    mid: Math.round((h.top + h.bottom) / 2 * 10) / 10, loopMid: l && Math.round((l.top + l.bottom) / 2 * 10) / 10,
    room: Math.round((s.left - h.right) * 100) / 100, startsLine: Math.abs(h.left - row.getBoundingClientRect().left) < 0.5,
    ground: hc.backgroundColor, loopGround: lc && lc.backgroundColor, ink: hc.color, loopInk: lc && lc.color,
    tapH: Math.round((tap.bottom - tap.top) * 100) / 100, tapW: Math.round((tap.right - tap.left) * 100) / 100,
    hitTop: hits(cx, tap.top + 1), hitBottom: hits(cx, tap.bottom - 0.5), hitMid: hits(cx, (h.top + h.bottom) / 2),
    speed: sp };
  return out; }"""

def placed(ln, foot=None):
    """The heart's place on a line (LINE's reading), as way 3 has it: first in
    the row, the loop button's height, middle, ground and ink, 10px from the
    scrubber, 44px to tap where a press lands, clear of the speed's; a card's
    foot, when given, as it was before likes (plays, comments, Share)."""
    h = (ln or {}).get("heart") or {}
    sp = h.get("speed")
    return (bool(ln) and ln["kids"] == ["heart", "scrub", "controls"] and h.get("startsLine")
            and h.get("h") == 32 and h.get("loopH") == 32 and abs(h.get("mid", 0) - h.get("loopMid", 99)) < 0.6
            and h.get("ground") == h.get("loopGround") and h.get("ink") == h.get("loopInk")
            and abs(h.get("room", 0) - 10) < 0.6 and h.get("tapH") == 44 and h.get("tapW", 0) >= 44
            and h.get("hitTop") and h.get("hitBottom") and h.get("hitMid") and sp is not None and sp["apart"]
            and (foot is None or foot == ["plays", "count", "share"]))


def told(ln):
    h = (ln or {}).get("heart") or {}
    return (f"row {ln and ln['kids']}; heart {h.get('w')}x{h.get('h')} (the loop's {h.get('loopH')}), middle"
            f" {h.get('mid')} / {h.get('loopMid')}; dress {h.get('ground')} {h.get('ink')} vs the loop's"
            f" {h.get('loopGround')} {h.get('loopInk')}; room {h.get('room')}; tap {h.get('tapW')}x{h.get('tapH')},"
            f" lands {h.get('hitTop')}/{h.get('hitMid')}/{h.get('hitBottom')}; apart from the speed's"
            f" {(h.get('speed') or {}).get('apart')}")


# A post's page: the time-and-plays line, its words, and whether a heart is in it.
META = r"""() => { const m = document.querySelector('.post-page > .post-meta');
  if (!m) return null; const r = m.getBoundingClientRect();
  return { top: r.top, bottom: r.bottom, h: Math.round(r.height * 100) / 100,
           lh: parseFloat(getComputedStyle(m).lineHeight), words: m.textContent.replace(/\s+/g, ' ').trim(),
           heart: !!m.querySelector('.lk-heart') }; }"""

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

# Every animation frame for `ms` from now: a heart's parts' paint, its icon's
# box, the pill's width and the scrubber's beside it on the line.
HSAMPLE = r"""([sel, ms]) => { window.__hf = []; const el = document.querySelector(sel); const t0 = performance.now();
  const scrub = el.closest('.skribl-inline-row') && el.closest('.skribl-inline-row').querySelector('.skribl-inline-scrub');
  const step = () => { const svg = el.querySelector('svg.ic-heart'), r = svg.getBoundingClientRect();
    const g = s => getComputedStyle(svg.querySelector(s)), n = el.querySelector('.lk-n');
    window.__hf.push({ t: Math.round(performance.now() - t0), off: parseFloat(g('.ht-ink').strokeDashoffset),
      dash: g('.ht-ink').strokeDasharray, ink: +g('.ht-ink').opacity, fill: +g('.ht-fill').opacity,
      line: +g('.ht-line').opacity, x: r.left, y: r.top, w: r.width, h: r.height,
      pw: el.getBoundingClientRect().width, sw: scrub ? scrub.getBoundingClientRect().width : null,
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
# page (the tint is its ::before, which the census cannot see).
LK_TINT = r"""() => { const a = document.getElementById('liked'); if (!a || !a.classList.contains('is-landed')) return null;
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (x, y) => { const p = lum(x), q = lum(y); return Math.round((Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05) * 100) / 100; };
  const tint = rgba(getComputedStyle(a, '::before').backgroundColor), page = rgba(getComputedStyle(document.body).backgroundColor);
  const g = over(tint, page), k = e => e ? ratio(over(rgba(getComputedStyle(e).color), g), g) : null;
  return { tint: getComputedStyle(a, '::before').backgroundColor, words: k(a.querySelector('.lk-by-words')),
           name: k(a.querySelector('.lk-by-words b')) }; }"""

# A mark's line against what is painted behind its box: the hearts (empty,
# liked; on a card or a page), Activity's small heart, the sheet's dot. The
# heart's pill is the player's lilac, a color-mix() Chrome reports as
# color(srgb r g b / a) in 0 to 1: read as such (the likes mock's own reader
# took those for 0 to 255 numbers and read the lilac as grey), and a colour
# in any other form it cannot read is a red mark that says so, never a guess.
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
  const put = (what, word, fg, g) => { out.push(unread || !fg ? { what, word, k: 0, unread: unread || 'no colour' }
                                                               : { what, word, k: ratio(over(fg, g), g) }); unread = null; };
  document.querySelectorAll('.lk-heart, .act-badge').forEach(h => { if (!h.getClientRects().length) return;
    const svg = h.querySelector('svg.ic-heart'); if (!svg) return;
    const liked = h.classList.contains('is-liked') || h.classList.contains('act-badge');
    const p = svg.querySelector(liked ? '.ht-ink' : '.ht-line'), cs = getComputedStyle(p);
    const where = h.classList.contains('act-badge') ? 'badge' : h.closest('.post-card') ? 'card' : 'page';
    let g = ground(h), c = read(cs.stroke); if (c) c[3] *= +cs.opacity;
    put(where + (liked ? ' liked' : ' empty'), false, c, g);
    const n = h.querySelector('.lk-n');
    if (n) { g = ground(h); put('count', true, read(getComputedStyle(n).color), g); } });
  document.querySelectorAll('#likeSheet:not([hidden]) .lk-mark').forEach(d => { const g = ground(d.parentElement);
    put('sheet dot', false, read(getComputedStyle(d).backgroundColor), g); });
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

# ---- the dots on the line and the hearts that rise (sections 14 and 15) -----------
# The page's own drawing is here (its player has the drawing).
PLAYER_LOADED = ("() => { const art = document.querySelector('.post-page > .post-art');"
                 " const p = art && window.SkriblInline && SkriblInline.mount(art)[0]; return !!p && p.state().loaded; }")

# The dots on the line in `sel` (Skribl's marks, the page's moments): each one's
# place on the scrubber (x, its middle from the scrubber's left), where it is on
# the screen, how far above the scrubber, its size, its count, its paint, any
# words, and whether a press there lands on the scrubber; left to right. With
# the scrubber's width, the replay's length the line was given, the moments the
# page sent, and where the playhead is drawn.
DOTS = r"""(sel) => { const root = document.querySelector(sel); if (!root) return null;
  const box = root.querySelector('.skribl-inline'), bar = root.querySelector('.skribl-inline-scrub');
  if (!box || !bar) return null;
  const br = bar.getBoundingClientRect(), head = bar.querySelector('.rl-head');
  let play = null; try { play = JSON.parse(box.getAttribute('data-skribl-line') || 'null').play; } catch (e) {}
  return { w: br.width, play, marks: box.getAttribute('data-skribl-marks'),
    head: head ? head.getBoundingClientRect().left + 1 - br.left : null,
    dots: [...root.querySelectorAll('.skribl-inline-marks i')].map(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2, at = document.elementFromPoint(cx, cy);
      return { x: Math.round((cx - br.left) * 100) / 100, cx, cy, above: Math.round((br.top - cy) * 100) / 100,
               w: r.width, h: r.height, n: e.dataset.n, bg: cs.backgroundColor, op: +cs.opacity,
               words: (e.textContent || '') + (e.getAttribute('title') || '') + (e.getAttribute('aria-label') || ''),
               bar: at === bar }; }).sort((p, q) => p.x - q.x) }; }"""

# For 700ms from now, every frame: the opacity of a dot that came (new) and of
# one on its way out (gone), on the line in `sel`.
DOT_OPS = r"""(sel) => { const root = document.querySelector(sel); window.__do = { new: [], gone: [] };
  const was = new Set(root.querySelectorAll('.skribl-inline-marks i')), t0 = performance.now();
  const step = () => { const now = [...root.querySelectorAll('.skribl-inline-marks i')];
    const added = now.filter(e => !was.has(e));
    if (added.length) window.__do.new.push(+getComputedStyle(added[0]).opacity);
    const going = [...was].filter(e => e.isConnected && +getComputedStyle(e).opacity < 0.999);
    if (going.length) window.__do.gone.push(+getComputedStyle(going[0]).opacity);
    if (performance.now() - t0 < 700) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# The drawing and its line in `sel`, part by part, as boxes from the drawing's top.
LINE_BOXES = r"""(sel) => { const root = document.querySelector(sel), t = root.querySelector('.skribl-inline').getBoundingClientRect().top;
  return ['.skribl-inline', '.skribl-inline-line', '.skribl-inline-lead', '.skribl-inline-scrub', '.skribl-inline-controls',
          '.skribl-inline-say'].map(s => { const e = root.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
    return [Math.round(r.left * 100) / 100, Math.round((r.top - t) * 100) / 100, Math.round(r.width * 100) / 100,
            Math.round(r.height * 100) / 100]; }); }"""

# For `ms` from now, every frame: each rising heart (or glow) in `sel`, as
# painted: which one, its middle, its size, its opacity, its ground colour,
# the time (T, the page's clock), and where the playhead is drawn then (head,
# the middle of the line's playhead mark, and the scrubber's width).
RISE = r"""([sel, ms]) => { window.__rf = []; const root = document.querySelector(sel), t0 = performance.now(); let n = 0;
  const step = () => { const T = performance.now(), hd = root.querySelector('.rl-head'), sc = root.querySelector('.skribl-inline-scrub');
    const head = hd ? hd.getBoundingClientRect().left + 1 : null, bw = sc ? sc.getBoundingClientRect().width : null;
    root.querySelectorAll('.lk-rise, .lk-glow').forEach(e => { if (!e.__k) e.__k = ++n;
      const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      window.__rf.push({ T, t: Math.round(T - t0), k: e.__k, c: e.className, x: r.left + r.width / 2, y: r.top + r.height / 2,
                         w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100, o: +cs.opacity,
                         bg: cs.backgroundColor, head, bw }); });
    if (T - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# A rising heart's paint now: its line and its inside, and a point of the
# drawing's paper beside it.
RISE_PAINT = r"""(sel) => { const h = document.querySelector(sel + ' .lk-rise'); if (!h) return null;
  const r = h.getBoundingClientRect();
  return { ink: getComputedStyle(h.querySelector('.ht-ink')).stroke, fill: getComputedStyle(h.querySelector('.ht-fill')).fill,
           paper: [r.right + 10, r.top + r.height / 2] }; }"""

# For `ms` from now, every frame: the boxes of a card's parts.
CARD_FRAMES = r"""([sel, ms]) => { window.__cf = []; const c = document.querySelector(sel), t0 = performance.now();
  const parts = { head: '.post-head', words: '.post-words', drawing: '.skribl-inline', heart: '.lk-heart',
                  scrubber: '.skribl-inline-scrub', line: '.skribl-inline-line', words2: '.skribl-inline-say', foot: '.post-foot' };
  const step = () => { const boxes = {};
    for (const [k, s] of Object.entries(parts)) { const e = c.querySelector(s); if (!e) continue;
      const r = e.getBoundingClientRect(); boxes[k] = [r.left, r.top, r.width, r.height]; }
    window.__cf.push({ t: performance.now() - t0, boxes });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# One like's dot, two together and three or more: (b), the owner's "All yes, b".
DOT_INK = {"light": ["rgb(230, 74, 120)", "rgb(227, 49, 87)", "rgb(209, 26, 50)"],
           "dark": ["rgb(255, 111, 145)", "rgb(255, 77, 120)", "rgb(255, 45, 95)"]}


def _lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def ratio_over(css, op, ground):
    """A colour (as Chrome writes it, rgb()) at opacity `op` over `ground` (a pixel), against that ground."""
    c = [float(v) for v in re.findall(r"[\d.]+", css or "")[:3]]
    if len(c) < 3 or not ground:
        return 0
    return round(contrast([c[i] * op + ground[i] * (1 - op) for i in range(3)], ground), 2)


def px(img, x, y):
    """The pixel at (x, y), or None where that point is off the picture."""
    x, y = int(x), int(y)
    return img.getpixel((x, y)) if img is not None and 0 <= x < img.width and 0 <= y < img.height else None


def dot_pixels(pg, sel):
    """Each dot on the line in `sel`, read off the screen (one CSS pixel a
    pixel): its middle pixel, the ground 5px above it (between the drawing and
    the line), and their contrast. The caller scrolls the line into view."""
    d = pg.evaluate(DOTS, sel)
    if not d or not d["dots"]:
        return []
    shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    out = []
    for dot in d["dots"]:
        x, y = int(dot["cx"]), int(dot["cy"])
        if 0 <= x < shot.width and 5 <= y < shot.height:
            fg, bg = shot.getpixel((x, y)), shot.getpixel((x, y - 5))
            out.append({"n": dot["n"], "fg": fg, "bg": bg, "k": round(contrast(fg, bg), 2)})
    return out


def rise_of(fs, dot):
    """A heart rising from `dot`, read on every frame (RISE): it starts at the
    dot, fades in (never whole on its first frame, no frame more than half its
    strength at once), rises about 30px over many frames (none carries a
    quarter of the way), never grows past its 14px, and is gone in about a
    second."""
    one = [f for f in fs if fs and f["k"] == fs[0]["k"]]
    if not one or not dot:
        return {"ok": False, "seen": len(one), "dot": bool(dot)}
    pos = [dot["cy"]] + [f["y"] for f in one]
    rise = max(dot["cy"] - f["y"] for f in one)
    steps = [abs(q - p) for p, q in zip(pos, pos[1:])]
    ops = [0.0] + [f["o"] for f in one]
    out = {"frames": len(one), "rise": round(rise, 2), "moving": len([s for s in steps if s > 0.05]),
           "step": round(max(steps), 2), "first": round(one[0]["o"], 3),
           "o_step": round(max(abs(q - p) for p, q in zip(ops, ops[1:])), 3),
           "grow": round(max(max(f["w"], f["h"]) for f in one) - 14, 2), "life": round(one[-1]["T"] - one[0]["T"]),
           "from": [round(one[0]["x"] - dot["cx"], 2), round(one[0]["y"] - dot["cy"], 2)]}
    out["ok"] = (26 <= rise <= 34 and out["moving"] >= 20 and out["step"] <= 0.25 * rise and out["first"] < 0.5
                 and out["o_step"] < 0.5 and out["grow"] <= 0.5 and 850 <= out["life"] <= 1150
                 and abs(out["from"][0]) < 0.6 and -3 < out["from"][1] <= 0.6)
    return out


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
    out["marked"] = html.count("data-skribl-marks=")
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
            p1d = make_post(ann, "Section 1, Ann's, taken down")
            d1 = make_drawing(ann, "Section 1, Ann's drawing", seed=11)
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (p1d,))


            ctx, pg = browser_as(b, ann)
            go(pg, "/social/")
            pg.locator(card(p1) + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            with_h = pg.evaluate(LINE, card(p1))
            pg.locator(card(p1d) + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            without = pg.evaluate(LINE, card(p1d))
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, bea)
            go(pg, "/social/")
            pg.locator(card(p1) + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            ln = pg.evaluate(LINE, card(p1))
            foot = pg.evaluate(FOOT, card(p1))
            h = pg.evaluate(HEART, card(p1) + " .lk-heart")
            check("on Home's card the heart is a pill at the start of the line under the drawing, before the scrubber:"
                  " the loop button's dress at the line's other end (32px, its lilac and its ink, on its middle), the"
                  " scrubber giving it room (10px from it), a 44px tap area that lands and stays clear of the speed"
                  " chip's; the card's foot as it was (plays, comments, Share)",
                  placed(ln, foot), told(ln) + f"; foot {foot}")
            check("with nothing liked it stays empty and says so: not pressed, named 'Like', no number at zero; the"
                  " pen's heart (one line drawn round), its blush and ink hidden, its line the line's own ink",
                  h and h["pressed"] == "false" and h["label"] == "Like" and h["n"] is None and not h["digits"]
                  and h["pen"] and h["fill"] == 0 and h["ink"] == 0 and h["line"] == 1
                  and h["lineColor"] == ((ln or {}).get("heart") or {}).get("loopInk") and not h["liked"],
                  json.dumps({k: h.get(k) for k in ("pressed", "label", "n", "pen", "fill", "ink", "line", "lineColor")} if h else None))
            check("nothing else moves: a line with the heart is the height of one without (its maker's taken-down card,"
                  " which has none), and nothing but the scrubber gives it room",
                  with_h and without and with_h["line"] == without["line"] and without["kids"] == ["scrub", "controls"]
                  and with_h["kids"] == ["heart", "scrub", "controls"],
                  f"with {with_h and (with_h['kids'], with_h['line'])}; without {without and (without['kids'], without['line'])}")
            go(pg, f"/social/p/{p1}")
            pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            m = pg.evaluate(META)
            lp = pg.evaluate(LINE, ".post-page > .post-art")
            hp = pg.evaluate(HEART, PAGE_HEART)
            check("on a post's page the same pill at the start of its drawing's line, in the same dress and the same"
                  " room; the time-and-plays line as it was, one line, no heart in it",
                  placed(lp) and m and not m["heart"] and abs(m["h"] - m["lh"]) < 0.6 and hp
                  and hp["pressed"] == "false" and hp["label"] == "Like" and hp["n"] is None,
                  told(lp) + f"; meta {m and (m['h'], m['lh'], m['heart'])}")
            go(pg, f"/social/b/{d1}")
            pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            ld = pg.evaluate(LINE, ".post-page > .post-art")
            hd = pg.evaluate(HEART, PAGE_HEART)
            check("on a drawing's own page (/social/b/<id>) the same pill in the same place, to its own like",
                  placed(ld) and hd and hd["like"] == f"/social/b/{d1}/like" and hd["label"] == "Like",
                  told(ld) + f"; like {hd and hd['like']}")
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
            sel = PAGE_HEART
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
            # A post whose drawing is in the gallery too: still its post's, and liked there.
            p3g = make_post(eli, "Section 3, Eli's, in the gallery", payload=dict(drawing(seed=32), visibility="public"))
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
            g3 = skribl_of(p3g)
            vis = db("select visibility from skribl_posts where public_id = ?", (g3 or "",))
            s9, _ = like(fay, ("s", g3))
            check("a drawing kept unlisted, and a post's own drawing asked as a drawing (in the gallery, too), take no"
                  " likes (404)",
                  s8 == 404 and s9 == 404 and vis == [("public",)] and likes_on(("s", d3u)) == [] and likes_on(("s", g3)) == [],
                  f"{s8} {s9} (its drawing {vis})")
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
            sel = PAGE_HEART
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
                h2 = pg.evaluate(HEART, PAGE_HEART)
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
            sel = PAGE_HEART
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
    if part(6, "kind, never jumpy: the heart draws and fills, fades back; the count fades, the pill grows round the heart"):
        try:
            rae = someone(b, "rae", "Rae Oaks")
            sam = someone(b, "sam", "Sam Pike")
            tam = someone(b, "tam", "Tam Gray")
            p6 = make_post(rae, "Section 6, Rae's")
            p6z = make_post(rae, "Section 6, Rae's, nobody's yet")
            p6r = make_post(rae, "Section 6, Rae's, for Reduce Motion")
            like(tam, ("p", p6))
            like(tam, ("p", p6r))
            sel = PAGE_HEART

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
            g = glide_of([f["sw"] for f in fs])
            ns = [f["n"] for f in fs if f["n"] is not None]
            fs2 = frames(pg)
            g2 = glide_of([f["sw"] for f in fs2])
            ns2 = [f["n"] for f in fs2 if f["n"] is not None]
            first_move = next((i for i, f in enumerate(fs2) if abs(f["sw"] - fs2[0]["sw"]) > 0.3), None)
            first_fade = next((i for i, f in enumerate(fs2) if f["n"] is not None and f["n"] < 0.97), None)
            check("a count that comes fades in, and the pill grows to hold it, the scrubber giving up its room over many"
                  " frames (none carries half the way), the heart itself never moving; one that goes fades first, then"
                  " the pill gives the room back the same way",
                  faded(ns) >= 2 and g["way"] >= 6 and g["frames"] >= 4 and g["step"] <= 0.5 * g["way"]
                  and faded(ns2) >= 2 and g2["way"] >= 6 and g2["frames"] >= 4 and g2["step"] <= 0.5 * g2["way"]
                  and first_fade is not None and first_move is not None and first_fade < first_move
                  and spread(fs + fs2, "x") < 0.5,
                  f"comes: fading {faded(ns)}, the scrubber {g}; goes: fading {faded(ns2)}, the scrubber {g2},"
                  f" fade from frame {first_fade}, room from {first_move}; the heart moved {spread(fs + fs2, 'x')}")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, tam, reduced=True)
            go(pg, f"/social/p/{p6z}")
            fs = frames(pg)
            ns = [f["n"] for f in fs if f["n"] is not None]
            gr = glide_of([f["sw"] for f in fs])
            close_ctx(ctx, pg)
            check("under Reduce Motion a count that comes fades in, and nothing glides: the pill takes its width at once",
                  faded(ns) >= 2 and gr["way"] >= 6 and gr["frames"] == 1,
                  f"fading {faded(ns)}; the scrubber {gr}")
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
            sel = PAGE_HEART
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
            sel = PAGE_HEART
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
            # Since follows (the follow mock, Nov 13) the same lines say follows too.
            check("Activity's words say likes: 'Who followed you, liked your posts or said something on them, and who"
                  " answered you.', and with nothing yet 'When someone follows you, likes your post, says something on"
                  " it, or answers you, you’ll see it here.'",
                  sub == "Who followed you, liked your posts or said something on them, and who answered you."
                  and empty == "When someone follows you, likes your post, says something on it, or answers you, you’ll see it here.",
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
            like(sly, ("p", p10e), at=600)
            like(tex, ("p", p10e))
            like(tex, ("p", p10f), at=900)  # theirs, on what somebody else made
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
                like(pex, ("p", p11), at=600)
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
            check("Home's feed asks for its cards' likes once a kind, their moments for the dots with them: a page of"
                  " posts and drawings, two grouped reads, cards with dots among them",
                  out.get("reads") == ["SELECT", "SELECT"] and (out.get("cards") or 0) >= 5 and out.get("kinds") == ["b", "p"]
                  and (out.get("marked") or 0) >= 1,
                  json.dumps({k: out.get(k) for k in ("reads", "cards", "kinds", "marked", "err")})[:400])
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
            lows, smalls, fields, marks, read, tints, sits = [], [], [], [], 0, [], []
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
                    # The heart sits as built on this screen too (the census
                    # above leaves Skribl's line to Skribl's suites): read
                    # after it, so its scroll moves nothing it reads.
                    pg.locator(card(p12b) + " .skribl-inline-line").scroll_into_view_if_needed()
                    pg.wait_for_timeout(200)
                    sits.append((tag, "Home's card", pg.evaluate(LINE, card(p12b)), pg.evaluate(FOOT, card(p12b))))
                    go(pg, f"/social/p/{p12}#liked", wait=200)
                    tints.append((tag, pg.evaluate(LK_TINT)))
                    pg.wait_for_timeout(3000)
                    got.append(("a post's page", pg.evaluate(READ)))
                    marks += [(tag, "post", m) for m in pg.evaluate(MARKS)]
                    pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
                    pg.wait_for_timeout(200)
                    sits.append((tag, "a post's page", pg.evaluate(LINE, ".post-page > .post-art"), None))
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
                    pg.locator(PAGE_HEART).click()
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
            off = [f"{t} {w}: {told(ln)}; foot {ft}" for t, w, ln, ft in sits if not placed(ln, ft)]
            check("the heart sits as built on every screen, light and dark, on Home's card and a post's page: first in"
                  " the drawing's line, the loop button's dress, 44px to tap where a press lands, clear of the speed's;"
                  " the card's foot as it was",
                  len(sits) == 8 and not off, f"{len(sits)} read; off {off[:2]}")
            kinds = {m["what"] for _, _, m in marks}
            weak = [(t, w, m) for t, w, m in marks if m["k"] < (4.5 if m.get("word") else 3)]
            lines = [m["k"] for _, _, m in marks if not m.get("word")]
            counts = [m["k"] for _, _, m in marks if m.get("word")]
            check("the heart's marks at 3:1 or more on their ground, light and dark: its line on the pill's lilac, empty"
                  " and liked, on a card and a page; Activity's small heart; the sheet's dot; and the pill's count, a"
                  " word, at 4.5:1",
                  {"card empty", "card liked", "page empty", "page liked", "badge liked", "sheet dot", "count"} <= kinds
                  and not weak,
                  f"kinds {sorted(kinds)}; under {weak[:3]}; lowest mark {min(lines, default=None)}, lowest count"
                  f" {min(counts, default=None)}")
            check("a landed 'Liked by…' reads 4.5:1 or more on the note's tint, its names and its words, light and dark",
                  len(tints) == 4 and all(t and t["words"] >= 4.5 and t["name"] and t["name"] >= 4.5 for _, t in tints),
                  json.dumps(tints))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)

    # ------------------------------------------------------------------ 14
    if part(14, "the dots on the line: a like's moment, where the line puts it; doubles redder; nobody hidden; Home's card"):
        try:
            mae = someone(b, "mae", "Mae Orr")
            sky = someone(b, "sky", "Sky Lund")
            ted = someone(b, "ted", "Ted Rowe")
            by = {h: someone(b, h, n) for h, n in (("fen", "Fen Ash"), ("gil", "Gil Hart"), ("hux", "Hux Bell"),
                                                   ("ike", "Ike Dorn"), ("jem", "Jem Ford"), ("kai", "Kai Lowe"),
                                                   ("lux", "Lux Penn"), ("ned", "Ned Quay"), ("oda", "Oda Reis"),
                                                   ("pia", "Pia Sand"), ("rio", "Rio Tate"))}
            # Sixteen seconds of drawing, and its moments: one alone at 0:05 and
            # 0:09, two together at 0:12, three at 0:14; Ned's with none; and
            # three by people Sky is not shown: Oda (Sky blocked), Pia (blocked
            # Sky) and Rio (taken down).
            p14 = make_post(mae, "Section 14, Mae's", payload=drawing(n=400, step=40))
            p14d = make_post(mae, "Section 14, Mae's, taken down", payload=drawing(n=400, step=40, seed=3))
            # The same drawing, liked as often by the same people, with no
            # moments: a line that never had a dot, to measure against.
            p14n = make_post(mae, "Section 14, Mae's, no moments", payload=drawing(n=400, step=40))
            moments = {"fen": 5000, "gil": 9000, "hux": 12000, "ike": 12000, "jem": 14000, "kai": 14000,
                       "lux": 14000, "ned": None, "oda": 3000, "pia": 7000, "rio": 10500}
            for h, at in moments.items():
                like(by[h], ("p", p14), at=at)
                like(by[h], ("p", p14d), at=at)
                like(by[h], ("p", p14n))
            block(sky, "oda")
            block(by["pia"], "sky")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'rio'")
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (p14d,))
            SKY_SEES = [(5000, "1"), (9000, "1"), (12000, "2"), (14000, "3")]
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    tag = f"{screen}/{scheme}"
                    ctx, pg = browser_as(b, sky, screen=screen, scheme=scheme)
                    go(pg, f"/social/p/{p14}", wait=0)
                    pg.wait_for_function(PLAYER_LOADED, timeout=15000)
                    pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
                    pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
                    pg.wait_for_timeout(400)
                    page_ = pg.evaluate(DOTS, ".post-page > .post-art")
                    heads = []
                    for at, _ in SKY_SEES:
                        pg.evaluate("(ms) => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].seek(ms)", at)
                        pg.wait_for_timeout(60)
                        heads.append(pg.evaluate(DOTS, ".post-page > .post-art")["head"])
                    page_px = dot_pixels(pg, ".post-page > .post-art")
                    go(pg, "/social/")
                    pg.locator(card(p14) + " .skribl-inline-line").scroll_into_view_if_needed()
                    pg.wait_for_timeout(400)
                    card_ = pg.evaluate(DOTS, card(p14))
                    card_px = dot_pixels(pg, card(p14))
                    close_ctx(ctx, pg)
                    seen[tag] = {"page": page_, "heads": heads, "page_px": page_px, "card": card_, "card_px": card_px}
            ph = seen["phone/light"]
            want = [round(at / ph["page"]["play"] * ph["page"]["w"], 2) for at, _ in SKY_SEES]
            check("on a post's page, one small dot a like at its moment, 5px, over the drawing's line, where the line"
                  " puts that moment (where its playhead is at it), in the middle of the 17px above the scrubber:"
                  " a phone and a desk alike",
                  all(len(s["page"]["dots"]) == 4 and all(d["w"] == 5 and d["h"] == 5 and abs(d["above"] - 8.5) < 0.6
                                                          for d in s["page"]["dots"])
                      and all(h is not None and abs(d["x"] - h) < 0.6 for d, h in zip(s["page"]["dots"], s["heads"]))
                      for s in seen.values())
                  and all(abs(d["x"] - x) < 0.6 for d, x in zip(ph["page"]["dots"], want)),
                  json.dumps({t: [[d["x"] for d in s["page"]["dots"]], s["heads"]] for t, s in seen.items()})[:700])
            check("likes that land together are one dot, the same size, a step redder: two, then three or more; never"
                  " bigger and never a number",
                  all([d["n"] for d in s[k]["dots"]] == [n for _, n in SKY_SEES] and not any(d["words"] for d in s[k]["dots"])
                      for s in seen.values() for k in ("page", "card")),
                  json.dumps({t: [d["n"] for d in s["page"]["dots"]] for t, s in seen.items()}))
            weak = [(t, k, p) for t, s in seen.items() for k in ("page_px", "card_px") for p in s[k] if p["k"] < 3]
            inks = {t: [d["bg"] for d in s["page"]["dots"]] + [d["bg"] for d in s["card"]["dots"]] for t, s in seen.items()}
            check("the colours, (b): on light #e64a78, #e33157 and #d11a32, on dark #ff6f91, #ff4d78 and #ff2d5f, one,"
                  " two and three or more; each 3:1 or more against what is painted behind it, read off the screen's"
                  " pixels, on a post's page and Home's card, a phone and a desk",
                  all(inks[t] == [DOT_INK[t.split("/")[1]][i] for i in (0, 0, 1, 2)] * 2 for t in seen)
                  and all(len(s["page_px"]) == 4 and len(s["card_px"]) == 4 for s in seen.values()) and not weak,
                  json.dumps({"read": {t: {k[:4]: {n: min(p["k"] for p in s[k] if p["n"] == n) for n in "123"
                                                   if any(p["n"] == n for p in s[k])} for k in ("page_px", "card_px")}
                                       for t, s in seen.items()},
                              "inks": {t: sorted(set(v)) for t, v in inks.items()}, "under": weak[:3]}))
            cw = seen["phone/light"]["card"]
            check("Home's card shows the same dots on its line, where its own line puts each moment",
                  [d["n"] for d in cw["dots"]] == [n for _, n in SKY_SEES]
                  and all(abs(d["x"] - at / cw["play"] * cw["w"]) < 0.6 for d, (at, _) in zip(cw["dots"], SKY_SEES))
                  and json.loads(cw["marks"] or "[]") == json.loads(ph["page"]["marks"] or "[]"),
                  json.dumps({"card": [d["x"] for d in cw["dots"]], "w": cw["w"], "marks": cw["marks"]}))
            sent = json.loads(ph["page"]["marks"] or "[]")
            ctx, pg = browser_as(b, ted)
            go(pg, f"/social/p/{p14}")
            ted_sees = pg.evaluate(DOTS, ".post-page > .post-art")
            ted_n = pg.evaluate(HEART, PAGE_HEART)
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, sky)
            go(pg, f"/social/p/{p14}")
            sky_n = pg.evaluate(HEART, PAGE_HEART)
            close_ctx(ctx, pg)
            check("a like with no moment has no dot, and nobody hidden from the viewer has one, as they have no count:"
                  " not Ned's (no moment), Oda's (Sky blocked her), Pia's (she blocked Sky) or Rio's (taken down);"
                  " somebody else is shown Oda's and Pia's, never Rio's",
                  sent == [{"ms": 5000, "n": 1}, {"ms": 9000, "n": 1}, {"ms": 12000, "n": 2}, {"ms": 14000, "n": 3}]
                  and sky_n and sky_n["n"] == "8"
                  and [d["x"] for d in ted_sees["dots"]] and len(ted_sees["dots"]) == 6
                  and json.loads(ted_sees["marks"]) == [{"ms": 3000, "n": 1}, {"ms": 5000, "n": 1}, {"ms": 7000, "n": 1},
                                                        {"ms": 9000, "n": 1}, {"ms": 12000, "n": 2}, {"ms": 14000, "n": 3}]
                  and ted_n and ted_n["n"] == "10",
                  json.dumps({"sky": sent, "sky_count": sky_n and sky_n["n"], "ted": ted_sees["marks"],
                              "ted_count": ted_n and ted_n["n"]}))
            check("dots say where, never who: the page sends each moment and how many and nothing more, and no dot"
                  " carries a word",
                  all(set(m) == {"ms", "n"} for m in sent) and not any(d["words"] for d in ph["page"]["dots"])
                  and not any(h in (ph["page"]["marks"] or "") for h in ("fen", "gil", "hux", "Fen", "Gil")),
                  ph["page"]["marks"])
            ctx, pg = browser_as(b, mae)
            go(pg, "/social/")
            down_card = pg.evaluate(DOTS, card(p14d))
            go(pg, f"/social/p/{p14d}")
            down_page = pg.evaluate(DOTS, ".post-page > .post-art")
            close_ctx(ctx, pg)
            check("nothing taken down has dots: its maker's own card and page send no moments and show none",
                  down_card and down_page and not down_card["marks"] and not down_page["marks"]
                  and down_card["dots"] == [] and down_page["dots"] == [],
                  json.dumps({"card": down_card and down_card["marks"], "page": down_page and down_page["marks"]}))
            # YOUR OWN DOT: Ugo likes it while it plays (a dot where he tapped,
            # fading in), takes it back (fading out), and likes it while it is
            # still (no dot).
            ugo = someone(b, "ugo", "Ugo Vane")
            ctx, pg = browser_as(b, ugo)
            go(pg, f"/social/p/{p14}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.pause(); p.seek(6000); p.play(); }")
            pg.wait_for_timeout(300)
            pg.evaluate(DOT_OPS, ".post-page > .post-art")
            tap_heart(pg, PAGE_HEART, after=500)
            came = pg.evaluate("() => window.__do")
            kept = [k[1] for k in likes_on(("p", p14)) if k[0] == "ugo"]
            mine = pg.evaluate(DOTS, ".post-page > .post-art")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.evaluate(DOT_OPS, ".post-page > .post-art")
            tap_heart(pg, PAGE_HEART, after=500)
            went = pg.evaluate("() => window.__do")
            after = pg.evaluate(DOTS, ".post-page > .post-art")
            tap_heart(pg, PAGE_HEART, after=500)
            still = pg.evaluate(DOTS, ".post-page > .post-art")
            close_ctx(ctx, pg)
            mx = round(kept[0] / mine["play"] * mine["w"], 2) if kept and kept[0] is not None else None
            new = [d for d in mine["dots"] if mx is not None and abs(d["x"] - mx) < 0.6]
            check("your own like moves your dot with your heart: liked while it plays, a dot comes where you tapped,"
                  " fading in; taken back, it fades out and is gone; liked while it is still, no dot",
                  kept and kept[0] is not None and 6000 < kept[0] < 7500 and len(mine["dots"]) == 7 and len(new) == 1
                  and faded(came.get("new", [])) >= 2 and faded(went.get("gone", [])) >= 2
                  and len(after["dots"]) == 6 and len(still["dots"]) == 6,
                  json.dumps({"kept": kept, "dots": [d["x"] for d in mine["dots"]], "want": mx, "in": came.get("new", [])[:8],
                              "out": went.get("gone", [])[:8], "then": len(after["dots"]), "still": len(still["dots"])}))
            # A DOT TAKES NO TAP: a finger where one is painted lands on the
            # scrubber under it, which shows the drawing there.
            ctx, pg = browser_as(b, sky)
            go(pg, f"/social/p/{p14}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            dd = pg.evaluate(DOTS, ".post-page > .post-art")
            d2 = dd["dots"][1] if len(dd["dots"]) > 1 else None
            if d2:
                pg.touchscreen.tap(d2["cx"], d2["cy"])
                pg.wait_for_timeout(400)
            at2 = pg.evaluate(PLAYHEAD)
            # NOTHING ELSE MOVES: the line with its dots, the same drawing's
            # line that never had one (as many likes, none with a moment), and
            # the first line again once its dots are taken away.
            before_ = pg.evaluate(LINE_BOXES, ".post-page > .post-art")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].marks([])")
            pg.wait_for_timeout(400)
            without = pg.evaluate(LINE_BOXES, ".post-page > .post-art")
            gone = pg.evaluate(DOTS, ".post-page > .post-art")
            go(pg, f"/social/p/{p14n}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.locator(".post-page > .post-art .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            never = pg.evaluate(LINE_BOXES, ".post-page > .post-art")
            never_dots = pg.evaluate(DOTS, ".post-page > .post-art")
            never_n = pg.evaluate(HEART, PAGE_HEART)
            close_ctx(ctx, pg)
            check("a dot takes no tap: a finger where it is painted lands on the scrubber under it, which shows the"
                  " drawing at that moment",
                  d2 and all(d["bar"] for d in dd["dots"]) and at2 and not at2["playing"]
                  and abs(at2["ms"] - 9000) < 0.02 * dd["play"] + 60,
                  json.dumps({"dot": d2, "then": at2}))
            check("nothing else moves for the dots: the drawing, the line, the heart, the scrubber, mute and loop and the"
                  " words under them are where they are on the same drawing's line that never had a dot (as many"
                  " likes, none with a moment), and where they were once its dots are taken away",
                  gone["dots"] == [] and before_ == without and never_dots["dots"] == [] and not never_dots["marks"]
                  and never_n and never_n["n"] == "8" and before_ == never,
                  json.dumps({"with": before_, "never": never, "taken": without})[:700])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(14, exc)

    # ------------------------------------------------------------------ 15
    if part(15, "the hearts that rise: from each dot as the replay reaches it, kind; a glow under Reduce Motion; calm"):
        try:
            via = someone(b, "via", "Via Wolde")
            wim = someone(b, "wim", "Wim Xu")
            xan = someone(b, "xan", "Xan Young")
            yul = someone(b, "yul", "Yul Zane")
            zoe = someone(b, "zoe", "Zoe Abbott")
            p15 = make_post(via, "Section 15, Via's", payload=drawing(n=400, step=40))
            like(wim, ("p", p15), at=5000)
            like(xan, ("p", p15), at=9000)
            like(yul, ("p", p15), at=12000)
            like(zoe, ("p", p15), at=12000)
            like(via, ("p", p15), at=12000)
            sel = ".post-page > .post-art"
            glides, colours, stays = {}, {}, {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, wim, scheme=scheme)
                go(pg, f"/social/p/{p15}", wait=0)
                pg.wait_for_function(PLAYER_LOADED, timeout=15000)
                pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
                pg.locator(sel + " .skribl-inline-line").scroll_into_view_if_needed()
                pg.wait_for_timeout(300)
                dots = pg.evaluate(DOTS, sel)
                pg.evaluate(RISE, [sel, 1600])
                pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                            " p.seek(4600); p.setRate(1); p.play(); }")
                pg.wait_for_timeout(700)
                peak = pg.evaluate(RISE_PAINT, sel)
                shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB") if peak else None
                pg.wait_for_timeout(1100)
                fs = pg.evaluate("() => window.__rf")
                pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
                after = pg.evaluate(DOTS, sel)
                close_ctx(ctx, pg)
                d5 = dots["dots"][0] if dots["dots"] else None
                glides[scheme] = rise_of([f for f in fs if f["c"] == "lk-rise"], d5)
                stays[scheme] = bool(d5) and [(d["x"], d["n"], d["op"]) for d in after["dots"]] == [
                    (d["x"], d["n"], d["op"]) for d in dots["dots"]]
                paper = px(shot, peak["paper"][0], peak["paper"][1]) if peak else None
                ground = px(shot, d5["cx"] + 12, d5["cy"]) if d5 else None
                colours[scheme] = {"ink": peak and peak["ink"], "fill": peak and peak["fill"], "paper": paper,
                                   "page": ground, "on the paper": ratio_over(peak and peak["ink"], 1, paper),
                                   "on the page": ratio_over(peak and peak["ink"], 1, ground)}
            check("as the replay reaches a dot, a small heart rises from it: from the dot, fading in as it starts (never"
                  " whole on its first frame), about 30px up over many frames (no frame carries a quarter of the way),"
                  " never growing, gone in about a second; the dot stays, light and dark",
                  all(g["ok"] for g in glides.values()) and all(stays.values()), json.dumps({"glides": glides, "stays": stays}))
            check("the heart wears the deeper blush in both themes (its line #e64a78, his blush inside): at full strength"
                  " 3:1 or more on the drawing's paper it crosses and on the page where it starts, read off the screen",
                  all(c["ink"] == "rgb(230, 74, 120)" and c["fill"] == "rgb(255, 111, 145)" and c["on the paper"] >= 3
                      and c["on the page"] >= 3 for c in colours.values()), json.dumps(colours))
            # ONE HEART FROM A REDDER DOT; and under Reduce Motion, a glow.
            ctx, pg = browser_as(b, wim)
            go(pg, f"/social/p/{p15}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.locator(sel + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.evaluate(RISE, [sel, 1500])
            pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.seek(11700); p.play(); }")
            pg.wait_for_timeout(1700)
            fs = pg.evaluate("() => window.__rf")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            close_ctx(ctx, pg)
            check("a redder dot (three at 0:12) sends up one heart", len({f["k"] for f in fs if f["c"] == "lk-rise"}) == 1,
                  f"{len({f['k'] for f in fs if f['c'] == 'lk-rise'})} hearts")
            ctx, pg = browser_as(b, wim, reduced=True)
            go(pg, f"/social/p/{p15}")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].play()")
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.locator(sel + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            dots = pg.evaluate(DOTS, sel)
            pg.evaluate(RISE, [sel, 1600])
            pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.seek(4600); p.play(); }")
            pg.wait_for_timeout(1800)
            fs = pg.evaluate("() => window.__rf")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            close_ctx(ctx, pg)
            gl = [f for f in fs if f["c"] == "lk-glow"]
            d5 = dots["dots"][0] if dots["dots"] else {}
            ops = [f["o"] for f in gl]
            check("under Reduce Motion nothing rises: the dot glows a moment, a halo of its own colour round it fading in"
                  " and out where it sits, 0px moved, and no heart",
                  gl and not [f for f in fs if f["c"] == "lk-rise"] and spread(gl, "x") < 0.01 and spread(gl, "y") < 0.01
                  and abs(gl[0]["x"] - d5.get("cx", -9)) < 0.6 and abs(gl[0]["y"] - d5.get("cy", -9)) < 0.6
                  and faded(ops) >= 8 and 0.2 < max(ops) <= 0.4 and gl[0]["bg"] == d5.get("bg"),
                  json.dumps({"frames": len(gl), "moved": [spread(gl, "x"), spread(gl, "y")] if gl else None,
                              "most": max(ops) if ops else None, "bg": gl and gl[0]["bg"], "dot": d5.get("bg")}))
            # NO BURST ON A SCRUB: a drag across every dot and back while it
            # plays, then on from where it was let go.
            ctx, pg = browser_as(b, wim)
            go(pg, f"/social/p/{p15}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => { const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.seek(500); p.play(); }")
            pg.locator(sel + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(200)
            sb = pg.evaluate("(s) => { const r = document.querySelector(s + ' .skribl-inline-scrub').getBoundingClientRect();"
                             " return [r.left, r.top + r.height / 2, r.width]; }", sel)
            dots = pg.evaluate(DOTS, sel)
            pg.evaluate(RISE, [sel, 4200])
            t_drag = pg.evaluate("() => performance.now()")
            pg.mouse.move(sb[0] + 2, sb[1])
            pg.mouse.down()
            for k in range(36):
                f = k / 35 if k < 24 else 1 - (k - 23) / 12 * 0.55
                pg.mouse.move(sb[0] + 2 + (sb[2] - 4) * f, sb[1])
                pg.wait_for_timeout(16)
            pg.mouse.up()
            t_up = pg.evaluate("() => performance.now()")
            pg.wait_for_timeout(3300)
            fs = pg.evaluate("() => window.__rf")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            close_ctx(ctx, pg)
            starts = {}
            for f in fs:
                if f["c"] == "lk-rise" and f["k"] not in starts:
                    starts[f["k"]] = f
            during = [s for s in starts.values() if s["T"] <= t_up + 20]
            later = [s for s in starts.values() if s["T"] > t_up + 20]
            d9 = next((d for d in dots["dots"] if abs(d["x"] - 9000 / dots["play"] * dots["w"]) < 1), None)
            check("no burst on a scrub: a finger dragged across every dot and back while it plays sends up no heart;"
                  " let go, it plays on from there, and the next dot it reaches sends one",
                  not during and len(later) == 1 and d9 and abs(later[0]["x"] - d9["cx"]) < 1.5,
                  json.dumps({"during": len(during), "after": [round(s["x"], 1) for s in later], "next": d9 and d9["cx"]}))
            # CALM AT 16x: a busy drawing, forty likes over thirty seconds (the
            # likes kept straight into the site's rows, by people kept the same
            # way: what the line shows is under test, not the liking).
            pz = make_post(via, "Section 15, Via's busy one", payload=drawing(n=750, step=40, seed=7))
            pid = db("select id, person_id from social_posts where public_id = ?", (pz,))[0]
            for i in range(40):
                h = f"bz{i:02d}"
                db_write("insert into social_people (public_id, handle, handle_key, display_name, user_handle, is_admin,"
                         " session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, 0, 1, datetime('now'),"
                         " datetime('now'))", ("site:" + h, h, h, "Busy " + h, secrets.token_bytes(32)))
                at = 400 + i * 730 + (i % 5) * 37
                db_write("insert into social_likes (post_id, owner_id, person_id, at_ms, created_at) values (?, ?,"
                         " (select id from social_people where handle_key = ?), ?, datetime('now'))", (pid[0], pid[1], h, at))
            ctx, pg = browser_as(b, wim)
            go(pg, f"/social/p/{pz}", wait=0)
            pg.wait_for_function(PLAYER_LOADED, timeout=15000)
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            pg.locator(sel + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            busy = pg.evaluate(DOTS, sel)
            pg.evaluate(RISE, [sel, 3600])
            pg.evaluate("() => { window.__mk = []; document.addEventListener('skribl:mark', (e) => {"
                        " const r = e.target.getBoundingClientRect(); window.__mk.push([performance.now(), r.left + r.width / 2]); });"
                        " const p = SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0];"
                        " p.setLoop(true); p.seek(0); p.setRate(16); p.play(); }")
            pg.wait_for_timeout(3700)
            fs = pg.evaluate("() => window.__rf")
            mk = pg.evaluate("() => window.__mk")
            pg.evaluate("() => SkriblInline.mount(document.querySelector('.post-page > .post-art'))[0].pause()")
            close_ctx(ctx, pg)
            rs = {}
            for f in fs:
                if f["c"] == "lk-rise":
                    rs.setdefault(f["k"], []).append(f)
            born = sorted(v[0]["T"] for v in rs.values())
            gaps = [q - p for p, q in zip(born, born[1:])]
            air = max((len({f["k"] for f in fs if f["c"] == "lk-rise" and f["T"] == T}) for T in {f["T"] for f in fs}), default=0)
            # NEVER LATE, judged by the playhead itself: each heart starts at a
            # dot, and on its first frame the playhead is at that dot or just
            # past it (3px: at 16x it covers about one a frame here). Not by
            # the events: a host can send one again, late. (The busy piece's
            # last like is 3% before its end, so no heart is born as the
            # playhead comes round.)
            behind = [round(v[0]["head"] - v[0]["x"], 2) for v in rs.values() if v[0]["head"] is not None]
            at_dot = all(any(abs(v[0]["x"] - d["cx"]) < 1 for d in busy["dots"]) for v in rs.values())
            fresh = at_dot and len(behind) == len(rs) and all(0 <= d <= 3 for d in behind)
            check("calm at 16x: on a busy drawing (40 likes, %d dots) the playhead reaches dots by the dozen, and at"
                  " most three hearts are in the air, each a third of a second or more after the one before, each"
                  " rising from a dot just reached (never late)" % len(busy["dots"]),
                  len(busy["dots"]) >= 30 and len(mk) >= 40 and len(rs) >= 6 and air <= 3 and min(gaps or [0]) >= 320
                  and fresh,
                  json.dumps({"dots": len(busy["dots"]), "reached": len(mk), "hearts": len(rs), "most in the air": air,
                              "closest": round(min(gaps or [0])), "fresh": fresh, "behind the playhead": behind}))
            # NOTHING ELSE MOVES on Home's card while a heart rises from its line,
            # and a heart takes no tap: one on the drawing where it is pauses it.
            ctx, pg = browser_as(b, wim)
            go(pg, "/social/")
            c15 = card(p15)
            pg.locator(c15 + " .skribl-inline-line").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            pg.evaluate("(s) => { const p = SkriblInline.mount(document.querySelector(s))[0]; p.play(); }", c15)
            pg.wait_for_function("(s) => SkriblInline.mount(document.querySelector(s))[0].state().loaded", arg=c15,
                                 timeout=15000)
            pg.evaluate("(s) => { const p = SkriblInline.mount(document.querySelector(s))[0]; p.pause(); }", c15)
            pg.wait_for_timeout(200)
            pg.evaluate(CARD_FRAMES, [c15, 1300])
            pg.evaluate(RISE, [c15, 1300])
            pg.evaluate("(s) => { const p = SkriblInline.mount(document.querySelector(s))[0]; p.seek(4700); p.play(); }", c15)
            pg.wait_for_timeout(700)
            mid = pg.evaluate("(s) => { const h = document.querySelector(s + ' .lk-rise'); if (!h) return null;"
                              " const r = h.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2,"
                              " at = document.elementFromPoint(x, y);"
                              " return { x, y, heart: !!at && !!at.closest('.lk-rise'), box: !!at && !!at.closest('.skribl-inline') }; }", c15)
            pg.wait_for_timeout(700)
            cf = pg.evaluate("() => window.__cf")
            fs = pg.evaluate("() => window.__rf")
            # A finger on a heart while it rises (a third of a second into it):
            # the drawing under it takes the tap and pauses.
            pg.evaluate("(s) => { const p = SkriblInline.mount(document.querySelector(s))[0]; p.seek(4700); p.play(); }", c15)
            pg.wait_for_timeout(650)
            here = pg.evaluate("(s) => { const h = document.querySelector(s + ' .lk-rise'); if (!h) return null;"
                               " const r = h.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }", c15)
            if here:
                pg.touchscreen.tap(here[0], here[1])
                pg.wait_for_timeout(300)
            paused = pg.evaluate("(s) => SkriblInline.mount(document.querySelector(s))[0].playhead()", c15)
            nav = urllib.parse.urlparse(pg.url).path
            close_ctx(ctx, pg)
            parts = sorted(cf[0]["boxes"]) if cf else []
            moved = {k: max(abs(f["boxes"][k][i] - cf[0]["boxes"][k][i]) for f in cf for i in range(4)) for k in parts}
            check("nothing else on the card moves while a heart rises from its line: its head, words, drawing, heart,"
                  " scrubber, line and foot keep their boxes, frame by frame",
                  cf and len(cf) > 20 and {f["k"] for f in fs if f["c"] == "lk-rise"} and parts
                  and all(v < 0.01 for v in moved.values()),
                  json.dumps({"frames": len(cf or []), "hearts": len({f["k"] for f in fs if f["c"] == "lk-rise"}), "moved": moved}))
            check("a heart takes no tap: one on the drawing where a heart is rising lands on the drawing, which pauses",
                  mid and not mid["heart"] and mid["box"] and here and paused and not paused["playing"] and nav == "/social/",
                  json.dumps({"at": mid, "tapped": here, "then": paused, "page": nav}))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(15, exc)

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
