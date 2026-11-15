"""Demo people on the site, made through the site as a person uses it (the owner, Nov 15: "Make more users. Make sure
they have avatars and this time, make their drawings show on the screens ... Use all the functions that we have so I
can see them in use. Have some follow me").

WHY THROUGH THE SITE: drawings posted to the API by a script carry no still picture (only the Pad and Flip make one
as they post), so their tiles and players started blank; Rook's and Pip's did, until this tool drew them again. Here
every drawing is performed in the composer's Pad or Flip with real pen input (artdraw: pressure along each stroke, an
artist's order and pace), so the editor makes its picture as it does for anyone; every face is drawn in the face
sheet's Pad; and the rest (follows, likes, comments, an answer, a drawn answer, reposts, quotes, mentions, bookmarks)
goes through the site's own endpoints with each person's own token.

THE PEOPLE'S WAY IN is the owner's: an invite link per new person, and a sign-in link per person who exists already
("Help someone back in"), both from the owner's Settings, Invites and sign-in links (or `flask social invite` /
`flask social recover HANDLE` from a shell). Each person gets a passkey of their own (Chromium's virtual
authenticator), kept in STATE.json with their cookies, so a run can stop and go on.

    usage: demo_people.py BASE LINKS.json STATE.json [--only STEP,...] [--check]
      LINKS.json  {"join": [a link per new person, in NEW's order],
                   "recover": {"rook_test": link, "pip_test": link},
                   "owner": the owner's handle, "owner_posts": [the owner's post ids],
                   "old": {"rook_test": [drawing ids to delete], ...}}
      STATE.json  written as it goes: each person's cookies and PASSKEY, every id made. It is a key to their
                  accounts: keep it in a scratch folder, never in the repository.
      --only      some of: join, recover, faces, posts, old, follow, like, talk, share, save, owner
      --check     no changes: on BASE, every post made has its drawing's own picture (its poster answers 200, not
                  the blank canvas's redirect), every face is set, and the old drawings are gone
      DEMO_FAST=1 two posts and no faces, for a quick rehearsal

REHEARSE FIRST on a local site shaped like the live one (harness/bootstrap.sh; the links from `flask social invite`
and `flask social recover`), then run it on the live site with the owner's links. Make the sign-in links last: they
last an hour. The plan below is what this made on the live site on Nov 15: three new people (Mira, Juno, Theo),
Rook and Pip mended (faces, their four blank drawings drawn again and the blank ones deleted), each with posts, and
everyone following the owner. Change the plan for new people; ids already in STATE.json are not made twice.
"""
import json
import math
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import artdraw  # noqa: E402
import artworks  # noqa: E402
import flipworks  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/")
LINKS = json.load(open(sys.argv[2]))
STATE_PATH = sys.argv[3]
ONLY = None
if "--only" in sys.argv:
    ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(","))
LOCAL = BASE.startswith("http://localhost") or BASE.startswith("http://127.")
STATE = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {"people": {}, "made": {}}
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
S = artdraw.Stroke
INK, PURPLE, PAPER = artdraw.INK, artdraw.PURPLE, artdraw.PAPER
PINK = artworks.PINK
_n = [0]


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def save():
    json.dump(STATE, open(STATE_PATH, "w"), indent=1)


def step(name):
    return ONLY is None or name in ONLY


