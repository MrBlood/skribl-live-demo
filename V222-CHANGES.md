# v222 — what changed since the sealed v221

**Evidence status: UNSEALED.** The full release aggregate has not been run
against this tree; `harness/RELEASE.md` and `harness/LAST-RUN.txt` still
describe the v221 seal and were deliberately not restamped (the v219 lesson:
an archive must not claim evidence it does not have). What HAS been run, all
green, immediately after the last edit in this file's scope:

    verify_drafts.py            16/16   (new — pins this release's core)
    verify_prefix.py            33/33   (extended 29 → 33)
    verify_layout.py            83/83   (section 4 rewritten — see below)
    verify_amber.py             21/21   (rewritten to the v3 contract)
    verify_dots.py              11/11   (rewritten to the v3 contract)
    verify_race.py              17/17
    verify_version.py           23/23
    verify_jsstrip.py           27/27
    verify_assetcache.py        12/12
    verify_lib.py                8/8
    verify_keys.py               9/9
    verify_storage.py           38/38
    verify_ux.py               302/302
    verify_player_isolation.py  22/22
    verify_pages.py             44/44
    verify_parity.py           115/115
    verify_tools.py            118/118
    verify_surfaces.py           7/7
    verify_visual.py            76/76
    verify_fix.py               18/18
    verify_hold.py              37/37
    verify_tips.py              43/43
    verify_csp.py               32/32
    verify_csrf.py              15/15
    verify_docs.py              39/39
    verify_integration.py       14/14   (env smoke, session start)
    verify_migrations.py        56/56   (env smoke, session start)

To seal: `python3 harness/release_run.py` (budgeted invocations), then
regenerate `SHA256SUMS` **last**, then archive. Seal order:
`HANDOFF-NEXT-SESSION.md` §5.

---

## Narrative

v222 is the durability release. An external pre-release review (28 findings,
three P0 — `docs/REVIEW-RESPONSE-v222.md` is the response log's natural home
when written; the review itself arrived as a .docx) independently converged on
DESIGN-DIRECTION.md's second prerequisite: a drawing you have not posted must
survive everything short of clearing it on purpose. Every claim of the
review's that was spot-checked verified against the tree verbatim, including
its prediction of *how* the passing prefix suite had missed a real defect.

**Navigation stays under the prefix because clicks are tested, not just
routes (review P0-1).** Four templates hardcoded root-literal hrefs
(`/flip`, `/` ×3), so any host mounting the blueprint under a `url_prefix`
had working pages whose links walked out of the app. All four now derive from
`url_for('.skribl_flip')` / `url_for('.skribl_editor')` — `.skribl_editor`,
not `.home`, because `.home` only exists when the host passes
`index_route=True`. `verify_prefix.py` proved every *route* resolved under
`/skribl` by navigating to each directly — which is exactly the shape of test
that cannot see a wrong link. It now clicks Flip→Pad and asserts the landed
URL, asserts the exact `href` attribute the Pad guard navigates with, and
carries a static gate refusing `href="/` in any Skribl template, so the
class is closed, not the instances.

**The mutation test of that pin found a false-green channel in the harness
itself.** Reverting one href produced four FAILs — and the run still
aggregated as `ok — 29/33 passed`, RESULT: PASS. `verify_prefix.py` was the
only summarising suite whose exit was unconditionally 0, and
`run_harness.sh` trusted exit codes without reading the summary line it was
quoting. Both layers are fixed: the suite exits 1 on failure like its
siblings, and the runner now refuses the class — any `X/Y passed` with X<Y
is a FAIL regardless of exit code. A green that cannot fail is not evidence,
and this one had been sitting inside every aggregate since the suite was
written.

**The debounce is no longer a loss window (review P0-2).** Draw a stroke,
leave within 1.2 s (Pad) or 0.8 s (Flip), and the work was gone — nothing
flushed on the way out. Both editors now flush synchronously on `pagehide`
and `visibilitychange('hidden')`, and Pad's in-app navigation flushes
explicitly before it decides anything else.

**"Is this work safe" is now measured, not inferred (review #19).** Pad's
leave guard is on its third predicate, and the history is documented at the
predicate because each version was wrong in a way the next fixed: v1 fired on
any drawing (dismissed unread), v2 fired on media presence (right only while
media bytes *couldn't* be stored — and silent when localStorage itself was
broken, which is when the drawing was the thing at risk). v3 flushes, then
asks whether the flush left the draft durable: `draftRev`/`durableRev`
revision comparison plus per-slot media durability. With working storage the
guard never fires — the direction doc's intended end state. With broken
storage it fires for exactly the work that would be lost, and the leave-sheet
copy now says that truthfully.

**Media bytes survive, in IndexedDB (the direction-doc prerequisite).**
`lib/draftstore.js` is a deliberately tiny promise wrapper — three verbs,
one object store, rejection means "not durable", no silent catch. Pad
captures photo/music `File`s at attach time (capture-phase listeners, so a
later handler clearing the input changes nothing) and deletes them with the
draft. Restore drives the stored bytes back through the *real* `<input>`
change pipeline via `DataTransfer`, so validation, the drawer handlers and
the pending-meta settings-reapply all run exactly as if the user had
re-picked the file — no second attach path to keep correct. Flip's quota
fallback, which used to drop the media bytes while a comment two screens up
asserted nothing could be lost (review #3), now spills the full payload to
IndexedDB and keeps a marked media-less record in localStorage for the fast
synchronous restore. The async merge back applies MEDIA ONLY, never frames:
the pagehide flush rewrites localStorage synchronously while its IndexedDB
put can die with the page, so the full payload may be one save older than
the drawing, and applying it wholesale could revert strokes. Media identity
is checked by NAME against the meta the lite record carries. (The first
version of the merge required savedAt equality between the two records; it
refused the dying-flush case entirely, which meant the media never came back
after exactly the navigation the flush exists to survive — caught by the
rewritten verify_amber.py before it shipped.)

**A durability problem is a state, not a toast (review #3).** "Autosave
failed" and "Saved without media" no longer fade after 1.6 s on either
surface — each describes an ongoing condition, and a warning that fades
claims the condition resolved. They clear when a successful save replaces
them. With bytes durable in IndexedDB, the amber pill's meaning inverts:
it used to describe a designed limitation; now it is a failure signal, and
a working system shows plain "Saved" with media attached.

**An empty tab can no longer delete a draft it doesn't own — including the
one it was just offered.** Two fences, found in two rounds. First: autosave
records carry a per-load writer id, and the empty-state clear refuses to
remove a record another tab wrote after this page loaded. Second, found by
the release aggregate itself: flushing on visibilitychange means a FRESH tab
flushes while still empty, and the empty-state path deleted the stored draft
— on Pad, with the restore banner still on screen offering it; on Flip, for
any record tryRestore rejects. Both surfaces now also gate the empty-state
clear on session OWNERSHIP: only a session that has written real work into
the slot — or accepted a restore of it (Flip's auto-restore, Pad's banner
confirm) — may treat its empty state as a deliberate clear; a record the
restore REJECTS confers nothing, and explicit discard via the banner's
clearAutosave is untouched. (The restore half of that rule came from the
second aggregate run: verify_fix's empty-clears-the-key regression test
restores and clears inside the first save's debounce window, where an
ownership rule keyed only to writes refused a clear the user had every right
to make.) The aggregate caught this as a
one-point loss in verify_strokegroups — its planted-draft scenario wrote
localStorage in a live page and reloaded, and the flush ate the plant the
same way it would eat a user's draft; that scenario now plants via init
script (a draft already on disk when the page opens), and the idle-flush
case is pinned directly in verify_drafts.py for both surfaces. Full
multi-tab arbitration still needs a project/draft-library model this tree
does not have — that remains an owner-scale item, recorded, not attempted.

**app.js stopped carrying the autosave machinery it never runs in the
player.** The whole draft path — serialize/write/schedule/read/restore, the
restore banner, its trigger bindings, and the leave guard — moved to a new
editor-only `editor_draft.js` (the fifth carve, after
editor_music/photo/shapes/draw). Every call site outside the moved region was
already `typeof`-guarded, which is what made the carve mechanical; ~17 KB of
raw source left the player's file, and the isolation ratchets stayed green
without being touched.

## Technical notes

- New files: `skribl/static/editor_draft.js` (carved + new durability
  machinery), `skribl/static/lib/draftstore.js` (IndexedDB store),
  `harness/verify_drafts.py` (14 assertions).
- IndexedDB: DB `skribl-drafts`, store `media`, keys `pad:photo`,
  `pad:music`, `flip:draft`. Writes resolve on transaction COMPLETE, not
  request success — a request can succeed and the transaction still abort on
  quota at commit, which is precisely when "durable" must not have been
  reported.
- Script order: `lib/draftstore.js` loads before `app.js` (Pad) and before
  `flip.js` (Flip); `editor_draft.js` loads last of the editor files because
  its restore path drives editor_photo/editor_music change handlers.
- `writeAutosave` captures the revision BEFORE serializing, so an edit
  landing mid-write leaves the draft correctly marked not-durable.
- Templates: the four fixed hrefs, the two new script tags per editor page,
  and the leave-sheet body copy (the old media-specific line would have been
  false in every case the sheet now appears).
- `harness/verify_layout.py` section 4 pinned the v2 guard predicate and
  failed the moment v3 landed — correctly. Rewritten to the v3 contract with
  the predicate history preserved in the pin, so nobody re-pins a superseded
  design. Its Flip back-link locator also matched on the literal
  `a[href='/']`, which P0-1 invalidated; it now matches the accessible name.
- `harness/verify_amber.py` and `harness/verify_dots.py` were the dedicated
  pins of the OLD amber contract ("media attached ⇒ amber, persistently").
  Both rewritten the same way: with a working store the honest light is
  green and the media actually comes back; the amber assertions — including
  the full re-add-card palette — moved under a broken-IndexedDB context,
  where they are still true. The old amber contract did not die; it moved to
  the failure case. `harness/verify_fix.py` — the original pin of the quota
  FALLBACK contract (bytes stripped, meta kept, saving continues, re-add
  card) — now runs its page with IndexedDB broken, because that fallback is
  only reachable when the store is unavailable; its assertions are otherwise
  unchanged.
- Flip's restored music is DECODED on merge (mirroring the draft-file load
  path), so a restored draft posts the cropped loop, not the whole sample,
  and the waveform is not blank.
- Mutation tests run and passing loudly: (d) removing either surface's
  session-ownership fence fails its idle-flush pin — Flip's needed a plant
  its restore rejects, because a healthy draft auto-restores and shields the
  record without the fence; (a) removing BOTH flush listeners
  fails the instant-reload pin — removing only `pagehide` survives because
  `visibilitychange` covers a reload, which is why both exist; (b) reverting
  the guard to media-presence fails the broken-storage pins; (c) the
  reintroduced hardcoded href fails through both the suite exit and the
  runner's new summary check.
- Open, recorded: Flip has flush + spillover but no leave-guard UI for total
  storage failure (both stores broken); the leave-sheet/pill strings are not
  yet pinned verbatim in verify_ux (batch with the next copy pass); share
  state machine (review #21/#22 — AbortController, and Pad must stop clearing
  the canonical draft on a failed share) is the next cluster and touches this
  file's code.
