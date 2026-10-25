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
    # On the dark canvas, picked: a new drawing starts on the theme's ground,
    # which is Paper in this browser's light scheme (lib/canvasground.js), and
    # the comparisons below were measured with ink standing ABOVE its ground's
    # brightness (grid_diff, ink_mass). A light ground turns that over.
    pg.evaluate("() => document.querySelector('.bg-swatch[data-bg=\"#0d0f14\"]').click()")
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
    # IN THE LINE UNDER THE DRAWING since v322 ("the loop button comes off
    # the drawing"); a box without the line keeps it inside.
    _LOOP_BTN = """(id) => { const el = document.querySelector('[data-skribl-id="' + id + '"]');
        return el.querySelector('.skribl-inline-loop')
          || (el.nextElementSibling && el.nextElementSibling.querySelector('.skribl-inline-loop')); }"""
    loop_state = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const ln = el.nextElementSibling;
        const btn = el.querySelector('.skribl-inline-loop')
          || (ln && ln.querySelector('.skribl-inline-loop'));
        return { present: !!btn, pressed: btn && btn.getAttribute('aria-pressed'),
                 noloop: el.classList.contains('is-noloop') }; }""", id_m)
    check("a post carries a loop control", loop_state["present"], json.dumps(loop_state))
    check("and it starts on, which is what a post did before it existed",
          loop_state["pressed"] == "true" and loop_state["noloop"] is False,
          json.dumps(loop_state))
    # LIT LOOP KEEPS ITS ICON ON A HOST THAT NAMES ITS OWN ACCENT. The chip
    # once took its ink and edge from --accent over a see-through ground;
    # skribls.net defines --accent, and on its light page the chip read as a
    # violet square with no icon. In the line (v322) it is lit the way the
    # speed beside it is -- the page's own text on an accent tint -- so the
    # question is asked of what the eye gets: the icon's ink against its
    # ground laid over the page, with the host's accent set, on a dark page
    # and then, AFTER LOAD, a light one (an accent mixed toward currentColor
    # stayed the dark page's colour there: 2.43, the first run of this check;
    # Chrome never recomputes such a mix when the page's colour changes).
    # 3:1 is the floor for a control's graphics (WCAG 1.4.11).
    host_look = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const b = el.querySelector('.skribl-inline-loop')
          || el.nextElementSibling.querySelector('.skribl-inline-loop');
        const cx = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
        cx.canvas.width = cx.canvas.height = 1;
        const px = (...layers) => { cx.clearRect(0, 0, 1, 1);
          for (const c of layers) { cx.fillStyle = c; cx.fillRect(0, 0, 1, 1); }
          return Array.from(cx.getImageData(0, 0, 1, 1).data).slice(0, 3); };
        const lum = (c) => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
          return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
        const out = {};
        b.style.setProperty('--accent', '#6d4cf0');
        /* The button fades its colour over 0.15s, so a read straight after
           the switch is the fade's first frame; the settled colour is the
           question, so the fade is held off while it is asked. */
        b.style.transition = 'none';
        for (const [name, page, ink] of [['dark', '#0b0d12', '#e8eaef'], ['light', '#ffffff', '#1d1a2b']]) {
          document.body.style.setProperty('background', page, 'important');
          document.body.style.setProperty('color', ink, 'important');
          const c = getComputedStyle(b);
          const ground = px(page, c.backgroundColor), icon = px(page, c.backgroundColor, c.color);
          const L1 = lum(icon), L2 = lum(ground);
          out[name] = { ground: ground, icon: icon,
                        ratio: Math.round((Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05) * 100) / 100 };
        }
        b.style.removeProperty('--accent'); b.style.removeProperty('transition');
        document.body.style.removeProperty('background'); document.body.style.removeProperty('color');
        return out; }""", id_m)
    check("lit Loop's icon stands out from its ground on a dark host and a light one, "
          "whatever the host calls --accent",
          host_look["dark"]["ratio"] >= 3 and host_look["light"]["ratio"] >= 3,
          json.dumps(host_look))

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

    # TURN THE LOOP OFF and let the replay run past its end. (_LOOP_BTN finds
    # it in the line under a post, or in a box without one.)
    pg.evaluate("(id) => (" + _LOOP_BTN + ")(id).click()", id_m)
    after_click = pg.evaluate("""(id) => {
        const el = document.querySelector('[data-skribl-id="' + id + '"]');
        return { noloop: el.classList.contains('is-noloop'),
                 pressed: (""" + _LOOP_BTN + """)(id).getAttribute('aria-pressed') }; }""", id_m)
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
    pg.evaluate("(id) => (" + _LOOP_BTN + ")(id).click()", id_m)
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
    # PLAYING FIRST. This read 'idle' after stopAll() above whatever scrolling
    # did, so it could not fail; the post is in view and playing, looped so
    # it is still playing when it is scrolled past.
    pg.evaluate("""(id) => { document.querySelector('[data-skribl-id="' + id + '"]').scrollIntoView({block: 'center'});
        const p = window.SkriblInline.find(id); p.setLoop(true); p.play(); }""", id_b)
    try:
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing' && window.SkriblInline.find(id).state().elapsedMs > 50",
                             arg=id_b, timeout=8000)
    except PWTimeout:
        pass
    pg.evaluate("""() => {
        const spacer = document.createElement('div');
        spacer.style.height = '250vh';
        document.body.appendChild(spacer);
        window.scrollTo(0, document.body.scrollHeight); }""")
    # The IntersectionObserver's callback is the state; wait for it, not 1200ms.
    # PAUSED, NOT SETTLED (the owner, after v324: "It goes away even if it's
    # playing and I scroll it out of view"): it waits where it was, and
    # carries on when it is back in view.
    _was = pg.evaluate("(id) => window.SkriblInline.find(id).state().state", id_b)
    try:
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state !== 'playing'",
                             arg=id_b, timeout=5000)
    except PWTimeout:
        pass
    scrolled = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_b)
    check("scrolling a playing post out of view pauses it where it was",
          _was == "playing" and scrolled["state"] == "paused" and scrolled["elapsedMs"] > 0,
          f"{_was} -> {scrolled['state']} at {scrolled['elapsedMs']} ms — a feed that keeps "
          f"drawing off-screen burns battery for nobody, and one that resets it loses the drawing")
    pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').scrollIntoView({block: 'center'})", id_b)
    try:
        pg.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'",
                             arg=id_b, timeout=5000)
    except PWTimeout:
        pass
    back = pg.evaluate("(id) => window.SkriblInline.find(id).state()", id_b)
    check("...and back in view, it carries on from there",
          back["state"] == "playing" and back["elapsedMs"] >= scrolled["elapsedMs"],
          f"{back['state']} at {back['elapsedMs']} ms")
    pg.evaluate("() => window.SkriblInline.stopAll()")
    pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    pg.wait_for_timeout(300)

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
                               " return H.plan("
                               "[{hold:2},{hold:4},{hold:2}], 6).cycle; }")
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
    # The clock's progress is 0 for a still page AND for a drawing page at the
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
        # fixture. The clock's progress is exactly 0 only when the clock is AT a
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
    # dueCount() releases the last point at progress 1, and the clock owns a
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
    # A BOX WITH NO SIZE. Every fixture here carries its canvas size, so every
    # post in this feed takes its drawing's shape (v322) and shows its poster
    # by fitPoster(); the band crop below is what a post WITHOUT a size shows
    # -- a row from before the column, a host that does not pass it -- so it
    # is measured on one: the page's own template, cloned as feed.js clones
    # it, with no size written in.
    cp.evaluate("""(id) => {
        const t = document.getElementById('skriblPostTpl').content.cloneNode(true);
        const box = t.querySelector('[data-skribl-inline]');
        box.setAttribute('data-skribl-id', id); box.id = 'bandBox';
        const img = box.querySelector('.skribl-inline-poster');
        img.setAttribute('src', img.getAttribute('src').replace('__ID__', id));
        const holder = document.createElement('article');
        holder.appendChild(t);
        document.getElementById('feedList').appendChild(holder);
        window.SkriblInline.mount(holder); }""", id_a)
    geom = cp.evaluate("""() => {
        const el = document.getElementById('bandBox');
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
    # RAISED (Blooby's card, owner: the card drawn once and kept under the
    #   waving pages), for one named cost: +1,014 B, the page underneath --
    #   lib/holdtiming.js underOf() (+457) and this player painting it once,
    #   offscreen, and drawing it under each page in its range (+684). Spent
    #   first: the round before it (the looped stretch) had already retired the
    #   old clock and moved the export's slot order out of the lib; nothing in
    #   these paths was left to delete. 37,814 B measured.
    # RAISED (owner: "squeeze the long pauses" ... "raise limits"), for one
    #   named cost: +81 B, lib/holdtiming.js's squeezed clock (playTimes), which
    #   spanMs and dueCount now read so a drawing page's pauses play as a beat.
    #   Spent first: the clock was compacted, spanMs lost a check the fallback
    #   made dead, dueCount a Math.max the clock made dead. 37,931 B measured.
    # RAISED (the owner's replay picks: "the author picks the default speed"),
    #   for one named cost: +289 B, the author's start -- a post's `playSpeed`
    #   read in adopt() by lib/replayline.js fromPost()'s rule, written out
    #   here rather than loading that module (7.8 KB a host would pay), and a
    #   Flip resetting it. Spent first: nothing in adopt() was dead; the rule
    #   is one loop and one expression. 38,239 B measured.
    # RAISED (the in-post player, owner: "bring Pad's watching experience into
    #   the post ... it's critical"; "all yes"), for four named costs, every
    #   one paid by every page that shows a post, because the line is there at
    #   rest:
    #     lib/replayline.js  +8,347  the Pad's own line and scrubber -- the
    #                                module, not a copy, so a post cannot say
    #                                or offer speeds differently from the Pad
    #                                and /s/<id> (this ratchet once paid 289 B
    #                                to keep it out; the line is the reason to
    #                                pay for it now)
    #     lib/scrubkeys.js   +1,604  the keyboard half every scrubber here has
    #     inlineplayer.css   +4,433  the line, the shaped box, the v4 button
    #     inlineplayer.js    +5,646  the line at rest from the listing, a
    #                                Flip's pages painted in the scrubber (here,
    #                                through the module's `draw` hook, so the
    #                                Pad and /s/<id> do not carry them), the
    #                                stored shape read, scrub, speed
    #   Spent first: the sheet's new rules carry no prose (their reasoning is
    #   in the script's header) and are one line each; the old wash behind the
    #   play button and its shadow are gone. 58,227 B measured; then +42 B
    #   when the words row stopped taking taps (A11Y 10 found the scrubber's
    #   and loop's 44px reach covered where they meet it): 58,292 B measured.
    # RAISED (the Pad plan, step 3, for this player: a long post scrubs from the
    #   nearest copy of its ink, not from zero), for one named cost, after
    #   spending: +3,831 B --
    #     lib/seekcache.js  +2,810  the copies -- the module the Pad's preview
    #                               and /s/<id> already use -- with the source
    #                               and put hooks this player needs, because its
    #                               photo is a layer of its own that an eraser
    #                               reveals, so it copies its ink and not its
    #                               canvas
    #     inlineplayer.js   +1,021  the compositor's ink layer and seed, the
    #                               repaint that starts from a copy, and the
    #                               suite's readout of where a seek started
    #   Spent first (-458 in inlineplayer.js): the copies are taken from inside
    #   replayTo's own loop (the module's tap) rather than by a second draw loop
    #   of its own. 62,123 B measured.
    # RAISED (the first far jump races there, owner: "yes, A" from the mock),
    #   for one named cost, after spending: +1,416 B, paid by every page that
    #   shows a post, because a scrub is there at rest --
    #     lib/seekcache.js  +790  far() and race(): when a jump races, and its
    #                             slices a frame -- the module /s/<id> and the
    #                             Pad use, so the three cannot race differently
    #     inlineplayer.js   +626  the race in render(), Play waiting for the
    #                             landing (and a tap, a key or a drag taking it
    #                             back), and the suite's readout of a race
    #   Spent first (-204 in inlineplayer.js, -74 in lib/seekcache.js): the
    #   tap and the key go through toggle() rather than each carrying it, the
    #   playing and paused looks are one helper, and the module dropped what no
    #   caller read. 63,539 B measured.
    # RAISED (a drawing that can't be shown says so kindly, the owner's pick
    #   from the skribls.net mock), for one named cost: +1,432 B, paid by every
    #   page that shows a post, because the words have to be there before
    #   anything fails --
    #     inlineplayer.js   +1,017  the two answers (gone, and worth another
    #                               try), their words, the box's name, the
    #                               retry, and the pencil mark
    #     inlineplayer.css    +415  the page's ground and type, the rest of the
    #                               box hidden and the line stepping away; the
    #                               old dark error pill's rule is gone
    #   64,971 B measured.
    # RAISED (a Flip's link opens on the page its card shows, the owner's pick
    #   A from the Blooby mock), for one named cost: +296 B, lib/holdtiming.js
    #   posterOf, the poster page as one rule for Flip's card and the /s/
    #   player. WHICH CALLER PAYS: every page that shows a post, for a function
    #   only the /s/ player and Flip run -- this player rests on the card
    #   itself. Carving it into a module of its own would put a request on both
    #   of those to save a host less than a third of a kilobyte, the trade the
    #   rules above already declined once. Spent first: posterOf was written as
    #   two findIndex calls rather than loops (-22). 65,267 B measured.
    # RAISED (the Gallery's cards take their drawing's shape one to a row and
    #   stay 16:9 two to a row, the owner's pick C from the Gallery mock), for
    #   one named cost: +119 B in inlineplayer.js, me.shape(on), the box's
    #   shape switched either way after it is attached, with the poster framed
    #   again for the new box. WHICH CALLER PAYS: every page that shows a post,
    #   for a switch only the Gallery throws today; it is the same few lines
    #   that shape a post at attach, made callable, so a host pays for the
    #   wrapper and not for a second copy. Spent first: its note is one line
    #   (fitPoster's own says why the poster must follow the box). 65,386 B
    #   measured.
    # RAISED (a bug fix, owner's iPhone: "Why is it jumpy ... It does it at 1x
    #   too"), for one named cost: +485 B -- lib/holdtiming.js untie(), which
    #   spreads a bundle of points that arrived together over the moment
    #   before it, and inlineplayer.js's line applying it to the timeline.
    #   WHICH CALLER PAYS: every page that shows a post, and every post it
    #   shows plays smoothly for it. Spent first: one line per caller, untie()
    #   taking the timeline as it is (-137 here). 65,871 B measured.
    # RAISED (a Gallery card says how it was drawn, "drawn in 15 sec", in the
    #   drawing's corner, the owner's pick A after v324), for one named cost:
    #   +722 B -- inlineplayer.js reading the post's line where there is no
    #   line to put it in, and writing the drawing's corner where fitPoster
    #   already knows it; inlineplayer.css the pill (.is-says), three rules.
    #   WHICH CALLER PAYS: every page that shows a post, for a look only a
    #   line-less box takes (the Gallery's cards); a host with the line
    #   already says it there. Spent first: the CSS is three dense rules and
    #   one line of pointer. 66,593 B measured.
    # RAISED (a bug fix, owner's iPhone after #516: "It goes away when scrolled
    #   out of sight then come back and blank screen"; "It goes away even if
    #   it's playing and I scroll it out of view"), for one named cost:
    #   +280 B -- the observer pausing a post that leaves the screen and
    #   carrying it on when it comes back, where it settled it to the start;
    #   settle() putting the card back on top (the canvas at time zero was
    #   left over it: a blank page) and look() bringing the canvas back on a
    #   play; inlineplayer.css the pill's spinner where its arrow was. WHICH
    #   CALLER PAYS: every page that shows a post, and every post scrolled
    #   past keeps its place for it. 66,873 B measured.
    # RAISED (the Gallery card's pill is glass, light over a light drawing and
    #   dark over a dark one, the owner's pick D after v324), for one named
    #   cost: +1,387 B -- inlineplayer.css the glass, its dark tone and its
    #   hover (dense rules, one line of pointer); inlineplayer.js tone(),
    #   reading the card's lower-left off the card already on screen, over
    #   white so a see-through card reads as it shows. WHICH CALLER PAYS:
    #   every page that shows a post, for a look only a line-less box takes
    #   (the Gallery's cards). 68,260 B measured.
    # RAISED (the owner's P5, pick A: the scrubber's clock rides over the
    #   finger), for one named cost: +394 B -- lib/replayline.js placing the
    #   bubble over a finger or a pen and keeping it on screen (+305), and
    #   inlineplayer.css fading the words under the line while it shows
    #   (+89). WHICH CALLER PAYS: every page that shows a post, because the
    #   scrubber is there at rest; it is the Pad's module, so a post cannot
    #   place the clock differently from the Pad and /s/<id>. 68,654 B measured.
    # RAISED (the Gallery card's fade takes its colours from the drawing, the
    #   owner's pick A after v326: "Smart fade is good"), for one named cost:
    #   +229 B -- inlineplayer.js tone()'s read of the card image becomes
    #   readCard(), handed to lib/fullbar.js with the card's frame (its width,
    #   the plate's round and inset), so the pill's glass and the card's fade
    #   read one drawing one way. The fade's own arithmetic, its read of the
    #   canvas and where the drawing is all live in lib/fullbar.js, which a
    #   host never loads (they were 1,912 B here in the first build). WHICH
    #   CALLER PAYS: every page that shows a post, for a look only the
    #   Gallery's cards take. 68,883 B measured.
    # RAISED (one full screen: the Gallery's and the Library's is the link
    #   page's, the owner's "why can't the gallery player look like the
    #   others? with the same scrubber and all?", then "All yes"), for one
    #   named cost: +449 B -- inlineplayer.js handing the line a post wears
    #   under it to a host's band (me.band), the clock it shows (me.clock: the
    #   artist's time, as the link page's) and the drawing's ground
    #   (me.ground), the wiring that was the line's own made one function
    #   (+431); inlineplayer.css the box in full screen as the whole frame, no
    #   border, round or ground of its own, so the drawing's reaches the
    #   screen's edges (+18). WHICH CALLER PAYS: every page that shows a post,
    #   for a band only the Gallery and the Library build; the scrubber and
    #   the speeds are the line's, so a host pays for the handle and not for
    #   a second copy. 69,332 B measured.
    # RAISED (the Gallery card's pill centred on the drawing's foot and always
    #   inside it, the owner's pick A after v326, and its glass picking by
    #   what reads, a "yes" from the same mock), for one named cost: +928 B --
    #   inlineplayer.js fitSays(), the words kept to the time on a drawing too
    #   narrow for them, measured on the real pill and again on a resize; the
    #   box's name carrying "drawn in ..."; tone() reading under the pill's
    #   new place and the contrast of both glasses' words there, with lum()
    #   (+890); inlineplayer.css the veil spanning the drawing and the words
    #   on one line (+38). WHICH CALLER PAYS: every page that shows a post,
    #   for a look only a line-less box takes (the Gallery's cards). 70,260 B
    #   measured.
    # RAISED (the in-post box's name says what a tap on it does next, after
    #   v326, the viewing pages' review: it said "Play this Skribl" while it
    #   played), for one named cost: +99 B -- inlineplayer.js look() naming
    #   the box "Pause this Skribl" while it plays and its own name again when
    #   it stops. WHICH CALLER PAYS: every page that shows a post, for a name
    #   a screen reader reads on every post. 70,359 B measured.
    # LOWERED (Blooby's first hello, as C): -9 B, attach()'s maxDpr, the
    #   hello's alone, becoming `dpr`, the name the player already gives that
    #   number. 70,350 B measured.
    # RAISED (a Flip's end, after v327: one that played once with Loop off,
    #   was taken to its end or sat at rest with no card showed its first
    #   page again, blank where that page draws itself), for one named cost:
    #   +131 B -- inlineplayer.js render() painting a Flip's last page whole
    #   at its end, as the editor's own replay does. Spent first: the rule is
    #   one test and one object, and the hello's workaround for the old end is
    #   gone (lib/hello.js, outside this sum). WHICH CALLER PAYS: every page
    #   that shows a post, for every Flip that reaches its end. 70,481 B
    #   measured.
    # RAISED (the owner's pick R2 of the recolour mock: a replay shows a
    #   line's new colour when it was given), for one named cost: +1,735 B,
    #   all inlineplayer.js -- the post's moments placed in its timeline, a
    #   moment painted into the compositor's ink layer or onto the canvas,
    #   the run ticked with the replay and kept through a scrub, and the
    #   fetch of lib/recolorplay.js (10,114 B) ONLY for a post that has
    #   recolours, which is why the module is not in this sum: the macro
    #   names it on inlineplayer.js's tag and nothing loads it otherwise.
    #   WHICH CALLER PAYS: every page that shows a post, for the hooks; a
    #   page showing a recoloured post, for the module, once. 72,216 B
    #   measured.
    # RAISED (the owner's yes to B after the desktop checks: a dot of the new
    #   colour on the scrubber where each line changed it), for a named cost:
    #   +1,758 B, all lib/replayline.js -- the moments found in the timeline
    #   the scrubber reads, and each dot's contrast against what is under the
    #   bar, ringed where it would not read. WHICH CALLER PAYS: every page that
    #   shows a post; the dots draw only for a post with recolours, once its
    #   drawing is there. 73,974 B measured.
    # RAISED (the owner's C, after v328: the glowing dot on a Flip page that
    #   draws itself, everywhere), for one named cost: +106 B, all
    #   inlineplayer.js -- render() handing the last revealed point of a
    #   drawing page to setNib while it plays, where it always passed null.
    #   WHICH CALLER PAYS: every page that shows a post, for every Flip with
    #   a Draw on page. 74,085 B measured.
    # RAISED (a bug fix, found building Match the beat: a post's box slid off
    #   its song about 12ms a second and started the song from its top after a
    #   pause), for one named cost: +226 B, all inlineplayer.js -- each pass
    #   carrying on from what its frame came late by, the passes' time kept
    #   (`lap`), and the song started where the drawing is. WHICH CALLER PAYS:
    #   every page that shows a post, for every post with music. Spent first:
    #   `lap` joins the clock's own line. 74,311 B measured.
    EMBED_RATCHET = 74_315
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
    check("the embed macro names exactly the nine assets a host pays for",
          len(embed_urls) == 9, str(embed_urls))
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
    print("\nIN-POST — a drawing keeps its own aspect in its box")
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

    # ---------------------------------------------------------------------------
    # THE POST (v322, the owner's pick for the in-post player: "bring Pad's
    # watching experience into the post ... it's critical"; "all yes").
    #
    # The box takes the drawing's shape; under it, always, the Pad's line --
    # the scrubber in the drawing's shape and "Drawn in 15 sec · watching at
    # 1×", the speed in it a button -- with mute and loop beside the scrubber,
    # off the drawing; the play button is white with a thin purple edge. All of
    # it at rest, from the listing, because NOTHING FETCHES UNTIL SOMEBODY
    # ASKS: so each check below that is about rest also proves no payload was
    # fetched. Measured at a phone's width with touch, where the 44px targets
    # matter, on fresh pages so no earlier check's state leaks in.
    print("\nTHE POST — shaped to its drawing, the line under it, before anybody asks")
    # ITS OWN POSTS, made here: by now this suite has posted enough that its
    # first fixtures have left the top of the feed. Real recordings through
    # the Pad (post_one), one with sound, and the three-page Flip with holds.
    id_a, _e1 = post_one(b, "The post fixture")
    id_b, _e2 = post_one(b, "The post fixture, unplayed")
    id_m, _e3 = post_one(b, "The post fixture with sound", music=True)
    try:
        flip_id = post_flip("The post flip fixture")["id"]
    except Exception:
        flip_id = None
    check("the post's own fixtures were posted (fixture)", bool(id_a and id_b and id_m and flip_id),
          f"{id_a}, {id_b}, {id_m}, {flip_id}; {(_e1 + _e2 + _e3)[:2]}")
    _listing = json.loads(urllib.request.urlopen(BASE + "/api/skribls?limit=100", timeout=20).read())
    _items = _listing.get("items", _listing) if isinstance(_listing, dict) else _listing
    _by = {i["id"]: i for i in _items}
    _la, _lm = (_by.get(id_a) or {}).get("line") or {}, (_by.get(id_m) or {}).get("line") or {}
    _lf = (_by.get(flip_id) or {}).get("line") or {} if flip_id else {}
    check("the listing carries each post's line: the drawing's time, its replay's, the author's "
          "speed and the scrubber's shape",
          isinstance(_la.get("drawn"), int) and _la["drawn"] > 0 and isinstance(_la.get("play"), int)
          and "speed" in _la and re.fullmatch(r"[0-9a-z]{128}", _la.get("shape") or "") is not None
          and set(_la.get("shape") or "0") != {"0"}, json.dumps(_la)[:240])
    check("...and whether it has sound, so mute holds its place from the first paint",
          _la.get("sound") is False and _lm.get("sound") is True,
          f"{_la.get('sound')!r} / {_lm.get('sound')!r}")
    if flip_id:
        check("...and a Flip's line is its page count, not a drawing time",
              _lf.get("pages") == 3 and "drawn" not in _lf, json.dumps(_lf))

    _pp = b.new_context(viewport={"width": 402, "height": 874}, is_mobile=True, has_touch=True)
    _pg2 = _pp.new_page()
    _perrs, _preqs = [], []
    _pg2.on("pageerror", lambda e: _perrs.append(str(e)))
    _pg2.on("request", lambda r: _preqs.append(r.url)
            if re.search(r"/api/skribls/[A-Za-z0-9_-]+$", r.url) else None)
    browsing.goto(_pg2, BASE, "/feed")
    _pg2.wait_for_timeout(600)
    _POST = """(id) => {
      const el = document.querySelector('[data-skribl-id="' + id + '"]');
      const ln = el.nextElementSibling, r = el.getBoundingClientRect();
      const strip = ln && ln.querySelector('.rl-strip');
      let ink = 0; const tall = new Set();
      if (strip && strip.width) { const W = strip.width, H = strip.height, d = strip.getContext('2d').getImageData(0, 0, W, H).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] > 0) ink++;
        /* THE SHAPE, NOT JUST INK: how tall each painted column is. An even
           placeholder track (no shape known) paints every column the same
           height, so it has one distinct height; a drawing has many. */
        for (let x = 0; x < W; x++) { let h = 0; for (let y = 0; y < H; y++) if (d[(y * W + x) * 4 + 3] > 0) h++; if (h) tall.add(h); } }
      return { aspect: r.width / r.height, w: +el.getAttribute('data-skribl-w'), h: +el.getAttribute('data-skribl-h'),
               line: !!ln && ln.classList.contains('skribl-inline-line'), on: !!ln && ln.classList.contains('is-on'),
               text: ln && ln.querySelector('.rl-text') ? ln.querySelector('.rl-text').innerText.replace(/\\s+/g, ' ').trim() : null,
               strip: strip ? strip.toDataURL() : null, ink: ink, heights: tall.size,
               height: Math.round((el.closest('article') || el).getBoundingClientRect().height * 10) / 10,
               fit: !!(ln && ln.querySelector('[data-r="fit"]') && !ln.querySelector('[data-r="fit"]').hidden) }; }"""
    _rest = _pg2.evaluate(_POST, id_a)
    _words = _pg2.evaluate("(ms) => window.SkriblReplayLine ? window.SkriblReplayLine.words(ms) : '?'", _la.get("drawn") or 0)
    # "long pauses skipped" joins the words when the replay skips a tenth or
    # more of the drawing's time (lib/replayline.js), which a hand's pauses
    # often do -- so the whole sentence is worked out from the listing too.
    _d, _p = _la.get("drawn") or 0, _la.get("play") or 0
    _said = f"Drawn in {_words} · watching at 1×" + (
        " long pauses skipped" if _d - _p >= _d / 10 and _d - _p >= 1000 else "")
    check("a post takes its drawing's shape: no bars beside it",
          _rest["w"] > 0 and abs(_rest["aspect"] - _rest["w"] / _rest["h"]) < 0.01,
          f"box {_rest['aspect']:.3f} vs drawing {_rest['w']}x{_rest['h']}")
    check("the line is under the drawing at rest, saying what it is, before any payload",
          _rest["line"] and _rest["on"] and _rest["text"] == _said
          and not _preqs, f"{_rest['text']!r} (expected {_said!r}); payload requests {len(_preqs)}")
    check("...over the drawing's shape, painted from the listing alone",
          _rest["ink"] > 200 and _rest["heights"] >= 4 and not _preqs,
          f"{_rest['ink']} painted pixels, {_rest['heights']} different column heights")
    if flip_id:
        _frest = _pg2.evaluate(_POST, flip_id)
        check("a Flip's line counts its pages and offers no Fit, before any payload",
              _frest["text"] == "3 pages · watching at 1×" and not _frest["fit"] and not _preqs,
              f"{_frest['text']!r}, Fit shown {_frest['fit']}")

    # THE FEED NEVER JUMPS, AND PRESSING PLAY CHANGES NOTHING UNDER THE DRAWING:
    # the same post height at rest, playing and paused, and the scrubber's
    # bars the same pixels before the drawing arrived and after it settled.
    _pg2.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_a)
    _pg2.wait_for_function("(id) => window.SkriblInline.find(id).state().state === 'playing'", arg=id_a, timeout=15000)
    _pg2.wait_for_timeout(900)
    _playing = _pg2.evaluate(_POST, id_a)
    _head = _pg2.evaluate("""(id) => { const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        const h = ln && ln.querySelector('.rl-head'); return h ? parseFloat(h.style.left) || 0 : -1; }""", id_a)
    _pg2.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", id_a)
    _pg2.wait_for_timeout(300)
    _paused = _pg2.evaluate(_POST, id_a)
    _pst = _pg2.evaluate("(id) => window.SkriblInline.find(id).state().state", id_a)
    check("a tap on the drawing pauses it, with the play button showing",
          _pst == "paused" and _pg2.evaluate("""(id) => getComputedStyle(document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-veil')).opacity""", id_a) == "1",
          _pst)
    check("the post is the same height at rest, playing and paused",
          _rest["height"] == _playing["height"] == _paused["height"],
          f"{_rest['height']} / {_playing['height']} / {_paused['height']}")
    check("the scrubber's playhead moves while it plays", 0 < _head < 100, f"{_head}%")
    _pg2.evaluate("() => window.SkriblInline.stopAll()")
    _pg2.wait_for_timeout(200)
    _settled = _pg2.evaluate(_POST, id_a)
    check("pressing play changes nothing under the drawing: the same bars before and after",
          _settled["strip"] == _rest["strip"] and _rest["strip"] is not None,
          "the strip repainted differently once the drawing arrived")
    check("...and the words stay the post's own", bool(_rest["text"]) and _settled["text"] == _rest["text"],
          repr(_settled["text"]))

    # THE PLAYER'S NUMBERS ARE THE LISTING'S: the server ported the clock, so
    # the line at rest and the drawing playing cannot disagree.
    _par = _pg2.evaluate("""async (id) => {
        const p = window.SkriblInline.find(id).state();
        const r = await fetch(document.querySelector('[data-skribl-id="' + id + '"]').getAttribute('data-skribl-api') + '/' + id);
        const j = await r.json(); const f = (j.skribl || j).frames;
        return { total: p.totalMs, drawn: window.SkriblReplayLine ? window.SkriblReplayLine.drawnMs(f[0].strokes) : -1 }; }""", id_a)
    check("the line's numbers are the player's: the replay's length and the drawing's time",
          abs(_par["total"] - _la.get("play", -9)) <= 1 and abs(_par["drawn"] - _la.get("drawn", -9)) <= 1,
          f"player {_par} vs listing play {_la.get('play')}, drawn {_la.get('drawn')}")

    # DRAG THE SCRUBBER OF A POST NOBODY HAS PLAYED: it fetches, and shows the
    # place it was dragged to, paused there with the poster gone.
    _SCRUB_AT = """(id) => { const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        const b = ln && ln.querySelector('.skribl-inline-scrub'); if (!b) return null; b.scrollIntoView({block: 'center'});
        const r = b.getBoundingClientRect(); return [r.left, r.top + r.height / 2, r.width]; }"""
    _bar = _pg2.evaluate(_SCRUB_AT, id_b)
    if _bar:
        _pg2.mouse.move(_bar[0] + 4, _bar[1]); _pg2.mouse.down()
        for _k in range(1, 11):
            _pg2.mouse.move(_bar[0] + 4 + (_bar[2] * 0.5 - 4) * _k / 10, _bar[1]); _pg2.wait_for_timeout(30)
        _pg2.mouse.up()
        try:
            _pg2.wait_for_function("(id) => window.SkriblInline.find(id).state().loaded", arg=id_b, timeout=15000)
        except PWTimeout:
            pass
        _pg2.wait_for_timeout(300)
    _ds = _pg2.evaluate("""(id) => { const s = window.SkriblInline.find(id).state();
        return { state: s.state, frac: s.elapsedMs / s.totalMs,
                 poster: getComputedStyle(document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-poster')).opacity }; }""", id_b)
    check("dragging the scrubber of an unplayed post shows the place it was dragged to",
          _ds["state"] == "paused" and abs(_ds["frac"] - 0.5) < 0.06 and _ds["poster"] == "0", json.dumps(_ds))

    # THE SPEED IN THE LINE IS THE BUTTON. One tap opens the speeds over the
    # scrubber, one picks and closes, and the clock runs at it.
    _IN_LINE = """([id, sel]) => { const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        return ln && ln.querySelector(sel); }"""
    _pg2.evaluate("(a) => { const n = (" + _IN_LINE + ")(a); if (n) n.click(); }", [id_b, ".rl-speed"])
    _pg2.wait_for_timeout(250)
    _open = _pg2.evaluate("(a) => { const n = (" + _IN_LINE + ")(a); return !!n && !n.hidden; }", [id_b, ".rl-chips"])
    _pg2.evaluate("(a) => { const n = (" + _IN_LINE + ")(a); if (n) n.click(); }", [id_b, '.rl-chips [data-r="2"]'])
    _pg2.wait_for_timeout(200)
    _sp = _pg2.evaluate("""(id) => { const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        const ch = ln && ln.querySelector('.rl-chips'), tx = ln && ln.querySelector('.rl-text');
        return { rate: window.SkriblInline.find(id).rate(), closed: !!ch && ch.hidden,
                 text: tx ? tx.innerText.replace(/\\s+/g, ' ').trim() : '' }; }""", id_b)
    check("the speed in the line opens the speeds, and a pick plays at it and closes them",
          _open and _sp["rate"] == 2 and _sp["closed"] and "watching at 2×" in _sp["text"], json.dumps(_sp))

    # ...AND STILL WHEN THE SOUND LETS GO ON THE WAY. It was reported twice
    # that "the 1x speed does not change when clicked", of the Gallery's full
    # screen, and never reproduced; what can produce it is a throw after the
    # rate is set and before the words are. A pick sets the rate, then
    # rebuilds the sound on an AudioContext the browser may take away, and the
    # line repaints after the pick returns -- so a throw from the sound would
    # leave the player at 2x and the line at 1x, a control that looks dead
    # while working. applyRate catches it. The Gallery's and the Library's
    # band are this line (me.band), moved here from verify_gallery with the
    # control, because only a drawing WITH sound reaches the sound: this
    # suite's post with sound, playing.
    #
    # DRIVEN BY MAKING THE THROW HAPPEN: every AudioContext's `state` throws
    # for the length of one press, and the probe counts that it was read, so
    # a row that never reached the sound says so instead of passing.
    _pg2.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').scrollIntoView({ block: 'center' })", id_m)
    _pg2.wait_for_timeout(300)
    _pg2.evaluate("(id) => { const p = window.SkriblInline.find(id); p.setRate(1); p.play(); }", id_m)
    try:
        _pg2.wait_for_function("(id) => { const s = window.SkriblInline.find(id).state(); return s.loaded && s.state === 'playing'; }",
                               arg=id_m, timeout=15000)
    except PWTimeout:
        pass
    _lg = _pg2.evaluate("""(id) => {
        const p = window.SkriblInline.find(id);
        const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        const btn = ln && ln.querySelector('.rl-speed');
        const B = window.BaseAudioContext && BaseAudioContext.prototype;
        const real = B && Object.getOwnPropertyDescriptor(B, 'state');
        if (!p || !btn || !real) return { missing: true };
        const out = { playing: p.state().state === 'playing', reads: 0 };
        Object.defineProperty(B, 'state', { configurable: true,
            get: function () { out.reads++; throw new Error('probe: the sound let go'); } });
        try {
            btn.click();
            const chip = ln.querySelector('.rl-chips [data-r="2"]');
            if (chip) chip.click();
        } finally { Object.defineProperty(B, 'state', real); }
        const tx = ln.querySelector('.rl-text');
        out.rate = p.rate();
        out.text = tx ? tx.innerText.replace(/\\s+/g, ' ').trim() : '';
        out.closed = ln.querySelector('.rl-chips').hidden;
        p.pause(); p.setRate(1);
        return out; }""", id_m)
    check("...and when the sound lets go on the way, the pick still plays at it and the line says so",
          not _lg.get("missing") and _lg["playing"] and _lg["reads"] > 0
          and _lg["rate"] == 2 and "watching at 2×" in _lg["text"] and _lg["closed"],
          json.dumps(_lg) + " — reads 0 is a probe that never reached the sound; "
          "2 with the line at 1× is the control that looks dead while working")

    # A FLIP'S SCRUBBER IS ITS PAGES, one equal segment each, not its clock.
    # Pages of 333, 667 and 333 ms: a quarter of the way along is three
    # quarters into page 1 (250 ms) where the clock would say page 2 (333),
    # and 70% is just into page 3 (1,033 ms) where the clock says page 2
    # (933). Halfway would not tell them apart -- both read 667.
    if flip_id:
        _fb = _pg2.evaluate(_SCRUB_AT, flip_id)
        _ftimes = []
        for _f in ((0.25, 0.7) if _fb else ()):
            _pg2.mouse.click(_fb[0] + _fb[2] * _f, _fb[1])
            try:
                _pg2.wait_for_function("(id) => window.SkriblInline.find(id).state().loaded", arg=flip_id, timeout=15000)
            except PWTimeout:
                pass
            _pg2.wait_for_timeout(250)
            _ftimes.append(_pg2.evaluate("(id) => window.SkriblInline.find(id).state().elapsedMs", flip_id))
        check("a Flip's scrubber is one segment a page, not its clock: a quarter lands in page 1, 70% in page 3",
              len(_ftimes) == 2 and abs(_ftimes[0] - 250) < 40 and 1000 <= _ftimes[1] < 1334, f"{_ftimes} ms")

    # THE PLAY BUTTON (the owner's v4): white, a thin purple edge, no shadow,
    # and no wash behind it.
    _pb = _pg2.evaluate("""(id) => { const el = document.querySelector('[data-skribl-id="' + id + '"]');
        const c = getComputedStyle(el.querySelector('.skribl-inline-play'));
        return { bg: c.backgroundColor, edge: c.borderTopWidth + ' ' + c.borderTopColor, shadow: c.boxShadow,
                 veil: getComputedStyle(el.querySelector('.skribl-inline-veil')).backgroundImage,
                 tri: getComputedStyle(el.querySelector('.skribl-inline-play svg')).fill }; }""", id_m)
    check("the play button is white with a thin purple edge, no shadow and no wash behind it",
          _pb["bg"] == "rgb(255, 255, 255)" and _pb["edge"].startswith("2px rgba(124, 92, 255")
          and _pb["shadow"] == "none" and _pb["veil"] == "none" and _pb["tri"] == "rgb(124, 92, 255)",
          json.dumps(_pb))

    # OFF THE DRAWING, AND 44px TO A FINGER. Mute and loop live in the line
    # now, and the speed, the scrubber and loop each answer a finger over 44px
    # -- asked of what is painted there (elementFromPoint), not of a rect.
    _tg = _pg2.evaluate("""(id) => { const el = document.querySelector('[data-skribl-id="' + id + '"]'), ln = el.nextElementSibling;
        if (!ln || !ln.classList.contains('skribl-inline-line')) return { inBox: !!el.querySelector('.skribl-inline-loop'), inLine: false,
          muteShown: false, speed: 0, scrub: 0, loop: 0 };
        ln.scrollIntoView({block: 'center'});
        const tall = (n) => { const b = n.getBoundingClientRect(), x = b.left + b.width / 2, y = b.top + b.height / 2;
          const own = (t) => !!t && (t === n || n.contains(t)); let up = 0, dn = 0;
          while (up < 40 && own(document.elementFromPoint(x, y - up - 1))) up++;
          while (dn < 40 && own(document.elementFromPoint(x, y + dn + 1))) dn++; return up + dn + 1; };
        return { inBox: !!el.querySelector('.skribl-inline-loop, .skribl-inline-mute'),
                 inLine: !!ln.querySelector('.skribl-inline-loop') && !!ln.querySelector('.skribl-inline-mute'),
                 muteShown: getComputedStyle(ln.querySelector('.skribl-inline-mute')).display !== 'none',
                 speed: tall(ln.querySelector('.rl-speed')), scrub: tall(ln.querySelector('.skribl-inline-scrub')),
                 loop: tall(ln.querySelector('.skribl-inline-loop')) }; }""", id_m)
    check("mute and loop are off the drawing, in the line under it",
          not _tg["inBox"] and _tg["inLine"], json.dumps(_tg))
    check("...and a post with sound shows mute there before it is played", _tg["muteShown"], json.dumps(_tg))
    check("the speed, the scrubber and loop are each 44px to a finger",
          min(_tg["speed"], _tg["scrub"], _tg["loop"]) >= 44, json.dumps(_tg))

    # A HOST THAT SWITCHES THEME AFTER LOAD. The line takes the host's text;
    # its quiet words were once a colour mixed from it, and Chrome left that
    # mix stale when the page's colour changed (the light page showed the
    # dark page's words, white on white). They are quiet by opacity now.
    _th = _pg2.evaluate("""(id) => { const ln = document.querySelector('[data-skribl-id="' + id + '"]').nextElementSibling;
        const q = ln && ln.querySelector('.rl-m'); if (!q) return { color: null, opacity: '1' };
        document.body.style.setProperty('color', 'rgb(29, 26, 43)', 'important');
        const c = getComputedStyle(q);
        const out = { color: c.color, opacity: c.opacity };
        document.body.style.removeProperty('color'); return out; }""", id_a)
    check("after the host switches theme, the line's quiet words take its new colour",
          _th["color"] == "rgb(29, 26, 43)" and float(_th["opacity"]) < 0.8, json.dumps(_th))
    check("no page errors on the post", not _perrs, "; ".join(_perrs[:2]))
    _pp.close()

    # NO STICKY HOVER. iOS keeps :hover on the last thing tapped, so a hover
    # outside (hover: hover) stays lit on a phone. Asked of the sheet's rules,
    # every one: a :hover selector must sit inside a (hover: hover) block.
    _hv = _pg2 = None
    _hc = b.new_page(viewport={"width": 620, "height": 900})
    browsing.goto(_hc, BASE, "/feed")
    _hv = _hc.evaluate("""() => { const bad = [];
        for (const sh of document.styleSheets) { if (!/inlineplayer\\.css/.test(sh.href || '')) continue;
          const walk = (rules, guarded) => { for (const r of rules) {
            if (r.media && r.cssRules) walk(r.cssRules, guarded || /hover:\\s*hover/.test(r.media.mediaText));
            else if (r.selectorText && /:hover/.test(r.selectorText) && !guarded) bad.push(r.selectorText); } };
          walk(sh.cssRules, false); }
        return bad; }""")
    _hc.close()
    check("every hover in the post's stylesheet waits for a real hover, so a tap leaves nothing lit",
          _hv == [], "; ".join(_hv))

    # THE BLOOBY CARD'S POSTER SHOWS BLOOBY. A page kept underneath is the
    # stage, not the picture: the poster is the first inked page drawn on it,
    # with it painted beneath (flip.js posterPage). The card's own page 1 is
    # the empty card. Asked of the editor that builds the card, on the demo.
    _fl = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(_fl, BASE, "/flip")
    _fl.wait_for_timeout(800)
    _demo = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "flip-blooby-card.json").read_text(encoding="utf-8"))
    _poster = _fl.evaluate("""(d) => { applyPayload(d);
        if (typeof posterPage !== 'function') return { missing: true };
        const withUnder = frames.indexOf(posterPage());
        const keep = docUnder; docUnder = null; const without = frames.indexOf(posterPage()); docUnder = keep;
        return { withUnder: withUnder, without: without }; }""", _demo)
    _fl.close()
    check("the Blooby card's poster is Blooby on the card, not the empty card",
          _poster.get("withUnder") == 1 and _poster.get("without") == 0, json.dumps(_poster))

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

        # A TAP ON THE PLAYER IS THE PLAYER'S (v316). skribls.net makes a
        # whole post a link: article[data-href] navigates on any click whose
        # target is not inside a, button, label, .actions, video, audio or
        # .video-embed. The player's box is a div, so on the real profile page
        # a tap started playback and then left for /post/<n>. The host's rule
        # is copied here onto the post the player sits in, and a real click
        # (not a scripted one) goes to the box's centre.
        print("\nIN-POST — a tap plays in place under a host that makes the whole post a link")
        _pg.evaluate("""(id) => { const box = document.querySelector('.skribl-inline[data-skribl-id="' + id + '"]');
            const card = box.parentElement; window.__cardNav = 0;
            card.addEventListener('click', (e) => {
              if (e.target.closest('a, button, label, .actions, video, audio, .video-embed')) return;
              window.__cardNav++; }); }""", _plain)
        _pb = _pg.locator('.skribl-inline[data-skribl-id="' + _plain + '"]').first
        _pb.scroll_into_view_if_needed()
        _bb = _pb.bounding_box()
        _pg.mouse.click(_bb["x"] + _bb["width"] / 2, _bb["y"] + _bb["height"] / 2)
        _pg.wait_for_timeout(900)
        _tap = _pg.evaluate("""(id) => ({ nav: window.__cardNav,
            cls: document.querySelector('.skribl-inline[data-skribl-id="' + id + '"]').className })""", _plain)
        check("the tap starts the drawing and never reaches the post's own link",
              _tap["nav"] == 0 and ("is-playing" in _tap["cls"] or "is-loading" in _tap["cls"]), str(_tap))

        # POSTS ADDED AFTER LOAD (v316). skribls.net's infinite scroll appends
        # server-rendered posts to the feed; the player mounts once, at load, so
        # a Skribl on page two showed its poster and did nothing when tapped.
        # docs/INTEGRATION.md now tells a host to call SkriblInline.mount() after
        # inserting; this does what that host does: clone a posted box as fresh
        # markup, insert it, mount, tap it for real. And mount() again over the
        # whole page must not give any box a second player.
        print("\nIN-POST — a post added after the page loaded plays once mounted, and re-mounting is safe")
        _before = _pg.evaluate("() => SkriblInline.players().length")
        _pg.evaluate("""(id) => { const src = document.querySelector('.skribl-inline[data-skribl-id="' + id + '"]');
            const tmp = document.createElement('div'); tmp.innerHTML = src.outerHTML;
            const box = tmp.firstElementChild; box.classList.remove('is-playing', 'is-paused', 'is-loading');
            box.id = 'lateSkribl'; const host = document.createElement('article');
            host.appendChild(box); src.parentElement.parentElement.appendChild(host); }""", _derived)
        _unmounted = _pg.evaluate("() => SkriblInline.players().length")
        _pg.evaluate("() => { SkriblInline.mount(document); SkriblInline.mount(document); }")
        _after = _pg.evaluate("() => SkriblInline.players().length")
        _lb = _pg.locator("#lateSkribl")
        _lb.scroll_into_view_if_needed()
        _lbb = _lb.bounding_box()
        _pg.mouse.click(_lbb["x"] + _lbb["width"] / 2, _lbb["y"] + _lbb["height"] / 2)
        _pg.wait_for_timeout(900)
        _lcls = _pg.evaluate("() => document.getElementById('lateSkribl').className")
        check("mount() picks up the new box once, and calling it twice adds nothing more",
              _unmounted == _before and _after == _before + 1, f"before {_before}, inserted {_unmounted}, after two mounts {_after}")
        check("...and the late post plays when tapped",
              "is-playing" in _lcls or "is-loading" in _lcls, _lcls)
        _b.close()


