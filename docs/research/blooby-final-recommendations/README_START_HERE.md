# Blooby + Skribl — Final Synthesized Recommendation

**Status:** One consolidated **recommendation and developer handoff**, not an implementation order or an override of previously approved owner decisions.  
**Prepared and rechecked:** November 24, 2026.  
**Repository evidence:** the user's **newer** uploaded `skribl-live-demo-main (2).zip`, with the application still at v330. This is a source-document audit, not a verified live deployment or a fresh test run.  
**Status:** current-repository-checked revision of the previously consolidated package.  
**Supersedes:** the four earlier ChatGPT analysis/recommendation ZIPs and their conflicting recommendations, plus incorporates the latest discussion of reusable contribution/editor layers.  
**Audience:** product owner and developer reconciling advice with the live repository.

## What to read

1. **`FINAL_RECOMMENDATION.md` — the sole canonical product recommendation.** Priorities, product principles, what to do, what to defer, and acceptance outcomes. Start here.
2. **`LAYERS_AND_DRAWBACK_ARCHITECTURE.md` — architecture design brief, not a proposed final database schema.** Contribution independence, lineage, ownership boundaries, shared layer foundation, Pad and Flip reuse, playback, performance, and unresolved product decisions.
3. **`DELIVERY_AND_ACCEPTANCE.md` — proposed gated sequence and test plan.** Verify issues on current main; mock before changing core behavior; deliver in stages.
4. **`RECONCILIATION_FOR_DEVELOPER.md` — precise instructions for this repository.** Names the two older research folders actually present, the `docs/NEXT-SESSION.md` section that points to them, and what to leave untouched.
5. **`CURRENT_REPO_AUDIT.md` — evidence-based source check.** Which earlier recommendations still hold, which were already anticipated in the handoff, what is not yet implemented, and what remains unapproved.

## One-paragraph product direction

**Blooby is the social place; Skribl Pad records a drawing performance; Skribl Flip creates frame-based animation.** The distinguishing experience is **watch a drawing draw itself → Draw back → explore how artists' contributions evolve**. First stabilize the present app and refine that journey. Then make **independent, attributed Draw back contributions** a foundational architecture investment for lineage and family trees. Deliberately design the reusable compositing/timing/persistence layer so Pad editable layers can follow and Flip animation layers can follow later, without forcing full editing layers into the first Draw back release. Protect Pad's timed stroke-by-stroke replay; **do not add conventional instant bucket Fill to Pad**. Fill remains in Flip.

## Important reconciliation rule

The rechecked upload contains the two earliest reviews extracted under `docs/research/` and a new **“owner’s two reviews”** section in `docs/NEXT-SESSION.md`. Compared with the prior uploaded ZIP, `DECISIONS.md`, `FUTURE.md`, `START-HERE.md` and the application code have **not** changed. The new handoff explicitly treats those reviews as **data, not instructions**, while the **Draw back as layers** proposal is **mock-first and not yet implemented or schema-approved**.

**Do not bulk-replace canonical files.** The developer should replace the two older *research-review inputs* and update the associated handoff pointer, but preserve prior decisions, the existing handoff's bug reports and unresolved owner questions, and all working agreements. Source files may have changed after this upload; verify main before acting.

## Explicitly not included

- No old ZIPs inside this ZIP, no competitor branding or links, and no duplicate earlier full reports.
- No application code modifications, migrations, approved UI mocks, or claims that a current CI run passes/fails.
- No independent benchmarking or new hands-on use of a live deployed app. The new audit compares the two supplied repository ZIPs and inspects files, not running the application.