# ---- a person, with a passkey of their own -----------------------------------------------------------------------
class Person:
    def __init__(self, b, handle):
        self.handle = handle
        kw = {}
        if LOCAL:
            _n[0] += 1
            kw["extra_http_headers"] = {"X-Forwarded-For": f"10.88.{_n[0]}.9"}
        self.ctx = b.new_context(color_scheme="light", **PHONE, **kw)
        self.pg = self.ctx.new_page()
        self.errs = []
        self.pg.on("pageerror", lambda e: self.errs.append(str(e)[:200]))
        self.cdp = self.ctx.new_cdp_session(self.pg)
        self.cdp.send("WebAuthn.enable")
        self.aid = self.cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
            "protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True,
            "isUserVerified": True, "automaticPresenceSimulation": True}})["authenticatorId"]
        had = STATE["people"].get(handle)
        if had:
            for cr in had.get("creds", []):
                self.cdp.send("WebAuthn.addCredential", {"authenticatorId": self.aid, "credential": cr})
            self.ctx.add_cookies(had.get("cookies", []))

    def keep(self):
        had = STATE["people"].get(self.handle, {}).get("creds", [])
        try:
            creds = self.cdp.send("WebAuthn.getCredentials", {"authenticatorId": self.aid})["credentials"] or had
        except Exception:
            creds = had           # the passkey made at join or sign-in, kept then; it does not change after
        STATE["people"][self.handle] = {"cookies": self.ctx.cookies(), "creds": creds}
        save()

    def go(self, path, wait=900):
        self.pg.goto(BASE + path)
        self.pg.wait_for_load_state()
        self.pg.wait_for_timeout(wait)

    def api(self, method, path, body=None):
        if not self.pg.url.startswith(BASE + "/social"):
            self.go("/social/", 400)
        return self.pg.evaluate("""async ([m, p, b]) => {
          const t = (document.querySelector('meta[name="social-csrf"]') || {}).content || '';
          const r = await fetch(p, { method: m, credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Social-CSRF': t },
            body: b === null ? undefined : JSON.stringify(b) });
          let j = null; try { j = await r.json(); } catch (e) {}
          return [r.status, j]; }""", [method, path, body])

    def join(self, link, name):
        pg = self.pg
        pg.goto(link)
        pg.wait_for_function("() => { const c = document.querySelector('[data-link]');"
                             " return !!c && !c.classList.contains('is-checking'); }", timeout=20000)
        pg.fill("#joinName", name)
        pg.fill("#joinHandle", self.handle)
        pg.check("#joinAge")
        with pg.expect_navigation(timeout=30000):
            pg.click("form[data-passkey] button[type=submit]")
        pg.wait_for_timeout(800)
        self.keep()
        return pg.url

    def recover(self, link):
        pg = self.pg
        pg.goto(link)
        pg.wait_for_function("() => { const c = document.querySelector('[data-link]');"
                             " return !!c && !c.classList.contains('is-checking'); }", timeout=20000)
        with pg.expect_navigation(timeout=30000):
            pg.click("[data-passkey=recover]")
        pg.wait_for_timeout(800)
        self.keep()
        return pg.url


class InFrame:
    """artdraw's page, for an editor in an iframe: the pen goes in at the top page's own coordinates."""

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


def frame_of(pg, needle, extra="compose=1", timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        fr = next((f for f in pg.frames if needle in (f.url or "") and extra in (f.url or "")), None)
        if fr:
            try:
                fr.wait_for_function("() => !!(window.__skriblBoot && (window.__skriblBoot.pad || window.__skriblBoot.flip))",
                                     timeout=1000)
                return fr
            except Exception:
                pass
        pg.wait_for_timeout(250)
    return None


def fit(strokes, src=(816, 612), dst=(816, 612), pad=0.0):
    """The same drawing in another canvas: scaled to fit (keeping its shape), centred, its lines with it."""
    k = min(dst[0] * (1 - 2 * pad) / src[0], dst[1] * (1 - 2 * pad) / src[1])
    ox, oy = (dst[0] - src[0] * k) / 2, (dst[1] - src[1] * k) / 2
    out = []
    for st in strokes:
        n = S([(x * k + ox, y * k + oy) for x, y in st.pts], st.role, st.color, size=max(2.0, st.size * k),
              pace=st.pace, peak=st.peak, taper=st.taper, bend=st.bend, weight=st.weight, tool=st.tool,
              shape=st.shape, flat=st.flat, brush=st.brush)
        out.append(n)
    return out


def pen_ready(fr):
    fr.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); if (typeof setTool === 'function') setTool('pen');"
                " if (window.SkriblPressure) SkriblPressure.setEnabled(true); }")


