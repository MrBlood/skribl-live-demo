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
