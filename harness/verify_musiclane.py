#!/usr/bin/env python3
"""The drawing in its lane (the owner's pick in the whole-drawer mock,
FUTURE.md 6s, step 7, from ACID's video track; "All yes").

  THE PAD'S STROKES IN THEIR OWN INKS. Each stroke's mark on the timeline's
  drawing lane is the ink it was drawn in, read off the canvas's pixels, light
  and dark, on the owner's phone and a desk: an ink that reads 3:1 against the
  lane exactly as drawn, and one that does not (a pale ink on the light lane,
  a dark one on the dark) its own hue kept, made darker on the light lane and
  lighter on the dark only as far as 3:1 takes it, so it stays the ink it was.
  An eraser's stroke is the lane's own accent.

  FLIP'S PAGES AS THEIR OWN LITTLE PICTURES. Each page's slot shows that
  page's picture (the strip's thumbnail) and no other's, at the lane's height
  and its own shape: one centred on the page's time and the rest either side,
  so a page held long is its picture again and again, and a page shorter than
  its picture is the whole picture, smaller; its number on a small badge in
  the corner of a picture at the lane's height and none on a smaller one, so
  it never hides a short page's drawing; the turns after the first its pictures
  too, fainter; each framed in the lane's purple, 3:1 and up against the lane;
  past the thumbnail cache's budget, the strip's own tile; a page drawn on
  shows its new picture.

  FLIP'S LANE TALLER FOR THEM. 34px over a box of its own height and 52 over
  one twice as tall, the song 8px under it, read off the canvas; on every
  frame of the taller box's glide, up and back, the lane the one for that
  frame's box, and the song and the ends' handles 8px under it. A press on
  the taller lane moves nothing. The beat lit as it is heard sits on its dot
  under it. The Pad's lane stays 26px, the box tall or not: a stroke reads as
  a line.

  THE STRIP IN ITS BOX (the owner: "things not fitting in the container").
  A drawing that ends on a dot (every mark is drawn 60ms wide, so a dot
  shows) has the dot inside its strip, moved back to end on the drawing's
  end, and none of its ink past it. Zoomed in past where the drawing ends,
  its box ends at the timeline's edge rounded, as the song's box does, and a
  stroke running past the edge is cut by that rounded corner.

Each row runs on the editor whose lane it is: the inks are the Pad's and the
pictures Flip's (the other lane has no inks or no pictures). The lane's
height is Flip's, and the Pad's staying put is the Pad's row; the handles,
the press and the lit beat follow the lane, so they are read where it moves
(on the Pad they cannot fail). Skribl's ears are off here.
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
    print("No assertions were executed. This is NOT evidence the drawing's lane shows the drawing.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: MUSICLANE_PART=inks (pictures, budget, fresh, height,
# glide, press, lit or strip) runs one part. A real run sets none.
PART = os.environ.get("MUSICLANE_PART", "")


def part(name):
    return not PART or PART == name


DESK = dict(viewport={"width": 1280, "height": 900})
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
FACES = (("phone", PHONE), ("desk", DESK))


def _wav(seconds, rate=8000):
    """A pulse twice a second."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(32767 * 0.34 * math.sin(2 * math.pi * 220 * i / rate) * math.exp(-((2 * i / rate) % 1) * 7)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


TWELVE = {"name": "twelve.wav", "mimeType": "audio/wav", "buffer": _wav(12.0)}
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"

# THE PAD'S DRAWING: a stroke in each ink, each 0.8s with 0.4s between, then
# an eraser's. Skribl purple and a near-black read as drawn on the light lane,
# a coral (2.80:1) and a pale yellow (1.12:1) do not; on the dark lane the
# near-black (1.08:1) does not and the rest do.
INKS = [("Skribl purple", "#7c5cff"), ("coral", "#ff6b5c"), ("pale yellow", "#fff3b0"), ("near-black", "#1b1b1f")]
STROKES = """(inks) => { strokes.length = 0; let t = 0;
  inks.concat([null]).forEach((c, k) => { for (let j = 0; j <= 16; j++) strokes.push({ x: 60 + j * 8, y: 60 + k * 40, color: c || '#ffffff', size: 8,
    t: t + j * 50, start: j === 0, erase: !c }); t += 16 * 50 + 400; });
  updateDrawingTimeLabels(); }"""
# FLIP'S PAGES: each an upright bar down its middle in its own colour, at 4
# pages a second: held 2s (8, the longest a page holds), two of half a second
# and one of a quarter (3.25s in all), that one with a bar near each side
# instead. Blue, not black: a page's paper is dark on the dark lane.
ART = [("red", "#e5484d", 8, [0.5]), ("green", "#30a46c", 2, [0.5]), ("amber", "#f5a524", 2, [0.5]), ("blue", "#0091ff", 1, [0.15, 0.85])]
PAGES = """(pages) => { frames.length = 0;
  for (const [c, hold, xs] of pages) { const f = newFrame();
    for (const fx of xs) { const pts = [];
      for (let j = 0; j <= 12; j++) pts.push({ x: CW * fx, y: CH * (0.1 + 0.8 * j / 12), color: c, size: CW * 0.15, t: j * 5, start: j === 0 });
      f.strokes.push(...pts); f.strokeGroups.push(pts.length); }
    if (hold > 1) f.hold = hold; frames.push(f); }
  fps = 4; idx = 0; buildStrip(); render(); updateToolState(); }"""
