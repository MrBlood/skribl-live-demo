"""A looped stretch of pages: the server, both players, the editor's preview,
its draft and post, and the export all walk pages in the same order.

The owner, on Blooby's trading card as a Flip: page 1 draws the card, pages
2-8 are Blooby waving, and "is there a way to just keep it looping forever so
he just keeps waving? and it doesn't start over?" A document may carry one
`loop`: pages from..to (0-based, inclusive) on repeat, then the rest -- by
`times`, by `ms`, or `forever`, where the pages before it play once and the
stretch never ends. lib/holdtiming.js's plan() is the one answer every surface
asks, the same reason that module exists for `hold`.

THE FIXTURE CAN BE READ OFF THE SCREEN. Ten pages, each drawing one vertical
bar in its own column, so which page a player is showing is a question of
which column has ink at the canvas's middle row -- what is PAINTED, not what a
variable claims. Page 0 draws itself (the card); pages 1-8 are the loop; page
9 comes after it, and is the page a forever loop must never reach.

Calibrated red per component: the lib's plan ignoring the loop, the /s/
player ignoring it, the in-post player ignoring it (and wrapping to 0 on a
forever loop), the editor's preview ignoring it, the draft and the post body
dropping it, the export ignoring it, and the server accepting a bad loop.
"""
import json
import os
import sys

from assertions import make_check
import browsing
from playerready import await_player

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results)

W, H, N = 640, 460, 10
COLS = [30 + k * 60 for k in range(N)]       # page k inks column COLS[k]


def page(k, draw=False):
    x = COLS[k]
    pts = [{"x": x, "y": y, "t": (y - 100) * 2 if draw else 0, "color": "#ffffff", "size": 6}
           for y in range(100, 361, 20)]
    out = {"strokes": pts, "strokeGroups": [len(pts)]}
    if draw:
        out["draw"] = True
    return out


def doc(loop):
    d = {"title": "loop harness", "playbackMode": "flip", "fps": 12, "visibility": "public",
         "canvasSize": {"cssWidth": W, "cssHeight": H, "dpr": 1},
         "frames": [page(0, draw=True)] + [page(k) for k in range(1, N)]}
    if loop is not None:
        d["loop"] = loop
    return d


# Which page is on screen: the column with ink on the canvas's middle row.
# Records the sequence of pages, one entry per change, once per frame.
SAMPLER = """([sel, cols, w, ms]) => new Promise(done => {
  const cv = document.querySelector(sel); const seq = []; const t0 = performance.now();
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  (function tick(){
    const sx = cv.width / w, y = Math.floor(cv.height / 2);
    const row = ctx.getImageData(0, y, cv.width, 1).data; let hit = -1, hits = 0;
    cols.forEach((c, k) => { const x0 = Math.max(0, Math.floor((c - 5) * sx)), x1 = Math.min(cv.width - 1, Math.ceil((c + 5) * sx));
      for (let x = x0; x <= x1; x++) { const o = x * 4; if (row[o] + row[o+1] + row[o+2] > 300) { hit = k; hits++; break; } } });
    const pg = hits === 1 ? hit : -1;
    if (pg >= 0 && seq[seq.length - 1] !== pg) seq.push(pg);
    if (performance.now() - t0 < ms) requestAnimationFrame(tick); else done(seq);
  })(); })"""