def pad_setup(pg, fr, mirror=None):
    """The Pad as the examples are drawn (make_art.py): the 4:3 canvas the drawings are authored on, paper under them
    so their dark ink reads in both themes, the pen with pressure on, and Mirror where the drawing asks for it."""
    fr.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t && t.SIZES.find(s => s.label === '4:3').id;
        const b = id && document.querySelector(`#canvasSeg button[data-size='${id}']`); if (b) b.click(); }""")
    pg.wait_for_timeout(400)
    fr.evaluate(f"""() => {{ bgColor = '{PAPER}'; if (window.canvasWrap) canvasWrap.style.backgroundColor = bgColor;
        if (typeof updateVignette === 'function') updateVignette(); }}""")
    pen_ready(fr)
    fr.evaluate("(m) => { const b = document.querySelector('#mirrorSeg [data-mirror=\"' + m + '\"]'); if (b) b.click(); }",
                mirror or "off")
    pg.wait_for_timeout(300)


def end_take_and_add(pg, fr):
    if fr.evaluate("() => typeof recording !== 'undefined' && !!recording"):
        fr.click("#recordBtn", timeout=8000)
        pg.wait_for_timeout(500)
    fr.click("#postBtn", timeout=8000)
    pg.wait_for_timeout(900)
    label = fr.evaluate("() => (document.getElementById('postSubmitLabel') || {}).textContent")
    fr.click("#postSubmitBtn", timeout=8000)
    pg.wait_for_timeout(1800)
    return label


# ---- a face ---------------------------------------------------------------------------------------------------------
def draw_face(p, strokes, tempo=1.0, gaps=1.6):
    pg = p.pg
    p.go(f"/social/@{p.handle}", 900)
    pg.click("button[data-face-sheet]", timeout=8000)
    pg.wait_for_timeout(600)
    pg.click("#faceSheet [data-face-open]", timeout=8000)
    fr = frame_of(pg, "", "face=1")
    if fr is None:
        return "no Pad"
    lg = fr.evaluate("() => { const s = getCanvasLogicalSize(); return [s.width, s.height]; }")
    pen_ready(fr)
    artdraw.draw(InFrame(pg, fr), fit(strokes, dst=tuple(lg), pad=0.02), tempo=tempo, pause_tempo=gaps)
    pg.wait_for_timeout(500)
    end_take_and_add(pg, fr)
    try:
        pg.wait_for_function("""() => { const w = document.getElementById('faceSheet'), s = w && w.querySelector('[data-step=place]');
          return !!s && !s.hidden && w.classList.contains('is-open'); }""", timeout=20000)
        pg.wait_for_timeout(600)
        with pg.expect_navigation(timeout=30000):
            pg.click("#faceSheet [data-face-use]", timeout=8000)
    except Exception as exc:
        return f"no circle ({str(exc).splitlines()[0][:80]})"
    pg.wait_for_timeout(600)
    return "kept"


# ---- a post through the composer -----------------------------------------------------------------------------------
def compose(p, words, strokes=None, flip=None, tempo=1.0, gaps=1.6, mirror=None):
    pg = p.pg
    p.go("/social/", 1200)
    sent = {}
    try:
        pg.tap("nav.nav .tab-make")
        pg.wait_for_timeout(900)
        if strokes is not None or flip is not None:
            pg.tap("#composeSheet [data-compose-open=%s]" % ("flip" if flip else "pad"))
            fr = frame_of(pg, "flip" if flip else "skribl-pad")
            if fr is None:
                return None, "no editor"
            if flip:
                draw_flip(pg, fr, flip)
            else:
                pad_setup(pg, fr, mirror)
                artdraw.draw(InFrame(pg, fr), strokes, tempo=tempo, pause_tempo=gaps)
                pg.wait_for_timeout(500)
                if mirror:
                    fr.evaluate("() => { const b = document.querySelector('#mirrorSeg [data-mirror=\"off\"]'); if (b) b.click(); }")
            end_take_and_add(pg, fr)
        pg.fill("#composeSheet [data-compose-words]", words)
        pg.wait_for_timeout(400)
        with pg.expect_response(lambda r: r.request.method == "POST" and r.url.split("?")[0].endswith("/social/posts"),
                                timeout=60000) as got:
            pg.tap("#composeSheet [data-compose-post]")
        status = got.value.status
        # The page goes to the new post at once (its body is gone by then): its address is the answer.
        try:
            pg.wait_for_url("**/social/p/**", timeout=20000)
            sent["j"] = {"status": status, "post": pg.url.split("/social/p/")[1].split("?")[0].split("#")[0]}
        except Exception as exc:
            sent["j"] = {"status": status, "stayed": pg.url, "why": str(exc).splitlines()[0][:80]}
        pg.wait_for_timeout(1200)
    except Exception as exc:
        sent["j"] = {"stopped": str(exc).splitlines()[0][:160]}
    j = sent.get("j") or {}
    return j.get("post"), j


def draw_flip(pg, fr, spec):
    fr.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); }")
    # As the examples are drawn (make_flip.py): the 4:3 canvas, paper under it.
    fr.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t && t.SIZES.find(s => s.label === '4:3').id;
        const b = id && document.querySelector(`#canvasSeg button[data-size='${id}']`); if (b) b.click(); }""")
    pg.wait_for_timeout(400)
    fr.evaluate(f"() => {{ if (typeof setBg === 'function') setBg('{PAPER}'); }}")
    fr.evaluate(f"""() => {{ onion = true; onionDepth = 1; fps = {spec['fps']};
        if (window.SkriblPressure) SkriblPressure.setEnabled(true); if (typeof setTool === 'function') setTool('pen'); }}""")
    logical = fr.evaluate("() => [CW, CH]")
    src = (816, 612)
    draw = lambda strokes, seed: artdraw.draw(InFrame(pg, fr), fit(strokes, src, tuple(logical)), seed=seed,
                                              canvas="#pad", logical=logical, tempo=1.1, pause_tempo=1.6)
    n = len(spec["pages"])
    draw(spec["base"], 1)
    for _ in range(n - 1):
        fr.evaluate("() => addFrame(true)")
    pg.wait_for_timeout(300)
    for i in spec["order"]:
        if not spec["pages"][i]:
            continue
        fr.evaluate("i => go(i)", i)
        pg.wait_for_timeout(150)
        draw(spec["pages"][i], 10 + i)
    if spec.get("holds"):
        fr.evaluate("h => { for (const [i, n] of Object.entries(h)) frames[+i].hold = n; }",
                    {str(k): v for k, v in spec["holds"].items()})
    fr.evaluate("() => go(0)")
    pg.wait_for_timeout(400)


