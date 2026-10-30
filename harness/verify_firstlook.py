#!/usr/bin/env python3
"""A long drawing's first look on the link page (the posting mock's 2b, B).

THE OWNER, "all yes" on the posting mock: "B, the picture at once, then
sharp". Before it, a two-hour piece's link page stood blank until its payload
had come and been painted (1.5 s here, 6.8 s on a phone at a phone's pace),
and the paint was one task in which nothing on the page could be touched.

WHAT IS ASKED, AND HOW IT IS READ
  * THE PAGE KNOWS (the route, read from the HTML): a Pad post's page carries
    its size, its title and caption in the shell, and its own picture. A
    Flip's, and a missing post's, carry none.
  * AT ONCE: the post's data is held back by the browser (a route), and on the
    page alone the picture is painted where the canvas is (a photograph of
    the box, since the picture takes no pointer), cropped to the drawing: the
    card's drawing edge to edge, none of its ground and none of its plate's
    ring. The title and caption are said, and the transport is laid out but
    not shown. Phone and desk.
  * NOTHING MOVES: the box stands where it stood before the data came once
    the drawing is in and whole, to the half pixel, phone and desk, short and
    long (the long one's line under the track is the one that wraps); and a
    phone turned while the drawing comes re-fits the box then, not later.
  * THE SWAP IS QUIET: the box photographed with the picture and again with
    the ink alone differ by little, cell by cell, the edge's ring of cells
    neither lighter nor darker (the frame's shade), and the picture's going is
    read on every frame: it fades, no step more than a third, then leaves.
    Reduce Motion: it leaves at once.
  * NEVER A FROZEN PAGE: with the CPU 4x slower, the ink is laid over many
    frames and shown as it goes (the canvas under the picture fills in), and
    no task from the data's arrival to the ink whole, the arrival's own
    included, runs longer than a third of what painting the drawing in one
    call takes on the same page. Measured against the one call, not a fixed
    number of milliseconds: the box this runs on sets both, and the one call
    is the freeze there was (the arrival's task held it, so a row that left
    the arrival out could not see the freeze it guards against).
  * THE INK IS THE SAME: what the slices leave on the canvas is, pixel for
    pixel, what one call leaves (the same drawing painted again at once on
    the same canvas).
  * PLAY WHILE IT PAINTS: pressed before the ink is whole, the picture goes,
    the replay starts from nothing (the slices stop), and its end is the
    drawing.
  * THE TRANSPORT comes up when the drawing can play, over several frames, and
    Play then plays.
  * A SHORT DRAWING, AN EMPTY ONE, A POST WITH NO PICTURE, A FAILED LOAD: the
    picture gives way and never stands over finished ink longer than its
    fade, an empty drawing's too (it has nothing to paint, so nothing would
    say its ink is whole); with no picture nothing is left over the ink; a
    refused payload shows the error panel and no picture.
"""
import base64
import io
import json
import math
import os
import sys
import urllib.request

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
CAPTION = "Every cat I drew this week, all in one sitting."
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the link page shows a long drawing at once.")
    raise SystemExit(77)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
W, H = 816, 612


def api_post(body):
    req = urllib.request.Request(BASE + "/api/skribls", method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["id"]


def html(pid):
    try:
        return urllib.request.urlopen(BASE + "/s/" + pid, timeout=20).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def spiral(n=300):
    pts = []
    for i in range(n):
        a, r = (i / n) * math.pi * 6, 20 + (i / n) * 200
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7, "color": "#1d1a2b",
                    "size": 7, "t": i * 20, "erase": False, "start": i == 0})
    return pts


def card(fill=(255, 0, 255), ring=(0, 200, 0)):
    """A share card laid out as lib/sharecard.js lays one: the drawing's
    rectangle (drawingRect) in one flat colour, its plate's 2px ring in
    another, on the card's dark ground. Where the link page crops it, only the
    fill may show."""
    k = min(1092 / W, 492 / H)
    dw, dh = round(W * k), round(H * k)
    dx, dy = round((1200 - dw) / 2), round((546 - dh) / 2)
    im = Image.new("RGB", (1200, 630), (11, 13, 18))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([dx, dy, dx + dw - 1, dy + dh - 1], radius=18, fill=fill, outline=ring, width=2)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# Generated in the Pad itself, from a fixed seed, shaped like a pointer's
