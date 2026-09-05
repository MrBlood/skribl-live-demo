"""The iOS playback session: lib/audiosession.js, and the gaps it fills.

THE BUG. On iOS, Web Audio is routed into an "ambient" audio session that the
hardware ringer switch silences; an <audio> element is not. So on a phone set to
silent, Test Seam (a plain <audio>) plays while Preview Loop (Web Audio) does
not — and neither does a posted Skribl's music in a feed, because
inlineplayer.js is Web Audio too. Found by the owner on their own phone.

WHY EVERY EXISTING GUARD MISSED IT, and this is the part worth keeping: app.js
has an elaborate hand-off for a context that never unlocks, and every one of its
tests is `state !== 'running'`. In silent mode the context reaches 'running'
perfectly well and is merely inaudible, so all the guards pass, the native
<audio> fallback is deliberately suppressed, and the result is confident
silence. app.js's own warning — "A source object existing is NOT the same as
audible playback" — applies one level further out than where it was written.

CONFIRMED ON THE DEVICE, 5 Sep 2026. The owner reported "Music works" from the
same iPhone that found the bug, in silent mode. That is the evidence; what
follows is why this file is still not.

WHAT THIS SUITE CAN AND CANNOT DO, stated plainly because the distinction is the
whole point, and the confirmation above does not change it. Chromium on Linux
has no ringer switch and no iOS audio session. These assertions pin the
MECHANISM — one element, silent, looping, playsinline, playing, idempotent,
released, loaded on every surface that makes sound. They CANNOT pin the OUTCOME,
which is whether an iPhone in silent mode is audible. app.js already says the
same of its own iOS branches: "Desktop never showed it … including in the
harness." The phone is the test. A green run here is evidence the mechanism is
still wired up — it is what protects the confirmed fix from being refactored
away — and it is not, and never becomes, evidence that the fix works.

Section 4 closes a different gap: verify_audiostate drives Preview Loop under a
HUNG unlock and asserts the fallback plumbing, but nothing anywhere asserted
that preview produces sound at all. That is why a silent preview could be
reported by a person rather than by a suite.
"""
import math
import os
import pathlib
import struct
import sys
import wave

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions ran. This is NOT evidence the audio session works.")
    raise SystemExit(77)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


RATE = 44100


def wav_bytes(sec, rate=RATE):
    n = int(sec * rate)
    fr = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate)))
                  for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(fr)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(fr)) + fr)


AUD = wav_bytes(4.0)

# Pretend to be an iPhone. The module gates on platform because the Control
# Center side effect is pure cost anywhere without a ringer switch; this is how
# the gated path gets exercised at all on Linux.
AS_IPHONE = """
Object.defineProperty(navigator, 'platform', { get: () => 'iPhone' });
"""


# ---- a posted Skribl carrying music, to drive the SHARED player -------------
# Section 5 needs a real /s/<id> page: the release edges live in app.js's player
# scope and there is no way to reach them from a page that has no post behind
# it. Copied from verify_inline.py rather than shared, for the reason v278
# recorded when a shared helper went wrong — a fixture is not surface-agnostic
# just because two suites happen to want one, and this one wants a LONGER
# drawing than that file's so section 5 can watch a loop run for six seconds
# without the drawing ending underneath it.
LOOP_WAV = "/tmp/audiosession_loop.wav"
with wave.open(LOOP_WAV, "wb") as _w:
    _w.setnchannels(2)
    _w.setsampwidth(2)
    _w.setframerate(RATE)
    _b = bytearray()
    for _i in range(6 * RATE):
        _v = int(18000 * math.sin(2 * math.pi * 220 * _i / RATE))
        _b += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_b))

POST_PUBLIC = """async (title) => {
  const p = serializeSkribl();
  p.title = title;
  p.visibility = 'public';
  const r = await fetch(window.SKRIBL_API_BASE, {
    method: 'POST', headers: skriblPostHeaders(), body: JSON.stringify(p) });
  if (!r.ok) return { error: r.status + ' ' + (await r.text()).slice(0, 200) };
  return await r.json();
}"""


def scribble(pg, box, n=110):
    """Draw over about three seconds of WALL CLOCK.

    Strokes carry timestamps, so a drawing made as fast as the mouse moves
    replays in under a second — over before Play/Pause can be observed at all.
    """
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        a = (i / n) * math.pi * 4
        r = 20 + (i / n) * 110
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r)
        pg.wait_for_timeout(25)
    pg.mouse.up()


