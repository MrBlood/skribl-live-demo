# v224 — what changed since the sealed v223

**Evidence status: SEALED.** `harness/RELEASE.md` is generated from a full
aggregate run against this tree, and states the result, the assertion count, the
suites reporting and anything skipped. Read it there — the tree hash and the
counts are computed, not typed, and restating them here is how a number goes
stale one release later while still sounding authoritative.

This release is a response to an outside review of the sealed v223 archive. All
eight numbered findings and all three low-severity items are implemented, each
with a regression suite. Nothing was deferred.

## Narrative

**The eight findings share one shape, and it is worth naming before the list.**
Every one of them is *a claim stated in two places, where only one of them could
enforce anything.* The documentation said a host could add a visibility state
without a migration; the create endpoint rejected every one of them. The
documentation said `sweep_orphans` reclaimed orphaned media; nothing shipped
could run it. Three files stated the caption limit and no two agreed. The media
validator's own comment promised that dimensions were a "deliberate follow-up",
and the follow-up had not happened.

That is the same failure the v223 release turned on — `RELEASE.md` describing a
64-suite tree because the process that regenerates it had silently stopped being
run — and it generalises: **when the same fact appears in N places, N-1 of them
are documentation of the other one, and only the one that can refuse is real.**
(DECISIONS.md v247.)

**Media had a cap on bytes, which is not a cap on cost.** The container checks
proved the declared subtype matched the leading bytes and the base64 was under a
size cap. Neither says anything about decoding. A 66-byte PNG whose IHDR
declares 30000x30000 passed everything, and every browser that opened the post
then allocated about 3.6 GB for it — bytes cannot be a proxy for decode cost,
because the whole point of a bomb is that it is small. Dimensions sit in the
header of all four accepted formats, so they read without a decoder and without
a new dependency: fixed-offset parsers for PNG/GIF/WebP (all three sub-formats)
and a bounded segment walk for JPEG. WAV duration comes from the byte rate its
`fmt ` chunk states outright.

Two choices inside that are deliberate and documented in the code rather than
implied. **An unparseable header is ACCEPTED** — a file that will not parse does
not decode either, and rejecting on "unparseable" turns every rare corner of
these formats into a 400 for no gain. And **compressed-audio duration is still
bounded only by bytes**; deriving it needs a real decoder, so a 12 MB Opus file
can be an hour long and is accepted by design. Saying so is the point: the
previous comment's honesty about what it did *not* check is what made this
finding findable.

**The orphan sweep was a maintenance plan, not a job.** `sweep_orphans` has
reclaimed disk since v180 and every document described it as the answer to
orphaned media. Nothing shipped could invoke it, so each deployment had to
resolve its own app, find the store the host passed in, get a session, and get
the argument order right on a function whose third positional argument deletes
user data. It was also unobservable — a run that removed nothing looked
identical whether there was nothing to reclaim, the credentials were pointed at
the wrong prefix, or the grace period was swallowing everything — and fragile:
`delete_key` ran uncaught, so one object a bucket policy refuses aborted the run
and left every later orphan in place, *while the key was already in the returned
list*, reporting a deletion that never happened.

`python -m skribl.sweep` is the entry point, dry by default with `--delete`
spelled out in full and a second interlock on a grace period under an hour.
`sweep_orphans_report()` counts every branch that declines to delete. Failures
are collected per key and the sweep continues; `removed` now means removed.

**Four seams the documentation had already promised.** The feed filtered on the
visibility *column* and never consulted the host's visibility policy, so a post
the policy denied still disclosed its title, caption, author and public id
through the listing. The fix has to be SQL — the feed is keyset-paginated, and
dropping rows after the fetch returns short pages and a `next_cursor` pointing
at a row the viewer never saw — so `set_feed_filter` contributes a predicate the
query composes. It is a seam, not an automatic fix, and both directions are
asserted: without one the feed still lists every public post, which is correct
where a host policy only restricts private and unlisted.

Alongside it: `set_visibility_values` (the model has no DB CHECK precisely so a
host can add `draft` without a migration), `set_author_resolver` (the API
answered a hard-coded `"demo-user"` for every author in every deployment, beside
the real id — the id is now the only default and is not overridable), and
`csrf=False`.

