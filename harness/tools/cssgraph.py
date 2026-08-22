"""Which blocks of styles.css can a player page never match?

NOT A SECTION SPLIT. styles.css carries 35 section banners and most of them read
editor-only — "Post composer sheet", "Help button + drawer", "More tools drawer".
Cutting along those names is the same move that nearly swallowed initBrandFit
during the JS extraction: the banner describes what the author was thinking
about, not what the rules match. This asks the browser instead.

METHOD. Parse styles.css into top-level blocks, keeping each block's byte range
so the split can be a verbatim move rather than a rewrite. For every block,
collect its selectors — recursing into @media, which holds most of the file's
responsive rules — and ask a real player page whether any of them matches
anything, across several scenes.

WHAT IS DELIBERATELY NOT CLASSIFIED, and why each would be a bug to cut:

  @keyframes / @font-face   have no selectors. A keyframes block matches
                            nothing by construction and would read as dead.
  :root and *               match everywhere; they carry the custom properties
                            every other rule reads.
  @media print,
  prefers-reduced-motion,
  orientation               conditions this harness does not enter. A rule that
                            is live only under a media query nobody exercised
                            is not evidence of anything.

Those are held as KEEP regardless of whether they matched, which is the superset
gate: the classifier is allowed to be wrong in the direction of shipping a rule
the player does not need, and is not allowed to be wrong in the other direction.

STATE. Selectors are tested as written AND with state stripped
(:hover/:focus/:active and pseudo-elements removed), because .menu-overlay.open
never matches at rest and .menu-overlay is what actually decides the question.
A block counts as live if EITHER form matches in ANY scene.
"""
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "skribl" / "static" / "styles.css"

# --- parse into top-level blocks ---------------------------------------------


def blocks(text):
    """Yield (start, end, header, body) for each top-level construct."""
    i, n = 0, len(text)
    out = []
    while i < n:
        # skip whitespace and comments, but keep them attached to what follows
        start = i
        while i < n:
            if text[i : i + 2] == "/*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
            elif text[i].isspace():
                i += 1
            else:
                break
        if i >= n:
            if start < n:
                out.append((start, n, "", ""))
            break
        head_start = i
        # at-rules without a body end at ';'
        depth = 0
        brace = -1
        while i < n:
            c = text[i]
            if text[i : i + 2] == "/*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            if c in "\"'":
                q = c
                i += 1
                while i < n and text[i] != q:
                    i += 2 if text[i] == "\\" else 1
                i += 1
                continue
            if c == ";" and depth == 0 and brace < 0:
                i += 1
                break
            if c == "{":
                if depth == 0:
                    brace = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        header = text[head_start : brace if brace > 0 else i].strip()
        body = text[brace + 1 : i - 1] if brace > 0 else ""
        out.append((start, i, header, body))
    return out


ALWAYS_KEEP = re.compile(
    r"^@(keyframes|-webkit-keyframes|font-face|import|charset|supports|property|layer)",
    re.I)
UNEXERCISED_MEDIA = re.compile(
    r"print|prefers-reduced-motion|prefers-contrast|forced-colors|orientation|"
    r"hover\s*:\s*none|pointer\s*:\s*coarse", re.I)
STATE = re.compile(r"::?(hover|focus|focus-visible|focus-within|active|"
                   r"before|after|placeholder|selection|backdrop|"
                   r"-webkit-[a-z-]+)(\([^)]*\))?", re.I)


def selectors_of(header, body, depth=0):
    """Every selector a block contributes, recursing into @media."""
    h = header.strip()
    if ALWAYS_KEEP.match(h):
        return None                       # unclassifiable by matching
    if h.startswith("@media"):
        if UNEXERCISED_MEDIA.search(h):
            return None                   # condition this run never enters
        out = []
        for _s, _e, hh, bb in blocks(body):
            sub = selectors_of(hh, bb, depth + 1)
            if sub is None:
                return None
            out.extend(sub)
        return out
    if h.startswith("@"):
        return None
    return [p.strip() for p in re.split(r",(?![^(]*\))", h) if p.strip()]


