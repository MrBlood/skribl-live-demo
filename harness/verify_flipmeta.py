"""Flip's share metadata: the title and caption a user actually typed.

THE BUG THIS REPRODUCES. `buildSharePayload()` in flip.js ended with a literal
`title:'Flip animation'` and sent no caption at all. Every Skribl shared from
Flip therefore arrived carrying the same meaningless title and an empty caption
— visible in production as `'title': 'Flip animation', 'caption': ''`. The Pad
has had `postTitleInput` and `postCaptionInput` since v131; Flip's template had
neither, so this was not a bug in the sense of code doing the wrong thing. It
was a whole control surface that was never built on one of the two editors.

Section 1 is source-only and is the regression guard: the literal must not come
back, and the payload builder must read the two inputs. It costs no browser.

Section 2 drives a real browser through the flow end to end — type a title and
a caption, share, then read the post back off the API and assert the values
survived. Asserting on the request body alone would prove only that the client
sent something; the round trip is what proves a user's words reach the platform.

Section 3 covers the empty case, because the compose step introduces a way to
share with nothing typed, and the server's substitution ('Untitled Skribl') is
what stops that becoming a blank row.
"""
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _layout import STATIC_DIR, template  # noqa: E402
from assertions import make_check

sys.path.insert(0, ROOT)
from skribl.core import MAX_CAPTION_CHARS  # noqa: E402

results = []


check = make_check(results, detail_on_pass=False)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------------------
print("FLIP METADATA — section 1: the regression guard, source only")

flip_js = os.path.join(STATIC_DIR, "flip.js")
with open(flip_js, encoding="utf-8") as fh:
    src = fh.read()

# The exact literal that shipped. Matched loosely on quoting/spacing so that
# reintroducing it in any form is caught, not just the original formatting.
check("the hardcoded 'Flip animation' title is gone from flip.js",
      not re.search(r"title\s*:\s*['\"]Flip animation['\"]", src),
      "the literal is back — every Flip share would carry the same title again")

check("buildSharePayload reads the title input",
      "postTitleInput" in src, "flip.js never reads #postTitleInput")
check("buildSharePayload reads the caption input",
      "postCaptionInput" in src, "flip.js never reads #postCaptionInput")

# A caption key that is never sent is the half of the bug that is easy to miss:
# the title is visible, an absent caption just looks like the user wrote none.
check("the share payload carries a caption key",
      re.search(r"caption\s*:", src) is not None,
      "no caption is sent, so the field can never be populated from Flip")

# Flip posts through the Pad's own sheet (owner: "shouldn't flip and pad look
# the same?"): one partial, included by both editors.
with open(template("skribl_flip.html"), encoding="utf-8") as fh:
    flip_markup = fh.read()
check("the Flip template includes the shared post sheet",
      "{% include 'skribl/_skribl_post.html' %}" in flip_markup)
with open(template("_skribl_post.html"), encoding="utf-8") as fh:
    markup = fh.read()
for _id in ("postTitleInput", "postCaptionInput", "postSubmitBtn",
            "postBody", "postResult"):
    check(f"the post sheet carries #{_id}", f'id="{_id}"' in markup)

# The compose step must not be able to appear as a fait accompli: the result
# row starts hidden, or a user would see a stale Watch under the fields.
check("the result row starts hidden",
      re.search(r'id="postResult"[^>]*\shidden', markup) is not None,
      "the previous post's row would show under the compose fields")


# ---------------------------------------------------------------------------
print("\nFLIP METADATA — section 2: a real browser, end to end")

TITLE = "Bouncing ball, take 3"
CAPTION = "Squash on frames 4-6. Timing still feels late on the recovery."


