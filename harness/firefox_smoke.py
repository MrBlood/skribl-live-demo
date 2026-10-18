#!/usr/bin/env python3
"""Skribl in Firefox: the one browser engine nothing else here drives.

THE OWNER'S CALL, after the v325 outside review asked for a wider browser
list ("all yes"): a Firefox check on the full run GitHub makes after each
merge, so a pull request stays quiet. It costs nothing (ubuntu-latest, a
public repository). The build container has no Firefox, so its first real
run is CI's.

A SMOKE, NOT A SECOND BATTERY. The suites are written to Chromium -- real
touches through CDP, its pixels for goldens, Chrome's encoders -- and a port
of them would be a second harness to keep in step with the first. This asks
what someone opening Skribl in Firefox meets first, and reads each answer
from the thing itself:

  * the Pad, Flip, the Gallery, the Library and a share link load and boot,
    and no page throws;
  * a stroke on each editor leaves ink: the drawing's own data, and pixels on
    its canvas that differ from its ground;
  * each editor posts through its own sheet, ticked public; the Pad's link
    plays (its slider moves) and shows ink; the Gallery shows both posts; the
    Library, in the same browser, lists both;
  * each editor's video is a real file with frames in it, counted in the file
    (WebM blocks, or an MP4's video samples, whichever Firefox makes).

NOT A verify_ SUITE, on purpose: a bare run or a seal here could only skip
it, and a skip proves nothing. CI's firefox job installs Firefox, runs this
through run_harness.sh, and fails when it skipped.
"""
import math
import os
import sys

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

# INK: pixels of the canvas's backing store that differ from its own corner
# (its ground) by more than a faint grid line, sampled every fourth pixel.
INK = """(sel) => { const c = document.querySelector(sel), x = c.getContext('2d');
  const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 0; i < d.length; i += 16)
    if (Math.abs(d[i] - d[0]) + Math.abs(d[i + 1] - d[1]) + Math.abs(d[i + 2] - d[2]) + Math.abs(d[i + 3] - d[3]) > 90) n++;
  return n; }"""

# EBML ids (verify_videoexport.py walks the same): containers entered, leaves read.
SEGMENT, CLUSTER, TRACKS, TRACKENTRY, BLOCKGROUP = 0x18538067, 0x1F43B675, 0x1654AE6B, 0xAE, 0xA0
TRACKNUMBER, TRACKTYPE, SIMPLEBLOCK, BLOCK = 0xD7, 0x83, 0xA3, 0xA1


def _vint(b, i, marker):
    first, mask, n = b[i], 0x80, 1
    while n <= 8 and not first & mask:
        mask >>= 1
        n += 1
    v = first if marker else first & (mask - 1)
    for k in range(1, n):
        v = (v << 8) | b[i + k]
    return v, n


def webm_frames(data):
    """Blocks on the WebM's video track (TrackType 1): one per frame encoded."""
    types, blocks, cur, i = {}, {}, {}, 0
    while i < len(data) - 2:
        try:
            eid, a = _vint(data, i, True)
            size, b = _vint(data, i + a, False)
        except IndexError:
            break
        body = i + a + b
        if eid in (SEGMENT, CLUSTER, TRACKS, BLOCKGROUP, TRACKENTRY):
            if eid == TRACKENTRY and cur.get("n"):
                types[cur["n"]] = cur.get("t")
            if eid == TRACKENTRY:
                cur = {}
            i = body
            continue
        if eid in (TRACKNUMBER, TRACKTYPE):
            cur["n" if eid == TRACKNUMBER else "t"] = int.from_bytes(data[body:body + size], "big")
        elif eid in (SIMPLEBLOCK, BLOCK):
            tn, _ = _vint(data, body, False)
            blocks[tn] = blocks.get(tn, 0) + 1
        i = body + size
    if cur.get("n"):
        types[cur["n"]] = cur.get("t")
    return sum(c for n, c in blocks.items() if types.get(n) == 1)


def _boxes(b, i, end):
    while i + 8 <= end:
        size, hdr = int.from_bytes(b[i:i + 4], "big"), 8
        if size == 1:
            size, hdr = int.from_bytes(b[i + 8:i + 16], "big"), 16
        elif size == 0:
            size = end - i
        if size < hdr:
            return
        yield b[i + 4:i + 8], i + hdr, i + size
        i += size


