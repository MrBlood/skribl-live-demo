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
