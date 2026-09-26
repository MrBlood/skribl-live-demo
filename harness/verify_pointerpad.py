"""Pad draws on Pointer Events (SK312-002): does every path that hangs off a
stroke still work, driven by REAL browser input?

The migration's risk is not the stroke itself. preventDefault() on a
pointerdown suppresses the compatibility MOUSE events for that press, so any
listener Pad hangs off a stroke that still waits for mousemove/mouseup goes
silently dead -- with no error, and with a synthetic-event suite green. So every
row here is driven through CDP (Playwright's mouse, Input.dispatchTouchEvent,
and Input.dispatchMouseEvent with pointerType 'pen'), which produces the whole
real event sequence: pointer, touch and compatibility mouse, in browser order.

What each row pins, and what it replaced:
  * a mouse stroke, and a touch stroke, each land as ONE stroke group;
  * a stroke that leaves the canvas and comes back is still one stroke
    (pointer capture replaced a window mousemove);
  * a second pointer mid-stroke neither restarts nor joins it (the ownership
    rule Flip already had);
  * two fingers on the canvas pinch-zoom and draw nothing;
  * an Apple-Pencil-like pen varies the width, and a finger does not -- the
    end-to-end plumbing verify_pressure could only mark UNVERIFIED while Pad
    was on touch events;
  * the eraser ring follows a MOUSE erase (it listened for mousemove);
  * a mouse drags the photo in reposition mode (it listened on window mouse*);
  * a mouse stroke schedules the autosave (it listened for canvas mouseup).
"""
import os
import struct
import sys
import zlib

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assertions import make_check  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    raise SystemExit(77)

results = []
check = make_check(results)

STATE = """() => ({
  groups: strokeGroups.length, points: strokes.length,
  last: strokeGroups.length ? strokeGroups[strokeGroups.length - 1] : 0,
  drawing: drawing, zoom: ZoomView ? ZoomView.get().zoom : null })"""
LAST_SIZES = """() => { const n = strokeGroups.length ? strokeGroups[strokeGroups.length-1] : 0;
  return n ? strokes.slice(-n).map(p => +p.size.toFixed(3)) : []; }"""


