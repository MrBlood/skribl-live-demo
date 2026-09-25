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
import struct
import wave
import pathlib
import re
import sys
import urllib.request
from assertions import make_check
import source
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the feed player works.")
    raise SystemExit(77)

# A REAL LOOP, because "the music stops when the drawing stops" is a claim about
# SOUND and cannot be checked by looking at the DOM. Same 220 Hz tone and the
# same analyser tap verify_player_isolation.py uses — a second way of measuring
# audio would be a second thing to drift.
WAV = "/tmp/inline_loop.wav"
with wave.open(WAV, "wb") as _w:
    _w.setnchannels(2)
    _w.setsampwidth(2)
    _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(6 * 44100):
        _v = int(18000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))

TAP = """
window.__an = null;
(function () {
  const Orig = window.AudioContext || window.webkitAudioContext;
  function Tapped() {
    const ctx = new Orig();
    const an = ctx.createAnalyser(); an.fftSize = 2048; an.connect(ctx.destination);
    window.__an = an;
    const orig = ctx.createBufferSource.bind(ctx);
    ctx.createBufferSource = function () {
      const n = orig();
      const oc = n.connect.bind(n);
      n.connect = function (d) { try { oc(an); } catch (e) {} return oc(d); };
      return n;
    };
    return ctx;
  }
  Tapped.prototype = Orig.prototype;
  window.AudioContext = Tapped; window.webkitAudioContext = Tapped;
})();
"""

PEAK = """() => {
  if (!window.__an) return -1;
  const buf = new Uint8Array(window.__an.frequencyBinCount);
  window.__an.getByteTimeDomainData(buf);
  let peak = 0;
  for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
  return peak;
}"""

results = []


check = make_check(results)


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
# composer sends "public" only when its "Show in the public gallery" box is
# ticked (v304; verify_gallery.py drives that box), so a post the composer
# makes with the box at its default is invisible to GET /api/skribls. A
# fixture built by clicking #postSubmitBtn therefore produced a feed page with
# nothing on it, and this suite was asserting against an empty list — which
# is how it first ran.
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


