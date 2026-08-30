"""v238 — Stamps: the clipboard, grown up.

WHAT WAS ALREADY THERE. Flip has had a selection clipboard since v219: Cut
remembers, Paste puts it back. Three things stopped it being the thing an
animator actually wants. It held ONE entry, so the second thing you copied
destroyed the first. It died with the tab, so an asset built on Monday was gone
on Tuesday. And Paste put the artwork back where it came from, which is right
for paste and useless for reuse — the whole point of reusing a drawing is
putting it somewhere else.

Stamps are those three properties and nothing else: persistent, multi-slot,
placed where you tap. No new primitive enters the format — a placed stamp is
ordinary stroke groups, exactly what Paste appends — so a Skribl made with
stamps opens in a player that predates them. That is asserted here, because it
is the property most likely to be lost by a later "improvement" that decides a
stamp should be a referenced instance rather than a copy.

THE ASSERTION THAT MATTERS MOST is not about placement, it is about the SHELF'S
BUDGET, and the reason is v231. localStorage is ONE ~5 MB allowance for the
whole origin. Flip's draft grew to 2.7 MB of it and the Pad's autosave — an
unrelated feature on an unrelated page — started failing, with nothing in either
feature mentioning the other. A stamp shelf is the same trap by construction: it
only ever grows, because every stamp you save stays until you delete it. So the
shelf has a byte budget, it refuses rather than evicting, and it lives in its own
key so a failure to save a stamp can never take the drawing down with it. All
three are asserted below, and all three are invisible in a screenshot.

WHY IT REFUSES INSTEAD OF EVICTING. Dropping the oldest stamp to make room is
the obvious design and it is the amber-pill failure over again: the user's work
disappearing with no event they can connect it to. A stamp is something they
deliberately made. Losing one has to be their decision.
"""
import os
import sys

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                    # pragma: no cover
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


SNAP = """() => { const f = frame();
  return { pts: f.strokes.length, groups: f.strokeGroups.length,
           xs: f.strokes.map(p => Math.round(p.x * 10) / 10),
           ys: f.strokes.map(p => Math.round(p.y * 10) / 10),
           sizes: f.strokes.map(p => p.size),
           cols: f.strokes.map(p => p.color) }; }"""


def draw_fixture(page, cx, cy):
    """TWO strokes, and a zigzag rather than a line. Both halves of that are
    load-bearing, and each was found by a mutation that a simpler fixture let
    through.

    A horizontal line makes every placement assertion pass on a build that
    ignores the y offset entirely — hence the zigzag, which has real extent in
    both axes.

    ONE stroke makes the undo assertion pass on a build that records `groups: 1`
    instead of the real count, because with one group the two are the same
    number. That is the bug the undo contract exists to prevent: a placement of
    forty groups that needs forty undos. A second stroke is the difference
    between a suite that tests the contract and a suite that agrees with it."""
    page.mouse.move(cx - 60, cy - 30)
    page.mouse.down()
    for i in range(1, 11):
        page.mouse.move(cx - 60 + i * 12, cy - 30 + (24 if i % 2 else -24))
    page.mouse.up()
    page.wait_for_timeout(200)
    page.mouse.move(cx - 40, cy + 60)
    page.mouse.down()
    for i in range(1, 7):
        page.mouse.move(cx - 40 + i * 14, cy + 60 + (14 if i % 2 else -14))
    page.mouse.up()
    page.wait_for_timeout(300)


