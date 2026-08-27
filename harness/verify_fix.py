import json, math, struct, wave, os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

def make_wav(path, seconds, sr=44100):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        buf = bytearray()
        for i in range(seconds * sr):
            v = int(12000 * math.sin(2*math.pi*220*i/sr))
            buf += struct.pack("<hh", v, v)
        w.writeframes(bytes(buf))
    return path

BIG   = make_wav("/tmp/big.wav", 30)    # ~6.7 MB base64 -> must exceed quota
SMALL = make_wav("/tmp/small.wav", 8)   # ~1.8 MB base64 -> must still fit

PILL = "() => document.getElementById('autosaveStatusText').textContent"
STORED = ("() => { const r = localStorage.getItem('skribl_flip_autosave_v1');"
          "return r ? +(r.length/1048576).toFixed(2) : null; }")

def scribble(pg, box, seed, n=300):
    cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a = (i/n)*math.pi*6 + seed; r = 20 + (i/n)*150
        pg.mouse.move(cx+math.cos(a)*r, cy+math.sin(a)*r*0.7)
    pg.mouse.up()

results = []
def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width":1280,"height":900})
    pg = ctx.new_page()
    # SCOPE (v222): this suite pins the media-less FALLBACK contract — bytes
    # stripped, meta preserved, later edits keep saving, re-add card on
    # reload. Since the quota spill to IndexedDB landed (lib/draftstore.js),
    # that fallback is reachable only when the store is unavailable, so this
    # page runs WITHOUT IndexedDB and the contract stays exactly as written.
    # The working-store path — spill, green pill, media back on reload — is
    # pinned in verify_amber.py, verify_dots.py and verify_drafts.py. Tests
    # 3 and 4 (under-quota fidelity, draft-file serialization) never touch
    # the store and are unaffected by this.
    pg.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pgerrs = []
    pg.on("pageerror", lambda e: pgerrs.append(str(e)))

    # ---------- TEST 1: oversized track no longer kills autosave ----------
    print("\nTEST 1 — 30s track (over quota) + 6 pages")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(500)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0)
    for k in range(1, 6):
        pg.evaluate("addFrame(false)"); pg.wait_for_timeout(60); scribble(pg, box, k*1.1)
    pg.wait_for_timeout(1300)
    pre_pts = pg.evaluate("() => frames.reduce((a,f)=>a+f.strokes.length,0)")
    pg.set_input_files("#musicInput", BIG); pg.wait_for_timeout(3000)

    check("pill is not 'Autosave failed'", pg.evaluate(PILL) != "Autosave failed",
          f"pill = {pg.evaluate(PILL)!r}")
    check("autosave was actually written", pg.evaluate(STORED) is not None,
          f"{pg.evaluate(STORED)} MB stored")
    saved = pg.evaluate("() => JSON.parse(localStorage.getItem('skribl_flip_autosave_v1'))")
    check("media bytes stripped from localStorage",
          saved.get("music") is None and saved.get("bgImage") is None)
    check("mediaOmitted flag set", saved.get("mediaOmitted") is True)
    check("musicMeta (name/trim/crossfade) preserved", saved.get("musicMeta") is not None,
          json.dumps(saved.get("musicMeta")))
    check("all 6 pages of strokes preserved", len(saved.get("frames", [])) == 6,
          f"{len(saved.get('frames',[]))} frames, {sum(len(f['strokes']) for f in saved['frames'])}/{pre_pts} pts")

    # edits AFTER the oversized track must keep saving (the real damage before)
    scribble(pg, box, 9.9); pg.wait_for_timeout(1300)
    post = pg.evaluate("() => JSON.parse(localStorage.getItem('skribl_flip_autosave_v1'))")
    check("later edits still autosave",
          sum(len(f["strokes"]) for f in post["frames"]) > sum(len(f["strokes"]) for f in saved["frames"]),
          f"{sum(len(f['strokes']) for f in saved['frames'])} -> {sum(len(f['strokes']) for f in post['frames'])} pts")

    # ---------- TEST 2: reload restores the drawing + prompts re-add ----------
    print("\nTEST 2 — reload restores work, prompts for the track")
    pg.reload(wait_until="load"); pg.wait_for_timeout(1200)
    check("drawing restored after reload",
          pg.evaluate("() => frames.length") == 6,
          f"{pg.evaluate('() => frames.length')} pages, "
          f"{pg.evaluate('() => frames.reduce((a,f)=>a+f.strokes.length,0)')} pts")
    card = pg.evaluate("() => ({ hidden: document.getElementById('musicPending').hidden,"
                       " name: document.getElementById('musicPendingName').textContent })")
    check("music re-add card shown in the drawer", card["hidden"] is False, str(card))

    # ---------- TEST 3: regression — a track that FITS keeps full fidelity ----------
    # STILL CORRECT AFTER v231, and worth saying why, because v231 reversed the
    # contract this looks like it is testing. Media bytes normally go to
    # IndexedDB now and localStorage keeps strokes and metadata only — but this
    # suite's context runs the page with `window.indexedDB` undefined (see the
    # init script above), so there is nowhere to spill to and Flip takes its
    # no-IndexedDB fallback: the whole payload into localStorage, exactly as
    # asserted below. That fallback is the reason these assertions were left
    # alone rather than rewritten.
    #
    # v231 also fixed a bug this section exposed: the "can I spill?" test read
    # `window.SkriblDraftStore`, which is the LIBRARY, and the library loads
    # fine with indexedDB undefined. So Flip took the spill path, the put
    # rejected, and a track that fits was reported as "Saved without media".
    # The check tests for indexedDB itself now.
    #
    # verify_flipdraft.py covers the normal, IndexedDB-present path.
    print("\nTEST 3 — regression: 8s track (fits) must still save WITH audio")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(500)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0, 150); pg.wait_for_timeout(1200)
    pg.set_input_files("#musicInput", SMALL); pg.wait_for_timeout(2500)
    small = pg.evaluate("() => JSON.parse(localStorage.getItem('skribl_flip_autosave_v1'))")
    check("pill reads plain 'Saved'", pg.evaluate(PILL) == "Saved", f"pill = {pg.evaluate(PILL)!r}")
    check("audio bytes STILL stored when they fit",
          isinstance(small.get("music"), str) and small["music"].startswith("data:audio"),
          f"{len(small.get('music') or '')/1048576:.2f} MB data URL")
    check("mediaOmitted absent on the happy path", "mediaOmitted" not in small or small["mediaOmitted"] is None)
    pg.reload(wait_until="load"); pg.wait_for_timeout(1500)
    check("audio survives reload unchanged",
          pg.evaluate("() => !!musicData && musicData.slice(0,10)==='data:audio'"))

    # ---------- TEST 4: regression — .skribl draft still carries media ----------
    print("\nTEST 4 — regression: saveDraft still serializes full media")
    check("serializeFlip() default keeps audio bytes",
          pg.evaluate("() => { const d = serializeFlip(); return !!d.music && d.music.slice(0,10)==='data:audio'; }"))
    check("serializeFlip({media:false}) drops them",
          pg.evaluate("() => serializeFlip({media:false}).music === null"))
    check("draft blob is the full-fidelity one",
          pg.evaluate("() => JSON.stringify(serializeFlip()).length > "
                      "JSON.stringify(serializeFlip({media:false})).length * 5"))

    # ---------- TEST 5: regression — empty state still clears the key ----------
    print("\nTEST 5 — regression: empty Flip clears the autosave key")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(400)
    pg.evaluate("() => localStorage.setItem('skribl_flip_autosave_v1','{\"stale\":1}')")
    pg.evaluate("() => { frames = [newFrame()]; idx=0; bgImage=null; musicData=null; saveNow(); }")
    check("stale key removed on empty",
          pg.evaluate("() => localStorage.getItem('skribl_flip_autosave_v1') === null"))

    check("no uncaught page errors", not pgerrs, "; ".join(pgerrs[:3]))
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*60}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.
import sys
sys.exit(1 if bad else 0)
