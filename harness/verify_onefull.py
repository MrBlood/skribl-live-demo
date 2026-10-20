#!/usr/bin/env python3
"""One full screen, everywhere: the Gallery's and the Library's are the link page's.

THE OWNER: "why can't the gallery player look like the others? with the same
scrubber and all?", then "All yes" to the mock (A: who drew it in the top
corner; the cards keep their own bar). The Gallery and the Library played in
full screen under a bar of their own (lib/fullbar.js) built before the link
page had its speed line and its scrubber in the drawing's shape: a 6px line,
three speeds, the replay's clock where the link page says the artist's (0:50
of 2:00 beside 8:26 of 20:09, one drawing, one moment), and the page's colour
round the drawing. Now lib/fullbar.js band() builds the link page's band and
x, fullband.css brings styles.css's own rules for them, and the in-post player
lends its line (inlineplayer.js band()).

WHAT IS ASKED, on the Gallery and the Library beside the link page, the same
drawing paused at the same place, on the owner's phone (402x874, the pinned
stand-in Safari gets) and a desk (the real API), in both themes:

  1. THE SAME BAND: scrubber, clock, words, buttons, in that order, the x in
     the corner -- and every part measures the same as the link page's, by
     its computed size, spacing, type, colours and glass.
  2. THE SAME CLOCK: the artist's time at the same place, and the whole of it.
  3. EVERY SPEED: the words' button opens the link page's speeds, a Flip's
     without Fit, and a pick reaches the player.
  4. THE DRAWING'S GROUND TO THE SCREEN'S EDGES, on the link page too, read
     off painted pixels at the edges. The link page's wore its canvas frame's
     inset vignette until the owner's yes to Q6: no shadow on any full screen.
  5. WHO DREW IT in the top corner across from the x, at its height, its
     words clear on their glass, stepping back with the controls.
  6. THE WAY OUT: the x and the full-screen button leave.

THE CARDS keep their own bar, which verify_cardfade and verify_gallery hold.
"""
import json
import math
import os
import sys
import urllib.request

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the full screens are one.")
    raise SystemExit(77)

import io

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
TAG = "one" + os.urandom(3).hex()

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""
GROUND = "#2e1b52"


def post(body):
    rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read())


def ring(r, n, t0, gap, color):
    return [{"x": round(201 + r * math.cos(i / n * 6.283), 1), "y": round(380 + r * math.sin(i / n * 6.283), 1),
             "color": color, "t": t0 + i * gap, "start": i == 0, "size": 4 + 3 * math.sin(i / n * math.pi)}
            for i in range(n + 1)]


# A drawing drawn over about twenty minutes, so the artist's clock and the
# replay's part ways (the replay skips the long pauses), and a Flip.
_pts = ring(60, 800, 0, 500, "#7c5cff") + ring(150, 800, 401500, 500, "#7c5cff") + ring(180, 800, 803000, 500, "#c9b8ff")
DRAWING = post({"title": f"One full {TAG}", "version": 2, "schemaVersion": 2, "visibility": "public",
                "playbackMode": "replay", "canvasSize": {"cssWidth": 402, "cssHeight": 760},
                "frames": [{"strokes": _pts, "strokeGroups": [801, 801, 801], "background": {"color": GROUND}}]})
FLIP = post({"title": f"One flip {TAG}", "version": 2, "schemaVersion": 2, "visibility": "public",
             "playbackMode": "flip", "fps": 6, "canvasSize": {"cssWidth": 402, "cssHeight": 760},
             "frames": [{"strokes": ring(60 + 40 * k, 60, 0, 400, "#ffd166"), "strokeGroups": [61],
                         "background": {"color": "#203040"}} for k in range(3)]})

