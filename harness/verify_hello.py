#!/usr/bin/env python3
"""Blooby says hi: the first time Skribl opens on a phone (lib/hello.js, FUTURE.md 6m).

The owner's picks, each a row below: he walks up from far away on his star,
waves once and fades into the canvas, full width and sharp on a 3x phone; once
only, a tap skips him (and draws nothing), a still hello under Reduce Motion,
the same on Flip with one "seen" for both, never on a desk or in a composer's
frame, and nothing fetched when he does not come.

Automation never meets him unless it asks (window.__skriblHelloForce): every
other suite opens a fresh browser and would otherwise find him over its first
canvas. So this suite asks, and one row proves that without asking he stays
away.

Visible means PAINTED: elementFromPoint at the screen's middle lands inside
him. Gone means removed, and the canvas painted there again.

A slow line is a row too: when his player is not here within hello.js's LATE
he does not come that time and is not marked seen, so the next open shows him.
The v327 seal run met that path by accident, on a server's first page (see the
warm-up below), and read it as a failure; this row meets it on purpose.
"""
import os
import sys
import time
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
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True,
             screen={"width": 402, "height": 874})
DESK = dict(viewport={"width": 1333, "height": 906})
FORCE = "window.__skriblHelloForce = true;"
ST = """() => { const h = document.getElementById('skriblHello'), c = h && h.querySelector('canvas');
  const at = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
  return { here: !!h, painted: !!h && !h.hidden && !!at && h.contains(at), on: !!h && h.classList.contains('is-on'),
           bg: h ? getComputedStyle(h).backgroundColor : null,
           css: c ? Math.round(c.getBoundingClientRect().width) : 0, px: c ? c.width : 0,
           canvasThere: !!at && (at.id === 'canvas' || at.id === 'pad' || !!(at.closest && at.closest('.canvas-wrap, .flip-wrap'))),
           seen: (() => { try { return localStorage.getItem('skribl.hello.v1'); } catch (e) { return 'n/a'; } })(),
           playing: !!(window.__hpState), state: h && window.SkriblInline ? (SkriblInline.players().map(p => p.state().state)) : [] }; }"""


def _open(ctx, route, force=True, fetched=None):
    if force:
        ctx.add_init_script(FORCE)
    q = ctx.new_page()
    if fetched is not None:
        q.on("request", lambda r: fetched.append(r.url) if "blooby-hello" in r.url else None)
    q.goto(BASE + route, wait_until="load")
    return q


def _until(q, cond, ms):
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        s = q.evaluate(ST)
        if cond(s):
            return s, round((time.time() - t0) * 1000)
        q.wait_for_timeout(40)
    return q.evaluate(ST), None


