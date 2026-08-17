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
  no right-edge overflow, no horizontal scroll, no same-row overlap. 24 pins.
  (Scope note per the v207 review: this is a right-edge + same-row horizontal
  audit, not a proof of full on-screen placement — see the response below.)

Gates: ux 259, visual 76, parity 115, cssplit 17, pages 44, tips 43, lib 8,
docs 34. Demo fixtures (harness/fixtures/) ship in this seal.

---

## Developer review of v207 (received after seal) — response

The reviewer's split is accepted as stated: **UI/device release: strong
candidate. Integration contract fully closed: not yet.** Seal evidence
(177/177, v207 stamp, compileall, node --check, 2,310/60/1, PG 14/14) was
independently confirmed by the reviewer.

| # | Finding | Status | What was done |
|---|---|---|---|
| F1 | P1 — SQLite AUTOCOMMIT guard checked the wrong SQLAlchemy field | **CLOSED (unsealed, next build)** | Reviewer exactly right and it was **dead code**: SA 2.x leaves `dialect.isolation_level` None for a real `create_engine(..., isolation_level="AUTOCOMMIT")`; the mode lives on `dialect._on_connect_isolation_level`. Guard now checks both. Regression builds a REAL AUTOCOMMIT engine (no faked attribute) and asserts the RuntimeError; a default engine is still accepted. verify_txcontract 34/34. |
| F4 | P2 — Record with Tune open stranded an open drawer with a hidden opener | **CLOSED (unsealed, next build)** | Reproduced. `editor_tune.js` exposes `window._skriblClosePadTune`; `beginRecording()` calls it first. Pinned exactly as specified: no `.open`, `aria-hidden="true"`, `aria-expanded="false"`, and stop does not reopen. ⚑ +23 B player-JS (`?.()` call), ratchet 142,344→142,370, flagged. |
| F2 | P1 — failed SQLite DB-backed POST can consume quota until pending TTL | **OPEN — needs owner decision** | The reviewer is right that the current regression uses a cap large enough to hide it; the decisive test is `SKRIBL_RATE_MAX_POSTS=1` → reserve → force host-commit failure → force the bounded cleanup failure → immediate retry. Two honest contracts: (a) make immediate retry mechanically true (release the slot on failure even if it means a second bounded write attempt), or (b) document that a failed SQLite DB-backed request may hold quota until pending-TTL. **This is a contract choice, not a bug fix, so it is not decided unilaterally here.** Recommend (a) — a user whose post failed should not also be told "slow down". |
| F3 | P1 — Pad replay's Web Audio unlock is fire-and-forget (iOS race) | **OPEN — real, deferred to next session** | Confirmed in `startWebAudioLoop()`: `audioCtx.resume()` not awaited; the ordinary Play path starts music from inside `clearAndRestore()`, which on the async `Image.onload` branch runs after the click gesture returns — the same unlock-timing class the v203 player fix (A1) closed. The fix shape is known (resume synchronously from the Play gesture, retain the Promise, start the loop when both restore + unlock resolve) and the A1 code is the template. Not attempted at end-of-session; needs the same care as A1 plus the regression the reviewer specifies (force the async branch, instrument resume, assert it starts before onload). Real iPhone remains the hardware check. |
| — | Phone-audit claim overstated | **ACCEPTED — wording corrected** | Reviewer is right: the audit is a strong **right-edge + same-row horizontal** fit check, not a proof that "every interactive rectangle is on-screen". It does not test left<0, vertical overflow, overflow-hidden ancestor clipping, off-row collisions, or pseudo-element hit-area overlap. The claim is narrowed here and in START-HERE; extending the checker is a follow-up. |

**Net for the next session:** F2 (owner decision), F3 (Pad audio unlock — the last iPhone item), and optionally widening the phone audit. F1 + F4 are done in the working tree and will seal as v208 with the pending ⚑ ratchet raise.