def fetch(pid):
    with urllib.request.urlopen(f"{API}/{pid}", timeout=15) as r:
        return json.loads(r.read())


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  [SKIP] playwright unavailable — section 2 needs a browser")
    summarise_and_exit()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    posted_bodies = []

    def _capture(route):
        req = route.request
        if req.method == "POST":
            # THE BODY MAY BE GZIPPED, and it did not use to be. lib/posted.js
            # compresses any post body over 4,096 B, and this fixture's — one
            # stroke, no media — sat under that until Flip started attaching a
            # share card (lib/postedcard.js, ~25 KB). Reading post_data as JSON
            # then returned nothing and three assertions here failed on a change
            # that had not touched titles at all. Read the bytes and inflate
            # when the client says it compressed them.
            try:
                raw = req.post_data_buffer
                if (req.headers.get("content-encoding") or "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                posted_bodies.append(json.loads((raw or b"{}").decode("utf-8")))
            except Exception:
                posted_bodies.append({})
        route.continue_()

    pg.route("**/api/skribls", _capture)

    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(1500)
    check("Flip loads with no JS errors", not errors, "; ".join(errors[:2]))

    # Draw one stroke, or the emptiness check refuses to open the sheet.
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 60, box["y"] + 60)
    pg.mouse.down()
    pg.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(200)

    pg.click("#postBtn")
    pg.wait_for_timeout(400)
    check("the Share button opens the compose step, not an immediate post",
          pg.is_visible("#postTitleInput") and not posted_bodies,
          f"{len(posted_bodies)} post(s) fired before the user typed anything")

    pg.fill("#postTitleInput", TITLE)
    pg.fill("#postCaptionInput", CAPTION)
    pg.wait_for_timeout(100)
    check("the caption counter tracks what was typed",
          pg.inner_text("#postCharCount").startswith(str(len(CAPTION))),
          pg.inner_text("#postCharCount"))
    # THE OTHER HALF OF THE COUNTER. maxlength is rendered from
    # skribl_limits.caption (300); the "/ N" beside it was a literal 280 in two
    # scripts and two templates, so a user could read "300 / 280". The limit
    # the counter names must be the limit the field enforces, and that must be
    # the column width. Red on v287.
    _maxlen = pg.get_attribute("#postCaptionInput", "maxlength")
    check("Flip's caption field enforces the configured limit",
          _maxlen == str(MAX_CAPTION_CHARS), repr(_maxlen))
    check("and Flip's counter names that same limit",
          pg.inner_text("#postCharCount") == f"{len(CAPTION)} / {_maxlen}",
          pg.inner_text("#postCharCount"))

    pg.click("#postSubmitBtn")
    pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
    pg.wait_for_timeout(600)

    check("exactly one post was made", len(posted_bodies) == 1, str(len(posted_bodies)))
    body = posted_bodies[0] if posted_bodies else {}
    check("the request body carries the typed title",
          body.get("title") == TITLE, repr(body.get("title")))
    check("the request body carries the typed caption",
          body.get("caption") == CAPTION, repr(body.get("caption")))

    # The link the post left in Your Skribls, which Watch, Share and Copy
    # link all hand on.
    url = pg.evaluate("() => (SkriblPosted.list()[0] || {}).url || ''")
    check("the post leaves a player link", "/s/" in url, url)
    check("the posted title stays in its field, as on the Pad",
          pg.is_visible("#postTitleInput") and pg.input_value("#postTitleInput") == TITLE,
          pg.input_value("#postTitleInput"))

    pid = url.rstrip("/").rsplit("/", 1)[-1]
    stored = fetch(pid)
    check("the stored post's title is what the user typed",
          stored.get("title") == TITLE, repr(stored.get("title")))
    check("the stored post's caption is what the user typed",
          stored.get("caption") == CAPTION, repr(stored.get("caption")))
    check("and it is not the old hardcoded string",
          stored.get("title") != "Flip animation", repr(stored.get("title")))

    # -----------------------------------------------------------------------
    print("\nFLIP METADATA — section 3: sharing with nothing typed")

    posted_bodies.clear()
    pg2 = b.new_page()
    pg2.route("**/api/skribls", _capture)
    pg2.goto(f"{BASE}/flip", wait_until="load")
    pg2.wait_for_timeout(1500)
    box = pg2.locator("#pad").bounding_box()
    pg2.mouse.move(box["x"] + 70, box["y"] + 70)
    pg2.mouse.down()
    pg2.mouse.move(box["x"] + 160, box["y"] + 140, steps=8)
    pg2.mouse.up()
    pg2.wait_for_timeout(200)
    pg2.click("#postBtn")
    pg2.wait_for_timeout(300)
    pg2.click("#postSubmitBtn")
    pg2.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
    pg2.wait_for_timeout(600)

    body2 = posted_bodies[0] if posted_bodies else {}
    check("an untouched title is sent as empty, not as a placeholder",
          body2.get("title") == "", repr(body2.get("title")))
    url2 = pg2.evaluate("() => (SkriblPosted.list()[0] || {}).url || ''")
    stored2 = fetch(url2.rstrip("/").rsplit("/", 1)[-1])
    check("the server substitutes 'Untitled Skribl' for an empty title",
          stored2.get("title") == "Untitled Skribl", repr(stored2.get("title")))
    check("an untyped caption stores as empty, not null",
          stored2.get("caption") == "", repr(stored2.get("caption")))

    # -----------------------------------------------------------------------
    print("\nFLIP METADATA — section 4: the Pad's counter, same contract")
    # Same defect, other editor: editor_post.js had its own ' / 280'. Pinned
    # here rather than in a Pad suite because this file is where the two
    # editors' title/caption surfaces are held to one contract.
    # The Pad's Post is disabled until a take exists: draw on #canvas and stop
    # the recording, the way verify_sheetfit's author() does.
    pg3 = b.new_page()
    pg3.goto(f"{BASE}/", wait_until="load")
    pg3.wait_for_timeout(1500)
    box = pg3.locator("#canvas").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg3.mouse.move(cx, cy)
    pg3.mouse.down()
    for i in range(30):
        pg3.mouse.move(cx + i * 4, cy + (i % 7) * 6)
        if i % 10 == 0:
            pg3.wait_for_timeout(80)
    pg3.mouse.up()
    pg3.wait_for_timeout(400)
    pg3.click("#recordBtn")
    pg3.wait_for_timeout(400)
    pg3.click("#postBtn")
    pg3.wait_for_timeout(600)
    _maxlen3 = pg3.get_attribute("#postCaptionInput", "maxlength")
    check("the Pad's caption field enforces the configured limit",
          _maxlen3 == str(MAX_CAPTION_CHARS), repr(_maxlen3))
    pg3.fill("#postCaptionInput", "x" * MAX_CAPTION_CHARS)
    pg3.wait_for_timeout(100)
    check("a full caption reads N / N on the Pad, never N / less-than-N",
          pg3.inner_text("#postCharCount") == f"{MAX_CAPTION_CHARS} / {_maxlen3}",
          pg3.inner_text("#postCharCount"))
    pg3.close()

    b.close()