# points: long enough that one paint is a long task at a phone's pace.
GEN = """(n) => { let s = 11; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const pts = [], groups = []; let t = 0; const cols = ['#7c5cff', '#1d1a2b', '#1d1a2b', '#ff7a59'];
  while (pts.length < n) {
    const m = 15 + Math.floor(rnd() * 60); let x = 60 + rnd() * 690, y = 50 + rnd() * 510;
    let ang = rnd() * 6.283; const curv = (rnd() - 0.5) * 0.12, step = 3 + rnd() * 5;
    const w = [2, 3, 4, 6, 10][Math.floor(rnd() * 5)], col = cols[Math.floor(rnd() * 4)];
    let k = 0;
    for (let i = 0; i < m && pts.length < n; i++, k++) {
      const f = i / (m - 1);
      const q = { x, y, color: col, size: w * (0.35 + 0.65 * Math.sin(Math.PI * f)) + 0.3, t: Math.round(t) };
      if (i === 0) q.start = true;
      pts.push(q); ang += curv;
      x = Math.min(810, Math.max(5, x + Math.cos(ang) * step)); y = Math.min(606, Math.max(5, y + Math.sin(ang) * step));
      t += 1000 / 55;
    }
    groups.push(k); t += 150 + rnd() * 650;
  }
  return { pts, groups }; }"""


def post_long(b, n=40000):
    """A long drawing posted through the Pad's own Post sheet, so its picture
    is the card the editor makes."""
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    pg.wait_for_timeout(1200)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    pg.evaluate("(n) => { const d = (" + GEN + ")(n); loadSkribl({ version: 1, strokes: d.pts, strokeGroups: d.groups,"
                " background: { color: '#f6f2ea' }, canvasSize: { cssWidth: " + str(W) + ", cssHeight: " + str(H) + " } }, ' '); }", n)
    pg.wait_for_timeout(1500)
    pg.click("#postBtn")
    pg.wait_for_selector("#postSheet", state="visible")
    pg.wait_for_timeout(450)
    pg.fill("#postTitleInput", "Two hours")
    pg.fill("#postCaptionInput", CAPTION)
    pg.click("#postSubmitBtn")
    pg.wait_for_selector("#postDone:not([hidden])", timeout=120000)
    pid = pg.evaluate("() => JSON.parse(localStorage.getItem('skribl_posted_v1') || '[]')[0].id")
    pg.close()
    return pid


# Watches the page from its first frame: when the picture shows, the box then,
# the picture's opacity every frame, and when it leaves. Asked to (`sample`),
# it also reads how many cells of the canvas under the picture hold ink, every
# second frame from the data's release until the picture starts to go.
WATCH = """(() => { window.__fl = { op: [], lt: [], ns: [] };
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__fl.lt.push([e.startTime, e.duration]); })
    .observe({ type: 'longtask', buffered: true }); } catch (e) {}
  const box = r => [r.x, r.y, r.width, r.height];
  let s = null;
  const inked = () => { const cv = document.getElementById('canvas');
    if (!s) { s = document.createElement('canvas'); s.width = 64; s.height = 48; }
    const x = s.getContext('2d'); x.clearRect(0, 0, 64, 48); x.drawImage(cv, 0, 0, 64, 48);
    const d = x.getImageData(0, 0, 64, 48).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++; return n; };
  const look = () => { const f = window.__fl, p = document.getElementById('playerPoster'), w = document.querySelector('.canvas-wrap');
    const now = performance.now();
    if (p && !p.hidden && f.shown == null) { f.shown = now; f.wrap0 = box(w.getBoundingClientRect()); }
    if (p && p.classList.contains('gone') && f.fade == null) f.fade = now;
    if (f.sample && f.release != null && f.fade == null && p && (f.k = (f.k || 0) + 1) % 2 === 0 && f.ns.length < 40) f.ns.push(inked());
    if (p) f.op.push([now, +getComputedStyle(p).opacity]);
    if (f.shown != null && !p && f.left == null) { f.left = now; f.wrap1 = box(w.getBoundingClientRect()); }
    requestAnimationFrame(look); };
  requestAnimationFrame(look); })()"""