# AN ERASER STROKE REVEALS THE DRAWING'S BACKGROUND, NOT THE BOX. The player
# paints the background into the same canvas as the ink, and an erase is
# destination-out, so on the direct path it cut through the background too and
# showed the box's own dark ground: a light drawing with an eraser stroke
# replayed with black lines in every feed, library and embed (the owner saw it
# on How it works' Eraser card). The fixture is that card's example -- a real
# recording, drawn through Pad with the eraser -- posted and played in a feed
# box, sampled along the eraser's own recorded path.
print("\nIN-POST — an eraser stroke reveals the drawing's background, not the box behind it")
with sync_playwright() as _ep:
    _eb = _ep.chromium.launch()
    _ex = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "eraser.json").read_text())
    _ex["title"] = "Eraser probe"
    _req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_ex).encode(),
                                  headers={"Content-Type": "application/json"})
    _esid = json.loads(urllib.request.urlopen(_req).read())["id"]
    _path = [s for s in _ex["frames"][0]["strokes"] if s.get("erase")]
    _ground = _ex["frames"][0]["background"]["color"]
    _epg = _eb.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(_epg, BASE, "/feed")
    _epg.evaluate("""(id) => { const src = document.querySelector('.skribl-inline[data-skribl-id]');
        const tmp = document.createElement('div'); tmp.innerHTML = src.outerHTML;
        const box = tmp.firstElementChild; box.classList.remove('is-playing', 'is-paused', 'is-loading');
        box.setAttribute('data-skribl-id', id); box.id = 'eraserProbe';
        box.querySelectorAll('img').forEach(i => i.remove());
        const host = document.createElement('article'); host.appendChild(box);
        src.parentElement.parentElement.prepend(host); SkriblInline.mount(document); }""", _esid)
    _epg.locator("#eraserProbe").scroll_into_view_if_needed()
    # Once through and stop: a feed box loops, and a sample taken mid-loop can
    # land before the eraser stroke and see nothing to find (it did).
    _epg.evaluate("(id) => { const p = SkriblInline.find(id); p.setLoop(false); p.play(); }", _esid)
    try:
        _epg.wait_for_function("(id) => { const p = SkriblInline.find(id); return p && p.state().loaded"
                               " && p.state().state !== 'playing' && p.state().state !== 'loading'; }",
                               arg=_esid, timeout=20000)
    except PWTimeout:
        pass
    _epg.wait_for_timeout(300)
    _er = _epg.evaluate("""([pts, w]) => {
        const c = document.querySelector('#eraserProbe .skribl-inline-canvas');
        if (!c || !c.width) return null;
        const x = c.getContext('2d'), k = c.width / w; let dark = 0, n = 0;
        for (let i = 0; i < pts.length; i += 4) {
          const d = x.getImageData(Math.round(pts[i].x * k), Math.round(pts[i].y * k), 1, 1).data;
          n++; if (d[3] < 200 || d[0] + d[1] + d[2] < 150) dark++; }
        return { n, dark, ground: (() => { const d = x.getImageData(4, 4, 1, 1).data; return [d[0], d[1], d[2], d[3]]; })() }; }""",
        [_path, _ex["canvasSize"]["cssWidth"]])
    _done = _epg.evaluate("(id) => { const s = SkriblInline.find(id).state(); return [s.state, s.loaded]; }", _esid)
    check("the probe is real: the eraser example played through in a feed box, over its own paper",
          _er is not None and _er["n"] > 10 and _er["ground"][0] > 200 and _done[0] != "playing",
          f"{_er}, ground {_ground}, player {_done}")
    check("along the eraser's path the drawing's paper shows, never the box's dark ground",
          _er is not None and _er["dark"] == 0,
          f"{_er} — dark or see-through samples on the eraser's path are the erase cutting through "
          f"the background to the box behind it")
    _eb.close()


