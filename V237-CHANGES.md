# v237 — polygons and rounded corners

The genuinely good half of the shapes proposal, on **both** surfaces, with no
format risk: shapes already rasterise to points, so a polygon is one more
generator in `lib/shapes.js` and rounding is a treatment applied to any
straight-edged kind.

## What shipped

- **Poly**, a fourth shape kind. A regular 3–12-gon inscribed in the drag's box.
- **Sides**, a slider, 3 to 12. Past twelve it is an ellipse with extra points,
  and the ellipse generator spaces itself by arc length in a way a polygon
  cannot.
- **Corners**, a rounding slider for rect and poly.

Both knobs live in the shape popover and **hide** rather than greying out when
they mean nothing for the current kind — a control you cannot use is still one
the eye has to read past, and that popover is small on a phone.

## Two details worth the words

**A triangle points up.** An unrotated polygon starts at 0 radians and gives a
triangle lying on its side, which is not what anybody means when they draw one.
The first vertex is at the top.

**The radius clamps itself to half the shortest edge.** A slider that lets
someone ask for more rounding than an edge can give produces a shape folded
through itself, and the value that does it differs with every shape and every
drag size — so it cannot be a `max` on the input. Clamped in the geometry, the
slider simply stops having an effect, which is what running a control to its end
should do. Asserted with radius 9999 on a 100px box.

## Shared, not duplicated

`_rect` and the polygon now share one corner treatment: a closed vertex list,
each corner cut back along both edges and filled with a quadratic through the
vertex. The old `_rect` became dead code and was removed rather than left.

Wired on **Pad and Flip both**. A shared lib with a feature only one surface can
reach is exactly the divergence `verify_surfaces` exists to catch.

## A stale precondition this exposed

`verify_tools` checked "Shift gives a circle" on Flip **immediately after a loop
over the shape kinds**, relying on `ellipse` happening to be last in that list.
Adding `poly` moved the goalposts, and the check started drawing a shifted
polygon — a real shape with a real bounding box, failing in a way that reads
like a geometry bug rather than a stale setup. It selects the kind explicitly
now. Pad's equivalent already did.

## Also confirmed, not built

The **eyedropper already exists** and is wired on both surfaces via
`lib/eyedropper.js` — it lives in the colour drawer rather than the tool shelf,
which is the right place for it. Nothing to add.

## Testing

`verify_tray` 85 → 93, `verify_tools` 119 → 120. Both shape-kind ratchets raised.