def open_held(b, pid, view, rate=1, reduce=False):
    """The link page with the post's data held back until release()."""
    c = b.new_context(reduced_motion="reduce" if reduce else "no-preference", **view)
    pg = c.new_page()
    pg.add_init_script(WATCH)
    held = []
    pg.route("**/api/skribls/" + pid, lambda route: held.append(route))
    if rate != 1:
        c.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": rate})
    pg.goto(BASE + "/s/" + pid, wait_until="load")
    for _ in range(100):
        if held:
            break
        pg.wait_for_timeout(50)

    def release():
        pg.evaluate("() => { window.__fl.release = performance.now(); }")
        for r in held:
            r.continue_()
        held.clear()
    return c, pg, release


def shot_box(pg, inset=0):
    """The box as painted, as an RGB image at CSS-pixel scale."""
    r = pg.evaluate("() => { const b = document.querySelector('.canvas-wrap').getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }")
    im = Image.open(io.BytesIO(pg.screenshot(clip={"x": r[0] + inset, "y": r[1] + inset,
                                                  "width": r[2] - 2 * inset, "height": r[3] - 2 * inset}))).convert("RGB")
    return im.resize((max(1, round(r[2] - 2 * inset)), max(1, round(r[3] - 2 * inset))))


def magenta(c):
    # The card's drawing, under the frame's own shade (as dark as 40% at the
    # very edge): its hue, not its exact value.
    return c[0] > 110 and c[2] > 110 and c[1] < 70 and abs(c[0] - c[2]) < 40


def ringish(c):
    return c[1] > 90 and c[1] > c[0] + 50 and c[1] > c[2] + 50


SAY = """() => { const t = document.getElementById('playerTitle'), c = document.getElementById('playerCaption'),
  k = document.querySelector('.player-controls'), sh = document.getElementById('playerShell'),
  s = document.querySelector('#playerLine .rl-speed');
  const seen = e => !!e && !e.hidden && e.getClientRects().length > 0 && getComputedStyle(e).visibility === 'visible';
  return { title: t && t.textContent, caption: c && !c.hidden ? c.textContent : null, shell: seen(sh), title_seen: seen(t),
           caption_seen: seen(c), controls: k ? getComputedStyle(k).visibility : null,
           speed: s ? getComputedStyle(s).visibility : null }; }"""

INK = """() => { const cv = document.getElementById('canvas'), x = cv.getContext('2d');
  const d = x.getImageData(0, 0, cv.width, cv.height).data; let h = 2166136261, ink = 0;
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3]) ink++; h = Math.imul(h ^ d[i] ^ (d[i + 1] << 8) ^ (d[i + 2] << 16) ^ (d[i + 3] << 24), 16777619); }
  return { hash: h >>> 0, ink }; }"""


SOME = """() => { const cv = document.getElementById('canvas'), s = document.createElement('canvas');
  s.width = 64; s.height = 48; const x = s.getContext('2d'); x.drawImage(cv, 0, 0, 64, 48);
  const d = x.getImageData(0, 0, 64, 48).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
  const p = document.getElementById('playerPoster');
  return { n, mid: !!p && !p.classList.contains('gone') }; }"""


def waited(pg, cond, timeout):
    """True once cond holds; False, not a crash, when it never does, so a
    break shows as the row it breaks. (A picture that never showed is waited
    on briefly after: its rows are red already.)"""
    try:
        pg.wait_for_function(cond, timeout=timeout, polling=50)
        return True
    except Exception:
        return False


def moved(f):
    a, z = f.get("wrap0"), f.get("wrap1")
    return max(abs(u - v) for u, v in zip(a, z)) if a and z else None


