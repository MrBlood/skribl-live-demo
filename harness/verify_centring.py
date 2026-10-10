"""Every control's mark sits in the middle of what you see: the centring census.

The owner: "Some buttons with regular ascii or Unicode doesn't get centered",
and then: build the checker into the harness as a real suite, so it runs with
every battery and catches new buttons on its own.

1. FIND EVERYTHING, THEN PROVE IT WAS REACHED. The population is read from
   the source (harness/centring_inventory.py: every <button>, role="button",
   and button a script builds, on every page). The suite then drives each page
   into every state where controls show -- drawers, sheets, menus, trays,
   popovers, dialogs, overlays, the replay, the Post sheet in each state -- and
   FAILS if a control in the inventory was never reached. A deliberate
   exception is named in UNREACHABLE with its reason.

2. MEASURE WHAT THE EYE SEES. Every reached control whose face is a symbol, an
   icon or a label of three characters or fewer, and the badges and chips, is
   photographed three times: as it is, with its mark hidden, and with the whole
   control hidden. The first two differ by the INK; the last two differ by the
   control's PAINTED SHAPE (its background and border), which is what the eye
   centres the mark in -- not its layout box, which can be wider than what is
   drawn. Optical centre = midpoint of the ink box's centre and the ink's
   centre of mass (the method of verify_icons.py's CENTRING section). A
   control with nothing painted is centred in its box. Measured at 402x874,
   390x664 and 1280x800, at 3x, in light and dark; anything off by more than a
   third of a CSS pixel (one screen pixel on an iPhone) is flagged. A label
   made of text is measured in every installed face, because where text sits
   depends on the font.

3. NO TYPED SYMBOLS. A mark typed as a character (+ - x ... arrows) sits at a
   different height in every font, and the owner's iPhone (SF) and Windows
   (Segoe UI) fonts are not in this container, so it can never be verified for
   them. The suite fails on any control whose visible face contains a Unicode
   symbol character, read from the DOM's own text nodes.

Writes a report to $CENTRING_OUT (default /tmp/centring-out): report.json and a
3x crop of each flagged control with crosshairs (green: the painted shape's
centre; magenta: the mark's optical centre).

    CENTRING_COMBOS=phone-light   run one combination (calibration, iteration)
"""
import io
import json
import math
import os
import pathlib
import struct
import sys
import time
import urllib.request

from assertions import make_check
import browsing
import centring_inventory

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageChops, ImageDraw
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
OUT = pathlib.Path(os.environ.get("CENTRING_OUT", "/tmp/centring-out"))
OUT.mkdir(parents=True, exist_ok=True)
results = []
check = make_check(results, with_detail=True)

TOL = 1 / 3          # CSS px: one screen pixel at 3x
DPR = 3
FACES = ("Liberation Sans", "DejaVu Sans", "FreeSans")
COMBOS = [("phone", {"width": 402, "height": 874}, True), ("short", {"width": 390, "height": 664}, True),
          ("desk", {"width": 1280, "height": 800}, False)]
THEMES = ("light", "dark")
ONLY = set(filter(None, os.environ.get("CENTRING_COMBOS", "").split(",")))

# Controls the suite does not reach, each with its reason. Kept short: an
# entry here is a control nobody checks.
UNREACHABLE = {
}

# Badges and chips that are not buttons but carry a mark the eye centres.
EXTRA = ".holdbadge, .loopchip, .rl-speed, .tool-badge, .tab-dot-badge"

HIDE_CSS = (".__ctr_ink, .__ctr_ink * { color: transparent !important; -webkit-text-fill-color: transparent !important;"
            " text-shadow: none !important; }"
            " .__ctr_ink svg, .__ctr_ink img, .__ctr_ink::before, .__ctr_ink::after { visibility: hidden !important; }"
            " .__ctr_gone { visibility: hidden !important; }"
            " *, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }")

