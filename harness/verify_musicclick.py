#!/usr/bin/env python3
"""The music drawer's click, and the beat lit as it is heard (the owner's picks
in the whole-drawer mock, FUTURE.md 6s, step 4; "All yes").

  The click is the end of Hear the loop's pill, a metronome a finger wide, the
  words of both buttons inside them on the owner's phone, a 320px phone and a
  desk; off at first, there once there is a beat. On, Hear the loop ticks on
  each beat of what plays, on the loop's own audio clock to the millisecond,
  the bar's tick higher every four beats from the loop's start, the loop's
  first beat as the music starts, each tick straight to the speakers, never
  into a post or a file; turned on while Hear plays, it ticks from the very
  next beat; a tick already set ahead never sounds once the click
  goes off or Hear stops; an end moved while it plays ticks the new loop from
  its next time round, no tick doubled at the join. Each beat's dot lights as
  it is heard (by the context's record of what its speakers play), a beat
  apart, at the dot's own place, the bar's bigger, the click on or off; it
  swells and fades, and under Reduce Motion only fades.

These rows were verify_musicbeat's until step 5: with them that suite went past
run_harness.sh's ten minutes a suite on CI and was stopped before it reported
(run 40658123304, shard 5 on both databases). Every row runs on the Pad and on
Flip: one drawer (lib/musicdrawer.js), and each editor's half is its hooks.
Skribl's ears are off here (lib/musicears.js): the pulse below is a beat the
ears would hear at once, and the beat is set as they or a tap would set it.
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


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the click ticks on the beat.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICCLICK_ONLY=Pad (or Flip) runs one editor.
# A real run sets neither.
ONLY = os.environ.get("MUSICCLICK_ONLY", "")
PART = os.environ.get("MUSICCLICK_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)


def _wav(seconds, rate=8000):
    """A pulse twice a second, on the half seconds: 120 beats a minute."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(11000 * math.sin(2 * math.pi * 220 * i / rate) * math.exp(-((2 * i / rate) % 1) * 7)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()
TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""
SET = "(o) => { musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; } if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } updateTrimUI(); }"


def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=TWELVE, opts=DESK, door="beat", ctx=None):
    c = ctx or waits.instrument(b.new_context(**opts))
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if drawn:
        if name == "Pad":
            box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
            pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down()
            for k in range(40):
                pg.mouse.move(box["x"] + 80 + k * 6, box["y"] + 80 + k * 3); pg.wait_for_timeout(50)
            pg.mouse.up(); pg.wait_for_timeout(300)
            pg.click("#recordBtn"); pg.wait_for_timeout(700)
        else:
            pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 8})
    if song:
        add(pg, song)
    if door:
        set_door(pg, door)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def tile(k):
    return f'#musicDoors .dp-tile[data-dp="{k}"]'


def open_door(pg):
    """The door that is open, or None."""
    return pg.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[aria-expanded=\"true\"]'); return t ? t.dataset.dp : null; }")


def set_door(pg, want):
    """A door open (its name) or every door shut (None), by the tiles, as a person does."""
    now = open_door(pg)
    if now == want:
        return
    pg.click(tile(want or now))
    pg.wait_for_timeout(350)
    browsing.wait_scroll_still(pg)


def door_for(pg, sel):
    """The door that holds `sel` open, as a person opens it to reach it."""
    k = pg.evaluate("(s) => { const e = document.querySelector(s), d = e && e.closest('#musicDoors .dp-panel'); return d ? d.dataset.dp : null; }", sel)
    if k:
        set_door(pg, k)


def press(pg, sel, ms=200):
    """A real click on a control that may be missing from a broken build: a
    row then says so in red rather than the run stopping on a timeout. Its
    door is opened first, where it is behind one."""
    try:
        door_for(pg, sel)
        pg.click(sel, timeout=3000)
    except Exception:
        return False
    pg.wait_for_timeout(ms)
    return True


