"""Pad and Flip are two implementations of one product, and they drift.

THIS IS THE DIAGNOSIS SUITE. Nearly every fault this codebase has shipped
recently was the same failure, not four different ones: a change landed on one
surface and not the other. Documented instances, all found in production or by
a user rather than here:

  * `loadSkribl` restoring media — the MUSIC branch was split so drawer UI runs
    only on the editor; the PHOTO branch was not, and threw on every shared link
    carrying a photo.
  * Where "watch it" opens — Flip used an <a target="_blank">, Pad used a
    <button> doing location.href, so two of three paths opened a tab and one
    navigated the host's document away.
  * Script loading — every script in the editor template carried `defer`; not
    one in the Flip template did.
  * `skriblPostHeaders` is defined twice, once in app.js and once in flip.js.

The measurement underneath: app.js and flip.js share ZERO runs of six or more
identical lines, and yet define 57 functions with the same names. They are not
copies that fell out of sync — they are parallel implementations of the same
responsibilities, which is worse, because there is no diff that will ever show
you the divergence. Every fix has to be made twice and nothing checks the
second one.

None of this can be fixed by an assertion. What an assertion can do is make the
divergence a number that has to be looked at, and fail when a discipline the two
templates DO agree on quietly stops being shared.
"""
import pathlib
import re
import sys
from assertions import make_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "skribl" / "static"
TPL = ROOT / "skribl" / "templates" / "skribl"

results = []


check = make_check(results)


def scripts(template):
    return re.findall(r'<script src="[^"]*"[^>]*>',
                      (TPL / template).read_text(encoding="utf-8"))


print("SURFACES — the two editors load their scripts the same way")
for tpl in ("skribl_editor.html", "skribl_flip.html"):
    tags = scripts(tpl)
    blocking = [t for t in tags
                if not re.search(r'\b(defer|async)\b|type="module"', t)]
    check(f"{tpl}: every script tag is deferred",
          not blocking,
          f"{len(blocking)} of {len(tags)} block the parser: "
          + ", ".join(re.search(r"'([^']+)'", t).group(1)
                      for t in blocking[:3] if re.search(r"'([^']+)'", t))
          + " — the editor deferred all of its and Flip deferred none, which is "
            "the drift this suite exists for")

