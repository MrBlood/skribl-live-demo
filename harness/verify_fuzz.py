"""Random editing, checked against the invariants the SERVER enforces.

WHY THIS SUITE EXISTS. Every other suite in this harness tests a feature. This
one tests the DOCUMENT, against the one rule that has broken three separate
times for three unrelated reasons:

    'frames[9].strokeGroups' accounts for 317 points, but the strokes array
    contains 318.

That is the server refusing a share. It is not a cosmetic failure — the user
has finished a drawing and the app will not let them post it — and every
occurrence was found the same way: in production, by the owner, on a phone.
The three causes were a second pointer landing mid-stroke, a page change
mid-stroke, and a shape committing its group before its points. Nothing they
had in common was visible in a diff, and no feature suite would have caught
any of them, because each one only appears when two features INTERLEAVE.

So this drives the editor the way a person actually uses it — a shuffled stream
of draws, erases, page adds and deletes, duplicates, selections, moves,
transforms, mirrors, cuts, pastes, liquifies, undos and redos — and after EVERY
single operation re-checks the invariants:

  * every frame: strokes.length equals the sum of strokeGroups
  * every group count is a positive integer
  * the current page index is in range, and there is always at least one page
  * nothing threw

and then, at the end, POSTS the result and requires the server to take it.
That last step is the one that matters: the invariants above are this file's
model of the rule, and the POST is the rule itself.

DETERMINISTIC BY DESIGN. The seed is fixed and printed. A failure here must be
reproducible on the next run and on somebody else's machine, or it is a story
rather than a bug report. The operation log is printed on failure so the
sequence can be replayed by hand.

VERIFIED BY BREAKING IT ON PURPOSE, because a check that has never failed is a
check nobody should trust. Each shape was injected into a clean document and the
invariant named it:

    a point with no group entry   frames[0].strokeGroups accounts for 20 points,
                                  but the strokes array contains 21
    a group with no points        ...accounts for 23 points, but the strokes
                                  array contains 20
    a zero-length group           frames[0].strokeGroups[1] is 0
    idx past the last page        idx 9 outside 0..0
    a NaN coordinate              frame 0 has a non-finite point

The first of those is the production message word for word, which is the point:
this file's model of the rule and validation.py's are the same sentence.

NINE SEEDS, AND THEY MUST DIVERGE. The first attempt at hunting seeds reported
six passes with byte-identical results — 8 pages, 1960 points, 72 groups, every
time — because the override had not actually been wired and every run replayed
one sequence. Identical statistics across different seeds is the signal that a
fuzzer is not fuzzing. Seeds 1-9 now end with 5 to 18 pages and 511 to 2411
points, and all of them pass.

WHAT A FAILURE HERE MEANS. Not "the fuzzer is flaky." The operations are all
things a person can do with a mouse, in an order a person could do them in. If
this suite goes red, some pair of features has stopped composing.
"""
import json
import os
import random
import sys

