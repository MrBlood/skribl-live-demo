# v204 — UI feature release (Grid, tune drawer, icon, help, toast)

Not a review response: a feature release driven by the product owner. No sealed
review findings outstanding; the v201/v202/v203 residuals carry forward.

## What changed

- **Grid moved to the tune drawer, both editors.** It was a Flip-only row in
  the shared draw drawer; it is now a tune-drawer control (a working aid,
  alongside Speed/Onion/Motion guides). This makes the shared color/brush
  drawer identical across Pad and Flip except the deliberately-kept cosmetic
  divergences (preset dots, brush range).
- **Pad gained a tune drawer.** New for Pad, holding Grid today; the shell
  exists so future single-canvas aids have a home. Reuses the tune-shell
  markup and lib/drawers.js exclusivity.
- **Grid is now shared code.** Flip's ~60-line grid overlay was extracted
  verbatim into lib/gridoverlay.js (skriblGrid(canvas, overlay)); both editors
  call it. Pad gained a #padGrid overlay canvas.
- **Grid/tune WIRING is editor-only.** editor_tune.js (loaded after app.js,
  not by the player) holds the button/drawer wiring and the grid state, so the
  player download does not carry it — the same split as editor_export/post.
  Net player-JS growth: 60 B (one layout hook), vs ~1,300 B for a naive add.
- **Motion-guide icon → flight-path arrow** (option D), replacing the
  arc-with-dots that read like signal bars.
- **Help text:** Motion guides added to the "Set the timing" step (it was
  entirely missing); Grid's documented location corrected Draw menu → Tune
  drawer.
- **Flip intro toast replaces the footer.** The always-present .flip-hint
  footer forced the page to scroll on load; it is deleted. A once-ever
  SkriblHints toast now fires on Flip start (honours the Tips toggle, persists
  seen, dismissable, points to the ⋯ menu).

## Decisions (owner)

- Draw-on NOT added to Pad; draft-slot parity for Flip skipped; cosmetic
  draw-drawer divergences left as-is — all by owner choice.
- **Player-JS ratchet:** the v203 A1 raise (→142,160) is signed off, and v204
  raises it 60 B further (→142,220) for the grid-sync layout hook, after the
  editor-only extraction cut the rest. Documented in verify_player_isolation.

## Gates

Pixel/behaviour suites are the gate for a UI change: visual 76, parity 115,
cssplit 16, ux 149 (9 new v204 pins — Pad tune drawer opens, Grid paints the
overlay and lights, Grid gone from the draw drawer, Flip intro toast fires,
footer gone), lib 8, player-isolation 20, jsstrip 27.

## Caught during the build

A temporal-dead-zone bug: layoutEditorCanvas() runs during init and read the
grid state, but the state was declared with `let` further down — a
ReferenceError that halted module init and broke the export-format label. node
--check passes it (runtime ordering, not syntax); verify_ux caught it. Fixed
by the editor_tune.js extraction, which owns the state entirely.
