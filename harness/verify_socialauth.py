#!/usr/bin/env python3
"""Sign-in at /social: invite-only, with passkeys (docs/SOCIAL-SITE.md, phase 1,
piece 2; the owner's "all yes", Nov 10).

Through the demo's own app (app.py), booted here with what sign-in needs:
CSRF on (the site's people post from the Pad as themselves only then), a
first-invite code, the demo's stand-in identity with its key, and one trusted
proxy, so each section speaks from an address of its own (X-Forwarded-For)
and no section spends another's limits. Driven at http://localhost:<port>,
never 127.0.0.1: a passkey cannot belong to an IP address. Passkeys are made
and used by Chromium's own virtual authenticator (CDP WebAuthn), resident
keys and user verification on, as Face ID or Windows Hello would be.

   1. THE FIRST PERSON: SKRIBL_SOCIAL_FIRST_INVITE lets the first person in,
      as an admin, while the site has nobody, and never again; the code is
      in no log and no table (its hash is).
   2. JOIN: an invite link (from the CLI); 13 or older asked for kindly and
      required by the server; the handle's rules; a passkey made; signed in,
      You in the bar and on the rail (leading to their profile, piece 3).
   3. LINKS THAT DO NOT WORK: used, run out, revoked, never made: one kind
      card for all, one answer from the server.
   4. SIGN OUT, SIGN IN: nothing typed; the sign count stored and checked;
      user verification required; a new session id at sign-in.
   5. ONE SKRIBL, SHARED: the Pad posts as the signed-in person (the listing
      and the Gallery name them); signed out, the demo identity still works.
   6. INVITES ARE AN ADMIN'S: a join link and a recovery link, shown once;
      to anybody else the page is a 404 no different from a missing page.
   7. A RECOVERY LINK adds a passkey to the account it was made for, once.
   8. PASSKEYS ON YOU: rename; remove one, never the last; never another's.
   9. SIGN OUT EVERYWHERE ends another browser's session, and a copied cookie.
  10. DELETE MY ACCOUNT: what goes and what stays said first; the handle typed
      to confirm; the person, their passkeys and invites really gone.
  11. LIMITS: sign-ins, joins, link checks per address, and tries per invite,
      answer 429 past the limit.
  12. A STATE-CHANGING REQUEST WITHOUT THE TOKEN, or from another origin, is
      refused, and changes nothing.
  13. THE COOKIE: HttpOnly, SameSite=Lax, path /, Secure over HTTPS, 30 days,
      signed.
  14. THE SITE'S OWN MIGRATION CHAIN: empty to head on SQLite with its own
      version table, Skribl's chain untouched in either order, no drift;
      gunicorn (as Render starts it) runs it, and one that fails is logged
      and the demo serves on.
  15. THE NEW SCREENS: every word at 4.5:1 on what is painted behind it,
      every target 44px, every text field 16px, phone and desk, light and dark.
  16. NO PAGE ERRORS AND NO CSP VIOLATIONS on any of it.

The layers (the site imports nothing of Skribl's but its documented names, and
Skribl never imports the site) stay verify_social's, section 8.

SOCIALAUTH_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Sign-in at /social".
"""
import base64
import hashlib
import json
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
PART = os.environ.get("SOCIALAUTH_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALAUTH {n} — {label}")
    return True


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence sign-in works.")
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


# ---- the demo's own server, with what sign-in needs ---------------------------
TMP = tempfile.mkdtemp(prefix="socialauth-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
DEMO_KEY = "demo-key-" + secrets.token_urlsafe(12)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialauth-" + secrets.token_hex(8),
           SKRIBL_CSRF_PROTECT="1", SKRIBL_SOCIAL_FIRST_INVITE=FIRST, SKRIBL_STAND_IN="0",
           SKRIBL_TRUSTED_PROXIES="1", SKRIBL_DEMO_IDENTITY="demo-owner", SKRIBL_DEMO_LOGIN_KEY=DEMO_KEY,
           SKRIBL_DEMO_IDENTITY_NAME="Demo Owner", SKRIBL_DEMO_INSECURE_COOKIE="1",
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           # The site's own address, so a passkey from any other is refused
           # (section 18). Every other section is at localhost, as before.
           SKRIBL_SOCIAL_HOSTS="localhost")
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES"):
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
    return f"10.{20 + _addr[0] // 250}.{_addr[0] % 250}.7"


# ---- the database and the CLI, as an operator has them -------------------------

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
    """`flask --app app social ...`, as from Render's shell: the last line it printed."""
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", *args, "--base", BASE],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    if out.returncode:
        return None, (out.stderr or out.stdout).strip()[-300:]
    return out.stdout.strip().splitlines()[-1], out.stderr


def code_of(link):
    return link.split("#", 1)[1] if link and "#" in link else ""


def hashed(code):
    return hashlib.sha256(("invite|" + code).encode()).hexdigest()


# ---- a client without a browser (limits, tokens, cookie flags) ----------------

class Client:
    def __init__(self, xff=None, origin=BASE):
        self.jar = CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                              _NoRedirect())
        self.xff = xff or address()
        self.origin = origin
        self.token = None

    def _req(self, method, path, body=None, headers=None, form=None):
        h = {"X-Forwarded-For": self.xff}
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
            with self.op.open(req, timeout=20) as r:
                return r.status, r.headers, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8", "replace")

    def get(self, path, headers=None):
        st, hd, text = self._req("GET", path, headers=headers)
        m = re.search(r'<meta name="social-csrf" content="([^"]+)"', text)
        if m:
            self.token = m.group(1)
        return st, hd, text

    def post(self, path, body=None, token=True, headers=None, form=None):
        h = dict(headers or {})
        if token and body is not None:
            h["X-Social-CSRF"] = self.token if token is True else token
        st, hd, text = self._req("POST", path, body=body, headers=h, form=form)
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def cookie(self, name="social_session"):
        return next((c for c in self.jar if c.name == name), None)

    def post_chunked(self, path, body):
        """A JSON post that declares no length (Transfer-Encoding: chunked):
        only what is read can tell how big it is."""
        raw = json.dumps(body).encode()
        h = {"X-Forwarded-For": self.xff, "Content-Type": "application/json", "Origin": self.origin,
             "X-Social-CSRF": self.token}
        req = urllib.request.Request(BASE + path, data=iter([raw[i:i + 8192] for i in range(0, len(raw), 8192)]),
                                     method="POST", headers=h)
        try:
            with self.op.open(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code


import urllib.parse  # noqa: E402


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


# ---- a browser with a passkey -------------------------------------------------

class Person:
    """One browser (a context, one page, its own virtual authenticator), from
    an address of its own."""

    def __init__(self, b, screen="phone", scheme="light", uv=True):
        self.xff = address()
        opts = dict(PHONE if screen == "phone" else DESK)
        self.ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": self.xff}, **opts)
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
            "hasUserVerification": True, "isUserVerified": uv,
            "automaticPresenceSimulation": True}})["authenticatorId"]
        self.handle = None

    def creds(self):
        return self.cdp.send("WebAuthn.getCredentials", {"authenticatorId": self.aid})["credentials"]

    def csp(self):
        try:
            return self.pg.evaluate("() => window.__csp || []")
        except Exception:
            return []

    def close(self):
        ERRS.extend(f"csp: {v}" for v in self.csp())
        self.ctx.close()

    def who(self):
        """The handle signed in here, as /social/you says it, or None."""
        r = self.ctx.request.get(BASE + "/social/you", max_redirects=0)
        if r.status != 200:
            return None
        m = re.search(r'<p class="page-sub">@([A-Za-z0-9_]+)</p>', r.text())
        return m.group(1) if m else None

    def cookie(self):
        return next((c for c in self.ctx.cookies(BASE) if c["name"] == "social_session"), None)


def session_data(cookie_value):
    """What the site's signed cookie carries (its payload is readable; its
    signature is what makes it the site's). itsdangerous marks a compressed
    payload with a leading dot."""
    import zlib
    try:
        packed = cookie_value.startswith(".")
        payload = cookie_value.lstrip(".").split(".")[0]
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        return json.loads(zlib.decompress(raw) if packed else raw)
    except Exception:
        return None


def pw_cookie(c):
    """A cookie Playwright read, in the shape it takes one back."""
    return {k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly", "sameSite",
                                                "secure", "expires")}


def link_state(pg):
    """A link page, once its code has been checked."""
    try:
        pg.wait_for_function("() => { const c = document.querySelector('[data-link]');"
                             " return !!c && !c.classList.contains('is-checking'); }", timeout=15000)
    except Exception:
        pass
    return pg.evaluate("""() => { const c = document.querySelector('[data-link]'); if (!c) return null;
        const ok = c.querySelector('[data-link-ok]'), gone = c.querySelector('[data-link-gone]');
        const first = c.querySelector('[data-link-first]'), who = c.querySelector('[data-link-handle]');
        return { ok: !!ok && !ok.hidden, gone: !!gone && !gone.hidden, first: !!first && !first.hidden,
                 handle: who ? who.textContent : null, checking: c.classList.contains('is-checking'),
                 words: gone && !gone.hidden ? gone.innerText.replace(/\\s+/g, ' ').trim() : '' }; }""")


SETTLED = """([start, sel]) => { try {
  if (location.pathname !== start) return true;
  const btn = document.querySelector(sel); if (!btn || btn.disabled) return false;
  return [...document.querySelectorAll('[data-err], [data-say], [data-link-gone]')].some(e => !e.hidden && e.textContent.trim());
} catch (e) { return false; } }"""


def press(p, sel, start):
    """Press a passkey button and wait for it to land somewhere or say why not."""
    p.pg.click(sel)
    try:
        p.pg.wait_for_function(SETTLED, arg=[start, sel], timeout=20000)
    except Exception:
        pass
    p.pg.wait_for_timeout(250)
    try:
        said = p.pg.evaluate("""() => ({ path: location.pathname,
            errs: Object.fromEntries([...document.querySelectorAll('[data-err]')].filter(e => !e.hidden)
                  .map(e => [e.getAttribute('data-err'), e.textContent.trim()])),
            say: [...document.querySelectorAll('[data-say]')].filter(e => !e.hidden).map(e => e.textContent.trim()).join(' ') })""")
    except Exception:
        said = {"path": None, "errs": {}, "say": ""}
    return said


