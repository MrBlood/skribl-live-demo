#!/usr/bin/env python3
"""The Pad's Repeat: Play goes round until you stop it, the music with it.

THE OWNER, of the Pad's replay: "i wasn't talking about the music looping - i
was talking about the drawing looping. should there be a loop button?"; of
the mock (the Snap, zoom and Repeat page), "all yes": a Repeat button beside
the speed, off to start and remembered like the speed; posts keep repeating
as now; not for Flip, whose Play already goes round.

WHAT IS ASKED, AND HOW IT IS READ
  * Where it is: on a desk beside the speed, in the pill beside Play and in
    the line under the drawing while it plays, the speed before it and full
    screen after it in the line; read from the page's own order, and what is
    painted at its middle (elementFromPoint), not its box. On a phone at the
    end of the bar instead (the owner's pick A on the Undo, reach and Repeat
    page), 8px past the bar's end and centred on it, the bar still a 44px
    grab, inline and in full screen: in the line it needed two rows for most
    drawings, and at 813 the words sat on the drawing. So the line is read
    with the longest words it held on one row before Repeat ("Drawn in 47 min
    · watching at Fit · 94×"): one row, full screen on it.
  * Off to start, its words its tooltip, lit only while on: aria-pressed, the
    title lib/tooltip.js keeps as data-tip, and its painted fill against a
    probe beside it wearing the chosen choice's purple.
  * Off, Play shows the drawing once, and its music stops with it.
  * On, it goes round: read on every frame, the replay's place falls back to
    its start and climbs again, round after round, with no frame held at the
    turn; the music begins again from its loop's start with each round (the
    loop engine's own start, counted), and is playing on every frame between.
    And a turn builds no new layers: from the first turn on no canvas is
    made, the round reseeding the two Play made. A pair for every turn was
    the turn's biggest cost, and on main after #668 one turn held 208 ms;
    the count says so on every box, where the time says so only on a slow one.
  * Turned off mid-round, that round is its last; Stop stops it at once and
    leaves Repeat on for the next Play. Remembered across a reload, and the
    pill and the line say the same.
  * The music drawer's "Play with my drawing" is the Pad's Play, so it goes
    round too.
  * A scrub back mid-play: the music plays on to the drawing's end. It
    counted the timer's ticks before and stopped early (editor_music.js
    drawingAt); with Repeat off as well as on.
  * In full screen the band tones it as it tones its neighbours: the speed's
    glass while off, a pressed full screen's light while on (computed paint).
  * Its glyph reads at 3:1 or more on what is behind it, on and off, light and
    dark, the pill and the line.
  * Posts are as they were: a link page and a post's box keep their own loop
    button and have no Repeat of this kind; Flip has none.
"""
import io
import json
import math
import os
import struct
import sys
import urllib.request
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
    print("No assertions were executed. This is NOT evidence the Pad's Repeat goes round.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: PADREPEAT_PART=where (once, round, off, kept, drawer, scrub,
# band, ink, posts) runs one part. A real run sets none.
PART = os.environ.get("PADREPEAT_PART", "")


def part(name):
    return not PART or PART == name


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
SAYS = {"on": "Repeat: on. Play goes round until you stop it.", "off": "Repeat: off. Play shows it once."}


def _wav(seconds, rate=8000):
    """A pulse twice a second: something to hear go round."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(11000 * math.sin(2 * math.pi * 220 * i / rate) * math.exp(-((2 * i / rate) % 1) * 7)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


SONG = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}

# Every frame: ms since the start, playing, the replay's place, its length,
# and whether the music's loop is playing.
REC = """(ms) => new Promise((done) => { const out = [], t0 = performance.now();
  (function f() { out.push([Math.round(performance.now() - t0), playing ? 1 : 0, playIndex, playTimeline ? playTimeline.length : 0,
                            _waLoop.playing() ? 1 : 0]);
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else done(out); })(); })"""
# Canvases made from the first turn on (Play's own layers come before it), and
# the ink on the drawing as each round ends and two frames into the next: the
# pixels, on a small copy, that differ from the corner's.
TURN_CANVASES = """() => { window.__turnCanvases = 0; window.__turnInk = []; let turned = false;
  const sm = document.createElement('canvas'); sm.width = 96; sm.height = 72;
  const sx = sm.getContext('2d', { willReadFrequently: true }), cv = document.getElementById('canvas');
  const ink = () => { sx.clearRect(0, 0, 96, 72); sx.drawImage(cv, 0, 0, 96, 72);
    const d = sx.getImageData(0, 0, 96, 72).data; let n = 0;
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - d[0]) + Math.abs(d[i + 1] - d[1]) + Math.abs(d[i + 2] - d[2]) + Math.abs(d[i + 3] - d[3]) > 60) n++;
    return n; };
  const ce = Document.prototype.createElement;
  Document.prototype.createElement = function (t) {
    if (turned && String(t).toLowerCase() === 'canvas') window.__turnCanvases++;
    return ce.apply(this, arguments); };
  const again = window.replayAgain;
  window.replayAgain = function () { turned = true; const end = ink(), r = again.apply(this, arguments);
    requestAnimationFrame(() => requestAnimationFrame(() => window.__turnInk.push([end, ink()])));
    return r; }; }"""
# The loop engine's starts, and where in its clip each began.
STARTS = """() => { window.__wa = []; const s = _waLoop.start;
  _waLoop.start = function (f, off) { window.__wa.push([performance.now(), off || 0]); return s.apply(this, arguments); }; }"""
# One Repeat button: in the page's order, painted, lit, and saying what.
BTN = """(sel) => { const b = document.querySelector(sel); if (!b) return null;
  const r = b.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const p = document.createElement('i'); p.style.background = 'var(--seg-on-fill)'; b.parentNode.appendChild(p);
  const lit = getComputedStyle(b).backgroundColor === getComputedStyle(p).backgroundColor; p.remove();
  const prev = b.previousElementSibling, next = b.nextElementSibling;
  return { w: Math.round(r.width), h: Math.round(r.height), painted: !!at && (at === b || b.contains(at)),
           pressed: b.getAttribute('aria-pressed'), name: b.getAttribute('aria-label'), lit,
           says: b.getAttribute('data-tip') || b.title, prev: prev && prev.className, next: next && next.className }; }"""


# On a phone, the Repeat at the bar's end: its box, painted at its middle,
# how far past the bar's end, how far its middle from the bar's, where its
# right edge sits against the line's (where the bar ended before), the bar's
# grab, and whether the line's own Repeat shows.
BAR_END = """() => { const r = document.querySelector('.rl-repeat.at-bar'), s = document.getElementById('playScrub'),
    ln = document.getElementById('padLine'), own = document.querySelector('#padLine .rl-repeat');
  if (!r || !s) return null;
  const a = r.getBoundingClientRect(), q = s.getBoundingClientRect(), t = getComputedStyle(s, '::after'), l = ln.getBoundingClientRect();
  const at = document.elementFromPoint(a.left + a.width / 2, a.top + a.height / 2);
  return { w: Math.round(a.width), h: Math.round(a.height), painted: !!at && (at === r || r.contains(at)), pressed: r.getAttribute('aria-pressed'),
           name: r.getAttribute('aria-label'), gap: Math.round(a.left - q.right), mid: Math.round(((a.top + a.bottom) - (q.top + q.bottom)) / 2),
           edge: Math.round(a.right - l.right), grab: Math.round(q.height - parseFloat(t.top) - parseFloat(t.bottom)),
           inLine: !!own && own.getClientRects().length > 0 }; }"""
# The line under the drawing with words of its own: one row, and the way into
# full screen on it.
LINE_ROW = """([a, sp]) => { const t = document.querySelector('#padLine .rl-text'), f = document.querySelector('#padLine .full-btn');
  t.querySelector('.rl-drawn').innerHTML = '<span class="rl-m">Drawn in </span><b>' + a + '</b><span class="rl-m"> · </span>';
  t.querySelector('.rl-speed > span').textContent = sp;
  const r = t.getBoundingClientRect(), b = f.getBoundingClientRect();
  return { h: Math.round(r.height), onRow: Math.abs((b.top + b.bottom) / 2 - (r.top + r.bottom) / 2) < 4 }; }"""


def turns(rec):
    """The frames at which the replay fell back to its start."""
    return [i for i in range(1, len(rec)) if rec[i][2] < rec[i - 1][2] - max(2, rec[i - 1][3] / 2)]


def pad(b, opts=DESK, ctx=None, repeat=None, song=SONG, rate="2"):
    """The Pad with a drawing of three strokes through real pointer events,
    Done, its song added, the speed at `rate`, and Repeat stored as `repeat`
    ('1', '0' or None for never set) before it boots."""
    c = ctx or waits.instrument(b.new_context(**opts))
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    pg.evaluate("""([r, rep]) => { localStorage.setItem('skribl_replay_rate', r);
      if (rep === null) localStorage.removeItem('skribl_replay_repeat'); else localStorage.setItem('skribl_replay_repeat', rep); }""", [rate, repeat])
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    box = pg.locator("#canvas").bounding_box()
    for k in range(3):
        pg.mouse.move(box["x"] + 60, box["y"] + 100 + k * 70); pg.mouse.down()
        for i in range(36):
            pg.mouse.move(box["x"] + 60 + i * 6, box["y"] + 100 + k * 70 + math.sin(i / 6) * 20); pg.wait_for_timeout(16)
        pg.mouse.up(); pg.wait_for_timeout(150)
    pg.click("#recordBtn"); pg.wait_for_timeout(400)
    if song:
        browsing.pad_drawer(pg, "music")
        pg.set_input_files("#musicInput", song)
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer",
                             timeout=20000)
        waits.settle(pg, 400)
        browsing.pad_drawer_close(pg)
    pg.evaluate(STARTS)
    return c, pg, errs


def play(pg, sel="#playBtn"):
    pg.click(sel)
    pg.wait_for_timeout(60)
    return pg.evaluate("() => playTotal / replayRate")


def lap_ok(rec, ts):
    """No frame held at a turn: how long the replay sat at its last place
    before the next round began, and at its first place after, each from the
    first frame it was there to the first frame it moved on, no more than
    three frames. (Two frames side by side are always a frame apart: a hold
    shows as frames that do not move.)"""
    gaps = sorted(b2[0] - a2[0] for a2, b2 in zip(rec, rec[1:]))
    frame = gaps[len(gaps) // 2] if gaps else 16
    at = []
    for i in ts:
        k = i - 1
        while k > 0 and rec[k - 1][2] == rec[i - 1][2]:
            k -= 1
        j = i
        while j + 1 < len(rec) and rec[j + 1][2] == rec[i][2]:
            j += 1
        at.append(max(rec[i][0] - rec[k][0], rec[min(j + 1, len(rec) - 1)][0] - rec[i][0]))
    return all(g <= max(50, 3 * frame) for g in at), at, frame


with sync_playwright() as p:
    b = p.chromium.launch()

    if part("where"):
        print("\nREPEAT — where it is")
        c, pg, errs = pad(b, song=None)
        d0 = pg.evaluate(BTN, "#padSpeed .rl-repeat")
        check("desk: Repeat sits in the pill beside Play, after the speed, painted, off to start, its words its tooltip",
              d0 and d0["painted"] and d0["prev"] == "rl-speed" and d0["pressed"] == "false" and not d0["lit"]
              and d0["name"] == "Repeat" and d0["says"] == SAYS["off"] and (d0["w"], d0["h"]) == (32, 26), str(d0))
        play(pg)
        l0 = pg.evaluate(BTN, "#padLine .rl-repeat")
        e0 = pg.evaluate(BAR_END)
        check("desk: ...and in the line under the drawing while it plays, between the speed and full screen, and none at the bar's end",
              l0 and l0["painted"] and l0["prev"] == "rl-speed" and l0["next"] == "full-btn" and l0["pressed"] == "false"
              and e0 and e0["w"] == 0 and e0["inLine"], f"{l0}; at the bar's end {e0}")
        check("no page errors where Repeat is", not errs, "; ".join(errs[:2]))
        c.close()
        c, pg, errs = pad(b, opts=PHONE, song=None, rate="1")
        rest = pg.evaluate("() => { const b = document.querySelector('#padSpeed .rl-repeat'); return !!b && b.getClientRects().length > 0; }")
        play(pg)
        pg.wait_for_timeout(200)
        e1 = pg.evaluate(BAR_END)
        check("phone: Repeat sits at the end of the bar while it plays, 34 by 27, painted, off, 8px past the bar's end and centred on it, "
              "where the bar ended; the bar still a 44px grab, and none in the line",
              e1 and e1["painted"] and (e1["w"], e1["h"]) == (34, 27) and e1["pressed"] == "false" and e1["name"] == "Repeat"
              and e1["gap"] == 8 and abs(e1["mid"]) <= 1 and e1["edge"] == 0 and e1["grab"] >= 44 and not e1["inLine"] and not rest,
              f"{e1}; the desk pill's shown on a phone: {rest}")
        # The longest words the line held on one row before Repeat, at 402.
        rows = [pg.evaluate(LINE_ROW, w) for w in (["47 min", "8×"], ["59 min", "16×"], ["47 min", "Fit · 94×"])]
        check("phone: ...so the line under the drawing keeps one row, full screen on it, up to 'Drawn in 47 min · watching at Fit · 94×', as before Repeat",
              all(r["h"] < 34 and r["onRow"] for r in rows), str(rows))
        pg.evaluate("() => document.querySelector('#padLine .full-btn').click()"); pg.wait_for_timeout(900)
        e2 = pg.evaluate(BAR_END)
        check("phone: in full screen, Repeat is at the bar's end in the band, painted, on the bar's row, 8px past it",
              e2 and e2["painted"] and e2["gap"] == 8 and abs(e2["mid"]) <= 1 and not e2["inLine"], str(e2))
        check("no page errors at the bar's end", not errs, "; ".join(errs[:2]))
        c.close()

    if part("once"):
        print("\nREPEAT — off, Play shows it once")
        c, pg, errs = pad(b)
        ms = play(pg)
        rec = pg.evaluate(REC, int(ms + 900))
        wa = pg.evaluate("() => window.__wa.length")
        ended = next((r[0] for r in rec if not r[1]), None)
        check("off: Play shows the drawing once and stops at its end, the music with it",
              not turns(rec) and ended is not None and abs(ended - ms) < 250 and not rec[-1][4] and wa == 1,
              f"a replay of {ms:.0f}ms ended at {ended}ms; rounds again {len(turns(rec))}; music on at the end {rec[-1][4]}; music starts {wa}")
        c.close()

    if part("round"):
        print("\nREPEAT — on, Play goes round")
        c, pg, errs = pad(b)
        pg.click("#padSpeed .rl-repeat"); pg.wait_for_timeout(250)
        pg.evaluate(TURN_CANVASES)
        d1 = pg.evaluate(BTN, "#padSpeed .rl-repeat")
        kept = pg.evaluate("() => localStorage.getItem('skribl_replay_repeat')")
        check("pressed, Repeat is on and lit, saying so, and remembered",
              d1["pressed"] == "true" and d1["lit"] and d1["says"] == SAYS["on"] and kept == "1", f"{d1}; stored {kept!r}")
        ms = play(pg)
        rec = pg.evaluate(REC, int(ms * 3.5))
        ts = turns(rec)
        ok, at, frame = lap_ok(rec, ts)
        wa = pg.evaluate("() => window.__wa")
        check("on: Play goes round, round after round, playing all the while, no frame held at a turn",
              len(ts) >= 3 and all(r[1] for r in rec) and ok,
              f"rounds begun again {len(ts)} in {rec[-1][0]}ms (a round {ms:.0f}ms); playing throughout {all(r[1] for r in rec)}; "
              f"at each turn {at}ms (a frame {frame}ms)")
        check("...the music begins again from its loop's start with each round, and plays on every frame between",
              len(wa) == len(ts) + 1 and all(abs(x[1]) < 1e-9 for x in wa) and all(r[4] for r in rec[5:]),
              f"music starts {len(wa)} for {len(ts)} rounds again, from {[round(x[1], 3) for x in wa]}; "
              f"frames with it off {sum(1 for r in rec[5:] if not r[4])}")
        made = pg.evaluate("() => [window.__turnCanvases, strokeLayersOn(), window.__turnInk]")
        check("...and a turn builds no new layers: from the first turn on, no canvas is made (the round reseeds Play's two)",
              len(ts) >= 3 and made[1] and made[0] == 0,
              f"canvases made over {len(ts)} turns: {made[0]}; layers on {made[1]}")
        check("...and each round starts from the bare canvas: two frames in, a fifth of the ink the round before ended with, or less",
              len(made[2]) >= 3 and all(e > 40 and a * 5 <= e for e, a in made[2]),
              f"ink as a round ended, and two frames into the next: {made[2]}")
        # Off mid-round: this round is the last.
        pg.click("#padSpeed .rl-repeat"); pg.wait_for_timeout(30)
        rec2 = pg.evaluate(REC, int(ms + 900))
        ended = next((r[0] for r in rec2 if not r[1]), None)
        check("turned off mid-round, that round is its last: it ends, the music with it, and goes round no more",
              not turns(rec2) and ended is not None and ended <= ms + 250 and not rec2[-1][4],
              f"ended {ended}ms after (a round {ms:.0f}ms); rounds again {len(turns(rec2))}; music on at the end {rec2[-1][4]}")
        # Stop mid-round: at once, and Repeat stays on for the next Play.
        pg.click("#padSpeed .rl-repeat"); pg.wait_for_timeout(100)
        play(pg); pg.wait_for_timeout(int(ms * 1.4))
        pg.click("#playBtn"); pg.wait_for_timeout(250)
        st = pg.evaluate("() => ({ playing, music: _waLoop.playing(), on: document.querySelector('#padSpeed .rl-repeat').getAttribute('aria-pressed') })")
        check("Stop stops it at once, the music with it, and leaves Repeat on for the next Play",
              not st["playing"] and not st["music"] and st["on"] == "true", str(st))
        check("no page errors going round", not errs, "; ".join(errs[:2]))
        c.close()

    if part("kept"):
        print("\nREPEAT — remembered, and one choice in both places")
        c, pg, errs = pad(b, repeat="1", song=None)
        a = pg.evaluate(BTN, "#padSpeed .rl-repeat")
        play(pg)
        pg.click("#padLine .rl-repeat"); pg.wait_for_timeout(200)
        both = pg.evaluate("() => [...document.querySelectorAll('.rl-repeat')].map(x => x.getAttribute('aria-pressed'))")
        kept = pg.evaluate("() => localStorage.getItem('skribl_replay_repeat')")
        pg.click("#playBtn"); pg.wait_for_timeout(150)
        browsing.goto(pg, BASE, "/")
        z = pg.evaluate(BTN, "#padSpeed .rl-repeat")
        check("Repeat is remembered across a reload, on and off, and the pill, the line and the bar's end say the same",
              a["pressed"] == "true" and a["lit"] and both == ["false", "false", "false"] and kept == "0" and z["pressed"] == "false" and not z["lit"],
              f"booted on: {a['pressed']}; the line pressed: {both}, stored {kept!r}; after a reload {z['pressed']}")
        c.close()

    if part("drawer"):
        print("\nREPEAT — the music drawer's Play with my drawing")
        c, pg, errs = pad(b, repeat="1")
        browsing.pad_drawer(pg, "music")
        ms = pg.evaluate("() => { const t = buildPlaybackTimeline(); return t.length ? t[t.length - 1].playT / replayRate : 0; }")
        pg.click("#musicPlayBtn"); pg.wait_for_timeout(60)
        rec = pg.evaluate(REC, int(ms * 2.6))
        check("with Repeat on, the music drawer's Play with my drawing goes round too",
              len(turns(rec)) >= 2 and all(r[1] for r in rec), f"rounds again {len(turns(rec))} in {rec[-1][0]}ms (a round {ms:.0f}ms)")
        c.close()

    if part("scrub"):
        print("\nREPEAT — a scrub back, and the music to the drawing's end")
        for rep in ("0", "1"):
            c, pg, errs = pad(b, repeat=rep, rate="1")
            ms = play(pg)
            pg.wait_for_timeout(int(ms * 0.75))
            pg.evaluate("() => editorSeek(0.1)")
            rec = pg.evaluate(REC, int(ms * 0.95))
            # Up to the drawing's end (or the round's turn), the music plays.
            stop = turns(rec)[0] if turns(rec) else next((i for i, r in enumerate(rec) if not r[1]), len(rec))
            gone = [r[0] for r in rec[:stop] if r[1] and not r[4]]
            check(f"Repeat {'on' if rep == '1' else 'off'}: scrubbed back from three quarters to a tenth, the music plays on to the drawing's end",
                  stop > 5 and not gone, f"frames with the drawing playing and the music gone: {len(gone)}, from {gone[:1]}ms of {rec[stop - 1][0]}ms")
            c.close()

    if part("band"):
        print("\nREPEAT — in full screen, toned as its neighbours")
        TONE = """() => { const q = (s) => document.querySelector('.watch-band ' + s);
          const t = (e) => e ? { tone: e.classList.contains('t-dark') ? 'dark' : e.classList.contains('t-light') ? 'light' : '',
                                 bg: getComputedStyle(e).backgroundColor, ink: getComputedStyle(e).color } : null;
          return { smart: !!document.querySelector('.watch-band.is-smart'), rep: t(q('.rl-repeat')), speed: t(q('.rl-speed')), full: t(q('.full-btn')),
                   pressed: q('.rl-repeat') && q('.rl-repeat').getAttribute('aria-pressed') }; }"""
        for theme in ("light", "dark"):
            ctx = waits.instrument(b.new_context(color_scheme=theme, **PHONE))
            c, pg, errs = pad(b, ctx=ctx, song=None, rate="0.25")
            play(pg); pg.wait_for_timeout(300)
            pg.evaluate("() => document.querySelector('#padLine .full-btn').click()"); pg.wait_for_timeout(1200)
            off = pg.evaluate(TONE)
            pg.evaluate("() => document.querySelector('.watch-band .rl-repeat').click()"); pg.wait_for_timeout(400)
            on = pg.evaluate(TONE)
            same = lambda x, y: bool(x and y and x["tone"] and x["tone"] == y["tone"] and x["bg"] == y["bg"] and x["ink"] == y["ink"])   # noqa: E731
            check(f"{theme}: in full screen, Repeat wears the speed's glass while off and a pressed full screen's light while on",
                  off["smart"] and same(off["rep"], off["speed"]) and on["pressed"] == "true" and same(on["rep"], on["full"]),
                  f"off {off['rep']} beside the speed {off['speed']}; on {on['rep']} beside full screen {on['full']}")
            c.close()

    if part("ink"):
        print("\nREPEAT — its glyph reads")
        INK = """(sel) => {
          const parse = (s) => { const m = s.match(/^rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
          const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a }; };
          const ground = (el) => { const l = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { l.push(c); if (c.a >= 0.999) break; } }
            let acc = { r: 255, g: 255, b: 255, a: 1 }; for (let i = l.length - 1; i >= 0; i--) acc = over(l[i], acc); return acc; };
          const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
          const ratio = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
          const el = document.querySelector(sel); const g = ground(el);
          return Math.round(ratio(over(parse(getComputedStyle(el).color), g), g) * 100) / 100; }"""
        seen = {}
        for theme in ("light", "dark"):
            for label, opts, sel in (("desk pill", DESK, "#padSpeed .rl-repeat"), ("desk line", DESK, "#padLine .rl-repeat"),
                                     ("phone, at the bar's end", PHONE, ".rl-repeat.at-bar")):
                ctx = waits.instrument(b.new_context(color_scheme=theme, **opts))
                c, pg, errs = pad(b, ctx=ctx, song=None, rate="0.25")
                if label != "desk pill":
                    play(pg); pg.wait_for_timeout(300)
                pg.mouse.move(2, 2)
                off = pg.evaluate(INK, sel)
                pg.evaluate("(s) => document.querySelector(s).click()", sel); pg.wait_for_timeout(300)
                on = pg.evaluate(INK, sel)
                seen[f"{theme}, {label}"] = (off, on)
                c.close()
        check("Repeat's glyph reads at 3:1 or more on what is behind it, off and on, light and dark, the pill, the line and the bar's end",
              all(min(v) >= 3 for v in seen.values()), "; ".join(f"{k}: off {v[0]}:1, on {v[1]}:1" for k, v in seen.items()))

    if part("ring"):
        print("\nREPEAT — on is outlined")
        # The owner, of the mock: "rather than solid purple on snap and taller
        # click and repeat I like the outline, but not so thick". Lit, Repeat
        # was told from off by its tint alone; on now wears a 1px ring (the
        # line's and the pill's in --ui-hi, the band's in the pressed full
        # screen's edge). Read off the pixels at 2x: the edge on against the
        # same edge off.
        from PIL import Image as _RImg
        import io as _rio
        _RLUM = lambda c: sum(w * ((v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4)   # noqa: E731
                              for w, v in zip((0.2126, 0.7152, 0.0722), c[:3]))
        _rr = lambda a, b: (max(_RLUM(a), _RLUM(b)) + 0.05) / (min(_RLUM(a), _RLUM(b)) + 0.05)   # noqa: E731
        _RECT = "(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
        # The left edge at mid-height: the band's glass lights its own top edge
        # when off (an inset highlight), which the ring is not about.
        _edge = lambda img, r: img.getpixel((int(r[0] * 2) + 1, int((r[1] + r[3] / 2) * 2)))   # noqa: E731
        rings = {}
        for theme in ("light", "dark"):
            for label, opts, sel in (("desk pill", dict(DESK, device_scale_factor=2), "#padSpeed .rl-repeat"),
                                     ("desk line", dict(DESK, device_scale_factor=2), "#padLine .rl-repeat"),
                                     ("full screen", dict(PHONE), ".watch-band .rl-repeat")):
                ctx = waits.instrument(b.new_context(color_scheme=theme, **opts))
                c, pg, errs = pad(b, ctx=ctx, song=None, rate="0.25")
                if label != "desk pill":
                    play(pg); pg.wait_for_timeout(300)
                if label == "full screen":
                    pg.evaluate("() => document.querySelector('#padLine .full-btn').click()"); pg.wait_for_timeout(1200)
                pg.mouse.move(2, 2)
                r0 = pg.evaluate(_RECT, sel); a0 = _RImg.open(_rio.BytesIO(pg.screenshot())).convert("RGB")
                pg.evaluate("(s) => document.querySelector(s).click()", sel); pg.wait_for_timeout(350)
                r1 = pg.evaluate(_RECT, sel); a1 = _RImg.open(_rio.BytesIO(pg.screenshot())).convert("RGB")
                on = pg.evaluate("(s) => document.querySelector(s).getAttribute('aria-pressed')", sel)
                rings[f"{theme}, {label}"] = (round(_rr(_edge(a1, r1), _edge(a0, r0)), 2), on)
                c.close()
        check("Repeat, on, is outlined: its edge at least 3:1 against the same edge off, in the pill, the line and the full-screen band, light and dark",
              all(v[1] == "true" and v[0] >= 3 for v in rings.values()), "; ".join(f"{k}: {v[0]}:1 ({v[1]})" for k, v in rings.items()))

    if part("posts"):
        print("\nREPEAT — posts as they were, and not on Flip")
        pts = [{"x": 100 + i * 8, "y": 200 + math.sin(i / 5) * 30, "color": "#1f1b2e", "size": 6, "t": i * 25, "start": i == 0} for i in range(60)]
        payload = {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": "tight", "fps": None,
                   "canvasSize": {"cssWidth": 816, "cssHeight": 612}, "title": "repeat",
                   "frames": [{"strokes": pts, "strokeGroups": [60], "background": {"color": "#f6f2ea"}}]}
        req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        pid = json.loads(urllib.request.urlopen(req, timeout=20).read())["id"]
        pg = b.new_page(**DESK)
        browsing.goto(pg, BASE, f"/s/{pid}")
        link = pg.evaluate("() => ({ loop: !!document.getElementById('playerLoopBtn'), ours: document.querySelectorAll('.rl-repeat').length })")
        browsing.goto(pg, BASE, "/feed")
        pg.wait_for_timeout(800)
        feed = pg.evaluate("() => ({ loop: document.querySelectorAll('.skribl-inline-loop').length, ours: document.querySelectorAll('.rl-repeat').length })")
        browsing.goto(pg, BASE, "/flip")
        flip = pg.evaluate("() => document.querySelectorAll('.rl-repeat').length")
        check("a link page and a post's box keep their own loop button and have no Repeat of the Pad's; Flip has none",
              link["loop"] and not link["ours"] and feed["loop"] >= 1 and not feed["ours"] and not flip,
              f"link page {link}; feed {feed}; Flip's {flip}")
        pg.close()

    b.close()

summarise_and_exit()
