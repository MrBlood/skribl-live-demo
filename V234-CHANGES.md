# v234 — the fill's fringe, and smudge earning its name

## Fill: it stopped at the anti-aliased fringe

A drawn line is anti-aliased, so the flood stops a pixel or two **outside** its
solid core and the two never meet. Because the fill is appended to the strokes
array it paints *on top of* that line — so wherever it fails to reach, the
leftover fringe shows through as a dark thread just inside the edge. Ragged,
because the flood's stopping point jitters row to row, which is why it read as
**dotted** rather than as a clean outline.

The region now grows by 2px before grouping (a box dilation over the row
extents), tucking the fill under the line. Every paint bucket does some version
of this; the alternative — raising the colour tolerance until the fringe is
eaten — is far less predictable and leaks through thin boundaries. The honest
limit: on a 1px hairline the fill would swallow the line.

**Already-drawn fills do not repair themselves.** A fill bakes into strokes at
the moment it is made, so one drawn by an earlier build keeps that build's
artefacts. Undo and re-fill to get the new geometry.

## The test that kept passing

Two assertions were added for this and **both were vacuous until mutation caught
them**:

- The first drew a *box*. Axis-aligned edges barely anti-alias, so there was no
  fringe to miss and the check passed with `GROW = 0`.
- The interior probe shrank the shape by 18% before counting holes — excluding
  exactly the band where the artefact lives.

The check now draws an **ellipse**, and counts non-white pixels between the first
and last ink on each row: holes enclosed by ink, edge band included. Measured at
device pixel ratios 1 and 3, on a freshly drawn ellipse: **0**.

## Smudge: it was Liquify with two constants changed

> "3rd is smudge. Looks like liquefy."

It did, because it was. Displacement alone *is* Liquify; a sharper falloff at
higher strength gives you a sharper Liquify, not a different tool.

Real smudged paint **thins as it travels** — there is only so much pigment, and
dragging spreads it over more area. So the ink a smudge carries now also fades
toward the ground and widens, in proportion to how far it has been dragged. The
result is a softening tail instead of a hard spike, which is the difference a
user actually sees. Accrued per pixel travelled, for the reason `BLUR_RATE`
gives.

**The smear needed per-point scratch state, and points are payload.** A field
parked on the point would ride into every saved draft, every shared Skribl and
past the server's validator. It lives in a `WeakMap` keyed by the point instead —
which also survives `liquifySubdivide` inserting points mid-drag, something an
index cannot. Asserted: no key on a point may begin with `_`.

## Testing

`verify_fill` 19 → 20, `verify_smudgeblur` 17 → 19.
