"""The page underneath: one page painted, complete, beneath a range of pages --
on the server, both players, the editor's preview and its export, the draft
and the post.

The owner, on Blooby's trading card as a Flip: the card is drawn once on page
1 and stays under the waving pages, "rasterized" as it plays rather than
copied onto every page. A document may carry one `under`: page `page` beneath
pages `from`..`to` (0-based, inclusive). lib/holdtiming.js underOf() is the
shape every surface accepts, validation.py's exactly (verify_sharedrules).

THE FIXTURE CAN BE READ OFF THE SCREEN, as verify_loop's can. Page 0 (the
card) is one horizontal bar along CARD_Y; pages 1-4 each draw one vertical bar
in their own column, clear of that row. under = page 0 beneath pages 1-3, so
page 4 is OUTSIDE the range and must show no card. Which page is up is the
column with ink on the middle row; whether the card is under it is the share
of the card row that has ink -- what is PAINTED, not what a variable claims.

Page 1 DRAWS ITSELF, so the drawing-page path (a page revealed stroke by
stroke) is asked as well as the still one. Page 2 carries an ERASER stroke
straight along the card row: in the editor page ink is its own layer, so a
page's eraser reveals what is under it and never cuts it. A player that paints
the card onto the same layer as the page's ink fails exactly there -- the
/s/ player paints straight onto its visible canvas, which is why it puts the
card in behind the ink (destination-over) instead.

Calibrated red per component: the lib refusing every `under`; the /s/ player
not painting it; the /s/ player painting it OVER the ink, where the eraser
cuts it; the in-post player not painting it; the editor's preview not painting
it (paintUnder and the drawing-page path, renderPartial, each alone); the
export not painting it; the draft and the post body dropping it; the editor's
editing view painting it at full strength; and the server accepting a bad one.
"""
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

W, H, N = 640, 460, 5
CARD_Y = 400
COLS = [0, 150, 270, 390, 510]        # page k (k >= 1) inks column COLS[k]
UNDER = {"page": 0, "from": 1, "to": 3}


def stroke(pts):
    return [dict(p, start=(i == 0)) for i, p in enumerate(pts)]


def card():
    pts = stroke([{"x": x, "y": CARD_Y, "t": 0, "color": "#ffffff", "size": 8} for x in range(40, 601, 20)])
    return {"strokes": pts, "strokeGroups": [len(pts)]}


def page(k, draw=False, erase=False):
    pts = stroke([{"x": COLS[k], "y": y, "t": (y - 100) * 3 if draw else 0, "color": "#ffffff", "size": 6}
                  for y in range(100, 301, 20)])
    groups = [len(pts)]
    if erase:   # straight along the card row: it must reveal the card, not cut it
        er = stroke([{"x": x, "y": CARD_Y, "t": 700, "color": "#ffffff", "size": 24, "erase": True}
                     for x in range(40, 601, 20)])
        pts += er
        groups.append(len(er))
    out = {"strokes": pts, "strokeGroups": groups}
    if draw:
        out["draw"] = True
    return out


def doc(under):
    d = {"title": "under harness", "playbackMode": "flip", "fps": 6, "visibility": "public",
         "canvasSize": {"cssWidth": W, "cssHeight": H, "dpr": 1},
         "frames": [card(), page(1, draw=True), page(2, erase=True), page(3), page(4)]}
    if under is not None:
        d["under"] = under
    return d


