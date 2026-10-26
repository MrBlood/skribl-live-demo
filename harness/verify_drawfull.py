#!/usr/bin/env python3
"""Draw in full screen, on a desk (the owner's A, "All yes", built on B).

The owner: "Is there any way that when canvas opens on a desktop it can have
a full screen button so it opens over everything else to full screen? So if
you're on a giant screen the editor/canvas can be huge?" B let the canvas use
the window; A puts the page itself in full screen, the header and the dock
with it, from a button at the dock's end after Magnify, on a desk only, and
the drawers open where they open today. lib/drawfull.js, one module for both
editors; going full screen is lib/immersive.js.

The rows, on both editors:

  THE BUTTON. On a 1920x945 desk window, light and dark, the dock ends with
  it, after Magnify; it is drawn at Magnify's 26px at the same 1.8px line, in
  Magnify's ink, as far from Magnify as Magnify is from Media (one rhythm at
  the right end), and it is named for what it does.

  IN AND OUT. Pressed, the page itself goes full screen and the header and
  the dock are still on it; the button then says how out ("Leave full screen
  (Esc)"), is pressed, and wears the dock's on tile, as Magnify does. Pressed
  again, the page comes back out and the button says so. With the window the
  screen's size, as a real full screen makes it, the canvas shows at the
  mock's sizes (the Pad's cat 1197x898 on a 1920x1080 screen, Flip's card
  932x699). A drawer opens where it opens out of full screen, under the dock.

  THE WATCH STILL WORKS. Playing the drawing big from here and leaving it
  comes back to the page in full screen, the button still pressed. And the
  page going in and out is not the watch's news: leaving with nothing focused
  does not hand focus to the watch's button (lib/immersive.js reports only a
  change of its own; every full screen fires the same event).

  WHERE IT FITS. In a 721px window, the narrowest it shows in, the dock holds
  it, painted, without clipping (at 641 the Pad's dock ran 26px past its
  edge).

  WHERE IT IS NOT. Not on a phone, not on a touch screen at a desk's width,
  not in a window 720px wide, and not where the page cannot go full screen
  (an iPhone, a frame that does not allow it), asked the way such a browser
  answers: requestFullscreen is there and fullscreenEnabled says no. (The
  editors refuse a frame from another site, frame-ancestors 'self', and a
  frame of their own site may go full screen, so no frame here says no.)

NOT TESTED HERE: Escape. In a real full screen the browser owns that key;
headless Chrome does not hand it over, so the way out tried here is the
button (and the API's own exit). A real full screen's size: headless Chrome
keeps the window's size in full screen, so the sizes are asked of a window
the screen's size.

For calibration: DRAWFULL_PART=button (inout, watch, not) runs one part, and
DRAWFULL_ONLY=Pad (or Flip) one editor. A real run sets neither.
"""
import json
import os
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the editors draw in full screen.")
    raise SystemExit(77)
import browsing  # noqa: E402

ONLY = os.environ.get("DRAWFULL_ONLY", "")
PART = os.environ.get("DRAWFULL_PART", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = {"Pad": json.load(open(os.path.join(ROOT, "skribl/static/help/demos/cat.json"))),
        "Flip": json.load(open(os.path.join(ROOT, "skribl/static/help/demos/flip-blooby-card.json")))}
ROUTE = {"Pad": "/skribl-pad", "Flip": "/flip"}
LOAD = {"Pad": "(d) => { loadSkribl(d); }", "Flip": "(d) => { applyFlipDraftObject(d); }"}
CANVAS = {"Pad": "canvas", "Flip": "pad"}
DOCK = {"Pad": "#toolBar", "Flip": ".flip-tools"}
UNDO = {"Pad": "#undoBtn", "Flip": "#undo"}
# The watch's way in, at the end of the Pad's line and Flip's speed row,
# which show while the drawing plays.
WATCH_BTN = {"Pad": "#padLine .full-btn", "Flip": "#flipSpeeds .full-btn"}
PLAY = {"Pad": "#playBtn", "Flip": "#play"}
# The mock's sizes in full screen (the owner's yes was to these).
FULL = {("Pad", 1920): (1197, 898), ("Flip", 1920): (932, 699)}
EDITORS = [e for e in ("Pad", "Flip") if not ONLY or e == ONLY]


def part(name):
    return not PART or PART == name


def eds(name):
    return EDITORS if part(name) else []


def editor(b, name, w=1920, h=945, theme="light", init=None, **extra):
    c = b.new_context(viewport={"width": w, "height": h}, color_scheme=theme, **extra)
    if init:
        c.add_init_script(init)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, ROUTE[name])
    pg.evaluate("() => localStorage.clear()")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    pg.evaluate(LOAD[name], DEMO[name])
    pg.wait_for_timeout(1300)
    return c, pg, errs


