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
  3. NOTHING LOADS UNTIL HELP OPENS. An editor that never opens How it works
     never fetches the player or an example.
  4. THEY PLAY, TOGETHER, AND STOP. Opened, the replays paint ink that grows
     over time -- read off the canvas pixels -- and more than one plays at once
     (the player's ambient mode). The clips advance and match the theme.
     Closed, everything stops.
  5. TRY IT picks the tool by the editor's own route and closes the panel;
     Shape's card is left open, as a tap on Shape leaves it.
  6. REDUCED MOTION: nothing plays; each replay shows its finished drawing and
     each clip its poster, and the clips are not even fetched.
  7. SEARCH: typing hands the panel to the reference.
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
STATE = """() => ({
    replays: [...document.querySelectorAll('#helpLearn .learn-card[data-demo]')].map(c =>
        c._learnPlayer ? c._learnPlayer.state().state : 'none'),
    clips: [...document.querySelectorAll('#helpLearn .learn-video')].map(v => ({
        src: v.getAttribute('src') || '', poster: v.getAttribute('poster') || '', t: v.currentTime, paused: v.paused })) })"""

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

        # 3. lazy
        early = [u for u in fetched if u.endswith("inlineplayer.js") or "/help/demos/" in u or "/help/clips/" in u]
        check(f"{name}: the editor fetches no player, example or clip until How it works opens",
              not early, str(early[:3]))

        # 2. census
        dock = pg.evaluate("() => [...document.querySelectorAll('.tool-btn[data-tool]')].map(b => b.dataset.tool)")
        reg = pg.evaluate("() => window.SkriblFlipTools ? SkriblFlipTools.list().map(t => t.id || t) : null")
        tools = set(dock) if name == "Pad" else ({"pen", "eraser", "shape"} & set(reg or []))
        cards = pg.evaluate("() => [...document.querySelectorAll('#helpLearn .learn-card[data-tool]')].map(c => c.dataset.tool)")
        tries = pg.evaluate("() => [...document.querySelectorAll('#helpLearn .learn-try')].map(b => b.dataset.try)")
        check(f"{name}: every tool ({', '.join(sorted(tools))}) has an example card with Try it",
              bool(tools) and tools <= set(cards) and tools <= set(tries),
              f"tools {sorted(tools)}, cards {cards}, Try it {tries}")
        check(f"{name}: the quick start is three steps, the second and third as screen clips",
              pg.evaluate("() => document.querySelectorAll('#helpLearn .learn-start .learn-card').length") == 3
              and pg.evaluate("() => document.querySelectorAll('#helpLearn .learn-start .learn-clip').length") == 2)

        # 4. plays
        pg.evaluate(OPEN)
        pg.wait_for_timeout(900)
        a = pg.evaluate(f"() => [...document.querySelectorAll('#helpLearn .learn-card[data-demo]')].map({INK})")
        pg.wait_for_timeout(1500)
        z = pg.evaluate(f"() => [...document.querySelectorAll('#helpLearn .learn-card[data-demo]')].map({INK})")
        s = pg.evaluate(STATE)
        check(f"{name}: opened, every replay paints ink, and the ink changes as it plays",
              all(x > 50 for x in z) and sum(1 for x, y in zip(a, z) if x != y) >= len(z) - 1,
              f"ink then {a}, later {z}")
        check(f"{name}: several examples play at once (the player's ambient mode)",
              s["replays"].count("playing") >= 3, str(s["replays"]))
        painted = pg.evaluate("""() => [...document.querySelectorAll('#helpLearn .learn-stage')].every(st => {
            const r = st.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return true;
            const at = document.elementFromPoint(r.left + r.width / 2, Math.min(innerHeight - 2, r.top + r.height / 2));
            return !!(at && st.contains(at)); })""")
        check(f"{name}: each example on screen is what is painted at its place", painted)
        t0 = [c["t"] for c in s["clips"]]
        pg.wait_for_timeout(900)
        s2 = pg.evaluate(STATE)
        check(f"{name}: the screen clips play (time advances) and match the dark theme",
              all(t2 > t1 for t1, t2 in zip(t0, [c["t"] for c in s2["clips"]]))
              and all("-dark." in c["src"] for c in s2["clips"]) and len(s2["clips"]) == 2, str(s2["clips"]))
        pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        pg.wait_for_timeout(500)
        s3 = pg.evaluate(STATE)
        check(f"{name}: in the light theme the clips switch to their light recording",
              all("-light." in c["src"] and "-light." in c["poster"] for c in s3["clips"]), str(s3["clips"]))
        pg.evaluate("() => document.documentElement.removeAttribute('data-theme')")

        # 7. search
        pg.fill("#helpSearch", "loop")
        pg.wait_for_timeout(300)
        check(f"{name}: searching hands the panel to the reference (the examples step aside)",
              pg.evaluate("() => document.getElementById('helpLearn').hidden") is True)
        pg.fill("#helpSearch", "")
        pg.wait_for_timeout(300)
        check(f"{name}: and clearing the search brings them back",
              pg.evaluate("() => document.getElementById('helpLearn').hidden") is False)

        # 4. closed, everything stops
        pg.evaluate("() => document.getElementById('helpClose').click()")
        pg.wait_for_timeout(700)
        s4 = pg.evaluate(STATE)
        check(f"{name}: closed, nothing keeps playing",
              "playing" not in s4["replays"] and all(c["paused"] for c in s4["clips"]), str(s4))

        # 5. Try it
        for t in sorted(tools):
            if not pg.locator(f'#helpLearn .learn-try[data-try="{t}"]').count():
                check(f"{name}: Try it on {t} picks it and closes How it works", False, "no Try it for this tool")
                continue
            pg.evaluate(OPEN); pg.wait_for_timeout(600)
            pg.locator(f'#helpLearn .learn-try[data-try="{t}"]').scroll_into_view_if_needed()
            pg.click(f'#helpLearn .learn-try[data-try="{t}"]')
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
        pg.wait_for_timeout(1500)
        s5 = pg.evaluate(STATE)
        ink = pg.evaluate(f"() => [...document.querySelectorAll('#helpLearn .learn-card[data-demo]')].map({INK})")
        check(f"{name}: with reduced motion nothing plays; each replay shows its finished drawing",
              "playing" not in s5["replays"] and all(x > 50 for x in ink), f"{s5['replays']} ink {ink}")
        check(f"{name}: and each clip shows its poster without fetching the video",
              all(c["poster"] and not c["src"] for c in s5["clips"]), str(s5["clips"]))
        ctx.close()
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r[1] for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
