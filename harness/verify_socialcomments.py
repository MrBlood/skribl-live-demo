"""Comments on the Skribl site (phase 2, comments; docs/SOCIAL-SITE.md "Built:
phase 2, comments"), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. THE SECTION: a post's page says "Comments" and how many, and at the
     heading's end the icon that opens the box (folded away until asked for:
     a phone's sheet, "Say something to Juno": their face, "Say something, or
     draw it…", Draw, Flip, Post); signed out, the comments are readable and
     the icon raises "Say something?"; Post with nothing written or drawn
     says so and sends nothing.
  2. COMMENTING, NEWEST FIRST: the box sends the words (tidied, as a post's);
     the new comment fades in at the top, the count with it; its time is
     short ("now", "40m"); its row names the post and the person.
  3. ANSWERS, ONE LEVEL DEEP: Answer opens the box for the comment (a phone's
     sheet, "Answer Theo"; a desk's fold under the conversation, "Answer
     Theo…"), the comment keeping its place on the screen; answers sit under
     it oldest first; an answer to an answer sits under the same comment; on
     a desk, Answer again and Esc fold it away, and under a long thread the
     page glides to it.
  4. THE ⋯ SHEET: Your comment (Delete comment); somebody else's on your own
     post ("Theo’s comment": Remove from my post, Report comment); anybody
     else's (Report comment); signed out, Report comment.
  5. DELETE AND REMOVE: your own comment goes, its answers with it, fading
     out; on your own post anybody's is removed the same way; nobody else
     can; an answer goes alone.
  6. WHO MAY COMMENT: the token, signed in, not taken down, no block either
     way with the post's author (or, answering, the comment's), words tidied
     and checked as a post's, the flood limit.
  7. HIDDEN: a block either way, or a person taken down: their comments, and
     the answers under them, neither shown nor counted, on the post's page
     and on Home's card.
  8. REPORTED AND TAKEN DOWN: Report comment, a post's reasons, into the
     site's queue; Your Reports' comment card (its words, whose, a link to
     it); Take it down hides it from everybody but its author, who sees the
     note; Keep it hides nothing.
  9. DELETING A POST OR AN ACCOUNT takes its comments, and an account the
     answers under its own, in code (shown with the database's cascade off).
 10. LOAD MORE: twenty comments a page, the next in place, none twice.
 11. HOME'S CARD: how many comments beside the plays, "N comments", a way to
     them; at none the icon alone, "Comment" (the owner's yes, Nov 12).
 12. ON A DESK: the comments beside the drawing, under Share; the icon at
     their heading's end; the box opening right under it.
 13. THE NEW SCREENS: every word at 4.5:1 on what is painted behind it, every
     target 44px, every text field 16px: phone and desk, light and dark.
 14. A DRAWING ANSWER, IN THE BOX: Draw and Flip open Skribl's editor over
     the post in compose mode, no gallery tick; Add hands the drawing back
     into the box's own in-post player, Edit drawing reopens it, Remove takes
     it away.
 15. A DRAWING ANSWER, POSTED: unlisted through create_post, its id on the
     comment; alone, or as an answer; still (not even fetched) until tapped
     while the post's own drawing plays by itself; listed nowhere.
 16. A DRAWING GOES WITH ITS COMMENT: deleted, removed, its post deleted, its
     person's account deleted (Skribl's delete_post, as its author).
 17. A DRAWING ANSWER REPORTED AND TAKEN DOWN: its picture on Your Reports'
     card, what Skribl's own link page reported of it on the same card;
     withheld in Skribl with it.
 18. THE BOX WITH A DRAWING: words at 4.5:1, targets 44px; phone and desk,
     light and dark.
 19. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last, after
     20 to 28).

COMMENTS ON EVERY DRAWING (the owner's yes, Nov 12): a drawing shown outside
a post (made in the Pad, shown in the gallery: /social/b/<id>) has them too.
 20. ITS PAGE HAS THE SECTION: the box, a comment on the drawing (its row on
     the drawing, whose it is kept), signed out readable, Load more.
 21. ANSWERS AND DRAWING ANSWERS on a drawing: one level deep; the real Pad
     over its page; unlisted through create_post.
 22. THE ⋯, DELETE AND REMOVE: by its author, and by the drawing's owner.
 23. BLOCKS AND TAKEDOWNS: a block between commenters, or either way with the
     drawing's maker; a person, the drawing, or its maker taken down.
 24. THE DRAWING DELETED: through the site its comments go, in code; in the
     Library its page goes, and its comments with it.
 25. THE ACCOUNT DELETED: every comment on its drawings, and its own on
     others', in code (shown with the database's cascade off).
 26. REPORTED AND TAKEN DOWN on a drawing; Home's card counts its comments.
 27. THE CHAIN on a populated database: on a post or a drawing, exactly one;
     and back down.
 28. THE NEW SCREENS on a drawing's page: words at 4.5:1, targets 44px, text
     fields 16px; phone and desk, light and dark.

THE COMMENT BOX IS AN ICON (the owner, Nov 13: "The comment needs to be an icon
not a card. It takes up too much room sitting there", then "Yes to all"):
 29. THE ICON at the heading's end (44px, round, its line 3:1 off the pixels,
     lit while open), the heading keeping its height, the box folded away
     (no room, unseen, nothing focusable); nobody who may not comment offered it.
 30. A PHONE: the box rises on Make's sheet, ready (read on every frame, the
     page under it still and inert); the dimmed page, a drag down or Esc puts
     it away, keeping the words; on a keyboard (stood in) it rides above it;
     Draw opens the Pad over it, and the page stays inert behind it after.
 31. A DESK: the box glides open under the heading (read on every frame),
     the icon lit; a second click, Esc or a press elsewhere folds it away,
     keeping the words; the Pad over the page is not "elsewhere".
 32. ANSWER: a phone's sheet, "Answer Theo" and Theo's words in a line; a
     desk's fold under the conversation, folding first from the heading,
     Answer again folding it; the page glides to it under a long thread.
 33. POSTED: the box goes as the comment comes, glowing in the landing's tint
     that fades; on a desk in step; "Posting…" on Post, no line growing the
     box; the box emptied once it has gone.
 34. SIGNED OUT, "Say something?" and Sign in back with the box open (#say,
     nothing posted, the address cleaned); "Say the first thing" at none.
 35. REDUCE MOTION: the sheet fades where it sits; a desk's box is put in
     place and fades; a posted comment too.
 36. A DRAWING'S OWN PAGE: the same.
 37. THE NEW SCREENS: every word at 4.5:1, targets 44px, fields 16px; phone
     and desk, light and dark.

SOCIALCOMMENTS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Comments at /social", "Comments on
every drawing" and "The comment box is an icon".
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
PART = os.environ.get("SOCIALCOMMENTS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALCOMMENTS {n} — {label}")
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
    print("No assertions were executed. This is NOT evidence comments work.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)


import artdraw  # noqa: E402  -- a real pen in the real Pad (harness/tools)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialcomments-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialcomments-" + secrets.token_hex(8),
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

    def get_json(self, path):
        st, text = self._req("GET", path)
        try:
            return st, json.loads(text)
        except ValueError:
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


def ready(pg):
    pg.wait_for_function("() => !!window.SocialSheet && !!window.SocialWhen && document.readyState === 'complete'",
                         timeout=15000)


def open_post(pg, post):
    pg.goto(BASE + f"/social/p/{post}")
    ready(pg)
    pg.wait_for_timeout(300)


# ---- a drawing shown outside a post (sections 20 to 28) --------------------------
# A drawing posted from the Pad on its own page (Make's Draw), as the Pad posts
# it: Skribl's API, as the person signed in, its own token from its own cookie
# (verify_socialposts section 9's).
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
# Deleted in the Library, as its author: Skribl's own DELETE, not the site's.
LIBRARY_DELETE = """async (id) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const r = await fetch('/api/skribls/' + id, { method: 'DELETE', credentials: 'same-origin',
    headers: { 'X-Skribl-CSRF': decodeURIComponent(tok) } });
  return r.status; }"""


def make_drawing(who, title, seed=0, vis="public"):
    """A drawing from the Pad, shown in the gallery: its skribl's public id, or None."""
    who.pg.goto(BASE + "/social/")
    st, sid = who.pg.evaluate(PAD, [title, vis, seed])
    return sid if st == 201 else None


