#!/usr/bin/env python3
"""The glowing dot on a Flip page that draws itself, everywhere it plays.

The owner, after v328: "on flip play on a draw on slide, I don't see a
glowing nib drawing the line", and then "C, everywhere". The Pad's replay
has always carried the bead at the tip of the line; a Flip page set to Draw
on now carries the same one, wherever it plays:

  * the Flip editor's Play (flip.js revealNib);
  * the link page, /s/<id> (app.js drawFlipFrame, through showNibAt);
  * the box a post plays in, the Gallery's, the Library's and the feed's
    (inlineplayer.js);
  * the files: a GIF and a video draw the page the way the player does, and
    the dot with it (flip.js drawFrameTo, painted by lib/nib.js). The GIF
    used to paint a Draw on page whole: it now reveals it, as the video did.

On every surface the dot rides the last point revealed, takes that point's
ink (a Smear's #rrggbbaa too), and is gone on a still page. Each row was red
with its hook taken out (DECISIONS, the entry for this change).
"""
import json
import os
import re
import struct
import sys
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the Flip's dot is right.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
TAG = "nib" + os.urandom(3).hex()
W, H = 402, 760
PINK, BLUE8 = "#ff48b0", "#0078bfcc"      # the second is a Smear's: alpha on the end
PINK_RGB, BLUE_RGB = "255,72,176", "0,120,191"


def line(y, color, gap):
    """A level line drawn left to right, one point every `gap` ms."""
    return [{"x": 60 + 7 * i, "y": y, "color": color, "t": i * gap, "start": i == 0, "size": 10, "pressure": 0.5}
            for i in range(41)]


# Page 1 draws itself in pink over 2.4 s, page 2 is still, page 3 draws itself
# in a Smear's blue. The still page's line is at a height of its own, so a dot
# left on it is a dot in the wrong place as well as one that should be gone.
DOC = {"title": f"Flip nib {TAG}", "version": 2, "schemaVersion": 2, "visibility": "public",
       "playbackMode": "flip", "fps": 6, "canvasSize": {"cssWidth": W, "cssHeight": H},
       "frames": [{"strokes": line(380, PINK, 60), "strokeGroups": [41], "draw": True},
                  {"strokes": line(200, "#2e1b52", 0), "strokeGroups": [41], "hold": 6},
                  {"strokes": line(560, BLUE8, 60), "strokeGroups": [41], "draw": True}]}
YS = {380: 0, 200: 1, 560: 2}


def post(body):
    rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read())


# Every animation frame, where the dot is and what ink it wears, in the
# drawing's own units, read off the dot's painted box over the canvas's.
# `nib` and `canvas` are selectors; a dot is shown when it is not hidden, is
# displayed and is not faded out (the post's box hides it by opacity).
SAMPLER = """([nibSel, canvasSel, W, H]) => { window.__n = []; const t0 = performance.now();
  const tick = () => { const n = document.querySelector(nibSel), c = document.querySelector(canvasSel);
    let row = { t: performance.now() - t0, on: false };
    if (n && c && !n.hidden) { const cs = getComputedStyle(n), r = n.getBoundingClientRect(), cr = c.getBoundingClientRect();
      if (cs.display !== 'none' && parseFloat(cs.opacity) > 0.5 && r.width > 0 && cr.width > 0) {
        row = { t: row.t, on: true, x: ((r.left + r.width / 2) - cr.left) * W / cr.width,
                y: ((r.top + r.height / 2) - cr.top) * H / cr.height,
                ink: (n.style.getPropertyValue('--nib-rgb') || n.style.getPropertyValue('--nib-c') || '').trim() }; } }
    window.__n.push(row); if (window.__n.length < 2000 && !window.__stopN) requestAnimationFrame(tick); };
  requestAnimationFrame(tick); return true; }"""


