"""Opening with no signal, and never opening old (the /sw.js route, lib/offline.js).

The owner wants Skribl to behave like an app on a phone; an app opens on a
train. The risk an offline cache brings is the opposite failure -- a phone with
a perfectly good signal shown yesterday's page -- and WORKING-AGREEMENTS records
two investigations that turned out to be exactly that. So the worker is NETWORK
FIRST for pages, with no timeout, and this suite pins both halves:

  * with the server up, every navigation is a fresh page (the CSP nonce, which
    the server mints per response, differs every time), and
  * with the server GONE, the Pad still boots, from the last page that loaded,
    and a page never opened online says it is offline rather than failing.

WHY THIS SUITE BOOTS ITS OWN SERVER. "Offline" has to be a real network failure.
Playwright's context.set_offline() does not reach a service worker's own
fetches: measured before this suite was written, it let a never-opened Flip
load "offline" and served the Pad fresh. An instrument that cannot go offline
would pass this suite on a worker that never answered anything. Stopping a
server is a failure the worker cannot tell from a dead signal, so this suite
starts one on its own port and stops it, without touching the runner's 5001.

Calibrated against: pages cache-first (fresh-online goes red), no page
fallback (offline boot goes red), no offline note, the API cached, and the
registration script removed.
"""
import os, re, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from assertions import make_check

ROOT = Path(__file__).resolve().parents[1]
PORT = 5019
BASE = f"http://127.0.0.1:{PORT}"

results = []
check = make_check(results)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp()
env = dict(os.environ,
           DATABASE_URL=f"sqlite:///{tmp}/offline.db",
           SKRIBL_RATE_MAX_POSTS="100000",
           SECRET_KEY="harness-offline-suite")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = None


def up():
    global proc
    proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                             "--port", str(PORT), "--no-reload"],
                            cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.time() + 25
    while time.time() < end:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(BASE + "/sw.js", timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def down():
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    # Gone means refusing connections, not merely signalled.
    end = time.time() + 10
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", PORT), 0.3):
                time.sleep(0.2)
        except OSError:
            return


NONCE = "() => { const s = document.querySelector('script[nonce]'); return s ? s.nonce : null; }"
BOOTED = "() => !!(window.__skriblBoot && window.__skriblBoot.pad)"

try:
    if not up():
        sys.exit(f"SKIP: instance did not start on port {PORT}.")

    print("\nTHE WORKER — what it is told to answer")
    with urllib.request.urlopen(BASE + "/sw.js", timeout=10) as r:
        sw = r.read().decode("utf-8")
        ctype, cache = r.headers.get("Content-Type", ""), r.headers.get("Cache-Control", "")
    check("/sw.js is JavaScript, at the mount point, and never cached",
          ctype.startswith("text/javascript") and cache == "no-cache", f"{ctype!r} {cache!r}")
    pages = re.search(r"var PAGES = (\[.*?\]);", sw)
    plist = pages.group(1) if pages else ""
    check("it answers for the Pad, Flip and the library, by url_for",
          all(f'"{p}"' in plist for p in ("/skribl-pad", "/flip", "/library")), plist)
    check("...and for nothing that holds anyone's data: no API, no post, no media",
          not any(x in plist for x in ("/api", "/s/", "/media")), plist)

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        print("\nONLINE — always the newest page")
        pg.goto(BASE + "/skribl-pad", wait_until="load")
        pg.wait_for_function(BOOTED, timeout=10000)
        scope = pg.evaluate("() => navigator.serviceWorker.ready.then(r => r.scope)")
        check("the Pad registers the worker, scoped to the mount point",
              scope == BASE + "/", repr(scope))
        seen = []
        for _ in range(3):
            pg.goto(BASE + "/skribl-pad", wait_until="load")
            pg.wait_for_function(BOOTED, timeout=10000)
            seen.append(pg.evaluate(NONCE))
        controlled = pg.evaluate("() => !!navigator.serviceWorker.controller")
        check("once installed, the worker controls the page", controlled)
        check("...and every load with a signal is a fresh page from the server, never a kept copy",
              len(set(seen)) == 3 and None not in seen, str(seen))
        last = seen[-1]
        pg.wait_for_timeout(600)   # the kept copy is written after the page is handed over
        kept = pg.evaluate("""async () => { const out = [];
            for (const k of await caches.keys()) for (const r of await (await caches.open(k)).keys())
              out.push(new URL(r.url).pathname); return out; }""")
        check("nothing from the API is kept", not any(k.startswith("/api") for k in kept),
              str([k for k in kept if k.startswith("/api")]))
        check("...and the files the Pad loaded are kept, by their content hash",
              any(k.endswith("/app.js") for k in kept), f"{len(kept)} kept")

        print("\nOFFLINE — the server is gone")
        down()
        try:
            pg.reload(wait_until="load")
            pg.wait_for_function(BOOTED, timeout=10000)
            booted = True
        except Exception:
            booted = False
        check("the Pad still opens, and boots, with no server at all", booted)
        check("...from the last page that loaded, not an older one",
              booted and pg.evaluate(NONCE) == last, f"{pg.evaluate(NONCE)!r} vs {last!r}")
        pg.goto(BASE + "/flip", wait_until="load")
        note = pg.evaluate("() => document.body.innerText")
        check("a page never opened online says it is offline, not the browser's error",
              "You’re offline" in note and "opened with one" in note, note[:120])
        api = pg.evaluate("""() => fetch('/api/skribls?limit=1').then(() => 'answered', () => 'failed')""")
        check("...and the API fails as the network does, not from a cache", api == "failed", api)

        print("\nBACK ONLINE")
        if not up():
            check("the instance restarts", False)
        pg.goto(BASE + "/skribl-pad", wait_until="load")
        pg.wait_for_function(BOOTED, timeout=10000)
        check("the next load is fresh again, not the copy that carried it through",
              pg.evaluate(NONCE) not in (last, None))
        check("no page errors", not errs, "; ".join(errs[:2]))
        b.close()
finally:
    down()

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("  FAILURES: " + ", ".join(r[1] for r in bad) if bad else ""))
sys.exit(1 if bad else 0)