# Per frame: which page is up (the column with ink on the middle row) and how
# much of the card row has ink, plus the brightest card-row pixel. One record
# per page per distinct reading.
# `w`/`h` are the canvas's LOGICAL size: the fixture's on the players, which
# fit the post's canvasSize, and the editor's own page size (CW x CH) there,
# since the fixture's points are written into its pages unscaled.
SAMPLER = """([sel, cols, w, h, cardY, ms]) => new Promise(done => {
  const cv = document.querySelector(sel); const seen = {}; const t0 = performance.now();
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  (function tick(){
    const sx = cv.width / w, sy = cv.height / h;
    const mid = ctx.getImageData(0, Math.floor(200 * sy), cv.width, 1).data;
    const row = ctx.getImageData(0, Math.floor(cardY * sy), cv.width, 1).data;
    let pg = -1, hits = 0;
    for (let k = 1; k < cols.length; k++) {
      const x0 = Math.floor((cols[k] - 4) * sx), x1 = Math.ceil((cols[k] + 4) * sx);
      for (let x = x0; x <= x1; x++) { const o = x * 4; if (mid[o] + mid[o+1] + mid[o+2] > 300) { pg = k; hits++; break; } }
    }
    let inked = 0, total = 0, peak = 0;
    for (let X = 60; X <= 580; X += 8) { const o = Math.floor(X * sx) * 4; total++;
      const v = row[o] + row[o+1] + row[o+2]; if (v > peak) peak = v; if (v > 300) inked++; }
    const card = inked / total;
    const key = (hits === 1 ? pg : (card > 0.5 ? 0 : -1));
    if (key >= 0) { const r = seen[key] || (seen[key] = { min: 1, max: 0, peak: 0, n: 0 });
      r.min = Math.min(r.min, card); r.max = Math.max(r.max, card); r.peak = Math.max(r.peak, peak); r.n++; }
    if (performance.now() - t0 < ms) requestAnimationFrame(tick); else done(seen);
  })(); })"""


