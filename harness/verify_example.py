"""The worked host app in examples/, driven end to end.

WHY A SUITE FOR AN EXAMPLE. Every other document here DESCRIBES the drop-in.
examples/host_app IS the drop-in, and an example nothing runs is a document
that goes stale silently — the exact failure this tree has been bitten by
repeatedly (a /library page drawing its own content, a README warning about it,
counts typed into prose). So the example is booted as a REAL SERVER on its own
port, with its own database, and a real browser draws a real Skribl in it.

WHAT IT PROVES THAT NOTHING ELSE DOES. Every other browser suite drives the
STANDALONE app, where Skribl is the whole site and mounted at the root. This
one drives a separate application that:

  * mounts the blueprint under a PREFIX (/skribl), which is what catches route
    literals in client JS and relative endpoint names in templates;
  * has its OWN users and posts, and renders the player inside its own post;
  * composes with a SERVER-SIDE FORM and skribl.create_post(), never touching
    POST /api/skribls from the browser at all.

THE ASSERTION THAT MATTERS MOST is the last one in section 4: the host's post
row and the Skribl are made durable by ONE commit, checked on a fresh
connection. That is the property the whole server-side path exists for, and it
is the one that silently would not hold if create_post ever committed on its
own.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "host_app"

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the example works.")
    raise SystemExit(77)

import sqlalchemy as sa
from assertions import make_check
import browsing

results = []


check = make_check(results)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()
BASE = f"http://127.0.0.1:{PORT}"
_tmp = tempfile.mkdtemp()
DB = f"{_tmp}/example.db"
DB_URL = f"sqlite:///{DB}"

env = dict(os.environ,
           EXAMPLE_DATABASE_URL=DB_URL,
           EXAMPLE_SECRET="harness-example-suite",
           # The example is a demonstration, not a load test; the default post
           # budget would stop the suite's own posting.
           SKRIBL_RATE_MAX_POSTS="100000",
           PYTHONPATH=str(ROOT))

# Seed in a separate process, exactly as a host's own CLI would.
subprocess.run(
    [sys.executable, "-c",
     "import app as ex; a = ex.create_app();"
     " ctx = a.app_context(); ctx.push(); ex.db.create_all();"
     " ex.db.session.add_all([ex.User(handle='ada'), ex.User(handle='grace')]);"
     " ex.db.session.commit()"],
    cwd=str(EXAMPLE), env=env, check=True, capture_output=True)

proc = subprocess.Popen(
    [sys.executable, "-m", "flask", "--app", "app", "run",
     "--port", str(PORT), "--no-reload"],
    cwd=str(EXAMPLE), env=env,
    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


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
    """A FRESH connection: only committed state is visible."""
    eng = sa.create_engine(DB_URL)
    try:
        with eng.connect() as c:
            return c.execute(sa.text(query)).scalar()
    finally:
        eng.dispose()


def draw(pg, box, turns=4, n=70):
    """A real recording over real wall clock — see verify_inline.py's note."""
    import math
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(n):
        t = i / float(n - 1)
        a = t * turns * 2 * math.pi
        r = 10 + t * min(box["width"], box["height"]) * 0.33
        pg.mouse.move(cx + math.cos(a) * r, cy + math.sin(a) * r)
        pg.wait_for_timeout(12)
    pg.mouse.up()


