#!/usr/bin/env python3
"""A first open at a slow phone's speed, measured (FUTURE.md 6af: "speed wherever Skribl lives").

    python3 harness/tools/firstopen.py [base] [runs]

A cold cache, the CPU slowed 4x and a 1.6 Mbps network with 150 ms round trips
(Chrome's own emulation), per editor: the files and the bytes it downloads,
first paint, when it can draw (its __skriblBoot mark), and how long the phone's
main thread was busy (Chrome's Performance metrics: tasks, scripts, layout).
Medians of `runs` (3) opens. Needs a server (the local one by default).
"""
import json, os, statistics, sys, time
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
NET = {"offline": False, "latency": 150, "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8}
PAGES = [("Pad", "/skribl-pad", "pad"), ("Flip", "/flip", "flip"), ("Pad in a post box", "/skribl-pad?compose=1", "pad")]
out = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, path, boot in PAGES:
        rows = []
        for r in range(RUNS):
            c = b.new_context(viewport={"width": 402, "height": 874}, is_mobile=True, has_touch=True, service_workers="block")
            pg = c.new_page(); cdp = c.new_cdp_session(pg)
            cdp.send("Network.enable"); cdp.send("Network.emulateNetworkConditions", NET)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4}); cdp.send("Performance.enable")
            t0 = time.monotonic()
            pg.goto(BASE + path, wait_until="commit")
            pg.wait_for_function(f"() => !!(window.__skriblBoot && window.__skriblBoot.{boot})", timeout=120000, polling=50)
            t_boot = time.monotonic() - t0
            pm = {x["name"]: x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]}
            pg.wait_for_timeout(1500)
            m = pg.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0], rs = performance.getEntriesByType('resource');
              const fcp = (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime;
              const s = document.querySelector('.canvas-empty-hand');
              return { requests: rs.length + 1, kb: Math.round((rs.reduce((a, e) => a + (e.transferSize || 0), 0) + (n.transferSize || 0)) / 1024),
                       scripts: rs.filter(e => e.initiatorType === 'script').length, fcp: Math.round(fcp || 0), dcl: Math.round(n.domContentLoadedEventEnd),
                       hand: s ? s.getAttribute('data-state') : null }; }""")
            m["boot"] = round(t_boot * 1000)
            m["scriptMs"] = round(pm.get("ScriptDuration", 0) * 1000); m["taskMs"] = round(pm.get("TaskDuration", 0) * 1000)
            m["layoutMs"] = round(pm.get("LayoutDuration", 0) * 1000)
            rows.append(m); c.close()
            print(name, r + 1, m, flush=True)
        med = {k: statistics.median([x[k] for x in rows]) for k in ("requests", "kb", "scripts", "fcp", "dcl", "boot", "scriptMs", "taskMs", "layoutMs")}
        out[name] = med
        print("==", name, "median:", med, flush=True)
    b.close()
print(json.dumps(out, indent=1))
