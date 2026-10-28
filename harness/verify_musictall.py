#!/usr/bin/env python3
"""The taller box, the wave filling it zoomed in deep, and pinch to zoom (the
owner's picks in the whole-drawer mock, FUTURE.md 6s, step 6; "All yes").

  THE TALLER BOX. After Magnify's - and +, at the end of the name's line, the
  same card and cell, a box with arrows up and down: named for what it does,
  saying whether the box is tall, there once there is a song. One tap and the
  timeline is twice as tall, one more and it is back. It glides (the owner, of
  the mock's: it "shook and jerked"), read on every frame, up and back, on the
  owner's phone and a desk: only the way it is going, in whole pixels, never a
  leap; every frame painted at that frame's height, not the one before
  stretched to fit; Hear the loop where the thumb is, to a quarter of a pixel;
  there within 400ms; and the page stays where the grow left it, the drawer's
  end below the screen or not (lib/drawerdetent.js followGrowth does not take
  it on). Under Reduce Motion it is there at once. With the timeline up at the
  header, it grows without taking its top under the header: Hear moves down
  instead.

  ZOOMED IN DEEP, THE WAVE FILLS THE BOX. Where the wave itself shows, a quiet
  passage is drawn against the loudest in view and stands most of the box's
  height, read off the canvas's pixels; it glides there frame by frame, and is
  there at once under Reduce Motion; where the song is drawn as its loudness
  it is drawn against the song's loudest, as before, so loud and quiet still
  compare.

  PINCH TO ZOOM. Two fingers on the timeline (the owner's phone, real touch
  points): spread sideways, a rung of Magnify for each doubling of the
  distance between them, and pinched in, back; spread up and down, the box
  as tall as the fingers take it, three times at most; locked to whichever way
  they first move; a finger already sliding the loop stops where it is when
  the second lands. On a desk, Ctrl and the wheel zoom the timeline a rung a
  notch, a trackpad's pinch (small deltas, the same events) a rung as they
  add up, and the page is not zoomed; without Ctrl the wheel is the page's.

Every row runs on the Pad and on Flip: one timeline (lib/musictimeline.js) in
one drawer (lib/musicdrawer.js). Skribl's ears are off here.
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
    print("No assertions were executed. This is NOT evidence the timeline grows, fills or pinches.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICTALL_ONLY=Pad (or Flip) runs one editor, and
# MUSICTALL_PART=control (glide, still, ceiling, fill, pinch or wheel) one part.
# A real run sets neither.
ONLY = os.environ.get("MUSICTALL_ONLY", "")
PART = os.environ.get("MUSICTALL_PART", "")
EDITORS = [e for e in (("Pad", "/"), ("Flip", "/flip")) if not ONLY or e[0] == ONLY]


def eds(name):
    """The editors a part runs on: none, when calibration asks for another part."""
    return EDITORS if not PART or PART == name else []


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
FACES = (("phone", PHONE), ("desk", DESK))


def _wav(seconds, rate=8000, loud=None):
    """A pulse twice a second; with `loud` (from, to) seconds, a quiet tone
    (5% of full) everywhere but there, where it is at 90%."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    frames = []
    for i in range(int(seconds * rate)):
        t = i / rate
        if loud:
            a = 0.9 if loud[0] <= t < loud[1] else 0.05
            v = a * math.sin(2 * math.pi * 110 * t)
        else:
            v = 0.34 * math.sin(2 * math.pi * 220 * t) * math.exp(-((2 * t) % 1) * 7)
        frames.append(struct.pack("<h", int(32767 * v)))
    w.writeframes(b"".join(frames))
    w.close()
    return buf.getvalue()
TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
# Quiet but for a loud second near the loop's end, so at 1x both are in view.
HUSH = {"name": "hush.wav", "mimeType": "audio/wav", "buffer": _wav(12.0, loud=(7.0, 7.6))}
PAGES = """(o) => { frames.length = 0;
  for (let k = 0; k < o.n; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); if (o.hold > 1) f.hold = o.hold; frames.push(f); }
  fps = o.fps; idx = 0; buildStrip(); render(); updateToolState(); }"""
SET = "(o) => { musicTempo = o.tempo; if ('s' in o) { trimStart = o.s; trimEnd = o.e; } if ('xf' in o) { loopCrossfadeMs = o.xf; setCrossfadeUI(); } updateTrimUI(); }"
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"


