#!/usr/bin/env python3
"""Skribl's first hello: the mark writes itself with the real pen, and the i's dot bounces in.

The owner's pick after v327 (mock M1: "I like m1"), in place of Blooby's star
(mock C), which never shipped. lib/hello.js plays it the first time Skribl
opens, on the page's own ground, and then it lifts away into the canvas.

The mark (_skribl_brand_mark.html) is ONE even stroke, round-capped, 2.3 units
wide in a 30-unit hand, skewed 8 degrees, its ink sweeping from the accent
(#7c5cff) to accent-2 (#5b8cff) across x = 0..65 of its own units. Both of its
paths are read from that template, so the hello writes the header's own mark,
dot included. The pen draws it monoline (pressure off) and the sweep is carried
by the ink itself: the stroke is laid down in PIECES short strokes, one after
another, each in the sweep's colour where it sits, a lift and a touch at the
same point, so the line runs on unbroken and the drawing plays as the mark.

A Flip, drawn through the real Flip editor with real pen input, on 9:16:

  page 0      the word without its dot, drawing itself: one movement of the
              hand, fitted into WORD_MS, kept UNDER every page after it
  pages 1-9   the dot: stretched as it falls, squashed as it lands, the
              bounce, then at rest over the i for the last three

    python3 harness/tools/make_hello.py OUTDIR
    cp OUTDIR/hello.json skribl/static/brand/hello.json

Needs the local server (SKRIBL_BASE). The payload carries no background colour:
the ground is the page's own (lib/hello.js), in either theme.
"""
import json
import math
import os
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402
import handmotion as hm  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
MARK = ROOT / "skribl" / "templates" / "skribl" / "_skribl_brand_mark.html"
A, B = (0x7c, 0x5c, 0xff), (0x5b, 0x8c, 0xff)   # --accent -> --accent-2, as the mark's gradient runs
PIECES = 64
WORD_MS = 1600
FPS = 12                                         # the dot's nine pages are three quarters of a second
# The dot's pages: how far above its place (in canvas widths), and how wide
# and tall against its own size. Stretched as it falls, squashed as it lands.
DOT_PAGES = ((-0.20, 0.80, 1.35), (-0.09, 0.85, 1.25), (0.0, 1.38, 0.70), (-0.045, 0.95, 1.10),
             (-0.018, 1.0, 1.0), (0.0, 1.14, 0.88), (0.0, 1.0, 1.0), (0.0, 1.0, 1.0), (0.0, 1.0, 1.0))


def mark():
    """The word's path, the dot's, the skew's slope and the pen's width, from the template."""
    src = MARK.read_text(encoding="utf-8")
    word = re.search(r'<path class="st" d="([^"]+)"', src).group(1)
    dot = re.search(r'<path class="st dot" d="([^"]+)"', src).group(1)
    skew = math.tan(math.radians(float(re.search(r'skewX\((-?[\d.]+)\)', src).group(1))))
    pen = float(re.search(r'stroke-width="([\d.]+)"', src).group(1))
    return word, dot, skew, pen


def sweep(t):
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(A, B))


def cubic(d, n=18):
    """A path of one M and its Cs, as points in the mark's own units, before the skew."""
    nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", d)]
    pts = [(nums[0], nums[1])]
    k = 2
    while k + 5 < len(nums):
        p0 = pts[-1]
        p1, p2, p3 = (nums[k], nums[k + 1]), (nums[k + 2], nums[k + 3]), (nums[k + 4], nums[k + 5])
        for i in range(1, n + 1):
            t = i / n
            a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
        k += 6
    return pts


def fit(cw, ch, width=0.78, at=0.46):
    """The word and the dot on the canvas, the word with each point's sweep t
    (the mark's own x / 65, before the skew, as its gradient is laid), and
    the canvas pixels to one of the mark's units."""
    wd, dd, skew, _ = mark()
    word, dot = cubic(wd), cubic(dd, 6)
    sk = lambda p: (p[0] + skew * p[1], p[1])
    allp = [sk(p) for p in word + dot]
    xs = [p[0] for p in allp]; ys = [p[1] for p in allp]
    s = width * cw / (max(xs) - min(xs))
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    place = lambda p: (cw / 2 + (sk(p)[0] - cx) * s, ch * at + (sk(p)[1] - cy) * s)
    return ([place(p) for p in word], [p[0] / 65 for p in word],
            [place(p) for p in dot], sum(p[0] for p in dot) / len(dot) / 65, s)


def send(cdp, box, sx, sy, kind, x, y, buttons=1):
    cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": box["x"] + x * sx, "y": box["y"] + y * sy,
             "button": "left", "buttons": buttons, "clickCount": 1 if kind != "mouseMoved" else 0,
             "pointerType": "pen", "force": 0.0 if kind == "mouseReleased" else 1.0})