def mp4_frames(data):
    """Samples in the MP4's video track: its handler says 'vide', its stsz counts them."""
    n = 0
    for t, s, e in _boxes(data, 0, len(data)):
        if t != b"moov":
            continue
        for t2, s2, e2 in _boxes(data, s, e):
            if t2 != b"trak":
                continue
            handler, count, todo = None, 0, [(s2, e2)]
            while todo:
                a, z = todo.pop()
                for t3, s3, e3 in _boxes(data, a, z):
                    if t3 in (b"mdia", b"minf", b"stbl"):
                        todo.append((s3, e3))
                    elif t3 == b"hdlr":
                        handler = data[s3 + 8:s3 + 12]
                    elif t3 == b"stsz":
                        count = int.from_bytes(data[s3 + 8:s3 + 12], "big")
            if handler == b"vide":
                n += count
    return n


TIMECODE = 0xE7


def webm_blocks(data):
    """When each video frame lands in a WebM (its cluster's time and its own,
    in ms) and how many bytes it takes: a repeated or blank frame is a small
    one."""
    types, found, cur, i, base = {}, [], {}, 0, 0
    while i < len(data) - 2:
        try:
            eid, a = _vint(data, i, True)
            size, b = _vint(data, i + a, False)
        except IndexError:
            break
        body = i + a + b
        if eid in (SEGMENT, CLUSTER, TRACKS, BLOCKGROUP, TRACKENTRY):
            if eid == TRACKENTRY and cur.get("n"):
                types[cur["n"]] = cur.get("t")
            if eid == TRACKENTRY:
                cur = {}
            i = body
            continue
        if eid in (TRACKNUMBER, TRACKTYPE):
            cur["n" if eid == TRACKNUMBER else "t"] = int.from_bytes(data[body:body + size], "big")
        elif eid == TIMECODE:
            base = int.from_bytes(data[body:body + size], "big")
        elif eid in (SIMPLEBLOCK, BLOCK):
            try:
                tn, c = _vint(data, body, False)
                found.append((tn, base + int.from_bytes(data[body + c:body + c + 2], "big", signed=True), size))
            except IndexError:
                break
        i = body + size
    if cur.get("n"):
        types[cur["n"]] = cur.get("t")
    return [(t, n) for tn, t, n in found if types.get(tn) == 1]


def video(data):
    """(the file's kind, its video frames), read from its own structure."""
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm", webm_frames(data)
    if data[4:8] == b"ftyp":
        return "mp4", mp4_frames(data)
    return "neither", 0


def draw(pg, sel):
    """One long stroke, as a hand makes it: down, sixty moves, up."""
    box = pg.locator(sel).bounding_box()
    x0, y0 = box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.4
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    for i in range(60):
        pg.mouse.move(x0 + i * box["width"] * 0.01, y0 + math.sin(i / 6) * box["height"] * 0.12)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    pg.wait_for_timeout(300)


# Each page's console errors and warnings, for a failure to quote.
LOGS = {}

# What the page shows while a video is made: the toast or chip, and each
# editor's progress (its words and how far its bar is).
SAID = """() => { const t = (id) => document.getElementById(id);
  const words = (id) => t(id) && (id + ': ' + (t(id).hidden ? '(hidden) ' : '') + t(id).textContent.replace(/\\s+/g, ' ').trim().slice(0, 120));
  const bar = (id) => t(id) && (id + ' at ' + (t(id).style.width || '0%'));
  return [words('toast'), words('flipChip'), words('exportProgress'), bar('exportProgressFill'), words('flipExport'), bar('flipExportFill')]
    .filter(Boolean).join(' | '); }"""

# Puts away what a stalled export leaves over the page (the Pad's sheet, Flip's
# progress), so the steps after it still run.
UNSTICK = """() => { const o = document.getElementById('exportOverlay');
  if (o && !o.hidden) document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  const f = document.getElementById('flipExport');
  if (f && !f.hidden) { f.hidden = true; if (typeof exporting !== 'undefined') exporting = false; } }"""

# What this browser offers a video: the MP4 path (WebCodecs, H.264) or the
# recorder's (MediaRecorder, WebM), which recorder types it takes, and where
# its requestFrame is (Chromium's is on the track, Gecko's on the stream).
OFFERS = """async () => { const t = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
  let avc = 'no VideoEncoder';
  if (typeof VideoEncoder !== 'undefined') {
    try { avc = (await VideoEncoder.isConfigSupported({ codec: 'avc1.42001f', width: 816, height: 612, bitrate: 6000000, framerate: 30 })).supported ? 'H.264 yes' : 'H.264 no'; }
    catch (e) { avc = 'H.264 threw ' + e.name; } }
  const has = (k) => typeof window[k] !== 'undefined' && 'requestFrame' in window[k].prototype;
  return 'WebCodecs: ' + avc + '; MediaRecorder: ' + (typeof MediaRecorder === 'undefined' ? 'none'
    : t.filter(x => MediaRecorder.isTypeSupported(x)).join(', ') || 'no type')
    + '; requestFrame: ' + (has('CanvasCaptureMediaStreamTrack') ? 'on the track' : has('CanvasCaptureMediaStream') ? 'on the stream' : 'none'); }"""


