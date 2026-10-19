"""The Pad's edges a read-only review found before the next seal (after v326).

Seven paths a person can walk that left the Pad in a state it should not be
in. Each section is driven through the real page with real input where input
is the point, and each was red on the code before its fix:

  * the photo and the music outlive Clear drawing and a post: their bytes
    were deleted while they stayed on screen, so a reload said "Media
    missing" under a pill that had said Saved;
  * Undo and Redo during a replay end it first: the keyboard reached them
    and the canvas jumped while the replay painted on, and a one-stroke
    drawing lost Play/Stop with the replay still running;
  * a shape tap with no drag draws nothing and starts no take, where it
    started an empty one and the next drawing was never recorded;
  * a reload keeps the drawing's name, its pauses and its viewers' speed;
  * New Skribl clears a photo on its own, where it said "Already a fresh one";
  * an image export taken mid-replay is the whole drawing, not the replay so far;
  * a draft opened over a drawing never played paints its see-through strokes
    once, where the old drawing's base decode painted them a second time.
"""
import base64
import json
import os
import struct
import sys
import tempfile
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
DESK = dict(viewport={"width": 1280, "height": 900})


def png(w, h):
    """A real PNG, so the photo path's validators see a real image."""
    raw = b"".join(b"\x00" + bytes((40, 160, 90)) * w for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


PHOTO = os.path.join(tempfile.gettempdir(), "padedges-photo.png")
with open(PHOTO, "wb") as fh:
    fh.write(png(64, 48))

INKED = """() => { const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; }"""
PHOTO_ON = "() => !!(photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName)"
STORE_HAS = "(k) => window.SkriblDraftStore.get(k).then(r => !!(r && r.blob), () => 'error')"


def page_on(b, path="/skribl-pad"):
    ctx = b.new_context(**DESK)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + path, wait_until="load")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("() => typeof strokeGroups !== 'undefined' && !!window.SkriblDraftStore", timeout=15000)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return ctx, pg, errs


def stroke(pg, pts, steps=8):
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + pts[0][0], box["y"] + pts[0][1])
    pg.mouse.down()
    for x, y in pts[1:]:
        pg.mouse.move(box["x"] + x, box["y"] + y, steps=steps)
    pg.mouse.up()


def add_photo(pg):
    pg.set_input_files("#photoInput", PHOTO)
    pg.wait_for_function(PHOTO_ON, timeout=8000)
    pg.wait_for_function("() => window.SkriblDraftStore.get('pad:photo').then(r => !!(r && r.blob))", timeout=8000)
    pg.evaluate("() => openDrawer(null)")
    pg.wait_for_timeout(200)


