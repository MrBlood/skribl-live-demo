"""Source text with the prose taken out, for the checks that read code as text.

WHY THIS EXISTS. CLAUDE.md states the rule in capitals -- A CHECK FOR ABSENCE
MUST MATCH THE MECHANISM, NOT THE WORD -- and records three occasions when a
check read the comment explaining a thing as the thing itself: verify_review's
"the player does not load this module" matched the filename inside the comment
saying why it doesn't; two /library gates passed on their own prose; and v283's
run_harness.sh comment illustrated the flag syntax verify_docs scrapes, so the
scraper found a file called `...`.

It happened a fourth time, and that one is why this module is shared rather than
copied. verify_ux pins the iOS late-decode hook with

    "_skriblLateAudio = " in _appjs                       # is it defined?
    _appjs.count("_skriblLateAudio") >= 2                 # and used?

over the raw file. An audit commented the assignment out and left the original
line verbatim in a `//` comment above it. The hook is then never defined and the
resync at app.js:3890 is dead -- and BOTH checks passed, the second reporting
"3 references", because the comment ADDED one. 371 assertions green with the
feature removed.

verify_seam had the fix all along (strip the comments first) and nothing else
imported it, so the tree held one working copy and nine sites that needed it.
This is that copy, in a place the others can reach.

WHAT IT DOES NOT DO. This is a comment stripper, not a parser. It does not know
about regex literals, so `/foo\\/\\/bar/` loses its tail, and it does not know
about template literals, so a `//` inside one is removed. Both are acceptable
HERE and nowhere else: these callers ask "does this token appear in the code",
and a false ABSENCE makes a check fail loudly rather than pass quietly. Anything
that needs to be right about JS syntax should use skribl/jsstrip.py, which is a
real tokeniser and is what the server ships.
"""
import re


def strip_js(src):
    """JS with // line and /* */ block comments removed."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return "\n".join(re.sub(r"//.*$", "", line) for line in src.split("\n"))


def strip_py(src):
    """Python with # comments removed, without cutting a # inside a string.

    Character-by-character rather than a regex, and this implementation is
    verify_seam's -- moved here rather than rewritten, because its own note
    records that it caught the changelog comment in the file it was guarding on
    its first run. A `#` inside a quoted literal is kept; everything from an
    unquoted one to end of line goes.
    """
    out = []
    for line in src.split("\n"):
        q = None
        buf = []
        for i, ch in enumerate(line):
            if q:
                buf.append(ch)
                if ch == q and line[i-1:i] != "\\":
                    q = None
            elif ch in "\"'":
                q = ch
                buf.append(ch)
            elif ch == "#":
                break
            else:
                buf.append(ch)
        out.append("".join(buf))
    return "\n".join(out)


def read_js(path):
    """A .js file as code only."""
    return strip_js(path.read_text(encoding="utf-8"))


def read_py(path):
    """A .py file as code only."""
    return strip_py(path.read_text(encoding="utf-8"))
