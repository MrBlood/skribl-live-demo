#!/usr/bin/env python3
"""verify_clouddrafts: drafts saved to an account, and opened in a composer (v316).

The owner's words: "a way to save skribl drafts (not on my machine as a file),
so I could just click the pen to add a skribl to the post, load the saved
skribl, then add it to post." Section 4 is that sentence, driven end to end in
a real host's composer; the rest is what has to hold for it to be safe.

Runs against examples/host_app — a real host with real sign-in, the
double-submit CSRF triple and its own composer — spawned on a free port with
its own database, so it needs no shared server. SKRIBL_MAX_DRAFTS is 3 here so
the cap can be reached in a few saves.

  1  The API: signed-out is 401, CSRF is required on writes, the payload is
     validated like a post, the cap is 409, and somebody else's draft is the
     same 404 a missing one is — for read, overwrite AND delete.
  2  Nothing a draft does publishes: no skribl_posts row, no Library entry.
  3  The editors say where drafts go: the account when signed in, this browser
     when not, and the limit on the page is the server's.
  4  The composer: draw, ⋯ Save draft, close, open the pen again (blank),
     ⋯ Open a draft, Add to post, Post. The post is the saved drawing.
  5  Signed out, drafts live in this browser and survive a reload.
  6  The Library's Drafts tab (v317): the account's list or this browser's,
     Open to the right editor, Delete asks first, and an editor holding work
     asks before a draft replaces it.
  7  Storage that never answers, or a connection that died in the background
     (v317, the owner's iPhone): the sheet says so and retries; a read reconnects.
  8  Drafts that stay (v317): a failed index read writes nothing over the list;
     a draft its index lost is listed again; a delete that stops half-way
     neither brings it back nor leaves a dead row; media is stored as bytes and
     comes back a Blob; a refused write keeps the working connection; and one
     row asks at a time, in the sheet and in the Library.
"""
import base64
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "host_app"

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence drafts work.")
    raise SystemExit(77)

import sqlalchemy as sa
from assertions import make_check
import browsing

results = []
check = make_check(results)
CAP = 3


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()
BASE = f"http://127.0.0.1:{PORT}"
_tmp = tempfile.mkdtemp()
DB_URL = f"sqlite:///{_tmp}/example.db"
env = dict(os.environ, EXAMPLE_DATABASE_URL=DB_URL,
           EXAMPLE_SECRET="harness-clouddrafts", SKRIBL_RATE_MAX_POSTS="100000",
           SKRIBL_MAX_DRAFTS=str(CAP), PYTHONPATH=str(ROOT))
subprocess.run(
    [sys.executable, "-c",
     "import app as ex; a = ex.create_app();"
     " ctx = a.app_context(); ctx.push(); ex.db.create_all();"
     " ex.db.session.add_all([ex.User(handle='ada'), ex.User(handle='grace')]);"
     " ex.db.session.commit()"],
    cwd=str(EXAMPLE), env=env, check=True, capture_output=True)
