# harness/tools

Measurement utilities. **Not suites** — nothing here is named `verify_*.py`, so
`run_harness.sh` does not pick them up and they contribute no assertions. They
need dependencies the suites deliberately do not (`node`, `npm i acorn
acorn-walk`), which is exactly why they are not in the aggregate: a suite that
cannot run everywhere becomes a skip, and a skip is not coverage.

## refgraph.js

An AST reference graph over `skribl/static/app.js`, built with acorn. Covers
`FunctionDeclaration` at any depth, attributes every identifier in a load
position to its innermost enclosing declaration, propagates references outward,
and computes player reachability from the `READ-ONLY PLAYER` section marker.

    npm i acorn acorn-walk
    node harness/tools/refgraph.js skribl/static/app.js

Reports, in bytes: player-reachable, editor-only, and the editor-only subset
pinned by top-level statements (which cannot move while the wiring names them).

**This is a measurement, NOT a safe-to-move list.** It carries the same caveat
as the regex graph in `verify_seam.py`, and it earned it: this tool classifies
all four functions that the reverted v132 split moved wrongly as editor-only,
and it fails the superset gate that `docs/REFACTOR-v132.md` originally proposed
as its own acceptance test. Read that section before acting on any output here.
