#!/usr/bin/env python3
"""Draw How it works' artworks through the real Pad and keep what it records.

    python3 harness/tools/make_art.py cat        # one
    python3 harness/tools/make_art.py            # all

Each drawing (artworks.py) is performed with real pen input (artdraw.py) on a
4:3 Pad canvas in the paper colour, and the editor's own serialization is
saved to skribl/static/help/demos/<name>.json. Needs the local server.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import artdraw  # noqa: E402
import artworks  # noqa: E402
import browsing  # noqa: E402

OUT = ROOT / "skribl" / "static" / "help" / "demos"
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
# (hand, pauses): the owner found the hand fast at 1.9, so it is calmer and
# the gaps between strokes stay brisk.
TEMPO = {"snail": (1.45, 1.9), "cat": (1.35, 1.9), "scene": (1.35, 1.9),
         "footballer": (2.6, 3.2), "skull": (2.6, 3.2)}   # 53 strokes: a brisk hand, or it runs a minute


def make(browser, name):
    ctx = browser.new_context(viewport={"width": 1280, "height": 960})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/skribl-pad")
    page.wait_for_timeout(800)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        document.querySelector(`#canvasSeg button[data-size='${id}']`).click(); }""")
    page.wait_for_timeout(300)
    # Paper, so dark ink reads in both themes; and the pen, with pressure on.
    page.evaluate(f"""() => {{ bgColor = '{artdraw.PAPER}'; canvasWrap.style.backgroundColor = bgColor;
        if (typeof updateVignette === 'function') updateVignette(); setTool('pen');
        if (window.SkriblPressure) SkriblPressure.setEnabled(true); }}""")
    # Examples are short: a few seconds of a confident hand, not a study.
    hand, gaps = TEMPO.get(name, (1.35, 1.9))
    artdraw.draw(page, artworks.ART[name](), tempo=hand, pause_tempo=gaps)
    page.wait_for_timeout(300)
    payload = page.evaluate("""() => { if (recording) endRecordingTake(); const p = serializeSkribl();
        for (const k of ['draftId', 'createdAt', 'updatedAt', 'title', 'userId']) delete p[k];
        for (const f of p.frames) delete f.baseSnapshot;
        return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    f0 = payload["frames"][0]
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, separators=(",", ":")))
    sizes = [p["size"] for p in f0["strokes"]]
    print(f"{name}: {len(f0['strokeGroups'])} strokes, {len(sizes)} points, {f0['strokes'][-1]['t'] / 1000:.1f} s, "
          f"width {min(sizes):.1f}-{max(sizes):.1f}, {path.stat().st_size:,} B")


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    names = sys.argv[1:] or list(artworks.ART)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for n in names:
            make(b, n)
        b.close()
