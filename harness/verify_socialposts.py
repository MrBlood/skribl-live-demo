"""Posts on the Skribl site (phase 1, piece 4; docs/SOCIAL-SITE.md "Built:
piece 4, posts"), through the demo's own server, with Chromium's virtual
authenticator for the site's people and a real pen in Skribl's real Pad.

  1. HOME, SIGNED IN: "Say something, then draw it…", Draw and Flip, Post;
     with nothing drawn, Post says so and sends nothing; an empty feed says
     so kindly. Signed out, Home is the first visit, as before.
  2. COMPOSING: Draw opens Skribl's Pad over Home in compose mode, with the
     gallery choice in its sheet (compose=1&gallery=1); Add hands the drawing
     back into the composer's own in-post player; Edit drawing reopens it
     with the drawing in it; Remove takes it away. Flip opens Flip the same.
  3. POSTING: the words and the drawing, one post: its row on the site's
     chain, its skribl through create_post (unlisted without the tick, its
     title the first words, no caption), and the post's own page, where the
     drawing plays by itself; under Reduce Motion it rests still. With the
     tick, the skribl is public and Skribl's listing shows it. On a desk,
     More from shows each other drawing alone, cut out of its share card.
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
     database itself), nor in the Gallery, while the drawing keeps its own
     page and its maker's; the posts shared the same minute are there; a
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
     Cal's tap map of Home's cards and the first visit's and a profile's
     Skribls cards (Skribl's own Gallery cards; Explore's were too until the
     map's step 3), on a touch phone in light and dark: every 4px one of the
     card's own controls or its ground, and an exact tap on every part of the
     ground opens the card's page (a post's, a drawing's, or Skribl's own
     for one by somebody not on the site); a finger on the drawing plays it,
     on the name opens the person, on the ground opens the page, followed;
     /social/b/<id>'s ways on; the line's own controls; on a desk Ctrl and
     the middle button, a drag, the title a keyboard's link; the ⋯; and
     Skribl's own /gallery as it was.
 13. THE GALLERY OF EVERYONE (Explore; the map's step 3, the Gallery mock's
     B): posts only, every post once, a Flip's too, never a drawing outside
     a post, one kept link-only, a face or one by somebody not on the site;
     its tiles two across on a touch phone and three on a desk, each the
     drawing on its paper in 650 x 486 with "▶ 15 sec" (what the player's
     play button says at rest, without "drawn in"; a Flip its pages), the
     maker's face at 22px and first name, the hearts and comments only when
     there are some; the drawing whole and alone, cut out of its share card;
     a tap anywhere on a tile opens its post (a touch, a click, the keyboard:
     every 4px of it its one link); Following only the people you follow and
     you, Everyone everybody, the pill gliding and the tiles fading, read on
     every frame, the address saying which; Hot plays in the last seven
     days, most first; a search by the words, the name and the @handle;
     Load more, by a cursor that names no internal id; every word at 4.5:1
     (the ▶'s words read off the pixels under them), every control 44px,
     the box 16px: phone and desk, light and dark.

SOCIALPOSTS_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Posts at /social (phase 1, piece 4)",
"Comments on every drawing" for 10 and 11, "Every card opens its post"
for 12, and "Explore becomes the Gallery of everyone" for 13.
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


def browser_as(b, who, screen="phone", scheme="light", reduced=False):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **(PHONE if screen == "phone" else DESK), **kw)
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
              .filter(t => /gallery/i.test(t)) })""")
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
    if part(1, "Home, signed in: the composer, an empty feed said kindly; Post with nothing drawn"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        sent = []
        pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and r.url.endswith("/social/posts") else None)
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        home = pg.evaluate("""() => ({ composer: !!document.querySelector('[data-composer]'),
          placeholder: (document.querySelector('[data-compose-words]') || {}).placeholder,
          chips: [...document.querySelectorAll('[data-compose-open]')].map(c => c.textContent.trim()),
          post: (document.querySelector('[data-compose-post]') || {}).textContent,
          none: (document.querySelector('[data-feed-none]') || {}).textContent || null,
          hello: !!document.querySelector('.hello') })""")
        pg.click("[data-compose-post]")
        pg.wait_for_timeout(300)
        said = pg.evaluate("() => document.querySelector('[data-compose-say]').textContent")
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/")
        npg.wait_for_timeout(400)
        nobody = npg.evaluate("() => ({ hello: !!document.querySelector('.hello'), composer: !!document.querySelector('[data-composer]') })")
        close_ctx(nctx, npg)
        check("Home signed in has the composer: \"Say something, then draw it…\", Draw and Flip, Post; an empty feed"
              " says so kindly; Post with nothing drawn says what is missing and sends nothing; signed out, Home is"
              " the first visit, as before",
              home["composer"] and home["placeholder"] == "Say something, then draw it…"
              and home["chips"] == ["Draw", "Flip"] and home["post"] == "Post"
              and home["none"] == "No posts yet. Yours could be the first: say something, then draw it."
              and not home["hello"] and said == "Draw something first, then Post." and not sent
              and nobody["hello"] and not nobody["composer"],
              f"home {home}; said {said!r}; posted {len(sent)}; signed out {nobody}")

    # ------------------------------------------------------------------ 2
    if part(2, "composing: the Pad over Home, Add hands the drawing back, Edit and Remove; Flip opens Flip"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        pg.click("[data-compose-open=pad]")
        fr = editor_frame(pg, "skribl-pad")
        src = pg.evaluate("() => document.querySelector('#composePad iframe').getAttribute('src')")
        sheet = add_from_pad(pg, fr) if fr else {}
        drafted = pg.evaluate("""() => { const d = document.querySelector('[data-compose-draft]');
          const box = d && d.querySelector('[data-skribl-inline]');
          return { shown: !!d && !d.hidden, attached: !!(box && box._skriblInline),
                   chips: [...document.querySelectorAll('[data-compose-open]')].map(c => c.hidden),
                   overlay: document.getElementById('composePad').hidden,
                   focus: document.activeElement ? document.activeElement.textContent.trim() : null }; }""")
        loads = []
        pg.evaluate("""() => { window.__loads = 0; const f = document.querySelector('#composePad iframe');
          f.contentWindow.addEventListener('message', e => { if (e.data && e.data.type === 'skribl:compose:load') window.__loads++; }); }""")
        pg.click("[data-compose-edit]")
        pg.wait_for_timeout(900)
        reopened = pg.evaluate("() => ({ open: !document.getElementById('composePad').hidden, loads: window.__loads })")
        fr2 = editor_frame(pg, "skribl-pad")
        if fr2:
            fr2.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        pg.click("[data-compose-remove]")
        pg.wait_for_timeout(400)
        removed = pg.evaluate("""() => ({ draft: document.querySelector('[data-compose-draft]').hidden,
          chips: [...document.querySelectorAll('[data-compose-open]')].map(c => c.hidden),
          frame: document.querySelector('#composePad iframe').getAttribute('src') })""")
        check("Draw opens Skribl's Pad over Home in compose mode with the gallery choice (compose=1&gallery=1); its"
              " sheet says Add to post and offers Show in the Skribls gallery; Add hands the drawing back into the"
              " composer's own in-post player, Draw and Flip step aside, and focus lands on Edit drawing",
              bool(fr) and "compose=1" in (src or "") and "gallery=1" in (src or "")
              and sheet.get("label") == "Add to post" and any("Skribls gallery" in t for t in sheet.get("tick", []))
              and drafted["shown"] and drafted["attached"] and drafted["chips"] == [True, True] and drafted["overlay"]
              and drafted["focus"] == "Edit drawing",
              f"src {src}; sheet {sheet}; drafted {drafted}")
        check("Edit drawing reopens the Pad with the drawing put back in it (a load message); Remove takes the"
              " drawing away, Draw and Flip come back, and the frame is let go (about:blank)",
              reopened["open"] and reopened["loads"] >= 1
              and removed["draft"] and removed["chips"] == [False, False] and removed["frame"] == "about:blank",
              f"reopened {reopened}; removed {removed}")
        pg.click("[data-compose-open=flip]")
        ffr = editor_frame(pg, "/flip?")
        fsrc = pg.evaluate("() => document.querySelector('#composeFlip iframe').getAttribute('src')")
        fopen = pg.evaluate("() => !document.getElementById('composeFlip').hidden")
        if ffr:
            ffr.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        check("Flip opens Skribl's Flip over Home the same way (compose=1&gallery=1), and its × puts it away",
              bool(ffr) and fopen and "compose=1" in (fsrc or "") and "gallery=1" in (fsrc or "")
              and pg.evaluate("() => document.getElementById('composeFlip').hidden"),
              f"frame {bool(ffr)}; src {fsrc}; open {fopen}")

    # ------------------------------------------------------------------ 3
    if part(3, "posting: one post, its row and its skribl together; its page plays by itself"):
        mira = someone(b, "mira", "Mira Okafor")
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(500)
        pg.click("[data-compose-open=pad]")
        fr = editor_frame(pg, "skribl-pad")
        if fr:
            add_from_pad(pg, fr)
        pg.fill("[data-compose-words]", "Day 12. The beard took longer than the skull.\nWatch it at 2×.")
        try:
            with pg.expect_navigation(timeout=30000):
                pg.click("[data-compose-post]")
        except Exception as exc:
            ERRS.append(f"post did not go: {str(exc).splitlines()[0][:100]}")
        pg.wait_for_timeout(1500)
        url = pg.evaluate("() => location.pathname")
        pid = url.rsplit("/", 1)[-1]
        row = post_row(pid)
        sk = skribl_row(row[1]) if row else None
        page = pg.evaluate("""() => ({ words: (document.querySelector('.post-words') || {}).textContent,
          meta: (document.querySelector('.post-meta') || {}).textContent,
          comments: (document.getElementById('commentsTitle') || {}).innerText,
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
        check("the post's own page plays its drawing by itself, its words, when and its comments (phase 2:"
              " verify_socialcomments holds them)",
              playing[:1] == ["playing"] and page["words"] == "Day 12. The beard took longer than the skull.\nWatch it at 2×."
              and " at " in (page["meta"] or "")
              and (page["comments"] or "").strip() == "Comments" and page["box"],
              f"players {playing}; page {page}")
        rctx, rpg = browser_as(b, mira, reduced=True)
        rpg.goto(BASE + url)
        rpg.wait_for_timeout(1500)
        still = rpg.evaluate(STATE)
        close_ctx(rctx, rpg)
        st, j = make_post(mira, "For the gallery", gallery=True, seed=3)
        gsk = skribl_row(post_row(j.get("post"))[1]) if st == 200 and isinstance(j, dict) else None
        listed = json.loads(urllib.request.urlopen(BASE + "/api/skribls?limit=50", timeout=20).read().decode())["items"]
        check("under Reduce Motion the post's page leaves the drawing still; with the gallery tick the skribl is"
              " public, keeps its caption, and Skribl's own listing shows it",
              still and still[0] != "playing" and gsk is not None and gsk[0] == "public"
              and gsk[2] == "From the gallery tick"
              and any(i["id"] == post_row(j["post"])[1] for i in listed),
              f"reduced {still}; gallery skribl {gsk}; status {st}")

        # MORE FROM, ON A DESK: each tile the drawing alone, whole, cut out of
        # its share card, read off the paint (the card's own colours: share_card).
        tiles, tall, wide = [], (531, 944), (816, 612)
        for words, size in (("Card, tall", tall), ("Card, wide", wide)):
            make_post(mira, words, seed=7, size=size, card=True)
        dctx, dpg = browser_as(b, mira, "desk", "light")
        dpg.goto(BASE + url)
        try:
            dpg.wait_for_function("""() => [...document.querySelectorAll('.more-plate img')].length >= 2 &&
              [...document.querySelectorAll('.more-plate img')].every(i => i.complete && i.naturalWidth > 0)""", timeout=15000)
            dpg.evaluate("() => Promise.all([...document.querySelectorAll('.more-plate img')].map(i => i.decode().catch(() => null)))")
        except Exception as exc:
            tiles.append({"stopped": str(exc).splitlines()[0][:100]})
        dpg.wait_for_timeout(300)
        for words, size in (("Card, tall", tall), ("Card, wide", wide)):
            tile = dpg.locator(".more-tile", has_text=words)
            box = dpg.evaluate("""(words) => { const t = [...document.querySelectorAll('.more-tile')].find(e => e.textContent.includes(words));
              const pl = t && t.querySelector('.more-plate'), i = pl && pl.querySelector('img');
              if (!i) return null; const p = pl.getBoundingClientRect(), r = i.getBoundingClientRect();
              const k = r.width / 1200;   // CSS pixels to one card pixel
              return { at: [(p.left - r.left) / k, (p.top - r.top) / k, p.width / k, p.height / k] }; }""", words)
            png = tile.locator(".more-pic").screenshot(timeout=5000) if tile.count() and Image else None
            card, marks = None, None
            if png:
                im = Image.open(io.BytesIO(png)).convert("RGB")
                W, H = im.size
                near = lambda c, t: abs(c[0] - t[0]) + abs(c[1] - t[1]) + abs(c[2] - t[2]) < 120
                card, marks = 0, [0, 0, 0, 0]
                for n, c in enumerate(im.getdata()):
                    if near(c, CARD_GROUND) or near(c, CARD_FOOT) or near(c, CARD_LINE):
                        card += 1
                    elif near(c, CARD_MARK):
                        marks[(2 if n // W >= H / 2 else 0) + (1 if n % W >= W / 2 else 0)] += 1
            x, y, dw, dh = plate_of(*size)
            want = [x + 3, y + 3, dw - 6, dh - 6]
            tiles.append({"words": words, "card": card, "marks": marks, "want": want,
                          "at": [round(v, 1) for v in box["at"]] if box else None})
        close_ctx(dctx, dpg)
        check("on a desk, More from shows each of the author's other drawings whole and alone, cut out of its share"
              " card: none of the card's own ground, wordmark strip or plate line painted, the drawing's four"
              " corners painted, its plate 3 card pixels in from the line, a tall drawing and a wide one",
              len(tiles) == 2 and all(t.get("card") == 0 and t.get("marks") and min(t["marks"]) >= 20
                                      and t.get("at") and all(abs(a - w) <= 1.0 for a, w in zip(t["at"], t["want"]))
                                      for t in tiles),
              f"{tiles}")

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
        check("your own post's ⋯ says Copy link, Share…, Delete post; Copy link gives the link (or says it to copy"
              " by hand); somebody else's says Copy link, Share…, Mute @them (mutes), Report this post",
              mine == ["Copy link", "Share…", "Delete post"]
              and theirs == ["Copy link", "Share…", "Mute @mira", "Report this post", "Block @mira"]
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
            "no drawing": c.post_json("/social/posts", {"words": "only words"})[1],
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
              " hidden character, or with no drawing (400, each its own words), and nothing is posted; a post's body"
              " may be far past the site's 64 KiB; somebody else's post is not theirs to delete (404) and stays",
              answers["no token"] == 403 and answers["signed out"] == 401
              and isinstance(answers["too many words"], dict) and answers["too many words"].get("error") == "words_long"
              and isinstance(answers["hidden character"], dict) and answers["hidden character"].get("error") == "words_chars"
              and isinstance(answers["no drawing"], dict) and answers["no drawing"].get("error") == "no_drawing"
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
        FLOOR = {"home": 6, "post": 10, "menu": 4, "report": 8}
        check("every word on Home's composer and feed, a post's page, its ⋯ and Report reads at 4.5:1 or more on"
              " what is painted behind it, every control is 44px or more each way, every text field 16px: phone and"
              " desk, light and dark",
              all(v["read"] >= FLOOR[k[2]] for k, v in seen.items()) and not low and not small and not fields,
              f"{reads} read, the lowest {lowest}; under 4.5: {low[:4]}; small: {small[:4]}; fields: {fields[:3]};"
              f" each {[(' '.join(k), v['read']) for k, v in seen.items()]}")

    # ------------------------------------------------------------------ 9
    # HOME SHOWS POSTS ONLY (the map's step 3, its second part; the owner's
    # decision 2, Nov 13: "Drawings already shared without a post stay in their
    # author's Gallery, so nothing is lost: the Gallery shows them, and Home
    # shows posts from then on"). Until then Home held every drawing the site's
    # people showed in the gallery, posts or not; these rows held that, and
    # now hold its opposite, and what was kept: the drawing's own page, its
    # maker's page, More from, its ⋯ and its Delete.
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
        # Juno shares twenty-four posts, a drawing shown from the Pad after every
        # second one (no post), so every walk below crosses a page of Home's
        # twenty, even with this section alone.
        made, drawn = [], []
        for i in range(24):
            st, j = make_post(juno, f"Interleave post {i:02d}", seed=100 + i)
            made.append(j.get("post") if isinstance(j, dict) else None)
            time.sleep(0.02)
            if i % 2:
                st, sid = pad(juno.pg, f"Interleave drawing {i // 2:02d}", "public", 100 + i)
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

        # ...AND NOTHING IS LOST: not in the Gallery of everyone either (posts
        # only, section 13), while it keeps its own page and its maker's page
        # (her Skribls: Skribl's own Gallery section, which its script fills).
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
                cpg.goto(BASE + "/social/@noor")
                cpg.wait_for_function("(s) => !!document.querySelector(s)", arg=f'#skriblGallery .tile[data-id="{lone}"]',
                                      timeout=12000)
                listed9[name] = True
            except Exception:  # noqa: BLE001 -- not listed is the row's red
                listed9[name] = False
            close_ctx(ctx, cpg)
        in_gal = [k for k, h in gal9.items() if f"/s/{lone}/poster" in h]
        post_there = [k for k, h in gal9.items() if f'href="/social/p/{p_after}"' in h]
        check("...nor in the Gallery of everyone (signed out, and a follower's Everyone and Following), where the post"
              " after it is; and nothing is lost: it keeps its own page (/social/b/<id>), signed in and out, and its"
              " maker's page lists it among her Skribls, signed in and out",
              made9 and not in_gal and len(post_there) == 3
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

        # LOAD MORE, POSTS ALONE: Juno's twenty-four posts, a drawing shown from
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
              f"Juno's {[x for x in got if x in made][:3]} want {want[:3]}; {len(got)} cards, {len(set(got))} different;"
              f" drawings among them {len({c['skribl'] for c in allc} & set(drawn))}")

        # A drawing's own page, its ⋯, and its Delete; and another of hers from
        # the Pad, untitled, for More from (one person's: posts and drawings).
        st_a, another = pad(mira.pg, "", "public", 5)
        jp = juno.pg
        jp.goto(BASE + f"/social/b/{shown}")
        jp.wait_for_timeout(1500)
        page = jp.evaluate("""() => ({ at: location.pathname, kind: document.querySelector('.post-page').getAttribute('data-kind'),
          words: (document.querySelector('.post-page .post-words') || {}).textContent || '',
          more: [...document.querySelectorAll('.more-tile')].map(e => [e.getAttribute('href'), e.querySelector('.more-words').textContent]) })""")
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
        check("a drawing's own page plays it by itself, its title for its words, with More from its author's"
              " posts and drawings (one untitled, said as a drawing); its ⋯ says Report to anybody else and Delete"
              " post to its author, asked once in the drawing's own words (it goes from her page too: Home never had"
              " it), and then it is gone (Home says so); a post's drawing's page is the post's",
              page["at"] == f"/social/b/{shown}" and page["kind"] == "s"
              and page["words"].strip() == "Section 9, shown from the Pad"
              and playing[:1] == ["playing"]
              and [f"/social/b/{another}", "A drawing"] in page["more"]
              and [f"/social/p/{g_post}", "Section 9, a post shown in the gallery"] in page["more"]
              and theirs == ["Copy link", "Share…", "Mute @mira", "Report this post", "Block @mira"]
              and landed == f"/social/p/{g_post}"
              and mine == ["Copy link", "Share…", "Delete post"] and ask.get("open") and "stopped" not in ask
              and ask.get("lede") == ["The drawing goes for good, from your page too. This can’t be undone."]
              and after["url"] == "/social/?note=deleted_drawing" and after["note"] == "Your drawing is gone." and gone,
              f"page {page}; players {playing}; theirs {theirs}; a post's drawing lands {landed}; mine {mine};"
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
        pages = {k: mc.get(f"/social/b/{v}")[0] for k, v in (("unlisted", kept), ("nobody's", nobodys), ("none", "nope0000000"))}
        # One by somebody not on the site has no page here, so since every card
        # opens /social/b/<id> (section 12) it goes on to Skribl's own (a 302).
        check("a drawing's Delete needs the page's token (403), is its author's alone (somebody else's: 404, the"
              " drawing kept), and never takes a post's drawing without the post (404); a drawing's page is a kind"
              " 404 for one kept unlisted and none, and one by somebody not on the site goes on to Skribl's own page",
              no_token == 403 and not_mine == 404 and skribl_row(sid_k) is not None
              and a_posts == 404 and skribl_row(g_skribl) is not None and post_row(g_post) is not None
              and pages == {"unlisted": 404, "nobody's": 302, "none": 404},
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
            ways = {"when": w["when"]} if key == bare else {"when": w["when"], "words": w["words"]}
            for name, x in ways.items():
                # A CARD WITH NO WORDS: the drawing lies over the time's last
                # pixels and keeps its taps there (the drawing never opens the
                # post); the time's middle and top corners are its own.
                ok_at = (x or {}).get("at") == (["self"] * 3 + ["drawing"] * 2 if key == bare else ["self"] * 5)
                if not (x and x["w"] >= 44 and x["h"] >= 44 and ok_at and x["tag"] == "a" and x["href"] == want_page[key]):
                    bad_open.append(f"{tag} {name}: {x}")
            if key == bare and w["words"] is not None:
                bad_open.append(f"{tag}: words where there are none {w['words']}")
            person = f"/social/@{'juno'}"
            for name in ("name", "face"):
                if not (big(w[name]) and w[name]["href"] == person):
                    bad_person.append(f"{tag} {name}: {w[name]}")
            if w["handle"] != person:
                bad_person.append(f"{tag} @handle lands on {w['handle']}")
            n = w["count"]
            want_label, want_text = ("1 comment", "1") if key == worded else ("Comment", "")
            if not (big(n) and n["href"] == want_page[key] + "#comments" and n["icon"] and n["label"] == want_label
                    and n["text"] == want_text):
                bad_count.append(f"{tag}: {n}")
            if not (w["sameLine"] and w["headH"] == 44 and (w["wordsGap"] is None or abs(w["wordsGap"] - 12) <= 0.5)
                    and abs(w["artGap"] - 12) <= 0.5):
                bad_still.append(f"{tag}: on the @handle's line {w['sameLine']}, the header {w['headH']}px, words"
                                 f" {w['wordsGap']}, drawing {w['artGap']}")
        made = bool(worded and bare and shown and st_s == 201 and commented == 200)
        check("a card's words and its time each open its post's page, each a link a tap lands on anywhere in its 44px"
              " or more (on a card with no words, the time's down to the drawing, which keeps its own taps): a post"
              " with words and one without, phone and desk, light and dark; a drawing shown outside a post has no"
              " card there (Home shows posts only)",
              made and len(seen) == 12 and not bad_open and not drawn_cards,
              f"made {made}; {len(seen)} read; {bad_open[:4]}; the drawing's card on Home {drawn_cards}")
        check("the face, the name and the @handle still open the person's page: the name's link 44px, painted under the"
              " @handle too, so a tap on the @handle lands on it",
              made and not bad_person, f"{bad_person[:4]}")
        check("the 💬 shows even at none: its icon alone, named \"Comment\", a way to the comments (#comments) a tap lands"
              " on, 44px; with one, its number, \"1 comment\"",
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
        SPOT = """([key, what]) => {
          const c = document.querySelector('.post-card[data-post="' + key + '"]'); if (!c) return null;
          c.scrollIntoView({ block: 'center' });
          const R = s => c.querySelector(s).getBoundingClientRect(), mid = r => [r.left + r.width / 2, r.top + r.height / 2];
          const text = (root, needle) => { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            for (let n = w.nextNode(); n; n = w.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
              const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g.getBoundingClientRect(); } }
            return null; };
          let xy;
          if (what === 'ground') { const f = R('.post-row'), n = R('.post-row .post-more'), s = R('.post-open');
            xy = [(n.right + s.left) / 2, f.top + f.height / 2]; }
          else if (what === 'words') xy = mid(text(c.querySelector('.post-words'), 'a card'));
          else if (what === 'drawing') xy = mid(R('.post-art .skribl-inline'));
          else if (what === 'under the time') { const t = R('.post-when'), a = R('.post-art .skribl-inline');
            xy = [t.left + t.width / 2, a.top + 4]; }
          else if (what === 'name') xy = mid(text(c.querySelector('.post-head'), c.querySelector('.post-name').textContent));
          else if (what === 'handle') xy = mid(text(c.querySelector('.post-head'), '@' + c.dataset.handle));
          else xy = mid(R({ face: '.post-face', more: '.post-more', share: '.post-share', count: '.post-count',
                            open: '.post-open' }[what]));
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
                for what in ("ground", "words", "count", "open"):
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
                for what in ("face", "name", "handle"):
                    home()
                    on = press(card, what)
                    r[what] = (on, landed())
                home()
                press(card, "more")
                try:
                    cpg.wait_for_function("() => document.getElementById('postSheet').classList.contains('is-open')", timeout=5000)
                except Exception:  # noqa: BLE001 -- not opening is the row's red
                    pass
                r["more"] = (cpg.evaluate("() => document.getElementById('postSheet').classList.contains('is-open')"),
                             landed(1500))
                home()
                press(card, "share")
                cpg.wait_for_timeout(600)
                r["share"] = (cpg.evaluate("() => window.__shared || null"), landed(1500))
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
                      and r.get("count", (None, None))[1] == page + "#comments"
                      and r.get("open") == ("post-open", page) for r in res.values())
        check("a tap anywhere on a card's own ground (here in the row, between the ⋯ and Open ›, where no finger is"
              " snapped to a button) opens its page, as"
              " a tap on its words does and Open › at the row's end; the 💬 opens it at its comments: a touch on a"
              " phone, a click on a desk",
              bool(card) and ok_open,
              f"{ {s: {k: r.get(k) for k in ('ground', 'words', 'count', 'open', 'stopped')} for s, r in res.items()} }")
        want_drawing = (("drawing", "playing", "/social/"), ("drawing", "paused", "/social/"))
        check("a tap on the drawing plays it and a second pauses it, and the page stays, even at its top edge under the"
              " time on a card with no words: the drawing never opens the post; phone and desk",
              bool(bare_sid) and all(r.get("drawing") == want_drawing for r in res.values()),
              f"{ {s: r.get('drawing') for s, r in res.items()} }")
        check("a tap on the face, the name or the @handle opens the person's page, never the post: phone and desk",
              all(r.get(k, (None, None))[1] == people for r in res.values() for k in ("face", "name", "handle")),
              f"{ {s: {k: r.get(k) for k in ('face', 'name', 'handle')} for s, r in res.items()} }")
        check("⋯ and Share do their own job and the page stays: ⋯ opens its sheet, Share the device's share sheet with"
              " the post's link: phone and desk",
              all(r.get("more") == (True, "/social/") and r.get("share") == (BASE + page, "/social/") for r in res.values()),
              f"{ {s: {k: r.get(k) for k in ('more', 'share')} for s, r in res.items()} }")
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
    # posts only), and the first visit's and a profile's Skribls, which are
    # Skribl's own Gallery cards
    # opening where the site says (skribl.set_card_url, app.py), with on the
    # first visit one by somebody not on the site. (Explore's were Skribl's
    # cards too until the map's step 3; the Gallery of everyone's tiles are
    # one link each, section 13.) Cal's tap map as rows: every 4px of each card,
    # light and dark, on a touch phone (TAPMAP); an EXACT tap on every part of
    # its ground, followed to where it lands (exact: a phone's own targeting
    # moves a tap that lands near a control onto it, which is the phone's
    # doing, not the page's); and a finger's tap on the drawing, the name and
    # the ground. Then /social/b/<id>'s three ways on, the line's controls, and
    # on a desk Ctrl, the middle button, a drag, a keyboard and the ⋯.
    if part(12, "every card opens its post: the tap map of Home's, the first visit's and a profile's cards"):
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
        # Each card as somebody meets it: signed in (Mira) on Home and a
        # profile; signed out on the first visit, the one page of the site
        # whose Gallery holds everybody's, the site's people's and not. The
        # drawing on its own is on the first visit and the profile: Home shows
        # posts only (section 9).
        CARDS = [("Home", "/social/", f'.post-card[data-post="{g_post}"]', g_sid, to_post, mira),
                 ("Home", "/social/", f'.post-card[data-post="{f_post}"]', f_sid, to_flip, mira),
                 ("the first visit", "/social/", TILE.format(g_sid), g_sid, to_post, None),
                 ("the first visit", "/social/", TILE.format(f_sid), f_sid, to_flip, None),
                 ("the first visit", "/social/", TILE.format(lone), lone, to_lone, None),
                 ("the first visit", "/social/", TILE.format(nobodys), nobodys, to_skribl, None),
                 ("a profile", "/social/@juno", TILE.format(g_sid), g_sid, to_post, mira),
                 ("a profile", "/social/@juno", TILE.format(lone), lone, to_lone, mira)]
        # Where a finger goes on a card: the drawing's middle, the name's, and
        # the ground's: on Home's calm card the row's open space between the ⋯
        # and Open › (its line waits until played, Nov 13), a Gallery card's
        # time; scrolled to the screen's middle first.
        SPOT12 = """([sel, what]) => { const c = document.querySelector(sel); if (!c) return null;
          const text = (root, needle) => { if (!root) return null; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            for (let n = w.nextNode(); n; n = w.nextNode()) { const i = n.textContent.indexOf(needle); if (i >= 0) {
              const g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + needle.length); return g; } }
            return null; };
          const at = { drawing: () => c.querySelector('.skribl-inline'),
                       name: () => { const e = c.querySelector('.post-name, .tdn'); return e && text(e, e.textContent.trim()); },
                       ground: () => { const m = c.querySelector('.post-row .post-more'), o = c.querySelector('.post-row .post-open');
                         if (m && o) return { getBoundingClientRect: () => { const a = m.getBoundingClientRect(), z = o.getBoundingClientRect();
                           return { left: a.right, top: a.top, width: z.left - a.right, height: a.height }; } };
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
        check("THE TAP MAP: on Home's cards (a post's drawing and a Flip's) and the first visit's and a profile's Skribls"
              " cards (those, one on its own, and on the first visit one by somebody not on the site), a touch phone in light and dark, every 4px is one of"
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
              " page for it (/s/…); on Home in the row between the ⋯ and Open ›, on a Gallery card at its time",
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
              " of them opens nothing and leaves them open) and takes one (2×), the loop stops repeating, and the page"
              " stays",
              made and line.get("chips") == "true" and line.get("between") == (True, "/social/", "true")
              and line.get("speed", "").startswith("2") and line.get("loop") == "false"
              and line.get("at") == "/social/", f"{line}")

        # ON A DESK: Ctrl (as ⌘ is on a Mac) and the middle button open the card
        # in a new tab and leave this page be; a drag that selects a card's words
        # opens nothing, nor does one across its ground; the title is the card's
        # link for a keyboard (Tab from ⋯ reaches it, Enter opens it).
        ctx, cpg = browser_as(b, mira, "desk", "light")
        desk = {}

        def newtab(press_):
            try:
                with ctx.expect_page(timeout=5000) as info:
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
            for name_, path, sel in (("home", "/social/", hsel), ("profile", "/social/@juno", esel)):
                ready(cpg, path, sel)
                xy = cpg.evaluate(SPOT12, [sel, "ground"])

                def ctrl_click():
                    cpg.keyboard.down("Control")
                    cpg.mouse.click(*xy)
                    cpg.keyboard.up("Control")
                desk[name_ + " ctrl"] = (newtab(ctrl_click), follow(cpg, path, 600))
                ready(cpg, path, sel)
                xy = cpg.evaluate(SPOT12, [sel, "ground"])
                desk[name_ + " middle"] = (newtab(lambda: cpg.mouse.click(*xy, button="middle")), follow(cpg, path, 600))
            # A drag that selects a Gallery card's caption, and one across its ground.
            csel = TILE.format(g_sid)
            ready(cpg, "/social/@juno", csel)
            ends = cpg.evaluate("""(s) => { const c = document.querySelector(s); const w = c.querySelector('.tcap'), n = w.firstChild;
              w.scrollIntoView({ block: 'center' }); const g = document.createRange(); g.setStart(n, 0); g.setEnd(n, 1);
              const a = g.getBoundingClientRect(); g.setStart(n, n.length - 1); g.setEnd(n, n.length); const z = g.getBoundingClientRect();
              return [a.left + 1, a.top + a.height / 2, z.right - 1, z.top + z.height / 2]; }""", csel)
            cpg.mouse.move(ends[0], ends[1])
            cpg.mouse.down()
            cpg.mouse.move(ends[2], ends[3], steps=12)
            cpg.mouse.up()
            cpg.wait_for_timeout(300)
            desk["select"] = (cpg.evaluate("() => String(getSelection())"), follow(cpg, "/social/@juno", 1500))
            ready(cpg, "/social/@juno", csel)
            g0 = cpg.evaluate(SPOT12, [csel, "ground"])
            cpg.mouse.move(g0[0], g0[1])
            cpg.mouse.down()
            cpg.mouse.move(g0[0] - 40, g0[1] + 2, steps=8)
            cpg.mouse.up()
            desk["drag"] = follow(cpg, "/social/@juno", 1500)
            # The keyboard: from the card's ⋯, Tab reaches its title, a link, and Enter opens it.
            ready(cpg, "/social/@juno", esel)
            cpg.evaluate("(s) => document.querySelector(s + ' .tileMore').focus()", esel)
            cpg.keyboard.press("Tab")
            desk["tab"] = cpg.evaluate("""(s) => { const a = document.activeElement, c = document.querySelector(s);
              return a && c.contains(a) ? [a.tagName.toLowerCase(), a.className, a.getAttribute('href'), a.textContent.trim()] : null; }""", esel)
            cpg.keyboard.press("Enter")
            desk["enter"] = follow(cpg, "/social/@juno")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is its rows' red
            desk["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        check("on a desk, Ctrl or the middle button opens the card in a new tab and this page stays: Home's card (in"
              " its row, between the ⋯ and Open ›) and a Gallery card of Skribl's (a profile's Skribls, at its time)",
              made and all(desk.get(k) == (w, p_) for k, w, p_ in (("home ctrl", to_post, "/social/"),
                                                                  ("home middle", to_post, "/social/"),
                                                                  ("profile ctrl", to_lone, "/social/@juno"),
                                                                  ("profile middle", to_lone, "/social/@juno"))),
              f"{ {k: desk.get(k) for k in ('home ctrl', 'home middle', 'profile ctrl', 'profile middle', 'stopped')} }")
        check("...pressing on a Gallery card's caption and pulling selects its words and opens nothing, and a drag"
              " across its ground opens nothing: a drag is not a tap",
              made and (desk.get("select") or ("", ""))[0].strip() == "From the gallery tick"
              and (desk.get("select") or ("", ""))[1] == "/social/@juno" and desk.get("drag") == "/social/@juno",
              f"select {desk.get('select')}; drag {desk.get('drag')}")
        check("...and for a keyboard the card's title is its link: Tab from its ⋯ reaches it, and Enter opens the"
              " card's page",
              made and (desk.get("tab") or [None])[0] == "a"
              and urllib.parse.urlsplit((desk.get("tab") or [None, None, ""])[2] or "").path == to_lone
              and desk.get("enter") == to_lone, f"tab {desk.get('tab')}; enter {desk.get('enter')}")

        # ⋯ ON A GALLERY CARD (Skribl's, on a profile's Skribls): Open goes to the
        # card's page, in this tab as a tap does, and Copy link and Share… give
        # its address.
        ctx, cpg = browser_as(b, mira, "phone", "light")
        ctx.add_init_script("Object.defineProperty(navigator, 'share', { configurable: true,"
                            " value: d => { window.__shared = d && d.url; return Promise.resolve(); } });")
        menu12 = {}
        try:
            for act in ("Copy link", "Share", "Open"):
                ready(cpg, "/social/@juno", TILE.format(g_sid))
                cpg.evaluate("() => { if (window.SkriblPostedUI) SkriblPostedUI.copyText = t => { window.__copied = t;"
                             " return Promise.resolve(true); }; }")
                cpg.locator(TILE.format(g_sid) + " .tileMore").tap()
                cpg.locator(f'.cardMenu .cmItem:has-text("{act}")').tap()
                if act == "Open":
                    menu12[act] = follow(cpg, "/social/@juno")
                else:
                    cpg.wait_for_timeout(400)
                    menu12[act] = cpg.evaluate("() => window.__copied || window.__shared || null")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            menu12["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, cpg)
        check("a Gallery card's ⋯ on the site: Open goes to the card's page in this tab (followed, a post's drawing its"
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
            own["open"] = (newtab(lambda: cpg.locator('.cardMenu .cmItem:has-text("Open")').tap()), follow(cpg, "/gallery", 600))
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
    # Everyone on top (Home's own pill), New, Hot and a search under it.
    # Quin looks (following Gwen alone, muting and blocking nobody); Gwen,
    # Hugo and Ivy share. Every post here says one word nothing else in the
    # suite says (G13), so a search on it is this section's own posts
    # whatever the sections before it made; Everyone and Load more are read
    # against the database itself.
    if part(13, "the Gallery of everyone: posts as drawings, two across and three, a tap opens its post"):
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
        fill = [share(ivy, f"{G13} filler {i:02d}", timed(2000 + i, 10 + i)) for i in range(24)]
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
        # not on the site. None of them is ever a tile.
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
        for key, n in (("a", 3), ("b", 2), ("c", 1)):
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

        def walk(cl, show="everyone", sort="new", q=""):
            """The Gallery walked to its end with Load more: (posts, their drawings' skribls, page sizes, cursors)."""
            qs = "&".join(x for x in (f"show={show}", f"sort={sort}", "q=" + urllib.parse.quote(q) if q else "") if x)
            posts, sids, sizes, cursors = [], [], [], []
            st_, j = getj(cl, "/social/explore/more?" + qs)
            while isinstance(j, dict):
                got = re.findall(r'<a class="gal-tile" href="/social/p/([^"]+)"', j.get("html", ""))
                posts += got
                sids += re.findall(r'class="gal-plate"[^>]*><img src="[^"]*/s/([A-Za-z0-9_-]+)/poster"', j.get("html", ""))
                sizes.append(len(got))
                if not j.get("next") or len(sizes) > 40:
                    break
                cursors.append(j["next"])
                st_, j = getj(cl, "/social/explore/more?" + qs + "&before=" + urllib.parse.quote(j["next"]))
            return posts, sids, sizes, cursors

        oracle = [r[0] for r in db(
            "select p.public_id from social_posts p join social_people pe on pe.id = p.person_id"
            " join skribl_posts s on s.public_id = p.skribl_id where p.taken_down_at is null and pe.taken_down_at is null"
            " and s.visibility in ('public', 'unlisted') order by p.created_at desc, p.public_id desc")]
        anon = Client()
        anon.get("/social/explore")
        q_cl = quin.client()
        q_cl.get("/social/explore")
        a_posts, a_sids, a_sizes, a_curs = walk(anon)
        q_posts, q_sids, q_sizes, q_curs = walk(q_cl)
        not_posts = {lone13, kept13, face13, nobody13}
        mine13 = [p_g2, p_q, p_c, p_b, p_flip, p_a] + fill[::-1]
        check("THE GALLERY IS POSTS ONLY: walked to its end (signed out, and signed in) it is every post, once each,"
              " newest first, a Flip's too, read against the database itself; never a drawing shown outside a post,"
              " one kept link-only, a face, or one by somebody not on the site",
              made13 and bool(lone13 and kept13 and face13 and nobody13) and a_posts == oracle and q_posts == oracle
              and all(m in oracle for m in mine13) and [x for x in oracle if x in mine13] == mine13
              and not (not_posts & set(a_sids)) and not (not_posts & set(q_sids))
              and len(a_sids) == len(a_posts) and set(a_sids) >= {sid.get("a"), sid.get("flip"), sid.get("b")},
              f"made {made13}; signed out {len(a_posts)} of {len(oracle)} (same {a_posts == oracle}), signed in"
              f" {len(q_posts)} (same {q_posts == oracle}); not posts among them"
              f" {sorted(x for x in not_posts & (set(a_sids) | set(q_sids)) if x)}")
        new_cur = re.compile(r"\d{16}\.p[A-Za-z0-9_-]{11}")

        def raw_of(cur, hot=False):
            try:
                body = cur[2:] if hot else cur
                return base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
            except Exception:  # noqa: BLE001 -- unreadable is the row's red
                return ""
        check("Load more walks it a page of 24 at a time, every page whole but the last, by a cursor that names a"
              " time and a post's public id, never an internal id",
              len(a_sizes) >= 2 and all(n == 24 for n in a_sizes[:-1]) and 0 < a_sizes[-1] <= 24
              and all(new_cur.fullmatch(raw_of(c)) for c in a_curs),
              f"pages {a_sizes}; cursors {[raw_of(c) for c in a_curs[:2]]}")

        # FOLLOWING | EVERYONE: Following is the people Quin follows (Gwen) and
        # Quin; Everyone everybody (here, the section's own, by its word).
        f_posts, _, _, _ = walk(q_cl, "following")
        e_posts, _, _, _ = walk(q_cl, "everyone", q=G13)
        gwen_quin = [x for x in oracle if x in (p_a, p_flip, p_q, p_g2)
                     or (post_row(x) or ("", "", ""))[2] in ("galgwen", "galquin")]
        check("Following holds only the people you follow and your own (Quin follows Gwen: hers and Quin's, newest"
              " first); Everyone holds everybody's",
              followed == 200 and f_posts == gwen_quin and set(f_posts) >= {p_a, p_flip, p_q, p_g2}
              and e_posts == mine13,
              f"follow {followed}; following {len(f_posts)} (want {len(gwen_quin)}), Hugo's or Ivy's among them"
              f" {[x for x in f_posts if x in (p_b, p_c)]}; everyone {len(e_posts)} of {len(mine13)}")

        # HOT: plays in the last seven days, most first, newest first among equals.
        h_posts, _, h_sizes, h_curs = walk(q_cl, "everyone", "hot", G13)
        zero = [x for x in mine13 if x not in (p_a, p_b, p_c)]
        hot_cur = re.compile(r"\d+\|\d{16}\|[A-Za-z0-9_-]{11}\|\d{16}")
        check("Hot is plays in the last seven days, most first: three this week, then two, then one (five eight days"
              " ago count for nothing), then the rest newest first; Load more keeps its order, by a cursor that holds"
              " the moment it was ranked at and names no internal id",
              h_posts == [p_a, p_b, p_c] + zero and len(h_sizes) >= 2
              and all(c.startswith("h.") and hot_cur.fullmatch(raw_of(c, hot=True)) for c in h_curs),
              f"first {[{p_a: 'a3', p_b: 'b2', p_c: 'c1'}.get(x, x) for x in h_posts[:5]]}; pages {h_sizes};"
              f" cursors {[raw_of(c, hot=True) for c in h_curs[:1]]}")

        # SEARCH: the post's words, the maker's name and @handle; nothing else.
        found = {q: walk(q_cl, "everyone", "new", q)[0] for q in
                 ("lighthouse at dusk", "Hugo Bell", "galivy", "@galivy", "WILHELMINACONSTANCE", "zz" + G13)}
        ivy_all = [x for x in mine13 if x in fill or x == p_c]
        check("a search finds a post by its words, and its maker by name or @handle (any case), and nothing else;"
              " a search that finds nothing finds nothing",
              found["lighthouse at dusk"] == [p_a] and found["Hugo Bell"] == [p_b]
              and found["galivy"] == ivy_all and found["@galivy"] == ivy_all
              and found["WILHELMINACONSTANCE"] == ivy_all and found["zz" + G13] == [],
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
            out.tiles[id] = { ratio: Math.round(pic.width / pic.height * 10000) / 10000, durL: Math.round((d.left - pic.left) * 10) / 10,
              durB: Math.round((pic.bottom - d.bottom) * 10) / 10, durH: Math.round(d.height * 10) / 10, tri: Math.round(tri.width * 10) / 10,
              words: (dur.querySelector('span') || { textContent: '' }).textContent.trim(),
              face: [Math.round(f.width * 10) / 10, Math.round(f.height * 10) / 10, getComputedStyle(ring).borderRadius,
                     !!ring.querySelector('img'), !!ring.querySelector('.face-blank'), ring.textContent.trim()],
              name: nm.textContent, weight: ns.fontWeight, ellipsis: ns.textOverflow + ' ' + ns.whiteSpace,
              cut: nm.scrollWidth > nm.clientWidth + 0.5, inside: nm.getBoundingClientRect().right <= r.right + 0.5,
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
        check("the tiles are two across on a touch phone (12px apart, rows 18px apart) and three on a desk (20px and"
              " 26px), each one link to its post, the drawing's box 650 x 486",
              cols.get("phone") == (2, 12, 18) and cols.get("desk") == (3, 20, 26)
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
        check("under it the maker's face at 22px (their drawn face, or the empty circle, never an initial) and first"
              " name (600, cut with an ellipsis, never past the tile), and the hearts and comments each only when there"
              " are some, their icons 14px",
              all(t["face"][:3] == [22, 22, "50%"] and not t["face"][5] for s in geo for t in geo[s]["tiles"].values())
              and all(geo[s]["tiles"][p_a]["face"][3] and geo[s]["tiles"][p_b]["face"][4] for s in geo)
              and all(geo[s]["tiles"][k]["name"] == n_ for s in geo for k, n_ in
                      ((p_a, "Gwen"), (p_b, "Hugo"), (p_c, "Wilhelminaconstance")))
              and all(t["weight"] == "600" and t["ellipsis"] == "ellipsis nowrap" and t["inside"]
                      for s in geo for t in geo[s]["tiles"].values()) and geo["phone"]["tiles"][p_c]["cut"]
              and all(geo[s]["tiles"][k]["counts"] == v for s in geo for k, v in WANT_N.items()),
              f"{ {k: (t['face'], t['name'], t['cut'], t['counts']) for k, t in geo.get('phone', {}).get('tiles', {}).items()} }")

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
                        cpg.wait_for_url(lambda u: "/social/p/" in u, timeout=5000)
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
              and taps.get(("desk", "keyboard")) == (["gal-tile", f"/social/p/{first_tile[0]}"],
                                                     f"/social/p/{first_tile[0]}") if first_tile else False,
              f"taps { {f'{s} {k}': v for (s, k), v in taps.items() if v != f'/social/p/{p_a}'} }; maps {tmaps}")

        # THE PILL: a tap on Following, read on every frame (light and dark, and
        # under Reduce Motion): the tint glides and starts before the tiles
        # change, the tiles fade and change only while they can't be seen, and
        # the page doesn't scroll; the address says Following, and a reload
        # opens on it.
        GFRAMES = r"""([ms]) => { window.__gf = []; const seg = document.querySelector('[data-gal-show]'), sl = seg.querySelector('.fo-slider');
          const swap = document.querySelector('[data-gal-swap]'), grid = document.querySelector('[data-gal-grid]'), t0 = performance.now();
          const sig = () => [...grid.children].slice(0, 4).map(e => e.getAttribute('data-post')).join('|') + '#' + grid.children.length;
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
                got["shown"] = cpg.evaluate("() => [...document.querySelectorAll('.gal-tile')].map(a => a.dataset.post)")[:30]
                cpg.reload()
                cpg.wait_for_timeout(700)
                got["after reload"] = cpg.evaluate("""() => [(document.querySelector('[data-gal-show] button[aria-pressed="true"]') || {}).textContent,
                  [...document.querySelectorAll('.gal-tile')].map(a => a.dataset.post).slice(0, 30)]""")
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
        # every new query's plan checked in its suite): New reads the posts by
        # their time's own index, newest first, with no sort of its own; Hot
        # reads the week's plays on the views' time (Skribl's index, through
        # recent_plays), and then orders by them, as the gallery's own Hot does.
        PROBE = r"""
import json
from sqlalchemy import event
from app import app, db
from social import gallery
seen = []
def keep(conn, cursor, statement, params, context, executemany):
    if "FROM social_posts" in statement and statement.lstrip().upper().startswith("SELECT"):
        seen.append((statement, params))
out = {}
with app.test_request_context("/social/explore"):
    for sort in ("new", "hot"):
        seen.clear()
        event.listen(db.engine, "before_cursor_execute", keep)
        gallery.page(None, "everyone", sort, "")
        event.remove(db.engine, "before_cursor_execute", keep)
        out[sort] = [r[3] for st, pr in seen[:1]
                     for r in db.session.connection().exec_driver_sql("EXPLAIN QUERY PLAN " + st, pr).fetchall()]
print("PLAN " + json.dumps(out))
"""
        pr = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
        plans = next((json.loads(ln[5:]) for ln in pr.stdout.splitlines() if ln.startswith("PLAN ")), {})
        check("the Gallery's reads are on their indexes: New the posts by their time's own index, newest first, with no"
              " sort of its own; Hot the week's plays by the views' time, both ends of the week (through recent_plays)",
              any("ix_social_posts_created" in x for x in plans.get("new", []))
              and not any("TEMP B-TREE" in x for x in plans.get("new", []))
              and any("ix_skribl_views_created (created_at>? AND created_at<?)" in x for x in plans.get("hot", [])),
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
