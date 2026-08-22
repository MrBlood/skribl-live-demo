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

## Button system pass (owner-driven, same v205 cycle)

After the size fixes above, a design-system pass answering "would this pass an
Apple HIG audit?" — without flattening the app's existing shape language.

**Shape language kept, on purpose.** The shapes already mean something:
rounded-square tile = tool/opener; round toggle = on/off switch; pill segment
= one-of-N with a sliding highlight; labelled pill = named action. Only ONE
genuine inconsistency existed and was fixed: Flip's undo/redo were circles
while Pad's (same function) are tiles — now tiles on both, matching the
tool rule. Nothing else changed shape.

**Sizes, by discretion, NOT everything to 44.** Header icon buttons 44/24
(desktop) · 40/22 (phone); action pills 44 tall; drawer toggles 32/18 (aligned
to the 32px segments they share rows with); segments fixed 34px cells,
centered; page-bar 40; color dots 30. Forcing 44 into drawers/swatches/phone
toolbars breaks layout, so those keep their visual size and instead gain an
invisible tap area (below).

**HIG tap areas.** Every sub-44 control grows an invisible `::before` hit
region to >=44pt (`--tap-grow` per family) with zero layout change. Found and
fixed during build: the ::before extends OUTSIDE the button over the parent
row, and without a stacking context the row won the hit-test in that band —
elementFromPoint even claimed the button while the real click target was the
row. `z-index:1` on the targets fixed it, and `--tap-grow` is +1px over the
arithmetic to absorb border-box rounding at the edge. Verified by an actual
click 5px outside the visual box that toggles the control, and one 12px
outside that does not (bounded).

**States, defined once.** Pressed = scale .94 + brightness .9 on every control
(reduced-motion drops the scale). Disabled = opacity .42, no pointer, no press.
Loading = `.is-loading` hides the label, shows an in-place spinner, keeps the
footprint, blocks re-tap.

**Style roles.** Post = filled (the one primary); Record = tinted; Play /
utilities = plain. Menu rows pinned to 44 min-height.

Gates: ux 166 (new pins: 32px visual preserved; 5px-outside tap toggles;
12px-outside does not; Flip undo/redo are 12px tiles), visual 76, parity 115,
cssplit 16, player-isolation 20, pages 44, tips 43.