SCAN = r"""(extra) => {
  const out = [], vw = innerWidth, vh = innerHeight;
  const els = new Set([...document.querySelectorAll('button, [role=button], ' + extra)]);
  let n = window.__ctrN || 0;
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (r.right <= 0 || r.bottom <= 0 || r.left >= vw || r.top >= vh) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || +cs.opacity < 0.05) continue;
    const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2)), cy = Math.min(vh - 1, Math.max(0, r.top + r.height / 2));
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || !(hit === el || el.contains(hit) || hit.contains(el))) continue;   // painted, not merely laid out
    if (!el.dataset.ctr) el.dataset.ctr = String(++n);
    const keys = [];
    if (el.id) keys.push('#' + el.id);
    for (const c of el.classList) keys.push('.' + c);
    for (const a of el.getAttributeNames()) if (a.startsWith('data-') && a !== 'data-ctr') keys.push('[' + a + ']');
    // The visible face: text nodes a person sees, and whether an icon is drawn.
    let text = '';
    const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let t; (t = walk.nextNode());) {
      const p = t.parentElement, ps = p && getComputedStyle(p);
      if (!p || ps.display === 'none' || ps.visibility === 'hidden' || p.closest('[hidden]')) continue;
      const pr = p.getBoundingClientRect(); if (pr.width < 1 || pr.height < 1) continue;
      text += t.nodeValue;
    }
    text = text.replace(/\s+/g, ' ').trim();
    const svg = [...el.querySelectorAll('svg, img')].some(s => { const b = s.getBoundingClientRect(); return b.width > 2 && b.height > 2 && getComputedStyle(s).visibility !== 'hidden'; });
    const typed = (text.match(/\p{S}/gu) || []).join('');
    out.push({ id: el.dataset.ctr, keys, text, svg, typed, name: el.getAttribute('aria-label') || text.slice(0, 40),
               rect: [r.left, r.top, r.width, r.height], extra: el.matches(extra), tag: el.tagName.toLowerCase() });
  }
  window.__ctrN = n;
  return out;
}"""


def _diff(a, b):
    d = ImageChops.difference(a, b).convert("L")
    return d.point(lambda v: v if v > 24 else 0)


def _centroid(w):
    W, H = w.size
    cols = list(w.resize((W, 1), Image.BOX).tobytes())
    rows = list(w.resize((1, H), Image.BOX).tobytes())
    sx, sy = sum(cols), sum(rows)
    if not sx or not sy:
        return None
    return sum(i * v for i, v in enumerate(cols)) / sx + 0.5, sum(i * v for i, v in enumerate(rows)) / sy + 0.5


def measure(pg, ctr, rect, keep=False):
    """(dx, dy) of the mark's optical centre from the painted shape's centre, in CSS px, or None."""
    pad = 3
    x, y, w, h = rect
    clip = {"x": max(0, x - pad), "y": max(0, y - pad), "width": w + 2 * pad, "height": h + 2 * pad}
    sel = f'[data-ctr="{ctr}"]'
    shot = lambda: Image.open(io.BytesIO(pg.screenshot(clip=clip, animations="disabled"))).convert("RGB")
    full = shot()
    pg.evaluate("(s) => document.querySelector(s).classList.add('__ctr_ink')", sel)
    plate = shot()
    pg.evaluate("(s) => document.querySelector(s).classList.add('__ctr_gone')", sel)
    behind = shot()
    pg.evaluate("(s) => { const e = document.querySelector(s); e.classList.remove('__ctr_ink'); e.classList.remove('__ctr_gone'); }", sel)
    ink, shape = _diff(full, plate), _diff(plate, behind)
    ib = ink.getbbox()
    if not ib:
        return None
    c = _centroid(ink)
    ox, oy = ((ib[0] + ib[2]) / 2 + c[0]) / 2, ((ib[1] + ib[3]) / 2 + c[1]) / 2
    sb = shape.getbbox()
    S = full.size[0] / clip["width"]
    if sb and (sb[2] - sb[0]) > 4 * S and (sb[3] - sb[1]) > 4 * S:
        sx, sy, painted = (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2, True
    else:
        sx, sy, painted = (x - clip["x"] + w / 2) * S, (y - clip["y"] + h / 2) * S, False
    dx, dy = (ox - sx) / S, (oy - sy) / S
    crop = None
    if keep:
        im = full.copy(); dr = ImageDraw.Draw(im)
        for (px, py, col) in ((sx, sy, (20, 200, 90)), (ox, oy, (230, 40, 200))):
            dr.line([(px, 0), (px, im.size[1])], fill=col, width=1)
            dr.line([(0, py), (im.size[0], py)], fill=col, width=1)
        crop = im
    return round(dx, 2), round(dy, 2), painted, crop


# ------------------------------------------------------------------ states
def wav_bytes(seconds, rate=22050):
    n = int(seconds * rate)
    body = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(body)) + body)


