"""Nudges on the Skribl site (push notifications; docs/SOCIAL-SITE.md "Built:
push notifications"; Blooby's Nudges, the owner's "All yes", Nov 18), through
the demo's own server, a stand-in push service of the suite's own (an http
origin on this machine, which the server is told it may send to:
SOCIAL_PUSH_TEST_ORIGIN), and Chromium with its virtual authenticator for the
site's people. Every nudge the stand-in is handed is opened with the device's
own keys, as a browser would open it, and its signature checked.

  1. THE SEAL AND THE SIGNATURE: seal() makes RFC 8291's worked example byte
     for byte; the site's key is the same for the same SECRET_KEY, another for
     another, and SOCIAL_VAPID_KEY's where it is set; the page hands out the
     key the nudges are signed with.
  2. WHERE A NUDGE MAY GO: /push/subscribe takes a push service's address and
     the device's keys, keeps them with the sign-in, and starts at the dot's
     rule; it refuses any other address (http, another port, a name in it, a
     host that only ends like one, the stand-in's lookalike), keys that are
     not keys, a request without the page's token or from another origin, and
     somebody signed out.
  3. WHAT BUZZES (A, the dot's rule): something said on your post, a reply to
     you, a drawn reply ("Tap to watch it draw."), a mention: sealed for the
     device, signed as the site (a VAPID JWT for the push service's origin
     that verifies with its own key), in Activity's words and its link, its
     tag, the number of new things that light the dot; two on one post say
     "Cyd and Bea" under one tag; a like, a follow and a repost wait until
     their switch is on; your own never buzzes you.
  4. NEVER WHAT ACTIVITY LEAVES OUT, NEVER TWICE: somebody muted makes no
     nudge, and does not buzz the row before it again.
  5. GONE DEVICES: a push service's 410 or 404 takes the device away.
  6. THE SIGN-IN: signing out here takes this browser's devices and leaves
     another's; Sign out everywhere takes them all; a device from before it
     is never nudged; another account asking about a device stops it being
     the last one's, and taking it starts it again; an account deleted takes
     its devices.
  7. THE PAGES: Activity's card (hidden as sent; shown where this device can
     be nudged and nobody said Not now; the device's word; Not now puts it
     away for good, gliding shut; Turn on subscribes and it goes) and
     Settings' panel (Turn on, then a row a kind with Theme's switch, the
     dot's rule pressed; a switch moves and the site keeps it; told no; an
     iPhone in a browser tab, the way to the Home Screen; a browser that
     cannot); every word 4.5:1 on what is painted behind it, every button
     44px, nothing wider than the screen; phone (touch) and desk, light and
     dark.
  8. THE SERVICE WORKER: a push delivered to the real push-sw.js shows the
     nudge (its title, words, tag and link), and only the site's own link.
  9. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

Not tested here: a real push service (Apple's, Google's) and a real phone; the
stand-in is handed exactly what they would be. SOCIALPUSH_PART=<n>[,<m>] runs
those sections only (calibration). Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Nudges".
"""
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT))
PART = os.environ.get("SOCIALPUSH_PART", "")
#: SOCIALPUSH_SHOTS=<folder> keeps a picture of the card and the panel in each look (for a mock or a PR).
SHOTS = os.environ.get("SOCIALPUSH_SHOTS", "")
#: SOCIALPUSH_LOOKS=phone/light[,desk/dark] runs section 7 in those looks only (calibration).
LOOKS = [x for x in os.environ.get("SOCIALPUSH_LOOKS", "").split(",") if x]
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALPUSH {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on says so as a red row, and the run
    goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence nudges work.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the stand-in push service --------------------------------------------------
# Every POST is kept as it came; /gone/... answers 410 and /lost/... 404, as a
# push service says a device is no more.
CAPTURED = []


class _Cap(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        CAPTURED.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                         "body": body, "at": time.time()})
        code = 410 if self.path.startswith("/gone/") else 404 if self.path.startswith("/lost/") else 201
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


CAP = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Cap)
CAP_ORIGIN = f"http://127.0.0.1:{CAP.server_address[1]}"
threading.Thread(target=CAP.serve_forever, daemon=True).start()

# ---- the demo's own server ----------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="socialpush-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
SECRET = "verify-socialpush-" + secrets.token_hex(8)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY=SECRET,
           SKRIBL_CSRF_PROTECT="1", SKRIBL_SOCIAL_FIRST_INVITE=FIRST, SKRIBL_STAND_IN="0",
           SKRIBL_TRUSTED_PROXIES="1", SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           SOCIAL_PUSH_TEST_ORIGIN=CAP_ORIGIN)
for k in ("SKRIBL_SOCIAL", "SKRIBL_URL_PREFIX", "SKRIBL_FORCE_SECURE_COOKIES", "SKRIBL_DEMO_IDENTITY",
          "SKRIBL_DEMO_LOGIN_KEY", "SKRIBL_SOCIAL_HOSTS", "SKRIBL_SQLITE_FOREIGN_KEYS", "SOCIAL_VAPID_KEY", "RENDER"):
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
    CAP.shutdown()


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

# A PHONE IS A TOUCH PHONE (WORKING-AGREEMENTS): is_mobile and has_touch.
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/18.0 Mobile/15E148 Safari/604.1")
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{120 + _addr[0] // 250}.{_addr[0] % 250}.9"


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


def drawing(n=40, seed=0):
    pts = [{"x": round(408 + (i + seed) % 7 * 20 + i * 3, 1), "y": round(306 + ((i * 7 + seed) % 11) * 9, 1),
            "color": "#7c5cff", "size": 6 + (i % 4), "t": i * 30, "start": i == 0} for i in range(n)]
    return {"version": 2, "schemaVersion": 2, "playbackMode": "replay",
            "canvasSize": {"cssWidth": 816, "cssHeight": 612},
            "frames": [{"strokes": pts, "strokeGroups": [len(pts)], "background": {"color": "#f6f2ea"}}]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """The site's own requests, without a browser, as a signed-in person."""

    def __init__(self, cookies=None, xff=None, origin=BASE):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), _NoRedirect(),
                                              urllib.request.ProxyHandler({}))
        self.xff = xff or address()
        self.origin = origin
        self.token = None
        self.cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in (cookies or []))

    def _req(self, method, path, data=None, headers=None):
        h = {"X-Forwarded-For": self.xff}
        if self.cookie_header:
            h["Cookie"] = self.cookie_header
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

    def post_json(self, path, body, token=None):
        st, text = self._req("POST", path, data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json",
                                      "X-Social-CSRF": (self.token or "") if token is None else token})
        try:
            return st, json.loads(text)
        except ValueError:
            return st, text

    def post_form(self, path, fields):
        data = urllib.parse.urlencode(dict(fields, csrf=self.token or "")).encode()
        return self._req("POST", path, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})[0]


class Person:
    """One browser with its own passkey, from an address of its own."""

    def __init__(self, b):
        self.xff = address()
        self.ctx = b.new_context(extra_http_headers={"X-Forwarded-For": self.xff}, **DESK)
        self.ctx.add_init_script(WATCH)
        self.pg = self.ctx.new_page()
        self.pg.on("pageerror", lambda e: ERRS.append(f"pageerror: {e} @ {self.pg.url}"))
        cdp = self.ctx.new_cdp_session(self.pg)
        cdp.send("WebAuthn.enable")
        cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
            "protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True,
            "isUserVerified": True, "automaticPresenceSimulation": True}})
        self.handle = None

    def client(self):
        c = Client(cookies=self.ctx.cookies(BASE), xff=self.xff)
        c.get("/social/")
        return c

    def id(self):
        return db("select id from social_people where handle_key = ?", (self.handle.lower(),))[0][0]