# ---------------------------------------------------------------------------
print("\nSCRUBBING A LONG POST -- a seek starts from the nearest copy and paints what a seek from zero paints")
# The v322 plan's step 3, for the in-post player. Its compositor keeps the
# photo as a layer of its own, which an eraser reveals, so its copies are of
# the ink layer and come back on a fresh compositor (lib/seekcache.js's source
# and put). THE REFERENCE is the same post on a page where lib/seekcache.js is
# refused, so that player seeks from zero as it always did; every byte of the
# canvas is hashed after each of ten seeks and the two pages must agree. The
# seeks after the first must also have started near their targets. One post
# goes through the compositor (see-through strokes and erasers), one does not.
LONGPOST = """([n, mixed]) => { let s = 11; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const pts = [], groups = []; let t = 0, gi = 0;
  while (pts.length < n) {
    const m = 20 + Math.floor(rnd() * 200); let x = 60 + rnd() * 700, y = 60 + rnd() * 480, a = rnd() * 6.283;
    const col = mixed && gi % 5 === 2 ? 'rgba(124,92,255,0.45)' : ['#1f1b2e', '#7c5cff', '#ff7a59'][gi % 3];
    const er = mixed && gi % 23 === 7; let k = 0;
    for (let i = 0; i < m && pts.length < n; i++, k++) {
      pts.push({ x: x, y: y, color: col, size: 2.5 + 6 * Math.sin(Math.PI * i / m), t: Math.round(t), start: i === 0, erase: er });
      a += (rnd() - 0.5) * 0.3; x = Math.min(800, Math.max(10, x + Math.cos(a) * 5)); y = Math.min(590, Math.max(10, y + Math.sin(a) * 5));
      t += 18; }
    groups.push(k); gi++; t += 200 + rnd() * 900; }
  return { pts: pts, groups: groups }; }"""