def png_bytes(w=120, h=90):
    im = Image.new("RGB", (w, h), (120, 160, 220)); b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


AUD, PNG = wav_bytes(2.5), png_bytes()


def js(pg, code, arg=None):
    try:
        return pg.evaluate(code, arg) if arg is not None else pg.evaluate(code)
    except Exception as e:
        return f"ERR {e}"[:120]


def click(pg, sel, wait=350):
    try:
        el = pg.locator(sel).first
        if el.count() and el.is_visible():
            el.click(timeout=3000)
            pg.wait_for_timeout(wait)
            return True
    except Exception:
        pass
    return False


def esc(pg, wait=350):
    pg.keyboard.press("Escape"); pg.wait_for_timeout(wait)


def draw(pg, sel="#canvas", n=40):
    box = pg.locator(sel).bounding_box()
    if not box:
        return
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx - 80, cy); pg.mouse.down()
    for i in range(n):
        pg.mouse.move(cx - 80 + i * 4, cy + math.sin(i / 6) * 40)
    pg.mouse.up(); pg.wait_for_timeout(250)


def post_fixture():
    pts = [{"x": 100 + i * 8, "y": 200 + math.sin(i / 5) * 60, "color": "#7c5cff", "size": 8, "t": i * 30, "start": i == 0} for i in range(40)]
    p = {"version": 2, "schemaVersion": 2, "playbackMode": "replay", "pauseMode": "tight", "fps": None,
         "canvasSize": {"cssWidth": 816, "cssHeight": 612}, "title": "Centring", "visibility": "public",
         "caption": "A caption, for the gallery's caption button.",
         "frames": [{"strokes": pts, "strokeGroups": [40], "background": {"color": "#f6f2ea"},
                     "music": {"data": "data:audio/wav;base64," + __import__("base64").b64encode(AUD).decode(),
                               "name": "t.wav", "trimStart": 0, "trimEnd": 2.5}}]}
    r = urllib.request.urlopen(urllib.request.Request(BASE + "/api/skribls", data=json.dumps(p).encode(),
                                                      headers={"Content-Type": "application/json"}), timeout=20)
    return json.loads(r.read())


IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
SEED_POSTED = """(p) => { try { localStorage.setItem('skribl_posted_v1', JSON.stringify([
  { id: p.id, url: p.url, title: 'Centring', kind: 'pad', pages: 1, visibility: 'public', tok: p.tok, local: false, has_audio: true, at: Date.now() },
  { id: 'localonly1', url: null, title: 'On this device', kind: 'pad', pages: 1, visibility: null, tok: null, local: true, has_audio: false, at: Date.now() - 5000 } ]));
  localStorage.setItem('skribl_recent_colors', '["#123456", "#ff6f91"]'); } catch (e) {} }"""
SHARE_STUB = "() => { navigator.share = () => Promise.resolve(); navigator.canShare = () => true; }"
SEED_DRAFT = """async () => { if (!window.SkriblDraftStore) return 'no store';
  await SkriblDraftStore.put('saved:d1', { id: 'd1', kind: 'pad', title: 'A draft', payload: { version: 2, schemaVersion: 2, frames: [] }, thumbnail: null, savedAt: new Date().toISOString() }); return 'ok'; }"""


