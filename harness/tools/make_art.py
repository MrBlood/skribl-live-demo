#!/usr/bin/env python3
"""Draw How it works' artworks through the real Pad and keep what it records.

    python3 harness/tools/make_art.py cat        # one
    python3 harness/tools/make_art.py            # all

Each drawing (artworks.py) is performed with real pen input (artdraw.py) on a
4:3 Pad canvas in the paper colour (or the drawing's own ground, GROUND), and
the editor's own serialization is saved to skribl/static/help/demos/<name>.json.
A drawing in SPEEDUP has its recorded clock shortened by that factor before it
is saved. Needs the local server.
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
import blooby  # noqa: E402
import browsing  # noqa: E402

OUT = ROOT / "skribl" / "static" / "help" / "demos"
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
# (hand, pauses): the owner found the hand fast at 1.9, so it is calmer and
# the gaps between strokes stay brisk.
TEMPO = {"snail": (1.45, 1.9), "cat": (2.4, 3.0), "scene": (1.35, 1.9),
         "footballer": (2.6, 3.2), "skull": (2.6, 3.2), "pug": (3.0, 7.0),   # 53 strokes: a brisk hand, or it runs a minute
         "blooby-card": blooby.CARD_TEMPO,
         "recolor": (2.2, 3.0),   # nine strokes and three colours: a dozen seconds, not twenty
         "text": (1.4, 2.2),      # one calm line round the bubble; the words keep the hand's own pace
         "mirror": (1.6, 2.2)}    # nine strokes, each drawn twice at once
# The card is 70 strokes, colouring most of it, and runs 1:18 as drawn. A quicker
# hand thins the pen's events until the small curves go faceted and lines stop
# short, so it is drawn at its careful pace and replays that much faster.
SPEEDUP = {"blooby-card": blooby.CARD_REPLAY_SPEEDUP}
# A ground other than paper: the ivory card would barely part from paper.
GROUND = {"blooby-card": blooby.TABLE}
# A taller window: the Text sheet keeps the words clear of itself (lib/textwrite.js
# clampAnchor), and at 960 it rests over the canvas's lower part, which moved
# "hello!" 24px up out of the middle of its bubble.
VIEWPORT = {"text": (1280, 1600)}
# Drawn with Mirror on, as a person sets it in Tune: the right half draws itself.
MIRROR = {"mirror": "vertical"}


def recolor_after(page, taps):
    """Recolor's drawing: with the take still recording, each tap gives a line
    the pen's colour, as a person would, so the replay shows it change at
    that moment (lib/recolorplay.js). A quick click, so it is a tap."""
    box = page.locator("#canvas").bounding_box()
    lg = page.evaluate("() => { const s = getCanvasLogicalSize(); return [s.width, s.height]; }")
    cdp = page.context.new_cdp_session(page)
    for hexc, (x, y) in taps:
        page.evaluate("(h) => { setPenColor(h); SkriblPadRecolor.arm(); }", hexc)
        page.wait_for_timeout(700)
        cx, cy = box["x"] + x * box["width"] / lg[0], box["y"] + y * box["height"] / lg[1]
        for t in ("mousePressed", "mouseReleased"):
            cdp.send("Input.dispatchMouseEvent", {"type": t, "x": cx, "y": cy, "button": "left",
                                                  "buttons": 1 if t == "mousePressed" else 0, "clickCount": 1, "pointerType": "mouse"})
        page.wait_for_timeout(900)
    page.evaluate("() => SkriblPadRecolor.disarm()")
    cdp.detach()
    page.wait_for_timeout(300)


def write_words(page, w):
    """The Text tool, as a person uses it: Text in Shape's picker opens the
    sheet; the words typed; the style and size picked; the words placed with
    their middle at w.at (the tap that says where they go); 1x, the hand's
    own pace; Write it. They write themselves in while the take records, in
    the pen's colour and thickness."""
    page.evaluate("([c, s]) => { color = c; size = s; }", [w.color, w.pen])
    page.evaluate("() => document.querySelector('#shapeSeg [data-shape=\"text\"]').click()")
    page.wait_for_function("() => window.SkriblText && SkriblText.isOpen()")
    page.evaluate("(p) => SkriblText.place(p)", {"x": w.at[0], "y": w.at[1]})
    page.wait_for_function("(s) => !!document.querySelector('#txStyles [data-style=\"' + s + '\"][data-face=\"drawn\"]')",
                           arg=w.style, timeout=15000)
    page.click(f'#txStyles [data-style="{w.style}"]')
    page.click(f'#txSize [data-size="{w.size}"]')
    page.evaluate("""() => { const s = document.getElementById('txSpeed'); s.value = String(SkriblText.SPEEDS.indexOf(1));
        s.dispatchEvent(new Event('input', { bubbles: true })); }""")
    page.evaluate("(t) => { const f = document.getElementById('txField'); f.value = t; f.dispatchEvent(new Event('input', { bubbles: true })); }",
                  w.text)
    page.wait_for_function("() => { const p = SkriblText.plan(); return !!p && p.strokes.length > 0; }", timeout=15000)
    page.wait_for_timeout(400)
    page.click("#txGo")
    page.wait_for_function("() => !SkriblText.isWriting()", timeout=60000)
    page.wait_for_timeout(500)


def perform(page, items, hand, gaps):
    """Strokes drawn with the pen; a Words written by the Text tool, between."""
    run = []
    for it in items + [None]:
        if isinstance(it, artworks.Words) or it is None:
            if run:
                artdraw.draw(page, run, tempo=hand, pause_tempo=gaps)
                run = []
            if it is not None:
                page.wait_for_timeout(500)
                write_words(page, it)
        else:
            run.append(it)


def make(browser, name):
    w, h = VIEWPORT.get(name, (1280, 960))
    ctx = browser.new_context(viewport={"width": w, "height": h})
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
    page.evaluate(f"""() => {{ bgColor = '{GROUND.get(name, artdraw.PAPER)}'; canvasWrap.style.backgroundColor = bgColor;
        if (typeof updateVignette === 'function') updateVignette(); setTool('pen');
        if (window.SkriblPressure) SkriblPressure.setEnabled(true); }}""")
    if name in MIRROR:
        page.evaluate("(m) => document.querySelector('#mirrorSeg [data-mirror=\"' + m + '\"]').click()", MIRROR[name])
    # Examples are short: a few seconds of a confident hand, not a study.
    hand, gaps = TEMPO.get(name, (1.35, 1.9))
    perform(page, artworks.ART[name](), hand, gaps)
    page.wait_for_timeout(300)
    if name == "recolor":
        recolor_after(page, artworks.RECOLOR_TAPS)
    payload = page.evaluate("""() => { if (recording) endRecordingTake(); const p = serializeSkribl();
        for (const k of ['draftId', 'createdAt', 'updatedAt', 'title', 'userId']) delete p[k];
        for (const f of p.frames) delete f.baseSnapshot;
        return p; }""")
    ctx.close()
    if errs:
        raise SystemExit(f"{name}: page errors {errs[:2]}")
    if name in SPEEDUP:
        for f in payload["frames"]:
            for pt in f["strokes"]:
                pt["t"] = round(pt["t"] / SPEEDUP[name])
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
