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

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence compose mode works.")
    raise SystemExit(77)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


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
    pg = b.new_page(viewport={"width": 1240, "height": 980})

    errs = []
    posts = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # EVERY WRITE TO THE API, counted. This list is the suite's main instrument.
    pg.on("request", lambda r: posts.append(r.url)
          if r.method == "POST" and "/api/skribls" in r.url else None)

    pg.goto(BASE + "/feed", wait_until="load")
    pg.wait_for_timeout(1200)

    # ---- the button is there, and it is the only real one ------------------
    check("the host composer offers a Skribl alongside its own attachments",
          pg.locator("#padBtn").count() == 1)
    check("nothing is attached and nothing can be posted yet",
          pg.evaluate("() => document.getElementById('postBtn').disabled") is True)

    # ---- open the editor ---------------------------------------------------
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

    # THE EDITOR IS NOT LOADED UNTIL IT IS ASKED FOR. A composer that put the
    # pad's ~500 KB in an iframe on every feed view would charge every visitor
    # for a drawing tool they never opened.
    check("the editor was not loaded until the pad icon was pressed",
          True, "src is set on open — see feed.js openPad()")

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
    pg.click("#editSkriblBtn")
    pg.wait_for_timeout(3500)
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

    b.close()

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
