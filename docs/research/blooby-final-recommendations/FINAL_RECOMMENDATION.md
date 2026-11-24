# Blooby + Skribl — Final Product Recommendation

**Single definitive recommendation for repository analysis — November 24, 2026.**  
**Basis:** consolidation of four previous review/correction packages, the owner's design clarifications, the subsequent shared-layer discussion, and verification against the newer owner-uploaded repository ZIP (still v330, with the first two reviews incorporated as research). **This is advice, not a declaration that an unimplemented feature has shipped.**

## 1. Executive conclusion

**Do not try to win by becoming a larger painting program. Win by making the creation and collaboration process uniquely watchable.**

The product already contains substantial drawing, animation, replay, music/export, sharing, mobile, social and help foundations. The largest near-term opportunity is not quantity of tools; it is the quality and continuity of the user journey. The most important long-term investment is **independently authored Draw back contributions, with a family tree and a reusable layer architecture**.

**The intended creative loop:**

1. **Watch:** Discover that a drawing can draw itself, then enjoy its timed replay.
2. **Draw back:** Add a response as its own creative work, without gaining control of the source artist's work.
3. **Explore:** View the shared picture, identify each artist, optionally isolate and replay contributions, and follow the parent/child branch of the idea.
4. **Return:** Find the original and the other responses easily; receive meaningful activity from real collaboration.

**Product roles:** Blooby = place/community; Skribl = what people create; **Pad = recorded drawing performance**; **Flip = frame-by-frame animation**. These differences are intentional. Avoid merging Pad and Flip into a single feature-heavy editor.

## 2. Priority calls — one source of truth

| Order | Recommendation | Status / gate | Reason |
|---|---|---|---|
| **Now, first** | Verify and close current interaction/reliability problems, especially touch/text, help navigation and obstructed Draw back canvas | Reported in v330 handoff; **reproduce on latest main/device before treating as open** | Trustworthy drawing is foundational |
| **Now, alongside fixes** | Refine the playback end → Draw back entry → return/explore journey | Small owner-approved UI mocks and 5 uncoached user sessions | Improves engagement without expensive schema work |
| **Next foundational architecture (owner-backed direction, mock-first)** | Model each Draw back as a distinct authored contribution referencing a stable ancestor/version, then compose/replay linked contributions | **Core strategic priority**; mock and resolve rights/deletion/version rules before build | Enables reliable family trees, authorship and independent contributions |
| **Next after foundation** | Expose a simple family-tree view and per-contributor views/replay | First parent and direct children; no sprawling graph UI initially | Makes creative lineage discoverable |
| **Planned extension** | Add **editable layers in Pad** on shared layer-aware primitives | Deliberate second-stage project, after stability and Draw back foundation; prototype replay first | Meaningful creative value with no duplicate engine |
| **Later extension** | Add **layers in Flip**, initially simple layers per frame, possibly persistent tracks across frames | Separate animation design, capacity and UI gate | Animation complexity exceeds Pad's |
| **Iterative enhancements** | Gallery discovery of Draw-back-ready art, small community prompts, better share/replay teaser, optional replay chapters | Evidence-gated; after core journey works | Converts spectators to returning creators |

**Parallelism:** Product/design exploration of the contribution architecture may begin while bugs are fixed. Do not merge a breaking payload-format change or launch new editor layer UI before the reliability, mock-first and compatibility gates are met.

## 3. Keep: important existing capabilities and decisions

The newer uploaded v330 source already supports timed replayable Pad strokes; Flip frames, holds, onion skinning, looping and animation-related controls; music/video/GIF/image sharing; drafts and public/restricted publishing paths; and substantial social foundations (profiles, follows, likes, comments, reposts, bookmarks, mentions, notifications, moderation). It also has a developed help/onboarding system and an existing Draw back workflow. **Improve, do not rebuild these systems.** Some details may have changed since the upload.

Specific protections:

