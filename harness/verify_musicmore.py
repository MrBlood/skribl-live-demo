#!/usr/bin/env python3
"""The music drawer's one view, and More (lib/musicdrawer.js), on the Pad and on Flip.

The owner, with the drawer at three levels: "The music drawer is so
complicated. I think I liked it better before you did so much to it," then
"we'll need to streamline it," and yes to the step 2 mock's five defaults.
The view is the timeline (step 2; it was the strip), the one line under it,
the pair that plays, Fit my drawing and Whole song, and More; More holds the
rest, the Restart view and Cut on silence among it (verify_musictimeline.py
has how those work). verify_music.py keeps
how each control works (the previews, the switch, Fit's sum on Flip) and
verify_musicbeat.py the beat; this keeps where each one lives, what the drawer
says, and More itself. It was verify_musiclevels.py, the three levels'.

The rows:

  THE VIEW AND MORE. A new drawer opens on the one view. More opens the
  restart, the beat, exact times and how it loops, each under its name, and
  what it holds is `hidden` while it is closed (so out of the Tab order too).
  Opening and closing keep the loop. It unfolds and folds away joined to its
  tile, as the draw drawer's tiles do, and at once under Reduce Motion. No
  line shows where they join, read on the screenshot's pixels in light and
  dark (the card's dark top light, a 1px inset, once showed under the tile),
  and the card's side edges run unbroken past it.
  Whether it is open is remembered, by the other editor too; the old Adjust
  opens closed.

  THE ONE LINE. A new song starts on Skribl's pick: the first 20 seconds (the
  whole song when it is shorter), with a smooth restart; on the Pad a drawing
  already there sets the length instead, what is heard as long as the
  drawing. The line says the length heard, the beats once there is a tempo,
  and against the drawing, then Skribl's pick or the way back; the way back
  has an Undo, which goes after eight seconds. Nobody is told they did
  something: a drawing that changed under the pick shows the way back and no
  more. Its height never changes as it says other things. A song a draft
  brings back keeps the draft's loop.

  THE PICKS. Fit counts the smooth restart (what is heard is as long as the
  drawing; Match Drawing Time fell short by the crossfade). Whole song loops
  all of a short song and a long one's first 20 seconds, and says which. The
  one that describes the loop wears the one tint. With nothing drawn Fit is
  off and says why, and wakes when a drawing is made with the drawer open.

  SMOOTH RESTART. One switch, on at its last length and off to a clean cut;
  the line counts what is heard.

  EXACT TIMES. A typed time moves its end (a comma is a point); a time that
  is not one puts the loop's own back. - and + move 0.1s, or a bar once there
  is a tempo, and their names and the line under them say which. Lock the
  length moves both ends together. Every field that takes text is 16px (A11Y
  11b; these are built hidden).

  PLAY. Play with my drawing is the editor's own Play and follows it however
  it is pressed; with nothing drawn it waits, and Hear the loop, beside it,
  plays the music on its own (verify_musicbeat has the rest).

  KIND, NOT JUMPY. More opened as a song lands never takes the tile just
  tapped out of sight, and closing it from the drawer's end glides: the tile
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
    print("No assertions were executed. This is NOT evidence the music drawer has its one view and More.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICMORE_ONLY=Pad (or Flip) runs one editor, and
# MUSICMORE_PART=more (pick, line, picks, smooth, exact, play, kind) one part,
# so a row can be shown red in seconds. A real run sets neither.
ONLY = os.environ.get("MUSICMORE_ONLY", "")
PART = os.environ.get("MUSICMORE_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def part(name):
    return not PART or PART == name


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if part(name) else []
DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
SIDEWAYS = dict(viewport={"width": 874, "height": 402}, device_scale_factor=2, is_mobile=True, has_touch=True)
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
SAID = """() => { const q = (id) => document.getElementById(id);
  return { line: q('musicPickText').textContent, tag: !q('musicPickTag').hidden, back: !q('musicBackPick').hidden, undo: !q('musicPickUndo').hidden,
           fit: q('matchDrawingBtn').getAttribute('aria-pressed'), fitOff: q('matchDrawingBtn').disabled, fitSub: q('musicFitSub').textContent,
           whole: q('musicWholeBtn').getAttribute('aria-pressed'), wholeName: q('musicWholeName').textContent, wholeSub: q('musicWholeSub').textContent,
           play: q('musicPlayLabel').textContent, step: q('musicStepLine').textContent,
           smooth: q('musicSmooth').getAttribute('aria-checked'), smoothSub: q('musicSmoothSub').textContent }; }"""
# Shown: no [hidden] on the way up, and a box. Hidden: a [hidden] on the way up.
SHOWN = """(ids) => ids.filter((id) => { const el = document.getElementById(id);
  return !!el && !el.closest('[hidden]') && el.getClientRects().length > 0; })"""
# Where More's tile is, against the pinned header (0 where the header scrolls away) and the screen.
SIGHT = """() => { const s = document.getElementById('fineTuneToggle').getBoundingClientRect(), h = document.querySelector('.header');
  const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
  return { seg: Math.round(s.top), header: Math.round(top), vh: innerHeight }; }"""
VIEW = ["musicTimeline", "musicPickLine", "musicPlayBtn", "previewLoopBtn", "matchDrawingBtn", "musicWholeBtn", "fineTuneToggle"]
MORE = ["fineTuneBody", "musicSmooth", "musicRestart", "crossfadeSlider", "testSeamBtn", "musicTapBtn",
        "startReadout", "endReadout", "musicStepLine", "musicCut", "musicLock"]
ALL = sorted(set(VIEW + MORE))
SECTIONS = ["The restart", "The beat", "Exact times", "How it loops"]


def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=SHORT, ctx=None, opts=DESK, more=False):
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
    if more:
        set_more(pg, True)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def set_more(pg, want):
    """More open or closed, by its tile, as a person does."""
    if (pg.get_attribute("#fineTuneToggle", "aria-expanded") == "true") != want:
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(350)
        browsing.wait_scroll_still(pg)


# Where More's tile meets what it opens, as painted (verify_drawtiles reads the
# draw drawer's tiles the same way): the largest step from the card's colour
# over the rows from the tile's bottom border to 3px into the card, across the
# tile's inside, and the smallest on each side edge at the joint (0 is a break,
# which a cover the tile's whole width paints).
JOINT = """() => { const t = document.getElementById('fineTuneToggle'), p = document.getElementById('fineTuneBody');
  t.scrollIntoView({ block: 'center', behavior: 'instant' });
  const a = t.getBoundingClientRect(), z = p.getBoundingClientRect();
  return { a: [a.left, a.top, a.right, a.bottom], z: [z.left, z.top, z.right, z.bottom], card: getComputedStyle(p).backgroundColor }; }"""


def seam(pg, dpr=1):
    from PIL import Image
    j = pg.evaluate(JOINT)
    a, z = j["a"], j["z"]
    card = [int(v) for v in re.findall(r"\d+", j["card"])[:3]]
    x0, y0 = min(a[0], z[0]) - 2, a[3] - 6
    im = Image.open(io.BytesIO(pg.screenshot(clip={"x": x0, "y": y0, "width": max(a[2], z[2]) + 2 - x0, "height": 14}))).convert("RGB")
    w, h = im.size

    def step(x, y):
        c = im.getpixel((min(w - 1, max(0, int((x - x0) * dpr))), min(h - 1, max(0, int((y - y0) * dpr)))))
        return max(abs(c[i] - card[i]) for i in range(3))
    inside = [a[0] + 2 + i / dpr for i in range(int((a[2] - a[0] - 4) * dpr))]
    worst = max(step(x, a[3] - 1 + i / dpr) for i in range(int(4 * dpr)) for x in inside)
    edges = [min(step(col, a[3] - 4 + i / dpr) for i in range(int(8 * dpr))) for col in (a[0] + .5 / dpr, a[2] - .5 / dpr)]
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

    print("\nMUSIC MORE — the one view, and More")
    for _n, _p in eds("more"):
        c, pg, errs = editor(b, _n, _p)
        closed = set(pg.evaluate(SHOWN, ALL))
        tile = pg.evaluate("() => { const t = document.getElementById('fineTuneToggle');"
                           " return [t.querySelector('.mt-k').textContent, t.querySelector('.mt-v').textContent, t.getAttribute('aria-expanded'), t.getAttribute('aria-controls')]; }")
        # The drawn mark the tile ends on (lib marks, _skribl_marks.html): + closed, - open.
        MARK = "() => ['.mk-plus', '.mk-minus'].filter(s => { const m = document.querySelector('#fineTuneToggle ' + s); return m && getComputedStyle(m).display !== 'none'; })"
        mark_closed = pg.evaluate(MARK)
        check(f"{_n}: a new drawer opens on the one view: the timeline, the one line, the pair that plays, the two picks and More, and nothing deeper",
              closed == set(VIEW) and tile == ["More", "The restart, the beat, exact times", "false", "fineTuneBody"],
              f"extra {sorted(closed - set(VIEW))}, missing {sorted(set(VIEW) - closed)}; the tile {tile}")
        set_more(pg, True)
        opened = set(pg.evaluate(SHOWN, ALL))
        heads = pg.evaluate("() => [...document.querySelectorAll('#fineTuneBody > .mt-sect')].map(p => p.textContent)")
        mark_open = pg.evaluate(MARK)
        check(f"{_n}: More opens the restart, the beat, exact times and how it loops, each under its name",
              opened == set(VIEW + MORE) and heads == SECTIONS and pg.get_attribute("#fineTuneToggle", "aria-expanded") == "true",
              f"extra {sorted(opened - set(VIEW + MORE))}, missing {sorted(set(VIEW + MORE) - opened)}; {heads}")
        check(f"{_n}: More's tile ends on a drawn +, and a - while it is open",
              mark_closed == [".mk-plus"] and mark_open == [".mk-minus"], f"closed {mark_closed}, open {mark_open}")
        # Joined: the open tile reaches over the card's top edge and is above it,
        # so the point just inside the card's edge is the tile's.
        j = pg.evaluate("""() => { const t = document.getElementById('fineTuneToggle'), d = document.getElementById('fineTuneBody');
            t.scrollIntoView({ block: 'center' }); const a = t.getBoundingClientRect(), r = d.getBoundingClientRect();
            const at = document.elementFromPoint(r.left + r.width / 2, r.top + 0.5);
            return { over: +(a.bottom - r.top).toFixed(2), same: Math.abs(a.left - r.left) < 0.5 && Math.abs(a.right - r.right) < 0.5,
                     tile: !!at && t.contains(at), open: t.classList.contains('open') }; }""")
        check(f"{_n}: open, More's tile and what it opens are one shape, the tile over the card's edge",
              j["open"] and j["same"] and j["tile"] and 0.5 <= j["over"] <= 1.5, str(j))
        painted = {}
        for scheme in ("light", "dark"):
            pg.emulate_media(color_scheme=scheme); pg.wait_for_timeout(150)
            painted[scheme] = seam(pg)
        pg.emulate_media(color_scheme="light")
        check(f"{_n}: no line shows where More's tile meets what it opens, light or dark (painted pixels: the rows "
              "at the joint are the card's colour), and the card's side edges run unbroken past it",
              all(w <= 2 and min(e) >= 4 for w, e in painted.values()),
              "; ".join(f"{s}: largest step from the card at the joint {w} (2 at most), the edges' smallest {e} (4 at least)"
                        for s, (w, e) in painted.items()))
        set_more(pg, False)
        pg.wait_for_timeout(300)
        tab = pg.evaluate("(ids) => ids.filter((id) => !document.getElementById(id).closest('[hidden]'))", MORE)
        check(f"{_n}: what More holds is hidden while it is closed, so out of the Tab order too",
              not tab and pg.get_attribute("#fineTuneToggle", "aria-expanded") == "false", f"not [hidden] with More closed: {tab}")

        # Opening and closing keep the loop: an own loop and smooth restart, through twice.
        set_more(pg, True)
        pg.evaluate("() => { trimStart = 0.7; trimEnd = 3.9; updateTrimUI(); }")
        pg.evaluate("() => { const s = document.getElementById('crossfadeSlider'); s.value = '120'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        before = pg.evaluate(TRIM)
        seen = []
        for want in (False, True, False):
            set_more(pg, want)
            pg.wait_for_timeout(250)
            seen.append(pg.evaluate(TRIM))
        check(f"{_n}: opening and closing More keeps the loop",
              all(t == before for t in seen) and before["xf"] == 120, f"{before} then {seen}")

        # It unfolds and folds away: the animations themselves, read as the
        # tap lands (opacity from 0 in, to 0 out, the draw drawer's 220ms and
        # 180ms), and the frames, read on every one: some on the way in, and
        # on the way out with the tile still joined, then hidden. One frame
        # each way is the most a loaded machine guarantees: beside other
        # suites a frame lasted up to 100ms and the unfold's ease is past 98%
        # by half its time.
        FRAMES = """() => { window.__mf = []; const d = document.getElementById('fineTuneBody'), t = document.getElementById('fineTuneToggle'), t0 = performance.now();
            (function f() { window.__mf.push([Math.round(performance.now() - t0), d.hidden, +getComputedStyle(d).opacity, t.classList.contains('open')]);
              if (performance.now() - t0 < 600) requestAnimationFrame(f); })();
            t.click();
            return d.getAnimations().map(a => { const k = a.effect.getKeyframes(); return [+k[0].opacity, +k[k.length - 1].opacity, a.effect.getTiming().duration]; }); }"""
        a_up = pg.evaluate(FRAMES); pg.wait_for_timeout(700)
        up = pg.evaluate("() => window.__mf")
        a_down = pg.evaluate(FRAMES); pg.wait_for_timeout(700)
        down = pg.evaluate("() => window.__mf")
        mid_up = [f for f in up if not f[1] and 0.02 < f[2] < 0.98]
        mid_down = [f for f in down if not f[1] and 0.02 < f[2] < 0.98 and f[3]]
        check(f"{_n}: More unfolds, and folds away joined to its tile before it goes",
              a_up == [[0, 1, 220]] and a_down == [[1, 0, 180]] and len(mid_up) >= 1 and len(mid_down) >= 1
              and down[-1][1] and not down[-1][3],
              f"animations {a_up} in, {a_down} out; {len(mid_up)} frames on the way in, {len(mid_down)} on the way out; last {down[-1] if down else None}")
        check(f"{_n}: no page errors through More", not errs, "; ".join(errs[:2]))
        c.close()

    # More's + sits on its words' line in any font: a centred line box
    # centres the font's ascent and descent, not the letters, and fonts split
    # those differently (the record clock's lesson, verify_ux). The words are
    # one block, which lib/labels.js trims to cap height (labels.css
    # .lbl-own; a flex row cannot be trimmed), so the INK is measured, in the page's
    # own face and in each installed face forced onto the tile: the + within
    # half a pixel of "More". The faces that split ascent and descent unlike
    # the app's are the ones that can tell: with the trim taken off, the + sat
    # 2px low in DejaVu Serif, 1.5 in FreeSerif, 1 in IPAPGothic and Inter
    # Display, and level in the sans faces; trimmed, within half a pixel in all.
    from PIL import Image as _Img
    import io as _io
    for _n, _p in eds("more"):
        c = waits.instrument(b.new_context(device_scale_factor=2, **DESK))
        c, pg, _ = editor(b, _n, _p, ctx=c, drawn=False)
        faces = [None] + pg.evaluate("""() => ['DejaVu Sans', 'Liberation Sans', 'FreeSans', 'Inter', 'Inter Display',
            'DejaVu Serif', 'FreeSerif', 'IPAPGothic'].filter(f => {
            const x = document.createElement('canvas').getContext('2d'), t = 'More The restart';
            x.font = '40px monospace'; const a = x.measureText(t).width;
            x.font = '40px "' + f + '", monospace'; return Math.abs(x.measureText(t).width - a) > 0.5; })""")
        off = {}
        for f in faces:
            pg.evaluate("""f => { let s = document.getElementById('moreFace'); if (!s) { s = document.createElement('style'); s.id = 'moreFace';
                document.head.appendChild(s); } s.textContent = f ? '#fineTuneToggle, #fineTuneToggle * { font-family: "' + f + '", sans-serif !important; }' : ''; }""", f)
            pg.wait_for_timeout(200)
            g = pg.evaluate("""() => { const t = document.getElementById('fineTuneToggle'); t.scrollIntoView({ block: 'center' });
                const r = t.getBoundingClientRect(), k = t.querySelector('.mt-k').getBoundingClientRect();
                const m = [...t.querySelectorAll('.mk')].find(e => getComputedStyle(e).display !== 'none').getBoundingClientRect();
                return { r: [r.left, r.top, r.width, r.height], k: [k.left - r.left, k.right - r.left], m: [m.left - r.left, m.right - r.left] }; }""")
            im = _Img.open(_io.BytesIO(pg.screenshot(clip={"x": g["r"][0], "y": g["r"][1], "width": g["r"][2], "height": g["r"][3]}))).convert("RGB")
            bg = im.getpixel((int((g["k"][1] + 4) * 2), 6))
            def centre(x0, x1):
                ys = [y for y in range(im.height) if any(sum(abs(a - b2) for a, b2 in zip(im.getpixel((x, y)), bg)) > 120
                                                       for x in range(int(x0 * 2) + 1, int(x1 * 2) - 1))]
                return (min(ys) + max(ys) + 1) / 4 if ys else None
            kc, mc = centre(*g["k"]), centre(*g["m"])
            off[f or "the page's own"] = None if kc is None or mc is None else round(mc - kc, 2)
        check(f"{_n}: More's + sits on its words' line, in every face there is to try",
              len(faces) >= 5 and all(v is not None and abs(v) <= 0.5 for v in off.values()),
              f"the + against the ink of More, px: {off}")
        c.close()

    # Reduce Motion: at once, both ways; nothing on the way.
    for _n, _p in eds("more"):
        c = waits.instrument(b.new_context(reduced_motion="reduce", **DESK))
        c, pg, _ = editor(b, _n, _p, ctx=c, drawn=False)
        pg.evaluate("""() => { window.__mf = []; const d = document.getElementById('fineTuneBody'), t0 = performance.now();
            (function f() { window.__mf.push([d.hidden, +getComputedStyle(d).opacity]); if (performance.now() - t0 < 2500) requestAnimationFrame(f); })(); }""")
        pg.click("#fineTuneToggle"); pg.wait_for_timeout(400); pg.click("#fineTuneToggle"); pg.wait_for_timeout(400)
        pg.wait_for_function("() => window.__mf.length && window.__mf[window.__mf.length - 1][0]", timeout=3000)
        fr = pg.evaluate("() => window.__mf")
        check(f"{_n}: under Reduce Motion More opens and closes at once, nothing on the way",
              fr and not [f for f in fr if not f[0] and f[1] < 0.999] and any(not f[0] for f in fr) and fr[-1][0], f"{len(fr)} frames, {fr[:3]} ... {fr[-2:]}")
        c.close()

    # Open or closed is one choice, kept for both editors (one origin, one key);
    # the old middle level, Adjust, opens closed.
    if part("more") and not ONLY:
        c = waits.instrument(b.new_context(**DESK))
        _, pad, _ = editor(b, "Pad", "/", ctx=c, drawn=False)
        set_more(pad, True)
        pad.reload(); browsing.goto(pad, BASE, "/"); add(pad, SHORT)
        again = pad.evaluate("() => [document.getElementById('fineTuneToggle').getAttribute('aria-expanded'), document.getElementById('fineTuneBody').hidden]")
        _, flip, _ = editor(b, "Flip", "/flip", ctx=c, drawn=False)
        there = flip.evaluate("() => [document.getElementById('fineTuneToggle').getAttribute('aria-expanded'), document.getElementById('fineTuneBody').hidden]")
        flip.evaluate("() => localStorage.setItem('skribl_music_level', 'adjust')")
        flip.reload(); browsing.goto(flip, BASE, "/flip"); add(flip, SHORT)
        adj = flip.evaluate("() => [document.getElementById('fineTuneToggle').getAttribute('aria-expanded'), document.getElementById('fineTuneBody').hidden]")
        check("whether More is open is remembered, on the other editor too, and the old Adjust opens it closed",
              again == ["true", False] and there == ["true", False] and adj == ["false", True],
              f"Pad after a reload {again}; Flip {there}; a saved Adjust {adj}")
        c.close()

    print("\nMUSIC MORE — Skribl's pick, and the one line")
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
            good = good and said["line"] == words and said["tag"] and not said["back"] and not said["undo"]
            ok = ok and good
            why.append(f"{'drawn' if drawn else 'blank'} {nm}: {t['s']:.2f}-{t['e']:.3f} xf {t['xf']} heard {h_:.3f} (drawing {secs:.3f}) {said['line']!r} tag {said['tag']}")
        check(f"{_n}: a new song starts on Skribl's pick, and the one line says so", ok, "; ".join(why))

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
        c, pg, errs = editor(b, _n, _p, more=True)
        pick = pg.evaluate(TRIM)
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(200)
        own, said = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: a change shows the way back in place of Skribl's pick",
              said["back"] and not said["tag"] and not said["undo"], f"{said['line']!r}, tag {said['tag']}, back {said['back']}, undo {said['undo']}")
        went = press(pg, "#musicBackPick")
        back, said2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        focus = pg.evaluate("() => document.activeElement && document.activeElement.id")
        undid = press(pg, "#musicPickUndo")
        undone, said3 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: Back to Skribl's pick puts it back, and its Undo undoes that",
              went and undid and back == pick and said2["tag"] and said2["undo"] and not said2["back"]
              and focus == "musicPickUndo" and undone == own and said3["back"] and not said3["tag"],
              f"pick {pick}, own {own}, back {back} (tag {said2['tag']}, undo {said2['undo']}, focus {focus}), undone {undone} (back {said3['back']}); pressed back {went}, undo {undid}")
        if _n == EDITORS[0][0]:
            # One shared timer (lib/musicdrawer.js), so one editor is asked.
            went = press(pg, "#musicBackPick", 8400)
            late = pg.evaluate(SAID)
            check("the Undo goes after eight seconds, and the line says Skribl's pick again",
                  went and not late["undo"] and not late["back"] and late["tag"],
                  str({k: late[k] for k in ('line', 'tag', 'undo', 'back')}) + f"; pressed back {went}")
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
        two, s0 = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        pg.evaluate("() => document.getElementById('undoBtn').click()"); pg.wait_for_timeout(400)
        one, s1 = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        press(pg, "#musicBackPick")
        t2, s2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check("Pad: an Undo with the drawer open shows the way back, no more, and Back to Skribl's pick fits the drawing again",
              s0["tag"] and s0["line"].endswith("· fits your drawing") and one < two - 0.5
              and s1["line"].endswith("· longer than your drawing") and s1["back"] and not s1["tag"] and s1["fit"] == "false"
              and abs(heard(t2) - one) < 0.002 and s2["fit"] == "true" and s2["tag"] and s2["line"].endswith("· fits your drawing"),
              f"{two:.2f}s then {one:.2f}s: {s1['line']!r}, back {s1['back']}; after the way back heard {heard(t2):.3f}s, fit {s2['fit']}, {s2['line']!r}")
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

    # The line's height never changes as it says other things: the pick, the
    # way back, the pick with its Undo, a tempo's beats, a longer length. Its
    # end has a share of its own, so it wraps below 540px whatever it says.
    for _n, _p in eds("line"):
        hs = {}
        for dev, o in (("phone", PHONE), ("desk", DESK)):
            c, pg, _ = editor(b, _n, _p, opts=o, more=True)
            H = "() => Math.round(document.getElementById('musicPickLine').getBoundingClientRect().height * 10) / 10"
            row = [pg.evaluate(H)]
            pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150); row.append(pg.evaluate(H))
            press(pg, "#musicBackPick"); row.append(pg.evaluate(H))
            pg.evaluate("() => { musicTempo = { bpm: 117, phase: 0.03 }; trimStart = 0.5; trimEnd = 5.9; updateTrimUI(); }")
            pg.wait_for_timeout(150); row.append(pg.evaluate(H))
            hs[dev] = row
            c.close()
        check(f"{_n}: the one line's height never changes as it says other things, on a phone and a desk",
              all(len(set(r)) == 1 for r in hs.values()) and hs["phone"][0] > hs["desk"][0],
              f"pick, own, back with its Undo, a tempo: {hs}")

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

    print("\nMUSIC MORE — Fit my drawing and Whole song")
    for _n, _p in eds("picks"):
        c, pg, _ = editor(b, _n, _p)
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
        check(f"{_n}: the pick that describes the loop wears the one tint",
              said["fit"] == "true" and said["whole"] == "false" and tint[0] == tint[1], f"fit {said['fit']}, whole {said['whole']}, {tint}")
        pg.click("#musicWholeBtn"); pg.wait_for_timeout(200)
        t2, said2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        add(pg, LONG)
        said3 = pg.evaluate(SAID)
        pg.evaluate("() => { trimStart = 3; trimEnd = 9; updateTrimUI(); }")
        pg.click("#musicWholeBtn"); pg.wait_for_timeout(200)
        t3 = pg.evaluate(TRIM)
        check(f"{_n}: Whole song loops all of a short song, and a long one's first 20 seconds, and says which",
              t2["s"] == 0 and abs(t2["e"] - 6) < 0.01 and said2["whole"] == "true" and said2["fit"] == "false"
              and (said2["wholeName"], said2["wholeSub"]) == ("Whole song", "6s")
              and (said3["wholeName"], said3["wholeSub"]) == ("Longest loop", "the first 20s") and t3["s"] == 0 and abs(t3["e"] - 20) < 0.001,
              f"short: {t2['s']:.2f}-{t2['e']:.2f} {said2['wholeName']!r} {said2['wholeSub']!r}; long: {said3['wholeName']!r} {said3['wholeSub']!r}, {t3['s']:.2f}-{t3['e']:.2f}")
        c.close()

    for _n, _p in eds("picks"):
        c, pg, _ = editor(b, _n, _p, drawn=False)
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

    print("\nMUSIC MORE — Smooth restart")
    for _n, _p in eds("smooth"):
        c, pg, _ = editor(b, _n, _p, more=True)
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

    print("\nMUSIC MORE — Exact times")
    for _n, _p in eds("exact"):
        c, pg, _ = editor(b, _n, _p, more=True)
        pg.fill("#endReadout", "4.25"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t1 = pg.evaluate(TRIM)
        pg.fill("#endReadout", "soon"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t2, v2 = pg.evaluate(TRIM), pg.evaluate("() => document.getElementById('endReadout').value")
        pg.fill("#startReadout", "1,5"); pg.press("#startReadout", "Enter"); pg.wait_for_timeout(150)
        t3, v3 = pg.evaluate(TRIM), pg.evaluate("() => document.getElementById('startReadout').value")
        check(f"{_n}: a typed time moves its end, and a time that is not one puts it back",
              abs(t1["e"] - 4.25) < 1e-9 and t2 == t1 and v2 == "4.250" and abs(t3["s"] - 1.5) < 1e-9 and v3 == "1.500",
              f"4.25 -> {t1['e']}; 'soon' -> {t2['e']} shown {v2!r}; '1,5' -> {t3['s']} shown {v3!r}")
        # - and +: 0.1s a press, or a bar once there is a tempo; their names and the line say which.
        NAMES = "() => [...document.querySelectorAll('.nudge-btn[data-which]')].map(b => b.getAttribute('aria-label'))"
        e0, n0, l0 = pg.evaluate("() => trimEnd"), pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.click('.nudge-btn[data-which="end"][data-amount="1"]'); pg.wait_for_timeout(150)
        e1 = pg.evaluate("() => trimEnd")
        pg.evaluate("() => { musicTempo = { bpm: 120, phase: 0 }; updateTrimUI(); }"); pg.wait_for_timeout(150)
        n1, l1 = pg.evaluate(NAMES), pg.evaluate(SAID)["step"]
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(150)
        e2 = pg.evaluate("() => trimEnd")
        check(f"{_n}: - and + move 0.1s, or a bar once there is a tempo, and say which",
              abs((e1 - e0) - 0.1) < 1e-9 and abs((e1 - e2) - 2.0) < 1e-9 and l0 == "\u2212 and + move 0.1s." and l1 == "\u2212 and + move a bar, 2.00s."
              and n0 == ["Start of loop, 0.1s earlier", "Start of loop, 0.1s later", "End of loop, 0.1s earlier", "End of loop, 0.1s later"]
              and n1 == ["Start of loop, a bar earlier", "Start of loop, a bar later", "End of loop, a bar earlier", "End of loop, a bar later"],
              f"+ moved the end {e1 - e0:.4f}s, then - at 120 a minute {e1 - e2:.4f}s; {l0!r} then {l1!r}; {n0} then {n1}")
        pg.evaluate("() => { musicTempo = null; updateTrimUI(); }"); pg.wait_for_timeout(100)
        pg.click("#musicLock"); pg.wait_for_timeout(100)
        l0 = pg.evaluate(TRIM)
        pg.click('.nudge-btn[data-which="start"][data-amount="1"]'); pg.wait_for_timeout(150)
        l1 = pg.evaluate(TRIM)
        pg.click("#musicLock"); pg.wait_for_timeout(100)
        pg.click('.nudge-btn[data-which="start"][data-amount="1"]'); pg.wait_for_timeout(150)
        l2 = pg.evaluate(TRIM)
        check(f"{_n}: Lock the length moves both ends together",
              abs((l1["s"] - l0["s"]) - 0.1) < 1e-9 and abs((l1["e"] - l0["e"]) - 0.1) < 1e-9
              and abs((l2["s"] - l1["s"]) - 0.1) < 1e-9 and abs(l2["e"] - l1["e"]) < 1e-9,
              f"locked: start {l0['s']:.3f}->{l1['s']:.3f}, end {l0['e']:.3f}->{l1['e']:.3f}; unlocked: start ->{l2['s']:.3f}, end ->{l2['e']:.3f}")
        sizes = pg.evaluate("() => [...document.querySelectorAll('#musicDetail input:not([type=range])')].map(i => [i.id, parseFloat(getComputedStyle(i).fontSize)])")
        check(f"{_n}: every field that takes text is 16px (iOS magnifies the page under that)",
              len(sizes) == 2 and all(px >= 16 for _, px in sizes), str(sizes))
        c.close()

    print("\nMUSIC MORE — Play with my drawing")
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

    print("\nMUSIC MORE — kind, not jumpy")
    # More opened as a song lands (as soon as its tile is on the screen, a
    # quick person): the app's own scrolls are still settling then -- the
    # drawer's open and the card's growth each re-assert at 300, 700 and
    # 1200ms -- and More makes the drawer taller under them. The tap is at the
    # tile's place on the screen: Playwright's own click scrolls a control
    # into view at once first, and on a phone held sideways, where the tile is
    # still below the screen 400ms on, that was a 207px frame of the test's
    # own making. On Flip held sideways the growth's reveal stops short of the
    # tile for the dock (lib/drawerdetent.js: "a short phone may still leave
    # the last row to scroll to"), so there a person scrolls to it first, and
    # so does this. Read the tile on every frame: no frame may
    # carry it more than 160px (a glide's frames measured 44-57px when this
    # was the level switch; a re-assert chasing the new end, 236-684px), and
    # it ends in sight, on a desk and on a phone held sideways, where More is
    # taller than the screen. Each frame's time is kept and said. Beside other
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
            ON = "() => { const r = document.getElementById('fineTuneToggle').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }"
            for _ in range(30):
                if pg.evaluate(ON):
                    break
                pg.wait_for_timeout(50)
            wheel = 0
            while not pg.evaluate(ON) and wheel < 12:
                pg.mouse.wheel(0, 100); pg.wait_for_timeout(150); wheel += 1
            at = pg.evaluate("() => { const r = document.getElementById('fineTuneToggle').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
            pg.evaluate("""() => { window.__tops = []; const s = document.getElementById('fineTuneToggle'), t0 = performance.now();
                (function f() { window.__tops.push([performance.now(), s.getBoundingClientRect().top]);
                  if (performance.now() - t0 < 1900) requestAnimationFrame(f); })(); }""")
            pg.mouse.click(*at)
            pg.wait_for_timeout(2100)
            tops = pg.evaluate("() => window.__tops")
            r = pg.evaluate(SIGHT)
            big = max((abs(b[1] - a[1]), b[0] - a[0]) for a, b in zip(tops, tops[1:])) if len(tops) > 1 else None
            check(f"{_n}: More opened as a song lands glides, and keeps its tile in sight ({dev})",
                  big is not None and big[0] <= 160 and r["header"] <= r["seg"] < r["vh"] - 40,
                  f"the biggest frame {round(big[0]) if big else None}px, in a {round(big[1]) if big else None}ms frame,"
                  f" over {len(tops)} frames; ends at {r}" + (f"; scrolled to it first ({wheel} turns of the wheel)" if wheel else ""))
            c.close()
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, drawn=False, opts=PHONE, more=True)
        pg.wait_for_timeout(1300)   # past every re-assert there is
        # Closed with its tile just under the header and More's end below the
        # screen: the drawer loses most of its height, which near the page's
        # end is a clamp. Read the tile on every frame.
        pg.evaluate("() => { const s = document.getElementById('fineTuneToggle'), h = document.querySelector('.header');"
                    " const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;"
                    " window.scrollBy(0, s.getBoundingClientRect().top - top - 10); }")
        browsing.wait_scroll_still(pg)
        pg.evaluate("""() => { window.__tops = []; const s = document.getElementById('fineTuneToggle'), t0 = performance.now();
            (function f() { window.__tops.push(s.getBoundingClientRect().top); if (performance.now() - t0 < 1400) requestAnimationFrame(f); })(); }""")
        pg.click("#fineTuneToggle")
        pg.wait_for_timeout(1500)
        tops = pg.evaluate("() => window.__tops")
        steps = [abs(tops[i] - tops[i - 1]) for i in range(1, len(tops))]
        moved = abs(tops[-1] - tops[0]) if tops else 0
        check(f"{_n}: closing More from the drawer's end glides: its tile never leaps",
              len(tops) > 20 and moved > 40 and max(steps) < 0.45 * moved,
              f"moved {moved:.0f}px over {len(tops)} frames, the biggest frame {max(steps) if steps else 0:.0f}px")
        c.close()
    # OPENED WITH MORE OPEN, THE DRAWER STARTS AT ITS TOP (the owner's iPhone:
    # "When you click the media button and click music it open all the way to
    # the bottom?"). More open is remembered, and with it the drawer is taller
    # than a phone; the open scrolled its end to the screen's foot, which took
    # the tabs, the song and the strip up under the header. Now the bar above
    # the drawer stays under the header, as a song landing already left it
    # (lib/drawerdetent.js), on the owner's phone and a short one; a drawer
    # that fits still opens with its end on screen; and a person who scrolls
    # on as it opens is left where they scrolled to. Media and Music tapped as
    # a person taps them, the page at rest at its top first.
    TOP = """() => { const h = document.querySelector('.header'), q = (s) => document.querySelector(s).getBoundingClientRect();
      const head = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
      const dock = document.querySelector('#toolBar, .flip-tools');
      return { head: Math.round(head), dock: Math.round(dock.getBoundingClientRect().top), tabs: Math.round(q('#mediaTabs').top),
               end: Math.round(q('#mediaCard').bottom), vh: Math.round(visualViewport ? visualViewport.height : innerHeight), y: Math.round(scrollY) }; }"""
    for _n, _p in eds("kind"):
        for dev, o in (("phone", PHONE), ("short phone", dict(PHONE, viewport={"width": 390, "height": 640}))):
            c, pg, _ = editor(b, _n, _p, opts=o, more=True)
            browsing.pad_drawer_close(pg)
            pg.wait_for_function("() => window.scrollY === 0", timeout=5000); pg.wait_for_timeout(300)
            pg.click("#mediaOpenBtn"); pg.wait_for_timeout(150)
            if pg.get_attribute("#mediaTabMusic", "aria-selected") != "true":
                pg.click("#mediaTabMusic")
            pg.wait_for_timeout(1500)                  # past every re-assert there is
            tall = pg.evaluate(TOP)
            pg.click("#mediaTabPhoto"); pg.wait_for_timeout(1500)
            fits = pg.evaluate(TOP)
            check(f"{_n}: opened with More open, the drawer starts at its top: the bar under the header, the tabs on screen ({dev})",
                  tall["end"] > tall["vh"] and tall["head"] - 1 <= tall["dock"] <= tall["head"] + 12 and tall["head"] <= tall["tabs"] < tall["vh"]
                  and fits["end"] <= fits["vh"] + 1 and fits["dock"] >= fits["head"] - 1,
                  f"Music with More open (its end at {tall['end']} on a {tall['vh']}px screen): {tall}; Photo, which fits: {fits}")
            c.close()
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, opts=PHONE, more=True)
        browsing.pad_drawer_close(pg)
        pg.wait_for_function("() => window.scrollY === 0", timeout=5000); pg.wait_for_timeout(300)
        pg.click("#mediaOpenBtn"); pg.wait_for_timeout(150)
        if pg.get_attribute("#mediaTabMusic", "aria-selected") != "true":
            pg.click("#mediaTabMusic")
        pg.wait_for_timeout(250)
        at = pg.evaluate(TOP)
        pg.mouse.move(200, 600); pg.mouse.wheel(0, 300); pg.wait_for_timeout(150)
        put = pg.evaluate(TOP)
        pg.wait_for_timeout(1500)
        left = pg.evaluate(TOP)
        check(f"{_n}: a person who scrolls on as the drawer opens is left where they scrolled to",
              put["y"] > at["y"] + 100 and abs(left["y"] - put["y"]) <= 2,
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
    # A DRAFT OPENED SAYS ITS OWN SMOOTH RESTART (the owner's Flip: "19.75s"
    # over a switch that said Off). A draft with a 0.25s smooth restart, saved,
    # then opened over a song whose smooth restart was switched off: the line,
    # the switch, its words and its length agree. Flip's draft and file opens
    # set the loop and repainted all but the switch's row.
    SAVE = {"Pad": "() => JSON.stringify(serializeSkribl())", "Flip": "() => JSON.stringify(serializeFlip())"}
    OPEN = {"Pad": "(s) => loadSkribl(JSON.parse(s))", "Flip": "(s) => applyFlipDraftObject(JSON.parse(s))"}
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, opts=PHONE, song=LONG, more=True)
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
