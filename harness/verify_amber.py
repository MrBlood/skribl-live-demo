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

def try_click(pg, sel, ms=3000):
    """Click, and turn "the element was never actionable" into a VALUE rather
    than an exception.

    Playwright waits for actionability before clicking, so against an element
    that is invisible, zero-sized or carrying `pointer-events: none` it does not
    fail fast — it blocks for the full default timeout and then raises, which
    run_harness.sh records as "crashed before reporting" with no assertion
    named. Every mutation of the v238 pill fix was caught that way at first:
    caught, and caught uselessly. Both of the states this section tests for —
    a pill that takes no taps, a dismiss button sitting 0x0 in a drawer that
    never opened — are exactly the states that wedge a click, so the guard is
    not defensiveness, it is the reporting channel for the defect itself."""
    try:
        pg.click(sel, timeout=ms)
        return True, ""
    except Exception as e:                                   # noqa: BLE001
        return False, type(e).__name__


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

    # CONTRACT CHANGE (v222, external review #3): amber used to mean "media is
    # attached and localStorage cannot hold it" — a designed limitation, pinned
    # here as 'amber after the drop' / 'stays amber on later saves'. The quota
    # fallback now spills the FULL payload to IndexedDB (lib/draftstore.js), so
    # with a working store the session IS fully recoverable and the honest
    # light is GREEN. Amber didn't die — it moved to the failure case, and the
    # old persistence assertions moved with it (broken-store section below).
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(5000)
    s = pg.evaluate(STATE)
    check("GREEN after the drop — the spill made the session recoverable",
          "partial" not in s["cls"] and "failed" not in s["cls"],
          f"{s['text']!r} dot={s['dot']}")
    spilled = pg.evaluate("""() => window.SkriblDraftStore.get('flip:draft')
        .then(r => !!(r && r.json)).catch(() => false)""")
    check("because the full payload is in IndexedDB", spilled is True)

    # keep editing — later saves spill again and settle green again
    scribble(pg, box, 5.5); pg.wait_for_timeout(2600)
    s = pg.evaluate(STATE)
    check("stays green on later saves while the store works",
          "partial" not in s["cls"], f"{s['text']!r}")

    print("\nFLIP — after reload the media comes BACK from IndexedDB")
    pg.reload(wait_until="load"); pg.wait_for_timeout(4500)   # merge + ~7MB decode
    m = pg.evaluate("""() => ({ music: typeof musicData === 'string' && musicData.slice(0,10) === 'data:audio',
        cardHidden: document.getElementById('musicPending').hidden,
        frames: frames.length })""")
    check("drawing survived", m["frames"] == 4, f"{m['frames']} pages")
    check("the track itself is restored — bytes, not a re-add card",
          m["music"] is True and m["cardHidden"] is True, json.dumps(m))

    print("\nFLIP — with the store BROKEN, the old amber contract holds")
    # This is where 'amber and STAYS amber' lives now: media attached, quota
    # hit, and no IndexedDB to spill to — the session genuinely is not fully
    # recoverable, and the light must say so for as long as it is true.
    pg2 = b.new_page(viewport={"width":1280,"height":900})
    errs2 = []; pg2.on("pageerror", lambda e: errs2.append(str(e)))
    pg2.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pg2.goto(BASE+"/flip", wait_until="load"); pg2.wait_for_timeout(700)
    pg2.evaluate("() => localStorage.clear()")
    box2 = pg2.locator("#pad").bounding_box()
    scribble(pg2, box2, 0.0)
    for k in range(1,4):
        pg2.evaluate("addFrame(false)"); pg2.wait_for_timeout(70); scribble(pg2, box2, k*1.2)
    pg2.wait_for_timeout(1300)
    pg2.set_input_files("#musicInput", WAV); pg2.wait_for_timeout(5000)
    s = pg2.evaluate(STATE)
    check("amber (not green, not red) after the drop", "partial" in s["cls"] and "failed" not in s["cls"],
          f"{s['text']!r} dot={s['dot']}")
    check("dot is yellow", s["dot"] == "rgb(255, 210, 63)", s["dot"])
    scribble(pg2, box2, 5.5); pg2.wait_for_timeout(1400)
    s = pg2.evaluate(STATE)
    check("stays amber on later saves", "partial" in s["cls"], f"{s['text']!r}")
    # THE OTHER AMBER, and the reason there are two wordings. This context has
    # IndexedDB disabled, so the bytes never spilled — but the photo and the
    # track are still LOADED, sitting in front of the user. Nothing is missing
    # and nothing needs re-adding; it simply will not survive a reload. Offering
    # "tap to re-add" here would send them to a drawer with no card in it.
    noroute = pg2.evaluate("""() => { const el = document.getElementById('autosaveStatus');
        return { text: document.getElementById('autosaveStatusText').textContent,
                 actionable: el.classList.contains('actionable'),
                 role: el.getAttribute('role') }; }""")
    check("amber with nothing to re-add does NOT pretend to be a route",
          noroute["actionable"] is False and noroute["role"] is None
          and "re-add" not in noroute["text"].lower(),
          f"{noroute} — the media is still loaded here; a control promising to "
          "bring it back would open an empty drawer")

    print("\nFLIP — re-add card in the music drawer after reload (store still broken)")
    pg2.reload(wait_until="load"); pg2.wait_for_timeout(1500)
    s = pg2.evaluate(STATE)
    check("amber immediately on restore", "partial" in s["cls"], f"{s['text']!r}")
    card = pg2.evaluate("""() => { const c=document.getElementById('musicPending');
        return { hidden: c.hidden, name: document.getElementById('musicPendingName').textContent,
                 meta: document.getElementById('musicPendingMeta').textContent,
                 dropzoneHidden: document.getElementById('musicUploadBtn').hidden }; }""")
    check("music re-add card visible", card["hidden"] is False, json.dumps(card))
    check("card names the file", "boombap" in card["name"], card["name"])
    check("card shows the saved loop", "Loop" in card["meta"], card["meta"])
    check("dropzone hidden behind the card", card["dropzoneHidden"] is True)
    check("drawing survived", pg2.evaluate("() => frames.length") == 4,
          f"{pg2.evaluate('() => frames.length')} pages")

    print("\nFLIP — the amber pill is a ROUTE, not a dead end (v238)")
    # WHY THESE ASSERTIONS EXIST AT ALL, because "amber immediately on restore"
    # above passes without a single one of them.
    #
    # v229 showed this amber. It was TRUE and it was reported from the live demo
    # as intolerable, because it went nowhere: the pill said media was missing,
    # the only controls that could do anything about it were the Re-add and
    # Dismiss buttons on a card inside a shut drawer, and that card measures 0x0
    # until the drawer is opened. So v235 removed the pill instead of the dead
    # end, and that is what broke the assertion above.
    #
    # The amber is back because the pill now OPENS that drawer. If someone later
    # deletes the route and keeps the warning, every assertion above still passes
    # and the product is back to the state its owner already rejected once. These
    # are the assertions that would fail.
    pill = pg2.evaluate("""() => { const el = document.getElementById('autosaveStatus');
        const cs = getComputedStyle(el);
        return { text: document.getElementById('autosaveStatusText').textContent,
                 actionable: el.classList.contains('actionable'),
                 role: el.getAttribute('role'), tab: el.getAttribute('tabindex'),
                 pe: cs.pointerEvents }; }""")
    check("the amber pill NAMES the way out",
          "re-add" in pill["text"].lower(),
          f"{pill['text']!r} — 'Saved without media' states a problem and offers "
          "nothing; the only control that resolves it is two taps away in a "
          "drawer with no sign it is there")
    check("...and is a real control, not a div that responds to poking",
          pill["role"] == "button" and pill["tab"] == "0",
          f"role={pill['role']} tabindex={pill['tab']} — announced as a button "
          "only while it actually is one")
    # THE ONE THAT IS EASIEST TO LOSE AND HARDEST TO SEE. The base pill sets
    # pointer-events:none so a status floating over a control cannot eat the tap
    # meant for it. A click listener alone therefore does NOTHING — the event
    # never reaches the element. Nothing about the JS says so.
    check("...and actually receives taps",
          pill["pe"] == "auto",
          f"pointer-events: {pill['pe']} — the base pill is `none` on purpose, so "
          "a listener without this is a control that silently ignores every tap")
    pg2.evaluate("() => _flipDrawerCtl.open(null)")
    pg2.wait_for_timeout(200)
    clicked, why = try_click(pg2, "#autosaveStatus")
    pg2.wait_for_timeout(400)
    check("the pill can be clicked at all",
          clicked,
          f"{why} — Playwright refused to click it, which is what an element "
          "that is not actually interactive looks like from the outside")
    opened = pg2.evaluate("""() => { const c = document.getElementById('musicPending');
        const r = c.getBoundingClientRect();
        return { drawer: _flipDrawerCtl.isOpen('music'), cardHidden: c.hidden,
                 w: Math.round(r.width), h: Math.round(r.height) }; }""")
    check("tapping the pill opens the drawer holding the missing file",
          opened["drawer"] is True and opened["cardHidden"] is False,
          json.dumps(opened))
    # 0x0 IS THE WHOLE COMPLAINT. `hidden: false` on a card inside a shut drawer
    # is what the old code already reported, and it is why the assertion has to
    # measure the box rather than trust the flag.
    check("...and the re-add card has a real size once it is there",
          opened["w"] > 100 and opened["h"] > 20,
          f"{opened['w']}x{opened['h']} — an element can be `hidden: false` and "
          "still measure 0x0 inside a collapsed drawer, which is exactly the "
          "state the owner reported as a warning with no way out")
    # THE LOOP CLOSES. A warning you can act on but never end is the same dead
    # end wearing a button.
    dismissed, dwhy = try_click(pg2, "#musicPendingDismiss")
    check("the Dismiss on the card is reachable once the drawer is open",
          dismissed,
          f"{dwhy} — this button is the ONLY thing that clears a pending record, "
          "and until v238 it sat 0x0 in a drawer nothing on screen pointed at")
    pg2.wait_for_timeout(1600)
    s = pg2.evaluate(STATE)
    check("dismissing the card ENDS the amber",
          "partial" not in s["cls"],
          f"{s['text']!r} — the record is gone, so the next save omits nothing "
          "and says so; without this the pill outlives the situation it "
          "describes, which is what made the old one intolerable")
    check("...and the pill stops being a control when it stops warning",
          pg2.evaluate("() => document.getElementById('autosaveStatus')"
                       ".classList.contains('actionable')") is False,
          "a status that still looks tappable after there is nowhere to go "
          "sends the user to an empty drawer")

    print("\nFLIP — re-adding the file restores the loop and clears the warning")
    pg2.evaluate("() => { trimStart=0; trimEnd=6; }")   # pretend the saved loop was 0-6s
    pg2.evaluate("() => { pendingMusicMeta = {name:'boombap.wav', trimStart:1, trimEnd:7, crossfadeMs:40, enabled:true}; }")
    pg2.set_input_files("#musicInput", WAV); pg2.wait_for_timeout(5000)
    check("saved loop reapplied on re-add",
          abs(pg2.evaluate("() => trimStart") - 1) < 0.01 and abs(pg2.evaluate("() => trimEnd") - 7) < 0.01,
          f"trim {pg2.evaluate('() => trimStart.toFixed(2)')}–{pg2.evaluate('() => trimEnd.toFixed(2)')}s, "
          f"crossfade {pg2.evaluate('() => loopCrossfadeMs')}ms")
    check("card hidden once the file is back",
          pg2.evaluate("() => document.getElementById('musicPending').hidden") is True)
    pg2.close()

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
    check("Pad GREEN once a track is attached — its bytes are in IndexedDB",
          "partial" not in s["cls"], f"{s['text']!r} dot={s['dot']}")
    ok_bytes = pg.evaluate("""() => window.SkriblDraftStore.get('pad:music')
        .then(r => !!(r && r.blob && r.blob.size > 0)).catch(() => false)""")
    check("because the attach stored them", ok_bytes is True)

    check("no uncaught page errors", not errs, "; ".join(errs[:3]))
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
