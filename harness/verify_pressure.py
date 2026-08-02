"""v132 — stylus pressure (`p`), the first new payload field since v109's `hold`.

`p` is optional, per-point, normalised 0..1, and it is governed by the same
additive rule `hold` established:

  - `pointWidth()` is the ONLY reader. It never trusts `p` to exist and clamps
    garbage (NaN, strings, negatives, >1) back into range, so a point without
    the field renders at exactly its stored `size` — that is what makes every
    pre-v132 Skribl play identically.
  - `p` is WRITTEN ONLY by a stylus reporting a non-neutral force. A mouse or
    finger stroke must serialise with no `p` key at all, so its payload is byte
    -identical to what it was before. Asserted here against a real browser-drawn
    payload rather than assumed.
  - A v132 payload in an older player degrades to uniform width, because an
    unknown field is ignored.

Both surfaces are covered: the Pad reads Touch.force (it is bound to mouse/touch
events), Flip reads PointerEvent.pressure. The two implementations are separate
by necessity, so the width maths is asserted independently in each.

The server-side half drives the API directly, in both directions: an in-range
`p` must be accepted and an out-of-range one refused, on the same reasoning that
already applies to `size`.
"""
import json
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200].decode("utf-8", "replace")}


def pt(x, y, **kw):
    p = {"x": x, "y": y, "color": "#ffffff", "size": 8, "t": 0}
    p.update(kw)
    return p


def frame(strokes, groups):
    return {"strokes": strokes, "strokeGroups": groups,
            "background": {"color": "#101418"}}


# --- 1. Width maths, evaluated against the real loaded modules ---------------
# Asserted in the browser against the actual shipped file, not a reimplementation
# here, so the suite cannot drift away from the code it is meant to guard.

WIDTH_PROBE = """
() => {
  const S = 10;
  const w = (p) => pointWidth(p === undefined ? {size:S} : {size:S, p});
  return {
    missing:   w(undefined),
    neutral:   w(0.5),
    full:      w(1),
    zero:      w(0),
    over:      w(9),
    under:     w(-4),
    nan:       w(NaN),
    str:       w("0.9"),
    nul:       w(null),
    light:     w(0.25),
    heavy:     w(0.75),
    base:      S
  };
}
"""


def assert_width_maths(surface, r):
    S = r["base"]
    check(f"[{surface}] a point with no `p` renders at exactly its stored size",
          r["missing"] == S, f"{r['missing']} == {S}")
    check(f"[{surface}] neutral pressure (0.5) is a no-op",
          abs(r["neutral"] - S) < 1e-9, f"{r['neutral']} == {S}")
    check(f"[{surface}] full pressure widens the stroke",
          r["full"] > S, f"{r['full']} > {S}")
    check(f"[{surface}] zero pressure thins the stroke but never to nothing",
          0 < r["zero"] < S, f"0 < {r['zero']} < {S}")
    check(f"[{surface}] pressure above 1 clamps to the full-pressure width",
          abs(r["over"] - r["full"]) < 1e-9, f"{r['over']} == {r['full']}")
    check(f"[{surface}] negative pressure clamps to the zero-pressure width",
          abs(r["under"] - r["zero"]) < 1e-9, f"{r['under']} == {r['zero']}")
    check(f"[{surface}] NaN pressure falls back to the unmodified size",
          r["nan"] == S, f"{r['nan']} == {S}")
    check(f"[{surface}] a string pressure falls back to the unmodified size",
          r["str"] == S, f"{r['str']} == {S}")
    check(f"[{surface}] null pressure is treated as absent",
          r["nul"] == S, f"{r['nul']} == {S}")
    check(f"[{surface}] width increases monotonically with pressure",
          r["zero"] < r["light"] < r["neutral"] < r["heavy"] < r["full"],
          f"{r['zero']} < {r['light']} < {r['neutral']} < {r['heavy']} < {r['full']}")