def write(page, logical, path, ts, size, pace=0.95, seed=7):
    """One continuous movement of the hand along `path`, laid down as PIECES
    strokes, each in the sweep's colour at its middle: a lift and a touch at
    the same point, so the line runs on unbroken."""
    box = page.locator("#pad").bounding_box()
    sx, sy = box["width"] / logical[0], box["height"] / logical[1]
    timed = hm.stroke(hm.catmull(path, 1.2), pace=pace, seed=seed, pmin=0.5, pmax=1.0, tremor=0.15)
    # Each timed point's sweep t, from the nearest point of the source path.
    tt, j = [], 0
    for x, y, ms, _ in timed:
        while j + 1 < len(path) and math.hypot(path[j + 1][0] - x, path[j + 1][1] - y) <= math.hypot(path[j][0] - x, path[j][1] - y):
            j += 1
        tt.append(ts[j])
    n = len(timed)
    cuts = [round(i * (n - 1) / PIECES) for i in range(PIECES + 1)]
    cdp = page.context.new_cdp_session(page)
    t0 = time.perf_counter()
    for a, b in zip(cuts, cuts[1:]):
        if b <= a:
            continue
        page.evaluate("([c, s]) => { color = c; size = s; }", [sweep((tt[a] + tt[b]) / 2), size])
        for k in range(a, b + 1):
            x, y, ms, _ = timed[k]
            while (time.perf_counter() - t0) * 1000 < ms:
                pass
            send(cdp, box, sx, sy, "mousePressed" if k == a else "mouseMoved", x, y)
        send(cdp, box, sx, sy, "mouseReleased", timed[b][0], timed[b][1], 0)
    cdp.detach()


def blob(page, logical, cx, cy, w, h, color):
    """A dot as the pen makes one: a pill along its long axis, as wide as the short."""
    box = page.locator("#pad").bounding_box()
    sx, sy = box["width"] / logical[0], box["height"] / logical[1]
    page.evaluate("([c, s]) => { color = c; size = s; }", [color, min(w, h)])
    half = max(0.4, (max(w, h) - min(w, h)) / 2)
    a = (cx - half, cy) if w >= h else (cx, cy - half)
    b = (cx + half, cy) if w >= h else (cx, cy + half)
    cdp = page.context.new_cdp_session(page)
    send(cdp, box, sx, sy, "mousePressed", *a)
    for i in range(1, 7):
        f = i / 6
        send(cdp, box, sx, sy, "mouseMoved", a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        time.sleep(0.008)
    send(cdp, box, sx, sy, "mouseReleased", *b, 0)
    cdp.detach()


def build(out_dir, browser):
    ctx = browser.new_context(viewport={"width": 1100, "height": 1500})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/flip")
    page.wait_for_timeout(900)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '9:16').id;
        const b = document.querySelector(`[data-size='${id}']`); if (b) b.click(); }""")
    page.wait_for_timeout(400)
    page.evaluate(f"""() => {{ setBg('#0b0d12'); onion = false; fps = {FPS};
        if (window.SkriblPressure) SkriblPressure.setEnabled(false);
        if (typeof setTool === 'function') setTool('pen'); }}""")
    cw, ch = page.evaluate("() => [CW, CH]")
    logical = [cw, ch]
    word, ts, dot, dot_t, s = fit(cw, ch)
    pen = mark()[3] * s                              # the mark's own pen, at this size

    # Page 0: the word, without its dot: Flip brings the dot in.
    write(page, logical, word, ts, pen)
    dcx, dcy = sum(p[0] for p in dot) / len(dot), sum(p[1] for p in dot) / len(dot)
    dot_d = 3.0 * s                                  # the dot as the mark paints it: a short curl of the same pen
    for dy, w, h in DOT_PAGES:
        page.evaluate("() => addFrame(false)")
        page.wait_for_timeout(60)
        blob(page, logical, dcx, dcy + dy * cw, dot_d * w, dot_d * h, sweep(dot_t))
    total = page.evaluate("() => frames.length")
    under = {"page": 0, "from": 1, "to": total - 1}
    # The word's page as the hand wrote it, fitted into WORD_MS: the pieces
    # run on with no beat between them (they are one movement of the hand).
    page.evaluate("""([ms]) => {
        const pts = frames[0].strokes; let shift = 0;
        for (let i = 1; i < pts.length; i++) {
          if (pts[i].start) { const gap = pts[i].t - shift - pts[i - 1].t; shift += Math.max(0, gap - 1); }
          pts[i].t -= shift; }
        const t0 = pts[0].t, k = ms / Math.max(1, pts[pts.length - 1].t - t0);
        pts.forEach(p => { p.t = Math.round(t0 + (p.t - t0) * k); }); }""", [WORD_MS])
    page.evaluate("""([under]) => { frames.forEach(f => { delete f.draw; }); frames[0].draw = true;
        docUnder = under; docLoop = null; idx = 0; buildStrip(); render(); }""", [under])
    page.wait_for_timeout(300)
    payload = page.evaluate("""async () => { const p = await buildSharePayload();
        for (const k of ['thumbnail', 'caption']) delete p[k]; return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"hello: page errors {errs[:2]}")
    for f in payload["frames"]:
        f["background"] = None
    (pathlib.Path(out_dir) / "hello.json").write_text(json.dumps(payload))
    f0 = payload["frames"][0]["strokes"]
    print(json.dumps({"pages": total, "under": payload.get("under"), "word_ms": f0[-1]["t"] - f0[0]["t"],
                      "pieces": sum(1 for p in f0 if p.get("start")),
                      "points": sum(len(f["strokes"]) for f in payload["frames"]),
                      "scale": round(s, 2), "pen": round(pen, 1)}), flush=True)


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    out = sys.argv[1] if len(sys.argv) > 1 else None
    if not out:
        raise SystemExit(__doc__)
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        build(out, b)
        b.close()