def png(w, h):
    """A real PNG, so the photo path's validators see a real image."""
    raw = b"".join(b"\x00" + bytes((40, 160, 90)) * w for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def fresh(b, touch=False):
    ctx = b.new_context(viewport={"width": 1100, "height": 900}, has_touch=touch)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("() => typeof strokeGroups !== 'undefined' && !!ZoomView", timeout=15000)
    box = pg.locator("#canvas").bounding_box()
    return ctx, pg, errs, box


def mouse_stroke(pg, box, x0=0.3, y0=0.4, steps=10, dx=0.03, dy=0.01):
    pg.mouse.move(box["x"] + box["width"] * x0, box["y"] + box["height"] * y0)
    pg.mouse.down()
    for i in range(1, steps + 1):
        pg.mouse.move(box["x"] + box["width"] * (x0 + i * dx), box["y"] + box["height"] * (y0 + i * dy))
    pg.mouse.up()


with sync_playwright() as sp:
    b = sp.chromium.launch()

    print("\nPOINTER PAD — a stroke is one pointer's, from down to up")
    ctx, pg, errs, box = fresh(b)
    mouse_stroke(pg, box)
    s = pg.evaluate(STATE)
    check("a real mouse stroke lands as one stroke group", s["groups"] == 1 and s["last"] >= 8, str(s))

    # Out past the right edge and back, button held throughout.
    y = box["y"] + box["height"] * 0.6
    pg.mouse.move(box["x"] + box["width"] * 0.8, y)
    pg.mouse.down()
    for x in (0.9, 1.05, 1.2, 1.05, 0.9, 0.8):
        pg.mouse.move(box["x"] + box["width"] * x, y)
    outside = pg.evaluate("() => drawing")
    pg.mouse.up()
    s2 = pg.evaluate(STATE)
    beyond = pg.evaluate("""() => { const n = strokeGroups[strokeGroups.length - 1];
        const w = getCanvasLogicalSize().width;
        return strokes.slice(-n).filter(p => p.x > w).length; }""")
    check("a stroke that leaves the canvas and comes back is still ONE stroke",
          s2["groups"] == 2 and outside is True and s2["last"] >= 6,
          f"{s2}; drawing while outside: {outside}")
    check("...and it kept following the pointer out there (pointer capture)",
          beyond >= 2, f"{beyond} captured points past the right edge")

    # A second pointer lands mid-stroke: refused, not a restart, not a join.
    pg.mouse.move(box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.8)
    pg.mouse.down()
    pg.mouse.move(box["x"] + box["width"] * 0.25, box["y"] + box["height"] * 0.8)
    pg.evaluate("""([x, y]) => { const c = document.getElementById('canvas');
        const o = { pointerId: 99, pointerType: 'touch', isPrimary: false, bubbles: true,
                    cancelable: true, clientX: x, clientY: y, button: 0 };
        c.dispatchEvent(new PointerEvent('pointerdown', o));
        c.dispatchEvent(new PointerEvent('pointermove', Object.assign({}, o, { clientX: x + 40 })));
        c.dispatchEvent(new PointerEvent('pointerup', o)); }""",
                [box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.2])
    still = pg.evaluate("() => drawing")
    pg.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.8)
    pg.mouse.up()
    s3 = pg.evaluate(STATE)
    check("a second pointer mid-stroke neither ends nor restarts the stroke",
          still is True and s3["groups"] == 3 and s3["points"] == sum(
              pg.evaluate("() => strokeGroups")),
          f"drawing after the intruder: {still}; {s3}")

    # Autosave after a MOUSE stroke (its trigger was a canvas mouseup).
    pg.wait_for_function("() => !!localStorage.getItem('skribl_autosave_v1')", timeout=6000)
    check("a mouse stroke schedules the autosave", True)
    check("no page errors from mouse drawing", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nPOINTER PAD — touch: one finger draws, two fingers pinch")
    ctx, pg, errs, box = fresh(b, touch=True)
    cdp = ctx.new_cdp_session(pg)
    X, Y = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5

    def touch(kind, pts):
        cdp.send("Input.dispatchTouchEvent",
                 {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in pts]})

    touch("touchStart", [(1, (X, Y))])
    for i in range(1, 9):
        touch("touchMove", [(1, (X + i * 12, Y + i * 4))])
    touch("touchEnd", [])
    s = pg.evaluate(STATE)
    check("a real one-finger touch stroke lands as one stroke group",
          s["groups"] == 1 and s["last"] >= 6, str(s))

    z0 = pg.evaluate(STATE)["zoom"]
    touch("touchStart", [(1, (X, Y))])
    touch("touchStart", [(1, (X, Y)), (2, (X + 60, Y))])
    for i in range(1, 8):
        touch("touchMove", [(1, (X - i * 10, Y)), (2, (X + 60 + i * 10, Y))])
    touch("touchEnd", [])
    s = pg.evaluate(STATE)
    check("two fingers on the canvas pinch-zoom the view",
          s["zoom"] is not None and s["zoom"] > (z0 or 1) + 0.1, f"zoom {z0} -> {s['zoom']}")
    check("...and the pinch drew nothing", s["groups"] == 1, str(s))
    # THE HEADER COMES BACK (v315, the owner's first look on a phone: "no top
    # menu"). The chrome fades while a stroke is down; after a touch stroke and
    # a pinch the page must not be left in that state.
    chrome = pg.evaluate("""() => ({ stroking: document.body.classList.contains('stroking'),
        header: +getComputedStyle(document.querySelector('.header')).opacity }) """)
    check("after a touch stroke and a pinch the header is back at full strength",
          chrome["stroking"] is False and chrome["header"] > 0.9, str(chrome))
    # THE GLASS IS NEVER THE THING FADED (v315). The header is backdrop-filter
    # glass, and WebKit can fail to repaint such an element after its opacity
    # animates -- the owner's iPhone showed the header's slot empty after a
    # take. So during a stroke the header ELEMENT stays at opacity 1 while its
    # contents whisper, and afterwards the glass is back.
    pg.evaluate("() => document.body.classList.add('stroking')")
    pg.wait_for_timeout(700)
    mid = pg.evaluate("""() => { const h = document.querySelector('.header'), cs = getComputedStyle(h);
        return { self: +cs.opacity, kids: [...h.children].map(k => +getComputedStyle(k).opacity),
                 glass: cs.webkitBackdropFilter || cs.backdropFilter }; }""")
    pg.evaluate("() => document.body.classList.remove('stroking')")
    pg.wait_for_timeout(500)
    after = pg.evaluate("""() => { const cs = getComputedStyle(document.querySelector('.header'));
        return { self: +cs.opacity, glass: cs.webkitBackdropFilter || cs.backdropFilter }; }""")
    check("while drawing, the header's contents fade but the glass element itself is never faded",
          mid["self"] == 1 and mid["kids"] and max(mid["kids"]) <= 0.15, str(mid))
    check("...and after the stroke the header's glass is back",
          after["self"] == 1 and "blur" in (after["glass"] or ""), str(after))
    # A touch on the canvas is Pad's, never the browser's: the touchstart and
    # touchmove are prevented, which is what stops iOS zooming or scrolling
    # the page under a drawing finger (touch-action alone is not enough there).
    prevented = pg.evaluate("""() => { const c = document.getElementById('canvas');
        const r = c.getBoundingClientRect();
        const t = new Touch({ identifier: 9, target: c, clientX: r.left + 20, clientY: r.top + 20 });
        const mk = (k) => new TouchEvent(k, { touches: [t], targetTouches: [t], changedTouches: [t],
                                              bubbles: true, cancelable: true });
        const a = mk('touchstart'), m = mk('touchmove');
        c.dispatchEvent(a); c.dispatchEvent(m);
        c.dispatchEvent(new TouchEvent('touchend', { touches: [], targetTouches: [], changedTouches: [t],
                                                     bubbles: true, cancelable: true }));
        return [a.defaultPrevented, m.defaultPrevented]; }""")
    check("a one-finger touch on the canvas is not left to the browser (no page zoom/scroll)",
          prevented == [True, True], str(prevented))
    check("no page errors from touch", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nPOINTER PAD — a pen's pressure reaches the line; a mouse's does not")
    ctx, pg, errs, box = fresh(b)
    cdp = ctx.new_cdp_session(pg)
    X, Y = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3

    def pen(kind, x, y, force):
        cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left",
                                              "buttons": 1 if kind != "mouseReleased" else 0,
                                              "clickCount": 1, "pointerType": "pen", "force": force})

    forces = [0.15, 0.3, 0.5, 0.7, 0.9, 1.0, 0.8, 0.4]
    pen("mousePressed", X, Y, forces[0])
    for i, f in enumerate(forces[1:], 1):
        pen("mouseMoved", X + i * 15, Y + i * 5, f)
    pen("mouseReleased", X + 120, Y + 40, 0.4)
    sizes = pg.evaluate(LAST_SIZES)
    check("a pen stroke's width follows its pressure",
          len(sizes) >= 5 and len(set(sizes)) >= 3, f"sizes {sizes}")
    mouse_stroke(pg, box, y0=0.6)
    msizes = pg.evaluate(LAST_SIZES)
    check("a mouse stroke stays one width", bool(msizes) and len(set(msizes)) == 1, f"sizes {msizes}")
    ctx.close()

    print("\nPOINTER PAD — what hangs off a stroke still hears it")
    ctx, pg, errs, box = fresh(b)
    pg.evaluate("() => { const b = document.querySelector('[data-tool=\"eraser\"]') || document.getElementById('eraserBtn'); if (b) b.click(); }")
    pg.wait_for_function("() => tool === 'eraser'", timeout=5000)
    RING = "() => { const r = document.getElementById('eraserCursor'); return r ? r.style.left + '|' + r.style.top + '|' + r.style.transform : null; }"
    pg.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    pg.mouse.down()
    pg.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.3)
    r1 = pg.evaluate(RING)
    pg.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.55)
    r2 = pg.evaluate(RING)
    pg.mouse.up()
    check("the eraser ring follows the mouse DURING an erase", r1 is not None and r1 != r2,
          f"ring {r1!r} then {r2!r}")

    check("no page errors from the eraser", not errs, "; ".join(errs[:2]))
    ctx.close()

    # A fresh page: the erase above auto-armed a recording, and reposition is
    # refused while one runs -- a fixture that would fail for the wrong reason.
    ctx, pg, errs, box = fresh(b)
    pg.set_input_files("#photoInput", {"name": "wide.png", "mimeType": "image/png",
                                       "buffer": png(1600, 300)})
    pg.wait_for_function("() => typeof photoBgImg !== 'undefined' && photoBgImg.naturalWidth > 0",
                         timeout=10000)
    pg.evaluate("() => enterReposition()")
    check("precondition: reposition mode is on", pg.evaluate("() => repositioning === true"),
          "without it the drag below is an ordinary stroke and proves nothing")
    ox0 = pg.evaluate("() => photoOffsetX")
    pg.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    pg.mouse.down()
    for i in range(1, 8):
        pg.mouse.move(box["x"] + box["width"] * (0.5 + i * 0.04), box["y"] + box["height"] * 0.5)
    pg.mouse.up()
    ox1 = pg.evaluate("() => photoOffsetX")
    check("a mouse drags the photo in reposition mode", abs(ox1 - ox0) > 0.02,
          f"photoOffsetX {ox0} -> {ox1}")
    check("no page errors from the photo drag", not errs, "; ".join(errs[:2]))
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
