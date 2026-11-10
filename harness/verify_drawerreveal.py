#!/usr/bin/env python3
"""Every drawer shows what a tap opens, all of it (lib/drawerdetent.js).

The owner: "is there any reason that all drawers shouldn't open all the way
(scroll to bottom) when a selection is made that shows below the screen?" A
sweep pressed every tile and door in every drawer, 44 of them, on the Pad and
on Flip, on a phone and a desk. On a desk the page did not move at all for the
pen drawer's four tiles or Text's three, and their choices ended 21-241px
below the foot of a 1280x800 screen. The owner's pick, one rule for every
drawer: the page glides just far enough to show all of what opened, without
going past the top of the drawer; with Reduce Motion it goes straight there.

Each tile and door -- the pen drawer's Brush, Size, Feel and Eraser, Text's
Size, Thickness and Speed, the music drawer's Length, Beat, Restart and Exact
times with a song in -- is pressed for real (a tap on the phone, a click on the
desk), from the drawer just opened, and the page is read on every frame until
it is still. Then:

  WHAT OPENED SHOWS: its end is on the screen, and inside any box that clips
  it (a drawer fitted under the header scrolls inside itself) -- or, for a
  pen or Text tile, the page stopped at the top of the drawer, the bar right
  above it reaching the header, or at Text's words, which stay in view while
  their sliders change them. A music drawer's door shows ALL of what it
  opens (the owner's pick for the Restart door, after #814: with the song
  and its timeline above the doors it is taller than the room the drawer's
  top leaves, and stopping there left up to 264px of it below a phone's
  screen), or stops only with its tile at the header -- or under the
  timeline's copy, which shows there once the timeline has gone up past it.
  JUST FAR ENOUGH: when the page moved, what opened (or, on a phone, the
  pen or Text drawer it is in) ends near the foot of the screen, not far
  above it.
  WHAT WAS TAPPED STAYS ON SCREEN, below the header (and the copy).
  IT GLIDES: the page moves over three frames or more, never more in one
  frame's time than 60% of the way (24px at the least: the browser's own
  glide of 33px moves 16px in its fastest frame), and never back up. Not
  half: the browser glides the page on its own thread, and a frame read on
  the page's can carry two of its steps -- the music drawer's Length door,
  10 frames peaking at 41px alone, read once as 41 and 25 together, 66px of
  118 in an 18ms frame.

And once each for the pen drawer, Text and the music drawer, on a desk:

  REDUCE MOTION GOES STRAIGHT THERE: with prefers-reduced-motion one frame
  carries the move.

And for one tile pressed after another, the pen drawer's Feel and then:

  ERASER, SHORTER: the drawer gets shorter at once, and the page, at its end,
  glides up with it rather than leaping (a swap is held, as a close is:
  SkriblDrawerDetent.shrinkGently), and Eraser's choices show.
  BRUSH, ON A DESK, ALREADY IN VIEW: the page stays where it is.

And on a short desk, 1280x560, where the holds bind:

  THE PEN'S FEEL stops with the bar above the drawer at the top of the
  screen, not past it, the choices going on below.
  TEXT, WITH WORDS TYPED, Thickness: the slider shows, or the page stopped
  with the words at the top -- words in view stay in view (the Pad). Words
  Text's own reveal has already let go above the screen hold nothing, and
  the slider shows (Flip).

And on a short phone, 402x664, where Restart cannot all show: the page goes
as far as it can, the tile stopping below the header and the timeline's
copy.

And on a slower phone (CPU 4x), the pen's Feel three times on each editor:

  IT STILL GLIDES THERE, AND NEVER BACK UP. The reveal's re-asserts wait for
  the page to be still (lib/drawerdetent.js whenStill): written while the
  browser was still gliding, the page went on past where it was going, and
  the next re-assert snapped it back up.

And on a slower, short phone (CPU 6x, 402x664), a song added to the Pad's
music drawer, eight times:

  THE PAGE FOLLOWS IT DOWN AND NEVER BACK UP. The follow's re-asserts
  (followGrowth) wait for the page to be still as well.

And NO DRAWER IS MISSED: every tile in the editor's page (.dp-tile) is one this
suite pressed, so a new drawer's tiles fail here until they are listed.

For calibration, DRAWERREVEAL_ONLY="Pad desk" (an editor, a device, a drawer,
any of them; "slow" for the slower phone alone) runs that part alone. A real
run sets nothing.

Checked red per component: see DECISIONS.md for which mutation turned which
row red.
"""
import io
import math
import os
import struct
import sys
import wave

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)
ONLY = os.environ.get("DRAWERREVEAL_ONLY", "").split()


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)
import browsing  # noqa: E402
import waits  # noqa: E402

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=1, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
DEVICES = {"phone": PHONE, "desk": DESK}
SHORT = dict(viewport={"width": 1280, "height": 560}, device_scale_factor=1)   # a short desk, where the holds bind
SHORTPHONE = dict(viewport={"width": 402, "height": 664}, device_scale_factor=1, is_mobile=True, has_touch=True)
EDITORS = {"Pad": {"route": "/skribl-pad", "ctl": "_padDrawerCtl", "dock": "#toolBar"},
           "Flip": {"route": "/flip", "ctl": "_flipDrawerCtl", "dock": ".flip-tools"}}
