"""v226 — a run of pages is one object, and the controls already there operate on it.

WHAT THIS IS. Flip's strip is a film; the thing a person reaches for is "these
four frames". Until now every page operation meant exactly one page, so
rearranging a sequence was N separate moves and copying a run was impossible.

WHY IT ADDS NO BUTTONS. DESIGN-DIRECTION is explicit that page management is
direct manipulation on the film and NOT a management cluster — "No 'Move left'.
No 'Move right'. No page-management cluster. The object itself is manipulable."
So the range is selected on the strip, and Copy / Delete / ×hold / the two
arrows change what they MEAN rather than multiplying. That is the design claim,
and this suite pins it: the same five controls, doing more.

THE ONE INVARIANT EVERYTHING ELSE RESTS ON. `idx` is always one end of the span.
There is no way to have a range that excludes the page you are looking at, which
is what makes re-scoping controls that already acted on `idx` safe rather than
surprising. Several assertions below exist only to hold that.

WHY A SPAN IS ALLOWED TO VANISH. A range is a pair of INDICES, so any page
count change it did not itself perform invalidates it — the same reasoning the
stroke selection uses when you change page. Adding or deleting a page drops it
rather than trying to fix it up, because a repaired range operates on artwork
the user never picked.

The arithmetic lives in lib/pagespan.js and is exercised here through the page,
including the case that is always wrong first time: a span moving RIGHTWARDS
lands short by its own length unless the target is adjusted for the splice-out.
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


def fresh(page, n=6):
    """n identifiable pages. Each carries one stroke whose x IS its page number,
    so any reorder can be read straight off the artwork rather than inferred."""
    page.evaluate("""(n) => {
      frames.length = 0;
      for (let i = 0; i < n; i++) {
        frames.push({ strokes: [{x: i, y: i, color: '#fff', size: 4, t: 0, start: true}],
                      strokeGroups: [1], hold: 1 });
      }
      idx = 0; spanAnchor = null; pageClip = null;
      redoStack.length = 0; buildStrip(); render();
    }""", n)


def order(page):
    """The page order, read from the artwork."""
    return page.evaluate("() => frames.map(f => f.strokes[0].x)")


with sync_playwright() as p:
    br = p.chromium.launch()
    try:
        page = br.new_page(viewport={"width": 1280, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/flip", wait_until="networkidle")
        page.wait_for_timeout(400)

        print("\nLIB — the arithmetic, including the case that is always wrong")
        check("lib/pagespan.js is loaded on Flip",
              page.evaluate("() => typeof window.SkriblPageSpan") == "object",
              "a lib the template does not list is a lib that does not exist")
        cases = page.evaluate("""() => {
          const S = window.SkriblPageSpan, f = ['a','b','c','d','e','f'];
          const sp = (a, b) => S.normalise(a, b, f.length);
          return {
            backwards: JSON.stringify(S.normalise(3, 1, 6)),
            clamped:   JSON.stringify(S.normalise(-5, 99, 6)),
            label:     S.label(sp(1, 3)),
            labelOne:  S.label(sp(2, 2)),
            beforeF:   S.moveSpan(f, sp(1, 3), 5).join(''),
            toEnd:     S.moveSpan(f, sp(1, 3), 6).join(''),
            toFront:   S.moveSpan(f, sp(1, 3), 0).join(''),
            ontoSelf:  S.moveSpan(f, sp(1, 3), 2).join(''),
            justPast:  S.moveSpan(f, sp(1, 3), 4).join(''),
            everything:S.moveSpan(f, sp(0, 5), 0).join(''),
          };
        }""")
        check("a backwards drag normalises to an ordered range",
              cases["backwards"] == '{"from":1,"to":3}', cases["backwards"])
        check("out-of-range ends are clamped, not trusted",
              cases["clamped"] == '{"from":0,"to":5}', cases["clamped"])
        check("a range reads as a range and a single page as a number",
              cases["label"] == "2–4" and cases["labelOne"] == "3",
              f"{cases['label']!r} / {cases['labelOne']!r}")
        check("MOVING RIGHT accounts for the span's own removal",
              cases["beforeF"] == "aebcdf",
              f"bcd before f -> {cases['beforeF']} — landing short by the span's "
              "own length is the classic form of this bug")
        check("...and the far end is reachable", cases["toEnd"] == "aefbcd",
              cases["toEnd"])
        check("moving left needs no adjustment", cases["toFront"] == "bcdaef",
              cases["toFront"])
        check("dropping a span onto itself is a no-op, not an error",
              cases["ontoSelf"] == "abcdef" and cases["justPast"] == "abcdef",
              f"{cases['ontoSelf']} / {cases['justPast']}")
        check("moving every page nowhere changes nothing",
              cases["everything"] == "abcdef", cases["everything"])

        print("\nSELECT — shift-click on the film, and the strip shows the run")
        fresh(page)
        page.locator("#strip .frame").nth(3).click(modifiers=["Shift"])
        page.wait_for_timeout(120)
        check("shift-click selects from the current page through that one",
              page.evaluate("() => JSON.stringify(pageSpan())") == '{"from":0,"to":3}',
              page.evaluate("() => JSON.stringify(pageSpan())"))
        check("THE INVARIANT: idx is one end of the span",
              page.evaluate("() => { const s = pageSpan();"
                            " return s && (idx === s.from || idx === s.to); }"),
              "every re-scoped control acts on idx, so this is what makes it safe")
        check("the run is drawn as one stretch of film",
              page.evaluate("() => document.querySelectorAll('#strip .frame.inspan').length") == 4)
        check("...with ends marked, so its shape reads without counting tiles",
              page.evaluate("() => !!document.querySelector('#strip .frame.span-first')"
                            " && !!document.querySelector('#strip .frame.span-last')"))
        check("the leading tile's number becomes the range",
              page.evaluate("() => strip.children[0].querySelector('.num').textContent") == "1–4")
        check("a single page is NOT a span — one page selected is just a page",
              page.evaluate("() => { spanAnchor = idx; return pageSpan(); }") is None,
              "otherwise every ordinary click would enter a range mode")

        print("\nSELECT — and the ways out of one")
        fresh(page)
        page.locator("#strip .frame").nth(3).click(modifiers=["Shift"])
        page.wait_for_timeout(80)
        page.keyboard.press("Escape")
        page.wait_for_timeout(80)
        check("Escape drops the range", page.evaluate("() => pageSpan()") is None)
        page.locator("#strip .frame").nth(3).click(modifiers=["Shift"])
        page.wait_for_timeout(80)
        page.locator("#strip .frame").nth(1).click()
        page.wait_for_timeout(80)
        check("a plain tap retires it — you moved on",
              page.evaluate("() => pageSpan()") is None
              and page.evaluate("() => idx") == 1, "and selects that page")
        fresh(page)
        page.keyboard.press("Shift+ArrowRight")
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_timeout(120)
        check("shift-arrow grows a range from the keyboard",
              page.evaluate("() => JSON.stringify(pageSpan())") == '{"from":0,"to":2}',
              page.evaluate("() => JSON.stringify(pageSpan())"))

        print("\nSCOPE — the same five controls, now saying 'these pages'")
        check("the page readout shows the range",
              page.evaluate("() => pbWho.textContent") == "1–3/6",
              page.evaluate("() => pbWho.textContent"))
        check("...and says so to a screen reader in full words",
              "Pages 1 to 3 of 6" in page.evaluate("() => pbWho.getAttribute('aria-label')"),
              page.evaluate("() => pbWho.getAttribute('aria-label')"))
        for el, want in (("pbDel", "Delete these 3 pages"),
                         ("pbCopy", "Copy these 3 pages"),
                         ("pbLeft", "Move these 3 pages left"),
                         ("pbHold", "Hold these 3 pages longer")):
            check(f"{el} re-scopes its own label", 
                  page.evaluate(f"() => {el}.title") == want,
                  page.evaluate(f"() => {el}.title"))
        check("MUTATION: with no range the same controls say 'this page'",
              page.evaluate("""() => { clearSpan(true); buildStrip();
                return pbDel.title; }""") == "Delete this page",
              "if they read the same either way, the re-scoping is decoration")

        print("\nOPERATE — copy, paste, delete, hold and move a run")
        fresh(page)
        page.keyboard.press("Shift+ArrowRight")
        page.keyboard.press("Shift+ArrowRight")     # pages 1-3 (x = 0,1,2)
        page.wait_for_timeout(100)
        page.evaluate("() => pbCopy.click()")
        page.wait_for_timeout(80)
        check("copying a run takes the whole run",
              page.evaluate("() => pageClip.length") == 3)
        check("the paste control offers the count rather than a bare verb",
              "3" in (page.evaluate(
                  "() => { const b = document.getElementById('addpaste');"
                  " return b ? b.textContent : ''; }") or ""),
              page.evaluate("() => { const b=document.getElementById('addpaste');"
                            " return b ? b.textContent.trim() : 'MISSING'; }"))
        page.evaluate("() => spanPaste()")
        page.wait_for_timeout(100)
        check("pasting inserts the whole run after the current page",
              page.evaluate("() => frames.length") == 9,
              str(order(page)))
        check("...and the pasted run lands SELECTED, ready to move",
              page.evaluate("() => JSON.stringify(pageSpan())") == '{"from":3,"to":5}',
              page.evaluate("() => JSON.stringify(pageSpan())"))
        check("...as a copy, not a reference to the pages it came from",
              page.evaluate("""() => { frames[3].strokes[0].x = 99;
                return frames[0].strokes[0].x; }""") == 0,
              "editing the paste must not edit the original")

        fresh(page)
        page.evaluate("() => { spanAnchor = 1; idx = 3; buildStrip(); }")
        page.evaluate("() => pbHold.click()")
        page.wait_for_timeout(80)
        check("×hold applies ONE value across the run",
              page.evaluate("() => frames.slice(1,4).map(f => f.hold).join(',')") == "2,2,2",
              page.evaluate("() => frames.map(f => f.hold).join(',')")
              + " — cycling each page independently would scatter them")
        check("...and leaves pages outside it alone",
              page.evaluate("() => frames[0].hold === 1 && frames[4].hold === 1"))

        fresh(page)
        page.evaluate("() => { spanAnchor = 1; idx = 3; buildStrip(); }")
        page.evaluate("() => pbRight.click()")
        page.wait_for_timeout(100)
        check("the arrows walk the whole run one slot", order(page) == [0, 4, 1, 2, 3, 5],
              str(order(page)))
        check("...and it stays selected, so a second press keeps walking",
              page.evaluate("() => JSON.stringify(pageSpan())") == '{"from":2,"to":4}',
              page.evaluate("() => JSON.stringify(pageSpan())"))
        check("...and you are still on the page you were on",
              page.evaluate("() => frames[idx].strokes[0].x") == 3,
              "moving pages must never silently switch which one you draw on")

        fresh(page)
        page.evaluate("() => { spanAnchor = 0; idx = 2; buildStrip(); }")
        page.evaluate("() => pbDel.click()")
        page.wait_for_timeout(100)
        check("deleting a run removes exactly it", order(page) == [3, 4, 5],
              str(order(page)))
        check("...and drops the range with it",
              page.evaluate("() => pageSpan()") is None)
        fresh(page)
        page.evaluate("() => { spanAnchor = 0; idx = frames.length - 1; buildStrip(); }")
        check("deleting EVERY page is refused rather than emptying the flipbook",
              page.evaluate("() => pbDel.disabled") is True,
              "Clear all is the control for that, and it has its own undo")

        print("\nINVALIDATION — a range must not outlive the pages it names")
        fresh(page)
        page.evaluate("() => { spanAnchor = 0; idx = 2; buildStrip(); }")
        page.evaluate("() => addFrame(false)")
        page.wait_for_timeout(80)
        check("adding a page drops the range",
              page.evaluate("() => pageSpan()") is None,
              "the indices no longer name the pages the user picked")
        fresh(page)
        page.evaluate("() => { spanAnchor = 0; idx = 2; buildStrip(); }")
        page.evaluate("() => delFrame(5)")
        page.wait_for_timeout(80)
        check("deleting an unrelated page drops it too",
              page.evaluate("() => pageSpan()") is None,
              "cheaper to re-pick than to be silently wrong")

        print("\nKEYBOARD — and the text fields it must not steal from")
        fresh(page)
        stolen = page.evaluate("""() => {
          const inp = document.getElementById('flipShareTitle');
          if (!inp) return 'no input';
          inp.hidden = false; inp.focus();
          const before = pageClip;
          inp.dispatchEvent(new KeyboardEvent('keydown',
            {key:'c', metaKey:true, bubbles:true}));
          return pageClip === before ? 'ignored' : 'STOLEN';
        }""")
        check("Cmd+C in a text field does not copy PAGES", stolen == "ignored",
              f"{stolen} — the share sheet's title and caption live on this page")

        check("no page error was raised anywhere in this suite",
              not errors, "; ".join(errors[:2]))
    finally:
        br.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
