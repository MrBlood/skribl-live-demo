# v207 — owner review of v206 + consistency / help / phone audit

Owner-driven, from device testing of v206.

## Fixes from v206 device review

- **641px post-record header** wrapped "Post to Skribl" to three lines and
  overflowed: `.btn { white-space: nowrap }` (a pill must never wrap) and the
  short "Post" label held to 720px where the long one genuinely fits.
- **Nudge grid on phone overlapped/wrapped** at 390/363 (the tier-2 32px
  buttons made three ~120px pills that a 290px grid could not hold; an
  earlier "fits" check measured the grid box, not the pills — a real testing
  mistake). On phone the three groups now STACK one per row, label left,
  pill right.
- **Player Repeat button gave no feedback.** Looping worked; `.player-btn.active`
  was in styles.css but dropped from player.css because every css-live scene
  was static (no scene ever pressed it). Added to the live set + a pressed
  scene (ordered last — its click/focus state bled into the next scene's
  capture, a 4px strip). Button now lights accent when on.
- **Onion on/off moved from the header into the tune drawer's Onion row**
  (frees header space; row now [on/off][depth][tint]) as an .onion-tint
  toggle so it lights ORANGE like grid/motion/tint. setOnion + shortcut
  unchanged. Dead header-only CSS removed.
- **Loop-detail Focus/Zoom groups** were unstyled-in-CSS rounded-rects built
  from an injected <style>; now real .seg pills (round shell, sliding
  highlight) matching Speed/Onion, plus a magnifier glyph on the zoom group.
  segslider `placeAttached` accepts .on as well as .active so one convention
  serves the whole app.
- **Toast** is now just "New here? — How it works ->".
- **How it works** pills carry the real button glyph (same SVG the control
  renders); concept pills stay icon-less. Eyedropper glyph corrected (was a
  lookalike). Onion text no longer says "in the header". Added: Match Drawing
  Time; a new step 6 "Watching a shared Skribl" documenting the player's
  Play/Restart/Repeat/Mute/Copy-link — the viewer had zero coverage.
- **Eyedropper**: icon 16->18 (tier-2), and it was the one colour-row control
  missing its 44pt tap area — added, verified by a real off-box click.
- **All icons are SVG now.** Flip's page bar was mixed (Hold/Artwork SVG;
  Move/Move/Copy/Delete text glyphs) and add-page used the fullwidth ＋; text
  glyphs render at different weights across fonts. Converted. Hold's ×N count
  and the nudge −/+ stay text (numbers/operators, not icons).
- **Player**: the ⋯ button rendered 0x0 dead (its menu was removed earlier);
  it and the orphan #draftInput are gone.

## Audits before seal

- Consistency: Pad/Flip ⋯ menus parallel (7 items each); shared-id controls
  have no label/title diffs; Post/Play labels appropriate per surface.
- Help completeness: 51 user-facing functions cross-checked; 2 real gaps
  (Match Drawing Time, player controls) filled.
- Phone fit: every interactive control's real rectangle measured on Pad,
  Flip, Player at 375/390 — each drawer open in turn + music/fine-tune —
  nothing off-screen, no scroll, no same-row overlap. 24 pins.

Gates: ux 259, visual 76, parity 115, cssplit 17, pages 44, tips 43, lib 8,
docs 34. Demo fixtures (harness/fixtures/) ship in this seal.