_HASH = """(id) => { const c = document.querySelector('[data-skribl-id="' + id + '"] .skribl-inline-canvas');
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 2166136261;
  for (let i = 0; i < d.length; i++) { h ^= d[i]; h = Math.imul(h, 16777619); }
  let ink = 0; for (let i = 3; i < d.length; i += 4) if (d[i - 3] < 200) ink++;
  return [h >>> 0, ink]; }"""
SEQ3 = [0.9, 0.3, 0.95, 0.5, 0.52, 0.1, 1.0, 0.75, 0.76, 0.2]
with sync_playwright() as _sp3:
    _b3 = _sp3.chromium.launch()
    _ids = {}
    try:
        _gp = _b3.new_page()
        browsing.goto(_gp, BASE, "/")
        for _kind, _mixed in (("layered", True), ("opaque", False)):
            _gen = _gp.evaluate(LONGPOST, [19000, _mixed])
            _req = urllib.request.Request(
                BASE + "/api/skribls", headers={"Content-Type": "application/json"},
                data=json.dumps({"title": f"Harness long {_kind}", "visibility": "public", "version": 2,
                                 "schemaVersion": 2, "playbackMode": "replay", "fps": None,
                                 "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                                 "frames": [{"strokes": _gen["pts"], "strokeGroups": _gen["groups"],
                                             "background": {"color": "#f6f2ea"}}]}).encode())
            with urllib.request.urlopen(_req, timeout=30) as _r:
                _ids[_kind] = json.loads(_r.read().decode())["id"]
        _gp.close()
    except Exception as exc:                               # noqa: BLE001
        check("two long posts were made (fixture)", False, f"{type(exc).__name__}: {exc}")

    def _scrub(block):
        pg = _b3.new_page(viewport={"width": 620, "height": 900})
        if block:
            pg.route("**/lib/seekcache.js*", lambda r: r.abort())
        browsing.goto(pg, BASE, "/feed")
        out = {}
        for kind, sid in _ids.items():
            pg.evaluate("(id) => { const el = document.querySelector('[data-skribl-id=\"' + id + '\"]');"
                        " el.scrollIntoView(); el.click(); }", sid)
            pg.wait_for_function("(id) => window.SkriblInline.find(id) && window.SkriblInline.find(id).state().loaded",
                                 arg=sid, timeout=20000)
            rows = []
            for f in SEQ3:
                # Once it lands: a far first jump races there.
                st = pg.evaluate("([id, f]) => new Promise(res => { const p = window.SkriblInline.find(id);"
                                 " p.seek(f * p.state().totalMs);"
                                 " const t = () => p.state().racing ? requestAnimationFrame(t) : res(p.state()); t(); })", [sid, f])
                rows.append((f, pg.evaluate(_HASH, sid), st["copies"], st["drawnLast"], st["stretch"]))
            out[kind] = rows
        pg.close()
        return out

    if len(_ids) == 2:
        _with, _without = _scrub(False), _scrub(True)
        for _kind in ("layered", "opaque"):
            _a, _z = _with[_kind], _without[_kind]
            _diff = [f for (f, h, *_), (_f, hz, *_) in zip(_a, _z) if h[0] != hz[0]]
            check(f"[{_kind} post, 19,000 points] the reference really seeks from zero: no copies on the page that refuses the cache",
                  all(r[2] == 0 for r in _z) and all(r[1][1] > 1000 for r in _z[:1]),
                  f"copies {[r[2] for r in _z]}, ink {_z[0][1][1]}")
            check(f"[{_kind} post, 19,000 points] every seek of ten paints exactly what a seek from zero paints",
                  not _diff, f"{len(_diff)} of 10 differ: {_diff}")
            _stretch = _a[0][4]
            _after = [(f, d) for f, _h, _c, d, _s in _a[1:]]
            check(f"[{_kind} post, 19,000 points] ...it keeps copies, and every seek after the first starts near its target",
                  _a[-1][2] >= 1 and 0 < _stretch and all(0 <= d <= 2 * _stretch for _, d in _after),
                  f"copies {_a[-1][2]}, stretch {_stretch}, points drawn after the first {_after}")
    _b3.close()