print("\nSHARE — a server failure is visible, not a vanished chip")
# WHAT HAPPENED. The Render Postgres instance became unresolvable and every
# POST /api/skribls returned 500. The client reported it only as a transient
# chip, which on a phone is easy to miss entirely — so a hard server failure
# read as "the share button does nothing", and three client-side theories were
# chased before the server log settled it.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    for _status, _expect in ((500, "server"), (503, "server"), (400, "client")):
        _pg = _b.new_page(viewport={"width": 390, "height": 844})
        # A def, not a lambda: Playwright's sync route handler must not be a
        # lambda returning the fulfil coroutine — it raises inside the event
        # listener and the route never completes.
        # Playwright calls a route handler with (route, request). Omitting the
        # second parameter means the Request object lands in the next slot —
        # here it became the status code, and fulfil failed trying to
        # serialise it.
        def _fulfil(route, request=None, st=_status):
            route.fulfill(status=st, content_type="application/json", body="{}")
        _pg.route("**/api/skribls", _fulfil)
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1300)
        _box = _pg.locator("#pad").bounding_box()
        _pg.mouse.move(_box["x"] + 60, _box["y"] + 60)
        _pg.mouse.down()
        _pg.mouse.move(_box["x"] + 150, _box["y"] + 130, steps=8)
        _pg.mouse.up()
        _pg.wait_for_timeout(250)
        _pg.click("#postBtn")
        _pg.wait_for_timeout(300)
        _pg.click("#postSubmitBtn")
        _pg.wait_for_timeout(900)

        check(f"a {_status} shows a visible error in the sheet",
              _pg.is_visible("#postStatusLabel")
              and _pg.evaluate("() => document.getElementById('postStatus').classList.contains('error')"),
              "the only signal was a chip that disappears")
        _msg = _pg.inner_text("#postStatusLabel")
        check(f"a {_status} says the drawing is safe",
              "safe" in _msg.lower() or "still here" in _msg.lower(), _msg)
        if _expect == "server":
            check(f"a {_status} blames the server, not the user",
                  "server" in _msg.lower(), _msg)
        check(f"after a {_status} the sheet is still usable",
              _pg.is_visible("#postTitleInput") and _pg.is_enabled("#postTitleInput")
              and _pg.is_visible("#postSubmitBtn"),
              "a failed post must not strand the user on a dead sheet")
        check(f"and a {_status} does not leave sharing stuck",
              _pg.evaluate("() => sharing") is False,
              "every later tap would silently do nothing")
        _pg.close()

    # A retry must not show the previous failure above it.
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _fail = {"on": True}
    def _route(route, request=None):
        if _fail["on"]:
            _fail["on"] = False
            route.fulfill(status=500, content_type="application/json", body="{}")
        else:
            route.continue_()
    _pg.route("**/api/skribls", _route)
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
    _box = _pg.locator("#pad").bounding_box()
    _pg.mouse.move(_box["x"] + 60, _box["y"] + 60)
    _pg.mouse.down()
    _pg.mouse.move(_box["x"] + 150, _box["y"] + 130, steps=8)
    _pg.mouse.up()
    _pg.wait_for_timeout(250)
    _pg.click("#postBtn"); _pg.wait_for_timeout(250)
    _pg.click("#postSubmitBtn"); _pg.wait_for_timeout(800)
    check("the first attempt failed visibly", _pg.is_visible("#postStatusLabel"))
    _pg.keyboard.press("Escape"); _pg.wait_for_timeout(450)
    _pg.click("#postBtn"); _pg.wait_for_timeout(300)
    check("reopening clears the stale failure",
          not _pg.is_visible("#postStatusLabel"),
          "a previous error sat above a fresh attempt")
    _pg.click("#postSubmitBtn")
    _pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
    check("and the retry succeeds", "/s/" in _pg.evaluate("() => (SkriblPosted.list()[0] || {}).url || ''"))
    _pg.close()

    # A 2xx THAT IS NOT A POST (preflight PF-028). Flip read any 2xx as
    # posted: a captive portal's sign-in page answers a POST with a 200 in
    # HTML, and the sheet said "Posted!" with a link to /s/undefined -- then
    # dropped the Idempotency-Key, so the retry was a second post whenever the
    # server had made the first. The first answer is the odd one; the retry
    # reaches the real server.
    for _label, _ctype, _odd_body in (
            ("a body that is not JSON", "application/json", "{not json"),
            ("a sign-in page", "text/html", "<html><body>Sign in to the Wi-Fi</body></html>"),
            ("JSON with no post in it", "application/json", "{}"),
            ("a JSON null", "application/json", "null")):
        _pg = _b.new_page(viewport={"width": 390, "height": 844})
        _keys = []
        _odd = {"on": True}
        def _answer(route, request=None, ct=_ctype, body=_odd_body):
            if route.request.method != "POST":
                return route.continue_()
            _keys.append(route.request.headers.get("idempotency-key"))
            if _odd["on"]:
                _odd["on"] = False
                route.fulfill(status=200, content_type=ct, body=body)
            else:
                route.continue_()
        _pg.route("**/api/skribls", _answer)
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1300)
        _box = _pg.locator("#pad").bounding_box()
        _pg.mouse.move(_box["x"] + 60, _box["y"] + 60)
        _pg.mouse.down()
        _pg.mouse.move(_box["x"] + 150, _box["y"] + 130, steps=8)
        _pg.mouse.up()
        _pg.wait_for_timeout(250)
        _pg.click("#postBtn"); _pg.wait_for_timeout(250)
        _pg.click("#postSubmitBtn"); _pg.wait_for_timeout(900)
        _said = _pg.inner_text("#postStatusLabel") if _pg.is_visible("#postStatusLabel") else ""
        check(f"{_label} in a 200 is a failure, not a post",
              _pg.evaluate("() => document.getElementById('postStatus').classList.contains('error')")
              and not _pg.is_visible("#postWatchBtn"),
              f"the sheet says {_said!r}")
        check(f"...and says so, without guessing the cause",
              "unexpected response" in _said and "safe" in _said, repr(_said))
        # THE RETRY: the same button, now Try again.
        _again = _pg.is_visible("#postSubmitBtn") and _pg.is_enabled("#postSubmitBtn")
        if _again:
            _pg.click("#postSubmitBtn")
            try:
                _pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
            except Exception:                        # noqa: BLE001
                pass
        check(f"...and the retry carries the same Idempotency-Key, so a post the server did make is found, not made twice",
              _again and len(_keys) == 2 and bool(_keys[0]) and _keys[0] == _keys[1],
              f"Try again offered: {_again}; keys sent: {_keys}")
        _pg.close()
    _b.close()

