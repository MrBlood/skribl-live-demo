#!/usr/bin/env python3
"""The music drawer's view and its four doors (lib/musicdrawer.js), on the Pad and on Flip.

The owner, of the mock: "I like D", then "All yes" to the whole drawer. The
view is the timeline, the one line under it and the pair that plays; under
them four tiles, Length, Beat, Restart and Exact times, the draw drawer's
(lib/drawtiles.js), each saying what it is set to and opening its group under
it, one at a time. They were More, one card over all four (and before it,
three levels): this was verify_musicmore.py, and before that
verify_musiclevels.py. verify_musictimeline.py has how the timeline, the
Restart view and Cut on silence work; verify_music.py how each control works
(the previews, the switch, Fit's sum on Flip) and verify_musicbeat.py the
beat; this keeps where each one lives, what the drawer says, and the doors
themselves.

The rows:

  THE VIEW AND THE DOORS. A new drawer opens on the view, its four doors shut.
  Each door opens its own group (Length: Skribl's pick, Fit my drawing, Whole
  song, Lock the length; Beat: Tap the beat; Restart: Smooth restart, the
  Restart view, its length, Hear the restart, Cut on silence; Exact times: the
  two times and Each press), and what a shut door holds is `hidden` (so out of
  the Tab order too). One door at a time: another's tile swaps them. Opening
  and closing keep the loop. A door unfolds and folds away joined to its tile,
  as the draw drawer's do, and at once under Reduce Motion; no line shows
  where they join, read on the screenshot's pixels in light and dark, and the
  card's side edges run unbroken past it. The doors start shut every time: on
  a load (More's old remembered key too), and on every opening of the drawer,
  Photo and back included. Each tile says what its door is set to, in words
  that fit it on a 390px phone and a desk, and Skribl's mark is on the Length
  tile's picture while the loop is Skribl's pick. The row runs edge to edge
  with the timeline and the pair above it, and an open door's group as wide,
  on a desk as on a phone (it stopped at 520px, short of them on a desk).

  THE ONE LINE AND SKRIBL'S PICK. A new song starts on Skribl's pick: the
  first 20 seconds (the whole song when it is shorter), with a smooth
  restart; on the Pad a drawing already there sets the length instead, what
  is heard as long as the drawing. The line says the length heard, the beats
  once there is a tempo, and against the drawing; in the Length door
  Skribl's pick is lit while the loop is it. Changed, the pick is the way
  back, and the loop's Undo takes the way back back (the Undo itself is
  verify_musicundo's; the Length door's own, for eight seconds, is gone).
  Nobody is told they did
  something: a drawing that changed under the pick says only that. The
  line's height never changes as it says other things. A song a draft brings
  back keeps the draft's loop.

  THE LENGTHS. Fit counts the smooth restart (what is heard is as long as the
  drawing; Match Drawing Time fell short by the crossfade). Whole song loops
  all of a short song and a long one's first 20 seconds, and says which. The
  one the loop is wears the one tint, one at a time; where two are the same
  loop (a short song's pick is the whole song), the one pressed, and neither
  moves the loop or offers an Undo. With nothing drawn Fit is off and says
  why, and wakes when a drawing is made with the drawer open.

  SMOOTH RESTART. One switch, on at its last length and off to a clean cut;
  the line counts what is heard.

  EXACT TIMES. A typed time moves its end (a comma is a point); a time that
  is not one puts the loop's own back. - and + move as far as Each press
  says: untouched 0.1s, or a bar once there is a tempo while Snap to the beat
  is on; 0.01s or 0.1s picked and kept; a bar there only once there is a
  tempo; a new song untouched. Their names say the step. Lock the
  length moves both ends together. Every field that takes text is 16px (A11Y
  11b; these are built hidden).

  THE TIMELINE FOLLOWS YOU. Exact times opens under the timeline, so on a
  phone and a desk, scrolled as far as the page goes, what it edits is still
  on the screen, all of it, and the copy stays away. Where it can scroll away
  (a small phone held sideways), with the timeline scrolled up past the
  header a copy of it shows under the header, on the drawer to the pixel (on
  a desk the page's scrollbar gutter moves where a fixed box's left counts
  from), painted over what passes under it and under the header; with the
  timeline on the screen it stays away. It frames the loop, the loop most of
  it, its ends the timeline's sharp lines (as wide as 1.5px rounds to on the
  screen, the ground either side flat, read off its canvas), and says the one
  line's length and beats. A press of End + moves its
  end at once; then it eases to frame the new loop, frame by frame. It glides
  in. A tap on it goes back up to the timeline, the drawer still open (Flip's
  tap-away rule closed it), and it goes. At once under Reduce Motion.

  PLAY. Play with my drawing is the editor's own Play and follows it however
  it is pressed; with nothing drawn it waits, and Hear the loop, beside it,
  plays the music on its own (verify_musicbeat has the rest).

  KIND, NOT JUMPY. A door opened as a song lands never takes the tile just
  tapped out of sight, and closing one from the drawer's end glides: the tile
  is read on every frame and never leaps.

Checked red per component: see DECISIONS.md for which mutation turned which
row red.
"""
import io
import math
import os
import re
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
    print("No assertions were executed. This is NOT evidence the music drawer has its view and its four doors.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICDOORS_ONLY=Pad (or Flip) runs one editor, and
# MUSICDOORS_PART=doors (words, pick, line, picks, smooth, exact, follow, play, kind)
# one part, so a row can be shown red in seconds. A real run sets neither.
ONLY = os.environ.get("MUSICDOORS_ONLY", "")
PART = os.environ.get("MUSICDOORS_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def part(name):
    return not PART or PART == name


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if part(name) else []
DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
SIDEWAYS = dict(viewport={"width": 874, "height": 402}, device_scale_factor=2, is_mobile=True, has_touch=True)
# An iPhone SE held sideways, its 375 less Safari's bar: where the timeline
# can scroll away under Exact times.
SMALL_SIDEWAYS = dict(SIDEWAYS, viewport={"width": 667, "height": 340})
WORK = {"Pad": "drawing", "Flip": "animation"}
PLAY = {"Pad": "#playBtn", "Flip": "#play"}


def _wav(seconds, rate=8000, f0=220.0):
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * (f0 + 30 * i / rate) * i / rate)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


SHORT = {"name": "short.wav", "mimeType": "audio/wav", "buffer": _wav(6.0)}
LONG = {"name": "long.wav", "mimeType": "audio/wav", "buffer": _wav(30.0, f0=330.0)}

# Flip's pages, each drawn, each held `hold` frames (lib/holdtiming.js).
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""
DRAWING = {"Pad": "() => strokes.length ? getPlaybackDuration() / 1000 : 0",
           "Flip": "() => window.SkriblHold.plan(frames, fps, docLoop).cycle / 1000"}
TRIM = "() => ({ s: trimStart, e: trimEnd, d: audioDuration, xf: loopCrossfadeMs })"
# What the drawer says. `pick`: Skribl's pick is lit, the loop is it; `back`:
# it is the way back, there to tap; `spark`: Skribl's mark on the Length tile.
SAID = """() => { const q = (id) => document.getElementById(id), card = q('musicPickCard');
  const tile = (k) => document.querySelector('#musicDoors .dp-tile[data-dp="' + k + '"]');
  return { line: q('musicPickText').textContent, pick: card.getAttribute('aria-pressed') === 'true',
           back: card.getAttribute('aria-pressed') !== 'true' && !card.disabled, undo: !q('musicUndo').disabled,
           pickSub: q('musicPickSub').textContent, spark: !q('musicLengthSpark').hidden,
           tiles: ['length', 'beat', 'restart', 'exact'].map((k) => tile(k).querySelector('.dp-v').textContent),
           fit: q('matchDrawingBtn').getAttribute('aria-pressed'), fitOff: q('matchDrawingBtn').disabled, fitSub: q('musicFitSub').textContent,
           whole: q('musicWholeBtn').getAttribute('aria-pressed'), wholeName: q('musicWholeName').textContent, wholeSub: q('musicWholeSub').textContent,
           play: q('musicPlayLabel').textContent,
           step: [...document.querySelectorAll('#musicStepSeg button')].filter(b => !b.hidden).map(b => (b.classList.contains('on') ? '*' : '') + b.textContent + (b.disabled ? ' (dim)' : '')).join(' · '),
           smooth: q('musicSmooth').getAttribute('aria-checked'), smoothSub: q('musicSmoothSub').textContent }; }"""
# Shown: no [hidden] on the way up, and a box. Hidden: a [hidden] on the way up.
SHOWN = """(ids) => ids.filter((id) => { const el = document.getElementById(id);
  return !!el && !el.closest('[hidden]') && el.getClientRects().length > 0; })"""
# Where the Restart door's tile is, against the pinned header (0 where the header scrolls away) and the screen.
TILE = "document.querySelector('#musicDoors .dp-tile[data-dp=\"restart\"]')"
SIGHT = """() => { const s = """ + TILE + """.getBoundingClientRect(), h = document.querySelector('.header');
  const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
  return { seg: Math.round(s.top), header: Math.round(top), vh: innerHeight }; }"""
VIEW = ["musicTimeline", "musicPickLine", "musicPlayBtn", "previewLoopBtn", "musicDoors"]
DOORS = {"length": ["musicDoorLength", "musicPickCard", "matchDrawingBtn", "musicWholeBtn", "musicLock"],
         "beat": ["musicDoorBeat", "musicTapBtn"],
         "restart": ["musicDoorRestart", "musicSmooth", "musicRestart", "crossfadeSlider", "testSeamBtn", "musicCut"],
         "exact": ["musicDoorExact", "startReadout", "endReadout", "musicStepSeg"]}
INSIDE = sorted(i for ids in DOORS.values() for i in ids)
ALL = sorted(set(VIEW + INSIDE))
DOOR_NAMES = {"length": "Length", "beat": "Beat", "restart": "Restart", "exact": "Exact"}


def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=SHORT, ctx=None, opts=DESK, door=None):
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


# Where an open door's tile meets what it opens, as painted, read as
# verify_drawtiles reads the draw drawer's tiles (they are the same tiles): the
# largest step from the card's colour over the rows from the tile's bottom
# border to 3px into the card, across the tile's inside; and, where the tile
# is at an end of the row, the smallest step on the card's side edge at the
# joint (0 is a break in the edge, which a cover the tile's whole width
# paints). The joint holds still for its photograph: read, photograph, read
# again, and the photograph counts only when the two reads agree.
JOINT = """(k) => { const t = document.querySelector('#musicDoors .dp-tile[data-dp="' + k + '"]'), p = document.getElementById(t.getAttribute('aria-controls'));
  let a = t.getBoundingClientRect();
  if (a.bottom < 8 || a.bottom > innerHeight - 8) { t.scrollIntoView({ block: 'center', behavior: 'instant' }); a = t.getBoundingClientRect(); }
  const z = p.getBoundingClientRect();
  return { a: [a.left, a.top, a.right, a.bottom], z: [z.left, z.top, z.right, z.bottom], card: getComputedStyle(p).backgroundColor }; }"""


