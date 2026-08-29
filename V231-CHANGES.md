# v231 — two bugs from the first hour of v230 being live

Both reported from the phone, minutes apart. Neither was findable any other way,
and one of them had been shipped and unnoticed for three versions.

## 1. Fill drew a dotted line down every slope

> "Fill left weird dotted line."

**What it was.** The first version collapsed every 6 pixel rows into one band and
gave the band the **union** of those rows' extents. On a straight edge that is
exact. On a diagonal the union is wider than the narrow rows in it; the
round-cap inset then pulls each run's ends back by half its width; and where the
region is narrow — the apex of a triangle, precisely where the dots appeared —
the run comes out *shorter than its own width* and collapses to a single dot.

A column of those down a slope is a perforated line. The dots were the fill's own
short-run fallback firing over and over.

**The fix is a better algorithm, not a tuned constant.** Rows now group only
while their extent is **unchanged**, and each group is drawn at its own height:

| region | before | after |
|---|---|---|
| 48×47 flat box | 8 runs | **1 run** (2 points) |
| 45° edge | 1 banded run per 6 rows, perforated | 1 exact run per row |

Cost follows the **perimeter** rather than the area — cheaper on ordinary shapes
*and* exact on diagonals. Groups tile exactly because a group of height `h` is
drawn at `lineWidth h` centred on its own middle, so there is no seam to leave a
gap in.

Dots still occur where a row is genuinely one or two pixels wide, which is honest
geometry. The suite asserts they stay confined to that.

## 2. Shape offered no choice — a regression from v227

> "Also shape is not give a choice, just gives you line."

Shape has a kind picker (line / rect / oval). It was opened by a click handler
bound to `#toolGroup .tool-btn` — **the shelf** — which was complete right up
until v227 put a **tray** in front of the shelf.

After that, choosing Shape from the tray never ran that handler. The picker never
opened, and Shape silently used whatever kind it already had: `line`, for
everyone who had never happened to have Shape sitting on the shelf. It shipped in
v227 and went unnoticed through v228, v229 and v230.

The picker now opens where **both** routes converge — the `setTool` callback that
`lib/toolshelf.js` calls for shelf and tray alike — and the shelf-only copy is
gone, because with both in place they toggled twice and cancelled out.

**The general shape of this is worth more than the instance:** adding a second
route to an action leaves any side effect wired to the first route silently
unreachable from the second. Nothing fails. The action still works. Only the
follow-on is gone, and only on the new path.

## Testing

`verify_fill` 14 → 18, `verify_tray` 80 → 85.

The fill assertions are on the **geometry**, not on pixels: a diagonal must
produce one run per row, a flat region must be one run however tall, and every
row must be covered exactly once. The tray assertions test the **tray** route
specifically — the shelf route never broke, so testing it proves nothing.

Both mutation-tested. Restoring the banding fails the diagonal and the flat-region
checks; rewiring the picker to the shelf alone fails the tray check.
