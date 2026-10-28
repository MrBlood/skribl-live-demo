#!/usr/bin/env python3
"""Songs in three (step 8 of the whole-drawer mock, FUTURE.md 6s; the owner:
"All yes"): Skribl hears a waltz's bar of three, and the music drawer counts
in it, 3 · 6 · 12 · 24, with Beats in a bar in the Beat door for when it hears
wrong.

THE SONGS ARE MADE IN THE PAGE (harness/songsynth.py), so every beat and
every bar is known: a waltz at 168 (oom-pah-pah), a ballad in three at 92, a
band in three speeding up from 132, a piano's waltz with no drums at 150, and
two slow waltzes heard first at their eighths (84 and 76); and in four, the ears' own songs
(verify_musicears) and a piano in four with a waltz's sounds two to a bar.

  THE EARS. Every song in three is heard in three, at its own beat within
  half a beat a minute (the slow waltzes at 84 and 76, not at their
  eighths); every song in four is heard in four.

  THE PICK IN THREE. A new waltz starts on one of its bars, within 10ms, and
  is 24 beats long by its own beats, within 10ms; its beat is heard, in
  three. The one line and the Length tile say 24 beats, Beats offers 3 · 6 ·
  12 · 24 with 24 lit, the timeline's dots are bigger on every third beat
  from the loop's start, "a bar" in Each press is three beats and + moves an
  end that far, and the click's higher tick and the lit beat's bigger light
  fall on every third beat.

  BEATS IN A BAR. Under the tap, 3 lit, "heard by Skribl". A tap on
  4 leaves the loop where it is, to the millisecond; Beats offers 4 · 8 · 16
  · 32 with none lit (24 beats is not whole bars of four), the dots are
  bigger every fourth beat, and it says "set by you"; Skribl's pick then
  counts in four. 3 again is "heard by Skribl". A song in four reads 4,
  "heard by Skribl"; a beat tapped where Skribl heard none, 4 and nothing
  said, and 3 tapped there, "set by you" and 3 · 6 · 12 · 24. The 4 and the 3
  stay put under the finger whatever the words say, on a phone and a desk.

  SNAP IN THREE. An end let go at 10.8 beats settles on 11, the nearest beat,
  as in four (whole bars of three took it to 12); zoomed in, an end let go
  within an eighth of a beat of 12, whole bars of three, stays, and the beat
  becomes the one that makes 12 exactly. A beat tapped
  on the waltz is the taps', still in three.

  KEPT. After a reload the waltz comes back in three, "heard by Skribl", and
  a bar set by you comes back "set by you".

  FLIP'S BEAT IN THREE. With a waltz, Beat's rounds are 1 and 2 bars (a
  quarter or half of a bar of three ends between its beats), and a round of
  eight pages lasts exactly three beats; the bar set to four, the four rounds
  are back and the round is four beats.

Every drawer row runs on the Pad and on Flip, on a phone: one drawer
(lib/musicdrawer.js), one pair of ears (lib/musicears.js); the ears' rows
read the module itself, once, as both editors load the same one.
"""
import base64
import json
import os
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence that Skribl hears a song in three.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402
from songsynth import SYNTH, SPECS, THREES, PIANO4  # noqa: E402

