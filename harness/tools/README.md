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

## corpus/

Twenty-seven pairs of pages — translation, rotation, scale, a blink, a limb, a
tap, an erased hole, three identical circles, a page held x4 — rendered through
both **Add in-between** and **Motion Smear**, at two sampling densities each.

    python3 -m flask --app app run --port 5001 --no-reload   # one shell
    python3 harness/tools/corpus/render.py out/              # another

One PNG per case, plus `results.json` with the geometry behind every verdict.
Exits non-zero if any case FAILs.

**It is an oracle, not a photo album, and that distinction is v300's.** From
v295 it rendered the same shapes every release and a human compared this
release's pictures to last release's. That answers "did it change?" and never
"is it right?" — an outside review of v299 said so, and it was correct. Each
case now states what it expects and the sheet carries the verdict.

The expectations are **computed from the poses** rather than written into the
case, because both rows draw the same geometry at different densities: a number
typed into a case could only be true of one of them, and the second row exists
precisely to tell a correct hand-sampled render from a broken one.

Calibrated by mutation — each of these is a defect that actually shipped here,
and what it reddens is the whole argument for the case existing:

| the tree, broken back to                        | cases that go red  |
| ----------------------------------------------- | ------------------ |
| `ibFit` testing one extent, not both (pre-v299)  | `23b` alone        |
| `carveForInsert` taking one slot (pre-v299)      | `24` alone         |
| the in-between not carrying erasers (pre-v300)   | `18` alone         |
| `tweenResample` walking by index, not arc length | `22`, `25`         |
| `ibApply` dropping its centroid lerp             | fourteen of them   |

Three of those defects are seen by exactly one case each. A corpus of this size
is worth its weight only while that stays true — a case nothing can redden is a
picture, and this file is where it gets removed rather than kept for tidiness.

**What the corpus reports rather than gates:** `08` and `09` are a matched
pair, and they disagree on purpose. An in-between is built by walking THIS
page's strokes, so an object that disappears lingers through the middle pose
and an object that appears is not there until the end. Both are defensible for
a single pose with no opacity to fade through; the pair is here so that
changing one moves the other.
