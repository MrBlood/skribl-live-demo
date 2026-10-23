#!/usr/bin/env python3
"""The music drawer's three levels (lib/musicdrawer.js), on the Pad and on Flip.

The owner: "like 3 levels of controls. The more control you want, the deeper
into the controls you go. I want it all, but from super simple to super
powerful... no getting rid of anything either... Keep it kind too." Step 1 of
the build plan: Simple, Adjust and Fine-tune, with today's controls in their
new homes and names. verify_music.py keeps how each control works (the
previews, the switch, Fit's sum on Flip); this keeps where each one lives,
what the drawer says, and the new pieces.

The rows:

  THE LEVELS. Three, Simple first, each its name over what it is for. Each
  shows what it adds and hides the rest with `hidden` (so out of the Tab order
  too): Simple is the strip, the pick line, the two picks and Play; Adjust
  adds the typed times, Smooth restart and Hear the restart; Fine-tune the
  loop detail, Each tap, the steppers, the sync line, Lock the length and
  Smooth restart's length. Switching keeps the loop, and says so over the
  strip without taking a tap. The level is remembered, by the other editor
  too.

  SKRIBL'S PICK. A new song starts on the first 20 seconds (the whole song
  when it is shorter), with a smooth restart; on the Pad a drawing already
  there sets the length instead, what is heard as long as the drawing. The
  pick line says which. A change says "your own loop" with the way back;
  the way back has an Undo, which goes after eight seconds. A song a draft
  brings back keeps the draft's loop.

  THE PICKS. Fit counts the smooth restart (what is heard is as long as the
  drawing; Match Drawing Time fell short by the crossfade). Whole song loops
  all of a short song and a long one's first 20 seconds, and says which. The
  one that describes the loop wears the one tint. With nothing drawn Fit is
  off and says why, and wakes when a drawing is made with the drawer open.

  SMOOTH RESTART. One switch, on at its last length and off to a clean cut;
  the lines count what is heard.

  FINE-TUNE. A typed time moves its end (a comma is a point); a time that is
  not one puts the loop's own back. Each tap's frame is the editor's own --
  the Pad's video, 30 a second; Flip's pages a second -- and keeps its place
  in size order. Lock the length moves both ends together. The sync line
  says the loop in seconds and frames against the drawing. Every field that
  takes text is 16px (A11Y 11b; these are built hidden).

  PLAY. Play with my drawing is the editor's own Play and follows it however
  it is pressed; with nothing drawn it waits, and Hear the loop, beside it on
  every level, plays the music on its own (verify_musicbeat has the rest).

  KIND, NOT JUMPY. Picking Fine-tune never takes the switch just tapped out of
  sight, and going back to Simple from the drawer's end glides: the switch is
  read on every frame and never leaps.

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
    print("No assertions were executed. This is NOT evidence the music drawer has its levels.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICLEVELS_ONLY=Pad (or Flip) runs one editor, and
# MUSICLEVELS_PART=levels (pick, picks, smooth, fine, play, kind) one part, so
# a row can be shown red in seconds. A real run sets neither.
ONLY = os.environ.get("MUSICLEVELS_ONLY", "")
PART = os.environ.get("MUSICLEVELS_PART", "")
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
  return { pick: q('musicPickText').textContent, back: !q('musicBackPick').hidden, undo: !q('musicPickUndo').hidden,
           fit: q('matchDrawingBtn').getAttribute('aria-pressed'), fitOff: q('matchDrawingBtn').disabled, fitSub: q('musicFitSub').textContent,
           whole: q('musicWholeBtn').getAttribute('aria-pressed'), wholeName: q('musicWholeName').textContent, wholeSub: q('musicWholeSub').textContent,
           len: q('musicLenLine').textContent, sync: q('musicSyncLine').textContent, play: q('musicPlayLabel').textContent,
           smooth: q('musicSmooth').getAttribute('aria-checked'), smoothSub: q('musicSmoothSub').textContent }; }"""
# Shown: no [hidden] on the way up, and a box. Hidden: a [hidden] on the way up.
SHOWN = """(ids) => ids.filter((id) => { const el = document.getElementById(id);
  return !!el && !el.closest('[hidden]') && el.getClientRects().length > 0; })"""