def join(p, link, name, handle, age=True):
    p.pg.goto(link)
    state = link_state(p.pg)
    if not state or not state["ok"]:
        return {"path": None, "state": state, "errs": {}, "say": ""}
    p.pg.fill("#joinName", name)
    p.pg.fill("#joinHandle", handle)
    if age:
        p.pg.check("#joinAge")
    said = press(p, "form[data-passkey] button[type=submit]", "/social/join")
    said["state"] = state
    if said["path"] == "/social/":
        p.handle = handle
    return said


def signin(p):
    p.pg.goto(BASE + "/social/signin")
    return press(p, "[data-passkey=signin]", "/social/signin")


def text_of(pg, sel):
    """The first `sel`'s words, or "" when the page has none: a page that is
    not the one expected must read as a red row, not stop the suite."""
    try:
        loc = pg.locator(sel)
        return loc.first.text_content(timeout=3000) if loc.count() else ""
    except Exception:
        return ""


def sign_out_here(p, everywhere=False):
    """Press You's Sign out (or Sign out everywhere) and land wherever the site
    sends: a sign-out that does not happen shows red in its own row, rather
    than stopping the suite while it waits for a page that never comes."""
    p.pg.goto(BASE + "/social/you")
    sel = "form[action$='/social/signout" + ("/everywhere" if everywhere else "") + "'] button"
    try:
        with p.pg.expect_navigation(timeout=15000):
            p.pg.click(sel, timeout=5000)
    except Exception:
        pass
    try:
        p.pg.wait_for_load_state()
    except Exception:
        pass
    return p.pg.url


def new_member(b, handle, name=None, **kw):
    """Somebody who joined through a CLI-made invite, signed in, in a browser of their own."""
    link, _ = cli("invite")
    p = Person(b, **kw)
    said = join(p, link, name or handle.title(), handle)
    return p, said


_admin = {}


def admin(b):
    """The site's admin: the first person, made through the first invite while
    nobody is here (section 1 does it with its rows; a section run alone does
    it here), or a member made an admin in the table where somebody already is."""
    if "p" in _admin:
        return _admin["p"]
    p = Person(b)
    if not db("select id from social_people limit 1"):
        said = join(p, BASE + "/social/join#" + FIRST, "Mira Okafor", "mira")
    else:
        link, _ = cli("invite")
        said = join(p, link, "Admin Person", "admin_" + secrets.token_hex(3))
        db("update social_people set is_admin = 1 where handle_key = ?", (p.handle.lower(),), write=True)
    _admin["p"] = p
    _admin["said"] = said
    return p


def options(c, path, body):
    return c.post(path, body)


