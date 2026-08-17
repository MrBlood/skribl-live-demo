# Skribl — Handoff for the next session (written at the v209 seal)

**Read this first.** It is the complete state of the project: what shipped,
what is open, what the owner has decided, what the harness protects, and the
exact procedures. Everything here was verified against the tree, not recalled.

---

## 0. Where things are

| Thing | Location |
|---|---|
| **Sealed, shipped builds** | `/mnt/user-data/outputs/skribl-vNNN-sealed.zip` — v203 … v209 |
| **Current sealed build** | **v209** — tree `see harness/RELEASE.md`, 2,337 assertions, 60/60, 1 skip (mp4), PG 14/14 |
| Working tree | `/home/claude/skribl-v209/` (identical to the seal at time of writing) |
| Demo `.skribl` files + previews | `/mnt/user-data/outputs/skribl-demos/` (also `harness/fixtures/` in-tree) |
| Design mockups (HTML, real pixels) | `/mnt/user-data/outputs/skribl-*.html` |
| Per-release response docs | `docs/REVIEW-RESPONSE-v200.md` … `v209.md` |
| **The developer's v207 review + this reply** | `docs/REVIEW-RETORT-v207.md` (in-tree), original in the review zip |
| Prior transcript catalog | `/mnt/transcripts/journal.txt` |

---

## 1. The lineage, one line each

| Seal | Assertions | What it was |
|---|---|---|
| v200–v203 | 2137 → 2184 | Four external review rounds: transaction ownership, media authz, idempotency, SQLite savepoint autocommit bug (`isolation_level=None` + explicit BEGIN), teardown ordering, iOS silent-audio (A1), vanishing canvas frame (A2). |
| v204 | 2199 | Grid → tune drawer both editors; Pad gained a tune drawer; grid extracted to `lib/gridoverlay.js`; editor-only `editor_tune.js` so the player carries none of it; motion-guide icon; help text; footer → toast. |
| v205 | 2224 | Owner fix pass: tune drawer into Pad's header (=Flip), icon B, 16px toggles, 1px ring, panel toast, tune hidden while recording. |
| v206 | 2244 | **Flip image/music drawer bug root-caused** (root-level file inputs + click-outside handler; unreproducible headless because it needs the real OS dialog); toast → link; menus aligned; Clear-all in both; `.skribl` iOS accept; cross-load guards; music drawer option A; grid lights; pill sliders unified. |
| v207 | 2310 | Repeat button lights; onion → tune drawer (orange); loop-detail pills + magnifier; 641px no-wrap; nudge grid stacks on phone; help icons + player step + Match Drawing Time; eyedropper tap area; **all icons SVG**; dead player ⋯ removed; demo fixtures; three audits (consistency / help completeness / phone fit). |
| v208 | 2318 | v207 review F1 + F4 closed (real AUTOCOMMIT guard; Record closes Tune). |
| **v209** | **2337** | **v207 review F2 + F3 closed** — failed posts no longer cost quota (tombstoned release + real-lock regression); Pad replay unlocks audio inside the Play gesture (A1 template, order-instrumented, mutation-tested). ⚑ ratchet +510 B. |

Every seal: verified from its own shipped zip (`sha256sum -c`), every fix behind a mutation-tested or counterexample pin.

---

## 2. What is OPEN — the actual to-do list

### 2a. From the v207 developer review (see `docs/REVIEW-RETORT-v207.md`)

**All four findings are now CLOSED.** F1 + F4 in v208, F2 + F3 in v209 — see
`docs/REVIEW-RESPONSE-v209.md` for both in full.

**F2 — CLOSED (v209), owner chose option (a).** A failed post no longer costs
quota. Reading the tree narrowed the finding: the failure path already
RELEASED the slot; what failed was the DELIVERY of the delete, against a host
still holding SQLite's write lock. Retrying that write cannot make immediate
retry *mechanically* true, so the release is recorded in a process-local
tombstone that `_db_rate_count()` subtracts immediately, and the row is deleted
by the next request that can get a writer. Regression at
`SKRIBL_RATE_MAX_POSTS=1` with a REAL held `BEGIN IMMEDIATE`, plus a
counterexample that reproduces v208 and goes 429.
**Scope to remember:** true within the process that took the reservation —
the same scope the reservation itself claims. Multi-worker SQLite still waits
for the sweep or the TTL, i.e. v208 behaviour, never worse.
**Watch:** `RateEvent.id` is SQLite's rowid and rowids are REUSED. A tombstoned
row has exactly one legal deleter (`_sweep_tombstones`, which drops the
tombstone with it). Adding another deleter of pending rows without dropping the
tombstone is the way to break this. Pinned in `verify_txcontract`.