SET = """(o) => { musicTempo = o.tempo || null; trimStart = o.s; trimEnd = o.e; loopCrossfadeMs = 0; setCrossfadeUI(); updateTrimUI();
  (typeof padDrawer !== 'undefined' ? padDrawer : musicDrawer).resetView(); }"""
# The lane's own colours, as the page resolves them (rgb), and the strip's
# thumbnail's shape.
TOKENS = """() => { const tl = document.getElementById('musicTimeline'), st = getComputedStyle(tl), out = {};
  for (const n of ['--menu-card', '--text-strong', '--accent', '--accent-fill', '--accent-ink']) {
    const p = document.createElement('i'); p.style.color = st.getPropertyValue(n).trim(); tl.appendChild(p);
    const c = getComputedStyle(p).color, m = c.match(/[\\d.]+/g).map(Number); p.remove();
    out[n] = /^color\\(/.test(c) ? m.slice(0, 3).map((v) => Math.round(v * 255)) : m.slice(0, 3); }
  const t = document.querySelector('#strip .frame canvas');
  out.thumb = t ? t.width / t.height : null;
  return out; }"""
PAINT = """() => { const tl = document.getElementById('musicTimeline'), cv = document.getElementById('musicTlCanvas'), P = tl._painted || {};
  return { marks: P.marks || [], lane: P.lane, art: P.art || 0, w: cv.clientWidth, dpr: cv.width / (cv.clientWidth || 1) }; }"""
# Pixels of the timeline's canvas: each [x, y] in CSS px (rgb), or each box
# [x0, y0, x1, y1] as its device pixels' rgb, row by row.
AT = """(pts) => { const cv = document.getElementById('musicTlCanvas'), d = cv.width / cv.clientWidth, x = cv.getContext('2d');
  return pts.map(([px, py]) => Array.from(x.getImageData(Math.round(px * d), Math.round(py * d), 1, 1).data).slice(0, 3)); }"""
BOX = """(boxes) => { const cv = document.getElementById('musicTlCanvas'), d = cv.width / cv.clientWidth, x = cv.getContext('2d');
  return boxes.map(([a, b, c, e]) => { const c0 = Math.ceil(a * d), r0 = Math.ceil(b * d), w = Math.max(1, Math.floor(c * d) - c0), h = Math.max(1, Math.floor(e * d) - r0);
    const img = x.getImageData(c0, r0, w, h).data, rows = [];
    for (let r = 0; r < h; r++) { const row = []; for (let k = 0; k < w; k++) { const i = (r * w + k) * 4; row.push([img[i], img[i + 1], img[i + 2]]); } rows.push(row); }
    return { c0: c0 / d, d, rows }; }); }"""
# The lane's height and the song's top as painted, down one column: the rows
# painted from the top, then the gap the canvas leaves clear.
SCAN = """(cx) => { const cv = document.getElementById('musicTlCanvas'), d = cv.width / cv.clientWidth, H = cv.height;
  const col = cv.getContext('2d').getImageData(Math.round(cx * d), 0, 1, H).data, a = (r) => col[r * 4 + 3];
  let r = Math.ceil(2 * d); while (r < H && a(r) > 0) r++; const lane = r / d; while (r < H && a(r) === 0) r++;
  const st = document.getElementById('musicTlStage').getBoundingClientRect();
  return { lane, song: r / d, h: +st.height.toFixed(2), hd: ['tlStart', 'tlEnd'].map((id) => +(document.getElementById(id).getBoundingClientRect().top - st.top).toFixed(2)) }; }"""
# Every frame from a tap on the taller box until it has held still a while,
# each reading taken first thing in the next frame (what that frame showed).
REC = r"""(cx) => new Promise(done => {
  const scan = new Function('cx', 'return (' + window.__scan + ')(cx)'), out = [], t0 = performance.now();
  const snap = () => { const s = scan(cx); s.t = Math.round(performance.now() - t0); out.push(s); };
  snap();
  let still = 0, n = 0;
  function loop() { snap(); n++; const a = out[out.length - 1], b = out[out.length - 2];
    still = a.h === b.h && a.lane === b.lane ? still + 1 : 0;
    if (still < 12 && n < 120) requestAnimationFrame(loop); else done(out); }
  requestAnimationFrame(loop);
  document.getElementById('musicTlTall').click();
})"""


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    p, q = lum(a), lum(b)
    return (max(p, q) + 0.05) / (min(p, q) + 0.05)


def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def hsl(c):
    r, g, b = (v / 255 for v in c)
    hi, lo = max(r, g, b), min(r, g, b)
    d, l, hu = hi - lo, (hi + lo) / 2, 0.0
    if d:
        hu = (g - b) / d if hi == r else (b - r) / d + 2 if hi == g else (r - g) / d + 4
        hu = (hu * 60 + 360) % 360
    return hu, (d / (1 - abs(2 * l - 1)) if d else 0.0), l


def lit(c, k, way):
    """`c` with its hue kept, k fiftieths lighter (way 1) or darker (-1), as
    whole channels."""
    hu, sa, l = hsl(c)
    l = max(0.0, min(1.0, l + way * k / 50))
    q = (1 - abs(2 * l - 1)) * sa
    x, m = q * (1 - abs((hu / 60) % 2 - 1)), l - q / 2
    p = [[q, x, 0], [x, q, 0], [0, q, x], [0, x, q], [x, 0, q], [q, 0, x]][int(math.floor(hu / 60)) % 6]
    return [math.floor((v + m) * 255 + 0.5) for v in p]


