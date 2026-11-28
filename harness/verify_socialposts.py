"""Posts on the Skribl site (phase 1, piece 4; docs/SOCIAL-SITE.md "Built:
piece 4, posts"), through the demo's own server, with Chromium's virtual
authenticator for the site's people and a real pen in Skribl's real Pad.

  1. HOME, SIGNED IN: no box at the top (the owner's "All yes", Nov 14:
     Make is the way to post); the bar's Make opens the composer
     (verify_composer holds the composer itself); there, with nothing drawn,
     Post says so and sends nothing; an empty feed says to tap Make. Signed
     out, Home is the first visit, as before.
  2. COMPOSING FROM HOME: Make, then the composer's Draw, opens Skribl's Pad over the
     composer in compose mode, asking for no gallery tick (compose=1, no
     gallery=1; its sheet still asks Viewers start at); Add hands the
     drawing back into the composer's own in-post player; Edit drawing reopens it with the drawing in it;
     Remove takes it away. Flip opens Flip the same.
  3. POSTING: the words and the drawing, one post: its row on the site's
     chain, its skribl through create_post (unlisted without the tick, its
     title the first words, no caption), and the post's own page, where the
     drawing plays by itself; under Reduce Motion it rests still. A payload
     that says public (the tick the composer asked for until Nov 19) is
     still kept public, and Skribl's listing shows it. No Make your
     own on the page (Nov 14): the bar's and the rail's Make opens the
     composer there. NO MORE FROM
     on it (the Calm Post Page, Nov 20): its author's other drawings are
     not on the page or in its source.
  4. THE FEED: everyone's posts, newest first, each card still until
     tapped, its time said in the person's own; Load more brings the next
     page in place, by a cursor that names no internal id.
  5. THE ⋯ SHEET: your own post's Copy link, Share…, Delete post; somebody
     else's Copy link, Share…, Mute @them (mutes: its name read, its line is
     verify_socialmute's), Report this post and Block @them (piece 5).
     Report sends the Gallery's reasons and "A child's safety" into the
     site's own queue and says thanks (verify_socialsafety holds the rest);
     Delete asks once, then the words and the drawing go.
  6. GUARDS: no token, no sign-in, too many words or a hidden character, no
     drawing, somebody else's post, the limit; a post's body may be bigger
     than the site's 64 KiB; deleting an account takes its posts.
  7. THE NEW SCREENS: every word at 4.5:1 on what is painted behind it,
     every target 44px, every text field 16px: phone and desk, light and
     dark.
  8. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).
  9. HOME SHOWS POSTS ONLY (the map's step 3): a drawing shown in the
     gallery from the Pad outside a post, one kept unlisted and one by
     somebody not on the site are on nobody's Home (its maker's Following
     and Everyone, a follower's, somebody else's, signed out; each walked
     with Load more, every card a post, signed out read against the
     database itself); the drawing is in the Gallery (every skribl, since
     Nov 14) and keeps its own page and its maker's; the posts shared the
     same minute are there; a
     cursor from before that names a drawing reads as its time; Load more
     walks the posts alone; a drawing's own page, its ⋯ and its Delete, and
     their guards.
 10. A CARD'S WAYS IN (the owner's yes, Nov 12): its words and its time each a
     link to its page, a tap landing on them across 44px; the face, the name
     and the @handle the person's; the 💬 even at none; nothing moved. Phone
     and desk, light and dark. A drawing shown outside a post has no card on
     Home (section 9).
 11. ANYWHERE ON A CARD opens its post (the same yes): its ground, its words,
     the 💬 at its comments; the drawing plays and pauses and stays, even at
     its edge under the time; the face, the name and the @handle open the
     person's page; ⋯ and Share do their own job; a drag that selects words
     opens nothing. A touch on a phone, a click on a desk.
 12. EVERY CARD OPENS ITS POST (the owner's "I thought on card?", Nov 13):
     Cal's tap map of Home's cards and of Skribl's own Gallery cards where a
     host says they open its page (Skribl's /gallery, its section given the
     address the site's pages gave theirs, /social/b/__ID__: no page of the
     site holds Skribl's section since the first visit became the Gallery's
     six, Nov 14; Explore's was until the map's step 3, a profile's until its
     step 4; how the section says it is verify_hostseams'), on a touch phone
     in light and dark: every 4px one of the card's own controls or its
     ground, and an exact tap on every part of the ground opens the card's
     page (a post's, a drawing's, or Skribl's own for one by somebody not on
     the site); a finger on the drawing plays it, on the name opens the
     person, on the ground opens the page, followed; /social/b/<id>'s ways
     on; the line's own controls; on a desk Ctrl and the middle button, a
     drag, the title a keyboard's link; the ⋯; and Skribl's own /gallery,
     with no address said, as it was.
 13. THE GALLERY OF EVERYONE (Explore; the map's step 3, the Gallery mock's
     B), OF EVERY SKRIBL since the owner's "Yes, your picks" (Nov 14): every
     post once, a Flip's too, and every drawing the site's people showed
     outside a post (its tile opening its own page), in one order; never one
     kept link-only, a face or one by somebody not on the site;
     its tiles two across on a touch phone and three on a desk, each the
     drawing whole in 650 x 486, the box around it the drawing's own ground
     (a tall one on the Pad's dark in its dark, read off the paint, there
     and on its maker's Gallery tab), with "▶ 15 sec" (what the player's
     play button says at rest, without "drawn in"; a Flip its pages), the
     maker's face at 22px and whole name, the hearts and comments only when
     there are some; the drawing whole and alone, cut out of its share card;
     a tap anywhere on a tile opens its post (a touch, a click, the keyboard:
     every 4px of it its one link); Following only the people you follow and
     you, Everyone everybody, the pill gliding and the tiles fading, read on
     every frame, the address saying which; Hot plays in the last seven
     days, most first, both kinds in one order; a search by the words, a
     drawing's title, the name and the @handle; Load more through both, by a
     cursor that names no internal id; the reads on their indexes; every
     word at 4.5:1
     (the ▶'s words read off the pixels under them), every control 44px,
     the box 16px: phone and desk, light and dark.
 14. THE FIRST VISIT, B (the owner's "Your picks", Nov 14): Home signed out
     keeps its welcome; under "Fresh from everyone" the six newest tiles of
     the Gallery of everyone (the first six /social/explore shows signed
     out, read against the database), every skribl (a drawing shown outside
     a post among them, opening its own page; never one kept link-only, a
     face or one by somebody not on the site, each newer than the six), none
     of Skribl's own Gallery section; then
     "See the whole Gallery ›" in the small violet words, 44px, landing on
     the Gallery; every word at 4.5:1, every control 44px, phone and desk,
     light and dark.
 15. A DRAWING ON A PICTURE KEEPS ITS PICTURE AT ITS SIDES (C+, the owner's
     "Yes to both, build them", Nov 14): a drawing made on a photo, or on the
     picture the Pad began on, a post's or one shown outside a post, shows that
     picture at its sides, blurred (read off the paint beside the plate: its
     colours, never its ground, no hard step), in the Gallery, on its maker's
     Gallery tab and on the first visit; a plain drawing keeps
     its strips in its own ground, with no copy behind it; every tile's ▶,
     and on your own Gallery tab its eye, is what is painted along its middle
     (elementFromPoint), phone and desk, light and dark; their words and the
     eye at 4.5:1 off the pixels over a picture; and hidden with the eye, the
     picture at its sides fades with the drawing.
 16. A LIST OF CHOICES IS ONE CARD (B, the owner's "B, equal lines", Nov 14),
     on every menu sheet of the site: the ☰'s, a post's ⋯ (yours and
     somebody else's), a comment's ⋯, a person's ⋯, and Report's reasons:
     each list one card (--row-bg, 16 round), its rows on it with nothing of
     their own, touching, a hairline (--rule) between two; the risky rows a
     card of their own 12px under the other; no Cancel under a menu sheet
     (Report keeps its pair), which goes by Esc, a tap outside, its grip and
     a swipe down; the card's colour in each row's margin and the paper
     between two cards, read off the screen; a key's ring drawn inside the
     row. Phone and desk, light and dark.
 24. BLUESKY'S COLUMNS (the owner's "I like Bluesky columns", Nov 28): on a
     card the face has its own column, and the words, the drawing, a quote
     and the row's first icon start where the name does, beyond the face;
     a reposted line's words there too, its arrows just before them; the
     row spread across the column; a post's own page keeps its full width.
     Phone and desk.

SOCIALPOSTS_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Posts at /social (phase 1, piece 4)",
"Comments on every drawing" for 10 and 11, "Every card opens its post"
for 12, "Explore becomes the Gallery of everyone" for 13, "Six small
yeses" for 14 and the rows of 3, 12 and 13 it changed, "The Gallery of
every skribl" for the rows of 9, 13 and 14 it changed, "A drawing on a
photo keeps its photo at its sides" for 15, and "One card for a list of
choices, and the menu's equal lines" for 16.
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
PART = os.environ.get("SOCIALPOSTS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALPOSTS {n} — {label}")
    return True


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence posts work.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)
try:
    from PIL import Image, ImageDraw
except ImportError:      # declared in harness/requirements.txt; the row that needs it fails, saying so
    Image = ImageDraw = None
import io  # noqa: E402
import artdraw  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialposts-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialposts-" + secrets.token_hex(8),
           SKRIBL_CSRF_PROTECT="1", SKRIBL_SOCIAL_FIRST_INVITE=FIRST, SKRIBL_STAND_IN="0",
           SKRIBL_TRUSTED_PROXIES="1", SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000")
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_DEMO_IDENTITY",
          "SKRIBL_DEMO_LOGIN_KEY", "SKRIBL_SOCIAL_HOSTS"):
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
    return f"10.{60 + _addr[0] // 250}.{_addr[0] % 250}.7"


def db(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def cli(*args):
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", *args, "--base", BASE],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    return out.stdout.strip().splitlines()[-1] if out.returncode == 0 else None


def drawing(n=40, seed=0, flip=False, size=(816, 612)):
    """A small drawing, as the Pad's Add hands one back (or a Flip's)."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * 30, "start": i == 0} for i in range(n)]
    body = {"version": 2, "schemaVersion": 2, "playbackMode": "flip" if flip else "replay",
            "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}
    if flip:
        body["fps"] = 12
        body["frames"].append({"strokes": [dict(p, x=p["x"] + 20) for p in pts], "strokeGroups": [len(pts)],
                               "background": {"color": "#f6f2ea"}})
    return body


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


def browser_as(b, who, screen="phone", scheme="light", reduced=False, scale=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    opts = dict(PHONE if screen == "phone" else DESK)
    if scale:
        opts["device_scale_factor"] = scale
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **opts, **kw)
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


# THE SHARE CARD, in colours nothing else on a page wears: the card's own
# ground magenta, its wordmark's strip cyan, the plate's hairline green (3 card
# pixels, 0 to 2 inside the plate's edge), the drawing's paper with a blue mark
# in each corner; the plate where lib/sharecard.js drawingRect() puts it.
CARD_GROUND, CARD_FOOT, CARD_LINE, CARD_MARK = (255, 0, 255), (0, 255, 255), (0, 160, 0), (0, 0, 255)


def plate_of(w, h):
    """lib/sharecard.js drawingRect(w, h): (x, y, w, h) in the 1200 x 630 card."""
    sc = min(1092 / w, 492 / h)
    dw, dh = int(w * sc + 0.5), int(h * sc + 0.5)
    return int((1200 - dw) / 2 + 0.5), int((546 - dh) / 2 + 0.5), dw, dh


def share_card(w, h):
    if Image is None:
        return None
    x, y, dw, dh = plate_of(w, h)
    im = Image.new("RGB", (1200, 630), CARD_GROUND)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 546, 1199, 629], fill=CARD_FOOT)
    d.rectangle([x, y, x + dw - 1, y + dh - 1], fill=(246, 242, 234), outline=CARD_LINE, width=3)
    for mx, my in ((x + 14, y + 14), (x + dw - 54, y + 14), (x + 14, y + dh - 54), (x + dw - 54, y + dh - 54)):
        d.rectangle([mx, my, mx + 39, my + 39], fill=CARD_MARK)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def make_post(who, words, gallery=False, flip=False, seed=0, size=(816, 612), card=False):
    """A post as the composer sends one: (status, answer). `card`: with a
    share card (share_card), as the editors' Add hands one back."""
    c = who.client()
    c.get("/social/")
    body = drawing(seed=seed, flip=flip, size=size)
    if card:
        body["thumbnail"] = share_card(*size)
    if gallery:
        body["visibility"] = "public"
        body["caption"] = "From the gallery tick"
    return c.post_json("/social/posts", {"words": words, "payload": body})


def post_row(public_id):
    got = db("select p.words, p.skribl_id, pe.handle from social_posts p join social_people pe on pe.id = p.person_id"
             " where p.public_id = ?", (public_id,))
    return got[0] if got else None


def skribl_row(public_id):
    got = db("select visibility, title, caption, user_id, kind from skribl_posts where public_id = ?", (public_id,))
    return got[0] if got else None


class InFrame:
    """artdraw's page, for an editor in an iframe: the pen goes in at the top
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


def editor_frame(pg, needle, timeout=30):
    """The editor (needle: its address) over the page, once it can be drawn on."""
    end = time.time() + timeout
    while time.time() < end:
        fr = next((f for f in pg.frames if needle in (f.url or "") and "compose=1" in (f.url or "")), None)
        if fr:
            try:
                fr.wait_for_function("() => !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip))",
                                     timeout=1000)
                return fr
            except Exception:
                pass
        pg.wait_for_timeout(200)
    return None


S = artdraw.Stroke
CIRCLE = [S([(354 + 150 * math.cos(a / 10), 300 + 130 * math.sin(a / 10)) for a in range(0, 64)], "gesture",
            artdraw.INK, size=16),
          S([(300, 280), (312, 292)], "detail", artdraw.PURPLE, size=14),
          S([(400, 280), (412, 292)], "detail", artdraw.PURPLE, size=14)]


def add_from_pad(pg, fr, tick=False):
    """Draw, end the take, and press Add (with or without the gallery tick)."""
    fr.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); setTool('pen');"
                " if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
    artdraw.draw(InFrame(pg, fr), CIRCLE, tempo=2.5, pause_tempo=3)
    pg.wait_for_timeout(400)
    if fr.evaluate("() => typeof recording !== 'undefined' && !!recording"):
        fr.click("#recordBtn")
        pg.wait_for_timeout(400)
    fr.click("#postBtn")
    pg.wait_for_timeout(700)
    sheet = fr.evaluate("""() => ({ label: (document.getElementById('postSubmitLabel') || {}).textContent,
      tick: [...document.querySelectorAll('#postSheet label')].map(l => l.textContent.trim())
              .filter(t => /gallery/i.test(t)),
      box: !!document.getElementById('postPublicInput'),
      speed: (() => { const g = document.getElementById('postSpeedSeg'); return !!g && g.getClientRects().length > 0; })() })""")
    if tick:
        fr.evaluate("() => { const b = document.getElementById('postPublic') || document.querySelector('#postSheet input[type=checkbox]');"
                    " if (b && !b.checked) b.click(); }")
    fr.click("#postSubmitBtn")
    pg.wait_for_timeout(1400)
    return sheet


# ---- what is painted: the site's own reader (verify_socialprofile's) ------------
READ = """(sel) => {
  const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return m.length >= 3 ? [m[0], m[1], m[2], m.length > 3 ? m[3] : 1] : null; };
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
  const roots = [...document.querySelectorAll(sel || 'main, header.top, nav.nav')];
  roots.forEach(root => root.querySelectorAll('*').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
    const c = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;
    const g = ground(e), col = over(rgba(getComputedStyle(e).color), g), k = ratio(col, g);
    out.read++;
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 30) + '" ' + k.toFixed(2));
  }));
  document.querySelectorAll('a[href], button, input, textarea, select, [role=button]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    if (sel && !e.closest(sel)) return;
    if (e.matches('input[type=radio]')) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    // A pill's option (Home's Following | Everyone: follows) is 36px to see and
    // 44px to a finger, by its band: it counts when a press at its middle and
    // 21px above and below lands on it.
    if (e.matches('.fo-seg > button')) { const mid = r.left + r.width / 2, hit = d => { const x = document.elementFromPoint(mid, r.top + r.height / 2 + d); return !!x && (x === e || e.contains(x)); }; if (r.width >= 44 && hit(0) && hit(-21) && hit(21)) return; }
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

STATE = """() => { const p = window.SkriblInline ? SkriblInline.players() : [];
  return p.map(x => x.state().state); }"""

# A LIST OF CHOICES IS ONE CARD (section 16). Every list of rows in the sheet
# `root` (a ⋯'s .post-acts, Report's .post-reasons): its colour, its corners
# and its box; and each row that shows (Sign out's form is a row, its button
# its face): its words (a mute row's name), whether it is a risky one, what is
# behind its words (its own background), the room between it and the row
# before, the line along its top, its box, and whether it is what is painted
# at its middle. And the Cancel and Send report painted in the sheet.
ONECARD = r"""(root) => {
  const R = document.querySelector(root); if (!R) return null;
  const shown = e => e.getClientRects().length > 0;
  const hit = (e, x, y) => { const at = document.elementFromPoint(x, y); return !!at && (at === e || e.contains(at)); };
  const lists = [...R.querySelectorAll('.post-acts, .post-reasons')].filter(shown).map(l => {
    const cs = getComputedStyle(l), lr = l.getBoundingClientRect();
    let prev = null;
      const thin = (x, c) => { if (c.borderTopWidth !== '0px' && c.borderTopColor !== 'rgba(0, 0, 0, 0)') return 'border ' + c.borderTopWidth + ' ' + c.borderTopColor;
        const bb = getComputedStyle(x, '::before');
        if (!bb.content || bb.content === 'none' || bb.content === 'normal' || bb.display === 'none') return 'none';
        const m = bb.transform === 'none' ? 1 : new DOMMatrix(bb.transform).d;
        return { color: bb.backgroundColor, from: Math.round(parseFloat(bb.left) * 10) / 10, to: Math.round(parseFloat(bb.right) * 10) / 10,
                 px: Math.round(parseFloat(bb.height) * m * devicePixelRatio * 100) / 100 }; };
      const wordsAt = (x) => { const w = document.createTreeWalker(x, NodeFilter.SHOW_TEXT); let n;
        while ((n = w.nextNode())) { if (!n.textContent.trim()) continue; const g = document.createRange(); g.selectNodeContents(n);
          const b = g.getBoundingClientRect(); if (b.width) return Math.round((b.left - x.getBoundingClientRect().left) * 10) / 10; }
        return null; };
    const rows = [...l.children].filter(x => shown(x) && !x.matches('legend')).map(x => {
      const q = x.getBoundingClientRect(), c = getComputedStyle(x);
      const face = x.matches('form') ? x.querySelector('.post-act') : x;
      const out = { words: (x.querySelector('.mu-words b') || x.querySelector('.who-head') || x).textContent.trim().replace(/\s+/g, ' ').slice(0, 32),
        risky: x.matches('.is-danger') || !!x.querySelector('.is-danger'), own: getComputedStyle(face).backgroundColor,
        gap: prev ? Math.round((q.top - prev.bottom) * 10) / 10 : null,
        line: thin(x, c), words_at: wordsAt(x),
        left: q.left, right: q.right, mid: (q.top + q.bottom) / 2, painted: hit(x, q.left + q.width / 2, (q.top + q.bottom) / 2) };
      prev = q; return out; });
    return { bg: cs.backgroundColor, r: [cs.borderTopLeftRadius, cs.borderBottomRightRadius],
             top: lr.top, bottom: lr.bottom, left: lr.left, right: lr.right, rows };
  });
  const said = t => [...R.querySelectorAll('button, a')].filter(b => shown(b) && b.textContent.trim() === t).length;
  return { lists, cancel: said('Cancel'), send: said('Send report') }; }"""

def thin_ok(row, colour, end):
    """The line over a row, Apple's way (the owner's "Apple's thin line",
    Nov 14): its own thin line and no top border, in --row-line, from where
    the row's words start (to the pixel) to `end` px before the card's edge,
    one screen pixel tall at the screen's own scale."""
    line = row.get("line")
    return (isinstance(line, dict) and line["color"] == colour and row.get("words_at") is not None
            and abs(line["from"] - row["words_at"]) <= 1 and abs(line["to"] - end) <= 0.5 and abs(line["px"] - 1) <= 0.05)


# The tokens those roles wear, as the page resolves them: a card on a sheet
# (--row-bg, --menu-card), the sheet's paper (--sheet-paper), the line
# between two rows (--rule, --menu-card-rule).
TOKENS16 = """() => { const p = document.createElement('i'); document.body.appendChild(p);
  const read = v => { p.style.color = 'var(' + v + ')'; return getComputedStyle(p).color; };
  const o = { row: read('--row-bg'), paper: read('--sheet-paper'), rule: read('--rule'), rowline: read('--row-line') }; p.remove(); return o; }"""

# A finger on a sheet: down 60px from its top, moved by each of `dys` in turn,
# `every` ms apart, and lifted (verify_social's, for any sheet).
SWIPE16 = """([sel, dys, every]) => new Promise(res => { const s = document.querySelector(sel), r = s.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + 60;
  const fire = (type, yy) => { const t = new Touch({ identifier: 7, target: s, clientX: x, clientY: yy });
    const end = type === 'touchend';
    s.dispatchEvent(new TouchEvent(type, { touches: end ? [] : [t], targetTouches: end ? [] : [t], changedTouches: [t],
                                           bubbles: true, cancelable: true, view: window })); };
  fire('touchstart', y);
  let i = 0;
  (function step() { if (i < dys.length) { fire('touchmove', y + dys[i++]); setTimeout(step, every); }
                     else { fire('touchend', y + dys[dys.length - 1]); setTimeout(res, 700); } })(); })"""

# A drawing posted from the Pad on its own page (Make's Draw), as the Pad posts
# it: Skribl's API, as the person signed in (or nobody), its own token from its
# own cookie (sections 9 and 10).
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

# The same, on a ground and a canvas of its own: the Pad's dark is its own
# default (section 13, the box wears the drawing's own ground).
PAD_ON = """async ([title, ground, w, h, seed]) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const pts = Array.from({ length: 30 }, (_, i) => ({ x: w / 2 + Math.cos((i + seed) / 4) * 90, y: 120 + i * (h - 240) / 29,
    color: '#7c5cff', size: 8, t: i * 30, start: i === 0 }));
  const r = await fetch('/api/skribls', { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) },
    body: JSON.stringify({ title, visibility: 'public', version: 2, schemaVersion: 2, playbackMode: 'replay',
      canvasSize: { cssWidth: w, cssHeight: h }, frames: [{ strokes: pts, strokeGroups: [pts.length], background: { color: ground } }] }) });
  const j = await r.json().catch(() => ({})); return [r.status, j.id || null]; }"""

# A tile's box and what is painted beside its plate (the bars of a drawing
# whose shape is not the box's), read off the paint: the box's place, and the
# middle of each bar, in the box's own picture's pixels (2 per CSS pixel).
BARS = """(sel) => { const t = document.querySelector(sel); if (!t) return null;
  t.scrollIntoView({ block: 'center', behavior: 'instant' });
  const box = t.querySelector('.gal-pic, .more-pic'), plate = t.querySelector('.gal-plate, .more-plate');
  const d = t.querySelector('.gal-dur'); if (d) d.style.visibility = 'hidden';
  const b = box.getBoundingClientRect(), p = plate ? plate.getBoundingClientRect() : b;
  return { left: (p.left - b.left) / 2, right: (b.right + p.right) / 2 - b.left, y: b.height / 2,
           bars: [Math.round(p.left - b.left), Math.round(b.right - p.right)], ground: box.getAttribute('style') }; }"""

# A CARD'S WAYS IN (section 10), read off what is painted: each link's box, and
# whether a tap anywhere in it (its middle and its four corners) lands on it,
# not on something laid over it; where a tap on the @handle lands; and the
# card's own rhythm (the time on the @handle's line, the words and the drawing
# 12px under the header), so making them links moved nothing.
WAYS = """(key) => {
  const c = document.querySelector('.post-card[data-post="' + key + '"]') || document.querySelector('.post-card[data-skribl="' + key + '"]');
  if (!c) return null;
  c.scrollIntoView({ block: 'center' });
  // Where a tap lands at the link's middle and its four corners (1px in): on
  // the link itself, the drawing, another link (its address), or the card.
  const landing = a => { const r = a.getBoundingClientRect();
    return [[r.left + r.width / 2, r.top + r.height / 2], [r.left + 1, r.top + 1], [r.right - 1, r.top + 1],
            [r.left + 1, r.bottom - 1], [r.right - 1, r.bottom - 1]]
      .map(([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return null;
        if (e.closest('.post-art')) return 'drawing'; const l = e.closest('a, button');
        return l === a ? 'self' : l ? (l.getAttribute('href') || l.className) : 'card'; }); };
  const one = sel => { const a = c.querySelector(sel); if (!a) return null; const r = a.getBoundingClientRect(), p = landing(a);
    // Sizes as the census reads them: never rounded up (43.99 is under 44).
    return { tag: a.tagName.toLowerCase(), href: a.getAttribute('href'), w: Math.floor(r.width * 100) / 100,
             h: Math.floor(r.height * 100) / 100, lands: p.every(x => x === 'self'), at: p,
             label: a.getAttribute('aria-label'), text: a.textContent.trim(), icon: !!a.querySelector('svg') }; };
  const text = (root, needle) => { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
      const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g.getBoundingClientRect(); } }
    return null; };
  const head = c.querySelector('.post-head').getBoundingClientRect();
  const handle = text(c.querySelector('.post-head'), '@' + c.dataset.handle);
  const when = c.querySelector('time').getBoundingClientRect();
  const at = handle ? document.elementFromPoint(handle.left + handle.width / 2, handle.top + handle.height / 2) : null;
  const wl = c.querySelector('.post-words'), art = c.querySelector('.post-art').getBoundingClientRect();
  const pad = wl ? parseFloat(getComputedStyle(wl).paddingTop) : 0, wr = wl ? wl.getBoundingClientRect() : null;
  const r1 = v => Math.round(v * 10) / 10;
  return { words: one('.post-words'), when: one('.post-when'), count: one('.post-count'), name: one('.post-name'),
           face: one('.post-face'), handle: at && at.closest('a') ? at.closest('a').getAttribute('href') : null,
           sameLine: !!handle && Math.abs(when.top - handle.top) < 1 && when.left > handle.right, headH: r1(head.height),
           wordsGap: wr ? r1(wr.top + pad - head.bottom) : null,
           artGap: r1(art.top - (wr ? wr.bottom - parseFloat(getComputedStyle(wl).paddingBottom) : head.bottom)) }; }"""


# THE TAP MAP (section 12; Cal's map of the owner's "I thought on card?",
# Nov 13): every `step` px of a card, what a tap there lands on, read as a
# phone has it. Each row is scrolled to the screen's middle, clear of the bars
# at the top and the foot, at the phone's own height (a drawing's box is sized
# by it: inlineplayer.css, min(70vh, 640px)), and read with elementFromPoint:
# one of the card's own controls (a link, a button, a role, a tab stop: it
# does its own job), or the card's ground, keyed by the element itself, so
# each part of the ground can be tapped for what it does. Off the card (past
# its round corners) is not the card's.
# WHERE A HOST SAYS SKRIBL'S CARDS OPEN, as the site's pages said it (app.py's
# card_url: /social/b/__ID__) on the section's root, put there as the page is
# read, before gallery.js (deferred) reads it: what a host's page sends, which
# verify_hostseams holds, here for gallery.js to act on (section 12).
SITE_OPENS = """(() => { const put = () => { const r = document.getElementById('skriblGallery');
    if (r && !r.hasAttribute('data-skribl-open')) r.setAttribute('data-skribl-open', '/social/b/__ID__'); return !!r; };
  if (put()) return; const o = new MutationObserver(() => { if (put()) o.disconnect(); });
  o.observe(document, { childList: true, subtree: true }); })();"""

TAPMAP = """([sel, step]) => {
  const card = document.querySelector(sel);
  if (!card) return null;
  const OWN = 'a, button, input, textarea, select, label, summary, [role="button"], [role="slider"], [role="group"], [tabindex]';
  const name = e => e.tagName.toLowerCase() + (e.classList.length ? '.' + e.classList[0] : '');
  const spacer = document.createElement('div');
  spacer.style.height = '100vh';
  document.body.appendChild(spacer);
  const box = card.getBoundingClientRect(), top = box.top + scrollY, left = box.left, mid = innerHeight / 2;
  const keys = {}, grid = [];
  for (let y = 1; y < box.height - 1; y += step) {
    window.scrollTo({ top: top + y - mid, behavior: 'instant' });
    const vy = top + y - scrollY, row = [];
    for (let x = 1; x < box.width - 1; x += step) {
      const e = document.elementFromPoint(left + x, vy);
      let k = 'off';
      if (e && card.contains(e)) {
        const own = e.closest(OWN);
        k = own && card.contains(own) ? 'own|' + name(own) : 'ground|' + name(e);
      }
      keys[k] = (keys[k] || 0) + 1;
      row.push(k);
    }
    grid.push(row);
  }
  spacer.remove();
  return { w: box.width, h: box.height, keys, grid };
}"""

# Where a point of a card (its own px, as TAPMAP read it) is on the screen,
# once it is scrolled to the screen's middle as TAPMAP read it.
AIM = """([sel, x, y]) => { const c = document.querySelector(sel); if (!c) return null;
  const b = c.getBoundingClientRect();
  window.scrollTo({ top: b.top + scrollY + y - innerHeight / 2, behavior: 'instant' });
  const r = c.getBoundingClientRect(); return [r.left + x, r.top + y]; }"""


def inmost(grid, key, step):
    """A point of `key`'s part of the map that is as far inside it as any:
    every neighbour the same part where the part has such points, and of
    those the nearest its middle. In the card's own px."""
    pts = [(i, j) for j, row in enumerate(grid) for i, k in enumerate(row) if k == key]
    inner = [(i, j) for i, j in pts
             if all(0 <= j + dj < len(grid) and 0 <= i + di < len(grid[0]) and grid[j + dj][i + di] == key
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    use = inner or pts
    cx, cy = sum(i for i, _ in use) / len(use), sum(j for _, j in use) / len(use)
    i, j = min(use, key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
    return 1 + i * step, 1 + j * step


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "Home, signed in: no box at the top, Make opens the composer, an empty feed said kindly; Post with nothing drawn"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        sent = []
        pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and r.url.endswith("/social/posts") else None)
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        home = pg.evaluate("""() => ({ box: document.querySelectorAll('[data-compose-row], [data-compose-go]').length,
          none: (document.querySelector('[data-feed-none]') || {}).textContent || null,
          hello: !!document.querySelector('.hello') })""")
        pg.click("nav.nav .tab-make")
        pg.wait_for_timeout(700)
        sheet = pg.evaluate("""() => ({ open: document.getElementById('composeSheet').classList.contains('is-open'),
          field: document.activeElement === document.querySelector('#composeSheet .make-sheet') })""")
        # The button's own click: a sheet that never opened is this row's red,
        # not a stop at a hidden button.
        pg.evaluate("() => document.querySelector('#composeSheet [data-compose-post]').click()")
        pg.wait_for_timeout(300)
        said = pg.evaluate("() => document.querySelector('#composeSheet [data-compose-say]').textContent")
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/")
        npg.wait_for_timeout(400)
        nobody = npg.evaluate("() => ({ hello: !!document.querySelector('.hello'), composer: !!document.querySelector('[data-compose-row], #composeSheet') })")
        close_ctx(nctx, npg)
        check("Home signed in has no box at the top (the owner's \"All yes\", Nov 14): Make opens the composer, on a"
              " touch phone calm, focus on the sheet itself; an empty feed says to tap Make, kindly; there Post with nothing said or drawn says what is"
              " missing and sends nothing; signed out, Home is the first visit, as before",
              home["box"] == 0 and sheet == {"open": True, "field": True}
              and home["none"] == "No posts yet. Tap the pencil to share your first one."
              and not home["hello"] and said == "Say something or draw something first, then Post." and not sent
              and nobody["hello"] and not nobody["composer"],
              f"home {home}; sheet {sheet}; said {said!r}; posted {len(sent)}; signed out {nobody}")

    # ------------------------------------------------------------------ 2
    if part(2, "composing from Home: the Pad over the composer, Add hands the drawing back, Edit and Remove; Flip opens Flip"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        pg.click("nav.nav .tab-make")
        pg.wait_for_timeout(700)
        pg.click("#composeSheet [data-compose-open=pad]")
        fr = editor_frame(pg, "skribl-pad")
        src = pg.evaluate("() => document.querySelector('#composePad iframe').getAttribute('src')")
        sheet = add_from_pad(pg, fr) if fr else {}
        drafted = pg.evaluate("""() => { const d = document.querySelector('[data-compose-draft]');
          const box = d && d.querySelector('[data-skribl-inline]');
          return { shown: !!d && !d.hidden, attached: !!(box && box._skriblInline),
                   chips: [...document.querySelectorAll('#composeSheet [data-compose-open]')].map(c => c.hidden),
                   overlay: document.getElementById('composePad').hidden,
                   focus: document.activeElement ? document.activeElement.textContent.trim() : null }; }""")
        loads = []
        pg.evaluate("""() => { window.__loads = 0; const f = document.querySelector('#composePad iframe');
          f.contentWindow.addEventListener('message', e => { if (e.data && e.data.type === 'skribl:compose:load') window.__loads++; }); }""")
        pg.click("#composeSheet [data-compose-edit]")
        pg.wait_for_timeout(900)
        reopened = pg.evaluate("() => ({ open: !document.getElementById('composePad').hidden, loads: window.__loads })")
        fr2 = editor_frame(pg, "skribl-pad")
        if fr2:
            fr2.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        pg.click("#composeSheet [data-compose-remove]")
        pg.wait_for_timeout(400)
        removed = pg.evaluate("""() => ({ draft: document.querySelector('[data-compose-draft]').hidden,
          chips: [...document.querySelectorAll('#composeSheet [data-compose-open]')].map(c => c.hidden),
          frame: document.querySelector('#composePad iframe').getAttribute('src') })""")
        # NO GALLERY TICK (the walkthrough's mocks, choice 2, the owner's "all
        # yes", Nov 19): the site asked the editors for "Show in the Skribls
        # gallery" (gallery=1), which fed Skribl's own gallery and said "Off,
        # it shows in your post only" of a site whose Gallery shows every
        # post's drawing. Read by the mechanism: the flag in the frame's
        # address and the sheet's own checkbox, and "Viewers start at" still
        # asked. (Not by the word: the gallery caption's field is in every
        # sheet, hidden, and its label says "Gallery". This row's first
        # version asked for no label with that word and failed on it.)
        check("Home's Draw opens Skribl's Pad over the composer in compose mode, asking for no gallery tick (compose=1,"
              " no gallery=1): its sheet says Add to post, holds no gallery checkbox and still asks Viewers start at;"
              " Add hands the drawing back into the composer's own in-post player, Draw and Flip still along its foot"
              " (a post holds one: they say so), and focus lands on Edit drawing",
              bool(fr) and "compose=1" in (src or "") and "gallery=1" not in (src or "")
              and sheet.get("label") == "Add to post" and sheet.get("box") is False
              and sheet.get("speed") is True
              and drafted["shown"] and drafted["attached"] and drafted["chips"] == [False, False] and drafted["overlay"]
              and drafted["focus"] == "Edit drawing",
              f"src {src}; sheet {sheet}; drafted {drafted}")
        check("Edit drawing reopens the Pad with the drawing put back in it (a load message); Remove takes the"
              " drawing away, Draw and Flip there, and the frame is let go (about:blank)",
              reopened["open"] and reopened["loads"] >= 1
              and removed["draft"] and removed["chips"] == [False, False] and removed["frame"] == "about:blank",
              f"reopened {reopened}; removed {removed}")
        pg.click("#composeSheet [data-compose-open=flip]")
        ffr = editor_frame(pg, "/flip?")
        fsrc = pg.evaluate("() => document.querySelector('#composeFlip iframe').getAttribute('src')")
        fopen = pg.evaluate("() => !document.getElementById('composeFlip').hidden")
        if ffr:
            ffr.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        check("Flip opens Skribl's Flip over the composer the same way (compose=1, no gallery=1), and its × puts it away",
              bool(ffr) and fopen and "compose=1" in (fsrc or "") and "gallery=1" not in (fsrc or "")
              and pg.evaluate("() => document.getElementById('composeFlip').hidden"),
              f"frame {bool(ffr)}; src {fsrc}; open {fopen}")

    # ------------------------------------------------------------------ 3
    if part(3, "posting: one post, its row and its skribl together; its page plays by itself"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        pg.click("nav.nav .tab-make")
        pg.wait_for_timeout(700)
        pg.click("#composeSheet [data-compose-open=pad]")
        fr = editor_frame(pg, "skribl-pad")
        if fr:
            add_from_pad(pg, fr)
        pg.fill("#composeSheet [data-compose-words]", "Day 12. The beard took longer than the skull.\nWatch it at 2×.")
        try:
            with pg.expect_navigation(timeout=30000):
                pg.click("#composeSheet [data-compose-post]")
        except Exception as exc:
            ERRS.append(f"post did not go: {str(exc).splitlines()[0][:100]}")
        pg.wait_for_timeout(1500)
        url = pg.evaluate("() => location.pathname")
        pid = url.rsplit("/", 1)[-1]
        row = post_row(pid)
        sk = skribl_row(row[1]) if row else None
        page = pg.evaluate("""() => ({ words: (document.querySelector('.post-words') || {}).textContent,
          meta: (document.querySelector('.post-meta') || {}).textContent,
          comments: !!document.getElementById('comments'), label: (l => !!l && !l.hidden)(document.getElementById('commentsTitle')),
          line: (document.querySelector('.ans-bar .cm-say') || {}).textContent || null,
          box: !!document.querySelector('[data-cm-box]') })""")
        playing = pg.evaluate(STATE)
        check("Post sends the words and the drawing as one post: the post's own page, its row (the words as typed,"
              " the person), its skribl through create_post (unlisted without the tick, its title the first words,"
              " no caption, the person its author)",
              url.startswith("/social/p/") and row is not None and row[0] == "Day 12. The beard took longer than the skull.\nWatch it at 2×."
              and row[2] == "mira" and sk is not None and sk[0] == "unlisted"
              and sk[1] == "Day 12. The beard took longer than the skull." and not sk[2]
              and sk[3] == db("select public_id from social_people where handle = 'mira'")[0][0],
              f"url {url}; row {row}; skribl {sk}")
        check("the post's own page plays its drawing by itself, its words, when, the answer bar (\"Say something…\") and"
              " its comments' place, with no heading over it while there are none (phase 2: verify_socialcomments holds"
              " them)",
              playing[:1] == ["playing"] and page["words"] == "Day 12. The beard took longer than the skull.\nWatch it at 2×."
              and " at " in (page["meta"] or "")
              and page["comments"] and not page["label"] and page["line"] == "Say something…" and page["box"],
              f"players {playing}; page {page}")
        rctx, rpg = browser_as(b, mira, reduced=True)
        rpg.goto(BASE + url)
        rpg.wait_for_timeout(1500)
        still = rpg.evaluate(STATE)
        close_ctx(rctx, rpg)
        st, j = make_post(mira, "For the gallery", gallery=True, seed=3)
        gsk = skribl_row(post_row(j.get("post"))[1]) if st == 200 and isinstance(j, dict) else None
        listed = json.loads(urllib.request.urlopen(BASE + "/api/skribls?limit=50", timeout=20).read().decode())["items"]
        check("under Reduce Motion the post's page leaves the drawing still; a payload that says public (the gallery"
              " tick, which the composer no longer asks for) is kept public with its caption, and Skribl's own listing"
              " shows it",
              still and still[0] != "playing" and gsk is not None and gsk[0] == "public"
              and gsk[2] == "From the gallery tick"
              and any(i["id"] == post_row(j["post"])[1] for i in listed),
              f"reduced {still}; gallery skribl {gsk}; status {st}")

        # NO "MAKE YOUR OWN" ON A POST'S PAGE (the owner's "Yes, remove it", Nov
        # 14): it was the bar's Make by another name, the same sheet. Make stays
        # in the bar (a touch phone) and the rail (a desk), and opens its sheet
        # there, on the post's own page.
        makes = {}
        for screen in ("phone", "desk"):
            mctx, mpg = browser_as(b, mira, screen, "light")
            try:
                mpg.goto(BASE + url)
                mpg.wait_for_timeout(600)
                here_ = mpg.evaluate("""() => ({ inPage: document.querySelectorAll('main [data-make]').length,
                  words: [...document.querySelectorAll('main button, main a')].filter(e => /make your own/i.test(e.textContent)).length,
                  bar: [...document.querySelectorAll('nav.nav [data-make]')].filter(e => e.getClientRects().length).length })""")
                if screen == "phone":
                    mpg.locator("nav.nav .tab-make").tap()
                else:
                    mpg.locator("nav.nav .tab-make").click()
                mpg.wait_for_timeout(700)
                here_["sheet"] = mpg.evaluate("""() => { const w = document.getElementById('composeSheet');
                  return !!w && !w.hidden && w.classList.contains('is-open'); }""")
                makes[screen] = here_
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                makes[screen] = {"stopped": str(exc).splitlines()[0][:120]}
            close_ctx(mctx, mpg)
        check("a post's own page has no Make your own (no make button in the page, phone and desk); the bar's Make on a"
              " touch phone and the rail's on a desk is there and opens the composer on it",
              all(makes.get(k) == {"inPage": 0, "words": 0, "bar": 1, "sheet": True} for k in ("phone", "desk")),
              json.dumps(makes))

        # NO MORE FROM ON A POST'S OWN PAGE (the Calm Post Page; the owner, Nov
        # 20, beside Bluesky's: "looks simpler. Most because there aren't the
        # more from images", then "All yes to everything"): on a page about one
        # drawing it started a second conversation; their face and name open
        # their page. Mira has two other drawings here, which More from showed
        # until then (each cut out of its share card: the same plate now reads
        # off the paint in the Gallery, section 13, and on a draw-back's tile,
        # verify_socialdrawback 6). Asked as gone, in the page and its source.
        tall, wide = (531, 944), (816, 612)
        others = []
        for words, size in (("Card, tall", tall), ("Card, wide", wide)):
            st_, j_ = make_post(mira, words, seed=7, size=size, card=True)
            others.append(j_.get("post") if st_ == 200 and isinstance(j_, dict) else None)
        gone3 = {}
        for screen in ("phone", "desk"):
            dctx, dpg = browser_as(b, mira, screen, "light")
            dpg.goto(BASE + url)
            dpg.wait_for_timeout(900)
            gone3[screen] = dpg.evaluate("""(others) => { const page = document.querySelector('.post-page');
              return { section: document.querySelectorAll('.more-from, .more-grid, .more-tile, #moreTitle').length,
                       links: others.filter(id => !!page.querySelector('a[href="/social/p/' + id + '"]')).length,
                       said: /More from/.test(document.body.innerText),
                       last: page.lastElementChild ? page.lastElementChild.id || page.lastElementChild.className : null }; }""", others)
            close_ctx(dctx, dpg)
        source3 = mira.client().get(url)[1]
        check("a post's own page has no More from: no section, no tile and no link to its author's two other drawings, the"
              " page ending with its comments (a phone and a desk); nothing of it in the page's source either",
              all(others) and all(v == {"section": 0, "links": 0, "said": False, "last": "comments"} for v in gone3.values())
              and "More from" not in source3 and "more-from" not in source3 and not any(o in source3 for o in others),
              json.dumps({"others": others, **gone3, "in the source": [w for w in ("More from", "more-from") if w in source3]}))

    # ------------------------------------------------------------------ 4
    if part(4, "the feed: everyone's, newest first, still until tapped; Load more in place"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        made = []
        for i in range(23):
            who = juno if i % 2 else mira
            st, j = make_post(who, f"Feed post {i:02d}", seed=i)
            made.append(j.get("post") if isinstance(j, dict) else None)
            time.sleep(0.01)
        pg = juno.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(1200)
        first = pg.evaluate("""() => [...document.querySelectorAll('.post-card')].map(c => ({ id: c.getAttribute('data-post'),
          name: c.querySelector('.post-name').textContent, href: c.querySelector('.post-name').getAttribute('href'),
          when: c.querySelector('time').textContent, words: (c.querySelector('.post-words') || {}).textContent }))""")
        idle = pg.evaluate(STATE)
        # THE ROW under every card (the reposts mock, the owner's "All yes", Nov 14):
        # the 💬, the repost (nothing reposted: no count, "Repost"), the heart and
        # the ⋯; Share is in the ⋯. No Open › (the owner's "completely remove
        # open", Nov 19): a tap on the card's ground opens it. DRAW BACK's pen
        # (Nov 19) after the heart, for Juno, signed in, under every drawing here.
        rows4 = pg.evaluate("""() => [...document.querySelectorAll('.post-card .post-row')].map(r => [...r.children].map(e =>
          e.classList.contains('db-pen') ? 'pen' : e.classList.contains('post-count') ? 'comment' : e.classList.contains('rp-btn') ? 'repost:' + e.getAttribute('aria-label')
          : e.classList.contains('lk-heart') ? 'heart' : e.classList.contains('post-share') ? 'share'
          : e.classList.contains('post-more') ? 'more' : e.classList.contains('post-open') ? 'open' : e.className).join(' '))""")
        cursor = pg.evaluate("() => document.querySelector('[data-feed-next]').getAttribute('data-feed-next')")
        try:
            raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        except Exception:
            raw = ""
        pg.click("[data-feed-next]")
        pg.wait_for_timeout(1500)
        after = pg.evaluate("""() => ({ n: document.querySelectorAll('.post-card').length,
          more: document.querySelector('[data-feed-next]').hidden,
          mounted: [...document.querySelectorAll('.post-card [data-skribl-inline]')].every(b => !!b._skriblInline) })""")
        newest = [x for x in reversed(made) if x][:20]
        total = db("select count(*) from social_posts")[0][0]
        check("Home's feed is everyone's posts, newest first, a page of 20: each name links to its person's page,"
              " its time is said (now), and every drawing waits for a tap",
              len(first) == 20 and [c["id"] for c in first] == newest
              and all(c["href"] in ("/social/@mira", "/social/@juno") for c in first)
              and all(c["when"] in ("now",) or c["when"].endswith("m") for c in first)
              and idle and all(s != "playing" for s in idle),
              f"{len(first)} cards; first {first[:2]}; idle {set(idle)}")
        check("the row under every card: the 💬, the repost (\"Repost\", none reposted), the heart, Draw back's pen"
              " and the ⋯, no Open ›; Share in the ⋯, not the row",
              rows4 and set(rows4) == {"comment repost:Repost heart pen more"}, json.dumps(sorted(set(rows4 or []))))
        check("Load more brings the rest in place, each player mounted, and goes away at the end; its cursor names"
              " a time and the card (p and a post's public id, or s and a drawing's), never an internal id",
              after["n"] == total and total > 20 and after["more"] and after["mounted"]
              and re.fullmatch(r"\d{16}\.[ps][A-Za-z0-9_-]{11}", raw or "") is not None,
              f"after {after} of {total}; cursor {raw!r}")

    # ------------------------------------------------------------------ 5
    if part(5, "the ⋯ sheet: yours and somebody else's; Report into the site's queue; Delete asked once"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(mira, "Mira's to report and delete", seed=40)
        pid = j.get("post") if isinstance(j, dict) else None
        skid = post_row(pid)[1] if pid else None
        pg = mira.pg
        pg.goto(BASE + f"/social/p/{pid}")
        pg.wait_for_timeout(800)
        pg.click(".post-page .post-row [data-post-menu]")
        pg.wait_for_timeout(600)
        mine = pg.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => (b.querySelector('.mu-words b') || b).textContent.trim())")
        pg.click("#postSheet [data-act=copy]")
        pg.wait_for_timeout(400)
        copied = pg.evaluate("() => document.querySelector('#postSheet [data-post-say]').textContent")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)
        jp = juno.pg
        jp.goto(BASE + f"/social/p/{pid}")
        jp.wait_for_timeout(800)
        jp.click(".post-page .post-row [data-post-menu]")
        jp.wait_for_timeout(600)
        theirs = jp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => (b.querySelector('.mu-words b') || b).textContent.trim())")
        jp.click("#postSheet [data-act=report]")
        jp.wait_for_timeout(800)
        rsheet = jp.evaluate("""() => ({ open: document.getElementById('reportSheet').classList.contains('is-open'),
          menu: document.getElementById('postSheet').classList.contains('is-open'),
          reasons: [...document.querySelectorAll('#reportSheet input[name=reason]')].map(i => [i.value, i.closest('label').textContent.trim()]) })""")
        jp.check("#reportSheet input[value=abuse]")
        jp.fill("#reportNote", "Testing the queue")
        jp.click("#reportSheet [data-report-send]")
        jp.wait_for_timeout(1200)
        thanks = jp.evaluate("() => document.querySelector('[data-report-say]').textContent")
        reported = db("select reason, note from social_reports where kind = 'post' and target = ?", (pid,))
        check("your own post's ⋯ says Bookmark (bookmarks), Pin to your page (pins), Copy link, Share…, Delete post;"
              " Copy link gives the link (or says it to copy by hand); somebody else's says Bookmark, Copy link,"
              " Share…, Mute @them (mutes), Report this post",
              mine == ["Bookmark", "Pin to your page", "Copy link", "Share…", "Delete post"]
              and theirs == ["Bookmark", "Copy link", "Share…", "Mute @mira", "Report this post", "Block @mira"]
              and (copied == "Link copied." or copied.startswith("Here’s the link to copy: " + BASE + f"/social/p/{pid}")),
              f"mine {mine}; theirs {theirs}; copied {copied!r}")
        check("Report this post rises as a sheet of its own with the Gallery's reasons and A child's safety, sends"
              " into the site's own queue (the reason, the note), and says thanks",
              rsheet["open"] and not rsheet["menu"]
              and rsheet["reasons"] == [["spam", "Spam or misleading"], ["abuse", "Abusive or hateful"],
                                        ["copyright", "Copies someone else’s work"],
                                        ["child_safety", "A child’s safety"], ["other", "Something else"]]
              and thanks == "Thanks. The people who run this site will look at it."
              and reported == [("abuse", "Testing the queue")],
              f"sheet {rsheet}; said {thanks!r}; queue {reported}")
        # A post deleted at the first tap leaves no sheet to read or close: the
        # steps after it say so in `ask` rather than stop the suite before
        # its row can say red (the calibration's "Delete without asking").
        ask, kept = {"open": False, "title": None}, False
        try:
            pg.goto(BASE + f"/social/p/{pid}")
            pg.wait_for_timeout(700)
            pg.click(".post-page .post-row [data-post-menu]")
            pg.wait_for_timeout(600)
            pg.click("#postSheet [data-act=delete]")
            pg.wait_for_timeout(700)
            ask = pg.evaluate("""() => { const s = document.getElementById('deleteSheet'), t = document.getElementById('deleteTitle');
              return { open: !!s && s.classList.contains('is-open'), title: t ? t.textContent : null,
                       at: location.pathname + location.search }; }""")
            pg.click("#deleteSheet .post-sheet-acts [data-make-close]", timeout=5000)
            pg.wait_for_timeout(600)
            kept = post_row(pid) is not None and skribl_row(skid) is not None
            pg.click(".post-page .post-row [data-post-menu]", timeout=5000)
            pg.wait_for_timeout(600)
            pg.click("#postSheet [data-act=delete]", timeout=5000)
            pg.wait_for_timeout(700)
            with pg.expect_navigation(timeout=20000):
                pg.click("[data-delete-now]", timeout=5000)
        except Exception as exc:
            ask["stopped"] = str(exc).splitlines()[0][:100]
        pg.wait_for_timeout(600)
        home = pg.evaluate("() => ({ url: location.pathname + location.search, note: (document.querySelector('.note') || {}).textContent })")
        st404, _ = mira.client().get(f"/social/p/{pid}")
        check("Delete post asks once (Keep it keeps it); then the words and the drawing both go, Home says so,"
              " and the post's address is a kind not-found",
              ask["open"] and ask["title"] == "Delete this post?" and "stopped" not in ask and kept
              and post_row(pid) is None and skribl_row(skid) is None
              and home["url"] == "/social/?note=deleted" and home["note"] == "Your post is gone, its drawing with it."
              and st404 == 404,
              f"ask {ask}; kept {kept}; after {home}; page {st404}")

    # ------------------------------------------------------------------ 6
    if part(6, "guards: token, sign-in, words, drawing, somebody else's post, the limit; deleting an account"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        c = mira.client()
        c.get("/social/")
        nb = Client()
        nb.get("/social/signin")
        answers = {
            "no token": c.post_json("/social/posts", {"words": "x", "payload": drawing()}, token=False)[0],
            "signed out": nb.post_json("/social/posts", {"words": "x", "payload": drawing()})[0],
            "too many words": c.post_json("/social/posts", {"words": "w" * 501, "payload": drawing()})[1],
            "hidden character": c.post_json("/social/posts", {"words": "hi‮you", "payload": drawing()})[1],
            "nothing": c.post_json("/social/posts", {"words": "  "})[1],
            "not a drawing": c.post_json("/social/posts", {"words": "x", "payload": "a drawing"})[1],
        }
        big = drawing(n=1800, seed=9)
        st_big, j_big = c.post_json("/social/posts", {"words": "A long drawing", "payload": big})
        size_big = len(json.dumps({"words": "A long drawing", "payload": big}))
        st, j = make_post(mira, "Not Juno's to delete", seed=60)
        pid = j.get("post")
        jc = juno.client()
        jc.get("/social/")
        st_other, j_other = jc.post_json(f"/social/p/{pid}/delete", {})
        check("a post is refused kindly without the page's token (403), signed out (401), with too many words or a"
              " hidden character, with nothing said or drawn, or with a drawing that is not one (400, each its own"
              " words), and nothing is posted; a post's body"
              " may be far past the site's 64 KiB; somebody else's post is not theirs to delete (404) and stays",
              answers["no token"] == 403 and answers["signed out"] == 401
              and isinstance(answers["too many words"], dict) and answers["too many words"].get("error") == "words_long"
              and isinstance(answers["hidden character"], dict) and answers["hidden character"].get("error") == "words_chars"
              and isinstance(answers["nothing"], dict) and answers["nothing"].get("error") == "empty"
              and isinstance(answers["not a drawing"], dict) and answers["not a drawing"].get("error") == "no_drawing"
              and st_big == 200 and size_big > 64 * 1024
              and st_other == 404 and post_row(pid) is not None,
              f"{answers}; big {st_big} at {size_big} bytes; another's delete {st_other}")
        counts = []
        tess = someone(b, "tess", "Tess Moreau")
        tc = tess.client()
        tc.get("/social/")
        for i in range(41):
            counts.append(tc.post_json("/social/posts", {"words": f"{i}", "payload": drawing(n=6, seed=i)})[0])
        check("posting is limited per person (40 an hour): the 41st is refused kindly (429), the 40 before it posted",
              counts[:40] == [200] * 40 and counts[40] == 429,
              f"{counts.count(200)} posted, then {counts[40:]}")
        nell = someone(b, "nell", "Nell Quist")
        ids = []
        for i in range(2):
            st, j = make_post(nell, f"Nell's {i}", seed=80 + i)
            ids.append(post_row(j["post"])[1])
        ncl = nell.client()
        _, page = ncl.get("/social/you/delete")
        listed = "Your posts (2): their words and their drawings" in page
        ncl._req("POST", "/social/you/delete", headers={"Content-Type": "application/x-www-form-urlencoded"},
                 raw=urllib.parse.urlencode({"csrf": ncl.token, "confirm": "nell"}).encode())
        gone = not db("select id from social_posts where skribl_id in (?, ?)", tuple(ids)) \
            and all(skribl_row(i) is None for i in ids)
        check("deleting an account says its posts go (and how many), and takes them: their words and drawings",
              listed and gone and not db("select id from social_people where handle = 'nell'"),
              f"said {listed}; posts and drawings gone {gone}")

    # ------------------------------------------------------------------ 7
    if part(7, "the new screens: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(juno, "Juno's, to look at", seed=90)
        pid = j.get("post")
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, mira, screen, scheme, reduced=True)
                cpg.goto(BASE + "/social/")
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "home")] = cpg.evaluate(READ, "main")
                cpg.goto(BASE + f"/social/p/{pid}")
                cpg.wait_for_timeout(800)
                seen[(screen, scheme, "post")] = cpg.evaluate(READ, None)
                cpg.click("[data-post-menu] >> visible=true")
                cpg.wait_for_timeout(600)
                seen[(screen, scheme, "menu")] = cpg.evaluate(READ, "#postSheet")
                cpg.click("#postSheet [data-act=report]")
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "report")] = cpg.evaluate(READ, "#reportSheet")
                close_ctx(ctx, cpg)
        low = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["low"]]
        small = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["small"]]
        fields = [f"{' '.join(k)}: {x}" for k, v in seen.items() for x in v["fields"]]
        reads = sum(v["read"] for v in seen.values())
        lowest = min(((v["lowest"], " ".join(k)) for k, v in seen.items()), default=(0, "nothing"))
        # Each screen read, not merely the lot: the fewest words each shows
        # with nothing else made (this section alone: Home 7, a post 13, its
        # ⋯ 5, Report 10), so a reader that missed a screen says so. It was a
        # total of 150 once, met only with the sections before it run first.
        # Home on a desk reads 5 since Open › came off every card (Nov 19, the
        # owner's "completely remove open"): its word was one of the six.
        FLOOR = {"home": 5, "post": 10, "menu": 4, "report": 8}
        # A post's page on a phone reads 7 this section alone since the phone's bar went to its icons alone
        # (Nov 15), their names for VoiceOver: the bar's words are a desk's alone now.
        FLOOR_PHONE = dict(FLOOR, post=6)
        check("every word on Home's composer and feed, a post's page, its ⋯ and Report reads at 4.5:1 or more on"
              " what is painted behind it, every control is 44px or more each way, every text field 16px: phone and"
              " desk, light and dark",
              all(v["read"] >= (FLOOR_PHONE if k[0] == "phone" else FLOOR)[k[2]] for k, v in seen.items())
              and not low and not small and not fields,
              f"{reads} read, the lowest {lowest}; under 4.5: {low[:4]}; small: {small[:4]}; fields: {fields[:3]};"
              f" each {[(' '.join(k), v['read']) for k, v in seen.items()]}")

    # ------------------------------------------------------------------ 9
    # HOME SHOWS POSTS ONLY (the map's step 3, its second part; the owner's
    # decision 2, Nov 13: "Drawings already shared without a post stay in their
    # author's Gallery, so nothing is lost: the Gallery shows them, and Home
    # shows posts from then on"). Until then Home held every drawing the site's
    # people showed in the gallery, posts or not; these rows held that, and
    # now hold its opposite, and what was kept: the drawing's own page, its
    # maker's page, its ⋯ and its Delete (and More from, until Nov 20).
    if part(9, "Home shows posts only: a drawing shown outside a post keeps its own page and its maker's, never Home"):
        from datetime import datetime, timezone
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        CARDS = """() => [...document.querySelectorAll('.post-card')].map(c => ({ id: c.getAttribute('data-post'),
          skribl: c.getAttribute('data-skribl'), url: c.getAttribute('data-url'),
          words: ((c.querySelector('.post-words') || {}).textContent || '') }))"""
        # A card as Home's JSON hands it over (Load more, the pill): its post and its drawing.
        CARD9 = re.compile(r'<article class="post-card" data-post="([^"]+)"[^>]*?data-skribl="([^"]+)"')

        def pad(who_pg, title, vis="public", seed=0):
            who_pg.goto(BASE + "/social/")
            return who_pg.evaluate(PAD, [title, vis, seed])

        def home_walk(cl, show="everyone", before=None):
            """Home's `show` as `cl` is sent it (the pill's first page, or Load
            more's from `before`), walked to its end with Load more: [(post, its
            drawing)] in order, or None where a page did not answer."""
            path = "/social/feed?" + ("before=" + urllib.parse.quote(before) if before else "show=" + show)
            seen = []
            for _ in range(80):
                st_, text = cl._req("GET", path)
                try:
                    j = json.loads(text)
                except ValueError:
                    return None
                if st_ != 200 or not isinstance(j, dict):
                    return None
                seen += CARD9.findall(j.get("html") or "")
                if not j.get("next"):
                    return seen
                path = "/social/feed?before=" + urllib.parse.quote(j["next"])
            return seen

        # What Mira shows: a post, a drawing from the Pad shown in the gallery
        # (no post), one kept unlisted, and a post with the gallery tick;
        # somebody not on the site shows one from Skribl's own Pad.
        st1, j1 = make_post(mira, "Section 9, a post", seed=91)
        time.sleep(0.02)
        st_s, shown = pad(mira.pg, "Section 9, shown from the Pad", "public", 1)
        time.sleep(0.02)
        st_u, kept = pad(mira.pg, "Section 9, kept unlisted", "unlisted", 2)
        nb_ctx, nb_pg = browser_as(b, None)
        nb_pg.goto(BASE + "/skribl-pad")
        nb_pg.wait_for_timeout(800)
        st_n, nobodys = nb_pg.evaluate(PAD, ["Section 9, nobody's", "public", 3])
        close_ctx(nb_ctx, nb_pg)
        time.sleep(0.02)
        st_g, jg = make_post(mira, "Section 9, a post shown in the gallery", gallery=True, seed=92)
        g_post = jg.get("post") if isinstance(jg, dict) else None
        g_skribl = post_row(g_post)[1] if g_post else None
        # Ines shares twenty-four posts, a drawing shown from the Pad after every
        # second one (no post), so every walk below crosses a page of Home's
        # twenty, even with this section alone. Somebody of her own: the site
        # takes forty posts an hour from one person, and Juno posts again in
        # sections 10 to 12.
        ines = someone(b, "ines", "Ines Varga")
        made, drawn = [], []
        for i in range(24):
            st, j = make_post(ines, f"Interleave post {i:02d}", seed=100 + i)
            made.append(j.get("post") if isinstance(j, dict) else None)
            time.sleep(0.02)
            if i % 2:
                st, sid = pad(ines.pg, f"Interleave drawing {i // 2:02d}", "public", 100 + i)
                drawn.append(sid)
                time.sleep(0.02)
        # Noor shares a post, then a drawing from the Pad on its own, shown in
        # the gallery (no post), then a post again, the same minute. Sora
        # follows her and she follows Sora, so each one's Following holds the
        # other's and their own (the read that asked Skribl for their drawings).
        noor = someone(b, "noor", "Noor Haddad")
        sora = someone(b, "sora", "Sora Lind")
        follows9 = []
        for x, y in ((sora, "noor"), (noor, "sora")):
            fc = x.client()
            fc.get(f"/social/@{y}")
            follows9.append(fc.post_json(f"/social/@{y}/follow", {"following": True})[0])
        st_pb, jb = make_post(noor, "Section 9, Noor's post before", seed=93)
        p_before = jb.get("post") if isinstance(jb, dict) else None
        time.sleep(0.02)
        st_l, lone = pad(noor.pg, "Section 9, Noor's drawing from the Pad", "public", 4)
        time.sleep(0.02)
        st_pa, jpa = make_post(noor, "Section 9, Noor's post after", seed=94)
        p_after = jpa.get("post") if isinstance(jpa, dict) else None
        made9 = ([st_s, st_u, st_n, st_l] == [201] * 4 and follows9 == [200, 200] and all(made) and all(drawn)
                 and all([j1.get("post") if isinstance(j1, dict) else None, g_post, p_before, p_after]))
        not_posts = {shown, kept, nobodys, lone, *drawn}
        posts9 = {r[0] for r in db("select public_id from social_posts")}
        oracle9 = [r[0] for r in db(
            "select p.public_id from social_posts p join social_people pe on pe.id = p.person_id"
            " where p.taken_down_at is null and pe.taken_down_at is null order by p.created_at desc, p.public_id desc")]
        walks = {"Noor's Following": home_walk(noor.client(), "following"),
                 "Noor's Everyone": home_walk(noor.client(), "everyone"),
                 "Sora's Following": home_walk(sora.client(), "following"),
                 "Sora's Everyone": home_walk(sora.client(), "everyone"),
                 "Juno's Everyone": home_walk(juno.client(), "everyone"),
                 "signed out": home_walk(Client(), "everyone")}
        st_h, noor_home = noor.client().get("/social/")
        bad9 = {k: [x for x in (v or []) if x[0] not in posts9 or x[1] in not_posts] for k, v in walks.items()}
        out_walk = [x[0] for x in walks["signed out"] or []]
        check("HOME SHOWS POSTS ONLY: a drawing shown in the gallery from the Pad outside a post is on nobody's Home,"
              " nor one kept unlisted or one by somebody not on the site: its maker's Following and Everyone, a"
              " follower's, somebody else's and signed out, each walked to its end with Load more, every card a post"
              " (signed out every post once, newest first, read against the database itself, so a post shown in the"
              " gallery shows once, as the post); the posts its maker shared the same minute are on every one of"
              " them, and on her Home as it opens",
              made9 and all(v is not None for v in walks.values()) and not any(bad9.values())
              and out_walk == oracle9 and out_walk.count(g_post) == 1 and len(out_walk) > 20
              and all({p_before, p_after} <= {x[0] for x in v} for v in walks.values() if v is not None)
              and st_h == 200 and lone not in noor_home and f'data-post="{p_after}"' in noor_home,
              f"made {made9}; cards {[(k, len(v) if v is not None else None) for k, v in walks.items()]}; not a post"
              f" or not one: {[(k, v[:2]) for k, v in bad9.items() if v]}; signed out is the database's"
              f" {out_walk == oracle9} ({len(out_walk)} of {len(oracle9)}); her Home {st_h}, the drawing on it"
              f" {lone in noor_home}")

        # ...AND NOTHING IS LOST: in the Gallery of everyone (every skribl
        # since Nov 14, section 13; until then posts only), a tile opening its
        # own page, and it keeps its own page and its maker's page (her
        # Gallery tab since the map's step 4, where it is a tile opening its
        # own page; verify_socialprofile section 16 holds the tab).
        gal9 = {}
        for name, cl, show in (("signed out", Client(), "everyone"), ("Sora's Everyone", sora.client(), "everyone"),
                               ("Sora's Following", sora.client(), "following")):
            st_, text = cl._req("GET", "/social/explore/more?sort=new&show=" + show)
            try:
                gal9[name] = json.loads(text).get("html") or ""
            except (ValueError, AttributeError):
                gal9[name] = ""
        own9 = {"signed out": Client().get(f"/social/b/{lone}"), "Sora": sora.client().get(f"/social/b/{lone}")}
        listed9 = {}
        for name, who_ in (("signed out", None), ("Sora", sora)):
            ctx, cpg = browser_as(b, who_)
            try:
                cpg.goto(BASE + "/social/@noor/gallery")
                cpg.wait_for_function("(s) => !!document.querySelector(s)",
                                      arg=f'[data-prof-list] .gal-tile[data-drawing="{lone}"][href="/social/b/{lone}"]',
                                      timeout=12000)
                listed9[name] = True
            except Exception:  # noqa: BLE001 -- not listed is the row's red
                listed9[name] = False
            close_ctx(ctx, cpg)
        in_gal = [k for k, h in gal9.items() if f'<a class="gal-tile" href="/social/b/{lone}"' in h
                  and f"/s/{lone}/poster" in h]
        post_there = [k for k, h in gal9.items() if f'href="/social/p/{p_after}"' in h]
        check("...and in the Gallery of everyone (every skribl, since Nov 14: signed out, and a follower's Everyone and"
              " Following), a tile opening its own page, beside the post after it; and nothing is lost: it keeps its"
              " own page (/social/b/<id>), signed in and out, and its maker's Gallery holds it, a tile opening that"
              " page, signed in and out",
              made9 and len(in_gal) == 3 and len(post_there) == 3
              and all(st_ == 200 and f'data-skribl="{lone}"' in html_ and 'data-kind="s"' in html_
                      for st_, html_ in own9.values())
              and listed9 == {"signed out": True, "Sora": True},
              f"in the Gallery {in_gal}, the post there {post_there}; its page {[(k, v[0]) for k, v in own9.items()]};"
              f" her page lists it {listed9}")

        # A HOME PAGE OPENED BEFORE may hold a cursor that names a drawing:
        # Home's cursor names the last card shown (posts._cursor), and a page
        # could end on a drawing (s, then its skribl's address). Read as its
        # time, the posts after it come next.
        when9 = (db("select created_at from skribl_posts where public_id = ?", (lone,)) or [(None,)])[0][0]
        old_cursor = None
        if when9:
            at9 = datetime.fromisoformat(str(when9)).replace(tzinfo=timezone.utc)
            old_cursor = base64.urlsafe_b64encode(f"{int(at9.timestamp() * 1_000_000)}.s{lone}".encode()).rstrip(b"=").decode()
        carried = home_walk(Client(), before=old_cursor) if old_cursor else None
        st_f, text_f = sora.client()._req("GET", "/social/feed?before=" + urllib.parse.quote("f." + (old_cursor or "")))
        try:
            first_f = [x[0] for x in CARD9.findall(json.loads(text_f).get("html") or "")][:1]
        except (ValueError, AttributeError):
            first_f = None
        tail9 = oracle9[oracle9.index(p_before):] if p_before in oracle9 else None
        carried_ids = [x[0] for x in carried or []]
        check("A HOME CURSOR FROM BEFORE THAT NAMES A DRAWING (a page opened before Home kept posts only could end on"
              " one) reads as its time: Load more from it brings the posts after it, the post shared just before the"
              " drawing first, none missed and none twice, never the first page again; Following's own the same",
              made9 and carried is not None and tail9 is not None and carried_ids == tail9 and len(carried_ids) > 20
              and st_f == 200 and first_f == [p_before],
              f"cursor {old_cursor and old_cursor[:12]}…; signed out {carried_ids[:3]} (want {(tail9 or [])[:3]},"
              f" {len(carried_ids)} of {len(tail9 or [])}); Following's {st_f} {first_f}")

        # LOAD MORE, POSTS ALONE: Ines's twenty-four posts, a drawing shown from
        # the Pad after every second one (made above), read back page by page
        # through the button.
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(800)
        for _ in range(12):
            nxt = pg.evaluate("() => { const b = document.querySelector('[data-feed-next]'); return !!b && !b.hidden; }")
            if not nxt:
                break
            n0 = pg.evaluate("() => document.querySelectorAll('.post-card').length")
            pg.click("[data-feed-next]")
            pg.wait_for_function("(n) => document.querySelectorAll('.post-card').length > n", arg=n0, timeout=15000)
            pg.wait_for_timeout(300)
        allc = pg.evaluate(CARDS)
        got = [c["id"] for c in allc]
        want = list(reversed(made))
        check("Load more walks the posts alone, newest first, none twice and none missed: twenty-four posts with a"
              " drawing shown from the Pad after every second one, read back page by page through the button, are the"
              " twenty-four posts in order and none of the drawings",
              all(made) and all(drawn) and [x for x in got if x in made] == want and len(got) == len(set(got))
              and len(got) > 20 and not ({c["skribl"] for c in allc} & set(drawn))
              and all((c["url"] or "").startswith("/social/p/") for c in allc),
              f"Ines's {[x for x in got if x in made][:3]} want {want[:3]}; {len(got)} cards, {len(set(got))} different;"
              f" drawings among them {len({c['skribl'] for c in allc} & set(drawn))}")

        # A drawing's own page, its ⋯, and its Delete; and another of hers from
        # the Pad, untitled, which More from listed beside it until Nov 20 and
        # the page must not offer now.
        st_a, another = pad(mira.pg, "", "public", 5)
        jp = juno.pg
        jp.goto(BASE + f"/social/b/{shown}")
        jp.wait_for_timeout(1500)
        # PLAYED BY ITSELF: playing, or (repeat off to start since Nov 15) a
        # short drawing already played through and resting on its end.
        played = jp.evaluate("() => (window.SkriblInline ? SkriblInline.players() : []).map(x => { const s = x.state();"
                             " return s.state === 'playing' || s.elapsedMs > 0; })")
        page = jp.evaluate("""() => ({ at: location.pathname, kind: document.querySelector('.post-page').getAttribute('data-kind'),
          words: (document.querySelector('.post-page .post-words') || {}).textContent || '',
          more: document.querySelectorAll('.more-from, .more-tile').length + (/More from/.test(document.body.innerText) ? 1 : 0),
          links: [...document.querySelectorAll('.post-page a[href^="/social/b/"], .post-page a[href^="/social/p/"]')].map(a => a.getAttribute('href')) })""")
        playing = jp.evaluate(STATE)
        OPEN = "(id) => document.getElementById(id).classList.contains('is-open')"
        jp.click("[data-post-menu] >> visible=true")
        jp.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        theirs = jp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => (b.querySelector('.mu-words b') || b).textContent.trim())")
        jp.keyboard.press("Escape")
        to_post = jp.goto(BASE + f"/social/b/{g_skribl}")
        landed = jp.evaluate("() => location.pathname")
        mp = mira.pg
        mp.goto(BASE + f"/social/b/{shown}")
        mp.wait_for_function("() => !!window.SocialSheet && document.readyState === 'complete'", timeout=15000)
        mp.wait_for_timeout(400)
        mp.click("[data-post-menu] >> visible=true")
        mp.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        mine = mp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => (b.querySelector('.mu-words b') || b).textContent.trim())")
        ask = {"open": False}
        try:
            mp.click("#postSheet [data-act=delete]", timeout=5000)
            mp.wait_for_function(OPEN, arg="deleteSheet", timeout=10000)
            ask = mp.evaluate("""() => ({ open: document.getElementById('deleteSheet').classList.contains('is-open'),
              lede: [...document.querySelectorAll('#deleteSheet .post-lede')].filter(e => !e.hidden).map(e => e.textContent) })""")
            with mp.expect_navigation(timeout=20000):
                mp.click("[data-delete-now]", timeout=5000)
        except Exception as exc:
            ask["stopped"] = str(exc).splitlines()[0][:100]
        mp.wait_for_timeout(600)
        after = mp.evaluate("() => ({ url: location.pathname + location.search, note: (document.querySelector('.note') || {}).textContent })")
        gone = skribl_row(shown) is None
        check("a drawing's own page plays it by itself, its title for its words, with no More from (her other"
              " drawing and her post are not offered on it: the Calm Post Page, Nov 20); its ⋯ says Report to anybody"
              " else and Delete post to its author, asked once in the drawing's own words (it goes from her page too:"
              " Home never had it), and then it is gone (Home says so); a post's drawing's page is the post's",
              page["at"] == f"/social/b/{shown}" and page["kind"] == "s"
              and page["words"].strip() == "Section 9, shown from the Pad"
              and (playing[:1] == ["playing"] or played[:1] == [True])
              and bool(another) and bool(g_post) and page["more"] == 0
              and f"/social/b/{another}" not in page["links"] and f"/social/p/{g_post}" not in page["links"]
              and theirs == ["Bookmark", "Copy link", "Share…", "Mute @mira", "Report this post", "Block @mira"]
              and landed == f"/social/p/{g_post}"
              and mine == ["Bookmark", "Copy link", "Share…", "Delete post"] and ask.get("open") and "stopped" not in ask
              and ask.get("lede") == ["The drawing goes for good, from your page too. This can’t be undone."]
              and after["url"] == "/social/?note=deleted_drawing" and after["note"] == "Your drawing is gone." and gone,
              f"page {page}; players {playing}, played {played}; theirs {theirs}; a post's drawing lands {landed}; mine {mine};"
              f" ask {ask}; after {after}; gone {gone}")

        # The guards.
        st_k, sid_k = pad(mira.pg, "Section 9, for the guards", "public", 9)
        c = juno.client()
        c.get("/social/")
        not_mine = c.post_json(f"/social/b/{sid_k}/delete", {})[0]
        mc = mira.client()
        mc.get("/social/")
        no_token = mc.post_json(f"/social/b/{sid_k}/delete", {}, token=False)[0]
        a_posts = mc.post_json(f"/social/b/{g_skribl}/delete", {})[0]
        pages = {k: c.get(f"/social/b/{v}")[0] for k, v in (("unlisted", kept), ("nobody's", nobodys), ("none", "nope0000000"))}
        # ITS MAKER'S OWN, kept unlisted (link-only: hidden from the Gallery, the
        # eye on her Gallery tab, since Nov 14), opens for her alone, as her
        # Gallery tab shows it to her.
        pages["unlisted, hers"] = mc.get(f"/social/b/{kept}")[0]
        # One by somebody not on the site has no page here, so since every card
        # opens /social/b/<id> (section 12) it goes on to Skribl's own (a 302).
        check("a drawing's Delete needs the page's token (403), is its author's alone (somebody else's: 404, the"
              " drawing kept), and never takes a post's drawing without the post (404); a drawing's page is a kind"
              " 404 for one kept unlisted (to anybody but its maker, whose own it is) and none, and one by somebody"
              " not on the site goes on to Skribl's own page",
              no_token == 403 and not_mine == 404 and skribl_row(sid_k) is not None
              and a_posts == 404 and skribl_row(g_skribl) is not None and post_row(g_post) is not None
              and pages == {"unlisted": 404, "nobody's": 302, "none": 404, "unlisted, hers": 200},
              f"no token {no_token}; somebody else's {not_mine} (kept {skribl_row(sid_k) is not None});"
              f" a post's drawing {a_posts}; pages {pages}")

    # ------------------------------------------------------------------ 10
    # EASY TO OPEN (the owner's yes, Nov 12: "tap its words, its name line or
    # its time; the 💬 shows even at zero"). The name and @handle keep going to
    # the person's page, as everywhere else; the words and the time each open
    # the card's own page. Read on Home, phone and desk, light and dark, off
    # what is painted (a tap's landing), on a post with words and one without;
    # a drawing shown outside a post, which had a card here until the map's
    # step 3, has none (Home shows posts only: section 9).
    if part(10, "a card opens its page from its words and its time; the face, name and @handle open the person's; the 💬 at none"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(juno, "Section 10, words that open the post", seed=301)
        worded = j.get("post") if isinstance(j, dict) else None
        st, j = make_post(juno, "", seed=302)
        bare = j.get("post") if isinstance(j, dict) else None
        juno.pg.goto(BASE + "/social/")
        st_s, shown = juno.pg.evaluate(PAD, ["Section 10, a drawing's own title", "public", 303])
        mc = mira.client()
        mc.get(f"/social/p/{worded}")
        commented = mc.post_json(f"/social/p/{worded}/comments", {"words": "Section 10, one comment"})[0]
        want_page = {worded: f"/social/p/{worded}", bare: f"/social/p/{bare}"}
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, mira, screen, scheme)
                cpg.goto(BASE + "/social/")
                cpg.wait_for_timeout(800)
                for key in (worded, bare, shown):
                    seen[(screen, scheme, key)] = cpg.evaluate(WAYS, key or "")
                close_ctx(ctx, cpg)
        bad_open, bad_person, bad_count, bad_still = [], [], [], []
        # The drawing shown outside a post: no card on Home, on any screen.
        drawn_cards = [f"{s}/{sc}" for (s, sc, key), w in seen.items() if key == shown and w is not None]
        for (screen, scheme, key), w in seen.items():
            if key == shown:
                continue
            tag = f"{screen}/{scheme} {'worded' if key == worded else 'bare'}"
            if not w:
                bad_open.append(f"{tag}: no card")
                continue
            big = lambda x: bool(x) and x["w"] >= 44 and x["h"] >= 44 and x["lands"]  # noqa: E731
            x = w["when"]
            # A CARD WITH NO WORDS: the drawing lies over the time's last
            # pixels and keeps its taps there (the drawing never opens the
            # post); the time's middle and top corners are its own.
            ok_at = (x or {}).get("at") == (["self"] * 3 + ["drawing"] * 2 if key == bare else ["self"] * 5)
            if not (x and x["w"] >= 44 and x["h"] >= 44 and ok_at and x["tag"] == "a" and x["href"] == want_page[key]):
                bad_open.append(f"{tag} when: {x}")
            # THE WORDS ARE NO LINK OF THEIR OWN since mentions (Nov 15: a link
            # can't hold the links to the people they name): the card's ground,
            # 44px or more, a tap anywhere in it landing on the card, which opens
            # the post (section 11 taps them, as a person would).
            x = w["words"]
            if key != bare and not (x and x["w"] >= 44 and x["h"] >= 44 and x["at"] == ["card"] * 5 and x["tag"] == "p"
                                    and x["href"] is None):
                bad_open.append(f"{tag} words: {x}")
            if key == bare and w["words"] is not None:
                bad_open.append(f"{tag}: words where there are none {w['words']}")
            person = f"/social/@{'juno'}"
            if not (big(w["face"]) and w["face"]["href"] == person):
                bad_person.append(f"{tag} face: {w['face']}")
            # THE NAME'S LINK IS AS WIDE AS THE NAME AND THE @HANDLE, WHICHEVER RUNS ON FURTHER (the owner, Nov
            # 21; it was the whole top's width): 44px each way still, its own at its middle, at both top corners
            # and at its bottom left, under the @handle (words, which let a tap through to it); at its bottom right
            # its own or, where the second line runs on under the name's end, the time's, to the post.
            x = w["name"]
            if not (x and x["w"] >= 44 and x["h"] >= 44 and x["href"] == person and x["at"][:4] == ["self"] * 4
                    and x["at"][4] in ("self", want_page[key])):
                bad_person.append(f"{tag} name: {x}")
            if w["handle"] != person:
                bad_person.append(f"{tag} @handle lands on {w['handle']}")
            n = w["count"]
            want_label, want_text = ("1 comment", "1") if key == worded else ("Comment", "")
            if not (big(n) and n["href"] == want_page[key] + "#say" and n["icon"] and n["label"] == want_label
                    and n["text"] == want_text):
                bad_count.append(f"{tag}: {n}")
            if not (w["sameLine"] and w["headH"] == 44 and (w["wordsGap"] is None or abs(w["wordsGap"] - 12) <= 0.5)
                    and abs(w["artGap"] - 12) <= 0.5):
                bad_still.append(f"{tag}: on the @handle's line {w['sameLine']}, the header {w['headH']}px, words"
                                 f" {w['wordsGap']}, drawing {w['artGap']}")
        made = bool(worded and bare and shown and st_s == 201 and commented == 200)
        check("a card's time opens its post's page, a link a tap lands on anywhere in its 44px or more (on a card with"
              " no words, the time's down to the drawing, which keeps its own taps), and its words, no link of their"
              " own since mentions, are the card's ground anywhere in their 44px, which opens it too: a post with"
              " words and one without, phone and desk, light and dark; a drawing shown outside a post has no card"
              " there (Home shows posts only)",
              made and len(seen) == 12 and not bad_open and not drawn_cards,
              f"made {made}; {len(seen)} read; {bad_open[:4]}; the drawing's card on Home {drawn_cards}")
        check("the face, the name and the @handle still open the person's page: the name's link 44px each way, its own"
              " along the name's line and painted under the @handle too, so a tap on the @handle lands on it",
              made and not bad_person, f"{bad_person[:4]}")
        check("the 💬 shows even at none: its icon alone, named \"Comment\", a way to the post with its answer box open (#say:"
              " the cloud answers, the owner's yes, Nov 21) a tap lands on, 44px; with one, its number, \"1 comment\"",
              made and not bad_count, f"{bad_count[:4]}")
        check("and nothing moved: the header the face's 44px, the time on the @handle's line just after it, the words"
              " 12px under the header, and the drawing 12px under the words (or the header, with none)",
              made and not bad_still, f"{bad_still[:4]}")

    # ------------------------------------------------------------------ 11
    # ANYWHERE ON A CARD OPENS ITS POST (the owner's yes, Nov 12), but what
    # does its own thing keeps it: the drawing plays and pauses and never opens
    # the post; the face, the name and the @handle open the person's page; ⋯
    # and Share do their own job; the 💬 opens the comments. A drag that
    # selects words opens nothing. Pressed for real: a touch on a phone, a
    # mouse on a desk, at the points a person would.
    if part(11, "anywhere on a card opens its post; the drawing, the person, ⋯ and Share keep their own"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(juno, "Section 11, a card to tap", seed=401)
        card = j.get("post") if isinstance(j, dict) else None
        st, j = make_post(juno, "", seed=402)
        bare = j.get("post") if isinstance(j, dict) else None
        bare_sid = (post_row(bare) or (None, None))[1] if bare else None
        # TWO NAMES OF TWO LETTERS (Juno's @handle ends under her name, so her link is her name's width). Al's
        # @handle runs on far past his name: his link is as wide as the @handle. Il's is the narrowest @handle
        # there can be (a letter and two more, accounts.HANDLE_RE): both of her lines are narrower than a finger,
        # and her link is 44px.
        al = someone(b, "al_has_a_long_handle", "Al")
        st, j = make_post(al, "Section 11, a name of two letters", seed=403)
        short = j.get("post") if isinstance(j, dict) else None
        il = someone(b, "ill", "Il")
        st, j = make_post(il, "Section 11, the narrowest @handle", seed=404)
        narrow = j.get("post") if isinstance(j, dict) else None
        SPOT = """([key, what]) => {
          const c = document.querySelector('.post-card[data-post="' + key + '"]'); if (!c) return null;
          c.scrollIntoView({ block: 'center' });
          const R = s => c.querySelector(s).getBoundingClientRect(), mid = r => [r.left + r.width / 2, r.top + r.height / 2];
          const text = (root, needle) => { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            for (let n = w.nextNode(); n; n = w.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
              const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g.getBoundingClientRect(); } }
            return null; };
          let xy;
          // The card's own ground: since Bluesky's columns (Nov 28) the face's column under the face, at the
          // row's middle (the row spread across its column leaves no open space past the ⋯).
          if (what === 'ground') { const f = R('.post-row'), m = R('.post-head .post-face');
            xy = [m.left + m.width / 2, f.top + f.height / 2]; }
          else if (what === 'words') xy = mid(text(c.querySelector('.post-words'), 'a card'));
          else if (what === 'drawing') xy = mid(R('.post-art .skribl-inline'));
          else if (what === 'under the time') { const t = R('.post-when'), a = R('.post-art .skribl-inline');
            xy = [t.left + t.width / 2, a.top + 4]; }
          else if (what === 'name') xy = mid(text(c.querySelector('.post-head'), c.querySelector('.post-name').textContent));
          else if (what === 'handle') xy = mid(text(c.querySelector('.post-head'), '@' + c.dataset.handle));
          // WHERE THE PERSON'S TAP STOPS (the owner, Nov 21): 10px past the name's last letter, on its line; the
          // top's far end, 12px in from its right edge, on the name's line; and the @handle's own last letter.
          else if (what === 'right of the name') { const n = text(c.querySelector('.post-head'), c.querySelector('.post-name').textContent);
            xy = [n.right + 10, n.top + n.height / 2]; }
          else if (what === 'top right') { const n = text(c.querySelector('.post-head'), c.querySelector('.post-name').textContent);
            xy = [R('.post-head').right - 12, n.top + n.height / 2]; }
          else if (what === 'end of the handle') { const h = text(c.querySelector('.post-head'), '@' + c.dataset.handle);
            xy = [h.right - 3, h.top + h.height / 2]; }
          else if (what === 'past the name') { const n = text(c.querySelector('.post-head'), c.querySelector('.post-name').textContent);
            xy = [R('.post-name').right + 12, n.top + n.height / 2]; }
          else xy = mid(R({ face: '.post-face', more: '.post-more', repost: '.post-row .rp-btn', count: '.post-count' }[what]));
          const e = document.elementFromPoint(xy[0], xy[1]);
          return { xy, on: e ? (e.closest('.post-art') ? 'drawing' : e.closest('a, button') ? e.closest('a, button').className : 'card') : null }; }"""
        PLAYER = """(sid) => { const p = (window.SkriblInline ? SkriblInline.players() : []).find(x => x.state().id === sid);
          return p ? p.state().state : null; }"""
        SHARE = ("Object.defineProperty(navigator, 'share', { configurable: true,"
                 " value: d => { window.__shared = d && d.url; return Promise.resolve(); } });")
        res = {}
        for screen in ("phone", "desk"):
            touch = screen == "phone"
            ctx, cpg = browser_as(b, mira, screen, "light")
            ctx.add_init_script(SHARE)

            def home():
                cpg.goto(BASE + "/social/")
                cpg.wait_for_function("() => !!window.SocialSheet && !!window.SocialWhen && document.readyState === 'complete'",
                                      timeout=15000)
                cpg.wait_for_timeout(300)

            def press(key, what):
                got = cpg.evaluate(SPOT, [key or "", what])
                if not got:
                    return None
                cpg.wait_for_timeout(150)
                (cpg.touchscreen.tap if touch else cpg.mouse.click)(*got["xy"])
                return got["on"]

            def landed(wait=2500):
                try:
                    cpg.wait_for_function("() => location.pathname !== '/social/'", timeout=wait)
                except Exception:  # noqa: BLE001 -- staying is an answer
                    pass
                cpg.wait_for_timeout(200)
                return cpg.evaluate("() => location.pathname + location.hash")

            r = res[screen] = {}
            try:
                for what in ("ground", "words", "count"):
                    home()
                    on = press(card, what)
                    r[what] = (on, landed())
                home()
                on1 = press(bare, "drawing")
                try:
                    cpg.wait_for_function(f"() => ({PLAYER})({json.dumps(bare_sid)}) === 'playing'", timeout=8000)
                except Exception:  # noqa: BLE001 -- not playing is the row's red
                    pass
                first = (on1, cpg.evaluate(PLAYER, bare_sid), cpg.evaluate("() => location.pathname"))
                on2 = press(bare, "under the time")
                cpg.wait_for_timeout(900)
                second = (on2, cpg.evaluate(PLAYER, bare_sid), cpg.evaluate("() => location.pathname"))
                r["drawing"] = (first, second)
                for what in ("face", "name", "handle", "end of the handle", "right of the name", "top right"):
                    home()
                    on = press(card, what)
                    r[what] = (on, landed())
                # THE LINK AGAINST ITS TWO LINES' OWN LETTERS: its width, the name's and the @handle's, and where
                # each starts from the link's left (all three together: nothing moved to make the link).
                LINES = """(key) => { const c = document.querySelector('.post-card[data-post="' + key + '"]'); if (!c) return null;
                  const a = c.querySelector('.post-name'), r = a.getBoundingClientRect(), g = document.createRange();
                  g.selectNodeContents(a); const t = g.getBoundingClientRect();
                  const n = document.createTreeWalker(c.querySelector('.post-sub'), NodeFilter.SHOW_TEXT).nextNode();
                  const at = '@' + c.dataset.handle, i = n ? n.textContent.indexOf(at) : -1; if (i < 0) return null;
                  g.setStart(n, i); g.setEnd(n, i + at.length); const h = g.getBoundingClientRect(), r2 = v => Math.round(v * 100) / 100;
                  // ...and what gives the link the @handle's width: the @handle said again beside the name, unseen.
                  const gb = getComputedStyle(c.querySelector('.post-who'), '::before');
                  return { link: r2(r.width), name: r2(t.width), handle: r2(h.width), starts: [r2(t.left - r.left), r2(h.left - r.left)],
                           ghost: [gb.content, gb.visibility, gb.height] }; }"""
                for tag, key, taps in (("Al", short, ("end of the handle", "right of the name", "past the name")),
                                       ("Il", narrow, ("end of the handle", "past the name"))):
                    home()
                    r[tag + "'s lines"] = cpg.evaluate(LINES, key or "")
                    for what in taps:
                        home()
                        on = press(key, what)
                        r[tag + ", " + what] = (on, landed())
                home()
                press(card, "more")
                try:
                    cpg.wait_for_function("() => document.getElementById('postSheet').classList.contains('is-open')", timeout=5000)
                except Exception:  # noqa: BLE001 -- not opening is the row's red
                    pass
                r["more"] = (cpg.evaluate("() => document.getElementById('postSheet').classList.contains('is-open')"),
                             landed(1500))
                # THE REPOST (the reposts mock, Nov 14: where Share was; Share is in the ⋯).
                home()
                press(card, "repost")
                try:
                    cpg.wait_for_function("() => document.getElementById('repostSheet').classList.contains('is-open')", timeout=5000)
                except Exception:  # noqa: BLE001 -- not opening is the row's red
                    pass
                r["repost"] = (cpg.evaluate("() => document.getElementById('repostSheet').classList.contains('is-open')"),
                               landed(1500))
                if not touch:
                    # A DRAG THAT SELECTS WORDS opens nothing: pressed on the words'
                    # first letter and let go on their last.
                    home()
                    ends = cpg.evaluate("""(key) => { const c = document.querySelector('.post-card[data-post="' + key + '"]');
                      c.scrollIntoView({ block: 'center' }); const w = c.querySelector('.post-words'), n = w.firstChild;
                      const g = document.createRange(); g.setStart(n, 0); g.setEnd(n, 1); const a = g.getBoundingClientRect();
                      g.setStart(n, n.length - 1); g.setEnd(n, n.length); const z = g.getBoundingClientRect();
                      return [a.left + 1, a.top + a.height / 2, z.right - 1, z.top + z.height / 2]; }""", card)
                    cpg.mouse.move(ends[0], ends[1])
                    cpg.mouse.down()
                    cpg.mouse.move(ends[2], ends[3], steps=12)
                    cpg.mouse.up()
                    cpg.wait_for_timeout(300)
                    r["select"] = (cpg.evaluate("() => String(getSelection())"), landed(1500))
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is its rows' red
                r["stopped"] = str(exc).splitlines()[0][:160]
            close_ctx(ctx, cpg)
        page, people = f"/social/p/{card}", "/social/@juno"
        ok_open = all(r.get("ground") == ("card", page) and r.get("words", (None, None))[1] == page
                      and r.get("count", (None, None))[1] in (page, page + "#say") for r in res.values())
        # NO OPEN › (the owner's "completely remove open", Nov 19): the card's
        # own ground is the door; since Bluesky's columns (Nov 28) the face's
        # column under the face is ground (the row spreads to the ⋯ at its end).
        check("a tap anywhere on a card's own ground (here the face's column under the face, beside the row: no"
              " finger is snapped to a button there) opens its page, as a tap on its words does;"
              " the 💬 opens it too, asking for its answer box (#say, which the page drops once it has opened it:"
              " verify_socialcomments 34 holds the box): a touch on a phone, a click on a desk",
              bool(card) and ok_open,
              f"{ {s: {k: r.get(k) for k in ('ground', 'words', 'count', 'stopped')} for s, r in res.items()} }")
        want_drawing = (("drawing", "playing", "/social/"), ("drawing", "paused", "/social/"))
        check("a tap on the drawing plays it and a second pauses it, and the page stays, even at its top edge under the"
              " time on a card with no words: the drawing never opens the post; phone and desk",
              bool(bare_sid) and all(r.get("drawing") == want_drawing for r in res.values()),
              f"{ {s: r.get('drawing') for s, r in res.items()} }")
        check("a tap on the face, the name or the @handle (its last letter too) opens the person's page, never the post:"
              " phone and desk",
              all(r.get(k, (None, None))[1] == people for r in res.values() for k in ("face", "name", "handle", "end of the handle")),
              f"{ {s: {k: r.get(k) for k in ('face', 'name', 'handle', 'end of the handle')} for s, r in res.items()} }")
        # THE PERSON'S TAP STOPS AT THEIR NAME (the owner, Nov 21: "on posts the name or icon should take you to
        # profile but anything on top right should open post. Right now profile tap extends past name. It should
        # stop at name so tap up there to right of name opens post"). The name's link was as wide as the whole top,
        # to the ⋯ (280px on a phone, 886 on a desk, for a name 73px wide).
        check("...and the person's tap stops at their name: a tap 10px past the name's last letter, and one at the far"
              " end of the card's top, lands on the card's own ground and opens the post: phone and desk",
              all(r.get(k) == ("card", page) for r in res.values() for k in ("right of the name", "top right")),
              f"{ {s: {k: r.get(k) for k in ('right of the name', 'top right')} for s, r in res.items()} }")
        # THE @HANDLE IS THE PERSON'S TOO, TO ITS LAST LETTER, AND A FINGER TALL: so where it runs on past the
        # name the link is as wide as the @handle, and the room right of a short name, over the @handle, goes
        # with it. (A link of the @handle's own was tried first, Nov 21: 44px tall, it reached down over the top
        # half of the words' first line, and a tap there opened the person's page.)
        als = {s_: {k: r.get(k) for k in ("Al's lines", "Al, end of the handle", "Al, right of the name", "Al, past the name")}
               for s_, r in res.items()}
        check("...and where the @handle runs on past a name of two letters, the link is as wide as the @handle and no"
              " wider (both lines start where the link does; what widens it is not shown and has no height): the"
              " @handle's last letter and the room over it, right of the name, open the person's page, and a tap 12px"
              " past the link opens the post: phone and desk",
              bool(short) and all((v["Al's lines"] or {}).get("handle", 0) > 100 and 0 < v["Al's lines"]["name"] < 30
                                  and abs(v["Al's lines"]["link"] - v["Al's lines"]["handle"]) <= 0.5
                                  and v["Al's lines"]["ghost"] == [f'"@{al.handle}"', "hidden", "0px"]
                                  and all(abs(x) <= 0.5 for x in v["Al's lines"]["starts"])
                                  and v["Al, past the name"] == ("card", f"/social/p/{short}")
                                  and all((v[k] or (None, None))[1] == "/social/@" + al.handle
                                          for k in ("Al, end of the handle", "Al, right of the name"))
                                  for v in als.values()), f"{als}")
        ils = {s_: {k: r.get(k) for k in ("Il's lines", "Il, end of the handle", "Il, past the name")} for s_, r in res.items()}
        check("...and where the name and the @handle are both narrower than a finger (two letters over the narrowest"
              " @handle there can be), the link is 44px and no more: the @handle opens the person's page, and a tap"
              " 12px past the link opens the post: phone and desk",
              bool(narrow) and all((v["Il's lines"] or {}).get("link") == 44 and 0 < v["Il's lines"]["name"] < 30
                                   and 0 < v["Il's lines"]["handle"] < 40
                                   and all(abs(x) <= 0.5 for x in v["Il's lines"]["starts"])
                                   and v["Il, past the name"] == ("card", f"/social/p/{narrow}")
                                   and (v["Il, end of the handle"] or (None, None))[1] == "/social/@" + il.handle
                                   for v in ils.values()), f"{ils}")
        check("⋯ and the repost do their own job and the page stays: ⋯ opens its sheet, the repost its own (Share is in"
              " the ⋯ since the reposts mock): phone and desk",
              all(r.get("more") == (True, "/social/") and r.get("repost") == (True, "/social/") for r in res.values()),
              f"{ {s: {k: r.get(k) for k in ('more', 'repost')} for s, r in res.items()} }")
        sel = res.get("desk", {}).get("select") or ("", None)
        check("pressing on a card's words and pulling selects them and opens nothing: a click that ends a selection is not"
              " a tap (desk)",
              sel[0].strip() == "Section 11, a card to tap" and sel[1] == "/social/", f"{sel}")

    # ------------------------------------------------------------------ 12
    # EVERY CARD OPENS ITS POST (the owner, Nov 13, from the phone: "Show me
    # where you click or touch to go to post view? It's not clear. I thought on
    # card?"). The rule said yes to on Nov 12, "anywhere on the card should open
    # the post and clicking on the player should make it play", on every card
    # the site shows: Home's (a post's; since the map's step 3 Home shows
    # posts only), and the first visit's Skribls, which are Skribl's own
    # Gallery cards opening where the site says (skribl.set_card_url,
    # app.py), with one by somebody not on the site. (Explore's were Skribl's
    # cards too until the map's step 3, and a profile's until its step 4; the
    # Gallery of everyone's tiles are one link each, section 13, and a
    # profile's Gallery tab is those tiles, verify_socialprofile section 16.)
    # The first visit, signed out, is where the site still shows Skribl's
    # own cards, so the desk's rows and the ⋯ are read there. Cal's tap map as rows: every 4px of each card,
    # light and dark, on a touch phone (TAPMAP); an EXACT tap on every part of
    # its ground, followed to where it lands (exact: a phone's own targeting
    # moves a tap that lands near a control onto it, which is the phone's
    # doing, not the page's); and a finger's tap on the drawing, the name and
    # the ground. Then /social/b/<id>'s three ways on, the line's controls, and
    # on a desk Ctrl, the middle button, a drag, a keyboard and the ⋯.
    if part(12, "every card opens its post: the tap map of Home's cards and Skribl's where a host says"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st_g, jg = make_post(juno, "Section 12, a post shown in the gallery", gallery=True, seed=121)
        g_post = jg.get("post") if isinstance(jg, dict) else None
        g_sid = (post_row(g_post) or (None, None))[1] if g_post else None
        # A Flip too: the Gallery and Home show a Flip's card as a drawing's.
        st_f, jf = make_post(juno, "Section 12, a Flip shown in the gallery", gallery=True, flip=True, seed=125)
        f_post = jf.get("post") if isinstance(jf, dict) else None
        f_sid = (post_row(f_post) or (None, None))[1] if f_post else None
        juno.pg.goto(BASE + "/social/")
        st_l, lone = juno.pg.evaluate(PAD, ["Section 12, a drawing on its own", "public", 122])
        nb_ctx, nb_pg = browser_as(b, None)
        nb_pg.goto(BASE + "/skribl-pad")
        nb_pg.wait_for_timeout(800)
        st_n, nobodys = nb_pg.evaluate(PAD, ["Section 12, nobody's", "public", 123])
        st_u, unlisted = nb_pg.evaluate(PAD, ["Section 12, nobody's, kept unlisted", "unlisted", 124])
        close_ctx(nb_ctx, nb_pg)
        made = bool(g_sid and f_sid and lone and nobodys and unlisted) and [st_l, st_n, st_u] == [201, 201, 201]
        to_post, to_lone, to_skribl = f"/social/p/{g_post}", f"/social/b/{lone}", f"/s/{nobodys}"
        to_flip = f"/social/p/{f_post}"
        TILE = '#skriblGallery .tile[data-id="{}"]'
        # Each card as somebody meets it: signed in (Mira) on Home; signed out
        # on Skribl's own Gallery, everybody's, the site's people's and not,
        # its section given the address the site's pages gave Skribl's cards
        # (app.py's card_url, /social/b/__ID__) as a host's page gives it,
        # read by gallery.js. No page of the site holds Skribl's section any
        # more: the first visit's was the last, the Gallery's six since Nov 14
        # (section 14). The drawing on its own is a tile on its maker's
        # Gallery tab (verify_socialprofile 16); Home shows posts only.
        G12 = "Skribl's /gallery, a host's address said"
        CARDS = [("Home", "/social/", f'.post-card[data-post="{g_post}"]', g_sid, to_post, mira),
                 ("Home", "/social/", f'.post-card[data-post="{f_post}"]', f_sid, to_flip, mira),
                 (G12, "/gallery", TILE.format(g_sid), g_sid, to_post, None),
                 (G12, "/gallery", TILE.format(f_sid), f_sid, to_flip, None),
                 (G12, "/gallery", TILE.format(lone), lone, to_lone, None),
                 (G12, "/gallery", TILE.format(nobodys), nobodys, to_skribl, None)]
        # Where a finger goes on a card: the drawing's middle, the name's, and
        # the ground's: on Home's calm card the face's column under the face,
        # beside the row (Bluesky's columns, Nov 28: the row spreads to the ⋯
        # at its end; no Open › since Nov 19), a Gallery card's time; scrolled
        # to the screen's middle first.
        SPOT12 = """([sel, what]) => { const c = document.querySelector(sel); if (!c) return null;
          const text = (root, needle) => { if (!root) return null; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            for (let n = w.nextNode(); n; n = w.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
              const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g; } }
            return null; };
          const at = { drawing: () => c.querySelector('.skribl-inline'),
                       name: () => { const e = c.querySelector('.post-name, .tdn'); return e && text(e, e.textContent.trim()); },
                       ground: () => { const m = c.querySelector('.post-head .post-face'), o = c.querySelector('.post-row');
                         if (m && o) return { getBoundingClientRect: () => { const a = m.getBoundingClientRect(), z = o.getBoundingClientRect();
                           return { left: a.left, top: z.top, width: a.width, height: z.height }; } };
                         return text(c.querySelector('.tm'), c.querySelector('.tm') ? c.querySelector('.tm').textContent.trim() : ''); } }[what];
          const it = at && at(); if (!it || !it.getBoundingClientRect().width) return null;
          let r = it.getBoundingClientRect();
          window.scrollTo({ top: r.top + scrollY + r.height / 2 - innerHeight / 2, behavior: 'instant' });
          r = it.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"""
        PLAYING = """(sid) => { const p = (window.SkriblInline ? SkriblInline.players() : []).find(x => x.state().id === sid);
          return p ? p.state().state : null; }"""

        def ready(pg_, path, sel):
            pg_.goto(BASE + path)
            pg_.wait_for_function("(s) => document.readyState === 'complete' && !!window.SkriblInline && !!document.querySelector(s)",
                                  arg=sel, timeout=15000)
            pg_.wait_for_timeout(250)

        def follow(pg_, path, wait=2500):
            """Where a tap took the page: its path (and #), redirects followed."""
            try:
                pg_.wait_for_url(lambda u: urllib.parse.urlsplit(u).path != path, timeout=wait)
                pg_.wait_for_load_state("load", timeout=10000)
            except Exception:  # noqa: BLE001 -- staying is an answer
                pass
            # A moment for the page arrived at to settle. #890 raised it from
            # 150ms believing that going on mid-fade made Chrome report
            # "Transition was aborted because of invalid state" on /s/<id>; it
            # does not (leaving mid-fade, 10 times of 10, reported nothing).
            # That was a first visit's fade, decided at <body> before
            # player.css had loaded, mended in the page's head (verify_menu,
            # "a first visit fades in too").
            pg_.wait_for_timeout(400)
            u = urllib.parse.urlsplit(pg_.url)
            return u.path + ("#" + u.fragment if u.fragment else "")

        maps = {}
        for scheme, viewer in (("light", mira), ("dark", mira), ("light", None), ("dark", None)):
            ctx, cpg = browser_as(b, viewer, "phone", scheme)
            if viewer is None:
                cpg.add_init_script(SITE_OPENS)
            for surface, path, sel, sid, want, who_ in CARDS:
                if who_ is not viewer:
                    continue
                got = maps[(scheme, surface, sel)] = {"want": want, "path": path,
                                                     "label": f"{surface} ({scheme}), the card for {want}"}
                try:
                    ready(cpg, path, sel)
                    m = cpg.evaluate(TAPMAP, [sel, 4])
                    got["keys"] = m["keys"]
                    parts = got["parts"] = {}
                    for key in sorted(k for k in m["keys"] if k.startswith("ground|")):
                        x, y = inmost(m["grid"], key, 4)
                        ready(cpg, path, sel)
                        cpg.mouse.click(*cpg.evaluate(AIM, [sel, x, y]))
                        parts[key] = ((x, y), follow(cpg, path))
                    for what, spot in (("drawing", "drawing"), ("person", "name"), ("finger", "ground")):
                        ready(cpg, path, sel)
                        xy = cpg.evaluate(SPOT12, [sel, spot])
                        if not xy:
                            got[what] = None
                            continue
                        cpg.touchscreen.tap(*xy)
                        if what == "drawing":
                            try:
                                cpg.wait_for_function(f"() => ({PLAYING})({json.dumps(sid)}) === 'playing'", timeout=8000)
                            except Exception:  # noqa: BLE001 -- not playing is the row's red
                                pass
                            got[what] = (cpg.evaluate(PLAYING, sid), follow(cpg, path, 900))
                        else:
                            got[what] = follow(cpg, path)
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is its rows' red
                    got["stopped"] = str(exc).splitlines()[0][:160]
            close_ctx(ctx, cpg)

        cards12 = list(maps.values())
        dead = {r["label"]: {k: v for k, v in r.get("parts", {}).items() if v[1] != r["want"]} for r in cards12}
        dead = {k: v for k, v in dead.items() if v}
        lacking = [(r["label"], r.get("stopped")) for r in cards12 if "stopped" in r or not r.get("parts")]
        check("THE TAP MAP: on Home's cards (a post's drawing and a Flip's) and Skribl's Gallery cards where a host"
              " says they open its page (those, one on its own, and one by somebody not on the site, on Skribl's"
              " /gallery given the site's address), a touch phone in light and dark, every 4px is one of"
              " the card's own controls or its ground, and an exact tap on every part of the ground (its words, its"
              " time, its edges, the line under the drawing, the space between) opens the card's page: no part does"
              " nothing",
              made and len(cards12) == 2 * len(CARDS) and not dead and not lacking,
              f"made {made}; does nothing or goes elsewhere: {dict(list(dead.items())[:3])}; stopped {lacking[:3]};"
              f" parts of the ground per card {[len(r.get('parts', {})) for r in cards12]}")
        check("...a finger's tap on the drawing plays it there, and the page stays",
              made and all(r.get("drawing") == ("playing", r["path"]) for r in cards12),
              f"{ {r['label']: r.get('drawing') for r in cards12 if r.get('drawing') != ('playing', r['path'])} }")
        check("...a finger's tap on the name opens the person's page (on the card by somebody not on the site,"
              " 'Anonymous' names nobody: it is the card's ground, and opens the card)",
              made and all(r.get("person") == ("/social/@juno" if r["want"] != to_skribl else r["want"])
                           for r in cards12),
              f"{ {r['label']: r.get('person') for r in cards12} }")
        check("...and a finger's tap on the ground opens the right page, followed: a post's drawing its post"
              " (/social/p/…), one on its own its page (/social/b/…), one by somebody not on the site Skribl's own"
              " page for it (/s/…); on Home in the face's column beside the row, on a Gallery card at its time",
              made and all(r.get("finger") == r["want"] for r in cards12),
              f"{ {r['label']: r.get('finger') for r in cards12 if r.get('finger') != r['want']} }")

        # /social/b/<id>, WHERE EVERY GALLERY CARD ON THE SITE OPENS: a post's
        # drawing goes on to its post for anybody who may see the post, and is
        # as gone as the post to anybody it is hidden from (here a block), without
        # naming it; one by somebody not on the site goes to Skribl's own page
        # for it; one of theirs kept unlisted is a kind 404, as before.
        kit = someone(b, "kit", "Kit Vale")
        kc = kit.client()
        kc.get("/social/")
        blocked = kc.post_json("/social/@juno/block", {})[0]

        def where(cookies, path):
            op = urllib.request.build_opener(_NoRedirect())
            req = urllib.request.Request(BASE + path, headers={"X-Forwarded-For": address(),
                                                                **({"Cookie": cookies} if cookies else {})})
            try:
                with op.open(req, timeout=30) as r_:
                    return r_.status, None, r_.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                return e.code, e.headers.get("Location"), e.read().decode("utf-8", "replace")

        def jar(who):
            return "; ".join(f"{c['name']}={c['value']}" for c in who.ctx.cookies(BASE))
        on = {"mira": where(jar(mira), f"/social/b/{g_sid}"), "nobody": where(None, f"/social/b/{g_sid}"),
              "kit": where(jar(kit), f"/social/b/{g_sid}"), "theirs": where(None, f"/social/b/{nobodys}"),
              "unlisted": where(None, f"/social/b/{unlisted}"), "lone": where(None, f"/social/b/{lone}")}
        check("/social/b/<id> takes a post's drawing on to its post for anybody who may see it, signed in or not; to"
              " somebody the post is hidden from (a block) it is a kind 404 that names no post; one by somebody not on"
              " the site goes to Skribl's own page for it; one of theirs kept unlisted is a kind 404; one on its own"
              " is its own page",
              made and blocked == 200
              and all(on[k][0] == 302 and (on[k][1] or "").endswith(to_post) for k in ("mira", "nobody"))
              and on["kit"][0] == 404 and not on["kit"][1] and g_post not in on["kit"][2]
              and on["theirs"][0] == 302 and (on["theirs"][1] or "").endswith(to_skribl)
              and on["unlisted"][0] == 404 and on["lone"][0] == 200,
              f"block {blocked}; {[(k, v[0], v[1]) for k, v in on.items()]}; the 404 names the post"
              f" {bool(g_post and g_post in on['kit'][2])}")

        # THE LINE'S OWN CONTROLS KEEP THEIR TAPS (Home's card): the speed opens
        # its choices and takes one, the loop stops repeating, and the page stays.
        ctx, cpg = browser_as(b, mira, "phone", "light")
        line = {}
        try:
            sel = f'.post-card[data-post="{g_post}"]'
            ready(cpg, "/social/", sel)
            # A card's line waits until its drawing is first played (the calm
            # card, Nov 13): played and paused, it is open, as for a person.
            cpg.evaluate("(s) => SkriblInline.mount(document.querySelector(s + ' .post-art'))[0].toggle()", sel)
            cpg.wait_for_function("(s) => !document.querySelector(s + ' .skribl-inline-line').className.match(/is-(waiting|opening)/)",
                                  arg=sel, timeout=8000)
            cpg.evaluate("(s) => { const p = SkriblInline.mount(document.querySelector(s + ' .post-art'))[0];"
                         " if (p.state().state === 'playing') p.toggle(); }", sel)
            cpg.wait_for_timeout(300)
            cpg.locator(sel + " .rl-speed").scroll_into_view_if_needed()
            cpg.locator(sel + " .rl-speed").tap()
            cpg.wait_for_timeout(300)
            line["chips"] = cpg.evaluate("(s) => document.querySelector(s + ' .rl-speed').getAttribute('aria-expanded')", sel)
            # Between two of the choices, an exact tap lands on their group: a near
            # miss, which opens nothing and leaves the choices open.
            gap = cpg.evaluate("""(s) => { const g = document.querySelector(s + ' .rl-chips'), r = g.getBoundingClientRect();
              for (let y = r.top + 1; y < r.bottom; y += 2) for (let x = r.left + 1; x < r.right; x += 1)
                if (document.elementFromPoint(x, y) === g) return [x, y];
              return null; }""", sel)
            if gap:
                cpg.mouse.click(*gap)
            line["between"] = (bool(gap), follow(cpg, "/social/", 900),
                               cpg.evaluate("(s) => document.querySelector(s + ' .rl-speed').getAttribute('aria-expanded')", sel))
            cpg.locator(sel + ' .rl-chips button[data-r="2"]').tap()
            cpg.wait_for_timeout(300)
            line["speed"] = cpg.evaluate("(s) => document.querySelector(s + ' .rl-speed').textContent.trim()", sel)
            cpg.locator(sel + " .skribl-inline-line .skribl-inline-loop").tap()
            cpg.wait_for_timeout(300)
            line["loop"] = cpg.evaluate("(s) => document.querySelector(s + ' .skribl-inline-line .skribl-inline-loop').getAttribute('aria-pressed')", sel)
            line["at"] = follow(cpg, "/social/", 600)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            line["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        check("...and on Home, once its drawing is played (the line waits until then), the line's own controls keep"
              " their taps: the speed opens its choices (a tap between two"
              " of them opens nothing and leaves them open) and takes one (2×), the loop (off to start since Nov 15)"
              " starts repeating, and the page stays",
              made and line.get("chips") == "true" and line.get("between") == (True, "/social/", "true")
              and line.get("speed", "").startswith("2") and line.get("loop") == "true"
              and line.get("at") == "/social/", f"{line}")

        # ON A DESK: Ctrl (as ⌘ is on a Mac) and the middle button open the card
        # in a new tab and leave this page be; a drag that selects a card's words
        # opens nothing, nor does one across its ground; the title is the card's
        # link for a keyboard (Tab from ⋯ reaches it, Enter opens it). Home's
        # card signed in (Mira); Skribl's cards signed out, on its /gallery given
        # the site's address (the first visit's until Nov 14).
        ctx, cpg = browser_as(b, mira, "desk", "light")
        octx, opg = browser_as(b, None, "desk", "light")
        opg.add_init_script(SITE_OPENS)
        desk = {}

        def newtab(press_, ctx_):
            try:
                with ctx_.expect_page(timeout=5000) as info:
                    press_()
                tab = info.value
                tab.wait_for_load_state("load", timeout=15000)
                u = urllib.parse.urlsplit(tab.url).path
                tab.close()
                return u
            except Exception:  # noqa: BLE001 -- no tab is the row's red
                return None

        try:
            hsel, esel = f'.post-card[data-post="{g_post}"]', TILE.format(lone)
            for name_, ctx_, pg_, path, sel in (("home", ctx, cpg, "/social/", hsel), ("gallery", octx, opg, "/gallery", esel)):
                ready(pg_, path, sel)
                xy = pg_.evaluate(SPOT12, [sel, "ground"])

                def ctrl_click():
                    pg_.keyboard.down("Control")
                    pg_.mouse.click(*xy)
                    pg_.keyboard.up("Control")
                desk[name_ + " ctrl"] = (newtab(ctrl_click, ctx_), follow(pg_, path, 600))
                ready(pg_, path, sel)
                xy = pg_.evaluate(SPOT12, [sel, "ground"])
                desk[name_ + " middle"] = (newtab(lambda: pg_.mouse.click(*xy, button="middle"), ctx_), follow(pg_, path, 600))
            # A drag that selects a Gallery card's caption, and one across its ground.
            csel = TILE.format(g_sid)
            ready(opg, "/gallery", csel)
            ends = opg.evaluate("""(s) => { const c = document.querySelector(s); const w = c.querySelector('.tcap'), n = w.firstChild;
              w.scrollIntoView({ block: 'center' }); const g = document.createRange(); g.setStart(n, 0); g.setEnd(n, 1);
              const a = g.getBoundingClientRect(); g.setStart(n, n.length - 1); g.setEnd(n, n.length); const z = g.getBoundingClientRect();
              return [a.left + 1, a.top + a.height / 2, z.right - 1, z.top + z.height / 2]; }""", csel)
            opg.mouse.move(ends[0], ends[1])
            opg.mouse.down()
            opg.mouse.move(ends[2], ends[3], steps=12)
            opg.mouse.up()
            opg.wait_for_timeout(300)
            desk["select"] = (opg.evaluate("() => String(getSelection())"), follow(opg, "/gallery", 1500))
            ready(opg, "/gallery", csel)
            g0 = opg.evaluate(SPOT12, [csel, "ground"])
            opg.mouse.move(g0[0], g0[1])
            opg.mouse.down()
            opg.mouse.move(g0[0] - 40, g0[1] + 2, steps=8)
            opg.mouse.up()
            desk["drag"] = follow(opg, "/gallery", 1500)
            # The keyboard: from the card's ⋯, Tab reaches its title, a link, and Enter opens it.
            ready(opg, "/gallery", esel)
            opg.evaluate("(s) => document.querySelector(s + ' .tileMore').focus()", esel)
            opg.keyboard.press("Tab")
            desk["tab"] = opg.evaluate("""(s) => { const a = document.activeElement, c = document.querySelector(s);
              return a && c.contains(a) ? [a.tagName.toLowerCase(), a.className, a.getAttribute('href'), a.textContent.trim()] : null; }""", esel)
            opg.keyboard.press("Enter")
            desk["enter"] = follow(opg, "/gallery")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is its rows' red
            desk["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        close_ctx(octx, opg)
        check("on a desk, Ctrl or the middle button opens the card in a new tab and this page stays: Home's card (in"
              " the face's column beside its row) and a Gallery card of Skribl's where a host says (at its time)",
              made and all(desk.get(k) == (w, p_) for k, w, p_ in (("home ctrl", to_post, "/social/"),
                                                                  ("home middle", to_post, "/social/"),
                                                                  ("gallery ctrl", to_lone, "/gallery"),
                                                                  ("gallery middle", to_lone, "/gallery"))),
              f"{ {k: desk.get(k) for k in ('home ctrl', 'home middle', 'gallery ctrl', 'gallery middle', 'stopped')} }")
        check("...pressing on a Gallery card's caption and pulling selects its words and opens nothing, and a drag"
              " across its ground opens nothing: a drag is not a tap",
              made and (desk.get("select") or ("", ""))[0].strip() == "From the gallery tick"
              and (desk.get("select") or ("", ""))[1] == "/gallery" and desk.get("drag") == "/gallery",
              f"select {desk.get('select')}; drag {desk.get('drag')}")
        check("...and for a keyboard the card's title is its link: Tab from its ⋯ reaches it, and Enter opens the"
              " card's page",
              made and (desk.get("tab") or [None])[0] == "a"
              and urllib.parse.urlsplit((desk.get("tab") or [None, None, ""])[2] or "").path == to_lone
              and desk.get("enter") == to_lone, f"tab {desk.get('tab')}; enter {desk.get('enter')}")

        # ⋯ ON A GALLERY CARD where a host says (Skribl's, signed out, on its
        # /gallery given the site's address; the first visit's until Nov 14):
        # Open goes to the card's page, in this tab as a tap does, and Copy
        # link and Share… give its address.
        ctx, cpg = browser_as(b, None, "phone", "light")
        cpg.add_init_script(SITE_OPENS)
        ctx.add_init_script("Object.defineProperty(navigator, 'share', { configurable: true,"
                            " value: d => { window.__shared = d && d.url; return Promise.resolve(); } });")
        menu12 = {}
        try:
            for act in ("Copy link", "Share", "Open"):
                ready(cpg, "/gallery", TILE.format(g_sid))
                cpg.evaluate("() => { if (window.SkriblPostedUI) SkriblPostedUI.copyText = t => { window.__copied = t;"
                             " return Promise.resolve(true); }; }")
                cpg.locator(TILE.format(g_sid) + " .tileMore").tap()
                cpg.locator(f'.cardMenu .cmItem:has-text("{act}")').tap()
                if act == "Open":
                    menu12[act] = follow(cpg, "/gallery")
                else:
                    cpg.wait_for_timeout(400)
                    menu12[act] = cpg.evaluate("() => window.__copied || window.__shared || null")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            menu12["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        check("a Gallery card's ⋯ where a host says: Open goes to the card's page in this tab (followed, a post's drawing its"
              " post), and Copy link and Share… give the card's address",
              made and menu12.get("Open") == to_post
              and menu12.get("Copy link") == BASE + f"/social/b/{g_sid}" and menu12.get("Share") == BASE + f"/social/b/{g_sid}",
              f"{menu12}")

        # SKRIBL'S OWN /gallery IS AS IT WAS: the site says nothing for Skribl's
        # pages, so its section carries no address, a card's title is no link, a
        # tap on its ground opens nothing, and ⋯ → Open opens the player's page
        # in a new tab.
        ctx, cpg = browser_as(b, mira, "phone", "light")
        own = {}
        try:
            gsel = TILE.format(lone)
            ready(cpg, "/gallery", gsel)
            own["root"] = cpg.evaluate("() => document.querySelector('[data-skribl-gallery]').hasAttribute('data-skribl-open')")
            own["title"] = cpg.evaluate("(s) => document.querySelector(s + ' .tt').tagName.toLowerCase()", gsel)
            cpg.mouse.click(*cpg.evaluate(SPOT12, [gsel, "ground"]))
            own["ground"] = follow(cpg, "/gallery", 1500)
            ready(cpg, "/gallery", gsel)
            cpg.locator(gsel + " .tileMore").tap()
            own["open"] = (newtab(lambda: cpg.locator('.cardMenu .cmItem:has-text("Open")').tap(), ctx), follow(cpg, "/gallery", 600))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            own["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        check("Skribl's own /gallery is as it was: no address on its section, a card's title is no link, a tap on its"
              " ground opens nothing, and ⋯ → Open opens the player's page in a new tab",
              made and own.get("root") is False and own.get("title") == "div" and own.get("ground") == "/gallery"
              and own.get("open") == (f"/s/{lone}", "/gallery"), f"{own}")

    # ------------------------------------------------------------------ 13
    # THE GALLERY OF EVERYONE (the map's step 3; the Gallery mock's B and the
    # owner's "Your picks are great", Nov 13): Explore lists the site's own
    # posts as their drawings, each tile one link to its post, Following |
    # Everyone on top (Home's own pill), New, Hot and a search under it; and
    # since the owner's "Yes, your picks" (Nov 14) every skribl the site's
    # people shared, a drawing shown outside a post a tile opening its own
    # page, both kinds in one order.
    # Quin looks (following Gwen alone, muting and blocking nobody); Gwen,
    # Hugo and Ivy share. Every post here says one word nothing else in the
    # suite says (G13), so a search on it is this section's own posts
    # whatever the sections before it made; Everyone and Load more are read
    # against the database itself.
    if part(13, "the Gallery of everyone: every skribl as drawings, two across and three, a tap opens its post"):
        from datetime import datetime, timedelta, timezone
        G13 = "gal" + secrets.token_hex(3)
        gwen = someone(b, "galgwen", "Gwen Lark")
        hugo = someone(b, "galhugo", "Hugo Bell")
        ivy = someone(b, "galivy", "Wilhelminaconstance Moss")
        quin = someone(b, "galquin", "Quin Hale")
        DARK_PAPER = (16, 20, 24)

        def timed(ms, seed=0, flip=False, size=(816, 612), bg="#f6f2ea", n=40):
            """A drawing drawn over `ms` (its points' own times), or a Flip of
            three pages: what the line says before it is played."""
            step = ms / (n - 1)
            pts = [{"x": round(size[0] / 2 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
                    "y": round(size[1] / 2 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
                    "color": "#7c5cff", "size": 6 + (i % 4), "t": round(i * step), "start": i == 0} for i in range(n)]
            body = {"version": 2, "schemaVersion": 2, "playbackMode": "flip" if flip else "replay",
                    "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
                    "frames": [{"strokes": pts, "strokeGroups": [n], "background": {"color": bg}}]}
            if flip:
                body["fps"] = 12
                body["frames"] += [{"strokes": [dict(p, x=p["x"] + 20 * k) for p in pts], "strokeGroups": [n],
                                    "background": {"color": bg}} for k in (1, 2)]
            return body

        def card_of(w, h, paper=None):
            """share_card(), its drawing's paper dark when asked (the ▶'s words over a dark drawing)."""
            if Image is None:
                return None
            if paper is None:
                return share_card(w, h)
            x, y, dw, dh = plate_of(w, h)
            im = Image.new("RGB", (1200, 630), CARD_GROUND)
            d = ImageDraw.Draw(im)
            d.rectangle([0, 546, 1199, 629], fill=CARD_FOOT)
            d.rectangle([x, y, x + dw - 1, y + dh - 1], fill=paper, outline=CARD_LINE, width=3)
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        clients = {}

        def share(who, words, body, size=(816, 612), paper=None):
            """A post as the composer sends one, its share card the colours share_card() paints."""
            c = clients.get(who.handle)
            if c is None:
                c = clients[who.handle] = who.client()
                c.get("/social/")
            body["thumbnail"] = card_of(*size, paper=paper)
            st, j = c.post_json("/social/posts", {"words": words, "payload": body})
            time.sleep(0.012)
            return (j.get("post") if st == 200 and isinstance(j, dict) else None)

        def wdb(sql, args=()):
            con = sqlite3.connect(DB, timeout=10)
            try:
                con.execute(sql, args)
                con.commit()
            finally:
                con.close()

        # What is shared: some of Ivy's first (two pages of the Gallery at
        # least), then a 4:3 drawing of 15 seconds, a Flip of three pages, a
        # tall one of four minutes, one on a dark paper of an hour and five
        # minutes, Quin's own and Gwen's newest, all on the first page.
        # Among Ivy's, after her eighth: a drawing she shows from the Pad on its
        # own, outside a post (d13): the 24th newest of the section's own, so
        # the search's first page ends on it and Load more goes on from a
        # drawing (since Nov 14 the Gallery is every skribl).
        fill, d13 = [], None
        for i in range(24):
            fill.append(share(ivy, f"{G13} filler {i:02d}", timed(2000 + i, 10 + i)))
            if i == 7:
                ivy.pg.goto(BASE + "/social/")
                _, d13 = ivy.pg.evaluate(PAD, [f"{G13} Ivy's drawing between posts", "public", 135])
                time.sleep(0.012)
        p_a = share(gwen, f"{G13} lighthouse at dusk", timed(15015, 1))
        p_flip = share(gwen, f"{G13} a flip of three", timed(3000, 2, flip=True))
        p_b = share(hugo, f"{G13} a tall one", timed(240000, 3, size=(531, 944)), size=(531, 944))
        p_c = share(ivy, f"{G13} under a dark sky", timed(3900000, 4, bg="#101418"), paper=DARK_PAPER)
        p_q = share(quin, f"{G13} Quin's own", timed(5000, 5))
        p_g2 = share(gwen, f"{G13} Gwen's newest", timed(7000, 6))
        made13 = all([p_a, p_flip, p_b, p_c, p_q, p_g2] + fill)
        sid = {k: (post_row(v) or (None, None))[1] for k, v in
               (("a", p_a), ("flip", p_flip), ("b", p_b), ("c", p_c), ("q", p_q), ("g2", p_g2)) if v}
        # NOT POSTS: a drawing Gwen showed in the gallery outside a post (the
        # Pad on its own), one she kept link-only, her face, and one by somebody
        # not on the site. Since Nov 14 the first is a tile, opening its own
        # page (the Gallery is every skribl); the other three never are.
        gwen.pg.goto(BASE + "/social/")
        _, lone13 = gwen.pg.evaluate(PAD, [f"{G13} shown outside a post", "public", 131])
        _, kept13 = gwen.pg.evaluate(PAD, [f"{G13} kept link-only", "unlisted", 132])
        fc = gwen.client()
        fc.get("/social/you/edit")
        _, fj = fc.post_json("/social/you/face", {"payload": drawing(seed=133, size=(707, 707))})
        face13 = fj.get("face") if isinstance(fj, dict) else None
        nb_ctx, nb_pg = browser_as(b, None)
        nb_pg.goto(BASE + "/skribl-pad")
        nb_pg.wait_for_timeout(600)
        _, nobody13 = nb_pg.evaluate(PAD, [f"{G13} nobody's", "public", 134])
        close_ctx(nb_ctx, nb_pg)
        # Likes and comments: Gwen's 4:3 has two hearts and one comment; Ivy's
        # dark one a comment and no heart; Hugo's tall one neither.
        for who, post_id, like, say_ in ((quin, p_a, True, None), (hugo, p_a, True, "Lovely light"),
                                         (gwen, p_c, False, "So dark, so good")):
            c = who.client()
            c.get(f"/social/p/{post_id}")
            if like:
                c.post_json(f"/social/p/{post_id}/like", {"liked": True})
            if say_:
                c.post_json(f"/social/p/{post_id}/comments", {"words": say_})
        qc = quin.client()
        qc.get("/social/@galgwen")
        followed = qc.post_json("/social/@galgwen/follow", {"following": True})[0]
        # PLAYS: Gwen's 4:3 played by three this week, Hugo's by two, Ivy's dark
        # one by one this week and by five eight days ago (outside the window).
        # And Gwen's drawing shown outside a post by two this week, as many as
        # Hugo's post and newer: Hot ranks both kinds in one order.
        sid["lone"] = lone13
        for key, n in (("a", 3), ("b", 2), ("c", 1), ("lone", 2)):
            for _ in range(n):
                urllib.request.urlopen(urllib.request.Request(BASE + f"/api/skribls/{sid.get(key)}",
                                                              headers={"X-Forwarded-For": address()}), timeout=30).read()
        old = (datetime.now(timezone.utc) - timedelta(days=8))
        c_row = db("select id from skribl_posts where public_id = ?", (sid.get("c"),))
        for k in range(5):
            wdb("insert into skribl_views (post_id, viewer_hash, day, created_at) values (?, ?, ?, ?)",
                (c_row[0][0], f"gal13-old-{k}", old.strftime("%Y-%m-%d"), old.strftime("%Y-%m-%d %H:%M:%S.%f")))

        def getj(cl, path):
            st_, text = cl._req("GET", path)
            try:
                return st_, json.loads(text)
            except ValueError:
                return st_, None

        HREF13 = {}

        def walk(cl, show="everyone", sort="new", q=""):
            """The Gallery walked to its end with Load more: (its tiles, a post's by its address and a drawing
            shown outside a post by its skribl's, their drawings' skribls, page sizes, cursors)."""
            qs = "&".join(x for x in (f"show={show}", f"sort={sort}", "q=" + urllib.parse.quote(q) if q else "") if x)
            posts, sids, sizes, cursors = [], [], [], []
            st_, j = getj(cl, "/social/explore/more?" + qs)
            while isinstance(j, dict):
                pairs = re.findall(r'<a class="gal-tile" href="/social/([pb])/([^"]+)"', j.get("html", ""))
                HREF13.update({x: f"/social/{k}/{x}" for k, x in pairs})
                got = [x for _, x in pairs]
                posts += got
                sids += re.findall(r'class="gal-plate"[^>]*><img src="[^"]*/s/([A-Za-z0-9_-]+)/poster"', j.get("html", ""))
                sizes.append(len(got))
                if not j.get("next") or len(sizes) > 40:
                    break
                cursors.append(j["next"])
                st_, j = getj(cl, "/social/explore/more?" + qs + "&before=" + urllib.parse.quote(j["next"]))
            return posts, sids, sizes, cursors

        # The database's own Gallery, both kinds in one order (time, a drawing
        # before the posts of its moment, then the address), each with its
        # maker's handle: every post not taken down nor hidden, its drawing
        # still there; every public skribl of the site's people that is no
        # post's, no comment's and not their face.
        ORACLE13 = ("select x.id, x.handle from ("
                    "select p.public_id id, p.created_at at, 'p' k, pe.handle handle from social_posts p"
                    " join social_people pe on pe.id = p.person_id join skribl_posts s on s.public_id = p.skribl_id"
                    " where p.taken_down_at is null and pe.taken_down_at is null and p.gallery_hidden_at is null"
                    " and s.visibility in ('public', 'unlisted')"
                    " union all select s.public_id, s.created_at, 's', pe.handle from skribl_posts s"
                    " join social_people pe on pe.public_id = s.user_id where s.visibility = 'public'"
                    " and pe.taken_down_at is null and s.public_id not in (select skribl_id from social_posts)"
                    " and s.public_id not in (select skribl_id from social_comments where skribl_id is not null)"
                    " and (pe.face_id is null or pe.face_id != s.public_id)"
                    ") x order by x.at desc, x.k desc, x.id desc")
        oracle_rows = db(ORACLE13)
        oracle = [r[0] for r in oracle_rows]
        maker13 = {r[0]: r[1] for r in oracle_rows}
        anon = Client()
        anon.get("/social/explore")
        q_cl = quin.client()
        q_cl.get("/social/explore")
        a_posts, a_sids, a_sizes, a_curs = walk(anon)
        q_posts, q_sids, q_sizes, q_curs = walk(q_cl)
        not_posts = {kept13, face13, nobody13}
        mine13 = ([lone13, p_g2, p_q, p_c, p_b, p_flip, p_a] + list(reversed(fill[8:])) + [d13]
                  + list(reversed(fill[:8])))
        check("THE GALLERY IS EVERY SKRIBL (the owner's \"I thought gallery was only skribls (pad or flip)?\", Nov 14):"
              " walked to its end (signed out, and signed in) it is every post and every drawing the site's people"
              " showed outside a post, once each, newest first in one order, a Flip's too, read against the database"
              " itself; a post's tile opens its post and a drawing's its own page; never one kept link-only, a face, or"
              " one by somebody not on the site",
              made13 and bool(lone13 and d13 and kept13 and face13 and nobody13) and a_posts == oracle and q_posts == oracle
              and all(m in oracle for m in mine13) and [x for x in oracle if x in mine13] == mine13
              and HREF13.get(lone13) == f"/social/b/{lone13}" and HREF13.get(d13) == f"/social/b/{d13}"
              and HREF13.get(p_a) == f"/social/p/{p_a}"
              and not (not_posts & set(a_sids)) and not (not_posts & set(q_sids)) and {lone13, d13} <= set(a_sids)
              and len(a_sids) == len(a_posts) and set(a_sids) >= {sid.get("a"), sid.get("flip"), sid.get("b")},
              f"made {made13}; signed out {len(a_posts)} of {len(oracle)} (same {a_posts == oracle}), signed in"
              f" {len(q_posts)} (same {q_posts == oracle}); the drawings {HREF13.get(lone13)}, {HREF13.get(d13)};"
              f" never these, among them {sorted(x for x in not_posts & (set(a_sids) | set(q_sids)) if x)}")
        new_cur = re.compile(r"\d{16}\.[ps][A-Za-z0-9_-]{11}")

        def raw_of(cur, hot=False):
            try:
                body = cur[2:] if hot else cur
                return base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
            except Exception:  # noqa: BLE001 -- unreadable is the row's red
                return ""
        g_tiles, _, g_sizes, g_curs = walk(q_cl, "everyone", "new", G13)
        check("Load more walks it a page of 24 at a time, every page whole but the last, by a cursor that names a"
              " time and a post's or a drawing's public id, never an internal id; THROUGH BOTH KINDS: a page that ends on"
              " a drawing shown outside a post goes on from it, the posts of its moment and older next, none twice and"
              " none missed",
              len(a_sizes) >= 2 and all(n == 24 for n in a_sizes[:-1]) and 0 < a_sizes[-1] <= 24
              and all(new_cur.fullmatch(raw_of(c)) for c in a_curs)
              and g_sizes == [24, len(mine13) - 24] and len(g_curs) == 1 and raw_of(g_curs[0]).endswith(".s" + str(d13))
              and g_tiles == mine13,
              f"pages {a_sizes}; cursors {[raw_of(c) for c in a_curs[:2]]}; the section's own {g_sizes}, its cursor"
              f" {[raw_of(c) for c in g_curs]} (Ivy's drawing {d13}), in order {g_tiles == mine13}")

        # FOLLOWING | EVERYONE: Following is the people Quin follows (Gwen) and
        # Quin; Everyone everybody (here, the section's own, by its word).
        f_posts, _, _, _ = walk(q_cl, "following")
        e_posts, _, _, _ = walk(q_cl, "everyone", q=G13)
        gwen_quin = [x for x in oracle if maker13.get(x) in ("galgwen", "galquin")]
        check("Following holds only the people you follow and your own (Quin follows Gwen: hers and Quin's, newest"
              " first, her drawing shown outside a post among them); Everyone holds everybody's",
              followed == 200 and f_posts == gwen_quin and set(f_posts) >= {p_a, p_flip, p_q, p_g2, lone13}
              and e_posts == mine13,
              f"follow {followed}; following {len(f_posts)} (want {len(gwen_quin)}), Hugo's or Ivy's among them"
              f" {[x for x in f_posts if x in (p_b, p_c)]}; everyone {len(e_posts)} of {len(mine13)}")

        # HOT: plays in the last seven days, most first, newest first among equals.
        h_posts, _, h_sizes, h_curs = walk(q_cl, "everyone", "hot", G13)
        zero = [x for x in mine13 if x not in (p_a, lone13, p_b, p_c)]
        hot_cur = re.compile(r"\d+\|\d{16}\|[ps][A-Za-z0-9_-]{11}\|\d{16}")
        check("Hot is plays in the last seven days, most first, both kinds in one order: three this week, then two (the"
              " drawing shown outside a post, newer, before the post), then one (five eight days ago count for"
              " nothing), then the rest newest first; Load more keeps its order, by a cursor that holds the moment it"
              " was ranked at and names no internal id, and goes on from a drawing too",
              h_posts == [p_a, lone13, p_b, p_c] + zero and h_sizes == [24, len(mine13) - 24]
              and all(c.startswith("h.") and hot_cur.fullmatch(raw_of(c, hot=True)) for c in h_curs)
              and len(h_curs) == 1 and f"|s{d13}|" in raw_of(h_curs[0], hot=True),
              f"first {[{p_a: 'a3', lone13: 'lone2', p_b: 'b2', p_c: 'c1'}.get(x, x) for x in h_posts[:5]]}; pages {h_sizes};"
              f" cursors {[raw_of(c, hot=True) for c in h_curs[:1]]}")

        # SEARCH: the post's words, a drawing's title, the maker's name and
        # @handle; nothing else.
        found = {q: walk(q_cl, "everyone", "new", q)[0] for q in
                 ("lighthouse at dusk", "Hugo Bell", "galivy", "@galivy", "WILHELMINACONSTANCE", "zz" + G13,
                  f"{G13} shown outside", "drawing between POSTS", f"{G13} kept link-only")}
        ivy_all = [x for x in mine13 if x in fill or x in (p_c, d13)]
        check("a search finds a post by its words, a drawing shown outside a post by its title (any case), and its maker"
              " by name or @handle (any case), and nothing else; never a drawing kept link-only; a search that finds"
              " nothing finds nothing",
              found["lighthouse at dusk"] == [p_a] and found["Hugo Bell"] == [p_b]
              and found["galivy"] == ivy_all and found["@galivy"] == ivy_all
              and found["WILHELMINACONSTANCE"] == ivy_all and found["zz" + G13] == []
              and found[f"{G13} shown outside"] == [lone13] and found["drawing between POSTS"] == [d13]
              and found[f"{G13} kept link-only"] == [],
              json.dumps({k: len(v) for k, v in found.items()}) + f"; Ivy's {len(ivy_all)}")

        # THE TILES, ON A TOUCH PHONE AND A DESK (light): two across and three,
        # the drawing's box 650 x 486, its ▶ and words at the bottom left, the
        # face 22px, the first name, the counts only when there are some.
        GEO = """(ids) => { const out = {}; const all = [...document.querySelectorAll('.gal-tile')];
          const rows = {}; all.slice(0, 6).forEach(a => { const r = a.getBoundingClientRect(); (rows[Math.round(r.top)] = rows[Math.round(r.top)] || []).push(r); });
          const tops = Object.keys(rows).map(Number).sort((x, y) => x - y);
          const first = (rows[tops[0]] || []).sort((x, y) => x.left - y.left), second = rows[tops[1]] || [];
          out.columns = first.length;
          out.colGap = first.length > 1 ? Math.round((first[1].left - first[0].right) * 10) / 10 : null;
          out.rowGap = second.length ? Math.round((second[0].top - first[0].bottom) * 10) / 10 : null;
          out.tiles = {};
          ids.forEach(id => { const a = document.querySelector('.gal-tile[data-post="' + id + '"]'); if (!a) return;
            const pic = a.querySelector('.gal-pic').getBoundingClientRect(), dur = a.querySelector('.gal-dur'), d = dur.getBoundingClientRect();
            const ring = a.querySelector('.gal-by .face-ring'), f = ring.getBoundingClientRect(), nm = a.querySelector('.gal-by b'), ns = getComputedStyle(nm);
            const n = a.querySelector('.gal-n'), tri = dur.querySelector('svg').getBoundingClientRect(), r = a.getBoundingClientRect();
            // The name's own width (a range round its words) and the room its row has left for it: the row less the
            // face, the counts and the gaps between. A NAME FITS OR NOT BY THESE TWO, in whatever face draws it.
            const by = a.querySelector('.gal-by'), rg = document.createRange(); rg.selectNodeContents(nm);
            const rest = [...by.children].filter(c => c !== nm), gap = parseFloat(getComputedStyle(by).columnGap) || 0;
            const room = by.getBoundingClientRect().width - rest.reduce((w, c) => w + c.getBoundingClientRect().width, 0) - gap * rest.length;
            out.tiles[id] = { ratio: Math.round(pic.width / pic.height * 10000) / 10000, durL: Math.round((d.left - pic.left) * 10) / 10,
              durB: Math.round((pic.bottom - d.bottom) * 10) / 10, durH: Math.round(d.height * 10) / 10, tri: Math.round(tri.width * 10) / 10,
              words: (dur.querySelector('span') || { textContent: '' }).textContent.trim(),
              face: [Math.round(f.width * 10) / 10, Math.round(f.height * 10) / 10, getComputedStyle(ring).borderRadius,
                     !!ring.querySelector('img'), !!ring.querySelector('.face-blank'), ring.textContent.trim()],
              name: nm.textContent, weight: ns.fontWeight, ellipsis: ns.textOverflow + ' ' + ns.whiteSpace + ' ' + ns.overflowX,
              cut: nm.scrollWidth > nm.clientWidth + 0.5, inside: nm.getBoundingClientRect().right <= r.right + 0.5,
              natural: Math.round(rg.getBoundingClientRect().width * 10) / 10, room: Math.round(room * 10) / 10,
              counts: n ? [...n.children].map(s => [s.className, s.textContent.trim(), Math.round(s.querySelector('svg').getBoundingClientRect().width)]) : null,
              link: a.tagName.toLowerCase() + ' ' + a.getAttribute('href'), label: a.getAttribute('aria-label') }; });
          return out; }"""
        geo = {}
        for screen in ("phone", "desk"):
            ctx, cpg = browser_as(b, quin, screen, "light")
            cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
            cpg.wait_for_timeout(700)
            geo[screen] = cpg.evaluate(GEO, [p_a, p_flip, p_b, p_c])
            close_ctx(ctx, cpg)
        WANT_WORDS = {p_a: "15 sec", p_flip: "3 pages", p_b: "4 min", p_c: "1 hr 5 min"}
        WANT_N = {p_a: [["gal-likes", "2", 14], ["gal-comments", "1", 14]], p_flip: None, p_b: None,
                  p_c: [["gal-comments", "1", 14]]}
        cols = {s: (geo[s].get("columns"), geo[s].get("colGap"), geo[s].get("rowGap")) for s in geo}
        check("the tiles are two across on a touch phone and three on a desk, 20px apart and rows 22px apart on both"
              " (a tile's own room round each picture and 8px of the page between two: section 22; they were 12 and"
              " 18, and 20 and 26 on a desk, under the bands), each one link to its post, the drawing's box 650 x 486",
              cols.get("phone") == (2, 20, 22) and cols.get("desk") == (3, 20, 22)
              and all(abs(t["ratio"] - 650 / 486) <= 0.003 and t["link"].startswith("a /social/p/")
                      for s in geo for t in geo[s]["tiles"].values()) and all(len(geo[s]["tiles"]) == 4 for s in geo),
              f"{cols}; ratios {[t['ratio'] for t in geo.get('phone', {}).get('tiles', {}).values()]}")
        # What the player's own play button says at rest, on Home (Hugo follows
        # nobody: Everyone), for the same drawings.
        ctx, cpg = browser_as(b, hugo, "phone", "light")
        cpg.goto(BASE + "/social/")
        cpg.wait_for_timeout(1200)
        player_says = cpg.evaluate("""(ids) => Object.fromEntries(ids.map(id => { const c = document.querySelector('.post-card[data-post="' + id + '"]');
          const s = c && c.querySelector('.skribl-inline-play span'); return [id, s ? s.textContent.trim() : null]; }))""",
                                   [p_a, p_flip, p_b, p_c])
        close_ctx(ctx, cpg)
        bare = {k: (v[9:] if (v or "").startswith("drawn in ") else v) for k, v in player_says.items()}
        check("each tile's ▶ says what the player's play button says at rest, without \"drawn in\" (15 sec, 4 min,"
              " 1 hr 5 min; a Flip its pages), 8px in from the box's bottom left, 24px tall, its ▶ 9px",
              all(geo[s]["tiles"].get(k, {}).get("words") == w == bare.get(k) for s in geo for k, w in WANT_WORDS.items())
              and all(t["durL"] == 8 and t["durB"] == 8 and t["durH"] == 24 and t["tri"] == 9
                      for s in geo for t in geo[s]["tiles"].values()),
              f"tiles {[geo.get('phone', {}).get('tiles', {}).get(k, {}).get('words') for k in WANT_WORDS]};"
              f" the player {player_says}; place {[(t['durL'], t['durB'], t['durH'], t['tri']) for t in geo.get('phone', {}).get('tiles', {}).values()]}")
        # CUT ONLY WHEN IT DOESN'T FIT, AND THEN ALWAYS, read as that rule: the name's own width against the room
        # its row has left, on every tile, a phone and a desk. (Main red after #1036, both databases, on
        # "Gwen Lark is whole beside two counts on a phone": true in this box's Inter, 72px in a room of 80, and not
        # in CI's DejaVu Sans, 83px. The tiles had taken 4px of the row, and the sample had fitted CI's face by one.
        # A sample that fits is a fact about a font; the rule holds in any.) A pixel either side of the edge is
        # either's: the browser's own two widths are whole numbers. THE OWNER'S "whole, never its first word" is
        # pinned where it is true in every face: beside no counts on a phone, and on a desk's wider tile. AND WHAT
        # THE OLD SAMPLE HELD WITHOUT SAYING IT, said: beside a heart's count and a comment's, a phone's tile
        # keeps the name ROOM13 or more (80 as built, 84 before the tiles; ten letters or so in the faces the site
        # is drawn in). Digits are near one width in every face, so this floor is the layout's and not a font's.
        ROOM13 = 78

        def name_cut_by_rule(t):
            return (t["cut"] or t["natural"] <= t["room"] + 1) and (not t["cut"] or t["natural"] >= t["room"] - 1)
        check("under it the maker's face at 22px (their drawn face, or the empty circle, never an initial) and name"
              " as they wrote it, whole (\"Gwen Lark\", never its first word: the owner's \"Your picks\", Nov 14; 600,"
              " cut with an ellipsis only when it doesn't fit and then always, its own width against the room its"
              " row has left, in whatever face draws it; beside two counts a phone's tile keeps it 78px or more;"
              " never past the tile; a screen reader hears it whole too),"
              " and the hearts and comments each only when there are some, their icons 14px",
              all(t["face"][:3] == [22, 22, "50%"] and not t["face"][5] for s in geo for t in geo[s]["tiles"].values())
              and all(geo[s]["tiles"][p_a]["face"][3] and geo[s]["tiles"][p_b]["face"][4] for s in geo)
              and all(geo[s]["tiles"][k]["name"] == n_ for s in geo for k, n_ in
                      ((p_a, "Gwen Lark"), (p_b, "Hugo Bell"), (p_c, "Wilhelminaconstance Moss")))
              and all((geo[s]["tiles"][p_a]["label"] or "").startswith("Gwen Lark: ") for s in geo)
              and all(name_cut_by_rule(t) for s in geo for t in geo[s]["tiles"].values())
              and not geo["phone"]["tiles"][p_flip]["cut"] and not geo["desk"]["tiles"][p_a]["cut"]
              and geo["phone"]["tiles"][p_a]["room"] >= ROOM13
              and all(t["weight"] == "600" and t["ellipsis"] == "ellipsis nowrap hidden" and t["inside"]
                      for s in geo for t in geo[s]["tiles"].values()) and geo["phone"]["tiles"][p_c]["cut"]
              and all(geo[s]["tiles"][k]["counts"] == v for s in geo for k, v in WANT_N.items()),
              f"{ {s: {k: (t['face'], t['name'], 'cut' if t['cut'] else 'whole', t['natural'], t['room'], t['counts']) for k, t in geo.get(s, {}).get('tiles', {}).items()} for s in geo} }")

        # THE DRAWING ON ITS PAPER: whole and alone, cut out of its share card
        # (the card's colours: share_card), a 4:3 filling the box, a tall one
        # its height and centred; read off the paint, on a desk.
        cut = []
        ctx, cpg = browser_as(b, quin, "desk", "light")
        cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
        for key, size in ((p_a, (816, 612)), (p_b, (531, 944))):
            sel = f'.gal-tile[data-post="{key}"]'
            try:
                cpg.locator(sel).scroll_into_view_if_needed(timeout=5000)
                cpg.wait_for_function("(s) => { const i = document.querySelector(s + ' .gal-plate img'); return i && i.complete && i.naturalWidth > 0; }",
                                      arg=sel, timeout=15000)
                cpg.wait_for_timeout(200)
                box = cpg.evaluate("""(s) => { const t = document.querySelector(s), pic = t.querySelector('.gal-pic').getBoundingClientRect();
                  const pl = t.querySelector('.gal-plate'), p = pl.getBoundingClientRect(), r = pl.querySelector('img').getBoundingClientRect(), k = r.width / 1200;
                  return { at: [(p.left - r.left) / k, (p.top - r.top) / k, p.width / k, p.height / k],
                           fill: [p.width - pic.width, p.height - pic.height], mid: (p.left + p.right) / 2 - (pic.left + pic.right) / 2 }; }""", sel)
                cpg.evaluate("(s) => { document.querySelector(s + ' .gal-dur').style.visibility = 'hidden'; }", sel)
                png = cpg.locator(sel + " .gal-pic").screenshot(timeout=5000) if Image else None
                cpg.evaluate("(s) => { document.querySelector(s + ' .gal-dur').style.visibility = ''; }", sel)
            except Exception as exc:  # noqa: BLE001 -- a tile that cannot be read is the row's red
                cut.append({"stopped": str(exc).splitlines()[0][:120]})
                continue
            card, marks = None, None
            if png:
                im = Image.open(io.BytesIO(png)).convert("RGB")
                W, H = im.size
                near = lambda c, t: abs(c[0] - t[0]) + abs(c[1] - t[1]) + abs(c[2] - t[2]) < 120
                card, marks = 0, [0, 0, 0, 0]
                for n_, c in enumerate(im.getdata()):
                    if near(c, CARD_GROUND) or near(c, CARD_FOOT) or near(c, CARD_LINE):
                        card += 1
                    elif near(c, CARD_MARK):
                        marks[(2 if n_ // W >= H / 2 else 0) + (1 if n_ % W >= W / 2 else 0)] += 1
            x, y, dw, dh = plate_of(*size)
            cut.append({"tile": "4:3" if key == p_a else "tall", "card": card, "marks": marks, "want": [x + 3, y + 3, dw - 6, dh - 6],
                        "at": [round(v, 1) for v in box["at"]], "fill": [round(v, 2) for v in box["fill"]], "mid": round(box["mid"], 2)})
        close_ctx(ctx, cpg)
        check("each tile is the drawing on its paper, whole and alone, cut out of its share card: none of the card's own"
              " ground, wordmark strip or plate line painted, the drawing's four corners painted, its plate 3 card pixels"
              " in from the line; a 4:3 drawing fills the box, a tall one is its height and in its middle",
              len(cut) == 2 and all(t.get("card") == 0 and t.get("marks") and min(t["marks"]) >= 20
                                    and all(abs(a - w) <= 1.0 for a, w in zip(t["at"], t["want"])) for t in cut)
              and all(abs(v) <= 1.0 for v in cut[0]["fill"]) and abs(cut[1]["fill"][1]) <= 1.0
              and cut[1]["fill"][0] < -50 and abs(cut[1]["mid"]) <= 1.0,
              f"{cut}")

        # THE BOX WEARS THE DRAWING'S OWN GROUND (the owner's "Your picks", Nov
        # 14: on their phone a tall drawing made on the Pad's dark canvas sat in
        # the tile's cream paper, cream bars at its sides). Hugo shares a tall one
        # on the Pad's own dark (#0d0f14) as a post, and one from the Pad outside
        # a post; each box is read off the paint in the middle of the bars beside
        # its plate: in the Gallery, on his Gallery tab (a post's tile, and one
        # shown outside a post: the listing it comes from says no ground, so the
        # site asks Skribl's description for it). His tall paper one keeps its paper (#f6f2ea),
        # and Gwen's 4:3 on paper, which fills its box, is the box it was.
        NIGHT, NIGHT_RGB = "night" + secrets.token_hex(3), (13, 15, 20)
        PAPER_RGB = (246, 242, 234)
        p_n = share(hugo, f"{NIGHT} a tall one in the dark", timed(4000, 7, size=(531, 944), bg="#0d0f14"),
                    size=(531, 944), paper=NIGHT_RGB)
        hugo.pg.goto(BASE + "/social/")
        _, d_n = hugo.pg.evaluate(PAD_ON, [f"{NIGHT} shown outside a post", "#0d0f14", 531, 944, 136])
        near_ = lambda c, t: abs(c[0] - t[0]) + abs(c[1] - t[1]) + abs(c[2] - t[2]) <= 12

        def bars_of(pg_, sel):
            """The colours painted in the middle of the bars beside a tile's plate, left and right."""
            try:
                pg_.wait_for_selector(sel, timeout=15000)
                at = pg_.evaluate(BARS, sel)
                pg_.wait_for_timeout(250)
                png = pg_.locator(sel + " :is(.gal-pic, .more-pic)").screenshot(timeout=5000) if Image else None
                if not (at and png):
                    return {"stopped": "no box" if not at else "no picture"}
                im = Image.open(io.BytesIO(png)).convert("RGB")
                k = im.size[1] / (2 * at["y"])          # the picture's pixels to one CSS pixel
                return {"bars": at["bars"], "left": im.getpixel((int(at["left"] * k), int(at["y"] * k))),
                        "right": im.getpixel((min(im.size[0] - 1, int(at["right"] * k)), int(at["y"] * k))),
                        "style": at["ground"]}
            except Exception as exc:  # noqa: BLE001 -- a box that cannot be read is the row's red
                return {"stopped": str(exc).splitlines()[0][:120]}

        def dark(got):
            return bool(got.get("bars")) and min(got["bars"]) >= 20 and near_(got.get("left", (0, 0, 0, 1)), NIGHT_RGB) \
                and near_(got.get("right", (0, 0, 0, 1)), NIGHT_RGB)
        grounds = {}
        ctx, cpg = browser_as(b, quin, "desk", "light")
        cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(NIGHT))
        grounds["gallery, dark"] = bars_of(cpg, f'.gal-tile[data-post="{p_n}"]')
        cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
        grounds["gallery, tall paper"] = bars_of(cpg, f'.gal-tile[data-post="{p_b}"]')
        cpg.wait_for_selector(f'.gal-tile[data-post="{p_a}"]', timeout=15000)
        grounds["gallery, 4:3 paper"] = cpg.evaluate("""(s) => { const pic = document.querySelector(s + ' .gal-pic');
          return [getComputedStyle(pic).backgroundColor, pic.getAttribute('style')]; }""", f'.gal-tile[data-post="{p_a}"]')
        cpg.goto(BASE + "/social/@galhugo/gallery")
        grounds["his Gallery tab, a post"] = bars_of(cpg, f'.gal-tile[data-post="{p_n}"]')
        grounds["his Gallery tab, outside a post"] = bars_of(cpg, f'.gal-tile[data-drawing="{d_n}"]')
        # (More from on a post's page wore it too, both kinds, until the Calm
        # Post Page took More from off the page, Nov 20: section 3 asks that it
        # is gone. A draw-back's tile on a post's page is the plate that is
        # left there: verify_socialdrawback 6 reads its ground.)
        close_ctx(ctx, cpg)
        check("THE BOX WEARS THE DRAWING'S OWN GROUND: in the Gallery a tall drawing made on the Pad's dark sits in its own"
              " dark, the bars beside it read off the paint (never the tile's cream); a paper drawing in the paper it had,"
              " a tall one's bars and a 4:3's box",
              bool(p_n) and dark(grounds["gallery, dark"])
              and min((grounds["gallery, tall paper"] or {}).get("bars") or [0]) >= 20
              and near_(grounds["gallery, tall paper"].get("left", (0, 0, 0)), PAPER_RGB)
              and near_(grounds["gallery, tall paper"].get("right", (0, 0, 0)), PAPER_RGB)
              and (grounds["gallery, 4:3 paper"] or [None])[0] == "rgb(246, 242, 234)",
              json.dumps({k: grounds.get(k) for k in ("gallery, dark", "gallery, tall paper", "gallery, 4:3 paper")}))
        check("...the same on its maker's Gallery tab, a post's tile and one shown outside a post (the site asks Skribl's"
              " description for its ground: the listing says none)",
              bool(d_n) and dark(grounds["his Gallery tab, a post"]) and dark(grounds["his Gallery tab, outside a post"]),
              json.dumps({k: grounds.get(k) for k in ("his Gallery tab, a post", "his Gallery tab, outside a post")}))

        # A TAP ANYWHERE ON A TILE OPENS ITS POST: a touch on a phone and a click
        # on a desk, on the drawing, its ▶, the face, the name, the counts, a
        # corner and the room between the drawing and the name; every 4px of it
        # is its one link; and the keyboard, from the search box, Tab and Enter.
        SPOTS = """(s) => { const t = document.querySelector(s); if (!t) return null;
          t.scrollIntoView({ block: 'center', behavior: 'instant' });
          const mid = e => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
          const pic = t.querySelector('.gal-pic').getBoundingClientRect(), by = t.querySelector('.gal-by').getBoundingClientRect();
          return { drawing: mid(t.querySelector('.gal-plate')), play: mid(t.querySelector('.gal-dur')), face: mid(t.querySelector('.gal-by .face-ring')),
                   name: mid(t.querySelector('.gal-by b')), counts: mid(t.querySelector('.gal-n')), corner: [pic.right - 4, pic.top + 4],
                   between: [pic.left + pic.width / 2, (pic.bottom + by.top) / 2] }; }"""
        tsel = f'.gal-tile[data-post="{p_a}"]'
        taps, tmaps = {}, {}
        for screen in ("phone", "desk"):
            ctx, cpg = browser_as(b, quin, screen, "light")
            try:
                for spot in ("drawing", "play", "face", "name", "counts", "corner", "between"):
                    cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
                    cpg.wait_for_selector(tsel, timeout=10000)
                    xy = cpg.evaluate(SPOTS, tsel)[spot]
                    if screen == "phone":
                        cpg.touchscreen.tap(*xy)
                    else:
                        cpg.mouse.click(*xy)
                    try:
                        cpg.wait_for_url(lambda u: "/social/p/" in u, timeout=5000)
                    except Exception:  # noqa: BLE001 -- staying is the row's red
                        pass
                    taps[(screen, spot)] = urllib.parse.urlsplit(cpg.url).path
                cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
                cpg.wait_for_selector(tsel, timeout=10000)
                tmaps[screen] = (cpg.evaluate(TAPMAP, [tsel, 4]) or {}).get("keys")
                if screen == "desk":
                    cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
                    cpg.wait_for_selector(tsel, timeout=10000)
                    cpg.focus("[data-gal-q]")
                    cpg.keyboard.press("Tab")
                    focus = cpg.evaluate("() => { const a = document.activeElement; return a ? [a.className, a.getAttribute('href')] : null; }")
                    cpg.keyboard.press("Enter")
                    try:
                        cpg.wait_for_url(lambda u: "/social/p/" in u or "/social/b/" in u, timeout=5000)
                    except Exception:  # noqa: BLE001 -- staying is the row's red
                        pass
                    taps[("desk", "keyboard")] = (focus, urllib.parse.urlsplit(cpg.url).path)
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                taps[(screen, "stopped")] = str(exc).splitlines()[0][:160]
            close_ctx(ctx, cpg)
        first_tile = walk(q_cl, "everyone", "new", G13)[0][:1]
        check("a tap anywhere on a tile opens its post: a touch on a phone and a click on a desk, on the drawing, its ▶,"
              " the face, the name, the counts, a corner and the room between the drawing and the name; every 4px of"
              " the tile is its one link; and from the search box Tab reaches the first tile and Enter opens it",
              all(taps.get((s, k)) == f"/social/p/{p_a}" for s in ("phone", "desk")
                  for k in ("drawing", "play", "face", "name", "counts", "corner", "between"))
              and all(m and set(m) == {"own|a.gal-tile"} for m in tmaps.values()) and len(tmaps) == 2
              and taps.get(("desk", "keyboard")) == (["gal-tile", HREF13.get(first_tile[0])],
                                                     HREF13.get(first_tile[0])) if first_tile else False,
              f"taps { {f'{s} {k}': v for (s, k), v in taps.items() if v != f'/social/p/{p_a}'} }; maps {tmaps}")

        # THE PILL: a tap on Following, read on every frame (light and dark, and
        # under Reduce Motion): the tint glides and starts before the tiles
        # change, the tiles fade and change only while they can't be seen, and
        # the page doesn't scroll; the address says Following, and a reload
        # opens on it.
        GFRAMES = r"""([ms]) => { window.__gf = []; const seg = document.querySelector('[data-gal-show]'), sl = seg.querySelector('.fo-slider');
          const swap = document.querySelector('[data-gal-swap]'), grid = document.querySelector('[data-gal-grid]'), t0 = performance.now();
          const sig = () => [...grid.children].slice(0, 4).map(e => e.getAttribute('data-post') || e.getAttribute('data-drawing')).join('|') + '#' + grid.children.length;
          const step = () => { const r = sl.getBoundingClientRect();
            window.__gf.push({ t: Math.round(performance.now() - t0), x: r.left, op: +getComputedStyle(swap).opacity, sig: sig(), y: window.scrollY });
            if (performance.now() - t0 < ms) requestAnimationFrame(step); };
          requestAnimationFrame(step); }"""
        FRAME = 1000 / 60

        def spans_of(ts):
            return [max(1.0, round((z - a) / FRAME)) for a, z in zip(ts, ts[1:])]

        def judge(fs, reduced):
            if len(fs) < 2:
                return {"ok": False, "frames": len(fs)}
            ts, xs, ops = [f["t"] for f in fs], [f["x"] for f in fs], [f["op"] for f in fs]
            sp = spans_of(ts)
            way = abs(xs[-1] - xs[0]) if fs else 0
            glides = len([1 for a, z in zip(xs, xs[1:]) if way and abs(z - a) / way > 0.005])
            gstep = round(max([abs(z - a) / n / way for a, z, n in zip(xs, xs[1:], sp)] or [0]), 3) if way else 0
            fstep = round(max([abs(z - a) / n for a, z, n in zip(ops, ops[1:], sp)] or [0]), 3)
            fading = len([1 for a, z in zip(ops, ops[1:]) if abs(z - a) > 0.005])
            change = next((i for i in range(1, len(fs)) if fs[i]["sig"] != fs[i - 1]["sig"]), None)
            started = change is not None and any(abs(fs[j]["x"] - fs[0]["x"]) > 0.3 for j in range(change + 1))
            out = {"glides": glides, "gstep": gstep, "way": round(way, 1), "fstep": fstep, "fading": fading,
                   "seen_at_change": fs[change]["op"] if change is not None else None, "started": started,
                   "scrolled": round(max(abs(f["y"] - fs[0]["y"]) for f in fs), 2) if fs else None,
                   "back": fs[-1]["op"] if fs else None}
            ok = (change is not None and out["seen_at_change"] <= 0.05 and fstep <= 0.35 and fading >= 8
                  and out["scrolled"] == 0 and out["back"] > 0.99 and way > 10)
            ok = ok and (glides <= 1 if reduced else (glides >= 8 and gstep <= 0.30 and started))
            out["ok"] = ok
            return out
        sw = {}
        for scheme, reduced in (("light", False), ("dark", False), ("light", True)):
            tag = scheme + (" reduced" if reduced else "")
            ctx, cpg = browser_as(b, quin, "phone", scheme, reduced=reduced)
            try:
                cpg.goto(BASE + "/social/explore")
                cpg.wait_for_selector("[data-gal-show][data-pill]", timeout=10000)
                cpg.wait_for_timeout(400)
                cpg.evaluate(GFRAMES, [1500])
                cpg.locator("[data-gal-show] button[data-show=following]").tap()
                cpg.wait_for_timeout(1900)
                got = judge(cpg.evaluate("() => window.__gf"), reduced)
                got["url"] = urllib.parse.urlsplit(cpg.url).query
                got["shown"] = cpg.evaluate("() => [...document.querySelectorAll('.gal-tile')].map(a => a.dataset.post || a.dataset.drawing)")[:30]
                cpg.reload()
                cpg.wait_for_timeout(700)
                got["after reload"] = cpg.evaluate("""() => [(document.querySelector('[data-gal-show] button[aria-pressed="true"]') || {}).textContent,
                  [...document.querySelectorAll('.gal-tile')].map(a => a.dataset.post || a.dataset.drawing).slice(0, 30)]""")
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                got = {"ok": False, "stopped": str(exc).splitlines()[0][:160]}
            sw[tag] = got
            close_ctx(ctx, cpg)
        f_page = f_posts[:24]
        check("a tap on Following, read on every frame from the tap (light and dark): the pill glides (eight frames or"
              " more, none more than 30% of the way) and starts before the tiles change; the tiles fade (none more than"
              " 35%), change only while they can't be seen (0.05 or less) and fade back; the page doesn't scroll; the"
              " address says Following and a reload opens on it",
              all(sw.get(t, {}).get("ok") and sw[t].get("url") == "show=following" and sw[t].get("shown") == f_page
                  and sw[t].get("after reload") == ["Following", f_page] for t in ("light", "dark")),
              json.dumps({t: {k: v for k, v in sw.get(t, {}).items() if k not in ("shown", "after reload")} for t in sw}))
        check("under Reduce Motion the pill is put there, as the site's pills are, and the tiles only fade, changing"
              " while unseen",
              bool(sw.get("light reduced", {}).get("ok")) and sw["light reduced"].get("shown") == f_page,
              json.dumps({k: v for k, v in sw.get("light reduced", {}).items() if k not in ("shown", "after reload")}))

        # THE READS ON THEIR INDEXES (docs/SOCIAL-SITE.md section 3, item 8:
        # every new query's plan checked in its suite): the Gallery is two
        # reads, each a page long, merged (since Nov 14, every skribl). New
        # reads the posts by their time's own index, newest first, with no sort
        # of its own; and the drawings shown outside a post by Skribl's index
        # for the gallery's (visibility, time), through shared_skribls, newest
        # first, sorting only those of one moment by their address, each asked
        # whether a post or a comment holds it on that table's own index. Hot
        # reads the week's plays on the views' time (Skribl's index, through
        # recent_plays) for both, and then orders by them, as the gallery's own
        # Hot does.
        PROBE = r"""
import json
from sqlalchemy import event
from app import app, db
from social import gallery
seen = []
def keep(conn, cursor, statement, params, context, executemany):
    if statement.lstrip().upper().startswith("SELECT") and ("FROM social_posts" in statement or "skribl_shared" in statement):
        seen.append((statement, params))
out = {}
with app.test_request_context("/social/explore"):
    for sort in ("new", "hot"):
        seen.clear()
        event.listen(db.engine, "before_cursor_execute", keep)
        gallery.page(None, "everyone", sort, "")
        event.remove(db.engine, "before_cursor_execute", keep)
        for kind, pick in (("posts", lambda s: "skribl_shared" not in s), ("drawings", lambda s: "skribl_shared" in s)):
            out[sort + " " + kind] = [r[3] for st, pr in [x for x in seen if pick(x[0])][:1]
                                      for r in db.session.connection().exec_driver_sql("EXPLAIN QUERY PLAN " + st, pr).fetchall()]
print("PLAN " + json.dumps(out))
"""
        pr = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
        plans = next((json.loads(ln[5:]) for ln in pr.stdout.splitlines() if ln.startswith("PLAN ")), {})
        nd = plans.get("new drawings", [])
        check("the Gallery's reads are on their indexes: New the posts by their time's own index, newest first, with no"
              " sort of its own, and the drawings shown outside a post by Skribl's (visibility, time) index (through"
              " shared_skribls), sorting no more than those of one moment, a post's and a comment's asked on their own"
              " indexes; Hot the week's plays by the views' time, both ends of the week (through recent_plays), for both",
              any("ix_social_posts_created" in x for x in plans.get("new posts", []))
              and not any("TEMP B-TREE" in x for x in plans.get("new posts", []))
              and any("ix_skribl_posts_visibility_created (visibility=?)" in x for x in nd)
              and not any("TEMP B-TREE FOR ORDER BY" in x for x in nd)
              and any("ix_social_posts_skribl_id (skribl_id=?)" in x for x in nd)
              and any("ix_social_comments_skribl_id (skribl_id=?)" in x for x in nd)
              and all(any("ix_skribl_views_created (created_at>? AND created_at<?)" in x for x in plans.get(k, []))
                      for k in ("hot posts", "hot drawings")),
              f"{plans or pr.stderr[-300:]}")

        # EVERY WORD AT 4.5:1, EVERY CONTROL 44px, THE BOX 16px (the suite's own
        # reader), phone and desk, light and dark; and the ▶'s words read off the
        # pixels under them (its glass over Ivy's drawing, dark paper).
        seen13, glass = {}, {}
        INK = (0x3a, 0x24, 0xa8)

        def lum(c):
            v = [x / 255 for x in c[:3]]
            v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, quin, screen, scheme, reduced=True)
                cpg.goto(BASE + "/social/explore?q=" + urllib.parse.quote(G13))
                cpg.wait_for_timeout(700)
                seen13[(screen, scheme)] = cpg.evaluate(READ, "main")
                dsel = f'.gal-tile[data-post="{p_c}"]'
                try:
                    cpg.locator(dsel).scroll_into_view_if_needed(timeout=5000)
                    cpg.wait_for_function("(s) => { const i = document.querySelector(s + ' .gal-plate img'); return i && i.complete && i.naturalWidth > 0; }",
                                          arg=dsel, timeout=15000)
                    cpg.wait_for_timeout(200)
                    box = cpg.evaluate("""(s) => { const d = document.querySelector(s + ' .gal-dur'), w = d.querySelector('span');
                      const a = d.getBoundingClientRect(), r = w.getBoundingClientRect(); w.style.color = 'transparent';
                      return [r.left - a.left, r.top - a.top, r.width, r.height, getComputedStyle(w).color]; }""", dsel)
                    png = cpg.locator(dsel + " .gal-dur").screenshot(timeout=5000)
                    im = Image.open(io.BytesIO(png)).convert("RGB")
                    px = [im.getpixel((int(box[0] + i), int(box[1] + j))) for i in range(int(box[2])) for j in range(int(box[3]))
                          if int(box[0] + i) < im.size[0] and int(box[1] + j) < im.size[1]]
                    ink = lum(INK)
                    glass[(screen, scheme)] = round(min((max(lum(p), ink) + 0.05) / (min(lum(p), ink) + 0.05) for p in px), 2) if px else None
                except Exception as exc:  # noqa: BLE001 -- a picture that cannot be read is the row's red
                    glass[(screen, scheme)] = str(exc).splitlines()[0][:100]
                close_ctx(ctx, cpg)
        low = [f"{' '.join(k)}: {x}" for k, v in seen13.items() for x in v["low"]]
        small = [f"{' '.join(k)}: {x}" for k, v in seen13.items() for x in v["small"]]
        fields = [f"{' '.join(k)}: {x}" for k, v in seen13.items() for x in v["fields"]]
        check("every word on the Gallery reads at 4.5:1 or more on what is painted behind it (the head, the pills, the"
              " box's words, the names and counts), every control is 44px or more each way and the search box 16px:"
              " phone and desk, light and dark",
              all(v["read"] >= 12 for v in seen13.values()) and not low and not small and not fields and len(seen13) == 4,
              f"read {[(' '.join(k), v['read'], v['lowest']) for k, v in seen13.items()]}; under 4.5: {low[:4]};"
              f" small: {small[:4]}; fields: {fields[:3]}")
        check("...and a tile's ▶ words read 4.5:1 or more off the pixels under them, its glass over a dark drawing:"
              " phone and desk, light and dark",
              len(glass) == 4 and all(isinstance(v, float) and v >= 4.5 for v in glass.values()),
              f"{ {' '.join(k): v for k, v in glass.items()} }")

    # ------------------------------------------------------------------ 8
    # ------------------------------------------------------------------ 14
    # THE FIRST VISIT, B (the owner's "Your picks", Nov 14): Home signed out
    # keeps its welcome; under "Fresh from everyone" the six newest tiles of
    # the Gallery of everyone, as /social/explore shows them signed out, then
    # "See the whole Gallery ›" (the small violet words, 44px) to it: where
    # Skribl's own Gallery section was, every public skribl, drawings by
    # people not on the site among them. Oda shares eight posts; then, newer
    # than all of them, she shows a drawing in the gallery outside a post,
    # keeps one link-only and draws her face, and somebody not on the site
    # shows one: since the Gallery is every skribl (Nov 14) the first is the
    # newest tile, opening its own page, and the other three never are.
    if part(14, "the first visit: the welcome, then the Gallery's six newest and See the whole Gallery ›"):
        F14 = "fv" + secrets.token_hex(3)
        oda = someone(b, "fvoda", "Oda Wren")
        oc = oda.client()
        oc.get("/social/")
        made14 = []
        for i in range(8):
            st_, j_ = oc.post_json("/social/posts", {"words": f"{F14} post {i}", "payload": drawing(seed=140 + i)})
            made14.append(j_.get("post") if st_ == 200 and isinstance(j_, dict) else None)
            time.sleep(0.012)
        oda.pg.goto(BASE + "/social/")
        _, lone14 = oda.pg.evaluate(PAD, [f"{F14} shown outside a post", "public", 141])
        _, kept14 = oda.pg.evaluate(PAD, [f"{F14} kept link-only", "unlisted", 142])
        fc14 = oda.client()
        fc14.get("/social/you/edit")
        _, fj14 = fc14.post_json("/social/you/face", {"payload": drawing(seed=143, size=(707, 707))})
        face14 = fj14.get("face") if isinstance(fj14, dict) else None
        nb_ctx, nb_pg = browser_as(b, None)
        nb_pg.goto(BASE + "/skribl-pad")
        nb_pg.wait_for_timeout(600)
        _, nobody14 = nb_pg.evaluate(PAD, [f"{F14} nobody's", "public", 144])
        close_ctx(nb_ctx, nb_pg)
        not14 = {x for x in (lone14, kept14, face14, nobody14) if x}
        made_ok = all(made14) and len(not14) == 4
        FV = """() => { const s = document.querySelector('.fresh'), h = s && s.querySelector('h2.sec'), a = s && s.querySelector('.fresh-more a');
          const tiles = s ? [...s.querySelectorAll('.gal-tile')] : [], cs = a ? getComputedStyle(a) : null, r = a ? a.getBoundingClientRect() : null;
          const probe = document.createElement('span'); probe.style.color = 'var(--accent-ink)'; document.body.append(probe);
          const accent = getComputedStyle(probe).color; probe.remove();
          const hid = a ? [...a.querySelectorAll('[aria-hidden="true"]')].map(e => e.textContent).join('') : null;
          return { welcome: !!document.querySelector('.hello #helloCard') && !!document.querySelector('.hello .cta [data-make]'),
                   heading: h ? h.textContent.trim() : null,
                   tiles: tiles.map(t => t.getAttribute('data-post') || t.getAttribute('data-drawing')),
                   drawings: tiles.filter(t => !t.hasAttribute('data-post')).map(t => t.getAttribute('href')),
                   srcs: tiles.map(t => (t.querySelector('.gal-plate img') || { getAttribute: () => '' }).getAttribute('src')),
                   inOrder: !!(h && a && tiles.length && (h.compareDocumentPosition(tiles[0]) & 4) && (tiles[tiles.length - 1].compareDocumentPosition(a) & 4)),
                   link: a ? { words: a.textContent.replace(hid, '').trim(), hidden: hid, href: a.getAttribute('href'),
                               h: Math.round(r.height * 100) / 100, ink: cs.color, accent: accent, weight: cs.fontWeight,
                               size: parseFloat(cs.fontSize), mid: Math.round((r.left + r.width / 2) - (s.getBoundingClientRect().left + s.getBoundingClientRect().width / 2)) } : null,
                   none: (document.querySelector('.fresh .feed-none') || {}).textContent || null,
                   skribls: !!document.getElementById('skriblGallery') || !!document.querySelector('[data-skribl-gallery]')
                            || [...document.querySelectorAll('link[rel=stylesheet]')].some(l => /gallerysection[.]css/.test(l.href)) }; }"""
        firsts = {}
        for screen in ("phone", "desk"):
            ctx, cpg = browser_as(b, None, screen, "light")
            cpg.goto(BASE + "/social/")
            cpg.wait_for_timeout(700)
            firsts[screen] = cpg.evaluate(FV)
            close_ctx(ctx, cpg)
        anon14 = Client()
        st_e, text_e = anon14._req("GET", "/social/explore/more?show=everyone&sort=new")
        try:
            explore6 = [x for _, x in re.findall(r'<a class="gal-tile" href="/social/([pb])/([^"]+)"',
                                                  json.loads(text_e).get("html", ""))][:6]
        except ValueError:
            explore6 = []
        # The database's own six newest, both kinds in one order: posts, and
        # public skribls of the site's people that are no post's, comment's or
        # face (section 13's oracle).
        oracle14 = [r_[0] for r_ in db(
            "select x.id from (select p.public_id id, p.created_at at, 'p' k from social_posts p"
            " join social_people pe on pe.id = p.person_id join skribl_posts s on s.public_id = p.skribl_id"
            " where p.taken_down_at is null and pe.taken_down_at is null and p.gallery_hidden_at is null"
            " and s.visibility in ('public', 'unlisted')"
            " union all select s.public_id, s.created_at, 's' from skribl_posts s join social_people pe"
            " on pe.public_id = s.user_id where s.visibility = 'public' and pe.taken_down_at is null"
            " and s.public_id not in (select skribl_id from social_posts)"
            " and s.public_id not in (select skribl_id from social_comments where skribl_id is not null)"
            " and (pe.face_id is null or pe.face_id != s.public_id)) x order by x.at desc, x.k desc, x.id desc limit 6")]
        fv_p = firsts.get("phone") or {}
        shown14 = {re.sub(r"^.*/s/([A-Za-z0-9_-]+)/poster.*$", r"\1", x or "") for v in firsts.values() for x in v.get("srcs", [])}
        want14 = [lone14] + list(reversed(made14))[:5]
        check("THE FIRST VISIT keeps its welcome (Blooby's card, Make a skribl), and under \"Fresh from everyone\" the six"
              " newest tiles of the Gallery of everyone: the first six /social/explore shows signed out, read against the"
              " database itself, phone and desk; six at most though more are shared",
              made_ok and all(v.get("welcome") and v.get("heading") == "Fresh from everyone" and v.get("inOrder")
                              and v.get("tiles") == explore6 == oracle14 for v in firsts.values())
              and len(explore6) == 6 and explore6 == want14,
              f"made {made_ok}; first visit {fv_p.get('tiles')}; explore {explore6}; database {oracle14};"
              f" want {want14}")
        check("...every skribl (since Nov 14): the drawing Oda showed outside a post, the newest, a tile opening its own"
              " page; never one kept link-only, a face, or one by somebody not on the site, though each is newer than the"
              " six; and nothing of Skribl's own Gallery section on the page",
              made_ok and all(v.get("drawings") == [f"/social/b/{lone14}"] and not v.get("skribls") for v in firsts.values())
              and not ((not14 - {lone14}) & shown14) and lone14 in shown14 and len(shown14) == 6,
              f"tiles of drawings outside a post {[v.get('drawings') for v in firsts.values()]}; Skribl's section"
              f" {[v.get('skribls') for v in firsts.values()]}; never-shown ones shown {sorted((not14 - {lone14}) & shown14)}")
        lk14 = fv_p.get("link") or {}
        went = {}
        for screen in ("phone", "desk"):
            ctx, cpg = browser_as(b, None, screen, "light")
            try:
                cpg.goto(BASE + "/social/")
                cpg.locator(".fresh-more a").scroll_into_view_if_needed(timeout=5000)
                with cpg.expect_navigation(timeout=15000):
                    if screen == "phone":
                        cpg.locator(".fresh-more a").tap()
                    else:
                        cpg.locator(".fresh-more a").click()
                went[screen] = (urllib.parse.urlsplit(cpg.url).path,
                                (cpg.locator(".page-title").text_content(timeout=5000) or "").strip())
            except Exception as exc:  # noqa: BLE001 -- not going is the row's red
                went[screen] = ("stopped", str(exc).splitlines()[0][:100])
            close_ctx(ctx, cpg)
        check("...then \"See the whole Gallery ›\" (the › hidden from a screen reader), in the small violet words"
              " (--accent-ink, 600, 16px), centred, 44px tall, a tap on a phone and a click on a desk landing on the Gallery",
              lk14.get("words") == "See the whole Gallery" and lk14.get("hidden") == "›" and lk14.get("href") == "/social/explore"
              and lk14.get("ink") == lk14.get("accent") and lk14.get("weight") == "600" and lk14.get("size") == 16
              and lk14.get("h", 0) >= 44 and abs(lk14.get("mid", 99)) <= 1
              and all(v == ("/social/explore", "Gallery") for v in went.values()) and len(went) == 2,
              f"{lk14}; landed {went}")
        seen14 = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, None, screen, scheme, reduced=True)
                cpg.goto(BASE + "/social/")
                cpg.wait_for_timeout(700)
                got = {"read": 0, "low": [], "small": [], "lowest": 99}
                for at in ("h2.sec", ".fresh .gal-tile:nth-of-type(3)", ".fresh-more a"):
                    cpg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.scrollIntoView({ block: 'center', behavior: 'instant' }); }", at)
                    cpg.wait_for_timeout(150)
                    r_ = cpg.evaluate(READ, ".fresh")
                    got["read"] += r_["read"]
                    got["low"] += r_["low"]
                    got["small"] += r_["small"]
                    got["lowest"] = min(got["lowest"], r_["lowest"])
                seen14[(screen, scheme)] = got
                close_ctx(ctx, cpg)
        check("...every word under \"Fresh from everyone\" reads at 4.5:1 or more on what is painted behind it (the"
              " names, the counts, the ▶'s words, the way to the Gallery), every control 44px: phone and desk, light"
              " and dark",
              all(v["read"] >= 12 and not v["low"] and not v["small"] for v in seen14.values()) and len(seen14) == 4,
              f"{ {' '.join(k): (v['read'], v['lowest'], v['low'][:2], v['small'][:2]) for k, v in seen14.items()} }")

    # ------------------------------------------------------------------ 15
    # A DRAWING ON A PICTURE KEEPS ITS PICTURE AT ITS SIDES (C+, the owner's
    # "Yes to both, build them", Nov 14, after "will the player not show the
    # strips on the side?"): a tile of a drawing made on a photo, or on the
    # picture the Pad began on, shows that picture at its sides, a copy of its
    # plate behind it, blurred; a plain drawing keeps its strips in its own
    # ground (#899). And the first C+ mock lifted the drawing over the "▶ 3 sec"
    # with a z-index: the ▶, and on your own Gallery tab the eye, stay what is
    # painted on top of every tile. Sol shares a paper drawing and a plain one
    # on the Pad's dark as posts, shows one made on the picture the Pad began
    # on outside a post, then posts one made on a photo; their share cards'
    # plates are painted so the reading is unambiguous: the picture warm over
    # its top half and cool under it, a hard edge across its middle (sharp on
    # the plate, soft at the sides), the plain one's bold purple lines across
    # its whole width (what a blurred copy would bring to its sides as a haze).
    if part(15, "a drawing on a picture keeps its picture at its sides; every tile's ▶ and eye stay on top"):
        T15 = "pic" + secrets.token_hex(3)
        sol = someone(b, "fillsol", "Sol Reyes")
        noa = someone(b, "fillnoa", "Noa Park")
        ORANGE, BLUE, DARK15, PAPER15 = (232, 120, 64), (40, 110, 200), (13, 15, 20), (246, 242, 234)
        PURPLE15, INK15 = (124, 92, 255), (0x3a, 0x24, 0xa8)
        dist = lambda c, t: sum(abs(x - y) for x, y in zip(c[:3], t[:3]))

        def png15(color):
            im = Image.new("RGB", (8, 8), color)
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        def card15(w, h, paint):
            """A share card whose drawing's plate `paint` paints (share_card's own colours around it)."""
            x, y, dw, dh = plate_of(w, h)
            im = Image.new("RGB", (1200, 630), CARD_GROUND)
            d = ImageDraw.Draw(im)
            d.rectangle([0, 546, 1199, 629], fill=CARD_FOOT)
            paint(d, x, y, dw, dh)
            d.rectangle([x, y, x + dw - 1, y + dh - 1], outline=CARD_LINE, width=3)
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        def on_picture(d, x, y, dw, dh):
            d.rectangle([x, y, x + dw - 1, y + dh // 2 - 1], fill=ORANGE)
            d.rectangle([x, y + dh // 2, x + dw - 1, y + dh - 1], fill=BLUE)
            for k in (1, 2, 3):                 # the drawing, in its middle, away from its sides
                cx, cy = x + dw // 2, y + k * dh // 4
                d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=(255, 255, 255), width=6)

        def plain_lines(d, x, y, dw, dh):
            d.rectangle([x, y, x + dw - 1, y + dh - 1], fill=DARK15)
            for k in range(1, 7):
                d.rectangle([x, y + k * dh // 7 - 14, x + dw - 1, y + k * dh // 7 + 14], fill=PURPLE15)

        def paper_marks(d, x, y, dw, dh):
            d.rectangle([x, y, x + dw - 1, y + dh - 1], fill=PAPER15)
            d.ellipse([x + dw // 3, y + dh // 3, x + 2 * dw // 3, y + 2 * dh // 3], outline=PURPLE15, width=12)

        def body15(size, bg, seed, **page):
            pts = [{"x": round(size[0] / 2 + math.cos((i + seed) / 5) * 60, 1),
                    "y": round(size[1] / 2 + math.sin((i + seed) / 5) * 60, 1),
                    "color": "#7c5cff", "size": 6, "t": i * 40, "start": i == 0} for i in range(30)]
            return {"version": 2, "schemaVersion": 2, "playbackMode": "replay",
                    "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
                    "frames": [dict({"strokes": pts, "strokeGroups": [30], "background": {"color": bg}}, **page)]}
        c15 = sol.client()
        c15.get("/social/")

        def share15(words, body):
            st_, j_ = c15.post_json("/social/posts", {"words": words, "payload": body})
            time.sleep(0.012)
            return j_.get("post") if st_ == 200 and isinstance(j_, dict) else None
        TALL = (531, 944)
        p_four = share15(f"{T15} on paper", dict(body15((816, 612), "#f6f2ea", 1), thumbnail=card15(816, 612, paper_marks)))
        p_plain = share15(f"{T15} plain, in the dark", dict(body15(TALL, "#0d0f14", 2), thumbnail=card15(*TALL, plain_lines)))
        sol.pg.goto(BASE + "/social/")
        _, d_snap = sol.pg.evaluate("""async (body) => {
          await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
          const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
          const r = await fetch('/api/skribls', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) }, body: JSON.stringify(body) });
          const j = await r.json().catch(() => ({})); return [r.status, j.id || null]; }""",
            dict(body15(TALL, "#f6f2ea", 3, baseSnapshot=png15(ORANGE)), title=f"{T15} on the picture it began on",
                 visibility="public", thumbnail=card15(*TALL, on_picture)))
        time.sleep(0.012)
        p_photo = share15(f"{T15} on a photo", dict(body15(TALL, "#0d0f14", 4, photo={"data": png15(BLUE), "fit": "cover"}),
                                                    thumbnail=card15(*TALL, on_picture)))
        sk15 = {"four": (post_row(p_four) or (None, None))[1], "plain": (post_row(p_plain) or (None, None))[1],
                "snap": d_snap, "photo": (post_row(p_photo) or (None, None))[1]}
        cols15 = {k: tuple(db("select ground, on_photo from skribl_posts where public_id = ?", (v,))[0]) if v else None
                  for k, v in sk15.items()}
        check("(setup) Sol shares a paper drawing and a plain one on the Pad's dark as posts, shows one made on the"
              " picture the Pad began on outside a post (Skribl's own API, as the Pad posts), then posts one made on a"
              " photo; Skribl writes each one's ground and whether it is on a picture as it is posted",
              all(sk15.values()) and cols15 == {"four": ("#f6f2ea", 0), "plain": ("#0d0f14", 0), "snap": ("#f6f2ea", 1),
                                                 "photo": ("#0d0f14", 1)},
              f"{sk15}; columns {cols15}")

        # WHAT IS PAINTED AT A BOX'S SIDES, read off its own picture (the ▶ and
        # the eye made invisible first): the middle of each bar beside the
        # plate, a fifth of the way down and four fifths, and a column down
        # each bar and one just inside the plate's edge, where the picture's
        # hard edge crosses (the steepest step between neighbouring pixels).
        FILLREAD = """(sel) => { const t = document.querySelector(sel); if (!t) return null;
          t.scrollIntoView({ block: 'center', behavior: 'instant' });
          const box = t.querySelector('.gal-pic, .more-pic'), plate = t.querySelector('.gal-plate, .more-plate'), cell = t.closest('.gal-cell');
          [t.querySelector('.gal-dur'), cell && cell.querySelector('.gal-eye')].forEach(e => { if (e) e.style.visibility = 'hidden'; });
          [...t.querySelectorAll('img')].forEach(i => { i.loading = 'eager'; });
          const b = box.getBoundingClientRect(), p = plate.getBoundingClientRect();
          return { w: b.width, h: b.height, pl: p.left - b.left, pr: p.right - b.left, pt: p.top - b.top, pb: p.bottom - b.top,
                   fill: !!box.querySelector(':scope > .plate-fill'), ground: box.getAttribute('style') }; }"""
        IMGS15 = """(sel) => { const t = document.querySelector(sel); return !!t && [...t.querySelectorAll('img')].every(i => i.complete && i.naturalWidth > 0); }"""
        SHOW15 = """(sel) => { const t = document.querySelector(sel), cell = t && t.closest('.gal-cell');
          [t && t.querySelector('.gal-dur'), cell && cell.querySelector('.gal-eye')].forEach(e => { if (e) e.style.visibility = ''; }); }"""

        def sides(pg_, sel):
            try:
                pg_.wait_for_selector(sel, timeout=15000)
                g = pg_.evaluate(FILLREAD, sel)
                pg_.wait_for_function(IMGS15, arg=sel, timeout=15000)
                pg_.evaluate("(s) => Promise.all([...document.querySelector(s).querySelectorAll('img')].map(i => i.decode().catch(() => null)))", sel)
                pg_.wait_for_timeout(250)
                shot = pg_.locator(sel + " :is(.gal-pic, .more-pic)").screenshot(timeout=5000)
                pg_.evaluate(SHOW15, sel)
            except Exception as exc:  # noqa: BLE001 -- a box that cannot be read is the row's red
                return {"stopped": str(exc).splitlines()[0][:120]}
            im = Image.open(io.BytesIO(shot)).convert("RGB")
            k = im.size[1] / g["h"]

            def px(x, y):
                return im.getpixel((min(im.size[0] - 1, int(x * k)), min(im.size[1] - 1, int(y * k))))
            xl, xr = g["pl"] / 2, (g["w"] + g["pr"]) / 2
            y0, y1 = max(g["pt"] + 2, g["h"] * 0.15), min(g["pb"] - 2, g["h"] * 0.85)

            def steepest(x):
                c = [px(x, y) for y in range(int(y0), int(y1))]
                return max((dist(p_, q_) for p_, q_ in zip(c, c[1:])), default=0)
            return {"fill": g["fill"], "bars": [round(g["pl"]), round(g["w"] - g["pr"])],
                    "lt": px(xl, g["h"] * 0.2), "lb": px(xl, g["h"] * 0.8), "rt": px(xr, g["h"] * 0.2),
                    "rb": px(xr, g["h"] * 0.8), "lm": px(xl, g["h"] / 2), "rm": px(xr, g["h"] / 2),
                    "soft": max(steepest(xl), steepest(xr)), "sharp": steepest(g["pl"] + 4), "ground": g["ground"]}

        def pictured(r, ground):
            """Its sides its picture's colours (warm above, cool below, never its ground), blurred (no step
            between neighbouring pixels a hard edge would make, where the plate beside it shows one)."""
            return (not r.get("stopped") and r["fill"] and min(r["bars"]) >= 20
                    and all(dist(r[k_], ground) >= 150 for k_ in ("lt", "lb", "rt", "rb"))
                    and all(dist(r[k_], ORANGE) <= 110 for k_ in ("lt", "rt"))
                    and all(dist(r[k_], BLUE) <= 110 for k_ in ("lb", "rb")) and r["soft"] <= 30 and r["sharp"] >= 100)

        def plain15(r, ground):
            """Its strips its own ground, painted, and no copy of its plate behind it."""
            return (not r.get("stopped") and not r["fill"] and min(r["bars"]) >= 20
                    and dist(r["lm"], ground) <= 12 and dist(r["rm"], ground) <= 12)
        TILE = {"photo": f'.gal-tile[data-post="{p_photo}"]', "snap": f'.gal-tile[data-drawing="{d_snap}"]',
                "plain": f'.gal-tile[data-post="{p_plain}"]'}
        GROUND15 = {"photo": DARK15, "snap": PAPER15, "plain": DARK15}
        read15 = {}
        for screen in ("phone", "desk"):
            for where, who, path, sels in (("the Gallery", noa, "/social/explore?q=" + urllib.parse.quote(T15), TILE),
                                           ("Sol's Gallery tab", noa, "/social/@fillsol/gallery", TILE),
                                           ("the first visit", None, "/social/", TILE)):
                ctx, cpg = browser_as(b, who, screen, "light")
                cpg.goto(BASE + path)
                cpg.wait_for_timeout(600)
                for key, sel in sels.items():
                    read15[(where, screen, key)] = sides(cpg, sel)
                close_ctx(ctx, cpg)
        # (More from on a post's page was a fourth place until the Calm Post
        # Page took it off the page, Nov 20: section 3 asks that it is gone.)
        WHERE15 = ("the Gallery", "Sol's Gallery tab", "the first visit")
        short = lambda r: {k_: v for k_, v in r.items() if k_ in ("stopped", "fill", "bars", "lt", "lb", "soft", "sharp", "lm")}
        check("A DRAWING ON A PICTURE KEEPS ITS PICTURE AT ITS SIDES: beside its plate the box is painted in its"
              " picture's own colours (warm above, cool below), blurred (no hard step where the plate shows one),"
              " never its ground: a post's made on a photo and a drawing shown outside a post made on the picture the"
              " Pad began on, in the Gallery, on its maker's Gallery tab and on the first visit, a touch"
              " phone and a desk",
              len(read15) == 18 and all(pictured(read15[(w, s, k_)], GROUND15[k_]) for w in WHERE15
                                        for s in ("phone", "desk") for k_ in ("photo", "snap")),
              json.dumps({f"{w}, {s}, {k_}": short(read15.get((w, s, k_), {})) for w in WHERE15 for s in ("phone", "desk")
                          for k_ in ("photo", "snap") if not pictured(read15.get((w, s, k_), {"stopped": "?"}), GROUND15[k_])})[:900])
        check("...and only on a picture: a plain drawing's strips stay its own ground, with no copy of its plate behind"
              " it (on a line drawing the blur is a coloured haze), everywhere the same",
              all(plain15(read15.get((w, s, "plain"), {"stopped": "?"}), DARK15) for w in WHERE15 for s in ("phone", "desk")),
              json.dumps({f"{w}, {s}": short(read15.get((w, s, "plain"), {})) for w in WHERE15 for s in ("phone", "desk")
                          if not plain15(read15.get((w, s, "plain"), {"stopped": "?"}), DARK15)})[:700])

        # EVERY TILE'S ▶ IS WHAT IS PAINTED ON TOP, and on your own Gallery tab
        # its eye: what is painted along the middle of each ▶ (every 2px of it
        # but its round ends), and of each eye's chip, is that ▶, that chip;
        # never the drawing or its copy.
        ONTOP = """(root) => { const out = [];
          for (const t of document.querySelectorAll(root + ' .gal-tile')) {
            t.scrollIntoView({ block: 'center', behavior: 'instant' });
            const probe = (el, inset) => { if (!el) return ['none']; const r = el.getBoundingClientRect(), y = r.top + r.height / 2, miss = [];
              for (let x = r.left + inset; x <= r.right - inset; x += 2) { const e = document.elementFromPoint(x, y);
                if (!(e && el.contains(e))) miss.push(Math.round(x - r.left) + ' ' + (e ? (e.getAttribute('class') || e.tagName) : 'nothing')); }
              return miss; };
            const cell = t.closest('.gal-cell');
            out.push({ id: t.getAttribute('data-post') || t.getAttribute('data-drawing'), fill: !!t.querySelector('.plate-fill'),
                       dur: probe(t.querySelector('.gal-dur'), 10), eye: cell ? probe(cell.querySelector('.gal-eye-chip'), 7) : null }); }
          return out; }"""
        top15 = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                for where, who, path, root in (("the Gallery", noa, "/social/explore?q=" + urllib.parse.quote(T15), "[data-gal-grid]"),
                                               ("Sol's Gallery tab", noa, "/social/@fillsol/gallery", "[data-prof-list]"),
                                               ("her own Gallery tab", sol, "/social/@fillsol/gallery", "[data-prof-list]"),
                                               ("the first visit", None, "/social/", "[data-fresh]")):
                    ctx, cpg = browser_as(b, who, screen, scheme)
                    cpg.goto(BASE + path)
                    cpg.wait_for_timeout(600)
                    try:
                        top15[(where, screen, scheme)] = cpg.evaluate(ONTOP, root)
                    except Exception as exc:  # noqa: BLE001 -- a page that cannot be read is the row's red
                        top15[(where, screen, scheme)] = [{"stopped": str(exc).splitlines()[0][:100]}]
                    close_ctx(ctx, cpg)
        missed = {f"{' '.join(k)} {t.get('id')}": (t.get("dur") or [])[:3] + (t.get("eye") or [])[:3]
                  for k, v in top15.items() for t in v if t.get("stopped") or t.get("dur") or t.get("eye")}
        photos_seen = {k: sum(1 for t in v if t.get("fill")) for k, v in top15.items()}
        check("EVERY TILE'S ▶ IS PAINTED ON TOP, and on your own Gallery tab its eye: along the middle of each ▶ (and"
              " each eye's chip) what is painted is the ▶ (the chip), never the drawing or its picture behind it, on"
              " every tile: the Gallery, a profile's Gallery tab, its maker's own with the eye, the first visit; a touch"
              " phone and a desk, light and dark",
              len(top15) == 16 and not missed and all(len(v) >= 4 for v in top15.values())
              and all(n == 2 for n in photos_seen.values())
              and all(t.get("eye") == [] for k, v in top15.items() if k[0] == "her own Gallery tab" for t in v),
              f"missed {json.dumps(missed)[:600]}; tiles {[len(v) for v in top15.values()]}; on a picture {list(photos_seen.values())}")

        # THE ▶'S WORDS AND THE EYE ON THEIR GLASS OVER A PICTURE, read off the
        # pixels (the words and the eye made see-through): the glass is the
        # ▶'s own over every drawing, and here the picture is under it.
        glass15 = {}

        def lum15(c):
            v = [x / 255 for x in c[:3]]
            v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

        def worst(png_, box):
            im = Image.open(io.BytesIO(png_)).convert("RGB")
            px_ = [im.getpixel((int(box[0] + i), int(box[1] + j))) for i in range(int(box[2])) for j in range(int(box[3]))
                   if int(box[0] + i) < im.size[0] and int(box[1] + j) < im.size[1]]
            ink = lum15(INK15)
            return round(min((max(lum15(p_), ink) + 0.05) / (min(lum15(p_), ink) + 0.05) for p_ in px_), 2) if px_ else None
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, cpg = browser_as(b, sol, screen, scheme)
                cpg.goto(BASE + "/social/@fillsol/gallery")
                sel = TILE["photo"]
                try:
                    cpg.locator(sel).scroll_into_view_if_needed(timeout=5000)
                    cpg.wait_for_function(IMGS15, arg=sel, timeout=15000)
                    cpg.wait_for_timeout(250)
                    box = cpg.evaluate("""(s) => { const d = document.querySelector(s + ' .gal-dur'), w = d.querySelector('span');
                      const a = d.getBoundingClientRect(), r = w.getBoundingClientRect(); w.style.color = 'transparent';
                      return [r.left - a.left, r.top - a.top, r.width, r.height]; }""", sel)
                    words_ = worst(cpg.locator(sel + " .gal-dur").screenshot(timeout=5000), box)
                    ebox = cpg.evaluate("""(s) => { const c = document.querySelector(s).closest('.gal-cell').querySelector('.gal-eye-chip');
                      const ic = c.querySelector('.gal-eye-ics'), a = c.getBoundingClientRect(), r = ic.getBoundingClientRect();
                      ic.style.visibility = 'hidden'; return [r.left - a.left, r.top - a.top, r.width, r.height]; }""", sel)
                    chip = cpg.locator(f".gal-cell:has({sel}) .gal-eye-chip")
                    glass15[(screen, scheme)] = (words_, worst(chip.screenshot(timeout=5000), ebox))
                except Exception as exc:  # noqa: BLE001 -- a picture that cannot be read is the row's red
                    glass15[(screen, scheme)] = (str(exc).splitlines()[0][:100], None)
                close_ctx(ctx, cpg)
        check("...and the ▶'s words and the eye read 4.5:1 or more off the pixels under them, their glass over a"
              " drawing's picture: a touch phone and a desk, light and dark (no colour or token added)",
              len(glass15) == 4 and all(isinstance(w, float) and isinstance(e, float) and w >= 4.5 and e >= 4.5
                                        for w, e in glass15.values()),
              f"{ {' '.join(k): v for k, v in glass15.items()} }")

        # A HIDDEN ONE FADES WITH ITS PICTURE (your own Gallery tab, the eye):
        # the copy behind the drawing fades to 55% with it, so a hidden drawing
        # on a picture reads hidden as every other does; read off the paint
        # beside the plate, then shown again.
        ctx, cpg = browser_as(b, sol, "phone", "light")
        cpg.goto(BASE + "/social/@fillsol/gallery")
        cpg.wait_for_timeout(600)
        sel, cellsel = TILE["photo"], f'.gal-cell:has({TILE["photo"]})'
        fade15 = {"shown": sides(cpg, sel)}
        try:
            cpg.click(cellsel + " .gal-eye")
            cpg.wait_for_function("(s) => { const c = document.querySelector(s); return c && c.classList.contains('is-hidden') && c.__eyeBusy === false; }",
                                  arg=cellsel, timeout=15000)
            cpg.wait_for_timeout(450)
            fade15["opacity"] = cpg.evaluate("""(s) => { const c = document.querySelector(s);
              return [+getComputedStyle(c.querySelector('.plate-fill > span')).opacity, +getComputedStyle(c.querySelector('.gal-plate')).opacity]; }""", cellsel)
            fade15["hidden"] = sides(cpg, sel)
            cpg.click(cellsel + " .gal-eye")
            cpg.wait_for_function("(s) => { const c = document.querySelector(s); return c && !c.classList.contains('is-hidden') && c.__eyeBusy === false; }",
                                  arg=cellsel, timeout=15000)
        except Exception as exc:  # noqa: BLE001 -- an eye that cannot be pressed is the row's red
            fade15["stopped"] = str(exc).splitlines()[0][:120]
        close_ctx(ctx, cpg)
        sh, hd = fade15.get("shown") or {}, fade15.get("hidden") or {}
        still = db("select gallery_hidden_at from social_posts where public_id = ?", (p_photo,))
        check("...and on your own Gallery tab a hidden drawing on a picture fades with its picture: the copy behind it"
              " at 55% with the drawing, the sides read off the paint nearer the box's own ground; shown again, back",
              not fade15.get("stopped") and fade15.get("opacity") == [0.55, 0.55] and pictured(sh, DARK15)
              and not hd.get("stopped") and all(dist(hd[k_], DARK15) < 0.75 * dist(sh[k_], DARK15) for k_ in ("lt", "lb", "rt", "rb"))
              and bool(still) and still[0][0] is None,
              f"{fade15.get('stopped') or ''} opacity {fade15.get('opacity')}; shown {short(sh)}; hidden {short(hd)};"
              f" in the Gallery again {bool(still) and still[0][0] is None}")

    # ------------------------------------------------------------------ 16
    # A LIST OF CHOICES IS ONE CARD (the owner's "B, equal lines", Nov 14: "Do
    # we need everything to be in a pill?"), on every menu sheet of the site:
    # the ☰'s (a touch phone's Home), a post's ⋯ (yours and somebody else's),
    # a comment's ⋯ and a person's ⋯, and Report's reasons. Read, for each,
    # on a touch phone and a desk, light and dark, as Ana: what the sheet
    # says its lists are (ONECARD), what is painted (the card's colour in
    # each row's margin, the sheet's paper between two cards, off the
    # screen), a key's ring on a row (off the screen), and, on a phone, the
    # four ways a menu sheet goes with no Cancel.
    if part(16, "a list of choices is one card: the ☰'s, a post's ⋯, a comment's ⋯, a person's ⋯, Report's reasons"):
        try:
            ana = someone(b, "ana", "Ana Ruiz")
            ben = someone(b, "ben", "Ben Holt")
            _, ja = make_post(ana, "Ana's, for the ⋯ sheets", seed=161)
            _, jb = make_post(ben, "Ben's, for the ⋯ sheets", seed=162)
            mine16, theirs16 = ja.get("post"), jb.get("post")
            bc = ben.client()
            bc.get(f"/social/p/{mine16}")
            stc, jc = bc.post_json(f"/social/p/{mine16}/comments", {"words": "Ben says hello"})
            # (name, page, what opens it, its wrap's id, a menu sheet?, a phone's alone?)
            SHEETS16 = (("the ☰", "/social/", ("[data-site-menu]",), "siteMenu", True, True),
                        ("your post's ⋯", f"/social/p/{mine16}", (".post-page .post-row [data-post-menu]",), "postSheet", True, False),
                        ("their post's ⋯", f"/social/p/{theirs16}", (".post-page .post-row [data-post-menu]",), "postSheet", True, False),
                        ("a comment's ⋯", f"/social/p/{mine16}", (".cm:not([data-mine]) [data-cm-menu]",), "commentSheet", True, False),
                        ("a person's ⋯", "/social/@ben", ("[data-person-menu]",), "personSheet", True, False),
                        ("Report's reasons", f"/social/p/{theirs16}",
                         (".post-page .post-row [data-post-menu]", "#postSheet [data-act=report]"), "reportSheet", False, False))
            # Your own post that can be drawn back on has a card between the two since Her say (Nov 20): "Who can
            # draw back", Settings' pill in it (verify_socialdrawback 12 holds what it does).
            WANT16 = {"your post's ⋯": [["Bookmark", "Pin to your page", "Copy link", "Share…"], ["Who can draw back"],
                                        ["Delete post"]],
                      "their post's ⋯": [["Bookmark", "Copy link", "Share…", "Mute @ben"], ["Report this post", "Block @ben"]],
                      "a comment's ⋯": [["Bookmark", "Copy link", "Share…"], ["Remove from my post", "Report this comment"]],
                      "a person's ⋯": [["Mute @ben"], ["Report @ben", "Block @ben"]],
                      "Report's reasons": [["Spam or misleading", "Abusive or hateful", "Copies someone else’s work",
                                            "A child’s safety", "Something else"]]}

            def open16(pg, page, steps, wrap):
                pg.goto(BASE + page)
                pg.wait_for_timeout(700)
                for sel in steps:
                    pg.evaluate("(s) => { const e = [...document.querySelectorAll(s)].find(x => x.getClientRects().length);"
                                " if (e) e.scrollIntoView({ block: 'center' }); }", sel)
                    pg.click(f"{sel} >> visible=true", timeout=5000)
                    pg.wait_for_timeout(650)
                pg.wait_for_function("(id) => document.getElementById(id).classList.contains('is-open')", arg=wrap, timeout=5000)
                pg.wait_for_timeout(450)

            def rgb16(s):
                n = [float(x) for x in re.findall(r"[\d.]+", s)[:3]]
                return tuple(round(v) for v in n)

            def near16(px, want, tol=6):
                return all(abs(a - b_) <= tol for a, b_ in zip(px[:3], want))

            looks16, rings16, ways16 = {}, {}, {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    for name, page, steps, wrap, menu, phone_only in SHEETS16:
                        if phone_only and screen != "phone":
                            continue
                        key = (screen, scheme, name)
                        ctx, cpg = browser_as(b, ana, screen, scheme, reduced=True)
                        try:
                            open16(cpg, page, steps, wrap)
                            got = cpg.evaluate(ONECARD, f"#{wrap} .make-sheet")
                            tok = cpg.evaluate(TOKENS16)
                            im = Image.open(io.BytesIO(cpg.screenshot())).convert("RGB") if Image else None
                            # The card's colour where each row has nothing (5px in from the card's
                            # edge, at the row's middle), and the sheet's paper between two cards.
                            margins, between = [], []
                            if im and got:
                                for li, L in enumerate(got["lists"]):
                                    for r_ in L["rows"]:
                                        margins.append(im.getpixel((int(L["left"] + 5), int(r_["mid"]))))
                                    if li:
                                        P_ = got["lists"][li - 1]
                                        between.append(im.getpixel((int((L["left"] + L["right"]) / 2), int((P_["bottom"] + L["top"]) / 2))))
                            looks16[key] = {"got": got, "tok": tok, "margins": margins, "between": between}
                            # A key's ring on a row, inside it: Tab puts focus on a row (the next,
                            # where the sheet put it on its first), and its four sides are read
                            # off the screen one pixel inside the row's edge.
                            if menu and screen == "phone" and im:
                                cpg.keyboard.press("Tab")
                                cpg.wait_for_timeout(250)
                                fr = cpg.evaluate("""() => { const a = document.activeElement; if (!a || !a.matches('.post-act')) return null;
                                  const r = a.getBoundingClientRect(); return { words: a.textContent.trim().slice(0, 24), l: r.left, r: r.right,
                                  t: r.top, b: r.bottom, ring: getComputedStyle(a).outlineColor, fv: a.matches(':focus-visible') }; }""")
                                if fr:
                                    # the pixel whose whole square lies in the ring's 2px band inside each edge
                                    im2 = Image.open(io.BytesIO(cpg.screenshot())).convert("RGB")
                                    my, mx = int((fr["t"] + fr["b"]) / 2), int((fr["l"] + fr["r"]) / 2)
                                    fr["sides"] = [im2.getpixel((int(fr["l"] + 0.5), my)), im2.getpixel((int(fr["r"] - 1.5), my)),
                                                   im2.getpixel((mx, int(fr["t"] + 0.5))), im2.getpixel((mx, int(fr["b"] - 1.5)))]
                                rings16[key] = fr
                        except Exception as exc:  # noqa: BLE001
                            looks16[key] = {"stopped": str(exc).splitlines()[0][:120]}
                        close_ctx(ctx, cpg)
            # The four ways a menu sheet goes, with no Cancel: Esc, a tap outside it,
            # its grip, and a swipe down (a touch phone, light).
            for name, page, steps, wrap, menu, phone_only in SHEETS16:
                if not menu:
                    continue
                for how in ("Esc", "outside", "grip", "swipe"):
                    ctx, cpg = browser_as(b, ana, "phone", "light")
                    try:
                        open16(cpg, page, steps, wrap)
                        if how == "Esc":
                            cpg.keyboard.press("Escape")
                        elif how == "outside":
                            cpg.mouse.click(200, 30)
                        elif how == "grip":
                            cpg.click(f"#{wrap} .make-grip", timeout=3000)
                        else:
                            cpg.evaluate(SWIPE16, [f"#{wrap} .make-sheet", [12, 40, 90, 160, 220], 90])
                        cpg.wait_for_timeout(700)
                        ways16[(name, how)] = cpg.evaluate("(id) => document.getElementById(id).hidden", wrap)
                    except Exception as exc:  # noqa: BLE001
                        ways16[(name, how)] = str(exc).splitlines()[0][:80]
                    close_ctx(ctx, cpg)

            bad_card, bad_risky, bad_cancel, bad_paint, bad_ring = [], [], [], [], []
            for key, v in looks16.items():
                tag = " ".join(key)
                got, tok = v.get("got"), v.get("tok")
                if not got or not got["lists"]:
                    bad_card.append(f"{tag}: {v.get('stopped') or 'no lists'}")
                    continue
                for L in got["lists"]:
                    rows = L["rows"]
                    ok = (L["bg"] == tok["row"] and L["r"] == ["16px", "16px"] and rows
                          and all(r_["own"] == "rgba(0, 0, 0, 0)" and r_["painted"]
                                  and abs(r_["left"] - L["left"]) <= 0.5 and abs(r_["right"] - L["right"]) <= 0.5 for r_ in rows)
                          and rows[0]["line"] == "none" and rows[0]["gap"] is None
                          and all(abs(r_["gap"]) <= 0.5 and thin_ok(r_, tok["rowline"], 16) for r_ in rows[1:]))
                    if not ok:
                        bad_card.append(f"{tag}: card {L['bg']} {L['r']}; rows "
                                        + "; ".join(f"{r_['words']} own {r_['own']} gap {r_['gap']} line {r_['line']}"
                                                    f" painted {r_['painted']}" for r_ in rows))
                name = key[2]
                words = [[r_["words"] for r_ in L["rows"]] for L in got["lists"]]
                risky = [[r_["risky"] for r_ in L["rows"]] for L in got["lists"]]
                if name in WANT16:
                    gaps = [round(got["lists"][i]["top"] - got["lists"][i - 1]["bottom"], 1) for i in range(1, len(got["lists"]))]
                    rk = name != "Report's reasons"
                    if not (words == WANT16[name] and gaps == [12.0] * (len(words) - 1)
                            and (not rk or (all(risky[-1]) and not any(x for r_ in risky[:-1] for x in r_)))):
                        bad_risky.append(f"{tag}: {words} risky {risky} {gaps}px apart")
                elif not (len(words) == 1 and len(words[0]) >= 4 and not any(risky[0])):
                    bad_risky.append(f"{tag}: {words}")
                menu = name != "Report's reasons"
                if (menu and got["cancel"]) or (not menu and not (got["cancel"] == 1 and got["send"] == 1)):
                    bad_cancel.append(f"{tag}: Cancel {got['cancel']}, Send report {got['send']}")
                if Image and not (v["margins"] and all(near16(px, rgb16(tok["row"])) for px in v["margins"])
                                  and all(near16(px, rgb16(tok["paper"])) for px in v["between"])):
                    bad_paint.append(f"{tag}: margins {v['margins']}; between {v['between']} (card {tok['row']}, paper {tok['paper']})")
            for key, fr in rings16.items():
                if not (fr and fr["fv"] and len(fr.get("sides", [])) == 4
                        and all(near16(px, rgb16(fr["ring"]), 24) for px in fr["sides"])):
                    bad_ring.append(f"{' '.join(key)}: {fr}")
            read16 = len(looks16)
            print(f"    {read16} sheets read; a row's ring on {len(rings16)}; {len(ways16)} closings")
            check("every list of choices on the site's menu sheets is ONE CARD, as the Pad's own menu list draws it:"
                  " the card --row-bg and 16 round, its rows on it with nothing of their own behind them, as wide as the"
                  " card and touching, Apple's thin line between two that show (the owner's \"Apple's thin line\":"
                  " its own line, no top border to see, in --row-line, from where the row's words start to 16px before the"
                  " card's edge), each row what is painted at its middle (the ☰'s, a post's ⋯ yours and somebody"
                  " else's, a comment's ⋯, a person's ⋯ and Report's reasons; phone and desk, light and dark)",
                  read16 == 22 and not bad_card, "; ".join(bad_card)[:1400] or f"{read16} read")
            # ...and ONE SCREEN PIXEL on the owner's own phone's screen (3x): the
            # line's height times its own scale times the screen's, read off its
            # style; a line left a CSS pixel thick is three there.
            px3 = []
            ctx, cpg = browser_as(b, ana, "phone", "dark", reduced=True, scale=3)
            try:
                open16(cpg, "/social/", ("[data-site-menu]",), "siteMenu")
                got3 = cpg.evaluate(ONECARD, "#siteMenu .make-sheet")
                px3 = [r_["line"]["px"] if isinstance(r_["line"], dict) else r_["line"]
                       for L in (got3 or {}).get("lists", []) for r_ in L["rows"][1:]]
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                px3 = [f"stopped: {str(exc).splitlines()[0][:120]}"]
            ctx.close()
            check("...and that line is one screen pixel on a 3x phone, the owner's (the ☰'s lines: three, or four"
                  " for an admin, whose ☰ holds Your reports)",
                  len(px3) >= 3 and all(isinstance(v, (int, float)) and abs(v - 1) <= 0.05 for v in px3), f"{px3}")
            check("the risky rows (Report, Block, Delete, Remove) are a card of their own, the last, 12px under the one"
                  " before, its rows the risky ones alone: your post's Copy link, Share… | Who can draw back (a card of"
                  " its own between the two, on a post that can be drawn back on) | Delete post; somebody else's Copy"
                  " link, Share…, Mute | Report, Block; a comment's ⋯ only its risky card; a person's Mute | Report,"
                  " Block; the ☰ one card with nothing risky; Report's reasons one card",
                  read16 == 22 and not bad_risky, "; ".join(bad_risky)[:1400])
            check("no Cancel under a menu sheet (the ☰'s, a post's ⋯, a comment's ⋯, a person's ⋯); Report keeps"
                  " its Cancel | Send report", read16 == 22 and not bad_cancel, "; ".join(bad_cancel)[:900])
            check("what is painted says the same: the card's own colour in every row's margin, and the sheet's paper"
                  " in the 12px between two cards (off the screen)",
                  read16 == 22 and not bad_paint, "; ".join(bad_paint)[:1400])
            check("a key's ring on a row is drawn inside the row, so the card's edge never cuts it: its four sides"
                  " painted in the ring's colour a pixel inside the row (a touch phone, light and dark, every menu sheet)",
                  len(rings16) == 10 and not bad_ring, "; ".join(bad_ring)[:1400] or f"{len(rings16)} read")
            check("a menu sheet with no Cancel still goes four ways: Esc, a tap outside it, its grip and a swipe down"
                  " (the ☰'s, a post's ⋯ yours and somebody else's, a comment's ⋯, a person's ⋯; a touch phone)",
                  len(ways16) == 20 and all(v_ is True for v_ in ways16.values()),
                  "; ".join(f"{n} {h}: {v_}" for (n, h), v_ in ways16.items() if v_ is not True)[:900])
        except Exception as exc:  # noqa: BLE001
            check("section 16 ran to its end", False, str(exc).splitlines()[0][:200])

    # ------------------------------------------------------------------ 17
    if part(17, "the edges: every outline one screen pixel; a Gallery tile's line on the light page; a field's edge 3:1"):
        # THE EDGES (the owner, Nov 15, "The edges", B): every outline the
        # site draws is one screen pixel, the rows' thin line given to every
        # edge, and the Gallery's tiles sit on the light page with the cards'
        # own lift. THAT LIFT IS ONE LINE OF SHADE NOW (the crisp build, the
        # owner's "All yes" to its B, Nov 20; section 23): 1px under the edge
        # and nothing soft below it, where it was a soft shadow. Read off the
        # paint at the owner's phone's 3x, light
        # and dark: at the middle of a box's left side (the bar: of its top),
        # the screen pixels that stand 1.15:1 apart from both the page beside
        # and what is inside. Every one of them was three; a field's edge
        # read 2.90:1 on its own white.
        try:
            def _lum(q):
                ch = [(v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4 for v in q[:3]]
                return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

            def _cr(p_, q_):
                a_, b_ = sorted((_lum(p_), _lum(q_)), reverse=True)
                return (a_ + 0.05) / (b_ + 0.05)

            # A line pixel stands 1.15:1 or more apart from both sides: every line here does (the faintest was a dark
            # card's hairline, 1.22:1 on its card, until dark's edge was made clear on Nov 21: 1.61 since), and a
            # tile's lift does not (its gradient beside the ring reads
            # 1.06:1 against the page: the first version, at 1.05, counted it as a second pixel of line).
            def _band(im, pts, page, inside):
                return [im.getpixel(p_) for p_ in pts if _cr(im.getpixel(p_), page) >= 1.15 and _cr(im.getpixel(p_), inside) >= 1.15]

            BOX = "(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"

            # WHAT A BOX'S SHADOW PAINTS UNDER IT, PAST ITS RING: the screen rows from its foot down (13px of
            # them) where the picture is darker than the same picture with the shadow cut to its ring. One line
            # of shade is a run of two or three rows at 3x (1px, the ring over its first); a soft shadow is
            # dozens; none is none. (A box's foot seldom lands on a whole screen pixel, so a set row cannot be
            # asked: the first writing of this read the ring twice and never the line.)
            def _shade(page_, im_, sel_, r_, across, ring):
                xm, yb = round((r_[0] + r_[2] * across) * 3), round((r_[1] + r_[3]) * 3)
                cut = page_.add_style_tag(content=sel_ + " { box-shadow: 0 0 0 var(--edge) " + ring + " !important; }")
                page_.wait_for_timeout(120)
                im2_ = Image.open(io.BytesIO(page_.screenshot())).convert("RGB")
                cut.evaluate("s => s.remove()")
                page_.wait_for_timeout(60)
                return [k for k in range(-4, 40) if _lum(im_.getpixel((xm, yb + k))) * 1000 < _lum(im2_.getpixel((xm, yb + k))) * 1000 - 2]

            def _one_line(rows):
                return bool(rows) and 2 <= len(rows) <= 3 and rows == list(range(rows[0], rows[0] + len(rows)))
            ed = member(b, "edgy", "Eddie Edge")
            st17, _ = make_post(ed, "Edges, one screen pixel.", card=True)
            edges, lift = {}, None
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, ed, screen="phone", scheme=scheme, scale=3)
                for path, sels in (("/social/", [".post-card"]), ("/social/explore", [".gal-find input", ".fo-seg", ".gal-pic"])):
                    pg.goto(BASE + path)
                    pg.wait_for_timeout(900)
                    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                    for sel in sels:
                        r = pg.evaluate(BOX, sel)
                        if not r:
                            edges[f"{scheme} {sel}"] = None
                            continue
                        x, y = round(r[0] * 3), round((r[1] + r[3] / 2) * 3)
                        page, inside = im.getpixel((x - 9, y)), im.getpixel((x + 12, y))
                        got = _band(im, [(i, y) for i in range(x - 6, x + 8)], page, inside)
                        edges[f"{scheme} {sel}"] = {"n": len(got), "px": got[:3], "inside": inside, "page": page}
                        if sel == ".gal-pic" and scheme == "light":
                            lift = _shade(pg, im, sel, r, 0.5, "var(--card-line)")
                    if path == "/social/explore":
                        r = pg.evaluate(BOX, "nav.nav")
                        x6, y = 6, round(r[1] * 3)
                        page, inside = im.getpixel((x6, y - 9)), im.getpixel((x6, y + 12))
                        got = _band(im, [(x6, j) for j in range(y - 6, y + 8)], page, inside)
                        edges[f"{scheme} the bar"] = {"n": len(got), "px": got[:3]}
                close_ctx(ctx, pg)
            check("every outline is one screen pixel at 3x, light and dark: a post's card on Home, the Gallery's search box,"
                  " New | Hot, a tile, and the bar's line along its top",
                  st17 == 200 and len(edges) == 10 and all(v and v["n"] == 1 for v in edges.values()),
                  json.dumps({k: (v and v["n"]) for k, v in edges.items()}) + " " + json.dumps(edges)[:500])
            check("...a Gallery tile sits on the light page with the cards' own lift, which is one line of shade (crisp):"
                  " under its edge the shadow paints two or three screen rows together (1px), and nothing below them for"
                  " 13px",
                  _one_line(lift), json.dumps(lift))
            # AN EDGE DOES THE SEPARATING, IN DARK TOO (the owner, Nov 21, after the crisp build: "I feel like you
            # may have overdone it with the shadows and now it looks less crisp in areas"; yes to step 3 of "The
            # Little V", "everywhere"). Dark's edge was 12% of the lilac over its card, set that faint while soft
            # shadows did the work: 1.23:1 from the card. It is 26% now, 1.61:1, where light's 34% of the accent
            # stands 1.56:1 from its white. The same pixels the row above counted: a post's card on Home (its ring is
            # --card-edge) against the card inside it and the page beside it, and a Gallery tile's line (--card-line,
            # a see-through lilac over whatever it lies on) against the ground beside it; inside a tile is somebody's
            # drawing, which is not asked.
            apart = {}
            for sc in ("light", "dark"):
                v = edges.get(f"{sc} .post-card")
                apart[f"{sc}, a card"] = (round(_cr(v["px"][0], v["inside"]), 2), round(_cr(v["px"][0], v["page"]), 2)) if v and v.get("px") else None
                v = edges.get(f"{sc} .gal-pic")
                apart[f"{sc}, a tile"] = (round(_cr(v["px"][0], v["page"]), 2),) if v and v.get("px") else None
            check("...and the edge does the separating in both themes: read off the paint, a post's card's edge stands 1.4 to"
                  " 1 or more apart from the card inside it and from the page beside it, and a Gallery tile's line as far"
                  " from the ground beside it, light and dark (dark's stood 1.23 from its card until Nov 21)",
                  all(v is not None and min(v) >= 1.4 for v in apart.values()), json.dumps(apart))
            fld = edges.get("light .gal-find input") or {}
            check("...and the search box's edge reads 3:1 or more against its own white",
                  bool(fld.get("px")) and _cr(fld["px"][0], fld["inside"]) >= 3.0,
                  json.dumps(fld) + (f" {_cr(fld['px'][0], fld['inside']):.2f}:1" if fld.get("px") else ""))

            # A DRAWING ON THE SITE (the edges, part four, its last: the owner's
            # yes to "a post's drawing on the site, with the mock's lift for it
            # on the light page"): the player's own line made transparent
            # (--border, the seam the site sets), and a line of one screen
            # pixel outside the box, in the drawing's line over its own ground,
            # made solid; on the light page the cards' own lift. SINCE THE
            # CRISP BUILD (Nov 20) that lift is the page's one line of shade,
            # and only where the drawing sits on the page itself: IN A CARD it
            # wears its edge and nothing else. Read as part
            # four reads the link page: the drawing hidden for the photograph,
            # and the screen pixels that stand apart from both their neighbours
            # (a line one pixel wide does; a wider line, or a shadow's soft
            # fall, does not). The box's left side on Home's card and on the
            # post's page, and a comment's drawing.
            def _line1(im, pts):
                far = lambda c, d: max(abs(c[k] - d[k]) for k in range(3)) > 4
                px = [im.getpixel(q_) for q_ in pts]
                return sum(1 for i in range(1, len(px) - 1) if far(px[i], px[i - 1]) and far(px[i], px[i + 1]))

            HIDE = "canvas, .skribl-inline-poster, .skribl-inline img { visibility: hidden !important; }"
            stc17, j17 = make_post(ed, "A drawing's edge, one screen pixel.", seed=17, card=True)
            pid17 = j17.get("post") if isinstance(j17, dict) else None
            ec = ed.client()
            ec.get(f"/social/p/{pid17}")
            stcm, _ = ec.post_json(f"/social/p/{pid17}/comments", {"words": "Drawn back.", "payload": drawing(seed=21)})
            art, lifts = {}, {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, ed, screen="phone", scheme=scheme, scale=3)
                for path, sels in (("/social/", [".post-card .post-art .skribl-inline"]),
                                   (f"/social/p/{pid17}", [".post-page .post-art .skribl-inline", ".cm-art .skribl-inline"])):
                    pg.goto(BASE + path)
                    pg.wait_for_timeout(900)
                    for sel in sels:
                        pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.scrollIntoView({ block: 'center' }); }", sel)
                        pg.wait_for_timeout(300)
                        hide = pg.add_style_tag(content=HIDE)
                        pg.wait_for_timeout(120)
                        r = pg.evaluate(BOX, sel)
                        if not r:
                            art[f"{scheme} {sel}"] = None
                            hide.evaluate("s => s.remove()")
                            continue
                        im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                        x, y = round(r[0] * 3), round((r[1] + r[3] / 2) * 3)
                        got = _line1(im, [(i, y) for i in range(x - 6, x + 6)])
                        # ...and by its mechanism, as the link page's edges are read:
                        # the player's own border transparent (a thick line beside a
                        # thin one reads as one thin line), and the line one screen
                        # pixel wide by its own measure, its widest unblurred shadow.
                        mech = pg.evaluate("""(s) => { const c = getComputedStyle(document.querySelector(s));
                            const a = (c.borderLeftColor.match(/[\\d.]+/g) || []).map(Number);
                            const line = (parseFloat(c.borderLeftWidth) || 0) > 0 && (a.length < 4 ? a.length > 0 : a[3] > 0);
                            let w = null;       // its ring: unblurred and not moved (a line of shade under it is moved down, and is not the ring)
                            for (const one of c.boxShadow.split(/,(?![^()]*\\))/)) {
                              const v = (one.replace(/[a-z]+\\([^)]*\\)/g, '').match(/-?[\\d.]+(?=px)/g) || []).map(Number);
                              if (v.length >= 2 && !v[0] && !v[1] && (v.length < 3 || v[2] === 0)) w = Math.max(w || 0, Math.abs(v[3] || 0));
                            }
                            return { border: line ? c.borderLeftColor : null, w: w }; }""", sel)
                        if mech["border"] or mech["w"] is None or abs(mech["w"] * 3 - 1) > 0.05:
                            got = f"{got} and {mech}"
                        art[f"{scheme} {sel}"] = got
                        if ".cm-art" not in sel:
                            # The lift: what its shadow paints under it, past its ring.
                            lifts[f"{scheme} {'in a card' if path == '/social/' else 'on the page'}"] = _shade(pg, im, sel, r, 0.3, "var(--draw-edge)")
                        hide.evaluate("s => s.remove()")
                close_ctx(ctx, pg)
            check("a drawing on the site wears a line of one screen pixel at 3x, light and dark: a post's on Home's card"
                  " and on its own page, and a comment's",
                  stc17 == 200 and stcm == 200 and len(art) == 6 and all(v == 1 for v in art.values()), json.dumps(art))
            check("...and its lift is the crisp one: ON THE PAGE in light (a post's own page) one line of shade under its"
                  " edge (two or three screen rows together, nothing below them); IN A CARD (Home's) its edge alone, the"
                  " shadow painting nothing; in dark, nothing either way",
                  len(lifts) == 4 and _one_line(lifts.get("light on the page")) and lifts.get("light in a card") == []
                  and lifts.get("dark in a card") == [] and lifts.get("dark on the page") == [],
                  json.dumps(lifts))
            # AND BETWEEN THE THREE (the colour audit of Nov 21, choice 1; the owner's "All yes"). --hair was 1, a
            # half and a third: one sharp screen pixel at 1x, 2x and 3x, and two soft ones between (a Windows screen
            # at 125, 150 or 175%; many Android phones at 2.625 and 2.75). A step for each now. READ TWO WAYS. What
            # each page's own sheet says (--hair, as the browser resolves it, times the screen's density: one
            # screen pixel, at every density from 1x to 3x, on the site, the Pad, Skribl's Gallery and its Library:
            # social.css, styles.css, and pagemenu.css with the Gallery section's sheet made from styles.css). And
            # what is painted: a post's card on Home on a touch phone at the five in-between densities the audit
            # read, its left edge counted as the row above counts it at 3x (16px in from the screen's edge, a whole
            # screen pixel at every one of them, so a line that is one is one).
            DENS = (1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.625, 2.75, 3)
            HAIR = "() => { const e = document.querySelector('#skriblGallery') || document.body; const v = getComputedStyle(e).getPropertyValue('--hair').trim(); return v ? parseFloat(v) : null; }"
            per = {}
            for dpr in DENS:
                ctx, pg = browser_as(b, ed, screen="phone", scheme="light", scale=dpr)
                for path in ("/social/", "/skribl-pad", "/gallery", "/library"):
                    pg.goto(BASE + path)
                    pg.wait_for_timeout(350)
                    h = pg.evaluate(HAIR)
                    per[f"{dpr} {path}"] = None if h is None else round(h * dpr, 4)
                close_ctx(ctx, pg)
            off_px = {k: v for k, v in per.items() if v is None or abs(v - 1) > 0.0005}
            check("one screen pixel at every density, as each page's sheet says it: --hair times the screen's density is one"
                  " at 1x, 1.25, 1.5, 1.75, 2x, 2.25, 2.5, 2.625, 2.75 and 3x, on the site, the Pad, the Gallery and the Library",
                  len(per) == len(DENS) * 4 and not off_px, json.dumps(off_px or {"all": len(per)}))
            between = {}
            for dpr in (1.25, 1.5, 1.75, 2.625, 2.75):
                for scheme in ("light", "dark"):
                    ctx, pg = browser_as(b, ed, screen="phone", scheme=scheme, scale=dpr)
                    pg.goto(BASE + "/social/")
                    pg.wait_for_timeout(900)
                    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                    r = pg.evaluate(BOX, ".post-card")
                    x, y = round(r[0] * dpr), round((r[1] + min(r[3], 300) / 2) * dpr)
                    k = lambda n: round(n * dpr)
                    page, inside = im.getpixel((x - k(3), y)), im.getpixel((x + k(4), y))
                    got = _band(im, [(i, y) for i in range(x - k(2), x + k(3))], page, inside)
                    between[f"{dpr} {scheme}"] = {"n": len(got), "at": round(r[0] * dpr, 3), "px": got[:3]}
                    close_ctx(ctx, pg)
            check("...and painted so: a post's card's edge is one screen pixel at 1.25, 1.5, 1.75, 2.625 and 2.75, light and"
                  " dark, on a whole screen pixel (where it was two soft ones)",
                  len(between) == 10 and all(v["n"] == 1 and abs(v["at"] - round(v["at"])) < 0.01 for v in between.values()),
                  json.dumps(between)[:900])
        except Exception as exc:  # noqa: BLE001
            check("section 17 ran to its end", False, str(exc).splitlines()[0][:200])

    if part(18, "a post's full screen: the link page's, from the end of the post's line"):
        # The owner, Nov 16: "yes to A and all your picks", to the mock of full
        # screen on the site's posts. A post's line ends in the full-screen
        # button, after Repeat; a press opens the link page's own full screen
        # (lib/fullbar.js band(), lib/postfull.js) around the post's own
        # player: the band's Restart, Play, Loop and Leave, the post's line
        # lent to it (its scrubber and its words with every speed), the x, and
        # who drew it in the corner, the post's words over "Name · @handle".
        # One player, one clock: the drawing carries on from where it was, and
        # leaving gives the post back as it was. Read on an iPhone's terms: no
        # Fullscreen API, so lib/immersive.js's stand-in. Nothing of the
        # band's sheet reaches the post's own line (it took its tint away and
        # its words to 15px, loaded whole).
        try:
            NO_FS = ("Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get() { return false; } });"
                     "Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get() { return false; } });")
            fs = someone(b, "fulla", "Fulla Screen")
            st18, j18 = make_post(fs, "A slow snail, full screen.", seed=18, card=True)
            pid18 = j18.get("post") if isinstance(j18, dict) else None
            c18 = fs.client()
            c18.get(f"/social/p/{pid18}")
            stc, _ = c18.post_json(f"/social/p/{pid18}/comments", {"words": "And an answer, drawn.", "payload": drawing(seed=19)})
            ctx, pg = browser_as(b, fs)
            ctx.add_init_script(NO_FS)
            pg.goto(BASE + f"/social/p/{pid18}")
            pg.wait_for_function("() => { const b = document.querySelector('.post-page [data-skribl-inline]'); return !!(b && b._skriblInline && b._skriblInline.state().loaded); }", timeout=20000)
            pg.wait_for_timeout(500)
            BTN = """(s) => { const b = document.querySelector(s); if (!b) return null; const r = b.getBoundingClientRect();
                const hit = (x, y) => { const h = document.elementFromPoint(x, y); return !!h && (h === b || b.contains(h)); };
                const prev = b.previousElementSibling;
                return { shown: !!b.getClientRects().length && getComputedStyle(b).display !== 'none', w: Math.round(r.width), h: Math.round(r.height),
                         after: prev ? prev.className : null, last: !b.nextElementSibling, name: b.getAttribute('aria-label'),
                         reach: hit(r.left - 5.5, r.top + r.height / 2) && hit(r.right + 5.5, r.top + r.height / 2) && hit(r.left + r.width / 2, r.top - 5.5) && hit(r.left + r.width / 2, r.bottom + 5.5) }; }"""
            btn = pg.evaluate(BTN, ".post-page .skribl-inline-line .skribl-inline-full")
            check("a post's line ends in the full-screen button, after Repeat: 32px drawn, 44 to a finger, named Full screen",
                  st18 == 200 and bool(btn) and btn["shown"] and btn["w"] == 32 and btn["h"] == 32 and btn["last"]
                  and "skribl-inline-loop" in (btn["after"] or "") and btn["reach"] and btn["name"] == "Full screen", str(btn))
            LINE = """() => { const l = document.querySelector('.post-page .skribl-inline-line'); const sc = l.querySelector('.skribl-inline-scrub'), w = l.querySelector('.skribl-inline-say');
                return { scrubBg: getComputedStyle(sc).backgroundColor, wordsSize: getComputedStyle(w).fontSize, head: (sc.querySelector('.rl-head') || {}).style ? sc.querySelector('.rl-head').style.left : null }; }"""
            before = pg.evaluate(LINE)
            # One player, one clock: put the drawing at 40%, paused, and open.
            pg.evaluate("() => { const p = document.querySelector('.post-page [data-skribl-inline]')._skriblInline; p.seek(p.state().totalMs * 0.4); }")
            pg.wait_for_timeout(200)
            at0 = pg.evaluate("() => document.querySelector('.post-page [data-skribl-inline]')._skriblInline.state().elapsedMs")
            pg.click(".post-page .skribl-inline-full")
            pg.wait_for_timeout(900)
            FULL = """() => { const st = document.querySelector('.post-page .skribl-post-stage'), box = document.querySelector('.post-page [data-skribl-inline]');
                const r = st ? st.getBoundingClientRect() : null, band = st && st.querySelector('.player-bar');
                const prog = band && band.querySelector('.player-progress.rl-scrub'), cv = prog && prog.querySelector('canvas.rl-strip');
                let ink = 0; if (cv && cv.width) { const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; for (let i = 3; i < d.length; i += 4) if (d[i]) ink++; }
                const names = band ? [...band.querySelectorAll('.player-controls .player-btn')].filter(x => x.getClientRects().length).map(x => x.getAttribute('aria-label')) : [];
                const who = st && st.querySelector('.fb-who');
                return { on: !!st && st.classList.contains('is-immersive-page'), rect: r ? [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] : null,
                         immersive: box.classList.contains('is-immersive'), band: !!band && !band.hidden, names, ink,
                         words: band ? (band.querySelector('.replay-line') || {}).textContent || '' : '',
                         x: !!(st && st.querySelector('.player-btn.full-exit') && st.querySelector('.player-btn.full-exit').getClientRects().length),
                         who: who ? [who.querySelector('b').textContent, who.querySelector('span').textContent] : null,
                         at: box._skriblInline.state().elapsedMs, playing: box._skriblInline.state().state,
                         still: getComputedStyle(document.documentElement).overflowY === 'hidden' && getComputedStyle(document.body).overflowY === 'hidden' }; }"""
            f1 = pg.evaluate(FULL)
            check("...a press opens the link page's full screen around the post's player, over the whole screen, the page"
                  " behind held still: Restart, Play, Loop and Leave, the x, and the post's line lent to it (its scrubber"
                  " painted with the drawing, its words with the speed)",
                  f1["on"] and f1["rect"] == [0, 0, 402, 874] and f1["still"] and f1["immersive"] and f1["band"] and f1["x"]
                  and f1["names"][:2] == ["Restart", "Play"] and "Loop" in f1["names"] and "Leave full screen" in f1["names"]
                  and f1["ink"] > 50 and "watching at" in f1["words"], json.dumps(f1)[:600])
            check("...who drew it, in the corner: the post's words over 'Name · @handle'",
                  f1["who"] == ["A slow snail, full screen.", "Fulla Screen · @fulla"], str(f1["who"]))
            check("...and the drawing carries on from where it was: paused at 40%, still there",
                  abs(f1["at"] - at0) < 60 and f1["playing"] != "playing", f"{at0} -> {f1['at']} {f1['playing']}")
            # Play: after a quiet spell the band steps back (the canvas is the
            # hero), and who drew it with it; a move brings them back. The
            # step-back is a class on the stage itself (lib/chromefade.js).
            pg.click(".post-page .skribl-post-stage .player-bar .player-btn[aria-label='Play']")
            pg.wait_for_timeout(4200)
            slept = pg.evaluate("""() => { const st = document.querySelector('.post-page .skribl-post-stage'),
                band = st.querySelector(':scope > .player-bar'), who = st.querySelector(':scope > .fb-who');
                return { asleep: st.classList.contains('chrome-asleep'), band: band ? getComputedStyle(band).opacity : null,
                         who: who ? getComputedStyle(who).opacity : null }; }""")
            check("...while it plays the band steps back, and who drew it with it",
                  slept["asleep"] and slept["band"] == "0" and slept["who"] == "0", str(slept))
            pg.mouse.move(200, 300)
            pg.mouse.move(220, 330)
            pg.wait_for_timeout(500)
            if pg.evaluate("() => document.querySelector('.post-page [data-skribl-inline]')._skriblInline.state().state") == "playing":
                pg.click(".post-page .skribl-post-stage .player-bar .player-btn[aria-label='Pause']")
                pg.wait_for_timeout(300)
            # Leave by the x: the post as it was, its line its own again.
            pg.click(".post-page .skribl-post-stage .player-btn.full-exit")
            pg.wait_for_timeout(700)
            pg.evaluate("() => { const p = document.querySelector('.post-page [data-skribl-inline]')._skriblInline; p.seek(p.state().totalMs * 0.8); }")
            pg.wait_for_timeout(300)
            back = pg.evaluate("""() => { const st = document.querySelector('.post-page .skribl-post-stage'), box = document.querySelector('.post-page [data-skribl-inline]');
                const h = document.querySelector('.post-page .skribl-inline-line .rl-head');
                return { on: st.classList.contains('is-immersive-page'), immersive: box.classList.contains('is-immersive') || box.classList.contains('is-bare'),
                         head: h ? parseFloat(h.style.left) : null, focus: document.activeElement === document.querySelector('.post-page .skribl-inline-full') }; }""")
            check("...and leaving gives the post back as it was: not full screen, its line its own again (a seek moves its"
                  " playhead), the button given the focus back",
                  not back["on"] and not back["immersive"] and back["head"] is not None and abs(back["head"] - 80) < 3
                  and back["focus"], str(back))
            # Again, from the keyboard: the focus goes into the full screen, onto
            # its Play (the button that opened it is under the full screen, and
            # a keyboard's next Tab would land behind it); and the line is lent
            # afresh, the band's scrubber moving with the drawing.
            pg.focus(".post-page .skribl-inline-full")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(800)
            kb = pg.evaluate("""() => { const st = document.querySelector('.post-page .skribl-post-stage'), a = document.activeElement;
                return { on: st.classList.contains('is-immersive-page'), inside: !!a && st.contains(a),
                         play: !!a && a.matches('.player-bar .player-btn.primary') }; }""")
            check("...and opened from the keyboard, the focus goes with it, onto the band's Play",
                  kb["on"] and kb["inside"] and kb["play"], str(kb))
            pg.evaluate("() => { const p = document.querySelector('.post-page [data-skribl-inline]')._skriblInline; p.seek(p.state().totalMs * 0.25); }")
            pg.wait_for_timeout(300)
            again = pg.evaluate("""() => { const h = document.querySelector('.post-page .skribl-post-stage .player-bar .rl-head');
                return h ? parseFloat(h.style.left) : null; }""")
            check("...and open again, the band has the line afresh: its playhead moves with the drawing", again is not None and abs(again - 25) < 3, str(again))
            # The mock: "Repeat and the speed you pick come back to the post
            # with you." Pick 4x in the band's words and Repeat on its Loop,
            # leave, and read the post's own line.
            pg.click(".post-page .skribl-post-stage .player-bar .rl-speed")
            pg.wait_for_timeout(300)
            pg.click(".post-page .skribl-post-stage .player-bar .rl-chips button[data-r='4']")
            pg.wait_for_timeout(300)
            pg.click(".post-page .skribl-post-stage .player-bar .player-btn[aria-label='Loop']")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            came = pg.evaluate("""() => { const st = document.querySelector('.post-page .skribl-post-stage'), l = document.querySelector('.post-page .skribl-inline-line');
                const lp = l.querySelector('.skribl-inline-loop');
                return { on: st.classList.contains('is-immersive-page'), speed: ((l.querySelector('.rl-speed') || {}).textContent || '').trim(),
                         repeat: !l.classList.contains('is-noloop'), pressed: lp ? lp.getAttribute('aria-pressed') : null }; }""")
            check("...and Repeat and the speed picked in full screen come back to the post with it: its line says 4x, and repeats",
                  not came["on"] and came["speed"] == "4×" and came["repeat"] and came["pressed"] == "true", str(came))
            after = pg.evaluate(LINE)
            check("...nothing of the full screen's sheets reaches the post's own line: its scrubber's tint and its words' size"
                  " as they are with no full screen on the page",
                  after["scrubBg"] == before["scrubBg"] and after["wordsSize"] == before["wordsSize"] == "14px", f"{before} -> {after}")
            # A COMMENT'S LINE WAITS FOR THE FIRST PLAY (the walkthrough's mocks,
            # choice 4, Nov 19), as a card's does, and its full-screen button with
            # it: the drawing is played first, as somebody would.
            pg.evaluate("() => { const b = document.querySelector('.cm .cm-art .skribl-inline'); if (b) b.scrollIntoView({ block: 'center' }); }")
            pg.wait_for_timeout(300)
            waited18 = pg.evaluate("() => { const l = document.querySelector('.cm .cm-art .skribl-inline-line'); return !!l && l.classList.contains('is-waiting'); }")
            pg.click(".cm .cm-art .skribl-inline")
            pg.wait_for_timeout(900)
            pg.evaluate("() => { const b = document.querySelector('.cm .skribl-inline-full'); if (b) b.scrollIntoView({ block: 'center' }); }")
            pg.wait_for_timeout(400)
            cm = pg.evaluate(BTN, ".cm .skribl-inline-line .skribl-inline-full")
            cmf = None
            if cm and cm["shown"]:
                pg.click(".cm .skribl-inline-full")
                pg.wait_for_timeout(900)
                cmf = pg.evaluate("""() => { const st = document.querySelector('.cm .skribl-post-stage'), who = st && st.querySelector('.fb-who');
                    return { on: !!st && st.classList.contains('is-immersive-page'), who: who ? [who.querySelector('b').textContent, who.querySelector('span').textContent] : null }; }""")
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(400)
            check("...and a comment's drawing, once played (its line waits till then), ends its line in the same button,"
                  " which opens the same full screen, its own words over its maker",
                  stc == 200 and waited18 and bool(cm) and cm["shown"] and cm["w"] == 32 and cm["reach"] and bool(cmf) and cmf["on"]
                  and cmf["who"] == ["And an answer, drawn.", "Fulla Screen · @fulla"], f"{cm} {cmf}")
            close_ctx(ctx, pg)
        except Exception as exc:  # noqa: BLE001
            check("section 18 ran to its end", False, str(exc).splitlines()[0][:200])
    if part(19, "words alone: a post can be its words, as a comment can (the owner's \"I like your pick\", Nov 16)"):
        # A on the words-only mock: Post works once there are words, and the
        # post is its words and its row, no empty drawing box; its own page the
        # words and the comments under them; the Gallery never shows it (it has
        # no drawing); a post of nothing is still refused (part 6).
        try:
            wo = someone(b, "wordy", "Wren Words")
            WORDS = "What should I draw this weekend? Ideas welcome."
            make_post(wo, "A drawing to stand beside it.", seed=19, card=True)
            ctx, pg = browser_as(b, wo)
            sent = []
            pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and r.url.endswith("/social/posts") else None)
            pg.goto(BASE + "/social/explore")
            pg.wait_for_timeout(700)
            pg.locator("nav.nav .tab-make").first.tap(force=True)
            pg.wait_for_timeout(700)
            pg.fill("#composeSheet [data-compose-words]", WORDS)
            pg.wait_for_timeout(200)
            lit = pg.evaluate("() => document.querySelector('#composeSheet [data-compose-post]').getAttribute('aria-disabled')")
            try:
                with pg.expect_navigation(timeout=15000):
                    pg.locator("#composeSheet [data-compose-post]").first.tap(force=True)
            except Exception:  # noqa: BLE001
                pass
            pg.wait_for_timeout(700)
            at = pg.url
            pid = at.split("#")[0].rstrip("/").split("/")[-1] if "/social/p/" in at else None
            page = pg.evaluate("""() => ({ words: ((document.querySelector('.post-page .post-words') || {}).textContent || '').trim(),
                art: !!document.querySelector('.post-page .post-art, .post-page [data-skribl-inline]'),
                comments: !!document.querySelector('#comments') })""")
            row = db("select skribl_id, is_quote, words from social_posts where public_id = ?", (pid,)) if pid else []
            pg.goto(BASE + "/social/@wordy")
            pg.wait_for_timeout(900)
            card = pg.evaluate("""(pid) => { const c = document.querySelector('.post-card[data-post="' + pid + '"]'); if (!c) return null;
                const d = [...document.querySelectorAll('.post-card')].find(x => x !== c && x.querySelector('.post-art'));
                return { words: ((c.querySelector('.post-words') || {}).textContent || '').trim(), art: !!c.querySelector('.post-art, [data-skribl-inline]'),
                         row: !!c.querySelector('.post-row'), h: Math.round(c.getBoundingClientRect().height),
                         drawn: d ? Math.round(d.getBoundingClientRect().height) : null }; }""", pid)
            pg.goto(BASE + "/social/explore")
            pg.wait_for_timeout(900)
            tiles = pg.evaluate("""(pid) => ({ n: document.querySelectorAll('.gal-tile').length,
                it: [...document.querySelectorAll('.gal-tile')].some(t => (t.getAttribute('href') || '').includes('/p/' + pid)) })""", pid)
            close_ctx(ctx, pg)
            check("words alone are a post: Make's Post lit once there are words, a press posting them and going to the new"
                  " post, which is its words and the comments under them, no drawing; stored with no drawing and no quote",
                  lit == "false" and len(sent) == 1 and bool(pid) and page["words"] == WORDS and not page["art"]
                  and page["comments"] and row == [(None, 0, WORDS)],
                  f"lit {lit}; sent {len(sent)}; at {at}; page {page}; row {row}")
            check("...its card is its words and its row, no empty drawing box, shorter than a drawing's card; and the"
                  " Gallery, which holds drawings, never shows it",
                  bool(card) and card["words"] == WORDS and not card["art"] and card["row"]
                  and card["drawn"] is not None and card["h"] < card["drawn"] and tiles["n"] >= 1 and not tiles["it"],
                  f"card {card}; gallery {tiles}")
        except Exception as exc:  # noqa: BLE001
            check("section 19 ran to its end", False, str(exc).splitlines()[0][:200])

    if part(20, "the walkthrough's small ones: an initial in a face not drawn yet; the Gallery's pills on one line"):
        # Choices 9 and 10 of the walkthrough's mocks (the owner's "all yes",
        # Nov 19). A FACE NOT DRAWN YET was a blank lilac circle on a card and
        # on a post's own page; it shows its person's initial there now, as a
        # comment's has since Nov 17 (a Gallery tile's 22px face stays plain,
        # as decided there). THE GALLERY'S SEARCH BOX shared New | Hot's line,
        # and a 402px phone left it 178px for words that need 217; the two
        # pills share a line now and the box takes the next one whole.
        try:
            op = someone(b, "opaln", "Opal Nakamura")
            st20, j20 = make_post(op, "Section 20, no face drawn yet", seed=201)
            p20 = j20.get("post") if st20 == 200 and isinstance(j20, dict) else None
            FACE20 = """(sel) => { const f = document.querySelector(sel); if (!f) return null;
              const lum = c => { const v = (c.match(/[\\d.]+/g) || []).slice(0, 3).map(Number).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                                 return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
              const bl = f.querySelector('.face-blank'), cs = bl ? getComputedStyle(bl) : null, r = f.getBoundingClientRect();
              const a = cs ? lum(cs.color) : 0, g = cs ? lum(cs.backgroundColor) : 0;
              const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { disc: Math.round(r.width), letter: bl ? bl.textContent.trim() : null, font: cs ? cs.fontSize : null,
                       bold: !!cs && parseInt(cs.fontWeight, 10) >= 700, painted: !!at && f.contains(at),
                       ratio: cs ? Math.round((Math.max(a, g) + 0.05) / (Math.min(a, g) + 0.05) * 100) / 100 : 0 }; }"""
            ROOM20 = """() => { const i = document.querySelector('[data-gal-q]'), cs = getComputedStyle(i), r = i.getBoundingClientRect();
              const c = document.createElement('canvas').getContext('2d'); c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
              const words = Math.ceil(c.measureText(i.placeholder).width);
              const room = Math.floor(i.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight));
              const pills = [...document.querySelectorAll('[data-gal-show], [data-gal-sort]')].map(e => e.getBoundingClientRect());
              const col = document.querySelector('.gal-bar').getBoundingClientRect();
              return { words, room, fits: words <= room, n: pills.length, oneLine: pills.every(p => Math.abs(p.top - pills[0].top) < 1),
                       apart: pills.length > 1 ? Math.round(pills[1].left - pills[0].right) : null,
                       under: pills.length > 0 && pills.every(p => r.top >= p.bottom), whole: Math.abs(r.width - col.width) <= 1,
                       below: pills.length ? Math.round(r.top - pills[0].bottom) : null,
                       pageScrolls: document.documentElement.scrollWidth > innerWidth }; }"""
            faces20, rooms20 = {}, {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, op, "phone", scheme)
                pg.goto(BASE + "/social/")
                pg.wait_for_timeout(700)
                faces20[f"card {scheme}"] = pg.evaluate(FACE20, f'.post-card[data-post="{p20}"] .post-face > .face-ring')
                pg.goto(BASE + f"/social/p/{p20}")
                pg.wait_for_timeout(700)
                faces20[f"page {scheme}"] = pg.evaluate(FACE20, ".post-page .post-head .post-face > .face-ring")
                pg.goto(BASE + "/social/explore")
                pg.wait_for_timeout(700)
                faces20[f"tile {scheme}"] = pg.evaluate(FACE20, f'.gal-tile[data-post="{p20}"] .gal-by .face-ring')
                rooms20[f"phone {scheme}"] = pg.evaluate(ROOM20)
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, op, "desk", "light")
            pg.goto(BASE + "/social/explore")
            pg.wait_for_timeout(700)
            rooms20["desk light"] = pg.evaluate(ROOM20)
            close_ctx(ctx, pg)
            want20 = {"card": (44, "O", "16px"), "page": (48, "O", "19px")}
            check("a face not drawn yet says whose it is: her initial on her post's card (16px in the 44px disc) and on the"
                  " post's own page (19px in the 48px one), bold, painted, at 4.5:1 or more on its disc, light and dark; a"
                  " Gallery tile's small face stays plain, no letter",
                  bool(p20) and all((v or {}).get("disc") == want20[k.split()[0]][0] and v.get("letter") == want20[k.split()[0]][1]
                                    and v.get("font") == want20[k.split()[0]][2] and v.get("bold") and v.get("painted")
                                    and v.get("ratio", 0) >= 4.5 for k, v in faces20.items() if not k.startswith("tile"))
                  and all((v or {}).get("letter") == "" and v.get("disc") == 22 for k, v in faces20.items() if k.startswith("tile")),
                  json.dumps(faces20))
            check("the Gallery, signed in: Following | Everyone and New | Hot share one line, 8px apart, and the search box"
                  " takes the next line whole, 10px under them, with room for all of its words (a phone, light and dark; a"
                  " desk); nothing makes the page scroll sideways",
                  all(v["n"] == 2 and v["oneLine"] and v["apart"] == 8 and v["under"] and v["whole"] and v["below"] == 10
                      and v["fits"] and not v["pageScrolls"] for v in rooms20.values()), json.dumps(rooms20))
        except Exception as exc:  # noqa: BLE001
            check("section 20 ran to its end", False, str(exc).splitlines()[0][:200])

    # ------------------------------------------------------------------ 21
    if part(21, "the way back: a screen's arrow goes where you were (the owner, Nov 20: \"You end up stranded a lot\")"):
        # A post's arrow and Activity's were links to Home, whatever you had
        # come from; a comment's own page alone went back where you were. A
        # phone's Home Screen app has no browser Back, so from the Gallery or a
        # profile a post's arrow lost your place. ONE RULE NOW (social.js): the
        # page you came from on this site, as the browser's own Back; opened
        # from anywhere else, the arrow's own address (Home).
        try:
            wren = someone(b, "wrenb", "Wren Baptiste")
            st21, j21 = make_post(wren, "Section 21, the way back", gallery=True, seed=211)
            p21 = j21.get("post") if st21 == 200 and isinstance(j21, dict) else None
            ctx, pg = browser_as(b, wren)

            def at(page_):
                return page_.evaluate("() => location.protocol === 'data:' ? 'the other site' : location.pathname")

            def arrow(page_):
                """Press the screen's arrow as a person does; say where it leaves you (the same page, if nowhere)."""
                was = page_.evaluate("() => location.href")
                page_.click("a.top-back", timeout=8000)
                try:
                    page_.wait_for_function("(u) => location.href !== u", arg=was, timeout=5000)
                    page_.wait_for_load_state("load")
                    page_.wait_for_timeout(300)
                except Exception:  # noqa: BLE001 -- it went nowhere: that is the answer
                    pass
                return at(page_)

            def into_post(page_, start):
                """From `start`, open the post by the first of its links that shows, as a person does."""
                page_.goto(BASE + start)
                page_.wait_for_load_state("load")
                page_.wait_for_timeout(500)
                link = page_.locator(f'a[href^="/social/p/{p21}"]').locator("visible=true").first
                link.scroll_into_view_if_needed(timeout=8000)
                with page_.expect_navigation(timeout=15000):
                    link.click()
                page_.wait_for_load_state("load")
                page_.wait_for_timeout(300)
                return at(page_)

            came, back = {}, {}
            for name, start in (("the Gallery", "/social/explore"), ("her profile", "/social/@wrenb"), ("Home", "/social/")):
                came[name] = into_post(pg, start)
                back[name] = arrow(pg)
            check("a post's arrow goes where you were: opened from the Gallery it brings you back to the Gallery, from a"
                  " profile to the profile, from Home to Home (it went to Home whatever you had come from)",
                  bool(p21) and all(v == f"/social/p/{p21}" for v in came.values())
                  and back == {"the Gallery": "/social/explore", "her profile": "/social/@wrenb", "Home": "/social/"},
                  f"opened {came}; the arrow then {back}")
            # Activity's arrow: opened by the bell from the Gallery, back on the Gallery.
            pg.goto(BASE + "/social/explore")
            pg.wait_for_load_state("load")
            pg.wait_for_timeout(400)
            with pg.expect_navigation(timeout=15000):
                pg.locator('body > .top a[href$="/social/activity"]').first.click()
            pg.wait_for_load_state("load")
            act_at = at(pg)
            act_back = arrow(pg)
            check("Activity's arrow the same: opened by the bell on the Gallery, it brings you back to the Gallery",
                  act_at == "/social/activity" and act_back == "/social/explore", f"at {act_at}; the arrow then {act_back}")
            # OPENED FROM ANYWHERE ELSE, THE ARROW'S OWN ADDRESS: cold; a new tab opened from this site (the page
            # you came from is this site's, but there is nothing behind you to go back to); and from another site
            # (a page behind you, and it is not ours: the arrow never leads out of the site).
            pg.goto(BASE + f"/social/p/{p21}")
            pg.wait_for_load_state("load")
            names = pg.evaluate("() => ({ says: document.querySelector('a.top-back').getAttribute('aria-label'),"
                                " box: (r => [Math.round(r.width), Math.round(r.height)])(document.querySelector('a.top-back').getBoundingClientRect()) })")
            cold = arrow(pg)
            pg.goto(BASE + "/social/")
            pg.wait_for_load_state("load")
            with ctx.expect_page(timeout=15000) as pop:
                pg.evaluate("(u) => { window.open(u); }", f"/social/p/{p21}")
            tab = pop.value
            tab.wait_for_load_state("load")
            tab.wait_for_timeout(300)
            tab_from = tab.evaluate("() => [document.referrer.replace(location.origin, ''), history.length]")
            new_tab = arrow(tab)
            tab.close()
            pg.goto("data:text/html," + urllib.parse.quote(f'<a id="x" href="{BASE}/social/p/{p21}">a link somebody sent</a>'))
            with pg.expect_navigation(timeout=15000):
                pg.click("#x")
            pg.wait_for_load_state("load")
            sent_from = pg.evaluate("() => [document.referrer, history.length]")
            sent = arrow(pg)
            pg.goto(BASE + "/social/activity")
            pg.wait_for_load_state("load")
            names["activity"] = pg.evaluate("() => document.querySelector('a.top-back').getAttribute('aria-label')")
            close_ctx(ctx, pg)
            check("opened from anywhere else it is the arrow's own address, Home: a post opened cold; one opened in a new"
                  " tab from this site, with nothing behind it to go back to; and one come to from another site, which"
                  " the arrow never leads back out to",
                  cold == "/social/" and new_tab == "/social/" and tab_from == ["/social/", 1] and sent == "/social/"
                  and sent_from[0] == "" and sent_from[1] >= 2,
                  f"cold {cold}; a new tab (came from {tab_from}) {new_tab}; from another site (came from {sent_from}) {sent}")
            check("the arrow says \"Back\" on a post and on Activity (it said \"Back to Home\"), and is 44px to press",
                  names.get("says") == "Back" and names.get("activity") == "Back" and min(names.get("box") or [0]) >= 44,
                  json.dumps(names))
            # PART TWO (the owner's "All yes", Nov 20, to the mock's A): THE ARROW ON THE SCREENS THAT HAD NONE. Every
            # screen the bar does not lead to has it at its top's start with the screen's name beside it, as a
            # post's top; the page's big heading then leaves a phone (a screen reader's still, and a desk's).
            TOP21 = """() => { const top = document.querySelector('body > .top'), a = top && top.querySelector('a.top-back'), t = top && top.querySelector('.top-title');
              const shows = e => { if (!e || !e.getClientRects().length) return false; const r = e.getBoundingClientRect();
                if (r.width < 3 || r.height < 3) return false; const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!at && (e === at || e.contains(at)); };
              const h = document.querySelector('h1'), r = a && a.getBoundingClientRect();
              return { arrow: shows(a) ? [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] : null, to: a ? a.getAttribute('href') : null,
                       says: a ? a.getAttribute('aria-label') : null, title: shows(t) ? t.textContent.trim() : null,
                       h1: h ? h.textContent.trim() : null, h1shows: shows(h), mark: shows(top && top.querySelector('.brand')) }; }"""
            kit = someone(b, "kitm", "Kit Moreau")
            ctx, pg = browser_as(b, wren)

            def top_of(page_, path):
                page_.goto(BASE + path)
                page_.wait_for_load_state("load")
                page_.wait_for_timeout(300)
                return page_.evaluate(TOP21)

            # SEE ALL, the people alone, the Gallery's and Search's (Nov 22, owed from part two: it kept the ☰ and the
            # bell, and a phone's Home Screen app had no way back from it): "People" beside the arrow.
            inner = {"Settings": "/social/you", "Edit profile": "/social/you/edit", "Delete account": "/social/you/delete", "How it works": "/social/how",
                     "Community rules": "/social/rules", "Privacy": "/social/privacy", "Terms": "/social/terms", "@kitm": "/social/@kitm",
                     "the Gallery's See all": "/social/explore?q=kit&who=people", "Search's See all": "/social/search?q=kit&who=people"}
            titles = {"the Gallery's See all": "People", "Search's See all": "People"}
            tops = {name: top_of(pg, path) for name, path in inner.items()}
            roots = {name: top_of(pg, path) for name, path in (("Home", "/social/"), ("the Gallery", "/social/explore"), ("Search", "/social/search"),
                                                                  ("your own profile", "/social/@wrenb"))}
            post_top = top_of(pg, f"/social/p/{p21}")
            homes = {"Settings": "/social/@wrenb", "Edit profile": "/social/@wrenb", "Delete account": "/social/you", "How it works": "/social/",
                     "Community rules": "/social/", "Privacy": "/social/", "Terms": "/social/", "@kitm": "/social/",
                     "the Gallery's See all": "/social/explore?q=kit", "Search's See all": "/social/search?q=kit"}
            # the heading the top has taken the place of is not shown on a phone; Delete account's is the question the
            # page asks, and a profile's is the person's name, so those two stay
            stays = {"Delete account": "Delete your account?", "@kitm": "Kit Moreau"}
            check("every screen the bar does not lead to has the arrow at its top's start, where a post's is, 44px, painted,"
                  " saying \"Back\", its own name beside it and its own address behind it (Settings, Edit profile, Delete"
                  " account, How it works, the three rules pages, somebody's profile, and the people alone, the Gallery's"
                  " and Search's See all, \"People\", back to the search); Home, the Gallery, Search and your own profile"
                  " have none; the page's big heading leaves a phone where the top says it, and stays where it says more"
                  " (Delete account's question, a person's name)",
                  bool(post_top.get("arrow")) and all(v["arrow"] == post_top["arrow"] and min(v["arrow"][2:]) >= 44 and v["says"] == "Back"
                                                      and v["title"] == titles.get(name, name) and v["to"] == homes[name] and not v["mark"]
                                                      and (v["h1shows"] and v["h1"] == stays[name] if name in stays
                                                           else (not v["h1shows"] and bool(v["h1"])))
                                                      for name, v in tops.items())
                  and all(v["arrow"] is None for v in roots.values()),
                  f"a post's {post_top.get('arrow')}; {json.dumps({k: [v['arrow'], v['title'], v['to'], v['h1'], v['h1shows']] for k, v in tops.items()})};"
                  f" roots {json.dumps({k: v['arrow'] for k, v in roots.items()})}")
            # WHERE THEY GO: where you were; opened cold, the screen each belongs to.
            went = {}
            pg.goto(BASE + "/social/@wrenb")
            pg.wait_for_load_state("load")
            with pg.expect_navigation(timeout=15000):
                pg.locator('a[href$="/social/you/edit"]').locator("visible=true").first.click()
            pg.wait_for_load_state("load")
            went["Edit profile, from your profile"] = arrow(pg)
            with pg.expect_navigation(timeout=15000):
                pg.locator('body > .top a[href$="/social/you"]').first.click()
            pg.wait_for_load_state("load")
            with pg.expect_navigation(timeout=15000):
                pg.locator('a[href$="/social/you/delete"]').locator("visible=true").first.click()
            pg.wait_for_load_state("load")
            went["Delete account, from Settings"] = arrow(pg)
            went["Settings, from your profile"] = arrow(pg)
            pg.goto(BASE + f"/social/p/{p21}")
            pg.wait_for_load_state("load")
            pg.evaluate("(u) => { location.href = u; }", "/social/@kitm")
            pg.wait_for_function("() => location.pathname === '/social/@kitm'", timeout=15000)
            pg.wait_for_load_state("load")
            went["a profile, from a post"] = arrow(pg)
            for name, path in (("Edit profile, cold", "/social/you/edit"), ("Delete account, cold", "/social/you/delete"), ("Settings, cold", "/social/you"),
                               ("a profile, cold", "/social/@kitm"), ("How it works, cold", "/social/how")):
                tab = ctx.new_page()
                tab.goto(BASE + path)
                tab.wait_for_load_state("load")
                went[name] = arrow(tab)
                tab.close()
            # See all's arrow: back to the search it came from, its words there; opened cold, that search's address.
            went_all = {}
            for name, start, path in (("the Gallery's See all, from its search", "/social/explore?q=kit", "/social/explore?q=kit&who=people"),
                                      ("Search's See all, from its search", "/social/search?q=kit", "/social/search?q=kit&who=people")):
                pg.goto(BASE + start)
                pg.wait_for_load_state("load")
                pg.evaluate("(u) => { location.href = u; }", path)
                pg.wait_for_function("(u) => location.pathname + location.search === u", arg=path, timeout=15000)
                pg.wait_for_load_state("load")
                arrow(pg)
                went_all[name] = pg.evaluate("() => [location.pathname + location.search, (document.querySelector('[data-gal-q]') || {}).value]")
            for name, path in (("the Gallery's See all, cold", "/social/explore?q=kit&who=people"), ("Search's See all, cold", "/social/search?q=kit&who=people")):
                tab = ctx.new_page()
                tab.goto(BASE + path)
                tab.wait_for_load_state("load")
                arrow(tab)
                went_all[name] = tab.evaluate("() => [location.pathname + location.search, (document.querySelector('[data-gal-q]') || {}).value]")
                tab.close()
            close_ctx(ctx, pg)
            check("and each goes where you were: Edit profile opened from your profile back to your profile, Delete account"
                  " opened from Settings back to Settings, Settings opened by your profile's gear back to your profile, a"
                  " profile opened from a post back to the post; opened cold, to the screen it belongs to (Edit profile"
                  " and Settings to your profile, Delete account to Settings, a profile and How it works to Home)",
                  went == {"Edit profile, from your profile": "/social/@wrenb", "Delete account, from Settings": "/social/you",
                           "Settings, from your profile": "/social/@wrenb", "a profile, from a post": f"/social/p/{p21}",
                           "Edit profile, cold": "/social/@wrenb", "Delete account, cold": "/social/you",
                           "Settings, cold": "/social/@wrenb", "a profile, cold": "/social/", "How it works, cold": "/social/"},
                  json.dumps(went))
            check("...and See all, the Gallery's and Search's, goes back to the search it came from, its words still in the"
                  " box; opened cold, to that search's own address",
                  went_all == {"the Gallery's See all, from its search": ["/social/explore?q=kit", "kit"],
                               "Search's See all, from its search": ["/social/search?q=kit", "kit"],
                               "the Gallery's See all, cold": ["/social/explore?q=kit", "kit"],
                               "Search's See all, cold": ["/social/search?q=kit", "kit"]},
                  json.dumps(went_all))
            # A DOOR SCREEN keeps the mark in the middle and has the arrow at the top's start; A DESK shows no arrow
            # anywhere (it has no top bar, and the browser has Back) and shows the headings.
            nctx, npg = browser_as(b, None)
            door = top_of(npg, "/social/signin")
            out_how = top_of(npg, "/social/how")
            close_ctx(nctx, npg)
            dctx, dpg = browser_as(b, wren, "desk")
            desk = {name: top_of(dpg, path) for name, path in (("Settings", "/social/you"), ("How it works", "/social/how"), ("@kitm", "/social/@kitm"),
                                                                 ("See all", "/social/search?q=kit&who=people"))}
            close_ctx(dctx, dpg)
            nd, ndp = browser_as(b, None, "desk")
            desk["Sign in"] = top_of(ndp, "/social/signin")
            close_ctx(nd, ndp)
            check("a door screen (Sign in) has the arrow at the same place with the mark still in the middle, and How it"
                  " works keeps its arrow and its name before you sign in; on a desk no arrow shows anywhere and the"
                  " headings do (Settings, How it works, a profile, See all, Sign in)",
                  door["arrow"] == post_top["arrow"] and door["mark"] and door["to"] == "/social/" and door["h1shows"]
                  and out_how["arrow"] == post_top["arrow"] and out_how["title"] == "How it works"
                  and all(v["arrow"] is None and v["h1shows"] for v in desk.values()),
                  f"Sign in {[door['arrow'], door['mark'], door['to']]}; signed out, How it works {[out_how['arrow'], out_how['title']]};"
                  f" a desk {json.dumps({k: [v['arrow'], v['h1shows']] for k, v in desk.items()})}")
            # THE MARK'S INK IN THE MIDDLE (the owner, Nov 20, of a door screen's top: "blooby. Does not look
            # centered, does it?"). The row above says "in the middle" and asked only that the mark was painted:
            # its LINK was in the middle, and the word stood 7.75px left of it (the link is 76px wide for a 61px
            # mark, and the mark stood at the link's start). READ OFF THE PAINT, at two pixels to one: the columns
            # of a picture of the screen that carry the mark's ink, against the screen's middle and the middle of
            # the heading under it. A DESK's door has the mark at the page's start (the rail's place), where there
            # is nothing to centre: its box starts where the bar's room does.
            MARK21 = """() => { const top = document.querySelector('body > .top'), m = top && top.querySelector('.brand .brand-mark');
              if (!m || !m.getClientRects().length) return null;
              // the heading the screen shows now (Join and a passkey's link carry more than one, for what the link turns out to be)
              const h = [...document.querySelectorAll('main h1, main h2')].find(e => e.getClientRects().length);
              const r = m.getBoundingClientRect(), hr = h ? h.getBoundingClientRect() : null;
              const tr = top.getBoundingClientRect(), cs = getComputedStyle(top);
              return { box: [r.left, r.top, r.right, r.bottom], w: innerWidth, head: hr ? (hr.left + hr.right) / 2 : null,
                       says: h ? h.textContent.trim().slice(0, 30) : null, start: tr.left + parseFloat(cs.paddingLeft) }; }"""

            def mark_of(page_, path):
                page_.goto(BASE + path)
                page_.wait_for_load_state("load")
                page_.wait_for_timeout(400)
                g = page_.evaluate(MARK21)
                if not g or Image is None:
                    return {"ink": None, "why": "no mark on the page" if not g else "Pillow is not installed"}
                im = Image.open(io.BytesIO(page_.screenshot())).convert("RGB")
                k = im.size[0] / g["w"]                          # the picture's pixels to one of the page's
                x0, y0 = max(int((g["box"][0] - 8) * k), 0), max(int((g["box"][1] - 2) * k), 0)
                x1, y1 = min(int((g["box"][2] + 9) * k), im.size[0]), min(int((g["box"][3] + 8) * k), im.size[1])
                ground = im.getpixel((x0, y0))
                cols = [x for x in range(x0, x1)
                        if any(sum(abs(a - c) for a, c in zip(im.getpixel((x, y)), ground)) > 60 for y in range(y0, y1))]
                if not cols:
                    return {"ink": None, "why": "no ink where the mark's box is"}
                mid = (cols[0] + cols[-1] + 1) / 2 / k
                return {"ink": [round(cols[0] / k, 1), round((cols[-1] + 1) / k, 1)], "off": round(mid - g["w"] / 2, 2),
                        "head": None if g["head"] is None else round(g["head"] - g["w"] / 2, 2), "says": g["says"],
                        "box": round(g["box"][0] - g["start"], 2)}

            marks = {}
            for scheme in ("light", "dark"):
                mctx, mpg = browser_as(b, None, "phone", scheme, scale=2)
                for name, path in (("Sign in", "/social/signin"), ("Join", "/social/join"), ("a link to add a passkey", "/social/recover")):
                    marks[f"{name}, {scheme}"] = mark_of(mpg, path)
                close_ctx(mctx, mpg)
            mctx, mpg = browser_as(b, None, "desk", "light", scale=2)
            desk_mark = mark_of(mpg, "/social/signin")
            close_ctx(mctx, mpg)
            check("on a phone the mark's INK is in the middle of the screen on every door screen (Sign in, Join, a link to"
                  " add a passkey; light and dark), within a pixel, over a heading that is; on a desk it starts where the"
                  " bar's room does, as before",
                  all(v.get("ink") and abs(v["off"]) <= 1 and v["head"] is not None and abs(v["head"]) <= 1 for v in marks.values())
                  and bool(desk_mark.get("ink")) and abs(desk_mark["box"]) <= 0.5,
                  f"{json.dumps(marks)}; a desk {json.dumps(desk_mark)}")
            # ...AND ON HOME, THE GALLERY AND SEARCH (the owner's pick A of "Blooby and Search", Nov 22: "I like A"): the
            # mark's ink in the middle of a phone's top, as Bluesky's butterfly sits, read off the paint the same way;
            # the ☰ at the top's start and the bell (or Sign in) at its end, where they were, the mark clear of both.
            SIDES21 = """() => { const top = document.querySelector('body > .top'); if (!top) return null;
              const r = (s) => { const e = top.querySelector(s); if (!e || !e.getClientRects().length) return null;
                const q = e.getBoundingClientRect(); return [q.left, q.right]; };
              return { menu: r('.top-menu'), end: r('.top-bell') || r('.top-signin'), mark: r('.brand .brand-mark'), w: innerWidth }; }"""
            homes = {}
            for who21, tag21 in ((wren, "signed in"), (None, "signed out")):
                for scheme in ("light", "dark"):
                    hctx, hpg = browser_as(b, who21, "phone", scheme, scale=2)
                    for name21, path21 in (("Home", "/social/"), ("the Gallery", "/social/explore"), ("Search", "/social/search")):
                        got21 = mark_of(hpg, path21)
                        got21["sides"] = hpg.evaluate(SIDES21)
                        homes[f"{name21}, {tag21}, {scheme}"] = got21
                    close_ctx(hctx, hpg)

            def sides_ok(v):
                s = v.get("sides") or {}
                m, end = s.get("mark"), s.get("end")
                # the ☰ (Home, the Gallery and Search) at the top's start, 10px past it as built; the bell or
                # Sign in at the end; the mark between them, touching neither
                menu_ok = s.get("menu") is None or (abs(s["menu"][0] - 6) <= 1 and s["menu"][1] < m[0])
                return bool(m and end) and menu_ok and end[1] >= s["w"] - 17 and end[0] > m[1]
            check("on a phone the mark's ink is in the middle of the top on Home, the Gallery and Search too (its top the"
                  " Gallery's, Nov 22), within a pixel, signed in and out, light and dark (the owner's pick A, as Bluesky's"
                  " butterfly sits); the ☰ stays at the top's start and the bell or Sign in at its end, the mark touching"
                  " neither",
                  len(homes) == 12 and all(v.get("ink") and abs(v["off"]) <= 1 and sides_ok(v) for v in homes.values()),
                  json.dumps({k: {"ink": v.get("ink"), "off": v.get("off"), "sides": v.get("sides"), "why": v.get("why")} for k, v in homes.items()})[:1600])

            # A WRONG ADDRESS (owed from this section's own build, Nov 20: "a kind page for a wrong address"; it
            # was the app's bare "Not Found", with no bar and no way home). GONE TO, the way a person goes there:
            # signed out and signed in, a phone and a desk. An address that was never one, one a level deeper, a
            # real page's with a slash too many, and a form's own address (the site has it under POST alone).
            LOST21 = """() => { const c = document.querySelector('.si-card');
              if (!c) return { card: false, says: document.body.innerText.trim().slice(0, 60) };
              const h = c.querySelector('h1'), a = c.querySelector('a.btn-primary'), i = c.querySelector('img.si-icon');
              const on = e => { if (!e) return false; const r = e.getBoundingClientRect();
                const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!t && (t === e || e.contains(t)); };
              const nav = document.querySelector('nav.nav'), words = c.querySelector('.si-lede');
              return { card: true, title: h ? h.textContent.trim() : null, words: words ? words.textContent.trim() : '',
                       home: a ? a.getAttribute('href') : null, homePainted: on(a), tall: a ? Math.round(a.getBoundingClientRect().height) : 0,
                       icon: on(i), nav: !!nav && nav.getClientRects().length > 0, lit: nav ? nav.querySelectorAll('[aria-current]').length : 0,
                       wide: document.documentElement.scrollWidth - innerWidth }; }"""
            lost = {}
            for who21, tag21 in ((None, "signed out"), (wren, "signed in")):
                for screen21 in ("phone", "desk"):
                    lctx, lpg = browser_as(b, who21, screen21)
                    for name21, path21 in (("never one", "/social/no-such-page"), ("a level deeper", "/social/no/such/page"),
                                           ("a slash too many", "/social/explore/"),
                                           ("a form's own address", f"/social/@{wren.handle}/follow")):
                        resp21 = lpg.goto(BASE + path21)
                        lpg.wait_for_load_state("load")
                        got21 = lpg.evaluate(LOST21)
                        got21["status"] = resp21.status if resp21 else None
                        lost[f"{name21}, {tag21}, {screen21}"] = got21
                    # ...and its one button is a way out: it lands on Home.
                    home21 = None
                    if lpg.locator(".si-card a.btn-primary").count():
                        lpg.click(".si-card a.btn-primary")
                        lpg.wait_for_load_state("load")
                        home21 = lpg.evaluate("() => location.pathname")
                    lost[f"its way home, {tag21}, {screen21}"] = {"at": home21}
                    close_ctx(lctx, lpg)
            bad_lost = {k: v for k, v in lost.items() if not (
                v.get("at") == "/social/" if k.startswith("its way home") else
                (v.get("status") == 404 and v.get("card") and v["title"] == "That page isn’t here" and "Blooby" in v["words"]
                 and v["home"] == "/social/" and v["homePainted"] and v["tall"] >= 44 and v["icon"] and v["nav"]
                 and v["lit"] == 0 and v["wide"] <= 0))}
            check("a wrong address is a kind page with a way out, where it was a bare \"Not Found\": an address that was"
                  " never one, one a level deeper, a real page's with a slash too many and a form's own address, gone to"
                  " signed out and signed in, on a phone and a desk, each answer 404 with Blooby's card (\"That page"
                  " isn’t here\"), the bar there and no tab lit, and Back to Blooby painted, 44px and landing on Home",
                  not bad_lost and len(lost) == 20, f"wrong: {json.dumps(bad_lost)[:900]}; read {len(lost)}")
            # WHAT IS NOT A PERSON GOING THERE READS WHAT IT READ BEFORE: a script's fetch (it says */* or JSON, never
            # text/html by name) and every other verb get the bare 404, without the page and without its headers.
            # And the route that catches a wrong address takes nothing from a right one: the site's root without its
            # slash still goes to it, and a real page still answers.
            rq21 = wren.ctx.request
            asks21 = {"a fetch": rq21.get(BASE + "/social/no-such-page", max_redirects=0),
                      "a fetch for JSON": rq21.get(BASE + "/social/no-such-page", headers={"Accept": "application/json"}, max_redirects=0),
                      "a POST": rq21.post(BASE + "/social/no-such-page", form={"a": "b"}, headers={"Origin": BASE}, max_redirects=0),
                      "a DELETE": rq21.delete(BASE + "/social/no-such-page", headers={"Origin": BASE}, max_redirects=0),
                      # more than the site reads from a form (64 KiB): a wrong address reads nothing, so it is
                      # still the 404 it was, never "too large"
                      "a POST of 100 KiB": rq21.post(BASE + "/social/no-such-page", data="x" * 102400, max_redirects=0,
                                                     headers={"Origin": BASE, "Content-Type": "text/plain"}),
                      "a sheet that is not there": rq21.get(BASE + "/social/static/no-such.css", headers={"Accept": "text/css,*/*;q=0.1"}, max_redirects=0)}
            # "BEFORE" IS THE APP'S OWN 404, which is what a wrong address under the site was: the same words and the
            # same headers as an address outside the site still gets (all but the date and the length).
            app21 = rq21.get(BASE + "/zz-no-such-surface", max_redirects=0)

            def heads21(r):
                return {k: v for k, v in r.headers.items() if k not in ("date", "set-cookie", "content-length")}
            bare21 = {k: {"status": r.status, "card": "si-card" in r.text(), "nonce": "nonce-" in r.headers.get("content-security-policy", ""),
                          "as the app's": k != "a fetch" or (r.text() == app21.text() and heads21(r) == heads21(app21)),
                          "differs": sorted(h for h in set(heads21(r)) | set(heads21(app21)) if heads21(r).get(h) != heads21(app21).get(h)) if k == "a fetch" else []}
                      for k, r in asks21.items()}
            root21 = rq21.get(BASE + "/social", max_redirects=0)
            real21 = rq21.get(BASE + "/social/explore", headers={"Accept": "text/html"}, max_redirects=0)
            check("...and what is not a person going there reads what it read before: a script's fetch, a fetch for JSON, a"
                  " POST, a DELETE, a POST of 100 KiB and a stylesheet that is not there each get the bare 404, with no"
                  " card and none of the page's headers (a fetch's, word for word and header for header what an address"
                  " outside the site gets); the site's root without its slash still goes to it, and a real page still"
                  " answers",
                  all(v["status"] == 404 and not v["card"] and not v["nonce"] and v["as the app's"] for v in bare21.values())
                  and app21.status == 404 and root21.status in (301, 308) and root21.headers.get("location", "").endswith("/social/")
                  and real21.status == 200 and "si-card" not in real21.text(),
                  f"{json.dumps(bare21)}; the root {root21.status} {root21.headers.get('location')}; a real page {real21.status}")
        except Exception as exc:  # noqa: BLE001
            check("section 21 ran to its end", False, str(exc).splitlines()[0][:200])

    # ------------------------------------------------------------------ 22
    if part(22, "a tile for each drawing: every cell of a grid of tiles on its own flat tile (the owner's yes, Nov 21)"):
        # The owner's picture of the Gallery in dark (Nov 20): a name floats between two pictures, and a drawing on
        # dark paper has no edge on the dark page. So under every ROW one flat band (--row-band; "each row
        # distinct"). Then, Nov 21, of the same Gallery in light: "I like the colors that make rows. Maybe they
        # should be individual tiles, not rows", and yes to the mock's A: THE SAME COLOUR, ONE TILE UNDER EACH
        # DRAWING AND ITS NAME, the page showing between two tiles, across and down; a last row that is not full
        # is its tiles and nothing more. READ OFF THE PAINT (a picture of the screen), since a tile's ground is a
        # part of its cell and has no box of its own to ask. ENAMEL SINCE NOV 26 (the owner's "Yes to B, with
        # their lavender edge", to the Enamel Tiles mock, a friend's colours): the tile white in light and
        # obsidian in dark, flat, its lavender edge drawn inside it (in whole screen pixels and alone since the
        # evening's crisp edge, "All yes on A"); the step from the page still in the band Nov 20 asked for.
        try:
            import io as _io
            from PIL import Image as _Image
            sol = someone(b, "solv", "Sol Vega")
            made22 = [make_post(sol, f"Section 22, tile {i}", gallery=True, seed=220 + i) for i in range(5)]
            ids22 = [j.get("post") for st, j in made22 if st == 200 and isinstance(j, dict)]
            # somebody else, with three drawings shared outside a post: what Make's "Use one you made" lists under
            # Drawings (and somebody to look at Sol's profile, whose grid is then tiles alone, with no eyes)
            tess = someone(b, "tessq", "Tess Quill")
            alone22 = [tess.pg.evaluate(PAD, [f"Section 22, on its own {i}", "public", 226 + i])[0] for i in range(3)]
            # A TILE'S PAINT IS ITS TOKEN'S OWN, within two levels (the picture's rounding). Until the crisp build
            # (section 23) this allowed eleven: a picture's soft shadow lay on the colour beside it, deepest 2px
            # from a picture on a sheet's paper. Nothing soft lies there now.
            SHADE22 = 2
            GRID22 = """([sel, scroll]) => { const g = [...document.querySelectorAll(sel)].find(e => e.getClientRects().length); if (!g) return null;
              if (scroll) window.scrollTo(0, g.getBoundingClientRect().top + scrollY - 90);
              const gr = g.getBoundingClientRect(), rows = {}, cs = getComputedStyle(g);
              [...g.children].forEach(t => { const r = t.getBoundingClientRect(); const k = Math.round(r.top); (rows[k] = rows[k] || []).push([r.left, r.top, r.right, r.bottom]); });
              return { grid: [gr.left, gr.right], vh: innerHeight, gap: parseFloat(cs.columnGap), rowGap: parseFloat(cs.rowGap),
                       out: parseFloat(cs.getPropertyValue('--tile-out')),
                       cols: cs.gridTemplateColumns.split(' ').length, token: getComputedStyle(g.children[0], '::before').backgroundColor,
                       cells: [...new Set([...g.children].map(c => c.className.split(' ')[0]))],
                       rows: Object.keys(rows).map(Number).sort((a, b) => a - b).map(k => rows[k]) }; }"""

            def lum22(c):
                v = [(x / 255 / 12.92) if x / 255 <= 0.03928 else ((x / 255 + 0.055) / 1.055) ** 2.4 for x in c[:3]]
                return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

            def tiles(page_, sel, scroll=True):
                """Every row of the grid that is on the screen, cell by cell: what is painted in the room a tile
                takes round its picture and under its name (the tile), and at its rounded corner, between it and
                the next, under it, beside the grid and where a row that is not full has no cell (the ground).
                EACH POINT IS READ TWICE, as the page paints it and with the tiles' own ground taken away: the
                page is not one flat colour (a glow lies over its top, 10% of the accent fading down: on this
                tall screen it reaches the first row and tints the page there half-way to a tile's colour), so
                "the ground" is what the page paints at that very point, not a colour read somewhere else."""
                # a tall screen of the same width, so every row is on it at once (the layout is the width's)
                page_.set_viewport_size({"width": page_.viewport_size["width"], "height": 1500})
                page_.wait_for_timeout(300)
                page_.evaluate(GRID22, [sel, scroll])
                page_.wait_for_timeout(300)
                g = page_.evaluate(GRID22, [sel, False])
                im = _Image.open(_io.BytesIO(page_.screenshot())).convert("RGB")
                bare = page_.add_style_tag(content=".gal-grid > *::before { display: none !important; }")
                page_.wait_for_timeout(150)
                im0 = _Image.open(_io.BytesIO(page_.screenshot())).convert("RGB")
                bare.evaluate("s => s.remove()")

                def px(x, y):
                    at = (min(max(int(round(x)), 0), im.size[0] - 1), min(max(int(round(y)), 0), im.size[1] - 1))
                    return [im.getpixel(at), im0.getpixel(at)]
                o, rows = g["out"], []

                def lines(x0, y0, dx, dy):
                    """The two screen pixels a line one CSS pixel wide can fall across, from (x0, y0) on (the
                    tile's own edge, at this density): what is painted there."""
                    import math as _m
                    return [im.getpixel((min(max(int(_m.floor(x0)) + k * dx, 0), im.size[0] - 1),
                                         min(max(int(_m.floor(y0)) + k * dy, 0), im.size[1] - 1))) for k in (0, 1)]
                for r in g["rows"]:
                    top, bot = min(t[1] for t in r), max(t[3] for t in r)
                    if top < 75 or bot > g["vh"] - 100:
                        continue
                    mid, tile, ground, edge = (top + bot) / 2, [], [], []
                    l0, t0, r0, b0 = r[0]
                    # ENAMEL: the edge drawn inside the tile, its first screen pixel at the tile's own edge; the
                    # next pixel down from its top and the next up from its foot (the tile runs 8px under the
                    # name), where a line of light and a dark foot were until the crisp edge.
                    lip = lines((l0 + r0) / 2, t0 - o + 1, 0, 1)
                    foot = lines((l0 + r0) / 2, b0 + 8 - 2, 0, 1)
                    for i, (l, t, rt, bt) in enumerate(r):
                        cx = (l + rt) / 2
                        edge.append(lines(l - o, mid, 1, 0))
                        # the tile: beside its picture each way, over it, and under its name
                        tile += [px(l - o / 2, mid), px(rt + o / 2 - 1, mid), px(cx, t - o / 2), px(cx, bt + 5)]
                        # the ground: at the tile's rounded corner, and under it, in the middle of the page's 8px
                        ground += [px(l - o + 1, t - o + 1), px(cx, bt + 8 + 4)]
                        if i + 1 < len(r):                       # between it and the next: the page, where a band ran
                            ground.append(px(rt + o + (r[i + 1][0] - o - rt - o) / 2, mid))
                    ground.append(px(r[0][0] - o - 3, mid))       # beside the grid
                    if len(r) < g["cols"]:                        # a row that is not full: no tile where no cell is
                        w = r[-1][2] - r[-1][0]
                        ground.append(px(r[-1][2] + g["gap"] + w / 2, mid))
                    rows.append({"tiles": len(r), "tile": tile, "ground": ground, "edge": edge, "lip": lip, "foot": foot})
                rgb = tuple(int(float(x)) for x in re.findall(r"[\d.]+", g["token"])[:3])
                # every cell as wide as every other: a lone one in a last row is a tile like the rest, not stretched
                wide = sorted({round(c[2] - c[0], 1) for r in g["rows"] for c in r})
                return {"cols": g["cols"], "token": rgb, "cells": g["cells"], "out": o, "gaps": [g["gap"], g["rowGap"]], "wide": wide, "rows": rows}

            def tiled(v, want_token, want_tiles, want_out):
                """Each cell on a tile of the token's colour, a step from what the page paints at that point
                (about one part in twelve where the page is flat, 1.08 to 1; less under the glow at its top:
                1.03 to 1.13); and nothing of a tile anywhere the ground should be (the two readings alike).
                The room between two pictures is the tile's each side and 8px of the page: 2 x out + 8 across,
                out + 16 down."""
                if not v or v["token"] != want_token or [r["tiles"] for r in v["rows"]] != want_tiles:
                    return False
                if v["out"] != want_out or v["gaps"] != [2 * want_out + 8, want_out + 16] or len(v["wide"]) != 1:
                    return False
                for r in v["rows"]:
                    for c, page_c in r["tile"]:
                        step = (max(lum22(c), lum22(page_c)) + 0.05) / (min(lum22(c), lum22(page_c)) + 0.05)
                        if max(abs(c[i] - want_token[i]) for i in range(3)) > SHADE22 or not 1.03 <= step <= 1.13:
                            return False
                    if any(max(abs(c[i] - page_c[i]) for i in range(3)) > 1 for c, page_c in r["ground"]):
                        return False
                return True

            def near22(cands, want, slack=6):
                """One of the two pixels a line can fall across is the line's colour, as painted."""
                return any(max(abs(c[i] - want[i]) for i in range(3)) <= slack for c in cands)

            def enamel(v, want_edge, bare=None):
                """ENAMEL (the owner's "Yes to B, with their lavender edge", Nov 26): every tile's edge their
                lavender, read where it is painted (each tile's left side). And since that evening's crisp edge
                (the owner's "All yes on A"), the edge alone: the screen pixel under it at the tile's top and over
                it at its foot (a row's first tile) the tile's own colour, where in dark there were a line of light
                and a dark line."""
                if not v or not v["rows"]:
                    return False
                for r in v["rows"]:
                    if not all(near22(e, want_edge) for e in r["edge"]):
                        return False
                    if bare and not (near22(r["lip"][:1], bare) and near22(r["foot"][:1], bare)):
                        return False
                return True

            # The tile's paint: white porcelain in light, obsidian (#171723) in dark; on a sheet's paper the same.
            TILE22 = {"light": (255, 255, 255), "dark": (23, 23, 35)}
            seen22 = {}
            for scheme, tok in (("light", TILE22["light"]), ("dark", TILE22["dark"])):
                ctx, pg = browser_as(b, sol, "phone", scheme)
                pg.goto(BASE + "/social/@solv/gallery")
                pg.wait_for_load_state("load")
                pg.wait_for_timeout(900)
                seen22[scheme] = tiles(pg, "[data-prof-list].gal-grid")
                close_ctx(ctx, pg)
                ctx, pg = browser_as(b, tess, "phone", scheme)
                pg.goto(BASE + "/social/@solv/gallery")
                pg.wait_for_load_state("load")
                pg.wait_for_timeout(900)
                seen22[scheme + ", somebody else's"] = tiles(pg, "[data-prof-list].gal-grid")
                if scheme == "light":
                    # Make's "Use one you made": the same grid on a sheet's paper, its tile the paper's own step.
                    pg.goto(BASE + "/social/")
                    pg.wait_for_load_state("load")
                    pg.click("nav.nav .tab-make")
                    pg.wait_for_timeout(700)
                    pg.click("#composeSheet [data-compose-yours]")
                    pg.wait_for_timeout(600)
                    pg.click('#composeSheet [data-pick="drawings"]')
                    pg.wait_for_selector("#composeSheet .cmp-grid .gal-tile", timeout=15000)
                    pg.wait_for_timeout(900)
                    seen22["picker"] = tiles(pg, "#composeSheet .cmp-grid", scroll=False)
                close_ctx(ctx, pg)
            check("on a phone every drawing of a profile's Gallery is on a tile of its own: 6px of the tile round its"
                  " picture and 8px under its name, the colour its token says (enamel since Nov 26: white in light,"
                  " obsidian in dark, a step of 1.03 to 1.13 from the page), and the page at the tile's rounded corner,"
                  " between two tiles across and down"
                  " (8px), and beside the grid; five drawings are two rows of two and a last row of one, and where that"
                  " row has no second drawing there is the page (it was a band right across) and the lone tile is as wide as"
                  " the others; your own profile's grid"
                  " (each tile in a cell with its eye) and somebody else's view of it (tiles alone) the same",
                  len(ids22) == 5 and all(tiled(seen22.get(k + who), tok, [2, 2, 1], 6) for k, tok in (("light", TILE22["light"]), ("dark", TILE22["dark"]))
                                          for who in ("", ", somebody else's"))
                  and seen22["light"]["cols"] == 2 and seen22["light"]["cells"] == ["gal-cell"]
                  and seen22["light, somebody else's"]["cells"] == ["gal-tile"],
                  json.dumps({k: [v["cells"], v["token"], v["out"], v["gaps"], v["wide"], [r["tiles"] for r in v["rows"]], v["rows"][-1:]] for k, v in seen22.items() if k != "picker"})[:1100])
            check("Make's \"Use one you made\" is the same grid on a sheet's paper: a tile each, the page's own white,"
                  " a step from the paper, 4px round a picture (the room the list leaves, so no tile is cut square by"
                  " it), the paper between two",
                  bool(seen22.get("picker")) and tiled(seen22["picker"], TILE22["light"], [2, 1], 4),
                  f"shared alone {alone22}; " + json.dumps(seen22.get("picker"))[:700])
            # ENAMEL'S LINE, as painted: light, the lavender edge (#dfdcf0); dark, the edge as it looks over the tile
            # (their 10% lavender-white, made solid: #2b2b39). Nothing under it at the top or over it at the foot:
            # the line of light (#3d3d4b) and the dark foot (#08080c) went with the crisp edge (Nov 26, "All yes on A").
            check("every tile wears their lavender edge, drawn inside it, and that alone: #dfdcf0 in light, #2b2b39 in"
                  " dark, read where it is painted, the screen pixel under it at the tile's top and over it at its foot"
                  " the tile's own colour (no line of light, no dark foot), on your own profile, on somebody else's"
                  " view of it and on Make's list",
                  all(enamel(seen22.get("light" + who), (223, 220, 240), TILE22["light"]) for who in ("", ", somebody else's"))
                  and all(enamel(seen22.get("dark" + who), (43, 43, 57), TILE22["dark"]) for who in ("", ", somebody else's"))
                  and enamel(seen22.get("picker"), (223, 220, 240), TILE22["light"]),
                  json.dumps({k: [(r["edge"][:1], r["lip"], r["foot"]) for r in v["rows"][:1]] for k, v in seen22.items()})[:900])
            # THE EDGE IN WHOLE SCREEN PIXELS (the owner's "All yes on A", Nov 26, to the Crisp Tile Edge mock, after
            # "the top edge of the gallery chips does not look good (dark is worse). It's not crisp at all"): at every
            # density the tile's one line is a whole number of the screen's own pixels, as near 1px as it allows (1px
            # at Windows' 150% was a pixel and a half, smeared across two). Asked of the line as the browser resolved
            # it, on a phone's width at each density (the tile's own box-shadow: one layer, its spread).
            dens22 = {}
            for d in (1, 1.25, 1.5, 1.75, 2, 2.625, 3):
                dctx2, dpg2 = browser_as(b, tess, "phone", "dark", scale=d)
                dpg2.goto(BASE + "/social/@solv/gallery")
                dpg2.wait_for_load_state("load")
                dpg2.wait_for_timeout(400)
                dens22[d] = dpg2.evaluate("""() => { const c = document.querySelector('[data-prof-list].gal-grid > *'); if (!c) return null;
                  const sh = getComputedStyle(c, '::before').boxShadow, px = (sh.match(/-?[\\d.]+px/g) || []).map(parseFloat);
                  return { layers: sh.split(/,(?![^(]*\\))/).length, w: px.length >= 4 ? px[3] : null, dpr: devicePixelRatio }; }""")
                close_ctx(dctx2, dpg2)

            def whole22(v):
                return (bool(v) and v["layers"] == 1 and v["w"] is not None and round(v["w"] * v["dpr"]) >= 1
                        and abs(v["w"] * v["dpr"] - round(v["w"] * v["dpr"])) < 0.02 and abs(v["w"] - 1) <= 0.34)
            check("the tile's edge is a whole number of screen pixels at every density, as near 1px as each allows (1, 1.25"
                  " and 1.5x one pixel; 1.75 to 2x two; 2.625 and 3x three), and the tile's one line",
                  len(dens22) == 7 and all(whole22(v) for v in dens22.values()),
                  json.dumps({str(k): v for k, v in dens22.items()}))
            dctx, dpg = browser_as(b, sol, "desk")
            dpg.goto(BASE + "/social/@solv/gallery")
            dpg.wait_for_load_state("load")
            dpg.wait_for_timeout(900)
            d5 = tiles(dpg, "[data-prof-list].gal-grid")
            c22 = sol.client()
            c22.get("/social/")
            gone22 = c22.post_json(f"/social/p/{ids22[0]}/delete", {})[0] if ids22 else None
            dpg.goto(BASE + "/social/@solv/gallery")
            dpg.wait_for_load_state("load")
            dpg.wait_for_timeout(900)
            d4 = tiles(dpg, "[data-prof-list].gal-grid")
            close_ctx(dctx, dpg)
            check("on a desk the grid is three across and the rule the same: five drawings are a row of three and a row"
                  " of two, four are three and one, each on its own tile, and the page where a row has no drawing",
                  gone22 == 200 and tiled(d5, TILE22["light"], [3, 2], 6) and tiled(d4, TILE22["light"], [3, 1], 6)
                  and d5["cols"] == 3 and enamel(d5, (223, 220, 240)),
                  json.dumps({"five": d5, "four": d4})[:900])
            # THE TILE ANSWERS A MOUSE (the owner's "All yes", Nov 26, to the Tile Hover mock: A, without the grow).
            # On a desk, light and dark, the mouse on the second tile: its edge, read where it is painted, is the
            # site's hover line as it lies over the tile (--btn2-line: #d2c7ff in light, #50477b in dark), the tile
            # beside it keeps its lavender, it does not grow and nothing soft appears. A touch phone has no hover:
            # a mouse put on a tile there changes nothing.
            HOVER22 = """(n) => { const g = document.querySelector('[data-prof-list].gal-grid'); const c = g.children[n];
              const r = c.getBoundingClientRect(), pic = c.querySelector('.gal-pic').getBoundingClientRect();
              return { left: r.left, mid: pic.top + pic.height / 2, cx: pic.left + pic.width / 2,
                       out: parseFloat(getComputedStyle(g).getPropertyValue('--tile-out')),
                       transform: getComputedStyle(c).transform, shadow: getComputedStyle(c, '::before').boxShadow }; }"""

            def soft22(v):
                """The layers of a shadow that carry any blur (each layer's third length)."""
                out = []
                for layer in re.split(r",(?![^(]*\))", v or ""):
                    lens = re.findall(r"(-?[\d.]+)px", re.sub(r"(?:rgba?|color)\([^)]*\)", "", layer))
                    if len(lens) >= 3 and float(lens[2]) > 0:
                        out.append(layer.strip())
                return out

            hov22 = {}
            for scheme, shape in (("light", "desk"), ("dark", "desk"), ("light", "phone")):
                hctx, hpg = browser_as(b, tess, shape, scheme)
                hpg.goto(BASE + "/social/@solv/gallery")
                hpg.wait_for_load_state("load")
                hpg.wait_for_timeout(900)
                one, two = hpg.evaluate(HOVER22, 0), hpg.evaluate(HOVER22, 1)
                hpg.mouse.move(two["cx"], two["mid"])
                hpg.wait_for_timeout(500)
                two = hpg.evaluate(HOVER22, 1)
                him = _Image.open(_io.BytesIO(hpg.screenshot())).convert("RGB")

                def at22(x, y):
                    return [him.getpixel((min(max(int(math.floor(x)) + d, 0), him.size[0] - 1), int(y))) for d in (0, 1)]
                hov22[f"{shape}, {scheme}"] = {"hovered": at22(two["left"] - two["out"], two["mid"]),
                                               "beside": at22(one["left"] - one["out"], one["mid"]),
                                               "transform": two["transform"], "soft": soft22(two["shadow"])}
                close_ctx(hctx, hpg)
            HOVER_WANT = {"desk, light": ((210, 199, 255), (223, 220, 240)), "desk, dark": ((80, 71, 123), (43, 43, 57)),
                          "phone, light": ((223, 220, 240), (223, 220, 240))}
            check("on a desk the tile under the mouse takes the site's hover line for its edge (a face tile's and Make's"
                  " door's: #d2c7ff over the tile in light, #50477b in dark), the tile beside it keeps its lavender, the"
                  " tile does not grow and nothing soft appears; on a touch phone a mouse put on a tile changes nothing"
                  " (the owner's \"All yes\" to the Tile Hover mock, Nov 26)",
                  len(hov22) == 3 and all(near22(hov22[k]["hovered"], want) and near22(hov22[k]["beside"], beside)
                                          and hov22[k]["transform"] == "none" and not hov22[k]["soft"]
                                          for k, (want, beside) in HOVER_WANT.items()),
                  json.dumps(hov22)[:900])
        except Exception as exc:  # noqa: BLE001
            check("section 22 ran to its end", False, str(exc).splitlines()[0][:200])

    # ------------------------------------------------------------------ 23
    if part(23, "crisp: three heights, and nothing soft at rest (the owner's \"All yes\" to the crisp mock's B, Nov 20)"):
        # The owner: "I want to minimize shadows to create depth and keep it crisp and luxurious. Shadows seem blurry
        # and kind of muddy the page." B, THREE HEIGHTS: in a card, an edge and nothing else; on the page, the edge
        # and one line of shade under it (1px, no blur); floating, the one true shadow, short and close, and a
        # sheet a line of light along its top. The fill an enamel edge, no glow. "SOFT" here is what the count
        # called soft: a shadow with more than 2.5px of blur. The replay's pen nib keeps its glow (left alone,
        # and said so in the mock).
        try:
            cris = someone(b, "crisv", "Cris Vale")
            odo = someone(b, "odoq", "Odo Quist")
            made23 = [make_post(cris, f"Section 23, post {i}", gallery=True, seed=230 + i) for i in range(3)]
            ids23 = [j.get("post") for st, j in made23 if st == 200 and isinstance(j, dict)]
            oc23 = odo.client()
            oc23.get("/social/")
            said23 = [oc23.post_json(f"/social/p/{ids23[0]}/comments", {"words": "Section 23, a comment"})[0],
                      oc23.post_json(f"/social/p/{ids23[0]}/comments", {"words": "Section 23, drawn", "payload": drawing(seed=239)})[0]]
            # A shadow's layers as the browser resolved them: [{ inset, x, y, blur, spread, a }] (a: its colour's alpha).
            LAYERS23 = """const layers23 = v => { if (!v || v === 'none') return []; const parts = []; let depth = 0, cur = '';
                for (const ch of v) { if (ch === '(') depth++; if (ch === ')') depth--; if (ch === ',' && !depth) { parts.push(cur); cur = ''; } else cur += ch; }
                if (cur.trim()) parts.push(cur);
                return parts.map(p => { const col = (p.match(/(?:rgba?|color)\\([^)]*\\)/) || [''])[0];
                  const nums = (col.match(/-?[\\d.]+(?:e-?\\d+)?/g) || []).map(Number);
                  const a = /^rgba\\(/.test(col) ? nums[3] : /^color\\(/.test(col) ? (col.includes('/') ? nums[nums.length - 1] : 1) : 1;
                  const px = (p.replace(col, '').match(/-?[\\d.]+px/g) || []).map(parseFloat);
                  return { inset: /inset/.test(p), x: px[0] || 0, y: px[1] || 0, blur: px[2] || 0, spread: px[3] || 0, a: a }; }); };"""
            # EVERYTHING PAINTED ON THE SCREEN THAT CASTS SOMETHING SOFT (a box, a text or a drop shadow, an element
            # or its ::before / ::after), and how many of the things that used to are there to be read.
            SOFT23 = """() => { """ + LAYERS23 + """
              const out = [], name = e => e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
              document.querySelectorAll('body *').forEach(e => { const r = e.getBoundingClientRect(); if (!r.width || !r.height) return;
                if (e.closest('[hidden], .skribl-inline-nib')) return;
                const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || +cs.opacity === 0) return;
                if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
                const vals = [cs.boxShadow, cs.textShadow];
                for (const pe of ['::before', '::after']) { const ps = getComputedStyle(e, pe); if (ps.content !== 'none') vals.push(ps.boxShadow); }
                vals.forEach(v => layers23(v).filter(l => l.blur > 2.5 && l.a > 0).forEach(l => out.push(name(e) + ' ' + l.blur + 'px')));
                if (cs.filter && cs.filter.includes('drop-shadow')) out.push(name(e) + ' ' + cs.filter); });
              const n = s => [...document.querySelectorAll(s)].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.bottom > 0 && r.top < innerHeight; }).length;
              return { soft: out, cards: n('.post-card'), plates: n('.skribl-inline'), pills: n('.skribl-inline-play'), tiles: n('.gal-pic'), durs: n('.gal-dur'),
                       eyes: n('.gal-eye-chip'), bubbles: n('.cm-bubble'), panels: n('.panel'), fill: n('.nav .tab-make') }; }"""
            # ONE THING'S SHADOW, as painted: its layers, the ring's aside (0 0 0 and a spread).
            OF23 = """(sel) => { """ + LAYERS23 + """
              const e = [...document.querySelectorAll(sel)].find(x => x.getClientRects().length); if (!e) return null;
              return layers23(getComputedStyle(e).boxShadow).filter(l => l.a > 0).map(l => [l.inset ? 'in' : 'out', l.x, l.y, l.blur, l.spread]); }"""
            # EVERY SHADOW THE SITE'S OWN SHEET DECLARES, whatever state it is for: each rule's box-shadow and
            # text-shadow resolved on a probe in this page's theme, and the ones with a soft layer named.
            SHEET23 = """() => { """ + LAYERS23 + """
              const probe = document.createElement('div'); probe.style.position = 'absolute'; document.body.appendChild(probe);
              const sheet = [...document.styleSheets].find(s => (s.href || '').includes('/social.css')); if (!sheet) return null;
              const root = getComputedStyle(document.documentElement), soft = [], lost = [], seen = { rules: 0, shadows: 0 };
              const read = (prop, v) => { probe.style.setProperty(prop, v);
                const got = getComputedStyle(probe)[prop === 'box-shadow' ? 'boxShadow' : 'textShadow']; probe.style.removeProperty(prop); return got; };
              // A rule's own token (--line on a button, say) is not the probe's: stood in for, a colour first and then a
              // length, so a soft layer cannot hide behind it.
              const resolve = (prop, v) => { let got = read(prop, v); if (got !== 'none' || !v.includes('var(')) return got;
                for (const stand of ['rgb(1, 2, 3)', '1px']) {
                  got = read(prop, v.replace(/var\\((--[\\w-]+)\\)/g, (m, n) => root.getPropertyValue(n).trim() ? m : stand)); if (got !== 'none') return got; }
                return null; };
              const walk = rules => { for (const r of rules) { if (r.cssRules && r.cssRules.length && !r.selectorText) { walk(r.cssRules); continue; }
                if (!r.style) continue; seen.rules++; const who = (r.selectorText || r.keyText || '?').slice(0, 60);
                for (const prop of ['box-shadow', 'text-shadow']) { const v = r.style.getPropertyValue(prop); if (!v || v === 'none') continue; seen.shadows++;
                  const got = resolve(prop, v); if (got === null) { lost.push([who, v.slice(0, 60)]); continue; }
                  const s = layers23(got).filter(l => l.blur > 2.5 && l.a > 0);
                  if (s.length) soft.push([who, s.map(l => [l.y, l.blur, l.spread])]); }
                const f = r.style.getPropertyValue('filter'); if (f && f.includes('drop-shadow')) soft.push([who, f]); } };
              walk(sheet.cssRules); probe.remove();
              return { soft, lost, rules: seen.rules, shadows: seen.shadows }; }"""
            seen23, heights, floats, sheet23 = {}, {}, {}, {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, cris, screen, scheme)
                    for name, path in (("Home", "/social/?show=everyone"), ("a post", f"/social/p/{ids23[0]}"), ("the Gallery", "/social/explore"),
                                       ("your profile", "/social/@crisv/gallery"), ("Settings", "/social/you")):
                        cpg.goto(BASE + path)
                        cpg.wait_for_load_state("load")
                        cpg.wait_for_timeout(900)
                        if name == "a post":         # its comments on the screen, where the bubbles are
                            cpg.evaluate("() => { const c = document.getElementById('comments'); c && c.scrollIntoView({ block: 'center' }); }")
                            cpg.wait_for_timeout(500)
                        seen23[f"{name}, {screen} {scheme}"] = cpg.evaluate(SOFT23)
                        if screen == "phone" and name == "Home":
                            heights[scheme] = {"a card": cpg.evaluate(OF23, ".post-card"), "in a card": cpg.evaluate(OF23, ".post-card .skribl-inline"),
                                               "the fill": cpg.evaluate(OF23, ".nav .tab-make .tab-ic"), "the pill": cpg.evaluate(OF23, ".skribl-inline-play")}
                            sheet23[scheme] = cpg.evaluate(SHEET23)
                        if screen == "phone" and name == "a post":
                            # SINCE THE OWNER'S C (Nov 28) a balloon's line is drawn by hand (comments.js): the balloon
                            # itself casts nothing, and its line is the drawing behind it, nothing round it.
                            heights[scheme].update({"a balloon": cpg.evaluate(OF23, ".cm-bubble"),
                                                    "drawn": cpg.evaluate("""() => { const m = document.querySelector('.cm-main.is-hand'),
                                                        s = m && m.querySelector(':scope > svg.cm-hand'), l = s && s.querySelector('.cm-hand-line');
                                                        return !!l && getComputedStyle(l).strokeWidth === '2px' && getComputedStyle(s).filter === 'none'
                                                          && getComputedStyle(s).boxShadow === 'none'; }"""),
                                                    "in a balloon": cpg.evaluate(OF23, ".cm-bubble .skribl-inline, .cm-main > .cm-art .skribl-inline"),
                                                    "on the page": cpg.evaluate(OF23, ".post-page > .post-art .skribl-inline")})
                        if screen == "phone" and name == "the Gallery":
                            heights[scheme]["a tile"] = cpg.evaluate(OF23, ".gal-pic")
                    if screen == "phone":
                        cpg.goto(BASE + "/social/?show=everyone")
                        cpg.wait_for_load_state("load")
                        cpg.wait_for_timeout(600)
                        cpg.evaluate("() => window.SocialToast && window.SocialToast.rise('Section 23', { plain: true })")
                        cpg.wait_for_timeout(700)
                        floats[scheme] = {"a toast": cpg.evaluate(OF23, ".mu-toast")}
                        cpg.goto(BASE + "/social/?show=everyone")
                        cpg.wait_for_load_state("load")
                        cpg.wait_for_timeout(600)
                        cpg.locator("nav.nav .tab-make").tap()
                        cpg.wait_for_function("() => document.getElementById('composeSheet').classList.contains('is-open')", timeout=8000)
                        cpg.wait_for_timeout(600)
                        floats[scheme]["a sheet"] = cpg.evaluate(OF23, "#composeSheet .make-sheet")
                    close_ctx(cctx, cpg)
            floors = {"Home": {"cards": 1, "plates": 1, "pills": 1}, "a post": {"bubbles": 2, "plates": 1}, "the Gallery": {"tiles": 3, "durs": 3},
                      "your profile": {"tiles": 3, "eyes": 3}, "Settings": {"panels": 2}}
            thin = [k for k, v in seen23.items() if v["fill"] < 1 or any(v[what] < n for what, n in floors[k.split(",")[0]].items())]
            softs = {k: v["soft"][:4] for k, v in seen23.items() if v["soft"]}
            check("AT REST NOTHING ON THE SCREEN CASTS A SOFT SHADOW (over 2.5px of blur; the replay's pen nib aside): Home, a"
                  " post's page at its comments, the Gallery, your own profile's grid and Settings, on a phone and a desk,"
                  " light and dark, each with the things that used to cast one on it (cards, drawings and their play pills,"
                  " bubbles, tiles with their time and eye chips, panels, Make's button)",
                  all(st == 200 for st in said23) and len(seen23) == 20 and not softs and not thin,
                  f"comments {said23}; soft {json.dumps(softs)[:600]}; too little on {thin}; e.g. Home {json.dumps(seen23.get('Home, phone light'))[:260]}")

            def line(l, tone):         # the page's one line under an edge: 1px down, no blur (light), or a line of light inside the top (dark)
                return l == (["out", 0, 1, 0, 0] if tone == "light" else ["in", 0, 1, 0, 0])

            def ring(l):
                return l[0] == "out" and l[1:4] == [0, 0, 0] and l[4] > 0

            def three(tone):
                h = heights.get(tone) or {}
                on_page = [h.get(k) or [] for k in ("a card", "a tile")]
                in_card = [h.get(k) or [] for k in ("in a card", "in a balloon")]
                balloon = h.get("a balloon") or []
                plate = h.get("on the page") or []
                fill = h.get("the fill") or []
                return (all(len(v) == 2 and ring(v[0]) and line(v[1], tone) for v in on_page)
                        and balloon == [] and h.get("drawn") is True
                        and all(len(v) == 1 and ring(v[0]) for v in in_card)
                        and (len(plate) == 2 and ring(plate[0]) and line(plate[1], "light") if tone == "light" else len(plate) == 1 and ring(plate[0]))
                        and len(fill) == 3 and fill[0] == ["in", 0, 1, 0, 0] and fill[1] == ["in", 0, -1, 0, 0] and fill[2] == ["out", 0, 1, 2, 0])
            check("THREE HEIGHTS, read off what is painted: ON THE PAGE (a card, a tile) the edge and one line under it, 1px"
                  " with no blur (in dark a line of light inside the top), and a comment's balloon its drawn line alone"
                  " (no lift: the owner's \"All yes (my row)\", Nov 27; drawn by hand since the owner's C, Nov 28, its"
                  " line the drawing behind it, nothing round it); IN A CARD (the drawing in a post's card,"
                  " in a comment's balloon) the edge alone; the drawing on a post's own page as a card on the page (the"
                  " edge alone in dark); THE FILL enamel: light on its top edge, shade on its foot, 1px/2px under it, no glow",
                  three("light") and three("dark"), json.dumps(heights)[:900])

            def floating(tone):
                f, h = floats.get(tone) or {}, heights.get(tone) or {}
                toast, sheet, pill = f.get("a toast") or [], f.get("a sheet") or [], h.get("the pill") or []
                return (len(toast) == 3 and ring(toast[0]) and line(toast[1], tone) and toast[2] == ["out", 0, 12, 22, -12]
                        and sheet == [["in", 0, 1, 0, 0]]
                        and bool(pill) and max(l[3] for l in pill) <= 2 and any(l[:4] == ["out", 0, 0, 0] and l[4] == 0.5 for l in pill))
            check("WHAT FLOATS: a toast has the one true shadow, short and close (22px of blur pulled in 12px under its"
                  " foot), over its edge and the page's line; a sheet casts nothing and has a line of light along its top;"
                  " the play pill on a drawing has a hairline and 1px/2px (nothing over 2px); light and dark",
                  floating("light") and floating("dark"), json.dumps({"floats": floats, "pill": {k: (v or {}).get("the pill") for k, v in heights.items()}})[:700])
            want_soft = {".mu-toast", ".mn-list"}
            check("AND THE SITE'S SHEET DECLARES NO OTHER SOFT SHADOW, whatever the state: every box-shadow and text-shadow"
                  " in social.css resolved in light and in dark, and the only rules with a soft layer are the two things"
                  " that float (the toast and the list under an @), each the same one shadow",
                  all(v and v["rules"] > 800 and v["shadows"] > 60 and not v["lost"] and {s[0] for s in v["soft"]} == want_soft
                      and all(s[1] == [[12, 22, -12]] for s in v["soft"]) for v in (sheet23.get("light"), sheet23.get("dark"))),
                  json.dumps(sheet23)[:600])
        except Exception as exc:  # noqa: BLE001
            check("section 23 ran to its end", False, str(exc).splitlines()[0][:200])

    if part(24, "Bluesky's columns: on a card everything under the head starts on the name's line, the face in its own column"):
        # BLUESKY'S COLUMNS (the owner, Nov 28, with a Bluesky quote post: "Should we indent also? Like Bluesky?",
        # then to Indent the Quote?'s C: "I like Bluesky columns"). Cora reposts Colm's drawing and quotes it: on
        # her Home the repost is Colm's card under "You reposted" (its words, its drawing, its row), and her quote
        # is her card with Colm's small inside. Each part's left edge read where it is painted: a text's own
        # letters (a Range over them), a box's own edge, the row's first icon; on Colm's post's own page the same.
        try:
            colm = someone(b, "colm", "Colm Ray")
            cora = someone(b, "colfan", "Cora Fan")
            st24, j24 = make_post(colm, "Section 24, a drawing in the column", seed=24, card=True)
            pd24 = j24.get("post") if st24 == 200 and isinstance(j24, dict) else None
            cc = cora.client()
            cc.get(f"/social/p/{pd24}")
            rst24, _ = cc.post_json(f"/social/p/{pd24}/repost", {"reposted": True})
            qst24, qj24 = cc.post_json("/social/posts", {"words": "Section 24, a quote in the column", "quote": pd24})
            qd24 = qj24.get("post") if qst24 == 200 and isinstance(qj24, dict) else None
            fst24, _ = cc.post_json("/social/@colm/follow", {"following": True})    # Home opens on Following
            COLS = r"""(sel) => { const c = document.querySelector(sel); if (!c) return null;
              const ink = e => { if (!e) return null; const r = document.createRange(); r.selectNodeContents(e);
                                 const b = r.getBoundingClientRect(); return b.width ? Math.round(b.left * 100) / 100 : null; };
              const box = e => e ? Math.round(e.getBoundingClientRect().left * 100) / 100 : null;
              const face = c.querySelector(':scope > .post-head .post-face .face-ring'), fr = face ? face.getBoundingClientRect() : null;
              const rpIc = c.querySelector(':scope > .rp-by .ic'), ir = rpIc ? rpIc.getBoundingClientRect() : null;
              const row = c.querySelector(':scope > .post-row'), last = row && [...row.children].filter(e => e.getClientRects().length).pop();
              return { face: fr ? [Math.round(fr.left * 100) / 100, Math.round(fr.right * 100) / 100] : null,
                       faceMid: fr ? Math.round((fr.left + fr.right) * 50) / 100 : null,
                       name: ink(c.querySelector(':scope > .post-head .post-name')),
                       words: ink(c.querySelector(':scope > .post-words')),
                       art: box(c.querySelector(':scope > .post-art')),
                       quote: box(c.querySelector(':scope > .qt-card')),
                       icon: box(c.querySelector(':scope > .post-row svg')),
                       rp: ink(c.querySelector(':scope > .rp-by span')),
                       rpRight: ir ? Math.round(ir.right * 100) / 100 : null,
                       spread: row && last ? Math.round((row.getBoundingClientRect().right - last.getBoundingClientRect().right) * 100) / 100 : null }; }"""
            cols24, page24 = {}, {}
            for screen in ("phone", "desk"):
                ctx, pg = browser_as(b, cora, screen=screen)
                pg.goto(BASE + "/social/")
                pg.wait_for_timeout(900)
                cols24[(screen, "repost")] = pg.evaluate(COLS, f'.post-card[data-post="{pd24}"]')
                cols24[(screen, "quote")] = pg.evaluate(COLS, f'.post-card[data-post="{qd24}"]')
                pg.goto(BASE + f"/social/p/{pd24}")
                pg.wait_for_timeout(900)
                page24[screen] = pg.evaluate(r"""() => { const p = document.querySelector('.post-page'); if (!p) return null;
                  const ink = e => { if (!e) return null; const r = document.createRange(); r.selectNodeContents(e);
                                     const b = r.getBoundingClientRect(); return b.width ? Math.round(b.left * 100) / 100 : null; };
                  const box = e => e ? Math.round(e.getBoundingClientRect().left * 100) / 100 : null;
                  return { face: box(p.querySelector(':scope > .post-head .face-ring')), words: ink(p.querySelector(':scope > .post-words')),
                           art: box(p.querySelector(':scope > .post-art')) }; }""")
                close_ctx(ctx, pg)

            def on_line(v, keys):
                return v and v["name"] is not None and all(v.get(k) is not None and abs(v[k] - v["name"]) <= 1 for k in keys)

            def beyond(v, keys):
                return v and v["face"] and all(v.get(k) is not None and v[k] >= v["face"][1] + 8 for k in keys)
            check("Bluesky's columns (the owner's \"I like Bluesky columns\", Nov 28): on a card the words, the drawing, a"
                  " quote and the row's first icon start where the name does (within a pixel), beyond the face, whose column"
                  " is its own: a drawing's card and a quote's, on a phone and a desk",
                  rst24 == 200 and fst24 == 200 and bool(qd24) and len(cols24) == 4
                  and all(on_line(cols24[(sc, "repost")], ("words", "art", "icon")) and beyond(cols24[(sc, "repost")], ("words", "art"))
                          and on_line(cols24[(sc, "quote")], ("words", "quote", "icon")) and beyond(cols24[(sc, "quote")], ("words", "quote"))
                          for sc in ("phone", "desk")),
                  f"repost {rst24}, quote {qst24}, follow {fst24}; " + json.dumps({" ".join(k): v for k, v in cols24.items()}))
            check("...a reposted line's words start there too, its arrows just before them, 6px from them, as Bluesky's"
                  " (the owner's \"Yes\", Nov 28; within a pixel); and the row spread across the column, its ⋯ at the"
                  " column's end (the same yes)",
                  all(cols24[(sc, k)] and cols24[(sc, "repost")]["rp"] is not None
                      and abs(cols24[(sc, "repost")]["rp"] - cols24[(sc, "repost")]["name"]) <= 1
                      and abs(cols24[(sc, "repost")]["rp"] - cols24[(sc, "repost")]["rpRight"] - 6) <= 1
                      and cols24[(sc, k)]["spread"] is not None and abs(cols24[(sc, k)]["spread"]) <= 0.6
                      for sc in ("phone", "desk") for k in ("repost", "quote")),
                  json.dumps({" ".join(k): v for k, v in cols24.items()}))
            # (On a desk a post's page puts its drawing in a column of its own, at the left: its words are read there.)
            check("...and a post's own page keeps its full width, as Bluesky's does: its words start where its face does,"
                  " on a phone and a desk, and on a phone its drawing too",
                  len(page24) == 2 and all(v and v["face"] is not None and v["words"] is not None
                                           and abs(v["words"] - v["face"]) <= 1 for v in page24.values())
                  and page24["phone"]["art"] is not None and abs(page24["phone"]["art"] - page24["phone"]["face"]) <= 1,
                  json.dumps(page24))
        except Exception as exc:  # noqa: BLE001
            check("section 24 ran to its end", False, str(exc).splitlines()[0][:200])

    if part(8, "no page errors, no console errors, no CSP violations"):
        for who in list(_people.values()):
            ERRS.extend(f"csp: {v}" for v in who.csp())
        check("no page errors, console errors or CSP violations on Home, the composer and its editors, a post's"
              " page and its sheets, through everything above",
              not ERRS, "; ".join(ERRS[:4]))
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
