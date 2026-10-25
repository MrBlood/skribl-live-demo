#!/usr/bin/env python3
"""Match the beat: Flip's Beat speed (the mock, with today's speed and a
matched one playing side by side to a song, and the owner: "all yes").

With a song that has a beat, heard by Skribl or tapped, Speed in Tune is
6 · 12 · 24 · Beat. Beat makes a round of the pages last a quarter, a half,
one or two bars of the song, the one nearest the speed there was to start,
and says what that makes ("12 pages in ½ bar · 12.4 a second"). A round is
what plays before it starts again; a stretch that loops forever is its own
round, the pages before it playing once. Still pages share the round by
their holds; a page that draws itself keeps its own time. Every row is held
to the song's own beat as Skribl heard it (musicTempo), never to a number
the editor wrote down for itself.

  SHOWS WITH A BEAT. With no song, or a song with no beat (a steady tone),
  Speed is as it was; with a beat heard, or tapped with Skribl not
  listening, Beat is there beside 24.

  THE ROUND. Turned on, the round nearest the speed there was: 12 pages at
  12 a second, at 124, is half a bar (12.4 a second), to half a millisecond;
  Beat is lit and the numbers not, the hint says "on the song's beat", and
  the line under the round says what it makes. The round's choices open
  under Speed as a glide, read on every animation frame, and at once under
  Reduce Motion. A quarter, one and two bars each make a round of exactly
  that; a round these pages cannot make (48 of them in a quarter bar, over
  60 a second) is not offered. A page held twice counts twice; a page that
  draws itself keeps its own time; a page added keeps the round, at a new
  speed; a stretch looping forever is the round. 6, 12 or 24 turns Beat off
  at that speed; the song taken away puts Beat aside and the speed stays.

  KEPT. After a reload Beat is the speed, the same round and speed; the post
  carries both (the server's half: verify_sharedrules).

  ON THE BEAT. Playing, every round starts on the song's beat as heard,
  within 30ms (a frame and a little more), for sixteen seconds; on their own
  timer the same pages slid 179ms off in that time. Play from a later page
  starts the song as far into its round, so the first round lands on the
  beat too, and a pause and a resume keep them together.

On Flip only (the Pad has no pages), on a phone. FLIPBEAT_PART=show (round,
kept, beat) runs one part, for calibration. Each row was shown red by its
own break, served in place of the real file.
"""
import io
import math
import os
import struct
import sys
import wave

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence that Flip's pages keep to the beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

PART = os.environ.get("FLIPBEAT_PART", "")
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)


def part(name):
    return not PART or PART == name


def _wav(seconds, bpm=None, rate=22050):
    """A click on every beat at `bpm`, the first of each bar louder (a beat
    Skribl hears); with no bpm, a steady tone (no beat at all)."""
    n = int(seconds * rate)
    out = []
    for i in range(n):
        t = i / rate
        if bpm:
            p = 60.0 / bpm
            k = int(t / p)
            x = t - k * p
            a = (0.9 if k % 4 == 0 else 0.55) * math.exp(-x * 60)
            v = a * (math.sin(2 * math.pi * 1000 * x) + 0.6 * math.sin(2 * math.pi * 90 * x)) if x < 0.08 else 0.0
        else:
            v = 0.3 * math.sin(2 * math.pi * 220 * t)
        out.append(int(max(-1.0, min(1.0, v * 0.7)) * 32767))
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack("<%dh" % len(out), *out))
    w.close()
    return buf.getvalue()


BEAT = {"name": "clicks.wav", "mimeType": "audio/wav", "buffer": _wav(32.0, 124)}
TONE = {"name": "tone.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}

# Pages quickly, as the beat suite makes them: a short stroke on each, `n` of them.
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.05 * (k % 16)) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); frames.push(f); }
  fps = o.fps || 12; idx = 0; buildStrip(); render(); updateToolState(); scheduleSave(); }"""
LISTENED = """() => { const E = window.SkriblEars; if (!E || E.__wrapped) return; const real = E.listen; E.__wrapped = true;
  E.listen = (b, d) => real(b, (H) => { d(H); window.__earsDone = true; }); }"""
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
# Speed as it stands, and what the round makes by the timing lib's own plan.
ST = """() => { const q = (id) => document.getElementById(id), H = window.SkriblHold, p = H.plan(frames, fps, docLoop);
  return { fps, bars: beatBars, bpm: musicTempo ? musicTempo.bpm : 0, shown: !q('fpsBeat').hidden, lit: [...document.querySelectorAll('#fps button')]
      .filter((b) => b.classList.contains('on') && !b.hidden).map((b) => b.textContent),
    open: q('beatMore').classList.contains('open'), inert: q('beatMore').hasAttribute('inert'),
    hint: document.querySelector('#tuneFpsRow .tune-hint').textContent, say: q('beatSay').textContent,
    rounds: [...document.querySelectorAll('#beatRoundSeg button')].filter((b) => !b.hidden).map((b) => +b.dataset.bars),
    round: p.forever ? p.stretchMs : p.cycle, pages: frames.length }; }"""
# While it plays: each time a new page is up, which page, and where the song is as heard.
REC = """(secs) => new Promise((done) => { const out = [], t0 = performance.now(); let last = -1;
  (function tick() { const now = performance.now();
    if (playing && !playPaused && idx !== last) { last = idx;
      out.push({ t: now - t0, page: idx, heard: _waLoop.playing() ? _waLoop.elapsed() - _waLoop.latency() : null }); }
    if (now - t0 < secs * 1000) requestAnimationFrame(tick); else done(out); })(); })"""
TAPS = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'); let i = 0, t0 = null, due = 0;
  const go = () => { if (t0 != null) while (performance.now() < t0 + due) {}
    if (t0 == null) t0 = performance.now(); b.click();
    if (i >= o.gaps.length) { res(true); return; }
    due += o.gaps[i++]; setTimeout(go, Math.max(0, t0 + due - performance.now() - 15)); };
  setTimeout(go, o.lead || 0); })"""


