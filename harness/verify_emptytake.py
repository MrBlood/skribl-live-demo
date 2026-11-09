#!/usr/bin/env python3
"""A take with nothing in it ends, and a blank base is not ink: the Pad comes back fresh.

THE OWNER, Nov 6, testing the Pad on a desk: "i can undo all the way (even
words), but it doesn't get to the home screen", and, of a new Skribl's words,
"it does not register the amount of time it took ... it acts like nothing has
been recorded. so I make a few strokes but the record doesn't start. I have to
manually click record". Undo all the way through a take left it running over
the empty canvas (the clock counting, Done showing), and its saves kept the
blank canvas the take began on as a base. A reload read that base as ink left
out of any take: an empty canvas the Pad thought was drawn on, so neither the
words nor the first stroke started a take, and a Record button stood over
nothing. (lib/recolor.js works on the lines of a take, so Recolor found
nothing there either.)

WHAT IS ASKED, AND HOW IT IS READ (the Pad, real presses and keys)
  * A TAKE UNDONE TO NOTHING ENDS, a stroke's or words': no take, the clock
    hidden, no Done and no Record, the empty canvas's hint; the next stroke
    starts a fresh take (its first point near the clock's start, not where
    the old take's clock had got to); Redo brings the words back as a take
    to watch.
  * A RELOAD AFTER IT is a fresh Pad, where words written are recorded, a
    take of their own that ends when they are written (as Done ends one,
    verify_text 19), and after Keep drawing a stroke joins their take.
  * A SAVE OF AN EMPTY CANVAS KEEPS NO BASE, even with a take's base held.
  * SAVES WRITTEN BEFORE THIS: an autosave holding a blank base (and the words
    to Redo), and a file holding one, come back as a fresh Pad; a base with ink
    in it comes back as ink (Record offered).
  * A SECOND FINGER on a blank canvas still leaves no take running.
"""
import base64
import io
import json
import os
import struct
import sys
import time
import zlib

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
    print("No assertions were executed. This is NOT evidence a take undone to nothing ends.")
    raise SystemExit(77)
import browsing  # noqa: E402

DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
STATE = """() => ({ rec: recording, fin: finishedRecording, has: hasContent, n: strokes.length,
  first: strokes.length ? strokes[0].t : null, maxT: strokes.reduce((m, p) => Math.max(m, p.t || 0), 0),
  clock: !recIndicator.hidden, rec_btn: recordBtn.hidden ? null : recordBtn.textContent.trim(),
  hint: !!canvasEmptyHint && !canvasEmptyHint.classList.contains('hidden'),
  play: !document.getElementById('playWrap').hidden, redo: !redoBtn.disabled })"""


def png(w, h, dot=False):
    """A PNG of w x h, see-through, with one opaque 3x3 dot in the middle if asked."""
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            ink = dot and abs(x - w // 2) <= 1 and abs(y - h // 2) <= 1
            row += bytes([30, 30, 30, 255]) if ink else bytes([0, 0, 0, 0])
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(data).decode()


def page(b, opts=DESK):
    c = b.new_context(**opts)
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)[:200]))
    browsing.goto(q, BASE, "/")
    q.wait_for_timeout(500)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    return c, q, errs


def at(q, fx, fy):
    r = q.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
    return r[0] + fx * r[2], r[1] + fy * r[3]


def line(q, fy=0.7):
    q.evaluate("() => { if (tool !== 'pen') document.getElementById('penToolBtn').click(); }")
    q.wait_for_timeout(150)
    q.keyboard.press("Escape")
    q.wait_for_timeout(100)
    x0, y0 = at(q, 0.2, fy)
    x1, y1 = at(q, 0.7, fy + 0.05)
    q.mouse.move(x0, y0)
    q.mouse.down()
    for i in range(1, 21):
        q.mouse.move(x0 + (x1 - x0) * i / 20, y0 + (y1 - y0) * i / 20)
        q.wait_for_timeout(16)
    q.mouse.up()
    q.wait_for_timeout(250)


def words(q, w="hi there"):
    q.evaluate("() => document.querySelector('#shapeSeg [data-shape=\"text\"]').click()")
    q.wait_for_timeout(200)
    x, y = at(q, 0.3, 0.35)
    q.mouse.click(x, y)
    q.wait_for_timeout(600)
    q.evaluate("(w) => { const f = document.getElementById('txField'); f.value = w; f.dispatchEvent(new Event('input', { bubbles: true })); }", w)
    q.wait_for_function("() => { const p = SkriblText.plan(); return !!p && p.strokes.length > 0; }", timeout=15000)
    q.click("#txGo")
    q.wait_for_function("() => !SkriblText.isWriting()", timeout=60000)
    q.wait_for_timeout(300)


def undo_all(q):
    for _ in range(40):
        if not q.evaluate("() => !undoBtn.disabled"):
            break
        q.keyboard.press("Control+z")
        q.wait_for_timeout(150)
    q.wait_for_timeout(200)


