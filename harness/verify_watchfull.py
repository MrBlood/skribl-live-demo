#!/usr/bin/env python3
"""Full screen while it plays, in the Pad and Flip: the way in, the whole
screen, the band, the fade, and back.

The owner's picks from the measured mock ("I like your picks"): the way in at
the end of the line under the drawing (Flip: the end of its speed row), the
drawing as big as the screen goes, and the controls fading a moment after it
starts. One module serves both editors (lib/watchfull.js), so both are driven
the same way and asked the same things. The surfaces that show a posted
drawing -- the link page, the Gallery and the Library -- are verify_fullfade's.

WHY ITS OWN SUITE. This was verify_parity's last section until the v323 seal,
whose release run stopped verify_parity at the 600-second budget every suite
runs under (harness/run_harness.sh), with every check it had reached passing
and this section unfinished: the suite had grown to 514 s on CI and past 600 s
on the seal's box. The section moved here whole, assertions word for word, with
the three helpers it borrowed from verify_parity (ED, _fresh, _drawn), so each
suite has room again.
"""
import io
import math
import os
import sys
from assertions import make_check
import browsing
import waits

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
    from PIL import Image
except ImportError:
    print("SKIP: playwright or Pillow is not installed")
    sys.exit(0)

# Each editor: its canvas, its Play, and how to ask whether it is playing.
ED = {"/skribl-pad": ("#canvas", "#playBtn", "() => playing"), "/flip": ("#pad", "#play", "() => playing")}


def _fresh(ctx, route):
    q = ctx.new_page()
    q.goto(BASE + route, wait_until="load"); waits.settle(q, 600)
    q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    q.goto(BASE + route, wait_until="load"); waits.settle(q, 800)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return q


def _drawn(ctx, route):
    """A fresh editor with something to play: strokes on the Pad; two drawn pages on Flip."""
    q = _fresh(ctx, route)
    cv = ED[route][0]
    for k in range(2):
        bx = q.locator(cv).bounding_box()
        y = bx["y"] + bx["height"] * (0.35 + 0.2 * k)
        q.mouse.move(bx["x"] + bx["width"] * 0.25, y); q.mouse.down()
        for s in range(1, 13):
            q.mouse.move(bx["x"] + bx["width"] * (0.25 + 0.04 * s), y + 6 * math.sin(s))
        q.mouse.up(); q.wait_for_timeout(200)
        if route == "/flip" and k == 0:
            q.evaluate("() => addFrame(false)"); q.wait_for_timeout(300)
    # The first stroke arms a take on the Pad, and Play hides while one records.
    q.evaluate("() => { if (typeof endRecordingTake === 'function' && recording) endRecordingTake(); }")
    q.wait_for_timeout(300)
    return q


