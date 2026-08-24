# v221 — what changed since the sealed v220

**Evidence status: sealed.** `harness/RELEASE.md` is generated from the full
aggregate run against this exact tree and is the ONLY place the tree hash,
suite count and assertion count live. This file deliberately quotes none of
them: v220's review snapshot quoted the tree hash in prose and was stale the
moment it was saved, because the file was itself inside the hash it quoted.
Volatile facts belong in generated documents. That lesson is now structural.

---

## Narrative

v221 is the identity release. v220 shipped the engine work and a design
direction; v221 made the app *look* like that direction, one owner-approved
drop at a time, and then paid down the release-hygiene debt the v220 review
had flagged.

**The review found the paperwork one step behind the tree — and then one step
behind itself.** The v220 archive verified clean (manifest, boot, every suite
re-run from a cold unpack), but `RELEASE.md` described an earlier tree, and
the snapshot document explaining that mismatch quoted a hash that was *also*
stale, for the exact reason it warned about. Worse, the two tree-hash
implementations disagreed with each other on this archive: `run_harness.sh`'s
banner and `release_run.py`'s record excluded different files (two PostgreSQL
gunicorn logs), so one tree printed two hashes. Both defects are fixed in this
tree (see technical notes) and the guard that should have caught the second
one has been repaired.

