#!/usr/bin/env python3
"""Draw How it works' Flip loops through the real Flip and keep what it records.

    python3 harness/tools/make_flip.py bounce

The fixed layer (flipworks: "base") is drawn on page 1 with real pen input and
the page duplicated for every page, so it is identical throughout; then each
page's own strokes are drawn, key poses first ("order"), with onion skin on, as
an animator works. Saved to skribl/static/help/demos/flip-<name>.json.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import artdraw  # noqa: E402
import browsing  # noqa: E402
import flipworks  # noqa: E402

OUT = ROOT / "skribl" / "static" / "help" / "demos"
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")


def make(browser, name):
    spec = flipworks.FLIPS[name]()
    ctx = browser.new_context(viewport={"width": 1280, "height": 960})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(page, BASE, "/flip")
    page.wait_for_timeout(900)
    page.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
    page.evaluate("""() => { const t = window.SkriblCanvasSizes, id = t.SIZES.find(s => s.label === '4:3').id;
        const b = document.querySelector(`[data-size='${id}']`); if (b) b.click(); }""")
    page.wait_for_timeout(300)
    page.evaluate(f"""() => {{ setBg('{artdraw.PAPER}'); onion = true; onionDepth = 1;
        fps = {spec['fps']}; if (window.SkriblPressure) SkriblPressure.setEnabled(true);
        if (typeof setTool === 'function') setTool('pen'); }}""")
    logical = page.evaluate("() => [CW, CH]")
    draw = lambda strokes, seed: artdraw.draw(page, strokes, seed=seed, canvas="#pad", logical=logical)
    n = len(spec["pages"])
    # The fixed layer, then a duplicate per page: identical proportions throughout.
    draw(spec["base"], 1)
    for _ in range(n - 1):
        page.evaluate("() => addFrame(true)")
    page.wait_for_timeout(300)
    for k, i in enumerate(spec["order"]):
        page.evaluate("i => go(i)", i)
        page.wait_for_timeout(150)
        draw(spec["pages"][i], 10 + i)
    page.wait_for_timeout(300)
    # Every page as it is, onion off: the squash on a one-page contact is
    # exactly what a sampled replay GIF skips, so review reads these.
    if os.environ.get("FLIP_PAGES"):
        d = pathlib.Path(os.environ["FLIP_PAGES"]); d.mkdir(parents=True, exist_ok=True)
        page.evaluate("() => { onion = false; }")
        for i in range(n):
            page.evaluate("i => go(i)", i); page.wait_for_timeout(120)
            page.locator("#pad").screenshot(path=str(d / f"{name}-p{i:02d}.png"))
        page.evaluate("() => go(0)")
    # The body Flip's own Share posts -- not the draft (serializeFlip), whose
    # frames carry the background as a bare string the player does not read.
    payload = page.evaluate("""async () => { const p = await buildSharePayload();
        for (const k of ['thumbnail', 'title', 'caption', 'visibility']) delete p[k];
        return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    path = OUT / f"flip-{name}.json"
    path.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"flip-{name}: {len(payload['frames'])} pages at {payload.get('fps')} fps, "
          f"{sum(len(f['strokes']) for f in payload['frames'])} points, {path.stat().st_size:,} B")


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for n in sys.argv[1:] or list(flipworks.FLIPS):
            make(b, n)
        b.close()
