#!/usr/bin/env python3
"""Look at an artwork the way a viewer will, before anyone else does.

    python3 harness/tools/review_art.py OUTDIR cat [more ...]

For each drawing: posts it to the LOCAL server, opens it in the real player
(/s/<id>), and writes the finished drawing in light and dark, on a phone and
a desktop, plus a replay GIF -- the self-check the owner's brief asks for
before anything is shown. Nothing here posts anywhere but the local server.
"""
import io
import json
import os
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import browsing  # noqa: E402
from PIL import Image  # noqa: E402

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")


def post(name):
    payload = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / f"{name}.json").read_text())
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["id"], payload


def main(out, names):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name in names:
            sid, payload = post(name)
            for dev, (w, h, mob) in {"phone": (390, 844, True), "desk": (1280, 900, False)}.items():
                for theme in ("dark", "light"):
                    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2,
                                        is_mobile=mob, has_touch=mob, color_scheme=theme)
                    pg = ctx.new_page(); browsing.goto(pg, BASE, f"/s/{sid}"); pg.wait_for_timeout(1800)
                    pg.screenshot(path=str(out / f"{name}-{dev}-{theme}.png"))
                    ctx.close()
            # The replay, as a GIF: the canvas, sampled through one play.
            ctx = b.new_context(viewport={"width": 900, "height": 760}, device_scale_factor=1, color_scheme="dark")
            pg = ctx.new_page(); browsing.goto(pg, BASE, f"/s/{sid}"); pg.wait_for_timeout(1500)
            r = pg.locator("#canvas").bounding_box()
            pg.click("#playerPlayBtn"); t0 = time.time(); frames = []
            while True:
                frames.append(Image.open(io.BytesIO(pg.screenshot(clip=r))).convert("RGB").resize((480, 360)))
                done = pg.evaluate("() => !document.getElementById('playerPlayBtn').classList.contains('is-playing') && "
                                   "document.getElementById('playerProgressFill').style.width === '100%'")
                if done or time.time() - t0 > 40:
                    break
                pg.wait_for_timeout(90)
            for _ in range(12):
                frames.append(frames[-1])
            frames[0].save(out / f"{name}-replay.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
            ctx.close()
            print(name, sid, len(frames), "frames")
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