# Each surface's frame and its parts. The link page's are its own ids; the
# Gallery's and the Library's are the band lib/fullbar.js builds in theirs.
LINK = {"frame": ".canvas-wrap:is(:fullscreen, .is-immersive-page)", "band": "#playerBar",
        "progress": "#playerProgress", "time": "#playerBar .player-time", "line": "#playerLine",
        "controls": "#playerBar .player-controls", "restart": "#playerRestartBtn", "play": "#playerPlayBtn",
        "loop": "#playerLoopBtn", "full": "#playerFullBtn", "x": "#playerFullExit"}


def parts(frame):
    return {"frame": frame, "band": frame + " > .player-bar", "progress": frame + " .player-progress",
            "time": frame + " .player-time", "line": frame + " .replay-line", "controls": frame + " .player-controls",
            "restart": frame + " .player-controls > :nth-child(1)", "play": frame + " .player-controls > .primary",
            "loop": frame + " .player-controls > :nth-child(3)", "full": frame + " .player-controls > :nth-child(5)",
            "x": frame + " > .player-btn.full-exit"}


GAL = parts(".tileStage.watch-full:is(:fullscreen, .is-immersive-page)")
LIB = parts(".stageCanvasWrap.watch-full:is(:fullscreen, .is-immersive-page)")

PROPS = ["width", "height", "padding-top", "padding-right", "padding-bottom", "padding-left", "row-gap", "column-gap",
         "font-size", "font-weight", "line-height", "font-family", "color", "background-color", "background-image",
         "border-top-width", "border-top-color", "border-top-left-radius", "box-shadow", "backdrop-filter", "text-shadow"]
READ = """([P, props]) => {
  const out = {}, q = s => document.querySelector(s);
  const one = (k, e) => { if (!e) { out[k] = null; return; } const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    out[k] = { left: Math.round(r.left), top: Math.round(r.top), right: Math.round(innerWidth - r.right), bottom: Math.round(innerHeight - r.bottom),
               cls: ['t-dark', 't-light', 'active', 'primary'].filter(c => e.classList.contains(c)).join(' '),
               text: (e.textContent || '').trim(), label: e.getAttribute('aria-label') || '', shown: !!e.getClientRects().length && cs.visibility !== 'hidden',
               css: Object.fromEntries(props.map(p => [p, cs.getPropertyValue(p)])) }; };
  for (const [k, s] of Object.entries(P)) if (k !== 'frame') one(k, q(s));
  const t = q(P.time); out.at = t ? t.children[0].textContent : null; out.dur = t ? t.children[1].textContent : null;
  const sp = q(P.line + ' .rl-speed'); one('speed', sp);
  const words = q(P.line + ' .rl-text'); out.words = words ? words.innerText.replace(/\\s+/g, ' ').trim() : null;
  const band = q(P.band);
  out.order = band ? [...band.children].filter(c => c.getClientRects().length).map(c => ['player-progress', 'player-time', 'replay-line', 'player-controls'].find(n => c.classList.contains(n)) || c.className) : [];
  out.buttons = q(P.controls) ? [...q(P.controls).children].filter(c => c.getClientRects().length && getComputedStyle(c).display !== 'none').map(c => c.getAttribute('aria-label')) : [];
  const head = q(P.progress + ' .rl-head'); out.head = head ? parseFloat(head.style.left) : null;
  out.strip = !!q(P.progress + ' canvas.rl-strip');
  return out; }"""


def same(a, b, tol=0.6):
    if a == b:
        return True
    try:
        return abs(float(str(a).rstrip("px")) - float(str(b).rstrip("px"))) <= tol
    except ValueError:
        return False


def diff(ref, got, keys=("band", "progress", "time", "line", "speed", "controls", "restart", "play", "loop", "full", "x")):
    bad = []
    for k in keys:
        r, g = ref.get(k), got.get(k)
        if not r or not g:
            bad.append(f"{k}: missing ({'link' if not r else 'here'})")
            continue
        for side in ("left", "top", "right", "bottom"):
            if k in ("band", "x") and not same(r[side], g[side], 1):
                bad.append(f"{k}.{side}: {r[side]} vs {g[side]}")
        if r["cls"] != g["cls"]:
            bad.append(f"{k} tone/state: {r['cls']!r} vs {g['cls']!r}")
        for p in PROPS:
            if not same(r["css"][p], g["css"][p]):
                bad.append(f"{k}.{p}: {r['css'][p]} vs {g['css'][p]}")
    return bad


