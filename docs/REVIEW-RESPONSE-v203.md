# Response to the v202 developer review

**Build: v203.** Both blockers and all findings fixed; every claim in this
response has a test that exercises the DB backend where the finding demanded
it ("backend equivalence matters" — taken).

| Finding | Fix | Test (all in verify_txcontract, DB backend + SQLite) |
| --- | --- | --- |
| F1 (P0) bookkeeping vs teardown ordering | The mechanism is bounded-failure, not divination: introspecting the host session under autobegin is guesswork, so the limiter's SQLite sessions carry a 200 ms busy_timeout (limiter connections only — the host engine untouched) and a collision with the host's still-open transaction resolves in milliseconds as a contained, logged exception leaving the row pending for RATE_PENDING_TTL. Flask's blueprint-before-app teardown ordering was confirmed empirically first. | Injected host after_request commit failure with the DB limiter on SQLite: 5xx, nothing durable, no hang (<4 s asserted, ~0.2 s actual), reservation pending-or-removed, next request unblocked. |
| F2 (P1) teardown exceptions escape | _finish_parked_reservation contains ALL limiter exceptions (logged with the token), so the documented "degrades to pending TTL" is now the implemented behaviour; committed posts stay successes, original exceptions are never masked. | Injected promotion failure → request stays 201; injected release failure during a 400 → still 400. |
| F3 (P1) engine-wide SQLite transaction takeover | Documented prominently in INTEGRATION.md ("SQLite transaction mode"); isolation_level="AUTOCOMMIT" engines are refused loudly at startup; a pre-existing host BEGIN recipe coexists (the recognised double-BEGIN shape is tolerated, anything else raises). | Host with its own connect/BEGIN listeners posts successfully. |
| F4 (P2) stale ordering comments | _db_rate_commit_post now carries the authoritative teardown-ordering story matching routes.py. | — |
| F5 (P2) START-HERE stale identity | Primer retitled to the current build, stale v191/6-revision facts corrected, historical narration fenced as historical. | verify_docs |

Accepted residuals: pending rows from contained failures under-count quota for
at most RATE_PENDING_TTL, observable in logs; everything from the v201/v202
residual lists carries forward unchanged.

## Amendment (A1/A2) — client defects, same reseal

| Finding | Fix | Note |
| --- | --- | --- |
| A1 iOS silent music | Late-decode hook starts the loop at the drawing's current elapsed when the buffer arrives mid-playback; `audioCtx.resume()` is awaited and audio start gated on the resolved promise; silent catches now log. | **⚑ OWNER DECISION: player-JS ratchet raised 141,730 → 142,160** for the fix's 430 functional bytes (golfed first). Approve or direct a compensating cut. |
| A2 vanishing canvas frame ≤~461px | `--canvas-ring` is now an INSET shadow: paints inside the border box (unclippable at the container edge), zero layout change, survives every state rule that swaps `box-shadow` wholesale since all re-include the variable. player.css re-emitted via cssgraph. | Simpler than the suggested `::after`; same guarantee, fewer moving parts. |

Untested on real hardware, as the amendment itself notes: both fixes verified
in headless Chromium; the iPhone-Safari behaviours (decode latency, resume
semantics) still need the five minutes on a physical device already standing
in the pre-live-flip flags.
