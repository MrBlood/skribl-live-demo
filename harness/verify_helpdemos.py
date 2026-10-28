#!/usr/bin/env python3
"""How it works, shown: the example cards at the top of the help panel.

The owner, choosing it: "Showing people will really improve how it works ...
it has to be supreme quality ... this is the first thing users will do." So
this holds the cards to what they claim, on both editors:

  1. EVERY EXAMPLE IS A REAL SKRIBL. Each example file is posted to the server
     exactly as the editor posts, and must be accepted -- the same validation a
     person's drawing meets. A hand-edited or stale file fails here.
     THE CARD THAT WAVES draws the card, then Blooby, then loops his wave
     Forever (owner: "draw blooby on slide 1 too, then make him wave in a
     loop"), read off the example itself.
  2. EVERY TOOL HAS ONE. Each tool in Pad's dock has a card with Try it; on
     Flip, each tool Flip shares with Pad does (Flip's own tools arrive with
     their examples in the next change, and this census grows to all of them).
  3. NOTHING LOADS UNTIL IT IS ASKED FOR. The editor fetches nothing for it;
     opening How it works fetches the player and the examples near the screen,
     the rest as they are scrolled to.
  ASK'S HOME (piece two of the help, FUTURE.md 6p): How it works opens on
     Ask, the examples a strip of pictures, one row that scrolls sideways.
     "Everything, by section" shows the answers: search and every entry,
     nothing playing; its back to Ask comes home, playing again.
  4. THEY PLAY, TOGETHER, AND STOP. On Ask's home the replays paint ink
     that changes over time -- read off the canvas pixels -- and more than one
     plays at once (the player's ambient mode). The clips advance and match
     the theme. On the answers, or with the panel closed, everything stops.
  5. TRY IT, with the example full screen, picks the tool by the editor's own
     route and closes the panel; Shape's card is left open, as a tap on Shape
     leaves it.
  6. REDUCED MOTION: nothing plays; each replay shows its finished drawing and
     each clip its poster, and the clips are not even fetched.
"""
import json
import math
import pathlib
import re
import sys
import urllib.error
import urllib.request

from assertions import make_check
import browsing
import os

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIPPED: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
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

# ---- 1b. the card that waves --------------------------------------------------
# The owner, on the Flip of Blooby's card: "the blooby card was supposed to draw
# blooby on slide 1 too, then make him wave in a loop". The players keeping draw,
# under and loop are verify_loop's and verify_under's; asked here is that the
# example says it. Each page of the wave was copied from page 2 once his body was
# drawn there, so each begins with that body point for point: that is what says
# page 2 holds Blooby, not merely some ink. What follows the body is his arm and
# eyes, and page 2's is the pose the wave comes round to, so he steps into it.
print("\nTHE CARD THAT WAVES -- the card, then Blooby, then his wave forever")
wc = json.loads((DEMOS / "flip-blooby-card.json").read_text())
fr, loop = wc["frames"], wc.get("loop") or {}
last = len(fr) - 1
draws = [f.get("draw") is True for f in fr]
check("the card draws itself on page 1 and stays under every page after it",
      draws[0] and wc.get("under") == {"page": 0, "from": 1, "to": last}, f"draws {draws[:3]}, under {wc.get('under')}")
check("then Blooby draws himself on page 2, once, before the loop",
      len(fr) > 2 and draws[1] and loop.get("from") == 2, f"draws {draws[:3]}, loop {loop}")


def shared(a, b):
    n = 0
    for p, q in zip(a["strokes"], b["strokes"]):
        if p != q:
            break
        n += 1
    return n