**F3 — CLOSED (v209) except the iPhone.** Fixed on the A1 template:
`unlockWebAudio()` runs inside the Play gesture, the promise is retained, the
loop source starts only once it resolves, a generation counter stops a late
start overtaking a stop, nothing is swallowed. Regression drives the real
button and instruments the ORDER (`resume` → `gesture-returned` →
`base-image-painted` → `loop-started:running`); it forces the async branch by
reporting `HTMLImageElement.complete` false, because the decoded-base cache
would otherwise make Play synchronous and hide the bug. Mutation-tested: remove
the gesture unlock and the two ordering pins go red.
**→ A real iPhone is the one thing still owed.** The harness's simulated
context unlocks late quite happily; a phone will not. Last iPhone item.

**Phone-audit widening (optional, unchanged).** The v207 audit is a strong
*right-edge + same-row horizontal* check. Extend to: `left < 0`, vertical
viewport overflow, overflow-hidden ancestor clipping, off-row collisions,
pseudo-element hit-area overlap. Not a known bug; a scope correction.

**Web Audio loop externalisation (new, measured).** The whole Web Audio loop
block in `app.js` is ~2,060 code bytes and is EDITOR-ONLY — the player has its
own `pa*` audio path. Moving it out the way `editor_tune.js` went would cut
roughly four times the v209 ratchet raise. Not done in the same pass as an
audio fix on purpose. `stopWebAudioLoop` has 8 call sites, several on teardown
paths.

### 2b. Standing owner items (unchanged for many builds)

- **DECISIONS.md #1** (visibility default `unlisted`) and **#2** (CSRF default
  off) — deliberately UNFLIPPED until authentication exists. A CSRF/auth
  tripwire warns when `current_user_id` is configured without `csrf` (tested
  both directions). Flip both together when cookie auth lands.
- **Hardware before any media-backend flip on live data:** S3Store has never
  run against a real bucket/MinIO (the suite verifies signatures only); Pad
  stylus path needs real-iPad minutes; A1's iOS audio fix and F3 above need
  a physical iPhone.

### 2c. The ratchet — signed off, nothing pending

Player-JS ratchet is **142,880** (target 153,600). Raised in small, flagged,
functional steps: +430 (A1 iOS audio, v203) · +60 (grid layout hook, v204) ·
+119 (cross-load guard, v206) · +23 (F4 hook, v208, **approved**) ·
**+510 (F3 gesture unlock, v209)**. Each is documented in
`harness/verify_player_isolation.py`. **Every raise to date is owner-approved**
— the v208 +23 and the v209 +510 were both signed off in the v209 session.
Nothing is pending. The externalisation noted in 2a would give back about four
times the last raise.

---

## 3. Owner decisions already made (do not re-litigate)

- Shape language is **functional and kept**: rounded-square tile = tool/opener;
  round toggle = on/off; pill segment = one-of-N with sliding highlight;
  labelled pill = named action. Only Flip's undo/redo (circles → tiles) was
  ever changed. Do NOT "unify to one shape".
- Tier-1 primary buttons **44/24 desktop, 40/22 phone**; tier-2 in-drawer
  toggles **32/18** (aligned to the 32px segments they share rows with);
  color dots 30; nudge 32 (30 phone); sub-44 controls get an **invisible 44pt
  tap area** (`::before` + `--tap-grow`, with `z-index:1` — without it the
  parent row wins the hit-test in the overflow band; verified by real clicks).
- 640/641 bare-glyph mobile header: **leave it** (intentional).
- No draw-on for Pad; no draft-slot parity for Flip; cosmetic draw-drawer
  divergences left.
- Toast: **"New here? — How it works →"** — just the link.
- Icons: **all SVG**; Hold's ×N count and nudge −/+ stay text (numbers /
  operators, not icons); the Move buttons carry a chevron (a page-RECT was once
  tried there and read as a "0" — pinned in verify_hold).
- Help: real button glyphs beside tappable-control pills only; concept pills
  stay icon-less.