def judge(where, rows, inks):
    """The three rows every surface answers: a dot while each Draw on page
    draws, on its line and in its ink; and none on the still page."""
    # The first time through only: a player that loops starts the pink line
    # again, and that is the start of a second pass, not a dot going back.
    first, seen_blue = [], False
    for r in rows:
        if r["on"] and abs(r["y"] - 560) < 12:
            seen_blue = True
        elif seen_blue and r["on"] and abs(r["y"] - 380) < 12:
            break
        first.append(r)
    rows = first
    on = [r for r in rows if r["on"]]
    by_page = {0: [], 1: [], 2: []}
    stray = []
    for r in on:
        near = min(YS, key=lambda y: abs(r["y"] - y))
        if abs(r["y"] - near) < 12 and 55 <= r["x"] <= 345:
            by_page[YS[near]].append(r)
        else:
            stray.append(r)
    pink, still, blue = by_page[0], by_page[1], by_page[2]
    xs = [r["x"] for r in pink]
    # Never back along the line by more than rounding (the box is read in
    # pixels on a canvas a phone shows at 0.67 of the drawing's units).
    back = [(a, b2) for a, b2 in zip(xs, xs[1:]) if b2 < a - 1.5]
    check(f"{where}: the dot rides a Draw on page's line as it draws, left to right",
          len(pink) >= 8 and not back and xs[-1] - xs[0] > 120 and not stray,
          f"{len(pink)} frames on the line, x {xs[0] if xs else None} to {xs[-1] if xs else None}; "
          f"{len(stray)} off any line {stray[:2]}; back {back[:3]}; {len(rows)} frames read")
    check(f"{where}: the dot wears the ink it lays down, a Smear's #rrggbbaa as well",
          bool(pink) and bool(blue) and all(inks(r["ink"]) == PINK_RGB for r in pink)
          and all(inks(r["ink"]) == BLUE_RGB for r in blue),
          f"pink page {sorted(set(r['ink'] for r in pink))}; blue page {sorted(set(r['ink'] for r in blue))}")
    check(f"{where}: no dot on a still page", not still and len([r for r in rows if not r["on"]]) > 4,
          f"{len(still)} frames with a dot on the still page")


def rgb_of(raw):
    """The post's box carries the colour raw (--nib-c); the others r,g,b."""
    m = re.match(r"#([0-9a-fA-F]{6})", raw)
    if m:
        h = m.group(1)
        return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
    return raw.replace(" ", "")


def gif_frames(b):
    """How many images a GIF holds: count image descriptors past the header."""
    i = 13 + (3 * 2 ** ((b[10] & 7) + 1) if b[10] & 0x80 else 0)
    n = 0
    while i < len(b):
        k = b[i]
        if k == 0x3B:
            break
        if k == 0x21:
            i += 2
            while b[i]:
                i += b[i] + 1
            i += 1
        elif k == 0x2C:
            n += 1
            flags = b[i + 9]
            i += 10 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
            i += 1
            while b[i]:
                i += b[i] + 1
            i += 1
        else:
            break
    return n