- **Pad must remain a stroke-by-stroke recorded performance.** Preserve ordering, timing and the experience of the work drawing itself.
- **Conventional instant bucket Fill remains in Flip, not Pad.** The earlier Fill-in-Pad suggestion is **withdrawn**. Progressive color drawn as meaningful strokes is only a possible research idea, not a planned feature.
- **Do not remove current selection tools.** Pad already has rectangular, stroke-group-oriented selection; a lasso would be a *refinement* to that, not bringing selection to Pad for the first time. Keep selections stroke-aware to avoid severing lines and replay artifacts.
- **Do not force painting-layer UI into Draw back** to get authorship separation. Contributions can be independent without exposing arbitrary layer controls to every user.
- Preserve the project's minimal, canvas-first interface and its mock-first/verification practices. A working demo should still feel simple.

## 4. Fix the current user experience before expanding the editor

**Reported in the current uploaded handoff, still to recheck on live main/devices** (the handoff is evidence of outstanding work as of its writing, not a live reproduction):

1. On iPhone embedded Pad, text/keyboard/viewports can move unexpectedly; text input should remain stable and readable.
2. Touch dragging of text is unreliable or teleports the object; actual touch gestures and final positions must be checked on real devices.
3. The desired desktop text-placement rule needs explicit owner confirmation (placed text should not move from an unrelated click unless that is the approved behavior).
4. A desktop help carousel may be hard to reach without touch; add accessible mouse/keyboard affordances, not an untested new carousel.
5. Help closing should return people to the context from which they entered.
6. The “Drawing back on…”/“Theirs” pill can obscure drawable canvas space. Preserve faint/full/hidden source visibility but move persistent controls out of the art area; mock first.
7. The current uploaded `docs/NEXT-SESSION.md` says CI failed `verify_tools` V214b on an unpaired `touchend`/`touchcancel` in `textwrite.js`. Verify the latest CI state, reproduce the case and fix the missing cancel path if it remains; do not describe main as green without evidence.

**Done means:** every still-open defect is reproduced, resolved, regression-tested in relevant modes (standalone Pad/Flip and embedded Blooby where shared), and checked on real touch hardware. Avoid claiming a bug survives because it appears in an old handoff.

## 5. Refine replay and the Watch → Draw back → Explore journey

Make the playback experience legible, without intrusive banners:

- **Before playing:** a subtle accessible “Watch it draw” cue indicates that the drawing is interactive, not merely a thumbnail.
- **During:** prioritize canvas visibility, dependable scrub/speed behavior, music sync where applicable, and minimal controls.
- **When finished:** keep the completed drawing visible; make **Watch again** and, when permitted, **Draw back** easy to find; for an ineligible viewer provide a truthful reason or appropriate action.
- **Entering Draw back:** explain the branded term once using plain language (“Add to this drawing”), attribute the source artist, and keep the drawing surface unobstructed.
- **After posting or leaving:** provide a clear route to the source post, sibling responses and the new contribution. Don't strand users after a successful creation.
- **Discovery:** begin with a “Draw back ready” Gallery filter using existing eligibility/permissions. Add an exploration view for parent and immediate responses as the architecture permits.

Test the *complete journey* with five uncoached people across a phone and desktop. Ask them to draw, replay, respond to a public drawing, then return to the original. Record where they hesitate or abandon the task. Make small fixes before adding more feature depth. This is a proposed study, not a claim that one has been completed.

## 6. Treat Draw back contributions as independently authored creations

**This is the pivotal architectural recommendation and reflects the owner's latest clarification.**

Current v330: the client captures responder strokes separately over the source underlay; on publishing, `social/drawback.py::join` combines source and response into one drawing payload, compressing the source overture to about three seconds; `hands_json` keeps contributor identity/timing metadata. That renders a collaborative result but stores merged stroke content as a copy.

**Target:** Each contribution retains its own post, author, strokes, original timing, editing permissions and relationship to a specific stable version of its parent. A composed artwork is a *view of multiple authored contributions*, not a flattened replacement of their records. A Draw back of a Draw back creates a deeper chain without copying every prior ancestor's strokes into its own author data.

This enables:

- Parent and direct reply navigation; eventually a branch/family tree.
- Composite, original-only and contribution-only views, without changing the underlying work.
- Playback of each artist's actions individually or sequentially, retaining the existing compressed-overture option.
- Source attribution; constrained edit/recolor operations on one's own work; consistent permissions.
- Clear treatment of removed or moderated ancestors (the exact behavior must be chosen, **not assumed**).