def pause_at(pg, P, frac, link):
    """Pause, then put the drawing at `frac` of its replay."""
    pg.evaluate("(s) => { const b = document.querySelector(s); if (b && /Pause/.test(b.getAttribute('aria-label') || '')) b.click(); }", P["play"])
    pg.wait_for_timeout(300)
    if link:
        box = pg.locator(P["progress"]).bounding_box()
        pg.mouse.click(box["x"] + box["width"] * frac, box["y"] + box["height"] / 2)
    else:
        pg.evaluate("""([F, f]) => { const p = document.querySelector(F + ' .skribl-inline')._skriblInline;
                       p.seek(p.state().totalMs * f); }""", [P["frame"], frac])
    pg.wait_for_timeout(700)
    pg.evaluate("(s) => { const b = document.querySelector(s); if (b && /Pause/.test(b.getAttribute('aria-label') || '')) b.click(); }", P["play"])
    pg.wait_for_timeout(400)


def open_link(b, view, theme):
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE:
        pg.add_init_script(NO_API)
    pg.add_init_script(f"try {{ localStorage.setItem('skribl_theme_v1', '{theme}'); }} catch (e) {{}}")
    browsing.goto(pg, BASE, "/s/" + DRAWING["id"])
    # The button shows once the player has its drawing; a busy box takes longer.
    pg.wait_for_selector("#playerFullBtn", state="visible", timeout=60000)
    pg.wait_for_timeout(600)
    pg.click("#playerFullBtn")
    pg.wait_for_timeout(1200)
    pause_at(pg, LINK, 0.42, True)
    return pg


def open_gallery(b, view, theme, item=None):
    item = item or DRAWING
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE:
        pg.add_init_script(NO_API)
    pg.add_init_script(f"try {{ localStorage.setItem('skribl_theme_v1', '{theme}'); }} catch (e) {{}}")
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(1500)
    tile = pg.locator(f".tile:has(.skribl-inline[data-skribl-id='{item['id']}'])").first
    tile.scroll_into_view_if_needed()
    tile.evaluate("t => t.classList.add('ctl-on')")
    tile.locator(".skfull-card .skfull-full").first.click()
    pg.wait_for_timeout(1500)
    return pg


def open_library(b, view, theme):
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE:
        pg.add_init_script(NO_API)
    seed = json.dumps([{"id": DRAWING["id"], "url": DRAWING.get("url"), "title": f"One full {TAG}", "kind": "pad",
                        "pages": 1, "visibility": "public"}])
    pg.add_init_script("try { localStorage.setItem('skribl_posted_v1', %s); localStorage.setItem('skribl_theme_v1', '%s'); } catch (e) {}"
                       % (json.dumps(seed), theme))
    browsing.goto(pg, BASE, "/library")
    pg.wait_for_timeout(1500)
    pg.evaluate("() => { const r = document.querySelector('#postedList .posted-row .posted-main'); if (r) r.click(); }")
    pg.wait_for_function("() => { const b = document.getElementById('btnFull'); return b && !b.hidden && !b.disabled; }", timeout=12000)
    pg.evaluate("() => document.getElementById('btnFull').click()")
    pg.wait_for_timeout(1500)
    return pg


