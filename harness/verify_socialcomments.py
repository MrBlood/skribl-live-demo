"""Comments on the Skribl site (phase 2, comments; docs/SOCIAL-SITE.md "Built:
phase 2, comments"), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. THE SECTION: a post's page says "Comments" and how many; the box on top
     for somebody signed in (their face, "Say something, or draw it…", Draw,
     Flip, Post); signed out, the comments are readable and "Sign in to
     answer" stands in the box's place; Post with nothing written or drawn
     says so and sends nothing.
  2. COMMENTING, NEWEST FIRST: the box sends the words (tidied, as a post's);
     the new comment fades in at the top, the count with it; its time is
     short ("now", "40m"); its row names the post and the person.
  3. ANSWERS, ONE LEVEL DEEP: Answer brings the box under the comment
     ("Answer Theo…"), the comment keeping its place on the screen and the
     box fading in; answers sit under it oldest first; an answer to an answer
     sits under the same comment; the box goes back once posted, on Answer
     again, and on Esc.
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
     them; none said at none.
 12. ON A DESK: the comments beside the drawing, under Share.
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
 19. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALCOMMENTS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Comments at /social".
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


# The section as the page shows it: each comment, and the answers under it.
SECTION = """() => { const one = li => ({ id: li.dataset.comment, name: li.querySelector(':scope > .cm-main .cm-name').textContent,
    when: li.querySelector(':scope > .cm-main .cm-when').textContent,
    words: (li.querySelector(':scope > .cm-main .cm-words') || {}).textContent || '',
    down: (li.querySelector(':scope > .cm-main .cm-down') || {}).textContent || null,
    answer: !!li.querySelector(':scope > .cm-main [data-cm-answer]') });
  return { count: (() => { const c = document.querySelector('[data-cm-count]'); return c && !c.hidden ? c.textContent : null; })(),
    list: [...document.querySelectorAll('[data-cm-list] > .cm')].map(li => Object.assign(one(li),
      { answers: [...li.querySelectorAll(':scope > .cm-answers > .cm')].map(one) })) }; }"""
BOX = """() => { const b = document.querySelector('[data-cm-box]'); if (!b) return null;
  const w = b.querySelector('[data-cm-words]'); const p = b.parentElement;
  return { placeholder: w.placeholder, label: b.querySelector('[data-cm-label]').textContent,
    under: p.classList.contains('cm') ? p.dataset.comment : null,
    home: !!b.previousElementSibling && b.previousElementSibling.id === 'commentsTitle',
    face: !!b.querySelector('.face-ring'), post: (b.querySelector('[data-cm-post]') || {}).textContent || null,
    chips: [...b.querySelectorAll('.chip')].filter(c => c.getClientRects().length).map(c => c.textContent.trim()),
    font: parseFloat(getComputedStyle(w).fontSize) }; }"""
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

# Press a comment's Answer, and read on every frame where the comment is on the
# screen (against where it was) and the box's opacity: did anything jump?
ANSWER_AND_WATCH = """async (id) => {
  const li = document.getElementById('c-' + id), box = document.querySelector('[data-cm-box]');
  const btn = li.querySelector(':scope > .cm-main [data-cm-answer]');
  const top0 = li.getBoundingClientRect().top, y0 = scrollY;
  btn.click();
  const now = li.getBoundingClientRect().top - top0;
  const t0 = performance.now(), frames = [];
  await new Promise(res => { const step = () => {
    frames.push({ dy: Math.round((li.getBoundingClientRect().top - top0) * 10) / 10,
                  op: Math.round(+getComputedStyle(box).opacity * 100) / 100 });
    if (performance.now() - t0 < 600) requestAnimationFrame(step); else res(); };
    requestAnimationFrame(step); });
  const bar = document.querySelector('body > .nav').getBoundingClientRect();
  const floor = bar.top > innerHeight / 2 ? bar.top : innerHeight, br = box.getBoundingClientRect();
  return { now: Math.round(now * 10) / 10, frames, scrolled: Math.round(scrollY - y0),
           focus: document.activeElement === box.querySelector('[data-cm-words]'),
           pressed: btn.getAttribute('aria-expanded'), seen: br.top >= 0 && br.bottom <= floor }; }"""


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


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the section: Comments and how many, the box on top, signed out readable"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 1, a snail", seed=11)
            pg = theo.pg
            sent = []
            pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and "/comments" in r.url else None)
            open_post(pg, post)
            empty = pg.evaluate(SECTION)
            box = pg.evaluate(BOX)
            soon = pg.evaluate("() => !!document.querySelector('.comments-soon')")
            title = pg.evaluate("() => document.getElementById('commentsTitle').innerText.replace(/\\s+/g, ' ').trim()")
            nothing = blank = None
            if box:                     # no box is the first row's red, never a stop
                pg.click("[data-cm-post]")
                pg.wait_for_timeout(300)
                nothing = pg.evaluate("() => document.querySelector('[data-cm-say]').textContent")
                pg.fill("[data-cm-words]", "   \n  ")
                pg.click("[data-cm-post]")
                pg.wait_for_timeout(300)
                blank = pg.evaluate("() => document.querySelector('[data-cm-say]').textContent")
            check("a post's page says Comments, with no number at none; the box on top for somebody signed in: their"
                  " face, the words' field (17px), \"Say something, or draw it…\", Draw, Flip and Post; no"
                  " \"Comments open soon\"",
                  empty == {"count": None, "list": []} and title == "Comments" and not soon
                  and box is not None and box["home"] and box["face"]
                  and box["placeholder"] == "Say something, or draw it…" and box["chips"] == ["Draw", "Flip"]
                  and box["post"] == "Post" and box["font"] >= 16,
                  f"section {empty}; title {title!r}; open soon {soon}; box {box}")
            check("Post with nothing written or drawn (or only spaces) says so and sends nothing",
                  nothing == "Say something or draw something first, then Post." and blank == nothing and not sent,
                  f"said {nothing!r} / {blank!r}; sent {len(sent)}")
            said(theo, post, "Read by somebody signed out")
            nctx, npg = browser_as(b, None)
            open_post(npg, post)
            out = {"section": npg.evaluate(SECTION), "box": npg.evaluate(BOX),
                   "link": npg.evaluate("() => { const a = document.querySelector('.cm-signin a'); return a ? [a.textContent, new URL(a.href).pathname + new URL(a.href).search] : null; }")}
            close_ctx(nctx, npg)
            want_link = ["Sign in to answer", "/social/signin?next=/social/p/" + post]
            check("signed out, the comments are readable, with no box and no Answer: \"Sign in to answer\" in the box's"
                  " place, back to the post once signed in",
                  out["box"] is None and out["section"]["count"] == "1"
                  and [(c["name"], c["words"], c["answer"]) for c in out["section"]["list"]]
                  == [("Theo Lind", "Read by somebody signed out", False)]
                  and out["link"] == want_link,
                  f"{out}; want link {want_link}")
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
            pg.fill("[data-cm-words]", "  That shell spiral   is so good.\n\n\n\nWatching it go round is the best part.  ")
            theo_said = pg.evaluate(POST_AND_WATCH)
            after1 = pg.evaluate(SECTION)
            cleared = pg.evaluate("() => document.querySelector('[data-cm-words]').value")
            row = db("select c.words, c.parent_id, pe.handle, c.post_id from social_comments c join social_people pe"
                     " on pe.id = c.person_id where c.public_id = ?", (theo_said["id"] or "",))
            check("the box sends the words, tidied as a post's (spaces run together, blank lines to one); the comment"
                  " fades in at the top, said \"now\", the count 1, the box emptied; its row names the post and the person",
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
    if part(3, "answers, one level deep: Answer brings the box, nothing jumps"):
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
            check("Answer brings the box under the comment, after its answers, saying \"Answer Theo…\" (its label too),"
                  " the words' field focused; the comment keeps its place on the screen while the box moves (the page"
                  " scrolls by what moved above it), the box fades in where it lands, and nothing after jumps",
                  there["under"] == theo_c and there["placeholder"] == "Answer Theo…" and there["label"] == "Answer Theo"
                  and went["focus"] and went["pressed"] == "true" and steady(went)
                  and faded([f["op"] for f in went["frames"]]) >= 2 and went["frames"][-1]["op"] == 1,
                  f"box {there}; the move {went['now']}px, then {glide(went)}, in view {went['seen']}; faded over"
                  f" {faded([f['op'] for f in went['frames']])} frames; focus {went['focus']}")
            pg.fill("[data-cm-words]", "Same! I watched it three times.")
            mine = pg.evaluate(POST_AND_WATCH)
            pg.wait_for_timeout(400)
            back = pg.evaluate(BOX)
            sec = pg.evaluate(SECTION)
            theo_li = next((c for c in sec["list"] if c["id"] == theo_c), {"answers": []})
            # ...and as the server renders them, which the page's own insertion cannot show.
            open_post(pg, post)
            again = next((c for c in pg.evaluate(SECTION)["list"] if c["id"] == theo_c), {"answers": []})
            want = ["Thank you! It took me two tries to get the spiral right.", "Same! I watched it three times."]
            check("the answer sits under the comment, after the ones before it (oldest first, put in place and after a"
                  " reload), fading in; the box goes back on top, \"Say something, or draw it…\" again",
                  [a["words"] for a in theo_li["answers"]] == want and [a["words"] for a in again["answers"]] == want
                  and faded(mine["ops"]) >= 2 and back["home"] and back["placeholder"] == "Say something, or draw it…"
                  and back["label"] == "Say something",
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
            check("answering an answer: the box comes under the same comment, saying \"Answer Mira…\", and the new answer"
                  " sits under that comment, last, its row's parent the comment, not the answer",
                  jbox["under"] == theo_c and jbox["placeholder"] == "Answer Mira…" and steady(jwent)
                  and len(rows) == 1 and rows[0][1] == theo_c and under[-1] == "Three times! Thank you, Mira."
                  and len(under) == 3,
                  f"box {jbox}; rows {rows}; under Theo's {[u[:20] for u in under]}; the move {jwent['now']}px,"
                  f" then {glide(jwent)}")
            open_post(pg, post)
            pg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", juno_a)
            pg.click(f"#c-{juno_a} > .cm-main [data-cm-answer]")
            pg.wait_for_timeout(300)
            toggled_in = pg.evaluate(BOX)
            pg.click(f"#c-{juno_a} > .cm-main [data-cm-answer]")
            pg.wait_for_timeout(300)
            toggled_out = pg.evaluate(BOX)
            pg.click(f"#c-{juno_a} > .cm-main [data-cm-answer]")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            escaped = pg.evaluate(BOX)
            check("the box goes back on top when Answer is pressed again, and on Esc",
                  toggled_in["under"] == theo_c and toggled_in["placeholder"] == "Answer Juno…"
                  and toggled_out["home"] and toggled_out["placeholder"] == "Say something, or draw it…"
                  and escaped["home"] and escaped["placeholder"] == "Say something, or draw it…",
                  f"in {toggled_in}; again {toggled_out}; Esc {escaped}")
            long_c = said(theo, post, "Section 3, a long thread")
            for k in range(7):
                said(juno if k % 2 else mira, post, f"Section 3, answer {k} in a long thread, long enough to take two lines",
                     answer_to=long_c)
            open_post(pg, post)
            pg.evaluate("(id) => { const r = document.getElementById('c-' + id).getBoundingClientRect();"
                        " window.scrollBy(0, r.top - innerHeight / 3); }", long_c)
            pg.wait_for_timeout(300)
            far = pg.evaluate(ANSWER_AND_WATCH, long_c)
            g = glide(far)
            check("under a long thread, where the box lands below what the screen shows, the page glides down to it (over"
                  " several frames, none carrying three quarters of the way) and leaves it in view above the bar; the"
                  " comment does not jump as the box moves",
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
            DELETE_AND_WATCH = """async ([id, act]) => {
              const li = document.getElementById('c-' + id);
              li.querySelector(':scope > .cm-main [data-cm-menu]').click();
              await new Promise(r => setTimeout(r, 450));
              document.querySelector('#commentSheet [data-cm-act=' + act + ']').click();
              const t0 = performance.now(), ops = [];
              await new Promise(res => { const step = () => { if (li.isConnected) ops.push(Math.round(+getComputedStyle(li).opacity * 100) / 100);
                if (!li.isConnected || performance.now() - t0 > 8000) res(); else requestAnimationFrame(step); }; requestAnimationFrame(step); });
              return { gone: !li.isConnected, ops, count: (document.querySelector('[data-cm-count]') || {}).textContent }; }"""
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
    if part(11, "Home's card: how many comments beside the plays, a way to them"):
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
              const n = c.querySelector('.post-count'), pl = c.querySelector('.post-plays:not(.post-count)');
              if (!n) return { none: true };
              const r = n.getBoundingClientRect(), p = pl.getBoundingClientRect();
              return { label: n.getAttribute('aria-label'), text: n.textContent.trim(), icon: !!n.querySelector('svg'),
                       href: new URL(n.href).pathname + new URL(n.href).hash, beside: Math.round(r.left - p.right),
                       middle: Math.abs((r.top + r.height / 2) - (p.top + p.height / 2)) < 1, w: r.width, h: r.height }; }"""
            got = pg.evaluate(CARD, post)
            none = pg.evaluate(CARD, bare)
            check("Home's card says how many comments beside the plays (the comment icon and the number, \"3 comments\"),"
                  " a way to them on the post's page, 44px; a post with none says nothing",
                  got is not None and got.get("label") == "3 comments" and got.get("text") == "3" and got.get("icon")
                  and got.get("href") == f"/social/p/{post}#comments" and 10 <= got.get("beside", 0) <= 18
                  and got.get("middle") and got.get("w", 0) >= 44 and got.get("h", 0) >= 44 and none == {"none": True},
                  f"{got}; with none {none}")
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(11, exc)

    # ------------------------------------------------------------------ 12
    if part(12, "on a desk: the comments beside the drawing, under Share"):
        try:
            juno = someone(b, "juno", "Juno Park")
            theo = someone(b, "theo", "Theo Lind")
            post = make_post(juno, "Section 12, a snail", seed=121)
            said(theo, post, "Section 12, beside the drawing")
            dctx, dpg = browser_as(b, juno, "desk", "light")
            open_post(dpg, post)
            where = dpg.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
              const art = r('.post-art'), share = r('.post-actions'), sec = r('#comments'), box = r('[data-cm-box]');
              return { right: Math.round(sec.left - art.right), under: Math.round(sec.top - share.bottom),
                       left: Math.round(sec.left - share.left), width: Math.round(sec.width), box: Math.round(box.width),
                       onscreen: sec.top < innerHeight }; }""")
            close_ctx(dctx, dpg)
            check("on a desk the comments sit beside the drawing, under Share and Make your own, in the same column, the box"
                  " on top within reach",
                  where["right"] >= 24 and 0 < where["under"] <= 40 and where["left"] == 0 and where["width"] >= 300
                  and where["box"] == where["width"] and where["onscreen"],
                  f"{where}")
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
                    cpg.click(f"#c-{t13} > .cm-main [data-cm-answer]")
                    cpg.wait_for_timeout(450)
                    seen[(screen, scheme, "answering")] = cpg.evaluate(READ, "#comments")
                    cpg.keyboard.press("Escape")
                    cpg.wait_for_timeout(300)
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
                    cpg.evaluate("(id) => { const c = document.querySelector('.post-card[data-post=\"' + id + '\"] .post-foot');"
                                 " c && c.scrollIntoView({ block: 'center' }); }", post)
                    cpg.wait_for_timeout(300)
                    seen[(screen, scheme, "home's card")] = cpg.evaluate(READ, f".post-card[data-post='{post}'] .post-foot")
                    close_ctx(cctx, cpg)
                    nctx, npg = browser_as(b, None, screen=screen, scheme=scheme)
                    open_post(npg, post)
                    npg.evaluate("() => document.getElementById('comments').scrollIntoView({ block: 'start' })")
                    npg.wait_for_timeout(300)
                    seen[(screen, scheme, "signed out")] = npg.evaluate(READ, "#comments")
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
                     "signed out": ("Sign in to answer",), "home's card": ("4",), "⋯": ("Report comment",),
                     "your reports": ("Theo Lind",)}
            missing = [(" ".join(k), w) for k, v in seen.items() for w in musts.get(k[2], ())
                       if not any(x == w or (len(w) > 3 and x.startswith(w[:24])) for x in v["words"])]
            check("every word on the comments (a comment, an answer, the box, the count, Answer, a taken-down note, Sign in to"
                  " answer), a comment's ⋯ and its report, Home's card's count and Your Reports' comment card reads at 4.5:1"
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
            pg.click("[data-cm-open=pad]")
            fr = editor_frame(pg, "skribl-pad")
            if fr:
                add_from_pad(pg, fr)
            pg.fill("[data-cm-words]", "My cat would never be this patient")
            got = pg.evaluate(POST_AND_WATCH)
            pg.wait_for_timeout(400)
            after = pg.evaluate(DRAFT)
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
                  f"row {row}; skribl {sk}; on the page {shown}; box {after}")
            # A drawing answer, alone, and under a comment.
            open_post(pg, post)
            pg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", theo_c)
            pg.click(f"#c-{theo_c} > .cm-main [data-cm-answer]")
            pg.wait_for_timeout(500)
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
                    seen[(screen, scheme, "the box")] = cpg.evaluate(READ, "[data-cm-box]")
                    cpg.click("[data-cm-open=pad]")
                    fr = editor_frame(cpg, "skribl-pad")
                    if fr:
                        add_from_pad(cpg, fr)
                    cpg.evaluate("() => document.querySelector('[data-cm-box]').scrollIntoView({ block: 'center' })")
                    cpg.wait_for_timeout(400)
                    seen[(screen, scheme, "a drawing waiting")] = cpg.evaluate(READ, "[data-cm-box]")
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