try:
    if not wait_ready():
        err = proc.stderr.read().decode("utf-8", "replace")[-1500:] if proc.stderr else ""
        sys.exit(f"SKIP: the example app did not start on port {PORT}.\n{err}")

    print("\n1 — IT RUNS, AND IT IS NOT THE STANDALONE APP")
    with urllib.request.urlopen(BASE + "/", timeout=15) as r:
        home = r.read().decode("utf-8")
        code = r.status
    check("the example host serves its own feed", code == 200, str(code))
    check("it is the HOST's page, not Skribl's", "Example host" in home)
    # Mounted under /skribl. If any client script or template had a root
    # literal in it, the page below would reference a path that does not exist.
    check("the blueprint is mounted under a PREFIX",
          "/skribl/" in home,
          f"{home.count('/skribl/')} /skribl/ URLs on the page")
    check("the in-post player's assets are on the page",
          "inlineplayer.css" in home and "inlineplayer.js" in home)
    check("the compose lifecycle module is too",
          "composehost.js" in home)
    # The macro writes the API endpoint in; a root literal here is the bug
    # verify_seam.py caught in inlineplayer.js.
    check("no root-level /api/skribls literal reached the page",
          '"/api/skribls' not in home and "'/api/skribls" not in home)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1180, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        # Every request the browser makes to Skribl's create endpoint. The
        # server-side path must make NONE.
        api_posts = []
        pg.on("request", lambda r: api_posts.append(r.url)
              if r.method == "POST" and "/api/skribls" in r.url else None)

        # require_boot=False, case 1: BASE is the EXAMPLE HOST APP, not Skribl.
        # Its "/" is the host's own page and raises no __skriblBoot marker,
        # so requiring one would spend the timeout and then fail a page that
        # is behaving correctly.
        browsing.goto(pg, BASE, "/", require_boot=False)

        print("\n2 — SIGN IN, AND THE COMPOSER APPEARS")
        check("signed out, there is no composer",
              pg.locator("#composer").count() == 0)
        pg.select_option("select[name=uid]", index=0)
        pg.click("button:has-text('Sign in')")
        pg.wait_for_timeout(800)
        check("signed in, the host's composer is there",
              pg.locator("#composer").count() == 1)
        check("with a pad button beside its own controls",
              pg.locator("#padBtn").count() == 1)
        check("and nothing can be posted yet",
              pg.evaluate("() => document.getElementById('postBtn').disabled") is True)
        src_before = pg.evaluate(
            "() => document.getElementById('padFrame').getAttribute('src')")
        check("the editor is NOT loaded until the pad button is pressed",
              not src_before or src_before in ("", "about:blank"),
              f"src was {src_before!r}")

        print("\n3 — DRAW ONE, IN THE HOST'S OWN COMPOSER")
        pg.click("#padBtn")
        # WAIT FOR THE PAD TO BOOT, not for a guess at how long booting takes
        # (browsing.py, WHY): its app.js says so on its last line, read here
        # in the frame's own window. A fixed five seconds drew before it was
        # there. The Pad's 119 files take about five seconds from the
        # example's development server, so the stroke fell on a canvas not
        # yet made (its default 300 x 150), no take began, and the record
        # button, shown only while a take is under way, never came: main red
        # after #763 and #764, the click timing out at 30 s; here every time,
        # at the last commit main ran green as well.
        pg.wait_for_function(
            "() => { const f = document.getElementById('padFrame');"
            " const w = f && f.contentWindow;"
            " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }",
            timeout=30000)
        # Booted is not laid out (browsing.py, A SMALL SETTLE).
        pg.wait_for_timeout(800)
        mode = pg.evaluate(
            "() => document.getElementById('padFrame').contentWindow.SKRIBL_MODE")
        check("the pad opens in compose mode, under the prefix",
              mode == "compose", f"SKRIBL_MODE={mode!r}")
        fr = pg.frame_locator("#padFrame")
        draw(pg, fr.locator("#canvas").bounding_box())
        pg.wait_for_timeout(400)
        fr.locator("#recordBtn").click()
        pg.wait_for_timeout(700)
        fr.locator("#postBtn").click()
        pg.wait_for_timeout(1200)
        # THE SHEET ASKS WHAT THIS HOST ASKED FOR (feed.html opens the editor
        # with gallery=1): the gallery tick, off; no title of its own, as the
        # post's words are its title; and where a viewer starts. Read off the
        # elements, laid out or not, never off the words.
        sheet = pg.evaluate("""() => { const d = document.getElementById('padFrame').contentDocument;
            const shown = id => { const e = d.getElementById(id); return !!(e && e.getClientRects().length); };
            const box = d.getElementById('postPublicInput');
            return { box: !!box, ticked: box ? box.checked : null, title: shown('postTitleInput'),
                     caption: shown('postCaptionInput'), speed: shown('postSpeedSeg') }; }""")
        check("the sheet asks: the gallery tick is there, and off", sheet["box"] and sheet["ticked"] is False,
              json.dumps(sheet))
        check("...no title field shows (the post's words are its title), nor the gallery caption while the tick is off",
              not sheet["title"] and not sheet["caption"], json.dumps(sheet))
        check("...and where a viewer starts does", sheet["speed"], json.dumps(sheet))
        fr.locator("#postSubmitBtn").click()
        pg.wait_for_timeout(4000)

        check("the overlay closed and the draft is attached",
              pg.evaluate("() => !document.getElementById('attach').hidden") is True)
        payload_len = pg.evaluate(
            "() => document.getElementById('skriblPayload').value.length")
        check("the payload is in the form's hidden field, ready to submit",
              payload_len > 500, f"{payload_len} chars")
        check("attaching published NOTHING", not api_posts,
              f"{len(api_posts)} POST(s) to the API: {api_posts}")
        check("nothing is durable in Skribl's table yet",
              durable("SELECT COUNT(*) FROM skribl_posts") == 0,
              f"{durable('SELECT COUNT(*) FROM skribl_posts')} row(s)")
        # The draft renders through the REAL player, on a payload with no id.
        st = pg.evaluate("""() => { var ps = window.SkriblInline.players();
            var p = ps && ps[0]; return p ? p.state() : null; }""")
        check("the draft previews through the real in-post player, not a thumbnail",
              st and st.get("id") is None and st.get("loaded") is True,
              json.dumps(st))

        print("\n4 — POST IT: ONE FORM SUBMIT, ONE TRANSACTION")
        pg.fill("#body", "drew this in a host composer")
        pg.click("#postBtn")
        pg.wait_for_url(BASE + "/", timeout=20000)
        pg.wait_for_timeout(2500)

        check("the browser NEVER posted to Skribl's API — the server did it",
              not api_posts,
              f"{len(api_posts)} POST(s): {api_posts}")
        n_posts = durable("SELECT COUNT(*) FROM host_posts")
        n_skribls = durable("SELECT COUNT(*) FROM skribl_posts")
        check("the host has exactly one post", n_posts == 1, str(n_posts))
        check("and Skribl has exactly one skribl", n_skribls == 1, str(n_skribls))
        # THE ASSERTION THIS SUITE EXISTS FOR.
        joined = durable(
            "SELECT COUNT(*) FROM host_posts h JOIN skribl_posts s "
            "ON h.skribl_id = s.public_id")
        check("ONE COMMIT made both durable, and the host's row points at it",
              joined == 1,
              f"{joined} joined row(s) — if this is 0 the two landed in "
              f"different transactions")
        # str() BOTH SIDES: skribl_posts.user_id is text since v279 while the
        # host's own author_id column is whatever the host chose — here an
        # integer. That the two agree AS IDENTITIES is the assertion; that they
        # share a SQL type never was, and requiring it would force every host
        # to store ids the way Skribl does.
        check("the author stamp on the Skribl is the host's user",
              str(durable("SELECT user_id FROM skribl_posts LIMIT 1")) ==
              str(durable("SELECT author_id FROM host_posts LIMIT 1")))
        # The tick was left off: in this post only. The host dropped the key
        # and the API's default stood, reachable by its link, listed nowhere.
        check("left off, the drawing is in the post only: unlisted, not in the gallery",
              durable("SELECT visibility FROM skribl_posts LIMIT 1") == "unlisted",
              str(durable("SELECT visibility FROM skribl_posts LIMIT 1")))
        # The post's words are its title; the caption is only what the author
        # wrote under the gallery tick (the owner, Nov 10: "say the post's
        # words once"). Copied in, a gallery card said them twice.
        check("the words became the title, and no caption was made up from them",
              durable("SELECT title FROM skribl_posts LIMIT 1") == "drew this in a host composer"
              and durable("SELECT caption FROM skribl_posts LIMIT 1") in (None, ""),
              "title %r, caption %r" % (durable("SELECT title FROM skribl_posts LIMIT 1"),
                                        durable("SELECT caption FROM skribl_posts LIMIT 1")))

        print("\n5 — AND IT PLAYS, INSIDE THE HOST'S POST")
        check("the post is on the host's feed",
              pg.locator("article.post").count() == 1)
        check("with a Skribl in it", pg.locator("[data-skribl-inline]").count() == 1)
        # IN ITS DRAWING'S SHAPE, WITH ITS NUMBERS (INTEGRATION.md): the host
        # passes canvas_w, canvas_h and line_info from the Skribl's own row.
        # With the id alone a 4:3 or tall drawing sat in the 16:9 box with the
        # share card's ground at its sides (the owner's phone, after #786).
        _dw = durable("SELECT canvas_w FROM skribl_posts LIMIT 1")
        _dh = durable("SELECT canvas_h FROM skribl_posts LIMIT 1")
        _hb = pg.evaluate("""() => { const b = document.querySelector('article.post [data-skribl-inline]');
            const r = b.getBoundingClientRect(); let line = null;
            try { line = JSON.parse(b.getAttribute('data-skribl-line')); } catch (e) {}
            return { w: +b.getAttribute('data-skribl-w') || 0, h: +b.getAttribute('data-skribl-h') || 0,
                     shaped: b.classList.contains('is-shaped'), ar: +(r.width / r.height).toFixed(3),
                     line: line }; }""")
        check("the post is in its drawing's shape: the host passes the drawing's size",
              bool(_dw) and bool(_dh) and _hb["shaped"] and _hb["w"] == _dw and _hb["h"] == _dh
              and abs(_hb["ar"] - _dw / _dh) < 0.02,
              f"drawing {_dw} x {_dh}; box {json.dumps(_hb)}")
        check("...and its line knows the drawing before anybody presses play (line_info)",
              bool(_hb["line"]) and (_hb["line"] or {}).get("drawn", 0) > 0, json.dumps(_hb["line"]))
        pg.wait_for_timeout(1500)
        st = pg.evaluate("""() => { var ps = window.SkriblInline.players();
            var p = ps && ps[0]; return p ? p.state() : null; }""")
        check("the player adopted the POSTED skribl, by id",
              st and st.get("id"), json.dumps(st))
        # NOT totalMs here. A posted box idles behind its share card and fetches
        # the payload LAZILY — totalMs is 0 and loaded is false until something
        # asks it to play, which is the whole point of the poster. Asserting a
        # duration before that measures the fetch not having happened yet.
        check("...and it has NOT fetched the payload yet — the poster is the "
              "idle state",
              st and st.get("loaded") is False, json.dumps(st))
        # Playing it is the difference between "the markup is there" and "it
        # works": the payload has to fetch, through the prefixed API, from the
        # host's page.
        pg.evaluate("""() => { var p = window.SkriblInline.players()[0];
                               p.play(); }""")
        # The fetch is part of this, so wait for movement, not 1200ms.
        try:
            pg.wait_for_function("() => window.SkriblInline.players()[0].state().elapsedMs > 100",
                                 timeout=8000)
        except PWTimeout:
            pass
        moved = pg.evaluate("""() => { var p = window.SkriblInline.players()[0];
                                       return p.state().elapsedMs; }""")
        check("it plays — the payload fetched through the PREFIXED api",
              moved > 100, f"elapsedMs {moved}")
        st2 = pg.evaluate("""() => window.SkriblInline.players()[0].state()""")
        check("...and now it knows how long the drawing is",
              st2 and st2.get("totalMs", 0) > 200, json.dumps(st2))
        ink = pg.evaluate("""() => {
            var c = document.querySelector('[data-skribl-inline] .skribl-inline-canvas');
            var x = c.getContext('2d');
            var d = x.getImageData(0, 0, c.width, c.height).data;
            var n = 0; for (var i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
            return n; }""")
        check("and there is ink on the canvas, not an empty box", ink > 200,
              f"{ink} opaque pixels")
        check("no page errors anywhere in the flow", not errs, "; ".join(errs[:2]))

        print("\n6 — TICKED: IN THE POST AND IN THE SKRIBLS GALLERY, WITH ITS OWN CAPTION")
        first = durable("SELECT public_id FROM skribl_posts LIMIT 1")
        pg.click("#padBtn")
        pg.wait_for_function(
            "() => { const f = document.getElementById('padFrame');"
            " const w = f && f.contentWindow;"
            " return !!(w && w.__skriblBoot && w.__skriblBoot.pad); }",
            timeout=30000)
        pg.wait_for_timeout(800)
        fr = pg.frame_locator("#padFrame")
        draw(pg, fr.locator("#canvas").bounding_box())
        pg.wait_for_timeout(400)
        fr.locator("#recordBtn").click()
        pg.wait_for_timeout(700)
        fr.locator("#postBtn").click()
        pg.wait_for_timeout(1200)
        fr.locator("#postSheet .post-check").click()
        pg.wait_for_timeout(600)
        fr.locator("#postCaptionInput").fill("a snail for the gallery")
        fr.locator("#postSubmitBtn").click()
        pg.wait_for_timeout(4000)
        pg.fill("#body", "and one for everyone")
        # The feed posts to itself and comes back to "/", where it already
        # is, so wait for the navigation itself, not for the address.
        with pg.expect_navigation(timeout=20000):
            pg.click("#postBtn")
        pg.wait_for_timeout(1500)
        second = durable("SELECT public_id FROM skribl_posts WHERE public_id != '%s'" % first)
        check("the second post made a second skribl", bool(second) and durable("SELECT COUNT(*) FROM skribl_posts") == 2,
              f"{durable('SELECT COUNT(*) FROM skribl_posts')} row(s)")
        check("ticked, it is in the gallery too: public",
              durable("SELECT visibility FROM skribl_posts WHERE public_id = '%s'" % second) == "public",
              str(durable("SELECT visibility FROM skribl_posts WHERE public_id = '%s'" % second)))
        check("...with the gallery caption the author wrote, not the post's words",
              durable("SELECT caption FROM skribl_posts WHERE public_id = '%s'" % second) == "a snail for the gallery",
              str(durable("SELECT caption FROM skribl_posts WHERE public_id = '%s'" % second)))
        with urllib.request.urlopen(BASE + "/skribl/api/skribls?limit=50", timeout=15) as r:
            listed = [i["id"] for i in json.loads(r.read().decode()).get("items", [])]
        check("the listing has the ticked one and not the one left off",
              second in listed and first not in listed,
              f"second={second in listed} first={first in listed}")
        check("no page errors in the second post", not errs, "; ".join(errs[:2]))

        print("\n7 — THE SKRIBLS PAGE: EVERY PUBLIC SKRIBL, IN THE HOST'S FRAME, EACH BACK TO ITS POST")
        # Two made in the app, by grace, ticked for the gallery there: a
        # drawing and a Flip, through create_post as the app's own Post sheet
        # makes them (public, in no post of the host's). Their own process,
        # as the seed.
        subprocess.run(
            [sys.executable, "-c",
             "import json, pathlib, app as ex; from skribl import create_post;"
             " a = ex.create_app(); ctx = a.app_context(); ctx.push();"
             " d = pathlib.Path(%r);"
             " g = ex.db.session.query(ex.User).filter_by(handle='grace').one();"
             " [create_post(dict(json.loads((d / f).read_text()), title=t, visibility='public'), author_id=g.id)"
             "  for f, t in (('pug.json', 'Pug, in one go'), ('flip-bounce.json', 'Bounce'))];"
             " ex.db.session.commit()" % str(ROOT / "skribl" / "static" / "help" / "demos")],
            cwd=str(EXAMPLE), env=env, check=True, capture_output=True)
        pug = durable("SELECT public_id FROM skribl_posts WHERE title = 'Pug, in one go'")
        bounce = durable("SELECT public_id FROM skribl_posts WHERE title = 'Bounce'")
        second_post = durable("SELECT id FROM host_posts WHERE skribl_id = '%s'" % second)
        with urllib.request.urlopen(BASE + "/skribl/api/skribls?limit=50", timeout=15) as r:
            items = {i["id"]: i for i in json.loads(r.read().decode()).get("items", [])}
        _s, _p = items.get(second, {}), items.get(pug, {})
        # THE TWO RESOLVERS (app.py): the names and the posts Skribl cannot know.
        check("the listing says where the ticked one was posted: the host's page for its post",
              (_s.get("source") or {}).get("url") == "/posts/%s" % second_post, json.dumps(_s.get("source")))
        check("...and nothing for one made in the app", "source" not in _p and pug in items,
              json.dumps(_p.get("source")))
        check("...and who drew each, by the host's name for them",
              (_s.get("author") or {}).get("username") == "ada"
              and (_p.get("author") or {}).get("username") == "grace",
              f"{_s.get('author')} {_p.get('author')}")
        with urllib.request.urlopen(BASE + "/skribl/api/skribls/" + second, timeout=15) as r:
            one = json.loads(r.read().decode())
        check("a skribl read on its own says the same post", one.get("source") == _s.get("source"),
              json.dumps(one.get("source")))

        # EVERY WAIT BELOW REPORTS RATHER THAN STOPS: a page that never fills
        # (or never finds, or has no link to follow) is a red row with what
        # it showed, and the rows after it still run.
        def settle(page, cond, ms):
            try:
                page.wait_for_function(cond, timeout=ms)
                return True
            except PWTimeout:
                return False

        # THE PAGE IS SKRIBL'S OWN GALLERY SECTION (after v330, the owner's B):
        # its cards, read where /gallery's are read. Who drew it is the host's
        # name in the card's head (the handle, `.tun`); what it was made in is
        # the card's kind, said in words for a screen reader (`.tileSr`).
        browsing.goto(pg, BASE, "/skribls", require_boot=False)
        settle(pg, "() => document.querySelectorAll('#galleryList > article.tile').length >= 3", 15000)
        pg.wait_for_timeout(800)
        tiles = pg.evaluate("""() => [...document.querySelectorAll('#galleryList > article.tile')].map(c => {
            const box = c.querySelector('[data-skribl-inline]'), a = c.querySelector('a.tfrom');
            return { id: box && box.getAttribute('data-skribl-id'), mounted: !!(box && box._skriblInline),
                     title: c.querySelector('.tt').textContent,
                     who: (c.querySelector('.tun') || {}).textContent || '',
                     from: a ? a.getAttribute('href') : null,
                     kind: (c.querySelector('.tileSr') || {}).textContent || '' }; })""")
        by_id = {t["id"]: t for t in tiles}
        check("the page shows the public ones, from both doors, and not the one left off",
              {second, pug, bounce} <= set(by_id) and first not in by_id, json.dumps(tiles))
        check("...each one a player, mounted where it sits",
              all(t["mounted"] for t in tiles), json.dumps(tiles))
        # ITS OWN POSTER: the page fills in the id wherever the macro wrote the
        # placeholder, so the idle tile shows its drawing, not a 404 hidden.
        # Read on the tiles in view: the poster is loading="lazy".
        _posters = pg.evaluate("""() => [...document.querySelectorAll('#galleryList > article.tile')].map(c => {
            const b = c.querySelector('[data-skribl-inline]'), i = b && b.querySelector('img');
            return { id: b && b.getAttribute('data-skribl-id'), src: i ? i.getAttribute('src') : null,
                     inView: !!i && i.getBoundingClientRect().top < innerHeight,
                     loaded: !!(i && !i.hidden && i.complete && i.naturalWidth > 0) }; })""")
        check("...each showing its own drawing's poster: the id where the macro wrote the placeholder",
              bool(_posters) and all(p["src"] and p["id"] in p["src"] and "__ID__" not in p["src"] for p in _posters)
              and any(p["inView"] for p in _posters)
              and all(p["loaded"] for p in _posters if p["inView"]), json.dumps(_posters))
        _ts, _tp, _tb = by_id.get(second, {}), by_id.get(pug, {}), by_id.get(bounce, {})
        check("the one from a post: its title, @ada, and 'From a post' linking to that post",
              _ts.get("title") == "and one for everyone" and _ts.get("who") == "@ada"
              and (_ts.get("from") or "").endswith("/posts/%s" % second_post), json.dumps(_ts))
        # A drawing made in the app is in no post, so its card says nothing
        # more (the A tiles' "Made in Skribl Pad" went with them); its kind is
        # the card's own, the pen or the book, said in words too.
        check("the ones made in the app link nowhere, and their cards say what they are (a replay, a flip)",
              _tp.get("who") == "@grace" and _tp.get("from") is None and "replay" in _tp.get("kind", "")
              and _tb.get("from") is None and ("pages" in _tb.get("kind", "") or "a flip" in _tb.get("kind", "")),
              f"{_tp} {_tb}")
        # The words ask the listing, as Skribl's own gallery does.
        pg.fill("#galleryQ", "snail")
        settle(pg, "() => document.querySelectorAll('#galleryList > article.tile').length === 1", 8000)
        _found = pg.evaluate("() => [...document.querySelectorAll('#galleryList [data-skribl-inline]')].map(b => b.getAttribute('data-skribl-id'))")
        check("searching finds the ticked one by the gallery caption its author wrote", _found == [second], json.dumps(_found))
        pg.fill("#galleryQ", "")
        settle(pg, "() => document.querySelectorAll('#galleryList > article.tile').length >= 3", 8000)

        _link = pg.locator(f"#galleryList > article.tile[data-id='{second}'] a.tfrom")
        _post = {"posts": [], "skribl": None, "composer": None, "why": "no 'From a post' link on its tile"}
        if _link.count():
            _link.click()
            try:
                pg.wait_for_url(BASE + "/posts/%s" % second_post, timeout=15000)
            except PWTimeout:
                pass
            pg.wait_for_timeout(800)
            _post = pg.evaluate("""() => ({ at: location.pathname, posts: [...document.querySelectorAll('article.post')].map(a => a.id),
                skribl: (document.querySelector('article.post [data-skribl-inline]') || {getAttribute: () => null}).getAttribute('data-skribl-id'),
                composer: !!document.getElementById('composer') })""")
        check("'From a post' opens that post, with its drawing in it and no composer",
              _post["posts"] == ["post-%s" % second_post] and _post["skribl"] == second and not _post["composer"],
              json.dumps(_post))

        # SKRIBL'S OWN GALLERY knows the names too, through the same resolver:
        # it said "Anonymous" for the site's people before.
        browsing.goto(pg, BASE, "/skribl/gallery", require_boot=False)
        settle(pg, "() => document.querySelectorAll('.tdn').length >= 3", 15000)
        _names = pg.evaluate("() => [...document.querySelectorAll('.tdn')].map(e => e.textContent.trim())")
        check("Skribl's own gallery names them as the site does, not 'Anonymous'",
              "Anonymous" not in _names and any("ada" in n for n in _names) and any("grace" in n for n in _names),
              json.dumps(_names))
        check("no page errors on the Skribls pages", not errs, "; ".join(errs[:2]))

        # THE GALLERY'S OWN LAYOUT IN THE HOST'S FRAME (the owner's B, as its
        # mock showed it): two cards across on the desk, one on a phone, as
        # /gallery lays them out, each with the card's own transport under its
        # drawing (lib/fullbar.js) rather than the in-post player's line. A
        # post keeps the line, whole even on the narrowest phone.
        def lines(page):
            return page.evaluate("""() => [...document.querySelectorAll('article.post .skribl-inline-line')].map(l => {
                const shown = s => { const e = l.querySelector(s); return !!(e && e.getClientRects().length); };
                return { w: Math.round(l.getBoundingClientRect().width), on: l.classList.contains('is-on'),
                         time: shown('.rl-drawn b'), speed: shown('.rl-speed'), watching: shown('.rl-text > .rl-m') }; })""")
        CARDS = """() => { const cards = [...document.querySelectorAll('#galleryList > article.tile')];
            return { cards: cards.length, across: new Set(cards.map(c => Math.round(c.getBoundingClientRect().x))).size,
                     bars: cards.filter(c => c.querySelector('.tileStage .skfull-card')).length,
                     lines: document.querySelectorAll('#galleryList .skribl-inline-line').length }; }"""
        browsing.goto(pg, BASE, "/skribls", require_boot=False)
        settle(pg, "() => document.querySelectorAll('#galleryList .skfull-card').length >= 3", 15000)
        _desk = pg.evaluate(CARDS)
        check("on the desk the cards go two across, each with the card's own transport",
              _desk["cards"] >= 3 and _desk["across"] == 2 and _desk["bars"] == _desk["cards"] and _desk["lines"] == 0,
              json.dumps(_desk))
        ph = b.new_context(viewport={"width": 402, "height": 874}, is_mobile=True, has_touch=True)
        pp = ph.new_page()
        pp.on("pageerror", lambda e: errs.append(str(e)))
        browsing.goto(pp, BASE, "/skribls", require_boot=False)
        settle(pp, "() => document.querySelectorAll('#galleryList .skfull-card').length >= 3", 15000)
        _phone = pp.evaluate(CARDS)
        check("on a phone they go one across",
              _phone["cards"] >= 3 and _phone["across"] == 1 and _phone["bars"] == _phone["cards"], json.dumps(_phone))
        pp.set_viewport_size({"width": 320, "height": 640})
        browsing.goto(pp, BASE, "/posts/%s" % second_post, require_boot=False)
        settle(pp, "() => !!document.querySelector('article.post .skribl-inline-line.is-on')", 15000)
        _narrow = lines(pp)
        check("...and a post on a 320px phone keeps the whole line",
              _narrow and all(x["speed"] and x["watching"] for x in _narrow), json.dumps(_narrow))
        ph.close()
        check("no page errors on a phone", not errs, "; ".join(errs[:2]))

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