print("\nSHARE — a refusal before sending is said in the sheet")
# Flip's page and point budgets answer before the network does. Its own card
# showed them in a box of its own; the Pad's sheet says them on its status line,
# drawn as an error, and Post keeps its word -- the remedy is to change the
# drawing, not to press again, so the button must not turn into Try again.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _sent = []
    _pg.on("request", lambda r: _sent.append(r.url) if r.method == "POST" and "/api/skribls" in r.url else None)
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
    # A real stroke first, which is what lets Post open at all; then pages
    # past the ceiling, which no hand would add one at a time.
    _box = _pg.locator("#pad").bounding_box()
    _pg.mouse.move(_box["x"] + 60, _box["y"] + 60)
    _pg.mouse.down()
    _pg.mouse.move(_box["x"] + 150, _box["y"] + 130, steps=8)
    _pg.mouse.up()
    _pg.wait_for_timeout(250)
    _pg.evaluate("""() => { const B = window.SkriblPointBudget;
      while (frames.length <= B.MAX_FRAMES) frames.push({ strokes: [], strokeGroups: [], hold: 1 });
      render(); }""")
    _pg.click("#postBtn"); _pg.wait_for_timeout(500)
    _pg.click("#postSubmitBtn"); _pg.wait_for_timeout(700)
    _ref = _pg.evaluate("""() => { const s = document.getElementById('postStatus'), l = document.getElementById('postStatusLabel');
      return { shown: !!s && !s.hidden && s.classList.contains('error'), says: l ? l.textContent : '',
               button: (document.getElementById('postSubmitLabel') || {}).textContent || '' }; }""")
    check("too many pages is said on the sheet's status line, as an error",
          _ref["shown"] and "pages and the limit is" in _ref["says"], str(_ref))
    check("...nothing is sent, and Post keeps its word rather than offering Try again",
          not _sent and _ref["button"].strip() == "Post to Skribl", f"{_ref}; {len(_sent)} POST(s)")
    _b.close()

