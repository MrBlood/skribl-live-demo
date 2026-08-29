# v232 — Smudge and Blur

Two tools, one sweep, and one architectural finding that nearly stopped half of
it.

## Blur almost wasn't possible

A frame is `{strokes, strokeGroups}` — a flat array of
`{x, y, color, size, t, erase, start}`. Liquify works because *displacement* is
expressible in a format made of points. **You cannot blur a polyline by moving
its points.** There is no raster layer to convolve, and adding one is a format
change the player must honour.

The way through is a detail of `paintStatic()`: a stroke whose **first point is
opaque** is painted by `paintSeg` with each point's *own* colour and *own* size.
So per-point colour is honoured, and blur becomes sayable in this format — fade
each touched point toward the ground it sits on, and widen it. It reads as
defocus on line art, it composes when you go over it twice, and the player
renders it identically because the player runs the same paint path.

**What it is not:** a convolution. It cannot soften a photograph underneath, and
it fades toward the page's background colour rather than toward whatever pixels
are actually behind the line. That is the honest boundary of doing this without
a format change, and it is written into the lib rather than left to be
discovered.

**Alpha was the obvious route and is the wrong one twice over.** `paintStatic`
takes a stroke's alpha from its *first* point, so a per-point change would not
apply; and translucent strokes composite one at a time against `LAYER_BUDGET`
(24), so a blur that made a dozen would flip the whole frame to direct painting
and change how every other stroke looks. Mixing toward the background gets the
same appearance with none of that.

## Smudge is not Liquify with a new name

It would have been easy to ship it as one. Liquify displaces at half strength
with a smooth shoulder — it warps a region, like pushing a sheet of rubber.
Smudge is a fingertip: a sharper falloff (2.2 vs 1) at near-full strength (0.92
vs 0.5), so ink right under the touch comes with you and ink a few pixels away
barely moves. Same traversal, genuinely different gesture — and the suite
asserts the falloffs differ, because equal, they are one tool shipped twice.

## The bug the tests caught, twice

Blur's first version faded a little on **every pointermove**. That makes the
tool's strength a property of the **hardware** — a 240Hz phone blurs several
times harder than a 60Hz laptop for the same gesture, and v230's coalesced
sampling raised that rate on purpose. Measured: one short swipe took `#ffffff`
to `rgb(87,89,92)`, most of the way to the background.

Saturating the accumulation was the obvious repair and **it was not enough** —
it bounds the maximum while a 4-event sweep still lands somewhere different from
a 40-event one. What fixes it is accruing **per pixel travelled**: distance is
the quantity a brush physically deposits against, and it is the same number
however often the OS sampled the finger.

| accrual | 4-event sweep | 40-event sweep | gap |
|---|---|---|---|
| per event | `rgb(239,240,240)` | `rgb(122,123,126)` | **117/255** |
| per pixel travelled | `rgb(182,182,184)` | `rgb(188,189,190)` | **6/255** |

The residual is arithmetic, not a bug: weight varies across the brush, so
integrating it from 4 samples cannot equal integrating it from 40.

## Shared, not copied

`lib/brushfield.js` holds the falloff, the colour mixing and the point
traversal — the same question Liquify, Smudge and Blur each ask. The colour
mixer preserves an alpha the stroke already carried and **returns unparseable
colours untouched**, because a parser that guesses turns one bad string into a
silhouette.

Both tools reuse Liquify's undo shape: a whole-frame before/after snapshot,
because smudge subdivides and an index-keyed diff cannot describe an insertion.
One drag is one undo.

## Testing

New suite `verify_smudgeblur.py`, 17 assertions, mutation-tested. Both roster
ratchets updated (`verify_tray`, `verify_select`).
