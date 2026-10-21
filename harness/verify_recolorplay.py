"""A recolour in the replay (lib/recolorplay.js): the owner's pick R2 of the
recolour mock, "the Pad's replay shows the change when you made it".

The rows, each the owner's choice or a fault found building it:

  THE TIMELINE. A recoloured line plays in the colour it was drawn in; the
  moment is two entries where it was made, RUN apart, and everything after
  waits RUN, so the replay is RUN longer a moment and Play's badge says so.

  THE PAD'S PLAY, read on every frame it is asked about: before the moment the
  line shows its old colour; as the colour runs, its near end shows the new
  one and its far end the old, the run laid exactly over the drawing; a scrub
  inside the run keeps it running; after it, the new colour all along, the
  line drawn later across it still on top, nothing laid over the drawing.
  Under Reduce Motion the colour changes at the moment, with no run.

  THE LINK PAGE fetches the module only for a drawing with recolours, and
  plays the change when it was made. THE GALLERY'S PLAYER plays it too, its
  run laid exactly over its letterboxed canvas.

  THE SERVER'S LINE under a post says the replay's length and shape with the
  run in them (validation._payload_line, a port of the module's rule).

  THE EXPORTS: a GIF and a video show the old colour, the run and the new
  colour at their moments. And a GIF keeps a base drawn before the first take
  with see-through layering on (its compositor was made before the base, and
  its first present() wiped it).

  THE SCRUBBER'S DOTS (the owner, of the desktop checks: "the scrubber shows
  nothing during the recolor part", then "all yes" to B): a dot of the new
  colour in the middle of each colour's run, half as strong ahead of the
  playhead and whole once played, on the link page in both themes and in the
  Pad's own preview; ringed in the bar's colour where it would not read on
  the track (pink is 2.7:1 on the light one) and not where it would (5.9:1 on
  the dark).

  THE BEAD IN THE FILES (the owner, of the desktop checks: "does the nip
  dissappear on mp4, on gif"; it did, then "all yes" to keeping it): the
  glowing dot the screen's replay has rides the line in a GIF and a video,
  sits on the tap while the colour runs, and is gone from the finished
  drawing. Read off each file's frames by what they show, not by when, so a
  recorder that runs late under load cannot move the answer: every frame
  with the long line part-drawn has the bead at its tip (the ground just
  over the tip, where the line is not, takes the ink's tint), every frame
  with the colour part-run has it on the tap, and the last frame has none.
  The GIF, the WebM, and the MP4 path (WebCodecs, a desk's Chrome or Edge):
  headless Chromium cannot encode H.264, so that row hands the export a
  stand-in encoder that steps the frames as lib/mp4export.js does and keeps
  each one, the frames the real encoder would have been handed.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageSequence
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)
import browsing  # noqa: E402
import waits  # noqa: E402

DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
INK, PINK = "#1f1b2e", "#ff48b0"
RUN = 380
NEAR, FAR, CROSS = (150, 200), (470, 200), (270, 200)


def _line(x0, y0, x1, y1, color, size, t0, n=24):
    return [dict(x=x0 + (x1 - x0) * k / (n - 1), y=y0 + (y1 - y0) * k / (n - 1), color=color, size=size,
                 t=t0 + k * 16, **({"start": True} if k == 0 else {})) for k in range(n)]


def drawing(recoloured=True, public=False, base=None, see_through=False):
    """Line 0 across, recoloured ink -> pink once all three were drawn, from
    its sixth point; line 1 drawn later across it; line 2 a long one."""
    ink0 = "rgba(31, 27, 46, 0.6)" if see_through else INK
    to0 = "rgba(255, 72, 176, 0.6)" if see_through else PINK
    lines = [_line(60, 200, 480, 200, to0 if recoloured else ink0, 14, 0),
             _line(270, 60, 270, 340, INK, 10, 1000), _line(40, 30, 490, 30, INK, 12, 2000, n=60)]
    pts = [p for l in lines for p in l]
    f = {"strokes": pts, "strokeGroups": [len(l) for l in lines], "baseSnapshot": base,
         "background": {"color": "#f6f2ea"}, "photo": None, "music": None}
    if recoloured:
        f["recolors"] = [{"g": 0, "n": len(pts), "k": 0, "at": 5, "was": ink0, "to": to0}]
    d = {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": "tight",
         "title": "Recolour replay", "frames": [f], "canvasSize": {"cssWidth": 816, "cssHeight": 612, "dpr": 1}}
    if public:
        d["visibility"] = "public"
    return d


def base_total(d):
    """The replay's length without recolours: every gap capped at Tight's 50ms."""
    pts, t = d["frames"][0]["strokes"], 0
    for a, b in zip(pts, pts[1:]):
        g = b["t"] - a["t"]
        t += min(g, 50) if g > 0 else 0
    return t


def post(d):
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(d).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    made = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return made.get("id") or made.get("skribl", {}).get("id")


def kind(c):
    r, g, b = c[:3]
    a = c[3] if len(c) > 3 else 255
    if a < 40:
        return "clear"
    if r > 200 and g < 130 and b > 120:
        return "pink"
    if r < 70 and g < 70 and b < 80:
        return "ink"
    return "other"


# What the screen shows at drawing points, on the frames asked for: the run's
# canvas while the drawing's is hidden under it, else the drawing's.
SHOWN = """([sel, pts]) => { const cv = document.querySelector(sel), ov = cv.parentNode.querySelector('.recolor-run');
  const on = !!(ov && ov.isConnected && getComputedStyle(cv).opacity === '0'), src = on ? ov : cv;
  const lg = (typeof getCanvasLogicalSize === 'function' && sel === 'canvas#canvas') ? getCanvasLogicalSize() : { width: 816, height: 612 };
  const px = pts.map(([x, y]) => { const d = src.getContext('2d').getImageData(Math.round(x * src.width / lg.width), Math.round(y * src.height / lg.height), 1, 1).data; return [d[0], d[1], d[2], d[3]]; });
  let geo = null;
  if (on) { const a = cv.getBoundingClientRect(), b = ov.getBoundingClientRect();
    geo = Math.max(Math.abs(a.left - b.left), Math.abs(a.top - b.top), Math.abs(a.width - b.width), Math.abs(a.height - b.height)); }
  return { on, px, geo }; }"""

# The same, read on every frame while a replay plays, for `ms`.
WATCH = """([sel, pts, ms]) => new Promise(res => { const out = [], t0 = performance.now(), read = %s;
  (function f() { out.push(Object.assign({ t: performance.now() - t0 }, read([sel, pts])));
    if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(out); })(); })""" % SHOWN


def phases(frames):
    """The run of what was seen, in order, near / far, with the run's flag."""
    seq = []
    for f in frames:
        k = ("RUN " if f["on"] else "") + kind(f["px"][0]) + "/" + kind(f["px"][1])
        if not seq or seq[-1] != k:
            seq.append(k)
    return seq


