import math, struct, wave, json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/boombap.wav"
# Was a real uploaded loop; that upload isn't in this sandbox, so synthesize a
# track that fills the same role: long enough that its base64 blows the ~4.5 MB
# localStorage ceiling, which is what puts the UI into the amber "re-add" state.
# Matches verify_fix.py's BIG (30s stereo 44.1k -> ~6.7 MB base64).
with wave.open(WAV, "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(30 * 44100):
        _v = int(12000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

STATE = """() => { const el=document.getElementById('autosaveStatus');
    const dot=el.querySelector('.autosave-dot');
    return { text: document.getElementById('autosaveStatusText').textContent,
             cls: el.className,
             dot: getComputedStyle(dot).backgroundColor }; }"""

def scribble(pg, box, seed, n=200):
    cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a=(i/n)*math.pi*6+seed; r=20+(i/n)*150
        pg.mouse.move(cx+math.cos(a)*r, cy+math.sin(a)*r*0.7)
    pg.mouse.up()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1280,"height":900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))

    print("\nFLIP — light turns amber when the file is dropped")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0)
    for k in range(1,4):
        pg.evaluate("addFrame(false)"); pg.wait_for_timeout(70); scribble(pg, box, k*1.2)
    pg.wait_for_timeout(1300)
    s = pg.evaluate(STATE)
    check("green while everything fits", "partial" not in s["cls"], f"{s['text']!r} dot={s['dot']}")

    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(5000)
    s = pg.evaluate(STATE)
    check("amber (not green, not red) after the drop", "partial" in s["cls"] and "failed" not in s["cls"],
          f"{s['text']!r} dot={s['dot']}")
    check("dot is yellow", s["dot"] == "rgb(255, 210, 63)", s["dot"])

    # keep editing — the light must STAY amber, not flip back to green
    scribble(pg, box, 5.5); pg.wait_for_timeout(1400)
    s = pg.evaluate(STATE)
    check("stays amber on later saves", "partial" in s["cls"], f"{s['text']!r}")

    print("\nFLIP — re-add card in the music drawer after reload")
    pg.reload(wait_until="load"); pg.wait_for_timeout(1500)
    s = pg.evaluate(STATE)
    check("amber immediately on restore", "partial" in s["cls"], f"{s['text']!r}")
    card = pg.evaluate("""() => { const c=document.getElementById('musicPending');
        return { hidden: c.hidden, name: document.getElementById('musicPendingName').textContent,
                 meta: document.getElementById('musicPendingMeta').textContent,
                 dropzoneHidden: document.getElementById('musicUploadBtn').hidden }; }""")
    check("music re-add card visible", card["hidden"] is False, json.dumps(card))
    check("card names the file", "boombap" in card["name"], card["name"])
    check("card shows the saved loop", "Loop" in card["meta"], card["meta"])
    check("dropzone hidden behind the card", card["dropzoneHidden"] is True)
    check("drawing survived", pg.evaluate("() => frames.length") == 4,
          f"{pg.evaluate('() => frames.length')} pages")

    print("\nFLIP — re-adding the file restores the loop and clears the warning")
    pg.evaluate("() => { trimStart=0; trimEnd=6; }")   # pretend the saved loop was 0-6s
    pg.evaluate("() => { pendingMusicMeta = {name:'boombap.wav', trimStart:1, trimEnd:7, crossfadeMs:40, enabled:true}; }")
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(5000)
    check("saved loop reapplied on re-add",
          abs(pg.evaluate("() => trimStart") - 1) < 0.01 and abs(pg.evaluate("() => trimEnd") - 7) < 0.01,
          f"trim {pg.evaluate('() => trimStart.toFixed(2)')}–{pg.evaluate('() => trimEnd.toFixed(2)')}s, "
          f"crossfade {pg.evaluate('() => loopCrossfadeMs')}ms")
    check("card hidden once the file is back",
          pg.evaluate("() => document.getElementById('musicPending').hidden") is True)

    print("\nPAD — same honest amber instead of a green light")
    pg.goto(BASE+"/skribl-pad", wait_until="load"); pg.wait_for_timeout(1200)
    pg.evaluate("() => localStorage.clear()")
    pbox = pg.locator("canvas").first.bounding_box()
    pg.mouse.move(pbox["x"]+120, pbox["y"]+120); pg.mouse.down()
    for i in range(60): pg.mouse.move(pbox["x"]+120+i*3, pbox["y"]+120+math.sin(i/4)*40)
    pg.mouse.up(); pg.wait_for_timeout(1800)
    s = pg.evaluate(STATE)
    check("Pad green with no media", "partial" not in s["cls"], f"{s['text']!r} dot={s['dot']}")
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(4500)
    s = pg.evaluate(STATE)
    check("Pad amber once a track is attached", "partial" in s["cls"], f"{s['text']!r} dot={s['dot']}")

    check("no uncaught page errors", not errs, "; ".join(errs[:3]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*60}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
