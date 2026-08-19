"""player.css is a derived subset of styles.css. Does it still render the same?

The player linked all 123,547 bytes of styles.css and matched about a tenth of
it. `harness/tools/cssgraph.py` classifies each top-level block by asking a real
page whether any of its selectors matches anything, and emits player.css — the
matching blocks in their original relative order, plus every at-rule that cannot
be classified that way.

THE CLASSIFIER IS NOT THE GATE. It is a claim, and this file is what tests it.
Two assertions do the work and they are independent:

  1. REGENERATION. Re-run the tool and require the output to equal the committed
     player.css byte for byte. A derived file that nobody checks is a second
     copy waiting to drift, and this project has been bitten by exactly that.
     A rule edited in styles.css and not regenerated here is a red suite.

  2. PIXELS. Screenshot the player and both editors across eleven scenes and
     require every one to be unchanged against styles.css. This is the real
     gate, because it does not depend on the classification being right — if a
     rule was dropped that the player needed, the page looks different and this
     says so, whatever the tool believed.

WHY THE SHAPE IS A SUBSET AND NOT A SPLIT, recorded because the split was built
first and failed here. A shared base plus an editor overlay is the obvious
design and it does not work: kept and editor-only blocks interleave through
styles.css 113 and 530 times, so neither load order reproduces the original
cascade. Seven of eleven editor scenes rendered differently, editor-pad-phone by
24,867 pixels. A subset touches no editor at all — styles.css is unmodified and
both editors still load the whole of it — at the cost of duplication, which
assertion 1 converts from a discipline problem into a test failure.

FREEZING MATTERS AND element.style IS NOT ENOUGH. The first version paused
animations by iterating elements and setting `style.animationPlayState`. That
cannot reach ::before/::after, and Flip has a pulsing indicator drawn on one:
two runs of the SAME build differed in a 6x6 box, which read exactly like a
regression. An injected stylesheet covering `*, *::before, *::after` makes the
scenes deterministic — verified by shooting one page three times.
"""
import json
import math
import pathlib
import struct
import subprocess
import sys
import tempfile
import time
import socket
import os
import urllib.request
import zlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORT = 5017
BASE = f"http://127.0.0.1:{PORT}"
LIVE = ROOT / "harness" / "tools" / "css_live.json"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# FREEZE neutralises everything that is NOT what this suite tests. The suite
# tests that the CSS SPLIT produced an identical stylesheet — so transitions
# (timing-dependent), the caret (blink-phase), and, since v211, ANTI-ALIASED
# CURVES are removed from the comparison. Rounded corners rasterise with a
# 1-5 RGB coverage jitter between two Chromium renders of byte-identical CSS
# at integer geometry (GPU layer promotion / compositor path differences
# between pages); editor-pad's #tuneBtn corners failed exactly so, three
# times, across two builds, after its position had been pixel-snapped and
# the mouse parked. Squaring corners for the capture keeps the test
# zero-tolerance on what it is FOR and blind to rasteriser jitter. (Hover
# and pointer position are also parked per scene, in capture().)
FREEZE = """*, *::before, *::after {
  animation: none !important;
  transition: none !important;
  animation-play-state: paused !important;
  caret-color: transparent !important;
  border-radius: 0 !important;
}"""


