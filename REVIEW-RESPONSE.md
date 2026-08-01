# Response to review of v109

**Build under review: v111.** All 18 harness suites green, **395 assertions, no skips.**

Every finding was reproduced before being fixed — including the two that got
*worse* after your review, both of which were mine.

## Summary

| # | Finding | Status |
| --- | --- | --- |
| 1 | title/caption 500 | **Fixed** |
| 2 | Media bypass past frame 200 | **Fixed** |
| 3 | X-Forwarded-For trusted | **Fixed by default; needs your topology to enable** |
| 4 | Clear-undo overwrites new work | **Fixed** |
| 5 | Clear deletes autosave, keeps media | **Fixed — semantics stated below** |
| 6 | Empty / signature-mismatched media | **Fixed** |
| 7 | Invalid requests consume post quota | **Fixed** |
| 8 | No structural complexity limits | **Fixed** |
| 9 | Snapshot isn't full state | **Fixed (renamed + scoped)** |
| 10 | WebM first-frame interval | **Open — needs a real browser** |
| 11 | Framing unrestricted everywhere | **Fixed for editors/API; player needs your origins** |
| 12 | Unsafe env integers | **Fixed** |
| 13 | In-memory limiter | **Open — infrastructure decision** |
| 14 | Unpinned dependencies | **Bounded; lockfile still recommended** |

## Two regressions we introduced after your review

You reviewed v109; v110 shipped before your report was actioned, and it made two
of your findings worse. Both are now fixed, but they are worth stating plainly:

- **#8 got a new instance.** v110 added a canvas-size feature that took
  `cssWidth`/`cssHeight` straight from the payload behind a `> 0` guard. Measured:
  a payload declaring 30000x30000 was accepted and allocated four canvases at that
  size. Now bounded server-side (`MAX_CANVAS_EDGE`, default 4096) *and*
  client-side, with finiteness checks.
- **#4 got wider.** v107 and v109 added four new page mutations (copy/paste,
  reorder, drag, hold) and none of them invalidated the clear backup.

## Notes on specific items

**#2.** The `frames[:200]` slice is gone; the walker visits every frame. The frame
*count* is now capped before the media walk runs, so there is no unbounded walk to
defend against. Non-object frame entries are rejected rather than silently skipped.

**#3.** `X-Forwarded-For` is ignored entirely unless `SKRIBL_TRUSTED_PROXIES` is
set to the number of proxies actually in front of the app; the default is `0`,
which keys the limiter on `remote_addr`. When enabled we take the entry *N hops
from the right*, since everything further left is client-supplied. We did not
apply `ProxyFix` blindly — **the correct value depends on your production edge,
which we do not know.** On a single-proxy host such as Render it is `1`.

**#6.** Now rejects empty decoded payloads and checks magic numbers for
PNG/JPEG/GIF/WebP/BMP. Audio is narrowed from "any `audio/*`" to an explicit
allow-list. We stopped short of Pillow decode/re-encode: it adds a dependency and
a decode surface, and is a larger change than we wanted to make inside a review
fix. Flagged as a follow-up.

**#7.** Two budgets. Every request is charged to an **attempt** budget
(`SKRIBL_RATE_MAX_ATTEMPTS`, default 200); only a **committed** post is charged to
the post budget. A flood of 400s can no longer exhaust a shared IP's posting
allowance, and request floods are still limited.

**#8.** Documented, env-tunable limits, all validated before the media walk:

| Limit | Default |
| --- | --- |
| `MAX_FRAMES` | 200 |
| `MAX_POINTS_PER_FRAME` | 20,000 |
| `MAX_TOTAL_POINTS` | 200,000 |
| `MAX_GROUPS_PER_FRAME` | 5,000 |
| `MAX_CANVAS_EDGE` | 4,096 |
| `MAX_HOLD` | 8 |
| `COORD_LIMIT` | 100,000 |
| `MAX_BRUSH` | 500 |

Non-finite values (`NaN`, `Infinity`) are rejected explicitly, since they arrive
through imported drafts and hand-built JSON and poison every downstream bound.

**#10.** Not fixed. We agree it is plausible and we did not want to "fix" a timing
bug we had not measured — the risk of trading it for a different off-by-one is
real. It needs a frame-level measurement in a real browser. Note the surrounding
code moved in v108/v109 (export now iterates a unit array), so the line numbers in
your report are stale though the pattern is intact.

**#11.** Editors, API and error responses now send `frame-ancestors 'self'`. The
player deliberately stays permissive **only while `SKRIBL_EMBED_ORIGINS` is
unset**, so this deploy cannot break an existing embed. Set it to the exact
origins — e.g. `'self' https://skribls.net` — to close the player too. We did not
hardcode an origin list we could not verify.

**#13.** Unchanged and still not production infrastructure. Per-process,
resets on deploy, independent quotas per worker. It should not be relied on as
abuse protection in a multi-worker deployment.

**#14.** Bounded to tested major versions rather than exact pins, because the exact
patch set has to be resolved against your real deployment. Generate a lockfile
there (`pip freeze > constraints.txt`, install with `-c`) for full reproducibility.

## 4. Intended clear/autosave semantics

**Clear removes pages only.** Music, background image, background colour, fps and
all media settings are deliberately retained.

This matches what the live editor already did; the bug was that it then *deleted*
the autosave, so a reload lost media that had visibly survived the clear. Clear now
**rewrites** the autosave, so the persisted draft always matches what is on screen.

Consequently the undo snapshot is **frames-only by design**, and is now named
`clearFramesBackup` rather than described as a full-animation snapshot — which it
never was. That resolves #9 as a naming-and-scope fix rather than by widening the
snapshot.

If you would rather Clear meant "everything, media included", the assertions to
change are in `harness/verify_review.py` under `#5 / #9`.

## 5. Trusted-proxy configuration

**We cannot state this — it is your deployment fact, not a code decision.**

The default (`SKRIBL_TRUSTED_PROXIES=0`) is safe: the header is ignored. Set it to
the real number of proxies in front of the app and confirm your edge overwrites
client-supplied forwarding headers. `harness/verify_review.py` asserts the safe
default; a topology-specific integration test belongs in your deploy pipeline.

## 6. Maximum-complexity payloads

**Accepted at the limit** — 200 frames x 1,000 points = 200,000 points, 5,000
groups per frame, `hold` 8, canvas 4096x4096, coordinates at ±100,000, brush 500:

```json
{"canvasSize": {"cssWidth": 4096, "cssHeight": 4096},
 "frames": [{"strokes": [{"x": 100000, "y": 0, "size": 500}, "... x1000"],
             "strokeGroups": ["... x5000"], "hold": 8}, "... x200"]}
```

**Rejected one over** — 201 frames:

```
400 {"error": "At most 200 frames are allowed (got 201)."}
```

Other representative rejections:

