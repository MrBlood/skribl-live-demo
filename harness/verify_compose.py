"""Compose mode: the Pad opened from a host's composer, and the rule it obeys.

skribls.net's composer has a row of attachment buttons and one of them is a
Skribl. Pressing it opens the editor over the feed; you draw; "Add to post"
puts the drawing in the draft; pressing the button again reopens the editor
with it; the host's Post publishes the lot. That flow is driven end to end
here, on the real /feed page, through the real iframe, with a real recording.

THE RULE THIS SUITE EXISTS TO PIN: COMPOSE MODE PUBLISHES NOTHING.

An attachment is not a post. The alternative — publish on "Add to post", and
republish on every edit — is not merely untidy, it is broken twice over, and
both failures are silent:

  * POST /api/skribls is CREATE-ONLY (routes.py registers one POST and two
    GETs). Every edit would orphan the previous skribl and spend another slot
    of the author's posting quota on a drawing nobody will see.
  * An abandoned draft would leave a published, shareable skribl behind that
    the host has no way to withdraw.

So the assertions below count POSTs. Not "does it work" — how many times it
talked to the server, and when.

The second thing asserted is that what compose hands back is what Pad would
have posted: same serialisation, same share-card thumbnail, same mono audio
bake. editor_post.js has one buildPostPayload() and both endings call it, and
this suite checks the RESULT rather than the arrangement — a composed skribl
and a Pad-posted one, from the same drawing, must agree.
"""
import json
import math
import os
import pathlib
import re
import sys
import urllib.request
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence compose mode works.")
    raise SystemExit(77)

results = []


check = make_check(results)


def draw(pg, box, turns=4, n=70):
    """A real recording, over real wall clock — see verify_inline.py's note."""
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        t = i / n
        pg.mouse.move(cx + math.cos(t * math.pi * turns) * (25 + t * 140),
                      cy + math.sin(t * math.pi * turns) * (25 + t * 110))
        if i % 5 == 0:
            pg.wait_for_timeout(90)
    pg.mouse.up()


INK = """(sel) => {
  const c = document.querySelector(sel);
  if (!c || !c.width) return -1;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const r = d[0], g = d[1], b = d[2], a = d[3];
  let n = 0;
  for (let i = 0; i < d.length; i += 4)
    if (Math.abs(d[i]-r) + Math.abs(d[i+1]-g) + Math.abs(d[i+2]-b)
        + Math.abs(d[i+3]-a) > 24) n++;
  return n;
}"""

EDITOR_INK = """() => {
  const c = document.getElementById('padFrame').contentDocument
              .getElementById('canvas');
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let n = 0;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++;
  return n;
}"""


