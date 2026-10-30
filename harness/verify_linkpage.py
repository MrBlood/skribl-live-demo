#!/usr/bin/env python3
"""The link page: the way back to the site, and the caption where people look.

THE OWNER, on the posting mock, "all yes": the link page's way back, a small
"‹ skribls.net" at the top, shown only when the site has named its home; and
the caption featured, "a size up in the page's ink" under a title a step up.

WHAT IS ASKED, AND HOW IT IS READ
  * THE WAY BACK, on a server of this suite's own whose host named its home
    (SKRIBL_HOME_URL / SKRIBL_HOME_LABEL, create_blueprint's home_url): one
    link, named "Back to skribls.net", saying the site's name, to the address
    the host gave, opening in the whole tab (_top, so a host that frames the
    page goes home whole). Painted at the top left (elementFromPoint, never a
    rect), 36px with a 44px tap, light and dark, phone and desk, and over
    nothing: not the drawing, the title or the caption, on a phone as small
    as an iPhone SE. Pressed, it goes there. The drawing's own full screen,
    and the page-filling fallback where the API is missing, cover it.
  * ITS WORDS read 7:1 against what is painted behind them (the two-inks rule
    for words off the brand purple), light and dark.
  * STANDALONE (the shared server, no home named): no way back at all.
  * THE CAPTION: 17px in the page's own ink (the title's colour, not the
    secondary grey it was), painted and whole; the title 21px at 800; on a
    phone turned on its side, 14 and 17. It reads 7:1, light and dark.
"""
import io
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = Path(__file__).resolve().parents[1]
HOME_URL, HOME_LABEL = "https://skribls.net/home", "skribls.net"
CAPTION = "She sits there every morning and tells the birds what she thinks of them."
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the link page has a way back.")
    raise SystemExit(77)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
SE = dict(viewport={"width": 375, "height": 667}, device_scale_factor=2, is_mobile=True, has_touch=True)
SIDE = dict(viewport={"width": 874, "height": 402}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)


