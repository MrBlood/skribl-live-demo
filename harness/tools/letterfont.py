"""Read a posted letter sheet back into letters.

The letter sheet (skribl/static/editor_letters.js, /skribl-pad?letters=1)
ends by posting the whole set as one Skribl: every letter on one canvas, each
in a cell of a grid, one after another at the pace it was drawn. This turns
that post back into the 92 letters, each as strokes of (x, y, width, t) in
CAP HEIGHTS: x from the letter's ink centre, y up from its baseline, the
width the pen drew, and t in ms from the letter's first point.

    python3 harness/tools/letterfont.py https://<site>/s/<id> [out.json]
    python3 harness/tools/letterfont.py saved-payload.json [out.json]

THE LAYOUT RULE IS editor_letters.js's, repeated here (gridFor, composeSet):
cells CELL_W cap heights wide and 1 / (base - cap) tall, as big as the canvas
allows inside a margin of 4% of its shorter side, centred; each letter scaled
by its cap height, on its cell's baseline, centred on its own ink, its width
drawn at GAIN times its scale. verify_letters.py composes a set in the page
and reads it back with this file, so the two copies cannot part company
without that suite going red.

WHICH STROKES ARE WHOSE is not written anywhere in the post: a Skribl's
strokeGroups are per stroke, and bending them into per letter would change
what undo and the readers take them to mean. It is read back from where each
stroke sits, in order: the letters were posted one after another, so each
stroke belongs to the same letter as the one before it or the next, and the
split that puts every stroke's middle nearest its cell wins (a dynamic
programme, so one stroke drawn wide of its box cannot shift every letter
after it).
"""
import json
import math
import sys
import urllib.request

LINES = {"cap": 0.16, "x": 0.334, "base": 0.74, "desc": 0.94}
CELL_W = 1.4
GAIN = 5

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
DIGITS = "0123456789"
MARKS = ".,!?'\"-:;()&@#/+"
ACCENTS = ["´", "`", "¨", "~", "¸"]
AGAIN = "etaoinsrh"
# The 92 boxes in the order they are drawn and posted (editor_letters.js BOXES).
BOX_IDS = (list(LOWER) + list(UPPER) + list(DIGITS) + list(MARKS) + ACCENTS
           + [c + "2" for c in AGAIN])


def grid(W, H, n=len(BOX_IDS)):
    cell_h = 1 / (LINES["base"] - LINES["cap"])
    m = 0.04 * min(W, H)
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        cap = min((W - 2 * m) / (cols * CELL_W), (H - 2 * m) / (rows * cell_h))
        if best is None or cap > best["cap"] + 1e-9:
            best = {"cols": cols, "rows": rows, "cap": cap}
    best["cell_h"] = cell_h
    best["x0"] = (W - best["cols"] * CELL_W * best["cap"]) / 2
    best["y0"] = (H - best["rows"] * cell_h * best["cap"]) / 2
    return best


def cell(L, i):
    """Cell i: its rectangle, its middle and its baseline, in canvas units."""
    col, row = i % L["cols"], i // L["cols"]
    w, h = CELL_W * L["cap"], L["cell_h"] * L["cap"]
    left, top = L["x0"] + col * w, L["y0"] + row * h
    return {"left": left, "top": top, "right": left + w, "bottom": top + h,
            "cx": left + w / 2, "base": top + LINES["base"] * h}


def payload_of(doc):
    """A Skribl payload from an API envelope, a payload, or a saved file's text."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    if isinstance(doc, dict) and isinstance(doc.get("skribl"), dict):
        doc = doc["skribl"]
    return doc


def split_strokes(frame):
    pts = frame.get("strokes") or []
    groups = frame.get("strokeGroups") or []
    out, k = [], 0
    if groups and sum(groups) == len(pts):
        for n in groups:
            out.append(pts[k:k + n])
            k += n
        return out
    for p in pts:   # no usable groups: a stroke starts where a point says so
        if p.get("start") or not out:
            out.append([])
        out[-1].append(p)
    return out


def assign(strokes, cells):
    """Each stroke's letter, in order, every letter at least one stroke."""
    S, G = len(strokes), len(cells)
    if S < G:
        raise ValueError(f"{S} strokes cannot make {G} letters")
    mids = []
    for st in strokes:
        xs = [p["x"] for p in st]
        ys = [p["y"] for p in st]
        mids.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))

    def cost(k, i):
        c, (x, y) = cells[i], mids[k]
        dx = max(c["left"] - x, 0, x - c["right"])
        dy = max(c["top"] - y, 0, y - c["bottom"])
        return math.hypot(dx, dy)

    INF = float("inf")
    # best[k][i]: least cost for strokes 0..k with stroke k in letter i.
    best = [[INF] * G for _ in range(S)]
    came = [[0] * G for _ in range(S)]
    best[0][0] = cost(0, 0)
    for k in range(1, S):
        lo = max(0, G - (S - k))          # room left for the letters after
        for i in range(lo, min(G, k + 1)):
            stay = best[k - 1][i]
            step = best[k - 1][i - 1] if i else INF
            if stay <= step:
                best[k][i], came[k][i] = stay + cost(k, i), i
            else:
                best[k][i], came[k][i] = step + cost(k, i), i - 1
    if best[S - 1][G - 1] == INF:
        raise ValueError("no way to give every letter a stroke")
    out, i = [0] * S, G - 1
    for k in range(S - 1, -1, -1):
        out[k] = i
        i = came[k][i]
    return out, best[S - 1][G - 1]


def decode(doc):
    payload = payload_of(doc)
    frame = (payload.get("frames") or [payload])[0]
    size = payload.get("canvasSize") or {}
    W, H = size.get("cssWidth"), size.get("cssHeight")
    if not W or not H:
        raise ValueError("the post does not say its canvas size")
    L = grid(W, H)
    cells = [cell(L, i) for i in range(len(BOX_IDS))]
    strokes = split_strokes(frame)
    owner, total = assign(strokes, cells)
    letters = {}
    for st, i in zip(strokes, owner):
        letters.setdefault(BOX_IDS[i], []).append(st)
    out = {}
    for i, bid in enumerate(BOX_IDS):
        c, sts = cells[i], letters.get(bid, [])
        t0 = sts[0][0].get("t", 0) if sts else 0
        out[bid] = [[[round((p["x"] - c["cx"]) / L["cap"], 5),
                      round((c["base"] - p["y"]) / L["cap"], 5),
                      round(p.get("size", 0) / (GAIN * L["cap"]), 6),
                      int(round(p.get("t", 0) - t0))] for p in st] for st in sts]
    return {"letters": out, "order": BOX_IDS, "lines": LINES,
            "misfit": round(total / L["cap"], 4)}


def fetch(url):
    """A /s/<id> link, or an /api/skribls/<id> one, as the post's JSON."""
    if "/s/" in url and "/api/" not in url:
        base, pid = url.split("/s/", 1)
        url = base.rstrip("/") + "/api/skribls/" + pid.split("?")[0].split("#")[0].strip("/")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    doc = fetch(src) if src.startswith(("http://", "https://")) else open(src, encoding="utf-8").read()
    res = decode(doc)
    text = json.dumps(res, ensure_ascii=False, separators=(",", ":"))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    n = sum(len(v) for v in res["letters"].values())
    print(f"{len(res['letters'])} letters, {n} strokes, misfit {res['misfit']} cap heights")
