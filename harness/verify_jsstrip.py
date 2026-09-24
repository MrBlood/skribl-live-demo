"""Is the JavaScript we serve still the JavaScript we wrote?

`skribl/jsstrip.py` removes comments on the way out, so the source keeps every
word and the player parses 78,768 fewer bytes. That is a rewrite of every JS
file on the site performed by a lexer written for this project, which is a large
claim resting on a small file.

THE LEXER IS NOT THE GATE, AND IT CANNOT BE. Its own round-trip check re-lexes
its own output with its own rules, so it agrees with itself by construction —
if it misreads a `/` as division it will misread it identically both times and
the check passes. Everything here is therefore independent of it:

  1. A REAL ENGINE PARSES THE OUTPUT. Chromium compiles every stripped file. The
     failure this exists for — a regex literal read as division, so `//` inside
     it eats the rest of the line — produces a SyntaxError here even though the
     lexer was satisfied.

  2. A REAL ENGINE AGREES ABOUT WHAT IT MEANS. Parsing is not enough: a strip
     that silently changed a value would still parse. Each adversarial fixture
     is EVALUATED before and after and the results compared, in the engine, not
     in Python.

  3. THE SURFACES STILL LOAD. Pad, Flip and the player, with zero page errors,
     against the stripped assets the browser actually fetches.

WHAT THE FIXTURES ARE. Every one is a case that a regex-based stripper gets
wrong, and the first is the line from app.js that motivated the whole file:
a regex literal containing an escaped `//`.

NOT TESTED HERE, DELIBERATELY: that the stripped player renders the same pixels.
`verify_visual.py`, `verify_parity.py` and `verify_cssplit.py` screenshot these
surfaces and would fail if it did not, and duplicating that here would mean two
places to update when a scene changes.
"""
import json
import re
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skribl.jsstrip import strip_bytes, strip_comments   # noqa: E402
from assertions import make_check

BASE = "http://127.0.0.1:5001"
STATIC = ROOT / "skribl" / "static"

results = []


check = make_check(results)


# Each fixture is (label, source). The source must be an expression-producing
# program: it is run as a function body and its return value compared.
FIXTURES = [
    ("regex containing an escaped slash-slash",
     r"""const re = /https:\/\//g; // trailing comment
         return 'a https:// b'.replace(re, 'X');"""),
    ("division that looks like a regex opener",
     """let a = 10, b = 2, c = 5; // comment
        return a / b / c;"""),
    ("string holding a block-comment opener",
     """const s = "/* not a comment */"; /* this one is */
        return s;"""),
    ("template literal holding both comment forms",
     """const x = 1;
        return `v${x}: // not a comment, /* nor this */`;"""),
    ("nested template substitution",
     """const n = 2;
        return `a${`b${n /* gone */}c`}d`;"""),
    ("regex after a statement-head close paren",
     """let out = ''; if (true) /ab/.test('ab') && (out = 'yes'); // gone
        return out;"""),
    ("division after a grouping close paren",
     """const q = (4 + 6) / 2; // gone
        return q;"""),
    ("division after a postfix increment",
     """let i = 8; return i++ / 2;"""),
    ("regex with a slash inside a character class",
     """const re = /[/]/; // gone
        return re.test('a/b');"""),
    ("comment markers inside a regex character class",
     r"""const re = /[/*]+/g; return 'a/*b'.replace(re, '-');"""),
    ("ASI: a multi-line comment is a line terminator",
     """let v = 1
        /* this comment
           spans lines */
        v = v + 1
        return v;"""),
    ("adjacent tokens separated only by a comment",
     """const a = 4, b = 2; return a/**/-b;"""),
    ("a line comment with no trailing newline at EOF",
     """return 42; // end"""),
    ("legal banner is not a comment for this purpose",
     """/*! @license kept */
        return 1;"""),
]


def _served(path):
    with urllib.request.urlopen(BASE + path) as r:
        return r.read(), dict(r.headers)