**That last one is a fail-closed change.** `current_user_id` without a CSRF
verifier used to log a warning, on the reasoning that a bearer-token host does
not need CSRF and should not be refused. The reasoning was right; the mechanism
was wrong. The failure mode is "any third-party page can post as your logged-in
user", the warning went to a logger the host may never have configured, and the
state you got by *not noticing* was the unsafe one. It refuses now — and what
makes refusing acceptable is that `csrf=False` exists to declare the legitimate
case. Five harness fixtures that authenticate with a closure rather than a
cookie now say so, which is the new rule doing its job on its first day.

**Three configuration defects, all the same mistake.** Title and caption
lengths were stated three times (`String(80)`/`String(300)` columns,
`[:80]`/`[:300]` truncation, `maxlength="60"`/`"280"`) and no two agreed: a
290-character caption could not be typed into the editor but posted fine, and a
350-character one came back **201** with fifty characters silently gone.
Production detection was `RENDER or FLASK_ENV=production` — two names for one
platform and one convention — so Fly, Heroku, Cloud Run, App Service, ECS,
Kubernetes and a plain gunicorn on a VM all silently got an *ephemeral*
SECRET_KEY, different in every worker, which surfaces as dropped sessions, CSRF
tokens rejected by whichever worker did not mint them, and a rate limiter whose
identity HMAC differs per process. And the rate limiter itself defaults to the
in-memory backend, which behind two workers is two limiters granting twice the
budget.

**OWNER, FLAGGED.** Unifying the caption limit reverses a documented earlier
decision. `verify_apiedges.py` carried a block headed *"280 and 300 are
different numbers ON PURPOSE"* asserting that a 350-character caption was
accepted and truncated. Those two assertions were removed rather than adjusted,
because what they pinned was the drift itself. If the split was intentional,
this is the change to revert.

## What is where

| Finding | Fix | Suite |
| --- | --- | --- |
| #1 orphan-sweep reuse race | `stat_key` re-check before delete, `put_bytes` touches | `verify_deletion_foundation.py`, `verify_s3.py` |
| #2 co-tenant key shapes | `KEY_RE` derived from the extension table | `verify_deletion_foundation.py` |
| #3 feed ignores the host policy | `set_feed_filter`, applied in SQL before `order_by` | `verify_hostseams.py` |
| #4 CSRF warning, not refusal | fail closed, with `csrf=False` as the declaration | `verify_txcontract.py`, `verify_hostseams.py` |
| #5 no media resource limits | header-parsed dimensions, WAV duration | `verify_medialimits.py` |
| #6 sweep unrunnable, unobservable | `sweep_orphans_report`, `python -m skribl.sweep` | `verify_sweepjob.py` |
| #7 visibility states rejected | `set_visibility_values` | `verify_hostseams.py` |
| #8 invented `"demo-user"` | `set_author_resolver`, id-only default | `verify_hostseams.py` |
| low: title/caption drift | one constant per field in `core.py` | `verify_hostconfig.py`, `verify_apiedges.py` |
| low: production detection | platform markers plus the app-server name | `verify_hostconfig.py` |
| low: rate-limiter guidance | host defaults a deployment to the db backend | `verify_hostconfig.py` |

## Notes for the next reader

**Every new suite runs in more than one direction.** The lesson recorded at
v240 — *a suite that only tests the direction a feature works passes forever
while the feature is broken* — is now structural rather than remembered.
`verify_medialimits` runs its reject cases, a 4x4 sweep proving real encoder
output parses to the size its encoder was asked for, the documented gaps
asserted rather than promised, and a mutation pass that lifts each cap and
requires every reject to turn back into a pass. `verify_sweepjob` cross-checks
its counters against the listed total. `verify_hostconfig` includes the case
where no platform marker is set at all, without which every refusal it asserts
could be passing for the wrong reason.

**Two suites caught real bugs in their own first draft**, which is the argument
for writing them this way. `verify_medialimits`' end-to-end block found the
first draft posting its bomb under a wrapper key the API does not read — the
assertion had been passing against an empty payload. And an assertion grepping
`routes.py` for `"[:80]"` failed against the *comment* explaining why the slice
was removed: a test of the file's prose, not its behaviour. It was deleted
rather than fixed.

**Fixtures now declare `csrf=False`.** If you write a new harness fixture that
passes `current_user_id`, it will refuse to build until you say which kind of
authentication it is pretending to have. That is the intended cost.
