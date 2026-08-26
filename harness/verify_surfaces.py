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

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "skribl" / "static"
TPL = ROOT / "skribl" / "templates" / "skribl"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


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
# Audio loop into a shared lib (HANDOFF-NEXT-SESSION.md), which would take
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
    css = re.sub(r":root\s*\{.*?\n\}", "", css, flags=re.S)  # where they are DEFINED
    out = []
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
