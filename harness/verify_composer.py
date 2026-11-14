"""The composer (docs/SOCIAL-SITE.md section 17, part two's first piece; the
owner's "Yes", Nov 14, to the mock beside Bluesky's new-post screen, B, and
to one drawing, one conversation), through the demo's own server, with
Chromium's virtual authenticator for the site's people and a real pen in
Skribl's real Pad.

  1. ONE MAKE, EVERYWHERE: signed in, every page with the bar (Home, the
     Gallery, Activity, your page, a post's page, Settings) carries the
     composer and no two-door sheet, and Make (the bar on a touch phone, the
     rail on a desk) opens it: a modal dialog, the words' field focused, the
     page behind inert. Home's row opens the same sheet, its words with the
     field ready and its Draw with the Pad rising over it. On a phone the
     sheet rises almost to the top (5vh short of it), on a desk it is a
     600px card in the middle. Signed out Make keeps its two doors, and the
     page holds no composer.
  2. IT GLIDES, NEVER A JUMP, read on every frame: up from below the screen
     and back down on Cancel (focus back on Make); a desk's card rising a
     little as it fades in; under Reduce Motion it never moves, it fades.
     Turning to Yours and back, the sheet keeps its box on every frame, one
     view fading out before the other fades in.
  3. THE SHEET, as the mock drew it: Cancel at the top left and Post at the
     top right, dim until a drawing is attached (a press says what is
     missing and sends nothing); your face beside "Say something…" at 18px;
     Draw, Flip and Yours along the bottom and the characters left at their
     end, 500, counting down as words are typed. On a phone's keyboard
     (stood in) the sheet rides above it, and a pinch's zoom is no keyboard.
  4. DRAW AND FLIP: Draw opens Skribl's Pad over the sheet in compose mode
     with the gallery's choice; Add hands the drawing back, PLAYING in the
     sheet's in-post player, Post lit and focus on Edit drawing; Edit drawing
     reopens it with the drawing put back; Remove takes it away and lets the
     frame go; Flip opens Flip the same way; with a drawing attached a tool
     says a post holds one and opens nothing; Post sends the words and the
     drawing as one post. Under Reduce Motion the drawing stays still.
  5. YOURS, "Use one you made": the one pill, Drafts | Drawings, Drafts
     first; your drafts (none of anybody else's), newest first; your
     drawings shared outside a post, link-only ones too, never a post's, a
     face, a comment's drawing or anybody else's, a page at a time with Load
     more; each tile a button. A drawing picked is attached as it is
     (playing, no Edit drawing, Remove ready); a draft picked opens in the
     editor that made it with the draft on its canvas, closing it is back to
     the picker, and Add to post attaches it playing. Its address refuses
     nobody and a list it does not have.
  6. ONE DRAWING, ONE CONVERSATION: an older drawing posted through Yours is
     the post's drawing (nothing new made in Skribl); its hearts (their
     moments kept), its comments and their answers move onto the post, their
     times kept, in the same transaction as the post (a failure at the move
     leaves no post and nothing moved); its old page sends everybody to the
     post, and its old like and comment addresses take nothing new; the
     Gallery shows it once, as the post, with the conversation's counts;
     Activity's row for a comment already seen opens the post, and the dot
     stays dark; one hidden from the Gallery stays hidden. Guards: somebody
     else's drawing, a face, a comment's drawing, one already in a post, a
     drawing beside a new one, no token, nobody.
  7. EVERY WORD AT 4.5:1 on what is painted behind it, every control 44px,
     every text field 16px: the composer empty, with words and a drawing,
     and Yours' Drafts and Drawings, phone and desk, light and dark.
  8. NO PAGE ERRORS, NO CONSOLE ERRORS AND NO CSP VIOLATIONS (run last).

COMPOSER_PART=<n>[,<m>] runs those sections only (calibration); a section
makes the people it needs. Every row was shown red by breaking one part and
green as built: DECISIONS.md, "The composer: one Make, and an older
drawing's conversation comes with it".
"""
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
from pathlib import Path

from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "harness" / "tools"))
PART = os.environ.get("COMPOSER_PART", "")
results = []
check = make_check(results, with_detail=True)


def part(n, label):
    if PART and str(n) not in PART.split(","):
        return False
    print(f"\nCOMPOSER {n} — {label}")
    return True


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the composer works.")
    raise SystemExit(77)
try:
    import webauthn  # noqa: F401  -- the site's own dependency (constraints.txt)
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc} (pip install -r constraints.txt --require-hashes)")
    raise SystemExit(77)
import artdraw  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the demo's own server, with what the site's people need -------------------
TMP = tempfile.mkdtemp(prefix="composer-")
DB = os.path.join(TMP, "site.db")
LOG = os.path.join(TMP, "server.log")
PORT = free_port()
BASE = f"http://localhost:{PORT}"
FIRST = "first-" + secrets.token_urlsafe(18)
ENV = dict(os.environ, DATABASE_URL=f"sqlite:///{DB}", SECRET_KEY="verify-composer-" + secrets.token_hex(8),
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
    return f"10.{70 + _addr[0] // 250}.{_addr[0] % 250}.9"


def db(sql, args=()):
    con = sqlite3.connect(DB, timeout=10)
    try:
        out = con.execute(sql, args).fetchall()
        con.commit()
        return out
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

    def api(self, method, path, body=None, token=True):
        """A request as this person from their own page (its token, its Origin)."""
        if not self.pg.url.startswith(BASE + "/social"):
            self.pg.goto(BASE + "/social/explore")
        return self.pg.evaluate("""async ([m, p, b, t]) => {
          const tok = t ? ((document.querySelector('meta[name="social-csrf"]') || {}).content || '') : '';
          const h = { 'Content-Type': 'application/json' }; if (tok) h['X-Social-CSRF'] = tok;
          const r = await fetch(p, { method: m, credentials: 'same-origin', headers: h, redirect: 'manual',
                                     body: b === null ? undefined : JSON.stringify(b) });
          let j = null; try { j = await r.json(); } catch (e) {}
          return [r.status, j]; }""", [method, path, body, token])

    def skribl(self, title, vis="public", seed=0):
        """A drawing shared from the Pad on its own page (its own Post): Skribl's
        API as this person, its own token from its own cookie: outside a post."""
        self.pg.goto(BASE + "/skribl-pad")
        self.pg.wait_for_timeout(300)
        return self.pg.evaluate("""async ([title, vis, seed]) => {
          await fetch('/api/skribls?limit=1', { credentials: 'same-origin' });
          const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
          const pts = Array.from({ length: 30 }, (_, i) => ({ x: 300 + i * 6, y: 300 + Math.sin((i + seed) / 3) * 60,
            color: '#7c5cff', size: 8, t: i * 30, start: i === 0 }));
          const r = await fetch('/api/skribls', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) },
            body: JSON.stringify({ title, visibility: vis, version: 2, schemaVersion: 2, playbackMode: 'replay',
              canvasSize: { cssWidth: 816, cssHeight: 612 }, frames: [{ strokes: pts, strokeGroups: [pts.length] }] }) });
          const j = await r.json().catch(() => ({})); return j.id || null; }""", [title, vis, seed])

    def draft(self, title, n=40, seed=0):
        """A draft saved to this person's account, as ⋯ Save draft saves one."""
        self.pg.goto(BASE + "/skribl-pad")
        self.pg.wait_for_timeout(300)
        return self.pg.evaluate("""async ([title, payload]) => {
          await fetch('/api/drafts', { credentials: 'same-origin' });
          const tok = (document.cookie.match(/(?:^|; )skribl_csrf=([^;]+)/) || [])[1] || '';
          const r = await fetch('/api/drafts', { method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Skribl-CSRF': decodeURIComponent(tok) },
            body: JSON.stringify({ kind: 'pad', title, payload }) });
          const j = await r.json().catch(() => ({})); return j.id || null; }""", [title, drawing(n=n, seed=seed)])


def browser_as(b, who, screen="phone", scheme="light", reduced=False, init=None):
    kw = {"reduced_motion": "reduce"} if reduced else {}
    ctx = b.new_context(color_scheme=scheme, extra_http_headers={"X-Forwarded-For": who.xff if who else address()},
                        **(PHONE if screen == "phone" else DESK), **kw)
    ctx.add_init_script(WATCH)
    if init:
        ctx.add_init_script(init)
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


def someone(b, handle, name):
    """Somebody who joined through an invite (the first through the first
    invite code), signed in, in a browser of their own."""
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


def go(pg, path, wait=500):
    pg.goto(BASE + path)
    pg.wait_for_timeout(wait)


def tap(pg, sel, screen="phone"):
    """A finger on a phone, a click on a desk; aria-disabled is pressed too."""
    loc = pg.locator(sel).first
    if screen == "phone":
        loc.tap(force=True, timeout=5000)
    else:
        loc.click(force=True, timeout=5000)


def press(pg, sel):
    """A button's own click, without waiting for it to be pressable."""
    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.click(); }", sel)