---

## 4. The harness — how it protects you

60 suites, ~2,300 assertions. The **pixel/behaviour suites are the gate for
any UI change**: `verify_visual` (76), `verify_parity` (115), `verify_ux`
(264), `verify_cssplit` (17), `verify_player_isolation` (20), `verify_pages`
(44), `verify_tips` (43), `verify_lib` (8), `verify_hold` (37). Server-side:
`verify_txcontract` (34, incl. the real-AUTOCOMMIT regression),
`verify_postgres` (14, live in batch 15), `verify_s3` (25).

Things the harness now guards that it did not before this arc (each was a
real bug first): tap areas fire on a real click 5px outside the box; the Flip
drawer survives a file-input click; grid/motion/onion/tint light on `.active`;
the Repeat button lights (`.player-btn.active` in player.css); a released-but-undeletable post reservation stops counting at once and is swept by the next writer, and a FAILING sweep neither escapes nor loses the release; Pad's Play calls `resume()` inside the click gesture, before the canvas restore calls back; nudge pills do
not overlap and stack on phone; every control on-screen at 375/390 with each
drawer open; help pills carry the button's OWN glyph; page-bar icons are SVG;
Record closes Tune; a real AUTOCOMMIT engine is refused.

**Two suites have deliberate one-time flakes worth knowing:** `verify_s3` once
failed on a URL-shape assertion at batch 17 and passed 25/25 in isolation
(server state after many batches); `verify_cssplit`'s pressed-player scene
must stay LAST in its scene list — its click/focus bled into the next capture.

---

## 5. Procedures (exact)

**Environment prefix for EVERY tool call that runs the harness.** PostgreSQL
does not persist between calls — and in the v209 container it was **not
installed at all**, which the old prefix turned into a silent
`verify_postgres` SKIP rather than an error. Two clean runs were sealed-ready
before anyone noticed the evidence said `skipped 2`. So: install if missing,
then use a prefix that REFUSES to run without a database.

First call of a session, if `/usr/lib/postgresql` is absent:
```
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib
pip install psycopg2-binary --break-system-packages
mkdir -p /tmp/pgdata && chown postgres:postgres /tmp/pgdata
su postgres -c "/usr/lib/postgresql/16/bin/initdb -D /tmp/pgdata -A trust"
su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log -o '-p 5433 -k /tmp' start"
su postgres -c "/usr/lib/postgresql/16/bin/psql -p 5433 -h /tmp -d postgres -c \"CREATE USER skribl WITH PASSWORD 'skribl' SUPERUSER;\""
su postgres -c "/usr/lib/postgresql/16/bin/psql -p 5433 -h /tmp -d postgres -c 'CREATE DATABASE skribl_test OWNER skribl;'"
```
Then write `/tmp/pgup.sh` once and prefix every harness call with
`. /tmp/pgup.sh &&`. It probes the DSN, clears a STALE `postmaster.pid` only
when nothing is listening (the process sometimes survives a call and sometimes
leaves the pid behind, and `pg_ctl` then refuses to start against a live
port), and exits non-zero rather than letting a run proceed PG-less:
```
export SKRIBL_PG_DSN="postgresql://skribl:skribl@127.0.0.1:5433/skribl_test"
probe() { python3 -c "
import sqlalchemy as sa, os, sys
try: sa.create_engine(os.environ['SKRIBL_PG_DSN']).connect().close()
except Exception: sys.exit(1)" 2>/dev/null; }
if ! probe; then
  rm -f /tmp/pgdata/postmaster.pid
  su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log -o '-p 5433 -k /tmp' start" >/dev/null 2>&1
  sleep 2
fi
probe && echo "PG UP" || { echo "PG DOWN — refusing to run"; exit 1; }
```

**Run one suite:** `bash harness/run_harness.sh verify_ux.py` (server
auto-managed on :5001). **Never** hand-roll `flask run` for diagnostics: it
serves the blueprint's static files as 404s and produced a fake layout
collapse + a stray `instance/skribl_demo.db` once. Use the harness's server.

**Release run:** `python3 harness/release_run.py --restart --budget 240`, then
`--budget 240` repeatedly until `PASS`. **150 in the v209 container** (240 overran the per-call limit on batch 1 and produced no checkpoint at all); 240 elsewhere. The old note read **240, not 170** — verify_ux with the
phone-audit pins no longer finishes batch 1 inside 170s and the run restarts
from the top instead of checkpointing. Expect ~5 invocations.