def reload(q):
    q.wait_for_function("() => typeof draftIsDurable === 'function' && draftIsDurable()", timeout=15000)
    q.reload(wait_until="load")
    q.wait_for_function("() => !!window.__skriblBoot && !!window.__skriblBoot.pad", timeout=15000)
    q.wait_for_timeout(900)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide()")


def fresh(s):
    return (not s["rec"] and not s["fin"] and not s["has"] and s["n"] == 0 and not s["clock"]
            and s["rec_btn"] is None and s["hint"])


def says(s):
    return (f"take {'on' if s['rec'] else 'off'}{', finished' if s['fin'] else ''}, content {s['has']}, {s['n']} points, "
            f"clock {'shown' if s['clock'] else 'hidden'}, button {s['rec_btn']!r}, hint {s['hint']}, play {s['play']}")


# A record as an old build saved it: the autosave of a take undone to nothing,
# the blank canvas the take began on as its base (or, the control, a base with
# ink in it), the words left to Redo. Put in place before the page's own
# scripts run, as a save from yesterday is; a page being left writes its own
# autosave on the way out, so it cannot be put there from the page before.
KEY = "skribl_autosave_v1"


def old_save(b, base_png):
    c, q, errs = page(b)
    words(q)
    undo_all(q)
    q.wait_for_timeout(1500)
    q.wait_for_function("() => typeof draftIsDurable === 'function' && draftIsDurable()", timeout=15000)
    rec = json.loads(q.evaluate("(k) => localStorage.getItem(k)", KEY))
    dims = q.evaluate("() => { const p = drawingPixels(); return [p.width, p.height]; }")
    c.close()
    rec["baseSnapshot"] = base_png(dims[0], dims[1])
    c = b.new_context(**DESK)
    c.add_init_script("if (!sessionStorage.getItem('old-save')) { sessionStorage.setItem('old-save', '1');"
                      " localStorage.setItem(%s, %s); }" % (json.dumps(KEY), json.dumps(json.dumps(rec))))
    q = c.new_page()
    browsing.goto(q, BASE, "/")
    q.wait_for_timeout(1500)
    q.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    return c, q, bool(rec.get("redoStrokes"))

