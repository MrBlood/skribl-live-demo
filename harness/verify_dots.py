import math, struct, wave
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/boombap.wav"
# See verify_amber.py: the original uploaded loop isn't in this sandbox, so
# synthesize an equivalent over-quota track (30s stereo -> ~6.7 MB base64).
with wave.open(WAV, "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(30 * 44100):
        _v = int(12000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))
AMBER = "rgb(255, 210, 63)"

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

COLOURS = """(which) => {
    const dot = document.getElementById(which + 'TabDot');
    const card = document.getElementById(which === 'photo' ? 'photoPending' : 'musicPending');
    const btn = document.getElementById(which === 'photo' ? 'photoPendingBtn' : 'musicPendingBtn');
    const meta = document.getElementById(which === 'photo' ? 'photoPendingMeta' : 'musicPendingMeta');
    const cs = e => e ? getComputedStyle(e) : null;
    return { dotHidden: dot ? dot.hidden : null,
             dotPending: dot ? dot.classList.contains('pending') : null,
             dotBg: dot ? cs(dot).backgroundColor : null,
             cardHidden: card ? card.hidden : null,
             cardBorder: card ? cs(card).borderTopColor : null,
             btnBg: btn ? cs(btn).backgroundColor : null,
             metaColor: meta ? cs(meta).color : null }; }"""

def scribble(pg, box, seed, n=200):
    cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a=(i/n)*math.pi*6+seed; r=20+(i/n)*150
        pg.mouse.move(cx+math.cos(a)*r, cy+math.sin(a)*r*0.7)
    pg.mouse.up()

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1280,"height":900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))

    print("\nFLIP")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0); pg.wait_for_timeout(1200)
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(5000)
    c = pg.evaluate(COLOURS, "music")
    check("music dot GREEN while the file is loaded", c["dotBg"] == "rgb(27, 207, 143)" and not c["dotPending"], c["dotBg"])

    # CONTRACT CHANGE (v222): with a working IndexedDB the quota spill brings
    # the media BACK on reload, so the dot is honestly green and there is no
    # re-add to ask for. The amber palette is still a real state — it now
    # means the store failed — so those assertions run against a page with
    # IndexedDB broken, where re-add genuinely is needed.
    pg.reload(wait_until="load"); pg.wait_for_timeout(4500)   # IDB merge + ~7MB decode
    c = pg.evaluate(COLOURS, "music")
    check("music dot visible after reload", c["dotHidden"] is False)
    check("music dot GREEN — the media came back from IndexedDB",
          not c["dotPending"] and c["cardHidden"] is True,
          f"{c['dotBg']} pending={c['dotPending']} cardHidden={c['cardHidden']}")

    pgB = b.new_page(viewport={"width":1280,"height":900})
    errsB = []; pgB.on("pageerror", lambda e: errsB.append(str(e)))
    pgB.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pgB.goto(BASE+"/flip", wait_until="load"); pgB.wait_for_timeout(700)
    pgB.evaluate("() => localStorage.clear()")
    boxB = pgB.locator("#pad").bounding_box()
    scribble(pgB, boxB, 0.0); pgB.wait_for_timeout(1200)
    pgB.set_input_files("#musicInput", WAV); pgB.wait_for_timeout(5000)
    pgB.reload(wait_until="load"); pgB.wait_for_timeout(1600)
    c = pgB.evaluate(COLOURS, "music")
    check("music dot AMBER when re-add is needed", c["dotBg"] == AMBER and c["dotPending"], c["dotBg"])
    check("re-add card visible", c["cardHidden"] is False)
    check("card border amber", "255, 210, 63" in c["cardBorder"], c["cardBorder"])
    check("Re-add button amber", c["btnBg"] == AMBER, c["btnBg"])
    check("card meta text amber", c["metaColor"] == AMBER, c["metaColor"])
    pgB.close()

    print("\nPAD")
    pg.goto(BASE+"/skribl-pad", wait_until="load"); pg.wait_for_timeout(1200)
    pg.evaluate("() => localStorage.clear()")
    pbox = pg.locator("canvas").first.bounding_box()
    pg.mouse.move(pbox["x"]+120, pbox["y"]+120); pg.mouse.down()
    for i in range(60): pg.mouse.move(pbox["x"]+120+i*3, pbox["y"]+120+math.sin(i/4)*40)
    pg.mouse.up(); pg.wait_for_timeout(1800)
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(4500)
    pg.reload(wait_until="load"); pg.wait_for_timeout(2000)
    pg.locator("#restoreConfirm").click(); pg.wait_for_timeout(4000)   # Pad gates restore behind a banner; IDB re-add + decode
    # CONTRACT CHANGE (v222): restore used to leave an amber pending dot —
    # the bytes were gone by design and re-adding was the user's job. The
    # bytes now come back from IndexedDB through the real change pipeline,
    # so the honest dot is GREEN with the track actually present. The amber
    # dot still exists and is pinned in verify_amber.py's broken-store
    # section, where it is true.
    c = pg.evaluate(COLOURS, "music")
    got = pg.evaluate("() => !!(audioEl && audioEl._fileName)")
    check("Pad music dot GREEN after restore — the track came back",
          got is True and c["dotPending"] is False and c["dotHidden"] is False,
          f"{c['dotBg']} pending={c['dotPending']} track={got}")
    check("Pad card amber", c["btnBg"] == AMBER, c["btnBg"])

    check("no uncaught page errors", not errs, "; ".join(errs[:2]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*58}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.
import sys
sys.exit(1 if bad else 0)
