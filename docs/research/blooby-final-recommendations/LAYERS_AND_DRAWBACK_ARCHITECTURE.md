# Architectural Brief — Draw back Contributions and Reusable Layers

**Purpose:** Give the developer an explicit *direction and risk register* for a mock/prototype **that must be approved by the owner**. The newer repo handoff (`docs/NEXT-SESSION.md` lines around its “draw-backs as layers” section) independently proposes this direction but explicitly says it has not been decided. These are **conceptual boundaries, not a drop-in schema or authorization to migrate data.** Inspect current models, playback, validation and deployment before making any code change.


### Source reality checked in the newer repository

- `social/drawback.py` intentionally **joins copies of strokes** and retimes the ancestor overture at publishing. Nested responses already include the earlier contributors' copied strokes.
- `social/models.py` has `Post.is_drawback`, `drawn_on_id`, `drawn_on_owner_id` and `hands_json`; these are existing post/credit relationships, not individual persisted stroke-layer objects.
- `skribl/static/lib/drawback.js` has a **separate client-side underlay** with faint/full/hidden states while editing. That is not a substitute for server-side independent stored contributions.
- `skribl/static/lib/strokelayers.js` is **a translucent-stroke compositing toggle** shared across Pad/Flip, not an editable-layer implementation. Its current performance budget must not be interpreted as a budget for future authorship layers.
- The uploaded handoff's **mock-first gate** and owner decision on source deletion/reuse take precedence over any model described below. Do not treat this brief as approval to migrate posts.

## A. Verified baseline in uploaded v330

- `skribl/static/lib/drawback.js` sets up the original underlay while the responder draws new strokes independently.
- `social/drawback.py::join` writes a published drawing with original strokes first (up to about a three-second overture), then the response strokes; the stored output is combined rather than a reusable contribution graph.
- `social/drawback.py`/post `hands_json` retain contributor identity and duration information but are not the same thing as independent editable source layers.
- `skribl/static/editor_draw.js` already supports stroke-group selection; it is not a blank slate.
- `FUTURE.md` explicitly identifies layers as a payload-format and player compatibility problem, not merely a storage backend problem. It also distinguishes Pad's timed drawing performance from Flip's page/frame model.
- `docs/NEXT-SESSION.md` (Nov 23) already requests a **mock first** for reference-based Draw backs, along with unresolved deletion, recolor and player-size questions.

## B. Architectural invariant: three identities, not one

1. **Contribution identity:** an artist-authored, permission-bound unit of collaborative work, linked to a parent contribution/post and to an immutable source version or explicit source-freeze policy. This is the basis for provenance and the family tree.
2. **Editing-layer identity:** an artist-controlled subdivision within their *own contribution/document*, independent of whether it is a Draw back. A future Pad document may contain Rough and Ink layers; a Draw back might contain several such layers belonging only to its responder.
3. **Frame/animation identity:** Flip's pages/frames and future layer tracks. A layer within a frame, a persistent track, a page hold and a replayed stroke event are not automatically interchangeable.

**Never use a layer name or layer ID alone to establish edit permission.** Authorship, access and parent-child relationships are authoritative on the server.

## C. Minimal conceptual model — refine with existing schema

| Concept | Suggested responsibility | Risk to resolve |
|---|---|---|
| `Contribution` | Stable id, author, post, parent reference, source-version reference, own drawing data, created/publication metadata | Who can edit after publication; post vs revision identity |
| `Document` | Canvas size, paper/background/media policy, payload version, drawing mode | Canvas/media conflicts between ancestors |
| `EditingLayer` | Stable id, ordering, visibility, lock where appropriate, belongs to **one** authored contribution | Shared render vs author editable state; layer order changes |
| `StrokeGroup/Event` | Existing points/timing, optional layer identity for new formats, global event ordering | Cross-layer stroke interleaving; legacy point formats |
| `CompositionManifest` | Bounded ordered refs to ancestor versions + own contribution, selective-view configuration | Stale refs, cycles, private content, latency |
| `Render/Replay` | Resolve authorized refs; composite final appearance and replay meaningful timed operations | Player isolation and performance |
| `Preview/Cache` | Bounded cached flattened thumbnail and, if needed, assembled display stream | Invalidation, removal/privacy propagation |

This is not a request to invent all these tables. Use the smallest representation compatible with existing post/drawing models and validators.

## D. Playback semantics by mode

### Draw back

- At minimum, **original then response**, preserving each author's own stroke shapes and time semantics; optionally accelerate the source into the existing short overture.
- Support **composite**, **source only**, and **my contribution only** as viewer modes (design these as read-only view options, not mutable ownership changes).
- A chain with A → B → C resolves A and B as C's ancestry without C storing duplicate copies of A and B's full strokes.
- If A → B and A → C diverge, both links remain visible. No silent combining of siblings into a new copyrighted work.

### Pad editing layers (future)

- Maintain one **global chronological sequence of stroke events** even while the artist switches layers. Rough → Ink → Rough must replay in that order, not layer-by-layer.
- Layer visibility may affect final composition; specify whether the viewer sees hidden historical strokes during playback, and make a consistent rule for published vs editing visibility.
- Undo/redo, moving/duplicating strokes and selection must preserve original group boundaries and predictable replay.
- Keep conventional instant bucket Fill out of Pad.

