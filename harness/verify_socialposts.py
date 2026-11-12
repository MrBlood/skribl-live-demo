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
     else's Copy link, Share…, Report this post and Block @them (piece 5).
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
  9. EVERY DRAWING THE SITE'S PEOPLE SHOW: Home holds the drawings they
     posted from the Pad on its own page (Make) and showed in the gallery,
     among the posts, newest first, once each; not one kept unlisted, nor
     one by somebody not on the site; Load more walks both; a drawing's own
     page, its ⋯ and its Delete, and their guards.

SOCIALPOSTS_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Posts at /social (phase 1, piece 4)".
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
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

STATE = """() => { const p = window.SkriblInline ? SkriblInline.players() : [];
  return p.map(x => x.state().state); }"""


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
          comments: (document.querySelector('.comments-soon') || {}).textContent })""")
        playing = pg.evaluate(STATE)
        check("Post sends the words and the drawing as one post: the post's own page, its row (the words as typed,"
              " the person), its skribl through create_post (unlisted without the tick, its title the first words,"
              " no caption, the person its author)",
              url.startswith("/social/p/") and row is not None and row[0] == "Day 12. The beard took longer than the skull.\nWatch it at 2×."
              and row[2] == "mira" and sk is not None and sk[0] == "unlisted"
              and sk[1] == "Day 12. The beard took longer than the skull." and not sk[2]
              and sk[3] == db("select public_id from social_people where handle = 'mira'")[0][0],
              f"url {url}; row {row}; skribl {sk}")
        check("the post's own page plays its drawing by itself, its words, when and Comments' place kept",
              playing[:1] == ["playing"] and page["words"] == "Day 12. The beard took longer than the skull.\nWatch it at 2×."
              and " at " in (page["meta"] or "")
              and (page["comments"] or "").startswith("Comments open soon."),
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
          name: c.querySelector('.post-name').textContent, href: c.querySelector('.post-who').getAttribute('href'),
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
        pg.click(".top [data-post-menu]")
        pg.wait_for_timeout(600)
        mine = pg.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())")
        pg.click("#postSheet [data-act=copy]")
        pg.wait_for_timeout(400)
        copied = pg.evaluate("() => document.querySelector('#postSheet [data-post-say]').textContent")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)
        jp = juno.pg
        jp.goto(BASE + f"/social/p/{pid}")
        jp.wait_for_timeout(800)
        jp.click(".top [data-post-menu]")
        jp.wait_for_timeout(600)
        theirs = jp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())")
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
              " by hand); somebody else's says Copy link, Share…, Report this post",
              mine == ["Copy link", "Share…", "Delete post"]
              and theirs == ["Copy link", "Share…", "Report this post", "Block @mira"]
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
            pg.click(".top [data-post-menu]")
            pg.wait_for_timeout(600)
            pg.click("#postSheet [data-act=delete]")
            pg.wait_for_timeout(700)
            ask = pg.evaluate("""() => { const s = document.getElementById('deleteSheet'), t = document.getElementById('deleteTitle');
              return { open: !!s && s.classList.contains('is-open'), title: t ? t.textContent : null,
                       at: location.pathname + location.search }; }""")
            pg.click("#deleteSheet .post-sheet-acts [data-make-close]", timeout=5000)
            pg.wait_for_timeout(600)
            kept = post_row(pid) is not None and skribl_row(skid) is not None
            pg.click(".top [data-post-menu]", timeout=5000)
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
    if part(9, "Home holds every drawing the site's people show: posts, and drawings from the Pad outside a post"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        # A drawing posted from the Pad on its own page (Make's Draw), as the
        # Pad posts it: Skribl's API, as the person signed in (or nobody), its
        # own token from its own cookie.
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
        CARDS = """() => [...document.querySelectorAll('.post-card')].map(c => ({ kind: c.getAttribute('data-kind'),
          id: c.getAttribute('data-post'), skribl: c.getAttribute('data-skribl'),
          words: ((c.querySelector('.post-words') || {}).textContent || ''), url: c.getAttribute('data-url') }))"""

        def pad(who_pg, title, vis="public", seed=0):
            who_pg.goto(BASE + "/social/")
            return who_pg.evaluate(PAD, [title, vis, seed])

        def home_cards(pg_):
            pg_.goto(BASE + "/social/")
            pg_.wait_for_timeout(700)
            return pg_.evaluate(CARDS)

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
        top = home_cards(juno.pg)[:3]
        seen_ids = [c["skribl"] for c in home_cards(juno.pg)]
        check("Home holds a drawing one of the site's people showed from the Pad, outside a post: newest first among"
              " the posts, its title for its words, with a page of its own; not one kept unlisted, nor one by somebody not on"
              " the site; and a post shown in the gallery shows once, as the post",
              [st_s, st_u, st_n] == [201, 201, 201]
              and [c["kind"] for c in top] == ["p", "s", "p"] and top[0]["id"] == g_post
              and top[1]["skribl"] == shown and top[1]["words"] == "Section 9, shown from the Pad"
              and top[1]["url"] == f"/social/b/{shown}"
              and top[2]["id"] == (j1.get("post") if isinstance(j1, dict) else None)
              and kept not in seen_ids and nobodys not in seen_ids and seen_ids.count(g_skribl) == 1,
              f"top {top}; unlisted on Home {kept in seen_ids}; nobody's {nobodys in seen_ids};"
              f" the gallery post's drawing {seen_ids.count(g_skribl)}x")

        # Load more across both: twelve posts and twelve drawings, one after
        # the other, read back page by page through the button.
        made = []
        for i in range(12):
            st, j = make_post(juno, f"Interleave post {i:02d}", seed=100 + i)
            made.append(("p", j.get("post") if isinstance(j, dict) else None))
            time.sleep(0.02)
            st, sid = pad(juno.pg, f"Interleave drawing {i:02d}", "public", 100 + i)
            made.append(("s", sid))
            time.sleep(0.02)
        pg = mira.pg
        pg.goto(BASE + "/social/")
        pg.wait_for_timeout(800)
        for _ in range(8):
            nxt = pg.evaluate("() => { const b = document.querySelector('[data-feed-next]'); return !!b && !b.hidden; }")
            if not nxt:
                break
            n0 = pg.evaluate("() => document.querySelectorAll('.post-card').length")
            pg.click("[data-feed-next]")
            pg.wait_for_function("(n) => document.querySelectorAll('.post-card').length > n", arg=n0, timeout=15000)
            pg.wait_for_timeout(300)
        allc = pg.evaluate(CARDS)
        got = [("p", c["id"]) if c["kind"] == "p" else ("s", c["skribl"]) for c in allc]
        want = list(reversed(made))
        order_ok = got[:len(want)] == want
        check("Load more walks the posts and the drawings together, newest first, none twice and none missed",
              order_ok and len(got) == len(set(got)) and all(m in got for m in made),
              f"first {got[:6]} want {want[:6]}; {len(got)} cards, {len(set(got))} different")

        # A drawing's own page, its ⋯, and its Delete; and another of hers from
        # the Pad, untitled, for More from.
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
        theirs = jp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())")
        jp.keyboard.press("Escape")
        to_post = jp.goto(BASE + f"/social/b/{g_skribl}")
        landed = jp.evaluate("() => location.pathname")
        mp = mira.pg
        mp.goto(BASE + f"/social/b/{shown}")
        mp.wait_for_function("() => !!window.SocialSheet && document.readyState === 'complete'", timeout=15000)
        mp.wait_for_timeout(400)
        mp.click("[data-post-menu] >> visible=true")
        mp.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        mine = mp.evaluate("() => [...document.querySelectorAll('#postSheet .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())")
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
              " post to its author, asked once in the drawing's own words, and then it is gone (Home says so); a"
              " post's drawing's page is the post's",
              page["at"] == f"/social/b/{shown}" and page["kind"] == "s"
              and page["words"].strip() == "Section 9, shown from the Pad"
              and playing[:1] == ["playing"]
              and [f"/social/b/{another}", "A drawing"] in page["more"]
              and [f"/social/p/{g_post}", "Section 9, a post shown in the gallery"] in page["more"]
              and theirs == ["Copy link", "Share…", "Report this post", "Block @mira"]
              and landed == f"/social/p/{g_post}"
              and mine == ["Copy link", "Share…", "Delete post"] and ask.get("open") and "stopped" not in ask
              and ask.get("lede") == ["The drawing goes for good, from Home and from Explore. This can’t be undone."]
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
        check("a drawing's Delete needs the page's token (403), is its author's alone (somebody else's: 404, the"
              " drawing kept), and never takes a post's drawing without the post (404); a drawing's page is a kind"
              " 404 for one kept unlisted, one by somebody not on the site, and none",
              no_token == 403 and not_mine == 404 and skribl_row(sid_k) is not None
              and a_posts == 404 and skribl_row(g_skribl) is not None and post_row(g_post) is not None
              and pages == {"unlisted": 404, "nobody's": 404, "none": 404},
              f"no token {no_token}; somebody else's {not_mine} (kept {skribl_row(sid_k) is not None});"
              f" a post's drawing {a_posts}; pages {pages}")

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
