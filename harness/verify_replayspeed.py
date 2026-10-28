"""Watching a drawing come alive: the replay's speeds, the line that says what
you are watching, the scrubber that shows the drawing's shape, and the speed
the author picks for viewers -- on the Pad's preview, the shared player and
the in-post player.

The owner's spec (WORKING-AGREEMENTS.md, "Skribl Pad first"): real time,
time-lapse and slow motion, about 1/4x to 16x plus "fit"; say what you are
watching ("drawn in 47 min · watching at 8x"); the author picks the default
speed and the viewer can change it; scrubbing feels good at every speed; a tap
pauses and another carries on. The owner's picks from the mocks: B (the speed
in the line), S3 (the drawing's shape in the bar, fine scrub, drag the drawing
itself), D1 (a row on the Post sheet, set to Auto), tap to pause on the shared
player too.

WHAT IS ASKED, AND HOW IT IS READ
  * Rules are read from lib/replayline.js itself, in a page, against a table:
    where a post starts, what Fit chooses, the artist's time and clock.
  * A speed is read by PLAYING: the same wall time at another rate moves the
    progress by that much more, and a change mid-play carries on from the same
    place rather than jumping.
  * The line is read as text a person sees (innerText, so a hidden span is not
    "said"), and the speeds' state from aria-pressed.
  * The scrubber's shape is read off its own pixels: ink where the drawing was
    drawn, nothing where the artist paused.
  * Drags are real mouse drags; how far the replay moved is read from the
    slider's own value. Where the bubble rides is read under REAL touches and
    a real pen (CDP), so the pointer type is the browser's own, and its paint
    from what is on top at its middle.
  * The author's pick is read from the payload serializeSkribl() writes, the
    server's answer to a bad one, and where each player starts with it.
"""
import json
import math
import os
import sys
import urllib.error
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def drawing(pause_ms, pause_mode, strokes=3, n=40, step=25, extra=None):
    """A Pad payload: `strokes` strokes of `n` points `step` ms apart, with a
    `pause_ms` thinking pause before every stroke after the first."""
    pts, t = [], 0
    for k in range(strokes):
        if k:
            t += pause_ms
        for i in range(n):
            pts.append({"x": 100 + i * 14, "y": 120 + k * 150 + math.sin(i / 4) * 30,
                        "color": "#1f1b2e", "size": 6, "t": t, "start": i == 0})
            t += step
    p = {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": pause_mode,
         "fps": None, "canvasSize": {"cssWidth": 816, "cssHeight": 612},
         "frames": [{"strokes": pts, "strokeGroups": [n] * strokes, "background": {"color": "#f6f2ea"}}],
         "title": "speed"}
    p.update(extra or {})
    return p


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


LINE = "() => document.querySelector('#playerLine .rl-text').innerText.replace(/\\s+/g, ' ').trim()"
FRAC = "() => +document.getElementById('playerProgress').getAttribute('aria-valuenow')"
FILL = "() => parseFloat(document.getElementById('playerProgressFill').style.width) || 0"