def export(pg, opener):
    """The editor's own Export sheet, Video: the bytes it downloads. When none
    comes, it prints what the page said instead and what it logged, and puts
    the stalled export away so the steps after it still run."""
    pg.evaluate("(id) => document.getElementById(id).click()", opener)
    pg.wait_for_selector("#exportVideo", state="visible", timeout=5000)
    try:
        with pg.expect_download(timeout=60000) as dl:
            pg.click("#exportVideo")
    except Exception as e:
        print(f"    the page says: {pg.evaluate(SAID)}")
        for line in LOGS.get(id(pg), [])[-6:] or ["nothing"]:
            print(f"    it logged: {line}")
        pg.evaluate(UNSTICK)
        pg.wait_for_timeout(400)
        raise RuntimeError(f"no video ({type(e).__name__}: {str(e).splitlines()[0][:120]})") from e
    data = open(dl.value.path(), "rb").read()
    pg.evaluate("() => { const o = document.getElementById('exportOverlay'); if (o && !o.hidden) document.getElementById('exportCancel').click(); }")
    pg.wait_for_timeout(400)
    return dl.value.suggested_filename, data


def post(pg, title, tick):
    """The editor's own Post sheet, ticked public: the share link it answers with."""
    pg.click("#postBtn")
    pg.wait_for_selector("#postTitleInput", state="visible", timeout=5000)
    pg.fill("#postTitleInput", title)
    pg.click(tick)
    ticked = pg.evaluate("() => document.getElementById('postPublicInput').checked")
    res = browsing.submit_post(pg)
    return ticked, res


# THE ENGINE IS FIREFOX. SKRIBL_SMOKE_ENGINE=chromium runs the same steps on
# Chromium, which is how this file is checked where there is no Firefox: the
# steps must hold on the engine the battery already trusts before a red here
# can be read as Firefox's.
ENGINE = os.environ.get("SKRIBL_SMOKE_ENGINE", "firefox")


def section(name, run):
    """Run one page's steps; a step that throws is a failed check that says
    where, so one broken page does not hide what the others found."""
    try:
        run()
    except Exception as e:
        check(f"{name}: every step ran", False, f"{type(e).__name__}: {str(e).splitlines()[0][:240]}")


# THE PLAN: how many beats each editor's video is made of, asked of the page
# before it exports. The recorder pushes one frame per beat (lib/videorecord.js,
# ONE FRAME PER TICK), so a WebM holds exactly that many; a recorder that only
# samples the canvas holds fewer. Flip's 12 a second are five screen refreshes
# apart, so they hold exactly in Gecko too. The Pad's 30 are two apart, and
# Gecko takes a pushed frame at its next refresh, one per refresh, so on a busy
# machine two can merge (63 of 82, then 47 of 78, on CI: about 18 a second
# however they are asked for); the Pad is held to never more than
# its beats, which still catches a doubled first frame. And once, on main
# after #533, Gecko made Flip one frame more than its beats (5 of 4, where the
# runs before made 4 of 4). Until where that frame sits is known, Flip is held
# to every beat and at most one more, and each frame's time and size is
# printed. An MP4 is made elsewhere (lib/mp4export.js) and is only asked for
# frames.
PAD_PLAN = """() => { const t = buildPlaybackTimeline(), ms = t.length ? t[t.length - 1].playT : 0;
  return Math.ceil(ms * 30 / 1000) + 1 + Math.round(700 * 30 / 1000); }"""
FLIP_PLAN = "() => { const r = exRange(); return exportUnits(r.from - 1, r.to - 1).length * exLoops; }"


def filmed(pg, opener, name, plan, also=True, exact=True, slack=0, show=False):
    """The editor's video, checked against its plan: a WebM holds a frame for
    every beat and at most `slack` more (exact), or never more than its beats.
    `show` prints each frame's time and size. A video that never comes fails
    this check alone: the post after it still runs."""
    want = pg.evaluate(plan)
    try:
        fname, data = export(pg, opener)
    except Exception as e:
        check(name, False, f"{type(e).__name__}: {str(e).splitlines()[0][:240]}")
        return
    kind, n = video(data)
    ok = (want <= n <= want + slack if exact else 3 < n <= want) if kind == "webm" else n > 3
    if show and kind == "webm":
        print("    its frames (ms: bytes): " + ", ".join(f"{t}: {b:,}" for t, b in webm_blocks(data)))
    check(name, also and ok and len(data) > 1000,
          f"{fname}: {kind}, {n} video frames of {want} planned, {len(data):,} B")


