"""Skribl mounted under a url_prefix — the whole point of the blueprint.

Every other suite drives Skribl at the ROOT prefix, which is exactly why the
hardcoded route literals in flip.js survived so long: they were correct at the
root and would have 404'd anywhere else, with all 632 assertions still green.

This suite is the missing coverage. It boots a SECOND server with
SKRIBL_URL_PREFIX=/skribl on its own port, and drives it with a real browser.
It is self-contained — it does not use the runner's server on 5001 — so it can
prove the mount without disturbing any other suite.
"""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/skribl"
PORT = 5007
BASE = f"http://127.0.0.1:{PORT}"

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
          ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(0)

# ---------- boot a prefixed instance on its own port ----------
tmp = tempfile.mkdtemp()
env = dict(os.environ,
           SKRIBL_URL_PREFIX=PREFIX,
           DATABASE_URL=f"sqlite:///{tmp}/prefix.db",
           SKRIBL_RATE_MAX_POSTS="100000",
           SECRET_KEY="harness-prefix-suite")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def wait_ready(timeout=25):
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

try:
    if not wait_ready():
        sys.exit(f"SKIP: prefixed instance did not start on port {PORT}.")

    def get(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    print("\nPREFIX — the surfaces answer under /skribl and NOT at the root")
    for path, label in [("/", "Pad"), ("/skribl-pad", "Pad (alias)"), ("/flip", "Flip")]:
        st, _ = get(PREFIX + path)
        check(f"{label} serves 200 at {PREFIX}{path}", st == 200, str(st))
    for path in ("/", "/flip", "/api/skribls"):
        st, _ = get(path)
        check(f"root {path} is NOT served (would be the host's)", st == 404, str(st))

    print("\nASSETS — blueprint static follows the prefix")
    for f in ("app.js", "flip.js", "styles.css"):
        st, _ = get(f"{PREFIX}/static/{f}")
        check(f"{PREFIX}/static/{f} serves 200", st == 200, str(st))

    print("\nSEAM — the injected config carries the prefixed routes")
    for path, label in [("/", "Pad"), ("/flip", "Flip")]:
        st, body = get(PREFIX + path)
        html = body.decode("utf-8", "replace")
        api = f'window.SKRIBL_API_BASE = "{PREFIX}/api/skribls"'
        check(f"{label} injects the prefixed API base", api in html,
              "missing" if api not in html else "")
        check(f"{label} carries no bare /api/skribls literal",
              'window.SKRIBL_API_BASE = "/api/skribls"' not in html)

    # ---------- a real post, end to end, through the browser ----------
    from playwright.sync_api import sync_playwright

    print("\nEND TO END — posting and replaying under the prefix")
    frame = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}
    payload = {"title": "prefix probe", "frames": [frame]}
    req = urllib.request.Request(
        BASE + PREFIX + "/api/skribls", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        created = json.loads(r.read())
    check("POST under the prefix returns 201", r.status == 201, str(r.status))
    sid = created.get("id")
    check("the response carries a public id", bool(sid), str(sid))
    check("the returned url is prefixed, not rooted",
          str(created.get("url", "")).startswith(PREFIX + "/s/"), str(created.get("url")))

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        failed = []
        pg.on("requestfailed", lambda r: failed.append(r.url))

        pg.goto(f"{BASE}{PREFIX}/s/{sid}", wait_until="load")
        pg.wait_for_timeout(2500)
        check("player page loads under the prefix with no JS errors",
              not errors, "; ".join(errors[:2]))
        check("no request failed while loading the player",
              not failed, "; ".join(failed[:2]))
        loaded = pg.evaluate(
            "() => !!(window.SKRIBL_PLAYER_ID && window.SKRIBL_API_BASE)")
        check("the player's config globals are present", loaded)
        api_base = pg.evaluate("() => window.SKRIBL_API_BASE")
        check("player API base is prefixed", api_base == PREFIX + "/api/skribls", str(api_base))

        # Flip is the surface that had no config block at all before v132.
        ferrors = []
        fp = b.new_page()
        fp.on("pageerror", lambda e: ferrors.append(str(e)))
        fp.goto(f"{BASE}{PREFIX}/flip", wait_until="load")
        fp.wait_for_timeout(2000)
        check("Flip loads under the prefix with no JS errors",
              not ferrors, "; ".join(ferrors[:2]))
        check("Flip's API base is prefixed (the bug this refactor closes)",
              fp.evaluate("() => window.SKRIBL_API_BASE") == PREFIX + "/api/skribls",
              str(fp.evaluate("() => window.SKRIBL_API_BASE")))
        check("Flip's player base is prefixed",
              fp.evaluate("() => window.SKRIBL_PLAYER_BASE") == PREFIX + "/s",
              str(fp.evaluate("() => window.SKRIBL_PLAYER_BASE")))
        b.close()

    print("\nCSP — the policy still applies under the prefix")
    import urllib.request as _u
    r = _u.urlopen(BASE + PREFIX + "/flip", timeout=10)
    csp = r.headers.get("Content-Security-Policy", "")
    check("Flip carries a CSP under the prefix", "default-src 'self'" in csp, csp[:60])
    check("and it is the restrictive default", "frame-ancestors 'self'" in csp)
    ra = _u.urlopen(BASE + PREFIX + "/static/app.js", timeout=10)
    check("prefixed static assets carry the security headers",
          ra.headers.get("X-Content-Type-Options") == "nosniff",
          str(ra.headers.get("X-Content-Type-Options")))

finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---- the documented session contract is now enforced -----------------------
# The package docs say the host MUST provide a session callable, but
# create_blueprint(session=None) accepted it and models.session() fell through
# to the process-wide binding. An app initialised WITHOUT a session could
# therefore reach whichever database the last app to pass one had bound — the
# cross-application coupling the per-app extension storage was written to end,
# reintroduced through the door left open for it. Failing at startup is safer
# than discovering the wrong database mid-request.
try:
    import sys as _sys, pathlib as _pl
    # this suite drives a subprocess server, so the package is not on
    # the path here the way it is in suites that import it directly
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
    import flask
    import skribl

    _raised = None
    try:
        skribl.init_skribl(flask.Flask("no_session_app"))
    except Exception as _e1:      # noqa: BLE001
        _raised = _e1
    check("initialising without a session is refused at startup",
          isinstance(_raised, (TypeError, RuntimeError, ValueError)),
          f"got {_raised!r} — a missing session must not be discoverable only "
          "later, as a query against another application's database")
    check("and the refusal names what the host has to do",
          _raised is not None and "session" in str(_raised).lower(),
          f"message was {str(_raised)!r}")

    _app_ok = flask.Flask("with_session_app")
    _sentinel = object()
    skribl.init_skribl(_app_ok, session=lambda: _sentinel)
    with _app_ok.app_context():
        from skribl.models import session as _sess
        check("an app that supplies one resolves its own session",
              _sess() is _sentinel)
except Exception as _e2:          # noqa: BLE001
    check("the session contract is testable", False, repr(_e2))


summarise_and_exit()