# Each drawer: its row of tiles, the drawer they are in, and the tiles.
DRAWERS = {
    "pen": {"row": "#drawTiles", "drawer": "#drawPanel", "tiles": ["brush", "size", "feel", "eraser"]},
    "Text": {"row": "#txTiles", "drawer": "#txSheet", "tiles": ["size", "weight", "speed"]},
    "music": {"row": "#musicDoors", "drawer": "#musicPanel", "tiles": ["length", "beat", "restart", "exact"]},
}


def wanted(*names):
    """Whether DRAWERREVEAL_ONLY lets this editor, device and drawer run."""
    return all(o in names for o in ONLY)


def _song(seconds=6.0, rate=8000, f0=220.0):
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * (f0 + 30 * i / rate) * i / rate)))
                           for i in range(int(seconds * rate))))
    w.close()
    return {"name": "short.wav", "mimeType": "audio/wav", "buffer": buf.getvalue()}


SONG = _song()

# The page's place on every frame from before the press, for 1.9s.
LOG = """() => { window.__rv = []; const t0 = performance.now(), sc = document.scrollingElement || document.documentElement;
  const f = () => { __rv.push([performance.now(), sc.scrollTop]); if (performance.now() - t0 < 1900) requestAnimationFrame(f); };
  f(); }"""

# Where everything is once the page is still. What opened is the tile's own
# panel (aria-controls). What can be seen of it ends at the foot of the
# screen, or sooner at a box that clips it.
GEOM = """([tile, dock, drawer]) => {
  const t = document.querySelector(tile), el = document.getElementById(t.getAttribute('aria-controls'));
  const vh = window.visualViewport ? visualViewport.height : innerHeight;
  const D = window.SkriblDrawerDetent, stuck = D && D.stuckBottom ? D.stuckBottom() : 0;
  const d = document.querySelector(dock), dk = d && d.offsetParent !== null ? d.getBoundingClientRect() : null;
  let foot = vh;
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    if (getComputedStyle(p).overflowY !== 'visible') foot = Math.min(foot, p.getBoundingClientRect().bottom); }
  const r = el.getBoundingClientRect(), tr = t.getBoundingClientRect(), pr = document.querySelector(drawer).getBoundingClientRect();
  const w = document.getElementById('txPlace'), wr = w && !w.hidden && w.getClientRects().length ? w.getBoundingClientRect() : null;
  const wc = wr && w.firstElementChild ? w.firstElementChild.getBoundingClientRect().top : null;
  const sc = document.scrollingElement || document.documentElement;
  return { open: !el.hidden && t.getAttribute('aria-expanded') === 'true', top: r.top, bottom: r.bottom, foot, vh, stuck,
           dockTop: dk ? dk.top : null, tileTop: tr.top, tileBottom: tr.bottom, drawerBottom: pr.bottom,
           wordsTop: wr ? Math.min(wr.top, wc == null ? wr.top : wc) : null,
           copyFoot: (() => { const f = document.getElementById('musicFollow'); return f && f.classList.contains('on') ? f.getBoundingClientRect().bottom : null; })(),
           y: sc.scrollTop, max: sc.scrollHeight - innerHeight }; }"""


