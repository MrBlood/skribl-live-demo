"""The profile's Skribls tab: real posts, one payload at a time, one player.

/library used to be a MOCK. It carried its own replay engine and a table of
hand-drawn motifs, and rendered those — nothing on it had ever been posted by
anyone, while it was registered as a real route that a host mounting Skribl got
in their own URL space. README.md carried a warning saying so.

That is the shape of thing this harness exists to refuse, and the reason is not
the pretending: a page that draws its own content cannot tell you whether the
thing it previews WORKS. This suite is what replaced the warning.

THREE PROPERTIES, in the order they matter:

  1. IT PLAYS REAL POSTS. Fixtures are recorded in Pad and posted through the
     API; the page reads GET /api/skribls and plays what comes back.
  2. IT IS NOT A THIRD PLAYER. The stage is inlineplayer.js — the same one the
     feed and a host's composer use — driven through the handle it exposes.
     Three replay implementations would drift, and verify_sharedrules.py's note
     says what that costs: nothing an author can see reveals it.
  3. IT FETCHES ONE PAYLOAD AT A TIME. The grid is share-card images. Fifty
     mounted players each holding a payload is tens of megabytes for a page of
     thumbnails, which is the exact cost GET /api/skribls returns metadata to
     avoid.
"""
import json
import math
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the library works.")
    raise SystemExit(77)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


POST_PUBLIC = """async (title) => {
  const p = serializeSkribl();
  p.title = title;
  p.visibility = 'public';
  const r = await fetch(window.SKRIBL_API_BASE, {
    method: 'POST', headers: skriblPostHeaders(), body: JSON.stringify(p) });
  return r.ok ? await r.json() : { error: r.status };
}"""


def post_one(b, title, turns=4):
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(70):
        t = i / 70
        pg.mouse.move(cx + math.cos(t * math.pi * turns) * (25 + t * 140),
                      cy + math.sin(t * math.pi * turns) * (25 + t * 110))
        if i % 5 == 0:
            pg.wait_for_timeout(90)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    res = pg.evaluate(POST_PUBLIC, title)
    pg.close()
    return (res or {}).get("id")