LEVEL_BTN = {"simple": "#musicLevelSimple", "adjust": "#fineTuneTrim", "fine": "#fineTuneToggle"}
# Where the level switch is, against the pinned header (0 where the header scrolls away) and the screen.
SIGHT = """() => { const s = document.getElementById('fineTuneSeg').getBoundingClientRect(), h = document.querySelector('.header');
  const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;
  return { seg: Math.round(s.top), header: Math.round(top), vh: innerHeight }; }"""
EVERY = ["musicTrack", "musicPickLine", "matchDrawingBtn", "musicWholeBtn", "musicPlayBtn", "previewLoopBtn"]
ADJUST = ["musicLenLine", "musicFrom", "musicTo", "musicTapBtn", "musicSmooth", "testSeamBtn"]
FINE = ["fineTuneBody", "zoomTrackWrap", "zoomPanSlider", "musicTapBtn", "musicStepSeg", "startReadout", "endReadout",
        "musicSyncLine", "musicLock", "musicSmooth", "crossfadeSlider", "testSeamBtn"]
ALL = sorted(set(EVERY + ADJUST + FINE))
WANT = {"simple": set(EVERY), "adjust": set(EVERY + ADJUST), "fine": set(EVERY + FINE)}


def heard(t):
    """What is heard each time round: the selection less the smooth restart's fold."""
    n = t["e"] - t["s"]
    return n - min(t["xf"] / 1000, n / 2)


def editor(b, name, path, *, drawn=True, song=SHORT, ctx=None, opts=DESK, level=None):
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
    if level:
        pick_level(pg, level)
    return c, pg, errs


def add(pg, song):
    browsing.pad_drawer(pg, "music")
    secs = len(song["buffer"]) / 16000
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
    waits.settle(pg, 500)