def judge(where, seen):
    """Pages 1-3 show the card under them on every frame; page 4 never does."""
    check(f"{where}: every page was seen", all(str(k) in seen for k in (1, 2, 3, 4)), str(seen))
    for k in (1, 2, 3):
        r = seen.get(str(k))
        check(f"{where}: page {k + 1} has the card under it, on every frame it is up"
              + (" (it draws itself)" if k == 1 else " (its eraser runs along the card)" if k == 2 else ""),
              bool(r) and r["min"] > 0.8, str(r))
    r = seen.get("4")
    check(f"{where}: page 5 is outside the range, and shows no card", bool(r) and r["max"] < 0.05, str(r))


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 900, "height": 900})

    print("\nTHE SERVER — an `under` is accepted on the clients' terms, and nothing else is")
    def post(body):
        r = ctx.request.post(BASE + "/api/skribls", data=body)
        return r.status, (r.json() if r.ok else r.text()[:160])
    st, made = post(doc(UNDER))
    check("a Flip with a page underneath posts", st in (200, 201), f"{st} {made}")
    for bad, why in (({"page": 2, "from": 1, "to": 3}, "under one of its own pages"),
                     ({"page": 0, "from": 1, "to": 5}, "past the last page"),
                     ({"page": 5, "from": 1, "to": 3}, "naming a page that is not there"),
                     ({"page": 0, "from": 3, "to": 1}, "from after to"),
                     ({"page": 0, "from": 1, "to": 3, "x": 1}, "with an unknown key"),
                     ({"page": True, "from": 1, "to": 3}, "with a page that is not a number")):
        st, body = post(doc(bad))
        check(f"an `under` {why} is refused", st == 400, f"{st} {body}")
    pid = made.get("id") if isinstance(made, dict) else None

    print("\nTHE /s/ PLAYER — the card under pages 2-4, through the eraser, and not under page 5")
    if pid:
        pg = ctx.new_page()
        browsing.goto(pg, BASE, f"/s/{pid}")
        await_player(pg, what="the under fixture's player")
        pg.click("#playerPlayBtn")
        judge("/s/", pg.evaluate(SAMPLER, ["#canvas", COLS, W, H, CARD_Y, 4500]))
        pg.close()

    print("\nTHE IN-POST PLAYER — the same answers on the feed")
    if pid:
        fp = ctx.new_page()
        browsing.goto(fp, BASE, "/feed")
        try:
            fp.wait_for_function("(id) => !!(window.SkriblInline && window.SkriblInline.find(id))",
                                 arg=pid, timeout=8000)
            found = True
        except Exception:
            found = False
        check("in-post: the fixture is on the feed", found)
        if found:
            fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').scrollIntoView({block:'center'})", pid)
            fp.wait_for_timeout(300)
            fp.evaluate("(id) => document.querySelector('[data-skribl-id=\"' + id + '\"]').click()", pid)
            judge("in-post", fp.evaluate(SAMPLER, ['[data-skribl-id="' + pid + '"] .skribl-inline-canvas',
                                                   COLS, W, H, CARD_Y, 4500]))
        fp.close()

    print("\nTHE EDITOR — its preview, its editing view, its export, its draft and its post body")
    ep = ctx.new_page()
    browsing.goto(ep, BASE, "/flip")
    ep.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    # On the dark canvas, picked: a new Flip starts on the theme's ground, Paper
    # in this browser's light scheme (lib/canvasground.js), and SAMPLER reads
    # the fixture's white ink as brightness standing above a dark ground.
    ep.evaluate("() => setBg('#0d0f14')")
    ep.evaluate("""(d) => { frames = d.frames.map(f => ({ strokes: f.strokes.map(p => Object.assign({}, p)),
                     strokeGroups: f.strokeGroups.slice(), hold: 1, ...(f.draw ? { draw: true } : {}) }));
                   idx = 0; docUnder = d.under; buildStrip(); render(); }""", doc(UNDER))
    ep.evaluate("() => play()")
    cw, ch = ep.evaluate("() => [CW, CH]")
    judge("preview", ep.evaluate(SAMPLER, ["#pad", COLS, cw, ch, CARD_Y, 4500]))
    ep.evaluate("() => stop()")

    # Editing page 4 (index 3): the card is a guide, FAINT, behind the page.
    # Its brightest pixel on the card row is well under the one a viewer gets.
    played = ep.evaluate("""() => { const c = document.createElement('canvas'); c.width = CW; c.height = CH;
        const x = c.getContext('2d'); drawFrameTo(x, frames[2]);
        const d = x.getImageData(320, """ + str(CARD_Y) + """, 1, 1).data; return d[0] + d[1] + d[2]; }""")
    ep.evaluate("() => { idx = 3; render(); }")
    # BETWEEN TWO BOUNDS: dimmer than a viewer's card, and clearly brighter
    # than the bare ground beside it. The first draft asked only "dimmer than
    # played", and an editing view with no card at all passed it.
    editing, ground = ep.evaluate("""() => { const c = document.getElementById('pad'), x = c.getContext('2d');
        const at = X => { const d = x.getImageData(Math.floor(X * c.width / CW), Math.floor(""" + str(CARD_Y) + """ * c.height / CH), 1, 1).data;
          return d[0] + d[1] + d[2]; };
        return [at(320), at(720)]; }""")
    check("editing a page in the range, the card shows FAINTLY behind it, a guide and not ink",
          played > 0 and ground + 60 < editing < played * 0.7,
          f"card-row brightness editing {editing}, bare ground {ground}, played {played}")

    # The export: a page in the range carries the card, through its eraser; a
    # page outside does not. drawFrameTo is asked as the PNG export and the
    # share and library cards ask it -- outside play and without `exporting`
    # set -- which is where a first draft painted a FAINT card: the editing
    # view's guide, leaking into files a viewer gets.
    ex = ep.evaluate("""() => { const out = {};
        for (const i of [2, 4]) { const c = document.createElement('canvas'); c.width = CW; c.height = CH;
          const x = c.getContext('2d'); drawFrameTo(x, frames[i]);
          const row = x.getImageData(0, """ + str(CARD_Y) + """, CW, 1).data; let ink = 0, n = 0;
          for (let X = 60; X <= 580; X += 8) { n++; const o = X * 4; if (row[o] + row[o+1] + row[o+2] > 300) ink++; }
          out[i] = ink / n; }
        return out; }""")
    check("the export paints the card WHOLE under a page in the range, through that page's eraser",
          ex.get("2", 0) > 0.8, str(ex))
    check("...and not under a page outside it", ex.get("4", 1) < 0.05, str(ex))

    body = ep.evaluate("() => buildSharePayload()")
    check("the post body carries the page underneath",
          isinstance(body, dict) and body.get("under") == UNDER, str(body.get("under") if isinstance(body, dict) else body))
    ep.evaluate("() => saveNow()")
    ep.wait_for_timeout(300)
    browsing.goto(ep, BASE, "/flip")
    back = ep.evaluate("() => docUnder")
    check("the draft keeps it across a reload", back == UNDER, str(back))
    ep.evaluate("() => { docUnder = null; saveNow(); }")
    ep.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