def editor(b, *, ears=True, still=False):
    c = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", **PHONE))
    if not ears:
        c.add_init_script(NO_EARS)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, "/flip")
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    q.evaluate(LISTENED)
    return c, q, errs


def song(q, f=BEAT, listen=True):
    browsing.pad_drawer(q, "music")
    q.set_input_files("#musicInput", f)
    q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
    if listen:
        q.wait_for_function("() => !!window.__earsDone", timeout=20000)
    waits.settle(q, 500)
    browsing.pad_drawer_close(q)


def tune(q):
    if not q.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"):
        q.click("#tuneBtn")
    waits.settle(q, 600)


def untune(q):
    if q.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"):
        q.click("#tuneBtn")
    waits.settle(q, 400)


def bar(st):
    return 4 * 60000 / st["bpm"]


def words(b):
    return {0.25: "¼ bar", 0.5: "½ bar", 1: "1 bar", 2: "2 bars"}[b]


def round_starts(rec, bpm, bars, first=0):
    """How far (ms) each round's first page came up from the song's beat grid
    for that round, as heard."""
    R = bars * 4 * 60 / bpm
    out = []
    for r in rec:
        if r["page"] == first and r["heard"] is not None:
            e = r["heard"] % R
            out.append((e - R if e > R / 2 else e) * 1000)
    return out


