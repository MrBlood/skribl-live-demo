# v218 — the shape picker moved onto the Shape button

## Shape kind is no longer buried in the drawer

It lived in the draw drawer, three taps from the tool it configures and with
nothing to suggest it existed. Now:

* Tap **Shape** — selects the tool AND opens the picker.
* Tap **Line / Rect / Oval** — sets the kind and closes. Draw as many as you like.
* Tap **Shape** again — re-opens the picker to switch kind.
* Tap **Pen** or **Eraser** — closes it and switches tool.
* Tap outside, or press Escape — closes it.

**This is a RELOCATION, not a rewrite.** The popover contains the same
`#shapeSeg` markup with the same `data-shape` buttons, so the handler in
`editor_shapes.js` binds to it unchanged — including the part that already
called `setTool('shape')` when you pick a kind. The new code only opens and
dismisses the popover; it never touches the selection, so the two cannot
disagree about which shape is active.

On a phone the popover anchors to the left rather than centring, because the
Shape button sits near the left edge and a centred popover would hang off it.
Verified on screen at 375px and 900px.

# v217 — image and music are two buttons again

## The merge is reverted, and the reason is measurement

Merging Image, Music and Magnify into one Media control was proposed to fix the
row wrapping at 320 and 360px, when Pad carried 10 controls. **Removing Select
did that job instead.** Measured on the current row:

    merged (one 66px media button)   305px, 46px slack at 375px
    split (image + music separate)   308px, 43px slack at 375px

Three pixels. The merge was solving a problem that no longer existed, and it
cost two real bugs while it was in — Flip dead at load from an unguarded
reference to a button that had been removed, and the drawer rows opening nothing
because the only element matching `[data-drawer="photo"]` had become the row
itself. Two separate buttons would have had neither.

**Restored verbatim from sealed v214**, not redrawn: the same markup, the same
paths, the same `.tab-dot` sitting inside each button at top-right.

**The media drawer partial is deleted.** With image and music back on the bar,
its only remaining row was Zoom, and Zoom already has two homes: the magnify
button on desktop and pinch on a phone, which reveals the zoom HUD where Fit
lives.

## v217a — mobile spacing

The row looked cramped on a phone because a v213 override was still squeezing
it. Its own comment explains why it was written: *"157px wide once Shape joined
and overflowed a 375px phone by 52px."* It set the row gap to 1px, padding to
`6px 4px`, button padding to `9px 7px` and icons to 21px.

That was an emergency measure for a TEN control row. The row is now EIGHT —
Select is gone from Pad, magnify is desktop-only — so it was still crushing a
row with room to spare.

Measured, and the trade is specific:

    gap 1px -> 3px, sep 1px -> 3px, icons 21 -> 22px    343px, one row at 375px
    controls 34 -> 38px, or desktop button padding      WRAPS at 375px

The bar hits its own `max-width` and wraps rather than overflowing, so size
could not grow. The room went into spacing instead — which is where the problem
actually was, since the icons read as cramped because they were 1px apart.

## Still in from v216

* **Colour ring is a pre-rendered PNG.** A live `conic-gradient` there was the
  draw lag, confirmed by A/B on device: identical builds, gradient versus flat
  colour, laggy versus smooth. `.toolbar` carries `backdrop-filter: blur(14px)`,
  so that layer recomposites every frame the canvas changes.
* **Select removed from Pad.** It edited already-recorded points, so replay drew
  a stroke at its new position at its old timestamp. Also what forced the
  history-aliasing fix.
* **Magnify restored, desktop only.** The button exists where the gesture does
  not.
* **Flip Mode in the overflow menu** with the original book glyph and a subtitle
  that says what it is.
* **Pen / Background switcher** in the draw drawer, `width: fit-content`.
* **Recent is pen-only**, hidden in Background mode.
* **Flip navigation guard** on both surfaces.
* **`.draw-inline` wraps** instead of clipping six controls into a two-child
  container.

## Open

`harness/verify_tools.py` has 25 selection references that will fail now Pad has
no Select. Untouched: it is your suite.

No harness run stands behind this build.
