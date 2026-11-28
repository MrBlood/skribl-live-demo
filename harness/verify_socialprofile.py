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

   1. A PROFILE: name, @handle and bio (its line breaks kept); on its
      Gallery tab that person's drawings shown outside a post, public only,
      newest first, each opening its own page, to visitors (and to the person
      their link-only one too, hidden, with the eye: section 19), Load more
      paging within them, and nothing of Skribl's Gallery
      section any more (the map's step 4); any case of the handle; a kind 404
      for nobody; You leads to your own profile, and somebody else's marks
      no place in the bar; the gear leads to Settings; an empty profile in
      its own words, tab by tab (to its own person, what puts something
      there; to anybody else, that there is nothing yet).
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
  15. A PROFILE'S TABS, THE STRIP (the map's step 4; the owner's "Yes" to its
      mock, Nov 14): Posts · Gallery · Likes · Bookmarks · Drafts on your own
      page (Bookmarks since the owner's "All yes", Nov 14), Posts · Gallery on
      anybody else's, on a touch phone and a desk, light and dark: painted,
      48px, the strip the screen's width on a phone and the column's on a
      desk; the chosen one in the first ink with the bar's pen line under it,
      read off the paint, the others in the second ink; your own five SIZED
      TO THEIR WORDS on a touch phone (16px or more between the painted
      words in every face here, the outer words 16px in where the face
      allows, never past the screen), a desk's equal columns; the line under
      the chosen tab before any script runs (every script refused), on a
      phone and a desk; Likes, Bookmarks and Drafts nowhere on anybody else's
      page or in its source, their addresses sending anybody else to the
      person's page; each tab its own address, the back button and forward,
      a reload and a shared link landing on it; the switch read on every
      frame (the line put under the tab and drawing itself there, the one it
      left fading; the panel fades and changes only while unseen, the page
      holds still), and under Reduce Motion the line put there whole and the
      panel still fading.
  16. WHAT EACH TAB HOLDS: Posts, their posts as Home's one card, newest
      first, Load more; the Gallery, every drawing and Flip they shared, a
      post's tile opening its post and one shown outside a post its own
      page, with its length, never a face or one kept link-only, each tile
      one link; Likes, yours alone, the posts you liked, newest liked first,
      Load more (posts only, nobody a block hides, nothing taken down, a mute
      changing nothing); Drafts, yours alone, your account's drafts as tiles,
      newest saved first, each a link to the Pad or Flip with that draft
      (what a tap on one does is section 20); the reads on their indexes;
      every tab's kind words when it holds nothing.
  17. THE TABS' WORDS: every word on the strip and in every tab at 4.5:1 on
      what is painted behind it, every control 44px, phone and desk, light
      and dark.
  18. DELETE FROM YOUR OWN PAGE (the owner's "Yes", Nov 14): Delete post on a
      card of your Posts tab keeps you on your page (never Home and its note),
      the post gone, focus on the next card's ⋯, and Home's own words in the
      site's toast near the finger (the owner's second "Yes", Nov 14), no
      Undo, never over the next card's ⋯; read on every frame it fades, then
      its room closes and the next card rises over many frames; under Reduce
      Motion it fades and its room goes at once once unseen; the last one
      gone, the tab's kind words.
  19. THE EYE ON YOUR OWN GALLERY TAB (the owner's "Yes, the eye in view",
      Nov 14): each of your tiles, and nobody else's, wears an eye at its top
      right (painted, 44px, 13px in, on the ▶'s glass); one tap hides the
      drawing from the Gallery (crossed, "Hidden", faded to 55%, the site's
      toast with Undo), a post's by the site's flag (the post stays on Home
      and in your Posts), one outside a post by its visibility in Skribl; end
      to end both kinds, through a reload; the toast never over an eye; read
      on every frame, and under Reduce Motion; its ink at 4.5:1 off the
      pixels; its guards; every tap counting when pressed fast. Nothing of it
      on anybody else's page or in its source.
  20. A DRAFT'S TILE OPENS INSIDE A POST (the owner's "All yes", Nov 19, to
      the walk of Save and Drafts): a tap keeps you on your page, the
      composer's sheet and the editor that made the draft over it, nothing
      of the sheet painted on any frame until Add (only the editor is seen
      rising: a phone, a desk, Reduce Motion) and the words never taking
      focus; the draft on its canvas, Add its button and its × there; put away without
      Add (its ×, on a desk as on a phone: the editor fills the window there
      since Nov 26, nothing beside it to tap) the sheet goes with it,
      nothing attached, focus back on the tile; Add brings it attached,
      the sheet under it; with a drawing attached already the sheet opens on
      it and says a post holds one; a Flip draft in Flip the same.
  21. THE PAGE BEHIND HOLDS STILL while the editor is over it (the owner's
      iPhone, Nov 22: each letter typed in Text scrolled the timeline behind
      the Pad): fixed where it stood, tries to scroll it moving nothing, and
      scrolled back to that same place once the editor has gone.

The layers (the site imports only Skribl's documented names, and its
templates only documented partials, the face player's now among them) stay
verify_social's, section 8.

SOCIALPROFILE_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Profiles with drawn faces at /social", and
"The Gallery of every skribl" for 1, 18 and 19.
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


def browser_as(b, who, screen="phone", scheme="light", reduced=False, scripts=True, init=()):
    """Another browser carrying `who`'s cookies (or nobody's), from its address.
    `scripts` False: a browser that runs none of the page's scripts, inline or
    not (what a page is before any script runs)."""
    opts = dict(PHONE if screen == "phone" else DESK)
    kw = {"reduced_motion": "reduce"} if reduced else {}
    if not scripts:
        kw["java_script_enabled"] = False
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **opts, **kw)
    ctx.add_init_script(WATCH)
    for s_ in init:
        ctx.add_init_script(s_)
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


def post_skribl(who, title, visibility="public", base=None, ground="#f6f2ea"):
    """One drawing through Skribl's own API as `who` (Skribl is told who is
    signed in to the site: CSRF is on), or as nobody. `base` is the picture
    it began on, a data URL, where the Pad keeps one (its frame's
    baseSnapshot); `ground`, the colour it is drawn on (the Pad's dark is
    #0d0f14)."""
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
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": ground}}]}
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


# ---- posts, likes and drafts, for a profile's tabs (sections 15 to 17) ------------

def tab_drawing(seed=0, n=40, step=30, flip=False):
    """A small drawing as the editors hand one back (`n` points `step` ms
    apart), or a Flip of three pages."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * step, "start": i == 0} for i in range(n)]
    body = {"version": 2, "schemaVersion": 2, "playbackMode": "flip" if flip else "replay",
            "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [n], "background": {"color": "#f6f2ea"}}]}
    if flip:
        body["fps"] = 12
        body["frames"] += [{"strokes": [dict(p, x=p["x"] + 20 * k) for p in pts], "strokeGroups": [n],
                            "background": {"color": "#f6f2ea"}} for k in (1, 2)]
    return body


def site_post(who, words, payload=None):
    """A post as Home's composer sends one (/social/posts): its address, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": payload or tab_drawing()})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def like_it(who, path, liked=True):
    """`who`'s like on a post (/p/<id>) or a drawing (/b/<id>), set or taken back: the status."""
    c = who.client()
    c.get("/social" + path)
    return c.post_json("/social" + path + "/like", {"liked": liked})[0]


def mark_it(who, path, kept=True):
    """`who`'s bookmark on a post (/p/<id>) or a drawing (/b/<id>), kept or taken away: the status."""
    c = who.client()
    c.get("/social" + path)
    return c.post_json("/social" + path + "/bookmark", {"bookmarked": kept})[0]


def thumb_of(rgb):
    """A draft's small picture as the editors make one: a JPEG data URL, the
    paper and a line in `rgb` (None without Pillow, which the editors' never is)."""
    if Image is None:
        return None
    from PIL import ImageDraw
    im = Image.new("RGB", (240, 180), (246, 242, 234))
    ImageDraw.Draw(im).line([(36, 120), (90, 48), (150, 138), (204, 58)], fill=rgb, width=8)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def save_draft(who, kind, title, payload, thumbnail, draft_id=None):
    """A draft saved to `who`'s account through Skribl's own API, as the
    editors' Save does (a new one, or `draft_id` saved again): its id."""
    ctx = who.ctx
    ctx.request.get(BASE + "/api/skribls?limit=1")
    tok = next((c["value"] for c in ctx.cookies(BASE) if c["name"] == "skribl_csrf"), "")
    h = {"Content-Type": "application/json", "X-Skribl-CSRF": tok}
    data = json.dumps({"kind": kind, "title": title, "payload": payload, "thumbnail": thumbnail})
    r = (ctx.request.put(BASE + f"/api/drafts/{draft_id}", data=data, headers=h) if draft_id
         else ctx.request.post(BASE + "/api/drafts", data=data, headers=h))
    return r.json().get("id") if r.ok else f"refused {r.status} {r.text()[:120]}"


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


def gone_by(pg, most=6000):
    """Until the editor over the page has gone (its wrap hidden), `most` ms at the longest, then a breath for the
    page behind to be put back: a read that waits for the thing, never a set time after it began."""
    try:
        pg.wait_for_function("() => { const w = document.getElementById('facePad'); return !w || w.hidden; }", timeout=most)
    except Exception:  # noqa: BLE001 -- still up: the row that reads it says so
        pass
    pg.wait_for_timeout(200)


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
# own: a face has no words; and since a profile holds Home's cards (its tabs,
# the map's step 4), the player's line under a drawing among them, as every
# other social suite's reader counts it).
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


# ---- a profile's tabs (sections 15 to 17; the map's step 4) --------------------------

#: The strip as it stands: each tab's box, whether it is painted where it is
#: (what is at its middle is the tab), its ink and whether it is the chosen
#: one; the inks it should wear, from the page's own tokens; the pen line's
#: box; and where the column's content runs.
STRIP = r"""() => { const s = document.querySelector('[data-prof-tabs]'); if (!s) return null;
  const probe = c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e);
    const v = getComputedStyle(e).color; e.remove(); return v; };
  const col = document.querySelector('main .col'), cs = getComputedStyle(col), cb = col.getBoundingClientRect();
  const r = s.getBoundingClientRect(), pen = s.querySelector('.prof-pen'), p = pen ? pen.getBoundingClientRect() : null;
  return { left: r.left, right: r.right, vw: innerWidth,
    inner: [cb.left + parseFloat(cs.paddingLeft), cb.right - parseFloat(cs.paddingRight)],
    ink: probe('var(--ink)'), ink2: probe('var(--ink-2)'), brand: probe('var(--brand)'),
    pen: p && { cx: p.left + p.width / 2, w: p.width, h: p.height, top: p.top, bottom: p.bottom },
    tabs: [...s.querySelectorAll('a[data-tab]')].map(a => { const b = a.getBoundingClientRect();
      const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return { key: a.getAttribute('data-tab'), name: a.textContent.trim(), cur: a.getAttribute('aria-current'),
               href: a.getAttribute('href'), w: b.width, h: b.height, cx: b.left + b.width / 2, top: b.top, bottom: b.bottom,
               painted: !!hit && (hit === a || a.contains(hit)), color: getComputedStyle(a).color }; }) }; }"""


def pen_paint(pg, st):
    """The pen line read off the paint: under each tab, in the line's own
    band, how many pixels are the pen's purple ({key: count})."""
    if Image is None or not st or not st.get("pen"):
        return {}
    want = [int(v) for v in re.findall(r"[\d.]+", st["brand"])[:3]]
    top, bottom = max(0, st["pen"]["top"] - 2), st["pen"]["bottom"] + 2
    png = pg.screenshot(clip={"x": 0, "y": top, "width": st["vw"], "height": bottom - top})
    im = Image.open(io.BytesIO(png)).convert("RGB")
    px, out = im.load(), {}
    for t in st["tabs"]:
        n = 0
        for x in range(max(0, int(t["cx"] - 26)), min(im.width, int(t["cx"] + 26))):
            for y in range(im.height):
                if sum((a - c) ** 2 for a, c in zip(px[x, y], want)) <= 70 ** 2:
                    n += 1
        out[t["key"]] = n
    return out


#: YOUR OWN FIVE, SIZED TO THEIR WORDS (bookmarks, the owner's "All yes", Nov
#: 14): the faces the strip is read in besides the page's own, where they are
#: installed. Inter, Liberation Sans and FreeSans have SF's, Arial's and
#: Helvetica's widths, near the owner's iPhone and Segoe UI; DejaVu Sans is
#: wider than any face the app is drawn in on a device, and the one CI draws
#: in (system-ui on Linux), so the room between words is read in it too.
TAB_FACES = ["Inter", "Liberation Sans", "FreeSans", "DejaVu Sans"]
TAB_HAVE = """(faces) => faces.filter((f) => { const x = document.createElement('canvas').getContext('2d'), t = 'Posts Gallery Likes Bookmarks Drafts';
  x.font = '600 40px monospace'; const a = x.measureText(t).width; x.font = '600 40px "' + f + '", monospace'; return Math.abs(x.measureText(t).width - a) > 0.5; })"""
#: Whether anything is past the screen, as a touch phone shows it: a phone
#: whose page is wider than it draws the whole page smaller to fit, so the
#: page's own widths say nothing (scrollWidth and innerWidth grow together);
#: what tells is the width the page was laid out at, its zoom, and the strip
#: scrolling within itself.
PAST = """(w) => { const s = document.querySelector('[data-prof-tabs]');
  return { vw: innerWidth, scale: visualViewport ? visualViewport.scale : 1, strip: s ? s.scrollWidth - s.clientWidth : null,
           ok: innerWidth === w && (!visualViewport || Math.abs(visualViewport.scale - 1) < 0.001) && !!s && s.scrollWidth <= s.clientWidth }; }"""
TAB_FORCE = """(f) => { let s = document.getElementById('tabsFace');
  if (!s) { s = document.createElement('style'); s.id = 'tabsFace'; document.head.appendChild(s); }
  s.textContent = f ? '[data-prof-tabs] .prof-tab { font-family: "' + f + '", sans-serif !important; }' : ''; }"""


def painted_words(pg, st):
    """The strip's words read off the paint: in the band of its tabs above the
    pen's line, the columns where anything but the strip's own ground is
    painted, run together where less than 7px apart (one word's letters):
    [(left, right)], in CSS pixels."""
    if Image is None or not st or not st.get("tabs"):
        return []
    top = st["tabs"][0]["top"] + 6
    png = pg.screenshot(clip={"x": 0, "y": top, "width": st["vw"], "height": 28})
    im = Image.open(io.BytesIO(png)).convert("RGB")
    px = im.load()
    ground = px[1, im.height // 2]
    cols = [any(max(abs(a - c) for a, c in zip(px[x, y], ground)) > 40 for y in range(im.height)) for x in range(im.width)]
    runs, start, gap = [], None, 0
    for x, on in enumerate(cols + [False] * 8):
        if on:
            if start is None:
                start = x
            gap, last = 0, x
        elif start is not None:
            gap += 1
            if gap >= 7:
                runs.append((start, last + 1))
                start, gap = None, 0
    k = st["vw"] / im.width
    return [(round(a * k, 1), round(z * k, 1)) for a, z in runs]


#: The strip and its panel on every animation frame from now, for `ms`, kept
#: in the page (window.__tabs) for reading after a person's tap: the pen
#: line's middle, the panel's opacity, which tab it holds, the page's scroll,
#: the strip's top, the frame's own time (the one it is drawn for, never when
#: its callback happened to run), how much of the line is drawn (its path's
#: dash: 1 when it has none), each copy of the line that is leaving, its
#: middle and opacity, and the drawing's own length once there is one
#: (window.__penMs).
TABS_SAMPLE = r"""(ms) => { const s = document.querySelector('[data-prof-tabs]'), sw = document.querySelector('[data-prof-swap]');
  const pen = s.querySelector('.prof-pen'), out = window.__tabs = [], t0 = performance.now();
  const mid = e => { const r = e.getBoundingClientRect(); return Math.round((r.left + r.width / 2) * 100) / 100; };
  (function f(frame) { const panel = sw.querySelector('[data-prof-panel]'), path = pen.querySelector('path'), cs = getComputedStyle(path);
    const a = path.getAnimations()[0]; if (a && window.__penMs === undefined) window.__penMs = a.effect.getTiming().duration;
    out.push([mid(pen), +getComputedStyle(sw).opacity,
              panel ? panel.getAttribute('data-tab') : null, Math.round(scrollY),
              Math.round(s.getBoundingClientRect().top * 100) / 100,
              Math.round(((frame === undefined ? performance.now() : frame) - t0) * 10) / 10,
              cs.strokeDasharray === 'none' ? 1 : Math.round(Math.max(0, Math.min(1, 1 - parseFloat(cs.strokeDashoffset))) * 1000) / 1000,
              [...s.querySelectorAll('.prof-pen.is-leaving')].map(e => [mid(e), Math.round(+getComputedStyle(e).opacity * 1000) / 1000])]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); })(); }"""


#: The pen line draws itself (social.css .prof-pen.is-drawn): 0.17s on the
#: pen's curve, cubic-bezier(0.3, 0.7, 0.3, 1), whose steepest is 0.7 / 0.3 =
#: 2.33 times its average speed. The line it left fades in 0.12s.
PEN_MS, PEN_STEEPEST = 170, 0.7 / 0.3


def judge_switch(frames, x0, x1, reduced=False, pen_ms=None):
    """A switch, as read frame by frame (the owner's "Yes to both", Nov 14:
    the line "draw itself really fast instead of sliding"): the pen line is
    put under the new tab with no place between (never a glide), and draws
    itself there, one way, on several frames, no frame drawing more than its
    curve ever does (by each frame's own time, so a runner that stalls a frame
    reads as the stall it is; 0.15 over, for where in a frame it began), all
    of it within 0.7s of its first frame however a busy runner stalls, its
    own length 0.17s (read off the animation itself, the property a stalled
    runner cannot blur); a copy of the line fades where it was, on frames
    between, and is gone. Under Reduce Motion it is
    put there whole, on every frame, and nothing fades. The panel fades out,
    changes only while it can't be seen, and fades back in; the page and the
    strip do not move."""
    if not frames:
        return {"ok": False, "why": "no frames"}
    xs, ops, tabs = [f[0] for f in frames], [f[1] for f in frames], [f[2] for f in frames]
    ts, ds, gone = [f[5] for f in frames], [f[6] for f in frames], [f[7] for f in frames]
    at = next((i for i, t in enumerate(tabs) if t != tabs[0]), None)
    places = sorted({round(x, 1) for x in xs})
    put = (abs(xs[-1] - x1) <= 0.6 and len(places) <= 2 and all(min(abs(x - x0), abs(x - x1)) <= 0.6 for x in xs))
    moved = next((i for i, x in enumerate(xs) if abs(x - x1) <= 0.6), None)
    after = ds[moved:] if moved is not None else []
    steps = [z - a for a, z in zip(after, after[1:])]
    dts = [z - a for a, z in zip(ts[moved:], ts[moved + 1:])] if moved is not None else []
    pace = [st_ / (PEN_STEEPEST * max(dt, 1.0) / PEN_MS + 0.15) for st_, dt in zip(steps, dts)]
    done = next((ts[moved + i] for i, d in enumerate(after) if d >= 0.999), None) if moved is not None else None
    leaving = [(f[5], g) for f in frames for g in f[7]]
    if reduced:
        drew = put and all(d >= 0.999 for d in ds)
        faded_old = not leaving
    else:
        drew = (put and moved is not None and bool(after) and after[0] <= 0.5
                and len({round(d, 3) for d in after if 0.02 < d < 0.98}) >= 2
                and all(st_ >= -0.01 for st_ in steps) and max(pace, default=0) <= 1.0
                and done is not None and done - ts[moved] <= 700 and 120 <= (pen_ms or 0) <= 250)
        lops = [o for _, (_, o) in leaving]
        faded_old = (bool(leaving) and all(abs(lx - x0) <= 0.6 for _, (lx, _) in leaving)
                     and len([o for o in lops if 0.05 < o < 0.95]) >= 1
                     and all(z <= a + 0.01 for a, z in zip(lops, lops[1:])) and not frames[-1][7])
    down = [o for o in ops[:at] if 0.05 < o < 0.95] if at else []
    up = [o for o in ops[at:] if 0.05 < o < 0.95] if at is not None else []
    unseen = at is not None and ops[at] <= 0.05 and all(t == tabs[-1] for t in tabs[at:])
    faded = len(down) >= 2 and len(up) >= 2 and ops[-1] >= 0.99
    held = len({f[3] for f in frames}) == 1 and len({f[4] for f in frames}) == 1
    return {"ok": bool(drew and faded_old and unseen and faded and held), "drew": drew, "old line": faded_old,
            "unseen": unseen, "faded": faded, "held": held, "places": places, "want": round(x1, 2),
            "drawn": [d for d in after if 0 < d < 1][:12], "first": after[0] if after else None,
            "pace": round(max(pace, default=0), 2), "done in": round(done - ts[moved], 1) if done is not None and moved is not None else None,
            "its length": pen_ms,
            "leaving": [round(o, 2) for _, (_, o) in leaving][:12], "changed at": at,
            "opacity there": ops[at] if at is not None else None, "fading": [len(down), len(up)]}


#: Every place a finger can be on a tile, every 6px: is it on the tile's one
#: link (whatever is painted there belongs to it)?
ONELINK = r"""(sel) => { const t = document.querySelector(sel); if (!t) return null; t.scrollIntoView({ block: 'center' });
  const r = t.getBoundingClientRect(), bad = []; let n = 0;
  for (let y = r.top + 1; y < r.bottom - 1; y += 6) for (let x = r.left + 1; x < r.right - 1; x += 6) {
    n++; const h = document.elementFromPoint(x, y); if (!h || h.closest('a') !== t) bad.push([Math.round(x - r.left), Math.round(y - r.top)]); }
  return { n, bad: bad.length, where: bad.slice(0, 4), href: t.getAttribute('href'), mid: [r.left + r.width / 2, r.top + r.height / 2] }; }"""

#: What a tab's panel holds, in order: each card's post, each tile's post or
#: drawing, each draft's id; and whether Load more is there.
PANEL = r"""() => { const p = document.querySelector('[data-prof-panel]'); if (!p) return null;
  const items = [...p.querySelectorAll('[data-prof-list] > *')].map(e => e.matches('.gal-cell') ? e.querySelector('.gal-tile') : e);
  const more = p.querySelector('[data-prof-next]'), none = p.querySelector('[data-prof-none]');
  const c = document.querySelector('[data-prof-tabs] a[aria-current]');
  return { tab: p.getAttribute('data-tab'), chosen: c ? c.getAttribute('data-tab') : null,
    ids: items.map(e => e.getAttribute('data-post') || e.getAttribute('data-drawing') || e.getAttribute('data-draft')),
    more: !!more && !more.hidden, none: none && !none.hidden ? none.innerText.replace(/\s+/g, ' ').trim() : null,
    at: location.pathname }; }"""

# THE SITE'S TOAST (mutes.js, window.SocialToast; section 18's delete and
# section 19's eye): up and saying `w`.
TOAST_UP = """(w) => { const t = document.querySelector('.mu-toast');
  return !!t && !t.hidden && t.classList.contains('is-up') && t.querySelector('[data-mute-said]').textContent === w; }"""

# Where the toast is, and whether it covers any of `sel` in view: by its box,
# and by what is painted at each one's middle with the toast made
# hit-testable (its words take no tap, so elementFromPoint would look through
# them as a tap does); how far it rose above its own place (--mu-lift).
CLEAR_OF = """(sel) => { const t = document.querySelector('.mu-toast'), box = document.querySelector('.mu-toasts');
  const r = t.getBoundingClientRect(); t.style.pointerEvents = 'auto';
  const out = { toast: [Math.round(r.top), Math.round(r.bottom), Math.round(r.left), Math.round(r.right)], vh: innerHeight,
    lifted: parseFloat(getComputedStyle(box).getPropertyValue('--mu-lift')) || 0, under: [], covered: [], seen: 0,
    words: t.querySelector('[data-mute-said]').textContent };
  document.querySelectorAll(sel).forEach(e => { if (!e.getClientRects().length) return; const q = e.getBoundingClientRect();
    if (q.bottom <= 0 || q.top >= innerHeight) return; out.seen++;
    if (q.bottom > r.top && q.top < r.bottom && q.right > r.left && q.left < r.right) out.under.push(Math.round(q.top));
    const at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    if (at && at.closest('.mu-toast')) out.covered.push(Math.round(q.top)); });
  t.style.pointerEvents = '';
  return out; }"""

# Section 19's eyes: each of the tab's cells, scrolled to, as it looks.
EYES19 = r"""() => [...document.querySelectorAll('[data-prof-list] > .gal-cell')].map(c => {
  c.scrollIntoView({ block: 'center', behavior: 'instant' });
  const a = c.querySelector('.gal-tile'), e = c.querySelector('.gal-eye'), chip = e && e.querySelector('.gal-eye-chip');
  const pic = a.querySelector('.gal-pic').getBoundingClientRect(), er = e ? e.getBoundingClientRect() : null, cr = chip ? chip.getBoundingClientRect() : null;
  const at = er ? document.elementFromPoint(er.left + er.width / 2, er.top + er.height / 2) : null;
  const w = c.querySelector('.gal-eye-word'), shut = c.querySelector('.ic-eye-shut'), open = c.querySelector('.ic-eye-open');
  const r1 = x => Math.round(x * 10) / 10;
  return { id: a.getAttribute('data-post') || a.getAttribute('data-drawing'), hidden: c.classList.contains('is-hidden'),
    pressed: e ? e.getAttribute('aria-pressed') : null, name: e ? e.getAttribute('aria-label') : null, label: a.getAttribute('aria-label'),
    eye: er ? [r1(er.width), r1(er.height)] : null,
    chip: cr ? [r1(cr.height), r1(pic.right - cr.right), r1(cr.top - pic.top), r1(cr.width)] : null,
    painted: !!(at && e && (at === e || e.contains(at))),
    word: w ? [w.textContent.trim(), +getComputedStyle(w).opacity] : null,
    icons: [open ? +getComputedStyle(open).opacity : null, shut ? +getComputedStyle(shut).opacity : null],
    plate: +getComputedStyle(a.querySelector('.gal-plate')).opacity,
    glass: chip ? getComputedStyle(chip).backgroundColor : null, ink: e ? getComputedStyle(e).color : null }; })"""

# One cell, as it looks now, and the toast.
ONE_EYE = r"""(s) => { const c = document.querySelector(s); if (!c) return null;
  const a = c.querySelector('.gal-tile'), e = c.querySelector('.gal-eye'), w = c.querySelector('.gal-eye-word');
  const t = document.querySelector('.mu-toast'), up = !!t && !t.hidden && t.classList.contains('is-up');
  return { hidden: c.classList.contains('is-hidden'), pressed: e.getAttribute('aria-pressed'), label: a.getAttribute('aria-label'),
    plate: +getComputedStyle(a.querySelector('.gal-plate')).opacity, word: [w.textContent.trim(), +getComputedStyle(w).opacity],
    toast: up ? { words: t.querySelector('[data-mute-said]').textContent, undo: !t.querySelector('[data-mute-undo]').hidden,
                  icon: getComputedStyle(t.querySelector('.ic')).display !== 'none' } : null }; }"""

# A cell's eye chip's width and its drawing's fade, on every frame from now.
EFRAMES = """([s, ms]) => { window.__ef = []; const c = document.querySelector(s), chip = c.querySelector('.gal-eye-chip'), pl = c.querySelector('.gal-plate'), t0 = performance.now();
  const step = () => { window.__ef.push({ t: Math.round(performance.now() - t0), w: Math.round(chip.getBoundingClientRect().width * 10) / 10,
                                          op: +getComputedStyle(pl).opacity });
    if (performance.now() - t0 < ms) requestAnimationFrame(step); };
  requestAnimationFrame(step); }"""

# The toast's words and its Undo, read on what is painted behind them (the
# toast made hit-testable to ask what is painted there).
READ_TOAST = """() => { const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1]; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ground = e => { const layers = []; for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
      if (b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
    let g = [255, 255, 255]; for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
    return g; };
  const t = document.querySelector('.mu-toast'), out = { read: 0, low: [], lowest: 99 };
  if (!t) return out;
  t.style.pointerEvents = 'auto';
  t.querySelectorAll('.mu-toast-words, .mu-undo').forEach(e => {
    if (e.hidden || !e.getClientRects().length || !e.textContent.trim()) return;
    const r = e.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (!at || !(at === e || e.contains(at))) { out.low.push('not painted: ' + e.textContent.trim()); return; }
    const a = lum(rgba(getComputedStyle(e).color)), b = lum(ground(e)), k = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    out.read++; out.lowest = Math.min(out.lowest, Math.round(k * 100) / 100);
    if (k < 4.5) out.low.push(e.textContent.trim() + ' ' + k.toFixed(2)); });
  t.style.pointerEvents = '';
  return out; }"""

_TABS = {}


def tab_people(b):
    """Pia's page, with something in every tab, and the people around it:
    Kai, whose posts she likes (one of his drawings too, shown outside a post,
    which is no post) and whose drawing and a post she bookmarks; Lux, whose
    post she likes and who then blocks her; Ola, who has nothing yet. Made
    once for sections 15 to 17, whichever runs."""
    if _TABS:
        return _TABS
    pia = _people.get("tabpia") or member(b, "tabpia", "Pia Rowe")
    kai = _people.get("tabkai") or member(b, "tabkai", "Kai Dunn")
    lux = _people.get("tablux") or member(b, "tablux", "Lux Reyes")
    ola = _people.get("tabola") or member(b, "tabola", "Ola Nyberg")
    tag = secrets.token_hex(3)
    # HER GALLERY, oldest first: a drawing shown outside a post before posts,
    # her posts, one shown from the Pad between them, and a Flip; her face and
    # one kept link-only are no post and never public.
    seq = [("s", post_skribl(pia, f"Pia before posts {tag}"))]
    linkonly = post_skribl(pia, f"Pia link-only {tag}", visibility=None)
    face = post_skribl(pia, f"Pia's face {tag}", visibility=None)
    db("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = 'tabpia'", (face,), write=True)
    posts = []
    for k in range(1, 23):
        if k == 12:
            seq.append(("s", post_skribl(pia, f"Pia from the Pad {tag}")))
        posts.append(site_post(pia, f"Pia's post {k} {tag}", tab_drawing(seed=k)))
        seq.append(("p", posts[-1]))
    flip = site_post(pia, f"Pia's flip {tag}", tab_drawing(seed=30, flip=True))
    posts.append(flip)
    seq.append(("p", flip))
    # HER LIKES: Kai's posts in an order of their own, her own post, a drawing
    # of Kai's shown outside a post (no post), and Lux's post, Lux then
    # blocking her.
    kais = [site_post(kai, f"Kai's post {k} {tag}", tab_drawing(seed=40 + k)) for k in range(21)]
    kai_d = post_skribl(kai, f"Kai's drawing {tag}")
    luxp = site_post(lux, f"Lux's post {tag}", tab_drawing(seed=70))
    order = [kais[i] for i in (5, 0, 17, 3, 12, 20, 8, 1, 14, 6, 19, 2, 10, 16, 4, 11, 9, 15, 7, 13, 18)]
    liked, statuses = [], []
    for pid in order[:10]:
        statuses.append(like_it(pia, f"/p/{pid}"))
        liked.append(pid)
    statuses.append(like_it(pia, f"/p/{posts[4]}"))
    liked.append(posts[4])
    statuses.append(like_it(pia, f"/b/{kai_d}"))
    statuses.append(like_it(pia, f"/p/{luxp}"))
    liked.append(luxp)
    for pid in order[10:]:
        statuses.append(like_it(pia, f"/p/{pid}"))
        liked.append(pid)
    lc = lux.client()
    lc.get("/social/")
    blocked = lc.post_json("/social/@tabpia/block", {})[0]
    # HER BOOKMARKS (bookmarks): Kai's drawing shown outside a post, and one of
    # his posts.
    marked = [mark_it(pia, f"/b/{kai_d}"), mark_it(pia, f"/p/{kais[0]}")]
    # HER DRAFTS, as the editors save them: the snail, the bike, then the
    # snail again (newest saved first: the snail); and one of Kai's.
    snail = save_draft(pia, "pad", f"A snail for Kai {tag}", tab_drawing(seed=50), thumb_of((124, 92, 255)))
    bike = save_draft(pia, "flip", f"The bike, half done {tag}", tab_drawing(seed=51, flip=True), thumb_of((255, 111, 145)))
    again = save_draft(pia, "pad", f"A snail for Kai {tag}", tab_drawing(seed=52), thumb_of((124, 92, 255)), draft_id=snail)
    kais_draft = save_draft(kai, "pad", f"Kai's own draft {tag}", tab_drawing(seed=53), thumb_of((31, 27, 46)))
    _TABS.update(pia=pia, kai=kai, lux=lux, ola=ola, tag=tag, seq=seq, posts=posts, flip=flip, linkonly=linkonly,
                 face=face, kais=kais, kai_d=kai_d, luxp=luxp, order=order, liked=liked, blocked=blocked,
                 snail=snail, bike=bike, again=again, kais_draft=kais_draft, marked=marked,
                 made=(all(posts) and all(kais) and all(i for _, i in seq) and bool(linkonly and face and kai_d and luxp)
                       and all(s_ == 200 for s_ in statuses) and blocked == 200 and again == snail
                       and marked == [200, 200]
                       and all(isinstance(x, str) and not x.startswith("refused") for x in (snail, bike, kais_draft))))
    return _TABS


def follow_to(pg_, path, wait=4000):
    """Where a tap took the page: its path, once it left `path` (or `path`)."""
    try:
        pg_.wait_for_url(lambda u: urllib.parse.urlsplit(u).path != path, timeout=wait)
        pg_.wait_for_load_state("load", timeout=10000)
    except Exception:  # noqa: BLE001 -- staying is an answer
        pass
    pg_.wait_for_timeout(300)
    return urllib.parse.urlsplit(pg_.url).path


def tab_shown(pg_, key, timeout=8000):
    """Wait for the panel to hold `key` and stand still (faded back in)."""
    try:
        pg_.wait_for_function("(k) => { const p = document.querySelector('[data-prof-panel]'), s = document.querySelector('[data-prof-swap]');"
                              " return !!p && p.getAttribute('data-tab') === k && !s.classList.contains('is-out')"
                              " && +getComputedStyle(s).opacity >= 0.99; }", arg=key, timeout=timeout)
    except Exception:  # noqa: BLE001 -- not there is the row's red
        pass


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

        # THEIR DRAWINGS ON THEIR GALLERY TAB (the map's step 4: the tabs took
        # the place of Skribl's Gallery section, which held their public
        # skribls). These were shown outside a post (Skribl's own API), so each
        # is a tile opening its own page; the link-only one and Juno's are not
        # Mira's Gallery's.
        def profile_view(pg, handle, path="/gallery"):
            pg.goto(BASE + f"/social/@{handle}{path}")
            pg.wait_for_timeout(300)
            return pg.evaluate("""() => { const t = s => { const e = document.querySelector(s); return e ? e.innerText : null; };
                const tiles = [...document.querySelectorAll('[data-prof-list] .gal-tile')];
                return { name: t('.prof-name'), handle: t('.prof-handle'), bio: t('.prof-bio'),
                         sections: document.querySelectorAll('[data-skribl-gallery], #skriblGallery, #profSkribls').length,
                         chosen: (document.querySelector('[data-prof-tabs] a[aria-current]') || {}).textContent || null,
                         tiles: tiles.map(a => a.getAttribute('data-drawing') || a.getAttribute('data-post')),
                         hidden: tiles.map(a => !!a.closest('.gal-cell.is-hidden')),
                         eyes: document.querySelectorAll('[data-eye]').length,
                         hrefs: tiles.map(a => a.getAttribute('href')),
                         canonical: (document.querySelector('link[rel=canonical]') || {}).href || null,
                         title: document.title }; }""")
        vctx, vpg = browser_as(b, juno)
        seen_by_juno = profile_view(vpg, "mira")
        close_ctx(vctx, vpg)
        actx, apg = browser_as(b, None)
        seen_by_nobody = profile_view(apg, "mira")
        close_ctx(actx, apg)
        check("a profile shows the person's name, @handle and bio (its line break kept), and on its Gallery tab their"
              " public drawings shown outside a post, newest first, each opening its own page, and nothing of Skribl's"
              " Gallery section: to somebody signed in and to nobody alike",
              st_bio == 303 and all(v["name"] == "Mira Okafor" and v["handle"] == "@mira" and v["bio"] == bio
                                    and v["sections"] == 0 and v["chosen"] == "Gallery" and v["tiles"] == [newer, older]
                                    and v["hrefs"] == [f"/social/b/{newer}", f"/social/b/{older}"]
                                    for v in (seen_by_juno, seen_by_nobody)),
              f"bio saved {st_bio}; seen by Juno {seen_by_juno}; by nobody {seen_by_nobody}; ids: newer {newer},"
              f" older {older}, link-only {hidden}, Juno's {theirs}")
        own = profile_view(mira.pg, "mira")
        # ON YOUR OWN GALLERY, YOUR LINK-ONLY ONE TOO (the eye, the owner's "Yes,
        # the eye in view", Nov 14): hidden from the Gallery, faded with the
        # crossed eye, yours alone; your visitors see the public ones (above).
        check("on your own profile's Gallery you see your public drawings, and your link-only one, hidden from the"
              " Gallery (faded, with the crossed eye: yours alone, since Nov 14), each with its eye; your visitors see"
              " the public ones, and no eye",
              own["tiles"] == [hidden, newer, older] and own["hidden"] == [True, False, False] and own["eyes"] == 3
              and seen_by_juno["eyes"] == 0 and seen_by_nobody["eyes"] == 0,
              f"{own['tiles']} hidden {own['hidden']}, eyes {own['eyes']}; link-only {hidden}; visitors' eyes"
              f" {seen_by_juno['eyes']}, {seen_by_nobody['eyes']}")
        # AN EMPTY PROFILE IN ITS OWN WORDS, TAB BY TAB (the owner's yes, Nov
        # 10, kept through the map's step 4): to its own person, what puts
        # something there; to anybody else, signed in or not, only that there
        # is nothing yet, and that it comes when they share one.
        ines = member(b, "ines", "Ines Vale")

        def empty_words(pg, path=""):
            pg.goto(BASE + "/social/@ines" + path)
            pg.wait_for_timeout(200)
            return pg.evaluate("""() => { const e = document.querySelector('[data-prof-none]');
                return e && !e.hidden && e.getClientRects().length ? e.innerText.replace(/\\s+/g, ' ').trim() : null; }""")
        own_empty = (empty_words(ines.pg), empty_words(ines.pg, "/gallery"))
        ectx, epg = browser_as(b, juno)
        their_empty = (empty_words(epg), empty_words(epg, "/gallery"))
        close_ctx(ectx, epg)
        nctx, npg = browser_as(b, None)
        nobodys_empty = (empty_words(npg), empty_words(npg, "/gallery"))
        close_ctx(nctx, npg)
        theirs_words = ("No posts from Ines yet. When Ines shares one, it shows up here.",
                        "No drawings from Ines yet. When Ines shares one, it shows up here.")
        check("an empty profile says it in its own words, tab by tab: to its own person what puts something there"
              " (Posts: say something on Home and draw it; the Gallery: share one in a post), to anybody else only"
              " that there is nothing yet, and that it comes when they share one",
              own_empty == ("No posts yet. Tap the pencil to share one, and your posts show up here.",
                            "No drawings here yet. Share one in a post, and it shows up here.")
              and their_empty == theirs_words and nobodys_empty == theirs_words,
              f"own {own_empty!r}; Juno's view {their_empty!r}; signed out {nobodys_empty!r}")
        actx, apg = browser_as(b, None)
        loud = profile_view(apg, "MiRa", "")
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
        # PAGING STAYS WITHIN THEM, now on their Gallery tab (the map's step 4):
        # past one page of 24, Load more brings the rest of theirs by its own
        # cursor (a drawing's, here: these were shown outside a post), and
        # nobody else's.
        many = [post_skribl(juno, f"Juno's page {tag} {i}") for i in range(26)]
        pctx, ppg = browser_as(b, None)
        ppg.goto(BASE + "/social/@juno/gallery")
        TILES = "() => [...document.querySelectorAll('[data-prof-list] .gal-tile')].map(a => a.getAttribute('data-drawing'))"
        first_page = ppg.evaluate(TILES)
        try:
            ppg.click("[data-prof-next]", timeout=5000)
            ppg.wait_for_function("(n) => document.querySelectorAll('[data-prof-list] .gal-tile').length > n",
                                  arg=len(first_page), timeout=15000)
        except Exception:
            pass
        ppg.wait_for_timeout(400)
        both = ppg.evaluate(TILES)
        more_left = ppg.evaluate("() => { const m = document.querySelector('[data-prof-next]'); return !!m && !m.hidden; }")
        close_ctx(pctx, ppg)
        juno_all = [theirs] + many
        check("past a page of their Gallery, Load more brings the rest of their drawings by its own cursor, and nobody"
              " else's",
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
    # is on Skribl's /gallery (the site's first visit held them until Nov 14,
    # a profile's skribls until the map's step 4). So each is read where it
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
        # You's pen line (the page you're on) sits inside its icon since the phone's bar went to its icons
        # alone (Nov 15): a line under the circle, not a picture in it, so it is no stock silhouette.
        own = juno.pg.evaluate("""() => { const f = document.querySelector('.prof-face'), y = document.querySelector('nav.nav .tab-you .tab-ic');
            return { words: f && f.innerText.trim(), img: !!(f && f.querySelector('img')), svg: !!(f && f.querySelector('svg:not(.ic)')),
                     you: y && y.innerHTML.includes('face-blank'), youImg: !!(y && y.querySelector('img, svg:not(.pen-line)')) }; }""")
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
        # A FIELD IN FOCUS WEARS THE SITE'S RING (the owner, Nov 16, with a
        # screenshot of About you in focus on an iPhone: "is this outline
        # supposed to be blue?"). The site's focus rule named input, button and
        # summary, not textarea, so the one text box fell to the browser's own
        # ring (Safari's blue) while Your name wore the site's. Both, focused:
        # the site's 2px solid --focus, as the page resolves it.
        rings = pg.evaluate("""() => { const pr = document.createElement('i'); document.body.appendChild(pr);
            pr.style.color = 'var(--focus)'; const want = getComputedStyle(pr).color; pr.remove();
            return { want, got: ['editName', 'editBio'].map(id => { const e = document.getElementById(id); if (!e) return { id, missing: true };
              e.focus(); const c = getComputedStyle(e);
              const r = { id, fv: e.matches(':focus-visible'), style: c.outlineStyle, width: c.outlineWidth, color: c.outlineColor };
              e.blur(); return r; }) }; }""")
        check("Edit profile's two fields, in focus, wear the site's own ring (2px solid in --focus), never the"
              " browser's: Your name and About you alike",
              all(r.get("fv") and r.get("style") == "solid" and r.get("width") == "2px" and r.get("color") == rings["want"]
                  for r in rings["got"]), json.dumps(rings))
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
        # A Gallery card of Skribl's with everybody's in it, signed out: on
        # Skribl's own /gallery since the site's first visit became the
        # Gallery's six newest (Nov 14; Explore's was until the map's step 3).
        # The author resolver is the app's, so its url is on every page.
        ctx, pg = browser_as(b, None, "desk")
        pg.goto(BASE + "/gallery")
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
              " round and centred on it, and You's in the bar is a 29px one (its 1.5px ring round it: 32 across, as"
              " Make's purple, the owner's G of Nov 15)",
              bool(pf and ff and yf) and (pf["w"], pf["h"]) == (112, 112) and abs(ff["w"] - ff["h"]) < 0.5
              and 96 <= ff["w"] <= 112 and abs(ff["cx"] - pf["cx"]) < 1 and abs(ff["cy"] - pf["cy"]) < 1
              and (yf["w"], yf["h"]) == (29, 29), json.dumps(ring))

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

    # ------------------------------------------------------------------ 15
    # A PROFILE'S TABS, THE STRIP (the map's step 4; the owner's "Yes" to its
    # mock, Nov 14), where the "Skribls" heading and Skribl's Gallery section
    # were. Pia's page, from her own browser, Kai's and nobody's.
    if part(15, "a profile's tabs, the strip: painted, its inks and pen line, yours alone, its own addresses, gliding"):
        T = tab_people(b)
        pia, kai = T["pia"], T["kai"]
        check("(setup) Pia's posts, drawings shown outside a post, likes and drafts, Kai's posts, Lux's post and block,"
              " each made as a person makes it",
              T["made"], json.dumps({k: T[k] for k in ("flip", "luxp", "blocked", "snail", "bike", "again", "kais_draft")}))
        strips, pens = {}, {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                for who, label in ((pia, "own"), (kai, "theirs"), (None, "nobody")):
                    ctx, pg = browser_as(b, who, screen, scheme)
                    pg.goto(BASE + "/social/@tabpia/gallery")
                    pg.evaluate("() => { const s = document.querySelector('[data-prof-tabs]'); if (s) s.scrollIntoView({ block: 'center' }); }")
                    pg.wait_for_timeout(300)
                    strips[(screen, scheme, label)] = st = pg.evaluate(STRIP)
                    pens[(screen, scheme, label)] = pen_paint(pg, st)
                    close_ctx(ctx, pg)
        names = {k: [t["name"] for t in (v or {}).get("tabs", [])] for k, v in strips.items()}
        wide = {}
        for (screen, scheme, label), st in strips.items():
            span = ([0, st["vw"]] if screen == "phone" else st["inner"]) if st else None
            wide[(screen, scheme, label)] = bool(st) and (
                abs(st["left"] - span[0]) <= 0.5 and abs(st["right"] - span[1]) <= 0.5
                and all(t["painted"] and abs(t["h"] - 48) <= 0.5 and t["w"] >= 44 for t in st["tabs"]))
        check("the strip where the Skribls heading was: Posts · Gallery · Likes · Bookmarks · Drafts on your own page,"
              " Posts · Gallery on anybody else's and signed out, in that order; each tab painted where it is, 48px tall"
              " and more than 44 wide; the strip the screen's width on a touch phone and the column's on a desk; light"
              " and dark",
              all(names[k] == (["Posts", "Gallery", "Likes", "Bookmarks", "Drafts"] if k[2] == "own" else ["Posts", "Gallery"])
                  for k in strips) and all(wide.values()),
              f"names { {' '.join(k): v for k, v in names.items() if k[1] == 'light'} }; not so"
              f" { {' '.join(k): (strips[k] or {}).get('tabs') for k, v in wide.items() if not v} }"[:900])
        inks = {}
        for k, st in strips.items():
            g = next((t for t in (st or {}).get("tabs", []) if t["key"] == "gallery"), None)
            pen, paint = (st or {}).get("pen") or {}, pens.get(k) or {}
            inks[k] = (bool(g) and [t["key"] for t in st["tabs"] if t["cur"] == "page"] == ["gallery"]
                       and g["color"] == st["ink"] and all(t["color"] == st["ink2"] for t in st["tabs"] if t["key"] != "gallery")
                       and abs(pen.get("w", 0) - 44) <= 0.5 and abs(pen.get("h", 0) - 8) <= 0.5
                       and abs(pen.get("cx", -99) - g["cx"]) <= 0.6 and abs(g["bottom"] - pen.get("bottom", -99) - 4) <= 0.6
                       and paint.get("gallery", 0) >= 30 and all(n == 0 for t_, n in paint.items() if t_ != "gallery"))
        check("the chosen tab (the Gallery, at its own address) in the first ink, with the bar's own pen line under it,"
              " 44 x 8, 4px off its foot, its middle under the tab's, read off the paint (the pen's purple under it and"
              " under no other tab); the others in the second ink; phone and desk, light and dark, every page",
              all(inks.values()),
              f"paint {pens.get(('phone', 'light', 'own'))}; not so"
              f" { {' '.join(k): (pens.get(k), (strips[k] or {}).get('pen')) for k, v in inks.items() if not v} }"[:900])

        # LIKES, BOOKMARKS AND DRAFTS ARE YOURS ALONE, in the page and in its
        # source (her bookmark on Kai's drawing is on no page of hers but her
        # own Bookmarks).
        kc, nc, pc = kai.client(), Client(), pia.client()
        mine_src = pc.get("/social/@tabpia")[2]
        srcs = {(name, path): cl.get(path)[2] for name, cl in (("Kai", kc), ("nobody", nc))
                for path in ("/social/@tabpia", "/social/@tabpia/gallery")}
        secret = [T["snail"], T["bike"], "A snail for Kai", "The bike, half done", 'data-tab="likes"',
                  'data-tab="bookmarks"', 'data-tab="drafts"', "/@tabpia/likes", "/@tabpia/bookmarks",
                  "/@tabpia/drafts", T["luxp"], T["kai_d"], "data-marked"] + [
                  p for p in T["liked"] if p != T["posts"][4]]
        leaks = {f"{k[0]} {k[1]}": [x for x in secret if x in src] for k, src in srcs.items()}
        sends = {}
        for name, cl in (("Kai", kc), ("nobody", nc)):
            for tab in ("likes", "bookmarks", "drafts"):
                st_, hd, _ = cl._req("GET", f"/social/@tabpia/{tab}")
                js = cl._req("GET", f"/social/@tabpia/more?tab={tab}")
                sends[f"{name} {tab}"] = (st_, (hd.get("Location") or "").split("?")[0], js[0], js[2][:60])
        own_has = all(x in mine_src for x in ('data-tab="likes"', 'data-tab="bookmarks"', 'data-tab="drafts"',
                                               "/social/@tabpia/likes", "/social/@tabpia/bookmarks",
                                               "/social/@tabpia/drafts"))
        check("Likes, Bookmarks and Drafts are yours alone: on Kai's view of Pia's page and a signed-out one there is no"
              " such tab, no address of any, no draft, nothing she liked and nothing she bookmarked, in the page or its"
              " source; their addresses send anybody else to her page (302), and the tab's own JSON answers them 404"
              " with nothing; her own page has all three",
              own_has and not any(leaks.values())
              and all(v[0] == 302 and v[1].endswith("/social/@tabpia") and v[2] == 404 and T["snail"] not in v[3]
                      for v in sends.values()),
              f"her own page has them {own_has}; leaks { {k: v for k, v in leaks.items() if v} }; {sends}")

        # EACH TAB ITS OWN ADDRESS: a tap, the back button and forward, a
        # reload, a tile opened and the way back.
        def is_(v, key, path):
            return bool(v) and isinstance(v, dict) and v.get("tab") == key and v.get("chosen") == key and v.get("at") == path
        trail = {}
        ctx, pg = browser_as(b, pia, "phone", "light")
        try:
            pg.goto(BASE + "/social/@tabpia")
            tab_shown(pg, "posts")
            trail["start"] = pg.evaluate(PANEL)
            for key in ("gallery", "likes"):
                pg.tap(f'[data-prof-tabs] a[data-tab="{key}"]')
                tab_shown(pg, key)
                pg.wait_for_timeout(250)
                trail[key] = pg.evaluate(PANEL)
            pg.go_back()
            tab_shown(pg, "gallery")
            trail["back"] = pg.evaluate(PANEL)
            pg.go_back()
            tab_shown(pg, "posts")
            trail["back again"] = pg.evaluate(PANEL)
            pg.go_forward()
            tab_shown(pg, "gallery")
            trail["forward"] = pg.evaluate(PANEL)
            pg.reload()
            tab_shown(pg, "gallery")
            trail["reload"] = pg.evaluate(PANEL)
            pg.tap("[data-prof-list] .gal-tile")
            trail["tile"] = follow_to(pg, "/social/@tabpia/gallery")
            pg.go_back()
            tab_shown(pg, "gallery")
            trail["after the tile"] = pg.evaluate(PANEL)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            trail["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        G, H = "/social/@tabpia/gallery", "/social/@tabpia"
        check("each tab is a link with its own address: a tap on the Gallery, then Likes, stays on the page, the address"
              " the tab's once it is in; the back button brings back the Gallery, then Posts, and forward the Gallery"
              " again, the strip and the panel with them; a reload opens on the tab; a tile opened, then the way back,"
              " lands on the Gallery",
              is_(trail.get("start"), "posts", H) and is_(trail.get("gallery"), "gallery", G)
              and is_(trail.get("likes"), "likes", H + "/likes") and is_(trail.get("back"), "gallery", G)
              and is_(trail.get("back again"), "posts", H) and is_(trail.get("forward"), "gallery", G)
              and is_(trail.get("reload"), "gallery", G) and trail.get("tile") == f"/social/p/{T['flip']}"
              and is_(trail.get("after the tile"), "gallery", G),
              json.dumps({k: (v if not isinstance(v, dict) else [v.get("tab"), v.get("chosen"), v.get("at")])
                          for k, v in trail.items()}))
        shared = {}
        for name, who, screen, path in (("Kai", kai, "desk", G), ("nobody", None, "phone", G),
                                        ("Pia's Drafts", pia, "desk", H + "/drafts")):
            ctx, pg = browser_as(b, who, screen, "dark")
            pg.goto(BASE + path)
            shared[name] = pg.evaluate(PANEL)
            close_ctx(ctx, pg)
        check("...and a shared link lands on its tab: Pia's Gallery, opened by Kai and signed out, on the Gallery, its"
              " tiles there; her own link to her Drafts on her Drafts",
              is_(shared.get("Kai"), "gallery", G) and is_(shared.get("nobody"), "gallery", G)
              and len(shared["Kai"]["ids"]) == 24 and is_(shared.get("Pia's Drafts"), "drafts", H + "/drafts"),
              json.dumps({k: v and [v.get("tab"), v.get("chosen"), v.get("at"), len(v.get("ids") or [])] for k, v in shared.items()}))

        # YOUR OWN FIVE ON A TOUCH PHONE, SIZED TO THEIR WORDS (the owner's "All
        # yes", Nov 14: "Bookmarks" is wider than a fifth of a phone), read off
        # the paint in the page's own face and in each of the faces here; a
        # desk's five in equal columns.
        fits, faced = {}, []
        for scheme in ("light", "dark"):
            ctx, pg = browser_as(b, pia, "phone", scheme)
            pg.goto(BASE + "/social/@tabpia/bookmarks")
            pg.evaluate("() => { const s = document.querySelector('[data-prof-tabs]'); if (s) s.scrollIntoView({ block: 'center' }); }")
            pg.wait_for_timeout(300)
            faces = [None] + (pg.evaluate(TAB_HAVE, TAB_FACES) if scheme == "light" else [])
            for f in faces:
                pg.evaluate(TAB_FORCE, f)
                pg.wait_for_timeout(150)
                st = pg.evaluate(STRIP)
                words = painted_words(pg, st)
                over = pg.evaluate(PAST, 402)
                fits[(scheme, f or "its own face")] = (st, words, over)
            pg.evaluate(TAB_FORCE, None)
            close_ctx(ctx, pg)
            if scheme == "light":
                faced = faces
        told15 = {}
        for (scheme, f), (st, words, over) in fits.items():
            gaps = [round(z[0] - a[1], 1) for a, z in zip(words, words[1:])]
            ok = (len(words) == 5 and min(gaps) >= 16 and words[0][0] >= 8 and st["vw"] - words[-1][1] >= 8
                  and over["ok"] and all(tb["w"] >= 44 and tb["painted"] for tb in st["tabs"]))
            if f in ("Inter", "Liberation Sans", "FreeSans"):
                ok = ok and abs(words[0][0] - 16) <= 2 and abs(st["vw"] - words[-1][1] - 16) <= 2
            told15[f"{scheme} {f}"] = {"words": words, "gaps": gaps, "over": over, "ok": ok}
        check("your own five on a 402px touch phone are sized to their words: 16px or more between every two painted"
              " words (about 24 in this box's faces), the outer words 16px in from the screen's edges in the faces of"
              " SF's, Arial's and Helvetica's widths and 8px at least in the widest (DejaVu Sans, CI's), every tab 44px"
              " or more to a finger, nothing past the screen; in the page's own face and every face here, light and"
              " dark",
              len(faced) >= 4 and len(fits) == len(faced) + 1 and all(v["ok"] for v in told15.values()),
              f"{len(faced)} faces; " + json.dumps({k: [v["gaps"], v["words"][:1], v["words"][-1:], v["over"]]
                                                      for k, v in told15.items()})[:700])
        # ...AND ON A NARROWER PHONE (360px, a common Android width), short of
        # room, the edges give first and then the tabs' own room: nothing is
        # ever past the screen, so the phone never draws the page smaller, in
        # every face (DejaVu Sans, CI's, the widest); in the faces of SF's,
        # Arial's and Helvetica's widths the words keep 12px or more.
        narrow = {}
        ctx = b.new_context(viewport={"width": 360, "height": 780}, device_scale_factor=1, is_mobile=True, has_touch=True,
                            extra_http_headers={"X-Forwarded-For": pia.xff})
        ctx.add_cookies([{k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly", "sameSite",
                                                             "secure", "expires")} for c in pia.cookies()])
        pg = ctx.new_page()
        pg.goto(BASE + "/social/@tabpia/bookmarks")
        pg.evaluate("() => { const s = document.querySelector('[data-prof-tabs]'); if (s) s.scrollIntoView({ block: 'center' }); }")
        pg.wait_for_timeout(300)
        for f in [None] + pg.evaluate(TAB_HAVE, TAB_FACES):
            pg.evaluate(TAB_FORCE, f)
            pg.wait_for_timeout(150)
            st = pg.evaluate(STRIP)
            words = painted_words(pg, st)
            gaps = [round(z[0] - a[1], 1) for a, z in zip(words, words[1:])]
            past = pg.evaluate(PAST, 360)
            ok = past["ok"] and all(tb["painted"] for tb in st["tabs"]) and (
                f not in ("Inter", "Liberation Sans", "FreeSans") or (len(words) == 5 and min(gaps) >= 12))
            narrow[f or "its own face"] = {"ok": ok, "gaps": gaps, "past": past}
        ctx.close()
        check("...and on a 360px touch phone, short of room, the edges give first and then the tabs' own room: nothing"
              " past the screen in any face (the phone never draws the page smaller to fit it), and 12px or more between"
              " the painted words in the faces of SF's, Arial's and Helvetica's widths",
              len(narrow) >= 4 and all(v["ok"] for v in narrow.values()),
              json.dumps(narrow)[:700])
        ctx, pg = browser_as(b, pia, "desk", "light")
        pg.goto(BASE + "/social/@tabpia/bookmarks")
        pg.wait_for_timeout(300)
        dst = pg.evaluate(STRIP)
        close_ctx(ctx, pg)
        widths = [round(tb["w"], 2) for tb in (dst or {}).get("tabs", [])]
        check("a desk keeps equal columns: your own five the same width, across the column",
              len(widths) == 5 and max(widths) - min(widths) <= 0.5
              and abs(sum(widths) - (dst["inner"][1] - dst["inner"][0])) <= 1, f"{widths}; column {dst and dst['inner']}")
        # THE LINE BEFORE ANY SCRIPT RUNS: a browser that runs none of the
        # page's scripts, inline or not.
        before = {}
        for who, screen, path, key in ((pia, "phone", "/social/@tabpia/bookmarks", "bookmarks"),
                                       (pia, "desk", "/social/@tabpia/bookmarks", "bookmarks"),
                                       (pia, "phone", "/social/@tabpia/likes", "likes"),
                                       (kai, "phone", "/social/@tabpia/gallery", "gallery")):
            ctx, pg = browser_as(b, who, screen, "light", scripts=False)
            pg.goto(BASE + path)
            pg.evaluate("() => { const s = document.querySelector('[data-prof-tabs]'); if (s) s.scrollIntoView({ block: 'center' }); }")
            pg.wait_for_timeout(300)
            st = pg.evaluate(STRIP)
            ran = pg.evaluate("() => !!window.SocialSheet")
            paint = pen_paint(pg, st)
            close_ctx(ctx, pg)
            tab = next((tb for tb in (st or {}).get("tabs", []) if tb["key"] == key), None)
            pen = (st or {}).get("pen") or {}
            before[f"{screen} {path.rsplit('/', 1)[-1]}"] = {
                "ok": (not ran and bool(tab) and tab["cur"] == "page" and abs(pen.get("cx", -99) - tab["cx"]) <= 0.6
                       and abs(tab["bottom"] - pen.get("bottom", -99) - 4) <= 0.6 and paint.get(key, 0) >= 30
                       and all(n == 0 for k_, n in paint.items() if k_ != key)),
                "pen": round(pen.get("cx", -1), 2), "tab": tab and round(tab["cx"], 2), "paint": paint, "scripts ran": ran}
        check("before any script runs (a browser that runs none), the pen's line is already under the chosen tab, read"
              " from its box and off the paint: your Bookmarks on a phone (the five sized to their words) and a desk,"
              " your Likes on a phone, and Kai's view of her Gallery (two tabs)",
              len(before) == 4 and all(v["ok"] for v in before.values()), json.dumps(before)[:700])

        # THE SWITCH, READ ON EVERY FRAME (to Bookmarks on a phone, where the
        # five are sized to their words, and to Likes on a desk).
        glides = {}
        for screen, scheme, reduced in (("phone", "light", False), ("desk", "dark", False), ("phone", "light", True)):
            ctx, pg = browser_as(b, pia, screen, scheme, reduced=reduced)
            try:
                pg.goto(BASE + "/social/@tabpia")
                tab_shown(pg, "posts")
                pg.evaluate("() => document.querySelector('[data-prof-tabs]').scrollIntoView({ block: 'center' })")
                pg.wait_for_timeout(300)
                st = pg.evaluate(STRIP)
                to_key = "bookmarks" if screen == "phone" else "likes"
                x0 = next(t["cx"] for t in st["tabs"] if t["key"] == "posts")
                x1 = next(t["cx"] for t in st["tabs"] if t["key"] == to_key)
                pg.evaluate(TABS_SAMPLE, 1500)
                if screen == "phone":
                    pg.tap(f'[data-prof-tabs] a[data-tab="{to_key}"]')
                else:
                    pg.click(f'[data-prof-tabs] a[data-tab="{to_key}"]')
                pg.wait_for_timeout(1700)
                glides[(screen, scheme, reduced)] = judge_switch(pg.evaluate("() => window.__tabs || []"), x0, x1, reduced,
                                                                 pg.evaluate("() => window.__penMs === undefined ? null : window.__penMs"))
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                glides[(screen, scheme, reduced)] = {"ok": False, "stopped": str(exc).splitlines()[0][:160]}
            close_ctx(ctx, pg)
        check("the switch, read on every frame (a touch phone in light, to Bookmarks; a desk in dark, to Likes): the pen"
              " line is put under the tab with no place between and draws itself there, one way, on several frames, no"
              " frame drawing more than"
              " its curve ever does (by each frame's own time), its own length 0.17s and all of it within 0.7s, while the"
              " line under Posts fades where it was and is gone; the panel fades out, changes only while it can't be"
              " seen (under 5%), and fades back in; the page doesn't scroll and the strip doesn't move",
              all(glides.get((s_, c_, False), {}).get("ok") for s_, c_ in (("phone", "light"), ("desk", "dark"))),
              json.dumps({f"{k[0]} {k[1]}": v for k, v in glides.items() if not k[2]}))
        check("under Reduce Motion the pen line is put there whole, no frame between, nothing fading where it was, and"
              " the panel still only fades, changing while unseen",
              bool(glides.get(("phone", "light", True), {}).get("ok")), json.dumps(glides.get(("phone", "light", True))))

    # ------------------------------------------------------------------ 16
    # WHAT EACH TAB HOLDS (the map's step 4): Posts, the Gallery, Likes and
    # Drafts, each read from the database's own order; the editors a draft
    # opens in; the reads' plans; the kind words.
    if part(16, "what each tab holds: Posts, the Gallery, Likes and Drafts, Load more, the editors, the kind words"):
        T = tab_people(b)
        pia, kai, ola = T["pia"], T["kai"], T["ola"]
        drawings = [i for k, i in T["seq"] if k == "s"]

        def more_of(pg_, sel, tap=True):
            """Load more, as a person presses it, and its page in."""
            n = pg_.evaluate("(s) => document.querySelectorAll(s).length", sel)
            try:
                (pg_.tap if tap else pg_.click)("[data-prof-next]")
                pg_.wait_for_function("([s, n]) => document.querySelectorAll(s).length > n", arg=[sel, n], timeout=15000)
            except Exception:  # noqa: BLE001 -- none coming is the row's red
                pass
            pg_.wait_for_timeout(400)
            return pg_.evaluate(PANEL)

        # POSTS: Kai's view of Pia's, and Home's own card for the same viewer.
        posts_want = list(reversed(T["posts"]))
        ctx, pg = browser_as(b, kai, "phone", "light")
        pg.goto(BASE + "/social/@tabpia")
        p1 = pg.evaluate(PANEL)
        p2 = more_of(pg, "[data-prof-list] > .post-card")
        late = pg.evaluate("""() => [...document.querySelectorAll('[data-prof-list] > .post-card')].slice(-3).map(c => {
            const box = c.querySelector('.skribl-inline'), t = c.querySelector('time[data-when]');
            return [!!(box && box._skriblInline), t ? t.textContent.trim() : null]; })""")
        close_ctx(ctx, pg)
        oc = ola.client()
        home_html, prof_html = oc.get("/social/")[2], oc.get("/social/@tabkai")[2]

        def card_of(html_, pid):
            m = re.search(r'<article class="post-card" data-post="' + re.escape(pid) + r'".*?</article>', html_, re.S)
            return m.group(0) if m else None
        k_last = T["kais"][-1]
        same = card_of(home_html, k_last) is not None and card_of(home_html, k_last) == card_of(prof_html, k_last)
        check("Posts: their posts and nothing else (not the drawings they showed outside a post), as Home's one card (the"
              " card Home shows the same viewer, the same), newest first; Load more brings the rest by its cursor, none"
              " twice, mounted and its times said as Home's are, and goes",
              p1["ids"] == posts_want[:20] and p1["more"] and p2["ids"] == posts_want and not p2["more"]
              and not set(drawings) & set(p2["ids"]) and same
              and all(m_ and re.fullmatch(r"now|\d+[mhd]", t_ or "") for m_, t_ in late),
              f"first {len(p1['ids'])} (more {p1['more']}), then {len(p2['ids'])} (more {p2['more']}); in order"
              f" {p2['ids'] == posts_want}; the last cards {late}; Home's card the same {same}")

        # THE GALLERY: her posts' drawings and the two she showed outside a post.
        gal_want = [i for _, i in reversed(T["seq"])]
        kind_of = {i: k for k, i in T["seq"]}
        ctx, pg = browser_as(b, kai, "phone", "dark")
        pg.goto(BASE + "/social/@tabpia/gallery")
        g1 = pg.evaluate(PANEL)
        g2 = more_of(pg, "[data-prof-list] > .gal-tile")
        tiles = pg.evaluate("""() => [...document.querySelectorAll('[data-prof-list] > .gal-tile')].map(a => ({
            id: a.getAttribute('data-post') || a.getAttribute('data-drawing'), post: a.hasAttribute('data-post'),
            href: a.getAttribute('href'), says: ((a.querySelector('.gal-dur span') || {}).textContent || '').trim(),
            src: (a.querySelector('.gal-plate img') || { getAttribute: () => '' }).getAttribute('src'),
            name: ((a.querySelector('.gal-by b') || {}).textContent || '').trim() }))""")
        close_ctx(ctx, pg)
        wrong = [t_ for t_ in tiles
                 if t_["post"] != (kind_of.get(t_["id"]) == "p")
                 or t_["href"] != (f"/social/p/{t_['id']}" if t_["post"] else f"/social/b/{t_['id']}")
                 or t_["says"] != ("3 pages" if t_["id"] == T["flip"] else "1 sec" if t_["post"] else "2 sec")
                 or t_["name"] != "Pia Rowe"]
        hidden_ = [x for x in (T["face"], T["linkonly"]) if any(x in (t_["id"] or "") or x in (t_["src"] or "") for t_ in tiles)]
        check("the Gallery: every drawing and Flip Pia shared, newest first, her posts' and the two she showed outside a"
              " post (before posts, and from the Pad between them) together; a post's tile opens its post and the others"
              " their own page, each saying its length (\"1 sec\", \"2 sec\", a Flip \"3 pages\") and her name as she"
              " wrote it (\"Pia Rowe\"); her face"
              " and her link-only drawing never; a page of 24, Load more bringing the last",
              len(g1["ids"]) == 24 and g1["more"] and g2["ids"] == gal_want and not g2["more"] and not wrong
              and not hidden_ and len(drawings) == 2 and all(d_ in g2["ids"] for d_ in drawings),
              f"first {len(g1['ids'])}, then {len(g2['ids'])}; in order {g2['ids'] == gal_want}; wrong {wrong[:3]};"
              f" face or link-only shown {hidden_}")
        links = {}
        ctx, pg = browser_as(b, kai, "phone", "light")
        for key, sel, want in (("post", f'.gal-tile[data-post="{T["posts"][-2]}"]', f"/social/p/{T['posts'][-2]}"),
                               ("drawing", f'.gal-tile[data-drawing="{drawings[1]}"]', f"/social/b/{drawings[1]}")):
            try:
                pg.goto(BASE + "/social/@tabpia/gallery")
                one = pg.evaluate(ONELINK, sel)
                pg.touchscreen.tap(*one["mid"])
                links[key] = (one, follow_to(pg, "/social/@tabpia/gallery"), want)
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                links[key] = ({"stopped": str(exc).splitlines()[0][:120]}, None, want)
        close_ctx(ctx, pg)
        check("each tile is one link, whole (a finger anywhere on it, every 6px, is on that link), and a tap on it opens the"
              " right page: a post's its post (/social/p/…), one shown outside a post its own page (/social/b/…)",
              len(links) == 2 and all(v[0].get("bad") == 0 and v[0].get("n", 0) > 100 and v[1] == v[2] for v in links.values()),
              json.dumps(links))

        # LIKES, Pia's own.
        likes_want = [p for p in reversed(T["liked"]) if p != T["luxp"]]
        ctx, pg = browser_as(b, pia, "desk", "light")
        pg.goto(BASE + "/social/@tabpia/likes")
        l1 = pg.evaluate(PANEL)
        l2 = more_of(pg, "[data-prof-list] > .post-card", tap=False)
        close_ctx(ctx, pg)
        check("Likes, on Pia's own page: the posts she liked, newest liked first (not the order they were posted), her own"
              " among them, as cards; not the drawing she liked outside a post, nor Lux's post now Lux has blocked her;"
              " Load more brings the rest by its cursor, none twice",
              l1["ids"] == likes_want[:20] and l1["more"] and l2["ids"] == likes_want and not l2["more"]
              and T["luxp"] not in l2["ids"] and T["posts"][4] in l2["ids"],
              f"first {len(l1['ids'])} (more {l1['more']}), then {len(l2['ids'])}; in order {l2['ids'] == likes_want};"
              f" Lux's there {T['luxp'] in l2['ids']}")
        gone, down = T["order"][0], T["order"][1]
        un = like_it(pia, f"/p/{gone}", liked=False)
        db("update social_posts set taken_down_at = ? where public_id = ?", ("2026-11-14 12:00:00.000000", down), write=True)
        pc = pia.client()
        pc.get("/social/")
        muted = pc.post_json("/social/@tabkai/mute", {})[0]
        ctx, pg = browser_as(b, pia, "desk", "light")
        pg.goto(BASE + "/social/@tabpia/likes")
        l3 = more_of(pg, "[data-prof-list] > .post-card", tap=False)
        close_ctx(ctx, pg)
        unmuted = pc.post_json("/social/@tabkai/unmute", {})[0]
        db("update social_posts set taken_down_at = NULL where public_id = ?", (down,), write=True)
        check("...a like taken back leaves it, a post taken down leaves it, and a mute changes nothing there (her likes of"
              " Kai's posts stay while she mutes him: what you go to stays)",
              un == 200 and muted == 200 and unmuted == 200
              and l3["ids"] == [p for p in likes_want if p not in (gone, down)],
              f"unliked {un}, muted {muted}; {len(l3['ids'])} now; the two gone {[x in l3['ids'] for x in (gone, down)]};"
              f" Kai's still there {sum(1 for x in l3['ids'] if x in T['kais'])}")

        # DRAFTS, Pia's own: the tiles, and the editors they open.
        ctx, pg = browser_as(b, pia, "phone", "light")
        pg.goto(BASE + "/social/@tabpia/drafts")
        drafts_ = pg.evaluate("""() => [...document.querySelectorAll('[data-prof-list] > .gal-tile')].map(a => {
            const pic = a.querySelector('.gal-pic'), r = pic.getBoundingClientRect(), img = a.querySelector('img'), b = a.querySelector('.gal-by b');
            return { id: a.getAttribute('data-draft'), kind: a.getAttribute('data-kind'), href: a.getAttribute('href'),
                     src: img ? img.getAttribute('src').slice(0, 23) : null, fit: img ? getComputedStyle(img).objectFit : null,
                     chip: (a.querySelector('.gal-dur') || {}).innerText, pen: !!a.querySelector('.gal-dur svg'),
                     title: b ? b.textContent : null, weight: b ? getComputedStyle(b).fontWeight : null,
                     line: (a.querySelector('.gal-when') || {}).textContent, ratio: r.width / r.height }; })""")
        close_ctx(ctx, pg)
        tg = T["tag"]
        want_d = [(T["snail"], "pad", f"/skribl-pad?draft={T['snail']}", f"A snail for Kai {tg}", "Pad · saved just now"),
                  (T["bike"], "flip", f"/flip?draft={T['bike']}", f"The bike, half done {tg}", "Flip · saved just now")]
        check("Drafts, on Pia's own page: the drafts on her account and nobody else's, newest saved first (the snail, saved"
              " again after the bike), each a tile of the Gallery's shape: its own small picture whole on the paper,"
              " \"✎ Draft\" where the ▶ sits, its title (600) and \"Pad · saved just now\" (or Flip) under it, one link"
              " to the editor that made it with ?draft=<id>",
              [(d_["id"], d_["kind"], d_["href"], d_["title"], d_["line"]) for d_ in drafts_] == want_d
              and all(d_["src"] == "data:image/jpeg;base64," and d_["fit"] == "contain" and (d_["chip"] or "").strip() == "Draft"
                      and d_["pen"] and d_["weight"] == "600" and abs(d_["ratio"] - 650 / 486) <= 0.01 for d_ in drafts_),
              json.dumps(drafts_))
        opened = {}
        for key, did, path, read in (("pad", T["snail"], "/skribl-pad", "strokes.length"),
                                     ("flip", T["bike"], "/flip", "serializeFlip({ recipes: true }).frames.length")):
            ctx, pg = browser_as(b, pia, "phone", "light")
            try:
                pg.goto(BASE + "/social/@tabpia/drafts")
                # The tile's own address, as a new tab opens it (a tap is section 20's).
                pg.goto(BASE + pg.get_attribute(f'.gal-tile[data-draft="{did}"]', "href"))
                pg.wait_for_url(lambda u, p=path: urllib.parse.urlsplit(u).path == p, timeout=20000)
                pg.wait_for_function("(id) => !!window.SkriblSavedDrafts && window.SkriblSavedDrafts.current() === id",
                                     arg=did, timeout=20000)
                opened[key] = pg.evaluate("() => ({ current: SkriblSavedDrafts.current(), name: window.SkriblName ? SkriblName.get() : null,"
                                          " at: location.pathname + location.search, drawn: " + read + " })")
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                opened[key] = {"stopped": str(exc).splitlines()[0][:160]}
            close_ctx(ctx, pg)
        check("a draft's own address (the tile's link, as a new tab opens it) opens it to keep drawing, as the editors'"
              " own Your drafts does: the Pad at its address,"
              " ?draft= gone once read, the draft open (the Pad's own draft, named as it is, its drawing on the canvas);"
              " a Flip draft in Flip the same way, its three pages there",
              opened.get("pad", {}).get("current") == T["snail"] and opened["pad"].get("at") == "/skribl-pad"
              and opened["pad"].get("name") == f"A snail for Kai {tg}" and (opened["pad"].get("drawn") or 0) > 0
              and opened.get("flip", {}).get("current") == T["bike"] and opened["flip"].get("at") == "/flip"
              and opened["flip"].get("name") == f"The bike, half done {tg}" and opened["flip"].get("drawn") == 3,
              json.dumps(opened))

        # THE READS ON THEIR INDEXES (docs/SOCIAL-SITE.md section 3: every new
        # query's plan checked in its suite): Likes on the likes' own index for
        # who liked, newest first; Posts on the posts' own index for one
        # person's, newest first.
        PROBE = r"""
import json
from sqlalchemy import event, select
from app import app, db
from social import likes, posts
from social.models import Person
seen = []
def keep(conn, cursor, statement, params, context, executemany):
    if statement.lstrip().upper().startswith("SELECT"):
        seen.append((statement, params))
out = {}
with app.test_request_context("/social/@tabpia"):
    pia = db.session.execute(select(Person).where(Person.handle_key == "tabpia")).scalar_one()
    for key, table, fn in (("likes", "FROM social_likes", lambda: likes.liked_page(pia)),
                           ("posts", "FROM social_posts", lambda: posts.person_page(pia, pia))):
        seen.clear()
        event.listen(db.engine, "before_cursor_execute", keep)
        fn()
        event.remove(db.engine, "before_cursor_execute", keep)
        st, pr = next((s, p) for s, p in seen if table in s)
        out[key] = [r[3] for r in db.session.connection().exec_driver_sql("EXPLAIN QUERY PLAN " + st, pr).fetchall()]
print("PLAN " + json.dumps(out))
"""
        pr = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
        plans = next((json.loads(ln[5:]) for ln in pr.stdout.splitlines() if ln.startswith("PLAN ")), {})
        check("the tabs' reads are on their indexes: Likes by who liked, newest first (ix_social_likes_person_created),"
              " sorting no more than likes made in the same moment; Posts one person's, newest first"
              " (ix_social_posts_person_created)",
              any("ix_social_likes_person_created" in x for x in plans.get("likes", []))
              and not any("TEMP B-TREE FOR ORDER BY" in x for x in plans.get("likes", []))
              and any("ix_social_posts_person_created" in x for x in plans.get("posts", [])),
              f"{plans or pr.stderr[-300:]}")

        # NOTHING THERE YET, KINDLY: Ola, who has nothing, and Kai at her page.
        empty = {}
        for path, who, label in (("", ola, "own posts"), ("/gallery", ola, "own gallery"), ("/likes", ola, "own likes"),
                                 ("/drafts", ola, "own drafts"), ("", kai, "Kai's view, posts"),
                                 ("/gallery", kai, "Kai's view, gallery")):
            ctx, pg = browser_as(b, who, "phone", "light")
            pg.goto(BASE + "/social/@tabola" + path)
            empty[label] = pg.evaluate(PANEL)
            close_ctx(ctx, pg)
        want_e = {"own posts": "No posts yet. Tap the pencil to share one, and your posts show up here.",
                  "own gallery": "No drawings here yet. Share one in a post, and it shows up here.",
                  "own likes": "Nothing liked yet. Tap the heart on a post you love, and it’s kept here. Only you can"
                               " see your likes.",
                  "own drafts": "No drafts yet. To finish a drawing later, open ⋯ in the Pad or Flip and tap Save. It"
                                " waits here for you.",
                  "Kai's view, posts": "No posts from Ola yet. When Ola shares one, it shows up here.",
                  "Kai's view, gallery": "No drawings from Ola yet. When Ola shares one, it shows up here."}
        check("every tab says kindly when it holds nothing, in its own words: on your own page what puts something there,"
              " on anybody else's that it comes when they share one; and no Load more",
              all((empty.get(k) or {}).get("none") == v and not empty[k]["ids"] and not empty[k]["more"]
                  for k, v in want_e.items()),
              json.dumps({k: (v or {}).get("none") for k, v in empty.items()}))
        # POSTS HOLDS THEIR REPOSTS (the reposts mock, the owner's "All yes", Nov
        # 14): merged with their posts, newest first, each the original's own
        # card with the line at its top; on your own page "You reposted".
        rae = _people.get("tabrae") or member(b, "tabrae", "Rae Lind")
        rown = site_post(rae, "Rae's own, before her repost", tab_drawing(seed=80))
        rc = rae.client()
        rc.get(f"/social/p/{T['kais'][0]}")
        st_r = rc.post_json(f"/social/p/{T['kais'][0]}/repost", {"reposted": True})[0]
        LINES = """() => [...document.querySelectorAll('[data-prof-list] > .post-card')].map(c => {
            const by = c.querySelector(':scope > .rp-by'); return [c.getAttribute('data-post'), c.getAttribute('data-handle'),
            by ? by.textContent.trim() : null]; })"""
        views = {}
        for who_, tag_ in ((kai, "Kai's view"), (rae, "her own")):
            ctx, pg = browser_as(b, who_, "phone", "light")
            pg.goto(BASE + "/social/@tabrae")
            pg.wait_for_timeout(600)
            views[tag_] = pg.evaluate(LINES)
            close_ctx(ctx, pg)
        check("Posts holds their reposts too, merged with their posts, newest first: Kai's post as his own card with"
              " \"Rae Lind reposted\" at its top (\"You reposted\" on her own page), then her own post",
              st_r == 200 and views.get("Kai's view") == [[T["kais"][0], "tabkai", "Rae Lind reposted"], [rown, "tabrae", None]]
              and views.get("her own") == [[T["kais"][0], "tabkai", "You reposted"], [rown, "tabrae", None]],
              json.dumps(views))

    # ------------------------------------------------------------------ 17
    # THE TABS' WORDS, READ ON THE PAINT (WORKING-AGREEMENTS, "Contrast and
    # consistency"): the strip and every tab's panel, scrolled to the top of
    # the screen, with the suite's own reader.
    if part(17, "the tabs' words: 4.5:1 on what is painted behind them, every control 44px; phone and desk, light and dark"):
        T = tab_people(b)
        pia, kai, ola = T["pia"], T["kai"], T["ola"]
        looks = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                for who, path, label in ((pia, "/social/@tabpia", "own Posts"), (pia, "/social/@tabpia/gallery", "own Gallery"),
                                         (pia, "/social/@tabpia/likes", "own Likes"), (pia, "/social/@tabpia/drafts", "own Drafts"),
                                         (pia, "/social/@tabpia/bookmarks", "own Bookmarks"),
                                         (ola, "/social/@tabola/bookmarks", "empty Bookmarks"),
                                         (kai, "/social/@tabpia", "Kai's view, Posts"),
                                         (None, "/social/@tabpia/gallery", "signed out, the Gallery"),
                                         (ola, "/social/@tabola/likes", "empty Likes"), (ola, "/social/@tabola/drafts", "empty Drafts"),
                                         (kai, "/social/@tabola", "Kai's view, empty Posts")):
                    ctx, pg = browser_as(b, who, screen, scheme, reduced=True)
                    pg.goto(BASE + path)
                    pg.evaluate("() => { const s = document.querySelector('[data-prof-tabs]');"
                                " if (s) window.scrollTo(0, s.getBoundingClientRect().top + scrollY - 8); }")
                    pg.wait_for_timeout(400)
                    looks[(screen, scheme, label)] = pg.evaluate(READ, ".prof-tabs, .prof-swap")
                    close_ctx(ctx, pg)
        low = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["low"]]
        reads = sum(v["read"] for v in looks.values())
        lowest = min(((v["lowest"], " ".join(k)) for k, v in looks.items()), default=(0, "nothing"))
        check("every word on the strip and in every tab (a card's, a tile's, a draft's chip, title and when, each tab's kind"
              " words) reads at 4.5:1 or more on what is painted behind it: phone and desk, light and dark, yours and"
              " somebody else's",
              reads >= 300 and not low, f"{reads} read, the lowest {lowest}; under 4.5: {low[:5]}")
        small = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["small"]]
        check("every link and button on them is 44px or more each way: a tab, a tile, a card's row, Load more",
              not small, "; ".join(small[:6]))

    # ------------------------------------------------------------------ 18
    # DELETE FROM YOUR OWN PAGE (the owner's "Yes", Nov 14, to #898's question):
    # deleting a post from your profile keeps you there, the post folding away
    # where it was, instead of landing on Home with its note; from a post's own
    # page it still lands there (verify_socialposts 5). Read on every frame from
    # the tap on Delete post: the card fades, then its room closes and the next
    # card rises into its place over many frames, never in one; under Reduce
    # Motion it fades, and its room goes only once it can't be seen.
    if part(18, "delete from your own page: you stay, the post folds away there"):
        mo = _people.get("delmo") or member(b, "delmo", "Mo Delaney")
        tag = secrets.token_hex(3)
        mos = [site_post(mo, f"Mo's post {k} {tag}", tab_drawing(seed=80 + k)) for k in range(6)]
        made18 = all(mos)
        DSAMPLE = """([sel, nextSel, ms]) => { window.__df = []; const c = document.querySelector(sel), n = document.querySelector(nextSel), t0 = performance.now();
          const step = () => { window.__df.push({ t: Math.round(performance.now() - t0), there: c.isConnected,
              op: c.isConnected ? +getComputedStyle(c).opacity : null, next: n ? Math.round(n.getBoundingClientRect().top * 10) / 10 : null,
              doc: n ? Math.round((n.getBoundingClientRect().top + scrollY) * 10) / 10 : null,
              y: Math.round(scrollY), at: location.pathname + location.search });
            if (performance.now() - t0 < ms) requestAnimationFrame(step); };
          requestAnimationFrame(step); }"""

        def delete_one(pg_, pid, nxt):
            """Delete post `pid` from its card's ⋯ on the page; the frames from the tap on Delete post."""
            sel, nsel = f'[data-prof-list] > .post-card[data-post="{pid}"]', f'[data-prof-list] > .post-card[data-post="{nxt}"]'
            pg_.locator(sel + " [data-post-menu]").scroll_into_view_if_needed(timeout=5000)
            pg_.locator(sel + " [data-post-menu]").tap(timeout=5000)
            pg_.wait_for_timeout(600)
            pg_.locator("#postSheet [data-act=delete]").tap(timeout=5000)
            pg_.wait_for_timeout(600)
            pg_.evaluate(DSAMPLE, [sel, nsel, 2200])
            pg_.locator("[data-delete-now]").tap(timeout=5000)
            pg_.wait_for_timeout(2600)
            return pg_.evaluate("() => window.__df")

        def judged(fs):
            """What the frames say: the fade, the room, and whether anything jumped.

            THE NEXT CARD IS READ WHERE IT IS ON THE PAGE (its top plus the
            scroll), not on the screen. Deleting the last card but one at the
            foot of a page makes the page shorter, and the browser pulls the
            scroll back to the new end in the same frame: on the screen the
            next card then moves by its room LESS that pull, which is only how
            far down the page happened to be. It read 130.7 one day and 98.7
            the next (the colour audit's fix E keeps a control the test scrolls
            to clear of the bar, so the page started 32px further down), with
            the room 440.7 both times. The room is the card's to close; the
            scroll is the browser's."""
            seen = [f for f in fs if f["there"] and f["op"] is not None]
            ops = [f["op"] for f in seen]
            tops = [f["doc"] for f in fs if f.get("doc") is not None]
            steps = [abs(b_ - a_) for a_, b_ in zip(tops, tops[1:])]
            way = abs(tops[-1] - tops[0]) if tops else 0
            # where the next card was while the deleted one could still be seen
            while_seen = [f["doc"] for f in fs if f["there"] and f["op"] is not None and f["op"] > 0.03 and f.get("doc") is not None]
            return {"fading": len([o for o in ops if 0.03 < o < 0.97]), "gone": bool(fs) and not fs[-1]["there"],
                    "way": round(way, 1), "moving": len([x for x in steps if x > 0.3]), "step": round(max(steps or [0]), 1),
                    "still while seen": bool(while_seen) and max(while_seen) - min(while_seen) <= 0.5,
                    "at": sorted({f["at"] for f in fs}), "scroll": sorted({f["y"] for f in fs})[:1] + sorted({f["y"] for f in fs})[-1:],
                    "scrolled": [fs[0]["y"], fs[-1]["y"]] if fs else []}
        SAID_INK = """() => { const rgba = s => { const m = (s.match(/[\\d.]+/g) || []).map(Number); return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1]; };
          const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                             return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
          const ground = e => { const layers = []; for (let n = e; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor);
              if (b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
            let g = [255, 255, 255]; for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; g = [0, 1, 2].map(k => l[k] * l[3] + g[k] * (1 - l[3])); }
            return g; };
          const out = { read: 0, low: [], lowest: 99, words: [], toast: 0 };
          /* THE SITE'S TOAST says it now (the owner's "Yes", Nov 14): its words
             take no tap, so they are made hit-testable to ask what is painted. */
          const toast = document.querySelector('.mu-toast.is-up');
          if (toast) toast.style.pointerEvents = 'auto';
          document.querySelectorAll('[data-page-say], [data-prof-none], .mu-toast.is-up .mu-toast-words').forEach(e => {
            if (e.hidden || !e.getClientRects().length || !e.textContent.trim()) return;
            if (!e.closest('.mu-toast')) e.scrollIntoView({ block: 'center', behavior: 'instant' });
            const r = e.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            if (!at || !(at === e || e.contains(at))) { out.low.push('not painted: ' + e.textContent.trim().slice(0, 24)); return; }
            const a = lum(rgba(getComputedStyle(e).color)), b = lum(ground(e)), k = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
            out.read++; out.lowest = Math.min(out.lowest, Math.round(k * 100) / 100); out.words.push(e.textContent.trim().slice(0, 40));
            if (e.closest('.mu-toast')) out.toast++;
            if (k < 4.5) out.low.push(e.textContent.trim().slice(0, 24) + ' ' + k.toFixed(2)); });
          if (toast) toast.style.pointerEvents = '';
          return out; }"""

        def said_read(pg_):
            """What the page said, read where it is painted: scrolled to, against what is behind it."""
            return pg_.evaluate(SAID_INK)
        gone18, inks18 = {}, {}
        ctx, pg = browser_as(b, mo, "phone", "light")
        try:
            pg.goto(BASE + "/social/@delmo")
            pg.wait_for_selector(f'[data-prof-list] > .post-card[data-post="{mos[4]}"]', timeout=15000)
            fs = delete_one(pg, mos[4], mos[3])
            gone18["glide"] = judged(fs)
            gone18["after"] = pg.evaluate("""(ids) => { const t = document.querySelector('.mu-toast'), up = !!t && !t.hidden && t.classList.contains('is-up');
              const r = up ? t.getBoundingClientRect() : null, bar = document.querySelector('nav.nav'), br = bar ? bar.getBoundingClientRect() : null;
              return { at: location.pathname + location.search,
              cards: [...document.querySelectorAll('[data-prof-list] > .post-card')].map(c => c.getAttribute('data-post')),
              note: !!document.querySelector('.note'), said: (document.querySelector('[data-page-say]') || {}).textContent || null,
              toast: up ? { words: t.querySelector('[data-mute-said]').textContent, undo: !t.querySelector('[data-mute-undo]').hidden,
                            eye: getComputedStyle(t.querySelector('.ic')).display !== 'none', top: Math.round(r.top), bottom: Math.round(r.bottom),
                            vh: innerHeight, bar: br ? Math.round(br.top) : null } : null,
              focus: document.activeElement ? [document.activeElement.className, (document.activeElement.closest('.post-card') || { getAttribute: () => null }).getAttribute('data-post')] : null,
              sheet: document.getElementById('deleteSheet').hidden, inert: !!document.querySelector('#main[inert]') }; }""", mos)
            inks18["phone light"] = said_read(pg)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the rows' red
            gone18["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        rows18 = db("select public_id from social_posts where public_id in (?, ?, ?, ?, ?, ?)", tuple(mos))
        # ON A DESK, light and dark: the words read where they are painted.
        for scheme, pid, nxt in (("light", mos[5], mos[3]), ("dark", mos[3], mos[2])):
            ctx, pg = browser_as(b, mo, "desk", scheme)
            try:
                pg.goto(BASE + "/social/@delmo")
                pg.wait_for_selector(f'[data-prof-list] > .post-card[data-post="{pid}"]', timeout=15000)
                sel_ = f'[data-prof-list] > .post-card[data-post="{pid}"] [data-post-menu]'
                pg.locator(sel_).scroll_into_view_if_needed(timeout=5000)
                pg.click(sel_, timeout=5000)
                pg.wait_for_timeout(600)
                pg.click("#postSheet [data-act=delete]", timeout=5000)
                pg.wait_for_timeout(600)
                pg.click("[data-delete-now]", timeout=5000)
                pg.wait_for_timeout(1600)
                inks18["desk " + scheme] = dict(said_read(pg), at=urllib.parse.urlsplit(pg.url).path)
            except Exception as exc:  # noqa: BLE001
                inks18["desk " + scheme] = {"stopped": str(exc).splitlines()[0][:120]}
            close_ctx(ctx, pg)
        g = gone18.get("glide") or {}
        a = gone18.get("after") or {}
        ts18 = a.get("toast") or {}
        check("DELETED FROM YOUR OWN PAGE, YOU STAY THERE: Delete post on a card of your Posts tab, and the page is still"
              " yours (never Home, never its note), the post gone (its row too), the cards around it as they were, and"
              " focus on the next card's ⋯; ITS WORDS IN THE SITE'S TOAST (the owner's \"Yes\", Nov 14), near the"
              " finger: \"Your post is gone, its drawing with it.\" (Home's own words, a status a screen reader hears),"
              " no Undo (a delete is final) and no eye, in view above the bar in the screen's lower half; the tab's"
              " status line says nothing",
              made18 and "stopped" not in gone18 and g.get("at") == ["/social/@delmo"] and a.get("at") == "/social/@delmo"
              and not a.get("note") and a.get("cards") == [mos[5], mos[3], mos[2], mos[1], mos[0]]
              and sorted(r_[0] for r_ in rows18) == sorted([mos[0], mos[1], mos[2], mos[3], mos[5]])
              and not (a.get("said") or "").strip() and ts18.get("words") == "Your post is gone, its drawing with it."
              and ts18.get("undo") is False and ts18.get("eye") is False and ts18.get("bar") is not None
              and ts18.get("bottom", 9999) <= ts18["bar"] - 8 and ts18.get("top", -1) >= ts18.get("vh", 0) / 2
              and (a.get("focus") or [None, None])[1] == mos[3]
              and "post-more" in ((a.get("focus") or [""])[0] or "") and a.get("sheet") and not a.get("inert"),
              f"{gone18}; rows left {rows18}")
        check("...and it folds away there, read on every frame: it fades, the next card still while it can be seen; then"
              " its room closes and the next card rises into its place over many frames, never in one, the page itself"
              " never scrolling",
              g.get("gone") and g.get("fading", 0) >= 4 and g.get("still while seen") and g.get("way", 0) >= 100
              and g.get("moving", 0) >= 5 and g.get("step", 999) <= 0.4 * g.get("way", 0)
              and len(set(g.get("scroll") or [0, 1])) == 1, json.dumps(g))
        # UNDER REDUCE MOTION: it fades where it is, and the room goes at once,
        # only once it can't be seen; the last one gone, the tab's own words.
        ctx, pg = browser_as(b, mo, "phone", "dark", reduced=True)
        rm = {}
        try:
            pg.goto(BASE + "/social/@delmo")
            pg.wait_for_selector(f'[data-prof-list] > .post-card[data-post="{mos[1]}"]', timeout=15000)
            rm["glide"] = judged(delete_one(pg, mos[1], mos[0]))
            inks18["phone dark"] = said_read(pg)
            for pid in (mos[2], mos[0]):
                pg.locator(f'[data-prof-list] > .post-card[data-post="{pid}"] [data-post-menu]').tap(timeout=5000)
                pg.wait_for_timeout(600)
                pg.locator("#postSheet [data-act=delete]").tap(timeout=5000)
                pg.wait_for_timeout(600)
                pg.locator("[data-delete-now]").tap(timeout=5000)
                pg.wait_for_timeout(1400)
            rm["last"] = pg.evaluate("""() => { const n = document.querySelector('[data-prof-none]');
              return { at: location.pathname, cards: document.querySelectorAll('[data-prof-list] > .post-card').length,
                       words: n && !n.hidden ? n.textContent.trim() : null, op: n ? +getComputedStyle(n).opacity : null,
                       focus: document.activeElement ? document.activeElement.className : null }; }""")
            inks18["phone dark, the tab's words"] = said_read(pg)
        except Exception as exc:  # noqa: BLE001
            rm["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        rg = rm.get("glide") or {}
        last = rm.get("last") or {}
        check("...under Reduce Motion it fades where it is, nothing moving while it can be seen, and its room goes at once"
              " once it can't (the next card put there in one step); the last one gone, you are still on your page and"
              " the tab says its own kind words, focus on the tab",
              "stopped" not in rm and rg.get("gone") and rg.get("fading", 0) >= 4 and rg.get("still while seen")
              and rg.get("moving") == 1 and rg.get("way", 0) >= 100 and rg.get("at") == ["/social/@delmo"]
              and last.get("at") == "/social/@delmo" and last.get("cards") == 0
              and last.get("words") == "No posts yet. Tap the pencil to share one, and your posts show up here."
              and last.get("op") == 1 and "prof-tab" in (last.get("focus") or "")
              and not db("select 1 from social_posts where person_id = (select id from social_people where handle_key = 'delmo')"),
              json.dumps(rm))
        check("...and what the page says reads at 4.5:1 or more on what is painted behind it (\"Your post is gone, its"
              " drawing with it.\" in the site's toast, the tab's kind words once the last is gone), a touch phone and a"
              " desk, light and dark, the desk too staying on the page",
              all(v.get("read", 0) >= 1 and not v.get("low") for v in inks18.values()) and len(inks18) == 5
              and all(inks18[k].get("toast", 0) >= 1 for k in ("phone light", "desk light", "desk dark", "phone dark"))
              and all(inks18[k].get("at") == "/social/@delmo" for k in ("desk light", "desk dark")),
              json.dumps({k: (v.get("read"), v.get("toast"), v.get("lowest"), v.get("low"), v.get("at"), v.get("stopped"))
                          for k, v in inks18.items()}))

        # NEVER OVER A BUTTON SOMEONE IS PRESSING FAST (WORKING-AGREEMENTS: a
        # toast never covers a button someone is pressing fast). A delete's next
        # press is the next card's ⋯, and the next card rises into the place of
        # the one deleted. Kit deletes a post whose ⋯ sits where the toast would
        # rise (its middle 105px above the screen's foot, a touch phone): the
        # toast rises just above it instead, and every ⋯ in view takes its own
        # tap (what is painted at its middle, the toast made hit-testable).
        kit = _people.get("delkit") or member(b, "delkit", "Kit Arden")
        kits = [site_post(kit, f"Kit's post {k} {tag}", tab_drawing(seed=90 + k)) for k in range(4)]
        clear18 = {}
        ctx, pg = browser_as(b, kit, "phone", "light")
        try:
            pg.goto(BASE + "/social/@delkit")
            msel = f'[data-prof-list] > .post-card[data-post="{kits[2]}"] [data-post-menu]'
            pg.wait_for_selector(msel, timeout=15000)
            pg.evaluate("""(s) => { const m = document.querySelector(s).getBoundingClientRect();
                window.scrollBy(0, (m.top + m.height / 2) - (innerHeight - 105)); }""", msel)
            pg.wait_for_timeout(300)
            clear18["menu"] = pg.evaluate("(s) => Math.round(document.querySelector(s).getBoundingClientRect().top + 22)", msel)
            pg.locator(msel).tap(timeout=5000)
            pg.wait_for_timeout(600)
            pg.locator("#postSheet [data-act=delete]").tap(timeout=5000)
            pg.wait_for_timeout(600)
            pg.locator("[data-delete-now]").tap(timeout=5000)
            pg.wait_for_function(TOAST_UP, arg="Your post is gone, its drawing with it.", timeout=8000)
            pg.wait_for_timeout(450)
            clear18.update(pg.evaluate(CLEAR_OF, "[data-prof-list] .post-card [data-post-menu]"))
            clear18["next"] = pg.evaluate("""(id) => { const m = document.querySelector('[data-prof-list] > .post-card[data-post="' + id + '"] [data-post-menu]');
                return m ? Math.round(m.getBoundingClientRect().top + 22) : null; }""", kits[1])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            clear18["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        check("...and NEVER OVER A BUTTON SOMEONE IS PRESSING FAST: a post deleted whose ⋯ sat where the toast rises"
              " (just above the bar, a touch phone), the next card's ⋯ rising into its place, and the toast rises just"
              " above it instead; every ⋯ in view takes its own tap (what is painted at its middle), the toast in view",
              all(kits) and "stopped" not in clear18 and abs(clear18.get("menu", 0) - (clear18.get("vh", 0) - 105)) <= 2
              and abs((clear18.get("next") or 0) - clear18.get("menu", -99)) <= 2
              and clear18.get("lifted", 0) > 0 and clear18.get("seen", 0) >= 1 and not clear18.get("under")
              and not clear18.get("covered") and clear18.get("toast", [-1])[0] >= 0,
              json.dumps(clear18))

    # ------------------------------------------------------------------ 19
    # THE EYE, IN VIEW, ON YOUR OWN GALLERY TAB (the owner's "Yes, the eye in
    # view", Nov 14; the tile-eye mock). Eli shares three posts and a drawing
    # outside a post, keeps one link-only (on the Pad's dark), draws a face and
    # answers Noa's post with a drawing. Her own Gallery tab holds the five,
    # each with an eye at its top right (the link-only one hidden: crossed,
    # "Hidden", faded), never the face or the answer's drawing; one tap hides
    # a drawing from the Gallery and the site's toast says so with Undo; a
    # post's by the site's flag (the post stays on Home and her Posts), one
    # outside a post by its visibility in Skribl. Nobody else sees the eye.
    if part(19, "the eye on your own Gallery tab: hide a drawing from the Gallery, show it again"):
        eli = _people.get("eyeeli") or member(b, "eyeeli", "Eli Marsh")
        noa = _people.get("eyenoa") or member(b, "eyenoa", "Noa Vance")
        tag = secrets.token_hex(3)
        n1 = site_post(noa, f"Noa's {tag}", tab_drawing(seed=190))
        p1 = site_post(eli, f"Eli's first {tag}", tab_drawing(seed=191))
        d1 = post_skribl(eli, f"Eli's drawing {tag}")
        p2 = site_post(eli, f"Eli's second {tag}", tab_drawing(seed=192))
        l1 = post_skribl(eli, f"Eli's link-only {tag}", visibility=None, ground="#0d0f14")
        p3 = site_post(eli, f"Eli's third {tag}", tab_drawing(seed=193))
        face19 = post_skribl(eli, f"Eli's face {tag}", visibility=None)
        db("update social_people set face_id = ?, face_w = 816, face_h = 612 where handle_key = 'eyeeli'", (face19,), write=True)
        ec = eli.client()
        ec.get(f"/social/p/{n1}")
        _, jc = ec.post_json(f"/social/p/{n1}/comments", {"words": f"Eli's answer {tag}", "payload": tab_drawing(seed=194)})
        answer19 = (db("select skribl_id from social_comments where public_id = ?",
                       ((jc or {}).get("comment") if isinstance(jc, dict) else "",)) or [(None,)])[0][0]
        made19 = all([n1, p1, d1, p2, l1, p3, face19, answer19])
        skr = {k: (db("select skribl_id from social_posts where public_id = ?", (v,)) or [(None,)])[0][0]
               for k, v in (("p1", p1), ("p2", p2), ("p3", p3))}
        GAL = "/social/@eyeeli/gallery"
        own_ids = [p3, l1, p2, d1, p1]

        def flag(pid):
            return (db("select gallery_hidden_at from social_posts where public_id = ?", (pid,)) or [("gone",)])[0][0]

        def vis(sid):
            return (db("select visibility from skribl_posts where public_id = ?", (sid,)) or [("gone",)])[0][0]

        def cell(key, kind="post"):
            return f'[data-prof-list] > .gal-cell:has(.gal-tile[data-{kind}="{key}"])'

        def where(key, href):
            """Where a drawing is shown: the Gallery of everyone (signed out, by the section's word), the first
            visit, Noa's view of Eli's Gallery, Home's Everyone signed out, Eli's own Posts."""
            anon = Client()
            anon.get("/social/")

            def html_of(cl, path):
                try:
                    return json.loads(cl._req("GET", path)[2]).get("html") or ""
                except ValueError:
                    return ""
            out = {}
            out["gallery"] = f'href="{href}"' in html_of(anon, "/social/explore/more?show=everyone&sort=new&q=" + urllib.parse.quote(tag))
            out["first visit"] = f'href="{href}"' in anon.get("/social/")[2]
            out["Noa's view"] = f'href="{href}"' in noa.client().get(GAL)[2]
            if href.startswith("/social/p/"):
                out["home"] = f'data-post="{key}"' in html_of(anon, "/social/feed?show=everyone")
                out["her posts"] = f'data-post="{key}"' in html_of(eli.client(), "/social/@eyeeli/more?tab=posts")
            return out

        # 1. THE EYE ON EACH OF HER TILES, AND THEIRS ALONE.
        looks19 = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, eli, screen, scheme)
                try:
                    pg.goto(BASE + GAL)
                    pg.wait_for_selector("[data-prof-list] > .gal-cell", timeout=15000)
                    pg.wait_for_timeout(300)
                    looks19[(screen, scheme)] = pg.evaluate(EYES19)
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                    looks19[(screen, scheme)] = [{"stopped": str(exc).splitlines()[0][:120]}]
                close_ctx(ctx, pg)
        bad19 = []
        for k, tiles in looks19.items():
            if [x.get("id") for x in tiles] != own_ids:
                bad19.append(f"{k}: tiles {[x.get('id') for x in tiles]}")
                continue
            for x in tiles:
                hid = x["id"] == l1
                good = (x["hidden"] == hid and x["pressed"] == ("false" if hid else "true") and x["painted"]
                        and x["eye"][1] == 44 and x["eye"][0] >= 44 and (hid or x["eye"][0] == 44)
                        and x["chip"][:3] == [30, 13, 13] and (hid or x["chip"][3] == 30)
                        and x["word"] == ["Hidden", 1 if hid else 0] and x["icons"] == ([0, 1] if hid else [1, 0])
                        and x["plate"] == (0.55 if hid else 1) and x["glass"] == "rgba(255, 255, 255, 0.82)"
                        and x["ink"] == "rgb(58, 36, 168)" and (x["name"] or "").startswith("In the Gallery: ")
                        and (x["label"] or "").endswith(", hidden from the Gallery") == hid)
                if not good:
                    bad19.append(f"{k}: {x}")
        check("THE EYE ON YOUR OWN TILES: on Eli's own Gallery tab each tile, her posts' and the drawings she showed"
              " outside a post, the link-only one too, has its eye at the top right on the ▶'s glass, painted, 44px to a"
              " finger, its chip 30px and 13px in; open in the Gallery, pressed; the link-only one hidden from it: the eye"
              " crossed, \"Hidden\" beside it, the drawing faded to 55%, its link saying so; never her face or her"
              " answer's drawing: a touch phone and a desk, light and dark",
              made19 and len(looks19) == 4 and not bad19,
              f"made {made19}; {bad19[:3]}")

        # 2. NOBODY ELSE SEES IT, IN THE PAGE OR ITS SOURCE.
        marks = ("data-eye", "gal-eye", "eye.js", "data-eye-words", "Hidden from the Gallery", "data-label-hidden")
        seen19 = {}
        for who, name in ((noa, "Noa"), (None, "signed out")):
            cl = who.client() if who else Client()
            st_, _, html_ = cl.get(GAL)
            st2, _, json_ = cl._req("GET", "/social/@eyeeli/more?tab=gallery")
            seen19[name] = {"status": [st_, st2], "marks": [m for m in marks if m in html_ or m in json_],
                            "tiles": [x for _, x in re.findall(r'<a class="gal-tile" href="/social/([pb])/([^"]+)"', html_)]}
        own_html = eli.client().get(GAL)[2]
        check("...and nobody else sees it, in the page or its source: Noa's view and nobody's hold no eye, no eye's"
              " words, no eye.js, in the page or the tab's own JSON, and not her link-only drawing; her own page has"
              " them all",
              all(v["status"] == [200, 200] and not v["marks"] and v["tiles"] == [p3, p2, d1, p1] for v in seen19.values())
              and all(m in own_html for m in marks), json.dumps(seen19))

        # 3. A POST'S DRAWING, HIDDEN AND SHOWN AGAIN, END TO END (a touch phone).
        post19 = {}
        ctx, pg = browser_as(b, eli, "phone", "light")
        try:
            pg.goto(BASE + GAL)
            pg.wait_for_selector(cell(p2), timeout=15000)
            post19["before"] = where(p2, f"/social/p/{p2}")
            pg.locator(cell(p2) + " .gal-eye").tap()
            pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
            pg.wait_for_timeout(350)
            post19["hidden"] = pg.evaluate(ONE_EYE, cell(p2))
            post19["flag"] = flag(p2) is not None
            post19["then"] = where(p2, f"/social/p/{p2}")
            pg.locator(".mu-toast [data-mute-undo]").tap()
            pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
            pg.wait_for_timeout(350)
            post19["undone"] = pg.evaluate(ONE_EYE, cell(p2))
            post19["flag after"] = flag(p2)
            post19["after"] = where(p2, f"/social/p/{p2}")
            pg.locator(cell(p2) + " .gal-eye").tap()
            pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
            pg.reload()
            pg.wait_for_selector(cell(p2), timeout=15000)
            pg.wait_for_timeout(300)
            post19["reloaded"] = pg.evaluate(ONE_EYE, cell(p2))
            pg.locator(cell(p2) + " .gal-eye").tap()
            pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
            post19["shown again"] = flag(p2)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            post19["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        h_, u_, r_ = post19.get("hidden") or {}, post19.get("undone") or {}, post19.get("reloaded") or {}
        everywhere = {"gallery": True, "first visit": True, "Noa's view": True, "home": True, "her posts": True}
        check("A POST'S DRAWING, HIDDEN FROM THE GALLERY AND SHOWN AGAIN, end to end on a touch phone: one tap, and the eye"
              " crosses and says \"Hidden\", the drawing fades to 55%, the site's own toast says \"Hidden from the"
              " Gallery\" with Undo (its closed eye beside the words); the post's flag set, the drawing out of the Gallery"
              " of everyone, the first visit and Noa's view of her Gallery, while the post stays on Home and in her Posts;"
              " Undo brings it all back (\"Back in the Gallery\"); hidden, it stays hidden through a reload",
              made19 and "stopped" not in post19 and post19.get("before") == everywhere
              and h_.get("hidden") is True and h_.get("pressed") == "false" and h_.get("plate") == 0.55
              and h_.get("word") == ["Hidden", 1] and (h_.get("label") or "").endswith(", hidden from the Gallery")
              and (h_.get("toast") or {}).get("undo") is True and (h_.get("toast") or {}).get("icon") is True
              and post19.get("flag") is True
              and post19.get("then") == {"gallery": False, "first visit": False, "Noa's view": False, "home": True, "her posts": True}
              and u_.get("hidden") is False and u_.get("pressed") == "true" and u_.get("plate") == 1
              and (u_.get("toast") or {}).get("undo") is False and post19.get("flag after") is None
              and post19.get("after") == everywhere
              and r_.get("hidden") is True and r_.get("plate") == 0.55 and post19.get("shown again") is None,
              json.dumps(post19))

        # 4. A DRAWING SHOWN OUTSIDE A POST, AND ONE KEPT LINK-ONLY (a desk, dark).
        draw19 = {}
        ctx, pg = browser_as(b, eli, "desk", "dark")
        try:
            pg.goto(BASE + GAL)
            pg.wait_for_selector(cell(d1, "drawing"), timeout=15000)
            draw19["before"] = (vis(d1), where(d1, f"/social/b/{d1}"))
            pg.click(cell(d1, "drawing") + " .gal-eye")
            pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
            draw19["hidden"] = (vis(d1), where(d1, f"/social/b/{d1}"))
            draw19["its page"] = {"Noa": noa.client().get(f"/social/b/{d1}")[0], "nobody": Client().get(f"/social/b/{d1}")[0],
                                  "Eli": eli.client().get(f"/social/b/{d1}")[0]}
            pg.reload()
            pg.wait_for_selector(cell(d1, "drawing"), timeout=15000)
            pg.wait_for_timeout(300)
            draw19["reloaded"] = pg.evaluate(ONE_EYE, cell(d1, "drawing"))
            pg.click(cell(d1, "drawing") + " .gal-eye")
            pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
            draw19["shown"] = (vis(d1), where(d1, f"/social/b/{d1}"))
            # The toast goes before the next tap, so its words are the next one's.
            pg.wait_for_function("() => document.querySelector('.mu-toast').hidden", timeout=8000)
            pg.click(cell(l1, "drawing") + " .gal-eye")
            pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
            draw19["link-only shown"] = (vis(l1), where(l1, f"/social/b/{l1}"))
            pg.wait_for_timeout(400)
            pg.click(cell(l1, "drawing") + " .gal-eye")
            pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
            draw19["link-only again"] = vis(l1)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            draw19["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        out_ = {"gallery": False, "first visit": False, "Noa's view": False}
        in_ = {"gallery": True, "first visit": True, "Noa's view": True}
        check("A DRAWING SHOWN OUTSIDE A POST, its eye its visibility in Skribl (a desk, dark): hidden, it is link-only"
              " (unlisted), out of the Gallery of everyone, the first visit and Noa's view, its own page hers alone (a"
              " kind 404 to Noa and to nobody); still on her own tab through a reload, hidden; shown, public and back"
              " everywhere; and a drawing kept link-only from the first shows the same way, and hides again",
              made19 and "stopped" not in draw19 and draw19.get("before") == ("public", in_)
              and draw19.get("hidden") == ("unlisted", out_)
              and draw19.get("its page") == {"Noa": 404, "nobody": 404, "Eli": 200}
              and (draw19.get("reloaded") or {}).get("hidden") is True and draw19.get("shown") == ("public", in_)
              and draw19.get("link-only shown") == ("public", in_) and draw19.get("link-only again") == "unlisted",
              json.dumps(draw19))

        # 5. THE TOAST NEVER COVERS AN EYE: one where the toast would rise.
        cov19 = {}
        ctx, pg = browser_as(b, eli, "phone", "light")
        try:
            pg.goto(BASE + GAL)
            pg.wait_for_selector(cell(p1) + " .gal-eye", timeout=15000)
            # The lowest eye the page can bring to where the toast's middle
            # would be (105px above the screen's foot), the page scrolled to it.
            esel = None
            for key, kind in ((p1, "post"), (d1, "drawing"), (p2, "post")):
                s_ = cell(key, kind) + " .gal-eye"
                pg.evaluate("""(s) => { const m = document.querySelector(s).getBoundingClientRect();
                    window.scrollBy(0, (m.top + m.height / 2) - (innerHeight - 105)); }""", s_)
                pg.wait_for_timeout(250)
                at_ = pg.evaluate("(s) => Math.round(document.querySelector(s).getBoundingClientRect().top + 22)", s_)
                if abs(at_ - (pg.evaluate("() => innerHeight") - 105)) <= 2:
                    esel, cov19["eye"], cov19["which"] = s_, at_, key
                    break
            if esel is None:
                raise RuntimeError("no eye could be brought where the toast rises")
            pg.locator(esel).tap()
            pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
            pg.wait_for_timeout(450)
            cov19.update(pg.evaluate(CLEAR_OF, "[data-eye-cell] [data-eye]"))
            pg.evaluate("() => window.scrollBy(0, 40)")
            pg.wait_for_timeout(500)
            cov19["after a scroll"] = pg.evaluate("() => { const t = document.querySelector('.mu-toast'); return t.hidden || !t.classList.contains('is-up'); }")
            pg.locator(esel).tap()
            pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            cov19["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        check("THE TOAST NEVER COVERS AN EYE (WORKING-AGREEMENTS): tapped where the toast would rise (just above the bar,"
              " a touch phone), it rises just above the eye instead, every eye in view taking its own tap (what is"
              " painted at its middle, the toast made hit-testable), the toast in view; and a scroll that brings an eye"
              " under it takes it away",
              "stopped" not in cov19 and abs(cov19.get("eye", 0) - (cov19.get("vh", 0) - 105)) <= 2
              and cov19.get("lifted", 0) > 0 and cov19.get("seen", 0) >= 2 and not cov19.get("under")
              and not cov19.get("covered") and cov19.get("toast", [-1])[0] >= 0 and cov19.get("after a scroll") is True,
              json.dumps(cov19))

        # 6. KIND, NEVER JUMPY: read on every frame from the tap.
        frames19 = {}
        for reduced in (False, True):
            ctx, pg = browser_as(b, eli, "phone", "light", reduced=reduced)
            try:
                pg.goto(BASE + GAL)
                pg.wait_for_selector(cell(p1), timeout=15000)
                pg.locator(cell(p1)).scroll_into_view_if_needed(timeout=5000)
                pg.wait_for_timeout(300)
                pg.evaluate(EFRAMES, [cell(p1), 900])
                pg.locator(cell(p1) + " .gal-eye").tap()
                pg.wait_for_timeout(1100)
                fs = pg.evaluate("() => window.__ef")
                pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
                pg.locator(cell(p1) + " .gal-eye").tap()
                pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
                ws, ops = [f["w"] for f in fs], [f["op"] for f in fs]
                steps = [abs(z - a) for a, z in zip(ws, ws[1:])]
                way = (ws[-1] - ws[0]) if ws else 0
                frames19["reduced" if reduced else "moving"] = {
                    "way": round(way, 1), "moving": len([s for s in steps if s > 0.3]), "step": round(max(steps or [0]), 1),
                    "fading": len([o for o in ops if 0.57 < o < 0.98]), "fstep": round(max([abs(z - a) for a, z in zip(ops, ops[1:])] or [0]), 3),
                    "end": [ws[-1] if ws else None, ops[-1] if ops else None]}
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                frames19["reduced" if reduced else "moving"] = {"stopped": str(exc).splitlines()[0][:160]}
            close_ctx(ctx, pg)
        mv, rd = frames19.get("moving") or {}, frames19.get("reduced") or {}
        check("KIND, NEVER JUMPY, read on every frame from the tap: the eye's chip opens to \"Hidden\" over many frames"
              " (none more than 40% of its way) and the drawing fades over many (none more than a fifth of the way at"
              " once); under Reduce Motion the chip takes its size at once and the drawing still fades",
              mv.get("way", 0) >= 30 and mv.get("moving", 0) >= 6 and mv.get("step", 99) <= 0.4 * mv.get("way", 0)
              and mv.get("fading", 0) >= 4 and mv.get("fstep", 1) <= 0.2 and (mv.get("end") or [0, 0])[1] == 0.55
              and rd.get("way", 0) >= 30 and rd.get("moving") == 1 and rd.get("fading", 0) >= 4
              and rd.get("fstep", 1) <= 0.2 and (rd.get("end") or [0, 0])[1] == 0.55,
              json.dumps(frames19))

        # 7. THE EYE'S INK ON ITS GLASS, READ OFF THE PIXELS UNDER IT (over the
        # Pad's dark, her link-only drawing, and over paper), and the toast's
        # words on what is painted behind them: phone and desk, light and dark.
        INK19 = (58, 36, 168)

        def lum19(c):
            v = [x / 255 for x in c[:3]]
            v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
        glass19, toast19 = {}, {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, eli, screen, scheme, reduced=True)
                try:
                    pg.goto(BASE + GAL)
                    for key, kind in ((l1, "drawing"), (p3, "post")):
                        chip = cell(key, kind) + " .gal-eye-chip"
                        pg.locator(chip).scroll_into_view_if_needed(timeout=5000)
                        pg.evaluate("(s) => document.querySelectorAll(s + ' .gal-eye-ics, ' + s + ' .gal-eye-word').forEach(e => e.style.visibility = 'hidden')", chip)
                        pg.wait_for_timeout(150)
                        im = Image.open(io.BytesIO(pg.locator(chip).screenshot(timeout=5000))).convert("RGB") if Image else None
                        pg.evaluate("(s) => document.querySelectorAll(s + ' .gal-eye-ics, ' + s + ' .gal-eye-word').forEach(e => e.style.visibility = '')", chip)
                        if im is None:
                            glass19[(screen, scheme, kind)] = "Pillow is not here"
                            continue
                        W, H = im.size
                        px = [im.getpixel((x, y)) for x in range(int(W * 0.25), int(W * 0.75)) for y in range(int(H * 0.3), int(H * 0.7))]
                        glass19[(screen, scheme, kind)] = round(min((max(lum19(c), lum19(INK19)) + 0.05) / (min(lum19(c), lum19(INK19)) + 0.05) for c in px), 2)
                    pg.locator(cell(p3) + " .gal-eye").click()
                    pg.wait_for_function(TOAST_UP, arg="Hidden from the Gallery", timeout=8000)
                    pg.wait_for_timeout(300)
                    toast19[(screen, scheme)] = pg.evaluate(READ_TOAST)
                    pg.locator(".mu-toast [data-mute-undo]").click()
                    pg.wait_for_function(TOAST_UP, arg="Back in the Gallery", timeout=8000)
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                    glass19[(screen, scheme, "stopped")] = str(exc).splitlines()[0][:120]
                close_ctx(ctx, pg)
        check("the eye's ink reads at 4.5:1 or more off the pixels of its glass, over the Pad's dark and over paper, and"
              " the toast's words (\"Hidden from the Gallery\", Undo) on what is painted behind them: a touch phone and a"
              " desk, light and dark",
              len(glass19) == 8 and all(isinstance(v, float) and v >= 4.5 for v in glass19.values())
              and len(toast19) == 4 and all(v.get("read", 0) >= 2 and not v.get("low") for v in toast19.values()),
              json.dumps({"glass": {" ".join(k): v for k, v in glass19.items()},
                          "toast": {" ".join(k): (v.get("read"), v.get("lowest"), v.get("low")) for k, v in toast19.items()}}))

        # 8. ITS GUARDS: yours alone, signed in, the page's token, a true or false.
        gc = eli.client()
        gc.get(GAL)
        nc = noa.client()
        nc.get("/social/")
        anon = Client()
        anon.get(GAL)
        db("update social_posts set taken_down_at = '2026-11-14 12:00:00.000000' where public_id = ?", (p3,), write=True)
        guards19 = {
            "no token": gc.post_json(f"/social/p/{p1}/gallery", {"gallery": False}, token=False)[0],
            "signed out": anon.post_json(f"/social/p/{p1}/gallery", {"gallery": False})[0],
            "somebody else's post": nc.post_json(f"/social/p/{p1}/gallery", {"gallery": False})[0],
            "somebody else's drawing": nc.post_json(f"/social/b/{d1}/gallery", {"gallery": False})[0],
            "her face": gc.post_json(f"/social/b/{face19}/gallery", {"gallery": True})[0],
            "her answer's drawing": gc.post_json(f"/social/b/{answer19}/gallery", {"gallery": True})[0],
            "a post's drawing as a drawing": gc.post_json(f"/social/b/{skr.get('p1')}/gallery", {"gallery": False})[0],
            "no true or false": gc.post_json(f"/social/p/{p1}/gallery", {"shown": False})[0],
            "words": gc.post_json(f"/social/p/{p1}/gallery", {"gallery": "no"})[0],
            "taken down": gc.post_json(f"/social/p/{p3}/gallery", {"gallery": False})[0]}
        db("update social_posts set taken_down_at = NULL where public_id = ?", (p3,), write=True)
        kept19 = [flag(p1), flag(p3), vis(d1), vis(face19), vis(answer19), vis(skr.get("p1"))]
        check("its guards: the page's token (403), signed in (401), yours alone (somebody else's post or drawing: 404), never"
              " a face, a comment's drawing or a post's drawing by itself (404), a true or false (400), never what was"
              " taken down (404); none of them changing anything",
              guards19 == {"no token": 403, "signed out": 401, "somebody else's post": 404, "somebody else's drawing": 404,
                           "her face": 404, "her answer's drawing": 404, "a post's drawing as a drawing": 404,
                           "no true or false": 400, "words": 400, "taken down": 404}
              and kept19 == [None, None, "public", "unlisted", "unlisted", "unlisted"],
              f"{guards19}; kept {kept19}")

        # 9. PRESSED FAST: every tap counts, and the site ends where the last
        # one left it (two taps hard after each other: shown; three: hidden).
        fast19 = {}
        ctx, pg = browser_as(b, eli, "phone", "light")
        try:
            pg.goto(BASE + GAL)
            pg.wait_for_selector(cell(p1), timeout=15000)
            pg.locator(cell(p1)).scroll_into_view_if_needed(timeout=5000)
            xy = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.right - 22, r.top + 22]; }",
                             cell(p1) + " .gal-eye")
            for n_taps in (2, 3):
                for _ in range(n_taps):
                    pg.touchscreen.tap(*xy)
                pg.wait_for_timeout(1800)
                fast19[n_taps] = {"hidden": pg.evaluate("(s) => document.querySelector(s).classList.contains('is-hidden')", cell(p1)),
                                  "flag": flag(p1) is not None}
            pg.touchscreen.tap(*xy)
            pg.wait_for_timeout(1500)
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
            fast19["stopped"] = str(exc).splitlines()[0][:160]
        close_ctx(ctx, pg)
        check("PRESSED FAST, every tap counts: two taps hard after each other leave it in the Gallery, as it was, and three"
              " hide it, the page and the site agreeing",
              fast19.get(2) == {"hidden": False, "flag": False} and fast19.get(3) == {"hidden": True, "flag": True},
              json.dumps(fast19))

    # ------------------------------------------------------------------ 20
    # A DRAFT'S TILE OPENS INSIDE A POST (the owner's "All yes", Nov 19, to
    # the evening's walk of Save and Drafts; choice 4). The tile was a plain
    # link to the editor by itself: out of the site, no bar, no way back, its
    # button "Post to Skribl". A tap now opens the draft inside a post, as
    # the picker's own tile does: the composer's sheet with the editor over
    # it (compose.js, draft). THE SHEET IS THERE TO HOLD WHAT ADD BRINGS, SO
    # UNTIL THEN IT IS NOT PAINTED, AND THAT IS READ ON EVERY FRAME (the
    # owner: "No transitions should be jumpy"): the editor is all that is
    # seen rising. As first built the two rose together; on a desk both
    # cards faded in at once and the sheet showed through the editor's.
    if part(20, "a draft's tile opens inside a post: only the editor seen as it rises, × back on your drafts, Add attached"):
        T = tab_people(b)
        pia = T["pia"]
        tg20 = T["tag"]

        def frame20(pg_, path, timeout=30):
            """The editor at `path` in compose mode, over the page, once it is up."""
            end = time.time() + timeout
            while time.time() < end:
                fr = next((f for f in pg_.frames if urllib.parse.urlsplit(f.url or "").path == path
                           and "compose=1" in (f.url or "")), None)
                if fr:
                    try:
                        fr.wait_for_function("() => !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip))",
                                             timeout=1000)
                        return fr
                    except Exception:  # noqa: BLE001 -- not up yet
                        pass
                pg_.wait_for_timeout(200)
            return None

        HOST20 = """(id) => { const tile = document.querySelector('.gal-tile[data-draft="' + id + '"]');
          const wrap = document.getElementById('composeSheet'), sheet = wrap.querySelector('.make-sheet');
          const up = [document.getElementById('composePad'), document.getElementById('composeFlip')].find(o => !o.hidden) || null;
          const fr = up && up.querySelector('iframe'), at = document.activeElement;
          const mid = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
          return { at: location.pathname, sheet: window.SocialComposer.isOpen(),
                   sheetSeen: !wrap.hidden && getComputedStyle(sheet).visibility === 'visible',
                   editor: up ? up.id : null, src: fr ? fr.getAttribute('src') : null, front: !!fr && mid === fr,
                   focus: at === fr ? 'the editor' : at === tile ? 'the tile' : at === sheet ? 'the sheet' : at && at.hasAttribute('data-compose-words') ? 'the words'
                     : at && at.hasAttribute('data-compose-edit') ? 'Edit drawing' : at ? at.tagName : null,
                   attached: window.SocialComposer.attached(), inert: document.getElementById('main').hasAttribute('inert'),
                   says: ((document.querySelector('[data-compose-say]') || {}).textContent || '').trim() }; }"""
        # Every frame from the tap (or the ×) on: whether the sheet or its
        # scrim is painted, and where the editor's own sheet stands and how
        # solid it is. [ms, sheet painted, the editor's top, its opacity]
        # AND THE GLIDE'S OWN CLOCK (window.__glide): every transition the
        # editor's sheet finishes, [what moved, for how many ms], as the
        # browser reports it (transitionend's elapsedTime). The frames say
        # what was painted; the clock says it glided, whatever the frames a
        # busy machine got round to showing this page's script.
        WATCH20 = """() => { window.__rise = []; window.__glide = [];
          const t0 = performance.now(), wrap = document.getElementById('composeSheet');
          const sheet = wrap.querySelector('.make-sheet'), scrim = wrap.querySelector('.make-scrim');
          if (window.__words === undefined) { window.__words = 0;
            wrap.querySelector('[data-compose-words]').addEventListener('focus', () => { window.__words += 1; });
            document.addEventListener('transitionend', (e) => { if (e.target.classList && e.target.classList.contains('facepad-sheet'))
              window.__glide.push([e.propertyName, Math.round(e.elapsedTime * 1000)]); }, true); }
          (function step() {
            const up = [document.getElementById('composePad'), document.getElementById('composeFlip')].find(o => !o.hidden) || null;
            const ed = up && up.querySelector('.facepad-sheet');
            const painted = !wrap.hidden && (getComputedStyle(sheet).visibility !== 'hidden' || +getComputedStyle(scrim).opacity > 0.001);
            window.__rise.push([Math.round(performance.now() - t0), painted,
                                ed ? Math.round(ed.getBoundingClientRect().top * 10) / 10 : null,
                                ed ? Math.round(+getComputedStyle(ed).opacity * 100) / 100 : null]);
            if (performance.now() - t0 < 1400) requestAnimationFrame(step); })(); }"""

        def judge20(got, rising, glides=True):
            """Nothing of the sheet painted on any frame; the editor gliding
            one way (where it glides: not under Reduce Motion, which fades
            it where it sits) and ending where it should (up: at rest and
            solid; away: gone).

            THE GLIDE IS READ FROM ITS OWN CLOCK, NOT FROM HOW MANY FRAMES
            THIS PAGE'S SCRIPT WAS SHOWN (main's run after #1008, sqlite 7/7
            alone: "pad, a desk" rose with 3 frames on which it had changed,
            54 frames in 1.4 s, where 4 were asked; green beside it on
            postgresql, the same tree). The editor's own page loads in the
            same thread while its card rises, so on a busy machine the
            frames this script is handed thin out, while the browser moves
            the card all the same. What cannot thin out is the transition
            itself: it ran its time, on what should move (transform where
            it glides, opacity where it only fades). A jump has no
            transition to report, however many frames there are. The frames
            still say what they can say truly at any pace: nothing of the
            sheet painted, never a step back, and where it ended."""
            frames, clock = got["frames"], got["glide"]
            seen = [f for f in frames if f[1]]
            shown = [f for f in frames if f[2] is not None]
            tops = [f[2] for f in shown]
            # Told, not asked: on how many frames it stood somewhere new or
            # was more (or less) solid than the frame before.
            changing = [k for k in range(1, len(shown)) if abs(shown[k][2] - shown[k - 1][2]) > 0.5 or shown[k][3] != shown[k - 1][3]]
            moving = [k for k in range(1, len(tops)) if abs(tops[k] - tops[k - 1]) > 0.5]
            back = [k for k in range(1, len(tops)) if (tops[k] - tops[k - 1]) * (1 if rising else -1) > 0.5]
            end_ok = (bool(tops) and frames[-1][3] == 1 and len(set(tops[-5:])) == 1) if rising else frames[-1][2] is None
            ran = {}
            for what, ms in clock:
                ran[what] = max(ran.get(what, 0), ms)
            glided = ran.get("transform" if glides else "opacity", 0) >= 150
            # THE WATCH RAN ITS 1.4 s. How many frames it was shown is told,
            # not asked: a frame is what gets painted, so however few a busy
            # machine shows, each was read (at a twelfth of this machine's
            # speed a desk showed 15, where 20 were asked until now).
            watched = len(frames) > 4 and frames[-1][0] >= 1300
            return {"ok": watched and not seen and glided and not back and end_ok,
                    "frames": len(frames), "sheet painted": seen[:3], "ran": ran, "changing": len(changing),
                    "moving": len(moving), "went back": len(back), "ends": frames[-1]}

        seen20 = {}
        for key, did, path, read, name, screen, reduced in (
                ("pad", T["snail"], "/skribl-pad", "strokes.length", f"A snail for Kai {tg20}", "phone", False),
                ("flip", T["bike"], "/flip", "serializeFlip({ recipes: true }).frames.length", f"The bike, half done {tg20}",
                 "phone", False),
                ("pad, a desk", T["snail"], "/skribl-pad", "strokes.length", f"A snail for Kai {tg20}", "desk", False),
                ("pad, Reduce Motion", T["snail"], "/skribl-pad", "strokes.length", f"A snail for Kai {tg20}", "phone", True)):
            got = seen20[key] = {"name": name, "id": did}
            ctx, pg = browser_as(b, pia, screen, "dark" if screen == "desk" else "light", reduced=reduced)
            press = pg.tap if screen == "phone" else pg.click
            try:
                pg.goto(BASE + "/social/@tabpia/drafts")
                pg.wait_for_function("() => !!window.SocialComposer && document.readyState === 'complete'", timeout=15000)
                tile = f'.gal-tile[data-draft="{did}"]'
                pg.evaluate(WATCH20)
                press(tile)
                fr = frame20(pg, path)
                fr.wait_for_function("(id) => !!window.SkriblSavedDrafts && window.SkriblSavedDrafts.current() === id", arg=did,
                                     timeout=20000)
                pg.wait_for_timeout(1500)
                got["rise"] = judge20(pg.evaluate("() => ({ frames: window.__rise, glide: window.__glide })"), True, glides=not reduced)
                got["up"] = pg.evaluate(HOST20, did)
                got["up"]["words took focus"] = pg.evaluate("() => window.__words")
                got["in"] = fr.evaluate("() => ({ current: SkriblSavedDrafts.current(), name: window.SkriblName ? SkriblName.get() : null,"
                                        " drawn: " + read + ", add: document.getElementById('postBtn').textContent.trim(),"
                                        " close: document.getElementById('composeCloseBtn').getClientRects().length > 0 })")
                # Put away, nothing added: its ×. On a desk too: the editor
                # fills the window there since Nov 26 (Room for the Drawer),
                # and a click at the corner, which was beside its card, lands
                # in the editor (green alone only where it found the × there).
                pg.evaluate(WATCH20)
                fr.click("#composeCloseBtn")
                pg.wait_for_timeout(1500)
                got["away"] = judge20(pg.evaluate("() => ({ frames: window.__rise, glide: window.__glide })"), False, glides=not reduced)
                got["after"] = pg.evaluate(HOST20, did)
                if key == "flip":
                    # Make, after a draft's editor was put away: the sheet is seen.
                    pg.tap("nav.nav .tab-make")
                    pg.wait_for_timeout(900)
                    got["make after"] = pg.evaluate(HOST20, did)
                    pg.tap("#composeSheet [data-compose-cancel]")
                    pg.wait_for_timeout(700)
                if key == "pad":
                    # Again, and Add: the draft comes back attached, the sheet under it.
                    press(tile)
                    fr = frame20(pg, path)
                    fr.wait_for_function("() => typeof strokes !== 'undefined' && strokes.length > 0", timeout=20000)
                    pg.wait_for_timeout(600)
                    fr.click("#postBtn")
                    pg.wait_for_timeout(700)
                    fr.click("#postSubmitBtn")
                    pg.wait_for_function("() => !!window.SocialComposer.attached()", timeout=25000)
                    pg.wait_for_timeout(900)
                    got["added"] = pg.evaluate(HOST20, did)
                    got["post lit"] = pg.evaluate("() => document.querySelector('[data-compose-post]').getAttribute('aria-disabled')")
                    # The sheet put away with the drawing still in it, then the
                    # other draft's tile: a post holds one.
                    pg.tap("#composeSheet [data-compose-cancel]")
                    pg.wait_for_timeout(900)
                    pg.tap(f'.gal-tile[data-draft="{T["bike"]}"]')
                    pg.wait_for_timeout(1200)
                    got["second"] = pg.evaluate(HOST20, T["bike"])
            except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                got["stopped"] = str(exc).splitlines()[0][:200]
            close_ctx(ctx, pg)

        def up_ok(v, wrap_id, drawn):
            u, i = v.get("up") or {}, v.get("in") or {}
            return bool(u.get("at") == "/social/@tabpia/drafts" and u.get("sheet") and u.get("editor") == wrap_id
                        and "compose=1" in (u.get("src") or "") and (u.get("src") or "").endswith("draft=" + v["id"])
                        and u.get("front") and u.get("focus") == "the editor" and u.get("words took focus") == 0
                        and u.get("attached") is None
                        and i.get("current") == v["id"] and i.get("name") == v["name"] and drawn(i.get("drawn") or 0)
                        and i.get("add", "").startswith("Add") and i.get("close"))
        check("a tap on a draft keeps you on your page and opens it INSIDE A POST: the composer's sheet and the editor that"
              " made it over it (compose mode, ?draft=<id>), the editor painted at the screen's middle and holding focus"
              " (the words never took it, counted, so no keyboard comes up under it), the draft on its canvas named as it"
              " is, its button Add and its × there; a Flip draft in Flip the same, its three pages; a click on a desk the"
              " same",
              up_ok(seen20["pad"], "composePad", lambda n: n > 0) and up_ok(seen20["flip"], "composeFlip", lambda n: n == 3)
              and up_ok(seen20["pad, a desk"], "composePad", lambda n: n > 0),
              json.dumps({k: {x: v.get(x) for x in ("up", "in", "stopped")} for k, v in seen20.items()})[:900])
        check("ONLY THE EDITOR IS SEEN, read on every frame: from the tap until it rests nothing of the sheet is painted, nor"
              " its scrim, and the editor glides one way, never a step back, its own transition running its time (a phone"
              " and a desk: up from the foot, the whole window; under Reduce Motion a fade where it"
              " sits); put away without Add the same, until it is gone (the Pad and Flip on a phone, a desk, Reduce Motion)",
              all((v.get("rise") or {}).get("ok") and (v.get("away") or {}).get("ok") for v in seen20.values()),
              json.dumps({k: {x: v.get(x) for x in ("rise", "away")} for k, v in seen20.items()})[:2000])
        want_after = {"at": "/social/@tabpia/drafts", "sheet": False, "sheetSeen": False, "editor": None, "focus": "the tile",
                      "attached": None, "inert": False}
        make_after = seen20["flip"].get("make after") or {}
        check("put away without Add (its ×, on a phone and a desk): the sheet goes with it and you are"
              " on your drafts as you were, nothing attached, the page in reach again and focus back on the tile; and Make,"
              " pressed after that, opens the sheet SEEN, calm as Make opens it on a touch phone (focus on the sheet itself)",
              all({k: (v.get("after") or {}).get(k) for k in want_after} == want_after for v in seen20.values())
              and bool(make_after.get("sheet") and make_after.get("sheetSeen") and make_after.get("editor") is None
                       and make_after.get("focus") == "the sheet"),
              json.dumps({"after": {k: v.get("after") for k, v in seen20.items()}, "Make after": make_after})[:1100])
        added, second = seen20["pad"].get("added") or {}, seen20["pad"].get("second") or {}
        check("Add brings it back attached: the sheet seen now, there under the editor as it goes, the drawing in it, Edit"
              " drawing in focus and Post lit; and with that drawing attached, a tap on another draft opens the sheet on it"
              " (seen) and says a post holds one, no editor over it",
              bool(added.get("sheet") and added.get("sheetSeen") and added.get("editor") is None
                   and added.get("attached") == {"kind": "payload", "id": None}
                   and added.get("focus") == "Edit drawing" and seen20["pad"].get("post lit") == "false"
                   and second.get("sheet") and second.get("sheetSeen") and second.get("editor") is None
                   and second.get("attached") == {"kind": "payload", "id": None}
                   and second.get("says") == "A post holds one drawing. Remove this one to use another."),
              json.dumps({"added": added, "post lit": seen20["pad"].get("post lit"), "second": second}))

    # ------------------------------------------------------------------ 21
    if part(21, "the page behind holds still while the editor is over it, and is where it stood once it goes"):
        # The owner's iPhone, Nov 22, the Pad over Make: each letter typed in Text scrolled the timeline behind a
        # little, and the overlay with it, so the screen jumped and a post showed under the keyboard's strip.
        # overflow: hidden does not hold a phone's page (the phone scrolls it to show what is typed): the page is
        # fixed where it stood while the editor is up (social.css body.facepad-open, social.js padOver) and
        # scrolled back to that place once the editor has gone. Read on a page scrolled 400px (made tall enough
        # here), with tries to scroll it while the editor is up.
        holda = member(b, "holda", "Holda Still")
        pg = holda.pg
        pg.goto(BASE + "/social/@holda")
        pg.wait_for_timeout(400)
        open_face_sheet(pg)
        pg.evaluate("""() => { const s = document.createElement('div'); s.id = 'holdMark'; s.style.height = '2400px';
            document.getElementById('main').appendChild(s); window.scrollTo({ top: 400, behavior: 'instant' }); }""")
        pg.wait_for_timeout(200)
        MARK = "() => ({ y: Math.round(scrollY), mark: Math.round(document.getElementById('holdMark').getBoundingClientRect().top) })"
        before = pg.evaluate(MARK)
        pg.evaluate(GLIDE, ["#faceSheet [data-face-open]", 900])
        up = pg.evaluate(OVERLAY)
        held = pg.evaluate("""() => { const cs = getComputedStyle(document.body), m = () => Math.round(document.getElementById('holdMark').getBoundingClientRect().top);
            const at = m(); window.scrollTo({ top: 900, behavior: 'instant' }); window.scrollBy(0, 300);
            return { position: cs.position, at: at, tried: m() }; }""")
        fr = pad_frame(pg)
        close_glide(pg, fr)
        # THE READ WAITS FOR THE EDITOR TO HAVE GONE, not a set 400ms after its close (alone, two runs in three on
        # main read it while it was still going: "gone" false, the page still held at 0).
        gone_by(pg)
        after, gone = pg.evaluate(MARK), pg.evaluate(OVERLAY)
        check("while the editor is over the page, the page behind holds still: fixed where it stood (scrolled 400px, it"
              " shows the same), and tries to scroll it move nothing; once the editor has gone it is scrolled to that same"
              " place, nothing behind having moved (the owner's iPhone, Nov 22: each letter typed scrolled the timeline"
              " behind the Pad)",
              before["y"] == 400 and up and up["open"] and held["position"] == "fixed" and held["at"] == before["mark"]
              and held["tried"] == before["mark"] and gone and gone["hidden"] and after == before,
              json.dumps({"before": before, "up": up and up.get("open"), "held": held, "after": after,
                          "gone": gone and gone.get("hidden")}))
        # ...AND IN THE APP'S FRAME (the owner's "Yes on the bottom bar", Nov 27; social.css THE APP'S FRAME): in the
        # Home Screen app the body is the page that scrolls, a frame, which a fixed body would lose its place in; it
        # is held by overflow alone (the user's finger cannot move it, and nothing of the page moves) and is where it
        # stood once the editor goes. The app is iOS's own say, the splash already seen this launch.
        actx, apg = browser_as(b, holda, init=("Object.defineProperty(navigator, 'standalone', { value: true, configurable: true });",
                                               "try { sessionStorage.setItem('blooby.splash.launch', '1'); } catch (e) {}"))
        apg.goto(BASE + "/social/@holda")
        apg.wait_for_timeout(500)
        open_face_sheet(apg)
        apg.evaluate("""() => { const s = document.createElement('div'); s.id = 'holdMark'; s.style.height = '2400px';
            document.getElementById('main').appendChild(s); document.body.scrollTop = 400; }""")
        apg.wait_for_timeout(200)
        AMARK = """() => ({ app: document.documentElement.classList.contains('is-app'), y: Math.round(document.body.scrollTop),
            win: Math.round(scrollY), mark: Math.round(document.getElementById('holdMark').getBoundingClientRect().top) })"""
        abefore = apg.evaluate(AMARK)
        apg.evaluate(GLIDE, ["#faceSheet [data-face-open]", 900])
        aup = apg.evaluate(OVERLAY)
        aheld = apg.evaluate("""() => { const cs = getComputedStyle(document.body);
            return { position: cs.position, overflow: cs.overflowY, y: Math.round(document.body.scrollTop),
                     at: Math.round(document.getElementById('holdMark').getBoundingClientRect().top) }; }""")
        afr = pad_frame(apg)
        close_glide(apg, afr)
        gone_by(apg)
        aafter, agone = apg.evaluate(AMARK), apg.evaluate(OVERLAY)
        close_ctx(actx, apg)
        check("in the app's frame the page behind holds still too: the body, which is the page that scrolls there, held by"
              " overflow and not fixed (a fixed frame loses its place), everything behind where it stood (scrolled 400px),"
              " and the frame at 400 once the editor has gone",
              abefore["app"] and abefore["y"] == 400 and abefore["win"] == 0 and aup and aup["open"]
              and aheld["position"] == "static" and aheld["overflow"] == "hidden" and aheld["y"] == 400
              and aheld["at"] == abefore["mark"] and agone and agone["hidden"] and aafter == abefore,
              json.dumps({"before": abefore, "up": aup and aup.get("open"), "held": aheld, "after": aafter,
                          "gone": agone and agone.get("hidden")}))

    # ----------------------------------------------------------------- 22
    # PIN THIS POST (the owner's idea, Nov 23; the Pin mock's A and A, the
    # owner's "all yes", Nov 25; pins.py): "Pin to your page" in your own
    # post's ⋯, after Bookmark; one at a time; the pinned post first on your
    # Posts tab with "Pinned", for you and anybody who visits, and never again
    # further down; the toast says what happened, with Undo.
    if part(22, "pin this post: Pin in your own post's ⋯, one at a time; first on your Posts tab with Pinned, for anyone"):
        try:
            pia = _people.get("pinpia") or member(b, "pinpia", "Pia Pinner")
            tom = _people.get("pintom") or member(b, "pintom", "Tom Visitor")
            tag = secrets.token_hex(3)
            ps = [site_post(pia, f"Pia's pin post {k} {tag}", tab_drawing(seed=120 + k)) for k in range(3)]
            toms = site_post(tom, f"Tom's post {tag}", tab_drawing(seed=130))
            LIST22 = """() => [...document.querySelectorAll('[data-prof-list] > .post-card[data-post]')].map(c =>
              [c.getAttribute('data-post'), !!c.querySelector(':scope > .pin-by'),
               (c.querySelector(':scope > .pin-by') || {}).textContent ? c.querySelector(':scope > .pin-by').textContent.trim() : null])"""
            ROW22 = """() => { const r = document.querySelector('#postSheet [data-act="pin"]'); if (!r) return null;
              const box = r.closest('.post-acts'), rows = [...box.querySelectorAll('.post-act')].filter(x => !x.hidden && x.getClientRects().length);
              const rr = r.getBoundingClientRect(), at = r.hidden ? null : document.elementFromPoint(rr.left + rr.width / 2, rr.top + rr.height / 2);
              return { shown: !r.hidden && !!r.getClientRects().length, words: r.textContent.trim(), order: rows.map(x => x.getAttribute('data-act')),
                       mark: [...r.querySelectorAll('svg path')].length, h: Math.round(rr.height), painted: !!at && (at === r || r.contains(at)) }; }"""
            TOAST22 = "() => { const t = document.querySelector('.mu-toast'); return t && !t.hidden ? [t.querySelector('.mu-toast-words, [data-toast-words]') ? t.querySelector('.mu-toast-words, [data-toast-words]').textContent.trim() : t.textContent.trim(), !!t.querySelector('button:not([hidden])')] : null; }"

            def menu22(pg_, pid):
                sel = f'.post-card[data-post="{pid}"] [data-post-menu]'
                pg_.locator(sel).first.scroll_into_view_if_needed(timeout=5000)
                pg_.locator(sel).first.tap(timeout=5000)
                pg_.wait_for_timeout(650)

            def pin22(pg_, pid):
                """Pin (or Unpin) `pid` from its card's ⋯; the toast's words and whether it has Undo."""
                menu22(pg_, pid)
                with pg_.expect_response(lambda r: r.url.endswith("/pin") and r.request.method == "POST", timeout=8000):
                    pg_.locator('#postSheet [data-act="pin"]').tap(timeout=5000)
                pg_.wait_for_timeout(900)
                return pg_.evaluate(TOAST22)

            def tab22(who_, path="/social/@pinpia"):
                ctx_, pg_ = browser_as(b, who_)
                pg_.goto(BASE + path)
                pg_.wait_for_timeout(700)
                out = pg_.evaluate(LIST22)
                close_ctx(ctx_, pg_)
                return out

            # The row: on your own post, after Bookmark; on somebody else's, none.
            ctx, pg = browser_as(b, pia)
            pg.goto(BASE + "/social/@pinpia")
            pg.wait_for_timeout(800)
            before = pg.evaluate(LIST22)
            menu22(pg, ps[0])
            own = pg.evaluate(ROW22)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            pg.goto(BASE + "/social/@pintom")
            pg.wait_for_timeout(800)
            menu22(pg, toms)
            other = pg.evaluate(ROW22)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            check("the ⋯ on your own post offers \"Pin to your page\" right after Bookmark, its pin drawn in our pen, 44px"
                  " and painted where it stands; on somebody else's post there is none",
                  all(ps) and bool(toms) and own and own["shown"] and own["words"] == "Pin to your page"
                  and own["order"][:2] == ["bookmark", "pin"] and own["mark"] >= 2 and own["h"] >= 44 and own["painted"]
                  and other is not None and not other["shown"],
                  json.dumps({"own": own, "theirs": other}))
            # Pin the oldest: the toast, then the page.
            pg.goto(BASE + "/social/@pinpia")
            pg.wait_for_timeout(800)
            said1 = pin22(pg, ps[0])
            menu22(pg, ps[0])
            again = pg.evaluate(ROW22)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            close_ctx(ctx, pg)
            mine1, theirs1, nobody1 = tab22(pia), tab22(tom), tab22(None)
            want1 = [[ps[0], True, "Pinned"], [ps[2], False, None], [ps[1], False, None]]
            check("pinned: the sheet goes down and the toast says \"Pinned. It’s first on your page.\" with Undo; the next"
                  " ⋯ says \"Unpin from your page\"",
                  said1 == ["Pinned. It’s first on your page.", True] and again and again["words"] == "Unpin from your page",
                  json.dumps({"toast": said1, "then": again}))
            check("your Posts tab leads with the pinned post, \"Pinned\" above it, and shows it once (the rest newest"
                  " first); the same for somebody who visits and for nobody signed in",
                  before[:3] == [[ps[2], False, None], [ps[1], False, None], [ps[0], False, None]]
                  and mine1 == want1 and theirs1 == want1 and nobody1 == want1,
                  json.dumps({"before": before, "you": mine1, "visitor": theirs1, "nobody": nobody1}))
            # Pin another: one at a time, the first back in its place; Undo puts it back.
            ctx, pg = browser_as(b, pia)
            pg.goto(BASE + "/social/@pinpia")
            pg.wait_for_timeout(800)
            said2 = pin22(pg, ps[1])
            moved = tab22(pia)
            pg.locator(".mu-toast button:not([hidden])").first.tap(timeout=5000)
            pg.wait_for_timeout(1200)
            undone = tab22(pia)
            rows = db("select count(*) from social_pins where person_id = (select id from social_people where handle_key = 'pinpia')")
            check("pinning another moves the pin: \"your other pin is back in its place\", the new one first, the old one"
                  " back among the rest; Undo puts the first back; one row a person",
                  said2 == ["Pinned. It’s first on your page, and your other pin is back in its place.", True]
                  and moved == [[ps[1], True, "Pinned"], [ps[2], False, None], [ps[0], False, None]]
                  and undone == want1 and rows and rows[0][0] == 1,
                  json.dumps({"toast": said2, "moved": moved, "undone": undone, "rows": rows}))
            # Unpin: back in its place.
            pg.goto(BASE + "/social/@pinpia")
            pg.wait_for_timeout(800)
            said3 = pin22(pg, ps[0])
            close_ctx(ctx, pg)
            un = tab22(pia)
            check("Unpin from your page: \"Unpinned. It’s back in its place.\", with Undo, and the tab is newest first again",
                  said3 == ["Unpinned. It’s back in its place.", True]
                  and un[:3] == [[ps[2], False, None], [ps[1], False, None], [ps[0], False, None]],
                  json.dumps({"toast": said3, "tab": un}))
            # Who may pin: your own post alone, signed in, the token; a deleted post takes its pin.
            c = pia.client()
            c.get("/social/@pinpia")
            st_theirs = c.post_json(f"/social/p/{toms}/pin", {"pinned": True})[0]
            st_bad = c.post_json(f"/social/p/{ps[2]}/pin", {"pinned": "yes"})[0]
            st_none = c.post_json("/social/p/nopost00/pin", {"pinned": True})[0]
            st_mine = c.post_json(f"/social/p/{ps[2]}/pin", {"pinned": True})[0]
            st_out = http(f"/social/p/{ps[2]}/pin", "POST", json.dumps({"pinned": False}).encode(), {"Content-Type": "application/json"})[0]
            gone = site_post(pia, f"Pia's short-lived post {tag}", tab_drawing(seed=140))
            c.post_json(f"/social/p/{gone}/pin", {"pinned": True})
            pinned_gone = db("select count(*) from social_pins p join social_posts s on s.id = p.post_id where s.public_id = ?", (gone,))
            d = c.post_json(f"/social/p/{gone}/delete", {})[0]
            after_del = db("select count(*) from social_pins where person_id = (select id from social_people where handle_key = 'pinpia')")
            check("who may pin: somebody else's post or one not there, \"gone\" (404); a body that is not a yes or a no, 400;"
                  " nobody signed in or without the token, refused; your own, done; and a pinned post deleted takes its pin",
                  st_theirs == 404 and st_bad == 400 and st_none == 404 and st_mine == 200 and st_out in (401, 403)
                  and pinned_gone and pinned_gone[0][0] == 1 and d == 200 and after_del and after_del[0][0] == 0,
                  json.dumps({"theirs": st_theirs, "bad": st_bad, "none": st_none, "mine": st_mine, "out": st_out,
                              "pinned": pinned_gone, "delete": d, "left": after_del}))
            # SAID IN CODE, with SQLite's cascade off (SKRIBL_SQLITE_FOREIGN_KEYS=0, on a copy): a post goes with
            # its pin (posts.drop_post), and an account with its own, always on a post of theirs
            # (accounts.delete_person drops each), the code alone.
            c.post_json(f"/social/p/{ps[1]}/pin", {"pinned": True})
            rob = _people.get("pinrob") or member(b, "pinrob", "Rob Pinner")
            robs = site_post(rob, f"Rob's pinned post {tag}", tab_drawing(seed=150))
            cr = rob.client()
            cr.get("/social/@pinrob")
            cr.post_json(f"/social/p/{robs}/pin", {"pinned": True})
            copy = os.path.join(TMP, "pin-probe.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            PIN_PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Person, Pin, Post
    from social.accounts import delete_person
    from social.posts import drop_post
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    n = lambda w: db.session.execute(sa.select(sa.func.count()).select_from(Pin).where(w)).scalar()
    row = db.session.execute(sa.select(Post).where(Post.public_id == sys.argv[1])).scalar_one()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[2])).scalar_one()
    author = db.session.get(Person, row.person_id)
    post_id, pid = row.id, who.id
    out = {"fk": fk, "post": [n(Pin.post_id == post_id)]}
    drop_post(author.public_id, row)
    db.session.commit()
    out["post"].append(n(Pin.post_id == post_id))
    out["person"] = [n(Pin.person_id == pid)]
    delete_person(db.session, pid)
    db.session.commit()
    out["person"].append(n(Pin.person_id == pid))
    print(json.dumps(out))
"""
            probe = subprocess.run([sys.executable, "-c", PIN_PROBE, ps[1], "pinrob"], cwd=ROOT, capture_output=True,
                                   text=True, timeout=180,
                                   env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out22 = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out22 = {"err": (probe.stderr or probe.stdout)[-600:]}
            check("with SQLite's cascade off (on a copy), a pinned post deleted takes its pin, and an account deleted its"
                  " own pin with its posts, by the code (posts.drop_post, accounts.delete_person)",
                  out22.get("fk") == 0 and out22.get("post") == [1, 0] and out22.get("person") == [1, 0], json.dumps(out22)[:500])
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            check("pin this post: the part ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))

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
