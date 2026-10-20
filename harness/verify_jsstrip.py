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
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skribl.jsstrip import strip_bytes, strip_comments, strip_css_bytes   # noqa: E402
from assertions import make_check
import os

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
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
    # The two vendored files are expected: each one's only comment is its
    # licence banner, which the stripper keeps (`/*!`). mp4-muxer joined gifenc
    # when its notice went in and its sourceMappingURL line came out.
    check("no file silently fell back to its unstripped form",
          unchanged == ["gifenc.min.js", "mp4-muxer.min.js"],
          f"fell back: {unchanged or 'none'} — gifenc and mp4-muxer are expected "
          f"(their only comment is the licence banner)")

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
    # RAISED WITH verify_player_isolation's ledger, which names the cost: the
    # link page loads lib/chromefade.js since every full screen steps back
    # while it plays (+2,014 B, 151,751 measured, #456). The two suites read
    # the same template, and this pin was left behind when that one moved --
    # main went red on it, which is the "disagreement is a real signal" above.
    # And with it again for the lap fix (+16 B, 151,767 measured), and for a
    # finished drawing seen whole in full screen (+42 B, 151,809 measured),
    # and for the empty frame gone from "couldn't be found" (+26 B, 151,835),
    # and for a Flip's link resting on its poster page (+400 B, 152,235),
    # and for a replay that glides, lib/holdtiming.js untie() (+475 B,
    # 152,710), raised in verify_player_isolation and missed here: main went
    # red on it again, the same signal. And for the icons app.js writes,
    # aria-hidden on each since WAVE read them as images with no alternative
    # text (+171 B, 152,881 measured), raised in both places together. And
    # for the scrubber's clock riding over the finger (+305 B, 153,186
    # measured), raised in both places together again. And for the smart
    # fade on every full screen (+5,479 B: lib/smartfade.js on the link page
    # and app.js's wiring of it, 158,665 measured, #546), raised in
    # verify_player_isolation and missed here: main went red on it, the same
    # signal once more. And LOWERED by the carve that paid for it, in both
    # places together: Preview Loop, Test Seam and Play's music loop left
    # app.js for editor_music.js (-6,992 B, 151,673 measured). And LOWERED
    # again, in both places together, by one music editor: the music drawer's
    # controls (the edges' nudges, Match Drawing Time, Crossfade's and
    # Scroll's sync, the switch, the dead "Plays for" label) left app.js for
    # lib/musicdrawer.js, which the player never loads (-3,134 B, 148,536
    # measured). And RAISED, in both places together, by the owner's seven
    # yeses (+88 B, all app.js, 148,624 measured): the file's own words
    # ("Saved as a file", and "Opened your file" handed to loadSkribl, which
    # says what its caller tells it), and the shape row in Settings kept true
    # once a drawing opens, one line as restoreAutosave has.
    check("stripping keeps the player's JS under its ratchet",
          lean_total <= 148_629,
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

    # WHAT THE TARGET IS FOR, so the next person does not read it as slack:
    # START-HERE concluded from a function count that reaching it needs a
    # separate player entry point, and the v199 handoff concluded it does not.
    # The number is the evidence for the second, and it is met.
    #
    # THE RULE: this target comes out of the 5 editor globals and the
    # editor-only paths verify_player_isolation still counts on the player, not
    # out of this line. A target raised once per release is a record of
    # spending, not an achievement.
    #
    # It was broken once before, deliberately and in writing, to ship the
    # viewer's speed control with 25 B of margin -- and then reversed by the
    # carve the same note had named as the debt, rather than left at the spent
    # value with a comfortable margin. That is the only way this line is
    # allowed to move: name the debt when you spend, pay it when you can.
    #
    # WHAT IS LEFT OF THE DEBT, so the next person finds a figure and not a
    # feeling: ~1,365 lines of editor-only code sat in app.js and shipped to
    # every player, less the ~270 the music preview carve moved. The photo
    # drawer was carvable because its call sites were ALL already outside
    # app.js. The music preview's were not: clearCanvas and resetMediaForLoad,
    # which the player runs through loadSkribl, and Pad's Play, whose hidden
    # button the player's page keeps. Each now calls into editor_music.js
    # behind a typeof guard. Next, the Web Audio engine's wrappers
    # (startWebAudioLoop and the rest), which editor_draw.js calls too.
    #
    # AND A CARVE CAN BREAK THE EDITOR INVISIBLY. `bindEl('resetPhotoBtn',
    # 'click', resetPhotoAdjustments)` sits at app.js's TOP LEVEL and passes
    # the handler BY REFERENCE, so the name has to exist when that line runs --
    # and a function carved into a file that loads after app.js does not. The
    # Pad threw a ReferenceError on load and abandoned every line after it.
    # verify_boot's "the script reached its last line" is the only gate that
    # caught it. A binding travels with its function.
    #
    # "-109 B under" is what this line said when it FAILED, which reads as a
    # margin and is a deficit. Over and under are named, not signed.
    #
    # BROKEN THE SECOND TIME, deliberately and in writing (after v326, #546),
    # AND PAID. The owner chose the smart fade for every full screen, the link
    # page's included, and lib/smartfade.js took the player 4,865 B over. The
    # line moved to the spent value with the debt named, the owner chose how
    # to pay it ("1, carve it"), and the music preview carve paid it: the
    # line is back at 153,800, with 2,127 B to spare.
    _margin = 153_800 - lean_total
    check("REACHES the 153,800 target (strip + whitespace collapse)",
          lean_total <= 153_800,
          f"lean_total {lean_total:,} B — "
          + (f"{_margin:,} B of margin left" if _margin >= 0
             else f"OVER the target by {-_margin:,} B"))

    pg.close()

    # ---- CSS (v315, SK312-004): stripped stylesheets must style identically --
    # The player's stylesheet was 63% comments. Stripping it is only safe if
    # the page it styles is the same page, so this compares EVERY element's
    # full computed style with the stripped CSS against the same page with the
    # raw files swapped back in (the unbusted URL, which is never stripped).
    print("\nSTRIP — CSS: the stripped stylesheets style every element identically")
    _req = urllib.request.Request(BASE + "/api/skribls", method="POST",
        data=json.dumps({"frames": [{"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 4, "t": 0, "start": True},
                                                {"x": 60, "y": 40, "color": "#fff", "size": 4, "t": 40}],
                                     "strokeGroups": [2], "background": {"color": "#101418"}}],
                         "title": "CSS strip fixture", "visibility": "public"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(_req, timeout=15) as _r:
        _pid = json.loads(_r.read())["id"]
    # The other editor's page, fetched ahead (lib/editorswitch.js), is a
    # <link> added to the head when the page is idle: in one load and not yet
    # in the other, it shifts every element after it. It carries no style.
    SIG = """() => [...document.querySelectorAll('*')].filter(el => !el.matches('link[data-editor-ahead]')).map(el => {
        const cs = getComputedStyle(el), kv = [];
        for (let i = 0; i < cs.length; i++) kv.push(cs[i] + ':' + cs.getPropertyValue(cs[i]));
        // SORTED: Chromium enumerates custom properties in a different order on
        // each load, which made every element "differ" before this -- the
        // instrument, not the strip, going red.
        return el.tagName + '|' + kv.sort().join('|'); })"""
    CALM = "*,*::before,*::after{transition:none!important;animation:none!important;caret-color:auto!important}"
    # ONE CLOCK FOR BOTH LOADS. The gallery prints each post's age ("now",
    # "1m"), and the fixture above is seconds old: when the minute turned
    # between the stripped load and the raw one, the age text changed width and
    # four boxes beside it "differed" -- red on main in both CI jobs, green
    # locally on a gallery too short to reach it. Different TEXT, not different
    # styling; the instrument, not the strip. Both loads now read the same time.
    FROZEN = time.time()

    def _sig(path, raw):
        ctx = b.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        p = ctx.new_page()
        if raw:
            def _swap(route):
                u = route.request.url
                resp = route.fetch(url=u.split("?")[0])
                route.fulfill(response=resp, body=resp.body())
            p.route(re.compile(r".*\.css(\?.*)?$"), _swap)
        p.clock.set_fixed_time(FROZEN)
        p.goto(BASE + path, wait_until="load")
        p.add_style_tag(content=CALM)
        p.wait_for_timeout(1200)
        out = p.evaluate(SIG)
        ctx.close()
        return out

    for _path in ("/skribl-pad", "/flip", "/gallery", "/s/" + _pid):
        lean_sig, raw_sig = _sig(_path, False), _sig(_path, True)
        _diff = [i for i, (x, y) in enumerate(zip(lean_sig, raw_sig)) if x != y]
        check(f"{_path.split('/')[1] or _path}: every element computes the same style, stripped or raw",
              len(lean_sig) == len(raw_sig) and not _diff and len(lean_sig) > 20,
              f"{len(lean_sig)} vs {len(raw_sig)} elements; {len(_diff)} differ"
              + (f" (first: {lean_sig[_diff[0]][:80]}...)" if _diff else ""))

    _raw_css = (ROOT / "skribl" / "static" / "player.css").read_bytes()
    with urllib.request.urlopen(BASE + "/s/" + _pid) as _r:
        _html = _r.read().decode()
    _href = re.search(r'href="([^"]*player\.css\?v=[^"]*)"', _html)
    _served_css = _served(_href.group(1))[0] if _href else b""
    # BROKEN IN WRITING with the JavaScript's (after v326, #546): the smart
    # fade's band rules and their four --on-canvas tokens took the stylesheet
    # 681 B over 40,000. The line moves to the spent value and 25 B. THE DEBT
    # is not yet tied to a carve; the first candidate is the band's own
    # selectors, which name its controls in every rule where one class set by
    # lib/smartfade.js would do. Put to the owner with the JavaScript's.
    #
    # AND 73 B MORE, IN WRITING, at one full screen: the band's no-double-tap
    # rule (`touch-action: manipulation` on its buttons and its speeds, one
    # rule, 73 B served), which the Gallery's old full-screen bar had and the
    # link page's band never did. The Gallery and the Library wear that band
    # now, so the rule went where it comes from. Spent value and 25 B again.
    #
    # AND 71 B MORE, IN WRITING, at the owner's yes to no shadow on any full
    # screen (Q6): `.canvas-wrap:is(:fullscreen, .is-immersive-page)` drops
    # the canvas frame's ring and vignette, the link page's full screen and
    # the Pad's own (the same frame). Spent value and 25 B again.
    _css_target = 40_850
    check(f"the player's stylesheet is served stripped, under the {_css_target:,}-byte target (40,000 once its debt is paid)",
          _href is not None and 0 < len(_served_css) <= _css_target and len(_served_css) < len(_raw_css),
          f"{len(_served_css):,} B served of {len(_raw_css):,} B on disk")
    check("...and a legal banner in CSS survives the strip",
          b"/*! keep */" in strip_css_bytes(b"/*! keep */\np{color:red}/* gone */\nq{}"))
    b.close()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
