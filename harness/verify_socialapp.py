#!/usr/bin/env python3
"""Blooby on the Home Screen (the owner, Nov 15: "Let's do the home icon so I
can get full screen on my iPhone", then "All yes" to the Home Screen mock;
the map's step 7, docs/SOCIAL-SITE.md), through the demo's own server, with
Chromium's virtual authenticator for the site's people.

  1. THE MANIFEST: /social/manifest.webmanifest, application/manifest+json:
     Blooby (its name and short name), opening on Home (start_url and id),
     standalone, the site's dark ground; its scope the folder the site and
     Skribl's pages share, with Home, a post's page, the Pad, Flip and the
     Library inside it; each icon fetched, a PNG of the size it says, the
     site's own. shared_folder() itself, on mounts of other shapes.
  2. EVERY PAGE OF THE SITE'S LINKS IT, with the site's own touch icon and
     page icon, and both theme-color metas say SITE_GROUND; Skribl's pages
     keep Skribl's manifest and icons.
  3. THE ICON IS BLOOBY.APP'S (the owner's pick, Nov 13): the site's three
     files read pixel by pixel against the filed pictures (docs/brand/
     blooby-app-icon-*.png), the lilac at every corner, no star, his ink 0.82
     of the side; blooby.py names the fill and the files. The sign-in page,
     joining, recovery, two kind pages (nobody there, a post not there) and
     Activity's empty state show it.
  4. WHO SEES WHICH ROW: an iPhone in a tab, Add to Home Screen in the ☰
     right under Settings (Sign in, signed out); an iPad that says it is a
     Mac, the same; opened from the Home Screen (navigator.standalone, or the
     standalone display), Reload in its place; a desk, neither; Android,
     neither until Chrome offers its install, then the row, which asks Chrome
     once, keeps Chrome's own bar away, and goes once installed.
  5. THE STEPS: the row lets the ☰ go down and the steps rise, gliding (read
     on every frame; under Reduce Motion, still); the words (the title,
     Blooby, "Opens full screen, like an app", iOS 26's three steps, "More"
     for a screen reader, the sign-in note, Got it) and the site's icon;
     focus on Got it, back on the ☰ after Got it, Esc or the scrim; Reload
     reloads the page.
  6. CONTRAST AND SIZES, light and dark, read off the paint: the ☰ with the
     row, and every word on the steps, at 4.5:1 and more; the row as tall as
     Settings, the steps' rows 56px, Got it 44px and more, every target 44px.
  7. THE PAD'S AND FLIP'S STEPS SAY iOS 26's TOO (their one shared partial):
     ⋯ (a screen reader's "More") then Share; Open as Web App; the banner's
     line the same.
  8. THE SPLASH (the owner, Nov 15: "make a splash screen load first and show
     blooby ... Fall the same way and compress then pop back the exact same
     way", on the dark ground "with no stars"): its drawing, the site's hello
     with the word in the icon's lilac; never in a browser tab; in the app,
     over the page from the first paint, the night ground with no stars and
     the bar the same; the first launch writes the word then the blush falls,
     a later one only the blush; once a launch; a tap lets it go at once;
     still under Reduce Motion; never held for a drawing that does not come;
     the page's own drawing waits for it; it fades out on several frames, and
     the bar comes back; the word and the period read off the paint.
  9. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALAPP_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "Blooby on the Home Screen".
"""
import ast
import io
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
from pathlib import Path

from assertions import make_check
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT))
PART = os.environ.get("SOCIALAPP_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALAPP {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on says so as a red row, and the run goes on."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the Home Screen app works.")
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
TMP = tempfile.mkdtemp(prefix="socialapp-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialapp-" + secrets.token_hex(8),
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

# THE DEVICES. A phone is a touch phone (WORKING-AGREEMENTS), 402x874 as the
# owner's; an iPhone says so in its user agent, as Safari's does.
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/18.0 Mobile/15E148 Safari/604.1")
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.0 Safari/605.1.15")
ANDROID_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0.0.0 Mobile Safari/537.36")
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
# Opened from the Home Screen: iOS says navigator.standalone; elsewhere the
# standalone display mode answers matchMedia.
STANDALONE = "Object.defineProperty(navigator, 'standalone', { value: true, configurable: true });"
DISPLAY_STANDALONE = """(() => { const real = window.matchMedia.bind(window);
  window.matchMedia = q => /display-mode:\\s*standalone/.test(q) ? { matches: true, media: q, addEventListener() {}, removeEventListener() {} } : real(q); })();"""
# The splash has been, this launch (splash-boot.js): the rows about the ☰ in
# the app are not about the splash, which section 8 reads.
SPLASHED = "try { sessionStorage.setItem('blooby.splash.launch', '1'); } catch (e) {}"
# iPadOS says it is a Mac; a Mac with a touch screen is an iPad.
IPAD = ("Object.defineProperty(navigator, 'platform', { value: 'MacIntel', configurable: true });"
        "Object.defineProperty(navigator, 'maxTouchPoints', { value: 5, configurable: true });")
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{140 + _addr[0] // 250}.{_addr[0] % 250}.9"


def get(path):
    """(status, headers, body bytes) of a GET with no cookies."""
    req = urllib.request.Request(BASE + path, headers={"X-Forwarded-For": address()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def cli(*args):
    out = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "social", *args, "--base", BASE],
                         cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    return out.stdout.strip().splitlines()[-1] if out.returncode == 0 else None


def db(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


class Person:
    """One browser with its own passkey, from an address of its own."""

    def __init__(self, b):
        self.xff = address()
        self.ctx = b.new_context(extra_http_headers={"X-Forwarded-For": self.xff}, **PHONE)
        self.ctx.add_init_script(WATCH)
        self.pg = self.ctx.new_page()
        self.pg.on("pageerror", lambda e: ERRS.append(f"member pageerror: {e} @ {self.pg.url}"))
        cdp = self.ctx.new_cdp_session(self.pg)
        cdp.send("WebAuthn.enable")
        cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
            "protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True,
            "isUserVerified": True, "automaticPresenceSimulation": True}})
        self.handle = None


_people = {}


def member(b, handle, name):
    """Somebody who joined through an invite (the first through the first invite code), signed in."""
    if handle in _people:
        return _people[handle]
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


def browser_as(b, who=None, screen="phone", scheme="light", ua=None, init=(), reduced=False):
    """A fresh browser as WHO (their cookies) or nobody, on a phone or a desk."""
    kw = dict(PHONE if screen == "phone" else DESK)
    if ua:
        kw["user_agent"] = ua
    if reduced:
        kw["reduced_motion"] = "reduce"
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()}, **kw)
    ctx.add_init_script(WATCH)
    for s in init:
        ctx.add_init_script(s)
    if who:
        ctx.add_cookies([{k: v for k, v in c.items() if k in ("name", "value", "domain", "path", "httpOnly",
                                                             "sameSite", "secure", "expires")}
                         for c in who.ctx.cookies(BASE)])
    pg = ctx.new_page()
    tag = f"{screen}/{scheme} as {who.handle if who else 'nobody'}"
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