POSTED = post(DOC)
PID = POSTED.get("id") or re.search(r"/s/([A-Za-z0-9_-]+)", POSTED.get("url", "")).group(1)
PLAY_MS = 2400 + 1000 + 2400 + 900

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True,
                        has_touch=True, accept_downloads=True)
    errs = []

    # ------------------------------------------------------- the Flip editor
    print("\nTHE FLIP EDITOR'S PLAY")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/flip")
    pg.evaluate("(d) => applyFlipDraftObject(d)", DOC)
    pg.wait_for_timeout(500)
    check("the editor holds the fixture: three pages, the first and last drawing themselves",
          pg.evaluate("() => frames.length === 3 && frameDraw(frames[0]) && !frameDraw(frames[1]) && frameDraw(frames[2])"),
          pg.evaluate("() => frames.map(f => [f.strokes.length, frameDraw(f)])"))
    pg.evaluate(SAMPLER, [".flip-wrap .player-nib", "#pad", W, H])
    pg.evaluate("() => play()")
    pg.wait_for_timeout(PLAY_MS)
    pg.evaluate("() => { window.__stopN = true; }")
    rows = pg.evaluate("() => window.__n")
    judge("Flip's Play", rows, rgb_of)
    pg.evaluate("() => { window.__stopN = false; go(0); play(); }")
    pg.wait_for_timeout(900)
    mid = pg.evaluate("() => { const n = document.querySelector('.flip-wrap .player-nib'); return !!n && !n.hidden; }")
    pg.evaluate("() => stop()")
    pg.wait_for_timeout(150)
    after = pg.evaluate("() => { const n = document.querySelector('.flip-wrap .player-nib'); return !!n && !n.hidden; }")
    check("Flip's Play: Stop takes the dot away mid-line", mid and not after, f"playing {mid}; stopped {after}")

    # ------------------------------------------------------------- the files
    print("\nTHE FILES (GIF, and the frames a video records)")
    # The video's frames are drawFrameTo's, as the GIF's now are; read one at
    # half way through the pink line. Its tip is at x 200: just ahead of it,
    # where the line has not reached yet, the halo is pink; once the page is
    # whole there is line there and no halo above it.
    px = pg.evaluate("""() => { const c = document.createElement('canvas'); c.width = CW; c.height = CH;
        const x = c.getContext('2d'); const read = (prog) => { x.clearRect(0, 0, CW, CH); drawFrameTo(x, frames[0], prog);
          return Array.from(x.getImageData(212, 372, 1, 1).data); };
        return { half: read(0.5), whole: read(1), bg: (() => { x.clearRect(0, 0, CW, CH); drawBackdrop(x); return Array.from(x.getImageData(212, 372, 1, 1).data); })() }; }""")
    tint = lambda c: c[0] - c[1]   # pink is red over green; the ground is not
    check("a video frame half way through a Draw on page carries the dot's pink halo at the tip",
          tint(px["half"]) > tint(px["bg"]) + 18, f"at the tip {px['half']}; the ground {px['bg']}")
    check("and the frame where the page is whole carries none above the line",
          abs(tint(px["whole"]) - tint(px["bg"])) < 10, f"whole page {px['whole']}; the ground {px['bg']}")
    calls = pg.evaluate("""async () => { let n = 0; const real = window.SkriblNib.paint;
        window.SkriblNib.paint = function () { n++; return real.apply(this, arguments); };
        window.__nibCalls = () => n; return true; }""")
    pg.evaluate("() => openExportSheet()")
    pg.wait_for_timeout(400)
    with pg.expect_download(timeout=90000) as dl:
        pg.click("#exportGif")
    gif = open(dl.value.path(), "rb").read()
    painted = pg.evaluate("() => window.__nibCalls()")
    n = gif_frames(gif)
    # 2.4 s at 6 fps is 15 ticks for each drawing page, and the still page is
    # one image held; painted whole each was one image: 3 in all.
    check("the GIF reveals a Draw on page tick by tick, as the video does, where it painted it whole",
          n >= 25, f"{n} images (3 when each page was one)")
    check("and the dot rides it in the GIF: one per image while a page draws",
          calls and painted >= 20, f"lib/nib.js painted the dot {painted} times")
    pg.close()

    # ---------------------------------------------------------- the link page
    print("\nTHE LINK PAGE, /s/<id>")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/s/{PID}", wait_until="load")
    pg.wait_for_selector("#playerPlayBtn", state="visible", timeout=20000)
    pg.wait_for_timeout(900)
    pg.evaluate(SAMPLER, [".player-nib", "#canvas", W, H])
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(PLAY_MS)
    pg.evaluate("() => { window.__stopN = true; }")
    judge("the link page", pg.evaluate("() => window.__n"), rgb_of)
    pg.close()

    # ----------------------------------------------------- the box in a post
    print("\nTHE BOX A POST PLAYS IN (the feed)")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/feed")
    sel = f".skribl-inline[data-skribl-id='{PID}']"
    pg.wait_for_selector(sel, state="attached", timeout=20000)
    pg.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'center'})", sel)
    pg.wait_for_timeout(600)
    pg.evaluate(SAMPLER, [sel + " .skribl-inline-nib", sel + " .skribl-inline-canvas", W, H])
    pg.evaluate("(s) => document.querySelector(s).click()", sel)
    pg.wait_for_timeout(PLAY_MS)
    pg.evaluate("() => { window.__stopN = true; }")
    judge("a post's box", pg.evaluate("() => window.__n"), rgb_of)
    pg.close()

    # ------------------------------------------------------------- one ink
    print("\nONE ANSWER FOR THE INK")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/s/{PID}", wait_until="load")
    pg.wait_for_selector("#playerPlayBtn", state="visible", timeout=20000)
    # The link page's nibRGB (app.js) and the editors' lib/nib.js rgb() give
    # one answer for every way a stroke writes its colour.
    nibjs = urllib.request.urlopen(BASE + "/static/skribl/lib/nib.js", timeout=20).read().decode()
    same = pg.evaluate("""(src) => { const g = {}; (new Function('window', src))(g);
        const cases = ['#7c5cff', '#ff48b0cc', '#0078BF', 'rgba(10, 20, 30, 0.4)', 'rgb(1,2,3)', 'red', '#abc', null];
        return cases.map(c => [c, nibRGB(c), g.SkriblNib.rgb(c)]); }""", nibjs)
    check("the link page's ink and the editors' give one answer for every colour a stroke can carry",
          all(a == b2 for _, a, b2 in same) and same[1][1] == "255,72,176",
          str([s for s in same if s[1] != s[2]] or same[:2]))
    pg.close()

    check("no page threw", not errs, str(errs[:3]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
