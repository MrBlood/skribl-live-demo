#!/usr/bin/env python3
"""One check() for the whole harness.

Ninety-nine suites each defined their own, in NINE distinct variants — which
is worse than ninety-nine copies of one thing, because the differences were
invisible. They varied on three axes and nothing recorded why:

  detail_on_pass  Most suites print `detail` either way. Ten do not, and
                  verify_flipmeta.py is the only one that wrote down the
                  reason: its details are DIAGNOSES rather than values, so a
                  passing line reading "— the literal is back" scans as a
                  failure to anyone reading the log.

  with_detail     Most append (ok, name) to `results`; nine append
                  (ok, name, detail). verify_review.py recorded that reason
                  too: its summary re-printed only the NAME of each failure,
                  so reading a 278-assertion run through `tail` showed
                  "FAILED: attempt and post budgets are separate" with the
                  measured values thousands of lines above. A failure has to
                  carry what it measured to the place it gets read.

  sep             verify_migrations.py alone used "→" where everything else
                  used "—". No reason was recorded and none is apparent; it
                  is preserved so this refactor changes no output.

`ok` is always coerced with bool() — the variants that did not were relying on
truthiness their summaries applied anyway, so this is the same behaviour
stated once.

THE OUTPUT FORMAT IS A CONTRACT. run_harness.sh parses "  [PASS] ..." lines and
the "N/M passed" summary, so a formatting change here is a harness-wide
breakage that would look like suites failing. Run this file directly to check
every variant still renders byte-identically:

    python3 harness/assertions.py
"""


def make_check(results, *, detail_on_pass=True, with_detail=False, sep="—"):
    """Return a check(name, ok, detail="") that appends to `results`.

    `results` is the suite's own list, so the summary each suite prints at the
    bottom is untouched by this — only the function that fills it is shared.
    """
    def check(name, ok, detail=""):
        ok = bool(ok)
        results.append((ok, name, detail) if with_detail else (ok, name))
        show = detail if (detail_on_pass or not ok) else ""
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
              + (f"  {sep} {show}" if show else ""))
        return ok
    return check


def _selftest():
    """Compare against the literal strings the nine variants produced."""
    import io
    import contextlib
    cases = [
        # (kwargs, name, ok, detail) -> expected line, expected tuple
        ({}, "a", True, "d",  "  [PASS] a  — d",  (True, "a")),
        ({}, "a", False, "d", "  [FAIL] a  — d",  (False, "a")),
        ({}, "a", True, "",   "  [PASS] a",       (True, "a")),
        ({"detail_on_pass": False}, "b", True, "d",  "  [PASS] b",      (True, "b")),
        ({"detail_on_pass": False}, "b", False, "d", "  [FAIL] b  — d", (False, "b")),
        ({"with_detail": True}, "c", True, "d",  "  [PASS] c  — d", (True, "c", "d")),
        ({"sep": "→"}, "e", True, "d", "  [PASS] e  → d", (True, "e")),
        # truthiness: a non-empty list is a PASS and is stored as a real bool
        ({}, "f", [1], "",  "  [PASS] f", (True, "f")),
        ({}, "g", [], "",   "  [FAIL] g", (False, "g")),
    ]
    bad = []
    for kwargs, name, ok, detail, want_line, want_tuple in cases:
        res = []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            make_check(res, **kwargs)(name, ok, detail)
        line = buf.getvalue().rstrip("\n")
        if line != want_line:
            bad.append(f"{kwargs} {name}: printed {line!r}, wanted {want_line!r}")
        if res[0] != want_tuple:
            bad.append(f"{kwargs} {name}: stored {res[0]!r}, wanted {want_tuple!r}")
    for b in bad:
        print("  FAIL", b)
    print(f"  {len(cases) - len(bad)}/{len(cases)} variant renderings match")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