def editor_common(pg, menu, export_item):
    """What both editors share: the draw drawer and its parts, the menu, its
    sheets, Media, How it works."""
    click(pg, "#penToolBtn"); click(pg, "#drawerDetentMore"); yield "draw drawer"
    click(pg, "#paintTargetSeg [data-target=background]"); yield "draw drawer, background"
    click(pg, "#paintTargetSeg [data-target=ink], #paintTargetSeg [data-target=pen], #paintTargetSeg button")
    click(pg, "#eyedropperBtn"); yield "eyedropper"; esc(pg)
    click(pg, "#penToolBtn")
    click(pg, menu); yield "menu"; esc(pg)
    click(pg, "#tuneBtn"); click(pg, "#gridBtn"); yield "settings, grid"; click(pg, "#gridBtn"); click(pg, "#tuneBtn")
    js(pg, "() => { if (window.SkriblRecoveryKey) SkriblRecoveryKey.present({ key: 'skrb_centring_key' }); }"); pg.wait_for_timeout(400)
    yield "recovery key"
    js(pg, "() => window.SkriblRecoveryKey && SkriblRecoveryKey.close()")
    js(pg, "() => showToast('Cleared', null, { label: 'Undo', onClick() {} })"); pg.wait_for_timeout(200); yield "toast with undo"
    js(pg, "() => { window.dispatchEvent(new StorageEvent('storage', { key: AUTOSAVE_KEY, newValue: 'x', storageArea: localStorage })); }")
    pg.wait_for_timeout(500); yield "two-tab notice"
    click(pg, ".othertab-x")
    js(pg, "() => { if (typeof pendingPhotoMeta !== 'undefined') { pendingPhotoMeta = { name: 'p.jpg' }; } if (typeof pendingMusicMeta !== 'undefined') { pendingMusicMeta = { name: 'song.mp3', trimStart: 0, trimEnd: 4 }; } if (typeof refreshPendingCards === 'function') refreshPendingCards(); }")
    js(pg, "() => typeof showAutosaveStatus === 'function' && showAutosaveStatus('saved-no-media')"); pg.wait_for_timeout(300)
    yield "media missing"
    click(pg, "#mediaOpenBtn"); click(pg, "#mediaTabPhoto"); yield "media card, photo to re-add"
    click(pg, "#mediaTabMusic"); yield "media card, song to re-add"
    js(pg, "() => { pendingPhotoMeta = null; pendingMusicMeta = null; if (typeof refreshPendingCards === 'function') refreshPendingCards(); }")
    yield "media card, no song"
    try:
        pg.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
        pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=15000)
    except Exception:
        pass
    yield "media card, song (Trim)"
    click(pg, "#fineTuneToggle"); yield "media card, song (Fine-tune)"
    click(pg, "#mediaTabPhoto")
    try:
        pg.set_input_files("#photoInput, #imageInput", {"name": "p.png", "mimeType": "image/png", "buffer": PNG}); pg.wait_for_timeout(1200)
    except Exception:
        pass
    yield "media card, photo"
    click(pg, "#mediaOpenBtn"); esc(pg)
    click(pg, menu); click(pg, "#openCloudDraftItem, #miOpenDraft", 900); yield "drafts sheet"; esc(pg)
    click(pg, menu); click(pg, "#reportItem, #miReport", 700); yield "report"; esc(pg)
    click(pg, menu); click(pg, "#nameItem, #miName", 500); yield "name"; esc(pg)
    click(pg, menu); click(pg, "#helpItem, #miInfo", 900); yield "how it works"
    click(pg, "#learnPeek", 900); yield "examples"
    click(pg, "#learnSheet .learn-card .learn-stage", 900); yield "example viewer"
    esc(pg); esc(pg); esc(pg)


def pad_states(pg):
    yield "rest"
    click(pg, "#tuneBtn"); yield "canvas settings"; click(pg, "#tuneBtn")
    yield from editor_common(pg, "#menuBtn", "#exportItem")
    click(pg, "#shapeToolBtn"); yield "shape card"; esc(pg); click(pg, "#penToolBtn")
    click(pg, "#magnifyBtn"); yield "zoom"; esc(pg)
    draw(pg); js(pg, "() => { if (recording) endRecordingTake(); }"); pg.wait_for_timeout(400); yield "take saved"
    click(pg, "#playBtn", 500); yield "replay"
    click(pg, "#padLine .rl-speed"); yield "replay speeds"
    click(pg, "#playBtn")
    click(pg, "#menuBtn"); click(pg, "#exportItem", 700); yield "export"
    click(pg, "#exportGif", 150); yield "export, rendering"; pg.wait_for_timeout(2500); esc(pg)
    js(pg, SHARE_STUB)
    click(pg, "#postBtn", 700); yield "post sheet, ready"
    click(pg, "#postSubmitBtn", 2500); yield "post sheet, posted"
    esc(pg)


