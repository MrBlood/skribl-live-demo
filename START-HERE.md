# START HERE — Skribl session primer

## Next session: read this block first

    result       see harness/RELEASE.md — generated, never typed here
    tree hash    see harness/RELEASE.md — generated, never typed here
    files        see SHA256SUMS — the command below prints the count

Nothing in this block is a number, deliberately. It used to carry an assertion
total, a suite count, a skip count and a file count, and carried all four
unchanged through three builds that changed every one of them. `verify_docs.py`
caught the suite count only because that one happened to be checked against the
directory listing. A number typed here is a number that goes stale silently.

Verify before believing anything in prose, including this file:

    cd skribl-v*                                    # the name derives from SKRIBL_VERSION
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N
    grep -m1 'tree hash' harness/RELEASE.md
    python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"

**What a visitor downloads on a shared link — RUN IT, do not read it:**

    ./harness/run_harness.sh verify_player_isolation.py

Its last assertion prints the whole payload broken down — JS, HTML and CSS
separately, their sum, and the gzipped figure — and the suite fails if any part
grows past its ratchet. **The numbers are deliberately not repeated here.** This
block used to carry nine of them across two tables, every one measured at v199,
and they were still sitting here unchanged dozens of releases later describing a
player that had shrunk under all of them. That is the same failure the paragraph
above this one warns about, committed fifteen lines after warning about it.

One of those numbers is worth knowing as a SHAPE rather than a value: the
gzipped "on the wire" figure is roughly a quarter of the source total, and must
never be quoted as "the player's JavaScript" — the suite says so at the
assertion itself.

`skribl/jsstrip.py` removes comments from the RESPONSE — the files on disk keep
every word, which is the only reason this was allowed at all — and
`harness/tools/cssgraph.py` classifies rules inside a media block instead of
keeping the whole block whenever one rule matched. Neither moved a byte of
source.
`verify_jsstrip.py` is the gate on the first (Chromium compiles and evaluates
every case; the lexer checking its own output proves nothing) and
`verify_cssplit.py` on the second (eleven scenes, pixel-identical).

### Closed in v278: an outside review, and a phone that answered

v278 is one thing from the owner's own phone and five from an external
developer review of the sealed v277 archive. **Every one of the five was
checked against the tree before it was acted on, and every one was real** —
two of them larger than the tree's own description of them.

