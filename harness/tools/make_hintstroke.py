#!/usr/bin/env python3
"""Draw the empty canvas's one stroke through the real Pad and keep what it records.

    python3 harness/tools/make_hintstroke.py

The stroke under "Draw anything" (lib/hintstroke.js, the owner's B after the
"Skribl's first look" mock) is a recording, like every example in How it
works: it is performed here with real pen input (artdraw.py: Chrome's own pen
events with pressure, the hand's timing from handmotion.py) on a 4:3 Pad
canvas, three times its size on screen so the hand has room, and the Pad's own
serialization of it is scaled back into the 200 x 40 box lib/hintstroke.js
draws in. The points are written between that file's MARK:BEGIN and MARK:END
markers. Needs the local server.
"""
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import artdraw  # noqa: E402
import browsing  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
TARGET = ROOT / "skribl" / "static" / "lib" / "hintstroke.js"
K = 3.0                     # drawn three times the size it shows
ORIGIN = (108.0, 246.0)     # where the 600 x 120 box sits on the 816 x 612 canvas
DURATION = 1000             # the recording's clock, scaled to a second of writing

# The line, in the 200 x 40 box: in from the left with a slight rise, one
# small loop (up its right side, over, down its left), and out to the right,
# lifting at the end.
PATH = [(8, 27), (34, 26.2), (58, 25.2), (78, 25.4), (95, 21), (101, 11.5), (93, 4.5), (83, 9.5), (85, 20.5),
        (98, 26), (124, 25.6), (150, 24.4), (172, 21), (190, 14)]


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 960})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(page, BASE, "/skribl-pad")
        page.wait_for_timeout(800)
        page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
        page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
            document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
        page.wait_for_timeout(300)
        page.evaluate("""() => { setTool('pen'); if (window.SkriblPressure) SkriblPressure.setEnabled(true); }""")
        pts = [(ORIGIN[0] + x * K, ORIGIN[1] + y * K) for x, y in PATH]
        artdraw.draw(page, [artdraw.Stroke(pts, role="contour", color=artdraw.PURPLE, size=18, taper=(0.14, 0.24))],
                     seed=7, tempo=1.0)
        page.wait_for_timeout(300)
        payload = page.evaluate("() => { if (recording) endRecordingTake(); return serializeSkribl(); }")
        ctx.close(); b.close()
    if errs:
        raise SystemExit(f"page errors: {errs[:2]}")
    f0 = payload["frames"][0]
    pts = f0["strokes"]
    if len(f0["strokeGroups"]) != 1:
        raise SystemExit(f"expected one stroke, the Pad recorded {len(f0['strokeGroups'])}")
    t0, t1 = pts[0]["t"], pts[-1]["t"]
    mark = [[round((q["x"] - ORIGIN[0]) / K, 1), round((q["y"] - ORIGIN[1]) / K, 1), round(q["size"] / K, 2),
             round((q["t"] - t0) * DURATION / max(1, t1 - t0))] for q in pts]
    src = TARGET.read_text()
    body = "var MARK = " + json.dumps(mark, separators=(",", ":")) + ";"
    new, n = re.subn(r"(MARK:BEGIN[^\n]*\n[^\n]*\n)\s*var MARK = .*?;\n", lambda m: m.group(1) + "  " + body + "\n", src, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("could not find the MARK block in " + str(TARGET))
    TARGET.write_text(new)
    ws = [m[2] for m in mark]
    print(f"{len(mark)} points over {t1 - t0} ms recorded, kept as {DURATION} ms; width {min(ws)}-{max(ws)}; "
          f"x {min(m[0] for m in mark)}-{max(m[0] for m in mark)}, y {min(m[1] for m in mark)}-{max(m[1] for m in mark)}")


if __name__ == "__main__":
    main()
