#!/usr/bin/env python3
"""Drawn letters at /social, the server (the owner's yes, Nov 26, A for all
six; DECISIONS.md, "Drawn letters, mocked"; social/letters.py). Its own
server and database, people who joined through invites, each in a browser
with a virtual passkey; the letters through the site's own routes.

  1. WHO CAN WRITE: two people who follow each other. Following one way,
     nobody by that name, yourself, a block either way, somebody taken down
     or signed out: refused, the first three said the same.
  2. SENDING: a letter is a row of its own (never a post), its drawing
     Skribl's with the site's own visibility, "letter", titled "A letter",
     landing on the two of you; nothing drawn, a photo, music or a Flip
     refused, each with its own word.
  3. READ BY ITS TWO ALONE: its drawing, its link page, its share card and
     its picture are the sender's and the recipient's, nobody else's
     (signed out, a third person, an admin it was not reported to); a block
     between the two shuts both out, and lifting it lets them back.
  4. NEVER LISTED: not in Skribl's feed, its search (by the title), Hot, its
     own Gallery or the Library's listing of the sender's own; not on Home,
     Explore, the site's search, the sender's page and its Gallery, More
     from, or the composer's Yours.
  5. HELD: nobody can make a letter's drawing anything else, or another
     drawing a letter: Skribl's PATCH as its author, the site's eye, and
     Skribl's own posting API with the state.
  6. WRITING BACK (Draw back's way, the owner's yes): the way in hands its
     recipient the letter and the sender's first name; nobody else. Posted,
     theirs plays first squeezed to three seconds, then yours at your own
     pace, on their paper; the mark where your hand starts; it goes to them.
     Written back on again, it plays in order. On another shape, with an
     eraser, or on a letter you sent: refused.
  7. OPENED by a POST from the recipient's page, never by a GET; the
     sender's POST opens nothing.
  8. TAKE BACK: the sender, until it is opened: the letter and its drawing
     go; once opened it stays; the recipient can't.
  9. DELETE FROM YOUR SIDE: gone for you, there for them; once both have,
     the letter and its drawing go.
 10. REPORT: the recipient reports it (the sender and anybody else can't);
     the admins then read it; taken down, it is withheld and gone from the
     recipient's side, the sender still has theirs.
 11. DELETING AN ACCOUNT takes every letter it sent or received, with
     their drawings.
 12. No page errors, no console errors and no CSP violations.
 15. THE PAGES (part three), on a phone: Write beside Following on a
     friend's page, nowhere else; the envelope beside the bell at the top of
     Home with its own dot, and Letters in a desk's rail under Activity;
     Letters' rows (a new one sealed, its dot, "It draws itself when you
     open it"; a sheet once); Write's list of people you may write to; the
     two of you: a new letter draws itself and is opened as it plays (the
     dot goes), the mark where the hand changes, Write back and New letter
     opening the Pad, the ⋯'s Take back and Report; behind a block, no page.
 13. WRITING ONE IN THE PAD (part two), on a phone: SocialLetters.write
     opens the Pad over the page, its button and its sheet's saying Send,
     its pill "A letter to Theo · only the two of you see it"; the picture
     and music drawer and the door to Flip dimmed, each saying why when
     tapped. Drawn and sent, it lands on the two of you, a letter to him
     with the strokes drawn. A send that does not go (a block meanwhile)
     says why and keeps the drawing: Write again opens the Pad with it.
 14. WRITING BACK IN THE PAD: SocialLetters.writeBack opens the Pad on her
     shape and paper, hers faint under the pen, Draw back's pill saying
     "Writing back to Ana · only the two of you see it", the eraser aside;
     sent, the letter is written back on, hers then his. A pill on fresh
     paper over the drawing goes at the first stroke; one clear of it stays.

SOCIALLETTERS_PART=<n>[,<m>] runs those sections only (calibration). Every
row was shown red by breaking one part and green as built: DECISIONS.md,
"Drawn letters, the server".
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
PART = os.environ.get("SOCIALLETTERS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALLETTERS {n} — {label}")
    return True


def steps(fn):
    """A row's steps: (what they gave, None), or ({}, what stopped them), so a
    control that is not there fails its own row and the next row still runs."""
    try:
        return fn(), None
    except Exception as exc:  # noqa: BLE001
        return {}, (str(exc).splitlines() or [repr(exc)])[0][:160]


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a sheet
    that never rose) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence drawn letters work.")
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
TMP = tempfile.mkdtemp(prefix="socialletters-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialletters-" + secrets.token_hex(8),
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

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{80 + _addr[0] // 250}.{_addr[0] % 250}.9"


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


def drawing(n=40, seed=0, size=(816, 612)):
    """A small drawing, as the Pad's Add hands one back."""
    pts = [{"x": round(408 + math.cos((i + seed) / 9) * (30 + i * 3), 1),
            "y": round(306 + math.sin((i + seed) / 9) * (30 + i * 3), 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * 30, "start": i == 0} for i in range(n)]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay",
            "canvasSize": {"cssWidth": size[0], "cssHeight": size[1]},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """The site's own requests, without a browser, as a signed-in person."""

    def __init__(self, cookies=None, xff=None, origin=BASE, base=None):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), _NoRedirect())
        self.xff = xff or address()
        self.origin = origin
        self.base = base or BASE
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
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
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

    def get_json(self, path):
        st, text = self._req("GET", path)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, fields):
        data = urllib.parse.urlencode(dict(fields, csrf=self.token or "")).encode()
        return self._req("POST", path, raw=data, headers={"Content-Type": "application/x-www-form-urlencoded"})[0]

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


def browser_as(b, who, screen="phone", scheme="light", reduced=False, dpr=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    shape = dict(PHONE if screen == "phone" else DESK)
    if dpr:
        shape["device_scale_factor"] = dpr      # a line's own colour needs whole pixels of it (section 9)
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **shape, **kw)
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


def admin(b):
    """The run's admin: the first person it made (the site makes its first
    person its admin), or Juno when it has made nobody yet."""
    got = db("select handle from social_people where is_admin order by id limit 1")
    if got:
        return _people[got[0][0]]
    return someone(b, "juno", "Juno Park")


