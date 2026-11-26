#!/usr/bin/env python3
"""Drawers beside the drawing, on a desk (lib/drawers.js sideApply; the owner's
"all yes", Nov 25, to the Drawers Beside the Drawing mock).

The owner: "What's next? When is desktop change?" On a desk a drawer opened
below the drawing and the page glided down to show it: with Pen open the Pad
showed 60-73% of its drawing on four desks and Flip 42-65%; with a song and
Restart's door open, none of it. The owner's three answers: on a desk every
drawer (Pen, Photo, Music, Text) opens beside the drawing; the drawing and
what sits under it slide left together, only as far as the drawer needs, the
header staying; where the two don't fit (a narrow window, a tablet) the
drawer opens below as before, and phones don't change.

On the Pad (How it works' cat) and Flip (its bouncing ball):

  BESIDE: each drawer opened is a column at the drawing's right, 392px,
  ending 16px in from where a drawer held to the screen can end (the page
  keeps a scrollbar's gutter at each edge), its top level with the
  drawing's; the drawing whole on the screen at its own size, 16px clear of
  the drawer at least; the page not scrolled.
  ONLY AS FAR AS NEEDED: the drawing slides left until it ends 16px from the
  drawer, and no further (none where there is room: Flip from 1536px up);
  the header stays; what sits under the drawing (the Pad's dock; Flip's page
  strip and dock) slides with it, by as much; the pen's drawer closed, all
  of it is back where it was.
  IT GLIDES, AND GLIDES BACK: the drawing's left read on every frame moves
  over three frames or more, never more than 60% of the way in one, and
  never back; closing, the same home again. Under Reduce Motion one frame
  carries it.
  INSIDE THE DRAWER: what a tile opens (the pen's Feel) and Restart's door
  with a song in (taller than the screen) show by the drawer's own column
  gliding inside itself, just far enough for the end of what opened, or
  until the tile tapped is 8px under its top, whichever comes first (on a
  1280x600 desk all of Feel's choices show; on a 1280x500 one Flip's tile
  stays); the page stays.
  THE EYEDROPPER: the drawer stays out while it picks (nothing covers the
  drawing to step aside for).
  THE BRUSH RING: Flip's ring stays on the pointer over the drawing before a
  drawer, with it beside, and home again (the slide's end sends a resize,
  which clears Flip's kept place of the drawing).
  STILL WHERE IT POINTS: a press on the drawing puts a drawer away, as
  below. Flip draws with it and its drawer goes on the click that ends the
  stroke, so the drawing holds still while the pen is down, every point
  landing where it is drawn, and glides home after (a drawer put away on
  the press would glide it under the pen); the Pad's first press draws
  nothing, and the drawing glides home. On both, the drawer gone, a stroke
  lands where it is drawn.

ROOM FOR THE DRAWER (the owner's "All yes", Nov 26, to the Room for the
Drawer mock, after "why is the drawer opening on the bottom?"):

  A WIDE DRAWING MAKES A LITTLE ROOM: a 16:9 drawing, which fills a desk's
  width, on 1366x768, 1440x900 and 1920x1080: the drawer opens beside it
  all the same, the drawing a little smaller (the least it needs, never past
  three quarters of its width), its shape kept, whole on the screen, the
  drawer level with its top and 16px clear of it, the dock under its
  middle; closed, its own size again where it was. It glides there and
  back with the slide, over many frames, never more than a third of the way
  in one. Where it would give up more than a quarter (1024x640) the drawer
  opens below, as before.
  FLIP'S STRIP UNDER THE DRAWER: with any drawer beside, the page strip
  runs from its own left (slid with the drawing) to the drawer's right
  edge, and the drawer ends above it (on a short desk it scrolls inside
  itself); closed, the strip is as it was. Its end glides out and home.

Elsewhere:

  BELOW: an 800x800 desk (neither drawing fits beside a drawer, even a
  quarter smaller; at 900 Flip's ball does, a fifth smaller), a tablet
  (a finger: 1180x820 with touch) and a phone open below as before.
  A RESIZE DECIDES AGAIN: open beside, the window narrowed: below; widened
  again: beside.
  THE TOOLS TRAY stays as it is: never beside, the page never moved.

Every row was shown red by breaking one part and green as built: DECISIONS.md,
"Drawers beside the drawing on a desk: built".
"""
import json
import os
import sys
from pathlib import Path

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = Path(__file__).resolve().parents[1]
results = []
check = make_check(results, detail_on_pass=False)


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