print("\nSHARE — it can never fail silently")
# THE SHAPE OF THE BUG BEING GUARDED. flip.js had 26 unguarded
# getElementById(id).addEventListener chains. A null from any one throws at the
# top level and aborts the rest of the file, so every binding written after it
# never happens — and postBtn was bound near the end. That is exactly what
# "share does nothing while everything else works" looks like from a phone.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _logs = []
    _pg.on("console", lambda m: _logs.append(m.text))
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)

    check("bindEl exists and is used instead of raw chained lookups",
          _pg.evaluate("() => typeof bindEl === 'function'"),
          "one missing element can still abort every later binding")

    # Deleting an element that is bound EARLY must not stop a later binding
    # from having happened. Reload with a node removed before scripts run.
    _pg2 = _b.new_page(viewport={"width": 390, "height": 844})
    _pg2.add_init_script("""
      document.addEventListener('readystatechange', () => {
        if (document.readyState === 'interactive') {
          const el = document.getElementById('miSave');
          if (el) el.remove();
        }
      });
    """)
    _errs2 = []
    _pg2.on("pageerror", lambda e: _errs2.append(str(e)))
    _pg2.goto(f"{BASE}/flip", wait_until="load")
    _pg2.wait_for_timeout(1400)
    check("removing a bound element does not throw at load",
          not _errs2, "; ".join(_errs2[:2]))
    check("and the share button is still wired afterwards",
          _pg2.evaluate("() => typeof openShareCompose === 'function'"
                        " && !!document.getElementById('postBtn')"))

    # Draw, then confirm the sheet actually opens — the user-visible contract.
    box = _pg2.locator("#pad").bounding_box()
    _pg2.mouse.move(box["x"] + 60, box["y"] + 60)
    _pg2.mouse.down()
    _pg2.mouse.move(box["x"] + 150, box["y"] + 130, steps=8)
    _pg2.mouse.up()
    _pg2.wait_for_timeout(300)
    _pg2.click("#postBtn")
    _pg2.wait_for_timeout(400)
    check("tapping share opens the compose sheet even after a missing element",
          _pg2.is_visible("#postTitleInput"),
          "share did nothing — the failure this whole section exists for")
    _b.close()

summarise_and_exit()