**Important qualification:** Separate authorship in code is not by itself a determination of copyright, licenses, or legal ownership. Creator rights, reuse permission, publication edits and removals require explicit rules and where appropriate legal review.

The initial release should be **one original + one respondent**, with a mock and technical prototype. The second gate should show a respondent to a respondent, with correct ancestry and playback. Ship a simple parent/replies presentation before attempting complex graph navigation. Legacy merged posts must remain playable; automatic migrations should be a separate, explicitly approved decision.

See `LAYERS_AND_DRAWBACK_ARCHITECTURE.md` for the implementation boundaries and open questions.

## 7. Layers are a strategic foundation — but separate two concepts

**Earlier advice to defer *all layers* was wrong.** The current `skribl/static/lib/strokelayers.js` is a translucent-stroke compositor setting, **not** editable/independently authored layer support. The latest owner direction is to make contribution separation part of Draw back's core future, and to exploit the work as a reusable foundation for editing layers.

| Concept | Unit being separated | Who may edit it? | Goal |
|---|---|---|---|
| **Contribution layer/record** | One person's authored response in a collaborative chain | That contributor, under version/publishing rules | Provenance, ownership boundaries, selective replay, lineage |
| **Pad editing layer** | Rough/ink/details within one person's creation | That creator | Independent editing without breaking timed replay |
| **Flip animation layer** | Artwork within frames or a track over frames | That creator | Animation compositing and reuse of persistent elements |

They should **reuse a common layer-aware representation/compositor/timeline/persistence where practical**, rather than implementing three unrelated engines. They should **not** be conflated into one generic database entity or authorization rule merely because each can be called a “layer.”

A Draw back system built *only* as a parent reference plus a final-image compositor would not automatically make Pad layers easy. Therefore design reusable primitives upfront: identifiable stroke groups, per-contribution/per-layer data ownership, composition order, versioned save/reload, a global ordered stroke-event timeline for Pad, and render/playback surfaces able to resolve references without loading the full editor.

### Pad extension — after contribution foundation

- Start with two layers (e.g., Rough and Ink), not an unlimited stack. Visibility, ordering, optional lock and basic editing are enough to validate the model.
- Preserve the **global chronological stroke sequence**, including switches between layers. If strokes were drawn on Rough, then Ink, then Rough, replay must follow that *interleaved order*, not complete all of Rough first.
- Selection/undo/recolor must preserve layer membership and stroke integrity. Save, reopen, share, inline replay and export must agree on the result.
- Keep Fill out of Pad; layers don't change that design rule.

### Flip extension — later and separately scoped

- First validate simple layers **inside a frame**, continuing to respect Flip's page/hold/onion-skin/loop semantics and existing “Keep under” behavior; don't assume they are interchangeable.
- Then separately consider **persistent animation-layer tracks across frames** (e.g., a stationary body and independently animated arm). This needs its own timing and interaction design.
- The layer foundation can reduce shared rendering/schema work, but Flip UI, per-frame operations and animation timeline remain significant work.

**Recommended order:** stabilize → contribution layer/lineage foundation → simple family-tree and replay views → Pad editable layers → Flip editable/track layers. UI polish and research may continue alongside architecture without violating stability gates.

## 8. Identity and community: build a place artists return to

**Brand:** The original Blooby character works because he looks drawn *in the app*: same jelly-bean silhouette and purple, one pink cheek, black boots, original simple hand-drawn face. No beret/hair tuft/glossy replacement. Prepare restrained dark-background treatment while preserving his ink character. Prefer the peeking pose for small helpful moments. Use mascot for welcome, truly empty states and meaningful first milestones, **not** over the drawing canvas or everywhere in the feed.

**Onboarding:** The current uploaded home page already contains a Blooby animation, Make entry, Look around entry, guest drawing, and integrated help. Do not replace it with a giant onboarding wizard. Test where first-time visitors lose the thread and remove dead ends.

**Community:** Pilot one weekly Draw back prompt manually, using a featured post and the existing social mechanics. Only build formal challenges if participation is real. Surface contributions to less-visible artists rather than only ranking popularity. Keep follows, comments, bookmarks and Gallery—they are implemented foundations, not gaps requiring recreation.

