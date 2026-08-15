# Response to the outside developer review of v199

**Build: v200.** Every blocker in RELEASE-BLOCKERS.md is fixed, each behind a
suite that fails on the v199 code, mutation-tested. The postgres skip is
CLOSED for the first time — `verify_postgres.py` ran against a live cluster
in this reseal.

Every claim was verified against the tree before fixing (the reviewer had no
Flask in their environment); all of them held.

## Blockers

| Finding | Status | Failing-on-old suite |
| --- | --- | --- |
| P0 transaction ownership | **Fixed.** Routes flush + savepoints, never commit/rollback the shared session; db limiter on its own app-local sessionmaker; app.py owns the per-request commit. Contract in docs/INTEGRATION.md — **⚑ pending your sign-off**. | verify_txcontract (9), verify_review updated |
| P0 media authorization | **Fixed.** `/media/<key>` asks `visible_to` like payload/card/player — host policies honoured in the grant AND revoke directions. | verify_mediaauthz (28) |
| P0 cache authorization | **Fixed.** Default `private, no-store` for anything authorisation-dependent; `public(+immutable)` only behind `public_media_cache=True` / `SKRIBL_PUBLIC_MEDIA_CACHE=1`. | verify_mediaauthz; verify_storage/verify_s3 now pin the opted-in side |
| P0-adjacent fake-bust DoS | **Fixed.** `?v=` honoured only when it equals the file's real content bust; strip/gzip caches app-local. | verify_assetcache (12) |
| P1 request cap | **Fixed.** Blueprint enforces its own bound (25 MB default, `SKRIBL_MAX_REQUEST_BYTES`) where the host set none; 411 for undeclared mutating bodies; gzip expansion cap unchanged. | verify_txcontract |
| P1 baseSnapshot | **Fixed.** In `_iter_media_items` root and per-frame: validated, capped (MAX_IMAGE_BYTES), externalised. | verify_apiedges, verify_mediaauthz |
| P1 idempotency | **Fixed.** `Idempotency-Key` header; author-scoped `skribl_idempotency` table riding the post's transaction; editors send a per-attempt key held until confirmed success. Migration a9d4c31e7b02. | verify_apiedges |
| P1 per-app isolation | **Fixed.** Visibility policy and rate budgets resolvable per app (`set_visibility_policy(fn, app=...)`, `app.config["SKRIBL_RATE_MAX_*"]`), joining the already-app-local session/csrf/store seams. Memory-limiter *counters* remain per-process by that backend's nature. | verify_mediaauthz |
| MIME parity | **Fixed.** All 20 accepted spellings map (`flac/x-flac/opus/m4a/x-m4a/vnd.wave/image-jpg` added); pinned structurally so a new accepted type without a mapping fails on arrival. | verify_mimeparity (26) |
| Orphan sweep | **Fixed.** Only KEY_RE-shaped keys at canonical paths are candidates (a co-tenant's prefix or a stray file is never ours to reclaim); reference checks chunked, memory O(500). | verify_deletion_foundation, verify_storage |
| Timezone datetimes | **Fixed.** `DateTime(timezone=True)` + migration b7e2f9a41c55 (TIMESTAMPTZ on postgres, `AT TIME ZONE 'UTC'`); `as_utc()` labels SQLite's naive round-trips; `createdAt` wire format pinned. | verify_apiedges, verify_migrations |
| Collision retry boundary | **Fixed.** Only `public_id` violations retry; idempotency-key collisions resolve to the winner; anything else raises as itself. | (exercised via verify_apiedges) |
| Externalised share card | **Fixed.** Card resolves a stored-URL thumbnail back through the store under the same visibility check and size cap. | verify_mediaauthz |
| Backfill `limit` | **Fixed.** Caps scanned posts exactly; the fetch never asks past the allowance. | verify_backfill |

## Also in this reseal

* **Drawer controller extraction** (carried over): the exclusive-open machine
  is `lib/drawers.js`, both editors rewired onto it; Flip's eight hand-rolled
  functions collapse to three thin wrappers. Gated by
  visual/parity/cssplit/ux; player JS ratchet LOWERED to 141,730 after the
  net reduction.
* `_collapse_whitespace` in jsstrip: player JS reached the 153,600 target
  (11.5 KB under), asserted so regressions are loud.
* Empty-frames + fps validation with `verify_apiedges.py` (32 pins,
  mutation-tested: reverting the validation block fails exactly 7).
* `verify_docs.py` now requires every suite on disk to be named in a .md.

## Decisions that are yours, surfaced here

1. **Transaction ownership contract** (docs/INTEGRATION.md §Transaction
   ownership) — written, flagged, awaiting sign-off.
2. **DECISIONS.md #1 and #2** — visibility default `'unlisted'` and CSRF
   default off. Both flip polarity once a host authenticates posts: an
   authenticated deployment likely wants `private`-by-default and CSRF on.
   The authz work made no change to either default; say the word and both are
   one-line flips plus suite updates.
3. **Not yet exercised against real infrastructure:** S3Store has never run
   against a real bucket or MinIO (the suite's fake verifies signatures;
   Amazon acceptance is unproven), and the Pad stylus path needs five minutes
   on a real iPad. Both before the media backend flips on live data.
