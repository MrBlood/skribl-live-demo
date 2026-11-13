"""Settings on the Skribl site: the theme, one choice for Blooby, Pad and Flip,
and finding Settings (docs/SOCIAL-SITE.md "Built: Settings and the theme"),
through the demo's own server, with Chromium's virtual authenticator for the
site's people. The owner's "Yes to all" on the Settings mock (Nov 13).

  1. THE THEME ROW, FIRST ON SETTINGS: Pad's own words and order (Theme, then
     System, Dark, Light; System's tip, the Pad's and Flip's own), "For
     Blooby, Pad and Flip" under its name; Pad's switch (216 x 52, three 44px
     choices in equal thirds, one weight for every word), its own card (86px,
     Your passkeys 102px further down), the one pill under the choice; named
     Theme, the choice pressed; phone (touch) and desk.
  2. ONE CHOICE, SKRIBL'S OWN, BOTH WAYS: Dark on Settings opens the Pad and
     Flip dark, their switch saying Dark; on a dark device Light in the Pad's
     own menu is light back on the site, its row saying Light, and Flip's
     System is System, the device again; kept under skribl_theme_v1 and
     nowhere else; another tab hears it; a page the back button brings back
     takes it; the site's code names neither the key nor the attribute, and
     Skribl's theme code names nothing of the site's.
  3. SYSTEM FOLLOWS THE DEVICE: nothing stored and System, on a light and a
     dark device, and as the device changes; Dark and Light ignore it; with no
     script at all, nothing stamped, the device.
  4. THE NEXT PAGE, NEVER A FLASH: Dark chosen on a light device (and Light on
     a dark one), every one of the next pages' first frames in the choice; the
     browser's bar (both theme-color metas, whichever the device picks) the
     chosen ground before any deferred script.
  5. THE SWITCH CROSS-FADES, read on every 1/60 s frame on the transitions'
     own clock: the page fades from one theme to the other in the site's
     0.28s, never back, never a flash, the pill gliding there (phone and
     desk); under Reduce Motion the page still fades and the pill is put
     there; a tap made while it fades is kept, and waits for that fade.
  6. FINDING SETTINGS: (a) the gear says Settings, at the top of your own
     profile on a phone and in your row of buttons on a desk; (b) on a desk,
     Settings in the rail above you on every page, lit on Settings and the
     pages it leads to; a phone's bar keeps its four places; not (c).
  7. SIGNED OUT, NOTHING NEW: no switch and no Settings anywhere; the device
     decides; the Pad's own switch (through Make) sets the one choice.
  8. THE DARK RAMP, WRITTEN TWICE, IS ONE: social.css's two copies (dark
     chosen; nothing stamped on a dark device) word for word; every token the
     same in the three ways to dark and in the two ways to light.
  9. WORDS AND MARKS: every word on every changed screen at 4.5:1 on what is
     painted behind it (the pill's chosen word on its tint), every target 44px
     to a finger, no field under 16px; phone (touch) and desk, light and dark.
 10. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

SOCIALSETTINGS_PART=<n>[,<m>] runs those sections only (calibration); a
section makes the people it needs. Every row was shown red by breaking one
part and green as built: DECISIONS.md, "Settings: the theme, one choice for
Blooby, Pad and Flip".
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
import urllib.request
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
PART = os.environ.get("SOCIALSETTINGS_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nSOCIALSETTINGS {n} — {label}")
    return True


def stopped(n, exc):
    """A section whose steps could not go on (a control not there, a page that
    never came) says so as a red row, and the run goes on to the next."""
    check(f"section {n} ran to its end", False, str(exc).splitlines()[0][:200] if str(exc) else repr(exc))


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence Settings works.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)
try:
    from PIL import Image, ImageStat
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (harness/requirements.txt: the cross-fade is read off the screen)")
    raise SystemExit(77)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="socialsettings-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-socialsettings-" + secrets.token_hex(8),
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

# A PHONE IS A TOUCH PHONE (WORKING-AGREEMENTS): is_mobile and has_touch.
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
SCREENS = (("phone", PHONE), ("desk", DESK))
KEY = "skribl_theme_v1"
GROUND = {"light": "#fbfcfd", "dark": "#0b0d12"}            # skribl.core.THEME_GROUND
PAGE_RGB = {"light": "rgb(251, 252, 253)", "dark": "rgb(11, 13, 18)"}
ERRS = []
WATCH = ("document.addEventListener('securitypolicyviolation', e => "
         "(window.__csp = window.__csp || []).push(e.violatedDirective + ' ' + e.blockedURI));")
_addr = [0]


def address():
    _addr[0] += 1
    return f"10.{160 + _addr[0] // 250}.{_addr[0] % 250}.9"


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


def stored(theme):
    """An init script that keeps `theme` as the choice before the page's own
    scripts run, once per tab (a later choice in that tab is the page's)."""
    if theme is None:
        return "try { if (!sessionStorage.getItem('__kept')) { localStorage.removeItem('%s'); sessionStorage.setItem('__kept', '1'); } } catch (e) {}" % KEY
    return ("try { if (!sessionStorage.getItem('__kept')) { localStorage.setItem('%s', %s); sessionStorage.setItem('__kept', '1'); } }"
            " catch (e) {}" % (KEY, json.dumps(theme)))


class Person:
    """One browser with its own passkey, from an address of its own."""

    def __init__(self, b, screen="phone", scheme="light"):
        self.xff = address()
        self.ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": self.xff},
                                 **(PHONE if screen == "phone" else DESK))
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


def browser_as(b, who, screen="phone", scheme="light", reduced=False, theme="nothing", init=None, js=True):
    """A browser for `who` (or nobody): the device's own appearance (`scheme`),
    and the choice kept before the first page (`theme`: None for nothing
    stored, "nothing" to leave storage as it is, or system, dark, light)."""
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        java_script_enabled=js, **(PHONE if screen == "phone" else DESK), **kw)
    ctx.add_init_script(WATCH)
    if theme != "nothing":
        ctx.add_init_script(stored(theme))
    for s in ([init] if isinstance(init, str) else (init or [])):
        ctx.add_init_script(s)
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


def member(b, handle, name):
    """Somebody who joined through an invite (the first through the first
    invite code, which makes them the site's admin), signed in, in a browser
    of their own."""
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


def someone(b, handle, name):
    return _people.get(handle) or member(b, handle, name)


def ready(pg):
    """A page of the site and its deferred scripts (all have run once it is complete)."""
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SocialSheet && !!window.SkriblTheme",
                         timeout=15000)


def go(pg, path, wait=300):
    r = pg.goto(BASE + path)
    ready(pg)
    pg.wait_for_timeout(wait)
    return r.status if r else None


def editor(pg, path=None, wait=600):
    """The Pad or Flip on its own page (opened at `path`, or the one a door
    just opened), its scripts run and its tips put away."""
    if path:
        pg.goto(BASE + path)
    pg.wait_for_function("() => document.readyState === 'complete' && !!window.SkriblTheme && !!document.querySelector('#themeSeg')",
                         timeout=30000)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => { if (window.SkriblHints) SkriblHints.hide(); }")


def press(pg, sel):
    """A finger on a phone (a touch phone taps), a click on a desk."""
    loc = pg.locator(sel).first
    if pg.evaluate("() => matchMedia('(pointer: coarse)').matches"):
        loc.tap(timeout=5000)
    else:
        loc.click(timeout=5000)


def editor_choose(pg, choice, menu):
    """A choice in the editor's own menu, as a person makes it: the menu, its
    Settings, the switch."""
    press(pg, menu)
    pg.wait_for_timeout(500)
    press(pg, "#menuSettingsItem")
    pg.wait_for_timeout(500)
    press(pg, f"#themeSeg [data-theme={choice}]")
    pg.wait_for_timeout(400)


