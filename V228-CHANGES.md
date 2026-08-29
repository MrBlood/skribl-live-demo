# v228 — the size-class migration, finished

v227 shipped the size class with the migration deliberately partial, and said
so. This closes it. The change is small in lines and specific in effect: every
rule that had an opinion about **where compact begins** now reads one attribute,
and the ~20px band where the app contradicted itself is gone.

## What was actually wrong

`lib/sizeclass.js` measures the ELEMENT (v227, for the host column). The media
queries left behind measured the VIEWPORT. Those are different numbers whenever
a scrollbar exists, so **three boundaries were live at once**:

| boundary | measured on | decided |
|---|---|---|
| `[data-size]` | the element, `> 640` | whether the page bar exists |
| `@media (min-width: 641px)` | the viewport | tool-row and header sizing |
| `@media (min-width: 645px)` | the viewport | whether page-bar buttons carry labels |

In a standalone window from **641 to 660 viewport px**, the first said compact
and the other two said regular. The visible result was the compact surface
wearing the desktop toolbar: the page bar hidden and its ⋯ replacement active,
while the tool row sat at its 44px desktop sizing. The 641/645 pair is its own
small bug — four pixels where the labels were hidden but the sizing was not,
which nobody chose.

Measured across 29 widths: **7 disagreed before, 0 after.** The other 22 are
byte-identical in computed style, which is the claim this change makes — a
no-op everywhere except the band it exists to fix.

## `:where()`, and why it is load-bearing

`flip.css` resolves its phone ladder by **source order at equal specificity**.
Its own comments say so, in the words of someone who had already been bitten:
*"Moving them loses them silently; that is exactly how the old max-380 tier's
gap came to be dead code."*

A bare `[data-size="compact"]` prefix raises those rules from (0,1,0) to
(0,2,0) and lets them beat every tier below. Measured, that flattens the 320px
tier's gap from 2px to 3px — a phone regression shipped inside a change
announced as a no-op. `:where()` contributes zero specificity, so source order
still decides. `verify_sizeclass` mutation-tests this: strip the `:where` and
the 320px assertion fails.

## The suite learned to see the failure

`verify_sizeclass` previously asserted that **some** `max-width` queries
remained — a statement equally true of a migration 1/8 done and 7/8 done, and
blind to whether the survivors *disagreed* with the class. It is now structural:
no width query may sit at or above `COMPACT_MAX`, so a query cannot reach the
boundary to contradict it. Seven tiers below it survive and are asserted to
survive, because how a row keeps fitting inside compact is a different question
from where compact starts.

18 assertions → 34. Three mutations, all confirmed to fail the right check:
drop the `:where` (ladder flattens), restore a straddling query (straddle check
fires), desync the two surfaces (six band widths fire).

One dead rule removed: a `@media (max-width: 640px)` block containing nothing
but a comment. The comment was a recorded decision and survives; the empty query
did not.

## Still open, carried honestly

* **The host column width is still unconfirmed**, and it is still the question
  that matters most. If it is ~510px then Skribl inside the host is always
  compact and the regular surface exists only in the standalone app. Whether 640
  is the right threshold for a COLUMN, and whether a third class belongs between
  510 and 640, remain the owner's calls. This change makes them cheaper, not
  answered: the threshold is one constant, and now nothing disagrees with it.
* **Seven `max-width` tiers remain** (359, 360, 392, 400, 440, 559, 560). They
  are progressive squeeze inside compact, not a second opinion about the
  boundary, and they are left deliberately.
* The **v213 stray-line report** has still never been shown to be the
  contact-identity defect `lib/eventpoint.js` fixed.
* A **signed tag or CI attestation** does not exist; the seal remains corruption
  detection, not provenance.
