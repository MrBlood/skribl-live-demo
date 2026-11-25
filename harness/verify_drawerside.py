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
  its top level with the drawing's, inside the screen; the drawing whole on
  the screen at its own size; the page not scrolled.
  ONLY AS FAR AS NEEDED: the drawing slides left by the drawer's room less
  the room at its right (none where there is enough: Flip from 1536px up);
  the header stays; what sits under the drawing (the Pad's dock; Flip's page
  strip and dock) slides with it, by as much.
  IT GLIDES, AND GLIDES BACK: the drawing's left read on every frame moves
  over three frames or more, never more than 60% of the way in one, and
  never back; closing, the same home again. Under Reduce Motion one frame
  carries it.
  INSIDE THE DRAWER: what a tile opens (the pen's Feel) and Restart's door
  with a song in (taller than the screen) show by the drawer's own column
  gliding inside itself, the tile tapped still in it; the page stays.
  THE EYEDROPPER: the drawer stays out while it picks (nothing covers the
  drawing to step aside for).
  STILL WHERE IT POINTS: a click on the drawing after the slide lands where
  it points (the drawing's place is read again: a resize at the end).

Elsewhere:

  BELOW: a 1024x800 desk (the cat would not fit whole beside it), a tablet
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
            "load": "d => loadSkribl(d)", "ready": "() => typeof loadSkribl === 'function' && !!window._padDrawerCtl"},
    "Flip": {"route": "/flip", "cv": "pad", "ctl": "_flipDrawerCtl", "move": [".strip-wrap", ".flip-tools"], "doc": BALL,
             "load": "d => applyFlipDraftObject(d)", "ready": "() => typeof applyFlipDraftObject === 'function' && typeof _flipDrawerCtl !== 'undefined'"},
}
DESKS = ((1440, 900), (1536, 864), (1920, 1080))
SIDE_W, EDGE = 392, 16

# The drawing, the open drawer, the header and what slides, as they are now.
LOOK = """([cv, move]) => {
  const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; };
  const open = [...document.querySelectorAll('#drawPanel, #mediaCard, #txSheet')].find(e => !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 40);
  return { beside: skriblDrawers.beside(), canvas: r(document.getElementById(cv)), drawer: r(open), id: open ? open.id : null,
           side: open ? open.classList.contains('drawer-side') : false, scrollY: scrollY, W: document.documentElement.clientWidth, H: innerHeight,
           header: r(document.querySelector('.header')), moved: move.map(s => r(document.querySelector(s))) }; }"""


