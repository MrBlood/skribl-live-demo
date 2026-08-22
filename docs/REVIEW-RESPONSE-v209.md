# v209 — the two open v207 findings closed (F2 + F3)

v208 closed F1 and F4 and left F2 and F3 open for the two reasons a fix pass
cannot supply: a product-contract decision and a physical iPhone. The owner has
now made the F2 decision — **option (a): a failed post must not cost quota** —
and F3 was never blocked on anything but care. Both are closed here. The iPhone
check on F3 remains, and is the only thing still owed on it.

## F2 — P1 — a failed SQLite DB-backed POST could hold quota until pending-TTL → CLOSED

**The finding was right, and reading the tree narrowed it usefully.** The
failure path already RELEASES the slot: `routes._finish_parked_reservation`
calls `_rate_release_post`, which deletes the pending row. What fails is the
DELIVERY of that delete. Flask runs blueprint teardowns before app teardowns,
so when the host's commit fails its rollback has not run and it still holds
SQLite's single write lock; the limiter's bounded `busy_timeout` turns the
collision into a fast `OperationalError`, teardown logs it, and the row stays
`pending` — counting until `RATE_PENDING_TTL`. So option (b) would not have
been "documenting the design we chose"; it would have been downgrading a
guarantee the code was already reaching for.

**Why not simply retry the write.** It is failing precisely because another
writer holds the file, so a second attempt is the same coin flip and cannot
make immediate retry *mechanically* true — which is the contract chosen. The
release is therefore recorded where no writer is needed: a process-local
tombstone. `_db_rate_count()` subtracts tombstoned ids immediately, and the row
itself is deleted by the next request that can get a writer
(`_sweep_tombstones`), so the store is a deferral, not a shadow ledger.

**Scope, stated rather than implied.** Immediate retry is mechanically true
*within the process that took the reservation* — the same scope
`_rate_reserve_post` already claims (internally correct single-process,
explicitly not distributed, #13). With several workers on one SQLite file
another worker still counts the row until it is swept or ages out: exactly the
v208 behaviour, never worse, better in the single-process case that is the
SQLite deployment.

**Regression** (`verify_txcontract`, +10, suite now 44): the reviewer's
sequence at `SKRIBL_RATE_MAX_POSTS=1`, with the collision REAL rather than
mocked — a second connection holds `BEGIN IMMEDIATE` across teardown. The
evidence that it is the real path: the release failed in 0.22 s (the 200 ms
`busy_timeout` firing), and the row was still physically present afterwards.
The immediate retry returns 201. The **counterexample** drops the in-memory
record before the retry, reproducing v208 exactly, and gets 429 — so the
contract check can go red.

**One hazard found while building it, pinned:** `RateEvent.id` is a plain
INTEGER PRIMARY KEY, i.e. SQLite's rowid, and SQLite REUSES rowids. An id-keyed
tombstone whose row had been deleted by somebody else could silently exempt an
innocent reservation. It cannot happen today because a tombstoned row has
exactly one deleter — the sweep, which drops the tombstone in the same breath.
That invariant is now written in `ratelimit.py` and pinned in the suite,
because whoever adds the next deleter of pending rows will read the test file.

## F3 — P1 — Pad replay's fire-and-forget Web Audio unlock → CLOSED (pending iPhone)

**Exactly as reported.** `startWebAudioLoop()` called `audioCtx.resume()` and
threw the Promise away, and Pad's Play reaches it from INSIDE
`clearAndRestore`'s `Image.onload` callback — after the click gesture has
returned. The same class the v203 player fix (A1) closed for the player; the
editor replay never got it.

**Fixed on the A1 template.** `unlockWebAudio()` is called from the Play
handler, synchronously, inside the gesture; the promise is retained; the loop
source starts only once it resolves. A generation counter stops a late start
overtaking a stop, and the failure path warns rather than swallowing. The
drawing does not wait — as in A1, only the audio start is gated.

**Regression** (`verify_ux`, +5, suite now 269): not a source pin — the whole
bug was code that looked right and ran late. The real button is clicked and
the ORDER is instrumented. The page is made to behave like iOS (state reports
`suspended` until a `resume()` promise resolves) because headless Chromium
starts contexts running, and `HTMLImageElement.complete` is forced false so
`clearAndRestore`'s decoded-base cache cannot turn Play synchronous and hide
the bug. Observed order: `resume` → `gesture-returned` → `base-image-painted`
→ `loop-started:running`.

**Mutation-tested.** Removing the gesture-time unlock moves `resume` to after
`base-image-painted` and turns the two ordering pins red, leaving the other
three green — the v208 shape, reproduced on demand.

**Still owed: a real iPhone.** The ordering pins are what carry the iOS claim;
the harness's simulated context will happily unlock late, which a phone will
not. This is the last iPhone item.

## ⚑ Owner: player-JS ratchet 142,370 → 142,880 (+510 B)

For the F3 unlock. Golfed from 623 B. Same category as the four prior raises
and, specifically, the same FIX as A1 (+430 B, approved) applied to the editor
replay A1 missed.

**The cheaper answer, measured, for the next pass:** the whole Web Audio loop
block is ~2,060 code bytes and is EDITOR-ONLY — `startWebAudioLoop`,
`playMusicLooped` and `startLoopPreview` are reached from the Play button and
the music drawer, never from the player, which has its own `pa*` audio path.
Externalising it the way `editor_tune.js` went would cut roughly four times
this raise. Deliberately not done in the same pass as an audio fix: a silent
replay must stay attributable to one change. Watch `stopWebAudioLoop` — 8 call
sites, several on teardown paths.

## Unchanged from v208

The phone-audit claim stays NARROWED (right-edge + same-row horizontal);
widening it is still queued as optional. DECISIONS.md #1 and #2 stay unflipped
until authentication exists. S3Store still has never run against a real bucket.