def png_bytes(w=200, h=120):
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        for x in range(w):
            rows += bytes((x * 255 // w, y * 255 // h, 140))

    def ch(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(bytes(rows), 6)) + ch(b"IEND", b""))


def spiral():
    pts, n = [], 300
    for i in range(n):
        a, r = (i / n) * math.pi * 6, 20 + (i / n) * 200
        pts.append({"x": 408 + math.cos(a) * r, "y": 306 + math.sin(a) * r * 0.7,
                    "color": "#7cf", "size": 7, "t": 0, "erase": False,
                    "start": i == 0})
    return pts, [n]


env = dict(os.environ, DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/css.db",
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           SECRET_KEY="harness-cssplit")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    sys.exit("SKIP: instance did not start.")


def post(body):
    req = urllib.request.Request(BASE + "/api/skribls", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


try:
    from PIL import Image, ImageChops
except ImportError:
    proc.terminate()
    sys.exit("SKIP: Pillow is not installed; the pixel gate cannot run.")

try:
    print("\nCSS SPLIT — player.css is what the tool produces")
    if not LIVE.is_file():
        check("the recorded live-selector set is in the tree", False, str(LIVE))
    else:
        out = pathlib.Path(tempfile.mkdtemp()) / "player.css"
        subprocess.run([sys.executable, str(ROOT / "harness" / "tools" / "cssgraph.py"),
                        "--emit", str(LIVE), str(out)],
                       cwd=ROOT, check=True, capture_output=True)
        committed = (ROOT / "skribl" / "static" / "player.css").read_text()
        regenerated = out.read_text()
        check("regenerating from styles.css reproduces player.css byte for byte",
              committed == regenerated,
              f"committed {len(committed):,} vs regenerated {len(regenerated):,} "
              "— if this fails, styles.css was edited without re-emitting")

    styles = (ROOT / "skribl" / "static" / "styles.css").read_text()
    player = (ROOT / "skribl" / "static" / "player.css").read_text()
    check("the player's sheet is a real reduction, not a rename",
          len(player) < len(styles) * 0.5,
          f"{len(player):,} vs {len(styles):,} chars "
          f"({100 - len(player) * 100 // len(styles)}% smaller)")

    tpl = (ROOT / "skribl" / "templates" / "skribl").resolve()
    check("the player template links player.css and not styles.css",
          "player.css" in (tpl / "skribl_player.html").read_text()
          and "skribl_asset('styles.css')" not in (tpl / "skribl_player.html").read_text())
    check("and BOTH editors still link the whole of styles.css",
          all("skribl_asset('styles.css')" in (tpl / t).read_text()
              for t in ("skribl_editor.html", "skribl_flip.html")),
          "the subset must change nothing for an authoring surface")

    print("\nCSS SPLIT — nothing renders differently")
    pts, groups = spiral()
    frame = {"strokes": pts, "strokeGroups": groups,
             "background": {"color": "#101418"}}
    plain = post({"title": "p", "schemaVersion": 2, "visibility": "public",
                  "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                  "frames": [frame]})
    pframe = dict(frame)
    pframe["photo"] = {"data": "data:image/png;base64," + __import__("base64")
                       .b64encode(png_bytes()).decode(), "name": "p.png",
                       "fit": "cover", "opacity": 1, "blur": 0,
                       "offset": {"x": 0.5, "y": 0.5}, "zoom": 1}
    photo = post({"title": "ph", "schemaVersion": 2, "visibility": "public",
                  "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                  "frames": [pframe]})

    SCENES = [
        ("player-desktop", plain["url"], (1280, 900), []),
        ("player-phone", plain["url"], (390, 844), []),
        ("player-photo", photo["url"], (1280, 900), []),
        ("player-404", "/s/nope", (1280, 900), []),
        # v207: the loop/mute buttons' PRESSED state. Every player scene was
        # static, so .player-btn.active (a JS-toggled class, not the :active
        # pseudo) never matched at rest and cssgraph dropped it from
        # player.css — the Repeat button worked but never lit up, so it read
        # as dead. .player-btn.active is now in css_live.json directly and the
        # ux suite proves the button lights; this scene pixel-compares the
        # pressed render. It is LAST so its click/focus state cannot bleed into
        # a following editor scene (it did: a 4px focus strip on the Pad tune
        # button differed between passes when this scene preceded editor-pad).

        ("editor-pad", "/", (1280, 900), []),
        ("editor-pad-phone", "/", (390, 844), []),
        ("editor-flip", "/flip", (1280, 900), []),
        ("editor-flip-phone", "/flip", (390, 844), []),
        ("editor-menu", "/", (1280, 900), ["menu"]),
        ("editor-export", "/", (1280, 900), ["menu", "export"]),
        ("editor-help", "/flip", (1280, 900), ["help"]),
        ("player-pressed", plain["url"], (1280, 900), ["loop", "mute"]),
    ]

    shots = pathlib.Path(tempfile.mkdtemp())

    # v211: because FREEZE squares corners for the pixel comparison, the split
    # could in principle drop a border-radius without this suite seeing it.
    # So radius is compared by COMPUTED STYLE instead, on the player's
    # controls, between the split sheet and the full one — the same
    # before/after the pixel test uses, exact, and immune to rasteriser jitter.
    def radii(b, override):
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        if override:
            pg.route("**/player.css*", lambda route: route.fulfill(
                status=200, content_type="text/css", body=styles))
        pg.goto(BASE + plain["url"], wait_until="load")
        pg.wait_for_timeout(1200)
        out = pg.evaluate("""() => {
          const sels = ['#playerPlayBtn', '#playerRestartBtn', '#playerLoopBtn', '.player-btn', '#playerShell', '.brand-mark'];
          const o = {};
          for (const s of sels) { const e = document.querySelector(s); if (e) o[s] = getComputedStyle(e).borderRadius; }
          return o; }""")
        pg.close()
        return out

    def capture(b, override, tag):
        """Shoot every scene, optionally forcing the player back onto styles.css."""
        for name, path, (vw, vh), acts in SCENES:
            pg = b.new_page(viewport={"width": vw, "height": vh})
            if override:
                # Serve the player the FULL stylesheet, so the "before" side of
                # the comparison is the pre-split rendering rather than another
                # copy of the same build.
                pg.route("**/player.css*", lambda route: route.fulfill(
                    status=200, content_type="text/css", body=styles))
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(1800)
            # v211: park the pointer. Pages share one browser context, and the
            # mouse position persists across new_page(); if the previous pass's
            # last scene left it over where a control lands in THIS scene, that
            # control is :hover in one pass and not the other — a 1-3 RGB
            # anti-aliasing delta on its rounded corners, and a zero-tolerance
            # pixel test rightly fails. editor-pad's #tuneBtn at (715,32-66)
            # failed exactly so, twice, after v210 had already pixel-snapped
            # its position. Hover state is part of the scene; fix it.
            pg.mouse.move(0, vh - 1)
            # Freeze BEFORE the clicks as well as after. Applying it only at the
            # end catches any sheet-open transition partway through, and where
            # it got to depends on timing — which is how editor-export came out
            # differing in a 135x4 strip between two passes that were served
            # byte-identical CSS.
            pg.add_style_tag(content=FREEZE)
            try:
                if "menu" in acts:
                    pg.click("#menuBtn", timeout=2500); pg.wait_for_timeout(600)
                if "export" in acts:
                    pg.click("#exportItem", timeout=2500); pg.wait_for_timeout(800)
                if "help" in acts:
                    pg.click("#helpBtn", timeout=2500); pg.wait_for_timeout(800)
                if "loop" in acts:
                    pg.click("#playerLoopBtn", timeout=2500); pg.wait_for_timeout(300)
                if "mute" in acts:
                    pg.click("#playerMuteBtn", timeout=2500); pg.wait_for_timeout(300)
            except Exception:
                pass
            pg.add_style_tag(content=FREEZE)
            pg.wait_for_timeout(400)
            # v210: settle JS-driven LAYOUT too, not just CSS transitions. The
            # header's fitBrand runs on ResizeObserver + requestAnimationFrame
            # and sheds classes by measuring; under batch load one pass could
            # capture a frame before that settled and the other after — a 4x34
            # strip at the cluster's edge differed between two byte-identical
            # passes (batch 18 of the v210 run; 17/17 in isolation). Two frames
            # is what a rAF-driven fit needs to converge, and a settled DOM is
            # a precondition of a pixel comparison, not something to hope for.
            pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            pg.screenshot(path=str(shots / f"{tag}-{name}.png"))
            pg.close()

    with sync_playwright() as sp:
        b = sp.chromium.launch()
        capture(b, True, "full")       # player served the whole styles.css
        capture(b, False, "subset")    # player served the committed player.css
        # Radii, by computed style (see radii() — the pixel pass squares them).
        _rf, _rs = radii(b, True), radii(b, False)
        check("player.css keeps every control's border-radius identical to styles.css "
              "(computed style; the pixel pass deliberately squares corners)",
              _rf == _rs and len(_rf) >= 3, f"full {_rf} vs subset {_rs}")

        # GATE. If the two capture passes produced identical bytes for a scene
        # the player does not even style, the comparison proves nothing. Require
        # the fixture to have actually rendered something.
        sizes = [(shots / f"subset-{n}.png").stat().st_size for n, *_ in SCENES]
        check("FIXTURE GATE: every scene produced a real screenshot",
              all(s > 3000 for s in sizes),
              f"smallest {min(sizes):,} B")

        for name, *_ in SCENES:
            a = Image.open(shots / f"full-{name}.png").convert("RGB")
            c = Image.open(shots / f"subset-{name}.png").convert("RGB")
            if a.size != c.size:
                check(f"{name} renders identically", False,
                      f"size {a.size} -> {c.size}")
                continue
            bbox = ImageChops.difference(a, c).getbbox()
            check(f"{name} renders identically", bbox is None,
                  "pixel-identical" if bbox is None else f"differs in {bbox}")
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

bad = [n for ok, n, _ in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed")
for ok, n, d in results:
    if not ok:
        print(f"  FAILED: {n}\n          {d or '(no measured value reported)'}")
sys.exit(1 if bad else 0)