# ---- what the page shows, read in the page ---------------------------------------
# The Theme row: where it is, its words, its switch's boxes, paint and state.
ROW = r"""() => { const sw = document.querySelector('[data-theme-switch]'); if (!sw || !sw.getClientRects().length) return null;
  const panel = sw.closest('section.panel'), panels = [...document.querySelectorAll('.acct > section.panel')];
  const q = e => { const r = e.getBoundingClientRect(); return [Math.round(r.left * 100) / 100, Math.round(r.top * 100) / 100,
                                                                Math.round(r.width * 100) / 100, Math.round(r.height * 100) / 100]; };
  const pill = sw.querySelector('.theme-pill'), on = sw.querySelector('button[aria-pressed="true"]');
  const title = document.getElementById(sw.getAttribute('aria-labelledby') || '');
  return { first: panels[0] === panel, index: panels.indexOf(panel), card: q(panel), next: panels[1] ? q(panels[1]) : null,
    title: panel.querySelector('h2') ? panel.querySelector('h2').textContent.trim() : null,
    line: panel.querySelector('.panel-sub') ? panel.querySelector('.panel-sub').textContent.trim() : null,
    role: sw.getAttribute('role'), name: title ? title.textContent.trim() : null, box: q(sw),
    track: { bg: getComputedStyle(sw).backgroundColor, line: getComputedStyle(sw).borderTopColor },
    options: [...sw.querySelectorAll('button')].map(b => { const cs = getComputedStyle(b), r = b.getBoundingClientRect();
      const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return { words: b.textContent.trim(), choice: b.getAttribute('data-choice'), pressed: b.getAttribute('aria-pressed'),
               tip: b.getAttribute('title'), box: q(b), size: cs.fontSize, weight: cs.fontWeight, color: cs.color,
               hit: !!at && (at === b || b.contains(at)) }; }),
    pressed: on ? on.textContent.trim() : null, placed: sw.hasAttribute('data-pill'), pill: q(pill),
    tint: getComputedStyle(pill).backgroundColor, tintOp: +getComputedStyle(pill).opacity,
    under: !!on && Math.abs(pill.getBoundingClientRect().left - on.getBoundingClientRect().left) < 0.6
           && Math.abs(pill.getBoundingClientRect().width - on.getBoundingClientRect().width) < 0.6 }; }"""

# The Theme row on each of the page's first frames, from the document's start
# (an init script): whether its pill is placed, where it is and how strong, and
# which choice is pressed.
ROW_FRAMES = r"""(() => { window.__rowf = []; let n = 0;
  const look = () => { const sw = document.querySelector('[data-theme-switch]');
    if (sw) { const pill = sw.querySelector('.theme-pill'), on = sw.querySelector('button[aria-pressed="true"]');
      window.__rowf.push({ n: n, placed: sw.hasAttribute('data-pill'),
        x: Math.round((pill.getBoundingClientRect().left - sw.getBoundingClientRect().left) * 100) / 100,
        op: +getComputedStyle(pill).opacity, pressed: on ? on.textContent.trim() : null }); }
    else window.__rowf.push({ n: n, none: true });
    if (++n < 40) requestAnimationFrame(look); };
  requestAnimationFrame(look); })();"""

# The page's theme as it stands: the stamp, the ground, what is kept, and the
# browser's bar (each theme-color meta, and the one the device picks).
STATE = r"""() => { const ms = [...document.querySelectorAll('meta[name="theme-color"]')];
  const used = ms.find(m => !m.media || matchMedia(m.media).matches);
  let kept = null; try { kept = localStorage.getItem('skribl_theme_v1'); } catch (e) { kept = 'unreadable'; }
  return { stamp: document.documentElement.getAttribute('data-theme'), page: getComputedStyle(document.body).backgroundColor,
           token: getComputedStyle(document.documentElement).getPropertyValue('--page').trim(), kept,
           mode: window.SkriblTheme ? SkriblTheme.mode() : null, metas: ms.map(m => m.content), bar: used ? used.content : null }; }"""

# The editor's own switch: what it shows pressed, and what Skribl holds.
EDITOR = r"""() => ({ mode: window.SkriblTheme ? SkriblTheme.mode() : null, stamp: document.documentElement.getAttribute('data-theme'),
  on: [...document.querySelectorAll('#themeSeg button.on')].map(b => b.dataset.theme),
  ground: getComputedStyle(document.body).backgroundColor })"""

# A tap during a fade is read through the transitions the page starts: each
# one's start and end on the page's clock (an init script, the page's own
# document.startViewTransition wrapped as it is called).
VT_LOG = r"""(() => { const o = Document.prototype.startViewTransition; if (!o) return;
  window.__vts = [];
  Document.prototype.startViewTransition = function (cb) { const vt = o.call(this, cb);
    const rec = { t0: performance.now(), done: null }; window.__vts.push(rec); window.__vt = vt;
    vt.finished.then(() => { rec.done = performance.now(); }, () => { rec.done = performance.now(); });
    return vt; }; })();"""

# What each of a page's first frames paints, read just before it paints, from
# the document's start (an init script): the page's ground and the stamp.
FIRST_FRAMES = r"""(() => { window.__first = []; let n = 0;
  const look = () => { const r = document.documentElement, b = document.body;
    window.__first.push({ n: n, token: r ? getComputedStyle(r).getPropertyValue('--page').trim() : '',
      body: b ? getComputedStyle(b).backgroundColor : null, stamp: r ? r.getAttribute('data-theme') : null });
    if (++n < 40) requestAnimationFrame(look); };
  requestAnimationFrame(look); })();"""

# The browser's bar the moment <body> appears: the head is whole and no
# deferred script has run (verify_identity's reading).
BAR_AT_BODY = r"""(() => { const mo = new MutationObserver(() => { if (!document.body) return;
  const ms = [...document.querySelectorAll('meta[name="theme-color"]')], used = ms.find(m => !m.media || matchMedia(m.media).matches);
  window.__barAtBody = { metas: ms.map(m => m.content), bar: used ? used.content : null, stamp: document.documentElement.getAttribute('data-theme') };
  mo.disconnect(); }); mo.observe(document, { childList: true, subtree: true }); })();"""

# Every word painted in `sel` (the page's roots by default) against what is
# painted behind it, every target and every text field (the site suites'
# census; a pill's option counts by its 44px band, as theirs do). The Theme
# switch's chosen word is read on its pill by THEME_INK.
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
    let op = 1; for (let n = e; n && n !== document.documentElement; n = n.parentElement) op *= +getComputedStyle(n).opacity;
    if (op < 0.01) return;
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
    if (e.matches('input[type=radio], input[type=hidden]')) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    // Home's pill (Following | Everyone): each option is 36px to see and 44px
    // to a finger, its band reaching past it (the site's censuses' rule).
    if (e.matches('.fo-seg > button')) { const mid = r.left + r.width / 2, hit = d => { const x = document.elementFromPoint(mid, r.top + r.height / 2 + d);
                                           return !!x && (x === e || e.contains(x)); };
                                         if (r.width >= 44 && hit(0) && hit(-21) && hit(21)) return; }
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

# The switch's chosen word on its pill (a sibling under it, which the census's
# ground cannot see, so it is laid over the track here), the other two on the
# track, and the track's own edge on the card. A colour in a form this cannot
# read is a red reading that says so, never a guess.
THEME_INK = r"""() => { const sw = document.querySelector('[data-theme-switch]'); if (!sw || !sw.getClientRects().length) return null;
  const KNOWN = /^(rgba?\(|color\(srgb )/;
  const rgba = s => { if (!KNOWN.test(s)) return null; const m = (s.match(/[\d.]+/g) || []).map(Number), k = /^color\(srgb/.test(s) ? 255 : 1;
    return m.length >= 3 ? [m[0] * k, m[1] * k, m[2] * k, m.length > 3 ? m[3] : 1] : null; };
  const lum = c => { const v = c.slice(0, 3).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                     return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const over = (c, g) => [0, 1, 2].map(k => c[k] * c[3] + g[k] * (1 - c[3]));
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) * 100) / 100; };
  let g = [255, 255, 255]; const layers = [];
  for (let n = sw; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor); if (b && b[3] > 0) { layers.push(b); if (b[3] >= 1) break; } }
  if (layers.some(l => !l)) return { unread: true };
  for (let i = layers.length - 1; i >= 0; i--) g = over(layers[i], g);
  let card = [255, 255, 255]; const under = [];
  for (let n = sw.parentElement; n; n = n.parentElement) { const b = rgba(getComputedStyle(n).backgroundColor); if (b && b[3] > 0) { under.push(b); if (b[3] >= 1) break; } }
  for (let i = under.length - 1; i >= 0; i--) card = over(under[i], card);
  const tint = rgba(getComputedStyle(sw.querySelector('.theme-pill')).backgroundColor), on = sw.querySelector('button[aria-pressed="true"]');
  const line = rgba(getComputedStyle(sw).borderTopColor);
  if (!tint || !on || !line) return { unread: true };
  const t = over(tint, g);
  return { on: ratio(over(rgba(getComputedStyle(on).color), t), t),
           off: [...sw.querySelectorAll('button[aria-pressed="false"]')].map(b => ratio(over(rgba(getComputedStyle(b).color), g), g)),
           edge: ratio(over(line, card), card) }; }"""