def make_post(who, words, seed=0):
    """A post as Home's composer sends one: its public id, or None."""
    c = who.client()
    c.get("/social/")
    st, j = c.post_json("/social/posts", {"words": words, "payload": drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def say(who, post, words, answer_to=None):
    """A comment (or an answer) as the box sends one: (status, answer)."""
    c = who.client()
    c.get(f"/social/p/{post}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    return c.post_json(f"/social/p/{post}/comments", body)


def said(who, post, words, answer_to=None):
    st, j = say(who, post, words, answer_to)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def pid_of(handle):
    got = db("select id, public_id from social_people where handle_key = ?", (handle.lower(),))
    return got[0] if got else (None, None)


def post_id(public_id):
    got = db("select id from social_posts where public_id = ?", (public_id,))
    return got[0][0] if got else None


def status(pg, path):
    r = pg.goto(BASE + path)
    pg.wait_for_timeout(300)
    return r.status if r else None




SHOTS = os.environ.get("SOCIALLETTERS_SHOTS")


def shot(pg, name):
    """A picture for a person to look at (SOCIALLETTERS_SHOTS=<dir>), never read by a row."""
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(SHOTS, name + ".png"))


def ready(pg):
    pg.wait_for_load_state("load")
    pg.wait_for_timeout(250)


def pid_of(handle):
    got = db("select id, public_id from social_people where handle_key = ?", (handle.lower(),))
    return got[0] if got else (None, None)


def follow(a, b, on=True):
    c = a.client()
    c.get(f"/social/@{b.handle}")
    return c.post_json(f"/social/@{b.handle}/follow", {"following": on})[0]


def friends(a, b):
    follow(a, b)
    follow(b, a)


def block(a, b, on=True):
    c = a.client()
    c.get(f"/social/@{b.handle}")
    return c.post_json(f"/social/@{b.handle}/{'block' if on else 'unblock'}", {})[0]


def send(who, to, payload, **extra):
    """A letter as the composer sends one: (status, answer)."""
    c = who.client()
    c.get("/social/")
    payload = dict(payload, thumbnail=payload.get("thumbnail") or red_png())   # the picture it rests on, as the Pad sends
    body = dict({"payload": payload}, **extra)
    if to is not None:
        body["to"] = to
    return c.post_json("/social/letters", body)


def sent(who, to, payload=None, seed=0):
    st, j = send(who, to, payload or drawing(seed=seed))
    if st != 200:
        print(f"  (send to {to}: {st} {str(j)[:200]})")
    return j.get("letter") if st == 200 and isinstance(j, dict) else None


def write_back(who, lid, payload, **extra):
    c = who.client()
    c.get("/social/")
    return c.post_json("/social/letters", dict({"payload": payload, "written_on": lid}, **extra))


def act(who, lid, what):
    c = who.client()
    c.get("/social/")
    return c.post_json(f"/social/letters/{lid}/{what}", {})


def letter(lid):
    got = db("select l.id, l.sender_id, l.recipient_id, l.skribl_id, l.written_on_id, l.hand_at_ms, l.opened_at,"
             " l.sender_deleted_at, l.recipient_deleted_at, l.taken_down_at, l.hands_json from social_letters l"
             " where l.public_id = ?", (lid or "",))
    if not got:
        return None
    k = ("id", "sender", "recipient", "sid", "on", "hand_at", "opened", "s_del", "r_del", "down", "hands")
    return dict(zip(k, got[0]))


def drawing_of(sid):
    got = db("select visibility, title, payload_json from skribl_posts where public_id = ?", (sid or "",))
    if not got:
        return None
    return {"visibility": got[0][0], "title": got[0][1], "payload": json.loads(got[0][2]) if got[0][2] else None}


def reads(who, sid):
    """What `who` (None: nobody signed in) gets from the drawing's four doors:
    its payload, its link page, its share card and its picture."""
    c = who.client() if who is not None else Client()
    return tuple(c._req("GET", path)[0] for path in (f"/api/skribls/{sid}", f"/s/{sid}", f"/s/{sid}/card.png",
                                                      f"/s/{sid}/poster"))


OPEN = (200, 200, 200, 200)


def shut(got):
    """Shut: no payload and no link page (404), and its two pictures Skribl's
    own blank stand-ins (a picture never 404s: it redirects to its fallback)."""
    return all(s in (403, 404) for s in got[:2]) and all(s == 302 for s in got[2:])


def xy(points):
    return [(round(p["x"], 2), round(p["y"], 2)) for p in points]


def red_png():
    import io as _io
    from PIL import Image as _Image
    buf = _io.BytesIO()
    _Image.new("RGB", (64, 48), (230, 40, 60)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def short_wav():
    import struct
    n = 800
    data = b"".join(struct.pack("<h", (i % 40 - 20) * 400) for i in range(n))
    head = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
            + b"data" + struct.pack("<I", len(data)))
    return "data:audio/wav;base64," + base64.b64encode(head + data).decode()


def in_browser(who, method, path, body):
    """A request from `who`'s own browser on the Pad (Skribl's CSRF key with
    it), as the Library's switch sends one: its status."""
    pg = who.pg
    if "/skribl-pad" not in pg.url:
        pg.goto(BASE + "/skribl-pad")
        ready(pg)
    return pg.evaluate("""async ([m, p, b]) => { const h = {'Content-Type': 'application/json'};
      if (window.SKRIBL_CSRF_TOKEN) h['X-Skribl-CSRF'] = window.SKRIBL_CSRF_TOKEN;
      const r = await fetch(p, {method: m, headers: h, body: JSON.stringify(b), credentials: 'same-origin'});
      return r.status; }""", [method, path, body])


with sync_playwright() as p:
    b = p.chromium.launch()
    # Juno first: the site makes its first person its admin.
    juno = someone(b, "juno", "Juno Park")
    ana = someone(b, "ana", "Ana Ruiz")
    theo = someone(b, "theo", "Theo Lind")
    cyd = someone(b, "cyd", "Cyd Moss")
    dee = someone(b, "dee", "Dee Hart")
    friends(ana, theo)
    friends(cyd, ana)
    friends(cyd, theo)
    follow(dee, ana)               # Dee follows Ana; Ana does not follow Dee

    # ------------------------------------------------------------------ 1
    if part(1, "who can write"):
        try:
            got = {}
            got["friends"] = send(ana, "theo", drawing(seed=1))[0]
            got["one way, from the follower"] = send(dee, "ana", drawing(seed=2))[0]
            got["one way, to the follower"] = send(ana, "dee", drawing(seed=3))[0]
            got["nobody"] = send(ana, "nobody-here", drawing(seed=4))
            got["yourself"] = send(ana, "ana", drawing(seed=5))
            check("two people who follow each other can write to each other; following one way, either way, can't",
                  got["friends"] == 200 and got["one way, from the follower"] == 403
                  and got["one way, to the follower"] == 403, json.dumps(got))
            check("nobody by that name, and yourself, are said as one way is (not_friends): the answer tells nobody"
                  " who is there", got["nobody"][0] == 403 and got["yourself"][0] == 403
                  and got["nobody"][1].get("error") == got["yourself"][1].get("error") == "not_friends",
                  json.dumps(got))
            block(theo, ana)
            blocked = (send(ana, "theo", drawing(seed=6))[0], send(theo, "ana", drawing(seed=7))[0])
            block(theo, ana, on=False)
            # A block ends a follow both ways, for good: friends again first.
            after = send(ana, "theo", drawing(seed=8))[0]
            friends(ana, theo)
            again = send(ana, "theo", drawing(seed=9))[0]
            check("a block shuts letters both ways, and ends the follow, so lifting it is not enough until both"
                  " follow again", blocked == (403, 403) and after == 403 and again == 200,
                  f"{blocked} {after} {again}")
            pid = pid_of("theo")[0]
            db_write("update social_people set taken_down_at = '2026-01-01 00:00:00' where id = ?", (pid,))
            down = (send(ana, "theo", drawing(seed=10))[0], send(theo, "ana", drawing(seed=11))[0])
            db_write("update social_people set taken_down_at = null where id = ?", (pid,))
            st_out, _ = Client().post_json("/social/letters", {"to": "theo", "payload": drawing()}, token=False)
            check("somebody taken down neither writes nor is written to; signed out is refused",
                  down == (403, 403) and st_out in (401, 403), f"{down} {st_out}")
        except Exception as exc:  # noqa: BLE001
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "sending"):
        try:
            st, j = send(ana, "theo", drawing(seed=20))
            row = letter(j.get("letter")) if isinstance(j, dict) else None
            d = drawing_of(row["sid"]) if row else None
            check("a letter is a row of its own, from her to him, never a post, landing on the two of you",
                  st == 200 and row is not None and row["sender"] == pid_of("ana")[0] and row["recipient"] == pid_of("theo")[0]
                  and not db("select id from social_posts where skribl_id = ?", (row["sid"],))
                  and urllib.parse.urlsplit(j.get("go") or "").path == "/social/letters/@theo",
                  f"{st} {j} {row}")
            check("its drawing is Skribl's, with the site's own visibility, \"letter\", titled \"A letter\", her"
                  " strokes as she drew them", d is not None and d["visibility"] == "letter" and d["title"] == "A letter"
                  and xy(d["payload"]["frames"][0]["strokes"]) == xy(drawing(seed=20)["frames"][0]["strokes"]),
                  str(d and (d["visibility"], d["title"])))
            empty = drawing(seed=21)
            empty["frames"][0]["strokes"] = []
            photo = drawing(seed=22)
            photo["frames"][0]["photo"] = {"data": red_png(), "fit": "cover", "opacity": 1}
            music = drawing(seed=23)
            music["frames"][0]["music"] = {"data": short_wav(), "name": None, "trimStart": 0, "trimEnd": 0}
            flip = drawing(seed=24)
            flip["frames"].append(dict(flip["frames"][0]))
            flip["playbackMode"] = "flip"
            ref = {k: send(ana, "theo", v) for k, v in (("empty", empty), ("photo", photo), ("music", music), ("flip", flip))}
            words = {k: (v[0], v[1].get("error"), v[1].get("why")) for k, v in ref.items()}
            check("nothing drawn, a photo, music or a Flip are refused, each with its word (no_drawing; why: photo,"
                  " music, pages), and nothing is kept",
                  words == {"empty": (400, "no_drawing", None), "photo": (400, "letter_unsupported", "photo"),
                            "music": (400, "letter_unsupported", "music"), "flip": (400, "letter_unsupported", "pages")}
                  and len(db("select id from social_letters")) == len(db("select id from skribl_posts where visibility = 'letter'")),
                  json.dumps(words))
        except Exception as exc:  # noqa: BLE001
            stopped(2, exc)

    L1 = sent(ana, "theo", seed=30)
    S1 = (letter(L1) or {}).get("sid")

    # ------------------------------------------------------------------ 3
    if part(3, "read by its two alone"):
        try:
            got = {"ana": reads(ana, S1), "theo": reads(theo, S1), "cyd": reads(cyd, S1), "nobody": reads(None, S1),
                   "juno (admin)": reads(juno, S1)}
            check("its drawing, link page, share card and picture are the sender's and the recipient's",
                  got["ana"] == OPEN and got["theo"] == OPEN, json.dumps(got))
            check("...and nobody else's: a friend of both, nobody signed in, an admin it was not reported to",
                  shut(got["cyd"]) and shut(got["nobody"]) and shut(got["juno (admin)"]), json.dumps(got))
            block(ana, theo)
            during = {"ana": reads(ana, S1), "theo": reads(theo, S1)}
            block(ana, theo, on=False)
            lifted = {"ana": reads(ana, S1), "theo": reads(theo, S1)}
            friends(ana, theo)
            check("a block between the two shuts both of them out; lifted, both read it again",
                  shut(during["ana"]) and shut(during["theo"]) and lifted["ana"] == OPEN and lifted["theo"] == OPEN,
                  json.dumps({"during": during, "lifted": lifted}))
        except Exception as exc:  # noqa: BLE001
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "never listed"):
        try:
            c = ana.client()
            c.get("/social/")
            ana_pid = pid_of("ana")[1]
            st_p, jp = c.post_json("/social/posts", {"words": "A public one", "payload": drawing(seed=40)})
            post = jp.get("post") if isinstance(jp, dict) else None
            seen = {}
            for who in (ana, theo, cyd):
                cl = who.client()
                for path in ("/api/skribls?limit=50", "/api/skribls?limit=50&sort=hot",
                             "/api/skribls?limit=50&q=" + urllib.parse.quote("A letter"),
                             "/api/skribls?limit=50&user_id=" + urllib.parse.quote(ana_pid), "/gallery",
                             "/social/", "/social/explore", "/social/explore?sort=hot", "/social/explore?show=following",
                             "/social/search?q=" + urllib.parse.quote("letter"), "/social/@ana", "/social/@ana/gallery",
                             f"/social/p/{post}", "/social/make/yours?tab=drawings", "/social/activity"):
                    st, text = cl._req("GET", path)
                    seen[f"{who.handle} {path}"] = (st, S1 in text)
            leaks = [k for k, (st, there) in seen.items() if there]
            check("never listed: not in Skribl's feed, Hot, its search by the title, the Library's listing of the"
                  " sender's own or Skribl's Gallery; not on Home, Explore, the site's search, her page, her"
                  " Gallery, More from, the composer's Yours or Activity, to her, to him or to a friend of both",
                  S1 and post and not leaks and all(st == 200 for st, _ in seen.values()),
                  f"leaks {leaks}; {[k for k, (st, _) in seen.items() if st != 200]}")
        except Exception as exc:  # noqa: BLE001
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "held: a letter stays a letter"):
        try:
            got = {}
            got["patch public"] = in_browser(ana, "PATCH", f"/api/skribls/{S1}", {"visibility": "public"})
            got["patch unlisted"] = in_browser(ana, "PATCH", f"/api/skribls/{S1}", {"visibility": "unlisted"})
            c = ana.client()
            c.get("/social/@ana/gallery")
            got["eye"] = c.post_json(f"/social/b/{S1}/gallery", {"gallery": True})[0]
            check("its sender can't make a letter's drawing anything else: Skribl's PATCH (public, unlisted) and the"
                  " site's eye are refused, and it is still a letter",
                  got["patch public"] == 400 and got["patch unlisted"] == 400 and got["eye"] in (403, 404)
                  and (drawing_of(S1) or {}).get("visibility") == "letter", json.dumps(got))
            st_n = in_browser(ana, "POST", "/api/skribls", dict(drawing(seed=50), visibility="letter", title="x"))
            st_pub = in_browser(ana, "POST", "/api/skribls", dict(drawing(seed=51), visibility="public", title="Mine"))
            mine = db("select public_id from skribl_posts where title = 'Mine' order by id desc limit 1")
            st_into = in_browser(ana, "PATCH", f"/api/skribls/{mine[0][0]}", {"visibility": "letter"}) if mine else None
            check("nor make one: Skribl's own posting API refuses the state, and a drawing of hers can't be"
                  " PATCHed into it", st_n == 400 and st_pub == 201 and st_into == 400
                  and (drawing_of(mine[0][0]) if mine else {}).get("visibility") == "public",
                  f"{st_n} {st_pub} {st_into}")
        except Exception as exc:  # noqa: BLE001
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "writing back"):
        try:
            long = drawing(n=200, seed=60)                 # 6 seconds at her pace: squeezed
            L6 = sent(ana, "theo", long)
            c = theo.client()
            st, j = c.get_json(f"/social/letters/{L6}/write-back")
            others = {"ana (sender)": ana.client().get_json(f"/social/letters/{L6}/write-back")[0],
                      "cyd": cyd.client().get_json(f"/social/letters/{L6}/write-back")[0],
                      "nobody": Client().get_json(f"/social/letters/{L6}/write-back")[0]}
            check("the way in hands its recipient the letter as Skribl stores it, and her first name; nobody else,"
                  " its sender included", st == 200 and isinstance(j, dict) and j.get("first") == "Ana"
                  and xy(j["payload"]["frames"][0]["strokes"]) == xy(long["frames"][0]["strokes"])
                  and others["ana (sender)"] == 404 and others["cyd"] == 404 and others["nobody"] in (401, 404),
                  f"{st} {others}")
            mine = drawing(n=30, seed=61)
            st, j = write_back(theo, L6, mine)
            r = letter(j.get("letter")) if isinstance(j, dict) else None
            d = drawing_of(r["sid"]) if r else None
            pts = d["payload"]["frames"][0]["strokes"] if d else []
            hers, his = pts[:200], pts[200:]
            span = hers[-1]["t"] - hers[0]["t"] if hers else None
            his_gaps = [b2["t"] - a2["t"] for a2, b2 in zip(his, his[1:])]
            own_gaps = [b2["t"] - a2["t"] for a2, b2 in zip(mine["frames"][0]["strokes"], mine["frames"][0]["strokes"][1:])]
            check("written back on, it goes to her, and plays hers first, squeezed to three seconds, then his at his"
                  " own pace, on her paper",
                  st == 200 and r is not None and r["sender"] == pid_of("theo")[0] and r["recipient"] == pid_of("ana")[0]
                  and r["on"] == letter(L6)["id"] and xy(hers) == xy(long["frames"][0]["strokes"])
                  and span is not None and 2900 <= span <= 3000 and his_gaps == own_gaps
                  and xy(his) == xy(mine["frames"][0]["strokes"]) and d["visibility"] == "letter",
                  f"{st} {j} span {span}")
            check("the mark where his hand starts is kept: his first point's time in the drawing",
                  r is not None and his and r["hand_at"] == his[0]["t"] and r["hand_at"] > span,
                  f"{r and r['hand_at']} {his[0]['t'] if his else None}")
            L6b = j.get("letter")
            st2, j2 = write_back(ana, L6b, drawing(n=20, seed=62))
            r2 = letter(j2.get("letter")) if isinstance(j2, dict) else None
            p2 = drawing_of(r2["sid"])["payload"]["frames"][0]["strokes"] if r2 else []
            check("written back on again, it plays in order: the sheet so far, squeezed, then hers",
                  st2 == 200 and r2 is not None and len(p2) == 250 and r2["recipient"] == pid_of("theo")[0]
                  and xy(p2[230:]) == xy(drawing(n=20, seed=62)["frames"][0]["strokes"])
                  and p2[229]["t"] - p2[0]["t"] <= 3000, f"{st2} {len(p2)}")
            wide = drawing(n=20, seed=63, size=(600, 600))
            erase = drawing(n=20, seed=64)
            erase["frames"][0]["strokes"][3]["erase"] = True
            ref = {"shape": write_back(theo, L1, wide), "erase": write_back(theo, L1, erase),
                   "her own": write_back(ana, L1, drawing(n=20, seed=65))}
            words = {k: (v[0], v[1].get("error")) for k, v in ref.items()}
            check("on another shape, with an eraser, or on a letter you sent: refused",
                  words == {"shape": (400, "letter_shape"), "erase": (400, "letter_unsupported"),
                            "her own": (404, "letter_gone")}, json.dumps(words))
        except Exception as exc:  # noqa: BLE001
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "opened by a POST"):
        try:
            L7 = sent(ana, "theo", seed=70)
            for path in (f"/social/letters/{L7}/open", f"/social/letters/@ana", f"/social/letters/{L7}/write-back"):
                theo.client()._req("GET", path)
            after_get = letter(L7)["opened"]
            by_sender = act(ana, L7, "open")[0]
            after_sender = letter(L7)["opened"]
            by_him = act(theo, L7, "open")[0]
            check("a GET opens nothing (a prefetch can't), nor does its sender's POST; its recipient's POST does",
                  after_get is None and by_sender == 200 and after_sender is None and by_him == 200
                  and letter(L7)["opened"] is not None, f"{after_get} {by_sender} {after_sender} {by_him}")
        except Exception as exc:  # noqa: BLE001
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "take back"):
        try:
            L8 = sent(ana, "theo", seed=80)
            s8 = letter(L8)["sid"]
            by_him = act(theo, L8, "take-back")
            st, _ = act(ana, L8, "take-back")
            check("its sender takes it back before it is opened: the letter and its drawing go; its recipient can't",
                  by_him[0] == 404 and st == 200 and letter(L8) is None and drawing_of(s8) is None
                  and shut(reads(theo, s8)), f"{by_him} {st}")
            L8b = sent(ana, "theo", seed=81)
            act(theo, L8b, "open")
            st2, j2 = act(ana, L8b, "take-back")
            check("once opened it stays", st2 == 409 and j2.get("error") == "letter_opened" and letter(L8b) is not None,
                  f"{st2} {j2}")
        except Exception as exc:  # noqa: BLE001
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "delete from your side"):
        try:
            L9 = sent(ana, "theo", seed=90)
            s9 = letter(L9)["sid"]
            st1 = act(theo, L9, "delete")[0]
            one = {"theo": reads(theo, s9), "ana": reads(ana, s9), "again": act(theo, L9, "delete")[0]}
            check("deleted from his side: gone for him, there for her", st1 == 200 and shut(one["theo"])
                  and one["ana"] == OPEN and one["again"] == 404 and letter(L9)["r_del"] is not None, json.dumps(one))
            st2 = act(ana, L9, "delete")[0]
            check("once both have, the letter and its drawing go", st2 == 200 and letter(L9) is None
                  and drawing_of(s9) is None, f"{st2}")
        except Exception as exc:  # noqa: BLE001
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "report"):
        try:
            L10 = sent(ana, "theo", seed=100)
            s10 = letter(L10)["sid"]

            def report(who, lid):
                c = who.client()
                c.get("/social/")
                return c.post_json("/social/report", {"kind": "letter", "target": lid, "reason": "abuse"})[0]

            tries = {"ana (sender)": report(ana, L10), "cyd": report(cyd, L10)}
            before = reads(juno, s10)
            st = report(theo, L10)
            after = reads(juno, s10)
            check("its recipient reports it (its sender and anybody else can't); then the admins read it",
                  tries == {"ana (sender)": 404, "cyd": 404} and st == 202 and shut(before) and after == OPEN,
                  f"{tries} {st} {before} {after}")
            c = juno.client()
            st_q, page = c.get("/social/reports")
            card = L10 in page and f"/s/{s10}/poster" in page
            st_d = c.post_form("/social/reports/down", {"kind": "letter", "target": L10})
            r = letter(L10)
            check("in the queue, its picture; taken down, it is withheld and gone from his side; she still has hers",
                  st_q == 200 and card and st_d == 303 and r["down"] is not None
                  and (drawing_of(s10) or {}).get("visibility") == "withheld" and shut(reads(theo, s10))
                  and reads(ana, s10)[0] == 200 and act(theo, L10, "open")[0] == 404,
                  f"{st_q} {card} {st_d} {r and r['down']}")
        except Exception as exc:  # noqa: BLE001
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "deleting an account"):
        try:
            eve = someone(b, "eve", "Eve Stone")
            friends(eve, ana)
            got = [sent(eve, "ana", seed=110), sent(ana, "eve", seed=111)]
            sids = [letter(x)["sid"] for x in got if x]
            c = eve.client()
            c.get("/social/you/delete")
            st = c.post_form("/social/you/delete", {"confirm": "eve"})
            check("deleting an account takes every letter it sent or received, with their drawings",
                  st in (200, 303) and len(sids) == 2 and all(letter(x) is None for x in got)
                  and all(drawing_of(s) is None for s in sids), f"{st} {sids}")
        except Exception as exc:  # noqa: BLE001
            stopped(11, exc)

    # ------------------------------------------------------------------ 13
    PADDING = """() => { const f = document.querySelector('#letterPad .facepad-frame');
      return !!f && document.querySelector('#letterPad').classList.contains('is-ready'); }"""

    def pad_of(pg):
        pg.wait_for_function(PADDING, timeout=30000)
        fe = pg.query_selector("#letterPad .facepad-frame")
        fr = fe.content_frame()
        fr.wait_for_function("() => !!window.SkriblCompose && document.readyState === 'complete'", timeout=15000)
        pg.wait_for_timeout(400)
        return fe, fr

    def strokes(pg, fe, fr, n=3, at=(300, 200)):
        box = fr.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return [r.left, r.top, r.width]; }")
        fb = fe.bounding_box()
        k = box[2] / 816
        for i in range(n):
            x0, y0 = fb["x"] + box[0] + (at[0] + i * 40) * k, fb["y"] + box[1] + at[1] * k
            pg.mouse.move(x0, y0)
            pg.mouse.down()
            for s_ in range(1, 12):
                pg.mouse.move(x0 + s_ * 4 * k, y0 + (s_ % 4) * 7 * k)
            pg.mouse.up()
            pg.wait_for_timeout(120)

    def send_it(pg, fr):
        fr.click("#recordBtn")               # Done drawing, as a person presses it
        pg.wait_for_timeout(500)
        fr.click("#postBtn")
        pg.wait_for_timeout(600)
        sub = fr.query_selector("#postSubmitBtn")
        words = fr.evaluate("() => document.getElementById('postSubmitLabel').textContent")
        if sub and sub.is_visible():
            sub.click()
        return words

    PILL = """() => { const p = document.querySelector('.cs-pill, .db-pill');
      return p ? { text: p.querySelector('.da-where').textContent, cls: p.className } : null; }"""

    if part(13, "writing one in the Pad"):
        try:
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/@theo")
            ready(pg)
            pg.evaluate("() => SocialLetters.write({ to: 'theo', first: 'Theo' })")
            fe, fr = pad_of(pg)
            look = fr.evaluate("""() => ({ btn: document.querySelector('#postBtn .btn-label').textContent,
              sheet: document.getElementById('postSubmitLabel').textContent,
              dim: ['mediaOpenBtn', 'flipBtn'].map(i => getComputedStyle(document.getElementById(i)).opacity) })""")
            look["pill"] = fr.evaluate(PILL)
            check("SocialLetters.write opens the Pad over the page: its button and its sheet's say Send, its pill \"A letter"
                  " to Theo · only the two of you see it\" (A letter in bold), the photo and music drawer and the door to"
                  " Flip dimmed",
                  look["btn"] == "Send" and look["sheet"] == "Send" and look["pill"]
                  and look["pill"]["text"] == "A letter to Theo · only the two of you see it" and "cs-pill" in look["pill"]["cls"]
                  and look["dim"] == ["0.4", "0.4"], json.dumps(look))
            said = {}
            fr.click("#mediaOpenBtn")
            pg.wait_for_timeout(200)
            said["media"] = fr.evaluate("() => [document.getElementById('mediaOpenBtn').getAttribute('aria-expanded'), document.getElementById('toast').textContent]")
            fr.evaluate("() => document.getElementById('flipBtn').click()")
            pg.wait_for_timeout(300)
            said["flip"] = fr.evaluate("() => [location.pathname, document.getElementById('toast').textContent]")
            check("tapped, each says why and stays shut: \"Letters don’t carry photos or music yet.\", \"Letters are drawn"
                  " in the Pad for now.\" (the frame stays the Pad)",
                  said["media"] == ["false", "Letters don’t carry photos or music yet."]
                  and said["flip"][1] == "Letters are drawn in the Pad for now." and "flip" not in said["flip"][0],
                  json.dumps(said))
            before = len(db("select id from social_letters"))
            strokes(pg, fe, fr)
            with pg.expect_navigation(timeout=20000):
                words = send_it(pg, fr)
            got = db("select l.public_id, l.recipient_id, s.payload_json from social_letters l join skribl_posts s"
                     " on s.public_id = l.skribl_id order by l.id desc limit 1")
            pts = json.loads(got[0][2])["frames"][0]["strokes"] if got else []
            check("drawn and sent (its sheet saying Send), it lands on the two of you: a letter to him, his strokes in it",
                  words == "Send" and len(db("select id from social_letters")) == before + 1 and got
                  and got[0][1] == pid_of("theo")[0] and len(pts) >= 30, f"{words} {len(pts)} {pg.url}")
            close_ctx(ctx, pg)
            # A SEND THAT DOES NOT GO keeps the drawing.
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/@theo")
            ready(pg)
            pg.evaluate("() => SocialLetters.write({ to: 'theo', first: 'Theo' })")
            fe, fr = pad_of(pg)
            strokes(pg, fe, fr, n=2)
            block(theo, ana)
            send_it(pg, fr)
            pg.wait_for_function("() => { const t = document.querySelector('.mu-toast, [data-toast], .toast'); return !!t && /follow each other/.test(t.textContent); }",
                                 timeout=15000)
            toast = pg.evaluate("() => (document.querySelector('.mu-toast, [data-toast], .toast') || {}).textContent")
            n_after = len(db("select id from social_letters"))
            block(theo, ana, on=False)
            friends(ana, theo)
            pg.evaluate("() => SocialLetters.write({ to: 'theo', first: 'Theo' })")
            fe, fr = pad_of(pg)
            kept = fr.evaluate("() => (typeof strokes !== 'undefined' ? strokes.length : -1)")
            close_ctx(ctx, pg)
            check("a send that does not go (a block meanwhile) says why, kindly, sends nothing, and keeps the drawing:"
                  " Write again opens the Pad with it",
                  "follow each other" in (toast or "") and n_after == before + 1 and kept > 0, f"{toast!r} {n_after} {kept}")
        except Exception as exc:  # noqa: BLE001
            stopped(13, exc)

    # ------------------------------------------------------------------ 14
    if part(14, "writing back in the Pad"):
        try:
            friends(ana, theo)
            L14 = sent(ana, "theo", drawing(n=60, seed=140))
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/@ana")
            ready(pg)
            pg.evaluate("(id) => SocialLetters.writeBack({ id, first: 'Ana' })", L14)
            fe, fr = pad_of(pg)
            fr.wait_for_function("() => !!window.SkriblDrawBack && !!SkriblDrawBack.state()", timeout=15000)
            look = fr.evaluate("""() => ({ size: getCanvasLogicalSize(), ground: String(bgColor).toLowerCase(),
              under: SkriblDrawBack.state().strokes, btn: document.querySelector('#postBtn .btn-label').textContent,
              dim: ['eraserToolBtn', 'mediaOpenBtn'].map(i => getComputedStyle(document.getElementById(i)).opacity) })""")
            look["pill"] = fr.evaluate(PILL)
            check("SocialLetters.writeBack opens the Pad on her shape and paper, hers faint under the pen, Draw back's pill"
                  " saying \"Writing back to Ana · only the two of you see it\", Send, the eraser and the drawer aside",
                  look["size"] == {"width": 816, "height": 612} and look["ground"] == "#f6f2ea" and look["under"] >= 1
                  and look["pill"] and look["pill"]["text"] == "Writing back to Ana · only the two of you see it"
                  and "db-pill" in look["pill"]["cls"] and look["btn"] == "Send" and look["dim"] == ["0.4", "0.4"],
                  json.dumps(look))
            strokes(pg, fe, fr, n=2, at=(560, 420))
            with pg.expect_navigation(timeout=20000):
                send_it(pg, fr)
            got = db("select l.written_on_id, l.recipient_id, s.payload_json from social_letters l join skribl_posts s"
                     " on s.public_id = l.skribl_id order by l.id desc limit 1")
            pts = json.loads(got[0][2])["frames"][0]["strokes"] if got else []
            close_ctx(ctx, pg)
            check("sent, the letter is written back on: to her, hers first (her 60 points), then his",
                  got and got[0][0] == letter(L14)["id"] and got[0][1] == pid_of("ana")[0] and len(pts) > 60
                  and xy(pts[:60]) == xy(drawing(n=60, seed=140)["frames"][0]["strokes"]), f"{got and got[0][:2]} {len(pts)}")
            # The pill on fresh paper: over the drawing, it goes at the first stroke.
            ctx, pg = browser_as(b, ana, screen="desk")
            pg.goto(BASE + "/social/@theo")
            ready(pg)
            pg.evaluate("() => SocialLetters.write({ to: 'theo', first: 'Theo' })")
            fe, fr = pad_of(pg)
            over = fr.evaluate("""() => { const p = document.querySelector('.cs-pill').getBoundingClientRect(), c = document.getElementById('canvas').getBoundingClientRect();
              return p.bottom > c.top && p.top < c.bottom && p.right > c.left && p.left < c.right; }""")
            strokes(pg, fe, fr, n=1)
            pg.wait_for_timeout(400)
            after = fr.evaluate("() => !!document.querySelector('.cs-pill')")
            close_ctx(ctx, pg)
            check("on fresh paper a pill clear of the drawing stays after the first stroke, and one over the drawing goes",
                  after == (not over), f"over the drawing {over}; there after {after}")
        except Exception as exc:  # noqa: BLE001
            stopped(14, exc)

    # ------------------------------------------------------------------ 15
    if part(15, "the pages"):
        try:
            friends(ana, theo)
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/@ana")
            ready(pg)
            shot(pg, "profile-phone-light")
            row = pg.evaluate("""() => [...document.querySelectorAll('.prof-acts > *')].map(e => e.matches('[data-lt-write]')
              ? ['write', e.textContent.trim(), Math.round(e.getBoundingClientRect().height)] : [e.className.split(' ')[1] || e.className])""")
            close_ctx(ctx, pg)
            seen = {}
            for who, at in ((dee, "/social/@ana"), (ana, "/social/@ana"), (cyd, "/social/@dee")):
                ctx, pg = browser_as(b, who)
                pg.goto(BASE + at)
                ready(pg)
                seen[f"{who.handle} on {at}"] = pg.evaluate("() => !!document.querySelector('[data-lt-write]')")
                close_ctx(ctx, pg)
            check("Write sits beside Following on a friend's page (Following, Write, Share, ⋯), 44px, saying Write; not"
                  " on somebody who doesn't follow back, not on your own page",
                  [r[0] for r in row][:2] == ["fo-btn", "write"] and row[1][1] == "Write" and row[1][2] >= 44
                  and not any(seen.values()), f"{row} {seen}")
            # A letter waits for Theo, and only it.
            for (lid,) in db("select public_id from social_letters where recipient_id = ? and opened_at is null", (pid_of("theo")[0],)):
                act(theo, lid, "open")
            L15 = sent(ana, "theo", drawing(n=50, seed=150))
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/")
            ready(pg)
            shot(pg, "home-phone-light")
            top = pg.evaluate("""() => { const e = document.querySelector('.top-letters'), bell = document.querySelector('.top-bell');
              return e ? { dot: !!e.querySelector('.act-dot'), label: e.getAttribute('aria-label'), next: e.nextElementSibling === bell,
                           h: Math.round(e.getBoundingClientRect().height) } : null; }""")
            pg.goto(BASE + "/social/letters")
            ready(pg)
            shot(pg, "letters-phone-light")
            rows_ = pg.evaluate("""() => [...document.querySelectorAll('.lt-row')].map(r => ({ say: r.querySelector('.act-say').textContent.trim(),
              peek: (r.querySelector('.act-peek') || {}).textContent || null, sealed: !!r.querySelector('.lt-seal'), dot: r.classList.contains('is-new'),
              href: new URL(r.href).pathname + new URL(r.href).hash }))""")
            only = pg.evaluate("() => (document.querySelector('.lt-only') || {}).textContent")
            close_ctx(ctx, pg)
            check("the envelope sits beside the bell at the top of Home (44px), its dot when a letter waits",
                  top and top["dot"] and top["next"] and top["h"] >= 44 and top["label"] == "Letters, a new one", json.dumps(top))
            new = [r for r in rows_ if r["dot"]]
            check("Letters: a new letter's row is sealed (the envelope, not its picture), its dot, \"Ana drew you a letter\","
                  " \"It draws itself when you open it\", opening the two of you at it; \"Only the two of you ever see a letter.\"",
                  new and new[0]["sealed"] and new[0]["say"] == "Ana drew you a letter"
                  and new[0]["peek"] == "It draws itself when you open it" and new[0]["href"] == f"/social/letters/@ana#l-{L15}"
                  and only == "Only the two of you ever see a letter.", json.dumps(rows_[:3]))
            ctx, pg = browser_as(b, theo, screen="desk")
            pg.goto(BASE + "/social/")
            ready(pg)
            shot(pg, "home-desk-light")
            rail = pg.evaluate("""() => { const t = [...document.querySelectorAll('.nav .tab')].filter(e => e.getClientRects().length).map(e => e.textContent.trim());
              const l = document.querySelector('.nav .tab-letters'); return { tabs: t, dot: !!(l && l.querySelector('.act-dot')) }; }""")
            close_ctx(ctx, pg)
            ai = rail["tabs"].index("Activity") if "Activity" in rail["tabs"] else -9
            check("on a desk, Letters in the rail right under Activity, with its dot",
                  ai >= 0 and rail["tabs"][ai + 1:ai + 2] == ["Letters"] and rail["dot"], json.dumps(rail))
            # The two of you: it draws itself, and is opened as it plays.
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/letters/@ana")
            ready(pg)
            pg.wait_for_function("(id) => { const b = document.querySelector('#l-' + id + ' [data-skribl-inline]'); return b && b.classList.contains('is-playing'); }",
                                 arg=L15, timeout=15000)
            for _ in range(40):
                if letter(L15)["opened"]:
                    break
                time.sleep(0.25)
            opened = letter(L15)["opened"]
            acts = pg.evaluate("""(id) => { const s = document.getElementById('l-' + id);
              return [...s.querySelectorAll('.lt-acts .btn')].map(b => b.textContent.trim()); }""", L15)
            pg.click(f"#l-{L15} [data-lt-write-back]")
            pg.wait_for_function("() => !!SocialLetters.writing() && SocialLetters.isOpen()", timeout=20000)
            wb = pg.evaluate("() => SocialLetters.writing()")
            pg.goto(BASE + "/social/")
            ready(pg)
            dot_after = pg.evaluate("() => !!document.querySelector('.top-letters .act-dot')")
            close_ctx(ctx, pg)
            check("the two of you: the new letter draws itself, and is opened as it plays (the envelope's dot goes);"
                  " under it Write back and New letter, and Write back opens the Pad on it",
                  opened is not None and acts == ["Write back", "New letter"] and wb and wb.get("id") == L15
                  and not dot_after, f"{opened} {acts} {wb} {dot_after}")
            # The mark where the hand changes, on a written-back letter.
            st, j = write_back(theo, L15, drawing(n=20, seed=151))
            LB = j.get("letter") if isinstance(j, dict) else None
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/letters/@theo")
            ready(pg)
            pg.wait_for_timeout(4000)
            shot(pg, "two-of-you-phone-light")
            marks = pg.evaluate("(id) => { const b = document.querySelector('#l-' + id + ' [data-skribl-inline]'); return b && JSON.parse(b.getAttribute('data-skribl-marks') || 'null'); }", LB)
            hands = pg.evaluate("(id) => (document.querySelector('#l-' + id + ' .lt-hands') || {}).textContent", LB)
            pg.goto(BASE + "/social/letters")
            ready(pg)
            ids = pg.evaluate("() => [...document.querySelectorAll('.lt-row')].map(r => new URL(r.href).hash.slice(3))")
            close_ctx(ctx, pg)
            check("a sheet once: the letter written back on is inside the one written on it, never a row of its own",
                  LB in ids and L15 not in ids, f"{ids}")
            check("a written-back letter carries the mark where his hand starts on its line, and says whose hands, in order",
                  marks == [{"ms": letter(LB)["hand_at"]}] and hands == "Yours, then Theo’s", f"{marks} {hands!r}")
            # The ⋯: Take back (yours, not opened) and Report (one that came to you).
            LT = sent(ana, "theo", seed=152)
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/letters/@theo")
            ready(pg)
            pg.click(f"#l-{LT} [data-lt-more]")
            pg.wait_for_timeout(500)
            shown = pg.evaluate("() => [...document.querySelectorAll('#letterSheet [data-lt-act]')].filter(b => !b.hidden).map(b => b.getAttribute('data-lt-act'))")
            pg.click('#letterSheet [data-lt-act="take-back"]')
            for _ in range(40):
                if letter(LT) is None:
                    break
                time.sleep(0.25)
            pg.wait_for_timeout(600)
            left = pg.evaluate("(id) => !!document.getElementById('l-' + id)", LT)
            close_ctx(ctx, pg)
            check("the ⋯ of your letter not opened yet has Take back (no Delete, no Report) and Block; Take back takes it"
                  " back, and its sheet folds away", shown == ["take-back", "block"] and letter(LT) is None and not left,
                  f"{shown} {left}")
            LR = sent(ana, "theo", seed=153)
            act(theo, LR, "open")
            ctx, pg = browser_as(b, theo)
            pg.goto(BASE + "/social/letters/@ana")
            ready(pg)
            pg.click(f"#l-{LR} [data-lt-more]")
            pg.wait_for_timeout(500)
            shown2 = pg.evaluate("() => [...document.querySelectorAll('#letterSheet [data-lt-act]')].filter(b => !b.hidden).map(b => b.getAttribute('data-lt-act'))")
            pg.click('#letterSheet [data-lt-act="report"]')
            pg.wait_for_timeout(600)
            pg.click('#letterReportSheet button[type="submit"]')
            for _ in range(40):
                if db("select id from social_reports where kind = 'letter' and target = ?", (LR,)):
                    break
                time.sleep(0.25)
            close_ctx(ctx, pg)
            check("the ⋯ of a letter that came to you has Delete, Report and Block; its Report sends a report of the letter",
                  shown2 == ["delete", "report", "block"]
                  and bool(db("select id from social_reports where kind = 'letter' and target = ?", (LR,))), f"{shown2}")
            fay = someone(b, "fay", "Fay Lund")
            follow(ana, fay)                 # Ana follows Fay; Fay does not follow back
            ctx, pg = browser_as(b, ana)
            pg.goto(BASE + "/social/letters/write")
            ready(pg)
            people = pg.evaluate("() => [...document.querySelectorAll('[data-lt-write]')].map(b => b.getAttribute('data-handle'))")
            close_ctx(ctx, pg)
            block(cyd, theo)
            ctx, pg = browser_as(b, cyd)
            st_b = status(pg, "/social/letters/@theo")
            close_ctx(ctx, pg)
            block(cyd, theo, on=False)
            check("Write's list is the people who follow each other with you (not one who follows you, nor one you"
                  " follow, one way); behind a block"
                  " there is no page of the two of you", sorted(people) == ["cyd", "theo"] and st_b == 404,
                  f"{people} {st_b}")
        except Exception as exc:  # noqa: BLE001
            stopped(15, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001
            stopped(12, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
