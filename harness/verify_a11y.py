"""Keyboard and assistive-technology contracts, as their own suite.

WHY THIS IS A NEW SUITE RATHER THAN MORE OF verify_ux.py. An accessibility
audit of v278 made a structural observation, not just a list of defects: the
tree carries thousands of assertions (see harness/RELEASE.md for the figure —
typing one here is how a number goes stale) and yet basic keyboard and ARIA
failures were visible in the SOURCE. Scrubbers declared `role="slider"` with
no tabindex, no `aria-valuenow` and no key handler. Every `aria-modal="true"`
dialog did nothing about focus, two of them calling `blur()` and hoping.
Visible slider captions were not labels. Segmented controls tracked selection in a CSS class
only. Post status and toasts announced nothing.

Its diagnosis is the part worth keeping: "the existing test architecture is not
asking enough questions about focus order, accessible names, ARIA state, or
keyboard equivalence", and accessibility should be part of the component state
machine rather than markup added afterwards. A suite that asks those questions
by name is how they stop being optional. verify_ux.py is already at 333
assertions and past the split trigger anyway.

THE RULE THIS SUITE ENFORCES ON ITSELF. Assert the BEHAVIOUR, not the
attribute. `role="slider"` present is worth nothing — that was the defect. So
these press keys and read what changed, focus things and read where focus
went. The two places an attribute IS the assertion (an accessible name, a live
region) say so.

SECTION 1 — a declared slider can actually be operated by keyboard.
SECTION 2 — EVERY modal surface takes focus, traps Tab, and gives focus back.
            The population is read out of the DOM and cross-checked against
            two source censuses — templates and lib/*.js — so a dialog built
            at runtime cannot slip past a sweep taken at load. See the note at
            that section for why the first two versions were unsound.
SECTION 3 — every form control has an accessible name.
SECTION 4 — one-of-N controls expose which one.
SECTION 5 — asynchronous status reaches a live region.
SECTION 6 — no meaningful text below the AA contrast floor.

Requires a running server:
    ./harness/run_harness.sh verify_a11y.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"

results = []


check = make_check(results)


# ---------------------------------------------------------------- contrast
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ------------------------------------------------------------ section 1
    print("\nA11Y 0 — an id is a name, and a name has to be unique")
    # AN SVG url(#...) AND getElementById BOTH TAKE THE FIRST MATCH, so a
    # duplicate id does not error — it silently points half the page at the
    # wrong element. The Pad carried two <linearGradient id="skink-m">: the
    # header includes the brand mark at brand_sweep=101 and
    # _skribl_player_controls.html includes it again at the default 65, so the
    # "made with" mark under the player DECLARED x2="65" and RENDERED at 101.
    # Nothing looked broken, which is why it lasted.
    #
    # Screen readers resolve aria-labelledby and aria-describedby the same way,
    # so this is an accessibility assertion and not only an HTML-validity one:
    # a label pointing at the first of two ids describes the wrong control.
    for _path, _name in (("/", "Pad"), ("/flip", "Flip"),
                         ("/library", "Library"), ("/feed", "the host feed")):
        _pg = browser.new_page(viewport={"width": 1280, "height": 900})
        _pg.goto(BASE + _path, wait_until="load")
        _pg.wait_for_timeout(900)
        _seen = _pg.evaluate("""() => {
          const seen = Object.create(null), dup = [];
          for (const el of document.querySelectorAll('[id]')) {
            if (seen[el.id]) dup.push(el.id); else seen[el.id] = 1;
          }
          return {total: document.querySelectorAll('[id]').length,
                  dup: [...new Set(dup)]};
        }""")
        check(f"{_name}: every id on the page is unique",
              _seen["total"] > 0 and not _seen["dup"],
              f"{_seen['total']} ids, duplicated: {', '.join(_seen['dup'])}"
              if _seen["dup"] else
              f"{_seen['total']} ids, none repeated")
        _pg.close()

    print("\nA11Y 1 — a declared slider can be driven from the keyboard")
    # role="slider" is a PROMISE: a screen reader announces a control the user
    # can move. All three players declared or implied it and none could be
    # focused, moved, or read. Asserted by pressing keys, because the attribute
    # being present is exactly what was true while it was broken.
    for path, sel, label, setup in (
            ("/", "#playScrub", "Pad", "record-and-play"),
            ("/flip", "#flipProgress", "Flip", None),
    ):
        pg = browser.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1200)
        if label == "Flip":
            # frac() is idx/(n-1); with a single frame there is no position to
            # move and the whole section would assert 0 == 0.
            pg.evaluate("() => { if (typeof addPage === 'function') "
                        "{ addPage(); addPage(); } }")
            pg.wait_for_timeout(400)
        if setup == "record-and-play":
            # Pad's scrubber is hidden until something is playing.
            box = pg.locator("#canvas").bounding_box()
            pg.mouse.move(box["x"] + 120, box["y"] + 120)
            pg.mouse.down()
            for i in range(20):
                pg.mouse.move(box["x"] + 120 + i * 6, box["y"] + 130 + i * 3)
                pg.wait_for_timeout(25)
            pg.mouse.up()
            pg.wait_for_timeout(300)
            pg.click("#recordBtn")
            pg.wait_for_timeout(300)
            pg.click("#playBtn")
            pg.wait_for_timeout(600)

        info = pg.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            return { tabindex: el.getAttribute('tabindex'),
                     role: el.getAttribute('role'),
                     now: el.getAttribute('aria-valuenow'),
                     text: el.getAttribute('aria-valuetext'),
                     name: el.getAttribute('aria-label') }; }""", sel)
        if info is None:
            check(f"{label}: the scrubber exists", False, sel)
            pg.close()
            continue

        check(f"{label}: the scrubber is reachable by Tab",
              info["tabindex"] == "0",
              f"tabindex={info['tabindex']!r} — role=slider without one "
              "announces a control that cannot be focused")
        check(f"{label}: it reports a current value",
              info["now"] is not None,
              "aria-valuemin/max were declared and aria-valuenow was not, so a "
              "screen reader could say the range but never the position")
        check(f"{label}: ...with a unit", (info["text"] or "").endswith("%"),
              f"{info['text']!r}")
        check(f"{label}: it has an accessible name", bool(info["name"]))

        # THE ASSERTION THAT MATTERS: a key press moves it.
        #
        # DISPATCHED AND READ IN ONE TICK, deliberately. The first version
        # pressed a key, waited 200ms and read aria-valuenow — and failed on
        # Pad with "74 -> 0", because Pad's scrubber only exists WHILE PLAYING
        # and the render loop rewrites the value on the next frame. It was
        # racing the thing under test. Dispatching the event and reading before
        # yielding removes the loop from the question entirely: what is being
        # asserted is that the handler ran and moved the position, which is the
        # claim `role="slider"` makes.
        pg.focus(sel)
        # Reads BEFORE and AFTER in the same tick. Reading "before" in an
        # earlier call was not good enough on Pad: playback keeps moving the
        # value between two Playwright round-trips, so "ArrowRight increased
        # it" passed at 0 -> 100 — true, and nothing to do with the key. A
        # delta measured across one dispatch cannot be produced by the loop.
        PRESS = """([sel, key]) => {
            const el = document.querySelector(sel);
            el.focus();
            const before = Number(el.getAttribute('aria-valuenow'));
            el.dispatchEvent(new KeyboardEvent('keydown', {
              key: key, bubbles: true, cancelable: true }));
            return { before: before,
                     after: Number(el.getAttribute('aria-valuenow')) };
        }"""
        _STEP = pg.evaluate("() => window.SkriblScrub && window.SkriblScrub.STEP")
        check(f"{label}: the shared step is exposed", isinstance(_STEP, (int, float)),
              str(_STEP))
        r = pg.evaluate(PRESS, [sel, "End"])
        check(f"{label}: End seeks to the end", r["after"] == 100, str(r))
        r = pg.evaluate(PRESS, [sel, "Home"])
        check(f"{label}: Home seeks to the start", r["after"] == 0, str(r))
        # THE EXACT-DELTA CHECKS RUN ONLY WHERE THE POSITION HOLDS STILL, and
        # the reason is a real property of the product rather than a testing
        # convenience. Pad's scrubber EXISTS ONLY WHILE PLAYING — it is hidden
        # otherwise — so between one dispatch and the next, playback has moved
        # the position on its own. Asserting "+2 from where it was" there
        # measured a value the loop had already changed, and reported
        # `before: 0, after: 100` for a handler that was behaving correctly:
        # it stepped 2% forward from ~98%, not from the 0 the previous call
        # had left. Flip's frame scrubber is static when not playing, so the
        # arithmetic is exact there and that is where it is asserted.
        #
        # End and Home are absolute, so they are meaningful on both and are
        # checked above for both.
        if label == "Flip":
            r = pg.evaluate(PRESS, [sel, "ArrowRight"])
            check(f"{label}: ArrowRight steps forward by exactly one step",
                  r["after"] - r["before"] == _STEP,
                  f"{r} — expected +{_STEP}; a mere increase is what playback "
                  "does on its own, so only the exact delta proves the key did it")
            r = pg.evaluate(PRESS, [sel, "ArrowLeft"])
            check(f"{label}: ArrowLeft steps back by exactly one step",
                  r["before"] - r["after"] == _STEP or r["after"] == 0,
                  f"{r} — expected -{_STEP}, or clamped at 0")
            r = pg.evaluate(PRESS, [sel, "PageUp"])
            check(f"{label}: PageUp is a bigger jump than an arrow",
                  r["after"] - r["before"] > _STEP or r["after"] == 100, str(r))
        else:
            # Still worth asserting the arrow REACHES the handler on Pad; the
            # size of the jump is the loop's business, the clamp is not.
            r = pg.evaluate(PRESS, [sel, "ArrowRight"])
            check(f"{label}: ArrowRight is handled and stays in range",
                  0 <= r["after"] <= 100, str(r))
        # An unhandled key must not be swallowed, or Tab is trapped on a
        # control the user then cannot leave.
        unhandled = pg.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            const e = new KeyboardEvent('keydown', {
              key: 'Tab', bubbles: true, cancelable: true });
            el.dispatchEvent(e);
            return e.defaultPrevented; }""", sel)
        check(f"{label}: Tab is not swallowed", unhandled is False,
              "preventDefault on every key would trap focus on the scrubber")
        pg.close()

    # ------------------------------------------------------------ section 2
    print("\nA11Y 2 — every modal surface takes focus, traps Tab, and hands it back")
    # aria-modal="true" while focus stays behind the sheet is worse than not
    # claiming it: the user is told they are in a modal and the page disagrees.
    #
    # THE FIRST VERSION OF THIS SECTION TESTED ONE MODAL BY HAND — the More
    # menu — and passed while Export, Report, Your Skribls and the leave
    # confirm all still declared the role and implemented none of it. An audit
    # of v279 named the shape: "a global semantic claim should generate its
    # test population from the DOM, not from a manually chosen specimen." The
    # suite had already learned to assert behaviour instead of attributes and
    # then asserted the right thing about the wrong population, which is the
    # same error one level up.
    #
    # So the population is read from the page. MODALS below supplies only HOW
    # to open each one — a recipe, not a list of what to test — and the first
    # assertion is that the two agree: a surface in the DOM with no recipe
    # FAILS rather than being skipped, so adding an eighth dialog without
    # testing it is not possible quietly.
    #
    # DYNAMICALLY CREATED DIALOGS ESCAPE A CENSUS TAKEN AT LOAD, which is a
    # real hole in "enumerate from the DOM": lib/recoverykey.js builds its
    # overlay the first time it is shown, so at load there is nothing to find.
    # It is primed below before the census is taken. Any future dialog built
    # the same way must be primed here too, and the template census that
    # follows is the backstop that says so.
    MODALS = {
        # id            (surface, how to open, expected focus-return target)
        "menuSheet":    ("/",     "click:#menuBtn",                "menuBtn"),
        "helpDrawer":   ("/",     "click:#menuBtn|click:#helpItem", None),
        "postedDrawer": ("/",     "click:#menuBtn|click:#postedItem", None),
        "exportSheet":  ("/",     "click:#menuBtn|click:#exportItem", None),
        "reportSheet":  ("/",     "click:#menuBtn|click:#reportItem", None),
        # Post is gated on a FINISHED take, not on ink: drawing auto-starts
        # recording and #recordBtn stops it. The first recipe here was
        # "draw|click:#postBtn" and timed out on a button that is hidden and
        # disabled mid-take — the enumeration turning a silent no-op into a
        # loud failure, which is the whole reason it replaced the specimen.
        "postSheet":    ("/",     "draw|click:#recordBtn|click:#postBtn", None),
        # atRisk() is `!flushPadDraft()`, so a draft that saves cleanly is not
        # at risk and the anchor simply navigates. Stubbing the flush puts the
        # app in the state the sheet exists for; the click, the handler and the
        # sheet are all still the product's.
        "leaveSheet":   ("/",     "js:window.flushPadDraft = () => false"
                                  "|click:#menuBtn|click:#flipBtn", None),
        "reckeyOverlay": ("/",    "js:window.SkriblRecoveryKey.present("
                                  "{key:'test-recovery-key-abc123'})", None),
        # The import half of the recovery key, and the guard that stands
        # between "Clear list" and every key it would take with it. Both are
        # built by lib/recoverykey.js the first time they are shown.
        "recoverOverlay": ("/",   "js:window.SkriblRecoveryKey.openRecover()", None),
        "clearKeysOverlay": ("/", "js:window.SkriblRecoveryKey.confirmClear("
                                  "[{id:'x',tok:'k'}], function () {})", None),
    }

    def _draw_on_pad(pg):
        """One real stroke on PAD's canvas, which is #canvas.

        Named for its surface rather than called DRAW_STROKE, because the
        generic name is what caused the v278 mess: a helper lifted to the top
        of a file reads as applying to the whole file, and Flip draws on #pad.
        Every recipe here is a Pad path; a Flip one would need its own."""
        box = pg.locator("#canvas").bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pg.mouse.move(cx - 60, cy)
        pg.mouse.down()
        pg.mouse.move(cx + 60, cy)
        pg.mouse.up()
        pg.wait_for_timeout(300)

    def _drive(pg, recipe):
        """Run one recipe's steps. Kept tiny on purpose: a recipe that needed
        real logic would be a second implementation of the product."""
        for step in recipe.split("|"):
            if step == "draw":
                _draw_on_pad(pg)
            elif step.startswith("click:"):
                pg.click(step[6:])
            elif step.startswith("js:"):
                pg.evaluate(step[3:])
            pg.wait_for_timeout(450)

    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/")
    # Prime the runtime-built dialog so the census can see it (see above).
    for _prime, _shut in (
            ("present({key:'census'})", "close()"),
            ("openRecover()", "closeRecover()"),
            ("confirmClear([{id:'c',tok:'k'}], function () {})", "closeClear()")):
        pg.evaluate(f"window.SkriblRecoveryKey && window.SkriblRecoveryKey.{_prime}")
        pg.wait_for_timeout(150)
        pg.evaluate(f"window.SkriblRecoveryKey && window.SkriblRecoveryKey.{_shut}")
    pg.wait_for_timeout(150)
    found = pg.evaluate("""() => [...document.querySelectorAll('[aria-modal="true"]')]
        .map(el => el.id || '(no id)')""")
    pg.close()

    unrecipe = sorted(set(found) - set(MODALS))
    check("every aria-modal surface in the DOM has a recipe here",
          not unrecipe,
          ", ".join(unrecipe) + " — a dialog claiming modal semantics that "
          "nothing drives is exactly what this section was rewritten to stop")
    stale = sorted(set(MODALS) - set(found))
    check("every recipe here names a surface that still exists",
          not stale,
          ", ".join(stale) + " — a recipe for a deleted dialog passes forever "
          "by testing nothing")

    for mid in sorted(set(found) & set(MODALS)):
        path, recipe, back_to = MODALS[mid]
        pg = browser.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1200)
        _drive(pg, recipe)

        inside = pg.evaluate("""(id) => {
            const d = document.getElementById(id), a = document.activeElement;
            return !!(d && a && d.contains(a)); }""", mid)
        check(f"{mid}: opening moves focus into it", inside,
              "focus stayed on whatever had it, behind the sheet")

        # Tab all the way round: focus must still be inside.
        for _ in range(25):
            pg.keyboard.press("Tab")
        still = pg.evaluate("""(id) => {
            const d = document.getElementById(id), a = document.activeElement;
            return !!(d && a && d.contains(a)); }""", mid)
        check(f"{mid}: Tab stays inside it", still,
              "25 tabs escaped the dialog — a keyboard user reaches the page "
              "underneath while a modal covers it")

        pg.keyboard.press("Escape")
        pg.wait_for_timeout(650)
        landed = pg.evaluate("""() => {
            const a = document.activeElement;
            return a === document.body ? '(body)' : (a && a.id) || '(unnamed)'; }""")
        # WHAT IS ASSERTED ON CLOSE, and why it is not always an exact id.
        # Only the More menu has a single unambiguous opener; the others are
        # reached from inside a menu that has itself closed by then. The
        # invariant that holds for all of them is the one the finding was
        # about: focus must not be dumped on <body>, which is where blur()
        # used to leave it and which loses the user's place entirely.
        if back_to:
            check(f"{mid}: closing returns focus to {back_to}", landed == back_to,
                  f"focus on {landed!r}")
        else:
            check(f"{mid}: closing does not drop focus on <body>",
                  landed != "(body)", f"focus on {landed!r}")
        pg.close()

    # THE TEMPLATE CENSUS, which the live one cannot replace. A dialog inside a
    # branch that did not render this run is invisible to the DOM sweep above
    # and would leave a genuine gap silently. Every aria-modal in the templates
    # must carry an id and that id must be recipe-backed.
    # ...AND THE SAME FOR DIALOGS BUILT IN JAVASCRIPT, which is the hole the
    # template census cannot see and which I fell into one release after
    # writing the note warning about it. v281 added two runtime dialogs
    # (recover, clear-keys) and this section stayed green at 62/62 because
    # nothing had primed them into the DOM before the sweep — the population
    # was generated, correctly, from a page that did not contain them yet.
    #
    # So: any non-minified module under static/ that writes `aria-modal` has
    # its assigned element ids extracted from source, and each must be
    # recipe-backed. A dialog cannot now be added in JS without either a recipe
    # or a deliberate argument about why it does not need one.
    #
    # WHAT THIS CANNOT SEE, stated rather than left to be discovered the way
    # the last two gaps were: it matches `el.id = 'name'`, which is how both
    # dialogs here are built. A module assigning an id through setAttribute, a
    # template literal or a computed name would pass this check while adding an
    # untested dialog. That is a narrower hole than the one it closes, and
    # naming it is the honest position until something needs the wider match.
    _js_dir = ROOT / "skribl" / "static"
    _js_modals = set()
    for f in sorted(_js_dir.rglob("*.js")):
        if "min.js" in f.name:
            continue
        body = f.read_text(encoding="utf-8")
        if "aria-modal" not in body:
            continue
        _js_modals |= set(re.findall(r"\.id\s*=\s*['\"]([A-Za-z0-9_-]+)['\"]", body))
    _js_untested = sorted(_js_modals - set(MODALS))
    check("every dialog built in JavaScript is recipe-backed",
          not _js_untested, ", ".join(_js_untested) +
          " — built at runtime, so the DOM census above cannot see it unless "
          "this section primes it first; add a recipe and prime it")

    _tpl = ROOT / "skribl" / "templates" / "skribl"
    _tpl_modals, _idless = set(), []
    for f in sorted(_tpl.glob("*.html")):
        for tag in re.findall(r"<[^>]*aria-modal=\"true\"[^>]*>",
                              f.read_text(encoding="utf-8")):
            m = re.search(r'\bid="([^"]+)"', tag)
            if m:
                _tpl_modals.add(m.group(1))
            else:
                _idless.append(f.name)
    check("every aria-modal in a template carries an id",
          not _idless, ", ".join(sorted(set(_idless))) +
          " — an id is how this suite addresses it; without one it cannot be "
          "enumerated and cannot be tested")
    _untested = sorted(_tpl_modals - set(MODALS))
    check("every aria-modal in a template is recipe-backed",
          not _untested, ", ".join(_untested) +
          " — declared in markup, never opened by this suite; a dialog behind "
          "an unrendered branch is the case the live census cannot see")

    # ------------------------------------------------------------ section 3
    print("\nA11Y 3 — every form control has an accessible name")
    # An unlabelled range is "slider" and nothing else to a screen reader. The
    # image drawer had three, labelled for Flip only, because the aria-label
    # was inside a {% if kind == 'flip' %}.
    NAMED = """() => {
      const out = [];
      document.querySelectorAll('input, select, textarea').forEach(el => {
        const t = (el.getAttribute('type') || 'text').toLowerCase();
        if (t === 'hidden') return;
        /* display:none is removed from the accessibility tree entirely, so an
           unnamed one is not a defect — the button that opens it carries the
           name. A CLIPPED input (.vis-hidden: 1px, absolute) is still exposed
           and still focusable, so it does need one. offsetParent cannot tell
           the two apart; computed display can. */
        if (getComputedStyle(el).display === 'none') return;
        let named = !!(el.getAttribute('aria-label')
                    || el.getAttribute('aria-labelledby'));
        if (!named && el.id) named = !!document.querySelector(
            'label[for="' + CSS.escape(el.id) + '"]');
        if (!named) named = !!el.closest('label');
        if (!named) out.push(el.id || el.className || el.type);
      });
      return out; }"""
    for path, label, opener in (("/", "Pad", "#photoBtn"), ("/flip", "Flip", "#imgBtn")):
        pg = browser.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1200)
        try:
            pg.click(opener, timeout=2500)
            pg.wait_for_timeout(400)
        except Exception:
            pass
        unnamed = pg.evaluate(NAMED)
        check(f"{label}: every visible form control is named",
              not unnamed, f"unnamed: {unnamed}")
        pg.close()

    # ------------------------------------------------------------ section 4
    print("\nA11Y 4 — a one-of-N control says WHICH")
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/")
    seg = pg.evaluate("""() => {
        const out = {};
        for (const id of ['smoothSeg']) {
          const el = document.getElementById(id);
          if (!el) { out[id] = 'missing'; continue; }
          const btns = [...el.querySelectorAll('button')];
          out[id] = {
            allHaveState: btns.every(b => b.hasAttribute('aria-pressed')),
            pressedCount: btns.filter(
              b => b.getAttribute('aria-pressed') === 'true').length,
            agrees: btns.every(b =>
              (b.getAttribute('aria-pressed') === 'true')
              === b.classList.contains('active')),
          };
        }
        return out; }""")
    for _id, r in seg.items():
        check(f"#{_id}: every option carries aria-pressed",
              r != "missing" and r["allHaveState"], str(r))
        check(f"#{_id}: exactly one is pressed",
              r != "missing" and r["pressedCount"] == 1, str(r))
        check(f"#{_id}: the ARIA state agrees with the visual state",
              r != "missing" and r["agrees"],
              f"{r} — a class-only selection is visible and unannounced")
    pg.close()

    # ------------------------------------------------------------ section 5
    print("\nA11Y 5 — asynchronous status reaches a live region")
    # Posting, autosave, copy and the Undo affordance all wrote into nodes with
    # no live semantics, so none of them was announced. These ARE attribute
    # assertions: a live region is an attribute contract, and there is nothing
    # behavioural to press.
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    browsing.goto(pg, BASE, "/")
    for _id, why in (("toast", "autosave, copy, and the Undo affordance"),
                     ("postStatus", "posting started / succeeded / failed"),
                     ("postedStatus", "server-side deletion from Your Skribls")):
        r = pg.evaluate("""(id) => {
            const el = document.getElementById(id);
            if (!el) return null;
            return { role: el.getAttribute('role'),
                     live: el.getAttribute('aria-live'),
                     atomic: el.getAttribute('aria-atomic') }; }""", _id)
        check(f"#{_id} is a live region — it carries {why}",
              r is not None and r["live"] == "polite"
              and r["role"] == "status",
              str(r))
        check(f"#{_id} announces atomically",
              r is not None and r["atomic"] == "true",
              f"{r} — without it a node whose children change announces only "
              "the fragment, which for the toast is the bare Undo button")
    pg.close()
    browser.close()

# ------------------------------------------------------------------ section 6
print("\nA11Y 6 — no meaningful text under the AA contrast floor")
# Computed from the stylesheet rather than sampled from a screenshot: a token
# used on four surfaces has four ratios, and the failing one is whichever
# surface happens not to be in the screenshot.
_css = (ROOT / "skribl" / "static" / "styles.css").read_text(encoding="utf-8")


def _token(name):
    m = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(name), _css)
    return m.group(1) if m else None


SURFACES = ["surface-base", "surface-raised", "surface-panel", "surface-control"]
_surf = {s: _token(s) for s in SURFACES}
check("the surface ramp resolves", all(_surf.values()), str(_surf))

# The tokens that CANNOT pass AA — see the note at --text-dim's definition.
# --text-dim survives for disabled controls and placeholders, where the
# requirement does not apply. What this asserts is that nothing a user READS
# uses one, and (below) that one which nothing uses at all does not exist.
#
# The list keeps the names v281 DELETED, deliberately: it is what stops them
# being reintroduced as definitions, and the census below is what tells the
# difference between "gone" and "back, unused, waiting to be picked up".
FAILING = ("text-faint", "text-dim", "text-faint-2")
_body = re.sub(r"/\*.*?\*/", "", _css, flags=re.S)

# The permitted uses: disabled controls and placeholders, where WCAG's text
# contrast requirement does not apply. A ratchet — it may shrink and must never
# grow without a reason written here.
#
# THE FIRST VERSION OF THIS GATE WAS VACUOUS, and only a mutation said so. Its
# exempt pattern included `--text-`, meant to skip the lines that DEFINE the
# tokens — and `var(--text-dim)` contains `--text-`, so it skipped every USE as
# well. Putting a failing token back on .tune-hint left the suite at 37/37.
# The definitions are excluded by shape instead: a definition is `--name:` at
# the start of a declaration, a use is `var(--name)`.
_EXEMPT = re.compile(r":disabled|::placeholder|:not\(:checked\)|\[disabled\]")
_DEFINITION = re.compile(r"^\s*--[a-z0-9-]+\s*:")
_bad = []
for _line in _body.split("\n"):
    if _DEFINITION.match(_line):
        continue
    if not any(f"var(--{t})" in _line for t in FAILING):
        continue
    if _EXEMPT.search(_line):
        continue
    _bad.append(_line.strip()[:90])
check("no readable text uses a token that fails AA",
      not _bad,
      "; ".join(_bad[:4]) + (f" (+{len(_bad) - 4} more)" if len(_bad) > 4 else ""))

# A DEFINED TOKEN IS AN INVITATION. v281 found --text-faint and --text-faint-2
# still in :root — the v278 audit had taken them off the last things they
# coloured (--text-faint-2 was on .accordion-count at 3.47:1) and left the
# definitions behind. Nothing referenced them, so the assertion above was green
# and stayed green; the trap is that the next person wanting faint text reaches
# for the faintest name in the ramp and reintroduces the finding. Both were
# deleted. What must hold from here is narrower than "unused tokens are bad":
# a token on THIS list either earns its place in a context the requirement does
# not reach, or it does not exist.
_defined = {t for t in FAILING
            if re.search(r"^\s*--%s\s*:" % re.escape(t), _css, re.M)}
_used = {t for t in FAILING if f"var(--{t})" in _body}
_idle = sorted(_defined - _used)
check("no failing token is defined with nothing using it",
      not _idle,
      ", ".join("--" + t for t in _idle) +
      " — defined, referenced by no rule, and unable to pass: use it somewhere "
      "the contrast requirement does not reach, or delete the definition"
      if _idle else
      f"{len(_defined)} of {len(FAILING)} defined, each used: " +
      ", ".join("--" + t for t in sorted(_defined)))

_muted = _token("text-muted")
_worst = min(ratio(_muted, s) for s in _surf.values())
check("the token that replaced them clears 4.5:1 on EVERY surface",
      _worst >= 4.5,
      f"worst {_worst:.2f}:1 — a token that passes on the darkest panel and "
      "fails on the lightest one has not fixed anything")

passed = sum(1 for ok, _ in results if ok)
bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed"
      + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