_people = {}


def member(b, handle, name):
    """Somebody who joined through an invite, signed in, in a browser of their own."""
    p = Person(b)
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


def make_post(who, words, seed=0):
    st, j = who.client().post_json("/social/posts", {"words": words, "payload": drawing(seed=seed)})
    return j.get("post") if st == 200 and isinstance(j, dict) else None


def comment(who, post, words, answer_to=None, payload=None):
    c = who.client()
    c.get(f"/social/p/{post}")
    body = {"words": words}
    if answer_to:
        body["answer_to"] = answer_to
    if payload is not None:
        body["payload"] = payload
    st, j = c.post_json(f"/social/p/{post}/comments", body)
    return j.get("comment") if st == 200 and isinstance(j, dict) else None


# ---- devices, and what they are handed ---------------------------------------------
DEVICES = {}


def device(name, where=None):
    """A device's own keys, as a browser makes them, and its address at the
    stand-in (or `where`): (endpoint, keys for /push/subscribe)."""
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    endpoint = where or f"{CAP_ORIGIN}/ep/{name}"
    DEVICES[urllib.parse.urlsplit(endpoint).path] = (key, pub, auth)
    return endpoint, {"p256dh": b64(pub), "auth": b64(auth)}


def subscribe(who, name):
    endpoint, keys = device(name)
    st, j = who.client().post_json("/social/push/subscribe", {"endpoint": endpoint, "keys": keys})
    return endpoint, st, j


def opened(cap):
    """A nudge as the device opens it (RFC 8291, the receiving side): its
    JSON, or {"unopened": why}."""
    key, pub, auth = DEVICES.get(cap["path"], (None, None, None))
    if key is None:
        return {"unopened": "no such device"}
    body = cap["body"]
    try:
        salt, rs, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
        as_pub, ct = body[21:21 + idlen], body[21 + idlen:]
        shared = key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
        ikm = HKDF(hashes.SHA256(), 32, salt=auth, info=b"WebPush: info\x00" + pub + as_pub).derive(shared)
        cek = HKDF(hashes.SHA256(), 16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
        nonce = HKDF(hashes.SHA256(), 12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
        plain = AESGCM(cek).decrypt(nonce, ct, None).rstrip(b"\x00")
        if rs != 4096 or not plain.endswith(b"\x02"):
            return {"unopened": f"record size {rs}, delimiter {plain[-1:]!r}"}
        return json.loads(plain[:-1])
    except Exception as exc:  # noqa: BLE001
        return {"unopened": repr(exc)}


def signed(cap, endpoint):
    """Whether the Authorization header is a VAPID JWT (RFC 8292) that
    verifies with its own key, for this push service's origin, good for no
    more than a day, from the site: (ok, what it says)."""
    m = re.fullmatch(r"vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=([\w-]+)", cap["headers"].get("authorization", ""))
    if not m:
        return False, {"header": cap["headers"].get("authorization", "")[:60]}
    head, claims, sig, k = m.groups()
    try:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(k))
        raw = unb64(sig)
        pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
                   f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))
        h, c = json.loads(unb64(head)), json.loads(unb64(claims))
    except Exception as exc:  # noqa: BLE001
        return False, {"error": repr(exc)}
    parts = urllib.parse.urlsplit(endpoint)
    now = time.time()
    ok = (h == {"typ": "JWT", "alg": "ES256"} and c.get("aud") == f"{parts.scheme}://{parts.netloc}"
          and now < c.get("exp", 0) <= now + 86400 and c.get("sub") == BASE + "/social/")
    return ok, {"head": h, "claims": c, "k": k}


def nudges(endpoint, since, want=1, wait=8.0):
    """What the stand-in was handed for `endpoint` after the first `since`
    captures, opened, once `want` have come (or `wait` seconds have gone)."""
    path = urllib.parse.urlsplit(endpoint).path
    end = time.time() + wait
    while True:
        got = [c for c in CAPTURED[since:] if c["path"] == path]
        if len(got) >= want or time.time() > end:
            return [dict(opened(c), _cap=c) for c in got]
        time.sleep(0.05)


def quiet(endpoint, since, wait=1.6):
    """Nothing for `endpoint` after `since`, given the moment a nudge takes."""
    return nudges(endpoint, since, want=10 ** 6, wait=wait)


def row_of(endpoint):
    got = db("select person_id, replies, mentions, likes, follows, reposts, badge, gen, browser, told_up_to"
             " from social_push_subscriptions where endpoint = ?", (endpoint,))
    return got[0] if got else None


DEFAULTS = (1, 1, 0, 0, 0, 1)

# ---- the pages: a stand-in for the browser's push service ------------------------------
# Chromium here cannot reach a real push service, so the page's PushManager
# hands out a subscription of the stand-in's (its keys the suite's own), kept
# in the page's storage as a browser keeps one. Everything else is the real
# thing: the permission, the service worker, the site's routes.
STUB = """(() => {
  const EP = %s, P = %s, A = %s, KEPT = 'suite.push.sub';
  if (!window.PushManager) return;
  const fake = (opts) => ({ endpoint: EP, expirationTime: null,
    options: opts || { userVisibleOnly: true, applicationServerKey: null },
    toJSON() { return { endpoint: EP, expirationTime: null, keys: { p256dh: P, auth: A } }; },
    unsubscribe() { try { localStorage.removeItem(KEPT); } catch (e) {} return Promise.resolve(true); } });
  PushManager.prototype.subscribe = function (opts) {
    window.__subscribed = (window.__subscribed || 0) + 1;
    try { localStorage.setItem(KEPT, '1'); } catch (e) {}
    return Promise.resolve(fake(opts));
  };
  PushManager.prototype.getSubscription = function () {
    let kept = null;
    try { kept = localStorage.getItem(KEPT); } catch (e) {}
    return Promise.resolve(kept ? fake(null) : null);
  };
})();"""
DENIED = "Object.defineProperty(Notification, 'permission', { get: () => 'denied', configurable: true });"
NO_PUSH = "try { delete window.PushManager; } catch (e) {}"
# When the page's own scripts have all run (DOMContentLoaded follows the last deferred one).
DCL = "document.addEventListener('DOMContentLoaded', () => { window.__dcl = performance.now(); });"

# Every word in a box against what is painted behind it, each see-through
# layer laid over what is under it (a pressed switch's pill over its track);
# the buttons' sizes; anything wider than the screen.
MEASURE_JS = r"""(sel) => {
  const box = document.querySelector(sel); if (!box) return null;
  const rgb = s => { const m = (s.match(/[\d.]+/g) || []).map(Number);
    return /^color\(srgb/.test(s) ? [m[0] * 255, m[1] * 255, m[2] * 255, m.length > 3 ? m[3] : 1] : m; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const over = (t, g) => t.length > 3 && t[3] < 1 ? [0, 1, 2].map(k => t[k] * t[3] + g[k] * (1 - t[3])) : t.slice(0, 3);
  const ground = el => { const layers = [];
    for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor);
      if (c.length >= 3 && (c.length < 4 || c[3] > 0)) { layers.push(c); if (c.length < 4 || c[3] >= 0.999) break; } }
    let acc = rgb(getComputedStyle(document.body).backgroundColor).slice(0, 3);
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc); return acc; };
  const out = [];
  box.querySelectorAll('*').forEach(e => {
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    const r = e.getBoundingClientRect(); if (!r.width || getComputedStyle(e).visibility === 'hidden') return;
    let g = ground(e);
    const pill = e.closest('.theme-switch') && e.getAttribute('aria-pressed') === 'true'
      ? e.parentElement.querySelector('.theme-pill') : null;
    if (pill) g = over(rgb(getComputedStyle(pill).backgroundColor), ground(pill.parentElement));
    out.push([e.textContent.trim().slice(0, 30), Math.round(ratio(rgb(getComputedStyle(e).color), g) * 100) / 100]); });
  const buttons = [...box.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width > 0)
    .map(b => { const r = b.getBoundingClientRect(); return [b.textContent.trim(), Math.round(r.width), Math.round(r.height)]; });
  return { least: Math.min(...out.map(o => o[1])), words: out.length, low: out.filter(o => o[1] < 4.5),
           small: buttons.filter(x => x[1] < 44 || x[2] < 44), buttons,
           wide: document.scrollingElement.scrollWidth - innerWidth }; }"""