class InFrame:
    """artdraw's page, for an editor in an iframe: the pen goes in at the top
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
CIRCLE = [S([(354 + 150 * math.cos(a / 10), 300 + 130 * math.sin(a / 10)) for a in range(0, 64)], "gesture",
            artdraw.INK, size=16),
          S([(300, 280), (312, 292)], "detail", artdraw.PURPLE, size=14)]


def add_from_pad(pg, fr):
    """Draw, end the take, and press Add, then Add to post."""
    fr.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); setTool('pen');"
                " if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")
    artdraw.draw(InFrame(pg, fr), CIRCLE, tempo=2.5, pause_tempo=3)
    pg.wait_for_timeout(400)
    if fr.evaluate("() => typeof recording !== 'undefined' && !!recording"):
        fr.click("#recordBtn")
        pg.wait_for_timeout(400)
    fr.click("#postBtn")
    pg.wait_for_timeout(700)
    sheet = fr.evaluate("""() => ({ label: (document.getElementById('postSubmitLabel') || {}).textContent,
      tick: [...document.querySelectorAll('#postSheet label')].map(l => l.textContent.trim()).filter(t => /gallery/i.test(t)) })""")
    fr.click("#postSubmitBtn")
    pg.wait_for_timeout(1400)
    return sheet


# ---- the composer, as it is now ---------------------------------------------------
SHEET = """() => { const w = document.getElementById('composeSheet'); if (!w) return null;
  const s = w.querySelector('.make-sheet'), a = document.activeElement, r = s.getBoundingClientRect();
  const att = window.SocialComposer ? SocialComposer.attached() : null;
  return { open: !w.hidden && w.classList.contains('is-open'), hidden: w.hidden, role: s.getAttribute('role'),
    modal: s.getAttribute('aria-modal'), focusIn: !!a && s.contains(a),
    focus: !a ? null : a.matches('[data-compose-words]') ? 'words' : (a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 24) || a.tagName,
    inert: ['body > .top', 'body > .nav', '#main'].map(q => { const e = document.querySelector(q); return !!e && e.hasAttribute('inert'); }),
    top: Math.round(r.top * 10) / 10, bottom: Math.round(r.bottom * 10) / 10, left: Math.round(r.left), right: Math.round(r.right),
    width: Math.round(r.width), opacity: +getComputedStyle(s).opacity, att,
    views: [...s.querySelectorAll('[data-compose-view]')].filter(v => !v.hidden).map(v => v.getAttribute('data-compose-view')),
    expanded: [...document.querySelectorAll('[data-make]')].filter(m => m.getClientRects().length).map(m => m.getAttribute('aria-expanded')),
    two: !!document.getElementById('makeSheet') }; }"""

# Its top, its opacity and whether it is hidden, on every frame for `ms`,
# from a press on `sel` (or "Cancel": the sheet's own Cancel).
GLIDE = """([sel, ms]) => new Promise(res => { const w = document.getElementById('composeSheet'), s = w.querySelector('.make-sheet'), out = [];
  const t0 = performance.now(); document.querySelector(sel === 'Cancel' ? '#composeSheet [data-compose-cancel]' : sel).click();
  (function f() { const r = s.getBoundingClientRect(); out.push([Math.round(r.top * 10) / 10, +getComputedStyle(s).opacity, w.hidden]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""

# Turning to Yours (or Back), on every frame for `ms`: the sheet's box, and
# each view's opacity as painted (0 while it is hidden).
SWAP = """([sel, ms]) => new Promise(res => { const s = document.querySelector('#composeSheet .make-sheet'), out = [];
  const v = k => s.querySelector('[data-compose-view="' + k + '"]');
  const op = e => e.hidden || !e.getClientRects().length ? 0 : +getComputedStyle(e).opacity;
  const t0 = performance.now(); document.querySelector(sel).click();
  (function f() { const r = s.getBoundingClientRect();
    out.push({ top: Math.round(r.top * 10) / 10, h: Math.round(r.height * 10) / 10, write: Math.round(op(v('write')) * 100) / 100,
               pick: Math.round(op(v('pick')) * 100) / 100 });
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })"""


def glide(frames, rest, start):
    """The tops of the frames read: did it start where it rests closed, end
    where it rests open, move on many frames, one way, and never jump?"""
    tops = [f[0] for f in frames]
    travel = abs(start - rest)
    steps = [b - a for a, b in zip(tops, tops[1:])]
    big = max((abs(s) for s in steps), default=0)
    way = [s for s in steps if s != 0]
    one_way = all(s < 0 for s in way) if start > rest else all(s > 0 for s in way)
    return {"from": tops[0], "to": tops[-1], "positions": len(set(tops)), "biggest step": round(big, 1),
            "travel": round(travel, 1), "one way": one_way}


def swap_ok(frames, going):
    """The swap read on every frame: the sheet's box one box throughout; the
    view going out fades on several frames before the one coming in is seen,
    and that one fades in on several; never both seen at once."""
    out_k, in_k = ("write", "pick") if going == "pick" else ("pick", "write")
    boxes = {(f["top"], f["h"]) for f in frames}
    outs = [f[out_k] for f in frames]
    first_in = next((i for i, f in enumerate(frames) if f[in_k] > 0), None)
    fading_out = sorted({o for o in outs[:first_in] if 0 < o < 1}) if first_in is not None else []
    fading_in = sorted({f[in_k] for f in frames if 0 < f[in_k] < 1})
    both = [f for f in frames if f["write"] > 0 and f["pick"] > 0]
    return {"one box": len(boxes) == 1, "fading out": len(fading_out), "fading in": len(fading_in),
            "both seen": len(both), "ends": [frames[-1][out_k], frames[-1][in_k]] if frames else None}


# A PHONE'S KEYBOARD, STOOD IN (verify_socialcomments' own): this box has
# none, so the visual viewport is stood in for (before the page's scripts
# run), and a keyboard of `px` is reported as iPhone's Safari reports one:
# the visual viewport shorter, the layout viewport unchanged. Not a phone.
KEYBOARD = """(() => { const t = new EventTarget(); let h = null, off = 0, scale = 1;
  const vv = { get width() { return innerWidth; }, get height() { return h === null ? innerHeight : h; },
    get offsetTop() { return off; }, get offsetLeft() { return 0; }, get scale() { return scale; },
    addEventListener: (...a) => t.addEventListener(...a), removeEventListener: (...a) => t.removeEventListener(...a) };
  Object.defineProperty(window, 'visualViewport', { configurable: true, get: () => vv });
  window.__keyboard = (px, zoom) => { scale = zoom || 1; h = innerHeight - px; off = 0; t.dispatchEvent(new Event('resize')); }; })();"""

# THE SHEET'S PARTS, where they are and whether they are what is painted
# there (elementFromPoint at their middle).
PARTS = """() => { const s = document.querySelector('#composeSheet .make-sheet'), r = s.getBoundingClientRect();
  const one = sel => { const e = s.querySelector(sel); if (!e || !e.getClientRects().length) return null; const q = e.getBoundingClientRect();
    const at = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
    return { x: Math.round(q.left - r.left), y: Math.round(q.top - r.top), right: Math.round(r.right - q.right), bottom: Math.round(r.bottom - q.bottom),
             w: Math.round(q.width), h: Math.round(q.height), painted: !!at && (at === e || e.contains(at)),
             words: (e.textContent || '').trim().replace(/\\s+/g, ' '), opacity: +getComputedStyle(e).opacity }; };
  const w = s.querySelector('[data-compose-words]'), cs = getComputedStyle(w);
  const tools = [...s.querySelectorAll('.cmp-tools > *')].filter(e => e.getClientRects().length).map(e => (e.textContent || '').trim().replace(/\\s+/g, ' '));
  return { cancel: one('[data-compose-cancel]'), post: one('[data-compose-post]'), face: one('.cmp-face'), words: one('[data-compose-words]'),
           tools, toolsBox: one('.cmp-tools'), left: one('.cmp-left'), disabled: s.querySelector('[data-compose-post]').getAttribute('aria-disabled'),
           field: { size: cs.fontSize, placeholder: w.getAttribute('placeholder'), max: w.getAttribute('maxlength') },
           say: (s.querySelector('[data-compose-say]') || {}).textContent || '' }; }"""

# EVERY WORD on what is painted behind it, every control 44px, every text
# field 16px, in `root` (the site's suites' own reader: the ground composited
# up to the first opaque one, and a word counted only where it is what is
# painted at its middle).
CENSUS = """(root) => {
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
  const op = e => { let o = 1; for (let n = e; n; n = n.parentElement) o *= +getComputedStyle(n).opacity; return o; };
  const SKRIBLS = '.skribl-inline, .skribl-inline-line';
  const R = document.querySelector(root); if (!R) return null;
  const out = { read: 0, low: [], small: [], fields: [], lowest: 99 };
  R.querySelectorAll('*').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    if (e.closest('[aria-disabled="true"]')) return;   // an inactive control: WCAG 1.4.3 exempts it
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    const isField = e.matches('textarea, input');
    if (!own && !isField) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
    const c = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    if (!c || !(c === e || e.contains(c) || c.contains(e))) return;
    const g = ground(e), ink = rgba(isField && !e.value ? getComputedStyle(e, '::placeholder').color : getComputedStyle(e).color);
    const k = ratio(over([ink[0], ink[1], ink[2], ink[3] * op(e)], g), g);
    out.read++;
    if (k < out.lowest) out.lowest = Math.round(k * 100) / 100;
    if (k < 4.5) out.low.push((e.className || e.tagName) + ' "' + (e.textContent || e.placeholder || '').trim().slice(0, 30) + '" ' + k.toFixed(2));
  });
  R.querySelectorAll('a[href], button, input, textarea, select, [role=button]').forEach(e => {
    if (!e.getClientRects().length || e.closest('[hidden], .words, .sr, ' + SKRIBLS)) return;
    const r = e.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (e.matches('.fo-seg > button')) { const mid = r.left + r.width / 2, hit = d => { const x = document.elementFromPoint(mid, r.top + r.height / 2 + d); return !!x && (x === e || e.contains(x)); }; if (r.width >= 44 && hit(0) && hit(-21) && hit(21)) return; }
    if (r.width < 44 || r.height < 44) out.small.push((e.className || e.tagName) + ' "' + (e.textContent || '').trim().slice(0, 20) + '" ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  R.querySelectorAll('input[type=text], input:not([type]), input[type=search], textarea, select').forEach(e => {
    if (!e.getClientRects().length) return;
    const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 16) out.fields.push((e.id || e.name) + ' ' + fs + 'px');
  });
  return out; }"""

STATE = """() => { const p = window.SkriblInline ? SkriblInline.players() : [];
  const box = document.getElementById('composeDraft'); const me = p.find(x => x.el === box);
  return me ? me.state().state : null; }"""


def open_composer(pg, screen="phone"):
    tap(pg, "nav.nav .tab-make", screen)
    pg.wait_for_timeout(700)


def yours(pg, screen="phone", which="drafts"):
    """Yours, and its list `which` (the picker keeps the one last shown)."""
    tap(pg, "#composeSheet [data-compose-yours]", screen)
    pg.wait_for_timeout(700)
    tap(pg, f"#composeSheet [data-compose-pill] button[data-pick={which}]", screen)
    pg.wait_for_timeout(900)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ------------------------------------------------------------------ 1
    if part(1, "one Make, everywhere: the bar and the rail open the composer on every page, Home's row the same"):
        mira = someone(b, "mira", "Mira Okafor")
        st, made = mira.api("POST", "/social/posts", {"words": "Section 1's post", "payload": drawing(seed=1)})
        post_url = (made or {}).get("go")
        pages = ["/social/", "/social/explore", "/social/activity", "/social/@mira", post_url or "/social/", "/social/you"]
        where = {}
        for screen in ("phone", "desk"):
            ctx, pg = browser_as(b, mira, screen)
            for path in pages:
                try:
                    go(pg, path)
                    before = pg.evaluate(SHEET)
                    open_composer(pg, screen)
                    got = pg.evaluate(SHEET)
                    where[(screen, path)] = (before is not None and not before["open"] and not before["two"]
                                             and got["open"] and got["role"] == "dialog" and got["modal"] == "true"
                                             and got["focus"] == "words" and all(got["inert"]) and got["expanded"]
                                             and all(x == "true" for x in got["expanded"]))
                    if not where[(screen, path)]:
                        where[(screen, path)] = {"before": before, "after": got}
                except Exception as exc:  # noqa: BLE001 -- the row's red
                    where[(screen, path)] = {"stopped": str(exc).splitlines()[0][:100]}
            close_ctx(ctx, pg)
        check("signed in, every page with the bar carries the composer and no two-door sheet, and Make opens it: the"
              " bar's on a touch phone, the rail's on a desk; a modal dialog, the words' field focused, the page behind"
              " inert (Home, the Gallery, Activity, your page, a post's page, Settings)",
              len(where) == 12 and all(v is True for v in where.values()),
              json.dumps({f"{k[0]} {k[1]}": v for k, v in where.items() if v is not True})[:900])
        rests = {}
        for screen in ("phone", "desk"):
            ctx, pg = browser_as(b, mira, screen)
            go(pg, "/social/explore")
            open_composer(pg, screen)
            rests[screen] = pg.evaluate(SHEET)
            close_ctx(ctx, pg)
        ph, dk = rests["phone"], rests["desk"]
        check("on a phone it rises almost to the top (5vh short of it, 43.7px), the screen's whole width, to the"
              " bottom; on a desk a 600px card in the middle of the screen",
              abs(ph["top"] - 874 * 0.05) <= 1 and ph["bottom"] == 874 and ph["left"] == 0 and ph["right"] == 402
              and dk["width"] == 600 and abs((dk["left"] + dk["right"]) / 2 - 640) <= 2
              and abs((dk["top"] + dk["bottom"]) / 2 - 430) <= 2,
              f"phone {[ph[k] for k in ('top', 'bottom', 'left', 'right')]}; desk {[dk[k] for k in ('top', 'bottom', 'left', 'right', 'width')]}")
        ctx, pg = browser_as(b, mira)
        go(pg, "/social/")
        row = pg.evaluate("""() => { const r = document.querySelector('[data-compose-row]');
          return r && { words: r.querySelector('[data-compose-go=words]').textContent.trim(),
            tools: [...r.querySelectorAll('[data-compose-go]')].map(b => b.getAttribute('data-compose-go')),
            post: !!r.querySelector('[data-compose-post], .composer-post') }; }""")
        tap(pg, "[data-compose-row] [data-compose-go=words]")
        pg.wait_for_timeout(700)
        by_words = pg.evaluate(SHEET)
        press(pg, "#composeSheet [data-compose-cancel]")
        pg.wait_for_timeout(700)
        tap(pg, "[data-compose-row] [data-compose-go=pad]")
        fr = editor_frame(pg, "skribl-pad")
        by_draw = pg.evaluate("""() => ({ sheet: document.getElementById('composeSheet').classList.contains('is-open'),
          pad: !document.getElementById('composePad').hidden, src: document.querySelector('#composePad iframe').getAttribute('src') })""")
        close_ctx(ctx, pg)
        check("Home's row (\"Say something, then draw it…\", Draw, Flip, no Post) opens the same sheet: its words with the"
              " field focused, its Draw with Skribl's Pad rising over the sheet (compose=1&gallery=1)",
              row == {"words": "Say something, then draw it…", "tools": ["words", "pad", "flip"], "post": False}
              and by_words["open"] and by_words["focus"] == "words" and bool(fr) and by_draw["sheet"] and by_draw["pad"]
              and "compose=1" in (by_draw["src"] or "") and "gallery=1" in (by_draw["src"] or ""),
              f"row {row}; by its words {by_words and {k: by_words[k] for k in ('open', 'focus')}}; by Draw {by_draw}, frame {bool(fr)}")
        nctx, npg = browser_as(b, None)
        go(npg, "/social/")
        raw = urllib.request.urlopen(BASE + "/social/explore", timeout=20).read().decode()
        press(npg, "nav.nav .tab-make")
        npg.wait_for_timeout(700)
        nobody = npg.evaluate("""() => { const m = document.getElementById('makeSheet');
          return { two: !!m && m.classList.contains('is-open') && [...m.querySelectorAll('a.make-door b')].map(b => b.textContent),
                   composer: !!document.getElementById('composeSheet') }; }""")
        close_ctx(nctx, npg)
        check("signed out there is nobody to post as: Make keeps its two doors into Skribl's own Pad and Flip, and the"
              " page holds no composer, in the page or its source",
              nobody == {"two": ["Draw", "Flip"], "composer": False} and "composeSheet" not in raw and "compose.js" not in raw,
              f"{nobody}; composer in the source {'composeSheet' in raw}")

    # ------------------------------------------------------------------ 2
    if part(2, "it glides, read on every frame, never a jump; Reduce Motion still; Yours and back keep the sheet's box"):
        mira = someone(b, "mira", "Mira Okafor")
        ctx, pg = browser_as(b, mira)
        go(pg, "/social/explore")
        frames = pg.evaluate(GLIDE, ["nav.nav .tab-make", 900])
        rest = pg.evaluate(SHEET)
        up = glide(frames, rest["top"], 874)
        check("on a phone it glides up from below the screen to where it rests, on many frames, one way, never a jump",
              up["from"] >= 873 and abs(up["to"] - rest["top"]) <= 0.5 and up["positions"] >= 8 and up["one way"]
              and up["biggest step"] <= 0.3 * up["travel"], json.dumps(up))
        frames = pg.evaluate(GLIDE, ["Cancel", 900])
        shut = pg.evaluate(SHEET)
        down = glide([f for f in frames if not f[2]], 874, rest["top"])
        check("Cancel puts it away, gliding down the same way, focus back on the bar's Make, the page no longer inert",
              shut["hidden"] and down["positions"] >= 6 and down["one way"] and down["biggest step"] <= 0.35 * down["travel"]
              and pg.evaluate("() => document.activeElement.classList.contains('tab-make')") and not any(shut["inert"]),
              f"{json.dumps(down)}; hidden {shut['hidden']}; inert {shut['inert']}")
        # Yours and back: the sheet keeps its box on every frame.
        open_composer(pg)
        there = pg.evaluate(SWAP, ["#composeSheet [data-compose-yours]", 700])
        back = pg.evaluate(SWAP, ["#composeSheet [data-compose-back]", 700])
        a, z = swap_ok(there, "pick"), swap_ok(back, "write")
        focus = pg.evaluate("() => document.activeElement.textContent.trim()")
        close_ctx(ctx, pg)
        check("Yours and Back: the sheet keeps its box on every frame; the words fade out on several frames before \"Use"
              " one you made\" fades in on several, never both seen, and back the same way, focus on Yours again",
              all(x["one box"] and x["fading out"] >= 3 and x["fading in"] >= 3 and x["both seen"] == 0 and x["ends"] == [0, 1]
                  for x in (a, z)) and focus == "Yours",
              f"to Yours {a}; back {z}; focus {focus!r}")
        ctx, pg = browser_as(b, mira, "desk")
        go(pg, "/social/explore")
        frames = pg.evaluate(GLIDE, ["nav.nav .tab-make", 700])
        rest = pg.evaluate(SHEET)
        seen = [f for f in frames if f[1] > 0.02]
        tops = [f[0] for f in seen]
        rises = all(b_ <= a_ for a_, b_ in zip(tops, tops[1:])) and tops and tops[0] - rest["top"] <= 28.5 and abs(tops[-1] - rest["top"]) <= 0.5
        check("on a desk the card rises a little (28px at most) as it fades in, never jumping",
              rises and len({round(f[1], 2) for f in frames}) >= 4 and len(set(tops)) >= 4,
              f"tops while seen {tops[:3]}…{tops[-2:]}, rests {rest['top']}; opacities {len({round(f[1], 2) for f in frames})}")
        close_ctx(ctx, pg)
        ctx, pg = browser_as(b, mira, reduced=True)
        go(pg, "/social/explore")
        frames = pg.evaluate(GLIDE, ["nav.nav .tab-make", 700])
        still = pg.evaluate(SHEET)
        gone = pg.evaluate(GLIDE, ["Cancel", 700])
        seen_up = sorted({f[0] for f in frames if f[1] > 0.02})
        seen_down = sorted({f[0] for f in gone if not f[2] and f[1] > 0.02})
        fades = (len({round(f[1], 2) for f in frames}), len({round(f[1], 2) for f in gone if not f[2]}))
        open_composer(pg)
        r_there = swap_ok(pg.evaluate(SWAP, ["#composeSheet [data-compose-yours]", 700]), "pick")
        close_ctx(ctx, pg)
        check("under Reduce Motion it does not move: it fades in where it rests and fades out there, every frame; Yours"
              " is the same fades, the sheet still",
              still["open"] and len(seen_up) == 1 and abs(seen_up[0] - still["top"]) <= 0.5 and seen_down == seen_up
              and min(fades) >= 3 and r_there["one box"] and r_there["both seen"] == 0 and r_there["ends"] == [0, 1],
              f"opening, its tops {seen_up[:3]}; closing {seen_down[:3]}; opacities {fades}; Yours {r_there}")

    # ------------------------------------------------------------------ 3
    if part(3, "the sheet: Cancel and Post, your face beside the words, Draw, Flip, Yours and 500; the keyboard"):
        mira = someone(b, "mira", "Mira Okafor")
        looks = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, mira, screen, scheme)
                sent = []
                pg.on("request", lambda r: sent.append(r.url) if r.method == "POST" and r.url.endswith("/social/posts") else None)
                go(pg, "/social/explore")
                open_composer(pg, screen)
                look = pg.evaluate(PARTS)
                tap(pg, "#composeSheet [data-compose-post]", screen)
                pg.wait_for_timeout(300)
                look["pressed"] = pg.evaluate(PARTS)["say"]
                pg.fill("#composeSheet [data-compose-words]", "A slow snail for a slow Saturday.")
                pg.wait_for_timeout(200)
                look["typed"] = pg.evaluate(PARTS)["left"]["words"]
                look["sent"] = len(sent)
                looks[f"{screen} {scheme}"] = look
                close_ctx(ctx, pg)
        bad = {}
        for k, v in looks.items():
            c, po = v["cancel"], v["post"]
            ok = (c and c["words"] == "Cancel" and c["x"] <= 16 and c["y"] <= 20 and c["painted"] and c["h"] >= 44
                  and po and po["words"] == "Post" and po["right"] <= 16 and abs((po["y"] + po["h"] / 2) - (c["y"] + c["h"] / 2)) <= 1
                  and po["painted"] and v["disabled"] == "true" and abs(po["opacity"] - 0.45) < 0.01
                  and v["face"] and v["face"]["w"] == 40 and v["words"] and v["words"]["x"] == v["face"]["x"] + 52
                  and v["field"] == {"size": "18px", "placeholder": "Say something…", "max": "500"}
                  and v["tools"] == ["Draw", "Flip", "Yours", "500 characters left"] and v["toolsBox"]["bottom"] <= 32
                  and v["left"]["right"] <= 16 and v["pressed"] == "Draw something first, or pick one you made."
                  and v["typed"] == "467 characters left" and v["sent"] == 0)
            if not ok:
                bad[k] = v
        check("as the mock drew it: Cancel at the top left and Post at the top right on its line, dim (0.45) until a"
              " drawing is attached, a press saying what is missing and sending nothing; your face (40) beside \"Say"
              " something…\" (18px, 500 at most); Draw, Flip and Yours along the bottom, the characters left at their"
              " end, 500, then 467 after 33 typed; phone and desk, light and dark",
              not bad, json.dumps(bad)[:1200])
        kctx, kpg = browser_as(b, mira, init=KEYBOARD)
        go(kpg, "/social/explore")
        open_composer(kpg)
        kpg.evaluate("() => window.__keyboard(336)")
        kpg.wait_for_timeout(500)
        on_kb = kpg.evaluate("""() => { const s = document.querySelector('#composeSheet .make-sheet').getBoundingClientRect(),
          t = document.querySelector('#composeSheet .cmp-tools').getBoundingClientRect(), w = document.querySelector('[data-compose-words]').getBoundingClientRect();
          return { bottom: Math.round(s.bottom), tools: Math.round(t.bottom), field: Math.round(w.bottom), floor: innerHeight - 336, top: Math.round(s.top) }; }""")
        kpg.evaluate("() => window.__keyboard(0)")
        kpg.wait_for_timeout(500)
        off_kb = kpg.evaluate("() => Math.round(document.querySelector('#composeSheet .make-sheet').getBoundingClientRect().bottom)")
        kpg.evaluate("() => window.__keyboard(300, 2)")
        kpg.wait_for_timeout(500)
        zoomed = kpg.evaluate("() => Math.round(document.querySelector('#composeSheet .make-sheet').getBoundingClientRect().bottom)")
        close_ctx(kctx, kpg)
        check("on a phone's keyboard the sheet's foot rides above it, the tools and the field in view, its top where it"
              " was, and goes back down with it; a pinch's zoom is no keyboard (a stand-in visual viewport: this box has"
              " no phone keyboard)",
              abs(on_kb["bottom"] - on_kb["floor"]) <= 1 and on_kb["tools"] <= on_kb["floor"] and on_kb["field"] < on_kb["floor"]
              and abs(on_kb["top"] - 44) <= 1 and off_kb == 874 and zoomed == 874,
              f"on a 336px keyboard {on_kb}; after {off_kb}; zoomed {zoomed}")

    # ------------------------------------------------------------------ 4
    if part(4, "Draw and Flip: Skribl's editor over the sheet; Add hands the drawing back, playing; Edit, Remove, Post"):
        mira = someone(b, "mira", "Mira Okafor")
        ctx, pg = browser_as(b, mira)
        go(pg, "/social/@mira")
        open_composer(pg)
        tap(pg, "#composeSheet [data-compose-open=pad]")
        fr = editor_frame(pg, "skribl-pad")
        src = pg.evaluate("() => document.querySelector('#composePad iframe').getAttribute('src')")
        sheet = add_from_pad(pg, fr) if fr else {}
        pg.wait_for_timeout(600)
        got = pg.evaluate(SHEET)
        state = pg.evaluate(STATE)
        parts_ = pg.evaluate(PARTS)
        check("Draw opens Skribl's Pad over the sheet in compose mode with the gallery's choice (compose=1&gallery=1), its"
              " sheet saying Add to post; Add hands the drawing back into the sheet's own in-post player, PLAYING, Post"
              " lit, Edit drawing and Remove under it, focus on Edit drawing, the editor gone",
              bool(fr) and "compose=1" in (src or "") and "gallery=1" in (src or "") and sheet.get("label") == "Add to post"
              and got["open"] and got["att"] == {"kind": "payload", "id": None} and state == "playing"
              and parts_["disabled"] == "false" and got["focus"] == "Edit drawing"
              and pg.evaluate("() => document.getElementById('composePad').hidden"),
              f"src {src}; sheet {sheet}; attached {got['att']}; player {state}; Post aria-disabled {parts_['disabled']}; focus {got['focus']}")
        pg.evaluate("""() => { window.__loads = 0; const f = document.querySelector('#composePad iframe');
          f.contentWindow.addEventListener('message', e => { if (e.data && e.data.type === 'skribl:compose:load') window.__loads++; }); }""")
        tap(pg, "#composeSheet [data-compose-open=flip]")
        pg.wait_for_timeout(500)
        one = pg.evaluate("() => ({ said: document.querySelector('[data-compose-say]').textContent, flip: !document.getElementById('composeFlip').hidden })")
        tap(pg, "#composeSheet [data-compose-edit]")
        pg.wait_for_timeout(900)
        reopened = pg.evaluate("() => ({ open: !document.getElementById('composePad').hidden, loads: window.__loads })")
        fr2 = editor_frame(pg, "skribl-pad")
        if fr2:
            fr2.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        tap(pg, "#composeSheet [data-compose-remove]")
        pg.wait_for_timeout(400)
        removed = pg.evaluate("""() => ({ att: SocialComposer.attached(), shown: !document.querySelector('[data-compose-draft]').hidden,
          post: document.querySelector('[data-compose-post]').getAttribute('aria-disabled'),
          frame: document.querySelector('#composePad iframe').getAttribute('src') })""")
        check("with a drawing attached a tool says a post holds one and opens nothing; Edit drawing reopens the Pad with the"
              " drawing put back in it (a load message); Remove takes it away, Post dim again, and the frame is let go",
              one == {"said": "A post holds one drawing. Remove this one to use another.", "flip": False}
              and reopened["open"] and reopened["loads"] >= 1
              and removed == {"att": None, "shown": False, "post": "true", "frame": "about:blank"},
              f"a second tool {one}; reopened {reopened}; removed {removed}")
        tap(pg, "#composeSheet [data-compose-open=flip]")
        ffr = editor_frame(pg, "/flip?")
        fsrc = pg.evaluate("() => document.querySelector('#composeFlip iframe').getAttribute('src')")
        fopen = pg.evaluate("() => !document.getElementById('composeFlip').hidden")
        if ffr:
            ffr.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        check("Flip opens Skribl's Flip over the sheet the same way (compose=1&gallery=1), and its × puts it away, the sheet"
              " still there",
              bool(ffr) and fopen and "compose=1" in (fsrc or "") and "gallery=1" in (fsrc or "")
              and pg.evaluate("() => document.getElementById('composeFlip').hidden") and pg.evaluate(SHEET)["open"],
              f"frame {bool(ffr)}; src {fsrc}; open {fopen}")
        tap(pg, "#composeSheet [data-compose-open=pad]")
        fr3 = editor_frame(pg, "skribl-pad")
        if fr3:
            add_from_pad(pg, fr3)
        pg.fill("#composeSheet [data-compose-words]", "Day 12. The beard took longer than the skull.")
        try:
            with pg.expect_navigation(timeout=30000):
                tap(pg, "#composeSheet [data-compose-post]")
        except Exception as exc:  # noqa: BLE001
            ERRS.append(f"post did not go: {str(exc).splitlines()[0][:100]}")
        pg.wait_for_timeout(1000)
        url = pg.evaluate("() => location.pathname")
        row = db("select p.words, p.skribl_id, pe.handle from social_posts p join social_people pe on pe.id = p.person_id"
                 " where p.public_id = ?", (url.rsplit("/", 1)[-1],))
        sk = db("select visibility, title, user_id from skribl_posts where public_id = ?", (row[0][1],)) if row else []
        close_ctx(ctx, pg)
        check("Post sends the words and the drawing as one post and lands on its page: its row (the words as typed), its"
              " skribl through create_post (unlisted without the tick, titled by the words, the person its author)",
              url.startswith("/social/p/") and row and row[0][0] == "Day 12. The beard took longer than the skull."
              and row[0][2] == "mira" and sk and sk[0][0] == "unlisted" and sk[0][1] == row[0][0]
              and sk[0][2] == db("select public_id from social_people where handle = 'mira'")[0][0],
              f"url {url}; row {row}; skribl {sk}")
        rctx, rpg = browser_as(b, mira, reduced=True)
        go(rpg, "/social/explore")
        open_composer(rpg)
        sid = mira.skribl("Still, please", seed=4)
        rpg.goto(BASE + "/social/explore")
        rpg.wait_for_timeout(500)
        open_composer(rpg)
        yours(rpg, which="drawings")
        tap(rpg, f"#composeSheet [data-pick-drawing='{sid}']")
        rpg.wait_for_timeout(1200)
        still = rpg.evaluate(STATE)
        close_ctx(rctx, rpg)
        check("under Reduce Motion the drawing attached does not play: it rests, finished",
              still in ("idle", "paused"), f"its player {still}")

    # ------------------------------------------------------------------ 5
    if part(5, "Yours: Drafts | Drawings, yours alone; a drawing attached as it is; a draft through its editor"):
        ana = someone(b, "ana", "Ana Ruiz")
        ben = someone(b, "ben", "Ben Cho")
        d_old = ana.draft("Pip at the window", seed=2)
        time.sleep(1.1)
        d_new = ana.draft("A snail for Theo", n=52, seed=3)
        ben.draft("Ben's own draft", seed=4)
        loose = ana.skribl("A slow snail", "public", seed=1)
        hidden = ana.skribl("Kept to its link", "unlisted", seed=2)
        theirs = ben.skribl("Ben's drawing", "public", seed=3)
        st, made = ana.api("POST", "/social/posts", {"words": "Ana's post", "payload": drawing(seed=5)})
        in_post = db("select skribl_id from social_posts where public_id = ?", ((made or {}).get("post"),))
        in_post = in_post[0][0] if in_post else None
        ana.pg.goto(BASE + "/social/@ana")
        ana.pg.wait_for_timeout(400)
        face_st, face = ana.api("POST", "/social/you/face", {"payload": drawing(seed=6)})
        st_c, cm = ben.api("POST", f"/social/p/{(made or {}).get('post')}/comments", {"words": "", "payload": drawing(seed=7)})
        ana_answer_st, _ = ana.api("POST", f"/social/p/{(made or {}).get('post')}/comments",
                                   {"words": "A drawing back", "payload": drawing(seed=8)})
        ana_cm = db("select c.skribl_id from social_comments c join social_people p on p.id = c.person_id"
                    " where p.handle = 'ana' and c.skribl_id is not null")
        extra = [ana.skribl(f"Older {i}", "public", seed=10 + i) for i in range(24)]
        ctx, pg = browser_as(b, ana)
        go(pg, "/social/explore")
        open_composer(pg)
        tap(pg, "#composeSheet [data-compose-yours]")
        pg.wait_for_timeout(1500)
        pick = pg.evaluate("""() => { const s = document.querySelector('#composeSheet [data-compose-view=pick]');
          const seg = s.querySelector('[data-compose-pill]');
          return { title: s.querySelector('.cmp-pick-title').textContent, pill: [...seg.querySelectorAll('button')].map(b => [b.textContent, b.getAttribute('aria-pressed')]),
            drafts: [...s.querySelectorAll('[data-compose-list=drafts] .gal-tile')].map(t => [t.tagName, t.getAttribute('data-pick-draft'), t.querySelector('b').textContent, t.querySelector('.gal-when').textContent]),
            focus: document.activeElement.textContent.trim() }; }""")
        check("Yours opens \"Use one you made\": Back, its title, the one pill Drafts | Drawings with Drafts pressed, and your"
              " drafts, newest first, each a button with its title and \"Pad · saved just now\", none of anybody else's",
              pick["title"] == "Use one you made" and pick["pill"] == [["Drafts", "true"], ["Drawings", "false"]]
              and pick["drafts"] == [["BUTTON", d_new, "A snail for Theo", "Pad · saved just now"],
                                     ["BUTTON", d_old, "Pip at the window", "Pad · saved just now"]]
              and pick["focus"] == "Back",
              json.dumps(pick)[:600])
        tap(pg, "#composeSheet [data-compose-pill] button[data-pick=drawings]")
        pg.wait_for_timeout(1200)
        first = pg.evaluate("""() => ({ ids: [...document.querySelectorAll('#composeSheet [data-compose-list=drawings] [data-pick-drawing]')].map(t => t.getAttribute('data-pick-drawing')),
          tags: [...new Set([...document.querySelectorAll('#composeSheet [data-compose-list=drawings] .gal-tile')].map(t => t.tagName))],
          more: !document.querySelector('#composeSheet [data-compose-more]').hidden,
          drafts: document.querySelector('#composeSheet [data-compose-list=drafts]').hidden,
          pill: [...document.querySelectorAll('#composeSheet [data-compose-pill] button')].map(b => b.getAttribute('aria-pressed')) })""")
        tap(pg, "#composeSheet [data-compose-more]")
        pg.wait_for_timeout(1200)
        every = pg.evaluate("""() => ({ ids: [...document.querySelectorAll('#composeSheet [data-compose-list=drawings] [data-pick-drawing]')].map(t => t.getAttribute('data-pick-drawing')),
          more: !document.querySelector('#composeSheet [data-compose-more]').hidden })""")
        mine = set(extra) | {loose, hidden}
        never = {in_post, theirs, (face or {}).get("face")} | {r[0] for r in ana_cm}
        check("Drawings: your drawings shared outside a post, newest first, the one kept to its link too, as the Gallery's"
              " tiles, each a button; never your post's drawing, your face, your drawing answer, or anybody else's; 24 a"
              " page, Load more bringing the rest",
              first["tags"] == ["BUTTON"] and len(first["ids"]) == 24 and first["more"] and first["drafts"]
              and first["pill"] == ["false", "true"] and set(every["ids"]) == mine and len(every["ids"]) == 26
              and not every["more"] and not (never & set(every["ids"])) and every["ids"][:2] == [extra[-1], extra[-2]],
              f"first page {len(first['ids'])} {first['tags']} more {first['more']}; all {len(every['ids'])}, the right ones"
              f" {set(every['ids']) == mine}, any never {never & set(every['ids'])}; face {face_st} answer {st_c}/{ana_answer_st}")
        tap(pg, f"#composeSheet [data-pick-drawing='{loose}']")
        pg.wait_for_timeout(1400)
        got = pg.evaluate(SHEET)
        state = pg.evaluate(STATE)
        edit = pg.evaluate("() => document.querySelector('[data-compose-edit]').getClientRects().length")
        check("a drawing picked is attached as it is: the words' view back, the drawing PLAYING in the sheet's player, no"
              " Edit drawing (it is posted as it is), Remove ready (focused), Post lit",
              got["views"] == ["write"] and got["att"] == {"kind": "skribl", "id": loose} and state == "playing"
              and edit == 0 and got["focus"] == "Remove"
              and pg.evaluate("() => document.querySelector('[data-compose-post]').getAttribute('aria-disabled')") == "false",
              f"views {got['views']}; attached {got['att']}; player {state}; Edit shown {edit}; focus {got['focus']}")
        tap(pg, "#composeSheet [data-compose-remove]")
        pg.wait_for_timeout(400)
        yours(pg)
        tap(pg, f"#composeSheet [data-pick-draft='{d_new}']")
        fr = editor_frame(pg, "skribl-pad")
        if fr:
            try:
                fr.wait_for_function("() => typeof strokes !== 'undefined' && strokes.length > 0", timeout=10000)
            except Exception:
                pass
        opened = pg.evaluate("""() => ({ src: document.querySelector('#composePad iframe').getAttribute('src'),
          pad: !document.getElementById('composePad').hidden })""")
        ink = fr.evaluate("() => typeof strokes !== 'undefined' ? strokes.length : null") if fr else None
        if fr:
            fr.click("#composeCloseBtn")
            pg.wait_for_timeout(700)
        under = pg.evaluate(SHEET)
        check("a draft picked opens in the editor that made it, over the sheet, the draft on its canvas (?draft=<id>, its"
              " 52 points); closing the editor is back in the picker",
              opened["pad"] and opened["src"].endswith("draft=" + d_new) and ink == 52 and under["views"] == ["pick"]
              and under["att"] is None,
              f"opened {opened}; ink {ink}; after closing it, views {under['views']}, attached {under['att']}")
        tap(pg, f"#composeSheet [data-pick-draft='{d_new}']")
        pg.wait_for_timeout(1500)
        fr = editor_frame(pg, "skribl-pad")
        if fr:
            try:
                fr.wait_for_function("() => typeof strokes !== 'undefined' && strokes.length > 0", timeout=10000)
            except Exception:
                pass
            pg.wait_for_timeout(400)
            fr.click("#postBtn")
            pg.wait_for_timeout(700)
            fr.click("#postSubmitBtn")
            pg.wait_for_timeout(1500)
        got = pg.evaluate(SHEET)
        state = pg.evaluate(STATE)
        close_ctx(ctx, pg)
        check("Add to post attaches the draft, PLAYING in the sheet's player, the words' view back, Edit drawing ready",
              got["att"] == {"kind": "payload", "id": None} and got["views"] == ["write"] and state == "playing"
              and got["focus"] == "Edit drawing",
              f"attached {got['att']}; views {got['views']}; player {state}; focus {got['focus']}")
        asked = {}
        for who_, path in ((None, "/social/make/yours?tab=drafts"), (ana, "/social/make/yours?tab=nope"),
                           (ben, "/social/make/yours?tab=drafts"), (ben, "/social/make/yours?tab=drawings")):
            if who_ is None:
                try:
                    with urllib.request.urlopen(BASE + path, timeout=20) as r:
                        asked["nobody"] = r.status
                except urllib.error.HTTPError as e:
                    asked["nobody"] = e.code
            else:
                c2, p2 = browser_as(b, who_)
                go(p2, "/social/explore")
                asked[f"{who_.handle} {path[-6:]}"] = p2.evaluate("""async (u) => { const r = await fetch(u, { credentials: 'same-origin' });
                  const j = await r.json().catch(() => ({})); return [r.status, (j.html || '').match(/data-pick-(?:draft|drawing)="[^"]+"/g) || []]; }""", path)
                close_ctx(c2, p2)
        bens = asked.get("ben drafts", [0, []])[1] + asked.get("ben awings", [0, []])[1]
        check("its address is yours alone: nobody signed in is refused (401), a list it does not have is a 400, and Ben"
              " asking gets his draft and his drawing, nothing of Ana's",
              asked.get("nobody") == 401 and asked.get("ana b=nope", [0])[0] == 400
              and sorted(bens) == sorted([f'data-pick-draft="{x}"' for x in [r[0] for r in db(
                  "select public_id from skribl_drafts where title = ?", ("Ben's own draft",))]]
                  + [f'data-pick-drawing="{theirs}"']),
              json.dumps(asked)[:500])

    # ------------------------------------------------------------------ 6
    if part(6, "one drawing, one conversation: its hearts and comments move onto the post, its page sends people there"):
        cy = someone(b, "cyra", "Cyra Moreau")
        dee = someone(b, "dee", "Dee Park")
        eli = someone(b, "eli", "Eli Stone")
        sid = cy.skribl("A slow snail", "public", seed=1)
        dee.pg.goto(BASE + "/social/b/" + sid)
        dee.pg.wait_for_timeout(400)
        like_st = dee.api("POST", f"/social/b/{sid}/like", {"liked": True, "at_ms": 900})[0]
        c_st, c_j = dee.api("POST", f"/social/b/{sid}/comments", {"words": "Love the shell."})
        eli.pg.goto(BASE + "/social/b/" + sid)
        eli.pg.wait_for_timeout(300)
        a_st = eli.api("POST", f"/social/b/{sid}/comments", {"words": "Same!", "answer_to": (c_j or {}).get("comment")})[0]
        e_like = eli.api("POST", f"/social/b/{sid}/like", {"liked": True})[0]
        before_likes = db("select id, person_id, at_ms, created_at, owner_id from social_likes where drawing_id = ? order by id", (sid,))
        before_cms = db("select id, person_id, parent_id, words, created_at, owner_id from social_comments where drawing_id = ? order by id", (sid,))
        # Cy has seen Activity since: the dot is dark.
        go(cy.pg, "/social/activity", 600)
        skribls_before = db("select count(*) from skribl_posts")[0][0]
        ctx, pg = browser_as(b, cy)
        go(pg, "/social/explore")
        open_composer(pg)
        yours(pg, which="drawings")
        tap(pg, f"#composeSheet [data-pick-drawing='{sid}']")
        pg.wait_for_timeout(1200)
        pg.fill("#composeSheet [data-compose-words]", "A slow snail for a slow Saturday.")
        with pg.expect_navigation(timeout=30000):
            tap(pg, "#composeSheet [data-compose-post]")
        pg.wait_for_timeout(1000)
        url = pg.evaluate("() => location.pathname")
        pid = url.rsplit("/", 1)[-1]
        row = db("select id, skribl_id, words, gallery_hidden_at from social_posts where public_id = ?", (pid,))
        post_id = row[0][0] if row else None
        after_likes = db("select id, person_id, at_ms, created_at, owner_id from social_likes where post_id = ? order by id", (post_id,))
        after_cms = db("select id, person_id, parent_id, words, created_at, owner_id from social_comments where post_id = ? order by id", (post_id,))
        left_on = db("select (select count(*) from social_likes where drawing_id = ?) + (select count(*) from social_comments where drawing_id = ?)", (sid, sid))[0][0]
        check("an older drawing posted through Yours is the post's drawing, nothing new made in Skribl; its two hearts (the"
              " moment 0:00.9 kept), its comment and the answer under it are the post's now, each its person, its time,"
              " its owner and its answer as they were, and none is left on the drawing",
              url.startswith("/social/p/") and row and row[0][1] == sid and row[0][2] == "A slow snail for a slow Saturday."
              and db("select count(*) from skribl_posts")[0][0] == skribls_before
              and like_st == 200 and e_like == 200 and c_st == 200 and a_st == 200
              and len(before_likes) == 2 and after_likes == before_likes
              and len(before_cms) == 2 and after_cms == before_cms and left_on == 0,
              f"url {url}; row {row}; skribls {skribls_before} -> {db('select count(*) from skribl_posts')[0][0]};"
              f" likes {before_likes} -> {after_likes}; comments {len(before_cms)} -> {len(after_cms)}; left {left_on}")
        page = pg.evaluate("""() => ({ said: [...document.querySelectorAll('[data-comments] .cm-words')].map(w => w.textContent.trim()),
          count: (document.getElementById('commentsTitle') || {}).innerText })""")
        close_ctx(ctx, pg)
        old = {}
        for who_ in (dee, None):
            req = urllib.request.Request(BASE + "/social/b/" + sid,
                                         headers={"Cookie": "; ".join(f"{c['name']}={c['value']}" for c in who_.ctx.cookies(BASE))} if who_ else {})

            class _No(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **kw):
                    return None
            try:
                urllib.request.build_opener(_No).open(req, timeout=20)
                old[who_.handle if who_ else "nobody"] = None
            except urllib.error.HTTPError as e:
                old[who_.handle if who_ else "nobody"] = [e.code, e.headers.get("Location")]
        refused = [dee.api("POST", f"/social/b/{sid}/like", {"liked": False})[0],
                   dee.api("POST", f"/social/b/{sid}/comments", {"words": "Late"})[0]]
        check("the post's page holds the conversation (Dee's comment, Eli's answer, 2 comments); the drawing's old page sends"
              " Dee and nobody signed in to the post (a redirect), and its old like and comment addresses take nothing new",
              "Love the shell." in page["said"] and "Same!" in page["said"] and (page["count"] or "").strip().startswith("Comments")
              and "2" in (page["count"] or "")
              and all(v and v[0] in (302, 303) and v[1] and v[1].endswith(url) for v in old.values()) and refused == [404, 404],
              f"page {page}; old page {old}; old addresses {refused}")
        tile = urllib.request.urlopen(BASE + "/social/explore", timeout=20).read().decode()
        tiles_of = re.findall(r'<a class="gal-tile" href="([^"]+)"[^>]*aria-label="([^"]*)"', tile)
        ours = [t for t in tiles_of if t[0] == url or t[0].endswith("/b/" + sid)]
        check("the Gallery shows it once, as the post, with the one conversation's counts (2 likes, 2 comments)",
              len(ours) == 1 and ours[0][0] == url and "2 likes" in ours[0][1] and "2 comments" in ours[0][1],
              f"{ours}")
        actx, apg = browser_as(b, cy)
        go(apg, "/social/explore")
        dot = apg.evaluate("() => (document.querySelector('a[data-activity]') || {}).getAttribute ? document.querySelector('a[data-activity]').getAttribute('aria-label') || 'Activity' : null")
        go(apg, "/social/activity")
        links = apg.evaluate("() => [...document.querySelectorAll('a.act-row')].map(a => a.getAttribute('href')).filter(Boolean)")
        close_ctx(actx, apg)
        check("Activity names the post now: the rows for Dee's and Eli's words open the post's page, none the drawing's"
              " old one; nothing is new again (the bell's dot stays dark, the times kept)",
              any(l.startswith(url) for l in links) and not any("/social/b/" in l for l in links)
              and dot in ("Activity",),
              f"links {links}; the bell says {dot!r}")
        # One kept to its link (the eye's hidden): posted, it stays out of the Gallery.
        sid2 = cy.skribl("Kept to its link", "unlisted", seed=2)
        st2, j2 = cy.api("POST", "/social/posts", {"words": "", "skribl": sid2})
        hid = db("select gallery_hidden_at from social_posts where skribl_id = ?", (sid2,))
        gal = urllib.request.urlopen(BASE + "/social/explore", timeout=20).read().decode()
        check("one kept to its link (hidden from the Gallery) stays hidden from it as a post, as the eye said",
              st2 == 200 and hid and hid[0][0] is not None and (j2 or {}).get("go", "?") not in gal and sid2 not in gal,
              f"{st2} {j2}; hidden {hid}")
        # THE SAME TRANSACTION: a move that fails takes the post with it.
        sid3 = cy.skribl("Moved or nothing", "public", seed=3)
        dee.pg.goto(BASE + "/social/b/" + sid3)
        dee.pg.wait_for_timeout(300)
        dee.api("POST", f"/social/b/{sid3}/like", {"liked": True})
        dee.api("POST", f"/social/b/{sid3}/comments", {"words": "Wait for it"})
        db("create trigger composer_no_move before update on social_likes begin select raise(abort, 'no move'); end")
        try:
            st3, j3 = cy.api("POST", "/social/posts", {"words": "Half?", "skribl": sid3})
        finally:
            db("drop trigger composer_no_move")
        stayed = db("select (select count(*) from social_posts where skribl_id = ?), (select count(*) from social_likes where drawing_id = ?),"
                    " (select count(*) from social_comments where drawing_id = ?)", (sid3, sid3, sid3))[0]
        st4, j4 = cy.api("POST", "/social/posts", {"words": "Whole", "skribl": sid3})
        moved = db("select (select count(*) from social_likes where drawing_id = ?), (select count(*) from social_comments where drawing_id = ?)", (sid3, sid3))[0]
        check("in the same transaction as the post: a move refused by the database leaves no post and nothing moved (the"
              " comment still on the drawing); asked again it all goes, together",
              st3 >= 500 and stayed == (0, 1, 1) and st4 == 200 and moved == (0, 0),
              f"refused {st3} {j3}; then post, likes, comments {stayed}; again {st4}, left on the drawing {moved}")
        # Guards.
        st_post, j_post = cy.api("POST", "/social/posts", {"words": "", "skribl": sid})
        mine_d = eli.skribl("Eli's", "public", seed=5)
        g = {"somebody else's": cy.api("POST", "/social/posts", {"words": "", "skribl": mine_d}),
             "in a post": (st_post, j_post),
             "beside a new one": cy.api("POST", "/social/posts", {"words": "", "skribl": sid2, "payload": drawing()}),
             "no token": cy.api("POST", "/social/posts", {"words": "", "skribl": sid}, token=False),
             "nothing": cy.api("POST", "/social/posts", {"words": "", "skribl": "nope"})}
        cy.pg.goto(BASE + "/social/@cyra")
        cy.pg.wait_for_timeout(300)
        fst, fj = cy.api("POST", "/social/you/face", {"payload": drawing(seed=9)})
        g["a face"] = cy.api("POST", "/social/posts", {"words": "", "skribl": (fj or {}).get("face")})
        n_st, n_j = cy.api("POST", f"/social/p/{pid}/comments", {"words": "", "payload": drawing(seed=6)})
        cm_sk = db("select skribl_id from social_comments where public_id = ?", ((n_j or {}).get("comment"),))
        g["a comment's drawing"] = cy.api("POST", "/social/posts", {"words": "", "skribl": cm_sk[0][0] if cm_sk else "x"})
        try:
            req = urllib.request.Request(BASE + "/social/posts", data=json.dumps({"words": "", "skribl": sid}).encode(),
                                         method="POST", headers={"Content-Type": "application/json", "Origin": BASE})
            urllib.request.urlopen(req, timeout=20)
            g["nobody"] = (200, None)
        except urllib.error.HTTPError as e:
            g["nobody"] = (e.code, None)
        want = {"somebody else's": (404, "drawing_gone"), "in a post": (409, "drawing_posted"),
                "beside a new one": (400, "one_drawing"), "no token": (403, "stale"), "nothing": (404, "drawing_gone"),
                "a face": (404, "drawing_gone"), "a comment's drawing": (404, "drawing_gone"), "nobody": (403, None)}
        got_g = {k: (v[0], (v[1] or {}).get("error") if isinstance(v[1], dict) else None) for k, v in g.items()}
        check("its guards: somebody else's drawing, nothing by that id, a face and a comment's drawing are as gone as one"
              " never made; one in a post already is said so (409); a drawing beside a new one is refused; no token, and"
              " nobody, are refused; posts made: none of these",
              got_g == want and db("select count(*) from social_posts where skribl_id = ?", (mine_d,))[0][0] == 0,
              json.dumps(got_g))

    # ------------------------------------------------------------------ 7
    if part(7, "every word at 4.5:1 on what is painted behind it, 44px, 16px: empty, a drawing, Yours; phone and desk, light and dark"):
        fay = someone(b, "fay", "Fay Quinn")
        fay.draft("A snail for Theo", seed=3)
        sid = fay.skribl("A slow snail", "public", seed=1)
        out = {}
        for screen in ("phone", "desk"):
            for scheme in ("light", "dark"):
                ctx, pg = browser_as(b, fay, screen, scheme)
                go(pg, "/social/explore")
                open_composer(pg, screen)
                out[f"{screen} {scheme} empty"] = pg.evaluate(CENSUS, "#composeSheet .make-sheet")
                yours(pg, screen)
                out[f"{screen} {scheme} drafts"] = pg.evaluate(CENSUS, "#composeSheet .make-sheet")
                tap(pg, "#composeSheet [data-compose-pill] button[data-pick=drawings]", screen)
                pg.wait_for_timeout(1000)
                out[f"{screen} {scheme} drawings"] = pg.evaluate(CENSUS, "#composeSheet .make-sheet")
                tap(pg, f"#composeSheet [data-pick-drawing='{sid}']", screen)
                pg.wait_for_timeout(1200)
                pg.fill("#composeSheet [data-compose-words]", "A slow snail for a slow Saturday.")
                pg.evaluate("() => document.activeElement.blur()")
                pg.wait_for_timeout(300)
                out[f"{screen} {scheme} drawing"] = pg.evaluate(CENSUS, "#composeSheet .make-sheet")
                close_ctx(ctx, pg)
        bad = {k: {x: v[x] for x in ("low", "small", "fields") if v and v[x]} for k, v in out.items()
               if not v or v["low"] or v["small"] or v["fields"] or v["read"] < 5}
        check("every word in the composer reads 4.5:1 or more on what is painted behind it, every control is 44px, every"
              " text field 16px: empty, with words and a drawing, Yours' Drafts and Drawings; phone and desk, light and"
              " dark (the dim Post, an inactive control, aside)",
              len(out) == 16 and not bad,
              f"read {sum(v['read'] for v in out.values() if v)} words, lowest {min((v['lowest'] for v in out.values() if v), default=None)};"
              f" {json.dumps(bad)[:900]}")

    # ------------------------------------------------------------------ 8
    if part(8, "no page errors, no console errors, no CSP violations"):
        for who in list(_people.values()):
            try:
                ERRS.extend(f"csp: {v}" for v in who.pg.evaluate("() => window.__csp || []"))
            except Exception:
                pass
        check("no page errors, no console errors and no CSP violations on the composer's pages", not ERRS, "; ".join(ERRS[:4]))

    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1][:60] for r in bad)))
sys.exit(1 if bad else 0)