print("\nSURFACES — how far apart app.js and flip.js have grown")
FN = re.compile(r"^\s{0,2}(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
app_src = (STATIC / "app.js").read_text(encoding="utf-8")
flip_src = (STATIC / "flip.js").read_text(encoding="utf-8")
app_fns = {m.group(1) for line in app_src.split("\n") if (m := FN.match(line))}
flip_fns = {m.group(1) for line in flip_src.split("\n") if (m := FN.match(line))}
shared = sorted(app_fns & flip_fns)

# A RATCHET, not a target of zero. Some overlap is legitimate — both surfaces
# genuinely draw strokes — and collapsing it is a redesign, not a cleanup. The
# number is here so that it goes DOWN over time and so that anyone adding the
# 58th parallel implementation has to change this line and think about why.
# v211: 57 -> 58. The new shared name is startLoopPreviewNative — the native
# <audio> fallback for Preview Loop, reachable asynchronously when Web Audio
# cannot unlock — added to BOTH editors by the v210 review's F1 (Flip) after
# Pad got it in v209. That is exactly the "fix made twice" this ratchet exists
# to count, and it is counted honestly rather than hidden behind a different
# name in one file. The cure is the externalisation of the editor-only Web
# Audio loop into a shared lib (an old handoff's suggestion), which would take
# startWebAudioLoop, stopWebAudioLoop, webAudioLoopSongTime, and this
# fallback OUT of both files and move this number the right way.
# v213: 58 -> 60. The two new shared names are _eraserSize and _brushWidth.
#
# THINKING ABOUT WHY, which is what this line is for. Both are four-line
# ADAPTERS, not parallel implementations: the eraser multiplier lives once in
# lib/erasersize.js and the brush curve once in lib/brushes.js, and each wrapper
# only reads its own surface's globals and delegates. The v213 work went the
# right way overall — erasersize, pressure, brushes, shapes, mirror, constrain,
# strokelayers, gridoverlay and selection are all single implementations shared
# by both files, and the eraser one replaced SEVEN copies of `size * 3`.
#
# The adapters are duplicated because the two surfaces name their state
# differently (`erase` against `erasing`, mouse/touch against Pointer Events).
# The alternative — having the libs reach for those globals themselves — would
# couple a shared module to two sets of variable names and is worse than a
# visible four-line wrapper.
#
# So this raise buys a large NET reduction in duplicated logic at the cost of
# two counted names, and it is counted honestly rather than hidden by giving
# the wrapper a different name in one file. The cure named in v211 (moving the
# Web Audio loop into a shared lib) is still the way to move this number down.
PARALLEL_RATCHET = 60
check(f"app.js and flip.js define at most {PARALLEL_RATCHET} of the same "
      f"function names", len(shared) <= PARALLEL_RATCHET,
      f"{len(shared)}: {', '.join(shared[:8])}... — each one is a fix that has "
      "to be made twice, with nothing to catch the second")

print("\nSURFACES — fixes that were made on one side and must stay on both")
# Each of these was an actual production fault. They are asserted by shape
# rather than by string where possible, because the point is the behaviour.
posted = (STATIC / "lib" / "posted.js").read_text(encoding="utf-8")
check("the post body helper is shared, not implemented twice",
      "function skriblPackBody" in posted
      and "skriblPackBody" in (STATIC / "editor_post.js").read_text(encoding="utf-8")
      and "skriblPackBody" in flip_src,
      "lib/posted.js loads before both; a second copy is a second thing to drift")

editor_html = (TPL / "skribl_editor.html").read_text(encoding="utf-8")
flip_html = (TPL / "skribl_flip.html").read_text(encoding="utf-8")
check("both editors are told where the player opens",
      "SKRIBL_PLAYER_TARGET" in editor_html and "SKRIBL_PLAYER_TARGET" in flip_html,
      "Pad navigated in place and Flip opened a tab, for no reason beyond one "
      "being a <button> and the other an <a>")

check("neither surface hardcodes a link target",
      'target="_blank"' not in flip_html and 'target="_blank"' not in editor_html,
      "a literal here is right by luck and wrong to keep")

print("\nSURFACES — the chrome's colours live in one place")
# v230 phase 1 of light mode: 179 neutral literals moved out of the call sites
# and into :root, with their values unaltered — all nine rendered scenes came
# back pixel-identical. The point of the move is that a light palette is then a
# second block rather than an archaeology exercise, and the point of THIS
# assertion is that the move does not quietly erode: one hard-coded grey added
# next month is one control that stays dark when the theme flips, and nothing
# else would catch it.
#
# `#fff` and `#0d0f14` are excluded deliberately. White is almost always text on
# a coloured fill, which stays white either way; #0d0f14 is the CANVAS default,
# which is the document's own colour and must not follow the UI theme at all.
def neutral_literals(name):
    css = (STATIC / name).read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)      # prose quotes colours
    # where they are DEFINED — the bare :root ramp AND any themed override of
    # it (:root[data-theme="light"]), which is by definition a second block of
    # literals for the same tokens.
    css = re.sub(r":root(?:\[[^\]]*\])?\s*\{.*?\n\}", "", css, flags=re.S)
    out = []
    # The rgb()/rgba() FUNCTION form is a hard-coded neutral too, and the first
    # version of this only looked for #hex — so `background: rgb(23, 27, 35)`
    # sat on two controls and stayed dark in light mode with nothing to say so.
    # Pure black and pure white are skipped: they are the alpha washes, which
    # --wash-rgb already flips.
    for m in re.finditer(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*[,)]", css):
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        if max(r, g, b) - min(r, g, b) > 30:
            continue
        if (r, g, b) in ((0, 0, 0), (255, 255, 255)):
            continue
        out.append(f"rgb({r},{g},{b})")
    for m in re.finditer(r"#[0-9a-fA-F]{3,6}\b", css):
        h = m.group(0).lower()
        if h in ("#fff", "#ffffff", "#0d0f14"):
            continue
        v = h.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        if max(r, g, b) - min(r, g, b) <= 30:            # neutral enough to need flipping
            # var(--token, #fallback): the token always resolves, so the literal
            # after it is unreachable in practice.
            before = css[max(0, m.start() - 80):m.start()]
            if re.search(r"var\(\s*--[a-z0-9-]+\s*,\s*$", before):
                continue
            out.append(h)
    return out