proc = subprocess.Popen(
    [sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(PORT), "--no-reload"],
    cwd=str(EXAMPLE), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def wait_ready(timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", PORT), 0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def durable(query):
    eng = sa.create_engine(DB_URL)
    try:
        with eng.connect() as c:
            return c.execute(sa.text(query)).scalar()
    finally:
        eng.dispose()


def draw(pg, box, turns=3, n=50):
    import math
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        t = i / float(n - 1)
        a = t * turns * 2 * math.pi
        r = 10 + t * min(box["width"], box["height"]) * 0.3
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r)
        pg.wait_for_timeout(10)
    pg.mouse.up()


def sign_in(pg, index):
    browsing.goto(pg, BASE, "/", require_boot=False)
    pg.select_option("select[name=uid]", index=index)
    pg.click("button:has-text('Sign in')")
    pg.wait_for_timeout(600)


def api(pg, method, path, body=None, csrf=True):
    """A request from the signed-in browser's own cookie jar."""
    token = pg.evaluate("() => window.SKRIBL_CSRF_TOKEN || ''") if csrf else ""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Skribl-CSRF"] = token
    kw = {"headers": headers}
    if body is not None:
        kw["data"] = json.dumps(body)
    r = pg.request.fetch(BASE + "/skribl/api/drafts" + path, method=method, **kw)
    try:
        data = r.json()
    except Exception:
        data = None
    return r.status, data


# Strokes on the Pad live under frames[] (payload version 2).
STROKES = "(s => s.frames.reduce((n, f) => n + (f.strokes || []).length, 0))"


# A drawing's identity, not its size: two spirals drawn by the same helper
# have the same stroke COUNT (section 6 found that out), never the same points.
PRINT = "(s => JSON.stringify(s.frames.map(f => f.strokes)))"


def canon(printed):
    """The drawing as a structure: the server hands JSON back with its keys
    sorted, so the same strokes come back in a different key order."""
    return json.dumps(json.loads(printed), sort_keys=True)


def _diff_detail(got, want, name):
    if got == want:
        return f"same drawing, name {name!r}"
    i = next((k for k in range(min(len(got), len(want))) if got[k] != want[k]), min(len(got), len(want)))
    return (f"name {name!r}; drawing differs at char {i} of {len(got)}/{len(want)}: "
            f"got ...{got[max(0, i - 40):i + 40]!r} want ...{want[max(0, i - 40):i + 40]!r}")


def pad_strokes(pg):
    return pg.evaluate("() => " + STROKES
                       + "(document.getElementById('padFrame').contentWindow.serializeSkribl())")


def menu_click(fr, item, btn="#menuBtn"):
    fr.locator(btn).click()
    fr.locator(item).wait_for(state="visible", timeout=5000)
    fr.locator(item).click()


try:
    if not wait_ready():
        err = proc.stderr.read().decode("utf-8", "replace")[-1500:] if proc.stderr else ""
        sys.exit(f"FAIL: the example app did not start on port {PORT}.\n{err}")

    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---------------------------------------------------------------- 1
        print("\n1 — THE API: OWNER ONLY, CSRF, VALIDATED, CAPPED")
        errs = []

        def watch(page, tag):
            # Every page this suite drives, not only the first: an uncaught
            # error on the hung-storage or second-user page is still a bug.
            page.on("pageerror", lambda e: errs.append(f"{tag}: {e}"))
            return page

        anon = watch(b.new_context().new_page(), "anon")
        browsing.goto(anon, BASE, "/skribl/skribl-pad", require_boot=False)
        st, _ = api(anon, "GET", "")
        check("signed out, the list is 401", st == 401, str(st))
        st, _ = api(anon, "POST", "", {"kind": "pad", "payload": {}})
        check("signed out, a save is 401", st in (401, 403), str(st))

        ctx_a = b.new_context(viewport={"width": 1180, "height": 900})
        pa = watch(ctx_a.new_page(), "owner")
        sign_in(pa, 0)
        browsing.goto(pa, BASE, "/skribl/skribl-pad", require_boot=False)
        pa.wait_for_timeout(1500)
        draw(pa, pa.locator("#canvas").bounding_box())
        pa.wait_for_timeout(300)
        payload = pa.evaluate("() => serializeSkribl()")
        check("a real Pad serialisation to save", isinstance(payload, dict) and payload,
              str(type(payload)))

        st, lst = api(pa, "GET", "")
        check("signed in, an empty list and the server's limit",
              st == 200 and lst.get("items") == [] and lst.get("limit") == CAP,
              f"{st} {lst}")
        st, made = api(pa, "POST", "", {"kind": "pad", "title": "Spiral", "payload": payload},
                       csrf=False)
        check("a save WITHOUT the CSRF header is refused", st in (400, 403), str(st))
        st, made = api(pa, "POST", "", {"kind": "pad", "title": "Spiral", "payload": payload})
        check("a save with it is 201, with an id", st == 201 and made and made.get("id"),
              f"{st} {made}")
        did = (made or {}).get("id", "none")
        st, got = api(pa, "GET", "/" + did)
        check("reading it back returns the same drawing",
              st == 200 and got.get("payload") == payload and got.get("title") == "Spiral",
              f"{st}")
        st, lst = api(pa, "GET", "")
        check("the list carries no payloads (it is a list, not a download)",
              st == 200 and len(lst["items"]) == 1 and "payload" not in lst["items"][0],
              json.dumps(lst)[:200])
        st, _ = api(pa, "PUT", "/" + did, {"kind": "pad", "title": "Spiral 2", "payload": payload})
        st2, got = api(pa, "GET", "/" + did)
        check("an overwrite keeps the id and takes the new title",
              st == 200 and got.get("title") == "Spiral 2", f"{st} {got and got.get('title')}")
        st, bad = api(pa, "POST", "", {"kind": "pad", "payload": "not an object"})
        check("a payload that is not an object is 400", st == 400, f"{st} {bad}")
        st, bad = api(pa, "POST", "", {"kind": "movie", "payload": payload})
        check("an unknown kind is 400", st == 400, f"{st} {bad}")
        st, bad = api(pa, "POST", "", {"kind": "pad", "payload": payload,
                                       "thumbnail": "javascript:alert(1)"})
        check("a thumbnail that is not an image data URL is 400", st == 400, f"{st} {bad}")
        # Only the raster types the editors make, their bytes checked (v317,
        # security review: anything that began "data:image/" was stored).
        _svg = "data:image/svg+xml;base64," + base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'/>").decode()
        st, _ = api(pa, "POST", "", {"kind": "pad", "payload": payload, "thumbnail": _svg})
        check("an SVG thumbnail is 400", st == 400, str(st))
        _fake = "data:image/png;base64," + base64.b64encode(b"not a png at all, just text").decode()
        st, _ = api(pa, "POST", "", {"kind": "pad", "payload": payload, "thumbnail": _fake})
        check("a 'PNG' thumbnail whose bytes are not a PNG is 400", st == 400, str(st))
        # A body nested past the parser's recursion was a 500 on every JSON route.
        _tok = pa.evaluate("() => window.SKRIBL_CSRF_TOKEN || ''")
        _deep = pa.request.fetch(BASE + "/skribl/api/drafts", method="POST",
                                 headers={"Content-Type": "application/json", "X-Skribl-CSRF": _tok},
                                 data=("[" * 100000).encode())
        check("a body nested too deeply to parse is a 400, not a server error", _deep.status == 400, str(_deep.status))
        # 201 frames: over SKRIBL_MAX_FRAMES, the bound a post meets.
        huge = dict(payload, frames=payload["frames"] * 201)
        st, bad = api(pa, "POST", "", {"kind": "pad", "payload": huge})
        check("a payload over a post's bounds is refused like a post's",
              st in (400, 413), f"{st} {(bad or {}).get('error', '')[:80]}")

        for i in range(CAP - 1):
            api(pa, "POST", "", {"kind": "pad", "title": f"fill {i}", "payload": payload})
        st, over = api(pa, "POST", "", {"kind": "pad", "title": "one too many", "payload": payload})
        check(f"the {CAP + 1}th draft is 409 with words a person can act on",
              st == 409 and "Delete one" in (over or {}).get("error", ""), f"{st} {over}")
        st, _ = api(pa, "PUT", "/" + did, {"kind": "pad", "title": "Spiral 3", "payload": payload})
        check("AT the cap, overwriting an existing draft still works", st == 200, str(st))

        # Somebody else.
        ctx_b = b.new_context()
        pb = watch(ctx_b.new_page(), "other")
        sign_in(pb, 1)
        browsing.goto(pb, BASE, "/skribl/skribl-pad", require_boot=False)
        st, lst = api(pb, "GET", "")
        check("another user lists none of them", st == 200 and lst["items"] == [], f"{st} {lst}")
        st_r, _ = api(pb, "GET", "/" + did)
        st_m, _ = api(pb, "GET", "/nosuchdraft")
        check("another user reading it gets the SAME 404 a missing id gets",
              st_r == 404 and st_m == 404, f"theirs {st_r}, missing {st_m}")
        st_w, _ = api(pb, "PUT", "/" + did, {"kind": "pad", "title": "hijack", "payload": payload})
        st_d, _ = api(pb, "DELETE", "/" + did)
        check("and cannot overwrite or delete it (404 both)", st_w == 404 and st_d == 404,
              f"PUT {st_w}, DELETE {st_d}")
        check("the owner's draft is untouched by those attempts",
              durable(f"SELECT title FROM skribl_drafts WHERE public_id='{did}'") == "Spiral 3")

        # ---------------------------------------------------------------- 2
        print("\n2 — A DRAFT PUBLISHES NOTHING")
        check("no skribl_posts row exists after all of that",
              durable("SELECT COUNT(*) FROM skribl_posts") == 0)
        lib = pa.request.get(BASE + "/skribl/library")
        check("and the owner's Library does not list drafts as posts",
              "Spiral 3" not in lib.text(), f"status {lib.status}")

        # Back to one draft for the browser sections.
        st, lst = api(pa, "GET", "")
        for it in lst["items"]:
            if it["id"] != did:
                api(pa, "DELETE", "/" + it["id"])
        st, lst = api(pa, "GET", "")
        check("delete works (back to one)", len(lst["items"]) == 1, str(len(lst["items"])))

        # ---------------------------------------------------------------- 3
        print("\n3 — THE EDITORS SAY WHERE A DRAFT GOES")
        for path in ("/skribl/skribl-pad", "/skribl/flip"):
            browsing.goto(pa, BASE, path, require_boot=False)
            pa.wait_for_timeout(800)
            cfg = pa.evaluate("() => window.SKRIBL_DRAFTS")
            where = pa.evaluate("() => window.SkriblSavedDrafts && window.SkriblSavedDrafts.where()")
            check(f"{path} signed in: the account, with the server's limit",
                  cfg and cfg.get("signedIn") is True and cfg.get("limit") == CAP
                  and where == "account", f"{cfg} where={where}")
            pa.locator("#moreBtn" if "flip" in path else "#menuBtn").click()
            sub = pa.locator("#saveCloudDraftItem").inner_text()
            check(f"{path} ⋯ Save draft says 'To your account'", "account" in sub.lower(), sub)
            pa.keyboard.press("Escape")
        browsing.goto(anon, BASE, "/skribl/skribl-pad", require_boot=False)
        anon.wait_for_timeout(800)
        where = anon.evaluate("() => window.SkriblSavedDrafts && window.SkriblSavedDrafts.where()")
        check("signed out: this browser", where == "browser", str(where))

        # ---------------------------------------------------------------- 4
        print("\n4 — THE PEN, A SAVED DRAWING, ADD TO POST")
        browsing.goto(pa, BASE, "/", require_boot=False)
        pa.click("#padBtn")
        pa.wait_for_timeout(4500)
        fr = pa.frame_locator("#padFrame")
        draw(pa, fr.locator("#canvas").bounding_box(), turns=5)
        pa.wait_for_timeout(300)
        pa.evaluate("() => document.getElementById('padFrame').contentWindow.SkriblName.set('Composer wave')")
        menu_click(fr, "#saveCloudDraftItem")
        pa.wait_for_timeout(1500)
        n = durable("SELECT COUNT(*) FROM skribl_drafts")
        check("⋯ Save draft inside the composer stores it on the account", n == 2, str(n))
        saved_strokes = pad_strokes(pa)
        saved_print = canon(pa.evaluate("() => " + PRINT
                                        + "(document.getElementById('padFrame').contentWindow.serializeSkribl())"))

        # Abandon: close the overlay without adding.
        fr.locator("#composeCloseBtn").click()
        pa.wait_for_timeout(800)
        check("closing the editor attached nothing",
              pa.evaluate("() => document.getElementById('attach').hidden") is True)
        pa.click("#padBtn")
        pa.wait_for_timeout(1500)
        # Closing is not discarding: composehost keeps the frame, and with it
        # the canvas, until the host's Remove. So the canvas is still busy, and
        # scribbling more makes it DIFFERENT from the saved draft.
        check("reopening the pen keeps what was on the canvas (close is not discard)",
              pad_strokes(pa) == saved_strokes, f"{pad_strokes(pa)} vs {saved_strokes}")
        draw(pa, fr.locator("#canvas").bounding_box(), turns=2, n=30)
        pa.wait_for_timeout(300)
        busy = pad_strokes(pa)
        check("more scribble makes the canvas differ from the draft", busy != saved_strokes,
              f"{busy}")

        menu_click(fr, "#openCloudDraftItem")
        fr.locator("#savedDraftsSheet .sdrafts-open").first.wait_for(timeout=5000)
        rows = fr.locator("#savedDraftsSheet .sdrafts-name").all_inner_texts()
        check("⋯ Open a draft lists the account's drafts, newest first",
              rows[:1] == ["Composer wave"] and len(rows) == 2, str(rows))
        fr.locator("#savedDraftsSheet .sdrafts-open").first.click()
        pa.wait_for_timeout(600)
        meta = fr.locator("#savedDraftsSheet .sdrafts-meta").first.inner_text()
        check("with work on the canvas, the first tap only ASKS",
              "replaces" in meta and pad_strokes(pa) == busy, f"{meta!r} {pad_strokes(pa)}")
        fr.locator("#savedDraftsSheet .sdrafts-open").first.click()
        pa.wait_for_timeout(1500)
        got = pad_strokes(pa)
        check("the second tap puts the saved drawing on the canvas",
              got == saved_strokes and got > 0, f"{got} vs saved {saved_strokes}")
        sheet_hidden = pa.evaluate("() => document.getElementById('padFrame').contentDocument"
                                   ".getElementById('savedDraftsSheet').hidden")
        check("and closes the sheet", sheet_hidden is True, str(sheet_hidden))
        name = pa.evaluate("() => document.getElementById('padFrame').contentWindow.SkriblName.get()")
        check("with the draft's name", name == "Composer wave", repr(name))

        fr.locator("#postBtn").click()
        pa.wait_for_timeout(1000)
        fr.locator("#postSubmitBtn").click()
        pa.wait_for_timeout(3500)
        check("Add to post attaches it",
              pa.evaluate("() => !document.getElementById('attach').hidden") is True)
        attached = pa.evaluate(
            "() => " + STROKES + "(JSON.parse(document.getElementById('skriblPayload').value))")
        check("the attached drawing is the saved one", attached == saved_strokes,
              f"{attached} vs {saved_strokes}")
        pa.fill("#body", "from a saved draft")
        pa.click("#postBtn")
        pa.wait_for_url(BASE + "/", timeout=20000)
        pa.wait_for_timeout(1500)
        check("posting it makes exactly one Skribl, authored by the signed-in user",
              durable("SELECT COUNT(*) FROM skribl_posts") == 1
              and str(durable("SELECT user_id FROM skribl_posts LIMIT 1")) == "1")
        check("and the draft is KEPT (the author deletes it when done)",
              durable("SELECT COUNT(*) FROM skribl_drafts") == 2)

        # --------------------------------------------------------------- 4b
        print("\n4b — A FLIP DRAFT, FROM THE PAD'S COMPOSER")
        browsing.goto(pa, BASE, "/skribl/flip", require_boot=False)
        pa.wait_for_timeout(1500)
        pa.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        for page in (0, 1):
            draw(pa, pa.locator("#pad").bounding_box(), turns=2, n=30)
            if page == 0:
                pa.evaluate("() => addFrame()")
        pa.evaluate("() => window.SkriblName.set('Bounce')")
        pa.wait_for_timeout(300)
        menu_click(pa, "#saveCloudDraftItem", btn="#moreBtn")
        pa.wait_for_timeout(1500)
        check("Flip's ⋯ Save draft stores a flip draft on the account",
              durable("SELECT COUNT(*) FROM skribl_drafts WHERE kind='flip'") == 1)

        browsing.goto(pa, BASE, "/", require_boot=False)
        pa.click("#padBtn")
        pa.wait_for_timeout(4000)
        fr = pa.frame_locator("#padFrame")
        menu_click(fr, "#openCloudDraftItem")
        fr.locator("#savedDraftsSheet .sdrafts-open").first.wait_for(timeout=5000)
        meta = fr.locator("#savedDraftsSheet .sdrafts-meta").first.inner_text()
        check("the Pad lists it, saying it opens in Flip", "opens in Flip" in meta, meta)
        fr.locator("#savedDraftsSheet .sdrafts-open").first.click()
        pa.wait_for_timeout(4500)
        flip_frame = next(f for f in pa.frames if "/skribl/flip" in f.url)
        inner = flip_frame.evaluate("""() => ({ path: location.pathname + location.search,
            pages: frames.length, name: SkriblName.get(), mode: window.SKRIBL_COMPOSE })""")
        check("one tap hands over to Flip IN THE COMPOSER, the id cleaned off the URL",
              inner["path"] == "/skribl/flip?compose=1" and inner["mode"] == "flip", str(inner))
        check("holding the saved animation and its name",
              inner["pages"] == 2 and inner["name"] == "Bounce", str(inner))
        pa.evaluate("() => document.getElementById('padFrame').contentDocument.getElementById('postBtn').click()")
        pa.wait_for_timeout(600)
        pa.evaluate("() => document.getElementById('padFrame').contentDocument"
                    ".getElementById('flipShareSubmit').click()")
        pa.wait_for_timeout(2500)
        att = pa.evaluate("""() => { var v = document.getElementById('skriblPayload').value;
            return { shown: !document.getElementById('attach').hidden,
                     frames: v ? JSON.parse(v).frames.length : 0 }; }""")
        check("Add to post attaches the two-page animation",
              att["shown"] and att["frames"] == 2, str(att))

        # ---------------------------------------------------------------- 5
        print("\n5 — SIGNED OUT: THIS BROWSER, AND IT SURVIVES A RELOAD")
        browsing.goto(anon, BASE, "/skribl/skribl-pad", require_boot=False)
        anon.wait_for_timeout(1200)
        draw(anon, anon.locator("#canvas").bounding_box())
        anon.wait_for_timeout(300)
        before = durable("SELECT COUNT(*) FROM skribl_drafts")
        menu_click(anon, "#saveCloudDraftItem")
        anon.wait_for_timeout(1200)
        after = durable("SELECT COUNT(*) FROM skribl_drafts")
        check("a signed-out save touches no table", after == before, f"{before} -> {after}")
        browsing.goto(anon, BASE, "/skribl/skribl-pad", require_boot=False)
        anon.wait_for_timeout(1200)
        menu_click(anon, "#openCloudDraftItem")
        anon.locator("#savedDraftsSheet .sdrafts-open").first.wait_for(timeout=5000)
        check("after a reload the browser draft is listed",
              anon.locator("#savedDraftsSheet .sdrafts-row").count() == 1)

        # ---------------------------------------------------------------- 6
        print("\n6 — THE LIBRARY'S DRAFTS TAB (v317)")
        n_acct = durable("SELECT COUNT(*) FROM skribl_drafts WHERE user_id='1'")
        browsing.goto(pa, BASE, "/skribl/library", require_boot=False)
        pa.wait_for_timeout(1200)
        check("the Library opens on Skribls", pa.evaluate(
            "() => document.getElementById('tabSkribls').getAttribute('aria-selected') === 'true'"
            " && document.getElementById('libDrafts').hidden"))
        pa.focus("#tabSkribls")
        pa.keyboard.press("ArrowRight")
        pa.wait_for_timeout(1200)
        st6 = pa.evaluate("""() => ({ sel: document.getElementById('tabDrafts').getAttribute('aria-selected'),
            focus: document.activeElement && document.activeElement.id, hash: location.hash,
            chips: getComputedStyle(document.querySelector('.chips')).display,
            where: document.getElementById('draftsWhere').textContent })""")
        check("ArrowRight moves to Drafts, with focus, and #drafts in the address",
              st6["sel"] == "true" and st6["focus"] == "tabDrafts" and st6["hash"] == "#drafts", str(st6))
        check("the Skribls tab's filter steps aside", st6["chips"] == "none", st6["chips"])
        rows = pa.locator("#draftsList .draft-row")
        check("signed in, it lists the ACCOUNT's drafts, and says so",
              rows.count() == n_acct and "account" in st6["where"], f"{rows.count()} rows vs {n_acct}; {st6['where']!r}")
        hrefs = pa.locator("#draftsList .draft-open").evaluate_all("els => els.map(e => e.getAttribute('href'))")
        names = pa.locator("#draftsList .draft-name").all_inner_texts()
        check("each Open goes to the editor that made it, carrying the id",
              any(h.startswith("/skribl/flip?draft=") for h in hrefs)
              and any(h.startswith("/skribl/skribl-pad?draft=") for h in hrefs), str(hrefs))
        # Delete asks first.
        victim = names[-1]
        pa.locator("#draftsList .draft-del").last.click()
        pa.wait_for_timeout(600)
        # The bin asks WITHOUT MOVING since the gallery/library pass: it keeps
        # its box and the row's meta line asks (verify_galib pins the box).
        check("Delete asks first, on the row, and deletes nothing yet",
              pa.locator("#draftsList .draft-del").last.evaluate("d => d.classList.contains('armed')")
              and "again" in pa.locator("#draftsList .draft-row").last.locator(".draft-meta").inner_text()
              and durable("SELECT COUNT(*) FROM skribl_drafts WHERE user_id='1'") == n_acct)
        pa.locator("#draftsList .draft-del").last.click()
        pa.wait_for_timeout(1500)
        check("the second tap deletes it from the account",
              durable("SELECT COUNT(*) FROM skribl_drafts WHERE user_id='1'") == n_acct - 1
              and victim not in pa.locator("#draftsList .draft-name").all_inner_texts(),
              f"{victim!r} {pa.locator('#draftsList .draft-name').all_inner_texts()}")
        # Open a Pad draft over a Pad that already holds work (section 1 drew
        # on it): the editor asks, it does not replace.
        pad_link = pa.locator("#draftsList .draft-row", has_text="Composer wave").locator(".draft-open")
        pad_link.click()
        pa.wait_for_timeout(3500)
        before = canon(pa.evaluate("() => " + PRINT + "(serializeSkribl())"))
        ask = pa.evaluate("""() => { var s = document.getElementById('savedDraftsSheet');
            var m = s && s.querySelector('.sdrafts-row.armed .sdrafts-meta');
            return { open: !!s && !s.hidden, meta: m ? m.textContent : null, url: location.pathname + location.search }; }""")
        check("opened over work on the canvas, the Pad ASKS instead of replacing it",
              ask["open"] and ask["meta"] and "replaces" in ask["meta"] and before != saved_print,
              f"{ask}; canvas {'is' if before == saved_print else 'is not'} the draft")
        check("and the id is off the address", ask["url"] == "/skribl/skribl-pad", ask["url"])
        pa.locator("#savedDraftsSheet .sdrafts-row.armed .sdrafts-open").click()
        pa.wait_for_timeout(1500)
        check("the second tap opens the draft, with its name",
              canon(pa.evaluate("() => " + PRINT + "(serializeSkribl())")) == saved_print
              and pa.evaluate("() => SkriblName.get()") == "Composer wave",
              _diff_detail(canon(pa.evaluate("() => " + PRINT + "(serializeSkribl())")), saved_print,
                           pa.evaluate("() => SkriblName.get()")))
        # Signed out: this browser's list.
        browsing.goto(anon, BASE, "/skribl/library#drafts", require_boot=False)
        anon.wait_for_timeout(1500)
        aw = anon.evaluate("() => document.getElementById('draftsWhere').textContent")
        check("signed out, #drafts lists THIS BROWSER's drafts, and says so",
              anon.locator("#draftsList .draft-row").count() == 1 and "browser" in aw,
              f"{anon.locator('#draftsList .draft-row').count()} rows; {aw!r}")

        # ---------------------------------------------------------------- 7
        print("\n7 — WHEN THIS BROWSER'S STORAGE STOPS ANSWERING (v317)")
        # The owner's iPhone: "Loading… and nothing comes". IndexedDB that never
        # fires an event is simulated at the source: open() hands back a
        # request that never answers. The sheet must say so and offer a retry.
        hung = b.new_context()
        hung.add_init_script("""(() => {
          const real = indexedDB.open.bind(indexedDB);
          window.__hangIDB = true;
          indexedDB.open = function (name, v) {
            if (!window.__hangIDB) return real(name, v);
            return {};                     // a request whose events never fire
          };
        })();""")
        ph = watch(hung.new_page(), "hung")
        browsing.goto(ph, BASE, "/skribl/skribl-pad", require_boot=False)
        ph.wait_for_timeout(800)
        menu_click(ph, "#openCloudDraftItem")
        ph.wait_for_timeout(6000)
        sheet = ph.evaluate("""() => { const l = document.querySelector('#savedDraftsSheet .sdrafts-list');
            return { text: l ? l.textContent : null, stalled: !!document.querySelector('#savedDraftsSheet .sdrafts-stalled') }; }""")
        check("storage that never answers: the sheet says so within seconds, not 'Loading…' for good",
              sheet["text"] and "Loading" not in sheet["text"] and sheet["stalled"] and "slow to answer" in sheet["text"],
              repr(sheet["text"]))
        # THE SHELF (the owner's iPhone, after v317: "I saved a draft and
        # nothing"). With IndexedDB hung, Save draft used to fail with the
        # sheet's error; a saved draft is plain JSON, so it is kept in
        # localStorage and moves into IndexedDB when it answers.
        ph.evaluate("() => { SkriblSavedDrafts.close(); }")
        draw(ph, ph.locator("#canvas").bounding_box())
        ph.evaluate("() => { SkriblSavedDrafts.forget(); SkriblName.set('Kept while hung'); }")
        kept = ph.evaluate("async () => { try { const s = await SkriblSavedDrafts.save(); return s ? s.id : null; } catch (e) { return null; } }")
        ph.wait_for_timeout(300)
        listed = ph.evaluate("async () => { try { return (await SkriblSavedDrafts.list()).map(i => i.title); } catch (e) { return ['ERR ' + e.message]; } }")
        check("with storage hung, Save draft still saves, and the draft is listed",
              bool(kept) and "Kept while hung" in listed, f"id={kept} list={listed}")
        if not kept:     # nothing further can be asked of a store that kept nothing
            hung.close(); raise SystemExit(f"{len(results) - len([r for r in results if r[0]])} failure(s): the shelf kept nothing")
        ph.evaluate("() => { SkriblSavedDrafts.forget(); SkriblName.set('Deleted while hung'); }")
        doomed = ph.evaluate("async () => { const s = await SkriblSavedDrafts.save(); await SkriblSavedDrafts.remove(s.id); return s.id; }")
        report = ph.evaluate("() => SkriblDraftStore.state()")
        check("...and 'Report a problem' can say the store is not answering",
              "NOT answering" in report and "no answer" in report, report)
        ph.evaluate("() => { window.__hangIDB = false; }")
        ph.wait_for_timeout(300)
        # The next probe is at most PROBE_MS away; poll until the store answers.
        after = ph.evaluate("""async () => { let titles = [];
            for (let i = 0; i < 20; i++) {
              titles = (await SkriblSavedDrafts.list()).map(i => i.title);
              if (!SkriblDraftStore.degraded()) break;
              await new Promise(r => setTimeout(r, 1000));
            }
            await new Promise(r => setTimeout(r, 1500));
            const shelf = Object.keys(localStorage).filter(k => k.startsWith('skribl-shelf'));
            const rec = await SkriblDraftStore.get('saved:' + arguments[0]);
            return { titles, shelf, rec: rec ? rec.title : null, stalled: SkriblDraftStore.degraded() }; }""".replace("arguments[0]", repr(kept)))
        check("when the storage answers, the draft moves into it and the shelf empties",
              "Kept while hung" in after["titles"] and after["rec"] == "Kept while hung" and not after["shelf"]
              and after["stalled"] is False, str(after))
        again = ph.evaluate("async () => (await SkriblSavedDrafts.list()).map(i => i.title)")
        check("...and a draft deleted while it was hung stays deleted",
              "Deleted while hung" not in again and "Kept while hung" in again, str(again))
        ph.evaluate(f"async () => {{ await SkriblSavedDrafts.remove({kept!r}); }}")
        hung.close()
        # A connection closed under the page (what WebKit does while it is in
        # the background): the next read gets one fresh connection, not an error.
        pd = watch(b.new_context().new_page(), "closed-db")
        browsing.goto(pd, BASE, "/skribl/skribl-pad", require_boot=False)
        pd.wait_for_timeout(800)
        dead = pd.evaluate("""async () => {
          await SkriblDraftStore.put('probe:x', {v: 7});
          const T = IDBDatabase.prototype.transaction; let thrown = 0;
          IDBDatabase.prototype.transaction = function () {
            if (!thrown++) throw new DOMException('The database connection is closing.', 'InvalidStateError');
            return T.apply(this, arguments);
          };
          try { const r = await SkriblDraftStore.get('probe:x'); return { v: r && r.v, thrown }; }
          catch (e) { return { err: String(e), thrown }; }
          finally { IDBDatabase.prototype.transaction = T; }
        }""")
        check("a connection that died in the background: the read succeeds on a fresh one",
              dead.get("v") == 7 and dead.get("thrown") == 2, str(dead))
        # ONE KEY, ONE QUEUE (third review): put() reads a Blob's bytes before
        # it opens its transaction, so a del() issued after it went in first and
        # the put wrote back what had just been removed. An 8 MB Blob makes the
        # read long enough to overtake every run; a put issued after the del
        # proves the queue does not simply drop writes.
        order = pd.evaluate("""async () => {
          const blob = new Blob([new Uint8Array(8e6)], { type: 'image/jpeg' });
          await Promise.all([SkriblDraftStore.put('probe:o', { blob, name: 'removed.jpg' }), SkriblDraftStore.del('probe:o')]);
          const afterDel = await SkriblDraftStore.get('probe:o');
          await Promise.all([SkriblDraftStore.del('probe:o'), SkriblDraftStore.put('probe:o', { blob, name: 'kept.jpg' })]);
          const afterPut = await SkriblDraftStore.get('probe:o');
          await SkriblDraftStore.del('probe:o');
          return { afterDel: afterDel ? afterDel.name : null, afterPut: afterPut ? afterPut.name : null }; }""")
        check("the store keeps each key's writes in the order they were asked for (a delete after a put stays deleted)",
              order == {"afterDel": None, "afterPut": "kept.jpg"}, str(order))
        # THE OWNER'S "they were there, then they disappeared". A read of the
        # index that failed used to answer [] and the next save wrote an index
        # holding only itself. Two drafts, then a save while the index read
        # fails: the save must refuse, and both drafts must still be listed.
        draw(pd, pd.locator("#canvas").bounding_box())
        pd.evaluate("() => SkriblName.set('Keep me one')")
        pd.evaluate("() => SkriblSavedDrafts.save()")
        pd.wait_for_timeout(600)
        pd.evaluate("() => { SkriblSavedDrafts.forget(); SkriblName.set('Keep me two'); }")
        pd.evaluate("() => SkriblSavedDrafts.save()")
        pd.wait_for_timeout(600)
        lost_try = pd.evaluate("""async () => {
          const G = SkriblDraftStore.get; let failed = 0;
          SkriblDraftStore.get = function (k) {
            if (k === 'saved:index' && !failed++) return Promise.reject(new Error("This browser's storage did not answer."));
            return G.apply(this, arguments);
          };
          SkriblSavedDrafts.forget(); SkriblName.set('Would overwrite');
          await SkriblSavedDrafts.save();
          SkriblDraftStore.get = G;
          const idx = await SkriblDraftStore.get('saved:index');
          return { failed, names: (idx && idx.items || []).map(i => i.title) };
        }""")
        check("a save whose index read FAILS writes nothing over the list",
              lost_try["failed"] == 1 and sorted(lost_try["names"]) == ["Keep me one", "Keep me two"],
              str(lost_try))
        # And the way back for drafts an older build already dropped from the
        # index: the record is still there, so the list finds it.
        back = pd.evaluate("""async () => {
          const pay = serializeSkribl();
          await SkriblDraftStore.put('saved:lost1', { id: 'lost1', kind: 'pad', title: 'Found again', payload: pay });
          const items = await SkriblSavedDrafts.list();
          const idx = await SkriblDraftStore.get('saved:index');
          return { listed: items.map(i => i.title), indexed: (idx.items || []).map(i => i.title) };
        }""")
        # BYTES, NOT BLOBS (v317): what lands in IndexedDB is an ArrayBuffer,
        # read straight from the database; what comes back is the same file.
        stored = pd.evaluate("""async () => {
          await SkriblDraftStore.put('probe:blob', { blob: new Blob(['hello bytes'], { type: 'text/plain' }), name: 'a.txt' });
          const raw = await new Promise((res, rej) => { const q = indexedDB.open('skribl-drafts');
            q.onsuccess = () => { const g = q.result.transaction('media').objectStore('media').get('probe:blob');
              g.onsuccess = () => { res(g.result); q.result.close(); }; g.onerror = () => rej(g.error); }; q.onerror = () => rej(q.error); });
          const back = await SkriblDraftStore.get('probe:blob');
          return { rawIsBlob: raw.blob instanceof Blob, rawBytes: raw.blob && raw.blob.__skriblBytes instanceof ArrayBuffer,
                   backIsBlob: back.blob instanceof Blob, text: await back.blob.text(), type: back.blob.type, name: back.name };
        }""")
        check("media goes into IndexedDB as bytes, not a Blob (WebKit's weak spot)",
              stored["rawIsBlob"] is False and stored["rawBytes"] is True, str(stored))
        check("...and comes back out as the same file, type and all",
              stored["backIsBlob"] is True and stored["text"] == "hello bytes" and stored["type"] == "text/plain"
              and stored["name"] == "a.txt", str(stored))
        # A REFUSED WRITE IS AN ANSWER, NOT A DEAD CONNECTION (v317 review). Every
        # failure used to drop the connection, unclosed, and open a fresh one.
        kept = pd.evaluate("""async () => {
          const real = indexedDB.open.bind(indexedDB); let opens = 0;
          indexedDB.open = (...a) => { opens++; return real(...a); };
          await SkriblDraftStore.get('saved:index');           // connection up
          let refused = null;
          try { await SkriblDraftStore.put('probe:fn', { f: () => 1 }); } catch (e) { refused = e.name; }
          await SkriblDraftStore.get('saved:index');
          indexedDB.open = real;
          return { refused, opens };
        }""")
        check("a write the browser refuses keeps the working connection (no fresh open per failure)",
              kept["refused"] == "DataCloneError" and kept["opens"] == 0, str(kept))
        check("a draft its index lost is listed again, and written back into the index",
              "Found again" in back["listed"] and "Found again" in back["indexed"]
              and "Keep me one" in back["listed"], str(back))
        # A DELETE THAT STOPS HALF-WAY (v317 review): the record goes first, the
        # row second. With the row first, recover() re-listed the record when
        # the second step failed and the deleted draft came back; with the
        # record first, the stale row is dropped rather than left to answer
        # "Draft not found".
        halfway = pd.evaluate("""async () => {
          const S = SkriblDraftStore, put = S.put;
          S.put = (k, v) => k === 'saved:index' ? Promise.reject(new Error('refused')) : put(k, v);
          let failed = false;
          try { await SkriblSavedDrafts.remove('lost1'); } catch (e) { failed = true; }
          S.put = put;
          const items = await SkriblSavedDrafts.list();
          return { failed, listed: items.map(i => i.title) };
        }""")
        check("a delete that stops half-way says so, and the draft neither comes back nor lingers as a dead row",
              halfway["failed"] is True and "Found again" not in halfway["listed"]
              and "Keep me one" in halfway["listed"], str(halfway))

        # ONE ROW ASKS AT A TIME (v317): the owner's sheet showed two rows both
        # saying "Tap again". pd's canvas has ink, so the first tap on a row asks.
        menu_click(pd, "#openCloudDraftItem")
        pd.locator("#savedDraftsSheet .sdrafts-open").nth(1).wait_for(timeout=5000)
        pd.locator("#savedDraftsSheet .sdrafts-open").nth(0).click()
        pd.wait_for_timeout(200)
        pd.locator("#savedDraftsSheet .sdrafts-open").nth(1).click()
        pd.wait_for_timeout(200)
        armed = pd.evaluate("() => [...document.querySelectorAll('#savedDraftsSheet .sdrafts-row')].map(r => r.classList.contains('armed'))")
        check("the sheet: arming a second row puts the first one back", armed[:2] == [False, True], str(armed))
        pd.locator("#savedDraftsSheet .sdrafts-del").nth(0).click()
        pd.wait_for_timeout(200)
        armed2 = pd.evaluate("""() => [...document.querySelectorAll('#savedDraftsSheet .sdrafts-row')].map(r =>
            r.classList.contains('armed') || r.querySelector('.sdrafts-del').classList.contains('armed'))""")
        check("...and asking to delete one row puts back the row that asked to open",
              armed2[:2] == [True, False], str(armed2))
        lab = pd.evaluate("""() => { const d = document.querySelectorAll('#savedDraftsSheet .sdrafts-del');
            return [d[0].getAttribute('aria-label'), d[1].getAttribute('aria-label'),
                    document.querySelector('#savedDraftsSheet .sdrafts-meta').getAttribute('aria-live')]; }""")
        check("the asking bin's name says what the next tap does, the others' do not, and the row's question is spoken",
              lab[0].startswith("Tap again to delete") and lab[1].startswith("Delete ") and lab[2] == "polite", str(lab))
        # A KEYBOARD DELETE KEEPS FOCUS IN THE DIALOG (third review). The list
        # is rebuilt and the focused bin goes with it: focus fell to <body>,
        # outside the modal, where Tab left the sheet and Escape did nothing.
        pd.evaluate("() => { SkriblSavedDrafts.close(); SkriblSavedDrafts.forget(); SkriblName.set('Delete me by keyboard'); }")
        pd.evaluate("() => SkriblSavedDrafts.save()"); pd.wait_for_timeout(600)
        pd.evaluate("() => SkriblSavedDrafts.open()"); pd.wait_for_timeout(900)
        kb_row = pd.evaluate("""() => [...document.querySelectorAll('#savedDraftsSheet .sdrafts-row')]
            .findIndex(r => r.textContent.includes('Delete me by keyboard'))""")
        pd.locator("#savedDraftsSheet .sdrafts-del").nth(kb_row).focus()
        pd.keyboard.press("Enter"); pd.wait_for_timeout(150); pd.keyboard.press("Enter"); pd.wait_for_timeout(900)
        kb = pd.evaluate("""() => { const a = document.activeElement, s = document.getElementById('savedDraftsSheet');
            return { inSheet: s.contains(a), what: a.className, gone: !s.textContent.includes('Delete me by keyboard') }; }""")
        pd.keyboard.press("Escape"); pd.wait_for_timeout(500)
        kb["escClosed"] = pd.evaluate("() => document.getElementById('savedDraftsSheet').hidden")
        check("the sheet: a draft deleted from the keyboard leaves focus in the sheet, where Escape still closes it",
              kb_row >= 0 and kb["gone"] and kb["inSheet"] and kb["what"] in ("sdrafts-open", "sdrafts-close") and kb["escClosed"],
              f"row {kb_row}: {kb}")
        # A draft deleted elsewhere (the Library) and saved again here is a NEW
        # draft, and the toast says so instead of "Draft updated" (third review).
        vanish = pd.evaluate("""async () => { SkriblSavedDrafts.forget(); SkriblName.set('Vanishing');
            const a = await SkriblSavedDrafts.save(); await SkriblSavedDrafts.remove(a.id);
            const b = await SkriblSavedDrafts.save(); await new Promise(r => setTimeout(r, 100));
            const t = [...document.querySelectorAll('.toast, #toast, .skribl-toast')].map(e => e.textContent).join(' | ');
            await SkriblSavedDrafts.remove(b.id); SkriblSavedDrafts.forget();
            return { same: a.id === b.id, toast: t }; }""")
        check("a save after its draft was deleted elsewhere says it saved a new draft, not 'Draft updated'",
              not vanish["same"] and "updated" not in vanish["toast"] and "Saved" in vanish["toast"], str(vanish))
        pd.evaluate("() => { SkriblSavedDrafts.forget(); SkriblName.set('Delete me in the library'); }")
        pd.evaluate("() => SkriblSavedDrafts.save()"); pd.wait_for_timeout(600)
        # The Library draws the same row: the card opens, the bin asks, one at a time.
        browsing.goto(pd, BASE, "/skribl/library#drafts", require_boot=False)
        pd.wait_for_timeout(1500)
        lib = pd.evaluate("""() => { const rows = [...document.querySelectorAll('#draftsList .draft-row')];
            return { n: rows.length, links: rows.every(r => r.querySelector('a.draft-open[href*="?draft="]')),
                     pills: document.querySelectorAll('#draftsList .draft-acts').length }; }""")
        check("the Library's rows are the card itself as the link, no pill buttons",
              lib["n"] >= 2 and lib["links"] and lib["pills"] == 0, str(lib))
        pd.locator("#draftsList .draft-del").nth(0).click()
        pd.wait_for_timeout(150)
        pd.locator("#draftsList .draft-del").nth(1).click()
        pd.wait_for_timeout(150)
        larmed = pd.evaluate("() => [...document.querySelectorAll('#draftsList .draft-del')].map(d => d.classList.contains('armed'))")
        check("the Library: one bin asks at a time", larmed[:2] == [False, True], str(larmed))
        llab = pd.evaluate("""() => [...document.querySelectorAll('#draftsList .draft-del')].slice(0, 2).map(d => d.getAttribute('aria-label'))""")
        check("the Library: the asking bin's name says so too", llab[0].startswith("Delete ") and llab[1].startswith("Tap again to delete"), str(llab))
        lk_row = pd.evaluate("""() => [...document.querySelectorAll('#draftsList .draft-row')]
            .findIndex(r => r.textContent.includes('Delete me in the library'))""")
        pd.locator("#draftsList .draft-del").nth(lk_row).focus()
        pd.keyboard.press("Enter"); pd.wait_for_timeout(150); pd.keyboard.press("Enter"); pd.wait_for_timeout(1000)
        lk = pd.evaluate("""() => { const a = document.activeElement;
            return { tag: a.tagName, cls: a.className, id: a.id,
                     gone: !document.getElementById('draftsList').textContent.includes('Delete me in the library') }; }""")
        check("the Library: a draft deleted from the keyboard hands focus to the next row, not the page",
              lk_row >= 0 and lk["gone"] and (lk["cls"] == "draft-open" or lk["id"] == "tabDrafts"), f"row {lk_row}: {lk}")
        head = pd.evaluate("""() => { const h = document.querySelector('h2.libtabs');
            return { role: h.getAttribute('role'), tabs: h.querySelectorAll('[role=tablist] [role=tab]').length }; }""")
        check("the Library's tab heading is still a heading, with its tabs inside it",
              head["role"] is None and head["tabs"] == 2, str(head))
        # A Pad holding only a photo is work: opening a draft over it asks first.
        pp = watch(pd.context.new_page(), "photo")   # the same browser, so the same drafts
        browsing.goto(pp, BASE, "/skribl/skribl-pad", require_boot=False); pp.wait_for_timeout(1200)
        pp.evaluate("() => { window.SkriblHints && window.SkriblHints.hide(); }")
        # The same browser restores pd's drawing here; start from nothing but a photo.
        pp.evaluate("() => { clearAllWithUndo(); }"); pp.wait_for_timeout(300)
        _fd, _name = tempfile.mkstemp(suffix=".png", prefix="clouddrafts_")
        os.close(_fd)
        _png = pathlib.Path(_name)
        _png.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
        pp.set_input_files("#photoInput", str(_png)); pp.wait_for_timeout(1500)
        _png.unlink(missing_ok=True)
        menu_click(pp, "#openCloudDraftItem")
        pp.locator("#savedDraftsSheet .sdrafts-open").nth(0).wait_for(timeout=5000)
        pp.locator("#savedDraftsSheet .sdrafts-open").nth(0).click(); pp.wait_for_timeout(200)
        asked = pp.evaluate("""() => ({ armed: document.querySelector('#savedDraftsSheet .sdrafts-row').classList.contains('armed'),
            strokes: strokes.length, ink: !!hasContent, photo: !!(photoBgImg && photoBgImg._fileName) })""")
        check("a Pad holding only a photo asks before a draft replaces it",
              asked["armed"] is True and asked["strokes"] == 0 and not asked["ink"] and asked["photo"], str(asked))
        # ...and so does one whose photo is still on its way (pending, restoring):
        # the draft must not replace the autosave mid-restore.
        pp.evaluate("""() => { SkriblSavedDrafts.close && SkriblSavedDrafts.close(); resetAll();
            pendingPhotoMeta = { name: 'coming.png' }; _restoring.photo = true; }""")
        pp.wait_for_timeout(400)
        menu_click(pp, "#openCloudDraftItem")
        pp.locator("#savedDraftsSheet .sdrafts-open").nth(0).wait_for(timeout=5000)
        pp.wait_for_timeout(300)
        pp.locator("#savedDraftsSheet .sdrafts-open").nth(0).click(); pp.wait_for_timeout(200)
        asked2 = pp.evaluate("""() => ({ armed: document.querySelector('#savedDraftsSheet .sdrafts-row').classList.contains('armed'),
            strokes: strokes.length })""")
        check("a Pad whose photo is still being restored asks too", asked2["armed"] is True and asked2["strokes"] == 0, str(asked2))
        pp.close()

        check("no page errors", not errs, "; ".join(errs[:3]))
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
