#!/usr/bin/env python3
"""The small previews on How it works' "Watch it work" bar.

    python3 harness/tools/make_help_thumbs.py

Each is a still of a finished example as the real panel shows it: the editor
is opened with reduced motion asked for, so every card in the examples drawer
holds its finished drawing, and each named card's stage is captured and saved
to skribl/static/help/thumbs/<name>.webp at twice the bar's 52 x 39. The bar
shows three per editor (skribl/templates/skribl/_skribl_help.html names them);
run this again after redrawing one of them. Needs the local server.
"""
import io
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402
from PIL import Image  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
OUT = ROOT / "skribl" / "static" / "help" / "thumbs"
# route -> the examples whose previews that editor's bar shows
BARS = {"/skribl-pad": ["cat", "pen", "scene"], "/flip": ["flip-wave", "flip-bounce"]}
SIZE = (104, 78)


def main():
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for route, names in BARS.items():
            ctx = b.new_context(viewport={"width": 1200, "height": 900}, device_scale_factor=2,
                                reduced_motion="reduce")
            pg = ctx.new_page()
            browsing.goto(pg, BASE, route)
            pg.wait_for_timeout(800)
            pg.evaluate("() => { window.SkriblHints && SkriblHints.hide(); openHelpDrawer(); }")
            pg.wait_for_timeout(400)
            pg.click("#learnPeek")
            pg.wait_for_timeout(2500)
            for name in names:
                stage = pg.locator(f'#learnSheet .learn-card[data-demo-name="{name}"] .learn-stage')
                stage.scroll_into_view_if_needed()
                pg.wait_for_timeout(200)
                im = Image.open(io.BytesIO(stage.screenshot())).convert("RGB")
                im = im.resize(SIZE, Image.LANCZOS)
                path = OUT / f"{name}.webp"
                im.save(path, "WEBP", quality=82, method=6)
                print(f"{name:12s} {path.stat().st_size:6,d} B  {path.relative_to(ROOT)}")
            ctx.close()
        b.close()


if __name__ == "__main__":
    main()
