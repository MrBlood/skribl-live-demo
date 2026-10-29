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


def post(base):
    """A drawing with a caption, through the API, as the editors post one."""
    pts, n = [], 300
    for i in range(n):
        a, r = (i / n) * math.pi * 6, 20 + (i / n) * 200
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7, "color": "#7c5cff",
                    "size": 7, "t": i * 20, "erase": False, "start": i == 0})
    body = {"title": "Window cat", "caption": CAPTION, "schemaVersion": 2, "visibility": "public",
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}, "frames": [{"strokes": pts, "strokeGroups": [n]}]}
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
                    pg.click("a.player-home")
                    try:
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
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:                                       # noqa: BLE001
        proc.kill()

summarise_and_exit()
