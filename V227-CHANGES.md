# v227 — what changed since the sealed v225

**Evidence status: SEALED.** `harness/RELEASE.md` is generated from a full
aggregate run against this tree and states the result, the assertion count, the
suites reporting and anything skipped, naming the CI job that covers each skip.

Two releases in one: v226 gave Flip's filmstrip page RANGES, and v227 finished
the four-stage plan that gives page management back to the film without taking
it away from the desktop.

## Narrative

**The plan started wrong, and the owner corrected it.** The first design note
argued for handing every page operation to direct manipulation and demoting the
button bar everywhere — quoting the design direction's *"No 'Move left'. No
'Move right'. No page-management cluster."* That quote sits in the section about
Flip **on a phone**, and the sentence a few lines later reads *"Desktop is not
phone-but-wider."* Two objections settled it: **buttons are good on a big
screen**, where hiding a control to reclaim space you already have is affectation
rather than restraint; and **not everyone knows the gestures** — a drag, a
long-press and a swipe are invisible until someone tries them, while a visible
row teaches every operation the app supports without anyone discovering
anything.

So the target was never *no controls*. It was controls that match the room
available, with the gestures present at every size for people who find them.

**What the strip region cost, and what it costs now.**

| | before | after |
| --- | --- | --- |
| page bar (regular) | 6 buttons | 3 — Left, Right, Copy, Delete |
| page bar (compact) | 6 buttons | none; a ⋯ on the active tile |
| above the strip | 4 with Paste | 3 |
| on the tile | delete ✕ | ✕, hold badge, paste ghost, ⋯ (compact) |

**Three controls left the bar, and none of them for space.** *Move artwork*
moved the DRAWING while sitting in a row about pages — it takes a drag on the
canvas, it has a mode, and it belongs beside Select and Liquify in every respect
except where it was filed. *×Hold* moved onto the badge that was already drawn
on the tile showing the value the button cycled: two pieces of interface for one
fact, and the better-placed one was the one you could not press. *Paste* became
a dashed ghost tile standing in the gap it will fill, because a button could say
WHAT but not WHERE — "after the current page" was a rule you had to know.

**Page ranges (v226).** Shift-click or a long-press sweep selects a run on the
strip; Copy, Delete, ×hold and the arrows then mean "these pages"; ⌘C/⌘V move
runs between positions. No new buttons — the same controls, re-scoped, which is
what the direction asks for. The arithmetic lives in `lib/pagespan.js` and
carries the case that is always wrong first time: a span moving RIGHTWARDS lands
short by its own length unless the target is adjusted for the splice-out.

**The size class, and the reversal in it.** Eight `max-width` rules in one
stylesheet, none agreeing where "small" begins, with a measured cost: one pixel
of resize took Pad's toolbar from 398px to 565px. `lib/sizeclass.js` is the one
decision they migrate onto — and it changed its mind once, on purpose.

v226 measured `window.innerWidth`, because the claim being made was that
migrating a rule onto the class was a *no-op*, and innerWidth is what the CSS
`width` feature uses. Correct for that claim. Then the owner supplied the case
that settles it: **the host site reserves a column for Pad and Flip, around
510px.** Inside a 1400px window that column measures 1400 by the viewport and
510 by the element — so viewport measurement classifies REGULAR and lays a
persistent command row into a space that cannot hold one. Wrong in the primary
embedding, and wrong in the direction that breaks the layout. It measures the
element now, and what that costs — a ~15px band where the migrated rule and the
unmigrated queries disagree — is asserted rather than discovered.

**Stage 4 shipped because its condition was met, not because it looked good.**
The compact surface drops the row for a ⋯ on the active tile. The design note's
own gate was accessibility: a filmstrip you can only operate by dragging is one
some people cannot operate. So the trigger is a real button with `aria-haspopup`
on a tile in the tab order, opening a `role="menu"` of real buttons; focus moves
in on open, arrows walk it, Escape returns focus to the trigger, and the items
are no smaller than the `.pb` buttons they replace. Every one of those is an
assertion in `verify_compactops.py`, alongside one proving the REGULAR surface
was left alone — a change scoped to one surface is only correct if it was.

## Bugs found by building this

**A temporal dead zone, in the file that warns about them.**
`SkriblSize.observe()` classifies synchronously, so it dispatched `skribl:size`
during init; a listener registered 160 lines earlier called `buildStrip()` →
`updateToolState()` → a `const` declared 250 lines further down. "Cannot access
'playBtn' before initialization", and every handler after it dies silently. The
fix is also the semantically right one: the event means *changed*, and going
from nothing to a value while the page is parsing is not a change.

**An unconditional line in a shared path.** `setTool` ended with
`pad.style.cursor='none'` — correct for every tool that existed when it was
written. Routing Artwork through it meant `setMoveMode` set the grab cursor and
four lines later the same function wiped it: the mode was live and the canvas
did not say so. Moving a feature into a shared code path subjects it to every
unconditional line already in that path.

**And two buttons both labelled "Move"**, which this project had already
recorded as a defect. They say Left and Right now.

## Still open, carried honestly

* **The host column width is unconfirmed.** If it really is ~510px then Skribl
  inside the host is ALWAYS compact and never sees the regular surface — the
  persistent row would exist only in the standalone app. Two questions follow
  and both are the owner's: whether 640 is the right threshold for a COLUMN (it
  was inherited from rules written about phone viewports), and whether a third
  class belongs between them, since a 510px column has a mouse, hover and a
  keyboard and can afford what a 360px phone cannot. Nothing has been built for
  either. `SkriblSize.COMPACT_MAX` is one constant in one file so the answer
  stays one edit.
* **Fourteen `max-width` queries remain in `flip.css`.** `verify_sizeclass`
  asserts they are still there, so the narrowing is permanent and visible
  rather than conversational, and finishing the migration costs a deliberate
  edit to that assertion.
  **SUPERSEDED by v228** — the boundary queries are gone and seven sub-boundary
  tiers remain by choice. See `V228-CHANGES.md`; that work also found the band
  where the class and the queries disagreed.
* The **v213 stray-line report** has still never been shown to be the
  contact-identity defect that `lib/eventpoint.js` fixed.
* A **signed tag or CI attestation** for release provenance does not exist; the
  seal remains corruption detection, not provenance.