**The iOS silent-mode fix is confirmed on a phone** (5 Sep 2026, "Music
works"). v277 sealed it saying in as many words that a green seal was not
evidence and the phone was the test; the phone answered. `verify_audiosession.py`
keeps its closing disclaimer, because the confirmation is evidence about the
FIX, not about a harness that still has no ringer switch. Details below, under
"Closed in v277".

**An external developer review of the sealed v277 archive found five things,
all of them real** — checked against the tree one at a time before any were
acted on. The one that mattered: the /s player claimed the iOS playback session
on the play/pause tap BEFORE the branch deciding which it was, and released it
nowhere, so the first Play held it until the tab closed. Not silence — a
Control Center entry the viewer cannot clear, which is why v277's own audio
sections stayed green over it. Every edge now routes through one
`syncAudioSession()`. Fixing it blew the player's JS ratchet, exactly as the
review predicted 600 B of headroom would; repaid by carving `initMoreTools()`
into `editor_tools.js` (153,251 → 149,946, ratchet down to 150,000). Full
account in the second v278 entry at the foot of `DECISIONS.md`.

**The feed draws the same picture as the shared page.** The wet/dry compositor
is implemented in `inlineplayer.js` — the review's last finding. It cost 2,913 B
and the embed ratchet went 29,000 → 32,000. The old reason for not doing it
("twenty boxes, one playing") was wrong: `play()` settles every other player, so
one is ever playing.

**A Skribl can be taken back.** `skribl/deletion.py` adds `delete_post()` and
`set_post_visibility()` — the review's second high finding. The FK cascade and
orphan sweep were already built and tested; what was missing was the authorised
product operation on top. A missing post and someone else's raise the same
exception with the same message, on purpose. **v278 registered `DELETE` and
`PATCH` only when the host passed `current_user_id`; v279 reversed that** — see
"Closed in v279" below. The gate was right about the danger and wrong about the
remedy: it also left the deployed product unable to revoke anything.

**`_ZOOM_EXEMPT` in `verify_ux.py` is now empty** — all seven sub-16px fields
were raised, so the iOS-zoom rule is absolute rather than a ratchet. The raise
was not free: Flip's `.mb-offset` readout WRAPPED at 16px and painted its second
line over the control beside it, at 320, 360, 375 and 390 — with every geometry
probe in the tree reporting "ok", because a wrap does not move the box.
`verify_layout.py` section 5 now measures `scrollHeight` against the box's own
height, which is the measurement that sees it. See the v278 entry at the
foot of `DECISIONS.md`.

### Closed in v281: the half of the recovery key that was missing

A third adversarial audit read the sealed v280 and returned **No-ship** again.
It confirmed the v279 fixes were all present and correct, and then named a gap
that is a design failure rather than a bug:

> A user can now **save** a recovery key but cannot **use** it after the browser
> copy is gone.

**v280 built export and never built import.** The panel said "keep it somewhere
you will find it". The tray offered **Copy key**. And nothing anywhere would
accept one back — the only `DELETE` the product could send read its token out
of the local record, and the button that sent it rendered only when that record
already held one. So the four situations the key exists for (cleared site data,
origin eviction, a new device, a failed write) all ended the same way: the
author holds the credential the product told them to keep and the product will
not take it.

The invariant the audit asked for, which is the one to hold on to:

> **Possess the id and the key → revoke through the product, whatever this
> browser happens to remember.**

**"Use a recovery key" in Your Skribls** is that loop closed. It takes a share
link or a bare id plus the key, and offers two outcomes: take it down, or add
it to this browser's list. The second matters as much as the first — it
re-establishes custody, which is what makes export → lose the browser → import
a round trip rather than a one-way door. Adding does NOT verify the key and
says so, because deletion is the only operation that can tell and it is
destructive.

**It is deliberately not on the player page.** Two reasons, and the second is
the real one: `/s/<id>` is what RECIPIENTS open. A takedown affordance
there would teach that holding the link is what entitles you to remove it,
which is the trap the second audit named when it warned against turning
possession of a shared URL into deletion authority.

**Clear list stopped being ordinary history.** It wiped every stored key on a
second tap while the posts stayed online. The single-row `×` had warned about
exactly that since v279 — the weaker contract was winning on the more
destructive path, which is the audit's "same structure, two incompatible
purposes" pattern. It now names how many keys are at stake and withholds
"Clear anyway" until an export has actually succeeded; a failed clipboard write
leaves it locked, because a failed copy that unlocked it would be the same
false certainty this release removes from `DELETE`.

**A 404 means unknown.** `deletion.py` answers the same 404 for "no such post"
and "not yours" so the API cannot be walked for which ids exist. The client was
collapsing that into success and dropping the credential for a post that might
still be live — with a comment of mine arguing for it: *"the local entry should
go either way."* It does not. Security ambiguity on the server cannot become
certainty in the UI.

### What the gates caught, including one I built last release

**`verify_a11y`'s modal census passed over both new dialogs.** The v280 gate
enumerated `[aria-modal="true"]` from the live DOM and primed the one
runtime-built dialog it knew about by name. Two more arrived in `recoverykey.js`
and the census could not see them, because a sweep taken at load cannot see a
node that does not exist yet. That is the hole the v280 note warned about, in
writing, one release before walking into it. There is now a **JS-source
census** beside the template one: every non-minified `.js` under
`skribl/static/` that mentions `aria-modal` has its assigned element ids
extracted and required to be recipe-backed, so the next runtime-built dialog
fails the suite instead of slipping through.

**The wrong-key test passed with the bug fully restored.** Deleting a row calls
`confirm()`, Playwright dismisses dialogs by default, so `destroy()` never ran
and the assertion was checking that nothing had changed after nothing had
happened. It drives `destroy()` directly now. Measuring something ADJACENT to
the claim is the recurring failure of this whole sequence of releases — it has
happened in most of them, to me, in assertions I had just written — and it is
the argument for mutating every new assertion rather than trusting a green
one.

### Also closed in v281: a staleness sweep, and what it says about the tree

The sweep ran until two consecutive passes from different angles found
nothing. **Twelve findings, and every one was a description that had drifted
from a thing — not one was a logic bug.** Three templates loaded modules
nothing on those pages read; the shared-module index had three wrong rows and
three missing; `docs/INTEGRATION.md` never mentioned `player_target`; README's
route table did not mention DELETE, which is the whole revocation feature the
previous two releases were spent building; `verify_jsstrip` measured four of
the player's nine scripts; two byte figures were measured on disk and reported
as what a link costs; 7.8 KB of CSS styled controls that do not exist; three
assertions asserted the literal `True`; and the Pad emitted two elements with
`id="skink-m"`, so the brand mark under the player declared `x2="65"` and
rendered at 101.

**The invariant to carry forward is about the shape of the tree, not any one
of those.** There are 41,546 lines of harness and 13,608 of markdown against
35,832 lines of shipped code — more description of the thing than thing. Every
restatement is a place where two files must change together or one becomes a
lie. Staleness here is not decay; it is the arithmetic of saying one fact
twice.

So the order of preference is **derive, then delete, then gate.** This sweep
reached for the gate six times and that is why the harness grew. A gate
detects drift and costs a permanent assertion; a derivation prevents it. The
pattern already exists in this repo — the generated HARNESS-COUNTS stanza
stopped being prose because prose kept going stale — and the module index,
route table and seam table are the same shape. Turning them into generated stanzas is v282's
first job, and it lets four of the gates added here be deleted.

**And the process rule, which cost more than any single finding.** Across the
sweep roughly as many probes were wrong as defects were found: a truncated
`head`, a `--` that swallowed an `--include`, a regex that took the first of
eight exports, a CSS trimmer that ate a comment terminator and corrupted the
shared `.slider` rule. Worst of them, the first README route-table gate reused
a set of PATHS, so GET, PATCH and DELETE collapsed into one entry — **it would
have passed on the tree that motivated it.**

> Calibrate the instrument on a known answer before believing its output. Run
> every new probe against one case known bad and one known good; if it cannot
> tell them apart, the probe is wrong, not the tree.

That is the mutation test moved BEFORE the fix rather than after. Its narrower
companion: **do not edit mechanically where prose and code interleave.** Three
automated passes over the stylesheets each produced fresh damage before the
fourth was done by hand.

### Closed in v280: a capability whose custody was nobody's job

A second adversarial audit read the sealed v279 and returned **No-ship**, with
one High of its own and one it re-raised, plus four Mediums and a Low. Every
finding was checked against the tree before it was acted on and every one held.
Its diagnosis is the sentence to keep:

> The server-side primitive is the strongest part of the new design… The
> failure is lifecycle ownership around that secret.

**Minting and verifying a capability is not the whole security boundary.**
Creation, durable custody, recovery, migration and retirement are all inside
it, and v279 had built the first two beautifully and left the rest to a
localStorage write whose return value nothing read.

**Two ways to publish something irrevocable and be told it went fine.**
`posted.js`'s `write()` has always returned whether it succeeded and `add()`
has always discarded it, so quota exhaustion or private mode produced a live
public post, no key, and a success message. Separately, `write()` truncated to
`LIMIT` on every call, so the 201st Skribl silently stranded the 1st — still
live, no longer withdrawable — and the 202nd stranded the next. Deterministic,
not an edge case.

`add()` now returns `{list, durable, key}` and both surfaces check it.
`capped()` keeps the newest `LIMIT` entries **plus every entry carrying a key**,
however old, so the cap bounds what is KEPT and never drops what authorises.
(It was written up as governing "what is rendered", which understates it: an
entry past the limit with no key is dropped from storage, not hidden.)

**IndexedDB was the obvious answer and the wrong one.** It is cleared by the
same user action and the same Safari eviction sweep as localStorage: it buys
capacity, not durability, and the durability is what was missing. What actually
survives cleared site data, a new phone, or an account system that does not
exist yet is the person holding the key. So `lib/recoverykey.js` shows it when
the browser cannot keep it, `warnIfVolatile()` says so *before* posting rather
than after, and Your Skribls offers **Copy key** beside Delete. (That is the
EXPORT half only, which a third audit called v280's blocker — see "Closed in
v281" above for the half that accepts one back.) It is called a
recovery key in everything a user reads, because the same secret is what a
future account system would take to CLAIM a post, and a name meaning only
"delete" would have to be retired exactly when the back-catalogue depended on
people still recognising it.

**Pre-v279 anonymous posts still cannot be self-served, and no migration can
change that** — see the note in `docs/INTEGRATION.md`. `python -m
skribl.takedown` is the operational answer, with `--list-orphans` as the census
that says whether any deployment actually has the problem.

### `verify_a11y.py` generates its population now

Three of seven `aria-modal` surfaces were routed through `SkriblModal`; the
suite tested one of the three by hand and passed. The audit named the shape:
*a global semantic claim should generate its test population from the DOM, not
from a manually chosen specimen.* The suite had already learned to assert
behaviour instead of attributes, and then asserted the right thing about the
wrong population — the same error one level up.

All eight surfaces route through the utility (the eighth is the new recovery
panel). Section 2 reads `[aria-modal="true"]` out of the live DOM; a surface
with no recipe **fails** rather than being skipped, a recipe naming a deleted
surface fails too, and a template census backstops the dialog that lives behind
an unrendered branch. A dialog built at runtime escapes a census taken at load,
so `recoverykey.js`'s overlay is primed before the sweep — anything added the
same way must be primed too, and the template census is what will say so.

**It immediately found a defect in `modalfocus.js` itself.** `close()` checked
`isConnected`, but an opener can be present and `display:none` — the leave
confirm closes the menu holding its opener on the way up. `focus()` was then a
silent no-op and the user landed on `<body>`: the exact outcome the utility
exists to prevent, reached through the one door it did not cover. It checks
`offsetParent` now and falls back to whatever had focus when the dialog opened.

### Two gates that were representatives of a global contract

`verify_txcontract.py` scanned two files — the two where the v224 violation
happened to be found — so `takedown.py` could have committed the shared session
from request-shaped code and stayed green. It scans every module now, by AST
rather than by grep, with exemptions named **per function**. Per function
because widening it produced a finding at once: `storage.py` is a library a
host imports and only its batch function may commit, so a file-level allowlist
would have waved the whole module through. Its stale-exemption check then
caught an exemption I had granted on an assumption, for a function that does
not commit at all.

`verify_docs.py` gates the CI-cost claim. Two of this release's findings were
stale statements in **source comments**, where the v279 sweep never looked: 22
lines above the delete routes still calling the v278 identity gate "the whole
design", and the header of `harness.yml`, which used to say a heavy CI day had
burned a monthly Actions allowance. This repository is public and every job
runs on `ubuntu-latest`, so there is no allowance — see `CLAUDE.md`. The gate
asserts the half that is checkable offline: while every runner is standard,
nothing current may call this project's minutes finite or billed. Move to a
larger runner and the claim becomes sayable again and the gate stands down by
itself.

### Closed in v279: twelve findings from a second audit, all real

An external audit read the sealed v278 archive and returned one High and
eleven Medium findings across three passes, plus a coverage ledger and the
sentence that set the release's shape: **"No-ship for the standalone premium
product until P1-H-01 is resolved."** Every one was checked against the tree
before it was acted on and every one held. What follows is what changed; the
reasoning is in the v279 entries at the foot of `DECISIONS.md`.

**The High finding was v278's own remedy.** v278 shipped `delete_post()` and
`set_post_visibility()` and then registered the HTTP routes only when the host
had passed `current_user_id` — so the standalone product, which is the premium
one, could not revoke anything at all. The gate was right that an
unauthenticated DELETE erases any Skribl anyone can name; it was wrong that
absence was the fix, because "you cannot delete it" and "anyone can delete it"
are both failures.

**The answer is a capability, not an account.** An anonymous post is created
with a `secrets.token_urlsafe(32)` returned once, in the create response, and
stored only as a SHA-256 digest (`skribl_posts.delete_token_hash`). DELETE and
PATCH are now registered unconditionally and a caller must present *something*:
a matching token, or ownership, or an explicit in-code `require_author=False`.
A stranger holding only a public id gets the same 404 as a stranger holding
nothing.

This was chosen over per-post passwords and over "wait for accounts" for one
reason: it composes with accounts instead of competing with them. A deployment
that grows real users later keeps every anonymous post revocable through the
capability while new owned posts authorise by identity. The alternative
stranded the whole back-catalogue on the day the feature it was waiting for
arrived.

**Three smaller Mediums in the same area.** `PATCH` accepted any JSON root and
any extra keys — `"null"` reached the handler and 500'd, and
`{"visibility": "private", "delete": true}` was silently tolerated; it now
takes an object with `visibility` and optionally `deleteToken`, nothing else.
Creation treated a failed pending-media claim as best effort and posted anyway,
which is the reservation protocol failing open; it now raises
`SkriblUnavailable`. And `/media/<key>` answered public objects
`max-age=31536000, immutable`, which `deletion.py` twenty lines away promised
"stops being reachable" — two documents corroborating each other into a false
guarantee. The window is `routes.PUBLIC_MEDIA_MAX_AGE`, five minutes, and
`immutable` is gone, so the promise is late rather than untrue. Closing it
completely needs a purge hook a deployment supplies.

**Identities became opaque text and the MP4 gap became evidence** — both below.

### `verify_a11y.py` — keyboard and assistive technology, as its own suite

Added after an accessibility audit of v278, and a suite rather than more of
`verify_ux.py` because of the audit's structural point: the tree carried
thousands of assertions — the count is in `harness/RELEASE.md`, never typed
here — while basic keyboard failures were visible in the source. Three
playback scrubbers were pointer-only, two of them declaring `role="slider"`
with no tabindex, no `aria-valuenow` and no key handler — announcing a control
that could not be operated. Every `aria-modal` dialog did nothing about
focus — this said "Five" until v280, when counting them for the enumeration
gate found seven.
Visible slider captions were not labels. Segmented controls kept selection in a
CSS class. Nothing announced that a post had succeeded or failed.

Its own rule: **assert the behaviour, not the attribute** — `role="slider"`
being present is exactly what was true while it was broken. It presses keys and
reads what moved, focuses things and reads where focus went.

Two things it caught that the audit had not: five unnamed controls in Flip's
share sheet and image drawer, and `--text-faint-2` on `.accordion-count` at
3.47:1.

And one about ITSELF. The contrast gate's first version exempted any line
matching `--text-`, meaning to skip the token definitions — but
`var(--text-dim)` contains `--text-`, so it skipped every use as well and the
check was vacuous. Putting a failing token back on readable text left it at
37/37. Definitions are excluded by shape now.

### Identities are opaque text

`skribl_posts.user_id` is `String(255)` behind a `TypeDecorator`, not `Integer`.
The column was Integer while `docs/INTEGRATION.md` advertised "your user id",
so a host using UUIDs, ULIDs or an OAuth subject could not integrate at all.
Integer hosts are unaffected — 42 stores as "42" and both sides of every
comparison normalise. `author.id` in the API is a JSON string now.

**Both sides, not just the argument.** Normalising only the incoming id passed
every suite that goes through `create_post` and failed `verify_privacy`, which
builds `SkriblPost(user_id=7)` in memory and never flushes it — so the
TypeDecorator never ran and an author could not read their own private post.
The type covers what is stored and loaded; the comparison covers what was never
persisted. Both are needed and for different reasons.

### The MP4 attestation — what a seal can honestly say about H.264

`verify_mp4.py` skips wherever Chromium is the browser: Playwright ships the
open-source build, which has WebCodecs but no H.264 encoder. (Probing
`VideoEncoder` on `about:blank` reports "no WebCodecs at all" and is
misleading — the suite checks on a real page, where the API is present and the
three `avc1.*` profiles are all unsupported.)

The `mp4 (real Chrome)` CI job covers it, and until v279 its result never
reached the archive: the seal said `skipped 1 (verify_mp4.py)` and nothing
about whether the gap had been closed elsewhere, so a reader could not tell
"not covered" from "covered somewhere you cannot see". An audit of v278 called
that an evidence gap rather than a defect, which is exactly what it was.

`harness/MP4-ATTESTATION.txt` is that job's answer, and `RELEASE.md` now
carries an `mp4 (H.264)` line computed from it. **The tree hash in the
attestation must match the one the release froze** — evidence about different
code is worse than no evidence, because the seal would then assert coverage it
does not have. Three outcomes, all stated rather than implied: verified, STALE,
or NOT VERIFIED with the command to fix it.

It never blocks a release. Whether an unverified MP4 path is shippable is a
product decision; the seal's job is to state the fact.

The file is excluded from BOTH tree-hash lists (`release_run.GENERATED` and
`run_harness.sh`'s `_tree_files`) for the same reason `RELEASE.md` is: it names
a hash, so including it would make writing the evidence change the thing the
evidence is about. The two lists must stay identical — that is the v221 defect.

### Environment traps, in the order they will bite

* `apt-get update` fails outright until the blocked nodesource repo is moved
  aside: `mv /etc/apt/sources.list.d/nodesource.list /tmp/`. Then install
  postgresql, start it, create the `skribl` role and database.
* `pip install -r constraints.txt --require-hashes --break-system-packages`, and
  `python3 -m playwright install chromium`.
* **PILLOW IS NOT IN requirements.txt AND THREE SUITES NEED IT.** `verify_cssplit`
  and `verify_smudgeblur` CRASH without it; `verify_sizeclass` is worse — it
  reports 81/82 with a single tidy failure while **eight of its assertions
  silently do not run**, which is the shape of problem this whole harness exists
  to refuse. With Pillow it is 89/89. A v273 release run reached batch 42 of 44
  before these three sank it. `pip install Pillow`.
* **PLAYWRIGHT MUST MATCH THE CHROMIUM BUILD ON DISK.** Check with
  `ls /opt/pw-browsers` (or wherever `PLAYWRIGHT_BROWSERS_PATH` points): build
  1194 wants playwright 1.56.0, and 1.62 fails to launch with an executable-not-
  found error that reads like a missing browser rather than a version mismatch.
* **THE INTERPRETER MUST BE THE PINNED 3.12, and a container's default may not
  be.** `verify_docs.py` fails the run outright when `.python-version` and the
  running interpreter disagree — deliberately, because evidence produced on a
  different interpreter from the deployed one describes nothing. If the default
  `python3` is not 3.12, build a venv from the 3.12 that is installed and put it
  on PATH ahead of everything for the whole run.
* **THE SEAL AND CI DO NOT TEST THE SAME THING, and CI's mode is the stricter
  one.** `release_run.py` runs its batches SEPARATELY, each getting a fresh
  server and database on a quiet machine. CI runs every suite in ONE invocation
  on a contended two-core runner. (Both counts were typed here once and both
  went stale — the suite count was caught by `verify_docs`, the batch count was
  not, because nothing checks it. `release_run.py --dry-run` prints them.) Anything sensitive to write contention or to
  cross-suite state therefore passes the seal and fails CI — which is exactly
  what happened: a 500 under SQLite lock contention (v274) failed main's sqlite
  job on one push and passed it on the next, with the bug unchanged in both,
  while v273 sealed green TWICE on this box. **A green seal is not a prediction
  that CI will be green — and a CI failure that clears itself on the next push
  is not thereby a flake.** If a suite fails only in CI, do not
  reach for "flake": reproduce it by loading the machine —
  `for i in $(seq 1 12); do (while :; do :; done) & done` — and it will very
  likely fall over locally too.
* **A suite's subprocess servers send stderr to DEVNULL, so the traceback you
  need is thrown away.** `verify_review.py`'s `server()` helper does this. When
  a request 500s inside a suite-launched server, patch that redirect to a file
  before theorising — the v274 bug named its own cause in the first traceback
  captured, after the wrong writer had been suspected on reasoning alone.
* **PostgreSQL: if `verify_postgres` SKIPS, the seal is weaker than the last
  one.** It wants `postgresql://skribl:skribl@127.0.0.1:5432/skribl` (override
  with `SKRIBL_PG_DSN`), and it skips rather than fails when it cannot connect —
  so a run can go green having never tested the multi-process behaviour SQLite
  cannot establish. `pg_ctlcluster 16 main start`, then create the role and
  database, then confirm the suite reports 20/20 rather than SKIPPED.
* **PostgreSQL dies between tool invocations.** Start it in the SAME invocation
  as whatever needs it, and check `pg_isready`.
* **Background processes do not survive between invocations**, and one
  invocation is capped well below the ~25 minutes a full aggregate needs. That is
  why `release_run.py` checkpoints:

      python3 harness/release_run.py --restart --budget 160   # first slice
      python3 harness/release_run.py --budget 160             # repeat ~5x

  It re-verifies the frozen tree hash on every resume and aborts if the tree
  changed, so the guarantee is stronger than a single-process run. The checkpoint
  is deleted on completion.

### Eight suites could fail silently — fixed at this seal

`run_harness.sh` takes ok/FAIL from a suite's **exit code**. Eight suites
(`verify_amber`, `verify_audio`, `verify_dots`, `verify_feed`, `verify_fix`,
`verify_lib`, `verify_privacy`, `verify_seam`) printed their failures and then
exited 0. The runner reported them as `ok`, and a full aggregate would have been
recorded as PASS with a failed assertion inside it. `verify_docs` was the ninth,
caught in the act: it printed `32/33 passed FAILURES: ...` and the runner said
`ok`.

All nine now end with `sys.exit(1 if bad else 0)`.

**This is very likely what the `verify_amber` "flake" earlier in the session
was.** It was reported as a crash by a parser bug that has since been fixed, and
it would ALSO have been reported as ok had it merely failed. Two independent
reporting holes over the same suite. Do not trust any green run recorded before
this seal for those eight suites.

The lesson generalises: **a suite's failure has to travel through the channel the
runner actually reads.** Printing it is not reporting it.

### The next step, and the honest distance

**THE JS TARGET IS MET. This section argued for years that it could not be, and
that argument is over.** `verify_jsstrip.py` asserts the player reaches the
153,600 B target after the serve-time strip, with room to spare, and
`verify_player_isolation.py` holds the ratchet below it. Run either for the
number; it is not typed here, because every previous number in this section
outlived the tree it described by dozens of releases.

How it was won, and why the old plan was the wrong plan:

* **Self-contained IIFEs** — `editor_export`, `editor_post`, `editor_menu`.
* **Wiring extraction** (move STATEMENTS, leave functions and state) — both
  drawers: `editor_music`, `editor_photo`.
* **The carves — there are NINE, not the four this file used to name.**
  `editor_draft`, `editor_draw`, `editor_export`, `editor_menu`,
  `editor_music`, `editor_photo`, `editor_post`, `editor_shapes` and
  `editor_tune` are all absent from the player. Pad loads every one; Flip loads
  only `editor_shapes`; the player loads none. `verify_player_isolation.py`
  reads that list OFF DISK now rather than from a hardcoded tuple of four, so
  five of them were unguarded until v273 and a tenth would be covered the day
  it lands.
* **The serve-time comment strip** — `skribl/jsstrip.py` removes comments from
  the RESPONSE; the files on disk keep every word. This is what closed the gap,
  and it moved no source at all.

**The plan this section used to prescribe was function relocation, and it was
never executed.** It held that shared paths NAME the editor-only functions, so
moving them means dependency inversion rather than relocation — and that even
moving all of them still would not reach the target. Both statements were true
of the tree they were measured on. Neither is now the binding question, because
the strip got there without moving a function. The AST tool built to de-risk
that relocation (`harness/tools/refgraph.js`) was DISPROVED — it fails its own
superset gate and would move the four functions the v132 attempt got wrong. The
v132 failure was load order, not classification. Read `docs/REFACTOR-v132.md`
before planning anything here.

**WHAT IS ACTUALLY OUTSTANDING IS CSS, NOT JS.** `verify_player_isolation.py`
carries a `CSS_TARGET` and the player's stylesheet is well above it, under a
ratchet (`CSS_RATCHET`) set far looser than the current value. That is the open
size question, and it is a different problem from the one this section spent its
life on: `player.css` is generated by `harness/tools/cssgraph.py`, so the lever
is the classifier, not a carve. See the CSS-ratchet decision under "Decisions
that are the user's" — the ratchet's slack is an owner call.

**The rule that governs all of it:** a binding declared in an editor-only file
does not exist on the player, so any player code touching it throws. Wiring moves
because nothing names it; state and shared functions cannot. Ask which direction
the reference runs.

### Before touching the loop engine

The isolation fixture carries real audio and asserts playback through an analyser
tap. Keep it that way. A silent fixture made Chrome's coverage profile report
every loop-building function as unused, and acting on that would have shipped a
player that cannot play music — with the suite calling it green.

---

**Read this file, `DECISIONS.md` and `ARCHIVE-README.md` before changing
anything.** The per-version narrative lives in `docs/HANDOFF.md` and in git
history. Everything below was verified by running it, not by reading the code.
(Historical sections below narrate older work; the numbers in prose are that
era's, not this build's.)

---

## What this is

Skribl is a browser drawing/animation tool — **Pad** (records a drawing and
replays it with its timing), **Flip** (frame-by-frame animation) and a
read-only **Player** — packaged as a Flask blueprint to drop into a social
platform.

    SKRIBL_VERSION   see skribl/core.py — the archive name derives from it.
                     This line used to hand-type it, and read v191 while the
                     code said v211: four releases stale, in the file whose
                     whole opening section is about numbers going stale
                     silently. Read the constant.
    client assets    app.js / flip.js / styles.css / flip.css and lib/ — one
                     continuous line of work; the per-version story is in
                     docs/HANDOFF.md and git history
    harness          see harness/RELEASE.md — the count is generated, and a
                     hand-typed one is exactly what drifts
    migrations       6 Alembic revisions
    last run         see the stamped stanza below — it is generated, and a
                     hand-typed total is exactly what drifts
    tree hash        see the generated stanza below — NEVER typed here
                     (a hand-typed hash in this file is what made an
                     external reviewer distrust the whole archive)

**Release evidence lives in `harness/RELEASE.md`** — every suite on disk,
on one frozen tree, generated by `harness/release_run.py`. The stanza below is
narrower: it records only the LAST `run_harness.sh` invocation, which is a batch,
not the release. When the two disagree it is because they answer different
questions; RELEASE.md is the one to quote.

**The last recorded run** — generated by `stamp_docs.py`, never typed:

<!-- HARNESS-COUNTS -->
**PASS WITH SKIPS — 4610 assertions across 98 reporting suites (99 on disk, 1 skipped), none failing** on sqlite as of v281 (tree `553f7ecfe525`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_mp4.py. A skipped suite contributes zero assertions and is not evidence of coverage.
<!-- /HARNESS-COUNTS -->

**The deployed runtime is pinned to Python 3.12** (`.python-version`, mirrored
by `PYTHON_VERSION` on the Render service). `constraints.txt` is a hash-locked
cp312 environment and the recorded evidence is produced on the same interpreter,
so the numbers in `harness/RELEASE.md` describe what production runs rather than
a configuration nobody has. Render's default Python depends on when the service
was created and moves over time; unpinned, the build resolves `requirements.txt`
fresh and runs versions no assertion ever exercised. `verify_docs.py` fails if
the pin, the lock and the interpreter running the harness disagree.

**Verify the archive first, in one command:**

    cd skribl-v*
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N

    # v224: the expected count is no longer TYPED here at all. It used to be,
    # with a note explaining that you should compare against the manifest
    # rather than against the number — which is an odd thing to write beside a
    # number, and it went stale anyway every time the file set changed. The
    # manifest already states its own size; asking it is strictly better than
    # asserting it. `verify_docs.py` still checks any count that IS typed
    # elsewhere against SHA256SUMS.

---

## The live demo

`skribl-live-demo.onrender.com` — a Render Starter web service ($7/mo) deployed
from GitHub (`MrBlood/skribl-live-demo`, branch `main`), backed by a paid
Postgres Basic instance ($6/mo), running the `inline` media backend.

**The deployed code can lag this tree** — Render deploys from `main`, so
anything merged is live after its build finishes and anything unmerged is not.
Check the version label in the app footer before diagnosing anything.

**Two operational facts learned the hard way:**

* A free Postgres instance expired mid-session and every `POST /api/skribls`
  returned 500 with `failed to resolve host 'dpg-...'`. It looked exactly like
  a broken client, and three client-side theories were chased before a server
  log settled it in one line. **Check the server log first.**
* **HISTORICAL — this is the incident that caused the pin, not the current
  state.** Render was building on **Python 3.14** while `constraints.txt`
  carried cp312 hashes, so production resolved `requirements.txt` fresh and was
  NOT running the versions the harness tested. **Fixed by pinning:**
  `.python-version` holds 3.12 and `PYTHON_VERSION` mirrors it on the Render
  service — see "The deployed runtime is pinned to Python 3.12" above, which is
  the current statement. `verify_docs.py` fails if the pin, the lock and the
  interpreter running the harness ever disagree again.

  Two statements about the runtime appeared in this file at once, one current
  and one historical, with nothing marking which was which. An external review
  flagged it: *"Both statements cannot describe the same current deployment."*
  It was right, and the fix is the label rather than a change of fact — CURRENT
  STATE and PAST INCIDENTS must be distinguishable at a glance.

---

## Decisions that are the user's, not the assistant's

**The migration chain collapse is CLOSED.** It required that no database had
run v135-v141. The live Postgres has run at least through `f0a3d81b47e2`. Do not
propose collapsing it again.

**The deploy now runs `alembic upgrade head` — via the RENDER START COMMAND,
not the Procfile (v270).** v267 wired the migrate-then-serve command into the
Procfile and declared the drift closed; **Render does not read Procfiles**
(that is a Heroku convention), so migrations still never ran on deploy, which
the v269 outage proved when the db rate limiter met a `skribl_rate_events`
table the stamp had promised and nobody had built (DECISIONS v270). The
authoritative setting is the Render dashboard's **Start Command**:
`python -m alembic upgrade head && gunicorn app:app`. The Procfile carries the
same line for Heroku-convention hosts and local reference, but changing it does
NOT change the deploy. `skribl/migrations/env.py` also runs a pre-flight that
recreates a baseline table a stamped-over database is missing, so the chain can
run at all on a database whose stamp lied.

**THE PAD/FLIP GUARD ASYMMETRY IS DELIBERATE.** Pad confirms before leaving for
Flip; Flip does NOT confirm on the way back. That is not an oversight and should
not be "fixed". Pad's autosave keeps strokes but NOT media — photo and audio
bytes never fit in localStorage, which is why the status pill reads *"Saved
without media"* whenever either is attached — so leaving Pad loses the photo and
the music. Flip persists pages, music and the background image, so a confirm
there could only ever be a false alarm. Pad's guard fires on
`photoBg || currentAudioBuffer`, not on "there is a drawing": a confirm that is
usually wrong is one people learn to dismiss unread, and then it fails on the
occasion that mattered.

**360px IS THE DESIGN TARGET; 320px IS THE SAFETY NET.** 360 must work properly
on one row — it is a very common Android width, so a two-row bar there is not a
rare fallback. 320 is Display Zoom on a modern iPhone, an accessibility setting
rather than a legacy device, so it must degrade rather than break. The two
surfaces degrade DIFFERENTLY and both are correct: Pad wraps, Flip scrolls
(`flip.css` sets `flex-wrap: nowrap; overflow-x: auto` below 560px on purpose).
`verify_layout.py` asserts that every control stays REACHABLE, not that a
particular mechanism is used — an earlier version asserted no-overflow and would
have failed Flip's scroll row as though a deliberate decision were a defect.

**EVERY REPAINT MUST GO THROUGH `makeStrokeCompositor`.** A see-through stroke
painted segment by segment stacks its own overlaps at every captured point —
measured, one 22%-alpha stroke: alpha spread 153 painted directly against 50
composited once. `selRepaint` was the last repaint in the editor passing the raw
`drawDot`/`drawLine` painters straight to `replayTimelineToCanvas`, and
`setTool()` calls it on EVERY tool change, so simply picking the eraser re-beaded
the whole canvas. Preview, playback and all three export paths already routed
through the compositor. If you add a repaint, route it through the compositor or
branch on `strokeLayersOn()` — never neither.

**THE CANVAS LOCK AFTER A TAKE IS DELIBERATE — do not "fix" it.** When a take
ends, `updateCanvasLockCue()` sets `cursor: not-allowed` and the canvas is not
drawable until you Record again or Clear. This looks like a dead end and is not:
it is the multi-take model, and `endRecordingTake()` says so in a toast —
*"Take saved — Record again to add more to this Skribl, or Play to preview."*
An external design pass in v215 read the lock as a bug and came close to
recommending its removal, which would have turned every stray tap after a take
into recorded timing. The round-trip through Record is the cost of knowing when
the clock is running. If it is ever revisited, the narrower change is to let
drawing on a locked canvas START the next take — same model, no round-trip —
rather than removing the lock.

**Visibility defaults to `unlisted`,** and the migration backfilled every
existing post as `unlisted`. The platform must send `"visibility": "public"`
explicitly or posts appear in no feed, silently. Leave the backfill alone.

**v140's recall framing is confirmed correct** — no database ran the v140 copy
of `f0a3d81b47e2` at `BATCH = 500`.

**The CSS ratchet decision is STILL OPEN, and the restatement it was given last
time has itself gone stale — read the numbers off the suite, not off this
paragraph.** It was long carried as "set at exactly the current size, so it has
no headroom by construction". That was true when `player.css` did not exist and
the player linked the whole of `styles.css`. It does exist, so `CSS_RATCHET` sits
well above what the player actually links and the mechanism has real headroom —
the same inert state the JS ratchet was in when it was reading gzipped lengths,
arrived at a different way.

**The size of that headroom has changed twice since anyone wrote it down here,
so this paragraph no longer quotes it.** `verify_player_isolation.py` prints the
ratchet, the linked total and the target on one line; run it. Note also that the
linked total has GROWN since the restatement, which is precisely what an inert
ratchet permits and why the decision matters.

The decision itself is unchanged and is the owner's: set the ratchet at today's
value (the convention the JS ratchet and the comment beside `CSS_RATCHET` both
follow) or at something with deliberate slack. Leaving it alone has now made it
staler twice, which is worth knowing when deciding.

---

# ============ HISTORICAL NARRATIVE FROM HERE ============

**Everything from this line down to "Known-open, in the order worth doing" is a
RECORD OF HOW THE TREE GOT HERE, not a description of how it is now.** Section
headings in this band are written in the tense of the release that produced
them: "most of it still to do", "will not extract", "the newest feature" were
all true once and several are not now. Numbers in this band are that era's.

The parenthetical warning at the top of this file said as much and was not
enough — three entries in the KNOWN-OPEN list, which is not even in this band,
still described fixed bugs as open and cost a session a day. So this divider is
loud on purpose. **If you want the current state, read above this line and the
known-open list below it; if a claim down here matters, verify it against a
suite before acting.**

## What was built in v142-v179

Client work, all covered by suites that drive a real browser:

* **Flip sends a typed title and caption** — it hardcoded `'Flip animation'`.
* **Stylus pressure** on both editors, scaled into the existing per-point
  `size` rather than a new field the player cannot read.
* **Export sheet**: Size/Pages had NO CSS at all; plus a Loops control, because
  video silently exported two passes.
* **Help drawer search** across ~50 entries, with derived section counts.
* **Your Skribls** (`lib/posted.js`) and **Report a problem** (`lib/report.js`,
  captures JS errors — it loads first so it can see failures in the editors).
* **Canvas presets shared by both editors** (`lib/canvassizes.js`); Pad used to
  inherit the viewport, so a drawing's shape depended on window width.
* **Styled tooltips** (`lib/tooltip.js`) and **first-use hints**
  (`lib/hints.js`) — native `title` cannot be styled at all.
* **A pixel-snapped canvas grid** with a sub-grid at every size.
* **Move artwork** — see below. Its transform bar now states its own
  geometry, and its offset readout accepts typed coordinates.

---

## Move artwork as it landed (historical) — what it set up

`Artwork` is a TOOL in Flip's tool shelf as of v226 — it was in the page bar
until then, which is where the paragraphs below were written. Picking it enters
a mode where dragging the canvas moves the whole page's drawing. The page bar is
REPLACED by a transform bar (offset readout, This page / & after, Reset, Done).
Escape cancels; Done commits.

Design notes worth keeping:

* It is a PAGE operation, so it lives with Copy/Hold/Delete, not with
  Pen/Eraser — and the tool row is full on a phone anyway.
* **Undo stores the inverse offset, not a snapshot.** A translation is exactly
  reversible. Not bit-exact (float), so `verify_move.py` asserts to 1e-6.
* **`actionLog` records the order of undoable actions** so undo after
  "draw, move" undoes the MOVE. Flip's undo otherwise just pops stroke groups.
* The offset applies to a working COPY of the original points, so a long drag
  cannot drift and Reset lands exactly.
* The drag is measured in canvas units (`CW / rect.width`), not screen pixels.

**Selection — moving PART of a drawing — reuses all of this**: the mode, the
bar, the readout, Reset, Done, Escape and the undo mechanism. Only hit-testing
and a selection overlay are new. That was the argument for building the
whole-page move first, and it is the natural next feature.

---

## Closed since the v179 archive was cut

* **`[hidden]` works everywhere now.** `styles.css` carries
  `[hidden] { display: none !important; }`. The UA rule loses to any author
  rule, so `el.hidden = true` drew nothing for 380 elements on Flip and 366 on
  Pad — the page bar rendered 55px tall throughout Move artwork's life while
  reporting `hidden === true`. Four one-off `.thing[hidden]` rules had been
  written before anyone looked for the general case.
* **Segmented controls state a height.** `--seg-h` was declared four times and
  read nowhere, so a `.seg` inherited its height through `font: inherit` and
  followed the VIEWER'S font: 20px headless, 23px on the owner's Mac, while
  `.pb` matched exactly. `.seg` now reads `var(--seg-h)` with NO fallback, so
  an unmeasured control keeps `auto` and opting one in is deliberate.
  `.mb-scope` and `.mb-offset` are 30px; the export segs 32px.
* **The offset readout takes typed coordinates.** Click it, type `40, -12`.
  Same moveDx/moveDy as a drag, so the same Reset, Done and single undo entry.
* **Skribl no longer steals a host application's homepage, and `docs/INTEGRATION.md`
  is now a real guide.** Both came out of the first actual DROP-IN TEST: a
  throwaway Flask host app, built from the docs, that is not `app.py`.
  The blueprint registered `GET /` unconditionally — a second copy of the Pad
  editor, there so the standalone demo had a landing page. Flask resolves
  duplicate rules by registration order and the blueprint registers first, so
  **mounting Skribl silently replaced the host's front page.** No error. It is
  now `create_blueprint(index_route=False)` by default; `app.py` opts in.
  Two more integration facts that were true but undiscoverable: a host's
  `db.create_all()` creates **nothing** without
  `skribl.models.attach_to_metadata(db.metadata)` — no tables, no error — and
  `docs/INTEGRATION.md` was a v98–v136 planning record that opened by admitting
  its own signature was obsolete, while `README.md` pointed integrators at it.
  The plan is preserved in git history; the guide is rewritten
  around a copy-pasteable example that was executed, not imagined.
  `harness/verify_integration.py` (no browser, seconds; count in RELEASE.md) pins all
  of it, including the negative controls — install a visibility policy, prove it
  changes the outcome, clear it, prove the default returns.
  One limitation was DECLARED rather than silent: the feed filters
  `visibility == 'public'` in SQL and never consults the host policy, because a
  Python predicate over a keyset-paginated query would break the pagination — a
  policy-refused post could appear in the feed as metadata (no payload, no
  image). **v224 built the `feed_filter` seam that paragraph asked for**: a host
  contributes a SQL predicate the query composes, so authorization pages
  correctly. It is a seam and not an automatic fix, and both directions are
  pinned by `verify_hostseams.py` — without a filter the feed still lists every
  public post, which is correct where a policy only restricts private and
  unlisted. Install one if your policy can deny a PUBLIC post.
* **Loop trim clamping is extracted to `lib/looptrim.js`, and it found a second
  real bug.** The 20-second cap was a named constant on Flip
  (`MAX_LOOP_SECONDS`, nine uses) and a **bare `20` on Pad, eight times, with no
  constant in the file** — so changing the cap meant one edit on one surface and
  eight on the other, with nothing failing if the second was missed.
  **Flip re-clamped the cap inside `updateTrimUI`**, with a comment calling it
  "the single choke point ... so the <=20s invariant can't be bypassed".
  **Pad had no such line**: it enforced the cap on drag and nudge ONLY, so a
  loop arriving any other way — a load, a draft restore, a re-add — kept
  whatever length it came with, and travelled in the payload. Measured: a 60s
  loop through `updateTrimUI` stayed 60s on Pad and became 20s on Flip. Pad now
  has the same choke point and both read the shared constant.
  The clamp rule itself existed in **six copies** across the two files, in two
  behaviours: `'constrain'` (the dragged handle stops at the cap) on the main
  track, `'slide'` (the OTHER end is pushed, so the window slides) on the zoom
  track and nudge. **Pad and Flip are identical about this, path for path**, so
  it is a design inconsistency faithfully duplicated, not drift — the mode is
  now an explicit named argument at each call site rather than hidden inside
  six copies of the arithmetic. Verified against all six transcribed sites
  across 140 scenarios: zero disagreements.
  **The player needed the module too** and the harness caught it: `updateTrimUI`
  lives in `app.js`, which serves the player, so the player threw
  `Cannot read properties of undefined` until `looptrim.js` was added to its
  template. Any client constant `app.js` reads has to load on THREE templates,
  not two.
* **Photo fit geometry is extracted to `lib/photofit.js`, and extracting it
  found a real bug.** Pad drew the background with `drawPhotoFitted`, Flip
  computed it with `photoRect`, and the PLAYER used Pad's copy — three call
  sites, two implementations. They agreed on cover and contain and disagreed on
  the third mode's NAME, which is why the shared partial carried
  `data-fit="{{ 'fill' if kind == 'flip' else 'stretch' }}"`: the markup had
  been bent to fit two vocabularies. flip.js posts
  `fit:(photoFit==='fill'?'stretch':fit)`, so **'stretch' is what the player and
  the database see** — but Flip's restore whitelist was
  `['cover','contain','fill']` and `photoRect` special-cased only `'fill'`.
  **Flip could not read the value Flip writes.** Measured on a 100x50 image
  before the fix, `fit='stretch'` returned `[-204,0,1224,612]` — byte-identical
  to cover — while `'fill'` returned `[0,0,816,612]`, and the fit row showed no
  active button at all. The lib treats `'fill'` as an alias of `'stretch'`, and
  Flip normalises at both entry points, so the value round-trips. Neither
  surface's PERSISTED vocabulary was changed: that is a decision about live
  data, not a refactor. The template conditional and the split vocabulary are
  still there, deliberately — see the open question below.
  Verified behaviour-preserving by comparing the lib against BOTH pre-extraction
  implementations across 405 combinations of size, canvas, offset, zoom and
  fit: zero disagreements. `lib/photofit.js` loads on the editor, Flip AND the
  player — the player draws photos through `app.js`, so omitting it there would
  have left viewers a blank background.
* **`lib/colorselect.js` is now covered by `verify_parity.py`.** It is the
  fifth shared-controller extraction (after `eyedropper`, `recentcolors`,
  `segslider`, `smoothing`) and it entered the archive with no parity
  assertions naming it. The suite already asserted the BEHAVIOUR it
  implements — hex validation, case normalisation, exactly one active swatch,
  on both surfaces — and all of that still passed when Flip was given back its
  own private copy of the logic. Behavioural parity says the copies agree
  today, not that there is one copy. Nine assertions now pin the extraction
  itself: one module, one URL including its content hash, one implementation,
  and — the load-bearing one — each editor's setter is spied on to prove it
  actually CALLS the module. Only that last assertion caught the re-inline;
  `verify_ux.py`'s source grep for `classList.toggle('active'` passed 130/130
  against a copy that merely wrote `classList["toggle"]("active"`.
* **The loop magnifier is NOT unstyled** — a claim made and withdrawn this
  session. `app.js` injects its CSS at runtime, including the
  `position: relative` the seg pill needs. Grep both stylesheets AND the
  injected `<style>` before believing a component has no rules.

## Closed after the v184 dotfix

* **The move-offset field summoned the wrong keyboard.** `#mbOffsetInput` takes
  BOTH coordinates in one box (`"40, -12"`) and declared `inputmode="numeric"`,
  which on a phone offers digits only — no comma, and on most keyboards no minus,
  so a negative offset could not be typed at all. `decimal` is not the fix; that
  adds a decimal POINT, not a separator. It is `text` now. The parser needed no
  change: `parseOffsetEntry()` already accepts a comma or a space between the two
  numbers plus a leading minus and decimals, and `verify_move.py` now asserts
  both halves — the attribute, and that the parser takes every form the fuller
  keyboard allows while still rejecting junk. Mutation-tested: restoring
  `numeric` fails the assertion.

* **The play scrubber's shape is no longer unverified — and it was correct.**
  It had never been seen rendered. Driving Pad through draw → stop → play and
  measuring the real shown state gives, at 1280x900 and at 390x844 alike: inset
  **24px at both ends, exactly `--r-frame`**, flush to the canvas bottom (gap 0),
  spanning wrap width less 48, radius reaching past half the height so the ends
  read round. Nothing needed adjusting. `verify_scrub.py` (17) pins it, and its
  FIRST assertion is the negative control: at rest the bar is genuinely not laid
  out, because `positionScrub()` returns early on `hidden` — so an element forced
  visible measures 0 wide and reads as catastrophic misalignment that is entirely
  an artifact. A gate assertion also refuses to compare insets until a real
  replay has actually shown the bar; a symmetric zero is a broken probe, not
  agreement. Mutation-tested: zeroing `_inset` fails four assertions.

* **`positionPlayScrub` does not exist.** The function is `positionScrub()`
  (`app.js`). The name was wrong in the `styles.css` comment that points at it
  and in the handoff, so anyone grepping for it found nothing. Corrected.

* **`verify_deletion_foundation.py` is in `harness/` now, and it crashed on
  arrival.** It resolved the repository root with `os.path.abspath(".")`, but
  `run_harness.sh` does `cd $ROOT/harness` before invoking a suite — so `from app
  import ...` raised `ModuleNotFoundError` and the suite reported zero assertions
  rather than eight. It anchors on `__file__` now, matching `verify_storage.py`.
  8/8 on PostgreSQL with the local media backend; it needs BOTH
  `SKRIBL_MEDIA_BACKEND=local` and a Postgres `DATABASE_URL`, and skips cleanly
  without them.

* **Hand-typed counts that had drifted are gone rather than corrected.** Three
  documents quoted three different line counts for `app.js` and none matched the
  tree; four places hand-typed the suite count. Replacing a stale number with a
  fresh one only resets the clock, so they now point at `wc -l` and at
  `harness/RELEASE.md`. `verify_docs.py` caught the suite counts by itself the
  moment the two new suites landed — that check works, and it is why this list
  can be trusted where prose cannot.

* **SQLite declared the foreign key and never enforced it.** `PRAGMA
  foreign_keys` defaults to OFF per connection, so revision `c7e1a5f04b93`'s
  `skribl_post_media.post_id -> skribl_posts.id` ON DELETE CASCADE was written
  into the schema and ignored. Deleting a post left its association row behind,
  `sweep_orphans` then read the media as still REFERENCED, and the bytes were
  never reclaimed — the exact leak the constraint was added to close, still open
  on the one engine the assertion had never been run against. It surfaced only
  because `verify_deletion_foundation.py` joined the aggregate, which runs on
  SQLite; standalone it had only ever run on PostgreSQL, where it passes 8/8
  because PostgreSQL enforces the constraint natively.
  **Access was never exposed** — `/media/<key>` authorises through an EXISTS join
  to the post, so a deleted post's media is refused (404) whether or not the
  orphan survives. It is a data-integrity and storage leak, not a security hole.
  `models.enable_sqlite_foreign_keys()` now sets the pragma, installed from
  `init_skribl()` so a process that merely imports Skribl without mounting it is
  untouched. Measured both ways: cascade fires with it, orphan survives with
  `SKRIBL_SQLITE_FOREIGN_KEYS=0`.
  **Scope worth knowing before deploying on SQLite:** the pragma is a property of
  the CONNECTION, so there is no way to enforce Skribl's foreign keys and not the
  host's. A host whose own data violates a constraint it declared will now get an
  error where it previously got silence. That is the correct outcome and it is a
  behaviour change; the env var is the opt-out.

* **A generated aggregate now survives being interrupted.** A full run needs
  ~25 minutes, longer than some environments allow in one invocation, and
  background processes do NOT reliably survive between invocations here —
  ARCHIVE-README claims they do, and a run killed after batch 1 proved otherwise.
  The tempting workaround is running batches by hand and adding up the totals,
  which is the hand-typed number this project keeps abolishing. `release_run.py`
  checkpoints after every batch instead (`--budget`, `--restart`; state lives
  OUTSIDE the tree, or writing it would change the hash of the tree it describes)
  and re-verifies the frozen tree hash on every resume — so an edit made between
  invocations aborts the run exactly as an edit between batches does. The
  checkpoint is deleted on completion, or the next release would silently resume
  a finished one.

## Player extraction, first cut (historical) — the target has since been MET

**Do not read `verify_player_isolation.py` going green as "the player is
extracted."** Its Half B assertions are RATCHETS: they hold the ground already
won and state the target beside each number. Half A (playback) is the real
regression net and must never go red.

Where it stands, all measured:

* **Down 56,727 bytes.** (SUPERSEDED — the target has since been met; see "The
  next step, and the honest distance" above, and run `verify_jsstrip.py`. The
  three figures in this bullet are v199's and are kept for the shape of the
  climb, not as current values.) A player page downloaded 329,159 bytes of
  JavaScript before that session and 272,432 after. The target is 153,600.
  **v199: 155,843 B**, after the serve-time comment strip — 2,243 over the
  target at the time, and the figure the ratchet was then set at. `verify_player_isolation.py`
  measures `r.body()`, the decoded response, so this is what a browser parses;
  the wire figure is 48,309 B and must never be quoted as the first number.
* **What moved:** `editor_export.js` (the PNG/GIF/WebM encoders and share-card
  builder) and `editor_post.js` (the post composer), lifted VERBATIM out of
  `app.js` and loaded only by `skribl_editor.html`. Not rewritten — a second
  implementation would drift, and this project has been bitten by exactly that.
  Both were self-contained IIFEs; the only name crossing the boundary was
  `drawPhotoFitted`, defined AND used inside the moved region (the two hits
  outside it are comments). `verify_exportui` 45/45, `verify_exopts` 26/26 and
  `verify_posted` 34/34 all still pass, and the isolation suite's own fixture
  posts through the editor, so the moved composer is exercised on every run.
* **Ground truth, from Chrome's coverage profiler** rather than from reading:
  of 284 named functions in `app.js`, a player page executes **78**. The player
  was calling `initExport()` and `initPostComposer()` on every shared link to
  wire up controls it does not have.

**Why the next cut is not another line-range move.** The two sections that came
out were the only ones that could. Leak analysis on the other candidates —
each name defined inside a region and referenced outside it:

    more-tools drawer     498 lines   21.7 KB   21 names leak
    overflow menu         329 lines   13.4 KB    2 names leak
    draft save/autosave   336 lines   15.4 KB    9 names leak
    music upload + trim   791 lines   34.2 KB   34 names leak
    loop preview/seam     286 lines   10.5 KB    3 names leak

The music drawer alone shares 34 names with the rest of the file. Moving these
means separating shared STATE (`audioEl`, `trimStart`, `strokes`, the canvas
handles) into a core module both halves import — real decoupling, not a cut.
The overflow menu (2 names) and loop preview (3 names) are the next smallest
and the sensible next targets.

**A trap on the audio path.** The coverage above was taken with a fixture that
has NO AUDIO, so every loop-building function reads as unused. Moving audio code
on the strength of that measurement would break playback for every Skribl with
music, and the isolation suite would not catch it, because its fixture is silent
too. Add audio to the fixture BEFORE touching anything under
"Sample-accurate live loop engine".

* **The runner reported every failing suite as a crash.** `run_harness.sh`
  matched a summary with `^[0-9]+/[0-9]+ passed$`, anchored at both ends. Suites
  do not agree on one format — several print
  `32/33 passed  FAILURES: <what failed>` on a single line — so the anchor
  rejected it, the runner concluded NO SUMMARY, and the suite was reported as
  "crashed before reporting": the one classification that says nothing about
  what went wrong. A failing suite and a suite killed mid-run were
  indistinguishable. `verify_amber` was written off as a flake on exactly this
  evidence; it may have been a real assertion failure, and that can no longer be
  recovered from the logs. The trailing anchor is gone; the leading one stays, so
  a mid-sentence "1/2 passed" still cannot be mistaken for a summary. **If a
  suite reports ERROR now, it really did crash.**

## Player extraction — second and third cuts

Cumulative, all measured by `verify_player_isolation.py`:

    329,159 bytes / 7 globals   unsplit
    272,432 / 6                 editor_export.js + editor_post.js
    261,707 / 5                 editor_menu.js

`editor_menu.js` holds the overflow menu, clear-all, the sheet gestures and the
help drawer. The player has none of those and was running `initClearAllMenu()`
and `setupSheetGestures()` on every shared link to attach handlers to elements
it never paints. `openHelpDrawer` is no longer reachable there.

**The obvious boundary was wrong.** Cutting the whole span from the "Overflow
menu" comment to the next section would have swallowed `initBrandFit()`, whose
inner `fit()` the PLAYER executes — it is why the header brand collapses
correctly on a shared link. Chrome's coverage profile reports function NAMES, so
a nested `fit()` is indistinguishable from any other until you look at where it
is defined. The cut stops before it. `verify_help` 61/61, `verify_ux` 130/130,
`verify_pages` 44/44 all still pass, and `verify_seam` still totals 2485
editor-only lines against 2467 before any of this — nothing became
player-reachable, the code only moved.

**The loop-preview region is NOT movable, despite looking like the next easy
cut.** Its leaked names are real calls, not guarded ones: `stopLoopPreview` is
called from four places outside it (1237, 1450, 2520, 4166) and `playMusicLooped`
from the editor replay path, and `stopLoopPreview` is in the player's executed
set. Moving it would throw on the player. Compare `closeMenu`, the only name
leaking out of the menu region, whose one external call site already reads
`typeof closeMenu === 'function'` — inert on the player instead of fatal. **That
guard is the difference between a movable region and one that is not**, and it is
worth checking for before planning any further cut.

## Why the music drawer would not extract (historical) — superseded below

The region has **64 top-level names, 36 of them referenced by code the player
executes.** Not all state: `audioEl`, `trimStart`, `trimEnd`, `audioCtx`,
`currentAudioBuffer` and `loopCrossfadeMs` are genuinely shared, but so are
`drawWaveform`, `drawZoomWaveform`, `updateTrimUI` and `updateZoomHandles` —
**and those are called from `loadSkribl`, which the player runs.** The player is
drawing waveforms into canvases it never paints.

That is the real obstacle, and it is not a file boundary. **`loadSkribl` calls
editor UI unconditionally, in player mode as well.** So the drawer cannot be
moved while a shared function reaches into it. The unblocking change is to guard
those calls the way the rest of `app.js` already guards
(`document.body.classList.contains('player-mode')`), after which the drawer's
dependency on shared code is one-directional and the cut becomes possible.
Cutting first and guarding later gets a player that throws.

`showToast` is also declared inside this region and used across the whole file —
a general utility that ended up filed under music. It should move up to the
shared section regardless of what happens to the drawer.

**A caution about the measurement that produced this.** The first pass matched
declarations with `^\s{0,2}(?:const|let|var)`, allowing two spaces of indent. It
swept up locals declared inside IIFEs — `s`, `w`, `data`, `file`, `err` — and
reported 65 names as shared state, which would have made the region look
hopeless. Column-zero matching gives 36. Same failure as the flattened DOM
selector that once invented a "mixed register" grammar problem: a loose pattern
inventing structure that is not there. **Anchor at column zero when asking what
is top-level.**

## Step 7 as it stood then (historical) — shared paths guarded, drawer not yet cut

`updateTrimUI` was never a UI function. It is **the choke point that clamps
`trimStart`/`trimEnd` and enforces the 20s loop cap on load**, and the player
reaches it through `loadSkribl`. The obvious decoupling — a player-mode guard
around the whole function — would have let a shared link play a loop longer than
either editor allows, reintroducing on the player exactly the bug that choke
point was added to fix. It is now split: `clampTrim()` runs on both surfaces,
the DOM half is guarded and null-checked.

`loadSkribl` and `resetMediaForLoad` now separate state from drawer UI. The
player no longer decodes waveforms into canvases it never shows, nor rewrites
button labels for a drawer it does not have. `dragZoomPan` needed nothing — it
is a drag handler for a zoom track the player has no markup for, and
`updateTrimUI` is null-safe now regardless.

**A ratchet was loosened, once, on purpose: 263,000 -> 264,000.** The guards cost
about 1.7 KB. I first wrote that they unlock "roughly 34 KB" — that was the size
of the whole region, claimed before measuring, and it is wrong. **Measured:**

    music region              34,947 B total
      stuck (player calls it) 14,891 B   drawWaveform, showToast, clampTrim, ...
      no outside reference     6,067 B   the drag handlers, validateMusicFile, ...
      top-level wiring        ~14,000 B

The debt is written beside the number in `verify_player_isolation.py`: when the
drawer moves, it must come back below 262,000. **If that line still reads 264,000
with no drawer cut behind it, the prep was never cashed in.** Worth noting the
ratchet fired on the change that set it — the mechanism caught its own author
twice in one session, which is the only real test of whether it works.

**The 6 KB is NOT independently movable, and this is the trap to avoid.** Those
eight functions have no reference outside the region, which makes them look free
to take. But they are called from TOP-LEVEL statements inside it —
`dragHandle(handleStart, true)` at what is now line 2320, `dragZoomHandle(...)`
at 1773, `validateMusicFile(file)` at 2044. Top-level calls evaluate at LOAD, on
the player, so moving the function without its call site throws immediately on
every shared link. Function and wiring have to travel together.

**The recipe, in order:**

1. Hoist the 12 stuck functions and the shared state declarations (`audioEl`,
   `trimStart`, `trimEnd`, `audioCtx`, `currentAudioBuffer`, `loopCrossfadeMs`,
   `audioDuration`) OUT of the region, into a marked shared section above it.
   Shared state can never live in an editor-only file: a binding declared there
   simply does not exist on the player, and any player code touching it throws.
2. `showToast` goes with them — it is used file-wide and only lives here by
   accident.
3. What remains in the region is then wiring plus its own helpers, and moves
   wholesale into `editor_music.js`.
4. Re-measure. Tighten the ratchet below 262,000 or explain why not.

## The editor shell is out of the player template

**31,530 bytes of markup removed** — the player's template went 56,716 -> 25,186 B
and the DOM ratchet reached its target: **0 authoring controls**, down from 8.

Out: the overflow menu, export sheet, post composer and help drawer (422 lines,
and safe to remove precisely BECAUSE the earlier cuts moved their JS into bundles
the player never loads — the markup had nothing left to wire it up), then the
record, post and undo buttons and the music and photo file inputs.

**The stub pattern is what made the controls removable.** `app.js` writes to them
from more than twenty places — `.disabled`, `.hidden`, `.innerHTML`,
`.classList` — so guarding each site would have cost more bytes on every shared
link than the markup it replaced, and would still have missed the next one added.
Instead `_authoringCtl(id, tag)` falls back to a DETACHED element of the same
kind: writes land harmlessly on something nothing renders, reads round-trip. Two
genuine null-crashes still had to be fixed by hand first (`photoInputEl` and the
autosave wiring, the latter rerouted through the `bindEl` helper that already
null-checks and predates the problem).

**The byte ratchet was measuring half the payload.** JS-only. So 31.5 KB of
markup leaving the player was invisible, while the ~700 bytes of guards that MADE
the removal safe registered as a regression and failed the run. A measurement
that sees one half of the payload rewards moving weight across the boundary
instead of removing it. There is now an HTML ratchet beside the JS one.

**Two mistakes worth not repeating.** A regex ending `(?:</\1>|>)` matched a
multi-line `<button>` only as far as its first `>`, orphaning the label and the
closing tag — tag counts went 54 open / 57 close and the template stopped
parsing. Match balanced tags, or count opens and closes. And when that produced a
blank player, `'playerShell' in template` read False and looked like the cause:
it is a red herring, `playerShell` lives in `_skribl_player_controls.html`, which
is included, not inlined.

**The next template target, found by a suite that caught up with reality.**
`verify_review` asserted the player "really does render media inputs" — true and
load-bearing when the player carried the whole shell, false now. Inverting it
surfaced the follow-up: the draw, music and photo TAB PANELS are still in the
player's template, and their `#photoUploadBtn` / `#musicUploadBtn` drop handlers
are the only remaining reason `lib/media_validation.js` (7,130 B) loads on the
player. Remove the panels and the module leaves with them.

## The player is down to a player

    JavaScript   329,159 -> 257,592 B
    HTML          56,716 ->   7,989 B
    total        385,875 -> 265,581 B   (-120,294, 31%)

The tab bar and the draw, music and photo panels are out of the player template
(862 lines -> under 150). That removed 87 elements the player never painted, 44
of which `app.js` dereferenced, and it broke the player four times on the way —
each caught by Half A and fixed at the source:

* **12 load-time listeners** now go through the detached-element fallback.
* **`waveformCanvas.getContext('2d')` at load.** A detached `<canvas>` returns a
  real 2D context, so `drawWaveform` and every `clearRect` downstream work
  unchanged and paint into nothing.
* **Three drag installers take an ELEMENT, not an id**, so the stub cannot help
  at the call site. One guard at each function's entry covers every caller.
* **The photo teardown in `resetMediaForLoad`** mixed state resets with
  unguarded DOM writes; split like the music half.

**`lib/media_validation.js` is off the player** — 7,130 B. Its only callers are
the photo and music drop/change handlers, and both upload buttons and both file
inputs left with the panels. `verify_review` asserts the editors still load it
and the player does not, so the saving cannot quietly revert.

**The ratchet debt is repaid.** It was loosened to 264,000 with a promise to get
back under 262,000; it is 257,592, and the ratchets now stand at 258,000 JS and
9,000 HTML.

**A test that something is ABSENT must match the mechanism, not the word.**
`verify_review` failed on "the player does not load the module" because the
template's comment explaining the absence contains the filename, and a substring
check read the comment as the thing it was looking for. Both checks now match the
`<script` tag. That is the third assertion in that file to encode a fact my
changes made false — and each one pointed at the next target.

## The music drawer's WIRING did move — the earlier "not worth cutting" was half wrong

`editor_music.js`, **14,286 bytes**: the upload and drop handlers, the trim-track
drag installers, the zoom-magnification and fine-tune controls, the remove
button, and the five helpers only they call (`dragHandle`, `dragZoomHandle`,
`dragRangeWindow`, `positionSegSlider`, `validateMusicFile`). Every call site of
those five was inside the moved set, so nothing left in `app.js` names them.

I had written this region off after measuring that only ~5.4 KB of FUNCTIONS were
free. That was true and it was the wrong question. The region is three kinds of
thing:

    declarations   5,115 B   state + element handles — can never move
    functions     18,358 B   mostly reached from loadSkribl — must stay
    wiring        8,717 B    listeners and IIFEs — nothing names them

Wiring moves even when the functions around it cannot, because a classic script
loaded AFTER `app.js` can read every top-level `let`/`const` it declares. The
direction that fails is the opposite one: a binding declared in an editor-only
file does not exist on the player at all. **Ask which direction the reference
runs, not whether the region is "shared".**

Since the player template lost the music panel, these listeners had been
attaching to detached stub elements on every shared link — work with no possible
effect.

## Photo drawer wiring out too

`editor_photo.js`, **12,298 bytes**: upload and drop handlers, the fit buttons,
reposition, the opacity and blur sliders and their nudgers, and the eraser
cursor's canvas listeners. Same rule as `editor_music.js` — only STATEMENTS
move; the functions they call stay in `app.js`.

The eraser cursor's listeners are on `.canvas-wrap`, which the player DOES have.
They are editor-only because the player has no eraser, not because the element is
missing — worth noting, since "the element is absent" was the test for everything
before this.

**A gap in `verify_seam` that this exposed.** Its "editor-only extracted" figure
counts named FUNCTION spans, so it read 951 lines both before and after 12.3 KB
of wiring moved: `editor_photo.js` contains no top-level functions at all. The
suite still passes and its leak assertion is still meaningful, but **that number
cannot see a wiring extraction**, and anyone using it to judge progress will
conclude nothing happened. `verify_player_isolation.py`'s byte ratchet is the
measurement that tracks this work.

## Closed in v212 — the trim strip, and an assertion that pinned nothing

**The bug.** `drawWaveform()` sized `#waveformCanvas` straight from
`musicTrack.getBoundingClientRect()` with no guard, and the decode chain is its
ONLY caller. Sizing a canvas from a 0-wide rect is not a no-op: it sets
`canvas.width = 0`, which CLEARS the bitmap, and the loop then paints zero
peaks. So a decode landing while the music drawer was shut left the strip blank
for the rest of the session, while `drawZoomWaveform` — guarded, and re-called
from `updateTrimUI()` — drew Loop Detail correctly from the SAME buffer. One
decoded buffer, two canvases, one painted. Reported from a phone, where the
slower decode makes it easier to hit; the realistic routes in are a draft reload
or closing the drawer before decode lands.

Reproduced before any edit, by holding `decodeAudioData` until the drawer was
shut: strip 0x0 with 0 ink, zoom 638x72 with 45,936 ink. That is the screenshot.

**The fix.** The guard on `drawWaveform` on both editors, plus a repaint from
Pad's `openDrawer()` music branch, two frames after opening so `musicTrack`
reports real width rather than 0.

**THE PART WORTH READING. My first Flip assertion pinned nothing, and only the
mutation test found it.** The handoff note said "same on Flip, which had the
identical unguarded line". The LINE is identical; the conclusion was wrong.
Flip's `reveal()` already calls `requestZoomWaveformDraw()`, and Flip's copy of
that repaints BOTH canvases — so **Flip self-heals this scenario and was never
broken by it.** An assertion that Flip "shows a painted strip after opening the
drawer" is green against the sealed v211 archive and green against the fix.

So the two surfaces are pinned by DIFFERENT assertions, deliberately:

* **Pad** fails the user-visible scenario, so the scenario is its pin.
* **Flip** cannot fail that scenario, so its guard is pinned by the property the
  guard actually governs: paint the strip, take the track's layout away, call
  `drawWaveform`, restore layout WITHOUT scheduling a repaint, read the canvas.
  Guarded, 9,499 ink survives; unguarded, the canvas is 0x0 and empty. The whole
  sequence runs inside ONE `evaluate` so no rAF can slip in and repaint between
  the wipe and the measurement — that would make the probe green for a reason
  having nothing to do with the guard.

**Generalises, and this project keeps relearning it.** `verify_parity`'s
re-inline caught the same class: behavioural parity says the copies agree today,
not that the assertion depends on the fix. **Run the mutation per COMPONENT, not
once for the whole change** — a single all-or-nothing revert would have shown
three reds and hidden that one of them was unreachable.

Mutation matrix, each component reverted independently (the full revert is
byte-identical to the sealed v211 `app.js` and `flip.js`):

    mutation      pad gate  pad scenario  pad no-wipe  flip no-wipe   total
    none            PASS       PASS          PASS         PASS       298/298
    pad-guard       PASS       PASS          FAIL         PASS       297/298
    pad-reveal      PASS       FAIL          FAIL         PASS       296/298
    flip-guard      PASS       PASS          PASS         FAIL       297/298
    all (= v211)    PASS       FAIL          FAIL         FAIL       295/298

The gate assertion stays green under every mutation BY DESIGN — it asserts the
scenario entered the failing state, so a red gate means a broken probe, not a
caught bug. Under `pad-reveal` the no-wipe pin fails on its own self-gate
(`before.ink > 500`), not on a wipe: the strip was never painted to begin with.
Same colour, different reason, and worth reading the detail line rather than the
column.

**Cost: 209 B served, 2,428 B of source.** Almost all of it is the comment
naming the pattern, which `jsstrip.py` removes from the response — this is the
third "sized from a rect with no layout yet" bug in this drawer, so naming it in
place is worth 209 B. The ratchet went 146,911 -> 147,120, set to fit, with the
accounting line beside it.

**A number from the previous handoff that was wrong: "+360 B".** It was recorded
against a fix whose Flip half was mischaracterised, and the measured figure is
209 B. Nothing from that note should be carried forward without re-measuring.

## Also closed in v212 — two generators, one stanza, and they disagreed

**Found while sealing this build, by causing it.** `release_run.py` drives
`run_harness.sh` one batch at a time, so the record it leaves behind describes
only the final batch. It already fixes that from one side: it rewrites
`LAST-RUN.txt` to cover every batch and re-stamps. **That holds only while the
release run is the LAST harness invocation.** A bare
`./harness/run_harness.sh verify_docs.py` afterwards rewrites `LAST-RUN.txt` and
re-stamps from it — publishing **a stanza claiming 36 assertions from a single
batch, beside a `RELEASE.md` recording 2400 across every suite on disk, on the
same frozen tree.**

**This is worse than a hand-typed number, not better.** It is machine-generated,
so it carries exactly the authority this project grants generated figures, and
it is wrong. The generated-not-typed rule assumes ONE generator. There are two,
and nothing made them agree.

`stamp_docs.py` now REFUSES a stamp that would narrow the record for the same
tree; `--force` is the deliberate override.

* **It compares ASSERTION TOTALS, not suite counts.** `read_run()` counts suites
  that REPORTED (59 here), while `RELEASE.md` counts suites reported INCLUDING
  skips (61). A suite-count comparison refuses a legitimate full release. The
  assertion total is the one figure both generators compute the same way,
  because a skipped suite contributes zero to each.
* **A `RELEASE.md` for a DIFFERENT tree does not gate at all.** It says nothing
  about the run being stamped, and gating on it would wedge every build — which
  is precisely the state the tree is in mid-release, since `RELEASE.md` is
  written at the END.

**The pin runs in an isolated temp ROOT, and that is load-bearing.** The first
version drove the real `stamp_docs` against the real files and could not work:
`stamp_docs` resolves `ROOT` from `__file__`, so mid-release it reads a
`RELEASE.md` describing the PREVIOUS tree, the guard correctly declines to gate,
and there is nothing to refuse — the assertion would fail inside the very run
that seals the archive. It also restored "the real record" from disk, which at
that moment WAS the damaged narrow one. Four assertions in `verify_docs.py` now
build a fabricated tree instead: refuse-on-narrow, stanza-untouched (exit code
alone would pass against a script that refuses loudly and writes anyway),
stamp-on-wide, and no-gate-on-other-tree. Mutation-tested: remove the guard and
the two refusal assertions go red while both controls stay green.

**The general lesson, and it is the one this file keeps restating.** A second
generator is a second place for a number to come from. When two of them write
the same field, something has to make them agree, or "generated" stops meaning
"trustworthy" and starts meaning "unattributable".

## The v213 loss — commit before anything destructive

**I destroyed several hours of harness work with `git checkout`.** The tree had
exactly ONE commit — the v211 baseline — and everything since was uncommitted.
`git checkout harness/verify_ux.py`, reached for as a cleanup after a botched
edit script, reverted that file to the baseline and wiped all 68 v213
assertions.

The source survived (only that one file was named), so every feature still
worked. What was gone was the evidence that it worked, which in this project is
most of the value.

**Root cause is not the command.** It is that nothing had been committed all
session, so `git checkout` had nothing to fall back to except the beginning.
`git checkout <file>` in a tree like that is not an undo, it is a delete.

**Rules that follow.**

* Commit before anything destructive, and commit as work lands rather than at
  the end. A commit costs nothing and is the only thing that makes a mistake
  cheap.
* Never `git checkout` a file with uncommitted work in it. For mutation tests,
  `cp` from a `/tmp` copy — that is what every source-file mutation in this
  session did, and it is why app.js, flip.js and the libs all survived while the
  one file handled with git did not.
* When an edit script goes wrong, FIX IT FORWARD. The botched split turned a
  2,770-line file into 3,941 by duplicating a range; that was recoverable by
  inspection. Reverting was the destructive choice, taken because it looked
  faster.

**What made recovery possible** was `/tmp/ux.log` from the last green run: it
held every assertion name WITH its measured detail values, so the rebuild could
be checked against the figures the code had actually produced (peak alpha
89/225, tall-grid aspect 0.99, 1,889ms against 410ms, 282x282 circles) rather
than against fresh guesses. Keep run logs. They are cheap and they are the only
reason this was a rebuild rather than a redesign.

## When to split a suite — measure runtime, not assertions

**The trigger is RUNTIME AND BROWSER LAUNCHES, not assertion count.** Assertions
are nearly free; a `chromium.launch()` and a page load are not, and it is wall
time that decides whether a suite still finishes inside one invocation. A suite
of 400 cheap assertions sharing two pages is fine; one of 40 that launches a
browser each is not.

Measured at v214, on this container:

    suite              launches   runtime   assertions
    verify_ux.py            17      206 s          298
    verify_tools.py         13      134 s           93

`verify_ux` needed splitting at ~366 assertions and roughly 20 launches, when it
stopped finishing in a single tool invocation and had to be run in the
background and polled. That is the failure to avoid: **a suite that becomes slow
enough stops being run**, and an unrun suite is worth less than no suite,
because it still reads as coverage.

**Rule of thumb: past ~150 s or ~15 launches, split BEFORE adding the next
feature's pins, not after the suite becomes unreliable.** `verify_tools` is at
134 s / 13 launches — close, so the next tool's pins should go into a new suite
rather than onto the end of this one.

**The cheap fix before splitting** is to share pages. The v213 mirror pin opened
six browser contexts (one per mode per surface) and was cut to two by reusing
one page and resetting the stroke arrays between cases. Reloads are the
expensive part, not assertions.

## The pen palette lives in lib/palette.js

It used to live in two places: seven `<button>`s written into
`_skribl_draw_drawer.html` for Pad, and a `COLORS` array at the top of `flip.js`
for Flip — the same seven hexes in the same order, kept in step by hand, with
nothing comparing them. The failure mode of forgetting one is not an error. It
is two editors quietly offering different colours, which nobody notices until
someone switches surfaces mid-drawing. Both build from the lib now, and
`verify_parity` asserts they render the same list, in the same order, and that
the list came from the lib rather than from a copy.

**The colours are Risograph inks** — fluorescent pink, hot orange, acid yellow,
a printed green and a federal blue, plus paper white and a toner black. That is
what small-press zines are actually printed with, and it is a deliberate
replacement for what was there: a purple and a blue lifted straight from the UI
accent, a mint green and a muddy amber. *A drawing palette that matches the
chrome is a palette that was never chosen.* Riso inks are spot colours, mixed
to sit on paper rather than to pass a contrast check, so they are strongest on
the dark grounds the background swatches default to — acid yellow on white is
nearly nothing, which is true of the ink as well.

The lib marks its dark swatches with `dark: true` and deliberately does **not**
say what colour their rim is. A near-black dot on a near-black drawer is an
empty hole, but the drawer is near-*white* in light mode, where the dot needs no
help and a light rim would be the thing that vanishes — so the rim is CSS,
keyed off `[data-ink="dark"]`, and follows the theme.

**Building the dots at runtime is what let the two lists become one.** Pad's
click handler is delegated on `#colorGroup`, so a dot created after load needs
no listener; Flip passes an `onPick` because it also closes the drawer. The
custom picker and the eyedropper stay in the markup — they are controls, not
colours, and they are what the dots get inserted before.

## Colour ratchets: three of them, and each was added after something escaped

1. **Neutrals outside `:root`** (`verify_surfaces`) — every grey the chrome
   paints must be a token, or it will not follow a light theme.
2. **Chromatic ink** (`verify_theme`) — stricter: `color`, `fill` and `stroke`
   may hold no literal at all except `#fff` and `#0d0f14`. A red is not a
   neutral by any measure, so the grey audit walked straight past `#f4326f` at
   3.32:1 on a light sheet.
3. **The `rgb()` function form** (`verify_surfaces`) — the first version of the
   neutral ratchet only looked for `#hex`, so `background: rgb(23, 27, 35)` sat
   on two controls and stayed dark in light mode with nothing to say so.

There is one exemption and it is a rule rather than a list: a token named for
the **canvas** is not chrome. `--on-canvas-rgb` is the empty-state hint, painted
on the drawing surface, which follows no theme — and naming it in `:root` is
what makes that a visible decision instead of a literal somebody missed.

**What a ratchet cannot see is a mark that is white on purpose.** `#fff` is
exempt because it is nearly always text on a coloured fill — but five marks were
white against a surface that flips, and simply disappeared in light mode: the
brush-size preview dot, the size-preset dots, the music playhead, the spinner's
leading arc, and the ring around the selected swatch. Those were found by
looking, not by asserting.

## The shared modules, all of them

`skribl/static/lib/` is where a rule lives once instead of twice. The two
editors are separate controllers — app.js and flip.js — so anything they both
obey drifts unless something owns it, and `verify_parity.py` exists because it
did. Eight of these had never been named in any document, which is how a
module gets forgotten and reimplemented.

Surfaces are read from the template `<script>` tags; the descriptions are each
file's own opening line. `verify_docs.py` fails if a lib here is named nowhere.

ONE ENTRY READS "HOST" RATHER THAN A SURFACE. `composehost.js` is the pad
button's lifecycle for a host's own composer, so nothing Skribl serves loads it
except the `/feed` preview standing in for a host. It is in `lib/` for the same
reason everything else is — the alternative is every host writing the same four
rules, three of them right — but it is the one module whose reader is somebody
else's page. It is not in `skribl_inline_assets()` and carries its own byte
ratchet in `verify_inline.py`, separate from the embed's: a page that only
DISPLAYS Skribls never composes one and must not be charged for it.

"in-post" is the fourth surface: the player a host embeds in a feed post (`skribl/static/inlineplayer.js`, `templates/skribl/_skribl_inline_player.html`).
It loads THREE of these — `canvassizes.js` for a legacy payload's default
shape, `holdtiming.js` for what a per-page hold means, and `audiosession.js`
for the iOS ringer fix — and its own code reads all three. This said "exactly
two ... and reads nothing else from `lib/`" until v281; `audiosession.js`
arrived with the ringer fix and the sentence did not move.

`sharecard.js` USED to be a fifth, and v281 dropped it. The idle poster's crop
is literals in `inlineplayer.css`; nothing in the page ever read
`window.SkriblShareCard`. The only reader was `verify_inline.py`, evaluating
`band()` in the page to check those literals still agree with the module's
arithmetic — a real assertion that did not need the payload. The suite injects
the module now (by `evaluate()`, since the page's CSP correctly refuses an
injected `<script>`), and the embed ratchet came down 32,000 → 31,000 rather
than banking the saving as slack.

**The saving is 993 B, not the 5,210 B this paragraph first claimed.** That was
the size on disk; `jsstrip.py` serves these files without comments and the
budget counts served bytes. The correct figure was in `verify_inline.py`'s own
note the whole time. A five-fold overstatement in the direction that made the
finding look better is exactly the kind worth writing down. `verify_inline.py` asserts both that it reads them and that the
macro loads them, because reading a global nothing loads is a silent fallback
rather than a shared rule.

<!-- GEN:MODULE-INDEX -->
| module | loaded on | what it owns |
|---|---|---|
| `artwork.js` | Pad+Flip | The artwork stage — ONE implementation, shared by Pad and Flip. |
| `audioloop.js` | Pad+Flip+player | Skribl shared audio-loop DSP — canonical copy (INTEGRATION step 3b). |
| `audiosession.js` | Pad+Flip+player+in-post | Making Web Audio audible on an iPhone whose ringer switch is off. |
| `brushes.js` | Pad+Flip | Brushes — presets expressed entirely through per-point size and colour. |
| `brushfield.js` | Flip | The arithmetic behind tools that act on ink already on the page. |
| `canvassizes.js` | Pad+Flip+library+in-post | Canvas presets — the one table both editors read. |
| `colorselect.js` | Pad+Flip | Colour selection — the part both editors must agree on. |
| `composehost.js` | HOST | The pad button's lifecycle, for a HOST's composer. |
| `constrain.js` | Pad+Flip | Shift-to-constrain — snap a stroke to the nearest axis, shared by both editors. |
| `draftstore.js` | Pad+Flip | Draft media persistence — the bytes localStorage cannot hold. |
| `drawerdetent.js` | Pad+Flip | The draw drawer's HALF detent — one implementation, both editors. |
| `drawers.js` | Pad+Flip | Exclusive drawer controller — the ONE implementation of a machine both editors had hand-rolled: named panels above/below a toolbar, at most one open, the opener button reflecting state, and a scroll that reveals the opened panel without stranding it under browser chrome. |
| `erasersize.js` | Pad+Flip | Eraser size — shared by both editors. |
| `eventpoint.js` | Pad+Flip+player | Which contact a gesture belongs to — shared by Pad, Flip and the player. |
| `eyedropper.js` | Pad+Flip | Eyedropper — the armed-state machine, shared by both editors. |
| `floodfill.js` | Flip | Flood fill, expressed in the only vocabulary this project has: strokes. |
| `framebitmap.js` | Flip+player | Frame bitmaps — a painted page is rasterised once per playback, shared rule. |
| `gridoverlay.js` | Pad+Flip | Grid overlay — the alignment guides both editors draw over the canvas. |
| `helpsearch.js` | Pad+Flip | Help drawer search + live section counts. |
| `hints.js` | Pad+Flip | First-use hints — one short toast the first time a control is used. |
| `holdtiming.js` | Pad+Flip+player+library+in-post | Per-page hold — the ONE definition of what a hold MEANS, shared by the Flip editor and the player. |
| `inputsamples.js` | Flip | The points the browser already captured and the handler was throwing away. |
| `keyregistry.js` | Flip | lib/keyregistry.js — what is bound to which key, and whether two things answer at once. |
| `looptrim.js` | Pad+Flip+player | Loop trim clamping — the rule both editors apply six times between them. |
| `media_validation.js` | Pad+Flip | media_validation.js — one owner for media format policy and byte verification. |
| `mirror.js` | Pad+Flip | Mirror drawing — reflect each point across the canvas centre, shared by both. |
| `modalfocus.js` | Pad+Flip | Focus for surfaces that declare aria-modal="true". |
| `nametab.js` | Pad+Flip | The skribl NAME drawer — a title for the drawing, shared by Pad and Flip. |
| `pagespan.js` | Flip | Page spans — a contiguous run of Flip pages, and the operations on it. |
| `palette.js` | Pad+Flip | The pen palette — one list, both editors. |
| `photofit.js` | Pad+Flip | Photo fit geometry — the part both editors and the player must agree on. |
| `pillfit.js` | Pad+Flip | The autosave pill yields to the controls it would sit on. |
| `pinchgesture.js` | Pad+Flip | Pinch contact tracking — the two editors only, never the player. |
| `popdrag.js` | Pad+Flip | Draggable tool popovers — one grip, both editors. |
| `posted.js` | Pad+Flip | Your Skribls — a local record of what you have posted. |
| `postedaudio.js` | Pad+Flip | What a POST stores, which is deliberately not what an EXPORT downloads. |
| `postedcard.js` | Pad+Flip | Compositing /s/<id>/card.png — the post-time half of lib/sharecard.js. |
| `postedui.js` | Pad+Flip | Your Skribls — rendering. |
| `pressure.js` | Pad+Flip | Stylus pressure — the curve, the floor, and the on/off, shared by both editors. |
| `recentcolors.js` | Pad+Flip | Recent colours — the first controller shared by both editors. |
| `recoverykey.js` | Pad+Flip | Both ends of an anonymous author's revocation key: showing one, taking one back, and standing between a bulk clear and the keys it would discard. |
| `report.js` | Pad+Flip | "Report a problem" — the context, collected once, for both editors. |
| `scrubkeys.js` | Pad+Flip+player | Keyboard operation and live value for the three playback scrubbers. |
| `segslider.js` | Pad+Flip | Keeps a .seg-slider pill aligned to the selected button in a .seg group. |
| `selection.js` | Pad+Flip | Selection — pick a region, then move what is inside it. |
| `shapes.js` | Pad+Flip | Shapes — line, rectangle and ellipse, expressed as ordinary stroke points. |
| `sharecard.js` | Pad+Flip | /s/<id>/card.png: WHERE THE DRAWING SITS INSIDE IT. |
| `sizeclass.js` | Flip | One size decision, made once, for the whole app. |
| `smoothing.js` | Pad+Flip | Smoothing (the stroke stabilizer) — shared by both editors. |
| `stamps.js` | Flip | Stamps — the clipboard, but named, persistent and multi-slot. |
| `strokelayers.js` | Pad+Flip+player | Stroke layers — the see-through-stroke compositor's on/off, shared by both. |
| `theme.js` | Pad+Flip | Light/dark chrome — the stored setting, and the one place that applies it. |
| `toolshelf.js` | Pad+Flip | Tool shelf + overflow tray — shared by Pad and Flip. |
| `tooltip.js` | Pad+Flip | Styled tooltips, replacing the browser's. |
| `zoomstep.js` | Pad+Flip | The loop-detail magnification stepper — the ladder, the chrome, and the rule for stepping it, in one place because Pad and Flip both draw this control. |
<!-- /GEN:MODULE-INDEX -->

Generated by `harness/gen_docs.py`: the surfaces come from the templates that
load each module and the description is the module's own opening sentence, so
neither can drift from the thing it describes.

Two are worth calling out because they were extracted after a bug, not before:
`holdtiming.js` (the editor and the player disagreed about what a hold means)
and the budget inside `strokelayers.js` (the editor capped its compositing cost
and the player did not). Both are covered by `verify_sharedrules.py`.

## The page counter reads "21/43", not "Page 21 / 43"

The word cost 69px against 30px, in a `nowrap` bar whose contents already
measured **369px inside 340** at a 360px viewport — the Delete button was being
clipped off the end, before any of the in-between work went near it. In a bar
whose every other control is a page operation, sitting directly above a
filmstrip of numbered pages, "Page" was spending real estate to say what the
context already said.

**The accessible name keeps the full sentence** — `aria-label="Page 21 of 43"`.
That is the trade a visual abbreviation should always make, and `verify_tween`
asserts both halves so a later tidy-up cannot drop the spoken one.
`verify_pages` used to assert `"Page " in textContent`; it now asserts the
*intent* — a digit on screen and "Page" in the accessible name — rather than the
wording.

## Closed in v213 — nine settings, four tools, four carves

**The shape of the release.** Five behaviours the code already had and no
control could reach were exposed; four genuinely new tools were added; and the
draw path was carved out of `app.js`. Everything is on BOTH editors unless
noted, and lives in `harness/verify_tools.py`, split out of
`verify_ux.py` when that suite stopped finishing in one invocation.

**Exposed, not invented** — stroke layers, eraser width, grid density, pause
handling (Pad only), pressure. Each is asserted through the code path that USES
it — painted pixels, `_eraserSize`, the grid overlay, `getPlaybackDuration` —
never through the control's own aria state. A switch that updates itself and
nothing else passes every attribute check ever written, and the eraser mutation
proved it: re-inlining Pad's copy left *"the editor CALLS lib/erasersize.js"*
GREEN while the draw-path assertion caught it.

**New** — shift-to-constrain, keyboard shortcuts, shapes, mirror, brushes,
preview speed (Pad only), selection (Pad only).

### The one rule that shaped every new tool

**Shapes, mirror and brushes all generate ORDINARY STROKE POINTS.** A Skribl is
a flat array of `{x, y, color, size, t, start, erase}` that the player replays
by calling `drawLine`; a shape primitive, a mirror flag or a brush id would each
mean a schema change, new rendering in the player, and every existing post
needing to keep working. Instead each feature shapes the numbers at CAPTURE
time. Three separate pins assert that no point carries a field outside that set
— that is what catches the format opening up.

The corollary is worth keeping: **anything a feature wants that cannot be said
in a position, a width and an `rgba()` is not available.** That is why the brush
list stops where it does. Texture, scatter and blend modes are not omissions.

### Two settings that look alike and go opposite ways

`pauseMode` IS serialized; preview speed is NOT. They sit one row apart in the
same drawer, and the distinction is whether the setting describes **the work**
or **the act of reviewing it**. Pause handling changes what the drawing is, so a
viewer must get the author's choice — the pin loads an author's `keep` drawing
into a browser set to `tight` and requires the same duration. Preview speed is
zoom, not content; posting it would impose one author's review habits on
everyone opening the link.

The mutation is the reason the round-trip assertion exists: with `loadSkribl`'s
adopt removed, *"the choice is written into the payload"* stayed GREEN while the
author's 1,903ms replay collapsed to 410ms for the viewer.

### Grouping, and the connecting-line family of bugs

Mirror emits **one group per reflection**; selection selects **whole groups**;
shapes commit as **one run**. All three are the same rule: the replay joins
consecutive points, so any structure that puts two distant places in one group
draws a line straight across the canvas between them. Flip refuses a share
outright when `strokeGroups` does not account for every point, so on that
surface the failure is a rejected upload rather than a stray line.

### The carves, and doing them in the right order

`editor_draw.js` is the fourth, after `editor_music.js`, `editor_photo.js` and
`editor_shapes.js`. The whole stroke CAPTURE path moved; `drawLine`, `drawDot`,
`getPos`, `pressureSize`, `_eraserSize` and `_brushWidth` stayed, because
`replayTimelineToCanvas` hands the first two to the PLAYER as its painters. The
listeners moved WITH the functions — a binding left behind would ReferenceError
on every player load.

**The numbers make the ordering lesson concrete.** The shape tool was built in
the shared file and carved afterwards: it cost the player 3,191 B, then a
second pass to get 2,337 B back. Selection was built AFTER `editor_draw.js`
existed and cost **195 B**. Same size of feature, one-sixteenth the price.
Carve first when the target is a tool the player has no use for.

`verify_player_isolation` now asserts the carve DIRECTLY as well as by bytes: no
editor-only file is referenced by the player template, and `startDraw`/`endDraw`
are absent from `app.js`. A byte ratchet notices size coming back; it does not
notice code coming back, and a later raise would hide it.

### Latent bug: the history stack aliases its points

`makeHistoryState()` does `strokes.slice()` — the ARRAY is copied, the point
objects are not. Every other writer in this codebase APPENDS points, so nothing
had ever mutated an existing one and the aliasing had never mattered. Selection
moves points in place, so it edited the undo snapshot too and Ctrl+Z restored
the moved position: undo "succeeding" and changing nothing.

Fixed by snapshotting FIRST and only then swapping the selected points for
clones. **The order is the fix** — cloning first captures the clones and fails
identically one step later, which is the mistake I made on the first attempt.
Mutation-tested; the reversed order reproduces the silent no-op exactly.

### Two assertions that were wrong rather than failing

* `verify_seam`'s *"a split is still worth doing"* was a TODO wearing a test's
  clothes: it asserted `editor_lines > player_lines` and could only pass while
  the work was OUTSTANDING. It went red the moment `editor_draw.js` landed.
  Inverted to guard the achievement instead — what is left in the shared file
  must STAY below the player's reachable set.
* `V213e`'s grid probe COUNTED grid lines and divided. With only ~4 columns on
  a `tall` canvas, missing one boundary swung the count 4→3 and the aspect
  0.99→1.31, and it flipped red when an unrelated tune row changed the panel
  height by a few pixels. It now measures MEDIAN SPACING between adjacent
  lines, which a missed edge cannot distort — and which turned out to be more
  accurate too, reporting the true 8x6 where the count version had undercounted
  at 7x5 all along.

### Scratch probes must not be published as the project's result

`stamp_docs.py` now refuses a run whose suite names begin with `_`. A one-off
`_probe_mir.py` (deleted afterwards, and deliberately not in the tree),
written to look at a screenshot, put *"RUN NOT GREEN — 1
suite(s) failed"* into four docs. The v212 narrowing guard did not catch it:
that only engages when `RELEASE.md` describes the CURRENT tree, and a scratch
probe is usually run mid-change when it does not.

### The tool row is full

Four tools plus five controls did not fit a 375px phone, which is what drove the
v219 redesign: Select left Pad and Flip Mode moved to the overflow menu, and the
row is now eight controls that fit from 360px. Magnify is hidden below 641px —
pinch already zooms, and the button exists where the gesture does not — but **hiding it was not safe as
written**: the zoom HUD is where Fit lives, and `beginPinch` enabled the zoom
without ever revealing the HUD, so a pinch-zoomed user would have had no way
back to 100%. `beginPinch` now reveals it. Hiding a control is only safe when
nothing reachable ONLY through it becomes unreachable.

**CORRECTED — the buttons are NOT at 44px.** That claim was carried for several
releases and is wrong: `styles.css` sets `.tool-open` and `.toolbar .undo-btn`
below 640px, and the smallest control *renders* well under 44px on every phone
width, including the v214 row this note was written against. 44px is the desktop
value. Re-measured on the v219 tree:

    320px       bar 288px  WRAPS (safety net)   smallest control 34px
    360px       bar 328px  one row              smallest control 34px
    375px       bar 343px  one row              smallest control 34px
    393px       bar 361px  one row              smallest control 36px
    430px       bar 398px  one row              smallest control 36px
    641px+      bar 565px  one row              smallest control 40px

So the row was never at the tap-target minimum, and any argument that started
"there is no room because we are already at 44" was resting on a number that
had not been true for some time. Whether 34px is acceptable is a decision, and
`verify_layout.py` pins it in ONE place (`MIN_TOUCH_PX`) so raising it is a
deliberate edit rather than a discovery.

## Closed in v214 — seven defects from two external review passes

**Read this before touching media, document loading, or touch gestures.** All
seven came from external review of the sealed v213 archive. None was found by
the harness, which was green throughout: they are phone-specific gesture
lifecycle bugs and asynchronous ordering bugs, and a steady-state desktop suite
cannot see either.

### The two families

**Touch cancellation (3 defects).** `touchcancel` is a real termination that a
browser or OS can deliver INSTEAD of `touchend` — a system gesture, an incoming
call, a scroll taking the pointer. Cleanup keyed only to `touchend` leaves the
move listener installed and the drag state set, so the next unrelated touch goes
on driving a gesture that is already over.

* `editor_music.js` — three trim drags. Reproduced: after a cancel, a further
  move took `trimStart` 1.129 -> 3.386 with `.dragging` still set.
* `editor_menu.js` — the mobile sheet swipe. Kept `transition: none` and its
  `translateY`, and carried the cancelled drag from 50px to 90px.
* `editor_photo.js` — the eraser ring left painted with no finger near it.

**Asynchronous ordering (4 defects).** An operation that completes LAST is not
the operation the user is looking at. Each of these let a superseded completion
write into current state.

* Music decode, Pad and Flip. A=3.00s, B=9.00s, B lands then A: Pad left
  `currentAudioBuffer` at 3.00s while `audioDuration` read 9.00s. The poster
  crops from the buffer, so the track shown and the audio shipped were
  different recordings. Flip's stale completion also rewrote `audioDuration`
  and the trim window.
* `loadSkribl` document loads. A rewrote buffer, duration AND `trimEnd` of the
  open Skribl — and `loadSkribl` schedules `writeAutosave` 300ms later, so the
  corruption PERSISTS. This is the only one that reaches disk.
* Flip draft restore. `applyPayload()` clears `currentAudioBuffer` and
  `ensureAudio()` only builds the `<audio>` element, so `loadDraftFile` restored
  music with no decoded buffer. `buildSharePayload()` crops to the loop ONLY
  when that buffer exists and otherwise ships the whole sample: **588,082 B
  posted after a fresh selection against 3,528,082 B after restoring the same
  draft, both reporting the same 5.00s loop.** A user's saved work posting six
  times the audio, with only a `console.warn` to say so.
* Flip image `Image.onload`. The token guarded validation and the FileReader
  but stopped before the Image load, so `bgImageObj` (what `render()` draws)
  could be A while `bgImage` and the serialized payload were B.

### The rule that came out of it

**A generation token must be checked at the WRITE, not before the await.**
`musicSelectionSeq` already existed and Pad's handler checked it TWICE — both
before `decodeAudioData` was awaited, which proves only that the selection was
current when the decode STARTED. That is not the question. Every async
completion that writes shared state now re-checks its token immediately before
writing.

`skriblLoadSeq` (app.js) is the document-load version: stamped once per
`loadSkribl` and checked at all five completions. A uniform token beats a guard
per callback, because the failure mode is a callback nobody remembered.

Flip bumps `imageSelectionSeq` and `musicSelectionSeq` on draft load, because a
draft load is a DOCUMENT BOUNDARY — a selection made moments earlier must not
complete into the new document.

### THE TWO UNPINNED GUARDS — defence in depth, not demonstrated behaviour

Both are labelled in the source at their own line. **Do not read them as tested,
and do not delete them assuming the suite would catch it — it would not.**

1. **`loadSkribl`'s deferred `writeAutosave` guard** (app.js). Removing it
   reddens nothing. With the other four guards holding, the state at 300ms IS
   the current document, so a stale timer autosaves the RIGHT thing and no
   assertion can see the difference. Pinning it would need a COMPOUND mutation
   (this guard and another removed together), which is weaker evidence than
   none. It earns its place only if one of the others is ever removed.
2. **Flip's draft-boundary `imageSelectionSeq++; musicSelectionSeq++`**
   (flip.js, in `loadDraftFile`). Added beyond the review's report because the
   model is right — a draft load is a new document. Removing it reddens
   nothing: no scenario drives a selection that is still in flight when a draft
   file is opened. Reasonable, unproven.

The other three `loadSkribl` guards and every guard in the other six fixes ARE
demonstrated: remove one and its specific assertion goes red.

### The pre-seal mutation pass earned its place

Removing each guard independently found that **three of five were decoration**.
Two were then given scenarios:

* The **fetch** guard reddened nothing because a `data:` URL fetch resolves long
  before the second load starts. Gating `window.fetch` as well as
  `decodeAudioData` exercises it, and it fails properly: `elDur` drops to 3
  while the decoded buffer stays 9. **A third split-state variant, found only by
  the mutation pass** — the `<audio>` element the transport plays from swapped
  to A's track while the buffer the poster crops from stayed B's.
* The **base snapshot** guard reddened nothing because the payloads carried no
  `baseSnapshot`. Now pinned with two known snapshot colours: remove it and the
  open document's blue canvas is overwritten by A's red.

**Run the mutation pass BEFORE sealing, not after.** A guard with no assertion
behind it is indistinguishable from a comment.

### FOUR TEST DEFECTS, all false confidence

Each would have produced a wrong result, and three of them made a WORKING fix
look broken or a BROKEN one look fixed:

1. **Hand-copied the flow instead of calling it.** The draft probe replicated
   `loadDraftFile`'s steps inline; the replica diverged from the code the moment
   the fix landed and reported a working fix as ineffective. Drive the real
   entry point — construct a `File` and call `loadDraftFile(f)`.
2. **Read the wrong payload path.** `pay.music` instead of
   `pay.frames[0].music`. Both routes read `None`, so the comparison was
   vacuous and passed.
3. **Targeted the wrong element.** `#photoInput` instead of `#imageInput`.
4. **Released gated images by INDEX.** Each `loadSkribl` enqueues more than one
   image, so "index 1 is B's" released one of A's. The GATE caught it as a black
   canvas rather than letting the real assertion pass for the wrong reason —
   release by load RANGE instead.

Add to the earlier vacuous-range-window case and the window-listener
contamination case, and the pattern is clear: **when an assertion behaves
strangely, suspect the probe first.** A gate assertion that proves the scenario
actually entered the failing state is what turns these from silent passes into
visible failures.

### Techniques worth reusing

* **Gate the async primitive into a queue released by index or range.**
  `decodeAudioData`, `window.fetch` and the `HTMLImageElement.prototype.src`
  setter are all overridable in an init script. This makes "B finishes first, A
  finishes last" EXACT. A sleep-based version passes whenever the machine
  happens to order them the other way.
* **Assert the invariant the user cares about.** For the image race that is
  "rendered and serialized AGREE", not "both are B" — a split between preview
  and posted content is worse than either being wrong alone, because nothing on
  screen says so.
* **Assert equivalence between routes, not a fixed number.** The draft pin
  compares restore against fresh selection, so it fails if EITHER route changes.
* **Mutate per component.** All three music trim paths went red from one removal
  until the probe cleared stale WINDOW listeners between cases; per-path
  isolation is what tells you which path a fix belongs to.

### The touch audit is now an assertion (V214b)

The first audit was described as whole-tree and was not: it matched
`window.addEventListener` only, so element-local registrations were invisible —
which is exactly how the menu sheet and eraser cursor escaped it. **An audit
that matches a RECEIVER NAME is the same mistake as an assertion that matches a
word instead of a mechanism.**

`verify_tools.py` now scans ANY receiver every run, with a three-entry allowlist
(`scheduleAutosave` — save triggers, not drag cleanups) and a check that no
exemption is stale. It matches by RECEIVER, not handler name, because the menu's
correct fix uses a DIFFERENT function for cancel — `onTouchEnd` dismisses the
menu past 80px, so wiring cancel to it would let a gesture the OS took away
commit a dismissal the user never finished. The weaker invariant is stated at
the assertion site; the behavioural pins cover the semantics.

## Closed in v272 — a day of live phone review, and one real performance bug

Thirteen shipped changes, every one of them an owner report from a phone or a
desktop in front of the live site. Most are chrome manners in the v271 line and
are recorded in DECISIONS; four carry invariants a next session can break.

**Undo stores a DRAWING, not a screenshot — and this is the one to read.**
`makeHistoryState()` used to copy the whole canvas into an offscreen canvas on
EVERY stroke start and keep thirty of them. On a desktop hi-DPI canvas that is
~17 MB a copy: half a gigabyte pinned for undo, plus one multi-MB allocation
per dot. A thousand dots made the owner's machine unusable, and restoring that
draft was worse — the rebuild rendered AND snapshotted every stroke boundary in
one synchronous burst. States are now `{base, strokes, strokeGroups,
hasContent}` and `restoreHistoryState()` repaints, because the canvas at any
stroke boundary IS `preRecordSnapshot + paintStrokesStatic(strokes)` — the same
identity `stopPlayback()` has always used to restore the drawing after a
preview. **THE INVARIANT THAT MAKES THIS SAFE:** every pixel must be
describable by the stroke list. Ink drawn while NOT recording is not — it never
enters `strokes` — so `unrecordedInk` (app.js) tracks exactly that window and
states carry a real snapshot while it is up. A fresh-take base capture (which
bakes the ink into `preRecordSnapshot`), a clear, or a load drops the flag, and
`restoreHistoryState()` settles it, since a restore determines the canvas
exactly. If you add a path that puts pixels on the canvas without adding
strokes, it MUST raise that flag or undo will silently lose them. Measured at
1414x1414 with 1,000 strokes: 0 pixel entries, 9 MB heap, undo 0.8 ms, restore
0.48 s where it used to freeze; undo/redo pixel-compared exact against live
reference states across pen, eraser and shape.

**The draw drawer opens at a HALF detent on phones** (`lib/drawerdetent.js`),
so choosing a colour no longer hides the art you are judging it against. The
reveal is the part that fought back: the owner's iPhone shipped the "Brush,
smoothing & more" button below the fold through TWO scrollIntoView-based
rounds while every Chromium run scrolled perfectly. `revealPanelEnd()` now
computes the target itself and writes `document.scrollingElement.scrollTop`,
measures the fold against `visualViewport.height` (iOS Safari's bottom bar
overlays the layout viewport, so `innerHeight` lies), and re-asserts at 300 /
700 / 1200 ms because the device settles URL bar, layout and its own competing
scrolls on a schedule no single timeout catches. Each assert is a no-op when
the end is already visible.

**The post-record lock got an affordance.** A finished take locks the canvas
and the only explanation was a toast fired by the press that had already
failed. `#addTakePill` floats at the locked canvas's bottom edge, appends a
take on tap, nudges when a press lands on the locked canvas, and hides under
`body.replaying` — it sits where the replay performs. It lives OUTSIDE
`#zoomLayer` so magnifying never scales it, and the player template never
ships it (the `_authoringCtl` stub keeps app.js's writes harmless there).

**One gradient sweep across the whole lockup.** The mark and its mode word each
restarted the accent gradient. Both now run `gradientUnits="userSpaceOnUse"` in
the shared 30-unit hand: the mark runs 0 -> the lockup's full width, passed in
as the `brand_sweep` Jinja variable by the including page (101 pad, 95 flip),
and each word's gradient starts at the matching NEGATIVE x. A standalone
include (player, library) passes nothing and defaults to its own width. If you
change the word svg's viewBox or the flex gap, `brand_sweep` moves with it.

Also in v272, each recorded in DECISIONS: chrome recedes to 10% while the pen
is down (`body.stroking`, both editors); the status pill yields to open menus
and sheets as it already did to drawers; Flip's Duplicate / Blank / In-between
stopped wearing the dashed-and-hollow costume this app reserves for "nothing
here yet"; the restore banner clears the toolbar on phones (its 20px anchor was
written for a desktop where the bottom edge is empty); and the custom swatch
keeps its rainbow as a ring around the picked colour while recents record the
COMMITTED pick (`change`) rather than every shade a drag passes through
(`input`) — which had filled the row with gradations of one colour.

**CI economics changed with this release, and the rule outlives it.** A single
productive day ran the full three-job harness thirty times. Pull requests now
run one smoke job (`verify_boot.py`); the full sqlite/postgres/mp4 battery runs
on pushes to main and manual dispatch only. That trim is safe because the
affected suites are run LOCALLY before every push and their counts are quoted
in the PR — CI's job on a PR is to catch a broken push, not to re-verify a
verified one. `CLAUDE.md` carries the owner's standing rule: **ask before
taking any action that could create or increase a bill on their accounts**.

**THE BILLING HALF OF THAT PARAGRAPH WAS WRONG AND IS SUPERSEDED (v280).** It
used to say the thirty runs "consumed the account's entire monthly Actions
allowance". This repository is public and every job runs on `ubuntu-latest`,
so there is no allowance to consume — standard runners are free there, with no
minute cap. The trim is still right, for turnaround rather than for money:
three jobs at 40-90 minutes each is a long time to sit on a PR. Still do not
widen the triggers to "fix" a red PR, but do not decline to run CI on cost
grounds either. `verify_docs.py` now gates this claim wherever it appears.

## Closed in v275 — the in-post player, and the three surfaces around it

Five changes that are one change: a Skribl can now be shown inside somebody
else's post, put there from their composer, listed on a profile, and it carries
its own picture and its own loop control. They were built in that order over one
session and they are sealed together because none of them is finished alone —
the player is what makes compose worth having, compose is what puts anything in
a feed, and the share card is the player's idle frame.

**Read this before the next change to any of it:** the in-post player is a
SECOND playback implementation, and the subsections below say what holds it to
the sealed one. The counts for every suite named here are in
`harness/RELEASE.md`; none are typed in this file.

### The in-post player — a fourth surface

A Skribl inside somebody else's feed post. It had existed only as a mockup in a
conversation; it is in the tree now, it plays real posted Skribls, and
`verify_inline.py` is what says so.

    skribl/static/inlineplayer.js       the player   (read its header first)
    skribl/static/inlineplayer.css      its styles, scoped, host-safe
    templates/skribl/_skribl_inline_player.html   two macros a host imports
    templates/skribl/skribl_feed.html + static/feed.js + GET /feed
                                        the smallest honest host, over the
                                        real GET /api/skribls listing
    harness/verify_inline.py            the proof (count: harness/RELEASE.md)

**IT IS A SECOND PLAYBACK IMPLEMENTATION, and that is the risk to understand
before touching it.** The sealed player is a page — app.js plus eight modules,
an app shell, a full transport. Twenty of those in a feed is not a feed. So
inlineplayer.js replays payloads itself, and `verify_sharedrules.py`'s warning
applies one surface further out: the author opens `/s/<id>`, it looks right, and
every viewer scrolling past sees something else. Three things hold it:

  * the RULES come out of `lib/` — `holdtiming.js` for what a hold means,
    `canvassizes.js` for a legacy payload's default shape;
  * what is retyped (the capped-gap timeline, `drawDot`/`drawLine`) is retyped
    verbatim and names its origin in app.js;
  * `verify_inline.py` plays the SAME posted drawing in both, from the same
    clock, and compares where each has got to and what each has drawn.

**The comparison's numbers were set by mutation, and the first set was
worthless.** A 32x32 grid at tolerance 48 passed while the in-post player read a
BLANK canvas (the selector matched the first post in the feed, not the one
playing) and passed again with the gap cap deliberately set to 500 ms, the two
players 0.58 and 0.34 through the same drawing. It is 96x96 at tolerance 18 now,
plus a scale-free ink-mass ratio, and it is floor-subtracted because the two
surfaces paint the drawing's ground in different places — the in-post player on
the canvas, the sealed player on `.canvas-wrap` behind it. Compared absolutely,
all 9,216 cells differ and the assertion is about paint order.

**That gap is CLOSED as of the v277 review.** It used to read: the wet/dry
stroke compositor is not implemented, so a sub-100%-opacity stroke beads at its
overlaps where it does not on `/s/<id>`. It is implemented now — 2,913 B, embed
ratchet 29,000 → 32,000 — because the difference was not beading but a
scalloped, banded rendering of a drawing that is smooth on the canonical page,
and in a drawing product the drawing is the content.

The opaque fixture above stays, because the two surfaces fit the drawing to
different boxes and an absolute cross-surface ink comparison is confounded
whatever the compositor does — an opaque control proved that by scoring worse
than the translucent case. A second fixture, translucent, asserts the shape
property on this player alone: 145,014 ink stamped against 177,246 composited.

**Two things found while building it, both real:**

  * **`POST /api/skribls` defaults to `unlisted` and Pad's composer has no
    visibility control**, so nothing posted from Pad ever appears in
    `GET /api/skribls`. `/feed` was empty on its first run and the suite was
    asserting against an empty list. The default is correct — it is what a
    link-sharing product should do — but it means a host feed's composer is what
    sends `"visibility": "public"`, and `/feed`'s empty state now says so
    instead of telling you to go and post from the Pad.
  * **`asset_url()` built a RELATIVE endpoint** (`url_for(".static")`), which
    resolves against `request.blueprint` — always Skribl's, while every caller
    was a template Skribl rendered. The embed macros render on the HOST's view,
    where a leading dot raises BuildError. It names the blueprint outright now,
    which is identical inside Skribl's pages and works everywhere else, and
    `init_skribl()` adds `skribl_asset` as the ONE app-wide template global —
    added, never overwritten.

**What a host downloads: 23,502 B served**, ratcheted at 24,000 in
`verify_inline.py`. A third of that is `inlineplayer.css`, which is not
comment-stripped — `jsstrip.py` is JavaScript-only — and is left that way
deliberately. Measure it at the BUSTED URLs the page requests: bare, the
JavaScript reads 28,739 B, and a ratchet on that number prices every explanatory
comment as if it shipped.

**The idle poster is `/s/<id>/card.png` CROPPED**, and the crop is the one piece
of geometry two files now share. The card is a branded 1200x630 Open Graph image
and the only per-post picture the server has; whole, it reads as an advert
twenty times down a feed. `lib/sharecard.js` owns where the drawing sits inside
it — `editor_post.js` composites from it, `inlineplayer.css` crops from it, and
`verify_inline.py` measures the RENDERED poster against the module, so a change
to one side fails rather than drifts.

Vertically the crop is exact (the drawing is contained, so its height and y are
identical in every card: 492 of 630, from 27). Horizontally it cannot be: the
drawing's width depends on its own aspect and nothing in the feed knows that —
`canvasSize` is inside `payload_json` and `GET /api/skribls` defers that column
deliberately. The drawing IS centred, though, so a symmetric side crop can only
remove ground as long as the window is at least as wide as the widest canvas.
That is 16:9, so the box is 16:9; a 1:1 drawing then leaves 22% of the box as
ground instead of 59%. A narrower drawing still shows some of the card's frame.
The real fix is the canvas size as a real COLUMN, which is a migration.

**And the ratchet caught the CSS.** Cropping added 2,800 B of explanation to
`inlineplayer.css` and pushed the embed past its byte ratchet — correctly:
`jsstrip.py` strips a JavaScript response and NOTHING strips CSS, so prose in
that file ships to every host on every page. It moved into `inlineplayer.js`'s
header and the CSS kept the numbers and a pointer. Same words, a third of the
weight.

### Compose mode — a Skribl attached to somebody else's draft post

The other half of the in-post player. That one answers "how does a Skribl LOOK
in a feed"; this answers "how does one GET there".

    skribl/static/editor_compose.js     the handshake (read its header first)
    /skribl-pad?compose=1               the same editor, ending differently
    skribl/static/feed.js               ~150 lines of HOST code, written to be
                                        read as the recipe
    harness/verify_compose.py           the proof (count: harness/RELEASE.md)

**THE RULE: COMPOSE MODE PUBLISHES NOTHING.** "Add to post" hands the host the
PAYLOAD, not an id. This is forced, not chosen:

  * `POST /api/skribls` is CREATE-ONLY — routes.py registers one POST and two
    GETs. "Publish on Add, republish on edit" therefore ORPHANS a skribl per
    edit, each having spent a slot of the author's posting quota.
  * An abandoned draft would leave a published, shareable skribl behind that
    the host cannot withdraw.

So verify_compose.py's main instrument is a COUNT OF POSTS, not a "does it
work": zero while attaching, zero after an edit, exactly one when the host
posts. Mutation-tested by disabling the compose branch — five assertions fail,
starting with that one.

**One builder, two endings.** editor_post.js's `submit()` was split: everything
that prepares a payload for posting (serialise, share-card thumbnail, mono audio
bake) is now `buildPostPayload()`, and both endings call it. A composed skribl is
byte-for-byte a Pad-posted one. Two paths preparing "the payload, but for
posting" is exactly the shape of that file's own BUG B — a post-time step that
silently stopped running on one path while the metadata looked identical.

**Three defects found by building it, all real and all fixed:**

  * `setState('idle')` hardcoded `'Post to Skribl'`, overwriting the label the
    TEMPLATE had already rendered. It was a duplicate string before compose
    mode existed; with it, the attach button relabelled itself to publishing
    the first time anything reset the sheet. The label now comes from the DOM.
  * The post sheet stayed open after delivering. The host closes its overlay
    immediately so nobody sees it — until the pad icon is pressed again, which
    reopens the SAME iframe, and the sheet is then sitting over the canvas.
    Found by a probe that could not draw on the second edit.
  * **The underlay repaint moved time.** `img.onload` in inlineplayer.js called
    `render(elapsed, true)`, and `elapsed` is 0 while idle — so on a drawing
    with a photo or a base snapshot, the underlay finishing its decode wiped the
    canvas and repainted the FIRST frame. Invisible on a posted skribl (the
    poster hides it) and fatal on a draft, where idle is the finished drawing:
    the composer showed an empty box. Every Pad recording has a baseSnapshot, so
    this fired every time.

**Posterless idle is a real state now.** A posted skribl idles at time zero
behind its cropped share card; a DRAFT has no card, so it idles showing the
finished drawing. `SkriblInline.attach(el, payload)` is that path — the real
player on a payload with no id, so the composer previews what it will publish
rather than a thumbnail standing in for it.

**The handshake targets an origin, never `'*'`.** Skribl mounts into a Flask
host as a blueprint, so the overlay is normally same-origin and a direct
contentWindow call would work; postMessage anyway, because it is the same code
if the host ever splits deployments and because a wildcard would hand the
author's drawing to whatever page is framing the editor. Asserted in the suite.

### The profile's Skribls tab — /library stops being a mock

The third surface for the same player. The feed shows a Skribl in a post; the
composer shows one on a draft; this is a page ABOUT the drawings — one stage
with a full transport (play, restart, scrub, loop, mute, copy link) and a grid
of share cards beside it.

    skribl/static/library.js       rewritten: real listing, no replay engine
    skribl/templates/skribl/skribl_library.html    the same chrome, real data
    harness/verify_library.py      the suite that replaced a README warning

**WHAT IT REPLACED IS THE POINT.** `library.js` carried its OWN replay engine
and a table of hand-drawn motifs — a bolt, a cassette, a smiley — and rendered
those. Nothing on the page had been posted by anyone, while the route was
registered the whole time, so a host mounting Skribl served invented drawings
from their own URL space and README.md had to carry a warning saying so. The
problem was never the pretending: a page that draws its own content cannot tell
you whether the thing it previews WORKS.

**It contains no player.** The stage is `inlineplayer.js`, driven through the
handle (`play`, `pause`, `seek`, `setLoop`, `state`) — three replay
implementations would drift, and verify_sharedrules.py's note says what that
costs. `verify_library.py` gates it at the source: no `requestAnimationFrame`
in `library.js`.

**The transport is the difference between the two surfaces, deliberately.** A
post gets a play tap and a mute button because a feed is not a media player
(inlineplayer.css says so at the mute rule). A profile tab is a page somebody
came to on purpose, so scrub and restart and a loop toggle belong. `setLoop` is
new on the player for exactly this and defaults ON, so a post is unchanged.

**One payload at a time.** Tiles are share-card images; only the stage's drawing
is fetched. Mutation-tested by prefetching every tile — the assertion fails.

**TWO OF ITS GATES WERE SUBSTRING SEARCHES THAT PASSED ON THEIR OWN PROSE.** One
looked for `offset` and matched a comment explaining why offset paging is wrong;
one looked for `cassette` and matched this file's own description of the motifs
it deleted. Same failure a v273 gate already made by searching for "Pillow" and
matching a comment that mentioned it. They match syntax now (`offset=`), and the
second was replaced by a check on the DOCUMENTS: a page that stops lying while
its docs keep saying the old thing has moved the lie, not removed it.

**FOUND WHILE BUILDING IT — fixed in the subsection below: Flip posts had no
share card.**
`editor_post.js` builds `payload.thumbnail` at post time and `flip.js` never
does — grep it, there is no `payload.thumbnail` anywhere in that file. So every
Flip post falls back to the static branded og-card: on its `/s/<id>` unfurl, as
the in-post player's idle poster in a feed, and as its tile here. It looks like
an advert in all three places. The fix is to share the card BUILDER the way
`lib/sharecard.js` now shares its geometry, and wire Flip's post path to it;
that is a change to a 437 KB file with its own post flow, so it got its own
pass — the next subsection.

### Flip's missing share card, and a 16x encoding mistake

The gap the profile tab turned up: `buildShareCardDataURL()` lived in
`editor_post.js`, which is PAD-ONLY, and `flip.js` set no `thumbnail` at all. So
every Flip Skribl ever posted fell back to the static branded og-card in three
places at once — its `/s/<id>` unfurl, the in-post player's idle poster in a
feed, and its tile on the profile. An advert where the drawing should be, and
invisible because the person who posts one does not look at their own unfurl.
Same shape as the title bug `verify_flipmeta.py` records: a whole control
surface built on one of the two editors.

    skribl/static/lib/postedcard.js   the compositor, editors only
    skribl/static/lib/sharecard.js    the geometry, editors only since v281
    harness/verify_sharecard.py       both editors, one builder, round-tripped

**TWO MODULES, NOT ONE, and the ratchet is what said so.** The first version put
the compositor beside the geometry in `sharecard.js`, which the in-post player
loaded. `verify_inline.py`'s embed ratchet failed on the next run: 2 KB of
canvas work on every feed page in the world, to composite a card a feed never
makes. Split on the same rule `lib/postedaudio.js` states: THE READER IS NOT
THE WRITER. A host embeds the geometry and never the compositor, because it
never posts.

**The split was right and its stated reason was not.** This said the in-post
player loaded the geometry "because it crops the poster by `band()`", and v281
found nothing in that page ever read `window.SkriblShareCard` — the crop is
literals in `inlineplayer.css`. The ratchet's 2 KB was real, because the module
really was on the page; the requirement that put it there never existed. A
right decision resting on a wrong reason is one reader-who-checks away from
being reversed, so the reason is corrected here rather than quietly dropped.

**AND THE ENCODING RULE WAS WRONG BY 16x.** The builder chose PNG for line art
and JPEG for photos, on the recorded grounds that "PNG is both SMALLER and
crisp" for lines. Measured on the actual card: **451,824 B as PNG against
28,062 B as JPEG q0.92.** The cause is the accent wash — Chromium DITHERS a
canvas gradient, putting per-pixel noise across all 1,200x630 that PNG cannot
compress — so the rule was true before the wash existed and was never
re-checked. It survived because a 450 KB card is not wrong, only expensive:
nobody looks at their own unfurl's byte count. The in-post player is what made
it matter, by turning this image into the IDLE COST OF EVERY POST IN A FEED —
a screenful was over five megabytes to show twelve thumbnails.

The fix is to stop having a rule: encode both, keep the smaller. Real cards are
now ~20 KB. `verify_sharecard.py` pins a 200,000 B ceiling, which is the check
that would have caught the original.

**Two suites broke on this change and both were right to.**

  * `verify_flipmeta.py` read the POST body as JSON. `lib/posted.js` gzips any
    body over 4,096 B, and its fixture — one stroke, no media — sat under that
    until a 25 KB card was attached. It inflates now.
  * `verify_library.py`'s search matched `verify_inline.py`'s "Harness fixture
    A" as well as its own, because `run_harness.sh` gives one database to every
    suite in an invocation. Its fixtures carry a per-run token now. Exactly the
    cross-suite state this file warns passes the seal and fails CI.

### A post gets a loop control, and the music stops with the drawing

Owner's call, and it reverses a decision recorded three sections up. The in-post
player shipped with ONE viewer control — mute — on the argument that a feed is
not a media player and a Pad replay stopping dead on its finished drawing reads
as a broken GIF. Both halves of that are still true; what was missing is that
some drawings are two seconds long and a viewer may simply want them to stop.

**Two controls now, in one cluster at bottom-left, and the asymmetry between
them is deliberate:**

    mute   PAGE-WIDE, session-remembered, off by default
    loop   PER POST, not remembered, on by default

Sound is environmental — someone in a quiet room wants it off for the whole
feed. Repeating is a property of the drawing in front of you, and a two-second
loop you want to watch twice says nothing about the next post. A silent Skribl
hides its mute button and keeps its loop button, because a silent drawing still
repeats.

**WHEN THE DRAWING STOPS, THE MUSIC STOPS**, and that is one call rather than
two: the end of a non-looping replay routes through `pause()`, which takes the
audio down in the same breath. It could have been a `cancelAnimationFrame` and
a class change, and then a finished drawing would sit there with a loop still
playing under it — a post that will not shut up, which is worse than one that
never started. `verify_inline.py` measures it on the AUDIO GRAPH with the
analyser tap verify_player_isolation.py uses, and it is mutation-tested: stop
the drawing without routing through `pause()` and the peak stays at 71 where it
should read 0.

That suite grew a third fixture WITH A REAL TRIMMED LOOP to make the assertion
possible. "The music stops" is a claim about sound and cannot be checked from
the DOM.

**Turning loop back on while a replay sits finished restarts it**, rather than
appearing to do nothing until the next tap.

**The embed ratchet moved 26,000 -> 27,500** for about 1.5 KB of stylesheet and
handler. Unlike the transport the profile tab needed, this one is paid for by
the caller that uses it.

**Three documents said "mute is the only viewer control"** and are corrected:
README.md, docs/INTEGRATION.md and the /feed page's own note. A claim that
becomes false the moment a control is added is exactly what `verify_docs.py`
cannot catch, because it is prose about behaviour rather than a name or a
number.

## Closed in v276 — the drop-in becomes something you can run

v275 made a Skribl displayable in somebody else's post. It did not make the
integration OBTAINABLE: a host still read four documents and wrote the same
hundred and fifty lines everyone writes. Three pieces close that, and the
general lesson of the release is in the third.

    skribl/creation.py                   create_post(), carved out of the route
    skribl/static/lib/composehost.js     the pad button's lifecycle, once
    examples/host_app/                   a host you can actually run
    harness/verify_createpost.py         agreement between the two callers
    harness/verify_example.py            the example, driven in a browser

### create_post() — for a host whose composer is a FORM

`POST /api/skribls` serves a host whose composer is a browser. skribls.net's is
a server-side form, and that host already has the payload, the author and its
own CSRF token — so POSTing to its own JSON endpoint buys a second request, a
second auth and a SEPARATE TRANSACTION. `create_post` runs in the caller's
request on the caller's session, so one commit makes the Skribl and the host's
own row durable together, or neither.

**IT IS A CARVE.** Everything in `creation.py` was MOVED out of
`create_skribl`'s body and the route now calls it. Two functions that both
"validate a payload and insert a post" is `editor_post.js`'s own BUG B. What
stayed in the route is what is HTTP: the two rate budgets, CSRF, the
Idempotency-Key header, jsonify.

**THE LIMITER CANNOT FOLLOW, and the mutation is what proved it.** The plan was
to document that a host calling create_post is unthrottled. The mutation written
to prove that assertion never reached it — it died on "Working outside of
request context", because `_client_ip()` reads the Flask `request` and the
reservation settles in a teardown. Not a policy; a fact about what the limiter
is made of. **A host must limit its own compose view.**

**The instrument for a carve is AGREEMENT**: ten bad payloads through both
callers from one table, comparing status and message.

### lib/composehost.js — and a comment corrected by a mutation

Four rules that are identical in every host: lazy `src`, the re-edit push, the
reset on clear, origin in and out. Its own comment claimed that without the push
the editor "reopens EMPTY" — it does not, because the iframe keeps the drawing,
so a host that skips the rule LOOKS correct while trusting the editor's retained
state. The rule earns its place when the draft and the editor differ
(`setPayload` on a saved post). Written from reasoning, corrected by a mutation
that failed to fail.

**And verify_compose did not cover it**: disabling the rule left it at 29/29,
because the ink assertion measures what the editor kept. It counts the
`skribl:compose:load` message now. One assertion in that file was
`check(..., True, ...)` — the literal True, in the file that names lazy loading
as a rule.

**Two byte ratchets now**, because display and compose are paid by different
pages: the embed's scrape would otherwise have charged every feed page in the
world for a module only a composer loads.

### examples/host_app — and the three copies it exposed

    python examples/host_app/app.py

A separate Flask site, its own users and posts, blueprint under a PREFIX,
composing with a server-side form. `verify_example.py` boots it as a real server
and drives a real browser through it, then checks on a FRESH connection that the
host's row and the Skribl were committed together. An example nothing runs is a
document that goes stale silently.

**THE THIRD CALLER IS WHAT EXPOSES DUPLICATION, BECAUSE THE FIRST TWO EACH HAD A
REASON.** A draft has no public id and the macro required one, so
`skribl_feed.html` hand-copied twenty lines of the player's internals and
`skribl_library.html` copied a variant — and the example was about to be the
third. It is one macro now (`skribl_inline_draft(id, controls)`), and the gate
added for it — no template outside the macro file writes the player's internal
class names — FAILED ON ITS FIRST RUN and named the library. Found, not guessed.

### Two things caught by gates rather than by reading

**A route literal in the one file whose comment says it never uses one.**
`inlineplayer.js` fell back to `'/api/skribls'` when `data-skribl-api` was
absent. Under a prefix that fetches a path that does not exist and fails quietly
into the error panel — the exact defect the surrounding comment describes as the
reason the attribute exists. `verify_seam.py` caught it; there is no fallback
now. The comment and the line contradicting it were written by the same hand in
the same hour. **A comment is not a gate.**

**Two hand-typed counts in one sentence of this file** — batches and suites.
`verify_docs` caught the suite count; nothing checks the batch count and it was
stale too. Both removed rather than updated.

## Closed in v277 — five things the owner found on a phone

Every one came from using the app on an iPhone, not from a suite going red. The
harness is Chromium on Linux; four of the five are invisible there by
construction. That is the pattern worth taking from this release.

    skribl/static/lib/audiosession.js    the iOS playback session (confirmed on a phone, 5 Sep 2026)
    harness/verify_audiosession.py       its mechanism, and preview's first
                                         assertion that sound comes out at all
    _skribl_export.html                  a file-name field; the GIF row
    skribl_editor.html                   the sound marker, one macro'd glyph
    styles.css                           --good lifted, --good-rgb added

### The four small ones

**The post sheet shows the toolbar's music mark**, so a Skribl with a loop and
one without stop looking identical at the moment of posting. The owner's sketch
beat mine — I proposed a chip that borrowed the tool row's green, they asked why
not use the tool row's mark. ONE GLYPH: a macro, called by both, compared as
RENDERED rather than grepped, because a copy satisfies any grep and drifts the
first time either is redrawn.

**Exports can be named.** Every one was a hardcoded literal — `skribl.gif`,
`skribl-flip.mp4` — so two exports of one drawing were indistinguishable and
titling the drawing changed nothing. `lib/nametab.js` had named drafts properly
for releases; the media exports were never wired to it.

**Placing that field's label found a bug no suite could see.**
`.export-optlbl` lived only in `flip.css`, which Pad does not load, while the
shared partial uses it outside the flip-only block — so Pad rendered
"Background" at browser-default size for releases. `verify_exportui`'s sweep
concatenates both stylesheets, so a class styled for ONE surface passed as if
styled for both. Split by surface now; the hole was demonstrated by reverting
the class.

**The GIF background control is a row, not a banner.** `width: 100%` was
commented "Full width so both labels fit" and did not survive measurement.
Restoring it fails the suite in the most telling way: both labels forced to
143px, so the sliding pill cannot tell them apart.

**And `--good` was too dull** — #1bcf8f to #30e8a7. Never short of contrast
(9.6:1) but of vividness, and it is spent on 6-7px dots. Three rules hardcoded
the token's own RGB and would have kept the old hue; they read `--good-rgb` now.

### iOS silences Web Audio when the ringer switch is off

`harness/verify_audiosession.py`, `skribl/static/lib/audiosession.js`.

Found by the owner on their own phone: **Test Seam plays and Preview Loop does
not**, on a phone set to silent. Test Seam is a plain `<audio>` element; Preview
Loop is Web Audio. iOS routes Web Audio into an "ambient" session the hardware
switch mutes and leaves `<audio>` alone.

**THE SCOPE IS NOT THE PREVIEW BUTTON.** `/s/<id>` and the in-post player are
both Web Audio, so on an iPhone in silent mode a shared link's music and every
feed post's music are silent too. For a component whose whole purpose is playing
in somebody else's feed, that is the feature not working.

**Why every existing guard missed it.** app.js has an elaborate hand-off for a
context that never unlocks, and every one of its tests is `state !== 'running'`.
In silent mode the context reaches `running` perfectly well and is merely
inaudible — so all the guards pass, the native `<audio>` fallback is
deliberately suppressed, and the result is confident silence. app.js's own
warning, *"A source object existing is NOT the same as audible playback"*,
applies one level further out than where it was written.

**The fix holds a silent looping `<audio>` element**, which moves the session to
"playback". Claimed only on a gesture that asks for sound — the unmute tap, the
Preview button — never at load, because a held session shows Skribl as playing
media in Control Center. Overriding the switch is defensible here only because
sound is never automatic: the in-post player ships muted.

**CONFIRMED ON THE DEVICE, 5 Sep 2026 — after v277 sealed it unverified.** The
owner reported *"Music works"* from the same iPhone that found the bug, in
silent mode. v277's DECISIONS entry sealed this fix with "A green seal is not
evidence this works. The phone is." The phone has now answered.

**THE SUITE STILL CANNOT VERIFY IT, AND STILL SAYS SO.** Chromium on Linux has
no ringer switch. `verify_audiosession.py` pins the mechanism — one element,
silent, looping, playing, idempotent, released, loaded on all four surfaces —
and prints a closing line saying none of it proves an iPhone is audible. That
line stays: the device confirmation is evidence about the fix, not about the
harness, and a green run here only proves the mechanism is still wired up. That
is the job it now has — protecting a confirmed fix from being refactored away.
This is the same limit app.js already records: *"Desktop never showed it …
including in the harness."*

It also closed a gap that let a person find this before a suite did:
`verify_audiostate` drove Preview Loop under a HUNG unlock and asserted the
fallback plumbing, but nothing anywhere asserted that preview makes a sound.

## Known-open, in the order worth doing

### Deferred: the bottom-toolbar redesign (owner-approved, still open)

The proposal: replace the bottom bar with Pen / Eraser / Shape / Select / Colour
/ **Tools** on Pad (Flip drops Shape), moving Image, Music and Magnify into a
labelled "Tools" action sheet — NOT another `•••`, because the top menu already
owns that glyph and two identical symbols meaning different collections is
avoidable ambiguity. Two things were never resolved: where Undo/Redo go once
they leave the bar, and whether Image/Music belong in "Tools" at all when they
are content rather than tools.

**Its measured premise no longer holds, and that is why the 208 lines of
measurement that used to sit here are gone.** The section argued from a v213
bug report: Pad WRAPPED at 320px with Image and Music orphaned on a second row
and the bar 113px tall, and Flip OVERFLOWED horizontally by 16px, which it
called the worse of the two because content was clipped with no cue. Re-measured
at 320px on the v282 tree:

    Pad    toolbar 92px          horizontal overflow 0
    Flip   toolbar 56px          horizontal overflow 0
    both   document overflow 0 — content is narrower than the viewport

Flip's clipping is gone and Pad's bar is 21px shorter than the number the
argument rested on. The proposal may still be worth doing on design grounds;
the emergency it was written up as is over. Anyone reviving it should re-measure
first rather than trust a snapshot — which is the whole reason this replaced it.

## Things that will bite an unwary assistant

* **NEVER edit a released Alembic migration.** `RELEASED.txt` freezes every
  digest and `verify_migrations.py` fails if one changes.
* **`view` does not show the user anything.** It renders an image for the
  assistant only. To show someone a screenshot, write it to
  `/mnt/user-data/outputs/` and call `present_files`. Saying "here it is" after
  a `view` call is describing something they cannot see.
* **Measure rendered geometry, not arithmetic.** Flex shrinks controls before
  anything overflows, so summing child widths reports room that is not there.
  Force the candidate into the DOM and read `scrollWidth` against
  `clientWidth`. Likewise `offsetParent`, not the `hidden` property.
* **An explicit `display` defeats `[hidden]`.** Hit three times. Scope layout
  rules with `:not([hidden])` or pair them with `[hidden]{display:none}`.
* **`classList.toggle(name, undefined)` TOGGLES.** An `&&` chain that can yield
  undefined must be wrapped in `!!` — this made two colour swatches appear
  selected at once.
* **An inline style beats any stylesheet rule.** `setTool()` writes
  `pad.style.cursor` inline, so cursor changes must also be inline.
* **Top-level `let` is not on `window`.** `window.frames` is the browser's
  frame collection and `window.fps` is the element with `id="fps"`. Read
  editor state through a bare identifier, not off `window`.
* **A retry must accept on the property the assertion checks.** A WebM test
  retried on byte count and asserted on duration; it flaked three times.
* **The two editors bind DIFFERENT event families.** Flip uses Pointer Events,
  Pad uses `mousedown`/`touchstart`. Code written for one is dead in the other,
  silently.
* **Finish all documentation BEFORE the final harness run.** `run_harness.sh`
  calls `stamp_docs.py` itself, and the run recorded LAST is the one stamped —
  so the recorded set must be the final invocation. Regenerate `SHA256SUMS`
  after, and delete any scratch probe suite first or it ships.
* **A skip is not coverage.**

---

## Running it

    pip install -r constraints.txt --require-hashes    # the pinned lock
    python -m alembic upgrade head                     # NOT create_all()
    gunicorn app:app

On Render, the middle two run together from the dashboard **Start Command**
(`python -m alembic upgrade head && gunicorn app:app`) — set in v270, when it
emerged that Render never reads the `Procfile` v267 had wired the same line
into, and production had therefore never run a migration on deploy (DECISIONS
v270). The Procfile keeps the same command for Heroku-style hosts and as local
reference only. If you ever run more than one web instance, move the migrate to
a Render `preDeployCommand` so two boots cannot race the same `upgrade head`.

    ./harness/run_harness.sh verify_move.py            # name them; a bare run hangs
    python3 harness/stamp_docs.py                      # docs from LAST-RUN.txt

`pip install -r requirements.txt` also works. What does NOT work is
`-r requirements.txt -c constraints.txt` — the lock carries hashes, which puts
pip in `--require-hashes` mode, and that mode rejects version ranges.

---

## A note on process

Almost every bug this session was found by RUNNING something, after the code
read correctly — and several were found by the owner on a real phone after the
suite was green. Screenshots caught what assertions did not: a canvas picker
that painted a purple bar over its own menu passed 21/21 first.

The pattern worth carrying: **when a change touches a surface, write the
assertion that reproduces the OLD behaviour first**, and prefer measuring what
is rendered over what the code was told to do.
