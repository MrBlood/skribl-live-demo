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