def post_one(b, title, music=False):
    """Record a drawing in Pad and post it PUBLICLY. Returns its public id."""
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/skribl-pad")
    pg.evaluate("() => localStorage.clear()")
    scribble(pg, pg.locator("#canvas").bounding_box())
    pg.wait_for_timeout(600)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    if music:
        # TRIMMED, not merely attached: an untrimmed upload can be posted
        # without ever building a loop, which would leave the thing under test
        # unexercised. Same reasoning as verify_player_isolation.py's fixture.
        pg.set_input_files("#musicInput", WAV)
        pg.wait_for_timeout(4000)
        pg.evaluate("() => { trimStart = 1.0; trimEnd = 3.0; loopCrossfadeMs = 120; "
                    "if (typeof updateTrimUI === 'function') updateTrimUI(); }")
        pg.wait_for_timeout(1200)
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
    id_m, errs_m = post_one(b, "Harness fixture with sound", music=True)
    if not (id_a and id_b and id_m):
        check("three drawings posted through the API, one with a loop (fixture)", False,
              f"got {id_a!r}, {id_b!r}, {id_m!r}; "
              f"errors: {(errs_a + errs_b + errs_m)[:2]}")
        print("\n" + "=" * 62 + "\n0/1 passed")
        sys.exit(1)
    check("three drawings posted through the API, one with a loop (fixture)",
          True, f"{id_a}, {id_b}, {id_m}")

    # ---- the macro's server-rendered markup --------------------------------
    # Before any script runs, a post must already be something. This is the
    # reason _skribl_inline_player.html renders markup instead of letting
    # inlineplayer.js create it: a host page with the script blocked, or simply
    # not arrived yet, shows the drawing's card and a play affordance rather
    # than an empty rectangle where a post should be.
    feed_html = urllib.request.urlopen(BASE + "/feed", timeout=20).read().decode()
    check("the feed page server-renders the poster before any script runs",
          "skribl-inline-poster" in feed_html and "/poster" in feed_html)
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
    pg.add_init_script(TAP)     # before any page script constructs a context
    browsing.goto(pg, BASE, "/feed")

    mounted = pg.evaluate("() => window.SkriblInline ? window.SkriblInline.players().length : -1")
    check("the feed mounts one in-post player per listed Skribl",
          mounted >= 3, f"{mounted} mounted")
    check("no page errors on the feed", not errs, "; ".join(errs[:2]))

    # THE FEED PAGE IS NOT A REQUEST LOG. Its header read "GET /api/skribls"
    # and an anonymous post's byline read "Someone". The mechanism pinned: no
    # HTTP-method-plus-path token anywhere in the page's visible text (a
    # method name followed by a slash is how a route is written, never how a
    # sentence is), and a post with no user_id renders no byline at all —
    # counted against the listing the page itself rendered from. Red on v287.
    _visible = pg.evaluate("() => document.body.innerText")
    check("the feed's visible text names no endpoint",
          not re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", _visible),
          (re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/\S*", _visible) or [""])[0]
          if re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", _visible) else "")
    # IT FOLLOWS THE HOST'S THEME (inlineplayer.js header): every chrome colour
    # is var(--token, fallback), with the token NAMES a feed already has. So a
    # host that sets --bg-elev on its root recolours the box, and one that sets
    # nothing gets the fallback. Asserted by setting the token on the page and
    # reading the computed background — a literal in the sheet would ignore it.
    _host_bg = pg.evaluate("""() => {
      document.documentElement.style.setProperty('--bg-elev', '#f6f8fa');
      const el = document.querySelector('.skribl-inline');
      return el ? getComputedStyle(el).backgroundColor : null; }""")
    check("the in-post box takes its ground from the host's --bg-elev",
          _host_bg == "rgb(246, 248, 250)", repr(_host_bg))
    pg.evaluate("() => document.documentElement.style.removeProperty('--bg-elev')")
    _listing = json.loads(urllib.request.urlopen(BASE + "/api/skribls", timeout=20).read())
    _items = _listing.get("items", _listing) if isinstance(_listing, dict) else _listing
    _named = sum(1 for it in _items if it.get("user_id") is not None)
    _bylines = pg.evaluate("() => document.querySelectorAll('.phead .dn').length")
    _heads = pg.evaluate("() => document.querySelectorAll('.phead').length")
    check("a post with no user_id renders no byline",
          _heads >= 3 and _bylines == _named,
          f"{_bylines} byline(s) for {_named} attributed post(s) of {_heads}")

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
    # MID-REPLAY IS A STATE, NOT A DELAY: the first play also waits on the lazy
    # payload fetch, so a fixed 1200ms sampled a player still loading whenever
    # the fetch was slow. Wait until it is playing and between 40% and 85% of
    # the way through (it loops, so the window comes round again), then sample
    # everything below at once.
    try:
        pg.wait_for_function("""(id) => {
            const p = window.SkriblInline.find(id); const s = p && p.state();
            return !!(s && s.state === 'playing' && s.loaded && s.totalMs
                      && s.elapsedMs >= 0.4 * s.totalMs && s.elapsedMs <= 0.85 * s.totalMs); }""",
            arg=id_a, timeout=8000)
    except PWTimeout:
        pass
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
    # B's first play waits on its own fetch; wait for the state, not a delay.
    try:
        pg.wait_for_function("""([a, b]) => window.SkriblInline.find(a).state().state === 'idle'
                                && window.SkriblInline.find(b).state().state === 'playing'""",
                             arg=[id_a, id_b], timeout=8000)
    except PWTimeout:
        pass
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

    # ---- THE TRANSLUCENT FIXTURE, which used to be impossible --------------
    # THE COMPARISON ABOVE DRAWS OPAQUE ON PURPOSE, and this file's own note
    # said why: the wet/dry compositor was not implemented here, so a
    # sub-100%-opacity stroke beaded at its overlaps and any pixel assertion
    # over one would have been "quietly tolerant of a gap it cannot see". It
    # also said that if the in-post player ever got the compositor, "that
    # fixture is where to widen the proof". It has, so this is that.
    #
    # WHAT THIS CAN AND CANNOT ASSERT. The two surfaces fit the drawing to
    # DIFFERENT boxes — the sealed player to its column, this one to the
    # payload's logical size — so their ink masses are not comparable in
    # absolute terms even when both are right. An opaque control proved that
    # the hard way while this was being built: it scored WORSE than the
    # translucent case on a cross-surface grid diff, which is how a confounded
    # instrument announces itself. So the assertion here is the SHAPE property
    # the compositor exists for, measured on this player alone: a stroke drawn
    # as accumulating translucent stamps has far less ink than the same stroke
    # composited once, because the overlaps eat it.
    #
    # BOTH ARMS ARE MEASURED IN THIS RUN, and the constant that used to sit
    # here is gone. It read STAMPED_INK_MAX = 160_000, with 145,014 stamped
    # against 177,246 composited — and the composited figure was inflated by a
    # bug this suite could not see. inlineplayer.js derived the compositor's
    # scale as backing/clientWidth, true only while the canvas's CSS width was
    # pinned to the drawing's logical size; max-width was already clamping that
    # width, so the offscreen layers were scaled ~1.94x and every composited
    # stroke was painted about twice its size. That is what carried the number
    # over the floor. Fixing the letterbox (v305) made the scale honest and the
    # figure fell to 82,443 — under a floor that had been calibrated on the
    # defect.
    #
    # The direction was wrong too. Translucent light strokes on a dark ground
    # STACK when stamped, so stamping is the BRIGHTER render: measured here,
    # 141,649 stamped against 82,443 composited. The compositor exists to stop
    # that stacking, so it must produce LESS ink, not more. The old sentence
    # said the opposite and the old gate asserted the opposite, and both passed
    # because the scale bug pushed the number the way the gate wanted.
    #
    # So: render the same drawing twice, once with the compositor disabled at
    # source, and compare the two. No constant to rot, and the comparison is
    # the mutation.

    tl_pts = []
    for _i in range(240):
        _a = (_i / 240) * math.pi * 8
        _r = 40 + (_i / 240) * 120
        tl_pts.append({"x": 260 + math.cos(_a) * _r, "y": 260 + math.sin(_a) * _r,
                       "color": "rgba(233,236,245,0.5)", "size": 26,
                       "t": _i * 12, "start": _i == 0, "erase": False})
    _tl_body = {"frames": [{"strokes": tl_pts, "strokeGroups": [len(tl_pts)],
                            "background": {"color": "#101418"}}],
                "title": "translucent", "visibility": "public"}
    _tl_req = urllib.request.Request(
        BASE + "/api/skribls", method="POST",
        data=json.dumps(_tl_body).encode(),
        headers={"Content-Type": "application/json"})
    id_tl = json.loads(urllib.request.urlopen(_tl_req, timeout=20).read())["id"]

    def _tl_ink(disable_compositor):
        """Play the translucent fixture in the feed and return its ink.

        `disable_compositor` patches the SERVED inlineplayer.js so
        makeCompositor returns null — the drawing, the colours and the
        geometry are identical in both arms, so the compositor is the only
        variable. Changing the alpha instead would change the picture, which
        is the confounded control this suite's note above warns about."""
        pg = b.new_page(viewport={"width": 620, "height": 900})
        if disable_compositor:
            def _kill(route):
                r = route.fetch()
                src, n = re.subn(r"if \(!any\)\s*return null;",
                                 "if (true) return null;", r.text())
                # A mutation that silently fails to apply reads as a pass.
                assert n == 1, f"compositor kill anchor matched {n}x"
                route.fulfill(response=r, body=src)
            pg.route(re.compile(r"inlineplayer\.js"), _kill)
        browsing.goto(pg, BASE, "/feed")
        pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_tl)
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'",
                             arg=id_tl, timeout=15000)
        # Long enough for the whole 2.9s replay plus the final bake.
        pg.wait_for_timeout(5000)
        g = pg.evaluate(GRID, f'[data-skribl-id="{id_tl}"] .skribl-inline-canvas')
        pg.close()
        if not g:
            return None, None
        _floor = min(g)
        return sum(v - _floor for v in g), g

    tl_ink, tl_grid = _tl_ink(False)
    stamped_ink, _ = _tl_ink(True)

    check("a translucent drawing renders at all in the feed", bool(tl_grid))
    if tl_ink is not None and stamped_ink is not None:
        # The drawing is still THERE. "Less ink" must not be reachable by
        # rendering nothing, which is the other way this could go green.
        check("the composited drawing is actually painted",
              tl_ink > stamped_ink * 0.25,
              f"composited ink {tl_ink} against {stamped_ink} stamped — a near-"
              "empty canvas would also have 'less ink' than the stamped one")
        check("a 50%-opacity stroke is composited, not stamped",
              tl_ink < stamped_ink * 0.8,
              f"composited ink {tl_ink} is not materially below the {stamped_ink} "
              "the same drawing scores with the compositor disabled — the "
              "overlaps are stacking, which is the scalloped, banded rendering "
              "the wet/dry compositor exists to prevent")

    # ---- LOOP, AND THE MUSIC THAT MUST STOP WITH THE DRAWING ---------------
    #
    # A post has exactly two viewer controls, and this is the second. It is PER
    # POST rather than page-wide (mute is page-wide) because repeating is a
    # property of the drawing in front of you; the asymmetry is deliberate and
    # asserted here so it cannot be quietly unified.
    loop_state = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const btn = el.querySelector('.skribl-inline-loop');
        return { present: !!btn, pressed: btn && btn.getAttribute('aria-pressed'),
                 noloop: el.classList.contains('is-noloop') }; }""", id_m)
    check("a post carries a loop control", loop_state["present"], json.dumps(loop_state))
    check("and it starts on, which is what a post did before it existed",
          loop_state["pressed"] == "true" and loop_state["noloop"] is False,
          json.dumps(loop_state))

    # The audio fixture, played and unmuted, so there is something to stop.
    pg.evaluate("() => window.SkriblInline.setSoundOn(true)")
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_m)
    pg.wait_for_timeout(1500)
    m_state = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_m)
    check("the Skribl with a loop reports its audio", m_state["hasAudio"] is True,
          json.dumps(m_state))
    playing_peak = max(pg.evaluate(PEAK) for _ in range(6))
    check("its music is actually audible while it plays",
          playing_peak > 4,
          f"analyser peak {playing_peak} — measured on the audio graph, not "
          f"inferred from a node existing")

    # TURN THE LOOP OFF and let the replay run past its end.
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"] "
                ".skribl-inline-loop').click()", id_m)
    after_click = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        return { noloop: el.classList.contains('is-noloop'),
                 pressed: el.querySelector('.skribl-inline-loop')
                            .getAttribute('aria-pressed') }; }""", id_m)
    check("the control reports the state it just changed to",
          after_click["noloop"] is True and after_click["pressed"] == "false",
          json.dumps(after_click))

    pg.wait_for_function(
        "(id) => window.SkriblInline.find(id).state().state !== 'playing'",
        arg=id_m, timeout=20000)
    ended = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_m)
    check("with the loop off the replay stops instead of going round",
          ended["state"] != "playing"
          and ended["elapsedMs"] >= ended["totalMs"] - 80,
          json.dumps(ended))

    # THE ASSERTION THIS BLOCK EXISTS FOR. A finished drawing with a loop still
    # playing under it is a post that will not shut up. Measured on the audio
    # graph after the replay has ended, not asserted from the DOM.
    pg.wait_for_timeout(400)
    stopped_peak = max(pg.evaluate(PEAK) for _ in range(6))
    check("AND THE MUSIC STOPS WITH IT",
          stopped_peak <= 1,
          f"analyser peak {stopped_peak} after the drawing finished (it was "
          f"{playing_peak} while playing)")

    # Turning it back on restarts a replay sitting at its end, rather than
    # appearing to do nothing until the next tap.
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"] "
                ".skribl-inline-loop').click()", id_m)
    try:
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'",
                             arg=id_m, timeout=5000)
    except PWTimeout:
        pass
    resumed = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_m)
    check("turning it back on starts it again rather than doing nothing",
          resumed["state"] == "playing", json.dumps(resumed))
    pg.evaluate("() => window.SkriblInline.stopAll()")
    pg.evaluate("() => window.SkriblInline.setSoundOn(false)")
    pg.wait_for_timeout(200)

    # ---- scrolling away ----------------------------------------------------
    pg.evaluate("""() => {
        const spacer = document.createElement('div');
        spacer.style.height = '250vh';
        document.body.appendChild(spacer);
        window.scrollTo(0, document.body.scrollHeight); }""")
    # The IntersectionObserver's callback is the state; wait for it, not 1200ms.
    try:
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'idle'",
                             arg=id_b, timeout=5000)
    except PWTimeout:
        pass
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

    # ---- THE PAGE SAYS WHAT IT IS, AND ITS STATES SPEAK THE PAGE'S LANGUAGE --
    # SK-AUD-012 (acquisition audit of v302) reviewed /feed as a consumer feed
    # and found its empty state teaching POST routes and JSON fields, and its
    # error state a dead end with nothing to press. The page IS a developer
    # demo; it now says so on the page, its two states carry no <code>, the
    # technical explanation lives under a "For developers" heading, and the
    # error state has a Retry that fetches the listing again. Mechanism, not
    # words: the label is an element, the states are counted for <code>
    # children, and Retry is driven with the listing failing and then not.
    dp = b.new_page(viewport={"width": 620, "height": 900})
    derrs = []
    dp.on("pageerror", lambda e: derrs.append(str(e)))
    browsing.goto(dp, BASE, "/feed")
    _tag = dp.evaluate("""() => {
      const t = document.querySelector('.fhead .demo-tag');
      return t ? t.textContent.trim() : null; }""")
    check("the feed page labels itself a developer demo, in its header",
          _tag is not None and "demo" in _tag.lower(), repr(_tag))
    _dev = dp.evaluate("""() => {
      const h = document.querySelector('.note h2');
      return h ? h.textContent.trim() : null; }""")
    check("...and the technical notes sit under a 'For developers' heading",
          _dev is not None and "developer" in _dev.lower(), repr(_dev))
    _codes = dp.evaluate(
        "() => document.querySelectorAll('#feedEmpty code, #feedError code').length")
    check("the empty and error states carry no <code> element",
          _codes == 0, f"{_codes} code element(s) in the two consumer states")
    dp.close()

    # THE ERROR STATE, WITH A WAY OUT. The listing fails on the wire, the page
    # says so with a Retry; the wire recovers, Retry is pressed, the feed loads.
    ep = b.new_page(viewport={"width": 620, "height": 900})
    eerrs = []
    ep.on("pageerror", lambda e: eerrs.append(str(e)))
    ep.route(re.compile(r"/api/skribls\?limit="), lambda route: route.abort())
    browsing.goto(ep, BASE, "/feed")
    ep.wait_for_timeout(600)
    _err = ep.evaluate("""() => {
      const e = document.getElementById('feedError'), r = document.getElementById('feedRetry');
      return { shown: !!e && !e.hidden, retry: !!r && r.offsetParent !== null,
               text: e ? e.textContent.trim() : '' }; }""")
    check("when the listing cannot be fetched the page says so",
          _err["shown"], json.dumps(_err))
    check("...and offers a Retry, not a dead end",
          _err["shown"] and _err["retry"], json.dumps(_err))
    ep.unroute(re.compile(r"/api/skribls\?limit="))
    if _err["retry"]:
        ep.click("#feedRetry")
        ep.wait_for_timeout(1500)
    _after = ep.evaluate("""() => ({
      err: !document.getElementById('feedError').hidden,
      empty: !document.getElementById('feedEmpty').hidden,
      mounted: window.SkriblInline ? window.SkriblInline.players().length : -1 })""")
    check("Retry fetches the listing again and the feed loads",
          _err["retry"] and not _after["err"] and (_after["mounted"] >= 1 or _after["empty"]),
          json.dumps(_after))
    check("no page errors through the failure and the retry", not eerrs, "; ".join(eerrs[:2]))
    ep.close()

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
    browsing.goto(p2, BASE, "/feed")
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
        browsing.goto(fp, BASE, "/feed")
        fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", flip_id)
        fp.wait_for_function("(id) => window.SkriblInline.find(id).state().loaded",
                             arg=flip_id, timeout=15000)
        fst = fp.evaluate("(id) => window.SkriblInline.find(id).state()", flip_id)
        check("a flip document is recognised as a flip, not replayed as strokes",
              fst["kind"] == "flip", json.dumps(fst))

        # ms table, not the slot table: holdtiming.js now denominates a page in
        # milliseconds because a drawing page is exempt from fps. Same answer
        # for a document with no `draw`, which this one is.
        expected = fp.evaluate("() => { const H = window.SkriblHold;"
                               " return H.cycleMs(H.msTable("
                               "[{hold:2},{hold:4},{hold:2}], 6)); }")
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

    # ---- DRAW-ON, AT ITS THREE BOUNDARIES, ON THIS SURFACE SPECIFICALLY ----
    #
    # One semantic timeline, four renderers. The editor, /s/ and the exporter
    # each turned progress into a stroke count themselves, and so did this
    # player — which tested `progress > 0` to decide whether a page draws.
    # progressAt() returns 0 for a still page AND for a drawing page at the
    # instant it starts, so on the feed, and ONLY on the feed, a drawing page
    # appeared finished for its first frame and then wiped and redrew.
    #
    # It is asserted here rather than at the module because the module was
    # never wrong: dueCount() is one function and this suite is the only place
    # that watches the feed's actual canvas. The three classes are the whole
    # contract — nothing at the start, some of it partway, all of it at the end
    # — and the comparison is against the SAME page posted without `draw`, so
    # "all of it" means a measured full render and not this player's own idea
    # of one.
    def post_draw_pair():
        # 26 points spread over 1,150 ms and across the canvas, so the ink a
        # prefix carries rises with the prefix. Points bunched in one corner
        # would grid down to nearly the same mass at every progress and the
        # measure would not be able to tell the classes apart.
        pts = [{"x": 90 + i * 24, "y": 300, "color": "#ffffff", "size": 16,
                "t": i * 46, "erase": False, "start": i == 0} for i in range(26)]
        page = {"strokes": pts, "strokeGroups": [len(pts)]}
        edge = [{"strokes": [dict(q, y=60) for q in pts[:4]],
                 "strokeGroups": [4], "hold": 1}]

        # THE DRAWING PAGE IS FIRST, and that is the whole point of the
        # fixture. progressAt() returns exactly 0 only when the clock is AT a
        # page's start, and the one moment a viewer reliably lands there is
        # elapsed 0 — every load of the post, and every time the loop comes
        # round. Put the drawing page second and probe a millisecond after the
        # boundary and progress is already 0.0009, the broken branch is not
        # taken, and the assertion passes on the defect: measured, it did.
        def body(title, first):
            return {"title": title, "visibility": "public", "version": 2,
                    "schemaVersion": 2, "playbackMode": "flip", "fps": 6,
                    "frames": [first] + edge + edge,
                    "canvasSize": {"cssWidth": 816, "cssHeight": 612}}

        out = []
        for title, mid in (("Harness draw-on page", dict(page, draw=True)),
                           ("Harness still page", dict(page, hold=1))):
            req = urllib.request.Request(
                BASE + "/api/skribls", data=json.dumps(body(title, mid)).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                out.append(json.loads(r.read().decode())["id"])
        return out

    draw_id = still_id = None
    try:
        draw_id, still_id = post_draw_pair()
    except Exception as exc:
        check("a Draw-on flip and its still twin were posted (fixture)", False,
              f"{type(exc).__name__}: {exc}")
    if draw_id and still_id:
        check("a Draw-on flip and its still twin were posted (fixture)", True,
              f"{draw_id} / {still_id}")
        dp = b.new_page(viewport={"width": 620, "height": 900})
        derrs = []
        dp.on("pageerror", lambda e: derrs.append(str(e)))
        browsing.goto(dp, BASE, "/feed")

        def ink_at(sid, ms):
            dp.evaluate("(id) => document.querySelector("
                        "'[data-skribl-id=\"' + id + '\"]').click()", sid)
            dp.wait_for_function("(id) => window.SkriblInline.find(id)"
                                 " && window.SkriblInline.find(id).state().loaded",
                                 arg=sid, timeout=15000)
            dp.evaluate("([id, t]) => window.SkriblInline.find(id).seek(t)", [sid, ms])
            dp.wait_for_timeout(120)
            g = dp.evaluate(GRID, f'[data-skribl-id="{sid}"] .skribl-inline-canvas')
            return ink_mass(g) if g else None

        # 6 fps, drawing page first: exempt from fps, it runs its own 1,150 ms
        # span from 0. seek() pauses, so each of these is read at exactly the
        # time named — and 0 is read at exactly 0, which is the case that was
        # broken. The still twin's first page is an ordinary one-unit page, so
        # 40 ms is safely inside it and reads the page rendered whole.
        full = ink_at(still_id, 40)
        start = ink_at(draw_id, 0)
        mid = ink_at(draw_id, 575)
        end = ink_at(draw_id, 1145)
        check("the Draw-on probe read a canvas at all",
              None not in (full, start, mid, end),
              f"full={full} start={start} mid={mid} end={end}")
        if None not in (full, start, mid, end) and full:
            check("a Draw-on page opens EMPTY on the feed, not finished",
                  start < full * 0.25,
                  f"ink {start} against a full page's {full} — at elapsed 0, "
                  f"which is every load and every loop, the feed was painting "
                  f"the completed drawing and then wiping it to redraw. The "
                  f"editor and /s/ open this page blank")
            check("...reveals a PREFIX partway through",
                  full * 0.25 < mid < full * 0.85,
                  f"ink {mid} against a full page's {full} — partway through, "
                  f"a reveal is neither blank nor finished")
            check("...and is COMPLETE by the end of its own span",
                  end > full * 0.90,
                  f"ink {end} against the same page posted still: {full} — a "
                  f"reveal that never finishes drops its last strokes")
            check("the three classes are strictly ordered",
                  start < mid < end, f"{start} / {mid} / {end}")
        check("no JS errors while a Draw-on page reveals on the feed",
              not derrs, "; ".join(derrs[:2]))
        dp.close()

    # ---- AND IT MUST REACH THE END BEFORE THE PAGE TURNS -------------------
    #
    # dueCount() releases the last point at progress 1, and indexAtMs() owns a
    # page over [start, end) — so the live clock climbs toward 1 and the page
    # is taken away before it arrives. Both contracts were individually right
    # and together could never show a drawing page finished: on a 1,150ms page
    # of 26 points the 26th was never due while that page was up. Fixed by
    # displayAt(), which holds an unfinished drawing page for one more frame.
    #
    # SEEKING CANNOT TEST THIS. seek() is a jump and deliberately bypasses the
    # guard, so this drives real playback and samples the canvas on every
    # animation frame — which sees every state the player actually painted,
    # including one that lasts a single frame.
    #
    # The last point is a BIG ISOLATED MARK in a corner, its own stroke, far
    # from the rest of the drawing. A missing endpoint hides easily inside a
    # whole-canvas ink tolerance; it cannot hide when the assertion is "did
    # that corner ever get painted at all".
    def post_endpoint_pair():
        body = [{"x": 60 + i * 20, "y": 300, "color": "#ffffff", "size": 14,
                 "t": i * 46, "erase": False, "start": i == 0} for i in range(25)]
        tail = {"x": 740, "y": 60, "color": "#ffffff", "size": 44,
                "t": 1150, "erase": False, "start": True}
        page = {"strokes": body + [tail], "strokeGroups": [25, 1]}
        rest = {"strokes": [dict(q, y=520) for q in body[:5]],
                "strokeGroups": [5], "hold": 1}

        def mk(title, first):
            return {"title": title, "visibility": "public", "version": 2,
                    "schemaVersion": 2, "playbackMode": "flip", "fps": 6,
                    "frames": [first, rest],
                    "canvasSize": {"cssWidth": 816, "cssHeight": 612}}

        out = []
        for title, first in (("Harness endpoint draw", dict(page, draw=True)),
                             ("Harness endpoint still", dict(page, hold=1))):
            req = urllib.request.Request(
                BASE + "/api/skribls", data=json.dumps(mk(title, first)).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                out.append(json.loads(r.read().decode())["id"])
        return out

    # Every painted frame, as (corner ink, body ink). Registered before play,
    # re-arming itself each frame, so nothing the player draws goes unseen.
    SAMPLER = """(sel) => {
      window.__f = [];
      var c = document.querySelector(sel);
      if (!c) return false;
      var g = document.createElement('canvas'); g.width = 96; g.height = 96;
      var gx = g.getContext('2d');
      var tick = function () {
        gx.clearRect(0, 0, 96, 96);
        gx.drawImage(c, 0, 0, 96, 96);
        var d = gx.getImageData(0, 0, 96, 96).data, corner = 0, body = 0;
        for (var y = 0; y < 96; y++) for (var x = 0; x < 96; x++) {
          var i = (y * 96 + x) * 4;
          var v = (0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2]) * (d[i+3] / 255);
          if (x >= 80 && y <= 16) corner += v; else body += v;
        }
        window.__f.push([Math.round(corner), Math.round(body)]);
        window.requestAnimationFrame(tick);
      };
      window.requestAnimationFrame(tick);
      return true; }"""

    draw2 = still2 = None
    try:
        draw2, still2 = post_endpoint_pair()
    except Exception as exc:
        check("an endpoint fixture pair was posted", False, f"{type(exc).__name__}: {exc}")
    if draw2 and still2:
        check("an endpoint fixture pair was posted", True, f"{draw2} / {still2}")

        def watch(sid, ms):
            """Play `sid` for `ms` and return every frame the player painted."""
            wp = b.new_page(viewport={"width": 620, "height": 900})
            browsing.goto(wp, BASE, "/feed")
            sel = '[data-skribl-id="%s"] .skribl-inline-canvas' % sid
            wp.evaluate("(id) => document.querySelector("
                        "'[data-skribl-id=\"' + id + '\"]').click()", sid)
            wp.wait_for_function("(id) => window.SkriblInline.find(id)"
                                 " && window.SkriblInline.find(id).state().loaded",
                                 arg=sid, timeout=15000)
            armed = wp.evaluate(SAMPLER, sel)
            wp.evaluate("(id) => window.SkriblInline.find(id).play()", sid)
            wp.wait_for_timeout(ms)
            frames = wp.evaluate("() => window.__f") if armed else None
            wp.close()
            return frames

        # One and a bit cycles: the drawing page is 1,150ms (fps-exempt) and the
        # still page one 6fps unit, so ~1,317ms round trip.
        seen = watch(draw2, 2100)
        ref = watch(still2, 900)
        check("the endpoint sampler recorded frames on both fixtures",
              bool(seen) and bool(ref), f"{len(seen or [])} / {len(ref or [])}")
        if seen and ref:
            corner_full = max(f[0] for f in ref)
            corner_max = max(f[0] for f in seen)
            check("the still twin proves the corner mark is visible at all "
                  "(fixture calibration)", corner_full > 200, str(corner_full))
            check("a Draw-on page REACHES its last stroke before the page turns",
                  corner_max > corner_full * 0.5,
                  f"the corner mark peaked at {corner_max} against the same page "
                  f"rendered whole: {corner_full}. The last recorded point is "
                  f"only due at progress 1, and the live clock leaves the page "
                  f"before progress 1 — so it never painted at all")
            # ...and it was a REVEAL, not the page simply appearing finished:
            # some painted frame carried the body without the endpoint.
            body_full = max(f[1] for f in ref)
            prefix = [f for f in seen
                      if f[0] <= corner_full * 0.1 and 0 < f[1] < body_full * 0.8]
            check("...having first shown a PREFIX, so it revealed rather than "
                  "arriving whole", bool(prefix),
                  f"no painted frame carried part of the body without the "
                  f"endpoint (body full {body_full})")

    # ---- the rules that must not be retyped --------------------------------
    # lib/holdtiming.js exists so the Flip editor and the player cannot disagree
    # about which page is on screen at time t (see its header). A third surface
    # that re-derives that from frames and fps would be the same bug a third
    # time, and it would be invisible until somebody posted a flip with a hold.
    # Code only: these are absence checks, and a comment explaining why a thing
    # is absent must not read as the thing being present.
    src = source.read_js(ROOT / "skribl" / "static" / "inlineplayer.js")
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
    browsing.goto(cp, BASE, "/feed")
    # INJECTED, NOT SHIPPED. The comparison below needs sharecard.js's
    # arithmetic in THIS page to check the CSS literals against it — and until
    # v281 the macro loaded it for every host to get it here, 5,210 B of a
    # 32,000 B budget for a module the page never calls. The check is the same
    # check; only who pays for it changed.
    #
    # evaluate(), NOT add_script_tag(). The latter inlines the source, and this
    # page's CSP is `script-src 'self' 'nonce-...'`, so Chromium refuses it —
    # which is verify_csp.py's subject matter arriving as a side effect and is
    # the right answer. evaluate() runs through the debugger protocol and is
    # not a page script, so the module's IIFE installs window.SkriblShareCard
    # without the page ever being allowed to load one.
    # WHAT THE POSTER LANDS ON. These fixtures carry no thumbnail (see the note
    # at POST_PUBLIC), so the bytes behind every poster here are the server's
    # fallback — which used to be the branded 1200x630 share card, cropped by
    # the rule below into a fragment of a wordmark (v287 audit SK-BUG-006).
    # fetch() reports the URL a redirect landed on; the <img> cannot.
    _landed = cp.evaluate("""async () => {
        const img = document.querySelector('.feed .skribl-inline-poster, .skribl-inline-poster');
        const r = await fetch(img.getAttribute('src'));
        return r.url; }""")
    check("a post with no thumbnail does NOT land its poster on the branded card",
          "og-card" not in _landed, f"landed on {_landed}")
    cp.evaluate((ROOT / "skribl" / "static" / "lib" / "sharecard.js")
                .read_text(encoding="utf-8"))
    geom = cp.evaluate("""() => {
        // SCOPED TO THE FEED. The page's first .skribl-inline is the
        // COMPOSER's draft box now, and a draft has no poster to crop — it is
        // not published, so there is no card. Selecting it read null.
        const el = document.querySelector('#feedList .skribl-inline');
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

    # THE PLAYER'S OWN COPY OF THE CARD'S ARITHMETIC (v309). fitPoster() frames
    # the idle poster onto the drawing's rect, which needs drawingRect()'s
    # constants and the plate's radius and hairline -- and it inlines them
    # rather than loading lib/sharecard.js, for the reason the macro's note
    # gives: a page that only DISPLAYS Skribls is not charged for the module
    # that COMPOSES one. That is the right trade and it is also how two files
    # drift apart, so the literals are read out of the player and compared to
    # the module evaluated above.
    #
    # READ FROM THE STRIPPED SOURCE, NOT THE FILE. A regex over the raw file
    # would happily match a number inside a comment explaining the number --
    # which is the "check the mechanism, not the word" failure this tree has
    # hit three times. jsstrip removes every comment first, so what is matched
    # is a declaration.
    sys.path.insert(0, str(ROOT))
    from skribl.jsstrip import strip_bytes as _strip                # noqa: E402
    _ipsrc = _strip((ROOT / "skribl" / "static" / "inlineplayer.js").read_bytes()).decode()
    _lits = {k: int(v) for k, v in re.findall(
        r"\b(CARD_W|CARD_H|AREA_W|AREA_H|FOOT|PLATE_R|PLATE_IN)\s*=\s*(\d+)\b", _ipsrc)}
    _mod = cp.evaluate("""() => { const S = window.SkriblShareCard;
        return { CARD_W: S.CARD_W, CARD_H: S.CARD_H, AREA_W: S.AREA_W,
                 AREA_H: S.AREA_H, FOOT: S.FOOTER,
                 PLATE_R: S.PLATE_R, PLATE_IN: S.PLATE_LW }; }""")
    check("the in-post player's inlined card constants are all seven of them",
          set(_lits) == set(_mod),
          f"found {sorted(_lits)} against {sorted(_mod)} \u2014 a constant that "
          f"stopped being a declaration stops being compared, silently")
    check("...and every one equals lib/sharecard.js",
          _lits == _mod,
          f"{_lits} against {_mod} \u2014 the player inlines these to save a host "
          f"the module; this row is what stops the copy drifting from it")

    # AND THE SAME NUMBERS ON THE OTHER SIDE. The card is composited from this
    # module's geometry too — by lib/postedcard.js, which the EDITORS load and a
    # feed does not (it has no drawing to composite; see that file's header). If
    # the compositor stopped reading sharecard.js, the crop above would be
    # measuring a rectangle nothing puts the drawing in.
    pc = (ROOT / "skribl" / "static" / "lib" / "postedcard.js").read_text(encoding="utf-8")
    check("the card compositor places the drawing using lib/sharecard.js",
          "SkriblShareCard" in pc and "drawingRect" in pc,
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
    #
    # MEASURED AT THE URLs THE PAGE ACTUALLY REQUESTS, bust and all. Fetching
    # /static/skribl/inlineplayer.js bare measures the wrong thing:
    # skribl/jsstrip.py removes comments from the RESPONSE only for the file's
    # real content bust (verify_assetcache.py explains why a fabricated one buys
    # no work), and this file is mostly comments. Bare it reads 28,739 B; what a
    # host downloads is a third of that. A ratchet on the unstripped number
    # would price every explanatory comment as if it shipped.
    #
    # THE CSS IS NOT STRIPPED and is a third of the figure. jsstrip.py is
    # JavaScript-only and cssgraph.py only derives player.css from styles.css,
    # so inlineplayer.css ships every word of its own reasoning. That is a real
    # 8 KB and it is left alone deliberately: it is the smaller half, it is the
    # part a host is most likely to read before overriding something, and
    # inventing a third asset pipeline to save 5 KB is not a trade this project
    # should make twice.
    #
    # AND THE CSS IS WHERE THIS RATCHET BITES FIRST -- a paragraph there is
    # bandwidth somebody else pays for. Product reasoning belongs in
    # inlineplayer.js's header, where jsstrip removes it from the response; the
    # stylesheet keeps the numbers and a pointer. That carve has twice been the
    # difference between a raise and none.
    #
    # THE RULES, which are what survives of the per-raise history git holds:
    #
    #   PIN JUST ABOVE THE MEASURED FLOOR, every time.
    #
    #   SPEND AGAINST A RAISE BEFORE ASKING FOR IT -- move prose out of the CSS,
    #   compact the module, delete what the new code replaces.
    #
    #   SAY WHICH CALLER PAYS. The transport on the player handle is used by
    #   /library, not by a feed, so a feed pays for something it never runs:
    #   that is the honest cost of three surfaces that cannot disagree about how
    #   a drawing replays, and carving it out would put a second request on the
    #   profile to save a third of a kilobyte on the feed. The loop control, by
    #   contrast, is paid for by the caller that wants it.
    #
    #   A NUMBER IN PROSE IS NOT CHECKED. Two ratchets in this tree once stated
    #   contradictory sizes for lib/audiosession.js, each looking corroborated
    #   by the other, and the stale one was quietly holding 500 B of slack open.
    #   An outside review caught it; no gate could.
    #
    #   MEASURE A FEATURE ON ONE SURFACE WITH IT ABSENT. The obvious
    #   cross-surface comparison is confounded -- an opaque control scores worse,
    #   because the two players fit the drawing to different boxes.
    # v315: 37,200 -> 36,800. The title line cost ~340 B of CSS and was paid
    # for by moving ~740 B of the stylesheet's header, which was reasoning
    # rather than values, into inlineplayer.js's (stripped) header. Measured
    # after both: 36,763 B.
    EMBED_RATCHET = 36_800
    # THE RATCHET MEASURES DISPLAY, NOT COMPOSE, and the two are separate costs
    # paid by separate pages. Excluded here and measured on its own below:
    #   feed.js          the PREVIEW PAGE's own script (fetch the listing, clone
    #                    the macro) — a host writes that loop themselves.
    #   lib/composehost  the pad button's lifecycle. A host page that only shows
    #                    Skribls in a feed never composes one, so charging every
    #                    such page for it would price a cost nobody on that page
    #                    pays — the same reader-is-not-the-writer split that put
    #                    the card compositor in lib/postedcard.js.
    _compose_only = ("feed.js", "composehost.js")
    _all_urls = sorted(set(re.findall(
        r'(?:src|href)="([^"]*/static/skribl/[^"]+)"', feed_html)))
    embed_urls = [u for u in _all_urls
                  if not any(n in u for n in _compose_only)]
    total = 0
    served = {}
    for u in embed_urls:
        raw = urllib.request.urlopen(BASE + u if u.startswith("/") else u,
                                     timeout=20).read()
        served[u.split("/static/skribl/")[-1].split("?")[0]] = len(raw)
        total += len(raw)
    # The count is pinned so a new asset cannot join the embed unnoticed; the
    # loop above is what proves each one is actually served, because urlopen
    # raises on a 404. Named for the count it checks — it used to be called
    # "every asset the embed macro names is one the server serves", which is
    # the loop's job and not this line's.
    check("the embed macro names exactly the six assets a host pays for",
          len(embed_urls) == 6, str(embed_urls))
    _embed_margin = EMBED_RATCHET - total
    check(f"the in-post player costs a host no more than {EMBED_RATCHET:,} bytes "
          f"of CSS and JavaScript",
          total <= EMBED_RATCHET,
          f"{total:,} B served ("
          + (f"{_embed_margin:,} B of margin left" if _embed_margin >= 0
             else f"OVER by {-_embed_margin:,} B") + "): "
          + ", ".join(f"{k} {v:,}" for k, v in served.items()))

    # THE COMPOSE COST, on its own ratchet. A host's composer page pays this and
    # a host's feed does not, so blurring the two into one number would hide
    # whichever grew. lib/composehost.js is the whole of Skribl's contribution
    # to the host side of compose mode — feed.js is this preview page's, not a
    # host's, and is excluded from both.
    COMPOSE_RATCHET = 4_000
    _ch = [u for u in _all_urls if "composehost.js" in u]
    check("the feed page loads lib/composehost.js exactly once",
          len(_ch) == 1, str(_ch))
    if _ch:
        _ch_bytes = len(urllib.request.urlopen(
            BASE + _ch[0] if _ch[0].startswith("/") else _ch[0], timeout=20).read())
        check(f"the compose lifecycle costs a host no more than "
              f"{COMPOSE_RATCHET:,} bytes",
              _ch_bytes <= COMPOSE_RATCHET, f"{_ch_bytes:,} B served")

    # ---- THE DRAWING KEEPS ITS SHAPE (v305) --------------------------------
    #
    # The box is 16:9 because that is the widest canvas a drawing can have, so
    # every other shape has to letterbox inside it. It did not: the canvas was
    # given a definite CSS width AND height, which max-width/max-height then
    # clamped one axis at a time, so a 9:16 drawing was painted 386x217 rather
    # than 122x217 -- stretched 216%. Wrong since the file was written, on the
    # feed and in every host's embed, and caught by the owner on the profile's
    # stage, where it is large enough to see.
    #
    # MEASURED ON THE RENDER, not on the CSS: the aspect the eye gets is the
    # canvas's own bounding box, and it must equal the aspect of the bitmap
    # that was drawn. Three shapes, because the error's size depends on how far
    # the drawing is from 16:9 and one landscape fixture would have shown a
    # third of it. Two widths, because the box is fluid.
    print("\nIN-POST — a drawing keeps its own aspect in a 16:9 box")
    for _label, _cw, _chh in (("9:16", 450, 800), ("4:3", 816, 612), ("1:1", 700, 700)):
        _pts = [{"x": 30 + i * 8, "y": 30 + i * 14, "color": "#e9ecf5", "size": 8,
                 "t": i * 30, "start": i == 0, "erase": False} for i in range(40)]
        _sid = json.loads(urllib.request.urlopen(urllib.request.Request(
            BASE + "/api/skribls", method="POST",
            data=json.dumps({"frames": [{"strokes": _pts, "strokeGroups": [len(_pts)]}],
                             "canvasSize": {"cssWidth": _cw, "cssHeight": _chh},
                             "title": f"aspect {_label}", "visibility": "public"}).encode(),
            headers={"Content-Type": "application/json"}), timeout=20).read())["id"]
        for _vw in (1280, 390):
            _ap = b.new_page(viewport={"width": _vw, "height": 900})
            browsing.goto(_ap, BASE, "/feed")
            _ap.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", _sid)
            _ap.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'",
                                  arg=_sid, timeout=15000)
            _ap.wait_for_timeout(1200)
            _m = _ap.evaluate("""(id) => {
                const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
                if (!c) return null;
                const r = c.getBoundingClientRect();
                const box = c.closest('.skribl-inline').getBoundingClientRect();
                return { drawn: c.width / c.height, shown: r.width / r.height,
                         w: Math.round(r.width), h: Math.round(r.height),
                         bw: Math.round(box.width), bh: Math.round(box.height) }; }""", _sid)
            _ap.close()
            check(f"{_label} at {_vw}px: the drawing is shown at its own aspect, not the box's",
                  _m and abs(_m["shown"] - _m["drawn"]) < 0.02,
                  f"drawn {_m['drawn']:.3f}, shown {_m['shown']:.3f} "
                  f"({_m['w']}x{_m['h']} in a {_m['bw']}x{_m['bh']} box)" if _m else "no canvas")
            # ...AND IT STILL FITS. A letterbox that overflows the box is a
            # different defect with the same cause, and a check on the aspect
            # alone would pass straight through it.
            check(f"{_label} at {_vw}px: ...and it fits inside the box",
                  _m and _m["w"] <= _m["bw"] + 1 and _m["h"] <= _m["bh"] + 1,
                  f"{_m['w']}x{_m['h']} in {_m['bw']}x{_m['bh']}" if _m else "no canvas")

    # ---------------------------------------------------------------------------
    # THE AUTHORED PHOTO FIT REACHES THE FEED BOX.
    #
    # The in-post player hard-coded a centred cover and discarded photo.fit, so a
    # photo composed with Fit was letterboxed in the editor and on /s/<id> and
    # CROPPED here. Owner, from the profile stage: "the pug in the background FIT
    # the screen on the editor and the original player. now he is cut off."
    #
    # ASSERTED ON PIXELS, NOT ON THE ARGUMENT PASSED TO drawImage. A spy on the
    # call would pass just as happily if the module returned nonsense, and a
    # substring search for "SkriblPhotoFit" in the source would pass on this very
    # comment. The fixture is a SOLID-COLOUR photo four times wider than it is
    # tall on a 4:3 canvas, so the two modes are not subtly different pictures:
    # contain paints a band and leaves the top and bottom showing the background,
    # cover paints every pixel. Sampling three rows tells them apart with no
    # appeal to how the code is written.
    print("\nPHOTO FIT — a feed box shows the shape the author composed")
    import base64 as _b64, io as _io                                    # noqa: E402

    def _solid_photo(w, h, rgb):
        try:
            from PIL import Image                                       # noqa: E402
        except ImportError:
            return None
        _buf = _io.BytesIO()
        Image.new("RGB", (w, h), rgb).save(_buf, format="PNG")
        return "data:image/png;base64," + _b64.b64encode(_buf.getvalue()).decode()


    def _split_photo(w, h, left, right):
        """Two flat halves with ONE hard vertical edge down the middle.

        A solid colour is useless for a blur probe: blurring it returns itself,
        so an assertion built on one would pass whether or not the blur ran.
        An edge is the only thing a blur can be seen in."""
        try:
            from PIL import Image                                       # noqa: E402
        except ImportError:
            return None
        _im = Image.new("RGB", (w, h), left)
        _im.paste(Image.new("RGB", (w // 2, h), right), (w // 2, 0))
        _buf = _io.BytesIO()
        _im.save(_buf, format="PNG")
        return "data:image/png;base64," + _b64.b64encode(_buf.getvalue()).decode()


    _PHOTO = _solid_photo(1000, 250, (0, 200, 120))
    _EDGE = _split_photo(800, 600, (0, 200, 120), (255, 72, 176))
    if _PHOTO is None:
        print("  (Pillow missing: the photo-fit pins cannot build a fixture)")
    else:
        def _post_photo(pg, photo, **ph):
            """Post one Skribl whose only variable is the photo's own state."""
            _spec = dict(fit="cover", offset={"x": 0.5, "y": 0.5}, zoom=1,
                         opacity=1, blur=0)
            _spec.update(ph)
            _spec["data"] = photo
            return pg.evaluate("""async ([spec]) => {
                const r = await fetch('/api/skribls', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        title: 'photo state', visibility: 'public',
                        playbackMode: 'replay',
                        canvasSize: {cssWidth: 800, cssHeight: 600},
                        frames: [{
                            strokes: [{x: 100, y: 100, color: '#ff48b0', size: 8, t: 0, start: true},
                                      {x: 700, y: 500, color: '#ff48b0', size: 8, t: 200}],
                            strokeGroups: [2],
                            background: {color: '#101418'},
                            photo: spec}]})});
                return (await r.json()).id; }""", [_spec])

        def _post_with_fit(pg, fit):
            return pg.evaluate("""async ([photo, fit]) => {
                const r = await fetch('/api/skribls', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        title: 'fit ' + fit, visibility: 'public',
                        playbackMode: 'replay',
                        canvasSize: {cssWidth: 800, cssHeight: 600},
                        frames: [{
                            strokes: [{x: 100, y: 100, color: '#ff48b0', size: 8, t: 0, start: true},
                                      {x: 700, y: 500, color: '#ff48b0', size: 8, t: 200}],
                            strokeGroups: [2],
                            background: {color: '#101418'},
                            photo: {data: photo, fit: fit, offset: {x: 0.5, y: 0.5},
                                    zoom: 1, opacity: 1, blur: 0}}]})});
                return (await r.json()).id; }""", [_PHOTO, fit])

        _fp = b.new_page(viewport={"width": 1280, "height": 900})
        browsing.goto(_fp, BASE, "/skribl-pad")
        _id_contain = _post_with_fit(_fp, "contain")
        _id_cover = _post_with_fit(_fp, "cover")
        _id_faded = _post_photo(_fp, _PHOTO, opacity=0.4)
        _id_sharp = _post_photo(_fp, _EDGE, blur=0) if _EDGE else None
        _id_blurred = _post_photo(_fp, _EDGE, blur=12) if _EDGE else None
        _fp.close()

        _rp = b.new_page(viewport={"width": 1280, "height": 900})
        browsing.goto(_rp, BASE, "/feed")

        def _painted(sid):
            """Play the box, then wait until it has ADOPTED its payload and
            painted a centre that differs from its corner -- a state that
            includes the lazy fetch and the photo decode, which a fixed 1200ms
            stood in for. On a timeout, carry on so the probe row reports."""
            _rp.evaluate("(id) => { const p = window.SkriblInline.find(id);"
                         " if (p) p.play(); }", sid)
            try:
                _rp.wait_for_function("""(id) => {
                    const p = window.SkriblInline.find(id);
                    const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
                    if (!p || !p.state().loaded || !c || c.width <= 300) return false;
                    const x = c.getContext('2d');
                    const a = x.getImageData(1, 1, 1, 1).data;
                    const m = x.getImageData(Math.round(c.width / 2), Math.round(c.height / 2), 1, 1).data;
                    return Math.abs(a[0] - m[0]) + Math.abs(a[1] - m[1]) + Math.abs(a[2] - m[2]) > 30; }""",
                    arg=sid, timeout=8000)
            except PWTimeout:
                pass

        def _rows(sid):
            """Play the box through the module's own API, then sample it."""
            _painted(sid)
            return _rp.evaluate("""(id) => {
                const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
                if (!c || c.width <= 300) return null;
                const x = c.getContext('2d');
                const at = (fy) => { const d = x.getImageData(Math.round(c.width * 0.5),
                                                              Math.round(c.height * fy), 1, 1).data;
                                     return [d[0], d[1], d[2]]; };
                return {size: [c.width, c.height], top: at(0.06), mid: at(0.5), bot: at(0.94)};
            }""", sid)

        def _is_photo(px):
            return px and abs(px[0]) < 60 and abs(px[1] - 200) < 60 and abs(px[2] - 120) < 60

        _c = _rows(_id_contain)
        check("the probe is real: the contain box adopted a payload and painted",
              _c is not None and _c["size"][0] > 300 and _is_photo(_c["mid"]),
              f"{_c} — without the photo on screen at all, the rows below say nothing")
        if _c:
            check("a photo authored CONTAIN is letterboxed in the feed box, not cropped",
                  not _is_photo(_c["top"]) and _is_photo(_c["mid"]) and not _is_photo(_c["bot"]),
                  f"top={_c['top']} mid={_c['mid']} bot={_c['bot']} — photo at every "
                  f"row is cover, which is the authored fit being discarded")

        _v = _rows(_id_cover)
        check("the probe is real: the cover box adopted a payload and painted",
              _v is not None and _v["size"][0] > 300, str(_v))
        if _v:
            # THE OTHER ARM, so the assertion above cannot be satisfied by a player
            # that simply letterboxes everything it is given.
            check("...and a photo authored COVER still fills it",
                  _is_photo(_v["top"]) and _is_photo(_v["mid"]) and _is_photo(_v["bot"]),
                  f"top={_v['top']} mid={_v['mid']} bot={_v['bot']}")
        # ---- OPACITY AND BLUR, the last known fidelity gap ------------------
        #
        # THE HEADER OF inlineplayer.js DECLARED THIS ONE OPEN, which is the
        # honest half; the other half is that a photo authored at 40% painted
        # opaque in every feed box and in every host embed, while the editor
        # and /s/<id> both faded it. Those two use a real <img> behind the
        # canvas and let CSS do it; a feed box has one canvas and nothing else,
        # so the same choice has to be made with globalAlpha and ctx.filter.
        #
        # TWO PROPERTIES, TWO ASSERTIONS, never one. A single "the photo looks
        # different" row passes while one of the pair is still discarded, which
        # is the same trap as pinning one arm of a two-state control: an
        # opacity row is green on a tree that drops the blur, and a blur row is
        # green on a tree that drops the opacity. Each is measured by the thing
        # only it can change.
        def _mid(sid):
            _painted(sid)
            return _rp.evaluate('''(id) => {
                const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
                if (!c || c.width <= 300) return null;
                const x = c.getContext('2d');
                const px = (fx, fy) => { const d = x.getImageData(Math.round(c.width * fx),
                                                                 Math.round(c.height * fy), 1, 1).data;
                                         return [d[0], d[1], d[2]]; };
                /* Columns 4px either side of the photo's own hard edge, on an
                   800px-wide drawing. The first version sampled at 48% and
                   52% -- 16px out -- where CSS blur(12px) (stdDev 6px, so
                   2.7 sigma) has almost entirely resolved: it read 128 sharp
                   against 106 blurred and called a working blur missing. The
                   blur has to be measured where it acts. */
                return {mid: px(0.5, 0.5), lo: px(0.495, 0.5), hi: px(0.505, 0.5)}; }''', sid)

        _f = _mid(_id_faded)
        check("the probe is real: the faded box adopted a payload and painted",
              _f is not None, str(_f))
        if _f:
            # rgb(0,200,120) at 40% over the authored ground rgb(16,20,24) is
            # about (6, 92, 62). Full strength is (0, 200, 120). The green
            # channel is the discriminator and it is not close.
            _g = _f["mid"][1]
            check("a photo authored at 40% is FADED in the feed box, not opaque",
                  60 < _g < 130,
                  f"mid={_f['mid']} — green {_g}; ~92 is the authored 40% over "
                  f"the background, ~200 is the opacity being discarded")

        if _id_sharp and _id_blurred:
            _s2, _b2 = _mid(_id_sharp), _mid(_id_blurred)
            check("the probe is real: both edge boxes adopted a payload and painted",
                  _s2 is not None and _b2 is not None, f"sharp={_s2} blurred={_b2}")
            if _s2 and _b2:
                # ANTI-VACUITY FIRST: the unblurred fixture must actually show a
                # step, or "the blurred one is smoother" compares two smooth
                # things and means nothing.
                _step = abs(_s2["lo"][1] - _s2["hi"][1])
                check("the unblurred fixture really does carry a hard edge",
                      _step > 100,
                      f"lo={_s2['lo']} hi={_s2['hi']} — a {_step}-point step; "
                      f"without one there is nothing for a blur to soften")
                _soft = abs(_b2["lo"][1] - _b2["hi"][1])
                check("...and a photo authored BLURRED is soft across that edge",
                      _step > 100 and _soft < _step * 0.6,
                      f"the step is {_step} sharp against {_soft} blurred — a "
                      f"blurred photo that keeps its edge is the blur being "
                      f"discarded, which is what a feed box used to do")
        _rp.close()

    b.close()

# ---------------------------------------------------------------------------
# THE PLAYER'S INSIDES ARE WRITTEN ONCE.
#
# skribl_feed.html used to hand-copy twenty-odd lines of the macro's internals
# for its draft box — the canvas, the veil, the mute and loop buttons — because
# a DRAFT has no id and the macro required one. That is the arrangement where
# the macro grows an element and the copy does not, and it was found only by
# building examples/host_app, whose author had no macro to call and would have
# copied the same block a third time.
#
# There is a skribl_inline_draft() macro now and both callers use it. This gate
# is on the SHAPE that made the copy possible: no template outside the macro
# file may write the player's internal class names itself.
_INTERNALS = ("skribl-inline-canvas", "skribl-inline-veil",
              "skribl-inline-mute", "skribl-inline-loop",
              "skribl-inline-prog", "skribl-inline-poster")
_macro_file = "_skribl_inline_player.html"
_offenders = []
for _tpl in sorted((ROOT / "skribl" / "templates").rglob("*.html")):
    if _tpl.name == _macro_file:
        continue
    _txt = _tpl.read_text(encoding="utf-8")
    _hits = [c for c in _INTERNALS if c in _txt]
    if _hits:
        _offenders.append(f"{_tpl.name}: {', '.join(_hits)}")
for _tpl in sorted((ROOT / "examples").rglob("*.html")) if (ROOT / "examples").exists() else []:
    _txt = _tpl.read_text(encoding="utf-8")
    _hits = [c for c in _INTERNALS if c in _txt]
    if _hits:
        _offenders.append(f"examples/{_tpl.name}: {', '.join(_hits)}")
check("no template hand-writes the in-post player's internals — they are the "
      "macro's, once",
      not _offenders, "; ".join(_offenders))
check("and there IS a draft macro, so a host previewing one need not copy them",
      "macro skribl_inline_draft" in
      (ROOT / "skribl" / "templates" / "skribl" / _macro_file).read_text(encoding="utf-8"))


print("\nINLINE — the title line under the player (v315)")
# The owner picked it from a mock: the drawing's name under the player, the
# way a caption follows a photo. OPT-IN through the macro, so a host that
# prints the title in its own layout, and every template written before this,
# renders exactly what it did. Rendered in-process here because the question is
# what the MACRO emits; the feed below is the browser half.
sys.path.insert(0, str(ROOT))
from flask import render_template_string as _rts
from app import app as _app
_T = ("{% from 'skribl/_skribl_inline_player.html' import skribl_inline %}"
      "{{ skribl_inline('abc123', title=t) }}")
with _app.test_request_context():
    _with = _rts(_T, t='Flower <i>for</i> you & me')
    _without = _rts(_T, t=None)
check("with a title, the macro puts one title line AFTER the player, not inside it",
      _with.count('class="skribl-inline-title"') == 1
      and _with.index('class="skribl-inline-title"') > _with.rindex("</div>"),
      _with[-200:])
check("...the title is escaped, never markup",
      "Flower &lt;i&gt;for&lt;/i&gt; you &amp; me" in _with and "<i>for</i>" not in _with,
      _with[-160:])
check("without one, nothing is rendered -- an existing host's template is unchanged",
      "skribl-inline-title" not in _without, _without[-120:])

try:
    from playwright.sync_api import sync_playwright as _spw
except Exception:
    _spw = None
if _spw:
    _tb = {"title": "Title line fixture", "version": 2, "schemaVersion": 2, "visibility": "public",
           "canvasSize": {"cssWidth": 800, "cssHeight": 600},
           "frames": [{"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6, "t": 0},
                                   {"x": 300, "y": 200, "color": "#fff", "size": 6, "t": 99}],
                       "strokeGroups": [2]}]}
    _rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_tb).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(_rq, timeout=20) as _r:
        _tid = json.loads(_r.read().decode())["id"]
    with _spw() as _pw:
        _b = _pw.chromium.launch()
        _pg = _b.new_page(viewport={"width": 390, "height": 844})
        browsing.goto(_pg, BASE, "/feed")
        _pg.wait_for_timeout(1500)
        _tl = _pg.evaluate("""(id) => {
            const box = document.querySelector('.skribl-inline[data-skribl-id="' + id + '"]');
            if (!box) return null;
            const post = box.parentElement;
            const line = post.querySelector('.skribl-inline-title');
            const bodies = [...post.querySelectorAll('.pbody')].map(e => e.textContent);
            if (!line) return { line: null, bodies };
            const lr = line.getBoundingClientRect(), br = box.getBoundingClientRect();
            return { name: line.querySelector('b').textContent, kind: line.querySelector('span').textContent,
                     below: lr.top >= br.bottom - 1, h: lr.height, bodies }; }""", _tid)
        check("the feed shows a post's title on a line under its player, marked Skribl",
              bool(_tl) and _tl.get("name") == "Title line fixture" and _tl.get("kind") == "Skribl"
              and _tl.get("below") and _tl.get("h", 0) > 0, str(_tl))
        check("...and a post with no caption does not print its title twice",
              bool(_tl) and "Title line fixture" not in _tl.get("bodies", []), str(_tl))

        # PLACEMENT (v315): where the marker is, the drawing is. And the title
        # line is the drawing's NAME: never the default, never a copy of the
        # post's own opening words (the demo composer derives one from the
        # other when the drawing has no name).
        def _mk(title, caption):
            _bd = dict(_tb, title=title, caption=caption)
            _rq2 = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_bd).encode(),
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(_rq2, timeout=20) as _r2:
                return json.loads(_r2.read().decode())["id"]
        _placed = _mk("Named drawing", "Above the drawing.\n[skribl]\nBelow the drawing.")
        _plain = _mk("Plain named", "Just words, no marker.")
        _derived = _mk("Morning sketch on the bus", "Morning sketch on the bus")
        _untitled = _mk("Untitled Skribl", "Words only.")
        browsing.goto(_pg, BASE, "/feed")
        _pg.wait_for_timeout(1500)
        _SHAPE = """(id) => { const box = document.querySelector('.skribl-inline[data-skribl-id="' + id + '"]');
            if (!box) return null;
            return [...box.parentElement.children].map(e => e === box ? 'PLAYER'
              : e.classList.contains('pbody') ? 'TEXT:' + e.textContent
              : e.classList.contains('skribl-inline-title') ? 'TITLE:' + e.querySelector('b').textContent
              : '-').filter(x => x !== '-'); }"""
        _s = _pg.evaluate(_SHAPE, _placed)
        check("a marker puts the drawing between the words: text, player, title, text",
              _s == ["TEXT:Above the drawing.", "PLAYER", "TITLE:Named drawing", "TEXT:Below the drawing."],
              str(_s))
        _s = _pg.evaluate(_SHAPE, _plain)
        check("...no marker keeps the old order: text, then the player",
              _s == ["TEXT:Just words, no marker.", "PLAYER", "TITLE:Plain named"], str(_s))
        _s = _pg.evaluate(_SHAPE, _derived)
        check("...a title that is only the post's opening words gets no title line",
              _s == ["TEXT:Morning sketch on the bus", "PLAYER"], str(_s))
        _s = _pg.evaluate(_SHAPE, _untitled)
        check("...and neither does the Untitled Skribl default",
              _s == ["TEXT:Words only.", "PLAYER"], str(_s))
        _b.close()


passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