**The header stopped being an application chrome and became a piece.** In
order: the gradient icon and the word "Skribl" left Pad's header (the host
site is branded; the header names the *mode*), which returned ~66–108px of a
~358px phone header. The wordmarks then went through eleven mockup rounds
with the owner — icons, monograms, hand-lettered tags — and landed on
graffiti piece lockups: **SKRIBL PAD** and **FLIP MODE** as stacked
throw-ups with a spray-cloud halo, block shadow, ink outline, brand-gradient
fill, shine pass, and the ORIGINAL logo star (the exact polygon still on the
player's card) demoted to the glints, dimmed to lavender at the owner's
request. They render at 44px — the height of the tallest element in either
header — one size at every viewport, per the wordmark-parity pin.

**The accent was consolidated, demoted, and un-demoted — and all three states
survive.** The audit found the real accent footprint was ~135 sites, a third
of them hardcoded hexes unreachable from `--accent`. Consolidation folded
them into tokens; a full demotion to neutrals then shipped, and the owner's
verdict was immediate and correct: flat. The demotion was reverted in four
lines because it had been built as *role tokens* (`--ui-hi`, `--ui-active`,
`--ui-line`, `--focus-ring`) rather than scattered edits. The tokens remain,
pointed at the accent; the `:root` comment records all three palettes (FULL
ACCENT — current; QUIET — tried, rejected; TINTED QUIET — untried). The
lesson for any retry: quiet cannot ship alone; it needs the "5% vandalized"
element with it, which v221's marks now are.

**What was deliberately NOT done**, and why, is recorded in the open-items
section. Most notably: `DESIGN-DIRECTION.md` ordered durable drafts and
pointer identity ahead of visual work. The owner chose the identity work
first. That is an owner's call to make and it is recorded as one — the two
prerequisites remain open, unchanged in scope, and remain the direction
document's top of list.

## Technical notes

**Tree-hash unification (release hygiene).** `run_harness.sh:_tree_files()`
now excludes `harness/.pg_gunicorn.log` and `harness/.pg_f3_gunicorn.log`,
matching `release_run.py`'s `GENERATED` byte for byte. The two
implementations were verified to produce the identical hash on this tree
before the seal run was started. The parity assertion in `verify_docs.py`
existed but its filename regex matched only `.md|.txt`, so the diverging
`.log` entries were invisible to it — the regex now includes `.log`. The
stray `harness/.pg_f3_gunicorn.log` that shipped inside the v220 archive
(1,626 bytes of runtime log) has been deleted.

**Header marks.** Both lockups are inline SVG in the templates
(`skribl_editor.html`, `skribl_flip.html`) with per-template defs ids
(`skmInk/skmSoft`, `fmmInk/fmmSoft`) to avoid collisions with the editors'
other inline SVGs. `role="img"` + `aria-label="Skribl Pad"` / `"Flipmode"` —
the marks are pictures of words, and assistive tech still gets the words;
this is the Flip-Mode-recognition lesson applied to its own successor. The
SVGs were produced by a session-local generator (not shipped; the shipped
SVGs are the settled artifact — edit them directly, no regeneration step
exists in-tree). Standalone copies were delivered to the owner for host-site
use.

**The (0,3,1) rule.** `.header .brand svg.brand-mark { height: 44px }` must
outrank the ≤340px player-only tier rule `.header .brand svg { 30px }`
(specificity 0,2,1) further down `styles.css`, which otherwise catches Pad's
mark and squashes it to 30×30 — observed, fixed, and commented at the rule.
Do not "simplify" that selector.

**`.brand svg` rules are player-only.** Pad has no icon; the player keeps
its branded card. Those rules must stay in `styles.css` because `player.css`
is EMITTED from it (`cssgraph.py --emit`), and `.brand svg` is in the
player's live-selector set. Any `styles.css` edit requires re-emitting;
`verify_cssplit.py` fails byte-for-byte if you forget (it caught exactly
that once this session).

**verify_ux wordmark pins.** Rewritten twice this cycle, intent preserved
each time: text-tier assertions (FLIPMODE/FLIP/FM at seven widths) became
"exactly one visible mark, carrying the word for assistive tech, at every
width"; the font-size parity check became rendered-size parity (44 vs 44).
The `_HDR` probe measures whatever brand content is visible instead of
assuming an `<svg>` mark exists.

**Accent state.** Role tokens exist and point at the accent. Canvas
`fillStyle` literals remain in `app.js`/`flip.js` (canvas cannot read
`var()`; `app.js` sits ~185 B under its byte ratchet, so the
computed-style helper waits for a session that re-measures the ratchet).
The share-card star gradient (`editor_post.js`) and the player logo keep
literal colors on purpose: brand-in-content does not follow UI chrome.

**Files.** `REVIEW-SNAPSHOT.md` deleted — it existed to flag the v220
evidence gap, which this seal closes; its sealing-order checklist moved to
`HANDOFF-NEXT-SESSION.md`. Net manifest count: 203 (was 204: −snapshot,
−stray log, +this file).

## Open items, in the order the next session should consider them

1. **Durable drafts** and **pointer identity** — still the direction doc's
   prerequisites, unchanged, deliberately deferred by the owner this cycle.
   The amber pill and Pad's leave guard exist BECAUSE persistence is
   partial; do not hide them before fixing it.
2. **Onion-skin promotion** — mechanism complete (`#onion*` in Flip's tune
   panel, depth + tint working). Two open calls: placement on the FILMSTRIP,
   not the pagebar (the pagebar just escaped clipping jail at 320/344); and
   vocabulary — long-press is right, but "Hold" is already a labelled
   page-duration feature six pixels away.
3. **Copy pass** — every string is pinned verbatim in `verify_ux`; do it as
   one batch with its pin updates. "Post to Skribl" already sheds to "Post"
   below 640. Leave "Flip Mode" alone (documented recognition lesson).
4. **Tray removal / five-control Pad** — +58px canvas (+22% height at 390),
   but it is the front edge of the direction doc's restructure, not a
   standalone tweak. Own session, direction doc open.
5. **Accent demotion retry** — only with TINTED QUIET plus one loud
   signature element. The palettes are in `:root`; the retry is four lines.

## Environment traps (verified again this session)

* `mv /etc/apt/sources.list.d/nodesource.* /tmp/` before any `apt-get`.
* PostgreSQL does not survive between tool invocations — start it inside
  every invocation that needs it; `verify_postgres` skips (not fails)
  without it.
* Flask dev servers also die between invocations; boot and test in ONE
  invocation.
* Playwright screenshot diffs: let animations settle (~1400ms for Pad's
  drawer slide) or an 11–15% pixel diff appears that is pure timing. Two
  screenshots of identical trees diffed 0.000% once settled.