**Finish EVERY doc edit before the release run.** `tree_hash()` covers every
file except `instance/`, `__pycache__` and the GENERATED list, so a one-word
fix to this handoff after a PASS invalidates the frozen hash and costs the
whole ~7-invocation run again. v209 paid that twice.

**Seal (in this order):** (1) run to PASS (writes `harness/RELEASE.md`);
(2) `rm -rf instance` and any `__pycache__`; (3) regenerate SHA256SUMS **last**:
```
{ echo "# SHA-256 of every file in this archive, excluding SHA256SUMS itself."; echo "# Verify from the archive root with:   sha256sum -c SHA256SUMS"; echo "#"; find . -type f ! -name SHA256SUMS ! -path '*__pycache__*' -print0 | sort -z | xargs -0 sha256sum; } > SHA256SUMS
```
(4) confirm `python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"` == RELEASE.md's tree hash; (5) `cd /home/claude && zip -rq skribl-vNNN-sealed.zip skribl-vNNN -x "*__pycache__*" -x "*/instance/*"`, copy to `/mnt/user-data/outputs/`; (6) extract the shipped zip and `sha256sum -c SHA256SUMS | grep -c ": OK$"` must equal the manifest count.

**On a version bump** update: `skribl/core.py` `SKRIBL_VERSION`, README.md,
ARCHIVE-README.md, START-HERE.md (the "expect NNN" manifest count appears
TWICE and must match the real file count; `verify_docs` checks it).

**Standing rules:** never raise a ratchet to fit your own commit without
flagging it for the owner; check the tree, not recollection; mutation-test
new suites; regenerate SHA256SUMS last; mp4 stays CI-skip.

---

## 6. Lessons this arc paid for (so they are not paid twice)

- **An old pin caught the new code.** The first draft of `_sweep_tombstones`
  (v209, F2) read `RATE_CLEANUP_BATCH` OUTSIDE its try block, so a cleanup
  failure escaped into a request whose reservation was already committed.
  `verify_review`'s injected-cleanup-failure pin — written rounds ago for the
  other janitor — caught it on the first release batch. The F2 suite I had
  just written did not: it tested the lock collision and not the
  cleanup-failure path. New suites test the bug you were thinking about; the
  old ones are what test the bug you were not.
- **A silent skip is a false green.** `verify_postgres` skipped in two
  otherwise-clean PASS runs because the container had no PostgreSQL, and the
  prefix was written to swallow that. The suite reports the skip honestly and
  `RELEASE.md` prints it in the header — reading it is the step that was
  missing. Prefer an environment check that REFUSES over one that degrades.

- **Headless is not the world.** The Flip drawer bug (v206) opened fine in
  headless every way tried and closed itself in real use — because it needed
  a real OS file dialog. The Repeat button "worked" in headless and looked
  dead in the browser (missing CSS in the emitted player.css). When the owner
  reports something headless can't reproduce, the owner is probably right;
  instrument, don't argue.
- **Measure the thing, not its container.** The nudge grid "fit at 375" —
  the grid BOX did; the pills inside overlapped. The phone audit now measures
  every control's rectangle.
- **The version footer is truth.** Cached-build theories were wrong twice;
  the `Skribl {Pad|Flip} · vNNN` footer settled it both times.
- **A pin can encode design history.** verify_hold's "no glyph on Move" was
  guarding against a rect that read as "0", not against arrows. Read the
  comment before rewriting a pin.
- **`.on` vs `.active`, and `.seg` vs ad-hoc.** Half the visual bugs were one
  control using a different convention than its siblings. Grep siblings first.

---

## 7. First things to do next session

1. **Put v209 on a real iPhone.** Pad → draw → Stop → Play with music: the
   replay must have audio on the first tap, from cold. That is the whole of
   what F3 still owes, and the only hardware item that blocks calling the
   integration contract closed.
2. Consider the Web Audio loop externalisation (2a) — measured at ~2,060 code
   bytes of editor-only code sitting in the player's payload.
3. Optionally widen the phone audit.
4. The remaining standing items are unchanged and all need hardware or auth:
   S3Store against a real bucket, the Pad stylus path on a real iPad,
   DECISIONS.md #1 + #2 when cookie auth lands.
