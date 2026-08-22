# Response to the v201 developer review

**Build: v202.** All eight findings fixed (the reviewer's gate was F1–F5; F6–F8
came along), each behind the requested test. One bonus: the F1 counterexample
test exposed a latent SQLite bug none of the three reviews caught — pysqlite's
deferred BEGIN made our savepoints run in autocommit for transaction-initial
requests, so `RELEASE` silently committed with no commit ever issued. Fixed
with the canonical isolation_level=None + explicit-BEGIN recipe (installed per
engine beside the FK pragma), which in turn required moving ALL post-slot
bookkeeping (promote AND release) into blueprint teardown — after the host
transaction closes — since two real writers cannot share one SQLite file
mid-request. Teardown promotion failure degrades to a pending row that ages
out via TTL: quota leaks only downward, briefly, only while the limiter's own
store is failing.

| Finding | Fix | Test |
| --- | --- | --- |
| F1 teardown-commit contract | Docs narrowed to commit-before-response (`after_request`); teardown commit declared OUT OF CONTRACT — and now load-bearing, since teardown is where slot bookkeeping resolves. | txcontract: teardown-commit host demonstrated (client 201, nothing durable) |
| F2 memory limiter cross-app | Buckets+lock in app.extensions; module dict is the no-app-context fallback. | mediaauthz: same IP exhausts A, B untouched |
| F3 bytes SECRET_KEY | `_rate_key` normalizes str/bytes, rejects other types plainly. | mediaauthz: bytes secret hashes |
| F4 key names a request | `request_fingerprint` column (migration d3f8b12c9a67); same key+same body replays, different body 409s, concurrent path same rule; editor mints a fresh key when the body changes. | mediaauthz: 409 on reuse, original still replays |
| F5 value-equality rewrite | Externalisation writes only walker-classified paths (label grammar pinned; unknown label raises). | mediaauthz: equal non-media string untouched |
| F6 session=False fail-closed | NO_SESSION sentinel recorded by both registration paths; a query raises instead of borrowing the global binding. | mediaauthz: 5xx, never another app's DB |
| F7 trusted proxies | `_trusted_proxies()`: app config > env, like caps/backend/HMAC. | — |
| F8 review-response pointers | README/HANDOFF point at docs/REVIEW-RESPONSE-v201.md (current); root file labelled historical. | verify_docs reference checks |

Accepted residuals unchanged from the reviewer's own list (anonymous duplicate
risk, cache opt-in constraints, mp4 skip, container-level media checks, feed
policy seam).