with sync_playwright() as p:
    b = p.chromium.launch()
    LONG = post_long(b)
    SHORT = api_post({"title": "A spiral", "caption": "Round and round.", "schemaVersion": 2, "visibility": "public",
                      "canvasSize": {"cssWidth": W, "cssHeight": H},
                      "frames": [{"strokes": spiral(), "strokeGroups": [300]}], "thumbnail": card()})
    NOPIC = api_post({"title": "No picture", "schemaVersion": 2, "visibility": "public",
                      "canvasSize": {"cssWidth": W, "cssHeight": H},
                      "frames": [{"strokes": spiral(), "strokeGroups": [300]}]})
    EMPTY = api_post({"title": "Nothing yet", "schemaVersion": 2, "visibility": "public",
                      "canvasSize": {"cssWidth": W, "cssHeight": H},
                      "frames": [{"strokes": [], "strokeGroups": []}], "thumbnail": card()})
    FLIP = api_post({"title": "Two pages", "schemaVersion": 2, "visibility": "public", "playbackMode": "flip", "fps": 8,
                     "canvasSize": {"cssWidth": W, "cssHeight": H},
                     "frames": [{"strokes": spiral(120), "strokeGroups": [120]}, {"strokes": spiral(200), "strokeGroups": [200]}]})

    print("\nTHE PAGE KNOWS (the route)")
    pre = lambda h: (h.split("window.SKRIBL_PLAYER_PRE = ", 1) + ["?"])[1].split(";", 1)[0]
    hl = html(LONG)
    try:
        pl = json.loads(pre(hl)) or {}
    except ValueError:
        pl = {}
    check("a Pad post's page carries its size, before its data",
          pl.get("w") == W and pl.get("h") == H, pre(hl))
    check("...and its line's numbers (drawn, play, speed), for the line under the track",
          isinstance(pl.get("line"), dict) and pl["line"].get("drawn", 0) > 60000
          and pl["line"].get("play", 0) > 0 and "speed" in pl["line"], pre(hl))
    check("...its title and caption, said in the shell by the server",
          'id="playerTitle">Two hours<' in hl and 'id="playerCaption">' + CAPTION + "<" in hl, "")
    check("...and its own picture, the card made when it was posted",
          'id="playerPoster"' in hl and "/s/" + LONG + "/poster" in hl, "")
    hf, hm = html(FLIP), html("zzzzzzzzzzz")
    check("a Flip's page and a missing post's carry no size and no picture",
          pre(hf) == "null" and pre(hm) == "null" and 'id="playerPoster"' not in hf + hm, f"{pre(hf)} / {pre(hm)}")

    print("\nAT ONCE, with the data held back")
    for name, view in (("phone", PHONE), ("desk", DESK)):
        c, pg, release = open_held(b, SHORT, view)
        shown = waited(pg, "() => window.__fl.shown != null", 8000)
        pg.wait_for_timeout(150)
        im = shot_box(pg)
        w_, h_ = im.size
        pts = [(w_ // 2, h_ // 2), (6, h_ // 2), (w_ - 7, h_ // 2), (w_ // 2, 6), (w_ // 2, h_ - 7),
               (w_ // 4, h_ // 4), (3 * w_ // 4, 3 * h_ // 4)]
        filled = shown and all(magenta(im.getpixel(q)) for q in pts)
        band = [im.getpixel((x, y)) for x in range(24, w_ - 24, 3) for y in (0, 1, 2, h_ - 3, h_ - 2, h_ - 1)] + \
               [im.getpixel((x, y)) for y in range(24, h_ - 24, 3) for x in (0, 1, 2, w_ - 3, w_ - 2, w_ - 1)]
        ringed = [q for q in band if ringish(q)]
        check(f"{name}: the post's picture is painted where the canvas is, before the drawing's data has come",
              filled, f"shown {shown}; " + str([im.getpixel(q) for q in pts]))
        check(f"{name}: ...cropped to the drawing: none of the card's ground, none of its plate's ring",
              filled and not ringed, f"{len(ringed)} ring pixels in the edge band")
        say = pg.evaluate(SAY)
        # The speed in the line is read on its own: the line there is a
        # stand-in from the post's numbers, with no pick (app.js playerPre),
        # safe only while no one can press it; and the suites wait for it seen
        # (browsing.SPEED_READY), not merely there.
        check(f"{name}: ...the title and caption are said, and the transport waits laid out, unseen, the speed in its line too",
              say["title"] == "A spiral" and say["caption"] == "Round and round." and say["title_seen"]
              and say["caption_seen"] and say["controls"] == "hidden" and say["speed"] == "hidden", str(say))
        release()
        left = waited(pg, "() => window.__fl.left != null", 30000)
        pg.wait_for_timeout(200)
        f = pg.evaluate("() => window.__fl")
        m = moved(f)
        check(f"{name}: nothing moves: the box stands where it stood before the data came",
              left and m is not None and m <= 0.5, f"left {left}; before {f.get('wrap0')}, after {f.get('wrap1')}")
        say = pg.evaluate(SAY)
        check(f"{name}: ...and once the drawing can play the transport is up, its speed with it",
              say["controls"] == "visible" and say["speed"] == "visible", str(say))
        c.close()

    for name, view in (("phone", PHONE), ("desk", DESK)):
        c, pg, release = open_held(b, LONG, view)
        shown = waited(pg, "() => window.__fl.shown != null", 15000)
        release()
        left = waited(pg, "() => window.__fl.left != null", 60000 if shown else 1500)
        f = pg.evaluate("() => window.__fl")
        m = moved(f)
        check(f"{name}: the long drawing's box stands still too, its longer line and all",
              shown and left and m is not None and m <= 0.5, f"before {f.get('wrap0')}, after {f.get('wrap1')}")
        c.close()

    # A phone turned while the drawing is still coming: the box re-fits then,
    # and does not move again when the drawing lands.
    c, pg, release = open_held(b, LONG, PHONE)
    shown = waited(pg, "() => window.__fl.shown != null", 15000)
    pg.set_viewport_size({"width": 874, "height": 402})
    pg.wait_for_timeout(400)
    turned = pg.evaluate("() => { const r = document.querySelector('.canvas-wrap').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
    release()
    left = waited(pg, "() => window.__fl.left != null", 60000 if shown else 1500)
    f = pg.evaluate("() => window.__fl")
    m = max(abs(u - v) for u, v in zip(turned, f["wrap1"])) if f.get("wrap1") else None
    check("a phone turned while the drawing comes: the box re-fits then, and stands when the drawing lands",
          shown and left and m is not None and m <= 0.5 and abs(turned[2] - f["wrap0"][2]) > 20,
          f"before the turn {f.get('wrap0')}, turned {turned}, after {f.get('wrap1')}")
    c.close()

    print("\nTHE SWAP IS QUIET, on the long drawing")
    c, pg, release = open_held(b, LONG, DESK)
    shown = waited(pg, "() => window.__fl.shown != null", 15000)
    pg.wait_for_timeout(300)
    pic = shot_box(pg, inset=3)
    release()
    left = waited(pg, "() => window.__fl.left != null", 60000 if shown else 1500)
    pg.wait_for_timeout(300)
    ink = shot_box(pg, inset=3)
    f = pg.evaluate("() => window.__fl")
    cells, worst, total = 0, 0.0, 0.0
    edge = []      # the outer ring of cells: (difference, picture minus ink)
    sw, sh = pic.size[0] // 16, pic.size[1] // 16
    a, b2 = pic.resize((sw, sh)), ink.resize((sw, sh))
    for y in range(sh):
        for x in range(sw):
            pa, pb = a.getpixel((x, y)), b2.getpixel((x, y))
            dlt = sum(abs(u - v) for u, v in zip(pa, pb)) / 3
            total += dlt
            worst = max(worst, dlt)
            cells += 1
            if x in (0, sw - 1) or y in (0, sh - 1):
                edge.append((dlt, (sum(pa) - sum(pb)) / 3))
    mean = total / max(1, cells)
    check("the picture and the ink it gives way to look alike, cell by cell (16px cells)",
          shown and left and mean <= 6 and worst <= 40, f"mean {mean:.1f}, worst cell {worst:.1f} of 255, {cells} cells")
    # THE FRAME'S SHADE, AT THE EDGE. The canvas has the frame's vignette over
    # its ground and under its ink; a flat picture can only have it over all of
    # it, so it wears it at 0.6 (styles.css), where the edge reads the same:
    # bare it was lighter by 14.5, at full strength darker by 9.
    em = sum(d for d, _ in edge) / max(1, len(edge))
    es = sum(s_ for _, s_ in edge) / max(1, len(edge))
    check("...and at the edge, where the frame shades both: neither lighter nor darker than the ink's",
          shown and left and edge and em <= 7.5 and abs(es) <= 4,
          f"edge ring of {len(edge)} cells: mean difference {em:.1f}, picture minus ink {es:+.1f} of 255")
    ops = [o for t, o in f["op"] if f.get("fade") is not None and t >= f["fade"]]
    steps = [abs(ops[i + 1] - ops[i]) for i in range(len(ops) - 1)]
    check("...it fades as the ink is whole, no step more than a third, then leaves",
          left and len(ops) >= 6 and ops[-1] <= 0.05 and max(steps or [1]) <= 0.34,
          f"{len(ops)} frames, last {ops[-1] if ops else None}, biggest step {max(steps or [0]):.2f}")
    h1 = pg.evaluate(INK)
    pg.evaluate("() => clearAndRestore(() => paintStrokesStatic(strokes))")
    h2 = pg.evaluate(INK)
    check("the ink the slices laid is, pixel for pixel, what one call lays",
          h1["ink"] > 10000 and h1["hash"] == h2["hash"], f"{h1} / {h2}")
    c.close()

    print("\nREDUCE MOTION")
    c, pg, release = open_held(b, LONG, DESK, reduce=True)
    shown = waited(pg, "() => window.__fl.shown != null", 15000)
    release()
    left = waited(pg, "() => window.__fl.left != null", 60000 if shown else 1500)
    f = pg.evaluate("() => window.__fl")
    mid = [o for t, o in f["op"] if f.get("fade") is not None and t >= f["fade"] and 0.05 < o < 0.95]
    check("with Reduce Motion the picture leaves at once, no frame between",
          shown and left and f.get("fade") is not None and not mid, f"{len(mid)} frames in between")
    c.close()

    print("\nNEVER A FROZEN PAGE, the CPU 4x slower")
    c, pg, release = open_held(b, LONG, DESK, rate=4)
    shown = waited(pg, "() => window.__fl.shown != null", 30000)
    pg.evaluate("() => { window.__fl.sample = true; }")
    release()
    left = waited(pg, "() => window.__fl.left != null", 120000 if shown else 1500)
    f = pg.evaluate("() => window.__fl")
    end_ = pg.evaluate(SOME)
    fade = f.get("fade") or float("inf")
    tasks = [d for t, d in f["lt"] if f["release"] <= t <= fade]
    frames = len([1 for t, o in f["op"] if f["release"] <= t <= fade])
    one = pg.evaluate("""() => { const t = performance.now(); clearAndRestore(() => paintStrokesStatic(strokes));
      document.getElementById('canvas').getContext('2d').getImageData(0, 0, 1, 1); return performance.now() - t; }""")
    check("the long drawing's ink is laid over many frames, the page answering between them",
          shown and left and frames >= 10, f"{frames} frames between the data and the ink whole")
    # Partway, the canvas under the picture holds some of the ink and not all,
    # read on the frames themselves. ONE READ after 20 frames was the first
    # instrument, and on a quicker box it came after the slices had nearly
    # finished: 2,546 of 2,647 cells on main's CI (#682's run), red with
    # nothing wrong. Any frame of the paint's own that shows part of the ink
    # is the claim; a paint shown only when whole has none.
    part_ = [n for n in f["ns"] if 0 < n < end_["n"] * 0.95]
    check("...shown as it goes: partway, the canvas under the picture holds some of the ink, not all",
          shown and left and bool(part_),
          f"{len(part_)} of {len(f['ns'])} frames read held part of the {end_['n']} inked cells: {f['ns'][:16]}")
    check("...and no task from the data's arrival to the ink whole runs a third of the one call",
          left and tasks and max(tasks) <= one / 3,
          f"one call {one:.0f} ms; the tasks {[round(x) for x in sorted(tasks, reverse=True)[:8]]} ({len(tasks)} over 50 ms)")
    c.close()

    print("\nPLAY WHILE IT PAINTS")
    c, pg, release = open_held(b, LONG, DESK, rate=4)
    shown = waited(pg, "() => window.__fl.shown != null", 30000)
    release()
    waited(pg, "() => document.body.classList.contains('player-ready') || !document.body.classList.contains('player-pending')", 60000)
    early = pg.evaluate("() => ({ poster: !!document.getElementById('playerPoster'), fading: window.__fl.fade != null })")
    pg.evaluate("() => document.getElementById('playerPlayBtn').click()")
    pg.wait_for_timeout(700)
    ink_soon = pg.evaluate(INK)["ink"]
    pg.wait_for_timeout(500)
    gone = pg.evaluate("() => !document.getElementById('playerPoster')")
    pg.evaluate("() => window.__skriblPlayerSeek(1)")
    pg.wait_for_timeout(3000)
    end = pg.evaluate(INK)
    pg.evaluate("() => clearAndRestore(() => paintStrokesStatic(strokes))")
    whole = pg.evaluate(INK)
    check("Play pressed while the ink is still being laid: the picture goes",
          shown and early["poster"] and not early["fading"] and gone, f"{early}; gone {gone}")
    check("...the replay starts from nothing, the slices stopped",
          ink_soon < whole["ink"] * 0.25, f"{ink_soon} inked pixels 0.7 s in, of {whole['ink']}")
    check("...and its end is the drawing",
          abs(end["ink"] - whole["ink"]) <= whole["ink"] * 0.01, f"{end['ink']} inked pixels at the end, of {whole['ink']}")
    c.close()

    print("\nTHE TRANSPORT")
    c, pg, release = open_held(b, SHORT, DESK)
    shown = waited(pg, "() => window.__fl.shown != null", 8000)
    pg.evaluate("""() => { window.__tp = []; const k = document.querySelector('.player-controls');
      const t = () => { window.__tp.push(+getComputedStyle(k).opacity * (getComputedStyle(k).visibility === 'visible' ? 1 : 0));
        if (window.__tp.length < 90) requestAnimationFrame(t); }; requestAnimationFrame(t); }""")
    release()
    pg.wait_for_timeout(1800)
    tp = pg.evaluate("() => window.__tp")
    rising = [v for v in tp if 0.05 < v < 0.95]
    check("the transport comes up when the drawing can play, over several frames",
          tp and tp[-1] >= 0.99 and len(rising) >= 3, f"{len(rising)} frames between, last {tp[-1] if tp else None}")
    pg.evaluate("() => document.getElementById('playerPlayBtn').click()")
    pg.wait_for_timeout(700)
    fill = pg.evaluate("() => parseFloat(getComputedStyle(document.getElementById('playerProgressFill')).width) || 0")
    check("...and Play then plays", fill > 0, f"progress {fill}px")
    c.close()

    print("\nA SHORT DRAWING, AN EMPTY ONE, NO PICTURE, A FAILED LOAD")
    for label, pid in (("a short drawing", SHORT), ("an empty drawing (nothing to paint)", EMPTY)):
        c = b.new_context(**DESK)
        pg = c.new_page()
        pg.add_init_script(WATCH)
        pg.goto(BASE + "/s/" + pid, wait_until="load")
        left = waited(pg, "() => document.body.classList.contains('player-mode') && window.__fl.left != null", 15000)
        f = pg.evaluate("() => window.__fl")
        over = (f["left"] - f["fade"]) if left and f.get("fade") is not None else None
        check(f"{label}: its picture gives way, and never stands over the ink longer than its fade",
              over is not None and over <= 600, f"shown {f.get('shown')}, fade {f.get('fade')}, left {f.get('left')}")
        c.close()
    c = b.new_context(**DESK)
    pg = c.new_page()
    pg.goto(BASE + "/s/" + NOPIC, wait_until="load")
    waited(pg, "() => !document.getElementById('playerPoster') || document.getElementById('playerPoster').classList.contains('gone')", 15000)
    pg.wait_for_timeout(600)
    left = pg.evaluate("() => ({ poster: !!document.getElementById('playerPoster'), ink: 0 })")
    left["ink"] = pg.evaluate(INK)["ink"]
    check("a post with no picture: nothing is left over its ink", not left["poster"] and left["ink"] > 500, str(left))
    c.close()
    c = b.new_context(**DESK)
    pg = c.new_page()
    pg.route("**/api/skribls/" + SHORT, lambda r: r.fulfill(status=500, body="no"))
    pg.goto(BASE + "/s/" + SHORT, wait_until="load")
    waited(pg, "() => { const e = document.getElementById('playerError'); return !!e && !e.hidden; }", 10000)
    st = pg.evaluate("""() => { const w = document.querySelector('.canvas-wrap'), p = document.getElementById('playerPoster'),
      e = document.getElementById('playerError');
      return { error: !!e && !e.hidden, wrap: !w.hidden && w.getClientRects().length > 0, poster: !!p && p.getClientRects().length > 0 && !w.hidden }; }""")
    check("a refused payload: the error panel, and no picture of a drawing that cannot play",
          st["error"] and not st["wrap"] and not st["poster"], str(st))
    c.close()
    b.close()

summarise_and_exit()