stray = {n: neutral_literals(n) for n in ("styles.css", "flip.css")}
total = sum(len(v) for v in stray.values())
check("no hard-coded neutral outside :root in either sheet",
      total == 0,
      "; ".join(f"{n}: {', '.join(sorted(set(v)))}" for n, v in stray.items() if v)
      + " — every grey the chrome paints has to be a token, or it will not "
        "follow a light theme")

print("\nSURFACES — no stylesheet hides in a JavaScript string")
# FOUR runtime <style> elements were found here, in two duplicated pairs:
# editor_photo.js/flip.js built the slider-nudger sheet, editor_music.js/flip.js
# built the zoom-bar sheet. Being strings put them outside every colour audit —
# a ratchet reads .css files — which is why the +/- buttons beside every slider
# stayed dark after the whole rest of the chrome had flipped to light. And the
# copies had already drifted: only Pad's zoom bar carried its 640px rule.
#
# `element.style` is NOT what this bans. Positioning one node is a different
# thing from shipping a stylesheet; the eraser cursor sets its own cssText and
# is painted ON the canvas, which follows no theme.
injectors = []
for js in sorted((STATIC).glob("*.js")) + sorted((STATIC / "lib").glob("*.js")):
    body = js.read_text(encoding="utf-8")
    if re.search(r"createElement\(\s*['\"]style['\"]\s*\)", body):
        injectors.append(js.name)
check("no editor script builds a stylesheet at runtime",
      not injectors,
      ", ".join(injectors) or "CSS in a string is CSS no audit can read, and "
      "two copies of it drift with nothing to show the diff")

print("\nSURFACES — every module a page loads is a module that page can reach")
# THREE DEAD LOADS FOUND BY HAND IN ONE SWEEP, which is a pattern and not three
# incidents:
#
#   * the in-post macro and the library page both loaded lib/sharecard.js;
#     inlineplayer.js never reads window.SkriblShareCard, and the only real
#     reader was verify_inline.py evaluating band() IN the page.
#   * the player loaded lib/photofit.js, whose only consumer is lib/artwork.js
#     — an editor module that is not on that page. It cost 1,155 B of a ratchet
#     with SIX BYTES of headroom, and that headroom was the standing argument
#     against putting anything new on the player.
#
# A surface inherits an asset list from the surface it was copied from, and
# nothing notices when the requirement does not come with it. This is that
# check: for every lib/*.js a template loads, SOMETHING that template also
# loads must read one of the globals it exports.
#
# EXPORTS ARE PLURAL. lib/media_validation.js assigns eight globals and the
# ones actually read are the lowercase helpers; a check that took the first
# match would report it dead. Every `global.X =` is collected.
#
# SELF-INSTALLERS NEED NO READER, and listing them is the honest way to say so:
# lib/pillfit.js wires itself on DOMContentLoaded and exposes its API only for
# tests. An entry here is a claim that the module runs itself.
_SELF_INSTALLING = {"pillfit.js"}