def go(pg, path, wait=400):
    r = pg.goto(BASE + path)
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet", timeout=15000)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def open_menu(pg):
    pg.click("[data-site-menu]")
    pg.wait_for_function("() => document.getElementById('siteMenu').classList.contains('is-open')", timeout=5000)
    pg.wait_for_timeout(450)


# What the ☰ shows: its rows in order, which of the two are showing, and each painted.
ROWS = r"""() => { const m = document.getElementById('siteMenu'), add = document.getElementById('siteAddHome'),
    rel = document.getElementById('siteReload');
  const rows = [...m.querySelectorAll('.post-acts > .post-act, .post-acts > form > .post-act')].filter(e => e.getClientRects().length);
  const painted = e => { if (!e || !e.getClientRects().length) return false; const r = e.getBoundingClientRect();
    const c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!c && (c === e || e.contains(c)); };
  return { rows: rows.map(e => e.textContent.trim()), add: !!add && !add.hidden, reload: !!rel && !rel.hidden,
           addPainted: painted(add), reloadPainted: painted(rel), open: m.classList.contains('is-open') }; }"""

# THE CENSUS OF WORDS AND TARGETS (verify_sociallikes' READ, as verify_socialreposts reads it).
READ = r"""(sel) => {
  const rgba = s => { const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
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
  const out = { read: 0, low: [], small: [], lowest: 99, each: {} };
  const root = document.querySelector(sel);
  if (!root) return null;
  root.querySelectorAll('*').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden]')) return;
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > innerHeight) return;
    const c = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;
    let op = 1; for (let n = e; n && n !== document.documentElement; n = n.parentElement) op *= +getComputedStyle(n).opacity;
    const fg = rgba(getComputedStyle(e).color); fg[3] *= op;
    const g = ground(e), col = over(fg, g), k = ratio(col, g);
    out.read++;
    out.each[e.textContent.trim().slice(0, 28)] = Math.round(k * 100) / 100;
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + e.textContent.trim().slice(0, 30) + '" ' + k.toFixed(2));
  });
  root.querySelectorAll('a[href], button').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden]') || e.matches('[data-make-close]:not(button)')) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  return out; }"""


def site_ground():
    """social.SITE_GROUND, read from the source (the one place the two grounds live)."""
    src = (ROOT / "social" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r"^SITE_GROUND = (\{[^}]*\})", src, re.M)
    return ast.literal_eval(m.group(1)) if m else None


def ink_box(im, cut=90):
    """His dark ink's box in a picture (his outline is the only ink that dark)."""
    return im.convert("L").point(lambda v: 255 if v < cut else 0).getbbox()


def png_of(url_path):
    st, hdr, raw = get(url_path)
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        im = None
    return st, (hdr.get("Content-Type") if hdr else None), im