CAT = json.loads((ROOT / "skribl/static/help/demos/cat.json").read_text())
BALL = json.loads((ROOT / "skribl/static/help/demos/flip-bounce.json").read_text())
ED = {
    "Pad": {"route": "/skribl-pad", "cv": "canvas", "ctl": "_padDrawerCtl", "move": ["#toolBar"], "doc": CAT,
            "load": "d => loadSkribl(d)", "ready": "() => typeof loadSkribl === 'function' && typeof _padDrawerCtl !== 'undefined' && !!_padDrawerCtl"},
    "Flip": {"route": "/flip", "cv": "pad", "ctl": "_flipDrawerCtl", "move": [".strip-wrap", ".flip-tools"], "doc": BALL,
             "load": "d => applyFlipDraftObject(d)", "ready": "() => typeof applyFlipDraftObject === 'function' && typeof _flipDrawerCtl !== 'undefined'"},
}
DESKS = ((1440, 900), (1536, 864), (1920, 1080))
SIDE_W, EDGE = 392, 16

# The drawing, the open drawer, the header and what slides, as they are now.
LOOK = """([cv, move]) => {
  const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; };
  const open = [...document.querySelectorAll('#drawPanel, #mediaCard, #txSheet')].find(e => !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 40);
  return { beside: !!(skriblDrawers.beside && skriblDrawers.beside()), canvas: r(document.getElementById(cv)), drawer: r(open), id: open ? open.id : null,
           side: open ? open.classList.contains('drawer-side') : false, scrollY: scrollY, W: document.documentElement.clientWidth, H: innerHeight,
           R: (() => { const p = document.createElement('div'); p.style.cssText = 'position:fixed;top:0;right:0;width:0;height:0';
                       document.body.appendChild(p); const x = p.getBoundingClientRect().left; p.remove(); return x; })(),
           header: r(document.querySelector('.header')), moved: move.map(s => r(document.querySelector(s))) }; }"""


def boot(b, ed, size, *, touch=False, phone=False, reduce=False, load=True, shape=None):
    e = ED[ed]
    kw = {"viewport": {"width": size[0], "height": size[1]}, "device_scale_factor": 1}
    if touch:
        kw.update(has_touch=True)
    if phone:
        kw.update(is_mobile=True, has_touch=True)
    if reduce:
        kw["reduced_motion"] = "reduce"
    c = b.new_context(**kw)
    if shape:
        # A drawing of this shape, as a draft of it would start (lib/chromefit.js noted).
        c.add_init_script("try { localStorage.setItem('skribl.shape.v1.%s', JSON.stringify(%s)); } catch (e) {}"
                          % (ed.lower(), json.dumps(shape)))
    q = c.new_page()
    browsing.goto(q, BASE, e["route"])
    q.wait_for_function(e["ready"], timeout=20000)
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    if load:
        q.evaluate(e["load"], e["doc"])
    q.wait_for_timeout(900)
    return c, q


def look(q, ed):
    return q.evaluate(LOOK, [ED[ed]["cv"], ED[ed]["move"]])


def open_(q, ed, name, wait=900):
    if name == "text":
        q.evaluate("() => document.querySelector('#shapeSeg [data-shape=text]').click()")
        q.wait_for_timeout(200)
        r = q.evaluate("(cv) => { const c = document.getElementById(cv).getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height * 0.3]; }", ED[ed]["cv"])
        q.mouse.click(*r)
    else:
        q.evaluate(f"(n) => {ED[ed]['ctl']}.open(n)", name)
    q.wait_for_timeout(wait)


def close_(q, ed, wait=900):
    q.evaluate(f"() => {ED[ed]['ctl']}.open(null)")
    q.wait_for_timeout(wait)


# The drawing's left, read on every frame for `ms`, from just before `act` runs.
TRACE = """([cv, ms]) => { const c = document.getElementById(cv), out = []; window.__tr = out; const t0 = performance.now();
  (function f() { out.push(c.getBoundingClientRect().left); if (performance.now() - t0 < ms) requestAnimationFrame(f); })(); }"""


def traced(q, ed, act, ms=700):
    q.evaluate(TRACE, [ED[ed]["cv"], ms])
    act()
    q.wait_for_timeout(ms + 150)
    return q.evaluate("() => window.__tr")


def glide(xs):
    """(frames that moved, the biggest step as a share of the way, monotone)."""
    steps = [b - a for a, b in zip(xs, xs[1:]) if abs(b - a) > 0.25]
    total = abs(xs[-1] - xs[0]) if xs else 0
    mono = all(s <= 0.25 for s in steps) or all(s >= -0.25 for s in steps)
    return len(steps), (max(abs(s) for s in steps) / total if steps and total else 0), mono, total