```
400 'frames[0].strokes' has a non-finite x coordinate.
400 'frames[0].hold' must be between 1 and 8.
400 'canvasSize.cssWidth' must be between 1 and 4096.
400 'photo' is not a valid png image.
400 'photo' is empty.
400 'music' has an unsupported audio format (basic).
400 'title' must be a string or null.
```

## 2 & 3. Harness output and new tests

`harness/verify_review.py` — **50 assertions**, one or more per finding, written to
fail against v110. Two existing suites also needed updating, which we note rather
than hide: `verify_csp.py` had pinned the old "frame-ancestors deliberately
absent" behaviour, and `verify_media.py`'s fixtures were all-zero bytes that the
new signature check correctly rejects.

```
verify_audio    9/9     verify_csp     31/31    verify_pages   28/28
verify_lib      8/8     verify_media   24/24    verify_exopts  23/23
verify_fix     18/18    verify_version 20/20    verify_hold    26/26
verify_amber   15/15    verify_ux      24/24    verify_canvas  21/21
verify_dots    10/10    verify_gifenc  35/35    verify_review  50/50
verify_loopcap 18/18    verify_muxer   18/18
verify_race    17/17
                                        TOTAL: 395 assertions, 18 suites, 0 skips
```

Two things the harness still cannot cover, unchanged and stated in `README.md`:
MP4 export (no avc1 in headless Chromium) and CSP in Safari/Firefox.

## 1. Changed files

No commit hash — this is delivered as an archive. Changed in v111:

```
app.py                      #1 #2 #3 #6 #7 #8 #11 #12
static/skribl/flip.js       #4 #5 #8 #9
requirements.txt            #14
.env.example                new configuration
harness/verify_review.py    new, 50 assertions
harness/verify_csp.py       updated for route-specific framing
harness/verify_media.py     fixtures given real signatures
```

## Still open

Items **10** (needs browser measurement), **13** (needs Redis or an edge limiter),
and the deployment facts behind **3** and **11**. We would not describe the posting
endpoint as production-hardened until 13 is addressed.

---

# Response to review round 2 (of v111)

**Build: v112.** 18 suites, **428 assertions, 0 failures, 0 skips.**
`verify_review.py` is now **83 assertions**.

Your revised status, updated:

| Round-2 item | Status |
| --- | --- |
| 1. WebP prefix + unknown image subtypes | **Fixed — strict allow-list** |
| 2. Post-quota check/record race | **Fixed — atomic reservation** |
| 3. Trusted-proxy enabled mode | **Hardened + tested; production values still yours** |
| 4. CSP route detection too broad | **Fixed — endpoint + 200, not path prefix** |
| 5. SKRIBL_EMBED_ORIGINS unvalidated | **Fixed — validated at startup** |
| 6. Permissive structural validation | **Fixed — malformed shapes now rejected** |
| 7. #14 reproducibility | **constraints.txt added; still partial (no hashes)** |
| 8. Weak assertions | **Replaced with behavioural + process-level tests** |
| 9. Clear wording | **Fixed** |

## 1. Image policy — strict allow-list, as you preferred

`ALLOWED_IMAGE_SUBTYPES = {png, jpeg, jpg, gif, webp, bmp}`; anything else is
rejected. Signatures are format-aware via `_valid_image_signature()`, and WebP is
checked as a container — `RIFF` at 0 **and** `WEBP` at bytes 8-11.

Your three cases are asserted, plus two more:

```
RIFF....WAVE as image/webp  -> rejected
RIFF....WEBP as image/webp  -> accepted
arbitrary bytes as image/avif -> rejected
arbitrary bytes as image/tiff -> rejected
b"RIFF" alone (truncated)     -> rejected
```

We did not add Pillow decode/re-encode. The allow-list plus container checks close
the reported hole; a decode surface is a larger change with its own risk, and we
would rather propose it separately than smuggle it into a review fix.

## 2. The race — reserved atomically, released on failure

You were right, and the fix is the pattern you sketched. `_rate_reserve_post()`
checks the cap and takes a `(timestamp, token)` slot inside one lock;
`_rate_release_post()` returns it if no row is created. The reservation now sits
immediately before the only database write, and the old non-atomic pre-check is
gone entirely.

Measured, in `verify_review.py`, against a server process configured with a quota
of 2:

```
12 simultaneous posts, quota 2
  -> 2 x 201, 10 x 429      (exactly 2 rows committed)
sequential: 8 invalid posts, then 3 valid
  -> [201, 201, 429]        (invalid requests spent no post quota)
```

This does not replace #13. The limiter is still per-process.

## 3. Trusted proxy — hardened, and explicitly not certified

The selected value is now parsed with `ipaddress.ip_address()` before it is used
as a bucket key, so a trusted-but-misconfigured edge cannot inject arbitrary
strings. IPv6 is handled.

Tested at three hop counts (0, 1, 2) by patching the module constant, plus non-IP
and IPv6 inputs. We have **not** described enabled proxy handling as verified, and
we cannot: whether Render replaces or appends the header, the true hop count, and
whether the origin is directly reachable are facts about your deployment. Those
belong in your deploy pipeline, not our harness.

## 4. Framing — endpoint, and only on a successful render

Now `request.endpoint == "skribl_player" and resp.status_code == 200`. The endpoint
alone was not enough: an error raised inside the player view carries the same
endpoint.

**One correction to your report:** `/s/<unknown-id>` does **not** 404. The player
shell is server-rendered and the client fetches the post, so an unknown id returns
**200** and is legitimately the player page. Real 404s do take the restrictive
policy. Verified:

```
/s/<valid-id>            200   (permissive - player)
/s/<unknown-id>          200   (permissive - still the player shell)
/s/<id>/card.png         200   frame-ancestors 'self'
/definitely-not-a-route  404   frame-ancestors 'self'
/api/skribls/nope        404   frame-ancestors 'self'
```

## 5. Embed origins — validated at startup

`_validate_embed_origins()` rejects semicolons, commas and newlines, and accepts
only `'self'`, `'none'`, `https://` origins, and explicit localhost dev origins —
bare origins with no path. A bad value fails startup with a message naming the
variable. Seven rejection cases asserted.

## 6. Structural validation — no longer permissive

Non-object stroke entries and non-integer `strokeGroups` entries are now
**rejected**, not skipped. `hold` must be a whole number, so `1.5` and `true` are
refused. We took your first option rather than restating the claim as "bounded but
permissive".

## 7. Dependencies — still partial, as you asked

`constraints.txt` is committed, generated from a clean install. It carries an
explicit header saying it was produced in the harness container (Python 3.12,
linux x86_64) and **without hashes**, and that it should be regenerated on the
deploy target with `--require-hashes` before builds are called reproducible.
**#14 stays partial.**

## 8. Assertions — behavioural, not configuration

The two you called out are gone. `verify_review.py` now:

- calls `_client_ip()` inside real request contexts and asserts two different
  `X-Forwarded-For` values resolve to the **same identity**, and that the identity
  is not the header value;
- spawns **server processes** with their own `SKRIBL_RATE_MAX_POSTS` to assert
  exact status sequences, since these constants are read at import;
