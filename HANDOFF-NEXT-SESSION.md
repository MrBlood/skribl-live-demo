# Skribl — Handoff for the next session (written at the v211 seal)

**Read this first.** It is the complete state of the project: what shipped,
what is open, what the owner has decided, what the harness protects, and the
exact procedures. Everything here was verified against the tree, not recalled.

---

## 0. Where things are

| Thing | Location |
|---|---|
| **Sealed, shipped builds** | `/mnt/user-data/outputs/skribl-vNNN-sealed.zip` — v203 … v211 |
| **Current sealed build** | **v211** — tree `see harness/RELEASE.md`, 61/61, 1 skip (mp4), PG 20/20 (two live workers) |
| Working tree | `/home/claude/skribl-v211/` (identical to the seal at time of writing) |
| Demo `.skribl` files + previews | `/mnt/user-data/outputs/skribl-demos/` (also `harness/fixtures/` in-tree) |
| Design mockups (HTML, real pixels) | `/mnt/user-data/outputs/skribl-*.html` |
| Per-release response docs | `docs/REVIEW-RESPONSE-v200.md` … `v211.md` |
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
| v209 | 2337 | v207 review F2 + F3 closed — failed posts no longer cost quota (tombstoned release + real-lock regression); Pad replay unlocks audio inside the Play gesture (A1 template, order-instrumented, mutation-tested). ⚑ ratchet +510 B. |
| v210 | *see RELEASE.md* | THE IPHONE BUILD. The phone found shared links silent; two deterministic bugs, both reproduced in-harness before fixing: player loop bounds lived in `loadedmetadata` (Bug A); post-time crop dead on v2 payloads (Bug B). v209 review F1–F4 closed. Three real-device layout defects fixed; phone audit widened. Release language changed: "mechanism corrected; verified on [device]" only. |
| **v211** | *see RELEASE.md* | **iPhone audio CONFIRMED by the owner.** v210 review closed: Flip Web Audio parity (F1), crop/decode race both editors (F2), failed-post release durable across workers/restarts — PostgreSQL proven with two live gunicorn workers, SQLite via a sidecar journal (F3, option A), `_FK_ENGINES` add after both listeners (F4), player native fallback (H1). Space+drag no longer draws. |

Every seal: verified from its own shipped zip (`sha256sum -c`), every fix behind a mutation-tested or counterexample pin.

---

## 2. What is OPEN — the actual to-do list

### 2a. State of the integration contract

**The iPhone is green.** The owner confirmed audio on the device after v210.
The release wording is now earned: *mechanism corrected; playback verified
on device.* That closes the arc that began at v203.

**The v210 developer review is fully closed** in v211 — see
`docs/REVIEW-RESPONSE-v211.md`. The one structural change worth carrying in
your head: the failed-post quota contract is now **uniform across backends**
(no worker counts a failed reservation against an immediate retry), proven
live on PostgreSQL with two real workers and made durable on SQLite with a
sidecar journal beside the DB file. `docs/INTEGRATION.md` has the contract
and the per-backend mechanism.

**Remaining open, none blocking:**
- Web Audio loop externalisation (~2,060 B of editor-only code in the
  player's payload) — measured repeatedly, now clearly worth its own build.
- Direct-buffer playback for zero-crossfade loops — deferred to keep the
  audio fixes' causal proof clean.
- Phone audit: still a strong right-edge/2-D/clip check; no known gap.

**Two things to know about the harness in this environment:**
- `verify_postgres` now launches a second gunicorn host (`harness/f3_host.py`)
  on PORT+1 for the cross-worker pin. It needs `gunicorn` and a live PG.
- `verify_audiostate` posts several skribls per run (F2 holds a decode open
  and submits; H1 needs a 3 s drawing). Fine on SQLite; noisy in the table.

### 2b. Standing owner items (unchanged for many builds)

- **DECISIONS.md #1** (visibility default `unlisted`) and **#2** (CSRF default
  off) — deliberately UNFLIPPED until authentication exists. A CSRF/auth
  tripwire warns when `current_user_id` is configured without `csrf` (tested
  both directions). Flip both together when cookie auth lands.
- **Hardware before any media-backend flip on live data:** S3Store has never
  run against a real bucket/MinIO (the suite verifies signatures only); Pad
  stylus path needs real-iPad minutes; A1's iOS audio fix and F3 above need
  a physical iPhone.

### 2c. The ratchet

146,911 (target 153,600). Owner: set to fit. Every raise is accounted for in
`harness/verify_player_isolation.py`. The externalisation in 2a is how to
give most of it back.

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

61 suites, ~2,400 assertions. New in v210: `verify_audiostate` (16) — the two iPhone bugs, behavioural, mutation-tested. The **pixel/behaviour suites are the gate for
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

- **The phone is not optional, and green is not evidence for it.** Three
  builds said "iOS audio fixed" on the strength of ordering pins. The player
  was silent the whole time. Automated browsers cannot certify device media
  policy; the release words for it are now "mechanism corrected; verified on
  [device]", and the second half waits for the device.
- **Reproduce before you fix.** Both v210 bugs were reproduced in the harness
  (suppress `loadedmetadata` → zero sources; measure posted bytes → full
  source) before a line changed. Both fixes were then trivial. The unlock
  theory that came first was wrong and would have shipped as "fixed" again.
- **A silent catch destroys the one piece of evidence you need.**
  `paLoopBuffer`'s `catch (e) { paBuffer = null; }` made "threw" and
  "returned null" identical to every caller for three builds. It warns now.
- **Measure the thing, not your model of it.** `trimEnd == 20` passed against
  the broken build (an uncropped payload keeps the authored trim). A byte
  count computed for mono was wrong for stereo. The pin reads the WAV header.
  A strokeless fixture "proved" playback was broken when `play()` simply had
  nothing to play. `fitBrand` measured `scrollWidth`, which never grows when
  things OVERLAP. The nudge grid "fit" — the pills inside did not. Every one
  of these looked like a real regression for ten minutes.
- **A design's own conventions must be readable by its audit.** The widened
  phone audit false-positived on `.seg` pills, `--tap-grow` hit areas and the
  thumbnail card until it was taught the shape language it was checking.

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

1. Nothing is owed on hardware. The iPhone confirmed audio; the contract is
   closed. Start from the externalisation in 2a if you want the ratchet back.
2. Standing items unchanged: S3Store against a real bucket, Pad stylus on a
   real iPad, DECISIONS.md #1 + #2 when cookie auth lands.

## 8. If a temporary on-device diagnostic is ever needed again

v210 used one (`audiodebug.js`, wrapping the real Web Audio API rather than
hooking `app.js`, behind a sticky `?audioDebug=1` cookie, collapsed to a pill
so it never covered controls) and REMOVED it before sealing. It was the single
most useful thing in the arc. If it comes back: separate file; zero references
in `app.js`; observe the API, not the app's beliefs; must not ride into the
player budget; and its useful checks belong in the harness before it goes.
