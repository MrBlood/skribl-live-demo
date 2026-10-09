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

THE INSTALLED APP, SIMULATED. lib/offline.js registers the worker only when
Skribl runs from the Home Screen (navigator.standalone, or the standalone
display mode). Chromium has no Home Screen, so the suite's browser declares
navigator.standalone before any script runs -- the same property Safari sets
-- and a second, ordinary tab asserts that nothing registers there.

Calibrated against: pages cache-first (fresh-online goes red), no page
fallback (offline boot goes red), no offline note, the API cached, and the
registration script removed.
"""
import json, os, re, socket, subprocess, sys, tempfile, time, urllib.request
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


def up(cwd=ROOT):
    global proc
    proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                             "--port", str(PORT), "--no-reload"],
                            cwd=cwd, env=env,
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
        print("\nA BROWSER TAB — no worker")
        tab = b.new_context(viewport={"width": 390, "height": 844})
        tp = tab.new_page()
        tp.goto(BASE + "/skribl-pad", wait_until="load")
        tp.wait_for_function(BOOTED, timeout=10000)
        tp.wait_for_timeout(1500)
        regs = tp.evaluate("() => navigator.serviceWorker.getRegistrations().then(r => r.length)")
        check("a page in an ordinary tab registers no worker, so nothing answers before the page's own requests",
              regs == 0, f"{regs} registered")
        tab.close()
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true });")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        print("\nONLINE — always the newest page")
        pg.goto(BASE + "/skribl-pad", wait_until="load")
        pg.wait_for_function(BOOTED, timeout=10000)
        scope = pg.evaluate("""() => Promise.race([navigator.serviceWorker.ready.then(r => r.scope),
            new Promise(res => setTimeout(() => res(null), 8000))])""")
        check("opened as the Home Screen app, the Pad registers the worker, scoped to the mount point",
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
        # The API, asked once with a signal, so that a worker that kept it
        # would have something to answer with when the signal goes.
        pg.evaluate("() => fetch('/api/skribls?limit=1').then(r => r.status)")
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
        try:
            pg.goto(BASE + "/flip", wait_until="load")
            note = pg.evaluate("() => document.body.innerText")
        except Exception as e:   # the browser's own error page: what this guards against
            note = f"navigation failed: {str(e).splitlines()[0]}"
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

        print("\nSTAYING CURRENT — the build, the menu's Reload, the pill, the pull")
        with urllib.request.urlopen(BASE + "/build.json", timeout=10) as r:
            bj = json.loads(r.read().decode("utf-8")); bcache = r.headers.get("Cache-Control", "")
        page_build = pg.evaluate("() => document.querySelector('script[data-build]').dataset.build")
        check("/build.json names the build the server is serving, never cached",
              bool(bj.get("build")) and bcache == "no-store", f"{bj} {bcache!r}")
        check("...and a page carries the build it was rendered from, the same one",
              page_build == bj.get("build"), f"page {page_build!r} server {bj.get('build')!r}")
        row = pg.evaluate("() => { const r = document.getElementById('reloadAppItem'); return r ? !r.hidden : null; }")
        check("in the Home Screen app, the ⋯ menu has a Reload row", row is True, repr(row))
        pg.evaluate("() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });"
                    " document.dispatchEvent(new Event('visibilitychange')); }")
        pg.wait_for_timeout(800)
        check("...and coming back to it with the same build offers nothing",
              pg.evaluate("() => !document.getElementById('skriblUpdate')"))
        before = pg.evaluate(NONCE)
        pg.click("#menuBtn"); pg.wait_for_timeout(500)
        with pg.expect_navigation(timeout=10000):
            pg.click("#reloadAppItem")
        pg.wait_for_function(BOOTED, timeout=10000)
        check("...and Reload loads the page fresh", pg.evaluate(NONCE) not in (before, None))

        # A newer build, as the page sees it: the server's answer is changed in
        # the page (the worker answers before page.route could), so this pins
        # the comparison and the offer, not the fingerprint.
        pg.evaluate("""() => { const real = window.fetch;
            window.fetch = (u, o) => String(u).endsWith('/build.json')
              ? Promise.resolve(new Response(JSON.stringify({ build: 'newer' }), { headers: { 'Content-Type': 'application/json' } }))
              : real(u, o);
            document.dispatchEvent(new Event('visibilitychange')); }""")
        pg.wait_for_selector("#skriblUpdate.in", timeout=5000)
        pill = pg.evaluate("""() => { const n = document.getElementById('skriblUpdate');
            return { text: n.textContent, role: n.getAttribute('role'), btn: n.querySelector('button') && n.querySelector('button').textContent }; }""")
        check("a newer build on the server: the Pad offers it, \"A new version of Skribl is ready · Reload\"",
              "new version" in pill["text"] and pill["btn"] == "Reload" and pill["role"] == "status", str(pill))
        before = pg.evaluate(NONCE)
        pg.wait_for_timeout(1500)
        check("...and never reloads by itself", pg.evaluate(NONCE) == before, "the page changed under the offer")
        with pg.expect_navigation(timeout=10000):
            pg.click("#skriblUpdate button")
        pg.wait_for_function(BOOTED, timeout=10000)
        check("...and its Reload loads the page fresh", pg.evaluate(NONCE) not in (before, None))

        tab = b.new_context(viewport={"width": 390, "height": 844})
        tp = tab.new_page(); tp.goto(BASE + "/skribl-pad", wait_until="load"); tp.wait_for_timeout(800)
        check("an ordinary tab has no Reload row (its browser has one)",
              tp.evaluate("() => document.getElementById('reloadAppItem').hidden") is True)
        tab.close()

        lib = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        lib.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true });")
        lp = lib.new_page(); lp.goto(BASE + "/library", wait_until="load"); lp.wait_for_timeout(1200)
        cdp = lib.new_cdp_session(lp)
        def pull(dy):
            pts = lambda y: [{"x": 195, "y": y}]
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": pts(150)})
            for i in range(1, 11):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": pts(150 + dy * i / 10)})
            h = lp.evaluate("() => document.getElementById('pullRefresh').getBoundingClientRect().height")
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            return h
        before = lp.evaluate(NONCE)
        h = pull(80); lp.wait_for_timeout(600)
        check("the Library: a short pull shows the indicator and lets go without refreshing",
              h > 20 and lp.evaluate(NONCE) == before
              and lp.evaluate("() => document.getElementById('pullRefresh').getBoundingClientRect().height") < 2, f"{h}px")
        with lp.expect_navigation(timeout=10000):
            h = pull(260)
        check("...a pull past the line refreshes the page", lp.evaluate(NONCE) not in (before, None), f"{h}px")
        lib.close()

        # ── A NEW BUILD, AND A PAGE KEPT FROM THE OLD ONE (v321 preflight, PF-007)
        # The worker dropped an older copy of a file the moment a newer one was
        # stored. Open Pad and Flip, deploy, open only the Pad: Flip's kept page
        # still named the old shared files, and offline it opened as bare HTML
        # once the browser's own cache no longer held them. The browser's cache
        # is cleared here to stand in for that (a phone evicts it; this one
        # would otherwise answer from it and hide the bug). The new build is a
        # COPY of the tree with two shared files changed: a suite must never
        # edit tracked files, which the seal hashes.
        print("\nA NEW BUILD — a page kept from the old one still opens offline")
        import shutil
        newer = Path(tempfile.mkdtemp()) / "build-n1"
        shutil.copytree(ROOT / "skribl", newer / "skribl")
        shutil.copy(ROOT / "app.py", newer / "app.py")
        for rel, tail in (("skribl/static/styles.css", "\n.pf-skew-probe { color: red; }\n"),
                          ("skribl/static/lib/theme.js", "\n;void 0;\n")):
            f = newer / rel
            f.write_text(f.read_text(encoding="utf-8") + tail, encoding="utf-8")
        sk = b.new_context(viewport={"width": 390, "height": 844})
        sk.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true });")
        sp = sk.new_page()
        sp.goto(BASE + "/skribl-pad", wait_until="load"); sp.wait_for_function(BOOTED, timeout=10000)
        sp.evaluate("() => navigator.serviceWorker.ready")
        sp.goto(BASE + "/skribl-pad", wait_until="load"); sp.wait_for_function(BOOTED, timeout=10000)
        sp.goto(BASE + "/flip", wait_until="load")
        sp.wait_for_function("() => !!(window.__skriblBoot && window.__skriblBoot.flip)", timeout=10000)
        sp.wait_for_timeout(1500)
        down()
        if not up(cwd=newer):
            check("the newer build starts", False)
        sp.goto(BASE + "/skribl-pad", wait_until="load"); sp.wait_for_function(BOOTED, timeout=10000)
        sp.wait_for_timeout(2500)
        names = sp.evaluate("""async () => { const out = [];
            for (const r of await (await caches.open('skribl-files-v1')).keys()) {
              const u = new URL(r.url); if (/styles\.css$|theme\.js$/.test(u.pathname)) out.push(u.pathname + u.search); }
            return out.sort(); }""")
        check("both builds' shared files are kept while the old Flip page names its own",
              len(names) == 4, str(names))
        sk.new_cdp_session(sp).send("Network.clearBrowserCache")
        down()
        failed = []
        sp.on("requestfailed", lambda r: "?v=" in r.url and failed.append(r.url.rsplit("/", 1)[-1]))
        sp.goto(BASE + "/flip", wait_until="load")
        try:
            sp.wait_for_function("() => !!(window.__skriblBoot && window.__skriblBoot.flip)", timeout=8000)
            flip_ok = True
        except Exception:
            flip_ok = False
        styled = sp.evaluate("() => getComputedStyle(document.querySelector('.header')).position")
        check("offline, Flip from the old build opens styled, every file it names answered",
              flip_ok and styled == "sticky" and not failed,
              f"booted {flip_ok}, header {styled!r}, failed {failed[:4]}")
        sk.close()
        up()
        b.close()
finally:
    down()

bad = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + ("  FAILURES: " + ", ".join(r[1] for r in bad) if bad else ""))
sys.exit(1 if bad else 0)
