"""A shared link with a PHOTO must load. Written against a real production bug.

WHY THIS EXISTS. The v190 cut removed the editor shell from the player template
— the drawers, the tab bar, both file inputs, the overflow menu. `loadSkribl()`
was split at the same time so the drawer half runs only on the editor, and the
MUSIC branch got that treatment: state (buffer, trim points, crossfade) on both
surfaces, drawer furniture (labels, waveforms, trim handles) behind a
`player-mode` guard.

The PHOTO branch was missed. It went on writing to markup that no longer exists:

    document.getElementById('photoDetail').hidden = false;   // null on /s/<id>

which threw `TypeError: Cannot set properties of null (setting 'hidden')` on
every shared link carrying a photo. Because it throws INSIDE loadSkribl, the
restore aborted where it stood and everything downstream never ran. One defect
reached the user as three separate-looking faults:

  * a Flip post with a photo that would not play at all;
  * a Pad drawing hanging off the edge of the player, because the canvas was
    never sized and kept authoring dimensions instead of the fitted ones;
  * a replay nib landing nowhere near the ink, because nibScale() divides by an
    authored width that sizePlayerCanvas() never got to set.

1,693 assertions did not catch it. The player was exercised with drawings and
with music, never with a photo — so the branch that broke was the one branch no
fixture entered. That gap is the reason this file exists, and the reason it
asserts on PAGE ERRORS and on canvas GEOMETRY rather than only on ink: the
drawing still rendered while all three symptoms were live, so an ink assertion
alone would have stayed green through the whole outage.

The fixture carries a photo AND music AND a background colour together, because
that combination is what the bug was reported against and each of the three
restores from a different branch of the same function.
"""
import math
import struct
import sys
import wave
import zlib

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/player_photo.wav"
PNG = "/tmp/player_photo.png"

with wave.open(WAV, "wb") as _w:
    _w.setnchannels(1)
    _w.setsampwidth(2)
    _w.setframerate(44100)
    _w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 220 * i / 44100)))
                            for i in range(3 * 44100)))


def _png(w, h):
    raw = b"".join(b"\x00" + bytes([(x * 7) % 256, (y * 5) % 256, 180, 255][k]
                                   for x in range(w) for k in range(4))
                   for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


open(PNG, "wb").write(_png(400, 300))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


STATE = """() => {
  const c = document.getElementById('canvas');
  if (!c) return null;
  const wrap = c.parentElement;
  const cr = c.getBoundingClientRect(), wr = wrap.getBoundingClientRect();
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let ink = 0;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 10) ink++;
  const photo = document.querySelector('#photoBg, .photo-bg, img[id*=photo]');
  return {
    ink, backing: [c.width, c.height],
    css: [Math.round(cr.width), Math.round(cr.height)],
    overflowRight: Math.round(cr.right - wr.right),
    overflowBottom: Math.round(cr.bottom - wr.bottom),
    photoDisplayed: !!(photo && getComputedStyle(photo).display !== 'none'),
    bg: getComputedStyle(wrap).backgroundColor,
  };
}"""


def scribble(pg, box, n=90):
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * 110
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 5 == 0:
            pg.wait_for_timeout(110)
    pg.mouse.up()


with sync_playwright() as sp:
    b = sp.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    print("PLAYER PHOTO — author a Skribl carrying photo, colour and music")
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    ed_errs = []
    pg.on("pageerror", lambda e: ed_errs.append(str(e)))
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    pg.set_input_files("#photoInput", PNG)
    pg.wait_for_timeout(2500)
    pg.set_input_files("#musicInput", WAV)
    pg.wait_for_timeout(4000)
    pg.evaluate("() => { const s = document.querySelector('.bg-swatch:not(.active)'); if (s) s.click(); }")
    pg.wait_for_timeout(300)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    scribble(pg, pg.locator("#canvas").bounding_box())
    pg.wait_for_timeout(600)
    pg.click("#recordBtn")
    pg.wait_for_timeout(500)
    editor = pg.evaluate(STATE)
    check("the editor itself restored the photo cleanly", not ed_errs,
          "; ".join(ed_errs[:2]))

    pg.click("#postBtn")
    pg.wait_for_timeout(1200)
    pg.click("#postSubmitBtn")
    pg.wait_for_timeout(9000)
    link = pg.evaluate("""() => {
        const v = [...document.querySelectorAll('*')].map(e => e.value || e.href || '')
          .find(v => typeof v === 'string' && v.includes('/s/'));
        return v || null; }""")
    pg.close()

    if not link:
        check("posting produced a share link (fixture)", False,
              f"no /s/ URL; editor errors: {ed_errs[:2]}")
        print("\n" + "=" * 62 + "\n0/1 passed  FAILURES: fixture")
        sys.exit(1)
    print(f"    authored {link}, editor ink {editor['ink']}\n")

    print("PLAYER PHOTO — the shared link restores it without editor markup")
    pg = b.new_page(viewport={"width": 420, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(link, wait_until="load")
    pg.wait_for_timeout(3500)
    st = pg.evaluate(STATE)

    # THE assertion. Everything else here is a symptom of this one going red.
    check("the player raises no page error restoring a photo", not errs,
          "; ".join(e[:120] for e in errs[:2])
          + "  — loadSkribl aborts on the first null, so the whole restore stops")

    check("the canvas was sized by the player, not left at the HTML default",
          st and st["backing"] != [300, 150],
          f"backing {st and st['backing']} — 300x150 means sizePlayerCanvas() never ran")
    check("the drawing fits inside its wrapper", st and st["overflowRight"] <= 1
          and st["overflowBottom"] <= 1,
          f"overflow right {st and st['overflowRight']}px, bottom {st and st['overflowBottom']}px")
    check("the photo layer is displayed", st and st["photoDisplayed"],
          "the photo restores from the same branch that threw")
    check("the drawing rendered", st and st["ink"] > 200,
          f"{st and st['ink']} inked pixels")

    print("\nPLAYER PHOTO — and it plays")
    before = pg.evaluate(STATE)["ink"]
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(700)
    mid = pg.evaluate(STATE)["ink"]
    check("pressing play restarts from a cleared canvas and redraws",
          mid < before,
          f"{before} inked before play, {mid} shortly after — playback never started")
    pg.wait_for_timeout(3000)
    end = pg.evaluate(STATE)["ink"]
    check("and reaches the finished drawing again", end >= before * 0.9,
          f"ended at {end} against a poster of {before}")
    check("no page error appeared during playback", not errs,
          "; ".join(e[:120] for e in errs[:2]))
    pg.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
