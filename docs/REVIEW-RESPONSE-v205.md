# v205 — UI fix pass on v204

Owner-driven refinements after reviewing v204 in the browser. No review
findings; the v201–v203 residuals carry forward.

## Fixes

- **Pad tune drawer moved to the header.** It was in the bottom toolbar in
  v204; it now sits in the header actions beside record/play and slides down
  FROM the header, structurally identical to Flip (same tune-shell markup and
  the same `margin: -10px 7px 0` tuck under the floating header card).
- **Motion-guide icon -> B (dotted trail + moving head).** v204 shipped icon D
  (flight-path arrow), but at the 13px glyph size its arrowhead was illegible
  and it read as the old arc. B's leading dot survives small sizes.
- **Small toggle icons enlarged 13px -> 16px** (the `.onion-tint` family:
  motion guides, grid, onion-skin tint). This was the root reason D looked
  unchanged; 16px in the 22px button reads clearly.
- **Canvas ring 2px -> 1px** (styles.css dark + light, player.css re-emitted).
- **Flip intro toast is now a roomy panel.** ~80% of the canvas width (capped),
  larger text, an explicit X, and NO auto-dismiss — the v204 toast used the
  shared 6.2s hint timer and vanished before it could be read. Small quick
  hints keep their auto-dismiss behaviour.
- **Tune button hidden while recording** (Pad), joining Help + the overflow
  menu. It added ~40px to the header and is meaningless mid-capture; its width
  was pushing the record indicator onto the "Skribl Pad" wordmark at ~600px.
  It returns the moment recording stops.

## Not changed (investigated)

- The Flip page-action bar's Delete button sitting at the horizontal-scroll
  edge at narrow widths is pre-existing `overflow-x: auto` behaviour, unchanged
  since before v204 and most visible with devtools narrowing the viewport. Left
  as-is rather than risk the page-navigation UX.

## Gates

Pixel/behaviour suites are the gate: visual 76, parity 115, ux 156 (new pins:
Pad tune button in header not toolbar; intro toast is the panel variant with an
X and does not auto-dismiss; the X dismisses it; at 600px the tune button hides
while recording, the record indicator does not overlap the brand, and the tune
button returns after stop), cssplit 16, player-isolation 20, tips 43, lib 8.