# The button as it shows: where, in what order, what it is called, and
# whether what is painted at its middle is it. Its words under the pointer are
# the title, which lib/tooltip.js moves to data-tip for its own bubble.
BTN = """(dock) => { const b = document.getElementById('drawFullBtn'), m = document.getElementById('magnifyBtn');
  if (!b) return null;
  const r = b.getBoundingClientRect(), mr = m.getBoundingClientRect(), d = document.querySelector(dock);
  const shown = !b.hidden && b.offsetParent !== null && r.width > 0;
  const hit = shown ? document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) : null;
  const kids = [...d.querySelectorAll('button')].filter((e) => e.offsetParent !== null && e.getBoundingClientRect().width > 0);
  const svg = b.querySelector('svg'), sr = svg.getBoundingClientRect(), sw = parseFloat(getComputedStyle(svg).strokeWidth);
  const ms = m.querySelector('svg');
  return { shown, painted: !!hit && b.contains(hit), last: kids[kids.length - 1] === b, afterMag: kids[kids.indexOf(b) - 1] === m,
           right: r.left >= mr.right - 0.5, size: Math.round(sr.width * 10) / 10, line: Math.round(sw * sr.width / 24 * 100) / 100,
           ink: getComputedStyle(svg).color, magInk: getComputedStyle(ms).color, bg: getComputedStyle(b).backgroundColor,
           label: b.getAttribute('aria-label'), pressed: b.getAttribute('aria-pressed'), title: b.title || b.getAttribute('data-tip') || '' }; }"""
# Each glyph's ink, left and right, to ask the gaps between them.
INK = """(sels) => sels.map((sel) => { const svg = document.querySelector(sel); if (!svg) return null;
  const r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, k = r.width / vb.width;
  const half = (parseFloat(getComputedStyle(svg).strokeWidth) || 0) * k / 2; let L = 1e9, R = -1e9;
  svg.querySelectorAll('path,rect,circle,line,polyline').forEach((el) => { const bb = el.getBBox();
    const h = el.getAttribute('stroke') === 'none' ? 0 : half;
    L = Math.min(L, r.left + (bb.x - vb.x) * k - h); R = Math.max(R, r.left + (bb.x + bb.width - vb.x) * k + h); });
  return { L, R }; })"""
FS = "() => document.fullscreenElement === document.documentElement ? 'page' : (document.fullscreenElement ? (document.fullscreenElement.id || document.fullscreenElement.className || 'other') : null)"
# The header and the dock on screen: their boxes, and what is painted there.
CHROME = """(dock) => [document.querySelector('.header'), document.querySelector(dock)].map((e) => { const r = e.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return r.height > 0 && !!hit && e.contains(hit); })"""
# The on tile a pressed Magnify wears, to compare.
MAG_ON = """() => { const m = document.getElementById('magnifyBtn'); m.classList.add('active');
  const bg = getComputedStyle(m).backgroundColor; m.classList.remove('active'); return bg; }"""
SHOWN = "(id) => { const r = document.getElementById(id).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }"
# The media drawer's top, as far under the dock as it opens.
DRAWER = """(dock) => { const d = document.querySelector(dock).getBoundingClientRect();
  const card = document.getElementById('mediaCard') || document.querySelector('.media-card');
  if (!card) return null; const r = card.getBoundingClientRect(); return r.height > 0 ? Math.round(r.top - d.bottom) : null; }"""
# The browser saying no, as a frame that does not allow full screen answers:
# requestFullscreen is there, and fullscreenEnabled (both spellings) is false.
NO_FS = """for (const k of ['fullscreenEnabled', 'webkitFullscreenEnabled'])
  Object.defineProperty(Document.prototype, k, { configurable: true, get() { return false; } });"""