# For calibration: MUSICTHREE_ONLY=Pad (or Flip) runs one editor, and
# MUSICTHREE_PART=ears (pick, bar, snap, kept, flip, words) one part. A real run sets neither.
ONLY = os.environ.get("MUSICTHREE_ONLY", "")
PART = os.environ.get("MUSICTHREE_PART", "")
EDITORS = [e for e in (("Pad", "/skribl-pad"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900})


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


def part(name):
    return not PART or PART == name


# Skribl's answer, marked as given even when the drawer throws taking it, so
# a broken drawer makes rows red rather than a wait that never ends.
LISTENED = """() => { const E = window.SkriblEars; if (!E || E.__wrapped) return; const real = E.listen; E.__wrapped = true;
  E.listen = (b, d) => real(b, (H) => { window.__heard = { bar: H.bar, bpm: H.bpm }; try { d(H); } finally { window.__earsDone = true; } }); }"""
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
# The drawer as it stands: the tempo kept, the loop, the one line, Beats and
# Beats in a bar, the tiles' words and the timeline's dots [time, bigger].
STATE = """() => { const q = (id) => document.getElementById(id), tl = q('musicTimeline'), p = tl && tl._painted;
  const tile = (k) => (document.querySelector('#musicDoors .dp-tile[data-dp="' + k + '"] .dp-v') || {}).textContent || '';
  return { tempo: musicTempo, s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs,
    line: (q('musicPickText') || {}).textContent || '', length: tile('length'),
    beats: [...q('musicBeatsSeg').querySelectorAll('button')].filter((b) => !b.hidden).map((b) => [+b.dataset.beats, b.textContent, b.classList.contains('on')]),
    barShown: !q('musicBarRow').hidden, bar: [...q('musicBarSeg').querySelectorAll('button')].filter((b) => b.classList.contains('on')).map((b) => +b.dataset.bar),
    says: q('musicBarSays').textContent, dots: p ? p.beats.map((b) => [b[2], b[1]]) : [] }; }"""
SET = "(o) => { musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; } if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } updateTrimUI(); }"
TRIM = "() => ({ s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs })"
TL = ("(id) => { const s = document.getElementById('musicTlStage').getBoundingClientRect(), h = document.getElementById(id).getBoundingClientRect(),"
      " v = (document.getElementById('musicTimeline').dataset.view || '0 1').split(' ').map(Number);"
      " return { x: s.left, w: s.width, hx: h.left + h.width / 2, hy: h.top + h.height / 2, v0: v[0], span: v[1], d: audioDuration }; }")
SONGS = {}


def songs(b):
    c = b.new_context()
    q = c.new_page()
    browsing.goto(q, BASE, "/skribl-pad")
    for name, spec in list(THREES.items()) + list(SPECS.items()) + [("piano4", PIANO4)]:
        r = q.evaluate(SYNTH, spec)
        SONGS[name] = {"file": {"name": name + ".wav", "mimeType": "audio/wav", "buffer": base64.b64decode(r["wav"])},
                       "truth": r["truth"], "seconds": r["seconds"], "wav": r["wav"]}
    c.close()


def editor(b, path, *, opts=PHONE, init=None, still=False):
    c = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", **opts))
    if init:
        c.add_init_script(init)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, path)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    q.evaluate(LISTENED)
    return c, q, errs


def add(q, name, wait=True):
    browsing.pad_drawer(q, "music")
    q.set_input_files("#musicInput", SONGS[name]["file"])
    q.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                        " && Math.abs(audioDuration - d) < 0.2", arg=SONGS[name]["seconds"], timeout=20000)
    if wait:
        q.wait_for_function("() => !!window.__earsDone", timeout=30000)
        waits.settle(q, 700)
    return q.evaluate(STATE)


def door(q, k):
    """A door open, as a person opens it (None shuts the open one)."""
    now = q.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[aria-expanded=\"true\"]'); return t ? t.dataset.dp : null; }")
    if now == k:
        return
    q.click(f'#musicDoors .dp-tile[data-dp="{k or now}"]')
    waits.settle(q, 450)


def tap_bar(q, n):
    """A real tap on Beats in a bar's 4 or 3, in the Beat door."""
    door(q, "beat")
    try:
        q.click(f'#musicBarSeg button[data-bar="{n}"]', timeout=3000)
    except Exception:
        return False
    waits.settle(q, 500)
    return True


def heard(st):
    n = st["e"] - st["s"]
    return n - min(st["xf"] / 1000, n / 2)


