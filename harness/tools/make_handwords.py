#!/usr/bin/env python3
"""Write the empty canvas's words in the owner's hand through the real Pad, and keep what it records.

    python3 harness/tools/make_handwords.py

"Draw anything" (the Pad) and "Draw page 1" (Flip) are written by the real Text
tool in Skribl's style (the owner's own hand, fonts/text-skribl.json), as a
person uses it (make_art.write_words: Shape's picker, Text, the style, size L,
the hand's own pace, the words typed, placed, Write it), on a 4:3 Pad canvas.
The Pad's own serialization of each is cropped to its ink, thinned to points a
quarter of a pen's width apart, given the player's tight pauses between strokes
(50 ms, as the "Empty canvas ideas" mock was filmed) and fitted to the time the
owner chose ("about 2 seconds, as filmed": 1.9 s and 1.7 s). The result is
written between lib/handwords.js's MARK:BEGIN and MARK:END markers.

It also writes what a site's post box shows once (lib/handwords.js, the snail):
How it works' snail and Flip's bouncing ball, cropped to their ink, without
their paper, page pictures or sound, thinned the same way, the ball in Skribl
purple, to skribl/static/brand/hint-snail.json and hint-ball.json.

Needs the local server.
"""
import json
import math
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402
import make_art  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
TARGET = ROOT / "skribl" / "static" / "lib" / "handwords.js"
DEMOS = ROOT / "skribl" / "static" / "help" / "demos"
BRAND = ROOT / "skribl" / "static" / "brand"
PEN = 9                       # the pen the words are written with, in the Pad's points
WORDS = {"Draw anything": 1900, "Draw page 1": 1700}   # the words, and the time they take
GAP = 50                      # the player's tight pause between strokes (inlineplayer.js PAUSE_CAPS)
PURPLE = "#7c5cff"


class Words:   # what make_art.write_words reads
    def __init__(self, text):
        self.text, self.at, self.style, self.size, self.color, self.pen = text, (408, 306), "skribl", "L", "#1f1b2e", PEN


def strokes_of(frame):
    pts, out, i = frame["strokes"], [], 0
    for n in frame["strokeGroups"]:
        out.append(pts[i:i + n]); i += n
    return out


def thin(stroke, step):
    """Points at least `step` apart, the stroke's first and last kept."""
    keep = [stroke[0]]
    for q in stroke[1:-1]:
        if math.hypot(q["x"] - keep[-1]["x"], q["y"] - keep[-1]["y"]) >= step:
            keep.append(q)
    if len(stroke) > 1:
        keep.append(stroke[-1])
    return keep


def record(page, text):
    browsing.goto(page, BASE, "/skribl-pad")
    page.wait_for_timeout(800)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    make_art.write_words(page, Words(text))
    return page.evaluate("() => { if (recording) endRecordingTake(); return serializeSkribl(); }")


def fitted(payload, ms):
    """The words as [x, y, t, x, y, t, ...] per stroke in their own box, timed to `ms`."""
    S = [thin(s, PEN / 4) for s in strokes_of(payload["frames"][0])]
    pad = PEN / 2 + 2
    x0 = min(q["x"] for s in S for q in s) - pad; y0 = min(q["y"] for s in S for q in s) - pad
    x1 = max(q["x"] for s in S for q in s) + pad; y1 = max(q["y"] for s in S for q in s) + pad
    # The hand's own time within each stroke; between strokes, the player's tight pause.
    clock, prev_end, timed = 0.0, None, []
    for s in S:
        if prev_end is not None:
            clock += min(GAP, max(0, s[0]["t"] - prev_end))
        start = s[0]["t"]
        timed.append([(q["x"] - x0, q["y"] - y0, clock + (q["t"] - start)) for q in s])
        clock += s[-1]["t"] - start
        prev_end = s[-1]["t"]
    k = ms / max(1.0, clock)
    out = [[v for x, y, t in s for v in (round(x, 1), round(y, 1), round(t * k))] for s in timed]
    return {"box": [round(x1 - x0, 1), round(y1 - y0, 1)], "size": PEN, "ms": ms, "strokes": out}


def trimmed(name, recolor=None, step=1.5, pad=14):
    """How it works' recording, cropped to its ink, with nothing but its strokes, `step` apart."""
    d = json.loads((DEMOS / f"{name}.json").read_text())
    frames = d.get("frames") or [d]
    xs = [q["x"] for f in frames for q in f.get("strokes") or []]
    ys = [q["y"] for f in frames for q in f.get("strokes") or []]
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    for f in frames:
        kept = []
        groups = []
        for s in strokes_of(f):
            t = thin(s, step)
            for i, q in enumerate(t):
                q = dict(q, x=round(q["x"] - x0, 1), y=round(q["y"] - y0, 1), size=round(q["size"], 1))
                if recolor and q.get("color"):
                    q["color"] = recolor
                if i == 0:
                    q["start"] = True
                else:
                    q.pop("start", None)
                kept.append(q)
            groups.append(len(t))
        f["strokes"], f["strokeGroups"], f["background"] = kept, groups, None
        for k in ("photo", "baseSnapshot", "music"):
            f.pop(k, None)
    for k in ("background", "photo", "baseSnapshot", "music", "thumbnail", "title"):
        d.pop(k, None)
    d["canvasSize"] = {"cssWidth": round(x1 - x0), "cssHeight": round(y1 - y0), "dpr": 1}
    return d


def main():
    from playwright.sync_api import sync_playwright
    marks = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for text, ms in WORDS.items():
            ctx = b.new_context(viewport={"width": 1280, "height": 960})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            payload = record(page, text)
            ctx.close()
            if errs:
                raise SystemExit(f"page errors writing {text!r}: {errs[:2]}")
            marks[text] = fitted(payload, ms)
        b.close()
    src = TARGET.read_text()
    body = "var WORDS = " + json.dumps(marks, separators=(",", ":")) + ";"
    new, n = re.subn(r"(MARK:BEGIN[^\n]*\n)\s*var WORDS = .*?;\n", lambda m: m.group(1) + "  " + body + "\n",
                     src, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("could not find the MARK block in " + str(TARGET))
    TARGET.write_text(new)
    for text, m in marks.items():
        pts = sum(len(s) // 3 for s in m["strokes"])
        print(f"{text!r}: {len(m['strokes'])} strokes, {pts} points, box {m['box']}, {m['ms']} ms")
    # The ball's pages are shown whole, ten of them, at 0.43 of their size: points two
    # screen pixels apart keep its round, at a third of the weight.
    for name, out, recolor, step in (("snail", "hint-snail.json", None, 1.5), ("flip-bounce", "hint-ball.json", PURPLE, 4)):
        d = trimmed(name, recolor, step)
        (BRAND / out).write_text(json.dumps(d, separators=(",", ":")))
        n = sum(len(f["strokes"]) for f in (d.get("frames") or [d]))
        print(f"{out}: {n} points, {(BRAND / out).stat().st_size // 1024} KB, {d['canvasSize']}")


if __name__ == "__main__":
    main()