def boot(b, ed, size, *, touch=False, phone=False, reduce=False, load=True):
    e = ED[ed]
    kw = {"viewport": {"width": size[0], "height": size[1]}, "device_scale_factor": 1}
    if touch:
        kw.update(has_touch=True)
    if phone:
        kw.update(is_mobile=True, has_touch=True)
    if reduce:
        kw["reduced_motion"] = "reduce"
    c = b.new_context(**kw)
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
            for name in ("draw", "photo", "music", "text"):
                open_(q, ed, name)
                got[name] = look(q, ed)
                if name == "text":
                    close_(q, ed)
            close_(q, ed)
            back = look(q, ed)
            c.close()
            cr, W, H = rest["canvas"], rest["W"], rest["H"]
            right_room = W - (cr[0] + cr[2])
            want = max(0, SIDE_W + 2 * EDGE - right_room)

            def placed(g):
                cv, d = g["canvas"], g["drawer"]
                return (g["beside"] and g["side"] and d is not None and abs(d[2] - SIDE_W) <= 1
                        and d[0] >= cv[0] + cv[2] + 8 and d[0] + d[2] <= W - EDGE + 1 and abs(d[1] - cv[1]) <= 1
                        and d[1] + d[3] <= H + 1 and cv[0] >= 0 and cv[0] + cv[2] <= W and cv[1] >= 0 and cv[1] + cv[3] <= H
                        and abs(cv[2] - cr[2]) <= 1 and abs(cv[3] - cr[3]) <= 1 and g["scrollY"] == 0)
            check(f"{ed} {size[0]}x{size[1]}: Pen, Photo, Music and Text each open beside the drawing, 392px at its right, its top"
                  " level with the drawing's, inside the screen; the drawing whole on the screen at its own size; the page not scrolled",
                  all(placed(g) for g in got.values()),
                  json.dumps({"rest": cr, **{k: [g["beside"], g["canvas"], g["drawer"], g["scrollY"]] for k, g in got.items()}})[:700])
            g = got["draw"]
            slid = cr[0] - g["canvas"][0]
            moved_ok = all(m0 and m1 and abs((m0[0] - m1[0]) - slid) <= 1 for m0, m1 in zip(rest["moved"], g["moved"]))
            check(f"{ed} {size[0]}x{size[1]}: the drawing slides left only as far as the drawer needs ({want:.0f}px here), what sits"
                  " under it with it by as much; the header stays; closed, everything is back",
                  abs(slid - want) <= 1.5 and moved_ok and rest["header"] == g["header"]
                  and not back["beside"] and abs(back["canvas"][0] - cr[0]) <= 1 and back["moved"] == rest["moved"],
                  json.dumps({"slid": slid, "want": want, "moved": [rest["moved"], g["moved"]], "header": [rest["header"], g["header"]],
                              "back": back["canvas"]})[:600])

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
    for ed in ED:
        c, q = boot(b, ed, (1280, 560))
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
        check(f"{ed} 1280x560: the pen's Feel, opened beside, shows all of its choices inside the drawer (its column glides, the"
              " tile still in it), the page where it was",
              m is not None and m["scroll"] > 0 and m["end"] <= m["boxEnd"] + 1 and m["tile"] >= m["boxTop"] - 1 and m["page"] == 0, json.dumps(m))
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
    for ed in ED:
        c, q = boot(b, ed, (1440, 900), load=False)
        open_(q, ed, "draw", wait=900)
        box = q.evaluate("(cv) => { const c = document.getElementById(cv).getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }", ED[ed]["cv"])
        n0 = q.evaluate(PTS[ed][0])
        x, y = box[0] + box[2] * 0.25, box[1] + box[3] * 0.75
        q.mouse.move(x, y)
        q.mouse.down()
        for k in range(1, 9):
            q.mouse.move(x + k * 6, y - k * 3)
        q.mouse.up()
        q.wait_for_timeout(300)
        first = q.evaluate(PTS[ed][1], n0)
        lg = q.evaluate(PTS[ed][2])
        slid = q.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--side-shift').trim()")
        c.close()
        check(f"{ed}: with the drawer beside (the drawing slid {slid}), a stroke begun a quarter across and three quarters down the"
              " drawing lands there in it",
              first is not None and abs(first[0] - lg[0] * 0.25) <= lg[0] * 0.02 and abs(first[1] - lg[1] * 0.75) <= lg[1] * 0.02,
              json.dumps({"first": first, "logical": lg, "slid": slid}))

    # ------------------------------------------------------------ below
    print("\nBELOW — where the two don't fit, with a finger, and on a phone; a resize decides again; the tools tray as it was")
    for label, size, kw in (("a 1024x800 desk", (1024, 800), {}), ("a tablet (1180x820, a finger)", (1180, 820), {"touch": True}),
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
        q.set_viewport_size({"width": 1024, "height": 800})
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
        check(f"{ed}: opened beside, the window narrowed to 1024 puts the drawer below; widened again, beside",
              a and not g["beside"] and g["drawer"] is not None and g["drawer"][1] > g["canvas"][1] + g["canvas"][3] - 1 and z["beside"],
              json.dumps({"wide": a, "narrow": [g["beside"], g["canvas"], g["drawer"]], "again": z["beside"]}))
        check(f"{ed}: the tools tray is never beside, and opens with the page where it was",
              not t["beside"] and tray and tray != "fixed" and t["scrollY"] == 0, json.dumps({"tray": tray, "beside": t["beside"], "y": t["scrollY"]}))
    b.close()

summarise_and_exit()
