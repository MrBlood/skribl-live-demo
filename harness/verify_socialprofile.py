#!/usr/bin/env python3
"""Profiles with drawn faces at /social (docs/SOCIAL-SITE.md, phase 1, piece 3;
the owner's "all yes" on phase 1's mocks, Nov 10: "Faces that draw
themselves").

Through the demo's own app (app.py) on a server of its own, booted with what
the site's people need (CSRF on, so Skribl is told who is signed in; a
first-invite code; one trusted proxy, so each browser speaks from an address
of its own and no section spends another's limits), driven at
http://localhost:<port> (a passkey cannot belong to an IP address), with
Chromium's virtual authenticator. Faces are drawn through the real Pad, in
the profile's own overlay, with pen input (harness/tools/artdraw.py: CDP pen
events with pressure, a hand's timing).

   1. A PROFILE: name, @handle and bio (its line breaks kept); Skribl's own
      Gallery section with that person's public skribls only, newest first,
      to visitors and to the person alike, Load more paging within them;
      any case of the handle; a kind 404 for nobody; You leads to your own
      profile, and somebody else's marks no place in the bar; the gear leads
      to Settings; an empty profile in its own words (to its own person, what
      puts a skribl there; to anybody else, that there are none yet).
   2. DRAW YOUR FACE through the real Pad in its face mode (compose=1&face=1:
      square, a face's words, no Flip switch), in an overlay that glides up
      (read on every frame) and fades where it sits under Reduce Motion; the
      Pad's own x closes it; Use this face keeps one UNLISTED skribl, theirs,
      as their face, listed nowhere; the bar's You wears it.
   3. IT DRAWS ITSELF ONCE on the profile, read from the paint: from the
      empty circle, ink over time, at about 4x, then it rests, finished,
      fetched once and never looped; under Reduce Motion it is finished at
      once and nothing is fetched.
   4. ELSEWHERE, STILL: the bar's You, the Gallery's tile (the site's
      Gallery of everyone) and a Gallery card of Skribl's own (its /gallery)
      wear the face as a picture (no player, no fetch, the same paint a while
      later), framed by lib/sharecard.js drawingRect's own sums; before a face
      is drawn, an empty circle, never a stock silhouette.
   5. REDRAW replaces it: a new unlisted face, the old one deleted (Skribl's
      delete_post), its link and its picture gone.
   6. EDIT PROFILE: CSRF and Origin required; a name's and a bio's limits and
      character rules refused kindly, what was typed kept; a good save shown;
      the edit's and the face's limits per person; whatever /you/face is sent
      is answered, never a 500, and changes nothing unless it is a face.
   7. GALLERY NAMES LINK TO PROFILES (the author resolver's url, and face);
      the listing's `visibility=public` narrows an author's own listing to
      what anyone is shown, and takes no other value.
   8. THE NEW SCREENS: every word at 4.5:1 on what is painted behind it,
      every target 44px, every text field 16px; phone and desk, light and
      dark.
   9. DELETE MY ACCOUNT takes the face with it (delete_post) and the bio with
      the row; the profile is the kind 404 after.
  10. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS on any of it.
  11. A FACE FROM A SKRIBL YOU MADE (the owner's yes on mock A, Nov 11): Add
      your face raises Your face, Make's own sheet, gliding up, its three doors;
      Use one you made glides the sheet to its new height and lists their own
      Pad skribls (the link-only one too; never a Flip, somebody else's or the
      face they have); one picked is placed in the circle from its middle square,
      moved by a drag and the arrow keys and sized by the slider; Use this
      face keeps a face of its own (707 square, unlisted, its card made, its
      points the drawing's moved and sized into the square) and the drawing it
      came from byte for byte as it was; Open a file... says a Flip and a
      drawing with a picture under it kindly, and keeps a .skribl file; every
      word on the sheet at 4.5:1, every target 44px.
  12. TRACE A PHOTO (the owner's "all yes, build A", Nov 11): Your face's
      third door opens the device's own picker for one photo, and a file
      that is not one is said kindly; a photo picked opens the Pad with it
      under the canvas, a guide at 40%, the drawer's row and its line saying
      what it is, the empty canvas saying Trace your face on a backing that
      reads at 4.5:1 over the photo's darkest middle (off the paint, light and
      dark); Use this face sends the lines alone (no photo in any frame, none
      on the card), and the site drops a photo sent anyway.

The layers (the site imports only Skribl's documented names, and its
templates only documented partials, the face player's now among them) stay
verify_social's, section 8.

SOCIALPROFILE_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Profiles with drawn faces at /social".
"""
import base64
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "harness" / "tools"))
PART = os.environ.get("SOCIALPROFILE_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALPROFILE {n} — {label}")
    return True


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence profiles work.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)
try:
    from PIL import Image
except ImportError:      # declared in harness/requirements.txt; the rows that need it fail, saying so
    Image = None
import artdraw  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialprofile-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialprofile-" + secrets.token_hex(8),
           SKRIBL_CSRF_PROTECT="1", SKRIBL_SOCIAL_FIRST_INVITE=FIRST, SKRIBL_STAND_IN="0",
           SKRIBL_TRUSTED_PROXIES="1", SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000")
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_DEMO_IDENTITY",
          "SKRIBL_DEMO_LOGIN_KEY"):
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
ERRS = []          # page errors, console errors and CSP violations, from every page
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    """An address of its own, for one browser or one client: X-Forwarded-For."""
    _addr[0] += 1
    return f"10.{40 + _addr[0] // 250}.{_addr[0] % 250}.9"


def db(sql, args=(), write=False):
    con = sqlite3.connect(DB, timeout=10)
    try:
        cur = con.execute(sql, args)
        rows = cur.fetchall()
        if write:
            con.commit()
        return rows
    finally:
        con.close()


def cli(*args):
    """`flask --app app social ...`: the last line it printed."""
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", *args, "--base", BASE],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    if out.returncode:
        return None
    return out.stdout.strip().splitlines()[-1]


def person_row(handle):
    """(public_id, display_name, bio, face_id, face_w, face_h) or None."""
    got = db("select public_id, display_name, bio, face_id, face_w, face_h from social_people where handle_key = ?",
             (handle.lower(),))
    return got[0] if got else None


def post_row(public_id):
    got = db("select visibility, user_id, title, canvas_w, canvas_h from skribl_posts where public_id = ?",
             (public_id,))
    return got[0] if got else None


def http(path, method="GET", data=None, headers=None):
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def picture(public_id):
    """What /s/<id>/poster shows now: the drawing's own picture (the share
    card the Pad made, a PNG or a JPEG), or the see-through blank Skribl
    serves for a skribl that is not there (poster-blank.svg; the poster never
    404s, by design)."""
    try:
        with urllib.request.urlopen(BASE + f"/s/{public_id}/poster", timeout=20) as r:
            return r.headers.get_content_type()
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"


#: A drawing's own picture: the share card the Pad made.
RASTER = ("image/png", "image/jpeg", "image/webp")


def listing(extra=""):
    st, raw = http("/api/skribls?limit=100" + extra)
    return json.loads(raw.decode())["items"] if st == 200 else None


# ---- a client without a browser (tokens, limits, odd bodies) -------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """The site's own requests, made without a browser, carrying a signed-in
    person's cookies when given them."""

    def __init__(self, cookies=None, xff=None, origin=BASE):
        self.jar = CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect())
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
                return r.status, r.headers, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8", "replace")

    def get(self, path):
        st, hd, text = self._req("GET", path)
        m = re.search(r'<meta name="social-csrf" content="([^"]+)"', text)
        if m:
            self.token = m.group(1)
        return st, hd, text

    def post_json(self, path, body, token=True):
        h = {"X-Social-CSRF": self.token} if token is True else ({"X-Social-CSRF": token} if token else {})
        st, hd, text = self._req("POST", path, body=body, headers=h)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, form, token=True):
        f = dict(form)
        if token is True:
            f["csrf"] = self.token
        elif token:
            f["csrf"] = token
        return self._req("POST", path, form=f)


# ---- a browser with a passkey -----------------------------------------------------

class Person:
    """One browser (a context, one page, its own virtual authenticator), from
    an address of its own."""

    def __init__(self, b, screen="phone", scheme="light", reduced=False):
        self.xff = address()
        opts = dict(PHONE if screen == "phone" else DESK)
        kw = {"reduced_motion": "reduce"} if reduced else {}
        self.ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": self.xff}, **opts, **kw)
        self.ctx.add_init_script(WATCH)
        self.pg = self.ctx.new_page()
        tag = f"{screen}/{scheme}"
        self.pg.on("pageerror", lambda e: ERRS.append(f"{tag} pageerror: {e}"))
        self.pg.on("console", lambda m: ERRS.append(f"{tag} console {m.type}: {m.text[:160]}")
                   if m.type == "error" and "Failed to load resource" not in m.text else None)
        self.cdp = self.ctx.new_cdp_session(self.pg)
        self.cdp.send("WebAuthn.enable")
        self.aid = self.cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
            "protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
            "hasUserVerification": True, "isUserVerified": True,
            "automaticPresenceSimulation": True}})["authenticatorId"]
        self.handle = None

    def csp(self):
        try:
            return self.pg.evaluate("() => window.__csp || []")
        except Exception:
            return []

    def cookies(self):
        return self.ctx.cookies(BASE)

    def client(self):
        c = Client(cookies=self.cookies(), xff=self.xff)
        return c

    def close(self):
        ERRS.extend(f"csp: {v}" for v in self.csp())
        self.ctx.close()


def browser_as(b, who, screen="phone", scheme="light", reduced=False):
    """Another browser carrying `who`'s cookies (or nobody's), from its address."""
    opts = dict(PHONE if screen == "phone" else DESK)
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **opts, **kw)
    ctx.add_init_script(WATCH)
    if who:
        ctx.add_cookies([{k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly",
                                                             "sameSite", "secure", "expires")}
                         for c in who.cookies()])
    pg = ctx.new_page()
    tag = f"{screen}/{scheme}{' reduced' if reduced else ''} as {who.handle if who else 'nobody'}"
    pg.on("pageerror", lambda e: ERRS.append(f"{tag} pageerror: {e}"))
    pg.on("console", lambda m: ERRS.append(f"{tag} console {m.type}: {m.text[:160]}")
          if m.type == "error" and "Failed to load resource" not in m.text else None)
    return ctx, pg


def close_ctx(ctx, pg):
    try:
        ERRS.extend(f"csp: {v}" for v in pg.evaluate("() => window.__csp || []"))
    except Exception:
        pass
    ctx.close()


def join(p, link, name, handle):
    p.pg.goto(link)
    try:
        p.pg.wait_for_function("() => { const c = document.querySelector('[data-link]');"
                               " return !!c && !c.classList.contains('is-checking'); }", timeout=15000)
        p.pg.fill("#joinName", name)
        p.pg.fill("#joinHandle", handle)
        p.pg.check("#joinAge")
        with p.pg.expect_navigation(timeout=20000):
            p.pg.click("form[data-passkey] button[type=submit]")
    except Exception as exc:
        return f"could not join: {str(exc).splitlines()[0][:120]}"
    p.handle = handle
    return p.pg.url


_people = {}


def member(b, handle, name, **kw):
    """Somebody who joined through an invite (the first one through the
    first-invite code), signed in, in a browser of their own."""
    p = Person(b, **kw)
    if not db("select id from social_people limit 1"):
        link = BASE + "/social/join#" + FIRST
    else:
        link = cli("invite")
    join(p, link, name, handle)
    _people[handle] = p
    return p