def flip_states(pg):
    yield "rest"
    click(pg, "#tuneBtn"); yield "playback settings"; click(pg, "#tuneBtn")
    yield from editor_common(pg, "#moreBtn", "#miExport")
    draw(pg, "#pad"); click(pg, "#addcopy"); draw(pg, "#pad"); click(pg, "#addcopy"); yield "pages"
    click(pg, "#pbLoop"); js(pg, "() => typeof loopCycle === 'function' && !document.querySelector('.loopchip') && loopCycle()"); yield "a loop"
    click(pg, "#pbUnder"); yield "a page underneath"
    click(pg, "#strip .frame.on .pageops", 500); yield "page menu"; esc(pg)
    click(pg, "#toolMoreBtn"); yield "more tools"
    click(pg, "#toolTray .tool-tray-btn"); yield "more tools, a tool"; esc(pg)
    js(pg, "() => setTool('artmove')"); pg.wait_for_timeout(300); yield "move artwork"
    js(pg, "() => setTool('select')")
    js(pg, "() => { selSpans = [[0, frames[idx].strokes.length]]; syncSelBar(); }"); pg.wait_for_timeout(300); yield "selection"
    click(pg, "#sbStamp", 400)
    js(pg, "() => { selClipboard = frames[idx].strokes.slice(0, 2); selSpans = [[0, frames[idx].strokes.length]]; syncSelBar(); }"); yield "selection, clipboard"
    js(pg, "() => setTool('stamp')"); pg.wait_for_timeout(300); yield "stamps"
    js(pg, "() => setTool('pen')")
    click(pg, "#play", 700); yield "playing"; click(pg, "#play")
    click(pg, "#moreBtn"); click(pg, "#miExport", 700); yield "export"
    js(pg, "() => exportShow('Exporting…')"); pg.wait_for_timeout(200); yield "export, progress"
    js(pg, "() => exportHide()"); esc(pg)
    js(pg, SHARE_STUB)
    click(pg, "#postBtn", 700); yield "post sheet, ready"; esc(pg)


def flip_stamps_empty(pg):
    js(pg, "() => setTool('stamp')"); pg.wait_for_timeout(400); yield "stamps, none saved"


def compose_states(pg, menu, other):
    yield "compose"
    draw(pg, "#canvas" if menu == "#menuBtn" else "#pad")
    click(pg, menu); click(pg, other, 600); yield "leave sheet"


def iphone_states(pg, menu):
    pg.wait_for_timeout(1400); yield "home screen card"
    click(pg, "#homeScreenBannerClose")
    click(pg, menu); yield "menu"
    click(pg, "#homeScreenItem", 600); yield "home screen steps"; esc(pg)


def standalone_states(pg, menu):
    click(pg, menu); yield "menu"


def error_states(pg):
    yield "error"


def player_states(pg):
    yield "rest"
    click(pg, "#playerPlayBtn", 600); yield "playing"
    click(pg, "#playerLine .rl-speed"); yield "speeds"
    click(pg, "#playerMoreBtn"); yield "more"; esc(pg)
    click(pg, "#playerFullBtn", 800); yield "full screen"; esc(pg, 600)


def library_states(pg):
    yield "rest"
    click(pg, "#btnFull", 800); yield "full screen"; click(pg, "#fullExit"); esc(pg, 500)
    pg.fill("#postedSearch", "Cen") if pg.locator("#postedSearch").count() else None
    pg.wait_for_timeout(300); yield "search"
    click(pg, "#searchClear")
    click(pg, ".posted-del"); click(pg, ".posted-del", 500); yield "undo bar"
    click(pg, "#postedUndoBtn")
    click(pg, "#postedRecover", 500); yield "recovery"; esc(pg)
    click(pg, "#postedClear", 500); yield "clear, keys"; esc(pg)
    click(pg, "#pageMenuBtn"); yield "page menu"; esc(pg)
    js(pg, SEED_DRAFT); click(pg, "#tabDrafts", 900); yield "drafts"


def gallery_states(pg):
    pg.wait_for_timeout(800); yield "rest"
    pg.hover(".tileStage") if pg.locator(".tileStage").count() else None
    yield "a tile"
    click(pg, ".tileMore"); yield "tile menu"
    click(pg, ".cmItem.cmReport", 600); yield "report"; esc(pg)
    click(pg, ".skfull-full", 900); yield "a tile, full screen"; click(pg, ".tileExit"); esc(pg)
    click(pg, "#pageMenuBtn"); yield "page menu"; esc(pg)