def far(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def lane_for(h, base):
    """Flip's lane over a box that tall: 34px at its own height, 52 at twice it."""
    return math.floor(34 + 18 * max(0.0, min(1.0, (h - base) / base)) + 0.5)


def editor(b, name, path, *, opts=PHONE, scheme="light", song=TWELVE, before=None):
    c = waits.instrument(b.new_context(color_scheme=scheme, **opts))
    c.add_init_script(NO_EARS)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    if before:
        pg.evaluate(before)
    if name == "Flip":
        pg.evaluate(PAGES, [[c2, h, xs] for _, c2, h, xs in ART])
    else:
        pg.evaluate(STROKES, [i for _, i in INKS])
    browsing.pad_drawer(pg, "music")
    pg.set_input_files("#musicInput", song)
    pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - 12) < 0.2", timeout=20000)
    waits.settle(pg, 500)
    pg.evaluate(SET, {"s": 1.0, "e": 7.0 if name == "Flip" else 9.0})
    pg.wait_for_timeout(500)
    pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })")
    pg.wait_for_timeout(300)
    browsing.wait_scroll_still(pg)
    return c, pg, errs


def first_turn(marks):
    return [m for m in marks if m[2] == 0]


def runs(cols, x0, d, need):
    """Groups of neighbouring device columns each holding `need` pixels or
    more, as their middles in CSS px (a group touching either end left out)."""
    out, cur = [], []
    for k, n in enumerate(cols + [0]):
        if n >= need:
            cur.append(k)
        elif cur:
            if cur[0] > 0 and cur[-1] < len(cols) - 1:
                out.append(round(x0 + (cur[0] + cur[-1] + 1) / 2 / d, 2))
            cur = []
    return out