# ---- the drawings ---------------------------------------------------------------------------------------------------
def _arc(cx, cy, rx, ry, a0, a1, n=12):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def two_waves():
    """Rook's "Two waves": two long swells, the second one under the first, a dark line and a purple one."""
    def wave(y, amp, ph, x0=110, x1=706, n=34):
        return [(x0 + (x1 - x0) * k / n, y + amp * math.sin(ph + 2.6 * math.pi * k / n)) for k in range(n + 1)]
    return [S(wave(250, 46, 0.2), "gesture", INK, size=12, weight=[(0, 0.7), (0.5, 1.0), (1, 0.7)]),
            S(wave(368, 40, 1.1), "gesture", PURPLE, size=14, weight=[(0, 0.7), (0.5, 1.0), (1, 0.7)]),
            S(_arc(642, 168, 20, 20, 0, 360, 10), "accent", PINK, size=6)]


def hello_sun():
    """Rook's "Hello, sun": the hills first, then the sun coming up behind them, its rays flicked last."""
    hills = [(60, 470), (190, 404), (320, 446), (450, 380), (600, 432), (756, 392)]
    rays = []
    for a in range(200, 341, 20):
        r0, r1 = 118, 168
        rays.append(S([(408 + r0 * math.cos(math.radians(a)), 410 + r0 * math.sin(math.radians(a))),
                       (408 + r1 * math.cos(math.radians(a)), 410 + r1 * math.sin(math.radians(a)))],
                      "accent", PURPLE, size=8, taper=(0.05, 0.6)))
    return [S(hills, "gesture", INK, size=12, bend=0.3),
            S(_arc(408, 410, 92, 92, 192, 348, 16), "contour", PURPLE, size=14),
            S(_arc(408, 404, 44, 30, 200, 340, 10), "fill", PINK, size=10, taper=(0.02, 0.02))] + rays