def boot(b, ed, dev, drawer, reduce=False):
    c = b.new_context(color_scheme="light", reduced_motion="reduce" if reduce else "no-preference",
                      **({"short": SHORT, "shortphone": SHORTPHONE}.get(dev) or DEVICES[dev]))
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, EDITORS[ed]["route"] + "?theme=light")
    waits.settle(q, 500)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide && SkriblHints.hide()")
    if drawer == "music":
        open_drawer(q, ed, drawer)
        q.set_input_files("#musicInput", SONG)
        q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=20000)
        waits.settle(q, 2500)
        close_drawer(q, ed)
    return c, q, errs


def open_drawer(q, ed, drawer):
    if drawer == "Text":
        q.evaluate("() => document.querySelector('#shapeSeg [data-shape=\"text\"]').click()")
    else:
        q.evaluate(f"(n) => {EDITORS[ed]['ctl']}.open(n)", "draw" if drawer == "pen" else drawer)
    waits.settle(q, 900)
    browsing.wait_scroll_still(q, 2500)


def close_drawer(q, ed):
    q.evaluate(f"() => {EDITORS[ed]['ctl']}.open(null)")
    waits.settle(q, 600)
    browsing.wait_scroll_still(q, 2500)


def press(q, dev, sel):
    """Press the tile for real and read the page on every frame until still."""
    q.evaluate(LOG)
    loc = q.locator(sel)
    if dev == "phone":
        loc.tap()
    else:
        loc.click()
    q.wait_for_timeout(1950)
    browsing.wait_scroll_still(q, 2500)
    return q.evaluate("() => window.__rv")


def motion(log):
    """The page's moves: each frame's step read for a frame's time (a dropped
    frame's two frames of travel is not a leap, as verify_sheetswipe reads its
    glides), the whole move, how many frames it took, and the furthest back."""
    steps = [((b[1] - a[1]) * 16.7 / max(16.7, min(b[0] - a[0], 50)), b[1] - a[1], b[0] - a[0])
             for a, b in zip(log, log[1:])]
    moving = [s for s in steps if abs(s[1]) > 0.5]
    total = (log[-1][1] - log[0][1]) if log else 0
    big = max(moving, key=lambda s: abs(s[0])) if moving else (0, 0, 0)
    back = min([s[1] for s in steps] + [0])
    return {"total": total, "frames": len(moving), "big": big, "back": back}


def glided(m):
    """Over three frames or more, and no frame's step (for a frame's time)
    more than 60% of the whole move, or 24px."""
    return m["frames"] >= 3 and abs(m["big"][0]) <= max(24, 0.6 * abs(m["total"]))


def judge(who, dev, drawer, g, m):
    """The rows for one press."""
    shows = g["bottom"] <= min(g["vh"], g["foot"]) + 1
    lid = max(g["stuck"], g["copyFoot"] or 0)
    if drawer == "music":
        # A door: all of it, or the tile tapped at the header (or the copy).
        at_lid = g["tileTop"] <= lid + 8 + 3
        at_words = False
        said = "or stopped with the tile at the header"
    else:
        at_lid = g["dockTop"] is not None and g["dockTop"] <= g["stuck"] + 6
        at_words = g["wordsTop"] is not None and g["wordsTop"] <= g["stuck"] + 10
        said = "or the page stopped at the drawer's top"
    check(f"{who}: what opened shows, all of it, {said}",
          g["open"] and (shows or at_lid or at_words),
          f"opened {round(g['top'])}..{round(g['bottom'])} of a screen to {round(g['vh'])} (seen to {round(g['foot'])}); "
          f"bar above the drawer at {None if g['dockTop'] is None else round(g['dockTop'])}, header to {round(g['stuck'])}"
          f"{'' if g['copyFoot'] is None else ', the timeline copy to ' + str(round(g['copyFoot']))}; tile at {round(g['tileTop'])}; "
          f"page {round(g['y'])} of {round(g['max'])}")
    if m["total"] > 1:
        ends = [g["bottom"]] + ([g["drawerBottom"]] if dev == "phone" and drawer != "music" else [])
        snug = any(g["vh"] - 44 <= e <= g["vh"] + 1 for e in ends) or at_lid or at_words or g["y"] >= g["max"] - 1
        check(f"{who}: ...just far enough", snug,
              f"moved {round(m['total'])}px; opened ends at {round(g['bottom'])}, the drawer at {round(g['drawerBottom'])}, of {round(g['vh'])}")
    check(f"{who}: ...and what was tapped stays on screen" + (", below the timeline's copy" if drawer == "music" else ""),
          g["tileTop"] >= lid - 1 and g["tileBottom"] <= g["vh"] + 1,
          f"tile {round(g['tileTop'])}..{round(g['tileBottom'])}, header to {round(g['stuck'])}"
          f"{'' if g['copyFoot'] is None else ', copy to ' + str(round(g['copyFoot']))}, screen to {round(g['vh'])}")
    if m["total"] > 12:
        big = m["big"]
        check(f"{who}: ...gliding there, never back up",
              glided(m) and m["back"] >= -2,
              f"{round(m['total'])}px over {m['frames']} frames, the most {round(big[1])}px in a {round(big[2])}ms frame "
              f"({round(big[0])}px a frame's time); the most back {round(m['back'])}px")