# The card's room, read on every animation frame for a while.
FRAMES_JS = """([sel, ms]) => new Promise(done => {
  const el = document.querySelector(sel), hs = [], t0 = performance.now();
  const step = () => { hs.push(el.hidden ? 0 : Math.round(el.getBoundingClientRect().height * 100) / 100);
    if (performance.now() - t0 < ms) requestAnimationFrame(step); else done(hs); };
  requestAnimationFrame(step); })"""


# On a copy of the database, the site's code with SQLite's cascade OFF
# (SKRIBL_SQLITE_FOREIGN_KEYS=0, the documented opt-out): an account deleted
# takes its devices because the code says so, not the cascade.
PROBE = r"""
import json, sys
from app import create_app, db
import sqlalchemy as sa
app = create_app()
with app.app_context():
    from social.models import Person, PushSubscription
    from social.accounts import delete_person
    fk = db.session.execute(sa.text("PRAGMA foreign_keys")).scalar()
    who = db.session.execute(sa.select(Person).where(Person.handle_key == sys.argv[1])).scalar_one()
    had = db.session.execute(sa.select(sa.func.count()).select_from(PushSubscription)
                             .where(PushSubscription.person_id == who.id)).scalar()
    others = db.session.execute(sa.select(sa.func.count()).select_from(PushSubscription)
                                .where(PushSubscription.person_id != who.id)).scalar()
    pid = who.id
    delete_person(db.session, pid)
    db.session.commit()
    left = db.session.execute(sa.select(sa.func.count()).select_from(PushSubscription)
                              .where(PushSubscription.person_id == pid)).scalar()
    kept = db.session.execute(sa.select(sa.func.count()).select_from(PushSubscription)
                              .where(PushSubscription.person_id != pid)).scalar()
    print(json.dumps({"fk": fk, "had": had, "left": left, "others": others, "kept": kept}))
"""


def browser_as(b, who, screen="phone", scheme="light", reduced=False, init=(), grant=False, ua=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    if ua:
        kw["user_agent"] = ua
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff},
                        **(PHONE if screen == "phone" else DESK), **kw)
    if grant:
        ctx.grant_permissions(["notifications"], origin=BASE)
    ctx.add_init_script(WATCH)
    for s in init:
        ctx.add_init_script(s)
    ctx.add_cookies([{k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly",
                                                         "sameSite", "secure", "expires")}
                     for c in who.ctx.cookies(BASE)])
    pg = ctx.new_page()
    tag = f"{screen}/{scheme}{' reduced' if reduced else ''} as {who.handle}"
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


def go(pg, path, wait=500):
    r = pg.goto(BASE + path)
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def glide(hs):
    """How a room moved over frames: the frames it moved on, its largest step,
    the whole way."""
    steps = [abs(b - a) for a, b in zip(hs, hs[1:])]
    return {"frames": len([s for s in steps if s > 0.5]), "step": round(max(steps or [0]), 2),
            "way": round(abs(hs[-1] - hs[0]), 2) if hs else 0}