# ---------------------------------------------------------------------------
print("\nTHE FIRST FAR JUMP RACES THERE -- the in-post player keeps moving, and lands on exactly today's picture")
# The owner's pick A, from the mock, in the in-post player (a feed, the
# Gallery, the Library): a first jump to a far part of a long post is drawn a
# slice a frame (lib/seekcache.js race()), not all at once. Read at 2x, where a
# stretch between copies is wider than a race's threshold. THE REFERENCE is
# the same post on a page that refuses lib/seekcache.js, so its player seeks
# from zero at once, as every seek used to; every byte is hashed on both. The
# bar for "keeps moving" is no task past 300 ms: the same jump drawn at once is
# one task of over a second here, and a frame that also takes a copy of a 2x
# canvas, drawn in software, runs to 60 ms or so, and past 200 with other
# suites sharing the machine.
_FF_WATCH = """() => { if (!window.__ff) { window.__ff = { lt: [], frames: 0 };
    new PerformanceObserver(l => { for (const e of l.getEntries()) window.__ff.lt.push(Math.round(e.duration)); }).observe({ type: 'longtask' });
    const f = () => { window.__ff.frames++; requestAnimationFrame(f); }; requestAnimationFrame(f); }
  window.__ff.lt = []; window.__ff.frames = 0; }"""
