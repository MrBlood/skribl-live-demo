# Architecture clarification: Why conventional Fill does not belong in Skribl Pad

**Status:** Owner clarification supersedes the Pad Fill recommendation in the review.

## Product principle

**Skribl Pad is a stroke-by-stroke performance.** Its distinctive promise is that a drawing visibly draws itself when replayed. An ordinary flood-fill command can make a complete region of color appear instantaneously, which breaks that visual grammar and turns the replay into a mixture of continuous strokes and sudden whole-area changes.

**Skribl Flip is an animation editor.** Its Fill tool is appropriate because Flip's purpose is to construct and animate frames, not necessarily to reconstruct the literal physical process of every stroke of color.

These are different creative modes on purpose. We should protect that difference rather than force feature parity between them.

## Corrected recommendation

1. **Do not add conventional bucket Fill to Pad's default toolbar or near-term roadmap.** Treat the earlier suggestion as withdrawn.
2. **Keep Fill in Flip.** Avoid moving it just because a competitor offers it in a unified editor.
3. **Preserve stroke-only replay as Pad's default design constraint.** Any future coloring enhancement must be evaluated for what the viewer actually sees during playback—not just whether the final image looks right.
4. **Prioritize improvements that strengthen Pad's existing model:** reliable text/stroke interaction, responsive drawing controls, stroke-aware lasso, robust replay compatibility, and possibly independently editable sketch/ink layers if they can retain visible stroke progression.
5. **If a coloring feature is explored later, prototype it as visibly drawn color**, such as a recorded broad marker stroke or intentional progressive hatching. This is an idea to test, **not** a feature request or commitment. It should not silently replace a large region with a static bitmap.

## Technical acceptance questions for any replay-related change

- Does playback still show the actual meaningful drawing actions in sequence?
- Are new operations represented in versioned data and backward-compatible with older drawings?
- Can the user undo and redo the operation without changing replay semantics?
- Does the posted replay look the same as the editor result, including on mobile?
- Does an operation unexpectedly cause a large image region to pop into existence?
- Are Pad and Flip deliberately different where their models require it?

## Revised Release B scope

**Keep:** two-layer replay-compatible prototype (only if it preserves stroke timing), freehand stroke-aware lasso, simpler tool access, resilient save/reopen/replay.

**Do not include:** flood-fill for Pad.

**Retain:** conventional Fill in Flip.

## Decision to keep in repo discussions

The objective is **not** to turn Skribl Pad into a conventional paint application. The objective is to make the act of drawing easy, expressive, dependable, and enjoyable to replay. Different limitations may be part of the product identity rather than missing features.
