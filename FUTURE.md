# FUTURE.md — where Skribl goes next

This is not a backlog. `START-HERE.md` has the known-open list, ordered and
honest. This is the argument for what Skribl *is*, what it could become, and
which of the obvious next moves are traps.

Read it after you have the demo running. It is opinionated on purpose; disagree
with it in writing and replace this file.

---

## 1. What Skribl actually is

Two tools that look similar and are not.

**Pad records a performance.** It captures the act of drawing — every point with
its timestamp — and replays it. The artefact is a *process*. That is rare. Almost
nothing on the web records drawing as a time series and hands you back a link.

**Flip is frame-by-frame animation.** Pages, onion skin, per-page holds, fps. The
artefact is a *loop*.

They share a payload format, a toolbar, and a player. They diverge in every
behaviour that touches time, and most of the bugs in this project's history live
exactly on that seam: a fix applied to one surface and not the other, or a
control named `musicBtn` in Flip and `musicOpenBtn` in Pad.

**The strategic point:** the recording is the rare thing. A GIF of a drawing is
commodity. A *replay* of a drawing — watchable, scrubable, with the timing the
artist actually used — is not. If Skribl ever needs a one-sentence pitch, it is
"drawings that draw themselves."

---

## 2. The three constraints that shape everything

### Payloads are base64 and inline in Postgres, and their size is a RANGE

**This heading used to read "~476 KB" as though a payload had one size.** It
does not, and the single number hid the term that actually matters. A
drawing-only post is small. A post carrying media is bounded by the caps in
`skribl/validation.py` and `app.py` — per-item audio and image limits, under an
overall `MAX_CONTENT_LENGTH` on the request — and the audio term dominates
everything else by an order of magnitude, because the posted loop is stored as
uncompressed PCM WAV. Read the constants; do not trust a number in this
sentence.

The rate limiter bounds the flow rather than the size: `validation.py` does that
multiplication itself in a comment beside the caps, and the answer is hundreds of
megabytes per hour per IP into the database. That is the ceiling on every
feature. Layers multiply it. Longer animations multiply it, and every byte lands
in the backups too.

`skribl/storage.py` has three real backends: `InlineStore` (default, v131
behaviour), `LocalDiskStore`, and `S3Store` — the S3 path is a full
implementation (hand-rolled SigV4 signing, content-addressed PUT/GET/LIST/DELETE
over `urllib`, no new dependency), wired in `app.py` behind
`SKRIBL_MEDIA_BACKEND=s3` and exercised by `harness/verify_s3.py`. So the
externalisation seam is DONE; what remains is a product decision, not a backend:
whether to raise the payload ceiling (layers, longer animations) now that the
bytes no longer have to live in `payload_json`.

Externalise before any feature that increases payload size. The mechanism is
ready; the schema decision is the owner's.

### `app.js` serves both the editor and the player — MOSTLY CLOSED

**This section used to say a viewer downloads "the entire authoring surface",
and that stopped being true several releases ago.** Four editor-only files —
`editor_draw`, `editor_shapes`, `editor_music`, `editor_photo` — were carved out
and `verify_player_isolation.py` asserts the player loads none of them. The
player links its own generated `player.css`, not the whole of `styles.css`. And
the JS size target the split existed to reach is now MET, by the serve-time
comment strip in `skribl/jsstrip.py` rather than by any split at all.

**No size figure is quoted here on purpose.** The ones that used to be went
stale by tens of percent while the sentence around them stayed confident. Run
`./harness/run_harness.sh verify_player_isolation.py`; its last assertion prints
JS, HTML, CSS, the sum and the gzipped total, and fails if any grows.

**What genuinely remains:** `app.js` itself is still loaded by both surfaces and
is still the largest single file the player pulls, and a handful of editor
globals remain reachable there — the suite counts them against a ratchet whose
target is zero. The outstanding size question is now CSS, not JS: the player's
stylesheet sits well above `CSS_TARGET`, and its lever is
`harness/tools/cssgraph.py`'s classifier rather than a carve.