def edges(pg):
    """The screen's edges, the controls and the name away: the ground there."""
    pg.add_style_tag(content=":is(.player-bar, .player-btn.full-exit, .fb-who, .player-nib, .skribl-inline-nib) { visibility: hidden !important; }")
    pg.wait_for_timeout(200)
    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    w, h = im.size
    return [im.getpixel(xy) for xy in ((2, h // 2), (w - 3, h // 2), (w // 2, 2), (w // 2, h - 3))]


def rgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) for i in (1, 3, 5))


WHO = """(F) => { const w = document.querySelector(F + ' > .fb-who'), x = document.querySelector(F + ' > .player-btn.full-exit');
  if (!w || !x || !w.getClientRects().length) return null;
  const a = w.getBoundingClientRect(), b = x.getBoundingClientRect(), cs = getComputedStyle(w);
  const col = s => (s.match(/[\\d.]+/g) || []).map(Number);
  return { title: w.querySelector('b').textContent, top: Math.round(a.top), xTop: Math.round(b.top), height: Math.round(a.height), xHeight: Math.round(b.height),
           left: Math.round(a.left), xRight: Math.round(innerWidth - b.right), ink: col(cs.color), glass: col(cs.backgroundColor),
           ground: col(getComputedStyle(document.querySelector(F)).backgroundColor), tone: w.className }; }"""


def contrast(ink, glass, ground):
    a = glass[3] if len(glass) > 3 else 1
    bg = [glass[i] * a + ground[i] * (1 - a) for i in range(3)]

    def L(c):
        c = [v / 255 for v in c]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((L(ink[:3]), L(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    for vname, view, theme in (("phone", PHONE, "dark"), ("phone", PHONE, "light"),
                               ("desk", DESK, "light"), ("desk", DESK, "dark")):
        where = f"{vname}, {theme}"
        lk = open_link(b, view, theme)
        ref = lk.evaluate(READ, [LINK, PROPS])
        ref_edges = edges(lk)
        lk.close()
        check(f"the link page ({where}): the drawing's ground reaches the screen's edges, with no shadow over it",
              all(max(abs(a - c) for a, c in zip(px, rgb(GROUND))) <= 3 for px in ref_edges),
              f"edges {ref_edges}; ground {GROUND}")
        print(f"\n{where}: the link page's band reads {ref['order']}, {ref['buttons']}, {ref['at']} of {ref['dur']}")
        for sname, P, opener in (("Gallery", GAL, open_gallery), ("Library", LIB, open_library)):
            pg = opener(b, view, theme)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            try:
                # The same place as the link page's playhead, to the pixel it paints.
                pause_at(pg, P, (ref["head"] or 42) / 100, False)
            except Exception:                 # no band to pause: the rows below say so
                pass
            got = pg.evaluate(READ, [P, PROPS])
            check(f"{sname} ({where}): the link page's band, in its order (scrubber, clock, words, buttons) with the x in the corner",
                  got["order"] == ref["order"] and got["buttons"] == ref["buttons"] and got["strip"] and ref["strip"]
                  and got["x"] and got["x"]["shown"], f"here {got['order']} {got['buttons']}; link {ref['order']} {ref['buttons']}")
            bad = diff(ref, got)
            check(f"{sname} ({where}): ...and every part measures the same as the link page's: size, spacing, type, colours, glass",
                  not bad, "; ".join(bad[:8]) + (f" (+{len(bad) - 8} more)" if len(bad) > 8 else ""))
            check(f"{sname} ({where}): the artist's clock at the same place, and the whole of it ({ref['at']} of {ref['dur']})",
                  got["at"] == ref["at"] and got["dur"] == ref["dur"] and got["words"] == ref["words"],
                  f"here {got['at']} of {got['dur']} '{got['words']}'; link {ref['at']} of {ref['dur']} '{ref['words']}'")
            if vname == "phone" and theme == "dark":
                chips, rate = [], None
                try:
                    pg.click(P["line"] + " .rl-speed", timeout=4000)
                    pg.wait_for_timeout(300)
                    chips = pg.evaluate("(s) => [...document.querySelectorAll(s + ' .rl-chips button')].filter(b => !b.hidden).map(b => b.textContent)", P["line"])
                    pg.click(P["line"] + " .rl-chips [data-r='4']", timeout=4000)
                    pg.wait_for_timeout(300)
                    rate = pg.evaluate("(F) => document.querySelector(F + ' .skribl-inline')._skriblInline.rate()", P["frame"])
                except Exception as exc:
                    chips = [f"no speeds: {str(exc)[:80]}"]
                check(f"{sname}: the words' speed opens every one of the link page's speeds and Fit, and a pick reaches the drawing",
                      chips == ["¼×", "½×", "1×", "2×", "4×", "8×", "16×", "Fit"] and rate == 4, f"{chips} -> {rate}")
            w = pg.evaluate(WHO, P["frame"])
            ok = bool(w) and w["title"] == f"One full {TAG}" and abs(w["top"] - w["xTop"]) <= 1 and abs(w["height"] - w["xHeight"]) <= 1 \
                and abs(w["left"] - w["xRight"]) <= 1 and contrast(w["ink"], w["glass"], w["ground"]) >= 4.5
            check(f"{sname} ({where}): who drew it in the top corner, across from the x at its height, its words clear on their glass",
                  ok, str(w) + (f" contrast {contrast(w['ink'], w['glass'], w['ground']):.2f}" if w else ""))
            here_edges = edges(pg)
            want = rgb(GROUND)
            check(f"{sname} ({where}): the drawing's ground reaches the screen's edges",
                  all(max(abs(a - c) for a, c in zip(px, want)) <= 3 for px in here_edges), f"here {here_edges}; the link page's {ref_edges}")
            check(f"{sname} ({where}): no page errors", not errs, "; ".join(errs[:2]))
            pg.close()

    # A Flip: its pages in the scrubber and no Fit, as on the link page.
    pg = open_gallery(b, PHONE, "dark", FLIP)
    try:
        pg.click(GAL["line"] + " .rl-speed", timeout=4000)
        pg.wait_for_timeout(400)
        fl = pg.evaluate("""(F) => ({ chips: [...document.querySelectorAll(F + ' .rl-chips button')].filter(b => !b.hidden).map(b => b.textContent),
            words: document.querySelector(F + ' .rl-text').innerText.replace(/\\s+/g, ' ').trim() })""", GAL["frame"])
    except Exception as exc:
        fl = {"chips": [], "words": f"no words: {str(exc)[:80]}"}
    check("Gallery: a Flip says its pages and offers every speed but Fit, as everywhere",
          fl["chips"] == ["¼×", "½×", "1×", "2×", "4×", "8×", "16×"] and fl["words"].startswith("3 pages · watching at"), str(fl))
    pg.close()

    # The controls step back while it plays, and the name with them; the x
    # and the full-screen button leave.
    pg = open_gallery(b, DESK, "light")
    pg.wait_for_timeout(4200)
    asleep = pg.evaluate("""(F) => { const f = document.querySelector(F), band = f && f.querySelector(':scope > .player-bar'), who = f && f.querySelector(':scope > .fb-who');
        return f && band && who && { asleep: f.classList.contains('chrome-asleep'), band: getComputedStyle(band).opacity, who: getComputedStyle(who).opacity }; }""", GAL["frame"])
    check("Gallery: while the drawing plays the band steps back, and who drew it with it",
          bool(asleep) and asleep["asleep"] and asleep["band"] == "0" and asleep["who"] == "0", str(asleep))
    pg.mouse.move(400, 300)
    pg.mouse.move(420, 320)
    pg.wait_for_timeout(500)
    left_x = left_full = False
    try:
        pg.click(GAL["x"], timeout=4000)
        pg.wait_for_timeout(700)
        left_x = pg.evaluate("(F) => !document.querySelector(F)", GAL["frame"])
    except Exception:
        pass
    pg.close()
    pg = open_gallery(b, PHONE, "dark")
    if pg.evaluate("(s) => { const b = document.querySelector(s); if (b) b.click(); return !!b; }", GAL["full"]):
        pg.wait_for_timeout(700)
        left_full = pg.evaluate("(F) => !document.querySelector(F)", GAL["frame"])
    pg.close()
    check("Gallery: the x and the full-screen button both leave full screen", left_x and left_full, f"x {left_x}, button {left_full}")
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
