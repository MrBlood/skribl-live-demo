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


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# Editor-only globals. Every one of these was CONFIRMED PRESENT on a real player
# page before this suite was written — a list of plausible names would prove
# nothing, since an absent-but-never-there symbol passes for free.
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
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(900)
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
    link = pg.evaluate("""() => {
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
    BYTES_RATCHET, BYTES_TARGET = 151_845, 153_600
    HTML_RATCHET = 9_000                    # template was 56,716 B before this session

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
    check("the player does not load any of the four editor-only files "
          "(the carves stay carved)",
          all(f"{_n}.js" not in _player_js for _n in
              ("editor_draw", "editor_shapes", "editor_music", "editor_photo")),
          "editor_draw / editor_shapes / editor_music / editor_photo all absent")
    _app_js = (ROOT / "skribl" / "static" / "app.js").read_text(encoding="utf-8")
    check("...and the stroke CAPTURE path has not drifted back into app.js, "
          "which the player does load",
          "function startDraw(" not in _app_js and "function endDraw(" not in _app_js,
          "startDraw/endDraw live in editor_draw.js")

    # CSS. The player links the WHOLE of styles.css — the editor's drawers,
    # export sheet, help panel and page bar included — and none of it was ever
    # measured here, which is why it grew unnoticed while the JS came down.
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

    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for ok, _ in results if ok)
print(f"{passed}/{len(results)} passed")
if passed != len(results):
    print("FAILED: " + "; ".join(n for ok, n in results if not ok))
sys.exit(0 if passed == len(results) else 1)
