"""Static guards for the two failure modes the v132 refactor exposed.

Neither is catchable by a browser test at the root prefix, which is precisely
why both survived so long.

SECTION 1 — route literals.
    flip.js hardcoded fetch('/api/skribls') and a '/s/' fallback, and the server
    returned a hardcoded f"/s/{id}" in the 201 body. All three were CORRECT at
    the root and wrong everywhere else, so 632 assertions stayed green while a
    prefixed mount would have 404'd. Every route must be derived: url_for() on
    the server, an injected global on the client.

SECTION 2 — module-level names.
    Splitting app.py into a package left five NameErrors that no suite reached
    (MAX_CARD_BYTES, RATE_PENDING_TTL, RATE_CLEANUP_BATCH, ipaddress,
    IntegrityError). Only one was on a path a test walked. A name that no
    import provides is a crash waiting for the right request.

SPLIT BUDGET — what the player is forced to download: its reachable lines,
    the editor-only lines kept off it (a ratchet), and the script tags of its
    template and every partial it includes, which must name no editor bundle.

SPLIT FRESHNESS — player.css is byte for byte what harness/tools/cssgraph.py
    emits from styles.css (it runs the tool in a subprocess).

All of it reads source only — no server, no browser.
"""
import ast
import builtins
import importlib
import re
import sys
from pathlib import Path

import _layout
from assertions import make_check
import source

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []
check = make_check(results)


# Was defined here, and was the tree's only working copy while nine other sites
# matched code as raw text and needed it. Moved to harness/source.py in v299
# after a mutation defeated verify_ux by putting the token it looks for inside
# a comment; this name stays so the call sites below read as they did.
strip_comments = source.strip_js


# ---------------------------------------------------------------- section 1
print("\nSEAM 1 — no route literals in client code")

ROUTE_LITERALS = [
    (r"""['"]/api/skribls""", "/api/skribls"),
    (r"""['"]/s/['"]""", "/s/"),
    (r"""['"]/skribl-pad""", "/skribl-pad"),
]

# Vendored libraries are third-party and not ours to police.
VENDORED = {"gifenc.min.js", "mp4-muxer.min.js"}

js_files = [p for p in sorted(_layout.STATIC_DIR.rglob("*.js"))
            if p.name not in VENDORED]
check("found the client scripts to scan", len(js_files) >= 3,
      ", ".join(p.name for p in js_files))

for p in js_files:
    src = strip_comments(p.read_text(encoding="utf-8"))
    for pattern, label in ROUTE_LITERALS:
        hits = re.findall(pattern, src)
        check(f"{p.name} contains no {label!r} literal", not hits,
              f"{len(hits)} occurrence(s)")

print("\nSEAM 1b — every surface is handed its routes")
tpls = {p.name: p.read_text(encoding="utf-8")
        for p in _layout.TEMPLATES_DIR.glob("skribl_*.html")}
for name in ("skribl_editor.html", "skribl_flip.html", "skribl_player.html"):
    src = tpls.get(name, "")
    check(f"{name} exists", bool(src))
    check(f"{name} injects SKRIBL_API_BASE", "window.SKRIBL_API_BASE" in src)
    # The value must come from Jinja, not be typed in.
    m = re.search(r"window\.SKRIBL_API_BASE\s*=\s*([^;]+);", src)
    check(f"{name} derives it rather than hardcoding it",
          bool(m) and "skribl_api_base" in m.group(1),
          m.group(1).strip() if m else "not assigned")
    check(f"{name}'s config block is nonced",
          re.search(r'<script nonce="\{\{ csp_nonce \}\}">', src) is not None)

print("\nSEAM 1d — asset cache-busts are derived, not typed")
for name, src in sorted(tpls.items()):
    hand = re.findall(r"v='[0-9]+'", src)
    check(f"{name} has no hand-typed ?v= bust", not hand, ", ".join(hand[:3]))
    check(f"{name} routes assets through skribl_asset()",
          "url_for('skribl.static'" not in src)


print("\nSEAM 1c — the server builds share URLs from routes")
# Drop # comments, so prose about a fixed bug does not read as the bug. (This
# guard caught its own changelog comment on first run.) The implementation moved
# to harness/source.py in v299 so the other suites reading code as text could
# stop needing a copy they did not have.
strip_py_comments = source.strip_py


route_src = ""
for cand in (ROOT / "skribl" / "routes.py", ROOT / "app.py"):
    if cand.exists():
        route_src += strip_py_comments(cand.read_text(encoding="utf-8"))
check("no f\"/s/{...}\" literal in the route layer",
      not re.search(r'f"/s/\{', route_src))
check("the created-post response uses url_for",
      re.search(r'"url":\s*url_for', route_src) is not None)


# ---------------------------------------------------------------- section 2
print("\nSEAM 2 — every module-level name resolves")

pkg = ROOT / "skribl"
modules = ([f"skribl.{p.stem}" for p in sorted(pkg.glob("*.py"))
            if p.stem != "__init__"] if pkg.is_dir() else ["app"])
check("found modules to sweep", bool(modules), ", ".join(modules))

