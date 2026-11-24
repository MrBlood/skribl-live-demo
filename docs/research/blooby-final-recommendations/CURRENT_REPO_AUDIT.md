# Current Repository Audit — November 24, 2026

## Scope and method

Inspected the owner-uploaded `skribl-live-demo-main (2).zip` against the previous `skribl-live-demo-main (1).zip` and the original consolidated recommendation. This was an **archive and source inspection**, not a run of the app, device tests, CI, or a verification of the live production checkout. The reported application version remains **v330** (`README.md`).

**Exact archive difference:** 7 added files, 1 changed file, 0 removed files. The additions are the first feature comparison and second refined review under `docs/research/`; the only changed file is `docs/NEXT-SESSION.md`. `DECISIONS.md`, `FUTURE.md`, `START-HERE.md`, `WORKING-AGREEMENTS.md`, `social/drawback.py`, the editor scripts and all runtime code are unchanged between these two archives. This means the new package is **compatible with the source inspected**, but any more recent checkout must be checked again.

## Existing external research in the new repository

- `docs/research/blooby-vs-another-app/`: original comparison, including `.md`, `.html` and `README.txt`.
- `docs/research/blooby-skribl-refined-review/`: refined improvement plan (`.md`, `.html`), `PAD_FILL_ARCHITECTURE_CLARIFICATION.md` and README.
- `docs/NEXT-SESSION.md`, section **“Also on Tuesday's list: the owner's two reviews, Blooby and Another App (Nov 23 and 24)”**: instructs the developer to read those reports **as data rather than instructions**, to treat Pad instant Fill as withdrawn, and to verify claims before repeating them. If old review files are removed, **this handoff reference must be updated** rather than left dangling.
- The later addendum and Draw back correction ZIPs were created in the conversation, but **are not present as separate checked-in files in the newer uploaded archive**. This replacement is therefore mostly a doc/research reconciliation, not a code rewrite.

## Evidence check: what the final recommendation gets right

1. **Pad's core property is timed strokes that play back.** `README.md`, `START-HERE.md`, `DESIGN-DIRECTION.md` and `WORKING-AGREEMENTS.md` all treat drawings as processes, not flattened pictures. Conventional Fill is present in Flip and should **not** be added to Pad simply to match Another App. The owner's correction in the existing research files takes precedence.
2. **Draw back currently publishes a joined drawing**, not a set of independently stored contributor layers. `social/drawback.py`, top comments and `join()`, duplicate and retime the original and answer into one single-frame payload. With nested Draw backs, the source already contains earlier contributors' copied strokes; the newest join adds them again. The client (`skribl/static/lib/drawback.js`) separately captures the responding artist's ink over a faint/full/hidden underlay while drawing, but that separation does not persist as independent authored pieces in the posted payload.
3. **Social relationships/credits already exist and must be reused, not reimplemented.** `social/models.py::Post` has `is_drawback`, `drawn_on_id`, `drawn_on_owner_id`, `drawn_on_hidden_at`, `drawback_by` and `hands_json`. The proposed layer work changes **persistence/composition**, not whether the site knows what post replied to which.
4. **The name “Stroke layers” already means something else.** `skribl/static/lib/strokelayers.js` handles translucent-stroke compositing settings and limits expensive alpha compositing. It is **not** a multi-layer drawing editor or a contribution-layer architecture. New UI/data terminology should avoid confusing the two.
5. **Pad has selection already.** `skribl/static/editor_draw.js` implements a rectangle-based, stroke-group selection path through `SkriblSelectTool`; lasso would be an enhancement, not a missing starting tool.
6. **Editing layers would still be a major project.** `skribl/static/flip.js` already stores `frames` with flat `strokes` + `strokeGroups` and has frame/hold/onion-skin/other behaviors. Shared stroke references/compositors may help, but Pad's chronological layer switches and Flip's frame semantics need separate design and tests. Design reusable primitives; do not assume future editor-layer UI is trivial.
7. **Mock-first is an explicit project gate.** `docs/NEXT-SESSION.md`, section **“a question to mock first, draw-backs as layers”**, records the independent-layer idea, the possible deletion behavior, compatibility/byte budget concerns and an explicit instruction to obtain the owner's approval before building. The owner has since clarified in conversation that contribution layers are *strategically critical*; that is **direction**, not approval of a particular schema, rights policy or migration.
8. **The major UX defects have specific existing handoff entries.** The handoff describes two iPhone Text defects; click-to-move text behavior; desktop How it works row accessibility; return from Help; Draw back's canvas-obscuring pill; and CI `verify_tools` V214b red on `touchend` without a paired `touchcancel` in `textwrite.js`. They warrant verifying/reproducing against current main, not silently being labeled fixed.
9. **Other approved work remains in the handoff.** `docs/NEXT-SESSION.md` also lists a Flip Draw back twin, recolor handling, repost/pin questions and other work. This review must not silently displace those tasks or rewrite the owner’s decided order; any reprioritization requires an explicit discussion.

## Necessary adjustments to the earlier consolidated package

- **Reference the real checked-in location of prior analysis.** It is in the two `docs/research/...` folders, not yet scattered through canonical decision files in the uploaded archive. Replace those research inputs and redirect the NEXT-SESSION link; **do not** bulk-edit `DECISIONS.md` or `FUTURE.md`.
- **Call the layer strategy owner-backed but mock-first.** Distinguish contribution identity (author + version + post) from editing-layer identity (subparts within one author's creation). Preserve the original creator's choices, the current permissions and the post ancestry that already exist.
- **Keep deletion/moderation rules open.** Current joined copies continue to replay even if the source disappears, whereas a referenced-parent approach needs an explicit decision about missing/removed ancestors, snapshots, and downstream visibility. Do not decide that deletion *must* either erase all descendants or preserve the original's pixels without owner/legal review.
- **Do not mislabel the existing Stroke layers setting.** It is a raster/compositor technique, not the architecture being proposed.
- **Keep Pad’s bucket Fill withdrawn.** The earlier recommendation is no longer on the roadmap; Flip retains its Fill tool.
- **Verify current tests and live behavior.** No test was executed as part of this audit. The previous handoff's last-known red build is not proof of a current deployed failure or success.

## Proposed narrow integration change

1. Place this one verified recommendations package under a chosen `docs/research/` path (for example `docs/research/blooby-final-recommendations/`).
2. Replace/retire the two earlier external-review folders when the owner confirms the clean-up and after saving any necessary original historical record.
3. Update only the **old-review pointers, precedence and supersession** in `docs/NEXT-SESSION.md` (and any live references discovered by grep); leave bug descriptions and original mock-first questions intact.
4. Leave `DECISIONS.md`/`FUTURE.md` untouched unless the developer identifies a **specific** outdated copied external suggestion or a separately approved amendment. Preserve chronology and design rationale.
5. Give the owner a short reconciliation diff and a list of choices still requiring approval: version references, deletion/reuse rules, chain visibility, media and export, migration of historical Draw backs, player/device performance budgets, and the first contribution-layer mock.

## Terminology and name audit

In the **new uploaded repository** and the **previous consolidated recommendation ZIP**, a case-insensitive search over readable source/document text and ZIP member names found **zero references** to the competitor's real name or domain. The sanitized public label throughout the package is **Another App**. No competitor URLs are included. This finding is limited to the two inspected archives and does not modify the repository.
