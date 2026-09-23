"""Does the player carry the editor? Written BEFORE the split, to fail.

`app.js` serves the editor AND the public player. Measured with Chrome's
coverage profiler, the player executes about 31% of it: ~94.5 KB used, ~202.4 KB
that never runs. Everyone who opens a shared link downloads the recorder, the
GIF and MP4 encoders, autosave and the drawer wiring in order to run none of it.

This suite is the acceptance test for splitting that apart, and it has two
halves that must move in opposite directions:

  HALF A — PLAYBACK STILL WORKS. Passes NOW and must never stop passing. If the
  split breaks rendering, this is what says so. It is deliberately the first
  half: a player that is small and blank is a worse player.

  HALF B — THE EDITOR IS NOT THERE. Fails NOW, by design, and passes when the
  split lands. Every assertion names something measured on the unsplit tree.

A note on how the payload is produced. The first version of this built a payload
by hand and posted it to the API, and the player rendered nothing — 0 ink on an
unsized 300x150 canvas. That looked exactly like a broken player and was a
malformed fixture. It now records a real drawing in Pad and follows the share
link the app itself produced, which is also the path a real viewer takes.
"""
import math
import pathlib
import re
import struct
import sys
import wave

from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/player_isolation.wav"

# THE FIXTURE HAS AUDIO ON PURPOSE, and it is load-bearing for the split.
#
# The first version of this authored a SILENT drawing. Chrome's coverage
# profiler then reported every loop-building function in app.js as unused —
# buildLoopAudioBuffer, buildLoopChannels, the lot — because nothing had asked
# them to run. Reading that profile as "editor-only, safe to move" would have
# shipped a player that cannot play music, and this suite would have called it
# green, because its own fixture was silent too. A measurement taken through a
# fixture that never exercises a path proves nothing about that path.
#
# So the fixture now carries a real trimmed loop, and playback is asserted with
# an analyser tap on the audio graph — real signal, not the existence of a node.
# The tap is the same one verify_audio.py uses, deliberately: a second way of
# measuring audio is a second thing to drift.
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
window.__tapMax = 0;
(function () {
  const Orig = window.AudioContext || window.webkitAudioContext;
  function Tapped() {
    const ctx = new Orig();
    window.__ctx = ctx;
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


# Editor-only globals. Every one of these was CONFIRMED PRESENT on a real player
# page before this suite was written — a list of plausible names would prove
# nothing, since an absent-but-never-there symbol passes for free.
# MEASURED, so the next person does not have to redo the analysis to decide.
#
# All five of these are unreachable from the player's entry point -- the same
# reachability walk verify_seam.py runs puts every one of them in the
# editor-only set, and none of their app.js call sites is player-reachable
# either. The player downloads roughly 5.7 KB of source it can never execute.
# Where each is actually called:
#
#   pressureSize      editor_draw.js, twice, and nothing else. Its neighbour
#                     comment in that file claimed it stays in app.js because
#                     replayTimelineToCanvas hands drawLine/drawDot to the
#                     player -- true of those two, never of this one. Corrected
#                     there.
#   setTool           editor_draw, editor_shapes, editor_tune, lib/eyedropper,
#                     lib/toolshelf
#   saveDraft         editor_menu, editor_post
#   addRecent         lib/recentcolors
#   attachSegSlider   editor_export, editor_music, editor_shapes, editor_tools
#
# NOT MOVED, AND THAT IS A DECISION. Every call site is inside a function --
# there is not one load-time caller, which was the thing that could have made
# the move unsafe -- so the obstacle is not correctness, it is judgement about
# where each belongs. saveDraft has an obvious home in editor_draft.js and
# pressureSize in editor_draw.js; setTool and addRecent have a defensible one;
# attachSegSlider has none, and editor_tools.js is an IIFE, so a function
# declared there would stop being the global its four callers read. A new
# editor_shared.js would take all five and would be a file whose contents are
# "things that had nowhere better to go".
#
# What the target is FOR is evidence that the player needs no separate entry
# point (see verify_jsstrip's note). Five editor-only globals on a 154 KB
# player is a 2.5% saving against a refactor of tool selection, stylus
# pressure and autosave -- core editor paths, for bytes. This tree's own
# stopping condition asks for "a specific duplicated or obsolete concept with
# concrete maintenance cost"; these are correctly-written editor code that
# happens to share a file with the player, which is a different thing. The
# measurement is here so the move can be chosen on its merits rather than
# started because a number reads 5.
EDITOR_GLOBALS = [
    "setTool",           # tool selection — the player has no tools
    "pressureSize",      # stylus capture
    "saveDraft",         # autosave
    "addRecent",         # recent colours
    "attachSegSlider",   # segmented-control wiring
    "openHelpDrawer",    # help drawer
]

# Editor-only DOM. All of these were CONFIRMED IN the player's document and
# simply not painted, so the player ships the authoring shell's markup too —
# this is not only a JavaScript problem. `exportPng` belongs here rather than in
# the globals list above: it is an element id, and the browser publishes ids as
# window properties, so `typeof window.exportPng !== 'undefined'` was true
# because of the MARKUP, not because a function of that name exists. Asserting
# it as a global would have quietly turned into a DOM assertion.
EDITOR_DOM = ["recordBtn", "helpDrawer", "exportSheet", "musicInput",
              "photoInput", "undoBtn", "postBtn", "exportPng"]


# The player fits the drawing into the COLUMN, not the viewport. playerFitScale()
# used `window.innerWidth - 40`, and .app has a max-width: on a 1023px viewport
# the column is 718px, the scale hit its 1:1 cap, the wrap was set to the
# authored 816px, and `overflow: hidden` cropped ~100px off the right of every
# shared link. It reached a user as "the image is off the edge" and was first
# misattributed to a different bug entirely, because the crop only appears when
# the viewport is WIDER than the column — which no fixture used.
FIT_GEOMETRY = """() => {
  const w = document.querySelector('.canvas-wrap'), c = document.getElementById('canvas');
  if (!w || !c) return null;
  const wr = w.getBoundingClientRect(), cr = c.getBoundingClientRect();
  return { wrapW: Math.round(wr.width), canvasW: Math.round(cr.width),
           wrapH: Math.round(wr.height), canvasH: Math.round(cr.height),
           scrolls: document.documentElement.scrollHeight > window.innerHeight + 2 };
}"""


INK = """() => {
  const c = document.getElementById('canvas');
  if (!c) return null;
  const r = c.getBoundingClientRect();
  let ink = 0;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) ink++;
  return {bitmap: [c.width, c.height],
          rect: [Math.round(r.width), Math.round(r.height)], ink};
}"""


def scribble(pg, box, n=120):
    """Draw over roughly three seconds of WALL CLOCK, deliberately.

    Strokes carry timestamps, so a drawing made as fast as the mouse can move
    replays in under a second. The first version of this waited 30ms every
    twentieth point — about 180ms of recorded time — and the replay was over
    before anything could be sampled: the progress bar read 100% on the first
    poll and the audio source had started and finished between the click and the
    measurement. The fixture has to last long enough to be observed mid-flight.
    """
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * 120
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
        if i % 5 == 0:
            pg.wait_for_timeout(120)
    pg.mouse.up()


with sync_playwright() as sp:
    # Same flags verify_audio.py uses. Headless Chromium blocks autoplay by
    # default, so without this the analyser reads 0 and the failure looks like a
    # broken player rather than a browser policy.
    b = sp.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                                 "--use-fake-device-for-media-stream"])

    # ---- author a real Skribl in Pad and take the share link it gives back ----
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    ed_errs = []
    pg.on("pageerror", lambda e: ed_errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => localStorage.clear()")
    scribble(pg, pg.locator("#canvas").bounding_box())
    pg.wait_for_timeout(700)
    pg.click("#recordBtn")          # stop the take
    pg.wait_for_timeout(400)
    editor = pg.evaluate(INK)

    # Attach a real, TRIMMED loop. Trimming matters: an untrimmed upload can be
    # stored and replayed without ever building a loop buffer, which would leave
    # buildLoopChannels unexercised and put us back where we started.
    pg.set_input_files("#musicInput", WAV)
    pg.wait_for_timeout(4000)
    pg.evaluate("() => { trimStart = 1.0; trimEnd = 4.0; loopCrossfadeMs = 120; "
                "if (typeof updateTrimUI === 'function') updateTrimUI(); }")
    pg.wait_for_timeout(1200)
    has_audio = pg.evaluate("() => { const has = (typeof audioEl !== 'undefined' && audioEl && audioEl.src) || (typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer); return !!has; }")
    loop_len = pg.evaluate("() => (typeof trimEnd === 'number' && "
                           "typeof trimStart === 'number') ? +(trimEnd - trimStart).toFixed(2) : null")

    pg.click("#postBtn")
    pg.wait_for_timeout(1200)
    pg.click("#postSubmitBtn")
    pg.wait_for_timeout(8000)
    # THE RECORD, not the DOM: the drawer whose row used to carry the URL
    # left the editor in v304 (Your Skribls is the profile page), so the
    # link is read from what the product keeps, lib/posted.js's entry --
    # which is where a person finds it again too.
    link = pg.evaluate("""() => {
        const kept = (window.SkriblPosted && window.SkriblPosted.list) ? window.SkriblPosted.list() : [];
        const rec = kept.map(e => e && e.url).find(u => typeof u === 'string' && u.includes('/s/'));
        if (rec) return rec;
        const v = [...document.querySelectorAll('*')]
          .map(e => e.value || e.href || '')
          .find(v => typeof v === 'string' && v.includes('/s/'));
        return v || null; }""")
    pg.close()

    # A missing link means the FIXTURE failed, not the player. Say which, or the
    # next reader spends the session debugging a player that was never reached.
    if not link:
        check("posting produced a share link (fixture)", False,
              f"no /s/ URL in the post sheet; editor errors: {ed_errs[:2]}")
        print("\n" + "=" * 62 + "\n0/1 passed")
        sys.exit(1)
    if link.startswith("/"):            # the record keeps the server's path; the browser needs the origin
        link = BASE + link
    print(f"authored {link}")
    print(f"editor rendered {editor['ink']} inked pixels at {editor['bitmap']}, "
          f"audio attached: {has_audio}, loop {loop_len}s\n")

    # ---- load it the way a viewer does -------------------------------------
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.add_init_script(TAP)      # must be in place before any page script runs
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    js_bytes = {}

    html_bytes = {}

    # CSS was not collected here until now, and that omission is the same
    # mistake this file already records making with HTML — see the note above
    # the HTML ratchet. A measurement that sees part of the payload rewards
    # moving weight into the part it cannot see, and in this case it did not
    # even need moving: styles.css simply grew, from 119,844 to 123,283 bytes
    # across v194-v198, while every ratchet in this suite stayed green.
    css_bytes = {}

    # WIRE SIZE IS NOT WHAT THESE RATCHETS ARE WRITTEN AGAINST, and reading
    # content-length made every one of them inert.
    #
    # security.py gzips compressible responses when the request accepts it, and
    # Chromium always does. content-length on such a response is the COMPRESSED
    # length, so this collector was reporting app.js at 65,230 bytes against a
    # ratchet of 232,000 — roughly 160,000 bytes of headroom in a mechanism whose
    # whole purpose is to have none. Every number the ratchets were set from
    # (329,159 -> 231,106, HTML 56,716 -> 7,989, the 153,600 target) is a SOURCE
    # size, and the extraction work they measure removes source bytes, not
    # compressed ones. The measurement has to be on the same basis as the
    # constant or the comparison is meaningless.
    #
    # r.body() returns the decoded body, so this measures what the browser
    # actually parses. Wire size is reported alongside, because it is the number
    # "what a visitor downloads" should quote, and the two are not the same fact.
    wire_bytes = {}

    def _record(r):
        u = r.url.split("?")[0]
        try:
            n = len(r.body())
        except Exception:
            return
        try:
            wire_bytes[u.split("/")[-1]] = int(r.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            pass
        if u.endswith(".js"):
            js_bytes[u.split("/")[-1]] = n
        elif u.endswith(".css"):
            css_bytes[u.split("/")[-1]] = n
        elif "/s/" in u and "text/html" in (r.headers.get("content-type") or ""):
            html_bytes[u.split("/")[-1]] = n

    pg.on("response", _record)
    pg.goto(link, wait_until="load")
    pg.wait_for_timeout(3500)
    player = pg.evaluate(INK)

    print("FIT — the drawing is not cropped by the column it sits in")
    # 1280 above is already wider than .app's max-width, which is the case that
    # used to crop. Check a second, much wider viewport too: the failure grows
    # with the gap between viewport and column, so a narrow fixture hides it.
    for _vw in (1280, 1600):
        pg.set_viewport_size({"width": _vw, "height": 900})
        pg.wait_for_timeout(400)
        _g = pg.evaluate(FIT_GEOMETRY)
        check(f"at {_vw}px the canvas fits inside its wrapper",
              _g and _g["canvasW"] <= _g["wrapW"] and _g["canvasH"] <= _g["wrapH"],
              f"canvas {_g and (_g['canvasW'], _g['canvasH'])} in wrap "
              f"{_g and (_g['wrapW'], _g['wrapH'])} — overflow:hidden means the "
              "difference is drawing the viewer never sees")
        check(f"and the page does not scroll at {_vw}px",
              _g and not _g["scrolls"],
              "the fit reserves vertical space for the shell; a scrollbar means "
              "it reserved too little")
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.wait_for_timeout(300)

    # ================= HALF A — playback still works ========================
    print("HALF A — playback (must keep passing through the split)")

    check("the player is in player mode",
          "player-mode" in pg.evaluate("() => document.body.className"))

    check("the player renders the drawing at its authored size",
          player is not None and player["bitmap"] == editor["bitmap"],
          f"player {player and player['bitmap']} vs editor {editor['bitmap']}")

    # Ink, not existence. A canvas that is present and blank passes any
    # "is there a canvas" check, which is the failure this must not miss.
    check("the player actually paints ink, not just a canvas",
          player is not None and player["ink"] > 500,
          f"{player and player['ink']} inked pixels")

    # The two surfaces replay the same strokes through the same code, so the
    # counts should agree closely. A tolerance rather than equality because
    # antialiasing at a different display scale moves the edge pixels.
    if player and editor["ink"]:
        drift = abs(player["ink"] - editor["ink"]) / editor["ink"]
        check("the player's drawing matches what the editor drew",
              drift <= 0.02,
              f"player {player['ink']} vs editor {editor['ink']} "
              f"({drift * 100:.2f}% apart)")

    # The fixture is only worth having if it really carried audio. Asserted
    # rather than assumed: a silent fixture is what made the coverage profile
    # lie, and it would fail silently again.
    check("the fixture actually carried a trimmed loop (not a silent drawing)",
          has_audio and loop_len == 3.0,
          f"audio attached: {has_audio}, loop length: {loop_len}s")

    check("the player knows the post has audio",
          pg.evaluate("() => { const has = (typeof audioEl !== 'undefined' && audioEl && audioEl.src) || (typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer); return !!has; }"),
          "the loop did not survive the round trip to the player")

    # #playerPlayBtn, NOT #playBtn. The editor's play button is present in the
    # player's document but never painted, so clicking it times out and the
    # analyser then reads 0 — which looks exactly like a player that cannot play
    # audio. The player's own transport is in _skribl_player_controls.html.
    check("the player's own transport control is painted",
          pg.evaluate("() => { const b = document.getElementById('playerPlayBtn');"
                      " return !!b && b.offsetParent !== null; }"),
          "#playerPlayBtn is what a visitor actually clicks")
    # Sample DURING the replay, from the moment it starts. The window is finite:
    # once playback ends the source is gone and the analyser reads silence again,
    # which is indistinguishable from never having played.
    pg.click("#playerPlayBtn")
    peak = 0
    for _ in range(20):
        pg.wait_for_timeout(150)
        peak = max(peak, pg.evaluate(PEAK))
        if peak > 4:
            break
    check("the player produces audible signal, not just an audio graph",
          peak > 4,
          f"analyser peak {peak} (0 = silence; the graph can exist and play nothing)")

    check("no page errors on the player", not errs, str(errs[:3]))

    # ================= HALF B — isolation ratchets ==========================
    # These three began as flat acceptance assertions and FAILED, which is how
    # the split was scoped: 7/7 editor globals reachable, 8/8 authoring controls
    # in the document, 329,159 bytes downloaded. The first cut (editor_export.js
    # and editor_post.js out of app.js) removed 56,727 of those bytes.
    #
    # They are RATCHETS now, not targets. Each asserts that the measurement does
    # not grow past where it currently stands, and each states the target it is
    # still short of. That keeps the win from silently eroding while the rest of
    # the split is done — but a green run here does NOT mean the player is
    # extracted. It means the player is not getting worse. The definition of
    # done is in START-HERE; when a cut lands, tighten the number beside it.
    print("\nMISSING — a Skribl that is not there says so, and offers no dead retry")
    # v287 audit SK-BUG-005: /s/<unknown> answered 200 with "This Skribl
    # couldn't be found. Try again" — a status that told crawlers the page had
    # content, and a button that could not succeed (a reload cannot make a
    # missing Skribl appear). The status is asserted on the wire; the panel and
    # the button on the rendered page; and the retry's OTHER case — a network
    # failure, where a reload is exactly right — is driven by aborting the fetch
    # on a real post, so the button's absence here is not its absence everywhere.
    import urllib.request as _ur, urllib.error as _ue
    try:
        with _ur.urlopen(BASE + "/s/not-a-real-id", timeout=15) as _r:
            _st, _body = _r.status, _r.read().decode()
    except _ue.HTTPError as _e:
        _st, _body = _e.code, _e.read().decode()
    check("GET /s/<unknown> answers 404", _st == 404, f"status {_st}")
    check("...and still renders the player shell, so the page can say so itself",
          'id="playerError"' in _body and 'id="playerShell"' in _body)
    VIS = """() => { const vis = el => !!el && !el.hidden && el.offsetParent !== null;
      return { panel: vis(document.getElementById('playerError')),
               retry: vis(document.getElementById('playerRetryBtn')),
               msg: (document.getElementById('playerErrorMsg') || {}).textContent || '' }; }"""
    _mp = b.new_page(viewport={"width": 1280, "height": 900})
    _mp.goto(BASE + "/s/not-a-real-id", wait_until="load")
    _mp.wait_for_timeout(1200)
    _m = _mp.evaluate(VIS)
    check("the page says the Skribl could not be found", _m["panel"] and "found" in _m["msg"], str(_m))
    check("...and offers no Try again for it", _m["retry"] is False,
          "a reload cannot make a missing Skribl appear; the button is a promise it cannot keep")
    _mp.close()
    _np = b.new_page(viewport={"width": 1280, "height": 900})
    _np.route("**/api/skribls/**", lambda route: route.abort())
    _np.goto(link, wait_until="load")          # the /s/ URL the post sheet handed back above
    _np.wait_for_timeout(1200)
    _n = _np.evaluate(VIS)
    check("a network failure on a real post keeps Try again", _n["panel"] and _n["retry"] is True, str(_n))
    _np.close()

    print("\nHALF B — isolation ratchets (green ≠ done; see the targets)")

    # Tightened after each cut. Loosening one of these needs a reason written
    # beside it, or the ratchet is just a number that follows the code down.
    #   329,159 / 7 globals  unsplit
    #   272,432 / 6          editor_export.js + editor_post.js
    #   261,707 / 5          editor_menu.js
    #   262,944 / 5          clampTrim split out of updateTrimUI
    #   263,451 / 5          resetMediaForLoad teardown split
    #   257,592 / 5          tab panels out; media_validation.js off the player
    #   243,428 / 5          music drawer WIRING out (editor_music.js)
    #   231,106 / 5          photo drawer wiring + eraser cursor (editor_photo.js)
    #   HTML: 56,716 -> 7,989 across the same run
    #
    # LOOSENED ONCE, DELIBERATELY: 263,000 -> 264,000. The player-mode guards in
    # loadSkribl and resetMediaForLoad are PREP for the music drawer cut.
    #
    # The first version of this note claimed they unlock "roughly 34 KB". That
    # was the size of the whole region, asserted before measuring, and it is
    # wrong. Measured: the region is 34,947 bytes, of which ~14.9 KB is
    # functions the player calls (drawWaveform, showToast, clampTrim and the
    # rest) that CANNOT move, ~6 KB is functions with no reference outside the
    # region, and ~14 KB is top-level wiring. The realistic cut is well under
    # half the region.
    #
    # THE DEBT, restated against the real number: when the drawer moves, this
    # must come back below 262,000 — the guards cost ~1.7 KB and the cut has to
    # return more than that to have been worth making. If a future session finds
    # this line at 264,000 with no drawer cut behind it, the prep was never
    # cashed in.
    # THE BYTES TARGET IS NOT REACHABLE BY EXTRACTION. Measured, not estimated
    # (harness/tools/refgraph.js, AST over app.js):
    #
    #   player downloads now                        231,106 B  (4 files)
    #   target                                      153,600 B
    #   gap                                          77,506 B
    #   ALL editor-only functions in app.js          71,633 B
    #   -> move every one, land at                  159,473 B   still 5,873 over
    #
    # And that best case assumes the ~34 KB pinned by top-level wiring is
    # unpinned first, which is the call-site restructuring, not a file move.
    # What is left over is not functions at all: roughly 88 KB of app.js is
    # top-level wiring and comments, outside every function body. Reaching
    # 153,600 means app.js stops being the player's file — a separate player
    # entry point. See docs/REFACTOR-v132.md.
    #
    # 153,600 is KEPT here deliberately, as the honest distance to a player that
    # loads only what it runs. It is not a number the next cut can hit, and a
    # session that treats it as one will repeat v132. Move it only alongside the
    # entry-point work, or when a reason is written beside it.
    #
    # GLOBALS_TARGET has the same shape: of the five remaining, four
    # (setTool, pressureSize, addRecent, attachSegSlider) are named by top-level
    # statements, so 5 -> 0 is that same restructuring in miniature, not a cut.
    # UNGUARDED EDITOR DOM. Two production outages came from this one shape:
    # app.js dereferencing an element the v190 cut removed from the player.
    #   loadSkribl:  getElementById('photoDetail').hidden = false  -> threw on
    #     every shared link with a photo, aborting the restore mid-way, which
    #     reached users as a Flip post that would not play, a Pad drawing
    #     hanging off the canvas edge, and a misplaced replay nib.
    #   startDraw:   getElementById('drawPanel').hidden -> threw on a TAP, so
    #     the link loaded fine and broke only when touched.
    # Both were found by a user, not here. The suites drove the player with
    # drawings and with music, so neither fixture entered the branch that broke.
    #
    # This asserts on the SHAPE, not on the two instances: any
    # `getElementById('x').` where x is absent from the player template and its
    # partials. That covers the ones nobody has hit yet, which is the point —
    # a reachability argument is what failed twice, and this needs none.
    # Remaining nine are pending-card and drawer-label writes on paths the
    # player is not believed to reach; "not believed to reach" is exactly the
    # claim that was wrong before, so they are counted, not excused.
    DOM_DEREF_RATCHET, DOM_DEREF_TARGET = 9, 0
    GLOBALS_RATCHET, GLOBALS_TARGET = 5, 0

    ROOT = pathlib.Path(__file__).resolve().parent.parent
    _player_tpl = (ROOT / "skribl" / "templates" / "skribl" /
                   "skribl_player.html").read_text(encoding="utf-8")
    _app_src = (ROOT / "skribl" / "static" / "app.js").read_text(encoding="utf-8")
    _player_ids = set(re.findall(r'id="([^"]+)"', _player_tpl))
    for _inc in re.findall(r"""include\s+['"]([^'"]+)['"]""", _player_tpl):
        _p = ROOT / "skribl" / "templates" / _inc
        if _p.is_file():
            _player_ids |= set(re.findall(r'id="([^"]+)"', _p.read_text(encoding="utf-8")))
    _deref = sorted({m.group(1) for m in re.finditer(
        r"""document\.getElementById\(\s*['"]([A-Za-z0-9_-]+)['"]\s*\)\s*\.""",
        _app_src)} - _player_ids)
    check(f"app.js dereferences at most {DOM_DEREF_RATCHET} elements the player "
          f"does not have (target {DOM_DEREF_TARGET})",
          len(_deref) <= DOM_DEREF_RATCHET,
          f"{len(_deref)}: {', '.join(_deref)} — each is a TypeError waiting for "
          "the first viewer whose skribl reaches that line")


    DOM_RATCHET, DOM_TARGET = 0, 0          # reached: the shell is out of the player
    # 232,000 until v199, and RED at 234,611: app.js grew 3,635 B across
    # v194-v198 while this collector read content-length, which is the GZIPPED
    # length, so nothing could see it. Both halves are fixed — the measurement
    # reads r.body(), and skribl/jsstrip.py strips comments at serve time — and
    # this is the post-strip number, set at exactly today's value in the same
    # spirit as CSS_RATCHET below. The comments still exist in every source
    # file; they are simply no longer parsed by a browser that will never read
    # them. verify_jsstrip.py is what proves the strip preserves meaning.
    # 142,344 = 142,220 (v204) + 119 B: the v206 cross-load guard in the
    # draft-input handler — refuses a Flip .skribl in Pad with directions,
    # instead of silently loading an EMPTY drawing that said "Draft loaded"
    # (data loss dressed as success). Golfed to its irreducible condition +
    # message. It stays in app.js because the PLAYER template also carries
    # #draftInput, so the handler is not editor-only and could not be moved
    # to editor_menu.js. RAISE FLAGGED FOR OWNER: same category as the two
    # prior approved raises (A1 audio, grid hook) — small, functional,
    # user-protecting, golfed first. History of the number: 141,730 / 141,824
    # lows after real cuts; +430 (A1) / +60 (grid hook) / +119 (this) raised.
    # 142,370 = 142,344 (v206) + 23 B: v208's F4 fix — beginRecording() closes
    # the Pad tune drawer via `window._skriblClosePadTune?.()` (optional
    # chaining; the hook itself lives in editor-only editor_tune.js). Golfed to
    # one call. APPROVED by the owner in the v209 session, with the three
    # prior raises (A1 audio, grid hook, cross-load guard).
    # 142,880 = 142,370 (v208) + 510 B: v209's F3 fix — Pad replay's Web Audio
    # unlock. resume() is now called INSIDE the Play gesture (unlockWebAudio),
    # its promise is retained, and the loop source starts only once that
    # resolves; a generation counter stops a late start overtaking a stop.
    # Golfed from 623 B (one closure instead of a second top-level function,
    # the file's own dense one-liner style). APPROVED by the owner at the v209
    # seal. Same category as the four prior approved raises and, specifically,
    # the same FIX as A1 (+430 B) applied to the editor replay A1 missed.
    #
    # AND THE CHEAPER ANSWER, MEASURED, FOR WHOEVER TAKES THE NEXT PASS: the
    # whole Web Audio loop block (_waLoopSource … webAudioLoopSongTime) is
    # ~2,060 code bytes and is EDITOR-ONLY — startWebAudioLoop, playMusicLooped
    # and startLoopPreview are reached from the Play button and the music
    # drawer, never from the player, which has its own pa* audio path. Moving
    # it to an editor-only file the way editor_tune.js went would CUT roughly
    # four times this raise. Not done here on purpose: an audio fix and an
    # externalisation in one pass makes a silent replay unattributable. Watch
    # stopWebAudioLoop — 8 call sites, several on teardown paths.
    # 143,217 = 142,880 (v209) + 337 B: v210's player-audio fix — the bug a
    # real iPhone found and 2,337 assertions could not. paStartAtElapsed no
    # longer constructs a source on a suspended context (it awaits the unlock
    # and re-checks a generation across the await), stopWebAudioLoop/paStop
    # invalidate pending starts, and a REJECTED resume no longer starts anyway
    # (v209 review F1+F2). Includes deleting A1's unreachable retry. RAISE
    # FLAGGED FOR OWNER: the largest single functional raise since A1 (+430),
    # and for the same class of defect A1 was meant to fix but did not.
    #
    # A temporary on-device diagnostic (audiodebug.js, wrapping the real Web
    # Audio API rather than hooking app.js) was used to trace this on the
    # owner's iPhone and then REMOVED before sealing — its useful checks live
    # in verify_audiostate now. If a runtime debugger is ever wanted again it
    # needs its own contract; it must not ride into the player budget.
    # 144,301 = 143,217 + 1,084 B: the native-<audio> HANDOFF. Refusing to
    # start on a suspended context is right, but on the owner's iPhone the
    # AudioContext never reaches 'running' at all — Test Seam (native <audio>)
    # plays there while Preview Loop (Web Audio) does not — so refusing alone
    # turned intermittent silence into total silence. startWebAudioLoop() now
    # takes an onFail handler and the two callers' native paths were split into
    # callable functions (playNativeLooped, startLoopPreviewNative) so they are
    # reachable when the unlock fails ASYNCHRONOUSLY, including a 600 ms timeout
    # for a resume() that never settles — iOS does that instead of rejecting.
    # RAISE FLAGGED FOR OWNER, and this one is big.
    #
    # HONEST COUNTER-ARGUMENT the owner should weigh: most of this is EDITOR
    # code sitting in the player's budget. The externalisation noted below
    # (~2,060 B of Web Audio loop code that the player never executes) would
    # more than pay for it. If the answer is "not another raise", the cut is
    # available and identified — it is deferred only to keep an audio fix and a
    # code move in separate builds.
    # 145,053 = 144,301 + 752 B: BUG A + BUG B, the two deterministic causes of
    # iPhone-silent shared links, both reproduced in the harness before being
    # fixed (verify_audiostate, 16 pins, both mutation-tested against the exact
    # historical mistakes). A: loop bounds installed synchronously from the
    # payload and finalised from the decoded buffer, so loadedmetadata is no
    # longer load-bearing. B: window.SkriblPayload.currentFrameMedia(), the
    # writer-side accessor for current-frame media, so the post-time crop stops
    # guarding on a field serializeSkribl() stopped producing at v2. RAISE
    # FLAGGED FOR OWNER. All temporary AUDIODEBUG instrumentation and
    # audiodebug.js were removed before this figure was taken; verify_seam
    # dropping 124 -> 121 is the evidence the extra file is gone.
    # 145,649 = 145,053 + 596 B: the header fit (v210). fitBrand measured
    # scrollWidth, which never grows when the cluster OVERLAPS the wordmark;
    # it now measures the real gap to the brand and sheds in cost order
    # (wordmark, Record label, inter-control gap, Post label), plus the
    # currentFrameMedia accessor. Owner: "don't worry about the ratchet, just
    # make the whole thing fixed" — set to fit. Full accounting for every raise
    # this arc is above; the externalisation gives most of it back.
    # 145,881 = 145,649 + 232 B: pixel-snapping the header cluster, which is
    # what closed verify_cssplit's twice-failing 4x34 sub-pixel strip at the
    # source rather than loosening a zero-tolerance pixel test. Owner: set to
    # fit. FINAL v210 figure.
    # 145,994 = 145,881 + 113 B: Space+drag fix (v211). The grab-pan
    # intercept was gated on zoom>1, so at 100% Space+drag DREW A LINE
    # (owner, desktop); Space now always claims the drag and startDraw refuses
    # a stroke while it is held. Pinned on both editors at both zoom states,
    # mutation-tested (the old gate back -> pad@100% fails, magnified passes).
    # Owner: set to fit.
    # 146,911 = 145,994 + 917 B: v210 review H1 (player native-<audio>
    # fallback when Web Audio cannot unlock — rejection, never-settles, or
    # resume landing on a still-suspended context — aligned to the drawing,
    # paused by paStop) and the F2 decode-await comments in app.js. Owner:
    # set to fit. The ~2,060 B editor-only Web Audio loop externalisation
    # noted above is now worth doing in its own build — it would recover
    # most of this arc's raises.
    # 147,120 = 146,911 + 209 B: v212 trim-strip repaint. drawWaveform() sized
    # #waveformCanvas from musicTrack's rect with no guard and is called ONLY
    # from the decode chain, so a decode landing while the music drawer was shut
    # sized the canvas to 0 (which CLEARS it), painted zero peaks, and nothing
    # ever repainted — the strip stayed blank while Loop Detail, guarded and
    # re-called from updateTrimUI(), drew correctly from the same buffer.
    # Guard on both editors + a repaint from Pad's openDrawer() music branch.
    # Owner: reported from a phone. Set to fit. NOTE THE COST IS ALMOST ALL
    # COMMENT: 2,428 B of source, 209 B served, because jsstrip removes the
    # rest at serve time — the third "sized from a rect with no layout yet" bug
    # in this drawer, and naming the pattern in place is worth 209 B.
    # 147,685 = 147,120 + 565 B: v213 eraser-width extraction. The `size * 3`
    # multiplier existed in SEVEN places across the two editors, including both
    # eraser-CURSOR sites, where a drifted copy leaves the ring lying about how
    # much it erases. `_eraserSize()` and the #eraserSeg wiring both live in
    # app.js, so the PLAYER carries them; lib/erasersize.js itself is loaded
    # only by the two editor templates (verified: 0 hits in skribl_player.html).
    # Owner: set to fit — this is a scratch build, not a seal.
    # WORTH KNOWING: the wiring block is editor-only work sitting in the shared
    # file, exactly the shape editor_music.js and editor_photo.js were carved
    # out of. If the tool row keeps growing, that carve is the place to give
    # this back rather than raising again.
    # 148,138 = 147,685 + 453 B: v213 pause handling. The 50ms idle-gap cap was
    # hardcoded at both gap sites; it is now PAUSE_CAPS + pauseMode, written into
    # the payload by serializeSkribl and adopted by loadSkribl. The player pays
    # for this ON PURPOSE — it builds its timeline with the same
    # buildPlaybackTimeline(), so without the adopt the author's replay and the
    # viewer's would differ on the same Skribl (mutation-measured: 1,903ms
    # against 410ms). This is the rare case where player bytes buy player
    # correctness rather than editor furniture. Owner: set to fit; scratch build.
    # 148,413 = 148,138 + 275 B: v213 pressure extraction. PRESSURE_MIN and its
    # curve existed once per surface; both now route through lib/pressure.js,
    # which is loaded by the two EDITOR templates only (0 hits in the player
    # template). The player pays only for the delegating branch inside
    # pressureSize(), which it never calls — the same editor-wiring-in-a-shared-
    # file shape noted at the eraser raise. Owner: set to fit; scratch build.
    # 148,787 = 148,413 + 374 B: v213 shift-to-constrain. lib/constrain.js is
    # editor-only (0 hits in the player template); the player carries the guarded
    # branches inside continueDraw/snapStrokeToFinal, which it never reaches
    # because it never draws. Third raise in this arc from editor-only work
    # living in app.js — the running total since v212 is ~1,667 B, and carving
    # the draw path into an editor bundle is now the obvious way to repay it
    # rather than raising a fourth time. Owner: set to fit; scratch build.
    # 149,641 = 151,978 - 2,337 B. A RATCHET THAT WENT DOWN.
    #
    # The shape tool's preview/commit helpers and its kind picker were added to
    # app.js and cost the PLAYER 3,191 B for a tool it can never select — the
    # largest editor-only addition to the shared file since v212, bigger than
    # the five before it combined, leaving 1,622 B of headroom. They now live in
    # editor_shapes.js, the third carve after editor_music.js and
    # editor_photo.js, and the player keeps three guarded call sites instead of
    # the implementation.
    #
    # It does not undo the whole 3,191: app.js still carries the branches and
    # the hook checks. It DOES turn a 1,622 B headroom into 3,959 B, which is
    # the difference between "the next feature does not fit" and "it does".
    #
    # The lesson worth keeping is the ordering. Building the feature in the
    # shared file and carving afterwards cost a ratchet raise and this second
    # pass; the draw path was already the obvious third carve before the shape
    # tool was written. Carve first when the target is a tool the player has no
    # use for.
    # 151,010 = 149,641 + 1,369 B: v213 preview speed. Unlike the shape tool,
    # this one CANNOT be carved the way editor_shapes.js was: the rate is read
    # by editorReplayFrame() and by startWebAudioLoop(), both of which live in
    # app.js because the player shares the audio path. Carving it would mean
    # splitting the replay loop itself, which is a bigger change than the
    # feature. The seg wiring did go to editor_shapes.js.
    # Headroom to target after this: 2,590 B. Owner: set to fit; scratch build.
    # 145,125 = 151,712 - 6,587 B. THE SECOND RATCHET THAT WENT DOWN, and by
    # far the larger: the whole stroke CAPTURE path now lives in editor_draw.js
    # (startDraw, continueDraw, snapStrokeToFinal, commitActiveStroke,
    # commitStrokeWithMirrors, endDraw, and the canvas and window listeners
    # that drive them).
    #
    # The player loads app.js to REPLAY a finished drawing; it never captures
    # one, so it had been carrying every byte of that path. drawLine(),
    # drawDot(), getPos(), pressureSize(), _eraserSize() and _brushWidth() stay
    # behind, because replayTimelineToCanvas hands drawLine/drawDot to the
    # player as its painters — only the gesture-to-points code moved.
    #
    # Headroom to target: 1,888 -> 8,475 B. Done BEFORE selection rather than
    # after, which is the lesson from the shape tool: building in the shared
    # file and carving afterwards cost a raise and a second pass.
    # 145,320 = 145,125 + 195 B: v213 selection. THE CARVE PAYING FOR ITSELF —
    # the entire tool (marquee, hit-testing, move, undo) cost the player 195 B,
    # against 3,191 B for the shape tool built the other way round. All of it
    # lives in editor_draw.js and lib/selection.js, both editor-only; app.js
    # gained only setTool's select branch and the selection-clearing call.
    # Headroom to target: 8,280 B.
    # 145,465 = 145,320 + 145 B: v213 pinch reveals the zoom HUD. beginPinch()
    # and the _skriblRevealZoomHud hook are in app.js because ZoomView and the
    # HUD are shared with the player's own pan/zoom. Small, and it buys the
    # magnify button being hidden on skinny phones without stranding a
    # pinch-zoomed user with no Fit. Headroom to target: 8,135 B.
    # 145,669 = 145,465 + 204 B of SERVED, COMMENT-STRIPPED JavaScript, which is
    # what this ratchet measures: len(r.body()) over the .js responses the player
    # actually fetches, after skribl/jsstrip.py removes comments at serve time,
    # before gzip. Not source bytes and not wire bytes — this project has had
    # all three in play at once, so an unlabelled byte figure is a future
    # ambiguity. Source cost here is larger; the gzip figure is smaller and is
    # only ever quoted as "downloaded".
    #
    # v214 touchcancel cleanup. The Loop Detail pan
    # and the scrub drag are in app.js and the player shares both, so it pays
    # for cleanup it also benefits from — a cancelled scrub on the player would
    # have left playback frozen with the listener live. Headroom: 7,931 B.
    # 145,920 = 145,669 + 251 B of SERVED, COMMENT-STRIPPED JavaScript: v214
    # loadSkribl generation token. The player CALLS loadSkribl for every shared
    # link, so it pays for this and benefits from it — a viewer opening a second
    # Skribl before the first finished decoding had the same overwrite.
    # Headroom: 7,680 B.
    # 150,945 = 145,920 + 5,025 B: v219. RAISED ON THE OWNER'S INSTRUCTION, and
    # the weakest entry in this log — recorded as such rather than dressed up.
    #
    # Every raise above names the feature that bought it and argues why the
    # PLAYER pays. This one cannot, and the reason is itself the finding: v219
    # was built without a harness run, so no raise was logged as each change
    # landed. The 5,025 B is the accumulated cost of a whole release measured in
    # one lump — correctness and layout work, the leave guard, the magnify
    # restore, the tool-pill fix — and the per-feature attribution that every
    # earlier line has is gone for good. That is the concrete price of building
    # without running, and it is worth more here as a warning than as a number.
    #
    # Still inside the 153,600 target. Headroom after this: 2,655 B — the
    # tightest this project has been, and roughly one feature from the target it
    # has been told repeatedly not to treat as reachable by extraction.
    #
    # CARVE CANDIDATE, MEASURED, FOR WHOEVER NEEDS HEADROOM NEXT: the Pad leave
    # guard (flipBtn/leaveSheet/leaveGo wiring, app.js ~5,430-5,490) is ~4,021 B
    # of source and is strictly editor-only — the player's template has no
    # #flipBtn and no #leaveSheet, so it downloads and parses all of it to run
    # none of it. It did not go into editor_draw.js here because carving under a
    # failing ratchet mid-release is how v132 happened: the carve is a real
    # change and wants its own run, not a scramble to make a number go green.
    #
    # AND IT MAY DELETE ITSELF. DESIGN-DIRECTION.md's second item is durable
    # drafts, after which Pad's guard should be REMOVED rather than moved — it
    # exists only because localStorage cannot hold media bytes. A session that
    # lands IndexedDB and then deletes this block should find the ratchet back
    # under 147,000 without carving anything.
    # 151,845 = 150,945 + 900 B of SERVED, COMMENT-STRIPPED JavaScript: v220
    # pointer identity. THE PLAYER PAYS AND THE PLAYER BENEFITS — the scrub is a
    # player control, and it read `e.touches[0]`, which is the first contact on
    # the SCREEN rather than the one on the track. A viewer holding the phone
    # with a thumb touching the glass scrubbed to wherever the thumb was.
    #
    # The 900 B is code, not prose: jsstrip removes comments from the response,
    # so the ~3,480 B of raw growth in app.js costs the player nothing. What it
    # buys, measured:
    #   eventPoint()          one helper replacing the positional read at 5 sites
    #                         in app.js and 5 more in the editor-only files
    #   _pinchPair()          the pinch owns its two contacts BY IDENTIFIER, so a
    #                         third finger cannot take a slot mid-gesture
    #   targetTouches guards  beginPinch/pressureSize/getPos read the element's
    #                         own contacts rather than the screen's
    #
    # The defect this closes, reproduced in-harness before the fix and pinned by
    # counterexample after it: with a thumb resting off-canvas, a Pad stroke drew
    # at x=56 (the thumb) instead of x=201 (the drawing finger). Reverting getPos
    # alone reproduces x=56, so both halves are load-bearing. DESIGN-DIRECTION.md
    # calls this the first promise a drawing app makes.
    #
    # Headroom after this: 1,755 B. Tighter still, and the carve candidate below
    # is unchanged and now the obvious next move for whoever needs room.
    # 151,845 -> 153,000 for lib/audiosession.js (~1,293 B served). THE COST IS
    # REAL AND THE HEADROOM IS NOW SMALL: 600 B to the target, down from 1,755.
    # Spent because without it a shared link's music is SILENT on any iPhone
    # with the ringer switch off — iOS routes Web Audio into a session that
    # switch mutes and leaves <audio> alone. A player nobody can hear is worse
    # than a player 1.2 KB larger, and the target is still met.
    #
    # The module was 1,650 B first, building its silent clip byte by byte; that
    # read better and this ratchet is not the place to pay 360 B for legibility,
    # so it carries a base64 constant instead.
    #
    # 153,000 -> 150,000 = A THIRD RATCHET THAT WENT DOWN, by 3,305 measured B,
    # and the sequence that produced it is the argument for the discipline.
    #
    # An external review of v277 said 600 B was not meaningful headroom
    # "particularly while the audio-session behavior still needs lifecycle
    # work". Its other finding WAS that lifecycle work: the /s player claimed
    # the iOS session on the play/pause tap before the branch deciding which it
    # was, and released it nowhere. Fixing that took the player to 153,251 B —
    # 251 over this ratchet — so the prediction and its proof landed inside one
    # change. The review also said not to solve it by raising the target.
    #
    # Repaid from initMoreTools(), now editor_tools.js: the "More" drawer and
    # its six tool controls, every branch guarded on an element or a lib the
    # player template does not load, so the player parsed ~4.9 KB of source to
    # run nothing at all. Behaviour-preserving for the player by construction
    # rather than by an argument about reachability — none of the six libs is in
    # skribl_player.html, so every branch was already false.
    #
    # Pinned just above the new floor, as every raise here has been: 149,946
    # measured, 150,000 set, 3,654 B to target. The lesson is the one the shape
    # tool's carve already recorded and this release had to learn twice — carve
    # first when the target is furniture the player has no use for.
    #
    # 150,000 -> 152,000 for lib/scrubkeys.js (1,489 B) and app.js's two call
    # sites (+559 B). An accessibility audit of v278 found the shared player's
    # progress bar was a bare div with mousedown/touchstart: a link sent to a
    # stranger could not be seeked by keyboard at all, and Pad and Flip both
    # DECLARED role="slider" while supplying no tabindex, no aria-valuenow and
    # no key handler — announcing to a screen reader a control that could not
    # be focused or moved.
    #
    # This is capability, not furniture, and it is capability the /s/<id> page
    # specifically needs: it is the surface a person who did not make the
    # drawing arrives at. Shared as a lib rather than written three times, so
    # the step size and the value reporting cannot drift between surfaces.
    # 152,000 -> 151,000 in v281: dropping lib/photofit.js, which the player
    # loads and cannot reach, took JS from 151,994 to 150,839. The old ratchet
    # had six bytes of headroom and was the reason given for keeping new work
    # off this surface; the constraint was partly dead weight.
    #
    # 151,000 -> 152,100 for PER-PAGE DRAW, measured at 152,054 B and pinned
    # just above it so the next addition has to argue for itself. What the
    # bytes bought: lib/holdtiming.js gained the millisecond model a page that
    # draws itself requires — a stroke timeline is not a whole number of fps
    # slots at any frame rate, so the cumulative table could no longer be
    # denominated in them — and app.js gained the reveal path that honours it,
    # which is what makes a shared link show the drawing draw.
    #
    # WHAT WAS SPENT BEFORE ASKING, because v281's note on the embed ratchet is
    # right that a raise taken without argument is a saving banked as slack:
    # the slot-denominated half of holdtiming.js (table/units/durationMs/
    # indexAt/slotMs) was DELETED rather than kept beside the new one, and
    # app.js's inline fallback deliberately does not reimplement the reveal —
    # without the lib a drawing page plays as a still one, which is exactly
    # what this player did before the field existed. Those two took the cost
    # from +2,535 B to +1,215 B. What remains is the feature itself.
    #
    # 152,100 -> 152,300, measured 152,220, and this one buys no feature at
    # all: it corrects the one above. Per-page draw shipped with the reveal
    # arithmetic — progress in, stroke count out — written separately on each
    # surface that renders it, and the copies disagreed at the ends of the
    # range. lib/holdtiming.js now owns that as dueCount(), which is the same
    # module and the same reason it already owns how long a page lasts.
    #
    # Spent before asking, on this surface: app.js's copy was DELETED, not
    # left beside the module's, so the player gives back 168 B of the module's
    # 334 and the net is 166. The fallback rule is unchanged and still costs
    # nothing — without the lib a drawing page plays as a still one rather
    # than reimplementing the reveal here.
    #
    # 152,300 -> 152,900, measured 152,794, and like the one above it corrects
    # rather than adds. dueCount() and pageMs() were each right and could not,
    # composed with indexAtMs(), ever produce a drawing page's final state: the
    # clock left the page at exactly the instant its progress would have
    # reached 1. lib/holdtiming.js gains displayAt() (331 B) and this player
    # routes its flip loop through it (243 B).
    #
    # The scrub path deliberately does NOT: a drag asks for a page and must get
    # that page, so it keeps the direct call it already had. That is the whole
    # of the surface's share — no second copy of the guard, and the fallback
    # rule is untouched and still free.
    #
    # 152,900 -> 153,000, measured 152,969, v290: +81 B in app.js so the error
    # panel knows WHICH failure it is showing. A missing Skribl answers 404 now
    # (v287 audit SK-BUG-005) and "Try again" is withheld for it — a reload
    # cannot make a missing Skribl appear — while a network failure keeps it.
    # The previous tree sat 12 B under the ceiling, so there was nothing on
    # this surface to spend first that was not a comment.
    #
    # 153,000 -> 150,500, measured 149,960, v294: THE RATCHET WENT DOWN AGAIN,
    # by 3,389 measured B, after v294, 5 had pushed it OVER (153,349) with the
    # load-based photo re-apply — code the player never runs, in the file it
    # downloads. The whole re-add block (that re-apply, and the pending cards'
    # Re-add / Dismiss buttons) is editor_draft.js's now. Lowered to the
    # measurement plus a 540 B allowance, the same margin the ceiling has
    # always carried, so the next editor-only addition to app.js is caught
    # rather than absorbed.
    # 150,500 -> 150,600, measured 150,517, v297: lib/strokelayers.js gains
    # uniformRun, the rule that a see-through run of one colour and one width is
    # drawn as a SINGLE canvas path rather than a dot plus a line per segment.
    # Per segment it composites against itself wherever the round caps overlap,
    # and a Motion Smear ghost written at alpha 46/255 painted at 83.
    #
    # That raise noted that this surface was PAYING for the rule without
    # spending it — app.js did not call uniformRun, so the sealed player still
    # beaded a smear — and said the change would cost more than 17 B and should
    # argue for itself. Here it is, arguing.
    #
    # 150,600 -> 151,500, measured 151,376, v297: app.js's paintStrokesStatic
    # walks runs and draws a uniform see-through one as a single path, and
    # makeStrokeCompositor gains pathFn to lay that run onto the dry layer in
    # order. Measured on this surface: a ghost written at alpha 46/255 painted
    # at 83 before, 46 after, on BOTH settings of the stroke-layers flag —
    # which is the branch that mattered, the compositor being on by default.
    # paintStrokesStatic is where the player renders a Flip document's frames,
    # so this is what a share link has been showing.
    #
    # Spent before asking, twice over. At the previous raise uniformRun was
    # compacted three times (-36 B measured). Here app.js carries NO inline
    # fallback for it (-296 B measured): that is this file's own precedent for
    # this very module — the overBudget call beside it treats an absent lib as
    # "not over budget" rather than keeping a second copy — so without the lib
    # a run simply paints the way it did before. The prose lives in
    # lib/strokelayers.js and flip.js; jsstrip means comments here are free
    # anyway, which the previous raise recorded after believing otherwise.
    #
    # 151,500 -> 153,800, measured 153,227, v302: uniformAlpha, and the wet-layer
    # route for the runs it identifies. uniformRun above asks "can this be ONE
    # path?" -- one colour, one width. Compositing asks something narrower: "is
    # there ONE alpha?" A smudge writes per-point colour AND size, so a generated
    # ghost fails the first question while still passing the second, falls to the
    # per-segment walk, and compounds at its own translucent round caps.
    #
    # Measured in Flip on a smeared ring after a 60-step smudge, one run written
    # at alpha 0.0314 where a single path paints 8:
    #
    #     midpoint between vertices   11.2    1.4x
    #     at the vertices             15.1    1.9x, a 35% ripple
    #     after the change             8.0    1.0x, ripple 0%
    #
    # The ripple sits at the ghost's own point spacing, which is what makes it a
    # visible mesh rather than a haze. THIS SURFACE HAS THE SAME DEFECT AND IT IS
    # THE ONE STRANGERS SEE: paintStrokesStatic is where a share link renders a
    # Flip document, parseStrokeAlpha reads rgba() and not hex-8 by the same
    # deliberate asymmetry, and a fix only the author can see is half a fix.
    #
    # Compacted before asking, per this file's own precedent. The prose for
    # uniformAlpha lives in flip.js paintStatic, which is in no byte budget;
    # lib/strokelayers.js keeps seven lines and a pointer, which is what its
    # uniformRun note already says to do (-804 B measured). app.js carries no
    # inline fallback for it, as it carries none for uniformRun.
    #
    # It is still a bigger raise than the two before it (100 B and 900 B), and it
    # was put to the owner as such rather than absorbed. Pinned at the
    # measurement plus the same 540 B allowance the ceiling has always carried,
    # so the next addition argues for itself as this one did.
    # RAISED 153,800 -> 154,000 for the full screen wiring, measured 153,911
    # (app.js 136,279 -> 136,510). The TARGET stays 153,800: this is a ratchet
    # moving to admit a control the surface was missing, not a target being
    # given up on, and the two numbers disagreeing is the honest record of
    # that. The player's JS budget is the tightest in the tree and the next
    # person to spend it should have to argue as well.
    # RAISED 154,000 -> 154,800 for the viewer's speed control, measured
    # 154,535 (app.js 136,510 -> 137,134). The TARGET stays 153,800, for the
    # same reason the line above gives: a ratchet moving to admit a control is
    # not a target being abandoned, and the two numbers disagreeing is the
    # honest record.
    #
    # Owner: "on players (across surfaces) should there be a speed control for
    # PAD? it sometimes draws too fast or slow and I'd like to control that".
    #
    # SPENT AGAINST FIRST, as this ceiling's own precedent requires, and the
    # spending is most of why the number is not larger. Nothing was invented:
    # `replayRate`, `REPLAY_RATES` and `setReplayRate` have been in app.js
    # since the Pad's preview row, and its comment there is what makes reuse
    # correct rather than convenient -- speed describes the act of LOOKING and
    # never the work, so it is not in the payload and serializeSkribl() has a
    # pin saying so. A viewer watching at half speed is making the same kind of
    # choice as an author reviewing a draft at double, which is why they share
    # one number and one stored preference.
    #
    # What the 535 B actually buys: segElapsed() (the clock, scaled in one
    # place so the flip hold table, the stroke timeline and the progress
    # fraction all keep working without knowing a rate exists), the
    # re-anchoring on a mid-play change, one playbackRate line so the music
    # keeps up, and the button's own label. The first draft cost 633 B; the
    # three-way title sentence went to one string before this number moved.
    #
    # The PAGE's own HTML paid the other half of this feature and paid it
    # DOWN -- see HTML_RATCHET below, where two full-width link rows came out
    # of the layout and three controls went into the transport for a net 233 B.
    # RAISED 154,800 -> 155,300 so full screen HAS a transport, measured
    # 155,197 (app.js 137,371 -> 137,796). The TARGET stays 153,800, for the
    # reason the first raise gives: this is a ratchet admitting a control the
    # surface was missing, not a target being let go.
    #
    # WHAT WAS MISSING. Full screen renders only the top-layer subtree, and the
    # transport is in .player-shell BELOW the wrapper that goes full screen --
    # so a person who pressed the control got a drawing, a close button, and no
    # way to pause, scrub, loop or change speed. The owner photographed it.
    #
    # SPENT AGAINST FIRST, as this ceiling's precedent requires. Nothing was
    # duplicated: a second transport rendered into the wrapper would be a
    # second set of controls, a second set of handlers and a second thing to
    # keep in step with the player -- which is the mistake lib/fullbar.js
    # exists on the other two surfaces to avoid. The row is MOVED, so there is
    # one of every control and every listener stays bound to it. The layout
    # cost nothing at all: #playerBar is `display: contents` at rest.
    #
    # What the 397 B buys: the move and the move back to a remembered anchor
    # (.player-shell is meta, bar, call-to-action, brand -- appending would put
    # the transport under the brand line), the band the sheet reserves so the
    # bar stands below the drawing rather than on it, and that band coming off
    # the fit scale so the centring and the scale agree. The band is read back
    # from the custom property rather than measured twice, which is where the
    # first draft's extra 43 B went.
    #
    # The nib's mapping is in this number too and is a FIX, not a feature: it
    # measured the wrapper on the premise that layoutPlayerCanvas sizes it to
    # the fitted rect, which full screen makes false, so the bead rode across
    # the screen nowhere near its own line.
    BYTES_RATCHET, BYTES_TARGET = 155_300, 153_800
    # Re-pinned 9,000 -> 10,500 at v269, deliberately: the brand became the
    # one-stroke skribl signature, INLINE in the page (~1.4KB of paths + a
    # ~0.9KB nonce'd draw-on script). Inline is load-bearing, not laziness —
    # stroke=currentColor (theme ink) and the dash-draw animation are both
    # impossible through an <img>. Still a ratchet: pinned just above the new
    # floor so the next kilobyte has to argue for itself like this one did.
    # (Template was 56,716 B before the editor shell came out.)
    # Re-pinned 10,500 -> 10,800 at v272: the signature is now inked with the
    # accent gradient, and the <linearGradient> defs ride in the same inline
    # svg for the same reason the paths do (~140 B measured; a url(#) stroke
    # cannot reference styles an <img> would strip). Same discipline: just
    # above the new floor of 10,640.
    # 10,800 -> 10,900 for one <script> tag: lib/audiosession.js, without which
    # this page is silent on a silent-mode iPhone. See the JS ratchet above.
    # 10,900 -> 11,000 for one <script> tag: lib/scrubkeys.js, without which
    # this page cannot be seeked from a keyboard. Same reasoning as the JS
    # ratchet above.
    # 11,000 -> 10,900: one fewer <script> tag, 10,946 -> 10,872.
    # 10,900 -> 11,200 at v288 for the inline theme boot (_skribl_theme_boot.html,
    # ~270 B): an embedding host passes ?theme=light and the attribute has to
    # land before first paint or the frame flashes dark — the same no-flash
    # rule verify_theme pins for the editors. Just above the new floor of 11,171.
    # 11,200 -> 11,300 at v292: the boot resolves "system" through
    # prefers-color-scheme before first paint (~150 B, a storage that throws
    # falling through to the OS included), so a bare page follows the OS
    # without a flash. Measured 11,327.
    # 11,400 -> 11,500 for the canvas's accessible name (SK-AUD-004): role=img
    # and an aria-label carrying the post's title, server-rendered because
    # app.js is on the JS ratchet and its reachable lines sit at their ceiling.
    # ~90 B; the player's one canvas was the only thing on the page with no
    # name. Measured 11,418 against the old ceiling of 11,400.
    # 11,500 -> 12,000 for the app's identity (SK-AUD-013): a manifest link,
    # a theme-color meta carrying both grounds, an icon and a touch icon
    # (_skribl_app_identity.html, ~360 B) and the boot's re-stamp of that
    # meta for a light page (~80 B). Without them a shared link added to a
    # Home Screen wore a screenshot for an icon. Measured 11,859.
    # RAISED 12,000 -> 12,750 FOR FULL SCREEN, measured 12,647: the transport
    # button (409 B) and the exit control inside the fullscreened subtree
    # (238 B), which is not optional -- see below.
    #
    # Owner, holding the copied link beside the profile stage: "shouldn't there
    # be a full screen on this player too? why do the players not share the
    # same functions?" The stage has had full screen since v304 and /s/<id> --
    # the page a person actually SENDS somebody -- did not. The two players are
    # separate implementations for a real reason (this one is the editor's
    # engine; the in-post one is built to a host's byte budget), but that is an
    # argument about CODE, not about which buttons a viewer gets, and nothing
    # made the canonical share surface the poorer of the two on purpose.
    #
    # 409 B of button and glyph on a page whose whole HTML is 12 KB. The glyph
    # is the stage's, character for character, so the two surfaces stay
    # recognisably one product rather than two takes on the same idea.
    #
    # THE EXIT CONTROL IS NOT DECORATION. Only the fullscreened subtree
    # renders, so the transport row -- including the button that got you there
    # -- is off screen, and without an exit inside that subtree the only way
    # out is Escape: a key not every device has and not every person knows.
    # The harness found this rather than review: the assertion that leaves
    # full screen timed out clicking a button that was no longer on screen.
    #
    # RAISED 12,750 -> 13,050 for the transport the owner asked for, measured
    # 12,983. Two things landed and one thing left:
    #
    #   + a speed button (the viewer's rate; see BYTES_RATCHET above)
    #   + Copy link and Gallery, as 46px buttons IN the transport row
    #   - the two full-width `.player-link` ROWS they used to be, and the
    #     `.player-link` rules in styles.css with them (the CSS budget went
    #     DOWN, and it is the same feature paying)
    #
    # Owner: "maybe we could enlarge the drawing to the biggest it can be for
    # whatever screen it's on by putting LINK as icon in the play row and
    # putting an icon for Gallery somewhere to free up space... it would be
    # cool if the drawing or flip was the showcase instead of all the stuff
    # (rows) on the bottom taking up so much space". On a 390px phone those
    # two rows were most of what sat below the drawing.
    #
    # SPENT AGAINST FIRST: the gallery glyph was four stroked `<rect>`s with
    # rounded corners in the first draft and is one filled `<path>` now, which
    # is 100 B of the 233 this is actually asking for. A raise this small for
    # three controls is only possible because two rows of markup left.
    HTML_RATCHET = 13_050

    present = pg.evaluate(
        "(names) => names.filter(n => typeof window[n] !== 'undefined')",
        EDITOR_GLOBALS)
    check(f"editor globals on the player do not exceed {GLOBALS_RATCHET} "
          f"(target {GLOBALS_TARGET})",
          len(present) <= GLOBALS_RATCHET,
          f"{len(present)} reachable: " + ", ".join(present))

    in_dom = pg.evaluate("""(ids) => ids.filter(i => document.getElementById(i))""",
                         EDITOR_DOM)
    check(f"authoring controls in the player's document do not exceed "
          f"{DOM_RATCHET} (target {DOM_TARGET})",
          len(in_dom) <= DOM_RATCHET,
          f"{len(in_dom)} present, downloaded and parsed though never painted: "
          + ", ".join(in_dom))

    # HTML counts too. The template shed 31,530 bytes when the overlays and
    # authoring controls came out — markup every visitor used to download — and a
    # JS-only measurement could not see any of it, while the ~700 bytes of
    # guards that MADE the removal safe showed up as a regression. Measuring one
    # half of the payload rewards moving weight across the boundary rather than
    # removing it.
    total_html = sum(html_bytes.values())
    check(f"the player's HTML does not grow past {HTML_RATCHET:,} bytes",
          total_html and total_html <= HTML_RATCHET,
          f"{total_html:,} bytes (was 56,716 before the editor shell came out)")

    total_js = sum(js_bytes.values())
    check(f"the player's JavaScript does not grow past {BYTES_RATCHET:,} bytes "
          f"(target {BYTES_TARGET:,})",
          total_js <= BYTES_RATCHET,
          f"{total_js:,} bytes over {len(js_bytes)} files; largest: "
          + ", ".join(f"{k} {v:,}" for k, v in
                      sorted(js_bytes.items(), key=lambda kv: -kv[1])[:3]))

    # The carve, asserted directly rather than only through the byte count. A
    # byte ratchet notices the SIZE coming back; this notices the CODE coming
    # back, which is the thing that matters and which a later raise would hide.
    _player_js = (ROOT / "skribl" / "templates" / "skribl" / "skribl_player.html").read_text(encoding="utf-8")
    # v273: this named FOUR carves in a hardcoded tuple while NINE editor_*.js
    # files existed, so editor_draft, editor_export, editor_menu, editor_post and
    # editor_tune could each have drifted back onto the player with nothing to
    # catch it — and a tenth carve would have been unguarded on the day it landed.
    # The list is read off disk instead, so the assertion covers whatever exists.
    _carves = sorted(p.name for p in (ROOT / "skribl" / "static").glob("editor_*.js"))
    _leaked = [c for c in _carves if c in _player_js]
    check(f"the player loads none of the {len(_carves)} editor-only files "
          "(the carves stay carved)",
          not _leaked,
          ("LEAKED: " + ", ".join(_leaked)) if _leaked
          else ", ".join(c[:-3] for c in _carves) + " all absent")
    _app_js = (ROOT / "skribl" / "static" / "app.js").read_text(encoding="utf-8")
    check("...and the stroke CAPTURE path has not drifted back into app.js, "
          "which the player does load",
          "function startDraw(" not in _app_js and "function endDraw(" not in _app_js,
          "startDraw/endDraw live in editor_draw.js")

    # CSS. SUPERSEDED WORDING, kept because the ratchet below still carries its
    # numbers: this used to read "the player links the WHOLE of styles.css — the
    # editor's drawers, export sheet, help panel and page bar included", and that
    # stopped being true when player.css was generated. The player links
    # player.css alone (skribl_player.html says so at the link tag), a derived
    # strict subset produced by harness/tools/cssgraph.py. What remains true is
    # the reason the measurement is here at all: none of it was measured once,
    # and it grew unnoticed while the JS came down.
    #
    # The ratchet is set at today's value, which is the POST-regression one.
    # That is deliberate and it is not an accommodation: 123,283 is where the
    # tree is, and a ratchet's job is to stop the next 3,439 bytes, not to
    # relitigate the last. The DEBT is the number beside it — 119,844 was the
    # v194 size, and getting back under it is the first repayment. The target is
    # what a player-only stylesheet would plausibly cost; like BYTES_TARGET it
    # is the honest distance, not the next cut.
    CSS_RATCHET, CSS_WAS, CSS_TARGET = 123_283, 119_844, 40_000
    total_css = sum(css_bytes.values())
    check(f"the player's CSS does not grow past {CSS_RATCHET:,} bytes "
          f"(was {CSS_WAS:,} at v194; target {CSS_TARGET:,})",
          total_css and total_css <= CSS_RATCHET,
          f"{total_css:,} bytes over {len(css_bytes)} files: "
          + ", ".join(f"{k} {v:,}" for k, v in
                      sorted(css_bytes.items(), key=lambda kv: -kv[1])))

    # The number this project quotes as "what a visitor downloads" has been
    # JS + HTML. It is short by every byte of the line above.
    _wire = sum(v for k, v in wire_bytes.items()
                if k.endswith((".js", ".css")) or "text/html" in k)
    check("the whole player payload is accounted for, not two thirds of it",
          bool(total_css and total_js and total_html),
          f"source: JS {total_js:,} + HTML {total_html:,} + CSS {total_css:,} = "
          f"{total_js + total_html + total_css:,} B; on the wire (gzip) "
          f"{_wire:,} B — quote the second only as 'downloaded', never as "
          f"'the player's JavaScript'")

    # ------------------------------------------------------------------
    # FULL SCREEN ON THE SHARED LINK, and the parity question behind it.
    #
    # Owner: "shouldn't there be a full screen on this player too? why do the
    # players not share the same functions?" The profile stage has had it since
    # v304; /s/<id>, the page somebody is actually SENT, had not.
    #
    # DRIVEN, NOT READ. The markup being present proves nothing -- the control
    # is hidden until app.js confirms the API exists, so a button that renders
    # and does nothing would satisfy any assertion about the DOM. Headless
    # Chromium does honour requestFullscreen from a click (checked before this
    # was written), so the state is asserted from document.fullscreenElement.
    _EXIT_VISIBILITY = """() => {
        const e = document.getElementById('playerFullExit');
        if (!e) return 'ABSENT';
        const r = e.getBoundingClientRect();
        return (r.width > 0 && r.height > 0) ? 'VISIBLE' : 'HIDDEN';
    }"""
    print("\nFULL SCREEN — the link people share has the control the stage has")
    _fp = b.new_page(viewport={"width": 1200, "height": 900})
    _fp.goto(link, wait_until="load")
    _fp.wait_for_timeout(1200)

    _api = _fp.evaluate("() => !!document.fullscreenEnabled")
    check("precondition: this browser offers the Fullscreen API at all",
          _api, "without it the control is correctly hidden and the rows below "
                "would be asserting the wrong thing")
    _shown = _fp.evaluate("() => { const b = document.getElementById('playerFullBtn');"
                          " return b ? !b.hidden : 'NO BUTTON'; }")
    check("the player offers a full screen control when the API is there",
          _shown is True, str(_shown))

    # THE ARM THAT WAS MISSING, and its absence shipped. The exit control is
    # asserted VISIBLE inside full screen further down; nothing checked it is
    # INVISIBLE outside it, so `.full-exit` tying with `.player-btn` on
    # specificity -- and losing, because .player-btn comes 185 lines later in
    # the sheet -- put a close button on the player at all times. The owner saw
    # it before any assertion did. One arm of a two-state control is not a pin.
    _exit_at_rest = _fp.evaluate(_EXIT_VISIBILITY)
    check("...and the way OUT of full screen is not on screen until you are in it",
          _exit_at_rest == "HIDDEN",
          f"{_exit_at_rest} — a close control on a page with nothing to close "
          f"is what a specificity tie with .player-btn produced")
    _NIB_ON_INK_SRC = """() => {
            const c = document.querySelector('.canvas-wrap > canvas');
            const n = document.querySelector('.player-nib');
            if (!c || !n || n.hidden) return { missing: true };
            const cr = c.getBoundingClientRect(), nr = n.getBoundingClientRect();
            const cx = nr.left + nr.width / 2, cy = nr.top + nr.height / 2;
            const inside = cx >= cr.left && cx <= cr.right
                        && cy >= cr.top && cy <= cr.bottom;
            const out = { inside: inside, nib: Math.round(nr.width),
                          canvas: [Math.round(cr.width), Math.round(cr.height)] };
            if (!inside) return out;
            const bx = Math.round((cx - cr.left) / cr.width * c.width);
            const by = Math.round((cy - cr.top) / cr.height * c.height);
            const r = Math.max(4, Math.round(c.width / cr.width * 5));
            const x0 = Math.max(0, bx - r), y0 = Math.max(0, by - r);
            const w = Math.min(c.width - x0, r * 2), h = Math.min(c.height - y0, r * 2);
            let best = 0;
            try {
              const d = c.getContext('2d').getImageData(x0, y0, w, h).data;
              for (let i = 0; i < d.length; i += 4) {
                const v = Math.min(d[i], d[i + 1], d[i + 2]) * (d[i + 3] / 255);
                if (v > best) best = v;
              }
            } catch (e) { out.err = String(e); return out; }
            out.ink = Math.round(best);
            return out; }"""

    _rest = _fp.evaluate("""
        () => { const c = document.querySelector('.canvas-wrap > canvas');
                if (!c) return {w: 0, h: 0};
                const r = c.getBoundingClientRect();
                return {w: Math.round(r.width), h: Math.round(r.height)}; }""")
    _rest_w, _rest_h = _rest["w"], _rest["h"]
    check("precondition: the canvas has a measurable size in the page",
          _rest_w > 0 and _rest_h > 0,
          f"{_rest} — the growth assertion below needs a size to grow from")
    # THE NIB AT REST, AND THAT IT IS ON ITS LINE HERE TOO. Both arms of the
    # full-screen pair below need this one: the size, to say full screen's is
    # bigger, and the ink, to say the probe can tell a nib that is on its
    # stroke from one that is not. Without the second arm the row in full
    # screen could go red for a probe that never finds ink anywhere.
    _fp.evaluate("() => { const b = document.getElementById('playerPlayBtn');"
                 " if (b) b.click(); }")
    _fp.wait_for_timeout(900)
    _NIB_REST_STATE = _fp.evaluate(_NIB_ON_INK_SRC)
    _NIB_REST = _NIB_REST_STATE.get("nib") or 0
    check("the nib rides its stroke in the page, at the page's scale",
          _NIB_REST_STATE.get("inside") and _NIB_REST_STATE.get("ink", 0) > 120
          and _NIB_REST > 0,
          f"{_NIB_REST_STATE} — the known-good arm: if this cannot find ink "
          f"under a correctly placed nib, the full-screen row below is "
          f"measuring the probe and not the player")
    _fp.evaluate("() => { const b = document.getElementById('playerPlayBtn');"
                 " if (b) b.click(); }")
    _fp.wait_for_timeout(200)
    if _shown is True:
        _fp.click("#playerFullBtn")
        _fp.wait_for_timeout(700)
        _on = _fp.evaluate("""() => ({
            wrap: document.fullscreenElement === document.querySelector('.canvas-wrap'),
            pressed: document.getElementById('playerFullBtn').getAttribute('aria-pressed'),
            label: document.getElementById('playerFullBtn').getAttribute('aria-label')})""")
        check("...and pressing it puts the DRAWING full screen, not the page",
              _on["wrap"],
              f"{_on} — the canvas wrapper is the element that should fill the "
              f"screen; fullscreening the document would bring the chrome too")
        check("...and the control says so, for a screen reader too",
              _on["pressed"] == "true" and _on["label"] == "Leave full screen",
              str(_on))
        # THE EXIT IS ASSERTED BEFORE IT IS USED, because a missing one must
        # FAIL and not CRASH. Clicking it straight away made the suite die on a
        # 30s Playwright timeout with no summary at all -- a mutation that
        # removes the control could then be read as a broken harness rather
        # than as the defect it is. Asking whether it is on screen first turns
        # that into one named red line.
        _exit_seen = _fp.evaluate(_EXIT_VISIBILITY)
        check("...and a way OUT is on screen while full screen, not just Escape",
              _exit_seen == "VISIBLE",
              f"{_exit_seen} — only the fullscreened subtree renders, so the "
              f"transport row is gone; without a control inside it the only "
              f"exit is a key some devices do not have")

        # AND THE DRAWING IS ACTUALLY BIGGER, which is the entire point and is
        # the arm the first version of this block did not have. Every assertion
        # above passes on a player whose canvas stays exactly the size it had in
        # the page: the wrapper fills the screen (the UA's `:fullscreen` rule
        # sets width/height to 100% with !important), the exit control appears,
        # aria-pressed flips -- and the drawing sits at its page size in the
        # middle of a black field. layoutPlayerCanvas() measured `.app`, whose
        # max-width is 720px, and capped the scale at 1:1; it runs again on
        # fullscreenchange, so its INLINE width beat the stylesheet's
        # `.canvas-wrap:fullscreen > canvas { width: auto }` every time and that
        # rule never applied at all.
        #
        # MEASURED AGAINST THE AT-REST SIZE rather than a constant: the
        # fixture's authored shape and the viewport decide the number, and the
        # defect's signature is precisely "the same width as at rest".
        _sz = _fp.evaluate("""
            () => { const c = document.querySelector('.canvas-wrap > canvas');
                    const w = document.querySelector('.canvas-wrap');
                    if (!c || !w) return {w: 0, h: 0, vw: 0, vh: 0, ww: 0, wh: 0};
                    const r = c.getBoundingClientRect(), q = w.getBoundingClientRect();
                    const d = document.documentElement;
                    return {w: Math.round(r.width), h: Math.round(r.height),
                            ww: Math.round(q.width), wh: Math.round(q.height),
                            vw: d.clientWidth, vh: d.clientHeight,
                            iw: window.innerWidth, ih: window.innerHeight}; }""")
        # MEASURED AGAINST clientWidth/clientHeight, NOT innerWidth. The first
        # version of this row used window.innerWidth and read 1180 against
        # 1200: innerWidth counts the scrollbar of the document still laid out
        # behind the top layer, and the fullscreen element's containing block
        # does not. 20px of nothing. The same mistake was live one line below,
        # where the scale branch divided by innerWidth; it measures the
        # wrapper's own box now, which is what layoutEditorCanvas does too.
        #
        # THE WRAPPER FIRST, because it is the element that went fullscreen and
        # because the rows below are about the drawing inside it. Measured
        # rather than assumed: the Fullscreen spec's UA stylesheet sizes the
        # top-layer element with `width: 100% !important`, which outranks both
        # styles.css's `.canvas-wrap:fullscreen { width: 100vw }` and the
        # inline width layoutPlayerCanvas writes. Those declarations therefore
        # say what the UA already says; they are kept as belt and braces for an
        # engine that does not apply the spec'd rule, and this row is what
        # would notice if no layer supplied it.
        check("...and the wrapper that went full screen IS the screen",
              _sz["ww"] >= _sz["vw"] - 2 and _sz["wh"] >= _sz["vh"] - 2,
              f"wrapper {_sz['ww']}x{_sz['wh']} in a {_sz['vw']}x{_sz['vh']} "
              f"screen (innerWidth {_sz['iw']}) — the element in the top "
              f"layer has to fill it before anything inside it can")
        check("...and the drawing FILLS the screen rather than staying page-sized",
              _rest_w and _sz["w"] >= _rest_w * 1.25,
              f"full screen {_sz['w']}x{_sz['h']} in a {_sz['vw']}x{_sz['vh']} "
              f"screen, against {_rest_w}x{_rest_h} in the page — a canvas that "
              f"does not grow is a black border, not a full screen")
        check("...and it keeps the authored shape while it does",
              bool(_rest_w) and bool(_sz["h"])
              and abs((_sz["w"] / _sz["h"]) - (_rest_w / _rest_h)) < 0.02,
              f"{_sz['w']}x{_sz['h']} against the authored "
              f"{_rest_w}x{_rest_h} — filling the screen by stretching is the "
              f"v305 in-post defect reappearing on another surface")

        # ---- AND THERE IS SOMETHING TO PRESS ---------------------------
        #
        # Only the top-layer subtree renders. The transport lives in
        # .player-shell, BELOW the wrapper that goes full screen, so pressing
        # the control gave a drawing, a close button and nothing else -- which
        # is what the owner photographed. #playerBar is moved into the wrapper
        # on the way in and back on the way out.
        #
        # ASKED AS WHAT IS PAINTED. Every one of these controls exists in the
        # document at all times and has a perfectly good rect whether or not it
        # is in the rendered subtree; `elementFromPoint` at the middle of the
        # play button is the only form of the question that a control outside
        # the top layer fails.
        _bar = _fp.evaluate("""() => {
            const w = document.querySelector('.canvas-wrap');
            const b = document.getElementById('playerBar');
            const c = document.querySelector('.canvas-wrap > canvas');
            if (!w || !b || !c) return { missing: true };
            const play = document.getElementById('playerPlayBtn');
            const br = b.getBoundingClientRect(), cr = c.getBoundingClientRect();
            const pr = play.getBoundingClientRect();
            const hit = document.elementFromPoint(pr.left + pr.width / 2,
                                                  pr.top + pr.height / 2);
            const shown = id => { const e = document.getElementById(id);
                                  return e ? getComputedStyle(e).display : 'absent'; };
            return { inWrap: w.contains(b),
                     painted: !!(hit && play.contains(hit)),
                     barH: Math.round(br.height),
                     band: Math.round(parseFloat(getComputedStyle(w).paddingBottom) || 0),
                     overlap: Math.round(Math.max(0, cr.bottom - br.top)),
                     copy: shown('playerCopyBtn'), gallery: shown('playerGalleryLink') }; }""")
        check("...and the transport came with it, painted and pressable",
              not _bar.get("missing") and _bar["inWrap"] and _bar["painted"],
              f"{_bar} \u2014 a control outside the fullscreened subtree keeps its "
              f"rect and loses its pixels, so this asks what is under the "
              f"pointer rather than where the box is")
        check("...standing below the drawing rather than on it",
              not _bar.get("missing") and _bar["barH"] > 20
              and _bar["overlap"] == 0 and abs(_bar["band"] - _bar["barH"]) <= 1,
              f"{_bar} \u2014 the bar is absolute and the drawing does not know it "
              f"is there; the wrapper reserves the measured height, and the fit "
              f"scale subtracts the same number so the two cannot disagree")
        check("...and the two ways OFF this drawing stand down while it fills the screen",
              not _bar.get("missing") and _bar["copy"] == "none"
              and _bar["gallery"] == "none",
              f"{_bar} \u2014 Copy link and Gallery both take a person somewhere "
              f"else, which is the one thing full screen is not for")

        # ---- THE NIB RIDES ITS OWN LINE --------------------------------
        #
        # showNibAtIndex measured canvasWrap, on the premise stated above it
        # that layoutPlayerCanvas sizes the wrapper to the fitted display rect.
        # True on the page. False here: the Fullscreen UA sheet forces the
        # top-layer element to `width: 100% !important`, so the wrapper is the
        # whole screen and the canvas is centred inside it -- the bead was
        # scaled by the screen's width over the drawing's and placed from the
        # screen's corner, and rode hundreds of pixels from its own stroke.
        #
        # ASKED OF THE PIXELS UNDER IT, not of its coordinates. A rect says
        # where a box is; whether the nib is ON the line is a question only the
        # bitmap can answer, and the bitmap is what a person is looking at.
        # The fixture draws white on a dark ground, so "is there ink here" is a
        # brightness sample in a small neighbourhood -- small enough that being
        # a nib's width off still fails it.
        _fp.evaluate("() => { const b = document.getElementById('playerPlayBtn');"
                     " if (b) b.click(); }")
        _fp.wait_for_timeout(900)
        _nib_fs = _fp.evaluate(_NIB_ON_INK_SRC)
        check("...and the nib is drawn ON the stroke it is leading",
              not _nib_fs.get("missing") and _nib_fs["inside"]
              and _nib_fs.get("ink", 0) > 120,
              f"{_nib_fs} \u2014 the bead is placed from the wrapper's corner and "
              f"scaled by its width; in full screen the wrapper is the screen "
              f"and the canvas is centred in it, so both were wrong at once")
        check("...and it is a size in the DRAWING, not a size on the screen",
              not _nib_fs.get("missing") and _nib_fs["nib"] > _NIB_REST + 2,
              f"full screen {_nib_fs.get('nib')}px against {_NIB_REST}px in the "
              f"page \u2014 fixed at 14px it was the one element whose whole job "
              f"is to say how big a pen is and which did not answer to how big "
              f"the drawing is")

        # EXITED THROUGH THAT CONTROL, and
        # getting here took two wrong turns worth recording. Escape first:
        # that is handled by the BROWSER's fullscreen chrome, which a headless
        # run does not have, so the page never saw it. Then the transport
        # button again -- which TIMED OUT, and the timeout was the product
        # telling the truth: only the fullscreened subtree renders, so the
        # whole control row, including the button that got you here, is off
        # screen. There was no way out but a key. That is what #playerFullExit
        # is for, and this line is what would have caught its absence.
        if _exit_seen == "VISIBLE":
            _fp.click("#playerFullExit")
        else:                      # fall back so the REST of the run survives
            _fp.evaluate("() => document.exitFullscreen && document.exitFullscreen()")
        _fp.wait_for_timeout(700)
        _off = _fp.evaluate("""() => ({
            fs: !!document.fullscreenElement,
            pressed: document.getElementById('playerFullBtn').getAttribute('aria-pressed')})""")
        check("...and leaving it returns the control to its resting state",
              not _off["fs"] and _off["pressed"] == "false", str(_off))
    _fp.close()

    # THE EDITOR RUNS THIS PLAYER TOO, and it does not have the way out.
    #
    # _skribl_player_controls.html is included by skribl_editor.html as well as
    # by skribl_player.html — byte-identical, no `kind` branch — so the full
    # screen button added in v306 appeared on BOTH. #playerFullExit is not in
    # that partial: it has to sit inside `.canvas-wrap`, which the partial is
    # not part of, so it is written into skribl_player.html alone. The editor
    # page runs initPlayer() for the `#skribl=<id>` local fallback that
    # editor_post.js hands back when posting to the server fails, and on that
    # page full screen would have had no control inside the fullscreened
    # subtree at all — the trap #playerFullExit exists to close, re-opened on
    # the surface nobody thought to look at.
    #
    # DRIVEN ON THE EDITOR PAGE, through the fallback's own mechanism: the post
    # this suite authored is written to localStorage under the key the hash
    # player reads, and the page is loaded at that hash. Reading the template
    # for the absence would prove nothing about what the page offers.
    _hp = b.new_page(viewport={"width": 1000, "height": 800})
    browsing.goto(_hp, BASE, "/")
    _pid = link.rstrip("/").rsplit("/", 1)[-1]
    _stored = _hp.evaluate("""
        async (id) => {
            const r = await fetch('/api/skribls/' + encodeURIComponent(id));
            if (!r.ok) return 'HTTP ' + r.status;
            localStorage.setItem('skribl_post_' + id, JSON.stringify(await r.json()));
            return 'ok'; }""", _pid)
    check("fixture: the posted Skribl is on this device for the hash player",
          _stored == "ok",
          f"{_stored} — without it the page below is a bare editor and the "
          f"assertion would pass for the wrong reason")
    _hp.goto(BASE + "/#skribl=" + _pid, wait_until="load")
    _hp.reload(wait_until="load")      # a hash-only navigation re-runs nothing
    _hp.wait_for_timeout(1800)
    _hash = _hp.evaluate("""
        () => { const sh = document.getElementById('playerShell');
                const b = document.getElementById('playerFullBtn');
                return {booted: !!(sh && !sh.hidden),
                        exit: !!document.getElementById('playerFullExit'),
                        offered: !!(b && !b.hidden)}; }""")
    check("precondition: the editor page's local hash player actually booted",
          _hash["booted"],
          f"{_hash} — a player that never started offers no controls either, "
          f"which would make the row below vacuous")
    check("precondition: and that page has no exit control inside the canvas",
          _hash["booted"] and not _hash["exit"],
          f"{_hash} — if the editor ever gains #playerFullExit this row is "
          f"measuring the wrong page and the gate below should be revisited")
    check("...so it does not offer a full screen there is no way back from",
          _hash["booted"] and not _hash["offered"],
          f"{_hash} — only the fullscreened subtree renders, so with no exit "
          f"control inside it the transport row is gone and the only way out "
          f"is a key some devices do not have")
    _hp.close()

    # THE PARITY CLAIM ITSELF, keyed by (surface, control). The two players are
    # separate implementations on purpose, so nothing but a check like this
    # stops one of them quietly gaining a control the other never gets -- which
    # is exactly how full screen came to exist on the stage alone.
    _stage_html = (ROOT / "skribl" / "templates" / "skribl" / "skribl_library.html").read_text(encoding="utf-8")
    _player_html = (ROOT / "skribl" / "templates" / "skribl"
                    / "_skribl_player_controls.html").read_text(encoding="utf-8")
    _pairs = [("stage", 'id="btnFull"', _stage_html),
              ("player", 'id="playerFullBtn"', _player_html)]
    _missing = [surface for surface, token, html in _pairs if token not in html]
    check("both playback surfaces carry a full screen control",
          not _missing,
          f"missing on: {_missing or 'neither'} — the stage and the shared link "
          f"are one product to the person using them")

    # ---- THE DRAWING IS THE SHOWCASE (v308) -------------------------------
    # Owner: "it would be cool if the drawing or flip was the showcase instead
    # of all the stuff (rows) on the bottom taking up so much space". Copy link
    # and Gallery were two FULL-WIDTH rows under the transport; on a phone they
    # were most of what sat below the drawing. Both are buttons in the
    # transport row now.
    #
    # THREE ASSERTIONS, AND THE CALIBRATION SAYS WHICH ONE IS THE PIN. Putting
    # the two link rows back reddens the two STRUCTURAL rows below and leaves
    # the ratio green: chrome went 259 -> 330 against a 370px drawing, so the
    # drawing still had more room and the ratio could not tell. The ratio is
    # therefore a FLOOR on the achievement -- it goes red when the chrome grows
    # past the drawing, whatever causes that -- and not the pin on this change.
    # Both are worth having and it is worth saying which is which, because a
    # comment claiming the ratio catches this would be a claim the mutation
    # test had already contradicted.
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.wait_for_timeout(400)
    _room = pg.evaluate("""() => {
        const shell = document.getElementById('playerShell');
        const row = document.querySelector('.player-controls');
        const cv = document.querySelector('.player-stage canvas, .player-canvas, canvas');
        if (!shell || !row || !cv) return { missing: !shell ? 'shell' : (!row ? 'row' : 'canvas') };
        const sr = shell.getBoundingClientRect(), cr = cv.getBoundingClientRect();
        const inRow = (id) => {
          const el = document.getElementById(id);
          return !!(el && row.contains(el));
        };
        return { drawing: Math.round(cr.height), chrome: Math.round(sr.height),
                 copyInRow: inRow('playerCopyBtn'),
                 galleryInRow: inRow('playerGalleryLink'),
                 rateInRow: inRow('playerRateBtn'),
                 leftoverLinks: document.querySelectorAll('.player-link').length }; }""")
    check("Copy link, Gallery and Speed are all IN the transport row",
          not _room.get("missing") and _room["copyInRow"] and _room["galleryInRow"]
          and _room["rateInRow"], str(_room))
    check("...and nothing is left of the two full-width rows they were",
          not _room.get("missing") and _room["leftoverLinks"] == 0,
          f"{_room} — a surviving .player-link is a row still taking the width")
    check("on a phone the drawing gets more room than the chrome under it",
          not _room.get("missing") and _room["drawing"] > _room["chrome"],
          f"drawing {_room.get('drawing')}px against {_room.get('chrome')}px of "
          f"player shell — the drawing is what the page is for")
    pg.set_viewport_size({"width": 1200, "height": 900})
    pg.wait_for_timeout(300)

    # ---- THE VIEWER'S SPEED (v308) ----------------------------------------
    # Owner: "on players (across surfaces) should there be a speed control for
    # PAD? it sometimes draws too fast or slow and I'd like to control that".
    _cycle = []
    for _ in range(4):
        _cycle.append(pg.evaluate(
            "() => document.getElementById('playerRateBtn').textContent.trim()"))
        pg.evaluate("() => document.getElementById('playerRateBtn').click()")
        pg.wait_for_timeout(120)
    check("the speed button cycles 1x, 2x, half, and comes back",
          _cycle == ["1×", "2×", "½×", "1×"],
          f"{_cycle} — a control whose label does not follow its own state "
          f"is a control nobody can read")

    # IT SCALES THE CLOCK, AND THAT IS MEASURED BY PLAYING. A label that
    # changes and a replay that does not is exactly the bug this is for, and
    # nothing about the button's own state can see the difference. Same wall
    # time, twice the rate, so materially more of the drawing should be done.
    def _progress_after(rate, ms=1400):
        pg.evaluate("() => { const b = document.getElementById('playerRestartBtn');"
                    " if (b) b.click(); }")
        pg.wait_for_timeout(200)
        pg.evaluate("() => { const p = document.getElementById('playerPlayBtn');"
                    " if (p && p.getAttribute('aria-label') === 'Pause') p.click(); }")
        for _ in range(4):
            now = pg.evaluate(
                "() => document.getElementById('playerRateBtn').textContent.trim()")
            if now == rate:
                break
            pg.evaluate("() => document.getElementById('playerRateBtn').click()")
            pg.wait_for_timeout(80)
        pg.evaluate("() => document.getElementById('playerRestartBtn').click()")
        pg.wait_for_timeout(ms)
        out = pg.evaluate(
            "() => parseFloat(document.getElementById('playerProgressFill').style.width) || 0")
        pg.evaluate("() => { const p = document.getElementById('playerPlayBtn');"
                    " if (p && p.getAttribute('aria-label') === 'Pause') p.click(); }")
        return out

    _at1 = _progress_after("1×")
    _at2 = _progress_after("2×")
    _athalf = _progress_after("½×")
    check("2x really does play the drawing faster, not just say so",
          _at1 > 1 and _at2 > _at1 * 1.5,
          f"after the same wall time: 1x reached {_at1:.1f}%, 2x reached "
          f"{_at2:.1f}% — a label that changes over an unchanged clock is "
          f"the whole defect this control could have shipped with")
    check("...and half speed really is slower",
          _at1 > 1 and _athalf < _at1 * 0.75,
          f"1x reached {_at1:.1f}%, half reached {_athalf:.1f}%")
    # Restore, so nothing downstream inherits a rate through localStorage.
    for _ in range(4):
        if pg.evaluate("() => document.getElementById('playerRateBtn').textContent.trim()") == "1\u00d7":
            break
        pg.evaluate("() => document.getElementById('playerRateBtn').click()")
        pg.wait_for_timeout(80)

    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for ok, _ in results if ok)
print(f"{passed}/{len(results)} passed")
if passed != len(results):
    print("FAILED: " + "; ".join(n for ok, n in results if not ok))
sys.exit(0 if passed == len(results) else 1)