def seam(pg, k, dpr=1):
    from PIL import Image
    for _ in range(8):
        j = pg.evaluate(JOINT, k)
        a, z = j["a"], j["z"]
        x0, y0 = min(a[0], z[0]) - 2, a[3] - 6
        im = Image.open(io.BytesIO(pg.screenshot(clip={"x": x0, "y": y0, "width": max(a[2], z[2]) + 2 - x0, "height": 14}))).convert("RGB")
        j2 = pg.evaluate(JOINT, k)
        if all(abs(u - v) <= 0.5 for u, v in zip(j["a"] + j["z"], j2["a"] + j2["z"])):
            break
        pg.wait_for_timeout(250)
    card = [int(v) for v in re.findall(r"\d+", j["card"])[:3]]
    w, h = im.size

    def step(x, y):
        c = im.getpixel((min(w - 1, max(0, int((x - x0) * dpr))), min(h - 1, max(0, int((y - y0) * dpr)))))
        return max(abs(c[i] - card[i]) for i in range(3))
    inside = [a[0] + 2 + i / dpr for i in range(int((a[2] - a[0] - 4) * dpr))]
    worst = max(step(x, a[3] - 1 + i / dpr) for i in range(int(4 * dpr)) for x in inside)
    edges = {side: min(step(col, a[3] - 4 + i / dpr) for i in range(int(8 * dpr)))
             for side, xa, xz, col in (("left", a[0], z[0], a[0] + .5 / dpr), ("right", a[2], z[2], a[2] - .5 / dpr))
             if abs(xa - xz) < .75}
    return worst, edges


def press(pg, sel, ms=200):
    """A real click on a control that may be missing from a broken build: a
    row then says so in red rather than the run stopping on a timeout."""
    try:
        pg.click(sel, timeout=3000)
    except Exception:
        return False
    pg.wait_for_timeout(ms)
    return True