def little_star():
    """Pip's "Little star": a five-point star in one go, a pink sparkle beside it, a smile in it."""
    pts = []
    for k in range(11):
        a = math.radians(-90 + 36 * k)
        r = 170 if k % 2 == 0 else 72
        pts.append((408 + r * math.cos(a), 318 + r * math.sin(a)))
    return [S(artworks._sharp(pts), "gesture", PURPLE, size=14, weight=[(0, 0.8), (0.5, 1.0), (1, 0.8)]),
            S([(384, 300), (386, 312)], "detail", INK, size=9),
            S([(432, 300), (434, 312)], "detail", INK, size=9),
            S(_arc(408, 340, 24, 14, 20, 160, 8), "detail", INK, size=7),
            S([(610, 150), (610, 210)], "accent", PINK, size=6),
            S([(580, 180), (640, 180)], "accent", PINK, size=6)]


def spiral_for_luck():
    """Pip's "A spiral for luck": one long spiral out from the middle, and a dot where it began."""
    pts = [(408 + (6 + 9.2 * t) * math.cos(t), 306 + (6 + 9.2 * t) * math.sin(t)) for t in [k * 0.32 for k in range(0, 88)]]
    return [S(pts, "gesture", PURPLE, size=12, weight=[(0, 0.5), (0.6, 1.0), (1, 0.8)]),
            S(_arc(408, 306, 9, 9, 0, 360, 8), "accent", INK, size=10)]


def portrait():
    """Juno's face, as an artist draws a friend: the face's outline in one sweep, the hair falling over it with a
    curl at each side, then the happy eyes, the nose, the smile, and the blush last. Three colours on the paper."""
    face = _arc(408, 330, 150, 182, 205, -25, 26)
    hair = [(250, 300), (262, 210), (318, 150), (408, 126), (500, 146), (556, 204), (568, 296)]
    fringe = [(300, 196), (352, 232), (408, 214), (462, 236), (520, 200)]
    curl_l = [(258, 300), (238, 352), (252, 402), (282, 392), (276, 362)]
    curl_r = [(560, 300), (580, 352), (566, 402), (536, 392), (542, 362)]
    return [S(face, "gesture", INK, size=16, weight=[(0, 0.8), (0.5, 1.0), (1, 0.8)]),
            S(hair, "contour", PURPLE, size=26, weight=[(0, 0.7), (0.5, 1.0), (1, 0.7)]),
            S(fringe, "form", PURPLE, size=18),
            S(curl_l, "form", PURPLE, size=16),
            S(curl_r, "form", PURPLE, size=16),
            S(_arc(350, 328, 24, 16, 200, 340, 8), "detail", INK, size=10),
            S(_arc(466, 328, 24, 16, 200, 340, 8), "detail", INK, size=10),
            S([(410, 352), (398, 388), (414, 392)], "detail", INK, size=7),
            S(_arc(408, 418, 46, 24, 20, 160, 10), "detail", INK, size=10),
            S(_arc(318, 392, 18, 10, 0, 700, 14), "fill", PINK, size=12),
            S(_arc(498, 392, 18, 10, 0, 700, 14), "fill", PINK, size=12)]


def little_snail():
    """Pip's drawn answer: a small snail, shell first."""
    shell = [(400 + (4 + 7 * t) * math.cos(t), 300 + (4 + 7 * t) * math.sin(t)) for t in [k * 0.4 for k in range(0, 34)]]
    return [S(shell, "gesture", PURPLE, size=12),
            S([(300, 392), (360, 396), (470, 394), (560, 380), (590, 330), (606, 300)], "contour", INK, size=11, bend=0.2),
            S([(596, 302), (592, 262)], "detail", INK, size=6),
            S([(608, 300), (622, 262)], "detail", INK, size=6)]