unresolved = []
for modname in modules:
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        check(f"{modname} imports", False, f"{type(e).__name__}: {e}")
        continue
    path = ROOT / (modname.replace(".", "/") + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    provided = set(dir(mod)) | set(dir(builtins))
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(n.name)
            a = n.args
            for arg in a.args + a.kwonlyargs + a.posonlyargs:
                bound.add(arg.arg)
            if a.vararg: bound.add(a.vararg.arg)
            if a.kwarg: bound.add(a.kwarg.arg)
        elif isinstance(n, ast.Lambda):
            for arg in n.args.args: bound.add(arg.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.ClassDef):
            bound.add(n.name)
    missing = sorted({(n.id, n.lineno) for n in ast.walk(tree)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                      and n.id not in provided and n.id not in bound})
    check(f"{modname}: all names resolve", not missing,
          ", ".join(f"{n}@{l}" for n, l in missing[:4]))
    unresolved.extend(missing)

check("no unresolved names anywhere in the package", not unresolved,
      f"{len(unresolved)} total")



# ---------------------------------------------------------------- section 3
print("\nSPLIT BUDGET — what the player is forced to download")

# app.js serves BOTH the editor and the read-only player, so every /s/<id>
# visitor downloads the eraser cursor, the export pipeline, the post composer and
# the autosave machinery in order to watch a drawing. On a social feed, where
# most traffic is viewing rather than authoring, that is the cost that matters.
#
# CAVEAT, learned the hard way: this call graph is built with a REGEX, and a
# regex misses real call sites (optional chaining, aliases, property calls,
# template strings). A split driven by these numbers was attempted and REVERTED
# — functions the player genuinely needs were misclassified as editor-only. Use
# these figures to size the prize, NEVER as a safe-to-move list. See
# docs/REFACTOR-v132.md.
#
# This does not enforce a split. It measures the one that has not happened yet,
# so the number is visible, and it fails if editor-only code starts leaking into
# the player's reachable set — which is how a split becomes impossible to do
# later. Reachability is computed from the READ-ONLY PLAYER section by following
# calls transitively.
_appjs = (_layout.STATIC_DIR / "app.js").read_text(encoding="utf-8")
_lines = _appjs.split("\n")

_fn = re.compile(r"^\s{0,2}(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
_spans, _cur, _start, _depth, _open = {}, None, 0, 0, False
for _i, _l in enumerate(_lines):
    _m = _fn.match(_l)
    if _m and _cur is None:
        _cur, _start, _depth, _open = _m.group(1), _i, 0, False
    if _cur is not None:
        _depth += _l.count("{") - _l.count("}")
        if "{" in _l:
            _open = True
        if _open and _depth <= 0:
            _spans[_cur] = (_start, _i); _cur = None

check("app.js parses into a plausible number of functions",
      150 <= len(_spans) <= 400, f"{len(_spans)} functions")

_names = set(_spans)
_body = {n: "\n".join(_lines[a:b + 1]) for n, (a, b) in _spans.items()}
_calls = {n: {o for o in _names if o != n and re.search(r"\b" + re.escape(o) + r"\s*\(", _body[n])}
          for n in _names}

_marker = "// ==================== READ-ONLY PLAYER ===================="
check("the READ-ONLY PLAYER section marker still exists", _marker in _appjs,
      "the split boundary this measures is gone")
if _marker in _appjs:
    _p0 = _appjs[:_appjs.index(_marker)].count("\n")
    _p1 = next((i for i in range(_p0 + 1, len(_lines))
                if _lines[i].startswith("// ---------- Image / Music")), len(_lines))
    _ptext = "\n".join(_lines[_p0:_p1])

    _seeds = {n for n, (a, b) in _spans.items() if a >= _p0 and b <= _p1}
    _seeds |= {o for o in _names if re.search(r"\b" + re.escape(o) + r"\s*\(", _ptext)}
    _seen, _stack = set(), list(_seeds)
    while _stack:
        _f = _stack.pop()
        if _f in _seen:
            continue
        _seen.add(_f)
        _stack.extend(_calls.get(_f, set()) - _seen)

    _editor_only = _names - _seen
    _editor_lines = sum(_spans[n][1] - _spans[n][0] + 1 for n in _editor_only)
    _player_lines = sum(_spans[n][1] - _spans[n][0] + 1 for n in _seen & _names)

    print(f"    player-reachable: {len(_seen & _names)} functions / {_player_lines} lines")
    print(f"    editor-only:      {len(_editor_only)} functions / {_editor_lines} lines")

    # Baselines from the v134 measurement. These are a RATCHET, not a target: the
    # editor-only figure is what a split would remove from the player bundle, so
    # it must not shrink by code migrating INTO the shared set.
    #
    # It counted editor-only lines INSIDE app.js only — so the moment editor-only
    # code was actually EXTRACTED to its own file, the number fell (2467 -> 1765)
    # and this failed. Extraction is the outcome this measurement exists to
    # encourage, and the metric punished it. The fix is to count editor-only code
    # wherever it now lives: app.js's editor-only spans PLUS the files that exist
    # solely to keep editor code off the player. Parsed with the same span logic,
    # so the figures stay commensurable rather than mixing spans with raw line
    # counts.
    #
    _extracted = 0
    for _name in ("editor_export.js", "editor_post.js", "editor_menu.js",
                  "editor_music.js", "editor_photo.js", "lib/slidernudge.js",
                  "lib/musicdrawer.js"):
        _p = _layout.STATIC_DIR / _name
        if not _p.exists():
            continue
        _el = _p.read_text(encoding="utf-8").split("\n")
        _es, _ec, _est, _ed, _eo = {}, None, 0, 0, False
        for _i, _l in enumerate(_el):
            _m = _fn.match(_l)
            if _m and _ec is None:
                _ec, _est, _ed, _eo = _m.group(1), _i, 0, False
            if _ec is not None:
                _ed += _l.count("{") - _l.count("}")
                if "{" in _l:
                    _eo = True
                if _eo and _ed <= 0:
                    _es[_ec] = (_est, _i); _ec = None
        _extracted += sum(b - a + 1 for a, b in _es.values())

    # BY THE SCRIPT TAGS, NOT THE WORDS (v317 review; WORKING-AGREEMENTS: "a
    # check for absence must match the mechanism"). This was a substring search
    # over the template, so a comment explaining why the player does NOT load a
    # file would have failed it. Now: the player template and every partial it
    # includes, comments stripped, and only what a <script src> actually names.
    def _player_scripts():
        seen, srcs, todo = set(), set(), ["skribl_player.html"]
        while todo:
            name = todo.pop()
            if name in seen:
                continue
            seen.add(name)
            txt = _layout.template(name).read_text(encoding="utf-8")
            txt = re.sub(r"\{#.*?#\}", "", txt, flags=re.S)
            txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
            todo += [inc.split("/", 1)[-1] for inc in
                     re.findall(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]", txt)]
            for src in re.findall(r"<script\b[^>]*\bsrc=\"([^\"]+)\"", txt):
                m = re.search(r"skribl_asset\(\s*['\"]([^'\"]+)['\"]", src)
                srcs.add(m.group(1) if m else src)
        return srcs
    _pscripts = _player_scripts()
    _never = {"editor_export.js", "editor_post.js", "editor_menu.js", "editor_music.js",
              "editor_photo.js", "editor_shapes.js", "editor_draw.js", "editor_tune.js",
              "lib/sheetswipe.js", "lib/postsheet.js", "lib/canvasground.js",
              "lib/slidernudge.js", "lib/musicdrawer.js"}
    # lib/tappause.js LEFT this list on purpose: since the owner's replay picks
    # the shared player pauses on a tap too, through the same module rather than
    # a second copy of it (verify_replayspeed drives it there).
    check("the player's own scripts are found at all (else the next check proves nothing)",
          "app.js" in _pscripts and "lib/eventpoint.js" in _pscripts, str(sorted(_pscripts)))
    check("the extracted editor bundles are not loaded by the player",
          not (_never & _pscripts),
          f"loaded: {sorted(_never & _pscripts)} — the whole point of moving them is that the player never fetches them")
    # Nor fetched at RUN time: a createElement('script') or import() naming one
    # of them from inside a player script would pass the tag check. A loader
    # has to name the file, so every quoted string in the player's own scripts
    # is read for the names (a comment explaining an absence is not a string).
    _lits = re.compile(r"""(['"`])((?:\\.|(?!\1).)*?)\1""")
    _dyn = []
    for _src in sorted(_pscripts):
        _f = _layout.STATIC_DIR / _src
        if not _f.is_file():
            continue
        _code = re.sub(r"/\*.*?\*/", "", _f.read_text(encoding="utf-8"), flags=re.S)
        _code = re.sub(r"(?m)^\s*//.*$", "", _code)
        for _m in _lits.finditer(_code):
            for _name in _never:
                if _name.split("/")[-1] in _m.group(2):
                    _dyn.append(f"{_src}: {_m.group(0)[:60]}")
    check("...nor named in a string inside any script the player runs (no loader can fetch them)",
          not _dyn, "; ".join(_dyn[:4]) or f"{len(_pscripts)} player scripts read")

    _editor_total = _editor_lines + _extracted
    print(f"    editor-only extracted to their own files: {_extracted} lines")
    # 2200 -> 2190 at v317, and the reason is a move, not a leak. The Pad menu's
    # own swipe (about 57 lines) left editor_menu.js for lib/sheetswipe.js,
    # which the player never loads (the script-tag check above says so). The
    # first cut counted all of sheetswipe.js here instead, and a review of
    # this suite caught what that did: most of its ~210 lines are NEW code the
    # Library and gallery load too, so counting it inflated the figure by ~150
    # and let that much editor code leak unseen. Measured without it: 2193.
    # 2190 -> 2185 with the one pill, and the reason is a DELETION, not a leak:
    # lib/segslider.js places every pill now, so app.js's initPhotoFitSlider
    # (7 lines) and the canvas seg's positionSlider (9), and editor_music.js's
    # positionSegSlider, are gone rather than moved. Diffed function by
    # function against the tree before it: nothing editor-only became
    # player-reachable; the restore helpers the change added live in the
    # editor bundles (markPhotoFit in editor_photo.js). Measured: 2189.
    # 2185 -> 2070 with the shared Post sheet, and the reason is a move, not a
    # leak, exactly as at v317. Flip posts through the Pad's sheet now, so its
    # behaviour left editor_post.js for lib/postsheet.js, which both editors
    # load and the player never does (_never above names it). Measured function
    # by function against the tree before it: the six that moved (updateCharCount,
    # setState, syncSoundMark, openPost, closePost, applyKeyboardInset) and the 7
    # lines submit lost to them are the 134 lines the figure fell by, 2210 to
    # 2076, while app.js's player-reachable and editor-only sets did not move.
    # Not counted here wholesale, for v317's reason: its one span (attach) also
    # wraps the listeners editor_post.js wired outside any function, which were
    # never counted, so counting it would add about 160 lines and let that much
    # editor code leak unseen.
    # lib/slidernudge.js is counted above for the same reason editor_menu.js is:
    # the Pad's addSliderNudgers (an editor-only span of app.js) MOVED there so
    # Flip could share it, and the file holds that one function and nothing
    # new. Uncounted, the move read as 2110 -> 2067, a "leak" while the
    # player-reachable set stood still at 98 functions / 1680 lines. Counted:
    # 2119 (the rest is the marks the editor bundles now draw).
    # lib/musicdrawer.js is counted for the same reason, and the floor RISES
    # to meet it (2070 -> 2330). The music drawer's controls (the edges'
    # drags and nudges, Scroll, Crossfade, Match Drawing Time, Preview Loop,
    # Test Seam and the switch) left editor_music.js, editor_photo.js and
    # app.js's editor-only spans for it, and Flip's copies with them: one copy
    # for both editors, which only the editors load (_never above). Uncounted,
    # the move read as 2185 -> 1943, a "leak" while the player-reachable set
    # FELL, 100 -> 98 functions and 1730 -> 1714 lines. Counted: 2335, and
    # left at the old floor that would let 265 lines of editor code leak
    # unseen, which is v317's warning; so the floor follows the measurement.
    check("editor-only code has not leaked into the player's reachable set",
          _editor_total >= 2330,
          f"{_editor_total} lines editor-only ({_editor_lines} still in app.js, "
          f"{_extracted} extracted), was 2467 — something the player now calls "
          f"used to be editor-only")
    # 1700 -> 1730 at v287, measured 1701, and the SPENDING CAME FIRST — a
    # raise taken before removing the waste is a raise that hides it.
    #
    # What grew: the flip play loop now goes through lib/holdtiming.js's
    # displayAt(), because no instant of the live clock supplies progress 1
    # while a drawing page is still current, so nothing else could ever paint
    # that page's last stroke. Player code, in the player — not editor code
    # leaking in, which is what this assertion exists to catch and what the
    # sibling assertion below still measures (editor-only 1536 vs reachable
    # 1701, and the carves hold).
    #
    # Removed before asking: the two call sites each recorded what they had
    # painted, so drawFlipFrame() now records it once — one owner, and no call
    # site can forget. That and dropping an explanation already written in full
    # in lib/holdtiming.js took the addition from +17 lines to +11.
    #
    # NOT shaved to 1700. It landed one line over and the remaining line is
    # explanation with a right to exist; deleting prose to hit a ceiling is the
    # habit this file's own history warns about. 30 lines of headroom instead
    # of nought, so the next edit here is a decision rather than an accident.
    # 1730 -> 1760 at v297, measured 1738, and again the spending came first.
    #
    # What grew: paintStrokesStatic walks runs and draws a uniform see-through
    # one as a single canvas path, and makeStrokeCompositor gains pathFn to lay
    # that run onto the dry layer in order. That is the beading fix, and it is
    # PLAYER code in the player -- paintStrokesStatic is where a Flip document's
    # frames are rendered for a viewer, and a Motion Smear ghost written at
    # alpha 46/255 was painting at 83 there. Not editor code leaking in, which
    # is what this assertion exists to catch: the two assertions that measure
    # that both hold (editor-only 2638 against a floor of 2200, and still above
    # the reachable set).
    #
    # Removed before asking: no inline fallback for uniformRun, because the
    # overBudget call beside it already treats an absent lib as "not over
    # budget" rather than keeping a second copy; and the explanation inside
    # paintStrokesStatic cut to a pointer, the full version living in
    # lib/strokelayers.js and flip.js. Those took the addition from 20 lines to
    # 8. NOT shaved further -- deleting prose that exists nowhere else to hit a
    # ceiling is the habit the note above warns about, twice.
    # 1760 -> 1790 at v306, measured 1764, and the spending came first as
    # always: 11 lines of my own new prose came back out of playerFitScale,
    # layoutPlayerCanvas and the fullscreen block before this number moved, and
    # what is left is the branch itself plus four lines saying why a second
    # measurement exists.
    #
    # What grew: playerFitScale answers "what scale fits the box", and full
    # screen is a different box. Everything else in that function measures
    # `.app` — max-width 720px — and caps the scale at 1:1, which is right for
    # a drawing in a page column and wrong for one that owns the screen. The
    # canvas therefore stayed page-sized inside a wrapper that filled the
    # display. That is PLAYER code in the player, which is the distinction this
    # assertion exists to police, and the two assertions that police it
    # directly both still hold.
    #
    # AND THE HEADROOM WAS ALREADY GONE, which is the part worth recording.
    # v297 left 30 lines deliberately, "so the next edit here is a decision
    # rather than an accident". The fullscreen feature earlier in v306 spent
    # every one of them and landed on 1760 exactly — passing by zero — and
    # nothing said so, because a ratchet met exactly is green. The next line
    # over then read as this fix's fault rather than as the previous change
    # having used the last of the budget. 26 lines of headroom now, and a
    # figure met exactly is worth treating as a warning.
    #
    # The old failure message said "was 1339", a figure from before four carves
    # and three raises. A ratchet's message should state what it MEASURED, not
    # carry a number nobody has re-checked since v282.
    #
    # 1790 -> 1810 at v308 for the viewer's speed control, measured 1793.
    # Reported: "on players (across surfaces) should there be a speed control for
    # PAD? it sometimes draws too fast or slow and I'd like to control that".
    #
    # WHAT IT COSTS: segElapsed(), three lines, which is the ONE place the
    # replay clock is scaled -- the flip hold table, the stroke timeline and
    # the progress fraction all keep working off it without knowing a rate
    # exists; and showRate(), which writes the button's own label. `replayRate`
    # itself is not new: it has been in app.js since the Pad's preview row.
    #
    # TWO SPENDS WERE TRIED AND BOTH BOUGHT EXACTLY ZERO, which is worth
    # recording because the reasoning looked sound both times:
    #
    #   - collapsing three statements in the click handler onto one line. The
    #     handler is an ANONYMOUS arrow passed to addEventListener, and this
    #     measurement sums the spans of NAMED functions -- so nothing inside it
    #     is counted and nothing could be saved there.
    #   - moving the explaining comment out of that handler, on the theory
    #     that a comment inside a counted span costs what a statement costs.
    #     True in general (a span is start line to end line, prose included)
    #     and irrelevant here, for the same reason.
    #
    # The number did not move for either, and both were reverted rather than
    # left in: a collapsed line that buys nothing is just a less readable line.
    #
    # The one spend that WOULD have worked is inlining `* replayRate` at the
    # three sites segElapsed() serves, deleting the function for exactly the
    # three lines needed. Refused: that duplicates the rate multiplication at
    # three call sites, which is the shape of thing this file's notes keep
    # warning about, and the whole design virtue is that the clock is scaled
    # once. A ceiling is there to make an addition argue for itself, not to
    # buy three lines with a duplication.
    #
    # 1810 -> 1830 after v330, measured 1818, for replays laying back only what
    # changed (FUTURE 6z item 11: a two-hour drawing at a 3x phone's pace,
    # 13.9 -> 41.3 frames a second). What grew is makeStrokeCompositor: the
    # box each stroke op marks, its reset, and present() drawing under a clip
    # to it. PLAYER code in the player, the distinction this assertion polices.
    # Removed before asking: the explanation (sixteen lines) moved above the
    # function, out of the counted span, and the box's helper joined onto two
    # lines; 1838 -> 1818. NOT shaved further: what is left is the change.
    check("the player's reachable set has not ballooned",
          _player_lines <= 1830,
          f"{_player_lines} lines reachable against a ceiling of 1,830")
    # THIS ASSERTION USED TO READ `_editor_lines > _player_lines`, under the
    # name "a split is still worth doing". It was a TODO wearing a test's
    # clothes: it could only pass while the work was OUTSTANDING, and it went
    # red at v213 the moment the stroke capture path moved into editor_draw.js
    # and editor-only code left in app.js fell to 1,526 lines against 1,637
    # reachable by the player. A green suite meant the split had not been done.
    #
    # Inverted, so it now guards the achievement instead of the intention: what
    # is left in the shared file must STAY below the player's own reachable set.
    # Adding editor-only code back to app.js is what this catches, which is the
    # thing that actually costs the player bytes — and it is a direction, not a
    # fixed number, so it does not need editing every time either side moves.
    check("editor-only code left in app.js stays BELOW the player's reachable "
          "set (the carves hold; adding editor work back here is what fails)",
          _editor_lines <= _player_lines,
          f"editor-only still in app.js {_editor_lines} vs player-reachable "
          f"{_player_lines} — was 1,900+ vs 1,339 before the four carves")


# ---------------------------------------------------------------------------
print("\nSPLIT FRESHNESS — player.css is what the tool makes from styles.css")
# verify_cssplit has asked this since the split, and it is right; but it also
# boots a server and a browser, so it runs only AFTER merge. #259 edited
# styles.css without re-emitting, passed its pull request, and turned main red
# on this one line (v317). The regeneration itself needs neither a server nor a
# browser, so the question lives here too, on the PR gate.
import shutil as _sh, subprocess as _sp, tempfile as _tf
_live = ROOT / "harness" / "tools" / "css_live.json"
_dir = Path(_tf.mkdtemp())
_out = _dir / "player.css"
try:
    _run = _sp.run([sys.executable, str(ROOT / "harness" / "tools" / "cssgraph.py"),
                    "--emit", str(_live), str(_out)], cwd=ROOT, capture_output=True,
                   text=True, timeout=120)
    _rc, _err = _run.returncode, (_run.stderr or "")[-500:]
except _sp.TimeoutExpired:
    _rc, _err = "timeout", "cssgraph did not finish in 120 s"
_committed = (ROOT / "skribl" / "static" / "player.css").read_text(encoding="utf-8")
_fresh = _out.read_text(encoding="utf-8") if _out.exists() else ""
# The same command emits the band's sheet beside it (fullband.css: the link
# page's full screen for the Gallery and the Library), from the same source.
_band_committed = (ROOT / "skribl" / "static" / "fullband.css").read_text(encoding="utf-8")
_band_fresh = (_dir / "fullband.css").read_text(encoding="utf-8") if (_dir / "fullband.css").exists() else ""
# And the Gallery section's (gallerysection.css: /gallery's own rules under the
# section's root, for a host's Skribls page; the owner's B, after v330), made
# by the same command from /gallery's <style> and component sheets and that
# band. An edit to /gallery's look not re-emitted here is a host whose cards
# no longer match: red on the pull request, as the band is.
_section_committed = (ROOT / "skribl" / "static" / "gallerysection.css").read_text(encoding="utf-8")
_section_fresh = (_dir / "gallerysection.css").read_text(encoding="utf-8") if (_dir / "gallerysection.css").exists() else ""
_sh.rmtree(_dir, ignore_errors=True)
check("player.css is byte for byte what cssgraph emits from styles.css "
      "(after editing styles.css: python3 harness/tools/cssgraph.py --emit "
      "harness/tools/css_live.json skribl/static/player.css)",
      _rc == 0 and _committed == _fresh,
      f"cssgraph exit {_rc}; committed {len(_committed):,} vs "
      f"regenerated {len(_fresh):,} chars" + (f"; stderr: {_err}" if _err else ""))
check("...and so is fullband.css, the band's sheet the same command writes beside it",
      _rc == 0 and _band_committed == _band_fresh,
      f"committed {len(_band_committed):,} vs regenerated {len(_band_fresh):,} chars")
check("...and so is gallerysection.css, /gallery's own rules for a host's Skribls page "
      "(after editing skribl_gallery.html's <style> or a sheet it loads, the same command)",
      _rc == 0 and bool(_section_fresh) and _section_committed == _section_fresh,
      f"committed {len(_section_committed):,} vs regenerated {len(_section_fresh):,} chars")

# ---------------------------------------------------------------------------
print("\nWARNING-CLEAN — every tracked Python file compiles without a SyntaxWarning")
# The v317 outside audit: verify_a11y.py carried a JavaScript regex's \\s in an
# ordinary Python string, an invalid escape that Python passes through with a
# SyntaxWarning (and will make an error). Harmless today; but the harness is
# part of the release evidence, and evidence should compile clean. Compiled
# with warnings as errors, one file at a time, so every offender is named.
import warnings as _w
_git = _sp.run(["git", "-C", str(ROOT), "ls-files", "*.py"], capture_output=True, text=True)
_noisy = []
for _rel in _git.stdout.split():
    with _w.catch_warnings():
        _w.simplefilter("error", SyntaxWarning)
        try:
            compile((ROOT / _rel).read_text(encoding="utf-8"), _rel, "exec")
        except SyntaxError as _e:
            _noisy.append(f"{_rel}:{_e.lineno} {_e.msg}")
check("no tracked Python file raises a SyntaxWarning (or fails to compile)",
      _git.returncode == 0 and len(_git.stdout.split()) > 50 and not _noisy,
      "; ".join(_noisy[:4]) or f"{len(_git.stdout.split())} files")

# ---------------------------------------------------------------------------
print("\nTHE PLAYHEAD — a host's read-only seam on the in-post player")
# docs/INTEGRATION.md, "Where the playhead is": player.playhead() answers
# { ms, playing } on the drawing's own clock, for any host (the Skribl site
# keeps it with a like; Skribl never depends on the site). Pinned here as
# source: the method is on the player, it returns those two and nothing more,
# it reads and never assigns or calls anything but the clock and Math.min, the
# guide names it, and the site reads where a drawing's playhead is only
# through it (never the suite's state().elapsedMs, not a host's to rely on).
# The player's own suite (verify_inline.py, "where the playhead is") plays it.
_ip = strip_comments((_layout.STATIC_DIR / "inlineplayer.js").read_text(encoding="utf-8"))
_m = re.search(r"\bplayhead:\s*function\s*\(\)\s*\{(.*?)\},\n", _ip, re.S)
_body = _m.group(1) if _m else ""
# Its answer's keys, read with every call's own parentheses folded away
# (innermost first, each to a mark that is not one), so a comma inside
# Math.min(...) is not taken for the next key.
_flat = _body
while re.search(r"\([^()]*\)", _flat):
    _flat = re.sub(r"\([^()]*\)", "\u2026", _flat)
_ret = re.fullmatch(r"\s*return\s*\{(.*)\};\s*", _flat, re.S)
_keys = re.findall(r"([A-Za-z_$][\w$]*)\s*:", _ret.group(1)) if _ret else []
check("the in-post player has playhead(), returning { ms, playing } and nothing else",
      _keys == ["ms", "playing"], f"keys {_keys}; {_body.strip()[:160] or 'no playhead method on the player'}")
_assigns = re.findall(r"(?<![=!<>])=(?!=)", _body)
_calls = sorted(set(re.findall(r"([A-Za-z_$][\w$.]*)\s*\(", _body)) - {"Math.min", "curMs"})
check("playhead() only reads: no assignment, and no call but the clock's (curMs) and Math.min",
      bool(_m) and not _assigns and not _calls and "curMs()" in _body and "totalMs" in _body,
      f"assignments {len(_assigns)}; other calls {_calls}")
_guide = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")
_gm = re.search(r"\*\*Where the playhead is\*\*(.*?)\n\n", _guide, re.S)
check("docs/INTEGRATION.md documents it: playhead(), its ms on the drawing's own clock, and playing",
      bool(_gm) and "player.playhead()" in _gm.group(1) and "`ms`" in _gm.group(1) and "`playing`" in _gm.group(1)
      and "own clock" in _gm.group(1), (_gm.group(1)[:120] if _gm else "no such section"))
_site_js = sorted((ROOT / "social" / "static").glob("*.js"))
_peek = [p.name for p in _site_js if "elapsedMs" in strip_comments(p.read_text(encoding="utf-8"))]
_reads = [p.name for p in _site_js if ".playhead()" in strip_comments(p.read_text(encoding="utf-8"))]
check("the site reads where a drawing's playhead is through playhead() alone, never state()'s elapsedMs",
      len(_site_js) >= 5 and not _peek and _reads, f"peeking: {_peek}; reading the seam: {_reads}")

# ---------------------------------------------------------------------------
print("\nA LINE THAT WAITS — no room and nothing shown until the drawing is first played")
# docs/INTEGRATION.md, "A line that waits" (Nov 13, the Skribl site's calm
# card, the owner's B): skribl_inline(..., line_waits=True) keeps the line out
# of sight and out of the layout at rest, the play button saying what the
# line would, and the first play opens it, gliding, for good. It took the
# place of the line's lead (after v330, the site's heart, now in the site's
# own row), whose rules paid for it. Pinned as source here; the player's own
# suite (verify_inline.py, "a line that waits") opens it and reads every
# frame, on a drawing and a Flip.
_macro = (_layout.TEMPLATES_DIR / "_skribl_inline_player.html").read_text(encoding="utf-8")
_macro_code = re.sub(r"\{#.*?#\}", "", _macro, flags=re.S)
_sig = re.search(r"\{%\s*macro\s+skribl_inline\((.*?)\)\s*-?%\}", _macro_code, re.S)
_css_raw = (_layout.STATIC_DIR / "inlineplayer.css").read_text(encoding="utf-8")
_css = re.sub(r"/\*.*?\*/", "", _css_raw, flags=re.S)
check("skribl_inline() takes line_waits (false unless given) and only then marks its line is-waiting; the line's"
      " lead is gone from the macro and the stylesheet, nothing of it left to pay for",
      bool(_sig) and re.search(r"\bline_waits=false\b", _sig.group(1)) is not None
      and re.search(r'<div class="skribl-inline-line is-muted is-silent\{% if line_waits %\} is-waiting\{% endif %\}">',
                    _macro_code) is not None
      and "lead" not in _sig.group(1) and "skribl-inline-lead" not in _macro_code and "skribl-inline-lead" not in _css,
      f"signature {(_sig.group(1)[-80:] if _sig else None)}")


def _sels(text):
    """A rule's selectors, split at its own commas (not those inside :is())."""
    out, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return out + [cur.strip()]


# Every rule, a @media's own included: (its selectors, its declarations).
_rules = [(_sels(m.group(1)), dict(kv.strip().split(":", 1) for kv in m.group(2).split(";") if ":" in kv))
          for m in re.finditer(r"([^{}@]+)\{([^{}]*)\}", _css)]


def _with(sel, prop):
    """The selectors of every rule that lists `sel` and sets `prop`."""
    return [ss for ss, d in _rules if sel in ss and prop in d]


def _decl(sels):
    """The declarations of the rule with exactly these selectors."""
    return next((d for ss, d in _rules if ss == sels), {})


_wait = {k.strip(): v.strip() for k, v in _decl([".skribl-inline-line.is-waiting"]).items()}
check("at rest a waiting line has no room and shows nothing: no height, no top margin, nothing seen, nothing"
      " spilling",
      _wait == {"height": "0", "margin-top": "0", "opacity": "0", "overflow": "hidden"}, str(_wait))
_open = re.search(r"\.skribl-inline-line\.is-opening\{([^{}]*)\}", _css)
_rm = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\.skribl-inline-line\.is-opening\s*\{\s*"
                r"transition:\s*opacity[^;}]*\}\s*\}", _css)
_tr = re.search(r"transition:([^;}]*)", _open.group(1)).group(1) if _open else ""
check("opening, its room and its top margin glide over the same time and it fades in after them; under Reduce"
      " Motion only the fade, in a rule that comes after the one it overrides (same weight, so the later wins)",
      bool(_open) and "height .3s" in _tr and "margin-top .3s" in _tr and re.search(r"opacity \.\d+s( \w+)? \.\d+s", _tr)
      and "overflow:hidden" in _open.group(1) and bool(_rm) and _rm.start() > _open.start(),
      f"opening {(_open.group(1) if _open else None)}; reduced {(_rm.group(0) if _rm else None)};"
      f" order {(_rm.start() if _rm else None)} after {(_open.start() if _open else None)}")
_skribl_parts = {"the macro": _macro_code, "inlineplayer.css": _css,
                 "inlineplayer.js": strip_comments((_layout.STATIC_DIR / "inlineplayer.js").read_text(encoding="utf-8"))}
_knows = sorted(f"{k}: {m.group(0)}" for k, v in _skribl_parts.items()
                for m in re.finditer(r"\b(?:lk-[\w-]+|likes?|heart|social)\b", v, re.I))
check("it is general: nothing of the player's (its markup, its stylesheet, its script) names a host's card or what"
      " a host puts on it",
      not _knows, "; ".join(_knows[:4]))
_lg = re.search(r"\*\*A line that waits\*\*(.*?)```", _guide, re.S)
check("docs/INTEGRATION.md documents it: line_waits=, with line_info for the play button's words, opening on the"
      " first play and staying, and what Reduce Motion keeps",
      bool(_lg) and "line_waits=True" in _lg.group(1) and "line_info" in _lg.group(1) and "first play" in _lg.group(1)
      and "stays" in _lg.group(1) and "Reduce Motion" in _lg.group(1), (_lg.group(1)[:140] if _lg else "no such section"))

# ---------------------------------------------------------------------------
print("\nMARKS ON THE LINE — a host's moments, as dots where the line puts them")
# docs/INTEGRATION.md, "Marks on the line" (after v330, the owner's D for the
# Skribl site's likes): skribl_inline(..., marks=[{ms, n}]) and
# player.marks(list) give the player a host's moments on the drawing's own
# clock; it draws a 5px dot over the scrubber for each where ITS LINE puts
# that moment (the playhead's own mapping), one dot standing for those that
# would overlap (data-n 1, 2, 3 for three or more), coloured by the host's
# tokens, taking no taps; and says when the playhead reaches one in normal
# play (skribl:mark, from the dot), never on a scrub, a seek or a jump.
# General: the lead's row above reads every part of the player for a host's
# words. Pinned as source here; verify_inline.py ("marks on the line") draws
# them, presses them and plays them, on a drawing and a Flip.
_ipjs = strip_comments((_layout.STATIC_DIR / "inlineplayer.js").read_text(encoding="utf-8"))


def _fn(name, src=None):
    """The body of `function name(...) { ... }` in the player, braces matched."""
    src = src or _ipjs
    m = re.search(r"\bfunction " + name + r"\s*\([^)]*\)\s*\{", src)
    if not m:
        return ""
    depth, i = 1, m.end()
    while depth and i < len(src):
        depth += (src[i] == "{") - (src[i] == "}")
        i += 1
    return src[m.end():i - 1]


_box = re.search(r'<div class="skribl-inline is-muted is-silent\{% if line %\}.*?aria-label="Play this Skribl">', _macro_code, re.S)
check("skribl_inline() takes marks (none unless given) and writes them onto the box as JSON, only when there is a"
      " line",
      bool(_sig) and re.search(r"\bmarks=None\b", _sig.group(1)) is not None and bool(_box)
      and re.search(r"\{%-?\s*if line and marks\s*%\}\s*data-skribl-marks='\{\{ marks\|tojson \}\}'\s*\{%-?\s*endif\s*%\}",
                    _box.group(0)) is not None,
      (_box.group(0)[-420:] if _box else "no box in the macro"))
_mm = re.search(r"\bmarks:\s*function\s*\(list\)\s*\{(.*?)\},\n", _ipjs, re.S)
check("the player reads them once, as it mounts, and a host changes them with marks(list), which answers the list"
      " it holds (a copy)",
      _ipjs.count("data-skribl-marks") == 1 and "JSON.parse(el.getAttribute('data-skribl-marks'))" in _ipjs
      and bool(_mm) and "marks = [].concat(list)" in _mm.group(1) and "return marks.slice()" in _mm.group(1),
      (_mm.group(1).strip()[:160] if _mm else "no marks() on the player"))
_where, _place, _reach, _frame, _play = (_fn(n) for n in ("where", "placeMarks", "reach", "frame", "play"))
check("a mark's place is the playhead's own: where() puts a moment through fracAt, the very mapping frac() gives"
      " the playhead; before the drawing comes, a replay's moment over the listing's play length (a Flip's line"
      " has none, so its marks wait for its pages)",
      re.search(r"function frac\(\)\s*\{\s*return payload && totalMs \? fracAt\(curMs\(\)\) : 0;\s*\}", _ipjs) is not None
      and "fracAt(ms)" in _where and "info.play > 0" in _where and "where(" in _place,
      _where.strip()[:200] or "no where()")
check("dots closer than their 5px are one, at their middle, standing for all of them (data-n 1, 2, or 3 for three or"
      " more)",
      "* W < 5" in _place and "d.n > 2 ? 3 : d.n" in _place and "l.n + d.n" in _place, _place.strip()[:200])
_mk = _decl([".skribl-inline-marks"])
_mi = _decl([".skribl-inline-marks i"])
_m2, _m3 = _decl(['.skribl-inline-marks [data-n="2"]']), _decl(['.skribl-inline-marks [data-n="3"]'])
check("they are 5px and take no taps, moving nothing: the layer lies over the scrubber, out of the flow, with no"
      " pointer events; each dot placed in it",
      _mk.get("position") == "absolute" and _mk.get("inset") == "0" and _mk.get("pointer-events") == "none"
      and _mi.get("position") == "absolute" and _mi.get("width") == "5px" and _mi.get("height") == "5px"
      and _mi.get("border-radius") == "50%" and "pointer-events" not in _mi,
      f"layer {_mk}; dot {_mi}")
check("their colour is the host's, by token: --mark, and --mark-2 and --mark-3 for two and for three or more, each"
      " falling back to --mark and that to --accent; a dot that comes fades in",
      _mi.get("--m") == "var(--mark,var(--accent,#7c5cff))" and _mi.get("background") == "var(--m)"
      and _m2.get("background") == "var(--mark-2,var(--m))" and _m3.get("background") == "var(--mark-3,var(--m))"
      and "opacity" in _mi.get("transition", "") and "@starting-style{.skribl-inline-marks i{opacity:0}}" in _css,
      f"dot {_mi}; two {_m2}; three {_m3}")
_calls = [m.start() for m in re.finditer(r"\breach\(", _ipjs)]
_fstart = _ipjs.find(_frame) if _frame else -1
check("reaching a dot is said in normal play alone: skribl:mark is sent only by reach(), reach() is called only as"
      " a frame plays, play() starts the count where the clock is, and a frame after a quarter second's gap tells"
      " nothing",
      _ipjs.count("skribl:mark") == 1 and "skribl:mark" in _reach and len(_calls) >= 4
      and all(_fstart <= c < _fstart + len(_frame) for c in _calls[1:])
      and "function reach(" in _ipjs[_calls[0] - 9:_calls[0] + 6] and "markAt = elapsed || -1" in _play
      and re.search(r"\bw - markWall < 250\b", _reach) is not None and "d.ms > markAt && d.ms <= t)" in _reach,
      f"{len(_calls)} reach( in the player; skribl:mark {_ipjs.count('skribl:mark')}; reach: {_reach.strip()[:120]}")
# The section runs to the paragraph after it, its words read with their
# line breaks as spaces.
_mg_ = re.search(r"\*\*Marks on the line\*\*(.*?)\nOne Skribl plays at a time", _guide, re.S)
_mgw = " ".join(_mg_.group(1).split()) if _mg_ else ""
check("docs/INTEGRATION.md documents it: marks= and player.marks(), on the drawing's own clock, where its line puts"
      " them, skribl:mark in normal play and never on a scrub, and the tokens that colour them",
      bool(_mg_) and all(w in _mgw for w in ("marks=", "player.marks(", "own clock", "where its line puts",
                                             "skribl:mark", "in normal play", "never for a scrub", "--mark")),
      (_mgw[:160] if _mg_ else "no such section"))
_site = {p.name: strip_comments(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "social" / "static").glob("*.js"))}
_scss = re.sub(r"/\*.*?\*/", "", (ROOT / "social" / "static" / "social.css").read_text(encoding="utf-8"), flags=re.S)
_draws = [n for n, s in _site.items() if "skribl-inline-marks" in s]
check("the site goes through the seam alone: likes.js gives the player its marks (marks()) and hears skribl:mark;"
      " no site script or style names the player's dots",
      ".marks(" in _site.get("likes.js", "") and "'skribl:mark'" in _site.get("likes.js", "") and not _draws
      and "skribl-inline-marks" not in _scss and "--mark:" in _scss,
      f"scripts naming the dots {_draws}; social.css names them {'skribl-inline-marks' in _scss}")

# ---------------------------------------------------------------------------
print("\nWHERE A CARD OPENS — a host's address for the Gallery's cards (card_url)")
# docs/INTEGRATION.md, "Where a Gallery card opens" (the owner's "I thought on
# card?", Nov 13): a host says, per request, where a card of Skribl's own
# Gallery opens on its pages (init_skribl card_url= or skribl.set_card_url: an
# address with __ID__). The section writes it on its root as data-skribl-open,
# and gallery.js then opens it from anywhere on a card that is the card's own,
# makes the title its link, and sends the ⋯'s Open, Copy link and Share there.
# Unsaid, nothing is written, and the Gallery is Skribl's own as it was.
# Pinned as source here; verify_hostseams renders it (per request, checked,
# app-local), and verify_socialposts section 12 taps it on the Skribl site.
_gsec = (_layout.TEMPLATES_DIR / "_skribl_gallery_section.html").read_text(encoding="utf-8")
_gsec_code = re.sub(r"\{#.*?#\}", "", _gsec, flags=re.S)
_gjs = strip_comments((_layout.STATIC_DIR / "gallery.js").read_text(encoding="utf-8"))
check("the section writes the host's address on its root, and only what skribl_card_url() answers, only when it"
      " answers",
      _gsec_code.count("data-skribl-open") == 1
      and re.search(r"\{%-?\s*set opens = skribl_card_url\(\) if skribl_card_url is defined else none\s*%\}", _gsec_code)
      is not None
      and re.search(r'\{%-?\s*if opens\s*%\}\s*data-skribl-open="\{\{ opens \}\}"\s*\{%-?\s*endif\s*%\}', _gsec_code)
      is not None, "the section's root" if "data-skribl-open" in _gsec_code else "no data-skribl-open in the section")
check("gallery.js reads it once, from the section's root, and makes a card's address by putting the drawing's id"
      " where __ID__ stands (every one), never by assembling a route",
      _gjs.count("data-skribl-open") == 1 and "root.getAttribute('data-skribl-open')" in _gjs
      and "opensTpl.split('__ID__').join(encodeURIComponent(id))" in _gjs, "")
_tile = _fn("tile", _gjs)
check("with it, a card's title is a link to that address and the card says where it opens (data-open); without,"
      " the title is the plain words it always was",
      "document.createElement(opens ? 'a' : 'div')" in _tile and "tt.href = opens" in _tile
      and "art.setAttribute('data-open', opens)" in _tile and "tt.draggable = false" in _tile,
      _tile[_tile.find("var opens"):_tile.find("var opens") + 200] if "var opens" in _tile else "no `opens` in tile()")
_ground = _gjs[_gjs.find("var OWN = "):_gjs.find("function load(")]
check("the card's ground opens it as Home's does: only on a card that has an address, never through a control of its"
      " own or the drawing's stage, never after a drag or a selection, and in a new tab with Ctrl, ⌘ or Shift or the"
      " middle button",
      ".tileStage" in _ground.split("\n", 1)[0] and "closest('.tile[data-open]')" in _ground
      and "if (moved(e) || selectedIn(card)) return null;" in _ground
      and "if (e.ctrlKey || e.metaKey || e.shiftKey) window.open(url, '_blank', 'noopener');" in _ground
      and "list.addEventListener('auxclick'" in _ground and "e.button !== 1" in _ground,
      _ground[:160] or "no ground handler")
_menu = _fn("openMenu", _gjs)
check("its ⋯: Open goes to the address in this tab, and Copy link and Share give it; without one, Open opens the"
      " player's page in a new tab, as always",
      "var url = opens || location.origin + tpl.replace('__ID__', encodeURIComponent(item.id));" in _menu
      and re.search(r"if \(opens\) window\.location\.assign\(opens\);\s*else window\.open\(url, '_blank', 'noopener'\);",
                    _menu) is not None
      and "copier(url)" in _menu and "url: url" in _menu, "")
_mods = (ROOT / "skribl" / "models.py").read_text(encoding="utf-8")
_init = (ROOT / "skribl" / "__init__.py").read_text(encoding="utf-8")
_pcu = _mods[_mods.find("def page_card_url"):_mods.find("def ", _mods.find("def page_card_url") + 10)]
check("the seam is asked per request and checked: set_card_url installs a callable (app-local with app=);"
      " page_card_url asks it, takes None or nothing as Skribl's own, and raises on an answer that is not an address"
      " with __ID__ in it; init_skribl takes card_url= and adds skribl_card_url() for the section",
      "def set_card_url(fn, app=None):" in _mods and '["card_url"] = fn' in _mods
      and "fn = _CARD_URL" in _pcu and 'get("card_url", _POLICY_UNSET)' in _pcu and "got = fn()" in _pcu
      and "if CARD_ID not in got:" in _pcu and "_safe_source_url(got) is None" in _pcu and _pcu.count("raise ") == 3
      and '_cards = kwargs.pop("card_url", None)' in _init and 'app.add_template_global(page_card_url, "skribl_card_url")' in _init
      and "set_card_url(_cards, app=app)" in _init and '"set_card_url"' in _init, _pcu[:120])
_knows_host = sorted({m.group(0) for src in (_gjs, _gsec_code, _pcu)
                      for m in re.finditer(r"social|blooby|/b/", src, re.I)})
check("it is general: nothing of Skribl's that does it (the section, gallery.js, the seam) names a host or a host's"
      " address", not _knows_host, f"{_knows_host}")
_cg = re.search(r"### Where a Gallery card opens \(`card_url`\)(.*?)\n### ", _guide, re.S)
check("docs/INTEGRATION.md documents it: per request, __ID__, None as Skribl's own, the card's ground, its title a"
      " link, ⋯ → Open, and a wrong answer raising; and the seams table names it",
      bool(_cg) and all(w in _cg.group(1) for w in ("per request", "__ID__", "None", "title is a link", "⋯ → Open",
                                                    "raises", "set_card_url"))
      and "| `card_url` |" in _guide, (_cg.group(1)[:120] if _cg else "no such section"))
_app = (ROOT / "app.py").read_text(encoding="utf-8")
_site_files = [f for f in (ROOT / "social").rglob("*") if f.suffix in (".py", ".html", ".js") and f.is_file()]
_site_writes = [str(f.relative_to(ROOT)) for f in _site_files if "data-skribl-open" in f.read_text(encoding="utf-8")]
check("the site goes through the seam alone: app.py installs it for the site's own pages (request.blueprint) with"
      " skribl.set_card_url, to its drawing's page, and nothing of the site writes the section's address itself",
      "skribl.set_card_url(where, app=app)" in _app and 'if request.blueprint != "social":' in _app
      and 'url_for("social.bloob_page", skribl_id="__ID__")' in _app and not _site_writes, f"{_site_writes}")

# ---------------------------------------------------------------------------
print("\nWHAT IS PLAYED MOST — recent_plays, the gallery's Hot for a host's own list")
# docs/INTEGRATION.md, "What is played most, among your own posts" (Nov 14,
# the Skribl site's Gallery of everyone, the map's step 3): plays in the last
# seven days, as a subquery a host joins to its own posts, so its Hot is one
# query on its own rows and never a query of Skribl's tables. Pinned as source
# here; verify_hostseams joins it in a throwaway host, and verify_socialposts
# section 13 ranks the site's Gallery by it.
_desc = (ROOT / "skribl" / "describing.py").read_text(encoding="utf-8")
_rp_fn = next((n for n in ast.parse(_desc).body if isinstance(n, ast.FunctionDef) and n.name == "recent_plays"), None)
_rp_code = ast.unparse(ast.Module(body=_rp_fn.body[1:], type_ignores=[])) if _rp_fn else ""
check("recent_plays is exported (skribl.__all__, from describing.py) and reads only: one subquery of the views in"
      " HOT_DAYS up to as_of, by public id (skribl_id) with their count (plays), running nothing (no session, no"
      " execute, nothing added, deleted or flushed)",
      '"recent_plays"' in _init and "from .describing import describe_posts, list_public_posts, recent_plays" in _init
      and bool(_rp_fn) and [a.arg for a in _rp_fn.args.kwonlyargs] == ["as_of"]
      and "timedelta(days=HOT_DAYS)" in _rp_code and ".subquery(" in _rp_code
      and "label('skribl_id')" in _rp_code and "label('plays')" in _rp_code
      and "SkriblView.created_at >= since" in _rp_code and "SkriblView.created_at <= as_of" in _rp_code
      and not re.search(r"session\(|\.execute\(|\.add\(|\.delete\(|\.flush\(|\.commit\(", _rp_code), _rp_code[:220])
check("it is general: nothing in it names a host or a host's rows",
      bool(_rp_code) and not re.search(r"social|blooby|Person|(?<!Skribl)Post\b", _rp_code), _rp_code[:120])
_rg = re.search(r"\*\*What is played most, among your own posts\*\*(.*?)\n\*\*", _guide, re.S)
check("docs/INTEGRATION.md documents it: a subquery joined outer to your own posts, skribl_id and plays, the last seven"
      " days, as_of held for a scroll-through, and that reading it counts nothing",
      bool(_rg) and all(w in _rg.group(1) for w in ("recent_plays(", "skribl_id", "plays", "as_of", "seven days", "counts no play"))
      and re.search(r"\bouter\b", _rg.group(1)) is not None,          # the word, not outerjoin in the sample
      (_rg.group(1)[:160] if _rg else "no such paragraph"))


def _skribl_rows_named(path):
    """Where a module of the site reaches Skribl's rows itself: Skribl's
    models by name, their module imported, or one of Skribl's tables named in
    a string of code (SQL), docstrings aside."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
            and isinstance(n.body[0].value.value, str)}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and re.fullmatch(r"Skribl[A-Z]\w*", n.id) and n.id not in ("SkriblRejected",
                                                                                          "SkriblUnavailable", "SkriblNotFound"):
            out.append(n.id)
        elif isinstance(n, ast.ImportFrom) and (n.module or "").startswith("skribl.models"):
            out.append("from " + n.module)
        elif isinstance(n, ast.Attribute) and n.attr == "models" and isinstance(n.value, ast.Name) and n.value.id == "skribl":
            out.append("skribl.models")
        elif (isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs
              and re.search(r"\bskribl_(views|posts|reports|post_media|drafts|rate_events|idempotency)\b", n.value)):
            out.append(repr(n.value[:40]))
    return out


_site_rows = {str(f.relative_to(ROOT)): _skribl_rows_named(f) for f in sorted((ROOT / "social").rglob("*.py"))}
_gal_code = source.read_py(ROOT / "social" / "gallery.py")
check("the site goes through the seam alone: no module of social/ reaches Skribl's rows itself (its models, their"
      " module, its tables in SQL), and the Gallery's Hot is recent_plays(), joined outer to the site's own posts",
      len(_site_rows) >= 10 and not any(_site_rows.values()) and "from skribl import recent_plays" in _gal_code
      and "recent_plays(as_of=as_of)" in _gal_code and "outerjoin(plays, plays.c.skribl_id == Post.skribl_id)" in _gal_code,
      f"{ {k: v for k, v in _site_rows.items() if v} }")

# ---------------------------------------------------------------------------
print("\nA PERSON'S DRAFTS — list_drafts, for a host's page that is theirs alone")
# docs/INTEGRATION.md, "A person's drafts on your own page" (Nov 14, the Skribl
# site's profile, its Drafts tab, the map's step 4): the list the editors' Your
# drafts shows, newest saved first, without payloads, by the id the host hands
# Skribl for the person; each opens in the editor that made it with
# ?draft=<id>, the editors' own hand-off. Pinned as source here;
# verify_hostseams asks it in a throwaway host, and verify_socialprofile
# section 16 opens one from the Skribl site's profile.
_drafts_src = (ROOT / "skribl" / "drafts.py").read_text(encoding="utf-8")
_ld_fn = next((n for n in ast.parse(_drafts_src).body if isinstance(n, ast.FunctionDef) and n.name == "list_drafts"), None)
_ld_code = ast.unparse(ast.Module(body=_ld_fn.body[1:], type_ignores=[])) if _ld_fn else ""
check("list_drafts is exported (skribl.__all__, from drafts.py) and reads only: the author's own rows, by the id the"
      " host hands Skribl, newest saved first, their payloads never read, nothing added, deleted, flushed or committed",
      '"list_drafts"' in _init and "from .drafts import list_drafts" in _init and bool(_ld_fn)
      and [a.arg for a in _ld_fn.args.args] == ["author_id"] and "_owner(author_id)" in _ld_code
      and "SkriblDraft.user_id == owner" in _ld_code and "defer(SkriblDraft.payload_json)" in _ld_code
      and "SkriblDraft.updated_at.desc()" in _ld_code
      and not re.search(r"\.add\(|\.delete\(|\.flush\(|\.commit\(|\.update\(|\.execute\(", _ld_code), _ld_code[:240])
check("it is general: nothing in it names a host or a host's rows",
      bool(_ld_code) and not re.search(r"social|blooby|site:|Person|(?<!Skribl)Post\b", _ld_code), _ld_code[:120])
_sdjs = strip_comments((_layout.STATIC_DIR / "lib" / "savedrafts.js").read_text(encoding="utf-8"))
_ofu = _fn("openFromUrl", _sdjs)
check("the editors open a draft named at their address as their own Your drafts does: ?draft=<id> read once and"
      " dropped from the address, the draft loaded from the store (the account's, signed in), work on the canvas"
      " asked about before anything replaces it, and the draft adopted, so Save goes on updating it",
      "get('draft')" in _ofu and "searchParams.delete('draft')" in _ofu and "history.replaceState" in _ofu
      and "backend.load(id)" in _ofu and "opts.hasContent && opts.hasContent()" in _ofu and "ask(id, rec)" in _ofu
      and "adopt(id, rec)" in _ofu, _ofu.strip()[:200] or "no openFromUrl")
_dg = re.search(r"\*\*A person's drafts on your own page\*\*(.*?)\n## ", _guide, re.S)
_dgw = " ".join(_dg.group(1).split()) if _dg else ""
check("docs/INTEGRATION.md documents it: skribl.list_drafts(author_id), newest saved first, no payload read, only on a"
      " page that is theirs alone, nobody refused, and ?draft=<id> on the editor that made it, which asks before"
      " anything replaces work on its canvas",
      bool(_dg) and all(w in _dgw for w in ("skribl.list_drafts(author_id)", "newest saved first", "No payload is read",
                                            "theirs alone", "refuses", "?draft=<id>", "asked about",
                                            "skribl.skribl_editor", "skribl.skribl_flip")),
      _dgw[:200] or "no such paragraph")
_prof_code = source.read_py(ROOT / "social" / "profiles.py")
check("the site goes through the seam alone: its profile's Drafts lists them with list_drafts, for the person whose"
      " page it is, and opens each at the editor's own address with draft=; no module of social/ reaches Skribl's"
      " drafts itself (their model, their table)",
      "from skribl import list_drafts" in _prof_code and "list_drafts(me.public_id)" in _prof_code
      and 'draft=d["id"]' in _prof_code and '".skribl_flip"' in _prof_code and '".skribl_editor"' in _prof_code
      and not any(v for v in _site_rows.values()), f"{ {k: v for k, v in _site_rows.items() if v} }")

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.
import sys
sys.exit(1 if bad else 0)