def select_all(page, cx, cy):
    page.evaluate("() => setTool('select')")
    page.wait_for_timeout(200)
    page.mouse.move(cx - 240, cy - 200)
    page.mouse.down()
    page.mouse.move(cx + 240, cy + 200)
    page.mouse.up()
    page.wait_for_timeout(400)


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(700)

        print("\nTHE LIB — pure, and it knows nothing about frames")
        check("lib/stamps.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblStamps") == "object",
              "a lib the template does not list is a lib that does not exist")
        check("stamp is in Flip's tool registry",
              "stamp" in page.evaluate("() => SkriblFlipTools.list()"),
              str(page.evaluate("() => SkriblFlipTools.list()")))

        # ROUND TRIP THROUGH THE CENTRE. A stamp stores offsets from its own
        # bounding-box centre, which is what makes the tap point the anchor and
        # what makes a stamp captured on one page size land sensibly on another.
        rt = page.evaluate("""() => {
          const S = window.SkriblStamps;
          const runs = [[{x: 100, y: 200, color: '#ff0000', size: 4, erase: false},
                         {x: 140, y: 260, color: '#00ff00', size: 6, erase: false}]];
          const st = S.fromRuns(runs);
          const out = S.toRuns(st, 500, 500, 1, 0);
          return { w: st.w, h: st.h, cols: st.c.length,
                   a: out[0][0], b: out[0][1],
                   json: JSON.stringify(st).length };
        }""")
        check("a stamp records its own extent, not its old position",
              rt["w"] == 40 and rt["h"] == 60, str(rt))
        check("placing it centres the ORIGINAL bounding box on the tap",
              rt["a"]["x"] == 480 and rt["a"]["y"] == 470
              and rt["b"]["x"] == 520 and rt["b"]["y"] == 530,
              f"{rt['a']} / {rt['b']} — anchored anywhere but the centre and a "
              "stamp lands beside the finger that placed it")
        check("colours survive the colour table",
              rt["a"]["color"] == "#ff0000" and rt["b"]["color"] == "#00ff00",
              f"{rt['a']['color']} / {rt['b']['color']} — the table is a size "
              "optimisation and must be invisible in the output")
        # `start` is DERIVED and `t` is REGENERATED, both on purpose. A recording
        # timestamp carried across sessions places a stroke in the timeline of a
        # drawing that no longer exists.
        check("the first point of a run is marked as a start",
              rt["a"]["start"] is True and rt["b"]["start"] is False,
              f"{rt['a']['start']} / {rt['b']['start']} — paintStatic reads "
              "`start`; a run without one is not a stroke")

        scaled = page.evaluate("""() => {
          const S = window.SkriblStamps;
          const st = S.fromRuns([[{x: 0, y: 0, color: '#000', size: 8},
                                  {x: 40, y: 0, color: '#000', size: 8}]]);
          const half = S.toRuns(st, 100, 100, 0.5, 0)[0];
          return { dx: half[1].x - half[0].x, size: half[0].size };
        }""")
        # THE ONE A "SIMPLIFICATION" WOULD TAKE OUT. Scaling only the geometry
        # is easier and gives you the same drawing with a fatter pen, which
        # reads as a different stamp rather than a smaller one.
        check("scaling a stamp scales its STROKE WIDTHS too",
              scaled["dx"] == 20 and scaled["size"] == 4,
              f"span {scaled['dx']}, size {scaled['size']} — geometry-only "
              "scaling makes a half-size stamp look like a different drawing "
              "done with the same pen")

        print("\nTHE BUDGET — v231's lesson, applied before it bites again")
        budget = page.evaluate("""() => {
          const S = window.SkriblStamps;
          const one = S.fromRuns([[{x:0,y:0,color:'#000',size:2},
                                   {x:9,y:9,color:'#000',size:2}]]);
          const full = []; for (let i = 0; i < S.MAX_SLOTS; i++) full.push(one);
          const big = []; for (let i = 0; i < S.MAX_POINTS + 10; i++)
            big.push({x: i, y: 0, color: '#000', size: 2});
          return { slots: S.MAX_SLOTS, bytes: S.MAX_BYTES,
                   emptyOk: S.fits([], one),
                   whenFull: S.fits(full, one),
                   oversize: S.fromRuns([big]),
                   key: S.KEY };
        }""")
        check("the shelf has a BYTE budget, not just a slot count",
              isinstance(budget["bytes"], int) and 0 < budget["bytes"] <= 1024 * 1024,
              f"{budget['bytes']} bytes of a ~5 MB origin — slots are a proxy "
              "for size and a bad one: one traced outline is worth fifty doodles")
        check("a stamp fits an empty shelf", budget["emptyOk"] is None)
        check("a FULL shelf refuses rather than evicting",
              budget["whenFull"] == "full",
              f"{budget['whenFull']} — dropping the oldest stamp to fit a new "
              "one loses work the user deliberately made, with no event they "
              "could connect it to")
        check("one enormous stamp cannot be made at all",
              budget["oversize"] is None,
              "without a per-stamp cap, one traced photograph fills the budget "
              "and every later save is refused for a reason that points at the "
              "shelf rather than at the stamp that ate it")
        # ITS OWN KEY. Not a corner of the draft: a stamp must not ride into a
        # shared Skribl, clearing a drawing must not clear the assets built for
        # it, and a shelf that will not write must not take the drawing with it.
        check("the shelf lives in its own storage key",
              budget["key"] == "skribl_stamps" and "flip" not in budget["key"],
              f"{budget['key']}")

        # A corrupt or downgraded slot costs ITS OWN slot, not the shelf. This is
        # the failure mode of every localStorage feature in this project that has
        # ever gone wrong at a version boundary.
        rot = page.evaluate("""() => {
          const S = window.SkriblStamps;
          const good = S.fromRuns([[{x:0,y:0,color:'#000',size:2},{x:5,y:5,color:'#000',size:2}]]);
          return { junk: S.decode('not json at all').length,
                   nonArray: S.decode('{"v":1}').length,
                   mixed: S.decode(JSON.stringify([good, {v: 99}, null, good])).length };
        }""")
        check("a corrupt shelf decodes to empty rather than throwing",
              rot["junk"] == 0 and rot["nonArray"] == 0, str(rot))
        check("one bad entry costs its own slot, not the shelf",
              rot["mixed"] == 2,
              f"{rot['mixed']} of 2 good entries survived alongside 2 bad ones")

        print("\nSAVING — the only route in is a selection")
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        draw_fixture(page, cx, cy)
        drawn = page.evaluate(SNAP)
        select_all(page, cx, cy)
        check("the selection bar offers Stamp",
              page.locator("#sbStamp").is_visible(),
              "a stamp is made out of a selection and out of nothing else, "
              "which is why the save lives here and not in the shelf")
        page.locator("#sbStamp").click()
        page.wait_for_timeout(400)
        shelf = page.evaluate("() => ({ n: stampShelf.length, armed: stampArmed })")
        check("saving puts one stamp on the shelf",
              shelf["n"] == 1, str(shelf))
        check("...and arms it",
              shelf["armed"] == 0,
              "the stamp you just made is the one you are about to place")
        check("saving does not alter the page it was taken from",
              page.evaluate(SNAP)["pts"] == drawn["pts"],
              "Stamp is a copy; Cut is the one that removes")
        check("the shelf reaches localStorage",
              page.evaluate("() => (localStorage.getItem('skribl_stamps') || '').length") > 20,
              "a shelf that lives only in memory is the clipboard again")

        print("\nPLACING — a tap, and one undo takes it back")
        page.evaluate("() => setTool('stamp')")
        page.wait_for_timeout(300)
        check("choosing the tool opens the shelf",
              page.locator("#stampPop").is_visible(),
              "the picker opens from the tool's own button — the shape picker "
              "learned this the hard way when the tray became a second route")
        check("the shelf shows a thumbnail per stamp",
              page.locator("#stampGrid canvas").count() == 1,
              "a hand-drawn asset is recognised by sight; asking for a name at "
              "save time is a keyboard on a phone in the middle of drawing")
        before = page.evaluate(SNAP)
        page.mouse.click(cx + 150, cy + 120)
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        check("a tap places the armed stamp",
              after["pts"] > before["pts"]
              and after["groups"] - before["groups"] == 2,
              f"{before['pts']}/{before['groups']} -> {after['pts']}/{after['groups']} "
              "— the fixture is two strokes on purpose, so the group count is "
              "the thing being checked and not a tautology")
        # NOTHING NEW ENTERS THE FORMAT. A placed stamp is ordinary stroke
        # groups: the groups must still sum to the point count or the server
        # refuses the share, and every point must carry the seven fields the
        # player reads and no others.
        shape = page.evaluate("""() => {
          const f = frame();
          let sum = 0; for (const g of f.strokeGroups) sum += g;
          const keys = Object.keys(f.strokes[f.strokes.length - 1]).sort();
          return { sum: sum, pts: f.strokes.length, keys: keys };
        }""")
        check("the groups still sum to the point count",
              shape["sum"] == shape["pts"],
              f"{shape['sum']} vs {shape['pts']} — the server refuses a share "
              "whose groups disagree with its strokes")
        check("a placed point carries the format's fields and no others",
              shape["keys"] == ["color", "erase", "size", "start", "t", "x", "y"],
              f"{shape['keys']} — a stamp that needed a new field would be a "
              "format change the player has to honour")
        # PLACED WHERE YOU TAPPED, which is the entire difference from Paste.
        landed = page.evaluate("""([n]) => {
          const f = frame(), s = f.strokes.slice(f.strokes.length - n);
          let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
          for (const p of s) { if (p.x < x0) x0 = p.x; if (p.y < y0) y0 = p.y;
                               if (p.x > x1) x1 = p.x; if (p.y > y1) y1 = p.y; }
          return { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
        }""", [after["pts"] - before["pts"]])
        want = page.evaluate("([x,y]) => { const r = pad.getBoundingClientRect();"
                             " return { x: (x - r.left) * CW / r.width,"
                             "          y: (y - r.top) * CH / r.height }; }",
                             [cx + 150, cy + 120])
        check("it lands centred on the tap, not back where it came from",
              abs(landed["cx"] - want["x"]) < 3 and abs(landed["cy"] - want["y"]) < 3,
              f"{landed} vs tap {want} — putting it back where it was is Paste, "
              "which already exists")

        # ONE TAP IS ONE UNDO. The placement lands as many groups, which is right
        # for the payload and wrong for the editor: popping fifty groups to take
        # back one tap is not undo. Fill states the same contract.
        page.evaluate("() => undoStroke()")
        page.wait_for_timeout(400)
        u = page.evaluate(SNAP)
        check("ONE undo takes back the whole placement",
              u["pts"] == before["pts"] and u["groups"] == before["groups"],
              f"{u['pts']}/{u['groups']} vs {before['pts']}/{before['groups']} "
              "— a stamp of forty groups that needs forty undos is not one action")
        page.evaluate("() => redoStroke()")
        page.wait_for_timeout(400)
        r = page.evaluate(SNAP)
        check("...and one redo puts it back exactly",
              r["xs"] == after["xs"] and r["ys"] == after["ys"]
              and r["cols"] == after["cols"] and r["sizes"] == after["sizes"],
              "redo restores COORDINATES; re-running the placement would land "
              "it wherever the tap happens to be now")

        print("\nTHE SHELF SURVIVES A RELOAD — the point of the whole feature")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(900)
        check("the stamp is still there after a reload",
              page.evaluate("() => stampShelf.length") == 1,
              "a clipboard that outlives the tab IS the feature; without this "
              "there is nothing here Cut and Paste did not already do")
        check("nothing is armed on a fresh load",
              page.evaluate("() => stampArmed") == -1,
              "an armed stamp across a reload turns the next tap on the canvas "
              "into a placement the user did not ask for")

        print("\nDELETING — and the index that goes stale when you do")
        # The reload above put the tool back to the pen, which closes the shelf
        # — setTool() derives that. Re-enter it, or the visibility assertion at
        # the end of this block is measuring the tool being off rather than the
        # empty state being on.
        page.evaluate("() => setTool('stamp')")
        page.wait_for_timeout(200)
        page.evaluate("""() => {
          const S = window.SkriblStamps;
          const mk = (n) => S.fromRuns([[{x:0,y:0,color:'#00' + n + '000',size:2},
                                         {x:9,y:9,color:'#00' + n + '000',size:2}]]);
          stampShelf = [mk(1), mk(2), mk(3)];
          stampArmed = 2; syncStampPop();
        }""")
        page.wait_for_timeout(200)
        check("the shelf renders one cell per stamp",
              page.locator("#stampGrid .stamp-cell").count() == 3,
              str(page.locator("#stampGrid .stamp-cell").count()))
        page.evaluate("() => stampDelete(0)")
        page.wait_for_timeout(200)
        # THE OFF-BY-ONE THAT WOULD SHIP. `stampArmed` is a position in a list
        # that just got shorter. Left alone, it arms whatever slid into the gap
        # — a different stamp than the one wearing the ring.
        st = page.evaluate("() => ({ n: stampShelf.length, armed: stampArmed })")
        check("deleting below the armed stamp keeps the SAME stamp armed",
              st["n"] == 2 and st["armed"] == 1,
              f"{st} — an index into a list that shrank points at a different "
              "stamp, and the ring in the shelf would say otherwise")
        page.evaluate("() => stampDelete(1)")
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ n: stampShelf.length, armed: stampArmed })")
        check("deleting the armed stamp disarms rather than re-aiming",
              st["armed"] == -1,
              f"{st} — silently arming the neighbour makes the next tap place "
              "something the user did not choose")
        page.evaluate("() => { stampShelf = []; SkriblStamps.store(null, []); syncStampPop(); }")
        page.wait_for_timeout(200)
        check("an empty shelf says what to do about it",
              page.locator("#stampEmpty").is_visible(),
              "an empty grid with no words is a broken feature; the only route "
              "in is Select then Stamp and nothing else on screen says so")

        print("\nTHE PAGE'S OWN BUDGET — the ceiling a tool that ADDS must respect")
        # The server refuses a frame over MAX_POINTS_PER_FRAME (20,000) and over
        # MAX_GROUPS_PER_FRAME (5,000). Liquify and the tween both carry long
        # comments about this and for the same reason: a tool that adds to a page
        # can make a drawing unpostable, and it does it SILENTLY — the user finds
        # out at the moment they try to share, with no way to connect the refusal
        # to the tap that caused it.
        page.evaluate("""() => {
          localStorage.clear();
          frames.length = 0;
          frames.push({ strokes: [], strokeGroups: [], hold: 1 });
          idx = 0;
          const f = frame(), now = performance.now();
          // Two points of headroom against a four-point stamp: the guard is a
          // `>`, so landing exactly ON the cap is allowed and a fixture that
          // does is testing the boundary rather than the refusal.
          for (let i = 0; i < STAMP_POINT_CAP - 2; i++)
            f.strokes.push({ x: 10 + (i % 100), y: 10 + ((i / 100) | 0), color: '#888888',
                             size: 2, t: now + i, erase: false, start: i === 0 });
          f.strokeGroups.push(STAMP_POINT_CAP - 2);
          stampShelf = [SkriblStamps.fromRuns(
            [[{x:0,y:0,color:'#00ffff',size:3},{x:20,y:0,color:'#00ffff',size:3}],
             [{x:0,y:9,color:'#00ffff',size:3},{x:20,y:9,color:'#00ffff',size:3}]])];
          stampArmed = 0; setTool('stamp'); syncStampPop();
        }""")
        page.wait_for_timeout(300)
        before = page.evaluate(SNAP)
        page.mouse.click(cx, cy)
        page.wait_for_timeout(400)
        after = page.evaluate(SNAP)
        # REFUSES WHOLE, and that is the half a naive guard gets wrong: trimming
        # the stamp to fit leaves a partial drawing on the page, which is worse
        # than not placing it, because it looks like something the user did.
        check("a page at its point budget refuses the whole stamp",
              after["pts"] == before["pts"] and after["groups"] == before["groups"],
              f"{before['pts']}/{before['groups']} -> {after['pts']}/{after['groups']} "
              "— over MAX_POINTS_PER_FRAME the server refuses the SHARE, so a "
              "tool that walks a page past it breaks the drawing at the one "
              "moment the user cannot connect to the tap that did it")
        check("...and says so rather than failing silently",
              "too full" in page.locator("#flipChip").text_content(),
              page.locator("#flipChip").text_content()
              + " — a tap that does nothing and says nothing reads as a broken "
                "tool")
        page.evaluate("() => { localStorage.clear(); }")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        b = page.locator("#pad").bounding_box()
        cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

        print("\nA TAP WITH NOTHING ARMED IS A NO-OP, NOT AN ACCIDENT")
        # THE SHELF IS DELIBERATELY NOT EMPTY HERE. Run against an empty shelf
        # this assertion passes on a build that quietly arms slot 0 for you,
        # because there is no slot 0 to arm — which is the same too-easy-fixture
        # failure the two-stroke drawing above answers.
        page.evaluate("""() => {
          stampShelf = [SkriblStamps.fromRuns(
            [[{x:0,y:0,color:'#ff00ff',size:3},{x:20,y:20,color:'#ff00ff',size:3}]])];
          stampArmed = -1; setTool('stamp'); syncStampPop();
        }""")
        page.wait_for_timeout(300)
        before = page.evaluate(SNAP)
        page.mouse.click(cx, cy - 100)
        page.wait_for_timeout(300)
        check("tapping with a stamp on the shelf but none ARMED changes nothing",
              page.evaluate(SNAP)["pts"] == before["pts"],
              "the tool is also the shelf's open/close button, so a stray tap "
              "on the canvas while browsing must not lay artwork — and arming "
              "the first slot 'helpfully' is how it would")

        check("no page error through any of it", not errs, "; ".join(errs[:2]))
    finally:
        br.close()


