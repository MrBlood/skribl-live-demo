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
    slider's own value.
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
    pg.mouse.click(cv["x"] + cv["width"] / 2, cv["y"] + cv["height"] / 2)
    pg.wait_for_timeout(300)
    p2 = pg.evaluate(FILL)
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
        geo = pg.evaluate("""() => { const l = document.getElementById('padLine').getBoundingClientRect(),
            s = document.getElementById('playScrub').getBoundingClientRect();
            return { shown: !document.getElementById('padLine').hidden, lineTop: l.top, lineBottom: l.bottom,
                     scrubTop: s.top, scrubBottom: s.bottom, dl: Math.abs(l.left - s.left), dw: Math.abs(l.width - s.width),
                     text: document.querySelector('#padLine .rl-text').innerText.replace(/\\s+/g, ' ').trim() }; }""")
        where = (geo["lineTop"] >= geo["scrubBottom"]) if label == "desk" else (geo["lineBottom"] <= geo["scrubTop"])
        check(f"[{label}] Play shows the line, " + ("under the scrubber" if label == "desk" else "above the scrubber")
              + ", as wide as it, and it was hidden before",
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
        if label == "desk":
            check(f"[{label}] Stop takes the line away (a desk has no place for it at rest)",
                  was and pg.evaluate("() => !playing && document.getElementById('padLine').hidden"))
            # THE SPEED BESIDE PLAY (owner's D1): at rest, in the Play pill.
            # Tap boxes are the rect grown by the ::before that makes the tap
            # (owner: "make sure target areas follow the rules too").
            TAP = """(el) => { const r = el.getBoundingClientRect(), b = getComputedStyle(el, '::before');
                const n = v => parseFloat(v) || 0, has = b.content !== 'none' && b.position === 'absolute';
                return [Math.round(r.width - (has ? Math.min(0, n(b.left)) + Math.min(0, n(b.right)) : 0)),
                        Math.round(r.height - (has ? Math.min(0, n(b.top)) + Math.min(0, n(b.bottom)) : 0))]; }"""
            sp = pg.locator("#padSpeed .rl-speed")
            st = pg.evaluate("""() => { const b = document.querySelector('#padSpeed .rl-speed'), r = b.getBoundingClientRect();
                const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return { painted: !!e && b.contains(e), text: b.textContent, label: b.getAttribute('aria-label'),
                         inPill: !!b.closest('#playWrap') }; }""")
            check(f"[{label}] at rest the speed sits in the Play pill, painted, saying its speed and what it is",
                  st["painted"] and st["inPill"] and st["text"] == "¼×" and st["label"] == "Replay speed, ¼×", str(st))
            sp.click(); pg.wait_for_timeout(350)
            chips = pg.evaluate("""() => [...document.querySelectorAll('#padSpeed .rl-chips button')].map(b => {
                const r = b.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return { t: b.textContent, hit: e === b, inside: r.left >= 0 && r.right <= innerWidth }; })""")
            check(f"[{label}] ...tapping it opens every speed, each one on top and on screen",
                  len(chips) == 8 and all(c["hit"] and c["inside"] for c in chips), str(chips))
            taps = [pg.evaluate(TAP, sp.element_handle())] + [pg.evaluate(TAP, h) for h in pg.locator("#padSpeed .rl-chips button").element_handles()]
            check(f"[{label}] ...and the button and every speed are at least a 44px tap",
                  all(w >= 44 and h >= 44 for w, h in taps), str(taps))
            pg.click("#padSpeed .rl-chips button[data-r='2']"); pg.wait_for_timeout(250)
            check(f"[{label}] ...a pick is the Pad's speed, and the line under the drawing says the same",
                  pg.evaluate("""() => [localStorage.getItem('skribl_replay_rate'), document.querySelector('#padSpeed .rl-speed').textContent,
                      document.querySelector('#padLine .rl-speed').textContent, document.querySelector('#padSpeed .rl-chips').hidden]""")
                  == ["2", "2×", "2×", True])
        else:
            # STAYS AT REST (owner's iPhone, after v321: "The speed only stays up
            # for the length of the play time. You can't adjust it if you
            # accidentally put it on 16x or if it's a short drawing").
            rest = pg.evaluate("""() => ({ playing, line: !document.getElementById('padLine').hidden,
                scrub: !document.getElementById('playScrub').hidden,
                hit: (() => { const b = document.querySelector('#padLine .rl-speed').getBoundingClientRect();
                  const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return !!e && !!e.closest('#padLine'); })() })""")
            check(f"[{label}] after the replay the line stays, its speed button on top, while the scrubber goes",
                  was and not rest["playing"] and rest["line"] and rest["hit"] and not rest["scrub"], str(rest))
            pick(pg, "#padLine", "16")
            check(f"[{label}] ...and a speed can still be picked there, for the next Play",
                  pg.evaluate("() => [localStorage.getItem('skribl_replay_rate'), document.querySelector('#padLine .rl-text').innerText.replace(/\\s+/g, ' ').trim().endsWith('watching at 16×')]")
                  == ["16", True], pg.evaluate("() => document.querySelector('#padLine .rl-text').innerText"))
            check(f"[{label}] the Play pill has no speed of its own on a phone (the line is the speed here)",
                  pg.evaluate("() => getComputedStyle(document.getElementById('padSpeed')).display === 'none'"))
            pg.mouse.move(box["x"] + 80, box["y"] + 400); pg.mouse.down()
            pg.mouse.move(box["x"] + 140, box["y"] + 420); pg.mouse.up(); pg.wait_for_timeout(300)
            check(f"[{label}] ...and the next stroke takes it away",
                  pg.evaluate("() => document.getElementById('padLine').hidden"))
        check(f"[{label}] the music keeps up between half and double speed and is a bed outside them",
              pg.evaluate("() => [0.25, 0.5, 2, 4].map(r => { setReplayRate(r); return musicRate(); })") == [1, 0.5, 2, 1])
        check(f"[{label}] no page errors", not errs, "; ".join(errs[:2]))
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
        .map(b => b.textContent + (b.classList.contains('on') ? '*' : ''))""")
    check("the Post sheet asks where viewers start: Auto (chosen), As drawn, Fit, and the speed last previewed",
          seg == ["Auto*", "As drawn", "Fit", "8×"], str(seg))
    check("...and Auto is what a post carries untouched", pg.evaluate("() => serializeSkribl().playSpeed") == "auto")
    picked = []
    for v in ("8", "fit", "drawn", "auto"):
        pg.evaluate("(v) => { const b = document.querySelector('#postSpeedSeg button[data-speed=\"' + v + '\"]'); if (b) b.click(); }", v)
        picked.append(pg.evaluate("() => [serializeSkribl().playSpeed, document.getElementById('postSpeedHint').textContent]"))
    check("each choice is what the post carries, and the line under it says what it does",
          [x[0] for x in picked] == [8, "fit", "drawn", "auto"]
          and picked[0][1].startswith("At 8×") and picked[1][1].startswith("The whole drawing in about 30 seconds")
          and all(x[1].endswith("Anyone watching can change it.") for x in picked), str(picked))
    h = pg.evaluate("() => document.getElementById('postSpeedSeg').getBoundingClientRect().height")
    check("...and its buttons are a 44px tap", h >= 44, f"{h}px")
    pg.close()
    pg = b.new_page()
    browsing.goto(pg, BASE, "/flip")
    check("Flip's Post sheet has no such row: a Flip loops, it has no speed to start at",
          pg.evaluate("() => !document.getElementById('postSpeedSeg')"))
    pg.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
