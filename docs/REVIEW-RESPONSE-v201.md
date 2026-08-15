# Response to the v200 follow-up review

**Build: v201.** The reviewer's gate was F1–F5 resolved before "every blocker
is fixed" can be claimed; all five are fixed, plus F6–F10, the cache caveat,
and all six requested counterexample tests — each verified to FAIL against the
pristine v200 modules before restoring the fixes. The v200 architecture is
unchanged, per the reviewer's own instruction.

| Finding | Fix | Counterexample test |
| --- | --- | --- |
| F1 direct-registration session isolation | `record_once` installs the captured factory into the registering app; the module global now serves only no-app-context callers. | txcontract: two manual blueprints, two apps, two DBs — each post lands in its own DB (fails on v200: A's post landed in B). |
| F2 anonymous idempotency scope | Anonymous callers get NO idempotency (`_idempotency_hash` returns None without a viewer). Authenticated authors keep full replay. Anonymous retries fall back to v199 behaviour: a duplicate, not a disclosure. | apiedges: two anon clients, same key → distinct posts (v200 replayed the first poster's id). mediaauthz: same author replays; different author never. |
| F3 gzip cap parity | One `_request_limit()` used by `_bound_request` AND `_inflate_request`. | txcontract: <4 KB gzip expanding past `SKRIBL_MAX_REQUEST_BYTES=4096` refused (v200: 201). |
| F4 parser normalization | `is_data_url` strips; `put_data_url` strips + lowercases the MIME before `_EXT`; mapping still keyed on the original string. | mediaauthz: padded data URL externalises with no inline survivor; `Audio/X-WAV` → `.wav`, served `audio/wav` (v200: inline leftover / `.bin` octet-stream). |
| F5 limiter backend/HMAC config | `_rate_backend()` / `_rate_hmac_key()` resolve per call: app config > env, HMAC falls back to the app's `SECRET_KEY`. Empty-key hashing now refuses everywhere (v200 hashed with `""` outside the db backend). | Exercised via verify_review #13 + db-backend suites. |
| F6 cleanup strands reservation | Opportunistic cleanup strictly best-effort (rollback + swallow). | verify_review: injected cleanup failure still returns a releasable token. |
| F7 policy docs | INTEGRATION example uses `set_visibility_policy(policy, app=app)`. | — |
| F8 card key from URL | Card resolves through the post's OWN association rows by `url_for_key` equality — no URL parsing; non-deterministic store URLs fall back to the branded card, documented. | mediaauthz card checks (unchanged, still green). |
| F9 `.part` leak | Best-effort unlink on write/replace failure; stale-temp maintenance documented in INTEGRATION.md. | verify_storage: injected replace failure leaves no `*.part`. |
| F10 stale Alembic head | INTEGRATION.md says `b7e2f9a41c55`. | verify_docs file-reference checks. |
| Cache caveat | INTEGRATION.md: `public_media_cache=True` is incompatible with viewer-dependent DENIAL, not merely a revocation window. | — |

Also in v201: the transaction-ownership contract is **signed off** (marker
updated in INTEGRATION.md; promotion-forfeiture rule accepted as written); the
CSRF/auth **tripwire** (a configured `current_user_id` without `csrf` logs a
security warning — DECISIONS.md #2 becomes machinery, since #1/#2 stay
deliberately unflipped until authentication exists); and the Flip motion-guide
switch now lights up while guides are on (it toggled a class nothing styled;
pinned by computed style in verify_flipmotion).