def passes(seq):
    """Count how many times the stretch 1..8 ran between page 0 and page 9."""
    return sum(1 for a, b in zip(seq, seq[1:]) if a == 8 and b in (1, 9))


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 900, "height": 900})

    print("\nTHE SERVER — a loop is accepted on the clients' terms, and nothing else is")
    def post(body):
        r = ctx.request.post(BASE + "/api/skribls", data=body)
        return r.status, (r.json() if r.ok else r.text()[:160])
    st, forever = post(doc({"from": 1, "to": 8, "forever": True}))
    check("a forever loop posts", st in (200, 201), f"{st} {forever}")
    st, twice = post(doc({"from": 1, "to": 8, "times": 2}))
    check("a ×2 loop posts", st in (200, 201), f"{st} {twice}")
    st, plain = post(doc(None))
    check("a Flip with no loop posts as it always did", st in (200, 201), f"{st}")
    for bad, why in (({"from": 1, "to": 10, "times": 2}, "past the last page"),
                     ({"from": 4, "to": 2, "times": 2}, "from after to"),
                     ({"from": 1, "to": 8}, "no times, ms or forever"),
                     ({"from": 1, "to": 8, "times": 2, "forever": True}, "two kinds at once"),
                     ({"from": 1, "to": 8, "times": 9}, "times above the shared ceiling"),
                     ({"from": 1, "to": 8, "ms": 100}, "ms below the shared floor"),
                     ({"from": 1, "to": 8, "forever": 1}, "forever not literally true")):
        st, body = post(doc(bad))
        check(f"a loop {why} is refused", st == 400, f"{st} {body}")
    fid = forever.get("id") if isinstance(forever, dict) else None
    tid = twice.get("id") if isinstance(twice, dict) else None

    print("\nTHE /s/ PLAYER — forever never starts over; ×2 runs the stretch twice, then the rest")
    def watch_s(pid, ms):
        pg = ctx.new_page()
        browsing.goto(pg, BASE, f"/s/{pid}")
        await_player(pg, what="the loop fixture's player")
        pg.click("#playerPlayBtn")
        seq = pg.evaluate(SAMPLER, ["#canvas", COLS, W, ms])
        pg.close()
        return seq
    if fid:
        seq = watch_s(fid, 5000)
        after = seq[seq.index(1):] if 1 in seq else []
        check("/s/ forever: the card page plays first", bool(seq) and seq[0] == 0, str(seq[:12]))
        check("/s/ forever: after it, only the stretch -- never page 0 again, never page 9",
              bool(after) and all(1 <= k <= 8 for k in after), str(seq))
        check("/s/ forever: still waving five seconds in (several passes, no end)",
              passes(seq) >= 4, f"{passes(seq)} passes: {seq[-12:]}")
    if tid:
        seq = watch_s(tid, 2600)
        upto = seq[:seq.index(9) + 1] if 9 in seq else seq
        check("/s/ ×2: the stretch runs twice, then page 9",
              9 in seq and passes(upto) == 2, str(seq))

    print("\nTHE IN-POST PLAYER — the same answers on the feed")
    fp = ctx.new_page()
    browsing.goto(fp, BASE, "/feed")
    def watch_inline(pid, ms):
        try:     # the feed lists by fetch after load; wait for the post, not a clock
            fp.wait_for_function("(id) => !!(window.SkriblInline && window.SkriblInline.find(id))",
                                 arg=pid, timeout=8000)
        except Exception:
            return None
        fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').scrollIntoView({block:'center'})", pid)
        fp.wait_for_timeout(300)
        fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", pid)
        return fp.evaluate(SAMPLER, ['[data-skribl-id="' + pid + '"] .skribl-inline-canvas', COLS, W, ms])
    if fid:
        seq = watch_inline(fid, 5000)
        check("in-post: the forever fixture is on the feed", seq is not None)
        if seq is not None:
            after = seq[seq.index(1):] if 1 in seq else []
            check("in-post forever: after the card, only the stretch -- never page 0 again, never page 9",
                  bool(after) and all(1 <= k <= 8 for k in after) and passes(seq) >= 4, str(seq))
    if tid:
        seq = watch_inline(tid, 2600)
        if seq is not None:
            upto = seq[:seq.index(9) + 1] if 9 in seq else seq
            check("in-post ×2: the stretch runs twice, then page 9", 9 in seq and passes(upto) == 2, str(seq))
    fp.close()

    print("\nTHE EDITOR — its preview, its draft, its post body and its export")
    ep = ctx.new_page()
    browsing.goto(ep, BASE, "/flip")
    ep.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    ep.evaluate("""(d) => { frames = d.frames.map(f => ({ strokes: f.strokes.map(p => Object.assign({}, p)),
                     strokeGroups: f.strokeGroups.slice(), hold: 1, ...(f.draw ? { draw: true } : {}) }));
                   idx = 0; docLoop = { from: 1, to: 8, forever: true }; buildStrip(); render(); }""", doc(None))
    ep.evaluate("() => play()")
    seq = []
    for _ in range(50):          # the preview's own page index, every 100ms for 5s
        k = ep.evaluate("() => idx")
        if not seq or seq[-1] != k:
            seq.append(k)
        ep.wait_for_timeout(100)
    ep.evaluate("() => stop()")
    after = seq[seq.index(1):] if 1 in seq else []
    check("preview forever: after the card, only the stretch -- never page 0 again, never page 9",
          bool(after) and all(1 <= k <= 8 for k in after) and len(set(after)) >= 6, str(seq))
    body = ep.evaluate("() => buildSharePayload()")
    check("the post body carries the loop", isinstance(body, dict) and body.get("loop") == {"from": 1, "to": 8, "forever": True},
          str(body.get("loop") if isinstance(body, dict) else body))
    order = ep.evaluate("() => exportPageOrder(0, frames.length - 1)")
    check("the export walks the card once, then the stretch until ~10s, and never page 9",
          order[0] == 0 and order.count(0) == 1 and 9 not in order and order.count(1) >= 10, f"{len(order)} pages: {order[:12]}…")
    check("a range export ignores the loop",
          ep.evaluate("() => exportPageOrder(2, 5)") == [2, 3, 4, 5])
    ep.evaluate("() => saveNow()")
    ep.wait_for_timeout(300)
    browsing.goto(ep, BASE, "/flip")
    back = ep.evaluate("() => docLoop")
    check("the draft keeps the loop across a reload", back == {"from": 1, "to": 8, "forever": True}, str(back))
    ep.evaluate("() => { docLoop = null; saveNow(); }")
    ep.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