with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("\nA TAKE UNDONE TO NOTHING ENDS")
    c, q, errs = page(b)
    line(q)
    armed = q.evaluate(STATE)
    undo_all(q)
    s = q.evaluate(STATE)
    check("a stroke's take undone to nothing ends: no clock, no Done or Record, the empty canvas's hint",
          armed["rec"] and fresh(s), f"after the stroke: {says(armed)}; after Undo: {says(s)}")
    q.wait_for_timeout(1500)
    line(q, 0.5)
    s2 = q.evaluate(STATE)
    check("...and the next stroke starts a fresh take, its first point at the clock's start",
          s2["rec"] and s2["first"] is not None and s2["first"] < 300,
          f"first point at {s2['first']} ms after the take began (an old take's clock would be past 1500); {says(s2)}")
    c.close()

    c, q, errs = page(b)
    words(q)
    armed = q.evaluate(STATE)
    undo_all(q)
    s = q.evaluate(STATE)
    # The words' take ends when they are written (verify_text 19), so it is
    # a finished take that is undone here, to the same fresh Pad.
    check("words' take undone to nothing ends the same way",
          armed["fin"] and not armed["rec"] and armed["n"] > 0 and fresh(s), f"after the words: {says(armed)}; after Undo: {says(s)}")
    q.keyboard.press("Control+y")
    q.wait_for_timeout(600)
    s3 = q.evaluate(STATE)
    check("...and Redo brings the words back, a take to watch",
          s3["n"] == armed["n"] and s3["fin"] and s3["play"] and not s3["rec"], says(s3))
    c.close()

    print("\nA RELOAD AFTER IT")
    c, q, errs = page(b)
    words(q)
    undo_all(q)
    q.wait_for_timeout(1500)
    reload(q)
    s = q.evaluate(STATE)
    check("after a take undone to nothing, a reload brings back a fresh Pad (no Record button, the hint)",
          fresh(s), says(s))
    words(q)
    w = q.evaluate(STATE)
    d0 = q.evaluate("() => getPlaybackDuration()")
    # Their take ends when they are written, as Done ends one; Keep drawing
    # carries the drawing on, and the stroke after is recorded into it, its
    # clock starting again as every Keep drawing's does (so the replay grows).
    if q.evaluate("() => !document.getElementById('addTakePill').hidden"):   # with no pill, the row says why
        q.click("#addTakePill")
        q.wait_for_timeout(200)
    line(q)
    s2 = q.evaluate(STATE)
    t_new = q.evaluate("(n0) => strokes.slice(n0).reduce((m, p) => Math.max(m, p.t || 0), 0)", w["n"])
    d1 = q.evaluate("() => getPlaybackDuration()")
    check("...where words written are recorded, and after Keep drawing a stroke joins their take",
          w["fin"] and not w["rec"] and w["n"] > 0 and w["maxT"] > 500 and s2["rec"] and s2["n"] > w["n"] and t_new > 0 and d1 > d0,
          f"after the words: {says(w)}, last point at {w['maxT']} ms, the replay {d0} ms; after Keep drawing and a stroke: {says(s2)}, "
          f"the stroke recorded to {t_new} ms, the replay {d1} ms")
    # The owner: "it doesn't recolor after text and undo". lib/recolor.js works
    # on the lines of a take, and a stroke left out of every take was not one.
    q.evaluate("() => { if (recording) recordBtn.click(); }")
    q.wait_for_timeout(400)
    before = q.evaluate("() => strokes.length ? strokes[strokes.length - 1].color : null")
    q.evaluate("() => { setPenColor('#00a95c'); SkriblPadRecolor.arm(); }")
    q.wait_for_timeout(300)
    q.mouse.click(*at(q, 0.45, 0.725))   # the middle of the stroke above
    q.wait_for_timeout(600)
    after = q.evaluate("() => strokes.length ? strokes[strokes.length - 1].color : null")
    check("...and Recolor finds that stroke: a press on it gives it the new colour",
          before is not None and after is not None and after != before, f"the stroke's colour {before} -> {after}")
    c.close()

    print("\nA SAVE OF AN EMPTY CANVAS KEEPS NO BASE")
    c, q, errs = page(b)
    kept = q.evaluate("""() => { const held = preRecordSnapshot, had = hasContent;
      preRecordSnapshot = drawingPixels().toDataURL(); hasContent = false;
      const r = { auto: serializeAutosave().baseSnapshot, frame: captureCurrentFrame().baseSnapshot };
      preRecordSnapshot = held; hasContent = had; return { auto: !!r.auto, frame: !!r.frame }; }""")
    check("a save of an empty canvas keeps no base, even with a take's base still held (the autosave and a file)",
          not kept["auto"] and not kept["frame"], str(kept))
    c.close()

    print("\nSAVES WRITTEN BEFORE THIS")
    for label, dot in (("blank", False), ("ink", True)):
        c, q, redo = old_save(b, lambda w, h: png(w, h, dot))
        s = q.evaluate(STATE)
        if not dot:
            check("an autosave holding a blank base (an old build's, the words to Redo) comes back as a fresh Pad",
                  redo and fresh(s) and s["redo"], f"saved with words to Redo {redo}; {says(s)}, Redo {'offered' if s['redo'] else 'not offered'}")
        else:
            check("...and one whose base has ink in it comes back as ink: Record offered, no hint",
                  s["has"] and s["rec_btn"] is not None and not s["hint"], says(s))
        c.close()

    c, q, errs = page(b)
    dims = q.evaluate("() => { const p = drawingPixels(); return [p.width, p.height]; }")
    q.evaluate("""(base) => loadSkribl({ version: 1, strokes: [], strokeGroups: [], baseSnapshot: base,
                                         background: { color: bgColor } })""", png(dims[0], dims[1]))
    q.wait_for_timeout(1200)
    s = q.evaluate(STATE)
    check("a file or saved draft holding a blank base opens as a fresh Pad", fresh(s), says(s))
    c.close()

    print("\nA SECOND FINGER ON A BLANK CANVAS")
    c, q, errs = page(b, PHONE)
    r = q.evaluate("""() => { const el = document.getElementById('canvas'), b = el.getBoundingClientRect();
      const at = (x, y) => ({ clientX: b.left + x, clientY: b.top + y });
      const ev = (t, id, x, y) => el.dispatchEvent(new PointerEvent(t, { pointerId: id, isPrimary: id === 1,
        bubbles: true, cancelable: true, pointerType: 'touch', ...at(x, y) }));
      const touch = (x, y, id) => new Touch({ identifier: id, target: el, ...at(x, y) });
      ev('pointerdown', 1, 60, 60);
      for (let i = 1; i <= 6; i++) ev('pointermove', 1, 60 + i * 4, 60 + i * 3);
      const armed = recording;
      ev('pointerdown', 2, 160, 160);
      el.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, cancelable: true,
        touches: [touch(84, 78, 1), touch(160, 160, 2)], targetTouches: [touch(84, 78, 1), touch(160, 160, 2)],
        changedTouches: [touch(160, 160, 2)] }));
      return armed; }""")
    q.wait_for_timeout(300)
    s = q.evaluate(STATE)
    check("a second finger on a blank canvas leaves no take running, and no Record button",
          r and not s["rec"] and s["n"] == 0 and s["rec_btn"] is None and not s["clock"],
          f"the first finger armed a take: {r}; after the pinch: {says(s)}")
    c.close()
    b.close()

summarise_and_exit()