def run_answer_drawn(p, post, under, strokes):
    """A drawn answer under a comment, as the box sends one: Answer, Draw, Add, Post."""
    pg = p.pg
    p.go(f"/social/p/{post}", 1500)
    pg.evaluate("(id) => document.getElementById('c-' + id).scrollIntoView({ block: 'center' })", under)
    pg.wait_for_timeout(300)
    pg.click(f"#c-{under} > .cm-main [data-cm-answer]", timeout=10000)
    pg.wait_for_timeout(900)
    pg.click("[data-cm-open=pad]", timeout=8000)
    fr = frame_of(pg, "skribl-pad")
    if fr is None:
        return None
    pad_setup(pg, fr)
    artdraw.draw(InFrame(pg, fr), strokes, tempo=1.1, pause_tempo=1.6)
    pg.wait_for_timeout(400)
    end_take_and_add(pg, fr)
    with pg.expect_response(lambda r: r.request.method == "POST" and "/comments" in r.url, timeout=60000) as got:
        pg.click("[data-cm-post]", timeout=8000)
    try:
        return (got.value.json() or {}).get("comment")
    except Exception:
        return None


# ---- the plan --------------------------------------------------------------------------------------------------------
NEW = [("mira", "Mira Lopez"), ("juno", "Juno Park"), ("theo", "Theo Lind")]
FACES = {"mira": artworks.snail, "juno": portrait, "theo": artworks.cat, "rook_test": artworks.skull, "pip_test": artworks.pug}
OWNER = LINKS["owner"]
POSTS = [  # who, key, words, drawing (a function of the 816 x 612 Pad), or a Flip
    ("rook_test", "two_waves", "Two waves.", two_waves, None),
    ("rook_test", "hello_sun", "Hello, sun.", hello_sun, None),
    ("pip_test", "little_star", "Little star.", little_star, None),
    ("pip_test", "spiral", "A spiral for luck.", spiral_for_luck, None),
    ("mira", "snail", "A slow snail for a slow Saturday.", artworks.snail, None),
    ("theo", "cat", "Our cat, who will not sit still for a portrait.", artworks.cat, None),
    ("juno", "scene", "My first one here! Watch it draw itself.", artworks.scene, None),
    ("pip_test", "pug", "Pug, in one sitting. Watch at 4x.", artworks.pug, None),
    ("rook_test", "skull", "Skull study, outline first.", artworks.skull, None),
    ("theo", "footballer", f"Mid-kick. @{OWNER}, you're up next.", artworks.footballer, None),
    ("juno", "bounce", "My first Flip! A ball, a bounce, a squash.", None, flipworks.bounce),
    ("mira", "mirror", "Mirror on: one wing, and the other draws itself.", artworks.tool_mirror, None),
]