with sync_playwright() as sp:
    b = sp.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # ---- 1 & 2: an engine parses the output and agrees what it means --------
    print("\nSTRIP — a real engine, on the cases a regex gets wrong")
    for label, src in FIXTURES:
        stripped = strip_comments(src)
        outcome = pg.evaluate(
            """([a, b]) => {
                 const run = (s) => {
                   try { return {ok: true, v: JSON.stringify(new Function(s)())}; }
                   catch (e) { return {ok: false, v: String(e)}; }
                 };
                 return [run(a), run(b)];
               }""", [src, stripped])
        before, after = outcome
        check(f"{label}: same value before and after",
              before["ok"] and after["ok"] and before["v"] == after["v"],
              f"before={before['v']!r} after={after['v']!r}"
              + ("" if after["ok"] else "  <- stripped source did not compile"))

    check("the legal banner survived the strip",
          "@license" in strip_comments(FIXTURES[-1][1]),
          "a licence notice is terms, not bytes")
    check("and an ordinary block comment did not",
          "/* this one is */" not in strip_comments(FIXTURES[2][1]))

    # ---- every real file compiles ------------------------------------------
    print("\nSTRIP — every file we serve, compiled by Chromium after stripping")
    files = sorted(p for p in STATIC.rglob("*.js"))
    bad, saved, before_total = [], 0, 0
    for p in files:
        raw = p.read_bytes()
        lean = strip_bytes(raw, p.name)
        before_total += len(raw)
        saved += len(raw) - len(lean)
        ok = pg.evaluate(
            """(s) => { try { new Function(s); return ''; }
                        catch (e) { return String(e); } }""",
            lean.decode("utf-8"))
        if ok:
            bad.append(f"{p.name}: {ok}")
    check(f"all {len(files)} JS files still compile after stripping",
          not bad, "; ".join(bad)[:400] or
          f"{before_total:,} B -> {before_total - saved:,} B "
          f"({100 * saved // max(before_total, 1)}% removed)")

    # A file that FAILED to strip is not a failure — jsstrip returns the input
    # unchanged rather than risk a corrupt asset — but it is a silence worth
    # breaking, because the whole saving would quietly evaporate.
    unchanged = [p.name for p in files
                 if strip_bytes(p.read_bytes(), p.name) == p.read_bytes()
                 and b"//" in p.read_bytes()]
    check("no file silently fell back to its unstripped form",
          unchanged == ["gifenc.min.js"],
          f"fell back: {unchanged or 'none'} — gifenc is expected (its only "
          f"comment is the licence banner)")

    # ---- 3: the surfaces load against the stripped assets -------------------
    print("\nSTRIP — the surfaces the strip is served to")
    for label, url in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        errs.clear()
        pg.goto(BASE + url, wait_until="load")
        pg.wait_for_timeout(1500)
        check(f"{label} loads with no page error against stripped JS",
              not errs, "; ".join(errs)[:300])

    # ---- what the wire actually carries ------------------------------------
    print("\nSTRIP — the response, not the function")
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    busted = pg.evaluate(
        """() => Array.from(document.querySelectorAll('script[src]'))
                     .map(s => s.getAttribute('src'))
                     .find(s => s.includes('app.js'))""")
    body, headers = _served(busted)
    plain, plain_headers = _served(busted.split("?")[0])
    check("a busted app.js is served stripped",
          len(body) < len(plain),
          f"{len(plain):,} B on disk -> {len(body):,} B served")
    check("an UNbusted app.js is served whole",
          len(plain) == (STATIC / "app.js").stat().st_size,
          "no ?v= means no cache key; paying ~90 ms per request to save a "
          "transfer is the trade gzip level 1 already refuses")
    check("the two are not served under one ETag",
          headers.get("ETag") and headers.get("ETag") != plain_headers.get("ETag"),
          f"{headers.get('ETag')} vs {plain_headers.get('ETag')} — a tag that "
          f"names two byte sequences is simply wrong")
    check("Content-Length describes the body actually sent",
          int(headers.get("Content-Length", -1)) == len(body),
          f"{headers.get('Content-Length')} vs {len(body)}")
    again, _ = _served(busted)
    check("a second request is byte-identical (the cache is a cache)",
          again == body)

    # ---- the number the ratchet is about -----------------------------------
    print("\nSTRIP — what the player parses")
    # DERIVED FROM THE TEMPLATE, because the hand-maintained list this replaced
    # named a population the player does not have. It was
    # ["app.js", "lib/photofit.js", "lib/looptrim.js", "lib/audioloop.js"] —
    # four files, one of which (photofit.js) v281 removed from the player, and
    # missing five the player really loads: eventpoint, scrubkeys,
    # audiosession, holdtiming, strokelayers, framebitmap.
    #
    # It measured 144,847 B against a real 150,839 B, so the assertion below
    # was TRUE and proven with the wrong number, understating the player's JS
    # by 5,992 B and its headroom under the target by more than three times.
    # This is the same defect DECISIONS.md records for v280 — a suite asserting
    # the right thing about the wrong population — and the reason it survived
    # is that a hand list goes stale silently while the assertion stays green.
    #
    # The derived figure now agrees with verify_player_isolation.py's, which
    # reads the same template independently: two suites, one number, and a
    # disagreement between them is a real signal rather than two hand lists
    # drifting apart.
    _tpl = (ROOT / "skribl" / "templates" / "skribl" / "skribl_player.html")
    _body = re.sub(r"\{#.*?#\}", "", _tpl.read_text(encoding="utf-8"), flags=re.S)
    player_js = [a for a in re.findall(r"skribl_asset\('([^']+)'\)", _body)
                 if a.endswith(".js")]
    check("the player's JS list came from the template, not a hand list",
          len(player_js) >= 5 and "app.js" in player_js,
          ", ".join(player_js) or "no script tags found — the regex or the "
          "template's asset helper changed, and an empty list measures 0 B "
          "and passes every ratchet")
    src_total = sum((STATIC / f).stat().st_size for f in player_js)
    lean_total = sum(len(strip_bytes((STATIC / f).read_bytes(), f))
                     for f in player_js)
    # 155,843 -> 150,300 at v310, measured 149,820. A RATCHET SIX KILOBYTES
    # ABOVE THE MEASUREMENT IS NOT A RATCHET: it is a number that will let the
    # next four features through without any of them having to say why, which
    # is the state this file's own notes spent two releases arguing against.
    # The carve that bought the room (four photo-drawer functions out of app.js
    # and into editor_photo.js -- see the target below) is what makes lowering
    # it honest rather than aspirational, and 480 B of margin is the same order
    # the previous pin used.
    check("stripping keeps the player's JS under its ratchet",
          lean_total <= 150_300,
          f"{src_total:,} B of source -> {lean_total:,} B parsed")
    # START-HERE concluded from a function count that reaching 153,600 needs a
    # separate player entry point, and the v199 handoff concluded from a
    # predicted 153,741 that it does not. Both were wrong in opposite
    # directions: comment stripping plus token-aware whitespace collapse
    # (_collapse_whitespace) REACHES the target with room to spare. Assert it,
    # so any regression that pushes the player back over the line is loud.
    # What keep_banner would cost, printed rather than asserted: it is the
    # number jsstrip.strip_comments's docstring cites for having the flag off
    # by default, and a figure in a docstring that nothing re-measures is how
    # the previous one (4,491 B, over a player that never had those files)
    # stayed wrong across several releases.
    _banner = 0
    for _f in player_js:
        _m = re.match(r"\s*/\*.*?\*/", (STATIC / _f).read_text(encoding="utf-8"), re.S)
        if _m:
            _banner += len(_m.group(0))
    print(f"    keeping our own leading block comments would add {_banner:,} B "
          f"across {len(player_js)} player scripts (jsstrip's keep_banner=False)")

    # 153,600 -> 153,800, and this is a target moving rather than a ratchet, so
    # it says why. Full screen on /s/<id> cost the player 231 B of wiring; 171 B
    # of that was given back first by sharing one exit handler between the two
    # controls, dropping a typeof guard that was checking a function
    # declaration in its own scope, and building aria-pressed from the boolean.
    # The remaining 140 B buys the control the canonical share surface was
    # missing, which the owner asked for and then waived this number over.
    #
    # THE NUMBER HAS NOT MOVED AGAIN SINCE, and the fix that would have moved
    # it paid for itself instead. Making full screen actually ENLARGE the
    # drawing -- the wrapper filled the screen while the canvas kept its page
    # size -- wanted another 169 B. It came out of the same block rather than
    # out of this target: `_fsWrap` was a second handle on `canvasWrap`, the
    # exit helper was guarding a method that cannot be missing once something
    # is fullscreen, and the scale branch reads a flag `_syncFull` already
    # computes for the control's label instead of re-reading the document.
    #
    # WHAT THE TARGET IS FOR, so the next person does not read it as slack:
    # START-HERE concluded from a function count that reaching it needs a
    # separate player entry point, and the v199 handoff concluded it does not.
    # The number is the evidence for the second.
    #
    # AND THE RULE WRITTEN HERE WAS TESTED WITHIN THE HOUR. This paragraph
    # first said the margin was single digits and that the next spend had to
    # come out of carving rather than out of raising the line again. Making
    # full screen measure the WRAPPER's box instead of the window -- the
    # correct fix, because a scrollbar gutter can make the two differ -- then
    # wanted 20 B more than existed. It came out of the same block: a
    # `canvasWrap &&` guard on a reference dereferenced unguarded three hundred
    # lines above, two reads of document.fullscreenElement that the fsFull flag
    # already answers, and a one-line helper with a single caller. The number
    # did not move, and the margin is printed below so the next person does not
    # have to work it out.
    #
    # The rule stands: this target comes out of the 5 editor globals and the
    # editor-only paths verify_player_isolation still counts on the player, not
    # out of this line. A target raised once per release is a record of
    # spending, not an achievement.
    # "-109 B under" is what this line used to say when it FAILED, which reads
    # as a margin and is a deficit. Over and under are named, not signed.
    #
    # ---- v308: RAISED 153,800 -> 154,600, AGAINST THE RULE WRITTEN ABOVE ----
    #
    # Measured 154,535. The rule two paragraphs up says this target comes out
    # of carving, not out of this line, and that a target raised once per
    # release is a record of spending. This raise breaks that rule, on purpose,
    # and says so rather than quietly moving a number and writing a tidy
    # justification -- which is the failure mode the rule exists to prevent.
    #
    # WHAT HAPPENED. The margin here was 25 B. The viewer's speed control
    # (owner: "on players (across surfaces) should there be a speed control for
    # PAD? it sometimes draws too fast or slow") costs 760 B of stripped player
    # JS: segElapsed(), showRate(), the cycle handler, and one playbackRate
    # line so the music keeps up. Measured before and after, not estimated:
    # app.js 136,374 -> 137,134.
    #
    # WHAT WAS TRIED. Tightening the control itself -- collapsing showRate's
    # three writes, dropping the per-rate title sentences -- is worth about
    # 140 B of the 735, and the version in the tree already has most of it.
    # Nothing else in the feature is removable without deleting the feature.
    #
    # WHAT WAS NOT TRIED, AND IS THE DEBT. The carve the rule points at: the
    # five editor globals verify_player_isolation still counts on the player
    # (GLOBALS_RATCHET 5, target 0) and the editor-only paths beside them.
    # That is a real piece of work in code this change does not otherwise
    # touch, and doing it badly at the end of a long session is how a player
    # regression ships. It is named here so the next person finds a debt
    # rather than a mystery, and so the owner can reverse this trade -- the
    # honest alternatives were "carve first, ship the control after" and "do
    # not ship the control", and both were available.
    #
    # The 800 B is the measurement plus 65 B, not a round number chosen for
    # comfort: the next addition should have to argue as this one did.
    #
    # ---- v310: LOWERED 154,600 -> 153,800, WHICH IS THE RAISE GIVEN BACK ----
    #
    # Measured 149,820, so the target is met with 3,980 B to spare -- met for
    # the first time since it was set, and met by the carve the note above
    # named as the debt rather than by another move of the line.
    #
    # WHAT WAS CARVED. Four functions out of app.js and into editor_photo.js:
    # normalizePhotoDataURL, resetPhotoAdjustments, beginPhotoDrag and
    # dragZoomPan, 177 lines whose every call site was already in an
    # editor-only module. A person reading a shared Skribl has no photo drawer
    # and was downloading its upload decoder on every link. app.js 137,796 ->
    # 132,419 B parsed; lean_total 155,214 -> 149,820.
    #
    # THE RAISE IS REVERSED, NOT JUST SURVIVED. v308's note said the honest
    # alternatives were "carve first, ship the control after" and "do not ship
    # the control", and that it was named "so the owner can reverse this
    # trade". The owner did: "do the right thing. Make it a cleaner better
    # tree." So the number goes back to what it was before that release spent
    # it, rather than being left at the spent value with a comfortable margin.
    #
    # WHAT IS LEFT OF THE DEBT, so the next person finds a figure and not a
    # feeling: 1,365 lines of editor-only code still sit in app.js and still
    # ship to every player. The photo drawer was the cluster whose call sites
    # were ALL already outside app.js, which is what made it safe to move at
    # the end of a long session. The music preview cluster (~223 lines:
    # startWebAudioLoop, startLoopPreviewNative, playNativeLooped,
    # startLoopPreview, playMusicLooped) is the next one and is harder,
    # because its callers are still inside app.js.
    #
    # AND THE CARVE BROKE THE PAD ONCE, which is worth recording because the
    # failure was invisible to every gate but one. `bindEl('resetPhotoBtn',
    # 'click', resetPhotoAdjustments)` sits at app.js's TOP LEVEL and passes
    # the handler BY REFERENCE, so the name has to exist when that line runs --
    # and a function carved into a file that loads after app.js does not. The
    # Pad threw a ReferenceError on load and abandoned every line after it.
    # verify_boot's "the script reached its last line" is what caught it. The
    # binding travels with the function now.
    _margin = 153_800 - lean_total
    check("REACHES the 153,800 target (strip + whitespace collapse)",
          lean_total <= 153_800,
          f"lean_total {lean_total:,} B — "
          + (f"{_margin:,} B of margin left" if _margin >= 0
             else f"OVER the target by {-_margin:,} B"))

    pg.close()
    b.close()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
