# v216 — the lag cause, and four changes

## The lag is fixed, and the cause is known

**A live `conic-gradient` on the colour swatch.** Measured A/B on device: the
full v215 build with the gradient was laggy to draw on; the byte-identical build
with a flat colour was smooth.

`.toolbar` carries `backdrop-filter: blur(14px)`. That layer must recomposite
every frame the canvas behind it changes — i.e. every frame while you draw — and
a live gradient inside it made each recomposite expensive enough to drop stroke
points. Hence "fine when slow, chunky when fast".

**The ring is now a pre-rendered PNG** (26px at 3x, 2.7KB, transparent core)
embedded as a data URI. A static image cannot be re-rasterised per frame, so the
rainbow is back at no cost.

Three earlier hypotheses were eliminated by measurement and are recorded so
nobody re-tests them: the segslider trackers (0.4ms per 600 stroke segments),
forced layout per pointer move (v215 measured FASTER than v214), and DOM size
(identical node count).

## Changes

**1. Select removed from Pad.** Pad captures a performance; Select edits points
that were already recorded, so replay draws a stroke at its NEW position at its
OLD timestamp. It is also what forced the history-aliasing fix, since every
other writer appends and Select was the first thing to mutate an existing point.
Shape stays — it generates ordinary points in order, which is on-model. Flip
never had Select, so this also restores symmetry.

**2. Magnify restored, desktop only** (`min-width: 641px`). The justification is
the gesture, not the space: a phone has pinch, a mouse has nothing, so the
button exists exactly where the gesture does not. Below 640px the **Zoom** row
in the media drawer keeps Fit and the presets reachable, so nothing reachable
only through this button becomes unreachable.

**3. Media control is 1.5x wide with two dots.** Photo and note are now separate
glyphs, each with its own status dot. One dot for two sources forced a
precedence rule — amber beats green — and still could not say WHICH item needed
re-adding. Two dots let each item report itself and the rule disappears.
Measured: the row goes 308px to 343px and still fits one line at 375px.

**4. Flip keeps its book glyph** in the overflow menu. The original icon meant
something — it is a flip book — and the generic rectangle that replaced it did
not.

## Measured

    375px   bar 343px  one row  7 controls  magnify hidden
    393px   bar 361px  one row  7 controls  magnify hidden
    430px   bar 398px  one row  7 controls  magnify hidden
    641px   bar 539px  one row  8 controls  magnify shown
    2560px  bar 539px  one row  8 controls  magnify shown

## Needs doing before this can be sealed

**`verify_tools.py` has 25 references to selection** and will fail now that Pad
has no Select. They must be removed rather than left to rot. Not done here: it
is your test suite and deleting assertions is not a change to make silently.

Still unverified generally: no harness run stands behind this build.