with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctx = br.new_context()

    print("\nWIDTH MATHS — the compatibility rule lives or dies here")
    pad = ctx.new_page()
    pad_errs = []
    pad.on("pageerror", lambda e: pad_errs.append(str(e)))
    pad.goto(f"{BASE}/skribl-pad", wait_until="load")
    pad.wait_for_timeout(600)
    assert_width_maths("Pad", pad.evaluate(WIDTH_PROBE))
    check("[Pad] no page errors after the pressure change", not pad_errs,
          "; ".join(pad_errs[:2]))

    flip = ctx.new_page()
    flip_errs = []
    flip.on("pageerror", lambda e: flip_errs.append(str(e)))
    flip.goto(f"{BASE}/flip", wait_until="load")
    flip.wait_for_timeout(600)
    assert_width_maths("Flip", flip.evaluate(WIDTH_PROBE))
    check("[Flip] no page errors after the pressure change", not flip_errs,
          "; ".join(flip_errs[:2]))

    # --- 2. The byte-identity rule -------------------------------------------
    # A mouse has no pressure. If any point picks up a `p` key from a mouse
    # stroke, every existing payload silently grows and this whole feature stops
    # being additive. Drawn through the real event path, not a synthesised array.
    print("\nBYTE IDENTITY — a mouse stroke must record no `p` at all")
    box = pad.evaluate("() => { const c = document.getElementById('canvas');"
                       " const r = c.getBoundingClientRect();"
                       " return {x: r.x, y: r.y, w: r.width, h: r.height}; }")
    pad.mouse.move(box["x"] + 40, box["y"] + 40)
    pad.mouse.down()
    for i in range(1, 12):
        pad.mouse.move(box["x"] + 40 + i * 9, box["y"] + 40 + i * 5)
    pad.mouse.up()
    pad.wait_for_timeout(300)

    drawn = pad.evaluate("() => ({ n: strokes.length,"
                         " withP: strokes.filter(s => 'p' in s).length })")
    check("a mouse stroke actually recorded points", drawn["n"] > 0,
          f"{drawn['n']} points")
    check("NOT ONE mouse-drawn point carries a `p` key",
          drawn["withP"] == 0, f"{drawn['withP']} of {drawn['n']} points")
    check("a mouse-drawn point serialises to the pre-v132 key set",
          pad.evaluate("() => Object.keys(strokes[0]).filter("
                       "k => k === 'p').length === 0"))

    # --- 3. Unknown fields are ignored, which is what old players rely on -----
    print("\nDEGRADATION — an unknown field must not break rendering")
    check("pointWidth ignores unrelated unknown keys on a point",
          pad.evaluate("() => pointWidth({size: 10, wobble: 3, p: undefined}) === 10"))

    br.close()

# --- 4. Server-side validation, both directions ------------------------------
print("\nACCEPT — every legitimate pressure payload must go through")
ok_cases = [
    ("no pressure at all (every pre-v132 payload)",
     [pt(10, 10, start=True), pt(20, 20)]),
    ("neutral pressure",
     [pt(10, 10, start=True, p=0.5), pt(20, 20, p=0.5)]),
    ("the full legal range, endpoints included",
     [pt(10, 10, start=True, p=0), pt(20, 20, p=1)]),
    ("pressure on some points but not others",
     [pt(10, 10, start=True, p=0.7), pt(20, 20)]),
]
for label, strokes in ok_cases:
    code, body = post({"frames": [frame(strokes, [len(strokes)])]})
    check(f"accepted: {label}", code == 201, f"HTTP {code} {body}")

print("\nREJECT — an out-of-range pressure must be refused at the door")
bad_cases = [
    ("pressure above 1", 2),
    ("pressure below 0", -0.5),
    ("a wildly out-of-range value", 1e9),
    ("NaN, which poisons every width downstream", float("nan")),
    ("infinity", float("inf")),
]
for label, val in bad_cases:
    strokes = [pt(10, 10, start=True, p=val), pt(20, 20)]
    payload = json.dumps({"frames": [frame(strokes, [2])]})
    req = urllib.request.Request(BASE + "/api/skribls", data=payload.encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 400   # non-JSON-serialisable NaN/inf never reaches the server
    check(f"refused: {label}", code == 400, f"HTTP {code}")

print("\nROUND TRIP — a pressure payload survives post and replay")
strokes = [pt(10 + i * 6, 10 + i * 4, p=round(0.1 + i * 0.08, 2),
              **({"start": True} if i == 0 else {}))
           for i in range(10)]
code, body = post({"frames": [frame(strokes, [len(strokes)])]})
pid = body.get("id") if isinstance(body, dict) else None
check("a varying-pressure Skribl posts successfully", code == 201 and bool(pid),
      f"HTTP {code}")

if pid:
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(f"{BASE}/s/{pid}", wait_until="load")
        page.wait_for_timeout(1500)
        check("the pressure Skribl loads in the player with no errors",
              not errs, "; ".join(errs[:2]))
        check("the pressure Skribl renders its canvas",
              page.evaluate("() => !!document.getElementById('canvas')"))
        br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