The v132 split was attempted and reverted (see `docs/REFACTOR-v132.md`) because
a regex call graph misclassified functions the player needs. **This section used
to say "use an AST; `node` is available" — that was tried and DISPROVED.**
`harness/tools/refgraph.js` fails its own superset gate and would move all four
of the functions the v132 attempt got wrong; the v132 failure was load order,
not classification. Do not spend the day rediscovering that.

### The two editors duplicate their controllers

`app.js` and `flip.js` both drive the *same* shared partials —
`_skribl_draw_drawer.html`, `_skribl_music_drawer.html`,
`_skribl_image_drawer.html` — with two independent implementations of the
eyedropper, recent colours, smoothing, photo adjustments and music trimming.

Every fix must be made twice, by someone who remembers there are two. Most of
this project's recurring bugs are that sentence playing out.

The v142–v174 work moved eight modules into `static/lib/` — `canvassizes`,
`posted`, `postedui`, `report`, `segslider`, `tooltip`, `hints`, `helpsearch` —
each shared by both surfaces. **That is the pattern to continue.** The drawer
controllers are the next and largest candidate.

---

## 3. Three futures, and which one to take

### A. The tool stays a tool

Polish Pad and Flip, ship them as a standalone site, let people share links.

*For:* it is what exists, it is nearly done, and the drawing tool is the rare
part. *Against:* no retention loop; people make one Skribl and leave.

**Cost:** weeks. **Risk:** low.

### B. The tool becomes a feature of someone else's platform

Mount the blueprint in a host application. `init_skribl()` is one call, the CSRF
seam is a three-element tuple, and `verify_prefix.py` proves it works mounted
under a prefix in a real browser.

*For:* distribution solved by someone else; the hard part is already built.
*Against:* you inherit their constraints, their release schedule, and their
answer to the visibility question.

**Cost:** days of integration, plus whatever the host needs. **Risk:** depends
entirely on the host saying yes.

### C. The tool becomes a network

Accounts, follows, a feed, moderation. `GET /api/skribls` already does keyset
pagination and a three-state visibility model.

*For:* the biggest upside. *Against:* the code is the easy half. A network with
nobody on it is worthless, and moderation is a permanent operational duty, not a
feature you ship once.

**Cost:** 6–18 months solo. **Risk:** high, and mostly non-technical.

### The recommendation

**A, then B, and treat C as a thing you back into rather than aim at.**

There is a fourth option worth more than it sounds: **join a network instead of
building one.** Every Skribl is already a public URL with OG meta and a share
card, so a link posted to Bluesky, Mastodon or Discord already produces a rich
preview. AT Protocol is open in the direction that helps — you can build on the
network without running one. That is a far smaller project than a Bluesky clone
and puts the tool in front of people who already exist.

---

## 4. Product ideas, ranked by (value ÷ cost)

**Ship-worthy now:**

1. ~~**Selection and transform.**~~ **SHIPPED.** Marquee select, move, uniform
   scale from the corners, rotate from a grip, cut/duplicate/paste and flip
   H/V — `verify_select.py`, 56 assertions. Lasso specifically was not built:
   selection is by stroke GROUP rather than by point, because moving half a
   stroke splits a line down the middle and bakes a connecting segment into the
   replay. A lasso over whole groups would be a nicer marquee, not a new
   capability.
2. **Two layers, not a layer stack.** Rough and clean. Most of the workflow
   benefit at a fraction of the complexity. *This used to say "blocked on the
   storage backend"; that stopped being true when media externalised. The real
   blocker is the PAYLOAD SCHEMA — a layer is a field the player must honour,
   so it is an owner decision, not an engineering one.*
3. ~~**A real timeline.**~~ **SHIPPED (v226).** Drag to reorder and holds
   already existed — the hard half. Range selection and page-span copy/paste
   landed on the strip rather than in a management cluster, per the direction:
   shift-click or hold-and-sweep to select a run, and Copy / Delete / ×hold /
   the arrows re-scope to it instead of multiplying. `lib/pagespan.js`,
   `verify_pagespan.py`. What is still absent is a scrubbable time RULER —
   this bought range editing, not a timeline view.