def say_on(who, sid, words, answer_to=None, payload=None):
    """A comment on a drawing (or an answer, or a drawing answer) as the box
    sends one: (status, answer)."""
    c = who.client()
    c.get(f"/social/b/{sid}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    if payload is not None:
        body["payload"] = payload
    return c.post_json(f"/social/b/{sid}/comments", body)


def said_on(who, sid, words, answer_to=None, payload=None):
    st, j = say_on(who, sid, words, answer_to, payload)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


def open_drawing(pg, sid):
    pg.goto(BASE + f"/social/b/{sid}")
    ready(pg)
    pg.wait_for_timeout(300)


def on_row(cid):
    """What a comment's row says it is on: (post_id, drawing_id, owner's handle, parent's public id)."""
    got = db("select c.post_id, c.drawing_id, o.handle, p.public_id from social_comments c"
             " join social_people o on o.id = c.owner_id left join social_comments p on p.id = c.parent_id"
             " where c.public_id = ?", (cid or "",))
    return got[0] if got else None


def skribl_there(*sids):
    return [bool(db("select 1 from skribl_posts where public_id = ?", (s or "",))) for s in sids]


def card_count(pg, sid):
    """Home's card for a drawing, as `pg` sees it: its comments' link, or None."""
    pg.goto(BASE + "/social/")
    pg.wait_for_timeout(600)
    return pg.evaluate("""(sid) => { const c = document.querySelector('.post-card[data-skribl="' + sid + '"]');
      if (!c) return null; const n = c.querySelector('.post-count'); if (!n) return { none: true };
      const r = n.getBoundingClientRect();
      return { label: n.getAttribute('aria-label'), text: n.textContent.trim(), icon: !!n.querySelector('svg'),
               href: new URL(n.href).pathname + new URL(n.href).hash, w: r.width, h: r.height }; }""", sid)


# The section as the page shows it: each comment, and the answers under it.
SECTION = """() => { const one = li => ({ id: li.dataset.comment, name: li.querySelector(':scope > .cm-main .cm-name').textContent,
    when: li.querySelector(':scope > .cm-main .cm-when').textContent,
    words: (li.querySelector(':scope > .cm-main .cm-words') || {}).textContent || '',
    down: (li.querySelector(':scope > .cm-main .cm-down') || {}).textContent || null,
    answer: !!li.querySelector(':scope > .cm-main [data-cm-answer]') });
  return { count: (() => { const c = document.querySelector('[data-cm-count]'); return c && !c.hidden ? c.textContent : null; })(),
    list: [...document.querySelectorAll('[data-cm-list] > .cm')].map(li => Object.assign(one(li),
      { answers: [...li.querySelectorAll(':scope > .cm-answers > .cm')].map(one) })) }; }"""
OPEN = "(id) => document.getElementById(id).classList.contains('is-open')"
ACTS = "(s) => [...document.querySelectorAll(s + ' .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())"
REASONS = "(s) => [...document.querySelectorAll(s + ' input[name=reason]')].map(i => [i.value, i.closest('label').textContent.trim()])"
POST_REASONS = [["spam", "Spam or misleading"], ["abuse", "Abusive or hateful"],
                ["copyright", "Copies someone else’s work"], ["child_safety", "A child’s safety"],
                ["other", "Something else"]]
THANKS = "Thanks. The people who run this site will look at it."
NOTE = "Taken down: it broke the rules. Only you can see it."

# Post through the box, and read the new comment's opacity on every frame from
# the press until it has been shown a while: (its id, the opacities).
POST_AND_WATCH = """async () => {
  const before = new Set([...document.querySelectorAll('.cm')].map(e => e.dataset.comment));
  document.querySelector('[data-cm-post]').click();
  const t0 = performance.now(), ops = []; let li = null;
  await new Promise(res => { const step = () => {
    li = li || [...document.querySelectorAll('.cm')].find(e => !before.has(e.dataset.comment));
    if (li) ops.push(Math.round(+getComputedStyle(li).opacity * 100) / 100);
    if ((li && ops.length >= 30) || performance.now() - t0 > 10000) res(); else requestAnimationFrame(step); };
    requestAnimationFrame(step); });
  return { id: li ? li.dataset.comment : null, ops }; }"""

# A comment's ⋯, then Delete comment or Remove from my post (act), and the
# comment's opacity on every frame until it has gone.
DELETE_AND_WATCH = """async ([id, act]) => {
  const li = document.getElementById('c-' + id);
  li.querySelector(':scope > .cm-main [data-cm-menu]').click();
  await new Promise(r => setTimeout(r, 450));
  document.querySelector('#commentSheet [data-cm-act=' + act + ']').click();
  const t0 = performance.now(), ops = [];
  await new Promise(res => { const step = () => { if (li.isConnected) ops.push(Math.round(+getComputedStyle(li).opacity * 100) / 100);
    if (!li.isConnected || performance.now() - t0 > 8000) res(); else requestAnimationFrame(step); }; requestAnimationFrame(step); });
  return { gone: !li.isConnected, ops, count: (document.querySelector('[data-cm-count]') || {}).textContent }; }"""

# ---- THE COMMENT BOX IS AN ICON (the owner, Nov 13: "The comment needs to be an
# icon not a card"; "Yes to all"). The box is folded away behind the icon at the
# heading's end: a phone opens it on Make's own sheet, a desk in place (the
# fold). These open it as a person does, and read where it is.
BOX = """() => { const b = document.querySelector('[data-cm-box]'); if (!b) return null;
  const w = b.querySelector('[data-cm-words]'), fold = document.querySelector('[data-cm-fold]');
  const sheet = document.getElementById('commentBoxSheet'), inSheet = !!sheet && sheet.contains(b);
  const at = fold && fold.parentElement.classList.contains('cm') ? fold.parentElement.dataset.comment : null;
  const open = inSheet ? (sheet.classList.contains('is-open') ? 'sheet' : null)
                       : (fold && fold.classList.contains('is-open') ? (at ? 'under' : 'home') : null);
  const q = sheet && sheet.querySelector('[data-cm-quote]'), i = document.querySelector('.cm-say');
  return { placeholder: w.placeholder, label: b.querySelector('[data-cm-label]').textContent,
    under: at, home: !at, open, inSheet, title: sheet ? sheet.querySelector('[data-cm-sheet-title]').textContent : null,
    quote: q && !q.hidden ? q.textContent : null, focus: document.activeElement === w,
    face: !!b.querySelector('.face-ring'), post: (b.querySelector('[data-cm-post]') || {}).textContent || null,
    chips: [...b.querySelectorAll('.chip')].filter(c => c.getClientRects().length).map(c => c.textContent.trim()),
    font: parseFloat(getComputedStyle(w).fontSize), words: w.value, icon: i ? i.getAttribute('aria-expanded') : null }; }"""
# Open and at rest: a phone's sheet risen (or faded in) all the way, or a desk's fold open and still.
BOX_STILL = """() => { const s = document.getElementById('commentBoxSheet'), f = document.querySelector('[data-cm-fold]');
  const m = s && s.querySelector('.make-sheet'), cs = m && getComputedStyle(m);
  return !!((s && !s.hidden && s.classList.contains('is-open') && cs.transform === 'none' && +cs.opacity === 1)
            || (f && f.classList.contains('is-still'))); }"""
# Post's place in the box: its left edge, and how far below the first chip it
# sits (the same line, or the next), so a counter that moved it shows.
POST_AT = """() => { const p = document.querySelector('[data-cm-post]').getBoundingClientRect();
  const boxEl = document.querySelector('[data-cm-box]'), box = boxEl.getBoundingClientRect(), cs = getComputedStyle(boxEl);
  const c = document.querySelector('[data-cm-box] .composer-acts .chip').getBoundingClientRect();
  const post = document.querySelector('[data-cm-post]'), was = post.textContent, w1 = p.width;
  const w = document.querySelector('[data-word="c_posting"]'), word = w ? w.textContent : '';
  post.textContent = word;
  const busy = post.getBoundingClientRect(), said = post.textContent;
  post.textContent = was;
  // Held by comments.js as its least width (in any font: it measures the word
  // in the font it is drawn in); this box's font fits both words in 96px
  // anyway, so the hold is asked of directly too.
  const w3 = parseFloat(post.style.minWidth) || 0, w4 = Math.ceil(busy.width) <= w3 ? w3 : -1;
  return { x: Math.round(p.left), dy: Math.round(p.top - c.top),
           edge: Math.round(box.right - parseFloat(cs.paddingRight) - p.right),
           foot: Math.round(box.bottom - parseFloat(cs.paddingBottom) - p.bottom),
           posting: said, held: Math.abs(busy.width - w1) < 0.5 && Math.abs(busy.top - p.top) < 0.5 && Math.abs(w4 - w3) < 0.5,
           sides: getComputedStyle(post).paddingLeft + ' ' + getComputedStyle(post).paddingRight }; }"""
# When what is in the box is wider than its line, whatever the font: the chips'
# words spread (as a wider font or larger text would make them), then something
# far wider than the column put in the box. The box keeps to its column, the
# chips and Post keep inside it, and Post keeps to its right edge. Restored
# after; set through the style object, which the page's policy allows.
TOO_WIDE = """() => { const boxEl = document.querySelector('[data-cm-box]'), sec = document.getElementById('comments');
  const words = [...boxEl.querySelectorAll('.composer-acts .chip span')];
  words.forEach(w => { w.style.letterSpacing = '6px'; });
  const cs = getComputedStyle(boxEl), inner = boxEl.getBoundingClientRect().right - parseFloat(cs.paddingRight);
  const box = boxEl.getBoundingClientRect(), post = boxEl.querySelector('[data-cm-post]').getBoundingClientRect();
  const chips = [...boxEl.querySelectorAll('.composer-acts .chip')].map(c => c.getBoundingClientRect().right);
  const spread = { box: Math.round(box.width), col: Math.round(sec.getBoundingClientRect().width),
                   edge: Math.round(inner - post.right), chipsIn: chips.every(r => r <= inner + 0.5) };
  words.forEach(w => { w.style.letterSpacing = ''; });
  const wide = document.createElement('div');
  wide.style.width = '600px'; wide.style.height = '1px';
  boxEl.appendChild(wide);
  const withWide = Math.round(boxEl.getBoundingClientRect().width);
  wide.remove();
  return Object.assign(spread, { withWide: withWide }); }"""
# Near the limit: the box against what holds it (the comments' column, or the
# comment it answers), Post's place, and the counter, asked of what is painted.
NEAR_LIMIT = """() => { const q = s => document.querySelector(s);
  const boxEl = q('[data-cm-box]'), left = q('[data-cm-left]');
  left.scrollIntoView({ block: 'center' });
  const holder = (boxEl.closest('.cm') || document.getElementById('comments')).getBoundingClientRect();
  const box = boxEl.getBoundingClientRect(), post = q('[data-cm-post]').getBoundingClientRect(), lr = left.getBoundingClientRect();
  const chip = q('[data-cm-box] .composer-acts .chip').getBoundingClientRect();
  const hit = document.elementFromPoint(lr.left + lr.width / 2, lr.top + lr.height / 2);
  return { text: left.textContent.trim(), painted: !!hit && (hit === left || left.contains(hit)),
           box: Math.round(box.width), holder: Math.round(holder.width), right: Math.round(box.right),
           holderRight: Math.round(holder.right), x: Math.round(post.left), dy: Math.round(post.top - chip.top),
           under: Math.round(lr.top - post.bottom), edge: Math.round(post.right - lr.right) }; }"""
GONE = """() => { const s = document.getElementById('commentBoxSheet'), f = document.querySelector('[data-cm-fold]');
  return (!s || s.hidden) && (!f || (!f.classList.contains('is-open') && f.parentElement.id === 'comments')); }"""
# The icon, the heading it sits in, and the box folded under it.
ICON = """() => { const b = document.querySelector('.cm-say'); if (!b) return null;
  const h = document.querySelector('.comments-head'), t = document.getElementById('commentsTitle'), sec = document.getElementById('comments');
  const r = b.getBoundingClientRect(), hr = h.getBoundingClientRect(), tr = t.getBoundingClientRect(), sr = sec.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const lands = [[cx, cy], [cx - 19, cy], [cx + 19, cy], [cx, cy - 19], [cx, cy + 19]].map(([x, y]) => {
    const e = document.elementFromPoint(x, y); return !!e && (e === b || b.contains(e)); });
  const list = document.querySelector('[data-cm-list]').getBoundingClientRect();
  const fold = document.querySelector('[data-cm-fold]'), inner = fold && fold.querySelector('.cm-fold-in');
  return { name: b.getAttribute('aria-label'), tip: b.getAttribute('title'), w: r.width, h: r.height,
    round: getComputedStyle(b).borderTopLeftRadius, right: Math.round((sr.right - r.right) * 100) / 100,
    centre: Math.round((cy - (tr.top + tr.height / 2)) * 100) / 100, head: Math.round(hr.height * 100) / 100,
    line: Math.round(tr.height * 100) / 100, lands: lands.every(Boolean), gap: Math.round((list.top - hr.bottom) * 100) / 100,
    expanded: b.getAttribute('aria-expanded'), popup: b.getAttribute('aria-haspopup'), controls: b.getAttribute('aria-controls'),
    plus: b.querySelectorAll('svg path').length,
    fold: fold ? { h: Math.round(fold.getBoundingClientRect().height * 100) / 100, seen: getComputedStyle(inner).visibility,
                   laid: fold.querySelector('[data-cm-words]').getClientRects().length > 0 } : null }; }"""
# What the signed-out sheet says, and where its Sign in goes.
OUT_SHEET = """() => { const w = document.getElementById('commentOutSheet'); if (!w) return null; const a = w.querySelector('a.btn');
  const i = document.querySelector('.cm-say');
  return { open: w.classList.contains('is-open') && !w.hidden, title: w.querySelector('.make-title').textContent,
    lit: i ? getComputedStyle(i).backgroundColor === getComputedStyle(document.querySelector('.composer-post, .btn-primary')).backgroundColor : null,
    lede: w.querySelector('.post-lede').textContent, acts: [...w.querySelectorAll('.post-sheet-acts .btn')].map(e => e.textContent.trim()),
    next: a ? new URL(a.href).searchParams.get('next') : null, path: a ? new URL(a.href).pathname : null,
    focus: document.activeElement ? document.activeElement.textContent.trim() : null,
    old: !!document.querySelector('.cm-signin') }; }"""
# "Say the first thing", where the comments will be at none.
FIRST_LINE = """() => { const b = document.querySelector('[data-cm-first]'); if (!b) return null;
  const f = document.querySelector('[data-cm-first-fold]'), r = b.getBoundingClientRect(), h = document.querySelector('.comments-head').getBoundingClientRect();
  const c = getComputedStyle(b);
  return { words: b.textContent.trim(), open: f.classList.contains('is-open'), w: r.width, h: Math.round(r.height * 100) / 100,
    room: Math.round(f.getBoundingClientRect().height * 100) / 100, gap: Math.round((r.top - h.bottom) * 100) / 100,
    ink: c.color, size: parseFloat(c.fontSize), weight: c.fontWeight, seen: getComputedStyle(f.querySelector('.cm-fold-in')).visibility,
    lands: (() => { const e = document.elementFromPoint(r.left + 10, r.top + r.height / 2); return !!e && (e === b || b.contains(e)); })() }; }"""


def open_box(pg, by=".cm-say"):
    """The box, opened as a person opens it (the icon, or `by`), once it is at rest."""
    pg.click(by, timeout=8000)
    pg.wait_for_function(BOX_STILL, timeout=8000)
    pg.wait_for_timeout(100)


def box_room(pg):
    """The room the open box takes, as the mock drew it: 136px, with Draw, Flip and
    Post on one line. In a font too wide for that line (GitHub's DejaVu Sans), Post
    keeps to the right on the next: one line more, its 44px and the 6px between.
    Read off the open box, so no row holds this box's font as everybody's."""
    two = pg.evaluate("""() => { const b = document.querySelector('[data-cm-box]');
      const p = b && b.querySelector('[data-cm-post]'), c = b && b.querySelector('.composer-acts .chip');
      return !!(p && c) && Math.abs(p.getBoundingClientRect().top - c.getBoundingClientRect().top) >= 1; }""")
    return 136 + (50 if two else 0)


def answer_box(pg, cid):
    """Answer on comment `cid`: the box open for it, at rest."""
    pg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", cid)
    pg.wait_for_timeout(150)
    pg.click(f"#c-{cid} > .cm-main [data-cm-answer]", timeout=8000)
    pg.wait_for_function(BOX_STILL, timeout=8000)
    pg.wait_for_timeout(100)


# KIND, NEVER JUMPY, READ ON EVERY FRAME: run `act` (a function's body), then
# read where `sels` are on the screen (each one's top, null while it is not
# painted) and the opacity of `fades`, on every animation frame for `ms`.
FRAMES = """async ([act, sels, fades, ms]) => {
  const q = s => document.querySelector(s);
  const top = s => { const e = q(s); return e && e.getClientRects().length ? Math.round(e.getBoundingClientRect().top * 100) / 100 : null; };
  const op = s => { const e = q(s); return e && e.getClientRects().length ? Math.round(+getComputedStyle(e).opacity * 100) / 100 : null; };
  const read = () => ({ tops: sels.map(top), ops: fades.map(op), y: Math.round(scrollY * 100) / 100 });
  const frames = [read()];
  (new Function(act))();
  frames.push(read());
  const t0 = performance.now();
  await new Promise(res => { const step = () => { frames.push(read());
    if (performance.now() - t0 < ms) requestAnimationFrame(step); else res(); }; requestAnimationFrame(step); });
  return frames; }"""


def track(frames, k):
    return [f["tops"][k] for f in frames if f["tops"][k] is not None]


def fades_of(frames, k):
    return [f["ops"][k] for f in frames if f["ops"][k] is not None]


def glided(xs, want=None):
    """A glide: three frames or more carry the move, none more than three
    quarters of it (a snap, or a late jump, carries all of it in one), nothing
    goes back against it, and, given `want`, it went that far. The rule the
    comments' own checks have used since they were built."""
    xs = [x for x in xs if x is not None]
    steps = [y - x for x, y in zip(xs, xs[1:])]
    way = xs[-1] - xs[0] if xs else 0
    moving = [s for s in steps if abs(s) > 0.3]
    back = [round(s, 2) for s in steps if way and s * way < -0.5]
    big = max((abs(s) for s in steps), default=0)
    ok = abs(way) > 0.5 and len(moving) >= 3 and big <= 0.75 * abs(way) and not back
    if want is not None:
        ok = ok and abs(abs(way) - want) <= 1.5
    return {"ok": ok, "way": round(way, 2), "frames": len(moving), "step": round(big, 2), "back": back}


def still_(xs):
    xs = [x for x in xs if x is not None]
    return bool(xs) and max(xs) - min(xs) <= 0.5


def moved_by(xs):
    """The frames something moved on, and by how much each time."""
    xs = [x for x in xs if x is not None]
    return [round(y - x, 2) for x, y in zip(xs, xs[1:]) if abs(y - x) > 0.3]


def one_step(xs):
    """Put in place: it moved on one frame at most (Reduce Motion), never a glide."""
    return len(moved_by(xs)) <= 1


def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def icon_mark(pg):
    """The icon's line against its own ground, read off the painted pixels
    (not the stylesheet: the comment mock found a reader that misread a colour
    form): the most contrasting pixel inside the icon's drawing, and the
    button's ground 5px in from its left edge at its middle."""
    import io
    from PIL import Image
    r = pg.evaluate("""() => { const b = document.querySelector('.cm-say'); const s = b.querySelector('svg').getBoundingClientRect(),
      o = b.getBoundingClientRect(); return { sx: s.left, sy: s.top, sw: s.width, sh: s.height, ox: o.left, oy: o.top, oh: o.height,
      dpr: devicePixelRatio }; }""")
    shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    k = r["dpr"]
    ground = shot.getpixel((int((r["ox"] + 5) * k), int((r["oy"] + r["oh"] / 2) * k)))
    best, ink = 0.0, None
    for x in range(int(r["sx"] * k), int((r["sx"] + r["sw"]) * k)):
        for y in range(int(r["sy"] * k), int((r["sy"] + r["sh"]) * k)):
            px = shot.getpixel((x, y))
            c = contrast(px, ground)
            if c > best:
                best, ink = c, px
    return {"ink": ink, "ground": ground, "k": round(best, 2)}


# A swipe down on the box's sheet, as a finger makes one (verify_social's, for this sheet).
SWIPE = """([dys, every]) => new Promise(res => { const s = document.querySelector('#commentBoxSheet .make-sheet'), r = s.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + 12;
  const fire = (type, yy) => { const t = new Touch({ identifier: 9, target: s, clientX: x, clientY: yy });
    const end = type === 'touchend';
    s.dispatchEvent(new TouchEvent(type, { touches: end ? [] : [t], targetTouches: end ? [] : [t], changedTouches: [t],
                                           bubbles: true, cancelable: true, view: window })); };
  fire('touchstart', y);
  let i = 0;
  (function step() { if (i < dys.length) { fire('touchmove', y + dys[i++]); setTimeout(step, every); }
                     else { fire('touchend', y + dys[dys.length - 1]); setTimeout(res, 700); } })(); })"""

# A PHONE'S KEYBOARD, STOOD IN: this box has none, so the visual viewport is
# stood in for (before the page's own scripts run), and a keyboard of `px`
# reported the way iPhone's Safari reports one: the visual viewport shorter,
# the layout viewport the sheet is fixed to unchanged. Not a phone.
KEYBOARD = """(() => { const t = new EventTarget(); let h = null, off = 0, scale = 1;
  const vv = { get width() { return innerWidth; }, get height() { return h === null ? innerHeight : h; },
    get offsetTop() { return off; }, get offsetLeft() { return 0; }, get scale() { return scale; },
    addEventListener: (...a) => t.addEventListener(...a), removeEventListener: (...a) => t.removeEventListener(...a) };
  Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => vv });
  window.__keyboard = (px, zoom) => { scale = zoom || 1; h = innerHeight - px; off = 0; t.dispatchEvent(new Event('resize')); }; })();"""

# Press Post in the open box and read on every frame, until `ms`: the old first
# comment's name (painted), the new comment's top, opacity and glow (the landing's
# tint on it, and that tint's own fade), a phone's sheet, and the box's height
# while it is seen (it must not change on its way out: emptied once gone); what
# Post says meanwhile, and whether a line was shown in the box.
POSTED = """async ([ms]) => {
  const q = s => document.querySelector(s);
  const oldName = q('[data-cm-list] > .cm > .cm-main .cm-name');
  const before = new Set([...document.querySelectorAll('.cm')].map(e => e.id));
  const box = q('[data-cm-box]'), say = box.querySelector('[data-cm-say]'), post = q('[data-cm-post]'), sheet = q('#commentBoxSheet .make-sheet');
  const top = e => e && e.isConnected && e.getClientRects().length ? Math.round(e.getBoundingClientRect().top * 100) / 100 : null;
  const seen = e => { if (!e.getClientRects().length) return false;
    for (let n = e; n; n = n.parentElement) { const c = getComputedStyle(n); if (c.visibility === 'hidden' || c.display === 'none') return false; }
    return true; };
  const out = { old: [], new: [], ops: [], sheet: [], glow: [], tints: [], heights: [], line: false, tint: null };
  const fold = q('[data-cm-fold]'), room = fold ? Math.round(fold.getBoundingClientRect().height * 100) / 100 : 0;
  post.click();
  out.label = post.textContent.trim();
  let li = null; const t0 = performance.now();
  await new Promise(res => { const step = () => {
    li = li || [...document.querySelectorAll('.cm')].find(e => !before.has(e.id));
    if (oldName) out.old.push(top(oldName));
    if (li) { out.new.push(top(li)); out.ops.push(Math.round(+getComputedStyle(li).opacity * 100) / 100);
              out.glow.push(li.classList.contains('is-landed'));
              const b = getComputedStyle(li, '::before');
              if (out.tint === null && li.classList.contains('is-landed')) out.tint = b.backgroundColor;
              out.tints.push(li.classList.contains('is-landed') ? Math.round(+b.opacity * 100) / 100 : 0); }
    if (sheet) { const t = top(sheet); if (t !== null) out.sheet.push(t); }
    if (seen(box)) out.heights.push(Math.round(box.getBoundingClientRect().height * 100) / 100);
    if (!say.hidden && !say.classList.contains('sr')) out.line = true;
    if (performance.now() - t0 < ms) requestAnimationFrame(step); else res(); }; requestAnimationFrame(step); });
  const head = q('.comments-head').getBoundingClientRect(), hs = out.heights;
  return { id: li ? li.id : null, room, old: out.old, new: out.new, ops: out.ops, sheet: out.sheet, glow: out.glow,
           tint: out.tint, fade: out.tints.filter(o => o > 0.03 && o < 0.97).length,
           step: hs.some((h, i) => i && Math.abs(h - hs[i - 1]) > 0.5), label: out.label, line: out.line,
           focus: document.activeElement ? document.activeElement.className : null,
           first: (q('[data-cm-list] > .cm') || {}).id || null, under_head: Math.round((head.bottom + 10) * 100) / 100 }; }"""

# The landing's tint (Activity's): what a posted comment glows in.
TINT = {"light": "rgba(124, 92, 255, 0.12)", "dark": "rgba(124, 92, 255, 0.18)"}

# Press a comment's Answer, and read on every frame where the comment is on the
# screen (against where it was), the box's opacity and a phone's sheet: did
# anything jump? At the end, whether the box is in view (above a phone's bar,
# unless it rides the sheet over it).
ANSWER_AND_WATCH = """async (id) => {
  const li = document.getElementById('c-' + id), box = document.querySelector('[data-cm-box]');
  const sheet = document.querySelector('#commentBoxSheet .make-sheet');
  const btn = li.querySelector(':scope > .cm-main [data-cm-answer]');
  const top0 = li.getBoundingClientRect().top, y0 = scrollY;
  btn.click();
  const now = li.getBoundingClientRect().top - top0;
  const t0 = performance.now(), frames = [];
  await new Promise(res => { const step = () => {
    frames.push({ dy: Math.round((li.getBoundingClientRect().top - top0) * 10) / 10,
                  op: Math.round(+getComputedStyle(box).opacity * 100) / 100,
                  sheet: sheet && sheet.getClientRects().length ? Math.round(sheet.getBoundingClientRect().top * 10) / 10 : null });
    if (performance.now() - t0 < 1500) requestAnimationFrame(step); else res(); };
    requestAnimationFrame(step); });
  const bar = document.querySelector('body > .nav').getBoundingClientRect(), riding = !!sheet && sheet.contains(box);
  const floor = !riding && bar.top > innerHeight / 2 ? bar.top : innerHeight, br = box.getBoundingClientRect();
  return { now: Math.round(now * 10) / 10, frames, scrolled: Math.round(scrollY - y0),
           focus: document.activeElement === box.querySelector('[data-cm-words]'),
           pressed: btn.getAttribute('aria-expanded'), seen: br.top >= 0 && br.bottom <= floor + 0.5 }; }"""


def faded(ops):
    """Frames shown part-way between nothing and whole."""
    return len([o for o in ops if 0.02 < o < 0.98])


def glide(watch):
    """How the page went to the box: the frames it moved on, its largest
    step, and the whole way (a snap goes the whole way in one frame)."""
    dys = [watch["now"]] + [f["dy"] for f in watch["frames"]]
    steps = [abs(b - a) for a, b in zip(dys, dys[1:])]
    return {"frames": len([x for x in steps if x > 0.5]), "step": max(steps or [0]),
            "way": abs(dys[-1] - dys[0])}


def steady(watch):
    """Nothing jumped: the comment did not move as the box did (the move
    itself), and whatever the page did after was stillness or a glide (over
    three frames or more, no one of them carrying three quarters of the way:
    a snap carries all of it in one), ending with the box in view."""
    g = glide(watch)
    return abs(watch["now"]) <= 1 and watch["seen"] and (g["way"] <= 1 or (g["frames"] >= 3 and g["step"] <= 0.75 * g["way"]))


def menu_of(pg, cid):
    """A comment's ⋯ sheet: its title and the rows it shows."""
    pg.click(f"#c-{cid} > .cm-main [data-cm-menu]")
    pg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
    got = {"title": pg.evaluate("() => document.getElementById('commentSheetTitle').textContent"),
           "acts": pg.evaluate(ACTS, "#commentSheet")}
    pg.keyboard.press("Escape")
    pg.wait_for_function("(id) => !document.getElementById(id).classList.contains('is-open')", arg="commentSheet",
                         timeout=10000)
    pg.wait_for_timeout(450)
    return got


class InFrame:
    """artdraw's page, for an editor in an iframe: the pen goes in at the top
    page's own coordinates, the editor's state is the frame's
    (verify_socialposts' own)."""

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
CAT = [S([(354 + 150 * math.cos(a / 10), 300 + 130 * math.sin(a / 10)) for a in range(0, 64)], "gesture",
         artdraw.INK, size=16),
       S([(300, 280), (312, 292)], "detail", artdraw.PURPLE, size=14),
       S([(400, 280), (412, 292)], "detail", artdraw.PURPLE, size=14)]


def add_from_pad(pg, fr):
    """Draw with a pen, end the take, and press Add: what its sheet said."""
    fr.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); setTool('pen');"
                " if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
    artdraw.draw(InFrame(pg, fr), CAT, tempo=2.5, pause_tempo=3)
    pg.wait_for_timeout(400)
    if fr.evaluate("() => typeof recording !== 'undefined' && !!recording"):
        fr.click("#recordBtn")
        pg.wait_for_timeout(400)
    fr.click("#postBtn")
    pg.wait_for_timeout(700)
    # What the sheet SHOWS about the gallery: a hidden field's label is in the page either way.
    sheet = fr.evaluate("""() => ({ label: (document.getElementById('postSubmitLabel') || {}).textContent,
      tick: [...document.querySelectorAll('#postSheet label')].filter(l => l.getClientRects().length)
              .map(l => l.textContent.trim()).filter(t => /gallery/i.test(t)) })""")
    fr.click("#postSubmitBtn")
    pg.wait_for_timeout(1400)
    return sheet


DRAFT = """() => { const d = document.querySelector('[data-cm-draft]'); const box = d && d.querySelector('.skribl-inline');
  return { shown: !!d && !d.hidden, attached: !!(box && box._skriblInline),
           chips: [...document.querySelectorAll('[data-cm-open]')].map(c => c.hidden),
           overlay: document.getElementById('commentPad').hidden,
           focus: document.activeElement ? document.activeElement.textContent.trim() : null }; }"""
ART = """(id) => { const li = document.getElementById('c-' + id);
  const a = li && li.querySelector(':scope > .cm-main .cm-art [data-skribl-inline]');
  return a ? a.getAttribute('data-skribl-id') : null; }"""
STATES = """() => (window.SkriblInline ? SkriblInline.players() : []).map(p => { const s = p.state();
  return [s.id, { state: s.state, loaded: s.loaded, ms: Math.round(s.elapsedMs || 0) }]; })"""


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
    // FAINT BY OPACITY TOO: a word's own colour, and every opacity over it up the page (the census read the
    // colour alone, and a word faded with opacity read as full).
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

# A copy of the database, and the site's two deletions run on it with the
# database's own cascade OFF (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented
# opt-out): what is gone then is gone because the code said so.
PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Comment, Person, Post
    from social.posts import drop_post
    from social.accounts import delete_person
    from social.comments import drop_comments
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    post_pub, handle, one = sys.argv[1], sys.argv[2], sys.argv[3]
    top = db.session.execute(sa.select(Comment).where(Comment.public_id == one)).scalar_one()
    drop_comments([top.id])
    db.session.flush()
    left_answers = db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.parent_id == top.id)).scalar()
    post = db.session.execute(sa.select(Post).where(Post.public_id == post_pub)).scalar_one()
    author = db.session.get(Person, post.person_id)
    drop_post(author.public_id, post)
    db.session.flush()
    left_post = db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.post_id == post.id)).scalar()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == handle)).scalar_one()
    mine = [r[0] for r in db.session.execute(sa.select(Comment.id).where(Comment.person_id == who.id, Comment.parent_id.is_(None)))]
    delete_person(db.session, who.id)
    db.session.commit()
    left_person = db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.person_id == who.id)).scalar()
    left_under = db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.parent_id.in_(mine or [-1]))).scalar()
    print(json.dumps({"fk": fk, "answers": left_answers, "post": left_post, "person": left_person, "under": left_under}))