def post(base, caption=CAPTION, flip=False):
    """A drawing with a caption, through the API, as the editors post one; a
    Flip of two pages when asked."""
    pts, n = [], 300
    for i in range(n):
        a, r = (i / n) * math.pi * 6, 20 + (i / n) * 200
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7, "color": "#7c5cff",
                    "size": 7, "t": i * 20, "erase": False, "start": i == 0})
    body = {"title": "Window cat", "caption": caption, "schemaVersion": 2, "visibility": "public",
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}, "frames": [{"strokes": pts, "strokeGroups": [n]}]}
    if flip:
        body.update(playbackMode="flip", fps=8, frames=[{"strokes": pts[:150], "strokeGroups": [150]},
                                                         {"strokes": pts, "strokeGroups": [n]}])
    req = urllib.request.Request(base + "/api/skribls", method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())["url"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def worst(pg, sel, scale):
    """The word's ink against what is painted behind it, at nine points of its
    text's box, the words hidden for the photograph."""
    box = pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null;
      const r = document.createRange(); r.selectNodeContents(e); const b = r.getBoundingClientRect();
      const c = getComputedStyle(e).color.match(/[\\d.]+/g).map(Number);
      return { l: b.left, t: b.top, r: b.right, b: b.bottom, ink: c }; }""", sel)
    if not box:
        return None
    st = pg.add_style_tag(content="body * { color: transparent !important; }")
    pg.wait_for_timeout(80)
    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    st.evaluate("s => s.remove()")
    a = box["ink"][3] if len(box["ink"]) > 3 else 1
    out = None
    for i in range(3):
        for j in range(3):
            x = int((box["l"] + (box["r"] - box["l"]) * (i + .5) / 3) * scale)
            y = int((box["t"] + (box["b"] - box["t"]) * (j + .5) / 3) * scale)
            g = im.getpixel((x, y))
            ink = [box["ink"][k] * a + g[k] * (1 - a) for k in range(3)]
            v = ratio(ink, g)
            out = v if out is None else min(out, v)
    return out


PILL = """() => { const a = document.querySelector('a.player-home'); if (!a) return null;
  const r = a.getBoundingClientRect(), mid = (x, y) => { const h = document.elementFromPoint(x, y); return !!h && (h === a || a.contains(h)); };
  const box = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect();
    return [b.left, b.top, b.right, b.bottom]; };
  return { text: a.textContent.trim(), href: a.getAttribute('href'), target: a.getAttribute('target'), name: a.getAttribute('aria-label'),
    l: r.left, t: r.top, w: r.width, h: r.height, painted: mid(r.left + r.width / 2, r.top + r.height / 2),
    tap: mid(r.left + r.width / 2, r.top - 3.5) && mid(r.left + r.width / 2, r.bottom + 3.5) && mid(r.left - 3.5, r.top + r.height / 2),
    fixed: getComputedStyle(a).position === 'fixed', edge: getComputedStyle(a).borderTopWidth,
    canvas: box('#canvas'), title: box('#playerTitle'), caption: box('#playerCaption'), vw: innerWidth }; }"""


def apart(a, b):
    return bool(a and b) and (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def open_page(b, base, url, opts, theme):
    ctx = b.new_context(color_scheme=theme, **opts)
    pg = ctx.new_page()
    pg.goto(base + url, wait_until="load")
    pg.wait_for_function("() => !document.getElementById('playerShell').hidden", timeout=20000)
    pg.wait_for_timeout(900)
    return ctx, pg


# A SERVER OF THIS SUITE'S OWN, whose host named its home: the name is read at
# startup (app.py), so the shared server cannot be asked to have one.
port = free_port()
HOSTED = f"http://127.0.0.1:{port}"
env = dict(os.environ, DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/linkpage.db",
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000", SECRET_KEY="harness-linkpage",
           SKRIBL_HOME_URL=HOME_URL, SKRIBL_HOME_LABEL=HOME_LABEL)
subprocess.run([sys.executable, "-c", "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(port), "--no-reload"],
                        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", port), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    print("SUITE-SKIPPED: the hosted instance did not start.")
    raise SystemExit(77)

try:
    hosted_url, shared_url = post(HOSTED), post(BASE)
    # Where the page's own button goes, Pad and Flip, as the server wrote it.
    _cta = re.search(r'<a href="([^"]+)" data-flip="([^"]+)" class="player-cta">',
                     urllib.request.urlopen(BASE + shared_url, timeout=20).read().decode())
    PAD_PATH, FLIP_PATH = (_cta.group(1), _cta.group(2)) if _cta else ("?", "?")
    with sync_playwright() as p:
        b = p.chromium.launch()

        print("\nTHE WAY BACK, when the site has named its home")
        for theme in ("light", "dark"):
            for dev, opts in (("phone", PHONE), ("iPhone SE", SE), ("desk", DESK)):
                ctx, pg = open_page(b, HOSTED, hosted_url, opts, theme)
                k = pg.evaluate(PILL)
                where = f"{dev}, {theme}"
                if dev == "phone" and theme == "light":
                    check("named home: one link, named 'Back to skribls.net', saying the site's name, to the address the host gave, in the whole tab",
                          bool(k) and k["text"] == HOME_LABEL and k["href"] == HOME_URL and k["target"] == "_top"
                          and k["name"] == "Back to " + HOME_LABEL
                          and pg.evaluate("() => document.querySelectorAll('a.player-home').length") == 1, str(k)[:300])
                check(f"{where}: ...painted at the top left, a pill 36px tall with a 44px tap",
                      bool(k) and k["painted"] and k["tap"] and k["fixed"] and k["edge"] == "1px"
                      and 10 <= k["t"] <= 14 and 10 <= k["l"] <= 24 and abs(k["h"] - 36) < 0.6, str(k)[:300])
                check(f"{where}: ...over nothing: not the drawing, the title or the caption",
                      bool(k) and apart([k["l"], k["t"], k["l"] + k["w"], k["t"] + k["h"]], k["canvas"])
                      and apart([k["l"], k["t"], k["l"] + k["w"], k["t"] + k["h"]], k["title"])
                      and apart([k["l"], k["t"], k["l"] + k["w"], k["t"] + k["h"]], k["caption"]), str(k)[:300])
                if dev != "iPhone SE":
                    v = worst(pg, "a.player-home", opts.get("device_scale_factor", 1))
                    check(f"{where}: ...its words read 7:1 on what is painted behind them",
                          v is not None and v >= 7, f"{v and round(v, 2)}:1")
                if dev == "phone" and theme == "light":
                    # PRESSED, IT GOES THERE. The address is the host's; its
                    # page is stood in for, so nothing leaves this box.
                    pg.route(HOME_URL, lambda r: r.fulfill(status=200, content_type="text/html", body="<p>home</p>"))
                    try:                                    # a missing link fails the row, not the run
                        pg.click("a.player-home", timeout=5000)
                        pg.wait_for_url(HOME_URL, timeout=8000)
                    except Exception:                       # noqa: BLE001
                        pass
                    check("...and pressed, it goes to the site's home", pg.url == HOME_URL, pg.url)
                ctx.close()

        # THE DRAWING'S OWN FULL SCREEN COVERS IT: the real one (the API, which
        # headless Chromium honours from a click), and the page-filling state
        # where the API is missing (lib/immersive.js's .is-immersive-page).
        ctx, pg = open_page(b, HOSTED, hosted_url, DESK, "light")
        pg.wait_for_selector("#playerFullBtn:not([hidden])", timeout=10000)
        pg.click("#playerFullBtn")
        pg.wait_for_timeout(900)
        k = pg.evaluate(PILL)
        full = pg.evaluate("() => !!document.fullscreenElement")
        check("in the drawing's full screen, the way back is not painted over it",
              full and bool(k) and not k["painted"], f"full screen {full}; {str(k)[:160]}")
        pg.evaluate("() => document.exitFullscreen && document.fullscreenElement && document.exitFullscreen()")
        pg.wait_for_timeout(500)
        pg.evaluate("() => { document.querySelector('.canvas-wrap').classList.add('is-immersive-page'); }")
        pg.wait_for_timeout(300)
        k = pg.evaluate(PILL)
        check("...nor in the page-filling state where the full screen API is missing",
              bool(k) and not k["painted"], str(k)[:160])
        ctx.close()

        print("\nSTANDALONE: no home named")
        ctx, pg = open_page(b, BASE, shared_url, PHONE, "light")
        n = pg.evaluate("() => document.querySelectorAll('.player-home').length")
        cls = pg.evaluate("() => document.body.className")
        check("standalone, the link page has no way back, and keeps no room for one",
              n == 0 and "has-home" not in cls, f"{n} pill(s); body class {cls!r}")
        ctx.close()

        print("\nTHE CAPTION, FEATURED")
        CAP = """() => { const c = document.getElementById('playerCaption'), t = document.getElementById('playerTitle');
          const cs = getComputedStyle(c), ts = getComputedStyle(t), r = c.getBoundingClientRect();
          const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return { text: c.textContent.trim(), hidden: c.hidden, size: cs.fontSize, ink: cs.color, titleInk: ts.color,
                   titleSize: ts.fontSize, titleWeight: ts.fontWeight, painted: !!h && (h === c || c.contains(h)),
                   whole: c.scrollHeight <= c.clientHeight + 1 && r.bottom <= innerHeight }; }"""
        for theme in ("light", "dark"):
            for dev, opts in (("phone", PHONE), ("desk", DESK)):
                ctx, pg = open_page(b, BASE, shared_url, opts, theme)
                c = pg.evaluate(CAP)
                check(f"{dev}, {theme}: the caption is 17px in the page's own ink, the title's colour, painted and whole",
                      c["text"] == CAPTION and not c["hidden"] and c["size"] == "17px" and c["ink"] == c["titleInk"]
                      and c["painted"] and c["whole"], str(c))
                check(f"{dev}, {theme}: ...under a title of 21px at 800",
                      c["titleSize"] == "21px" and c["titleWeight"] == "800", str(c))
                v = worst(pg, "#playerCaption", opts.get("device_scale_factor", 1))
                check(f"{dev}, {theme}: ...and it reads 7:1 on the page", v is not None and v >= 7, f"{v and round(v, 2)}:1")
                ctx.close()
        ctx, pg = open_page(b, BASE, shared_url, SIDE, "light")
        c = pg.evaluate(CAP)
        check("a phone on its side: the caption 14px and the title 17px, a size up from 12 and 15, painted and whole",
              c["size"] == "14px" and c["titleSize"] == "17px" and c["painted"] and c["whole"], str(c))
        ctx.close()

        # ---- TWO LINES, AND YOUR OWN POST'S WAY BACK -------------------------
        # The owner, from a phone: a long title and caption made the drawing a
        # third smaller ("words never shrink the drawing": two lines and a
        # "more"), and "Make your own should be back to pad, cuz that's what it
        # does, and should" (Back to Pad on a post of your own).
        print("\nTWO LINES OF A LONG CAPTION, AND A MORE")
        LONGC = ("Every morning she sits in the one square of sun by the window and tells the birds what she "
                 "thinks of them, at length, and then she naps there until the sun has moved on and she has "
                 "to move with it, very slowly, as if it were her idea, while the dog watches from the doorway "
                 "and decides, again, that it is not worth the trouble of trying.")[:300]
        THREEC = ("Every morning she sits in the one square of sun by the window and tells the birds what she "
                  "thinks of them, at length, and then she naps there.")
        long_url, three_url = post(BASE, LONGC), post(BASE, THREEC)
        flip_url = post(BASE, THREEC, flip=True)
        WORDS = """() => { const c = document.getElementById('playerCaption'), m = document.getElementById('playerCapMore');
          const w = document.querySelector('.canvas-wrap').getBoundingClientRect(), cs = getComputedStyle(c);
          const lh = parseFloat(cs.lineHeight), r = c.getBoundingClientRect(), q = m.getBoundingClientRect();
          const at = (e, x, y) => { const h = document.elementFromPoint(x, y); return !!h && (h === e || e.contains(h)); };
          if (!m.hidden) m.scrollIntoView({ block: 'nearest' });
          return { text: c.textContent, lines: r.height / lh, more: !m.hidden && at(m, q.left + q.width / 2, q.top + q.height / 2),
                   moreH: q.height, word: m.textContent.trim(), expanded: m.getAttribute('aria-expanded'), name: m.getAttribute('aria-label'),
                   wrap: [w.left + scrollX, w.top + scrollY, w.width, w.height] }; }"""
        # The caption's height on every frame of the glide, and where the
        # drawing's box stands in the page (a column with room to spare is
        # centred, so a caption opening under it may move it: that must glide).
        GLIDE = """() => new Promise(done => { const c = document.getElementById('playerCaption'), hs = [], tops = [];
          const w = document.querySelector('.canvas-wrap');
          const t0 = performance.now(); (function f() { hs.push(c.getBoundingClientRect().height);
            tops.push(w.getBoundingClientRect().top + scrollY);
            if (performance.now() - t0 < 700) requestAnimationFrame(f); else done({ hs, tops }); })();
          document.getElementById('playerCapMore').click(); })"""

        def steps(hs):
            a, z = hs[0], hs[-1]
            span = abs(z - a) or 1
            mid = [h for h in hs if min(a, z) + 0.5 < h < max(a, z) - 0.5]
            big = max([abs(hs[i + 1] - hs[i]) / span for i in range(len(hs) - 1)] or [1])
            return len(mid), big, a, z

        same = lambda u, v: max(abs(x - y) for x, y in zip(u, v)) <= 0.5
        for dev, opts in (("phone", PHONE), ("desk", DESK)):
            ctx, pg = open_page(b, BASE, three_url, opts, "light")
            three = pg.evaluate(WORDS)
            ctx.close()
            ctx, pg = open_page(b, BASE, long_url, opts, "light")
            w = pg.evaluate(WORDS)
            check(f"{dev}: a long caption shows two lines of it and a painted 'more', 44px, its state and its word in its name",
                  w["text"] == LONGC and w["lines"] <= 2.05 and w["more"] and w["moreH"] >= 44 and w["word"] == "more"
                  and w["expanded"] == "false" and w["name"] == "Read more of the caption", str({k: w[k] for k in w if k != 'text'}))
            check(f"{dev}: ...and the drawing is as big as beside three lines: the words never shrink it",
                  same(w["wrap"], three["wrap"]), f"long {w['wrap']}, three lines {three['wrap']}")
            g = pg.evaluate(GLIDE)
            o = pg.evaluate(WORDS)
            n, big, a, z = steps(g["hs"])
            check(f"{dev}: 'more' opens the rest in place, and the drawing keeps its size",
                  o["lines"] > 3 and o["expanded"] == "true" and o["word"] == "less" and o["name"] == "Show less of the caption"
                  and same(o["wrap"][2:], w["wrap"][2:]), f"{o['lines']:.1f} lines, {o['word']!r}; box {o['wrap']} was {w['wrap']}")
            check(f"{dev}: ...gliding open, over several frames, none more than 40% of the way",
                  z > a + 20 and n >= 4 and big <= 0.4, f"{a:.0f} -> {z:.0f}px, {n} frames between, the biggest {big:.0%}")
            tn, tbig, ta, tz = steps(g["tops"])
            check(f"{dev}: ...and where the drawing moves with it, it glides too",
                  abs(tz - ta) <= 0.5 or (tn >= 4 and tbig <= 0.4),
                  f"its top {ta:.1f} -> {tz:.1f}, {tn} frames between, the biggest {tbig:.0%}")
            g = pg.evaluate(GLIDE)
            s2 = pg.evaluate(WORDS)
            n, big, a, z = steps(g["hs"])
            check(f"{dev}: 'less' glides it back to two lines",
                  s2["lines"] <= 2.05 and s2["expanded"] == "false" and s2["word"] == "more" and n >= 4 and big <= 0.4,
                  f"{s2['lines']:.1f} lines, {n} frames between, the biggest {big:.0%}")
            ctx.close()
        ctx = b.new_context(color_scheme="light", reduced_motion="reduce", **PHONE)
        pg = ctx.new_page()
        pg.goto(BASE + long_url, wait_until="load")
        pg.wait_for_function("() => !document.getElementById('playerShell').hidden", timeout=20000)
        pg.wait_for_timeout(900)
        n, big, a, z = steps(pg.evaluate(GLIDE)["hs"])
        check("Reduce Motion: 'more' just opens, no frame between", z > a + 20 and n == 0, f"{a:.0f} -> {z:.0f}px, {n} frames between")
        ctx.close()
        ctx, pg = open_page(b, BASE, shared_url, PHONE, "light")
        w = pg.evaluate(WORDS)
        check("a caption that fits in two lines has no 'more'", not w["more"] and w["lines"] <= 2.05, str({k: w[k] for k in w if k != 'text'}))
        ctx.close()
        for theme in ("light", "dark"):
            ctx, pg = open_page(b, BASE, long_url, PHONE, theme)
            v = worst(pg, "#playerCapMore", 2)
            check(f"{theme}: 'more' reads 7:1 on the page", v is not None and v >= 7, f"{v and round(v, 2)}:1")
            ctx.close()
        # THE BOX STANDS STILL while the drawing comes, a long caption and all:
        # its two lines and its "more" are laid out before the data is asked for.
        ctx = b.new_context(color_scheme="light", **PHONE)
        pg = ctx.new_page()
        held = []
        pid = long_url.rstrip("/").split("/")[-1]
        pg.route("**/api/skribls/" + pid, lambda r: held.append(r))
        pg.goto(BASE + long_url, wait_until="load")
        for _ in range(100):
            if held:
                break
            pg.wait_for_timeout(50)
        pg.wait_for_timeout(300)
        before = pg.evaluate("() => { const r = document.querySelector('.canvas-wrap').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        for r in held:
            r.continue_()
        pg.wait_for_function("() => document.body.classList.contains('player-ready')", timeout=20000)
        pg.wait_for_timeout(500)
        after = pg.evaluate(WORDS)["wrap"]
        check("phone: the box stands where it stood before the drawing came, a long caption and all",
              bool(held) and same(before, after), f"before {before}, after {after}")
        ctx.close()

        # ---- THE SMALLEST WORDS ----------------------------------------------
        # The owner, after the polish run: the last words under 12px go up, and
        # "made with" at the foot was this page's one, at 11px. Every word on
        # the page is read, at rest, with the controls showing after Play, and
        # with its More menu open, on a phone and a desk. A word counts when it
        # is laid out and not hidden or faded, which can only count too many,
        # never too few.
        print("\nTHE SMALLEST WORDS")
        SMALL = """() => { const out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          while (w.nextNode()) { const t = w.currentNode, s = t.textContent.trim(), el = t.parentElement;
            if (!s || !el || !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
            const r = el.getBoundingClientRect(), fs = parseFloat(getComputedStyle(el).fontSize);
            if (r.width >= 1 && r.height >= 1 && fs < 12) out.push(fs + 'px ' + JSON.stringify(s.slice(0, 30))); }
          return out; }"""
        for dev, opts in (("phone", PHONE), ("desk", DESK)):
            ctx, pg = open_page(b, HOSTED, hosted_url, opts, "light")
            rest = pg.evaluate(SMALL)
            brand = pg.evaluate("() => { const m = document.querySelector('.player-brand'); return m && getComputedStyle(m).fontSize; }")
            pg.click("#playerPlayBtn")
            pg.wait_for_timeout(700)
            playing = pg.evaluate(SMALL)
            pg.click("#playerMoreBtn")
            pg.wait_for_timeout(400)
            more = pg.evaluate(SMALL)
            check(f"{dev}: nothing on the link page is under 12px, at rest, playing or with More open ('made with' at 12px)",
                  brand == "12px" and not rest and not playing and not more,
                  f"made with {brand}; at rest {rest[:4]}; playing {playing[:4]}; More {more[:4]}")
            ctx.close()

        print("\nYOUR OWN POST'S WAY BACK")
        CTA = """() => { const a = document.querySelector('.player-cta');
          return { text: a.textContent.trim(), path: new URL(a.href).pathname, flip: new URL(a.dataset.flip, location.href).pathname,
                   pad: new URL(document.querySelector('.player-cta').getAttribute('href'), location.href).pathname }; }"""

        def mine(ctx, url, kind="pad"):
            pid = url.rstrip("/").split("/")[-1]
            ctx.add_init_script("try { localStorage.setItem('skribl_posted_v1', " + json.dumps(json.dumps([{
                "id": pid, "url": BASE + url, "title": "Window cat", "kind": kind, "pages": 1, "visibility": "public",
                "tok": None, "local": False, "has_audio": False, "canvas_w": 816, "canvas_h": 612, "at": 1700000000000}])) + "); } catch (e) {}")
        ctx = b.new_context(color_scheme="light", **PHONE)
        mine(ctx, three_url)
        pg = ctx.new_page()
        pg.goto(BASE + three_url, wait_until="load")
        pg.wait_for_function("() => !document.getElementById('playerShell').hidden", timeout=20000)
        pg.wait_for_timeout(600)
        k = pg.evaluate(CTA)
        check("a post this browser made: the button says 'Back to Pad' and goes to the Pad",
              k["text"] == "Back to Pad" and k["path"] == PAD_PATH, str(k))
        ctx.close()
        ctx = b.new_context(color_scheme="light", **PHONE)
        mine(ctx, flip_url, "flip")
        pg = ctx.new_page()
        pg.goto(BASE + flip_url, wait_until="load")
        pg.wait_for_function("() => !document.getElementById('playerShell').hidden", timeout=20000)
        pg.wait_for_timeout(600)
        k = pg.evaluate(CTA)
        check("...a Flip of its own: 'Back to Flip', to Flip", k["text"] == "Back to Flip" and k["path"] == FLIP_PATH, str(k))
        ctx.close()
        ctx, pg = open_page(b, BASE, three_url, PHONE, "light")
        k = pg.evaluate(CTA)
        check("someone else's post: 'Make your own Skribl', to the Pad",
              " ".join(k["text"].split()) == "\u2736 Make your own Skribl" and k["path"] == PAD_PATH, str(k))
        ctx.close()
        # THE REAL WAY: the Pad, a drawing, its Post sheet, Watch in place (as
        # on the Home Screen, lib/homescreen.js), then Back to Pad: a step back
        # to the Pad as it was left, its drawing on it.
        ctx = b.new_context(color_scheme="light", **PHONE)
        pg = ctx.new_page()
        pg.goto(BASE + PAD_PATH, wait_until="load")
        pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad", timeout=20000)
        pg.wait_for_timeout(800)
        pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide(); document.documentElement.setAttribute('data-skribl-app', ''); }")
        bx = pg.locator("#canvas").bounding_box()
        x0, y0 = bx["x"] + bx["width"] * 0.3, bx["y"] + bx["height"] * 0.4
        pg.mouse.move(x0, y0)
        pg.mouse.down()
        for i in range(1, 22):
            pg.mouse.move(x0 + i * bx["width"] * 0.02, y0 + (i % 5) * bx["height"] * 0.03, steps=2)
            pg.wait_for_timeout(16)
        pg.mouse.up()
        pg.wait_for_timeout(400)
        pg.evaluate("() => { if (typeof recording !== 'undefined' && recording) endRecordingTake(); }")
        pg.wait_for_timeout(300)
        drawn = pg.evaluate("() => strokes.length")
        pg.click("#postBtn")
        pg.wait_for_selector("#postSheet", state="visible")
        pg.wait_for_timeout(450)
        pg.fill("#postTitleInput", "Back again")
        pg.click("#postSubmitBtn")
        pg.wait_for_selector("#postDone:not([hidden])", timeout=20000)
        pg.wait_for_timeout(600)
        pg.click("#postWatchBtn")
        try:
            pg.wait_for_function("() => document.body.classList.contains('player-mode') && !document.getElementById('playerShell').hidden", timeout=20000)
        except Exception:                                   # noqa: BLE001
            pass
        pg.wait_for_timeout(600)
        k = pg.evaluate("() => (document.querySelector('.player-cta') || {}).textContent || ''").strip()
        try:
            pg.click(".player-cta", timeout=5000)
            pg.wait_for_function("() => !!window.__skriblBoot && !document.body.classList.contains('player-mode') && typeof strokes !== 'undefined'", timeout=20000)
        except Exception:                                   # noqa: BLE001
            pass
        pg.wait_for_timeout(800)
        back = pg.evaluate("() => ({ path: location.pathname, nav: (performance.getEntriesByType('navigation')[0] || {}).type,"
                           " strokes: typeof strokes !== 'undefined' ? strokes.length : -1 })")
        check("pressed after the Pad: a step back, to the Pad as it was left, its drawing on it",
              k == "Back to Pad" and back["path"] == PAD_PATH and back["nav"] == "back_forward" and back["strokes"] == drawn > 0,
              f"button {k!r}; {back}; drawn {drawn}")
        ctx.close()
        # With no Pad behind it (opened fresh), it opens the Pad.
        ctx = b.new_context(color_scheme="light", **PHONE)
        mine(ctx, three_url)
        pg = ctx.new_page()
        pg.goto(BASE + three_url, wait_until="load")
        pg.wait_for_function("() => !document.getElementById('playerShell').hidden", timeout=20000)
        pg.wait_for_timeout(600)
        try:
            pg.click(".player-cta", timeout=5000)
            pg.wait_for_function("(p) => location.pathname === p", arg=PAD_PATH, timeout=20000)
        except Exception:                                   # noqa: BLE001
            pass
        pg.wait_for_timeout(500)
        nav = pg.evaluate("() => ({ path: location.pathname, nav: (performance.getEntriesByType('navigation')[0] || {}).type })")
        check("...and with no Pad behind it, it opens the Pad", nav["path"] == PAD_PATH and nav["nav"] == "navigate", str(nav))
        ctx.close()
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:                                       # noqa: BLE001
        proc.kill()

summarise_and_exit()