text = CSS.read_text()
parsed = []
for s, e, h, b in blocks(text):
    sels = selectors_of(h, b)
    parsed.append({"start": s, "end": e, "header": h[:70], "sels": sels,
                   "bytes": e - s})

classifiable = [p for p in parsed if p["sels"]]
kept_blind = [p for p in parsed if p["sels"] is None]
all_sels = sorted({s for p in classifiable for s in p["sels"]})

print(f"styles.css       {len(text):,} B")
print(f"blocks           {len(parsed)}")
print(f"  classifiable   {len(classifiable)}  ({sum(p['bytes'] for p in classifiable):,} B)")
print(f"  held KEEP      {len(kept_blind)}  ({sum(p['bytes'] for p in kept_blind):,} B)"
      f"  — at-rules with no selectors, and media queries this run never enters")
print(f"distinct selectors {len(all_sels)}")

Path("/tmp/css_selectors.json").write_text(json.dumps({
    "selectors": all_sels,
    "blocks": [{"start": p["start"], "end": p["end"], "header": p["header"],
                "sels": p["sels"], "bytes": p["bytes"]} for p in parsed],
}))
print("\nwrote /tmp/css_selectors.json")


# --- emit ---------------------------------------------------------------------
# `python3 harness/tools/cssgraph.py --emit <live.json>` writes player.css from
# styles.css and the recorded live-selector set. Kept as a separate step so the
# classification (which needs a browser) and the generation (which does not) can
# be re-run independently — and so verify_cssplit.py can regenerate and compare
# without deciding anything itself.
def _split_media(block_text, live):
    """Emit only the live rules inside one @media block, or None to keep it whole.

    The block-level rule — keep the construct if ANY selector in it is live —
    was applied to a whole @media, so one live rule dragged in every editor rule
    that happened to share the breakpoint. styles.css puts most of its
    responsive rules in a handful of large media blocks, so that is thousands of
    bytes of drawer and composer styling on a page with neither.

    The condition is not re-evaluated here: liveness is a property of a
    selector, measured by asking a real page whether anything matches it, and
    that answer does not change with the viewport the rule is gated on. This is
    the same classification, applied one level deeper.

    Returns None when the block should be emitted verbatim — when every inner
    rule is live (so a rebuild could only differ in whitespace), when none is
    (the caller drops it), or when anything inside cannot be classified by
    matching at all, which is the superset gate one level down.
    """
    brace = block_text.find("{")
    close = block_text.rfind("}")
    if brace < 0 or close < brace:
        return None
    inner = block_text[brace + 1:close]
    kept, total = [], 0
    for s, e, hh, bb in blocks(inner):
        sub = selectors_of(hh, bb)
        if sub is None:
            return None                     # nested at-rule: do not touch it
        total += 1
        if any(x in live for x in sub):
            kept.append(inner[s:e])
    if not kept or len(kept) == total:
        return None
    return block_text[:brace + 1] + "".join(kept) + block_text[close:]


def emit(live_path, out_path):
    live = set(json.loads(Path(live_path).read_text())["player"])
    parts = []
    for p in parsed:
        block_text = text[p["start"]:p["end"]]
        if p["sels"] is None:
            parts.append(block_text)
            continue
        if not any(s in live for s in p["sels"]):
            continue
        if p["header"].startswith("@media"):
            split = _split_media(block_text, live)
            if split is not None:
                parts.append(split)
                continue
        parts.append(block_text)
    Path(out_path).write_text(HEADER + "".join(parts))
    return sum(len(p) for p in parts) + len(HEADER)


HEADER = Path(__file__).with_name("player_css_header.txt").read_text()

if len(sys.argv) > 2 and sys.argv[1] == "--emit":
    n = emit(sys.argv[2], sys.argv[3] if len(sys.argv) > 3
             else ROOT / "skribl" / "static" / "player.css")
    print(f"emitted {n:,} chars")