body = min((shared(fr[1], f) for f in fr[2:]), default=0)
check("...page 2 is Blooby: every page of the wave begins with its body, point for point, and it has his arm and eyes too",
      len(fr[1]["strokes"]) // 2 <= body < len(fr[1]["strokes"]), f"{body} of page 2's {len(fr[1]['strokes'])} points shared")


def arm(f):
    pts = f["strokes"][body:] or [{"x": 0, "y": 0}]
    return sum(p["x"] for p in pts) / len(pts), sum(p["y"] for p in pts) / len(pts)


lo, hi = loop.get("from", 1), loop.get("to", last)
near = min(range(lo, hi + 1), key=lambda k: math.dist(arm(fr[1]), arm(fr[k])))
check("...and he steps straight into the wave: of all its pages, page 2's arm is nearest the last one's",
      near == hi, f"nearest page {near + 1}; the loop is pages {lo + 1}-{hi + 1}")
check("his wave is every page after, looped Forever, and none of them draws itself",
      loop == {"from": 2, "to": last, "forever": True} and not any(draws[2:]), f"loop {loop}, draws {draws}")

# ---- 1c. the card's title is the header's mark -----------------------------
# The card's title is the header's own mark, drawn by the pen: blooby.py reads
# both its paths from the template. After v327 the mark's dot moved 1.3 of its
# units left, over the i, and the two examples that draw the card kept the old
# spot until they were drawn again (3.6 px right, on the card). Asked of the
# drawings: the dot each draws twice, ink then purple, sits where the
# template's dot falls on the card, and the title's line is the template's.
print("\nTHE CARD'S TITLE -- the header's mark, its dot over the i")
sys.path.insert(0, str(ROOT / "harness" / "tools"))
import blooby  # noqa: E402

_main, _dot = blooby.sig_strokes(*blooby.TITLE)
_want = ((_dot[0][0] + _dot[1][0]) / 2, (_dot[0][1] + _dot[1][1]) / 2)
_box = (min(x for x, _ in _main), min(y for _, y in _main), max(x for x, _ in _main), max(y for _, y in _main))


def _seg(p, a, b):
    """How far p is from the segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1)))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _title(f):
    """The strokes inside the title's box (and a pen's width round it), as
    (points, extent): the yellow shadow, the ink and purple lines, the dots."""
    out, i = [], 0
    for n in f["strokeGroups"]:
        g, i = f["strokes"][i:i + n], i + n
        xs, ys = [p["x"] for p in g], [p["y"] for p in g]
        if min(xs) >= _box[0] - 15 and max(xs) <= _box[2] + 15 and min(ys) >= _box[1] - 15 and max(ys) <= _box[3] + 15:
            out.append((g, max(max(xs) - min(xs), max(ys) - min(ys))))
    return out


for _name in ("blooby-card.json", "flip-blooby-card.json"):
    _t = _title(json.loads((DEMOS / _name).read_text())["frames"][0])
    _dots = [g for g, ext in _t if ext < 6]
    _cols = [g[0]["color"] for g in _dots]
    _off = [math.dist(_want, (sum(p["x"] for p in g) / len(g), sum(p["y"] for p in g) / len(g))) for g in _dots]
    check(f"{_name}: the title's dot is drawn twice, ink then purple",
          _cols == [blooby.INK, blooby.PURPLE], f"{len(_dots)} dot(s), colours {_cols}")
    check(f"...where the header's mark puts it, over the i",
          _dots and max(_off) < 1.0, "off by " + ", ".join(f"{d:.1f}" for d in _off) + " px")
    # The line: its corners where the template's are, and no point of it
    # farther from the template's line than the pen's own wobble (1.1 px as
    # drawn; an i moved a unit sideways is 2.7).
    _ink = [g for g, ext in _t if ext > 100 and g[0]["color"] == blooby.INK]
    _err = [max(abs(a - b) for a, b in zip(_box, (min(p["x"] for p in g), min(p["y"] for p in g),
                                                   max(p["x"] for p in g), max(p["y"] for p in g)))) for g in _ink]
    _far = [max(min(_seg((p["x"], p["y"]), _main[k], _main[k + 1]) for k in range(len(_main) - 1)) for p in g)
            for g in _ink]
    check(f"...and the title's line is the header's mark's line",
          len(_ink) == 1 and _err[0] < 1.5 and _far[0] < 1.6,
          f"{len(_ink)} ink line(s), corners off by " + ", ".join(f"{e:.1f}" for e in _err)
          + " px, farthest point " + ", ".join(f"{d:.1f}" for d in _far) + " px")

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
# Flip's animating techniques -> the control that does each one. Hold is the
# badge on a page in the strip; the first page always has one.
TECHNIQUES = {"onion": "#onion", "inbetween": "#addinbetween", "smear": "#addtween",
              "hold": "#strip .frame .holdbadge", "guides": "#arcGuideBtn"}
# Pad's extras -> the control each one is.
EXTRAS = {"takes": "#addTakePill", "speed": "#padLine .rl-speed", "photo": "#photoUploadBtn", "export": "#exportItem",
          "zoom": "#magnifyBtn"}
OPEN = "() => { window.SkriblHints && window.SkriblHints.hide(); openHelpDrawer(); }"
SHEET = "() => window.SkriblHelpLearn.show('home')"
CARDS = "#helpWatch .learn-card"
# On screen: under Ask's field, above the sheet's foot, and inside the strip,
# which scrolls sideways and clips what it has scrolled past.
VIS = """const i = document.querySelector('#helpDrawer .help-drawer-inner').getBoundingClientRect(),
    t = document.querySelector('#helpDrawer .ask-bar').getBoundingClientRect(),
    s = document.querySelector('#helpWatch .learn-all').getBoundingClientRect(),
    vis = e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.bottom > t.bottom + r.height * 0.4 && r.top < i.bottom - r.height * 0.4
      && r.right > s.left + r.width * 0.4 && r.left < s.right - r.width * 0.4; };"""
STATE = """() => { """ + VIS + """
    return {
    sheet: (!document.getElementById('helpDrawer').hidden && !document.getElementById('helpWatch').hidden),
    replays: [...document.querySelectorAll('#helpWatch .learn-card[data-demo]')].map(c =>
        c._learnPlayer ? c._learnPlayer.state().state : 'none'),
    clips: [...document.querySelectorAll('#helpWatch .learn-video')].map(v => ({
        src: v.getAttribute('src') || '', poster: v.getAttribute('poster') || '', t: v.currentTime, paused: v.paused,
        start: v.closest('.learn-card').dataset.group === 'start', vis: vis(v.closest('.learn-stage')) })) }; }"""
PLAYER = lambda u: u.endswith("inlineplayer.js") or "/help/demos/" in u or "/help/clips/" in u
EXAMPLE = lambda u: "/help/demos/" in u or ("/help/clips/" in u and (u.endswith(".mp4") or u.endswith(".webm")))
# The strip brought into view and scrolled to its end in steps, so every
# example comes near the screen once -- which is when it is fetched (V319-005).
STRIP = "() => document.querySelector('#helpWatch .learn-all').scrollIntoView({ block: 'center', behavior: 'instant' })"
SCROLL_ALL = "() => { const s = document.querySelector('#helpWatch .learn-all'); s.scrollBy({ left: s.clientWidth * 0.8, behavior: 'instant' }); return s.scrollLeft + s.clientWidth >= s.scrollWidth - 2; }"
HOME_TOP = "() => { document.querySelector('#helpDrawer .help-drawer-inner').scrollTo({ top: 0, behavior: 'instant' }); document.querySelector('#helpWatch .learn-all').scrollTo({ left: 0, behavior: 'instant' }); }"
def scroll_all(pg):
    pg.evaluate(STRIP)
    pg.wait_for_timeout(400)
    for _ in range(40):
        done = pg.evaluate(SCROLL_ALL)
        pg.wait_for_timeout(250)
        if done:
            break
    pg.wait_for_timeout(1200)

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

        # 3. lazy: the editor fetches nothing; How it works fetches what is
        # near the screen.
        early = [u for u in fetched if PLAYER(u)]
        check(f"{name}: the editor fetches no player, example or clip until How it works opens",
              not early, str(early[:3]))

        # 2. census
        dock = pg.evaluate("() => [...document.querySelectorAll('.tool-btn[data-tool]')].map(b => b.dataset.tool)")
        reg = pg.evaluate("() => window.SkriblFlipTools ? SkriblFlipTools.list().map(t => t.id || t) : null")
        # Every tool on Flip's shelf, its own included: those that reshape a
        # page (Select, Liquify, Smudge, Blur, Fill, Stamps, Artwork) are clips.
        tools = set(dock) if name == "Pad" else set(reg or [])
        cards = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-learn-tool]')].map(c => c.dataset.learnTool)")
        tries = pg.evaluate("() => [...document.querySelectorAll('#helpWatch .learn-try')].map(b => b.dataset.try)")
        check(f"{name}: every tool ({', '.join(sorted(tools))}) has an example card with Try it",
              bool(tools) and tools <= set(cards) and tools <= set(tries),
              f"tools {sorted(tools)}, cards {cards}, Try it {tries}")
        # The cards must not borrow the app's own attribute: they come first in
        # the page, so "the [data-tool=eraser]" found a card (#304; main red on
        # verify_pointerpad). Anything with data-tool is the app's.
        borrowed = pg.evaluate("() => [...document.querySelectorAll('[data-tool]')].filter(e => e.closest('#helpDrawer')).length")
        check(f"{name}: no example card carries the app's data-tool attribute", borrowed == 0,
              f"{borrowed} element(s) in How it works with data-tool")
        # Flip's techniques: each control a person uses to animate has an
        # example under Techniques. The control is looked up in the editor too,
        # so a renamed or removed one fails here instead of leaving the list stale.
        # Pad's extras likewise: takes, the replay's speed, a photo, export.
        def group(g, controls):
            return pg.evaluate(f"""() => ({{
                controls: Object.fromEntries(Object.entries({json.dumps(controls)}).map(([k, s]) => [k, !!document.querySelector(s)])),
                cards: [...document.querySelectorAll('{CARDS}[data-group={g}]')].map(c => c.dataset.clipName) }})""")
        mine, theirs = (("techniques", TECHNIQUES), ("extras", EXTRAS)) if name == "Flip" else (("extras", EXTRAS), ("techniques", TECHNIQUES))
        got = group(*mine)
        check(f"{name}: every one of its {mine[0]} (" + ", ".join(sorted(mine[1])) + ") is a control in the editor and has an example",
              all(got["controls"].values()) and set(mine[1]) <= set(got["cards"]), str(got))
        other = group(theirs[0], {})
        check(f"{name}: no {theirs[0]} cards (they are the other editor's)", not other["cards"], str(other))
        check(f"{name}: the quick start is three steps, the second and third as screen clips",
              pg.evaluate(f"() => document.querySelectorAll('{CARDS}[data-group=start]').length") == 3
              and pg.evaluate(f"() => document.querySelectorAll('{CARDS}[data-group=start].learn-clip').length") == 2)

        # ASK'S HOME: How it works opens on it, the examples a strip.
        fetched.clear()
        pg.evaluate(OPEN)
        pg.wait_for_timeout(900)
        home = pg.evaluate("""() => { const t = id => document.getElementById(id);
            const cs = [...document.querySelectorAll('#helpWatch .learn-card')];
            const c = cs[0].getBoundingClientRect();
            return { n: cs.length, shown: !t('helpWatch').hidden, lookShown: !t('helpLook').hidden,
                     rows: new Set(cs.map(k => Math.round(k.getBoundingClientRect().top))).size,
                     card: Math.round(c.width), title: getComputedStyle(document.querySelector('#helpWatch .learn-title')).fontSize }; }""")
        bar = home
        check(f"{name}: How it works opens on Ask's home: the examples showing, the answers not",
              home["shown"] and not home["lookShown"], str(home))
        check(f"{name}: ...and the examples are one strip of pictures, every card in one row, 200px on a desk, titled at 15px",
              home["rows"] == 1 and home["card"] == 200 and home["title"] == "15px", str(home))
        pg.evaluate(STRIP)
        pg.wait_for_timeout(1200)

        # 4. plays, once How it works is open
        a = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        pg.wait_for_timeout(1500)
        z = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        s = pg.evaluate(STATE)
        # On screen in the drawer's scroll, or not: a card scrolled out of view
        # is paused by design and is not asked to change.
        seen = pg.evaluate("() => { " + VIS + f" return [...document.querySelectorAll('{CARDS}[data-demo]')].map(c => vis(c.querySelector('.learn-stage'))); }}")
        moving = [x != y for x, y, v in zip(a, z, seen) if v]
        check(f"{name}: on Ask's home, every replay on screen paints ink and changes as it plays",
              all(x > 50 for x, v in zip(z, seen) if v) and moving and all(moving),
              f"ink then {a}, later {z}, on screen {seen}")
        # LOADING FOLLOWS THE EYE (outside audit V319-005). Opening the drawer
        # fetched every example in it, about 3 MB, for someone come to watch
        # one. Now: what is on screen and the next one or two, and no more.
        asked = sorted({u for u in fetched if EXAMPLE(u)})
        check(f"{name}: opening How it works fetches the examples near the screen, not all {bar['n']}",
              0 < len(asked) < bar["n"] - 3, f"{len(asked)} fetched of {bar['n']}: {[u.split('/')[-1] for u in asked]}")
        # The strip in view at its tools (the quick start before them is one
        # replay and two clips): the replays on screen play at once (the
        # player's ambient mode).
        pg.evaluate(f"""() => {{ const s = document.querySelector('#helpWatch .learn-all'), c = s.querySelector('.learn-card[data-group=tools]');
            s.scrollTo({{ left: c.offsetLeft - s.offsetLeft, behavior: 'instant' }}); }}""")
        pg.wait_for_timeout(1500)
        two = pg.evaluate(STATE)["replays"]
        check(f"{name}: the replays in the strip play at once (the player's ambient mode)",
              two.count("playing") >= 2, str(two))
        s = pg.evaluate(STATE)
        painted = pg.evaluate("() => { " + VIS + """ const on = [...document.querySelectorAll('#helpWatch .learn-stage')].filter(vis);
            return on.length > 1 && on.every(st => { const r = st.getBoundingClientRect();
              const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return !!(at && st.contains(at)); }); }""")
        check(f"{name}: each example on screen is what is painted at its place", painted)
        # Back to the strip's start, where the quick start's two clips are.
        pg.evaluate("() => document.querySelector('#helpWatch .learn-all').scrollTo({ left: 0, behavior: 'instant' })")
        pg.wait_for_timeout(900)
        s = pg.evaluate(STATE)
        t0 = [c["t"] for c in s["clips"]]
        pg.wait_for_timeout(900)
        s2 = pg.evaluate(STATE)
        nclips = pg.evaluate("() => document.querySelectorAll('#helpWatch .learn-clip').length")
        # A clip on screen plays; one further down plays when scrolled to,
        # and is not asked to.
        check(f"{name}: the screen clips on screen play (time advances) and every clip matches the dark theme",
              all(t2 > t1 for t1, t2, c in zip(t0, [c["t"] for c in s2["clips"]], s2["clips"]) if c["vis"])
              and any(c["vis"] for c in s2["clips"])
              and all("-dark." in c["src"] for c in s2["clips"] if c["src"]) and len(s2["clips"]) == nclips, str(s2["clips"]))
        pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        pg.wait_for_timeout(500)
        s3 = pg.evaluate(STATE)
        check(f"{name}: in the light theme the clips switch to their light recording",
              any(c["src"] for c in s3["clips"])
              and all("-light." in c["src"] and "-light." in c["poster"] for c in s3["clips"] if c["src"]), str(s3["clips"]))
        pg.evaluate("() => document.documentElement.removeAttribute('data-theme')")
        pg.wait_for_timeout(300)
        # ...AND THE REST WHEN SCROLLED TO: every example fetched by the end,
        # each replay with its player, each clip with a recording in the theme
        # showing. A loader that only ever fetched the first screen fails here.
        scroll_all(pg)
        s4 = pg.evaluate(STATE)
        check(f"{name}: scrolled to the end, every example has been fetched and set up",
              all(x != "none" for x in s4["replays"]) and all("-dark." in c["src"] for c in s4["clips"]),
              f"replays {s4['replays']}, clips {[c['src'].split('/')[-1] for c in s4['clips']]}")
        pg.evaluate(HOME_TOP)
        pg.wait_for_timeout(300)

        # FULL SCREEN (owner: "we should be allowed to click ... and have it
        # full screen"). A tap on a replay opens a player of its own, large; a
        # tap on a clip, the clip large; the cards pause beneath; Escape closes
        # only the viewer and hands focus back to the card that opened it.
        VIEW = """() => { const v = document.getElementById('learnViewer'), st = document.getElementById('learnViewerStage');
            const box = st.querySelector('.skribl-inline'), vid = st.querySelector('video');
            const r = (box || vid) ? (box || vid).getBoundingClientRect() : null;
            return { open: !v.hidden, w: r ? Math.round(r.width) : 0, h: r ? Math.round(r.height) : 0,
                     player: box && box._skriblInline ? box._skriblInline.state().state : null,
                     t: vid ? vid.currentTime : null, title: document.getElementById('learnViewerTitle').textContent,
                     try: document.getElementById('learnViewerTry').hidden ? null : document.getElementById('learnViewerTry').dataset.try,
                     cards: [...document.querySelectorAll('#helpWatch .learn-card[data-demo]')].map(c =>
                       c._learnPlayer ? c._learnPlayer.state().state : 'none') }; }"""
        first = pg.locator(f"{CARDS}[data-demo]:has(.learn-try)").first
        first.scroll_into_view_if_needed()
        cw = first.locator(".learn-stage").bounding_box()["width"]
        ftry = first.locator(".learn-try").get_attribute("data-try")
        first.locator(".learn-stage").click()
        pg.wait_for_timeout(1800)
        v1 = pg.evaluate(VIEW)
        check(f"{name}: a tap on a replay opens it full screen, at least twice the card's size, playing",
              v1["open"] and v1["w"] >= 2 * cw and v1["player"] == "playing", f"{v1}, card {cw:.0f}px")
        check(f"{name}: ...and the cards pause beneath it", "playing" not in v1["cards"], str(v1["cards"]))
        check(f"{name}: ...with its Try it, since the strip's cards are pictures",
              ftry and v1["try"] == ftry, f"card {ftry}, viewer {v1['try']}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
        back = pg.evaluate("() => ({ viewer: !document.getElementById('learnViewer').hidden,"
                           " sheet: (!document.getElementById('helpDrawer').hidden && !document.getElementById('helpWatch').hidden),"
                           " focus: !!(document.activeElement && document.activeElement.classList.contains('learn-stage')) })")
        check(f"{name}: Escape closes full screen only, focus back on the card", 
              not back["viewer"] and back["sheet"] and back["focus"], str(back))
        clip = pg.locator(f"{CARDS}.learn-clip").first
        ch = clip.locator(".learn-stage").bounding_box()["height"]
        clip.locator(".learn-stage").click()
        pg.wait_for_timeout(700)
        c1 = pg.evaluate(VIEW); pg.wait_for_timeout(900); c2 = pg.evaluate(VIEW)
        check(f"{name}: a tap on a clip opens it full screen, larger than its card, and it plays",
              c1["open"] and c1["h"] >= 1.25 * ch and (c2["t"] or 0) > (c1["t"] or 0), f"{c1} then t={c2['t']}, card {ch:.0f}px tall")
        pg.click("#learnViewerClose"); pg.wait_for_timeout(300)
        check(f"{name}: the close button puts it away",
              pg.evaluate("() => document.getElementById('learnViewer').hidden") is True)

        # EVERYTHING, BY SECTION: the answers, and nothing playing. From down
        # Ask's home, the change of view lands at the top at once: the panel
        # scrolls smoothly, and it glided back past every example.
        jump = pg.evaluate("""() => new Promise(res => { const sc = document.querySelector('#helpDrawer .help-drawer-inner');
            sc.scrollTo({ top: sc.scrollHeight, behavior: 'instant' }); const from = sc.scrollTop;
            document.getElementById('askBrowse').click();
            requestAnimationFrame(() => requestAnimationFrame(() => res([from, sc.scrollTop]))); })""")
        check(f"{name}: a change of view from down the sheet lands at the top at once, no glide",
              jump[0] > 100 and jump[1] == 0, f"from {jump[0]}px, two frames later {jump[1]}px")
        pg.wait_for_timeout(500)
        look = pg.evaluate("""() => { const f = document.getElementById('helpSearch'), r = f.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            const bk = document.getElementById('askLookBack');
            return { home: !document.getElementById('helpWatch').hidden, look: !document.getElementById('helpLook').hidden,
                     search: !!at && (at === f || f.contains(at)), back: !!bk && bk.offsetParent !== null,
                     entries: [...document.querySelectorAll('#helpLook .help-tip')].length }; }""")
        s4 = pg.evaluate(STATE)
        check(f"{name}: Everything, by section shows the search, painted, every entry and a way back; Ask's home steps away",
              look["look"] and not look["home"] and look["search"] and look["back"] and look["entries"] > 20, str(look))
        check(f"{name}: ...and on the answers nothing keeps playing",
              "playing" not in s4["replays"] and all(c["paused"] for c in s4["clips"]), str(s4))
        pg.click("#askLookBack"); pg.wait_for_timeout(400)
        pg.evaluate(STRIP); pg.wait_for_timeout(900)
        kb = pg.evaluate("""() => ({ focus: document.activeElement && document.activeElement.id,
            shown: !document.getElementById('helpWatch').hidden, look: !document.getElementById('helpLook').hidden })""")
        s4b = pg.evaluate(STATE)
        check(f"{name}: back to Ask comes home: the field focused, the examples playing again",
              kb["focus"] == "helpSearch" and kb["shown"] and not kb["look"] and "playing" in s4b["replays"],
              f"{kb}, replays {s4b['replays']}")

        # 4. closing How it works closes the drawer and stops everything
        pg.evaluate(SHEET); pg.wait_for_timeout(700)
        pg.locator(f"{CARDS}[data-demo]").first.locator(".learn-stage").click(); pg.wait_for_timeout(600)
        pg.evaluate("() => document.getElementById('helpClose').click()")
        pg.wait_for_timeout(700)
        s5 = pg.evaluate(STATE)
        check(f"{name}: closing How it works stops everything; nothing keeps playing",
              not s5["sheet"] and "playing" not in s5["replays"] and all(c["paused"] for c in s5["clips"]), str(s5))
        check(f"{name}: ...and closes full screen with it",
              pg.evaluate("() => document.getElementById('learnViewer').hidden") is True)
        # THE THEME CHANGED WHILE IT WAS SHUT, which is the only way (Theme is in
        # the menu): reopened, the clips already fetched are in the new theme
        # (owner's phone, dark, after v323: the light clip in a dark card).
        pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        pg.wait_for_timeout(300)
        pg.evaluate(OPEN); pg.wait_for_timeout(800)
        s6 = pg.evaluate(STATE)
        check(f"{name}: themed while shut, reopened: the clips are the light recording",
              any(c["src"] for c in s6["clips"])
              and all("-light." in c["src"] and "-light." in c["poster"] for c in s6["clips"] if c["src"]),
              str([c["src"].split("/")[-1] for c in s6["clips"]]))
        pg.evaluate("() => document.getElementById('helpClose').click()"); pg.wait_for_timeout(500)
        pg.evaluate("() => document.documentElement.removeAttribute('data-theme')")
        pg.wait_for_timeout(300)

        # 5. Try it, from the example full screen
        for t in sorted(tools):
            if not pg.locator(f'#helpWatch .learn-try[data-try="{t}"]').count():
                check(f"{name}: Try it on {t} picks it and closes How it works", False, "no Try it for this tool")
                continue
            pg.evaluate(OPEN); pg.wait_for_timeout(500)
            pg.evaluate(SHEET); pg.wait_for_timeout(500)
            pg.locator(f'{CARDS}:has(.learn-try[data-try="{t}"]) .learn-stage').click()
            pg.wait_for_timeout(400)
            pg.click("#learnViewerTry")
            # How it works closes on a transition of about half a second; under
            # a busy page it can run past a fixed 600ms. Wait for it, up to 3s,
            # so a panel that never closes still fails.
            try:
                pg.wait_for_function("() => document.getElementById('helpDrawer').hidden", timeout=3000)
            except Exception:
                pass
            pg.wait_for_timeout(150)
            got = pg.evaluate(f"() => ({{ tool: {tool_expr}, help: document.getElementById('helpDrawer').hidden,"
                              " viewer: document.getElementById('learnViewer').hidden,"
                              " card: !document.getElementById('shapePop').hidden })")
            check(f"{name}: Try it on {t} picks it and closes How it works and full screen"
                  + (", leaving the shape card open" if t == "shape" else ""),
                  got["tool"] == t and got["help"] is True and got["viewer"] is True and (got["card"] if t == "shape" else True), str(got))
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
        # Every card, not the first screen: they load as they come near it.
        scroll_all(pg)
        s6 = pg.evaluate(STATE)
        ink = pg.evaluate(f"() => [...document.querySelectorAll('{CARDS}[data-demo]')].map({INK})")
        check(f"{name}: with reduced motion nothing plays; each replay shows its finished drawing",
              "playing" not in s6["replays"] and all(x > 50 for x in ink), f"{s6['replays']} ink {ink}")
        check(f"{name}: and each clip shows its poster without fetching the video",
              all(c["poster"] and not c["src"] for c in s6["clips"]), str(s6["clips"]))
        ctx.close()

        # 8. HOW IT WORKS RISES IN, it does not jump (owner's iPhone: "the menu
        # hiccups before it slides in"). Opening moves focus to the close button
        # while the panel is still off screen; a focus() that may scroll made
        # the browser scroll the drawer to reveal it, so the panel snapped
        # fully in at once and then eased back as the slide ran. On a phone it
        # is a sheet since Ask, rising from the foot. Measured frame by frame,
        # opened from the menu as a person does.
        ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(800)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        opener = ("#menuBtn", "#helpItem") if name == "Pad" else ("#moreBtn", "#miInfo")
        pg.click(opener[0]); pg.wait_for_timeout(600)
        # The browser's own count of the times it worked out the page's style.
        cdp = ctx.new_cdp_session(pg)
        cdp.send("Performance.enable")
        recalc = lambda: next(m["value"] for m in cdp.send("Performance.getMetrics")["metrics"] if m["name"] == "RecalcStyleCount")
        r0 = recalc()
        # Each frame on its own clock (document.timeline), which is the time
        # the sheet's place is worked out for: performance.now() at the read
        # can come after a hold in the same frame, so the hold showed nowhere.
        frames = pg.evaluate("""(item) => new Promise(res => { const d = document.getElementById('helpDrawer'),
            i = d.querySelector('.help-drawer-inner'), out = [], t0 = performance.now(), t1 = document.timeline.currentTime;
            document.querySelector(item).click();
            (function tick() { out.push([Math.max(d.scrollLeft, d.scrollTop), i.getBoundingClientRect().top, document.timeline.currentTime - t1]);
              if (performance.now() - t0 < 700) requestAnimationFrame(tick); else res(out); })(); })""", opener[1])
        scrolled = max(f[0] for f in frames)
        tops = [f[1] for f in frames]
        total = tops[0] - tops[-1]
        steps = [(frames[j + 1][2] - frames[j][2], tops[j] - tops[j + 1]) for j in range(len(frames) - 1)]
        # One way, and travelled: a snap from off-screen to home in a single
        # frame is "one way" too, which is how the first draft of this passed
        # on the broken tree; so it is seen at three places on the way at least.
        # A FRAME THE BOX HELD IS NOT A JUMP (main red after #656: 733 to 390,
        # 45% of the way, on one database's runner and not the other's). The
        # sheet is a transform the compositor moves, so a person sees it glide
        # whatever the page is doing; the page reads where it is once a frame,
        # and a frame held 50ms or more reads a stretch of the glide at once.
        # The ease's fastest stretch is about 15% of the way a frame, so a
        # frame under 50ms cannot cover 40%. One such step is set aside, the
        # biggest, named in the detail.
        held = [j for j, (dt, dy) in enumerate(steps) if dt >= 50 and dy >= 0.4 * total]
        aside = max(held, key=lambda j: steps[j][1]) if held else None
        way = {round(t) for t in tops if tops[-1] + 1 < t < tops[0] - 1}
        steady = (all(dy >= -1 for _, dy in steps) and len(way) >= 3
                  and all(dy < 0.4 * total for j, (_, dy) in enumerate(steps) if j != aside))
        check(f"{name}: How it works rises in; its frame never scrolls",
              scrolled == 0, f"drawer scroll peaked at {scrolled}px over {len(frames)} frames")
        check(f"{name}: ...and the sheet travels up from the foot, no frame jumping 40% of the way",
              steady and total > 200, f"sheet top edge by frame: {[round(x) for x in tops]}"
              + (f"; set aside: {round(steps[aside][1])}px across a {round(steps[aside][0])}ms frame the box held" if aside is not None else ""))
        # ...AND NOTHING HOLDS IT UP WHILE IT DOES (main red after #571: the
        # sheet jumped 59% of the way in one frame on a busy runner). Opening
        # it rewrote every entry's More and read the next one's height, so the
        # style was worked out again once an entry, and again for each new
        # label lib/labels.js wrapped: 150 to 165 times, 120-170 ms in one go
        # here and about a second on a phone-slow processor, where the sheet
        # did not move at all. Counted, not timed, so a busy runner cannot
        # make it pass or fail: about one a frame is the rise itself.
        recalcs = round(recalc() - r0)
        check(f"{name}: ...and opening it does not work the page's style out again for every entry",
              recalcs < 100, f"{recalcs} style recalculations in the {len(frames)} frames it rises")
        ctx.close()

        # 7. on a phone with a panel open, How it works is still the SCREEN.
        # Photo/Music makes the page taller than the phone; the drawer was
        # positioned in .app, grew with it, and the examples sheet and the
        # full-screen example hung off the bottom (owner's iPhone, Pad).
        # Pad is opened the way a person does, from the menu with the panel
        # still open. Flip's menu shuts the panel first and Flip's .app does
        # not grow, so Flip cannot fail that scenario: it is opened directly,
        # and pinned by the property the fix governs, the drawer's position.
        # 600 tall: about what a small iPhone shows between Safari's bars.
        ctx = b.new_context(viewport={"width": 390, "height": 600}, has_touch=True)
        pg = ctx.new_page()
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(800)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        pg.click("#mediaOpenBtn"); pg.wait_for_timeout(900)
        tall = pg.evaluate("() => document.documentElement.scrollHeight - innerHeight")
        if name == "Pad":
            pg.evaluate("() => document.getElementById('menuBtn').click()"); pg.wait_for_timeout(500)
            pg.evaluate("() => document.getElementById('helpItem').click()"); pg.wait_for_timeout(800)
        else:
            pg.evaluate(OPEN); pg.wait_for_timeout(800)
        pg.evaluate(SHEET); pg.wait_for_timeout(900)
        pg.evaluate("() => document.querySelector('#helpWatch .learn-stage[role=button]').click()")
        pg.wait_for_timeout(900)
        seen = pg.evaluate("""() => { const r = e => { const b = e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; };
            const d = document.getElementById('helpDrawer');
            return { drawer: r(d), position: getComputedStyle(d).position,
                     example: r(document.getElementById('learnViewerStage')),
                     caption: r(document.querySelector('#learnViewer .learn-viewer-cap')), vh: innerHeight }; }""")
        check(f"{name}: (setup) with Photo/Music open the page is taller than a phone",
              tall > 100, f"{tall}px taller — without it the checks below prove nothing")
        check(f"{name}: How it works is pinned to the screen, not to the page",
              seen["position"] == "fixed", str(seen))
        check(f"{name}: on a phone with a panel open, How it works and its examples fill the screen, no more",
              seen["drawer"] == [0, seen["vh"]], str(seen))
        # Not asserted: "the example and its close button are wholly on screen".
        # In Chromium the old drawer still squeezed the caption on at 600 and
        # 664 tall (it is the iPhone's bars that pushed it off), so that check
        # stayed green on the broken tree and proved nothing. The two above went red.
        ctx.close()

    # 8. WHEN AN EXAMPLE CANNOT LOAD (outside audit V319-004). A failed
    # example got a class nothing drew: an empty tile, and a screen clip whose
    # video failed was not even marked. Cut the network to every example and
    # the sheet must say how many, in one banner a screen reader hears, with a
    # Retry that brings them back once the network does.
    FAILS = """() => {
        const box = document.getElementById('learnFail'), cards = [...document.querySelectorAll('#helpWatch .learn-card')];
        let painted = false;
        if (box && !box.hidden) { const r = box.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            painted = !!at && box.contains(at); }
        const a = document.activeElement;
        return { cards: cards.length, failed: cards.filter(c => c.classList.contains('learn-failed')).length,
                 shown: !!box && !box.hidden, painted,
                 said: (document.getElementById('learnFailCount') || {}).textContent || '',
                 status: (document.getElementById('learnFailCount') || { getAttribute() { return null; } }).getAttribute('role'),
                 players: cards.filter(c => c.hasAttribute('data-demo') && c._learnPlayer).length,
                 demos: cards.filter(c => c.hasAttribute('data-demo')).length,
                 clipsOk: [...document.querySelectorAll('#helpWatch .learn-video')]
                     .every(v => !!v.getAttribute('src') && !v.error),
                 body: a === document.body }; }"""
    print("\nWHEN AN EXAMPLE CANNOT LOAD")
    for name, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        ctx = b.new_context(viewport={"width": 1200, "height": 900}, color_scheme="dark")
        pg = ctx.new_page()
        cut = {"on": True}
        # ONE PARAMETER: Playwright passes the request as a second argument to
        # a handler that takes two, so a `cut=cut` default would receive it.
        def _mk_gate(cut):
            def _gate(r):
                if cut["on"]:
                    r.abort()
                else:
                    r.continue_()
            return _gate
        _gate = _mk_gate(cut)
        pg.route(re.compile(r"/help/(demos|clips)/[^?]*\.(json|mp4|webm)(\?.*)?$"), _gate)
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(800)
        pg.evaluate(OPEN); pg.wait_for_timeout(500)
        pg.evaluate(SHEET); pg.wait_for_timeout(1500)
        scroll_all(pg)
        # The banner heads the examples; read it where it is.
        pg.evaluate("() => document.getElementById('learnFail').scrollIntoView({ block: 'center', behavior: 'instant' })")
        pg.wait_for_timeout(300)
        f0 = pg.evaluate(FAILS)
        check(f"{name}: offline, every example is marked as not loaded -- the screen clips too",
              f0["cards"] > 10 and f0["failed"] == f0["cards"], str(f0))
        check(f"{name}: ...and one banner, painted on top, says how many",
              f0["shown"] and f0["painted"] and f0["said"] == f"{f0['cards']} examples couldn\u2019t load.", str(f0))
        check(f"{name}: ...in a status a screen reader announces", f0["status"] == "status", str(f0))
        cut["on"] = False
        # No button to press is a FAILURE to report, not a 30-second hang.
        if pg.query_selector("#learnRetry"):
            pg.focus("#learnRetry")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(4000)
        f1 = pg.evaluate(FAILS)
        if not pg.query_selector("#learnRetry"):
            f1["shown"], f1["body"] = "no Retry button", True
        check(f"{name}: Retry with the network back loads them: no banner, no failures, every replay playing, every clip fetched",
              not f1["shown"] and f1["failed"] == 0 and f1["players"] == f1["demos"] and f1["clipsOk"], str(f1))
        check(f"{name}: ...and focus, which was on the banner's Retry, does not fall to <body>",
              not f1["body"], str(f1))
        ctx.close()
        # ONE THAT FAILS AMONG MANY: the count is a count, not "offline".
        ctx = b.new_context(viewport={"width": 1200, "height": 900}, color_scheme="dark")
        pg = ctx.new_page()
        pg.route(re.compile(r"/help/demos/[^?]*\.json(\?.*)?$"),
                 lambda r: r.abort() if r.request.url.split("?")[0].endswith(_one[0]) else r.continue_())
        _one = [""]
        browsing.goto(pg, BASE, route)
        pg.wait_for_timeout(800)
        _one[0] = pg.evaluate("() => document.querySelector('#helpWatch .learn-card[data-demo]').getAttribute('data-demo').split('?')[0].split('/').pop()")
        pg.evaluate(OPEN); pg.wait_for_timeout(500)
        pg.evaluate(SHEET); pg.wait_for_timeout(1500)
        scroll_all(pg)
        f2 = pg.evaluate(FAILS)
        check(f"{name}: one example missing among many: \"1 example couldn\u2019t load.\" and the rest play",
              f2["failed"] == 1 and f2["said"] == "1 example couldn\u2019t load." and f2["players"] == f2["demos"] - 1,
              f"{f2} (cut {_one[0]})")
        ctx.close()
    b.close()

passed = sum(1 for r in results if r[0])
bad = [r[1] for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