def press(pg):
    # A button that is not on screen is a red row below, not a click that
    # waits out its timeout.
    if pg.is_visible("#drawFullBtn"):
        pg.click("#drawFullBtn")
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()

    for name in eds("button"):
        print(f"\nTHE BUTTON -- {name}, a 1920 desk window")
        for theme in ("light", "dark"):
            c, pg, errs = editor(b, name, theme=theme)
            m = pg.evaluate(BTN, DOCK[name])
            check(f"{name} ({theme}): the dock ends with Draw in full screen, after Magnify, painted where it is",
                  bool(m) and m["shown"] and m["painted"] and m["last"] and m["afterMag"] and m["right"], str(m))
            check(f"{name} ({theme}): ...drawn at Magnify's 26px, at the same 1.8px line",
                  bool(m) and abs(m["size"] - 26) <= 0.5 and abs(m["line"] - 1.8) <= 0.05, str(m and [m["size"], m["line"]]))
            check(f"{name} ({theme}): ...in Magnify's ink",
                  bool(m) and m["ink"] == m["magInk"], str(m and [m["ink"], m["magInk"]]))
            if theme == "light":
                ink = pg.evaluate(INK, ["#mediaOpenBtn .media-glyph", "#magnifyBtn svg", "#drawFullBtn svg"])
                gaps = None if None in ink else [round(ink[1]["L"] - ink[0]["R"], 1), round(ink[2]["L"] - ink[1]["R"], 1)]
                check(f"{name}: ...as far from Magnify as Magnify is from Media: one rhythm at the right end",
                      bool(gaps) and abs(gaps[0] - gaps[1]) <= 0.5, f"Media to Magnify {gaps and gaps[0]}, Magnify to it {gaps and gaps[1]}")
                check(f"{name}: ...named for what it does, and not pressed",
                      bool(m) and m["label"] == "Draw in full screen" and m["pressed"] == "false" and m["title"] == "Draw in full screen",
                      str(m and [m["label"], m["pressed"], m["title"]]))
            check(f"{name} ({theme}): nothing went wrong on the page", not errs, "; ".join(errs)[:200])
            c.close()

    for name in eds("inout"):
        print(f"\nIN AND OUT -- {name}")
        c, pg, errs = editor(b, name)
        tile = pg.evaluate(MAG_ON)
        out_gap = None
        pg.click("#mediaOpenBtn")
        pg.wait_for_timeout(500)
        out_gap = pg.evaluate(DRAWER, DOCK[name])
        pg.click("#mediaOpenBtn")
        pg.wait_for_timeout(400)
        press(pg)
        on = pg.evaluate(FS)
        ch = pg.evaluate(CHROME, DOCK[name])
        m = pg.evaluate(BTN, DOCK[name])
        check(f"{name}: pressed, the page itself goes full screen, the header and the dock still on it",
              on == "page" and all(ch), f"full screen: {on}; header, dock painted: {ch}")
        check(f"{name}: ...and the button says how out: Leave full screen (Esc), pressed, on the dock's on tile",
              bool(m) and m["label"] == "Leave full screen" and m["pressed"] == "true" and "Esc" in m["title"] and m["bg"] == tile,
              str(m and [m["label"], m["pressed"], m["title"], m["bg"], tile]))
        # A real full screen makes the window the screen's size; headless
        # Chrome keeps the window, so this makes it so.
        pg.set_viewport_size({"width": 1920, "height": 1080})
        pg.wait_for_timeout(900)
        got = pg.evaluate(SHOWN, CANVAS[name])
        want = FULL[(name, 1920)]
        check(f"{name}: ...and on a 1920x1080 screen the canvas takes the room, at the mock's {want[0]}x{want[1]}",
              abs(got[0] - want[0]) <= 2 and abs(got[1] - want[1]) <= 2, f"shown {got[0]}x{got[1]}")
        pg.click("#mediaOpenBtn")
        pg.wait_for_timeout(500)
        in_gap = pg.evaluate(DRAWER, DOCK[name])
        pg.click("#mediaOpenBtn")
        pg.wait_for_timeout(400)
        check(f"{name}: ...a drawer opens where it opens out of full screen, under the dock",
              in_gap is not None and out_gap is not None and in_gap >= 0 and abs(in_gap - out_gap) <= 1,
              f"{in_gap}px under the dock in full screen, {out_gap}px out of it")
        pg.set_viewport_size({"width": 1920, "height": 945})
        press(pg)
        off = pg.evaluate(FS)
        m = pg.evaluate(BTN, DOCK[name])
        check(f"{name}: pressed again, the page comes back out, and the button says so",
              off is None and bool(m) and m["label"] == "Draw in full screen" and m["pressed"] == "false",
              f"full screen: {off}; {m and [m['label'], m['pressed']]}")
        check(f"{name}: nothing went wrong in and out of full screen", not errs, "; ".join(errs)[:200])
        c.close()

    for name in eds("watch"):
        print(f"\nTHE WATCH STILL WORKS -- {name}")
        c, pg, errs = editor(b, name)
        press(pg)
        pg.click(PLAY[name])
        pg.wait_for_timeout(500)
        pg.click(WATCH_BTN[name])
        pg.wait_for_timeout(700)
        watching = pg.evaluate(FS)
        pg.click(".watch-exit")
        pg.wait_for_timeout(700)
        back = pg.evaluate(FS)
        m = pg.evaluate(BTN, DOCK[name])
        check(f"{name}: watching the drawing big from here and leaving it comes back to the page in full screen, still pressed",
              watching not in (None, "page") and back == "page" and bool(m) and m["pressed"] == "true",
              f"watching: {watching}; after: {back}; pressed {m and m['pressed']}")
        # Leaving with nothing focused (Escape's way: the browser leaves and
        # focus is on the page), the watch's button is not handed focus.
        pg.evaluate("() => { document.activeElement && document.activeElement.blur(); "
                    "return document.fullscreenElement ? document.exitFullscreen() : null; }")
        pg.wait_for_timeout(600)
        foc = pg.evaluate("(sel) => { const a = document.activeElement; return { full: !!a && a.classList.contains('full-btn'), "
                          "tag: a ? a.tagName + (a.id ? '#' + a.id : '') + (a.className ? '.' + a.className : '') : null, "
                          "watch: document.querySelector(sel).getAttribute('aria-pressed') }; }", WATCH_BTN[name])
        check(f"{name}: ...and the page leaving full screen is not the watch's news: its button is not handed focus",
              not foc["full"] and foc["watch"] == "false", str(foc))
        check(f"{name}: nothing went wrong with the watch", not errs, "; ".join(errs)[:200])
        c.close()

    for name in eds("not"):
        print(f"\nWHERE IT FITS -- {name}")
        c, pg, errs = editor(b, name, w=721, h=900)
        m = pg.evaluate(BTN, DOCK[name])
        over = pg.evaluate("(dock) => { const d = document.querySelector(dock); return d.scrollWidth - d.clientWidth; }", DOCK[name])
        check(f"{name}: in a 721px window, the narrowest it shows in, the dock holds it, painted, without clipping",
              bool(m) and m["shown"] and m["painted"] and m["last"] and over <= 0, f"{m and [m['shown'], m['painted']]}; the dock {over}px past its edge")
        c.close()
        print(f"\nWHERE IT IS NOT -- {name}")
        for label, kw in (("a phone (402x874, touch)", dict(w=402, h=874, is_mobile=True, has_touch=True, device_scale_factor=3)),
                          ("a touch screen at a desk's width (1024x768)", dict(w=1024, h=768, has_touch=True, is_mobile=True)),
                          ("a window 720px wide, with a mouse", dict(w=720, h=900))):
            c, pg, errs = editor(b, name, **kw)
            m = pg.evaluate(BTN, DOCK[name])
            check(f"{name}: not on {label}", bool(m) and not m["shown"], str(m and [m["shown"], m["label"]]))
            c.close()
        c, pg, errs = editor(b, name, init=NO_FS)
        m = pg.evaluate(BTN, DOCK[name])
        api = pg.evaluate("() => [document.fullscreenEnabled, document.webkitFullscreenEnabled, typeof document.documentElement.requestFullscreen]")
        check(f"{name}: not where the browser says the page can't go full screen, though requestFullscreen is there",
              bool(m) and not m["shown"] and api == [False, False, "function"],
              f"{m and [m['shown'], m['label']]}; fullscreenEnabled, webkit's, requestFullscreen: {api}")
        c.close()

    b.close()

summarise_and_exit()
