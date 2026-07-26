"""v102 (c) — the Pad could persist a garbage loop.

`audioEl._fileName` is set as soon as the file is picked, but `trimEnd` isn't
written until `loadedmetadata` fires. An autosave landing in that window used to
serialize {trimStart: 0, trimEnd: 0}; on re-add that hit the 0.5s minimum-loop
clamp in applyPendingMusicSettings, so a 42s track came back as a half-second
loop and the pending card read "Loop 0:00-0:00".

The race is timing-dependent, so this suite forces the window deterministically
rather than hoping to hit it: it calls the serializer directly at the moment
_fileName exists but the duration doesn't.
"""
import math, struct, wave
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
BIG = "/tmp/race42.wav"

with wave.open(BIG, "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(42 * 44100):
        _v = int(12000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

with sync_playwright() as p:
    br = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    pg.goto(BASE + "/", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load"); pg.wait_for_timeout(700)

    print("\nPAD — autosave DURING the decode window")
    # Reproduce the exact pre-decode state: a filename is attached, the duration
    # hasn't arrived, trimEnd is still its initial 0.
    state = pg.evaluate("""() => {
        audioEl = audioEl || new Audio();
        audioEl._fileName = 'race42.wav';
        audioDuration = 0; trimStart = 0; trimEnd = 0;
        const m = currentMusicMeta();
        return { meta: m, dur: audioDuration, trimEnd: trimEnd };
    }""")
    meta = state["meta"]
    check("the decode window is genuinely open", state["dur"] == 0 and state["trimEnd"] == 0,
          f"audioDuration {state['dur']}, trimEnd {state['trimEnd']}")
    check("the filename is still persisted", meta and meta.get("name") == "race42.wav",
          f"name = {meta.get('name')!r}" if meta else "meta is null")
    check("a zero-length loop is NOT written",
          not (meta.get("trimStart") == 0 and meta.get("trimEnd") == 0),
          f"trimStart={meta.get('trimStart')!r} trimEnd={meta.get('trimEnd')!r}")
    check("trim values are null, not bogus numbers",
          meta.get("trimStart") is None and meta.get("trimEnd") is None,
          f"{meta.get('trimStart')!r} / {meta.get('trimEnd')!r}")

    print("\nPAD — a null loop restores to the 20s default, not a 0.5s stub")
    restored = pg.evaluate("""() => {
        audioDuration = 42; trimStart = 0; trimEnd = Math.min(audioDuration, 20);
        applyPendingMusicSettings({ name: 'race42.wav', trimStart: null, trimEnd: null });
        return { s: trimStart, e: trimEnd };
    }""")
    check("restored loop is 20s, not the 0.5s clamp",
          abs((restored["e"] - restored["s"]) - 20) < 0.01,
          f"trim {restored['s']:.2f}–{restored['e']:.2f} = {restored['e'] - restored['s']:.2f}s")

    print("\nPAD — the card reads honestly instead of 'Loop 0:00–0:00'")
    card = pg.evaluate("""() => {
        pendingMusicMeta = { name: 'race42.wav', trimStart: null, trimEnd: null };
        const keep = audioEl; audioEl = null;
        refreshPendingCards();
        const t = document.getElementById('musicPendingMeta').textContent;
        audioEl = keep;
        return t;
    }""")
    check("no 0:00–0:00 loop on the pending card", "0:00–0:00" not in card, f"card reads {card!r}")
    check("card falls back to a plain 'Loop saved'", "Loop saved" in card, card)

    print("\nPAD — regression: a real loop still round-trips exactly")
    real = pg.evaluate("""() => {
        audioEl = audioEl || new Audio();
        audioEl._fileName = 'race42.wav';
        audioDuration = 42; trimStart = 3; trimEnd = 11; loopCrossfadeMs = 80;
        return currentMusicMeta();
    }""")
    check("a decoded loop is persisted verbatim",
          real.get("trimStart") == 3 and real.get("trimEnd") == 11 and real.get("crossfadeMs") == 80,
          f"{real.get('trimStart')}–{real.get('trimEnd')}, xfade {real.get('crossfadeMs')}")

    print("\nPAD — regression: a saved loop survives a later decode window")
    kept = pg.evaluate("""() => {
        pendingMusicMeta = { name: 'race42.wav', trimStart: 3, trimEnd: 11, crossfadeMs: 80 };
        audioEl._fileName = 'race42.wav';
        audioDuration = 0; trimStart = 0; trimEnd = 0;
        return currentMusicMeta();
    }""")
    check("an already-saved loop isn't clobbered by the null path",
          kept.get("trimStart") == 3 and kept.get("trimEnd") == 11,
          f"{kept.get('trimStart')}–{kept.get('trimEnd')}")

    print("\nPAD — end to end: real file pick, autosave hammered throughout")
    pg.reload(wait_until="load"); pg.wait_for_timeout(600)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load"); pg.wait_for_timeout(600)
    # A drawing is required or writeAutosave() clears the key instead of writing.
    # Note the resulting loop is the DRAWING's length (setLoopToDrawingLength on
    # the load path), not 20s — so the assertion below is that what landed on
    # disk matches the settled in-memory loop, which is the invariant the race
    # actually broke.
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 100, box["y"] + 100); pg.mouse.down()
    for i in range(40):
        pg.mouse.move(box["x"] + 100 + i * 4, box["y"] + 100 + math.sin(i / 3) * 30)
    pg.mouse.up()
    pg.set_input_files("#musicInput", BIG)
    # Save repeatedly across the decode window — the old code would latch a
    # zero-length loop into localStorage here.
    for _ in range(30):
        pg.evaluate("() => { try { writeAutosave(); } catch (e) {} }")
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(3000)
    pg.evaluate("() => { try { writeAutosave(); } catch (e) {} }")
    saved = pg.evaluate("""() => {
        try { const v = JSON.parse(localStorage.getItem('skribl_autosave_v1'));
              return v ? v.musicMeta : null; } catch (e) { return null; }
    }""")
    check("an autosave with music meta was written", saved is not None, str(saved))
    if saved:
        bogus = saved.get("trimStart") == 0 and saved.get("trimEnd") == 0
        check("no zero-length loop landed in localStorage", not bogus,
              f"trimStart={saved.get('trimStart')!r} trimEnd={saved.get('trimEnd')!r}")
        check("persisted loop is a real one, not a stub",
              saved.get("trimEnd") is not None and saved["trimEnd"] > 0.5,
              f"trimEnd={saved.get('trimEnd')!r}")
    live = pg.evaluate("() => ({ dur: audioDuration, s: trimStart, e: trimEnd })")
    if saved:
        check("what landed on disk matches the settled in-memory loop",
              abs(saved["trimEnd"] - live["e"]) < 0.01 and abs(saved["trimStart"] - live["s"]) < 0.01,
              f"disk {saved['trimStart']:.2f}-{saved['trimEnd']:.2f} vs live {live['s']:.2f}-{live['e']:.2f}")
    check("full duration reached (no provisional value stuck)",
          abs(live["dur"] - 42) < 0.5, f"audioDuration {live['dur']}")

    print("\nPAD — regression: the drawing-length default still applies")
    pg.reload(wait_until="load"); pg.wait_for_timeout(600)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="load"); pg.wait_for_timeout(600)
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 100, box["y"] + 100); pg.mouse.down()
    for i in range(40):
        pg.mouse.move(box["x"] + 100 + i * 4, box["y"] + 100 + math.sin(i / 3) * 30)
    pg.mouse.up()
    pg.set_input_files("#musicInput", BIG); pg.wait_for_timeout(4000)
    drawn = pg.evaluate("() => ({ s: trimStart, e: trimEnd, dur: audioDuration })")
    check("loop sized to the drawing, not the 20s default",
          0.2 < (drawn["e"] - drawn["s"]) < 19,
          f"trim {drawn['s']:.2f}–{drawn['e']:.2f} = {drawn['e'] - drawn['s']:.2f}s")
    check("and it is a real loop, not a zero-length stub",
          (drawn["e"] - drawn["s"]) > 0.5, f"{drawn['e'] - drawn['s']:.2f}s")

    check("no page errors", not errors, "; ".join(errors[:2]))
    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
