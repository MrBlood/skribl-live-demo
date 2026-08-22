# v218 — the shape picker moved onto the Shape button

## v218e — Flip's tool pill, and the two editors now read the same

**Flip's pen/eraser/shape pill did not work — same bug as Pad's, worse.**
`positionToolSlider` subtracted the GROUP's own `offsetLeft` from a button's
`offsetLeft`, which is already relative to the group because `.tool-group` is
`position: relative` and therefore the offsetParent. On Pad that was a couple of
pixels out. On Flip the group sits after the colour and media controls, so the
group's offsetLeft is large and the pill was thrown clear off its button — which
reads as the slider simply not working. Fixed the same way, plus re-placement on
ResizeObserver, resize, orientationchange and `fonts.ready`.

**The two editors ordered the same controls differently.** Pad ran tools, then
undo/redo, then colour and media. Flip ran colour and media first with the tools
after them. Same set, mirrored — so muscle memory built on one surface aimed at
the wrong thing on the other. Flip now matches Pad.

A note on how that reorder went, because it nearly shipped broken: the first
attempt pulled the blocks out with non-greedy regex, and `<div class="tool-group"
…>.*?</div>` stopped at the FIRST `</div>` — which closes `.tool-slider`, not the
group. Undo, redo, colour and media all ended up nested INSIDE `#toolGroup`. The
div COUNT stayed balanced, so a balance check passed; only rendering the page and
asking whether `penToolBtn.parentElement === toolGroup` caught it. Nested
containers need brace matching, not regex.

## v218d — the Air brush beaded on every tool change

**Reported as: Air looks fine until you switch to the eraser, then beads appear.**
Switching tool, before erasing anything.

`setTool()` calls `SkriblSelectTool.clear()` on every tool change. That calls
`selClear()` → `selRepaint()`, which repainted the ENTIRE drawing by passing the
raw `drawDot`/`drawLine` painters straight to `replayTimelineToCanvas`. Painted
that way, a see-through stroke's own overlaps stack at every captured point —
which is precisely what stroke layers exists to prevent, undone by a repaint.

Live drawing looked right because it takes the wet/dry path. The beads appeared
the moment anything called `selRepaint`, and picking the eraser calls it.

Measured, painting one 22%-alpha stroke both ways and reading the alpha profile
along it:

    segment by segment (old)      alpha spread 153   <- the beads
    solid then composite once     alpha spread  50   <- soft edge only

**`selRepaint` was the only repaint in the editor bypassing the compositor.**
Preview, playback and all three export paths already route through
`makeStrokeCompositor`; every other `replayTimelineToCanvas` call with raw
painters is the `else` branch of a `strokeLayersOn()` check. This one had no
branch at all.

Also: `selClear()` now returns early when nothing is selected. Pad has no Select
tool any more, so the common case was repainting the whole drawing to remove a
marquee that was never there.

## v218c — Flip's colour swatch had a leftover white border

The ring and its wiring were correct on Flip — `colorCurrentCore` gets the pen
colour, confirmed by rendering it. What was wrong sat on top: `.color-current`
in `flip.css` still carried `border: 2px solid var(--text-primary)` and an inset
white highlight. Those gave the swatch its edge back when it was a plain disc.
With the spectrum ring inside, they stacked into three concentric circles —
white border, rainbow, white core — where Pad has one clean ring.

Border and highlight removed; the ring is the edge now, sized 30px with a 24px
core so it fills Flip's slightly larger control at Pad's proportions.

This is the same shape of miss as the Pad `.tool-chip` white ring in v215: a
style written for the OLD control surviving the new one. Worth checking for
directly next time a control changes form.

## v218b — the width policy, decided and pinned

**360px is the design target. 320px is the safety net.**

360 must work properly — one row, nothing shrunk past the floor — because it is
a very common Android width, so a two-row bar there is not a rare fallback. It
was wrapping: the base tier had been sized for 375.

320 is not a design target. It is Display Zoom on a modern iPhone, an
accessibility setting rather than a legacy device, so it must DEGRADE rather
than break: wrap to a taller bar, clip nothing, spill nothing.

Measured across the range:

    320px   bar 288px   WRAPS (fallback)   clip 0   page overflow 0
    340px   bar 308px   WRAPS (fallback)   clip 0   page overflow 0
    360px   bar 326px   one row            controls 34px
    375px   bar 326px   one row            controls 34px
    393px   bar 359px   one row            controls 36px
    641px   bar 565px   one row            controls 40px

The 10px that bought 360 came from the tool group's internal button padding,
NOT from the controls — they stay at 34px. Reaching the same width by shrinking
them to 33px was measured and rejected: the tap targets are already under the
44px the docs assumed, and making them worse to save the same pixels is the
wrong trade.

**`verify_layout.py` now pins the policy** rather than leaving it as folklore:
360 joins the widths that must fit on one row, and 320 is asserted to wrap
without clipping AND without spilling horizontally, on both surfaces.

## v218a — three fixes from a real iPhone

**The tool pill was misplaced, and it was my regression.** `.tool-group` is
`position: relative`, so it is the buttons' offsetParent and `offsetLeft` is
already relative to it. The code subtracted the GROUP's own `offsetLeft` on top
of that — a double subtraction that only looked right while the toolbar's left
padding happened to equal the group's padding. v217a changed that padding from
`6px 4px` to `6px` and the pill slid off its button. It now measures against the
group's padding, which is what `.tool-slider`'s own `left` is matched to.

It also **re-places on layout change** — ResizeObserver, resize and
orientationchange, plus `document.fonts.ready`. A single `setTimeout(…, 50)` is
not enough on a phone, where the bar is often laid out after that and the pill
ends up measured against zero widths. Same failure `lib/segslider.js` exists for,
different element.

**A second phone tier at 393px.** The 640px block is sized for the narrowest
supported phone. Every current iPhone is 393px or wider and had room the 375px
squeeze was denying it. 393 is measured, not chosen: at 390px the larger sizing
wraps.

    375px   bar 343px   controls 34px
    390px   bar 358px   controls 34px
    393px   bar 361px   controls 36px
    402px   bar 370px   controls 36px
    430px   bar 398px   controls 36px

**The shape kind now follows the pointer.** A small line / rect / oval badge
rides beside the cursor while the Shape tool is active, using the same tracking
as the eraser ring — including clearing on `touchcancel`, since a cancelled
touch never fires `touchend` and a badge left painted with no finger near it is
the same stale state the ring used to have. The kind is chosen on the toolbar,
so without this there was nothing at the point of drawing saying what the next
drag would make.

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