with sync_playwright() as pw:
    b = waits.instrument(pw.chromium.launch())

    # ============================================================ the timeline
    print("\nTHE TIMELINE — the old colour, the moment where it was made, RUN after it")
    D = drawing()
    c = b.new_context(**DESK)
    q = c.new_page()
    browsing.goto(q, BASE, "/skribl-pad")
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    q.evaluate("(d) => loadSkribl(d)", D); q.wait_for_timeout(300)
    tl = q.evaluate("""() => { const t = buildPlaybackTimeline(), rc = t.filter(e => e.rc);
        return { first: t[0].color, n: t.length, at: rc.map(e => [t.indexOf(e), e.playT, !!e.rcEnd]),
                 before: t[rc.length ? t.indexOf(rc[0]) - 1 : 0].playT, last: t[t.length - 1].playT,
                 dur: getPlaybackDuration(), points: strokes.length }; }""")
    T0 = base_total(D)
    check("a recoloured line plays in the colour it was drawn in", tl["first"] == INK, json.dumps(tl)[:200])
    check("the moment is two entries where it was made, RUN apart, as the last point is drawn",
          len(tl["at"]) == 2 and tl["at"][0][0] == tl["points"] and tl["at"][1][0] == tl["points"] + 1
          and tl["at"][0][1] == tl["before"] and tl["at"][1][1] - tl["at"][0][1] == RUN and tl["at"][1][2],
          json.dumps(tl["at"]))
    check("the replay is RUN longer, and the length Play's badge reads says so",
          tl["last"] == T0 + RUN and tl["dur"] == T0 + RUN, f"{tl['last']} / {tl['dur']} against {T0} + {RUN}")
    S = tl["at"][0][1] if tl["at"] else T0

    # ========================================================= the Pad's Play
    print("\nTHE PAD'S PLAY — old colour, the run from the tap, the new colour; a scrub glides through it")
    q.evaluate("() => document.getElementById('playBtn').click()"); q.wait_for_timeout(120)
    q.evaluate("() => pausePlayback()"); q.wait_for_timeout(120)

    def seek(ms):
        q.evaluate(f"() => editorSeek({ms} / playTotal)"); q.wait_for_timeout(220)
        return q.evaluate(SHOWN, ["canvas#canvas", [NEAR, FAR, CROSS]])

    s0 = seek(S - 60)
    check("before the moment, the line shows its old colour", not s0["on"] and [kind(p) for p in s0["px"][:2]] == ["ink", "ink"], json.dumps(s0))
    s1 = seek(S + 60)
    check("as the colour runs, its near end shows the new colour and its far end the old, laid exactly over the drawing",
          s1["on"] and [kind(p) for p in s1["px"][:2]] == ["pink", "ink"] and s1["geo"] is not None and s1["geo"] < 0.1, json.dumps(s1))
    s2 = seek(S + 150)
    check("a scrub inside the run keeps it running", s2["on"] and [kind(p) for p in s2["px"][:2]] == ["pink", "ink"], json.dumps(s2))
    s3 = seek(S + RUN + 5)
    check("after it, the new colour all along, the line drawn later still on top where it crosses, and nothing laid over",
          not s3["on"] and [kind(p) for p in s3["px"]] == ["pink", "pink", "ink"]
          and not q.evaluate("() => !!document.querySelector('.recolor-run') && document.querySelector('.recolor-run').isConnected"),
          json.dumps(s3))
    s4 = seek(S - 60)
    check("and scrubbed back before the moment, the old colour again", not s4["on"] and [kind(p) for p in s4["px"][:2]] == ["ink", "ink"], json.dumps(s4))
    c.close()

    c = b.new_context(reduced_motion="reduce", **DESK)
    q = c.new_page()
    browsing.goto(q, BASE, "/skribl-pad")
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    q.evaluate("(d) => loadSkribl(d)", D); q.wait_for_timeout(300)
    q.evaluate("() => document.getElementById('playBtn').click()"); q.wait_for_timeout(120)
    q.evaluate("() => pausePlayback()"); q.wait_for_timeout(120)
    r1 = seek(S + 60)
    check("under Reduce Motion the colour changes at the moment, with no run", not r1["on"] and [kind(p) for p in r1["px"][:2]] == ["pink", "pink"], json.dumps(r1))
    c.close()

    # ========================================================== the link page
    print("\nTHE LINK PAGE — the module only for a drawing that has recolours; the change when it was made")
    plain_id, rc_id = post(drawing(recoloured=False)), post(drawing())
    for sid, has in ((plain_id, False), (rc_id, True)):
        c = b.new_context(**DESK)
        q = c.new_page()
        asked = []
        q.on("request", lambda r: asked.append(r.url) if "recolorplay" in r.url else None)
        q.goto(BASE + "/s/" + str(sid), wait_until="load"); q.wait_for_timeout(1500)
        loaded = q.evaluate("() => !!window.SkriblRecolorPlay")
        if not has:
            check("a drawing without recolours fetches no recolour module", not loaded and not asked, f"{loaded} {asked}")
        else:
            q.evaluate("() => document.getElementById('playerPlayBtn').click()")
            seen = phases(q.evaluate(WATCH, ["canvas#canvas", [NEAR, FAR], T0 + RUN + 300]))
            check("a recoloured drawing fetches it once, and plays the old colour, the run, then the new colour",
                  loaded and len(asked) == 1 and "ink/ink" in seen and "RUN pink/ink" in seen and seen.index("ink/ink") < seen.index("RUN pink/ink")
                  and any(k.endswith("pink/pink") for k in seen[seen.index("RUN pink/ink"):]), f"{asked} {seen}")
        c.close()

    # ======================================================== the Gallery's
    print("\nTHE GALLERY'S PLAYER — the change when it was made, the run laid over its letterboxed canvas")
    gid = post(drawing(public=True))
    for label, opts in (("desk", DESK), ("phone", PHONE)):
        c = b.new_context(**opts)
        q = c.new_page()
        q.goto(BASE + "/gallery", wait_until="load"); q.wait_for_timeout(1500)
        sel = f'[data-skribl-id="{gid}"]'
        if not q.query_selector(sel):
            check(f"on a {label}, the Gallery's player plays the change when it was made, its run laid exactly over the drawing", False, "the post is not on the Gallery")
            c.close()
            continue
        q.evaluate(f"() => document.querySelector('{sel}').scrollIntoView({{ block: 'center' }})"); q.wait_for_timeout(300)
        q.evaluate(f"() => (document.querySelector('{sel} .skribl-inline-play') || document.querySelector('{sel}')).click()")
        fr = q.evaluate(WATCH, [sel + " .skribl-inline-canvas", [NEAR, FAR], T0 + RUN + 400])
        seen, geo = phases(fr), max([f["geo"] for f in fr if f["geo"] is not None] or [99])
        check(f"on a {label}, the Gallery's player plays the change when it was made, its run laid exactly over the drawing",
              "ink/ink" in seen and "RUN pink/ink" in seen and seen.index("ink/ink") < seen.index("RUN pink/ink") and geo < 0.1,
              f"{seen} geo {geo}")
        c.close()

    # ======================================================== the server's line
    print("\nTHE SERVER'S LINE — the replay's length and shape, the run in them")
    with urllib.request.urlopen(BASE + "/api/skribls?limit=30", timeout=20) as resp:
        items = json.loads(resp.read()).get("items") or []
    line = next((it.get("line") for it in items if it.get("id") == gid), None)
    c = b.new_context(**DESK)
    q = c.new_page()
    q.goto(BASE + "/s/" + str(gid), wait_until="load"); q.wait_for_timeout(1500)
    mine = q.evaluate("""() => { const t = buildPlaybackTimeline(), T = t[t.length - 1].playT || 1, n = 128, c = new Array(n).fill(0);
        for (let k = 1; k < t.length; k++) { if (t[k].start) continue;
          c[Math.min(n - 1, Math.floor(t[k].playT / T * n))] += Math.hypot(t[k].x - t[k - 1].x, t[k].y - t[k - 1].y); }
        const top = Math.max(...c), D = '0123456789abcdefghijklmnopqrstuvwxyz';
        return { play: t[t.length - 1].playT, shape: c.map(v => (top && v) ? D[Math.max(1, Math.round(Math.sqrt(v / top) * 35))] : '0').join('') }; }""")
    check("the line under a post says the replay's length and shape, with the colour's run in them",
          bool(line) and line.get("play") == mine["play"] == T0 + RUN and line.get("shape") == mine["shape"],
          f"server {json.dumps(line)[:160]} / replay {mine['play']}")
    c.close()

    # ====================================================== the scrubber's dots
    print("\nTHE SCRUBBER'S DOTS — the new colour mid-run, half ahead and whole once played, ringed only where it would not read")
    # The dot's middle and its rim on the bar's own canvas (lib/replayline.js
    # scrub()), at the run's middle: the colour there, how strong, and whether
    # the rim leans to the bar's purple (a ring) or stays the dot's pink.
    DOT = """([sel, f]) => { const cv = document.querySelector(sel + ' .rl-strip'); if (!cv || !cv.width) return null;
      const x = cv.getContext('2d'), cx = Math.round(f * cv.width), cy = Math.floor(cv.height / 2), d = Math.min(2, devicePixelRatio || 1);
      const at = (dx) => Array.from(x.getImageData(cx + dx, cy, 1, 1).data);
      const rims = [3, 4].map(k => at(Math.round(k * d)));
      return { mid: at(0), rim: Math.max(...rims.map(c => c[3] ? c[2] - c[0] : -999)) }; }"""
    F = (T0 + RUN / 2) / (T0 + RUN)
    pink = lambda c: bool(c) and c[0] > 200 and c[1] < 130 and c[2] > 120
    sid = post(D)
    for scheme in ("light", "dark"):
        c = b.new_context(color_scheme=scheme, **DESK)
        q = c.new_page()
        q.goto(BASE + "/s/" + str(sid), wait_until="load"); q.wait_for_timeout(1500)
        ahead = q.evaluate(DOT, ["#playerProgress", F])
        r = q.evaluate("() => { const r = document.getElementById('playerProgress').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        q.mouse.click(r[0] + r[2] - 1, r[1] + r[3] / 2); q.wait_for_timeout(500)
        played = q.evaluate(DOT, ["#playerProgress", F])
        ringed = scheme == "light"
        check(f"the link page, {scheme}: a pink dot mid-run, half as strong ahead and whole once played, "
              + ("ringed in the bar's purple (pink is 2.7:1 on this track)" if ringed else "with no ring (pink reads at 5.9:1 here)"),
              bool(ahead) and bool(played) and pink(ahead["mid"]) and 100 <= ahead["mid"][3] <= 160 and pink(played["mid"])
              and played["mid"][3] >= 240 and ((played["rim"] > 0) if ringed else (played["rim"] < 0)),
              f"ahead {ahead}, played {played}")
        c.close()
    c = b.new_context(**DESK)
    q = c.new_page()
    browsing.goto(q, BASE, "/skribl-pad")
    q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
    q.evaluate("(d) => loadSkribl(d)", D); q.wait_for_timeout(300)
    q.evaluate("() => document.getElementById('playBtn').click()"); q.wait_for_timeout(200)
    q.evaluate("() => { pausePlayback(); editorSeek(1); }"); q.wait_for_timeout(400)
    pad = q.evaluate(DOT, ["#playScrub", F])
    check("the Pad's own preview has the dot too, whole once played", bool(pad) and pink(pad["mid"]) and pad["mid"][3] >= 240, json.dumps(pad))
    c.close()

    # ============================================================== the exports
    print("\nTHE EXPORTS — a GIF and a video show the old colour, the run and the new colour")

    def pad_with(d):
        c = b.new_context(accept_downloads=True, **DESK)
        q = c.new_page()
        browsing.goto(q, BASE, "/skribl-pad")
        q.evaluate("() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
        q.evaluate("(d) => loadSkribl(d)", d); q.wait_for_timeout(300)
        return c, q

    def frame_at(frames, fps, ms, pt, size):
        f = frames[min(len(frames) - 1, int(ms * fps / 1000))]
        W, H = f.size
        return kind(f.getpixel((int(pt[0] / size[0] * W), int(pt[1] / size[1] * H))))

    c, q = pad_with(D)
    q.evaluate("() => document.getElementById('exportItem').click()"); q.wait_for_timeout(400)
    with q.expect_download(timeout=60000) as dl:
        q.evaluate("() => document.getElementById('exportGif').click()")
    gif = [f.convert("RGB").copy() for f in ImageSequence.Iterator(Image.open(dl.value.path()))]
    got = [(frame_at(gif, 15, ms, NEAR, (816, 612)), frame_at(gif, 15, ms, FAR, (816, 612))) for ms in (S - 100, S + 60, S + RUN + 100)]
    check("a GIF shows the old colour, the run, then the new colour, at their moments",
          got == [("ink", "ink"), ("pink", "ink"), ("pink", "pink")], json.dumps(got))
    c.close()

    if shutil.which("ffmpeg"):
        c, q = pad_with(D)
        with q.expect_download(timeout=60000) as dl:
            q.evaluate("() => { document.getElementById('exportItem').click(); setTimeout(() => document.getElementById('exportVideo').click(), 300); }")
        tmp = tempfile.mkdtemp()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", dl.value.path(), "-vsync", "0", os.path.join(tmp, "f%04d.png")], check=True)
        vid = [Image.open(p).convert("RGB") for p in sorted(glob.glob(os.path.join(tmp, "f*.png")))]
        got = [(frame_at(vid, 30, ms, NEAR, (816, 612)), frame_at(vid, 30, ms, FAR, (816, 612))) for ms in (S - 100, S + 60, S + RUN + 100)]
        check("a video shows them too", got == [("ink", "ink"), ("pink", "ink"), ("pink", "pink")], json.dumps(got))
        shutil.rmtree(tmp, ignore_errors=True)
        c.close()
    else:
        print("  (not checked here: the video's frames need ffmpeg, which this machine does not have)")

    # ================================================== the bead in the files
    print("\nTHE BEAD IN THE FILES — the glowing dot rides the line, sits on the tap while a colour runs, gone at the end")

    def probe(f, x, y, s):
        return f.getpixel((max(0, min(f.size[0] - 1, int(round(x * s)))), max(0, min(f.size[1] - 1, int(round(y * s))))))[:3]

    def bead_reads(frames):
        """Over a file's frames: the bead's tint at the long line's tip on each
        frame that has it part-drawn; at the tap on each frame with the colour
        part-run; and at both places on the last frame. A tint is how far the
        ground just over the line has moved from the ground."""
        W = frames[0].size[0]
        s = W / 816
        g = probe(frames[-1], 300, 110, s)                      # ground in every frame
        tint = lambda c: sum(abs(a - b_) for a, b_ in zip(c, g))
        lift = lambda size: (size / 2 + 0.95 * size) / 2       # between the line's edge and the bead's
        tips, taps = [], []
        for f in frames:
            row = [x for x in range(int(40 * s), int(492 * s)) if kind(f.getpixel((x, int(round(30 * s))))) == "ink"]
            if row and 100 * s < row[-1] - 6 * s < 430 * s:
                tips.append(tint(probe(f, (row[-1] - 6 * s) / s, 30 - lift(12), s)))
            near, far = kind(probe(f, 150, 200, s)), kind(probe(f, 470, 200, s))
            if near == "pink" and far == "ink":
                c = probe(f, 151.3, 200 - lift(14), s)
                taps.append(c[0] - c[1])                            # pink: red well over green; the ground has neither
        end = [tint(probe(frames[-1], 490, 30 - lift(12), s)), tint(probe(frames[-1], 151.3, 200 - lift(14), s))]
        return tips, taps, end, g

    def _png_rgb(url):
        import base64 as _b64
        return Image.open(io.BytesIO(_b64.b64decode(url.split(",", 1)[1]))).convert("RGB")

    def bead_ok(r):
        tips, taps, end, _ = r
        return (len(tips) >= 3 and sum(t > 60 for t in tips) >= 0.9 * len(tips) and len(taps) >= 2
                and sum(t > 25 for t in taps) >= 0.9 * len(taps) and max(end) < 30)

    def bead_say(r):
        tips, taps, end, g = r
        return (f"ground {g}; at the tip on {len(tips)} frames {sorted(tips)[:4]}..{sorted(tips)[-2:]}; "
                f"on the tap on {len(taps)} frames {sorted(taps)}; the last frame {end}")

    c, q = pad_with(D)
    q.evaluate("() => document.getElementById('exportItem').click()"); q.wait_for_timeout(400)
    with q.expect_download(timeout=60000) as dl:
        q.evaluate("() => document.getElementById('exportGif').click()")
    r = bead_reads([f.convert("RGB").copy() for f in ImageSequence.Iterator(Image.open(dl.value.path()))])
    check("a GIF's bead rides the line's tip, sits on the tap while the colour runs, and is gone at the end", bead_ok(r), bead_say(r))
    c.close()
    if shutil.which("ffmpeg"):
        c, q = pad_with(D)
        with q.expect_download(timeout=60000) as dl:
            q.evaluate("() => { document.getElementById('exportItem').click(); setTimeout(() => document.getElementById('exportVideo').click(), 300); }")
        tmp = tempfile.mkdtemp()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", dl.value.path(), "-vsync", "0", os.path.join(tmp, "f%04d.png")], check=True)
        r = bead_reads([Image.open(p).convert("RGB") for p in sorted(glob.glob(os.path.join(tmp, "f*.png")))])
        check("a video's bead does the same", bead_ok(r), bead_say(r))
        shutil.rmtree(tmp, ignore_errors=True)
        c.close()
    else:
        print("  (not checked here: the video's frames need ffmpeg, which this machine does not have)")
    # THE MP4 PATH, the one a desk's Chrome or Edge takes (WebCodecs; the owner's
    # own video came from it). Headless Chromium here cannot encode H.264, so a
    # stand-in encoder runs the path's own frames and keeps each one: what is
    # read is what the real encoder would have been handed.
    c, q = pad_with(D)
    q.evaluate("""() => { window.__frames = []; window.SkriblMp4 = Object.assign({}, window.SkriblMp4, {
        prepare: async (w, h) => ({ w: w, h: h }),
        encode: async (o) => { const n = Math.max(1, Math.ceil(o.durationSec * 30));   // lib/mp4export.js's own stepping
          for (let f = 0; f < n; f++) { await o.drawFrame(f, f === n - 1); window.__frames.push(o.canvas.toDataURL('image/png')); }
          return new ArrayBuffer(8); } }); }""")
    with q.expect_download(timeout=60000):
        q.evaluate("() => { document.getElementById('exportItem').click(); setTimeout(() => document.getElementById('exportVideo').click(), 300); }")
    r = bead_reads([_png_rgb(u) for u in q.evaluate("() => window.__frames")])
    check("the MP4 path's frames (the desk's Chrome and Edge) carry it the same way", bead_ok(r), bead_say(r))
    c.close()

    # A base drawn before the first take: a solid block, then see-through ink.
    c, q = pad_with(drawing(recoloured=False))
    block = q.evaluate("""() => { const k = document.createElement('canvas'); k.width = canvas.width; k.height = canvas.height;
        const x = k.getContext('2d'); x.fillStyle = '#1f1b2e'; x.fillRect(0, 0, k.width * 120 / 816, k.height * 120 / 612); return k.toDataURL(); }""")
    q.evaluate("(d) => loadSkribl(d)", drawing(recoloured=False, base=block, see_through=True)); q.wait_for_timeout(400)
    q.evaluate("() => document.getElementById('exportItem').click()"); q.wait_for_timeout(400)
    with q.expect_download(timeout=60000) as dl:
        q.evaluate("() => document.getElementById('exportGif').click()")
    gif = [f.convert("RGB").copy() for f in ImageSequence.Iterator(Image.open(dl.value.path()))]
    kept = [frame_at([f], 15, 0, (40, 40), (816, 612)) for f in (gif[0], gif[len(gif) // 2], gif[-1])]
    check("a GIF keeps a base drawn before the first take, with see-through layering on", kept == ["ink"] * 3, json.dumps(kept))
    c.close()

    b.close()

summarise_and_exit()