def editor(b, name, path, *, song=TWELVE, opts=PHONE, ctx=None, scheme="light"):
    c = ctx or waits.instrument(b.new_context(color_scheme=scheme, **opts))
    c.add_init_script(NO_EARS)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if name == "Flip":
        pg.evaluate(PAGES, {"n": 3, "fps": 12, "hold": 8})
    browsing.pad_drawer(pg, "music")
    if song:
        secs = len(song["buffer"]) / 16000
        pg.set_input_files("#musicInput", song)
        pg.wait_for_function("(d) => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                             " && Math.abs(audioDuration - d) < 0.2", arg=secs, timeout=20000)
        waits.settle(pg, 500)
        browsing.wait_scroll_still(pg)
    return c, pg, errs


# Every frame from the tap until the box has held still a while: each reading
# taken first thing in the next frame, so the box's size, the canvas's pixels
# and where Hear is are what that frame showed.
REC = r"""() => new Promise(done => {
  const stage = document.getElementById('musicTlStage'), hear = document.getElementById('previewLoopBtn'), cv = document.getElementById('musicTlCanvas');
  const tl = document.getElementById('musicTimeline'), out = [], t0 = performance.now();
  const snap = () => { const s = stage.getBoundingClientRect();
    out.push({ t: Math.round(performance.now() - t0), h: +s.height.toFixed(3), hear: +hear.getBoundingClientRect().top.toFixed(3),
               top: +tl.getBoundingClientRect().top.toFixed(2), bmp: cv.height, want: Math.round(s.height * devicePixelRatio), y: scrollY }); };
  snap();
  let still = 0, n = 0;
  function loop() {
    snap(); n++;
    const a = out[out.length - 1], b = out[out.length - 2];
    still = a.h === b.h && a.bmp === a.want ? still + 1 : 0;
    if (still < 12 && n < 120) requestAnimationFrame(loop); else done(out);
  }
  requestAnimationFrame(loop);
  document.getElementById('musicTlTall').click();
})"""
TALL = """() => { const t = document.getElementById('musicTlTall'), s = document.getElementById('musicTlStage').getBoundingClientRect();
  return { h: +s.height.toFixed(2), pressed: t.getAttribute('aria-pressed'), disabled: t.disabled, name: t.getAttribute('aria-label') }; }"""


# A LOOK THIS LONG AFTER THE ONE BEFORE (ms, three frames) MEANS THE BOX HELD
# THE PAGE (verify_flipbeat's HELD): the glide's clock went on, so the frame
# after it shows two or three frames' worth in one, as it should. Beside the
# calibration's other runs one step back went 60px after 21 on a desk.
HELD = 50


def glide(rows, h0, h1):
    """What the frames say: (the way it goes and never leaps, whole pixels,
    painted at its height, Hear's drift, when it got there). One step at most
    that came after a look HELD late is set aside from the leaps, and named."""
    hs = [r["h"] for r in rows]
    way = 1 if h1 > h0 else -1
    steps = [way * (b2 - a2) for a2, b2 in zip(hs, hs[1:])]
    gaps = [b2["t"] - a2["t"] for a2, b2 in zip(rows, rows[1:])]
    back = [round(s, 2) for s in steps if s < -0.01]
    leaps = [(i, s, steps[i - 1]) for i, s in enumerate(steps) if i and steps[i - 1] > 0 and s > 2 * steps[i - 1] + 2]
    held = [lp for lp in leaps if gaps[lp[0]] >= HELD or gaps[lp[0] - 1] >= HELD][:1]
    leaps = [lp for lp in leaps if lp not in held]
    first = next((s for s in steps if abs(s) > 0.01), 0)
    frac = [h for h in hs if abs(h - round(h)) > 0.01]
    stretched = [(r["t"], r["bmp"], r["want"]) for r in rows if abs(r["bmp"] - r["want"]) > 1]
    drift = max(abs(r["hear"] - rows[0]["hear"]) for r in rows)
    end = next((r["t"] for r in rows if abs(r["h"] - h1) < 0.5), None)
    return {"way": not back and not leaps and first > 0, "back": back, "leaps": leaps[:3], "frac": frac[:4],
            "aside": [(round(s, 1), max(gaps[i], gaps[i - 1])) for i, s, _ in held],
            "stretched": stretched[:4], "drift": drift, "end": end, "last": hs[-1],
            "steps": [round(s, 1) for s in steps if abs(s) > 0.01][:14]}


# The song's ink as painted, read off the canvas: per device column (every
# second one) the farthest ink from the middle line, in CSS px, the line's own
# rows and the loop's two edge lines left out.
INK = """(o) => {
  const tl = document.getElementById('musicTimeline'), cv = document.getElementById('musicTlCanvas'), P = tl._painted || {};
  const w = cv.clientWidth, hh = cv.clientHeight, dpr = cv.width / w, W = cv.width;
  const img = cv.getContext('2d').getImageData(0, 0, W, cv.height).data;
  const at = (c, r) => { const i = (r * W + c) * 4; return [img[i], img[i + 1], img[i + 2]]; };
  const far = (a, b) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]);
  const sTop = 26 + 8, sH = hh - sTop, mid = sTop + sH / 2 + 3, room = sH / 2 - 10;
  const r0 = Math.ceil((sTop + 3) * dpr), r1 = Math.floor((hh - 3) * dpr), m0 = Math.floor((mid - 1.5) * dpr), m1 = Math.ceil((mid + 1.5) * dpr);
  const edges = (P.edges || []).map((e) => e[0] * dpr);
  const v = (tl.dataset.view || '0 1').split(' ').map(Number), X = (t) => (t - v[0]) / v[1] * w * dpr;
  const cols = [];
  for (let c = Math.ceil(12 * dpr); c < W - 12 * dpr; c += 2) {
    if (edges.some((e) => Math.abs(c - e) < 5 * dpr)) continue;
    if (o && o.from != null && (c < X(o.from) || c > X(o.to))) continue;
    const g = at(c, r0); let reach = 0;
    for (let r = r0 + 1; r <= r1; r++) {
      if (r >= m0 && r <= m1) continue;
      if (far(at(c, r), g) > 60) reach = Math.max(reach, Math.abs(r / dpr - mid));
    }
    cols.push(reach);
  }
  cols.sort((a, b) => a - b);
  return { song: P.song || null, room, n: cols.length, most: cols.length ? cols[cols.length - 1] : 0,
           high: cols.length ? cols[Math.floor(cols.length * 0.95)] : 0, mag: document.getElementById('musicTlMag').textContent }; }"""
# The same, on every frame for a while after a press, the farthest ink only.
INK_REC = """(o) => new Promise(done => {
  const read = new Function('o', 'return (' + o.ink + ')(o)'), out = [], t0 = performance.now();
  function loop() { const k = read(null); out.push([Math.round(performance.now() - t0), +k.high.toFixed(2), k.song]);
    if (performance.now() - t0 < o.ms) requestAnimationFrame(loop); else done(out); }
  requestAnimationFrame(loop);
  document.querySelector(o.press).click();
})"""


def into_view(pg, sel, block="center"):
    pg.evaluate("(o) => document.querySelector(o.s).scrollIntoView({ block: o.b })", {"s": sel, "b": block})
    pg.wait_for_timeout(250)
    browsing.wait_scroll_still(pg)


with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("\nMUSIC TALL — the control")
    # Its place, its words and its glyph's ink, against what is behind it, on
    # the owner's phone and a desk, light and dark.
    PLACE = """() => { const q = (s) => document.querySelector(s), r = (s) => q(s).getBoundingClientRect();
      const parse = (s) => { const m = s.match(/^rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
      const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a }; };
      const ground = (el) => { const l = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { l.push(c); if (c.a >= 0.999) break; } }
        let acc = { r: 255, g: 255, b: 255, a: 1 }; for (let i = l.length - 1; i >= 0; i--) acc = over(l[i], acc); return acc; };
      const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
      const ratio = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
      const t = q('#musicTlTall'), g = ground(t), ink = ratio(over(parse(getComputedStyle(t).color), g), g);
      const m = r('.mt-tl-mag'), k = r('.mt-tl-tallbox'), n = r('#musicTlName'), st = r('#musicTlStage'), b = t.getBoundingClientRect();
      const cm = getComputedStyle(q('.mt-tl-mag')), ck = getComputedStyle(q('.mt-tl-tallbox'));
      // Where a finger lands on it: the middle and 21px out each way.
      const cx = (b.left + b.right) / 2, cy = (b.top + b.bottom) / 2;
      const hit = [[0, 0], [-21, 0], [21, 0], [0, -21], [0, 21]].every(([dx, dy]) => { const e = document.elementFromPoint(cx + dx, cy + dy); return e === t || t.contains(e); });
      return { right: k.right - st.right, after: k.left - m.right, middle: (k.top + k.bottom) / 2 - (m.top + m.bottom) / 2, nameMid: (k.top + k.bottom) / 2 - (n.top + n.bottom) / 2,
               same: cm.backgroundColor === ck.backgroundColor && cm.borderTopColor === ck.borderTopColor && cm.borderRadius === ck.borderRadius && Math.abs(b.width - q('#musicTlIn').getBoundingClientRect().width) < 0.5,
               hit, ink: +ink.toFixed(2), glyph: !!t.querySelector('svg rect') && t.querySelectorAll('svg path').length === 1 }; }"""
    for _n, _p in eds("control"):
        # Without a song: there, and not pressable.
        c, pg, errs = editor(b, _n, _p, song=None)
        before = pg.evaluate(TALL)
        c.close()
        placed, inks = [], []
        for face, opts in FACES:
            for scheme in ("light", "dark"):
                c, pg, errs = editor(b, _n, _p, opts=opts, scheme=scheme)
                into_view(pg, "#musicTimeline")
                off = pg.evaluate(PLACE)
                pg.click("#musicTlTall"); pg.wait_for_timeout(600)
                on = pg.evaluate(PLACE)
                placed.append((face, scheme, off))
                inks.append((face, scheme, off["ink"], on["ink"]))
                if face == "phone" and scheme == "light":
                    s1 = pg.evaluate(TALL)
                    pg.click("#musicTlTall"); pg.wait_for_timeout(600)
                    s2 = pg.evaluate(TALL)
                c.close()
        check(f"{_n}: the taller box sits after Magnify's - and +, at the end of the name's line, its middle on theirs, the same card and cell, a finger wide",
              all(abs(p["right"]) <= 0.5 and p["after"] >= 4 and abs(p["middle"]) <= 0.5 and abs(p["nameMid"]) <= 1 and p["same"] and p["hit"] and p["glyph"]
                  for _, _, p in placed),
              "; ".join(f"{f} {s}: right {p['right']:+.2f}, {p['after']:.1f}px after -/+, middle {p['middle']:+.2f} (name {p['nameMid']:+.2f}),"
                        f" same card {p['same']}, a finger wide {p['hit']}, its glyph {p['glyph']}" for f, s, p in placed))
        check(f"{_n}: it is named for what it does and says whether the box is tall, and is there to press once there is a song",
              before["disabled"] and before["name"] == "Make the box taller" and before["pressed"] == "false"
              and s1["pressed"] == "true" and abs(s1["h"] - 236) < 0.5 and s2["pressed"] == "false" and abs(s2["h"] - 118) < 0.5,
              f"no song: {before}; one tap: {s1}; two: {s2}")
        check(f"{_n}: its glyph reads 3:1 and up against what is behind it, off and on, light and dark, phone and desk",
              all(a >= 3 and o >= 3 for _, _, a, o in inks), "; ".join(f"{f} {s}: off {a}:1, on {o}:1" for f, s, a, o in inks))
        check(f"{_n}: no page errors with the taller box", not errs, "; ".join(errs[:2]))

    print("\nMUSIC TALL — it glides")
    for _n, _p in eds("glide"):
        for face, opts in FACES:
            c, pg, errs = editor(b, _n, _p, opts=opts)
            into_view(pg, "#musicTimeline")
            up = pg.evaluate(REC); pg.wait_for_timeout(1500)
            y_up = (up[-1]["y"], pg.evaluate("() => scrollY"))
            down = pg.evaluate(REC); pg.wait_for_timeout(300)
            gu, gd = glide(up, 118, 236), glide(down, 236, 118)
            check(f"{_n} ({face}): one tap and the box glides to twice as tall, and one more back, each within 400ms",
                  gu["end"] is not None and gu["end"] <= 400 and gd["end"] is not None and gd["end"] <= 400
                  and abs(gu["last"] - 236) < 0.5 and abs(gd["last"] - 118) < 0.5,
                  f"up: there at {gu['end']}ms, {gu['last']}px; back: at {gd['end']}ms, {gd['last']}px")
            check(f"{_n} ({face}): ...only the way it is going, in whole pixels, never a leap",
                  gu["way"] and gd["way"] and not gu["frac"] and not gd["frac"],
                  f"up: steps {gu['steps']}, against the way {gu['back']}, leaps {gu['leaps']}, between pixels {gu['frac']}"
                  + (f", set aside as the box held the page (px, ms) {gu['aside']}" if gu["aside"] else "")
                  + f"; back: steps {gd['steps']}, against {gd['back']}, leaps {gd['leaps']}, between {gd['frac']}"
                  + (f", set aside {gd['aside']}" if gd["aside"] else ""))
            check(f"{_n} ({face}): ...every frame painted at that frame's height, not the one before stretched to fit",
                  not gu["stretched"] and not gd["stretched"], f"up {gu['stretched']}; back {gd['stretched']} (when, the canvas's rows, the box's)")
            check(f"{_n} ({face}): ...Hear the loop staying where the thumb is, to a quarter of a pixel",
                  gu["drift"] <= 0.25 and gd["drift"] <= 0.25, f"up {gu['drift']:.2f}px, back {gd['drift']:.2f}px at most")
            check(f"{_n} ({face}): ...and the page staying where the grow left it",
                  y_up[0] == y_up[1], f"scrolled to {y_up[0]} as it got there, {y_up[1]} a second and a half on")
            check(f"{_n} ({face}): no page errors as the box glides", not errs, "; ".join(errs[:2]))
            c.close()
        # The Restart door open, which takes the drawer's end well below the
        # screen, and the page where the bar shows under the header: a song
        # landing there is followed down (lib/drawerdetent.js followGrowth),
        # the grow is not.
        c, pg, errs = editor(b, _n, _p)
        pg.click('#musicDoors .dp-tile[data-dp="restart"]'); pg.wait_for_timeout(600)
        browsing.wait_scroll_still(pg)
        pg.evaluate("""() => { const bar = document.getElementById('toolBar') || document.querySelector('.flip-tools');
          scrollBy(0, bar.getBoundingClientRect().top - window.SkriblDrawerDetent.stuckBottom() - 120); }""")
        pg.wait_for_timeout(400)
        low = pg.evaluate("""() => [document.getElementById('mediaCard').getBoundingClientRect().bottom - innerHeight,
          (document.getElementById('toolBar') || document.querySelector('.flip-tools')).getBoundingClientRect().top - window.SkriblDrawerDetent.stuckBottom()]""")
        up = pg.evaluate(REC); pg.wait_for_timeout(1500)
        gu = glide(up, 118, 236)
        late = pg.evaluate("() => [scrollY, document.getElementById('previewLoopBtn').getBoundingClientRect().top]")
        check(f"{_n}: with the drawer's end below the screen, the grow is not followed down: the page stays, Hear where it was",
              low[0] > 20 and low[1] > 20 and gu["end"] is not None and up[-1]["y"] == late[0] and abs(late[1] - up[0]["hear"]) <= 0.25,
              f"the drawer's end {low[0]:.0f}px below the screen, the bar {low[1]:.0f}px under the header; scrolled to {up[-1]['y']} as it got there,"
              f" {late[0]} 1.5s on; Hear {up[0]['hear']} -> {late[1]:.2f}")
        c.close()

    print("\nMUSIC TALL — under Reduce Motion")
    for _n, _p in eds("still"):
        ctx = waits.instrument(b.new_context(reduced_motion="reduce", color_scheme="light", **PHONE))
        c, pg, errs = editor(b, _n, _p, ctx=ctx)
        into_view(pg, "#musicTimeline")
        up = pg.evaluate(REC)
        hs = [r["h"] for r in up]
        moved = [round(b2 - a2, 1) for a2, b2 in zip(hs, hs[1:]) if abs(b2 - a2) > 0.01]
        gu = glide(up, 118, 236)
        check(f"{_n}: under Reduce Motion the box is twice as tall at once, painted so, Hear the loop where it was",
              moved == [118.0] and not gu["stretched"] and gu["drift"] <= 0.25,
              f"its steps {moved}; stretched {gu['stretched']}; Hear moved {gu['drift']:.2f}px")
        check(f"{_n}: no page errors under Reduce Motion", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC TALL — the timeline up at the header")
    for _n, _p in eds("ceiling"):
        c, pg, errs = editor(b, _n, _p)
        # The Restart door open, so the page goes on far enough, and the
        # timeline's top 20px under the header's foot.
        pg.click('#musicDoors .dp-tile[data-dp="restart"]'); pg.wait_for_timeout(600)
        browsing.wait_scroll_still(pg)
        pg.evaluate("""() => { const f = window.SkriblDrawerDetent.stuckBottom(), t = document.getElementById('musicTimeline').getBoundingClientRect().top;
          scrollBy(0, t - f - 20); }""")
        pg.wait_for_timeout(400)
        up = pg.evaluate(REC); pg.wait_for_timeout(400)
        foot = pg.evaluate("() => window.SkriblDrawerDetent.stuckBottom()")
        tops = [r["top"] for r in up]
        check(f"{_n}: with the timeline up at the header, the box grows without taking its top under it: Hear moves down instead",
              abs(tops[0] - (foot + 20)) <= 2 and abs(up[-1]["h"] - 236) < 0.5 and min(tops) >= foot + 4 - 0.5 and up[-1]["hear"] > up[0]["hear"] + 50,
              f"the header ends at {foot}; the timeline's top from {tops[0]} to {min(tops)} at its highest; Hear {up[0]['hear']} -> {up[-1]['hear']}; the box {up[-1]['h']}px")
        check(f"{_n}: no page errors with the timeline up at the header", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC TALL — zoomed in deep, the wave fills the box")
    for _n, _p in eds("fill"):
        for still in (False, True):
            ctx = waits.instrument(b.new_context(reduced_motion="reduce" if still else "no-preference", color_scheme="light", **PHONE))
            c, pg, errs = editor(b, _n, _p, song=HUSH, ctx=ctx)
            pg.evaluate(SET, {"tempo": None, "s": 3.0, "e": 7.5, "xf": 0})
            into_view(pg, "#musicTimeline")
            pg.wait_for_timeout(500)
            wide = pg.evaluate(INK, {"from": 3.2, "to": 6.8})
            loud = pg.evaluate(INK, {"from": 7.05, "to": 7.45})
            # In around the start, the quiet passage alone in view, to the last
            # rung the song is its loudness; then the next, read on every frame.
            for _ in range(9):
                pg.click("#musicTlIn"); pg.wait_for_timeout(250)
                if pg.evaluate(INK)["song"] != "loudness":
                    pg.click("#musicTlOut"); pg.wait_for_timeout(400)
                    break
            pg.wait_for_timeout(500)
            near = pg.evaluate(INK)
            if not still:
                check(f"{_n}: where the song is drawn as its loudness it is against the song's loudest, as before: a quiet passage a few pixels, a loud one most of the box",
                      wide["song"] == near["song"] == "loudness" and wide["n"] > 50 and near["n"] > 50 and wide["high"] <= 4 and near["high"] <= 4
                      and loud["high"] >= 0.7 * loud["room"],
                      f"at {wide['mag']}: the quiet passage {wide['high']:.1f}px from the middle over {wide['n']} columns, the loud {loud['high']:.1f} of {loud['room']:.0f}px;"
                      f" at {near['mag']}, the quiet passage alone in view, {near['song']}: {near['high']:.1f}px")
            rec = pg.evaluate(INK_REC, {"ink": INK, "press": "#musicTlIn", "ms": 700})
            pg.wait_for_timeout(300)
            deep = pg.evaluate(INK)
            highs = [h for _, h, s in rec if s in ("wave", "samples")]
            if not still:
                check(f"{_n}: zoomed in deep, the quiet passage fills the box: its wave stands most of the box's height, read off its pixels",
                      deep["song"] in ("wave", "samples") and deep["n"] > 50 and deep["high"] >= 0.8 * deep["room"],
                      f"at {deep['mag']}, {deep['song']}: {deep['high']:.1f}px from the middle over {deep['n']} columns, of {deep['room']:.0f}")
                rising = [h2 - h1 for h1, h2 in zip(highs, highs[1:])]
                check(f"{_n}: ...gliding there frame by frame, never a leap to it",
                      len(highs) >= 5 and highs[-1] >= 0.8 * deep["room"] and highs[0] <= 0.6 * deep["room"]
                      and sum(1 for d in rising if d > 0.25) >= 3 and all(d >= -0.75 for d in rising),
                      f"{len(highs)} frames of the wave, its height {[round(h, 1) for h in highs[:14]]}")
            else:
                check(f"{_n}: under Reduce Motion the quiet passage fills the box at once",
                      deep["high"] >= 0.8 * deep["room"] and highs and highs[0] >= 0.8 * deep["room"],
                      f"its height on the first frames {[round(h, 1) for h in highs[:6]]}, then {deep['high']:.1f} of {deep['room']:.0f}")
            check(f"{_n}: no page errors as the wave fills the box{' under Reduce Motion' if still else ''}", not errs, "; ".join(errs[:2]))
            c.close()

    print("\nMUSIC TALL — pinch to zoom")
    # Two real touch points on the timeline's song, through the browser's own
    # touch input: both down, moved together, then up.
    def fingers(pg):
        return pg.evaluate("""() => { const s = document.getElementById('musicTlStage').getBoundingClientRect();
          return { cx: s.left + s.width / 2, cy: s.top + 34 + (s.height - 34) / 2, w: s.width }; }""")

    def touch(cdp, kind, pts):
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i + 1} for i, (x, y) in enumerate(pts)]})

    def pinch(pg, cdp, at, a, z, steps=10, hold=True):
        """Two fingers about the stage's middle, `a` = (dx, dy) apart, moved to
        `z` = (dx, dy) apart (or a list of them, in turn)."""
        cx, cy = at["cx"], at["cy"]
        pts = lambda d: [(cx - d[0] / 2, cy - d[1] / 2), (cx + d[0] / 2, cy + d[1] / 2)]   # noqa: E731
        touch(cdp, "touchStart", pts(a)[:1]); touch(cdp, "touchStart", pts(a))
        legs, now = (z if isinstance(z, list) else [z]), a
        for goal in legs:
            for k in range(1, steps + 1):
                f = k / steps
                touch(cdp, "touchMove", pts((now[0] + (goal[0] - now[0]) * f, now[1] + (goal[1] - now[1]) * f)))
                pg.wait_for_timeout(16)
            now = goal
        touch(cdp, "touchEnd", [])
        pg.wait_for_timeout(450)

    MAGTALL = "() => [document.getElementById('musicTlMag').textContent, +document.getElementById('musicTlStage').getBoundingClientRect().height.toFixed(2)]"
    for _n, _p in eds("pinch"):
        c, pg, errs = editor(b, _n, _p)
        into_view(pg, "#musicTimeline")
        cdp = c.new_cdp_session(pg)
        at = fingers(pg)
        pinch(pg, cdp, at, (60, 0), (120, 0)); x2 = pg.evaluate(MAGTALL)
        pinch(pg, cdp, at, (40, 0), (160, 0)); x8 = pg.evaluate(MAGTALL)
        pinch(pg, cdp, at, (160, 0), (40, 0)); x2b = pg.evaluate(MAGTALL)
        check(f"{_n}: two fingers spread sideways zoom in a rung for each doubling of the distance between them, and pinched in, back",
              x2[0] == "2×" and x8[0] == "8×" and x2b[0] == "2×" and x2[1] == x8[1] == 118,
              f"60 to 120px apart: {x2}; then 40 to 160: {x8}; then 160 to 40: {x2b}")
        at = fingers(pg)
        pinch(pg, cdp, at, (0, 30), (0, 60)); y2 = pg.evaluate(MAGTALL)
        pinch(pg, cdp, at, (0, 30), (0, 150)); y3 = pg.evaluate(MAGTALL)
        pressed = pg.evaluate("() => document.getElementById('musicTlTall').getAttribute('aria-pressed')")
        check(f"{_n}: ...spread up and down, the box as tall as the fingers take it, three times at most, the button saying it is tall",
              abs(y2[1] - 236) <= 1 and abs(y3[1] - 354) <= 0.5 and y2[0] == y3[0] == "2×" and pressed == "true",
              f"30 to 60px apart: {y2}; then 30 to 150 from there: {y3}; the button pressed {pressed}")
        pg.click("#musicTlTall"); pg.wait_for_timeout(500)
        at = fingers(pg)
        pinch(pg, cdp, at, (60, 30), [(90, 30), (90, 90)]); lk = pg.evaluate(MAGTALL)
        check(f"{_n}: ...locked to whichever way the fingers first move: sideways first, then up and down, only zooms",
              lk[0] == "4×" and abs(lk[1] - 118) < 0.5, f"from 2x and 118px: {lk}")
        # A finger sliding the loop when the second lands stops where it is.
        at = fingers(pg)
        cx, cy = at["cx"], at["cy"]
        touch(cdp, "touchStart", [(cx - 50, cy)])
        for k in range(1, 7):
            touch(cdp, "touchMove", [(cx - 50 + 5 * k, cy)]); pg.wait_for_timeout(16)
        s1 = pg.evaluate("() => trimStart")
        touch(cdp, "touchStart", [(cx - 20, cy), (cx + 40, cy)])
        for k in range(1, 11):
            touch(cdp, "touchMove", [(cx - 20 - 3 * k, cy), (cx + 40 + 3 * k, cy)]); pg.wait_for_timeout(16)
        s2, m2 = pg.evaluate("() => trimStart"), pg.evaluate(MAGTALL)
        touch(cdp, "touchEnd", []); pg.wait_for_timeout(450)
        check(f"{_n}: ...and a finger already sliding the loop stops where it is when the second lands",
              abs(s2 - s1) < 1e-9 and m2[0] == "8×", f"the loop's start {s1:.4f} as the second finger landed, {s2:.4f} through the pinch; {m2}")
        check(f"{_n}: no page errors with two fingers", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC TALL — Ctrl and the wheel on a desk")
    WHEEL = """(o) => { const s = document.getElementById('musicTlStage').getBoundingClientRect(), out = [];
      const probe = (e) => out.push(e.defaultPrevented);
      window.addEventListener('wheel', probe);
      for (let k = 0; k < o.n; k++) document.getElementById('musicTlStage').dispatchEvent(new WheelEvent('wheel',
        { bubbles: true, cancelable: true, ctrlKey: o.ctrl, deltaY: o.dy, deltaMode: 0, clientX: s.left + s.width / 2, clientY: s.top + s.height / 2 }));
      window.removeEventListener('wheel', probe);
      return out; }"""
    for _n, _p in eds("wheel"):
        c, pg, errs = editor(b, _n, _p, opts=DESK)
        into_view(pg, "#musicTimeline")
        st = pg.evaluate("() => { const s = document.getElementById('musicTlStage').getBoundingClientRect(); return { x: s.left + s.width / 2, y: s.top + 70 }; }")
        pg.mouse.move(st["x"], st["y"])
        pg.keyboard.down("Control"); pg.mouse.wheel(0, -100); pg.wait_for_timeout(250); pg.keyboard.up("Control")
        notch = pg.evaluate(MAGTALL)
        kept = pg.evaluate(WHEEL, {"n": 1, "ctrl": True, "dy": -100})
        pg.wait_for_timeout(250)
        notch2 = pg.evaluate(MAGTALL)
        check(f"{_n}: on a desk Ctrl and the wheel zoom the timeline a rung a notch, and the page is not zoomed",
              notch[0] == "2×" and notch2[0] == "4×" and kept == [True], f"a notch: {notch}; another: {notch2}; the page's own zoom called off {kept}")
        small = pg.evaluate(WHEEL, {"n": 8, "ctrl": True, "dy": -5})
        pg.wait_for_timeout(250)
        trackpad = pg.evaluate(MAGTALL)
        check(f"{_n}: ...a trackpad's pinch, small deltas, a rung once they add up to one",
              trackpad[0] == "8×" and all(small), f"eight of 5: {trackpad}")
        plain = pg.evaluate(WHEEL, {"n": 1, "ctrl": False, "dy": -100})
        pg.wait_for_timeout(250)
        after = pg.evaluate(MAGTALL)
        check(f"{_n}: ...and without Ctrl the wheel is the page's, as before",
              after[0] == "8×" and plain == [False], f"{after}; called off {plain}")
        check(f"{_n}: no page errors with the wheel", not errs, "; ".join(errs[:2]))
        c.close()

    b.close()

summarise_and_exit()