- fires concurrent posts and counts committed rows.

## Two of our own suites needed correcting again

Stated rather than quietly amended: `verify_media.py`'s WebP fixture was `RIFF` +
zero bytes, which the new container check correctly rejects, and `verify_csp.py`
had pinned the old permissive framing. Both were our test fixtures encoding the
old behaviour.

## Still open, unchanged

**#10** (WebM first frame) — needs a real browser measurement.
**#13** (distributed limiter) — the endpoint should not be called
production-hardened until quotas leave process memory.
Plus the deployment facts behind **#3** and **#11**, and hashes for **#14**.

---

# Response to review round 3 (of v112)

**Build: v113.** 18 suites, **448 assertions, 0 failures, 0 skips.**
`verify_review.py` is now **103 assertions**. Raw run output is committed at
`harness/LAST-RUN.txt`.

All four items fixed.

## 1. Reservation leaked on non-IntegrityError — correct, and fixed

You were right, and the response document overstated the behaviour: the release
only ran on the id-exhaustion path, so any other commit failure returned 500 with
the slot held for the full window. The insert loop is now wrapped in
`try/except/finally`, and the reservation is released in `finally` whenever no row
was created — id exhaustion, operational error, lost connection, anything.

Tested at the route level by monkeypatching `db.session.commit` to raise a
non-`IntegrityError`:

```
a non-IntegrityError commit failure returns 5xx            500
the reserved post slot is released, not held               0 -> 0
a subsequent valid post can still use that slot            201
and it does consume exactly one slot                       0 -> 1
```

## 2. The concurrency test did not prove the claim — you were right

The test asserted `created <= 2` while our response said "exactly 2 rows". That
was an overstatement on our part, not a passing test. It now asserts the exact
split **and** the database row delta, since 201s are responses and not rows:

```
exactly two concurrent posts succeed        out.count(201) == 2
the other ten are rate-limited              out.count(429) == 10
no other status appeared                    {201, 429}
exactly two rows were committed             SkriblPost.query.count() delta == 2
```

Measured result, 12 simultaneous posts against a quota of 2:
**2 x 201, 10 x 429, database row delta 2.**

## 3. Embed origins now parsed structurally

`_is_bare_origin()` uses `urlsplit` and checks scheme, hostname, userinfo, path,
query, fragment and port parsing. All five of your cases are rejected, plus
`https://` and non-local `http://`:

```
rejected: https://example.com?x=1   https://example.com#fragment
          https://user@example.com  https://example.com:invalid
          https://example.com/path  https://
          http://evil.example.com   https://*.example.com
accepted: 'self'  'none'  https://skribls.net
          https://a.example.com:8443  http://localhost:3000
```

**Wildcards are rejected**, deliberately. They are valid CSP source expressions but
are not origins, and the variable is named `SKRIBL_EMBED_ORIGINS`. A trailing
slash is accepted as equivalent to a bare origin; everything else in the path
position is refused.

## 4. Stale clear label — and a worse one behind it

`templates/_skribl_draw_drawer.html` now renders `Clear all pages` directly, so it
is correct before initialisation, without JavaScript, and to accessibility tooling.

Your test suggestion found a second instance we had missed: the **help text** still
read *"Clear animation wipes everything after a confirm tap"*. That was not just a
stale label — it described the OLD semantics, contradicting the pages-only
behaviour we had just documented. Corrected to:

> **Clear all pages** asks for a second tap first, and the **Undo** beside it
> brings it back. It clears pages only — your music and background image stay.

The assertion is on the **server-rendered HTML**, not the post-initialisation DOM,
so a regression cannot hide behind JavaScript.

## Raw run

`harness/LAST-RUN.txt`:

```
verify_audio    9/9      verify_csp     31/31    verify_pages    28/28
verify_lib      8/8      verify_media   24/24    verify_exopts   23/23
verify_fix     18/18     verify_version 20/20    verify_hold     26/26
verify_amber   15/15     verify_ux      24/24    verify_canvas   21/21
verify_dots    10/10     verify_gifenc  35/35    verify_review  103/103
verify_loopcap 18/18     verify_muxer   18/18
verify_race    17/17
                              TOTAL: 448 assertions, 18 suites, 0 failures, 0 skips
```

## Unchanged and still open

**#10** (WebM first-frame timing) — needs a real browser measurement.
**#13** (distributed limiter) — the reservation is now correct *within a process*;
it is still per-process, still resets on deploy, still independent per worker. The
posting endpoint should not be described as production-hardened until quotas leave
process memory.
**#3 / #11** — the code is hardened and tested; the trusted-proxy hop count and the
embed-origin list remain deployment decisions.
**#14** — partial by agreement: `constraints.txt` is committed but was generated in
the harness container and carries no hashes.

---

# Response to review round 4 (of v113)

**Build: v114.** 18 suites, **506 assertions, 0 failures, 0 skips.**
`verify_review.py` is now **161 assertions**. `harness/LAST-RUN.txt` now carries a
run-context header.

All eight items addressed.

## 1. Classic root-level strokeGroups — real gap, fixed

You were right: round 3 only covered `frames[i].strokeGroups`. A classic Pad
payload could carry `strokeGroups: [{"unexpected": "object"}]` unchecked.

`_validate_stroke_groups()` is now shared by the root payload and every frame, and
it enforces the consistency check you suggested: entries are whole numbers and
their **total must equal the strokes array length**.

Before enforcing that equality we checked it against real browser-generated
payloads rather than assuming — a page with two strokes over 16 points serialises
as `[10, 6]`, exactly matching. Had it not matched, this would have broken posting.

**One deliberate deviation:** zero-valued entries are permitted, not rejected. A
degenerate stroke that registered no points would push a `0`, and refusing it would
fail a legitimate post; the exact total is the real protection and is checked
strictly. If you know zero has no legitimate history, say so and we will tighten it.

Endpoint-level test added, not just a function test.

## 2. Audio bytes — was genuinely open, now checked