def pick(pg, scope, r):
    pg.evaluate("""([s, r]) => { document.querySelector(s + ' .rl-speed').click();
        document.querySelector(s + ' .rl-chips [data-r="' + r + '"]').click(); }""", [scope, r])
    pg.wait_for_timeout(60)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- 1. THE RULES, from the lib itself ------------------------------------
    print("\nTHE RULES (lib/replayline.js)")
    pg = b.new_page()
    browsing.goto(pg, BASE, "/")
    rules = pg.evaluate("""() => { const L = window.SkriblReplayLine;
        return {
          start: [[undefined, 30e3], ['auto', 30e3], ['auto', 90e3], ['fit', 5e3], [8, 1e3], ['drawn', 90e3],
                  ['bogus', 90e3], [3, 1e3], [0.25, 1e3]].map(([v, d]) => L.fromPost(v, d)),
          fit: [L.rate('fit', 120e3), L.rate('fit', 10e3), L.rate(4, 120e3)],
          drawn: L.drawnMs([{t: 0}, {t: 100}, {t: 250}, {t: 0}, {t: 40}]),
          words: [L.words(14800), L.words(47 * 60e3), L.words(125 * 60e3)],
          labels: [0.25, 0.5, 1, 16, 94.4, 1.67].map(L.label),
          clock: (() => { const tl = [{playT: 0, i: 0}, {playT: 100, i: 1}, {playT: 150, i: 2}, {playT: 250, i: 3}];
                          const pts = [{t: 0}, {t: 100}, {t: 40100}, {t: 40200}];
                          const m = L.clockMap(tl, pts); return [m(0), m(100), m(125), m(150), m(250), m(999)]; })(),
          rates: L.RATES };
    }""")
    check("where a post starts: none -> as drawn; Auto -> as drawn under a minute of drawing, Fit over it; "
          "Fit and a listed rate as chosen; 'drawn', unknown values and unlisted rates -> as drawn",
          rules["start"] == [1, 1, "fit", "fit", 8, 1, 1, 1, 0.25], str(rules["start"]))
    check("Fit lands the whole replay in about 30 seconds and is never slower than as drawn; a rate is itself",
          rules["fit"] == [4, 1, 4], str(rules["fit"]))
    check("the artist's time counts every positive gap and nothing across a take's restart",
          rules["drawn"] == 290, str(rules["drawn"]))
    check("...and is said in the words a person uses: 15 sec, 47 min, 2 hr 5 min",
          rules["words"] == ["15 sec", "47 min", "2 hr 5 min"], str(rules["words"]))
    check("speeds read ¼× ½× 1× 16×, and a Fit's own number to a tenth under 10 (94×, 1.7×)",
          rules["labels"] == ["¼×", "½×", "1×", "16×", "94×", "1.7×"], str(rules["labels"]))
    check("the speeds offered are ¼× to 16×", rules["rates"] == [0.25, 0.5, 1, 2, 4, 8, 16], str(rules["rates"]))
    check("the artist's clock passes through a squeezed 40-second pause in proportion, not in a jump",
          rules["clock"] == [0, 100, 20100, 40100, 40200, 40200], str(rules["clock"]))
    pg.close()

    # ---- 2. THE SERVER --------------------------------------------------------
    print("\nTHE SERVER")
    codes = {repr(v): post(drawing(0, "tight", extra={} if v is None else {"playSpeed": v}))[0]
             for v in (None, "auto", "drawn", "fit", 8, 0.25, 3, "fast", True)}
    check("a post may carry playSpeed 'auto', 'drawn', 'fit' or a listed rate, or none",
          all(codes[k] == 201 for k in ("None", "'auto'", "'drawn'", "'fit'", "8", "0.25")), str(codes))
    check("...and anything else is refused, not stored for a player to guess at",
          all(codes[k] == 400 for k in ("3", "'fast'", "True")), str(codes))

    # ---- 3. THE SHARED PLAYER ------------------------------------------------
    print("\nTHE SHARED PLAYER")
    # Long pauses kept: about 103 s drawn, about 103 s of replay.
    _, keep = post(drawing(50000, "keep", extra={"playSpeed": "auto"}))
    # The same drawing with its pauses squeezed: 103 s drawn, 3 s of replay.
    _, tight = post(drawing(50000, "tight"))
    _, eight = post(drawing(0, "tight", extra={"playSpeed": 8}))
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def open_player(url):
        pg.goto(BASE + url, wait_until="load")
        pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
        pg.wait_for_timeout(300)

    open_player(tight["url"])
    t_line, t_dur = pg.evaluate(LINE), pg.evaluate("() => document.getElementById('playerDur').textContent")
    open_player(keep["url"])
    k_line = pg.evaluate(LINE)
    check("the line says how long it took to draw and how fast it is watched",
          t_line.startswith("Drawn in 2 min · watching at 1×"), t_line)
    check("...says 'long pauses skipped' when the replay skips them, so the numbers never look wrong",
          t_line.endswith("long pauses skipped"), t_line)
    check("...and does not say it when the pauses are kept", "skipped" not in k_line, k_line)
    check("the clock under the track reads the ARTIST's time (1:42), not the 3-second replay's",
          t_dur == "1:42", t_dur)
    check("an Auto post drawn over a minute starts at Fit, and says the real number",
          k_line == "Drawn in 2 min · watching at Fit · 3.4×", k_line)

    # Fit really fits: the 103 s replay advances about 1/30 of the way a second.
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(200)
    f0 = pg.evaluate(FILL)
    pg.wait_for_timeout(1500)
    f1 = pg.evaluate(FILL)
    check("...and Fit really does play the whole thing in about 30 seconds (5% in 1.5s)",
          3.5 < f1 - f0 < 7, f"{f0:.1f}% -> {f1:.1f}%")
    # Mid-play, a new speed carries on from the same place, then goes faster.
    # Read on either side of the pick, one frame apart, so the gap between the
    # two readings is a frame of drawing (well under 1%) and a jump is not
    # hidden in it: without the re-anchor the segment so far is re-timed at
    # 16x and the drawing leaps about a fifth of the way.
    a, b0 = pg.evaluate("""async () => { const f = () => parseFloat(document.getElementById('playerProgressFill').style.width) || 0;
        const frame = () => new Promise(r => requestAnimationFrame(() => r()));
        await frame(); const a = f();
        document.querySelector('#playerLine .rl-speed').click();
        document.querySelector('#playerLine .rl-chips [data-r="16"]').click();
        await frame(); await frame(); return [a, f()]; }""")
    pg.wait_for_timeout(1000)
    b1 = pg.evaluate(FILL)
    check("a speed picked mid-play carries on from where the drawing is, without a jump",
          abs(b0 - a) < 1.5, f"{a:.2f}% before, {b0:.2f}% two frames after")
    check("...and then plays at the new speed (16x: about 16% a second of a 103 s replay)",
          12 < b1 - b0 < 20, f"{b0:.1f}% -> {b1:.1f}%")
    check("...and the line and the chips say so, and the speeds close",
          pg.evaluate(LINE).endswith("watching at 16×")
          and pg.evaluate("() => document.querySelector('#playerLine .rl-chips [aria-pressed=true]').textContent") == "16×"
          and pg.evaluate("() => document.querySelector('#playerLine .rl-chips').hidden"), pg.evaluate(LINE))
    pg.click("#playerPlayBtn")   # pause

    # EVERY SPEED FITS ITS OWN PILL (centring census): an even split gave each
    # chip 28px and "16×" ran 5px out of its pill, at every width.
    for vw in (320, 402, 1100):
        pg.set_viewport_size({"width": vw, "height": 874 if vw < 1000 else 900})
        open_player(keep["url"])
        pg.evaluate("() => document.querySelector('#playerLine .rl-speed').click()"); pg.wait_for_timeout(350)
        fit = pg.evaluate("""() => { const c = document.querySelector('#playerLine .rl-chips'), cr = c.getBoundingClientRect();
            return { row: [Math.round(cr.left), Math.round(cr.right)], chips: [...c.querySelectorAll('button')].map(b =>
              [b.textContent, b.scrollWidth - b.clientWidth, Math.round(b.getBoundingClientRect().right) <= Math.round(cr.right)]) }; }""")
        check(f"at {vw}px every speed's label fits inside its own chip, and every chip inside the row and the screen",
              len(fit["chips"]) == 8 and all(o <= 0 and inside for _, o, inside in fit["chips"])
              and fit["row"][0] >= 0 and fit["row"][1] <= vw, str(fit))
    pg.set_viewport_size({"width": 1100, "height": 900})

    open_player(eight["url"])
    check("a post whose author picked 8x starts at 8x", pg.evaluate(LINE).endswith("watching at 8×"),
          pg.evaluate(LINE))

    # The scrubber: the drawing's shape. Three strokes with two 50 s pauses kept:
    # ink in three bursts, flat in the two pauses between them.
    open_player(keep["url"])
    shape = pg.evaluate("""() => { const c = document.querySelector('#playerProgress canvas.rl-strip');
        if (!c || !c.width) return null; const x = c.getContext('2d'), w = c.width, h = c.height, cols = [];
        const d = x.getImageData(0, 0, w, h).data;
        for (let k = 0; k < 20; k++) { let n = 0; const x0 = Math.floor(k * w / 20), x1 = Math.floor((k + 1) * w / 20);
          for (let y = 0; y < h; y++) for (let xx = x0; xx < x1; xx++) if (d[(y * w + xx) * 4 + 3] > 0) n++;
          cols.push(n); }
        return cols; }""")
    # Strokes take 1 s each in a 103 s replay: ink at the very start, the middle and the end.
    check("the bar shows the drawing's shape: ink where it was drawn, flat where the artist paused",
          shape is not None and shape[0] > 0 and shape[19] > 0 and shape[10] > 0
          and shape[4] == 0 and shape[5] == 0 and shape[14] == 0 and shape[15] == 0, str(shape))

    bar = pg.locator("#playerProgress").bounding_box()
    y = bar["y"] + bar["height"] / 2
    pg.mouse.move(bar["x"] + bar["width"] * 0.25, y)
    pg.mouse.down()
    pg.wait_for_timeout(250)   # the bubble fades in over 0.15s
    at_press = pg.evaluate(FRAC)
    bubble = pg.evaluate("""() => { const t = document.querySelector('#playerProgress .rl-bubble');
        return { text: t.textContent, shown: getComputedStyle(t).opacity }; }""")
    pg.mouse.move(bar["x"] + bar["width"] * 0.45, y, steps=6)
    on_bar = pg.evaluate(FRAC)
    pg.mouse.move(bar["x"] + bar["width"] * 0.45, y - 130, steps=4)
    up_at = pg.evaluate(FRAC)
    pg.mouse.move(bar["x"] + bar["width"] * 0.65, y - 130, steps=6)
    fine = pg.evaluate(FRAC)
    fine_tip = pg.evaluate("() => document.querySelector('#playerProgress .rl-bubble').textContent")
    pg.mouse.up()
    check("a press on the bar jumps to where it lands, and a bubble shows the artist's clock there",
          24 <= at_press <= 26 and bubble["shown"] == "1" and bubble["text"].startswith("0:2"),
          f"{at_press}%, {bubble}")
    check("...dragging along it moves the replay as far as the finger moves", 43 <= on_bar <= 47, f"{on_bar}%")
    check("...and slid up off the bar, the same movement covers a quarter of that (fine scrub), and says so",
          3 <= fine - up_at <= 7 and "fine ¼×" in fine_tip, f"{up_at}% -> {fine}%, '{fine_tip}'")

    cv = pg.locator("#canvas").bounding_box()
    s0 = pg.evaluate(FRAC)
    pg.mouse.move(cv["x"] + 60, cv["y"] + 80)
    pg.mouse.down()
    pg.mouse.move(cv["x"] + 60 + cv["width"] * 0.3, cv["y"] + 86, steps=8)
    pg.mouse.up()
    s1 = pg.evaluate(FRAC)
    # Mostly down, and more than the 10px a tap allows sideways: a scroll or a
    # stray gesture, not a scrub.
    pg.mouse.move(cv["x"] + 300, cv["y"] + 40)
    pg.mouse.down()
    pg.mouse.move(cv["x"] + 340, cv["y"] + 280, steps=8)
    pg.mouse.up()
    s2 = pg.evaluate(FRAC)
    check("a sideways drag across the drawing scrubs it: the whole width is the whole replay",
          27 <= s1 - s0 <= 33, f"{s0}% -> {s1}%")
    check("...and an up-and-down drag does not", s2 == s1, f"{s1}% -> {s2}%")

    # Tap to pause, on the shared player too.
    open_player(eight["url"])
    pg.click("#playerPlayBtn")
    pg.wait_for_timeout(400)
    pg.mouse.click(cv["x"] + cv["width"] / 2, cv["y"] + cv["height"] / 2)
    pg.wait_for_timeout(100)
    p0 = pg.evaluate(FILL)
    glyph = pg.evaluate("() => { const g = document.querySelector('.canvas-wrap .tap-paused'); return g ? getComputedStyle(g).display : 'absent'; }")
    pg.wait_for_timeout(500)
    p1 = pg.evaluate(FILL)
    # The fill read on every frame from before the second tap, and the most
    # it reached: at 8x what is left of this replay runs about 310 ms and a
    # post loops, so one read 300 ms on caught the next lap at 0% on a busy
    # machine (the replay had carried on, finished and begun again).
    pg.evaluate("""() => { const out = window.__fills = [], t0 = performance.now();
        (function f() { out.push(parseFloat(document.getElementById('playerProgressFill').style.width) || 0);
          if (performance.now() - t0 < 2000) requestAnimationFrame(f); })(); }""")
    pg.mouse.click(cv["x"] + cv["width"] / 2, cv["y"] + cv["height"] / 2)
    pg.wait_for_timeout(300)
    p2 = pg.evaluate("() => Math.max(...window.__fills)")
    glyph2 = pg.evaluate("() => { const g = document.querySelector('.canvas-wrap .tap-paused'); return g ? getComputedStyle(g).display : 'absent'; }")
    check("on a shared link a tap on the drawing pauses it where it is, with the play mark in the middle",
          p0 > 0 and p1 == p0 and glyph == "grid", f"{p0}% -> {p1}%, mark {glyph}")
    check("...and a second tap carries it on, and the mark goes", p2 > p1 and glyph2 == "none",
          f"{p1}% -> {p2}%, mark {glyph2}")
    check("no page errors on the shared player", not errs, "; ".join(errs[:2]))
    pg.close()

    # ---- 4. THE IN-POST PLAYER -------------------------------------------------
    print("\nTHE IN-POST PLAYER")
    pg = b.new_page(viewport={"width": 900, "height": 900})
    browsing.goto(pg, BASE, "/feed")
    inline = pg.evaluate("""(ps) => ps.map(p => { const src = document.querySelector('.skribl-inline');
        const el = src.cloneNode(true); document.body.appendChild(el);
        return window.SkriblInline.attach(el, p).rate(); })""",
                         [drawing(0, "tight", extra={"playSpeed": 8}), drawing(50000, "keep", extra={"playSpeed": "auto"}),
                          drawing(0, "tight"), drawing(0, "tight", extra={"playSpeed": "drawn"})])
    check("the in-post player starts where the author chose too: 8x, Fit's number, and as drawn without a pick",
          inline[0] == 8 and abs(inline[1] - 102.975 / 30) < 0.01 and inline[2] == 1 and inline[3] == 1, str(inline))
    pg.close()

    # ---- 5. THE PAD -----------------------------------------------------------
    for label, vw, vh in (("desk", 1280, 900), ("phone", 402, 874)):
        print(f"\nTHE PAD ({label})")
        pg = b.new_page(viewport={"width": vw, "height": vh})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(pg, BASE, "/")
        pg.evaluate("() => localStorage.removeItem('skribl_replay_rate')")
        box = pg.locator("#canvas").bounding_box()
        for k in range(2):
            pg.mouse.move(box["x"] + 60, box["y"] + 120 + k * 120)
            pg.mouse.down()
            for i in range(60):
                pg.mouse.move(box["x"] + 60 + i * 4, box["y"] + 120 + k * 120 + math.sin(i / 6) * 30)
                pg.wait_for_timeout(16)
            pg.mouse.up()
            pg.wait_for_timeout(300)
        pg.click("#recordBtn")
        pg.wait_for_timeout(300)
        pg.evaluate("() => setPauseMode('keep')")
        at_rest = pg.evaluate("() => document.getElementById('padLine').hidden")
        pg.click("#playBtn")
        pg.wait_for_timeout(250)
        # On a phone the Pad's Repeat sits at the bar's end (verify_padrepeat):
        # the line spans the two.
        geo = pg.evaluate("""() => { const l = document.getElementById('padLine').getBoundingClientRect(),
            b = document.getElementById('playScrub').getBoundingClientRect(), rp = document.getElementById('padBarRepeat'),
            rr = rp && rp.getClientRects().length ? rp.getBoundingClientRect() : null,
            s = { left: b.left, top: b.top, bottom: b.bottom, width: (rr ? Math.max(b.right, rr.right) : b.right) - b.left };
            return { shown: !document.getElementById('padLine').hidden, lineTop: l.top, lineBottom: l.bottom,
                     scrubTop: s.top, scrubBottom: s.bottom, dl: Math.abs(l.left - s.left), dw: Math.abs(l.width - s.width),
                     text: document.querySelector('#padLine .rl-text').innerText.replace(/\\s+/g, ' ').trim() }; }""")
        where = (geo["lineTop"] >= geo["scrubBottom"]) if label == "desk" else (geo["lineBottom"] <= geo["scrubTop"])
        check(f"[{label}] Play shows the line, " + ("under the scrubber" if label == "desk" else "above the scrubber")
              + ", as wide as it" + (" and Repeat at its end" if label != "desk" else "") + ", and it was hidden before",
              at_rest and geo["shown"] and where and geo["dl"] <= 1 and geo["dw"] <= 1, str(geo))
        check(f"[{label}] ...saying how long it took to draw and how fast the preview runs",
              geo["text"].startswith("Drawn in ") and geo["text"].endswith("watching at 1×"), geo["text"])
        pos = "() => Math.min(playTotal, (performance.now() - playStart) * replayRate)"
        a = pg.evaluate(pos)
        pick(pg, "#padLine", "0.25")
        b0 = pg.evaluate(pos)
        pg.wait_for_timeout(400)
        b1 = pg.evaluate(pos)
        check(f"[{label}] a speed picked mid-play carries on from the same place, then runs at it (¼x)",
              abs(b0 - a) < 80 and 60 < b1 - b0 < 160, f"{a:.0f} -> {b0:.0f} -> {b1:.0f} ms of drawing")
        check(f"[{label}] ...remembered for the Pad's next preview, and never written into the post",
              pg.evaluate("() => [localStorage.getItem('skribl_replay_rate'), serializeSkribl().playSpeed]")
              == ["0.25", "auto"], str(pg.evaluate("() => [localStorage.getItem('skribl_replay_rate'), serializeSkribl().playSpeed]")))
        was = pg.evaluate("() => playing")
        pg.click("#playBtn")   # Stop (at 1/4x the replay is still running)
        pg.wait_for_timeout(400)
        check(f"[{label}] Stop takes the line away: it shows only while a replay plays",
              was and pg.evaluate("() => !playing && document.getElementById('padLine').hidden"))
        TAP = """(el) => { const r = el.getBoundingClientRect(), b = getComputedStyle(el, '::before');
            const n = v => parseFloat(v) || 0, has = b.content !== 'none' && b.position === 'absolute';
            return [Math.round(r.width - (has ? Math.min(0, n(b.left)) + Math.min(0, n(b.right)) : 0)),
                    Math.round(r.height - (has ? Math.min(0, n(b.top)) + Math.min(0, n(b.bottom)) : 0))]; }"""
        CHIPS = """(s) => [...document.querySelectorAll(s + ' .rl-chips button')].map(b => {
            const r = b.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { t: b.textContent, hit: e === b, inside: r.left >= 0 && r.right <= innerWidth }; })"""
        # REPLAY SPEED IN CANVAS SETTINGS (owner's pick 2): the speed at rest,
        # on a phone and a desk alike, under Pauses. (Kept after the replay,
        # #386, the line sat over the frame's edge on the owner's iPhone.)
        pg.click("#tuneBtn"); pg.wait_for_timeout(600)
        pg.evaluate("() => document.getElementById('tuneSpeedRow').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(200)
        rw = pg.evaluate("""() => { const b = document.querySelector('#tuneSpeed .rl-speed'), r = b.getBoundingClientRect();
            const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            const prev = document.getElementById('tuneSpeedRow').previousElementSibling;
            return { painted: !!e && b.contains(e), text: b.textContent, label: b.getAttribute('aria-label'), afterPauses: !!prev && prev.id === 'tunePauseRow' }; }""")
        check(f"[{label}] Canvas settings has a Watching speed row under Pauses, painted, saying the speed and what it is",
              rw["painted"] and rw["afterPauses"] and rw["text"] == "¼×" and rw["label"] == "Watching speed, ¼×", str(rw))
        pg.click("#tuneSpeed .rl-speed"); pg.wait_for_timeout(350)
        ch = pg.evaluate(CHIPS, "#tuneSpeed")
        check(f"[{label}] ...its speeds open inside the panel, each one on top and on screen",
              len(ch) == 8 and all(c["hit"] and c["inside"] for c in ch), str(ch))
        taps = [pg.evaluate(TAP, pg.locator("#tuneSpeed .rl-speed").element_handle())] + \
               [pg.evaluate(TAP, h) for h in pg.locator("#tuneSpeed .rl-chips button").element_handles()]
        # The eight share the pill evenly (THE PILL'S ENDS, below): 44px each
        # where the row has room, narrower together on a phone, where 44 apiece
        # ran out of the pill and, at 375 and under, off the screen.
        share = pg.evaluate("() => { const p = document.querySelector('#tuneSpeed .rl-chips'), c = getComputedStyle(p); return (p.clientWidth - parseFloat(c.paddingLeft) - parseFloat(c.paddingRight)) / 8; }")
        check(f"[{label}] ...the button is a 44px tap, and every speed 44px tall and as wide as the eight share the pill (44 where the row has room)",
              taps[0][0] >= 44 and taps[0][1] >= 44 and all(h >= 44 and w >= min(44, math.floor(share) - 1) for w, h in taps[1:]), f"{taps}; share {share:.1f}")
        pg.click("#tuneSpeed .rl-chips button[data-r='16']"); pg.wait_for_timeout(250)
        check(f"[{label}] ...a pick there is the Pad's speed, and the line (and a desk's pill) say the same",
              pg.evaluate("""() => [localStorage.getItem('skribl_replay_rate'), document.querySelector('#tuneSpeed .rl-speed').textContent,
                  document.querySelector('#padLine .rl-speed').textContent, document.querySelector('#padSpeed .rl-speed').textContent,
                  document.querySelector('#tuneSpeed .rl-chips').hidden]""") == ["16", "16×", "16×", "16×", True])
        pg.click("#tuneBtn"); pg.wait_for_timeout(400)
        if label == "desk":
            # THE SPEED BESIDE PLAY (owner's D1): on a desk, also in the Play pill.
            sp = pg.locator("#padSpeed .rl-speed")
            st = pg.evaluate("""() => { const b = document.querySelector('#padSpeed .rl-speed'), r = b.getBoundingClientRect();
                const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return { painted: !!e && b.contains(e), text: b.textContent, label: b.getAttribute('aria-label'),
                         inPill: !!b.closest('#playWrap') }; }""")
            check(f"[{label}] on a desk the speed also sits in the Play pill, painted, saying its speed and what it is",
                  st["painted"] and st["inPill"] and st["text"] == "16×" and st["label"] == "Watching speed, 16×", str(st))
            sp.click(); pg.wait_for_timeout(350)
            chips = pg.evaluate(CHIPS, "#padSpeed")
            check(f"[{label}] ...tapping it opens every speed, each one on top and on screen",
                  len(chips) == 8 and all(c["hit"] and c["inside"] for c in chips), str(chips))
            taps = [pg.evaluate(TAP, sp.element_handle())] + [pg.evaluate(TAP, h) for h in pg.locator("#padSpeed .rl-chips button").element_handles()]
            check(f"[{label}] ...and the button and every speed are at least a 44px tap",
                  all(w >= 44 and h >= 44 for w, h in taps), str(taps))
            pg.click("#padSpeed .rl-chips button[data-r='2']"); pg.wait_for_timeout(250)
            check(f"[{label}] ...a pick is the Pad's speed, and the line and the settings row say the same",
                  pg.evaluate("""() => [localStorage.getItem('skribl_replay_rate'), document.querySelector('#padSpeed .rl-speed').textContent,
                      document.querySelector('#padLine .rl-speed').textContent, document.querySelector('#tuneSpeed .rl-speed').textContent,
                      document.querySelector('#padSpeed .rl-chips').hidden]""") == ["2", "2×", "2×", "2×", True])
        else:
            check(f"[{label}] the Play pill has no speed of its own on a phone (the settings row is the speed here)",
                  pg.evaluate("() => getComputedStyle(document.getElementById('padSpeed')).display === 'none'"))
        check(f"[{label}] the music keeps up between half and double speed and is a bed outside them",
              pg.evaluate("() => [0.25, 0.5, 2, 4].map(r => { setReplayRate(r); return musicRate(); })") == [1, 0.5, 2, 1])
        check(f"[{label}] no page errors", not errs, "; ".join(errs[:2]))
        pg.close()

    # ---- 5b. ROOM TO BREATHE (the owner's pick B, iPhone) -------------------
    # Two rows of words above a 30px bar sat 21px onto the drawing on every
    # phone height but the tallest (874, the one the checks above use). The bar
    # now sits slim and low in the toolbar's band, 24px clear of the screen's
    # foot, the words are one row in the middle of what is left, and the pauses
    # note comes with the speeds. Asserted at the owner's height (813, a Home
    # Screen app) and around it, where the old layout was wrong.
    print("\nTHE PAD ON A PHONE: ROOM TO BREATHE")
    for vh in (874, 813, 750, 664):
        pg = b.new_page(viewport={"width": 402, "height": vh})
        browsing.goto(pg, BASE, "/")
        box = pg.locator("#canvas").bounding_box()
        for k in range(2):
            pg.mouse.move(box["x"] + 80, box["y"] + 140 + k * 100)
            pg.mouse.down()
            for i in range(30):
                pg.mouse.move(box["x"] + 80 + i * 6, box["y"] + 140 + k * 100 + math.sin(i / 5) * 20)
                pg.wait_for_timeout(16)
            pg.mouse.up()
            pg.wait_for_timeout(2300 if k == 0 else 300)   # a long pause, so "long pauses skipped" applies
        pg.click("#recordBtn"); pg.wait_for_timeout(300)
        rest = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return [r.top, r.bottom, r.width]; }")
        pg.click("#playBtn"); pg.wait_for_timeout(500)
        g = pg.evaluate("""() => { const q = s => document.querySelector(s), R = s => q(s).getBoundingClientRect();
            const c = R('#canvas'), w = R('.canvas-wrap'), t = R('#padLine .rl-text'), s = R('#playScrub'), a = getComputedStyle(q('#playScrub'), '::after');
            const mid = document.elementFromPoint(t.left + t.width / 2, t.top + t.height / 2);
            return { canvas: [c.top, c.bottom, c.width], rim: w.bottom, textTop: t.top, textBottom: t.bottom, textH: t.height,
                     scrubTop: s.top, scrubBottom: s.bottom, scrubH: s.height, grab: s.height - parseFloat(a.top) - parseFloat(a.bottom),
                     foot: innerHeight - s.bottom, painted: !!mid && q('#padLine').contains(mid),
                     skipNow: getComputedStyle(q('#padLine .rl-skip')).display, skipApplies: !q('#padLine .rl-skip').hidden }; }""")
        check(f"[402x{vh}] the words clear the drawing and the bar, painted, on one row",
              g["textTop"] >= g["rim"] + 4 and g["textBottom"] <= g["scrubTop"] - 4 and g["painted"] and g["textH"] < 34,
              str({k: round(v, 1) if isinstance(v, float) else v for k, v in g.items()}))
        check(f"[402x{vh}] ...the bar is slim (18px), still a 44px grab, and sits 24px clear of the screen's foot",
              abs(g["scrubH"] - 18) < 0.5 and g["grab"] >= 44 and abs(g["foot"] - 24) < 1,
              f"h {g['scrubH']} grab {g['grab']} foot {g['foot']}")
        check(f"[402x{vh}] ...and the drawing did not move or shrink for it",
              [round(v, 1) for v in g["canvas"]] == [round(v, 1) for v in rest], f"{rest} -> {g['canvas']}")
        pg.click("#padLine .rl-speed"); pg.wait_for_timeout(350)
        opened = pg.evaluate("() => getComputedStyle(document.querySelector('#padLine .rl-skip')).display")
        check(f"[402x{vh}] \"long pauses skipped\" is not on the line, and shows with the speeds",
              g["skipApplies"] and g["skipNow"] == "none" and opened != "none", f"applies {g['skipApplies']} rest {g['skipNow']} open {opened}")
        pg.close()

    # ---- 5c. THE BUBBLE RIDES OVER THE FINGER (the owner's P5, pick A) -------
    # 10px over the bar, the artist's clock sat under the fingertip and on the
    # Pad's words on the owner's iPhone. A finger or a pen now carries it 56px
    # over the touch, up with it into fine scrub, kept on screen at both ends;
    # a mouse keeps it 10px over the bar; and while it shows, the words beside
    # the bar fade -- on the Pad, the link page and the in-post player alike.
    print("\nTHE BUBBLE OVER THE FINGER")
    LIFT = 56
    # PAINTED is what is on top at the bubble's middle, passing over layers
    # faded to nothing (the words, which fade so the bubble shows through).
    BUB = """([bar, line]) => { const q = s => document.querySelector(s), t = q(bar + ' .rl-bubble');
        const r = t.getBoundingClientRect(), cs = getComputedStyle(t);
        const seen = el => { for (let n = el; n; n = n.parentElement) if (getComputedStyle(n).opacity === '0') return false; return true; };
        t.style.pointerEvents = 'auto';   // it takes no touches; asked here only what is painted on top
        const e = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2).find(seen);
        t.style.pointerEvents = '';
        return { bottom: r.bottom, left: r.left, right: r.right, shown: cs.opacity, painted: !!e && t.contains(e),
                 barTop: q(bar).getBoundingClientRect().top, words: getComputedStyle(q(line)).opacity,
                 vw: document.documentElement.clientWidth }; }"""

    def finger(pg, cdp, bar, line, name):
        """A real finger on the bar: press at a quarter, drag along it, slide up
        into fine scrub, back down and off the right end, then the left end, and
        lift there (the start, so the Pad's preview is still running after)."""
        pg.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", bar)
        pg.wait_for_timeout(150)
        bx = pg.locator(bar).bounding_box()
        x, y = bx["x"] + bx["width"] * 0.25, bx["y"] + bx["height"] / 2

        def t(kind, px, py):
            cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": px, "y": py}]})
            pg.wait_for_timeout(16)

        t("touchStart", x, y)
        for k in range(1, 7):
            t("touchMove", x + bx["width"] * 0.2 * k / 6, y)
        x += bx["width"] * 0.2
        pg.wait_for_timeout(250)   # the bubble and the words fade over 0.15s
        on = pg.evaluate(BUB, [bar, line])
        for k in range(1, 5):
            t("touchMove", x, y - 130 * k / 4)
        up = pg.evaluate(BUB, [bar, line])
        vw = on["vw"]
        for k in range(1, 9):
            t("touchMove", x + (vw - 1 - x) * k / 8, y)
        hi = pg.evaluate(BUB, [bar, line])
        for k in range(1, 9):
            t("touchMove", vw - 1 - (vw - 2) * k / 8, y)
        lo = pg.evaluate(BUB, [bar, line])
        t("touchEnd", 0, 0)
        pg.wait_for_timeout(300)
        after = pg.evaluate(BUB, [bar, line])
        r1 = lambda d: {k: round(v, 1) if isinstance(v, float) else v for k, v in d.items()}
        check(f"[{name}] a finger's press shows the clock {LIFT}px over the touch, painted, not under the fingertip",
              on["shown"] == "1" and on["painted"] and abs(on["bottom"] - (y - LIFT)) <= 1, f"touch at {y:.1f}: {r1(on)}")
        check(f"[{name}] ...and slid up into fine scrub, the bubble rides up with the finger",
              up["painted"] and abs(up["bottom"] - (y - 130 - LIFT)) <= 1, f"touch at {y - 130:.1f}: {r1(up)}")
        check(f"[{name}] ...the words beside the bar fade while it shows",
              on["words"] == "0" and up["words"] == "0", f"{on['words']} / {up['words']}")
        check(f"[{name}] ...the bubble stays on screen at both ends of the drawing",
              hi["right"] <= vw - 7.5 and lo["left"] >= 7.5 and hi["painted"] and lo["painted"],
              f"end: right {hi['right']:.1f} of {vw}; start: left {lo['left']:.1f}")
        check(f"[{name}] ...and when the finger lifts, the bubble goes and the words come back",
              after["shown"] == "0" and after["words"] == "1", r1(after))

    phone = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)

    # The Pad's preview, at a quarter speed so it is still running when the finger lifts.
    pg = phone.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/")
    box = pg.locator("#canvas").bounding_box()
    for k in range(2):
        pg.mouse.move(box["x"] + 60, box["y"] + 120 + k * 120)
        pg.mouse.down()
        for i in range(60):
            pg.mouse.move(box["x"] + 60 + i * 4, box["y"] + 120 + k * 120 + math.sin(i / 6) * 30)
            pg.wait_for_timeout(16)
        pg.mouse.up()
        pg.wait_for_timeout(300)
    pg.click("#recordBtn"); pg.wait_for_timeout(300)
    pg.click("#playBtn"); pg.wait_for_timeout(300)
    pick(pg, "#padLine", "0.25")
    pg.wait_for_timeout(400)   # the speeds close
    finger(pg, pg.context.new_cdp_session(pg), "#playScrub", "#padLine", "Pad, phone")
    check("[Pad, phone] ...the preview carries on after the drag", pg.evaluate("() => playing && !scrubbing"))
    check("[Pad, phone] no page errors", not errs, "; ".join(errs[:2]))
    pg.close()

    # The link page, on the same phone; then a finger on the drawing itself.
    pg = phone.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + keep["url"], wait_until="load")
    pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
    pg.wait_for_timeout(300)
    cdp = pg.context.new_cdp_session(pg)
    finger(pg, cdp, "#playerProgress", "#playerLine", "link page, phone")
    cv = pg.locator("#canvas").bounding_box()
    cx, cy = cv["x"] + 60, cv["y"] + cv["height"] * 0.6
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx, "y": cy}]})
    for k in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": cx + 12 * k, "y": cy}]})
        pg.wait_for_timeout(16)
    pg.wait_for_timeout(250)
    on = pg.evaluate(BUB, ["#playerProgress", "#playerLine"])
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    check(f"[link page, phone] a finger dragging across the drawing itself has the clock {LIFT}px over it too",
          on["shown"] == "1" and on["painted"] and abs(on["bottom"] - (cy - LIFT)) <= 1, f"touch at {cy:.1f}: {on}")
    check("[link page, phone] no page errors", not errs, "; ".join(errs[:2]))
    pg.close()

    # The in-post player, in the feed (a public post, so the feed lists it).
    _, pub = post(drawing(50000, "keep", extra={"visibility": "public", "title": "Bubble fixture"}))
    pg = phone.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, "/feed")
    sel = f'[data-skribl-id="{pub["id"]}"] + .skribl-inline-line'
    pg.wait_for_selector(sel + ".is-on", timeout=10000)
    finger(pg, pg.context.new_cdp_session(pg), sel + " .skribl-inline-scrub", sel + " .skribl-inline-say", "in-post, phone")
    check("[in-post, phone] no page errors", not errs, "; ".join(errs[:2]))
    pg.close()
    phone.close()

    # A mouse covers nothing: its bubble keeps to 10px over the bar, slid up or
    # not. A pen is a hand on the glass, as a finger is.
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    pg.goto(BASE + keep["url"], wait_until="load")
    pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
    pg.wait_for_timeout(300)
    bx = pg.locator("#playerProgress").bounding_box()
    x, y = bx["x"] + bx["width"] * 0.3, bx["y"] + bx["height"] / 2
    pg.mouse.move(x, y); pg.mouse.down()
    pg.mouse.move(x + 60, y, steps=4); pg.wait_for_timeout(250)
    m_on = pg.evaluate(BUB, ["#playerProgress", "#playerLine"])
    pg.mouse.move(x + 60, y - 130, steps=4)
    m_up = pg.evaluate(BUB, ["#playerProgress", "#playerLine"])
    pg.mouse.up(); pg.wait_for_timeout(300)
    check("[link page, desk] a mouse's bubble keeps to 10px over the bar, on it and slid up off it",
          abs(m_on["bottom"] - (m_on["barTop"] - 10)) <= 1 and abs(m_up["bottom"] - (m_up["barTop"] - 10)) <= 1
          and m_on["shown"] == "1" and m_on["painted"], f"{m_on} / {m_up}")
    cdp = pg.context.new_cdp_session(pg)
    pen = lambda kind, py, px=x: cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": px, "y": py, "button": "left",
                                                                      "buttons": 0 if kind == "mouseReleased" else 1,
                                                                      "clickCount": 1, "pointerType": "pen", "force": 0.5})
    pen("mousePressed", y)
    for k in range(1, 5):
        pen("mouseMoved", y, x + 15 * k); pg.wait_for_timeout(16)
    pg.wait_for_timeout(250)
    p_on = pg.evaluate(BUB, ["#playerProgress", "#playerLine"])
    pen("mouseReleased", y, x + 60)
    check(f"[link page, desk] ...and a pen's rides {LIFT}px over its tip, as a finger's does",
          p_on["shown"] == "1" and abs(p_on["bottom"] - (y - LIFT)) <= 1, f"pen at {y:.1f}: {p_on}")
    pg.close()

    # ---- 6. THE POST SHEET ----------------------------------------------------
    print("\nTHE POST SHEET")
    pg = b.new_page(viewport={"width": 402, "height": 874})
    browsing.goto(pg, BASE, "/")
    pg.evaluate("() => localStorage.setItem('skribl_replay_rate', '8')")
    browsing.goto(pg, BASE, "/")
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 200)
    pg.mouse.down()
    for i in range(40):
        pg.mouse.move(box["x"] + 60 + i * 5, box["y"] + 200 + math.sin(i / 6) * 30)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.evaluate("() => { if (recording) endRecordingTake(); document.getElementById('postBtn').click(); }")
    pg.wait_for_timeout(700)
    seg = pg.evaluate("""() => [...document.querySelectorAll('#postSpeedSeg button')].filter(b => !b.hidden)
        .map(b => b.textContent.trim() + (b.classList.contains('on') ? '*' : ''))""")
    # The fourth button is "Speed", not the speed last previewed (owner, on the
    # iPhone: "1/4th?"): the preview was left at 8x here, and the sheet does
    # not pull it in.
    check("the Post sheet asks where viewers start: Auto (chosen), As drawn, Fit, and Speed (not the speed last previewed)",
          seg == ["Auto*", "As drawn", "Fit", "Speed"], str(seg))
    check("...and Auto is what a post carries untouched", pg.evaluate("() => serializeSkribl().playSpeed") == "auto")
    pg.click("#postSpeedPick"); pg.wait_for_timeout(150)
    chips = pg.evaluate("""() => { const c = document.getElementById('postSpeedChips'); const r = c.getBoundingClientRect();
        const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return { open: !c.hidden, painted: !!h && c.contains(h), rates: [...c.querySelectorAll('button')].map(b => b.textContent),
                 taps: [...c.querySelectorAll('button')].map(b => Math.round(b.getBoundingClientRect().height)) }; }""")
    check("...Speed opens all seven rates, painted, each a 44px tap",
          chips["open"] and chips["painted"] and chips["rates"] == ["¼×", "½×", "1×", "2×", "4×", "8×", "16×"]
          and min(chips["taps"]) >= 44, str(chips))
    picked = []
    for v in ("8", "fit", "drawn", "auto"):
        if v == "8":
            pg.click("#postSpeedChips button[data-rate='8']")
        else:
            pg.evaluate("(v) => document.querySelector('#postSpeedSeg button[data-speed=\"' + v + '\"]').click()", v)
        picked.append(pg.evaluate("""() => [serializeSkribl().playSpeed, document.getElementById('postSpeedHint').textContent,
            document.getElementById('postSpeedPick').textContent.trim(), document.getElementById('postSpeedChips').hidden]"""))
    check("each choice is what the post carries, and the line under it says what it does",
          [x[0] for x in picked] == [8, "fit", "drawn", "auto"]
          and picked[0][1].startswith("At 8×") and picked[1][1].startswith("The whole drawing in about 30 seconds")
          and all(x[1].endswith("Anyone watching can change it.") for x in picked), str(picked))
    check("...a rate picked from Speed closes the row and the button shows it; another choice puts Speed back",
          picked[0][2] == "8×" and picked[0][3] and picked[1][2] == "Speed", str(picked))
    h = pg.evaluate("() => document.getElementById('postSpeedSeg').getBoundingClientRect().height")
    check("...and its buttons are a 44px tap", h >= 44, f"{h}px")
    pg.close()
    pg = b.new_page()
    browsing.goto(pg, BASE, "/flip")
    check("Flip's Post sheet has no such row: a Flip loops, it has no speed to start at",
          pg.evaluate("() => !document.getElementById('postSpeedSeg')"))
    pg.close()

    # FLIP'S PREVIEW, KIND TO THE CANVAS (F1, the owner's pick C). While it
    # plays nothing sits on the drawing: the scrubber is a 3px line along the
    # page strip, the page on screen is outlined in the strip, and the speeds
    # (five, ¼x to 4x) take the idle Duplicate / Blank row. The same speeds sit
    # in Playback settings for when nothing plays.
    for vw, vh in ((402, 874), (1280, 800)):
        pg = b.new_page(viewport={"width": vw, "height": vh})
        browsing.goto(pg, BASE, "/flip")
        pg.evaluate("() => { if (window.SkriblHints) SkriblHints.hide(); localStorage.removeItem('skribl_flip_rate'); }")
        # Four pages with ink, the second held three beats: six beats in all.
        pg.evaluate("""() => { const pt = (x, i) => ({ x: x + i * 6, y: 200 + (i % 5) * 5, size: 6, color: '#7c5cff', t: i * 20, start: i === 0 });
            frames.length = 0;
            for (let k = 0; k < 4; k++) frames.push({ strokes: Array.from({ length: 14 }, (_, i) => pt(100 + k * 40, i)), strokeGroups: [14] });
            frames[1].hold = 3; fps = 12; idx = 0; buildStrip(); render(); }""")
        label = f"Flip {vw}"
        pg.click("#play"); pg.wait_for_timeout(500)
        st = pg.evaluate("""() => { const pad = document.getElementById('pad'), r = pad.getBoundingClientRect();
            // what is painted along the drawing's foot, where the old controls sat
            const foot = [0.2, 0.4, 0.5, 0.6, 0.8].map(f => document.elementFromPoint(r.left + r.width * f, r.bottom - 30));
            const line = document.getElementById('flipProgress'), lr = line.getBoundingClientRect(), band = getComputedStyle(line, '::before');
            const sp = document.getElementById('flipSpeeds'), sr = sp.getBoundingClientRect();
            const hit = document.elementFromPoint(sr.left + sr.width / 2, sr.top + sr.height / 2);
            const add = document.querySelector('.addcol');
            return { clear: foot.every(e => e === pad || (e && e.closest && e.closest('.zoom-layer'))),
                     inStrip: !!line.closest('.strip-wrap'), lineH: Math.round(lr.height), band: parseFloat(band.height),
                     linePainted: !!document.elementFromPoint(lr.left + lr.width / 2, lr.top + 1) && line.contains(document.elementFromPoint(lr.left + lr.width / 2, lr.top + 1)),
                     speeds: [...sp.querySelectorAll('[data-rate]')].map(x => x.textContent), speedsPainted: !!hit && sp.contains(hit),
                     addHidden: !add || getComputedStyle(add).display === 'none' }; }""")
        check(f"[{label}] playing, nothing sits on the drawing: its foot shows the drawing itself",
              st["clear"], str(st))
        check(f"[{label}] ...the scrubber is a 3px line along the page strip, painted, with a 44px band to grab",
              st["inStrip"] and st["lineH"] <= 4 and st["band"] >= 44 and st["linePainted"], str(st))
        check(f"[{label}] ...and the speeds, ¼x to 4x, take the Duplicate / Blank row while it plays",
              st["speeds"] == ["¼×", "½×", "1×", "2×", "4×"] and st["speedsPainted"] and st["addHidden"], str(st))
        beats = pg.evaluate("() => [0.1, 0.3, 0.6, 0.7, 0.95].map(_flipPageAt)")
        check(f"[{label}] a place on the line lands on the page holding that beat (page 2 holds beats 2 to 4 of 6)",
              beats == [0, 1, 1, 2, 3], str(beats))
        now = pg.evaluate("() => { const n = [...document.querySelectorAll('#strip .frame')].findIndex(f => f.classList.contains('now')); return [n, idx]; }")
        check(f"[{label}] the strip outlines the page on screen", now[0] == now[1] and now[0] >= 0, str(now))
        # DRAG ACROSS THE DRAWING (the owner's pick, "all yes"): the Pad's
        # sideways scrub, page by page. Paused first (a tap), so the page the
        # drag starts from is known; half the drawing's width from the start
        # of page 1 is beat 3 of 6, which page 2 holds. Then the two things
        # that are not a scrub: mostly up and down, and the tap that paused.
        pcv = pg.locator("#pad").bounding_box()
        pg.evaluate("() => { scrubToPage(0); }")
        pg.mouse.click(pcv["x"] + pcv["width"] / 2, pcv["y"] + pcv["height"] / 2)
        pg.wait_for_timeout(150)
        held = pg.evaluate("() => [idx, document.body.classList.contains('playback-paused')]")
        pg.mouse.move(pcv["x"] + pcv["width"] * 0.2, pcv["y"] + pcv["height"] * 0.5)
        pg.mouse.down()
        pg.mouse.move(pcv["x"] + pcv["width"] * 0.7, pcv["y"] + pcv["height"] * 0.52, steps=10)
        mid = pg.evaluate("() => idx")
        pg.mouse.up()
        pg.wait_for_timeout(150)
        after_drag = pg.evaluate("() => [idx, document.body.classList.contains('playback-paused'), playing]")
        # THE SWIPE, FROM PAGE 3 (one beat of six) and built in pixels: a
        # quarter of the width sideways would cross into page 4 if it were
        # taken for a drag, and it moves 1.4 times as far down, so it is
        # mostly up and down on any shape of box. The first swipe here moved
        # 5% of the width and passed with the guard deleted; the second was
        # sized for a 4:3 box and was sideways on the desk's.
        pg.evaluate("() => { scrubToPage(2); endFrameScrub(); }")
        before_swipe = pg.evaluate("() => idx")
        _dx = pcv["width"] * 0.25
        _dy = min(_dx * 1.4, pcv["height"] * 0.9)
        _cx, _cy = pcv["x"] + pcv["width"] / 2, pcv["y"] + pcv["height"] / 2
        pg.mouse.move(_cx - _dx / 2, _cy - _dy / 2)
        pg.mouse.down()
        pg.mouse.move(_cx + _dx / 2, _cy + _dy / 2, steps=10)
        pg.mouse.up()
        pg.wait_for_timeout(150)
        after_swipe = pg.evaluate("() => idx")
        check(f"[{label}] a sideways drag across the drawing scrubs a Flip page by page: half its width is half the beats",
              held == [0, True] and mid == 1 and after_drag[0] == 1, f"paused on {held}, mid-drag {mid}, released {after_drag}")
        check(f"[{label}] ...a paused Flip stays paused after it, still playing underneath",
              after_drag[1] and after_drag[2], str(after_drag))
        check(f"[{label}] ...and a mostly up-and-down drag leaves the page alone",
              before_swipe == 2 and after_swipe == before_swipe and _dy > _dx,
              f"{before_swipe} -> {after_swipe} ({_dx:.0f}px across, {_dy:.0f}px down)")
        pg.mouse.click(pcv["x"] + pcv["width"] / 2, pcv["y"] + pcv["height"] / 2)   # carry on, as before
        pg.wait_for_timeout(150)
        count = """() => new Promise(res => { let n = 0, last = idx; const t0 = performance.now();
            const tick = () => { if (idx !== last) { n++; last = idx; } if (performance.now() - t0 < 1200) requestAnimationFrame(tick); else res(n); };
            requestAnimationFrame(tick); })"""
        n1 = pg.evaluate(count)
        pg.click("#flipSpeedSeg button[data-rate='4']"); pg.wait_for_timeout(60)
        n4 = pg.evaluate(count)
        check(f"[{label}] 4x turns the pages about four times as fast",
              n1 >= 4 and n4 >= 2.5 * n1, f"{n1} page turns at 1x, {n4} at 4x")
        pg.click("#play"); pg.wait_for_timeout(300)
        rest = pg.evaluate("""() => { const add = document.querySelector('.addcol'), sp = document.getElementById('flipSpeeds');
            return { add: !!add && getComputedStyle(add).display !== 'none', speeds: getComputedStyle(sp).display === 'none' }; }""")
        check(f"[{label}] Stop puts the Duplicate / Blank row back", rest["add"] and rest["speeds"], str(rest))
        pg.click("#tuneBtn"); pg.wait_for_timeout(600)
        row = pg.evaluate("""() => { const g = document.getElementById('watchSeg'); if (!g) return null; g.scrollIntoView({ block: 'center' });
            const on = g.querySelector('button.on'); const r = g.getBoundingClientRect(); const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { on: on && on.textContent, painted: !!h && g.contains(h) }; }""")
        check(f"[{label}] Playback settings has Watching speed at rest, showing the speed picked while it played",
              bool(row) and row["on"] == "4×" and row["painted"], str(row))
        pg.click("#watchSeg button[data-rate='0.5']"); pg.wait_for_timeout(100)
        check(f"[{label}] ...and a speed picked there is the one Play uses",
              pg.evaluate("() => flipRate") == 0.5)
        pg.reload(); pg.wait_for_timeout(700)
        check(f"[{label}] the speed is remembered in this browser", pg.evaluate("() => flipRate") == 0.5)
        pg.evaluate("() => localStorage.removeItem('skribl_flip_rate')")
        pg.close()

    # ---- SCRUBBING A LONG DRAWING (v322 plan, step 3, lib/seekcache.js) -------
    # A seek used to clear the canvas and draw every point from the first: a
    # two-hour drawing took 2.9 s a seek on a CPU slowed 4x. Now a seek starts
    # from the nearest copy of the canvas. What has to hold is that it paints
    # EXACTLY what a replay from the first point paints -- read as pixels, every
    # byte, after each seek of a sequence that goes forward, back, and nudges
    # -- and that it really did start near its target, read as how many points
    # it drew. The drawing has see-through strokes (the compositor's wet layer)
    # and erasers in it; the Pad is checked with the layering on and off.
    print("\nSCRUBBING A LONG DRAWING -- a seek starts from the nearest copy and paints what a replay from the start paints")
    LONG = """(n) => { let s = 11; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
      const pts = [], groups = []; let t = 0, gi = 0;
      while (pts.length < n) {
        const m = 20 + Math.floor(rnd() * 200); let x = 60 + rnd() * 700, y = 60 + rnd() * 480, a = rnd() * 6.283;
        const col = gi % 5 === 2 ? 'rgba(124,92,255,0.45)' : ['#1f1b2e', '#7c5cff', '#ff7a59'][gi % 3];
        const er = gi % 23 === 7; let k = 0;
        for (let i = 0; i < m && pts.length < n; i++, k++) {
          pts.push({ x: x, y: y, color: col, size: 2.5 + 6 * Math.sin(Math.PI * i / m), t: Math.round(t), start: i === 0, erase: er });
          a += (rnd() - 0.5) * 0.3; x = Math.min(800, Math.max(10, x + Math.cos(a) * 5)); y = Math.min(590, Math.max(10, y + Math.sin(a) * 5));
          t += 18; }
        groups.push(k); gi++; t += 200 + rnd() * 900; }
      return { pts: pts, groups: groups }; }"""
    # After a seek, the canvas against a replay from the first point on the
    # same canvas. The replay's own compositor is LEFT AS THE SEEK LEFT IT: when
    # the seek was right, it holds what the reference just painted, so the next
    # seek carries on from it; when the seek kept a stale one, the next seek
    # shows it. (Handing the reference's compositor back hid exactly that.)
    PAD_SAME = """async (f) => { editorSeek(f);
      await new Promise(res => { const t = () => seekRacing() ? requestAnimationFrame(t) : res(); t(); });   // a far first jump races there
      const r = { idx: playIndex, held: playSeek ? playSeek.held().length : -1,
                  drawn: playSeek ? playSeek.drawn() : -1, gap: playSeek ? playSeek.gap() : -1 };
      const w = canvas.width, h = canvas.height, a = ctx.getImageData(0, 0, w, h).data.slice();
      const layers = strokeLayersOn(); let comp = null, i = -1;
      clearAndRestore(() => { comp = layers ? makeStrokeCompositor(ctx, canvas) : null;
        i = replayTimelineToCanvas(playTimeline, 0, lastTargetMs, comp ? comp.dotFn : drawDot, comp ? comp.lineFn : drawLine);
        if (comp) comp.present(); });
      const b = ctx.getImageData(0, 0, w, h).data; let off = 0;
      for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) off++;
      return Object.assign(r, { off: off, ref: i }); }"""
    SEQ = [0.9, 0.3, 0.95, 0.5, 0.52, 0.1, 1.0, 0.75, 0.76, 0.2]
    for _layers, _n in (("on", 60000), ("off", 60000), ("on", 2000)):
        _pg = b.new_context(viewport={"width": 1280, "height": 820}).new_page()
        browsing.goto(_pg, BASE, "/skribl-pad")
        _pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad")
        _pg.evaluate("([n, layers]) => { if (layers === 'off') window.SKRIBL_STROKE_LAYERS = false; const d = (" + LONG + """)(n);
            restoreAutosave({ version: 1, strokes: d.pts, strokeGroups: d.groups, background: { color: '#f6f2ea' } }); }""",
                     [_n, _layers])
        _pg.wait_for_timeout(500)
        _pg.click("#playBtn"); _pg.wait_for_timeout(250)
        _pg.evaluate("() => { scrubbing = true; }")      # the replay holds still; the seeks are the suite's
        _rows = [(f, _pg.evaluate(PAD_SAME, f)) for f in SEQ]
        _bad = [(f, r) for f, r in _rows if r["off"] or r["idx"] != r["ref"]]
        _label = f"Pad, {_n:,} points, layering {_layers}"
        check(f"[{_label}] every seek of ten, forward, back and nudged, paints exactly what a replay from the first point paints",
              not _bad, f"{len(_bad)} differ, first {_bad[:1]}")
        if _n >= 20000:
            # The first seek draws everything before it (that is what takes the
            # copies); every one after it, forward or back, starts near its
            # target -- from a copy or from where the canvas stands, whichever
            # is further along -- so it draws at most two stretches.
            _gap = _rows[0][1]["gap"]
            _after = [(f, r["drawn"]) for f, r in _rows[1:]]
            check(f"[{_label}] ...it keeps copies, and every seek after the first starts near its target: at most two stretches drawn",
                  _rows[-1][1]["held"] >= 2 and 0 < _gap < _n * 0.3 and all(0 <= d <= 2 * _gap for _, d in _after),
                  f"held {_rows[-1][1]['held']}, stretch {_gap:,}, points drawn by each seek after the first {_after}")
        else:
            check(f"[{_label}] a short drawing keeps no copies and seeks as it always did",
                  all(r["held"] == 0 for _, r in _rows), str([r["held"] for _, r in _rows]))
        _pg.context.close()

    # The shared link's player, with the same drawing at what a post may carry
    # today (20,000 points a page). Its compositor is the editor's; the
    # reference is drawn on an offscreen canvas so the player's own state is
    # left as it is between seeks.
    _d = b.new_page()
    browsing.goto(_d, BASE, "/")
    _gen = _d.evaluate("(n) => (" + LONG + ")(n)", 19000)
    _d.close()
    _st, _body = post({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "fps": None,
                       "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                       "frames": [{"strokes": _gen["pts"], "strokeGroups": _gen["groups"], "background": {"color": "#f6f2ea"}}],
                       "title": "a long drawing"})
    PLAYER_SAME = """async (f) => { const r = await window.__skriblPlayerSeek(f);   // once it lands
      const w = canvas.width, h = canvas.height, a = ctx.getImageData(0, 0, w, h).data;
      const off = document.createElement('canvas'); off.width = w; off.height = h;
      const comp = makeStrokeCompositor(off.getContext('2d'), off);
      replayTimelineToCanvas(buildPlaybackTimeline(), 0, r.ms, comp.dotFn, comp.lineFn); comp.present();
      const b = off.getContext('2d').getImageData(0, 0, w, h).data; let n = 0;
      for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) n++;
      return Object.assign(r, { off: n, held: r.held ? r.held.length : -1 }); }"""
    if _st in (200, 201) and _body.get("id"):
        _pg = b.new_context(viewport={"width": 1280, "height": 820}).new_page()
        browsing.goto(_pg, BASE, f"/s/{_body['id']}")
        _pg.wait_for_function("() => typeof window.__skriblPlayerSeek === 'function'")
        _pg.wait_for_timeout(600)
        # Played first, as a viewer would: the replay's own compositor exists
        # before the first seek, so a seek that kept it instead of its own shows.
        _pg.click("#playerPlayBtn")
        _pg.wait_for_timeout(500)
        _rows = [(f, _pg.evaluate(PLAYER_SAME, f)) for f in SEQ]
        _bad = [(f, r) for f, r in _rows if r["off"]]
        check("[shared player, 19,000 points] every seek of ten paints exactly what a replay from the first point paints",
              not _bad, f"{len(_bad)} differ, first {_bad[:1]}")
        _after = [(f, r["drawn"]) for f, r in _rows[1:]]
        check("[shared player, 19,000 points] ...it keeps copies, and every seek after the first starts near its target: at most two stretches drawn",
              _rows[-1][1]["held"] >= 1 and all(0 <= d <= 2 * _rows[0][1]["gap"] for _, d in _after),
              f"held {_rows[-1][1]['held']}, stretch {_rows[0][1]['gap']}, points drawn by each seek after the first {_after}")
        _pg.context.close()
    else:
        check("[shared player, 19,000 points] the long drawing posted", False, f"{_st} {_body}")

    # ---- THE FIRST FAR JUMP RACES THERE (the owner's pick A, from the mock) ----
    # The copies above make every jump after the first short. The first jump to
    # a far part of a long drawing still drew everything up to it at once, and
    # the page stood still: the bar stuck, then the picture jumped. Now it is
    # drawn a slice a frame (lib/seekcache.js race()). Read on a phone the
    # owner's width at 2x for the Pad and on a 2x desk for the shared player: at
    # 2x a stretch between copies is wider than a race's threshold, so "it has
    # copies there" and "it is short" are two different questions. What has to
    # hold:
    #   * the bar and the clock say where it was pointed AT ONCE, while the
    #     drawing is still behind;
    #   * the page keeps moving: frames are painted while it races, and no task
    #     holds one up past 300 ms (the same jump drawn at once is one task of
    #     about a second and a half here). 300, not 50: this box draws a 2x
    #     canvas in software, so a frame that also takes a copy runs 60 ms or
    #     so, and over 200 with three other suites sharing the machine;
    #   * it lands on EXACTLY what a replay from the first point paints, every
    #     byte, and plays on from there;
    #   * the clock holds the place pointed while it races, so a pause mid-race
    #     pauses there;
    #   * a newer seek mid-race takes over from where the canvas really stands;
    #   * Play pressed mid-race waits for the landing; a second press, or a tap
    #     on the drawing, takes it back; a drag holds it;
    #   * Stop or Restart mid-race leaves nothing racing over the canvas;
    #   * a jump through parts it has copies of lands at once, and so does a
    #     short one into new ground.
    print("\nTHE FIRST FAR JUMP RACES THERE -- the page keeps moving, and it lands on exactly today's picture")
    FF_N = 120000
    FF_WATCH = """() => { if (!window.__ff) { window.__ff = { lt: [], frames: 0 };
        new PerformanceObserver(l => { for (const e of l.getEntries()) window.__ff.lt.push(Math.round(e.duration)); }).observe({ type: 'longtask' });
        const f = () => { window.__ff.frames++; requestAnimationFrame(f); }; requestAnimationFrame(f); }
      window.__ff.lt = []; window.__ff.frames = 0; }"""
    # Until it lands; then two frames and a beat, so a long task in the landing
    # frame has been reported before it is read.
    FF_LANDED = """() => new Promise(res => { const t0 = performance.now();
        const t = () => { if (seekRacing() && performance.now() - t0 < 60000) return requestAnimationFrame(t);
          const fr = window.__ff ? window.__ff.frames : 0, ms = Math.round(performance.now() - t0);
          requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(() =>
            res({ frames: fr, ms: ms, lt: window.__ff ? window.__ff.lt.slice() : [], racing: seekRacing() }), 60))); };
        t(); })"""
    FRAMES2 = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
    # PRESSES MID-RACE GO IN ONE TASK, a couple of frames into the race, so it
    # cannot land between them. With real clicks it did on CI: the waiting Play
    # started at the landing and the second press paused real playback, which
    # proves nothing about taking a waiting Play back. Each check also asks
    # that the race was still running after its presses. Real input reaches
    # the same handlers, and the first check's tap on the bar is a real one.
    IN2 = "await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));"
    PTR = """(el, type, x, y, id) => el.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true,
        isPrimary: true, pointerId: id, button: 0, clientX: x, clientY: y }))"""
    # The Pad's canvas against a replay of exactly the points it stands on,
    # with the replay held still while it is read (scrubbing). As PAD_SAME,
    # the replay's own compositor is left as the seek left it.
    PAD_AT = """() => { scrubbing = true;
      const n = playIndex, w = canvas.width, h = canvas.height, a = ctx.getImageData(0, 0, w, h).data.slice();
      const layers = strokeLayersOn(); let comp = null, i = -1;
      clearAndRestore(() => { comp = layers ? makeStrokeCompositor(ctx, canvas) : null;
        i = replayTimelineToCanvas(playTimeline, 0, n ? playTimeline[n - 1].playT : -1, comp ? comp.dotFn : drawDot, comp ? comp.lineFn : drawLine);
        if (comp) comp.present(); });
      const b = ctx.getImageData(0, 0, w, h).data; let off = 0;
      for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) off++;
      return { off: off, idx: n, ref: i, to: playSeek.indexAt(lastTargetMs) }; }"""
    # A seek that lands exactly on point K: between its time and the next.
    PAD_TO = "(k) => (playTimeline[k - 1].playT + 0.5) / playTotal"

    # ---- the Pad, on a phone the owner's width ---------------------------------
    _fc = b.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=2)
    _pg = _fc.new_page()
    browsing.goto(_pg, BASE, "/skribl-pad")
    _pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad")
    _pg.evaluate("(n) => { const d = (" + LONG + """)(n);
        restoreAutosave({ version: 1, strokes: d.pts, strokeGroups: d.groups, background: { color: '#f6f2ea' } }); }""", FF_N)
    _pg.wait_for_timeout(500)
    _pg.click("#playBtn"); _pg.wait_for_timeout(400)
    _pg.evaluate(FF_WATCH)
    _bx = _pg.locator("#playScrub").bounding_box()
    _x = round(_bx["x"] + _bx["width"] * 0.8)
    _pg.mouse.click(_x, _bx["y"] + _bx["height"] / 2)      # a tap on the bar, as a person makes it
    _f = (_x - _bx["x"]) / _bx["width"]
    _now = _pg.evaluate("""() => ({ racing: seekRacing(), at: playIndex, to: playSeek.indexAt(lastTargetMs),
        f: lastTargetMs / playTotal, fill: parseFloat(playScrubFill.style.width) / 100, gap: playSeek.gap(),
        badge: durationBadge.hidden ? null : durationBadge.textContent, want: formatDuration(lastTargetMs) })""")
    check("[Pad, 120,000 points, phone at 2x] a first far jump races there: the bar and the clock say where it was pointed at once, while the drawing is still behind",
          _now["racing"] and _now["at"] < _now["to"] and abs(_now["f"] - _f) < 0.01 and abs(_now["fill"] - _now["f"]) < 1e-6
          and (_now["badge"] is None or _now["badge"] == _now["want"]), str(_now))
    _land = _pg.evaluate(FF_LANDED)
    check("[Pad] ...the page keeps moving while it does: frames are painted, and none is held up past 300 ms",
          not _land["racing"] and _land["frames"] >= 5 and max(_land["lt"] or [0]) < 300,
          f"{_land['frames']} frames in {_land['ms']} ms, long tasks {_land['lt']}")
    _pg.wait_for_timeout(300)
    _c = _pg.evaluate(PAD_AT)
    check("[Pad] ...it lands on exactly what a replay from the first point paints, every byte, and plays on from there",
          _c["off"] == 0 and _c["ref"] == _c["idx"] and _c["idx"] >= _now["to"], f"{_c}; landed at {_now['to']}")
    # SHORT ONES LAND AT ONCE. The race is for a long draw through a part with
    # no copy yet. Into new ground but short -- 6,000 points across into the
    # first stretch without a copy -- and back through parts with copies,
    # 9,000 points past the nearest one: both at once, and exact.
    _e = _pg.evaluate("""() => { const g = playSeek.gap(), n = playSeek.count(), held = playSeek.held(), T = playTimeline,
          to = (i) => (T[i - 1].playT + 0.5) / playTotal, have = held.map(c => Math.floor(c / g));
        let s = 1; while (s <= n && have.indexOf(s) >= 0) s++;
        const B = s * g;                                   // where the first stretch with no copy starts
        const out = { gap: g, held: held.length, B: B, ok: s <= n && B + 3000 < T.length };
        if (!out.ok) return out;
        editorSeek(to(B - 3000)); out.a = [seekRacing(), playIndex, B - 3000];
        editorSeek(to(B + 3000)); out.b = [seekRacing(), playIndex, B + 3000];
        const c = held[Math.floor(held.length / 2)], next = held.find(h => h > c) || T.length;
        const K = Math.min(c + 9000, next - 1, (Math.floor(c / g) + 1) * g - 1);
        editorSeek(to(K)); out.c = [seekRacing(), playIndex, K, K - c];
        return out; }""")
    _cs = _pg.evaluate(PAD_AT)
    check("[Pad] a short jump into new ground (6,000 points) and one back through parts it has copies of (over 8,000 past the nearest) both land at once, exactly",
          _e["ok"] and _e["gap"] > 9000 and not _e["a"][0] and _e["a"][1] == _e["a"][2] and not _e["b"][0] and _e["b"][1] == _e["b"][2]
          and not _e["c"][0] and _e["c"][1] == _e["c"][2] and _e["c"][3] > 8000 and _cs["off"] == 0,
          f"{_e}; picture {_cs}")
    # A FRESH PREVIEW (Play again: a new timeline and no copies) for the rest.
    # The newer seek comes two frames in, before the race has passed a stretch
    # and taken a copy: a seek that restores a copy repaints the canvas from it
    # and would hide a race that never said where it had got to.
    _pg.click("#playBtn"); _pg.wait_for_timeout(200)          # Stop
    _pg.click("#playBtn"); _pg.wait_for_timeout(300)          # Play
    _d = _pg.evaluate("""async () => { editorSeek(0.9); const from = playIndex;
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        const at = playIndex, held = playSeek.held().length; editorSeek(0.6); const again = seekRacing();
        await new Promise(res => { const t = () => seekRacing() ? requestAnimationFrame(t) : res(); t(); });
        return { from: from, at: at, held: held, again: again }; }""")
    _dc = _pg.evaluate(PAD_AT)
    check("[Pad] a newer seek mid-race takes over from where the canvas stands, and lands exactly too",
          _d["at"] > _d["from"] and _d["held"] == 0 and _d["again"] and _dc["off"] == 0 and _dc["ref"] == _dc["idx"]
          and _dc["idx"] >= _dc["to"], f"{_d}; {_dc}")
    # A third, for a pause and then Stop, twelve frames into a race to 97%
    # (short of the end, where a pause's clock is capped and could not show
    # running ahead), each in one task with the race seen running.
    _pg.click("#playBtn"); _pg.wait_for_timeout(200)          # Stop
    _pg.click("#playBtn"); _pg.wait_for_timeout(300)          # Play
    _p = _pg.evaluate("""async () => { editorSeek(0.97);
        for (let n = 0; n < 12; n++) await new Promise(r => requestAnimationFrame(r));
        const was = seekRacing(), want = playTotal * 0.97; pausePlayback();
        const r = { racing: was, off: lastTargetMs - want }; resumePlayback(); return r; }""")
    check("[Pad] the clock holds the place pointed while it races: a pause twelve frames in pauses there, not where the clock ran on to",
          _p["racing"] and 0 <= _p["off"] < 50, f"{_p} (ms past the place pointed)")
    _was = _pg.evaluate("() => { const was = seekRacing(); document.getElementById('playBtn').click(); return was; }")   # Stop, mid-race
    _pg.evaluate("() => new Promise(r => { let n = 8; const t = () => --n ? requestAnimationFrame(t) : r(); requestAnimationFrame(t); })")
    _st = _pg.evaluate("""() => { const w = canvas.width, h = canvas.height, a = ctx.getImageData(0, 0, w, h).data.slice();
        clearAndRestore(() => paintStrokesStatic(strokes)); const b = ctx.getImageData(0, 0, w, h).data; let off = 0;
        for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) off++; return { off: off, racing: seekRacing(), playing: playing }; }""")
    check("[Pad] Stop while it races: the finished drawing comes back, and nothing races on over it",
          _was and _st["off"] == 0 and not _st["racing"] and not _st["playing"], f"racing when stopped {_was}; {_st}")
    _fc.close()

    # ---- the shared player, on a 2x desk ---------------------------------------
    _fg = b.new_page()
    browsing.goto(_fg, BASE, "/")
    _gen = _fg.evaluate("(n) => (" + LONG + ")(n)", FF_N)
    _fg.close()
    _st2, _body2 = post({"version": 2, "schemaVersion": 2, "playbackMode": "replay", "fps": None,
                         "canvasSize": {"cssWidth": 816, "cssHeight": 612},
                         "frames": [{"strokes": _gen["pts"], "strokeGroups": _gen["groups"], "background": {"color": "#f6f2ea"}}],
                         "title": "a two-hour drawing"})
    _gen = None
    # The canvas against a replay from the first point to where the player
    # says it stands, on an offscreen canvas so the player is left as it is.
    PLAYER_AT = """async (f) => { const r = await window.__skriblPlayerSeek(f);
      const w = canvas.width, h = canvas.height, a = ctx.getImageData(0, 0, w, h).data;
      const off = document.createElement('canvas'); off.width = w; off.height = h;
      const comp = makeStrokeCompositor(off.getContext('2d'), off);
      replayTimelineToCanvas(buildPlaybackTimeline(), 0, r.ms, comp.dotFn, comp.lineFn); comp.present();
      const b = off.getContext('2d').getImageData(0, 0, w, h).data; let n = 0;
      for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) n++;
      return { off: n, ms: r.ms, idx: r.idx }; }"""
    BTN = "() => document.getElementById('playerPlayBtn').getAttribute('aria-label')"
    FILL = "() => parseFloat(document.getElementById('playerProgressFill').style.width) / 100"

    def _player():
        c = b.new_context(viewport={"width": 1280, "height": 820}, device_scale_factor=2)
        pg = c.new_page()
        browsing.goto(pg, BASE, f"/s/{_body2['id']}")
        pg.wait_for_function("() => typeof window.__skriblPlayerSeek === 'function'")
        pg.wait_for_timeout(600)
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(600)
        return c, pg

    if _st2 in (200, 201) and _body2.get("id"):
        _c1, _pg = _player()
        _pg.evaluate(FF_WATCH)
        _bx = _pg.locator("#playerProgress").bounding_box()
        _x = round(_bx["x"] + _bx["width"] * 0.8)
        _pg.mouse.click(_x, _bx["y"] + _bx["height"] / 2)   # a tap on the bar while it plays
        _f = (_x - _bx["x"]) / _bx["width"]
        _now = _pg.evaluate("""() => { const T = buildPlaybackTimeline(), tot = T[T.length - 1].playT,
            fill = parseFloat(document.getElementById('playerProgressFill').style.width) / 100;
            return { racing: seekRacing(), fill: fill, at: document.getElementById('playerAt').textContent,
                     want: SkriblReplayLine.clock(SkriblReplayLine.clockMap(T, strokes)(fill * tot)),
                     btn: document.getElementById('playerPlayBtn').getAttribute('aria-label') }; }""")
        check("[shared player, 120,000 points, desk at 2x] a first far jump races there: the bar and the clock say where it was pointed at once, and the button says Pause for the Play that waits",
              _now["racing"] and abs(_now["fill"] - _f) < 0.01 and _now["at"] == _now["want"] and _now["btn"] == "Pause", str(_now))
        _land = _pg.evaluate(FF_LANDED)
        check("[shared player] ...the page keeps moving while it does: frames are painted, and none is held up past 300 ms",
              not _land["racing"] and _land["frames"] >= 5 and max(_land["lt"] or [0]) < 300,
              f"{_land['frames']} frames in {_land['ms']} ms, long tasks {_land['lt']}")
        _a = _pg.evaluate(FILL)
        _pg.wait_for_timeout(300)
        _b2 = _pg.evaluate(FILL)
        _btn = _pg.evaluate(BTN)
        _pg.click("#playerPlayBtn")                           # pause
        _cc = _pg.evaluate(PLAYER_AT, _b2 + 0.01)
        check("[shared player] ...it plays on from where it landed, and the picture is exactly what a replay from the first point paints",
              _b2 > _a >= _now["fill"] - 1e-9 and _btn == "Pause" and _cc["off"] == 0,
              f"bar {_a} -> {_b2}, button {_btn!r}; {_cc}")
        _d = _pg.evaluate("""async () => { const p = window.__skriblPlayerSeek(1);
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const mid = seekRacing(); const q = window.__skriblPlayerSeek(0.93); const again = seekRacing();
            await q; return { mid: mid, again: again }; }""")
        _dc = _pg.evaluate(PLAYER_AT, 0.93)
        check("[shared player] a newer seek mid-race takes over from where the canvas stands, and lands exactly too",
              _d["mid"] and _d["again"] and _dc["off"] == 0, f"{_d}; {_dc}")
        _c1.close()

        # Play pressed mid-race waits for the landing, and a second press, or a
        # tap on the drawing, takes it back -- as either would pause playing.
        _c2, _pg = _player()
        _g = _pg.evaluate("""async () => { window.__skriblPlayerSeek(0.5); """ + IN2 + """
            const b = document.getElementById('playerPlayBtn'), was = seekRacing();
            b.click(); const q1 = b.getAttribute('aria-label'); b.click(); const q2 = b.getAttribute('aria-label');
            return [was, q1, q2, seekRacing()]; }""")
        _l = _pg.evaluate(FF_LANDED); _pg.wait_for_timeout(300)
        _g += [_l["racing"], _pg.evaluate(BTN), _pg.evaluate(FILL)]
        check("[shared player] Play pressed mid-race says Pause and waits; a second press takes it back, and the drawing stays where it was pointed",
              _g[:6] == [True, "Pause", "Play", True, False, "Play"] and abs(_g[6] - 0.5) < 1e-6, str(_g))
        _h = _pg.evaluate("""async () => { window.__skriblPlayerSeek(0.97); """ + IN2 + """
            const b = document.getElementById('playerPlayBtn'), cv = document.getElementById('canvas'), r = cv.getBoundingClientRect();
            const x = r.left + r.width / 2, y = r.top + r.height / 2, was = seekRacing();
            b.click(); const q1 = b.getAttribute('aria-label');
            (""" + PTR + """)(cv, 'pointerdown', x, y, 7); (""" + PTR + """)(cv, 'pointerup', x, y, 7);   // a tap on the drawing
            return [was, q1, b.getAttribute('aria-label'), seekRacing()]; }""")
        _pg.evaluate(FF_LANDED); _pg.wait_for_timeout(300)
        _h += [_pg.evaluate(BTN), _pg.evaluate(FILL)]
        check("[shared player] ...and so does a tap on the drawing",
              _h[:5] == [True, "Pause", "Play", True, "Play"] and abs(_h[5] - 0.97) < 1e-6, str(_h))
        _c2.close()

        # Restart mid-race, with a Play waiting, starts the drawing over: nothing
        # races on, and the Play that waited is spent -- a keyboard step after
        # it holds still, as a step while playing always has.
        _c3, _pg = _player()
        _r = _pg.evaluate("""async () => { window.__skriblPlayerSeek(0.9); """ + IN2 + """
            const was = seekRacing(); document.getElementById('playerPlayBtn').click();   // a Play that waits
            const q = document.getElementById('playerPlayBtn').getAttribute('aria-label');
            document.getElementById('playerRestartBtn').click(); return [was && q === 'Pause']; }""")
        _pg.wait_for_timeout(400)
        _r += [_pg.evaluate("() => seekRacing()"), _pg.evaluate(BTN), _pg.evaluate(FILL)]
        _pg.focus("#playerProgress")
        _pg.keyboard.press("ArrowRight")
        _pg.wait_for_timeout(300)
        _r.append(_pg.evaluate(BTN))
        _rc = _pg.evaluate(PLAYER_AT, _pg.evaluate(FILL) + 0.01)
        check("[shared player] Restart while it races, with a Play waiting, starts the drawing over; nothing races on over it, and the Play that waited is spent",
              _r[0] and not _r[1] and _r[2] == "Pause" and _r[3] < 0.05 and _r[4] == "Play" and _rc["off"] == 0, f"{_r}; {_rc}")
        # A drag to the very end while it plays stays on the finished drawing,
        # as it always did, though the drawing gets there after the finger lifts.
        _pg.click("#playerPlayBtn"); _pg.wait_for_timeout(300)   # playing again
        _bx = _pg.locator("#playerProgress").bounding_box()
        _pg.mouse.move(_bx["x"] + _bx["width"] * 0.9, _bx["y"] + _bx["height"] / 2)
        _pg.mouse.down()
        _pg.mouse.move(_bx["x"] + _bx["width"] + 40, _bx["y"] + _bx["height"] / 2, steps=4)
        _pg.mouse.up()
        _was = _pg.evaluate("() => seekRacing()")
        _pg.evaluate(FF_LANDED); _pg.wait_for_timeout(400)
        _j = [_was, _pg.evaluate(BTN), _pg.evaluate(FILL)]
        check("[shared player] a drag to the very end while it plays stays on the finished drawing, though the drawing gets there after the finger lifts",
              _j == [True, "Play", 1.0], str(_j))
        _c3.close()

        # A drag holds a Play that waits, as it holds playing: nothing starts
        # under the finger, and letting go plays.
        _c4, _pg = _player()
        HOLD = """(type) => { const bar = document.getElementById('playerProgress'), r = bar.getBoundingClientRect();
            (""" + PTR + """)(bar, type, r.left + r.width * 0.95, r.top + r.height / 2, 9); }"""
        _k = _pg.evaluate("""async () => { window.__skriblPlayerSeek(0.5); """ + IN2 + """
            const b = document.getElementById('playerPlayBtn'), was = seekRacing();
            b.click(); const q1 = b.getAttribute('aria-label');
            (""" + HOLD + """)('pointerdown');   // the finger goes down on the bar, and stays
            return [was, q1, b.getAttribute('aria-label'), seekRacing()]; }""")
        _pg.evaluate(FF_LANDED); _pg.wait_for_timeout(300)
        _h1 = [_pg.evaluate(BTN), _pg.evaluate(FILL)]
        _pg.wait_for_timeout(300)
        _h2 = _pg.evaluate(FILL)
        _pg.evaluate("() => (" + HOLD + ")('pointerup')"); _pg.wait_for_timeout(400)
        _k += [_h1[0], _h1[1] == _h2, _pg.evaluate(BTN), _pg.evaluate(FILL) > _h2]
        check("[shared player] a drag holds a Play that waits, as it holds playing: nothing starts under the finger, and letting go plays",
              _k == [True, "Pause", "Play", True, "Play", True, "Pause", True], f"{_k}; held at {_h1[1]}")
        _c4.close()
    else:
        check("[shared player, 120,000 points] the two-hour drawing posted", False, f"{_st2} {_body2}")

    # ---- THE PILL'S ENDS (the owner: "everywhere this strip is the padding on
    # right and left side is off - not enough"; the mock's B) -----------------
    # Each place's speed pill, at the widths it is used: an end speed's word is
    # at least the space between two speeds' words from the pill's edge (within
    # 1.5px), and never inside the inner half of the curve; and no speed runs
    # out of its pill. Read in the words' own boxes (a Range), so it is what
    # the eye sees that is measured, not the buttons. Tune's pill stays inside
    # its row; the lines' pills may reach past their line (on a 320px phone the
    # eight and their ends are 270px, the line 260) but never nearer the
    # screen's edge than 16px; the post's box keeps its pill inside its line.
    # Today's stylesheets failed every place: the Pad's line and the link page
    # 9px for 11, the post's box 8 for 10.5, the Pad's desk pill 17 for 26,
    # Tune's last speeds out of the pill at every phone width and past the
    # screen's edge at 375 and under. And the ends opened inside a line held
    # to its width ran "Fit" out of the pill at 320, which the row above found.
    print("\nTHE PILL'S ENDS")
    ENDS = r"""(sel) => { const pill = document.querySelector(sel); if (!pill || pill.hidden || !pill.getClientRects().length) return null;
      const pr = pill.getBoundingClientRect(), cs = getComputedStyle(pill), bs = [...pill.querySelectorAll('button')];
      const t = bs.map((b) => { const r = document.createRange(); r.selectNodeContents(b); return r.getBoundingClientRect(); });
      const gaps = t.slice(1).map((x, i) => x.left - t[i].right).sort((a, c) => a - c);
      let row = pill.parentElement; while (row && getComputedStyle(row).display === 'contents') row = row.parentElement;
      const rr = row.getBoundingClientRect(), first = bs[0].getBoundingClientRect(), last = bs[bs.length - 1].getBoundingClientRect();
      return { L: +(t[0].left - pr.left).toFixed(2), R: +(pr.right - t[t.length - 1].right).toFixed(2), between: +gaps[Math.floor(gaps.length / 2)].toFixed(2),
               radius: Math.min(parseFloat(cs.borderTopLeftRadius), pr.height / 2),
               spill: +Math.max(last.right - (pr.right - parseFloat(cs.borderRightWidth)), (pr.left + parseFloat(cs.borderLeftWidth)) - first.left).toFixed(2),
               out: +Math.max(pr.right - rr.right, rr.left - pr.left).toFixed(2), screen: +(Math.max(pr.right, last.right) - innerWidth).toFixed(2),
               edge: +Math.min(pr.left, innerWidth - pr.right).toFixed(2) }; }"""
    def ends_ok(m, fits="row"):
        if not m:
            return False, "no pill"
        need = max(m["between"] - 1.5, m["radius"] / 2)
        held = {"row": m["spill"] <= 0.5 and m["out"] <= 0.5 and m["screen"] <= 0.5,
                "screen": m["spill"] <= 0.5 and m["edge"] >= 15.5, None: True}[fits]
        ok = m["L"] >= need and m["R"] >= need and held
        return ok, (f"ends {m['L']}/{m['R']}, need {need:.1f} (between {m['between']}, half the curve {m['radius'] / 2}); "
                    f"spill {m['spill']} out {m['out']} screen {m['screen']} edge {m['edge']}")
    # IN MORE THAN ONE FACE. A word is centred in its speed's box, and where
    # the boxes are at least 44px wide (a desk's pill) or share the pill
    # (Tune), how far the end word sits from the edge, and two words from each
    # other, follows how wide the words are in the face the page is drawn in:
    # "¼×" is wider beside "2×" in Liberation Sans (CI's face) than in Inter
    # (this box's), and at 1280 the first build's ends were half a pixel to a
    # pixel short there, red on main after #655 and green here. So each pill
    # is read in the page's own face and in Inter, Liberation Sans and
    # FreeSans where they are installed (SF's, Arial's and Helvetica's widths,
    # near the owner's iPhone and Segoe UI), and passes only in all of them,
    # three at least. Not DejaVu Sans: wider than any face the app is drawn in
    # where it is used, it runs Fit 3px out of a 320px phone's line, which no
    # device of ours shows.
    FACES = ["Inter", "Liberation Sans", "FreeSans"]
    HAVE = """(faces) => faces.filter((f) => { const x = document.createElement('canvas').getContext('2d'), t = '\u00bc\u00d7 \u00bd\u00d7 16\u00d7 Fit';
      x.font = '40px monospace'; const a = x.measureText(t).width; x.font = '40px "' + f + '", monospace'; return Math.abs(x.measureText(t).width - a) > 0.5; })"""
    FORCE = """([sel, f]) => { let s = document.getElementById('endsFace');
      if (!s) { s = document.createElement('style'); s.id = 'endsFace'; document.head.appendChild(s); }
      s.textContent = f ? sel + ', ' + sel + ' * { font-family: "' + f + '", sans-serif !important; }' : ''; }"""

    def ends_faces(pg, sel, fits="row"):
        faces = [None] + pg.evaluate(HAVE, FACES)
        good, said = True, []
        for f in faces:
            pg.evaluate(FORCE, [sel, f]); pg.wait_for_timeout(120)
            ok, why = ends_ok(pg.evaluate(ENDS, sel), fits)
            good = good and ok
            said.append(f"{f or 'its own face'}: " + ("ok" if ok else why))
        pg.evaluate(FORCE, [sel, None])
        return good and len(faces) >= 3, f"{len(faces)} faces; " + "; ".join(said)
    for vw, sel, where, fits in ((320, "#padLine", "the Pad's line while it plays", "screen"),
                                 (402, "#padLine", "the Pad's line while it plays", "screen"),
                                 (1280, "#padSpeed", "the Pad's speed pill on a desk", None)):
        pg = b.new_page(viewport={"width": vw, "height": 874})
        browsing.goto(pg, BASE, "/")
        box = pg.locator("#canvas").bounding_box()
        for k in range(2):
            pg.mouse.move(box["x"] + 80, box["y"] + 140 + k * 100); pg.mouse.down()
            for i in range(30):
                pg.mouse.move(box["x"] + 80 + i * 6, box["y"] + 140 + k * 100 + math.sin(i / 5) * 20); pg.wait_for_timeout(12)
            pg.mouse.up(); pg.wait_for_timeout(200)
        pg.click("#recordBtn"); pg.wait_for_timeout(300); pg.click("#playBtn"); pg.wait_for_timeout(400)
        pg.evaluate("(s) => document.querySelector(s + ' .rl-speed').click()", sel); pg.wait_for_timeout(400)
        ok, said = ends_faces(pg, sel + " .rl-chips", fits)
        check(f"[{vw}] {where}: its end speeds as far from the pill's edge as two speeds are apart, in each face", ok, said)
        pg.close()
    for vw in (320, 360, 375, 402, 430, 1280):
        pg = b.new_page(viewport={"width": vw, "height": 860})
        browsing.goto(pg, BASE, "/")
        pg.click("#tuneBtn"); pg.wait_for_timeout(600)
        pg.evaluate("() => document.querySelector('#tuneSpeed .rl-speed').click()"); pg.wait_for_timeout(400)
        ok, said = ends_faces(pg, "#tuneSpeed .rl-chips")
        check(f"[{vw}] Tune's speeds: all eight inside the pill and its row, the ends as far from the edge as two speeds are apart, in each face", ok, said)
        pg.close()
    _st3, _pe = post(drawing(0, "real", extra={"visibility": "public"}))   # public: the feed shows it
    if _st3 == 201:
        for vw in (320, 402, 1280):
            pg = b.new_page(viewport={"width": vw, "height": 874})
            pg.goto(BASE + _pe["url"], wait_until="load")
            pg.wait_for_function("() => !!document.querySelector('#playerLine .rl-speed')", timeout=10000)
            pg.evaluate("() => document.querySelector('#playerLine .rl-speed').click()"); pg.wait_for_timeout(400)
            ok, said = ends_faces(pg, "#playerLine .rl-chips", "screen")
            check(f"[{vw}] the link page's speeds (player.css): the ends as far from the edge as two speeds are apart, in each face", ok, said)
            pg.close()
        # The post's box (inlineplayer.css, a copy of its own: it loads on a
        # host's page), its line at rest on the feed.
        _box = '[data-skribl-id="' + _pe["id"] + '"] + * '
        for vw in (402, 1280):
            pg = b.new_page(viewport={"width": vw, "height": 874})
            browsing.goto(pg, BASE, "/feed")
            pg.wait_for_function("(s) => !!document.querySelector(s + '.rl-speed')", arg=_box, timeout=10000)
            pg.evaluate("(s) => document.querySelector(s + '.rl-speed').click()", _box); pg.wait_for_timeout(400)
            ok, said = ends_faces(pg, _box + ".rl-chips")
            check(f"[{vw}] the post's box's speeds (inlineplayer.css): the ends as far from the edge as two speeds are apart, inside its line, in each face", ok, said)
            pg.close()
    else:
        check("[the pill's ends] the link page's drawing posted", False, f"{_st3} {_pe}")
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