_TPL = ROOT / "skribl" / "templates" / "skribl"
_ST = ROOT / "skribl" / "static"
_SURFACES = {"editor": "skribl_editor.html", "flip": "skribl_flip.html",
             "player": "skribl_player.html", "feed": "skribl_feed.html",
             "library": "skribl_library.html",
             "in-post": "_skribl_inline_player.html"}

def _scripts(path):
    """Script SRCs only — Jinja comments are stripped first, because a note
    saying a file is NOT loaded names it too. (That false positive turned up
    the first time this was run by hand.)"""
    body = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.S)
    return re.findall(r"<script[^>]*skribl_asset\('([^']+)'\)", body)

def _unread(asset, siblings):
    """True when nothing else the page loads names any global this module
    exports. EXPORTS ARE PLURAL — every `global.X =` counts."""
    body = (_ST / asset).read_text(encoding="utf-8")
    names = set(re.findall(r"(?:global|window)\.([A-Za-z_][A-Za-z0-9_]*)\s*=", body))
    if not names:
        return False          # exports nothing; it is a side-effect module
    return not any(n in src for a, src in siblings.items()
                   if a != asset for n in names)

_orphans, _exempted = [], {}
for _surf, _tpl in sorted(_SURFACES.items()):
    _p = _TPL / _tpl
    if not _p.is_file():
        continue
    _assets = _scripts(_p)
    _src = {a: (_ST / a).read_text(encoding="utf-8")
            for a in _assets if (_ST / a).is_file()}
    for _a in _assets:
        if not _a.startswith("lib/") or not (_ST / _a).is_file():
            continue
        if (_ST / _a).name in _SELF_INSTALLING:
            _exempted.setdefault((_ST / _a).name, []).append(_surf)
            continue
        if _unread(_a, _src):
            _orphans.append(f"{_surf}:{_a}")
check("no page loads a lib module nothing on that page reads",
      not _orphans, ", ".join(_orphans) +
      " — an asset list copied from another surface without the requirement "
      "that justified it; either something must read it or it must go")

# AN EXEMPTION NOTHING CHECKS IS WHERE THE NEXT DEAD LOAD HIDES. Each entry in
# _SELF_INSTALLING makes three claims, and all three go stale on their own:
# that some surface still loads it, that it still wires itself (so it needs no
# reader), and that it still NEEDS the exemption — once something on the page
# reads it, the entry stops being a statement and becomes cover.
_stale = []
for _name in sorted(_SELF_INSTALLING):
    _hits = _exempted.get(_name)
    if not _hits:
        _stale.append(f"{_name}: no surface loads it — drop the entry")
        continue
    _body = (_ST / "lib" / _name).read_text(encoding="utf-8")
    if "DOMContentLoaded" not in _body:
        _stale.append(f"{_name}: no longer wires itself, so it now needs a reader")
    _needed = False
    for _surf in _hits:
        _sib = {a: (_ST / a).read_text(encoding="utf-8")
                for a in _scripts(_TPL / _SURFACES[_surf]) if (_ST / a).is_file()}
        if _unread(f"lib/{_name}", _sib):
            _needed = True
    if not _needed:
        _stale.append(f"{_name}: something reads it on every surface — "
                      "the exemption is doing nothing and hiding the next one")
check("every self-installing exemption still earns its place",
      not _stale, "; ".join(_stale) or
      f"{len(_SELF_INSTALLING)} exemption(s), each loaded, self-wiring, and "
      "load-bearing — an entry here is a claim that the module runs itself")

# THE SHARED-MODULE INDEX CENSUS LIVED HERE AND IS GONE, which is the point.
# It checked that START-HERE.md's table agreed with the templates, and it found
# three wrong rows and three missing ones in v281. harness/gen_docs.py now
# GENERATES that table from the templates and each module's own opening
# sentence, so there is no second copy to disagree — and a gate that guards a
# fact nothing restates is pure cost. Derive, then delete, then gate.