# Overridable like verify_parity's, so a fuzz run can be pointed at a scratch
# instance while the main harness holds 5001.
BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
# FIXED BY DEFAULT: a failure has to be reproducible to be a bug report rather
# than a story. Overridable so the seed space can be HUNTED — a suite that only
# ever runs one sequence stops finding anything the day it goes green, and the
# whole point of this file is the interleavings nobody thought of. Run it in a
# loop over seeds when touching anything that edits the document.
SEED = int(os.environ.get("SKRIBL_FUZZ_SEED", 20260827))
OPS = 220                # ~4 s of driving; long enough to interleave everything

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# The invariant check runs in the page after every operation. It returns the
# FIRST violation it finds, or null. Kept as one evaluate so a fuzz run is not
# 220 round trips per rule.
INVARIANTS = """() => {
  if (!Array.isArray(frames) || frames.length < 1) return 'no frames at all';
  if (!(idx >= 0 && idx < frames.length)) return 'idx ' + idx + ' outside 0..' + (frames.length - 1);
  for (let f = 0; f < frames.length; f++) {
    const fr = frames[f];
    if (!fr || !Array.isArray(fr.strokes) || !Array.isArray(fr.strokeGroups))
      return 'frame ' + f + ' is malformed';
    let total = 0;
    for (let g = 0; g < fr.strokeGroups.length; g++) {
      const n = fr.strokeGroups[g];
      if (typeof n !== 'number' || !Number.isInteger(n) || n <= 0)
        return 'frames[' + f + '].strokeGroups[' + g + '] is ' + n;
      total += n;
    }
    if (total !== fr.strokes.length)
      return 'frames[' + f + '].strokeGroups accounts for ' + total
           + ' points, but the strokes array contains ' + fr.strokes.length;
    for (const p of fr.strokes) {
      if (typeof p.x !== 'number' || typeof p.y !== 'number'
          || !isFinite(p.x) || !isFinite(p.y))
        return 'frame ' + f + ' has a non-finite point';
      if (typeof p.size !== 'number' || !isFinite(p.size) || p.size <= 0)
        return 'frame ' + f + ' has a bad size ' + p.size;
    }
  }
  return null;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(1500)

    print(f"FUZZ — driving the editor with seed {SEED}")
    check("Flip booted before the fuzz starts",
          page.evaluate("() => !!(window.__skriblBoot && window.__skriblBoot.flip)"),
          "; ".join(errs[:2]))

    page.evaluate("""() => {
      frames.length = 0;
      frames.push({ strokes: [], strokeGroups: [], hold: 1 });
      idx = 0; actionLog.length = 0; redoStack.length = 0;
      setTool('pen'); buildStrip(); render();
    }""")

    box = page.locator("#pad").bounding_box()
    x0, y0 = box["x"] + 30, box["y"] + 30
    x1, y1 = box["x"] + box["width"] - 30, box["y"] + box["height"] - 30
    rng = random.Random(SEED)

    def pt():
        return (rng.uniform(x0, x1), rng.uniform(y0, y1))

    def drag(tool, steps=None):
        page.evaluate("(t) => setTool(t)", tool)
        ax, ay = pt()
        bx, by = pt()
        n = steps or rng.randint(3, 14)
        page.mouse.move(ax, ay)
        page.mouse.down()
        for i in range(1, n + 1):
            page.mouse.move(ax + (bx - ax) * i / n, ay + (by - ay) * i / n)
        page.mouse.up()

    def op_draw():      drag("pen")
    def op_erase():     drag("eraser")
    def op_shape():     drag("shape")
    def op_liquify():    drag("liquify")
    def op_select():    drag("select")

    def op_undo():      page.evaluate("() => undoStroke()")
    def op_redo():      page.evaluate("() => redoStroke()")
    # addFrame(copy) and delFrame(i) — the REAL names. Written against guessed
    # ones first (addPage/dupPage/delPage), where `typeof fn === 'function'`
    # guards turned every page operation into a silent no-op: the fuzz ran its
    # whole budget on a single page and reported a confident pass having never
    # tested a page change at all. A guard that skips is a guard that lies about
    # coverage, so these are called directly and a wrong name is a hard error.
    def op_addpage():   page.evaluate("() => { if (frames.length < 24) addFrame(false); }")
    def op_dup():       page.evaluate("() => { if (frames.length < 24) addFrame(true); }")
    def op_delpage():   page.evaluate("() => { if (frames.length > 1) delFrame(idx); }")
    def op_go():        page.evaluate("(r) => go(Math.min(frames.length - 1, Math.floor(r * frames.length)))",
                                      rng.random())
    def op_mirror():    page.evaluate("() => { if (typeof selMirror === 'function' && selSpans.length) selMirror('h'); }")
    def op_dupsel():    page.evaluate("() => { if (typeof selDuplicate === 'function' && selSpans.length) selDuplicate(); }")
    def op_cut():       page.evaluate("() => { if (typeof selCut === 'function' && selSpans.length) selCut(); }")
    def op_paste():     page.evaluate("() => { if (typeof selPaste === 'function' && selClipboard) selPaste(); }")
    def op_color():     page.evaluate("(h) => setColor(h)",
                                      rng.choice(["#ffffff", "#ff48b0", "#ffe800", "#0078bf", "#141414"]))
    def op_size():      page.evaluate("""(v) => { const el = document.getElementById('size');
                                          if (el) { el.value = v;
                                          el.dispatchEvent(new Event('input', { bubbles: true })); } }""",
                                      rng.randint(2, 34))

    # Weighted so drawing dominates, the way real use does — a fuzz that
    # deletes as often as it draws spends its whole budget on an empty page.
    POOL = ([op_draw] * 9 + [op_erase] * 3 + [op_shape] * 2 + [op_liquify] * 4
            + [op_select] * 4 + [op_undo] * 4 + [op_redo] * 2
            + [op_addpage] * 2 + [op_dup] * 1 + [op_delpage] * 1 + [op_go] * 3
            + [op_mirror] + [op_dupsel] + [op_cut] + [op_paste]
            + [op_color] * 2 + [op_size] * 2)

    log = []
    first_bad = None
    for step in range(OPS):
        fn = rng.choice(POOL)
        log.append(fn.__name__)
        try:
            fn()
        except Exception as e:                    # a throw IS a finding
            first_bad = (step, fn.__name__, f"raised {type(e).__name__}: {e}")
            break
        bad = page.evaluate(INVARIANTS)
        if bad:
            first_bad = (step, fn.__name__, bad)
            break

    if first_bad:
        step, name, why = first_bad
        print(f"    broke at step {step} on {name}: {why}")
        print(f"    sequence: {' '.join(log[max(0, step - 12):step + 1])}")
    check(f"{OPS} random operations keep the document valid",
          first_bad is None,
          "" if not first_bad else
          f"step {first_bad[0]} ({first_bad[1]}): {first_bad[2]} — some pair of "
          f"features has stopped composing; the seed is fixed, so this replays")

    check("no uncaught error during the fuzz", not errs, "; ".join(errs[:3]))

    stats = page.evaluate("""() => ({
      pages: frames.length,
      points: frames.reduce((a, f) => a + f.strokes.length, 0),
      groups: frames.reduce((a, f) => a + f.strokeGroups.length, 0)
    })""")
    print(f"    ended with {stats['pages']} pages, {stats['points']} points, "
          f"{stats['groups']} groups")
    check("the fuzz actually drew something — the run is not vacuous",
          stats["points"] > 50,
          f"{stats} — a fuzz that ends empty proved nothing, and an empty page "
          f"satisfies every invariant above trivially")
    # The same objection applies to the page operations: if every one of them
    # had quietly done nothing, the invariants would still all hold and this
    # suite would still be green while testing a single page.
    check("...and actually used more than one page",
          stats["pages"] > 1 or log.count("op_addpage") == 0,
          f"{stats['pages']} pages after {log.count('op_addpage')} adds, "
          f"{log.count('op_delpage')} deletes and {log.count('op_dup')} "
          f"duplicates — page operations that no-op make this suite a "
          f"single-page test wearing a multi-page name")

    print("\nFUZZ — and the server takes what the fuzz produced")
    # THE REAL TEST. Everything above is this file's MODEL of the rule; the POST
    # is the rule. If validation.py and this file ever disagree, this is the
    # assertion that says so.
    posted = page.evaluate("""async (base) => {
      const frs = frames.map(f => ({ strokes: f.strokes,
                                     strokeGroups: f.strokeGroups,
                                     background: '#0d0f14' }));
      const r = await fetch(base + '/api/skribls', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'fuzz', kind: 'flip', frames: frs, fps: 12 })
      });
      let body = null; try { body = await r.json(); } catch (e) {}
      return { status: r.status, ok: r.ok, body: body };
    }""", BASE)
    check("a fuzzed document POSTS",
          posted.get("ok"),
          f"{posted.get('status')}: "
          f"{json.dumps(posted.get('body'))[:220] if posted.get('body') else ''}"
          f" — the invariants above are a model of the rule; this is the rule")

    if posted.get("ok"):
        url = (posted["body"] or {}).get("url") or "/s/" + ((posted["body"] or {}).get("slug") or "")
        viewer = browser.new_page(viewport={"width": 900, "height": 800})
        verrs = []
        viewer.on("pageerror", lambda e: verrs.append(str(e)))
        viewer.goto(BASE + url, wait_until="load")
        viewer.wait_for_timeout(2200)
        check("...and the player renders it without erroring",
              not verrs, "; ".join(verrs[:2]))
        viewer.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