if os.environ.get("DEMO_FAST"):
    FACES = {}
    POSTS = [p_ for p_ in POSTS if p_[1] in ("snail", "scene", "bounce")]


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        people = {}
        # 1. In: three new people on the owner's invites; Rook and Pip on their sign-in links.
        for i, (h, name) in enumerate(NEW):
            p = Person(b, h)
            if h not in STATE["people"] and step("join"):
                say("join", h, p.join(LINKS["join"][i], name))
            people[h] = p
        for h in ("rook_test", "pip_test"):
            p = Person(b, h)
            if h not in STATE["people"] and step("recover"):
                say("recover", h, p.recover(LINKS["recover"][h]))
            people[h] = p
        # 2. Faces, drawn in the face sheet's Pad.
        if step("faces"):
            for h, fn in FACES.items():
                if STATE["made"].get(f"face:{h}"):
                    continue
                r = draw_face(people[h], fn())
                say("face", h, r)
                if r == "kept":
                    STATE["made"][f"face:{h}"] = True
                    save()
        # 3. Posts, drawn live in the composer.
        if step("posts"):
            for who, key, words, fn, flip in POSTS:
                if STATE["made"].get(key):
                    continue
                pid, j = compose(people[who], words, strokes=fn() if fn else None, flip=flip() if flip else None,
                                 mirror="vertical" if key == "mirror" else None)
                say("post", who, key, pid, "" if pid else str(j)[:160])
                if pid:
                    STATE["made"][key] = pid
                    save()
        M = STATE["made"]
        # 4. Rook's and Pip's old drawings, the ones without a picture, go.
        if step("old"):
            for h, ids in LINKS.get("old", {}).items():
                for sid in ids:
                    if M.get(f"gone:{sid}"):
                        continue
                    st = people[h].api("POST", f"/social/b/{sid}/delete", {})
                    say("old drawing", h, sid, st[0])
                    if st[0] in (200, 404):
                        M[f"gone:{sid}"] = st[0]
                        save()
        # 5. Everyone follows the owner, and some of each other.
        if step("follow"):
            for a, bb in [(h, OWNER) for h in people] + [("mira", "juno"), ("juno", "mira"), ("theo", "mira"), ("juno", "theo"),
                                                       ("rook_test", "pip_test"), ("pip_test", "rook_test"), ("pip_test", "mira"),
                                                       ("mira", "theo"), ("rook_test", "juno")]:
                st = people[a].api("POST", f"/social/@{bb}/follow", {"following": True})
                say("follow", a, bb, st[0])
        # 6. Likes.
        if step("like"):
            likes = {"mira": ["cat", "scene", "little_star", "bounce", "hello_sun"], "juno": ["snail", "cat", "pug", "two_waves"],
                     "theo": ["snail", "scene", "skull", "mirror", "spiral"], "rook_test": ["snail", "pug", "footballer", "bounce"],
                     "pip_test": ["snail", "cat", "scene", "footballer", "skull"]}
            for h, keys in likes.items():
                for k in keys:
                    if M.get(k):
                        st = people[h].api("POST", f"/social/p/{M[k]}/like", {"liked": True})
                        say("like", h, k, st[0])
        # 7. Comments, an answer, a drawn answer, mentions.
        if step("talk") and M.get("snail") and not M.get("talked"):
            c1 = people["rook_test"].api("POST", f"/social/p/{M['snail']}/comments", {"words": "The timing on this is perfect."})[1]
            c1 = (c1 or {}).get("comment")
            a1 = people["mira"].api("POST", f"/social/p/{M['snail']}/comments",
                                    {"words": "Thank you! I slowed the shell on purpose.", "answer_to": c1})[1]
            say("comment", c1, "answer", (a1 or {}).get("comment"))
            try:
                d1 = run_answer_drawn(people["pip_test"], M["snail"], c1, little_snail())
            except Exception as exc:
                d1 = f"stopped: {str(exc).splitlines()[0][:120]}"
            say("drawn answer", d1)
            if M.get("cat"):
                people["juno"].api("POST", f"/social/p/{M['cat']}/comments", {"words": "Ha, the tail! @mira, look at the whiskers."})
                people["pip_test"].api("POST", f"/social/p/{M['cat']}/comments", {"words": "Three whiskers each side. Perfect."})
            if M.get("scene"):
                people["theo"].api("POST", f"/social/p/{M['scene']}/comments", {"words": f"Welcome, @juno! @{OWNER}, look who's here."})
            if M.get("footballer"):
                people["mira"].api("POST", f"/social/p/{M['footballer']}/comments", {"words": "The follow-through!"})
            M["talked"] = True
            save()
        # 8. Reposts and a quote.
        if step("share") and not M.get("shared"):
            for h, k in (("juno", "cat"), ("pip_test", "snail"), ("theo", "bounce")):
                if M.get(k):
                    st = people[h].api("POST", f"/social/p/{M[k]}/repost", {"reposted": True})
                    say("repost", h, k, st[0])
            if M.get("scene"):
                st, j = people["mira"].api("POST", "/social/posts", {"words": "Welcome to Blooby, @juno! Look at that path.",
                                                                      "quote": M["scene"]})
                say("quote", st, (j or {}).get("post"))
                if st == 200:
                    M["quote"] = j.get("post")
            M["shared"] = True
            save()
        # 9. Bookmarks (private: each person's own Saved).
        if step("save"):
            for h, k in (("theo", "scene"), ("juno", "snail"), ("mira", "pug")):
                if M.get(k):
                    st = people[h].api("POST", f"/social/p/{M[k]}/bookmark", {"bookmarked": True})
                    say("bookmark", h, k, st[0])
        # 10. The owner's own posts: liked, a word with a mention on the newest, and a quote of it.
        if step("owner") and not M.get("owner_done"):
            posts_ = LINKS.get("owner_posts", [])
            for k, pid in enumerate(posts_):
                for h in (("mira", "juno", "theo", "rook_test", "pip_test") if k == 0 else ("mira", "theo", "pip_test")):
                    st = people[h].api("POST", f"/social/p/{pid}/like", {"liked": True})
                    say("like owner's", h, pid, st[0])
            for sid in LINKS.get("owner_drawings", []):
                for h in ("mira", "juno"):
                    st = people[h].api("POST", f"/social/b/{sid}/like", {"liked": True})
                    say("like owner's drawing", h, sid, st[0])
            if posts_:
                st = people["juno"].api("POST", f"/social/p/{posts_[0]}/comments",
                                        {"words": f"@{OWNER} this made my day. More please!"})
                say("comment on owner's", st[0])
                st, j = people["theo"].api("POST", "/social/posts", {"words": f"This is the one that got me drawing. Thanks, @{OWNER}!",
                                                                     "quote": posts_[0]})
                say("quote owner's", st, (j or {}).get("post"))
                if st == 200:
                    M["owner_quote"] = j.get("post")
            M["owner_done"] = True
            save()
        for h, p in people.items():
            p.keep()
            if p.errs:
                say("page errors", h, p.errs[:3])
        b.close()
    say("done", json.dumps(STATE["made"]))


