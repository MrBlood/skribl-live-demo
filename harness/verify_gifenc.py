"""v104 — gifenc is VENDORED, so GIF export can finally be exercised in-sandbox.

Both surfaces used to pull gifenc from jsdelivr as an ESM module. jsdelivr is
blocked here, so `window.gifenc` was always undefined and every prior handoff had
to list GIF export as "not verified — needs a real browser". Upstream ships ESM +
CJS only, neither of which loads as a classic <script>, so vendoring meant
building a global-publishing IIFE from the published tarball's own src (see the
banner in static/skribl/gifenc.min.js for the exact reproduce command).

Unlike verify_muxer.py — which can only test the MP4 capability GATE, because
headless Chromium here has VideoEncoder but no avc1 — this suite runs the encoder
for real: it drives the export UI on both surfaces, captures the downloaded file,
and parses the GIF byte stream (dimensions, frame count, loop extension, delays,
transparency + disposal flags). That closes the oldest gap in the handoff.
"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

_GIFENC = os.path.join(os.path.dirname(__file__), "..", "static", "skribl", "gifenc.min.js")
if not os.path.exists(_GIFENC):
    sys.exit("SKIP: static/skribl/gifenc.min.js not present.\n"
             "      Build it from npm — see harness/README.md, or the banner\n"
             "      comment in the file itself, for the reproduce command.")

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def parse_gif(b):
    """Minimal GIF89a walker: enough to assert what the exporter claims to write.

    Returns screen size, per-frame size + graphic-control flags, and the
    NETSCAPE2.0 loop count. Raises on anything it doesn't recognise, so a
    truncated or malformed export fails loudly instead of silently passing.
    """
    if b[:6] not in (b"GIF89a", b"GIF87a"):
        raise ValueError(f"bad signature {b[:6]!r}")
    w = b[6] | (b[7] << 8)
    h = b[8] | (b[9] << 8)
    flags = b[10]
    pos = 13
    gct = 0
    if flags & 0x80:                                  # global colour table
        gct = 2 ** ((flags & 7) + 1)
        pos += 3 * gct
    frames, loop, gce = [], None, None
    while pos < len(b):
        blk = b[pos]
        if blk == 0x21:                               # extension
            label = b[pos + 1]
            pos += 2
            size = b[pos]
            data = b[pos + 1:pos + 1 + size]
            pos += 1 + size
            sub = []
            while b[pos]:                             # sub-blocks -> terminator
                n = b[pos]
                sub.append(b[pos + 1:pos + 1 + n])
                pos += 1 + n
            pos += 1
            if label == 0xF9:                         # graphic control
                gce = {"transparent": bool(data[0] & 1),
                       "dispose": (data[0] >> 2) & 7,
                       "delay_cs": data[1] | (data[2] << 8),
                       "tindex": data[3]}
            elif label == 0xFF and data[:11] == b"NETSCAPE2.0" and sub:
                if sub[0][0] == 1:
                    loop = sub[0][1] | (sub[0][2] << 8)
        elif blk == 0x2C:                             # image descriptor
            fw = b[pos + 5] | (b[pos + 6] << 8)
            fh = b[pos + 7] | (b[pos + 8] << 8)
            lflags = b[pos + 9]
            pos += 10
            local = 0
            if lflags & 0x80:                         # local colour table
                local = 2 ** ((lflags & 7) + 1)
                pos += 3 * local
            pos += 1                                  # LZW minimum code size
            while b[pos]:                             # image data sub-blocks
                pos += 1 + b[pos]
            pos += 1
            frames.append({"w": fw, "h": fh, "local_palette": local, "gce": gce})
            gce = None
        elif blk == 0x3B:                             # trailer
            break
        else:
            raise ValueError(f"unknown block 0x{blk:02x} at offset {pos}")
    return {"w": w, "h": h, "gct": gct, "frames": frames, "loop": loop}


def draw(page, sel, x0, y0, n=24, dy=0):
    box = page.locator(sel).bounding_box()
    page.mouse.move(box["x"] + x0, box["y"] + y0)
    page.mouse.down()
    for i in range(n):
        page.mouse.move(box["x"] + x0 + i * 6, box["y"] + y0 + dy + (i % 5) * 4)
    page.mouse.up()
    page.wait_for_timeout(120)


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)

    API = """() => ({
        hasGlobal: typeof window.gifenc !== 'undefined',
        hasEncoder: typeof (window.gifenc||{}).GIFEncoder === 'function',
        hasQuantize: typeof (window.gifenc||{}).quantize === 'function',
        hasApply: typeof (window.gifenc||{}).applyPalette === 'function'
    })"""

    print("\nVENDORED GIFENC — loads with the CDN unreachable")
    flip_errors, pad_errors = [], []
    flip_reqs, pad_reqs = [], []
    flip = ctx.new_page()
    flip.on("pageerror", lambda e: flip_errors.append(str(e)))
    flip.on("request", lambda r: flip_reqs.append(r.url))
    flip.goto(BASE + "/flip", wait_until="load")
    flip.wait_for_timeout(1200)

    f = flip.evaluate(API)
    check("Flip exposes window.gifenc", f["hasGlobal"])
    check("Flip has GIFEncoder / quantize / applyPalette",
          f["hasEncoder"] and f["hasQuantize"] and f["hasApply"], str(f))
    check("no Flip page errors from the vendored script", not flip_errors,
          "; ".join(flip_errors[:2]))

    pad = ctx.new_page()
    pad.on("pageerror", lambda e: pad_errors.append(str(e)))
    pad.on("request", lambda r: pad_reqs.append(r.url))
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(1200)
    d = pad.evaluate(API)
    check("Pad exposes the same global", d["hasGlobal"] and d["hasEncoder"])
    check("both surfaces agree on the API shape", f == d, f"flip {f} vs pad {d}")
    check("no Pad page errors", not pad_errors, "; ".join(pad_errors[:2]))

    print("\nORIGIN — nothing third-party is fetched any more")
    for label, reqs in (("Flip", flip_reqs), ("Pad", pad_reqs)):
        cdn = [u for u in reqs if "gifenc" in u and "jsdelivr" in u]
        local = [u for u in reqs if "gifenc" in u and "127.0.0.1" in u]
        check(f"{label}: no CDN request for gifenc", not cdn, str(cdn[:1]))
        check(f"{label}: gifenc served from our own origin", bool(local),
              local[0].split("/")[-1] if local else "none")
    # The CSP payoff: with both libraries vendored there is no off-origin script
    # left, so script-src can drop cdn.jsdelivr.net entirely (INTEGRATION §7).
    offsite = [u for u in flip_reqs + pad_reqs
               if not u.startswith(BASE) and not u.startswith("data:") and not u.startswith("blob:")]
    check("zero off-origin requests across both surfaces", not offsite, str(offsite[:2]))

    print("\nREAL GIF — Flip, opaque (the encoder actually runs)")
    flip.evaluate("() => { addFrame(); }")
    draw(flip, "#pad", 90, 90)
    flip.evaluate("() => { addFrame(); }")
    draw(flip, "#pad", 120, 140)
    flip.evaluate("() => { addFrame(); }")
    draw(flip, "#pad", 150, 190)
    n_pages = flip.evaluate("() => frames.length")
    fps = flip.evaluate("() => fps")
    check("Flip has multiple pages to encode", n_pages >= 3, f"{n_pages} pages @ {fps}fps")

    flip.evaluate("() => openExportSheet()")
    flip.wait_for_timeout(400)
    gif_state = flip.evaluate("""() => ({
        disabled: document.getElementById('exportGif').disabled,
        desc: (document.getElementById('exportGifDesc')||{}).textContent })""")
    check("GIF button is enabled, not gated off", not gif_state["disabled"], str(gif_state))
    check("GIF description no longer blames the connection",
          "connection" not in (gif_state["desc"] or "").lower(), repr(gif_state["desc"]))

    with flip.expect_download(timeout=60000) as dl:
        flip.click("#exportGif")
    got = dl.value
    check("Flip download is named skribl-flip.gif", got.suggested_filename == "skribl-flip.gif",
          got.suggested_filename)
    raw = open(got.path(), "rb").read()
    g = parse_gif(raw)
    check("bytes are a valid GIF89a", raw[:6] == b"GIF89a", f"{len(raw)} bytes")
    check("screen size is the 480px-max-edge downscale", (g["w"], g["h"]) == (480, 345),
          f"{g['w']}x{g['h']}")
    check("one GIF frame per page", len(g["frames"]) == n_pages,
          f"{len(g['frames'])} frames vs {n_pages} pages")
    check("loops forever (NETSCAPE2.0 repeat 0)", g["loop"] == 0, repr(g["loop"]))
    want_cs = round(round(1000 / fps) / 10)
    delays = {fr["gce"]["delay_cs"] for fr in g["frames"] if fr["gce"]}
    check("frame delay matches the chosen fps", delays == {want_cs},
          f"{delays} vs expected {want_cs}cs at {fps}fps")
    check("opaque export sets no transparency flag",
          not any(fr["gce"] and fr["gce"]["transparent"] for fr in g["frames"]))

    print("\nREAL GIF — Flip, transparent (rgba4444 / 1-bit alpha path)")
    flip.evaluate("() => openExportSheet()")
    flip.wait_for_timeout(300)
    flip.click('#exportGifToggle .gif-seg-btn[data-gif-bg="transparent"]')
    check("transparent mode selected", flip.evaluate("() => gifBgMode") == "transparent")
    with flip.expect_download(timeout=60000) as dl2:
        flip.click("#exportGif")
    raw_t = open(dl2.value.path(), "rb").read()
    gt = parse_gif(raw_t)
    check("transparent export is still a valid GIF89a", raw_t[:6] == b"GIF89a", f"{len(raw_t)} bytes")
    check("same frame count as the opaque export", len(gt["frames"]) == len(g["frames"]))
    check("every frame carries the transparency flag",
          all(fr["gce"] and fr["gce"]["transparent"] for fr in gt["frames"]))
    check("disposal is 'restore to background' (2), so frames don't smear",
          all(fr["gce"] and fr["gce"]["dispose"] == 2 for fr in gt["frames"]),
          str([fr["gce"]["dispose"] for fr in gt["frames"] if fr["gce"]]))
    check("transparent and opaque encodes differ", raw_t != raw,
          f"{len(raw_t)} vs {len(raw)} bytes")

    print("\nREAL GIF — the Pad's own export path (IIFE-scoped, driven via the UI)")
    draw(pad, "#canvas", 80, 80, n=30)
    pad.wait_for_timeout(300)
    # The Pad's openExport() is IIFE-scoped (asserted in verify_muxer.py), so it
    # can only be reached by clicking. The sheet then animates in via .open — the
    # click below drives the real gating logic, and the class is forced so the
    # button is hit-testable without waiting on a CSS transition.
    pad.evaluate("() => { const b = document.getElementById('exportBtn'); if (b) b.click(); }")
    pad.wait_for_timeout(600)
    pad.evaluate("""() => { const o = document.getElementById('exportOverlay');
                            o.hidden = false; o.classList.add('open'); }""")
    pad.wait_for_timeout(600)
    check("Pad's GIF button is enabled after a recording",
          not pad.evaluate("() => document.getElementById('exportGif').disabled"))
    with pad.expect_download(timeout=90000) as dl3:
        pad.click("#exportGif")
    raw_p = open(dl3.value.path(), "rb").read()
    gp = parse_gif(raw_p)
    check("Pad exports a valid GIF89a too", raw_p[:6] == b"GIF89a", f"{len(raw_p)} bytes")
    check("Pad GIF has at least one frame and loops", len(gp["frames"]) >= 1 and gp["loop"] == 0,
          f"{len(gp['frames'])} frames, loop={gp['loop']}")

    print("\nDEGRADATION — a missing vendored file disables the button, nothing else")
    gone = ctx.new_page()
    gone_errors = []
    gone.on("pageerror", lambda e: gone_errors.append(str(e)))
    gone.route("**/gifenc.min.js*", lambda route: route.abort())
    gone.goto(BASE + "/flip", wait_until="load")
    gone.wait_for_timeout(1000)
    check("window.gifenc is undefined when the file can't be fetched",
          gone.evaluate("() => typeof window.gifenc") == "undefined")
    check("Flip still boots without it", gone.evaluate("() => Array.isArray(frames)"))
    gone.evaluate("() => { addFrame(); addFrame(); openExportSheet(); }")
    gone.wait_for_timeout(400)
    st = gone.evaluate("""() => ({
        disabled: document.getElementById('exportGif').disabled,
        desc: (document.getElementById('exportGifDesc')||{}).textContent })""")
    check("GIF button is disabled rather than throwing", st["disabled"], str(st))
    check("copy points at the file, not the user's wifi",
          "connection" not in (st["desc"] or "").lower(), repr(st["desc"]))
    check("no page errors from the missing library", not gone_errors,
          "; ".join(gone_errors[:2]))

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