with sync_playwright() as p:
    try:
        b = getattr(p, ENGINE).launch()
    except Exception as e:   # no build of it installed: CI's job installs one
        print(f"SKIP: {ENGINE} is not installed ({str(e).splitlines()[0][:120]})")
        sys.exit(0)
    print(f"{ENGINE} {b.version}")
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    errs = []
    hide = "() => { if (window.SkriblHints) window.SkriblHints.hide(); }"
    got = {"pad": "", "flip": ""}

    def page(path):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(f"{path}: {e}"))
        mine = LOGS.setdefault(id(pg), [])
        pg.on("console", lambda m: mine.append(f"{m.type}: {m.text[:400]}") if m.type in ("error", "warning") else None)
        browsing.goto(pg, BASE, path)
        pg.evaluate(hide)
        return pg

    def pad():
        pg = page("/")
        print(f"  ({ENGINE} offers: {pg.evaluate(OFFERS)})")
        draw(pg, "#canvas")
        pts, ink = pg.evaluate("() => strokes.length"), pg.evaluate(INK, "#canvas")
        check("the Pad boots, and a stroke is drawing data and ink on its canvas",
              pts > 10 and ink > 50, f"{pts} points, {ink} ink samples")
        pg.click("#recordBtn")
        pg.wait_for_timeout(400)
        pg.click("#playBtn")
        pg.wait_for_timeout(600)
        check("...its replay plays, with the scrubber up",
              pg.evaluate("() => playing && !document.getElementById('playScrub').hidden"))
        pg.evaluate("() => { if (playing) document.getElementById('playBtn').click(); }")
        pg.wait_for_timeout(400)
        filmed(pg, "exportItem", "...its video is a real file, never more frames than its replay's beats", PAD_PLAN,
               exact=False)
        ticked, res = post(pg, "Firefox smoke, Pad", ".post-check")
        got["pad"] = res["url"] or ""
        check("...and it posts through its own sheet, ticked public, and gets its link",
              ticked and "/s/" in got["pad"], str(res))
        pg.close()

    def flip():
        pg = page("/flip")
        draw(pg, "#pad")
        pts, ink = pg.evaluate("() => frames[0].strokes.length"), pg.evaluate(INK, "#pad")
        check("Flip boots, and a stroke is drawing data and ink on its page",
              pts > 10 and ink > 50, f"{pts} points, {ink} ink samples")
        # A second page: a one-page Flip is a picture, and its Video is off.
        pg.click("#addblank")
        pg.wait_for_timeout(300)
        draw(pg, "#pad")
        filmed(pg, "miExport", "...its two pages make a real video file, a frame for every beat and at most one more",
               FLIP_PLAN, also=pg.evaluate("() => frames.length") == 2, slack=1, show=True)
        ticked, res = post(pg, "Firefox smoke, Flip", "#postSheet .post-check")
        got["flip"] = res["url"] or ""
        check("...and it posts through its own sheet, ticked public, and gets its link",
              ticked and "/s/" in got["flip"], str(res))
        pg.close()

    def link():
        pid = got["pad"].rstrip("/").split("/")[-1]
        check("(the Pad's post gave a link to open)", bool(pid), repr(got["pad"]))
        if not pid:
            return
        pg = page("/s/" + pid)
        pg.click("#playerPlayBtn")
        pg.wait_for_timeout(1500)
        now = pg.evaluate("() => +document.getElementById('playerProgress').getAttribute('aria-valuenow')")
        ink = pg.evaluate(INK, "#canvas")
        check("the Pad's link boots and plays: its slider moves, and the drawing has ink",
              now > 0 and ink > 50, f"at {now}%, {ink} ink samples")
        pg.close()

    def pages():
        ids = [u.rstrip("/").split("/")[-1] for u in (got["pad"], got["flip"])]
        pg = page("/gallery")
        pg.wait_for_timeout(600)
        tiles = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].map(t => t.getAttribute('data-id'))")
        check("the Gallery boots and shows both posts", all(i and i in tiles for i in ids),
              f"{len(tiles)} tiles; looking for {ids}")
        pg.close()
        pg = page("/library")
        pg.wait_for_timeout(900)
        listed = pg.inner_text("#postedList")
        check("the Library boots and lists both, in the browser that posted them",
              "Firefox smoke, Pad" in listed and "Firefox smoke, Flip" in listed, listed[:160])
        pg.close()

    print("\nTHE PAD")
    section("the Pad", pad)
    print("\nFLIP")
    section("Flip", flip)
    print("\nTHE LINK")
    section("the link", link)
    print("\nTHE GALLERY AND THE LIBRARY")
    section("the Gallery and the Library", pages)
    check("no page threw, on any of them", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