_FF_LANDED = """(id) => new Promise(res => { const p = window.SkriblInline.find(id), t0 = performance.now();
    const t = () => { if (p.state().racing && performance.now() - t0 < 60000) return requestAnimationFrame(t);
      const fr = window.__ff ? window.__ff.frames : 0, ms = Math.round(performance.now() - t0);
      requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(() =>
        res({ frames: fr, ms: ms, lt: window.__ff ? window.__ff.lt.slice() : [], racing: p.state().racing }), 60))); };
    t(); })"""
_FF_STATE = "(id) => { const s = window.SkriblInline.find(id).state(); return [s.state, s.racing, s.elapsedMs, s.totalMs]; }"
# PRESSES MID-RACE GO IN ONE TASK, a couple of frames into the race, so it
# cannot land between them: with real clicks it did on CI, the waiting Play
# started, and the second press paused real playback. `_FF_IN(body)` seeks to
# `f` of the post, waits two frames and runs `body` with `p`, `el` (the post)
# and `st()` (its state) in hand.
def _FF_IN(body):
    return ("""async ([id, f, sel]) => { const p = window.SkriblInline.find(id),
        el = document.querySelector('[data-skribl-id="' + id + '"]');
      const st = () => { const s = p.state(); return [s.state, s.racing, s.elapsedMs, s.totalMs]; };
      p.seek(f * p.state().totalMs); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      """ + body + " }")
with sync_playwright() as _sp4:
    _b4 = _sp4.chromium.launch()
    _ffid = None
    try:
        _gp = _b4.new_page()
        browsing.goto(_gp, BASE, "/")
        _gen = _gp.evaluate(LONGPOST, [120000, True])
        _req = urllib.request.Request(
            BASE + "/api/skribls", headers={"Content-Type": "application/json"},
            data=json.dumps({"title": "Harness two-hour post", "visibility": "public", "version": 2,
                             "schemaVersion": 2, "playbackMode": "replay", "fps": None,
                             "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                             "frames": [{"strokes": _gen["pts"], "strokeGroups": _gen["groups"],
                                         "background": {"color": "#f6f2ea"}}]}).encode())
        with urllib.request.urlopen(_req, timeout=60) as _r:
            _ffid = json.loads(_r.read().decode())["id"]
        _gen = None
        _gp.close()
    except Exception as exc:                               # noqa: BLE001
        check("a two-hour post was made (fixture)", False, f"{type(exc).__name__}: {exc}")

    def _ffpage(block=False, play=True):
        pg = _b4.new_page(viewport={"width": 620, "height": 900}, device_scale_factor=2)
        if block:
            pg.route("**/lib/seekcache.js*", lambda r: r.abort())
        browsing.goto(pg, BASE, "/feed")
        pg.wait_for_function("(id) => !!document.querySelector('[data-skribl-id=\"' + id + '\"]')", arg=_ffid, timeout=30000)
        pg.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').scrollIntoView({ block: 'center' })", _ffid)
        pg.click(f'[data-skribl-id="{_ffid}"]')                # a tap: it loads and plays
        pg.wait_for_function("(id) => window.SkriblInline.find(id) && window.SkriblInline.find(id).state().loaded", arg=_ffid, timeout=30000)
        pg.wait_for_timeout(600)
        if not play:
            pg.evaluate("(id) => window.SkriblInline.find(id).pause()", _ffid)
        return pg

    if _ffid:
        _ref = _ffpage(block=True, play=False)

        def _refhash(ms):
            _ref.evaluate("([id, ms]) => window.SkriblInline.find(id).seek(ms)", [_ffid, ms])
            return _ref.evaluate(_HASH, _ffid)[0]

        _pl = _ffpage()
        _pl.evaluate(_FF_WATCH)
        _sel = f'[data-skribl-id="{_ffid}"] + .skribl-inline-line .skribl-inline-scrub'
        _bx = _pl.locator(_sel).bounding_box()
        _x = round(_bx["x"] + _bx["width"] * 0.8)
        _pl.mouse.click(_x, _bx["y"] + _bx["height"] / 2)      # a tap on the line while it plays
        _f = (_x - _bx["x"]) / _bx["width"]
        _now = _pl.evaluate("([id, sel]) => { const s = window.SkriblInline.find(id).state();"
                            " return { racing: s.racing, state: s.state, f: s.elapsedMs / s.totalMs,"
                            " now: +document.querySelector(sel).getAttribute('aria-valuenow') }; }", [_ffid, _sel])
        check("[in-post, 120,000 points, 2x] a first far jump races there: the line says where it was pointed at once, and the Play the scrub carries on with waits, saying it plays",
              _now["racing"] and _now["state"] == "playing" and abs(_now["f"] - _f) < 0.01 and _now["now"] == round(_now["f"] * 100), str(_now))
        _land = _pl.evaluate(_FF_LANDED, _ffid)
        check("[in-post] ...the page keeps moving while it does: frames are painted, and none is held up past 300 ms",
              not _land["racing"] and _land["frames"] >= 5 and max(_land["lt"] or [0]) < 300,
              f"{_land['frames']} frames in {_land['ms']} ms, long tasks {_land['lt']}")
        _s1 = _pl.evaluate(_FF_STATE, _ffid)
        _pl.wait_for_timeout(300)
        _s2 = _pl.evaluate(_FF_STATE, _ffid)
        _ms = _pl.evaluate("(id) => { const p = window.SkriblInline.find(id); p.pause(); const ms = p.state().elapsedMs; p.seek(ms); return ms; }", _ffid)
        _same = _pl.evaluate(_HASH, _ffid)[0] == _refhash(_ms)
        check("[in-post] ...it plays on from where it landed, and the picture is exactly what a seek from zero paints",
              _s1[0] == _s2[0] == "playing" and _s2[2] > _s1[2] >= _now["f"] * _s1[3] - 1 and _same,
              f"{_s1[:3]} -> {_s2[:3]}, same picture {_same}")
        _d = _pl.evaluate("""async (id) => { const p = window.SkriblInline.find(id), T = p.state().totalMs; p.seek(T);
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const mid = p.state().racing; p.seek(0.93 * T); const again = p.state().racing;
            await new Promise(res => { const t = () => p.state().racing ? requestAnimationFrame(t) : res(); t(); });
            return { mid: mid, again: again, ms: p.state().elapsedMs }; }""", _ffid)
        _same = _pl.evaluate(_HASH, _ffid)[0] == _refhash(_d["ms"])
        check("[in-post] a newer seek mid-race takes over from where the canvas stands, and lands exactly too",
              _d["mid"] and _d["again"] and _same, f"{_d}, same picture {_same}")
        _pl.close()

        # Anything that repaints stops a race: settled mid-race (scrolled past,
        # or another post started), it shows the post at rest and nothing races
        # on over it.
        _pl = _ffpage()
        _pl.evaluate("(id) => { const p = window.SkriblInline.find(id); p.seek(0.9 * p.state().totalMs); }", _ffid)
        _pl.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        _was = _pl.evaluate("(id) => window.SkriblInline.find(id).state().racing", _ffid)
        _pl.evaluate("(id) => window.SkriblInline.find(id).settle()", _ffid)
        _pl.evaluate("() => new Promise(r => { let n = 8; const t = () => --n ? requestAnimationFrame(t) : r(); requestAnimationFrame(t); })")
        _ref.evaluate("(id) => window.SkriblInline.find(id).settle()", _ffid)
        _same = _pl.evaluate(_HASH, _ffid)[0] == _ref.evaluate(_HASH, _ffid)[0]
        check("[in-post] settled while it races, it shows the post at rest, and nothing races on over it",
              _was and _same and not _pl.evaluate("(id) => window.SkriblInline.find(id).state().racing", _ffid),
              f"racing when settled {_was}, same picture {_same}")
        # Play pressed mid-race waits for the landing, and a second press takes
        # it back: by a tap on the post, and by its keys. The first from rest,
        # as the Library seeks a post nobody has played yet: taken back, it is
        # paused where it was pointed, not "at rest" with its drawing showing.
        _q1, _q2 = _pl.evaluate(_FF_IN("el.click(); const a = st(); el.click(); return [a, st()];"), [_ffid, 0.5, ""])
        _pl.evaluate(_FF_LANDED, _ffid); _pl.wait_for_timeout(300)
        _q3 = _pl.evaluate(_FF_STATE, _ffid)
        check("[in-post] Play pressed mid-race (a tap, from rest) says it plays and waits; a second tap takes it back, paused where it was pointed",
              _q1[:2] == ["playing", True] and _q2[:2] == ["paused", True] and _q3[:2] == ["paused", False]
              and abs(_q3[2] - 0.5 * _q3[3]) < 1, f"{_q1} {_q2} {_q3}")
        _k1, _k2 = _pl.evaluate(_FF_IN("""const key = () => el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
            key(); const a = st(); key(); return [a, st()];"""), [_ffid, 0.97, ""])
        _pl.evaluate(_FF_LANDED, _ffid); _pl.wait_for_timeout(300)
        _k3 = _pl.evaluate(_FF_STATE, _ffid)
        check("[in-post] ...and so do its keys",
              _k1[:2] == ["playing", True] and _k2[:2] == ["paused", True] and _k3[:2] == ["paused", False]
              and abs(_k3[2] - 0.97 * _k3[3]) < 1, f"{_k1} {_k2} {_k3}")
        _pl.close()

        # A drag holds a Play that waits, as it holds playing: nothing starts
        # under the finger, and letting go plays.
        _pl = _ffpage()
        _HOLD = """const bar = document.querySelector(sel), r = bar.getBoundingClientRect();
            const ptr = (t) => bar.dispatchEvent(new PointerEvent(t, { bubbles: true, cancelable: true, isPrimary: true,
              pointerId: 9, button: 0, clientX: r.left + r.width * 0.95, clientY: r.top + r.height / 2 }));"""
        _g1, _gd = _pl.evaluate(_FF_IN("el.click(); const a = st(); " + _HOLD + " ptr('pointerdown'); return [a, st()];"),
                                [_ffid, 0.5, _sel])   # a Play that waits, then the finger goes down on the line, and stays
        _pl.evaluate(_FF_LANDED, _ffid); _pl.wait_for_timeout(300)
        _g2 = _pl.evaluate(_FF_STATE, _ffid)
        _pl.wait_for_timeout(300)
        _g3 = _pl.evaluate(_FF_STATE, _ffid)
        _pl.evaluate("([id, f, sel]) => { " + _HOLD + " ptr('pointerup'); }", [_ffid, 0, _sel]); _pl.wait_for_timeout(400)
        _g4 = _pl.evaluate(_FF_STATE, _ffid)
        check("[in-post] a drag holds a Play that waits, as it holds playing: nothing starts under the finger, and letting go plays",
              _g1[:2] == ["playing", True] and _gd[:2] == ["paused", True] and _g2[0] == "paused" and _g3[0] == "paused"
              and _g2[2] == _g3[2] and _g4[0] == "playing" and _g4[2] > _g3[2], f"{_g1} {_gd} {_g2} {_g3} {_g4}")
        _pl.close()
        _ref.close()
    _b4.close()


