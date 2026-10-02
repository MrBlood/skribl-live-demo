#!/usr/bin/env python3
"""How it works, shown: the example cards at the top of the help panel.

The owner, choosing it: "Showing people will really improve how it works ...
it has to be supreme quality ... this is the first thing users will do." So
this holds the cards to what they claim, on both editors:

  1. EVERY EXAMPLE IS A REAL SKRIBL. Each example file is posted to the server
     exactly as the editor posts, and must be accepted -- the same validation a
     person's drawing meets. A hand-edited or stale file fails here.
  2. EVERY TOOL HAS ONE. Each tool in Pad's dock has a card with Try it; on
     Flip, each tool Flip shares with Pad does (Flip's own tools arrive with
     their examples in the next change, and this census grows to all of them).
  3. NOTHING LOADS UNTIL IT IS ASKED FOR. The editor fetches nothing for it;
     opening How it works fetches only the bar's three previews; the player,
     examples and clips come with the drawer.
  THE BAR AND THE DRAWER (owner: "it fills the page"): How it works shows one
     "Watch it work" bar that counts the examples from the page; the drawer
     opens over the panel, its chips show one group or all, and it closes on
     Escape (leaving How it works open), a pull or tap on its grip, and with
     How it works.
  4. THEY PLAY, TOGETHER, AND STOP. In the open drawer the replays paint ink
     that changes over time -- read off the canvas pixels -- and more than one
     plays at once (the player's ambient mode). The clips advance and match
     the theme. Drawer or panel closed, everything stops.
  5. TRY IT picks the tool by the editor's own route and closes the panel;
     Shape's card is left open, as a tap on Shape leaves it.
  6. REDUCED MOTION: nothing plays; each replay shows its finished drawing and
     each clip its poster, and the clips are not even fetched.
  7. SEARCH: typing hands the panel to the reference; the bar steps aside.
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIPPED: playwright is not installed")
    sys.exit(0)

BASE = "http://127.0.0.1:5001"
ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMOS = ROOT / "skribl" / "static" / "help" / "demos"
results = []
check = make_check(results, with_detail=True)


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf-8", "replace")


# ---- 1. every example is a real Skribl --------------------------------------
print("\nEXAMPLES -- each one is accepted as a post")
files = sorted(DEMOS.glob("*.json"))
check("there are examples to check", len(files) >= 4, f"{len(files)} files in {DEMOS.relative_to(ROOT)}")
for f in files:
    st, why = post(json.loads(f.read_text()))
    check(f"{f.name}: the server accepts it as a post", st in (200, 201), f"HTTP {st} {why}")

# Ink across the stage's canvas: pixels clearly unlike the drawing's own
# ground, read at its corner. (It counted pixels brighter than a DARK ground
# until the illustrations brought a paper one, where it counted the paper.)
INK = """card => { const c = card.querySelector('canvas.skribl-inline-canvas');
    if (!c || !c.width) return -1;
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
    const g = [d[0], d[1], d[2]];
    for (let i = 0; i < d.length; i += 16)
      if (d[i + 3] > 200 && Math.abs(d[i] - g[0]) + Math.abs(d[i + 1] - g[1]) + Math.abs(d[i + 2] - g[2]) > 90) n++;
    return n; }"""
OPEN = "() => { window.SkriblHints && window.SkriblHints.hide(); openHelpDrawer(); }"
SHEET = "() => document.getElementById('learnPeek').click()"
CARDS = "#learnSheet .learn-card"
STATE = """() => ({
    sheet: !document.getElementById('learnSheet').hidden,
    replays: [...document.querySelectorAll('#learnSheet .learn-card[data-demo]')].map(c =>
        c._learnPlayer ? c._learnPlayer.state().state : 'none'),
    clips: [...document.querySelectorAll('#learnSheet .learn-video')].map(v => ({
        src: v.getAttribute('src') || '', poster: v.getAttribute('poster') || '', t: v.currentTime, paused: v.paused,
        start: v.closest('.learn-card').dataset.group === 'start' })) })"""
PLAYER = lambda u: u.endswith("inlineplayer.js") or "/help/demos/" in u or "/help/clips/" in u

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route, tool_expr in (("Pad", "/skribl-pad", "tool"), ("Flip", "/flip", "flipTool")):
        print(f"\n{name}")
        ctx = b.new_context(viewport={"width": 1200, "height": 900}, color_scheme="dark")
        pg = ctx.new_page()
        errs, fetched = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: fetched.append(r.url.split("?")[0]))
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(900)

        # 3. lazy, in two steps: the editor fetches nothing; How it works
        # fetches only the bar's previews; the drawer fetches the rest.
        early = [u for u in fetched if PLAYER(u) or "/help/thumbs/" in u]
        check(f"{name}: the editor fetches no player, example, clip or preview until How it works opens",
              not early, str(early[:3]))

        # 2. census
        dock = pg.evaluate("() => [...document.querySelectorAll('.tool-btn[data-tool]')].map(b => b.dataset.tool)")
        reg = pg.evaluate("() => window.SkriblFlipTools ? SkriblFlipTools.list().map(t => t.id || t) : null")
        # Every tool on Flip's shelf, its own included: those that reshape a
        # page (Select, Liquify, Smudge, Blur, Fill, Stamps, Artwork) are clips.
        tools = set(dock) if name == "Pad" else set(reg or [])
        cards = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-learn-tool]')].map(c => c.dataset.learnTool)")
        tries = pg.evaluate("() => [...document.querySelectorAll('#learnSheet .learn-try')].map(b => b.dataset.try)")
        check(f"{name}: every tool ({', '.join(sorted(tools))}) has an example card with Try it",
              bool(tools) and tools <= set(cards) and tools <= set(tries),
              f"tools {sorted(tools)}, cards {cards}, Try it {tries}")
        # The cards must not borrow the app's own attribute: they come first in
        # the page, so "the [data-tool=eraser]" found a card (#304; main red on
        # verify_pointerpad). Anything with data-tool is the app's.
        borrowed = pg.evaluate("() => [...document.querySelectorAll('[data-tool]')].filter(e => e.closest('#helpDrawer')).length")
        check(f"{name}: no example card carries the app's data-tool attribute", borrowed == 0,
              f"{borrowed} element(s) in How it works with data-tool")
        check(f"{name}: the quick start is three steps, the second and third as screen clips",
              pg.evaluate(f"() => document.querySelectorAll('{CARDS}[data-group=start]').length") == 3
              and pg.evaluate(f"() => document.querySelectorAll('{CARDS}[data-group=start].learn-clip').length") == 2)

        # THE BAR: what the page shows instead of the cards.
        fetched.clear()
        pg.evaluate(OPEN)
        pg.wait_for_timeout(900)
        bar = pg.evaluate("""() => { const b = document.getElementById('learnPeek'), r = b.getBoundingClientRect();
            return { n: document.querySelectorAll('#learnSheet .learn-card').length,
                     said: document.getElementById('learnPeekCount').textContent,
                     thumbs: [...b.querySelectorAll('img')].map(i => i.complete && i.naturalWidth > 0),
                     h: r.height, sheet: !document.getElementById('learnSheet').hidden }; }""")
        check(f"{name}: How it works shows one bar, not the cards: the drawer is shut and the bar is under 100px",
              bar["h"] < 100 and not bar["sheet"], str(bar))
        check(f"{name}: the bar counts the examples there are (counted, not typed)",
              bar["said"].startswith(f"{bar['n']} "), str(bar))
        check(f"{name}: the bar's three previews load when How it works opens",
              len(bar["thumbs"]) == 3 and all(bar["thumbs"]), str(bar["thumbs"]))
        check(f"{name}: opening How it works fetches no player, example or clip (only the drawer does)",
              not [u for u in fetched if PLAYER(u)], str([u for u in fetched if PLAYER(u)][:3]))

        # 4. plays, once the drawer is open
        pg.evaluate(SHEET)
        pg.wait_for_timeout(900)
        a = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        pg.wait_for_timeout(1500)
        z = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        s = pg.evaluate(STATE)
        # On screen in the drawer's scroll, or not: a card scrolled out of view
        # is paused by design and is not asked to change.
        seen = pg.evaluate(f"""() => {{ const sc = document.querySelector('#learnSheet .learn-sheet-scroll').getBoundingClientRect();
            return [...document.querySelectorAll('{CARDS}[data-demo]')].map(c => {{ const r = c.querySelector('.learn-stage').getBoundingClientRect();
              return r.bottom > sc.top + r.height * 0.4 && r.top < sc.bottom - r.height * 0.4; }}); }}""")
        moving = [x != y for x, y, v in zip(a, z, seen) if v]
        check(f"{name}: in the drawer, every replay paints ink, and the ones on screen change as they play",
              all(x > 50 for x in z) and len(moving) >= 2 and sum(moving) >= len(moving) - 1,
              f"ink then {a}, later {z}, on screen {seen}")
        check(f"{name}: several examples play at once (the player's ambient mode)",
              s["replays"].count("playing") >= 3, str(s["replays"]))
        painted = pg.evaluate("""() => [...document.querySelectorAll('#learnSheet .learn-stage')].every(st => {
            const r = st.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight || !r.width) return true;
            const sc = document.querySelector('#learnSheet .learn-sheet-scroll').getBoundingClientRect();
            if (r.bottom < sc.top || r.top > sc.bottom) return true;
            const y = Math.min(sc.bottom - 2, Math.max(sc.top + 2, r.top + r.height / 2));
            const at = document.elementFromPoint(r.left + r.width / 2, y);
            return !!(at && st.contains(at)); })""")
        check(f"{name}: each example on screen is what is painted at its place", painted)
        t0 = [c["t"] for c in s["clips"]]
        pg.wait_for_timeout(900)
        s2 = pg.evaluate(STATE)
        nclips = pg.evaluate("() => document.querySelectorAll('#learnSheet .learn-clip').length")
        # The quick start's clips are on screen when the drawer opens, so they
        # play; a clip further down plays when scrolled to, and is not asked to.
        check(f"{name}: the screen clips play (time advances) and every clip matches the dark theme",
              all(t2 > t1 for t1, t2, c in zip(t0, [c["t"] for c in s2["clips"]], s2["clips"]) if c["start"])
              and sum(1 for c in s2["clips"] if c["start"]) == 2
              and all("-dark." in c["src"] for c in s2["clips"]) and len(s2["clips"]) == nclips, str(s2["clips"]))
        pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        pg.wait_for_timeout(500)
        s3 = pg.evaluate(STATE)
        check(f"{name}: in the light theme the clips switch to their light recording",
              all("-light." in c["src"] and "-light." in c["poster"] for c in s3["clips"]), str(s3["clips"]))
        pg.evaluate("() => document.documentElement.removeAttribute('data-theme')")

        # THE CHIPS show one group, or all.
        shown = lambda: pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}')].filter(c => c.offsetParent)"
                                    ".map(c => c.dataset.group)")
        pg.click('#learnSheet .learn-chip[data-filter="tools"]'); pg.wait_for_timeout(150)
        only = shown()
        pg.click('#learnSheet .learn-chip[data-filter="all"]'); pg.wait_for_timeout(150)
        back = shown()
        check(f"{name}: Tools shows the tool cards and nothing else; All brings every card back",
              only and set(only) == {"tools"} and len(back) == bar["n"], f"tools {only}, all {len(back)}")

        # THE DRAWER CLOSES, and stops what it was playing.
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        esc = pg.evaluate("() => ({ sheet: !document.getElementById('learnSheet').hidden,"
                          " help: !document.getElementById('helpDrawer').hidden,"
                          " focus: document.activeElement && document.activeElement.id })")
        s4 = pg.evaluate(STATE)
        check(f"{name}: Escape closes the drawer and leaves How it works open, focus back on the bar",
              not esc["sheet"] and esc["help"] and esc["focus"] == "learnPeek", str(esc))
        check(f"{name}: with the drawer closed, nothing keeps playing",
              "playing" not in s4["replays"] and all(c["paused"] for c in s4["clips"]), str(s4))
        if not esc["help"]:                 # a failure above shut the panel; carry on
            pg.evaluate(OPEN); pg.wait_for_timeout(500)
        pg.evaluate(SHEET); pg.wait_for_timeout(500)
        g = pg.locator("#learnGrip").bounding_box()
        pg.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2); pg.mouse.down()
        for k in range(1, 9):
            pg.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2 + k * 18); pg.wait_for_timeout(16)
        pg.mouse.up(); pg.wait_for_timeout(500)
        check(f"{name}: a pull down on the grip closes the drawer",
              pg.evaluate("() => document.getElementById('learnSheet').hidden") is True)
        pg.evaluate(SHEET); pg.wait_for_timeout(500)
        pg.click("#learnGrip"); pg.wait_for_timeout(500)
        check(f"{name}: a tap on the grip closes it too",
              pg.evaluate("() => document.getElementById('learnSheet').hidden") is True)

        # 7. search
        pg.evaluate(SHEET); pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('learnSheet').querySelector('[data-learn-close].learn-close').click()")
        pg.wait_for_timeout(400)
        pg.fill("#helpSearch", "loop")
        pg.wait_for_timeout(300)
        check(f"{name}: searching hands the panel to the reference (the bar steps aside)",
              pg.evaluate("() => document.getElementById('helpLearn').hidden") is True)
        pg.fill("#helpSearch", "")
        pg.wait_for_timeout(300)
        check(f"{name}: and clearing the search brings it back",
              pg.evaluate("() => document.getElementById('helpLearn').hidden") is False)

        # 4. closing How it works closes the drawer and stops everything
        pg.evaluate(SHEET); pg.wait_for_timeout(700)
        pg.evaluate("() => document.getElementById('helpClose').click()")
        pg.wait_for_timeout(700)
        s5 = pg.evaluate(STATE)
        check(f"{name}: closing How it works closes the drawer; nothing keeps playing",
              not s5["sheet"] and "playing" not in s5["replays"] and all(c["paused"] for c in s5["clips"]), str(s5))

        # 5. Try it
        for t in sorted(tools):
            if not pg.locator(f'#learnSheet .learn-try[data-try="{t}"]').count():
                check(f"{name}: Try it on {t} picks it and closes How it works", False, "no Try it for this tool")
                continue
            pg.evaluate(OPEN); pg.wait_for_timeout(500)
            pg.evaluate(SHEET); pg.wait_for_timeout(500)
            pg.locator(f'#learnSheet .learn-try[data-try="{t}"]').scroll_into_view_if_needed()
            pg.click(f'#learnSheet .learn-try[data-try="{t}"]')
            pg.wait_for_timeout(600)
            got = pg.evaluate(f"() => ({{ tool: {tool_expr}, help: document.getElementById('helpDrawer').hidden,"
                              " card: !document.getElementById('shapePop').hidden })")
            check(f"{name}: Try it on {t} picks it and closes How it works"
                  + (", leaving the shape card open" if t == "shape" else ""),
                  got["tool"] == t and got["help"] is True and (got["card"] if t == "shape" else True), str(got))
            pg.evaluate("() => { const p = document.getElementById('shapePop'); if (p) p.hidden = true; }")
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        ctx.close()

        # 6. reduced motion
        ctx = b.new_context(viewport={"width": 1200, "height": 900}, reduced_motion="reduce")
        pg = ctx.new_page()
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(800)
        pg.evaluate(OPEN)
        pg.wait_for_timeout(400)
        pg.evaluate(SHEET)
        pg.wait_for_timeout(1500)
        s6 = pg.evaluate(STATE)
        ink = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        check(f"{name}: with reduced motion nothing plays; each replay shows its finished drawing",
              "playing" not in s6["replays"] and all(x > 50 for x in ink), f"{s6['replays']} ink {ink}")
        check(f"{name}: and each clip shows its poster without fetching the video",
              all(c["poster"] and not c["src"] for c in s6["clips"]), str(s6["clips"]))
        ctx.close()
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r[1] for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