def post_skribl(who, title, visibility="public", base=None):
    """One drawing through Skribl's own API as `who` (Skribl is told who is
    signed in to the site: CSRF is on), or as nobody. `base` is the picture
    it began on, a data URL, where the Pad keeps one (its frame's
    baseSnapshot)."""
    ctx = who.ctx if who else None
    if ctx is None:
        jar = CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        op.open(BASE + "/api/skribls?limit=1", timeout=20).read()
        tok = next((k.value for k in jar if k.name == "skribl_csrf"), "")
    else:
        ctx.request.get(BASE + "/api/skribls?limit=1")
        tok = next((c["value"] for c in ctx.cookies(BASE) if c["name"] == "skribl_csrf"), "")
    pts = [{"x": round(408 + math.cos(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "y": round(306 + math.sin(i / 59 * 4 * math.pi) * (20 + i * 2.3), 1),
            "color": "#7c5cff", "size": 6 + (i % 5), "t": i * 40, "start": i == 0} for i in range(60)]
    body = {"title": title, "caption": "", "version": 2, "schemaVersion": 2, "playbackMode": "replay",
            "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}
    if base:
        body["frames"][0]["baseSnapshot"] = base
    if visibility:
        body["visibility"] = visibility
    h = {"Content-Type": "application/json", "X-Skribl-CSRF": tok}
    if ctx is None:
        req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(), headers=h)
        with op.open(req, timeout=20) as r:
            return json.loads(r.read().decode())["id"]
    r = ctx.request.post(BASE + "/api/skribls", data=json.dumps(body), headers=h)
    return r.json().get("id") if r.ok else None


# ---- a face, drawn through the real Pad with a pen ----------------------------------

PURPLE, INK, PINK = artdraw.PURPLE, artdraw.INK, "#ff6f91"


def _arc(cx, cy, rx, ry, a0, a1, n=16):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def face_strokes():
    """A face as an artist draws one: the head's outline, the hair, the
    features, the blush last; three colours on the paper."""
    S = artdraw.Stroke
    hair = [(354 + 205 * math.cos(math.radians(a)) * (1 + 0.06 * math.sin(math.radians(a * 7))),
             300 + 190 * math.sin(math.radians(a))) for a in range(165, 376, 6)]
    return [S(_arc(354, 360, 170, 205, 200, -20, 22), "gesture", INK, size=24),
            S(hair, "contour", PURPLE, size=26),
            S(_arc(284, 350, 26, 24, 0, 360, 12), "form", INK, size=14),
            S(_arc(424, 350, 26, 24, 0, 360, 12), "form", INK, size=14),
            S(_arc(354, 448, 58, 34, 20, 160, 10), "detail", INK, size=13),
            S(_arc(244, 430, 18, 11, 0, 700, 14), "fill", PINK, size=14),
            S(_arc(464, 430, 18, 11, 0, 700, 14), "fill", PINK, size=14)]


def quick_face():
    """A second face, quicker: a round head and two dots."""
    S = artdraw.Stroke
    return [S(_arc(354, 354, 200, 200, 0, 360, 24), "gesture", PURPLE, size=28),
            S(_arc(290, 330, 10, 10, 0, 360, 8), "detail", INK, size=22),
            S(_arc(418, 330, 10, 10, 0, 360, 8), "detail", INK, size=22)]


class _InFrame:
    """artdraw's page, for a Pad in an iframe: the pen goes in at the top
    page's own coordinates, the editor's state is the frame's."""

    def __init__(self, page, frame):
        self.page, self.frame = page, frame
        outer = page.context

        class _Ctx:
            def new_cdp_session(_self, _p):
                return outer.new_cdp_session(page)
        self.context = _Ctx()

    def locator(self, sel):
        return self.frame.locator(sel)

    def evaluate(self, js, arg=None):
        return self.frame.evaluate(js, arg) if arg is not None else self.frame.evaluate(js)


OVERLAY = """() => { const w = document.getElementById('facePad'); if (!w) return null;
  const s = w.querySelector('.facepad-sheet'), r = s.getBoundingClientRect(), a = document.activeElement;
  return { open: !w.hidden && w.classList.contains('is-open'), hidden: w.hidden, top: Math.round(r.top),
           role: s.getAttribute('role'), modal: s.getAttribute('aria-modal'),
           src: w.querySelector('iframe').getAttribute('src'),
           inert: ['body > .top', 'body > .nav', '#main'].map(q => { const e = document.querySelector(q); return !!e && e.hasAttribute('inert'); }),
           focus: a ? (a.tagName + (a.className ? '.' + a.className : '')) : null,
           opacity: +getComputedStyle(s).opacity }; }"""
# The overlay's sheet on every animation frame from the press that opens it
# (verify_glide's way, as verify_social reads Make's sheet).
GLIDE = """([sel, ms]) => new Promise(res => { const s = document.querySelector('#facePad .facepad-sheet'), out = [];
  const t0 = performance.now(); document.querySelector(sel).click();
  (function f() { const r = s.getBoundingClientRect(); out.push([Math.round(r.top * 10) / 10, +getComputedStyle(s).opacity]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""


# ...and while a person presses the Pad's own x (inside the frame, a real
# click), until it has long gone: the sheet's place, its opacity and whether
# it is hidden yet, every frame, kept in the page and read after.
SAMPLE = """(ms) => { const w = document.getElementById('facePad'), s = w.querySelector('.facepad-sheet'), out = window.__sheet = [];
  const t0 = performance.now();
  (function f() { const r = s.getBoundingClientRect(); out.push([Math.round(r.top * 10) / 10, +getComputedStyle(s).opacity, w.hidden]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); })(); }"""


def close_glide(pg, frame, ms=1400):
    """The Pad's x pressed as a person presses it, the sheet read every frame."""
    pg.evaluate(SAMPLE, ms)
    try:
        frame.click("#composeCloseBtn", timeout=5000)
    except Exception as exc:
        ERRS.append(f"could not press the Pad's x: {str(exc).splitlines()[0][:100]}")
    pg.wait_for_timeout(ms + 150)
    frames = pg.evaluate("() => window.__sheet || []")
    # From the last frame at rest before it moved or faded, to the last one.
    moved = next((i for i, f in enumerate(frames) if f[0] != frames[0][0] or f[1] != frames[0][1] or f[2]),
                 len(frames))
    return frames[max(0, moved - 1):]
# THE FIRST PAINT'S SHAPE: the Pad with its scripts held back, so only the
# early fit (_skribl_fit_early.html, before anything paints) has laid it out.
FIRST_SHAPE = """() => { const w = document.querySelector('.canvas-wrap'); if (!w) return null; const r = w.getBoundingClientRect();
  return { w: Math.round(r.width), h: Math.round(r.height), fit: document.documentElement.classList.contains('skribl-fit'),
           booted: !!(window.__skriblBoot && window.__skriblBoot.pad) }; }"""


def pad_frame(pg, timeout=30):
    """The Pad in the overlay, once it can be drawn on."""
    end = time.time() + timeout
    while time.time() < end:
        fr = next((f for f in pg.frames if "face=1" in (f.url or "")), None)
        if fr:
            try:
                fr.wait_for_function("() => !!document.getElementById('canvas') && typeof getCanvasLogicalSize === 'function'"
                                     " && !!(window.__skriblBoot && window.__skriblBoot.pad)", timeout=1000)
                return fr
            except Exception:
                pass
        pg.wait_for_timeout(200)
    return None


def draw_in_pad(pg, frame, strokes, tempo=1.6, gaps=2.6):
    frame.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); setTool('pen');"
                   " if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
    artdraw.draw(_InFrame(pg, frame), strokes, tempo=tempo, pause_tempo=gaps)
    pg.wait_for_timeout(400)


# Your face's circle is up, at its place step.
PLACED = """() => { const w = document.getElementById('faceSheet'), s = w && w.querySelector('[data-step=place]');
  return !!s && !s.hidden && w.classList.contains('is-open'); }"""


def use_in_pad(pg, frame):
    """End the take, open the Pad's sheet and press its button ("Use"), as a
    person does. Returns what the sheet said."""
    if frame.evaluate("() => typeof recording !== 'undefined' && !!recording"):
        frame.click("#recordBtn", timeout=5000)
        pg.wait_for_timeout(400)
    frame.click("#postBtn", timeout=5000)
    pg.wait_for_timeout(700)
    sheet = frame.evaluate("""() => ({ head: (document.querySelector('#postSheet .export-head') || {}).textContent,
        label: (document.getElementById('postSubmitLabel') || {}).textContent })""")
    frame.click("#postSubmitBtn", timeout=5000)
    return sheet


def keep_in_pad(pg, frame):
    """Use in the Pad; the circle comes up with the drawing in it (the
    owner's all yes, after v330: "the circle after the Pad, every time"), and
    its Use this face keeps it; land wherever the site sends. A drawing the
    circle cannot take is kept at once, as it was drawn. What the page sent is
    kept, and the sheet says whether the circle came."""
    sent = {}

    def on_req(r):
        if r.method == "POST" and r.url.split("?")[0].endswith("/social/you/face"):
            sent["body"] = r.post_data
    pg.on("request", on_req)
    try:
        sheet = use_in_pad(pg, frame)
        try:
            pg.wait_for_function(PLACED, timeout=15000)
            sheet["circle"] = True
        except Exception:
            sheet["circle"] = False
        if sheet["circle"]:
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                pg.click("#faceSheet [data-face-use]", timeout=5000)
        pg.wait_for_load_state()
        pg.wait_for_timeout(300)
    except Exception as exc:
        sheet = {"could not": str(exc).splitlines()[0][:140]}
    finally:
        pg.remove_listener("request", on_req)
    return sheet, sent.get("body")


FACE_PAYLOAD = {}


def open_face_sheet(pg, wait=520):
    """Your face, raised as a person raises it: the button beside Edit profile
    (Change my face, or Add your face), and the sheet's glide let finish."""
    pg.click("button[data-face-sheet]", timeout=5000)
    pg.wait_for_timeout(wait)


def draw_face(p, strokes=None, tempo=1.6, gaps=2.6):
    """`p` draws their face on their own profile, through the real Pad, and
    keeps it. Returns what the Pad's sheet said and where the page landed."""
    pg = p.pg
    pg.goto(BASE + f"/social/@{p.handle}")
    pg.wait_for_timeout(300)
    try:
        open_face_sheet(pg)
        pg.click("#faceSheet [data-face-open]", timeout=5000)
    except Exception as exc:
        return {"could not": str(exc).splitlines()[0][:120]}, None
    fr = pad_frame(pg)
    if fr is None:
        return {"no Pad in the overlay": True}, None
    draw_in_pad(pg, fr, strokes or face_strokes(), tempo, gaps)
    sheet, body = keep_in_pad(pg, fr)
    if body and "payload" not in FACE_PAYLOAD:
        try:
            FACE_PAYLOAD["payload"] = json.loads(body)["payload"]
        except (ValueError, KeyError, TypeError):
            pass
    return sheet, pg.url


def give_face(b, p):
    """A face for `p`, as the profile's page sends one (the drawing the real
    Pad handed back in section 2, or a new one through the Pad when that
    section did not run)."""
    if "payload" not in FACE_PAYLOAD:
        sheet, landed = draw_face(p)
        return person_row(p.handle)[3]
    c = p.client()
    c.get(f"/social/@{p.handle}")
    st, j = c.post_json("/social/you/face", {"payload": FACE_PAYLOAD["payload"]})
    return person_row(p.handle)[3] if st == 200 else None


# ---- what is painted ------------------------------------------------------------------

def ink(png, ground=(246, 242, 234)):
    """The drawn face as painted: every pixel inside the circle that is not
    the Pad's paper (the face's own ground, and the empty circle's before
    the drawing arrives)."""
    if not png:
        return None
    im = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = im.size
    cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 3
    px = im.load()
    n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                continue
            rr, gg, bb = px[x, y]
            if abs(rr - ground[0]) + abs(gg - ground[1]) + abs(bb - ground[2]) > 90:
                n += 1
    return n


def shot(pg, sel):
    try:
        return pg.locator(sel).first.screenshot(timeout=5000, animations="allow")
    except Exception:
        return None


# Every image under each selector loaded and decoded: a picture that has
# come, not one on its way (section 4: the still face photographed twice).
PAINTED = """(sels) => sels.every(s => { const i = document.querySelector(s + ' img');
  return !!i && i.complete && i.naturalWidth > 0; })"""
DECODED = """(sels) => Promise.all(sels.map(s => { const i = document.querySelector(s + ' img');
  return i && i.decode ? i.decode().catch(() => null) : null; }))"""


# THE SITE'S OWN WORDS AND CONTROLS, read from the paint (verify_socialauth's
# reader, with the face player counted among Skribl's parts, which keep their
# own: a face has no words).
READ = """(sel) => {
  const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const ground = e => { const layers = [];
    for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const SKRIBLS = '.skribl-inline, #skriblGallery, .skribl-face';
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99 };
  const roots = [...document.querySelectorAll(sel || 'main, header.top, nav.nav')];
  roots.forEach(root => root.querySelectorAll('*').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
    const c = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;
    const st = getComputedStyle(e);
    if (+st.opacity === 0) return;
    const k = ratio(rgba(st.color), ground(e));
    out.read++; out.lowest = Math.min(out.lowest, Math.round(k * 100) / 100);
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 24) + '" ' + k.toFixed(2));
  }));
  document.querySelectorAll('a[href], button, summary, label.check, input:not([type=hidden]):not([type=checkbox]), textarea').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, #makeSheet, #facePad, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    if (e.matches('input') && e.closest('.at')) { const a = e.closest('.at').getBoundingClientRect();
      if (a.height < 44) out.small.push('field ' + (e.id || e.name) + ' ' + Math.round(a.height)); }
    else { const r = e.getBoundingClientRect();
      if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

# THE FACE PLAYER'S FRAME, from the module itself: lib/sharecard.js
# drawingRect(), its middle square 3 card pixels in, as shares of the circle.
FRAME_JS = """([src, sizes]) => { (0, eval)(src); const C = window.SkriblShareCard;
  return sizes.map(([w, h]) => { const d = C.drawingRect(w, h), m = Math.min(d.w, d.h), side = m - 6;
    return { w: 120000 / side, x: -100 * (d.x + (d.w - m) / 2 + 3) / side, y: -100 * (d.y + (d.h - m) / 2 + 3) / side }; }); }"""
SHARECARD = (ROOT / "skribl" / "static" / "lib" / "sharecard.js").read_text(encoding="utf-8")


def frame_of(style):
    """The three shares a face's markup (custom properties) or a card's
    avatar (inline left, top, width) carries."""
    def num(pat):
        m = re.search(pat, style or "")
        return float(m.group(1)) if m else None
    w = num(r"--skribl-face-w:\s*(-?[\d.]+)%") or num(r"(?<![-\w])width:\s*(-?[\d.]+)%")
    x = num(r"--skribl-face-x:\s*(-?[\d.]+)%") or num(r"(?<![-\w])left:\s*(-?[\d.]+)%")
    y = num(r"--skribl-face-y:\s*(-?[\d.]+)%") or num(r"(?<![-\w])top:\s*(-?[\d.]+)%")
    return {"w": w, "x": x, "y": y}


def same_frame(a, b, tol=0.01):
    return all(a.get(k) is not None and abs(a[k] - b[k]) <= tol for k in ("w", "x", "y"))


with sync_playwright() as p_:
    b = p_.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "a profile: name, handle, bio and only their public skribls; any case; a kind 404"):
        mira = member(b, "mira", "Mira Okafor")
        juno = member(b, "juno", "Juno Park")
        mc = mira.client()
        mc.get("/social/you/edit")
        bio = "Cats, coffee and the 6 a.m. light.\nDrawing something every day this year."
        st_bio = mc.post_form("/social/you/edit", {"name": "Mira Okafor", "bio": bio})[0]
        tag = secrets.token_hex(3)
        older = post_skribl(mira, f"Mira's older {tag}")
        newer = post_skribl(mira, f"Mira's newer {tag}")
        hidden = post_skribl(mira, f"Mira's link-only {tag}", visibility=None)
        theirs = post_skribl(juno, f"Juno's {tag}")
        mid = person_row("mira")[0]

        def profile_view(pg, handle):
            pg.goto(BASE + f"/social/@{handle}")
            try:
                pg.wait_for_function("() => document.querySelectorAll('#galleryList > article.tile').length > 0"
                                     " || !document.getElementById('galleryEmpty').hidden", timeout=15000)
            except Exception:
                pass
            pg.wait_for_timeout(300)
            return pg.evaluate("""() => { const t = s => { const e = document.querySelector(s); return e ? e.innerText : null; };
                const g = document.getElementById('skriblGallery');
                return { name: t('.prof-name'), handle: t('.prof-handle'), bio: t('.prof-bio'),
                         author: g && g.getAttribute('data-skribl-author'), sections: document.querySelectorAll('[data-skribl-gallery]').length,
                         tiles: [...document.querySelectorAll('#galleryList > article.tile')].map(a => a.getAttribute('data-id')),
                         canonical: (document.querySelector('link[rel=canonical]') || {}).href || null,
                         title: document.title }; }""")
        vctx, vpg = browser_as(b, juno)
        seen_by_juno = profile_view(vpg, "mira")
        close_ctx(vctx, vpg)
        actx, apg = browser_as(b, None)
        seen_by_nobody = profile_view(apg, "mira")
        close_ctx(actx, apg)
        check("a profile shows the person's name, @handle and bio (its line break kept), and Skribl's own Gallery"
              " section with their public skribls only, newest first: to somebody signed in and to nobody alike",
              st_bio == 303 and all(v["name"] == "Mira Okafor" and v["handle"] == "@mira" and v["bio"] == bio
                                    and v["author"] == mid and v["sections"] == 1 and v["tiles"] == [newer, older]
                                    for v in (seen_by_juno, seen_by_nobody)),
              f"bio saved {st_bio}; seen by Juno {seen_by_juno}; by nobody {seen_by_nobody}; ids: newer {newer},"
              f" older {older}, link-only {hidden}, Juno's {theirs}")
        own = profile_view(mira.pg, "mira")
        check("on your own profile you see what your visitors see: your public skribls, not the link-only one",
              own["tiles"] == [newer, older], f"{own['tiles']}; link-only {hidden}")
        # AN EMPTY PROFILE IN ITS OWN WORDS (the owner's yes, Nov 10): to its
        # own person, what puts a skribl there, in the Pad's tick's words; to
        # anybody else, signed in or not, only that there are none yet. It
        # said "their author" to its own author before.
        ines = member(b, "ines", "Ines Vale")

        def empty_words(pg):
            pg.goto(BASE + "/social/@ines")
            try:
                pg.wait_for_function("() => !document.getElementById('galleryEmpty').hidden", timeout=15000)
            except Exception:
                pass
            return pg.evaluate("""() => { const e = document.getElementById('galleryEmpty');
                return e && !e.hidden ? e.innerText.replace(/\\s+/g, ' ').trim() : null; }""")
        own_empty = empty_words(ines.pg)
        ectx, epg = browser_as(b, juno)
        their_empty = empty_words(epg)
        close_ctx(ectx, epg)
        nctx, npg = browser_as(b, None)
        nobodys_empty = empty_words(npg)
        close_ctx(nctx, npg)
        check("an empty profile says it in its own words: to its own person what puts a skribl there (the Pad's"
              " tick), to anybody else only that there are none yet",
              own_empty == ("Nothing here yet. Your skribls show here when you tick Show in the public gallery as"
                            " you post, or later in your Library.")
              and their_empty == "No skribls here yet." and nobodys_empty == "No skribls here yet.",
              f"own {own_empty!r}; Juno's view {their_empty!r}; signed out {nobodys_empty!r}")
        actx, apg = browser_as(b, None)
        loud = profile_view(apg, "MiRa")
        close_ctx(actx, apg)
        resp = http("/social/@MIRA")[0]
        check("a handle written in another case is the same profile, and the page names its own address",
              resp == 200 and loud["name"] == "Mira Okafor" and (loud["canonical"] or "").endswith("/social/@mira"),
              f"{resp}; {loud['name']}; canonical {loud['canonical']}")
        st_none, body_none = http("/social/@nobody_here")
        st_odd, body_odd = http("/social/@" + urllib.parse.quote("9<b>x"))
        words_none = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_none.decode()))
        words_odd = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_odd.decode()))
        check("a handle nobody has is a kind not-found (404): one card that blames nobody, the handle said back only"
              " when it could be one",
              st_none == 404 and "Nobody here by that name" in words_none and "@nobody_here" in words_none
              and st_odd == 404 and "Nobody here by that name" in words_odd and "at that address" in words_odd
              and "9<b>x" not in body_odd.decode() and "9&lt;b&gt;x" not in body_odd.decode(),
              f"nobody {st_none} {words_none[words_none.find('Nobody'):][:120]!r}; odd {st_odd}")
        places = {}
        for screen in ("phone", "desk"):
            ctx, pg = browser_as(b, mira, screen)
            for where in ("mira", "juno"):
                pg.goto(BASE + f"/social/@{where}")
                pg.wait_for_timeout(300)
                places[(screen, where)] = pg.evaluate("""() => { const y = document.querySelector('nav.nav .tab-you');
                    return { href: y && y.getAttribute('href'), current: [...document.querySelectorAll('nav.nav [aria-current]')]
                             .map(e => (e.querySelector('.tab-name') || e).textContent.trim()),
                             gear: [...document.querySelectorAll('header.top a[href$="/social/you"], .prof-acts a[href$="/social/you"]')]
                                   .filter(a => a.getClientRects().length).map(a => a.getAttribute('href')),
                             acts: [...document.querySelectorAll('.prof-acts > *')].filter(e => e.getClientRects().length)
                                   .map(e => e.matches('.fo-btn') ? 'follow' : e.matches('[data-share]') ? 'share'
                                        : e.matches('[data-person-menu]') ? 'more' : e.matches('[href$="/you/edit"]') ? 'edit'
                                        : e.matches('[data-face-sheet]') ? 'face' : e.matches('a[href$="/social/you"]') ? 'gear'
                                        : e.tagName.toLowerCase()) }; }""")
            close_ctx(ctx, pg)
        # FOLLOWS (the owner's B, Nov 13): Follow first in the row on somebody
        # else's profile, before Share and ⋯; never on your own.
        check("the row of buttons: on somebody else's profile Follow, Share and ⋯ (follows: Follow first); on your own"
              " Edit profile, your face and Share (and on a desk the gear), no Follow",
              all(places[(s, "juno")]["acts"] == ["follow", "share", "more"] for s in ("phone", "desk"))
              and places[("phone", "mira")]["acts"] == ["edit", "face", "share"]
              and places[("desk", "mira")]["acts"] == ["edit", "face", "share", "gear"],
              json.dumps({f"{k[0]} @{k[1]}": v["acts"] for k, v in places.items()}))
        check("You leads to your own profile, on the bar and the rail, and is the place marked there; somebody else's"
              " profile marks no place",
              all(places[(s, "mira")]["href"] == "/social/@mira" and places[(s, "mira")]["current"] == ["You"]
                  and places[(s, "juno")]["current"] == [] for s in ("phone", "desk")),
              json.dumps({f"{k[0]} @{k[1]}": v for k, v in places.items()}))
        # PAGING STAYS WITHIN THEM: past one page of 24, Load more brings the
        # rest of theirs by the listing's own cursor, and nobody else's.
        many = [post_skribl(juno, f"Juno's page {tag} {i}") for i in range(26)]
        pctx, ppg = browser_as(b, None)
        ppg.goto(BASE + "/social/@juno")
        try:
            ppg.wait_for_function("() => document.querySelectorAll('#galleryList > article.tile').length >= 24", timeout=15000)
        except Exception:
            pass
        first_page = ppg.evaluate("() => [...document.querySelectorAll('#galleryList > article.tile')].map(a => a.getAttribute('data-id'))")
        try:
            ppg.click("#galleryMore", timeout=5000)
            ppg.wait_for_function("(n) => document.querySelectorAll('#galleryList > article.tile').length > n",
                                  arg=len(first_page), timeout=15000)
        except Exception:
            pass
        ppg.wait_for_timeout(400)
        both = ppg.evaluate("() => [...document.querySelectorAll('#galleryList > article.tile')].map(a => a.getAttribute('data-id'))")
        more_left = ppg.evaluate("() => { const m = document.getElementById('galleryMore'); return !!m && !m.hidden; }")
        close_ctx(pctx, ppg)
        juno_all = [theirs] + many
        check("past a page, Load more brings the rest of their skribls by the listing's own cursor, and nobody else's",
              len(first_page) == 24 and len(both) == 27 and sorted(both) == sorted(juno_all) and len(set(both)) == 27
              and not more_left,
              f"first page {len(first_page)}, after Load more {len(both)} (theirs {len(juno_all)}), more left {more_left};"
              f" others' among them {sorted(set(both) - set(juno_all))[:3]}")
        sp = mira.client()
        st_set, _, set_text = sp.get("/social/you")
        # The gear says Settings since the Settings mock's a (after v330), so it
        # is found by where it leads, not by a name only it had;
        # verify_socialsettings holds its word and its size.
        check("the gear on your own profile (the phone's top, beside the buttons on a desk) leads to Settings, the"
              " account page as before; nobody else's profile has one",
              all(places[(s, "mira")]["gear"] == ["/social/you"] and places[(s, "juno")]["gear"] == []
                  for s in ("phone", "desk"))
              and st_set == 200 and '<h1 class="page-title">Settings</h1>' in set_text and "Your passkeys" in set_text,
              f"gears {[places[k]['gear'] for k in places]}; settings {st_set}")

    # ------------------------------------------------------------------ 2
    if part(2, "draw your face through the real Pad, kept as an unlisted skribl that is their face"):
        theo = member(b, "theo", "Theo Lind")
        pg = theo.pg
        pg.goto(BASE + "/social/@theo")
        pg.wait_for_timeout(400)
        blank = pg.evaluate("""() => { const a = document.querySelector('.prof-face .face-ask'), btn = document.querySelector('button[data-face-sheet]');
            return { ask: a ? a.innerText.replace(/\\s+/g, ' ').trim() : null, button: btn ? btn.innerText.trim() : null,
                     img: !!document.querySelector('.prof-face img, .prof-face svg:not(.ic)') }; }""")
        closed = pg.evaluate(OVERLAY)
        open_face_sheet(pg)
        frames = pg.evaluate(GLIDE, ["#faceSheet [data-face-open]", 900])
        opened = pg.evaluate(OVERLAY)
        tops = [f[0] for f in frames]
        steps = [z - a for a, z in zip(tops, tops[1:])]
        travel = abs(tops[0] - opened["top"]) if tops else 0
        check("Add your face, then Draw a new one, opens the Pad over the page: a modal dialog, the page behind inert,"
              " the Pad's address set only now; it glides up from below the screen, on many frames, one way, never a jump",
              blank["ask"] == "Add your face" and blank["button"] == "Add your face" and not blank["img"]
              and closed["hidden"] and not closed["src"]
              and opened["open"] and opened["role"] == "dialog" and opened["modal"] == "true" and all(opened["inert"])
              and (opened["src"] or "").endswith("compose=1&face=1")
              and tops and tops[0] >= 860 and abs(tops[-1] - opened["top"]) <= 0.5 and len(set(tops)) >= 8
              and all(s <= 0 for s in steps) and max((abs(s) for s in steps), default=0) <= 0.3 * travel,
              f"before {blank}; closed {closed}; opened {opened}; glide from {tops[:1]} to {tops[-1:]} on"
              f" {len(set(tops))} positions, biggest step {max((abs(s) for s in steps), default=0):.1f} of {travel}")
        fr = pad_frame(pg)
        # Use pressed on the empty canvas: it says, in a face's words, what is
        # missing (the status region compose mode speaks through).
        empty_said = None
        if fr:
            try:
                fr.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
                fr.click("#postBtn", timeout=5000)
                pg.wait_for_timeout(400)
                empty_said = fr.evaluate("""() => { const t = document.getElementById('toast'), o = document.getElementById('postOverlay');
                    return { said: t ? t.textContent.trim() : null, role: t && t.getAttribute('role'), sheet: !!o && !o.hidden,
                             title: document.getElementById('postBtn').getAttribute('title') }; }""")
            except Exception as exc:
                empty_said = {"could not": str(exc).splitlines()[0][:100]}
        pad = fr.evaluate("""() => { const s = getCanvasLogicalSize(), q = id => document.getElementById(id);
            const fields = document.querySelector('#postSheet .post-fields');
            return { w: s.width, h: s.height, label: (q('postSubmitLabel') || {}).textContent,
                     head: ((document.querySelector('#postSheet .export-head') || {}).firstChild || {}).textContent,
                     header: (document.querySelector('#postBtn .btn-label') || {}).textContent,
                     fieldsHidden: !!fields && fields.hidden, speed: !!q('postSpeedSeg'), tick: !!q('postPublicInput'),
                     flip: !!q('flipBtn'), close: !!q('composeCloseBtn'), hint: (q('canvasEmptyHint') || {}).innerText }; }""") if fr else None
        check("the Pad there is the real one in its face mode (compose=1&face=1): a square canvas, a face's words"
              " (Draw your face; Your face; Use this face; a press with nothing drawn says Draw your face first), no"
              " title, no Viewers start at, no gallery tick and no switch to Flip",
              bool(pad) and pad["w"] == pad["h"] == 707 and pad["label"] == "Use this face"
              and isinstance(empty_said, dict) and empty_said.get("said") == "Draw your face first"
              and empty_said.get("role") == "status" and empty_said.get("sheet") is False
              and empty_said.get("title") == "Keep it as your face"
              and (pad["head"] or "").strip() == "Your face" and "Use" in (pad["header"] or "")
              and pad["fieldsHidden"] and not pad["speed"] and not pad["tick"] and not pad["flip"] and pad["close"]
              and "Draw your face" in (pad["hint"] or ""),
              f"{json.dumps(pad)}; Use with nothing drawn {empty_said}")
        # THE CLOSE, READ ON EVERY FRAME as the opening is: an overlay that
        # only ends up hidden could vanish in one frame and read the same.
        down = close_glide(pg, fr) if fr else []
        shut = pg.evaluate(OVERLAY)
        dtops = [f[0] for f in down if not f[2]]
        dsteps = [z - a for a, z in zip(dtops, dtops[1:])]
        dtravel = (max(dtops) - dtops[0]) if dtops else 0
        check("the Pad's own x closes it, gliding down the way it came, on many frames, one way, never a jump: the"
              " page behind usable again, focus back on the button that opened it, and nothing kept",
              shut["hidden"] and not any(shut["inert"]) and (shut["focus"] or "").startswith("BUTTON")
              and person_row("theo")[3] is None and len(set(dtops)) >= 6 and all(z >= 0 for z in dsteps)
              and dtravel >= 600 and max(dsteps, default=0) <= 0.35 * dtravel,
              f"{shut}; face {person_row('theo')[3]}; glide down from {dtops[:1]} to {dtops[-1:]} on"
              f" {len(set(dtops))} positions, biggest step {max(dsteps, default=0):.1f} of {dtravel}")
        # THE FIRST PAINT: with the Pad's scripts held back, the page is laid
        # out by the early fit alone, and in face mode it is square from there;
        # the same address without face=1 is not (a phone starts tall), which
        # is what says this reading can tell the two apart.
        firsts = {}
        for q in ("/skribl-pad?compose=1&face=1", "/skribl-pad?compose=1"):
            fctx = b.new_context(**PHONE, extra_http_headers={"X-Forwarded-For": address()})
            fctx.route("**/*", lambda route: route.abort() if route.request.resource_type == "script"
                       and "/static/" in route.request.url and "/lib/" not in route.request.url else route.continue_())
            fpg = fctx.new_page()
            fpg.goto(BASE + q)
            fpg.wait_for_timeout(500)
            firsts[q] = fpg.evaluate(FIRST_SHAPE)
            fctx.close()
        face_first, post_first = firsts["/skribl-pad?compose=1&face=1"], firsts["/skribl-pad?compose=1"]
        check("and it is square from the first paint: laid out square before any of the Pad's own scripts run (the"
              " early fit), where a post's Pad on the same phone starts tall",
              bool(face_first) and face_first["fit"] and not face_first["booted"] and face_first["w"] > 200
              and abs(face_first["w"] - face_first["h"]) <= 2
              and bool(post_first) and post_first["h"] > 1.3 * post_first["w"],
              f"face mode {face_first}; a post's {post_first}")
        before = listing() or []
        sheet, landed = draw_face(theo)
        row = person_row("theo")
        face = row[3]
        post = post_row(face) if face else None
        after = listing() or []
        theirs = listing("&visibility=public&user_id=" + urllib.parse.quote(row[0])) or []
        st_get = http(f"/api/skribls/{face}")[0] if face else None
        check("Use this face keeps it as their face: ONE new skribl, UNLISTED, theirs (Skribl's user is their public"
              " id), its id and canvas size on their row; no listing shows it, and its own link plays it",
              bool(face) and post is not None and post[0] == "unlisted" and post[1] == row[0]
              and (row[4], row[5]) == (707, 707) == (post[3], post[4]) and post[2] == "Theo Lind’s face"
              and len(after) == len(before) and all(i["id"] != face for i in after) and theirs == [] and st_get == 200
              and picture(face) in RASTER
              and db("select count(*) from skribl_posts where user_id = ?", (row[0],))[0][0] == 1,
              f"sheet {sheet}; landed {landed}; row {row}; post {post}; listed {len(before)} -> {len(after)}, theirs"
              f" {len(theirs)}; GET {st_get}; its picture {picture(face) if face else None}")
        pg.wait_for_timeout(600)
        back = pg.evaluate("""() => { const y = document.querySelector('nav.nav .tab-you .skribl-face'), i = y && y.querySelector('img');
            return { at: location.pathname + location.search, note: (document.querySelector('.note') || {}).textContent || '',
                     you: y ? y.getAttribute('data-play') : null, src: i ? i.getAttribute('src') : null,
                     button: (document.querySelector('button[data-face-sheet]') || {}).textContent || '' }; }""")
        check("the page comes back with a kind note, Change my face, and You in the bar wearing the new face, still",
              back["at"] == "/social/@theo?note=face" and "That’s your face now" in back["note"]
              and back["you"] == "still" and back["src"] == f"/s/{face}/poster" and "Change my face" in back["button"],
              json.dumps(back))
        rctx, rpg = browser_as(b, theo, reduced=True)
        rpg.goto(BASE + "/social/@theo")
        rpg.wait_for_timeout(400)
        open_face_sheet(rpg)
        rframes = rpg.evaluate(GLIDE, ["#faceSheet [data-face-open]", 700])
        # Read the way out too: with only opacity changing, an overlay that
        # would drop off the bottom stands where it rests on the way in either
        # way; on the way out it would leave in one frame, still showing.
        rpad = pad_frame(rpg)
        rgone = close_glide(rpg, rpad) if rpad else []
        rtops = sorted({f[0] for f in rframes if f[1] > 0.02})
        rtops_out = sorted({f[0] for f in rgone if not f[2] and f[1] > 0.02})
        fades = (len({round(f[1], 2) for f in rframes}), len({round(f[1], 2) for f in rgone if not f[2]}))
        check("under Reduce Motion the overlay does not move: it fades in where it rests, and out there, every frame",
              len(rtops) == 1 and rframes[-1][1] >= 0.99 and rtops_out == rtops and min(fades) >= 3,
              f"tops while seen, opening {rtops[:4]}, closing {rtops_out[:4]}; opacities in the fades {fades}")
        close_ctx(rctx, rpg)
        _people["theo"] = theo

    # ------------------------------------------------------------------ 3
    if part(3, "it draws itself once on the profile, at about 4x, and rests; still under Reduce Motion"):
        theo = _people.get("theo") or member(b, "theo", "Theo Lind")
        face = person_row("theo")[3] or give_face(b, theo)
        vctx, vpg = browser_as(b, None)
        fetched = []
        vpg.on("request", lambda r: fetched.append(r.url) if r.url.split("?")[0].endswith(f"/api/skribls/{face}") else None)
        # THE DRAWING HELD BACK A MOMENT, so the circle before it can be
        # photographed however slow the machine is: how soon the first photo
        # lands depends on the machine; the face's start does not. The page's
        # one fetch of it waits here, and is let go once the photos are in.
        held = []
        vpg.route(f"**/api/skribls/{face}", lambda route: held.append(route))
        vpg.goto(BASE + "/social/@theo")
        sel = ".prof-face .skribl-face"
        before = []
        for _ in range(4):
            if Image is not None:
                before.append(ink(shot(vpg, sel)))
            vpg.wait_for_timeout(120)
        for route in held:
            route.continue_()
        film = []
        t0 = time.time()
        while time.time() - t0 < 7.5 and Image is not None:
            png = shot(vpg, sel)
            if png:
                film.append((round(time.time() - t0, 3), ink(png)))
        state = vpg.evaluate("""() => { const f = document.querySelector('.prof-face .skribl-face'), b = f && f.querySelector('.skribl-inline'),
            p = b && b._skriblInline, s = p && p.state();
            return { cls: f && f.className, rate: f && f.getAttribute('data-skribl-rate'), speed: f && f.getAttribute('data-skribl-speed'),
                     state: s && s.state, total: s && Math.round(s.totalMs), at: s && Math.round(s.elapsedMs), looping: p && p.looping(),
                     ambient: !!(p && p.ambient) }; }""")
        rest = [ink(shot(vpg, sel))] if Image is not None else []
        vpg.wait_for_timeout(1000)
        if Image is not None:
            rest.append(ink(shot(vpg, sel)))
        close_ctx(vctx, vpg)
        inks = [i for _, i in film]
        top = max(inks, default=0)
        rises = sum(1 for a, z in zip(inks, inks[1:]) if z > a)
        check("on their profile the face draws itself: from the empty circle (photographed while its drawing is on"
              " the way), its ink comes in over time, read from the paint (photographs of the circle)",
              len(held) == 1 and len(before) == 4 and None not in before and max(before) <= 0.03 * max(top, 1)
              and len(film) >= 12 and top > 100 and rises >= 6,
              (f"while the drawing was on its way {before}; then {len(film)} photos, ink {inks[:6]} ... {inks[-3:]};"
               f" rose on {rises}" if film
               else ("Pillow is not here (harness/requirements.txt)" if Image is None else "no face to photograph")))
        start = next((t for t, i in film if i > 0.03 * top), None)
        end = next((t for t, i in film if i >= 0.97 * top), None)
        took = (end - start) if start is not None and end is not None else None
        want = (state.get("total") or 0) / 4000.0
        check("at about 4x: the drawing's own time over four, measured on the paint from its first ink to its last,"
              " and the player says 4",
              state.get("speed") == "4" and state.get("rate") == "4" and took is not None and want > 1.2
              and abs(took - want) <= 0.35 * want + 0.25,
              f"drawn {state.get('total')} ms, so {want:.2f} s at 4x; took {took}; rate {state.get('rate')}")
        check("once: it rests, finished (the same picture a second later, as much ink as the drawing's most), was"
              " fetched once and does not loop; it starts nothing else and nothing stops it",
              len(rest) == 2 and rest[0] == rest[1] and rest[0] >= 0.97 * top and state.get("state") == "paused"
              and state.get("looping") is False and state.get("at") == state.get("total") and len(fetched) == 1
              and state.get("ambient"),
              f"at rest {rest} (most {top}); {state}; fetched {len(fetched)}")
        still_ink = None
        rctx, rpg = browser_as(b, None, reduced=True)
        rfetched = []
        rpg.on("request", lambda r: rfetched.append(r.url) if r.url.split("?")[0].endswith(f"/api/skribls/{face}") else None)
        rpg.goto(BASE + "/social/@theo")
        rpg.wait_for_timeout(300)
        early = ink(shot(rpg, sel)) if Image is not None else None
        rpg.wait_for_timeout(2700)
        late = ink(shot(rpg, sel)) if Image is not None else None
        rcls = rpg.evaluate("() => { const f = document.querySelector('.prof-face .skribl-face'); return { cls: f && f.className,"
                            " draw: !!(f && f.querySelector('.skribl-inline')._skriblInline) }; }")
        close_ctx(rctx, rpg)
        still_ink = late
        check("under Reduce Motion it is the finished face from the first look, and still: nothing fetched, no player",
              early is not None and early == late and late >= 0.8 * top and not rfetched and not rcls["draw"],
              f"ink at 0.3 s {early}, at 3 s {late} (the drawn face's most {top}); fetched {len(rfetched)}; {rcls}")

    # ------------------------------------------------------------------ 4
    # ELSEWHERE, STILL. Since the map's step 3 the site's Gallery (Explore) is
    # its own, each tile with its maker's face from the site's face macro; a
    # Gallery card of Skribl's own, whose avatar gallery.js frames (faceOf),
    # is on Skribl's /gallery (and a profile's skribls and the first visit,
    # where a face plays or nobody is signed in). So each is read where it
    # stands: You in the bar and the Gallery's tile on the site's Gallery,
    # Skribl's card on /gallery; still, all three, and framed alike.
    if part(4, "elsewhere, still: the bar's You, the Gallery's tile and a Gallery card; the frame from sharecard.js; the empty circle"):
        theo = _people.get("theo") or member(b, "theo", "Theo Lind")
        face = person_row("theo")[3] or give_face(b, theo)
        mine = post_skribl(theo, "Theo's card " + secrets.token_hex(3))
        tc = theo.client()
        tc.get("/social/")
        pst, pj = tc.post_json("/social/posts", {"words": "Theo's tile", "payload": {
            "version": 2, "schemaVersion": 2, "playbackMode": "replay", "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": [{"x": 300 + k * 9, "y": 300, "color": "#7c5cff", "size": 8, "t": k * 40, "start": k == 0}
                                    for k in range(12)], "strokeGroups": [12], "background": {"color": "#f6f2ea"}}]}})
        tile_post = pj.get("post") if isinstance(pj, dict) else None
        ctx, pg = browser_as(b, theo)
        fetched = []
        pg.on("request", lambda r: fetched.append(r.url) if r.url.split("?")[0].endswith(f"/api/skribls/{face}") else None)
        card_sel = f'#galleryList > article.tile[data-id="{mine}"] .tavatar'
        tile_sel = f'.gal-tile[data-post="{tile_post}"] .gal-by .skribl-face'
        you_sel = "nav.nav .tab-you .skribl-face"
        # BOTH PICTURES COME BEFORE THEY ARE READ: the card brought into view
        # (its picture loads lazily), then each image loaded and decoded, and
        # whether they were is part of the row (a still face that never came
        # is a broken face, not a face standing still).
        painted, pics, where = {}, {}, {}
        for page_, sels in (("/gallery", [card_sel]), ("/social/explore", [tile_sel, you_sel])):
            pg.goto(BASE + page_)
            try:
                pg.wait_for_function("(s) => !!document.querySelector(s + ' img')", arg=sels[0], timeout=15000)
                pg.locator(sels[0]).first.scroll_into_view_if_needed(timeout=5000)
                pg.wait_for_function(PAINTED, arg=sels, timeout=15000)
                pg.evaluate(DECODED, sels)
            except Exception:
                pass
            pg.wait_for_timeout(500)
            painted[page_] = pg.evaluate(PAINTED, sels)
            first = [shot(pg, x) for x in sels]
            pg.wait_for_timeout(2500)
            pics[page_] = (first, [shot(pg, x) for x in sels])
            where[page_] = pg.evaluate("""(sels) => sels.map(s => { const e = document.querySelector(s), i = e && e.querySelector('img');
                return { src: i && i.getAttribute('src'), play: e && (e.getAttribute('data-play') || (e.closest('[data-play]') || {getAttribute: () => null}).getAttribute('data-play')),
                         players: document.querySelectorAll('.skribl-face-draw').length }; })""", sels)
        same = all(a and z and a == z for pg_ in pics for a, z in zip(*pics[pg_]))
        # SOMETHING DRAWN SHOWS, read off the paint. At this phone's one device
        # pixel to a CSS pixel the bar's 28px face and the card's 34px circle
        # read 36 and 34 inked samples here (Nov 11), and on main's run after
        # #847 (CI, sqlite 3/6) one read 30 or fewer: a line at 30 stood on the
        # measurement's own edge: with the bar's face 4px smaller (24), that
        # line went red in main's own words (the same paint True, inked
        # False). An empty or broken circle reads 0 (the face hidden, or its
        # picture never coming: red both), so the line is 10. The Gallery's
        # tile wears it at 22px: the same line.
        inks = [ink(x) if x else None for pg_ in pics for x in pics[pg_][1]]
        inked = Image is not None and all(v is not None and v > 10 for v in inks)
        srcs = [w["src"] for pg_ in where for w in where[pg_]]
        # What failed comes first in the detail: a run's summary keeps only
        # its first 300 characters (run_harness.sh).
        check("elsewhere the face is a picture, still: You in the bar, the Gallery's tile (the site's face macro) and a"
              " Gallery card's avatar of Skribl's (gallery.js) wear it (its own poster), with no player, no fetch of the"
              " drawing, and the same paint seconds later",
              bool(tile_post) and srcs == [f"/s/{face}/poster"] * 3 and where["/social/explore"][1]["play"] == "still"
              and where["/social/explore"][0]["play"] == "still"
              and all(w["players"] == 0 for pg_ in where for w in where[pg_]) and not fetched and same
              and all(painted.values()) and inked,
              f"ink card, tile, You {inks} (over 10); painted {painted}; the same paint {same}; fetched {len(fetched)};"
              f" srcs {srcs}; {where}")
        sizes = [(707, 707), (816, 612), (450, 800)]
        want = pg.evaluate(FRAME_JS, [SHARECARD, sizes])
        got = []
        for (w, h), exp in zip(sizes, want):
            db("update social_people set face_w = ?, face_h = ? where handle_key = 'theo'", (w, h), write=True)
            row = {}
            for page_, key, sel in (("/gallery", "card", card_sel), ("/social/explore", "tile", tile_sel),
                                    ("/social/explore", "you", you_sel)):
                if pg.url.split("?")[0] != BASE + page_:
                    pg.goto(BASE + page_)
                try:
                    pg.wait_for_function("(s) => !!document.querySelector(s + ' img')", arg=sel, timeout=15000)
                except Exception:
                    pass
                row[key] = pg.evaluate("""([s, k]) => { const e = document.querySelector(s); if (!e) return null;
                    return k === 'card' ? (e.querySelector('img') || { getAttribute: () => null }).getAttribute('style')
                                        : e.getAttribute('style'); }""", [sel, key])
            got.append(row)
            pg.goto("about:blank")
        db("update social_people set face_w = 707, face_h = 707 where handle_key = 'theo'", write=True)
        close_ctx(ctx, pg)
        rows = [(s_, e, frame_of(g["you"]), frame_of(g["tile"]), frame_of(g["card"])) for s_, e, g in zip(sizes, want, got)]
        check("its frame is the drawing's middle square in the share card, 3 card pixels in, by lib/sharecard.js"
              " drawingRect()'s own sums: in the face macro (You, and the Gallery's tile) and on Skribl's Gallery card,"
              " for a square, a 4:3 and a tall drawing",
              len(rows) == 3 and all(same_frame(m, e) and same_frame(t, e) and same_frame(c, e) for _, e, m, t, c in rows),
              "; ".join(f"{s_}: want {({k: round(v, 3) for k, v in e.items()})}, macro {m}, tile {t}, card {c}"
                        for s_, e, m, t, c in rows))
        juno = _people.get("juno") or member(b, "juno", "Juno Park")
        jcard = post_skribl(juno, "Juno's card " + secrets.token_hex(3))
        juno.pg.goto(BASE + "/social/@juno")
        juno.pg.wait_for_timeout(400)
        own = juno.pg.evaluate("""() => { const f = document.querySelector('.prof-face'), y = document.querySelector('nav.nav .tab-you .tab-ic');
            return { words: f && f.innerText.trim(), img: !!(f && f.querySelector('img')), svg: !!(f && f.querySelector('svg:not(.ic)')),
                     you: y && y.innerHTML.includes('face-blank'), youImg: !!(y && y.querySelector('img, svg')) }; }""")
        octx, opg = browser_as(b, theo)
        opg.goto(BASE + "/social/@juno")
        opg.wait_for_timeout(400)
        other = opg.evaluate("""() => { const f = document.querySelector('.prof-face');
            return { words: f && f.innerText.trim(), img: !!(f && f.querySelector('img, svg')), blank: !!(f && f.querySelector('.face-blank')) }; }""")
        opg.goto(BASE + "/gallery")
        try:
            opg.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"] .tavatar')",
                                  arg=jcard, timeout=15000)
        except Exception:
            pass
        jav = opg.evaluate("(id) => { const a = document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"] .tavatar');"
                           " return a ? { text: a.textContent.trim(), img: !!a.querySelector('img') } : null; }", jcard)
        close_ctx(octx, opg)
        check("before a face is drawn, an empty circle and never a stock silhouette: on your own profile it says Add"
              " your face, to anybody else it is empty, and You in the bar is an empty circle too; a Gallery card keeps"
              " Skribl's own initial",
              own["words"] == "Add your face" and not own["img"] and not own["svg"] and own["you"] and not own["youImg"]
              and other["words"] == "" and other["blank"] and not other["img"]
              and bool(jav) and jav["text"] == "J" and not jav["img"],
              f"own {own}; another's view {other}; her card {jav}")

    # ------------------------------------------------------------------ 5
    if part(5, "redraw my face replaces it: the old face deleted, the new one unlisted"):
        theo = _people.get("theo") or member(b, "theo", "Theo Lind")
        first = person_row("theo")[3] or give_face(b, theo)
        was = picture(first)
        sheet, landed = draw_face(theo, quick_face(), tempo=2.4, gaps=3.0)
        row = person_row("theo")
        second = row[3]
        post = post_row(second) if second else None
        gone_get = http(f"/api/skribls/{first}")[0]
        gone_card = picture(first)
        theo.pg.wait_for_timeout(500)
        now = theo.pg.evaluate("() => { const f = document.querySelector('.prof-face .skribl-face'); return f && f.getAttribute('data-skribl-id'); }")
        check("Change my face, then Draw a new one, draws a new one in the real Pad and keeps it: a new unlisted skribl on their row, the old"
              " one deleted (no row; its link 404s and its picture is Skribl's see-through blank), and the profile"
              " plays the new one",
              bool(first) and bool(second) and second != first and post is not None and post[0] == "unlisted"
              and post[1] == row[0] and not post_row(first) and gone_get == 404 and was in RASTER
              and gone_card == "image/svg+xml" and now == second,
              f"sheet {sheet}; landed {landed}; {first} -> {second}; new {post}; old GET {gone_get}, picture {was} ->"
              f" {gone_card}; profile plays {now}")

    # ------------------------------------------------------------------ 6
    if part(6, "Edit profile: CSRF, limits and character rules refused kindly; a good save shown; /you/face's guards"):
        rosa = member(b, "rosa", "Rosa Lima")
        pg = rosa.pg
        pg.goto(BASE + "/social/you/edit")
        pg.wait_for_timeout(300)
        form = pg.evaluate("""() => ({ name: (document.getElementById('editName') || {}).value, bio: (document.getElementById('editBio') || {}).value,
            sizes: ['editName', 'editBio'].map(id => { const e = document.getElementById(id); return e ? parseFloat(getComputedStyle(e).fontSize) : 0; }),
            cancel: (document.querySelector('a.btn[href$="/social/@rosa"]') || {}).textContent })""")
        pg.fill("#editName", "Rosa Lima-Reyes")
        pg.fill("#editBio", "Line one\n\n\n\nLine   two")
        with pg.expect_navigation(timeout=15000):
            pg.click("form[action$='/social/you/edit'] button[type=submit]")
        shown = pg.evaluate("() => ({ at: location.pathname + location.search, name: (document.querySelector('.prof-name') || {}).innerText,"
                            " bio: (document.querySelector('.prof-bio') || {}).innerText, note: (document.querySelector('.note') || {}).innerText })")
        check("Edit profile is a form with the name and bio as they are (16px or more); a good save goes back to the"
              " profile, which says so and shows them, the bio tidied (spaces and blank lines run together)",
              form["name"] == "Rosa Lima" and form["bio"] == "" and min(form["sizes"]) >= 16 and form["cancel"] == "Cancel"
              and shown["at"] == "/social/@rosa?note=saved" and shown["name"] == "Rosa Lima-Reyes"
              and shown["bio"] == "Line one\n\nLine two" and "Saved" in (shown["note"] or "")
              and person_row("rosa")[2] == "Line one\n\nLine two",
              f"{form}; {shown}; stored {person_row('rosa')[2]!r}")
        pg.goto(BASE + "/social/you/edit")
        pg.fill("#editName", "‮Rosa")
        pg.fill("#editBio", "one\ntwo\nthree\nfour\nfive")
        with pg.expect_navigation(timeout=15000):
            pg.click("form[action$='/social/you/edit'] button[type=submit]")
        kind = pg.evaluate("""() => ({ errs: [...document.querySelectorAll('.err')].map(e => e.textContent.trim()),
            invalid: [...document.querySelectorAll('[aria-invalid=true]')].map(e => e.id),
            name: (document.getElementById('editName') || {}).value, bio: ((document.getElementById('editBio') || {}).value || '').length })""")
        c = rosa.client()
        c.get("/social/you/edit")
        cases = {"empty name": {"name": "  ", "bio": ""}, "a name of 41": {"name": "R" * 41, "bio": ""},
                 "a zero-width space in the bio": {"name": "Rosa", "bio": "hi​there"},
                 "five lines": {"name": "Rosa", "bio": "a\nb\nc\nd\ne"}, "a bio of 161": {"name": "Rosa", "bio": "x" * 161},
                 "a bidi control in the bio": {"name": "Rosa", "bio": "evil ‮txt"}}
        answers = {}
        for k, f in cases.items():
            st, _, text = c.post_form("/social/you/edit", f)
            answers[k] = (st, [re.sub(r"\s+", " ", m).strip() for m in re.findall(r'<p class="err"[^>]*>(.*?)</p>', text, re.S)])
        want = {"empty name": "Add a name", "a name of 41": "40 characters at most",
                "a zero-width space in the bio": "a character we can’t show", "five lines": "more than 4 lines",
                "a bio of 161": "160 characters at most",
                "a bidi control in the bio": "a character we can’t show"}
        check("names and bios past their limits, or hiding a character nobody can see, are refused kindly: 400, said"
              " under the field (aria-invalid), what was typed kept, and nothing saved",
              len(kind["errs"]) == 2 and "a character we can’t show" in kind["errs"][0] and "more than 4 lines" in kind["errs"][1]
              and kind["invalid"] == ["editName", "editBio"] and kind["name"] == "‮Rosa" and kind["bio"] == 23
              and all(answers[k][0] == 400 and any(w in m for m in answers[k][1]) for k, w in want.items())
              and person_row("rosa")[1] == "Rosa Lima-Reyes" and person_row("rosa")[2] == "Line one\n\nLine two",
              f"in the page {kind}; sent {answers}")
        st_none, _, t_none = c.post_form("/social/you/edit", {"name": "Hijacked", "bio": ""}, token=False)
        c.origin = "https://evil.example"
        st_far, _, t_far = c.post_form("/social/you/edit", {"name": "Hijacked", "bio": ""})
        c.origin = BASE
        fj = c.post_json("/social/you/face", {"payload": {}}, token=False)
        c.origin = "https://evil.example"
        fo = c.post_json("/social/you/face", {"payload": {}})
        c.origin = BASE
        anon = Client()
        anon.get("/social/signin")
        fa = anon.post_json("/social/you/face", {"payload": {}})
        check("without this page's token, or from another origin, Edit profile and /you/face are refused (the kind"
              " page; 403 stale) and change nothing; signed out, /you/face is 401",
              st_none == 403 and "didn’t go through" in t_none and st_far == 403 and fj[0] == 403
              and fj[1] == {"error": "stale"} and fo[0] == 403 and fa[0] == 401
              and person_row("rosa")[1] == "Rosa Lima-Reyes" and person_row("rosa")[3] is None,
              f"edit: no token {st_none}, another origin {st_far}; face: no token {fj}, another origin {fo[0]}, signed out {fa}")
        odd = {"a list for a payload": c.post_json("/social/you/face", {"payload": [1, 2]}),
               "no payload": c.post_json("/social/you/face", {"nothing": True}),
               "not JSON": (c._req("POST", "/social/you/face",
                                   headers={"X-Social-CSRF": c.token, "Content-Type": "application/json"})[0], None),
               "a drawing Skribl refuses": c.post_json("/social/you/face", {"payload": {"frames": "nope"}})}
        got = {k: (v[0], (v[1].get("error") if isinstance(v[1], dict) else None)) for k, v in odd.items()}
        check("whatever /you/face is sent is answered, never a 500: no face in it, 400; a drawing Skribl refuses, 400"
              " with Skribl's own words; nothing kept, no skribl made",
              got["a list for a payload"] == (400, "no_face") and got["no payload"] == (400, "no_face")
              and got["not JSON"][0] == 400 and got["a drawing Skribl refuses"] == (400, "rejected")
              and isinstance(odd["a drawing Skribl refuses"][1], dict) and odd["a drawing Skribl refuses"][1].get("message")
              and person_row("rosa")[3] is None
              and db("select count(*) from skribl_posts where user_id = ?", (person_row("rosa")[0],))[0][0] == 0,
              str(got))
        lim = member(b, "lena", "Lena Berg")
        lc = lim.client()
        lc.get("/social/you/edit")
        edits = [lc.post_form("/social/you/edit", {"name": "Lena Berg", "bio": f"try {i}"})[0] for i in range(61)]
        held_text = lc.post_form("/social/you/edit", {"name": "Lena Berg", "bio": "again"})[2]
        faces = [lc.post_json("/social/you/face", {"payload": {"frames": "nope"}})[0] for i in range(21)]
        check("past its limit, per person, the edit is a kind 429 page (60 an hour), and a face 429 (20 an hour,"
              " every try counted, kept or not)",
              edits[:60] == [303] * 60 and edits[60] == 429 and "Wait a little" in held_text
              and faces[:20] == [400] * 20 and faces[20] == 429,
              f"edits {edits[55:]}; faces {faces[15:]}")

    # ------------------------------------------------------------------ 7
    if part(7, "a Gallery card's name links to the profile; the listing's public-only filter"):
        mira = _people.get("mira") or member(b, "mira", "Mira Okafor")
        theo = _people.get("theo") or member(b, "theo", "Theo Lind")
        face = person_row("theo")[3] or give_face(b, theo)
        tag = secrets.token_hex(3)
        hers = post_skribl(mira, "Mira's card " + tag)
        his = post_skribl(theo, "Theo's card " + tag)
        mine_hidden = post_skribl(mira, "Mira's link-only " + tag, visibility=None)
        # A Gallery card of Skribl's with everybody's in it, on the site: the first
        # visit's (Explore's were until the map's step 3), signed out.
        ctx, pg = browser_as(b, None, "desk")
        pg.goto(BASE + "/social/")
        try:
            pg.wait_for_function("(id) => !!document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"]')",
                                 arg=his, timeout=15000)
        except Exception:
            pass
        link = pg.evaluate("(id) => { const a = document.querySelector('#galleryList > article.tile[data-id=\"' + id + '\"] .tauth');"
                           " return a ? { tag: a.tagName, href: a.getAttribute('href') } : null; }", his)
        try:
            with pg.expect_navigation(timeout=15000):
                pg.click(f'#galleryList > article.tile[data-id="{his}"] .tauth')
            went = pg.evaluate("() => ({ at: location.pathname, name: (document.querySelector('.prof-name') || {}).innerText })")
        except Exception as exc:
            went = {"could not": str(exc).splitlines()[0][:100]}
        close_ctx(ctx, pg)
        items = {i["id"]: i for i in (listing() or [])}
        a_his, a_hers = (items.get(his) or {}).get("author") or {}, (items.get(hers) or {}).get("author") or {}
        check("a Gallery card's name is a link to the person's profile, and lands there: the author resolver says"
              " their url (and their face, once drawn)",
              bool(link) and link["tag"] == "A" and link["href"].endswith("/social/@theo")
              and went.get("at") == "/social/@theo" and went.get("name") == "Theo Lind"
              and a_his.get("url") == "/social/@theo" and a_his.get("face", {}).get("id") == face
              and a_hers.get("url") == "/social/@mira" and "face" not in a_hers,
              f"link {link}; went {went}; authors {a_his} / {a_hers}")
        mid = person_row("mira")[0]
        q = "&user_id=" + urllib.parse.quote(mid)
        mpg = mira.ctx.request
        own_all = mpg.get(BASE + "/api/skribls?limit=100" + q).json().get("items", [])
        own_pub = mpg.get(BASE + "/api/skribls?limit=100" + q + "&visibility=public").json().get("items", [])
        bad = mpg.get(BASE + "/api/skribls?limit=100" + q + "&visibility=unlisted")
        plain = [i["id"] for i in (listing("&visibility=public") or [])]
        check("the listing's visibility=public narrows an author's own listing to what anyone is shown (their"
              " link-only skribl out), takes no other value (400), and leaves the public listing as it was",
              any(i["id"] == mine_hidden for i in own_all) and not any(i["id"] == mine_hidden for i in own_pub)
              and any(i["id"] == hers for i in own_pub) and all(i["visibility"] == "public" for i in own_pub)
              and bad.status == 400 and plain == [i["id"] for i in (listing() or [])],
              f"own {len(own_all)}, public {len(own_pub)}; unlisted asked {bad.status}")

    # ------------------------------------------------------------------ 8
    if part(8, "the new screens: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        theo = _people.get("theo") or member(b, "theo", "Theo Lind")
        if not person_row("theo")[3]:
            give_face(b, theo)
        juno = _people.get("juno") or member(b, "juno", "Juno Park")
        looks = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                for who, path, label, prep in (
                        (theo, "/social/@theo?note=face", "own, a face", None),
                        (juno, "/social/@juno", "own, none", None),
                        (theo, "/social/@juno", "another's, none", None),
                        (juno, "/social/@theo", "another's, a face", None),
                        (theo, "/social/you/edit", "edit, its messages showing", "edit"),
                        (None, "/social/@nobody_here", "nobody", None),
                        (theo, "/social/you", "settings", None)):
                    ctx, pg = browser_as(b, who, screen, scheme, reduced=True)
                    pg.goto(BASE + path)
                    pg.wait_for_timeout(500)
                    if prep == "edit":
                        pg.fill("#editName", "")
                        pg.fill("#editBio", "a\nb\nc\nd\ne")
                        try:
                            with pg.expect_navigation(timeout=15000):
                                pg.click("form[action$='/social/you/edit'] button[type=submit]")
                        except Exception:
                            pass
                        pg.wait_for_timeout(300)
                    looks[(screen, scheme, label)] = pg.evaluate(READ)
                    close_ctx(ctx, pg)
        low = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["low"]]
        reads = sum(v["read"] for v in looks.values())
        lowest = min(((v["lowest"], " ".join(k)) for k, v in looks.items()), default=(0, "nothing"))
        check("every word on a profile (yours with a face and with none, somebody else's), Edit profile with its"
              " messages showing, the kind 404 and Settings reads at 4.5:1 or more on what is painted behind it",
              reads >= 300 and not low, f"{reads} read, the lowest {lowest}; under 4.5: {low[:5]}")
        small = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["small"]]
        check("every link, button and field on them is 44px or more each way (phone and desk)", not small,
              "; ".join(small[:6]))
        fields = [f"{k[0]} {k[2]}: {x}" for k, v in looks.items() for x in v["fields"]]
        check("every text field on them is 16px or more, so a phone never magnifies the page on a tap",
              not fields and any(k[2].startswith("edit") for k in looks), "; ".join(fields[:6]))

    # ------------------------------------------------------------------ 9
    if part(9, "delete my account takes the face with it, and the bio with the row"):
        zoe = member(b, "zoe", "Zoe Park")
        zc = zoe.client()
        zc.get("/social/you/edit")
        zc.post_form("/social/you/edit", {"name": "Zoe Park", "bio": "Here for the cats."})
        face = give_face(b, zoe)
        kept = post_skribl(zoe, "Zoe's own " + secrets.token_hex(3))
        zid = person_row("zoe")[0]
        before_pic = picture(face) if face else None
        zoe.pg.goto(BASE + "/social/you/delete")
        says = zoe.pg.evaluate("() => document.querySelector('main').innerText.replace(/\\s+/g, ' ')")
        zoe.pg.fill("#delConfirm", "@zoe")
        try:
            with zoe.pg.expect_navigation(timeout=15000):
                zoe.pg.click("form[action$='/social/you/delete'] button[type=submit]")
        except Exception:
            pass
        st_face, st_poster, st_prof = http(f"/api/skribls/{face}")[0], picture(face), http("/social/@zoe")[0]
        check("the delete confirm says the profile and the face drawn for it go; deleting takes the face skribl with it"
              " (Skribl's delete_post: no row, its link a 404, its picture Skribl's see-through blank), the bio with the"
              " person's row, and the profile is the kind 404; their other skribls stay, as the page says",
              "Your profile, and the face you drew for it" in says and bool(face) and before_pic in RASTER and person_row("zoe") is None
              and not post_row(face) and st_face == 404 and st_poster == "image/svg+xml" and st_prof == 404
              and post_row(kept) is not None and not db("select id from social_people where bio = ?", ("Here for the cats.",)),
              f"face {face}: GET {st_face}, picture {before_pic} -> {st_poster}; profile {st_prof}; person {person_row('zoe')};"
              f" their other skribl {post_row(kept)}; {zid}")

    # ------------------------------------------------------------------ 10
    # ------------------------------------------------------------------ 11
    if part(11, "a face from a skribl you made: Your face's doors, the picker, the circle, a face of its own"):
        nell = member(b, "nell", "Nell Quist")
        junx = _people.get("juno") or member(b, "juno", "Juno Park")

        def post_body(who, body):
            ctx = who.ctx
            ctx.request.get(BASE + "/api/skribls?limit=1")
            tok = next((c["value"] for c in ctx.cookies(BASE) if c["name"] == "skribl_csrf"), "")
            r = ctx.request.post(BASE + "/api/skribls", data=json.dumps(body),
                                 headers={"Content-Type": "application/json", "X-Skribl-CSRF": tok})
            return r.json().get("id") if r.ok else f"refused {r.status} {r.text()[:120]}"

        tag = secrets.token_hex(3)
        older = post_skribl(nell, f"Nell's older {tag}")
        linkonly = post_skribl(nell, f"Nell's link-only {tag}", visibility=None)
        flipbody = {"title": f"Nell's flip {tag}", "caption": "", "version": 2, "schemaVersion": 2,
                    "playbackMode": "flip", "fps": 12, "visibility": "public",
                    "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                    "frames": [{"strokes": [{"x": 100 + i * 9, "y": 300, "color": "#7c5cff", "size": 8, "t": i * 30,
                                             "start": i == 0} for i in range(12)], "strokeGroups": [12],
                                "background": {"color": "#f6f2ea"}} for _ in range(2)]}
        flipped = post_body(nell, flipbody)
        newer = post_skribl(nell, f"Nell's newer {tag}")
        theirs = post_skribl(junx, f"Juno's {tag}")
        pg = nell.pg
        pg.goto(BASE + "/social/@nell")
        pg.wait_for_timeout(400)

        SHEETSTATE = """() => { const w = document.getElementById('faceSheet'), s = w && w.querySelector('.make-sheet');
            const vis = [...w.querySelectorAll('.face-step')].filter(x => !x.hidden).map(x => x.getAttribute('data-step'));
            const r = s.getBoundingClientRect(), a = document.activeElement;
            return { hidden: w.hidden, open: w.classList.contains('is-open'), step: vis.join(','), top: Math.round(r.top * 10) / 10,
                     height: Math.round(r.height), role: s.getAttribute('role'), modal: s.getAttribute('aria-modal'),
                     inert: ['body > .top', 'body > .nav', '#main'].map(q => { const e = document.querySelector(q); return !!e && e.hasAttribute('inert'); }),
                     doors: [...w.querySelectorAll('.face-step[data-step=doors] .make-words b')].map(e => e.textContent.trim()),
                     button: (document.querySelector('button[data-face-sheet]') || {}).textContent.trim(),
                     focus: a ? (a.closest('.make-door') ? 'door:' + a.textContent.trim().slice(0, 16) : a.tagName + (a.getAttribute('data-face-sheet') !== null ? '[face-sheet]' : '')) : null,
                     say: [...w.querySelectorAll('[data-face-say]')].filter(x => !x.hidden).map(x => x.textContent.trim()) }; }"""
        RISE = """(ms) => new Promise(res => { const s = document.querySelector('#faceSheet .make-sheet'), out = [];
            const t0 = performance.now(); document.querySelector('button[data-face-sheet]').click();
            (function f() { out.push(Math.round(s.getBoundingClientRect().top * 10) / 10);
              if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""
        before = pg.evaluate(SHEETSTATE)
        rise = pg.evaluate(RISE, 700)
        opened = pg.evaluate(SHEETSTATE)
        rsteps = [z - a for a, z in zip(rise, rise[1:])]
        rtravel = abs(rise[0] - opened["top"]) if rise else 0
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(600)
        gone = pg.evaluate(SHEETSTATE)
        check("Add your face raises Your face, Make's own sheet: it glides up from below the screen on many frames, one"
              " way; a modal dialog, the page behind inert, focus on its first door; before a face, Draw your face"
              " leads, then Trace a photo and Use one you made; Esc puts it away and focus comes back to the button",
              before["hidden"] and before["button"] == "Add your face"
              and opened["open"] and opened["step"] == "doors" and opened["role"] == "dialog" and opened["modal"] == "true"
              and all(opened["inert"]) and opened["doors"] == ["Draw your face", "Trace a photo", "Use one you made"]
              and (opened["focus"] or "").startswith("door:Draw your face")
              and rise and rise[0] >= 860 and len(set(rise)) >= 8 and all(x <= 0 for x in rsteps)
              and max((abs(x) for x in rsteps), default=0) <= 0.3 * rtravel
              and gone["hidden"] and not any(gone["inert"]) and gone["focus"] == "BUTTON[face-sheet]",
              f"before {before}; opened {opened}; rise from {rise[:1]} to {rise[-1:]} on {len(set(rise))} positions,"
              f" biggest step {max((abs(x) for x in rsteps), default=0):.1f} of {rtravel}; after Esc {gone}")

        # PICK: the step's height glides; the list is theirs, Pad drawings only.
        open_face_sheet(pg)
        GROW = """(ms) => new Promise(res => { const s = document.querySelector('#faceSheet .make-sheet'), out = [];
            const t0 = performance.now(); document.querySelector('#faceSheet [data-face-go=pick]').click();
            (function f() { out.push([Math.round(s.getBoundingClientRect().height), performance.now() - t0]);
              if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""
        grown = pg.evaluate(GROW, 1000)
        grow, grow_t = [h for h, _ in grown], [t for _, t in grown]
        try:
            pg.wait_for_function("() => document.querySelectorAll('#faceSheet .face-tile').length > 0", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(300)
        tiles = pg.evaluate("""() => [...document.querySelectorAll('#faceSheet .face-tile')].map(t => {
            const i = t.querySelector('img'); return { title: t.querySelector('b').textContent, src: i ? i.getAttribute('src') : null,
            style: i ? i.getAttribute('style') : null }; })""")
        gsteps = [z - a for a, z in zip(grow, grow[1:])]
        gtravel = abs(grow[-1] - grow[0]) if grow else 0
        # JUDGED FAIRLY (main's run after #889 read this red on a busy runner):
        # a step is judged over the display frames it spans, so a frame the
        # browser dropped is not read as a jump; and the change must take a
        # glide's time (150ms or more from its first frame to its last), so a
        # snap is a snap however the frames fell.
        _moves = [(a, b, ta, tb) for (a, ta), (b, tb) in zip(zip(grow, grow_t), zip(grow[1:], grow_t[1:])) if b != a]
        gbig = max((abs(b - a) / max(1.0, round((tb - ta) / (1000 / 60))) for a, b, ta, tb in _moves), default=0)
        gspan = (_moves[-1][3] - _moves[0][2]) if _moves else 0
        titles = [t["title"] for t in tiles]
        check("Use one you made glides the sheet to its new height (read every frame: one way, never a jump) and lists"
              " their own skribls, newest first, the link-only one too: Pad drawings only, never a Flip, never somebody"
              " else's; each tile is the drawing cut from its own card",
              grow and gtravel > 40 and all(x >= 0 for x in gsteps)
              and gbig <= 0.45 * gtravel and gspan >= 150
              and titles == [f"Nell's newer {tag}", f"Nell's link-only {tag}", f"Nell's older {tag}"]
              and all(t["src"] and t["src"].endswith("/poster") for t in tiles),
              f"heights {grow[:1]} to {grow[-1:]} on {len(set(grow))} values over {round(gspan)}ms, biggest step a frame"
              f" {round(gbig, 1)} of {gtravel}; tiles {titles}; flip {flipped}; Juno's {theirs}")

        # PLACE: pick the newest; it starts on its middle square, painted whole.
        pg.click(f"#faceSheet .face-tile:has-text(\"Nell's newer {tag}\")", timeout=5000)
        try:
            pg.wait_for_function("() => !document.querySelector('#faceSheet [data-step=place]').hidden", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(500)
        GEOM = """() => { const st = document.querySelector('#faceSheet [data-face-stage]'), a = document.querySelector('#faceSheet [data-face-art]');
            const c = a.querySelector('canvas'), S = st.clientWidth;
            let ink = 0; try { const x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
              for (let i = 0; i < x.length; i += 16) if (x[i + 3] > 0 && Math.abs(x[i] - 246) + Math.abs(x[i + 1] - 242) + Math.abs(x[i + 2] - 234) > 90) ink++; } catch (e) { ink = -1; }
            return { S, left: parseFloat(a.style.left), top: parseFloat(a.style.top), w: parseFloat(a.style.width), h: parseFloat(a.style.height),
                     slider: +document.querySelector('[data-face-size]').value, text: document.querySelector('[data-face-size]').getAttribute('aria-valuetext'), ink }; }"""

        def square(g, W=816, H=612):
            """The square of the drawing the circle shows, read back off the stage."""
            D, m = g["S"] * 0.88, g["S"] * 0.06
            k = g["w"] / W
            return {"x": (m - g["left"]) / k, "y": (m - g["top"]) / k, "side": D / k}
        g0 = pg.evaluate(GEOM)
        s0 = square(g0)
        st = pg.locator("#faceSheet [data-face-stage]").bounding_box()
        cx, cy = st["x"] + st["width"] / 2, st["y"] + st["height"] / 2
        pg.mouse.move(cx, cy)
        pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(cx + 5 * i, cy + 2.5 * i)
        pg.mouse.up()
        g1 = pg.evaluate(GEOM)
        s1 = square(g1)
        pg.focus("#faceSheet [data-face-stage]")
        pg.keyboard.press("ArrowLeft")
        g2 = pg.evaluate(GEOM)
        pg.evaluate("() => { const r = document.querySelector('[data-face-size]'); r.value = '800'; r.dispatchEvent(new Event('input', { bubbles: true })); }")
        g3 = pg.evaluate(GEOM)
        s3 = square(g3)
        check("picking one places it in the circle, painted whole by Skribl's engine and starting on its middle square;"
              " a drag moves it with the hand, the arrow keys move it, and the slider sizes it about its middle",
              abs(s0["x"] - 102) < 0.5 and abs(s0["y"]) < 0.5 and abs(s0["side"] - 612) < 0.5 and g0["ink"] > 20
              and abs((g1["left"] - g0["left"]) - 40) < 1 and abs((g1["top"] - g0["top"]) - 20) < 1
              and abs((g2["left"] - g1["left"]) + 8) < 0.6 and abs(g2["top"] - g1["top"]) < 0.01
              and s3["side"] < s1["side"] * 0.75
              and abs((s3["x"] + s3["side"] / 2) - (square(g2)["x"] + square(g2)["side"] / 2)) < 0.5,
              f"start {s0} ink {g0['ink']}; dragged {s1}; arrow {square(g2)}; sized {s3} ({g3['text']})")

        # USE THIS FACE: a face of its own, the drawing it came from untouched.
        orig_before = db("select payload_json from skribl_posts where public_id = ?", (newer,))[0][0]
        with pg.expect_navigation(timeout=30000):
            pg.click("#faceSheet [data-face-use]", timeout=5000)
        pg.wait_for_timeout(400)
        row = person_row("nell")
        face = row[3] if row else None
        frow = post_row(face) if face else None
        fpay = json.loads(db("select payload_json from skribl_posts where public_id = ?", (face,))[0][0]) if face else {}
        opay = json.loads(orig_before)
        orig_after = db("select payload_json from skribl_posts where public_id = ?", (newer,))[0][0]
        fp, op = (fpay.get("frames") or [{}])[0].get("strokes", [{}])[0], opay["frames"][0]["strokes"][0]
        want = {"x": (op["x"] - s3["x"]) * 707 / s3["side"], "y": (op["y"] - s3["y"]) * 707 / s3["side"],
                "size": op["size"] * 707 / s3["side"]}
        check("Use this face keeps a face of its own: one new skribl, unlisted, theirs, 707 square, its card made (a"
              " picture, not the see-through blank), on their row; its points the drawing's, moved and sized into the"
              " placed square; the drawing it came from byte for byte as it was",
              bool(face) and face != newer and frow is not None and frow[0] == "unlisted" and frow[1] == row[0]
              and (frow[3], frow[4]) == (707, 707) and tuple(row[4:6]) == (707, 707) and picture(face) in RASTER
              and len(fpay["frames"][0]["strokes"]) == len(opay["frames"][0]["strokes"])
              and all(abs(fp[k] - want[k]) < 0.06 for k in ("x", "y", "size"))
              and orig_after == orig_before and pg.url.endswith("/social/@nell?note=face"),
              f"face {face} row {row}; post {frow}; card {picture(face) if face else None}; first point {fp} want"
              f" {want}; original unchanged {orig_after == orig_before}; at {pg.url}")

        # THE PROFILE'S OWN CIRCLE, UNTOUCHED BY THE SHEET'S STYLES. A rule the
        # sheet wrote under the profile's own class name (.face-ring) once drew
        # the profile's face as an oval across the page: caught in the
        # pictures, not by a row, so this row reads the circle itself.
        ring = pg.evaluate("""() => { const box = q => { const e = document.querySelector(q); if (!e) return null;
              const b = e.getBoundingClientRect(); return { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10,
              cx: Math.round((b.left + b.width / 2) * 10) / 10, cy: Math.round((b.top + b.height / 2) * 10) / 10 }; };
            return { prof: box('.prof-face'), face: box('.prof-face .skribl-face'), you: box('nav.nav .tab-you .face-ring') }; }""")
        pf, ff, yf = ring["prof"], ring["face"], ring["you"]
        check("the profile's own circle is untouched by the sheet's styles: on a phone its face sits in a 112px circle,"
              " round and centred on it, and You's in the bar is a 28px one",
              bool(pf and ff and yf) and (pf["w"], pf["h"]) == (112, 112) and abs(ff["w"] - ff["h"]) < 0.5
              and 96 <= ff["w"] <= 112 and abs(ff["cx"] - pf["cx"]) < 1 and abs(ff["cy"] - pf["cy"]) < 1
              and (yf["w"], yf["h"]) == (28, 28), json.dumps(ring))

        # ITS FACE NEVER AMONG THEM, and Change my face now.
        open_face_sheet(pg)
        pg.click("#faceSheet [data-face-go=pick]")
        try:
            pg.wait_for_function("() => document.querySelectorAll('#faceSheet .face-tile').length > 0", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(300)
        again = pg.evaluate("() => [...document.querySelectorAll('#faceSheet .face-tile b')].map(b => b.textContent)")
        label = pg.evaluate("() => document.querySelector('button[data-face-sheet]').textContent.trim()")

        # OPEN A FILE: a Flip and a drawing with a picture under it are said
        # kindly and the picker stays; a .skribl file is placed and kept.
        tmp = Path(tempfile.mkdtemp())
        skull = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "skull.json").read_text(encoding="utf-8"))
        skull["title"] = "Skull in a hat"
        (tmp / "skull.skribl").write_text(json.dumps(skull), encoding="utf-8")
        flipfile = dict(flipbody)
        (tmp / "flip.skribl").write_text(json.dumps(flipfile), encoding="utf-8")
        photo = json.loads(json.dumps(skull))
        photo["frames"][0]["photo"] = {"data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
                                       "fit": "cover", "opacity": 1, "blur": 0, "offset": {"x": 0.5, "y": 0.5}, "zoom": 1}
        (tmp / "photo.skribl").write_text(json.dumps(photo), encoding="utf-8")
        said = {}

        def open_file(name):
            if pg.evaluate(SHEETSTATE)["step"] == "place":
                pg.click("#faceSheet [data-step=place] [data-face-go=pick]", timeout=5000)
                pg.wait_for_timeout(500)
            with pg.expect_file_chooser(timeout=8000) as fc:
                pg.click("#faceSheet [data-face-file]", timeout=5000)
            fc.value.set_files(str(tmp / f"{name}.skribl"))
            pg.wait_for_timeout(700)
            return pg.evaluate(SHEETSTATE)
        for name in ("flip", "photo"):
            try:
                said[name] = open_file(name)
            except Exception as exc:
                said[name] = {"step": f"could not: {str(exc).splitlines()[0][:80]}", "say": []}
        try:
            placed_skull = open_file("skull")
            with pg.expect_navigation(timeout=30000):
                pg.click("#faceSheet [data-face-use]", timeout=5000)
        except Exception as exc:
            placed_skull = {"step": f"could not: {str(exc).splitlines()[0][:80]}"}
        pg.wait_for_timeout(400)
        row2 = person_row("nell")
        face2 = row2[3] if row2 else None
        check("its own face is never among the ones to pick, and the button says Change my face; Open a file...: a"
              " Flip's file and a drawing with a picture under it are said kindly where they were picked, and the"
              " picker stays; a .skribl file is placed and kept as a face of its own, the old face gone",
              face and f"Nell's flip {tag}" not in again and len(again) == 3 and label == "Change my face"
              and said["flip"]["step"] == "pick" and any("That one’s a Flip" in x for x in said["flip"]["say"])
              and said["photo"]["step"] == "pick" and any("picture under it" in x for x in said["photo"]["say"])
              and placed_skull["step"] == "place"
              and bool(face2) and face2 != face and post_row(face2) is not None and post_row(face2)[3] == 707
              and post_row(face) is None and picture(face2) in RASTER,
              f"listed again {again}; button {label}; flip {said['flip']['step']} {said['flip']['say']};"
              f" photo {said['photo']['step']} {said['photo']['say']}; skull {placed_skull['step']}; faces {face} -> {face2}")

        # THE SHEET'S OWN WORDS AND TARGETS, every step, as a profile's are
        # (section 8): phone and desk, light and dark.
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, nell, screen, scheme, reduced=True)
                cpg.goto(BASE + "/social/@nell")
                cpg.wait_for_timeout(400)
                open_face_sheet(cpg, 700)
                seen[(screen, scheme, "doors")] = cpg.evaluate(READ, "#faceSheet")
                cpg.click("#faceSheet [data-face-go=pick]")
                try:
                    cpg.wait_for_function("() => document.querySelectorAll('#faceSheet .face-tile').length > 0", timeout=15000)
                except Exception:
                    pass
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "pick")] = cpg.evaluate(READ, "#faceSheet")
                cpg.click("#faceSheet .face-tile >> nth=0")
                try:
                    cpg.wait_for_function("() => !document.querySelector('#faceSheet [data-step=place]').hidden", timeout=15000)
                except Exception:
                    pass
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "place")] = cpg.evaluate(READ, "#faceSheet")
                close_ctx(ctx, cpg)
        low = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["low"]]
        small = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["small"]]
        fields = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["fields"]]
        reads = sum(v["read"] for v in seen.values())
        lowest = min(((v["lowest"], " ".join(k)) for k, v in seen.items()), default=(0, "nothing"))
        check("Your face's every word, at every step, reads at 4.5:1 or more on what is painted behind it, every"
              " button, tile and the slider is 44px or more each way, and it has no text field to magnify a phone:"
              " phone and desk, light and dark",
              reads >= 60 and not low and not small and not fields,
              f"{reads} read, the lowest {lowest}; under 4.5: {low[:4]}; small: {small[:4]}; fields: {fields[:3]}")

        # THE BLANK A TAKE BEGAN ON IS NO PICTURE (after v330: "Use one you
        # made" refused every drawing made in the Pad, as "a picture under
        # it"). The Pad keeps the canvas its first take began on under the
        # drawing (its frame's baseSnapshot), and on a fresh Pad that canvas
        # is see-through. Such a drawing is placed like any other and its face
        # keeps no base; a base with ink on it is still a picture.
        def base_png(dot):
            if Image is None:
                return None
            im = Image.new("RGBA", (816, 612), (0, 0, 0, 0))
            if dot:
                for x in range(404, 412):
                    for y in range(302, 310):
                        im.putpixel((x, y), (30, 30, 30, 255))
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        inked = post_skribl(nell, f"Nell's on a picture {tag}", base=base_png(True))
        padmade = post_skribl(nell, f"Nell's from the Pad {tag}", base=base_png(False))
        pg.goto(BASE + "/social/@nell")
        pg.wait_for_timeout(400)
        open_face_sheet(pg)
        pg.click("#faceSheet [data-face-go=pick]")
        try:
            pg.wait_for_function("() => document.querySelectorAll('#faceSheet .face-tile').length > 1", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(300)
        on_ink = on_pad = None
        face3, fpay3, g3b = None, {}, {}
        try:
            pg.click(f"#faceSheet .face-tile:has-text(\"Nell's on a picture {tag}\")", timeout=5000)
            try:
                pg.wait_for_function("""() => [...document.querySelectorAll('#faceSheet [data-step=pick] [data-face-say]')]
                    .some(s => !s.hidden && s.textContent.indexOf('picture under it') >= 0)""", timeout=10000)
            except Exception:
                pass
            on_ink = pg.evaluate(SHEETSTATE)
            pg.click(f"#faceSheet .face-tile:has-text(\"Nell's from the Pad {tag}\")", timeout=5000)
            try:
                pg.wait_for_function("() => !document.querySelector('#faceSheet [data-step=place]').hidden", timeout=15000)
            except Exception:
                pass
            pg.wait_for_timeout(500)
            on_pad = pg.evaluate(SHEETSTATE)
            g3b = pg.evaluate(GEOM)
            if on_pad["step"] == "place":
                with pg.expect_navigation(timeout=30000):
                    pg.click("#faceSheet [data-face-use]", timeout=5000)
                pg.wait_for_timeout(400)
                row3 = person_row("nell")
                face3 = row3[3] if row3 and row3[3] != face2 else None
                fpay3 = json.loads(db("select payload_json from skribl_posts where public_id = ?", (face3,))[0][0]) if face3 else {}
        except Exception as exc:
            on_pad = on_pad or {"step": f"could not: {str(exc).splitlines()[0][:90]}", "say": []}
        f3 = (fpay3.get("frames") or [{}])[0]
        check("a drawing made in the Pad, the see-through canvas its first take began on under it, is placed in the"
              " circle like any other, painted whole, and kept as a face with no base and every point; a drawing on"
              " a base with ink on it is still said kindly to have a picture under it, and the picker stays",
              bool(inked and padmade) and on_ink is not None and on_ink["step"] == "pick"
              and any("picture under it" in x for x in on_ink["say"])
              and on_pad is not None and on_pad["step"] == "place" and not on_pad["say"] and g3b.get("ink", 0) > 20
              and bool(face3) and not f3.get("baseSnapshot") and not fpay3.get("baseSnapshot")
              and len(f3.get("strokes") or []) == 60 and post_row(face3) is not None and post_row(face3)[3] == 707,
              f"posted {inked} {padmade}; on the inked base {on_ink and (on_ink['step'], on_ink['say'])};"
              f" on the Pad's blank {on_pad and (on_pad['step'], on_pad['say'])} ink {g3b.get('ink')};"
              f" face {face2} -> {face3}, its base {bool(f3.get('baseSnapshot') or fpay3.get('baseSnapshot'))},"
              f" {len(f3.get('strokes') or [])} points")

    # ------------------------------------------------------------------ 12
    if part(12, "trace a photo: the third door, the photo under the canvas as a guide, the lines alone kept"):
        tess = member(b, "tess", "Tess Moreau")
        pg = tess.pg
        tmp = Path(tempfile.mkdtemp())
        # A PHOTO TO TRACE, made here: a bright green ground (a colour no ink,
        # paper or purple is, so a photo that reached the card would be seen
        # on it) with a dark round in the middle, where the empty canvas's
        # words sit: the hardest ground they will have (dark hair, a dark room).
        snap = Image.new("RGB", (600, 600), (40, 200, 80))
        from PIL import ImageDraw as _Draw
        _Draw.Draw(snap).ellipse((130, 150, 470, 450), fill=(20, 20, 20))
        snap.save(tmp / "IMG_0412.jpg", quality=92)
        (tmp / "notes.txt").write_text("not a photo", encoding="utf-8")

        DOORS = """() => { const s = document.querySelector('#faceSheet [data-step=doors]');
          const d = [...s.querySelectorAll('.make-door')].map(b => ({ title: b.querySelector('b').textContent,
            words: b.querySelector('.make-words > span').textContent, trace: b.hasAttribute('data-face-trace'),
            h: Math.round(b.getBoundingClientRect().height), w: Math.round(b.getBoundingClientRect().width) }));
          const i = s.querySelector('[data-face-photo]'), say = s.querySelector('[data-face-say]');
          return { doors: d, accept: i ? i.getAttribute('accept') : null, multiple: i ? i.multiple : null,
                   say: say && !say.hidden ? say.textContent : '',
                   open: document.getElementById('faceSheet').classList.contains('is-open') }; }"""
        pg.goto(BASE + "/social/@tess")
        pg.wait_for_timeout(400)
        open_face_sheet(pg, 700)
        doors = pg.evaluate(DOORS)
        try:
            with pg.expect_file_chooser(timeout=8000) as fc:
                pg.click("#faceSheet [data-face-trace]", timeout=5000)
            chooser = {"multiple": fc.value.is_multiple()}
            fc.value.set_files(str(tmp / "notes.txt"))
            pg.wait_for_timeout(700)
        except Exception as exc:
            chooser = {"could not": str(exc).splitlines()[0][:100]}
        after_txt = pg.evaluate(DOORS)
        titles = [d["title"] for d in doors["doors"]]
        tr = next((d for d in doors["doors"] if d["trace"]), {})
        check("Your face has Trace a photo between Draw your face and Use one you made, saying what it does to a"
              " screen reader; it opens the device's own picker, for one photo of the kinds the Pad takes; a file"
              " that is not a photo is said kindly, and the sheet stays",
              titles == ["Draw your face", "Trace a photo", "Use one you made"]
              and tr.get("words") == "Draw over a photo. Only your lines are kept." and tr.get("h", 0) >= 44
              and doors["accept"] == "image/jpeg,image/png,image/gif,image/webp" and chooser.get("multiple") is False
              and after_txt["open"] and "isn’t a photo the Pad can use" in after_txt["say"],
              f"doors {titles}; trace {tr}; accept {doors['accept']}; chooser {chooser};"
              f" after a text file: open {after_txt['open']}, said {after_txt['say']!r}")

        GUIDE_STATE = """() => { const z = document.getElementById('photoUploadBtn'), i = document.getElementById('photoBgImg'), h = document.getElementById('canvasEmptyHint');
          const g = h.querySelector('.face-guide-words'), n = document.getElementById('photoGuideNote');
          return { loaded: !!z && z.classList.contains('loaded'), slider: document.getElementById('photoOpacity').value,
            shown: i ? +getComputedStyle(i).opacity : null, meta: (document.getElementById('photoBtnMeta') || {}).textContent,
            note: n ? n.textContent : null, guide: h.classList.contains('is-guide'),
            words: g ? [...g.children].map(c => c.textContent) : [] }; }"""

        def trace_open(page):
            """Your face, Trace a photo, the photo picked: the Pad in its frame,
            once the photo is in."""
            page.goto(BASE + "/social/@tess")
            page.wait_for_timeout(400)
            open_face_sheet(page, 700)
            with page.expect_file_chooser(timeout=8000) as fc:
                page.click("#faceSheet [data-face-trace]", timeout=5000)
            fc.value.set_files(str(tmp / "IMG_0412.jpg"))
            fr = pad_frame(page)
            if fr is None:
                return None
            try:
                fr.wait_for_function("() => { const z = document.getElementById('photoUploadBtn');"
                                     " return !!z && z.classList.contains('loaded'); }", timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(600)
            return fr

        def painted(page, fr, sel):
            """The lowest contrast of the words at `sel` (in the Pad's frame)
            against what is painted under them: the words made see-through, the
            box photographed, every pixel of the ground against the words' own
            colour laid over it, their see-through part included."""
            box = fr.evaluate("""(sel) => { const e = document.querySelector(sel); if (!e) return null;
              const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height,
              color: getComputedStyle(e).color }; }""", sel)
            if not box or box["w"] < 2:
                return None
            off = page.locator("#facePad iframe").bounding_box()
            c = [float(v) for v in re.findall(r"[\d.]+", box["color"])]
            rgb, a = c[:3], (c[3] if len(c) > 3 else 1.0)
            fr.evaluate("(sel) => { document.querySelector(sel).style.color = 'transparent'; }", sel)
            page.wait_for_timeout(150)
            png = page.screenshot(clip={"x": off["x"] + box["x"], "y": off["y"] + box["y"],
                                        "width": box["w"], "height": box["h"]})
            fr.evaluate("(sel) => { document.querySelector(sel).style.color = ''; }", sel)
            im = Image.open(io.BytesIO(png)).convert("RGB")

            def lum(px):
                v = [(x / 255) / 12.92 if x / 255 <= 0.03928 else ((x / 255 + 0.055) / 1.055) ** 2.4 for x in px]
                return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
            low = 99.0
            for px in set(im.getdata()):
                shown = [a * t + (1 - a) * g for t, g in zip(rgb, px)]
                x, y = lum(shown), lum(px)
                low = min(low, (max(x, y) + 0.05) / (min(x, y) + 0.05))
            return round(low, 2)

        fr = trace_open(pg)
        state = fr.evaluate(GUIDE_STATE) if fr else {"no Pad": True}
        sheet_gone = pg.evaluate("() => !document.getElementById('faceSheet').classList.contains('is-open')")
        check("a photo picked opens the Pad above with it under the canvas, a guide: at 40% to start (the slider"
              " says so), the row says A guide to trace, the drawer says only the lines are kept, the empty canvas"
              " says Trace your face; the sheet has gone",
              bool(fr) and state.get("loaded") and state.get("slider") == "40" and state.get("shown") == 0.4
              and state.get("meta") == "A guide to trace"
              and state.get("note") == "Only your lines are kept. The photo is never posted."
              and state.get("guide") and state.get("words") == ["Trace your face",
                                                               "Draw over your photo. Only your lines are kept."]
              and sheet_gone,
              f"{state}; sheet gone {sheet_gone}")

        # THE GUIDE'S WORDS, READ OFF THE PAINT over the photo's dark middle:
        # light here, and dark in a second browser.
        reads = {}
        if fr:
            reads["light"] = [painted(pg, fr, "#canvasEmptyHint .face-guide-words > span:first-child"),
                              painted(pg, fr, "#canvasEmptyHint .face-guide-words > .canvas-empty-sub")]
        dctx, dpg = browser_as(b, tess, "phone", "dark")
        try:
            dfr = trace_open(dpg)
            if dfr:
                reads["dark"] = [painted(dpg, dfr, "#canvasEmptyHint .face-guide-words > span:first-child"),
                                 painted(dpg, dfr, "#canvasEmptyHint .face-guide-words > .canvas-empty-sub")]
        except Exception as exc:
            reads["dark"] = [f"could not: {str(exc).splitlines()[0][:80]}"]
        close_ctx(dctx, dpg)
        flat = [x for v in reads.values() for x in v]
        check("the guide's words read at 4.5:1 or more over the photo's darkest middle, read off the paint with"
              " their see-through ink laid over it: light and dark",
              len(flat) == 4 and all(isinstance(x, float) and x >= 4.5 for x in flat), str(reads))

        # USE THIS FACE: the lines alone, in what the page sends and on its card.
        sent = None
        if fr:
            strokes = [artdraw.Stroke(_arc(354, 330, 150, 170, -90, 270, 30), "gesture", INK, size=18),
                       artdraw.Stroke(_arc(300, 300, 14, 14, 0, 360, 10), "detail", INK, size=12),
                       artdraw.Stroke(_arc(408, 300, 14, 14, 0, 360, 10), "detail", INK, size=12),
                       artdraw.Stroke(_arc(354, 400, 50, 24, 20, 160, 10), "detail", PURPLE, size=10)]
            draw_in_pad(pg, fr, strokes)
            sheet, sent = keep_in_pad(pg, fr)
        body = {}
        try:
            body = json.loads(sent or "{}").get("payload") or {}
        except ValueError:
            body = {}
        photos = [body.get("photo")] + [f.get("photo") for f in (body.get("frames") or []) if isinstance(f, dict)]
        green = None
        thumb = body.get("thumbnail") or ""
        if thumb.startswith("data:image"):
            im = Image.open(io.BytesIO(base64.b64decode(thumb.split(",", 1)[1]))).convert("RGB")
            green = sum(1 for (r_, g_, b_) in im.getdata() if g_ - max(r_, b_) > 30)
        row = person_row("tess")
        face = row[3] if row else None
        kept = json.loads(db("select payload_json from skribl_posts where public_id = ?", (face,))[0][0]) if face else {}
        kept_photos = [kept.get("photo")] + [f.get("photo") for f in (kept.get("frames") or [])]
        check("Use this face keeps the lines alone: the drawing the page sends has no photo in any frame, its card"
              " has none of the photo's colour on it, and the face kept is the lines, its strokes all there",
              bool(body) and all(x is None for x in photos) and green == 0
              and bool(face) and all(x is None for x in kept_photos)
              and len((kept.get("frames") or [{}])[0].get("strokes") or []) > 40,
              f"sent photos {[bool(x) for x in photos]}; green pixels on the card {green}; face {face};"
              f" kept photos {[bool(x) for x in kept_photos]}")

        # THE SITE DROPS A PHOTO SENT ANYWAY: the same lines, with a photo put
        # back in, straight to /you/face.
        sneaky = json.loads(json.dumps(body)) if body else {}
        dot = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
        if sneaky:
            ph = {"data": dot, "fit": "cover", "opacity": 1, "blur": 0, "offset": {"x": 0.5, "y": 0.5}, "zoom": 1}
            sneaky["photo"] = ph
            for f in sneaky.get("frames") or []:
                f["photo"] = ph
        c = tess.client()
        c.get("/social/@tess")
        st, j = c.post_json("/social/you/face", {"payload": sneaky}) if sneaky else (None, None)
        face3 = (person_row("tess") or [None] * 4)[3]
        kept3 = json.loads(db("select payload_json from skribl_posts where public_id = ?", (face3,))[0][0]) \
            if face3 and face3 != face else {}
        kept3_photos = [kept3.get("photo")] + [f.get("photo") for f in (kept3.get("frames") or [])]
        check("a face sent with a photo anyway (straight to /you/face) is kept without it: the site drops the"
              " photo from every frame, and keeps the lines",
              st == 200 and bool(kept3) and all(x is None for x in kept3_photos)
              and len((kept3.get("frames") or [{}])[0].get("strokes") or []) > 40,
              f"status {st} {str(j)[:80]}; face {face} -> {face3}; kept photos {[bool(x) for x in kept3_photos]}")

    # ------------------------------------------------------------------ 13
    if part(13, "a face fits the circle: the circle after the Pad, its Back, and Edit this face"):
        # The owner's "all yes" after v330: "when I traced an image it didn't
        # fit in the circle. there should be a way to adjust the size", and
        # "maybe you should be able to edit it after it's done".
        uma = member(b, "uma", "Uma Reyes")
        pg = uma.pg
        S_ = artdraw.Stroke
        # HEAD AND SHOULDERS, as a traced portrait is drawn: the shoulders run
        # into the canvas's bottom corners, which the drawing's middle square
        # (the face a drawing had before) leaves outside its circle.
        PORTRAIT = [S_(_arc(354, 290, 140, 170, 0, 360, 24), "gesture", INK, size=20),
                    S_([(40, 700), (90, 640), (200, 585), (354, 570), (510, 585), (620, 640), (668, 700)],
                       "contour", PURPLE, size=22),
                    S_(_arc(300, 280, 14, 12, 0, 360, 8), "detail", INK, size=12),
                    S_(_arc(408, 280, 14, 12, 0, 360, 8), "detail", INK, size=12)]
        R = 707 / 2
        corner_out = max(math.hypot(x - R, y - R) for s in PORTRAIT for (x, y) in s.pts) - R

        # The circle read every frame from the Pad's Use: whether the place
        # step is up, the drawing laid out on the stage (its width) and
        # painted (ink in its canvas), and where the sheet is.
        WATCH = """() => { window.__fit = []; const t0 = performance.now(), sheet = document.querySelector('#faceSheet .make-sheet');
          let inked = false;
          (function f() { const st = document.querySelector('#faceSheet [data-step=place]');
            const shown = !!st && !st.hidden && document.getElementById('faceSheet').classList.contains('is-open');
            const a = document.querySelector('#faceSheet [data-face-art]'), c = a && a.querySelector('canvas');
            let ink = inked ? 99 : 0;
            if (shown && !inked && c && c.width) { try { const x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
              for (let i = 0; i < x.length; i += 64) if (x[i + 3] > 0 && Math.abs(x[i] - 246) + Math.abs(x[i + 1] - 242) + Math.abs(x[i + 2] - 234) > 90) ink++;
              inked = ink > 20; } catch (e) { ink = -1; } }
            window.__fit.push([Math.round(performance.now() - t0), shown ? 1 : 0, a ? (parseFloat(a.style.width) || 0) : 0, ink,
                               sheet ? Math.round(sheet.getBoundingClientRect().top) : null]);
            if (performance.now() - t0 < 5000) requestAnimationFrame(f); })(); }"""

        def kept_face():
            row = person_row("uma")
            fid = row[3] if row else None
            pay = json.loads(db("select payload_json from skribl_posts where public_id = ?", (fid,))[0][0]) if fid else {}
            return fid, (pay.get("frames") or [{}])[0]

        def inside(frame0):
            """How far the kept face's furthest line reaches past its circle
            (negative: inside), each point's own size included."""
            pts = [p for p in (frame0.get("strokes") or []) if not p.get("erase")]
            return max((math.hypot(p["x"] - R, p["y"] - R) + (p.get("size") or 0) / 2 - R for p in pts), default=None), len(pts)

        # A. DRAW A NEW ONE, then Use: the circle, the whole drawing inside it.
        pg.goto(BASE + "/social/@uma")
        pg.wait_for_timeout(400)
        open_face_sheet(pg, 700)
        pg.click("#faceSheet [data-face-open]", timeout=5000)
        fr = pad_frame(pg)
        drawn = 0
        frames, stage = [], {}
        face_a, frame_a = None, {}
        if fr is not None:
            draw_in_pad(pg, fr, PORTRAIT, tempo=2.4, gaps=3.0)
            drawn = fr.evaluate("() => strokes.filter(p => !p.erase).length")
            pg.evaluate(WATCH)
            use_in_pad(pg, fr)
            try:
                pg.wait_for_function(PLACED, timeout=15000)
            except Exception:
                pass
            pg.wait_for_timeout(1500)
            frames = pg.evaluate("() => window.__fit || []")
            stage = pg.evaluate("""() => { const st = document.querySelector('#faceSheet [data-face-stage]'), a = document.querySelector('#faceSheet [data-face-art]');
                return st && a ? { S: st.clientWidth, w: parseFloat(a.style.width) || 0 } : {}; }""")
            if pg.evaluate(PLACED):
                with pg.expect_navigation(timeout=30000):
                    pg.click("#faceSheet [data-face-use]", timeout=5000)
                pg.wait_for_timeout(400)
                face_a, frame_a = kept_face()
        seen = [f for f in frames if f[1]]
        first = seen[0] if seen else None
        ink_at = next((f[0] for f in seen if f[3] > 20), None)
        reach_a, kept_n = inside(frame_a)
        tops = [f[4] for f in seen]
        check("after the Pad, Use brings Your face's circle, every time: it glides up with the drawing already laid out"
              " in it (no frame of it empty) and painted at once, and starts with ALL of the drawing inside the circle,"
              " where its middle square cut the shoulders off; Use this face keeps it so, every line inside its circle",
              corner_out > 40 and bool(first) and all(f[2] > 0 for f in seen) and ink_at is not None
              and ink_at - first[0] <= 300 and len(set(tops)) >= 5 and stage.get("w", 0) > 0
              and bool(face_a) and reach_a is not None and reach_a <= 0.5 and kept_n == drawn,
              f"on the middle square the shoulders reach {corner_out:.0f} past the circle; circle first seen at"
              f" {first and first[0]} ms, laid out {[f[2] for f in seen[:3]]}, painted at {ink_at} ms, the sheet at"
              f" {len(set(tops))} places; stage {stage}; kept {face_a}: its furthest line {reach_a} past its circle,"
              f" {kept_n} of {drawn} points")

        # B. TRACE A PHOTO, Use, then the circle's Back: the Pad again, the
        # drawing still in it and the photo under it again; Use comes back.
        tmp = Path(tempfile.mkdtemp())
        Image.new("RGB", (500, 500), (210, 170, 120)).save(tmp / "IMG_7731.jpg", quality=90)
        GUIDED = """() => ({ n: strokes.filter(p => !p.erase).length,
            photo: !!document.getElementById('photoUploadBtn') && document.getElementById('photoUploadBtn').classList.contains('loaded'),
            slider: (document.getElementById('photoOpacity') || {}).value })"""
        before = after = {}
        overlay_back = {}
        again = False
        face_b = None
        pg.goto(BASE + "/social/@uma")
        pg.wait_for_timeout(400)
        open_face_sheet(pg, 700)
        try:
            with pg.expect_file_chooser(timeout=8000) as fc:
                pg.click("#faceSheet [data-face-trace]", timeout=5000)
            fc.value.set_files(str(tmp / "IMG_7731.jpg"))
            fr = pad_frame(pg)
            fr.wait_for_function("() => { const z = document.getElementById('photoUploadBtn'); return !!z && z.classList.contains('loaded'); }",
                                 timeout=15000)
            pg.wait_for_timeout(500)
            draw_in_pad(pg, fr, PORTRAIT[:2], tempo=2.6, gaps=3.0)
            before = fr.evaluate(GUIDED)
            use_in_pad(pg, fr)
            pg.wait_for_function(PLACED, timeout=15000)
            pg.wait_for_timeout(600)
            pg.click("#faceSheet [data-step=place] [data-face-go=pick]", timeout=5000)
            pg.wait_for_function("() => { const w = document.getElementById('facePad'); return !!w && !w.hidden && w.classList.contains('is-open'); }",
                                 timeout=10000)
            fr = pad_frame(pg)
            try:
                fr.wait_for_function("""(n) => strokes.filter(p => !p.erase).length === n
                    && document.getElementById('photoUploadBtn').classList.contains('loaded')""", arg=before.get("n", -1), timeout=10000)
            except Exception:
                pass
            pg.wait_for_timeout(400)
            after = fr.evaluate(GUIDED)
            overlay_back = pg.evaluate(OVERLAY) or {}
            use_in_pad(pg, fr)
            pg.wait_for_function(PLACED, timeout=15000)
            again = True
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                pg.click("#faceSheet [data-face-use]", timeout=5000)
            pg.wait_for_timeout(400)
            face_b, frame_b = kept_face()
            kept_b = inside(frame_b)[1]
            photos_b = frame_b.get("photo")
        except Exception as exc:
            ERRS.append(f"section 13, Back: {str(exc).splitlines()[0][:120]}")
            kept_b, photos_b = None, "?"
        check("from the circle, Back goes to the Pad with the drawing still in it and, traced, the photo under it again"
              " (at the guide's 40%); Use brings the circle back, and the face kept is the lines alone, every one",
              before.get("n", 0) > 10 and before.get("photo") and overlay_back.get("open")
              and after.get("n") == before.get("n") and after.get("photo") and after.get("slider") == "40"
              and again and bool(face_b) and face_b != face_a and kept_b == before.get("n") and not photos_b,
              f"before Use {before}; after Back {after}, overlay {overlay_back.get('open')}; the circle again {again};"
              f" kept {face_b}: {kept_b} points, photo {bool(photos_b)}")

        # C. EDIT THIS FACE: the first door once there is a face; the face in
        # the Pad, a line added, the circle, and a face with both.
        pg.goto(BASE + "/social/@uma")
        pg.wait_for_timeout(400)
        open_face_sheet(pg, 700)
        doors = pg.evaluate("""() => [...document.querySelectorAll('#faceSheet [data-step=doors] .make-door')].map(b => ({
            title: b.querySelector('b').textContent, words: b.querySelector('.make-words > span').textContent,
            edit: b.hasAttribute('data-face-edit'), h: Math.round(b.getBoundingClientRect().height) }))""")
        loaded = added = 0
        pill = None
        face_c, frame_c = None, {}
        _, frame_had = kept_face()
        had = inside(frame_had)[1]
        try:
            pg.click("#faceSheet [data-face-edit]", timeout=5000)
            fr = pad_frame(pg)
            fr.wait_for_function("(n) => strokes.filter(p => !p.erase).length === n", arg=had, timeout=15000)
            pg.wait_for_timeout(500)
            loaded = fr.evaluate("() => strokes.filter(p => !p.erase).length")
            pill = fr.evaluate("() => { const p = document.getElementById('addTakePill'); return !!p && !p.hidden; }")
            fr.click("#addTakePill", timeout=5000)
            pg.wait_for_timeout(400)
            draw_in_pad(pg, fr, [S_([(200, 120), (354, 90), (508, 120)], "accent", PURPLE, size=16)], tempo=2.6, gaps=3.0)
            added = fr.evaluate("() => strokes.filter(p => !p.erase).length")
            use_in_pad(pg, fr)
            pg.wait_for_function(PLACED, timeout=15000)
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                pg.click("#faceSheet [data-face-use]", timeout=5000)
            pg.wait_for_timeout(400)
            face_c, frame_c = kept_face()
        except Exception as exc:
            ERRS.append(f"section 13, Edit: {str(exc).splitlines()[0][:120]}")
        reach_c, kept_c = inside(frame_c)
        titles = [d["title"] for d in doors]
        ed = doors[0] if doors else {}
        check("Edit this face is the first of Your face's four doors once there is a face (the others as before), saying"
              " what it does; it opens the Pad with the face in it, every line, Keep drawing showing the way on; a line"
              " added, Use brings the circle, and the face kept has both, every line inside its circle",
              titles == ["Edit this face", "Draw a new one", "Trace a photo", "Use one you made"] and ed.get("edit")
              and ed.get("words") == "Add to it, undo or erase, then fit it in the circle." and ed.get("h", 0) >= 44
              and had > 10 and loaded == had and pill and added > loaded
              and bool(face_c) and face_c != face_b and kept_c == added and reach_c is not None and reach_c <= 0.5,
              f"doors {titles}; edit {ed}; the face had {had} points, the Pad loaded {loaded} (Keep drawing {pill}),"
              f" {added} with the line; kept {face_c}: {kept_c} points, its furthest {reach_c} past its circle")

    # ------------------------------------------------------------------ 14
    if part(14, "your face first: the face leads, the other ways side by side, their icons drawn in our pen"):
        # The owner's "all yes" on mock C after v330: "do you think those icons
        # represent skribl ... the 4 in a column look kinda weak".
        wyn = member(b, "wyn", "Wyn Adler")
        vic = member(b, "vic", "Vic Moss")
        face_w = give_face(b, wyn)
        DOORSET = """() => { const st = document.querySelector('#faceSheet [data-step=doors]');
          return [...st.querySelectorAll('.make-door')].map(d => { const r = d.getBoundingClientRect();
            const img = d.querySelector('.face-lead-me .skribl-face img'), sr = d.querySelector('.make-words .sr');
            return { title: d.querySelector('.make-words b').textContent, lead: d.classList.contains('face-lead'),
                     face: img ? img.getAttribute('src') : null, circle: !!d.querySelector('.face-lead-me svg.pen-ic'),
                     said: sr ? sr.textContent.trim() : null, x: Math.round(r.left), y: Math.round(r.top),
                     w: Math.round(r.width), h: Math.round(r.height) }; }); }"""
        INKS = """() => { const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
          const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                             return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
          const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
          const probe = document.createElement('span'); probe.style.color = 'var(--accent-ink)'; document.body.appendChild(probe);
          const accent = getComputedStyle(probe).color; probe.remove();
          return [...document.querySelectorAll('#faceSheet [data-step=doors] .make-ic, #faceSheet [data-step=doors] .face-lead-me.is-new')].map(t => {
            const svg = t.querySelector('svg'), door = t.closest('.make-door');
            const tile = rgba(getComputedStyle(t).backgroundColor), row = rgba(getComputedStyle(door).backgroundColor), ink = rgba(getComputedStyle(svg).color);
            const ground = [0, 1, 2].map(k => tile[k] * tile[3] + row[k] * (1 - tile[3]));
            return { door: door.querySelector('b').textContent, pen: svg.classList.contains('pen-ic'), ink: getComputedStyle(svg).color, accent,
                     k: Math.round(ratio(ink, ground) * 100) / 100, faint: [...svg.querySelectorAll('path.faint')].map(p => +p.getAttribute('opacity')) }; }); }"""
        # The sheet raised by its button, read every frame: the dash of one of
        # Trace a photo's own lines (1 unseen, 0 drawn) and the lead's face.
        DRAWIN = """(ms) => new Promise(res => { const out = [], t0 = performance.now();
          document.querySelector('button[data-face-sheet]').click();
          (function f() { const p = document.querySelector('#faceSheet [data-face-trace] svg.pen-ic path:not(.faint)');
            const face = document.querySelector('#faceSheet [data-face-lead] .skribl-face');
            out.push([Math.round(performance.now() - t0), p ? parseFloat(getComputedStyle(p).strokeDashoffset) || 0 : null,
                      face ? face.getAttribute('data-play') : null, face ? face.className : '']);
            if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""
        seen, still_in = {}, {}
        for who, tag in ((wyn, "face"), (vic, "none")):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, who, "phone", scheme)
                cpg.goto(BASE + f"/social/@{who.handle}")
                cpg.wait_for_timeout(500)
                # The lead's still, in the page before the sheet rises (what
                # shows under Reduce Motion and before the face draws itself).
                still_in[(tag, scheme)] = cpg.evaluate("""() => { const i = document.querySelector('#faceSheet [data-face-lead] .skribl-face img');
                    return i ? i.getAttribute('src') : null; }""")
                open_face_sheet(cpg, 900)
                seen[(tag, scheme)] = (cpg.evaluate(DOORSET), cpg.evaluate(INKS))
                close_ctx(ctx, cpg)
        d_face, d_none = seen[("face", "light")][0], seen[("none", "light")][0]

        def side_by_side(row):
            return (len(row) >= 2 and max(r["y"] for r in row) - min(r["y"] for r in row) <= 1
                    and all(a["x"] < b_["x"] for a, b_ in zip(row, row[1:])) and all(r["w"] >= 44 and r["h"] >= 44 for r in row)
                    and all(r["said"] for r in row))
        lead, rest = (d_face[0] if d_face else {}), d_face[1:]
        check("with a face, Your face leads with it: Edit this face, the sheet's one big door (twice any other's"
              " area or more), holding a still of"
              " their own face; Draw a new one, Trace a photo and Use one you made sit side by side under it, each"
              " 44px or more and still saying what it does to a screen reader; before a face, the empty circle leads,"
              " Draw your face, and the other two sit side by side",
              [d["title"] for d in d_face] == ["Edit this face", "Draw a new one", "Trace a photo", "Use one you made"]
              and lead.get("lead") and (lead.get("face") or "").endswith(f"/s/{face_w}/poster")
              and all((still_in[("face", sc)] or "").endswith(f"/s/{face_w}/poster") for sc in ("light", "dark"))
              and lead.get("w", 0) * lead.get("h", 0) >= 2 * max((r["w"] * r["h"] for r in rest), default=10 ** 9)
              and side_by_side(rest)
              and [d["title"] for d in d_none] == ["Draw your face", "Trace a photo", "Use one you made"]
              and d_none[0]["lead"] and d_none[0]["circle"] and side_by_side(d_none[1:]),
              f"with a face {[(d['title'], d['w'], d['h'], d['y']) for d in d_face]}, its face {lead.get('face')}"
              f" (its still before the sheet rises {still_in.get(('face', 'light'))});"
              f" before one {[(d['title'], d['w'], d['h'], d['y']) for d in d_none]}")
        inks = [(t, s_, i) for (t, s_), (_, ii) in seen.items() for i in ii]
        low = [f"{t} {s_} {i['door']}: {i['k']}" for t, s_, i in inks if i["k"] < 4.5]
        check("every door's icon is drawn in our pen (the signature's pen, .pen-ic) in the small violet ink"
              " (--accent-ink) on the note's tint, 4.5:1 or more against its tile, and what is already there (the"
              " empty circle, the photo) faint at 40%: light and dark, with a face and before one",
              len(inks) == 12 and all(i["pen"] and i["ink"] == i["accent"] for _, _, i in inks) and not low
              and all(i["faint"] == [0.4] for _, _, i in inks if i["door"] in ("Draw a new one", "Draw your face"))
              and all(i["faint"] == [0.4, 0.4] for _, _, i in inks if i["door"] == "Trace a photo"),
              f"{len(inks)} icons; not the pen or not the ink: {[(t, s_, i['door']) for t, s_, i in inks if not (i['pen'] and i['ink'] == i['accent'])]};"
              f" under 4.5: {low}; lowest {min((i['k'] for _, _, i in inks), default=None)}")
        ctx, cpg = browser_as(b, wyn, "phone", "light")
        cpg.goto(BASE + "/social/@wyn")
        cpg.wait_for_timeout(5500)
        drawn = cpg.evaluate(DRAWIN, 1600)
        close_ctx(ctx, cpg)
        ctx, cpg = browser_as(b, wyn, "phone", "light", reduced=True)
        cpg.goto(BASE + "/social/@wyn")
        cpg.wait_for_timeout(800)
        still = cpg.evaluate(DRAWIN, 900)
        close_ctx(ctx, cpg)
        offs = [f[1] for f in drawn if f[1] is not None]
        steps = [z - a for a, z in zip(offs, offs[1:])]
        check("each icon draws itself once as the sheet rises, read every frame: a line goes from unseen (1) to"
              " drawn (0) on many frames, one way; the face that leads draws itself again (a fresh copy, playing);"
              " under Reduce Motion every line is there from the first frame and the face is the still",
              bool(offs) and offs[0] >= 0.9 and offs[-1] <= 0.001 and all(s_ <= 1e-6 for s_ in steps)
              and len({round(o, 3) for o in offs}) >= 8 and drawn[-1][2] == "once" and "is-live" in drawn[-1][3]
              and still and all((f[1] or 0) <= 0.001 for f in still) and still[-1][2] == "still",
              f"offsets {[round(o, 2) for o in offs[:4]]}..{[round(o, 2) for o in offs[-2:]]} on {len({round(o, 3) for o in offs})} values;"
              f" the face {drawn[-1][2:] if drawn else None}; reduced: offsets {sorted({round(f[1] or 0, 3) for f in still})[:3]},"
              f" face {still[-1][2] if still else None}")

    if part(10, "no page errors, no console errors, no CSP violations"):
        for p in list(_people.values()):
            ERRS.extend(f"csp: {v}" for v in p.csp())
        check("no page errors, console errors or CSP violations on the profiles, Edit profile, the Pad's overlay and"
              " the pages around them, through everything above (a refused request's own status line aside)",
              not ERRS, "; ".join(ERRS[:4]))
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