"""

# The same for a drawing's comments (section 25): delete_person for the
# drawing's owner, on a copy, the cascade off. With it on, owner_id's ON DELETE
# CASCADE would take them whether or not the code said so.
PROBE_DRAWING = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Comment, Person
    from social.accounts import delete_person
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    handle, sid = sys.argv[1], sys.argv[2]
    who = db.session.execute(sa.select(Person).where(Person.handle_key == handle)).scalar_one()
    on = lambda: db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.drawing_id == sid)).scalar()
    before = on()
    delete_person(db.session, who.id)
    db.session.commit()
    owned = db.session.execute(sa.select(sa.func.count()).select_from(Comment).where(Comment.owner_id == who.id)).scalar()
    print(json.dumps({"fk": fk, "before": before, "left": on(), "owned": owned}))
"""


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the section: Comments and how many, the box behind the icon, signed out readable"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 1, a snail", seed=11)
            pg = theo.pg
            sent = []
            pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and "/comments" in r.url else None)
            open_post(pg, post)
            empty = pg.evaluate(SECTION)
            folded = pg.evaluate(BOX)
            icon = pg.evaluate(ICON)
            soon = pg.evaluate("() => !!document.querySelector('.comments-soon')")
            title = pg.evaluate("() => document.getElementById('commentsTitle').innerText.replace(/\\s+/g, ' ').trim()")
            box, err = steps(lambda: (open_box(pg), pg.evaluate(BOX))[1])
            nothing = blank = None
            def nothing_sent():         # a box that cannot be used is this row's red, never a stop
                pg.click("[data-cm-post]", timeout=8000)
                pg.wait_for_timeout(300)
                said_ = pg.evaluate("() => document.querySelector('[data-cm-say]').textContent")
                pg.fill("[data-cm-words]", "   \n  ", timeout=8000)
                pg.click("[data-cm-post]", timeout=8000)
                pg.wait_for_timeout(300)
                again_ = pg.evaluate("() => document.querySelector('[data-cm-say]').textContent")
                pg.keyboard.press("Escape")
                pg.wait_for_function(GONE, timeout=8000)
                return said_, again_

            if box:                     # no box is the first row's red, never a stop
                got_, _ = steps(nothing_sent)
                nothing, blank = got_ or (None, None)
            check("a post's page says Comments, with no number at none, and at the heading's end the icon (\"Say something\"),"
                  " the box folded away behind it; a tap opens it on a phone's sheet, \"Say something to Juno\": their face, the"
                  " words' field (17px, focused), \"Say something, or draw it…\", Draw, Flip and Post; no \"Comments open soon\"",
                  empty == {"count": None, "list": []} and title == "Comments" and not soon
                  and icon is not None and icon["name"] == "Say something" and folded is not None and folded["open"] is None
                  and box is not None and box["open"] == "sheet" and box["title"] == "Say something to Juno" and box["face"]
                  and box["focus"] and box["placeholder"] == "Say something, or draw it…" and box["chips"] == ["Draw", "Flip"]
                  and box["post"] == "Post" and box["font"] >= 16,
                  f"section {empty}; title {title!r}; open soon {soon}; icon {icon and icon['name']}; folded"
                  f" {folded and folded['open']}; opened {box}; stopped {err}")
            check("Post with nothing written or drawn (or only spaces) says so and sends nothing",
                  nothing == "Say something or draw something first, then Post." and blank == nothing and not sent,
                  f"said {nothing!r} / {blank!r}; sent {len(sent)}")
            said(theo, post, "Read by somebody signed out")
            nctx, npg = browser_as(b, None)
            open_post(npg, post)
            out = {"section": npg.evaluate(SECTION), "box": npg.evaluate(BOX), "icon": npg.evaluate(ICON)}
            sheet, err2 = steps(lambda: (npg.click(".cm-say", timeout=8000),
                                         npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000),
                                         npg.wait_for_timeout(450), npg.evaluate(OUT_SHEET))[-1])
            close_ctx(nctx, npg)
            check("signed out, the comments are readable, with no box and no Answer; the icon is there all the same, and a tap"
                  " raises \"Say something?\", its Sign in back to the post with the box open; no \"Sign in to answer\"",
                  out["box"] is None and out["section"]["count"] == "1"
                  and [(c["name"], c["words"], c["answer"]) for c in out["section"]["list"]]
                  == [("Theo Lind", "Read by somebody signed out", False)]
                  and out["icon"] is not None and sheet and sheet["open"] and sheet["title"] == "Say something?"
                  and sheet["next"] == f"/social/p/{post}#say" and not sheet["old"],
                  f"{out['section']}; box {out['box']}; icon {out['icon'] and out['icon']['name']}; sheet {sheet}; stopped {err2}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "commenting: the box sends the words; newest first, the count with it"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 2, a snail for a slow Sunday", seed=21)
            pg = theo.pg
            open_post(pg, post)
            open_box(pg)
            pg.fill("[data-cm-words]", "  That shell spiral   is so good.\n\n\n\nWatching it go round is the best part.  ")
            theo_said = pg.evaluate(POST_AND_WATCH)
            pg.wait_for_function(GONE, timeout=8000)
            pg.wait_for_timeout(300)
            after1 = pg.evaluate(SECTION)
            cleared = pg.evaluate("() => document.querySelector('[data-cm-words]').value")
            row = db("select c.words, c.parent_id, pe.handle, c.post_id from social_comments c join social_people pe"
                     " on pe.id = c.person_id where c.public_id = ?", (theo_said["id"] or "",))
            check("the box sends the words, tidied as a post's (spaces run together, blank lines to one); the comment"
                  " fades in at the top, said \"now\", the count 1, the box gone and emptied; its row names the post and the person",
                  theo_said["id"] and faded(theo_said["ops"]) >= 2 and theo_said["ops"][-1] == 1
                  and row == [("That shell spiral is so good.\n\nWatching it go round is the best part.", None, "theo",
                               post_id(post))]
                  and after1["count"] == "1" and [c["when"] for c in after1["list"]] == ["now"] and cleared == "",
                  f"{theo_said}; row {row}; section {after1}; box {cleared!r}")
            mira_id = said(mira, post, "My cat would never be this patient")
            db_write("update social_comments set created_at = datetime('now', '-40 minutes') where public_id = ?", (mira_id,))
            db_write("update social_comments set created_at = datetime('now', '-2 hours') where public_id = ?",
                     (theo_said["id"] or "",))
            open_post(pg, post)
            open_box(pg)
            pg.fill("[data-cm-words]", "And the colour!")
            third = pg.evaluate(POST_AND_WATCH)
            listed = pg.evaluate(SECTION)
            open_post(pg, post)
            again = pg.evaluate(SECTION)
            check("newest first, on the page and after a reload, each said short (\"now\", \"40m\", \"2h\"), the count"
                  " with them",
                  [(c["name"], c["when"]) for c in listed["list"]] == [("Theo Lind", "now"), ("Mira Okafor", "40m"),
                                                                         ("Theo Lind", "2h")]
                  and listed["count"] == "3" and [c["id"] for c in again["list"]] == [c["id"] for c in listed["list"]]
                  and again["count"] == "3" and third["id"] == listed["list"][0]["id"],
                  f"{[(c['name'], c['when'], c['words'][:20]) for c in listed['list']]}; count {listed['count']};"
                  f" after a reload {[c['id'] for c in again['list']]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "answers, one level deep: Answer opens the box for the comment, nothing jumps"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 3, a snail", seed=31)
            theo_c = said(theo, post, "That shell spiral is so good. Watching it go round is the best part.")
            juno_a = said(juno, post, "Thank you! It took me two tries to get the spiral right.", answer_to=theo_c)
            for k in range(3):
                said(juno, post, f"Section 3, filler {k}: so the page scrolls")
            pg = mira.pg
            open_post(pg, post)
            pg.evaluate("(id) => { const r = document.getElementById('c-' + id).getBoundingClientRect();"
                        " window.scrollBy(0, r.top - innerHeight / 2); }", theo_c)
            pg.wait_for_timeout(300)
            went = pg.evaluate(ANSWER_AND_WATCH, theo_c)
            there = pg.evaluate(BOX)
            rise = glided([f["sheet"] for f in went["frames"]])
            check("Answer on a phone raises the box on Make's sheet for that comment: \"Answer Theo\", the field saying"
                  " \"Answer Theo…\" (its label too) and focused, Answer pressed; the comment stays where it is on the screen"
                  " and the sheet glides up (read on every frame)",
                  there["open"] == "sheet" and there["title"] == "Answer Theo" and there["placeholder"] == "Answer Theo…"
                  and there["label"] == "Answer Theo" and went["focus"] and went["pressed"] == "true" and steady(went)
                  and all(abs(f["dy"]) <= 0.5 for f in went["frames"]) and rise["ok"],
                  f"box {there}; the comment {went['now']}px then {glide(went)}; the sheet {rise}; focus {went['focus']}")
            pg.fill("[data-cm-words]", "Same! I watched it three times.")
            mine = pg.evaluate(POST_AND_WATCH)
            pg.wait_for_function(GONE, timeout=8000)
            pg.wait_for_timeout(300)
            sec = pg.evaluate(SECTION)
            theo_li = next((c for c in sec["list"] if c["id"] == theo_c), {"answers": []})
            open_box(pg)
            back = pg.evaluate(BOX)
            pg.keyboard.press("Escape")
            pg.wait_for_function(GONE, timeout=8000)
            # ...and as the server renders them, which the page's own insertion cannot show.
            open_post(pg, post)
            again = next((c for c in pg.evaluate(SECTION)["list"] if c["id"] == theo_c), {"answers": []})
            want = ["Thank you! It took me two tries to get the spiral right.", "Same! I watched it three times."]
            check("the answer sits under the comment, after the ones before it (oldest first, put in place and after a"
                  " reload), fading in; the box goes, and the icon opens it as \"Say something, or draw it…\" again",
                  [a["words"] for a in theo_li["answers"]] == want and [a["words"] for a in again["answers"]] == want
                  and faded(mine["ops"]) >= 2 and back["open"] == "sheet" and back["placeholder"] == "Say something, or draw it…"
                  and back["label"] == "Say something" and back["title"] == "Say something to Juno",
                  f"answers {[a['words'][:24] for a in theo_li['answers']]}; after a reload"
                  f" {[a['words'][:24] for a in again['answers']]}; faded {faded(mine['ops'])}; box {back}")
            jpg = juno.pg
            open_post(jpg, post)
            jpg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", mine["id"])
            jpg.wait_for_timeout(200)
            jwent = jpg.evaluate(ANSWER_AND_WATCH, mine["id"])
            jbox = jpg.evaluate(BOX)
            jpg.fill("[data-cm-words]", "Three times! Thank you, Mira.")
            jpg.evaluate(POST_AND_WATCH)
            rows = db("select c.public_id, p.public_id from social_comments c left join social_comments p on p.id = c.parent_id"
                      " where c.words like 'Three times!%'")
            jsec = jpg.evaluate(SECTION)
            under = [a["words"] for a in next((c for c in jsec["list"] if c["id"] == theo_c), {"answers": []})["answers"]]
            check("answering an answer: the box answers Mira (\"Answer Mira…\"), and the new answer sits under the same"
                  " comment, last, its row's parent the comment, not the answer",
                  jbox["title"] == "Answer Mira" and jbox["placeholder"] == "Answer Mira…" and steady(jwent)
                  and len(rows) == 1 and rows[0][1] == theo_c and under[-1] == "Three times! Thank you, Mira."
                  and len(under) == 3,
                  f"box {jbox}; rows {rows}; under Theo's {[u[:20] for u in under]}; the move {jwent['now']}px,"
                  f" then {glide(jwent)}")
            # A desk: Answer opens it under the conversation; Answer again, or Esc, folds it away.
            dctx, dpg = browser_as(b, mira, "desk")
            open_post(dpg, post)

            def toggles():             # a box that never goes is this row's red, never a stop
                answer_box(dpg, juno_a)
                t_in = dpg.evaluate(BOX)
                dpg.click(f"#c-{juno_a} > .cm-main [data-cm-answer]")
                dpg.wait_for_function(GONE, timeout=8000)
                t_out = dpg.evaluate(BOX)
                answer_box(dpg, juno_a)
                dpg.keyboard.press("Escape")
                dpg.wait_for_function(GONE, timeout=8000)
                return t_in, t_out, dpg.evaluate(BOX)

            got_, err = steps(toggles)
            toggled_in, toggled_out, escaped = got_ if err is None else ({}, {}, {})
            check("on a desk, Answer opens the box under the conversation (\"Answer Juno…\"); Answer again folds it away, and so"
                  " does Esc, home under the heading",
                  err is None and toggled_in["open"] == "under" and toggled_in["under"] == theo_c
                  and toggled_in["placeholder"] == "Answer Juno…"
                  and toggled_out["open"] is None and toggled_out["home"] and escaped["open"] is None and escaped["home"],
                  f"in {toggled_in}; again {toggled_out}; Esc {escaped}; stopped {err}")
            long_c = said(theo, post, "Section 3, a long thread")
            for k in range(7):
                said(juno if k % 2 else mira, post, f"Section 3, answer {k} in a long thread, long enough to take two lines",
                     answer_to=long_c)
            open_post(dpg, post)
            dpg.evaluate("(id) => { const r = document.getElementById('c-' + id).getBoundingClientRect();"
                         " window.scrollBy(0, r.top - innerHeight / 3); }", long_c)
            dpg.wait_for_timeout(300)
            far = dpg.evaluate(ANSWER_AND_WATCH, long_c)
            g = glide(far)
            close_ctx(dctx, dpg)
            check("under a long thread, where the box opens below what the screen shows, the page glides down to it (over"
                  " several frames, none carrying three quarters of the way) and leaves it in view; the comment does not jump"
                  " as the box opens",
                  steady(far) and g["way"] > 60,
                  f"the move {far['now']}px; then {g}; in view {far['seen']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "a comment's ⋯: yours, somebody else's on your own post, anybody else's, signed out"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 4, a snail", seed=41)
            theo_c = said(theo, post, "Section 4, Theo's")
            mira_c = said(mira, post, "Section 4, Mira's")
            juno_c = said(juno, post, "Section 4, Juno's own")
            open_post(juno.pg, post)
            on_mine = {"own": menu_of(juno.pg, juno_c), "theo's": menu_of(juno.pg, theo_c)}
            open_post(mira.pg, post)
            elsewhere = {"own": menu_of(mira.pg, mira_c), "theo's": menu_of(mira.pg, theo_c)}
            nctx, npg = browser_as(b, None)
            open_post(npg, post)
            nobody = menu_of(npg, theo_c)
            close_ctx(nctx, npg)
            check("on your own post: your own comment's ⋯ is \"Your comment\": Delete comment; somebody else's is"
                  " \"Theo’s comment\": Remove from my post, Report comment",
                  on_mine == {"own": {"title": "Your comment", "acts": ["Delete comment"]},
                              "theo's": {"title": "Theo’s comment", "acts": ["Remove from my post", "Report comment"]}},
                  f"{on_mine}")
            check("on somebody else's post: your own is \"Your comment\": Delete comment; anybody else's \"Theo’s comment\":"
                  " Report comment alone; signed out, Report comment",
                  elsewhere == {"own": {"title": "Your comment", "acts": ["Delete comment"]},
                                "theo's": {"title": "Theo’s comment", "acts": ["Report comment"]}}
                  and nobody == {"title": "Theo’s comment", "acts": ["Report comment"]},
                  f"{elsewhere}; signed out {nobody}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "delete and remove: a comment goes with its answers, fading out; nobody else can"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 5, a snail", seed=51)
            theo_c = said(theo, post, "Section 5, Theo's, to be deleted")
            under_theo = [said(mira, post, "Section 5, Mira under Theo", answer_to=theo_c),
                          said(juno, post, "Section 5, Juno under Theo", answer_to=theo_c)]
            mira_c = said(mira, post, "Section 5, Mira's, to be removed")
            under_mira = said(theo, post, "Section 5, Theo under Mira", answer_to=mira_c)
            keep_c = said(mira, post, "Section 5, Mira's, kept")
            lone = said(theo, post, "Section 5, an answer alone", answer_to=keep_c)
            tpg = theo.pg
            open_post(tpg, post)
            t_del = tpg.evaluate(DELETE_AND_WATCH, [theo_c, "delete"])
            gone_rows = db("select public_id from social_comments where public_id in (?, ?, ?)", (theo_c, *under_theo))
            check("Delete comment takes your own comment and every answer under it (anybody's): it fades out and is gone,"
                  " the count with it, its rows and its answers' gone",
                  t_del["gone"] and faded(t_del["ops"]) >= 2 and t_del["count"] == "4" and gone_rows == [],
                  f"{t_del}; rows left {gone_rows}")
            jpg = juno.pg
            open_post(jpg, post)
            j_rm = jpg.evaluate(DELETE_AND_WATCH, [mira_c, "remove"])
            rm_rows = db("select public_id from social_comments where public_id in (?, ?)", (mira_c, under_mira))
            check("on your own post, Remove from my post takes somebody else's comment, its answers with it, the same way",
                  j_rm["gone"] and faded(j_rm["ops"]) >= 2 and j_rm["count"] == "2" and rm_rows == [],
                  f"{j_rm}; rows left {rm_rows}")
            tc = theo.client()
            tc.get(f"/social/p/{post}")
            other = tc.post_json(f"/social/c/{keep_c}/delete", {})
            alone = tc.post_json(f"/social/c/{lone}/delete", {})
            left = db("select public_id from social_comments where public_id in (?, ?)", (keep_c, lone))
            check("nobody else can (somebody else's comment on somebody else's post is gone to them, 404); an answer"
                  " deleted goes alone, the comment it was under stays",
                  other[0] == 404 and alone[0] == 200 and left == [(keep_c,)], f"other {other}; alone {alone}; left {left}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "who may comment: the token, signed in, not taken down, no block; the words; the limit"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            kai = someone(b, "kai", "Kai Ferro")
            lou = someone(b, "lou", "Lou Amari")
            post = make_post(juno, "Section 6, a snail", seed=61)
            theo_c = said(theo, post, "Section 6, Theo's")
            c = theo.client()
            c.get(f"/social/p/{post}")
            nc = Client()
            nc.get(f"/social/p/{post}")
            path = f"/social/p/{post}/comments"
            ans = {
                "no token": c.post_json(path, {"words": "hi"}, token=False)[0],
                "another site": Client(cookies=theo.ctx.cookies(BASE), xff=theo.xff, origin="https://elsewhere.example")
                .post_json(path, {"words": "hi"}, token=c.token)[0],
                "signed out": nc.post_json(path, {"words": "hi"})[0],
                "too long": c.post_json(path, {"words": "x" * 501})[1],
                "a hidden character": c.post_json(path, {"words": "hello‮world"})[1],
                "no words": c.post_json(path, {"words": " \n "})[1],
                "not words": c.post_json(path, {"words": ["hi"]})[1],
                "a post not there": c.post_json("/social/p/nothinghere/comments", {"words": "hi"})[0],
                "an answer to nothing": c.post_json(path, {"words": "hi", "answer_to": "nothinghere"})[0],
            }
            n = db("select count(*) from social_comments where post_id = ?", (post_id(post),))[0][0]
            check("a comment is refused kindly without the page's token or from another site (403), signed out (401),"
                  " with too many words, a hidden character, no words or not words (400, each its own), on a post or"
                  " under a comment not there (404); nothing is written",
                  ans == {"no token": 403, "another site": 403, "signed out": 401, "too long": {"error": "words_long"},
                          "a hidden character": {"error": "words_chars"}, "no words": {"error": "empty"},
                          "not words": {"error": "empty"}, "a post not there": 404, "an answer to nothing": 404}
                  and n == 1, f"{ans}; rows {n}")
            kc = kai.client()
            kc.get("/social/")
            kc.post_json("/social/@juno/block", {})          # Kai blocks the post's author
            lc = lou.client()
            lc.get(f"/social/p/{post}")
            tc2 = theo.client()
            tc2.get("/social/")
            tc2.post_json("/social/@lou/block", {})          # Theo blocks Lou: Lou may not answer Theo
            juc = juno.client()
            juc.get("/social/")
            blocked = {"kai, who blocked the author": kc.post_json(path, {"words": "hi"}),
                       "lou, answering theo who blocked lou": lc.post_json(path, {"words": "hi", "answer_to": theo_c})}
            lou_top = lc.post_json(path, {"words": "Section 6, Lou's, on the post itself"})
            juc.post_json("/social/@kai/unblock", {})
            kc.post_json("/social/@juno/unblock", {})
            jc = juno.client()
            jc.get("/social/")
            jc.post_json("/social/@lou/block", {})           # the author blocks Lou: Lou may say nothing there
            lc2 = lou.client()
            lc2.get("/social/")
            by_author = lc2.post_json(path, {"words": "hi"})
            lou_page = status(lou.pg, f"/social/p/{post}")
            check("no block either way with the post's author (gone to them, 404, as its page is), nor, answering, with the"
                  " comment's author (404); with neither, a comment on the post itself is taken",
                  blocked["kai, who blocked the author"] == (404, {"error": "gone"})
                  and blocked["lou, answering theo who blocked lou"] == (404, {"error": "gone"})
                  and lou_top[0] == 200 and by_author == (404, {"error": "gone"}) and lou_page == 404,
                  f"{blocked}; lou on the post {lou_top[0]}; after the author blocks lou {by_author}, its page {lou_page}")
            zed = someone(b, "zed", "Zed Okoro")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'zed'")
            zc = zed.client()
            zc.get(f"/social/p/{post}")
            down = zc.post_json(path, {"words": "hi"})
            zpg = zed.pg
            open_post(zpg, post)
            zbox = zpg.evaluate(BOX)
            zword = zpg.evaluate("() => (document.querySelector('[data-word=c_taken_down]') || {}).textContent")
            check("somebody taken down shares nothing new: refused kindly, in its own words, and no box is shown to them",
                  down == (403, {"error": "taken_down"}) and zbox is None
                  and zword == "Your account was taken down, so nothing new can be shared from it.",
                  f"{down}; box {zbox}; words {zword!r}")
            ivy = someone(b, "ivy", "Ivy Novak")
            ic = ivy.client()
            ic.get(f"/social/p/{post}")
            got = [ic.post_json(path, {"words": f"Section 6, flood {k}"})[0] for k in range(61)]
            check("comments are limited per person (60 an hour): the 61st is refused kindly (429), the 60 before it taken",
                  got[:60] == [200] * 60 and got[60] == 429, f"{got.count(200)} taken, then {got[60:]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "hidden: a block either way, or a person taken down, neither shown nor counted"):
        try:
            ada = someone(b, "ada", "Ada Quist")
            ben = someone(b, "ben", "Ben Reyes")
            cyd = someone(b, "cyd", "Cyd Mbeki")
            dee = someone(b, "dee", "Dee Varga")
            post = make_post(ada, "Section 7, a post", seed=71)
            ben_c = said(ben, post, "Section 7, Ben's")
            cyd_c = said(cyd, post, "Section 7, Cyd's")
            ben_under_cyd = said(ben, post, "Section 7, Ben under Cyd", answer_to=cyd_c)
            cyd_under_ben = said(cyd, post, "Section 7, Cyd under Ben", answer_to=ben_c)

            def seen_by(who):
                open_post(who.pg, post)
                sec = who.pg.evaluate(SECTION)
                who.pg.goto(BASE + "/social/")
                who.pg.wait_for_timeout(500)
                card = who.pg.evaluate("(id) => { const c = document.querySelector('.post-card[data-post=\"' + id + '\"] .post-count');"
                                       " return c ? c.getAttribute('aria-label') : null; }", post)
                return {"count": sec["count"], "card": card,
                        "shown": sorted([c["words"] for c in sec["list"]] + [a["words"] for c in sec["list"] for a in c["answers"]])}

            before = seen_by(dee)
            dc = dee.client()
            dc.get("/social/")
            dc.post_json("/social/@cyd/block", {})
            dee_blocked = seen_by(dee)
            cyd_sees = seen_by(cyd)
            dc.post_json("/social/@cyd/unblock", {})
            cc = cyd.client()
            cc.get("/social/")
            cc.post_json("/social/@dee/block", {})
            dee_by_cyd = seen_by(dee)
            cc.post_json("/social/@dee/unblock", {})
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'cyd'")
            ben_after = seen_by(ben)
            cyd_own = seen_by(cyd)
            db_write("update social_people set taken_down_at = null where handle_key = 'cyd'")
            all4 = sorted(["Section 7, Ben's", "Section 7, Cyd's", "Section 7, Ben under Cyd", "Section 7, Cyd under Ben"])
            without_cyd = ["Section 7, Ben's"]
            check("a block, either way, hides the other's comments and every answer under them: neither shown nor counted,"
                  " on the post's page and on Home's card (the one who blocked, and the one blocked, alike)",
                  before == {"count": "4", "card": "4 comments", "shown": all4}
                  and dee_blocked == {"count": "1", "card": "1 comment", "shown": without_cyd}
                  and dee_by_cyd == dee_blocked and cyd_sees["count"] == "4",
                  f"before {before}; dee blocked cyd {dee_blocked}; cyd blocked dee {dee_by_cyd}; cyd {cyd_sees['count']}")
            check("a person taken down: their comments, and the answers under them, neither shown nor counted for anybody"
                  " else; they still see their own",
                  ben_after == {"count": "1", "card": "1 comment", "shown": without_cyd} and cyd_own["count"] == "4",
                  f"ben {ben_after}; cyd {cyd_own}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "reported, and taken down: Report comment, Your Reports' card, the note"):
        try:
            juno = admin(b)
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            kim = someone(b, "kim", "Kim Ito")
            db_write("update social_reports set state = 'kept' where state = 'open'")
            db_write("update skribl_reports set state = 'closed' where state = 'open'")
            post = make_post(mira, "Section 8, Mira's post", seed=81)
            theo_c = said(theo, post, "Section 8, a mean thing\nand a second line")
            kept_c = said(theo, post, "Section 8, kept")
            pg = kim.pg
            open_post(pg, post)
            pg.click(f"#c-{theo_c} > .cm-main [data-cm-menu]")
            pg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
            pg.click("#commentSheet [data-cm-act=report]")
            pg.wait_for_function(OPEN, arg="commentReportSheet", timeout=10000)
            title = pg.evaluate("() => document.getElementById('commentReportTitle').textContent")
            reasons = pg.evaluate(REASONS, "#commentReportSheet")
            pg.check("#commentReportSheet input[value=abuse]")
            pg.fill("#commentReportNote", "Not kind")
            pg.click("#commentReportSheet [data-cm-report-send]")
            pg.wait_for_function("() => (document.querySelector('#commentReportSheet [data-cm-report-say]') || {}).textContent.length > 12",
                                 timeout=10000)
            thanks = pg.evaluate("() => document.querySelector('#commentReportSheet [data-cm-report-say]').textContent")
            tid, _ = pid_of("theo")
            kid, _ = pid_of("kim")
            rows = db("select kind, target, about_id, reason, note, reporter_id, state from social_reports where target = ?", (theo_c,))
            kc = kim.client()
            kc.get(f"/social/p/{post}")
            kc.post_json("/social/report", {"kind": "comment", "target": kept_c, "reason": "spam"})
            tc = theo.client()
            tc.get(f"/social/p/{post}")
            own = tc.post_json("/social/report", {"kind": "comment", "target": theo_c, "reason": "spam"})[0]
            check("Report comment rises as \"Report this comment\" with a post's reasons, in order, into the site's own queue"
                  " (kind comment, the comment, whose it is, the reason, the note, who sent it), and says thanks; your own"
                  " is not yours to report (404)",
                  title == "Report this comment" and reasons == POST_REASONS and thanks == THANKS
                  and rows == [("comment", theo_c, tid, "abuse", "Not kind", kid, "open")] and own == 404,
                  f"title {title!r}; reasons {reasons}; said {thanks!r}; rows {rows}; own {own}")
            apg = juno.pg
            apg.goto(BASE + "/social/reports")
            apg.wait_for_timeout(700)
            card = apg.evaluate("""(t) => { const c = document.querySelector('[data-rep][data-target="' + t + '"]'); if (!c) return null;
              const a = c.querySelector('.rep-open'); return { kind: c.dataset.kind, who: c.querySelector('.rep-who').innerText,
              words: [...c.querySelectorAll('.rep-words')].map(e => e.textContent), face: !!c.querySelector('.rep-face .face-ring'),
              why: [...c.querySelectorAll('.rep-why')].map(e => e.textContent),
              link: a ? new URL(a.href).pathname + new URL(a.href).hash : null }; }""", theo_c)
            check("Your Reports shows a comment's card: whose it is (\"Theo Lind @theo · a comment\"), its face, its words,"
                  " the reason, and a link to it on its post's page",
                  card == {"kind": "comment", "who": "Theo Lind @theo · a comment", "words": ["“Section 8, a mean thing”"],
                           "face": True, "why": ["Abusive or hateful"], "link": f"/social/p/{post}#c-{theo_c}"},
                  f"{card}")
            with apg.expect_navigation(timeout=15000):
                apg.click(f"[data-rep][data-target='{theo_c}'] form[action$=down] button")
            down_note = apg.evaluate("() => (document.querySelector('.note') || {}).textContent")
            with apg.expect_navigation(timeout=15000):
                apg.click(f"[data-rep][data-target='{kept_c}'] form[action$=keep] button")
            states = dict(db("select target, state from social_reports where target in (?, ?)", (theo_c, kept_c)))
            open_post(mira.pg, post)
            others = mira.pg.evaluate(SECTION)
            open_post(theo.pg, post)
            his = theo.pg.evaluate(SECTION)
            kept = db("select taken_down_at is not null from social_comments where public_id = ?", (kept_c,))
            mine = next((c for c in his["list"] if c["id"] == theo_c), {})
            check("Take it down hides the comment from everybody else at once (neither shown nor counted), keeps it, and"
                  " closes its reports; its author sees it with the note; Keep it closes the other and hides nothing",
                  down_note and down_note.startswith("Taken down.") and states == {theo_c: "taken_down", kept_c: "kept"}
                  and [c["id"] for c in others["list"]] == [kept_c] and others["count"] == "1"
                  and mine.get("down") == NOTE and his["count"] == "2" and kept == [(0,)]
                  and db("select count(*) from social_comments where public_id = ?", (theo_c,))[0][0] == 1,
                  f"note {down_note!r}; states {states}; mira sees {[c['id'] for c in others['list']]} ({others['count']});"
                  f" theo's own {mine.get('down')!r} ({his['count']})")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "deleting a post or an account takes its comments, in code"):
        try:
            nia = someone(b, "nia", "Nia Holm")
            oz = someone(b, "ozan", "Oz Brandt")
            pia = someone(b, "pia", "Pia Laine")
            post = make_post(nia, "Section 9, Nia's post", seed=91)
            said(oz, post, "Section 9, Oz on Nia's")
            on_nia = said(pia, post, "Section 9, Pia on Nia's")
            said(oz, post, "Section 9, Oz under Pia", answer_to=on_nia)
            nc = nia.client()
            nc.get(f"/social/p/{post}")
            gone = nc.post_json(f"/social/p/{post}/delete", {})
            left_post = db("select count(*) from social_comments where words like 'Section 9, % on Nia''s' or words = 'Section 9, Oz under Pia'")[0][0]
            other = make_post(oz, "Section 9, Oz's post", seed=92)
            pia_top = said(pia, other, "Section 9, Pia on Oz's")
            oz_under_pia = said(oz, other, "Section 9, Oz under Pia's", answer_to=pia_top)
            pia_under_oz_top = said(pia, other, "Section 9, Pia under Oz's", answer_to=said(oz, other, "Section 9, Oz's own"))
            pia_post = make_post(pia, "Section 9, Pia's post", seed=93)
            oz_on_pia = said(oz, pia_post, "Section 9, Oz on Pia's")
            ppg = pia.pg
            ppg.goto(BASE + "/social/you/delete")
            ppg.wait_for_timeout(400)
            ppg.fill("input[name=confirm]", "pia")
            with ppg.expect_navigation(timeout=15000):
                ppg.click("form button[type=submit].btn-danger, form button[type=submit]")
            pia_id = pid_of("pia")[0]
            left = {"pia's": db("select count(*) from social_comments where words like 'Section 9, Pia%'")[0][0],
                    "under hers": db("select count(*) from social_comments where public_id = ?", (oz_under_pia or "",))[0][0],
                    "on her post": db("select count(*) from social_comments where public_id = ?", (oz_on_pia or "",))[0][0],
                    "oz's own": db("select count(*) from social_comments where words = 'Section 9, Oz''s own'")[0][0]}
            check("through the site: deleting a post takes every comment and answer on it; deleting an account takes the"
                  " person's comments, every answer under them, and every comment on their posts, and leaves anybody"
                  " else's elsewhere",
                  gone[0] == 200 and left_post == 0 and pia_id is None and pia_under_oz_top
                  and left == {"pia's": 0, "under hers": 0, "on her post": 0, "oz's own": 1},
                  f"post delete {gone[0]}, comments left {left_post}; account gone {pia_id is None}; left {left}")
            # IN CODE, NOT BY THE CASCADE: the demo's SQLite enforces the schema's
            # ON DELETE CASCADE (Skribl's pragma hook), so the rows above would go
            # either way. A copy of the database, the two deletions run on it with
            # the cascade off: what goes then, the code took.
            qua = someone(b, "qua", "Qua Imre")
            rho = someone(b, "rho", "Rho Ngata")
            qpost = make_post(qua, "Section 9, Qua's post", seed=94)
            said(rho, qpost, "Section 9, Rho on Qua's")
            said(qua, qpost, "Section 9, Qua under Rho", answer_to=said(rho, qpost, "Section 9, Rho again"))
            rpost = make_post(qua, "Section 9, Qua's second", seed=95)
            rho_top = said(rho, rpost, "Section 9, Rho's, to go with her")
            said(qua, rpost, "Section 9, Qua under Rho's", answer_to=rho_top)
            one = said(qua, rpost, "Section 9, Qua's, deleted with its answers")
            said(rho, rpost, "Section 9, Rho under Qua's", answer_to=one)
            said(qua, rpost, "Section 9, Qua under her own", answer_to=one)
            copy = os.path.join(TMP, "probe.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            probe = subprocess.run([sys.executable, "-c", PROBE, qpost, "rho", one], cwd=ROOT, capture_output=True, text=True,
                                   timeout=180, env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-400:]}
            check("in code, not by the database's cascade: with SQLite's foreign keys off (SKRIBL_SQLITE_FOREIGN_KEYS=0),"
                  " a comment deleted leaves none of its answers, drop_post no comment on the post, and delete_person none"
                  " of the person's, nor any answer under them",
                  out == {"fk": 0, "answers": 0, "post": 0, "person": 0, "under": 0}, f"{out}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "Load more: twenty comments a page, the next in place, none twice"):
        try:
            juno = someone(b, "juno", "Juno Park")
            sam = someone(b, "sam", "Sam Okafor")
            post = make_post(juno, "Section 10, a busy post", seed=101)
            made = [said(sam, post, f"Section 10, comment {k:02d}") for k in range(23)]
            pg = sam.pg
            open_post(pg, post)
            first = [c["id"] for c in pg.evaluate(SECTION)["list"]]
            btn = pg.evaluate("() => { const b = document.querySelector('[data-cm-next]'); return b && !b.hidden ? b.textContent : null; }")
            cur0 = pg.evaluate("() => document.querySelector('[data-cm-next]').getAttribute('data-cm-next')") or ""
            try:
                named = base64.urlsafe_b64decode(cur0 + "=" * (-len(cur0) % 4)).decode().split(".", 1)
            except Exception:  # noqa: BLE001
                named = None
            if btn:                     # no Load more is the row's red, never a stop
                pg.click("[data-cm-next]")
                pg.wait_for_function("() => document.querySelectorAll('[data-cm-list] > .cm').length > 20", timeout=10000)
                pg.wait_for_timeout(300)
            allc = [c["id"] for c in pg.evaluate(SECTION)["list"]]
            gone = pg.evaluate("() => document.querySelector('[data-cm-next]').hidden")
            cursor = pg.evaluate("() => document.querySelector('[data-cm-next]').getAttribute('data-cm-next')")
            check("twenty comments a page, newest first; Load more brings the rest in place, in order, none twice and none"
                  " missed, then goes; its cursor names no internal id",
                  first == list(reversed(made))[:20] and btn == "Load more" and allc == list(reversed(made)) and gone
                  and len(set(allc)) == 23 and cursor == "" and named is not None and named[1] == first[-1]
                  and named[0].isdigit(),
                  f"first page {len(first)}; button {btn!r}; after {len(allc)} ({len(set(allc))} different); hidden {gone};"
                  f" the cursor says {named}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(10, exc)

    # ------------------------------------------------------------------ 11
    if part(11, "Home's card: how many comments, first in its row, a way to them"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 11, counted", seed=111)
            bare = make_post(juno, "Section 11, nothing yet", seed=112)
            one = said(theo, post, "Section 11, one")
            said(theo, post, "Section 11, two", answer_to=one)
            said(juno, post, "Section 11, three")
            pg = theo.pg
            pg.goto(BASE + "/social/")
            pg.wait_for_timeout(600)
            CARD = """(id) => { const c = document.querySelector('.post-card[data-post="' + id + '"]'); if (!c) return null;
              const n = c.querySelector('.post-count'), row = c.querySelector('.post-row'), pl = n && n.nextElementSibling;
              if (!n || !pl) return { none: true };
              const r = n.getBoundingClientRect(), p = pl.getBoundingClientRect();
              return { label: n.getAttribute('aria-label'), text: n.textContent.trim(), icon: !!n.querySelector('svg'),
                       href: new URL(n.href).pathname + new URL(n.href).hash, first: row.firstElementChild === n,
                       next: pl.classList.contains('lk-heart'), beside: Math.round(p.left - r.right),
                       middle: Math.abs((r.top + r.height / 2) - (p.top + p.height / 2)) < 1, w: r.width, h: r.height }; }"""
            got = pg.evaluate(CARD, post)
            none = pg.evaluate(CARD, bare) or {}
            # EVEN AT NONE (the owner's yes, Nov 12: "the 💬 shows even at zero"):
            # the icon alone, named Comment, the same way in, where the number goes.
            check("Home's card says how many comments first in the row under the drawing (the comment icon and the"
                  " number, \"3 comments\"), 14px before the heart and on its middle, a way to them on the post's page,"
                  " 44px; a post with none shows the icon alone, no number, named \"Comment\", the same way in at the"
                  " same place",
                  got is not None and got.get("label") == "3 comments" and got.get("text") == "3" and got.get("icon")
                  and got.get("first") and got.get("next")
                  and got.get("href") == f"/social/p/{post}#comments" and got.get("beside") == 14
                  and got.get("middle") and got.get("w", 0) >= 44 and got.get("h", 0) >= 44
                  and none.get("label") == "Comment" and none.get("text") == "" and none.get("icon")
                  and none.get("href") == f"/social/p/{bare}#comments" and none.get("beside") == got.get("beside")
                  and none.get("middle") and none.get("w", 0) >= 44 and none.get("h", 0) >= 44,
                  f"{got}; with none {none}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "on a desk: the comments beside the drawing, under Share"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 12, a snail", seed=121)
            cid = said(theo, post, "Section 12, beside the drawing")
            dctx, dpg = browser_as(b, juno, "desk", "light")
            open_post(dpg, post)
            WHERE = """() => { const r = s => document.querySelector(s).getBoundingClientRect();
              const art = r('.post-art'), share = r('.post-actions'), sec = r('#comments'), box = r('[data-cm-box]'), icon = r('.cm-say');
              return { right: Math.round(sec.left - art.right), under: Math.round(sec.top - share.bottom),
                       left: Math.round(sec.left - share.left), width: Math.round(sec.width), box: Math.round(box.width),
                       boxTop: Math.round(box.top - r('.comments-head').bottom), icon: Math.round(sec.right - icon.right),
                       onscreen: icon.bottom < innerHeight }; }"""
            where = dpg.evaluate(WHERE)
            _, err = steps(lambda: open_box(dpg))
            opened = dpg.evaluate(WHERE)
            # TYPING TO THE LAST HUNDRED (the counter, "5 left"), in the box and in
            # an answer's: the box keeps to its column (main's run after #883 read it
            # 350 in a 340 column in GitHub's wider font, and here the counter pushed
            # it to 360), Post stays where it was, and the counter reads on its own
            # line under Post, at its right edge.
            before = dpg.evaluate(POST_AT)
            named = dpg.locator("[data-cm-box]").get_by_role("button", name="Post", exact=True).count()
            spread = dpg.evaluate(TOO_WIDE)
            dpg.fill("#cmWords", "word " * 99)
            dpg.wait_for_timeout(200)
            near = dpg.evaluate(NEAR_LIMIT)
            _, err2 = steps(lambda: answer_box(dpg, cid))
            dpg.fill("#cmWords", "word " * 99)
            dpg.wait_for_timeout(200)
            answering = dpg.evaluate(NEAR_LIMIT)
            close_ctx(dctx, dpg)
            check("on a desk the comments sit beside the drawing, under Share and Make your own, in the same column, the icon at"
                  " the end of their heading within reach; the box opens right under the heading, as wide as the column",
                  where["right"] >= 24 and 0 < where["under"] <= 40 and where["left"] == 0 and where["width"] >= 300
                  and where["icon"] == 0 and where["onscreen"] and err is None and opened["box"] == opened["width"]
                  and opened["boxTop"] == 10,
                  f"{where}; opened {opened}; stopped {err}")
            check("the box keeps to its column whatever is in it (a wider font, larger words, something far too wide):"
                  " Post at its right edge, nothing past it, no gap under Post, and as wide saying \"Posting…\" (named"
                  " Post all the same); typing to the last hundred characters,"
                  " the counter (\"5 left\") reads on its own line under Post, at its right edge, and Post stays where"
                  " it was; the same in an answer's box",
                  abs(before["edge"]) <= 1 and abs(before["foot"]) <= 1
                  and before["posting"] == "Posting…" and before["held"] and before["sides"] == "12px 12px" and named == 1
                  and spread["box"] == spread["col"] and spread["chipsIn"] and abs(spread["edge"]) <= 1
                  and spread["withWide"] == spread["col"]
                  and near["text"] == "5 left" and near["painted"] and near["box"] == near["holder"]
                  and near["right"] <= near["holderRight"] and near["x"] == before["x"] and near["dy"] == before["dy"]
                  and near["under"] >= 0 and abs(near["edge"]) <= 1
                  and err2 is None and answering["text"] == "5 left" and answering["painted"]
                  and answering["box"] <= answering["holder"] and answering["right"] <= answering["holderRight"]
                  and answering["under"] >= 0 and abs(answering["edge"]) <= 1,
                  f"before {before}; named Post {named}; too wide {spread}; near {near}; answering {answering};"
                  f" stopped {err2}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(12, exc)

    # ------------------------------------------------------------------ 13
    if part(13, "the new screens: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        try:
            juno = admin(b)
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 13, a snail", seed=131)
            t13 = said(theo, post, "That shell spiral is so good.")
            said(juno, post, "Thank you!", answer_to=t13)
            m13 = said(mira, post, "My cat would never be this patient")
            down13 = said(mira, post, "Section 13, taken down")
            db_write("update social_comments set taken_down_at = datetime('now') where public_id = ?", (down13,))
            kc = mira.client()
            kc.get(f"/social/p/{post}")
            kc.post_json("/social/report", {"kind": "comment", "target": t13, "reason": "spam"})
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, mira, screen=screen, scheme=scheme)
                    open_post(cpg, post)
                    cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    cpg.wait_for_timeout(300)
                    seen[(screen, scheme, "comments")] = cpg.evaluate(READ, "#comments")
                    cpg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", m13)
                    answer_box(cpg, t13)
                    seen[(screen, scheme, "answering")] = cpg.evaluate(READ, "#comments, #commentBoxSheet")
                    cpg.keyboard.press("Escape")
                    cpg.wait_for_function(GONE, timeout=8000)
                    cpg.wait_for_timeout(200)
                    cpg.click(f"#c-{t13} > .cm-main [data-cm-menu]")
                    cpg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
                    cpg.wait_for_timeout(450)
                    seen[(screen, scheme, "⋯")] = cpg.evaluate(READ, "#commentSheet")
                    cpg.click("#commentSheet [data-cm-act=report]")
                    cpg.wait_for_function(OPEN, arg="commentReportSheet", timeout=10000)
                    cpg.wait_for_timeout(450)
                    seen[(screen, scheme, "report")] = cpg.evaluate(READ, "#commentReportSheet")
                    cpg.goto(BASE + "/social/")
                    cpg.wait_for_timeout(600)
                    cpg.evaluate("(id) => { const c = document.querySelector('.post-card[data-post=\"' + id + '\"] .post-row');"
                                 " c && c.scrollIntoView({ block: 'center' }); }", post)
                    cpg.wait_for_timeout(300)
                    seen[(screen, scheme, "home's card")] = cpg.evaluate(READ, f".post-card[data-post='{post}'] .post-row")
                    close_ctx(cctx, cpg)
                    nctx, npg = browser_as(b, None, screen=screen, scheme=scheme)
                    open_post(npg, post)
                    npg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    npg.wait_for_timeout(300)
                    seen[(screen, scheme, "signed out")] = npg.evaluate(READ, "#comments")
                    npg.click(".cm-say")
                    npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000)
                    npg.wait_for_timeout(450)
                    seen[(screen, scheme, "say something?")] = npg.evaluate(READ, "#commentOutSheet")
                    close_ctx(nctx, npg)
                    actx, apg = browser_as(b, juno, screen=screen, scheme=scheme)
                    apg.goto(BASE + "/social/reports")
                    apg.wait_for_timeout(600)
                    apg.evaluate("(t) => { const c = document.querySelector('[data-rep][data-target=\"' + t + '\"]'); c && c.scrollIntoView({ block: 'center' }); }", t13)
                    apg.wait_for_timeout(300)
                    seen[(screen, scheme, "your reports")] = apg.evaluate(READ, f"[data-rep][data-target='{t13}']")
                    close_ctx(actx, apg)
            low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
            small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
            fields = [(k, v["fields"]) for k, v in seen.items() if v["fields"]]
            lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
            musts = {"comments": ("Comments", "Mira Okafor", "My cat would never be this patient", "Answer", NOTE[:24]),
                     # Mira sees her own comment taken down, so four, said alone.
                     "answering": ("Post",), "signed out": ("Comments", "Theo Lind"),
                     "say something?": ("Say something?", "Sign in, and you can answer", "Not now", "Sign in"),
                     "home's card": ("4",), "⋯": ("Report comment",), "your reports": ("Theo Lind",)}
            missing = [(" ".join(k), w) for k, v in seen.items() for w in musts.get(k[2], ())
                       if not any(x == w or (len(w) > 3 and x.startswith(w[:24])) for x in v["words"])]
            check("every word on the comments (a comment, an answer, the box answering, the count, Answer, a taken-down note,"
                  " \"Say something?\" signed out), a comment's ⋯ and its report, Home's card's count and Your Reports' comment card reads at 4.5:1"
                  " or more on what is painted behind it, every control is 44px or more each way, every text field 16px:"
                  " phone and desk, light and dark",
                  not low and not small and not fields and not missing and all(v["read"] >= 1 for v in seen.values()),
                  f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small: {small[:3]};"
                  f" fields: {fields[:3]}; not read: {missing[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(13, exc)

    # ------------------------------------------------------------------ 14
    if part(14, "a drawing answer, in the box: Draw and Flip open Skribl's editor over the post; it waits there until Post"):
        try:
            juno = someone(b, "juno", "Juno Park")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 14, a snail", seed=151)
            pg = mira.pg
            open_post(pg, post)

            def draw():
                open_box(pg)
                pg.click("[data-cm-open=pad]", timeout=8000)
                fr = editor_frame(pg, "skribl-pad")
                src = pg.evaluate("() => document.querySelector('#commentPad iframe').getAttribute('src')")
                sheet = add_from_pad(pg, fr) if fr else {}
                return {"fr": bool(fr), "src": src, "sheet": sheet, "drafted": pg.evaluate(DRAFT)}

            got, err = steps(draw)
            src, sheet, drafted = got.get("src") or "", got.get("sheet") or {}, got.get("drafted") or {}
            check("Draw opens Skribl's Pad over the post in compose mode, without the gallery tick (a drawing answer is"
                  " unlisted); Add hands the drawing back into the box's own in-post player, Draw and Flip step aside, and"
                  " focus lands on Edit drawing",
                  err is None and got["fr"] and "compose=1" in src and "gallery=1" not in src
                  and sheet.get("label") == "Add to post" and not sheet.get("tick")
                  and drafted.get("shown") and drafted.get("attached") and drafted.get("chips") == [True, True]
                  and drafted.get("overlay") and drafted.get("focus") == "Edit drawing",
                  f"src {src}; sheet {sheet}; drafted {drafted}; stopped {err}")

            def edit_and_remove():
                pg.evaluate("""() => { window.__loads = 0; const f = document.querySelector('#commentPad iframe');
                  f.contentWindow.addEventListener('message', e => { if (e.data && e.data.type === 'skribl:compose:load') window.__loads++; }); }""")
                pg.click("[data-cm-edit]", timeout=8000)
                pg.wait_for_timeout(900)
                reopened = pg.evaluate("() => ({ open: !document.getElementById('commentPad').hidden, loads: window.__loads })")
                if reopened["open"]:
                    fr2 = editor_frame(pg, "skribl-pad")
                    if fr2:
                        fr2.click("#composeCloseBtn", timeout=8000)
                        pg.wait_for_timeout(700)
                kept = pg.evaluate(DRAFT)
                pg.click("[data-cm-remove]", timeout=8000)
                pg.wait_for_timeout(400)
                return {"reopened": reopened, "kept": kept, "removed": pg.evaluate(DRAFT),
                        "frame": pg.evaluate("() => document.querySelector('#commentPad iframe').getAttribute('src')")}

            got, err = steps(edit_and_remove)
            reopened, kept, removed = got.get("reopened") or {}, got.get("kept") or {}, got.get("removed") or {}
            check("Edit drawing reopens the Pad with the drawing put back in it (a load message), and closing it keeps the"
                  " drawing waiting; Remove takes it away, Draw and Flip come back, and the frame is let go (about:blank)",
                  err is None and reopened.get("open") and reopened.get("loads", 0) >= 1 and kept.get("shown")
                  and kept.get("attached") and not removed.get("shown") and removed.get("chips") == [False, False]
                  and got.get("frame") == "about:blank",
                  f"reopened {reopened}; kept {kept}; removed {removed}; frame {got.get('frame')}; stopped {err}")

            def flip():
                pg.click("[data-cm-open=flip]", timeout=8000)
                ffr = editor_frame(pg, "/flip?", timeout=20)
                out = {"frame": bool(ffr),
                       "src": pg.evaluate("() => document.querySelector('#commentFlip iframe').getAttribute('src')"),
                       "open": pg.evaluate("() => !document.getElementById('commentFlip').hidden")}
                if ffr:
                    ffr.click("#composeCloseBtn", timeout=8000)
                    pg.wait_for_timeout(700)
                out["closed"] = pg.evaluate("() => document.getElementById('commentFlip').hidden")
                return out

            got, err = steps(flip)
            fsrc = got.get("src") or ""
            check("Flip opens Skribl's Flip over the post the same way (compose=1, no gallery tick), and its × puts it away",
                  err is None and got.get("frame") and got.get("open") and "compose=1" in fsrc
                  and "gallery=1" not in fsrc and got.get("closed"),
                  f"{got}; stopped {err}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(14, exc)

    # ------------------------------------------------------------------ 15
    if part(15, "a drawing answer, posted: unlisted through create_post, still until tapped"):
        try:
            juno = someone(b, "juno", "Juno Park")
            mira = someone(b, "mira", "Mira Okafor")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 15, a snail", seed=161)
            theo_c = said(theo, post, "Section 15, Theo's")
            pg = mira.pg
            open_post(pg, post)

            def drawn_and_posted():    # a box that cannot be used is this row's red, never a stop
                open_box(pg)
                pg.click("[data-cm-open=pad]", timeout=8000)
                fr = editor_frame(pg, "skribl-pad")
                if fr:
                    add_from_pad(pg, fr)
                pg.fill("[data-cm-words]", "My cat would never be this patient", timeout=8000)
                g = pg.evaluate(POST_AND_WATCH)
                pg.wait_for_function(GONE, timeout=8000)
                pg.wait_for_timeout(300)
                return g, pg.evaluate(DRAFT)

            got_, err15 = steps(drawn_and_posted)
            got, after = got_ or ({"id": None, "ops": []}, {"shown": True, "chips": []})
            row = db("select skribl_id, words from social_comments where public_id = ?", (got["id"] or "",))
            sid = row[0][0] if row else None
            sk = db("select visibility, user_id, title, caption from skribl_posts where public_id = ?", (sid or "",))
            shown = pg.evaluate(ART, got["id"] or "")
            check("Post sends the words and the drawing as one comment: its drawing through create_post, unlisted, the"
                  " person its author, titled by the words; the comment's row keeps the drawing's id; it arrives with its"
                  " drawing in Skribl's in-post player; the box is ready again (no drawing, Draw and Flip back)",
                  row and row[0][1] == "My cat would never be this patient" and sid
                  and sk and sk[0][:3] == ("unlisted", pid_of("mira")[1], "My cat would never be this patient")
                  and not sk[0][3]
                  and shown == sid and not after["shown"] and after["chips"] == [False, False],
                  f"row {row}; skribl {sk}; on the page {shown}; box {after}; stopped {err15}")
            # A drawing answer, alone, and under a comment.
            open_post(pg, post)
            answer_box(pg, theo_c)
            pg.click("[data-cm-open=pad]")
            fr = editor_frame(pg, "skribl-pad")
            if fr:
                add_from_pad(pg, fr)
            alone = pg.evaluate(POST_AND_WATCH)
            arow = db("select c.words, c.skribl_id is not null, p.public_id from social_comments c"
                      " left join social_comments p on p.id = c.parent_id where c.public_id = ?", (alone["id"] or "",))
            check("a drawing alone is a comment too, and an answer can be one: under the comment it answers, its drawing"
                  " in the player, no words",
                  arow == [("", 1, theo_c)] and pg.evaluate(ART, alone["id"] or "") is not None,
                  f"row {arow}")
            # STILL UNTIL TAPPED: on the post's own page only the post's drawing plays by itself.
            open_post(pg, post)
            pg.wait_for_timeout(1500)
            states = dict(pg.evaluate(STATES))
            post_sid = db("select skribl_id from social_posts where public_id = ?", (post,))[0][0]
            mine = states.get(sid) or {}
            pg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", got["id"])
            pg.click(f"#c-{got['id']} > .cm-main .cm-art .skribl-inline")
            pg.wait_for_timeout(1200)
            tapped = dict(pg.evaluate(STATES)).get(sid) or {}
            own = states.get(post_sid) or {}
            check("on the post's page the post's own drawing plays by itself, and a comment's drawing waits, still and not"
                  " even fetched, until it is tapped; tapped, it plays",
                  own.get("loaded") and own.get("ms", 0) > 0 and mine.get("state") == "idle" and not mine.get("loaded")
                  and tapped.get("loaded") and tapped.get("ms", 0) > 0,
                  f"post {own}; comment's before {mine}, tapped {tapped}")
            listed = [i["id"] for i in json.loads(urllib.request.urlopen(BASE + "/api/skribls?limit=100", timeout=20)
                                                  .read().decode())["items"]]
            pg.goto(BASE + "/social/")
            pg.wait_for_timeout(600)
            on_home = pg.evaluate("(id) => !!document.querySelector('[data-skribl=\"' + id + '\"], [data-skribl-id=\"' + id + '\"]')", sid)
            check("a drawing answer is unlisted: Skribl's listing does not show it, nor Home",
                  sid not in listed and not on_home, f"listed {sid in listed}; on Home {on_home}")
            # AS BIG AS A POST'S: a long drawing is past the site's 64 KiB for every other request.
            big = drawing(n=2000, seed=163)
            weight = len(json.dumps({"words": "", "payload": big}).encode())
            bc = mira.client()
            bc.get(f"/social/p/{post}")
            st_big = bc.post_json(f"/social/p/{post}/comments", {"words": "", "payload": big})[0]
            check("a drawing answer may weigh what a post's drawing does: a long one, past the 64 KiB every other request"
                  " to the site stops at, is taken",
                  weight > 64 * 1024 and st_big == 200, f"{weight // 1024} KiB: {st_big}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(15, exc)

    # ------------------------------------------------------------------ 16
    if part(16, "a drawing goes with its comment: deleted, removed, its post deleted, its person's account deleted"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            ute = someone(b, "ute", "Ute Brandt")
            post = make_post(juno, "Section 16, a snail", seed=171)

            def drawn(who, on, words, seed, answer_to=None):
                c = who.client()
                c.get(f"/social/p/{on}")
                body = {"words": words, "payload": drawing(seed=seed)}
                if answer_to:
                    body["answer_to"] = answer_to
                st, j = c.post_json(f"/social/p/{on}/comments", body)
                cid = j.get("comment") if st == 200 and isinstance(j, dict) else None
                sid = db("select skribl_id from social_comments where public_id = ?", (cid or "",))
                return cid, (sid[0][0] if sid else None)

            def there(*sids):
                return [bool(db("select 1 from skribl_posts where public_id = ?", (s or "",))) for s in sids]

            own_c, own_s = drawn(theo, post, "Section 16, Theo's, deleted", 172)
            under_s = drawn(mira, post, "Section 16, Mira under Theo's", 173, answer_to=own_c)[1]
            tc = theo.client()
            tc.get(f"/social/p/{post}")
            before = there(own_s, under_s)
            tc.post_json(f"/social/c/{own_c}/delete", {})
            rm_c, rm_s = drawn(mira, post, "Section 16, Mira's, removed", 174)
            jc = juno.client()
            jc.get(f"/social/p/{post}")
            jc.post_json(f"/social/c/{rm_c}/delete", {})
            check("a comment deleted takes its drawing with it, and every answer's drawing under it; a comment removed from"
                  " your post takes the commenter's drawing too (Skribl's delete_post, as its author)",
                  before == [True, True] and there(own_s, under_s, rm_s) == [False, False, False] and own_s and rm_s,
                  f"before {before}; after {there(own_s, under_s, rm_s)}")
            gone_post = make_post(juno, "Section 16, to be deleted", seed=175)
            on_c, on_s = drawn(mira, gone_post, "Section 16, on the post", 176)
            ans_s = drawn(theo, gone_post, "Section 16, under it", 177, answer_to=on_c)[1]
            jc.get(f"/social/p/{gone_post}")
            jc.post_json(f"/social/p/{gone_post}/delete", {})
            other = make_post(theo, "Section 16, Theo's post", seed=178)
            ute_c, ute_s = drawn(ute, other, "Section 16, Ute's", 179)
            ute_under = drawn(theo, other, "Section 16, Theo under Ute's", 180, answer_to=ute_c)[1]
            theo_own = drawn(theo, other, "Section 16, Theo's own", 181)[1]
            upg = ute.pg
            upg.goto(BASE + "/social/you/delete")
            upg.wait_for_timeout(400)
            upg.fill("input[name=confirm]", "ute")
            with upg.expect_navigation(timeout=15000):
                upg.click("form button[type=submit].btn-danger, form button[type=submit]")
            check("a post deleted takes its comments' drawings, answers' too; an account deleted takes the drawings of its"
                  " comments and of every answer under them, and leaves anybody else's",
                  there(on_s, ans_s) == [False, False] and there(ute_s, ute_under, theo_own) == [False, False, True],
                  f"post's {there(on_s, ans_s)}; account's {there(ute_s, ute_under, theo_own)}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(16, exc)

    # ------------------------------------------------------------------ 17
    if part(17, "a drawing answer reported and taken down: its picture on the card, withheld in Skribl"):
        try:
            juno = admin(b)
            theo = someone(b, "theo", "Theo Lind")
            kim = someone(b, "kim", "Kim Ito")
            db_write("update social_reports set state = 'kept' where state = 'open'")
            db_write("update skribl_reports set state = 'closed' where state = 'open'")
            post = make_post(kim, "Section 17, Kim's post", seed=181)
            c = theo.client()
            c.get(f"/social/p/{post}")
            st, j = c.post_json(f"/social/p/{post}/comments", {"words": "", "payload": drawing(seed=182)})
            cid = j.get("comment") if st == 200 else None
            sid = db("select skribl_id from social_comments where public_id = ?", (cid or "",))[0][0]
            kc = kim.client()
            kc.get(f"/social/p/{post}")
            kc.post_json("/social/report", {"kind": "comment", "target": cid, "reason": "spam"})
            nctx, npg = browser_as(b, None)
            npg.goto(BASE + f"/s/{sid}")
            npg.wait_for_timeout(500)
            on_link = npg.evaluate("""async (id) => { await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
              const tok = decodeURIComponent((document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '');
              const r = await fetch('/api/skribls/' + id + '/report', { method: 'POST', credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': tok }, body: JSON.stringify({ reason: 'abuse' }) });
              return r.status; }""", sid)
            close_ctx(nctx, npg)
            apg = juno.pg
            apg.goto(BASE + "/social/reports")
            apg.wait_for_timeout(700)
            card = apg.evaluate("""(t) => { const cs = [...document.querySelectorAll('[data-rep][data-target="' + t + '"]')];
              if (cs.length !== 1) return { cards: cs.length }; const c = cs[0], p = c.querySelector('.rep-pic');
              return { cards: 1, kind: c.dataset.kind, pic: p ? getComputedStyle(p).backgroundImage.includes('/s/') : false,
                       words: [...c.querySelectorAll('.rep-words')].map(e => e.textContent),
                       why: [...c.querySelectorAll('.rep-why')].map(e => e.textContent).sort(),
                       by: c.querySelector('.rep-by').innerText }; }""", cid)
            others = apg.evaluate("(s) => !!document.querySelector('[data-rep][data-target=\"' + s + '\"]')", sid)
            check("a drawing answer's card on Your Reports shows its picture (\"A drawing\" for no words), and what was"
                  " reported of its drawing on Skribl's own link page lands on the same card",
                  st == 200 and on_link == 202 and not others
                  and card == {"cards": 1, "kind": "comment", "pic": True, "words": ["A drawing"],
                               "why": ["Abusive or hateful", "Spam or misleading"],
                               "by": "Reported by Kim Ito, somebody on Explore"},
                  f"posted {st}; link page report {on_link}; card {card}; a drawing card too {others}")
            with apg.expect_navigation(timeout=15000):
                apg.click(f"[data-rep][data-target='{cid}'] form[action$=down] button")
            vis = db("select visibility from skribl_posts where public_id = ?", (sid,))
            sk_open = db("select count(*) from skribl_reports r join skribl_posts p on p.id = r.post_id"
                         " where p.public_id = ? and r.state = 'open'", (sid,))[0][0]
            nctx, npg = browser_as(b, None)
            link = status(npg, f"/s/{sid}")
            close_ctx(nctx, npg)
            check("Take it down withholds its drawing in Skribl too (its link page gone for everybody else) and closes"
                  " Skribl's reports of it with the site's",
                  vis == [("withheld",)] and sk_open == 0 and link == 404, f"visibility {vis}; open {sk_open}; link page {link}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(17, exc)

    # ------------------------------------------------------------------ 18
    if part(18, "the box with a drawing: words at 4.5:1, targets 44px; phone and desk, light and dark"):
        try:
            juno = someone(b, "juno", "Juno Park")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 18, a snail", seed=191)
            c = mira.client()
            c.get(f"/social/p/{post}")
            c.post_json(f"/social/p/{post}/comments", {"words": "Section 18, drawn", "payload": drawing(seed=192)})
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, mira, screen=screen, scheme=scheme)
                    open_post(cpg, post)
                    cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    cpg.wait_for_timeout(300)
                    def read_box():    # a box that cannot be used is this row's red, never a stop
                        open_box(cpg)
                        seen[(screen, scheme, "the box")] = cpg.evaluate(READ, "[data-cm-box]")
                        cpg.click("[data-cm-open=pad]", timeout=8000)
                        fr = editor_frame(cpg, "skribl-pad")
                        if fr:
                            add_from_pad(cpg, fr)
                        cpg.evaluate("() => document.querySelector('[data-cm-box]').scrollIntoView({ block: 'center' })")
                        cpg.wait_for_timeout(400)
                        seen[(screen, scheme, "a drawing waiting")] = cpg.evaluate(READ, "[data-cm-box]")

                    _, err = steps(read_box)
                    for k in ("the box", "a drawing waiting"):
                        seen.setdefault((screen, scheme, k), {"read": 0, "low": [], "small": [], "fields": [], "lowest": 99,
                                                              "words": [], "stopped": err})
                    close_ctx(cctx, cpg)
            low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
            small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
            fields = [(k, v["fields"]) for k, v in seen.items() if v["fields"]]
            lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
            musts = {"the box": ("Draw", "Flip", "Post"), "a drawing waiting": ("Edit drawing", "Remove", "Post")}
            missing = [(" ".join(k), w) for k, v in seen.items() for w in musts.get(k[2], ())
                       if not any(x == w for x in v["words"])]
            check("every word in the box (Draw, Flip, Post; with a drawing waiting, Edit drawing and Remove) reads at 4.5:1"
                  " or more on what is painted behind it, every control is 44px or more each way, the words' field"
                  " 16px or more: phone and desk, light and dark",
                  not low and not small and not fields and not missing,
                  f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]};"
                  f" small: {small[:3]}; fields: {fields[:3]}; not read: {missing[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(18, exc)

    # ------------------------------------------------------------------ 20
    # COMMENTS ON EVERY DRAWING (the owner's yes, Nov 12): a drawing shown
    # outside a post, made in the Pad and shown in the gallery, has a post's
    # comments on its own page (/social/b/<id>), by the rules of that page.
    if part(20, "a drawing's own page has the comments: the section, the box, signed out, Load more"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            sid = make_drawing(juno, "Section 20, a wave from the Pad", seed=201)
            pg = theo.pg
            open_drawing(pg, sid)
            empty = pg.evaluate(SECTION)
            title = pg.evaluate("() => { const t = document.getElementById('commentsTitle');"
                                " return t ? t.innerText.replace(/\\s+/g, ' ').trim() : null; }")
            box, err = steps(lambda: (open_box(pg), pg.evaluate(BOX))[1])
            got = {}
            if box:                     # no box is the row's red, never a stop
                got = steps(lambda: (pg.fill("[data-cm-words]", "  That wave!   Hello to you too.  ", timeout=8000),
                                     pg.evaluate(POST_AND_WATCH))[1])[0]
            after = pg.evaluate(SECTION)
            words = db("select words from social_comments where public_id = ?", (got.get("id") or "",))
            check("a drawing shown outside a post (/social/b/<id>, made in the Pad) has a post's comments: \"Comments\","
                  " no number at none, the box behind the icon (a face, \"Say something, or draw it…\", Draw, Flip, Post,"
                  " \"Say something to Juno\"); the box sends the words, tidied, and the comment fades in at the top, said"
                  " \"now\", the count with it; its row is on the drawing (its skribl's id, no post) and keeps whose the drawing is",
                  bool(sid) and empty == {"count": None, "list": []} and title == "Comments" and box is not None
                  and box["open"] == "sheet" and box["title"] == "Say something to Juno"
                  and box["face"] and box["placeholder"] == "Say something, or draw it…"
                  and box["chips"] == ["Draw", "Flip"] and box["post"] == "Post" and box["font"] >= 16
                  and bool(got.get("id")) and faded(got.get("ops", [])) >= 2 and got["ops"][-1] == 1
                  and words == [("That wave! Hello to you too.",)] and on_row(got["id"]) == (None, sid, "juno", None)
                  and after["count"] == "1" and [c["when"] for c in after["list"]] == ["now"],
                  f"drawing {sid}; before {empty}; title {title!r}; box {box}; posted {got.get('id')} (faded"
                  f" {faded(got.get('ops', []))}); words {words}; row {on_row(got.get('id'))}; after {after}")
            nctx, npg = browser_as(b, None)
            open_drawing(npg, sid)
            out = {"section": npg.evaluate(SECTION), "box": npg.evaluate(BOX)}
            sheet, err2 = steps(lambda: (npg.click(".cm-say", timeout=8000),
                                         npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000),
                                         npg.wait_for_timeout(450), npg.evaluate(OUT_SHEET))[-1])
            close_ctx(nctx, npg)
            check("signed out, a drawing's comments are readable, with no box and no Answer: the icon raises \"Say"
                  " something?\", its Sign in back to the drawing's page with the box open",
                  out["box"] is None and out["section"]["count"] == "1"
                  and [(c["name"], c["answer"]) for c in out["section"]["list"]] == [("Theo Lind", False)]
                  and sheet and sheet["path"] == "/social/signin" and sheet["next"] == f"/social/b/{sid}#say",
                  f"{out}; sheet {sheet}; stopped {err2}")
            # LOAD MORE on a drawing reads the drawing's own comments, by its own route.
            sam = someone(b, "sam", "Sam Okafor")
            busy = make_drawing(juno, "Section 20, a busy drawing", seed=202)
            made = [said_on(sam, busy, f"Section 20, comment {k:02d}") for k in range(22)]
            spg = sam.pg
            open_drawing(spg, busy)
            first = [c["id"] for c in spg.evaluate(SECTION)["list"]]
            btn = spg.evaluate("() => { const b = document.querySelector('[data-cm-next]'); return b && !b.hidden ? b.textContent : null; }")

            def more():
                spg.click("[data-cm-next]")
                spg.wait_for_function("() => document.querySelectorAll('[data-cm-list] > .cm').length > 20", timeout=10000)
                spg.wait_for_timeout(300)

            # No Load more, or one that never brings anything, is the row's red, never a stop.
            _, stuck = steps(more) if btn else ({}, None)
            allc = [c["id"] for c in spg.evaluate(SECTION)["list"]]
            check("on a drawing too, twenty comments a page, newest first; Load more brings the rest in place, the"
                  " drawing's own, in order, none twice and none missed",
                  all(made) and first == list(reversed(made))[:20] and btn == "Load more" and stuck is None
                  and allc == list(reversed(made)),
                  f"made {sum(1 for m in made if m)}; first page {len(first)}; button {btn!r}; after {len(allc)}"
                  f" ({len(set(allc))} different); stopped {stuck}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(20, exc)

    # ------------------------------------------------------------------ 21
    if part(21, "answers and drawing answers on a drawing: one level deep, the real Pad over its page"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            sid = make_drawing(juno, "Section 21, a drawing", seed=211)
            theo_c = said_on(theo, sid, "Section 21, Theo's")
            for k in range(3):
                said_on(juno, sid, f"Section 21, filler {k}: so the page scrolls")
            pg = mira.pg
            open_drawing(pg, sid)
            pg.evaluate("(id) => { const r = document.getElementById('c-' + id).getBoundingClientRect();"
                        " window.scrollBy(0, r.top - innerHeight / 2); }", theo_c)
            pg.wait_for_timeout(300)
            went = pg.evaluate(ANSWER_AND_WATCH, theo_c)
            there = pg.evaluate(BOX)
            mine = steps(lambda: (pg.fill("[data-cm-words]", "Section 21, Mira under Theo's", timeout=8000),
                                  pg.evaluate(POST_AND_WATCH))[1])[0] or {"id": None}
            deep = said_on(juno, sid, "Section 21, Juno answering Mira", answer_to=mine["id"])
            open_drawing(pg, sid)
            under = [a["words"] for a in next((c for c in pg.evaluate(SECTION)["list"] if c["id"] == theo_c),
                                              {"answers": []})["answers"]]
            rows = [on_row(mine["id"]), on_row(deep)]
            # An answer is on what its comment is on: never from another drawing, nor from a post.
            elsewhere = make_drawing(juno, "Section 21, another drawing", seed=212)
            a_post = make_post(juno, "Section 21, a post", seed=213)
            crossed = [say_on(mira, elsewhere, "Section 21, crossing over", answer_to=theo_c)[0],
                       say(mira, a_post, "Section 21, crossing from a post", answer_to=theo_c)[0]]
            check("on a drawing, Answer opens the box for the comment (\"Answer Theo\", \"Answer Theo…\"), the comment keeping its place;"
                  " the answer sits under it, and an answer to an answer under the same comment, oldest first, each on"
                  " the drawing, whose the drawing is kept; an answer to it from another drawing, or from a post, is"
                  " refused (404)",
                  there["open"] == "sheet" and there["title"] == "Answer Theo" and there["placeholder"] == "Answer Theo…"
                  and steady(went)
                  and under == ["Section 21, Mira under Theo's", "Section 21, Juno answering Mira"]
                  and rows == [(None, sid, "juno", theo_c)] * 2 and crossed == [404, 404],
                  f"box {there}; the move {went['now']}px, then {glide(went)}; under Theo's {under}; rows {rows};"
                  f" crossing over {crossed}")

            def drawn():
                open_drawing(pg, sid)
                open_box(pg)
                pg.click("[data-cm-open=pad]", timeout=8000)
                fr = editor_frame(pg, "skribl-pad")
                src = pg.evaluate("() => document.querySelector('#commentPad iframe').getAttribute('src')")
                sheet = add_from_pad(pg, fr) if fr else {}
                pg.fill("[data-cm-words]", "Section 21, a drawing back")
                return {"fr": bool(fr), "src": src or "", "sheet": sheet, "got": pg.evaluate(POST_AND_WATCH)}

            got, err = steps(drawn)
            cid = (got.get("got") or {}).get("id")
            row = db("select skribl_id from social_comments where public_id = ?", (cid or "",))
            skr = row[0][0] if row else None
            sk = db("select visibility, user_id, title from skribl_posts where public_id = ?", (skr or "",))
            shown = pg.evaluate(ART, cid or "") if cid else None
            sheet_said = {k: v for k, v in got.items() if k != "got"}   # not `said`: that is the module's helper
            check("a drawing answer on a drawing: Draw opens the real Pad over the drawing's page in compose mode, no"
                  " gallery tick; Post sends it with the words through create_post, unlisted, the person its author,"
                  " titled by the words; its comment is on the drawing; it arrives in Skribl's in-post player",
                  err is None and got.get("fr") and "compose=1" in got.get("src", "")
                  and "gallery=1" not in got.get("src", "") and not (got.get("sheet") or {}).get("tick")
                  and bool(skr) and on_row(cid) == (None, sid, "juno", None)
                  and sk == [("unlisted", pid_of("mira")[1], "Section 21, a drawing back")] and shown == skr,
                  f"{sheet_said}; comment {cid}, row {on_row(cid)}; skribl {sk}; on the page {shown}; stopped {err}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(21, exc)

    # ------------------------------------------------------------------ 22
    if part(22, "a comment's ⋯ on a drawing; delete and remove, by its author and by the drawing's owner"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            kim = someone(b, "kim", "Kim Ito")
            sid = make_drawing(juno, "Section 22, a drawing", seed=221)
            theo_c = said_on(theo, sid, "Section 22, Theo's, to be deleted")
            under = said_on(mira, sid, "Section 22, Mira's drawing under Theo's", answer_to=theo_c,
                            payload=drawing(seed=222))
            under_s = (db("select skribl_id from social_comments where public_id = ?", (under or "",)) or [(None,)])[0][0]
            mira_c = said_on(mira, sid, "Section 22, Mira's, to be removed")
            juno_c = said_on(juno, sid, "Section 22, Juno's own, kept")
            open_drawing(juno.pg, sid)
            on_mine = {"own": menu_of(juno.pg, juno_c), "theo's": menu_of(juno.pg, theo_c)}
            open_drawing(mira.pg, sid)
            elsewhere = menu_of(mira.pg, theo_c)
            check("on a drawing the ⋯ is a post's: on your own drawing your own comment's is \"Your comment\": Delete"
                  " comment, somebody else's \"Theo’s comment\": Remove from my post, Report comment; on somebody else's"
                  " drawing, Report comment alone",
                  on_mine == {"own": {"title": "Your comment", "acts": ["Delete comment"]},
                              "theo's": {"title": "Theo’s comment", "acts": ["Remove from my post", "Report comment"]}}
                  and elsewhere == {"title": "Theo’s comment", "acts": ["Report comment"]},
                  f"{on_mine}; on somebody else's {elsewhere}")
            before = skribl_there(under_s)
            open_drawing(theo.pg, sid)
            t_del = theo.pg.evaluate(DELETE_AND_WATCH, [theo_c, "delete"])
            left = db("select public_id from social_comments where public_id in (?, ?)", (theo_c, under or ""))
            check("on a drawing, Delete comment takes your own comment and every answer under it, their drawings too:"
                  " it fades out and is gone, the count with it",
                  t_del["gone"] and faded(t_del["ops"]) >= 2 and t_del["count"] == "2" and left == []
                  and bool(under_s) and before == [True] and skribl_there(under_s) == [False],
                  f"{t_del}; rows left {left}; the answer's drawing {before}, then {skribl_there(under_s)}")
            open_drawing(juno.pg, sid)
            j_rm = juno.pg.evaluate(DELETE_AND_WATCH, [mira_c, "remove"])
            kc = kim.client()
            kc.get(f"/social/b/{sid}")
            other = kc.post_json(f"/social/c/{juno_c}/delete", {})
            kept = db("select public_id from social_comments where public_id in (?, ?)", (mira_c, juno_c))
            check("the drawing's owner removes anybody's comment from it the same way (Remove from my post); nobody else"
                  " can (somebody else's, on somebody else's drawing, is gone to them: 404), and it stays",
                  j_rm["gone"] and faded(j_rm["ops"]) >= 2 and j_rm["count"] == "1" and other[0] == 404
                  and kept == [(juno_c,)],
                  f"{j_rm}; somebody else's {other}; rows {kept}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(22, exc)

    # ------------------------------------------------------------------ 23
    if part(23, "on a drawing: blocks either way, people taken down, the drawing taken down"):
        try:
            ada = someone(b, "ada", "Ada Quist")
            ben = someone(b, "ben", "Ben Reyes")
            cyd = someone(b, "cyd", "Cyd Mbeki")
            dee = someone(b, "dee", "Dee Varga")
            sid = make_drawing(ada, "Section 23, Ada's drawing", seed=231)
            ben_c = said_on(ben, sid, "Section 23, Ben's")
            cyd_c = said_on(cyd, sid, "Section 23, Cyd's")
            said_on(ben, sid, "Section 23, Ben under Cyd", answer_to=cyd_c)
            said_on(cyd, sid, "Section 23, Cyd under Ben", answer_to=ben_c)

            def seen_by(who):
                open_drawing(who.pg, sid)
                sec = who.pg.evaluate(SECTION)
                card = card_count(who.pg, sid)
                return {"count": sec["count"], "card": (card or {}).get("label"),
                        "shown": sorted([c["words"] for c in sec["list"]] + [a["words"] for c in sec["list"] for a in c["answers"]])}

            before = seen_by(dee)
            dc = dee.client()
            dc.get("/social/")
            dc.post_json("/social/@cyd/block", {})
            dee_blocked = seen_by(dee)
            dc.post_json("/social/@cyd/unblock", {})
            cc = cyd.client()
            cc.get("/social/")
            cc.post_json("/social/@dee/block", {})
            dee_by_cyd = seen_by(dee)
            cc.post_json("/social/@dee/unblock", {})
            all4 = sorted(["Section 23, Ben's", "Section 23, Cyd's", "Section 23, Ben under Cyd", "Section 23, Cyd under Ben"])
            bens = {"count": "1", "card": "1 comment", "shown": ["Section 23, Ben's"]}
            check("on a drawing, a block either way hides the other's comments and every answer under them: neither shown"
                  " nor counted, on the drawing's page and on its card on Home",
                  before == {"count": "4", "card": "4 comments", "shown": all4} and dee_blocked == bens
                  and dee_by_cyd == bens,
                  f"before {before}; dee blocked cyd {dee_blocked}; cyd blocked dee {dee_by_cyd}")

            # A BLOCK EITHER WAY WITH THE DRAWING'S MAKER: its page is gone to them,
            # and everything its comments' routes would answer.
            def asks(who, on_sid, a_comment):
                c = who.client()
                c.get("/social/")
                return {"page": status(who.pg, f"/social/b/{on_sid}"),
                        "comment": c.post_json(f"/social/b/{on_sid}/comments", {"words": "hi"}),
                        "answer": c.post_json(f"/social/b/{on_sid}/comments", {"words": "hi", "answer_to": a_comment}),
                        "more": c.get_json(f"/social/b/{on_sid}/comments")[0],
                        "report": c.post_json("/social/report", {"kind": "comment", "target": a_comment, "reason": "spam"})[0]}

            gone = {"page": 404, "comment": (404, {"error": "gone"}), "answer": (404, {"error": "gone"}), "more": 404,
                    "report": 404}
            eli = someone(b, "eli", "Eli Sato")
            fay = someone(b, "fay", "Fay Lund")
            ec = eli.client()
            ec.get("/social/")
            ec.post_json("/social/@ada/block", {})            # Eli blocks the drawing's maker
            ac = ada.client()
            ac.get("/social/")
            ac.post_json("/social/@fay/block", {})            # the drawing's maker blocks Fay
            eli_asks, fay_asks = asks(eli, sid, ben_c), asks(fay, sid, ben_c)
            n_rows = db("select count(*) from social_comments where drawing_id = ?", (sid,))[0][0]
            ec.post_json("/social/@ada/unblock", {})
            ac.post_json("/social/@fay/unblock", {})
            check("a block either way with the drawing's maker: its page is gone to them (a kind 404), and its comments"
                  " with it: none read (Load more), said, answered or reported, nothing written",
                  eli_asks == gone and fay_asks == gone and n_rows == 4,
                  f"eli, who blocked ada {eli_asks}; fay, whom ada blocked {fay_asks}; rows {n_rows}")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'cyd'")
            ben_after = seen_by(ben)
            cyd_own = seen_by(cyd)
            db_write("update social_people set taken_down_at = null where handle_key = 'cyd'")
            check("on a drawing, a person taken down: their comments, and the answers under them, neither shown nor"
                  " counted for anybody else; they still see their own",
                  ben_after == bens and cyd_own["count"] == "4", f"ben {ben_after}; cyd {cyd_own}")

            # THE DRAWING TAKEN DOWN (Your Reports' Take it down: withheld in Skribl):
            # its comments go from everybody else with its page; its maker keeps them.
            juno = admin(b)
            jc = juno.client()
            jc.get("/social/reports")
            down = jc._req("POST", "/social/reports/down", raw=urllib.parse.urlencode({"kind": "drawing", "target": sid}).encode(),
                           headers={"Content-Type": "application/x-www-form-urlencoded", "X-Social-CSRF": jc.token})[0]
            vis = db("select visibility from skribl_posts where public_id = ?", (sid,))
            ben_asks = asks(ben, sid, ben_c)
            own = status(ada.pg, f"/social/b/{sid}")
            own_sec, own_box = ada.pg.evaluate(SECTION), ada.pg.evaluate(BOX)
            own_note = ada.pg.evaluate("() => (document.querySelector('.post-page > .post-down') || {}).textContent || null")
            check("the drawing taken down by an admin (withheld in Skribl) takes its comments from everybody else with its"
                  " page: none read, said, answered or reported; its maker still sees them all on its page, with the note,"
                  " and no box",
                  down == 303 and vis == [("withheld",)] and ben_asks == gone and own == 200
                  and own_sec["count"] == "4" and own_box is None and own_note == NOTE,
                  f"take it down {down}, visibility {vis}; ben {ben_asks}; ada: page {own}, count {own_sec['count']},"
                  f" box {own_box}, note {own_note!r}")
            # Its maker taken down: the same for every drawing they made.
            other = make_drawing(ada, "Section 23, another of Ada's", seed=232)
            on_other = said_on(ben, other, "Section 23, Ben on the other")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'ada'")
            maker_down = asks(ben, other, on_other)
            db_write("update social_people set taken_down_at = null where handle_key = 'ada'")
            check("a drawing whose maker was taken down: its page and its comments are gone to everybody else the same way",
                  bool(on_other) and maker_down == gone, f"{maker_down}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(23, exc)

    # ------------------------------------------------------------------ 24
    if part(24, "a drawing deleted takes its comments: through the site, in code; in the Library, with its page"):
        try:
            nia = someone(b, "nia", "Nia Holm")
            oz = someone(b, "ozan", "Oz Brandt")
            # Somebody no earlier section deletes (section 9 deletes Pia's account).
            vee = someone(b, "vee", "Vee Laine")
            sid = make_drawing(nia, "Section 24, deleted on the site", seed=241)
            oz_c = said_on(oz, sid, "Section 24, Oz's")
            pia_a = said_on(vee, sid, "Section 24, Vee's drawing under it", answer_to=oz_c, payload=drawing(seed=242))
            pia_s = (db("select skribl_id from social_comments where public_id = ?", (pia_a or "",)) or [(None,)])[0][0]
            kept = make_drawing(nia, "Section 24, kept", seed=243)
            said_on(oz, kept, "Section 24, on the one kept")
            oc = oz.client()
            oc.get(f"/social/b/{kept}")
            not_hers = oc.post_json(f"/social/b/{kept}/delete", {})[0]
            before = skribl_there(pia_s)
            nc = nia.client()
            nc.get(f"/social/b/{sid}")
            gone = nc.post_json(f"/social/b/{sid}/delete", {})[0]
            left = db("select count(*) from social_comments where drawing_id = ?", (sid,))[0][0]
            still = db("select count(*) from social_comments where drawing_id = ?", (kept,))[0][0]
            check("a drawing deleted through the site (its ⋯, Delete post) takes every comment and answer on it, their"
                  " drawings too (Skribl's delete_post, as their authors); somebody else's try deletes nothing, its"
                  " comments kept",
                  gone == 200 and left == 0 and bool(pia_s) and before == [True] and skribl_there(pia_s) == [False]
                  and not_hers == 404 and still == 1 and skribl_there(kept) == [True],
                  f"deleted {gone}, comments left {left}; the answer's drawing {before}, then {skribl_there(pia_s)};"
                  f" somebody else's try {not_hers}, kept {still}")
            lib = make_drawing(nia, "Section 24, deleted in the Library", seed=244)
            lib_c = said_on(oz, lib, "Section 24, on it")
            nia.pg.goto(BASE + "/social/")
            st = nia.pg.evaluate(LIBRARY_DELETE, lib)
            asked = {"page, oz": status(oz.pg, f"/social/b/{lib}"), "page, nia": status(nia.pg, f"/social/b/{lib}")}
            c = oz.client()
            c.get("/social/")
            asked["more"] = c.get_json(f"/social/b/{lib}/comments")[0]
            asked["comment"] = c.post_json(f"/social/b/{lib}/comments", {"words": "hi"})[0]
            asked["answer"] = c.post_json(f"/social/b/{lib}/comments", {"words": "hi", "answer_to": lib_c})[0]
            asked["report"] = c.post_json("/social/report", {"kind": "comment", "target": lib_c, "reason": "spam"})[0]
            asked["home"] = card_count(oz.pg, lib)
            check("a drawing deleted in the Library, outside the site: its page is a kind 404 for everybody, its maker too,"
                  " and its comments go with it: none read (Load more), said, answered or reported, and no card on Home",
                  bool(lib_c) and st == 204
                  and asked == {"page, oz": 404, "page, nia": 404, "more": 404, "comment": 404, "answer": 404,
                                "report": 404, "home": None},
                  f"Library delete {st}; {asked}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(24, exc)

    # ------------------------------------------------------------------ 25
    if part(25, "an account deleted takes every comment on its drawings, and its own on others', in code"):
        try:
            qua = someone(b, "qua", "Qua Imre")
            rho = someone(b, "rho", "Rho Ngata")
            sol = someone(b, "sol", "Sol Berg")
            sid = make_drawing(qua, "Section 25, Qua's drawing", seed=251)
            rho_c = said_on(rho, sid, "Section 25, Rho on Qua's drawing")
            sol_a = said_on(sol, sid, "Section 25, Sol's drawing under Rho's", answer_to=rho_c, payload=drawing(seed=252))
            sol_s = (db("select skribl_id from social_comments where public_id = ?", (sol_a or "",)) or [(None,)])[0][0]
            rho_d = make_drawing(rho, "Section 25, Rho's drawing", seed=253)
            qua_c = said_on(qua, rho_d, "Section 25, Qua on Rho's drawing")
            rho_under = said_on(rho, rho_d, "Section 25, Rho under Qua's", answer_to=qua_c)
            rho_own = said_on(rho, rho_d, "Section 25, Rho's own")
            qpg = qua.pg
            qpg.goto(BASE + "/social/you/delete")
            qpg.wait_for_timeout(400)
            qpg.fill("input[name=confirm]", "qua")
            with qpg.expect_navigation(timeout=15000):
                qpg.click("form button[type=submit].btn-danger, form button[type=submit]")
            n = lambda cid: db("select count(*) from social_comments where public_id = ?", (cid or "",))[0][0]  # noqa: E731
            left = {"on her drawing": db("select count(*) from social_comments where drawing_id = ?", (sid,))[0][0],
                    "the drawing under it": skribl_there(sol_s)[0], "hers on rho's": n(qua_c),
                    "under hers": n(rho_under), "rho's own": n(rho_own)}
            check("through the site: deleting an account takes every comment and answer on its drawings (their drawings"
                  " too), its own comments on other people's drawings and every answer under them, and leaves anybody"
                  " else's",
                  pid_of("qua")[0] is None and bool(sol_s) and bool(rho_own)
                  and left == {"on her drawing": 0, "the drawing under it": False, "hers on rho's": 0, "under hers": 0,
                               "rho's own": 1},
                  f"account gone {pid_of('qua')[0] is None}; left {left}")
            # IN CODE, NOT BY THE CASCADE: owner_id's ON DELETE CASCADE takes these
            # with SQLite's foreign keys on, so a copy runs delete_person with them off.
            tia = someone(b, "tia", "Tia Moss")
            uma = someone(b, "uma", "Uma Roy")
            tsid = make_drawing(tia, "Section 25, Tia's drawing", seed=254)
            u1 = said_on(uma, tsid, "Section 25, Uma on Tia's")
            said_on(tia, tsid, "Section 25, Tia under Uma's", answer_to=u1)
            said_on(uma, tsid, "Section 25, Uma again")
            copy = os.path.join(TMP, "probe-drawing.db")
            src = sqlite3.connect(DB, timeout=10)
            dst = sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            probe = subprocess.run([sys.executable, "-c", PROBE_DRAWING, "tia", tsid or ""], cwd=ROOT, capture_output=True,
                                   text=True, timeout=180,
                                   env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}", SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-400:]}
            check("in code, not by the database's cascade: with SQLite's foreign keys off, delete_person for a drawing's"
                  " maker leaves no comment or answer on the drawing, nor any on anything they owned",
                  out == {"fk": 0, "before": 3, "left": 0, "owned": 0}, f"{out}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(25, exc)

    # ------------------------------------------------------------------ 26
    if part(26, "on a drawing: Report comment, Your Reports' card and its link, Take it down; Home's count"):
        try:
            juno = admin(b)
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            kim = someone(b, "kim", "Kim Ito")
            db_write("update social_reports set state = 'kept' where state = 'open'")
            db_write("update skribl_reports set state = 'closed' where state = 'open'")
            sid = make_drawing(mira, "Section 26, Mira's drawing", seed=261)
            bare = make_drawing(mira, "Section 26, nothing said yet", seed=262)
            theo_c = said_on(theo, sid, "Section 26, a mean thing")
            kept_c = said_on(theo, sid, "Section 26, kept")
            said_on(kim, sid, "Section 26, Kim under it", answer_to=kept_c)
            pg = kim.pg
            open_drawing(pg, sid)

            def report():
                pg.click(f"#c-{theo_c} > .cm-main [data-cm-menu]", timeout=8000)
                pg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
                pg.click("#commentSheet [data-cm-act=report]")
                pg.wait_for_function(OPEN, arg="commentReportSheet", timeout=10000)
                pg.check("#commentReportSheet input[value=abuse]")
                pg.click("#commentReportSheet [data-cm-report-send]")
                pg.wait_for_function("() => (document.querySelector('#commentReportSheet [data-cm-report-say]') || {})"
                                     ".textContent.length > 12", timeout=10000)
                return pg.evaluate("() => document.querySelector('#commentReportSheet [data-cm-report-say]').textContent")

            thanks, err = steps(report)
            rows = db("select kind, target, about_id, reason from social_reports where target = ?", (theo_c or "",))
            apg = juno.pg
            apg.goto(BASE + "/social/reports")
            apg.wait_for_timeout(700)
            card = apg.evaluate("""(t) => { const c = document.querySelector('[data-rep][data-target="' + t + '"]'); if (!c) return null;
              const a = c.querySelector('.rep-open'); return { kind: c.dataset.kind, who: c.querySelector('.rep-who').innerText,
              words: [...c.querySelectorAll('.rep-words')].map(e => e.textContent),
              link: a ? new URL(a.href).pathname + new URL(a.href).hash : null }; }""", theo_c)
            check("on a drawing, Report comment sends it into the site's own queue and says thanks; Your Reports' card"
                  " says whose it is and its words, with a link to it on the drawing's page",
                  err is None and thanks == THANKS and rows == [("comment", theo_c, pid_of("theo")[0], "abuse")]
                  and card == {"kind": "comment", "who": "Theo Lind @theo · a comment",
                               "words": ["“Section 26, a mean thing”"], "link": f"/social/b/{sid}#c-{theo_c}"},
                  f"said {thanks!r}; rows {rows}; card {card}; stopped {err}")
            if card:
                with apg.expect_navigation(timeout=15000):
                    apg.click(f"[data-rep][data-target='{theo_c}'] form[action$=down] button")
            open_drawing(mira.pg, sid)
            others = mira.pg.evaluate(SECTION)
            open_drawing(theo.pg, sid)
            his = theo.pg.evaluate(SECTION)
            mine = next((c for c in his["list"] if c["id"] == theo_c), {})
            state = db("select state from social_reports where target = ?", (theo_c or "",))
            check("Take it down hides a drawing's comment from everybody else at once (neither shown nor counted), keeps"
                  " it and closes its reports; its author sees it, with the note",
                  [c["id"] for c in others["list"]] == [kept_c] and others["count"] == "2" and mine.get("down") == NOTE
                  and his["count"] == "3" and state == [("taken_down",)]
                  and db("select count(*) from social_comments where public_id = ?", (theo_c or "",))[0][0] == 1,
                  f"mira sees {[c['id'] for c in others['list']]} ({others['count']}); theo's own {mine.get('down')!r}"
                  f" ({his['count']}); reports {state}")
            home = card_count(mira.pg, sid) or {}
            none = card_count(mira.pg, bare) or {}
            check("Home's card for a drawing counts its comments as its page does (the one taken down not counted): the"
                  " icon and the number, \"2 comments\", a way to them on the drawing's page, 44px; a drawing with none,"
                  " the icon alone, named \"Comment\"",
                  home.get("label") == "2 comments" and home.get("text") == "2" and home.get("icon")
                  and home.get("href") == f"/social/b/{sid}#comments" and home.get("w", 0) >= 44 and home.get("h", 0) >= 44
                  and none.get("label") == "Comment" and none.get("text") == "" and none.get("icon")
                  and none.get("href") == f"/social/b/{bare}#comments" and none.get("w", 0) >= 44
                  and none.get("h", 0) >= 44,
                  f"{home}; with none {none}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(26, exc)

    # ------------------------------------------------------------------ 27
    if part(27, "the site's chain on a populated database: a comment is on a post or a drawing, exactly one"):
        try:
            mdb = os.path.join(TMP, "chain-comments.db")
            # The chain's head before comments on drawings (that migration's down_revision).
            BEFORE = "b7d4e2f9a618"

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
            then = "2026-11-12 10:00:00"
            for i, h in ((1, "ann"), (2, "bob")):
                con.execute("insert into social_people (id, public_id, handle, handle_key, display_name, user_handle,"
                            " is_admin, session_gen, age_confirmed_at, created_at) values (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                            (i, "site:" + h, h, h, h.title(), bytes([i]) * 32, then, then))
            con.execute("insert into social_posts (id, public_id, person_id, words, skribl_id, created_at)"
                        " values (10, 'P1', 1, 'hi', 'S1', ?)", (then,))
            for row in ((100, "C1", 10, 2, None), (101, "C2", 10, 1, 100), (102, "C3", 99, 2, None)):
                con.execute("insert into social_comments (id, public_id, post_id, person_id, parent_id, words, created_at)"
                            " values (?, ?, ?, ?, ?, 'x', ?)", row + (then,))
            con.commit()
            con.close()
            up2 = chain("upgrade", "head")
            filled = at("select public_id, post_id, drawing_id, owner_id from social_comments order by id")
            con = sqlite3.connect(mdb)
            took = {}
            for name, post, drawing_id in (("both", 10, "D1"), ("neither", None, None), ("a drawing", None, "D1")):
                try:
                    con.execute("insert into social_comments (public_id, post_id, drawing_id, owner_id, person_id, words,"
                                " created_at) values (?, ?, ?, 1, 2, 'x', ?)", ("N-" + name, post, drawing_id, then))
                    took[name] = True
                except sqlite3.IntegrityError:
                    took[name] = False
            con.commit()
            con.close()
            check("the site's chain on a database with comments in it: each stays on its post and keeps whose the post is"
                  " (owner_id, from its author); one whose post is not there goes; the database takes a comment on a"
                  " post or on a drawing, never both or neither",
                  up1.returncode == 0 and up2.returncode == 0
                  and filled == [("C1", 10, None, 1), ("C2", 10, None, 1)]
                  and took == {"both": False, "neither": False, "a drawing": True},
                  f"up {up1.returncode}/{up2.returncode} {up2.stderr.strip().splitlines()[-1:] if up2.returncode else ''};"
                  f" rows {filled}; taken {took}")
            down = chain("downgrade", BEFORE)
            kept = at("select public_id from social_comments order by id")
            notnull = {r[1]: r[3] for r in at("pragma table_info(social_comments)")}
            check("taken back down, the chain deletes the comments on drawings (there is no post for them to be on) and"
                  " keeps every comment on a post, post_id NOT NULL again",
                  down.returncode == 0 and kept == [("C1",), ("C2",)] and notnull.get("post_id") == 1
                  and "drawing_id" not in notnull and "owner_id" not in notnull,
                  f"down {down.returncode} {down.stderr.strip().splitlines()[-1:] if down.returncode else ''};"
                  f" kept {kept}; columns {notnull}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(27, exc)

    # ------------------------------------------------------------------ 28
    if part(28, "a drawing's comments: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            sid = make_drawing(juno, "Section 28, a drawing", seed=281)
            t28 = said_on(theo, sid, "That wave is so good.")
            said_on(juno, sid, "Thank you!", answer_to=t28)
            said_on(mira, sid, "My cat would wave like that")
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, mira, screen=screen, scheme=scheme)
                    open_drawing(cpg, sid)
                    cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    cpg.wait_for_timeout(300)
                    seen[(screen, scheme, "comments")] = cpg.evaluate(READ, "#comments")
                    answer_box(cpg, t28)
                    seen[(screen, scheme, "answering")] = cpg.evaluate(READ, "#comments, #commentBoxSheet")
                    cpg.keyboard.press("Escape")
                    cpg.wait_for_function(GONE, timeout=8000)
                    cpg.wait_for_timeout(200)
                    cpg.click(f"#c-{t28} > .cm-main [data-cm-menu]")
                    cpg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
                    cpg.wait_for_timeout(450)
                    seen[(screen, scheme, "⋯")] = cpg.evaluate(READ, "#commentSheet")
                    cpg.click("#commentSheet [data-cm-act=report]")
                    cpg.wait_for_function(OPEN, arg="commentReportSheet", timeout=10000)
                    cpg.wait_for_timeout(450)
                    seen[(screen, scheme, "report")] = cpg.evaluate(READ, "#commentReportSheet")
                    close_ctx(cctx, cpg)
                    nctx, npg = browser_as(b, None, screen=screen, scheme=scheme)
                    open_drawing(npg, sid)
                    npg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    npg.wait_for_timeout(300)
                    seen[(screen, scheme, "signed out")] = npg.evaluate(READ, "#comments")
                    npg.click(".cm-say")
                    npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000)
                    npg.wait_for_timeout(450)
                    seen[(screen, scheme, "say something?")] = npg.evaluate(READ, "#commentOutSheet")
                    close_ctx(nctx, npg)
            low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
            small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
            fields = [(k, v["fields"]) for k, v in seen.items() if v["fields"]]
            lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
            musts = {"comments": ("Comments", "Theo Lind", "That wave is so good.", "Answer"), "answering": ("Post",),
                     "signed out": ("Comments", "Theo Lind"), "say something?": ("Say something?", "Not now", "Sign in"),
                     "⋯": ("Report comment",), "report": ("Report this comment",)}
            missing = [(" ".join(k), w) for k, v in seen.items() for w in musts.get(k[2], ())
                       if not any(x == w or (len(w) > 3 and x.startswith(w[:24])) for x in v["words"])]
            check("every word in a drawing's comments (a comment, an answer, the box answering, the count, Answer, \"Say something?\"),"
                  " a comment's ⋯ and its report reads at 4.5:1 or more on what is painted behind it, every control is"
                  " 44px or more each way, every text field 16px: phone and desk, light and dark",
                  not low and not small and not fields and not missing and all(v["read"] >= 1 for v in seen.values()),
                  f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]};"
                  f" small: {small[:3]}; fields: {fields[:3]}; not read: {missing[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(28, exc)

    # ------------------------------------------------------------------ 29
    # THE COMMENT BOX IS AN ICON (the owner, Nov 13: "The comment needs to be an
    # icon not a card. It takes up too much room sitting there", "Yes to all").
    if part(29, "the icon at the heading's end, the box folded away behind it; who is offered it"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 29, a snail", seed=291)
            said(theo, post, "Section 29, so there is a list")
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, theo, screen=screen, scheme=scheme)
                    open_post(cpg, post)
                    cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
                    cpg.wait_for_timeout(300)
                    got = {"icon": cpg.evaluate(ICON), "box": cpg.evaluate(BOX)}
                    got["focusable"] = cpg.evaluate("""() => { const w = document.querySelector('[data-cm-words]'); w.focus();
                      const f = document.activeElement === w; w.blur(); return f; }""")
                    got["mark"] = icon_mark(cpg)
                    if screen == "desk":            # lit while its box is open: white on the action purple
                        _, err = steps(lambda: open_box(cpg))
                        got["lit"] = icon_mark(cpg) if err is None else {"k": 0, "stopped": err}
                        got["lit_ground"] = cpg.evaluate("() => getComputedStyle(document.querySelector('.cm-say')).backgroundColor")
                    seen[(screen, scheme)] = got
                    close_ctx(cctx, cpg)
            ok_place = all(v["icon"] and v["icon"]["name"] == "Say something" and v["icon"]["tip"] == "Say something"
                           and v["icon"]["w"] == 44 and v["icon"]["h"] == 44 and v["icon"]["round"] == "999px"
                           and abs(v["icon"]["right"]) <= 0.5 and abs(v["icon"]["centre"]) <= 0.5 and v["icon"]["lands"]
                           and v["icon"]["head"] == v["icon"]["line"] == 29 and v["icon"]["gap"] == 10 and v["icon"]["plus"] == 3
                           for v in seen.values())
            check("the icon at the end of the Comments heading: a round 44px button, a bubble with a plus, named \"Say"
                  " something\" (its tip too), every tap point on it landing on it; the heading keeps its 29px (the icon"
                  " reaches into the room round it) and the comments start 10px under it: phone and desk, light and dark",
                  ok_place, "; ".join(f"{' '.join(k)}: {v['icon']}" for k, v in seen.items())[:900])
            ok_fold = all(v["box"] and v["box"]["open"] is None and v["icon"]["fold"]["h"] == 0
                          and v["icon"]["fold"]["seen"] == "hidden" and not v["icon"]["fold"]["laid"] and not v["focusable"]
                          and v["icon"]["expanded"] == "false" for v in seen.values())
            check("the box is folded away until asked for: no room under the heading, unseen, not laid out at all (so no"
                  " reader takes its words for shown words), and nothing in it takes focus",
                  ok_fold, "; ".join(f"{' '.join(k)}: box {v['box'] and v['box']['open']}, fold {v['icon']['fold']},"
                                     f" focusable {v['focusable']}" for k, v in seen.items()))
            ok_mark = all(v["mark"]["k"] >= 3 for v in seen.values()) and all(v["lit"]["k"] >= 3 and v["lit_ground"] in (
                "rgb(109, 76, 240)",) for k, v in seen.items() if k[0] == "desk")
            check("its line reads at 3:1 or more on its lilac, off the painted pixels, light and dark; lit while its box is"
                  " open, white on the action purple",
                  ok_mark, "; ".join(f"{' '.join(k)}: {v['mark']['k']}" + (f", lit {v['lit']['k']} on {v.get('lit_ground')}"
                                                                          if k[0] == 'desk' else '') for k, v in seen.items()))
            # Who is offered it: nobody who may not comment, as the box was not shown to them.
            zed = someone(b, "zed", "Zed Okoro")
            db_write("update social_people set taken_down_at = datetime('now') where handle_key = 'zed'")
            open_post(zed.pg, post)
            zed_icon = zed.pg.evaluate("() => [!!document.querySelector('.cm-say'), !!document.querySelector('[data-cm-first]')]")
            db_write("update social_people set taken_down_at = null where handle_key = 'zed'")
            db_write("update social_posts set taken_down_at = datetime('now') where public_id = ?", (post,))
            open_post(juno.pg, post)
            maker = juno.pg.evaluate("() => [!!document.querySelector('.cm-say'), !!document.querySelector('[data-cm-box]')]")
            db_write("update social_posts set taken_down_at = null where public_id = ?", (post,))
            check("nobody who may not comment is offered it: somebody taken down, or the maker of a post taken down (they"
                  " read its comments, with the note, and no box)",
                  zed_icon == [False, False] and maker == [False, False], f"taken down {zed_icon}; maker {maker}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(29, exc)

    # ------------------------------------------------------------------ 30
    if part(30, "a phone: the box rises on Make's sheet, ready; it goes kindly and keeps the words"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 30, a snail", seed=301)
            said(theo, post, "Section 30, the page under the sheet")
            pctx, ppg = browser_as(b, theo)
            ppg.add_init_script(KEYBOARD)
            open_post(ppg, post)
            ppg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
            ppg.wait_for_timeout(300)
            rise = ppg.evaluate(FRAMES, ["document.querySelector('.cm-say').click()",
                                         ["#commentBoxSheet .make-sheet", "[data-cm-list] > .cm .cm-name", "#commentsTitle"],
                                         ["#commentBoxSheet .make-scrim"], 700])
            up = ppg.evaluate(BOX)
            inert = ppg.evaluate("() => ['body > .top', 'body > .nav', '#main'].map(s => document.querySelector(s).hasAttribute('inert'))")
            g_up = glided(track(rise, 0))
            dim = fades_of(rise, 0)
            check("a tap on the icon raises Make's own sheet from the bottom, the box on it: \"Say something to Juno\", their"
                  " face, the field focused and ready (17px), Draw, Flip and Post; it glides up (read on every frame) while the"
                  " page dims, the page under it holding still and inert; the icon lit",
                  up and up["open"] == "sheet" and up["title"] == "Say something to Juno" and up["quote"] is None
                  and up["focus"] and up["font"] == 17 and up["chips"] == ["Draw", "Flip"] and up["post"] == "Post"
                  and up["placeholder"] == "Say something, or draw it…" and up["icon"] == "true"
                  and g_up["ok"] and 150 <= abs(g_up["way"]) and len([o for o in dim if 0.02 < o < 0.98]) >= 3
                  and still_(track(rise, 1)) and still_(track(rise, 2)) and all(inert),
                  f"box {up}; the rise {g_up}; the dimming {dim[:4]}..{dim[-1:]}; the page {glided(track(rise, 1))}; inert {inert}")
            # Put away three ways, each keeping what was typed.
            kept, downs = {}, {}
            for how in ("the dimmed page", "a drag down", "Esc"):
                act = {"the dimmed page": "document.querySelector('#commentBoxSheet .make-scrim').click()",
                       "Esc": "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"}.get(how)

                def put_away():        # a sheet that never goes is this row's red, never a stop
                    open_post(ppg, post)
                    open_box(ppg)
                    ppg.fill("[data-cm-words]", f"Typed, then {how}")
                    if act is None:
                        ppg.evaluate(SWIPE, [[12, 40, 90, 160, 220], 60])
                        down = None
                    else:
                        down = glided(track(ppg.evaluate(FRAMES, [act, ["#commentBoxSheet .make-sheet"], [], 600]), 0))
                    ppg.wait_for_function(GONE, timeout=8000)
                    ppg.wait_for_timeout(200)
                    gone = ppg.evaluate("() => ({ inert: !!document.querySelector('#main[inert]'), focus: document.activeElement.className })")
                    open_box(ppg)
                    words_ = ppg.evaluate(BOX)["words"]
                    ppg.keyboard.press("Escape")
                    ppg.wait_for_function(GONE, timeout=8000)
                    return {"words": words_, "gone": gone, "down": down}

                got_, err = steps(put_away)
                got_ = got_ or {"words": None, "gone": {"inert": True, "focus": ""}, "down": {"ok": False}}
                downs[how] = got_.pop("down")
                kept[how] = dict(got_, stopped=err)
            check("a tap on the dimmed page, a drag down or Esc puts it away (gliding down, read on every frame), focus back on"
                  " the icon and the page no longer inert; open it again and what was typed is there",
                  all(v["stopped"] is None and v["words"] == f"Typed, then {k}" and not v["gone"]["inert"]
                      and v["gone"]["focus"].startswith("icon-btn cm-say") for k, v in kept.items())
                  and all(g is None or g["ok"] for g in downs.values()),
                  f"{kept}; going down {downs}")
            # ON A PHONE'S KEYBOARD it rides above it (stood in: this box has no phone keyboard).
            open_post(ppg, post)
            open_box(ppg)
            ppg.evaluate("() => window.__keyboard(336)")
            ppg.wait_for_timeout(500)
            on_kb = ppg.evaluate("""() => { const s = document.querySelector('#commentBoxSheet .make-sheet').getBoundingClientRect(),
              w = document.querySelector('[data-cm-words]').getBoundingClientRect();
              return { bottom: Math.round(s.bottom), field: Math.round(w.bottom), floor: innerHeight - 336 }; }""")
            ppg.evaluate("() => window.__keyboard(0)")
            ppg.wait_for_timeout(500)
            off_kb = ppg.evaluate("() => Math.round(document.querySelector('#commentBoxSheet .make-sheet').getBoundingClientRect().bottom)")
            ppg.evaluate("() => window.__keyboard(300, 2)")
            ppg.wait_for_timeout(500)
            zoomed = ppg.evaluate("() => Math.round(document.querySelector('#commentBoxSheet .make-sheet').getBoundingClientRect().bottom)")
            ppg.evaluate("() => window.__keyboard(0)")
            close_ctx(pctx, ppg)
            check("on a phone's keyboard the sheet rides above it, its field in view, and goes back down with it; a pinch's zoom"
                  " is no keyboard (a stand-in visual viewport: this box has no phone keyboard)",
                  abs(on_kb["bottom"] - on_kb["floor"]) <= 1 and on_kb["field"] < on_kb["floor"] and off_kb == 874 and zoomed == 874,
                  f"on a 336px keyboard {on_kb}; after {off_kb}; zoomed {zoomed}")
            # Draw over the sheet: the Pad rises above it and goes; the page behind stays inert under the sheet.
            dctx, dpg = browser_as(b, theo)
            open_post(dpg, post)

            def pad_over():
                open_box(dpg)
                dpg.click("[data-cm-open=pad]", timeout=8000)
                fr = editor_frame(dpg, "skribl-pad")
                if fr:
                    fr.click("#composeCloseBtn", timeout=8000)
                dpg.wait_for_timeout(800)
                return dpg.evaluate("""() => ({ sheet: document.getElementById('commentBoxSheet').classList.contains('is-open'),
                  inert: ['body > .top', 'body > .nav', '#main'].map(s => document.querySelector(s).hasAttribute('inert')),
                  pad: document.getElementById('commentPad').hidden, focus: document.activeElement.textContent.trim() })""")

            got, err = steps(pad_over)
            close_ctx(dctx, dpg)
            check("Draw on the sheet opens the Pad over it; closed, the sheet is still there with focus back on Draw, and the page"
                  " behind it is still inert (the editor gives back only what it made inert)",
                  err is None and got.get("sheet") and got.get("inert") == [True, True, True] and got.get("pad")
                  and got.get("focus") == "Draw", f"{got}; stopped {err}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(30, exc)

    # ------------------------------------------------------------------ 31
    if part(31, "a desk: the box glides open under the heading, the icon lit; it folds away kindly and keeps the words"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 31, a snail", seed=311)
            said(theo, post, "Section 31, the comment under the box")
            dctx, dpg = browser_as(b, theo, "desk")
            open_post(dpg, post)
            opened = dpg.evaluate(FRAMES, ["document.querySelector('.cm-say').click()",
                                           ["[data-cm-list] > .cm .cm-name", "#commentsTitle", ".post-page > .post-art"],
                                           ["[data-cm-box]"], 700])
            there = dpg.evaluate(BOX)
            g_open = glided(track(opened, 0))
            ops = fades_of(opened, 0)
            room = dpg.evaluate("() => Math.round(document.querySelector('[data-cm-fold]').getBoundingClientRect().height * 100) / 100")
            want = box_room(dpg)
            check("a click glides the box open under the heading: the comments under it slide down to make room (read on every"
                  " frame, 136px, or a line more where a wider font puts Post on the next) while the box fades in, nothing"
                  " above it moving; the field focused, the icon lit",
                  there and there["open"] == "home" and there["focus"] and there["icon"] == "true" and there["font"] == 17
                  and g_open["ok"] and abs(g_open["way"] - room) <= 1 and room == want
                  and len([o for o in ops if 0.02 < o < 0.98]) >= 3 and ops[-1] == 1
                  and still_(track(opened, 1)) and still_(track(opened, 2)),
                  f"box {there}; the room {room} (the box's {want}); the comments {g_open}; the fade {ops[:5]}..; the heading"
                  f" {glided(track(opened, 1))}")
            folds = {}
            for how in ("a second click", "Esc", "a press elsewhere"):
                act = {"a second click": "document.querySelector('.cm-say').click()",
                       "Esc": "document.querySelector('[data-cm-words]').focus();"
                              " document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))",
                       "a press elsewhere": "document.querySelector('.post-page > .post-meta').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))"}[how]

                def fold_away():       # a fold that never goes is this row's red, never a stop
                    open_post(dpg, post)
                    open_box(dpg)
                    dpg.fill("[data-cm-words]", f"Typed, then {how}")
                    room_ = box_room(dpg)
                    fr = dpg.evaluate(FRAMES, [act, ["[data-cm-list] > .cm .cm-name"], ["[data-cm-box]"], 600])
                    dpg.wait_for_function(GONE, timeout=8000)
                    after_ = dpg.evaluate("() => ({ icon: document.querySelector('.cm-say').getAttribute('aria-expanded'), focus: document.activeElement.className })")
                    open_box(dpg)
                    words_ = dpg.evaluate(BOX)["words"]
                    dpg.click(".cm-say")
                    dpg.wait_for_function(GONE, timeout=8000)
                    return {"g": glided(track(fr, 0)), "icon": after_["icon"], "focus": after_["focus"], "words": words_,
                            "room": room_}

                got_, err = steps(fold_away)
                folds[how] = dict(got_ or {"g": {"ok": False, "way": 0}, "icon": None, "focus": "", "words": None, "room": 136},
                                  stopped=err)
            check("a second click, Esc (focus back on the icon) or a press anywhere else folds it away, the comments sliding back"
                  " up (read on every frame) and the icon going out; open it again and what was typed is there",
                  all(v["stopped"] is None and v["g"]["ok"] and abs(v["g"]["way"] + v["room"]) <= 1 and v["icon"] == "false"
                      and v["words"] == f"Typed, then {k}" for k, v in folds.items())
                  and folds["Esc"]["focus"].startswith("icon-btn cm-say"),
                  f"{folds}")
            # Draw opens the Pad over the page with the box open; a press on the Pad's ground is not "elsewhere".
            def pad_kept():
                open_post(dpg, post)
                open_box(dpg)
                dpg.click("[data-cm-open=pad]", timeout=8000)
                fr = editor_frame(dpg, "skribl-pad")
                dpg.mouse.click(30, 400)                 # beside the Pad's card: puts the Pad away, the drawing kept in it
                dpg.wait_for_timeout(800)
                return {"frame": bool(fr), "box": dpg.evaluate(BOX)["open"], "pad": dpg.evaluate("() => document.getElementById('commentPad').hidden")}

            got, err = steps(pad_kept)
            close_ctx(dctx, dpg)
            check("a press beside the Pad (opened by Draw in the box) puts the Pad away and leaves the box open: the editor over"
                  " the page is not \"elsewhere\"",
                  err is None and got.get("frame") and got.get("box") == "home" and got.get("pad"), f"{got}; stopped {err}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(31, exc)

    # ------------------------------------------------------------------ 32
    if part(32, "Answer opens the same box: a phone's sheet says whom and what; a desk's opens under the conversation"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 32, a snail", seed=321)
            theo_c = said(theo, post, "Ha, I counted too.\nAll three on each side.")
            other = said(mira, post, "Section 32, another conversation")
            pg = mira.pg
            open_post(pg, post)
            went = pg.evaluate(ANSWER_AND_WATCH, theo_c)
            sheet = pg.evaluate(BOX)
            check("on a phone, Answer raises the sheet titled \"Answer Theo\", Theo's words in a line under it (in quotes, one"
                  " line), the field saying \"Answer Theo…\" and focused; the comment answered does not move, the sheet glides up",
                  sheet["open"] == "sheet" and sheet["title"] == "Answer Theo" and sheet["quote"] == "“Ha, I counted too. All three on each side.”"
                  and sheet["placeholder"] == "Answer Theo…" and sheet["label"] == "Answer Theo" and went["focus"]
                  and went["pressed"] == "true" and sheet["icon"] == "false"
                  and all(abs(f["dy"]) <= 0.5 for f in went["frames"]) and glided([f["sheet"] for f in went["frames"]])["ok"],
                  f"{sheet}; the comment {[f['dy'] for f in went['frames']][:3]}..; the sheet {glided([f['sheet'] for f in went['frames']])}")
            quote_line = pg.evaluate("""() => { const q = document.querySelector('[data-cm-quote]'), c = getComputedStyle(q);
              return { lines: Math.round(q.getBoundingClientRect().height / parseFloat(c.lineHeight)), wrap: c.whiteSpace, cut: c.textOverflow }; }""")
            pg.keyboard.press("Escape")
            pg.wait_for_function(GONE, timeout=8000)
            open_box(pg)
            home_again = pg.evaluate(BOX)
            pg.keyboard.press("Escape")
            pg.wait_for_function(GONE, timeout=8000)
            check("its words stay one line, cut short with an ellipsis when long; the icon opens it as \"Say something to Juno\""
                  " again, its field back to \"Say something, or draw it…\" and no quote",
                  quote_line == {"lines": 1, "wrap": "nowrap", "cut": "ellipsis"} and home_again["title"] == "Say something to Juno"
                  and home_again["quote"] is None and home_again["placeholder"] == "Say something, or draw it…",
                  f"quote {quote_line}; again {home_again}")
            # A desk: under the conversation, as today; open on the heading first, it folds there, then opens there.
            dctx, dpg = browser_as(b, mira, "desk")
            open_post(dpg, post)
            open_box(dpg)
            moved = dpg.evaluate(FRAMES, [f"document.querySelector('#c-{theo_c} > .cm-main [data-cm-answer]').click()",
                                          [f"#c-{theo_c} > .cm-main .cm-name", f"#c-{other} > .cm-main .cm-name"], ["[data-cm-box]"], 1300])
            under = dpg.evaluate(BOX)
            want = box_room(dpg)
            ops = fades_of(moved, 0)
            g_theo, g_other = glided(track(moved, 0)), glided(track(moved, 1))
            check("on a desk, Answer opens it under that conversation (\"Answer Theo…\"); open under the heading first, it folds"
                  " away there and then glides open under the conversation, every move a glide (read on every frame), the box"
                  " fading out and in",
                  under["open"] == "under" and under["under"] == theo_c and under["placeholder"] == "Answer Theo…" and under["focus"]
                  and g_theo["ok"] and abs(g_theo["way"] + want) <= 1 and (g_other["ok"] or still_(track(moved, 1)))
                  and min(ops) == 0 and ops[-1] == 1 and len([o for o in ops if 0.02 < o < 0.98]) >= 4,
                  f"{under}; Theo's {g_theo}; the next conversation {g_other}; the box {ops[:3]}..{min(ops)}..{ops[-1]}")
            again, err = steps(lambda: (dpg.click(f"#c-{theo_c} > .cm-main [data-cm-answer]"),
                                        dpg.wait_for_function(GONE, timeout=8000), dpg.evaluate(BOX))[-1])
            check("Answer again folds it away, home and unseen",
                  err is None and again["open"] is None and again["home"], f"{again}; stopped {err}")
            if err is not None:
                open_post(dpg, post)
            long_c = said(theo, post, "Section 32, a long thread")
            for k in range(7):
                said(juno if k % 2 else mira, post, f"Section 32, answer {k} in a long thread, long enough to take two lines",
                     answer_to=long_c)
            open_post(dpg, post)
            dpg.evaluate("(id) => { const r = document.getElementById('c-' + id).getBoundingClientRect(); window.scrollBy(0, r.top - innerHeight / 3); }", long_c)
            dpg.wait_for_timeout(300)
            far = dpg.evaluate(ANSWER_AND_WATCH, long_c)
            g = glide(far)
            close_ctx(dctx, dpg)
            check("on a desk, under a long thread below the screen, it opens there and the page glides down to it (several"
                  " frames, none carrying three quarters of the way), the comment not jumping as it opens",
                  steady(far) and g["way"] > 60, f"the move {far['now']}px; then {g}; in view {far['seen']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(32, exc)

    # ------------------------------------------------------------------ 33
    if part(33, "posted: the box goes as the comment comes, glowing a moment; on a desk in step"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            mira = someone(b, "mira", "Mira Okafor")
            post = make_post(juno, "Section 33, a snail", seed=331)
            said(theo, post, "Section 33, the comment that was first")
            got = {}
            for screen in ("phone", "desk"):
                cctx, cpg = browser_as(b, mira, screen)
                open_post(cpg, post)
                cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
                cpg.wait_for_timeout(300)
                open_box(cpg)
                cpg.fill("[data-cm-words]", f"Section 33 on a {screen}: her tail is a question mark. What is she asking?")
                w = cpg.evaluate(POSTED, [1800])
                cpg.wait_for_timeout(2200)
                got[screen] = {"w": w, "box": cpg.evaluate(BOX), "after": cpg.evaluate(SECTION),
                               "glow": cpg.evaluate("(id) => document.getElementById(id).classList.contains('is-landed')", w["id"])}
                close_ctx(cctx, cpg)
            ok, why_ = True, []
            for screen, v in got.items():
                w = v["w"]
                g_old, g_new = glided(w["old"]), glided(w["new"])
                want = {"posted, at the top": bool(w["id"]) and w["first"] == w["id"],
                        "counted": v["after"]["count"] in ("2", "3"),
                        "glowing in the tint": bool(w["glow"]) and w["glow"][0] and w["tint"] == TINT["light"],
                        "the tint fading": w["fade"] >= 10 and not v["glow"],
                        "fading in": len([o for o in w["ops"] if 0.02 < o < 0.98]) >= 3 and w["ops"][-1] == 1,
                        "the box gone and emptied": v["box"]["open"] is None and v["box"]["words"] == "",
                        "focus on the icon": w["focus"] == "icon-btn cm-say",
                        "what was under it, a glide": g_old["ok"],
                        "the box not changing on its way": not w["step"],
                        "Post says Posting": w["label"] == "Posting…" and not w["line"]}
                if screen == "desk":
                    want["in step, where the box was"] = (g_new["ok"] and abs(g_new["way"] + w["room"]) <= 1.5
                                                          and abs(w["new"][-1] - w["under_head"]) <= 1)
                else:
                    want["the sheet gliding down"] = glided(w["sheet"])["ok"] and still_(w["new"])
                ok = ok and all(want.values())
                why_.append(f"{screen}: not {[k for k, x in want.items() if not x]}; the old first {g_old}; the new {g_new}"
                            f" (the box's room {w['room']}); sheet {glided(w['sheet']) if w['sheet'] else None}; fade in"
                            f" {w['ops'][:4]}..{w['ops'][-1:]}; the tint {w['tint']}, fading {w['fade']} frames; Post said"
                            f" {w['label']!r}, a line {w['line']}, a step {w['step']}; box {v['box']['open']} {v['box']['words']!r};"
                            f" focus {w['focus']}")
            check("posted, the box goes (a phone's sheet glides down; a desk's fold folds away in step as the comment opens its"
                  " room where the box was) and the comment sits at the top, fading in and glowing in the landing's tint, which"
                  " fades; what was under it moves only as a glide (read on every frame); Post says \"Posting…\" meanwhile and no"
                  " line grows the box; the box is emptied once it has gone; focus on the icon",
                  ok, " | ".join(why_))
            # An answer posted on a desk: under its comment, the fold folding away there in step.
            dctx, dpg = browser_as(b, mira, "desk")
            open_post(dpg, post)
            top_c = db("select public_id from social_comments where words = 'Section 33, the comment that was first'")[0][0]
            answer_box(dpg, top_c)
            dpg.fill("[data-cm-words]", "Section 33, an answer from a desk")
            w = dpg.evaluate(POSTED, [1800])
            dpg.wait_for_timeout(600)
            sec = dpg.evaluate(SECTION)
            close_ctx(dctx, dpg)
            under = [a["words"] for a in next((c for c in sec["list"] if c["id"] == top_c), {"answers": []})["answers"]]
            check("an answer posted on a desk sits under its comment and glows; the fold folds away under the conversation and"
                  " goes home; focus on the new answer's Answer",
                  under[-1:] == ["Section 33, an answer from a desk"] and w["glow"][0] and w["focus"] == "cm-act",
                  f"under {under}; glow {w['glow'][:2]}; focus {w['focus']}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(33, exc)

    # ------------------------------------------------------------------ 34
    if part(34, "signed out the icon raises Say something?; signed in it comes back open; Say the first thing at none"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 34, a snail", seed=341)
            said(theo, post, "Section 34, readable signed out")
            nctx, npg = browser_as(b, None)
            open_post(npg, post)
            icon = npg.evaluate(ICON)

            def out_sheet():          # no icon, or no sheet, is this row's red, never a stop
                npg.click(".cm-say", timeout=8000)
                npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000)
                npg.wait_for_timeout(450)
                o = npg.evaluate(OUT_SHEET)
                npg.click("#commentOutSheet .post-sheet-acts [data-make-close]", timeout=8000)
                npg.wait_for_timeout(500)
                return o, npg.evaluate("() => ({ open: document.getElementById('commentOutSheet').classList.contains('is-open'), focus: document.activeElement.className })")

            got_, err34 = steps(out_sheet)
            out, shut = got_ or ({"open": False, "title": None, "lede": None, "acts": [], "path": None, "next": None,
                                  "focus": None, "old": None}, {"open": True, "focus": ""})
            close_ctx(nctx, npg)
            check("signed out, the icon is there all the same (\"Say something\", a dialog, and unlit while it is up: no box is"
                  " open); a tap raises a small sheet like the heart's: \"Say something?\", \"Sign in, and you can answer Juno in words or with a drawing.\", Not now and"
                  " Sign in, which comes back to this post with the box open (#say); Not now puts it away; no \"Sign in to"
                  " answer\" anywhere",
                  icon and icon["name"] == "Say something" and icon["popup"] == "dialog" and icon["controls"] == "commentOutSheet"
                  and out["open"] and out["title"] == "Say something?"
                  and out["lede"] == "Sign in, and you can answer Juno in words or with a drawing."
                  and out["acts"] == ["Not now", "Sign in"] and out["path"] == "/social/signin"
                  and out["next"] == f"/social/p/{post}#say" and out["focus"] == "Not now" and not out["old"]
                  and out["lit"] is False and not shut["open"] and shut["focus"].startswith("icon-btn cm-say"),
                  f"icon {icon and {k: icon[k] for k in ('name', 'popup', 'controls')}}; sheet {out}; after Not now {shut};"
                  f" stopped {err34}")
            # Signed in from there: back on the post with the box open, nothing posted, the address without #say.
            before = db("select count(*) from social_comments")[0][0]
            back = {}
            for screen in ("phone", "desk"):
                cctx, cpg = browser_as(b, theo, screen)
                cpg.goto(BASE + "/social/signin?next=" + urllib.parse.quote(f"/social/p/{post}#say", safe="/"))
                cpg.wait_for_function("() => document.readyState === 'complete' && !!document.querySelector('[data-comments]')", timeout=15000)
                _, err = steps(lambda: cpg.wait_for_function(BOX_STILL, timeout=8000))
                back[screen] = {"box": cpg.evaluate(BOX), "url": cpg.evaluate("() => location.pathname + location.hash"), "stopped": err}
                close_ctx(cctx, cpg)
            check("signed in from it, the post comes back with the box open and ready (a phone's sheet, a desk's fold), its field"
                  " focused, nothing posted, and the address without its #say",
                  all(v["box"]["open"] == ("sheet" if k == "phone" else "home") and v["box"]["focus"] and v["url"] == f"/social/p/{post}"
                      for k, v in back.items()) and db("select count(*) from social_comments")[0][0] == before,
                  f"{back}; comments {before} -> {db('select count(*) from social_comments')[0][0]}")
            # At none: "Say the first thing" where the comments will be.
            quiet = make_post(juno, "Section 34, nobody has said anything yet", seed=342)
            got = {}
            for screen in ("phone", "desk"):
                cctx, cpg = browser_as(b, theo, screen)
                open_post(cpg, quiet)
                cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
                cpg.wait_for_timeout(300)
                line = cpg.evaluate(FIRST_LINE)
                fr = cpg.evaluate(FRAMES, ["const f = document.querySelector('[data-cm-first]'); if (f) f.click();",
                                           [".more-from"], [".cm-first"], 700])
                _, err = steps(lambda: cpg.wait_for_function(BOX_STILL, timeout=8000))
                opened = cpg.evaluate(BOX)
                line_open = cpg.evaluate(FIRST_LINE)
                got[screen] = {"line": line, "opened": opened, "line_open": line_open, "fr": fr, "stopped": err,
                               "room": box_room(cpg)}
                close_ctx(cctx, cpg)
            d = got["desk"]
            check("with nothing said yet, \"Say the first thing\" stands where the comments will be: the small violet words (16px,"
                  " 600, Sign in's ink), 44px tall, 10px under the heading; a tap opens the box (a phone's sheet; a desk's fold,"
                  " where the words fold away in step as the box opens in their place)",
                  all(v["stopped"] is None and v["line"] and v["line"]["words"] == "Say the first thing" and v["line"]["h"] == 44 and v["line"]["open"]
                      and v["line"]["gap"] == 10 and v["line"]["size"] == 16 and v["line"]["weight"] == "600" and v["line"]["lands"]
                      and v["line"]["ink"] in ("rgb(76, 49, 196)",) for v in got.values())
                  and got["phone"]["opened"]["open"] == "sheet" and got["phone"]["line_open"]["open"]
                  and d["opened"]["open"] == "home" and not d["line_open"]["open"] and d["line_open"]["seen"] == "hidden"
                  and glided(track(d["fr"], 0), d["room"] - 52)["ok"] and still_(track(got["phone"]["fr"], 0)),
                  f"phone {got['phone']['line']} -> {got['phone']['opened']['open']}; desk {d['line']} -> {d['opened']['open']},"
                  f" the line {d['line_open']}; under it on a desk {glided(track(d['fr'], 0))}")
            dctx, dpg = browser_as(b, theo, "desk")
            open_post(dpg, quiet)

            def first_and_last():      # a step that cannot go on is this row's red, never a stop
                dpg.click(".cm-say")    # the icon, as "Say the first thing" may not be there to press
                dpg.wait_for_function(BOX_STILL, timeout=8000)
                dpg.fill("[data-cm-words]", "Section 34, the first thing")
                w = dpg.evaluate(POSTED, [900])
                dpg.wait_for_timeout(400)
                after_first = dpg.evaluate(FIRST_LINE)
                dpg.evaluate("(id) => document.querySelector('#' + id + ' > .cm-main [data-cm-menu]').click()", w["id"])
                dpg.wait_for_function(OPEN, arg="commentSheet", timeout=10000)
                dpg.wait_for_timeout(450)
                back_fr = dpg.evaluate(FRAMES, ["document.querySelector('#commentSheet [data-cm-act=delete]').click()",
                                                [".more-from"], [".cm-first"], 1400])
                return w, after_first, back_fr, dpg.evaluate(FIRST_LINE)

            got_, err = steps(first_and_last)
            w, after_first, back_fr, again_line = got_ if err is None else ({"id": None}, None, [], None)
            close_ctx(dctx, dpg)
            check("the first comment takes its place (the line gone, folded away); the last one deleted, it comes back, fading in"
                  " as its room opens",
                  err is None and w["id"] and after_first and not after_first["open"] and after_first["seen"] == "hidden"
                  and again_line and again_line["open"] and fades_of(back_fr, 0)[-1:] == [1]
                  and len([o for o in fades_of(back_fr, 0) if 0.02 < o < 0.98]) >= 2,
                  f"posted {w['id']}; the line {after_first}; after the delete {again_line}; its fade"
                  f" {fades_of(back_fr, 0)[-6:] if back_fr else None}; stopped {err}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(34, exc)

    # ------------------------------------------------------------------ 35
    if part(35, "under Reduce Motion the sheet fades where it sits; a desk's box is put in place and fades"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 35, a snail", seed=351)
            said(theo, post, "Section 35, a comment")
            pctx, ppg = browser_as(b, theo, reduced=True)
            open_post(ppg, post)
            ppg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
            ppg.wait_for_timeout(300)
            up = ppg.evaluate(FRAMES, ["document.querySelector('.cm-say').click()", ["#commentBoxSheet .make-sheet"], ["#commentBoxSheet .make-sheet"], 600])
            ppg.wait_for_function(BOX_STILL, timeout=8000)
            ppg.fill("[data-cm-words]", "Section 35, posted under Reduce Motion")
            pw = ppg.evaluate(POSTED, [900])
            close_ctx(pctx, ppg)
            dctx, dpg = browser_as(b, theo, "desk", reduced=True)
            open_post(dpg, post)
            dn = dpg.evaluate(FRAMES, ["document.querySelector('.cm-say').click()", ["[data-cm-list] > .cm .cm-name"], ["[data-cm-box]"], 600])
            dpg.wait_for_function(BOX_STILL, timeout=8000)
            room35 = box_room(dpg)
            dpg.fill("[data-cm-words]", "Section 35, posted on a desk under Reduce Motion")
            dw = dpg.evaluate(POSTED, [900])
            close_ctx(dctx, dpg)
            sheet_tops, sheet_ops = track(up, 0), fades_of(up, 0)
            box_ops = fades_of(dn, 0)
            moves = [abs(y - x) for x, y in zip(track(dn, 0), track(dn, 0)[1:]) if abs(y - x) > 0.3]
            check("under Reduce Motion nothing glides: a phone's sheet fades in where it sits (0px moved), a desk's box is put in"
                  " place (one step) and fades in; a posted comment is put in place and fades in, what was under it moving in"
                  " one step",
                  still_(sheet_tops) and len([o for o in sheet_ops if 0.02 < o < 0.98]) >= 2 and sheet_ops[-1] == 1
                  and len(moves) == 1 and abs(moves[0] - room35) <= 1 and len([o for o in box_ops if 0.02 < o < 0.98]) >= 2
                  and still_(pw["new"]) and len([o for o in pw["ops"] if 0.02 < o < 0.98]) >= 2
                  and still_(dw["new"]) and len([o for o in dw["ops"] if 0.02 < o < 0.98]) >= 2
                  and one_step(pw["old"]) and one_step(dw["old"]),
                  f"the sheet's top {sorted(set(sheet_tops))[:3]}, its fade {sheet_ops[:4]}; the desk's moves {moves}, the box's fade"
                  f" {box_ops[:4]}; posted on a phone {pw['new'][:3]} {pw['ops'][:4]}, what was under it {moved_by(pw['old'])};"
                  f" on a desk {dw['new'][:3]} {dw['ops'][:4]}, what was under it {moved_by(dw['old'])}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(35, exc)

    # ------------------------------------------------------------------ 36
    if part(36, "a drawing's own page: the same icon, sheet, fold and posting; signed out back to the drawing"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            sid = make_drawing(juno, "Section 36, a wave", seed=361)
            open_drawing(theo.pg, sid)
            first = theo.pg.evaluate(FIRST_LINE)
            icon = theo.pg.evaluate(ICON)
            open_box(theo.pg)
            sheet = theo.pg.evaluate(BOX)
            theo.pg.fill("[data-cm-words]", "Section 36, on the drawing")
            pw = theo.pg.evaluate(POSTED, [900])
            dctx, dpg = browser_as(b, theo, "desk")
            open_drawing(dpg, sid)
            opened = dpg.evaluate(FRAMES, ["document.querySelector('.cm-say').click()", ["[data-cm-list] > .cm .cm-name"], ["[data-cm-box]"], 700])
            fold = dpg.evaluate(BOX)
            close_ctx(dctx, dpg)
            nctx, npg = browser_as(b, None)
            open_drawing(npg, sid)
            npg.click(".cm-say")
            npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000)
            out = npg.evaluate(OUT_SHEET)
            close_ctx(nctx, npg)
            check("on a drawing's own page the same: \"Say the first thing\" at none, the icon, a phone's sheet (\"Say something to"
                  " Juno\"), posting (it glows at the top), a desk's fold gliding open; signed out, Sign in comes back to the"
                  " drawing with the box open",
                  first and first["words"] == "Say the first thing" and icon and icon["w"] == 44 and sheet["open"] == "sheet"
                  and sheet["title"] == "Say something to Juno" and pw["id"] and pw["glow"][0]
                  and fold["open"] == "home" and glided(track(opened, 0))["ok"]
                  and out["next"] == f"/social/b/{sid}#say" and out["lede"] == "Sign in, and you can answer Juno in words or with a drawing.",
                  f"first {first}; icon {icon and icon['w']}; sheet {sheet}; posted {pw['id']}; fold {fold['open']}"
                  f" {glided(track(opened, 0))}; signed out {out}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(36, exc)

    # ------------------------------------------------------------------ 37
    if part(37, "the new screens' words and marks: the sheet, Say something?, Say the first thing; 4.5:1, 44px, 16px"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 37, a snail", seed=371)
            t37 = said(theo, post, "That shell spiral is so good, and the long words under its title are cut short nicely")
            quiet = make_post(juno, "Section 37, nothing yet", seed=372)
            seen = {}
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    cctx, cpg = browser_as(b, juno, screen=screen, scheme=scheme)
                    open_post(cpg, post)
                    answer_box(cpg, t37)
                    seen[(screen, scheme, "answering")] = cpg.evaluate(READ, "#comments, #commentBoxSheet")
                    cpg.keyboard.press("Escape")
                    cpg.wait_for_function(GONE, timeout=8000)
                    open_box(cpg)
                    seen[(screen, scheme, "the box")] = cpg.evaluate(READ, "#comments, #commentBoxSheet")
                    open_post(cpg, quiet)
                    cpg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'center' })")
                    cpg.wait_for_timeout(300)
                    seen[(screen, scheme, "none yet")] = cpg.evaluate(READ, "#comments")
                    close_ctx(cctx, cpg)
                    nctx, npg = browser_as(b, None, screen=screen, scheme=scheme)
                    open_post(npg, post)
                    npg.click(".cm-say")
                    npg.wait_for_function(OPEN, arg="commentOutSheet", timeout=8000)
                    npg.wait_for_timeout(450)
                    seen[(screen, scheme, "say something?")] = npg.evaluate(READ, "#commentOutSheet")
                    close_ctx(nctx, npg)
            low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
            small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
            fields = [(k, v["fields"]) for k, v in seen.items() if v["fields"]]
            lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
            musts = {"answering": ("Post",), "the box": ("Draw", "Flip", "Post"),
                     "none yet": ("Comments", "Say the first thing"),
                     "say something?": ("Say something?", "Sign in, and you can answer", "Not now", "Sign in")}
            phone_only = {"answering": ("Answer Theo", "“That shell spiral is so good"), "the box": ("Say something",)}
            missing = [(" ".join(k), w) for k, v in seen.items()
                       for w in musts.get(k[2], ()) + (phone_only.get(k[2], ()) if k[0] == "phone" else ())
                       if not any(x == w or (len(w) > 3 and x.startswith(w[:24])) for x in v["words"])]
            check("every word on the new screens (the sheet's title and the words it answers, the box on it and in place, \"Say"
                  " the first thing\", \"Say something?\" and its words and buttons) reads at 4.5:1 or more on what is painted"
                  " behind it, every control is 44px or more each way, every text field 16px: phone and desk, light and dark",
                  not low and not small and not fields and not missing and all(v["read"] >= 1 for v in seen.values()),
                  f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small: {small[:3]};"
                  f" fields: {fields[:3]}; not read: {missing[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(37, exc)

    # ------------------------------------------------------------------ 19
    if part(19, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                ERRS.extend(f"csp: {v}" for v in who.csp())
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(19, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