# ---- what is painted: the words, the targets, the fields ------------------------
READ = """() => {
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
  // The site's own words and controls: Skribl's player and Gallery section
  // inside a page keep their own (verify_inline, verify_gallery).
  // Skribl's own parts keep their own (its player's box and its line under it: verify_inline's),
  // as verify_socialposts reads them; Home holds drawings since the site's people's show there.
  const SKRIBLS = '.skribl-inline, .skribl-inline-line, #skriblGallery';
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99 };
  const roots = [...document.querySelectorAll('main, header.top, nav.nav')];
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
  document.querySelectorAll('a[href], button, summary, label.check, input:not([type=hidden]):not([type=checkbox])').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, #makeSheet, ' + SKRIBLS)) return;
    if (e.matches('input') && e.closest('.at')) { const a = e.closest('.at').getBoundingClientRect();
      if (a.height < 44) out.small.push('field ' + (e.id || e.name) + ' ' + Math.round(a.height)); }
    else { const r = e.getBoundingClientRect();
      if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
  });
  document.querySelectorAll('input[type=text], input:not([type]), textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""


with sync_playwright() as p_:
    b = p_.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the first person: the first invite, while nobody is here, makes an admin, once"):
        nobody = not db("select id from social_people limit 1")
        stranger = Person(b)
        stranger.pg.goto(BASE + "/social/join#" + "x" * len(FIRST))
        wrong = link_state(stranger.pg)
        stranger.pg.goto(BASE + "/social/join#" + FIRST)
        right = link_state(stranger.pg)
        check("with nobody here, the first-invite code opens the join form, saying this account will look after the"
              " site; a code that is not it gets the kind card that the link does not work",
              nobody and right and right["ok"] and right["first"] and not right["gone"]
              and wrong and wrong["gone"] and not wrong["ok"],
              f"nobody {nobody}; the code {right}; another {wrong}")
        stranger.close()
        owner = admin(b)
        said = _admin.get("said") or {}
        made = owner.creds()
        rows = db("select handle, is_admin, display_name from social_people")
        inv = owner.ctx.request.get(BASE + "/social/invites", max_redirects=0)
        bar = owner.pg.evaluate("() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')]"
                                ".map(e => e.querySelector('.tab-name') ? e.querySelector('.tab-name').textContent.trim() : e.getAttribute('aria-label'))")
        check("joining with it makes the first person an admin: a resident passkey for this address made with the"
              " person verified, signed in on Home, You in the bar, and Invites theirs to open",
              said.get("path") == "/social/" and len(made) == 1 and made[0]["isResidentCredential"]
              and made[0]["rpId"] == "localhost" and rows == [("mira", 1, "Mira Okafor")]
              and inv.status == 200 and bar[-1:] == ["You"] and owner.who() == "mira",
              f"landed {said.get('path')} {said.get('say')!r}; credentials {[(c['rpId'], c['isResidentCredential']) for c in made]};"
              f" people {rows}; invites {inv.status}; bar {bar}")
        late = Person(b)
        late.pg.goto(BASE + "/social/join#" + FIRST)
        again = link_state(late.pg)
        c = Client()
        c.get("/social/signin")
        st_check, j_check = c.post("/social/join/check", {"code": FIRST})
        st_opt, j_opt = c.post("/social/join/options", {"code": FIRST, "name": "Late", "handle": "late_one", "age13": True})
        check("never again: once somebody is here the code is a link that does not work, in a new browser too"
              " (the check answers 404, a join begun with it 410), and nobody else is made",
              again and again["gone"] and not again["ok"] and st_check == 404 and st_opt == 410
              and len(db("select id from social_people")) == 1,
              f"page {again}; check {st_check} {j_check}; options {st_opt} {j_opt}")
        late.close()
        spent = db("select kind, used_at is not null, used_by_id from social_invites where code_hash = ?", (hashed(FIRST),))
        raw = open(DB, "rb").read()
        logged = open(LOG, encoding="utf-8", errors="replace").read()
        check("the code is in no table and no log line: its SHA-256 is the spent invite's, used by the first person",
              len(spent) == 1 and spent[0][0] == "join" and spent[0][1] == 1 and FIRST.encode() not in raw
              and FIRST not in logged,
              f"spent rows {spent}; in the database {FIRST.encode() in raw}; in the log {FIRST in logged}")

    # ------------------------------------------------------------------ 2
    if part(2, "join with an invite: 13 or older, the handle's rules, a passkey, signed in"):
        owner = admin(b)
        link, said_cli = cli("invite")
        check("`flask social invite` prints a whole join link on the address it is given, its code after the #",
              bool(link) and link.startswith(BASE + "/social/join#") and len(code_of(link)) >= 20,
              f"{link!r} {said_cli[-120:] if said_cli else ''}")
        p = Person(b)
        young = join(p, link, "Sam Young", "sam_young", age=False)
        check("the page asks kindly for 13 or older before any passkey is made, and makes none without it",
              young.get("path") == "/social/join" and "13" in young["errs"].get("age13", "")
              and "welcome to look around" in young["errs"].get("age13", "") and not p.creds(),
              f"{young}; credentials {len(p.creds())}")
        c = Client()
        c.get("/social/signin")
        code = code_of(link)
        st_age, j_age = c.post("/social/join/options", {"code": code, "name": "Sam", "handle": "sam_young", "age13": False})
        st_bad, j_bad = c.post("/social/join/options", {"code": code, "name": "Sam", "handle": "9lives", "age13": True})
        st_res, j_res = c.post("/social/join/options", {"code": code, "name": "Sam", "handle": "Admin", "age13": True})
        st_tak, j_tak = c.post("/social/join/options", {"code": code, "name": "Sam", "handle": "MIRA", "age13": True})
        st_nam, j_nam = c.post("/social/join/options", {"code": code, "name": "‮evil", "handle": "sam_ok", "age13": True})
        fields = lambda j: (j or {}).get("fields", {}) if isinstance(j, dict) else {}
        check("the server has the last word: no 13-or-older, a handle that does not start with a letter, one kept"
              " for the site, one taken however it is written, a name with an invisible control: each refused",
              st_age == 400 and fields(j_age).get("age13") == "age"
              and st_bad == 400 and fields(j_bad).get("handle") == "handle_shape"
              and st_res == 400 and fields(j_res).get("handle") == "handle_reserved"
              and st_tak == 400 and fields(j_tak).get("handle") == "handle_taken"
              and st_nam == 400 and fields(j_nam).get("name") == "name_chars",
              f"age {st_age} {j_age}; shape {st_bad} {j_bad}; reserved {st_res} {j_res}; taken {st_tak} {j_tak}; name {st_nam} {j_nam}")
        p.pg.goto(link)
        link_state(p.pg)
        p.pg.fill("#joinName", "Sam Young")
        p.pg.fill("#joinHandle", "Mira")
        p.pg.check("#joinAge")
        taken = press(p, "form[data-passkey] button[type=submit]", "/social/join")
        check("a handle somebody has is said under its field, kindly, with the handle in it",
              "@Mira" in taken["errs"].get("handle", "") and "Try another" in taken["errs"].get("handle", ""),
              str(taken))
        good = join(p, link, "Sam Young", "sam_young")
        made = p.creds()
        bar = p.pg.evaluate("() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')].map(e => (e.querySelector('.tab-name') || e).textContent.trim())")
        spent = db("select i.used_at is not null, p.handle from social_invites i join social_people p on p.id = i.used_by_id"
                   " where i.code_hash = ?", (hashed(code),))
        check("a good join makes a resident passkey with the person verified, signs in on Home with You in the bar,"
              " and spends the invite on them",
              good.get("path") == "/social/" and len(made) == 1 and made[0]["isResidentCredential"]
              and bar[-1:] == ["You"] and p.who() == "sam_young" and spent == [(1, "sam_young")],
              f"{good}; credentials {len(made)}; bar {bar}; spent {spent}")
        # WHAT JOINING AGREES TO (the owner's "all yes" to A, Nov 12): the line
        # on Join, painted, in its words, just above the rules' row; and the
        # row of somebody who joined keeps which Terms (rules.TERMS_VERSION,
        # read from the module, never typed here) and when they pressed Join.
        TERMS_VERSION = re.search(r'^TERMS_VERSION = "([^"]+)"', (ROOT / "social" / "rules.py").read_text(encoding="utf-8"),
                                  re.M).group(1)
        agreed = db("select terms_version, terms_agreed_at is not null from social_people where handle_key = ?",
                    ("sam_young",))
        fresh, _ = cli("invite")
        q = Person(b)
        q.pg.goto(fresh)
        link_state(q.pg)
        line = q.pg.evaluate("""() => { const p = document.querySelector('.link-ok p.legal-agree'), n = document.querySelector('.link-ok .legal-foot');
            if (!p || !n || !p.getClientRects().length) return null;
            const r = p.getBoundingClientRect(), f = n.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { words: p.textContent.trim(), painted: !!at && (at === p || p.contains(at)),
                     gap: Math.round((f.top - r.bottom) * 10) / 10, px: parseFloat(getComputedStyle(p).fontSize) }; }""")
        q.close()
        check("Join says what joining agrees to, just above the rules (\"Joining means you agree to the Terms and the"
              " Community rules. Privacy says what we keep.\"), and the person's row keeps which Terms and when",
              bool(line) and line["painted"] and line["px"] >= 14 and 0 <= line["gap"] <= 8
              and line["words"] == "Joining means you agree to the Terms and the Community rules. Privacy says what we keep."
              and agreed == [(TERMS_VERSION, 1)],
              f"line {line}; row {agreed} (Terms {TERMS_VERSION})")
        desk = Person(b, screen="desk")
        desk.ctx.add_cookies([pw_cookie(p.cookie())])
        desk.pg.goto(BASE + "/social/")
        rail = desk.pg.evaluate("""() => { const y = document.querySelector('nav.nav .tab-you'); if (!y) return null;
            const r = y.getBoundingClientRect(), n = document.querySelector('nav.nav').getBoundingClientRect();
            return { who: y.querySelector('.tab-who') ? y.querySelector('.tab-who').innerText.replace(/\\s+/g, ' ').trim() : null,
                     foot: Math.round(n.bottom - r.bottom), href: y.getAttribute('href') }; }""")
        # You leads to the person's own profile since piece 3 (the account
        # page is its gear's, Settings); verify_socialprofile holds the rest.
        check("on a desk the rail's foot is You: the person's name and @handle, leading to their profile",
              bool(rail) and rail["who"] == "Sam Young @sam_young" and rail["href"] == "/social/@sam_young"
              and rail["foot"] < 60, str(rail))
        desk.close()
        nonadmin = p.ctx.request.get(BASE + "/social/invites", max_redirects=0)
        check("somebody who joined by invite is not an admin: Invites is a 404 to them",
              nonadmin.status == 404, str(nonadmin.status))
        _admin["member"] = p

    # ------------------------------------------------------------------ 3
    if part(3, "links that do not work: one kind card, one answer, whatever the reason"):
        owner = admin(b)
        used, _ = cli("invite")
        u = Person(b)
        join(u, used, "Used Once", "used_once")
        expired, _ = cli("invite")
        revoked, _ = cli("invite")
        owner.pg.goto(BASE + "/social/invites")
        rid = db("select public_id from social_invites where code_hash = ?", (hashed(code_of(revoked)),))[0][0]
        owner.pg.click(f"form[action$='/invites/{rid}/revoke'] button")
        owner.pg.wait_for_load_state()
        # Run out AFTER Invites was read: reading it deletes links that ran out
        # unused, and a deleted link is the never-made case, not this one.
        db("update social_invites set expires_at = '2020-01-01 00:00:00.000000' where code_hash = ?",
           (hashed(code_of(expired)),), write=True)
        ran_out = db("select count(*) from social_invites where code_hash = ? and used_at is null",
                     (hashed(code_of(expired)),))[0][0]
        never = BASE + "/social/join#" + secrets.token_urlsafe(16)
        rec_used, _ = cli("recover", "used_once")
        rv = Person(b)
        rv.pg.goto(rec_used)
        link_state(rv.pg)
        press(rv, "[data-passkey=recover]", "/social/recover")
        rv.close()
        seen, answers = {}, {}
        look = Person(b)
        c = Client()
        c.get("/social/signin")
        for name, link in (("used", used), ("expired", expired), ("revoked", revoked), ("never made", never),
                           ("recovery used", rec_used)):
            look.pg.goto(BASE + "/social/signin")
            look.pg.goto(link)
            seen[name] = link_state(look.pg)
            path = "/social/recover/check" if "/recover" in link else "/social/join/check"
            answers[name] = c.post(path, {"code": code_of(link)})
        words = {s["words"] for s in seen.values() if s}
        check("used, run out, revoked, never made, and a spent recovery link: each shows the one kind card"
              " (\"This link doesn't work anymore\", ask for a new one, Look around, Sign in), never the form",
              ran_out == 1 and all(s and s["gone"] and not s["ok"] for s in seen.values()) and len(words) == 1
              and "doesn’t work anymore" in next(iter(words)) and "Ask whoever sent it for a new one" in next(iter(words))
              and "Look around Blooby" in next(iter(words)),
              "; ".join(f"{k}: {v}" for k, v in seen.items())[:600])
        check("and the server answers each the same, 404 {\"error\": \"gone\"}: nothing tells a used code from one never made",
              all(st == 404 and j == {"error": "gone"} for st, j in answers.values()),
              str(answers))
        st_o, j_o = c.post("/social/join/options", {"code": code_of(used), "name": "Again", "handle": "again_x", "age13": True})
        check("a join begun on a spent invite is refused (410), and no person is made",
              st_o == 410 and not db("select id from social_people where handle_key = 'again_x'"), f"{st_o} {j_o}")
        look.close()
        u.close()

    # ------------------------------------------------------------------ 4
    if part(4, "sign out, and sign in with the passkey: nothing typed"):
        p, said = new_member(b, "nadia")
        before = p.cookie()
        sign_out_here(p)
        note = text_of(p.pg, ".note")
        # The sign-in page gives a signed-out browser a session id of its own
        # (its form's token is bound to it); the person is what must be gone.
        held = session_data((p.cookie() or {}).get("value", "")) or {}
        p.pg.goto(BASE + "/social/")
        bar = p.pg.evaluate("() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')].map(e => (e.querySelector('.tab-name') || e).textContent.trim())")
        was = session_data(before["value"]) if before else {}
        check("Sign out (a button) ends this browser's sign-in: the cookie no longer carries the person, the page"
              " says so kindly, the bar says Sign in, and You sends to the sign-in page",
              said.get("path") == "/social/" and (was or {}).get("p", "").startswith("site:") and "p" not in held
              and held.get("s") != (was or {}).get("s") and "signed out" in note
              and bar[-1:] == ["Sign in"] and p.who() is None,
              f"joined {said.get('path')}; cookie before {was} after {held}; note {note!r}; bar {bar}")
        p.pg.goto(BASE + "/social/signin")
        pre = session_data((p.cookie() or {}).get("value", ""))
        pre_token = p.pg.get_attribute("meta[name=social-csrf]", "content")
        back = signin(p)
        post = session_data((p.cookie() or {}).get("value", ""))
        stored = db("select k.sign_count from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'nadia'")
        auth = p.creds()[0]["signCount"]
        check("Sign in with a passkey, nothing typed (the passkey says whose it is): signed in on Home, and the sign"
              " count stored is the authenticator's, which went up",
              back.get("path") == "/social/" and p.who() == "nadia" and stored == [(auth,)] and auth >= 2,
              f"{back}; stored {stored}; authenticator {auth}")
        replay = p.ctx.request.post(BASE + "/social/signout/everywhere", form={"csrf": pre_token},
                                    headers={"Origin": BASE}, max_redirects=0)
        check("signing in made a new session id (no fixation): the cookie's id is not the one from before, and a"
              " token from before no longer works (403, still signed in)",
              bool(pre and post) and pre.get("s") != post.get("s") and post.get("p", "").startswith("site:")
              and replay.status == 403 and p.who() == "nadia",
              f"before {pre and pre.get('s')}; after {post and post.get('s')}; old token {replay.status}")
        db("update social_passkeys set sign_count = 100000 where person_id = (select id from social_people where handle_key = 'nadia')", write=True)
        sign_out_here(p)
        cloned = signin(p)
        check("an authenticator whose count did not go up (a copied key) is refused, kindly, and nobody is signed in",
              cloned.get("path") == "/social/signin" and "didn’t check out" in cloned["say"] and p.who() is None,
              str(cloned))
        db("update social_passkeys set sign_count = 0 where person_id = (select id from social_people where handle_key = 'nadia')", write=True)
        # USER VERIFICATION IS REQUIRED BY THE SERVER, not only asked of the
        # browser: the page's own options are made to ask for less, and an
        # authenticator that does not verify the person answers them.
        lazy = Person(b, uv=False)
        lazy.cdp.send("WebAuthn.addCredential", {"authenticatorId": lazy.aid, "credential": {
            k: v for k, v in p.creds()[0].items() if k in ("credentialId", "isResidentCredential", "rpId",
                                                             "privateKey", "userHandle", "signCount")}})
        lazy.pg.add_init_script("""(() => { const get = navigator.credentials.get.bind(navigator.credentials);
            navigator.credentials.get = (o) => { if (o && o.publicKey) o.publicKey.userVerification = 'discouraged'; return get(o); }; })();""")
        unverified = signin(lazy)
        check("a passkey answered without the person verified (no Face ID, no PIN) is refused by the server",
              unverified.get("path") == "/social/signin" and lazy.who() is None and "didn’t check out" in unverified["say"],
              str(unverified))
        lazy.close()
        # SOMEBODY WITH NO PASSKEY HERE YET (the owner's first evening, Nov
        # 10: an invite code taken for a passkey, Sign in pressed, and the
        # phone with nothing to offer). The words say where joining starts.
        stranger = Person(b)
        nothing = signin(stranger)
        check("Sign in with no passkey here yet says where joining starts: \"Haven’t joined yet? Open the invite"
              " link you were sent.\"",
              nothing.get("path") == "/social/signin" and stranger.who() is None and not stranger.creds()
              and "Haven’t joined yet? Open the invite link you were sent." in nothing["say"],
              str(nothing))
        stranger.close()
        p.close()

    # ------------------------------------------------------------------ 5
    if part(5, "one Skribl, shared: the Pad posts as the signed-in person; the demo identity still works"):
        import browsing  # noqa: E402

        def draw(pg):
            box = pg.locator("#canvas").bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            pg.mouse.move(cx - 100, cy)
            pg.mouse.down()
            for i in range(30):
                pg.mouse.move(cx - 100 + i * 7, cy + (i % 5) * 6)
                pg.wait_for_timeout(15)
            pg.mouse.up()
            pg.wait_for_timeout(400)

        def pad_post(ctx, title):
            """A drawing posted through the Pad's own Post sheet, ticked for the
            Gallery, by whoever `ctx`'s cookies say is signed in. A fresh
            browser carrying those cookies: the Pad keeps a draft of the last
            drawing, and a stroke over a kept drawing starts no new take."""
            fresh = b.new_context(**DESK, extra_http_headers={"X-Forwarded-For": address()})
            fresh.add_cookies([pw_cookie(c) for c in ctx.cookies(BASE)])
            try:
                return _pad_post(fresh, title)
            finally:
                fresh.close()

        def _pad_post(ctx, title):
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: ERRS.append(f"pad pageerror: {e}"))
            browsing.goto(pg, BASE, "/skribl-pad")
            pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} if (window.SkriblHints) window.SkriblHints.hide(); }")
            draw(pg)
            pg.click("#recordBtn")
            pg.wait_for_timeout(400)
            pg.click("#postBtn")
            pg.wait_for_timeout(500)
            pg.fill("#postTitleInput", title)
            if pg.evaluate("() => !!document.getElementById('postPublicInput')"):
                pg.click(".post-check")
            got = browsing.submit_post(pg)
            pg.close()
            return got

        def flip_post(ctx, title):
            """The same through Flip's own Post sheet (Pad and Flip move together)."""
            fresh = b.new_context(**DESK, extra_http_headers={"X-Forwarded-For": address()})
            fresh.add_cookies([pw_cookie(c) for c in ctx.cookies(BASE)])
            pg = fresh.new_page()
            pg.on("pageerror", lambda e: ERRS.append(f"flip pageerror: {e}"))
            try:
                browsing.goto(pg, BASE, "/flip")
                pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} if (window.SkriblHints) window.SkriblHints.hide(); }")
                box = pg.locator("#pad").bounding_box()
                cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                pg.mouse.move(cx - 100, cy)
                pg.mouse.down()
                for i in range(30):
                    pg.mouse.move(cx - 100 + i * 7, cy + (i % 5) * 6)
                    pg.wait_for_timeout(15)
                pg.mouse.up()
                pg.wait_for_timeout(400)
                pg.click("#postBtn")
                pg.wait_for_timeout(500)
                pg.fill("#postTitleInput", title)
                if pg.evaluate("() => !!document.getElementById('postPublicInput')"):
                    pg.click("#postSheet .post-check")
                with pg.expect_response(lambda r: r.request.method == "POST"
                                        and r.url.split("?")[0].endswith("/api/skribls"), timeout=20000) as got:
                    pg.click("#postSubmitBtn")
                return got.value.status
            except Exception as exc:
                return f"no post: {str(exc).splitlines()[0][:120]}"
            finally:
                fresh.close()

        def listed(title):
            with urllib.request.urlopen(BASE + "/api/skribls?limit=50", timeout=20) as r:
                items = json.loads(r.read().decode())["items"]
            return next((i for i in items if i.get("title") == title), None)

        p, _ = new_member(b, "priya", "Priya Raman", screen="desk")
        tag = secrets.token_hex(3)
        got = pad_post(p.ctx, "Priya's skribl " + tag)
        item = listed("Priya's skribl " + tag)
        pid = db("select public_id from social_people where handle_key = 'priya'")[0][0]
        author = (item or {}).get("author") or {}
        check("signed in to the site, the Pad's own Post sheet posts as the person: Skribl's listing names them,"
              " their public id (site:...) as the author, with their handle and name",
              got.get("status") == 201 and author.get("id") == pid and pid.startswith("site:")
              and author.get("username") == "priya" and author.get("display_name") == "Priya Raman",
              f"post {got.get('status')} {got.get('label')!r}; author {author}; person {pid}")
        flipped = flip_post(p.ctx, "Priya's flip " + tag)
        f_author = ((listed("Priya's flip " + tag) or {}).get("author") or {})
        check("and Flip's own Post sheet posts as them too (Pad and Flip move together)",
              flipped == 201 and f_author.get("id") == pid and f_author.get("username") == "priya",
              f"post {flipped}; author {f_author}")
        g = p.ctx.new_page()
        g.goto(BASE + "/social/explore")
        try:
            g.wait_for_function("(t) => [...document.querySelectorAll('#skriblGallery .tile')].some(x => x.textContent.includes(t))",
                                arg="Priya's skribl " + tag, timeout=15000)
        except Exception:
            pass
        card = g.evaluate("""(t) => { const tile = [...document.querySelectorAll('#skriblGallery .tile')].find(x => x.textContent.includes(t));
            return tile ? (tile.querySelector('.tauth') || tile).innerText.replace(/\\s+/g, ' ').trim() : null; }""",
                          "Priya's skribl " + tag)
        check("and the Gallery's card on the site's Explore says who drew it: their name and @handle",
              bool(card) and "Priya Raman" in card and "@priya" in card, str(card))
        g.close()
        sign_out_here(p)
        anon = pad_post(p.ctx, "Nobody's skribl " + tag)
        a_item = listed("Nobody's skribl " + tag)
        demo = b.new_context(**DESK, extra_http_headers={"X-Forwarded-For": address()})
        dpg = demo.new_page()
        dpg.goto(BASE + "/demo-login")
        dpg.fill("#key", DEMO_KEY)
        dpg.click("form[action='/demo-login'] button")
        dpg.wait_for_load_state()
        dgot = pad_post(demo, "Demo's skribl " + tag)
        d_item = listed("Demo's skribl " + tag)
        check("signed out of the site, the demo's own identity still works (its key posted at /demo-login, its"
              " posts its own), and with nobody signed in at all a post is nobody's",
              anon.get("status") == 201 and a_item is not None and (a_item.get("author") or {}).get("id") is None
              and dgot.get("status") == 201 and ((d_item or {}).get("author") or {}).get("id") == "demo-owner"
              and ((d_item or {}).get("author") or {}).get("display_name") == "Demo Owner",
              f"signed out {anon.get('status')} {(a_item or {}).get('author')}; demo {dgot.get('status')} {(d_item or {}).get('author')}")
        demo.close()
        p.close()

    # ------------------------------------------------------------------ 6
    if part(6, "invites are an admin's: a join link and a recovery link, shown once; a 404 to anybody else"):
        owner = admin(b)
        if "member" not in _admin:
            _admin["member"], _ = new_member(b, "sam_young", "Sam Young")
        member = _admin["member"]
        owner.pg.goto(BASE + "/social/invites")
        owner.pg.click("form[action$='/social/invites'] button[type=submit]")
        owner.pg.wait_for_load_state()
        join_link = owner.pg.input_value("[data-made-link]")
        listed_join = owner.pg.evaluate("() => [...document.querySelectorAll('.links .key-name')].map(e => e.textContent.trim())")
        owner.pg.goto(BASE + "/social/invites")
        owner.pg.fill("#recHandle", "@" + member.handle)
        owner.pg.click("form[action$='/social/invites/recover'] button[type=submit]")
        owner.pg.wait_for_load_state()
        rec_link = owner.pg.input_value("[data-made-link]")
        rec_title = text_of(owner.pg, "#madeTitle")
        listed_rec = owner.pg.evaluate("() => [...document.querySelectorAll('.links .key-name')].map(e => e.textContent.trim())")
        owner.pg.goto(BASE + "/social/invites")
        shown_again = owner.pg.evaluate("(c) => document.body.innerHTML.includes(c)", code_of(rec_link))
        rows = db("select kind, julianday(expires_at) - julianday(created_at), for_person_id is not null from social_invites"
                  " where code_hash in (?, ?)", (hashed(code_of(join_link)), hashed(code_of(rec_link))))
        check("an admin makes a join link (once, 14 days) and a recovery link for a named person (once, an hour):"
              " each shown once, its code after the #, listed as waiting, never shown again",
              join_link.startswith(BASE + "/social/join#") and rec_link.startswith(BASE + "/social/recover#")
              and f"@{member.handle}" in rec_title and "Invite link" in listed_join
              and f"Sign-in link for @{member.handle}" in listed_rec and not shown_again
              and sorted((k, round(d * 24, 2), f) for k, d, f in rows) == [("join", 336.0, 0), ("recover", 1.0, 1)],
              f"join {join_link[:60]}; recovery {rec_link[:60]} {rec_title!r}; waiting {listed_rec}; again {shown_again}; rows {rows}")
        _admin["rec_link"] = rec_link
        owner.pg.fill("#recHandle", "nobody_here")
        owner.pg.click("form[action$='/social/invites/recover'] button[type=submit]")
        owner.pg.wait_for_load_state()
        unknown = text_of(owner.pg, ".note")
        check("a recovery link for a handle nobody has makes nothing, and says so kindly",
              "No one has the handle @nobody_here" in unknown and not owner.pg.locator("[data-made-link]").count(),
              unknown)

        def same_as_missing(req, token):
            """Invites asked for, beside a page that is not there: status,
            words and headers (all but the date and the length)."""
            out = []
            for method, hidden, missing in (("GET", "/social/invites", "/social/no-such-page"),
                                            ("POST", "/social/invites", "/social/no-such-page"),
                                            ("POST", "/social/invites/recover", "/social/no-such/page")):
                if method == "GET":
                    a, m = req.get(BASE + hidden, max_redirects=0), req.get(BASE + missing, max_redirects=0)
                else:
                    form = {"csrf": token, "handle": "sam_young"}
                    a = req.post(BASE + hidden, form=form, headers={"Origin": BASE}, max_redirects=0)
                    m = req.post(BASE + missing, form=form, headers={"Origin": BASE}, max_redirects=0)
                ha = {k: v for k, v in a.headers.items() if k not in ("date", "set-cookie", "content-length")}
                hm = {k: v for k, v in m.headers.items() if k not in ("date", "set-cookie", "content-length")}
                out.append((method, hidden, a.status, m.status, a.text() == m.text(), ha == hm,
                            sorted(k for k in set(ha) | set(hm) if ha.get(k) != hm.get(k))))
            return out

        member.pg.goto(BASE + "/social/you")
        member_token = member.pg.get_attribute("meta[name=social-csrf]", "content")
        stranger = Person(b)
        stranger.pg.goto(BASE + "/social/signin")
        stranger_token = stranger.pg.get_attribute("meta[name=social-csrf]", "content")
        as_member = same_as_missing(member.ctx.request, member_token)
        as_stranger = same_as_missing(stranger.ctx.request, stranger_token)
        stranger.close()
        ok = all(a == 404 and m == 404 and body and heads for _, _, a, m, body, heads, _ in as_member + as_stranger)
        check("to a member and to somebody signed out, Invites (the page and both of its forms) is a 404 the same as"
              " a page that is not there: the same status, the same words, the same headers",
              ok and bool(member_token), f"member {as_member}; signed out {as_stranger}")
        made_by = db("select count(*) from social_invites where created_by_id = (select id from social_people where handle_key = ?)",
                     (member.handle.lower(),))[0][0]
        check("and nothing was made by them", made_by == 0, str(made_by))

    # ------------------------------------------------------------------ 7
    if part(7, "a recovery link adds a passkey to the account it was made for, once"):
        owner = admin(b)
        target, _ = new_member(b, "rosa", "Rosa Lima")
        before = {h: n for h, n in db("select p.handle, count(k.id) from social_people p left join social_passkeys k"
                                       " on k.person_id = p.id group by p.id")}
        link, _ = cli("recover", "rosa")
        check("`flask social recover HANDLE` prints a recovery link for that person (for the admin who lost every"
              " passkey: Render's shell)", bool(link) and link.startswith(BASE + "/social/recover#"), str(link))
        fresh = Person(b)
        fresh.pg.goto(link)
        st = link_state(fresh.pg)
        got = press(fresh, "[data-passkey=recover]", "/social/recover")
        after = {h: n for h, n in db("select p.handle, count(k.id) from social_people p left join social_passkeys k"
                                      " on k.person_id = p.id group by p.id")}
        handle_bytes = db("select user_handle from social_people where handle_key = 'rosa'")[0][0]
        made = fresh.creds()
        check("in a browser with no passkey, the link names whose account it is for, makes a passkey there, and signs"
              " in as them: Rosa has one more, nobody else has any more, and the new passkey carries her account's handle",
              st and st["ok"] and st["handle"] == "@rosa" and got.get("path") == "/social/you" and fresh.who() == "rosa"
              and after["rosa"] == before["rosa"] + 1
              and all(after[h] == n for h, n in before.items() if h != "rosa")
              and len(made) == 1 and base64.b64decode(made[0]["userHandle"]) == handle_bytes,
              f"page {st}; landed {got}; before {before}; after {after}")
        again = Person(b)
        again.pg.goto(link)
        spent = link_state(again.pg)
        check("the recovery link is spent: opened again, it is the kind card", spent and spent["gone"], str(spent))
        again.close()
        sign_out_here(fresh)
        back = signin(fresh)
        check("and the new passkey signs Rosa in on its own", back.get("path") == "/social/" and fresh.who() == "rosa",
              str(back))
        _admin["rosa"] = (target, fresh)

    # ------------------------------------------------------------------ 8
    if part(8, "passkeys on You: rename, remove one but never the last, never another's"):
        if "rosa" not in _admin:
            target, _ = new_member(b, "rosa", "Rosa Lima")
            link, _ = cli("recover", "rosa")
            fresh = Person(b)
            fresh.pg.goto(link)
            link_state(fresh.pg)
            press(fresh, "[data-passkey=recover]", "/social/recover")
            _admin["rosa"] = (target, fresh)
        target, fresh = _admin["rosa"]
        pg = target.pg
        pg.goto(BASE + "/social/you")
        names = pg.evaluate("() => [...document.querySelectorAll('.key-name')].map(e => e.textContent.trim())")
        pg.click(".key:first-child .key-more summary >> text=Rename")
        pg.fill(".key:first-child .key-form input[name=nickname]", "Rosa's phone")
        pg.click(".key:first-child .key-form button[type=submit]")
        pg.wait_for_url("**/social/you?note=renamed")
        renamed = pg.evaluate("() => [...document.querySelectorAll('.key-name')].map(e => e.textContent.trim())")
        check("a passkey is renamed in place, and the list says the new name",
              len(names) == 2 and renamed[0] == "Rosa's phone", f"{names} -> {renamed}")
        others = db("select k.public_id from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key != 'rosa' limit 1")
        if not others:
            kai, _ = new_member(b, "kai", "Kai Lee")
            kai.close()
            others = db("select k.public_id from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'kai'")
        token = pg.get_attribute("meta[name=social-csrf]", "content")
        if others:
            foreign = pg.request.post(BASE + f"/social/you/passkeys/{others[0][0]}/remove", form={"csrf": token},
                                      headers={"Origin": BASE}, max_redirects=0)
            still = db("select count(*) from social_passkeys where public_id = ?", (others[0][0],))[0][0]
        else:
            foreign, still = None, None
        check("another person's passkey cannot be removed from your page: 404, and it stays",
              foreign is not None and foreign.status == 404 and still == 1, f"{foreign and foreign.status} {still}")
        second = db("select k.public_id, k.credential_id from social_passkeys k join social_people p on p.id = k.person_id"
                    " where p.handle_key = 'rosa' order by k.id desc limit 1")[0]
        pg.click(f".key:has(form[action$='/{second[0]}/remove']) .key-more summary >> text=Remove")
        pg.click(f"form[action$='/{second[0]}/remove'] button[type=submit]")
        pg.wait_for_url("**/social/you?note=removed")
        left = db("select count(*) from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'rosa'")[0][0]
        sign_out_here(fresh)
        gone = signin(fresh)
        check("one of two is removed: gone from the list and the table, and that passkey no longer signs anybody in"
              " (the page says the passkey is not on an account here anymore)",
              left == 1 and gone.get("path") == "/social/signin" and "isn’t on an account here anymore" in gone["say"]
              and fresh.who() is None, f"left {left}; signing in with it: {gone}")
        pg.goto(BASE + "/social/you")
        last = pg.evaluate("() => ({ remove: document.querySelectorAll('form[action$=\"/remove\"]').length,"
                           " note: (document.querySelector('.key-last') || {}).textContent || '' })")
        only = db("select k.public_id from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'rosa'")[0][0]
        token = pg.get_attribute("meta[name=social-csrf]", "content")
        forced = pg.request.post(BASE + f"/social/you/passkeys/{only}/remove", form={"csrf": token},
                                 headers={"Origin": BASE}, max_redirects=0)
        kept = db("select count(*) from social_passkeys where public_id = ?", (only,))[0][0]
        check("the last passkey stays: it has no Remove, the page says why, and a remove sent anyway is turned away"
              " with that note, the passkey kept",
              last["remove"] == 0 and "only passkey" in last["note"] and forced.status == 303
              and "note=last" in forced.headers.get("location", "") and kept == 1,
              f"{last}; forced {forced.status} {forced.headers.get('location')}; kept {kept}")
        fresh.close()

    # ------------------------------------------------------------------ 9
    if part(9, "sign out everywhere ends another browser's session, and a copied cookie"):
        a, _ = new_member(b, "theo", "Theo Lind")
        # Another browser, signed in by its own passkey ceremony: the same
        # passkey, as a synced one would be on a second device.
        bee = Person(b, screen="desk")
        bee.cdp.send("WebAuthn.addCredential", {"authenticatorId": bee.aid, "credential": {
            k: v for k, v in a.creds()[0].items() if k in ("credentialId", "isResidentCredential", "rpId",
                                                             "privateKey", "userHandle", "signCount")}})
        both = signin(bee)
        copied = dict(a.cookie())
        drafts_before = bee.ctx.request.get(BASE + "/api/drafts")
        sign_out_here(a, everywhere=True)
        note = text_of(a.pg, ".note")
        bee.pg.goto(BASE + "/social/you")
        bee_at = bee.pg.url
        drafts_after = bee.ctx.request.get(BASE + "/api/drafts")
        thief = b.new_context(**DESK, extra_http_headers={"X-Forwarded-For": address()})
        thief.add_cookies([pw_cookie(copied)])
        stolen = thief.request.get(BASE + "/social/you", max_redirects=0)
        check("Sign out everywhere, pressed in one browser, signs out that browser (it says so) and another browser"
              " signed in by its own passkey, on the site and to Skribl (its drafts list answers 401 now), and a cookie"
              " copied before it is nobody's",
              both.get("path") == "/social/" and drafts_before.status == 200 and "everywhere" in note
              and "/social/signin" in bee_at and drafts_after.status == 401 and stolen.status == 303
              and a.who() is None,
              f"B signed in {both.get('path')}; drafts before {drafts_before.status} after {drafts_after.status};"
              f" note {note!r}; B now {bee_at}; copied cookie {stolen.status}")
        thief.close()
        bee.close()
        a.close()

    # ------------------------------------------------------------------ 10
    if part(10, "delete my account: what goes and what stays said first; really gone"):
        owner = admin(b)
        p, _ = new_member(b, "zoe", "Zoe Park")
        pid = db("select id, public_id from social_people where handle_key = 'zoe'")[0]
        # An admin, so there are invite links of theirs to see go with them.
        db("update social_people set is_admin = 1 where id = ?", (pid[0],), write=True)
        p.pg.goto(BASE + "/social/invites")
        p.pg.click("form[action$='/social/invites'] button[type=submit]")
        p.pg.wait_for_load_state()
        made = p.pg.input_value("[data-made-link]")
        link, _ = cli("recover", "zoe")
        p.pg.goto(BASE + "/social/you/delete")
        page = p.pg.evaluate("() => document.querySelector('main').innerText.replace(/\\s+/g, ' ')")
        check("the confirm says what goes (the account, its name and handle, its passkeys, the invite links made)"
              " and what stays (the skribls and drafts, with the Library to delete them first)",
              "Your account: your name, Zoe Park, and your handle, @zoe" in page and "Your passkeys (1)" in page
              and "invite links you made that nobody has used yet (1)" in page and "skribls and saved drafts stay" in page
              and p.pg.locator("a:has-text('Open your Library')").count() == 1, page[:400])
        p.pg.fill("#delConfirm", "zoey")
        p.pg.click("form[action$='/social/you/delete'] button[type=submit]")
        p.pg.wait_for_load_state()
        wrong = text_of(p.pg, ".err")
        still = db("select count(*) from social_people where id = ?", (pid[0],))[0][0]
        check("a handle typed wrong deletes nothing and says what to type, kindly",
              "Type @zoe to confirm" in wrong and still == 1, f"{wrong!r} {still}")
        p.pg.fill("#delConfirm", "@zoe")
        p.pg.click("form[action$='/social/you/delete'] button[type=submit]")
        p.pg.wait_for_load_state()
        title = text_of(p.pg, "h1")
        left = {t: db(f"select count(*) from {t} where {w}", a)[0][0] for t, w, a in (
            ("social_people", "id = ?", (pid[0],)),
            ("social_passkeys", "person_id = ?", (pid[0],)),
            ("social_invites", "created_by_id = ? or for_person_id = ? or used_by_id = ?", (pid[0],) * 3),
            ("social_challenges", "person_id = ?", (pid[0],)))}
        p.pg.goto(BASE + "/social/signin")
        after = signin(p)
        dead = Person(b)
        dead.pg.goto(made)
        dead_link = link_state(dead.pg)
        dead.close()
        check("the right handle deletes for real: the person, their passkey, the invite they came in by, the links"
              " they made and the recovery link for them are gone from the tables; their passkey signs nobody in, and"
              " the link they made no longer works",
              "deleted" in title and all(v == 0 for v in left.values()) and after.get("path") == "/social/signin"
              and "isn’t on an account here anymore" in after["say"] and p.who() is None
              and dead_link and dead_link["gone"],
              f"{title!r}; left {left}; signing in {after}; their invite {dead_link}")
        p.close()

    # ------------------------------------------------------------------ 11
    if part(11, "limits: sign-ins, joins and link checks per address; tries per invite"):
        def burst(path, body_fn, n, xff=None):
            c = Client(xff=xff)
            c.get("/social/signin")
            codes = [c.post(path, body_fn(i))[0] for i in range(n)]
            return codes
        s = burst("/social/signin/options", lambda i: {}, 31)
        other = burst("/social/signin/options", lambda i: {}, 1)
        check("sign-ins begun from one address: 30 in an hour, then 429; another address is not held up",
              s[:30] == [200] * 30 and s[30] == 429 and other == [200], f"{s[25:]} other {other}")
        j = burst("/social/join/options", lambda i: {"code": secrets.token_urlsafe(16), "name": "x", "handle": "xyz_abc", "age13": True}, 21)
        check("joins begun from one address: 20 in an hour (each a link that does not work: 410), then 429",
              j[:20] == [410] * 20 and j[20] == 429, str(j[15:]))
        look = burst("/social/join/check", lambda i: {"code": secrets.token_urlsafe(16)}, 61)
        check("links checked from one address: 60 in an hour, then 429 (guessing codes is slow, and they are 128 bits)",
              look[:60] == [404] * 60 and look[60] == 429, str(look[55:]))
        link, _ = cli("invite")
        code = code_of(link)
        tries = []
        for i in range(13):
            c = Client()
            c.get("/social/signin")
            tries.append(c.post("/social/join/check", {"code": code})[0])
        check("one invite tried from thirteen addresses: 12 in an hour, then 429, wherever the tries come from",
              tries[:12] == [200] * 12 and tries[12] == 429, str(tries))
        lim = Person(b)
        lim.pg.goto(BASE + "/social/signin")
        tok = lim.pg.get_attribute("meta[name=social-csrf]", "content")
        for _ in range(30):
            lim.ctx.request.post(BASE + "/social/signin/options", data="{}", headers={
                "Content-Type": "application/json", "X-Social-CSRF": tok, "Origin": BASE})
        held = press(lim, "[data-passkey=signin]", "/social/signin")
        check("and past it, the page says so kindly (wait a little), and no passkey is asked for",
              held.get("path") == "/social/signin" and "Wait a little" in held["say"], str(held))
        lim.close()

    # ------------------------------------------------------------------ 12
    if part(12, "a state-changing request without the token, or from another origin, is refused"):
        c = Client()
        c.get("/social/signin")
        other = Client()
        other.get("/social/signin")
        none = c.post("/social/signin/options", {}, token=False)
        theirs = c.post("/social/signin/options", {}, token=other.token)
        c.origin = "https://evil.example"
        foreign = c.post("/social/signin/options", {})
        c.origin = None
        cross = c.post("/social/signin/options", {}, headers={"Sec-Fetch-Site": "cross-site"})
        c.origin = BASE
        right = c.post("/social/signin/options", {})
        check("the passkey ceremonies refuse a post with no token, with another browser's token, from another"
              " origin, or that a browser says is cross-site (403 {\"error\": \"stale\"}); with this page's token"
              " and origin it is answered",
              none[0] == 403 and none[1] == {"error": "stale"} and theirs[0] == 403 and foreign[0] == 403
              and cross[0] == 403 and right[0] == 200 and "options" in right[1],
              f"none {none}; theirs {theirs[0]}; foreign {foreign[0]}; cross-site {cross[0]}; right {right[0]}")
        p, _ = new_member(b, "omar", "Omar Haddad")
        gen = db("select session_gen from social_people where handle_key = 'omar'")[0][0]
        keys = db("select count(*) from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'omar'")[0][0]
        kid = db("select k.public_id from social_passkeys k join social_people p on p.id = k.person_id where p.handle_key = 'omar'")[0][0]
        outs = {}
        for path, form in (("/social/signout/everywhere", {}), ("/social/you/delete", {"confirm": "omar"}),
                           (f"/social/you/passkeys/{kid}/rename", {"nickname": "hijacked"})):
            r = p.ctx.request.post(BASE + path, form=form, headers={"Origin": BASE}, max_redirects=0)
            outs[path] = (r.status, "didn’t go through" in r.text())
        p.pg.goto(BASE + "/social/you")
        good_token = p.pg.get_attribute("meta[name=social-csrf]", "content")
        r = p.ctx.request.post(BASE + "/social/signout/everywhere", form={"csrf": good_token},
                               headers={"Origin": "https://evil.example"}, max_redirects=0)
        outs["everywhere, this page's token, another origin"] = (r.status, "didn’t go through" in r.text())
        # WHATEVER A BODY SAYS IS ANSWERED, NEVER A 500: a number for a name,
        # a list for a handle, no answer or the wrong shape of one where a
        # passkey's answer goes, and more than the site takes at all.
        m = Client()
        m.get("/social/signin")
        link, _ = cli("invite")
        odd = {}
        odd["name and handle not text"] = m.post("/social/join/options", {"code": code_of(link), "name": 5,
                                                                           "handle": ["x"], "age13": True})
        m.post("/social/signin/options", {})
        odd["no answer"] = m.post("/social/signin/verify", {"credential": None})
        m.post("/social/signin/options", {})
        odd["an answer that is a string"] = m.post("/social/signin/verify", {"credential": "x"})
        m.post("/social/join/options", {"code": code_of(link), "name": "Odd", "handle": "odd_one", "age13": True})
        odd["a list for a new passkey"] = m.post("/social/join/verify", {"code": code_of(link), "credential": [1, 2]})
        m.post("/social/join/options", {"code": code_of(link), "name": "Odd", "handle": "odd_one", "age13": True})
        odd["no new passkey"] = m.post("/social/join/verify", {"code": code_of(link)})
        odd["65 KiB"] = m.post("/social/signin/options", {"pad": "x" * (65 * 1024)})
        # Saying no length (chunked), a body is read only to 64 KiB, as a
        # WSGI server cuts it there: a good invite's code sent past that is
        # never read, so it does not count (the check answers as for no code).
        odd["a good code past 64 KiB, no length said"] = (
            m.post_chunked("/social/join/check", {"pad": "x" * (65 * 1024), "code": code_of(link)}), None)
        odd["the same code, short"] = m.post("/social/join/check", {"code": code_of(link)})
        want = {"name and handle not text": (400, {"name": "name_empty", "handle": "handle_shape"}),
                "no answer": (400, "failed"), "an answer that is a string": (400, "failed"),
                "a list for a new passkey": (400, "failed"), "no new passkey": (400, "failed"), "65 KiB": (413, None),
                "a good code past 64 KiB, no length said": (404, None), "the same code, short": (200, None)}
        got = {k: (st, (j.get("fields") or j.get("error")) if isinstance(j, dict) else None) for k, (st, j) in odd.items()}
        check("whatever a body says is answered, never a 500: a number for a name and a list for a handle are"
              " field messages, an answer missing or the wrong shape is refused (400); past 64 KiB a body is refused"
              " by the length it says (413), or, saying none, read no further (a good code past it does not count)",
              got == want, str(got))
        check("the site's forms (sign out everywhere, delete my account, rename) without the token, or from another"
              " origin, are refused with the kind page, and change nothing",
              all(st == 403 and kind for st, kind in outs.values())
              and db("select session_gen from social_people where handle_key = 'omar'")[0][0] == gen
              and db("select nickname from social_passkeys where public_id = ?", (kid,))[0][0] != "hijacked"
              and keys == 1 and p.who() == "omar", str(outs))
        p.close()

    # ------------------------------------------------------------------ 13
    if part(13, "the cookie: HttpOnly, SameSite=Lax, path /, Secure over HTTPS, 30 days, signed"):
        c = Client()
        st, heads, _ = c._req("GET", "/social/signin")
        plain = heads.get("Set-Cookie", "")
        st, heads2, _ = Client()._req("GET", "/social/signin", headers={"X-Forwarded-Proto": "https"})
        tls = heads2.get("Set-Cookie", "")
        flags = lambda s: {x.strip().split("=")[0].lower() for x in s.split(";")[1:]}
        check("its cookie is social_session, HttpOnly, SameSite=Lax, path /; not Secure over plain http (a local"
              " run), Secure where the page came over HTTPS (Render says so in X-Forwarded-Proto)",
              plain.startswith("social_session=") and {"httponly", "path"} <= flags(plain)
              and "samesite=lax" in plain.lower() and "path=/" in plain.lower() and "secure" not in flags(plain)
              and "secure" in flags(tls) and "httponly" in flags(tls),
              f"http: {plain[-90:]}; https: {tls[-90:]}")
        p, _ = new_member(b, "lena", "Lena Berg")
        ck = p.cookie()
        days = (ck["expires"] - time.time()) / 86400 if ck else 0
        data = session_data(ck["value"]) if ck else None
        # A FORGERY THAT ONLY ITS SIGNATURE CAN STOP: this cookie's signature
        # under a payload naming somebody else (the admin), with their own
        # current generation, so nothing but the signature is wrong.
        boss = admin(b)
        other = db("select public_id, session_gen from social_people where handle_key = ?", (boss.handle.lower(),))[0]
        bad = dict(ck)
        bad["value"] = base64.urlsafe_b64encode(json.dumps({"s": data["s"], "p": other[0], "g": other[1]},
                                                           separators=(",", ":")).encode()).rstrip(b"=").decode() \
            + "." + ck["value"].split(".", 1)[1]
        forged = b.new_context(**DESK, extra_http_headers={"X-Forwarded-For": address()})
        forged.add_cookies([pw_cookie(bad)])
        f = forged.request.get(BASE + "/social/you", max_redirects=0)
        forged.close()
        check("signed in, it lasts 30 days, HttpOnly and Lax in the browser too, and it is signed: one rewritten to"
              " name somebody else (with their own generation) signs nobody in",
              ck is not None and ck["httpOnly"] and ck["sameSite"] == "Lax" and 29.5 < days < 30.5
              and data and data.get("p", "").startswith("site:") and f.status == 303,
              f"{ck and {k: ck[k] for k in ('httpOnly', 'sameSite', 'secure', 'path')}}; {days:.1f} days; payload {data}; forged {f.status}")
        p.close()

    # ------------------------------------------------------------------ 14
    if part(14, "the site's own migration chain, and the deploy that runs it"):
        def alembic(dbfile, *args, ini=True):
            env = dict(os.environ, DATABASE_URL=f"sqlite:///{dbfile}")
            cmd = [sys.executable, "-m", "alembic"] + (["-c", "social/alembic.ini"] if ini else []) + list(args)
            return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)

        def tables(dbfile):
            con = sqlite3.connect(dbfile)
            names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
            idx = {r[0] for r in con.execute("select name from sqlite_master where type='index' and name like 'ix_social%'")}
            stamps = {}
            for t in ("alembic_version", "social_alembic_version"):
                if t in names:
                    stamps[t] = [r[0] for r in con.execute(f"select version_num from {t}")]
            con.close()
            return names, idx, stamps

        heads = subprocess.run([sys.executable, "-m", "alembic", "-c", "social/alembic.ini", "heads"], cwd=ROOT,
                               capture_output=True, text=True, timeout=60).stdout.split()[0]
        skribl_head = subprocess.run([sys.executable, "-m", "alembic", "heads"], cwd=ROOT,
                                     capture_output=True, text=True, timeout=60).stdout.split()[0]
        d1 = os.path.join(TMP, "chain-empty.db")
        r1 = alembic(d1, "upgrade", "head")
        names, idx, stamps = tables(d1)
        want = {"social_people", "social_passkeys", "social_invites", "social_challenges", "social_rate_events",
                "social_posts",                          # posts: piece 4
                "social_blocks", "social_reports",       # report and block: piece 5
                "social_comments"}                       # comments: phase 2
        want_idx = {"ix_social_people_public_id", "ix_social_people_handle_key", "ix_social_people_user_handle",
                    "ix_social_passkeys_credential_id", "ix_social_passkeys_public_id", "ix_social_passkeys_person_id",
                    "ix_social_invites_code_hash", "ix_social_invites_public_id", "ix_social_invites_expires_at",
                    "ix_social_invites_for_person_id", "ix_social_invites_created_by_id", "ix_social_invites_used_by_id",
                    "ix_social_challenges_sid_purpose", "ix_social_challenges_expires_at",
                    "ix_social_rate_bucket_key_time", "ix_social_rate_created_at",
                    "ix_social_posts_public_id", "ix_social_posts_created", "ix_social_posts_person_created",
                    "ix_social_posts_skribl_id",
                    "ix_social_blocks_pair", "ix_social_blocks_blocked_id",
                    "ix_social_reports_public_id", "ix_social_reports_once", "ix_social_reports_state_created",
                    "ix_social_reports_about_id", "ix_social_reports_reporter_id", "ix_social_reports_handled_by_id",
                    "ix_social_comments_public_id", "ix_social_comments_post_created",
                    "ix_social_comments_parent_created", "ix_social_comments_person_id",
                    "ix_social_comments_skribl_id",
                    # comments on every drawing: a drawing's newest first, and whose it is
                    "ix_social_comments_drawing_created",
                    # Activity (notifications): whose, newest first (the owner's own index
                    # folded into it), and whom an answer answers, newest first
                    "ix_social_comments_owner_created", "ix_social_comments_to_created"}
        check("on an empty SQLite file the site's chain builds its nine tables with every index, stamps its own"
              " version table (social_alembic_version) at its head, and touches nothing of Skribl's",
              r1.returncode == 0 and names == want | {"social_alembic_version"} and want_idx <= idx
              and stamps == {"social_alembic_version": [heads]},
              f"exit {r1.returncode} {r1.stderr.strip().splitlines()[-1:] if r1.returncode else ''}; tables {sorted(names)};"
              f" missing indexes {sorted(want_idx - idx)}; stamps {stamps}")
        d2 = os.path.join(TMP, "chain-both-a.db")
        a1, a2 = alembic(d2, "upgrade", "head", ini=False), alembic(d2, "upgrade", "head")
        d3 = os.path.join(TMP, "chain-both-b.db")
        b1, b2 = alembic(d3, "upgrade", "head"), alembic(d3, "upgrade", "head", ini=False)
        n2, _, s2 = tables(d2)
        n3, _, s3 = tables(d3)
        both = {"alembic_version": [skribl_head], "social_alembic_version": [heads]}
        check("beside Skribl's chain on one file, in either order: each chain stamps its own table at its own head,"
              " and every table of both is there",
              all(r.returncode == 0 for r in (a1, a2, b1, b2)) and s2 == both and s3 == both
              and want <= n2 and "skribl_posts" in n2 and want <= n3 and "skribl_posts" in n3,
              f"Skribl first {s2}; site first {s3}")
        chk = alembic(d1, "check")
        down = alembic(d2, "downgrade", "base")
        n4, _, s4 = tables(d2)
        check("no drift: Alembic finds nothing the models have that the chain has not (alembic check), and the site's"
              " chain taken back to base removes only the site's tables, Skribl's untouched",
              chk.returncode == 0 and "No new upgrade operations detected" in (chk.stdout + chk.stderr)
              and down.returncode == 0 and not (want & n4) and "skribl_posts" in n4
              and s4 == {"alembic_version": [skribl_head], "social_alembic_version": []},
              f"check {chk.returncode} {(chk.stdout + chk.stderr).strip().splitlines()[-1:]}; after downgrade {s4}")

        def gunicorn(dbfile):
            glog = os.path.join(TMP, "gunicorn-" + os.path.basename(dbfile) + ".log")
            env = dict(os.environ, DATABASE_URL=f"sqlite:///{dbfile}", SKRIBL_ALLOW_EPHEMERAL_SECRET="1",
                       SKRIBL_STAND_IN="0", SKRIBL_CSRF_PROTECT="1")
            env.pop("SKRIBL_SOCIAL", None)
            with open(glog, "w") as fh:
                g = subprocess.Popen([sys.executable, "-m", "gunicorn", "-b", "127.0.0.1:0", "--no-control-socket",
                                      "--log-level", "info", "app:app"], cwd=ROOT, env=env, stdout=fh,
                                     stderr=subprocess.STDOUT)
            port, text = None, ""
            try:
                for _ in range(240):
                    text = open(glog).read()
                    m = re.search(r"Listening at: http://127\.0\.0\.1:(\d+)", text)
                    if m:
                        port = m.group(1)
                    if port and "stripped and compressed before the first visitor" in text:
                        break
                    if g.poll() is not None:
                        break
                    time.sleep(0.5)
                got = {}
                if port and g.poll() is None:
                    gb = f"http://127.0.0.1:{port}"
                    for path in ("/skribl-pad", "/social/", "/social/signin"):
                        try:
                            with urllib.request.urlopen(gb + path, timeout=60) as r:
                                got[path] = r.status
                        except urllib.error.HTTPError as e:
                            got[path] = e.code
                    gc = Client()
                    gc.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(gc.jar), _NoRedirect())
                    req = urllib.request.Request(gb + "/social/signin", headers={"Host": f"localhost:{port}"})
                    with gc.op.open(req, timeout=60) as r:
                        tok = re.search(r'name="social-csrf" content="([^"]+)"', r.read().decode()).group(1)
                    req = urllib.request.Request(gb + "/social/signin/options", data=b"{}", method="POST",
                                                 headers={"Host": f"localhost:{port}", "Origin": f"http://localhost:{port}",
                                                          "Content-Type": "application/json", "X-Social-CSRF": tok})
                    try:
                        with gc.op.open(req, timeout=60) as r:
                            got["options"] = (r.status, json.loads(r.read().decode()).get("error"))
                    except urllib.error.HTTPError as e:
                        got["options"] = (e.code, json.loads(e.read().decode()).get("error"))
                return got, open(glog).read()
            finally:
                g.terminate()
                try:
                    g.wait(15)
                except subprocess.TimeoutExpired:
                    g.kill()

        d5 = os.path.join(TMP, "deploy-ok.db")
        got_ok, log_ok = gunicorn(d5)
        n5, _, s5 = tables(d5)
        check("gunicorn, started as Render starts it (`gunicorn app:app`, its conf read by name), brings the site's"
              " tables up to date once before any worker, says so, and serves: the Pad, the site, a sign-in begun",
              "social: the site's tables are up to date" in log_ok and want <= n5
              and s5.get("social_alembic_version") == [heads]
              and got_ok.get("/skribl-pad") == 200 and got_ok.get("/social/signin") == 200
              and (got_ok.get("options") or (0,))[0] == 200,
              f"served {got_ok}; stamps {s5}; log: {[l for l in log_ok.splitlines() if 'social:' in l][:2]}")
        d6 = os.path.join(TMP, "deploy-bad.db")
        con = sqlite3.connect(d6)
        con.execute("create table social_alembic_version (version_num varchar(32) not null primary key)")
        con.execute("insert into social_alembic_version values ('deadbeef0000')")
        con.commit()
        con.close()
        got_bad, log_bad = gunicorn(d6)
        said = next((l for l in log_bad.splitlines() if "could not be brought up to date" in l), "")
        check("a site chain that fails does not take the demo down: it is logged loudly (alembic's own words, no"
              " database address), the Pad and the site's pages are served, and a sign-in begun is a kind 503 (resting)",
              bool(said) and "deadbeef0000" in said and d6 not in log_bad and got_bad.get("/skribl-pad") == 200
              and got_bad.get("/social/") == 200 and got_bad.get("options") == (503, "resting"),
              f"served {got_bad}; said {said[-200:]!r}")
        spec = __import__("importlib.util").util.spec_from_file_location("gconf_probe", ROOT / "gunicorn.conf.py")
        gconf = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(gconf)
        blanked = gconf._blank_addresses("FAILED: could not connect to postgresql://skribl:hunter2-secret@db.internal:5432/x now")
        check("and a database address in alembic's words never reaches the log: its password is blanked with it",
              "hunter2" not in blanked and "<database address>" in blanked, blanked)

    # ------------------------------------------------------------------ 15
    if part(15, "the new screens: words at 4.5:1, targets 44px, text fields 16px; phone and desk, light and dark"):
        owner = admin(b)
        if "member" not in _admin:
            _admin["member"], _ = new_member(b, "sam_young", "Sam Young")
        member_handle = _admin["member"].handle
        looks = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                v = Person(b, screen=screen, scheme=scheme)
                # Signed out: sign-in (with a note), a join page with its
                # fields' messages showing, a link that does not work, the
                # kind pages.
                v.pg.goto(BASE + "/social/signin?out=all")
                v.pg.wait_for_timeout(400)
                looks[(screen, scheme, "signin")] = v.pg.evaluate(READ)
                link, _ = cli("invite")
                v.pg.goto(link)
                link_state(v.pg)
                v.pg.fill("#joinHandle", "9")
                v.pg.click("form[data-passkey] button[type=submit]")
                v.pg.wait_for_timeout(300)
                looks[(screen, scheme, "join")] = v.pg.evaluate(READ)
                v.pg.goto(BASE + "/social/join#" + secrets.token_urlsafe(16))
                link_state(v.pg)
                looks[(screen, scheme, "gone")] = v.pg.evaluate(READ)
                rec, _ = cli("recover", member_handle)
                v.pg.goto(rec)
                link_state(v.pg)
                looks[(screen, scheme, "recover")] = v.pg.evaluate(READ)
                v.pg.goto(BASE + "/social/")
                v.pg.wait_for_timeout(400)
                looks[(screen, scheme, "home, signed out")] = v.pg.evaluate(READ)
                # A form sent without its token: the kind page that says so.
                v.pg.evaluate("() => { const f = document.createElement('form'); f.method = 'post';"
                              " f.action = '/social/signout/everywhere'; document.body.appendChild(f); f.submit(); }")
                v.pg.wait_for_load_state()
                v.pg.wait_for_timeout(200)
                looks[(screen, scheme, "stale")] = v.pg.evaluate(READ)
                v.close()
                # Signed in as the admin: You (a note, a rename open, a
                # remove open), Invites (a link just made, the waiting list),
                # the delete confirm with a wrong handle.
                w = Person(b, screen=screen, scheme=scheme)
                w.ctx.add_cookies([pw_cookie(owner.cookie())])
                w.pg.goto(BASE + "/social/you?note=added")
                w.pg.wait_for_timeout(300)
                w.pg.evaluate("() => document.querySelectorAll('.key-more').forEach(d => d.open = true)")
                looks[(screen, scheme, "you")] = w.pg.evaluate(READ)
                w.pg.goto(BASE + "/social/invites")
                w.pg.click("form[action$='/social/invites'] button[type=submit]")
                w.pg.wait_for_load_state()
                looks[(screen, scheme, "invites")] = w.pg.evaluate(READ)
                w.pg.goto(BASE + "/social/you/delete")
                w.pg.fill("#delConfirm", "not-it")
                w.pg.click("form[action$='/social/you/delete'] button[type=submit]")
                w.pg.wait_for_load_state()
                looks[(screen, scheme, "delete")] = w.pg.evaluate(READ)
                w.pg.goto(BASE + "/social/")
                w.pg.wait_for_timeout(400)
                looks[(screen, scheme, "home, signed in")] = w.pg.evaluate(READ)
                w.close()
        looks = {k: v for k, v in looks.items() if v}
        low = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["low"]]
        reads = sum(v["read"] for v in looks.values())
        lowest = min(((v["lowest"], " ".join(k)) for k, v in looks.items()), default=(0, "nothing"))
        check("every word on sign-in, join (its messages showing), a recovery link, a link that does not work, You,"
              " Invites, the delete confirm and the signed-in frame reads at 4.5:1 or more on what is painted behind it",
              reads >= 400 and not low, f"{reads} read, the lowest {lowest}; under 4.5: {low[:5]}")
        small = [f"{k[0]} {k[1]} {k[2]}: {x}" for k, v in looks.items() for x in v["small"]]
        check("every link, button, toggle and field on them is 44px or more each way (phone and desk)",
              not small, "; ".join(small[:6]))
        fields = [f"{k[0]} {k[2]}: {x}" for k, v in looks.items() for x in v["fields"]]
        counted = sum(1 for k in looks if k[2] in ("join", "invites", "delete", "you"))
        check("every text field is 16px or more, so a phone never magnifies the page on a tap",
              not fields and counted >= 12, "; ".join(fields[:6]))

    # ------------------------------------------------------------------ 16
    # ------------------------------------------------------------------ 17
    if part(17, "a limit is never passed, not even by tries at the very same instant"):
        # The site's limiter, in a process of its own on this suite's
        # database: twelve tries at once against a limit of five, then one at
        # a time. A pause is held where a try is first written (RateEvent's
        # insert), which in the old order, counted and then written, was the
        # gap two tries at once could both pass through (the review of piece
        # 2; DECISIONS, "Where things stand, Nov 10").
        probe = r"""
import json, sys, threading, time
sys.path.insert(0, %r)
from app import app
from social import security as sec
from social.models import RateEvent
import sqlalchemy as sa
sec.LIMITS["probe"] = (5, 3600)
t = RateEvent.__table__
first = t.insert
def held(*a, **k):
    time.sleep(0.05)
    return first(*a, **k)
t.insert = held
N = 12
gate = threading.Barrier(N)
got = []
def one():
    with app.app_context():
        gate.wait()
        try:
            got.append(sec.over("probe", "one-address"))
        except Exception as exc:
            got.append("error: " + type(exc).__name__ + ": " + str(exc).splitlines()[0][:80])
ts = [threading.Thread(target=one) for _ in range(N)]
for x in ts: x.start()
for x in ts: x.join()
def rows():
    with app.app_context():
        with sec.site().engine().connect() as c:
            return c.execute(sa.select(sa.func.count()).select_from(t).where(t.c.bucket == "probe")).scalar()
burst_rows = rows()
after = []
with app.app_context():
    for _ in range(8):
        after.append(sec.over("probe", "one-address"))
print("PROBE " + json.dumps({"burst": got, "burst_rows": burst_rows, "after": after, "rows": rows()}))
""" % str(ROOT)
        out = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=180)
        line = next((x for x in out.stdout.splitlines() if x.startswith("PROBE ")), None)
        got = json.loads(line[6:]) if line else {}
        let = (got.get("burst") or []).count(False)
        after = got.get("after") or []
        more = after.count(False)
        check("a limit is never passed, not even by twelve tries at the very same instant: of twelve at once against a"
              " limit of five, five at most are let through, and only those are counted; then one at a time, the rest"
              " of the five are, and no more",
              bool(got) and len(got["burst"]) == 12 and all(isinstance(x, bool) for x in got["burst"])
              and let <= 5 and got["burst_rows"] == let and let + more == 5
              and after == [False] * more + [True] * (8 - more) and got["rows"] == 5,
              f"{got or (out.stdout[-300:] + out.stderr[-600:])}")

    # ------------------------------------------------------------------ 18
    if part(18, "a passkey is made and used only at the site's own address"):
        other = f"elsewhere.test:{PORT}"
        far = Client(origin=f"http://{other}")
        far.get("/social/signin", headers={"Host": other})
        st_far, body_far = far.post("/social/signin/options", {}, headers={"Host": other})[:2]
        home = Client()
        home.get("/social/signin")
        st_home, body_home = home.post("/social/signin/options", {})[:2]
        jfar = body_far if isinstance(body_far, dict) else {}
        jhome = body_home if isinstance(body_home, dict) else {}
        check("a passkey is begun only at the site's own address (SKRIBL_SOCIAL_HOSTS): from another, no ceremony,"
              " and the page is told so (its own words); at its own, as ever",
              st_far == 400 and jfar.get("error") == "elsewhere" and "options" not in jfar
              and st_home == 200 and bool(jhome.get("options"))
              and ((jhome.get("options") or {}).get("rpId") in (None, "localhost")),
              f"elsewhere {st_far} {str(jfar)[:120]}; home {st_home} {str(jhome)[:120]}")

    if part(16, "no page errors, no console errors, no CSP violations"):
        check("no page errors, console errors or CSP violations on the site's sign-in pages, through every"
              " ceremony above (a refused request's own status line aside)",
              not ERRS, "; ".join(ERRS[:4]))
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