def feed_states(pg):
    yield "rest"
    pg.hover(".skribl-inline") if pg.locator(".skribl-inline").count() else None
    yield "a post"
    if click(pg, "#padBtn", 1500):
        fr = pg.frame_locator("#padFrame")
        try:
            pg.wait_for_timeout(1500)
            frm = [f for f in pg.frames if "compose=1" in f.url]
            if frm:
                frm[0].evaluate("() => { const c = document.getElementById('canvas'); }")
                frm[0].evaluate("""() => { strokes.push({x: 100, y: 100, color: '#7c5cff', size: 8, t: 0, start: true}, {x: 200, y: 140, color: '#7c5cff', size: 8, t: 40, start: false});
                    redrawAll && redrawAll(); window.SkriblCompose && SkriblCompose.deliver(serializeSkribl()); }""")
                pg.wait_for_timeout(1200)
        except Exception:
            pass
    yield "attached"


def simple_states(pg):
    yield "rest"


def scenarios(fx):
    """(path, states, extra context options, init scripts, routes, combos)."""
    idp = fx["url"].rsplit("/", 1)[-1]
    seed = SEED_POSTED.replace("(p) =>", "(() => { const p = " + json.dumps({"id": idp, "url": fx["url"], "tok": fx.get("deleteToken")}) + ";") + ")();"
    seed = seed.replace("} }\"\"\"", "} }")
    return [
        ("/", pad_states, {}, [seed], {}, None),
        ("/flip", flip_states, {}, [seed], {}, None),
        ("/flip", flip_stamps_empty, {}, [], {}, None),
        ("/?compose=1", lambda pg: compose_states(pg, "#menuBtn", "#flipBtn"), {}, [], {}, None),
        ("/flip?compose=1", lambda pg: compose_states(pg, "#moreBtn", "#padBtn"), {}, [], {}, None),
        ("/", lambda pg: iphone_states(pg, "#menuBtn"), {"user_agent": IPHONE_UA}, [], {}, {"phone", "short"}),
        ("/", lambda pg: standalone_states(pg, "#menuBtn"), {}, ["Object.defineProperty(navigator, 'standalone', { get: () => true });"], {}, None),
        ("/library", library_states, {}, [seed, SHARE_STUB.replace("() =>", "(() =>") + ")();"], {}, None),
        ("/gallery", gallery_states, {}, [], {}, None),
        ("/gallery", error_states, {}, [], {"**/api/skribls?*": 500}, None),
        ("/feed", feed_states, {}, [], {}, None),
        ("/feed", error_states, {}, [], {"**/api/skribls?limit=*": 500}, None),
        (fx["url"], player_states, {}, [], {}, None),
        (fx["url"], error_states, {}, [], {"**/api/skribls/" + idp: 500}, None),
        ("/", lambda pg: (yield from help_error(pg, "#menuBtn", "#helpItem")), {}, [], {"**/help/demos/*.json": 500}, None),
    ]


def help_error(pg, menu, item):
    click(pg, menu); click(pg, item, 900); click(pg, "#learnPeek", 1500); yield "examples failed"


# ------------------------------------------------------------------ run
inventory = centring_inventory.entries()
reached, typed_bad, rows, errs = set(), {}, [], []

