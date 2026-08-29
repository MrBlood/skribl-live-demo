# v235 — the pill that would not go away

> "The saving still stays too."

Two separate causes, one symptom. The 12-second spill deadline shipped in v233
fixed the first; the second was a mistake I introduced in v229 and had not
noticed.

## A pending media record is a memo, not a property of this save

v229 changed Flip's autosave so amber means a real failure. It also made the
no-media path report amber whenever `pendingPhotoMeta` existed:

```js
showAutosaveStatus((pendingPhotoMeta || pendingMusicMeta) ? 'saved-no-media' : 'saved');
```

Reaching that line means `hasMedia` is **false** — no photo, no track. The save
omitted **nothing**, so "Saved without media" described something that did not
happen. The record is a memo about a *past* loss, kept so the same image can be
re-added with its settings intact.

Three things made it permanent rather than merely wrong:

- `serializeFlip` round-trips it (`photo: pendingPhotoMeta` when `bgImage` is
  null), so a reload brings it straight back.
- The only control that clears it lives in a drawer and measures **0×0** until
  that drawer is opened.
- Warnings deliberately never fade.

A warning with no reachable resolution, on a drawing with no media in it. That
is how a user learns to ignore the colour amber — which is the real cost, since
the same colour has to carry a genuine "your bytes are gone".

**The real warning is untouched:** media attached and its bytes failing still
raises amber and still keeps it up. Mutation-tested both ways.

## What v233's deadline actually fixed

Verified separately, because the two were easy to confuse. With a `put()` that
never settles — iOS Safari's failure mode — the pill reads "Saving…" while the
write is genuinely pending, and flips to "Saved without media" once the deadline
passes. It no longer sits there for the session.

## Testing

`verify_drafts` 24 → 28. Both fixes mutation-tested: restoring the v229
expression fails the past-loss check, and removing the deadline leaves the pill
on "Saving…" and fails the other.

One test bug fixed along the way: the new section used `DRAW_STROKE`, which
targets **Pad's** `#canvas`, so on Flip it drew nothing, scheduled no save, and
reported whatever the pill happened to show. It passed as "Saving…" and proved
nothing.

## Still open

The pending-media card is still invisible until its drawer is opened, so a photo
that genuinely failed to save offers no visible route to re-adding it. Making
that reachable is a UI question rather than a correctness one, and it is
unbuilt.