# A desk's rail (or a phone's bar): the places shown, in order, each with its
# box, whether it is lit, its name's weight and the pen's line under it.
RAIL = r"""() => [...document.querySelectorAll('nav.nav > a, nav.nav > button')].filter(e => e.getClientRects().length).map(e => {
  const r = e.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const name = e.querySelector('.tab-name'), line = name ? name.querySelector('.pen-line') : null;
  const lr = line ? line.getBoundingClientRect() : null;
  let hits = 0;
  if (lr && lr.width && lr.height) for (let i = 1; i < 10; i++) for (let j = 1; j < 10; j++) {
    const x = document.elementFromPoint(lr.left + lr.width * i / 10, lr.top + lr.height * j / 10);
    if (x && (x === line || line.contains(x))) { hits++; break; } }
  const linePainted = hits >= 5;
  return { place: e.classList.contains('brand') ? 'brand' : e.classList.contains('tab-settings') ? 'Settings'
                : e.classList.contains('tab-you') ? 'You' : (name || e).textContent.trim(),
           href: e.getAttribute('href'), current: e.getAttribute('aria-current'), w: Math.round(r.width * 100) / 100,
           h: Math.round(r.height * 100) / 100, top: r.top, bottom: r.bottom, hit: !!at && (at === e || e.contains(at)),
           gear: !!e.querySelector('.tab-ic svg'), weight: name ? getComputedStyle(name).fontWeight : null,
           color: getComputedStyle(e).color, line: linePainted }; })"""

# Your own profile's way to Settings: the phone's top and a desk's row.
GEAR = r"""() => { const at = (e) => { const r = e.getBoundingClientRect(); const x = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!x && (x === e || e.contains(x)); };
  const box = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return { words: e.textContent.trim(), href: e.getAttribute('href'), gear: !!e.querySelector('svg.ic'), x: Math.round(r.left * 100) / 100,
             right: Math.round((innerWidth - r.right) * 100) / 100, y: r.top, w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
             hit: at(e), bg: cs.backgroundColor, line: cs.borderTopColor, ink: cs.color, weight: cs.fontWeight, size: cs.fontSize,
             label: e.getAttribute('aria-label') }; };
  const top = [...document.querySelectorAll('header.top a[href$="/social/you"]')].filter(e => e.getClientRects().length);
  const row = [...document.querySelectorAll('.prof-acts > *')].filter(e => e.getClientRects().length);
  const inMain = [...document.querySelectorAll('main a[href$="/social/you"]')].filter(e => e.getClientRects().length);
  const title = document.querySelector('header.top .top-title'), face = document.querySelector('.prof-face');
  return { top: top.map(box), row: row.map(e => Object.assign(box(e), { what: e.matches('[data-share]') ? 'share'
             : e.matches('[href$="/you/edit"]') ? 'edit' : e.matches('[data-face-sheet]') ? 'face'
             : e.matches('a[href$="/social/you"]') ? 'settings' : e.matches('.fo-btn') ? 'follow' : e.matches('[data-person-menu]') ? 'more' : '?' })),
           inMain: inMain.length, title: title ? title.getBoundingClientRect().right : null,
           faceTop: face ? Math.round(face.getBoundingClientRect().top * 100) / 100 : null }; }"""


def colour(css):
    """A colour as Chrome writes it (rgb(), rgba(), or color(srgb ...) in 0 to 1): [r, g, b, a], or None."""
    m = [float(v) for v in re.findall(r"[\d.]+", css or "")]
    if not m or not (css.startswith("rgb") or css.startswith("color(srgb")):
        return None
    k = 255 if css.startswith("color(srgb") else 1
    return [m[0] * k, m[1] * k, m[2] * k, m[3] if len(m) > 3 else 1.0]


def same_colour(a, b, tol=1.5):
    ca, cb = colour(a), colour(b)
    return bool(ca and cb) and all(abs(x - y) <= tol for x, y in zip(ca[:3], cb[:3])) and abs(ca[3] - cb[3]) <= 0.01


def bright(png):
    """The mean brightness of a picture of the screen (0 to 255)."""
    return ImageStat.Stat(Image.open(io.BytesIO(png)).convert("L")).mean[0]


# THE SWITCH, READ ON THE TRANSITIONS' OWN CLOCK (the mock's reading, and the
# replay's habit, verify_glide): every animation on the page is paused and set
# to each 1/60 s frame from its own start, and the page's brightness is read
# off the screen there, away from the switch, with the pill's place. A kind
# switch: the change spread over eight frames or more, none carrying more
# than 35% of it, never back the other way, and never brighter than where it
# started or darker than where it ends (a flash). The pill glides the same
# way (over eight frames or more, none more than 30% of its way), or under
# Reduce Motion is put there (in one).
STEP = 1000 / 60
FRAMES = 22


def judge_fade(vals):
    whole = vals[-1] - vals[0]
    steps = [b - a for a, b in zip(vals, vals[1:])]
    moving = [s for s in steps if abs(s) > 0.5]
    big = max((abs(s) for s in steps), default=0)
    sign = 1 if whole >= 0 else -1
    back = any(s * sign < -0.5 for s in steps)
    lo, hi = min(vals[0], vals[-1]), max(vals[0], vals[-1])
    flash = any(v > hi + 2 or v < lo - 2 for v in vals)
    share = round(big / abs(whole), 3) if whole else 1.0
    return {"from": round(vals[0], 1), "to": round(vals[-1], 1), "frames": len(moving), "biggest": share, "back": back,
            "flash": flash, "ok": abs(whole) > 30 and len(moving) >= 8 and share <= 0.35 and not back and not flash}


def judge_glide(xs, reduced=False):
    way = xs[-1] - xs[0]
    steps = [abs(b - a) for a, b in zip(xs, xs[1:])]
    moving = [s for s in steps if s > 0.3]
    share = round(max(steps, default=0) / abs(way), 3) if way else 1.0
    ok = abs(way) > 40 and (len(moving) <= 1 if reduced else (len(moving) >= 8 and share <= 0.30))
    return {"way": round(way, 2), "frames": len(moving), "biggest": share, "ok": ok}


def read_switch(pg, choice, clip):
    """Tap `choice` on the Theme switch and read every 1/60 s frame of what
    follows, on the transitions' own clock: the page's brightness in `clip`
    and the pill's left edge. Frame 0 is the page before the tap."""
    before = bright(pg.screenshot(clip=clip))
    x0 = pg.evaluate("() => document.querySelector('.theme-pill').getBoundingClientRect().left")
    pg.evaluate("() => { window.__vt = null; }")
    press(pg, f"[data-theme-switch] button[data-choice={choice}]")
    try:
        pg.evaluate("() => window.__vt ? window.__vt.ready.then(() => true, () => false) : null")
    except Exception:  # noqa: BLE001
        pass
    n = pg.evaluate("() => { window.__a = document.getAnimations(); window.__a.forEach(a => a.pause()); return window.__a.length; }")
    vals, xs, lengths = [before], [x0], pg.evaluate(
        "() => window.__a.filter(a => a.effect && /view-transition-(old|new)\\(root\\)/.test(a.effect.pseudoElement || ''))"
        ".map(a => a.effect.getTiming().duration)")
    for i in range(FRAMES):
        pg.evaluate("(t) => window.__a.forEach(a => { a.currentTime = t; })", i * STEP)
        vals.append(bright(pg.screenshot(clip=clip)))
        xs.append(pg.evaluate("() => document.querySelector('.theme-pill').getBoundingClientRect().left"))
    pg.evaluate("() => window.__a.forEach(a => { try { a.finish(); } catch (e) {} })")
    pg.wait_for_timeout(400)
    return {"page": vals, "pill": xs, "animations": n, "lengths": lengths, "vt": pg.evaluate("() => !!window.__vt")}