# ============================================================================
# FINDING THE STAMP BUTTON AT ALL
#
# Reported from the live demo: "I didn't know where the stamp was so I kept
# pushing stamp in the tool menu. I didn't see the stamp button."
#
# Three separate things sent them there, and all three had to go:
#
#   1. The empty shelf said "tap Stamp to save it here" while the shelf was
#      OPEN -- and the button it names lives in the SELECTION bar, which does
#      not exist until something is selected. The instruction was displayed at
#      the one moment its target could not be on screen.
#   2. "Stamp" names two things. The tray has a tool called Stamps, which is
#      where the word IS visible, so the sentence pointed at the wrong control.
#   3. Below the "regular" size class .pb-tx is display:none, so on a phone the
#      selection bar is icons only and NO button is labelled "Stamp" at all.
#      The sentence named a label the surface does not render.
#
# So the shelf now offers the step that has to come first, and the button is
# pointed at rather than described.
# ============================================================================
print("\nDISCOVERY — the route into the shelf has to be findable")
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    try:
        # A PHONE-WIDTH VIEWPORT ON PURPOSE. This is the size where the labels
        # vanish, so a desktop-width test would pass while the reported bug
        # stood.
        pg = _b.new_page(viewport={"width": 430, "height": 900})
        pg.goto(BASE + "/flip", wait_until="load")
        pg.wait_for_timeout(1200)
        pg.evaluate("() => localStorage.clear()")
        pg.reload(wait_until="load")
        pg.wait_for_timeout(1200)

        labels = pg.evaluate(
            "() => getComputedStyle(document.querySelector('#sbStamp .pb-tx')).display")
        check("the selection bar really is icons-only at this width",
              labels == "none",
              f"display:{labels} — if labels show here this suite is testing the "
              "wrong surface and the reported bug cannot reproduce")

        pg.evaluate("() => setTool('stamp')")
        pg.wait_for_timeout(400)
        empty = pg.evaluate(
            "() => { const e = document.getElementById('stampEmpty');"
            " return { shown: !e.hidden,"
            " text: e.textContent.replace(/\\s+/g, ' ').trim() }; }")
        check("an empty shelf explains itself", empty["shown"], str(empty))
        check("...and no longer says to tap a word that is not on screen",
              "tap Stamp" not in empty["text"],
              f"{empty['text']!r} — that label is display:none at this width")
        check("...and shows the button's GLYPH inside the sentence",
              pg.evaluate("() => !!document.querySelector"
                          "('#stampEmpty .stamp-empty-ic svg')"),
              "a picture to match against a picture; the word is not rendered")
        check("...while still reading correctly to a screen reader",
              "stamp button" in empty["text"],
              f"{empty['text']!r} — the glyph is aria-hidden, so without this "
              "the sentence ends mid-clause in speech")

        go = pg.query_selector("#stampEmptyGo")
        check("the empty shelf offers the step that comes first", go is not None,
              "a sentence telling someone to go and find a tool is what failed")
        # Guarded: a regression that deletes the button would otherwise time
        # out here and kill the suite AFTER its findings, which through a
        # failures-only filter looks like a clean pass of the mutation.
        if go:
            pg.click("#stampEmptyGo")
            pg.wait_for_timeout(400)
        check("...and tapping it actually switches to Select",
              bool(go) and pg.evaluate("() => flipTool") == "select",
              f"flipTool={pg.evaluate('() => flipTool')!r}"
              + ("" if go else " (no button to press)"))
        check("...and gets the shelf out of the way",
              pg.evaluate("() => document.getElementById('stampPop').hidden") is True,
              "the shelf cannot fill until a selection exists elsewhere")

        pg.evaluate("() => setTool('pen')")
        box = pg.eval_on_selector("#pad", "e => { const r = e.getBoundingClientRect();"
                                  " return { x: r.x, y: r.y, w: r.width, h: r.height }; }")
        pg.mouse.move(box["x"] + 50, box["y"] + 70)
        pg.mouse.down()
        for i in range(1, 12):
            pg.mouse.move(box["x"] + 50 + i * 14, box["y"] + 70 + (i % 2) * 26)
        pg.mouse.up()
        pg.wait_for_timeout(300)
        pg.evaluate("() => setTool('select')")
        pg.mouse.move(box["x"] + 30, box["y"] + 40)
        pg.mouse.down()
        for i in range(1, 10):
            pg.mouse.move(box["x"] + 30 + i * 22, box["y"] + 40 + i * 10)
        pg.mouse.up()
        pg.wait_for_timeout(700)

        check("the Stamp button is on screen once something is selected",
              pg.evaluate("() => { const b = document.getElementById('sbStamp');"
                          " return !!(b && b.offsetParent); }") is True,
              "the bar it lives in is created by the selection")
        check("and it is SPOTLIT, not merely present",
              pg.evaluate("() => document.getElementById('sbStamp')"
                          ".classList.contains('pb-spot')") is True,
              "naming it is what failed; pointing at it is what replaces that")
        hint = pg.evaluate("() => { const h = document.querySelector('.skribl-hint');"
                           " return h && !h.hidden ? h.textContent : ''; }")
        # The requirement is NOT a particular word. It is that the hint never
        # sends the reader to a label that is not drawn: below "regular" the
        # selection bar has none, and the word "Stamp" IS rendered in the tool
        # tray, so naming it points at the wrong control. Identification is the
        # glyph's job now -- asserted separately below -- which is why this no
        # longer insists on the word "highlighted" that used to carry it.
        check("the hint never names a label the surface does not draw",
              "tap Stamp" not in hint and "Stamp button" not in hint,
              f"{hint!r} — that phrasing sent the reader to the tool tray, "
              "where the word IS visible")
        check("the hint offers to do it for you", "Stamp it" in hint, f"{hint!r}")

        # THE TOAST MUST NOT EAT THE CANVAS UNDERNEATH IT. It is position:fixed
        # over the drawing, and while it was pointer-reactive it swallowed
        # anything aimed below it -- this hint made verify_select's rotation
        # drag miss its handle, because the toast was sitting on the handle.
        #
        # Asserted with elementFromPoint rather than by clicking, because the
        # suites dismiss hints with element.click(), which dispatches straight
        # to the node and ignores pointer-events entirely: a click-based check
        # would pass whether this were fixed or not.
        # h.contains(el), NOT the tag name. The first version of this check read
        # el.tagName and accepted "div" -- and the hint IS a div, so it passed
        # whether the fix was in place or not. Caught by mutating the CSS back
        # to pointer-events: auto and watching the suite stay green.
        thru = pg.evaluate(
            "() => { const h = document.querySelector('.skribl-hint');"
            " if (!h || h.hidden) return { up: false };"
            " const r = h.getBoundingClientRect();"
            " const el = document.elementFromPoint(r.left + r.width / 2,"
            "                                      r.top + r.height / 2);"
            " return { up: true, blocked: !!(el && h.contains(el)),"
            "          hit: el ? (el.id || el.className || el.tagName) : null }; }")
        check("the hint is actually on screen for this check to mean anything",
              thru["up"] is True, "no toast up — the assertion below is vacuous")
        check("a press in the middle of the hint reaches what is behind it",
              thru["up"] and thru["blocked"] is False,
              f"elementFromPoint lands on {thru.get('hit')!r}, inside the toast — "
              "it is intercepting the drawing surface")
        check("but its action button still takes a press",
              pg.evaluate("() => { const a = document.querySelector"
                          "('.skribl-hint-action');"
                          " return a ? getComputedStyle(a).pointerEvents : null; }")
              == "auto",
              "the panel opting out must not take the button with it")

        pg.click("#sbStamp")
        pg.wait_for_timeout(400)
        check("pressing the button ends the spotlight",
              pg.evaluate("() => document.getElementById('sbStamp')"
                          ".classList.contains('pb-spot')") is False,
              "a highlight that survives being obeyed is an alarm, not a hint")
        check("...and the press actually saved a stamp",
              pg.evaluate("() => stampShelf.length") == 1,
              f"shelf holds {pg.evaluate('() => stampShelf.length')}")

        # ONCE PER PERSON. It introduces the shelf; it does not nag.
        pg.evaluate("() => { stampShelf.length = 0; selSpans = []; selRect = null;"
                    " syncSelBar(); }")
        pg.evaluate("() => setTool('select')")
        pg.mouse.move(box["x"] + 30, box["y"] + 40)
        pg.mouse.down()
        for i in range(1, 10):
            pg.mouse.move(box["x"] + 30 + i * 22, box["y"] + 40 + i * 10)
        pg.mouse.up()
        pg.wait_for_timeout(600)
        check("the spotlight does not fire a second time",
              pg.evaluate("() => document.getElementById('sbStamp')"
                          ".classList.contains('pb-spot')") is False,
              "SkriblHints keeps the once-per-person promise, so the spotlight "
              "has to be tied to it rather than fired alongside it")
        pg.close()
    finally:
        _b.close()


