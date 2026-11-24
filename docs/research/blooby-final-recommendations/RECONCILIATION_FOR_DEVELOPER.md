# Reconciliation Instructions — Replace Prior Analysis, Not Project History

## Goal

**Verified against the user-uploaded current repository ZIP:** the application's version remains v330. Relative to the prior ZIP, only seven review files were added in two research folders and `docs/NEXT-SESSION.md` changed; `DECISIONS.md`, `FUTURE.md`, `START-HERE.md` and runtime code are byte-identical. See `CURRENT_REPO_AUDIT.md` for details. This is not proof of the state of a later live checkout.

The owner has already added the first two recommendation reviews as repository research and linked them in the handoff; further changes to canonical decision/future records are not present in this uploaded snapshot. This package is the **final synthesized external recommendation** and should replace the earlier *ChatGPT recommendation set* as an input to planning. It is **not** a request to replace `DECISIONS.md`, `FUTURE.md`, or existing code wholesale.

## Supersession matrix

| Earlier recommendation / emphasis | Final canonical direction |
|---|---|
| Add Fill to Pad because Another App has it | **Withdraw.** Conventional Fill belongs in Flip. Pad replay must remain visibly stroke-based. |
| Layers are the top immediate paint-editor gap | **Reframe.** Independent author contributions are the core layer investment; paint/editor layers follow deliberately. |
| Defer all layers until users ask for painting layers | **Superseded.** The owner's purpose for layers is Draw back authorship, ownership boundaries and family trees. This is a core priority. |
| Build Pad editor layers before Draw back | **Reordered.** Shared foundation → Draw back independent contributions → Pad editable layers → Flip layers. |
| Treat reference-based Draw back as a UI-only change | **Incomplete.** Design version refs, per-author data, timing, permission, deletion/moderation and legacy compatibility. |
| Add Select to Pad as a new feature | **Corrected.** Pad already has rectangular stroke-group selection in v330; consider lasso refinement later. |
| Rebuild onboarding/home/social systems | **Not recommended.** Refine paths already present and verify any unmet needs. |
| Compete on brushes, rich paint effects and parity | **Deprioritized.** Protect the differentiated draw-itself experience and collaboration. |
| Treat historical v330 bugs as currently open | **Corrected.** Reproduce on current main/device before opening or closing work. |
| Build complex family graph immediately | **Stage.** First root/parent/direct responses and contributor views; expand only after validation. |

## What to keep out of the active backlog unless separately approved

- Conventional Pad bucket Fill.
- Full editor-layer UI inside the first Draw back contribution rollout.
- Large paint-brush parity initiatives; advanced blur/halftone/filter features.
- Direct messages, algorithmic recommendation feed, competitive rankings.
- Animated mascot overlays covering canvas or a glossy redesign.
- Automatic conversion of legacy merged Draw backs without verified reconstruction rules.

## Required differences between product direction and approval

- **Owner-supported direction:** Preserve Pad replay; contribution separation is central to Draw back and family trees; design the foundation so Pad/Flip editable layers become easier later; fix verified bugs first.
- **Open owner decisions:** exact layer UI, published version policy, deletion behavior, permissions/rights, recolor semantics, music/photos, media size limits, depth limits and automatic legacy migration.
- **Research ideas, not commitments:** lasso, replay chapters, share teaser, weekly formal challenges, elaborate family tree graphics, persistent animation tracks.

## How to reconcile safely

**Repository-specific cleanup (not application work):**

