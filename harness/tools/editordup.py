"""How much of Pad and Flip is still the same code written twice?

FUTURE.md used to answer this from memory: it named five controllers as
duplicated long after all five had moved into lib/. An outside audit of v312
quoted that paragraph as a High finding and withdrew it on reading the source.
The duplication it pointed at had gone; a larger body of it had not, and no
document said where. This measures instead of remembering.

METHOD. Every named function in Pad (app.js and the editor_*.js carves) is
paired with the function of the same name in flip.js, comments stripped, and
the two bodies compared as TOKEN sequences. Tokens, not lines: flip.js packs a
function onto one or two lines where app.js spreads it over twenty, so a
line-level clone detector finds almost nothing -- the first version of this
measurement did exactly that and reported 27 duplicated lines.

CALIBRATED against two known cases before being believed: `initPaintTarget`
is the same block reformatted and scores 1.00; `frame` is two unrelated
functions that share a name and scores 0.04.

WHAT IT DOES NOT SEE, so read every total as a LOWER BOUND:
  * anonymous handlers and top-level statements -- only named functions pair;
  * a copy that was renamed on one side;
  * lib/ and vendor code, deliberately: those are the shared answer.
And what it OVER-counts: a small pair can be legitimate glue around a shared
module (each editor's adapter to lib/recentcolors.js, say). --min-tokens,
which defaults to 100, keeps those out of the totals.

    python3 harness/tools/editordup.py [--min-tokens N] [--min-sim F]
"""
import argparse
import difflib
import pathlib
import re

STATIC = pathlib.Path(__file__).resolve().parents[2] / "skribl" / "static"
TOKEN = re.compile(r"[A-Za-z_$][\w$]*|\d+\.?\d*|'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`"
                   r"|==?=?|!==?|=>|&&|\|\||[^\s\w]")
DEF = re.compile(
    r"(?:function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
    r"(?:function\s*\([^)]*\)|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)\s*\{)")


def strip_comments(text):
    # Newlines inside a block comment are kept so file:line stays true.
    text = re.sub(r"/\*.*?\*/", lambda m: " " + "\n" * m.group(0).count("\n"),
                  text, flags=re.S)
    return re.sub(r"(^|[^:'\"\\])//[^\n]*", r"\1", text)


def functions(path):
    """{name: (tokens, 'file:line')}, keeping the longest body per name."""
    text = strip_comments(path.read_text(encoding="utf-8"))
    out = {}
    for m in DEF.finditer(text):
        name = m.group(1) or m.group(2)
        i, depth = m.end(), 1
        while i < len(text) and depth:
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        toks = TOKEN.findall(text[m.start():i])
        where = f"{path.name}:{text.count(chr(10), 0, m.start()) + 1}"
        if name not in out or len(toks) > len(out[name][0]):
            out[name] = (toks, where)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-tokens", type=int, default=100,
                    help="smaller side must be at least this long (default 100)")
    ap.add_argument("--min-sim", type=float, default=0.5,
                    help="token similarity to count as a copy (default 0.5)")
    args = ap.parse_args()

    pad = {}
    for f in [STATIC / "app.js"] + sorted(STATIC.glob("editor_*.js")):
        for name, v in functions(f).items():
            if name not in pad or len(v[0]) > len(pad[name][0]):
                pad[name] = v
    flip = functions(STATIC / "flip.js")

    rows = []
    for name in set(pad) & set(flip):
        a, b = pad[name][0], flip[name][0]
        small = min(len(a), len(b))
        if small < args.min_tokens:
            continue
        sim = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
        if sim >= args.min_sim:
            rows.append((small, name, len(a), len(b), sim, pad[name][1],
                         flip[name][1]))
    rows.sort(key=lambda r: (-r[0], r[1]))

    print(f"{'function':26} {'pad':>6} {'flip':>6} {'sim':>5}  pad | flip")
    for small, name, a, b, sim, pw, fw in rows:
        print(f"{name:26} {a:6} {b:6} {sim:5.2f}  {pw} | {fw}")
    pad_total = sum(len(TOKEN.findall(strip_comments(f.read_text(encoding="utf-8"))))
                    for f in [STATIC / "app.js"] + sorted(STATIC.glob("editor_*.js")))
    dup = sum(r[0] for r in rows)
    print(f"\n{len(rows)} pairs, {dup} tokens on the smaller side "
          f"({100 * dup / pad_total:.0f}% of Pad's {pad_total}); a lower bound")


if __name__ == "__main__":
    main()