print("\nSURFACES — stylesheets keep no rule nothing can match")
# 31 class names had rule-sets in styles.css, flip.css and player.css and were
# applied by NOTHING — no template, no script, no test, no example host. About
# 7.8 KB, and every byte of it served: a whole "More tools" drawer, a help
# button cluster, a fine-tune stepper, a size picker, a magnifier toggle, a tab
# slider, a loading spinner and its @keyframes. Dead CSS is quieter than dead
# JavaScript because nothing ever fails to load — the rule simply never matches.
#
# ONLY FULLY-DEAD RULE-SETS COUNT. A selector list like
# `.slider:focus, .opacity-slider:focus` keeps a dead fragment beside a live
# one, and trimming those is not worth it: the attempt ate a comment
# terminator, corrupted the shared .slider rule, and verify_sizeclass and
# verify_tray caught it. A fragment that can never match costs a few bytes and
# breaks nothing; a rule-set devoted entirely to a class nobody applies is the
# thing that accumulates.
_SHEETS = sorted(_ST.rglob("*.css"))
_decomment = lambda t: re.sub(r"/\*.*?\*/", "", t, flags=re.S)

_applied = []
for _p in ROOT.rglob("*"):
    if not _p.is_file() or ".git" in _p.parts or "__pycache__" in _p.parts:
        continue
    if _p.suffix in (".html", ".js", ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".sh"):
        _applied.append(_p.read_text(encoding="utf-8", errors="ignore"))
_applied = "".join(_applied)

def _rulesets(css):
    """(selector, depth) for every rule-set, at any nesting depth."""
    i, n, depth, start, stack, out = 0, len(css), 0, 0, [], []
    while i < n:
        if css.startswith("/*", i):
            j = css.find("*/", i + 2); i = (j + 2) if j != -1 else n; continue
        if css[i] == "{":
            stack.append(css[start:i]); depth += 1; i += 1; start = i; continue
        if css[i] == "}":
            if stack: out.append(stack.pop())
            depth -= 1; i += 1; start = i; continue
        i += 1
    return out

_dead_rules = []
for _sheet in _SHEETS:
    for _sel in _rulesets(_sheet.read_text(encoding="utf-8")):
        _clean = _decomment(_sel).strip()
        if not _clean or _clean.startswith("@"):
            continue
        _parts = [q.strip() for q in _clean.split(",") if q.strip()]
        if not _parts:
            continue
        if all(any(c not in _applied
                   for c in re.findall(r"\.([a-z][a-z0-9-]{2,})", q)) and
               re.findall(r"\.([a-z][a-z0-9-]{2,})", q)
               for q in _parts):
            _dead_rules.append(f"{_sheet.name}: {_clean.splitlines()[0][:52]}")

check("no stylesheet keeps a rule-set whose every selector is unmatched",
      not _dead_rules,
      "; ".join(_dead_rules[:5]) +
      (f" (+{len(_dead_rules) - 5} more)" if len(_dead_rules) > 5 else "") +
      " — a class nothing applies, styled anyway, and served to everyone"
      if _dead_rules else
      f"{len(_SHEETS)} stylesheets, every rule-set reachable by some class the "
      "tree actually applies")


print("\nSURFACES — what the player is made to download")
# Not a pass/fail on size: this is the number the JS-only byte ratchet in
# verify_player_isolation.py cannot see, reported so it stops being invisible.
player_html = (TPL / "skribl_player.html").read_text(encoding="utf-8")
sheets = re.findall(r"skribl_asset\('([^']+\.css)'\)", player_html)
css_bytes = sum((STATIC / s).stat().st_size for s in sheets if (STATIC / s).is_file())
check("the player's stylesheets are accounted for somewhere",
      bool(sheets),
      "no stylesheet found to measure")
print(f"    player loads {', '.join(sheets)} = {css_bytes:,} B raw for a "
      f"{len(player_html):,} B template")
print("    the byte ratchet in verify_player_isolation.py counts JavaScript "
      "only, so this walks past it")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