with sync_playwright() as p:
    b = p.chromium.launch()
    fx = post_fixture()
    for size, vp, mobile in COMBOS:
        for theme in THEMES:
            combo = f"{size}-{theme}"
            if ONLY and combo not in ONLY:
                continue
            print(f"\n{combo}")
            for path, states, extra, inits, routes, only_sizes in scenarios(fx):
                if only_sizes and size not in only_sizes:
                    continue
                ctx = b.new_context(viewport=vp, device_scale_factor=DPR, color_scheme=theme,
                                    is_mobile=mobile, has_touch=mobile, **extra)
                for code in inits:
                    ctx.add_init_script(code)
                for pat, status in routes.items():
                    ctx.route(pat, lambda r, st=status: r.fulfill(status=st, body="{}", content_type="application/json"))
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
                try:
                    browsing.goto(pg, BASE, path, require_boot=False)
                except Exception as e:
                    errs.append(f"{path}: {e}"[:120]); ctx.close(); continue
                pg.wait_for_timeout(700)
                js(pg, "() => { window.SkriblHints && SkriblHints.hide && SkriblHints.hide(); }")
                pg.add_style_tag(content=HIDE_CSS)
                seen = set()
                for state in states(pg):
                    for c in pg.evaluate(SCAN, EXTRA):
                        reached.update(c["keys"])
                        if c["typed"]:
                            typed_bad.setdefault((path, c["name"]), c["typed"])
                        # An icon alone, a label of three characters or fewer, or a
                        # badge or chip. A menu row with an icon AND words is a
                        # line of text, aligned by the row, and not in scope.
                        in_scope = c["extra"] or (c["svg"] and not c["text"]) or (0 < len(c["text"]) <= 3)
                        sig = (tuple(sorted(c["keys"])), c["text"])
                        if not in_scope or sig in seen:
                            continue
                        seen.add(sig)
                        textual = bool(c["text"]) and not c["svg"]
                        for face in (FACES if textual else (None,)):
                            if face:
                                js(pg, "([s, f]) => { document.querySelector(s).style.fontFamily = '\"' + f + '\"'; }",
                                   [f'[data-ctr="{c["id"]}"]', face])
                            try:
                                m = measure(pg, c["id"], c["rect"], keep=True)
                            except Exception as e:
                                m = None
                            if face:
                                js(pg, "(s) => { const e = document.querySelector(s); if (e) e.style.fontFamily = ''; }",
                                   f'[data-ctr="{c["id"]}"]')
                            if not m:
                                continue
                            dx, dy, painted, crop = m
                            row = {"combo": combo, "page": path if not path.startswith("/s/") else "/s/<id>", "state": state,
                                   "control": c["name"] or c["keys"][0] if c["keys"] else c["tag"], "keys": c["keys"],
                                   "size": [round(c["rect"][2], 1), round(c["rect"][3], 1)], "face": face or ("text" if textual else "icon"),
                                   "typed": c["typed"], "dx": dx, "dy": dy, "painted": painted}
                            if max(abs(dx), abs(dy)) > TOL and crop is not None:
                                fn = f"{len(rows):04d}.png"
                                crop.save(OUT / fn); row["crop"] = fn
                            rows.append(row)
                ctx.close()
    b.close()

# ------------------------------------------------------------------ verdicts
inv_keys = {e["key"] for e in inventory}
unreached = sorted(k for k in inv_keys if k not in reached and k not in UNREACHABLE)
print(f"\nfound in source {len(inv_keys)} / reached live {len(inv_keys) - len(unreached) - len([k for k in UNREACHABLE if k in inv_keys])}"
      f" / named exceptions {len([k for k in UNREACHABLE if k in inv_keys])} / unreached {len(unreached)} (must be 0)")
check("every control in the inventory was reached on a live page (or is a named exception)",
      not unreached, f"{len(unreached)} unreached: " + ", ".join(unreached[:40]))
check("every inventory exception still names a control that exists",
      all(k in inv_keys for k in UNREACHABLE), str([k for k in UNREACHABLE if k not in inv_keys]))
off = sorted((r for r in rows if max(abs(r["dx"]), abs(r["dy"])) > TOL), key=lambda r: -max(abs(r["dx"]), abs(r["dy"])))
check(f"every measured mark sits within a third of a CSS pixel of its control's middle ({len(rows)} measurements)",
      rows and not off, f"{len(off)} off; worst: " + "; ".join(
          f"{r['page']} {r['state']} '{r['control']}' {r['combo']} {r['face']} dx {r['dx']} dy {r['dy']}" for r in off[:6]))
check("no control's visible face is a typed symbol character",
      not typed_bad, f"{len(typed_bad)}: " + "; ".join(f"{pg_} '{n}' {t}" for (pg_, n), t in list(typed_bad.items())[:12]))
(OUT / "report.json").write_text(json.dumps({"rows": rows, "off": off, "typed": [[k[0], k[1], v] for k, v in typed_bad.items()],
                                             "unreached": unreached, "inventory": inventory, "errors": errs[:50]}, indent=1))
print(f"report: {OUT / 'report.json'}")

print("\n" + "=" * 62)
passed = sum(1 for r in results if r[0])
print(f"{passed}/{len(results)} passed" + ("" if passed == len(results) else
      "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
sys.exit(0 if passed == len(results) else 1)
