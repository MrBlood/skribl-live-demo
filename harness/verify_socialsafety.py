"""Safety on the Skribl site (phase 1, piece 5: report and block, your Reports
and what taking something down does, and the rules; docs/SOCIAL-SITE.md
"Built: piece 5, report and block", "Built: piece 5, your Reports" and "Built:
piece 5, the rules"), through the demo's own server, with Chromium's virtual
authenticator for the site's people.

  1. REPORT SOMEBODY: a profile's ⋯ (never your own; Block only signed in),
     Report @them with a person's own reasons, in order; into the site's queue
     (whose, the reason, the note, who sent it), once per reporter; signed
     out, Report alone, and the report names no sender.
  2. REPORT A POST OR A DRAWING: the post sheet's Report sends the Gallery's
     reasons and "A child's safety" to the site's own queue; a drawing shown
     outside a post is reported as a drawing.
  3. REPORT GUARDS: the token, the closed sets, a note too long or hidden,
     your own, gone; the limit.
  4. BLOCK, BOTH WAYS AND QUIETLY: from a profile's ⋯ and from a post's ⋯,
     asked once; then neither sees the other on Home or on a post's or a
     drawing's page; the blocker's Home says so; the blocker finds the
     profile saying so, with Unblock; the one blocked meets nobody.
  5. AND ON SKRIBL'S OWN PAGES: Explore's listing, a profile's skribls, a
     drawing's link page, its payload and its card; anybody else, and the
     author, as before.
  6. UNBLOCK: Settings lists the people you blocked, newest first, each with
     Unblock, which comes back saying so; only the blocker lifts a block.
  7. BLOCK GUARDS, and deleting an account: its blocks go, the reports that
     name it stay, naming nobody.
  8. SKRIBL'S OWN REPORT: the Gallery's sheet offers "A child's safety", and
     the operator's queue lists those first, with a word about the law.
  9. THE NEW SCREENS: every word at 4.5:1 on what is painted behind it, every
     target 44px, every text field 16px: phone and desk, light and dark.
 10. YOUR REPORTS: an admin's alone (the same 404 for anybody else); a card
     per thing, a child's safety first (its picture blurred and its words
     hidden until Open it, Keep it only then, a word about the law), then the
     newest; what and whose, each reason, what reporters wrote and who they
     are; Skribl's own reports on the same card.
 11. TAKE IT DOWN, OR KEEP IT: Keep it closes, hiding nothing; Take it down
     hides a post or a drawing from everybody else at once, withholds it in
     Skribl, keeps a copy and closes its reports; its maker sees the note.
 12. A PERSON TAKEN DOWN: nobody to everybody else, on the site's pages and
     Skribl's; they see their own with the note, and share nothing new.
 13. SKRIBL'S SEAMS: list_reports and close_reports, exported, documented,
     ordered, naming nobody, taking nothing down.
 14. THE REPORTS PAGE AND THE NOTES: words at 4.5:1, targets 44px; phone and
     desk, light and dark.
 15. THE RULES: Terms, Privacy and Community rules, three pages anybody can
     read, each a draft, each with the pills to the others; Terms in the
     mock's own words; Join and Settings link all three.
 16. THE RULES PAGES AND JOIN: words at 4.5:1, targets 44px; phone and desk,
     light and dark.
 17. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALSAFETY_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs (the first person a run makes is its admin, so a
section that needs one asks for the admin first). Every row was shown red by
breaking one part and green as built: DECISIONS.md, "Report and block at
/social", "Your Reports at /social" and "The rules, in plain words".
"""
import base64  # noqa: F401
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
import urllib.parse  # noqa: F401
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALSAFETY_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALSAFETY {n} — {label}")
    return True


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence report and block work.")
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
TMP = tempfile.mkdtemp(prefix="socialsafety-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialsafety-" + secrets.token_hex(8),
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


def admin(b):
    """The run's admin: the first person it made (the site makes its first
    person its admin), or Mira when it has made nobody yet. A section that
    needs one asks for it first, so a run of any sections has one."""
    got = db("select handle from social_people where is_admin order by id limit 1")
    if got:
        return _people[got[0][0]]
    return someone(b, "mira", "Mira Okafor")



def make_post(who, words, gallery=False, seed=0):
    """A post as the composer sends one: (status, answer)."""
    c = who.client()
    c.get("/social/")
    body = drawing(seed=seed)
    if gallery:
        body["visibility"] = "public"
    return c.post_json("/social/posts", {"words": words, "payload": body})


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


PAD = """async ([title, vis, seed, card]) => {
  await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
  const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
  const pts = Array.from({ length: 30 }, (_, i) => ({ x: 300 + i * 6, y: 300 + Math.sin((i + seed) / 3) * 60,
    color: '#7c5cff', size: 8, t: i * 30, start: i === 0 }));
  const r = await fetch('/api/skribls', { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) },
    body: JSON.stringify(Object.assign({ title, visibility: vis, version: 2, schemaVersion: 2, playbackMode: 'replay',
      canvasSize: { cssWidth: 816, cssHeight: 612 }, frames: [{ strokes: pts, strokeGroups: [pts.length] }] },
      card ? { thumbnail: (() => { const c = document.createElement('canvas'); c.width = 1200; c.height = 630;
        const g = c.getContext('2d'); g.fillStyle = '#7c5cff'; g.fillRect(0, 0, 1200, 630); return c.toDataURL('image/png'); })() } : {})) });
  const j = await r.json().catch(() => ({})); return [r.status, j.id || null]; }"""
CARDS = "() => [...document.querySelectorAll('.post-card')].map(c => c.getAttribute('data-handle'))"
OPEN = "(id) => document.getElementById(id).classList.contains('is-open')"
ACTS = "(s) => [...document.querySelectorAll(s + ' .post-act')].filter(b => !b.hidden).map(b => b.textContent.trim())"
REASONS = "(s) => [...document.querySelectorAll(s + ' input[name=reason]')].map(i => [i.value, i.closest('label').textContent.trim()])"
PERSON_REASONS = [["fake", "Spam or a fake account"], ["abuse", "Abusive or hateful"],
                  ["impersonation", "Pretending to be someone"], ["under13", "Under 13"],
                  ["child_safety", "A child’s safety"], ["other", "Something else"]]
POST_REASONS = [["spam", "Spam or misleading"], ["abuse", "Abusive or hateful"],
                ["copyright", "Copies someone else’s work"], ["child_safety", "A child’s safety"],
                ["other", "Something else"]]
THANKS = "Thanks. The people who run this site will look at it."


def pad(who, title, vis="public", seed=0, card=False):
    """A drawing posted from the Pad on its own page (not a post), as `who`;
    with a share card (a real picture) when `card`."""
    who.pg.goto(BASE + "/social/")
    return who.pg.evaluate(PAD, [title, vis, seed, card])


def explore_report(b, public_id, reason, note=None):
    """A report sent the way a signed-out visitor sends one from Explore's
    tiles or a drawing's link page: through Skribl's own report route, into
    Skribl's queue (not the site's). Its HTTP status."""
    ctx, pg = browser_as(b, None)
    try:
        pg.goto(BASE + "/social/explore")
        pg.wait_for_timeout(500)
        return pg.evaluate("""async ([id, reason, note]) => { await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
          const tok = decodeURIComponent((document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '');
          const r = await fetch('/api/skribls/' + id + '/report', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': tok },
            body: JSON.stringify(note ? { reason, note } : { reason }) }); return r.status; }""", [public_id, reason, note])
    finally:
        close_ctx(ctx, pg)


def home(pg):
    pg.goto(BASE + "/social/")
    pg.wait_for_timeout(600)
    return pg.evaluate(CARDS)


def on_home(pg, post):
    """Whether one post's card is on this person's Home (by its id: a
    person's other posts are not this one)."""
    pg.goto(BASE + "/social/")
    pg.wait_for_timeout(600)
    return pg.evaluate("(id) => !!document.querySelector('.post-card[data-post=\"' + id + '\"]')", post)


def pid_of(handle):
    got = db("select id, public_id from social_people where handle_key = ?", (handle.lower(),))
    return got[0] if got else (None, None)


def status(pg, path):
    r = pg.goto(BASE + path)
    pg.wait_for_timeout(300)
    return r.status if r else None


def card_of(pg, path):
    """What a drawing's card route gives this person: its picture, or the
    blank canvas it falls back to (it never 404s), by where it lands."""
    r = pg.goto(BASE + path)
    pg.wait_for_timeout(200)
    return "blank" if pg.url.endswith("poster-blank.svg") else ("picture" if r and r.status == 200 else r and r.status)


def api(pg, path):
    """A GET from inside the page, as its person: (status, json or None)."""
    return pg.evaluate("""async (u) => { const r = await fetch(u, { credentials: 'same-origin' });
      let j = null; try { j = await r.json(); } catch (e) {} return [r.status, j]; }""", path)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "report somebody: a profile's ⋯, a person's own reasons, into the site's queue"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        pg = mira.pg
        pg.goto(BASE + "/social/@mira")
        pg.wait_for_timeout(600)
        own_more = pg.evaluate("() => !!document.querySelector('[data-person-menu]')")
        pg.goto(BASE + "/social/@juno")
        pg.wait_for_function("() => !!window.SocialSafety", timeout=15000)
        pg.click("[data-person-menu]")
        pg.wait_for_function(OPEN, arg="personSheet", timeout=10000)
        sheet = pg.evaluate(ACTS, "#personSheet")
        pg.click("#personSheet [data-safety=report-person]")
        pg.wait_for_function(OPEN, arg="personReportSheet", timeout=10000)
        title = pg.evaluate("() => document.getElementById('personReportTitle').textContent")
        reasons = pg.evaluate(REASONS, "#personReportSheet")
        first = pg.evaluate("() => document.querySelector('#personReportSheet input[name=reason]:checked').value")
        pg.check("#personReportSheet input[value=impersonation]")
        pg.fill("#personReportNote", "Says she is me")
        pg.click("#personReportSheet [data-safety-send]")
        pg.wait_for_function("() => (document.querySelector('#personReportSheet [data-safety-say]') || {}).textContent.length > 12",
                             timeout=10000)
        said = pg.evaluate("() => document.querySelector('#personReportSheet [data-safety-say]').textContent")
        done = pg.evaluate("() => document.querySelector('#personReportSheet .post-sheet-acts [data-make-close]').textContent")
        mid, _ = pid_of("mira")
        jid, jpub = pid_of("juno")
        rows = db("select kind, target, about_id, reason, note, reporter_id, state from social_reports where kind = 'person'")
        check("a profile's ⋯ (never on your own) offers Report @them and, signed in, Block @them; Report @them rises"
              " with a person's own reasons, in order, the first picked",
              not own_more and sheet == ["Report @juno", "Block @juno"] and title == "Report @juno"
              and reasons == PERSON_REASONS and first == "fake",
              f"own ⋯ {own_more}; sheet {sheet}; title {title!r}; reasons {reasons}; first {first}")
        c = mira.client()
        c.get("/social/@juno")
        again = c.post_json("/social/report", {"kind": "person", "target": "juno", "reason": "abuse", "note": None})[0]
        rows2 = db("select count(*) from social_reports where kind = 'person' and target = ?", (jpub,))[0][0]
        check("it lands in the site's queue: about them (their public id), the reason and the note, who sent it,"
              " open; it says thanks; a second report of them by the same person writes nothing more",
              rows == [("person", jpub, jid, "impersonation", "Says she is me", mid, "open")]
              and said == THANKS and done == "Done" and again == 202 and rows2 == 1,
              f"rows {rows}; said {said!r}; button {done!r}; again {again}, {rows2} row(s)")
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/@juno")
        npg.wait_for_function("() => !!window.SocialSafety", timeout=15000)
        npg.click("[data-person-menu]")
        npg.wait_for_function(OPEN, arg="personSheet", timeout=10000)
        nsheet = npg.evaluate(ACTS, "#personSheet")
        npg.click("#personSheet [data-safety=report-person]")
        npg.wait_for_function(OPEN, arg="personReportSheet", timeout=10000)
        npg.check("#personReportSheet input[value=fake]")
        npg.click("#personReportSheet [data-safety-send]")
        npg.wait_for_timeout(1200)
        nsaid = npg.evaluate("() => document.querySelector('#personReportSheet [data-safety-say]').textContent")
        close_ctx(nctx, npg)
        anon = db("select reason, reporter_id from social_reports where kind = 'person' and target = ? and reporter_id is null",
                  (jpub,))
        check("signed out, the ⋯ offers Report alone, and the report lands naming nobody as its sender",
              nsheet == ["Report @juno"] and nsaid == THANKS and anon == [("fake", None)],
              f"sheet {nsheet}; said {nsaid!r}; rows {anon}")

    # ------------------------------------------------------------------ 2
    if part(2, "report a post or a drawing: the Gallery's reasons and a child's safety, into the site's queue"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(juno, "Section 2, a post", seed=21)
        post = j.get("post") if isinstance(j, dict) else None
        st_d, shown = pad(juno, "Section 2, a drawing", "public", 22)
        pg = mira.pg
        pg.goto(BASE + f"/social/p/{post}")
        pg.wait_for_function("() => !!window.SocialSheet && document.readyState === 'complete'", timeout=15000)
        pg.click("[data-post-menu] >> visible=true")
        pg.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        acts = pg.evaluate(ACTS, "#postSheet")
        pg.click("#postSheet [data-act=report]")
        pg.wait_for_function(OPEN, arg="reportSheet", timeout=10000)
        reasons = pg.evaluate(REASONS, "#reportSheet")
        pg.check("#reportSheet input[value=child_safety]")
        pg.fill("#reportNote", "Not something for here")
        pg.click("#reportSheet [data-report-send]")
        pg.wait_for_function("() => (document.querySelector('#reportSheet [data-report-say]') || {}).textContent.length > 12",
                             timeout=10000)
        said = pg.evaluate("() => document.querySelector('#reportSheet [data-report-say]').textContent")
        jid, _ = pid_of("juno")
        mid, _ = pid_of("mira")
        prow = db("select kind, about_id, reason, note, reporter_id from social_reports where target = ?", (post,))
        pg.goto(BASE + f"/social/b/{shown}")
        pg.wait_for_function("() => !!window.SocialSheet && document.readyState === 'complete'", timeout=15000)
        pg.click("[data-post-menu] >> visible=true")
        pg.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        pg.click("#postSheet [data-act=report]")
        pg.wait_for_function(OPEN, arg="reportSheet", timeout=10000)
        pg.check("#reportSheet input[value=spam]")
        pg.click("#reportSheet [data-report-send]")
        pg.wait_for_timeout(1200)
        drow = db("select kind, about_id, reason from social_reports where target = ?", (shown,))
        sk_queue = db("select count(*) from skribl_reports")[0][0]
        check("somebody else's post's ⋯ says Copy link, Share…, Report this post and Block @them; Report sends the"
              " Gallery's reasons and A child's safety, in order, into the site's own queue (the post, whose it is,"
              " the reason, the note, who sent it), and says thanks; Skribl's own queue is not asked",
              st == 200 and acts == ["Copy link", "Share…", "Report this post", "Block @juno"]
              and reasons == POST_REASONS and said == THANKS
              and prow == [("post", jid, "child_safety", "Not something for here", mid)] and sk_queue == 0,
              f"post {st}; sheet {acts}; reasons {reasons}; said {said!r}; row {prow}; Skribl's queue {sk_queue}")
        check("a drawing shown outside a post is reported as a drawing (its skribl's address), from its own page's ⋯",
              st_d == 201 and drow == [("drawing", jid, "spam")], f"drawing {st_d}; row {drow}")

    # ------------------------------------------------------------------ 3
    if part(3, "report guards: the token, the closed sets, the note, your own, gone, a block, the limit"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        st, j = make_post(juno, "Section 3, a post", seed=31)
        post = j.get("post") if isinstance(j, dict) else None
        st2, j2 = make_post(mira, "Section 3, mine", seed=32)
        mine = j2.get("post") if isinstance(j2, dict) else None
        c = mira.client()
        c.get("/social/")
        base = {"kind": "post", "target": post, "reason": "spam", "note": None}
        ans = {
            "no token": c.post_json("/social/report", base, token=False)[0],
            "a kind not in the set": c.post_json("/social/report", dict(base, kind="everything"))[0],
            "a reason not in the set": c.post_json("/social/report", dict(base, reason="fake"))[0],
            "a person's reason for a post": c.post_json("/social/report", dict(base, reason="under13"))[0],
            "a note too long": c.post_json("/social/report", dict(base, note="x" * 301))[1],
            "a hidden character": c.post_json("/social/report", dict(base, note="hello‮world"))[1],
            "your own post": c.post_json("/social/report", dict(base, target=mine))[0],
            "yourself": c.post_json("/social/report", {"kind": "person", "target": "mira", "reason": "fake"})[0],
            "a post not there": c.post_json("/social/report", dict(base, target="nothinghere"))[0],
            "nobody by that name": c.post_json("/social/report", {"kind": "person", "target": "nobodyhere", "reason": "fake"})[0],
        }
        n = db("select count(*) from social_reports where target in (?, ?)", (post, mine))[0][0]
        check("a report is refused kindly without the page's token (403), with a kind or reason not in its set (400),"
              " a note too long or with a hidden character (400, each its own words), for your own post or yourself,"
              " or for something not there (404); nothing is written",
              ans == {"no token": 403, "a kind not in the set": 400, "a reason not in the set": 400,
                      "a person's reason for a post": 400, "a note too long": {"error": "note_long"},
                      "a hidden character": {"error": "note_chars"}, "your own post": 404, "yourself": 404,
                      "a post not there": 404, "nobody by that name": 404} and n == 0,
              f"{ans}; rows {n}")
        theo = someone(b, "theo", "Theo Lind")
        tc = theo.client()
        tc.get("/social/")
        got = [tc.post_json("/social/report", {"kind": "person", "target": "juno", "reason": "fake"})[0] for _ in range(31)]
        check("reports are limited per person (30 an hour): the 31st is refused kindly (429), the 30 before it taken",
              got[:30] == [202] * 30 and got[30] == 429, f"{got.count(202)} taken, then {got[30:]}")

    # ------------------------------------------------------------------ 4
    if part(4, "block: both ways and quietly, from a profile's ⋯ and from a post's ⋯"):
        ada = someone(b, "ada", "Ada Quist")
        ben = someone(b, "ben", "Ben Reyes")
        st1, j1 = make_post(ada, "Section 4, Ada's post", seed=41)
        ada_post = j1.get("post")
        st2, ada_d = pad(ada, "Section 4, Ada's drawing", "public", 42)
        st3, j3 = make_post(ben, "Section 4, Ben's post", seed=43)
        ben_post = j3.get("post")
        st4, ben_d = pad(ben, "Section 4, Ben's drawing", "public", 44)
        before = (home(ada.pg).count("ben"), home(ben.pg).count("ada"))
        pg = ada.pg
        pg.goto(BASE + "/social/@ben")
        pg.wait_for_function("() => !!window.SocialSafety", timeout=15000)
        pg.click("[data-person-menu]")
        pg.wait_for_function(OPEN, arg="personSheet", timeout=10000)
        pg.click("#personSheet [data-safety=block]")
        pg.wait_for_function(OPEN, arg="blockSheet", timeout=10000)
        ask = pg.evaluate("""() => ({ title: document.getElementById('blockTitle').textContent,
          lede: document.querySelector('#blockSheet .post-lede').textContent,
          go: document.querySelector('#blockSheet [data-safety-block]').textContent })""")
        with pg.expect_navigation(timeout=20000):
            pg.click("#blockSheet [data-safety-block]")
        pg.wait_for_timeout(800)
        prof = pg.evaluate("""() => ({ at: location.pathname, note: (document.querySelector('.prof-blocked') || {}).textContent,
          unblock: !!document.querySelector('form[data-unblock] button'), skribls: !!document.getElementById('profSkribls'),
          more: !!document.querySelector('[data-person-menu]') })""")
        rows = db("select blocker_id, blocked_id from social_blocks")
        aid, _ = pid_of("ada")
        nid, _ = pid_of("ben")
        check("Block @them is asked once, in its own words (both ways, quietly, undone in Settings); then their profile"
              " says you blocked them, with Unblock, and shows nothing they made",
              ask == {"title": "Block @ben?",
                      "lede": "You won’t see each other’s posts or drawings, and they can’t see your profile. They aren’t"
                              " told. You can unblock them in Settings.", "go": "Block"}
              and prof["at"] == "/social/@ben"
              and prof["note"] == "You blocked @ben. You won’t see each other’s posts or drawings, and they can’t see your profile."
              and prof["unblock"] and not prof["skribls"] and not prof["more"] and rows == [(aid, nid)],
              f"asked {ask}; profile {prof}; rows {rows}")
        after = {"ada's home": home(ada.pg), "ben's home": home(ben.pg)}
        pages = {"ada at ben's post": status(ada.pg, f"/social/p/{ben_post}"),
                 "ada at ben's drawing": status(ada.pg, f"/social/b/{ben_d}"),
                 "ben at ada's post": status(ben.pg, f"/social/p/{ada_post}"),
                 "ben at ada's drawing": status(ben.pg, f"/social/b/{ada_d}"),
                 "ben at ada's profile": status(ben.pg, "/social/@ada")}
        nobody = ben.pg.evaluate("() => document.title")
        check("then neither sees the other on Home, posts and drawings alike, nor their post's page or drawing's page"
              " (gone, as a deleted one is); to the one blocked, the blocker's profile is nobody's",
              before == (2, 2) and "ben" not in after["ada's home"] and "ada" not in after["ben's home"]
              and pages == {"ada at ben's post": 404, "ada at ben's drawing": 404, "ben at ada's post": 404,
                            "ben at ada's drawing": 404, "ben at ada's profile": 404}
              and nobody.startswith("Nobody here"),
              f"before {before}; after {after}; pages {pages}; title {nobody!r}")
        cyd = someone(b, "cyd", "Cyd Mbeki")
        st5, j5 = make_post(ben, "Section 4, Ben again", seed=45)
        cpg = cyd.pg
        cpg.goto(BASE + "/social/")
        cpg.wait_for_function("() => !!window.SocialSafety && !!window.SocialSheet", timeout=15000)
        card = f".post-card[data-post='{j5.get('post')}']"
        cpg.click(f"{card} [data-post-menu]")
        cpg.wait_for_function(OPEN, arg="postSheet", timeout=10000)
        cacts = cpg.evaluate(ACTS, "#postSheet")
        cpg.click("#postSheet [data-act=block]")
        cpg.wait_for_function(OPEN, arg="blockSheet", timeout=10000)
        ctitle = cpg.evaluate("() => document.getElementById('blockTitle').textContent")
        with cpg.expect_navigation(timeout=20000):
            cpg.click("#blockSheet [data-safety-block]")
        cpg.wait_for_timeout(800)
        cafter = cpg.evaluate("""() => ({ url: location.pathname + location.search, note: (document.querySelector('.note') || {}).textContent,
          cards: [...document.querySelectorAll('.post-card')].map(c => c.getAttribute('data-handle')) })""")
        check("from a post's ⋯ on Home: Block @them, asked once; then Home says so and holds nothing of theirs",
              cacts == ["Copy link", "Share…", "Report this post", "Block @ben"] and ctitle == "Block @ben?"
              and cafter["url"] == "/social/?note=blocked"
              and cafter["note"] == "Blocked. You won’t see each other’s posts or drawings. You can unblock them in Settings."
              and "ben" not in cafter["cards"],
              f"sheet {cacts}; title {ctitle!r}; after {cafter}")

    # ------------------------------------------------------------------ 5
    if part(5, "and on Skribl's own pages: its listings, a drawing's link page, payload and card"):
        ada = someone(b, "ada", "Ada Quist")
        ben = someone(b, "ben", "Ben Reyes")
        aid, apub = pid_of("ada")
        nid, bpub = pid_of("ben")
        if not db("select 1 from social_blocks where blocker_id = ? and blocked_id = ?", (aid, nid)):
            c = ada.client()
            c.get("/social/@ben")
            c.post_json("/social/@ben/block", {})
        st, ben_d = pad(ben, "Section 5, Ben's drawing", "public", 51, card=True)
        st2, ada_d = pad(ada, "Section 5, Ada's drawing", "public", 52)
        ada.pg.goto(BASE + "/social/explore")
        ada.pg.wait_for_timeout(500)
        a_list = [i["id"] for i in (api(ada.pg, "/api/skribls?limit=100")[1] or {}).get("items", [])]
        a_by = (api(ada.pg, f"/api/skribls?limit=100&user_id={bpub}")[1] or {}).get("items", [])
        ben.pg.goto(BASE + "/social/explore")
        ben.pg.wait_for_timeout(500)
        b_list = [i["id"] for i in (api(ben.pg, "/api/skribls?limit=100")[1] or {}).get("items", [])]
        b_own = [i["id"] for i in (api(ben.pg, f"/api/skribls?limit=100&user_id={bpub}")[1] or {}).get("items", [])]
        links = {"ada: ben's link page": status(ada.pg, f"/s/{ben_d}"),
                 "ada: ben's payload": api(ada.pg, f"/api/skribls/{ben_d}")[0],
                 "ada: ben's card": card_of(ada.pg, f"/s/{ben_d}/poster"),
                 "ben: ada's link page": status(ben.pg, f"/s/{ada_d}"),
                 "ben: ada's payload": api(ben.pg, f"/api/skribls/{ada_d}")[0],
                 "ben: his own": status(ben.pg, f"/s/{ben_d}"),
                 "ben: his own card": card_of(ben.pg, f"/s/{ben_d}/poster")}
        # THE FILTER, NOT ONLY THE POLICY. Skribl's listing gives the policy the
        # last word: a row it refuses is dropped and the page refilled from the
        # rows after it, and the log says once to install a feed filter. So the
        # listing alone reads the same without the filter; the log does not.
        warned = "the listing held posts the visibility policy refuses" in open(LOG).read()
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/explore")
        npg.wait_for_timeout(400)
        n_list = [i["id"] for i in (api(npg, "/api/skribls?limit=100")[1] or {}).get("items", [])]
        n_page = status(npg, f"/s/{ben_d}")
        close_ctx(nctx, npg)
        check("on Skribl's own pages too: Explore's listing and a profile's skribls leave out the other's drawings, both"
              " ways, in the listing's own query (the feed filter: Skribl never has to drop and refill a page); their link"
              " page and payload are not there for them (404) and their card is the blank canvas; the author still has"
              " their own, card and all",
              st == 201 and st2 == 201 and ben_d not in a_list and a_by == [] and ada_d not in b_list and not warned
              and ben_d in b_own
              and links == {"ada: ben's link page": 404, "ada: ben's payload": 404, "ada: ben's card": "blank",
                            "ben: ada's link page": 404, "ben: ada's payload": 404, "ben: his own": 200,
                            "ben: his own card": "picture"},
              f"ada lists ben's {ben_d in a_list}, by ben {len(a_by)}; ben lists ada's {ada_d in b_list}, his own {ben_d in b_own};"
              f" refill warning in the log {warned};"
              f" {links}")
        check("...and for anybody else nothing changes: signed out, both drawings are listed and open",
              ben_d in n_list and ada_d in n_list and n_page == 200, f"listed {ben_d in n_list}/{ada_d in n_list}; page {n_page}")

    # ------------------------------------------------------------------ 6
    if part(6, "unblock: Settings lists who you blocked, each with Unblock; then all is as before"):
        eve = someone(b, "eve", "Eve Sato")
        fay = someone(b, "fay", "Fay Imre")
        gus = someone(b, "gus", "Gus Oyelaran")
        st, j = make_post(fay, "Section 6, Fay's post", seed=61)
        fay_post = j.get("post")
        c = eve.client()
        c.get("/social/")
        c.post_json("/social/@fay/block", {})
        time.sleep(0.05)
        c.post_json("/social/@gus/block", {})
        pg = eve.pg
        pg.goto(BASE + "/social/you")
        pg.wait_for_timeout(600)
        listed = pg.evaluate("() => [...document.querySelectorAll('.blocked-row')].map(r => r.querySelector('.blocked-who').innerText.replace(/\\s+/g, ' ').trim())")
        said = pg.evaluate("() => { const t = document.getElementById('blockedTitle'); return t ? t.nextElementSibling.textContent : null; }")
        with pg.expect_navigation(timeout=15000):
            pg.click(".blocked-row:has-text('@fay') button")
        back = pg.evaluate("() => ({ url: location.pathname + location.search, note: (document.querySelector('.note') || {}).textContent,"
                           " rows: document.querySelectorAll('.blocked-row').length })")
        again = {"eve's home has fay": "fay" in home(eve.pg), "fay at eve": status(fay.pg, "/social/@eve"),
                 "eve at fay's post": status(eve.pg, f"/social/p/{fay_post}")}
        check("Settings lists the people you blocked, newest first, each with Unblock, in the mock's words; Unblock comes"
              " back to Settings saying so, and they see each other again",
              listed == ["Gus Oyelaran @gus", "Fay Imre @fay"] and said == "You and they don’t see each other. They aren’t told."
              and back["url"] == "/social/you?note=unblocked"
              and back["note"] == "Unblocked. You’ll see each other’s posts and drawings again." and back["rows"] == 1
              and again == {"eve's home has fay": True, "fay at eve": 200, "eve at fay's post": 200},
              f"listed {listed}; said {said!r}; back {back}; again {again}")
        gc = gus.client()
        gc.get("/social/")
        lift = gc.post_json("/social/@eve/unblock", {})
        still = db("select count(*) from social_blocks b join social_people p on p.id = b.blocked_id where p.handle = 'gus'")[0][0]
        gus_at = status(gus.pg, "/social/@eve")
        # Recorded, never a stop: a block already gone leaves no Unblock to press.
        lifted, stopped = None, None
        try:
            pg.goto(BASE + "/social/@gus")
            pg.wait_for_function("() => !!document.querySelector('form[data-unblock]')", timeout=10000)
            pg.wait_for_timeout(300)
            pg.click("form[data-unblock] button")
            pg.wait_for_function("() => !document.querySelector('.prof-blocked')", timeout=15000)
        except Exception as exc:  # noqa: BLE001
            stopped = str(exc).splitlines()[0][:80]
        lifted = db("select count(*) from social_blocks b join social_people p on p.id = b.blocked_id where p.handle = 'gus'")[0][0]
        check("only the blocker lifts a block: the one blocked asking changes nothing; on the blocked profile,"
              " Unblock lifts it in place",
              lift[0] == 200 and still == 1 and gus_at == 404 and lifted == 0 and stopped is None,
              f"gus asks {lift}; still {still}; gus at eve {gus_at}; after eve's Unblock {lifted}; stopped {stopped}")

    # ------------------------------------------------------------------ 7
    if part(7, "block guards; deleting an account takes its blocks and leaves the reports that name it"):
        hal = someone(b, "hal", "Hal Brandt")
        ivy = someone(b, "ivy", "Ivy Novak")
        c = hal.client()
        c.get("/social/")
        nc = Client()
        nc.get("/social/@ivy")              # a profile carries the page's token for anybody
        ans = {"no token": c.post_json("/social/@ivy/block", {}, token=False)[0],
               "signed out": nc.post_json("/social/@ivy/block", {})[0],
               "yourself": c.post_json("/social/@hal/block", {})[0],
               "nobody by that name": c.post_json("/social/@nobodyhere/block", {})[0],
               "once": c.post_json("/social/@ivy/block", {})[0],
               "twice": c.post_json("/social/@ivy/block", {})[0]}
        hid, _ = pid_of("hal")
        iid, ipub = pid_of("ivy")
        n = db("select count(*) from social_blocks where blocker_id = ?", (hid,))[0][0]
        check("a block is refused without the page's token (403), signed out (401), for yourself or nobody by that"
              " name (404); twice is still one",
              ans == {"no token": 403, "signed out": 401, "yourself": 404, "nobody by that name": 404, "once": 200,
                      "twice": 200} and n == 1, f"{ans}; rows {n}")
        got = [c.post_json("/social/@ivy/unblock", {})[0] for _ in range(60)]
        # The four tries above that reached the limit (yourself, nobody, once,
        # twice) are counted; the one without a token never got that far.
        check("blocks and unblocks are limited per person (60 an hour, the four tries above among them): the 61st is"
              " refused kindly (429)",
              429 in got and got.index(429) == 56 and set(got[:56]) == {200},
              f"{got.count(200)} taken, first refused at {got.index(429) if 429 in got else None}")
        ivc = ivy.client()
        ivc.get("/social/")
        # Ivy reports Hal first: once a block stands, he is not hers to report.
        ivc.post_json("/social/report", {"kind": "person", "target": "hal", "reason": "abuse"})
        ivc.post_json("/social/@hal/block", {})
        mc = someone(b, "mira", "Mira Okafor").client()
        mc.get("/social/@ivy")
        mc.post_json("/social/report", {"kind": "person", "target": "ivy", "reason": "abuse"})
        ivy.pg.goto(BASE + "/social/you/delete")
        ivy.pg.wait_for_timeout(400)
        ivy.pg.fill("input[name=confirm]", "ivy")
        with ivy.pg.expect_navigation(timeout=15000):
            ivy.pg.click("form button[type=submit].btn-danger, form button[type=submit]")
        blocks = db("select count(*) from social_blocks where blocker_id = ? or blocked_id = ?", (iid, iid))[0][0]
        about = db("select about_id from social_reports where target = ?", (ipub,))
        sent = db("select reporter_id from social_reports where kind = 'person' and reason = 'abuse' and about_id = ?", (hid,))
        check("deleting an account takes its blocks, both ways; a report about them stays, naming nobody, and so does"
              " one they sent",
              blocks == 0 and about == [(None,)] and sent == [(None,)], f"blocks {blocks}; about {about}; sent {sent}")

    # ------------------------------------------------------------------ 8
    if part(8, "Skribl's own report: the Gallery's sheet offers a child's safety, its queue lists those first"):
        joy = someone(b, "joy", "Joy Lindqvist")
        st, d1 = pad(joy, "Section 8, reported for spam", "public", 81)
        st2, d2 = pad(joy, "Section 8, reported for a child's safety", "public", 82)
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/explore")
        npg.wait_for_timeout(1200)
        gal = npg.evaluate(REASONS, "#reportSheet")
        rep = npg.evaluate("""async ([a, b2]) => { await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
          const tok = decodeURIComponent((document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '');
          const go = (id, reason) => fetch('/api/skribls/' + id + '/report', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': tok }, body: JSON.stringify({ reason }) }).then(r => r.status);
          return [await go(a, 'spam'), await go(a, 'abuse'), await go(b2, 'child_safety')]; }""", [d1, d2])
        close_ctx(nctx, npg)
        q = subprocess.run([sys.executable, "-m", "skribl.takedown", "--reports"], cwd=ROOT, env=ENV,
                           capture_output=True, text=True, timeout=120)
        lines = [ln for ln in q.stdout.splitlines() if ln.startswith("  ")]
        order = [ln.split()[0] for ln in lines if ln.strip().split()[0] in (d1, d2)]
        law = [ln for ln in lines if "CHILD'S SAFETY" in ln]
        check("Explore's own report sheet (Skribl's) offers A child's safety among its reasons; its route takes it; and"
              " the operator's queue lists a child's safety first, before a drawing reported more often, with a word"
              " about the law",
              ["child_safety", "A child's safety"] in gal and rep == [202, 202, 202] and q.returncode == 0
              and order[:2] == [d2, d1] and len(law) == 1 and "NCMEC" in law[0],
              f"reasons {gal}; sent {rep}; queue order {order}; {law}; exit {q.returncode}")

    # ------------------------------------------------------------------ 9
    if part(9, "the new screens: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        mira = someone(b, "mira", "Mira Okafor")
        juno = someone(b, "juno", "Juno Park")
        kai = someone(b, "kai", "Kai Ferro")
        kc = mira.client()
        kc.get("/social/")
        kc.post_json("/social/@kai/block", {})
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                cctx, cpg = browser_as(b, mira, screen=screen, scheme=scheme)
                cpg.goto(BASE + "/social/@juno")
                cpg.wait_for_function("() => !!window.SocialSafety", timeout=15000)
                cpg.click("[data-person-menu]")
                cpg.wait_for_function(OPEN, arg="personSheet", timeout=10000)
                cpg.wait_for_timeout(450)
                seen[(screen, scheme, "person ⋯")] = cpg.evaluate(READ, "#personSheet")
                cpg.click("#personSheet [data-safety=report-person]")
                cpg.wait_for_function(OPEN, arg="personReportSheet", timeout=10000)
                cpg.wait_for_timeout(450)
                seen[(screen, scheme, "report a person")] = cpg.evaluate(READ, "#personReportSheet")
                cpg.keyboard.press("Escape")
                cpg.wait_for_timeout(450)
                cpg.click("[data-person-menu]")
                cpg.wait_for_function(OPEN, arg="personSheet", timeout=10000)
                cpg.click("#personSheet [data-safety=block]")
                cpg.wait_for_function(OPEN, arg="blockSheet", timeout=10000)
                cpg.wait_for_timeout(450)
                seen[(screen, scheme, "block")] = cpg.evaluate(READ, "#blockSheet")
                cpg.goto(BASE + "/social/@kai")
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "blocked profile")] = cpg.evaluate(READ, "main")
                cpg.goto(BASE + "/social/you")
                cpg.wait_for_timeout(600)
                cpg.evaluate("() => document.getElementById('blockedTitle').scrollIntoView({ block: 'center' })")
                cpg.wait_for_timeout(300)
                seen[(screen, scheme, "settings")] = cpg.evaluate(READ, "main")
                close_ctx(cctx, cpg)
        low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
        small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
        fields = [(k, v["fields"]) for k, v in seen.items() if v["fields"]]
        lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
        floors = all(v["read"] >= 2 for v in seen.values())
        check("every word on a person's ⋯, Report @them, Block @them?, a profile you blocked and Settings' Blocked reads at"
              " 4.5:1 or more on what is painted behind it, every control is 44px or more each way, every text field"
              " 16px: phone and desk, light and dark",
              not low and not small and not fields and floors,
              f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small: {small[:3]};"
              f" fields: {fields[:3]}; each {[(' '.join(k), v['read']) for k, v in seen.items()]}")

    # ------------------------------------------------------------------ 10
    if part(10, "your Reports: an admin's, a card per thing, a child's safety first"):
        # THE QUEUE STARTS EMPTY: what earlier sections reported is answered
        # first, the site's and Skribl's, so the page holds this section's
        # cards and Settings counts them (a whole run left seven open).
        con = sqlite3.connect(DB, timeout=10)
        try:
            con.execute("update social_reports set state = 'kept' where state = 'open'")
            con.execute("update skribl_reports set state = 'closed' where state = 'open'")
            con.commit()
        finally:
            con.close()
        mira = admin(b)
        lee = someone(b, "lee", "Lee Varga")
        ora = someone(b, "ora", "Ora Quinn")
        st, j = make_post(lee, "Section 10, Lee's post", seed=101)
        lee_post = j.get("post")
        st_d, lee_d = pad(lee, "Section 10, Lee's drawing", "public", 102, card=True)
        oc = ora.client()
        oc.get("/social/")
        # The oldest first: a child's safety must lead the page for its reason,
        # not for being the newest.
        sent = [oc.post_json("/social/report", {"kind": "drawing", "target": lee_d, "reason": "child_safety"})[0]]
        sent.append(explore_report(b, lee_d, "spam", "From Explore"))
        nc = Client()
        nc.get(f"/social/p/{lee_post}")         # a post's page carries the page's token for anybody
        sent.append(nc.post_json("/social/report", {"kind": "post", "target": lee_post, "reason": "abuse"})[0])
        time.sleep(0.05)
        sent.append(oc.post_json("/social/report", {"kind": "post", "target": lee_post, "reason": "abuse", "note": "Mean words"})[0])
        time.sleep(0.05)
        sent.append(oc.post_json("/social/report", {"kind": "person", "target": "lee", "reason": "impersonation"})[0])
        nctx, npg = browser_as(b, None)
        anon = status(npg, "/social/reports")
        close_ctx(nctx, npg)
        not_admin = status(ora.pg, "/social/reports")
        pg = mira.pg
        pg.goto(BASE + "/social/you")
        pg.wait_for_timeout(500)
        panel = pg.evaluate("() => { const t = document.getElementById('repTitle'); return t ? t.nextElementSibling.textContent : null; }")
        pg.goto(BASE + "/social/reports")
        pg.wait_for_timeout(800)
        # What is painted: a blur is a computed filter, a control is one with a box.
        CARD = """c => ({ kind: c.dataset.kind,
          child: c.classList.contains('is-child'), tag: (c.querySelector('.rep-tag') || {}).textContent || null,
          why: [...c.querySelectorAll('.rep-why')].map(e => e.textContent), meta: c.querySelector('.rep-meta').textContent.split(' · ')[0],
          who: c.querySelector('.rep-who').innerText, notes: [...c.querySelectorAll('.rep-note')].map(n => n.innerText),
          by: c.querySelector('.rep-by').innerText,
          veiled: [...c.querySelectorAll('*')].filter(e => getComputedStyle(e).filter.includes('blur')).length,
          words: [...c.querySelectorAll('.rep-words')].filter(e => e.getClientRects().length > 0).map(e => e.textContent),
          link: !!c.querySelector('.rep-open') && c.querySelector('.rep-open').getClientRects().length > 0,
          keep: c.querySelector('form[action$=keep] button').getClientRects().length > 0,
          open: !!c.querySelector('[data-unveil]') && c.querySelector('[data-unveil]').getClientRects().length > 0,
          law: (c.querySelector('.rep-law') || {}).textContent || null })"""
        cards = pg.evaluate(f"() => [...document.querySelectorAll('[data-rep]')].map({CARD})")
        check("Your Reports is an admin's: anybody else, signed in or not, meets the same 404 as a page that is not there;"
              " Settings tells an admin how many wait",
              sent == [202] * 5 and anon == 404 and not_admin == 404
              and panel == "3 open. You run this site, so reports come to you.",
              f"sent {sent}; signed out {anon}; not an admin {not_admin}; panel {panel!r}")
        want0 = {"kind": "drawing", "child": True, "tag": "A child’s safety", "why": ["Spam or misleading"],
                 "meta": "2 reports", "who": "Lee Varga @lee · a drawing", "notes": ["Somebody wrote: From Explore"],
                 "by": "Reported by Ora Quinn, somebody on Explore", "veiled": 1, "words": ["Hidden until you open it."],
                 "link": False, "keep": False, "open": True}
        LAW = ("Look before anything else. Taking it down hides it at once and keeps a copy; the lawyer will say what"
               " the law asks of you next.")
        c0 = dict(cards[0]) if cards else {}
        law = c0.pop("law", None)
        opened = None
        if cards and cards[0]["open"]:
            pg.click("[data-rep] [data-unveil]")
            pg.wait_for_timeout(300)
            got = pg.evaluate(f"() => ({CARD})(document.querySelector('[data-rep]'))")
            opened = {k: got[k] for k in ("veiled", "words", "link", "keep", "open")}
        check("a card per thing: a child's safety first, ringed, its picture blurred and its words hidden until Open it,"
              " Keep it only once opened, a word about the law; then the newest; each says what and whose, each reason and how many, what"
              " reporters wrote and who they are (seen only here), Skribl's own reports of a drawing on its card",
              c0 == want0 and law == LAW
              and opened == {"veiled": 0, "words": ["“Section 10, Lee's drawing”"], "link": True, "keep": True, "open": False}
              and [(c["kind"], c["why"], c["meta"], c["who"], c["words"], c["notes"], c["by"], c["keep"], c["link"])
                   for c in cards[1:]]
              == [("person", ["Pretending to be someone"], "1 report", "Lee Varga @lee · a profile", [], [],
                   "Reported by Ora Quinn", True, True),
                  ("post", ["Abusive or hateful ×2"], "2 reports", "Lee Varga @lee · a post", ["“Section 10, Lee's post”"],
                   ["Ora Quinn wrote: Mean words"], "Reported by Ora Quinn, somebody signed out", True, True)],
              f"{cards}; law {law!r}; opened {opened}")

    # ------------------------------------------------------------------ 11
    if part(11, "take it down, or keep it: what changes, for whom, and that a copy is kept"):
        mira = admin(b)
        lee = someone(b, "lee", "Lee Varga")
        ora = someone(b, "ora", "Ora Quinn")
        st, j = make_post(lee, "Section 11, Lee's post", seed=111)
        lee_post = j.get("post")
        lee_sk = db("select skribl_id from social_posts where public_id = ?", (lee_post,))[0][0]
        st_d, lee_d = pad(lee, "Section 11, Lee's drawing", "public", 112, card=True)
        oc = ora.client()
        oc.get("/social/")
        oc.post_json("/social/report", {"kind": "post", "target": lee_post, "reason": "abuse"})
        oc.post_json("/social/report", {"kind": "person", "target": "lee", "reason": "fake"})
        oc.post_json("/social/report", {"kind": "drawing", "target": lee_d, "reason": "child_safety"})
        on_explore = [explore_report(b, lee_sk, "abuse"), explore_report(b, lee_d, "spam")]
        pg = mira.pg

        def skribl_states(public_id):
            return db("select r.state from skribl_reports r join skribl_posts p on p.id = r.post_id"
                      " where p.public_id = ?", (public_id,))

        def answer(kind, target, how):
            pg.goto(BASE + "/social/reports")
            pg.wait_for_timeout(500)
            card = f"[data-rep][data-kind='{kind}'][data-target='{target}']"
            if how == "down" and pg.evaluate("(s) => !!document.querySelector(s + ' [data-unveil]')", card):
                pg.click(f"{card} [data-unveil]")
                pg.wait_for_timeout(200)
            with pg.expect_navigation(timeout=15000):
                pg.click(f"{card} form[action$={how if how == 'keep' else 'down'}] button")
            return pg.evaluate("() => (document.querySelector('.note') || {}).textContent")

        lee_pub = pid_of("lee")[1]
        kept = answer("person", lee_pub, "keep")
        kept_rows = db("select state, handled_by_id is not null from social_reports where kind = 'person' and target = ?", (lee_pub,))
        check("Keep it closes a thing's reports, saying who answered and when, and hides nothing",
              kept == "Kept. Its reports are closed." and kept_rows and all(r == ("kept", 1) for r in kept_rows)
              and status(ora.pg, "/social/@lee") == 200, f"said {kept!r}; rows {kept_rows}")
        before = on_home(ora.pg, lee_post)
        down = answer("post", lee_post, "down")
        rows = db("select state from social_reports where kind = 'post' and target = ?", (lee_post,))
        seen = {"on ora's home before": before, "on ora's home": on_home(ora.pg, lee_post),
                "ora at the post": status(ora.pg, f"/social/p/{lee_post}"),
                "ora at its drawing's link": status(ora.pg, f"/s/{lee_sk}"),
                "kept": bool(db("select 1 from social_posts where public_id = ?", (lee_post,))),
                "withheld": db("select visibility from skribl_posts where public_id = ?", (lee_sk,))[0][0],
                "explore's report": skribl_states(lee_sk)}
        lpg = lee.pg
        lpg.goto(BASE + "/social/")
        lpg.wait_for_timeout(600)
        lee_home = lpg.evaluate("(id) => { const c = document.querySelector('.post-card[data-post=\"' + id + '\"]'); return c ? (c.querySelector('.post-down') || {}).textContent || '' : null; }", lee_post)
        lpg.goto(BASE + f"/social/p/{lee_post}")
        lpg.wait_for_timeout(500)
        lee_page = lpg.evaluate("() => (document.querySelector('.post-down') || {}).textContent || ''")
        NOTE = "Taken down: it broke the rules. Only you can see it."
        check("Take it down hides a post from everybody else at once (Home, its page, its drawing's link page), withholds its"
              " drawing in Skribl, keeps a copy, and closes its reports; its maker sees it, on Home and on its page, saying"
              " Taken down: it broke the rules",
              down == "Taken down. It’s hidden for everybody, and a copy is kept." and rows == [("taken_down",)]
              and seen == {"on ora's home before": True, "on ora's home": False, "ora at the post": 404,
                           "ora at its drawing's link": 404, "kept": True, "withheld": "withheld",
                           "explore's report": [("closed",)]} and lee_home == NOTE and lee_page == NOTE,
              f"said {down!r}; rows {rows}; {seen}; lee's home {lee_home!r}; page {lee_page!r}")
        dn = answer("drawing", lee_d, "down")
        sk_rows = skribl_states(lee_d)
        left = pg.evaluate("(ts) => ts.filter(t => document.querySelector('[data-rep][data-target=\"' + t + '\"]'))",
                           [lee_post, lee_d, lee_pub])
        lpg.goto(BASE + f"/social/b/{lee_d}")
        lpg.wait_for_timeout(500)
        lee_d_page = lpg.evaluate("() => (document.querySelector('.post-down') || {}).textContent || ''")
        check("a drawing reported for a child's safety, opened and taken down, is withheld in Skribl and gone for everybody"
              " else; its maker sees the note on its page; what Explore reported is closed with it, and nothing answered"
              " stays on Your Reports",
              dn.startswith("Taken down.") and db("select visibility from skribl_posts where public_id = ?", (lee_d,))[0][0] == "withheld"
              and status(ora.pg, f"/social/b/{lee_d}") == 404 and lee_d_page == NOTE
              and db("select state from social_reports where target = ?", (lee_d,)) == [("taken_down",)]
              and sk_rows == [("closed",)] and on_explore == [202, 202] and left == [],
              f"said {dn!r}; Explore's reports {on_explore}, now {sk_rows}; still on Your Reports {left};"
              f" page {lee_d_page!r}")
        mc = mira.client()
        mc.get("/social/reports")
        oc.get("/social/")
        guard = {"no token": mc._req("POST", "/social/reports/down", body=None, headers={})[0],
                 "not an admin": oc._req("POST", "/social/reports/keep", body=None,
                                         headers={"X-Social-CSRF": oc.token or ""})[0]}
        check("its answers need an admin (anybody else: 404) and the page's token (403)",
              guard == {"no token": 403, "not an admin": 404}, f"{guard}")

    # ------------------------------------------------------------------ 12
    if part(12, "a person taken down: nobody to everybody else; they see their own, and share nothing new"):
        mira = admin(b)
        ora = someone(b, "ora", "Ora Quinn")
        zoe = someone(b, "zoe", "Zoe Brand")
        st, j = make_post(zoe, "Section 12, Zoe's post", seed=121)
        zoe_post = j.get("post")
        st_d, zoe_d = pad(zoe, "Section 12, Zoe's drawing", "public", 122)
        oc = ora.client()
        oc.get("/social/")
        oc.post_json("/social/report", {"kind": "person", "target": "zoe", "reason": "fake"})
        zpub = pid_of("zoe")[1]
        pg = mira.pg
        pg.goto(BASE + "/social/reports")
        pg.wait_for_timeout(500)
        with pg.expect_navigation(timeout=15000):
            pg.click(f"[data-rep][data-kind='person'][data-target='{zpub}'] form[action$=down] button")
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/explore")
        npg.wait_for_timeout(400)
        others = {"ora: profile": status(ora.pg, "/social/@zoe"), "ora: post": status(ora.pg, f"/social/p/{zoe_post}"),
                  "ora: drawing": status(ora.pg, f"/social/b/{zoe_d}"), "ora: home": "zoe" in home(ora.pg),
                  "signed out: listing": zoe_d in [i["id"] for i in (api(npg, "/api/skribls?limit=100")[1] or {}).get("items", [])],
                  "signed out: link page": status(npg, f"/s/{zoe_d}")}
        close_ctx(nctx, npg)
        zpg = zoe.pg
        zpg.goto(BASE + "/social/@zoe")
        zpg.wait_for_timeout(500)
        own = zpg.evaluate("() => (document.querySelector('.prof-down') || {}).textContent || ''")
        posted = make_post(zoe, "Section 12, after", seed=123)
        words = zpg.evaluate("() => { const w = document.querySelector('[data-word=taken_down]'); return w ? w.textContent : null; }") \
            if zpg.goto(BASE + "/social/") else None
        check("taken down, a person is nobody to everybody else: their profile, posts and drawings, on the site's pages and"
              " Skribl's, signed in or out",
              others == {"ora: profile": 404, "ora: post": 404, "ora: drawing": 404, "ora: home": False,
                         "signed out: listing": False, "signed out: link page": 404}, f"{others}")
        check("they can still sign in and see their own, with the note, and nothing new is shared from the account"
              " (refused kindly, in its own words)",
              own == "Your profile was taken down: it broke the rules. Only you can see it, and what you made."
              and posted == (403, {"error": "taken_down"})
              and words == "Your account was taken down, so nothing new can be shared from it.",
              f"own {own!r}; posted {posted}; words {words!r}")

    # ------------------------------------------------------------------ 13
    if part(13, "Skribl's seams for a host's own reports page: list_reports and close_reports"):
        import ast as _ast
        init = (ROOT / "skribl" / "__init__.py").read_text(encoding="utf-8")
        public = next((_ast.literal_eval(n.value) for n in _ast.parse(init).body if isinstance(n, _ast.Assign)
                       and any(getattr(t, "id", None) == "__all__" for t in n.targets)), [])
        guide = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
        check("Skribl exports list_reports and close_reports and docs/INTEGRATION.md documents them",
              {"list_reports", "close_reports"} <= set(public) and "## Your own reports page" in guide
              and "list_reports(" in guide and "close_reports(" in guide, f"exported {[n for n in public if 'report' in n]}")
        kim = someone(b, "kim", "Kim Ito")
        st1, a = pad(kim, "Section 13, reported twice", "public", 131)
        st2, c = pad(kim, "Section 13, a child's safety", "public", 132)
        st3, d = pad(kim, "Section 13, to close", "public", 133)
        nctx, npg = browser_as(b, None)
        npg.goto(BASE + "/social/explore")
        npg.wait_for_timeout(400)
        npg.evaluate("""async ([a, c, d]) => { await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
          const tok = decodeURIComponent((document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '');
          const go = (id, reason, note) => fetch('/api/skribls/' + id + '/report', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': tok }, body: JSON.stringify({ reason, note }) });
          await go(a, 'spam', 'once'); await go(c, 'child_safety', null); await go(d, 'other', null); }""", [a, c, d])
        close_ctx(nctx, npg)
        con = sqlite3.connect(DB, timeout=10)     # a second reporter for `a`, as Skribl's queue would hold one
        try:
            con.execute("insert into skribl_reports (post_id, reason, note, reporter_hash, state, created_at)"
                        " select post_id, 'abuse', null, reporter_hash || '-2', 'open', created_at from skribl_reports"
                        " where post_id = (select id from skribl_posts where public_id = ?)", (a,))
            con.commit()
        finally:
            con.close()
        probe = subprocess.run([sys.executable, "-c", (
            "import json; from app import create_app; import skribl; app = create_app()\n"
            "with app.app_context():\n"
            "    got = skribl.list_reports(limit=500)\n"
            f"    closed = skribl.close_reports({d!r}); none = skribl.close_reports('nothinghere')\n"
            "    skribl.models.session().commit()\n"
            "    print(json.dumps({'got': got, 'closed': closed, 'none': none}))")],
            cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
        try:
            out = json.loads(probe.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            out = {"got": [], "closed": None, "none": None, "err": (probe.stderr or probe.stdout)[-300:]}
        mine = [g for g in out["got"] if g["id"] in (a, c, d)]
        order = [g["id"] for g in mine]
        ga = next((g for g in mine if g["id"] == a), {})
        still = db("select r.state from skribl_reports r join skribl_posts p on p.id = r.post_id where p.public_id = ?", (d,))
        vis = db("select visibility from skribl_posts where public_id = ?", (d,))[0][0]
        check("list_reports gives a group per drawing, a child's safety first and then the most reported, with its reasons,"
              " notes, count and times, naming nobody; close_reports closes one drawing's reports, takes nothing down,"
              " and answers 0 for none",
              order == [c, a, d] and ga.get("count") == 2 and ga.get("reasons") == {"spam": 1, "abuse": 1}
              and ga.get("notes") == ["once"] and ga.get("child_safety") is False and ga.get("first") and ga.get("latest")
              and not any("reporter" in k for g in mine for k in g)
              and next((g for g in mine if g["id"] == c), {}).get("child_safety") is True
              and out["closed"] == 1 and out["none"] == 0 and still == [("closed",)] and vis == "public",
              f"order {order} want {[c, a, d]}; a {ga}; closed {out.get('closed')}, none {out.get('none')}; d now {still} {vis};"
              f" {out.get('err', '')}")

    # ------------------------------------------------------------------ 14
    if part(14, "the Reports page and the notes: words at 4.5:1, targets 44px; phone and desk, light and dark"):
        mira = admin(b)
        lee = someone(b, "lee", "Lee Varga")
        ora = someone(b, "ora", "Ora Quinn")
        st, j = make_post(lee, "Section 14, Lee's post", seed=141)
        lee_post = j.get("post")
        st_d, lee_d = pad(lee, "Section 14, Lee's drawing", "public", 142, card=True)
        oc = ora.client()
        oc.get("/social/")
        oc.post_json("/social/report", {"kind": "drawing", "target": lee_d, "reason": "child_safety", "note": "Please look"})
        oc.post_json("/social/report", {"kind": "post", "target": lee_post, "reason": "spam", "note": "Again and again"})
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                cctx, cpg = browser_as(b, mira, screen=screen, scheme=scheme)
                cpg.goto(BASE + "/social/reports")
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "reports")] = cpg.evaluate(READ, "main")
                cpg.goto(BASE + "/social/you")
                cpg.wait_for_timeout(500)
                cpg.evaluate("() => document.getElementById('repTitle').scrollIntoView({ block: 'center' })")
                cpg.wait_for_timeout(300)
                seen[(screen, scheme, "settings")] = cpg.evaluate(READ, "main")
                close_ctx(cctx, cpg)
        con = sqlite3.connect(DB, timeout=10)
        try:
            con.execute("update social_posts set taken_down_at = '2026-01-01 00:00:00' where public_id = ?", (lee_post,))
            con.commit()
        finally:
            con.close()
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                cctx, cpg = browser_as(b, lee, screen=screen, scheme=scheme)
                cpg.goto(BASE + f"/social/p/{lee_post}")
                cpg.wait_for_timeout(700)
                seen[(screen, scheme, "a post taken down")] = cpg.evaluate(READ, "main")
                close_ctx(cctx, cpg)
        con = sqlite3.connect(DB, timeout=10)
        try:
            con.execute("update social_posts set taken_down_at = null where public_id = ?", (lee_post,))
            con.commit()
        finally:
            con.close()
        low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
        small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
        lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
        check("every word on Your Reports (a child's safety's card among them), Settings' Reports and a post its maker sees"
              " taken down reads at 4.5:1 or more on what is painted behind it, and every control is 44px or more each way:"
              " phone and desk, light and dark",
              not low and not small and all(v["read"] >= 3 for v in seen.values()),
              f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small: {small[:3]};"
              f" each {[(' '.join(k), v['read']) for k, v in seen.items()]}")

    # ------------------------------------------------------------------ 15
    if part(15, "the rules: three pages anybody can read, each a draft, each linking the others; Join and Settings link them"):
        mira = admin(b)
        PILLS = "() => [...document.querySelectorAll('.legal-nav a')].map(a => [a.textContent, new URL(a.href).pathname, a.getAttribute('aria-current')])"
        HEADS = "() => [...document.querySelectorAll('.legal h2')].map(h => h.textContent)"
        RULES = [("/social/terms", "Terms"), ("/social/privacy", "Privacy"), ("/social/rules", "Community rules")]
        WANT_HEADS = {
            "Terms": ["Your drawings are yours", "Who can join", "Be kind", "When something is reported"],
            "Privacy": ["What we keep", "What we don’t do", "Who sees what", "When you leave"],
            "Community rules": ["Be kind", "Keep children safe", "Be yourself", "Share what you made", "If something breaks the rules"]}
        DRAFT = "A draft, in plain words. A lawyer reads it before Skribl opens to everyone."
        nctx, npg = browser_as(b, None)
        pages = {}
        for path, name in RULES:
            st = status(npg, path)
            npg.wait_for_timeout(200)
            pages[name] = {"status": st, "h1": npg.evaluate("() => (document.querySelector('h1') || {}).textContent"),
                           "draft": npg.evaluate("() => (document.querySelector('.legal-draft') || {}).textContent"),
                           "pills": npg.evaluate(PILLS), "heads": npg.evaluate(HEADS)}
        close_ctx(nctx, npg)
        pills_ok = all(p["pills"] == [[n, path, "page" if n == name else None] for path, n in RULES]
                       for name, p in pages.items())
        check("the rules are three pages anybody can read, signed out too, each a draft in plain words, each with the"
              " pills to the others (its own marked), Terms in the mock's own words",
              all(p["status"] == 200 and p["h1"] == name and p["draft"] == DRAFT and p["heads"] == WANT_HEADS[name]
                  for name, p in pages.items()) and pills_ok,
              f"{pages}")
        FOOT = "() => [...document.querySelectorAll('.legal-foot a')].filter(a => a.getClientRects().length).map(a => [a.textContent, new URL(a.href).pathname])"
        jctx, jpg = browser_as(b, None)
        jpg.goto(cli("invite"))
        jpg.wait_for_timeout(600)
        joined = jpg.evaluate(FOOT)
        close_ctx(jctx, jpg)
        pg = mira.pg
        pg.goto(BASE + "/social/you")
        pg.wait_for_timeout(500)
        settings = pg.evaluate(FOOT)
        want = [[n, path] for path, n in RULES]
        check("Join (from an invite) and Settings each link all three, at their foot", joined == want and settings == want,
              f"join {joined}; settings {settings}")

    # ------------------------------------------------------------------ 16
    if part(16, "the rules pages: words at 4.5:1, targets 44px; phone and desk, light and dark"):
        seen = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                cctx, cpg = browser_as(b, None, screen=screen, scheme=scheme)
                for path in ("/social/terms", "/social/privacy", "/social/rules"):
                    cpg.goto(BASE + path)
                    cpg.wait_for_timeout(400)
                    seen[(screen, scheme, path.rsplit("/", 1)[1])] = cpg.evaluate(READ, "main")
                cpg.goto(cli("invite"))
                cpg.wait_for_timeout(600)
                seen[(screen, scheme, "join's rules")] = cpg.evaluate(READ, ".legal-foot")
                close_ctx(cctx, cpg)
        low = [(k, v["low"]) for k, v in seen.items() if v["low"]]
        small = [(k, v["small"]) for k, v in seen.items() if v["small"]]
        lowest = min((v["lowest"], " ".join(k)) for k, v in seen.items())
        check("every word on the three rules pages and in Join's rules row reads at 4.5:1 or more on what is"
              " painted behind it, and every control is 44px or more each way: phone and desk, light and dark",
              not low and not small and all(v["read"] >= 3 for v in seen.values()),
              f"{sum(v['read'] for v in seen.values())} read, the lowest {lowest}; under 4.5: {low[:3]}; small: {small[:3]};"
              f" each {[(' '.join(k), v['read']) for k, v in seen.items()]}")

    # ------------------------------------------------------------------ 17
    if part(17, "no page errors, no console errors and no CSP violations"):
        for who in list(_people.values()):
            ERRS.extend(f"csp: {v}" for v in who.csp())
        check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
              not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