def pick_level(pg, level):
    pg.click(LEVEL_BTN[level])
    pg.wait_for_timeout(350)
    browsing.wait_scroll_still(pg)


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

    print("\nMUSIC LEVELS — three, and what each shows")
    for _n, _p in eds("levels"):
        c, pg, errs = editor(b, _n, _p)
        seg = pg.evaluate("() => [...document.querySelectorAll('#fineTuneSeg button')].map(b => [b.dataset.level, b.querySelector('.lv-k').textContent, b.querySelector('.lv-v').textContent])")
        check(f"{_n}: three levels, Simple first, each its name over what it is for",
              seg == [["simple", "Simple", "Skribl does it"], ["adjust", "Adjust", "shape it yourself"], ["fine", "Fine-tune", "make it perfect"]],
              str(seg))
        shown = {}
        for lv in ("simple", "adjust", "fine"):
            if lv != "simple":
                pick_level(pg, lv)
            shown[lv] = set(pg.evaluate(SHOWN, ALL))
        check(f"{_n}: a new drawer opens on Simple: the strip, the pick line, the pair that plays and the two picks, and nothing deeper",
              shown["simple"] == WANT["simple"], f"extra {sorted(shown['simple'] - WANT['simple'])}, missing {sorted(WANT['simple'] - shown['simple'])}")
        check(f"{_n}: Adjust adds the typed times, Tap the beat, Smooth restart and Hear the restart",
              shown["adjust"] == WANT["adjust"], f"extra {sorted(shown['adjust'] - WANT['adjust'])}, missing {sorted(WANT['adjust'] - shown['adjust'])}")
        check(f"{_n}: Fine-tune adds the loop detail, Each tap, the steppers, the sync line, Lock the length and Smooth restart's length",
              shown["fine"] == WANT["fine"], f"extra {sorted(shown['fine'] - WANT['fine'])}, missing {sorted(WANT['fine'] - shown['fine'])}")
        pick_level(pg, "simple")
        tab = pg.evaluate("""(ids) => ids.filter((id) => { const el = document.getElementById(id); return !el.closest('[hidden]'); })""",
                          sorted(set(ADJUST + FINE) - set(EVERY)))
        check(f"{_n}: what a level hides is hidden, so out of the Tab order too", not tab, f"not [hidden] on Simple: {tab}")

        # Switching keeps the loop: an own loop and smooth restart, through every level and back.
        pick_level(pg, "fine")
        pg.evaluate("() => { trimStart = 0.7; trimEnd = 3.9; updateTrimUI(); }")
        pg.evaluate("() => { const s = document.getElementById('crossfadeSlider'); s.value = '120'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        before = pg.evaluate(TRIM)
        seen = []
        for lv in ("simple", "adjust", "fine", "simple"):
            pick_level(pg, lv)
            seen.append(pg.evaluate(TRIM))
        check(f"{_n}: switching the level keeps the loop",
              all(t == before for t in seen) and before["xf"] == 120, f"{before} then {seen}")
        pick_level(pg, "adjust")
        k = pg.evaluate("() => { const k = document.getElementById('musicKept'), r = k.getBoundingClientRect(), s = getComputedStyle(k);"
                        " return { shown: k.classList.contains('show'), taps: s.pointerEvents, pos: s.position, in: k.closest('#musicTrack') !== null }; }")
        pg.wait_for_timeout(2900)
        gone = pg.evaluate("() => !document.getElementById('musicKept').classList.contains('show')")
        check(f"{_n}: switching the level says so, over the strip, and takes no taps or room",
              k["shown"] and k["taps"] == "none" and k["pos"] == "absolute" and k["in"] and gone, f"{k}; gone after 2.9s: {gone}")
        check(f"{_n}: no page errors through the levels", not errs, "; ".join(errs[:2]))
        c.close()

    # The level is one choice, kept for both editors (one origin, one key).
    if part("levels") and not ONLY:
        c = waits.instrument(b.new_context(**DESK))
        _, pad, _ = editor(b, "Pad", "/", ctx=c, drawn=False)
        pick_level(pad, "adjust")
        pad.reload(); browsing.goto(pad, BASE, "/"); add(pad, SHORT)
        again = pad.evaluate("() => document.getElementById('musicDetail').dataset.level")
        _, flip, _ = editor(b, "Flip", "/flip", ctx=c, drawn=False)
        there = flip.evaluate("() => [document.getElementById('musicDetail').dataset.level, [...document.querySelectorAll('#fineTuneSeg button.on')].map(b => b.dataset.level)]")
        check("the level is remembered, on the other editor too",
              again == "adjust" and there == ["adjust", ["adjust"]], f"Pad after a reload {again!r}; Flip {there}")
        c.close()

    print("\nMUSIC LEVELS — Skribl's pick")
    for _n, _p in eds("pick"):
        got = {}
        for drawn, song in ((True, SHORT), (False, LONG), (True, LONG)):
            c, pg, _ = editor(b, _n, _p, drawn=drawn, song=song)
            got[(drawn, song["name"])] = (pg.evaluate(TRIM), pg.evaluate(DRAWING[_n]), pg.evaluate(SAID)["pick"])
            c.close()
        ok, why = True, []
        for (drawn, nm), (t, secs, words) in got.items():
            if _n == "Pad" and drawn:
                good = t["s"] == 0 and t["xf"] == 250 and abs(heard(t) - secs) < 0.002 and "as long as your drawing, with a smooth restart." in words
            elif nm == "long.wav":
                good = t["s"] == 0 and abs(t["e"] - 20) < 0.001 and t["xf"] == 250 and words == "Skribl picked the first 20 seconds, with a smooth restart."
            else:
                good = t["s"] == 0 and abs(t["e"] - t["d"]) < 0.001 and t["xf"] == 250 and words == "Skribl picked the whole song, with a smooth restart."
            ok = ok and good
            why.append(f"{'drawn' if drawn else 'blank'} {nm}: {t['s']:.2f}-{t['e']:.3f} xf {t['xf']} heard {heard(t):.3f} (drawing {secs:.3f}) {words!r}")
        check(f"{_n}: a new song starts on Skribl's pick", ok, "; ".join(why))

    for _n, _p in eds("pick"):
        c, pg, errs = editor(b, _n, _p, level="fine")
        pick = pg.evaluate(TRIM)
        pg.click('.nudge-btn[data-which="end"][data-amount="-1"]'); pg.wait_for_timeout(200)
        own, said = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: a change says so, with the way back",
              said["pick"] == "You've made your own loop." and said["back"] and not said["undo"], f"{said['pick']!r}, back {said['back']}, undo {said['undo']}")
        went = press(pg, "#musicBackPick")
        back, said2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        focus = pg.evaluate("() => document.activeElement && document.activeElement.id")
        undid = press(pg, "#musicPickUndo")
        undone, said3 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: Back to Skribl's pick puts it back, and its Undo undoes that",
              went and undid and back == pick and said2["pick"] == "Back to Skribl's pick." and said2["undo"] and not said2["back"]
              and focus == "musicPickUndo" and undone == own and said3["pick"] == "You've made your own loop.",
              f"pick {pick}, own {own}, back {back} ({said2['pick']!r}, focus {focus}), undone {undone} ({said3['pick']!r}); pressed back {went}, undo {undid}")
        if _n == EDITORS[0][0]:
            # One shared timer (lib/musicdrawer.js), so one editor is asked.
            went = press(pg, "#musicBackPick", 8400)
            late = pg.evaluate(SAID)
            check("the Undo goes after eight seconds, and the line says Skribl's pick again",
                  went and not late["undo"] and not late["back"] and late["pick"].startswith("Skribl picked"),
                  str({k: late[k] for k in ('pick', 'undo', 'back')}) + f"; pressed back {went}")
        c.close()

    # The Pad's pick follows the drawing. Undo with the drawer open is the
    # drawing changing, not the person: the line says so, and the way back
    # fits the drawing as it is now.
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
        check("Pad: an Undo with the drawer open says the drawing changed, and Back to Skribl's pick fits it again",
              s0["pick"].startswith("Skribl picked") and one < two - 0.5
              and s1["pick"] == "Your drawing has changed since Skribl picked this loop." and s1["back"] and s1["fit"] == "false"
              and abs(heard(t2) - one) < 0.002 and s2["fit"] == "true",
              f"{two:.2f}s then {one:.2f}s: {s1['pick']!r}, back {s1['back']}; after the way back heard {heard(t2):.3f}s, fit {s2['fit']}")
        c.close()

    # The pick's seconds are rounded from the hundredths the lines show, as a
    # person rounds what they read: a drawing 4.448s long was "4.4 seconds"
    # over an Adjust line saying 4.45s. Built point by point, 8ms apart.
    if part("pick") and (not ONLY or ONLY == "Pad"):
        c, pg, _ = editor(b, "Pad", "/", drawn=False, song=None)
        pg.evaluate("""() => { strokes.length = 0;
            for (let k = 0; k <= 556; k++) strokes.push({ x: 0.2 + k * 0.001, y: 0.4, color: '#7c5cff', size: 6, t: k * 8, start: k === 0 });
            strokeGroups.length = 0; strokeGroups.push(strokes.length); updateDrawingTimeLabels(); }""")
        add(pg, SHORT)
        pick_level(pg, "adjust")
        secs, said = pg.evaluate(DRAWING["Pad"]), pg.evaluate(SAID)
        check("Pad: the pick's seconds and the lengths under it agree, as a person rounds them",
              abs(secs - 4.448) < 1e-9 and said["pick"].startswith("Skribl picked the first 4.5 seconds,")
              and said["len"].startswith("4.45s · ") and said["fitSub"] == "4.5s",
              f"a {secs:.3f}s drawing: {said['pick']!r}; {said['len']!r}; Fit says {said['fitSub']!r}")
        c.close()

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

    print("\nMUSIC LEVELS — Fit my drawing and Whole song")
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

    print("\nMUSIC LEVELS — Smooth restart")
    for _n, _p in eds("smooth"):
        c, pg, _ = editor(b, _n, _p, level="adjust")
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        a, sa = pg.evaluate(TRIM), pg.evaluate(SAID)
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        b2 = pg.evaluate(TRIM)
        pick_level(pg, "fine")
        pg.evaluate("() => { const s = document.getElementById('crossfadeSlider'); s.value = '400'; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        pg.click("#musicSmooth"); pg.wait_for_timeout(150)
        c2, sc = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: Smooth restart's switch turns the fold on at its last length, and off",
              a["xf"] == 0 and sa["smooth"] == "false" and sa["smoothSub"] == "A clean cut back to the start."
              and b2["xf"] == 250 and c2["xf"] == 400 and sc["smooth"] == "true"
              and sc["smoothSub"] == "The end fades into the start over 0.40s, which makes the loop 0.40s shorter.",
              f"off {a['xf']} ({sa['smoothSub']!r}), on {b2['xf']}, after the length is set {c2['xf']} ({sc['smoothSub']!r})")
        pick_level(pg, "adjust")
        t, s2 = pg.evaluate(TRIM), pg.evaluate(SAID)
        check(f"{_n}: the lines count what is heard: the length less the smooth restart",
              s2["len"].startswith(f"{heard(t):.2f}s · "), f"{s2['len']!r} for {t}")
        c.close()

    print("\nMUSIC LEVELS — Fine-tune")
    for _n, _p in eds("fine"):
        c, pg, _ = editor(b, _n, _p, level="fine")
        pg.fill("#endReadout", "4.25"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t1 = pg.evaluate(TRIM)
        pg.fill("#endReadout", "soon"); pg.press("#endReadout", "Enter"); pg.wait_for_timeout(150)
        t2, v2 = pg.evaluate(TRIM), pg.evaluate("() => document.getElementById('endReadout').value")
        pick_level(pg, "adjust")
        pg.fill("#musicFrom", "1,5"); pg.press("#musicFrom", "Enter"); pg.wait_for_timeout(150)
        t3 = pg.evaluate(TRIM)
        pick_level(pg, "fine")
        v3 = pg.evaluate("() => document.getElementById('startReadout').value")
        check(f"{_n}: a typed time moves its end, and a time that is not one puts it back",
              abs(t1["e"] - 4.25) < 1e-9 and t2 == t1 and v2 == "4.250" and abs(t3["s"] - 1.5) < 1e-9 and v3 == "1.500",
              f"4.25 -> {t1['e']}; 'soon' -> {t2['e']} shown {v2!r}; Adjust's '1,5' -> {t3['s']}, Fine-tune shows {v3!r}")
        frame = pg.evaluate("() => { const b = document.querySelector('#musicStepSeg [data-step=frame]'); return b.getAttribute('aria-label'); }")
        rate = 30 if _n == "Pad" else 12
        pg.click("#musicStepSeg [data-step=frame]"); pg.wait_for_timeout(100)
        e0 = pg.evaluate("() => trimEnd")
        pg.click('.nudge-btn[data-which="end"][data-amount="1"]'); pg.wait_for_timeout(150)
        e1 = pg.evaluate("() => trimEnd")
        order = None
        if _n == "Flip":
            # At 6 pages a second a frame is 1/6 s, past 0.1s: it moves to keep the four in size order
            # (the four shown: 1 beat waits, hidden, until a tempo is tapped).
            pg.evaluate("() => { fps = 6; updateToolState(); }"); pg.wait_for_timeout(150)
            order = pg.evaluate("() => [...document.querySelectorAll('#musicStepSeg button')].filter(b => !b.hidden).map(b => b.dataset.step)")
            pg.evaluate("() => { fps = 12; updateToolState(); }"); pg.wait_for_timeout(150)
        check(f"{_n}: Each tap's frame is the editor's own, and keeps its place in size order",
              frame == f"1 frame, 1/{rate} of a second" and abs((e1 - e0) - 1 / rate) < 1e-9
              and (order is None or order == ["0.01", "0.1", "frame", "1"]),
              f"{frame!r}; one tap moved the end {e1 - e0:.5f}s (1/{rate} is {1 / rate:.5f}); at 6 a second {order}")
        pg.click("#musicStepSeg [data-step='0.1']")
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
        pg.click("#matchDrawingBtn"); pg.wait_for_timeout(200)
        t, s = pg.evaluate(TRIM), pg.evaluate(SAID)
        # Read as numbers: JavaScript's toFixed and Python's format round a
        # half differently (59.25 frames is "59.3" there, "59.2" here).
        m = re.fullmatch(r"Comes round every (\d+\.\d{3})s · (\d+(?:\.\d)?) frames at (\d+) a second · fits your (\w+)", s["sync"])
        check(f"{_n}: the sync line says the loop in seconds and frames, against the drawing",
              bool(m) and abs(float(m.group(1)) - heard(t)) <= 0.0006 and abs(float(m.group(2)) - heard(t) * rate) <= 0.051
              and int(m.group(3)) == rate and m.group(4) == WORK[_n],
              f"{s['sync']!r} for {heard(t):.4f}s, {heard(t) * rate:.3f} frames at {rate}")
        sizes = pg.evaluate("() => [...document.querySelectorAll('#musicDetail input:not([type=range])')].map(i => [i.id, parseFloat(getComputedStyle(i).fontSize)])")
        check(f"{_n}: every field that takes text is 16px (iOS magnifies the page under that)",
              len(sizes) == 4 and all(px >= 16 for _, px in sizes), str(sizes))
        c.close()

    print("\nMUSIC LEVELS — Play with my drawing")
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

    print("\nMUSIC LEVELS — kind, not jumpy")
    # Fine-tune picked as a song lands (400ms on, a quick person): the app's
    # own scrolls are still settling then -- the drawer's open and the card's
    # growth each re-assert at 300, 700 and 1200ms -- and the level makes the
    # drawer taller under them. Read the switch on every frame: no frame may
    # carry it more than 160px (a glide's frames measured 44-57px here; a
    # re-assert chasing the new end, 236-684px), and it ends in sight, on a
    # desk and on a phone held sideways, where Fine-tune is taller than the screen.
    # Each frame's time is kept and said. Beside other suites a frame of the
    # reveal lasted up to 150ms, and a glide seen through one is one big step
    # (165px once, in a run beside two others): a red in a long frame is told
    # apart by a run alone. Allowing a long frame more would hide a chase: one
    # measured 424px in a 176ms frame, under the 3px a millisecond tried.
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
            pg.evaluate("""() => { window.__tops = []; const s = document.getElementById('fineTuneSeg'), t0 = performance.now();
                (function f() { window.__tops.push([performance.now(), s.getBoundingClientRect().top]);
                  if (performance.now() - t0 < 1900) requestAnimationFrame(f); })(); }""")
            pg.click("#fineTuneToggle")
            pg.wait_for_timeout(2100)
            tops = pg.evaluate("() => window.__tops")
            r = pg.evaluate(SIGHT)
            big = max((abs(b[1] - a[1]), b[0] - a[0]) for a, b in zip(tops, tops[1:])) if len(tops) > 1 else None
            check(f"{_n}: Fine-tune picked as a song lands glides, and keeps the switch in sight ({dev})",
                  big is not None and big[0] <= 160 and r["header"] <= r["seg"] < r["vh"] - 40,
                  f"the biggest frame {round(big[0]) if big else None}px, in a {round(big[1]) if big else None}ms frame,"
                  f" over {len(tops)} frames; ends at {r}")
            c.close()
    for _n, _p in eds("kind"):
        c, pg, _ = editor(b, _n, _p, drawn=False, opts=PHONE, level="fine")
        pg.wait_for_timeout(1300)   # past every re-assert there is
        # Back to Simple with the switch just under the header and Fine-tune's
        # end below the screen: the drawer loses most of its height, which near
        # the page's end is a clamp. Read the switch on every frame.
        pg.evaluate("() => { const s = document.getElementById('fineTuneSeg'), h = document.querySelector('.header');"
                    " const top = h && ['sticky', 'fixed'].includes(getComputedStyle(h).position) ? h.getBoundingClientRect().bottom : 0;"
                    " window.scrollBy(0, s.getBoundingClientRect().top - top - 10); }")
        browsing.wait_scroll_still(pg)
        pg.evaluate("""() => { window.__tops = []; const s = document.getElementById('fineTuneSeg'), t0 = performance.now();
            (function f() { window.__tops.push(s.getBoundingClientRect().top); if (performance.now() - t0 < 1400) requestAnimationFrame(f); })(); }""")
        pg.click("#musicLevelSimple")
        pg.wait_for_timeout(1500)
        tops = pg.evaluate("() => window.__tops")
        steps = [abs(tops[i] - tops[i - 1]) for i in range(1, len(tops))]
        moved = abs(tops[-1] - tops[0]) if tops else 0
        check(f"{_n}: going back to Simple from the drawer's end glides: the switch never leaps",
              len(tops) > 20 and moved > 40 and max(steps) < 0.45 * moved,
              f"moved {moved:.0f}px over {len(tops)} frames, the biggest frame {max(steps) if steps else 0:.0f}px")
        c.close()

    b.close()

summarise_and_exit()