def from_bar(truth, start, k):
    """The song's own length of k beats from its bar nearest `start`, and how far that bar is."""
    db = min(truth["downbeats"], key=lambda t: abs(t - start))
    j = min(range(len(truth["beats"])), key=lambda i: abs(truth["beats"][i] - db))
    return (truth["beats"][j + k] - truth["beats"][j] if j + k < len(truth["beats"]) else None), start - db


def bigger_every(st, n):
    """Whether the timeline's dots are bigger on every n-th beat from the loop's start and on no other."""
    tp = st["tempo"] or {}
    p = 60 / tp["bpm"] if tp.get("bpm") else 0
    if not p or len(st["dots"]) < 2 * n:
        return False, f"{len(st['dots'])} dots"
    ks = [(round((t - st["s"]) / p), big) for t, big in st["dots"]]
    bad = [k for k, big in ks if big != (k % n == 0)]
    return not bad, f"{len(ks)} dots, bigger at {[k for k, big in ks if big][:6]}{' wrong at ' + str(bad[:6]) if bad else ''}"


with sync_playwright() as pw:
    b = pw.chromium.launch()
    songs(b)
    W = SONGS["waltz"]["truth"]

    if part("ears"):
        print("\nTHE EARS -- songs in three heard in three, songs in four in four")
        c, q, errs = editor(b, "/skribl-pad")
        HEAR = """(o) => { const raw = atob(o.wav), n = (raw.length - 44) >> 1, x = new Float32Array(n);
          for (let i = 0; i < n; i++) { let v = raw.charCodeAt(44 + 2 * i) | (raw.charCodeAt(45 + 2 * i) << 8); if (v >= 32768) v -= 65536; x[i] = v / 32768; }
          try { const H = SkriblEars.hear(x, 22050); return { bar: H.bar, bpm: H.bpm, steady: SkriblEars.steady(H) }; }
          catch (e) { return { bar: 0, bpm: 0, steady: false, err: String(e) }; } }"""
        got = {name: q.evaluate(HEAR, {"wav": SONGS[name]["wav"]}) for name in SONGS if name not in ("chords", "tone", "sweep", "scatter")}
        threes = {k: v for k, v in got.items() if k in THREES}
        fours = {k: v for k, v in got.items() if k not in THREES}
        check("every song in three is heard in three, at its own beat within half a beat a minute (the slow waltzes at 84 and 76, not their eighths)",
              len(threes) == 6 and all(v["steady"] and v["bar"] == 3 and abs(v["bpm"] - THREES[k]["bpm"] * (1 + THREES[k].get("drift", 0) / 2)) < 1.5
                                       and abs(v["bpm"] - THREES[k]["bpm"]) < (2.5 if THREES[k].get("drift") else 0.5) for k, v in threes.items()),
              "; ".join(f"{k}: in {v['bar']} at {v['bpm']:.2f} (the song's {THREES[k]['bpm']})" for k, v in threes.items()))
        check("every song in four is heard in four: the ears' own songs, and a piano in four with a waltz's sounds two to a bar",
              len(fours) == 5 and all(v["steady"] and v["bar"] == 4 for v in fours.values()),
              "; ".join(f"{k}: in {v['bar']} at {v['bpm']:.2f}" for k, v in fours.items()))
        thrown = [f"{k}: {v['err']}" for k, v in got.items() if v.get("err")] + errs
        check("hearing threes threw nothing", not thrown, "; ".join(thrown[:3]))
        c.close()

    print("\nTHE PICK IN THREE -- a waltz counted in its own bars")
    # Every oscillator the page makes, its frequency and start (the click's
    # ticks: 1568 Hz on a bar, 1175 between, as verify_musicclick reads them).
    OSC = """(() => { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return; const made = window.__osc = [];
      const co = AC.prototype.createOscillator; AC.prototype.createOscillator = function () { const o = co.call(this), rec = { f: [], start: null }; made.push(rec);
        const sv = o.frequency.setValueAtTime.bind(o.frequency); o.frequency.setValueAtTime = (v, t) => { rec.f.push(v); return sv(v, t); };
        const st = o.start.bind(o); o.start = (t) => { rec.start = t; return st(t); }; return o; }; })()"""
    for name, path in eds("pick"):
        c, q, errs = editor(b, path, init=OSC)
        st = add(q, "waltz")
        tp = st["tempo"] or {}
        L, off = from_bar(W, st["s"], 24)
        check(f"{name}: a new waltz starts on one of its bars, within 10ms, and is 24 beats long by its own beats, within 10ms",
              abs(off) <= 0.010 and L is not None and abs(heard(st) - L) <= 0.010,
              f"start {st['s']:.4f}, {off * 1000:+.1f}ms from its bar; heard {heard(st):.4f}s, 24 of its beats {L}")
        # The beat given back is the loop's own length's (lib/musicears.js):
        # a tenth of a beat a minute at 168 is 5ms over 24 beats.
        check(f"{name}: its beat is the song's, to a tenth of a beat a minute, heard by Skribl and in three",
              abs(tp.get("bpm", 0) - 168) <= 0.1 and tp.get("heard") is True and tp.get("bar") == 3 and "barBy" not in tp, f"tempo {tp}")
        check(f"{name}: the one line and the Length tile say 24 beats, and Beats offers 3 · 6 · 12 · 24 with 24 lit",
              "24 beats" in st["line"] and st["length"] == "24 beats" and [x[0] for x in st["beats"]] == [3, 6, 12, 24]
              and [x[1] for x in st["beats"]] == ["3", "6", "12", "24"] and [x[2] for x in st["beats"]] == [False, False, False, True],
              f"line {st['line']!r}, tile {st['length']!r}, beats {st['beats']}")
        ok, why = bigger_every(st, 3)
        check(f"{name}: the timeline's dots are bigger on every third beat from the loop's start, and on no other", ok, why)
        door(q, "exact")
        q.click('#musicStepSeg button[data-step="bar"]'); waits.settle(q, 300)
        title = q.get_attribute('#musicStepSeg button[data-step="bar"]', "title") or ""
        before = q.evaluate(TRIM)
        q.click('.nudge-btn[data-which="end"][data-amount="-1"]', timeout=3000)
        waits.settle(q, 500)
        after = q.evaluate(TRIM)
        bar3 = 3 * 60 / tp.get("bpm", 168)
        check(f"{name}: 'a bar' in Each press is three beats: its name says so, and - moves the end that far",
              f"A bar, {bar3:.2f}s" == title and abs((before["e"] - after["e"]) - bar3) < 0.002,
              f"title {title!r} ({bar3:.3f}s a bar); the end moved {before['e'] - after['e']:.4f}s")
        # The click: on, Hear the loop for two and a half seconds, then which ticks were the higher.
        try:
            q.evaluate(SET, {"tempo": tp, "s": st["s"], "e": st["s"] + 24 * 60 / tp.get("bpm", 168) + 0.25, "xf": 250})
        except Exception as e:   # the drawer threw repainting: said below, not a stopped run
            errs.append(str(e).splitlines()[0])
        waits.settle(q, 300)
        door(q, None)
        q.click("#musicClickBtn"); q.wait_for_timeout(100)
        q.evaluate("""() => { const tl = document.getElementById('musicTimeline'), out = window.__lit = []; let n = 0;
          window.__litT = setInterval(() => { const l = tl._lit; if (l && l.n !== n) { n = l.n; out.push({ bar: l.bar, t: l.t }); } }, 4); }""")
        q.click("#previewLoopBtn"); q.wait_for_timeout(2600)
        ticks = q.evaluate("() => (window.__osc || []).filter((o) => o.f.length && [1568, 1175].includes(o.f[0]) && o.start != null).map((o) => [o.start, o.f[0] === 1568])")
        lit = q.evaluate("() => { clearInterval(window.__litT); return window.__lit; }")
        q.click("#previewLoopBtn"); q.wait_for_timeout(200)
        ticks.sort()
        p = 60 / tp.get("bpm", 168)
        tk = [(round((t - ticks[0][0]) / p), hi) for t, hi in ticks] if ticks else []
        lk = [(round((x["t"] - st["s"]) / p), x["bar"]) for x in lit]
        check(f"{name}: the click's higher tick and the lit beat's bigger light fall on every third beat from the loop's start",
              len(tk) >= 6 and all(hi == (k % 3 == 0) for k, hi in tk) and len(lk) >= 6 and all(bg == (k % 3 == 0) for k, bg in lk),
              f"ticks {tk[:9]}; lit {lk[:9]}")
        check(f"{name}: the waltz threw nothing", not errs, "; ".join(errs[:3]))
        c.close()

    print("\nBEATS IN A BAR -- 4 or 3, heard by Skribl or set by you")
    for name, path in eds("bar"):
        c, q, errs = editor(b, path)
        st = add(q, "waltz")
        door(q, "beat")
        shown = q.evaluate(STATE)
        check(f"{name}: under the tap, Beats in a bar shows 3 lit, heard by Skribl",
              shown["barShown"] and shown["bar"] == [3] and shown["says"] == "heard by Skribl"
              and q.evaluate("() => { const s = document.querySelector('#musicDoorBeat .mt-tap-row'), r = document.getElementById('musicBarRow'); return !!(s.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_FOLLOWING); }"),
              f"shown {shown['barShown']}, lit {shown['bar']}, says {shown['says']!r}")
        four = q.evaluate(STATE) if not tap_bar(q, 4) else q.evaluate(STATE)
        ok, why = bigger_every(four, 4)
        check(f"{name}: a tap on 4 leaves the loop where it is, to the millisecond, and counts it in four: Beats 4 · 8 · 16 · 32, none lit, the dots bigger every fourth beat",
              abs(four["s"] - st["s"]) < 1e-3 and abs(four["e"] - st["e"]) < 1e-3 and [x[0] for x in four["beats"]] == [4, 8, 16, 32]
              and not any(x[2] for x in four["beats"]) and ok,
              f"loop {st['s']:.4f}-{st['e']:.4f} then {four['s']:.4f}-{four['e']:.4f}; beats {four['beats']}; {why}")
        check(f"{name}: then it says set by you, and the tempo keeps it: four, set by you, still heard",
              four["says"] == "set by you" and four["bar"] == [4] and (four["tempo"] or {}).get("barBy") == "you"
              and "bar" not in (four["tempo"] or {}) and (four["tempo"] or {}).get("heard") is True,
              f"says {four['says']!r}, lit {four['bar']}, tempo {four['tempo']}")
        door(q, "length")
        try:
            q.click("#musicPickCard", timeout=3000)
        except Exception:
            pass
        waits.settle(q, 900)
        pk = q.evaluate(STATE)
        n4 = heard(pk) * (pk["tempo"] or {"bpm": 168})["bpm"] / 60
        check(f"{name}: with the bar set to four, Skribl's pick counts in four: its loop is 4, 8, 16 or 32 beats",
              any(abs(n4 - k) < 0.02 for k in (4, 8, 16, 32)) and (pk["tempo"] or {}).get("barBy") == "you",
              f"the pick {heard(pk):.3f}s, {n4:.2f} beats; tempo {pk['tempo']}")
        tap_bar(q, 3)
        back = q.evaluate(STATE)
        check(f"{name}: 3 again is Skribl's bar again: heard by Skribl, 3 · 6 · 12 · 24",
              back["says"] == "heard by Skribl" and back["bar"] == [3] and [x[0] for x in back["beats"]] == [3, 6, 12, 24]
              and (back["tempo"] or {}).get("bar") == 3 and "barBy" not in (back["tempo"] or {}),
              f"says {back['says']!r}, beats {back['beats']}, tempo {back['tempo']}")
        c.close()
        # A song in four: 4, heard by Skribl.
        c, q, errs = editor(b, path)
        st = add(q, "steady")
        door(q, "beat")
        st = q.evaluate(STATE)
        check(f"{name}: a song in four reads 4, heard by Skribl, and Beats offers 4 · 8 · 16 · 32",
              st["bar"] == [4] and st["says"] == "heard by Skribl" and [x[0] for x in st["beats"]][:4] == [4, 8, 16, 32]
              and "bar" not in (st["tempo"] or {}), f"lit {st['bar']}, says {st['says']!r}, beats {st['beats']}, tempo {st['tempo']}")
        c.close()
        # No ears: a beat tapped (set here as a tap sets it) on a song Skribl did not hear.
        c, q, errs = editor(b, path, init=NO_EARS)
        add(q, "waltz", wait=False)
        q.evaluate(SET, {"tempo": {"bpm": 168, "phase": 0.35}, "s": 0.35, "e": 0.35 + 12 * 60 / 168, "xf": 0})
        waits.settle(q, 500)
        door(q, "beat")
        none = q.evaluate(STATE)
        tap_bar(q, 3)
        three = q.evaluate(STATE)
        check(f"{name}: a tapped beat Skribl never heard reads 4 and says nothing; 3 tapped there says set by you, and Beats offers 3 · 6 · 12 · 24 with 12 lit",
              none["bar"] == [4] and none["says"] == "" and three["bar"] == [3] and three["says"] == "set by you"
              and [x[0] for x in three["beats"]] == [3, 6, 12, 24] and [x[2] for x in three["beats"]] == [False, False, True, False]
              and (three["tempo"] or {}).get("bar") == 3 and (three["tempo"] or {}).get("barBy") == "you",
              f"before: lit {none['bar']}, says {none['says']!r}; after: lit {three['bar']}, says {three['says']!r}, beats {three['beats']}, tempo {three['tempo']}")
        c.close()

    print("\nSNAP IN THREE")
    for name, path in eds("snap"):
        c, q, errs = editor(b, path)
        st = add(q, "waltz")
        tp = st["tempo"]
        p = 60 / tp["bpm"]
        q.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })"); q.wait_for_timeout(300)
        at = q.evaluate(TL, "tlEnd")
        target = st["s"] + 10.8 * p + st["xf"] / 1000
        q.mouse.move(at["hx"], at["hy"]); q.mouse.down()
        q.mouse.move(at["x"] + (target - at["v0"]) / at["span"] * at["w"], at["hy"], steps=8)
        q.mouse.up(); q.wait_for_timeout(900)
        got = q.evaluate(TRIM)
        n = heard(got) / p
        check(f"{name}: an end let go at 10.8 beats settles on 11, the nearest beat, as in four (whole bars of three took it to 12)",
              abs(n - 11) < 0.01 and abs(got["s"] - st["s"]) < 1e-6, f"let go at {(target - st['s'] - st['xf'] / 1000) / p:.2f} beats; settled at {n:.3f} beats")
        # Zoomed in: the loop 12.06 beats, the end let go where it is.
        q.evaluate(SET, {"tempo": tp, "s": st["s"], "e": st["s"] + 12.06 * p, "xf": 0})
        waits.settle(q, 300)
        for _ in range(4):
            q.click("#musicTlIn"); q.wait_for_timeout(260)
        q.wait_for_timeout(400)
        at = q.evaluate(TL, "tlEnd")
        q.mouse.move(at["hx"], at["hy"]); q.mouse.down()
        q.mouse.move(at["hx"] + 1, at["hy"], steps=2); q.mouse.move(at["hx"], at["hy"], steps=2)
        let_go = q.evaluate(TRIM)
        q.mouse.up(); q.wait_for_timeout(900)
        got, nt = q.evaluate(TRIM), q.evaluate("() => musicTempo") or {}
        k = heard(got) * nt.get("bpm", 0) / 60
        check(f"{name}: zoomed in, an end let go within an eighth of a beat of 12 stays, and the beat becomes the one that makes 12 exactly, still in three",
              abs(got["e"] - let_go["e"]) < 1e-6 and abs(k - 12) < 0.003 and nt.get("by") == "end" and nt.get("bar") == 3,
              f"let go {let_go['e']:.4f}, now {got['e']:.4f}; {k:.4f} beats at {nt.get('bpm')}; tempo {nt}")
        c.close()
        # A beat tapped on the waltz: the taps', still in three.
        c, q, errs = editor(b, path)
        add(q, "waltz")
        door(q, "beat")
        TAP = """(o) => new Promise((res) => { const b = document.getElementById('musicTapBtn'); let i = 0;
          const go = () => { b.click(); if (++i < o.n) setTimeout(go, i === 1 ? 600 : o.gap); else setTimeout(res, 2600); }; go(); })"""
        q.evaluate(TAP, {"n": 7, "gap": 500})
        tt = q.evaluate("() => musicTempo") or {}
        check(f"{name}: a beat tapped on the waltz is the taps' own, and still in three",
              abs(tt.get("bpm", 0) - 120) <= 1 and not tt.get("heard") and tt.get("bar") == 3, f"tempo {tt}")
        c.close()

    print("\nKEPT -- the bar comes back with the song")
    for name, path in eds("kept"):
        c, q, errs = editor(b, path)
        st = add(q, "waltz")
        save = "() => (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)()"

        def reload_(q):
            q.evaluate(save); q.wait_for_timeout(2500)
            q.reload()
            q.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
            q.evaluate(LISTENED)
            q.wait_for_timeout(3500)
            browsing.pad_drawer(q, "music")
            door(q, "beat")
            return q.evaluate(STATE)
        again = reload_(q)
        check(f"{name}: after a reload the waltz comes back in three, heard by Skribl, 3 · 6 · 12 · 24",
              (again["tempo"] or {}).get("bar") == 3 and again["bar"] == [3] and again["says"] == "heard by Skribl"
              and [x[0] for x in again["beats"]] == [3, 6, 12, 24] and abs(again["s"] - st["s"]) < 1e-3,
              f"tempo {again['tempo']}, lit {again['bar']}, says {again['says']!r}, beats {again['beats']}")
        tap_bar(q, 4)
        mine = reload_(q)
        check(f"{name}: a bar set by you comes back set by you", (mine["tempo"] or {}).get("barBy") == "you" and mine["bar"] == [4]
              and mine["says"] == "set by you", f"tempo {mine['tempo']}, lit {mine['bar']}, says {mine['says']!r}")
        c.close()

    print("\nFLIP'S BEAT IN THREE")
    if part("flip") and (not ONLY or ONLY == "Flip"):
        PAGES = """(o) => { frames.length = 0;
          for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
            for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.05 * (k % 16)) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
            f.strokes.push(...pts); f.strokeGroups.push(pts.length); frames.push(f); }
          fps = 12; idx = 0; buildStrip(); render(); updateToolState(); scheduleSave(); }"""
        ST = """() => { const H = window.SkriblHold, p = H.plan(frames, fps, docLoop);
          return { fps, bars: beatBars, bpm: musicTempo ? musicTempo.bpm : 0, round: p.forever ? p.stretchMs : p.cycle,
            rounds: [...document.querySelectorAll('#beatRoundSeg button')].filter((b) => !b.hidden).map((b) => +b.dataset.bars),
            say: document.getElementById('beatSay').textContent }; }"""
        c, q, errs = editor(b, "/flip")
        q.evaluate(PAGES, {"n": 8})
        add(q, "waltz")
        browsing.pad_drawer_close(q)
        q.click("#tuneBtn"); waits.settle(q, 600)
        q.click("#fpsBeat"); waits.settle(q, 500)
        s3 = q.evaluate(ST)
        b3 = 3 * 60000 / s3["bpm"] if s3["bpm"] else 0
        check("Flip: with a waltz, Beat's rounds are 1 and 2 bars, and a round of 8 pages lasts exactly three beats",
              s3["rounds"] == [1, 2] and s3["bars"] == 1 and b3 and abs(s3["round"] - b3) < 0.5 and "in 1 bar" in s3["say"],
              f"rounds {s3['rounds']}, round {s3['round']:.1f}ms against a bar of three {b3:.1f}ms; {s3['say']!r}")
        q.click("#tuneBtn"); waits.settle(q, 400)
        browsing.pad_drawer(q, "music")
        tap_bar(q, 4)
        browsing.pad_drawer_close(q)
        q.click("#tuneBtn"); waits.settle(q, 600)
        s4 = q.evaluate(ST)
        b4 = 4 * 60000 / s4["bpm"] if s4["bpm"] else 0
        check("Flip: the bar set to four, the four rounds are back and the round is four beats",
              s4["rounds"] == [0.25, 0.5, 1, 2] and s4["bars"] == 1 and b4 and abs(s4["round"] - b4) < 0.5,
              f"rounds {s4['rounds']}, round {s4['round']:.1f}ms against a bar of four {b4:.1f}ms; {s4['say']!r}")
        c.close()

    print("\nTHE WORDS -- the 4 and the 3 stay put under the finger")
    WHERE = """() => { const r = (b) => { const x = b.getBoundingClientRect(); return [Math.round(x.left * 4) / 4, Math.round(x.top * 4) / 4]; };
      const row = document.getElementById('musicBarRow'), rr = row.getBoundingClientRect(), panel = row.closest('.dp-panel').getBoundingClientRect();
      return { says: document.getElementById('musicBarSays').textContent, four: r(document.querySelector('#musicBarSeg button[data-bar="4"]')),
               three: r(document.querySelector('#musicBarSeg button[data-bar="3"]')), inside: rr.left >= panel.left - 0.5 && rr.right <= panel.right + 0.5,
               over: row.scrollWidth - row.clientWidth }; }"""
    for name, path in eds("words"):
        for face, opts in (("a 402 phone", PHONE), ("a 320 phone", dict(PHONE, viewport={"width": 320, "height": 700})), ("a desk", DESK)):
            c, q, errs = editor(b, path, opts=opts, init=NO_EARS)
            add(q, "waltz", wait=False)
            runs = []
            # Each word the row says, reached as a person reaches it, by a tap:
            # heard by Skribl, then set by you (4), then set by you (3); and a
            # beat Skribl never heard, nothing said, then set by you (3).
            for tp, taps in (({"bpm": 168, "phase": 0.35, "heard": True, "bar": 3}, (4, 3)), ({"bpm": 168, "phase": 0.35}, (3,))):
                q.evaluate(SET, {"tempo": tp, "s": 0.35, "e": 0.35 + 12 * 60 / 168, "xf": 0})
                waits.settle(q, 400)
                door(q, "beat")
                # In view first, so a tap needs no scroll: what moves then is the drawer's own doing.
                q.evaluate("() => document.getElementById('musicBarRow').scrollIntoView({ block: 'center' })")
                waits.settle(q, 400)
                seen = [q.evaluate(WHERE)]
                for n in taps:
                    tap_bar(q, n)
                    seen.append(q.evaluate(WHERE))
                runs.append(seen)
            still = all(s["four"] == r[0]["four"] and s["three"] == r[0]["three"] for r in runs for s in r)
            says = [[s["says"] for s in r] for r in runs]
            check(f"{name} ({face}): the 4 and the 3 stay put under the finger whatever the words say (heard by Skribl, set by you, nothing), inside the door",
                  still and says == [["heard by Skribl", "set by you", "set by you"], ["", "set by you"]]
                  and all(s["inside"] and s["over"] <= 0 for r in runs for s in r),
                  " | ".join("; ".join(f"{s['says']!r}: 4 at {s['four']}, 3 at {s['three']}" for s in r) for r in runs))
            c.close()

    b.close()
summarise_and_exit()