1. The old review files live in `docs/research/blooby-vs-another-app/` and `docs/research/blooby-skribl-refined-review/`. The newer ZIP contains no separate checked-in copies of the later addendum/correction ZIPs. Replace the two earlier analysis folders with this **one** versioned research package under an agreed location such as `docs/research/blooby-final-recommendations/`; do not silently delete historical owner decisions.
2. Change the **“owner’s two reviews, Blooby and Another App”** part of `docs/NEXT-SESSION.md` to reference the new single package and note the resolved precedence: no Pad instant Fill, contribution layers first (mock-first), editable Pad layers later, Flip layers later. Preserve the rest of `NEXT-SESSION.md`, including actual bugs, work order and unresolved owner choices. Existing notes about the external product walk may remain as historic research, not as a mandatory active recommendation.
3. Keep `DECISIONS.md`, `FUTURE.md`, `START-HERE.md`, `WORKING-AGREEMENTS.md` and all application code intact unless a separate approved, verified change is needed. Do not rewrite the original Nov 23 Draw back layer proposal as though it were implemented.
4. Produce a small mapping of removed old research items → the corresponding final recommendation / explicit withdrawal. Ask the owner before changing priorities in a way that would displace separately approved work.

**General reconciliation process:**

1. Compare this package against **current** `DECISIONS.md`, `FUTURE.md`, `START-HERE.md`, `docs/NEXT-SESSION.md`, tickets, implementation and approved mocks.
2. Make a list of duplicated, outdated, contradicted or already completed material originating from the older recommendations.
3. Remove or mark superseded only outdated *advice*, preserving owner-approved decisions and their historical rationale. If a current decision disagrees with this new recommendation, **flag it for the owner** rather than quietly altering it.
4. Merge new accepted direction into existing documentation using the repository's usual terminology and organization. Link to `FINAL_RECOMMENDATION.md` or copy only its relevant conclusion rather than pasting all four files throughout the repo.
5. Keep a small change record: file/section changed, older recommendation retired, current approved decision retained, and any open decision left for the owner.
6. Do not edit runtime code solely because this ZIP exists. Mock-first, verify, then implement via normal owner gates.

## Ready-to-paste request to the developer

> Please treat the attached **Blooby + Skribl Final Recommendations — Repo Verified** ZIP as the **single external product-review input** that supersedes the older analysis. The uploaded repo currently has earlier reviews in `docs/research/blooby-vs-another-app/` and `docs/research/blooby-skribl-refined-review/`, referenced in the **“owner’s two reviews”** section of `docs/NEXT-SESSION.md`. Replace those review inputs with this package and update that reference, while preserving historical owner decisions and all unrelated handoff information. Compare against latest `DECISIONS.md`, `FUTURE.md`, `START-HERE.md`, `WORKING-AGREEMENTS.md`, code, tickets and CI before acting. Do not overwrite canonical docs wholesale. Identify only genuinely new or revised recommendations, retire duplicate/contradictory older analysis, and give me a concise proposed changeset and a list of questions that still need my approval. In particular: keep conventional Fill out of Pad; treat **independently authored Draw back contributions and family-tree lineage** as a core architecture priority; design reusable layer primitives so future Pad layers and later Flip layers are easier; and stabilize/retest existing defects before major implementation. **Mock the Draw back layer UX and resolve creator rights, source deletion and versioning before changing schemas.** Do not implement the roadmap until I approve the scoped mock and plan.

## Evidence and limitations

Original evidence rechecked against the **newer** uploaded v330 archive (no changes to runtime code between the two uploaded ZIPs):

- `README.md`: Pad, Flip, replay/player, v330 context.
- `DESIGN-DIRECTION.md`: “The art should look messy. The interface should be immaculate.” and the canvas-first UI direction.
- `FUTURE.md`: Pad performance vs Flip frames; layers as payload/player schema; storage backend; selection already shipped; animation background/Keep-under details.
- `docs/NEXT-SESSION.md`: historical text/touch/Help issues, Draw back banner and Nov 23 proposed mock for Draw backs as layers.
- `social/drawback.py`: current `join` approach; `social/models.py`: `hands_json`, `drawn_on_id`, existing post-level attribution and lineage.
- `skribl/static/lib/drawback.js`: source underlay and separately recorded responder strokes before publishing; `skribl/static/lib/strokelayers.js`: **alpha compositing, not editing layers**.
- `skribl/static/editor_draw.js`, `skribl/static/flip.js`: editor/animation differences (recheck on latest code).

This package is a product/design synthesis. It does not assert that defects remain in the current deployment, approve a new storage schema, resolve legal rights or verify current production settings.
