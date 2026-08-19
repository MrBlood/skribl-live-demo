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
PARALLEL_RATCHET = 58
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
