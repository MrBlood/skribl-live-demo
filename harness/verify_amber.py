import math, struct, wave, json
from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

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
check = make_check(results)

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
    # THE DARK THEME, EXPLICITLY (v292): the literals below are the dark ramp's amber. Since
    # v292 a bare page follows the OS and headless Chromium says light, on which amber is
    # rgb(138, 91, 0). The pin is the semantics (amber, not green, not red); measured on the
    # ramp it was written for.
    pg = b.new_page(viewport={"width":1280,"height":900}, color_scheme="dark")
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
    pg2 = b.new_page(viewport={"width":1280,"height":900}, color_scheme="dark")
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

    print("\nFLIP — the amber with nothing to re-add can be acknowledged (v294)")
    # From a phone: "Saved without media ... stays and doesn't fade and
    # media is there. It never leaves." The warning is true — the bytes did not
    # reach the store — and it had no exit. The × acknowledges it for the
    # session; a change of state speaks again.
    ack = pg2.evaluate("""() => { const x = document.getElementById('autosaveStatusDismiss');
        return x ? { hidden: x.hidden, pe: getComputedStyle(x).pointerEvents, label: x.getAttribute('aria-label') || '' } : null; }""")
    check("the × is offered on this amber too, and takes taps",
          bool(ack) and ack["hidden"] is False and ack["pe"] == "auto" and ack["label"] != "", str(ack))
    # THE × IS A THUMB TARGET (v294 audit, section 3; owner: keep the pill
    # floating). It was 22px on the near edge of the canvas, so a miss by a few
    # pixels drew a stroke — which schedules a save, which re-shows the warning
    # being closed. The box is 44px each way now, and a tap 16px above the
    # glyph's centre — outside the old box, inside the new — acknowledges the
    # pill and draws nothing.
    xbox = pg2.evaluate("() => { const r = document.getElementById('autosaveStatusDismiss').getBoundingClientRect(); return { w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; }")
    check("the × is at least 44px each way", xbox["w"] >= 44 and xbox["h"] >= 44, f"{round(xbox['w'])}x{round(xbox['h'])}")
    strokes_before = pg2.evaluate("() => frames[idx].strokes.length")
    pg2.mouse.click(xbox["cx"], xbox["cy"] - 16)
    pg2.wait_for_timeout(500)
    ackc, ackwhy = True, ""
    check("a near miss on the × acknowledges the pill instead of drawing on the canvas",
          pg2.evaluate("() => document.getElementById('autosaveStatus').hidden") is True
          and pg2.evaluate("() => frames[idx].strokes.length") == strokes_before,
          f"hidden={pg2.evaluate('() => document.getElementById(\'autosaveStatus\').hidden')} strokes {strokes_before} -> {pg2.evaluate('() => frames[idx].strokes.length')}")
    check("acknowledging hides the pill", pg2.evaluate("() => document.getElementById('autosaveStatus').hidden") is True, ackwhy)
    scribble(pg2, box2, 7.5); pg2.wait_for_timeout(1600)
    check("...and it stays quiet on the next save",
          pg2.evaluate("() => document.getElementById('autosaveStatus').hidden") is True,
          "an acknowledged warning that comes back on the next stroke was never acknowledged")

    print("\nFLIP — re-add card in the music drawer after reload (store still broken)")
    pg2.reload(wait_until="load"); pg2.wait_for_timeout(1500)
    snap_pending = pg2.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
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
    # The control is the pill's TEXT, not the pill. A × sits beside it,
    # and a button inside a role=button is invalid nesting; the status stays a
    # status and holds two controls.
    pill = pg2.evaluate("""() => { const el = document.getElementById('autosaveStatus');
        const t = document.getElementById('autosaveStatusText');
        const cs = getComputedStyle(el);
        return { text: t.textContent,
                 actionable: el.classList.contains('actionable'),
                 role: t.getAttribute('role'), tab: t.getAttribute('tabindex'),
                 pe: cs.pointerEvents,
                 // Painted and on top, not merely laid out (a rect is not a paint).
                 readd: (() => { const b = document.getElementById('autosaveStatusReadd'); if (!b || b.hidden || b.textContent !== 'Re-add') return false; const r = b.getBoundingClientRect(); if (r.width < 30) return false; const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); let op = 1; for (let a = b; a; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity); return !!hit && (hit === b || b.contains(hit)) && op > 0.5; })() }; }""")
    # v317: the way out is a button that SAYS Re-add, beside the ×. The words
    # alone were tappable and looked like a label; the owner tapped the ×.
    check("the amber pill NAMES the way out, on a button that says Re-add",
          pill["text"] == "Media missing" and pill["readd"] is True,
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
    clicked, why = try_click(pg2, "#autosaveStatusText")
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
          "state the report was as a warning with no way out")
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

    print("\nFLIP — the pill carries its own Dismiss (v294)")
    # From a phone: "the re-add media button doesn't go away
    # unless I click it or go to the drawer and x out." The card's Dismiss is
    # the only thing that ended the amber, two taps away. The pill has a × of
    # its own that does the same thing. The pending record is put back the
    # honest way: the draft as it was BEFORE the card was dismissed, restored
    # into storage and reloaded, so the × acts on a real restore.
    # NOT a reload: pagehide flushes the CURRENT draft (no record) over whatever
    # storage holds, so a snapshot written before a reload is gone by the time
    # the page comes back. Close the editor first, seed from a same-origin page
    # that runs no editor, then open a fresh one.
    pg2.goto(BASE + "/static/lib/drawers.js", wait_until="load")   # the editor's pagehide flush has now run, on the OLD state
    pg2.evaluate("(snap) => { localStorage.clear(); for (const [k, v] of Object.entries(snap)) localStorage.setItem(k, v); }", snap_pending)
    pg2.goto(BASE+"/flip", wait_until="load"); pg2.wait_for_timeout(1500)
    s = pg2.evaluate(STATE)
    check("amber again on the restore", "partial" in s["cls"], f"{s['text']!r}")
    xbtn = pg2.evaluate("""() => { const x = document.getElementById('autosaveStatusDismiss');
        if (!x) return null; const r = x.getBoundingClientRect();
        return { hidden: x.hidden, w: Math.round(r.width), h: Math.round(r.height), label: x.getAttribute('aria-label') || '' }; }""")
    check("the pill carries a Dismiss of its own, with a name",
          bool(xbtn) and xbtn["hidden"] is False and xbtn["w"] > 0 and xbtn["h"] > 0 and xbtn["label"] != "",
          str(xbtn))
    xclicked, xwhy = try_click(pg2, "#autosaveStatusDismiss")
    check("...that takes a tap", xclicked, xwhy)
    pg2.wait_for_timeout(1600)
    s = pg2.evaluate(STATE)
    check("the pill's Dismiss ENDS the amber without a drawer",
          "partial" not in s["cls"] and pg2.evaluate("() => _flipDrawerCtl.current()") is None,
          f"{s['text']!r} drawer={pg2.evaluate('() => _flipDrawerCtl.current()')}")
    check("...and the record is gone, so the card is too",
          pg2.evaluate("() => pendingMusicMeta === null && document.getElementById('musicPending').hidden"),
          "the × must do what the card's Dismiss does, not merely hide the pill")

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

    print("\nPAD — a pending record is the same amber, the same route, the same way out (v294)")
    # The Pad reported GREEN "Saved" with a re-add card waiting in a drawer
    # nothing pointed at: hasMusic counted the pending record but
    # mediaDurabilityOk() had nothing failed. Same contract as Flip's now, and
    # driven the same way — store broken, track attached, reload, restore.
    pg3 = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    errs3 = []; pg3.on("pageerror", lambda e: errs3.append(str(e)))
    pg3.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pg3.goto(BASE+"/skribl-pad", wait_until="load"); pg3.wait_for_timeout(1200)
    pg3.evaluate("() => localStorage.clear()")
    pbox3 = pg3.locator("canvas").first.bounding_box()
    pg3.mouse.move(pbox3["x"]+120, pbox3["y"]+120); pg3.mouse.down()
    for i in range(60): pg3.mouse.move(pbox3["x"]+120+i*3, pbox3["y"]+120+math.sin(i/4)*40)
    pg3.mouse.up(); pg3.wait_for_timeout(1800)
    pg3.set_input_files("#musicInput", WAV); pg3.wait_for_timeout(4500)
    s = pg3.evaluate(STATE)
    check("Pad: amber with the track loaded and no store to hold it", "partial" in s["cls"], f"{s['text']!r}")
    noroute3 = pg3.evaluate("""() => { const el = document.getElementById('autosaveStatus'), t = document.getElementById('autosaveStatusText');
        return { text: t.textContent, actionable: el.classList.contains('actionable'), role: t.getAttribute('role') }; }""")
    check("Pad: amber with nothing to re-add does NOT pretend to be a route",
          noroute3["actionable"] is False and noroute3["role"] is None and "re-add" not in noroute3["text"].lower(),
          str(noroute3))
    ack3 = pg3.evaluate("""() => { const x = document.getElementById('autosaveStatusDismiss');
        return x ? { hidden: x.hidden, pe: getComputedStyle(x).pointerEvents } : null; }""")
    check("Pad: the × is offered on this amber too", bool(ack3) and ack3["hidden"] is False and ack3["pe"] == "auto", str(ack3))
    xbox3 = pg3.evaluate("() => { const r = document.getElementById('autosaveStatusDismiss').getBoundingClientRect(); return { w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; }")
    check("Pad: the × is at least 44px each way", xbox3["w"] >= 44 and xbox3["h"] >= 44, f"{round(xbox3['w'])}x{round(xbox3['h'])}")
    strokes3 = pg3.evaluate("() => strokes.length")
    pg3.mouse.click(xbox3["cx"], xbox3["cy"] - 16); pg3.wait_for_timeout(500)
    check("Pad: a near miss on the × acknowledges the pill instead of drawing on the canvas",
          pg3.evaluate("() => document.getElementById('autosaveStatus').hidden") is True and pg3.evaluate("() => strokes.length") == strokes3,
          f"hidden={pg3.evaluate('() => document.getElementById(\'autosaveStatus\').hidden')} strokes {strokes3} -> {pg3.evaluate('() => strokes.length')}")
    check("Pad: acknowledging hides the pill", pg3.evaluate("() => document.getElementById('autosaveStatus').hidden") is True, "")
    pg3.mouse.move(pbox3["x"]+300, pbox3["y"]+200); pg3.mouse.down()
    for i in range(40): pg3.mouse.move(pbox3["x"]+300+i*3, pbox3["y"]+200+math.cos(i/4)*30)
    pg3.mouse.up(); pg3.wait_for_timeout(1800)
    check("Pad: ...and it stays quiet on the next save",
          pg3.evaluate("() => document.getElementById('autosaveStatus').hidden") is True,
          "an acknowledged warning that comes back on the next stroke was never acknowledged")
    # ON A PHONE, where the pill is lifted above the tool row and the only
    # thing under a near miss is the canvas (the owner's complaint, verbatim:
    # "when you push it you are over the canvas and likely to draw on canvas").
    # 390x664 is what an iPhone's Safari gives the page once its own chrome is
    # on screen; at that height the canvas reaches the pill. (At 393x852 it
    # stops 9px short, and this pin would be vacuous.)
    pgm = b.new_page(viewport={"width": 390, "height": 664}, color_scheme="dark")
    pgm.add_init_script("Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pgm.goto(BASE+"/skribl-pad", wait_until="load"); pgm.wait_for_timeout(1200)
    pgm.evaluate("() => { localStorage.clear(); window.SkriblHints && window.SkriblHints.hide(); }")
    # The 9:16 canvas a portrait phone actually shows (from a screenshot):
    # it reaches the bottom of the screen, which is where the pill lives.
    pgm.evaluate("() => { const b = document.querySelector('#canvasSeg [data-size=\"tall\"]'); if (b) b.click(); }")
    pgm.wait_for_timeout(600)
    mbox = pgm.locator("canvas").first.bounding_box()
    pgm.mouse.move(mbox["x"]+80, mbox["y"]+120); pgm.mouse.down()
    for i in range(40): pgm.mouse.move(mbox["x"]+80+i*3, mbox["y"]+120+math.sin(i/4)*30)
    pgm.mouse.up(); pgm.wait_for_timeout(1800)
    pgm.set_input_files("#musicInput", WAV); pgm.wait_for_timeout(4500)
    sm = pgm.evaluate(STATE)
    check("Pad phone: amber, with the pill over the canvas", "partial" in sm["cls"] and pgm.evaluate("""() => { const p = document.getElementById('autosaveStatus').getBoundingClientRect(), c = document.querySelector('canvas').getBoundingClientRect();
        return !(p.right <= c.left || p.left >= c.right || p.bottom <= c.top || p.top >= c.bottom); }"""), f"{sm['text']!r}")
    xm = pgm.evaluate("() => { const r = document.getElementById('autosaveStatusDismiss').getBoundingClientRect(); return { cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; }")
    strokes_m = pgm.evaluate("() => strokes.length")
    pgm.mouse.click(xm["cx"], xm["cy"] - 16); pgm.wait_for_timeout(600)
    check("Pad phone: a near miss on the × acknowledges the pill and draws NOTHING",
          pgm.evaluate("() => document.getElementById('autosaveStatus').hidden") is True and pgm.evaluate("() => strokes.length") == strokes_m,
          f"hidden={pgm.evaluate('() => document.getElementById(\'autosaveStatus\').hidden')} strokes {strokes_m} -> {pgm.evaluate('() => strokes.length')}")
    pgm.close()
    pg3.reload(wait_until="load"); pg3.wait_for_timeout(2700)
    check("Pad: the draft is applied at boot, with no banner (v294)",
          pg3.evaluate("() => { const b = document.getElementById('restoreBanner'); return (!b || b.hidden) && strokes.length > 0; }"),
          "a banner, or an empty canvas, on the return visit")
    s = pg3.evaluate(STATE)
    check("Pad: amber immediately on restore", "partial" in s["cls"], f"{s['text']!r} cls={s['cls']!r}")
    pill3 = pg3.evaluate("""() => { const el = document.getElementById('autosaveStatus'), t = document.getElementById('autosaveStatusText');
        return { text: t.textContent, role: t.getAttribute('role'), tab: t.getAttribute('tabindex'),
                 pe: getComputedStyle(el).pointerEvents }; }""")
    readd3 = pg3.evaluate("() => " + """(() => { const b = document.getElementById('autosaveStatusReadd'); if (!b || b.hidden || b.textContent !== 'Re-add') return false; const r = b.getBoundingClientRect(); if (r.width < 30) return false; const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); let op = 1; for (let a = b; a; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity); return !!hit && (hit === b || b.contains(hit)) && op > 0.5; })()""")
    check("Pad: the amber pill NAMES the way out, on a button that says Re-add",
          pill3["text"] == "Media missing" and readd3 is True, f"{pill3['text']!r} readd={readd3}")
    check("Pad: ...and is a real control that receives taps",
          pill3["role"] == "button" and pill3["tab"] == "0" and pill3["pe"] == "auto", str(pill3))
    pc, pwhy = try_click(pg3, "#autosaveStatusText")
    pg3.wait_for_timeout(400)
    opened3 = pg3.evaluate("""() => { const c = document.getElementById('musicPending'); const r = c.getBoundingClientRect();
        return { drawer: _padDrawerCtl.isOpen('music'), cardHidden: c.hidden, w: Math.round(r.width), h: Math.round(r.height) }; }""")
    check("Pad: tapping the pill opens the drawer holding the missing file, with a card of real size",
          pc and opened3["drawer"] is True and opened3["cardHidden"] is False and opened3["w"] > 100 and opened3["h"] > 20,
          f"{pwhy} {json.dumps(opened3)}")
    pg3.evaluate("() => _padDrawerCtl.open(null)"); pg3.wait_for_timeout(300)
    xc, xwhy3 = try_click(pg3, "#autosaveStatusDismiss")
    # AT ONCE (v317): the owner saw a lag before the pill went -- it waited for
    # the save Dismiss schedules (a 1.2 s debounce plus the storage round trip).
    gone = pg3.evaluate("() => new Promise(r => setTimeout(() => r(!document.getElementById('autosaveStatus').classList.contains('show')), 150))")
    check("Pad: the pill goes the moment Dismiss is tapped, not after the save it schedules",
          gone is True, f"still showing 150 ms after the tap: {not gone}")
    pg3.wait_for_timeout(1600)
    s = pg3.evaluate(STATE)
    check("Pad: the pill's Dismiss ENDS the amber without a drawer",
          xc and "partial" not in s["cls"] and pg3.evaluate("() => _padDrawerCtl.current()") is None,
          f"{xwhy3} {s['text']!r}")
    check("Pad: ...and the record is gone, so the card is too",
          pg3.evaluate("() => pendingMusicMeta === null && document.getElementById('musicPending').hidden"),
          "the × must do what the card's Dismiss does")
    check("Pad: no uncaught page errors", not errs3, "; ".join(errs3[:3]))
    pg3.close()

    print("\nPAD — the store write is retried, not decided once (v294)")
    # The Pad wrote the bytes to IndexedDB exactly once, at attach time, and
    # carried that verdict for the whole session: one rejected write was a
    # permanent amber over media that was loaded and in front of the user.
    # Flip re-spills the whole payload on every save and heals by itself.
    def pad_page(hook):
        pg = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
        pg.goto(BASE+"/skribl-pad", wait_until="load"); pg.wait_for_timeout(1200)
        pg.evaluate("() => localStorage.clear()")
        pg.evaluate("""(hook) => { const orig = SkriblDraftStore.put.bind(SkriblDraftStore); window.__puts = 0;
            SkriblDraftStore.put = (k, v) => { window.__puts++; return (window.__puts === 1) ? hook() : orig(k, v); }; }""".replace("hook()", hook))
        box = pg.locator("canvas").first.bounding_box()
        return pg, box
    def stroke(pg, box, y):
        pg.mouse.move(box["x"]+120, box["y"]+y); pg.mouse.down()
        for i in range(50): pg.mouse.move(box["x"]+120+i*3, box["y"]+y+math.sin(i/4)*30)
        pg.mouse.up()
    pg4, box4 = pad_page("Promise.reject(new Error('transient'))")
    stroke(pg4, box4, 120); pg4.wait_for_timeout(1800)
    pg4.set_input_files("#musicInput", WAV); pg4.wait_for_timeout(500)   # before the attach's own save retries
    s = pg4.evaluate(STATE)
    check("Pad: amber after the store refuses the bytes once", "partial" in s["cls"], f"{s['text']!r}")
    r4c, r4why = try_click(pg4, "#autosaveStatusDismiss"); pg4.wait_for_timeout(500)
    check("Pad: acknowledged", r4c and pg4.evaluate("() => document.getElementById('autosaveStatus').hidden") is True, r4why)
    stroke(pg4, box4, 260); pg4.wait_for_timeout(2500)
    s = pg4.evaluate(STATE)
    puts = pg4.evaluate("() => window.__puts")
    check("Pad: the next save retries the write, the bytes land, and the pill speaks again — green",
          puts >= 2 and "partial" not in s["cls"] and pg4.evaluate("() => document.getElementById('autosaveStatus').hidden") is False,
          f"puts={puts} {s['text']!r} hidden={pg4.evaluate('() => document.getElementById(\'autosaveStatus\').hidden')}")
    ok4 = pg4.evaluate("""() => window.SkriblDraftStore.get('pad:music').then(r => !!(r && r.blob && r.blob.size > 0)).catch(() => false)""")
    check("Pad: ...because the retry stored them", ok4 is True)
    pg4.close()

    pg5, box5 = pad_page("new Promise(() => {})")
    stroke(pg5, box5, 120); pg5.wait_for_timeout(1800)
    pg5.set_input_files("#musicInput", WAV); pg5.wait_for_timeout(2500)
    s = pg5.evaluate(STATE)
    check("Pad: amber while a write that never settles is in flight", "partial" in s["cls"], f"{s['text']!r}")
    stroke(pg5, box5, 260); pg5.wait_for_timeout(2500)
    check("Pad: a save inside the deadline does not pile a second write on a hung one",
          pg5.evaluate("() => window.__puts") == 1, f"puts={pg5.evaluate('() => window.__puts')}")
    pg5.wait_for_timeout(9000)   # past the 12s deadline in total
    stroke(pg5, box5, 400); pg5.wait_for_timeout(2500)
    s = pg5.evaluate(STATE)
    check("Pad: past the deadline the hung write is given up, retried on the next save, and the amber ends",
          pg5.evaluate("() => window.__puts") >= 2 and "partial" not in s["cls"],
          f"puts={pg5.evaluate('() => window.__puts')} {s['text']!r}")
    pg5.close()

    print("\nPAD — a refused store write names its reason where a phone can carry it (v294)")
    # From a phone, twice: "Saved without media" with the media loaded,
    # then after a reload "Media missing — tap to re-add". The bytes never
    # reached the store, and the code swallowed the reason: a silent catch on
    # the write, a silent miss on the restore. There is no console on a phone;
    # lib/report.js is the channel that exists, and it carries console.error
    # lines. So the reason is logged there, and the report states the store.
    pg9, box9 = pad_page("Promise.reject(Object.assign(new Error('boom-store'), { name: 'QuotaExceededError' }))")
    stroke(pg9, box9, 120); pg9.wait_for_timeout(600)
    pg9.set_input_files("#musicInput", WAV); pg9.wait_for_timeout(600)   # before the attach's save retries
    rep = pg9.evaluate("() => SkriblReport.collect()")
    check("Pad: the report names the refused write and its reason",
          "QuotaExceededError" in rep and "boom-store" in rep, rep[-400:])
    check("Pad: ...and states the media store's slots",
          "Media store:" in rep and "music failed" in rep, rep[-400:])
    pg9.close()

    print("\nTHE BYTES GO WHEN THE MEDIA GOES (v294 audit, PR 6)")
    # AUDIT, finding 7: Flip's store record holds the WHOLE payload, frames and
    # media bytes together, and nothing ever deleted it. Remove the track, or
    # clear everything, and the lite record forgot it while the bytes sat in
    # IndexedDB until the next save that happened to have media. Finding 8: the
    # Pad deletes the bytes the moment Remove is tapped but rewrites the draft
    # 1.2 s later, so a tab that dies in that window comes back offering a
    # re-add card for a track the user removed.
    fp6 = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    fp6.goto(BASE+"/flip", wait_until="load"); fp6.wait_for_timeout(700)
    fp6.evaluate("() => { localStorage.clear(); window.SkriblHints && window.SkriblHints.hide(); }")
    fbox6 = fp6.locator("#pad").bounding_box()
    scribble(fp6, fbox6, 0.0)
    fp6.set_input_files("#musicInput", WAV); fp6.wait_for_timeout(5000)
    stored6 = fp6.evaluate("() => SkriblDraftStore.get('flip:draft').then(r => !!(r && r.json)).catch(() => false)")
    check("Flip: the spill put the payload in the store", stored6 is True)
    fp6.evaluate("() => removeMusic()"); fp6.wait_for_timeout(2000)
    left6 = fp6.evaluate("() => SkriblDraftStore.get('flip:draft').then(r => !!(r && r.json)).catch(() => false)")
    check("Flip: removing the last media deletes the stored payload with it",
          left6 is False,
          "the bytes outlive the media that owned them — and the frames are in there twice over")
    fp6.close()

    pd6 = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pd6.goto(BASE+"/skribl-pad", wait_until="load"); pd6.wait_for_timeout(1200)
    pd6.evaluate("() => localStorage.clear()")
    pbox6 = pd6.locator("canvas").first.bounding_box()
    pd6.mouse.move(pbox6["x"]+120, pbox6["y"]+120); pd6.mouse.down()
    for i in range(50): pd6.mouse.move(pbox6["x"]+120+i*3, pbox6["y"]+120+math.sin(i/4)*30)
    pd6.mouse.up(); pd6.wait_for_timeout(1800)
    pd6.set_input_files("#musicInput", WAV); pd6.wait_for_timeout(4500)
    # Remove, then read the DRAFT immediately — inside the 1.2 s debounce, which
    # is the window a dying tab falls into. Two clicks: the bin asks first (the
    # first arms it, lib/pendingcards.js), and the second is the Remove.
    pd6.evaluate("() => { const b = document.getElementById('musicRemove'); b.click(); b.click(); }")
    pd6.wait_for_timeout(150)
    draft6 = pd6.evaluate("() => { const r = localStorage.getItem('skribl_autosave_v1'); return r ? !!(JSON.parse(r).musicMeta && JSON.parse(r).musicMeta.name) : null; }")
    check("Pad: Remove writes the draft before it deletes the bytes",
          draft6 is False,
          "the record still names a track whose bytes are already gone: a tab that "
          "dies in the debounce window comes back offering a re-add card for a file "
          "the user removed")
    pd6.close()

    print("\nTHE DISMISS IS A BUTTON YOU CAN SEE (v294; owner: \"should the button be big so people don't stress\")")
    # An invisible 44px target stopped the accidental stroke and did nothing for
    # the aiming: nothing on screen said the button was bigger than its 12px
    # glyph. The puck is the button as far as the eye is concerned — drawn at
    # rest, filled when pressed — and the 44px box around it is the forgiveness
    # margin. Read from ::before, which is where the puck lives; the button's
    # own background must stay transparent or the pressed state overhangs the
    # pill again (the previous bug, owner: "when I push it it shows big").
    SEEN = r"""() => { const x = document.getElementById('autosaveStatusDismiss');
        const p = document.getElementById('autosaveStatus');
        const b = getComputedStyle(x, '::before'), s = getComputedStyle(x);
        const px = v => Math.round(parseFloat(v) || 0);
        const clear = c => !c || c === 'transparent' || /rgba\(\s*\d+,\s*\d+,\s*\d+,\s*0\s*\)/.test(c);
        return { pill: Math.round(p.getBoundingClientRect().height),
                 target: Math.round(x.getBoundingClientRect().height),
                 puck: px(b.width), puckFill: b.backgroundColor, puckBorder: px(b.borderTopWidth),
                 boxFill: s.backgroundColor, restVisible: !clear(b.backgroundColor) || px(b.borderTopWidth) > 0 }; }"""
    for _label, _vp, _touch in (("phone", {"width": 390, "height": 664}, True),
                                ("desktop", {"width": 1280, "height": 900}, False)):
        _ctx = b.new_context(viewport=_vp, color_scheme="dark", has_touch=_touch, is_mobile=_touch)
        _p = _ctx.new_page()
        _p.goto(BASE + "/skribl-pad", wait_until="load"); _p.wait_for_timeout(1200)
        _p.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); SkriblAutosavePill.show('saved-no-media'); }")
        _p.wait_for_timeout(500)
        _s = _p.evaluate(SEEN)
        check(f"{_label}: the × is drawn at rest, not only when touched",
              _s["restVisible"], f"puck fill {_s['puckFill']} border {_s['puckBorder']}px — "
              "an affordance nobody can see is an affordance nobody aims at")
        check(f"{_label}: ...and the drawn button sits INSIDE the pill",
              0 < _s["puck"] <= _s["pill"], f"puck {_s['puck']}px in a {_s['pill']}px pill")
        check(f"{_label}: ...while the 44px target stays the forgiveness margin, unseen",
              _s["target"] >= 44 and _s["boxFill"] in ("rgba(0, 0, 0, 0)", "transparent"),
              f"target {_s['target']}px, box fill {_s['boxFill']} — a filled 44px box overhangs a 28px pill, "
              "which is what made a tap look like the button growing")
        if _touch:
            # On a finger the pill carries two actions on the route amber: the
            # words re-add, the × dismisses. Both have to be thumb-sized.
            check("phone: the pill itself is thumb-sized, so the words are a target too",
                  _s["pill"] >= 44, f"{_s['pill']}px tall at 13px type")
            check("phone: ...and the drawn button is at least 28px",
                  _s["puck"] >= 28, f"{_s['puck']}px")
        _ctx.close()

    print("\nPAD — media is a draft; a restore reads the store, and speaks only when it misses (v294 audit, PR 1)")
    # AUDIT, finding 1: a photo or a track with no strokes was "nothing
    # meaningful" — the draft was never written, the banner never offered, and
    # the bytes already in IndexedDB were orphaned. Finding 2: a restore replayed
    # the attach pipeline, whose first step wrote the same bytes to the store
    # again (the write that hangs on a phone). Finding 3: the route amber was
    # shown at the moment of restore, before the store had been asked — a false
    # alarm flashed on every healthy restore.
    pg6, box6 = pad_page("orig(k, v)")   # a working store; the hook counts puts
    pg6.set_input_files("#musicInput", WAV); pg6.wait_for_timeout(4500)
    check("Pad: a track with no strokes is saved as a draft",
          pg6.evaluate("() => { const r = localStorage.getItem('skribl_autosave_v1'); return !!(r && JSON.parse(r).musicMeta && JSON.parse(r).musicMeta.name); }"),
          "the draft slot is empty: media alone was 'nothing meaningful' and the bytes in the store are orphans")
    pg6.reload(wait_until="load"); pg6.wait_for_timeout(6000)
    check("Pad: ...and back at boot, bytes and all, for a media-only draft",
          pg6.evaluate("() => !!(audioEl && audioEl._fileName === 'boombap.wav')"),
          "the track did not come back from the store on the return visit")
    pg6.close()

    # Findings 2 and 3, on a draft that restores today (a stroke plus the track).
    pg7, box7 = pad_page("orig(k, v)")
    stroke(pg7, box7, 120); pg7.wait_for_timeout(1800)
    pg7.set_input_files("#musicInput", WAV); pg7.wait_for_timeout(4500)
    # The restore runs at boot now, so the instruments go in BEFORE the page
    # scripts: a setter trap catches the store the moment lib/draftstore.js
    # defines it, and the pill is sampled from the first frame.
    pg7.add_init_script("""(() => { let real;
        Object.defineProperty(window, 'SkriblDraftStore', { configurable: true, get: () => real,
          set: (v) => { const orig = v.put.bind(v); window.__puts = 0; v.put = (k, val) => { window.__puts++; return orig(k, val); };
                        // A SLOW STORE, deterministically (v315): the healthy-restore row below went
                        // red only when the machine was loaded -- the store answered after the 200 ms
                        // post-restore autosave, which then called the track missing. 800 ms makes
                        // that the case every run instead of the unlucky one.
                        const g = v.get.bind(v); v.get = (k) => new Promise(r => setTimeout(() => r(g(k)), 800));
                        real = v; } });
        window.__pillTexts = [];
        setInterval(() => { const el = document.getElementById('autosaveStatus'); if (el && !el.hidden) window.__pillTexts.push(document.getElementById('autosaveStatusText').textContent); }, 100); })();""")
    pg7.reload(wait_until="load"); pg7.wait_for_timeout(6000)
    check("Pad: the bytes are back from the store at boot",
          pg7.evaluate("() => !!(audioEl && audioEl._fileName === 'boombap.wav')"), "no track on the return visit")
    check("Pad: ...without writing them to the store again",
          pg7.evaluate("() => window.__puts") == 0, f"puts={pg7.evaluate('() => window.__puts')} — the attach pipeline's first step is the write that hangs on a phone")
    check("Pad: ...and the slot reads durable at once, so nothing is amber",
          pg7.evaluate("() => mediaDraft.music") == "durable" and "partial" not in pg7.evaluate(STATE)["cls"],
          f"{pg7.evaluate('() => mediaDraft.music')} {pg7.evaluate(STATE)['text']!r}")
    texts = pg7.evaluate("() => window.__pillTexts")
    check("Pad: a healthy restore never says the media is missing",
          not any(t.startswith("Media missing") for t in texts), f"pill read {sorted(set(texts))} during the restore")
    # v317, THE GAP AFTER THE STORE ANSWERS: the owner's iPhone flashed "Media
    # missing" while a large photo that HAD come back was still decoding. The
    # state that moment is reproduced exactly: the draft names a photo, the
    # restore has stood down, the File is in hand, the image is not attached yet.
    gap = pg7.evaluate("""() => {
        const keep = { meta: pendingPhotoMeta, file: _mediaFile.photo, name: photoBgImg && photoBgImg._fileName, r: _restoring.photo };
        pendingPhotoMeta = { name: 'map.png' }; _restoring.photo = false;
        const keepAt = _mediaAt.photo;
        _mediaFile.photo = new File(['x'], 'map.png', { type: 'image/png' });
        _mediaAt.photo = Date.now();
        if (photoBgImg) photoBgImg._fileName = null;
        const loading = _pendingPhotoLost();
        // A decode that failed: the File never left, and the window has closed.
        _mediaAt.photo = Date.now() - 20000;
        const stuck = _pendingPhotoLost();
        _mediaFile.photo = null;
        const gone = _pendingPhotoLost();
        pendingPhotoMeta = keep.meta; _mediaFile.photo = keep.file; _restoring.photo = keep.r;
        _mediaAt.photo = keepAt;
        if (photoBgImg) photoBgImg._fileName = keep.name;
        return { loading, stuck, gone }; }""")
    check("Pad: a file in hand and still decoding is loading, not missing (and one truly absent still is)",
          gap["loading"] is False and gap["gone"] is True, str(gap))
    check("Pad: ...but only for the decode window -- a file that never lands is missing after it",
          gap["stuck"] is True, str(gap))
    pg7.close()

    print("\nPAD — a restored photo that is still decoding stays in the draft, and one that never lands is missing again (v317 review)")
    # The re-apply listener took the draft's photo settings off the moment the
    # restored file was handed over; an autosave before the image was on the
    # canvas wrote no photo. Driven with a file that cannot decode, which is
    # also the other half: it must come back as pending, not vanish.
    pgR = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pgR.goto(BASE+"/skribl-pad", wait_until="load"); pgR.wait_for_timeout(1200)
    pgR.evaluate("() => localStorage.clear()")
    pbR = pgR.locator("canvas").first.bounding_box()
    pgR.mouse.move(pbR["x"]+120, pbR["y"]+120); pgR.mouse.down()
    for i in range(30): pgR.mouse.move(pbR["x"]+120+i*4, pbR["y"]+120+math.sin(i/4)*30)
    pgR.mouse.up(); pgR.wait_for_timeout(1500)
    flight = pgR.evaluate("""() => {
        pendingPhotoMeta = { name: 'broken.png', fit: 'contain', opacity: 0.6 };
        const input = document.getElementById('photoInput');
        const dt = new DataTransfer();
        dt.items.add(new File([new Uint8Array([1, 2, 3, 4])], 'broken.png', { type: 'image/png' }));
        input.files = dt.files;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        const meta = serializeAutosave().photoMeta;
        return { name: meta && meta.name, fit: meta && meta.fit, pending: !!pendingPhotoMeta }; }""")
    check("Pad: an autosave while a restored photo decodes still names the photo and its settings",
          flight["name"] == "broken.png" and flight["fit"] == "contain", str(flight))
    pgR.wait_for_timeout(15600)
    after = pgR.evaluate("""() => ({ pending: pendingPhotoMeta && pendingPhotoMeta.name,
        card: !document.getElementById('photoPending').hidden,
        text: document.getElementById('autosaveStatusText').textContent,
        shown: !document.getElementById('autosaveStatus').hidden,
        saved: serializeAutosave().photoMeta && serializeAutosave().photoMeta.name })""")
    check("Pad: ...and a photo that never lands is missing again once the window closes: pending, its card, the pill says so",
          after["pending"] == "broken.png" and after["card"] and after["shown"] and "missing" in after["text"].lower()
          and after["saved"] == "broken.png", str(after))
    # The × on "Media missing" dismisses what is MISSING: a track still
    # decoding beside a lost photo keeps its loop and crossfade (it lost them).
    dism = pgR.evaluate("""() => {
        pendingPhotoMeta = { name: 'gone.png' };
        pendingMusicMeta = { name: 'loop.wav', trimStart: 1, trimEnd: 3, crossfadeMs: 40 };
        _mediaFile.music = new File(['x'], 'loop.wav'); _mediaAt.music = Date.now();
        showAutosaveStatus('saved-no-media');
        return new Promise(r => requestAnimationFrame(() => {
          document.getElementById('autosaveStatusDismiss').click();
          r({ photo: pendingPhotoMeta, music: pendingMusicMeta && pendingMusicMeta.trimEnd });
        }));
    }""")
    check("Pad: dismissing 'Media missing' clears the missing photo and keeps the track still on its way",
          dism["photo"] is None and dism["music"] == 3, str(dism))
    pgR.close()

    print("\nPAD — an opened draft is the only document: the old session's media book-keeping goes (v317 review)")
    # loadSkribl reset the canvas and the media on screen, not the draft's
    # book-keeping, so a reload could re-attach the PREVIOUS photo or ask about
    # a file the opened draft never had.
    pgO = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pgO.goto(BASE+"/skribl-pad", wait_until="load"); pgO.wait_for_timeout(1200)
    pgO.evaluate("() => localStorage.clear()")
    pbO = pgO.locator("canvas").first.bounding_box()
    pgO.mouse.move(pbO["x"]+100, pbO["y"]+100); pgO.mouse.down()
    for i in range(25): pgO.mouse.move(pbO["x"]+100+i*4, pbO["y"]+100+math.sin(i/4)*25)
    pgO.mouse.up(); pgO.wait_for_timeout(800)
    PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    opened = pgO.evaluate("""async (png) => {
        // The session before: a remembered photo, its bytes in the store.
        await SkriblDraftStore.put('pad:photo', { blob: new Blob(['old']), name: 'image.jpg', type: 'image/jpeg' });
        pendingPhotoMeta = { name: 'image.jpg' }; mediaDraft.photo = 'durable';
        const d = serializeSkribl(); d.photo = { data: png, name: 'new.png', fit: 'contain' }; (d.frames || []).forEach(f => { f.photo = d.photo; });
        loadSkribl(d);
        await new Promise(r => setTimeout(r, 1500));
        const rec = await SkriblDraftStore.get('pad:photo');
        const withPhoto = { pending: pendingPhotoMeta, stored: rec && rec.name, slot: mediaDraft.photo };
        const d2 = serializeSkribl(); delete d2.photo; (d2.frames || []).forEach(f => { delete f.photo; });
        pendingPhotoMeta = { name: 'image.jpg' };
        loadSkribl(d2);
        await new Promise(r => setTimeout(r, 800));
        const rec2 = await SkriblDraftStore.get('pad:photo');
        return { withPhoto, without: { pending: pendingPhotoMeta, stored: rec2 ? rec2.name : null } };
    }""", PNG)
    check("Pad: opening a draft with a photo makes ITS photo the stored copy, and forgets the old one",
          opened["withPhoto"]["pending"] is None and opened["withPhoto"]["stored"] == "new.png"
          and opened["withPhoto"]["slot"] == "durable", str(opened))
    check("Pad: opening a draft with no photo drops the old stored photo and asks about nothing",
          opened["without"]["pending"] is None and opened["without"]["stored"] is None, str(opened))
    # A store read still out when a document opens must not land the previous
    # session's file on it (the read is late; the slot has moved on).
    late = pgO.evaluate("""async () => {
        const S = SkriblDraftStore, get = S.get;
        let release; const gate = new Promise(r => release = r);
        S.get = (k) => k === 'pad:photo' ? gate.then(() => ({ blob: new Blob(['x']), name: 'late.png', type: 'image/png' })) : get(k);
        let changed = 0; const inp = document.getElementById('photoInput');
        const count = () => changed++; inp.addEventListener('change', count, true);
        reAddMediaFromStore('photo', 'photoInput', { name: 'late.png' });
        padAdoptLoadedMedia({});            // a document opened meanwhile
        release(); await new Promise(r => setTimeout(r, 300));
        S.get = get; inp.removeEventListener('change', count, true);
        return { changed, file: _mediaFile.photo && _mediaFile.photo.name, restoring: _restoring.photo };
    }""")
    check("Pad: a store answer that arrives after a document opened is ignored, not attached",
          late["changed"] == 0 and late["file"] is None and late["restoring"] is False, str(late))
    # New Skribl carries nothing: a pending record, a photo in flight.
    fresh_ = pgO.evaluate("""() => {
        pendingPhotoMeta = { name: 'old.png' }; _inFlight.photo = { name: 'flying.png' };
        resetAll();
        return { pending: pendingPhotoMeta, flight: _inFlight.photo };
    }""")
    check("Pad: New Skribl drops a pending photo and one still in flight (no 'Media missing' later about a discarded Skribl)",
          fresh_["pending"] is None and fresh_["flight"] is None, str(fresh_))
    # The player keeps no draft: viewing a post must never touch stored media.
    guard = pgO.evaluate("""async () => {
        await SkriblDraftStore.put('pad:photo', { blob: new Blob(['keep']), name: 'keep.png', type: 'image/png' });
        document.body.classList.add('player-mode');
        padAdoptLoadedMedia({});
        document.body.classList.remove('player-mode');
        await new Promise(r => setTimeout(r, 300));
        const rec = await SkriblDraftStore.get('pad:photo');
        return rec && rec.name;
    }""")
    check("Pad: in player mode an opened document touches no stored media", guard == "keep.png", str(guard))
    pgO.close()

    print("\nPAD — a restored photo keeps its adjustments however long the decode takes (v294 audit, PR 2)")
    # AUDIT, finding 4: the saved fit / opacity / blur / zoom were re-applied on
    # a 140 ms timer after the change event and DROPPED if the image was not yet
    # showing. Attach is async (a decode check, a FileReader, normalisation), so
    # on a slow phone the timer won the race and the adjustments vanished
    # without a word. Music re-applies in loadedmetadata; the photo now
    # re-applies when the image itself loads. The decode check is slowed here
    # to make the race certain rather than probable.
    import base64, pathlib, tempfile
    _png = pathlib.Path(tempfile.gettempdir()) / "skribl_amber_probe.png"
    _png.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
    pg8, box8 = pad_page("orig(k, v)")
    stroke(pg8, box8, 120); pg8.wait_for_timeout(600)
    pg8.set_input_files("#photoInput", str(_png)); pg8.wait_for_timeout(1500)
    pg8.evaluate("""() => { document.querySelector('.photo-fit-btn[data-fit="contain"]').click();
        const o = document.getElementById('photoOpacity'); o.value = 40; o.dispatchEvent(new Event('input', { bubbles: true })); }""")
    pg8.wait_for_timeout(2000)
    saved8 = pg8.evaluate("() => { const d = JSON.parse(localStorage.getItem('skribl_autosave_v1') || '{}'); return d.photoMeta ? [d.photoMeta.fit, d.photoMeta.opacity] : null; }")
    check("Pad: the adjustments are in the draft", saved8 == ["contain", 0.4], str(saved8))
    # The slow decode check has to be in place before the boot restore runs;
    # media_validation.js assigns the real one at load, so a setter trap
    # replaces whatever is assigned.
    pg8.add_init_script("""Object.defineProperty(window, 'skriblDecodeCheckImage', { configurable: true,
        get: () => ((f) => new Promise(r => setTimeout(() => r(null), 700))), set: () => {} });""")
    pg8.reload(wait_until="load"); pg8.wait_for_timeout(4700)
    got8 = pg8.evaluate("() => [photoFit, photoOpacityVal_, photoBgImg.style.display, photoBgImg.style.opacity]")
    check("Pad: after a slow decode the restored photo is showing",
          got8[2] == "block", f"{got8}")
    check("Pad: ...with its saved fit and opacity, not the defaults",
          got8[0] == "contain" and abs(got8[1] - 0.4) < 0.01 and got8[3] == "0.4", str(got8))
    pg8.close()

    print("\nPAD — a photo-only document survives its own reload while the photo decodes (third review)")
    # _mediaPresent() did not count a photo on its way back in, so for the
    # length of the decode a photo-only document was "empty" -- and the empty
    # branch of writeAutosave, seeing this session had restored it, DELETED the
    # autosave. The pill still said Saved; a tab killed then lost the document.
    pgP = b.new_page(viewport={"width": 1280, "height": 900})
    pgP.on("pageerror", lambda e: errs.append(f"photo-only: {e}"))
    pgP.goto(BASE + "/skribl-pad", wait_until="load"); pgP.wait_for_timeout(1000)
    pgP.evaluate("() => { localStorage.clear(); }")
    pgP.reload(wait_until="load"); pgP.wait_for_timeout(1000)
    pgP.set_input_files("#photoInput", str(_png))
    pgP.wait_for_function("() => mediaDraft.photo === 'durable'", timeout=20000); pgP.wait_for_timeout(1800)
    AUTO = "() => { const r = localStorage.getItem('skribl_autosave_v1'); if (!r) return null; const d = JSON.parse(r); return d.photoMeta ? d.photoMeta.name : 'no photo'; }"
    before = pgP.evaluate(AUTO)
    pgP.add_init_script("""(() => { let v; Object.defineProperty(window, 'skriblDecodeCheckImage', { configurable: true,
        get: () => v, set: (f) => { v = function () { const a = arguments;
          return new Promise(r => setTimeout(r, 2000)).then(() => f.apply(this, a)); }; } }); })();""")
    pgP.reload(wait_until="load"); pgP.wait_for_timeout(1000)
    during = pgP.evaluate("() => [(" + AUTO + ")(), !!_inFlight.photo]")
    pgP.wait_for_timeout(4000)
    landed = pgP.evaluate("() => [(" + AUTO + ")(), photoBgImg.style.display, photoBgImg._fileName]")
    check("Pad: a photo-only draft is still stored while its photo decodes after a reload",
          before == _png.name and during == [_png.name, True], f"before {before!r}, during {during}")
    check("Pad: ...and still stored once the photo is back on the canvas",
          landed == [_png.name, "block", _png.name], str(landed))
    pgP.close()

    print("\nSAVE DRAFT WAITS FOR A FILE STILL BEING READ (third review)")
    # The name switches to the new file before its bytes land, so a Save draft
    # in that gap stored the NEW name over the OLD photo's bytes (or, first
    # time, no photo while the toast said Saved). Save now waits, on both
    # editors. The decode check is slowed so the gap is certain, not lucky.
    import struct, zlib

    def _png1(rgb):
        raw = b"\x00" + bytes(rgb)
        chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    # Where each editor's gap is: Pad names the photo after its decode check
    # and holds the old bytes until the read AND the downscale finish, so the
    # downscale is slowed; Flip is busy from the moment a file is chosen, so
    # its decode check is.
    SLOW_DECODE = """(() => { let v; Object.defineProperty(window, 'skriblDecodeCheckImage', { configurable: true,
        get: () => v, set: (f) => { v = function () { const a = arguments;
          return new Promise(r => setTimeout(r, 1500)).then(() => f.apply(this, a)); }; } }); })();"""
    SLOW_NORMALISE = """() => { const f = window.normalizePhotoDataURL;
        window.normalizePhotoDataURL = function () { const a = arguments;
          return new Promise(r => setTimeout(r, 1500)).then(() => f.apply(this, a)); }; }"""
    SAVE = """async () => { const s = await SkriblSavedDrafts.save(); if (!s) return null;
        const rec = await SkriblDraftStore.get('saved:' + s.id); const pl = rec.payload;
        // Flip keeps the bytes in bgImage beside a photo settings object.
        const ph = pl.bgImage || pl.photo || (pl.frames && pl.frames[0] && pl.frames[0].photo) || null;
        return { id: s.id, data: typeof ph === 'string' ? ph : (ph && ph.data) || null }; }"""
    for route, inp, nm in (("/skribl-pad", "#photoInput", "Pad"), ("/flip", "#imageInput", "Flip")):
        pgS = b.new_page(viewport={"width": 1280, "height": 900})
        pgS.on("pageerror", lambda e, nm=nm: errs.append(f"save-busy {nm}: {e}"))
        if nm == "Flip":
            pgS.add_init_script(SLOW_DECODE)
        pgS.goto(BASE + route, wait_until="load"); pgS.wait_for_timeout(1200)
        pgS.evaluate("() => { localStorage.clear(); window.SkriblHints && window.SkriblHints.hide(); }")
        if nm == "Pad":
            pgS.evaluate(SLOW_NORMALISE)
        pgS.set_input_files(inp, {"name": "b.png", "mimeType": "image/png", "buffer": _png1((20, 90, 250))})
        pgS.wait_for_timeout(200)                      # the read has started, the decode has not finished
        early = pgS.evaluate(SAVE)
        toast = pgS.evaluate("() => document.body.innerText.includes('Preparing media')")
        pgS.wait_for_timeout(4000)
        late = pgS.evaluate(SAVE)
        check(f"{nm}: Save draft while a photo is still being read waits, and says so",
              early is None and toast, f"saved={early}, toast={toast}")
        check(f"{nm}: ...and once it has landed, the draft holds that photo",
              bool(late and late["data"]), str(late and {"id": late["id"], "data": (late["data"] or "")[:30]}))
        pgS.close()

    print("\nPAD — a restore overtaken by a newer photo stands down, so Save draft is not refused for good (fix review)")
    # reAddMediaFromStore left _restoring set when a newer pick or a remove
    # overtook it, and busy() read that as "media still being read" until the
    # next document: every Save draft said "Preparing media". The store read is
    # slowed so the newer photo lands first.
    pgX = b.new_page(viewport={"width": 1280, "height": 900})
    pgX.on("pageerror", lambda e: errs.append(f"restore-standdown: {e}"))
    pgX.goto(BASE + "/skribl-pad", wait_until="load"); pgX.wait_for_timeout(1200)
    pgX.evaluate("""() => { localStorage.clear(); const orig = SkriblDraftStore.get;
        SkriblDraftStore.get = (k) => new Promise(r => setTimeout(() => r(orig.call(SkriblDraftStore, k)), 1500));
        reAddMediaFromStore('photo', 'photoInput', { name: 'old.png' }); }""")
    pgX.set_input_files("#photoInput", {"name": "new.png", "mimeType": "image/png", "buffer": _png1((30, 160, 90))})
    pgX.wait_for_timeout(3500)
    stood = pgX.evaluate("""async () => { const s = await SkriblSavedDrafts.save();
        return { restoring: _restoring.photo, photo: photoBgImg._fileName, saved: !!s }; }""")
    check("Pad: a restore overtaken by a newer photo stands down, and Save draft saves",
          stood == {"restoring": False, "photo": "new.png", "saved": True}, str(stood))
    pgX.close()

    print("\nPAD — every restore writer fills the drawers' file rows, and an empty document empties them")
    # The Pad is the surface with separate restore writers: loadSkribl in
    # app.js (which the player loads too) resets and fills the photo and music
    # rows through typeof-guarded hooks, one per writer -- the reset of each,
    # the photo restore, and the music restore's loadedmetadata. Flip's restore
    # paths all end in syncMediaUI, which verify_parity pins. A restored photo
    # used to show no name at all, and a restored track "Loaded from draft".
    # Each drawer is opened for real before anything is asked about what shows
    # in it: a closed panel is display:none, where every visibility answer is
    # "no" on any tree.
    pgW = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pgW.on("pageerror", lambda e: errs.append(f"pad-rows: {e}"))
    pgW.goto(BASE + "/skribl-pad", wait_until="load"); pgW.wait_for_timeout(1200)
    pgW.evaluate("() => { localStorage.clear(); window.SkriblHints && window.SkriblHints.hide(); }")
    import base64 as _b64, io as _io
    _wb = _io.BytesIO()
    with wave.open(_wb, "wb") as _w2:
        _w2.setnchannels(1); _w2.setsampwidth(2); _w2.setframerate(8000)
        _w2.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 330 * _i / 8000))) for _i in range(8000 * 3)))
    WAVURL = "data:audio/wav;base64," + _b64.b64encode(_wb.getvalue()).decode()
    PNGW = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    pgW.evaluate("""async ([png, wav]) => {
        const d = serializeSkribl();
        d.photo = { data: png, name: 'new.png', fit: 'contain' };
        d.music = { data: wav, name: 'y.wav' };
        (d.frames || []).forEach(f => { f.photo = d.photo; });
        loadSkribl(d);
        for (let i = 0; i < 60 && !document.getElementById('musicUploadBtn').classList.contains('loaded'); i++)
          await new Promise(r => setTimeout(r, 100));
    }""", [PNGW, WAVURL])
    ROW = """(k) => { const g = (id) => document.getElementById(id), t = g(k + 'Thumb');
        const vis = (id) => { const e = g(id); return !!e && e.offsetParent !== null; };
        return { cur: (typeof _padDrawerCtl !== 'undefined' && _padDrawerCtl) ? _padDrawerCtl.current() : null,
                 name: g(k + 'BtnLabel').textContent, meta: g(k + 'BtnMeta').textContent,
                 nameShown: vis(k + 'BtnLabel'), add: vis(k + 'AddBtn'),
                 src: t ? (t.getAttribute('src') || '').slice(0, 15) : null, hasSrc: t ? t.hasAttribute('src') : null }; }"""
    browsing.pad_drawer(pgW, "photo")
    rp = pgW.evaluate(ROW, "photo")
    check("Pad: a restored photo's row names it and says its fit, with its picture",
          rp["cur"] == "photo" and rp["name"] == "new.png" and rp["meta"] == "Behind the drawing · Fit"
          and rp["nameShown"] and not rp["add"] and rp["src"].startswith("data:image/png"), str(rp))
    browsing.pad_drawer(pgW, "music")
    rm = pgW.evaluate(ROW, "music")
    check("Pad: a restored track's row names it and gives its length",
          rm["cur"] == "music" and rm["name"] == "y.wav" and rm["meta"] == "Loops under the drawing · 0:03"
          and rm["nameShown"] and not rm["add"], str(rm))
    pgW.evaluate("""async () => {
        const d2 = serializeSkribl(); delete d2.photo; delete d2.music;
        (d2.frames || []).forEach(f => { delete f.photo; });
        loadSkribl(d2);
        await new Promise(r => setTimeout(r, 800)); }""")
    browsing.pad_drawer(pgW, "photo")
    ep = pgW.evaluate(ROW, "photo")
    browsing.pad_drawer(pgW, "music")
    em = pgW.evaluate(ROW, "music")
    check("Pad: opening a document with no media empties both rows back to their drop areas",
          ep["cur"] == "photo" and ep["add"] and not ep["nameShown"] and ep["name"] == "" and ep["hasSrc"] is False
          and em["cur"] == "music" and em["add"] and not em["nameShown"] and em["name"] == "",
          f"photo {ep}; music {em}")
    pgW.close()

    print("\nFLIP — a draft opened from the Library asks over an autosaved photo, and the photo never lands on it (third review)")
    # Flip's content test ignored media on its way back from the store, so
    # /flip?draft=<id> replaced a photo-only autosave without asking; and the
    # boot restore's late answer then put that photo onto the OPENED draft,
    # whose next Save wrote it in. The store read is slowed to make the late
    # answer certain.
    ctxF = b.new_context(viewport={"width": 1280, "height": 900})
    pgF = ctxF.new_page(); pgF.on("pageerror", lambda e: errs.append(f"flip-draft: {e}"))
    pgF.goto(BASE + "/flip", wait_until="load"); pgF.wait_for_timeout(1200)
    pgF.evaluate("() => { localStorage.clear(); window.SkriblHints && window.SkriblHints.hide(); }")
    boxF = pgF.locator("#pad").bounding_box()
    pgF.mouse.move(boxF["x"] + 50, boxF["y"] + 50); pgF.mouse.down()
    pgF.mouse.move(boxF["x"] + 200, boxF["y"] + 150, steps=8); pgF.mouse.up(); pgF.wait_for_timeout(300)
    sidF = pgF.evaluate("async () => (await SkriblSavedDrafts.save()).id")
    pgF.evaluate("() => clearAllPages()")
    pgF.set_input_files("#imageInput", {"name": "auto.png", "mimeType": "image/png", "buffer": _png1((200, 40, 40))})
    pgF.wait_for_function("() => !!bgImage", timeout=20000)
    pgF.evaluate("() => flushFlipDraft()"); pgF.wait_for_timeout(1500)
    pgF2 = ctxF.new_page(); pgF2.on("pageerror", lambda e: errs.append(f"flip-draft: {e}"))
    pgF2.add_init_script("""(() => { let v; Object.defineProperty(window, 'SkriblDraftStore', { configurable: true, get: () => v,
        set: (x) => { const g = x.get; x.get = function (k) { const pr = g.apply(this, arguments);
          return k === 'flip:draft' ? pr.then(r => new Promise(res => setTimeout(() => res(r), 3000))) : pr; }; v = x; } }); })();""")
    pgF.close()
    pgF2.goto(BASE + "/flip?draft=" + sidF, wait_until="load"); pgF2.wait_for_timeout(900)
    asked = pgF2.evaluate("""() => { const s = document.getElementById('savedDraftsSheet');
        const row = s && s.querySelector('.sdrafts-row.armed'); return { shown: !!(s && !s.hidden), armed: !!row,
        strokes: frames[0].strokes.length }; }""")
    check("Flip: a Library link over an autosaved photo still on its way asks first",
          asked["shown"] and asked["armed"] and asked["strokes"] == 0, str(asked))
    pgF2.click("#savedDraftsSheet .sdrafts-row.armed .sdrafts-open"); pgF2.wait_for_timeout(4000)
    landed = pgF2.evaluate("() => ({ strokes: frames[0].strokes.length, photo: !!bgImage, name: imageName, current: SkriblSavedDrafts.current() })")
    check("Flip: ...and opened anyway, the draft does not collect the autosave's late photo",
          landed["strokes"] > 0 and not landed["photo"] and landed["current"] == sidF, str(landed))
    ctxF.close()

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