with sync_playwright() as sp:
    b = sp.chromium.launch()

    # UNIQUE PER RUN. run_harness.sh gives one server and one database to every
    # suite in an invocation, so the search assertion below was matching
    # verify_inline.py's "Harness fixture A" as well as this suite's own — two
    # tiles where it wanted one, intermittently, depending on which suites ran.
    # Exactly the cross-suite state START-HERE.md warns passes the seal and
    # fails CI. A token nothing else can produce makes the query this suite's.
    tag = "lib" + os.urandom(4).hex()
    ids = [post_one(b, tag + " alpha", 4), post_one(b, tag + " beta", 2)]
    if not all(ids):
        check("two public skribls posted (fixture)", False, str(ids))
        print("\n" + "=" * 62 + "\n0/1 passed")
        sys.exit(1)
    check("two public skribls posted (fixture)", True, ", ".join(ids))

    pg = b.new_page(viewport={"width": 1280, "height": 1000})
    errs = []
    payload_reqs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: payload_reqs.append(r.url)
          if re.search(r"/api/skribls/[A-Za-z0-9_-]+$", r.url) else None)
    pg.goto(BASE + "/library", wait_until="load")
    pg.wait_for_timeout(3000)

    tiles = pg.evaluate("() => document.getElementById('grid').children.length")
    check("the grid is built from GET /api/skribls, not from demo motifs",
          tiles >= 2, f"{tiles} tiles")
    check("no page errors", not errs, "; ".join(errs[:2]))

    # ONE PAYLOAD, for the one drawing on the stage. Not one per tile.
    check("only the selected Skribl's payload is fetched",
          len(payload_reqs) == 1,
          f"{len(payload_reqs)} payload fetch(es) for {tiles} tiles: "
          f"{payload_reqs}")
    check("every tile's picture is the share card, which is one cached image",
          pg.evaluate("""() => [...document.querySelectorAll('.card .art img')]
             .every(i => /\\/s\\/[^/]+\\/card\\.png$/.test(i.getAttribute('src')))"""))

    # ---- the stage IS the in-post player -----------------------------------
    st = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline && window.SkriblInline.players()
                   .filter(x => x.el === el)[0];
        return p ? p.state() : null; }""")
    check("the stage is an inlineplayer instance, not a second replay engine",
          st is not None and st["loaded"] is True, json.dumps(st))
    check("it loaded a real drawing with a real duration",
          st and st["totalMs"] > 300, f"totalMs={st and st['totalMs']}")

    title0 = pg.inner_text("#pTitle")
    check("the newest Skribl is on the stage", title0.strip() != "—", title0)

    # ---- the transport -----------------------------------------------------
    pg.click("#btnPlay")
    pg.wait_for_timeout(900)
    moving = pg.evaluate("""() => ({
        frac: parseFloat(document.getElementById('scrubFill').style.width) || 0,
        label: document.getElementById('tElapsed').textContent })""")
    check("play advances the scrub and the clock",
          0 < moving["frac"] < 100 and not moving["label"].startswith("0:00 /"),
          json.dumps(moving))
    # The transport reads the PLAYER's clock. Two clocks is two answers to "how
    # far through is it", and the one on screen would be the wrong one.
    live = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline.players().filter(x => x.el === el)[0].state();
        const shown = parseFloat(document.getElementById('scrubFill').style.width) || 0;
        return { player: p.totalMs ? p.elapsedMs / p.totalMs * 100 : 0, shown: shown }; }""")
    check("the scrub shows the player's own clock rather than one of its own",
          abs(live["player"] - live["shown"]) < 12,
          f"player {live['player']:.1f}% vs shown {live['shown']:.1f}%")

    pg.click("#btnPlay")
    pg.wait_for_timeout(500)
    paused = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0]
                 .state().state; }""")
    check("play/pause is a toggle", paused == "paused", paused)

    pg.click("#btnRestart")
    pg.wait_for_timeout(300)
    pg.click("#btnPlay")            # restart plays; this pauses it again
    pg.wait_for_timeout(200)
    restarted = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0]
                 .state().elapsedMs; }""")
    check("restart goes back to the beginning",
          restarted < 900, f"elapsedMs={restarted:.0f}")

    # Scrub: click three-quarters along and the player must be there.
    pg.evaluate("""() => {
        const s = document.getElementById('scrub');
        const r = s.getBoundingClientRect();
        s.dispatchEvent(new MouseEvent('click', {
          clientX: r.left + r.width * 0.75, clientY: r.top + r.height / 2,
          bubbles: true })); }""")
    pg.wait_for_timeout(300)
    sought = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        const p = window.SkriblInline.players().filter(x => x.el === el)[0].state();
        return p.totalMs ? p.elapsedMs / p.totalMs : -1; }""")
    check("the scrub track seeks the drawing",
          0.6 < sought < 0.9, f"landed at {sought:.2f} of the replay")

    # A post has no loop toggle (inlineplayer.css says why); a page ABOUT one
    # does, because somebody looking at a single drawing may want it to stop.
    pg.click("#btnLoop")
    pg.wait_for_timeout(100)
    pg.click("#btnRestart")
    pg.wait_for_timeout(4000)
    ended = pg.evaluate("""() => {
        const el = document.getElementById('stageBox');
        return window.SkriblInline.players().filter(x => x.el === el)[0].state(); }""")
    check("with loop off the replay stops at the end instead of going round",
          ended["state"] != "playing"
          and ended["elapsedMs"] >= ended["totalMs"] - 60,
          json.dumps(ended))

    # ---- picking another one -----------------------------------------------
    before = len(payload_reqs)
    pg.evaluate("() => document.getElementById('grid').children[1].click()")
    pg.wait_for_timeout(2500)
    title1 = pg.inner_text("#pTitle")
    check("picking a tile puts that Skribl on the stage",
          title1.strip() != title0.strip(), f"{title0.strip()!r} -> {title1.strip()!r}")
    check("and fetches exactly one more payload",
          len(payload_reqs) == before + 1,
          f"{len(payload_reqs) - before} fetch(es)")

    # ---- search says what it is doing --------------------------------------
    pg.fill("#search", tag + " alpha")
    # WAIT FOR THE FILTER, do not sleep at it. The grid re-renders on `input`,
    # and a fixed pause raced it: this read 2 tiles on one run and 1 on the next
    # with the same code, which is a flaky assertion rather than a finding.
    try:
        pg.wait_for_function(
            "() => document.getElementById('grid').children.length === 1",
            timeout=4000)
    except Exception:
        pass
    filtered = pg.evaluate("() => document.getElementById('grid').children.length")
    typed = pg.evaluate("() => document.getElementById('search').value")
    foot = pg.inner_text("#libFoot")
    check("the search filters the grid", filtered == 1,
          f"{filtered} tiles for {typed!r}")
    check("and says it is filtering only what has been LOADED",
          "loaded" in foot.lower(),
          f"{foot!r} — the listing is keyset-paginated and the API has no "
          f"search, so a box that looked like it searched everything would lie")
    pg.close()

    # ---- the source gates --------------------------------------------------
    src = (ROOT / "skribl" / "static" / "library.js").read_text(encoding="utf-8")
    check("library.js contains no replay loop of its own",
          "requestAnimationFrame" not in src,
          "the stage is inlineplayer.js; a second rAF loop here would be a "
          "third implementation of playback")
    check("it drives the shared player through the exposed handle",
          "SkriblInline.attach" in src and ".seek(" in src and ".setLoop(" in src)
    # KEYSET, not offset. list_skribls() is explicit about why: OFFSET makes the
    # database walk and discard every skipped row, and a post created mid-scroll
    # shifts every later page.
    # A PARAMETER, not the word. Both of these gates were substring searches
    # first and both passed on their own prose — this file's header names the
    # motifs it replaced, and the paging comment explains why OFFSET is wrong.
    # That is the failure a v273 gate already made once (it searched for
    # "Pillow" and matched a comment mentioning it), so: match the syntax.
    check("paging uses the cursor the server hands back, never an offset",
          "next_cursor" in src and "cursor=" in src and "offset=" not in src)
    # And the DOCS, which described this page as demo tiles for as long as it
    # was one. A page that stops lying while its documentation keeps saying the
    # old thing has moved the lie, not removed it.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    integration = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
    stale = [n for n, t in (("README.md", readme), ("docs/INTEGRATION.md", integration))
             if "demo tiles" in t or "demo drawings" in t
             or "self-contained demo" in t.lower()]
    check("no document still calls /library a page of demo tiles",
          not stale, ", ".join(stale))

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