def post_one(b, title, music=True):
    """Record a drawing in Pad and post it PUBLICLY. Returns (id, errors)."""
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
    if music:
        pg.set_input_files("#musicInput", LOOP_WAV)
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

# The analyser tap from verify_player_isolation, so section 4 measures SOUND
# rather than the absence of an error.
TAP = """
(() => {
  const Orig = window.AudioContext || window.webkitAudioContext;
  function Tapped() {
    const ctx = new Orig();
    window.__ctx = ctx;
    const an = ctx.createAnalyser(); an.fftSize = 2048; an.connect(ctx.destination);
    window.__an = an;
    const ob = ctx.createBufferSource.bind(ctx);
    ctx.createBufferSource = function () {
      const n = ob(); const oc = n.connect.bind(n);
      n.connect = function (d) { try { oc(an); } catch (e) {} return oc(d); };
      return n;
    };
    return ctx;
  }
  Tapped.prototype = Orig.prototype;
  window.AudioContext = Tapped; window.webkitAudioContext = Tapped;
})();
"""

PEAK = """() => { if (!window.__an) return -1;
  const b = new Uint8Array(window.__an.frequencyBinCount);
  window.__an.getByteTimeDomainData(b);
  let p = 0; for (const v of b) p = Math.max(p, Math.abs(v - 128)); return p; }"""

print("\n1 — THE MODULE SHIPS WHEREVER SOUND DOES")
TPL = ROOT / "skribl" / "templates" / "skribl"
for name, why in [("skribl_editor.html", "Pad's Preview Loop is Web Audio"),
                  ("skribl_flip.html", "Flip's Preview Loop is Web Audio"),
                  ("skribl_player.html", "a shared link's music is Web Audio"),
                  ("_skribl_inline_player.html", "a feed post's music is Web Audio")]:
    src = (TPL / name).read_text(encoding="utf-8")
    check(f"{name} loads lib/audiosession.js — {why}",
          "lib/audiosession.js" in src)

src = (ROOT / "skribl" / "static" / "lib" / "audiosession.js").read_text(encoding="utf-8")
check("the module says it cannot be verified here",
      "harness" in src.lower() and "phone is the test" in src.lower(),
      "a fix nobody can check must say so where it lives")

print("\n2 — CLAIMED ON A GESTURE, NEVER ON LOAD")
# Claiming at load would hold an iOS media session for anyone who merely opened
# a page. Every call site must be inside a handler.
for f, fn in [("app.js", None), ("flip.js", None), ("inlineplayer.js", None)]:
    js = (ROOT / "skribl" / "static" / f).read_text(encoding="utf-8")
    calls = js.count("SkriblAudioSession.claim()")
    check(f"{f} claims the session", calls >= 1, f"{calls} call(s)")
inline = (ROOT / "skribl" / "static" / "inlineplayer.js").read_text(encoding="utf-8")
check("the in-post player claims on the UNMUTE path, not at mount",
      "setSoundOn" in inline
      and inline.index("SkriblAudioSession") > inline.index("function setSoundOn"),
      "claiming at mount would hold a media session for every feed visitor")

