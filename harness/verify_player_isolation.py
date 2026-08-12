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

    def _record(r):
        u = r.url.split("?")[0]
        try:
            n = int(r.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            return
        if u.endswith(".js"):
            js_bytes[u.split("/")[-1]] = n
        elif "/s/" in u and "text/html" in (r.headers.get("content-type") or ""):
            html_bytes[u.split("/")[-1]] = n

    pg.on("response", _record)
    pg.goto(link, wait_until="load")
    pg.wait_for_timeout(3500)
    player = pg.evaluate(INK)

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
    GLOBALS_RATCHET, GLOBALS_TARGET = 5, 0
    DOM_RATCHET, DOM_TARGET = 0, 0          # reached: the shell is out of the player
    BYTES_RATCHET, BYTES_TARGET = 232_000, 153_600
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

    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for ok, _ in results if ok)
print(f"{passed}/{len(results)} passed")
if passed != len(results):
    print("FAILED: " + "; ".join(n for ok, n in results if not ok))
sys.exit(0 if passed == len(results) else 1)