with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ------------------------------------------------------------ beside
    print("\nBESIDE — every drawer at the drawing's right on a desk, the drawing whole, nothing scrolled")
    for ed in ED:
        for size in DESKS:
            c, q = boot(b, ed, size)
            rest = look(q, ed)
            got = {}
            back = None
            for name in ("draw", "photo", "music", "text"):
                open_(q, ed, name)
                got[name] = look(q, ed)
                close_(q, ed)
                if name == "draw":
                    back = look(q, ed)
            c.close()
            cr, W, H, R = rest["canvas"], rest["W"], rest["H"], rest["R"]
            # The drawer ends EDGE in from where a drawer held to the screen
            # can end (R: the page keeps a scrollbar's gutter at each edge).
            want = max(0, SIDE_W + 2 * EDGE - (R - (cr[0] + cr[2])))

            def placed(g):
                cv, d = g["canvas"], g["drawer"]
                return (g["beside"] and g["side"] and d is not None and abs(d[2] - SIDE_W) <= 1
                        and d[0] >= cv[0] + cv[2] + EDGE - 1 and abs(d[0] + d[2] - (R - EDGE)) <= 1 and abs(d[1] - cv[1]) <= 1
                        and d[1] + d[3] <= H + 1 and cv[0] >= 0 and cv[0] + cv[2] <= W and cv[1] >= 0 and cv[1] + cv[3] <= H
                        and abs(cv[2] - cr[2]) <= 1 and abs(cv[3] - cr[3]) <= 1 and g["scrollY"] == 0)
            check(f"{ed} {size[0]}x{size[1]}: Pen, Photo, Music and Text each open beside the drawing, 392px at its right, its top"
                  " level with the drawing's, inside the screen; the drawing whole on the screen at its own size; the page not scrolled",
                  all(placed(g) for g in got.values()),
                  json.dumps({"rest": cr, **{k: [g["beside"], g["canvas"], g["drawer"], g["scrollY"]] for k, g in got.items()}})[:700])
            g = got["draw"]
            slid = cr[0] - g["canvas"][0]
            # Only as far as needed: slid, the drawing ends EDGE from the
            # drawer; not slid, it already ended that far from it or more.
            gap = g["drawer"][0] - (g["canvas"][0] + g["canvas"][2]) if g["drawer"] else None
            far = gap is not None and ((slid > 0.5 and abs(gap - EDGE) <= 1.5) or (abs(slid) <= 0.5 and gap >= EDGE - 1))
            moved_ok = all(m0 and m1 and abs((m0[0] - m1[0]) - slid) <= 1 for m0, m1 in zip(rest["moved"], g["moved"]))
            same = lambda u, v: u is not None and v is not None and all(abs(x - y) <= 0.5 for x, y in zip(u, v))
            ends = f"it ends {EDGE}px from the drawer" if want else f"it has {EDGE}px or more already"
            check(f"{ed} {size[0]}x{size[1]}: the drawing slides left only as far as the drawer needs ({want:.0f}px here: {ends}),"
                  " what sits under it with it by as much; the header stays; closed, everything is back",
                  far and abs(slid - want) <= 1.5 and moved_ok and rest["header"] == g["header"] and back is not None
                  and not back["beside"] and same(back["canvas"], cr) and all(same(u, v) for u, v in zip(back["moved"], rest["moved"])),
                  json.dumps({"slid": slid, "want": want, "gap": gap, "moved": [rest["moved"], g["moved"]], "header": [rest["header"], g["header"]],
                              "back": back and [back["beside"], back["canvas"], back["moved"]]})[:700])

    # ------------------------------------------------------------ the glide
    print("\nIT GLIDES — the drawing's left read on every frame, opening and closing; Reduce Motion goes straight there")
    for ed in ED:
        c, q = boot(b, ed, (1280, 800))
        xs_open = traced(q, ed, lambda: q.evaluate(f"() => {ED[ed]['ctl']}.open('draw')"))
        xs_close = traced(q, ed, lambda: q.evaluate(f"() => {ED[ed]['ctl']}.open(null)"))
        c.close()
        go, back = glide(xs_open), glide(xs_close)
        check(f"{ed}: opening, the drawing glides left over three frames or more, never more than 60% of the way in one, never back;"
              " closing, the same home again",
              go[0] >= 3 and go[1] <= 0.6 and go[2] and go[3] > 50 and back[0] >= 3 and back[1] <= 0.6 and back[2] and abs(back[3] - go[3]) <= 1.5,
              json.dumps({"open": go, "close": back, "xs": [round(x) for x in xs_open[:24]]}))
        c, q = boot(b, ed, (1280, 800), reduce=True)
        xs = traced(q, ed, lambda: q.evaluate(f"() => {ED[ed]['ctl']}.open('draw')"), ms=400)
        c.close()
        st = glide(xs)
        check(f"{ed}: under Reduce Motion one frame carries it", st[0] == 1 and st[3] > 50, json.dumps({"steps": st, "xs": [round(x) for x in xs[:8]]}))

    # ------------------------------------------------------------ inside the drawer
    print("\nINSIDE THE DRAWER — what a tile or a door opens shows by the drawer's own column, never the page")
    # The column glides just far enough for the end of what opened to show,
    # or until the tile tapped is 8px under its top, whichever comes first:
    # on a 1280x600 desk there is room for both; on a 1280x500 one Flip's
    # Feel has not, in any face (at 560 it had in CI's, whose words are
    # narrower: main's run after #1105), and the tile stays, the choices going
    # on below it, as a Music door's do.
    took = []
    for ed in ED:
        for h in (600, 500):
            c, q = boot(b, ed, (1280, h))
            open_(q, ed, "draw")
            q.evaluate("""() => { window.__opened = null; document.getElementById('drawPanel').addEventListener('drawtile',
                (e) => { if (e.detail && e.detail.open) window.__opened = e.detail.el; }); }""")
            q.click("#drawTiles .dp-tile[data-dp='feel']")
            q.wait_for_timeout(1200)
            m = q.evaluate("""() => { const box = document.querySelector('.drawer-side'), p = window.__opened,
                t = document.querySelector("#drawTiles .dp-tile[data-dp='feel']"); if (!box || !p) return null;
                const b = box.getBoundingClientRect(), r = p.getBoundingClientRect(), tr = t.getBoundingClientRect();
                return { scroll: box.scrollTop, end: r.top + p.offsetHeight, boxEnd: b.bottom, tile: tr.top, boxTop: b.top, page: scrollY }; }""")
            c.close()
            shows = m is not None and abs(m["end"] - (m["boxEnd"] - 12)) <= 1.5 and m["tile"] >= m["boxTop"] + 6.5
            stays = m is not None and abs(m["tile"] - (m["boxTop"] + 8)) <= 1.5 and m["end"] > m["boxEnd"] - 12
            took.append((ed, h, "all of it" if shows else "the tile" if stays else None))
            check(f"{ed} 1280x{h}: the pen's Feel, opened beside, shows by its column gliding just far enough for its choices' end,"
                  " or until the tile tapped is 8px under the column's top, whichever comes first; the page where it was",
                  m is not None and m["scroll"] > 0 and (shows or stays) and m["page"] == 0, json.dumps(m))
    check("...both ways seen: all of what opened shown (the tile in view), and the tile kept where the column cannot have both",
          any(t == "all of it" for *_, t in took) and any(t == "the tile" for *_, t in took), json.dumps(took))
    song = browsing.wav_song(30.0) if hasattr(browsing, "wav_song") else None
    if song is None:
        import io, math, struct, wave
        buf = io.BytesIO(); w = wave.open(buf, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * (330 + 30 * i / 8000) * i / 8000))) for i in range(8000 * 30)))
        w.close(); song = {"name": "song.wav", "mimeType": "audio/wav", "buffer": buf.getvalue()}
    c, q = boot(b, "Pad", (1440, 900))
    open_(q, "Pad", "music", wait=600)
    q.set_input_files("#musicInput", song)
    q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
    q.wait_for_function("() => !document.querySelector('#musicDoors .dp-tile[data-dp=\"beat\"]').classList.contains('listening')", timeout=20000)
    q.wait_for_timeout(1000)
    q.click("#musicDoors .dp-tile[data-dp='restart']")
    q.wait_for_timeout(1500)
    rs = q.evaluate("""() => { const box = document.querySelector('.drawer-side'), d = document.getElementById('musicDoorRestart'),
        t = document.querySelector("#musicDoors .dp-tile[data-dp='restart']"); if (!box) return null;
        const b = box.getBoundingClientRect(), r = d.getBoundingClientRect(), tr = t.getBoundingClientRect();
        return { scroll: box.scrollTop, room: box.scrollHeight - box.clientHeight, end: r.bottom, boxEnd: b.bottom, tile: tr.top, boxTop: b.top, page: scrollY,
                 cat: document.getElementById('canvas').getBoundingClientRect().top }; }""")
    c.close()
    check("Pad 1440x900, a 30s song: Restart's door, taller than the screen beside the drawing, shows all of it by the drawer gliding"
          " inside itself, the Restart tile still in it; the page and the drawing stay",
          rs is not None and rs["scroll"] > 0 and rs["end"] <= rs["boxEnd"] + 1 and rs["tile"] >= rs["boxTop"] - 1
          and rs["page"] == 0 and rs["cat"] >= 0, json.dumps(rs))

    # ------------------------------------------------------------ the eyedropper, and the pointer
    print("\nTHE EYEDROPPER, AND THE POINTER — the drawer stays out while it picks; a click lands where it points")
    for ed in ED:
        c, q = boot(b, ed, (1440, 900))
        open_(q, ed, "draw")
        q.click("#eyedropperBtn")
        q.wait_for_timeout(400)
        ey = q.evaluate("""() => { const d = document.getElementById('drawPanel'); return { shown: !d.hidden && !d.classList.contains('eyedropper-veiled') && d.getBoundingClientRect().width > 300, page: scrollY }; }""")
        q.keyboard.press("Escape")
        q.wait_for_timeout(300)
        c.close()
        check(f"{ed}: beside the drawing, picking with the eyedropper leaves the drawer out (nothing to step aside for), the page where it was",
              ey["shown"] and ey["page"] == 0, json.dumps(ey))
    # Flip keeps its drawing's place (flip.js invalidatePadRect, on a resize):
    # without the resize at the slide's end its strokes would land 50-64px off.
    PTS = {"Pad": ("() => strokes.length", "(n) => strokes[n] ? [strokes[n].x, strokes[n].y] : null",
                   "() => { const s = getCanvasLogicalSize(); return [s.width, s.height]; }"),
           "Flip": ("() => frame().strokes.length", "(n) => frame().strokes[n] ? [frame().strokes[n].x, frame().strokes[n].y] : null",
                    "() => [CW, CH]")}
    def stroke(q, ed, fx=0.25, fy=0.75):
        """A stroke begun `fx` across and `fy` down the drawing: its first point, the drawing's logical size."""
        box = q.evaluate("(cv) => { const c = document.getElementById(cv).getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }", ED[ed]["cv"])
        n0 = q.evaluate(PTS[ed][0])
        x, y = box[0] + box[2] * fx, box[1] + box[3] * fy
        q.mouse.move(x, y)
        q.mouse.down()
        for k in range(1, 9):
            q.mouse.move(x + k * 6, y - k * 3)
        q.mouse.up()
        q.wait_for_timeout(300)
        return q.evaluate(PTS[ed][1], n0), q.evaluate(PTS[ed][2])

    def lands(first, lg, fx=0.25, fy=0.75):
        return first is not None and abs(first[0] - lg[0] * fx) <= lg[0] * 0.02 and abs(first[1] - lg[1] * fy) <= lg[1] * 0.02

    SHIFT = "() => getComputedStyle(document.documentElement).getPropertyValue('--side-shift').trim()"
    for ed in ED:
        c, q = boot(b, ed, (1440, 900), load=False)
        open_(q, ed, "draw", wait=900)
        slid = q.evaluate(SHIFT)
        if ed == "Flip":
            # Flip draws with a press on the drawing, and its drawer goes on the click that ends it (its own
            # rule, as below): the drawing holds still while the pen is down, every point landing where it is
            # drawn, and glides home after. A drawer put away on the press would glide it under the pen.
            box = q.evaluate("(cv) => { const c = document.getElementById(cv).getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }", ED[ed]["cv"])
            n0 = q.evaluate(PTS[ed][0])
            x, y = box[0] + box[2] * 0.25, box[1] + box[3] * 0.75
            q.mouse.move(x, y)
            q.mouse.down()
            lefts = []
            for k in range(1, 9):
                q.mouse.move(x + k * 6, y - k * 3)
                q.wait_for_timeout(45)
                lefts.append(q.evaluate("(cv) => document.getElementById(cv).getBoundingClientRect().left", ED[ed]["cv"]))
            q.mouse.up()
            q.wait_for_timeout(900)
            pts = q.evaluate("(n) => frame().strokes.slice(n).map(p => [p.x, p.y])", n0)
            lg = q.evaluate(PTS[ed][2])
            home = not q.evaluate(SHIFT) and not q.evaluate("() => !!(skriblDrawers.beside && skriblDrawers.beside())")
            last_at = ((x + 48 - box[0]) / box[2], (y - 24 - box[1]) / box[3])
            check(f"Flip: with the drawer beside (the drawing slid {slid}), a stroke drawn on the drawing holds it still under the pen"
                  " while it is down, its first and last points landing where they were drawn, and it glides home after",
                  bool(slid) and len(pts) >= 2 and all(abs(v - box[0]) <= 0.5 for v in lefts) and lands(pts[0], lg)
                  and lands(pts[-1], lg, *last_at) and home,
                  json.dumps({"lefts": [round(v, 1) for v in lefts], "from": round(box[0], 1), "first": pts[:1], "last": pts[-1:],
                              "logical": lg, "slid": slid, "home": home}))
            close_(q, ed)
        else:
            # The Pad's first press on the drawing puts a drawer away, as it does below (and draws nothing).
            box = q.evaluate("(cv) => { const c = document.getElementById(cv).getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }", ED[ed]["cv"])
            q.mouse.click(box[0] + box[2] * 0.6, box[1] + box[3] * 0.4)
            q.wait_for_timeout(900)
            away = q.evaluate(f"() => {ED[ed]['ctl']}.current()") is None and not q.evaluate("() => !!(skriblDrawers.beside && skriblDrawers.beside())")
            check(f"Pad: with the drawer beside (the drawing slid {slid}), the first press on the drawing puts it away, as below,"
                  " and the drawing glides home",
                  bool(slid) and away and not q.evaluate(SHIFT), json.dumps({"slid": slid, "away": away}))
        # Home again: a stroke lands where it is drawn.
        first, lg = stroke(q, ed, 0.7, 0.3)
        c.close()
        check(f"{ed}: the drawer gone and the drawing home, a stroke begun seven tenths across and three tenths down lands there",
              lands(first, lg, 0.7, 0.3), json.dumps({"first": first, "logical": lg}))

    # Flip's brush ring keeps the drawing's place (flip.js _padRectCached,
    # cleared on a resize): the slide's end sends one, or the ring would sit
    # as far from the pointer as the drawing slid, there and back.
    RING = """([x, y]) => { const r = document.querySelector('.flip-brush-cursor').getBoundingClientRect();
      return r.width > 0 && getComputedStyle(document.querySelector('.flip-brush-cursor')).display !== 'none'
        ? [Math.round((r.left + r.width / 2 - x) * 10) / 10, Math.round((r.top + r.height / 2 - y) * 10) / 10] : null; }"""
    c, q = boot(b, "Flip", (1440, 900), load=False)
    offs = []
    for step in ("before", "beside", "home"):
        if step == "beside":
            open_(q, "Flip", "draw")
        elif step == "home":
            close_(q, "Flip")
        box = q.evaluate("() => { const c = document.getElementById('pad').getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }")
        pt = (box[0] + box[2] * 0.4, box[1] + box[3] * 0.5)
        q.mouse.move(pt[0] - 12, pt[1] - 6)
        q.mouse.move(*pt)
        q.wait_for_timeout(120)
        offs.append((step, q.evaluate(RING, list(pt))))
    c.close()
    check("Flip: the brush ring stays on the pointer over the drawing before the drawer, with it beside (the drawing slid), and home"
          " again (the slide's end reads the drawing's place again)",
          all(o is not None and abs(o[0]) <= 1.5 and abs(o[1]) <= 1.5 for _, o in offs), json.dumps(offs))

    # ------------------------------------------------------------ room for the drawer
    print("\nROOM FOR THE DRAWER — a drawing too wide to sit beside a drawer gets a little smaller; Flip's strip runs under it")
    WIDE = {"w": 944, "h": 531, "ink": False}          # the 16:9 preset, which fills a desk's width
    for size in ((1366, 768), (1440, 900), (1920, 1080)):
        c, q = boot(b, "Pad", size, load=False, shape=WIDE)
        rest = look(q, "Pad")
        open_(q, "Pad", "draw")
        g = look(q, "Pad")
        close_(q, "Pad")
        back = look(q, "Pad")
        c.close()
        cr, cv, d, R, H = rest["canvas"], g["canvas"], g["drawer"], rest["R"], rest["H"]
        most = R - SIDE_W - 3 * EDGE                      # the widest a drawing beside a drawer can be
        dock = g["moved"][0]
        ok = (g["beside"] and g["side"] and d is not None and abs(d[2] - SIDE_W) <= 1 and abs(d[0] + d[2] - (R - EDGE)) <= 1
              and abs(d[1] - cv[1]) <= 1 and cv[0] >= EDGE - 1 and abs(d[0] - (cv[0] + cv[2]) - EDGE) <= 1.5
              and cv[1] >= 0 and cv[1] + cv[3] <= H and g["scrollY"] == 0
              and cr[2] > most and most - 6 <= cv[2] <= most + 1 and cv[2] >= 0.75 * cr[2]
              and abs(cv[2] / cv[3] - cr[2] / cr[3]) < 0.01 and abs((dock[0] + dock[2] / 2) - (cv[0] + cv[2] / 2)) <= 2
              and not back["beside"] and all(abs(x - y) <= 0.5 for x, y in zip(back["canvas"], cr)))
        check(f"Pad {size[0]}x{size[1]}, a 16:9 drawing too wide to sit beside a drawer ({cr[2]}px, the most beside one {most}px):"
              " the drawer opens beside it all the same, the drawing a little smaller, the least it needs and never past three"
              " quarters, its shape kept, whole on the screen, the drawer level with its top and 16px clear of it, the dock"
              " under its middle; closed, the drawing is its own size again where it was",
              ok, json.dumps({"rest": cr, "open": [g["beside"], cv, d, dock, g["scrollY"]], "most": most, "back": back["canvas"]})[:700])
    c, q = boot(b, "Pad", (1366, 768), load=False, shape=WIDE)
    trace_w = """() => { const c = document.getElementById('canvas'), out = []; window.__tw = out; const t0 = performance.now();
      (function f() { const r = c.getBoundingClientRect(); out.push([r.left, r.width]); if (performance.now() - t0 < 700) requestAnimationFrame(f); })(); }"""
    q.evaluate(trace_w)
    q.evaluate("() => _padDrawerCtl.open('draw')")
    q.wait_for_timeout(850)
    opening = q.evaluate("() => window.__tw")
    q.evaluate(trace_w)
    q.evaluate("() => _padDrawerCtl.open(null)")
    q.wait_for_timeout(850)
    closing = q.evaluate("() => window.__tw")
    c.close()
    gw, gx, bw = glide([w for _, w in opening]), glide([x for x, _ in opening]), glide([w for _, w in closing])
    check("Pad 1366x768, the 16:9 drawing: opening, it glides smaller and left together over many frames, never more than a"
          " third of the way in one, never back; closing, it glides to its own size again the same way",
          gw[0] >= 8 and gw[1] <= 0.34 and gw[2] and gw[3] > 50 and gx[0] >= 8 and gx[2]
          and bw[0] >= 8 and bw[1] <= 0.34 and bw[2] and abs(bw[3] - gw[3]) <= 1.5,
          json.dumps({"width": gw, "left": gx, "back": bw, "ws": [round(w) for _, w in opening[:20]]}))
    c, q = boot(b, "Pad", (1024, 640), load=False, shape=WIDE)
    open_(q, "Pad", "draw")
    g = look(q, "Pad")
    c.close()
    check("Pad 1024x640, the 16:9 drawing, which would give up more than a quarter of its width: the drawer opens below, as before,"
          " the drawing its own size",
          not g["beside"] and g["drawer"] is not None and g["drawer"][1] > g["canvas"][1] + g["canvas"][3] - 1,
          json.dumps({"beside": g["beside"], "canvas": g["canvas"], "drawer": g["drawer"]}))
    # Flip's strip: from its own left to the drawer's right edge, every drawer ending above it; on a short desk too,
    # where the pen's drawer is taller than the room above the strip and scrolls inside itself.
    for size in ((1366, 768), (1440, 900), (1366, 600)):
        c, q = boot(b, "Flip", size)
        rest = look(q, "Flip")
        got = {}
        for name in ("draw", "photo", "music", "text"):
            open_(q, "Flip", name)
            got[name] = look(q, "Flip")
            got[name]["inner"] = q.evaluate("() => { const d = document.querySelector('.drawer-side'); return d ? [d.scrollHeight, d.clientHeight] : null; }")
            close_(q, "Flip")
        back = look(q, "Flip")
        c.close()
        R, st0 = rest["R"], rest["moved"][0]

        def under(g):
            st, d, cv = g["moved"][0], g["drawer"], g["canvas"]
            slid = rest["canvas"][0] - cv[0]
            return (g["beside"] and d is not None and abs(st[0] - (st0[0] - slid)) <= 1 and abs((st[0] + st[2]) - (d[0] + d[2])) <= 2
                    and d[1] + d[3] <= st[1] - 11 and abs(st[1] - st0[1]) <= 1)
        check(f"Flip {size[0]}x{size[1]}: with Pen, Photo, Music or Text beside the drawing, the page strip runs under the drawer, from"
              " its own left (slid with the drawing) to the drawer's right edge, and the drawer ends above it; closed, the strip is"
              " as it was" + (" (here the pen's drawer is taller than the room, and scrolls inside itself)" if size[1] == 600 else ""),
              all(under(g) for g in got.values()) and all(abs(x - y) <= 0.5 for x, y in zip(back["moved"][0], st0))
              and (size[1] != 600 or (got["draw"]["inner"] and got["draw"]["inner"][0] > got["draw"]["inner"][1])),
              json.dumps({"strip": st0, **{k: [g["beside"], g["moved"][0], g["drawer"], g["inner"]] for k, g in got.items()},
                          "back": back["moved"][0]})[:800])
    c, q = boot(b, "Flip", (1366, 768))
    trace_s = """() => { const s = document.querySelector('.strip-wrap'), out = []; window.__ts = out; const t0 = performance.now();
      (function f() { out.push(s.getBoundingClientRect().right); if (performance.now() - t0 < 700) requestAnimationFrame(f); })(); }"""
    q.evaluate(trace_s)
    q.evaluate("() => _flipDrawerCtl.open('draw')")
    q.wait_for_timeout(850)
    out_ = q.evaluate("() => window.__ts")
    q.evaluate(trace_s)
    q.evaluate("() => _flipDrawerCtl.open(null)")
    q.wait_for_timeout(850)
    home = q.evaluate("() => window.__ts")
    c.close()
    so, sh = glide(out_), glide(home)
    check("Flip 1366x768: the strip's end glides out under the drawer as it comes, over many frames, never more than a third of"
          " the way in one, never back; and home again the same way as it goes",
          so[0] >= 8 and so[1] <= 0.34 and so[2] and so[3] > 50 and sh[0] >= 8 and sh[1] <= 0.34 and sh[2] and abs(sh[3] - so[3]) <= 2,
          json.dumps({"out": so, "home": sh, "xs": [round(x) for x in out_[:20]]}))

    # ------------------------------------------------------------ below
    print("\nBELOW — where the two don't fit, with a finger, and on a phone; a resize decides again; the tools tray as it was")
    for label, size, kw in (("an 800x800 desk", (800, 800), {}), ("a tablet (1180x820, a finger)", (1180, 820), {"touch": True}),
                            ("a phone (402x874)", (402, 874), {"phone": True})):
        for ed in ED:
            c, q = boot(b, ed, size, **kw)
            open_(q, ed, "draw")
            g = look(q, ed)
            c.close()
            check(f"{ed}, {label}: the drawer opens below the drawing, as before",
                  not g["beside"] and not g["side"] and g["drawer"] is not None and g["drawer"][1] > g["canvas"][1] + g["canvas"][3] - 1,
                  json.dumps({"beside": g["beside"], "canvas": g["canvas"], "drawer": g["drawer"]}))
    for ed in ED:
        c, q = boot(b, ed, (1440, 900))
        open_(q, ed, "draw")
        a = look(q, ed)["beside"]
        q.set_viewport_size({"width": 800, "height": 800})
        q.wait_for_timeout(900)
        g = look(q, ed)
        q.set_viewport_size({"width": 1440, "height": 900})
        q.wait_for_timeout(900)
        z = look(q, ed)
        close_(q, ed)
        q.evaluate(f"() => {ED[ed]['ctl']}.open('tools')")
        q.wait_for_timeout(700)
        t = look(q, ed)
        tray = q.evaluate("() => { const t = document.getElementById('toolTray'); return !!t && !t.hidden && getComputedStyle(t).position; }")
        c.close()
        check(f"{ed}: opened beside, the window narrowed to 800 puts the drawer below; widened again, beside",
              a and not g["beside"] and g["drawer"] is not None and g["drawer"][1] > g["canvas"][1] + g["canvas"][3] - 1 and z["beside"],
              json.dumps({"wide": a, "narrow": [g["beside"], g["canvas"], g["drawer"]], "again": z["beside"]}))
        check(f"{ed}: the tools tray is never beside, and opens with the page where it was",
              not t["beside"] and tray and tray != "fixed" and t["scrollY"] == 0, json.dumps({"tray": tray, "beside": t["beside"], "y": t["scrollY"]}))
    b.close()

summarise_and_exit()