# SKRIBL'S EARS ARE OFF HERE (lib/musicears.js). These rows are what a person
# does with no beat yet, from the first tap, and the pulse below is a beat the
# ears would hear at once; verify_musicears holds the ears to songs of their own.
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    _new_context = b.new_context

    def _deaf(*a, **k):
        c = _new_context(*a, **k)
        c.add_init_script(NO_EARS)
        return c
    b.new_context = _deaf

    print("\nMUSIC CLICK — the click, and the beat lit as it is heard")
    # THE CLICK (the owner's pick in the whole-drawer mock, FUTURE.md 6s): the
    # end of Hear the loop's pill, a metronome; off at first, there once there
    # is a beat. On, Hear the loop ticks on each beat of what plays, on the
    # loop's own audio clock, the bar's tick higher, every four beats from the
    # loop's start as the timeline draws them, the loop's first beat as the
    # music starts (the engine starts LEAD ahead of its sound); each tick
    # straight to the speakers, never into a post or a file. A tick already
    # set ahead never sounds once the click goes off or Hear stops, and an end
    # moved while it plays ticks the new loop from its next time round with no
    # tick doubled at the join. Each beat's dot lights as it is heard (by the
    # context's own record of what its speakers play), click on or off, at
    # the dot's own place, bigger on a bar; under Reduce Motion it fades
    # without the swell.
    PILL = """() => { const r = (e) => e.getBoundingClientRect(), q = (s) => document.querySelector(s);
        const p = q('#musicPanel .mt-hear'), h = q('#previewLoopBtn'), k = q('#musicClickBtn'), a = q('#musicPlayBtn');
        if (!p || !k) return null;
        const P = r(p), H = r(h), K = r(k), A = r(a), fits = (b) => [...b.querySelectorAll('.tp-k, .tp-v')].every((x) => x.scrollWidth <= x.clientWidth + 0.5 && r(x).right <= r(b).right + 0.5);
        return { inPill: H.left >= P.left - 0.5 && K.right <= P.right + 0.5 && Math.abs(H.right - K.left) <= 1.5 && Math.abs(H.top - K.top) <= 0.5 && Math.abs(H.bottom - K.bottom) <= 0.5,
                 line: getComputedStyle(k).borderLeftWidth !== '0px' && getComputedStyle(k).borderLeftColor === getComputedStyle(p).borderTopColor,
                 card: getComputedStyle(p).backgroundColor, hearBg: getComputedStyle(h).backgroundColor, kw: Math.round(K.width), kh: Math.round(K.height),
                 words: fits(h) && fits(a), side: Math.round(A.top) === Math.round(P.top) || A.bottom <= P.top, label: k.getAttribute('aria-label'),
                 pressed: k.getAttribute('aria-pressed'), disabled: k.disabled,
                 reach: { vh: innerHeight, hear: Math.round((H.top + H.bottom) / 2), click: Math.round((K.top + K.bottom) / 2), top: Math.round(P.top), bottom: Math.round(P.bottom) } }; }"""
    for _n, _p in eds("click"):
        got = {}
        for dev, o in (("the owner's phone", PHONE), ("a 320px phone", dict(PHONE, viewport={"width": 320, "height": 640})), ("a desk", DESK)):
            c, pg, errs = editor(b, _n, _p, door=None, opts=o)
            first = pg.evaluate(PILL)
            pg.evaluate(SET, {"tempo": {"bpm": 120, "phase": 0}})
            pg.wait_for_timeout(200)
            got[dev] = (first, pg.evaluate(PILL))
            c.close()
        ok = all(a and z and a["inPill"] and a["line"] and a["hearBg"] in ("rgba(0, 0, 0, 0)", "transparent") and a["kw"] >= 44 and a["kh"] >= 44
                 and a["words"] and a["side"] and a["label"] == "Click on each beat" for a, z in got.values())
        check(f"{_n}: the click is the end of Hear the loop's pill: one card, a metronome parted by the card's line, as tall as Hear and a finger "
              "wide, Hear's words and Play's inside their buttons (the owner's phone, a 320px phone, a desk)", ok,
              "; ".join(f"{d}: {a}" for d, (a, z) in got.items()))
        # THUMB REACH (FUTURE.md 6s, from Wavebox, which keeps play at the
        # foot): on the owner's phone, as the drawer opens with a song, Hear
        # the loop and the click sit in the screen's lower half, whole on it.
        rc = got["the owner's phone"][1]["reach"] if got["the owner's phone"][1] else None
        check(f"{_n}: on the owner's phone, Hear the loop and the click sit within a thumb's reach as the drawer opens with a song: "
              "in the lower half of the screen, whole on it",
              bool(rc) and rc["hear"] >= rc["vh"] / 2 and rc["click"] >= rc["vh"] / 2 and rc["top"] >= 0 and rc["bottom"] <= rc["vh"], str(rc))
        check(f"{_n}: the click is off at first, and there once there is a beat: with no beat it cannot be pressed",
              all(a and z and a["pressed"] == "false" and a["disabled"] and z["pressed"] == "false" and not z["disabled"] for a, z in got.values()),
              "; ".join(f"{d}: no beat {a and (a['pressed'], a['disabled'])}, a beat {z and (z['pressed'], z['disabled'])}" for d, (a, z) in got.items()))

    # Every oscillator the page makes: its frequency, when it starts and when
    # it was made (on the audio clock), where its gain goes (the speakers, or
    # anything else), and whether it was called off (its gain let go of, or a
    # stop before its start).
    OSC = """(() => { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return; const made = window.__osc = [];
      const co = AC.prototype.createOscillator;
      AC.prototype.createOscillator = function () { const o = co.call(this), ctx = this, rec = { f: [], start: null, out: [], off: false, made: ctx.currentTime }; made.push(rec);
        const sv = o.frequency.setValueAtTime.bind(o.frequency); o.frequency.setValueAtTime = (v, t) => { rec.f.push(v); return sv(v, t); };
        const st = o.start.bind(o); o.start = (t) => { rec.start = t; return st(t); };
        const sp = o.stop.bind(o); o.stop = (t) => { if (rec.start != null && t < rec.start) rec.off = true; return sp(t); };
        const cn = o.connect.bind(o); o.connect = (g, ...r) => { const gc = g.connect.bind(g), gd = g.disconnect.bind(g);
          g.connect = (d, ...rr) => { rec.out.push(d === ctx.destination ? 'speakers' : (d && d.constructor && d.constructor.name) || String(d)); return gc(d, ...rr); };
          g.disconnect = (...rr) => { rec.off = true; return gd(...rr); };
          return cn(g, ...r); };
        return o; }; })()"""
    TICKS = "() => window.__osc.filter((o) => o.f.length && [1568, 1175].includes(o.f[0])).map((o) => ({ at: o.start, f: o.f[0], out: o.out, off: o.off, made: o.made }))"
    # Called with a tick set ahead of the sound (its start still to come): the
    # control pressed at that moment, and whether that tick was called off.
    AHEAD = """(sel) => new Promise((res) => { const t0 = performance.now(), ticks = () => window.__osc.filter((o) => o.f.length && [1568, 1175].includes(o.f[0]));
      const id = setInterval(() => { const ahead = ticks().filter((o) => o.start > audioCtx.currentTime + 0.02 && !o.off);
        if (!ahead.length && performance.now() - t0 < 3000) return;
        clearInterval(id); const n = ticks().length, lit = (window.__lit || []).length; document.querySelector(sel).click();
        res({ ahead: ahead.length, off: ahead.every((o) => o.off), n, lit }); }, 5); })"""
    # The lit beat, each time it lights: the timeline's own record, with the
    # context's record of what its speakers play just after.
    LIT_REC = """() => { const tl = document.getElementById('musicTimeline'), out = window.__lit = []; let n = 0;
      window.__litT = setInterval(() => { const l = tl._lit; if (l && l.n !== n) { n = l.n;
        const ts = audioCtx.getOutputTimestamp ? audioCtx.getOutputTimestamp() : null;
        out.push({ x: l.x, bar: l.bar, t: l.t, at: l.at, ctxT: ts ? ts.contextTime : null, perfT: ts ? ts.performanceTime : null,
                   beats: (tl._painted && tl._painted.beats || []).map((b) => [b[0], b[1], b[2]]) }); } }, 4); }"""
    CLOCK = "() => ({ now: audioCtx.currentTime, el: _waLoop.elapsed(), dur: _waLoop.duration(), s0: document.getElementById('musicClickBtn')._soundFrom, lead: SkriblAudioLoop.LEAD })"
    PRESSED = "() => document.getElementById('musicClickBtn').getAttribute('aria-pressed')"
    CLICK_LOOP = "() => { musicTempo = { bpm: 120, phase: 0 }; trimStart = 1.0; trimEnd = 5.0; loopCrossfadeMs = 0; setCrossfadeUI(); loopCutOnSilence = false; updateTrimUI(); }"

    def grid(at, top, dur, p=0.5):
        """Where a time on the audio clock falls in what plays: (the beat's
        index from the loop's top, how far off that beat in seconds)."""
        if not dur:
            return 0, 99
        u = (at - top) % dur
        k = round(u / p)
        return k % round(dur / p), abs(u - k * p)

    for _n, _p in eds("click"):
        c = waits.instrument(b.new_context(**DESK))
        c.add_init_script(OSC)
        c, pg, errs = editor(b, _n, _p, door=None, ctx=c)
        pg.evaluate(CLICK_LOOP)
        pg.wait_for_timeout(300)
        press(pg, "#musicClickBtn", 100)
        on = pg.evaluate(PRESSED)
        pg.evaluate(LIT_REC)
        press(pg, "#previewLoopBtn", 2400)
        clock = pg.evaluate(CLOCK)
        ticks = sorted(pg.evaluate(TICKS), key=lambda t: t["at"])
        # The click off just as a tick is set ahead: that one never sounds, and
        # none after it; on again, then Hear stopped just as one is set ahead.
        offed = pg.evaluate(AHEAD, "#musicClickBtn")
        pg.wait_for_timeout(1200)
        n_off = len(pg.evaluate(TICKS))
        lit_off = pg.evaluate("() => window.__lit.length")
        press(pg, "#musicClickBtn", 50)
        stopped = pg.evaluate(AHEAD, "#previewLoopBtn")
        pg.wait_for_timeout(1000)
        n_stop = len(pg.evaluate(TICKS))
        lit = pg.evaluate("() => { clearInterval(window.__litT); return window.__lit; }")
        # The loop's top (where what plays begins: 120 a minute from 0, the
        # loop from 1.0s, so a beat every half second of it, the bars at its
        # 0 and 2s), LEAD before its sound began.
        top, dur = clock["s0"] - clock["lead"], clock["dur"]
        first, rest = (ticks[0], ticks[1:]) if ticks else (None, [])
        placed = [grid(t["at"], top, dur) for t in rest]
        gaps = [round(z["at"] - a["at"], 4) for a, z in zip(rest, rest[1:])]
        check(f"{_n}: with the click on, Hear the loop ticks on each beat of what plays, on the loop's own clock, to the millisecond, "
              "the bar's tick higher, every four beats from the loop's start, and the loop's first beat as the music starts",
              on == "true" and first is not None and abs(first["at"] - clock["s0"]) < 0.0015 and first["f"] == 1568 and len(rest) >= 3
              and all(e < 0.0015 for _, e in placed) and all(abs(g - 0.5) < 0.0015 for g in gaps)
              and all((t["f"] == 1568) == (k % 4 == 0) for t, (k, e) in zip(rest, placed)),
              f"pressed {on}; the first at {first and round((first['at'] - clock['s0']) * 1000, 2)}ms from the sound's start ({first and first['f']}Hz); "
              + f"then {len(rest)}, off their beats by " + ", ".join(f"{e * 1000:.2f}ms" for _, e in placed) + f"; gaps {gaps}; the loop {dur:.3f}s")
        check(f"{_n}: each tick goes straight to the speakers and nowhere else, so never into a post or a file",
              bool(ticks) and all(t["out"] == ["speakers"] for t in ticks), "; ".join(str(t["out"]) for t in ticks[:4]))
        check(f"{_n}: a tick already set ahead never sounds once the click goes off or Hear stops, and nothing ticks after either",
              offed["ahead"] > 0 and offed["off"] and n_off == offed["n"] and stopped["ahead"] > 0 and stopped["off"] and n_stop == stopped["n"],
              f"the click off with {offed['ahead']} set ahead (called off {offed['off']}), {offed['n']} -> {n_off} after; "
              f"Hear stopped with {stopped['ahead']} set ahead (called off {stopped['off']}), {stopped['n']} -> {n_stop} after")
        # The lit beat: one per beat heard, at its dot, the bar's bigger; and
        # when: each light against when its beat reached the ear, by the
        # context's record of what its speakers played (the first beat's
        # sound is the music's start).
        def dot(l):
            return min((abs(l["x"] - bx), bb, abs(l["t"] - bt)) for bx, bb, bt in l["beats"]) if l["beats"] else (99, None, 99)
        def late(l):
            if l["ctxT"] is None or l["perfT"] is None or not dur:
                return None
            heard = l["ctxT"] + (l["at"] - l["perfT"]) / 1000
            u = l["t"] - 1.0
            n = round((heard - top - u) / dur)
            beat = max(top + n * dur + u, clock["s0"]) if n == 0 else top + n * dur + u
            return (heard - beat) * 1000
        at_dots = [dot(l) for l in lit]
        lates = [late(l) for l in lit]
        known = sorted(x for x in lates if x is not None)
        mid = known[len(known) // 2] if known else None
        lgaps = sorted(round(z["at"] - a["at"]) for a, z in zip(lit, lit[1:]))
        check(f"{_n}: each beat's dot lights as it is heard, a beat apart, at the dot's own place on the timeline, the bar's bigger, with the click on or off",
              len(lit) >= 6 and offed["lit"] > 0 and lit_off > offed["lit"] and lgaps and abs(lgaps[len(lgaps) // 2] - 500) <= 30
              and all(d < 0.6 and bt < 1e-3 and bb == l["bar"] for (d, bb, bt), l in zip(at_dots, lit))
              and known and len(known) == len(lit) and min(known) > -5 and -5 < mid < 25,
              f"{len(lit)} lit ({offed['lit']} as the click went off, {lit_off - offed['lit']} after), the middle gap {lgaps and lgaps[len(lgaps) // 2]}ms; "
              + f"after its beat was heard by {', '.join('%.1f' % x for x in known[:8])}ms (the middle {mid and round(mid, 1)}); "
              + "; ".join(f"x {l['x']} ({d:.2f} from its dot, bar {l['bar']}/{bb})" for (d, bb, bt), l in zip(at_dots[:4], lit[:4])))
        c.close()

    # An end moved while it plays: the click follows the new loop from its
    # next time round, and the loop's first beat ticks once at the join: as
    # the new loop's music starts when it starts again before the old loop
    # comes round (the old loop's tick for its top, set ahead, called off), or
    # as the old loop came round when the timer that starts it again fired
    # late (the new loop's first beat then not set a second time, a tenth of
    # a second after). Late on purpose too: the page held busy from 60ms
    # before the old loop comes round to 40ms after, so its timer, due 10ms
    # before, can only fire after.
    def restart(pg, late):
        press(pg, "#musicClickBtn", 100)
        press(pg, "#previewLoopBtn", 1000)
        old = pg.evaluate(CLOCK)
        pg.fill("#endReadout", "4"); pg.press("#endReadout", "Enter")
        top0 = old["s0"] - old["lead"]
        came = top0 + old["dur"] * math.ceil((old["now"] - top0) / old["dur"] + 1e-9)   # the old loop's next top
        if late:
            # From 60ms before it comes round to 40ms after: the timer that
            # starts it again (due 10ms before) can only fire after.
            pg.evaluate("""(T) => { const ms = (T - audioCtx.currentTime) * 1000 - 60;
                setTimeout(() => { const t0 = performance.now(); while (performance.now() - t0 < 100) {} }, Math.max(0, ms)); }""", came)
        pg.wait_for_timeout(int((came - old["now"]) * 1000) + 1800)
        new = pg.evaluate(CLOCK)
        made = pg.evaluate(TICKS)
        sounded = sorted((t for t in made if not t["off"]), key=lambda t: t["at"])
        press(pg, "#previewLoopBtn", 100)
        again = new["s0"] - new["lead"]            # where it started again, on the audio clock
        early = again < came
        # The old loop's tick for its top (made before it started again):
        # called off when it started again before; sounding (the join's one
        # tick) when it started again after.
        top_tick = [t["off"] for t in made if t["made"] < again - 0.005 and abs(t["at"] - came) < 0.0015]
        join = [t for t in sounded if abs(t["at"] - new["s0"]) < 0.12]
        rest = [t for t in sounded if t["at"] >= new["s0"] + 0.12]
        want = new["s0"] if early else came
        close = [round(z["at"] - a["at"], 4) for a, z in zip(sounded, sounded[1:]) if z["at"] - a["at"] < 0.3]
        ok = (abs(old["dur"] - 4.0) < 0.01 and abs(new["dur"] - 3.0) < 0.01 and len(join) == 1 and abs(join[0]["at"] - want) < 0.0015
              and join[0]["f"] == 1568 and len(rest) >= 2 and all(grid(t["at"], again, new["dur"])[1] < 0.0015 for t in rest) and not close
              and (all(top_tick) if early else top_tick == [False]))
        why = (f"the loop {old['dur']:.2f}s then {new['dur']:.2f}s, started again {(again - came) * 1000:+.1f}ms from when the old one came round; "
               f"at the join {[(round((t['at'] - new['s0']) * 1000, 1), t['f']) for t in join]} (ms from the new sound's start), "
               f"the old loop's tick for its top called off {top_tick}; "
               f"{len(rest)} after, on the new loop's beats {all(grid(t['at'], again, new['dur'])[1] < 0.0015 for t in rest)}; ticks closer than 0.3s: {close}")
        return ok, early, why

    for _n, _p in eds("click"):
        res = {}
        for late in (False, True):
            c = waits.instrument(b.new_context(**DESK))
            c.add_init_script(OSC)
            c, pg, errs = editor(b, _n, _p, door="exact", ctx=c)
            pg.evaluate(CLICK_LOOP)
            pg.wait_for_timeout(300)
            res[late] = restart(pg, late)
            c.close()
        ok, early, why = res[False]
        check(f"{_n}: an end moved while the click plays: from the next time round it ticks the new loop, and the loop's first beat "
              "ticks once at the join, never twice", ok, ("started again before it came round: " if early else "started again late: ") + why)
        ok, early, why = res[True]
        check(f"{_n}: the loop started again late, just after it came round (the page held busy across it): its first beat still "
              "ticks once, as the old loop came round", ok and not early, why)

    # The click turned on while Hear plays ticks from the very next beat: one
    # already set ahead, lit and not yet ticked, ticks too. Turned on 40 to
    # 120ms before a beat, which the scheduler (every 30ms, 160ms ahead) has
    # already set.
    NEXT = """() => new Promise((res) => { const t0 = performance.now();
      const id = setInterval(() => { const now = audioCtx.currentTime, d = _waLoop.duration(), top = document.getElementById('musicClickBtn')._soundFrom - SkriblAudioLoop.LEAD;
        if (!(d > 0)) return;
        const u = ((now - top) % d + d) % d, next = now + (0.5 - (u % 0.5));
        if ((next - now > 0.04 && next - now < 0.12) || performance.now() - t0 > 3000) { clearInterval(id);
          document.getElementById('musicClickBtn').click(); res({ next: next, gap: next - now }); } }, 3); })"""
    for _n, _p in eds("click"):
        c = waits.instrument(b.new_context(**DESK))
        c.add_init_script(OSC)
        c, pg, errs = editor(b, _n, _p, door=None, ctx=c)
        pg.evaluate(CLICK_LOOP)
        pg.wait_for_timeout(300)
        press(pg, "#previewLoopBtn", 1300)
        got = pg.evaluate(NEXT)
        pg.wait_for_timeout(700)
        ticks = sorted(pg.evaluate(TICKS), key=lambda t: t["at"])
        press(pg, "#previewLoopBtn", 100)
        first = ticks[0]["at"] if ticks else None
        check(f"{_n}: the click turned on while Hear the loop plays ticks from the very next beat, one already set ahead among them",
              first is not None and abs(first - got["next"]) < 0.0015 and 0.04 < got["gap"] < 0.12,
              f"turned on {got['gap'] * 1000:.0f}ms before a beat; the first tick {first and round((first - got['next']) * 1000, 2)}ms from it")
        c.close()

    # Under Reduce Motion the light fades with no swell; otherwise it swells.
    for _n, _p in eds("click"):
        anims = {}
        for mode in ("no-preference", "reduce"):
            c = waits.instrument(b.new_context(reduced_motion=mode, **DESK))
            c, pg, errs = editor(b, _n, _p, door=None, ctx=c)
            pg.evaluate("() => { musicTempo = { bpm: 120, phase: 0 }; trimStart = 1.0; trimEnd = 5.0; updateTrimUI(); }")
            pg.wait_for_timeout(300)
            pg.evaluate("""() => { window.__an = []; const E = Element.prototype.animate;
                Element.prototype.animate = function (k, o) { if (this.classList && this.classList.contains('mt-tl-lit')) window.__an.push(JSON.stringify(k)); return E.call(this, k, o); }; }""")
            press(pg, "#previewLoopBtn", 1500)
            anims[mode] = pg.evaluate("() => window.__an.slice(0, 2)")
            press(pg, "#previewLoopBtn", 100)
            c.close()
        moves = lambda ks: any("transform" in k for k in ks)
        check(f"{_n}: the light swells and fades; under Reduce Motion it only fades",
              anims["no-preference"] and moves(anims["no-preference"]) and anims["reduce"] and not moves(anims["reduce"]),
              f"as it is: {anims['no-preference'][:1]}; Reduce Motion: {anims['reduce'][:1]}")

    b.close()

summarise_and_exit()