with sync_playwright() as p:
    b = waits.instrument(p.chromium.launch())

    # ---- full screen while it plays ---------------------------------------------
    # The owner's picks from the measured mock ("I like your picks"): the way in
    # at the end of the line under the drawing (Flip: the end of its speed row),
    # the drawing as big as the screen goes, and the controls fading a moment
    # after it starts. One module for both (lib/watchfull.js), so both are driven
    # the same way: an iPhone-sized phone with no Fullscreen API, which takes the
    # pinned stand-in (lib/immersive.js), and a desk with the real one. Visible
    # means PAINTED (elementFromPoint), and gone means not painted: a faded
    # control keeps its rect.
    print("FULL SCREEN WHILE IT PLAYS — the way in, the whole screen, the band, the fade, and back, on both editors")
    NO_API = """(() => { try {
      Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
      Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
      try { delete Element.prototype.requestFullscreen; } catch (e) {}
      try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""
    # The way in follows the speed. On a desk the Pad's Repeat sits between
    # the two; on a phone it is at the bar's end, and the line's own is not
    # drawn, so what is drawn before the way in is read, not what is there.
    FW = {"/skribl-pad": {"wrap": ".canvas-wrap", "cv": "#canvas", "btn": "#padLine .full-btn",
                          "carry": ["#playScrub", "#padBarRepeat", "#padLine"], "after": "rl-speed", "after_desk": "rl-repeat"},
          "/flip": {"wrap": ".flip-wrap", "cv": "#pad", "btn": "#flipSpeeds .full-btn",
                    "carry": ["#flipProgress", "#flipSpeeds"], "after": "seg"}}
    WAY = """(o) => { const b = document.querySelector(o.btn), c = document.querySelector(o.cv); if (!b) return null;
        const r = b.getBoundingClientRect(), cr = c.getBoundingClientRect(), t = getComputedStyle(b, '::before');
        const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        let prev = b.previousElementSibling;
        while (prev && !prev.getClientRects().length) prev = prev.previousElementSibling;
        return { painted: !!h && b.contains(h), after: prev ? prev.className : null,
                 off: r.bottom <= cr.top || r.top >= cr.bottom || r.right <= cr.left || r.left >= cr.right,
                 tap: [Math.round(r.width - 2 * (parseFloat(t.left) || 0)), Math.round(r.height - 2 * (parseFloat(t.top) || 0))] }; }"""
    FS = """(o) => { const w = document.querySelector(o.wrap), c = document.querySelector(o.cv), b = document.querySelector(o.btn);
        const r = c.getBoundingClientRect(), q = w.getBoundingClientRect(), band = w.querySelector('.watch-band');
        const paint = el => { if (!el) return false; const x = el.getBoundingClientRect(); if (!x.width || !x.height) return false;
            const h = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2); return !!h && el.contains(h); };
        return { mode: document.fullscreenElement === w ? 'api' : (w.classList.contains('is-immersive-page') ? 'stand-in' : 'page'),
                 wrap: [q.left, q.top, q.width, q.height].map(Math.round), canvas: [r.left, r.top, r.width, r.height].map(Math.round),
                 band: band ? [...band.children].map(e => e.id || e.className.split(' ')[0]) : [],
                 play: paint(w.querySelector('.watch-play')), exit: paint(w.querySelector('.watch-exit')),
                 asleep: w.classList.contains('chrome-asleep'), drawing: paint(c),
                 label: b && b.getAttribute('aria-label'), pressed: b && b.getAttribute('aria-pressed'),
                 homes: o.carry.map(s => { const e = document.querySelector(s); return e && e.parentElement ? e.parentElement.className.split(' ')[0] : null; }),
                 locked: document.documentElement.classList.contains('skribl-immersive'), vw: innerWidth, vh: innerHeight,
                 focus: !!b && document.activeElement === b }; }"""
    NIB = """() => { const n = document.querySelector('.canvas-wrap .player-nib'); if (!n || n.hidden || !(playIndex > 0)) return null;
        const r = n.getBoundingClientRect(), c = canvas.getBoundingClientRect(), lg = getCanvasLogicalSize(), p = playTimeline[playIndex - 1];
        return Math.round(Math.hypot(r.left + r.width / 2 - (c.left + p.x * c.width / lg.width),
                                     r.top + r.height / 2 - (c.top + p.y * c.height / lg.height))); }"""
    POINTS = "() => frames.reduce((n, f) => n + f.strokes.length, 0)"
    AE = "() => { const a = document.activeElement; return a ? (a.id || a.className || a.tagName) : null; }"
    PAINTED = """(sel) => { const el = document.querySelector(sel); if (!el) return false; const x = el.getBoundingClientRect();
        if (!x.width || !x.height) return false;
        const h = document.elementFromPoint(x.left + x.width / 2, x.top + x.height / 2); return !!h && el.contains(h); }"""

    def _band(q, sel):
        """A press on a control in the band, as a person makes it: a faded band is woken first, so a
        regression that leaves it faded is a red row below, not a click that waits out its timeout."""
        if q.evaluate("() => !!document.querySelector('.chrome-asleep')"):
            q.mouse.move(5, 5); q.mouse.move(25, 25); q.wait_for_timeout(450)
        q.click(sel)

    def _fills(s, page):
        """Over the whole screen, the drawing as big as it allows, centred, in the page's shape."""
        cw, ch = s["canvas"][2], s["canvas"][3]
        whole = (abs(cw - s["vw"]) <= 1 and abs(s["canvas"][1] * 2 + ch - s["vh"]) <= 2) or \
                (abs(ch - s["vh"]) <= 1 and abs(s["canvas"][0] * 2 + cw - s["vw"]) <= 2)
        return whole and s["wrap"] == [0, 0, s["vw"], s["vh"]] and abs(cw / ch - page["canvas"][2] / page["canvas"][3]) < 0.02

    def _long_pad(ctx):
        """The Pad with a take whose replay outlasts every wait below at the slowest speed: four slow strokes."""
        q = _fresh(ctx, "/skribl-pad")
        for k in range(4):
            bx = q.locator("#canvas").bounding_box()
            y = bx["y"] + bx["height"] * (0.25 + 0.16 * k)
            q.mouse.move(bx["x"] + bx["width"] * 0.2, y); q.mouse.down()
            for s in range(1, 31):
                q.mouse.move(bx["x"] + bx["width"] * (0.2 + 0.02 * s), y + 8 * math.sin(s / 3)); q.wait_for_timeout(30)
            q.mouse.up(); q.wait_for_timeout(200)
        q.evaluate("() => { if (typeof endRecordingTake === 'function' && recording) endRecordingTake(); }")
        q.wait_for_timeout(300)
        return q

    for _route, _o in FW.items():
        _name = "Pad" if _route == "/skribl-pad" else "Flip"
        for _dev, _opts in (("phone", {"viewport": {"width": 402, "height": 874}, "is_mobile": True, "has_touch": True}),
                            ("desk", {"viewport": {"width": 1333, "height": 906}})):
            _fc = b.new_context(**_opts)
            if _dev == "phone":
                _fc.add_init_script(NO_API)
            _q = _long_pad(_fc) if _route == "/skribl-pad" else _drawn(_fc, _route)
            if _route == "/skribl-pad":
                _q.evaluate("() => setPreviewSpeed(0.25)")
            _q.click(ED[_route][1]); _q.wait_for_timeout(500)
            _tag = f"{_route} on a {_dev}"
            _w = _q.evaluate(WAY, _o)
            check(f"{_tag}: the way in sits at the end of the {'line under the drawing' if _name == 'Pad' else 'speed row'}, "
                  "painted, off the drawing and 44px to tap",
                  bool(_w) and _w["painted"] and _w["off"] and _o.get("after_" + _dev, _o["after"]) in (_w["after"] or "")
                  and min(_w["tap"]) >= 44, str(_w))
            _page = _q.evaluate(FS, _o)
            _q.click(_o["btn"]); _q.wait_for_timeout(600)
            _s = _q.evaluate(FS, _o)
            check(f"{_tag}: it opens over the whole screen ({'the stand-in' if _dev == 'phone' else 'the real API'}), "
                  "the drawing as big as the screen allows, centred, in its own shape",
                  _s["mode"] == ("stand-in" if _dev == "phone" else "api") and _fills(_s, _page)
                  and _s["canvas"][2] > _page["canvas"][2], f"page {_page['canvas']} -> {_s}")
            # NO SHADOW ON ANY FULL SCREEN (the owner's yes, Q6). The Pad's frame is
            # the link page's .canvas-wrap, and wore its inset vignette at the
            # screen's edges; Flip's never did. Asked of both as a property, and
            # of the Pad, which could show it, as what is painted at each edge.
            _sh = _q.evaluate("(o) => [o.wrap, o.cv].map(s => getComputedStyle(document.querySelector(s)).boxShadow)", _o)
            check(f"{_tag}: no shadow round the screen's edges, the frame's or the drawing's, as on every full screen",
                  _sh == ["none", "none"], str(_sh))
            if _name == "Pad":
                _sty = _q.add_style_tag(content=".watch-band, .watch-exit { visibility: hidden !important; }")
                _q.wait_for_timeout(150)
                _im = Image.open(io.BytesIO(_q.screenshot())).convert("RGB")
                _q.evaluate("(el) => el.remove()", _sty)
                _gw, _gh = _im.size
                _gnd = _q.evaluate("(o) => (getComputedStyle(document.querySelector(o.wrap)).backgroundColor.match(/\\d+/g) || []).slice(0, 3).map(Number)", _o)
                _px = [_im.getpixel(xy) for xy in ((2, _gh // 2), (_gw - 3, _gh // 2), (_gw // 2, 2), (_gw // 2, _gh - 3))]
                check(f"{_tag}: ...and the drawing's ground reaches every edge of the screen, painted, with no shadow over it",
                      len(_gnd) == 3 and all(max(abs(a - c) for a, c in zip(px, _gnd)) <= 3 for px in _px),
                      f"edges {_px}, ground {_gnd}")
            check(f"{_tag}: the band carries the editor's own controls, with Play and a way out painted",
                  _s["band"] == [x[1:] for x in _o["carry"]] + ["watch-row"] and _s["play"] and _s["exit"]
                  and _s["label"] == "Leave full screen" and _s["pressed"] == "true", str(_s))
            if _route == "/flip":
                # Flip's page rules (body.playing) outrank a plain band rule: two
                # did, and the band kept the page's 3px line. It is the link page's.
                _lk = _q.evaluate("""() => { const p = document.getElementById('flipProgress'), f = p.querySelector('.player-progress-fill');
                    return { h: getComputedStyle(p).height, r: getComputedStyle(p).borderTopLeftRadius,
                             fill: getComputedStyle(f).borderTopLeftRadius, pad: getComputedStyle(document.getElementById('flipSpeeds')).paddingLeft }; }""")
                check(f"{_tag}: in the band, the progress line is the link page's, 6px and round, and the speed row sits flush",
                      _lk == {"h": "6px", "r": "999px", "fill": "999px", "pad": "0px"}, str(_lk))
            if _route == "/skribl-pad":
                _gap = []
                for _k in range(3):
                    _q.wait_for_timeout(250); _gap.append(_q.evaluate(NIB))
                check(f"{_tag}: the replay's pen dot rides the point being drawn, in the middle of the screen",
                      all(g is not None and g <= 2 for g in _gap), str(_gap))
            # THE SPEED, FROM THE BAND. The owner: the controls "should be there
            # in case you want to adjust the speed". Changed without leaving, the
            # drawing playing on; the Pad's chooser is a menu, and an open menu
            # keeps them up however long it is open.
            if _route == "/skribl-pad":
                _sp = {"opener": _q.evaluate(PAINTED, ".watch-band .rl-speed")}
                if _sp["opener"]:
                    _band(_q, ".watch-band .rl-speed"); _q.wait_for_timeout(3000)
                    _sp.update(asleep=_q.evaluate(FS, _o)["asleep"], half=_q.evaluate(PAINTED, ".watch-band [data-r='0.5']"))
                check(f"{_tag}: the speed opens from the band, and stays up as long as it is open",
                      _sp["opener"] and _sp.get("half") and _sp.get("asleep") is False, str(_sp))
                if _sp.get("half"):
                    _band(_q, ".watch-band [data-r='0.5']"); _q.wait_for_timeout(200)
                    _sp["picked"] = _q.evaluate("() => [replayChoice, playing && !playPaused, !!document.querySelector('.watch-band')]")
                    _band(_q, ".watch-band .rl-speed"); _band(_q, ".watch-band [data-r='0.25']")
                check(f"{_tag}: ...and a speed picked there takes, in full screen, the drawing playing on",
                      _sp.get("picked") == [0.5, True, True], str(_sp))
            else:
                _sp = {"half": _q.evaluate(PAINTED, ".watch-band [data-rate='0.5']")}
                if _sp["half"]:
                    _band(_q, ".watch-band [data-rate='0.5']"); _q.wait_for_timeout(200)
                    _sp["picked"] = _q.evaluate("() => [flipRate, playing && !playPaused, !!document.querySelector('.watch-band')]")
                    _band(_q, ".watch-band [data-rate='1']")
                check(f"{_tag}: a speed picked in the band takes, in full screen, the drawing playing on",
                      _sp.get("picked") == [0.5, True, True], str(_sp))
            if _dev == "phone":
                # TURNED ON ITS SIDE AND BACK, it fits each screen: each editor's
                # own layout asks full screen first (layoutEditorCanvas, fitPad).
                _turn = []
                for _vp in ({"width": 874, "height": 402}, {"width": 402, "height": 874}):
                    _q.set_viewport_size(_vp); _q.wait_for_timeout(400)
                    _turn.append(_q.evaluate(FS, _o))
                check(f"{_tag}: turned on its side and back, the drawing fills each screen it is given, centred, in its own shape",
                      all(_fills(_t, _page) for _t in _turn), " | ".join(f"{_t['vw']}x{_t['vh']}: {_t['canvas']}" for _t in _turn))
            _q.wait_for_timeout(3000)
            _z = _q.evaluate(FS, _o)
            check(f"{_tag}: a quiet spell while it plays puts the controls away and leaves the drawing",
                  _z["asleep"] and not _z["play"] and not _z["exit"] and _z["drawing"], str(_z))
            _c = _q.locator(_o["cv"]).bounding_box()
            _mid = (_c["x"] + _c["width"] / 2, _c["y"] + _c["height"] / 2)
            if _dev == "phone":
                # A FINGER'S FIRST TAP ON A FADED SCREEN ONLY BRINGS THE CONTROLS
                # BACK (the owner: "matching how video apps work"), so the speed
                # can be reached without stopping the drawing; with them up, a
                # tap pauses, as it does on the page.
                _q.touchscreen.tap(*_mid); _q.wait_for_timeout(300)
                _t1, _on1 = _q.evaluate(FS, _o), _q.evaluate("() => playing && !playPaused")
                check(f"{_tag}: a finger's first tap on the faded screen only brings the controls back; the drawing plays on",
                      not _t1["asleep"] and _t1["play"] and _t1["exit"] and _on1, f"{_t1}; plays on {_on1}")
                _q.touchscreen.tap(*_mid); _q.wait_for_timeout(300)
                _t2, _p2 = _q.evaluate(FS, _o), _q.evaluate("() => playPaused")
                check(f"{_tag}: ...and with them up, the next tap pauses it, as on the page",
                      _p2 and not _t2["asleep"] and _t2["play"], f"{_t2}; paused {_p2}")
                _q.touchscreen.tap(*_mid); _q.wait_for_timeout(300)    # on again, for the band's own Play below
            else:
                _q.mouse.move(40, 40); _q.mouse.move(60, 70); _q.wait_for_timeout(450)
                _m = _q.evaluate(FS, _o)
                check(f"{_tag}: ...and a mouse that moves brings them back", not _m["asleep"] and _m["play"] and _m["exit"], str(_m))
            _band(_q, ".watch-play"); _q.wait_for_timeout(3000)
            _p = _q.evaluate(FS, _o)
            check(f"{_tag}: paused from the band, they stay up however long it rests",
                  _q.evaluate("() => playPaused") and not _p["asleep"] and _p["play"], str(_p))
            _band(_q, ".watch-play")
            if _dev == "desk":      # the mouse comes to rest on the drawing, and the spell runs out under it
                _q.mouse.move(*_mid)
            _q.wait_for_timeout(3000)
            check(f"{_tag}: ...and go again once it plays on", _q.evaluate(FS, _o)["asleep"]
                  and _q.evaluate("() => playing && !playPaused"))
            if _dev == "desk":
                # A MOUSE'S CLICK IS A PAUSE, faded or not: a video app on a desk
                # takes it so. Only a finger's first tap is held back.
                _q.mouse.down(); _q.mouse.up(); _q.wait_for_timeout(300)
                _k = _q.evaluate(FS, _o)
                check(f"{_tag}: a click on the faded drawing pauses it at once, and the controls come back",
                      _q.evaluate("() => playPaused") and not _k["asleep"] and _k["play"], str(_k))
                _q.mouse.down(); _q.mouse.up(); _q.wait_for_timeout(300)    # and on again, as it was
            if _route == "/skribl-pad":
                # WATCHED TO ITS END, in full screen: it stays full screen with
                # its controls up and Play to see it again; then they step back
                # after a quiet spell, so the finished drawing is seen whole
                # (the owner, after the full-screen A/B); a tap or a move brings
                # them back without playing it; and Play plays it from the top.
                _q.evaluate("() => setPreviewSpeed(16)")
                for _w8 in range(40):
                    if not _q.evaluate("() => playing"):
                        break
                    _q.wait_for_timeout(200)
                _q.wait_for_timeout(300)
                _f = _q.evaluate(FS, _o)
                _f["label"] = _q.evaluate("() => document.querySelector('.watch-play').getAttribute('aria-label')")
                check(f"{_tag}: watched to its end, it stays full screen with its controls up and Play to see it again",
                      not _q.evaluate("() => playing") and _f["mode"] != "page" and not _f["asleep"] and _f["play"]
                      and _f["exit"] and _f["label"] == "Play", str(_f))
                _q.wait_for_timeout(2800)      # longer than a quiet spell
                _r8 = _q.evaluate(FS, _o)
                check(f"{_tag}: ...then they step back after a quiet spell, and the finished drawing is whole",
                      not _q.evaluate("() => playing") and _r8["mode"] != "page" and _r8["asleep"]
                      and not _r8["play"] and not _r8["exit"] and _r8["drawing"], str(_r8))
                if _dev == "phone":
                    _q.touchscreen.tap(*_mid)
                else:
                    _q.mouse.move(_mid[0] + 30, _mid[1] + 20)
                _q.wait_for_timeout(400)
                _w8 = _q.evaluate(FS, _o)
                check(f"{_tag}: ...and a " + ("tap" if _dev == "phone" else "mouse that moves") + " brings them back, without playing it",
                      not _q.evaluate("() => playing") and not _w8["asleep"] and _w8["play"] and _w8["exit"], str(_w8))
                _q.evaluate("() => setPreviewSpeed(0.25)")
                _band(_q, ".watch-play"); _q.wait_for_timeout(400)
                check(f"{_tag}: ...and Play in the band plays it again, from the top",
                      _q.evaluate("() => playing && !playPaused && playIndex < playTimeline.length / 2"))
            if _route == "/flip":
                # NOTHING DRAWS IN FULL SCREEN. Flip's canvas takes a stroke the
                # moment its preview stops; the Pad's finished take is locked
                # anyway, so this is pinned where it can fail.
                _q.evaluate("() => stop()"); _q.wait_for_timeout(400)
                _n0 = _q.evaluate(POINTS)
                _bx = _q.locator("#pad").bounding_box()
                _q.mouse.move(_bx["x"] + _bx["width"] * 0.3, _bx["y"] + _bx["height"] * 0.5); _q.mouse.down()
                _q.mouse.move(_bx["x"] + _bx["width"] * 0.6, _bx["y"] + _bx["height"] * 0.55, steps=6); _q.mouse.up()
                _q.wait_for_timeout(300)
                _r = _q.evaluate(FS, _o)
                check(f"{_tag}: once it stops, a stroke on the drawing draws nothing, and the controls are up",
                      _q.evaluate(POINTS) == _n0 and not _r["asleep"] and _r["play"], f"points {_n0} -> {_q.evaluate(POINTS)}; {_r}")
                # Playing again from the band, so the page it goes back to is
                # the one it left: Flip's speed row only shows while it plays.
                _band(_q, ".watch-play"); _q.wait_for_timeout(400)
                check(f"{_tag}: ...and Play in the band plays it again", _q.evaluate("() => playing && !playPaused"))
            _band(_q, ".watch-exit"); _q.wait_for_timeout(600)
            _x = _q.evaluate(FS, _o)
            check(f"{_tag}: the way out puts back the page: the drawing at its size, the controls where they were",
                  _x["mode"] == "page" and _x["canvas"] == _page["canvas"] and _x["homes"] == _page["homes"]
                  and _x["label"] == "Full screen" and _x["pressed"] == "false" and not _x["locked"] and not _x["band"],
                  f"page {_page['canvas']} {_page['homes']} -> {_x}")
            check(f"{_tag}: ...and the x hands focus back to the way in, as a dialog gives it back to what opened it",
                  _x["focus"], _q.evaluate("() => document.activeElement && (document.activeElement.className || document.activeElement.tagName)"))
            if _dev == "phone":
                if not _q.evaluate(ED[_route][2]):
                    _q.click(ED[_route][1]); _q.wait_for_timeout(400)
                _e0 = None      # the way in, if the way out put it back
                if _q.evaluate(PAINTED, _o["btn"]):
                    _q.click(_o["btn"]); _q.wait_for_timeout(500)
                    _e0 = _q.evaluate(FS, _o)["mode"]
                    _q.keyboard.press("Escape"); _q.wait_for_timeout(500)
                _e = _q.evaluate(FS, _o)
                check(f"{_tag}: Escape leaves the stand-in too, and lets the page scroll again",
                      _e0 == "stand-in" and _e["mode"] == "page" and not _e["locked"], f"{_e0} -> {_e['mode']}, locked {_e['locked']}")
            else:
                # The browser can drop focus to the page as it leaves its full
                # screen, before fullscreenchange arrives: the v323 release run
                # read <body> here on a loaded box, where CI and a quiet box read
                # the way in. Dropped on purpose, so the race is driven every time.
                if not _q.evaluate(ED[_route][2]):
                    _q.click(ED[_route][1]); _q.wait_for_timeout(400)
                _d0 = None
                if _q.evaluate(PAINTED, _o["btn"]):
                    _q.click(_o["btn"]); _q.wait_for_timeout(600)
                    _d0 = _q.evaluate(FS, _o)["mode"]
                    _q.evaluate("""(w) => { const x = document.querySelector(w + ' .watch-exit'); x.focus();
                        document.activeElement.blur(); document.exitFullscreen(); }""", _o["wrap"])
                    _q.wait_for_timeout(600)
                _d = _q.evaluate(FS, _o)
                check(f"{_tag}: ...and focus comes back to the way in even when the browser drops it on the way out",
                      _d0 == "api" and _d["mode"] == "page" and _d["focus"],
                      f"{_d0} -> {_d['mode']}, focus on {_q.evaluate(AE)}")
            _fc.close()

    # NEVER MAGNIFIED: full screen is the whole drawing. Flip fits its
    # magnifier on Play; the Pad keeps it, so a Pad zoomed in on a detail goes
    # full screen as the whole drawing and comes back to it still magnified.
    _zc = b.new_context(viewport={"width": 1333, "height": 906})
    _q = _drawn(_zc, "/skribl-pad")
    _q.evaluate("() => { ZoomView.enable(); ZoomView.setPct(200); }"); _q.wait_for_timeout(400)
    _q.click("#playBtn"); _q.wait_for_timeout(300)
    _q.evaluate("() => pausePlayback()"); _q.wait_for_timeout(200)
    _zo = FW["/skribl-pad"]
    _zp = _q.evaluate(FS, _zo)
    _q.click(_zo["btn"]); _q.wait_for_timeout(600)
    _zs = _q.evaluate(FS, _zo)
    check("/skribl-pad on a desk, magnified to 200%: full screen is the whole drawing, never magnified",
          _q.evaluate("() => ZoomView.get().zoom") > 1.9 and _zs["mode"] == "api" and _fills(_zs, _zp), f"page {_zp['canvas']} -> {_zs}")
    _band(_q, ".watch-exit"); _q.wait_for_timeout(600)
    _zx = _q.evaluate(FS, _zo)
    check("/skribl-pad on a desk: ...and back on the page it is magnified as it was",
          _zx["mode"] == "page" and _zx["canvas"] == _zp["canvas"] and _q.evaluate("() => ZoomView.get().zoom") > 1.9,
          f"{_zp['canvas']} -> {_zx['canvas']}")
    _zc.close()

    b.close()

summarise_and_exit()