with sync_playwright() as p:
    b = p.chromium.launch()
    print("BLOOBY SAYS HI — the first open on a phone")

    # WARM THE SERVER FIRST. A fresh server trims the comments out of each
    # script on its first request (security.py; about 3 s of lexing for the
    # Pad's 107 files here), and his player waits in that queue: on a server's
    # first page he came about 0.2 s inside his 4 s, and in the v327 seal run,
    # where this suite had a fresh server to itself, he missed it. This suite
    # is about him, not a cold server, so both editors are opened once in a
    # context of their own; every row below still opens a fresh browser.
    w = b.new_context(**PHONE)
    for route in ("/skribl-pad", "/flip"):
        _open(w, route)
    w.close()

    for scheme in ("light", "dark"):
        c = b.new_context(color_scheme=scheme, **PHONE)
        got = []
        q = _open(c, "/skribl-pad", fetched=got)
        s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
        check(f"Pad, phone, {scheme}: the first open shows him over the whole screen, in his own lilac",
              ms is not None and s["bg"] == "rgb(205, 191, 255)", f"{s} after {ms} ms")
        if scheme == "light":
            check("...full width, his drawing at the screen's own sharpness (3 pixels a point)",
                  s["css"] == 402 and s["px"] >= 3 * s["css"] - 3, f"{s['css']} css px drawn at {s['px']}")
            check("...and the first open is remembered as seen", s["seen"] == "1", str(s["seen"]))
            # The walk-up is 3.4 s and the wave 2 s: he stays for the whole of it.
            q.wait_for_timeout(3000)
            mid = q.evaluate(ST)
            check("...he is still there through the walk-up, playing",
                  mid["painted"] and "playing" in mid["state"], str(mid))
            s2, ms2 = _until(q, lambda s: not s["here"], 6000)
            check("...then, his wave done, he fades and is gone, the canvas there again",
                  ms2 is not None and s2["canvasThere"], f"{s2} after a further {ms2} ms")
            q.reload(wait_until="load")
            q.wait_for_timeout(2500)
            again = q.evaluate(ST)
            check("...and never again: the next open goes straight to the canvas",
                  not again["painted"] and again["canvasThere"] and len(got) == 1,
                  f"{again}, the hello fetched {len(got)} time(s)")
        c.close()

    # A tap skips him, and the tap draws nothing.
    c = b.new_context(**PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    q.touchscreen.tap(201, 437)
    s2, ms2 = _until(q, lambda s: not s["here"], 1500)
    ink = q.evaluate("() => { const h = document.getElementById('canvasEmptyHint'); return h && !h.classList.contains('hidden'); }")
    check("a tap skips him at once (gone within the half-second fade), and draws nothing on the canvas",
          ms is not None and ms2 is not None and ms2 <= 900 and ink, f"gone after {ms2} ms; words still up: {ink}")
    c.close()

    # Reduce Motion: a still hello, then the fade.
    c = b.new_context(reduced_motion="reduce", **PHONE)
    q = _open(c, "/skribl-pad")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    states = set()
    t0 = time.time()
    while time.time() - t0 < 1.2:
        states.update(q.evaluate(ST)["state"])
        q.wait_for_timeout(100)
    s2, ms2 = _until(q, lambda s: not s["here"], 4000)
    check("Reduce Motion: a still hello (never playing), then he fades and is gone",
          ms is not None and "playing" not in states and ms2 is not None, f"states {sorted(states)}, gone after a further {ms2} ms")
    c.close()

    # A slow line: his player held for 5 s, past his 4. The page's load waits
    # for that script, so this open waits only for the page's own parse.
    c = b.new_context(**PHONE)
    c.add_init_script(FORCE)
    held = []
    c.route("**/inlineplayer.js*", lambda r: held.append(r))
    q = c.new_page()
    q.goto(BASE + "/skribl-pad", wait_until="domcontentloaded")
    q.wait_for_timeout(5000)
    s = q.evaluate(ST)
    for r in held:
        r.continue_()
    c.unroute("**/inlineplayer.js*")
    q.wait_for_timeout(1000)
    s1 = q.evaluate(ST)
    q.reload(wait_until="load")
    s2, ms2 = _until(q, lambda s: s["painted"] and s["on"], 8000)
    check("a slow line: his player 5 s late, he does not come (the canvas there, nothing marked seen, "
          "and not when it does arrive), and the next open shows him",
          len(held) == 1 and not s["painted"] and s["canvasThere"] and s["seen"] is None
          and not s1["painted"] and s1["seen"] is None and ms2 is not None and s2["seen"] == "1",
          f"held {len(held)}; at 5 s {s}; once it came {s1}; next open {s2} after {ms2} ms")
    c.close()

    # Flip: the same hello, and one "seen" for both editors.
    c = b.new_context(**PHONE)
    q = _open(c, "/flip")
    s, ms = _until(q, lambda s: s["painted"] and s["on"], 8000)
    check("Flip, phone: the same hello on its first open", ms is not None and s["css"] == 402, f"{s} after {ms} ms")
    q.touchscreen.tap(201, 437)
    _until(q, lambda s: not s["here"], 1500)
    q.goto(BASE + "/skribl-pad", wait_until="load")
    q.wait_for_timeout(2500)
    pad = q.evaluate(ST)
    check("...and seen once is seen for both: the Pad does not show him again", not pad["painted"] and pad["seen"] == "1", str(pad))
    c.close()

    # Where he never comes, and fetches nothing.
    for name, opts, route, force in (("a desk", DESK, "/skribl-pad", True),
                                     ("a composer's frame (?compose=1)", PHONE, "/skribl-pad?compose=1", True),
                                     ("automation that does not ask", PHONE, "/skribl-pad", False)):
        c = b.new_context(**opts)
        got = []
        q = _open(c, route, force=force, fetched=got)
        q.wait_for_timeout(3000)
        s = q.evaluate(ST)
        check(f"never on {name}, and nothing of his is fetched",
              not s["painted"] and s["seen"] != "1" and not got, f"{s}, fetched {got}")
        c.close()

    b.close()

summarise_and_exit()