with sync_playwright() as p:
    # Chromium's own headless (channel "chromium", as verify_social's back
    # button asks for): the headless shell says no to every notification, and
    # grants none, so it could not show a page that asks.
    b = p.chromium.launch(channel="chromium")
    ann = member(b, "ann", "Ann Lark")
    bea = member(b, "bea", "Bea Moss")
    cyd = member(b, "cyd", "Cyd Fern")
    dov = member(b, "dov", "Dov Reed")
    KEY = re.search(r'<meta name="social-push" content="([^"]+)"', ann.client().get("/social/you")[1])
    KEY = KEY.group(1) if KEY else ""

    # ------------------------------------------------------------------ 1
    if part(1, "the seal and the signature"):
        try:
            import social.push as push
            # RFC 8291, section 5: its keys, its salt, its words, its message.
            ex = {"as": "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw",
                  "ua": "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
                  "auth": "BTBZMqHH6r4Tts7J_aSIgg", "salt": "DGv6ra1nlYgDCS1FRnbzlw",
                  "out": "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8"
                         "wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"}
            as_key = ec.derive_private_key(int.from_bytes(unb64(ex["as"]), "big"), ec.SECP256R1())
            real = (push.ec.generate_private_key, push.os.urandom)
            push.ec.generate_private_key = lambda curve: as_key
            push.os.urandom = lambda n: unb64(ex["salt"])
            try:
                made = push.seal(ex["ua"], ex["auth"], b"When I grow up, I want to be a watermelon")
            finally:
                push.ec.generate_private_key, push.os.urandom = real
            check("a nudge is sealed as RFC 8291 says: its worked example (section 5), sealed with its own keys and"
                  " salt, comes out byte for byte (aes128gcm, one 4096-byte record)", made == unb64(ex["out"]),
                  b64(made)[:48] + "…")

            from flask import Flask

            def key_for(secret, own=None):
                app = Flask("k")
                app.config["SECRET_KEY"] = secret
                if own is not None:
                    app.config["SOCIAL_VAPID_KEY"] = own
                return push.public_key(app)
            one, again, other = key_for(SECRET), key_for(SECRET), key_for(SECRET + "x")
            own = ec.generate_private_key(ec.SECP256R1())
            pem = own.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()).decode()
            own_pub = b64(own.public_key().public_bytes(serialization.Encoding.X962,
                                                        serialization.PublicFormat.UncompressedPoint))
            check("the site's signing key comes from its SECRET_KEY, the same every time for the same secret and"
                  " another for another, and SOCIAL_VAPID_KEY's own where it is set (nothing new to keep)",
                  one == again and one != other and key_for(SECRET, pem) == own_pub and len(unb64(one)) == 65,
                  f"{one[:12]}… {other[:12]}…")
            check("a page of somebody signed in hands out that key (base.html's social-push meta), the service"
                  " worker's address and the site's own folder as its scope", KEY == one and
                  re.search(r'<meta name="social-push" content="[^"]+" data-mark="[0-9a-f]{16}" data-sw="/social/sw.js"'
                            r' data-scope="/social/">', ann.client().get("/social/")[1]) is not None, KEY[:16])
            st, text = Client().get("/social/")
            check("a page for somebody signed out hands out nothing of the kind, nor push.js",
                  st == 200 and "social-push" not in text and "push.js" not in text, str(st))
            with urllib.request.urlopen(BASE + "/social/sw.js", timeout=10) as r:
                sw = (r.status, r.headers.get("Content-Type", ""), r.headers.get("Cache-Control", ""), r.read().decode())
            check("the service worker is the site's own push-sw.js, served from its own folder as JavaScript and"
                  " asked again each time (no-cache)", sw[0] == 200 and sw[1].startswith("text/javascript")
                  and sw[2] == "no-cache" and sw[3] == (ROOT / "social/static/push-sw.js").read_text(encoding="utf-8"),
                  f"{sw[:3]}")
        except Exception as exc:  # noqa: BLE001
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "where a nudge may go"):
        try:
            ep, st, j = subscribe(ann, "ann-1")
            row = row_of(ep)
            check("a device's address and keys, handed over by somebody signed in, are kept with their sign-in"
                  " (their session's generation and a mark of this browser's sign-in), starting at the dot's rule:"
                  " replies and comments, mentions and the number on; likes, follows, reposts off",
                  st == 200 and isinstance(j, dict) and j.get("on") == {"replies": True, "mentions": True, "likes": False,
                                                                       "follows": False, "reposts": False, "badge": True}
                  and row is not None and row[0] == ann.id() and tuple(row[1:7]) == DEFAULTS and row[7] == 1
                  and re.fullmatch(r"[0-9a-f]{64}", row[8] or ""), f"{st} {j} {row}")
            c = ann.client()
            _, keys = device("ann-x")
            refused = {}
            for what, where in (("http to a push service", "http://fcm.googleapis.com/fcm/send/x"),
                                ("another port", "https://fcm.googleapis.com:8443/fcm/send/x"),
                                ("a name in it", "https://me@fcm.googleapis.com/fcm/send/x"),
                                ("a host that only ends like one", "https://evilpush.apple.com.example/x"),
                                ("a host of its own", "https://example.com/push/x"),
                                ("the stand-in's lookalike", CAP_ORIGIN.replace("127.0.0.1", "127.0.0.2") + "/ep/x"),
                                ("the stand-in on another port", f"http://127.0.0.1:{free_port()}/ep/x"),
                                ("no address", None)):
                st2, j2 = c.post_json("/social/push/subscribe", {"endpoint": where, "keys": keys})
                refused[what] = (st2, j2.get("error") if isinstance(j2, dict) else j2)
            check("any other address is refused (400, endpoint): http, another port, a name in it, a host that only"
                  " ends like a push service's, a host of its own, the stand-in's lookalike and its other ports,"
                  " none: nobody can make the site send to an address of their choosing",
                  all(v == (400, "endpoint") for v in refused.values()), json.dumps(refused))
            ok_hosts = [push_host for push_host in ("https://web.push.apple.com/QGx", "https://fcm.googleapis.com/fcm/send/a:b",
                                                    "https://updates.push.services.mozilla.com/wpush/v2/x",
                                                    "https://wns2-par02p.notify.windows.com/w/?token=x")]
            took = []
            for where in ok_hosts:
                _, k2 = device("real-" + str(len(took)), where)
                st3, _ = c.post_json("/social/push/subscribe", {"endpoint": where, "keys": k2})
                took.append(st3)
            check("the push services browsers use are taken: Apple's, Google's, Mozilla's and Microsoft's (https)",
                  took == [200, 200, 200, 200], str(took))
            bad = {}
            for what, k3 in (("a key too short", {"p256dh": b64(b"\x04" + os.urandom(31)), "auth": keys["auth"]}),
                             ("a key not a point", {"p256dh": b64(b"\x05" + os.urandom(64)), "auth": keys["auth"]}),
                             ("a secret too long", {"p256dh": keys["p256dh"], "auth": b64(os.urandom(32))}),
                             ("no keys", None)):
                st4, j4 = c.post_json("/social/push/subscribe", {"endpoint": f"{CAP_ORIGIN}/ep/ann-bad", "keys": k3})
                bad[what] = (st4, j4.get("error") if isinstance(j4, dict) else j4)
            check("keys that are not a device's are refused (400, keys)", all(v == (400, "keys") for v in bad.values()),
                  json.dumps(bad))
            body = {"endpoint": f"{CAP_ORIGIN}/ep/ann-guard", "keys": keys}
            st5, _ = c.post_json("/social/push/subscribe", body, token="")
            other = Client(cookies=ann.ctx.cookies(BASE), xff=ann.xff, origin="https://elsewhere.example")
            other.get("/social/")
            st6, _ = other.post_json("/social/push/subscribe", body)
            nobody = Client()
            nobody.get("/social/signin")         # a signed-out page with its own token
            st7, _ = nobody.post_json("/social/push/subscribe", body)
            check("without the page's token, or from another origin, it is refused (403); signed out, 401; and"
                  " nothing is kept", (st5, st6, st7) == (403, 403, 401) and row_of(body["endpoint"]) is None,
                  str((st5, st6, st7)))
            guarded = {}
            for path in ("/social/push/state", "/social/push/prefs", "/social/push/unsubscribe"):
                guarded[path] = (nobody.post_json(path, {"endpoint": ep})[0],
                                 c.post_json(path, {"endpoint": ep}, token="")[0])
            check("its state, its switches and turning it off are as guarded (signed out: 401; no token: 403), and"
                  " the device is still there", all(v == (401, 403) for v in guarded.values())
                  and row_of(ep) is not None, json.dumps(guarded))
            again = {"p256dh": b64(DEVICES["/ep/ann-1"][1]), "auth": b64(DEVICES["/ep/ann-1"][2])}
            st9, j9 = c.post_json("/social/push/subscribe", {"endpoint": ep, "keys": again})
            check("the same device handed over again is still one device", st9 == 200 and
                  db("select count(*) from social_push_subscriptions where endpoint = ?", (ep,))[0][0] == 1, str(st9))
            for where in ok_hosts:
                db_write("delete from social_push_subscriptions where endpoint = ?", (where,))
        except Exception as exc:  # noqa: BLE001
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    E1 = f"{CAP_ORIGIN}/ep/ann-1"
    POST1 = POST2 = None
    if part(3, "what buzzes: the dot's rule, in Activity's words"):
        try:
            if row_of(E1) is None:
                subscribe(ann, "ann-1")
            POST1 = make_post(ann, "My little house", seed=1)
            POST2 = make_post(ann, "A cat on a wall", seed=2)
            n0 = len(CAPTURED)
            c1 = comment(bea, POST1, "Love the little curl of smoke")
            got = nudges(E1, n0)
            one = got[0] if got else {}
            cap = one.get("_cap", {"headers": {}})
            ok_sig, said = signed(cap, E1) if got else (False, {})
            check("something said on your post buzzes your device once, sealed for it alone (it opens with the"
                  " device's own keys)", len(got) == 1 and "unopened" not in one, f"{len(got)} {str(one)[:160]}")
            check("in Activity's words, word for word: \"Bea said something on your post\", their words in quotes"
                  " under it", one.get("title") == "Bea said something on your post"
                  and one.get("body") == "“Love the little curl of smoke”", f"{one.get('title')!r} {one.get('body')!r}")
            check("a tap opens the comment where it shows (Activity's own link), and it carries the site's icon",
                  one.get("url") == f"/social/p/{POST1}#c-{c1}" and str(one.get("icon", "")).startswith("/social/static/blooby-icon-192"),
                  f"{one.get('url')} {one.get('icon')}")
            check("it is signed as the site: a VAPID JWT (ES256) that verifies with its own key, the page's key, for"
                  " the push service's origin, good for no more than a day, from the site's own address", ok_sig
                  and said.get("k") == KEY, json.dumps(said)[:300])
            h = cap["headers"]
            check("as a push service wants it: aes128gcm, a day to live, normal urgency, and a Topic of its tag"
                  " (a phone that was off is handed the newest only)", h.get("content-encoding") == "aes128gcm"
                  and h.get("ttl") == "86400" and h.get("urgency") == "normal"
                  and re.fullmatch(r"[\w-]{1,32}", h.get("topic", "")) is not None, json.dumps(
                      {k: h.get(k) for k in ("content-encoding", "ttl", "urgency", "topic")}))
            check("the number on the icon is how many new things light the dot (one)", one.get("badge") == 1,
                  str(one.get("badge")))
            n1 = len(CAPTURED)
            comment(cyd, POST1, "Smoke like a ribbon")
            two = (nudges(E1, n1) or [{}])[0]
            check("two on one post say so as Activity does, \"Cyd and Bea said something on your post\", under the"
                  " same tag and Topic, so the phone puts the newest in place of the last",
                  two.get("title") == "Cyd and Bea said something on your post" and two.get("tag") == one.get("tag")
                  and two.get("_cap", {}).get("headers", {}).get("topic") == h.get("topic") and two.get("badge") == 1,
                  f"{two.get('title')!r} {two.get('tag')} {one.get('tag')}")
            n2 = len(CAPTURED)
            mine = comment(ann, POST2, "Our cat lives there")
            check("what you say yourself never buzzes you", quiet(E1, n2) == [], "")
            n3 = len(CAPTURED)
            comment(bea, POST2, "It is a lovely cat", answer_to=mine)
            three = (nudges(E1, n3) or [{}])[0]
            check("a reply to you: \"Bea replied to your comment\", their words, the number two",
                  three.get("title") == "Bea replied to your comment" and three.get("body") == "“It is a lovely cat”"
                  and three.get("badge") == 2, f"{three.get('title')!r} {three.get('badge')}")
            n4 = len(CAPTURED)
            drawn = comment(bea, POST2, "", answer_to=mine, payload=drawing(seed=5))
            four = (nudges(E1, n4) or [{}])[0]
            check("a drawn reply: \"Bea replied with a drawing\", \"Tap to watch it draw.\", a tag of its own, and"
                  " a tap opens it", four.get("title") == "Bea replied with a drawing"
                  and four.get("body") == "Tap to watch it draw." and four.get("tag") != three.get("tag")
                  and str(four.get("url", "")).endswith(f"#c-{drawn}") and four.get("badge") == 3,
                  f"{four.get('title')!r} {four.get('body')!r} {four.get('url')}")
            n5 = len(CAPTURED)
            st, _ = bea.client().post_json("/social/posts", {"words": "Look at this @ann, a cottage",
                                                             "payload": drawing(seed=6)})
            five = (nudges(E1, n5) or [{}])[0]
            check("a mention: \"Bea mentioned you\", their words, the number four", st == 200
                  and five.get("title") == "Bea mentioned you" and five.get("body") == "“Look at this @ann, a cottage”"
                  and five.get("badge") == 4, f"{st} {five.get('title')!r} {five.get('badge')}")
            n6 = len(CAPTURED)
            st_l, _ = bea.client().post_json(f"/social/p/{POST1}/like", {"liked": True})
            st_f, _ = bea.client().post_json("/social/@ann/follow", {"following": True})
            st_r, _ = cyd.client().post_json(f"/social/p/{POST2}/repost", {"reposted": True})
            check("a like, a follow and a repost wait quietly in Activity: their switches start off",
                  (st_l, st_f, st_r) == (200, 200, 200) and quiet(E1, n6, wait=2.0) == [], str((st_l, st_f, st_r)))
            c = ann.client()
            st_p, j_p = c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "likes", "on": True})
            n7 = len(CAPTURED)
            cyd.client().post_json(f"/social/p/{POST1}/like", {"liked": True})
            six = (nudges(E1, n7) or [{}])[0]
            check("with Likes switched on for this device, a like buzzes it: \"Cyd and Bea liked your post\" (the"
                  " number still four: likes never light the dot)", st_p == 200 and (j_p.get("on") or {}).get("likes") is True
                  and six.get("title") == "Cyd and Bea liked your post" and six.get("badge") == 4,
                  f"{st_p} {six.get('title')!r} {six.get('badge')}")
            c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "badge", "on": False})
            n8 = len(CAPTURED)
            comment(dov, POST1, "Hello from Dov")
            seven = (nudges(E1, n8) or [{}])[0]
            check("with the number switched off, a nudge leaves the icon's number alone (badge null)",
                  "badge" in seven and seven.get("badge") is None, str(seven.get("badge")))
            st_x, j_x = c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "everything", "on": True})
            st_y, j_y = c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "likes", "on": "yes"})
            check("a switch that is not one, or a choice that is not on or off, is refused (400)",
                  (st_x, st_y) == (400, 400), str((st_x, st_y)))
            c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "badge", "on": True})
            c.post_json("/social/push/prefs", {"endpoint": E1, "kind": "likes", "on": False})
        except Exception as exc:  # noqa: BLE001
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "never what Activity leaves out, never twice"):
        try:
            if row_of(E1) is None:
                subscribe(ann, "ann-1")
            POST3 = make_post(ann, "Clouds over the hill", seed=3)
            st_m, _ = ann.client().post_json("/social/@dov/mute", {})
            n0 = len(CAPTURED)
            comment(bea, POST3, "What a sky")
            first = nudges(E1, n0)
            n1 = len(CAPTURED)
            comment(dov, POST3, "Muted words")
            check("somebody you muted makes no nudge (Activity has no row of theirs), and does not buzz the row"
                  " before it again, though it is moments old (a device is never told a row it was told)",
                  st_m == 200 and len(first) == 1 and first[0].get("title") == "Bea said something on your post"
                  and quiet(E1, n1, wait=2.0) == [], f"{st_m} {len(first)}")
            told = row_of(E1)[9]
            check("the device keeps the time of the newest row it was told about", bool(told), str(told))
        except Exception as exc:  # noqa: BLE001
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "gone devices"):
        try:
            if row_of(E1) is None:
                subscribe(ann, "ann-1")
            gone, keys = device("x", f"{CAP_ORIGIN}/gone/ann")
            lost, keys2 = device("y", f"{CAP_ORIGIN}/lost/ann")
            c = ann.client()
            c.post_json("/social/push/subscribe", {"endpoint": gone, "keys": keys})
            c.post_json("/social/push/subscribe", {"endpoint": lost, "keys": keys2})
            POST4 = make_post(ann, "Rain on the roof", seed=4)
            n0 = len(CAPTURED)
            comment(bea, POST4, "Pitter patter")
            nudges(gone, n0)
            nudges(lost, n0)
            nudges(E1, n0)
            for _ in range(60):
                if row_of(gone) is None and row_of(lost) is None:
                    break
                time.sleep(0.1)
            check("a device its push service says is gone (410) or not there (404) is taken away when a nudge finds"
                  " it so, and the others keep theirs", row_of(gone) is None and row_of(lost) is None
                  and row_of(E1) is not None, f"{row_of(gone)} {row_of(lost)}")
        except Exception as exc:  # noqa: BLE001
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "the sign-in"):
        try:
            eve = member(b, "eve", "Eve Stone")
            here, st, _ = subscribe(eve, "eve-here")
            elsewhere, keys = device("eve-else")
            db_write("insert into social_push_subscriptions (person_id, endpoint, p256dh, auth, gen, browser, replies,"
                     " mentions, likes, follows, reposts, badge, created_at) values (?, ?, ?, ?, 1, ?, 1, 1, 0, 0, 0, 1,"
                     " '2026-11-18 00:00:00')", (eve.id(), elsewhere, keys["p256dh"], keys["auth"], "f" * 64))
            c = eve.client()
            st_out = c.post_form("/social/signout", {})
            check("signing out here takes this browser's device with it, and leaves one another browser made",
                  st == 200 and st_out == 303 and row_of(here) is None and row_of(elsewhere) is not None,
                  f"{st} {st_out} {row_of(here)} {row_of(elsewhere) is not None}")
            fay = member(b, "fay", "Fay Holt")
            f_here, _, _ = subscribe(fay, "fay-here")
            f_else, keys = device("fay-else")
            db_write("insert into social_push_subscriptions (person_id, endpoint, p256dh, auth, gen, browser, replies,"
                     " mentions, likes, follows, reposts, badge, created_at) values (?, ?, ?, ?, 1, ?, 1, 1, 0, 0, 0, 1,"
                     " '2026-11-18 00:00:00')", (fay.id(), f_else, keys["p256dh"], keys["auth"], "f" * 64))
            st_all = fay.client().post_form("/social/signout/everywhere", {})
            check("Sign out everywhere takes every device of theirs", st_all == 303 and row_of(f_here) is None
                  and row_of(f_else) is None, f"{st_all}")
            # A device from before Sign out everywhere (an older generation), as
            # if the drop had missed it: never nudged, and taken away.
            old, keys = device("bea-old")
            db_write("insert into social_push_subscriptions (person_id, endpoint, p256dh, auth, gen, browser, replies,"
                     " mentions, likes, follows, reposts, badge, created_at) values (?, ?, ?, ?, 0, ?, 1, 1, 0, 0, 0, 1,"
                     " '2026-11-18 00:00:00')", (bea.id(), old, keys["p256dh"], keys["auth"], "e" * 64))
            BPOST = make_post(bea, "Bea's kite", seed=8)
            n0 = len(CAPTURED)
            comment(cyd, BPOST, "Fly it high")
            for _ in range(60):
                if row_of(old) is None:
                    break
                time.sleep(0.1)
            check("a device from before Sign out everywhere (an older generation) is never nudged, and is taken"
                  " away", quiet(old, n0, wait=0.5) == [] and row_of(old) is None, str(row_of(old)))
            if row_of(E1) is None:
                subscribe(ann, "ann-1")
            st_s, j_s = cyd.client().post_json("/social/push/state", {"endpoint": E1})
            check("another account signed in on a device (it asks the device's state, as push.js does each new"
                  " sign-in) stops it being the last one's: it says nothing is on, and the device is let go",
                  st_s == 200 and j_s.get("on") is None and row_of(E1) is None, f"{st_s} {j_s}")
            _, k1 = device("ann-1")
            subscribe(ann, "ann-1")
            ann.client().post_json("/social/push/prefs", {"endpoint": E1, "kind": "likes", "on": True})
            st_t, j_t = cyd.client().post_json("/social/push/subscribe",
                                               {"endpoint": E1, "keys": {"p256dh": b64(DEVICES["/ep/ann-1"][1]),
                                                                          "auth": b64(DEVICES["/ep/ann-1"][2])}})
            row = row_of(E1)
            check("and one who turns nudges on there takes it, starting at the dot's rule again (Ann's Likes switch"
                  " does not come with it)", st_t == 200 and row is not None and row[0] == cyd.id()
                  and tuple(row[1:7]) == DEFAULTS and row[9] is None, str(row))
            st_u, _ = cyd.client().post_json("/social/push/unsubscribe", {"endpoint": E1})
            check("turning it off there lets it go", st_u == 200 and row_of(E1) is None, str(st_u))
            gil = member(b, "gil", "Gil Ward")
            g_here, _, _ = subscribe(gil, "gil-here")
            copy = os.path.join(TMP, "cascade-off.db")
            src, dst = sqlite3.connect(DB), sqlite3.connect(copy)
            src.backup(dst)
            src.close()
            dst.close()
            probe = subprocess.run([sys.executable, "-c", PROBE, "gil"], cwd=ROOT, capture_output=True, text=True,
                                   timeout=180, env=dict(ENV, DATABASE_URL=f"sqlite:///{copy}",
                                                         SKRIBL_SQLITE_FOREIGN_KEYS="0"))
            try:
                out = json.loads(probe.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                out = {"err": (probe.stderr or probe.stdout)[-400:]}
            check("deleting an account, with SQLite's cascade off (on a copy), takes its devices in code, and leaves"
                  " everybody else's", out.get("fk") == 0 and out.get("had") == 1 and out.get("left") == 0
                  and out.get("others", 0) >= 1 and out.get("kept") == out.get("others"), json.dumps(out))
            c = gil.client()
            c.get("/social/you/delete")
            st_d = c.post_form("/social/you/delete", {"confirm": "gil"})
            check("an account deleted takes its devices with it", st_d in (200, 303) and row_of(g_here) is None
                  and not db("select id from social_people where handle_key = 'gil'"), f"{st_d} {row_of(g_here)}")
            subscribe(ann, "ann-1")
        except Exception as exc:  # noqa: BLE001
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "the pages: Activity's card and Settings' panel"):
        try:
            for screen in ("phone", "desk"):
                for scheme in ("light", "dark"):
                    look = f"{screen}/{scheme}"
                    if LOOKS and look not in LOOKS:
                        continue
                    hal = member(b, f"h{screen[0]}{scheme[0]}", "Hal Pine")
                    ep_h, keys = device(f"{hal.handle}-page")
                    stub = STUB % (json.dumps(ep_h), json.dumps(keys["p256dh"]), json.dumps(keys["auth"]))
                    # Asked: a device that can be nudged and was never asked.
                    ctx, pg = browser_as(b, hal, screen, scheme, init=[stub])
                    st = go(pg, "/social/activity", wait=900)
                    card = pg.evaluate("""() => { const f = document.querySelector('[data-push-ask]');
                      const s = f && f.querySelector('.push-ask'); const r = s && s.getBoundingClientRect();
                      const word = f && f.querySelector('[data-push-device]');
                      return f && { hidden: f.hidden, open: f.classList.contains('is-open'), h: r && r.height,
                        title: f.querySelector('#pushAskTitle').textContent, word: word && word.textContent,
                        words: f.querySelector('.panel-sub').textContent,
                        acts: [...f.querySelectorAll('.post-sheet-acts .btn')].map(x => x.textContent.trim()),
                        painted: (() => { const b = f.querySelector('[data-push-on]').getBoundingClientRect();
                          const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
                          return !!e && !!e.closest('[data-push-on]'); })() }; }""")
                    word = "phone" if screen == "phone" else "computer"
                    check(f"{look}: Activity asks once, a card at its top: \"Hear when someone answers you\", what"
                          f" buzzes and what waits, on this {word}, then Not now and Turn on, painted",
                          st == 200 and card and not card["hidden"] and card["open"] and card["word"] == word
                          and card["title"] == "Hear when someone answers you"
                          and card["words"] == f"A nudge on this {word} when someone replies to you, says something on"
                          " your post or mentions you. Likes and follows wait here. Change it any time in Settings."
                          and card["acts"] == ["Not now", "Turn on"] and card["painted"], json.dumps(card)[:300])
                    if SHOTS:
                        pg.wait_for_timeout(500)
                        pg.screenshot(path=os.path.join(SHOTS, f"card-{screen}-{scheme}.png"))
                    m = pg.evaluate(MEASURE_JS, ".push-ask")
                    check(f"{look}: every word on the card 4.5:1 or more on what is painted behind it, both buttons"
                          " 44px or more, nothing wider than the screen", m and m["least"] >= 4.5 and not m["small"]
                          and m["wide"] <= 0 and m["words"] >= 4, json.dumps(m)[:300])
                    hs = pg.evaluate("""() => { const f = document.querySelector('[data-push-ask]');
                      document.querySelector('[data-push-later]').click(); return 1; }""") and \
                        pg.evaluate(FRAMES_JS, ["[data-push-ask]", 700])
                    g = glide(hs)
                    gone = pg.evaluate("() => [document.querySelector('[data-push-ask]').hidden,"
                                       " localStorage.getItem('blooby.push.later')]")
                    check(f"{look}: Not now glides the card away (its room closing over many frames, no step a"
                          " jump), and says so on this device for good", g["frames"] >= 6 and g["step"] < g["way"] * 0.5
                          and gone == [True, "1"], f"{g} {gone}")
                    go(pg, "/social/activity", wait=900)
                    check(f"{look}: Activity does not ask again on this device",
                          pg.evaluate("() => document.querySelector('[data-push-ask]').hidden") is True, "")
                    close_ctx(ctx, pg)
                    # Turn on, from the card: the permission granted, the
                    # service worker made, the device kept.
                    ctx, pg = browser_as(b, hal, screen, scheme, init=[stub], grant=True)
                    go(pg, "/social/activity", wait=900)
                    shown = pg.evaluate("() => !document.querySelector('[data-push-ask]').hidden")
                    pg.click("[data-push-on]")
                    pg.wait_for_function("() => document.querySelector('[data-push-ask]').hidden", timeout=10000)
                    reg = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration('/social/');
                      return r && { scope: r.scope, script: (r.active || r.waiting || r.installing || {}).scriptURL }; }""")
                    row = row_of(ep_h)
                    check(f"{look}: Turn on makes the site's service worker, subscribes this device with the site's"
                          " key, keeps it at the dot's rule, and the card goes", shown and reg
                          and reg["scope"] == BASE + "/social/" and str(reg["script"]).endswith("/social/sw.js")
                          and pg.evaluate("() => window.__subscribed") == 1 and row is not None
                          and tuple(row[1:7]) == DEFAULTS, f"{shown} {reg} {row}")
                    go(pg, "/social/activity", wait=900)
                    check(f"{look}: once this device is nudged, Activity does not ask",
                          pg.evaluate("() => document.querySelector('[data-push-ask]').hidden") is True, "")
                    # A NEW SIGN-IN on this device: its pages ask the site once
                    # about the device (it follows the sign-in), then never again.
                    asked = []
                    pg.on("request", lambda r: asked.append(r.url) if r.url.endswith("/push/state") else None)
                    go(pg, "/social/explore", wait=900)
                    quiet_page = len(asked)
                    pg.evaluate("() => localStorage.setItem('blooby.push.mark', 'a sign-in before')")
                    go(pg, "/social/explore", wait=900)
                    once = len(asked) - quiet_page
                    go(pg, "/social/explore", wait=900)
                    check(f"{look}: a page of a new sign-in asks the site about this device once (so it follows the"
                          " sign-in, or stops being the last one's), and a page of the same sign-in asks nothing",
                          quiet_page == 0 and once == 1 and len(asked) == 1, f"{quiet_page} {once} {len(asked)}")
                    # Settings: a row a kind, Theme's switch, the dot's rule pressed.
                    go(pg, "/social/you", wait=1200)
                    pan = pg.evaluate("""() => { const f = document.querySelector('[data-push-panel]');
                      const rows = [...f.querySelectorAll('.push-row')].map(r => [r.querySelector('.push-name').textContent,
                        r.querySelector('.panel-sub').textContent,
                        r.querySelector('[aria-pressed="true"]') && r.querySelector('[aria-pressed="true"]').textContent]);
                      const pills = [...f.querySelectorAll('.push-sw')].map(sw => { const p = sw.querySelector('.theme-pill').getBoundingClientRect();
                        const b = sw.querySelector('[aria-pressed="true"]').getBoundingClientRect();
                        return Math.abs(p.left - b.left) < 1 && Math.abs(p.width - b.width) < 1 && sw.hasAttribute('data-pill'); });
                      const order = [...document.querySelectorAll('.acct > section, .acct > .push-fold')].map(e => e.getAttribute('aria-labelledby') || 'push');
                      const shown = [...f.querySelectorAll('[data-push-when]')].filter(e => e.getClientRects().length
                        && getComputedStyle(e).display !== 'none').map(e => e.getAttribute('data-push-when'));
                      return { hidden: f.hidden, title: f.querySelector('#pushTitle').textContent, rows, pills, order,
                               on: f.querySelector('[data-push-when="on"]').hidden, shown }; }""")
                    check(f"{look}: Settings has \"Notifications on this {word}\" under Theme, a row a kind with"
                          " Theme's own switch, the dot's rule pressed (Replies and comments, Mentions and the number"
                          " On; Likes, New followers, Reposts and quotes Off), each pill under its choice",
                          not pan["hidden"] and pan["title"] == f"Notifications on this {word}" and not pan["on"]
                          and [r[0] for r in pan["rows"]] == ["Replies and comments", "Mentions", "Likes", "New followers",
                                                              "Reposts and quotes", "The number on the icon"]
                          and [r[2] for r in pan["rows"]] == ["On", "On", "Off", "Off", "Off", "On"]
                          and all(pan["pills"]) and pan["order"][:2] == ["themeTitle", "push"]
                          and pan["shown"] == ["on"], json.dumps(pan)[:400])
                    check(f"{look}: only that state is drawn: no Turn on above switches that are on",
                          pan["shown"] == ["on"], str(pan["shown"]))
                    if SHOTS:
                        pg.evaluate("() => document.querySelectorAll('.nav').forEach(n => { n.style.visibility = 'hidden'; })")
                        pg.evaluate("() => document.querySelector('[data-push-panel]').scrollIntoView({block: 'start'})")
                        pg.wait_for_timeout(300)
                        pg.screenshot(path=os.path.join(SHOTS, f"settings-{screen}-{scheme}.png"))
                        pg.evaluate("() => document.querySelectorAll('.nav').forEach(n => { n.style.visibility = ''; })")
                    m = pg.evaluate(MEASURE_JS, ".push-panel")
                    check(f"{look}: every word on the panel 4.5:1 or more (a pressed choice on its see-through pill"
                          " over the track), every choice 44px, nothing wider than the screen",
                          m and m["least"] >= 4.5 and not m["small"] and m["wide"] <= 0 and m["words"] >= 20,
                          json.dumps({k: m[k] for k in ("least", "low", "small", "wide", "words")}) if m else "none")
                    with pg.expect_response(lambda r: r.url.endswith("/push/prefs"), timeout=8000):
                        pg.click('[data-push-kind="likes"] [data-choice="on"]')
                    pg.wait_for_timeout(400)
                    moved = pg.evaluate("""() => { const sw = document.querySelector('[data-push-kind="likes"]');
                      const p = sw.querySelector('.theme-pill').getBoundingClientRect(), b = sw.querySelector('[data-choice="on"]').getBoundingClientRect();
                      return [sw.querySelector('[aria-pressed="true"]').textContent, Math.abs(p.left - b.left) < 1]; }""")
                    check(f"{look}: a switch moves at once and the site keeps it for this device",
                          moved == ["On", True] and row_of(ep_h)[3] == 1, f"{moved} {row_of(ep_h)}")
                    pg.route("**/push/prefs", lambda r: r.fulfill(status=503, body="{}", content_type="application/json"))
                    pg.click('[data-push-kind="follows"] [data-choice="on"]')
                    pg.wait_for_timeout(500)
                    back = pg.evaluate("""() => [document.querySelector('[data-push-kind="follows"] [aria-pressed="true"]').textContent,
                      document.querySelector('[data-push-panel] .push-said').textContent]""")
                    check(f"{look}: one the site did not take goes back, and says so kindly", back[0] == "Off"
                          and back[1] == "That didn’t work. Try again in a moment.", str(back))
                    pg.unroute("**/push/prefs")
                    close_ctx(ctx, pg)
                    # Settings before it is on: Turn on, and the rows glide in.
                    db_write("delete from social_push_subscriptions where endpoint = ?", (ep_h,))
                    ctx, pg = browser_as(b, hal, screen, scheme, init=[stub], grant=True)
                    go(pg, "/social/you", wait=1200)
                    pg.evaluate("() => localStorage.removeItem('suite.push.sub')")
                    go(pg, "/social/you", wait=1200)
                    off = pg.evaluate("""() => { const f = document.querySelector('[data-push-panel]');
                      const t = f.querySelector('[data-push-when="off"]');
                      const shown = [...f.querySelectorAll('[data-push-when]')].filter(e => e.getClientRects().length
                        && getComputedStyle(e).display !== 'none').map(e => e.getAttribute('data-push-when'));
                      return [f.hidden, t.hidden, t.textContent.trim(), f.querySelector('[data-push-when="on"]').hidden, shown]; }""")
                    pg.click('[data-push-panel] [data-push-on]')
                    pg.wait_for_function("() => !document.querySelector('[data-push-when=\"on\"]').hidden", timeout=10000)
                    pg.wait_for_timeout(600)
                    after = pg.evaluate("""() => [...document.querySelectorAll('[data-push-panel] [data-push-when]')]
                      .filter(e => e.getClientRects().length && getComputedStyle(e).display !== 'none').map(e => e.getAttribute('data-push-when'))""")
                    check(f"{look}: before it is on, Settings offers Turn on alone, and turning on puts the rows in its"
                          " place", off == [False, False, "Turn on", True, ["off"]] and after == ["on"]
                          and row_of(ep_h) is not None, f"{off} {after}")
                    close_ctx(ctx, pg)
                    if screen == "phone" and scheme == "light":
                        ctx, pg = browser_as(b, hal, screen, scheme, init=[stub, DENIED])
                        go(pg, "/social/activity", wait=900)
                        asked = pg.evaluate("() => document.querySelector('[data-push-ask]').hidden")
                        go(pg, "/social/you", wait=900)
                        told = pg.evaluate("() => { const t = document.querySelector('[data-push-when=\"denied\"]');"
                                           " return [t.hidden, t.textContent]; }")
                        check("told no: Activity does not ask, and Settings says where to allow it",
                              asked is True and told[0] is False and "allow notifications for this site" in told[1], str(told))
                        close_ctx(ctx, pg)
                        ctx, pg = browser_as(b, hal, screen, scheme, init=[NO_PUSH], ua=IPHONE_UA)
                        go(pg, "/social/activity", wait=900)
                        asked = pg.evaluate("() => document.querySelector('[data-push-ask]').hidden")
                        go(pg, "/social/you", wait=900)
                        home = pg.evaluate("() => { const t = document.querySelector('[data-push-when=\"install\"]');"
                                           " return [t.hidden, t.querySelector('.panel-text').textContent,"
                                           " document.querySelector('#pushTitle').textContent]; }")
                        pg.click("[data-push-home]")
                        pg.wait_for_timeout(700)
                        steps = pg.evaluate("() => { const s = document.getElementById('homeSteps');"
                                            " return !!s && !s.hidden && s.querySelector('.make-title').textContent; }")
                        check("an iPhone in a browser tab (no push there): Activity does not ask; Settings says nudges"
                              " come to Blooby on the Home Screen, and Add to Home Screen opens the steps",
                              asked is True and home[0] is False and "on your Home Screen" in home[1]
                              and home[2] == "Notifications on this phone" and steps == "Add to Home Screen",
                              f"{home} {steps}")
                        close_ctx(ctx, pg)
                        ctx, pg = browser_as(b, hal, "desk", scheme, init=[NO_PUSH])
                        go(pg, "/social/you", wait=900)
                        none = pg.evaluate("() => document.querySelector('[data-push-panel]').hidden")
                        check("a browser that cannot be nudged shows nothing about it in Settings", none is True, "")
                        close_ctx(ctx, pg)
                        # Told no, the state is known at once: put there as the
                        # page is drawn, never gliding in under the reader.
                        ctx, pg = browser_as(b, hal, "desk", scheme, init=[stub, DENIED, DCL])
                        pg.goto(BASE + "/social/you")
                        pg.wait_for_function("() => window.__dcl !== undefined")
                        hs = pg.evaluate(FRAMES_JS, ["[data-push-panel]", 500])
                        check("a state known at once (told no) is there from the first frame the page is ready, at"
                              " its height, never gliding in", len(hs) > 3 and min(hs) > 40 and max(hs) - min(hs) < 1,
                              str(hs[:6]))
                        close_ctx(ctx, pg)
        except Exception as exc:  # noqa: BLE001
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "the service worker shows the nudge"):
        try:
            ivy = member(b, "ivy", "Ivy Dale")
            ep_i, keys = device("ivy-sw")
            stub = STUB % (json.dumps(ep_i), json.dumps(keys["p256dh"]), json.dumps(keys["auth"]))
            ctx, pg = browser_as(b, ivy, "desk", "light", init=[stub], grant=True)
            go(pg, "/social/activity", wait=900)
            pg.click("[data-push-on]")
            pg.wait_for_function("() => document.querySelector('[data-push-ask]').hidden", timeout=10000)
            cdp = ctx.new_cdp_session(pg)
            regs = []
            cdp.on("ServiceWorker.workerRegistrationUpdated", lambda e: regs.extend(e.get("registrations", [])))
            cdp.send("ServiceWorker.enable")
            for _ in range(40):
                if any(r.get("scopeURL") == BASE + "/social/" for r in regs):
                    break
                pg.wait_for_timeout(100)
            rid = next((r["registrationId"] for r in regs if r.get("scopeURL") == BASE + "/social/"), None)
            data = {"title": "Bea replied to your comment", "body": "“It is a lovely cat”",
                    "url": "/social/p/abc#c-def", "tag": "answer:/social/p/abc", "icon": "/social/static/blooby-icon-192.png",
                    "badge": 2}
            cdp.send("ServiceWorker.deliverPushMessage", {"origin": BASE, "registrationId": rid, "data": json.dumps(data)})
            shown = None
            for _ in range(40):
                shown = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration('/social/');
                  const n = r ? await r.getNotifications() : [];
                  return n.map(x => ({ title: x.title, body: x.body, tag: x.tag, url: x.data && x.data.url })); }""")
                if shown:
                    break
                pg.wait_for_timeout(100)
            check("a nudge handed to the service worker is shown at once: its title, its words, its tag, and the"
                  " link a tap opens, on the site", shown == [{"title": data["title"], "body": data["body"],
                                                                "tag": data["tag"], "url": BASE + "/social/p/abc#c-def"}],
                  json.dumps(shown))
            cdp.send("ServiceWorker.deliverPushMessage", {"origin": BASE, "registrationId": rid, "data": json.dumps(
                dict(data, body="The newest", url="https://elsewhere.example/phish"))})
            for _ in range(40):
                shown = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration('/social/');
                  const n = r ? await r.getNotifications() : [];
                  return n.map(x => ({ body: x.body, url: x.data && x.data.url })); }""")
                if shown and shown[0]["body"] == "The newest":
                    break
                pg.wait_for_timeout(100)
            check("the same tag takes the last one's place (one shown, the newest), and a link off the site opens"
                  " the site's Home instead", shown == [{"body": "The newest", "url": BASE + "/social/"}],
                  json.dumps(shown))
            go(pg, "/social/activity", wait=900)
            left = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration('/social/');
              return r ? (await r.getNotifications()).length : -1; }""")
            check("opening Activity puts away the nudges already shown: everything in them is seen", left == 0, str(left))
            close_ctx(ctx, pg)
        except Exception as exc:  # noqa: BLE001
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "no page errors, no console errors and no CSP violations"):
        try:
            for who in list(_people.values()):
                try:
                    ERRS.extend(f"csp: {v}" for v in who.pg.evaluate("() => window.__csp || []"))
                except Exception:
                    pass
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
            log = open(LOG).read()
            check("the server said nothing went wrong sending a nudge", "push: nudges were not sent" not in log
                  and "Traceback" not in log, log[-400:] if "Traceback" in log else "")
        except Exception as exc:  # noqa: BLE001
            stopped(9, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
