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

## Fixed in v216b — three bugs, all mine

**The media button did nothing.** The toolbar handler calls
`toggle(btn.dataset.drawer)`, and `media` was never registered in the drawer
panel list. The call resolved to nothing — a button that looked right and was
inert. Registered on both surfaces.

**FLIP WAS COMPLETELY BROKEN.** `flip.js` lines 1740-41 did
`imageBtn.addEventListener(...)` with no null guard, and those buttons no longer
exist since they merged into the media control. That throws a TypeError at load,
so every line of flip.js after it never ran. Now guarded. `node --check` cannot
see this: it is valid syntax that throws at runtime.

**Recent showed pen colours under Background.** The Recent row sits between the
two swatch grids as a sibling, so switching to Background left it on screen
reading as "recent backgrounds". Recent is a list of PEN colours; it now hides
in Background mode, reading `recentColors.children` rather than a parallel flag,
since `lib/recentcolors.js` owns that row.

**Media note is now FILLED, not stroked.** A stroke-drawn note at 28px turns to
mush; solid shapes survive downscaling where thin outlines do not. The photo
frame stays outlined so it still matches Pen, Eraser and Shape. A single 26px
composite (frame with the note inside) was drawn and compared — it is a cleaner
icon in isolation, but it can only carry ONE dot, which brings back the
amber-beats-green precedence rule and its inability to say which item needs
re-adding. Two separate glyphs keep the honest signal.

**Media glyphs redrawn.** The photo and note now share optical height, corner
radius and stroke rhythm, so they read as one control rather than two mismatched
icons.

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

**4. Flip keeps its book glyph** in the overflow menu — the ACTUAL original,
copied verbatim from sealed v214: an open book with two facing pages and a
spine. An earlier pass claimed to "restore" it and in fact drew a new generic
stacked-rectangle shape from memory, which meant nothing. The original icon was
saying *flip book*, which is exactly what the control is.

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