with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    if part("show"):
        print("\nSHOWS WITH A BEAT -- heard or tapped; with none, Speed is as it was")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12})
        tune(q)
        st = q.evaluate(ST)
        check("with no song, Speed is 6 · 12 · 24 and Beat does not show",
              not st["shown"] and st["lit"] == ["12"] and st["hint"] == "pages per second", f"{st}")
        untune(q); song(q, TONE); tune(q)
        st = q.evaluate(ST)
        check("with a song Skribl hears no beat in (a steady tone), Beat does not show",
              not st["shown"] and st["bpm"] == 0, f"{st}")
        c.close()
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        st = q.evaluate(ST)
        check("with a beat Skribl heard, Beat shows beside 24",
              st["shown"] and abs(st["bpm"] - 124) < 0.1 and st["lit"] == ["12"], f"{st}")
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
        c, q, errs = editor(b, ears=False)
        q.evaluate(PAGES, {"n": 12}); song(q, listen=False)
        browsing.pad_drawer(q, "music")
        q.click("#fineTuneToggle"); waits.settle(q, 500)
        q.evaluate("() => document.getElementById('musicTapBtn').scrollIntoView({ block: 'center' })")
        q.click("#musicTapBtn")                                     # the first tap starts the loop
        q.wait_for_function("() => _waLoop.playing() && _waLoop.elapsed() > 0.3", timeout=5000)
        q.evaluate(TAPS, {"lead": 300, "gaps": [500] * 6})
        q.wait_for_timeout(2600)
        browsing.pad_drawer_close(q); tune(q)
        st = q.evaluate(ST)
        check("with a beat tapped (Skribl not listening), Beat shows too",
              st["shown"] and abs(st["bpm"] - 120) < 1, f"{st}")
        c.close()

    if part("round"):
        print("\nTHE ROUND -- whole bars of the song, nearest the speed there was")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.evaluate("() => { const el = document.getElementById('beatMore'); window.__hs = [];"
                   " (function t() { window.__hs.push(el.getBoundingClientRect().height); if (window.__hs.length < 40) requestAnimationFrame(t); })(); }")
        q.click("#fpsBeat")
        q.wait_for_timeout(900)
        hs = q.evaluate("() => window.__hs")
        st = q.evaluate(ST)
        R = bar(st) * 0.5
        check("Beat picks the round nearest the speed there was: 12 pages at 12 a second is half a bar, to half a millisecond",
              st["bars"] == 0.5 and abs(st["round"] - R) < 0.5 and abs(st["fps"] - 12000 / R) < 1e-6,
              f"round {st['round']:.3f}ms against half a bar {R:.3f}, {st['fps']:.4f} a second, bars {st['bars']}")
        want = f"12 pages in ½ bar · {round(12000 / R, 1)} a second"
        check("Beat is lit and the numbers not; Speed says it is on the song's beat, and the line says what the round makes",
              st["lit"] == ["Beat"] and st["hint"] == "on the song’s beat" and st["say"] == want and st["open"] and not st["inert"],
              f"lit {st['lit']}, hint {st['hint']!r}, line {st['say']!r} (want {want!r}), open {st['open']}, inert {st['inert']}")
        full = max(hs) if hs else 0
        mid = [x for x in hs if 1 < x < full - 1]
        check("the round's choices open under Speed as a glide, frame by frame",
              full > 30 and len(mid) >= 3 and all(y >= x - 0.5 for x, y in zip(hs, hs[1:])),
              f"{len(mid)} frames on the way to {full:.0f}px: " + ", ".join(f"{x:.0f}" for x in hs[:14]))
        made = {}
        for bars in (0.25, 1, 2):
            q.click(f"#beatRoundSeg [data-bars='{bars}']"); waits.settle(q, 300)
            s2 = q.evaluate(ST); made[bars] = (s2["bars"], s2["round"], s2["fps"], s2["say"])
        ok = all(m[0] == bb and abs(m[1] - bar(st) * bb) < 0.5 and m[3].startswith("12 pages in " + words(bb)) for bb, m in made.items())
        check("a quarter, one and two bars each make a round of exactly that",
              ok, "; ".join(f"{bb}: {m[1]:.1f}ms at {m[2]:.3f} ({m[3]})" for bb, m in made.items()))
        q.click("#beatRoundSeg [data-bars='0.5']"); waits.settle(q, 300)
        untune(q)
        q.evaluate("() => { frames[2].hold = 2; scheduleSave(); }")
        s3 = q.evaluate(ST)
        q.evaluate("() => { delete frames[2].hold; frames[3].draw = true; scheduleSave(); }")
        s4 = q.evaluate(ST)
        span = q.evaluate("() => SkriblHold.pageMs(frames[3], fps)")
        check("a page held twice counts twice, and a page that draws itself keeps its own time",
              abs(s3["fps"] - 13000 / R) < 1e-6 and abs(s3["round"] - R) < 0.5
              and abs(s4["fps"] - 11000 / (R - span)) < 1e-6 and abs(s4["round"] - R) < 0.5,
              f"held: {s3['fps']:.4f} a second, round {s3['round']:.2f}; drawn ({span:.0f}ms): {s4['fps']:.4f}, round {s4['round']:.2f} (half a bar {R:.2f})")
        q.evaluate("() => { delete frames[3].draw; scheduleSave(); }")
        q.click("#addblank"); waits.settle(q, 400)
        s5 = q.evaluate(ST)
        check("a page added keeps the round: 13 pages in half a bar, at a new speed",
              s5["pages"] == 13 and s5["bars"] == 0.5 and abs(s5["round"] - R) < 0.5 and s5["say"].startswith("13 pages in ½ bar"),
              f"{s5['pages']} pages, round {s5['round']:.2f}ms, {s5['fps']:.4f} a second, {s5['say']!r}")
        q.evaluate("() => { docLoop = { from: 5, to: 12, forever: true }; scheduleSave(); }")
        s6 = q.evaluate(ST)
        check("a stretch looping forever is the round, the pages before it playing once",
              abs(s6["round"] - R) < 0.5 and abs(s6["fps"] - 8000 / R) < 1e-6 and s6["say"].startswith("The loop in ½ bar"),
              f"stretch {s6['round']:.2f}ms at {s6['fps']:.4f} a second, {s6['say']!r}")
        q.evaluate("() => { docLoop = null; frames.push(...Array.from({ length: 35 }, () => JSON.parse(JSON.stringify(frames[0])))); buildStrip(); scheduleSave(); }")
        s7 = q.evaluate(ST)
        check("a round these pages cannot make is not offered: 48 pages in a quarter bar would be over 60 a second",
              s7["pages"] == 48 and 0.25 not in s7["rounds"] and 0.5 in s7["rounds"] and 48000 / (bar(st) * 0.25) > 60,
              f"{s7['pages']} pages, rounds offered {s7['rounds']}")
        q.evaluate("() => { frames.length = 13; buildStrip(); scheduleSave(); }")
        tune(q)
        q.click("#fps [data-fps='12']"); waits.settle(q, 500)
        s8 = q.evaluate(ST)
        check("6, 12 or 24 turns Beat off and plays at that speed; the round's choices close",
              s8["bars"] is None and s8["fps"] == 12 and s8["lit"] == ["12"] and not s8["open"] and s8["inert"] and s8["shown"],
              f"{s8}")
        q.click("#fpsBeat"); waits.settle(q, 400)
        before = q.evaluate(ST)["fps"]
        untune(q)
        browsing.pad_drawer(q, "music")
        q.click("#musicRemove"); q.click("#musicRemove")           # it asks once more before it goes
        waits.settle(q, 500); browsing.pad_drawer_close(q)
        tune(q)
        s9 = q.evaluate(ST)
        check("the song taken away puts Beat aside, and the speed stays where it was",
              s9["bars"] is None and not s9["shown"] and abs(s9["fps"] - before) < 1e-9
              and s9["hint"] == f"pages per second · this one plays at {round(before, 2)}",
              f"before {before:.4f}; now {s9}")
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
        c, q, errs = editor(b, still=True)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.evaluate("() => { const el = document.getElementById('beatMore'); window.__hs = [];"
                   " (function t() { window.__hs.push(el.getBoundingClientRect().height); if (window.__hs.length < 30) requestAnimationFrame(t); })(); }")
        q.click("#fpsBeat"); q.wait_for_timeout(700)
        hs = q.evaluate("() => window.__hs")
        full = max(hs) if hs else 0
        check("under Reduce Motion the round's choices are there at once",
              full > 30 and not [x for x in hs if 1 < x < full - 1], ", ".join(f"{x:.0f}" for x in hs[:10]))
        c.close()

    if part("kept"):
        print("\nKEPT -- with the draft, and in the post")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.click("#fpsBeat"); waits.settle(q, 300)
        q.click("#beatRoundSeg [data-bars='1']"); waits.settle(q, 300)
        st = q.evaluate(ST)
        pay = q.evaluate("async () => { const p = await buildSharePayload(); return { fps: p.fps, beat: p.beat || null }; }")
        check("the post carries the speed and the round",
              pay["beat"] == {"bars": 1} and abs(pay["fps"] - st["fps"]) < 1e-9, f"{pay}, speed {st['fps']}")
        q.wait_for_timeout(2500)
        q.reload()
        q.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip", timeout=15000)
        waits.settle(q, 1200)
        tune(q)
        again = q.evaluate(ST)
        check("after a reload Beat is the speed, the same round and the same speed",
              again["bars"] == 1 and abs(again["fps"] - st["fps"]) < 1e-9 and again["lit"] == ["Beat"] and again["open"],
              f"before {st['bars']} at {st['fps']:.4f}; after {again['bars']} at {again['fps']:.4f}, lit {again['lit']}")
        c.close()

    if part("beat"):
        print("\nON THE BEAT -- the pages keep to the song's own clock")
        c, q, errs = editor(b)
        q.evaluate(PAGES, {"n": 12}); song(q); tune(q)
        q.click("#fpsBeat"); waits.settle(q, 300); untune(q)
        bpm = q.evaluate("() => musicTempo.bpm")
        q.evaluate("() => { idx = 0; render(); }")
        q.click("#play"); rec = q.evaluate(REC, 16); q.click("#play")
        off = round_starts(rec, bpm, 0.5)
        check("playing, every round starts on the song's beat as heard, within 30ms, for sixteen seconds",
              len(off) >= 15 and max(abs(x) for x in off) <= 30,
              f"{len(off)} rounds: " + " ".join(f"{x:+.0f}" for x in off))
        waits.settle(q, 400)
        q.evaluate("() => { idx = 7; render(); }")
        q.click("#play"); rec = q.evaluate(REC, 5); q.click("#play")
        first = rec[0]["page"] if rec else None
        off = round_starts(rec, bpm, 0.5)
        check("Play from page 8 starts the song as far into its round, so the first round lands on the beat too",
              first == 7 and len(off) >= 4 and abs(off[0]) <= 30 and max(abs(x) for x in off) <= 30,
              f"first page {first}, rounds: " + " ".join(f"{x:+.0f}" for x in off))
        waits.settle(q, 400)
        q.evaluate("() => { idx = 0; render(); }")
        q.click("#play"); q.wait_for_timeout(2300)
        q.evaluate("() => pausePlay()"); q.wait_for_timeout(900); q.evaluate("() => resumePlay()")
        rec = q.evaluate(REC, 5); q.click("#play")
        off = round_starts(rec, bpm, 0.5)
        check("a pause and a resume keep them together",
              len(off) >= 4 and max(abs(x) for x in off) <= 30, " ".join(f"{x:+.0f}" for x in off))
        check("nothing went wrong on the page", not errs, "; ".join(errs)[:200])
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