with sync_playwright() as sp:
    b = sp.chromium.launch()

    print("\nPAD — the photo and the music outlive Clear drawing and a post")
    ctx, pg, errs = page_on(b)
    add_photo(pg)
    stroke(pg, [(100, 100), (240, 160), (360, 120)])
    pg.click("#recordBtn")                       # Done
    pg.wait_for_timeout(300)
    pg.evaluate("() => { openDrawer('draw'); const c = document.getElementById('clearDrawerBtn'); c.click(); c.click(); openDrawer(null); }")
    pg.wait_for_timeout(2200)                    # the autosave's 1.2 s, and the write
    kept = pg.evaluate(STORE_HAS, "pad:photo")
    # The drawing went, the photo stayed, and the autosave says so on its own,
    # not only when a page hide flushes it (dropping it lost the photo to a
    # browser that closed without one).
    slot = pg.evaluate("() => { const r = localStorage.getItem('skribl_autosave_v1'); return r ? JSON.parse(r) : null; }")
    check("Clear drawing rewrites the autosave with the photo in it, and keeps the photo's bytes",
          kept is True and bool(slot) and bool((slot or {}).get("photoMeta")) and not (slot or {}).get("strokes"),
          f"bytes {kept}; autosave {('photoMeta ' + str(bool(slot.get('photoMeta'))) + ', strokes ' + str(len(slot.get('strokes') or []))) if slot else None}")
    pg.reload(wait_until="load")
    pg.wait_for_function("() => typeof strokeGroups !== 'undefined'", timeout=15000)
    pg.wait_for_timeout(2500)
    cleared = pg.evaluate("() => ({ photo: (" + PHOTO_ON + ")(), strokes: strokes.length })")
    check("...and a reload straight after brings back the photo alone",
          cleared["photo"] and cleared["strokes"] == 0, f"after the reload {cleared}")
    stroke(pg, [(120, 300), (260, 330), (400, 290)])
    pg.wait_for_timeout(2200)                    # the autosave's 1.2 s, and the write
    pg.reload(wait_until="load")
    pg.wait_for_function("() => typeof strokeGroups !== 'undefined'", timeout=15000)
    pg.wait_for_timeout(2500)                    # the photo comes back from the store
    back = pg.evaluate("""() => ({ photo: !!(photoBgImg && photoBgImg.style.display !== 'none' && photoBgImg._fileName),
        strokes: strokes.length, missing: !!document.querySelector('.media-missing:not([hidden]), #mediaMissing:not([hidden])') })""")
    check("...and the next drawing over it comes back with it after another reload",
          back["photo"] and back["strokes"] > 0, f"after the reload {back}")
    # The post path drops the draft (it was posted) while the photo stays on the
    # page; the property is the store, so it is read straight after the drop.
    pg.evaluate("() => clearAutosave()")
    pg.wait_for_timeout(300)
    check("...and dropping the draft after a post keeps the bytes while the photo is on the page",
          pg.evaluate(STORE_HAS, "pad:photo") is True and pg.evaluate(PHOTO_ON),
          f"store {pg.evaluate(STORE_HAS, 'pad:photo')}, photo on page {pg.evaluate(PHOTO_ON)}")
    check("no page errors around the photo", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nPAD — Undo and Redo during a replay end it first")
    ctx, pg, errs = page_on(b)
    for k in range(3):
        stroke(pg, [(80 + 120 * k, 100), (120 + 120 * k, 300), (160 + 120 * k, 120)], steps=25)
        pg.wait_for_timeout(300)
    pg.click("#recordBtn")
    pg.wait_for_timeout(300)
    pg.click("#playBtn")
    pg.wait_for_timeout(250)
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(120)
    u = pg.evaluate("() => ({ playing, groups: strokeGroups.length, replaying: document.body.classList.contains('replaying') })")
    pg.keyboard.press("Control+Shift+z")
    pg.wait_for_timeout(120)
    r = pg.evaluate("() => ({ playing, groups: strokeGroups.length })")
    check("Ctrl+Z mid-replay ends the replay, then undoes one stroke; Redo brings it back",
          u["playing"] is False and not u["replaying"] and u["groups"] == 2 and r["groups"] == 3,
          f"after Ctrl+Z {u}; after redo {r}")
    ctx.close()
    ctx, pg, errs = page_on(b)
    stroke(pg, [(80, 100), (300, 300), (500, 120)], steps=60)
    pg.click("#recordBtn")
    pg.wait_for_timeout(300)
    pg.click("#playBtn")
    pg.wait_for_timeout(150)
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(2500)                    # long past the replay's end
    one = pg.evaluate("() => ({ playing, strokes: strokes.length })")
    one["inked"] = pg.evaluate(INKED)
    check("...and undoing a one-stroke drawing mid-replay leaves a blank canvas and no replay",
          one["playing"] is False and one["strokes"] == 0 and one["inked"] == 0, str(one))
    check("no page errors from Undo during a replay", not errs, "; ".join(errs[:2]))
    ctx.close()

    print("\nPAD — a shape tap with no drag draws nothing and starts no take")
    for kind in ("ellipse", "poly"):
        ctx, pg, errs = page_on(b)
        pg.click("#shapeToolBtn")
        pg.wait_for_timeout(150)
        pg.click(f'#shapeSeg [data-shape="{kind}"]')
        pg.wait_for_timeout(150)
        pg.evaluate("() => { document.getElementById('shapePop').hidden = true; }")
        box = pg.locator("#canvas").bounding_box()
        pg.mouse.click(box["x"] + 200, box["y"] + 200)
        pg.wait_for_timeout(200)
        tap = pg.evaluate("() => ({ recording, hasContent, undo: undoStack.length })")
        pg.click("#penToolBtn")
        pg.wait_for_timeout(100)
        stroke(pg, [(100, 300), (250, 320), (400, 280)])
        pg.click("#recordBtn")                   # Done
        pg.wait_for_timeout(300)
        after = pg.evaluate("() => ({ strokes: strokes.length, recorded, post: !document.getElementById('postBtn').disabled })")
        check(f"{kind}: a tap with no drag starts no take and marks nothing drawn; the next pen stroke records",
              tap["recording"] is False and tap["hasContent"] is False and tap["undo"] == 0
              and after["strokes"] > 0 and after["recorded"] and after["post"],
              f"after the tap {tap}; after a pen stroke and Done {after}")
        check(f"{kind}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

    print("\nPAD — a reload keeps the name, the pauses and the viewers' speed")
    ctx, pg, errs = page_on(b)
    pg.evaluate("""() => { const n = document.getElementById('skriblName'); n.value = 'Lighthouse';
        n.dispatchEvent(new Event('input')); setPauseMode('keep'); authorSpeed = 2; }""")
    stroke(pg, [(100, 100), (200, 160), (320, 120)])
    pg.wait_for_timeout(2200)
    pg.reload(wait_until="load")
    pg.wait_for_function("() => typeof strokeGroups !== 'undefined'", timeout=15000)
    pg.wait_for_timeout(1500)
    kept = pg.evaluate("""() => ({ strokes: strokes.length, name: document.getElementById('skriblName').value,
        pause: pauseMode, speed: authorSpeed })""")
    check("the name, Keep pauses and a 2x start for viewers come back after a reload",
          kept["strokes"] > 0 and kept["name"] == "Lighthouse" and kept["pause"] == "keep" and kept["speed"] == 2,
          str(kept))
    ctx.close()

    print("\nPAD — New Skribl clears a photo on its own")
    ctx, pg, errs = page_on(b)
    add_photo(pg)
    pg.click("#menuBtn")
    pg.wait_for_timeout(400)
    pg.click("#menuNewTile")
    pg.wait_for_timeout(400)
    pg.click("#clearMenuItem")
    pg.wait_for_timeout(600)
    gone = pg.evaluate(PHOTO_ON)
    toast = pg.evaluate("() => { const t = document.getElementById('toast'); return t && !t.hidden ? t.textContent : ''; }")
    check("New Skribl with only a photo takes the photo away, and offers Undo",
          gone is False and "New Skribl" in toast, f"photo still on: {gone}; toast {toast!r}")
    ctx.close()

    print("\nPAD — an image export taken mid-replay is the whole drawing")
    ctx, pg, errs = page_on(b)
    for k in range(3):
        stroke(pg, [(80 + 120 * k, 100), (120 + 120 * k, 300), (160 + 120 * k, 120)], steps=25)
        pg.wait_for_timeout(300)
    pg.click("#recordBtn")
    pg.wait_for_timeout(300)
    full = pg.evaluate(INKED)
    pg.click("#playBtn")
    pg.wait_for_timeout(300)
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.click(box["x"] + 600, box["y"] + 500)   # tap to pause, part-way
    pg.wait_for_timeout(200)
    part = pg.evaluate(INKED)
    pg.click("#menuBtn")
    pg.wait_for_timeout(400)
    pg.click("#exportItem")
    pg.wait_for_timeout(500)
    shown = pg.evaluate("() => ({ playing, inked: (" + INKED + ")() })")
    check("opening Export mid-replay ends the replay and shows the whole drawing to save",
          part < full and shown["playing"] is False and shown["inked"] == full,
          f"whole {full}, paused at {part}, at Export {shown}")
    ctx.close()

    print("\nPAD — a draft opened over a drawing never played paints its strokes once")
    ALPHA = "([x, y]) => { const d = window.devicePixelRatio || 1; return ctx.getImageData(Math.round(x * d), Math.round(y * d), 1, 1).data[3]; }"
    ctx, pg, errs = page_on(b)
    pg.evaluate("() => { const s = document.getElementById('opacitySlider'); s.value = 50; s.dispatchEvent(new Event('input')); }")
    stroke(pg, [(100, 200), (400, 200)], steps=30)
    pg.click("#recordBtn")
    pg.wait_for_timeout(300)
    snap = pg.evaluate("() => JSON.stringify(serializeSkribl())")
    pt = pg.evaluate("() => [strokes[Math.floor(strokes.length / 2)].x, strokes[Math.floor(strokes.length / 2)].y]")
    ref = pg.evaluate(ALPHA, pt)
    ctx.close()
    ctx, pg, errs = page_on(b)
    stroke(pg, [(100, 400), (400, 420)], steps=20)
    pg.click("#recordBtn")
    pg.wait_for_timeout(300)
    pg.evaluate("(s) => loadSkribl(JSON.parse(s))", snap)
    pg.wait_for_timeout(900)
    got = pg.evaluate(ALPHA, pt)
    check("a 50% stroke reads the same alpha opened over another drawing as drawn alone",
          ref > 0 and abs(got - ref) <= 4, f"alone {ref}, opened over a drawing never played {got}")
    check("no page errors opening a draft", not errs, "; ".join(errs[:2]))
    ctx.close()
    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
