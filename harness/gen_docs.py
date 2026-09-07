#!/usr/bin/env python3
"""Generate the documentation tables that restate facts the source already holds.

WHY THIS EXISTS. The v281 staleness sweep produced twelve findings and every
one was a description that had drifted from a thing — never a logic bug. Three
of them were this file's targets: the shared-module index had three wrong rows
and three missing, and README's route table did not mention DELETE, which was
the whole revocation capability two releases had been spent building. Each was
caught by a bespoke gate written after the fact.

A gate DETECTS drift and costs a permanent assertion. A derivation PREVENTS it.
So the order of preference recorded in DECISIONS.md is derive, then delete,
then gate — and every table generated here lets its gate be deleted outright.

WHY NOT stamp_docs.py. That stamps facts derived from a RUN, and carries a lot
of precedence logic because two run records can legitimately disagree about the
same tree. These tables derive from SOURCE, need no run, and have no such
ambiguity. Different input, different cadence, different file.

THE DESCRIPTIONS COME FROM THE CODE ITSELF, not from a list kept beside it.
A lib module's own header sentence and a route handler's own docstring are
what appear in the table, so the prose cannot drift from the thing it
describes — moving a module or renaming a route rewrites its row.

    python3 harness/gen_docs.py            # rewrite the generated regions
    python3 harness/gen_docs.py --check    # exit 1 if any is stale
"""
import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "skribl" / "templates" / "skribl"
ST = ROOT / "skribl" / "static"

# Marker names are distinct per region so one generator can own several tables
# in one document without the first BEGIN swallowing the wrong END. That is not
# hypothetical: v281 nearly shipped a START-HERE.md with two HARNESS-COUNTS
# opening markers because a note QUOTED the marker, and the next stamp would
# have deleted everything between the sentence and the real stanza.
def markers(name):
    return f"<!-- GEN:{name} -->", f"<!-- /GEN:{name} -->"


def _sentence(text, cap=320):
    """The first complete sentence of a comment block, unwrapped.

    A SENTENCE, NOT A LINE. Three rows of the hand-written module index ended
    mid-clause ("...the ONE implementation of a machine both") because someone
    pasted the first LINE of a wrapped source header. Taking text up to the
    first terminator and collapsing whitespace cannot make that mistake.
    """
    body = re.sub(r"^\s*\*+", " ", text, flags=re.M)
    body = re.sub(r"\s+", " ", body).strip()
    m = re.match(r"(.{10,%d}?[.!])(\s|$)" % cap, body)
    return m.group(1).strip() if m else None


def _lead_comment(src):
    m = re.match(r"\s*/\*(.*?)\*/", src, re.S)
    return m.group(1) if m else ""


def _scripts(path):
    """Script assets a template loads. Jinja comments are stripped first: a note
    saying a module is NOT loaded names it too, and that false positive turned
    up the first time this was done by hand."""
    body = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.S)
    return re.findall(r"skribl_asset\('([^']+)'\)", body)


# The column vocabulary, and the template each token means. skribl_feed.html is
# the demo HOST page rather than a Skribl surface, which is why lib/composehost.js
# is the one module only a host loads.
SURFACES = [("Pad", "skribl_editor.html"), ("Flip", "skribl_flip.html"),
            ("player", "skribl_player.html"), ("library", "skribl_library.html"),
            ("in-post", "_skribl_inline_player.html"), ("HOST", "skribl_feed.html")]


def module_index():
    loaded = {}
    for token, tpl in SURFACES:
        for asset in _scripts(TPL / tpl):
            if asset.startswith("lib/"):
                loaded.setdefault(asset[4:], []).append(token)
    rows = ["| module | loaded on | what it owns |", "|---|---|---|"]
    for path in sorted((ST / "lib").glob("*.js")):
        where = "+".join(loaded.get(path.name, [])) or "—"
        what = _sentence(_lead_comment(path.read_text(encoding="utf-8"))) \
            or "_(no header sentence — give the module one)_"
        rows.append(f"| `{path.name}` | {where} | {what} |")
    return "\n".join(rows)


def route_table():
    src = (ROOT / "skribl" / "routes.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    seen = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            text = ast.unparse(dec)
            m = re.search(r"\.(route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)", text)
            if not m:
                continue
            verbs = re.search(r"methods=\[([^\]]*)\]", text)
            methods = ([v.strip().strip("\"'").upper() for v in verbs.group(1).split(",") if v.strip()]
                       if verbs else [m.group(1).upper().replace("ROUTE", "GET")])
            doc = ast.get_docstring(node)
            what = _sentence(doc, cap=200) if doc else None
            for verb in methods:
                seen.append((m.group(2), verb, what))
    rows = ["| route | purpose |", "|---|---|"]
    for path, verb, what in sorted(seen, key=lambda r: (r[0], r[1])):
        shown = path.replace("public_id", "id")
        label = f"`{verb} {shown}`" if verb != "GET" or path.startswith("/api") or path.startswith("/media") else f"`{shown}`"
        rows.append(f"| {label} | {what or '_(undocumented — give the handler a docstring)_'} |")
    return "\n".join(rows)


REGIONS = [
    ("MODULE-INDEX", ROOT / "START-HERE.md", module_index),
    ("ROUTES", ROOT / "README.md", route_table),
]


def apply(name, path, build, check):
    begin, end = markers(name)
    text = path.read_text(encoding="utf-8")
    if text.count(begin) != 1 or text.count(end) != 1:
        return "unmarked"
    body = f"{begin}\n{build()}\n{end}"
    new = re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: body, text, flags=re.S)
    if new == text:
        return "current"
    if check:
        return "stale"
    path.write_text(new, encoding="utf-8")
    return "updated"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale, unmarked, updated = [], [], []
    for name, path, build in REGIONS:
        result = apply(name, path, build, args.check)
        label = f"{path.relative_to(ROOT)}:{name}"
        {"stale": stale, "unmarked": unmarked, "updated": updated}.get(result, []).append(label)
    if unmarked:
        print(f"no GEN region (skipped): {', '.join(unmarked)}")
    if args.check:
        if stale:
            print(f"STALE: {', '.join(stale)}")
            print("Run: python3 harness/gen_docs.py")
            return 1
        print(f"generated tables are current: {len(REGIONS)} region(s)")
        return 0
    print(f"generated {len(REGIONS)} region(s)"
          + (f", updated {', '.join(updated)}" if updated else " (already current)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
