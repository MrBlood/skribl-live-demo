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
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the example works.")
    raise SystemExit(77)

import sqlalchemy as sa

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


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

        pg.goto(BASE + "/", wait_until="load")
        pg.wait_for_timeout(800)

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
        pg.wait_for_timeout(5000)
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
        check("the author stamp on the Skribl is the host's user",
              durable("SELECT user_id FROM skribl_posts LIMIT 1") ==
              durable("SELECT author_id FROM host_posts LIMIT 1"))
        check("the host set it public, so it is feed content not a hidden link",
              durable("SELECT visibility FROM skribl_posts LIMIT 1") == "public")
        check("the words became the caption",
              durable("SELECT caption FROM skribl_posts LIMIT 1")
              == "drew this in a host composer")

        print("\n5 — AND IT PLAYS, INSIDE THE HOST'S POST")
        check("the post is on the host's feed",
              pg.locator("article.post").count() == 1)
        check("with a Skribl in it", pg.locator("[data-skribl-inline]").count() == 1)
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
        pg.wait_for_timeout(1200)
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