`_valid_audio_signature()` covers every allowed subtype: RIFF/**WAVE** for wav,
`fLaC`, `OggS`, EBML for webm, ID3-or-frame-sync for mpeg/mp3, and the `ftyp` box
for the MP4 family, with ADTS for raw AAC. Anything not identifiable honestly is
rejected rather than waved through with a weak test.

**Your sharpest catch:** our own test asserted `RIFF + junk` was an acceptable WAV
— the suite documented the permissiveness under review. That assertion is
corrected. Negative tests now cover arbitrary bytes under **every** allowed audio
subtype, and positive tests cover a real header for each.

## 3. Signature-only, and now described that way

Adopted your "minimal and honest" option. Messages now read *"does not match the
declared &lt;subtype&gt; container"*, and `_valid_image_signature()` carries a
docstring stating plainly that a truncated `b"\x89PNG\r\n\x1a\n"` passes, and
that decodability, dimensions and decompression cost are **not** checked.

There is an explicit test asserting the header-only PNG **is** accepted, so the
limitation is pinned rather than merely written down. Pillow decoding with
dimension and pixel-count limits remains the stronger design and is a deliberate
follow-up, not something we will imply is already done.

## 4 & 5. Embed origins — exclusive, deduplicated, canonical

`'none'` must stand alone; duplicates are rejected before and after normalisation.
Accepted values are now **normalised rather than echoed**, so
`https://Example.COM/` enters the header as `https://example.com`. IPv6 hosts get
their brackets restored and explicit ports are preserved.

## 6. Canvas dimensions must be whole pixels

Rejected: `0.5`, `1.5`, `True`, `"640"`, `0`, `-1`, `4097`. Accepted: `1`, `640`,
`4096`. The same `Number.isInteger` rule now applies in `applyCanvasSize()`, so an
imported local draft and a public payload behave identically.

## 7. Run artifact now states its conditions

`run_harness.sh` emits a context header: UTC timestamp, host, **tree SHA-256**, git
commit, SKRIBL_VERSION, Python/Flask/SQLAlchemy/Playwright/Chromium versions,
DATABASE_URL class, whether the database was reset, every limit and CSP variable,
and the exact command.

It also **creates a fresh SQLite database per run** in a temp directory, so row-delta
assertions and "did this start clean?" are answerable. `SKRIBL_KEEP_DB=1` restores
the old behaviour.

One honest caveat recorded in the file: the run is split into two invocations
because of a sandbox time limit. Both halves ran against the same tree.

## 8. Stale coverage comment corrected

`run_harness.sh` now distinguishes the shared server (raised cap, limiter not
exercised) from `verify_review.py`'s own low-quota server processes, which do test
sequencing, the attempt/post split and concurrent reservation — with a note not to
delete them on the assumption the limiter is untested.

## Our test fixtures encoded old behaviour again

Third time, so worth naming as a pattern rather than an incident: tightening
validation broke `verify_media.py`'s fixtures twice this round (WebP, then audio),
because they were synthetic bytes that only passed under the looser rule. Each
break was the harness working, but it means fixtures need to be realistic from the
start, not minimal.

## Unchanged

**#10** WebM first-frame timing — needs a real browser measurement.
**#13** distributed limiter — still per-process; the endpoint is not
production-hardened.
**#3 / #11** deployment facts.
**#14** partial: `constraints.txt` has no hashes and was generated in the harness
container.

---

# Response to review round 5 (of v114)

**Build: v115.** 18 suites, **522 assertions, 0 failures, 0 skips.**
`verify_review.py` is now **177 assertions**.

## 1. Zero-length stroke groups — you were right, and my reasoning was wrong

Fixed: entries must be **strictly positive**, and the exact-sum check remains.

More important than the fix is how it got there. Last round I wrote that zero was
permitted because "a degenerate stroke that registered no points would push a 0".
I did not check. You did, and the code says otherwise:

- Flip sets `curCount=1` at stroke start (`flip.js:428`) before pushing it
  (`flip.js:460`) — never zero.
- The Pad only pushes under `currentStroke.length > 0` (`app.js:610, 627`) — never
  zero.
- Flip's undo does `splice(strokes.length - n, n)`, so `n = 0` removes nothing
  while still consuming a group: a **no-op undo entry**.

I verified all three against the source before making the change this time. Both of
your example payloads (`[0, 1]` against one point, `[0,0,0,0]` against an empty
frame) passed the old exact-sum check and are now rejected, at the function and at
the endpoint. A crafted run of dead undo entries is refused with
`'strokeGroups[0]' must be a positive whole number of points`.

That is the second time a stated rationale of mine has been contradicted by the
code it described. The lesson is the same one this project's own docs keep
teaching: check the code, don't reason about it.

## 2 & 3. The pickers advertised what the server refuses

Both fixed by narrowing the client to the server's contract.

`.aiff` is **removed from the picker** rather than added to the server. Browser
decode support for AIFF is inconsistent, so offering it would trade a post-time
failure for a decode-time one.

All `accept="audio/*"` and `accept="image/*"` wildcards are gone, replaced with the
explicit type and extension lists. `app.js`'s `startsWith('audio/')` /
`startsWith('image/')` checks are replaced by `SKRIBL_AUDIO_MIMES` and
`SKRIBL_IMAGE_MIMES`, so the editor refuses unsupported media **before** the user
invests time loading and editing it.

To stop these drifting apart again, the suite reads the client's sets out of a live
page and diffs them against `ALLOWED_AUDIO_SUBTYPES` / `ALLOWED_IMAGE_SUBTYPES`.
Adding a type on one side without the other now fails a test.

## 4. Container-FAMILY checks, named as such

The docstring now states plainly that two checks identify a container family, not
audio: EBML admits a video-only WebM or a Matroska file declared `audio/webm`, and
the `ftyp` box admits a video MP4 or an HEIF/HEIC container declared `audio/mp4`.
What they do close is the arbitrary-bytes case. Track and codec inspection needs a
real media parser and is out of scope, stated rather than implied.

## 5. Per-invocation context recorded

`LAST-RUN.txt` now carries a full context block for **each** invocation, its own
results, and a verification footer comparing the two tree hashes:

```
HISTORICAL — v115 SOURCE-TREE hashes (not an archive hash, not this build):
Invocation 1 tree SHA-256: 087111fd592ef4dc708d0f08e8c6755c50841d216f7e3243c9e8868023884af9
Invocation 2 tree SHA-256: 087111fd592ef4dc708d0f08e8c6755c50841d216f7e3243c9e8868023884af9
MATCH — both halves ran against an identical tree.
```
(Retained as the round-5 record. For THIS build's tree hashes see
`harness/LAST-RUN.txt`; for the archive hash see the delivery message.)

## 6. Tree hash no longer includes its own output

Uses `git ls-files` when available, and otherwise a find with explicit exclusions
for `harness/LAST-RUN.txt`, `__pycache__` and `instance/`. That is also why the two
hashes above can match at all — previously the hash depended on the partial state
of the file being written.

## 7. Versions read from package metadata

`importlib.metadata.version()` for Flask, SQLAlchemy and Playwright. Playwright now
reports **1.56.0** instead of the false "missing" that undercut the whole header.

## 8 & 9. Runner hygiene

The temp directory is removed in a `cleanup` trap alongside the Flask kill. The
readiness loop now sets an explicit flag, checks whether the Flask process died
during startup, and **exits 1 with the server log** instead of falling through into
the suites and producing a pile of misleading browser errors.

## Unchanged

**#10** WebM first-frame timing — needs a real browser measurement.
**#13** distributed limiter — still per-process; not production-hardened.
**#3 / #11** — code hardened; hop count and embed origins remain deployment facts.
**#14** — partial: `constraints.txt` carries no hashes and was generated in the
harness container.

---

# Response to review round 6 (of v115)

**Build: v116.** 18 suites, **527 assertions, 0 failures, 0 skips.**
`verify_review.py` is now **213 assertions**.

Both integrity issues are fixed, and — having twice been caught reasoning about
editor behaviour instead of reading it — I checked real serialised payloads from
both editors *before* tightening anything.

## 1. Coordinates are now required

`{}`, `{"x": 10}`, `{"y": 20}` and null coordinates are rejected, at root and frame
level, with per-index messages (`'frames[0].strokes[0].y' is required`).

Verified first: a live Flip payload emits points keyed
`['color','erase','size','start','t','x','y']` with x and y on **every** point, and
the Pad serialises into `frames[0]` the same way. So nothing legitimate loses out —
confirmed again by the nine posting suites still passing.

## 2. strokeGroups is mandatory once there are points

`groups is None` is only acceptable for an **empty** strokes array. A non-empty
flat strokes array without groups is refused at both levels, so a payload cannot
deliberately ship points with no undo structure.

I checked the modern Pad shape for this specifically: its root `strokes` is empty
and the real content lives in `frames[0]`, which does carry `strokeGroups`. That is
why this could be tightened without breaking classic payloads.

## 3. Extension fallback completed

`SKRIBL_AUDIO_EXTENSIONS` and `SKRIBL_IMAGE_EXTENSIONS` now cover everything the
pickers advertise — `.flac`, `.webm`, `.opus`, `.mp4` were all missing. This was a
genuinely user-visible bug on real devices, since `File.type` is routinely empty for
drag-and-drop and some platform file providers.

Tested with `File` objects whose `type` is `""`, exactly as you suggested: `.flac`,
`.webm`, `.opus`, `.mp4`, `.mp3`, `.png`, `.webp` all accepted.

## 4. The extension is a fallback, not an alternative

`skriblHasUsableMime()` gates it: a usable MIME type is authoritative, and the
extension is consulted only when the browser gives us nothing (empty, or
`application/octet-stream`). `song.mp3` declaring `image/png` is now refused for
audio, and `photo.png` declaring `audio/mpeg` refused for images. Both asserted.

## 5. Anti-drift now tests equality, in both directions

Changed to `client_audio == server_audio` (and the same for images), reporting
`client-only` and `server-only` differences. The suite also checks the extension
fallbacks and the `accept=` attributes, since the extension mismatch in #3 passed
every previous anti-drift assertion.

## 6. One image policy — BMP removed

Dropped BMP rather than adding it everywhere. The Pad's drawers only ever offered
jpeg/png/gif/webp, nothing the client produces is BMP, and keeping it meant two
policies sharing one comment claiming to be one. Server allow-list, signature
function, client set and every `accept=` attribute now agree.

## 7. Client-side byte verification — acknowledged, not done

Correct as stated: the client checks labels, not bytes. Decoding before acceptance
(`createImageBitmap`, `decodeAudioData`) is the right UX fix and is a real change to
the media-loading path rather than a validation tweak, so I would rather propose it
separately than rush it here. Server validation remains authoritative. **Recorded
as open**, not claimed.

## 8. canvasSize must be a complete object

`"huge"`, `[]`, `{}`, and half-specified objects are rejected. Public persisted
payloads should have a schema that means something.

## 9 & 10. Runner ordering and strictness

Every variable the app reads is exported **before** the first import, so the
db-init process and the server can no longer see different environments. `set -uo
pipefail` is on, with `set +e`/`set -e` bracketing only the intentionally
non-fatal suite runs.

## Verification

```
HISTORICAL — v116 SOURCE-TREE hashes (not an archive hash, not this build):
Invocation 1 tree SHA-256: 611f025c67855459d33aa9afda4f2c0acec68d3d77b0ad6d6fede5e2f959157c
Invocation 2 tree SHA-256: 611f025c67855459d33aa9afda4f2c0acec68d3d77b0ad6d6fede5e2f959157c
MATCH — both halves ran against an identical tree.
```
(Retained as the round-6 record.)

## Unchanged

**#7 above** (client byte verification) — newly open, deliberately.
**#10** WebM first-frame timing — needs a real browser measurement.
**#13** distributed limiter — still per-process; not production-hardened.
**#3 / #11** — hop count and embed origins remain deployment facts.
**#14** — partial: `constraints.txt` carries no hashes.

---

# Round 7 — the previously "open" items

**Build: v117.** 18 suites, **537 assertions, 0 failures, 0 skips.**

Three of the five open items are now closed. Two cannot be closed by us.

## #10 — measured, and NOT reproducible

The original report marked this "needs browser confirmation", and we repeated that.
Both of us were wrong about why: the sandbox has no **avc1**, so *MP4* cannot be
encoded — but MediaRecorder and WebM work fine, so the claim was testable all along.

Measured: 5 pages at 12fps over 2 loops = 10 units = **0.833s expected**, and the
exported file measures **0.841s**. An extra first-frame interval would add 0.083s
and land at ~0.917s. It does not.

The reason is that the pre-`rec.start()` draw seeds the canvas with the *same* unit
the first timer tick draws, so it costs no time. Now asserted every run, with a
tolerance of half a frame interval. **Closed by measurement, not by argument.**

## #13 — shared-store limiter, opt-in via `SKRIBL_RATE_BACKEND=db`

The in-memory limiter is now one of two backends. The `db` backend uses the
database the app already has — **no Redis, no new infrastructure**.

- **Key is a salted SHA-256 of the client identity, never a raw IP.** Rate limiting
  does not need to know who anyone is, and storing addresses in a posts database is
  a privacy cost with no operational benefit.
- **Concurrency:** the slot row is INSERTed first and counted second, so two racing
  workers both see both rows. The failure mode is over-rejection, not
  over-acceptance — the safe direction.
- Opportunistic cleanup keeps the table bounded.

The property that matters, asserted directly: **a fresh server process still sees
the quota as spent.** The in-memory limiter never had that.

```
db backend enforces the post quota            [201, 201, 429]
concurrent burst over quota                   0 x 201, all 429
a restarted process sees the quota as spent   429
```

Default remains `memory`, so nothing changes unless you set it. With
`SKRIBL_RATE_BACKEND=db` the quota is genuinely shared across gunicorn workers and
survives deploys — which is what "production-hardened" required.

## #14 — real hashes

`constraints.txt` now carries `--hash=sha256:` for all 16 resolved artifacts, from
a clean `pip download`. Install with `--require-hashes`.

It states plainly that it was generated on **linux x86_64 / CPython 3.12** and that
`psycopg[binary]` resolves to a platform-specific wheel, so a different deploy
target **must regenerate it there**. Hashes that do not match your platform are
worse than none.

## #7 — NOT done, deliberately

Client-side byte verification (decode before accepting) is a change to the
media-loading path, not a validator tweak, and the two entry points (drag-drop and
picker) must change together or the result is half-wired. Doing that at the end of
a long session is how the earlier mistakes in this review happened. It remains
open, honestly, rather than rushed.

## #3 / #11 — we cannot close these, and neither can more code

Both now fail safe by default and are fully validated when enabled. What is missing
is not implementation but **two facts only the operator has**:

- `SKRIBL_TRUSTED_PROXIES` — the real hop count at your edge, plus confirmation
  that the edge overwrites client-supplied forwarding headers and that the origin
  is not directly reachable. On a single-proxy host such as Render this is `1`.
- `SKRIBL_EMBED_ORIGINS` — the exact origins permitted to frame the player. Unset
  leaves the player framable by anyone, which is the current (deliberate) behaviour.

We have not guessed at either. Supply them and both close.

---

# Round 7 response — including two reporting failures that were ours

**Build: v118.** 18 suites, **574 assertions**, both halves `RESULT: PASS`,
machine-generated. `verify_review.py` is **229 assertions**.

## 1. The hash mismatch — your option 3, and our process error

`ae0cca…` (HISTORICAL, v117 archive) was the hash of the archive we packaged. We then fixed two stale
ROADMAP lines, **repackaged**, and produced `4c60b818…` — which is the artifact you
received. The new hash was stated in the accompanying message, but the earlier one
was already published, and publishing a hash and then rebuilding the artifact is
indefensible regardless of intent.

The third value, `ac0c2e10…`, is the **source-tree** hash from the run log — a
different thing from the archive hash, which is itself confusing.

Process fix, applied to this build: **the archive is packaged once, hashed as the
final action, and not touched afterwards.** The archive hash is quoted in the
delivery message only, because a file cannot contain its own hash; the tree hash
stays in the run log for cross-checking.

## 2. verify_csp.py — full output, and the real defect

Full stdout/stderr:

```
Traceback (most recent call last):
  File "harness/verify_csp.py", line 53, in <module>
    with urllib.request.urlopen(req) as r:
  ...
urllib.error.HTTPError: HTTP Error 400: BAD REQUEST
---- verify_csp.py exit=1 ----
```

Cause: the suite's fixture posted `canvasSize: {"w": 640, "h": 460}`. Our own v116
rule (round 6, #8) requires `cssWidth`/`cssHeight`, so the post returned 400 and
the suite raised **at module scope, before printing any summary**.

The worse defect is ours, not the fixture's: the aggregate was assembled by hand
with `grep -c FAILED`, and **a suite that crashes prints no FAILED line at all**.
The "0 failures" claim came from a check that structurally cannot observe a crash.
You are right that it should never have been relabelled.

## 3. The runner now generates the aggregate itself

Each suite's output goes to its own log; the runner parses `^\d+/\d+ passed$`,
and a **missing summary or non-zero exit is an ERROR that forces
`RESULT: FAIL`**. The totals above are the runner's, not ours. Verified by the
fact that it caught two real failures during this round — a dead test server and
a flaky WebM capture — and refused to call either green.

## 4. WebM assertion renamed and instrumented

Now `exported WebM duration is within half a frame of expected`, recording MIME
(`video/webm;codecs=vp9`), pages, fps, loops, units, byte length, retry attempts
and the duration-extraction path. A second assertion separately excludes a whole
surplus interval.

It also revealed a real flake: MediaRecorder intermittently yields a header-only
file (1434 bytes vs ~2600 when it works). The test now retries rather than
asserting on a degenerate capture — and if no real recording appears it **fails
loudly** rather than skipping. Latest: measured 0.837s against 0.833s expected.

Scope, as you put it: this closes the alleged duplication for **this
Chromium/WebM path**, not every browser.

## 5. Fresh-bucket concurrency — added; PostgreSQL — NOT done

Added: a brand-new identity, empty bucket, quota 2, **12 simultaneous requests**,
asserting exactly 2 x 201 and 10 x 429. The previous test only proved an already
exhausted bucket stayed exhausted; you were right that it missed the interesting
race.

**Not done: the PostgreSQL run.** There is no PostgreSQL in this sandbox and we
cannot install one. The threads-against-one-process result is what we have. The
docstring now says so explicitly: *"Verified under SQLite and threads; NOT yet
verified on PostgreSQL across processes. Treat the guarantee as 'biased safe', not
proven."* Insert-then-count is not a database constraint, and we no longer imply
otherwise.

## 6, 7, 8. Crash window, write amplification, cleanup

All three documented in the model docstring rather than glossed: the slot commits
before the post row, so **abrupt process termination overcharges** until the window
expires; every attempt is a **database write**, so a malformed flood becomes a
write flood and an edge limiter is still preferable; cleanup is now **bounded**
(`SKRIBL_RATE_CLEANUP_BATCH`, default 500) with a dedicated `created_at` index,
since the composite index does not serve a time-ordered sweep.

## 9. HMAC with a required, dedicated key

`SKRIBL_RATE_HMAC_KEY` (falling back to `SECRET_KEY`), and the db backend **refuses
to start without one** — the public `"skribl-dev"` fallback is gone. Now `hmac`
rather than concatenation. A dedicated key means rotating the session secret no
longer silently resets every quota.

## 10. Restart claim narrowed

Renamed to *"quota survives an application-process restart (same DB, same key)"*,
with a comment listing what it does **not** cover: database replacement, ephemeral
storage, migrations dropping the table, key rotation.

## 11 & 12. Stale header; subprocess readiness

Header corrected. The subprocess helper now checks `proc.poll()` and requires a
ready flag — **which immediately caught a real bug**: making the HMAC key mandatory
broke the db test servers, and under the old code that would have surfaced as a
pile of confusing request errors instead of one clear failure.

## 13. The install command was wrong, and running it proved it

You were right that a text count establishes nothing. Running the documented
command failed:

```
ERROR: In --require-hashes mode, all requirements must have their versions
pinned with ==. These do not: Flask<4.0,>=3.0 ...
```

`--require-hashes` rejects `requirements.txt`'s ranges. The correct command is
`pip install -r constraints.txt --require-hashes`, verified end to end in a clean
venv: 16 packages installed, all imports OK. Documented in `constraints.txt` and
`README.md`, and the test now checks pinning and the documented command rather
than counting hash lines.

## Still not closed

- **PostgreSQL concurrency run** — no PostgreSQL available here.
- **#7 client byte verification** — still deliberately not rushed.
- **#3 / #11** — deployment facts only the operator has.
- A **pending/committed split** with reservation expiry would close the crash
  window properly; documented, not built.

---

# Round 8 — client-side media byte verification (#7)

**Build: v120.** 18 suites, **584 assertions**, both halves `RESULT: PASS`,
machine-generated. `verify_review.py` is **239 assertions**.

The item deferred for two rounds is done.

## The gap

MIME type and file extension are **labels**. A renamed text file called
`photo.png` declaring `image/png` passed both checks, was read into memory, turned
into a data URL, autosaved, and edited — and only failed later, if at all. The
previous rounds' "frontend and server format policy match" was true of labels only,
exactly as your round-6 note said.

## What now happens

`skriblDecodeCheckImage()` and `skriblDecodeCheckAudio()` verify the actual bytes
before a file is accepted, on **both surfaces and all four entry points**. Drag-drop
handlers dispatch into the same `change` handlers, so those are the single choke
point — no half-wired path.

Deliberately cheap: `createImageBitmap()` decodes headers rather than rendering,
and audio uses `<audio>` `loadedmetadata` rather than `decodeAudioData()`, because
the question is "can this browser open it at all", not "give me the samples". A
file that fires neither event within 6s is allowed through and left to the server,
so a slow-but-valid decode is never blocked.

## Verified

```
renamed text as photo.png  (image/png)  -> rejected, "could not be opened"
renamed text as song.wav   (audio/wav)  -> rejected, "could not be played"
a real 1x1 PNG                          -> accepted
via the actual <input>, end to end      -> NOT applied to the canvas, user told why
Flip, both media paths                  -> same behaviour
```

The end-to-end assertion drives the real `photoInput` element rather than calling
the helper directly, so a regression cannot hide in the wiring.

## Known limitation, stated

This proves the browser can **open** the file. It does not prove the file is
well-formed, that its dimensions are sane, or that it will survive re-encoding.
The server's container checks remain authoritative, and full decode-and-re-encode
(Pillow, with pixel and dimension limits) is still the stronger design and still
not built.

## Note on the run log

`harness/LAST-RUN.txt` contains one `ERROR in app: Exception on /api/skribls` line.
That is **deliberate**: the reservation-release test monkeypatches
`db.session.commit` to raise a non-IntegrityError, to prove the rate-limit slot is
returned on an unexpected database failure. The suite asserts the 5xx and the
released slot.

---

# Round 9 — the async selection race, and honest timeout policy

**Build: v121.** 18 suites, **602 assertions**, both halves `RESULT: PASS`,
machine-generated. `verify_review.py` is **257 assertions**.

## 1. The stale-selection race — my regression, fixed

You are right, and it is a regression I introduced: those handlers were
**synchronous** before I added byte verification. Adding `await` opened a window
where a slow decode of file A could land after the user had already chosen B.

Each media slot now carries a monotonic token, bumped on **every selection and
every removal**. A handler returning from its await with a stale token drops its
result silently — including its toast, because complaining about a file the user
already replaced is noise. Four slots, two surfaces, separate tokens.

Proven with controlled promises exactly as you specified:

```
dispatch A, dispatch B, resolve B, resolve A late
  -> B applied, and the late A does NOT overwrite it
dispatch A, remove media, resolve A
  -> nothing reappears
```

## 2. The timeout now FAILS CLOSED

You caught a real contradiction: I claimed "bytes are verified before acceptance"
while a 6s timeout **resolved success**, so a stalled decode was accepted — on
precisely the pathological input the check exists for.

Now fails closed at a named `DECODE_TIMEOUT_MS` (10s), with *"That audio took too
long to check. Please try another file."* Same policy for images, which previously
had no timeout at all — your #7. The claim is now true as written: nothing is
accepted that the browser has not affirmatively opened.

Cost, stated: an unusually slow but valid file on a slow device is rejected. 10s
is generous for metadata; if that proves wrong in the field, the fix is a
"still checking" state, which needs the tokens that now exist.

## 3. All four inputs, driven end to end

Previously only Pad photo was driven through a real element. Now all four —
Pad photo, Pad music, Flip image, Flip music — each asserting **post-rejection
state**, not just the toast: no image source, no `audioEl`, no `bgImage`, no
`musicData`. Valid files are asserted to still be accepted, so the checks cannot
pass by rejecting everything.

## 4. Failed replacement leaves existing media intact

Asserted: load a valid image, attempt a malformed replacement, confirm the
original src is byte-identical afterwards. This matters more now that tokens
exist, since an over-broad invalidation could have dropped the good one.

## 5. Deduplicated — the helpers now exist once

New `static/skribl/lib/media_validation.js` owns the MIME sets, extension
regexes, usable-MIME logic, both decode checks, the timeout constant and the
user-facing strings. Loaded before the main script on all three surfaces, with
back-compat aliases so call sites are unchanged. `app.js` and `flip.js` no longer
define any of it, and a test asserts they don't.

Given this history's repeated policy-drift bugs, two copies of a security- and
UX-sensitive check was a bug waiting to happen rather than a style question.

## 6 & 7. Probe cleanup and image cancellation

`finish()` now clears the timer, detaches both handlers, removes `src`, calls
`load()` and revokes the object URL — so rapid selections no longer leave a
timer and a live probe element per attempt. The image check races against the
same timeout and, if a bitmap arrives after the caller has moved on, **closes it**
rather than leaking. `createImageBitmap` has no universal abort, so the work can
be discarded but not cancelled — stated in the comment.

## 8. Comment corrected

Now: *"createImageBitmap asks the browser to decode the image without adding it to
the document or running our normalization/re-encode path."* The old
"decodes headers" understated it.

---

# Round 10 — two remaining races, and a test that proved the wrong thing

**Build: v122.** 18 suites, **615 assertions**, both halves `RESULT: PASS`,
machine-generated, both invocations against one tree.

## 1. Pad photo removal — a real bug my test was hiding

Confirmed and fixed. `photoRemove` never touched `photoSelectionSeq`, so a decode
running when the user hit Remove finished with a *current* token and re-applied
the photo that had just been removed.

The part worth dwelling on is your diagnosis of the test. It did:

```js
photoSelectionSeq++;   // what a removal does
```

That comment was a lie the test could not detect: it simulated the implementation
I intended rather than exercising the one I shipped, so it passed against broken
code. It now clicks the real control:

```js
document.getElementById('photoRemove').click();
```

I have written variants of this mistake more than once in this review — asserting
against my own model instead of the artifact. The rule I should have been applying
is the one you stated: assertions use user-accessible behaviour only.

## 2. Flip lost the token after decode — fixed through every async stage

You were right that the guard stopped at the decode await while `FileReader`
remained asynchronous. Both Flip handlers now re-check the token inside
`reader.onload` and `reader.onerror`, so a slower read cannot overwrite a newer
selection or restore media after removal.

Tested by stubbing `FileReader` to hold A's result, applying B completely, then
releasing A: **B survives.**

## 3. Valid audio now driven through both real music inputs

Fair — the positive coverage was image-only. The suite now builds a genuinely
decodable 44-byte-header WAV and drives it through `musicInput` on both surfaces,
asserting resulting state (`audioEl` on the Pad, populated `musicData` on Flip),
not the absence of a toast.

## 4. The fallback leaked its object URL on exactly the path that mattered

Fixed with a cleanup hook that every completion path runs, including the timeout —
which is the path that fires precisely when the `<img>` emits neither event.
Asserted by stubbing `createImageBitmap` away, `URL.createObjectURL`/`revokeObjectURL`,
and an `Image` that never fires: **created 1, revoked 1.**

## 5. Cache-bust corrected

`media_validation.js` now `v='121'` in all three templates. You are right that
deriving asset versions from one build identifier would be better than hand-editing
each query; recorded as a follow-up rather than done.

## 6. The player is NOT trimmed — evidence

`skribl_player.html` renders **both** `musicInput` and `photoInput`, unconditionally
(lines 696 and 803). `app.js` runs on the player and binds change handlers to those
elements, so `SkriblMedia` is genuinely reachable there; removing it would leave a
`ReferenceError` waiting behind a live control. Asserted in the suite so nobody
trims it later on the same reasoning.

If those inputs *should not* exist on the player, that is a different and probably
better fix — but it is a behaviour change to the player, not a script-loading tidy.

## A test correction made during this round

The WebM assertion failed at 0.748s — about one frame **short**. That is
MediaRecorder dropping frames under load, exactly the variance you flagged in round
7. The two-sided bound was therefore testing recorder fidelity, not the claim. It is
now **one-sided** (no duration *above* expected, which is the alleged bug) plus a
floor to catch a degenerate capture. Stated here rather than quietly retuned.

The runner caught this and refused to report the run green, which is what it is for.

---

# Round 10 — PostgreSQL concurrency, tested rather than assumed

**Build: v123.** 19 suites, **632 assertions**, 0 skipped, 0 problems.

## The assumption was wrong

For several rounds I wrote that PostgreSQL was unavailable in the build
environment and recorded it as a limitation. I never tried to install it. It took
two commands. That is the same failure as the stroke-group rationale and the
`frames[:200]` boundary — an assumption stated confidently enough that it stopped
looking like one.

## Result

`harness/verify_postgres.py`, 10 assertions, run against a live PostgreSQL 16.14
with gunicorn serving from **four worker processes** — separate OS processes with
separate connections, not threads against one dev server:

```
12 requests released together through a threading.Barrier, quota 2
  HTTP           : 2 x 201, 10 x 429
  post rows      : 2 (queried directly from PostgreSQL, not inferred)
  rate events    : committed=2, pending=0
```

No over-admission, no under-admission, no worker crash, no stranded reservation.
Insert-then-count holds, and the pending/committed split promotes cleanly with
nothing left dangling.

**Narrow conclusion, deliberately:** this closes multi-process over-admission for
the *tested* configuration — this PostgreSQL version, default isolation,
gunicorn's default worker model, this connection setup, no induced failures, one
12-request burst. It says nothing about other isolation levels, pooling
arrangements, failure modes, or production load.

## Skips are not passes

The suite exits **77** and prints `SUITE-SKIPPED` when PostgreSQL, psycopg or
gunicorn are absent. The runner records skipped suites separately: **zero
assertions**, listed by name, and the verdict becomes `PASS WITH SKIPS` with the
explicit line *"Their coverage is NOT demonstrated by this run"*. Your reviewer
will see a skip, because they have no PostgreSQL — and it will not read as
evidence of anything.

## Two defects this work surfaced

**In the runner.** With `set -e` active, `line="$(grep ...)"` aborts the script
when grep matches nothing — which is precisely when a suite has CRASHED or
SKIPPED. The mechanism built to stop crashed suites being misreported would have
silently ended the run instead. Fixed with `|| true`, and both paths are now
proven: a crashing probe yields `ERROR ... RESULT: FAIL`, a skip yields
`SKIPPED (0 assertions) ... PASS WITH SKIPS`.

**In the new suite.** It first counted *all* committed rate events rather than the
delta, so rows from an earlier manual run made it report `committed=4` and fail.
Every count is now a before/after delta.

---

# v124 — page controls moved out of the thumbnail

**Build: v124.** 19 suites, **636 assertions**, 0 skipped, 0 problems.

Three UI fixes, all from screenshots rather than the roadmap.

## 1. "Re-add" was blurry — a text-shadow in the wrong place

`.pending-btn` shared a rule with three other selectors:

```css
.pending-btn, .restore-btn.confirm, .tool-btn.active, .photo-fit-btn.active {
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
}
```

The other three are **white text on colour**, where a dark shadow lifts the
glyphs. `.pending-btn` is dark `#171a22` **on yellow** — the same shadow just
smeared the edges. Removed there only. Four instances, all the same button: the
shared music and photo pending cards, plus two inlined in the player template.

## 2. The selected-frame border drew 3px, not 2

`.frame` has a 1px border and `.frame.on` added a 2px ring on top. Ring is now
1px, so 2px total — unmistakable at thumbnail size without the slab look.

## 3. Per-page controls left the thumbnail entirely

Measured on the reported setup, every in-tile control was **18x18 px** — roughly
a third of the 44px both Apple and Google recommend, five of them on an 88x62
tile, with the hold badge immediately beside the delete button. A mis-tap there
deleted a page.

Worse: the strip had **no mobile rules at all**. `.frame` sits at brace depth 0,
so a phone got byte-identical sizing to a 27-inch monitor.

Controls now act on the **selected** page from a toolbar above the strip:

| | before | after |
| --- | --- | --- |
| Target size | 18x18 | **38x38** (icons) / 38 tall with labels |
| Thumbnail covered | ~36% | **0%** |
| Delete adjacency | ~4px from Hold | **223px**, pushed to the far end |
| Mobile rules | none | icons under 560px, labels above |

Delete's separation is asserted by measuring the rendered gap, not the CSS
declaration — `margin-left: auto` resolves to a pixel value, so the obvious
assertion passed while proving nothing.

## The harness caught both breakages

Removing the in-tile controls broke `verify_pages.py` and `verify_hold.py`, which
drove them. Both crashed before printing a summary, and both were reported as
`ERROR — exit 1, NO assertion summary` rather than silently skipped — the
machinery added in v118 doing exactly its job. Suites updated to drive the
toolbar.

---

# v125 — worker-level liveness, not just master survival

**Build: v125.** 19 suites, **640 assertions**, 0 skipped, 0 problems.
`verify_postgres.py` is now **14 assertions**.

## The gap was real

v124 asserted *"no gunicorn worker crashed during the burst"* from
`proc.poll() is not None` — which watches the **master**. A worker that crashes is
silently replaced by the master, leaving the master alive and the worker count
unchanged. The assertion could not have observed the thing it claimed. The result
was true; the evidence for it was not.

## Now observed three independent ways

- **PID set identity.** Worker PIDs are read from
  `/proc/<master>/task/<master>/children` before and after the burst and compared
  as a set. A crash-and-respawn changes a PID even though the count stays 4.
  Recorded: `before=[792, 793, 794, 795] after=[792, 793, 794, 795]`.
- **Boot count.** gunicorn runs at `--log-level info`, which announces every
  worker boot. Exactly **4** `Booting worker` lines; a respawn would make 5.
- **Exit log.** Zero `Worker exiting` / `was terminated` / `Worker failed to boot`
  lines during the burst.

The master check is kept as a separate, correctly-named assertion.

## A trap in the first attempt

Sampling the log after `proc.terminate()` counted **4 exit lines** — our own
shutdown, not crashes. The log is now snapshotted *before* termination, so the
assertion sees only the burst window. Had that gone unnoticed the suite would
have failed permanently on a healthy system, which is its own kind of wrong.
