# v233 — the stuck pill, and the fill's corners

## 1. "Saving…" stayed up forever

> "Saving stays blinking."

`SkriblDraftStore.put()` had **no timeout**. IndexedDB on iOS Safari can accept a
multi-megabyte write and then neither resolve nor reject it, so `_mediaSpillState`
stayed `'saving'`, the pill never moved off "Saving…", and — because every later
save re-entered the same branch — the state was not merely stuck but *sticky*.

The spill now races a 12-second deadline. Past it the bytes are treated as lost,
which is the truthful reading: a write that hasn't landed in twelve seconds is
not one a reload can count on. A late resolve is ignored, because by then the
amber has told the user the truth and flipping to green would un-tell it.

That also explains the "Saved without media" that outlived its photo: once a
spill fails, `pendingPhotoMeta` is set and survives until the image is re-added
or dismissed. The amber was correct — it just had nothing on screen to point at.

## 2. The pill sat on the Pen button

`lib/pillfit.js`'s target list read as "the bottom chrome" when what it means is
"anything the pill must not cover". Popovers were missing, so with the tool tray
open the pill parked squarely on the Pen cell. `#toolTray` and `#shapePop` are
targets now. They are tall, so lifting usually can't clear them and the pill
fades instead — right, for a transient status against a menu the user just
opened. **A warning still refuses to fade.**

## 3. The fill's dotted edges, round two

The v231 fix — group rows by exact extent — was correct and incomplete, and the
same report came back.

`drawLine` uses **round caps**, so a run paints a *stadium*, not a rectangle: the
ends curve inward toward the top and bottom of a thick line. Two things followed
from that, and both had to go:

- **Tall groups.** A circle's widest rows repeat their extent and so form the
  tallest groups — which is why the bare corners appeared at the far left and
  right of a filled circle and nowhere else. Groups are capped at 3 rows.
- **The inset.** Runs were pulled in by half the lineWidth to stop the caps
  bleeding past the boundary. True of the centre row, false everywhere else. Runs
  are drawn to their **full extent** now and the cap bulges outward instead.

The trade is deliberate: at most ~2px of sideways bleed, underneath a boundary
line already wider than that. **Gaps are far more visible than bleed**, and
between a fill that stops two pixels short and one that runs two pixels over,
the one that runs over is the one nobody reports.

Measured on a filled circle, rasterising the runs exactly as `flip.js` draws
them: **52 of 7845 pixels bare before, 0 after.**

## The test that was missing

Everything `verify_fill` asserted was about the runs' **geometry** — one run per
row on a slope, bounded height, every row covered once. All of it passed while
the fill visibly had holes, because none of it knew that `drawLine` paints a
stadium.

The new assertion rasterises the runs onto a canvas and counts mask pixels the
paint misses. It is the only check in the file that sees the **renderer** rather
than the plan, and it failed on first run — 52 pixels — which is how the second
half of the fix got found rather than shipped.