with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("\nMUSIC DOORS — the view, and its four doors")
    TILES = """() => [...document.querySelectorAll('#musicDoors .dp-tile')].map((t) => [t.dataset.dp, t.querySelector('.dp-k').textContent,
        t.getAttribute('aria-expanded'), t.getAttribute('aria-controls')])"""
    WHERE = """() => [document.getElementById('musicDoors').dataset.col || null, document.getElementById('musicDetail').dataset.door,
        [...document.querySelectorAll('#musicDoors .dp-tile')].map((t) => t.getAttribute('aria-expanded') === 'true' ? 1 : 0).join('')]"""
    for _n, _p in eds("doors"):
        c, pg, errs = editor(b, _n, _p)
        closed = set(pg.evaluate(SHOWN, ALL))
        tiles = pg.evaluate(TILES)
        check(f"{_n}: a new drawer opens on the view: the timeline, the one line, the pair that plays and four doors, each shut",
              closed == set(VIEW) and [t[:3] for t in tiles] == [[k, DOOR_NAMES[k], "false"] for k in DOORS]
              and all(t[3] == DOORS[t[0]][0] for t in tiles) and pg.evaluate(WHERE) == [None, "none", "0000"],
              f"extra {sorted(closed - set(VIEW))}, missing {sorted(set(VIEW) - closed)}; the tiles {tiles}; {pg.evaluate(WHERE)}")
        opened, where = {}, {}
        for k in DOORS:
            set_door(pg, k)
            opened[k] = set(pg.evaluate(SHOWN, ALL)) - set(VIEW)
            where[k] = pg.evaluate(WHERE)
        check(f"{_n}: each door opens its own group, one at a time: another's tile swaps them",
              all(opened[k] == set(DOORS[k]) for k in DOORS)
              and [where[k] for k in DOORS] == [["0", "length", "1000"], ["1", "beat", "0100"], ["2", "restart", "0010"], ["3", "exact", "0001"]],
              "; ".join(f"{k}: extra {sorted(opened[k] - set(DOORS[k]))}, missing {sorted(set(DOORS[k]) - opened[k])}, {where[k]}" for k in DOORS))
        set_door(pg, None)
        pg.wait_for_timeout(300)
        tab = pg.evaluate("(ids) => ids.filter((id) => !document.getElementById(id).closest('[hidden]'))", INSIDE)
        check(f"{_n}: what a shut door holds is hidden, so out of the Tab order too",
              not tab and pg.evaluate(WHERE) == [None, "none", "0000"], f"not [hidden] with every door shut: {tab}; {pg.evaluate(WHERE)}")
        # Joined: the open tile reaches over the card's edge and is above it,
        # so the point just inside the card's edge under it is the tile's, and
        # at an end of the row the card's corner under it is square.
        JOIN = """(k) => { const t = document.querySelector('#musicDoors .dp-tile[data-dp="' + k + '"]'), d = document.getElementById(t.getAttribute('aria-controls'));
            t.scrollIntoView({ block: 'center' }); const a = t.getBoundingClientRect(), r = d.getBoundingClientRect(), cs = getComputedStyle(d);
            const at = document.elementFromPoint(a.left + a.width / 2, r.top + 0.5);
            return { over: +(a.bottom - r.top).toFixed(2), tile: !!at && t.contains(at), open: t.classList.contains('dp-open'),
                     corners: [cs.borderTopLeftRadius, cs.borderTopRightRadius] }; }"""
        joins, painted = {}, {}
        for k in ("length", "exact"):
            set_door(pg, k)
            joins[k] = pg.evaluate(JOIN, k)
            for scheme in ("light", "dark"):
                pg.emulate_media(color_scheme=scheme); pg.wait_for_timeout(150)
                painted[(k, scheme)] = seam(pg, k)
        pg.emulate_media(color_scheme="light")
        check(f"{_n}: open, a door's tile and its group are one shape, the tile over the card's edge, the corner square at the row's ends",
              all(j["open"] and j["tile"] and 0.5 <= j["over"] <= 1.5 for j in joins.values())
              and joins["length"]["corners"][0] == "0px" and joins["exact"]["corners"][1] == "0px", str(joins))
        check(f"{_n}: no line shows where a door's tile meets its group, light or dark (painted pixels: the rows "
              "at the joint are the card's colour), and at an end the card's edge runs unbroken",
              all(w <= 2 and len(e) == 1 and min(e.values()) >= 4 for w, e in painted.values()),
              "; ".join(f"{k} {sc}: largest step from the card at the joint {w} (2 at most), the edge's smallest {e} (4 at least)"
                        for (k, sc), (w, e) in painted.items()))
        set_door(pg, None)
        # Opening, swapping and closing keep the loop: an own loop and smooth restart.
        set_door(pg, "restart")
        pg.evaluate("() => { trimStart = 0.7; trimEnd = 3.9; updateTrimUI(); }")
        pg.evaluate("() => { const s = document.getElementById('crossfadeSlider'); s.value = '120'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        before = pg.evaluate(TRIM)
        seen = []
        for want in ("length", None, "exact", "beat", None):
            set_door(pg, want)
            pg.wait_for_timeout(250)
            seen.append(pg.evaluate(TRIM))
        check(f"{_n}: opening, swapping and closing the doors keeps the loop",
              all(t == before for t in seen) and before["xf"] == 120, f"{before} then {seen}")

        # A door unfolds and folds away: the animations themselves, read as
        # the tap lands (opacity from 0 in, to 0 out, the draw drawer's 220ms
        # and 180ms), and the frames, read on every one: some on the way in,
        # and on the way out with the tile still joined, then hidden. One
        # frame each way is the most a loaded machine guarantees: beside other
        # suites a frame lasted up to 100ms and the unfold's ease is past 98%
        # by half its time.
        FRAMES = """() => { window.__mf = []; const t = """ + TILE + """, d = document.getElementById(t.getAttribute('aria-controls')), t0 = performance.now();
            (function f() { window.__mf.push([Math.round(performance.now() - t0), d.hidden, +getComputedStyle(d).opacity, t.classList.contains('dp-open')]);
              if (performance.now() - t0 < 600) requestAnimationFrame(f); })();
            t.click();
            return d.getAnimations().map(a => { const k = a.effect.getKeyframes(); return [+k[0].opacity, +k[k.length - 1].opacity, a.effect.getTiming().duration]; }); }"""
        a_up = pg.evaluate(FRAMES); pg.wait_for_timeout(700)
        up = pg.evaluate("() => window.__mf")
        a_down = pg.evaluate(FRAMES); pg.wait_for_timeout(700)
        down = pg.evaluate("() => window.__mf")
        mid_up = [f for f in up if not f[1] and 0.02 < f[2] < 0.98]
        mid_down = [f for f in down if not f[1] and 0.02 < f[2] < 0.98 and f[3]]
        check(f"{_n}: a door unfolds, and folds away joined to its tile before it goes",
              a_up == [[0, 1, 220]] and a_down == [[1, 0, 180]] and len(mid_up) >= 1 and len(mid_down) >= 1
              and down[-1][1] and not down[-1][3],
              f"animations {a_up} in, {a_down} out; {len(mid_up)} frames on the way in, {len(mid_down)} on the way out; last {down[-1] if down else None}")
        check(f"{_n}: no page errors through the doors", not errs, "; ".join(errs[:2]))
        c.close()

    # Reduce Motion: at once, both ways; nothing on the way.
    for _n, _p in eds("doors"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **DESK))
        c, pg, _ = editor(b, _n, _p, ctx=c, drawn=False)
        pg.evaluate("""() => { window.__mf = []; const t = """ + TILE + """, d = document.getElementById(t.getAttribute('aria-controls')), t0 = performance.now();
            (function f() { window.__mf.push([d.hidden, +getComputedStyle(d).opacity]); if (performance.now() - t0 < 2500) requestAnimationFrame(f); })(); }""")
        pg.click(tile("restart")); pg.wait_for_timeout(400); pg.click(tile("restart")); pg.wait_for_timeout(400)
        pg.wait_for_function("() => window.__mf.length && window.__mf[window.__mf.length - 1][0]", timeout=3000)
        fr = pg.evaluate("() => window.__mf")
        check(f"{_n}: under Reduce Motion a door opens and closes at once, nothing on the way",
              fr and not [f for f in fr if not f[0] and f[1] < 0.999] and any(not f[0] for f in fr) and fr[-1][0], f"{len(fr)} frames, {fr[:3]} ... {fr[-2:]}")
        c.close()

    # THE DOORS START SHUT, EVERY TIME (as More did: the owner, finding it
    # open from an old Fine-tune, "More starts open"; then the pick, always
    # closed): on a load, the old remembered key on file too, and on every
    # opening of the drawer, whether it was closed or Photo was picked.
    # Nothing remembers them.
    for _n, _p in eds("doors"):
        c = waits.instrument(b.new_context(**DESK))
        _, pg, _ = editor(b, _n, _p, ctx=c, drawn=False)
        set_door(pg, "exact")
        opened = pg.evaluate(WHERE)
        pg.evaluate("() => localStorage.setItem('skribl_music_level', 'fine')")
        pg.reload(); browsing.goto(pg, BASE, _p); add(pg, SHORT)
        loaded = pg.evaluate(WHERE)
        set_door(pg, "length")
        browsing.pad_drawer_close(pg); browsing.pad_drawer(pg, "music")
        reopened = pg.evaluate(WHERE)
        set_door(pg, "beat")
        pg.click("#mediaTabPhoto"); pg.wait_for_timeout(300); pg.click("#mediaTabMusic"); pg.wait_for_timeout(300)
        back = pg.evaluate(WHERE)
        shut = [None, "none", "0000"]
        check(f"{_n}: the doors start shut every time: on a load, the old remembered key too; the drawer opened again; Photo and back",
              opened == ["3", "exact", "0001"] and loaded == reopened == back == shut,
              f"opened {opened}; after a reload {loaded}; the drawer opened again {reopened}; Photo and back {back}")
        c.close()

    # WHAT EACH TILE SAYS: Length the loop's length (Skribl's mark on its
    # picture while the loop is Skribl's pick, and in its name for a screen
    # reader), Beat the tempo or Tap it, Restart Smooth or Clean cut, Exact the
    # loop's two times, as precisely as the tile has room for; every word
    # inside its tile (no ellipsis) on a 390px phone, the owner's 402 and a desk.
    TWORDS = """() => [...document.querySelectorAll('#musicDoors .dp-tile')].map((t) => { const v = t.querySelector('.dp-v');
        return [t.dataset.dp, v.textContent, v.scrollWidth <= v.clientWidth + 0.5, t.getAttribute('aria-label')]; })"""
    # THE DOORS SPAN THE DRAWER (the owner's pick in the whole-drawer mock,
    # "Tiles grow"): edge to edge with the timeline and the pair above them, and
    # an open door's group as wide, on a phone as on a desk. The row stopped at
    # 520px, 140px short of the pair on a desk.
    SPAN = """() => { const r = (s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null;
        const b = e.getBoundingClientRect(); return [+b.left.toFixed(1), +b.right.toFixed(1)]; };
      return { timeline: r('#musicTimeline'), pair: r('.mt-transport'), doors: r('#musicDoors .dp-tiles'), open: r('#musicDoors > .dp-panel:not([hidden])'),
               tiles: [...document.querySelectorAll('#musicDoors .dp-tile')].map((t) => +t.getBoundingClientRect().width.toFixed(1)) }; }"""
    for _n, _p in eds("words"):
        got, span = {}, {}
        for dev, o in (("390", dict(PHONE, viewport={"width": 390, "height": 844})), ("402", PHONE), ("desk", DESK)):
            c, pg, _ = editor(b, _n, _p, opts=o)
            pick = pg.evaluate(TWORDS)
            pg.evaluate("() => { trimStart = 0.5; trimEnd = 5.75; loopCrossfadeMs = 0; setCrossfadeUI(); updateTrimUI(); }")
            pg.wait_for_timeout(150)
            own = pg.evaluate(TWORDS)
            # The beat, tapped, heard, then set by the loop's end.
            sources = []
            for tp in ("{ bpm: 100, phase: 0 }", "{ bpm: 100, phase: 0, heard: true }", "{ bpm: 100.437, phase: 0, by: 'end' }"):
                pg.evaluate(f"() => {{ musicTempo = {tp}; updateTrimUI(); }}")
                pg.wait_for_timeout(150)
                sources.append(pg.evaluate(TWORDS))
            beat = sources[0]
            add(pg, LONG)
            pg.evaluate("() => { musicTempo = null; trimStart = 12.25; trimEnd = 28.5; updateTrimUI(); }")
            pg.wait_for_timeout(150)
            far = pg.evaluate(TWORDS)
            got[dev] = (pick, own, beat, far, pg.evaluate(SAID), sources)
            set_door(pg, "exact")
            span[dev] = pg.evaluate(SPAN)
            c.close()
        ok, why = True, []
        for dev, (pick, own, beat, far, said, sources) in got.items():
            w = lambda rows: [r[1] for r in rows]
            fits = all(r[2] for rows in (pick, own, far, *sources) for r in rows)
            # THE BEAT TILE SAYS WHERE ITS BEAT CAME FROM (the owner's pick,
            # "83 · heard"), where the tile has room; else the beat alone, as
            # before ("100 bpm", or "100.4" where even that has no room). A
            # desk always has room; its name always says.
            said_as = [("100", "tapped"), ("100", "heard"), ("100.4", "by hand")]
            tiles = [w(rows)[1] for rows in sources]
            whole = all(t == f"{n} · {f}" or (dev != "desk" and t in (f"{n} bpm", n)) for t, (n, f) in zip(tiles, said_as))
            named = all(rows[1][3] == f"Beat, {n} beats a minute, {f}" for rows, (n, f) in zip(sources, said_as))
            good = (fits and w(own)[1:3] == ["Tap it", "Clean cut"] and w(own)[0] == "5.3s"
                    and w(own)[3] == ("0.50–5.75")
                    and own[0][3] == "Length, 5.3s" and pick[0][3].startswith("Length, Skribl's pick, ")
                    and w(beat)[0] == "8.8 beats" and whole and named
                    and w(far)[3] in ("12.25–28.50", "12.3–28.5")
                    and (dev != "desk" or w(far)[3] == "12.25–28.50"))
            ok = ok and good
            why.append(f"{dev}: the pick {w(pick)}, own {w(own)}, a tempo {w(beat)}, the beat's tiles {tiles} (named {named}), far {w(far)}; "
                       f"every word inside {fits}; labels {pick[0][3]!r}, {own[0][3]!r}")
        check(f"{_n}: each tile says what its door is set to, the Beat tile where its beat came from where it has room, every word inside its tile on a 390px phone, the owner's 402 and a desk",
              ok, "; ".join(why))
        same = lambda a, z: bool(a and z) and all(abs(u - v) <= 0.5 for u, v in zip(a, z))
        check(f"{_n}: the four doors span the drawer, edge to edge with the timeline and the pair above them, each as wide "
              "as the others and an open door's group as wide as the row, on a 390px phone, the owner's 402 and a desk",
              all(same(s["doors"], s["pair"]) and same(s["doors"], s["timeline"]) and same(s["open"], s["doors"])
                  and max(s["tiles"]) - min(s["tiles"]) <= 0.5 for s in span.values()),
              "; ".join(f"{dev}: {s}" for dev, s in span.items()))
    for _n, _p in eds("words"):
        c, pg, _ = editor(b, _n, _p)
        a = pg.evaluate(SAID)
        pg.evaluate("() => { trimStart = 0.5; trimEnd = 4.5; updateTrimUI(); }"); pg.wait_for_timeout(150)
        b2 = pg.evaluate(SAID)
        check(f"{_n}: Skribl's mark is on the Length tile's picture while the loop is Skribl's pick, and goes once it is changed",
              a["pick"] and a["spark"] and not b2["pick"] and not b2["spark"], f"the pick: lit {a['pick']}, mark {a['spark']}; changed: lit {b2['pick']}, mark {b2['spark']}")
        c.close()

    print("\nMUSIC DOORS — Skribl's pick, and the one line")
    for _n, _p in eds("pick"):
        got = {}
        for drawn, song in ((True, SHORT), (False, LONG), (True, LONG)):
            c, pg, _ = editor(b, _n, _p, drawn=drawn, song=song)
            got[(drawn, song["name"])] = (pg.evaluate(TRIM), pg.evaluate(DRAWING[_n]), pg.evaluate(SAID))
            c.close()
        ok, why = True, []
        for (drawn, nm), (t, secs, said) in got.items():
            h_ = heard(t)
            # The line: the length heard, then against the drawing once there is one.
            rel = "" if not drawn else " · fits your drawing" if abs(h_ - secs) < 0.0005 else \
                f" · {'shorter' if h_ < secs else 'longer'} than your {WORK[_n]}"
            words = f"{h_:.2f}s" + (rel or " loop")
            if _n == "Pad" and drawn:
                good = t["s"] == 0 and t["xf"] == 250 and abs(h_ - secs) < 0.002
            elif nm == "long.wav":
                good = t["s"] == 0 and abs(t["e"] - 20) < 0.001 and t["xf"] == 250
            else:
                good = t["s"] == 0 and abs(t["e"] - t["d"]) < 0.001 and t["xf"] == 250
            good = good and said["line"] == words and said["pick"] and said["spark"] and not said["back"] and not said["undo"]
            ok = ok and good
            why.append(f"{'drawn' if drawn else 'blank'} {nm}: {t['s']:.2f}-{t['e']:.3f} xf {t['xf']} heard {h_:.3f} (drawing {secs:.3f}) {said['line']!r} pick lit {said['pick']}, mark {said['spark']}")
        check(f"{_n}: a new song starts on Skribl's pick: the one line says its length, and Skribl's pick is lit", ok, "; ".join(why))

    # The line's words, from the loop as it is: what is heard, the beats once
    # there is a tempo, against the drawing.
    for _n, _p in eds("line"):
        c, pg, _ = editor(b, _n, _p)
        secs = pg.evaluate(DRAWING[_n])
        got = []
        for xf, end, tempo in ((250, 4.25, None), (250, 4.25, {"bpm": 120, "phase": 0}), (0, 3.0, {"bpm": 90, "phase": 0.1})):
            pg.evaluate("(o) => { loopCrossfadeMs = o.xf; setCrossfadeUI(); trimStart = 0; trimEnd = o.end; musicTempo = o.tempo; updateTrimUI(); }",
                        {"xf": xf, "end": end, "tempo": tempo})
            pg.wait_for_timeout(100)
            got.append(pg.evaluate("() => [document.getElementById('musicPickText').textContent, document.getElementById('musicPickText').querySelector('b').textContent]"))
        h1, h3 = 4.0, 3.0
        rel = lambda h_: f"{'shorter' if h_ < secs else 'longer'} than your {WORK[_n]}"
        want = [[f"4.00s · {rel(h1)}", "4.00s"], [f"4.00s · 8 beats · {rel(h1)}", "4.00s"], [f"3.00s · 4.5 beats · {rel(h3)}", "3.00s"]]
        check(f"{_n}: the one line says the length heard, bold, its beats once there is a tempo, and against the {WORK[_n]}",
              got == want, f"{got} for a {secs:.3f}s {WORK[_n]}, want {want}")
        c.close()

    for _n, _p in eds("pick"):
        c, pg, errs = editor(b, _n, _p, door="exact")
        pick = pg.evaluate(TRIM)
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(200)
        own, said = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: a change unlights Skribl's pick, which is the way back, and the loop's Undo can take it back",
              said["back"] and not said["pick"] and not said["spark"] and said["undo"],
              f"{said['line']!r}, pick lit {said['pick']}, the way back {said['back']}, undo {said['undo']}, mark {said['spark']}")
        set_door(pg, "length")
        went = press(pg, "#musicPickCard")
        back, said2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        focus = pg.evaluate("() => document.activeElement && document.activeElement.id")
        undid = press(pg, "#musicUndo")
        undone, said3 = pg.evaluate(TRIM), pg.evaluate(SAID)
        focus3 = pg.evaluate("() => document.activeElement && document.activeElement.id")
        # The nudge is a step under the way back, so the Undo stays, and with
        # it the focus.
        check(f"{_n}: Skribl's pick, tapped, puts it back, and the loop's Undo undoes that; focus is never lost",
              went and undid and back == pick and said2["pick"] and said2["spark"] and said2["undo"] and not said2["back"]
              and focus == "musicPickCard" and undone == own and said3["back"] and not said3["pick"] and said3["undo"] and focus3 == "musicUndo",
              f"pick {pick}, own {own}, back {back} (lit {said2['pick']}, undo {said2['undo']}, focus {focus}), undone {undone} (the way back {said3['back']},"
              f" undo {said3['undo']}, focus {focus3}); pressed the pick {went}, undo {undid}")
        c.close()

    # The Pad's pick follows the drawing. Undo with the drawer open is the
    # drawing changing, not the person: the line says only that it no longer
    # fits, and the way back fits the drawing as it is now.
    if part("pick") and (not ONLY or ONLY == "Pad"):
        c, pg, _ = editor(b, "Pad", "/", drawn=False, song=None)
        box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
        for row in (0, 1):
            pg.mouse.move(box["x"] + 60, box["y"] + 60 + row * 90); pg.mouse.down()
            for k in range(30):
                pg.mouse.move(box["x"] + 60 + k * 7, box["y"] + 60 + row * 90 + k * 2); pg.wait_for_timeout(40)
            pg.mouse.up(); pg.wait_for_timeout(300)
        pg.click("#recordBtn"); pg.wait_for_timeout(700)
        add(pg, SHORT)
        set_door(pg, "length")
        two, s0 = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        pg.evaluate("() => document.getElementById('undoBtn').click()"); pg.wait_for_timeout(400)
        one, s1 = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        press(pg, "#musicPickCard")
        t2, s2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check("Pad: an Undo with the drawer open shows the way back, no more, and Skribl's pick fits the drawing again",
              s0["pick"] and s0["line"].endswith("· fits your drawing") and one < two - 0.5
              and s1["line"].endswith("· longer than your drawing") and s1["back"] and not s1["pick"] and s1["fit"] == "false"
              and abs(heard(t2) - one) < 0.002 and s2["pick"] and s2["line"].endswith("· fits your drawing"),
              f"{two:.2f}s then {one:.2f}s: {s1['line']!r}, the way back {s1['back']}; after it heard {heard(t2):.3f}s, lit {s2['pick']}, {s2['line']!r}")
        c.close()

    # Fit's seconds are rounded from the hundredths the line shows, as a
    # person rounds what they read: a drawing 4.448s long was "4.4 seconds"
    # over a line saying 4.45s. Built point by point, 8ms apart.
    if part("pick") and (not ONLY or ONLY == "Pad"):
        c, pg, _ = editor(b, "Pad", "/", drawn=False, song=None)
        pg.evaluate("""() => { strokes.length = 0;
            for (let k = 0; k <= 556; k++) strokes.push({ x: 0.2 + k * 0.001, y: 0.4, color: '#7c5cff', size: 6, t: k * 8, start: k === 0 });
            strokeGroups.length = 0; strokeGroups.push(strokes.length); updateDrawingTimeLabels(); }""")
        add(pg, SHORT)
        secs, said = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        check("Pad: the line's length and Fit's agree, as a person rounds them",
              abs(secs - 4.448) < 1e-9 and said["line"] == "4.45s · fits your drawing" and said["fitSub"] == "4.5s",
              f"a {secs:.3f}s drawing: {said['line']!r}; Fit says {said['fitSub']!r}")
        c.close()

    # The line's height never changes as it says other things: the pick, a
    # change, the way back, a tempo's beats, the longest words it has
    # ("19.75s · 39.5 beats · longer than your animation"), or everything
    # under it would move with a finger still on the timeline. With the
    # loop's Undo and Redo at its end: one row and the pair's height where
    # the longest fit beside them (a desk), two on a phone (to 459px), what
    # the loop is against the drawing on its own row whatever it says.
    LONGEST = "() => { musicTempo = { bpm: 120, phase: 0 }; loopCrossfadeMs = 250; setCrossfadeUI(); trimStart = 0; trimEnd = 20; updateTrimUI(); }"
    for _n, _p in eds("line"):
        hs = {}
        for dev, o in (("320", dict(PHONE, viewport={"width": 320, "height": 700})), ("375", dict(PHONE, viewport={"width": 375, "height": 760})),
                       ("390", dict(PHONE, viewport={"width": 390, "height": 844})), ("phone", PHONE), ("desk", DESK)):
            c, pg, _ = editor(b, _n, _p, opts=o, door="exact")
            H = "() => Math.round(document.getElementById('musicPickLine').getBoundingClientRect().height * 10) / 10"
            row = [pg.evaluate(H)]
            pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150); row.append(pg.evaluate(H))
            set_door(pg, "length")
            press(pg, "#musicPickCard"); row.append(pg.evaluate(H))
            pg.evaluate("() => { musicTempo = { bpm: 117, phase: 0.03 }; trimStart = 0.5; trimEnd = 5.9; updateTrimUI(); }")
            pg.wait_for_timeout(150); row.append(pg.evaluate(H))
            add(pg, LONG)
            pg.evaluate(LONGEST); pg.wait_for_timeout(150); row.append(pg.evaluate(H))
            hs[dev] = (row, pg.evaluate("() => document.getElementById('musicPickText').textContent"))
            c.close()
        check(f"{_n}: the one line's height never changes as it says other things: two rows on a phone, 320 to 402px, one on a desk as tall as the Undo and Redo",
              all(len(set(r)) == 1 for r, _ in hs.values()) and all(36 < hs[d][0][0] < 45 for d in ("320", "375", "390", "phone"))
              and abs(hs["desk"][0][0] - 36) < 0.6,
              f"the pick, a change, the way back, a tempo, the longest words: {hs}")

    # A song the autosave had to drop is re-added from its card: its saved loop
    # comes back with it (pendingMusicMeta), and Skribl's pick stays away.
    for _n, _p in eds("pick"):
        c, pg, _ = editor(b, _n, _p, song=None)
        browsing.pad_drawer(pg, "music")
        pg.evaluate("() => { pendingMusicMeta = { trimStart: 1, trimEnd: 3, crossfadeMs: 0, enabled: true }; }")
        add(pg, SHORT)
        t = pg.evaluate(TRIM)
        check(f"{_n}: a song re-added from its card keeps its saved loop, never Skribl's pick",
              t["s"] == 1 and t["e"] == 3 and t["xf"] == 0, str(t))
        c.close()

    # A song a draft brings back keeps the draft's loop: the pick is for a song just chosen.
    for _n, _p in eds("pick"):
        c, pg, _ = editor(b, _n, _p)
        pg.evaluate("() => { trimStart = 1; trimEnd = 3; loopCrossfadeMs = 0; setCrossfadeUI(); updateTrimUI();"
                    " (typeof scheduleAutosave === 'function' ? scheduleAutosave : scheduleSave)(); }")
        pg.wait_for_timeout(2500)
        pg.reload()
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        waits.settle(pg, 600)
        t = pg.evaluate(TRIM)
        check(f"{_n}: a song a draft brings back keeps the draft's loop, never Skribl's pick",
              t["s"] == 1 and t["e"] == 3 and t["xf"] == 0, str(t))
        c.close()

    print("\nMUSIC DOORS — Fit my drawing and Whole song")
    for _n, _p in eds("picks"):
        c, pg, _ = editor(b, _n, _p, door="length")
        secs = pg.evaluate(DRAWING[_n])
        pg.evaluate("() => { trimStart = 0.5; trimEnd = 5.5; updateTrimUI(); }")
        pg.click("#matchDrawingBtn"); pg.wait_for_timeout(200)
        t, said = pg.evaluate(TRIM), pg.evaluate(SAID)
        tint = pg.evaluate("""() => { const d = document.createElement('div'); d.style.background = 'var(--seg-on-fill)';
            document.getElementById('musicPanel').appendChild(d); const want = getComputedStyle(d).backgroundColor; d.remove();
            return [getComputedStyle(document.getElementById('matchDrawingBtn')).backgroundColor, want]; }""")
        check(f"{_n}: Fit counts the smooth restart: what is heard is as long as the drawing",
              t["xf"] == 250 and abs(heard(t) - secs) < 0.002 and abs(t["s"] - 0.5) < 1e-9,
              f"{t['s']:.2f}-{t['e']:.3f}, smooth {t['xf']}ms: heard {heard(t):.3f}s for a {secs:.3f}s {WORK[_n]}")
        check(f"{_n}: the length the loop is wears the one tint, one at a time",
              said["fit"] == "true" and said["whole"] == "false" and not said["pick"] and tint[0] == tint[1],
              f"fit {said['fit']}, whole {said['whole']}, the pick {said['pick']}, {tint}")
        pg.click("#musicWholeBtn"); pg.wait_for_timeout(200)
        t2, said2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        add(pg, LONG)
        said3 = pg.evaluate(SAID)
        pg.evaluate("() => { trimStart = 3; trimEnd = 9; updateTrimUI(); }")
        set_door(pg, "length")
        pg.click("#musicWholeBtn"); pg.wait_for_timeout(200)
        t3 = pg.evaluate(TRIM)
        check(f"{_n}: Whole song loops all of a short song, and a long one's first 20 seconds, and says which",
              t2["s"] == 0 and abs(t2["e"] - 6) < 0.01 and said2["whole"] == "true" and said2["fit"] == "false"
              and (said2["wholeName"], said2["wholeSub"]) == ("Whole song", "6s")
              and (said3["wholeName"], said3["wholeSub"]) == ("Longest loop", "the first 20s") and t3["s"] == 0 and abs(t3["e"] - 20) < 0.001,
              f"short: {t2['s']:.2f}-{t2['e']:.2f} {said2['wholeName']!r} {said2['wholeSub']!r}; long: {said3['wholeName']!r} {said3['wholeSub']!r}, {t3['s']:.2f}-{t3['e']:.2f}")
        c.close()

    # Two cards can be the same loop: a short song's pick, nothing drawn, is
    # the whole song. The one pressed is the one lit, so a press answers, and
    # neither moves the loop or offers an Undo of nothing.
    for _n, _p in eds("picks"):
        c, pg, _ = editor(b, _n, _p, drawn=False, door="length")
        t0, s0 = pg.evaluate(TRIM), pg.evaluate(SAID)
        press(pg, "#musicWholeBtn")
        t1, s1 = pg.evaluate(TRIM), pg.evaluate(SAID)
        press(pg, "#musicPickCard")
        t2, s2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        same = all(abs(t["s"] - t0["s"]) < 1e-9 and abs(t["e"] - t0["e"]) < 1e-9 and t["xf"] == t0["xf"] for t in (t1, t2))
        check(f"{_n}: where Skribl's pick is the whole song, the card pressed is the one lit, the loop stays, and nothing offers an Undo",
              s0["pick"] and s0["whole"] == "false" and t0["s"] == 0 and abs(t0["e"] - 6) < 0.01
              and s1["whole"] == "true" and not s1["pick"] and s2["pick"] and s2["whole"] == "false"
              and same and not s1["undo"] and not s2["undo"],
              f"the pick {t0['s']:.2f}-{t0['e']:.2f}, lit {s0['pick']}; Whole pressed: whole {s1['whole']}, pick {s1['pick']}, undo {s1['undo']}; "
              f"the pick pressed: pick {s2['pick']}, whole {s2['whole']}, undo {s2['undo']}; the loop {t1['s']:.2f}-{t1['e']:.2f}, {t2['s']:.2f}-{t2['e']:.2f}")
        c.close()

    for _n, _p in eds("picks"):
        c, pg, _ = editor(b, _n, _p, drawn=False, door="length")
        off = pg.evaluate(SAID)
        if _n == "Pad":
            # Up to the canvas, as a person goes. On the Pad the first press on
            # the canvas closes the drawer; the second draws, and the take ends.
            pg.evaluate("() => window.scrollTo(0, 0)"); browsing.wait_scroll_still(pg)
            box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
            pg.mouse.click(box["x"] + 40, box["y"] + 40); pg.wait_for_timeout(300)
            pg.mouse.move(box["x"] + 60, box["y"] + 60); pg.mouse.down()
            for k in range(30):
                pg.mouse.move(box["x"] + 60 + k * 7, box["y"] + 60 + k * 2); pg.wait_for_timeout(40)
            pg.mouse.up(); pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('recordBtn').click()"); pg.wait_for_timeout(700)
            browsing.pad_drawer(pg, "music")
        else:
            # Flip's pages change with its drawer open.
            pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 8})
        pg.wait_for_timeout(200)
        on = pg.evaluate(SAID)
        check(f"{_n}: with nothing drawn Fit is off and says why, and wakes once there is a drawing",
              off["fitOff"] and off["fitSub"] == "once you've drawn" and not on["fitOff"] and on["fitSub"].endswith("s")
              and on["play"] == f"Play with my {WORK[_n]}",
              f"before: off {off['fitOff']} {off['fitSub']!r} {off['play']!r}; after: off {on['fitOff']} {on['fitSub']!r} {on['play']!r}")
        c.close()

    print("\nMUSIC DOORS — Smooth restart")
    for _n, _p in eds("smooth"):
        c, pg, _ = editor(b, _n, _p, door="restart")
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        a, sa = pg.evaluate(TRIM), pg.evaluate(SAID)
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        b2 = pg.evaluate(TRIM)
        pg.evaluate("() => { const s = document.getElementById('crossfadeSlider'); s.value = '400'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        c2, sc = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: Smooth restart's switch turns the fold on at its last length, and off",
              a["xf"] == 0 and sa["smooth"] == "false" and sa["smoothSub"] == "A clean cut back to the start."
              and b2["xf"] == 250 and c2["xf"] == 400 and sc["smooth"] == "true"
              and sc["smoothSub"] == "The end fades into the start over 0.40s, which makes the loop 0.40s shorter.",
              f"off {a['xf']} ({sa['smoothSub']!r}), on {b2['xf']}, after the length is set {c2['xf']} ({sc['smoothSub']!r})")
        t, s2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: the line counts what is heard: the length less the smooth restart",
              s2["line"].startswith(f"{heard(t):.2f}s · ") and abs(heard(t) - (t["e"] - t["s"] - 0.4)) < 1e-9, f"{s2['line']!r} for {t}")
        c.close()

    print("\nMUSIC DOORS — Exact times")
    for _n, _p in eds("exact"):
        c, pg, _ = editor(b, _n, _p, door="exact")
        pg.fill("#endReadout", "4.25"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t1 = pg.evaluate(TRIM)
        pg.fill("#endReadout", "soon"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t2, v2 = pg.evaluate(TRIM), pg.evaluate("() => document.getElementById('endReadout').value")
        pg.fill("#startReadout", "1,5"); pg.press("#startReadout", "Enter"); pg.wait_for_timeout(150)
        t3, v3 = pg.evaluate(TRIM), pg.evaluate("() => document.getElementById('startReadout').value")
        check(f"{_n}: a typed time moves its end, and a time that is not one puts it back",
              abs(t1["e"] - 4.25) < 1e-9 and t2 == t1 and v2 == "4.250" and abs(t3["s"] - 1.5) < 1e-9 and v3 == "1.500",
              f"4.25 -> {t1['e']}; 'soon' -> {t2['e']} shown {v2!r}; '1,5' -> {t3['s']} shown {v3!r}")
        # - and +: as far as Each press says. Untouched it is 0.1s, or a bar
        # once there is a tempo while Snap to the beat is on; the pill shows
        # which, and the buttons' names say it.
        NAMES = "() => [...document.querySelectorAll('.nudge-btn[data-which]')].map(b => b.getAttribute('aria-label'))"
        e0, n0, l0 = pg.evaluate("() => trimEnd"), pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.click('.nudge-btn[data-which="end"][data-amount="1"]'); pg.wait_for_timeout(150)
        e1 = pg.evaluate("() => trimEnd")
        pg.evaluate("() => { musicTempo = { bpm: 120, phase: 0 }; updateTrimUI(); }"); pg.wait_for_timeout(150)
        n1, l1 = pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150)
        e2 = pg.evaluate("() => trimEnd")
        # Snap to the beat off, the magnet by the zoom: the step a free set wants, untouched.
        pg.click("#musicSnap"); pg.wait_for_timeout(150)
        n2, l2 = pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.click("#musicSnap"); pg.wait_for_timeout(150)
        check(f"{_n}: untouched, - and + move 0.1s, or a bar once there is a tempo while Snap to the beat is on, and say which",
              abs((e1 - e0) - 0.1) < 1e-9 and abs((e1 - e2) - 2.0) < 1e-9
              and l0 == "0.01s · *0.1s" and l1 == "0.01s · 0.1s · *a bar" and l2 == "0.01s · *0.1s · a bar"
              and n0 == ["Start of loop, 0.1s earlier", "Start of loop, 0.1s later", "End of loop, 0.1s earlier", "End of loop, 0.1s later"]
              and n1 == ["Start of loop, a bar earlier", "Start of loop, a bar later", "End of loop, a bar earlier", "End of loop, a bar later"]
              and n2 == n0,
              f"+ moved the end {e1 - e0:.4f}s, then - at 120 a minute {e1 - e2:.4f}s; Each press {l0!r}, then {l1!r}, then with the magnet off {l2!r}; {n0} then {n1}")
        # Picked, a step is kept, a tempo or not, and a new song starts untouched.
        pg.evaluate("() => { musicTempo = null; updateTrimUI(); }"); pg.wait_for_timeout(150)
        pg.click('#musicStepSeg button[data-step="0.01"]'); pg.wait_for_timeout(150)
        f0 = pg.evaluate("() => trimEnd")
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150)
        f1, m1, k1 = pg.evaluate("() => trimEnd"), pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.evaluate("() => { musicTempo = { bpm: 120, phase: 0 }; updateTrimUI(); }"); pg.wait_for_timeout(150)
        k2 = pg.evaluate(SAID)["step"]
        pg.click('#musicStepSeg button[data-step="0.1"]'); pg.wait_for_timeout(150)
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150)
        f2, k3 = pg.evaluate("() => trimEnd"), pg.evaluate(SAID)["step"]
        check(f"{_n}: Each press picks the step and keeps it, a tempo or not",
              abs((f0 - f1) - 0.01) < 1e-9 and abs((f1 - f2) - 0.1) < 1e-9
              and k1 == "*0.01s · 0.1s" and k2 == "*0.01s · 0.1s · a bar" and k3 == "0.01s · *0.1s · a bar"
              and m1 == ["Start of loop, 0.01s earlier", "Start of loop, 0.01s later", "End of loop, 0.01s earlier", "End of loop, 0.01s later"],
              f"0.01s picked: - moved {f0 - f1:.4f}s ({k1!r}, {m1}); a tempo: {k2!r}; 0.1s picked with it: - moved {f1 - f2:.4f}s ({k3!r})")
        # 0.01s picked first: 0.1s kept would look untouched.
        pg.click('#musicStepSeg button[data-step="0.01"]'); pg.wait_for_timeout(150)
        k5 = pg.evaluate(SAID)["step"]
        add(pg, LONG)
        k4 = pg.evaluate(SAID)["step"]
        check(f"{_n}: a new song starts on the untouched step",
              k5.startswith("*0.01s") and k4 == "0.01s · *0.1s", f"0.01s picked ({k5!r}), then a new song: {k4!r}")
        # Lock the length is in the Length door, the steppers in Exact times.
        pg.evaluate("() => { musicTempo = null; updateTrimUI(); }"); pg.wait_for_timeout(100)
        set_door(pg, "length"); pg.click("#musicLock"); pg.wait_for_timeout(100)
        l0 = pg.evaluate(TRIM)
        set_door(pg, "exact"); pg.click('.nudge-btn[data-which="start"][data-amount="1"]'); pg.wait_for_timeout(150)
        l1 = pg.evaluate(TRIM)
        set_door(pg, "length"); pg.click("#musicLock"); pg.wait_for_timeout(100)
        set_door(pg, "exact"); pg.click('.nudge-btn[data-which="start"][data-amount="1"]'); pg.wait_for_timeout(150)
        l2 = pg.evaluate(TRIM)
        check(f"{_n}: Lock the length moves both ends together",
              abs((l1["s"] - l0["s"]) - 0.1) < 1e-9 and abs((l1["e"] - l0["e"]) - 0.1) < 1e-9
              and abs((l2["s"] - l1["s"]) - 0.1) < 1e-9 and abs(l2["e"] - l1["e"]) < 1e-9,
              f"locked: start {l0['s']:.3f}->{l1['s']:.3f}, end {l0['e']:.3f}->{l1['e']:.3f}; unlocked: start ->{l2['s']:.3f}, end ->{l2['e']:.3f}")
        sizes = pg.evaluate("() => [...document.querySelectorAll('#musicDetail input:not([type=range])')].map(i => [i.id, parseFloat(getComputedStyle(i).fontSize)])")
        check(f"{_n}: every field that takes text is 16px (iOS magnifies the page under that)",
              len(sizes) == 2 and all(px >= 16 for _, px in sizes), str(sizes))
        c.close()

    print("\nMUSIC DOORS — the timeline follows you")
    # The copy under the header as it stands: on, where, what is painted at
    # its middle, its canvas and the header's (a rect is not a paint), its
    # framing and words, and whether the drawer is still open.
    FOLLOW = """() => { const f = document.getElementById('musicFollow'), tl = document.getElementById('musicTimeline'), card = document.getElementById('mediaCard');
      if (!f) return null;
      const r = f.getBoundingClientRect(), c = card.getBoundingClientRect(), t = tl.getBoundingClientRect(), cs = getComputedStyle(f), h = document.querySelector('.header'), hr = h.getBoundingClientRect();
      const foot = ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? parseFloat(getComputedStyle(h).top || 0) + hr.height : 0;
      const at = (x, y) => { const e = document.elementFromPoint(x, y); return !e ? null : e.closest('#musicFollow') ? 'copy' : e.closest('.header') ? 'header' : (e.id || e.tagName); };
      return { on: f.classList.contains('on'), vis: cs.visibility, op: +cs.opacity, top: r.top, left: r.left, w: r.width,
               cardLeft: c.left, cardW: c.width, tlTop: t.top, tlBottom: t.bottom, foot: foot, vh: innerHeight, open: !document.getElementById('musicPanel').hidden,
               mid: at(r.left + r.width / 2, r.top + 20), lane: at(r.left + r.width / 2, r.bottom - 30), head: at(hr.left + hr.width / 2, hr.bottom - 8),
               p: f._painted || null, words: (document.getElementById('musicFollowWords') || {}).textContent || '',
               line: document.getElementById('musicPickText').textContent, s: trimStart, e: trimEnd }; }"""
    # Every frame from now, 700ms: the copy's opacity and what it painted.
    FOLLOW_REC = """() => { const out = window.__frec = [], t0 = performance.now(), f = document.getElementById('musicFollow');
      (function k() { const p = f._painted; out.push([performance.now() - t0, +getComputedStyle(f).opacity, p ? p.view.slice() : null]);
        if (performance.now() - t0 < 700) requestAnimationFrame(k); })(); }"""
    # The copy's canvas across each of its ends, at the canvas's own pixels
    # (the screen's), over two of its top rows: under the beat's dots and
    # over the song, so only the ground, the loop's light and the line.
    FOLLOW_EDGES = """() => { const f = document.getElementById('musicFollow'), cv = document.getElementById('musicFollowCanvas'), p = f._painted, d = devicePixelRatio;
      if (!p) return null;
      const x = cv.getContext('2d'), h = Math.round(2 * d), y0 = Math.round(2 * d), W = 14;
      return { d, acc: getComputedStyle(f).getPropertyValue('--accent').trim(), ends: [p.start, p.end].map((at) => {
        const L = Math.round(at * d) - 7, px = x.getImageData(L, y0, W, h).data;
        return Array.from({ length: h }, (_, j) => Array.from({ length: W }, (_, i) => Array.from(px.slice((j * W + i) * 4, (j * W + i) * 4 + 4)))); }) }; }"""

    def sharp_cv(rows, acc, n):
        """A run of the accent n columns wide, and the ground either side of it
        flat: no column part-lit beside it."""
        W = len(rows[0])
        near = lambda a, z, t: max(abs(u - v) for u, v in zip(a, z)) <= t
        line = [i for i in range(W) if all(near(r[i][:3], acc, 10) and r[i][3] >= 250 for r in rows)]
        if not line or line != list(range(line[0], line[-1] + 1)) or line[0] < 2 or line[-1] > W - 3:
            return False, f"the accent's columns {line}"
        a, z = line[0], line[-1]
        flat = all(near(r[a - 1], r[a - 2], 3) and near(r[z + 1], r[z + 2], 3) for r in rows)
        return len(line) == n and flat, f"{len(line)} columns of the accent ({n} wanted), the ground either side {'flat' if flat else 'part-lit'}"

    # As far down as the page goes, as a person scrolls to the drawer's end.
    DOWN = "() => scrollTo(0, document.documentElement.scrollHeight)"
    TUNED = "() => { musicTempo = { bpm: 120, phase: 0 }; trimStart = 2; trimEnd = 10.25; loopCrossfadeMs = 250; setCrossfadeUI(); updateTrimUI(); }"
    # Exact times under the timeline: on a phone and a desk the page cannot
    # scroll what it edits away (with More's four groups above it, it did).
    for _n, _p in eds("follow"):
        kept = {}
        for dev, opts in (("phone", PHONE), ("desk", DESK)):
            c, pg, errs = editor(b, _n, _p, song=LONG, opts=opts, door="exact")
            pg.evaluate(TUNED)
            pg.evaluate(DOWN); waits.settle(pg, 700); browsing.wait_scroll_still(pg)
            kept[dev] = pg.evaluate(FOLLOW)
            c.close()
        check(f"{_n}: Exact times opens under the timeline: scrolled as far as the page goes, what it edits is still on the screen, all of it, and the copy stays away (phone, desk)",
              all(k and k["tlTop"] >= k["foot"] - 1 and k["tlBottom"] <= k["vh"] + 1 and not k["on"] for k in kept.values()),
              "; ".join(f"{d}: the timeline {k['tlTop']:.0f}-{k['tlBottom']:.0f} under a header ending {k['foot']:.0f}, of {k['vh']}px, the copy on {k['on']}"
                        for d, k in kept.items()))
    for _n, _p in eds("follow"):
        for dev, opts in (("a small phone sideways", SMALL_SIDEWAYS),):
            c, pg, errs = editor(b, _n, _p, song=LONG, opts=opts, door="exact")
            pg.evaluate(TUNED)
            pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })")
            waits.settle(pg, 700); browsing.wait_scroll_still(pg)
            up = pg.evaluate(FOLLOW)
            pg.evaluate(FOLLOW_REC)
            pg.evaluate(DOWN)
            pg.wait_for_timeout(800)
            rec = pg.evaluate("() => window.__frec")
            dn = pg.evaluate(FOLLOW)
            way = [f for f in rec if 0.02 < f[1] < 0.98]
            check(f"{_n}: with the timeline on the screen the copy stays away; scrolled up past the header, it shows under the header, on the drawer to the pixel ({dev})",
                  up is not None and not up["on"] and up["vis"] == "hidden" and dn["on"] and dn["vis"] == "visible" and dn["op"] > 0.99
                  and dn["tlBottom"] < dn["foot"] + 4 and abs(dn["top"] - dn["foot"]) <= 1 and abs(dn["left"] - dn["cardLeft"]) <= 1 and abs(dn["w"] - dn["cardW"]) <= 1,
                  f"in view: on {up and up['on']} ({up and up['vis']}); scrolled down: on {dn['on']}, top {dn['top']:.1f} under a header ending {dn['foot']:.1f}, "
                  f"left {dn['left']:.1f} / the card's {dn['cardLeft']:.1f}, width {dn['w']:.1f} / {dn['cardW']:.1f}")
            check(f"{_n}: it is painted over what passes under it, and the header over it ({dev})",
                  dn["mid"] == "copy" and dn["lane"] == "copy" and (dn["foot"] == 0 or dn["head"] == "header"),
                  f"at its words: {dn['mid']}, its lane: {dn['lane']}, the header's foot: {dn['head']}")
            p = dn["p"] or {}
            fill = (p.get("end", 0) - p.get("start", 0)) / p["width"] if p.get("width") else 0
            check(f"{_n}: it frames the loop, the loop filling most of it, and says the one line's length and beats ({dev})",
                  fill >= 0.7 and dn["words"] == " · ".join(dn["line"].split(" · ")[:2]) == "8.00s · 16 beats",
                  f"the loop {fill:.0%} of it; it says {dn['words']!r}, the line {dn['line']!r}")
            check(f"{_n}: it glides in, frame by frame ({dev})", len(way) >= 3, f"{len(way)} frames on the way: " + ", ".join(f"{f[1]:.2f}" for f in way[:8]))
            # Its two ends are the timeline's sharp lines (lib/musictimeline.js
            # edge): as wide as 1.5px rounds to on the screen, on its pixels.
            fe = pg.evaluate(FOLLOW_EDGES)
            acc = tuple(int(fe["acc"][k:k + 2], 16) for k in (1, 3, 5)) if fe else None
            n_want = int(math.floor(1.5 * fe["d"] + 0.5)) if fe else 0
            ends = [sharp_cv(rows, acc, n_want) for rows in fe["ends"]] if fe else [(False, "nothing painted")]
            check(f"{_n}: its ends are the timeline's lines, sharp: as wide as 1.5px rounds to on the screen, the ground either side flat, "
                  f"read off its canvas ({dev})", all(ok for ok, _ in ends), "; ".join(f"{w}: {why}" for w, (ok, why) in zip(("start", "end"), ends)))
            # One press of End +, a bar: the end at once, then the framing eases.
            pg.evaluate(FOLLOW_REC)
            pg.click('.nudge-btn[data-which="end"][data-amount="1"]')
            pg.wait_for_timeout(800)
            spans = [f[2][1] for f in pg.evaluate("() => window.__frec") if f[2]]
            after = pg.evaluate(FOLLOW)
            moving = [s for s in spans if abs(s - spans[0]) > 1e-3 and abs(s - spans[-1]) > 1e-3] if spans else []
            m = max((after["e"] - after["s"]) / 7, 0.5)
            want = min(after["e"] + m, 30) - max(0, after["s"] - m)
            check(f"{_n}: a press of End + moves its end at once, then it eases to frame the new loop, frame by frame ({dev})",
                  abs(after["e"] - 12.25) < 1e-6 and len(moving) >= 3 and all(b2 >= a2 - 1e-6 for a2, b2 in zip(spans, spans[1:]))
                  and bool(spans) and abs(spans[-1] - want) < 0.01 and after["words"] == "10.00s · 20 beats",
                  f"the end at {after['e']:.3f}; the framing {spans[0] if spans else 0:.2f}s -> {spans[-1] if spans else 0:.2f}s (wanted {want:.2f}), "
                  f"{len(moving)} frames on the way; it says {after['words']!r}")
            # A tap on it: back up to the timeline, the drawer still open, and the copy goes.
            tapped = press(pg, "#musicFollow", 1100); browsing.wait_scroll_still(pg)
            back = pg.evaluate(FOLLOW)
            check(f"{_n}: a tap on it takes the page back up to the timeline, the drawer still open, and it goes ({dev})",
                  tapped and back["open"] and back["tlBottom"] - back["tlTop"] > 50 and back["tlTop"] >= back["foot"] - 1 and back["tlBottom"] <= back["vh"] + 1 and not back["on"],
                  f"tapped {tapped}; drawer open {back['open']}; the timeline {back['tlTop']:.0f}-{back['tlBottom']:.0f} under a header ending {back['foot']:.0f}, of a {back['vh']}px screen; the copy on {back['on']}")
            check(f"{_n}: no page errors from the copy ({dev})", not errs, "; ".join(errs[:2]))
            c.close()
    for _n, _p in eds("follow"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **SMALL_SIDEWAYS))
        c, pg, errs = editor(b, _n, _p, song=LONG, ctx=c, door="exact")
        pg.evaluate(TUNED)
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })")
        waits.settle(pg, 700)
        pg.evaluate(FOLLOW_REC)
        pg.evaluate(DOWN); pg.wait_for_timeout(600)
        way = [f for f in pg.evaluate("() => window.__frec") if 0.02 < f[1] < 0.98]
        pg.evaluate(FOLLOW_REC)
        pg.click('.nudge-btn[data-which="end"][data-amount="1"]'); pg.wait_for_timeout(600)
        spans = [f[2][1] for f in pg.evaluate("() => window.__frec") if f[2]]
        moving = [s for s in spans if abs(s - spans[0]) > 1e-3 and abs(s - spans[-1]) > 1e-3] if spans else []
        on = pg.evaluate(FOLLOW)["on"]
        check(f"{_n}: under Reduce Motion the copy is there at once, and so is its new framing",
              on and not way and len(spans) > 2 and abs(spans[-1] - spans[0]) > 0.5 and not moving,
              f"on {on}; {len(way)} frames fading, {len(moving)} frames easing, the framing {spans[0] if spans else 0:.2f}s -> {spans[-1] if spans else 0:.2f}s")
        c.close()

    print("\nMUSIC DOORS — Play with my drawing")
    for _n, _p in eds("play"):
        c, pg, errs = editor(b, _n, _p)
        was = pg.evaluate(SAID)["play"]
        pg.click("#musicPlayBtn"); pg.wait_for_timeout(500)
        st = pg.evaluate("() => ({ play: playing, pv: previewingLoop, label: document.getElementById('musicPlayLabel').textContent })")
        pg.click(PLAY[_n]); pg.wait_for_timeout(400)
        after = pg.evaluate("() => ({ play: playing, label: document.getElementById('musicPlayLabel').textContent })")
        pg.click(PLAY[_n]); pg.wait_for_timeout(500)
        theirs = pg.evaluate("() => ({ play: playing, label: document.getElementById('musicPlayLabel').textContent })")
        if theirs["play"]:
            pg.click(PLAY[_n]); pg.wait_for_timeout(300)
        check(f"{_n}: Play with my drawing is the editor's own Play, and follows it however it is pressed",
              was == f"Play with my {WORK[_n]}" and st["play"] and not st["pv"] and st["label"] == f"Stop the {WORK[_n]}"
              and not after["play"] and after["label"] == was and theirs["play"] and theirs["label"] == f"Stop the {WORK[_n]}",
              f"{was!r}; pressed: {st}; the editor's Play stopped it: {after}; the editor's Play started it: {theirs}")
        c.close()
    for _n, _p in eds("play"):
        c, pg, _ = editor(b, _n, _p, drawn=False)
        was = pg.evaluate("() => ({ label: document.getElementById('musicPlayLabel').textContent, off: document.getElementById('musicPlayBtn').disabled })")
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(500)
        st = pg.evaluate("() => ({ play: playing, pv: previewingLoop, hear: document.getElementById('musicHearLabel').textContent })")
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(300)
        stop = pg.evaluate("() => ({ pv: previewingLoop, hear: document.getElementById('musicHearLabel').textContent })")
        check(f"{_n}: with nothing drawn, Play with my drawing waits, and Hear the loop plays the music on its own",
              was == {"label": f"Play with my {WORK[_n]}", "off": True} and not st["play"] and st["pv"] and st["hear"] == "Stop the loop"
              and not stop["pv"] and stop["hear"] == "Hear the loop",
              f"Play: {was}; Hear the loop pressed: {st}; again: {stop}")
        c.close()

    print("\nMUSIC DOORS — kind, not jumpy")
    # A door opened as a song lands (the Restart door, the tallest, as soon as
    # its tile is on the screen, a quick person): the app's own scrolls are
    # still settling then -- the drawer's open and the card's growth each
    # re-assert at 300, 700 and 1200ms -- and the door makes the drawer taller
    # under them. (It was More, which held all four.) The tap is at the
    # tile's place on the screen: Playwright's own click scrolls a control
    # into view at once first, and on a phone held sideways, where the tile is
    # still below the screen 400ms on, that was a 207px frame of the test's
    # own making. On Flip held sideways the growth's reveal stops short of the
    # tile for the dock (lib/drawerdetent.js: "a short phone may still leave
    # the last row to scroll to"), so there a person scrolls to it first, and
    # so does this. Read the tile on every frame: no frame may
    # carry it more than 160px (a glide's frames measured 44-57px when this
    # was the level switch; a re-assert chasing the new end, 236-684px), and
    # it ends in sight, on a desk and on a phone held sideways, where the
    # drawer is taller than the screen. Each frame's time is kept and said. Beside other
    # suites a frame of the reveal lasted up to 150ms, and a glide seen
    # through one is one big step (165px once, in a run beside two others): a
    # red in a long frame is told apart by a run alone. Allowing a long frame
    # more would hide a chase: one measured 424px in a 176ms frame, under the
    # 3px a millisecond tried.
    for _n, _p in eds("kind"):
        for dev, o in (("desk", DESK), ("phone sideways", SIDEWAYS)):
            c = waits.instrument(b.new_context(**o))
            pg = c.new_page()
            browsing.goto(pg, BASE, _p)
            pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
            browsing.pad_drawer(pg, "music", settle=50)
            pg.set_input_files("#musicInput", SHORT)
            pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
            pg.wait_for_timeout(400)
            ON = "() => { const r = " + TILE + ".getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }"
            for _ in range(30):
                if pg.evaluate(ON):
                    break
                pg.wait_for_timeout(50)
            wheel = 0
            while not pg.evaluate(ON) and wheel < 12:
                pg.mouse.wheel(0, 100); pg.wait_for_timeout(150); wheel += 1
            at = pg.evaluate("() => { const r = " + TILE + ".getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
            pg.evaluate("""() => { window.__tops = []; const s = """ + TILE + """, t0 = performance.now();
                (function f() { window.__tops.push([performance.now(), s.getBoundingClientRect().top]);
                  if (performance.now() - t0 < 1900) requestAnimationFrame(f); })(); }""")
            pg.mouse.click(*at)
            pg.wait_for_timeout(2100)
            tops = pg.evaluate("() => window.__tops")
            r = pg.evaluate(SIGHT)
            big = max((abs(b[1] - a[1]), b[0] - a[0]) for a, b in zip(tops, tops[1:])) if len(tops) > 1 else None
            check(f"{_n}: a door opened as a song lands glides, and keeps its tile in sight ({dev})",
                  big is not None and big[0] <= 160 and r["header"] <= r["seg"] < r["vh"] - 40,
                  f"the biggest frame {round(big[0]) if big else None}px, in a {round(big[1]) if big else None}ms frame,"
                  f" over {len(tops)} frames; ends at {r}" + (f"; scrolled to it first ({wheel} turns of the wheel)" if wheel else ""))
            c.close()
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, drawn=False, opts=PHONE, door="restart")
        pg.wait_for_timeout(1300)   # past every re-assert there is
        # Closed with its tile just under the header and the door's end below
        # the screen: the drawer loses a third of its height, which near the page's
        # end is a clamp. Read the tile on every frame. With the timeline up
        # under the header its copy shows there (lib/musicdrawer.js) and covers
        # what passes under it, so the tile goes just under the copy, where a
        # person sees it and taps it: under the copy, the tap landed on the
        # copy, and Playwright scrolled the page to the tile in one 739px frame.
        UNDER = ("() => { const s = " + TILE + ", h = document.querySelector('.header'), f = document.getElementById('musicFollow');"
                 " const head = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;"
                 " const top = f && f.classList.contains('on') ? Math.max(head, parseFloat(f.style.top) + f.offsetHeight) : head;"
                 " window.scrollBy(0, s.getBoundingClientRect().top - top - 10); }")
        pg.evaluate(UNDER); browsing.wait_scroll_still(pg)
        pg.wait_for_timeout(300); pg.evaluate(UNDER); browsing.wait_scroll_still(pg)
        pg.evaluate("""() => { window.__tops = []; const s = """ + TILE + """, t0 = performance.now();
            (function f() { window.__tops.push(s.getBoundingClientRect().top); if (performance.now() - t0 < 1400) requestAnimationFrame(f); })(); }""")
        pg.click(tile("restart"))
        pg.wait_for_timeout(1500)
        tops = pg.evaluate("() => window.__tops")
        steps = [abs(tops[i] - tops[i - 1]) for i in range(1, len(tops))]
        moved = abs(tops[-1] - tops[0]) if tops else 0
        check(f"{_n}: closing a door from the drawer's end glides: its tile never leaps",
              len(tops) > 20 and moved > 40 and max(steps) < 0.45 * moved,
              f"moved {moved:.0f}px over {len(tops)} frames, the biggest frame {max(steps) if steps else 0:.0f}px")
        c.close()
    # A DRAWER TALLER THAN THE SCREEN OPENS AT ITS TOP (the owner's iPhone:
    # "When you click the media button and click music it open all the way to
    # the bottom?"). The open scrolled the drawer's end to the screen's foot,
    # which took the tabs, the song and the strip up under the header; More
    # was open then, remembered, and the doors start shut now, but the music
    # drawer is still taller than a 390x640 phone. The bar above the drawer
    # stays under the header, as a song landing already left it
    # (lib/drawerdetent.js); on the owner's phone, where the drawer fits, it
    # opens with its end on screen; and a person who scrolls on as it opens
    # is left where they scrolled to. Media and Music tapped as a person taps
    # them, the page at rest at its top first.
    TOP = """() => { const h = document.querySelector('.header'), q = (s) => document.querySelector(s).getBoundingClientRect();
      const head = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
      const dock = document.querySelector('#toolBar, .flip-tools');
      return { head: Math.round(head), dock: Math.round(dock.getBoundingClientRect().top), tabs: Math.round(q('#mediaTabs').top),
               end: Math.round(q('#mediaCard').bottom), vh: Math.round(visualViewport ? visualViewport.height : innerHeight), y: Math.round(scrollY) }; }"""
    SHORT_PHONE = dict(PHONE, viewport={"width": 390, "height": 640})
    def reopen(pg, settle):
        browsing.pad_drawer_close(pg)
        pg.wait_for_function("() => window.scrollY === 0", timeout=5000); pg.wait_for_timeout(300)
        pg.click("#mediaOpenBtn"); pg.wait_for_timeout(150)
        if pg.get_attribute("#mediaTabMusic", "aria-selected") != "true":
            pg.click("#mediaTabMusic")
        pg.wait_for_timeout(settle)
    for _n, _p in eds("kind"):
        got = {}
        for dev, o in (("short phone", SHORT_PHONE), ("phone", PHONE)):
            c, pg, _ = editor(b, _n, _p, opts=o)
            reopen(pg, 1500)                           # past every re-assert there is
            got[dev] = pg.evaluate(TOP)
            c.close()
        tall, fits = got["short phone"], got["phone"]
        check(f"{_n}: a drawer taller than the screen opens at its top, the bar under the header and the tabs on screen; one that fits shows its end",
              tall["end"] > tall["vh"] and tall["head"] - 1 <= tall["dock"] <= tall["head"] + 12 and tall["head"] <= tall["tabs"] < tall["vh"]
              and fits["end"] <= fits["vh"] + 1 and fits["dock"] >= fits["head"] - 1,
              f"390x640, the drawer's end at {tall['end']} on a {tall['vh']}px screen: {tall}; 402x874, where it fits: {fits}")
    # (With the doors shut the 390x640 page has about 90px left below the
    # opening's place, so a scroll on is 40px or more, not the 100 there was.)
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, opts=SHORT_PHONE)
        reopen(pg, 250)
        at = pg.evaluate(TOP)
        pg.mouse.move(200, 500); pg.mouse.wheel(0, 300); pg.wait_for_timeout(150)
        put = pg.evaluate(TOP)
        pg.wait_for_timeout(1500)
        left = pg.evaluate(TOP)
        check(f"{_n}: a person who scrolls on as the drawer opens is left where they scrolled to",
              put["y"] > at["y"] + 40 and abs(left["y"] - put["y"]) <= 2,
              f"opening at {at['y']}, scrolled on to {put['y']}, then {left['y']} once the opening's re-asserts were done")
        c.close()
    # A SONG LANDING IS THE NEWER REVEAL (main went red after the fix above:
    # verify_parity's switch moved 29px on Flip and 5px on the Pad between two
    # reads). The opening re-asserts its place either way until 1.2s; a song
    # landing in that time grows the drawer and glides to its new end, and the
    # opening's re-asserts, aimed at the end before it grew, snapped that glide
    # short and pulled back a page moved on since. Here the song lands as the
    # drawer opens, the page is taken on down to its foot, past where the
    # growth left it (bringing the bin into view, verify_parity's move, did
    # that on the strip's shorter drawer; on the timeline's it moves the page
    # up, into the growth's own hold on the card's end, which rightly brings
    # it back), and the page is read on every frame until the opening's last
    # re-assert is past. Nothing may move it. The page is taken there well
    # inside that time (said), or this row could not tell.
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, drawn=False, song=None, opts=DESK)
        browsing.pad_drawer(pg, "music", settle=50)
        opened = pg.evaluate("() => performance.now()")
        pg.set_input_files("#musicInput", SHORT)
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
        pg.wait_for_timeout(300)
        got = pg.evaluate("""() => new Promise((done) => {
            scrollTo(0, document.scrollingElement.scrollHeight);
            const ys = [], t0 = performance.now();
            (function f() { ys.push(Math.round(scrollY));
              if (performance.now() - t0 < 1400) requestAnimationFrame(f); else done({ ys, t0 }); })(); })""")
        ys, early = got["ys"], got["t0"] - opened
        check(f"{_n}: a song landing as the drawer opens is the newer reveal: nothing pulls the page back after it",
              len(ys) > 20 and early < 1000 and max(ys) - min(ys) <= 1,
              f"the page taken to its foot {early:.0f}ms after the drawer opened, at {ys[0]}px;"
              f" over {len(ys)} frames it went {min(ys)}-{max(ys)}px")
        c.close()
    # A PERSON WHO SCROLLS BACK UP AS A SONG LANDS IS LEFT THERE. The growth's
    # hold (lib/drawerdetent.js followGrowth) only ever pushed down, so a scroll
    # up to the drawing came straight back to the drawer's end at its next
    # re-assert, 300px in one frame. The drawer open and past the opening's own
    # re-asserts, a song lands, and a person scrolls up while the growth's are
    # still due: a finger on the owner's phone, a wheel and Page Up on a desk.
    # The page is read on every frame from the song landing until the last
    # re-assert is past, and from a quarter second after they let go it stays
    # where they put it. When they let go is said: after the last re-assert,
    # this row could not tell.
    for _n, _p in eds("kind"):
        for how, o in (("a finger on the phone", PHONE), ("a wheel on a desk", DESK), ("Page Up on a desk", DESK)):
            c, pg, _ = editor(b, _n, _p, drawn=False, song=None, opts=o)
            browsing.pad_drawer(pg, "music", settle=50)
            pg.wait_for_timeout(1400)                       # past the opening's re-asserts
            cdp = c.new_cdp_session(pg) if o is PHONE else None
            pg.set_input_files("#musicInput", SHORT)
            pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer", timeout=20000)
            pg.evaluate("""() => { window.__ys = []; const t0 = window.__t0 = performance.now();
                (function f() { __ys.push([performance.now() - t0, Math.round(scrollY)]);
                  if (performance.now() - t0 < 1900) requestAnimationFrame(f); })(); }""")
            pg.wait_for_timeout(350)
            was = pg.evaluate("() => Math.round(scrollY)")
            if cdp:
                tab = pg.evaluate("() => { const r = document.getElementById('mediaTabs').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")

                def touch(kind, y):
                    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": tab[0], "y": y}]})
                touch("touchStart", tab[1])
                for k in range(1, 9):
                    touch("touchMove", tab[1] + k * 30); pg.wait_for_timeout(16)
                for _ in range(3):                         # held still, so it lets go with no fling
                    touch("touchMove", tab[1] + 240); pg.wait_for_timeout(16)
                touch("touchEnd", tab[1] + 240)
            elif how.startswith("a wheel"):
                pg.mouse.move(640, 450); pg.mouse.wheel(0, -300)
            else:
                pg.keyboard.press("PageUp")
            let_go = pg.evaluate("() => performance.now() - window.__t0")
            pg.wait_for_timeout(250)
            put = pg.evaluate("() => Math.round(scrollY)")
            pg.wait_for_timeout(1500)
            after = [y for t, y in pg.evaluate("() => window.__ys") if t >= let_go + 250]
            check(f"{_n}: a person who scrolls back up as a song lands is left where they scrolled to ({how})",
                  was - put >= 100 and let_go < 1100 and len(after) > 20 and max(abs(y - put) for y in after) <= 2,
                  f"the page at {was}px, scrolled up to {put}px, let go {let_go:.0f}ms after the song landed;"
                  f" then over {len(after)} frames {min(after) if after else None}-{max(after) if after else None}px")
            c.close()
    # A DRAFT OPENED SAYS ITS OWN SMOOTH RESTART (the owner's Flip: "19.75s"
    # over a switch that said Off). A draft with a 0.25s smooth restart, saved,
    # then opened over a song whose smooth restart was switched off: the line,
    # the switch, its words and its length agree. Flip's draft and file opens
    # set the loop and repainted all but the switch's row.
    SAVE = {"Pad": "() => JSON.stringify(serializeSkribl())", "Flip": "() => JSON.stringify(serializeFlip())"}
    OPEN = {"Pad": "(s) => loadSkribl(JSON.parse(s))", "Flip": "(s) => applyFlipDraftObject(JSON.parse(s))"}
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, opts=PHONE, song=LONG, door="restart")
        saved = pg.evaluate(SAVE[_n])
        was = pg.evaluate(TRIM)
        pg.click("#musicSmooth"); pg.wait_for_timeout(200)
        off = pg.evaluate(SAID)
        pg.evaluate(OPEN[_n], saved)
        pg.wait_for_function("() => !!currentAudioBuffer && audioDuration > 25", timeout=20000)
        pg.wait_for_timeout(1200)
        t, said = pg.evaluate(TRIM), pg.evaluate(SAID)
        val = pg.evaluate("() => document.getElementById('crossfadeVal').textContent")
        check(f"{_n}: a draft opened says its own smooth restart: the line, the switch, its words and its length agree",
              was["xf"] == 250 and off["smooth"] == "false" and t["xf"] == 250 and said["smooth"] == "true" and val == "0.25s"
              and said["smoothSub"] == "The end fades into the start over 0.25s, which makes the loop 0.25s shorter."
              and said["line"].startswith(f"{heard(t):.2f}s"),
              f"saved with {was['xf']}ms, switched off ({off['smooth']}), opened: {t['xf']}ms, the switch {said['smooth']}, "
              f"its length {val!r}, the line {said['line']!r}")
        c.close()

    b.close()

summarise_and_exit()
