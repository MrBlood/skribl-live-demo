# Delivery Stages, Research Gates and Acceptance Checklist

**Scope:** Proposed release order; no dates, estimates, or claims that current production is in a particular state. Product owner approval and repository working agreements govern actual work.

## Stage 0 — Integrate this package with the rechecked repo

- [ ] Read `CURRENT_REPO_AUDIT.md` and verify the repo still matches the newer owner upload. Re-read latest `DECISIONS.md`, `FUTURE.md`, `START-HERE.md`, `docs/NEXT-SESSION.md` and current work items before copying recommendations.
- [ ] Identify what has already shipped, what is already decided, what is still open, and what exists only in earlier analysis text.
- [ ] Retire the older review contents under `docs/research/blooby-vs-another-app/` and `docs/research/blooby-skribl-refined-review/` **only after** replacing their references in `docs/NEXT-SESSION.md`; keep valid historical decisions and owner corrections intact.
- [ ] Confirm current branch/production/deployed environment and automated test baseline; both uploaded ZIPs are v330 and the newer one adds research documents and an updated handoff, not new app code.

**Exit:** a small deduplicated, owner-reviewed list of active issues and approved design questions—not a giant imported wishlist.

## Stage A — Reliability and immediate experience

- [ ] Reproduce or close the iPhone embedded text/keyboard jump on a physical phone.
- [ ] Confirm placed-text finger dragging and no unintended movement after release; test touch vs mouse separately.
- [ ] Owner resolves desktop placement semantics; regression tests cover the chosen behavior.
- [ ] Confirm desktop How it works examples are accessible by pointer and keyboard.
- [ ] Confirm Help closing returns to original context from Pad/Flip entry.
- [ ] Mock and resolve Draw back attribution/banner obstruction while keeping faint/full/hidden source control reachable.
- [ ] Check the documented `verify_tools` V214b failure (`textwrite.js` touchend/touchcancel) against **latest** CI; fix the missing cancel path if still present, and show the test failure before and pass after the fix.
- [ ] Regress standalone Pad/Flip and embedded Blooby variations of shared controls; ensure saves/replays match before and after edits.

**Exit:** verified defects addressed; no new movement, obstruction, lost work or broken CI caused by fixes.

## Stage B — Product loop / usability study (may run alongside Stage A)

- [ ] Mock at least two subtle playback-end treatments on phone and desktop; keep artwork visible with Watch again and eligible Draw back.
- [ ] Explain “Draw back” in natural language (“Add to this drawing”) at first encounter; preserve the brand name.
- [ ] Make ineligible states honest (login, permissions, unsupported drawing) rather than dead buttons.
- [ ] Make return-to-original and browse-responses paths visible after drawing or exiting.
- [ ] Observe five uninstructed users, mix of actual phone/desktop: make drawing → watch → respond → return.
- [ ] Record anonymous device, task, completion, hesitation, wrong expectation, severity, proposed minimal correction, and retest.

**Exit:** first-time users can complete the four-step journey without coaching, and the developer has evidence about remaining friction.

## Stage C — Contribution-layer architecture / family tree

- [ ] Mock independent A and B authored contributions with read-only composite, source-only and response-only views; do **not** skip the current handoff’s explicit owner-approval gate.
- [ ] Obtain owner decisions on versioning, deletion/moderation, permissions, creator rights, edits/recoloring, media policy and legacy behavior.
- [ ] Keep source and response stroke data separately stored/authorized while retaining per-stroke meaning and playback.
- [ ] Render A→B, A→B→C and A→D correctly without copying every ancestor into each descendant's authored payload.
- [ ] Show root/parent/direct responses and a path back, without requiring an elaborate graph UI.
- [ ] Maintain old combined Draw back posts in their current form; no unapproved migration.
- [ ] Validate by full player, in-post player, Gallery preview, export (as approved), device performance and access control.

**Exit:** independently attributed contributions, correct replay and ancestry, compatible old posts, and safe handling of source removal—**as chosen by owner**.

## Stage D — Shared primitives → Pad editing layers

- [ ] Explicitly decide to proceed after Stage C; do not treat this stage as automatically implemented by Draw back.
- [ ] Prove reuse of shared layer/data/compositor/timeline functions; document unavoidable Pad-specific logic.
- [ ] Prototype two editor layers: Rough and Ink; visibility, basic reordering and optional lock.
- [ ] Test cross-layer timing Rough→Ink→Rough; replay reflects original global event order.
- [ ] Test select/transform, undo/redo, save/reopen, posting, preview, all players and export with layers.
- [ ] Confirm no conventional Pad flood-fill was introduced and stroke-by-stroke identity remains intact.
- [ ] Keep controls hidden/simple unless the artist opts into layers; device testing verifies canvas remains primary.

**Exit:** a layer-enabled Pad drawing edits correctly and redraws itself faithfully without degrading existing drawings or phone experience.

## Stage E — Flip layers (later)

- [ ] Prototype two layers within one frame, then several frames.
- [ ] Verify onion skin, holds, page order, range loop, Keep under/Draw-on and Flip exports.
- [ ] Decide whether persistent animation layer tracks warrant the additional UI and schema cost.
- [ ] Maintain Pad/Flip distinction and reuse shared primitives without forcing identical timeline behavior.

**Exit:** only release features that work across Flip editor, player, export and phone.

## Stage F — Community/growth experiments, after core loop

- [ ] Pilot one weekly featured Draw back prompt using existing posts before building a challenge engine.
- [ ] Consider a Gallery “Draw back ready” filter, then branch exploration when lineage exists.
- [ ] Consider lightweight replay preview sharing and optional creator-defined replay chapter markers.
- [ ] Add accessible artwork description at publish time if compatible with owner standards.
- [ ] Review moderation of source and derived posts, legal/privacy/reuse/rights, permission changes and public registration gates before broad launch.

## Ongoing compatibility suite — suggested fixtures

1. Old Pad drawing / old Flip animation / old joined Draw back / new independent contribution.
2. Two contributors; three-generation line; sibling branches; missing source; moderated source; blocked users; revoked future contributions; inactive author.
3. Distinct stroke timings and source compressed overture; select individual contribution; hide/display; source/edit-version freeze.
4. Interleaved editing layers (Pad); mixed frame layers with holds/loops (Flip).
5. Save/reopen and export across relevant surfaces. No unexpected instant fill or missing strokes in Pad.
6. Low-powered phone, slow network and long drawing; bounded points/assets/references; no unbounded recursive fetches; player remains editor-free.
7. Screen reader / keyboard / actual touch paths; contrast/reduced-motion expectations; no canvas-obscuring persistent overlays.

## Simple product success measures (proposed, not existing data)

- New visitor draw-start → first-drawing completion.
- Replay view → completed watch.
- Eligible replay view → Draw back opened and completed.
- Contribution posted → parent/branch discovered.
- Creator active again within seven days.
- Save/publish failure frequency and real-user UI surprise/obstruction reports.

**Privacy note:** aggregate interactions, not personal artwork or raw strokes, are sufficient for these measures.
