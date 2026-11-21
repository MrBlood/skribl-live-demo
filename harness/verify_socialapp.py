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
     way", on the dark ground "with no stars", then Blooby jumping, "All yes,
     B with the stage spotlight"): its pictures, the site's hello and his
     strip, the last pose without its sparks; never in a browser tab, his
     strip never downloaded there; in the app, over the page from the first
     paint, the night ground and the bar the same; the spotlight in the
     icon's lilac, still, coming up once the pictures are here; his jump read
     on every frame (the floor, the top, the poses in order, his shadow, and
     it glides); his outline against the light at every pose; the word
     writes itself, then the blush; once a launch; a later launch quick; a
     tap lets it go; still under Reduce Motion; never held for a picture that
     does not come; the page's own drawing waits for it; it fades out on
     several frames and the bar comes back; the word and its period read off
     the paint.
  9. THE APP'S TOP EDGE (the owner, Nov 15, from the Home Screen app: "the
     top bar is fuzzy on top"): in the app, every page's top 6px are its own
     ground over whatever scrolls under them, light and dark, so iOS 26 lays
     no glass blur there; never in a tab; under the sheets' scrims; out of
     the header's buttons' way.
  11. HOW IT WORKS (the owner's "All yes", Nov 19: "first row on a phone,
     above Settings on a desktop, and there for visitors too", opening
     "Blooby's own short page, with Pad's and Flip's help at the bottom").
     THE DOOR: the ☰'s first row, with its mark, as tall as the others,
     opening /social/how, for a visitor too; on a desk a tab in the rail
     above Settings (above Sign in before that), lit on its own page; a
     phone's bar keeps its four. THE PAGE: its head and three parts, nothing
     past the screen. THE EXAMPLES: three of Skribl's in-post player, each a
     drawing from its file, their boxes the drawings' shape before the
     drawings come (nothing moves); each play button says what the files
     say (the cat's own time; the draw-back's two hands, read off both
     files; the Flip's pages), the draw-back's file being that cat and then
     an answer; the first draws itself as the page opens and the others
     wait, none under Reduce Motion; a tap plays one and stops another; when
     the files do not come, one line says so and Try again brings them.
     PEOPLE OFTEN ASK: four rows, a tap going where it is done (the composer
     here; Home's Everyone; your profile); a visitor reads the same four
     with nothing to tap, and a line with Sign in. THE DRAWING TOOLS: signed
     in, the Pad or Flip inside a post with its own How it works showing,
     only the editor seen, its × back on the page, asked again without a
     reload; a visitor, the editor's own page with it. EVERY WORD at 4.5:1,
     every row 44px and more, phone and desk, light and dark.
  10. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

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
import urllib.parse
import urllib.request
from pathlib import Path

from assertions import make_check
from PIL import Image, ImageChops, ImageFilter

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
            check("an iPhone in a browser tab: Add to Home Screen in the ☰, right under Settings (How it works is the sheet's"
                  " first row since Nov 19, so it is the third); no Reload",
                  ip["add"] and ip["addPainted"] and not ip["reload"]
                  and ip["rows"][:3] == ["How it works", "Settings", "Add to Home Screen"], json.dumps(ip))
            check("signed out, the same row right under Sign in", io_["add"] and io_["addPainted"]
                  and io_["rows"][:3] == ["How it works", "Sign in", "Add to Home Screen"], json.dumps(io_))
            check("an iPad, which says it is a Mac with a touch screen: the same row", ipad["add"] and ipad["addPainted"],
                  json.dumps(ipad))
            check("opened from the Home Screen (navigator.standalone): Reload in its place, right under Settings; no Add to"
                  " Home Screen",
                  app["reload"] and app["reloadPainted"] and not app["add"]
                  and app["rows"][:3] == ["How it works", "Settings", "Reload"], json.dumps(app))
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
                  return { add: r(document.getElementById('siteAddHome')), settings: r(rows.find(e => e.textContent.trim() === 'Settings')) }; }""")
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
    if part(8, "the splash: the app's first paint, Blooby's jump in a stage spotlight, the word and its blush, kind"):
        try:
            sys.path.insert(0, str(ROOT / "harness" / "tools"))
            import importlib
            tile = importlib.import_module("blooby").ICON_TILE.lower()
            css = (ROOT / "social" / "static" / "social.css").read_text(encoding="utf-8")
            brand = re.search(r"--brand:\s*(#[0-9a-fA-F]{6})", css).group(1).lower()
            blush = re.search(r"--blooby-blush:\s*(#[0-9a-fA-F]{6})", css).group(1).lower()
            hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

            def lum(c):
                v = [x / 255 for x in c[:3]]
                v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
                return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

            def ratio(a, c):
                x, y = lum(a), lum(c)
                return round((max(x, y) + 0.05) / (min(x, y) + 0.05), 2)

            # ITS PICTURES, as the page names them: the word is the site's hello, Blooby his strip, and the head
            # asks for the same two.
            st, _, body = get("/social/")
            html = body.decode("utf-8")
            def named(pat):
                m = re.search(pat, html)
                return m.group(1) if m else None
            names = {"word": named(r'id="bloobySplash"[^>]*\sdata-splash="([^"?]+)'),
                     "strip": named(r'<div class="splash-jump"[^>]*><img [^>]*data-src="([^"?]+)'),
                     "boot_word": named(r'splash-boot\.js[^"]*"[^>]*\sdata-word="([^"?]+)'),
                     "boot_jump": named(r'splash-boot\.js[^"]*"[^>]*\sdata-jump="([^"?]+)')}
            hello = json.load(open(ROOT / "social" / "static" / "brand" / "blooby-hello.json"))
            inks = [sorted({q["color"].lower() for q in f["strokes"]}) for f in hello["frames"]]
            check("its pictures: the word is the site's hello (brand/blooby-hello.json: the word in the site's purple, "
                  "its period in Blooby's blush, falling as skribl's i-dot does), Blooby is his strip (brand/"
                  "blooby-splash-jump.webp), and the head asks for the same two",
                  bool(names["word"]) and names["word"].endswith("/brand/blooby-hello.json")
                  and bool(names["strip"]) and names["strip"].endswith("/brand/blooby-splash-jump.webp")
                  and names["boot_word"] == names["word"] and names["boot_jump"] == names["strip"]
                  and inks[0] == [brand] and all(k == [blush] for k in inks[1:])
                  and hello.get("under") == {"page": 0, "from": 1, "to": len(hello["frames"]) - 1},
                  json.dumps({"names": names, "inks": inks[:3]}))

            # HIS STRIP: seven poses on a clear ground; the last Blooby alone, arms up (the owner: "lose the little
            # motion lines on the last frame by his hand balls"), the poses at the top with their sparks.
            strip = Image.open(ROOT / "social" / "static" / "brand" / "blooby-splash-jump.webp").convert("RGBA")
            fw = strip.width // 7

            def shapes(k, q=4, cut=64):
                """Frame k's separate shapes of ink (its alpha at a quarter size, side by side counts)."""
                a = strip.crop((k * fw, 0, (k + 1) * fw, strip.height)).getchannel("A").resize((fw // q, strip.height // q))
                w, h = a.size
                px = a.load()
                seen, sizes = set(), []
                for y in range(h):
                    for x in range(w):
                        if px[x, y] > cut and (x, y) not in seen:
                            stack, c = [(x, y)], 0
                            seen.add((x, y))
                            while stack:
                                cx, cy = stack.pop()
                                c += 1
                                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and px[nx, ny] > cut:
                                        seen.add((nx, ny))
                                        stack.append((nx, ny))
                            sizes.append(c)
                return sizes
            parts = [len(shapes(k)) for k in range(7)]
            corners = [strip.getpixel((k * fw + dx, dy))[3] for k in range(7)
                       for dx, dy in ((2, 2), (fw - 3, 2), (2, strip.height - 3), (fw - 3, strip.height - 3))]
            check("his strip: seven poses side by side on a clear ground, each frame as tall as wide or near it, the last "
                  "Blooby alone with his arms up (one shape: no lines by his hands), the top of his jump with its sparks",
                  strip.width % 7 == 0 and 0.9 < fw / strip.height < 1.0 and max(corners) == 0
                  and parts[6] == 1 and parts[3] >= 3,
                  json.dumps({"size": strip.size, "shapes": parts, "corners": max(corners)}))

            # THE SPLASH'S OWN CLASSES, read off what splash-boot.js puts on the page (its classList.add calls).
            # The page wears others that are none of the splash's business (lib/postfull.js's skribl-postfull,
            # since #939), so a row about the splash asks about these, never the whole class list. The three it
            # has always had must be among them: a boot that stamps a class another way goes red here, not quiet.
            boot = (ROOT / "social" / "static" / "splash-boot.js").read_text(encoding="utf-8")
            SPLASH_CLS = {c for a in re.findall(r"classList\.add\(([^)]*)\)", boot) for c in re.findall(r"'([\w-]+)'", a)}
            ours = lambda cls: SPLASH_CLS & set(cls.split())

            # NEVER IN A BROWSER TAB: Home and the Gallery, signed in; not shown, and its pictures never asked for.
            mira = member(b, "mira", "Mira Lopez")
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA)
            asked = []
            pg.on("request", lambda r: asked.append(r.url.split("/")[-1]) if "splash-jump" in r.url else None)
            tab = {}
            for path in ("/social/", "/social/explore"):
                pg.goto(BASE + path)
                pg.wait_for_function("() => document.readyState === 'complete'")
                pg.wait_for_timeout(300)
                tab[path] = pg.evaluate("""() => ({ cls: document.documentElement.className,
                  shown: getComputedStyle(document.getElementById('bloobySplash')).display })""")
            close_ctx(ctx, pg)
            check("never in a browser tab: no splash on Home or the Gallery, and Blooby's strip never downloaded there "
                  "(only the Home Screen app opens with one)",
                  {"is-app", "is-splashing", "is-splash-first"} <= SPLASH_CLS
                  and all(not ours(v["cls"]) and v["shown"] == "none" for v in tab.values()) and not asked,
                  json.dumps({"tab": tab, "asked": asked, "the splash's": sorted(SPLASH_CLS)}))

            # IN THE APP: from the first paint, then every frame until it has gone: the splash, the show, his box
            # (lift and squash), the strip's pose, his shadow, and where the light is.
            WATCH_SPLASH = """() => { window.__sp = []; const t0 = performance.now(); const el = document.getElementById('bloobySplash');
              const show = el.querySelector('.splash-show'), j = el.querySelector('.splash-jump'), im = j.querySelector('img'),
                    sh = el.querySelector('.splash-shadow'), beam = el.querySelector('.splash-beam'), pool = el.querySelector('.splash-pool');
              const first = { cls: document.documentElement.className, shown: getComputedStyle(el).display,
                              bar: document.querySelector('meta[name=theme-color]').content };
              const r = e => { const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height].map(v => Math.round(v * 10) / 10).join(','); };
              const step = () => { const cs = getComputedStyle(el), m = new DOMMatrix(getComputedStyle(j).transform),
                  s = new DOMMatrix(getComputedStyle(im).transform), w = im.offsetWidth / 7;
                window.__sp.push({ t: performance.now() - t0, shown: cs.display !== 'none', o: +cs.opacity,
                  show: +getComputedStyle(show).opacity, on: el.classList.contains('is-on'), pic: im.complete && im.naturalWidth > 0,
                  lift: Math.round(m.m42 * 10) / 10, sx: m.m11, sy: m.m22, pose: w ? Math.round(-s.m41 / w) : -1,
                  shade: +getComputedStyle(sh).opacity, light: r(beam) + '|' + r(pool) });
                if (performance.now() - t0 < 5200) requestAnimationFrame(step); };
              requestAnimationFrame(step); return first; }"""
            # Read as the page is parsed, before any deferred script runs (Skribl's lib/theme.js among them, which
            # stamps the bar again): what the first paint shows is the head's own work.
            # The moment the show comes up, caught as it happens (from before the page's scripts run): are both its
            # pictures here then? The trace starts too late to see it: by the page's load the strip has come anyway.
            ON_AT = ("new MutationObserver((ms, ob) => { for (const m of ms) { const el = m.target; if (el.id !== 'bloobySplash' "
                     "|| !el.classList.contains('is-on')) continue; const im = el.querySelector('.splash-jump img'); "
                     "const p = (window.SkriblInline && SkriblInline.players ? SkriblInline.players() : []).find(x => x.el && x.el.id === 'splashBox'); "
                     "window.__onAt = { pic: !!im && im.complete && im.naturalWidth > 0, word: !!p && p.state().loaded }; ob.disconnect(); return; } })"
                     ".observe(document, { subtree: true, attributes: true, attributeFilter: ['class'] });")
            FIRST_PAINT = "document.addEventListener('readystatechange', () => { if (document.readyState !== 'interactive') return; const el = document.getElementById('bloobySplash'); window.__dcl = { cls: document.documentElement.className, shown: el && getComputedStyle(el).display, bar: (document.querySelector('meta[name=theme-color]') || {}).content }; });"
            INK = """([word, blush]) => { const c = document.querySelector('#bloobySplash canvas'); if (!c) return null;
              const x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; const hx = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
              const T = hx(word), B = hx(blush); let w = 0, p = 0;
              for (let i = 0; i < x.length; i += 16) { if (x[i + 3] < 128) continue;
                const d = (a) => Math.abs(x[i] - a[0]) + Math.abs(x[i + 1] - a[1]) + Math.abs(x[i + 2] - a[2]);
                if (d(T) < 60) w++; else if (d(B) < 60) p++; }
              return [w, p]; }"""
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE, FIRST_PAINT, ON_AT))
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            # the word's moments, from when the show comes up (once its pictures are here)
            pg.wait_for_function("() => document.getElementById('bloobySplash').classList.contains('is-on')", timeout=6000)
            t_on = time.time()
            ink = []
            for at in (400, 1200, 1750, 2600):
                pg.wait_for_timeout(max(0, at - (time.time() - t_on) * 1000))
                ink.append((at, pg.evaluate(INK, [brand, blush])))
            shot = pg.screenshot()
            jump_foot = pg.evaluate("() => document.querySelector('#bloobySplash .splash-jump').getBoundingClientRect().bottom")
            pg.wait_for_timeout(2400)
            fr = pg.evaluate("() => window.__sp")
            after = pg.evaluate("""() => ({ cls: document.documentElement.className, bar: document.querySelector('meta[name=theme-color]').content,
              seen: localStorage.getItem('blooby.splash.v1'), launch: sessionStorage.getItem('blooby.splash.launch') })""")
            dcl = pg.evaluate("() => window.__dcl")
            on_at = pg.evaluate("() => window.__onAt || null")
            light_css = pg.evaluate("""() => { const el = document.getElementById('bloobySplash');
              return getComputedStyle(el).getPropertyValue('--splash-light').trim(); }""")
            pg.goto(BASE + "/social/explore")
            pg.wait_for_function("() => document.readyState === 'complete'")
            pg.wait_for_timeout(300)
            next_page = pg.evaluate("() => document.documentElement.className")
            close_ctx(ctx, pg)
            im = Image.open(io.BytesIO(shot)).convert("RGB")
            W, H = im.size
            top, foot = im.getpixel((8, 3)), im.getpixel((8, H - 4))
            stars = sum(1 for y in range(10, 2 * H // 3, 3) for x in list(range(0, 24, 3)) + list(range(W - 24, W, 3))
                        if sum(im.getpixel((x, y))) > 300)
            check("in the app, the first launch: over the page from the first paint (is-splashing and shown before the "
                  "page's scripts), the browser's bar in its night (#0f1218), the night ground from the dark ground at "
                  "the top to the deep purple at the foot, and no stars beside the light",
                  bool(dcl) and "is-splashing" in dcl["cls"] and dcl["shown"] == "block" and dcl["bar"] == "#0f1218"
                  and max(abs(a - c) for a, c in zip(top, (0x0f, 0x12, 0x18))) <= 6
                  and max(abs(a - c) for a, c in zip(foot, (0x2e, 0x21, 0x78))) <= 10 and stars == 0,
                  json.dumps({"dcl": dcl, "top": top, "foot": foot, "stars": stars}))

            # THE STAGE SPOTLIGHT: in the icon's lilac, still, coming up with Blooby and the word, and only once both
            # pictures are here.
            shown = [f for f in fr if f["shown"]]
            up = [f["show"] for f in shown if f["on"]]
            rise = [o for o in up if 0.05 < o < 0.95]
            rsteps = [c - a for a, c in zip(up, up[1:])]
            lights = {f["light"] for f in shown if f["show"] > 0.99 and f["o"] > 0.99}
            check("the stage spotlight: in the icon's lilac (blooby.py's ICON_TILE), still while he jumps (the beam and the "
                  "pool where they were on every frame), coming up with him and the word on several frames (none more "
                  "than a third at once), and only once his strip and the word's drawing are here",
                  tuple(int(v) for v in light_css.split()) == hx(tile) and len(lights) == 1 and len(rise) >= 4
                  and max(rsteps or [1]) <= 0.34 and on_at == {"pic": True, "word": True},
                  json.dumps({"light": light_css, "tile": tile, "places": len(lights), "rise": len(rise),
                              "step": round(max(rsteps or [1]), 2), "up with": on_at}))

            # HIS JUMP, read on every frame: he leaves the floor and lands, his poses in order, his shadow with him;
            # it glides: no frame moves him faster than the jump is drawn to (1.8 px a ms at its fastest).
            jumping = [f for f in shown if f["on"] and f["o"] > 0.99]
            lifts = [f["lift"] for f in jumping]
            poses = [f["pose"] for f in jumping]
            order = [p for i, p in enumerate(poses) if i == 0 or p != poses[i - 1]]
            fast = [(round(c["t"]), round(abs(c["lift"] - a["lift"]) / max(1, c["t"] - a["t"]), 2))
                    for a, c in zip(jumping, jumping[1:]) if abs(c["lift"] - a["lift"]) > 2.2 * (c["t"] - a["t"]) + 2]
            peak = min(lifts or [0])
            i_top = lifts.index(peak) if lifts else 0
            on_way_up = [v for v in lifts[:i_top] if -90 < v < -5]
            on_way_down = [v for v in lifts[i_top:] if -90 < v < -5]
            at_top = [f["shade"] for f in jumping if f["lift"] <= -90]
            check("his jump, read on every frame: he crouches, leaves the floor 96px (the top of his jump) and lands back "
                  "on it, his seven poses in order and the last held (arms up); his shadow smaller and fainter at the top "
                  "and whole on the floor; and it glides (several frames between the floor and the top each way, none "
                  "moving him faster than the jump is drawn to)",
                  -97.5 <= peak <= -94.5 and abs(lifts[-1]) < 0.5 and order == [0, 1, 2, 3, 4, 5, 6]
                  and len(on_way_up) >= 6 and len(on_way_down) >= 4 and not fast
                  and bool(at_top) and max(at_top) <= 0.45 and jumping[-1]["shade"] > 0.99,
                  json.dumps({"peak": peak, "end": lifts[-1] if lifts else None, "order": order, "up": len(on_way_up),
                              "down": len(on_way_down), "fast": fast[:4], "shade_top": max(at_top or [1])}))

            check("...the word writes itself first, the blush only once it is written (it falls), then both whole",
                  all(v is not None for _, v in ink) and ink[0][1][0] > 0 and ink[0][1][1] == 0
                  and ink[1][1][0] > ink[0][1][0] and ink[1][1][1] == 0 and ink[2][1][1] > 0
                  and ink[3][1][0] >= ink[1][1][0] and ink[3][1][1] > 0, json.dumps(ink))
            fade = [f["o"] for f in shown if f["o"] < 0.999]
            gone_at = max((f["t"] for f in shown), default=0)
            steps = [abs(a - c) for a, c in zip([1.0] + fade, fade)]
            mids = [o for o in fade if 0.05 < o < 0.95]
            check("...then it fades on several frames (no frame more than a third at once) and is gone by 4.6 s, the "
                  "bar back in the page's ground, marked seen and this launch's",
                  len(mids) >= 4 and (max(steps) if steps else 1) <= 0.34 and 2600 <= gone_at <= 4600
                  and not {"is-splashing", "is-splash-first"} & set(after["cls"].split()) and after["bar"] == "#f6f8fa"
                  and after["seen"] == "1" and after["launch"] == "1",
                  json.dumps({"fade": [round(v, 2) for v in fade[:8]], "gone": round(gone_at), "after": after}))
            check("...once a launch: the next page in the app has none (it is the app's still: is-app, not is-splashing)",
                  ours(next_page) == {"is-app"}, next_page)

            # HIS OUTLINE AGAINST THE LIGHT (the owner: "you can't see his black outline"), at every pose: his
            # dark ink against what is painted just outside him (2 to 4 px out), read off two shots, the splash as
            # it is and Blooby alone on white, which says where he and his ink are. The word is held still so the
            # splash stays while it is read.
            FREEZE = """(ms) => { const el = document.getElementById('bloobySplash');
              const p = (SkriblInline.players ? SkriblInline.players() : []).find(x => x.el && x.el.id === 'splashBox'); if (p) p.seek(0);
              const a = ['.splash-jump', '.splash-jump img', '.splash-shadow'].flatMap(s => el.querySelector(s).getAnimations());
              a.forEach(x => { x.pause(); x.currentTime = ms; }); return a.length; }"""
            ALONE = """(on) => { const el = document.getElementById('bloobySplash'); el.style.background = on ? '#fff' : '';
              for (const s of ['.splash-beam', '.splash-pool', '.splash-shadow', '.splash-word']) el.querySelector(s).style.visibility = on ? 'hidden' : ''; }"""
            HOLD = [266, 384, 523, 853, 974, 1151, 1220]     # each pose, held (splash.js POSES)

            def outline(s_png, w_png):
                S = Image.open(io.BytesIO(s_png)).convert("RGB")
                Wb = Image.open(io.BytesIO(w_png)).convert("RGB")
                M = ImageChops.difference(Wb, Image.new("RGB", Wb.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 12 else 0)
                ring = ImageChops.subtract(M.filter(ImageFilter.MaxFilter(9)), M.filter(ImageFilter.MaxFilter(3)))
                inkm = ImageChops.multiply(Wb.convert("L").point(lambda v: 255 if v < 50 else 0), ring.filter(ImageFilter.MaxFilter(9)))
                sp, wd = S.load(), S.size[0]
                at = lambda m: [(i % wd, i // wd) for i, v in enumerate(m.getdata()) if v]
                cols = [sp[x, y] for x, y in at(inkm)]
                if not cols:
                    return None
                col = tuple(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(3))
                rs = sorted(ratio(sp[x, y], col) for x, y in at(ring))
                return {"p10": rs[len(rs) // 10], "min": rs[0]}

            def read_poses(screen, which):
                c2, p2 = browser_as(b, mira, screen=screen, ua=IPHONE_UA, init=(STANDALONE,))
                p2.goto(BASE + "/social/")
                p2.wait_for_function("() => document.querySelector('#bloobySplash .splash-jump').getAnimations().length > 0", timeout=8000)
                p2.wait_for_timeout(450)
                got = {}
                for k in which:
                    p2.evaluate(FREEZE, HOLD[k])
                    p2.wait_for_timeout(40)
                    s_png = p2.screenshot()
                    p2.evaluate(ALONE, True)
                    p2.wait_for_timeout(40)
                    w_png = p2.screenshot()
                    p2.evaluate(ALONE, False)
                    got[k] = outline(s_png, w_png)
                close_ctx(c2, p2)
                return got
            phone = read_poses("phone", range(7))
            desk = read_poses("desk", (3,))
            every = list(phone.values()) + list(desk.values())
            check("his outline shows against the light at every pose: his ink against what is painted just outside him, "
                  "4.5:1 and more for nearly all of it and 3:1 at its faintest, on a phone at each of his seven poses "
                  "and on a desk at the top of his jump (on the night alone it is 1.1:1)",
                  all(v and v["p10"] >= 4.5 and v["min"] >= 3.0 for v in every),
                  json.dumps({"phone": phone, "desk": desk}))

            # A LATER LAUNCH: the word there, he jumps as the blush falls, and it is quick.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE, "try { localStorage.setItem('blooby.splash.v1', '1'); } catch (e) {}"))
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_function("() => document.getElementById('bloobySplash').classList.contains('is-on')")
            pg.wait_for_timeout(60)
            early = pg.evaluate(INK, [brand, blush])
            pg.wait_for_timeout(3200)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            top_later = min((f["lift"] for f in fr if f["shown"]), default=0)
            check("a later launch: the word is there from the start, he jumps all the same (to the top) as the blush "
                  "falls; gone by 2.9 s",
                  early is not None and early[0] >= 0.9 * ink[3][1][0] and top_later <= -94.5 and gone_at <= 2900,
                  json.dumps({"early": early, "whole": ink[3][1], "top": top_later, "gone": round(gone_at)}))

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

            # REDUCE MOTION: Blooby still in his last pose, the light on, the word whole, then the fade.
            ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE,), reduced=True)
            pg.goto(BASE + "/social/")
            pg.evaluate(WATCH_SPLASH)
            pg.wait_for_function("() => document.getElementById('bloobySplash').classList.contains('is-on')")
            pg.wait_for_timeout(150)
            a1 = pg.evaluate(INK, [brand, blush])
            pg.wait_for_timeout(300)
            a2 = pg.evaluate(INK, [brand, blush])
            pg.wait_for_timeout(1700)
            fr = pg.evaluate("() => window.__sp")
            close_ctx(ctx, pg)
            on = [f for f in fr if f["shown"] and f["on"]]
            gone_at = max((f["t"] for f in fr if f["shown"]), default=0)
            check("Reduce Motion: Blooby still in his last pose, arms up, on every frame (no lift, no squash), the light "
                  "on, the word whole with its period and still (the same ink a moment later), then the fade; gone by "
                  "2 s",
                  bool(on) and all(f["pose"] == 6 and f["lift"] == 0 and f["sx"] == 1 and f["sy"] == 1 for f in on)
                  and max(f["show"] for f in on) > 0.99
                  and a1 is not None and a1 == a2 and a1[1] > 0 and a1[0] >= 0.9 * ink[3][1][0] and gone_at <= 2000,
                  json.dumps({"poses": sorted({f["pose"] for f in on}), "lifts": sorted({f["lift"] for f in on})[:4],
                              "a": a1, "b": a2, "gone": round(gone_at)}))

            # NEVER HELD FOR A PICTURE THAT DOES NOT COME: the word's drawing, or Blooby's strip.
            held = {}
            for what, pat in (("the word's drawing", "**/brand/blooby-hello.json*"), ("his strip", "**/brand/blooby-splash-jump.webp*")):
                ctx, pg = browser_as(b, mira, ua=IPHONE_UA, init=(STANDALONE,))
                pg.route(pat, lambda route: route.fulfill(status=404, body="no"))
                pg.goto(BASE + "/social/")
                pg.evaluate(WATCH_SPLASH)
                pg.wait_for_timeout(1500)
                fr = pg.evaluate("() => window.__sp")
                close_ctx(ctx, pg)
                held[what] = {"gone": round(max((f["t"] for f in fr if f["shown"]), default=0)),
                              "show": max((f["show"] for f in fr), default=0)}
            check("either picture not there (the word's drawing, his strip): it goes at once, fading (gone within 0.7 s), "
                  "never holding the page, and the show never comes up without it",
                  all(v["gone"] <= 700 and v["show"] == 0 for v in held.values()), json.dumps(held))

            # THE PAGE'S OWN DRAWING WAITS: Home's first visit draws Blooby's card, signed out, not under the splash.
            ctx, pg = browser_as(b, None, ua=IPHONE_UA, init=(STANDALONE,))
            pg.goto(BASE + "/social/")
            pg.evaluate("""() => { window.__card = []; const t0 = performance.now(); const step = () => {
                const sp = document.documentElement.classList.contains('is-splashing');
                const p = (window.SkriblInline && SkriblInline.players ? SkriblInline.players() : []).find(x => x.el && x.el.id === 'helloCard');
                window.__card.push({ t: performance.now() - t0, sp, playing: !!p && p.state().state === 'playing' });
                if (performance.now() - t0 < 5500) requestAnimationFrame(step); }; requestAnimationFrame(step); }""")
            pg.wait_for_timeout(5600)
            card = pg.evaluate("() => window.__card")
            close_ctx(ctx, pg)
            under = sum(1 for f in card if f["sp"] and f["playing"])
            later = any(f["playing"] for f in card if not f["sp"])
            check("the page's own drawing waits for it: Home's first visit draws Blooby's card once the splash has gone, "
                  "never under it", under == 0 and later, json.dumps({"under": under, "after": later}))

            # THE WORD UNDER THE STAGE (the owner, of 83%, 76% and 70%: "70"): its ink read off the paint below
            # Blooby's feet (his purple is the word's), its middle at 70% of the splash, all of it below the light's
            # pool.
            pool = [float(v) for v in next(f["light"] for f in reversed(shown) if f["show"] > 0.99).split("|")[1].split(",")]
            pool_foot = pool[1] + pool[3]
            B, pxs = hx(brand), im.load()
            rows = [y for y in range(int(jump_foot) + 1, H)
                    if sum(1 for x in range(0, W, 2) if sum(abs(a - c) for a, c in zip(pxs[x, y], B)) < 60) >= 3]
            word_mid = (rows[0] + rows[-1]) / 2 if rows else None
            check("the word under the stage (the owner's 70): its ink's middle at 70% of the splash, give or take 2%, and "
                  "all of it below the light's pool",
                  bool(rows) and abs(word_mid / H - 0.70) <= 0.02 and rows[0] > pool_foot,
                  json.dumps({"word": [rows[0], rows[-1]] if rows else None, "middle": round(word_mid / H * 100, 1) if rows else None,
                              "pool_foot": round(pool_foot), "his_feet": round(jump_foot)}))

            # THE WORD AND THE PERIOD, READ OFF THE PAINT, against the ground beside them at the word's own height: a big
            # word in the site's purple, 3:1 and more (the bar for large text), its period the same.
            beside = im.getpixel((8, round(word_mid if rows else H * 0.70)))
            check("the word and its period read off the paint against the ground beside them: the word (the site's purple, "
                  "a large word) 3:1 and more, the period 3:1 and more",
                  ratio(hx(brand), beside) >= 3.0 and ratio(hx(blush), beside) >= 3.0,
                  json.dumps({"ground": beside, "word": ratio(hx(brand), beside), "period": ratio(hx(blush), beside)}))
        except Exception as exc:  # noqa: BLE001
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "the app's top edge: the page's own ground, so iOS 26 lays no glass over it"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            # Something under the top to cover: a tall red block at the head of the page, scrolled up past the top.
            UNDER = """() => { const d = document.createElement('div'); d.style.cssText = 'height:1600px;background:#ff0000';
              const m = document.querySelector('main') || document.body; m.insertBefore(d, m.firstChild); window.scrollTo(0, 300); }"""
            def top_rows(pg):
                im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
                W = im.width
                rows = [{im.getpixel((x, y)) for x in range(0, W, 7)} for y in range(0, 12)]
                return rows
            hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
            app_rows, tab_rows = {}, {}
            for scheme in ("light", "dark"):
                for path in ("/social/", "/social/explore"):
                    ctx, pg = browser_as(b, mira, scheme=scheme, ua=IPHONE_UA, init=(STANDALONE, SPLASHED))
                    go(pg, path)
                    ground = pg.evaluate("() => getComputedStyle(document.body).getPropertyValue('--page').trim()")
                    pg.evaluate(UNDER)
                    pg.wait_for_timeout(200)
                    rows = top_rows(pg)
                    app_rows[f"{scheme} {path}"] = {"ground": ground, "edge": [sorted(r) for r in rows[:6]],
                                                    "below": sorted(rows[8])[:3]}
                    close_ctx(ctx, pg)
                ctx, pg = browser_as(b, mira, scheme=scheme, ua=IPHONE_UA)
                go(pg, "/social/")
                pg.evaluate(UNDER)
                pg.wait_for_timeout(200)
                tab_rows[scheme] = [sorted(r)[:2] for r in top_rows(pg)[:6]]
                close_ctx(ctx, pg)
            red = (255, 0, 0)
            check("in the app, the top edge is the page's own ground on every page (Home, the Gallery), light and dark: "
                  "its top 6px all that ground, over the page scrolled up under it, and the page itself just below",
                  all(all(r == [hx(v["ground"])] for r in v["edge"]) and red in v["below"]
                      for v in app_rows.values()),
                  json.dumps(app_rows)[:600])
            check("a browser tab never has it: the page runs up to the top edge there",
                  all(all(red in r for r in v) for v in tab_rows.values()), json.dumps(tab_rows))

            # UNDER THE SHEETS, AND OUT OF THE HEADER'S WAY: the ☰'s scrim dims it; the ☰ takes a tap at its own top.
            ctx, pg = browser_as(b, mira, scheme="light", ua=IPHONE_UA, init=(STANDALONE, SPLASHED))
            go(pg, "/social/")
            ground = hx(pg.evaluate("() => getComputedStyle(document.body).getPropertyValue('--page').trim()"))
            hit = pg.evaluate("""() => { const m = document.querySelector('[data-site-menu]'); const r = m.getBoundingClientRect();
              const at = document.elementFromPoint(r.x + r.width / 2, r.top + 1); return { top: r.top, mine: !!at && !!at.closest('[data-site-menu]') }; }""")
            open_menu(pg)
            dim = Image.open(io.BytesIO(pg.screenshot())).convert("RGB").getpixel((201, 3))
            close_ctx(ctx, pg)
            check("...under the bar and every sheet: the ☰'s scrim dims it as it dims the page; and the header's buttons "
                  "start below it and take their taps (the ☰ at its own top edge)",
                  sum(dim) < sum(ground) - 60 and hit["top"] >= 6 and hit["mine"],
                  json.dumps({"ground": ground, "dimmed": dim, "menu": hit}))
        except Exception as exc:  # noqa: BLE001
            stopped(9, exc)

    # ------------------------------------------------------------------ 11
    # HOW IT WORKS, the site's own page and its two doors (the owner's "All
    # yes", Nov 19). The site had no door to any help: its menu's own note
    # said "No Help row until there is a Help page." What the examples say is
    # worked out HERE from the three files themselves, never copied from the
    # page: the cat's own time, the answer's own time in the draw-back's
    # file, the Flip's pages.
    if part(11, "How it works: the ☰'s first row, a tab in the rail, and the site's own page with its examples and rows"):
        try:
            mira = member(b, "mira", "Mira Lopez")
            cat_f = json.loads((ROOT / "skribl/static/help/demos/cat.json").read_text())
            back_f = json.loads((ROOT / "social/static/how/drawback.json").read_text())
            flip_f = json.loads((ROOT / "skribl/static/help/demos/flip-bounce.json").read_text())
            cat_pts, back_pts = cat_f["frames"][0]["strokes"], back_f["frames"][0]["strokes"]
            # The answer: what the file holds after the cat's points (a file
            # that is only the cat has none, and says so in its row).
            his = back_pts[len(cat_pts):] or [{"t": 0}]
            hers_s, his_s = round(cat_pts[-1]["t"] / 1000), round((his[-1]["t"] - his[0]["t"]) / 1000)
            same_cat = len(back_pts) >= len(cat_pts) and all(
                abs(a["x"] - c["x"]) < 0.01 and abs(a["y"] - c["y"]) < 0.01 and a["color"] == c["color"] for a, c in zip(cat_pts, back_pts))
            hers_end = back_pts[min(len(cat_pts), len(back_pts)) - 1]["t"]
            check("the draw-back example is a draw-back: its file holds Skribl's cat point for point, squeezed to three"
                  " seconds as the site joins one, then an answer that starts after it; and the Flip has pages",
                  same_cat and len(back_pts) > len(cat_pts) + 50 and hers_end <= 3000
                  and his[0].get("start") is True and his[0]["t"] > hers_end
                  and back_f["canvasSize"]["cssWidth"] * 3 == back_f["canvasSize"]["cssHeight"] * 4 and len(flip_f["frames"]) > 1,
                  f"the cat's {len(cat_pts)} points first: {same_cat}, of {len(back_pts)}; hers ends at {hers_end}ms, his from"
                  f" {his[0]['t']} to {his[-1]['t']}; the Flip's pages {len(flip_f['frames'])}")

            # ---- THE DOOR ---------------------------------------------------------
            door = {}
            for key, who in (("signed in", mira), ("a visitor", None)):
                ctx, pg = browser_as(b, who)
                go(pg, "/social/")
                open_menu(pg)
                door[key] = pg.evaluate("""() => { const rows = [...document.querySelectorAll('#siteMenu .post-acts > .post-act, #siteMenu .post-acts > form > .post-act')].filter(e => e.getClientRects().length);
                  const r0 = rows[0], r = r0.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  return { rows: rows.map(e => e.textContent.trim()), href: r0.getAttribute('href'), h: Math.round(r.height), hs: rows.map(e => Math.round(e.getBoundingClientRect().height)),
                           mark: !!r0.querySelector('svg circle') && !!r0.querySelector('svg path'), hit: !!at && r0.contains(at),
                           bar: [...document.querySelectorAll('nav.nav > .tab')].filter(e => e.getClientRects().length).map(e => e.querySelector('.tab-name').firstChild.textContent.trim()) }; }""")
                with pg.expect_navigation(timeout=15000):
                    pg.tap("#siteMenu .post-acts > .post-act")
                pg.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
                door[key]["lands"] = pg.evaluate("() => [location.pathname, document.title, !!document.querySelector('[data-site-menu]')]")
                close_ctx(ctx, pg)
            check("the ☰'s first row is How it works, with its mark, as tall as the rows under it (56px), painted, to the"
                  " site's own page; signed in above Settings, a visitor above Sign in; a phone's bar keeps its four places;"
                  " the page it opens has no ☰ of its own",
                  door["signed in"]["rows"][:2] == ["How it works", "Settings"] and door["a visitor"]["rows"][:2] == ["How it works", "Sign in"]
                  and all(d["href"] == "/social/how" and d["h"] == 56 and set(d["hs"]) == {56} and d["mark"] and d["hit"]
                          and d["lands"] == ["/social/how", "How it works · Blooby", False] for d in door.values())
                  and door["signed in"]["bar"] == ["Home", "Gallery", "Make", "You"] and door["a visitor"]["bar"] == ["Home", "Gallery", "Make", "Sign in"],
                  json.dumps(door))
            RAIL = """() => { const tabs = [...document.querySelectorAll('nav.nav > .tab')].filter(e => e.getClientRects().length);
              const name = e => e.querySelector('.tab-name').firstChild.textContent.trim();
              const how = document.querySelector('nav.nav .tab-how'), r = how.getBoundingClientRect(), next = how.nextElementSibling.getBoundingClientRect();
              const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { tabs: tabs.map(name), h: Math.round(r.height), href: how.getAttribute('href'), gap: Math.round(next.top - r.bottom), hit: !!at && how.contains(at),
                       here: how.getAttribute('aria-current'), filled: !!how.querySelector('svg path[fill="currentColor"]'),
                       line: [...how.querySelectorAll('.pen-line')].some(l => l.getBoundingClientRect().width > 10),
                       foot: Math.round(innerHeight - document.querySelector('nav.nav > .tab:last-child').getBoundingClientRect().bottom) }; }"""
            rail = {}
            for key, who in (("signed in", mira), ("a visitor", None)):
                ctx, pg = browser_as(b, who, screen="desk")
                go(pg, "/social/")
                rail[key] = pg.evaluate(RAIL)
                # By its tab where the tab is there to press; a rail without
                # one fails its own row above, and the page is gone to anyway.
                if rail[key]["hit"]:
                    with pg.expect_navigation(timeout=15000):
                        pg.click("nav.nav .tab-how")
                    pg.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
                else:
                    go(pg, "/social/how")
                rail[key + ", on its page"] = pg.evaluate(RAIL)
                rail[key + ", on its page"]["at"] = pg.evaluate("() => location.pathname")
                close_ctx(ctx, pg)
            check("on a desk the rail has How it works above Settings (above Sign in for a visitor), a 52px row painted and"
                  " to the page, 8px over the next as Settings is over You, the rail's foot where it was; not lit on Home",
                  rail["signed in"]["tabs"][-3:-1] == ["How it works", "Settings"] and rail["a visitor"]["tabs"][-2:] == ["How it works", "Sign in"]
                  and all(rail[k]["h"] == 52 and rail[k]["href"] == "/social/how" and rail[k]["gap"] == 8 and rail[k]["hit"]
                          and rail[k]["here"] is None and not rail[k]["filled"] and not rail[k]["line"] and rail[k]["foot"] == 20
                          for k in ("signed in", "a visitor")),
                  json.dumps({k: rail[k] for k in ("signed in", "a visitor")}))
            check("...and on its own page its place is lit, as Home's is on Home: marked the page, its mark filled, the pen's"
                  " line under its name",
                  all(rail[k]["at"] == "/social/how" and rail[k]["here"] == "page" and rail[k]["filled"] and rail[k]["line"]
                      for k in ("signed in, on its page", "a visitor, on its page")),
                  json.dumps({k: rail[k] for k in rail if "on its page" in k}))

            # ---- THE PAGE AND ITS EXAMPLES ---------------------------------------
            PAGE = """() => { const h = document.querySelector('.how'), pics = [...document.querySelectorAll('.how-pic')];
              const players = window.SkriblInline ? SkriblInline.players() : [];
              const probe = document.createElement('i'); probe.style.cssText = 'position:fixed;left:-99px;top:0;width:1px;height:1px;background:var(--draw-wait)';
              document.body.appendChild(probe); const wait = getComputedStyle(probe).backgroundColor; probe.remove();
              return { h1: (document.querySelector('h1') || {}).textContent, h1s: document.querySelectorAll('h1').length, sub: (document.querySelector('.page-sub') || {}).textContent, wait,
                       parts: [...h.querySelectorAll('h2')].map(e => e.textContent), over: document.documentElement.scrollWidth - innerWidth,
                       ex: pics.map(p => { const b = p.querySelector('.skribl-inline'), r = p.getBoundingClientRect(), pl = b.querySelector('.skribl-inline-play'), d = b.querySelector('.skribl-inline-dur');
                         const cv = b.querySelector('canvas'); let ink = 0;
                         if (cv && cv.width) { try { const dd = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, p0 = [dd[0], dd[1], dd[2]];
                           for (let i = 0; i < dd.length; i += 16) if (Math.abs(dd[i] - p0[0]) + Math.abs(dd[i + 1] - p0[1]) + Math.abs(dd[i + 2] - p0[2]) > 60) ink++; } catch (e) { ink = -1; } }
                         return { in: p.classList.contains('is-in'), player: b.classList.contains('skribl-inline'), w: Math.round(r.width * 10) / 10, ratio: Math.round(r.width / r.height * 1000) / 1000,
                                  says: pl ? pl.textContent.trim() : null, playing: b.classList.contains('is-playing'), ink,
                                  // its box's ground: what the box holds as --plate-ground, what it wears, what its player's box wears, what the player says it paints on
                                  ground: [p.style.getPropertyValue('--plate-ground'), getComputedStyle(p).backgroundColor, getComputedStyle(b).backgroundColor,
                                           b._skriblInline && b._skriblInline.ground ? b._skriblInline.ground() : null],
                                  chip: !!d && d.getClientRects().length > 0, cap: [...p.parentElement.querySelectorAll('.how-cap b, .how-cap span')].map(e => e.textContent) }; }),
                       players: players.length, strip: Math.round(document.querySelector('.how-strip').getBoundingClientRect().height * 10) / 10,
                       say: !document.querySelector('[data-how-say]').hidden }; }"""
            FILES = re.compile(r".*/(cat|drawback|flip-bounce)\.json.*")

            # The three files held at the door until the page has been read
            # without them (held, never slept on: a sleep here would hold the
            # reading too).
            held = []
            ctx, pg = browser_as(b, mira)
            ctx.route(FILES, lambda route: held.append(route))
            pg.goto(BASE + "/social/how")
            pg.wait_for_function("() => !!document.querySelector('.how-pic .skribl-inline') && document.readyState === 'complete'", timeout=15000)
            pg.wait_for_timeout(600)
            before = pg.evaluate(PAGE)
            before["held"] = len(held)
            for route in held:
                route.continue_()
            pg.wait_for_function("() => document.querySelectorAll('.how-pic.is-in').length === 3", timeout=20000)
            pg.wait_for_timeout(1500)
            after = pg.evaluate(PAGE)
            # A tap on the second: it plays, and the first stops.
            pg.tap("#howEx2")
            pg.wait_for_timeout(900)
            tapped = [e["playing"] for e in pg.evaluate(PAGE)["ex"]]
            close_ctx(ctx, pg)
            check("the page: one heading, \"How it works\", \"Blooby is where people talk in drawings.\", then Watch an example,"
                  " People often ask and The drawing tools; nothing past the screen",
                  after["h1"] == "How it works" and after["h1s"] == 1 and after["sub"] == "Blooby is where people talk in drawings."
                  and after["parts"] == ["Watch an example", "People often ask", "The drawing tools"] and after["over"] <= 0,
                  json.dumps({k: after[k] for k in ("h1", "h1s", "sub", "parts", "over")}))
            caps = [["A drawing", "It draws itself, the way it was made"], ["A draw-back", "Theirs, then yours on top"], ["A Flip", "Pages that move"]]
            check("the examples: three of Skribl's in-post player, 168px wide on a phone and their drawings' 4 to 3 BEFORE the"
                  " drawings come, so nothing moves when they do (the strip as tall before as after); each then a drawing on"
                  " its canvas, with what it is and one line under it; no second time label beside the play button",
                  len(before["ex"]) == 3 and before["held"] == 3 and not any(e["in"] for e in before["ex"]) and before["strip"] == after["strip"]
                  and all(e["player"] and e["w"] == 168 and abs(e["ratio"] - 4 / 3) < 0.01 for e in before["ex"] + after["ex"])
                  and all(e["in"] and e["ink"] > 20 and not e["chip"] for e in after["ex"]) and after["players"] == 3
                  and [e["cap"] for e in after["ex"]] == caps and not after["say"],
                  json.dumps({"before": [(e["in"], e["w"], e["ratio"]) for e in before["ex"]], "strip": [before["strip"], after["strip"]],
                              "after": [(e["in"], e["ink"], e["chip"], e["cap"]) for e in after["ex"]]})[:700])
            # EACH EXAMPLE'S BOX IS ITS DRAWING'S OWN PAPER TO ITS EDGE (A of "The Drawing's Edge", the owner, Nov 21).
            # An example is a file handed to the player as it is, so the page was never told its ground and the box
            # kept the waiting lilac round the picture; the box takes it from the player now (social.js SocialGround).
            rgb = lambda h: "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))  # noqa: E731
            check("each example's box is its drawing's own paper to its edge: while its file is held, the box and its"
                  " player's wear the waiting colour and hold no ground; once the drawing has come, the box holds the ground"
                  " its player says it paints (the one colour a page may use) and both wear it, not the waiting colour",
                  len(before["ex"]) == 3 and all(e["ground"][0] == "" and e["ground"][1] == e["ground"][2] == before["wait"] for e in before["ex"])
                  and all(re.fullmatch(r"#[0-9a-f]{6}", e["ground"][0] or "") and e["ground"][0] == e["ground"][3]
                          and e["ground"][1] == e["ground"][2] == rgb(e["ground"][0]) and e["ground"][1] != after["wait"] for e in after["ex"]),
                  json.dumps({"held": [e["ground"] for e in before["ex"]], "come": [e["ground"] for e in after["ex"]], "waiting": after["wait"]}))
            want_says = [f"{hers_s} sec", f"{hers_s + his_s} sec", f"{len(flip_f['frames'])} pages"]
            check(f"each play button says what its file says: the cat's own time ({want_says[0]}), the draw-back's two hands"
                  f" together ({hers_s} and {his_s}: {want_says[1]}, not the joined drawing's nine), the Flip's pages ({want_says[2]})",
                  [(e["says"] or "").replace("drawn in ", "") for e in after["ex"]] == want_says,
                  json.dumps([e["says"] for e in after["ex"]]))
            check("the first draws itself as the page opens and the others wait; a tap on the second plays it and the first"
                  " stops: one at a time",
                  [e["playing"] for e in after["ex"]] == [True, False, False] and tapped == [False, True, False],
                  json.dumps({"as it opens": [e["playing"] for e in after["ex"]], "after a tap on the second": tapped}))
            ctx, pg = browser_as(b, mira, reduced=True)
            go(pg, "/social/how")
            pg.wait_for_function("() => document.querySelectorAll('.how-pic.is-in').length === 3", timeout=20000)
            pg.wait_for_timeout(1800)
            still = pg.evaluate(PAGE)
            close_ctx(ctx, pg)
            check("under Reduce Motion none plays by itself: each rests on its finished drawing",
                  [e["playing"] for e in still["ex"]] == [False, False, False] and all(e["ink"] > 20 for e in still["ex"]),
                  json.dumps([(e["playing"], e["ink"]) for e in still["ex"]]))
            # The files do not come: one line, and Try again.
            ctx, pg = browser_as(b, mira)
            ctx.route(FILES, lambda route: route.abort())
            go(pg, "/social/how", wait=1500)
            failed = pg.evaluate("""() => { const s = document.querySelector('[data-how-say]'), bt = s.querySelector('button'), r = bt.getBoundingClientRect();
              return { shown: !s.hidden, words: s.querySelector('[role=status]').textContent.trim(), button: bt.textContent.trim(), h: Math.round(r.height),
                       in: document.querySelectorAll('.how-pic.is-in').length }; }""")
            ctx.unroute(FILES)
            mended = {}
            if failed["shown"]:
                pg.tap("[data-how-again]")
                try:
                    pg.wait_for_function("() => document.querySelectorAll('.how-pic.is-in').length === 3", timeout=20000)
                except Exception:  # noqa: BLE001 -- they never came: the row's red
                    pass
                pg.wait_for_timeout(400)
                mended = pg.evaluate("() => ({ shown: !document.querySelector('[data-how-say]').hidden, in: document.querySelectorAll('.how-pic.is-in').length })")
            close_ctx(ctx, pg)
            check("when the examples' files do not come, one line says so (\"The examples didn’t load. Check your connection,"
                  " then try again.\") with Try again, 44px; Try again brings them and the line goes",
                  failed == {"shown": True, "words": "The examples didn’t load. Check your connection, then try again.",
                             "button": "Try again", "h": 44, "in": 0} and mended == {"shown": False, "in": 3},
                  json.dumps({"failed": failed, "mended": mended}))

            # ---- PEOPLE OFTEN ASK -------------------------------------------------
            ROWS11 = """() => [...document.querySelectorAll('.how-rows')].map(sec => [...sec.querySelectorAll('.how-row')].map(r => ({
              tag: r.tagName, words: [...r.querySelectorAll('.how-words b, .how-words span')].map(e => e.textContent), href: r.getAttribute('href'),
              go: !!r.querySelector('svg'), h: Math.round(r.getBoundingClientRect().height), make: r.hasAttribute('data-make') })))"""
            ctx, pg = browser_as(b, mira)
            go(pg, "/social/how")
            rows_in = pg.evaluate(ROWS11)
            # The first row, whatever it is: Post a drawing.
            pg.evaluate("() => document.querySelector('.how-rows .how-row').scrollIntoView({ block: 'center' })")
            pg.tap(".how-rows .how-row >> nth=0")
            pg.wait_for_timeout(900)
            made = pg.evaluate("() => ({ open: SocialComposer.isOpen(), at: location.pathname, focus: document.querySelector('#composeSheet .make-sheet').contains(document.activeElement),"
                               " seen: getComputedStyle(document.querySelector('#composeSheet .make-sheet')).visibility })")
            close_ctx(ctx, pg)
            ctx, pg = browser_as(b, None)
            go(pg, "/social/how")
            rows_out = pg.evaluate(ROWS11)
            note = pg.evaluate("() => { const n = document.querySelector('.how-out'), a = n && n.querySelector('a'); return n ? [n.querySelector('span').textContent.trim(),"
                               " a.getAttribute('href'), a.textContent.trim(), Math.round(a.getBoundingClientRect().height)] : null; }")
            close_ctx(ctx, pg)
            ask = [["Post a drawing", "The pencil, then Draw"], ["Answer a drawing with a drawing", "Draw back: the pen under any drawing"],
                   ["Comment with a drawing", "The speech bubble, then Draw"], ["Draw your face", "On your profile"]]
            check("People often ask, signed in: four rows, the question over its answer, each 60px and more with a chevron,"
                  " each going where it is done: Post a drawing opens the composer on this page, focus in it; the"
                  " two about answering go to Home's Everyone; Draw your face to your profile",
                  [r["words"] for r in rows_in[0]] == ask and all(r["h"] >= 60 and r["go"] for r in rows_in[0])
                  and [(r["tag"], r["href"], r["make"]) for r in rows_in[0]] == [("BUTTON", None, True), ("A", "/social/?tab=everyone", False),
                                                                             ("A", "/social/?tab=everyone", False), ("A", "/social/@mira", False)]
                  and made == {"open": True, "at": "/social/how", "focus": True, "seen": "visible"},
                  json.dumps({"rows": rows_in[0], "Post a drawing": made})[:700])
            check("a visitor reads the same four as plain lines, nothing to tap and no chevron, and one line under them says"
                  " why, with Sign in beside it, a 44px button",
                  [r["words"] for r in rows_out[0]] == ask and all(r["tag"] == "DIV" and not r["go"] and r["href"] is None for r in rows_out[0])
                  and note == ["You’ll need an account for these, and Blooby is by invite for now.", "/social/signin", "Sign in", 44],
                  json.dumps({"rows": [(r["tag"], r["go"]) for r in rows_out[0]], "note": note}))
            tools = [["The Pad", "Pens, colour, music and replay speed"], ["Flip", "Pages that move"]]
            check("The drawing tools: the Pad and Flip, each a link to the editor's own address asking for its help, the same"
                  " for a visitor",
                  all([r["words"] for r in rr[1]] == tools and [(r["tag"], r["href"], r["go"]) for r in rr[1]]
                      == [("A", "/skribl-pad?help=1", True), ("A", "/flip?help=1", True)] and all(r["h"] >= 60 for r in rr[1])
                      for rr in (rows_in, rows_out)), json.dumps({"signed in": rows_in[1], "a visitor": rows_out[1]})[:600])

            # ---- THE DRAWING TOOLS, OPENED -----------------------------------------
            def editor11(pg_, path, timeout=30):
                end = time.time() + timeout
                while time.time() < end:
                    fr = next((f for f in pg_.frames if urllib.parse.urlsplit(f.url or "").path == path and "compose=1" in (f.url or "")), None)
                    if fr:
                        try:
                            fr.wait_for_function("() => !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip))", timeout=1000)
                            return fr
                        except Exception:  # noqa: BLE001 -- not up yet
                            pass
                    pg_.wait_for_timeout(200)
                return None
            HOST11 = """(kind) => { const w = document.getElementById('composeSheet'), row = document.querySelector('[data-how-editor="' + kind + '"]');
              const up = [document.getElementById('composePad'), document.getElementById('composeFlip')].find(o => !o.hidden) || null, fr = up && up.querySelector('iframe');
              const mid = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
              return { at: location.pathname, sheet: SocialComposer.isOpen(), sheetSeen: !w.hidden && getComputedStyle(w.querySelector('.make-sheet')).visibility === 'visible',
                       editor: up ? up.id : null, front: !!fr && mid === fr, attached: SocialComposer.attached(),
                       focus: document.activeElement === fr ? 'the editor' : document.activeElement === row ? 'the row' : document.activeElement.tagName }; }"""
            IN11 = """() => ({ at: location.pathname + location.search, help: !document.getElementById('helpDrawer').hidden && document.getElementById('helpDrawer').classList.contains('open'),
              home: !document.getElementById('helpWatch').hidden, add: document.getElementById('postBtn').textContent.replace(/\\s+/g, ' ').trim(),
              mark: (window.__mark = window.__mark || String(Math.random())) })"""
            opened = {}
            ctx, pg = browser_as(b, mira)
            go(pg, "/social/how")
            for kind, path, wrap_id in (("pad", "/skribl-pad", "composePad"), ("flip", "/flip", "composeFlip")):
                got = opened[kind] = {"wrap": wrap_id}
                try:
                    row = f'[data-how-editor="{kind}"]'
                    pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", row)
                    pg.tap(row)
                    fr = editor11(pg, path)
                    fr.wait_for_function("() => !document.getElementById('helpDrawer').hidden && document.getElementById('helpDrawer').classList.contains('open')",
                                         timeout=15000)
                    pg.wait_for_timeout(900)
                    got["up"], got["in"] = pg.evaluate(HOST11, kind), fr.evaluate(IN11)
                    fr.evaluate("() => closeHelpDrawer()")
                    pg.wait_for_timeout(600)
                    fr.click("#composeCloseBtn")
                    pg.wait_for_timeout(1300)
                    got["after"] = pg.evaluate(HOST11, kind)
                    # Asked again: the editor is there already, so it is asked at once.
                    pg.tap(row)
                    fr.wait_for_function("() => !document.getElementById('helpDrawer').hidden && document.getElementById('helpDrawer').classList.contains('open')",
                                         timeout=15000)
                    pg.wait_for_timeout(600)
                    got["again"] = fr.evaluate(IN11)
                    fr.evaluate("() => closeHelpDrawer()")
                    pg.wait_for_timeout(600)
                    fr.click("#composeCloseBtn")
                    pg.wait_for_timeout(1300)
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                    got["stopped"] = str(exc).splitlines()[0][:200]
            close_ctx(ctx, pg)

            def tool_ok(v, at):
                u, i, a, g = v.get("up") or {}, v.get("in") or {}, v.get("after") or {}, v.get("again") or {}
                return bool(u == {"at": "/social/how", "sheet": True, "sheetSeen": False, "editor": v["wrap"], "front": True, "attached": None,
                                  "focus": "the editor"}
                            and i.get("at") == at + "?compose=1" and i.get("help") and i.get("home") and i.get("add", "").startswith("Add")
                            and a == {"at": "/social/how", "sheet": False, "sheetSeen": False, "editor": None, "front": False, "attached": None,
                                      "focus": "the row"}
                            and g.get("help") and g.get("home") and g.get("mark") == i.get("mark") and not v.get("stopped"))
            check("signed in, The Pad and Flip open that editor INSIDE A POST with its own How it works showing, on its home:"
                  " you stay on the page, only the editor is seen (the sheet under it not painted) and it holds focus, its"
                  " button Add; its × is back on the page with nothing attached, focus on the row; asked again, the same"
                  " editor (no reload) shows its help again",
                  tool_ok(opened["pad"], "/skribl-pad") and tool_ok(opened["flip"], "/flip"), json.dumps(opened)[:1200])
            walked = {}
            for kind, path in (("pad", "/skribl-pad"), ("flip", "/flip")):
                ctx, pg = browser_as(b, None)
                go(pg, "/social/how")
                try:
                    pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", f'[data-how-editor="{kind}"]')
                    with pg.expect_navigation(timeout=20000):
                        pg.tap(f'[data-how-editor="{kind}"]')
                    pg.wait_for_function("() => !!document.getElementById('helpDrawer') && !document.getElementById('helpDrawer').hidden"
                                         " && document.getElementById('helpDrawer').classList.contains('open')", timeout=20000)
                    walked[kind] = pg.evaluate("() => ({ at: location.pathname + location.search, home: !document.getElementById('helpWatch').hidden })")
                except Exception as exc:  # noqa: BLE001 -- a step that cannot go on is the row's red
                    walked[kind] = {"stopped": str(exc).splitlines()[0][:160]}
                close_ctx(ctx, pg)
            check("a visitor's rows go to the editor's own page with its How it works showing (their only Pad is that page,"
                  " as Make's two doors are), the asking gone from the address",
                  walked == {"pad": {"at": "/skribl-pad", "home": True}, "flip": {"at": "/flip", "home": True}}, json.dumps(walked))

            # ---- EVERY WORD, EVERY ROW ---------------------------------------------
            words = {}
            for who, tag in ((mira, "signed in"), (None, "a visitor")):
                for screen in ("phone", "desk"):
                    for scheme in ("light", "dark"):
                        ctx, pg = browser_as(b, who, screen=screen, scheme=scheme, reduced=True)
                        go(pg, "/social/how")
                        pg.wait_for_function("() => document.querySelectorAll('.how-pic.is-in').length === 3", timeout=20000)
                        pg.wait_for_timeout(500)
                        top = pg.evaluate(READ, ".how")
                        pg.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                        pg.wait_for_timeout(350)
                        foot = pg.evaluate(READ, ".how")
                        words[f"{tag}, {screen}, {scheme}"] = {"read": top["read"] + foot["read"], "low": top["low"] + foot["low"],
                                                             "small": top["small"] + foot["small"], "lowest": min(top["lowest"], foot["lowest"])}
                        close_ctx(ctx, pg)
            print("      measured:", json.dumps({k: v["lowest"] for k, v in words.items()}))
            check("every word of the page at 4.5:1 and more on its ground (the head, the parts' lines, what each example is,"
                  " the rows' two lines, a visitor's note and its link), every link and button 44px and more: signed in and"
                  " a visitor, a phone and a desk, light and dark",
                  len(words) == 8 and all(v["read"] >= 20 and not v["low"] and not v["small"] for v in words.values()),
                  json.dumps({k: (v["read"], v["lowest"], v["low"][:2], v["small"][:2]) for k, v in words.items()})[:900])
        except Exception as exc:  # noqa: BLE001
            stopped(11, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "no page errors, no console errors and no CSP violations"):
        try:
            check("no page errors, no console errors and no CSP violations, in every browser the suite opened",
                  not ERRS, f"{len(ERRS)}: {ERRS[:4]}")
        except Exception as exc:  # noqa: BLE001
            stopped(10, exc)
    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