def check():
    """On BASE, without changing anything: each post made shows its drawing's own picture, each face is set, and the
    old drawings are gone. (Its poster's answer is the instrument: 200 for a drawing's own picture, a redirect to the
    blank canvas for one posted without it; Rook's and Pip's old ones read the redirect before this tool ran.)"""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    op = urllib.request.build_opener(NoRedirect)

    def status(url):
        try:
            return op.open(urllib.request.Request(url), timeout=40).status
        except urllib.error.HTTPError as e:
            return e.code

    def text(url):
        return urllib.request.urlopen(url, timeout=40).read().decode("utf-8", "replace")
    bad = []
    for k_, v in STATE["made"].items():
        if not isinstance(v, str) or k_.startswith("gone"):
            continue
        html = text(BASE + f"/social/p/{v}")
        m = re.search(r'data-skribl="([A-Za-z0-9_-]*)"', html)    # the post's own drawing (its face's poster comes first)
        sid = m.group(1) if m and m.group(1) else None
        st = status(BASE + f"/s/{sid}/poster") if sid else None
        ok = st == 200 or (sid is None and k_ in ("quote", "owner_quote"))
        say(f"{k_:12} post {v} drawing {sid} poster {st} {'ok' if ok else 'BLANK'}")
        if not ok:
            bad.append(k_)
    for h in [h for h, _ in NEW] + ["rook_test", "pip_test"]:
        html = text(BASE + f"/social/@{h}")
        has = "Add your face" not in html and "skribl-face" in html
        say(f"face {h:10} {'set' if has else 'MISSING'}")
        if not has:
            bad.append("face " + h)
    for h, ids in LINKS.get("old", {}).items():
        for sid in ids:
            st = status(BASE + f"/api/skribls/{sid}")
            say(f"old {h} {sid} -> {st} {'gone' if st == 404 else 'STILL THERE'}")
            if st != 404:
                bad.append("old " + sid)
    say("ALL GOOD" if not bad else f"PROBLEMS: {bad}")
    return not bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    main()
