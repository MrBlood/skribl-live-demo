#!/usr/bin/env python3
"""The viewing pages' edges a read-only review found after v326.

The Gallery's card, the Gallery's and the Library's full screen, the
Library's stage and the box a post plays in. Each row is driven on the real
page and each was red on the code before its fix:

  * leaving the Gallery's full screen puts the card back on top, where it
    left the card see-through over a blank canvas;
  * the speeds stay open while the drawing plays in full screen, where they
    faded away with the rest of the band;
  * Loop turned off in the Library's full screen reads off on the page, and
    one press turns it back on, where the page's stayed lit and took two;
  * the Library's full screen names who drew it from the listing, where it
    printed the signed-in id as a name and an @handle;
  * a card with sound offers Unmute before its first play, where it said
    "This Skribl has no sound", greyed out;
  * the card's scrubber takes focus and moves on a key, as every other one
    here does;
  * the card names Loop and Mute as its own full screen, the link page and
    the Library do;
  * the Library's Play and Mute, and the box a post plays in, say by name
    what a press does next ("Pause this Skribl" while it plays);
  * the Gallery's words: "come alive" for a Pad or a Flip, and the empty
    state names the switch an author can use later, in the Library;
  * a Flip at its end shows its last page whole: played once with Loop off,
    taken to its end on the scrubber, and at rest with no card (a draft in a
    host's composer), where the player's clock came round to its first page,
    blank where that page draws itself (after v327);
  * every colour the Gallery and the Library declare is read by the page or
    by something it loads.
"""
import base64
import io
import json
import math
import os
import re
import struct
import sys
import urllib.request
import wave

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the viewing pages are right.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)
TAG = "view" + os.urandom(3).hex()

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
# The owner's iPhone has no Fullscreen API for a page: the stage is pinned
# over the viewport instead (lib/immersive.js), as verify_onefull drives it.
NO_API = """(() => { try {
  Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true });
  Object.defineProperty(Document.prototype, 'webkitFullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
  try { delete Element.prototype.requestFullscreen; } catch (e) {}
  try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""


def post(body):
    rq = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read())


def wav():
    b = io.BytesIO()
    w = wave.open(b, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(i / 7))) for i in range(16000)))
    w.close()
    return "data:audio/wav;base64," + base64.b64encode(b.getvalue()).decode()


def ring(r, n, gap, color):
    return [{"x": round(201 + r * math.cos(i / n * 6.283), 1), "y": round(380 + r * math.sin(i / n * 6.283), 1),
             "color": color, "t": i * gap, "start": i == 0, "size": 4 + 3 * math.sin(i / n * math.pi)}
            for i in range(n + 1)]


def drawing(title, n, music=False):
    frame = {"strokes": ring(150, n, 50, "#7c5cff"), "strokeGroups": [n + 1], "background": {"color": "#2e1b52"}}
    if music:
        frame["music"] = {"data": wav(), "name": "t.wav", "trimStart": 0, "trimEnd": 2}
    return post({"title": title, "version": 2, "schemaVersion": 2, "visibility": "public",
                 "playbackMode": "replay", "canvasSize": {"cssWidth": 402, "cssHeight": 760}, "frames": [frame]})


# Twenty seconds of replay with music, and forty without: long enough to
# still be playing when a row has waited out the controls' fade.
SOUND = drawing(f"View sound {TAG}", 400, music=True)
SILENT = drawing(f"View silent {TAG}", 800)

# A FLIP WHOSE ENDS DIFFER: its first page draws itself (blank at its start),
# its last is still, and each page's mark has a corner of its own, so a
# reading says which page is on screen and whether it is whole.
FLIP_AT = {"first": (100, 150), "middle": (201, 380), "last": (300, 610)}


def mark(at, color, gap):
    cx, cy = FLIP_AT[at]
    return [{"x": round(cx + 60 * math.cos(i / 24 * 6.283), 1), "y": round(cy + 60 * math.sin(i / 24 * 6.283), 1),
             "color": color, "t": i * gap, "start": i == 0, "size": 10} for i in range(25)]


FLIP = post({"title": f"View flip {TAG}", "version": 2, "schemaVersion": 2, "visibility": "public",
             "playbackMode": "flip", "fps": 6, "canvasSize": {"cssWidth": 402, "cssHeight": 760},
             "frames": [{"strokes": mark("first", "#7c5cff", 40), "strokeGroups": [25], "draw": True,
                         "background": {"color": "#2e1b52"}},
                        {"strokes": mark("middle", "#7c5cff", 0), "strokeGroups": [25], "hold": 2},
                        {"strokes": mark("last", "#ff48b0", 0), "strokeGroups": [25], "hold": 2}]})

# Which corners carry ink, read off the canvas the box paints: a mark is a
# ring of ten-pixel line, so a corner with a few hundred pixels off the ground
# is drawn and one with none is not.
INK = """(box) => { const c = box && box.querySelector('.skribl-inline-canvas');
  if (!c || !c.width) return null;
  const x = c.getContext('2d'), k = c.width / 402, g = x.getImageData(2, 2, 1, 1).data, out = {};
  for (const [name, [cx, cy]] of Object.entries(%s)) {
    const d = x.getImageData(Math.round((cx - 75) * k), Math.round((cy - 75) * k), Math.round(150 * k), Math.round(150 * k)).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - g[0]) + Math.abs(d[i + 1] - g[1]) + Math.abs(d[i + 2] - g[2]) > 60) n++;
    out[name] = n; }
  return out; }""" % json.dumps(FLIP_AT)


def last_page(ink):
    return bool(ink) and ink["last"] > 300 and ink["first"] == 0 and ink["middle"] == 0

FULL = {"gallery": ".tileStage.watch-full:is(:fullscreen, .is-immersive-page)",
        "library": ".stageCanvasWrap.watch-full:is(:fullscreen, .is-immersive-page)"}


def themed(b, view, theme="dark", phone_api=False):
    pg = b.new_page(color_scheme=theme, **view)
    if view is PHONE and not phone_api:
        pg.add_init_script(NO_API)
    pg.add_init_script(f"try {{ localStorage.setItem('skribl_theme_v1', '{theme}'); }} catch (e) {{}}")
    return pg


CARD = """([id, sel]) => { const box = document.querySelector(`.skribl-inline[data-skribl-id="${id}"]`);
  const tile = box && box.closest('.tile'); return tile ? tile.querySelector('.skfull-card ' + sel) : null; }"""


def card(pg, item, sel, js):
    return pg.evaluate("([id, sel, js]) => { const box = document.querySelector(`.skribl-inline[data-skribl-id=\"${id}\"]`);"
                       " const tile = box && box.closest('.tile'); const el = tile && tile.querySelector('.skfull-card ' + sel);"
                       " return el ? (new Function('el', 'box', js))(el, box) : null; }", [item["id"], sel, js])


def gallery(b, view, theme="dark"):
    pg = themed(b, view, theme)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_selector(f".skribl-inline[data-skribl-id='{SILENT['id']}']", state="attached", timeout=20000)
    pg.wait_for_timeout(600)
    return pg


def library(b, view, item, theme="light", kind="pad", pages=1):
    pg = themed(b, view, theme)
    seed = json.dumps([{"id": item["id"], "url": item.get("url"), "title": item.get("title") or "", "kind": kind,
                        "pages": pages, "visibility": "public"}])
    pg.add_init_script("try { localStorage.setItem('skribl_posted_v1', %s); } catch (e) {}" % json.dumps(seed))
    browsing.goto(pg, BASE, "/library")
    pg.wait_for_timeout(800)
    pg.evaluate("() => { const r = document.querySelector('#postedList .posted-row .posted-main'); if (r) r.click(); }")
    pg.wait_for_function("() => { const b = document.getElementById('btnPlay'); return b && !b.disabled; }", timeout=15000)
    pg.wait_for_timeout(400)
    return pg


STAGE = "() => { const b = document.querySelector('.stageCanvasWrap .skribl-inline'); return b && b._skriblInline; }"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    # ------------------------------------------------------------ the card
    print("\nTHE GALLERY'S CARD, on the owner's phone")
    pg = gallery(b, PHONE)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    m = card(pg, SOUND, ".skfull-mute", "return { disabled: el.disabled, label: el.getAttribute('aria-label'), title: el.title,"
             " shown: !el.hidden && getComputedStyle(el).display !== 'none', loaded: !!(box._skriblInline && box._skriblInline.state().loaded) };")
    check("a card with sound offers Unmute before its first play, not 'This Skribl has no sound'",
          bool(m) and not m["loaded"] and m["shown"] and not m["disabled"] and m["label"] == "Unmute", str(m))
    lp = card(pg, SOUND, ".skfull-loop", "return { label: el.getAttribute('aria-label'), title: el.title };")
    check("the card names Loop and Mute as the band, the link page and the Library do",
          bool(lp) and lp["label"] == "Loop" and lp["title"] in ("Repeating", "Plays once")
          and bool(m) and m["label"] in ("Mute", "Unmute") and m["title"] in ("Sound is on", "Sound is off"), f"loop {lp}; mute {m}")

    # The scrubber: a slider Tab reaches, and a key moves.
    card(pg, SILENT, ".skfull-play", "el.click(); return true;")
    pg.wait_for_timeout(1500)
    card(pg, SILENT, ".skfull-play", "el.click(); return true;")
    pg.wait_for_timeout(300)
    before = card(pg, SILENT, ".skfull-track", "const s = box._skriblInline.state(); el.focus();"
                  " return { role: el.getAttribute('role'), tab: el.getAttribute('tabindex'), label: el.getAttribute('aria-label'),"
                  " focused: document.activeElement === el, at: s.elapsedMs, total: s.totalMs, state: s.state };")
    pg.keyboard.press("PageUp")
    pg.wait_for_timeout(300)
    after = card(pg, SILENT, ".skfull-track", "const s = box._skriblInline.state(); return { at: s.elapsedMs, now: el.getAttribute('aria-valuenow') };")
    moved = bool(before and after and before["total"]) and after["at"] - before["at"] >= 0.08 * before["total"]
    check("the card's scrubber is a slider Tab reaches, named Scrub, and a key moves the drawing",
          bool(before) and before["role"] == "slider" and before["tab"] == "0" and before["label"] == "Scrub"
          and before["focused"] and moved, f"{before} -> {after}")

    # Full screen and back: the card on top again.
    card(pg, SOUND, ".skfull-full", "el.click(); return true;")
    pg.wait_for_timeout(1500)
    playing = pg.evaluate("(F) => { const f = document.querySelector(F); const p = f && f.querySelector('.skribl-inline')._skriblInline;"
                          " return p ? p.state().state : null; }", FULL["gallery"])
    pg.evaluate("(F) => { const x = document.querySelector(F + ' > .player-btn.full-exit'); if (x) x.click(); }", FULL["gallery"])
    pg.wait_for_timeout(900)
    back = card(pg, SOUND, ".skfull-play", "const poster = box.querySelector('.skribl-inline-poster');"
                " return { state: box._skriblInline.state().state, playing: box.classList.contains('is-playing'),"
                " paused: box.classList.contains('is-paused'), poster: poster ? getComputedStyle(poster).opacity : null };")
    check("leaving the Gallery's full screen puts the card back on top, at rest",
          playing == "playing" and bool(back) and back["state"] == "idle" and not back["playing"] and not back["paused"]
          and back["poster"] == "1", f"in full screen {playing}; back {back}")
    check("the card: no page errors", not errs, "; ".join(errs[:2]))
    pg.close()

    # ------------------------------------------------------- full screen
    print("\nFULL SCREEN'S SPEEDS, while the drawing plays (a desk)")
    pg = gallery(b, DESK, "light")
    card(pg, SILENT, ".skfull-full", "el.click(); return true;")
    pg.wait_for_timeout(1200)
    F = FULL["gallery"]
    try:
        pg.click(F + " .replay-line .rl-speed", timeout=4000)
    except Exception as exc:
        print(f"  (no speed button: {str(exc)[:80]})")
    pg.wait_for_timeout(4500)
    st = pg.evaluate("""(F) => { const f = document.querySelector(F), band = f && f.querySelector(':scope > .player-bar');
        const sp = f && f.querySelector('.replay-line .rl-speed'), chips = f && f.querySelector('.replay-line .rl-chips');
        const p = f && f.querySelector('.skribl-inline')._skriblInline;
        return f && band && sp && { asleep: f.classList.contains('chrome-asleep'), band: getComputedStyle(band).opacity,
          open: sp.getAttribute('aria-expanded'), chips: !!chips && !chips.hidden && chips.getClientRects().length > 0,
          state: p ? p.state().state : null }; }""", F)
    check("the speeds stay open, and the band with them, while the drawing plays on",
          bool(st) and st["state"] == "playing" and st["open"] == "true" and st["chips"]
          and not st["asleep"] and st["band"] == "1", str(st))
    pg.close()

    # ------------------------------------------------------------ Library
    print("\nTHE LIBRARY'S STAGE (a desk)")
    pg = library(b, DESK, SILENT)
    # The stage starts playing on its own when a row is picked; each reading
    # is the player's state beside the button's name. (Its words for the
    # pointer are the tooltip's, which takes the title over.)
    PLAY = ("(S) => { const p = (new Function('return (' + S + ')()'))(); const b = document.getElementById('btnPlay');"
            " return { state: p ? p.state().state : null, label: b.getAttribute('aria-label') }; }")
    reads = [pg.evaluate(PLAY, STAGE)]
    for _ in range(2):
        pg.evaluate("() => document.getElementById('btnPlay').click()")
        pg.wait_for_timeout(600)
        reads.append(pg.evaluate(PLAY, STAGE))
    check("the Library's Play is named Pause while the drawing plays, and Play when it does not",
          all(r["label"] == ("Pause" if r["state"] == "playing" else "Play") for r in reads)
          and any(r["state"] == "playing" for r in reads) and any(r["state"] != "playing" for r in reads), str(reads))

    # Loop, off in full screen, is off on the page; one press turns it on.
    was = pg.evaluate("() => document.getElementById('btnLoop').getAttribute('aria-pressed')")
    pg.evaluate("() => document.getElementById('btnFull').click()")
    pg.wait_for_timeout(1200)
    L = FULL["library"]
    pg.evaluate("(F) => { const b = document.querySelector(F + ' .player-controls > :nth-child(3)'); if (b) b.click(); }", L)
    pg.wait_for_timeout(300)
    pg.evaluate("(F) => { const x = document.querySelector(F + ' > .player-btn.full-exit'); if (x) x.click(); }", L)
    pg.wait_for_timeout(900)
    page_loop = pg.evaluate("(S) => { const p = (new Function('return (' + S + ')()'))(); const b = document.getElementById('btnLoop');"
                            " return { pressed: b.getAttribute('aria-pressed'), lit: b.classList.contains('on'), looping: p ? p.looping() : null }; }", STAGE)
    pg.evaluate("() => document.getElementById('btnLoop').click()")
    pg.wait_for_timeout(300)
    again = pg.evaluate("(S) => { const p = (new Function('return (' + S + ')()'))(); const b = document.getElementById('btnLoop');"
                        " return { pressed: b.getAttribute('aria-pressed'), looping: p ? p.looping() : null }; }", STAGE)
    check("Loop turned off in full screen reads off on the page, and one press turns it back on",
          was == "true" and page_loop == {"pressed": "false", "lit": False, "looping": False}
          and again == {"pressed": "true", "looping": True}, f"before {was}; after full screen {page_loop}; one press {again}")
    # ...and the press reads the player itself, so it holds even before the
    # page's clock has caught up with a loop turned off elsewhere (the row
    # above passes on that clock alone; this one pins the press).
    # From Loop on, on the page and the player alike, so a page that flips
    # its own flag would turn it off again here.
    quick = pg.evaluate("(S) => { const p = (new Function('return (' + S + ')()'))(), b = document.getElementById('btnLoop');"
                        " if (!p.looping()) b.click(); const on = p.looping() && b.getAttribute('aria-pressed') === 'true';"
                        " p.setLoop(false); b.click(); return on && p.looping(); }", STAGE)
    check("...a press on Loop turns on what is off, read from the player, not from the page's last look",
          quick is True, str(quick))
    pg.close()

    pg = library(b, DESK, SOUND)
    pg.wait_for_function("() => !document.getElementById('btnMute').disabled", timeout=15000)
    mu = pg.evaluate("(S) => { const p = (new Function('return (' + S + ')()'))(); const b = document.getElementById('btnMute');"
                     " return { label: b.getAttribute('aria-label'), muted: p ? p.state().muted : null }; }", STAGE)
    check("the Library's Mute is named what a press does: Unmute while the sound is off",
          mu == {"label": "Unmute", "muted": True}, str(mu))
    pg.close()

    # A host with accounts: the listing's author, never the signed-in id.
    pg = themed(b, DESK, "light")

    def as_host(route):
        r = route.fetch()
        route.fulfill(response=r, body=r.text().replace('data-skribl-me=""', 'data-skribl-me="host-user-42"', 1))
    pg.route(re.compile(r"/library$"), as_host)
    listing = {"items": [{"id": SILENT["id"], "title": f"View silent {TAG}", "caption": None, "has_audio": False,
                          "views": 0, "user_id": "host-user-42", "visibility": "public", "kind": "pad", "pages": 1,
                          "canvas_w": 402, "canvas_h": 760, "created_at": "2026-10-19T10:00:00+00:00",
                          "author": {"id": "host-user-42", "display_name": "Ada Draws", "username": "ada"}}],
               "next_cursor": None}
    pg.route(re.compile(r"/api/skribls\?.*user_id="), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(listing)))
    browsing.goto(pg, BASE, "/library")
    pg.wait_for_function("() => { const b = document.getElementById('btnFull'); return b && !b.hidden && !b.disabled; }", timeout=15000)
    pg.wait_for_timeout(500)
    pg.evaluate("() => document.getElementById('btnFull').click()")
    pg.wait_for_timeout(1200)
    who = pg.evaluate("(F) => { const w = document.querySelector(F + ' > .fb-who'); return w ? w.innerText.replace(/\\s+/g, ' ').trim() : null; }",
                      FULL["library"])
    check("a host's Library names who drew it in full screen from the listing, never the signed-in id",
          bool(who) and "Ada Draws" in who and "@ada" in who and "host-user-42" not in who, str(who))
    pg.close()

    # ------------------------------------------------------- a Flip's end
    # At exactly its length a Flip's clock comes round to its first page, and
    # the player showed that page at its end: blank, for one whose first page
    # draws itself. The editor's own replay ends on the last page whole.
    print("\nA FLIP AT ITS END (the Library's stage, a desk)")
    pg = library(b, DESK, FLIP, kind="flip", pages=3)
    BOX = "() => document.querySelector('.stageCanvasWrap .skribl-inline')"
    READ = "(B) => (" + INK + ")((new Function('return (' + B + ')()'))())"
    STATE = ("(S) => { const s = (new Function('return (' + S + ')()'))().state();"
             " return [s.state, Math.round(s.elapsedMs), Math.round(s.totalMs)]; }")
    # A wait's test runs under the page's script policy, which refuses
    # new Function, so the stage is named outright there.
    ON_STAGE = "document.querySelector('.stageCanvasWrap .skribl-inline')._skriblInline"
    # As a person does it: the drawing starts on its own when its row is
    # picked; Loop off, then Restart, and watch it to its end.
    pg.wait_for_function(f"() => {{ const p = {ON_STAGE}; return p && p.state().state === 'playing'; }}", timeout=15000)
    pg.click("#btnLoop")
    pg.click("#btnRestart")
    try:
        pg.wait_for_function(f"() => {{ const s = {ON_STAGE}.state(); return s.state !== 'playing' && s.elapsedMs >= s.totalMs; }}",
                             timeout=15000)
    except PWTimeout:
        pass
    pg.wait_for_timeout(300)
    once, st = pg.evaluate(READ, BOX), pg.evaluate(STATE, STAGE)
    looping = pg.evaluate("(S) => (new Function('return (' + S + ')()'))().looping()", STAGE)
    check("a Flip played once stops on its last page, whole, never back on its first",
          looping is False and last_page(once), f"ink by corner {once}; player {st}, looping {looping}")
    # From its first page, partly drawn, a click at the very end of the
    # page's own scrubber: the end of the drawing.
    pg.click("#btnRestart")
    pg.wait_for_timeout(250)
    pg.click("#btnPlay")
    pg.wait_for_timeout(200)
    was = pg.evaluate(READ, BOX)
    pg.evaluate("""() => { const s = document.getElementById('scrub'), r = s.getBoundingClientRect();
        s.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.right, clientY: r.top + r.height / 2 })); }""")
    pg.wait_for_timeout(300)
    end, st = pg.evaluate(READ, BOX), pg.evaluate(STATE, STAGE)
    check("...and taken to its end, by a click at the far end of the scrubber, it shows its last page",
          bool(was) and was["first"] > 0 and was["last"] == 0 and last_page(end),
          f"before, on its first page: {was}; after: {end}; player {st}")
    pg.close()

    # At rest with no card: a draft in a host's composer is attached by its
    # payload, and its rest is the finished drawing (inlineplayer.js attach).
    pg = themed(b, DESK)
    browsing.goto(pg, BASE, "/feed")
    pg.wait_for_selector(".skribl-inline[data-skribl-id]", state="attached", timeout=20000)
    body = json.loads(urllib.request.urlopen(BASE + f"/api/skribls/{FLIP['id']}", timeout=30).read())
    pg.evaluate("""(payload) => { const src = document.querySelector('.skribl-inline[data-skribl-id]');
        const tmp = document.createElement('div'); tmp.innerHTML = src.outerHTML;
        const box = tmp.firstElementChild; box.classList.remove('is-playing', 'is-paused', 'is-loading');
        box.setAttribute('data-skribl-w', 402); box.setAttribute('data-skribl-h', 760); box.id = 'flipRest';
        box.style.width = '402px';
        const host = document.createElement('article'); host.appendChild(box); document.body.prepend(host);
        SkriblInline.attach(box, payload); }""", body.get("skribl") or body)
    pg.wait_for_function("() => { const p = document.getElementById('flipRest')._skriblInline; return p && p.state().loaded; }",
                         timeout=10000)
    pg.wait_for_timeout(400)
    rest = pg.evaluate("""(INK) => { const box = document.getElementById('flipRest');
        return { state: box._skriblInline.state().state, ink: (new Function('return (' + INK + ')'))()(box) }; }""", INK)
    check("a Flip at rest with no card (a draft in a host's composer) shows its last page whole, not its first page blank",
          bool(rest) and rest["state"] == "idle" and last_page(rest["ink"]), str(rest))
    pg.close()

    # --------------------------------------------------------- in a post
    print("\nTHE BOX A POST PLAYS IN (the feed)")
    pg = themed(b, PHONE)
    browsing.goto(pg, BASE, "/feed")
    sel = f".skribl-inline[data-skribl-id='{SILENT['id']}']"
    pg.wait_for_selector(sel, state="attached", timeout=20000)
    rest = pg.evaluate("(s) => document.querySelector(s).getAttribute('aria-label')", sel)
    pg.evaluate("(s) => document.querySelector(s).click()", sel)
    pg.wait_for_timeout(900)
    playing = pg.evaluate("(s) => { const b = document.querySelector(s); return { label: b.getAttribute('aria-label'), state: b._skriblInline.state().state }; }", sel)
    pg.evaluate("(s) => document.querySelector(s).click()", sel)
    pg.wait_for_timeout(400)
    paused = pg.evaluate("(s) => { const b = document.querySelector(s); return { label: b.getAttribute('aria-label'), state: b._skriblInline.state().state }; }", sel)
    check("a post's box is named Pause this Skribl while it plays, and Play this Skribl again when it stops",
          bool(rest) and rest.startswith("Play this Skribl") and playing["state"] == "playing"
          and playing["label"] == "Pause" + rest[len("Play"):] and paused["state"] == "paused" and paused["label"] == rest,
          f"at rest {rest!r}; playing {playing}; paused {paused}")
    pg.close()

    # ------------------------------------------------------------ words
    print("\nTHE GALLERY'S WORDS")
    pg = gallery(b, DESK, "light")
    sub = pg.evaluate("() => document.getElementById('gallerySub').textContent")
    try:
        pg.click("[data-sort='hot']", timeout=4000)
        pg.wait_for_timeout(400)
    except Exception:
        pass
    hot = pg.evaluate("() => document.getElementById('gallerySub').textContent")
    check("the Gallery invites a tap to watch a Skribl come alive, a Pad's or a Flip's, on both tabs",
          sub.endswith("Tap one to watch it come alive.") and hot.endswith("Tap one to watch it come alive.") and sub != hot,
          f"new {sub!r}; hot {hot!r}")
    pg.route(re.compile(r"/api/skribls(\?|$)"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"items": [], "next_cursor": None})))
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(1200)
    empty = pg.evaluate("() => { const e = document.getElementById('galleryEmpty'); return e && !e.hidden ? e.innerText.replace(/\\s+/g, ' ').trim() : null; }")
    check("an empty Gallery says a Skribl can be shown later, from its author's Library",
          bool(empty) and "Show in the public gallery" in empty and "turns it on later in their Library" in empty, str(empty))
    pg.close()
    b.close()

# ------------------------------------------------------------ the colours
# What the page loads is the mechanism: its own <style> and inline script,
# and every stylesheet and script it names, as the server sends them. A name
# styles.css gives a colour is not the page's own: each page maps the
# editors' vocabulary onto its palette for the sheets it shares with them
# ("posted.css's vocabulary", skribl_library.html), whether or not one of
# them reads every word today. The page's own names are what this counts.
print("\nTHE COLOURS EACH PAGE DECLARES")
_shared = set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", re.sub(r"/\*.*?\*/", "", urllib.request.urlopen(
    BASE + "/static/skribl/styles.css", timeout=20).read().decode("utf-8", "replace"), flags=re.S)))
for path in ("/gallery", "/library"):
    html = urllib.request.urlopen(BASE + path, timeout=20).read().decode()
    own = re.sub(r"/\*.*?\*/", "", "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S)), flags=re.S)
    declared = sorted(set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", own)) - _shared)
    loaded = [html]
    for u in sorted(set(re.findall(r'(?:src|href)="([^"]*/static/skribl/[^"]+\.(?:css|js)[^"]*)"', html))):
        loaded.append(urllib.request.urlopen(BASE + u if u.startswith("/") else u, timeout=20).read().decode("utf-8", "replace"))
    blob = "\n".join(loaded)
    unread = [d for d in declared if not re.search(r"var\(\s*" + re.escape(d) + r"\b", blob)
              and f"'{d}'" not in blob and f'"{d}"' not in blob]
    check(f"{path}: every colour of the page's own is read by the page or by what it loads",
          len(declared) >= 5 and not unread, f"{len(declared)} of its own; unread: {unread}")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