with sync_playwright() as p:
    b = p.chromium.launch()

    print("\n3 — THE MECHANISM, IN A BROWSER PRETENDING TO BE AN IPHONE")
    pg = b.new_page(viewport={"width": 390, "height": 840})
    pg.add_init_script(AS_IPHONE)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(1500)
    check("the module loaded and knows it is on iOS",
          pg.evaluate("() => !!window.SkriblAudioSession && window.SkriblAudioSession._isIOS()"))
    check("nothing is held before anything asks for sound",
          pg.evaluate("() => window.SkriblAudioSession.active()") is False
          and pg.evaluate("() => window.SkriblAudioSession._element()") is None,
          "a session held at load would show Skribl as playing media to every visitor")

    st = pg.evaluate("""() => { window.SkriblAudioSession.claim();
        const el = window.SkriblAudioSession._element();
        return { active: window.SkriblAudioSession.active(),
                 tag: el && el.tagName, loop: el && el.loop,
                 inline: el ? el.hasAttribute('playsinline') : null,
                 count: document.querySelectorAll('audio[playsinline]').length,
                 src: el ? el.src.slice(0, 22) : null }; }""")
    check("claim() creates one looping, playsinline <audio>",
          st["tag"] == "AUDIO" and st["loop"] is True and st["inline"] is True,
          str(st))
    # A CONSTANT, NOT A BUILDER. The byte-by-byte builder read better and cost
    # 1,650 B served against ~450 for this; the /s/<id> player's JS ratchet is
    # not the place to spend 1,200 B on legibility.
    check("...from a silent data URI, the cheap form on the byte ratchets",
          st["src"].startswith("data:audio/wav"), str(st["src"]))
    check("...and it is held", st["active"] is True)
    pg.evaluate("() => { window.SkriblAudioSession.claim(); window.SkriblAudioSession.claim(); }")
    n = pg.evaluate("() => document.querySelectorAll('audio[playsinline]').length")
    check("claim() is idempotent — a second tap must not stack a second element",
          n == 1, f"{n} elements; a stacked one would play on forever after release()")
    silent = pg.evaluate("""() => new Promise(res => {
        const el = window.SkriblAudioSession._element();
        fetch(el.src).then(r => r.arrayBuffer()).then(buf => {
          const b = new Uint8Array(buf).slice(44);
          let loud = 0; for (const v of b) if (Math.abs(v - 128) > 1) loud++;
          res({ bytes: b.length, loud: loud }); }); })""")
    check("the held clip is actually silent", silent["loud"] == 0,
          f"{silent['loud']} non-silent of {silent['bytes']} samples")
    check("release() stops holding it",
          pg.evaluate("""() => { window.SkriblAudioSession.release();
              const el = window.SkriblAudioSession._element();
              return window.SkriblAudioSession.active() === false && el.paused; }"""))
    check("no page errors from the session module", not errs, "; ".join(errs[:2]))
    pg.close()

    print("\n4 — AND PREVIEW LOOP ACTUALLY MAKES A SOUND")
    # The gap that let this be reported by a person: verify_audiostate drives
    # preview under a hung unlock and asserts the plumbing; nothing asserted
    # that sound comes out on the ordinary path.
    for path, opener, label in [("/", "#musicOpenBtn", "Pad"), ("/flip", "#musicBtn", "Flip")]:
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.add_init_script(TAP)
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1200)
        pg.evaluate(f"() => {{ const x = document.querySelector('{opener}'); if (x) x.click(); }}")
        pg.wait_for_timeout(400)
        pg.set_input_files("#musicInput",
                           {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
        pg.wait_for_timeout(3000)
        pg.click("#previewLoopBtn")
        peak = 0
        for _ in range(12):
            pg.wait_for_timeout(200)
            peak = max(peak, pg.evaluate(PEAK))
        check(f"{label}: Preview Loop puts signal on the audio graph",
              peak > 5, f"analyser peak {peak}")
        check(f"{label}: and claiming the session did not break it",
              pg.inner_text("#previewLoopBtn").strip() == "Stop Preview")
        pg.close()

    print("\n5 — AND IT IS RELEASED WHEN NOTHING WANTS SOUND ANY MORE")
    # THE FINDING THIS SECTION EXISTS FOR, from an external review of v277.
    # Claiming was correct and releasing was not: the /s player claimed on the
    # play/pause tap BEFORE the branch that decides which of the two it is, so
    # a Pause tap claimed the session on its way to stopping the audio — and no
    # path released it at all. The first Play held an iOS media session until
    # the tab closed.
    #
    # WHY NOTHING CAUGHT IT, and it is the same shape as the bug this whole
    # module exists for. The failure is not silence. Sound works perfectly;
    # what is wrong is a Control Center and lock-screen entry claiming Skribl
    # is playing when it is not, which no assertion about audibility can see.
    # Section 3 pinned claim/release as an API and section 4 pinned that sound
    # comes out. Neither asked WHEN the session is let go, so both stayed green.
    #
    # active() is the observable here, and it is only worth reading because
    # claim() no longer sets it optimistically and leaves it — see the last
    # assertions in this section.
    pid, perrs = post_one(b, "session lifecycle", music=True)
    if not pid:
        check("posted a Skribl carrying music to drive the shared player",
              False, "; ".join(perrs[:2]))
    else:
        pg = b.new_page(viewport={"width": 390, "height": 840})
        pg.add_init_script(AS_IPHONE)
        pg.goto(f"{BASE}/s/{pid}", wait_until="load")
        pg.wait_for_timeout(2500)
        held = "() => window.SkriblAudioSession.active()"

        check("the shared player holds nothing before you press Play",
              pg.evaluate(held) is False,
              "opening a link is not asking for sound")

        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(700)
        check("Play claims the session", pg.evaluate(held) is True)

        # The regression itself: the tap that STOPS sound used to claim.
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(500)
        check("Pause releases it", pg.evaluate(held) is False,
              "a paused player holding a media session is a lock-screen entry "
              "for audio that is not playing, and the viewer cannot clear it")

        # Mute is the other edge that stops wanting sound.
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(600)
        pg.click("#playerMuteBtn")
        pg.wait_for_timeout(400)
        check("Mute releases it while still playing", pg.evaluate(held) is False)
        pg.click("#playerMuteBtn")
        pg.wait_for_timeout(400)
        check("...and unmuting takes it back", pg.evaluate(held) is True)

        # Natural completion with the loop OFF. The fixture is a few seconds of
        # drawing, so this waits for the player's own end rather than guessing.
        pg.evaluate("() => { const l = document.getElementById('playerLoopBtn');"
                    " if (l && l.classList.contains('active')) l.click(); }")
        pg.evaluate("() => { const r = document.getElementById('playerRestartBtn');"
                    " if (r) r.click(); }")
        ended = False
        for _ in range(40):
            pg.wait_for_timeout(500)
            if pg.evaluate("() => { const b = document.getElementById('playerPlayBtn');"
                           " return b ? b.getAttribute('aria-label') : null; }") == "Play":
                ended = True
                break
        check("the drawing reached its end with the loop off", ended,
              "the rest of this assertion cannot mean anything without it")
        if ended:
            check("natural completion releases it", pg.evaluate(held) is False,
                  "playback is over and the session is still held")

        # A LOOP RESTART MUST NOT DROP AND RETAKE IT. Releasing on the last
        # frame and reclaiming on the next lap would flicker the Control Center
        # entry once per pass, which is why onEnded() only syncs when it is NOT
        # about to restart.
        pg.evaluate("() => { const l = document.getElementById('playerLoopBtn');"
                    " if (l && !l.classList.contains('active')) l.click(); }")
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(600)
        drops = pg.evaluate("""() => new Promise(res => {
            let seen = 0;
            const t = setInterval(() => {
              if (!window.SkriblAudioSession.active()) seen++;
            }, 100);
            setTimeout(() => { clearInterval(t); res(seen); }, 6000); })""")
        check("a looping player holds the session continuously across laps",
              drops == 0,
              f"released {drops} time(s) mid-loop — a tear-down and reacquire "
              "every pass")
        pg.close()

    print("\n6 — active() MEANS HELD, NOT ATTEMPTED")
    # claim() used to set its flag synchronously after a fire-and-forget play().
    # play() settles asynchronously, so on a rejection the module reported a
    # session it had never been granted, and — because claim() returned early
    # on that flag — no later gesture would ever retry. Also found in the v277
    # review. The fix is two lines: clear the flag when play() rejects, and
    # re-play an element that exists but is paused.
    pg = b.new_page(viewport={"width": 390, "height": 840})
    pg.add_init_script(AS_IPHONE)
    # Reject every play() BEFORE the module loads, so the first claim is the
    # rejected one.
    pg.add_init_script("""
      HTMLMediaElement.prototype.play = function () {
        return Promise.reject(new DOMException('blocked', 'NotAllowedError'));
      };
    """)
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(1200)
    rejected = pg.evaluate("""() => new Promise(res => {
        window.SkriblAudioSession.claim();
        setTimeout(() => res(window.SkriblAudioSession.active()), 300); })""")
    check("a rejected play() leaves the session NOT held",
          rejected is False,
          "active() would be reporting an attempt rather than a session, and "
          "claim()'s early return would make it permanent")
    # READ THE ELEMENT, NOT THE RETURN VALUE. claim()'s own answer passes on the
    # bug: the optimistic version left `claimed` true after the rejection, so a
    # retry early-returned true without ever calling play() again — a stale flag
    # reporting success for a session it did not have. What separates the fix
    # from the bug is whether the element is actually PLAYING afterwards.
    retried = pg.evaluate("""() => new Promise(res => {
        HTMLMediaElement.prototype.play = function () {
          this.__played = true;
          return Promise.resolve();
        };
        const ok = window.SkriblAudioSession.claim();
        setTimeout(() => {
          const el = window.SkriblAudioSession._element();
          res({ ok: ok, replayed: !!(el && el.__played),
                active: window.SkriblAudioSession.active() });
        }, 200); })""")
    check("...and the next gesture actually re-plays the element",
          retried["replayed"] is True and retried["active"] is True
          and retried["ok"] is True,
          f"{retried} — a one-off rejection must not lock the module out for "
          "the page's life, and a stale flag must not fake the recovery")
    pg.close()

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
print("\nNOTE: none of the above proves an iPhone in silent mode is audible."
      "\n      The device did: confirmed by the owner on 5 Sep 2026. This suite"
      "\n      guards the mechanism behind that confirmation, not the outcome.")
sys.exit(1 if bad else 0)