# ============================================================================
# PUTTING THE SHELF AWAY, AND A RING THAT OUTLIVES ITS OWN EXPLANATION
#
# Reported from the live demo: "the stamp library doesn't go away until another
# tool is chosen."
#
# Press-again-to-close was WRITTEN and did not WORK, which is the interesting
# part. #stampToolBtn carried two click listeners: lib/toolshelf.js binds the
# cells it builds to the registry's setTool, and each surface ALSO bound every
# '#toolGroup .tool-btn' to its own. A deriving handler survives being run
# twice; a TOGGLING one does not. The registry's toggle closed the shelf and the
# surface's setTool re-derived it open in the same click.
#
# Two further traps, both hit while fixing it:
#   * the toggle read stampPop.hidden AFTER setTool had rederived it, so it saw
#     false every time and could only ever close -- shut on the second tap and
#     never back on the third;
#   * the spotlight ran its own 6000ms timer while an ACTION hint dwells
#     DURATION * 2 = 12400, so the ring went out six seconds before the sentence
#     calling it "the highlighted button" did.
# ============================================================================
print("\nSHELF DISMISSAL — and a ring tied to the sentence that explains it")
with sync_playwright() as _sp2:
    _sb = _sp2.chromium.launch()
    try:
        sp = _sb.new_page(viewport={"width": 430, "height": 900})
        sp.goto(BASE + "/flip", wait_until="load")
        sp.wait_for_timeout(1200)
        sp.evaluate("() => localStorage.clear()")
        sp.reload(wait_until="load")
        sp.wait_for_timeout(1200)

        hidden = lambda: sp.evaluate(
            "() => document.getElementById('stampPop').hidden")
        # THE TRAY FIRST, because the shelf is most-recently-used: Stamps has
        # no cell until it has been chosen once, and this is also the route a
        # person takes the first time. It is the re-tap of the promoted button
        # that carried two listeners.
        sp.click("#toolMoreBtn"); sp.wait_for_timeout(300)
        sp.click(".tool-tray-btn[data-tool='stamp']"); sp.wait_for_timeout(400)
        check("choosing Stamps opens the shelf", hidden() is False,
              f"flipTool={sp.evaluate('() => flipTool')!r}")
        check("...and it is promoted onto the shelf, so it can be re-tapped",
              sp.evaluate("() => { const b = document.getElementById"
                          "('stampToolBtn'); return !!(b && b.offsetParent); }")
              is True,
              "without a cell there is nothing to tap again")

        sp.click("#stampToolBtn"); sp.wait_for_timeout(350)
        check("tapping Stamps again PUTS THE SHELF AWAY",
              hidden() is True,
              "the toggle existed but a second click listener re-derived it open")
        check("...without leaving the tool",
              sp.evaluate("() => flipTool") == "stamp",
              f"flipTool={sp.evaluate('() => flipTool')!r} — the shelf covers the "
              "filmstrip, so dismissing it must not cost you the tool")
        sp.click("#stampToolBtn"); sp.wait_for_timeout(350)
        check("...and a third tap brings it back",
              hidden() is False,
              "reading .hidden after setTool rederived it makes the toggle "
              "one-way: it closes and never reopens")

        # The derived behaviour must survive: every OTHER route still opens it,
        # and leaving the tool still closes it.
        sp.evaluate("() => setTool('pen')")
        sp.wait_for_timeout(300)
        check("leaving the tool still closes the shelf", hidden() is True, "")
        sp.evaluate("() => setTool('stamp')")
        sp.wait_for_timeout(300)
        check("and a route that is not the shelf button still opens it",
              hidden() is False,
              "setTool derives this so EVERY way in works; the toggle is only "
              "an override for re-tapping the button itself")

        # ---- the ring lasts as long as the toast --------------------------
        sp.evaluate("() => localStorage.clear()")
        sp.reload(wait_until="load")
        sp.wait_for_timeout(1200)
        sp.evaluate("() => setTool('pen')")
        sbox = sp.eval_on_selector("#pad", "e => { const r = e.getBoundingClientRect();"
                                   " return { x: r.x, y: r.y }; }")
        sp.mouse.move(sbox["x"] + 40, sbox["y"] + 50)
        sp.mouse.down()
        for i in range(1, 10):
            sp.mouse.move(sbox["x"] + 40 + i * 12, sbox["y"] + 50 + i * 6)
        sp.mouse.up()
        sp.wait_for_timeout(250)
        sp.evaluate("() => setTool('select')")
        sp.mouse.move(sbox["x"] + 20, sbox["y"] + 30)
        sp.mouse.down()
        for i in range(1, 10):
            sp.mouse.move(sbox["x"] + 20 + i * 16, sbox["y"] + 30 + i * 8)
        sp.mouse.up()
        sp.wait_for_timeout(700)

        ring = lambda: sp.evaluate("() => document.getElementById('sbStamp')"
                                   ".classList.contains('pb-spot')")
        up = lambda: sp.evaluate("() => { const h = document.querySelector"
                                 "('.skribl-hint'); return !!(h && !h.hidden); }")
        check("the ring and the toast both start", ring() and up(), "")

        # THE TOAST SHOWS THE BUTTON, it does not only describe it. "The
        # highlighted button" only works if the highlight is noticed; the glyph
        # identifies the subject even when it is not. Lifted from #sbStamp
        # rather than redrawn, so the two cannot end up depicting different
        # buttons -- asserted by comparing the markup, not by its presence.
        icon = sp.evaluate(
            "() => { const h = document.querySelector('.skribl-hint');"
            " const ic = h && h.querySelector('.skribl-hint-ic svg');"
            " const sb = document.querySelector('#sbStamp svg');"
            " return { has: !!ic,"
            "          same: !!(ic && sb && ic.innerHTML === sb.innerHTML) }; }")
        check("the toast carries a glyph", icon["has"] is True,
              "a sentence about a button the reader still has to find")
        check("...and it is the SAME drawing as the button it points at",
              icon["same"] is True,
              "a second copy would drift the moment either icon is changed")
        # It has to read as one sentence, not a caption stacked over a paragraph:
        # .skribl-hint-text is display:block, so an icon before it lands on its
        # own line unless the toast lays out as a row.
        row = sp.evaluate(
            "() => { const h = document.querySelector('.skribl-hint');"
            " const ic = h.querySelector('.skribl-hint-ic');"
            " const tx = h.querySelector('.skribl-hint-text');"
            " const a = h.querySelector('.skribl-hint-action');"
            " const ir = ic.getBoundingClientRect(), tr = tx.getBoundingClientRect();"
            " return { sameRow: Math.abs(ir.top - tr.top) < 30,"
            "          w: Math.round(h.getBoundingClientRect().width),"
            "          actionLines: a ? Math.round("
            "            a.getBoundingClientRect().height / 20) : 0 }; }")
        check("the glyph sits beside the sentence, not above it",
              row["sameRow"] is True,
              "an icon over a paragraph reads as a caption, not as one sentence")
        check("...and the toast keeps its width rather than shrink-wrapping",
              row["w"] >= 300,
              f"{row['w']}px — position:fixed with no width shrink-wraps, which "
              "is fine for a centred block and wrong for a flex row")
        # 8s is past the 6000ms timer the spotlight used to run and comfortably
        # short of an action hint's DURATION * 2 dwell. Pinned at a point where
        # the two behaviours DISAGREE rather than at an exact end time, which
        # would be flaky and would break whenever the dwell is retuned.
        sp.wait_for_timeout(8000)
        check("8s in, the toast is still up",
              up() is True,
              "an action hint dwells twice the normal duration; if this is "
              "false the timing assumption below no longer holds")
        check("...and the ring is still lit",
              ring() is True,
              "it used to go out at 6s, leaving a toast saying 'the highlighted "
              "button' while nothing was highlighted")
        # And it must not outlive the sentence either.
        for _ in range(20):
            if not up():
                break
            sp.wait_for_timeout(1000)
        check("once the toast goes, the ring goes with it",
              up() is False and ring() is False,
              f"toast up={up()}, ring={ring()} — a highlight with nothing "
              "explaining it is just a button that looks broken")
        sp.close()
    finally:
        _sb.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