### Flip layers (later)

- Frame/page layer visibility and render order operate within Flip's existing page sequence, holds, loops, onion skinning, Draw-on and Keep-under semantics.
- A **persistent track across frames** is a distinct later design: no implied automatic retiming or page duplication.
- Confirm how published animation composites, frame edits, imports/exports, video and GIF output represent layered content.

## E. Owner decisions needed BEFORE implementation

Mark each item **open until approved in the live repository**; the old notes explicitly leave some undecided:

1. **Deletion/moderation:** When an original becomes unavailable, do descendants show their *own strokes only* with source attribution/status, become unavailable, or retain an explicitly licensed snapshot? A previous suggestion favored own-strokes-only; **not an approved decision**.
2. **Publication versions:** Are published contributions immutable, edited through new revisions, or replaced in place? Children should reference a stable version and never silently change.
3. **Permissions inheritance:** Revoking future Draw back permission, making a post private, blocking someone, or reporting content must have defined effects on existing descendants and caches.
4. **Rights:** What permission does participation grant to display/composite an ancestor? What can a descendant export, copy, recolor, remix, or redistribute? Attribution is not the same as legal ownership.
5. **Recolor/edit controls:** A responder may edit their own strokes; changing a source artist's work should require a defined derivative/permission policy rather than a hidden modification.
6. **Source assets:** Define paper color, canvas dimensions, photo/background, music, copyrighted imported media, and timing/size restrictions when composing contributions. Current Draw back eligibility has limits; do not silently expand them.
7. **Depth limits and cost:** How many generations can a browser/player compose directly, what gets cached, and how is fallback handled when an ancestor is unavailable?
8. **Legacy strategy:** Keep historic joined Draw backs working by default. Determine separately whether/when any reliable migration is possible, including cases with ambiguous authored ownership.
9. **Layer visibility semantics:** Whether public published view matches saved visible layers, and whether hiding a layer in an editor affects what spectators can replay.

## F. Recommended prototyping sequence

**Prototype 0 — read-only compatibility fixture.** Load original v330 Pad, Flip, joined Draw back and media posts. Capture golden render/replay expectations; verify current CI and payload validators.

**Prototype 1 — A + B contribution data.** Save A's existing published source; save only B's new strokes as B-owned data referencing an immutable version of A. Render a combined view without copying A into B's own payload. Provide source-only/response-only views. Keep standard Draw back replay.

**Prototype 2 — branch and lineage.** A → B → C and A → D. Confirm identity, attribution, parent navigation and replay composition; ensure no ancestor copying and no cycles.

**Prototype 3 — production-surface loading.** Inline card, full player, Gallery, saved draft/reopen and export surfaces. Keep thumbnail/card cheap through bounded previews/caching. Don't pull full editor code to play.

**Prototype 4 — Pad reuse proof.** Add **two editing layers inside one authored document** behind a feature flag. Test Rough → Ink → Rough switching and its original chronological playback, select/move/undo, save/reopen, and share. This proves the layer primitives are actually reusable rather than mere social reference edges.

**Prototype 5 — Flip feasibility, later.** One frame with two layers, then a short multi-frame animation. Test page hold, loop, Keep under, onion skin and export before designing a persistent cross-frame track UI.

Do not ship every prototype together. Move each through mock → owner decision → implementation → focused validation → real-device feedback.

## G. Shared technical constraints and tests

- **Versioned payloads:** New layer references/fields are opt-in and readers retain a legacy path. Never silently mutate an old posted payload.
- **Validation/security:** Server rejects spoofed author IDs, inaccessible parent refs, cycles, excessive lineage depth, invalid point counts, media abuse, and actions crossing author permissions. Child authorization must not imply visibility into a private ancestor without an agreed policy.
- **Storage:** `skribl/storage.py` has inline, local and S3-compatible stores; confirm production backend and size policy before broader layered data. No assumption that external storage alone solves schema, replay, or player-limit constraints.
- **Player isolation:** Keep inline card/poster lightweight and avoid fetching all ancestor editor payloads by default. Use caching and bounded composition to preserve current isolation and bundle budgets (`harness/verify_inline.py`, `verify_player_isolation.py` where present).
- **Compatibility:** Old merged Draw backs must render and play exactly as prior to migration. The new lineage UI must be able to label legacy posts honestly when their original/response strokes cannot be independently recovered.
- **Accessibility:** Contribution views and family navigation require accessible names, focus order, keyboard access and reduced-motion/contrast review.
- **Failure paths:** Graceful display of unavailable source, corrupted branch, deleted contribution, timeout and unauthorized ancestor without revealing private content or trapping a loading indicator.

## H. Definition of architecture success

**One work can have several separately authored, independently replayable contributions; their links form an acyclic family; the shared picture can be rendered without flattening the underlying ownership; old content still works; and the same composition/timeline primitives demonstrably support a future multi-layer Pad drawing.**

This is the architectural objective. It does **not** require exposing a full paint-layer interface to users before Draw back is ready.