pressed = {}
with sync_playwright() as p:
    b = waits.instrument(p.chromium.launch())
    for ed in EDITORS:
        for dev in DEVICES:
            for drawer, spec in DRAWERS.items():
                if not wanted(ed, dev, drawer):
                    continue
                c = q = errs = None
                for k in spec["tiles"]:
                    sel = f'{spec["row"]} .dp-tile[data-dp="{k}"]'
                    who = f"{ed} {dev} {drawer}: {k}"
                    # Text closes as a whole, so each of its tiles starts on a
                    # fresh page; the pen and music drawers close and open again.
                    if q is None or drawer == "Text":
                        if c:
                            c.close()
                        c, q, errs = boot(b, ed, dev, drawer)
                    open_drawer(q, ed, drawer)
                    g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], spec["drawer"]])
                    log = press(q, dev, sel)
                    g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], spec["drawer"]])
                    pressed.setdefault(ed, set()).add(f'{spec["row"][1:]}:{k}')
                    judge(who, dev, drawer, g, motion(log))
                    if drawer != "Text":
                        close_drawer(q, ed)
                check(f"{ed} {dev} {drawer}: no page errors", not errs, "; ".join((errs or [])[:2]))
                c.close()

    # A SHORT DESK, 1280x560, where the holds bind. The pen's Feel: the page
    # stops with the bar above the drawer at the top of the screen, the
    # choices going on below it. Text with words typed: on the Pad the words
    # hold the page (they stay in view while the slider changes them); on
    # Flip its own reveal has already let the words go above the screen, so
    # they hold nothing and the slider shows.
    for ed in EDITORS:
        if wanted(ed, "desk", "pen"):
            c, q, errs = boot(b, ed, "short", "pen")
            open_drawer(q, ed, "pen")
            sel = '#drawTiles .dp-tile[data-dp="feel"]'
            m = motion(press(q, "desk", sel))
            g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], "#drawPanel"])
            check(f"{ed} short desk pen: Feel stops with the bar above the drawer at the top, not past it",
                  m["total"] > 12 and g["dockTop"] is not None and 0 <= g["dockTop"] - g["stuck"] <= 6
                  and g["tileTop"] >= g["stuck"] - 1,
                  f"moved {round(m['total'])}px; bar at {g['dockTop'] and round(g['dockTop'])}, tile at {round(g['tileTop'])}, "
                  f"choices to {round(g['bottom'])} of {round(g['vh'])}")
            c.close()
        if wanted(ed, "desk", "Text"):
            c, q, errs = boot(b, ed, "short", "Text")
            open_drawer(q, ed, "Text")
            q.fill("#txField", "Hello there")
            waits.settle(q, 600)
            q.evaluate("() => document.activeElement && document.activeElement.blur()")
            browsing.wait_scroll_still(q, 2500)
            sel = '#txTiles .dp-tile[data-dp="weight"]'
            g0 = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], "#txSheet"])
            m = motion(press(q, "desk", sel))
            g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], "#txSheet"])
            shows = g["bottom"] <= min(g["vh"], g["foot"]) + 1
            seen = g0["wordsTop"] is not None and g0["wordsTop"] >= g0["stuck"] - 1
            check(f"{ed} short desk Text, words typed: Thickness shows, or the page stopped with the words at the top",
                  g["open"] and (shows or (g["wordsTop"] is not None and g["stuck"] - 1 <= g["wordsTop"] <= g["stuck"] + 10)),
                  f"moved {round(m['total'])}px; slider to {round(g['bottom'])} of {round(g['vh'])}; words at "
                  f"{g0['wordsTop'] and round(g0['wordsTop'])} then {g['wordsTop'] and round(g['wordsTop'])}")
            check(f"{ed} short desk Text, words typed: ...words that were in view stay in view",
                  g["wordsTop"] is not None and (not seen or g["wordsTop"] >= g["stuck"] - 1),
                  f"words at {g0['wordsTop'] and round(g0['wordsTop'])} then {g['wordsTop'] and round(g['wordsTop'])}")
            c.close()

    # A SHORT PHONE, 402x664, where Restart cannot all show: the page goes as
    # far as it can and the tile stops below the header -- and below the
    # timeline's copy, which shows there once the timeline has gone up past
    # it and covers what passes under it.
    for ed in EDITORS:
        if not wanted(ed, "phone", "music"):
            continue
        c, q, errs = boot(b, ed, "shortphone", "music")
        open_drawer(q, ed, "music")
        sel = '#musicDoors .dp-tile[data-dp="restart"]'
        m = motion(press(q, "phone", sel))
        g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], "#musicPanel"])
        lid = max(g["stuck"], g["copyFoot"] or 0)
        check(f"{ed} short phone music: Restart goes as far as it can, its tile below the header and the timeline's copy",
              m["total"] > 12 and g["open"] and g["copyFoot"] is not None and lid - 1 <= g["tileTop"] <= lid + 12
              and g["bottom"] > g["vh"],
              f"moved {round(m['total'])}px; tile at {round(g['tileTop'])}, header to {round(g['stuck'])}, the copy "
              f"{'off' if g['copyFoot'] is None else 'to ' + str(round(g['copyFoot']))}; Restart to {round(g['bottom'])} of {round(g['vh'])}")
        c.close()

    # REDUCE MOTION: once per drawer, on a desk.
    for ed in EDITORS:
        for drawer, k in (("pen", "feel"), ("Text", "weight"), ("music", "restart")):
            if not wanted(ed, "desk", drawer):
                continue
            spec = DRAWERS[drawer]
            sel = f'{spec["row"]} .dp-tile[data-dp="{k}"]'
            c, q, errs = boot(b, ed, "desk", drawer, reduce=True)
            open_drawer(q, ed, drawer)
            m = motion(press(q, "desk", sel))
            big = m["big"]
            check(f"{ed} desk {drawer}: under Reduce Motion, {k} goes straight there",
                  m["total"] > 12 and abs(big[1]) >= 0.9 * m["total"] and m["back"] >= -2,
                  f"{round(m['total'])}px over {m['frames']} frames, the most {round(big[1])}px in one")
            c.close()

    # ONE TILE FOR ANOTHER, and a choice that already shows: Feel open (the
    # page brought to its choices), then Eraser, which is shorter, and on a
    # desk Brush, which is already in view.
    for ed in EDITORS:
        for dev in DEVICES:
            if not wanted(ed, dev, "pen"):
                continue
            for then in ("eraser", "brush") if dev == "desk" else ("eraser",):
                c, q, errs = boot(b, ed, dev, "pen")
                open_drawer(q, ed, "pen")
                press(q, dev, '#drawTiles .dp-tile[data-dp="feel"]')
                sel = f'#drawTiles .dp-tile[data-dp="{then}"]'
                m = motion(press(q, dev, sel))
                g = q.evaluate(GEOM, [sel, EDITORS[ed]["dock"], "#drawPanel"])
                big = m["big"]
                if then == "eraser":
                    check(f"{ed} {dev} pen: Feel for Eraser, the page glides up as the drawer gets shorter, never leaps",
                          m["total"] < -40 and glided(m),
                          f"{round(m['total'])}px over {m['frames']} frames, the most {round(big[1])}px in a {round(big[2])}ms frame "
                          f"({round(big[0])}px a frame's time)")
                    check(f"{ed} {dev} pen: ...and Eraser's choices show", g["open"] and g["bottom"] <= min(g["vh"], g["foot"]) + 1,
                          f"opened {round(g['top'])}..{round(g['bottom'])} of {round(g['vh'])}")
                else:
                    check(f"{ed} {dev} pen: Feel for Brush, already in view, the page stays where it is",
                          g["open"] and g["bottom"] <= g["vh"] - 12 and abs(m["total"]) <= 1,
                          f"moved {round(m['total'])}px; Brush's choices end at {round(g['bottom'])} of {round(g['vh'])}")
                c.close()

    # A SLOWER PHONE, CPU 4x. The reveal's re-asserts (lib/drawerdetent.js
    # revealPanelEnd, at 300, 700 and 1200ms) caught the browser still gliding
    # the page there, and a write then lands on top of the glide: Flip's Feel
    # went on past 726 to 754 and the next re-assert snapped it 28px back up
    # (main's run after #818 caught 3px of it, at full speed on a busy
    # runner). They wait for the page to be still now. The pen's Feel, three
    # times on each editor, the page read on every frame.
    for ed in EDITORS:
        if not wanted(ed, "phone", "pen", "slow"):
            continue
        c, q, errs = boot(b, ed, "phone", "pen")
        cdp = c.new_cdp_session(q)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        sel = '#drawTiles .dp-tile[data-dp="feel"]'
        seen = []
        for _ in range(3):
            open_drawer(q, ed, "pen")
            seen.append(motion(press(q, "phone", sel)))
            close_drawer(q, ed)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        check(f"{ed} slower phone (CPU 4x) pen: Feel glides there and never back up, three times",
              all(m["total"] > 12 and glided(m) and m["back"] >= -2 for m in seen),
              "; ".join(f"{round(m['total'])}px over {m['frames']} frames, the most {round(m['big'][1])}px "
                        f"in a {round(m['big'][2])}ms frame, the most back {round(m['back'])}px" for m in seen))
        c.close()

    # A SONG ADDED ON A SLOWER, SHORT PHONE (CPU 6x, 402x664). The page
    # follows the music drawer as a song lands in it (lib/drawerdetent.js
    # followGrowth), and its re-asserts, at 300, 700 and 1200ms, caught that
    # glide still going too: the 300ms one wrote at 383 on the way to 406, the
    # page went on to 423, and the 700ms one took it 17px back up under the
    # header (3 of 6 adds at 6x). They wait for the page to be still now.
    # Added as a person adds one, a tap on Add music and then the file, eight
    # times, each on a fresh page; only the step back is asked, since a frame
    # the busy page never drew (it is decoding the song) is not a leap the
    # person sees. Flip's song lands in two steps, and its add never went back
    # in twelve tries before the fix or after, so the Pad's row pins the code
    # both editors share.
    if wanted("Pad", "phone", "music", "slow"):
        seen = []
        for _ in range(8):
            c, q, errs = boot(b, "Pad", "shortphone", "pen")
            cdp = c.new_cdp_session(q)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 6})
            open_drawer(q, "Pad", "music")
            q.evaluate(LOG.replace("1900", "3200"))
            with q.expect_file_chooser() as fc:
                q.locator("#musicAddBtn").tap()
            fc.value.set_files(SONG)
            q.wait_for_timeout(3300)
            browsing.wait_scroll_still(q, 3000)
            seen.append(motion(q.evaluate("() => window.__rv")))
            c.close()
        check("Pad slower short phone (CPU 6x) music: a song added glides to the drawer's end and never back up, eight times",
              all(m["total"] > 12 and m["back"] >= -2 for m in seen),
              "; ".join(f"{round(m['total'])}px, the most back {round(m['back'])}px" for m in seen))

    # NO DRAWER IS MISSED: every tile in the page is one pressed above.
    if not ONLY:
        for ed in EDITORS:
            c, q, errs = boot(b, ed, "desk", None)
            every = set(q.evaluate("""() => [...document.querySelectorAll('.dp-tile')].map(t => {
                const row = t.parentElement.closest('.dp[id]'); return (row ? row.id : '?') + ':' + t.dataset.dp; })"""))
            check(f"{ed}: every tile in the page is one this suite presses", every and every <= pressed.get(ed, set()),
                  f"not pressed: {sorted(every - pressed.get(ed, set()))}; pressed {len(pressed.get(ed, set()))}")
            c.close()
    b.close()

summarise_and_exit()
