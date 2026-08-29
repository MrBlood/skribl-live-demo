# v230 — Fill

The first tool added under the new rhythm: build it, merge it, look at it on a
phone. No seal — `main` now runs the full harness in CI, so a merge is verified
without freezing an archive.

## The constraint, because it shaped the whole design

A frame is `{strokes, strokeGroups}` — a flat array of
`{x, y, color, size, t, erase, start}` — and the player replays those points and
nothing else. **There is no fill primitive**, and adding one is a format change
the player must honour, which is the owner's call rather than a thing a tool
should quietly introduce.

So Fill produces strokes, the way Shape already turns a drag into a path
(`lib/shapes.js`). The difference is that a shape is a 1-D curve and a fill is a
2-D region, and the naive reading — one point per filled pixel — puts a single
tap far past the server's 20,000-points-per-frame limit.

**What makes it cheap:** `paintSeg()` draws `drawLine(prev → point)` at
`lineWidth = size`, so a horizontal band of the region costs **two points**, its
endpoints. Measured on a 180×140 box: **52 points across 26 bands.** A full
640×460 fill lands near 200.

## Three details that are not details

**Round caps overshoot.** A run drawn to its true extent extends `size/2` past
both ends, so the fill bleeds half a brush past the line that bounds it. Every
run is inset by half its width; a run too short to survive the inset collapses
to a dot, which `drawDot()` paints at the same width.

**Rows must overlap** or hairline gaps show at every band boundary — very
visible on a dark ground. Each row is drawn 1.35× its step.

**Tolerance is anchored to the seed, not the neighbour.** Comparing each pixel
to the one it spread from lets a gradient walk the entire canvas: every step is
within tolerance of the last while the end is nothing like the start. Asserted
with a 256-wide gradient — seed-anchored, the fill stops at x=9 of 255.

## One tap is one undo

The fill lands as many stroke groups, which is right for the payload and wrong
for the editor — popping 26 groups to take back one tap is not undo. `actionLog`
already carries object entries for moves, so a `fill` entry records how many
groups the tap produced and `undoStroke` pops them together. **Nothing about the
saved format changes.**

That entry had to go *above* the existing catch-all object branch, which pops any
object entry and then assumes it is a move. Placed below it, a fill fell past
every `m.type` check and died on `m.idxs.length`. Order was the whole of the fix.

## Alpha is deliberately not supported

Rows overlap by design, so a translucent fill bands at every seam; and each run
is its own stroke, so a translucent fill of 100 runs blows `LAYER_BUDGET` (24)
and flips the **whole frame** to direct painting, changing how every other stroke
on it looks. `solidOf()` avoids both, and neither has a cheap fix. If translucent
fill is wanted, that is a format conversation.

## Testing

New suite `verify_fill.py`, 14 assertions: the two-point cost model on the pure
function, the cap inset, the dot collapse, the gradient walk, fills-inside **and**
does-not-leak-outside, one-tap-one-undo, one-redo, and that `strokeGroups`
accounts for every point — the invariant the server rejects a share over.

Both exact-roster ratchets updated (`verify_tray`, `verify_select`).

---

# v230 also — the points the handler was throwing away

Reported from the live demo: *"when I draw circles fast we get a lot of straight
line segments that make a curve. Drawing slowly smoothes it out."* Both halves of
that are exactly right, and the cause is arithmetic rather than feel.

**A `pointermove` listener receives at most one event per animation frame.** The
digitiser samples at 120–240Hz and the browser stashes what it batched inside
`event.getCoalescedEvents()` — which nothing in this project ever called. So
every stroke was recorded at ~60Hz no matter what the hardware offered. A circle
drawn in 0.4s becomes ~24 points and renders as a 24-sided polygon, because
`paintSeg()` joins consecutive points with `drawLine()` and nothing interpolates.
The same circle over 2s gets ~120 points and looks smooth. The drawing was never
the problem; the sampling was.

## The thinning is the design, not a compromise

Keeping every coalesced sample would multiply point counts several-fold against
the 20,000-per-frame server limit, and most of those points change no pixel — a
slowly moving finger at 240Hz emits samples a fraction of a pixel apart.

A minimum-distance filter is **self-balancing**, which is the property that makes
this work with one rule and no mode switch:

| | samples in | kept |
|---|---|---|
| slow finger (0.3px steps) | 40 | 9 |
| fast finger (20px steps) | 8 | 8 |

Draw slowly and nearly everything is dropped, so the point count lands about
where it does today. Draw fast and everything survives — which is precisely the
case that was starved. Points get spent where curvature is actually being lost
and nowhere else.

Events are passed through whole rather than reduced to coordinates: `sizeFor()`
reads pressure off the event, and taking positions from the batch while taking
pressure from the last event would flatten every taper onto one value.

## A bug the rewrite exposed

The handler read:

```js
if (smoothingAlpha >= 1 || erasing) { px = raw.x; py = raw.y; }
if (flipTool === 'shape') { ...; return; }
else { smoothPt = ...; px = smoothPt.x; py = smoothPt.y; }
```

The `else` binds to the **shape** test, not the smoothing one. So with the
stabilizer on, an eraser stroke had its precise point overwritten by the smoothed
one — directly contradicting the comment on the line above it. Invisible at the
default, where the stabilizer is off and the smoothed point equals the raw point,
which is why it survived this long.

## What the suite can and cannot see

Said plainly, because it changes what the assertions are worth: **Playwright's
synthetic pointer events are not coalesced**, so the harness cannot observe the
extra samples arriving. Asserting "a fast circle now has more points" would pass
on a build with the fix removed — the exact failure mode this project keeps
rediscovering. `verify_input.py` therefore tests what is observable and what
carries the risk: the thinning rule at its boundaries, the fallbacks for engines
without `getCoalescedEvents`, and the eraser's precision, which is mutation-tested.