**Sharing:** Existing links, rich preview cards, image/GIF/video export provide a base. Consider an optional short replay teaser and frictionless “Share drawing” path, so the distinctive draw-itself experience travels beyond Blooby. Keep artist attribution and privacy choices intact.

**Later, not critical path:** replay chapter markers (“outline,” “details”) explicitly set by creators, a replay-as-learning experience, optional drawing-description field for accessibility, and a stroke-aware freehand lasso if user testing identifies it as a meaningful need. More brushes, texture effects, advanced image editing, frame-sequence interchange and rich selection modes are exploratory, not launch blockers.

## 9. Launch, technical and safety guardrails

- **Compatibility first.** Maintain a versioned payload format. Historical Pad, Flip and merged Draw back data must load and play in every supported surface.
- **Authorship and access checks server-side.** Layer IDs and parent references cannot authorize editing other users' contributions, bypass blocks, or expose private ancestors.
- **Deletion/moderation must work across descendants.** Treat it as an explicit design and rights decision before backend implementation.
- **Storage and player budgets.** `skribl/storage.py` already implements inline, disk and S3-compatible paths; the v330 docs state deployment chooses a backend. Verify real deployment configuration before expanding payload size. Avoid forcing inline cards to download every ancestor or load editor code; protect inline-player isolation and bundle budgets.
- **Cycle, depth and malformed-data defenses.** Bound ancestry traversal and point counts. No branch should render forever or blow up a phone.
- **Accessibility and testing.** Focus/keyboard/touch semantics, contrast and reduced-motion behavior matter alongside tests of data correctness.
- **Public launch gates.** Maintain invite-only status until approved legal/safety/moderation requirements are satisfied; direct messaging and recommendation algorithms are not prerequisites.
- **Respect current architecture and owner process.** Mock first for interaction changes and major data/schema choices; no direct modifications implied by this recommendation.

## 10. How to measure whether improvements work

Proposed **aggregate** measures (not currently reported product data):

1. Visitors who start → successfully complete a first drawing.
2. Replay viewers who understand it can play → finish a watch.
3. Eligible replay viewers who start → complete Draw back.
4. People who make a contribution → find the original or another branch afterward.
5. Creators who return within seven days to draw or contribute.
6. Save/publish failures and unintended movements/obstructions reported during observed sessions.

Use anonymous journey data where possible; do not record private artwork/strokes just to calculate conversion. A/B-test wording/UI only after basic usability is stable.

## 11. Explicitly rejected or deferred suggestions

| Earlier suggestion | Final disposition |
|---|---|
| Add instant flood-fill to Pad | **WITHDRAWN.** Keep Fill in Flip; Pad stroke-performance identity is non-negotiable without a new owner decision. |
| Treat layers solely as paint-program convenience and defer them all | **SUPERSEDED.** Contribution layers are core architectural priority. |
| Ship full editable Pad/Flip layer UI as a prerequisite to Draw back | **REJECTED.** Reusable primitives first; editor UIs in staged follow-up work. |
| Make two Pad painting layers the immediate next sprint | **REORDERED.** Valuable later after stabilized Draw back contribution foundation. |
| Bring selection to Pad from zero | **CORRECTED.** Pad already has rectangular stroke-group selection in v330; improve it only when needed. |
| Copy another app's brush count, fill UX or unified editor | **NOT A GOAL.** Keep the intentionally distinct Pad/Flip design. |
| Rebuild the social network or onboarding | **NOT A GOAL.** Extend the existing foundations after confirming current code. |
| Full family-tree graph, recommendation algorithm, DMs, dozens of brushes | **DEFERRED.** No proven need ahead of the collaborative core. |

## 12. The definitive recommendation

**Prioritize polished reliability and a clear Watch → Draw back → Explore journey; treat separately authored, lineage-aware Draw back contributions as the next foundational architecture project; engineer its primitives so Pad layers and later Flip layers are natural extensions, not unrelated rewrites.** Do not sacrifice Pad's honest stroke-by-stroke replay. Use real-user testing to decide how much editor complexity to expose, not whether independently owned contributions matter.

A Blooby drawing should be not just a finished picture but a **traceable, watchable sequence of creative contributions**, each with an artist, a history and a place in the evolving artwork.