with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the manifest: Blooby, opening on Home, standalone, its scope over the site and Skribl's pages, its icons"):
        try:
            st, hdr, raw = get("/social/manifest.webmanifest")
            ctype = (hdr.get("Content-Type") or "") if hdr else ""
            man = json.loads(raw) if st == 200 else {}
            check("/social/manifest.webmanifest answers 200 as application/manifest+json",
                  st == 200 and ctype.startswith("application/manifest+json"), f"{st} {ctype}")
            check("its name and short name are Blooby, the name under the icon (the owner's pick: blooby.app's name)",
                  man.get("name") == "Blooby" and man.get("short_name") == "Blooby", json.dumps(man)[:300])
            check("it opens on Home, the site's own (start_url and id are Home's address), standalone: full screen, no browser bar",
                  man.get("start_url") == "/social/" and man.get("id") == "/social/" and man.get("display") == "standalone",
                  f"{man.get('start_url')} {man.get('id')} {man.get('display')}")
            g = site_ground() or {}
            check("its colours are the site's dark ground, social.SITE_GROUND (the Home Screen's splash and bar)",
                  bool(g) and man.get("theme_color") == g.get("dark") and man.get("background_color") == g.get("dark"),
                  f"{man.get('theme_color')} {man.get('background_color')} {g}")
            post = None
            pages = {"Home": "/social/", "a post's page": "/social/p/abcdefghijk", "the Pad": "/skribl-pad",
                     "Flip": "/flip", "the Library": "/library", "the Gallery": "/social/explore"}
            scope = man.get("scope") or ""
            inside = {k: v.startswith(scope) for k, v in pages.items()}
            check("its scope is the folder the site and Skribl's pages share (/ here): Home, a post, the Gallery, the Pad,"
                  " Flip and the Library open inside the app, full screen, not in a browser's sheet",
                  scope == "/" and all(inside.values()), f"scope {scope!r}: {inside}")
            icons, sizes = [], {}
            for ic in man.get("icons") or []:
                s2, ct2, im = png_of(ic.get("src", ""))
                want = ic.get("sizes", "")
                icons.append((ic.get("src"), s2, ct2, im.size if im else None, want))
                sizes[want] = bool(im) and s2 == 200 and (ct2 or "").startswith("image/png") and f"{im.width}x{im.height}" == want
            check("each icon it names is fetched: a PNG of the size it says, 192 and 512, the site's own files (blooby-icon-*)",
                  set(sizes) == {"192x192", "512x512"} and all(sizes.values())
                  and all("/social/static/blooby-icon-" in (i[0] or "") for i in icons), json.dumps(icons))
            from social import shared_folder
            cases = {("/social/", "/skribl-pad"): "/", ("/app/social/", "/app/flip", "/app/library"): "/app/",
                     ("/social/", "/social/explore"): "/social/", ("/social/?next=/a/b", "/skribl-pad"): "/",
                     ("/a/b/c/", "/a/b/d"): "/a/b/", ("/skribl-pad",): "/", ("/app/flip", "/app/flip"): "/app/"}
            got = {" ".join(k): shared_folder(*k) for k in cases}
            check("shared_folder: the deepest folder its addresses share, on other mounts too (a page is not a folder;"
                  " a query is not a path)", all(got[" ".join(k)] == v for k, v in cases.items()), json.dumps(got))
        except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is a red row, never a stop
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "every page of the site's links it, with the site's own icons; Skribl's pages keep Skribl's"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            g = site_ground() or {}
            ctx, pg = browser_as(b, mira)
            heads = {}
            for name, path in (("Home", "/social/"), ("the Gallery", "/social/explore"), ("a profile", "/social/@mira"),
                               ("Activity", "/social/activity"), ("Settings", "/social/you"), ("nobody", "/social/@nosuch_person")):
                pg.goto(BASE + path)
                heads[name] = pg.evaluate("""() => ({
                  manifest: [...document.querySelectorAll('link[rel=manifest]')].map(l => l.getAttribute('href')),
                  touch: [...document.querySelectorAll('link[rel=apple-touch-icon]')].map(l => l.getAttribute('href')),
                  icon: [...document.querySelectorAll('link[rel=icon]')].map(l => l.getAttribute('href')) })""")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b)
            for name, path in (("signed out: Home", "/social/"), ("sign in", "/social/signin")):
                pg.goto(BASE + path)
                heads[name] = pg.evaluate("""() => ({
                  manifest: [...document.querySelectorAll('link[rel=manifest]')].map(l => l.getAttribute('href')),
                  touch: [...document.querySelectorAll('link[rel=apple-touch-icon]')].map(l => l.getAttribute('href')),
                  icon: [...document.querySelectorAll('link[rel=icon]')].map(l => l.getAttribute('href')) })""")
            close_ctx(ctx, pg)
            ok = {k: v["manifest"] == ["/social/manifest.webmanifest"]
                  and len(v["touch"]) == 1 and v["touch"][0].startswith("/social/static/blooby-icon-180.png")
                  and len(v["icon"]) == 1 and v["icon"][0].startswith("/social/static/blooby-icon-192.png")
                  for k, v in heads.items()}
            check("every page of the site's, signed in and out, links the site's manifest once, its touch icon blooby-icon-180"
                  " and its page icon blooby-icon-192 (the site's own files, not Skribl's)", all(ok.values()),
                  json.dumps({k: v for k, v in heads.items() if not ok[k]} or ok)[:600])
            st, _, raw = get("/social/signin")
            metas = re.findall(r'<meta name="theme-color"[^>]*>', raw.decode("utf-8", "replace"))
            want = [f'<meta name="theme-color" content="{g.get("light")}" media="(prefers-color-scheme: light)" data-light="{g.get("light")}" data-dark="{g.get("dark")}">',
                    f'<meta name="theme-color" content="{g.get("dark")}" media="(prefers-color-scheme: dark)" data-light="{g.get("light")}" data-dark="{g.get("dark")}">']
            check("both theme-color metas, as the page is sent, say social.SITE_GROUND (#f6f8fa, #0f1218): the browser's bar"
                  " in the page's ground, from the one place the manifest's colour comes from too",
                  metas == want and g == {"light": "#f6f8fa", "dark": "#0f1218"}, json.dumps(metas))
            sk = {}
            for name, path in (("the Pad", "/skribl-pad"), ("Flip", "/flip")):
                st, _, raw = get(path)
                t = raw.decode("utf-8", "replace")
                sk[name] = {"manifest": re.findall(r'<link rel="manifest" href="([^"]+)"', t),
                            "touch": re.findall(r'<link rel="apple-touch-icon"[^>]*href="([^"]+)"', t)}
            check("Skribl's pages keep Skribl's own: the Pad and Flip link /manifest.webmanifest (Skribl, opening the Pad)"
                  " and Skribl's apple-touch-icon, not the site's",
                  all(v["manifest"] == ["/manifest.webmanifest"] and len(v["touch"]) == 1
                      and "/static/skribl/apple-touch-icon.png" in v["touch"][0] for v in sk.values()), json.dumps(sk))
            st, _, raw = get("/manifest.webmanifest")
            sman = json.loads(raw) if st == 200 else {}
            check("and Skribl's manifest is Skribl's: its name Skribl, opening the Pad, its icons Skribl's",
                  sman.get("name") == "Skribl" and sman.get("start_url") == "/skribl-pad"
                  and all("/static/skribl/icon-" in i.get("src", "") for i in sman.get("icons", [])), json.dumps(sman)[:300])
        except Exception as exc:  # noqa: BLE001
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "the icon is blooby.app's: the owner's pick, read pixel by pixel; the site's pages show it"):
        try:
            import importlib
            sys.path.insert(0, str(ROOT / "harness" / "tools"))
            blooby = importlib.import_module("blooby")
            names = getattr(blooby, "SITE_ICON_SIZES", {})
            check("blooby.py draws it (site-icon): his fill 0.82 of the side, the three files the site serves",
                  getattr(blooby, "SITE_ICON_FILL", None) == 0.82
                  and names == {"blooby-icon-512.png": 512, "blooby-icon-192.png": 192, "blooby-icon-180.png": 180},
                  f"{getattr(blooby, 'SITE_ICON_FILL', None)} {names}")
            edge = tuple(int(blooby.ICON_EDGE[i:i + 2], 16) for i in (1, 3, 5))
            per = {}
            for name, px in sorted(names.items(), key=lambda kv: -kv[1]):
                mine = Image.open(ROOT / "social" / "static" / name).convert("RGB")
                filed = Image.open(ROOT / "docs" / "brand" / f"blooby-app-icon-{px}.png").convert("RGB")
                d = ImageChops.difference(mine, filed).convert("L").histogram()
                mean = sum(i * c for i, c in enumerate(d)) / max(1, sum(d))
                bm, bf = ink_box(mine), ink_box(filed)
                corners = [mine.getpixel(p) for p in ((1, 1), (px - 2, 1), (1, px - 2), (px - 2, px - 2))]
                # Where today's star is white and this icon is the lilac: beside him at mid-height, and over his
                # head toward each top corner (the star's upper points).
                probes = [mine.getpixel((round(px * x), round(px * y))) for x, y in ((0.06, 0.5), (0.94, 0.5), (0.24, 0.1), (0.5, 0.03))]
                per[px] = {"size": mine.size, "mean": round(mean, 2), "box": bm, "filed": bf,
                           "corners": all(max(abs(c[i] - edge[i]) for i in range(3)) <= 4 for c in corners),
                           "nostar": all(min(p) < 235 and p[2] > p[0] for p in probes),
                           "fill": round((bm[3] - bm[1]) / px, 3) if bm else None}
            check("the site's three files are the owner's pick: each read against the filed picture of its size"
                  " (docs/brand/blooby-app-icon-*), within 1 of 255 on average, his ink's box within 2px",
                  len(per) == 3 and all(v["size"] == (px, px) and v["mean"] <= 1.0 and v["box"] and v["filed"]
                                        and max(abs(a - c) for a, c in zip(v["box"], v["filed"])) <= 2 for px, v in per.items()),
                  json.dumps(per))
            check("the lilac at every corner (blooby.py's ICON_EDGE), no star (lilac, not white, beside him and over his"
                  " head), and his ink 0.82 of the side (0.80 to 0.84)",
                  all(v["corners"] and v["nostar"] and v["fill"] and 0.80 <= v["fill"] <= 0.84 for v in per.values()),
                  json.dumps({k: (v["corners"], v["nostar"], v["fill"]) for k, v in per.items()}))
            # The site's pages show it, in small, where they show Blooby: the sign-in page, joining (a link with no
            # code still shows its card), recovery, a kind page (nobody there), and Activity's empty state.
            fresh = member(b, "pip_new", "Pip New")
            seen = {}
            for who, name, path in ((None, "sign in", "/social/signin"), (None, "joining", "/social/join"),
                                    (None, "recovery", "/social/recover"), (None, "nobody there", "/social/@nosuch_person"),
                                    (None, "a post not there", "/social/p/abcdefghijk"),
                                    (fresh, "Activity, nothing yet", "/social/activity")):
                ctx, pg = browser_as(b, who)
                pg.goto(BASE + path)
                pg.wait_for_timeout(700)
                seen[name] = pg.evaluate("""() => { const i = document.querySelector('img.si-icon'); if (!i) return null;
                  const r = i.getBoundingClientRect(), c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  return { src: i.getAttribute('src'), w: Math.round(r.width), nat: i.naturalWidth, painted: c === i }; }""")
                close_ctx(ctx, pg)
            check("where the site shows Blooby in small (sign in, joining, recovery, two kind pages, Activity's nothing yet)"
                  " it is this icon, 64px, loaded and painted (each kind page imports its card with the page's context)",
                  all(v and v["src"].startswith("/social/static/blooby-icon-180.png") and v["w"] == 64 and v["nat"] == 180
                      and v["painted"] for v in seen.values()), json.dumps(seen))
        except Exception as exc:  # noqa: BLE001
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "who sees which row: an iPhone in a tab, an iPad, the Home Screen app, a desk, Android"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            got = {}
            for name, who, ua, init in (("iPhone, signed in", mira, IPHONE_UA, ()), ("iPhone, signed out", None, IPHONE_UA, ()),
                                        ("iPad (says Mac)", mira, MAC_UA, (IPAD,)),
                                        ("Home Screen app (iOS)", mira, IPHONE_UA, (STANDALONE, SPLASHED)),
                                        ("installed (display standalone)", mira, ANDROID_UA, (DISPLAY_STANDALONE, SPLASHED)),
                                        ("Android, no offer", mira, ANDROID_UA, ())):
                ctx, pg = browser_as(b, who, ua=ua, init=init)
                go(pg, "/social/")
                open_menu(pg)
                got[name] = pg.evaluate(ROWS)
                close_ctx(ctx, pg)
            ip, io_, ipad, app, inst, andr = (got[k] for k in ("iPhone, signed in", "iPhone, signed out", "iPad (says Mac)",
                                                                "Home Screen app (iOS)", "installed (display standalone)",
                                                                "Android, no offer"))
            check("an iPhone in a browser tab: Add to Home Screen in the ☰, the second row, right under Settings; no Reload",
                  ip["add"] and ip["addPainted"] and not ip["reload"] and ip["rows"][:2] == ["Settings", "Add to Home Screen"],
                  json.dumps(ip))
            check("signed out, the same row right under Sign in", io_["add"] and io_["addPainted"]
                  and io_["rows"][:2] == ["Sign in", "Add to Home Screen"], json.dumps(io_))
            check("an iPad, which says it is a Mac with a touch screen: the same row", ipad["add"] and ipad["addPainted"],
                  json.dumps(ipad))
            check("opened from the Home Screen (navigator.standalone): Reload in its place, the second row; no Add to Home Screen",
                  app["reload"] and app["reloadPainted"] and not app["add"] and app["rows"][:2] == ["Settings", "Reload"],
                  json.dumps(app))
            check("installed anywhere else (the standalone display mode): Reload, not Add to Home Screen",
                  inst["reload"] and not inst["add"], json.dumps(inst))
            check("Android before Chrome offers its install: neither row", not andr["add"] and not andr["reload"], json.dumps(andr))
            # A desk: the ☰ is a phone's; neither row shows (and the ☰ is not there to open).
            ctx, pg = browser_as(b, mira, screen="desk")
            go(pg, "/social/")
            desk = pg.evaluate("""() => ({ add: !document.getElementById('siteAddHome').hidden, reload: !document.getElementById('siteReload').hidden,
              menu: !!document.querySelector('[data-site-menu]') && document.querySelector('[data-site-menu]').getClientRects().length > 0 })""")
            close_ctx(ctx, pg)
            check("a desk: neither row (and no ☰ to open)", not desk["add"] and not desk["reload"] and not desk["menu"], json.dumps(desk))
            # Android, once Chrome offers its own install: the row asks Chrome, once, and Chrome's own bar is kept away.
            ctx, pg = browser_as(b, mira, ua=ANDROID_UA)
            go(pg, "/social/")
            pg.evaluate("""() => { const e = new Event('beforeinstallprompt', { cancelable: true }); window.__asked = 0;
              e.prompt = () => { window.__asked++; return Promise.resolve(); }; window.dispatchEvent(e); window.__kept = e.defaultPrevented; }""")
            open_menu(pg)
            offered = pg.evaluate(ROWS)
            pg.click("#siteAddHome")
            pg.wait_for_timeout(500)
            after = {"asked": pg.evaluate("window.__asked"), "kept": pg.evaluate("window.__kept"),
                     "row": not pg.evaluate("document.getElementById('siteAddHome').hidden"),
                     "menu": pg.evaluate("document.getElementById('siteMenu').classList.contains('is-open')")}
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, mira, ua=ANDROID_UA)
            go(pg, "/social/")
            pg.evaluate("""() => { const e = new Event('beforeinstallprompt', { cancelable: true }); e.prompt = () => Promise.resolve();
              window.dispatchEvent(e); window.dispatchEvent(new Event('appinstalled')); }""")
            gone = pg.evaluate("document.getElementById('siteAddHome').hidden")
            close_ctx(ctx, pg)
            check("Android once Chrome offers its install: the row; a tap asks Chrome once (its own bar kept away), the ☰"
                  " goes down and the row goes; installed some other way, the row goes too",
                  offered["add"] and offered["addPainted"] and after == {"asked": 1, "kept": True, "row": False, "menu": False}
                  and gone is True, json.dumps({"offered": offered, "after": after, "gone": gone}))
        except Exception as exc:  # noqa: BLE001
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "the steps: rising as the ☰ goes, their words and icon, focus, and Reload"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            glides = {}
            for reduced in (False, True):
                ctx, pg = browser_as(b, mira, ua=IPHONE_UA, reduced=reduced)
                go(pg, "/social/")
                open_menu(pg)
                pg.evaluate("""() => { window.__sf = []; const s = document.querySelector('#homeSteps .make-sheet'), t0 = performance.now();
                  const step = () => { const w = document.getElementById('homeSteps'), r = s.getBoundingClientRect();
                    window.__sf.push({ t: performance.now() - t0, top: r.top, shown: !w.hidden,
                      menu: document.getElementById('siteMenu').classList.contains('is-open') });
                    if (performance.now() - t0 < 1000) requestAnimationFrame(step); }; requestAnimationFrame(step); }""")
                pg.click("#siteAddHome")
                pg.wait_for_timeout(1100)
                fr = pg.evaluate("() => window.__sf")
                tops = [f["top"] for f in fr if f["shown"]]
                glides[reduced] = {"n": len(tops), "moved": round((tops[0] - tops[-1]) if tops else 0, 1),
                                   "jump": round(max((a - c for a, c in zip(tops, tops[1:])), default=0), 1),
                                   "up": all(c <= a + 0.5 for a, c in zip(tops, tops[1:])),
                                   "menuGone": not fr[-1]["menu"] if fr else False}
                if not reduced:
                    state = pg.evaluate("""() => { const w = document.getElementById('homeSteps'), s = w.querySelector('.make-sheet');
                      const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : null;
                      const seen = e => { const c = e.cloneNode(true); c.querySelectorAll('.home-steps-say').forEach(x => x.remove());
                                          return t(c); };
                      const img = s.querySelector('.home-steps-app img');
                      const list = s.querySelector('ol');
                      return { open: w.classList.contains('is-open'), title: t(s.querySelector('#homeStepsTitle')),
                               name: t(s.querySelector('.home-steps-app b')), line: t(s.querySelector('.home-steps-app span')),
                               steps: [...list.querySelectorAll('li > span')].map(seen), role: list.getAttribute('role'),
                               said: t(s.querySelector('.home-steps-say')),
                               dots: (s.querySelector('.home-steps-say') || {}).previousElementSibling ?
                                     s.querySelector('.home-steps-say').previousElementSibling.getAttribute('aria-hidden') : null,
                               note: t(s.querySelector('.home-steps-note')), act: t(s.querySelector('.btn-primary')),
                               focus: t(document.activeElement), labelled: s.getAttribute('aria-labelledby'),
                               icon: img ? { src: img.getAttribute('src'), nat: img.naturalWidth, w: Math.round(img.getBoundingClientRect().width) } : null }; }""")
                    check("the row lets the ☰ go down and the steps rise in its place (the ☰ closed, the steps open)",
                          state["open"] and glides[False]["menuGone"], json.dumps(state)[:300])
                    check("its words: \"Add to Home Screen\", Blooby and \"Opens full screen, like an app\", iOS 26's three"
                          " steps, the sign-in note, Got it",
                          state["title"] == "Add to Home Screen" and state["name"] == "Blooby"
                          and state["line"] == "Opens full screen, like an app"
                          and state["steps"] == ["Tap ⋯ in Safari’s bar, then Share", "Scroll down and tap Add to Home Screen",
                                                 "Keep Open as Web App on, and tap Add"]
                          and state["note"] == "Open it from your Home Screen. It may ask you to sign in once there, with your passkey."
                          and state["act"] == "Got it", json.dumps(state))
                    check("a screen reader hears a list of three, \"More\" for Safari's ⋯ (the dots hidden from it), and the"
                          " sheet's name from its title",
                          state["role"] == "list" and state["said"] == "More" and state["dots"] == "true"
                          and state["labelled"] == "homeStepsTitle", json.dumps(state))
                    check("the icon in it is the site's own, the one the Home Screen will show (blooby-icon-180, loaded, 60px)",
                          bool(state["icon"]) and state["icon"]["src"].startswith("/social/static/blooby-icon-180.png")
                          and state["icon"]["nat"] == 180 and state["icon"]["w"] == 60, json.dumps(state["icon"]))
                    check("focus is on Got it as the steps open", state["focus"] == "Got it", state["focus"])
                    # Got it, Esc and the scrim each close the steps, and focus comes back to the ☰.
                    closes = {}
                    for how in ("Got it", "Esc", "scrim"):
                        if how != "Got it":
                            open_menu(pg)
                            pg.click("#siteAddHome")
                            pg.wait_for_timeout(700)
                        if how == "Got it":
                            pg.click("#homeSteps .btn-primary")
                        elif how == "Esc":
                            pg.keyboard.press("Escape")
                        else:
                            pg.mouse.click(200, 40)
                        pg.wait_for_timeout(700)
                        closes[how] = pg.evaluate("""() => ({ hidden: document.getElementById('homeSteps').hidden,
                          focus: document.activeElement && document.activeElement.matches('[data-site-menu]') })""")
                    check("Got it, Esc and a tap outside each close the steps, and focus comes back to the ☰",
                          all(v == {"hidden": True, "focus": True} for v in closes.values()), json.dumps(closes))
                close_ctx(ctx, pg)
            g0, g1 = glides[False], glides[True]
            check("the steps rise gliding, read on every frame: from below to where they rest, only ever up, no frame more than"
                  " a fifth of the way at once; under Reduce Motion they do not move",
                  g0["n"] >= 8 and g0["up"] and g0["moved"] > 100 and g0["jump"] <= g0["moved"] / 5
                  and g1["n"] >= 2 and abs(g1["moved"]) < 1, json.dumps(glides))
            # Reload, from the Home Screen: the page comes again, from the server.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE, SPLASHED))
            go(pg, "/social/")
            pg.evaluate("() => { window.__before = 1; }")
            open_menu(pg)
            try:
                with pg.expect_navigation(timeout=8000):
                    pg.click("#siteReload")
                pg.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
            except PWTimeout:
                pass    # no page came again: the row below says so
            again = pg.evaluate("""() => ({ before: window.__before === 1,
              type: (performance.getEntriesByType('navigation')[0] || {}).type, at: location.pathname })""")
            close_ctx(ctx, pg)
            check("from the Home Screen, Reload loads the page again (a reload, the same page)",
                  again == {"before": False, "type": "reload", "at": "/social/"}, json.dumps(again))
        except Exception as exc:  # noqa: BLE001
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "contrast and sizes, light and dark, read off the paint"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            res = {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, mira, scheme=scheme, ua=IPHONE_UA)
                go(pg, "/social/")
                open_menu(pg)
                menu = pg.evaluate(READ, "#siteMenu .make-sheet")
                hs = pg.evaluate("""() => { const r = e => Math.round(e.getBoundingClientRect().height * 10) / 10;
                  const rows = [...document.querySelectorAll('#siteMenu .post-acts > .post-act')].filter(e => e.getClientRects().length);
                  return { add: r(document.getElementById('siteAddHome')), settings: r(rows[0]) }; }""")
                pg.click("#siteAddHome")
                pg.wait_for_timeout(900)
                steps = pg.evaluate(READ, "#homeSteps .make-sheet")
                sz = pg.evaluate("""() => ({ rows: [...document.querySelectorAll('#homeSteps li')].map(e => Math.round(e.getBoundingClientRect().height)),
                  act: Math.round(document.querySelector('#homeSteps .btn-primary').getBoundingClientRect().height) })""")
                res[scheme] = {"menu": menu, "steps": steps, "heights": hs, "sizes": sz}
                close_ctx(ctx, pg)
            show = {s: {"menu lowest": v["menu"]["lowest"], "steps": v["steps"]["each"], "heights": v["heights"], "sizes": v["sizes"]}
                    for s, v in res.items()}
            print("      measured:", json.dumps(show))
            check("the ☰ with its new row: every word at 4.5:1 and more off the paint, light and dark, every target 44px,"
                  " the row as tall as Settings",
                  all(v["menu"]["read"] >= 5 and not v["menu"]["low"] and not v["menu"]["small"]
                      and v["heights"]["add"] == v["heights"]["settings"] >= 44 for v in res.values()), json.dumps(show)[:600])
            check("the steps: every word at 4.5:1 and more, light and dark (the numbers, the note and Got it too), every step's"
                  " row 56px and more, Got it 44px and more",
                  all(v["steps"]["read"] >= 8 and not v["steps"]["low"] and not v["steps"]["small"]
                      and len(v["sizes"]["rows"]) == 3 and min(v["sizes"]["rows"]) >= 56 and v["sizes"]["act"] >= 44
                      for v in res.values()),
                  json.dumps({s: (v["steps"]["low"], v["steps"]["small"], v["sizes"]) for s, v in res.items()}))
        except Exception as exc:  # noqa: BLE001
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "the Pad's and Flip's own steps say iOS 26's too"):
        try:
            said = {}
            for name, path in (("the Pad", "/skribl-pad"), ("Flip", "/flip")):
                ctx, pg = browser_as(b, None, ua=IPHONE_UA)
                pg.goto(BASE + path)
                pg.wait_for_timeout(800)
                said[name] = pg.evaluate("""() => { const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : null;
                  const seen = e => { const c = e.cloneNode(true); c.querySelectorAll('.vis-hidden').forEach(x => x.remove()); return t(c); };
                  const li = [...document.querySelectorAll('#homeScreenSteps .hs-list li')];
                  const sub = document.querySelector('#homeScreenBanner .hs-banner-sub');
                  return { steps: li.map(seen), more: li[0] ? t(li[0].querySelector('.vis-hidden')) : null,
                           dots: li[0] && li[0].querySelector('[aria-hidden=true]') ? t(li[0].querySelector('[aria-hidden=true]')) : null,
                           banner: sub ? seen(sub) : null }; }""")
                close_ctx(ctx, pg)
            check("the Pad's and Flip's steps say iOS 26's: ⋯ in Safari's bar, then Share; Scroll down and tap Add to Home"
                  " Screen; Keep Open as Web App on, and tap Add (\"More\" for a screen reader); the Pad's banner the same"
                  " (Flip has none)",
                  all(v["steps"] == ["Tap ⋯ in Safari’s bar, then Share", "Scroll down and tap Add to Home Screen",
                                     "Keep Open as Web App on, and tap Add"]
                      and v["more"] == "More" and v["dots"] == "⋯" for v in said.values())
                  and said["the Pad"]["banner"] == "Tap ⋯, then Share, then Add to Home Screen", json.dumps(said))
        except Exception as exc:  # noqa: BLE001
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "the splash: the app's first paint, the word and its blush, once a launch, kind"):
        try:
            # ITS DRAWING: the site's hello, the word in the icon's lilac.
            hello = json.load(open(ROOT / "social" / "static" / "brand" / "blooby-hello.json"))
            spl = json.load(open(ROOT / "social" / "static" / "brand" / "blooby-splash.json"))
            sys.path.insert(0, str(ROOT / "harness" / "tools"))
            import importlib
            tile = importlib.import_module("blooby").ICON_TILE.lower()
            css = (ROOT / "social" / "static" / "social.css").read_text(encoding="utf-8")
            blush = re.search(r"--blooby-blush:\s*(#[0-9a-fA-F]{6})", css).group(1).lower()
            inks = [sorted({q["color"].lower() for q in f["strokes"]}) for f in spl["frames"]]
            box = lambda f: [round(v) for v in (min(q["x"] for q in f["strokes"]), min(q["y"] for q in f["strokes"]),
                                                max(q["x"] for q in f["strokes"]), max(q["y"] for q in f["strokes"]))]
            same = len(spl["frames"]) == len(hello["frames"]) and all(
                max(abs(a - c) for a, c in zip(box(f), box(g))) <= 2 for f, g in zip(spl["frames"], hello["frames"]))
            check("its drawing is the site's hello, page for page (the word, then the period's fall, squash and pop, as "
                  "skribl's i-dot), the word in the icon's lilac (blooby.py's ICON_TILE) and the period in Blooby's blush",
                  same and inks[0] == [tile] and all(k == [blush] for k in inks[1:])
                  and spl.get("under") == {"page": 0, "from": 1, "to": len(spl["frames"]) - 1},
                  f"{len(spl['frames'])} pages, the same as the hello's: {same}; inks {inks[:3]}")

            # NEVER IN A BROWSER TAB: Home and a post's page, signed in.
            mira = member(b, "mira", "Mira Lopez")
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA)
            tab = {}
            for path in ("/social/", "/social/explore"):
                pg.goto(BASE + path)
                pg.wait_for_function("() => document.readyState === 'complete'")
                tab[path] = pg.evaluate("""() => ({ cls: document.documentElement.className,
                  shown: getComputedStyle(document.getElementById('bloobySplash')).display })""")
            close_ctx(ctx, pg)
            check("never in a browser tab: no splash on Home or the Gallery (only the Home Screen app opens with one)",
                  all(v == {"cls": "", "shown": "none"} for v in tab.values()), json.dumps(tab))

            # IN THE APP: from the first paint, then every frame until it has gone.
            WATCH_SPLASH = """() => { window.__sp = []; const t0 = performance.now(); const el = document.getElementById('bloobySplash');
              const first = { cls: document.documentElement.className, shown: getComputedStyle(el).display,
                              bar: document.querySelector('meta[name=theme-color]').content };
              const step = () => { const cs = getComputedStyle(el), c = el.querySelector('canvas');
                window.__sp.push({ t: performance.now() - t0, shown: cs.display !== 'none', o: +cs.opacity });
                if (performance.now() - t0 < 5200) requestAnimationFrame(step); };
              requestAnimationFrame(step); return first; }"""
            # Read as the page is parsed, before any deferred script runs (Skribl's lib/theme.js among them, which
            # stamps the bar again): what the first paint shows is the head's own work.
            FIRST_PAINT = "document.addEventListener('readystatechange', () => { if (document.readyState !== 'interactive') return; const el = document.getElementById('bloobySplash'); window.__dcl = { cls: document.documentElement.className, shown: el && getComputedStyle(el).display, bar: (document.querySelector('meta[name=theme-color]') || {}).content }; });"
            INK = """([tile, blush]) => { const c = document.querySelector('#bloobySplash canvas'); if (!c) return null;
              const x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; const hx = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
              const T = hx(tile), B = hx(blush); let w = 0, p = 0;
              for (let i = 0; i < x.length; i += 16) { if (x[i + 3] < 128) continue;
                const d = (a) => Math.abs(x[i] - a[0]) + Math.abs(x[i + 1] - a[1]) + Math.abs(x[i + 2] - a[2]);
                if (d(T) < 60) w++; else if (d(B) < 60) p++; }
              return [w, p]; }"""
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE, FIRST_PAINT))
            pg.goto(BASE + "/social/")
            first = pg.evaluate(WATCH_SPLASH)
            ink = []
            for at in (500, 1300, 1700, 2600):
                pg.wait_for_timeout(max(0, at - (ink[-1][0] if ink else 0)))
                ink.append((at, pg.evaluate(INK, [tile, blush])))
            # the night ground with no stars, as painted: the top, the foot, and no light dot between
            ground = pg.evaluate("""() => new Promise(res => { const el = document.getElementById('bloobySplash');
              const cs = getComputedStyle(el); res({ bg: cs.backgroundImage }); })""")
            shot = pg.screenshot()
            pg.wait_for_timeout(2600)
            fr = pg.evaluate("() => window.__sp")
            after = pg.evaluate("""() => ({ cls: document.documentElement.className, bar: document.querySelector('meta[name=theme-color]').content,
              seen: localStorage.getItem('blooby.splash.v1'), launch: sessionStorage.getItem('blooby.splash.launch') })""")
            dcl = pg.evaluate("() => window.__dcl")
            pg.goto(BASE + "/social/explore")
            pg.wait_for_function("() => document.readyState === 'complete'")
            pg.wait_for_timeout(300)
            next_page = pg.evaluate("() => document.documentElement.className")
            close_ctx(ctx, pg)
            im = Image.open(io.BytesIO(shot)).convert("RGB")
            W, H = im.size
            top, foot = im.getpixel((W // 2, 3)), im.getpixel((W // 2, H - 4))
            stars = sum(1 for y in range(10, H // 3, 3) for x in range(0, W, 3) if sum(im.getpixel((x, y))) > 300)
            check("in the app, the first launch: over the page from the first paint (is-splashing and shown before the "
                  "page's scripts), the browser's bar in its night (#0f1218), the night ground from the dark ground at "
                  "the top to the deep purple at the foot, and no stars",
                  dcl and "is-splashing" in dcl["cls"] and dcl["shown"] == "grid" and dcl["bar"] == "#0f1218"
                  and max(abs(a - c) for a, c in zip(top, (0x0f, 0x12, 0x18))) <= 6
                  and max(abs(a - c) for a, c in zip(foot, (0x2e, 0x21, 0x78))) <= 10 and stars == 0,
                  json.dumps({"dcl": dcl, "top": top, "foot": foot, "stars": stars}))
            check("...the word writes itself first, the blush only once it is written (it falls), then both whole",
                  all(v is not None for _, v in ink) and ink[0][1][0] > 0 and ink[0][1][1] == 0
                  and ink[1][1][0] > ink[0][1][0] and ink[1][1][1] == 0 and ink[2][1][1] > 0
                  and ink[3][1][0] >= ink[1][1][0] and ink[3][1][1] > 0, json.dumps(ink))
            shown = [f for f in fr if f["shown"]]
            fade = [f["o"] for f in shown if f["o"] < 0.999]
            gone_at = max((f["t"] for f in shown), default=0)
            steps = [abs(a - c) for a, c in zip([1.0] + fade, fade)]
            mids = [o for o in fade if 0.05 < o < 0.95]
            check("...then it fades on several frames (no frame more than a third at once) and is gone by 4 s, the "
                  "bar back in the page's ground, marked seen and this launch's",
                  len(mids) >= 4 and (max(steps) if steps else 1) <= 0.34 and 2600 <= gone_at <= 4000
                  and after["cls"] == "" and after["bar"] == "#f6f8fa" and after["seen"] == "1" and after["launch"] == "1",
                  json.dumps({"fade": [round(v, 2) for v in fade[:8]], "gone": round(gone_at), "after": after}))
            check("...once a launch: the next page in the app has none", next_page == "", next_page)

            # A LATER LAUNCH: the word there, only the blush falls, and it is quick.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE, "try { localStorage.setItem('blooby.splash.v1', '1'); } catch (e) {}"))
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_function("() => { const c = document.querySelector('#bloobySplash canvas'); return !!c && c.width > 0; }")
            pg.wait_for_timeout(120)
            early = pg.evaluate(INK, [tile, blush])
            pg.wait_for_timeout(2900)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            check("a later launch: the word is there from the start and only the blush falls; gone by 2.4 s",
                  early is not None and early[0] >= 0.9 * ink[3][1][0] and gone_at <= 2400,
                  json.dumps({"early": early, "whole": ink[3][1], "gone": round(gone_at)}))

            # A TAP LETS IT GO AT ONCE, fading.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE,))
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_timeout(500)
            pg.touchscreen.tap(201, 437)
            pg.wait_for_timeout(1000)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            fading = [f["o"] for f in fr if f["shown"] and 0.05 < f["o"] < 0.95]
            check("a tap lets it go at once: fading on several frames from the tap, gone within 0.6 s of it",
                  len(fading) >= 4 and gone_at <= 500 + 650, json.dumps({"gone": round(gone_at), "fading": len(fading)}))

            # REDUCE MOTION: the finished word, still, then the fade.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE,), reduced=True)
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_function("() => { const c = document.querySelector('#bloobySplash canvas'); return !!c && c.width > 0; }")
            pg.wait_for_timeout(150)
            a1 = pg.evaluate(INK, [tile, blush])
            pg.wait_for_timeout(300)
            a2 = pg.evaluate(INK, [tile, blush])
            pg.wait_for_timeout(1600)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            check("Reduce Motion: the finished word with its period, still (the same ink a moment later), then the fade; "
                  "gone by 1.6 s",
                  a1 is not None and a1 == a2 and a1[1] > 0 and a1[0] >= 0.9 * ink[3][1][0] and gone_at <= 1600,
                  json.dumps({"a": a1, "b": a2, "gone": round(gone_at)}))

            # NEVER HELD FOR A DRAWING THAT DOES NOT COME.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE,))
            pg.route("**/brand/blooby-splash.json*", lambda route: route.fulfill(status=404, body="no"))
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_timeout(1500)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            check("the drawing not there: it goes at once, fading (gone within 0.7 s), never holding the page",
                  gone_at <= 700, json.dumps({"gone": round(gone_at)}))

            # THE PAGE'S OWN DRAWING WAITS: Home's first visit draws Blooby's card, signed out, not under the splash.
            ctx, pg = browser_as(b, None, ua=IPHONE_UA, init=(STANDALONE,))
            pg.goto(BASE + "/social/")
            pg.evaluate("""() => { window.__card = []; const t0 = performance.now(); const step = () => {
                const sp = document.documentElement.classList.contains('is-splashing');
                const p = (window.SkriblInline && SkriblInline.players ? SkriblInline.players() : []).find(x => x.el && x.el.id === 'helloCard');
                window.__card.push({ t: performance.now() - t0, sp, playing: !!p && p.state().state === 'playing' });
                if (performance.now() - t0 < 5000) requestAnimationFrame(step); }; requestAnimationFrame(step); }""")
            pg.wait_for_timeout(5100)
            card = pg.evaluate("() => window.__card")
            close_ctx(ctx, pg)
            under = sum(1 for f in card if f["sp"] and f["playing"])
            later = any(f["playing"] for f in card if not f["sp"])
            check("the page's own drawing waits for it: Home's first visit draws Blooby's card once the splash has gone, "
                  "never under it", under == 0 and later, json.dumps({"under": under, "after": later}))

            # THE WORD AND THE PERIOD, READ OFF THE PAINT: at rest, against the ground beside them.
            img = im
            def lum(c):
                v = [x / 255 for x in c]
                v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
                return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
            def ratio(a, c):
                x, y = lum(a), lum(c)
                return round((max(x, y) + 0.05) / (min(x, y) + 0.05), 2)
            hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
            beside = img.getpixel((10, H // 2 - 30))
            check("the word and its period read off the paint against the ground beside them: the word 4.5:1 and more, "
                  "the period 3:1 and more", ratio(hx(tile), beside) >= 4.5 and ratio(hx(blush), beside) >= 3.0,
                  json.dumps({"ground": beside, "word": ratio(hx(tile), beside), "period": ratio(hx(blush), beside)}))
        except Exception as exc:  # noqa: BLE001
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "no page errors, no console errors and no CSP violations"):
        try:
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001
            stopped(9, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