# ---------------------------------------------------------------------------
# A DRAWING THAT CAN'T BE SHOWN SAYS SO KINDLY (the owner's pick after v322,
# from a mock on skribls.net's own Home page). It was a black box -- the blank
# poster was the dark canvas ground -- then red words in the code face and a
# Play that did nothing. Two probes, cloned from the feed's own box with their
# lines: one for a drawing that is gone (an id the API answers 404 for, which
# is also its answer for a post this viewer may no longer see) and one for a
# real post whose payload request is dropped and then let through. The host's
# ground is set light, as skribls.net's is, so the black box and the page's
# ground cannot be mistaken for each other. Every probe of what is SEEN reads
# pixels or elementFromPoint, never a rect.
print("\nIN-POST — a drawing that can't be shown says so kindly, in the page's own colours and type")
_GONE_WORDS = "This drawing isn’t here anymore."
_DROP_WORDS = ["Couldn’t load this drawing.", "Tap to try again."]
_GROUND = (246, 248, 250)          # the host's --bg-elev, set below


def _px(pg, sel, fx, fy):
    """The colour PAINTED at a fraction of an element's box (a screenshot, not a style)."""
    import io
    from PIL import Image
    r = pg.locator(sel).bounding_box()
    shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    k = shot.width / pg.viewport_size["width"]
    return shot.getpixel((int((r["x"] + r["width"] * fx) * k), int((r["y"] + r["height"] * fy) * k)))


def _near(c, ref, tol=8):
    return all(abs(a - b) <= tol for a, b in zip(c, ref))


def _purple_at_centre(pg, sel, half=30):
    """Pixels of the Play disc's purple (its arrow and its ring) painted within
    `half` CSS px of the box's centre. elementFromPoint cannot answer this: the
    veil and the disc take no pointer events, so it sees straight through them."""
    import io
    from PIL import Image
    r = pg.locator(sel).bounding_box()
    shot = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    k = shot.width / pg.viewport_size["width"]
    cx, cy = (r["x"] + r["width"] / 2) * k, (r["y"] + r["height"] / 2) * k
    n = 0
    for x in range(int(cx - half * k), int(cx + half * k)):
        for y in range(int(cy - half * k), int(cy + half * k)):
            pr, pg_, pb = shot.getpixel((x, y))
            if pb > 200 and pb - pg_ > 70 and pr < 190:
                n += 1
    return n


with sync_playwright() as _kp:
    _kb = _kp.chromium.launch()
    _kc = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "cat.json").read_text())
    _kc["title"] = "Kind probe"
    _kreq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(_kc).encode(),
                                   headers={"Content-Type": "application/json"})
    _kid = json.loads(urllib.request.urlopen(_kreq).read())["id"]
    _kpg = _kb.new_page(viewport={"width": 402, "height": 874}, device_scale_factor=2)
    _asked = []
    _kpg.on("request", lambda r: _asked.append(r.url) if "/api/skribls/" in r.url else None)
    browsing.goto(_kpg, BASE, "/feed")
    # The probes are the macro's own markup: the feed page carries it as the
    # template its script fills in, so no internals are written here by hand.
    _kpg.evaluate("""([gone, real]) => {
        const st = document.documentElement.style;
        st.setProperty('--bg-elev', '#f6f8fa'); st.setProperty('--text-dim', '#5b7083');
        const tpl = document.getElementById('skriblPostTpl').innerHTML;
        for (const [id, pid] of [[gone, 'goneProbe'], [real, 'dropProbe']]) {
          const host = document.createElement('article'); host.id = pid + 'Post';
          host.style.cssText = 'display:block; width: 360px; margin: 16px auto';
          host.innerHTML = tpl.split('__ID__').join(id);
          host.querySelector('.skribl-inline').id = pid;
          host.querySelector('.skribl-inline-line').id = pid + 'Line';
          document.body.prepend(host);
        }
        SkriblInline.mount(document); }""", ["gone0000000", _kid])
    # The blank must LOAD to be judged: an SVG that is not valid XML (a double
    # hyphen in its comment did it once, in this change) never paints, and a
    # box with nothing in it would pass the colour test for the wrong reason.
    try:
        _kpg.wait_for_function("() => { const i = document.querySelector('#goneProbe .skribl-inline-poster');"
                               " return i.complete && i.naturalWidth > 0; }", timeout=10000)
        _blank = True
    except PWTimeout:
        _blank = False
    _kpg.locator("#goneProbePost").scroll_into_view_if_needed(); _kpg.wait_for_timeout(300)
    _rest = _px(_kpg, "#goneProbe", 0.12, 0.5)
    check("at rest, a drawing with no poster of its own shows the page's ground, not a black box",
          _blank and _near(_rest, _GROUND),
          f"painted {_rest}, the page's ground {_GROUND}" + ("" if _blank else "; the blank poster never loaded"))

    _kpg.locator("#goneProbe").click()
    try:
        _kpg.wait_for_function("() => SkriblInline.find('gone0000000').state().failed", timeout=10000)
    except PWTimeout:
        pass
    _kpg.wait_for_timeout(300)
    _g = _kpg.evaluate("""() => { const b = document.querySelector('#goneProbe'), e = b.querySelector('.skribl-inline-err');
        const ln = document.querySelector('#goneProbeLine');
        return { words: e && !e.hidden ? e.innerText.replace(/\\s+/g, ' ').trim() : null,
                 font: e ? getComputedStyle(e).fontFamily : null, host: getComputedStyle(b.parentElement).fontFamily,
                 line: getComputedStyle(ln).display, label: b.getAttribute('aria-label'),
                 failed: SkriblInline.find('gone0000000').state().failed }; }""")
    _gonePx = _px(_kpg, "#goneProbe", 0.12, 0.5)
    _gonePurple = _purple_at_centre(_kpg, "#goneProbe")
    check("a drawing that is gone says so in plain words, and says 'drawing' -- on skribls.net every post is a Skribl",
          _g["words"] == _GONE_WORDS, f"{_g['words']!r}")
    check("...in the page's own type, not the code face",
          _g["font"] == _g["host"] and "monospace" not in (_g["font"] or ""), f"{_g['font']!r} vs the page's {_g['host']!r}")
    check("...on the page's ground, with nothing painted that asks for a tap: no Play where the words are",
          _gonePurple == 0 and _near(_gonePx, _GROUND),
          f"{_gonePurple} pixels of the Play disc's purple at the centre; the ground painted {_gonePx}")
    check("...and the line under it steps away: there is nothing to scrub",
          _g["line"] == "none", f"the line's display is {_g['line']!r}")
    check("...and the box's name says the same words, for a screen reader",
          _g["label"] == _GONE_WORDS, f"{_g['label']!r}")
    _before = len([u for u in _asked if "gone0000000" in u])
    _kpg.locator("#goneProbe").click(); _kpg.wait_for_timeout(700)
    _after = len([u for u in _asked if "gone0000000" in u])
    check("a second tap on a drawing that is gone asks the server nothing more",
          _before == 1 and _after == 1, f"payload requests: {_before} after the first tap, {_after} after the second")

    _kpg.route(f"**/api/skribls/{_kid}", lambda r: r.abort())
    _kpg.locator("#dropProbePost").scroll_into_view_if_needed(); _kpg.wait_for_timeout(200)
    _kpg.locator("#dropProbe").click()
    try:
        _kpg.wait_for_function(f"() => SkriblInline.find('{_kid}').state().failed", timeout=10000)
    except PWTimeout:
        pass
    _kpg.wait_for_timeout(300)
    _d = _kpg.evaluate("""() => { const e = document.querySelector('#dropProbe .skribl-inline-err');
        return e && !e.hidden ? [...e.querySelectorAll('span')].map(s => s.innerText.trim()) : (e ? [e.innerText] : null); }""")
    check("a drawing that couldn't load (a dropped connection) says so, and offers another try",
          _d == _DROP_WORDS, f"{_d}")
    _kpg.unroute(f"**/api/skribls/{_kid}")
    _kpg.locator("#dropProbe").click()
    try:
        _kpg.wait_for_function(f"() => {{ const s = SkriblInline.find('{_kid}').state(); return s.loaded && s.state === 'playing'; }}",
                               timeout=10000)
    except PWTimeout:
        pass
    _r = _kpg.evaluate(f"""() => {{ const s = SkriblInline.find('{_kid}').state(), b = document.querySelector('#dropProbe');
        return [s.state, s.loaded, !!s.failed, b.classList.contains('is-failed'), getComputedStyle(document.querySelector('#dropProbeLine')).display]; }}""")
    check("...and a tap tries again: with the connection back, the drawing plays and the line returns",
          _r[0] == "playing" and _r[1] and not _r[2] and not _r[3] and _r[4] != "none", f"{_r}")
    _kb.close()