def fade_clip(pg, screen):
    """Where the page's change is read: the page below the Theme card, away
    from the sliding pill, and right of a desk's rail."""
    top = pg.evaluate("() => document.querySelector('.theme-panel').getBoundingClientRect().bottom") + 10
    return {"x": 0, "y": top, "width": 402, "height": 300} if screen == "phone" else \
           {"x": 260, "y": top, "width": 1000, "height": 300}


CSS = (ROOT / "social" / "static" / "social.css").read_text(encoding="utf-8")


def declarations(body):
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return {k.strip(): " ".join(v.split()) for k, v in re.findall(r"([-\w]+)\s*:\s*([^;]+);", body)}


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "the Theme row, first on Settings: Pad's words, order and switch; its own card; the one pill"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            pad = {}
            for path in ("/skribl-pad", "/flip"):
                q = b.new_page()
                q.goto(BASE + path)
                q.wait_for_function("() => !!document.querySelector('#themeSeg button')", timeout=30000)
                # The editors' styled tooltips move a title into data-tip as they start (lib/tooltip.js).
                pad[path] = q.evaluate("() => [...document.querySelectorAll('#themeSeg button')].map(b => [b.textContent.trim(), b.dataset.theme,"
                                       " b.getAttribute('data-tip') || b.getAttribute('title')])")
                q.close()
            rows = {}
            for screen, _ in SCREENS:
                ctx, pg = browser_as(b, nico, screen, "light", theme=None)
                go(pg, "/social/you")
                rows[screen] = pg.evaluate(ROW)
                close_ctx(ctx, pg)
            ok_words = all(r and r["first"] and r["title"] == "Theme" and r["line"] == "For Blooby, Pad and Flip"
                           and [o["words"] for o in r["options"]] == ["System", "Dark", "Light"]
                           and [o["choice"] for o in r["options"]] == ["system", "dark", "light"] for r in rows.values())
            pad_words = [[w for w, _, _ in v] for v in pad.values()]
            pad_tip = {v[0][2] for v in pad.values()}
            check("first on Settings, its own card: Theme, \"For Blooby, Pad and Flip\" under it, then System, Dark and"
                  " Light, the Pad's and Flip's own words in their own order",
                  ok_words and pad_words == [["System", "Dark", "Light"]] * 2,
                  f"{json.dumps({k: (v and [v['first'], v['title'], v['line'], [o['words'] for o in v['options']]]) for k, v in rows.items()})};"
                  f" the Pad's and Flip's {pad_words}")
            check("System keeps the Pad's tip, the Pad's and Flip's own words to the letter (\"Follow the device's"
                  " appearance setting\"), and the others carry none, as there",
                  all(r and r["options"][0]["tip"] in pad_tip and len(pad_tip) == 1 and r["options"][0]["tip"]
                      and r["options"][1]["tip"] is None and r["options"][2]["tip"] is None for r in rows.values()),
                  f"the site's {[r and r['options'][0]['tip'] for r in rows.values()]}; the editors' {pad_tip}")
            sizes = []
            for screen, r in rows.items():
                if not r:
                    sizes.append((False, f"{screen}: no row"))
                    continue
                opts = r["options"]
                ws = [o["box"][2] for o in opts]
                ok = (r["box"][2:] == [216, 52] and all(o["box"][3] == 44 for o in opts) and max(ws) - min(ws) < 0.05
                      and min(ws) >= 44 and len({(o["size"], o["weight"]) for o in opts}) == 1 and opts[0]["size"] == "15px"
                      and opts[0]["weight"] == "600" and r["card"][3] == 86 and r["next"]
                      and round(r["next"][1] - (r["card"][1] + r["card"][3]), 2) == 16 and all(o["hit"] for o in opts))
                sizes.append((ok, f"{screen}: switch {r['box'][2:]}, choices {[o['box'][2:] for o in opts]},"
                                  f" {opts[0]['size']} at {[o['weight'] for o in opts]}, card {r['card'][3]}px,"
                                  f" Your passkeys {r['next'] and round(r['next'][1] - r['card'][1], 2)}px below its top,"
                                  f" each landing {[o['hit'] for o in opts]}"))
            check("the switch is Pad's: 216 x 52, three 44px choices in equal thirds, 15px words at one weight (600),"
                  " each landing where it is painted; the card 86px tall, so Your passkeys sits 102px below its top"
                  " (phone and desk)", all(o for o, _ in sizes), "; ".join(w for _, w in sizes))
            check("named Theme (a group labelled by the row's name), with nothing stored System pressed, alone, and"
                  " the one pill under it: the site's tint, the chosen word in the pill's ink, the others in its"
                  " second ink, on a track in the second button's dress",
                  all(r and r["role"] == "group" and r["name"] == "Theme" and r["pressed"] == "System"
                      and [o["pressed"] for o in r["options"]] == ["true", "false", "false"] and r["placed"] and r["under"]
                      and r["tintOp"] > 0.99 and r["pill"][3] == 44 and same_colour(r["tint"], "rgba(124, 92, 255, 0.22)")
                      and same_colour(r["options"][0]["color"], "rgb(63, 39, 168)")
                      and all(same_colour(o["color"], "rgb(63, 71, 86)") for o in r["options"][1:])
                      and same_colour(r["track"]["bg"], "rgb(255, 255, 255)") and same_colour(r["track"]["line"], "rgba(124, 92, 255, 0.34)")
                      for r in rows.values()),
                  json.dumps({k: v and {x: v[x] for x in ("role", "name", "pressed", "placed", "under", "pill", "tint", "track")}
                              | {"inks": [o["color"] for o in v["options"]]} for k, v in rows.items()}))
            # AS THE PAGE STARTS: the choice lives in the browser, so you.js
            # presses it; the pill then fades in where it belongs and never
            # slides in (Dark kept, so a slide would cross the switch).
            starts = []
            for screen, _ in SCREENS:
                ctx, pg = browser_as(b, nico, screen, "light", theme="dark", init=ROW_FRAMES)
                go(pg, "/social/you", wait=900)
                fs = [f for f in pg.evaluate("() => window.__rowf || []") if not f.get("none")]
                placed = [f for f in fs if f["placed"]]
                xs = {f["x"] for f in placed}
                ops = [f["op"] for f in placed]
                starts.append((bool(placed) and len(xs) == 1 and all(b2 >= a2 - 0.001 for a2, b2 in zip(ops, ops[1:])) and ops[-1] > 0.99
                               and all(f["pressed"] == "Dark" for f in placed) and placed[-1]["x"] > 60,
                               f"{screen}: {len(fs)} frames read, placed from frame {placed[0]['n'] if placed else None} (the first read"
                               f" {fs[0]['n'] if fs else None}), at {sorted(xs)}, its strength {[round(o, 2) for o in ops[:8]]}…"))
                close_ctx(ctx, pg)
            check("as Settings starts, the kept choice is pressed and its pill fades in where it belongs, never sliding"
                  " in (Dark kept; phone and desk)", all(o for o, _ in starts), "; ".join(w for _, w in starts))
        except Exception as exc:  # noqa: BLE001
            stopped(1, exc)

    # ------------------------------------------------------------------ 2
    if part(2, "one choice, Skribl's own, both ways: Settings sets the Pad and Flip, their switch sets the site"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            ctx, pg = browser_as(b, nico, "phone", "light", theme=None)
            go(pg, "/social/you")
            keys0 = pg.evaluate("() => Object.keys(localStorage)")
            press(pg, "[data-theme-switch] button[data-choice=dark]")
            pg.wait_for_timeout(700)
            site_dark = pg.evaluate(STATE)
            keys1 = pg.evaluate("() => Object.keys(localStorage)")
            # Through Make's doors, as a person goes: the Pad, then Flip.
            press(pg, ".nav .tab-make")
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                press(pg, "#makeSheet a.make-door >> nth=0")
            editor(pg)
            pad_dark = pg.evaluate(EDITOR)
            pg.go_back()
            ready(pg)
            pg.wait_for_timeout(300)
            press(pg, ".nav .tab-make")
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                press(pg, "#makeSheet a.make-door >> nth=1")
            editor(pg)
            flip_dark = pg.evaluate(EDITOR)
            check("Dark chosen on Settings is kept as Skribl's own choice (skribl_theme_v1, nothing else added), the"
                  " site turns dark, and the Pad and Flip open dark, their own switch saying Dark",
                  site_dark["kept"] == "dark" and site_dark["stamp"] == "dark" and site_dark["page"] == PAGE_RGB["dark"]
                  and sorted(set(keys1) - set(keys0)) == [KEY]
                  and pad_dark["mode"] == "dark" and pad_dark["stamp"] == "dark" and pad_dark["on"] == ["dark"]
                  and flip_dark["mode"] == "dark" and flip_dark["stamp"] == "dark" and flip_dark["on"] == ["dark"],
                  f"site {site_dark}; added keys {sorted(set(keys1) - set(keys0))}; Pad {pad_dark}; Flip {flip_dark}")
            close_ctx(ctx, pg)
            # The other way, on a DARK device, so the site following the choice
            # and the site following the device read differently: Light in the
            # Pad's own menu, then System in Flip's.
            ctx, pg = browser_as(b, nico, "phone", "dark", theme=None)
            editor(pg, "/skribl-pad")
            editor_choose(pg, "light", "#menuBtn")
            pad_light = pg.evaluate(EDITOR)
            go(pg, "/social/you")
            site_light, row_light = pg.evaluate(STATE), pg.evaluate(ROW)
            go(pg, "/social/")
            home_light = pg.evaluate(STATE)
            editor(pg, "/flip")
            editor_choose(pg, "system", "#moreBtn")
            go(pg, "/social/you")
            site_system, row_system = pg.evaluate(STATE), pg.evaluate(ROW)
            close_ctx(ctx, pg)
            check("on a dark device, Light picked in the Pad's own menu is light back on the site, Settings' row saying"
                  " Light and Home light; System picked in Flip's is System there, and the site follows the device again",
                  pad_light["mode"] == "light" and site_light["stamp"] == "light" and site_light["page"] == PAGE_RGB["light"]
                  and row_light and row_light["pressed"] == "Light" and row_light["under"]
                  and home_light["stamp"] == "light" and home_light["page"] == PAGE_RGB["light"]
                  and site_system["kept"] == "system" and site_system["stamp"] == "dark" and site_system["page"] == PAGE_RGB["dark"]
                  and row_system and row_system["pressed"] == "System",
                  f"Pad {pad_light}; Settings {site_light} row {row_light and row_light['pressed']}; Home {home_light};"
                  f" after Flip's System {site_system} row {row_system and row_system['pressed']}")
            # Another tab: Settings in one, Settings in the other; Dark in the first.
            ctx, pg = browser_as(b, nico, "desk", "light", theme=None)
            go(pg, "/social/you")
            pg2 = ctx.new_page()
            pg2.goto(BASE + "/social/you")
            ready(pg2)
            pg2.wait_for_timeout(300)
            press(pg, "[data-theme-switch] button[data-choice=dark]")
            pg.wait_for_timeout(900)
            other = pg2.evaluate(STATE)
            other_row = pg2.evaluate(ROW)
            # A page the back button brings back whole (the bfcache) missed the
            # storage event: a choice kept behind its back, then the page shown
            # again as a restore shows it (pageshow, persisted).
            pg2.evaluate("() => { localStorage.setItem('skribl_theme_v1', 'light');"
                         " window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })); }")
            pg2.wait_for_timeout(400)
            restored, restored_row = pg2.evaluate(STATE), pg2.evaluate(ROW)
            pg2.close()
            close_ctx(ctx, pg)
            check("another tab hears it: Dark chosen in one tab turns the other dark and moves its switch to Dark;"
                  " a page brought back whole by the back button takes a choice made while it was away",
                  other["stamp"] == "dark" and other["page"] == PAGE_RGB["dark"] and other_row and other_row["pressed"] == "Dark"
                  and other_row["under"] and restored["stamp"] == "light" and restored["page"] == PAGE_RGB["light"]
                  and restored_row and restored_row["pressed"] == "Light" and restored_row["under"],
                  f"the other tab {other}, its switch {other_row and other_row['pressed']}; brought back {restored},"
                  f" its switch {restored_row and restored_row['pressed']}")
            # THE SEAM, read from the source: the site's code names neither the
            # key nor the attribute (it goes through SkriblTheme), and Skribl's
            # theme code names nothing of the site's.
            # Code, not prose: the words a comment says about the key are not a
            # reading of it (a check for absence matches the mechanism).
            def code(f):
                t = f.read_text(encoding="utf-8")
                if f.suffix == ".js":
                    return re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", t, flags=re.S)
                if f.suffix == ".html":
                    return re.sub(r"\{#.*?#\}|<!--.*?-->", "", t, flags=re.S)
                tree = ast.parse(t)
                prose = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
                return "\n".join(n.value for n in ast.walk(tree)
                                 if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in prose)
            site_files = [f for f in sorted((ROOT / "social").rglob("*")) if f.suffix in (".js", ".html", ".py") and f.is_file()]
            site_src = "\n".join(code(f) for f in site_files)
            site_js = "\n".join(code(f) for f in site_files if f.suffix == ".js")
            reach = [w for w in ("skribl_theme_v1",) if w in site_src]
            stamps = re.findall(r"(?:setAttribute|removeAttribute)\(\s*['\"]data-theme['\"]|dataset\.theme\s*=", site_js)
            calls = re.findall(r"\bT\.set\(|SkriblTheme\.set\(", site_js)
            sk = ((ROOT / "skribl" / "static" / "lib" / "theme.js").read_text(encoding="utf-8")
                  + (ROOT / "skribl" / "templates" / "skribl" / "_skribl_theme_boot.html").read_text(encoding="utf-8"))
            sk_code = re.sub(r"/\*.*?\*/|\{#.*?#\}", "", sk, flags=re.S)
            knows = [w for w in ("/social", "data-theme-switch", "theme-switch", "theme-pill", "SocialSheet", "blooby")
                     if w.lower() in sk_code.lower()]
            check("through Skribl's own theme code only: the site's code never names the key nor stamps the attribute,"
                  " and its switch calls SkriblTheme.set(); Skribl's theme code (lib/theme.js, the boot) names nothing"
                  " of the site's",
                  not reach and not stamps and calls and not knows,
                  f"the key named by the site: {reach}; stamps: {stamps}; SkriblTheme.set calls: {len(calls)};"
                  f" the site in Skribl's code: {knows}")
        except Exception as exc:  # noqa: BLE001
            stopped(2, exc)

    # ------------------------------------------------------------------ 3
    if part(3, "System follows the device: nothing stored and System, light and dark, and as it changes; a choice ignores it"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            seen = []
            for scheme in ("light", "dark"):
                for kept in (None, "system"):
                    ctx, pg = browser_as(b, nico, "phone", scheme, theme=kept)
                    go(pg, "/social/you")
                    st, row = pg.evaluate(STATE), pg.evaluate(ROW)
                    seen.append((st["stamp"] == scheme and st["page"] == PAGE_RGB[scheme] and st["bar"] == GROUND[scheme]
                                 and row and row["pressed"] == "System", f"device {scheme}, kept {kept}: {st}, row {row and row['pressed']}"))
                    close_ctx(ctx, pg)
            check("with nothing kept, or System, the site follows the device (light on light, dark on dark), its bar"
                  " the device's ground, and the switch says System",
                  all(o for o, _ in seen), "; ".join(w for _, w in seen))
            moves = []
            for kept, want_light, want_dark in ((None, "light", "dark"), ("dark", "dark", "dark"), ("light", "light", "light")):
                ctx, pg = browser_as(b, nico, "desk", "dark", theme=kept)
                go(pg, "/social/")
                pg.emulate_media(color_scheme="light")
                pg.wait_for_timeout(400)
                a = pg.evaluate(STATE)
                pg.emulate_media(color_scheme="dark")
                pg.wait_for_timeout(400)
                c2 = pg.evaluate(STATE)
                moves.append((a["stamp"] == want_light and a["page"] == PAGE_RGB[want_light]
                              and c2["stamp"] == want_dark and c2["page"] == PAGE_RGB[want_dark],
                              f"kept {kept}: device to light {a['stamp']} {a['page']}, back to dark {c2['stamp']} {c2['page']}"))
                close_ctx(ctx, pg)
            check("a page open on System follows the device as it changes, both ways; Dark and Light ignore it",
                  all(o for o, _ in moves), "; ".join(w for _, w in moves))
            bare = []
            for scheme in ("light", "dark"):
                # With no script nothing kept can be read, so a device is the whole of it.
                ctx, pg = browser_as(b, nico, "phone", scheme, js=False)
                pg.goto(BASE + "/social/explore")
                pg.wait_for_timeout(300)
                st = pg.evaluate("() => [document.documentElement.getAttribute('data-theme'), getComputedStyle(document.body).backgroundColor,"
                                 " [...document.querySelectorAll('meta[name=theme-color]')].find(m => matchMedia(m.media).matches).content]")
                bare.append((st[0] is None and st[1] == PAGE_RGB[scheme] and st[2] == GROUND[scheme], f"device {scheme}: {st}"))
                close_ctx(ctx, pg)
            check("with no script at all, nothing is stamped and the site follows the device, its bar too (\"even"
                  " before any script runs\")", all(o for o, _ in bare), "; ".join(w for _, w in bare))
        except Exception as exc:  # noqa: BLE001
            stopped(3, exc)

    # ------------------------------------------------------------------ 4
    if part(4, "the next page, never a flash: every first frame in the choice; the browser's bar from the first moment"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            mira = someone(b, "mira", "Mira Okafor")
            frames, bars = [], []
            for screen, _ in SCREENS:
                for device, choice in (("light", "dark"), ("dark", "light")):
                    ctx, pg = browser_as(b, nico, screen, device, theme=choice, init=[FIRST_FRAMES, BAR_AT_BODY])
                    for path in ("/social/you", "/social/", "/social/explore", "/social/@nico", "/social/@mira"):
                        go(pg, path, wait=900)
                        log = pg.evaluate("() => window.__first || []")
                        read = [f for f in log if f["token"]]
                        wrong = [f["n"] for f in read if f["token"].lower() != GROUND[choice] or f["stamp"] != choice
                                 or (f["body"] and f["body"] != PAGE_RGB[choice])]
                        frames.append((len(read) >= 20 and read[0]["n"] == 0 and not wrong,
                                       f"{screen}, {choice} on a {device} device, {path}: {len(read)} frames read, the first"
                                       f" {read[0] if read else None}, off {wrong[:5]}"))
                        bar = pg.evaluate("() => window.__barAtBody || null")
                        bars.append((bool(bar) and bar["metas"] == [GROUND[choice]] * 2 and bar["bar"] == GROUND[choice]
                                     and bar["stamp"] == choice, f"{screen} {choice}/{device} {path}: {bar}"))
                    close_ctx(ctx, pg)
            check("Dark chosen on a light device (and Light on a dark one): every one of the next pages' first frames is"
                  " in the choice, from the very first (Settings, Home, Explore, your profile and somebody's; phone and"
                  " desk)", all(o for o, _ in frames), "; ".join(w for o, w in frames if not o)[:1500] or f"{len(frames)} pages")
            check("the browser's bar says the chosen ground before any deferred script has run: both theme-color metas,"
                  " whichever the device picks", all(o for o, _ in bars), "; ".join(w for o, w in bars if not o)[:1500] or f"{len(bars)} pages")
        except Exception as exc:  # noqa: BLE001
            stopped(4, exc)

    # ------------------------------------------------------------------ 5
    if part(5, "the switch cross-fades in the site's 0.28s while the pill slides; Reduce Motion fades, the pill put there"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            reads = {}
            for screen, _ in SCREENS:
                ctx, pg = browser_as(b, nico, screen, "light", theme=None, init=VT_LOG)
                go(pg, "/social/you", wait=600)
                reads[screen] = read_switch(pg, "dark", fade_clip(pg, screen))
                reads[screen]["after"] = pg.evaluate(STATE)
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, nico, "phone", "light", reduced=True, theme=None, init=VT_LOG)
            go(pg, "/social/you", wait=600)
            reads["reduced"] = read_switch(pg, "dark", fade_clip(pg, "phone"))
            reads["reduced"]["after"] = pg.evaluate(STATE)
            close_ctx(ctx, pg)
            fades = {k: judge_fade(v["page"]) for k, v in reads.items()}
            glides = {k: judge_glide(v["pill"], reduced=(k == "reduced")) for k, v in reads.items()}
            for k, v in reads.items():
                print(f"    {k}: page {[round(x, 1) for x in v['page']]}")
                print(f"    {k}: pill {[round(x, 1) for x in v['pill']]}")
            check("tap Dark: the page cross-fades from light to dark, spread over its frames and never back, never a"
                  " flash, and ends dark (phone and desk)",
                  all(fades[k]["ok"] and reads[k]["vt"] and reads[k]["after"]["stamp"] == "dark" for k in ("phone", "desk")),
                  json.dumps({k: fades[k] for k in ("phone", "desk")}))
            check("...in the site's own 0.28 seconds (the fade's two halves, old and new, each 280ms)",
                  all(reads[k]["lengths"] and all(abs(x - 280) < 0.5 for x in reads[k]["lengths"]) for k in reads),
                  json.dumps({k: v["lengths"] for k, v in reads.items()}))
            check("...while the pill slides from System to Dark, over its frames (Pad's 0.26s)",
                  all(glides[k]["ok"] for k in ("phone", "desk")), json.dumps({k: glides[k] for k in ("phone", "desk")}))
            check("under Reduce Motion the page still fades the same way, and the pill is put there",
                  fades["reduced"]["ok"] and glides["reduced"]["ok"] and reads["reduced"]["vt"]
                  and reads["reduced"]["after"]["stamp"] == "dark",
                  f"page {fades['reduced']}; pill {glides['reduced']}")
            # A TAP WHILE IT FADES lands on the page itself (the browser shows a
            # picture of it then): it is kept, and its fade waits for this one.
            kept = []
            for screen, _ in SCREENS:
                ctx, pg = browser_as(b, nico, screen, "light", theme=None, init=VT_LOG)
                go(pg, "/social/you", wait=600)
                light_at = pg.evaluate("() => { const r = document.querySelector('[data-theme-switch] [data-choice=light]').getBoundingClientRect();"
                                       " return [r.left + r.width / 2, r.top + r.height / 2]; }")
                press(pg, "[data-theme-switch] button[data-choice=dark]")
                pg.wait_for_timeout(90)
                if screen == "phone":
                    pg.touchscreen.tap(light_at[0], light_at[1])
                else:
                    pg.mouse.click(light_at[0], light_at[1])
                pg.wait_for_timeout(1300)
                st, row, vts = pg.evaluate(STATE), pg.evaluate(ROW), pg.evaluate("() => window.__vts || []")
                kept.append((st["kept"] == "light" and st["stamp"] == "light" and row and row["pressed"] == "Light"
                             and len(vts) == 2 and vts[0]["done"] is not None and vts[1]["t0"] >= vts[0]["done"] - 1,
                             f"{screen}: kept {st['kept']}, page {st['stamp']}, switch {row and row['pressed']},"
                             f" fades {[{k: round(v, 1) if v else v for k, v in x.items()} for x in vts]}"))
                close_ctx(ctx, pg)
            check("a tap made while the page fades is kept (Light, 90ms after Dark), and its fade begins only once the"
                  " first has ended, so the page never jumps from half way", all(o for o, _ in kept), "; ".join(w for _, w in kept))
        except Exception as exc:  # noqa: BLE001
            stopped(5, exc)

    # ------------------------------------------------------------------ 6
    if part(6, "finding Settings: the gear says Settings; on a desk, Settings in the rail; a phone's bar keeps four; not c"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            mira = someone(b, "mira", "Mira Okafor")
            mine, theirs = {}, {}
            for screen, _ in SCREENS:
                for scheme in ("light", "dark"):
                    ctx, pg = browser_as(b, nico, screen, scheme, theme=None)
                    go(pg, "/social/@nico")
                    mine[(screen, scheme)] = pg.evaluate(GEAR)
                    go(pg, "/social/@mira")
                    theirs[(screen, scheme)] = pg.evaluate(GEAR)
                    close_ctx(ctx, pg)
            BTN2 = {"light": ("rgb(255, 255, 255)", "rgba(124, 92, 255, 0.34)"),
                    "dark": ("rgba(167, 146, 255, 0.1)", "rgba(167, 146, 255, 0.26)")}
            phone_ok = all(len(mine[("phone", s)]["top"]) == 1 and mine[("phone", s)]["top"][0]["words"] == "Settings"
                           and mine[("phone", s)]["top"][0]["gear"] and mine[("phone", s)]["top"][0]["h"] == 44
                           and mine[("phone", s)]["top"][0]["w"] >= 44 and mine[("phone", s)]["top"][0]["hit"]
                           and mine[("phone", s)]["top"][0]["href"] == "/social/you" and mine[("phone", s)]["top"][0]["right"] <= 16.01
                           and same_colour(mine[("phone", s)]["top"][0]["bg"], BTN2[s][0])
                           and same_colour(mine[("phone", s)]["top"][0]["line"], BTN2[s][1])
                           and mine[("phone", s)]["top"][0]["label"] is None
                           and [r["what"] for r in mine[("phone", s)]["row"]] == ["edit", "face", "share"]
                           and mine[("phone", s)]["inMain"] == 0 for s in ("light", "dark"))
            check("(a) on a phone, the top of your own profile says Settings with the gear: the word itself, a 44px"
                  " link to Settings at the top right, in the Share button's dress (the second button's), named by its"
                  " word", phone_ok, json.dumps({s: mine[("phone", s)]["top"] for s in ("light", "dark")}))
            desk_ok = all([r["what"] for r in mine[("desk", s)]["row"]] == ["edit", "face", "share", "settings"]
                          and mine[("desk", s)]["row"][3]["words"] == "Settings" and mine[("desk", s)]["row"][3]["gear"]
                          and mine[("desk", s)]["row"][3]["h"] == 44 and mine[("desk", s)]["row"][3]["hit"]
                          and mine[("desk", s)]["row"][3]["href"] == "/social/you" and mine[("desk", s)]["row"][3]["label"] is None
                          and round(mine[("desk", s)]["row"][3]["x"] - (mine[("desk", s)]["row"][2]["x"] + mine[("desk", s)]["row"][2]["w"]), 2) == 8
                          and same_colour(mine[("desk", s)]["row"][3]["bg"], BTN2[s][0])
                          and not mine[("desk", s)]["top"] and mine[("desk", s)]["inMain"] == 1 for s in ("light", "dark"))
            check("(a) on a desk, the boxed gear in your row of buttons says Settings: Edit profile, your face, Share,"
                  " then Settings with the gear, 44px, 8px after Share, in the buttons' dress", desk_ok,
                  json.dumps({s: mine[("desk", s)]["row"] for s in ("light", "dark")}))
            moved = [(k, mine[k]["faceTop"], theirs[k]["faceTop"]) for k in mine if mine[k]["faceTop"] != theirs[k]["faceTop"]]
            check("nothing moves for it: your face sits where it does on anybody's profile, and nobody else's profile"
                  " has Settings", not moved and all(not theirs[k]["top"] and "settings" not in [r["what"] for r in theirs[k]["row"]]
                                                       and theirs[k]["inMain"] == 0 for k in theirs),
                  f"moved {moved}; on Mira's {json.dumps({str(k): [r['what'] for r in v['row']] for k, v in theirs.items()})}")
            # (b) a desk's rail, on every page; a phone's bar, its four.
            post = None
            c = mira.pg
            c.goto(BASE + "/social/")
            st, ans = c.evaluate("""async () => { const tok = document.querySelector('meta[name=social-csrf]').content;
                const pts = Array.from({ length: 30 }, (_, i) => ({ x: 300 + i * 6, y: 300 + Math.sin(i / 3) * 60, color: '#7c5cff', size: 8, t: i * 30, start: i === 0 }));
                const r = await fetch('/social/posts', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': tok },
                  body: JSON.stringify({ words: 'A cat, three whiskers a side', payload: { version: 2, schemaVersion: 2, playbackMode: 'replay',
                    canvasSize: { cssWidth: 816, cssHeight: 612 }, frames: [{ strokes: pts, strokeGroups: [pts.length], background: { color: '#f6f2ea' } }] } }) });
                return [r.status, await r.json().catch(() => ({}))]; }""")
            post = ans.get("post") if st == 200 else None
            pages = ["/social/", "/social/explore", "/social/activity", "/social/@mira", "/social/@nico", "/social/you/edit",
                     "/social/you", "/social/invites", "/social/you/delete"] + ([f"/social/p/{post}"] if post else [])
            lit_on = {"/social/you", "/social/invites", "/social/you/delete"}
            rails, bars = {}, {}
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, nico, "desk", scheme, theme=None)
                for path in pages:
                    go(pg, path)
                    rails[(scheme, path)] = pg.evaluate(RAIL)
                close_ctx(ctx, pg)
            ctx, pg = browser_as(b, nico, "phone", "light", theme=None)
            for path in pages:
                go(pg, path)
                bars[path] = [x["place"] for x in pg.evaluate(RAIL)]
            close_ctx(ctx, pg)
            bad = []
            for (scheme, path), rail in rails.items():
                places = [x["place"] for x in rail]
                s = next((x for x in rail if x["place"] == "Settings"), None)
                you = next((x for x in rail if x["place"] == "You"), None)
                lit = path in lit_on
                ok = (places[-2:] == ["Settings", "You"] and s and you and s["h"] == 52 and s["w"] == 215 and s["hit"] and s["gear"]
                      and s["href"] == "/social/you" and round(you["top"] - s["bottom"], 2) == 8
                      and (s["current"] == "page") == lit and s["line"] == lit and (s["weight"] == "700") == lit
                      and (not lit or you["current"] == "page"))
                if not ok:
                    bad.append(f"{scheme} {path}: {places} Settings {s} You {you and {k: you[k] for k in ('current', 'top')}}")
            check("(b) on a desk, Settings in the rail on every page, above your name at its foot (the gear, 215 x 52,"
                  " to Settings), lit like Home where it leads (Settings, Invites, deleting the account: the page's"
                  " mark, its name bold, the pen's line under it) and only there, You lit there too",
                  not bad and len(rails) == 2 * len(pages), "; ".join(bad)[:1600] or f"{len(rails)} rails read")
            check("a phone's bar keeps its four places (Home, Explore, Make, You) on every one of those pages: no"
                  " Settings in it", all(v == ["Home", "Explore", "Make", "You"] for v in bars.values()) and len(bars) == len(pages),
                  json.dumps(bars))
        except Exception as exc:  # noqa: BLE001
            stopped(6, exc)

    # ------------------------------------------------------------------ 7
    if part(7, "signed out, nothing new: no switch, no Settings; the device decides; the Pad's own switch sets it"):
        try:
            outs = []
            for screen, _ in SCREENS:
                for scheme in ("light", "dark"):
                    ctx, pg = browser_as(b, None, screen, scheme, theme=None)
                    for path in ("/social/", "/social/explore"):
                        go(pg, path)
                        st = pg.evaluate(STATE)
                        seen = pg.evaluate("""() => ({ switch: !!document.querySelector('[data-theme-switch]'),
                            settings: [...document.querySelectorAll('a[href$="/social/you"]')].filter(a => a.getClientRects().length).length,
                            places: [...document.querySelectorAll('nav.nav > a, nav.nav > button')].filter(e => e.getClientRects().length && !e.classList.contains('brand'))
                                     .map(e => (e.querySelector('.tab-name') || e).textContent.trim()) })""")
                        outs.append((not seen["switch"] and seen["settings"] == 0 and seen["places"] == ["Home", "Explore", "Make", "Sign in"]
                                     and st["stamp"] == scheme and st["page"] == PAGE_RGB[scheme],
                                     f"{screen} {scheme} {path}: {seen}, {st['stamp']} {st['page']}"))
                    close_ctx(ctx, pg)
            check("signed out the site shows nothing new: no Theme switch and no way to Settings anywhere, the bar and"
                  " the rail as they were (Home, Explore, Make, Sign in), and the device decides",
                  all(o for o, _ in outs), "; ".join(w for o, w in outs if not o) or f"{len(outs)} pages")
            ctx, pg = browser_as(b, None, "phone", "light", theme=None)
            go(pg, "/social/")
            press(pg, ".nav .tab-make")
            pg.wait_for_timeout(500)
            with pg.expect_navigation(timeout=30000):
                press(pg, "#makeSheet a.make-door >> nth=0")
            editor(pg)
            editor_choose(pg, "dark", "#menuBtn")
            pad = pg.evaluate(EDITOR)
            go(pg, "/social/")
            home = pg.evaluate(STATE)
            close_ctx(ctx, pg)
            check("signed out, the Pad's own switch (Make, Draw, its menu) sets the one choice: Dark there is Dark on"
                  " Blooby's Home", pad["mode"] == "dark" and pad["on"] == ["dark"] and home["stamp"] == "dark"
                  and home["page"] == PAGE_RGB["dark"] and home["kept"] == "dark", f"the Pad {pad}; Home {home}")
        except Exception as exc:  # noqa: BLE001
            stopped(7, exc)

    # ------------------------------------------------------------------ 8
    if part(8, "the dark ramp, written twice, is one: word for word, and every token the same each way"):
        try:
            css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
            chosen = re.search(r'^:root\[data-theme="dark"\]\s*\{(.*?)\n\}', css, re.S | re.M)
            device = re.search(r"^@media \(prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-theme\]\)\s*\{(.*?)\n  \}\s*\n\}", css, re.S | re.M)
            base = re.search(r"^:root\s*\{(.*?)\n\}", css, re.S | re.M)
            media = re.findall(r"@media[^{]*prefers-color-scheme[^{]*\{", css)
            d1, d2 = declarations(chosen.group(1)) if chosen else {}, declarations(device.group(1)) if device else {}
            lt = declarations(base.group(1)) if base else {}
            only_dark = sorted(k for k in d1 if k.startswith("--") and k not in lt)
            check("social.css says dark twice, once for Dark chosen and once for nothing stamped on a dark device, and the"
                  " two copies are the same declarations word for word; one media query in the sheet; no token only dark",
                  bool(d1) and d1 == d2 and len(media) == 1 and not only_dark,
                  f"{len(d1)} and {len(d2)} declarations; differ: {sorted(set(d1.items()) ^ set(d2.items()))[:6]};"
                  f" media queries {media}; dark-only {only_dark}")
            names = sorted(k for k in lt if k.startswith("--"))
            nico = someone(b, "nico", "Nico Reyes")
            TOKENS = "(names) => { const cs = getComputedStyle(document.documentElement); const o = {}; names.forEach(n => o[n] = cs.getPropertyValue(n).trim()); o['color-scheme'] = cs.colorScheme; return o; }"
            ways = {}
            for label, scheme, kept, js in (("dark chosen, light device", "light", "dark", True), ("dark chosen, dark device", "dark", "dark", True),
                                            ("nothing stamped, dark device", "dark", None, False),
                                            ("light chosen, dark device", "dark", "light", True), ("nothing stamped, light device", "light", None, False),
                                            ("light chosen, light device", "light", "light", True)):
                ctx, pg = browser_as(b, nico, "desk", scheme, theme=kept if js else "nothing", js=js)
                pg.goto(BASE + "/social/you")
                pg.wait_for_timeout(500 if js else 200)
                ways[label] = pg.evaluate(TOKENS, names)
                close_ctx(ctx, pg)
            darks = [ways[k] for k in ways if k.startswith(("dark", "nothing stamped, dark"))]
            lights = [ways[k] for k in ways if k.startswith(("light", "nothing stamped, light"))]
            check(f"every one of the site's {len(names)} tokens is the same in the three ways to dark, and in the three ways"
                  " to light, and the two differ",
                  len(names) > 30 and all(w == darks[0] for w in darks) and all(w == lights[0] for w in lights)
                  and darks[0]["--page"] == GROUND["dark"] and lights[0]["--page"] == GROUND["light"]
                  and darks[0]["color-scheme"] == "dark" and lights[0]["color-scheme"] == "light",
                  "; ".join(f"{k}: {sorted(n for n in v if v[n] != (darks if k.startswith(('dark', 'nothing stamped, dark')) else lights)[0][n])[:4]}"
                            for k, v in ways.items()))
        except Exception as exc:  # noqa: BLE001
            stopped(8, exc)

    # ------------------------------------------------------------------ 9
    if part(9, "words and marks: every changed screen, phone and desk, light and dark"):
        try:
            nico = someone(b, "nico", "Nico Reyes")
            looks, inks = {}, {}
            for screen, _ in SCREENS:
                for scheme in ("light", "dark"):
                    for kept in (None, "dark" if scheme == "light" else "light"):
                        ctx, pg = browser_as(b, nico, screen, scheme, theme=kept)
                        tag = f"{screen} {scheme} device, {kept or 'System'}"
                        go(pg, "/social/you")
                        looks[(tag, "Settings")] = pg.evaluate(READ, None)
                        inks[tag] = pg.evaluate(THEME_INK)
                        if kept is None:
                            for path, name in (("/social/@nico", "your profile"), ("/social/", "Home"),
                                               ("/social/you/delete", "deleting"), ("/social/invites", "Invites")):
                                go(pg, path)
                                looks[(tag, name)] = pg.evaluate(READ, None)
                        close_ctx(ctx, pg)
            low = [f"{k[0]} {k[1]}: {x}" for k, v in looks.items() for x in v["low"]]
            small = [f"{k[0]} {k[1]}: {x}" for k, v in looks.items() for x in v["small"]]
            fields = [f"{k[0]} {k[1]}: {x}" for k, v in looks.items() for x in v["fields"]]
            reads = sum(v["read"] for v in looks.values())
            lowest = min(((v["lowest"], f"{k[0]} {k[1]}") for k, v in looks.items()), default=(0, "nothing read"))
            print(f"    {reads} words read on {len(looks)} screens, the lowest {lowest[0]}:1 ({lowest[1]})")
            check("every word on Settings with the Theme row, your profile with Settings, a desk's rail with Settings"
                  " (Home, and lit on Settings, deleting and Invites) reads at 4.5:1 or more on what is painted behind"
                  " it: phone (touch) and desk, light and dark, System and a choice against the device",
                  reads >= 400 and not low, f"{reads} read, the lowest {lowest}; under 4.5: {low[:5]}")
            check("every target there 44px to a finger, and no text field under 16px", not small and not fields,
                  f"small {small[:5]}; fields {fields[:5]}")
            bad_ink = {k: v for k, v in inks.items() if not v or v.get("unread") or v["on"] < 4.5 or min(v["off"]) < 4.5}
            print("    the switch's words (on its pill; the others; the track's edge on the card):",
                  json.dumps(inks))
            check("the switch's chosen word reads at 4.5:1 or more on its pill, laid over the track, and the other two on"
                  " the track (phone and desk, light and dark)", not bad_ink and len(inks) == 8, json.dumps(bad_ink or inks))
        except Exception as exc:  # noqa: BLE001
            stopped(9, exc)

    # ------------------------------------------------------------------ 10
    if part(10, "no page errors, no console errors and no CSP violations"):
        nico = someone(b, "nico", "Nico Reyes")
        for screen, _ in SCREENS:
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, nico, screen, scheme, theme="dark" if scheme == "light" else "light")
                for path in ("/social/you", "/social/", "/social/explore", "/social/@nico", "/social/activity"):
                    go(pg, path)
                close_ctx(ctx, pg)
        check("no page errors, no console errors and no CSP violations, on every page this suite opened (the boot"
              " inline on each, by its nonce)", not ERRS, "; ".join(ERRS[:4]))

    b.close()

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(n for n, _ in bad)) if bad else ""))
sys.exit(1 if bad else 0)
