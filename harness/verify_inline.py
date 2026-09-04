"""The in-post player: does it play a REAL Skribl, and does it agree with /s/<id>?

A Skribl inside somebody else's feed is a second playback implementation
(skribl/static/inlineplayer.js — its header says why it is not the sealed
player). verify_sharedrules.py already names the shape of the risk this creates:

    "the EDITOR and the PLAYER disagreeing is uniquely expensive, because
     nothing an author can see reveals it. The preview is not the product."

A FEED player that disagrees is the same defect one surface further out — the
author opens the share link, it looks right, and every viewer scrolling past
sees something else. So this suite is built the way that one is: what it asserts
is not shared code but that the two cannot disagree about the ANSWER. Both play
the same posted drawing, from the same clock, and are compared to each other.

The fixture is a real recording posted through the API, for the reason
verify_player_isolation.py records learning the hard way: a hand-built payload
rendered nothing and looked exactly like a broken player. Everything here goes
through /skribl-pad, #postBtn, and GET /api/skribls.

WHAT IS DELIBERATELY NOT ASSERTED. The wet/dry stroke compositor is not
implemented in the in-post player, so a translucent stroke beads there and does
not on /s/<id>. The comparison fixture below draws OPAQUE, which keeps the pixel
assertion meaningful rather than quietly tolerant of a gap it cannot see; the
gap itself is named in inlineplayer.js. If the compositor is ever ported, widen
the fixture here rather than loosening the tolerance.
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
    print("No assertions were executed. This is NOT evidence the feed player works.")
    raise SystemExit(77)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def scribble(pg, box, n=110):
    """Draw over about three seconds of WALL CLOCK.

    Same reason verify_player_isolation.py's version says so: strokes carry
    timestamps, and a drawing made as fast as the mouse moves replays in under a
    second — over before anything can be sampled mid-flight. Everything below
    that compares the two players at a shared moment depends on there being a
    moment to share.
    """
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * 110
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 5 == 0:
            pg.wait_for_timeout(120)
    pg.mouse.up()


# POSTED PUBLIC, THROUGH THE PAGE, AND WHY IT IS NOT #postSubmitBtn.
#
# `POST /api/skribls` defaults to visibility "unlisted" (skribl/routes.py: "that
# is exactly what a link-sharing product should default to") and the Pad's
# composer has no visibility control, so EVERY post the composer makes is
# invisible to GET /api/skribls. A fixture built by clicking #postSubmitBtn
# therefore produces a feed page with nothing on it, and this suite would be
# asserting against an empty list — which is how it first ran.
#
# So the recording is real — a genuine take in Pad, with real per-point
# timestamps, which is the whole reason the two players can be compared on
# timing at all — and only the ENVELOPE is built here: serializeSkribl() is the
# same function the composer serialises, and the request carries the page's own
# CSRF header through skriblPostHeaders(). What is not exercised is the
# composer's post-time work (the share-card thumbnail and the mono audio bake),
# so these fixtures' posters fall back to the generic branded card — a path the
# in-post player has to survive anyway, and one this suite asserts.
POST_PUBLIC = """async (title) => {
  const p = serializeSkribl();
  p.title = title;
  p.visibility = 'public';
  const r = await fetch(window.SKRIBL_API_BASE, {
    method: 'POST', headers: skriblPostHeaders(), body: JSON.stringify(p) });
  if (!r.ok) return { error: r.status + ' ' + (await r.text()).slice(0, 200) };
  return await r.json();
}"""


def post_one(b, title):
    """Record a drawing in Pad and post it PUBLICLY. Returns its public id."""
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    scribble(pg, pg.locator("#canvas").bounding_box())
    pg.wait_for_timeout(600)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    res = pg.evaluate(POST_PUBLIC, title)
    pg.close()
    if not isinstance(res, dict) or not res.get("id"):
        errs.append(str(res))
        return None, errs
    return res["id"], errs


# A 96x96 grayscale reduction of a canvas. Comparing the two players' canvases
# directly is not possible — the sealed player fits the drawing to its column
# and the in-post player renders at the payload's own logical size, so the
# bitmaps differ in both dimensions and in device-pixel ratio. Downscaling both
# to the same small grid compares WHAT IS DRAWN rather than how many pixels it
# happens to occupy, which is the only comparison that means anything across two
# different fits.
GRID = """(sel) => {
  const c = document.querySelector(sel);
  if (!c || !c.width || !c.height) return null;
  const g = document.createElement('canvas'); g.width = 96; g.height = 96;
  const gx = g.getContext('2d');
  gx.fillStyle = '#000'; gx.fillRect(0, 0, 96, 96);
  gx.drawImage(c, 0, 0, 96, 96);
  const d = gx.getImageData(0, 0, 96, 96).data;
  const out = [];
  for (let i = 0; i < d.length; i += 4)
    out.push(Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]));
  return out;
}"""


def grid_diff(a, b, tol=18):
    """Cells whose ink differs by more than `tol`, each grid read against its
    OWN ground.

    The subtraction is not a fudge, it is the only correct comparison here: the
    two surfaces put the drawing's background in different places. The in-post
    player paints the payload's background colour onto the canvas itself; the
    sealed player leaves the canvas transparent and paints the ground on
    .canvas-wrap behind it. Compared absolutely, every one of the 2,304 cells
    differs by the background level and the assertion is about paint order
    rather than about the drawing. Floor-subtracted, it is about the ink.
    """
    fa, fb = min(a), min(b)
    return sum(1 for x, y in zip(a, b) if abs((x - fa) - (y - fb)) > tol)


with sync_playwright() as sp:
    b = sp.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    # ---- fixture: two real posts -------------------------------------------
    id_a, errs_a = post_one(b, "Harness fixture A")
    id_b, errs_b = post_one(b, "Harness fixture B")
    if not id_a or not id_b:
        check("two drawings posted through the API (fixture)", False,
              f"got {id_a!r}, {id_b!r}; errors: {(errs_a + errs_b)[:2]}")
        print("\n" + "=" * 62 + "\n0/1 passed")
        sys.exit(1)
    check("two drawings posted through the API (fixture)", True, f"{id_a}, {id_b}")

    # ---- the macro's server-rendered markup --------------------------------
    # Before any script runs, a post must already be something. This is the
    # reason _skribl_inline_player.html renders markup instead of letting
    # inlineplayer.js create it: a host page with the script blocked, or simply
    # not arrived yet, shows the drawing's card and a play affordance rather
    # than an empty rectangle where a post should be.
    feed_html = urllib.request.urlopen(BASE + "/feed", timeout=20).read().decode()
    check("the feed page server-renders the poster before any script runs",
          "skribl-inline-poster" in feed_html and "/card.png" in feed_html)
    check("the feed page server-renders the play affordance",
          "skribl-inline-play" in feed_html)
    check("the in-post markup carries the listing endpoint from url_for, "
          "not a literal path",
          'data-skribl-api="/api/skribls"' in feed_html,
          "a hardcoded path breaks every host that mounts under a url_prefix")

    # THE POINT OF A SEPARATE PLAYER. If the feed page pulls app.js in anyway,
    # every one of the reasons inlineplayer.js exists has evaporated and the
    # honest move would be to delete it and iframe /s/<id>.
    for heavy in ("app.js", "flip.js", "styles.css", "player.css"):
        check(f"the feed page does not load {heavy}",
              not re.search(r'src="[^"]*/' + re.escape(heavy) + r'[?"]', feed_html)
              and not re.search(r'href="[^"]*/' + re.escape(heavy) + r'[?"]', feed_html))

    # ---- the feed itself ---------------------------------------------------
    pg = b.new_page(viewport={"width": 620, "height": 900})
    errs = []
    payload_reqs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: payload_reqs.append(r.url)
          if re.search(r"/api/skribls/[A-Za-z0-9_-]+$", r.url) else None)
    pg.goto(BASE + "/feed", wait_until="load")
    pg.wait_for_timeout(1500)

    mounted = pg.evaluate("() => window.SkriblInline ? window.SkriblInline.players().length : -1")
    check("the feed mounts one in-post player per listed Skribl",
          mounted >= 2, f"{mounted} mounted")
    check("no page errors on the feed", not errs, "; ".join(errs[:2]))

    # NOTHING FETCHES UNTIL SOMEBODY ASKS. GET /api/skribls/<id> returns the
    # WHOLE payload including base64 audio; a feed that prefetched a screenful
    # of those would move tens of megabytes to render thumbnails. This is the
    # assertion that stops a well-meaning "preload the visible ones" change.
    check("an idle post has fetched no payload",
          not payload_reqs, f"{len(payload_reqs)} payload request(s) before any play")
    st = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_a)
    check("an idle post reports itself unloaded and idle",
          st and st["state"] == "idle" and st["loaded"] is False, json.dumps(st))

    # ---- play --------------------------------------------------------------
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_a)
    # MID-REPLAY, deliberately. The fixture runs about 2.6 seconds and the
    # in-post player loops, so sampling near the end reads a progress bar that
    # is either ~97% or has just wrapped to ~2% — and an assertion that accepts
    # both is an assertion that accepts anything.
    pg.wait_for_timeout(1200)
    st = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_a)
    check("tapping a post loads its payload and plays it",
          st and st["state"] == "playing" and st["loaded"] is True, json.dumps(st))
    check("the payload was fetched exactly once, for the post that was tapped",
          len(payload_reqs) == 1 and payload_reqs[0].endswith(id_a),
          str(payload_reqs))
    check("the replay has a real duration taken from the payload's own timeline",
          st and st["totalMs"] > 500, f"totalMs={st and st['totalMs']}")

    # Counting non-transparent pixels would pass on a canvas holding nothing but
    # the drawing's background colour — which is exactly what an empty replay
    # paints. Count pixels that differ from the corner instead, so this measures
    # STROKES and not a flood fill.
    ink = pg.evaluate("""(id) => {
        const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        const br = d[0], bg = d[1], bb = d[2], ba = d[3];
        let n = 0;
        for (let i = 0; i < d.length; i += 4)
          if (Math.abs(d[i] - br) + Math.abs(d[i+1] - bg)
              + Math.abs(d[i+2] - bb) + Math.abs(d[i+3] - ba) > 24) n++;
        return n; }""", id_a)
    check("the drawing itself is on the canvas, not just a ground colour",
          ink > 500, f"{ink} pixels differ from the background")

    chrome = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const prog = el.querySelector('.skribl-inline-prog');
        const nib = el.querySelector('.skribl-inline-nib');
        return { playing: el.classList.contains('is-playing'),
                 progPct: parseFloat(prog.style.width) || 0,
                 nib: parseFloat(getComputedStyle(nib).opacity) }; }""", id_a)
    check("the progress hairline advances during playback",
          0 < chrome["progPct"] < 100, f"{chrome['progPct']}%")
    check("the nib is visible at the drawing head during playback",
          chrome["nib"] > 0.5, str(chrome["nib"]))
    check("the box is in its playing state, so the poster and veil are gone",
          chrome["playing"] is True)

    # ---- one at a time -----------------------------------------------------
    # A feed that can play two loops at once is a feed nobody scrolls twice.
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_b)
    pg.wait_for_timeout(2500)
    a_after = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_a)
    b_after = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_b)
    check("starting one Skribl settles every other one on the page",
          a_after["state"] == "idle" and b_after["state"] == "playing",
          f"a={a_after['state']} b={b_after['state']}")
    # Settled, not paused: a displaced post goes back to being a post rather
    # than sitting frozen mid-stroke behind a play button.
    check("a displaced post returns to zero rather than freezing mid-stroke",
          a_after["elapsedMs"] == 0, str(a_after["elapsedMs"]))

    # ---- sound -------------------------------------------------------------
    check("sound is off by default", b_after["muted"] is True)
    pg.evaluate("() => window.SkriblInline.setSoundOn(true)")
    pg.wait_for_timeout(200)
    both = pg.evaluate("() => window.SkriblInline.players().map(p => p.state().muted)")
    check("unmuting is a page-wide choice, not a per-post one",
          both and not any(both), str(both))
    persisted = pg.evaluate("() => sessionStorage.getItem('skribl.inline.sound')")
    check("the sound choice is remembered for the SESSION, not forever",
          persisted == "1" and pg.evaluate("() => localStorage.getItem('skribl.inline.sound')") is None,
          f"session={persisted!r}")

    # ---- scrolling away ----------------------------------------------------
    pg.evaluate("""() => {
        const spacer = document.createElement('div');
        spacer.style.height = '250vh';
        document.body.appendChild(spacer);
        window.scrollTo(0, document.body.scrollHeight); }""")
    pg.wait_for_timeout(1200)
    scrolled = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_b)
    check("scrolling a playing post out of view settles it",
          scrolled["state"] == "idle",
          f"{scrolled['state']} — a feed that keeps drawing off-screen burns "
          f"battery for nobody")

    # ---- a post that cannot load ------------------------------------------
    bad = pg.evaluate("""() => {
        const el = document.querySelector('[data-skribl-inline]').cloneNode(true);
        el.setAttribute('data-skribl-id', 'zzzznotreal');
        el.id = 'badbox';
        document.body.appendChild(el);
        window.SkriblInline.mount(document.body);
        el.click();
        return true; }""")
    pg.wait_for_timeout(2500)
    bad_state = pg.evaluate("""() => {
        const el = document.getElementById('badbox');
        const err = el.querySelector('.skribl-inline-err');
        return { hidden: err.hidden, text: err.textContent }; }""")
    check("a Skribl that will not load says so instead of sitting dead",
          bad_state["hidden"] is False and bad_state["text"].strip() != "",
          json.dumps(bad_state))
    pg.close()

    # ---- AGREEMENT WITH THE SEALED PLAYER ----------------------------------
    # The whole reason this suite exists. Both surfaces play the same posted
    # drawing from a standing start; sampled at the same elapsed wall-clock
    # time, they must be at the same point in the replay and must have drawn
    # the same thing. Disagreement here means the timeline logic retyped in
    # inlineplayer.js has drifted from app.js's buildPlaybackTimeline — which
    # is precisely the failure nothing an author can see would reveal.
    SAMPLE_MS = 1500

    p1 = b.new_page(viewport={"width": 1280, "height": 900})
    p1.goto(BASE + "/s/" + id_a, wait_until="load")
    p1.wait_for_timeout(3500)
    p1.click("#playerPlayBtn")
    p1.wait_for_timeout(SAMPLE_MS)
    player_grid = p1.evaluate(GRID, "#canvas")
    player_frac = p1.evaluate("""() => {
        const f = document.getElementById('playerProgressFill');
        return f ? (parseFloat(f.style.width) || 0) / 100 : null; }""")
    p1.close()

    p2 = b.new_page(viewport={"width": 620, "height": 900})
    p2.goto(BASE + "/feed", wait_until="load")
    p2.wait_for_timeout(1500)
    p2.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_a)
    # The tap issues a fetch before the first frame; wait for the payload to
    # land, then time the sample from the moment playback actually begins.
    p2.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'",
                         arg=id_a, timeout=15000)
    # Restart from a standing start: wait_for_function polls, so by the time it
    # returns the replay is already some hundreds of milliseconds in, and
    # sampling from there would compare two different points.
    p2.evaluate("(id) => { window.SkriblInline.find(id).settle(); "
                "document.querySelector('[data-skribl-id=\"' + id + '\"]').click(); }", id_a)
    p2.wait_for_timeout(SAMPLE_MS)
    inline_state = p2.evaluate("(id) => window.SkriblInline.find(id).state()", id_a)
    # SELECTED BY ID, not by class. `.skribl-inline-canvas` matches the FIRST
    # post in the feed, which is not necessarily the one being played — and an
    # idle post's canvas is blank, so the comparison silently ran against an
    # empty bitmap and passed. Found by mutation: replaying at a deliberately
    # wrong gap cap left this assertion green.
    inline_grid = p2.evaluate(GRID, f'[data-skribl-id="{id_a}"] .skribl-inline-canvas')
    p2.close()

    inline_frac = (inline_state["elapsedMs"] / inline_state["totalMs"]
                   if inline_state["totalMs"] else None)
    def _pct(v):
        return "unreadable" if v is None else f"{v:.3f}"

    check("both players report the same point in the replay at the same moment",
          player_frac is not None and inline_frac is not None
          and abs(player_frac - inline_frac) < 0.12,
          f"/s/<id> {_pct(player_frac)} vs in-post {_pct(inline_frac)} — a gap "
          f"here means the capped-gap timeline has drifted from app.js's")

    def ink_mass(g):
        """How much of the drawing is on the canvas, scale-free.

        The cell-by-cell diff below answers "is it the same picture"; this
        answers "is the same AMOUNT of it drawn yet", which is the question a
        timing drift actually changes. A drawing that is 34% replayed and one
        that is 58% replayed are the same picture as far as a downscaled grid is
        concerned — thin lines average back toward the ground — but they carry
        visibly different ink, and that is what caught the deliberately-wrong
        gap cap this fixture was mutation-tested with.
        """
        floor = min(g)
        return sum(v - floor for v in g)

    if player_grid and inline_grid:
        diff = grid_diff(player_grid, inline_grid)
        mp, mi = ink_mass(player_grid), ink_mass(inline_grid)
        ratio = (min(mp, mi) / max(mp, mi)) if max(mp, mi) else 0
        check("both players have drawn the same AMOUNT of the drawing",
              ratio >= 0.80,
              f"ink {mp} vs {mi} (ratio {ratio:.2f}) — a low ratio means one "
              f"player is further through the replay than the other")
        # 9,216 cells, brightness tolerance 18, budget 24. EVERY ONE OF THOSE
        # NUMBERS WAS MEASURED BY MUTATION, because the first set was not and
        # was worthless:
        #
        #   32x32 @ tol 48, budget 140   passed with the in-post player reading
        #                                a BLANK canvas (the selector matched the
        #                                first post, not the one playing) and
        #                                passed again with the gap cap set to
        #                                500 ms — the two players 0.58 and 0.34
        #                                through the same drawing.
        #   96x96 @ tol 18               displacing every stroke by 30 px (3.7%
        #                                of the canvas) moves 75 cells; an
        #                                unmutated run moves 1.
        #
        # 24 sits between those two figures. What it has to absorb is the two
        # different fits — the sealed player scales the drawing to its column,
        # the in-post player renders at the payload's logical size — and a few
        # milliseconds of jitter between two independently clocked replays.
        check("both players have drawn the same thing at that moment",
              diff <= 24, f"{diff}/9216 cells differ beyond tolerance")
    else:
        check("both players have drawn the same thing at that moment", False,
              "a canvas could not be read")

    # ---- FLIP, AND THE THING lib/holdtiming.js EXISTS TO PROTECT -----------
    #
    # Loading holdtiming.js proves nothing on its own: a surface can load a
    # module and still answer the question itself, which is how flip.js and
    # app.js came to disagree about which page is on screen at time t. So this
    # posts a flip document whose pages have DIFFERENT HOLDS and asserts the
    # in-post player shows the page the module says it should — the drawing must
    # not change inside a hold, and must change at the boundary.
    #
    # 6 fps, holds 2/4/2 — 8 units of 166.7 ms:
    #     page 0   0 - 333 ms      page 1   333 - 1000 ms   page 2  1000 - 1333 ms
    # A player that ignored holds would give each page a third of the run and
    # put page 1 at 500 ms boundaries that are nowhere near these.
    def post_flip(title):
        pts = [{"x": 120 + i * 40, "y": 140, "color": "#ffffff", "size": 14,
                "t": i * 4, "erase": False, "start": i == 0} for i in range(8)]

        def frame(dy, hold):
            return {"strokes": [dict(q, y=q["y"] + dy) for q in pts],
                    "strokeGroups": [len(pts)], "hold": hold}

        body = {"title": title, "visibility": "public", "version": 2,
                "schemaVersion": 2, "playbackMode": "flip", "fps": 6,
                "frames": [frame(0, 2), frame(180, 4), frame(360, 2)],
                "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
        req = urllib.request.Request(BASE + "/api/skribls",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    flip_id = None
    try:
        flip_id = post_flip("Harness flip fixture")["id"]
    except Exception as exc:
        check("a flip document was posted (fixture)", False, f"{type(exc).__name__}: {exc}")
    if flip_id:
        check("a flip document was posted (fixture)", True, flip_id)
        fp = b.new_page(viewport={"width": 620, "height": 900})
        fp.goto(BASE + "/feed", wait_until="load")
        fp.wait_for_timeout(1500)
        fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", flip_id)
        fp.wait_for_function("(id) => window.SkriblInline.find(id).state().loaded",
                             arg=flip_id, timeout=15000)
        fst = fp.evaluate("(id) => window.SkriblInline.find(id).state()", flip_id)
        check("a flip document is recognised as a flip, not replayed as strokes",
              fst["kind"] == "flip", json.dumps(fst))

        expected = fp.evaluate("() => window.SkriblHold.durationMs([2, 4, 2], 6)")
        check("the flip's duration is the one lib/holdtiming.js computes",
              abs(fst["totalMs"] - expected) < 1,
              f"player {fst['totalMs']} vs module {expected}")

        def at(ms):
            fp.evaluate("([id, t]) => window.SkriblInline.find(id).seek(t)", [flip_id, ms])
            fp.wait_for_timeout(120)
            return fp.evaluate(GRID, f'[data-skribl-id="{flip_id}"] .skribl-inline-canvas')

        g_early, g_late_p0 = at(80), at(280)
        g_p1, g_p2 = at(600), at(1150)
        check("the page does not change inside its own hold",
              grid_diff(g_early, g_late_p0) == 0,
              "80 ms and 280 ms are both inside page 0's two-unit hold")
        check("the page changes at the hold boundary",
              grid_diff(g_late_p0, g_p1) > 20,
              "280 ms is page 0 and 600 ms is page 1")
        check("a later hold boundary advances again",
              grid_diff(g_p1, g_p2) > 20,
              "600 ms is page 1 and 1150 ms is page 2")
        fp.close()

    # ---- the rules that must not be retyped --------------------------------
    # lib/holdtiming.js exists so the Flip editor and the player cannot disagree
    # about which page is on screen at time t (see its header). A third surface
    # that re-derives that from frames and fps would be the same bug a third
    # time, and it would be invisible until somebody posted a flip with a hold.
    src = (ROOT / "skribl" / "static" / "inlineplayer.js").read_text(encoding="utf-8")
    check("the in-post player reads per-page holds from lib/holdtiming.js",
          "SkriblHold" in src,
          "the rule lives in lib/, and this is the third surface to read it")
    check("the in-post player does not define its own hold clamp",
          "MAX_HOLD" not in src,
          "a second clamp is how flip.js and app.js disagreed in the first place")
    check("the in-post player reads the default canvas size from "
          "lib/canvassizes.js",
          "SkriblCanvasSizes" in src)
    assets = (ROOT / "skribl" / "templates" / "skribl"
              / "_skribl_inline_player.html").read_text(encoding="utf-8")
    for lib in ("lib/holdtiming.js", "lib/canvassizes.js"):
        check(f"the embed macro actually loads {lib}", lib in assets,
              "reading a global nothing loads is a silent fallback, not a shared rule")

    # ---- THE POSTER CROP, MEASURED AGAINST THE MODULE THAT DEFINES IT ------
    #
    # The idle poster is /s/<id>/card.png with its brand strip cropped off, and
    # the crop lives in inlineplayer.css as two percentages. A stylesheet cannot
    # read a JavaScript module, so those two numbers are the one place this
    # design can silently drift from the card editor_post.js actually
    # composites. Rather than regex the CSS, measure what the browser RENDERED
    # and compare it to lib/sharecard.js's own arithmetic: if the card's layout
    # moves and only one side is updated, this fails.
    cp = b.new_page(viewport={"width": 620, "height": 900})
    cp.goto(BASE + "/feed", wait_until="load")
    cp.wait_for_timeout(1500)
    geom = cp.evaluate("""() => {
        const el = document.querySelector('.skribl-inline');
        const img = el.querySelector('.skribl-inline-poster');
        const box = el.getBoundingClientRect(), pr = img.getBoundingClientRect();
        // The poster's percentage height and top resolve against the PADDING
        // box, not the border box — the box carries a 1px border, which is
        // enough to put a ratio 0.9% out and read as a drift that is not there.
        const h = el.clientHeight, w = el.clientWidth;
        const band = window.SkriblShareCard.band();
        return { boxAspect: box.width / box.height,
                 wantAspect: band.aspect,
                 scale: pr.height / h, wantScale: band.scale,
                 offset: (box.top - pr.top) / h,
                 wantOffset: band.offset }; }""")
    # THE BOX MUST NOT BE NARROWER THAN THE WIDEST CANVAS A DRAWING CAN HAVE.
    # The side crop is symmetric and the drawing is centred in the card, so it
    # can only ever remove the card's dark ground — UNTIL the box is narrower
    # than the drawing, at which point it starts cutting the picture. Nothing
    # about that failure is loud: a wide drawing simply loses its edges in the
    # feed and looks fine in the player. Asserted against lib/canvassizes.js, so
    # adding a wider preset fails here rather than there.
    widest = cp.evaluate("""() => {
        const S = window.SkriblCanvasSizes.SIZES;
        return Math.max.apply(null, S.map(s => s.w / s.h)); }""")
    check("the in-post box is at least as wide as the widest canvas preset, so "
          "the side crop can never cut a drawing",
          geom["boxAspect"] >= widest - 0.005,
          f"box {geom['boxAspect']:.4f} vs widest preset {widest:.4f}")
    check("and no wider than the card's band, so it is not showing dead ground",
          geom["boxAspect"] <= geom["wantAspect"] + 0.005,
          f"box {geom['boxAspect']:.4f} vs band {geom['wantAspect']:.4f}")
    check("the poster is scaled by exactly what lib/sharecard.js says",
          abs(geom["scale"] - geom["wantScale"]) < 0.01,
          f"{geom['scale']:.4f} vs {geom['wantScale']:.4f}")
    check("the poster is offset by exactly what lib/sharecard.js says, so the "
          "brand strip lands outside the box",
          abs(geom["offset"] - geom["wantOffset"]) < 0.01,
          f"{geom['offset']:.4f} vs {geom['wantOffset']:.4f}")

    # AND THE SAME NUMBERS ON THE OTHER SIDE. editor_post.js composites the card
    # from this module too; if it stopped, the crop would be measuring a
    # rectangle nothing puts the drawing in.
    ep = (ROOT / "skribl" / "static" / "editor_post.js").read_text(encoding="utf-8")
    check("editor_post.js composites the card from lib/sharecard.js",
          "SkriblShareCard" in ep,
          "otherwise the two sides derive the same rectangle independently")
    for tpl, label in ((["skribl_editor.html"], "Pad"), (["skribl_flip.html"], "Flip")):
        body = (ROOT / "skribl" / "templates" / "skribl" / tpl[0]).read_text(encoding="utf-8")
        check(f"{label} loads lib/sharecard.js, so the composite uses it",
              "lib/sharecard.js" in body)
    cp.close()

    # ---- what a host downloads --------------------------------------------
    # A RATCHET, in the same spirit as verify_player_isolation.py's: the number
    # is the floor this landed on, not a target, and the next kilobyte has to
    # argue for itself. The in-post player's entire reason for existing is that
    # it is small; a version of it that grows toward app.js should fail here
    # rather than be discovered on somebody's feed.
    # MEASURED AT THE URLs THE PAGE ACTUALLY REQUESTS, bust and all. Fetching
    # /static/skribl/inlineplayer.js bare measures the wrong thing: skribl/
    # jsstrip.py removes comments from the RESPONSE only for the file's real
    # content bust (verify_assetcache.py explains why a fabricated one buys no
    # work), and this file is mostly comments. Bare, it read 28,739 B; what a
    # host downloads is a third of that. A ratchet on the unstripped number
    # would have priced every explanatory comment as if it shipped.
    #
    # THE CSS IS NOT STRIPPED and is a third of the figure. jsstrip.py is
    # JavaScript-only and cssgraph.py only derives player.css from styles.css,
    # so inlineplayer.css ships every word of its own reasoning. That is a real
    # 8 KB and it is left alone deliberately: it is the smaller half, it is the
    # part a host is most likely to read before overriding something, and
    # inventing a third asset pipeline to save 5 KB is not a trade this project
    # should make twice.
    #
    # AND THE CSS IS WHERE THIS RATCHET BITES FIRST. Cropping the poster added
    # lib/sharecard.js (993 B) and, at first, 2,800 B of explanation in
    # inlineplayer.css — which took the total past 27,000 and was the right
    # failure: that prose ships to every host on every page. It moved into
    # inlineplayer.js's header, where jsstrip removes it from the response, and
    # the CSS kept the numbers and a pointer. Same words, a third of the weight.
    #
    # Pinned just above the floor that landed, the way verify_player_isolation.py
    # pins its own: the next kilobyte has to argue for itself, and a version of
    # this player growing toward app.js fails here rather than being discovered
    # on somebody's feed.
    EMBED_RATCHET = 25_000
    # feed.js is excluded: it is the PREVIEW PAGE's own script (fetch the
    # listing, clone the macro), not part of what a host embeds — a host writes
    # that loop themselves against their own posts.
    embed_urls = sorted(u for u in
                        set(re.findall(r'(?:src|href)="([^"]*/static/skribl/[^"]+)"',
                                       feed_html))
                        if "feed.js" not in u)
    total = 0
    served = {}
    for u in embed_urls:
        raw = urllib.request.urlopen(BASE + u if u.startswith("/") else u,
                                     timeout=20).read()
        served[u.split("/static/skribl/")[-1].split("?")[0]] = len(raw)
        total += len(raw)
    check("every asset the embed macro names is one the server serves",
          len(embed_urls) == 5, str(embed_urls))
    check(f"the in-post player costs a host no more than {EMBED_RATCHET:,} bytes "
          f"of CSS and JavaScript",
          total <= EMBED_RATCHET,
          f"{total:,} B served: " + ", ".join(f"{k} {v:,}" for k, v in served.items()))

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