print("\nIN-POST — a poster's corner is the card's own corner, round at every shape")
# fitPoster() clips the share card down to the drawing with the card's rounded
# plate. Its radius was worked out as a share of the DRAWING, and CSS resolves
# inset()'s radius against the IMAGE, which is the whole card: the corner came
# out stretched by the card's width over the drawing's. A tall drawing's was
# 27.7 x 8.1 px on a phone instead of 6.3 round, a long curve with the box's
# ground showing in it (found mocking the Gallery without its bars). Read from
# the computed clip and the image's own box, at every canvas shape, in a box
# with no line (a Gallery tile) and in one with it (a post, shaped to its
# drawing). The card's own corner is PLATE_R less the hairline, card pixels.
_CORNER_CARD = 16
_SHAPES = [(816, 612), (944, 531), (707, 707), (531, 944)]
with sync_playwright() as _rp:
    _rb = _rp.chromium.launch()
    _rc = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "cat.json").read_text())
    _rc["title"] = "Corner probe"
    _rid = json.loads(urllib.request.urlopen(urllib.request.Request(
        BASE + "/api/skribls", data=json.dumps(_rc).encode(),
        headers={"Content-Type": "application/json"})).read())["id"]
    _rpg = _rb.new_page(viewport={"width": 402, "height": 874}, device_scale_factor=2)
    browsing.goto(_rpg, BASE, "/feed")
    _rpg.evaluate("""([id, shapes]) => {
        const tpl = document.getElementById('skriblPostTpl').innerHTML;
        shapes.forEach(([w, h], k) => [false, true].forEach(line => {
          const host = document.createElement('article');
          host.style.cssText = 'display:block; width: 360px; margin: 16px auto';
          host.innerHTML = tpl.split('__ID__').join(id);
          const box = host.querySelector('.skribl-inline');
          box.id = 'corner' + k + (line ? 'post' : 'tile');
          box.setAttribute('data-skribl-w', w); box.setAttribute('data-skribl-h', h);
          if (!line) host.querySelector('.skribl-inline-line').remove();
          document.body.prepend(host);
        }));
        SkriblInline.mount(document); }""", [_rid, _SHAPES])
    _rpg.wait_for_function("() => [...document.querySelectorAll('[id^=corner] .skribl-inline-poster')]"
                           ".every(i => i.complete && i.naturalWidth > 0)", timeout=10000)
    _round = _rpg.evaluate("""(card) => [...document.querySelectorAll('[id^=corner]')].map(box => {
        const img = box.querySelector('.skribl-inline-poster'), r = img.getBoundingClientRect();
        const m = /round\\s+([\\d.]+)%(?:\\s*\\/\\s*([\\d.]+)%)?/.exec(getComputedStyle(img).clipPath);
        if (!m) return [box.id, null, null, null];
        const rx = parseFloat(m[1]) / 100 * r.width, ry = parseFloat(m[2] || m[1]) / 100 * r.height;
        return [box.id + ' ' + box.dataset.skriblW + 'x' + box.dataset.skriblH, +rx.toFixed(2), +ry.toFixed(2),
                +(card * r.width / 1200).toFixed(2)]; })""", _CORNER_CARD)
    _bent = [x for x in _round if x[1] is None or abs(x[1] - x[2]) > 0.1 or abs(x[1] - x[3]) > 0.1]
    check("a poster's corner is the card's own corner at every canvas shape: round, and the card's "
          "size wherever the box puts it, in a Gallery tile and in a post",
          len(_round) == 8 and not _bent,
          "; ".join(f"{n}: {rx} x {ry} px, the card's is {want}" for n, rx, ry, want in (_bent or _round)[:4]))
    _rb.close()


print("\nIN-POST — a page can put a box in its drawing's shape and back, and the picture follows")
# me.shape(on), for a page whose layout changes under its boxes: the Gallery
# shapes its cards one to a row and keeps them 16:9 two to a row (the owner's
# pick C). The box takes the drawing's shape or goes back to 16:9, and the
# picture before Play is framed again for the box it is in, because
# fitPoster's percentages are shares of the box: framed for the box it left,
# it lands tens of pixels from where the drawing will be. Driven on line-less
# boxes (a Gallery card's kind) cloned from the feed's own template, one that
# knows its drawing's size and one that does not. "Off" is the furthest edge of
# the picture's clip from the drawing contained in the box; up to about 2.6 px
# is the card's plate hairline, scaled up.
_SHAPE_READ = r"""(id) => {
  const box = document.getElementById(id), p = box && box._skriblInline;
  if (!p) return null;
  const r = box.getBoundingClientRect(), cs = getComputedStyle(box), b = parseFloat(cs.borderTopWidth) || 0;
  const inn = { x: r.left + b, y: r.top + b, w: r.width - 2 * b, h: r.height - 2 * b };
  const pw = +box.dataset.skriblW || 0, ph = +box.dataset.skriblH || 0;
  let off = null;
  if (pw && ph) {
    const k = Math.min(inn.w / pw, inn.h / ph), w = pw * k, h = ph * k;
    const want = { x: inn.x + (inn.w - w) / 2, y: inn.y + (inn.h - h) / 2, w: w, h: h };
    const img = box.querySelector('.skribl-inline-poster'), ir = img.getBoundingClientRect();
    const m = /inset\(([^)]*?)(?:\s+round[^)]*)?\)/.exec(getComputedStyle(img).clipPath || '');
    if (m) {
      const v = m[1].trim().split(/\s+/).map(x => parseFloat(x) / 100);
      const tp = v[0], rp = v.length > 1 ? v[1] : v[0], bp = v.length > 2 ? v[2] : v[0], lp = v.length > 3 ? v[3] : rp;
      const sx = ir.left + lp * ir.width, sy = ir.top + tp * ir.height;
      const sw = ir.width * (1 - lp - rp), sh = ir.height * (1 - tp - bp);
      off = +Math.max(Math.abs(sx - want.x), Math.abs(sy - want.y),
                      Math.abs(sx + sw - want.x - want.w), Math.abs(sy + sh - want.y - want.h)).toFixed(2);
    }
  }
  return { shaped: box.classList.contains('is-shaped'), ar: +(r.width / r.height).toFixed(4),
           size: [+r.width.toFixed(1), +r.height.toFixed(1)], off: off, can: typeof p.shape === 'function' };
}"""
with sync_playwright() as _sp2:
    _sb = _sp2.chromium.launch()
    _sc = json.loads((ROOT / "skribl" / "static" / "help" / "demos" / "cat.json").read_text())
    _sc["title"] = "Shape probe"
    _sid = json.loads(urllib.request.urlopen(urllib.request.Request(
        BASE + "/api/skribls", data=json.dumps(_sc).encode(),
        headers={"Content-Type": "application/json"})).read())["id"]
    _spg = _sb.new_page(viewport={"width": 402, "height": 874}, device_scale_factor=2)
    browsing.goto(_spg, BASE, "/feed")
    _spg.evaluate("""(id) => {
        const tpl = document.getElementById('skriblPostTpl').innerHTML;
        [['shapeTall', 531, 944], ['shapeUnsaid', 0, 0]].forEach(([name, w, h]) => {
          const host = document.createElement('article');
          host.style.cssText = 'display:block; width: 360px; margin: 16px auto';
          host.innerHTML = tpl.split('__ID__').join(id);
          const box = host.querySelector('.skribl-inline');
          box.id = name;
          if (w) { box.setAttribute('data-skribl-w', w); box.setAttribute('data-skribl-h', h); }
          host.querySelector('.skribl-inline-line').remove();
          document.body.prepend(host);
        });
        SkriblInline.mount(document); }""", _sid)
    _spg.wait_for_function("() => [...document.querySelectorAll('[id^=shape] .skribl-inline-poster')]"
                           ".every(i => i.complete && i.naturalWidth > 0)", timeout=10000)
    _SHAPE = "([id, on]) => { const p = document.getElementById(id)._skriblInline; if (p.shape) p.shape(on); }"
    _rest = _spg.evaluate(_SHAPE_READ, "shapeTall")
    check("a box with no line rests 16:9, its picture framed for 16:9",
          bool(_rest) and not _rest["shaped"] and abs(_rest["ar"] / (16 / 9) - 1) < 0.01
          and _rest["off"] is not None and _rest["off"] <= 3, str(_rest))
    _spg.evaluate(_SHAPE, ["shapeTall", True])
    _on = _spg.evaluate(_SHAPE_READ, "shapeTall")
    check("shape(true) gives it the drawing's shape and frames the picture again for that box",
          bool(_on) and _on["can"] and _on["shaped"] and abs(_on["ar"] / (531 / 944) - 1) < 0.01
          and _on["off"] is not None and _on["off"] <= 3, str(_on))
    _spg.evaluate(_SHAPE, ["shapeTall", False])
    _off = _spg.evaluate(_SHAPE_READ, "shapeTall")
    check("...and shape(false) puts it back to 16:9, the picture framed for 16:9 again",
          bool(_off) and _off["can"] and not _off["shaped"] and abs(_off["ar"] / (16 / 9) - 1) < 0.01
          and _off["off"] is not None and _off["off"] <= 3, str(_off))
    _spg.evaluate(_SHAPE, ["shapeUnsaid", True])
    _un = _spg.evaluate(_SHAPE_READ, "shapeUnsaid")
    check("a box that doesn't know its drawing's size stays 16:9 when asked to take its shape",
          bool(_un) and _un["can"] and not _un["shaped"] and abs(_un["ar"] / (16 / 9) - 1) < 0.01, str(_un))
    _sb.close()


passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
