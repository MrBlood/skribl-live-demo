"""harness/waits.py keeps its promise: settle is never weaker than the sleep it replaces.

waits.settle() stands in for the fixed sleeps after a load, a click or a
reload, and waits.until() for the long ones after an upload or a restore. Both
are only as good as the work counter in waits.QUIET_JS: a kind of work it
cannot see is a kind it returns early on, and a suite that leaned on it would
read a page mid-change -- red for the wrong reason, or green.

So each kind of work is driven here on a page with nothing else on it, and
each must hold settle until it is done when it falls inside the window: a
timer, a chain of timers, a request, a database open and write, a file read,
a decode, a chain of animation frames, a CSS transition, a smooth scroll.
Nothing may hold it past the window, which is the old sleep: a timer due
later, an interval, an animation that never stops, a navigation partway
through. A quiet page must come back early, or settle saves nothing. until()
with a window must settle what the sleep would have waited for after its
state arrives, and a page without the counter gets the plain sleep.

No Skribl server: the pages come from a small server of this suite's own, so
IndexedDB and fetch behave as on a real origin.
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

from assertions import make_check
import waits

results = []
check = make_check(results)

PAGES = {
    "idle": "",
    "timer": "setTimeout(() => { window.done = 1; }, 700);",
    "late-timer": "setTimeout(() => { window.done = 1; }, 5000);",
    "chained": "setTimeout(() => setTimeout(() => setTimeout(() => { window.done = 1; }, 250), 250), 250);",
    "fetch": "fetch('/slow').then(r => r.json()).then(j => { window.done = j.ok; });",
    # Each of these three takes 300 ms or more on this box, well past settle's
    # own 100 ms of quiet, so a counter that missed it would return first.
    "idb": """const r = indexedDB.open('w', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('s');
        r.onsuccess = () => { let k = 0; const put = () => { const t = r.result.transaction('s', 'readwrite');
          t.objectStore('s').put(new Uint8Array(4e6).fill(k), 'k');
          t.oncomplete = () => { if (++k < 30) put(); else window.done = 1; }; }; put(); };""",
    "file": """const blob = new Blob([new Uint8Array(64e6)]); let k = 0;
        const go = () => { const f = new FileReader();
          f.onload = () => { if (++k < 6) go(); else window.done = 1; }; f.readAsArrayBuffer(blob); }; go();""",
    "decode": """const wav = (() => { const n = 44100 * 120, v = new DataView(new ArrayBuffer(44 + n * 2));
          const s = (o, t) => [...t].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
          s(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); s(8, 'WAVEfmt '); v.setUint32(16, 16, true);
          v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, 44100, true);
          v.setUint32(28, 88200, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
          s(36, 'data'); v.setUint32(40, n * 2, true); return v.buffer; })();
        const ac = new AudioContext(); let k = 0;
        const go = () => ac.decodeAudioData(wav.slice(0)).then(() => { if (++k < 5) go(); else window.done = 1; }); go();""",
    "frames": "let n = 0; const f = () => { if (++n < 40) requestAnimationFrame(f); else window.done = 1; }; requestAnimationFrame(f);",
    "endless-frames": "const f = () => requestAnimationFrame(f); requestAnimationFrame(f);",
    "interval": "setInterval(() => { window.ticks = (window.ticks || 0) + 1; (window.tickAt = window.tickAt || []).push(performance.now()); }, 200);",
    "transition": """document.body.innerHTML = '<div id=b style="width:40px;height:40px;background:#000;transition:opacity .6s">';
        requestAnimationFrame(() => requestAnimationFrame(() => {
          const b = document.getElementById('b'); b.style.opacity = '0';
          b.addEventListener('transitionend', () => { window.done = 1; }); }));""",
    "state-then-work": "setTimeout(() => { window.ready = 1; }, 100); setTimeout(() => { window.done = 1; }, 900);",
    # A smooth scroll runs no timer and no frame of the page's own.
    "smooth-scroll": """document.documentElement.style.scrollBehavior = 'smooth';
        document.body.innerHTML = '<div style="height:20000px"></div>';
        addEventListener('scrollend', () => { window.done = scrollY; });
        requestAnimationFrame(() => scrollTo(0, 15000));""",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/slow":
            time.sleep(0.7)
            body, kind = b'{"ok": 1}', "application/json"
        else:
            name = self.path.strip("/").split("/")[-1]
            body = (f"<!doctype html><html><body><script>{PAGES.get(name, '')}</script></body></html>").encode()
            kind = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
ORIGIN = f"http://127.0.0.1:{srv.server_address[1]}"


def timed(pg, name, ms):
    pg.goto(f"{ORIGIN}/p/{name}", wait_until="load")
    t0 = time.monotonic()
    waits.settle(pg, ms)
    return (time.monotonic() - t0) * 1000, pg.evaluate("() => window.done")


with sync_playwright() as p:
    b = waits.instrument(p.chromium.launch())

    print("\nSETTLE COMES BACK EARLY ON A QUIET PAGE -- or it saves nothing")
    pg = b.new_page()
    ms, _ = timed(pg, "idle", 2000)
    check("a page with nothing to do settles well inside the window", ms < 1000, f"{ms:.0f} ms of 2000")

    print("\nWORK DUE INSIDE THE WINDOW HOLDS IT until the work is done")
    for name, what in (("timer", "a timer"), ("chained", "a timer that sets a timer that sets a timer"),
                       ("fetch", "a request the server answers in 700 ms, and its body"),
                       ("idb", "opening a database and thirty 4 MB writes"), ("file", "reading a 64 MB file six times"),
                       ("decode", "decoding two minutes of audio five times"),
                       ("frames", "a chain of 40 animation frames"), ("transition", "a 0.6 s CSS transition")):
        ms, done = timed(pg, name, 4000)
        check(f"{what}: done before settle returns", bool(done), f"done={done!r} after {ms:.0f} ms")

    print("\nNOTHING HOLDS IT PAST THE WINDOW -- the old sleep is the ceiling")
    ms, done = timed(pg, "late-timer", 900)
    check("a timer due after the window does not hold it (the sleep never saw it fire either)",
          ms < 600 and not done, f"{ms:.0f} ms of 900, done={done!r}")
    ms, done = timed(pg, "endless-frames", 900)
    check("animation frames that never stop (a replay): held to the window, and no further",
          850 <= ms < 1600, f"{ms:.0f} ms of 900")
    # AN INTERVAL IS OWED THE SLEEP'S VIEW, NOT ITS LENGTH (after v326). Settle
    # may let go once the next tick falls past the window, so how early it
    # goes depends on where the ticks fall against the window: their clock
    # starts at the page's load, the window when goto returns. A floor on the
    # time went red on CI at 837 ms with nothing due in between, and a 95 ms
    # pause between load and settle reproduced it here. What settle owes is
    # that no tick lands between its return and the window's end, read on the
    # page's own clock.
    pg.goto(f"{ORIGIN}/p/interval", wait_until="load")
    p0 = pg.evaluate("() => performance.now()")
    t0 = time.monotonic()
    waits.settle(pg, 900)
    ms = (time.monotonic() - t0) * 1000
    p1 = pg.evaluate("() => performance.now()")
    pg.wait_for_timeout(max(0, 900 - ms) + 50)
    missed = pg.evaluate("([a, b]) => (window.tickAt || []).filter((t) => t > a && t <= b).length", [p1, p0 + 900])
    check("an interval ticking every 200 ms: held until no tick is due inside the window, and no further",
          missed == 0 and ms < 1600, f"{ms:.0f} ms of 900; {missed} tick(s) after settle returned, inside the window")

    print("\nA SCROLL HOLDS IT, AND A NAVIGATION DOES NOT STRETCH IT")
    ms, done = timed(pg, "smooth-scroll", 4000)
    check("a smooth scroll is done before settle returns", bool(done), f"scrollend at {done!r} after {ms:.0f} ms")
    # The page has been open three seconds when it leaves, so a deadline read
    # from its clock would hold the next page (whose clock starts again near
    # zero, and which never goes quiet) about three seconds past the window.
    pg.goto(f"{ORIGIN}/p/idle", wait_until="load")
    pg.wait_for_timeout(3000)
    pg.evaluate("() => setTimeout(() => { location.href = '/p/interval'; }, 200)")
    t0 = time.monotonic()
    waits.settle(pg, 1500)
    ms = (time.monotonic() - t0) * 1000
    check("a page that navigates while settle waits is held no longer than the window",
          1400 <= ms < 2300, f"{ms:.0f} ms of 1500")

    print("\nUNTIL WITH A WINDOW: the state, then what the sleep would have waited for")
    pg.goto(f"{ORIGIN}/p/state-then-work", wait_until="load")
    t0 = time.monotonic()
    ok = waits.until(pg, "() => window.ready === 1", "ready", window=1500)
    ms = (time.monotonic() - t0) * 1000
    check("the state arrived", ok, f"{ms:.0f} ms")
    check("...and the timer due inside the old window ran before until returned",
          pg.evaluate("() => window.done") == 1, f"done={pg.evaluate('() => window.done')!r} after {ms:.0f} ms")
    pg.close()

    print("\nA PAGE WITHOUT THE COUNTER GETS THE PLAIN SLEEP")
    plain = p.chromium.launch()
    pp = plain.new_page()
    pp.goto(f"{ORIGIN}/p/idle", wait_until="load")
    t0 = time.monotonic()
    waits.settle(pp, 800)
    ms = (time.monotonic() - t0) * 1000
    check("settle on an uninstrumented page sleeps the whole window", ms >= 780, f"{ms:.0f} ms of 800")
    plain.close()
    b.close()
srv.shutdown()

passed = sum(1 for r in results if r[0])
print(f"\n{'=' * 62}\n{passed}/{len(results)} passed"
      + ("" if passed == len(results) else "  FAILURES: " + ", ".join(r[1] for r in results if not r[0])))
raise SystemExit(0 if passed == len(results) else 1)