with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    print("\nMUSIC LANE — the Pad's strokes in their own inks")
    if part("inks"):
        got = []
        for face, opts in FACES:
            for scheme in ("light", "dark"):
                c, pg, errs = editor(b, "Pad", "/", opts=opts, scheme=scheme)
                tk = pg.evaluate(TOKENS)
                p = pg.evaluate(PAINT)
                ms = first_turn(p["marks"])
                lane = p["lane"] or 26
                px = pg.evaluate(AT, [[(m[0] + m[1]) / 2, lane / 2] for m in ms])
                got.append((face, scheme, tk, ms, px, errs))
                c.close()
        as_drawn, moved, reads, eraser, wrong = [], [], [], [], []
        for face, scheme, tk, ms, px, errs in got:
            card, words = tk["--menu-card"], tk["--text-strong"]
            if len(px) != len(INKS) + 1:
                wrong.append(f"{face} {scheme}: {len(px)} marks for {len(INKS) + 1} strokes")
                continue
            for (nm, ink), g in zip(INKS, px):
                drawn = rgb(ink)
                reads.append((face, scheme, nm, round(ratio(g, card), 2)))
                if ratio(drawn, card) >= 3:
                    as_drawn.append((face, scheme, nm, far(g, drawn) <= 3, g))
                else:
                    way = -1 if lum(words) < lum(card) else 1
                    k = next((k for k in range(1, 51) if far(lit(drawn, k, way), g) <= 3), None)
                    same = abs((hsl(g)[0] - hsl(drawn)[0] + 180) % 360 - 180) <= 4 or hsl(drawn)[1] < 0.15
                    moved.append((face, scheme, nm, k, g, k is not None and same and ratio(g, card) >= 3 and ratio(lit(drawn, k - 1, way), card) < 3))
            eraser.append((face, scheme, far(px[-1], tk["--accent"]) <= 3, px[-1], tk["--accent"]))
        themes_moved = {s for _, s, *_ in moved}
        check("Pad: each stroke's mark is the ink it was drawn in where that reads 3:1 against the lane, light and dark, phone and desk",
              not wrong and as_drawn and all(ok for *_, ok, _ in as_drawn),
              "; ".join(wrong) or "; ".join(f"{f} {s} {n}: {g}{'' if ok else ' (not as drawn)'}" for f, s, n, ok, g in as_drawn))
        check("Pad: ...and an ink that would not read (a pale one on the light lane, a dark one on the dark) keeps its own hue, made darker"
              " on the light lane and lighter on the dark only as far as 3:1 takes it",
              not wrong and themes_moved == {"light", "dark"} and all(ok for *_, ok in moved),
              "; ".join(wrong) or "; ".join(f"{f} {s} {n}: {g}, {k if k is not None else 'off its hue'} fiftieths {'darker' if s == 'light' else 'lighter'}" + ("" if ok else " (not the least that reads)")
                                            for f, s, n, k, g, ok in moved))
        check("Pad: every stroke's mark reads 3:1 and up against the lane",
              not wrong and reads and all(r >= 3 for *_, r in reads), "; ".join(f"{f} {s} {n} {r}:1" for f, s, n, r in reads if r < 3.3))
        check("Pad: an eraser's stroke is the lane's own accent", not wrong and eraser and all(ok for _, _, ok, *_ in eraser),
              "; ".join(f"{f} {s}: {g}, the accent {a}" for f, s, ok, g, a in eraser))
        check("Pad: no page errors with the inks", not any(e for *_, e in got), "; ".join(e for *_, es in got for e in es[:2]))

    print("\nMUSIC LANE — Flip's pages as their own little pictures")
    if part("pictures"):
        for face, opts, scheme in (("phone", PHONE, "light"), ("desk", DESK, "dark")):
            c, pg, errs = editor(b, "Flip", "/flip", opts=opts, scheme=scheme)
            tk = pg.evaluate(TOKENS)
            p = pg.evaluate(PAINT)
            lane, ms = p["lane"] or 34, first_turn(p["marks"])
            later = [m for m in p["marks"] if m[2] == 1]
            regions = [[m[0] + 2, 5, m[1] - 2, lane - 5] for m in ms] + [[m[0] + 2, 5, m[1] - 2, lane - 5] for m in later[:1]]
            boxes = pg.evaluate(BOX, regions)
            cols = [rgb(h) for _, h, *_ in ART]
            fill, card = tk["--accent-fill"], tk["--menu-card"]

            def count(bx, col, lim):
                return sum(1 for row in bx["rows"] for px in row if far(px, col) < lim)
            own = []
            for i, (m, bx) in enumerate(zip(ms, boxes)):
                if i >= len(ART):
                    break
                own.append((ART[i][0], round(m[1] - m[0], 1), count(bx, cols[i], 60), {ART[j][0]: count(bx, cols[j], 60) for j in range(len(ART)) if j != i}))
            check(f"Flip ({face}, {scheme}): each page's slot shows its own picture, and no other page's",
                  len(ms) == len(ART) and p["art"] >= len(ART) and all(n >= 4 and not any(o.values()) for _, _, n, o in own),
                  f"{len(ms)} slots for {len(ART)} pages, {p['art']} pictures; " + "; ".join(f"{nm} ({w}px): {n} of its own colour, others {o}" for nm, w, n, o in own))
            # The red page, 2s: its picture again and again, one centred on it.
            tw = (lane - 8) * (tk["thumb"] or 88 / 62)
            red = boxes[0] if boxes else None
            per = [sum(1 for row in red["rows"] if far(row[k], cols[0]) < 60) for k in range(len(red["rows"][0]))] if red else []
            mids = runs(per, red["c0"], red["d"], 6) if red else []
            gaps = [round(z - a, 2) for a, z in zip(mids, mids[1:])]
            centre = (ms[0][0] + ms[0][1]) / 2 if ms else 0
            check(f"Flip ({face}, {scheme}): a page held long is its picture again and again along its time, its own shape kept, one centred on the page",
                  len(mids) >= 3 and all(abs(g - tw) <= 1.5 for g in gaps) and any(abs(x - centre) <= 1.5 for x in mids),
                  f"the bar at {mids} in a slot {ms[0][0] if ms else '?'} to {ms[0][1] if ms else '?'} (its middle {centre:.2f}), a picture {tw:.2f}px wide; apart {gaps}")
            # The blue page, a quarter of a second, narrower than its picture:
            # the whole picture, smaller (its two bars where the page has them,
            # their height the smaller picture's).
            bk = ms[3] if len(ms) > 3 else None
            sh, got_b, want_b, rows_b = 0, [], [], 0
            if bk:
                pl, pw = bk[0] + 1.5, max(3, bk[1] - bk[0] - 3)
                sh = pw / (tk["thumb"] or 88 / 62)
                bb = pg.evaluate(BOX, [[pl - 1, 4, pl + pw + 1, lane - 4]])[0]
                per = [sum(1 for row in bb["rows"] if far(row[k], cols[3]) < 60) for k in range(len(bb["rows"][0]))]
                got_b = runs(per, bb["c0"], bb["d"], 1)
                want_b = [round(pl + 0.15 * pw, 2), round(pl + 0.85 * pw, 2)]
                rows_b = round(sum(1 for row in bb["rows"] if any(far(px, cols[3]) < 60 for px in row)) / bb["d"], 2)
            check(f"Flip ({face}, {scheme}): a page shorter than its picture is the whole picture, smaller",
                  bk is not None and bk[1] - bk[0] < tw and len(got_b) == 2 and all(abs(g - w) <= 1.5 for g, w in zip(got_b, want_b))
                  and 0.5 * sh <= rows_b <= 0.85 * sh + 2,
                  f"the blue page's slot {bk and round(bk[1] - bk[0], 1)}px (its picture {tw:.1f} wide at the lane's height): its bars at {got_b}, "
                  f"the page has them at {want_b}, {rows_b}px tall in a picture {sh:.1f}px tall")
            # Its number on a small badge on a picture at the lane's height, none on a smaller one.
            badge = []
            for i, m in enumerate(ms[:len(ART)]):
                wide = m[1] - m[0] - 3 >= tw - 0.01
                bx = pg.evaluate(BOX, [[m[0] + 5, 10.5, m[0] + 7, 16.5], [m[0] + 7.5, 8, m[0] + 20, 19], [m[0] + 2, 5, min(m[1] - 2, m[0] + 24), lane - 5]])
                on = sum(1 for row in bx[0]["rows"] for px in row if far(px, fill) < 40) / max(1, sum(len(r) for r in bx[0]["rows"]))
                digit = sum(1 for row in bx[1]["rows"] for px in row if min(px) > 225)
                anyfill = sum(1 for row in bx[2]["rows"] for px in row if far(px, fill) < 40)
                badge.append((ART[i][0], round(m[1] - m[0], 1), wide, round(on, 2), digit, anyfill))
            check(f"Flip ({face}, {scheme}): its number on a small badge in the corner where the page is its picture at the lane's height, and none on a smaller picture",
                  any(w for _, _, w, *_ in badge) and any(not w for _, _, w, *_ in badge)
                  and all((on >= 0.8 and dg >= 3) if w else af == 0 for _, _, w, on, dg, af in badge),
                  "; ".join(f"{nm} ({wd}px, {'its picture at the lane height' if w else 'a smaller picture'}): badge {on:.0%} its fill, {dg} white of the number, {af} of its fill anywhere"
                            for nm, wd, w, on, dg, af in badge))
            # Each page's picture framed in the lane's purple, on whole device
            # pixels: across its left edge at the picture's middle, a pixel
            # that is the purple itself (a frame between pixels is only ever
            # part of it), 3:1 and up against the lane.
            frames_ = []
            for i, m in enumerate(ms[:len(ART)]):
                pl = m[0] + 1.5
                row = [px for r in pg.evaluate(BOX, [[pl - 2, lane / 2 - 0.5, pl + 2, lane / 2 + 0.5]])[0]["rows"] for px in r]
                best = min(row, key=lambda px: far(px, tk["--accent-ink"]))
                frames_.append((ART[i][0], far(best, tk["--accent-ink"]), round(ratio(best, card), 2)))
            check(f"Flip ({face}, {scheme}): each page's picture is framed in the lane's purple, crisp, 3:1 and up against the lane",
                  len(frames_) == len(ART) and all(d <= 24 and r >= 3 for _, d, r in frames_),
                  "; ".join(f"{nm}: {d} off the purple, {r}:1" for nm, d, r in frames_))
            # The second turn (the animation goes round in the loop): the red
            # page again, its picture at a little under half strength.
            faint = [round(0.45 * a + 0.55 * k) for a, k in zip(cols[0], card)]
            lb = boxes[len(ms)] if later and len(boxes) > len(ms) else None
            n_faint = count(lb, faint, 50) if lb else 0
            n_full = count(lb, cols[0], 40) if lb else 0
            check(f"Flip ({face}, {scheme}): the turns after the first are its pictures too, fainter",
                  later and n_faint >= 4 and n_full == 0,
                  f"{len(later)} later slots; the first: {n_faint} pixels at the fainter red {faint}, {n_full} at the full red")
            check(f"Flip ({face}, {scheme}): no page errors with the pictures", not errs, "; ".join(errs[:2]))
            c.close()

    if part("budget"):
        # Past the thumbnail cache's budget (a long document on a 3x phone):
        # the lane shows the strip's own tile, and paints no page itself.
        c, pg, errs = editor(b, "Flip", "/flip", opts=PHONE, before="() => { _thumbBytes = THUMB_CACHE_BYTES; }")
        p = pg.evaluate(PAINT)
        lane, ms = p["lane"] or 34, first_turn(p["marks"])
        boxes = pg.evaluate(BOX, [[m[0] + 2, 5, m[1] - 2, lane - 5] for m in ms])
        cols = [rgb(h) for _, h, *_ in ART]
        own = [(ART[i][0], sum(1 for row in bx["rows"] for px in row if far(px, cols[i]) < 60),
                sum(1 for j in range(len(ART)) if j != i for row in bx["rows"] for px in row if far(px, cols[j]) < 60)) for i, bx in enumerate(boxes[:len(ART)])]
        kept = pg.evaluate("() => frames.filter((f) => _thumbCache.get(f)).length")
        check("Flip: past the thumbnail cache's budget, each page's slot still shows its own picture, the strip's own tile",
              kept == 0 and len(own) == len(ART) and all(n >= 4 and o == 0 for _, n, o in own),
              f"{kept} pages in the cache; " + "; ".join(f"{nm}: {n} of its own colour, {o} of the others'" for nm, n, o in own))
        check("Flip: no page errors past the cache's budget", not errs, "; ".join(errs[:2]))
        c.close()

    if part("fresh"):
        # A page drawn on (the second, green), a broad stroke in a new colour
        # down its left quarter through the real canvas (a pen's own width is
        # under a pixel at the lane's size): its slot shows it. A stroke
        # is a tap away from the drawer on Flip, which closes it, so the lane
        # is read as the drawer opens again, as a person would see it.
        c, pg, errs = editor(b, "Flip", "/flip", opts=DESK)
        NEW = "#d6409f"

        def blues():
            p = pg.evaluate(PAINT)
            lane, ms = p["lane"] or 34, first_turn(p["marks"])
            return sum(1 for row in pg.evaluate(BOX, [[ms[1][0] + 2, 5, ms[1][1] - 2, lane - 5]])[0]["rows"] for px in row if far(px, rgb(NEW)) < 60)
        before = blues()
        pg.evaluate("(c) => { idx = 1; render(); buildStrip(); updateToolState(); setColor(c); size = Math.round(CW * 0.12); }", NEW)
        pg.evaluate("() => document.getElementById('pad').scrollIntoView({ block: 'center' })")
        pg.wait_for_timeout(300)
        browsing.wait_scroll_still(pg)
        bb = pg.locator("#pad").bounding_box()
        pg.mouse.move(bb["x"] + bb["width"] * 0.25, bb["y"] + bb["height"] * 0.15); pg.mouse.down()
        for k in range(1, 15):
            pg.mouse.move(bb["x"] + bb["width"] * 0.25, bb["y"] + bb["height"] * (0.15 + 0.7 * k / 14)); pg.wait_for_timeout(16)
        pg.mouse.up(); pg.wait_for_timeout(500)
        on_page = pg.evaluate("(c) => frames[1].strokes.filter((s) => s.color === c).length", NEW)
        browsing.pad_drawer(pg, "music")
        pg.evaluate("() => document.getElementById('musicTimeline').scrollIntoView({ block: 'center' })")
        pg.wait_for_timeout(400)
        browsing.wait_scroll_still(pg)
        after = blues()
        check("Flip: a page drawn on shows its new picture in the lane", before == 0 and on_page > 3 and after >= 4,
              f"the new colour on the second page's slot: {before} pixels before, {after} after ({on_page} of its points on the page)")
        check("Flip: no page errors drawing with the lane open", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nMUSIC LANE — Flip's lane taller for its pictures")
    if part("height"):
        for _n, _p in (("Flip", "/flip"), ("Pad", "/")):
            got = {}
            for face, opts in FACES:
                c, pg, errs = editor(b, _n, _p, opts=opts)
                p = pg.evaluate(PAINT)
                cx = (p["marks"][0][0] + p["marks"][0][1]) / 2
                a = pg.evaluate(SCAN, cx)
                pg.click("#musicTlTall"); pg.wait_for_timeout(700)
                z = pg.evaluate(SCAN, cx)
                got[face] = (a, z, errs)
                c.close()
            if _n == "Flip":
                check("Flip: its lane is 34px over the box at its own height and 52 over one twice as tall, the song 8px under it, read off the canvas",
                      all(abs(a["lane"] - 34) <= 0.5 and abs(z["lane"] - 52) <= 0.5 and abs(a["song"] - 42) <= 0.5 and abs(z["song"] - 60) <= 0.5
                          and abs(z["h"] - 2 * a["h"]) <= 0.5 for a, z, _ in got.values()),
                      "; ".join(f"{f}: lane {a['lane']} then {z['lane']}, the song from {a['song']} then {z['song']}, the box {a['h']} then {z['h']}" for f, (a, z, _) in got.items()))
                check("Flip: the ends' handles start 8px under the lane, short and tall",
                      all(all(abs(h - a["lane"] - 8) <= 0.5 for h in a["hd"]) and all(abs(h - z["lane"] - 8) <= 0.5 for h in z["hd"]) for a, z, _ in got.values()),
                      "; ".join(f"{f}: handles at {a['hd']} under a lane of {a['lane']}, then {z['hd']} under {z['lane']}" for f, (a, z, _) in got.items()))
            else:
                check("Pad: its lane stays 26px, the box tall or not, the song and the handles 8px under it",
                      all(abs(a["lane"] - 26) <= 0.5 and abs(z["lane"] - 26) <= 0.5 and abs(z["song"] - 34) <= 0.5 and abs(z["h"] - 2 * a["h"]) <= 0.5
                          and all(abs(h - 34) <= 0.5 for h in a["hd"] + z["hd"]) for a, z, _ in got.values()),
                      "; ".join(f"{f}: lane {a['lane']} then {z['lane']}, the song from {z['song']}, handles {a['hd']} then {z['hd']}" for f, (a, z, _) in got.items()))
            check(f"{_n}: no page errors as the lane grows", not any(e for *_, e in got.values()), "; ".join(e for *_, es in got.values() for e in es[:2]))

    if part("glide"):
        for face, opts in FACES:
            c, pg, errs = editor(b, "Flip", "/flip", opts=opts)
            pg.evaluate("(s) => { window.__scan = s; }", SCAN)
            p = pg.evaluate(PAINT)
            cx = (p["marks"][0][0] + p["marks"][0][1]) / 2
            up = pg.evaluate(REC, cx); pg.wait_for_timeout(600)
            down = pg.evaluate(REC, cx); pg.wait_for_timeout(300)
            base = up[0]["h"]

            def judge(rows, way, end):
                lanes = [r["lane"] for r in rows]
                off = [(r["t"], r["h"], r["lane"], lane_for(r["h"], base)) for r in rows if abs(r["lane"] - lane_for(r["h"], base)) > 0.5]
                back = [round(way * (z - a), 2) for a, z in zip(lanes, lanes[1:]) if way * (z - a) < -0.01]
                between = sum(1 for r in rows if base + 1 < r["h"] < 2 * base - 1)
                under = [(r["t"], r["lane"], r["song"], r["hd"]) for r in rows
                         if abs(r["song"] - r["lane"] - 8) > 0.5 or any(abs(h - r["lane"] - 8) > 0.5 for h in r["hd"])]
                return {"ok": not off and not back and between >= 3 and abs(lanes[-1] - end) <= 0.5, "off": off[:4], "back": back, "between": between,
                        "lanes": sorted(set(lanes)), "last": lanes[-1], "under": under[:4]}
            gu, gd = judge(up, 1, 52), judge(down, -1, 34)
            check(f"Flip ({face}): on every frame of the taller box's glide, up and back, the lane is the one for that frame's box, only the way it goes",
                  gu["ok"] and gd["ok"],
                  f"up: {gu['between']} frames between, lanes {gu['lanes']} to {gu['last']}, off its box {gu['off']}, against the way {gu['back']}; "
                  f"back: {gd['between']} between, lanes {gd['lanes']} to {gd['last']}, off {gd['off']}, against {gd['back']}")
            check(f"Flip ({face}): ...and the song and the ends' handles 8px under it on every frame",
                  not gu["under"] and not gd["under"] and gu["between"] >= 3, f"up {gu['under']}; back {gd['under']} (when, the lane, the song's top, the handles)")
            check(f"Flip ({face}): no page errors as the lane glides", not errs, "; ".join(errs[:2]))
            c.close()

    if part("press"):
        # The box tall, a press on the lane and a drag along it: nothing moves.
        # Just under it, on the song, the same drag slides the song (so the
        # press is where it is meant to be).
        c, pg, errs = editor(b, "Flip", "/flip", opts=DESK)
        pg.click("#musicTlTall"); pg.wait_for_timeout(700)
        st = pg.evaluate("() => { const r = document.getElementById('musicTlStage').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width }; }")
        lane = pg.evaluate(PAINT)["lane"] or 34
        trim = lambda: pg.evaluate("() => [+trimStart.toFixed(4), +trimEnd.toFixed(4), document.getElementById('musicTimeline').dataset.view]")

        def drag(y):
            x0 = st["x"] + st["w"] * 0.55
            pg.mouse.move(x0, y); pg.mouse.down()
            for k in range(1, 13):
                pg.mouse.move(x0 - 7 * k, y); pg.wait_for_timeout(16)
            pg.mouse.up(); pg.wait_for_timeout(400)
        t0 = trim(); drag(st["y"] + lane - 6); t1 = trim()
        drag(st["y"] + lane + 8 + 14); t2 = trim()
        check("Flip: a press on its taller lane moves nothing; just under it, on the song, the same drag slides the song",
              lane >= 50 and t1 == t0 and t2[:2] != t1[:2], f"the lane {lane}px: before {t0}, after a drag on the lane {t1}, after one on the song {t2}")
        check("Flip: no page errors pressing the lane", not errs, "; ".join(errs[:2]))
        c.close()

    if part("lit"):
        # The beat lit as it is heard sits on its dot, the lane short and tall.
        LIT = """() => new Promise((done) => { const tl = document.getElementById('musicTimeline'), t0 = performance.now(), n0 = tl._lit ? tl._lit.n : 0;
          const id = setInterval(() => { const l = tl._lit; if (!(l && l.n >= n0 + 2) && performance.now() - t0 < 4000) return; clearInterval(id);
            const el = tl.querySelector('.mt-tl-lit'), st = document.getElementById('musicTlStage').getBoundingClientRect();
            if (!l || !el) return done(null);
            const r = el.getBoundingClientRect(), cv = document.getElementById('musicTlCanvas'), d = cv.width / cv.clientWidth, H = cv.height;
            const col = (x) => { const g = cv.getContext('2d').getImageData(Math.round(x * d), 0, 1, H).data, o = []; for (let k = 0; k < H; k++) o.push([g[k * 4], g[k * 4 + 1], g[k * 4 + 2]]); return o; };
            done({ x: l.x, y: (r.top + r.bottom) / 2 - st.top, at: col(l.x), beside: col(l.x - 6), d, lane: (tl._painted || {}).lane }); }, 4); })"""
        got = []
        for tall in (False, True):
            c, pg, errs = editor(b, "Flip", "/flip", opts=DESK)
            pg.evaluate("() => { musicTempo = { bpm: 120, phase: 0 }; updateTrimUI(); }")
            if tall:
                pg.click("#musicTlTall"); pg.wait_for_timeout(700)
            pg.wait_for_timeout(300)
            pg.click("#previewLoopBtn")
            r = pg.evaluate(LIT)
            pg.click("#previewLoopBtn"); pg.wait_for_timeout(200)
            dot = None
            if r:
                lo, hi = int((r["lane"] + 8) * r["d"]), int((r["lane"] + 8 + 13) * r["d"])
                rows = [k for k in range(lo, hi) if far(r["at"][k], r["beside"][k]) > 60]
                dot = round((rows[0] + rows[-1] + 1) / 2 / r["d"], 2) if rows else None
            got.append(("tall" if tall else "short", r and round(r["y"], 2), dot, r and r["lane"], errs))
            c.close()
        check("Flip: the beat lit as it is heard sits on its dot, under the lane short and tall",
              all(y is not None and d is not None and abs(y - d) <= 1 for _, y, d, _, _ in got),
              "; ".join(f"{k} (lane {ln}): lit at {y}, its dot at {d}" for k, y, d, ln, _ in got))
        check("Flip: no page errors as the beat lights", not any(e for *_, e in got), "; ".join(e for *_, es in got for e in es[:2]))

    print("\nMUSIC LANE — the drawing's strip fits its box (the owner: \"things not fitting in the container\")")
    if part("strip"):
        # A drawing that ends on a dot: each mark is drawn 60ms wide so a dot
        # shows, and the last one was drawn past the strip's end. Read off the
        # canvas: the lane's row just past the drawing's end holds none of the
        # dot's ink, and the dot is there, inside.
        DOTS = """() => { strokes.length = 0; let t = 0;
          for (let k = 0; k < 3; k++) { for (let j = 0; j <= 10; j++) strokes.push({ x: 60 + j * 10, y: 60 + k * 30, color: '#7c5cff', size: 8, t: t + j * 45, start: j === 0 }); t += 450 + 150; }
          for (let k = 0; k < 4; k++) { strokes.push({ x: 300, y: 60 + k * 20, color: '#7c5cff', size: 8, t: t, start: true }); t += 300; }
          updateDrawingTimeLabels(); updateTrimUI(); }"""
        END = """() => { const v = document.getElementById('musicTimeline').dataset.view.split(' ').map(Number), cv = document.getElementById('musicTlCanvas');
          return (trimStart + getPlaybackDuration() / 1000 - v[0]) / v[1] * cv.clientWidth; }"""
        got = []
        for face, opts, scheme in (("phone", PHONE, "light"), ("desk", DESK, "dark")):
            c, pg, errs = editor(b, "Pad", "/", opts=opts, scheme=scheme)
            pg.evaluate(DOTS); pg.wait_for_timeout(500)
            end, P = pg.evaluate(END), pg.evaluate(PAINT)
            lane, ms = P["lane"] or 26, first_turn(P["marks"])
            past = pg.evaluate(AT, [[end + dx, lane / 2] for dx in (2, 3.5, 5, 6.5, 8)])
            inside = pg.evaluate(AT, [[end - dx, lane / 2] for dx in (2, 3, 4)])
            ink = (124, 92, 255)
            # and moved back to end there, not cut off there: every mark ends on the drawing's end or before
            whole = bool(ms) and all(m[1] <= end + 0.5 for m in ms)
            got.append((face, scheme, round(end, 2), [p for p in past if far(p, ink) <= 60], any(far(p, ink) <= 60 for p in inside), whole, ms[-1:], errs))
            c.close()
        check("Pad: a drawing that ends on a dot has the dot inside its strip, moved back to end there, and nothing of it past the strip's end, phone and desk",
              all(not out and dot and whole for _, _, _, out, dot, whole, _, _ in got),
              "; ".join(f"{f} {s}: the drawing ends at {e}px, its ink past it {o or 'none'}, the dot inside {d}, its mark {m}" for f, s, e, o, d, _, m, _ in got))
        check("Pad: no page errors with the dot", not any(e for *_, e in got), "; ".join(e for *_, es in got for e in es[:2]))

        # Zoomed in past where the drawing ends, its box ends at the
        # timeline's edge rounded, as the song's box under it does, not cut
        # flat at the canvas's edge: the box's top right corner is left
        # unpainted, as the song box's is, and the box's own edge is there.
        ALPHA = """(pts) => { const cv = document.getElementById('musicTlCanvas'), d = cv.width / cv.clientWidth, x = cv.getContext('2d');
          return pts.map(([px, py]) => x.getImageData(Math.floor(px * d), Math.floor(py * d), 1, 1).data[3]); }"""
        got = []
        for name, path in (("Pad", "/"), ("Flip", "/flip")):
            c, pg, errs = editor(b, name, path, opts=DESK, scheme="dark")
            pg.click("#musicTlIn"); pg.wait_for_timeout(700)
            p = pg.evaluate(PAINT)
            w, lane = p["w"], p["lane"] or 26
            # the last reading is inside the box, 6px from the edge: the box
            # runs there, so the corners read are its own and not where it ended
            a = pg.evaluate(ALPHA, [[w - 0.5, 0.5], [w - 0.5, lane - 0.5], [w - 0.5, lane + 8 + 0.5], [w - 6, lane / 2]])
            got.append((name, a, errs))
            c.close()
        check("Pad and Flip: zoomed in past where the drawing ends, its box ends at the timeline's edge with its corners rounded, as the song's box does",
              all(a[0] == 0 and a[1] == 0 and a[2] == 0 and a[3] > 0 for _, a, _ in got),
              "; ".join(f"{n}: the lane's top and bottom right corners {a[0]}, {a[1]} (0 is rounded), the song's {a[2]}, inside the box {a[3]}" for n, a, _ in got))
        check("Pad and Flip: no page errors zoomed in", not any(e for *_, e in got), "; ".join(e for *_, es in got for e in es[:2]))

        # A stroke running past the timeline's edge, zoomed in, is cut there by
        # the box's rounded corner too, not drawn square over it: just outside
        # the corner's curve, above the mark's middle, the canvas holds no
        # more than the box's own edge does, on the phone's fine pixels.
        c, pg, errs = editor(b, "Pad", "/", opts=PHONE, scheme="light")
        cross = []
        for _ in range(5):                                  # in until a stroke crosses the edge
            pg.click("#musicTlIn"); pg.wait_for_timeout(700)
            P = pg.evaluate(PAINT)
            w, lane = P["w"], P["lane"] or 26
            cross = [m for m in first_turn(P["marks"]) if m[0] < w - 10 and m[1] > w]
            if cross:
                break
        a = pg.evaluate(ALPHA, [[w - 0.25, 6.25], [w - 6, lane / 2]])
        check("Pad: zoomed in, a stroke running past the timeline's edge is cut by the box's rounded corner, not drawn square over it",
              bool(cross) and a[0] < 200 and a[1] == 255,
              f"a stroke across the edge {cross[:1]}; just outside the corner's curve {a[0]} (a mark is 255), inside {a[1]}")
        check("Pad: no page errors with a stroke past the edge", not errs, "; ".join(errs[:2]))
        c.close()

    b.close()

summarise_and_exit()