with sync_playwright() as sp:
    b = sp.chromium.launch()
    # THE DARK THEME, EXPLICITLY (v292): the literals below are the dark ramp's amber. Since
    # v292 a bare page follows the OS and headless Chromium says light, on which amber is
    # rgb(138, 91, 0). The pin is the semantics (amber, not green, not red); measured on the
    # ramp it was written for.
    pg = b.new_page(viewport={"width": 1240, "height": 980}, color_scheme="dark")

    errs = []
    posts = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # EVERY WRITE TO THE API, counted. This list is the suite's main instrument.
    pg.on("request", lambda r: posts.append(r.url)
          if r.method == "POST" and "/api/skribls" in r.url else None)

    browsing.goto(pg, BASE, "/feed")

    # ---- the button is there, and it is the only real one ------------------
    check("the host composer offers a Skribl alongside its own attachments",
          pg.locator("#padBtn").count() == 1)
    check("nothing is attached and nothing can be posted yet",
          pg.evaluate("() => document.getElementById('postBtn').disabled") is True)

    # ---- open the editor ---------------------------------------------------
    # Captured BEFORE the click, because the assertion below is about what the
    # page had NOT done yet.
    src_before = pg.evaluate(
        "() => document.getElementById('padFrame').getAttribute('src')")
    pg.click("#padBtn")
    pg.wait_for_timeout(4000)
    mode = pg.evaluate("() => document.getElementById('padFrame').contentWindow.SKRIBL_MODE")
    check("the pad icon opens the editor in compose mode",
          mode == "compose", f"SKRIBL_MODE={mode!r}")
    check("the overlay is open over the feed",
          pg.evaluate("() => !document.getElementById('padOverlay').hidden"))

    fr = pg.frame_locator("#padFrame")
    label = fr.locator("#postSubmitLabel").inner_text()
    check("the editor's button says it is attaching, not publishing",
          label.strip() == "Add to post", f"reads {label.strip()!r}")

    # THE EDITOR IS NOT LOADED UNTIL IT IS ASKED FOR (lib/composehost.js rule 1).
    # A composer that put the pad's ~500 KB in an iframe on every feed view
    # would charge every visitor for a drawing tool they never opened.
    #
    # This assertion used to be check(..., True, "src is set on open"), which
    # asserts the literal True and cannot fail — it would have stayed green
    # through any regression it names. It reads the attribute now.
    check("the editor was not loaded until the pad icon was pressed",
          not src_before or src_before in ("", "about:blank"),
          f"src before the click was {src_before!r}")
    src_after = pg.evaluate(
        "() => document.getElementById('padFrame').getAttribute('src')")
    check("...and pressing it is what set the src",
          bool(src_after) and src_after not in ("", "about:blank"),
          f"src after the click was {src_after!r}")

    # ---- draw and attach ---------------------------------------------------
    draw(pg, fr.locator("#canvas").bounding_box())
    pg.wait_for_timeout(400)
    fr.locator("#recordBtn").click()
    pg.wait_for_timeout(400)
    fr.locator("#postBtn").click()
    pg.wait_for_timeout(1000)
    fr.locator("#postSubmitBtn").click()
    pg.wait_for_timeout(4000)

    check("attaching closes the overlay",
          pg.evaluate("() => document.getElementById('padOverlay').hidden") is True)
    check("the drawing is attached to the draft",
          pg.evaluate("() => !document.getElementById('composerAttach').hidden") is True)

    # THE ASSERTION THIS SUITE IS FOR.
    check("attaching a drawing PUBLISHES NOTHING",
          not posts,
          f"{len(posts)} POST(s) to /api/skribls before the host posted: {posts}")

    ink = pg.evaluate(INK, "#composerSkribl .skribl-inline-canvas")
    check("the draft shows the real in-post player with the real drawing in it",
          ink > 500,
          f"{ink} pixels of ink — a composer that previews a thumbnail is "
          f"previewing something other than what it will publish")
    st = pg.evaluate("""() => {
        const el = document.getElementById('composerSkribl');
        const p = window.SkriblInline.players().filter(x => x.el === el)[0];
        return p ? p.state() : null; }""")
    check("the draft's player has no id, because there is nothing to have one",
          st and st["id"] is None and st["loaded"] is True, json.dumps(st))
    check("the draft is at rest, not showing a finished progress bar",
          pg.evaluate("""() => parseFloat(document.querySelector(
             '#composerSkribl .skribl-inline-prog').style.width) || 0""") == 0)

    # ---- re-edit -----------------------------------------------------------
    # COUNT THE LOAD MESSAGE, not just the ink. The ink assertion below passes
    # even with lib/composehost.js's re-edit push disabled, because the editor
    # iframe is still loaded and still holding the drawing from the previous
    # open — so it measures the editor's retained state, not the handshake.
    # Rule 2 is the guarantee that the editor shows the DRAFT's payload rather
    # than whatever it happens to have kept, which is what makes it correct
    # when the host sets a payload the editor has never seen (setPayload).
    # Mutation-tested: disabling the push takes this to 0 and leaves the ink
    # assertion green.
    pg.evaluate("""() => {
        var w = document.getElementById('padFrame').contentWindow;
        w.__skriblLoads = 0;
        w.addEventListener('message', function (e) {
          if (e.data && e.data.type === 'skribl:compose:load') w.__skriblLoads++;
        });
    }""")
    pg.click("#editSkriblBtn")
    pg.wait_for_timeout(3500)
    loads = pg.evaluate(
        "() => document.getElementById('padFrame').contentWindow.__skriblLoads")
    check("re-opening pushes the draft's payload into the loaded editor",
          loads == 1,
          f"{loads} skribl:compose:load message(s) — without this the editor "
          f"shows whatever it kept, not what the draft holds")
    restored = pg.evaluate(EDITOR_INK)
    check("re-opening the editor brings the drawing back",
          restored > 500,
          f"{restored} inked pixels in the editor — without this, 'change it' "
          f"means 'draw it again'")

    draw(pg, fr.locator("#canvas").bounding_box(), turns=2)
    pg.wait_for_timeout(400)
    fr.locator("#postBtn").click()
    pg.wait_for_timeout(1000)
    fr.locator("#postSubmitBtn").click()
    pg.wait_for_timeout(4000)
    check("editing an attached drawing still publishes nothing",
          not posts,
          f"{len(posts)} POST(s) after an edit — this is the orphan-per-edit "
          f"failure the design exists to avoid")

    # ---- post --------------------------------------------------------------
    pg.fill("#composerText", "drew this in the composer")
    pg.click("#postBtn")
    pg.wait_for_timeout(6000)
    check("the host's Post makes exactly one skribl",
          len(posts) == 1, f"{len(posts)} POST(s): {posts}")
    status = pg.inner_text("#composerStatus")
    check("the composer reports the post landed", "Posted" in status, status)
    check("the new post is in the feed, playing through the in-post player",
          pg.evaluate("() => document.getElementById('feedList').children.length") >= 1)
    check("the composer is empty again and cannot post a second time by accident",
          pg.evaluate("""() => document.getElementById('composerAttach').hidden
                            && document.getElementById('postBtn').disabled""") is True)
    # lib/composehost.js rule 3: clearing drops the EDITOR too, not just the
    # payload. Without it the next pad press reopens the drawing that was just
    # posted, and the author's next Skribl starts as a copy of their last one.
    check("clearing reset the editor frame, so the next pad press starts blank",
          pg.evaluate("() => document.getElementById('padFrame').getAttribute('src')")
          == "about:blank",
          pg.evaluate("() => document.getElementById('padFrame').getAttribute('src')"))
    check("no page errors through the whole flow", not errs, "; ".join(errs[:2]))

    posted_id = pg.evaluate("""() => {
        const el = document.querySelector('#feedList [data-skribl-id]');
        return el ? el.getAttribute('data-skribl-id') : null; }""")
    check("the posted skribl has an id the host can store on its own row",
          bool(posted_id), str(posted_id))
    pg.close()

    # ---- WHAT WAS PUBLISHED IS WHAT PAD WOULD HAVE PUBLISHED ---------------
    # buildPostPayload() is shared by both endings, so the composed skribl must
    # carry the post-time work: the share-card thumbnail that becomes the idle
    # poster, and a visibility the host chose rather than the API default.
    with urllib.request.urlopen(BASE + "/api/skribls/" + posted_id, timeout=20) as r:
        env = json.loads(r.read().decode())
    sk = env.get("skribl") or {}
    check("the composed skribl carries a real drawing",
          bool((sk.get("frames") or [{}])[0].get("strokes")),
          "frames[0].strokes is where a Pad recording lives")
    # The GET envelope drops the thumbnail deliberately (routes.py), so the
    # card route is where to see whether one was stored: a real card is served
    # inline, a missing one redirects to the static branded image.
    req = urllib.request.Request(BASE + "/s/" + posted_id + "/card.png")
    with urllib.request.urlopen(req, timeout=20) as r:
        card_url = r.geturl()
    check("the composed skribl has its own share card, so the feed poster is "
          "its drawing and not the generic one",
          "og-card" not in card_url,
          f"card resolved to {card_url}; the generic og-card here would mean "
          f"buildPostPayload()'s thumbnail step did not run on this path")
    # The HOST decided this, not Skribl. POST /api/skribls defaults to
    # "unlisted" — a link-sharing product's correct default — and a feed's
    # composer is exactly the caller that means otherwise. It rides in the body
    # the composer sent, which is why it comes back in the stored payload.
    check("the host's composer chose the visibility rather than taking the "
          "API's link-sharing default",
          sk.get("visibility") == "public",
          f"payload carried visibility={sk.get('visibility')!r}")
    with urllib.request.urlopen(BASE + "/api/skribls?limit=50", timeout=20) as r:
        listed = json.loads(r.read().decode())
    check("the composed skribl appears in GET /api/skribls",
          any(i["id"] == posted_id for i in listed.get("items", [])),
          "the composer sent visibility=public; the API's own default is "
          "unlisted, which would keep it out of every feed")

    # ---- the carve ---------------------------------------------------------
    # editor_compose.js is an editor_*.js file, so verify_player_isolation.py's
    # glob enrols it automatically and fails if the player ever loads it. What
    # that glob cannot say is that the ordinary Pad does not load it either: it
    # is compose-only, and a Pad that loaded it would answer postMessages from
    # whatever framed it.
    plain = urllib.request.urlopen(BASE + "/skribl-pad", timeout=20).read().decode()
    composed = urllib.request.urlopen(BASE + "/skribl-pad?compose=1", timeout=20).read().decode()
    check("the ordinary Pad does not load editor_compose.js",
          "editor_compose.js" not in plain)
    check("the compose Pad does", "editor_compose.js" in composed)
    check("the ordinary Pad still says it is publishing",
          "Post to Skribl" in plain and "Add to post" not in plain)

    # The handshake targets an origin, never '*'. A wildcard would post the
    # author's drawing to whatever page happened to be framing the editor.
    src = (ROOT / "skribl" / "static" / "editor_compose.js").read_text(encoding="utf-8")
    check("the compose handshake never posts a drawing to a wildcard origin",
          "'*'" not in src and '"*"' not in src,
          "postMessage(msg, '*') would hand the drawing to any framing page")
    check("and it ignores messages from any other origin",
          "e.origin !== HOST_ORIGIN" in src)

    # ---- the post sheet's sound marker -------------------------------------
    # The toolbar's music mark, repeated on the sheet at the moment of posting.
    # It exists for the AMBER case: a loop is remembered, its file is gone, and
    # without this the author posts silence believing otherwise.
    #
    # "The same glyph as the toolbar" is asserted as RENDERED, not as source. A
    # copy of the path data would satisfy any grep written against the template
    # and drift the first time one of the two is redrawn — which is exactly how
    # the in-post player's markup ended up written three times.
    # The macro has its own file since the tab strip became a partial both
    # editors include (the dock redesign): the sheet's caller is in the editor
    # template, the Music tab's in _skribl_media_tabs.html.
    _T = ROOT / "skribl" / "templates" / "skribl"
    _glyph = (_T / "_skribl_music_glyph.html").read_text(encoding="utf-8")
    tmpl = (_T / "skribl_editor.html").read_text(encoding="utf-8")
    _tabs = (_T / "_skribl_media_tabs.html").read_text(encoding="utf-8")
    _copies = sum(t.count('d="M9 18V5l12-2v13"') for t in (_glyph, tmpl, _tabs))
    check("the music glyph's path data is written ONCE, in its macro",
          _copies == 1 and _glyph.count('d="M9 18V5l12-2v13"') == 1,
          f"{_copies} copies — a second one is a redraw waiting to disagree "
          f"with the first")
    _calls = tmpl.count("{{ music_glyph() }}") + _tabs.count("{{ music_glyph() }}")
    check("...and both callers reach it through the macro",
          _calls == 2 and tmpl.count("{{ music_glyph() }}") == 1,
          f"{_calls} call(s)")
    # The music drawer draws the note three times (the empty drop area, the
    # loaded row's tile, the re-add card) and held two raw copies of its path
    # before the drawer redesign. Every one goes through the macro now.
    _drawer = (_T / "_skribl_music_drawer.html").read_text(encoding="utf-8")
    _raw, _via = _drawer.count('d="M9 18V5l12-2v13"'), _drawer.count("{{ music_glyph() }}")
    check("the music drawer reaches the glyph through the macro, never a copy",
          _raw == 0 and _via >= 3 and "import music_glyph" in _drawer,
          f"{_raw} raw copies, {_via} macro calls")

    pad = b.new_page(viewport={"width": 1180, "height": 900}, color_scheme="dark")
    perrs = []
    pad.on("pageerror", lambda e: perrs.append(str(e)))
    browsing.goto(pad, BASE, "/")
    draw(pad, pad.locator("#canvas").bounding_box(), turns=2)
    pad.wait_for_timeout(300)
    pad.locator("#recordBtn").click()
    pad.wait_for_timeout(600)

    # SILENT: nothing renders at all, so the sheet is exactly as it was.
    pad.locator("#postBtn").click()
    pad.wait_for_timeout(900)
    check("a Skribl with no music shows no sound marker",
          pad.evaluate("() => document.getElementById('postSound').hidden") is True)

    # THE GLYPHS ARE THE SAME, as rendered. Compares the DOM the browser
    # actually built from both macro calls.
    same = pad.evaluate(
        "() => { var a = document.querySelector('#mediaTabMusic svg');"
        "        var b = document.querySelector('#postSound svg');"
        "        return (a && b) ? (a.outerHTML === b.outerHTML) : null; }")
    check("the sheet's glyph is byte-identical to the Media drawer's Music tab, as rendered",
          same is True, f"outerHTML comparison returned {same!r}")

    # GREEN: a loop is loaded. Driven by the toolbar's own dot, which is the
    # app's existing statement about the track — a second opinion computed here
    # could disagree with it, and then one mark would say two things.
    pad.evaluate("() => { var d = document.getElementById('musicTabDot');"
                 "        d.hidden = false; d.classList.remove('pending'); }")
    pad.keyboard.press("Escape")
    pad.wait_for_timeout(500)
    pad.locator("#postBtn").click()
    pad.wait_for_timeout(900)
    st = pad.evaluate(
        "() => { var m = document.getElementById('postSound');"
        "        var d = document.getElementById('postSoundDot');"
        "        return { hidden: m.hidden, pending: d.classList.contains('pending'),"
        "                 bg: getComputedStyle(d).backgroundColor,"
        # WHEREVER THE WORDS ARE, `title` FIRST. editor_post.js writes this
        # marker's words to `title` after load, and on a fine pointer
        # lib/tooltip.js moves every title to `data-tip` and removes it --
        # including the ones written after load, since v310. For the tick
        # that wrote it the new words are still in `title`, so freshest
        # first and the empty string a removed title leaves falls through.
        "                 title: (m.getAttribute('title')"
        "                         || m.getAttribute('data-tip')),"
        "                 sr: document.getElementById('postSoundText').textContent,"
        "                 tag: m.tagName }; }")
    check("a loaded loop shows the marker", st["hidden"] is False, json.dumps(st))
    # Read from the token rather than typed, so lifting --good does not have to
    # be chased through the suites. The point of the assertion is that the sheet
    # marker and the toolbar dot are THE SAME green, not which green it is.
    # `pad`, not `pg`: this section drives its own page and pg was closed long
    # before. Using the wrong one crashed the suite outright, which is at least
    # the loud kind of wrong.
    _good = pad.evaluate(
        "() => getComputedStyle(document.documentElement)"
        ".getPropertyValue('--good').trim()")
    _toolbar = pad.evaluate(
        "() => getComputedStyle(document.getElementById('musicTabDot'))"
        ".backgroundColor")
    check("...in --good green, the same colour the toolbar dot uses",
          st["bg"] == _toolbar and bool(_good),
          f"sheet {st['bg']} vs toolbar {_toolbar} (--good: {_good})")
    check("...and it says so in text, not only in colour",
          "has sound" in (st["sr"] or "") and st["sr"] == st["title"],
          json.dumps({"sr": st["sr"], "title": st["title"]}))
    # On the toolbar this mark is a button that opens the music drawer. Here
    # there is nothing to open, so it must not invite a tap.
    check("the marker is not a button — nothing to tap and be disappointed by",
          st["tag"] == "SPAN", st["tag"])
    check("and it has no pointer cursor",
          pad.evaluate("() => getComputedStyle("
                       "document.getElementById('postSound')).cursor") != "pointer")

    # AMBER: remembered, file gone. THE STATE THAT EARNS THE FEATURE.
    pad.evaluate("() => document.getElementById('musicTabDot')"
                 ".classList.add('pending')")
    pad.keyboard.press("Escape")
    pad.wait_for_timeout(500)
    pad.locator("#postBtn").click()
    pad.wait_for_timeout(900)
    st2 = pad.evaluate(
        "() => { var d = document.getElementById('postSoundDot');"
        "        return { pending: d.classList.contains('pending'),"
        "                 bg: getComputedStyle(d).backgroundColor,"
        "                 sr: document.getElementById('postSoundText').textContent }; }")
    check("a remembered loop whose file is gone goes amber, not green",
          st2["pending"] is True and st2["bg"] == "rgb(255, 210, 63)",
          json.dumps(st2))
    check("...and says the post will have no sound, which is the whole point",
          "missing" in (st2["sr"] or "") and "without sound" in (st2["sr"] or ""),
          st2["sr"])
    check("no page errors from the marker", not perrs, "; ".join(perrs[:2]))
    pad.close()

    # ADD IS NEVER GREYED OUT IN COMPOSE MODE (owner, mock A2). It was dimmed
    # until there was a take, looked broken to someone who had come to add a
    # drawing, and could not say why. Both editors: before anything is drawn
    # the button is painted at full strength, a REAL click at its centre lands
    # on it, says what is missing in the editor's status region and opens
    # nothing; once there is something to add, the same click opens the sheet.
    print("\nCOMPOSE — Add is always ready, and says why when it cannot add")
    _A2 = (("Pad", "/skribl-pad?compose=1", "#canvas", "#toast",
            "() => { const o = document.getElementById('postOverlay'); return !!o && !o.hidden; }"),
           ("Flip", "/flip?compose=1", "#pad", "#flipChip",
            "() => { const m = document.getElementById('flipShare'); return !!m && !m.hidden; }"))
    for _name, _path, _cv, _say, _opened in _A2:
        _ac = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        _ap = _ac.new_page()
        _aerr = []
        _ap.on("pageerror", lambda e: _aerr.append(str(e)))
        browsing.goto(_ap, BASE, _path)
        _ap.wait_for_timeout(600)
        _ap.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _st = _ap.evaluate("""() => { const p = document.getElementById('postBtn'), r = p.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { attr: p.hasAttribute('disabled'), aria: p.getAttribute('aria-disabled'),
                     op: getComputedStyle(p).opacity, onIt: !!(hit && p.contains(hit)) }; }""")
        check(f"{_name}: before anything is drawn, Add is painted ready and takes the tap",
              not _st["attr"] and _st["aria"] is None and _st["op"] == "1" and _st["onIt"], json.dumps(_st))
        _bb = _ap.locator("#postBtn").bounding_box()
        _ap.mouse.click(_bb["x"] + _bb["width"] / 2, _bb["y"] + _bb["height"] / 2)
        _ap.wait_for_timeout(400)
        _msg = _ap.evaluate(f"() => document.querySelector('{_say}').textContent")
        check(f"{_name}: ...and a press says what is missing, in the status region",
              "Draw something first, then Add" in (_msg or "")
              and _ap.evaluate(f"() => document.querySelector('{_say}').getAttribute('role')") == "status",
              repr(_msg))
        check(f"{_name}: ...and opens nothing", _ap.evaluate(_opened) is False)
        draw(_ap, _ap.locator(_cv).bounding_box(), turns=2, n=40)
        _ap.evaluate("() => { if (typeof recording !== 'undefined' && recording) document.getElementById('recordBtn').click(); }")
        _ap.wait_for_timeout(700)
        _ap.mouse.click(_bb["x"] + _bb["width"] / 2, _bb["y"] + _bb["height"] / 2)
        _ap.wait_for_timeout(900)
        check(f"{_name}: once there is a drawing, the same press opens Add to post",
              _ap.evaluate(_opened) is True)
        check(f"{_name}: no page errors", not _aerr, "; ".join(_aerr[:2]))
        _ac.close()

    # ---- the drawing goes after the words ------------------------------------
    # v315 put it where the cursor was, through a [skribl] marker typed into
    # the text; the owner chose mock M2 over it, so the composer types nothing
    # and the drawing follows the words like a photo. The caret is still put
    # mid-text below, so a marker written "at the cursor" would be caught.
    # Driven through the real iframe, because the composer's half of this runs
    # in onDone, which only the editor's "Add to post" reaches.
    print("\nCOMPOSE — the drawing goes after the words")
    ictx = b.new_context(viewport={"width": 1240, "height": 980}, color_scheme="dark")
    pi = ictx.new_page()
    ierrs = []
    pi.on("pageerror", lambda e: ierrs.append(str(e)))
    # The author has a Pad draft of their own in this browser before they ever
    # compose a post: a real one, drawn on the ordinary Pad and autosaved.
    _SLOT = "() => localStorage.getItem('skribl_autosave_v1')"
    own = ictx.new_page()
    browsing.goto(own, BASE, "/skribl-pad")
    own.wait_for_timeout(1500)
    draw(own, own.locator("#canvas").bounding_box(), turns=3, n=40)
    own.wait_for_function("() => !!localStorage.getItem('skribl_autosave_v1')", timeout=10000)
    own.close()   # its pagehide flush rewrites the slot, so read it after
    browsing.goto(pi, BASE, "/feed")
    OWN_DRAFT = pi.evaluate(_SLOT)
    TOP, BOTTOM = "Made this on the bus.", "Loop it to see where I stopped."
    _caret = """([top, bottom]) => { const t = document.getElementById('composerText');
        t.value = top + '\\n' + bottom; t.focus();
        t.selectionStart = t.selectionEnd = top.length + 1; }"""

    # COMPOSE KEEPS NO PAD DRAFT (v315). It used to share the Pad's autosave
    # slot, which is how this section first went red: the removed drawing was
    # restored on the next open as a finished take, and nothing could be drawn.
    # Asserted AS THE PAD OPENS, because a restored take then blocks drawing and
    # the rest of the flow crashes before a later check could name the cause.
    def attach_one(blank_claim):
        pi.click("#padBtn")
        pi.wait_for_timeout(4000)
        _ink = pi.evaluate(EDITOR_INK)
        check(blank_claim, _ink == 0, f"{_ink} inked pixels as the Pad opened")
        fi = pi.frame_locator("#padFrame")
        draw(pi, fi.locator("#canvas").bounding_box(), turns=2, n=40)
        pi.wait_for_timeout(300)
        fi.locator("#recordBtn").click()
        pi.wait_for_timeout(300)
        fi.locator("#postBtn").click()
        pi.wait_for_timeout(900)
        fi.locator("#postSubmitBtn").click()
        pi.wait_for_timeout(3000)

    pi.evaluate(_caret, [TOP, BOTTOM])
    attach_one("the composer's Pad opens blank, not on the author's own Pad draft")
    _txt = pi.evaluate("() => document.getElementById('composerText').value")
    # THE DRAWING GOES AFTER THE WORDS, like a photo (owner, mock M2). The
    # composer used to type a [skribl] marker at the caret; it was the most
    # confusing thing on the page and one backspace from gone. Attaching now
    # leaves the text exactly as typed.
    check("attaching leaves the author's words exactly as typed (no marker)",
          _txt == TOP + "\n" + BOTTOM, repr(_txt))
    pi.click("#removeSkriblBtn")
    pi.wait_for_timeout(300)
    _txt = pi.evaluate("() => document.getElementById('composerText').value")
    check("...and removing the drawing leaves them alone too",
          _txt == TOP + "\n" + BOTTOM, repr(_txt))
    pi.evaluate(_caret, [TOP, BOTTOM])
    attach_one("...and a drawing removed from the post does not come back on the next open")
    check("attaching to a post leaves the author's own Pad draft exactly as it was",
          bool(OWN_DRAFT) and pi.evaluate(_SLOT) == OWN_DRAFT,
          "the slot changed" if pi.evaluate(_SLOT) != OWN_DRAFT else "unchanged")
    # YOUR OWN DRAWING, NOT A POSTER (owner, mock P1). The draft tile showed
    # the feed's dim wash and big Play, which hid which drawing was attached.
    # Idle on the finished drawing is the draft player's own rule
    # (verify_inline); what the host page adds is that nothing covers it.
    _tile = pi.evaluate("""() => {
        const el = document.getElementById('composerSkribl');
        const play = el.querySelector('.skribl-inline-play');
        const veil = el.querySelector('.skribl-inline-veil');
        const dur = el.querySelector('.skribl-inline-dur');
        return { playShown: !!(play && play.offsetParent),
                 wash: veil ? getComputedStyle(veil).backgroundImage : 'none',
                 dur: dur && !dur.hidden ? dur.textContent.trim() : null,
                 mark: dur ? getComputedStyle(dur, '::before').borderLeftWidth : null }; }""")
    check("the attached drawing shows plain: no big Play over it, no wash",
          not _tile["playShown"] and _tile["wash"] == "none", json.dumps(_tile))
    check("...and its length chip carries the play mark and the length",
          bool(_tile["dur"]) and ":" in _tile["dur"] and _tile["mark"] not in (None, "0px"),
          json.dumps(_tile))
    pi.click("#postBtn")
    pi.wait_for_timeout(5000)
    _order = pi.evaluate("""() => {
        const post = document.querySelector('#feedList .post');
        if (!post) return null;
        return [...post.children].map(e => e.matches('[data-skribl-inline], .skribl-inline') ? 'PLAYER'
               : e.classList.contains('pbody') ? 'TEXT:' + e.textContent
               : e.classList.contains('skribl-inline-title') ? 'TITLE' : e.className); }""")
    _texts = [x for x in (_order or []) if isinstance(x, str) and x.startswith("TEXT:")]
    check("the posted feed shows the words, then the drawing",
          bool(_order) and "PLAYER" in _order and len(_texts) == 1
          and _texts[0] == "TEXT:" + TOP + "\n" + BOTTOM
          and _order.index(_texts[0]) < _order.index("PLAYER"),
          str(_order))
    check("...and no title line, because the title the composer derived IS those words",
          bool(_order) and "TITLE" not in _order, str(_order))
    check("...and no marker is ever shown",
          all("[skribl]" not in x for x in _texts), str(_texts))
    check("no page errors placing the drawing", not ierrs, "; ".join(ierrs[:2]))
    ictx.close()

    # THE HEADER IN COMPOSE MODE (owner, v316: option B of the mock). A host's
    # floating close sat on the Pad's ⋯ on a phone, and the header called the
    # attach "Post". Compose mode now leads with the editor's own × beside the
    # skribl wordmark, and the button says Add. The × is driven with a REAL
    # click at its centre in the overlay, which is also the painted check: a
    # covered × would not close anything.
    print("\nCOMPOSE — the header: × beside the wordmark, Add, nothing on the ⋯")
    for _vp in ({"width": 360, "height": 740}, {"width": 1280, "height": 900}):
        _hc = b.new_context(viewport=_vp, is_mobile=_vp["width"] < 700, has_touch=_vp["width"] < 700)
        _hp = _hc.new_page()
        browsing.goto(_hp, BASE, "/feed")
        check(f"@{_vp['width']}: the feed floats no close of its own over the editor",
              _hp.locator("#padCloseBtn").count() == 0)
        _hp.click("#padBtn")
        _hp.wait_for_timeout(3500)
        _hf = [x for x in _hp.frames if "compose=1" in x.url][0]
        _hf.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _hfr = _hp.frame_locator("#padFrame")
        draw(_hp, _hfr.locator("#canvas").bounding_box(), n=40)
        _hf.evaluate("() => { if (recording) document.getElementById('recordBtn').click(); }")
        _hp.wait_for_timeout(600)
        _g = _hf.evaluate("""() => { if (!document.getElementById('composeCloseBtn')) return null;
            const b = (id) => document.getElementById(id).getBoundingClientRect();
            const x = b('composeCloseBtn'), m = b('menuBtn'), br = document.querySelector('.brand').getBoundingClientRect();
            const lab = document.querySelector('#postBtn .btn-label');
            return { xRight: Math.round(x.right), brandLeft: Math.round(br.left), brandW: Math.round(br.width),
                     menuLeft: Math.round(m.left), label: lab.innerText.trim(),
                     labelShown: getComputedStyle(lab).display !== 'none' && lab.getBoundingClientRect().width > 0 }; }""")
        _want = "Add" if _vp["width"] < 700 else "Add to post"
        check(f"@{_vp['width']}: × first, then the skribl wordmark, and the ⋯ well clear of both",
              bool(_g) and _g["xRight"] <= _g["brandLeft"] + 1 and _g["brandW"] > 20
              and _g["menuLeft"] > _g["xRight"] + 100, str(_g))
        _lab = _hf.evaluate("() => document.querySelector('#postBtn .btn-label').innerText.trim()")
        check(f"@{_vp['width']}: the attach button says {_want!r}, in words",
              _lab == _want and (not _g or _g["labelShown"]), repr(_lab))
        if _g:
            _xb = _hfr.locator("#composeCloseBtn").bounding_box()
            _hp.mouse.click(_xb["x"] + _xb["width"] / 2, _xb["y"] + _xb["height"] / 2)
            _hp.wait_for_timeout(600)
        check(f"@{_vp['width']}: a real tap on × closes the overlay",
              bool(_g) and _hp.evaluate("() => document.getElementById('padOverlay').hidden") is True)
        if _g:
            _hp.click("#padBtn")
            _hp.wait_for_timeout(1200)
        check(f"@{_vp['width']}: ...and the drawing is still there when the Skribl button reopens it",
              bool(_g) and _hf.evaluate("() => hasContent === true"))
        _hc.close()
    # FLIP, FROM THE SAME BUTTON (owner, v316: "couldn't you just select flip
    # from the menu once you've opened the editor?"). The host has ONE Skribl
    # button; the Pad's ⋯ "Flip Mode" row, while composing, opens Flip in the
    # SAME frame in compose mode, and Flip's "Skribl Pad" row comes back. The
    # frame then holds either editor, so the handshake names the editor and a
    # drawing is handed back only to the one that made it.
    print("\nCOMPOSE — Flip from the Pad's ⋯, and back")
    def _cur(pg):
        return [x for x in pg.frames if x.parent_frame is not None][0]
    _fc = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    _fp = _fc.new_page()
    _ferrs = []
    _fp.on("pageerror", lambda e: _ferrs.append(str(e)))
    _fposts = []
    _fp.on("request", lambda r: _fposts.append(r.url) if r.method == "POST" and "/api/skribls" in r.url else None)
    browsing.goto(_fp, BASE, "/feed")
    _fp.click("#padBtn")
    _fp.wait_for_timeout(3000)
    _ff = _cur(_fp)
    _ff.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    _ff.evaluate("() => { localStorage.removeItem('skribl_flip_autosave_v1'); document.getElementById('menuBtn').click(); }")
    _fp.wait_for_timeout(400)
    _ff.evaluate("() => document.getElementById('flipBtn').click()")
    _fp.wait_for_timeout(3500)
    _ff = _cur(_fp)
    _ff.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    _hdr = _ff.evaluate("""() => ({ path: location.pathname + location.search, x: !!document.getElementById('composeCloseBtn'),
        label: document.querySelector('#postBtn .btn-label').innerText.trim(),
        submit: document.getElementById('flipShareSubmit').textContent.trim() })""")
    check("the Pad's Flip Mode row opens Flip in the composer, with × and Add",
          _hdr["path"].endswith("/flip?compose=1") and _hdr["x"] and _hdr["label"] == "Add"
          and _hdr["submit"] == "Add to post", str(_hdr))
    _ffr = _fp.frame_locator("#padFrame")
    for _dy in (0, 30):
        _bx = _ffr.locator("#pad").bounding_box()
        _cx, _cy = _bx["x"] + _bx["width"] / 2, _bx["y"] + _bx["height"] / 2 + _dy
        _fp.mouse.move(_cx - 50, _cy); _fp.mouse.down()
        for _i in range(30):
            _fp.mouse.move(_cx - 50 + _i * 3, _cy + math.sin(_i / 5) * 25); _fp.wait_for_timeout(15)
        _fp.mouse.up()
        if _dy == 0:
            _ff.evaluate("() => addFrame()")
    _fp.wait_for_timeout(1200)
    check("composing, Flip writes no draft of its own",
          _ff.evaluate("() => localStorage.getItem('skribl_flip_autosave_v1') === null"))
    _ff.evaluate("() => document.getElementById('postBtn').click()")
    _fp.wait_for_timeout(600)
    _ff.evaluate("() => document.getElementById('flipShareSubmit').click()")
    _fp.wait_for_timeout(2500)
    check("Add to post closes the overlay and attaches the animation, publishing nothing",
          _fp.evaluate("() => document.getElementById('padOverlay').hidden") is True and not _fposts,
          f"POSTs: {_fposts}")
    _fp.click("#padBtn")
    _fp.wait_for_timeout(1500)
    _ff = _cur(_fp)
    _re = _ff.evaluate("() => ({ path: location.pathname + location.search, pages: frames.length })")
    check("reopening brings back Flip, holding both pages",
          _re["path"].endswith("/flip?compose=1") and _re["pages"] == 2, str(_re))
    _ff.evaluate("() => document.getElementById('moreBtn').click()")
    _fp.wait_for_timeout(400)
    _ff.evaluate("() => document.getElementById('padBtn').click()")
    _fp.wait_for_timeout(700)
    _sh = _ff.evaluate("""() => ({ shown: !document.getElementById('leaveSheet').hidden,
        title: document.getElementById('leaveSheetTitle').textContent, go: document.getElementById('leaveGo').textContent })""")
    check("switching back with an animation on the canvas asks first, in the composer's words",
          _sh["shown"] and _sh["title"] == "Switch to Skribl Pad?" and _sh["go"] == "Switch", str(_sh))
    _ff.evaluate("() => document.getElementById('leaveGo').click()")
    _fp.wait_for_timeout(3000)
    _ff = _cur(_fp)
    _pb = _ff.evaluate("() => ({ path: location.pathname + location.search, blank: !hasContent })")
    check("...and the Pad opens in the composer, blank: Flip's animation is not pushed into it",
          _pb["path"].endswith("/skribl-pad?compose=1") and _pb["blank"], str(_pb))
    check("no page errors across the switch", not _ferrs, "; ".join(_ferrs[:2]))
    _fc.close()
    _sf = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(_sf, BASE, "/flip")
    check("the standalone Flip has no × and still says Post",
          _sf.locator("#composeCloseBtn").count() == 0
          and _sf.evaluate("() => document.querySelector('#postBtn .btn-label').innerText.trim()") == "Post to Skribl")
    _sf.close()

    _sp = b.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(_sp, BASE, "/skribl-pad")
    check("the standalone Pad has no × and still says Post",
          _sp.locator("#composeCloseBtn").count() == 0
          and _sp.evaluate("() => document.querySelector('#postBtn .btn-label').innerText.trim()") == "Post to Skribl")
    _sp.close()

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