4. **Import a reference.** Draw over a video frame or image sequence. Still
   missing entirely; a still image per page is all there is.

**Speculative, and interesting:**

5. **Replays as a teaching format.** The recording captures *how* something was
   drawn. A "watch it build" mode with variable speed is a genuinely different
   product from a GIF — closer to a lesson than a post.
6. **Collaborative pages.** Flip's pages are independent; two people could hold
   different pages of the same animation. The payload format already separates
   them.
7. **Skribl as a reply.** A drawing in response to a drawing, with the original
   as an onion-skinned underlay. This is the feature that would make a network
   worth having, and it needs almost nothing new — onion skin and background
   images already do the work.

**Deliberately not doing:**

- Free-form canvas sizing. A closed set of ratios is what makes a feed possible.
- Ranked feeds. Reverse-chronological is correct until it demonstrably is not.
- Multi-take. A product decision first, a data model second.

---

## 5. What this project has learned, and should not relearn

Every one of these cost real time. They are in `START-HERE.md` too; they are
here because they are the actual inheritance.

**Run it, do not read it.** Every bug found in the v142–v174 work was found by
executing something. The code always read correctly. A stroke-width of 1.1, a
`display: flex` defeating `[hidden]`, a `pointerType` check on events that carry
no `pointerType` — all of them survived review and died on first run.

**A property assertion is not a rendering assertion.** A suite counting
`!el.hidden` passed while seven sections sat visibly on screen. Use
`offsetParent`, bounding boxes, computed style.

**Measure geometry, never arithmetic.** Summing element widths and calling the
remainder "free space" was wrong twice, because flex shrinks controls before
anything overflows. Force the candidate into the DOM and read `scrollWidth`.

**A retry must accept on the property the assertion checks.** A WebM test
retried on byte count and asserted on duration; a large 0.001s file passed the
gate and failed the assertion, flaking three times before the cause was found.

**Check the server log before theorising about the client.** Three client-side
theories were chased for a "share does nothing" bug that was a dead database,
visible in one line of the log, reported from a desktop the whole time.

**The two surfaces diverge; assume it.** When fixing anything in one editor, the
first question is what the other one does. Roughly half the bugs in this
project's history are that question going unasked.

**When a compromise is made for a layout, revisit it when the layout changes.**
"FM", the 15px wordmark, the 1px grid inset — all correct once, all wrong later,
all shipped for months.

---

## 6. If you do only one thing

Turn on media externalisation in the deployment.

The S3 backend is already built and tested; the remaining work is operational,
not code — set `SKRIBL_MEDIA_BACKEND=s3` (or `local`) with its credentials so
new posts stop writing base64 blobs into `payload_json`. That is the
precondition for layers, for longer animations, for more than a handful of
users, and for anyone else being willing to host this. Everything else on the
list gets easier once the bytes are out of the database.

---

## 6b. The orphan-sweep race — CLOSED in v266

This section documented the one known correctness gap: an orphan-media sweep
could delete an object a concurrent post had just reused, because the post's
association row commits in the host transaction after the bytes are written and
no delete-time check could see it. It is fixed. A poster now writes a short-TTL
COMMITTED pending-media claim (skribl_pending_media) the moment after it writes
the bytes; the sweeper unions unexpired claims into its reference check and
re-checks per key immediately before deleting. The deterministic reproduction —
a claim committed at the stat seam must spare the object — lives in
verify_sweepjob and fails if the per-key re-check is removed. See DECISIONS.md
(v266) for the design and the honest SQLite bound.

## 7. The honest state

The tool is good. It is better than it needs to be for a demo and not yet enough
for a platform. The engineering is unusually well tested for a project this size
— the assertion and suite totals are in `harness/RELEASE.md`, generated by the
run rather than typed here, because the three numbers this sentence used to
carry went stale by a factor of four and said so with total confidence — plus a
PostgreSQL concurrency suite that runs four gunicorn workers and proves the
rate limiter admits exactly its quota under twelve simultaneous posts.

What it does not have is users. That is not an engineering problem, and no
amount of further polish will solve it.

The next real milestone is not a version number. It is the first person who is
not you making something with it and sending you the link.
