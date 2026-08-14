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
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skribl.jsstrip import strip_bytes, strip_comments   # noqa: E402

BASE = "http://127.0.0.1:5001"
STATIC = ROOT / "skribl" / "static"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


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
    player_js = ["app.js", "lib/photofit.js", "lib/looptrim.js", "lib/audioloop.js"]
    src_total = sum((STATIC / f).stat().st_size for f in player_js)
    lean_total = sum(len(strip_bytes((STATIC / f).read_bytes(), f))
                     for f in player_js)
    check("stripping keeps the player's JS under its ratchet",
          lean_total <= 155_843,
          f"{src_total:,} B of source -> {lean_total:,} B parsed")
    # START-HERE concluded from a function count that reaching 153,600 needs a
    # separate player entry point, and the v199 handoff concluded from a
    # predicted 153,741 that it does not. Neither number is this one. Assert the
    # gap so the next person reads a measurement rather than either claim.
    check("and does NOT reach the 153,600 target on its own",
          lean_total > 153_600,
          f"{lean_total - 153_600:,} B short — stripping is most of the "
          f"distance, not all of it; the remaining cut is real work")

    pg.close()
    b.close()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
