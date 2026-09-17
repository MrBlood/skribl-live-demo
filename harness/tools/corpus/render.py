#!/usr/bin/env python3
"""Render the in-between corpus and check each case against its expectations.

NOT A SUITE. It needs a Flip page served somewhere and a browser, which is why
it sits here and not in the aggregate -- see this directory's README.

    python3 -m flask --app app run --port 5001 --no-reload   # in one shell
    python3 harness/tools/corpus/render.py out/              # in another

Writes one PNG per case (the two poses, the in-between and the smear, at two
sampling densities, with every expectation printed underneath) plus a
results.json carrying the geometry each verdict was read from. Exits non-zero
if any case FAILs, so it can be run as a gate by hand.
"""
import base64
import json
import os
import pathlib
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

HERE = pathlib.Path(__file__).resolve().parent
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "corpus-out")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1500, "height": 1400})
    errs = []
    page.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    page.goto(BASE + "/flip", wait_until="networkidle")
    page.wait_for_timeout(1200)
    for f in ("lib.js", "cases.js", "run.js"):
        page.evaluate("(()=>{" + (HERE / f).read_text() + "})()")

    n = page.evaluate("window.__CASES.length")
    print(f"{n} cases, against {BASE}\n")
    rows, fails = [], 0
    for i in range(n):
        r = page.evaluate("(i)=>window.__RUN(i)", i)
        png = base64.b64decode(r.pop("png").split(",", 1)[1])
        fn = OUT / f"case-{r['id']}-{r['name']}.png"
        fn.write_bytes(png)
        r["file"] = fn.name
        rows.append(r)
        if r["verdict"] == "FAIL":
            fails += 1
        print(f"  {r['verdict']:<4} {r['id']:<4} {r['name']}")
        for tag in ("uniform", "hand"):
            for x in r["oracle"][tag]:
                if not x["ok"]:
                    print(f"         {tag:<8} {x['name']} -> {x['got']}")
    (OUT / "results.json").write_text(json.dumps(rows, indent=1))
    print(f"\n{n - fails}/{n} cases PASS   ->  {OUT}")
    if errs:
        print("PAGE ERRORS: " + "; ".join(errs[:3]))
    browser.close()

sys.exit(1 if fails or errs else 0)
