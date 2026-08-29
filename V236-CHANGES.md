# v236 — smudging a fill, and why it combs

Smudge on a **line** looks right. Smudge on a **fill** produces a comb: dark
stripes through the smeared tail. This explains why, improves it by about 65%,
and is honest that it is a mitigation rather than a cure.

## A fill is not a region

It is a stack of thin horizontal strokes — that is the whole design, forced by a
format that has no fill primitive. Drag that stack through a brush whose weight
falls off with distance and **neighbouring runs move by different amounts**, so
they fan apart and the ground shows between them.

Measured on a filled ellipse:

| | value |
|---|---|
| run width | 4px |
| run spacing | 0.9px |
| overlap (slack) | 3.1px |
| smudge falloff variation across one spacing | 4.7% |
| separation growth | ~4.3% of drag distance |
| **drag before a gap opens** | **~72px** |

A line has none of this because it is *one* stroke, dragged coherently. That is
exactly the difference in the two screenshots.

## What changed

Runs are now drawn 3px taller than their group instead of 1px, which is pure
overlap. Slack goes 3.1px → 5.1px and the gap threshold **72px → 119px**.

The cost is horizontal: a round cap overshoots by half the run's width, so the
fill tucks a further 1px under the line bounding it. Coverage still measures 0
bare pixels of 7845, and the fill still does not escape its region.

## What it is not

**Nothing available here survives a 200px pull.** To hold that, the runs would
need ~8px of overlap, and the fill would then spill visibly past its boundary.
Combing on a heavily smudged fill is inherent to fills being strokes.

The cure is a format that can hold a *region* — which is the same conversation
as editable shapes, non-exporting guides, and blurring a photograph. All four
want the same thing, and it is the owner's call.

## The assertion

The overlap does not look load-bearing; it looks like a rounding guard. A future
"the runs already tile, why is this wider than the group" simplification would
halve the threshold with nothing visible to show for it. So it is pinned, with
the measurement in the failure message.
