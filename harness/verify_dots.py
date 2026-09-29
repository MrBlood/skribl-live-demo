import io, math, re, struct, wave
from PIL import Image
from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"
WAV = "/tmp/boombap.wav"
# See verify_amber.py: the original uploaded loop isn't in this sandbox, so
# synthesize an equivalent over-quota track (30s stereo -> ~6.7 MB base64).
with wave.open(WAV, "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _buf = bytearray()
    for _i in range(30 * 44100):
        _v = int(12000 * math.sin(2 * math.pi * 220 * _i / 44100))
        _buf += struct.pack("<hh", _v, _v)
    _w.writeframes(bytes(_buf))
AMBER = "rgb(255, 210, 63)"

results = []
check = make_check(results)

def _rgb(h):
    """'#30e8a7' -> 'rgb(48, 232, 167)', the form getComputedStyle returns."""
    h = h.lstrip("#")
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

COLOURS = """(which) => {
    const dot = document.getElementById(which + 'TabDot');
    const card = document.getElementById(which === 'photo' ? 'photoPending' : 'musicPending');
    const btn = document.getElementById(which === 'photo' ? 'photoPendingBtn' : 'musicPendingBtn');
    const meta = document.getElementById(which === 'photo' ? 'photoPendingMeta' : 'musicPendingMeta');
    const cs = e => e ? getComputedStyle(e) : null;
    return { dotHidden: dot ? dot.hidden : null,
             dotPending: dot ? dot.classList.contains('pending') : null,
             dotBg: dot ? cs(dot).backgroundColor : null,
             cardHidden: card ? card.hidden : null,
             cardBorder: card ? cs(card).borderTopColor : null,
             btnBg: btn ? cs(btn).backgroundColor : null,
             btnColor: btn ? cs(btn).color : null,
             accent: getComputedStyle(document.documentElement).getPropertyValue('--accent-fill').trim(),
             metaColor: meta ? cs(meta).color : null }; }"""

# THE RE-ADD BUTTON IS THE ACTION COLOUR, NOT THE WARNING (v317, the owner:
# "maybe not so gold?", and never dark text on a coloured pill). It was amber
# with dark words; it is the app's --accent with white words, the same as the
# pill's Re-add. The amber stays where it is the warning: the dot, the card's
# border and its meta line, all still asserted amber below. Compared against
# the page's own --accent-fill (the accent one step deeper, so white words on
# it clear AA -- third review), so a retuned purple does not redden this.
WHITE = "rgb(255, 255, 255)"

def scribble(pg, box, seed, n=200):
    cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
    pg.mouse.move(cx, cy); pg.mouse.down()
    for i in range(n):
        a=(i/n)*math.pi*6+seed; r=20+(i/n)*150
        pg.mouse.move(cx+math.cos(a)*r, cy+math.sin(a)*r*0.7)
    pg.mouse.up()

with sync_playwright() as p:
    # THE DARK THEME, EXPLICITLY (v292): the literals below are the dark ramp's amber. Since
    # v292 a bare page follows the OS and headless Chromium says light, on which amber is
    # rgb(138, 91, 0). The pin is the semantics (amber, not green, not red); measured on the
    # ramp it was written for.
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1280,"height":900}, color_scheme="dark")
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))

    print("\nFLIP")
    pg.goto(BASE+"/flip", wait_until="load"); pg.wait_for_timeout(700)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#pad").bounding_box()
    scribble(pg, box, 0.0); pg.wait_for_timeout(1200)
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(5000)
    c = pg.evaluate(COLOURS, "music")
    # Compared against the --good token rather than a typed literal: the colour
    # was lifted once (too dull at 6px) and a hand-typed hex here would have
    # failed for the right reason and the wrong cause.
    _good = pg.evaluate("() => getComputedStyle(document.documentElement)"
                        ".getPropertyValue('--good').trim()")
    check("music dot GREEN while the file is loaded",
          c["dotBg"] == _rgb(_good) and not c["dotPending"],
          f"{c['dotBg']} vs --good {_good}")

    # CONTRACT CHANGE (v222): with a working IndexedDB the quota spill brings
    # the media BACK on reload, so the dot is honestly green and there is no
    # re-add to ask for. The amber palette is still a real state — it now
    # means the store failed — so those assertions run against a page with
    # IndexedDB broken, where re-add genuinely is needed.
    pg.reload(wait_until="load"); pg.wait_for_timeout(4500)   # IDB merge + ~7MB decode
    c = pg.evaluate(COLOURS, "music")
    check("music dot visible after reload", c["dotHidden"] is False)
    check("music dot GREEN — the media came back from IndexedDB",
          not c["dotPending"] and c["cardHidden"] is True,
          f"{c['dotBg']} pending={c['dotPending']} cardHidden={c['cardHidden']}")

    pgB = b.new_page(viewport={"width":1280,"height":900}, color_scheme="dark")
    errsB = []; pgB.on("pageerror", lambda e: errsB.append(str(e)))
    pgB.add_init_script(
        "Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pgB.goto(BASE+"/flip", wait_until="load"); pgB.wait_for_timeout(700)
    pgB.evaluate("() => localStorage.clear()")
    boxB = pgB.locator("#pad").bounding_box()
    scribble(pgB, boxB, 0.0); pgB.wait_for_timeout(1200)
    pgB.set_input_files("#musicInput", WAV); pgB.wait_for_timeout(5000)
    pgB.reload(wait_until="load"); pgB.wait_for_timeout(1600)
    c = pgB.evaluate(COLOURS, "music")
    check("music dot AMBER when re-add is needed", c["dotBg"] == AMBER and c["dotPending"], c["dotBg"])
    check("re-add card visible", c["cardHidden"] is False)
    check("card border amber", "255, 210, 63" in c["cardBorder"], c["cardBorder"])
    check("Re-add button is the action colour with white words, not amber",
          c["btnBg"] == _rgb(c["accent"]) and c["btnColor"] == WHITE,
          f"bg {c['btnBg']} (accent {c['accent']}), text {c['btnColor']}")
    check("card meta text amber", c["metaColor"] == AMBER, c["metaColor"])
    pgB.close()

    print("\nPAD")
    pg.goto(BASE+"/skribl-pad", wait_until="load"); pg.wait_for_timeout(1200)
    pg.evaluate("() => localStorage.clear()")
    pbox = pg.locator("canvas").first.bounding_box()
    pg.mouse.move(pbox["x"]+120, pbox["y"]+120); pg.mouse.down()
    for i in range(60): pg.mouse.move(pbox["x"]+120+i*3, pbox["y"]+120+math.sin(i/4)*40)
    pg.mouse.up(); pg.wait_for_timeout(1800)
    pg.set_input_files("#musicInput", WAV); pg.wait_for_timeout(4500)
    pg.reload(wait_until="load"); pg.wait_for_timeout(2000)
    pg.wait_for_timeout(4000)   # restore at boot (v294); IDB re-add + decode
    # CONTRACT CHANGE (v222): restore used to leave an amber pending dot —
    # the bytes were gone by design and re-adding was the user's job. The
    # bytes now come back from IndexedDB through the real change pipeline,
    # so the honest dot is GREEN with the track actually present. The amber
    # dot still exists and is pinned in verify_amber.py's broken-store
    # section, where it is true.
    c = pg.evaluate(COLOURS, "music")
    got = pg.evaluate("() => !!(audioEl && audioEl._fileName)")
    check("Pad music dot GREEN after restore — the track came back",
          got is True and c["dotPending"] is False and c["dotHidden"] is False,
          f"{c['dotBg']} pending={c['dotPending']} track={got}")
    check("Pad Re-add button is the action colour with white words, not amber",
          c["btnBg"] == _rgb(c["accent"]) and c["btnColor"] == WHITE,
          f"bg {c['btnBg']} (accent {c['accent']}), text {c['btnColor']}")

    check("no uncaught page errors", not errs, "; ".join(errs[:2]))
    b.close()

# DOT RING (the owner, twice): "for the dot next to the Music/Photo can it just
# be the same as the dot on the icon?", then "can the ring be thinner ... white
# looks too thick". So the Photo and Music tab dots carry the media button's
# dot exactly, ring colour included, and the ring is 0.75px. It is an inset
# shadow because Chrome floors a BORDER to whole CSS pixels: the old 1.5px
# border drew as 1px, and a 0.75px one would too.
#
# Computed style answers "is it the same dot, and how thick is the ring"; a
# pixel answers "is a ring actually painted" (a rect is not a paint). Both
# editors, both themes, desktop and a 3x phone, because the dock's ground and
# the tabs differ per theme and the phone is where the owner looked.
RING = """() => {
  const ids = ['mediaTabDot', 'photoTabDot', 'musicTabDot'];
  ids.forEach(id => { const d = document.getElementById(id); if (d) { d.hidden = false; d.classList.remove('pending'); } });
  const probe = document.createElement('i');
  probe.style.color = 'rgb(' + getComputedStyle(document.documentElement).getPropertyValue('--surface-well-2-rgb').trim() + ')';
  document.body.appendChild(probe); const ground = getComputedStyle(probe).color; probe.remove();
  const out = { ground };
  ids.forEach(id => { const d = document.getElementById(id), c = getComputedStyle(d), r = d.getBoundingClientRect();
    out[id] = { shadow: c.boxShadow, border: c.borderTopWidth, w: c.width, h: c.height, bg: c.backgroundColor,
                x: r.left, y: r.top, rw: r.width }; });
  return out; }"""

def _inset(shadow):
    """(colour, spread px) of the inset ring in a computed box-shadow, or (None, 0)."""
    for part in re.split(r",\s*(?=rgba?\()", shadow or ""):
        if "inset" in part:
            m = re.match(r"(rgba?\([^)]*\))\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+(-?[\d.]+)px", part.strip())
            if m:
                return m.group(1), float(m.group(5))
    return None, 0.0

def _rgbt(s):
    return tuple(int(v) for v in re.findall(r"\d+", s)[:3])

with sync_playwright() as p:
    b = p.chromium.launch()
    for path, surf in (("/skribl-pad", "Pad"), ("/flip", "Flip")):
        for theme in ("dark", "light"):
            for form, vp, dsf in (("desktop", {"width": 1400, "height": 900}, 1),
                                  ("phone", {"width": 390, "height": 844}, 3)):
                ctx = b.new_context(viewport=vp, device_scale_factor=dsf,
                                    is_mobile=form == "phone", has_touch=form == "phone")
                pg = ctx.new_page()
                browsing.goto(pg, BASE, f"{path}?theme={theme}")
                pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
                browsing.pad_drawer(pg, "photo")
                r = pg.evaluate(RING)
                tag = f"DOT RING {surf} {theme} {form}"
                dock = r["mediaTabDot"]
                dcol, dw = _inset(dock["shadow"])
                check(f"{tag}: the dock dot's ring is 0.75px in the dock's ground, not a border",
                      abs(dw - 0.75) < 0.01 and dcol == r["ground"] and dock["border"] == "0px",
                      f"ring {dcol} {dw}px (ground {r['ground']}), border {dock['border']}")
                for tab in ("photoTabDot", "musicTabDot"):
                    t = r[tab]
                    check(f"{tag}: {tab} is the dock dot exactly (ring, glow, size)",
                          t["shadow"] == dock["shadow"] and t["border"] == dock["border"]
                          and t["w"] == dock["w"] and t["h"] == dock["h"] and t["bg"] == dock["bg"],
                          f"tab {t['shadow']} {t['w']}x{t['h']} b{t['border']} vs dock "
                          f"{dock['shadow']} {dock['w']}x{dock['h']} b{dock['border']}")
                if dsf == 3:
                    # One device pixel in from the photo tab dot's left edge, on
                    # its centre row, is ring; its centre is the dot's own colour.
                    t = r["photoTabDot"]
                    shot = pg.screenshot(clip={"x": t["x"] - 2, "y": t["y"] - 2,
                                               "width": t["rw"] + 4, "height": t["rw"] + 4})
                    im = Image.open(io.BytesIO(shot)).convert("RGB")
                    cy = im.height // 2
                    edge = im.getpixel((2 * dsf + 1, cy))
                    centre = im.getpixel((im.width // 2, cy))
                    ring_c, dot_c = _rgbt(r["ground"]), _rgbt(t["bg"])
                    dist = lambda a, c: sum(abs(x - y) for x, y in zip(a, c))
                    check(f"{tag}: the tab dot's ring is painted (edge nearer the ring, centre the dot)",
                          dist(edge, ring_c) < dist(edge, dot_c) and dist(centre, dot_c) < 40,
                          f"edge {edge} ring {ring_c} dot {dot_c} centre {centre}")
                ctx.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*58}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.
import sys
sys.exit(1 if bad else 0)
